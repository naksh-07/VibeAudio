"""AntiOS PreToolUse Guard Engine.

Enforces deterministic boundary protection, framework self-protection,
path canonicalization, and workspace boundary confinement with strict fail-closed semantics.
"""

from __future__ import annotations
import fnmatch
import os
from typing import Any, Dict, List, Optional, Tuple

from framework.core.config import AntiOSConfig, load_config


# Immutable Core Zones that CANNOT be disabled or modified via adapter configs
IMMUTABLE_CORE_ZONES: List[str] = [
    ".agents",
    "framework",
    "antios.config.json",
    ".git",
]


def evaluate_tool_call(
    input_data: Any,
    config: Optional[AntiOSConfig] = None
) -> Tuple[str, Optional[str]]:
    """Evaluates a PreToolUse hook payload against security boundaries.

    Returns:
        (decision, reason) where decision is either "allow" or "deny".
    """
    try:
        # 1. Validate JSON root type
        if not isinstance(input_data, dict):
            return "deny", "AntiOS Security Guard: Invalid JSON root type (must be object). Failing closed."

        # 2. Extract and validate toolCall
        tool_call = input_data.get("toolCall")
        if not isinstance(tool_call, dict):
            return "deny", "AntiOS Security Guard: Missing or malformed toolCall object. Failing closed."

        args = tool_call.get("args")
        if not isinstance(args, dict):
            return "deny", "AntiOS Security Guard: Missing or malformed tool args. Failing closed."

        target_file = args.get("TargetFile")
        if not target_file or not isinstance(target_file, str):
            return "deny", "AntiOS Security Guard: TargetFile must be a non-empty string. Failing closed."

        # 3. Extract and validate workspacePaths
        workspace_paths = input_data.get("workspacePaths")
        if not workspace_paths or not isinstance(workspace_paths, list) or len(workspace_paths) == 0:
            return "deny", "AntiOS Security Guard: workspacePaths must be a non-empty list. Failing closed."

        canonical_workspaces: List[str] = []
        for ws in workspace_paths:
            if not isinstance(ws, str) or not ws.strip():
                return "deny", "AntiOS Security Guard: workspacePaths contains invalid entry. Failing closed."
            c_ws = os.path.normcase(os.path.abspath(os.path.realpath(ws)))
            if c_ws not in canonical_workspaces:
                canonical_workspaces.append(c_ws)

        if not canonical_workspaces:
            return "deny", "AntiOS Security Guard: workspacePaths contains invalid entry. Failing closed."

        # 4. Resolve TargetFile and matching workspace root
        if not os.path.isabs(target_file):
            # Check if relative target matches an existing file in any workspace
            matched_root = None
            matched_resolved = None
            for ws_root in canonical_workspaces:
                candidate = os.path.normcase(os.path.realpath(os.path.abspath(os.path.join(ws_root, target_file))))
                try:
                    if os.path.commonpath([candidate, ws_root]) == ws_root and os.path.exists(candidate):
                        matched_root = ws_root
                        matched_resolved = candidate
                        break
                except ValueError:
                    pass

            if not matched_root:
                matched_root = canonical_workspaces[0]
                matched_resolved = os.path.normcase(os.path.realpath(os.path.abspath(os.path.join(matched_root, target_file))))
            
            repo_root = matched_root
            target_resolved = matched_resolved
        else:
            target_resolved = os.path.normcase(os.path.realpath(os.path.abspath(target_file)))
            # Longest-prefix matching among all workspaces
            containing_roots: List[str] = []
            for ws_root in canonical_workspaces:
                try:
                    if os.path.commonpath([target_resolved, ws_root]) == ws_root:
                        containing_roots.append(ws_root)
                except ValueError:
                    pass

            if containing_roots:
                containing_roots.sort(key=len, reverse=True)
                repo_root = containing_roots[0]
            else:
                repo_root = canonical_workspaces[0]

        # 5. Load config if not provided
        if config is None:
            config = load_config(repo_root)

        # 6. Confinement Check: TargetFile must reside within matched repo_root
        is_inside_repo = False
        try:
            if os.path.commonpath([target_resolved, repo_root]) == repo_root:
                is_inside_repo = True
        except ValueError:
            is_inside_repo = False

        if not is_inside_repo:
            return (
                "deny",
                f"AntiOS Boundary Policy: Modifying files outside the workspace repository ({repo_root}) "
                f"is strictly forbidden. Target: '{target_file}' -> '{target_resolved}'. Failing closed."
            )

        # 7. Framework Self-Protection (Immutable Core + Configured Zones)
        all_protected_zones = list(dict.fromkeys(IMMUTABLE_CORE_ZONES + (config.protected_zones if config else [])))
        protected_self_zones = [
            (zone, os.path.normcase(os.path.abspath(os.path.join(repo_root, zone))))
            for zone in all_protected_zones
        ]

        for zone_name, zone_path in protected_self_zones:
            try:
                if os.path.commonpath([target_resolved, zone_path]) == zone_path:
                    return (
                        "deny",
                        f"AntiOS Self-Protection Policy: Modifying AntiOS framework governance files, "
                        f"hooks, or configurations ({zone_name}) is strictly forbidden. "
                        f"DO NOT RETRY THIS ACTION. Re-evaluate your plan."
                    )
            except ValueError:
                pass

        # 8. Decompose relative path for domain boundary and alias checks
        rel_path = os.path.relpath(target_resolved, repo_root)
        rel_norm = rel_path.replace("\\", "/").lower().strip("/")
        parts = rel_path.split(os.sep)

        # 8.3 alias defense on self-protection zones and configured protected zones/domains
        alias_targets = ["framework", "agents", "antios"]
        for pz in config.protected_zones:
            c = pz.replace("\\", "/").strip("/").split("/")[0].lower()
            if c and c not in alias_targets:
                alias_targets.append(c)
        for dp in config.protected_domain_paths:
            c = dp.replace("\\", "/").strip("/").split("/")[0].lower()
            if c and c not in alias_targets:
                alias_targets.append(c)

        for part in parts:
            part_lower = part.lower()
            if "~" in part_lower:
                prefix = part_lower.split("~")[0]
                if (
                    any(fnmatch.fnmatch(part_lower, f"{z[:6].lower()}~*") for z in alias_targets if len(z) >= 1)
                    or (len(prefix) >= 3 and any(z.startswith(prefix) for z in alias_targets))
                ):
                    return (
                        "deny",
                        f"AntiOS Boundary Policy: 8.3 alias '{part}' targeting protected governance or domain files "
                        f"is strictly forbidden. Failing closed."
                    )

        # 9. Check Upstream Domain Boundaries (Multi-segment and segment-level)
        domain_targets = [p.replace("\\", "/").lower().strip("/") for p in config.protected_domain_paths]
        patterns = [p.lower() for p in config.forbidden_patterns]

        # Multi-segment prefix check (e.g. "src/core" or "vendor/upstream")
        for dom in domain_targets:
            if dom and (rel_norm == dom or rel_norm.startswith(dom + "/")):
                return (
                    "deny",
                    f"AntiOS Boundary Policy: Modifying '{dom}' (upstream domain core) is strictly forbidden. "
                    f"Protected by {config.name}. Direct implementation to application layers."
                )

        # Individual segment checks & pattern matching (including 8.3 aliases)
        for part in parts:
            part_lower = part.lower()
            if part_lower in domain_targets:
                return (
                    "deny",
                    f"AntiOS Boundary Policy: Modifying '{part}' (upstream domain core) is strictly forbidden. "
                    f"Protected by {config.name}. Direct implementation to application layers."
                )

            for pat in patterns:
                if fnmatch.fnmatch(part_lower, pat):
                    return (
                        "deny",
                        f"AntiOS Boundary Policy: Modifying path matching '{pat}' ({part}) is strictly forbidden. "
                        f"Protected by {config.name}."
                    )

        # 10. All checks passed
        return "allow", None

    except Exception as e:
        # STRICT FAIL-CLOSED ON ANY UNHANDLED EXCEPTION
        return "deny", f"AntiOS Security Guard Fatal Exception: {str(e)}. Failing closed."
