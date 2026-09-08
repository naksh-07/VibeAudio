"""AntiOS 3.0 PreToolUse Security Guard Hook.

Intercepts native mutation tool calls (write_to_file, replace_file_content)
before physical execution.
Enforces multi-workspace containment, longest-prefix matching, immutable core
protection, and Windows 8.3 alias defense.

Runtime Invariants:
- INV-04: Fail-closed boundary enforcement.
- INV-10: 4-Zone ownership boundary (SOURCE != INSTANCE != PROJECT != ANTIGRAVITY).
- INV-11: Zero framework imports (pure stdlib + local hook helpers).
- INV-12: Sanitized telemetry emission.
- High performance: < 10ms execution budget.
"""

from __future__ import annotations

import fnmatch
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

# Sibling import bootstrap (zero framework imports)
HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
if HOOK_DIR not in sys.path:
    sys.path.insert(0, HOOK_DIR)

import path_resolver
import emitter

# Immutable Core Zones that CANNOT be modified via tool calls
IMMUTABLE_CORE_ZONES: List[str] = [
    ".agents",
    ".antios",
    "antios.config.json",
    ".git",
    "framework",
]

# Read-only tools that must never be blocked by boundary checks
READ_ONLY_TOOLS = {
    "view_file",
    "read_url_content",
    "list_dir",
    "grep_search",
    "find_by_name",
    "list_resources",
    "read_resource",
    "search_web",
    "ask_question",
    "schedule",
    "manage_task",
    "manage_subagents",
    "gemini_search_docs",
    "gemini_get_doc",
}

# Modifying tools that target the filesystem
MUTATING_FILE_TOOLS = {
    "write_to_file",
    "replace_file_content",
    "create_file",
    "delete_file",
    "modify_file",
}


def output_decision(
    decision: str,
    reason: Optional[str] = None,
    reason_code: Optional[str] = None,
    project_root: Optional[str] = None,
    tool_name: Optional[str] = None,
) -> None:
    """Emits JSON decision to stdout and non-blocking telemetry."""
    payload: Dict[str, Any] = {"decision": decision}
    if reason:
        payload["reason"] = reason

    # Attempt non-blocking telemetry emission
    if project_root:
        try:
            emitter.emit_event(
                project_root=project_root,
                event_type="pre_tool_use",
                decision=decision,
                reason_code=reason_code,
                tool_class=tool_name,
            )
        except Exception:
            pass

    print(json.dumps(payload))
    sys.exit(0)


def load_adapter_config(repo_root: str) -> Dict[str, Any]:
    """Loads antios.config.json from repo_root if present."""
    config_path = os.path.join(repo_root, "antios.config.json")
    if os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def extract_target_path(args: Dict[str, Any]) -> Optional[str]:
    """Extracts target path across diverse platform tool schemas."""
    for key in ("TargetFile", "AbsolutePath", "file_path", "path", "target_file", "FilePath"):
        val = args.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def evaluate_pre_tool_use(input_data: Any) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """Evaluates the PreToolUse hook payload.

    Returns:
        (decision, reason, reason_code, resolved_project_root)
    """
    if not isinstance(input_data, dict):
        return "deny", "AntiOS Security Guard: Invalid JSON root type (must be object). Failing closed.", "MALFORMED_INPUT", None

    tool_call = input_data.get("toolCall")
    if not isinstance(tool_call, dict):
        return "deny", "AntiOS Security Guard: Missing or malformed toolCall object. Failing closed.", "MALFORMED_INPUT", None

    tool_name = str(tool_call.get("name", "")).strip()

    # Read-only tools are immediately allowed (NO-OP / NOT APPLICABLE)
    if tool_name in READ_ONLY_TOOLS:
        return "allow", None, None, None

    args = tool_call.get("args")
    if not isinstance(args, dict):
        # Mutating tool with missing args fails closed
        if tool_name in MUTATING_FILE_TOOLS:
            return "deny", "AntiOS Security Guard: Missing or malformed tool args. Failing closed.", "MALFORMED_INPUT", None
        return "allow", None, None, None

    # Extract target path
    target_path = extract_target_path(args)

    # If it's a file mutation tool, target path is mandatory
    if tool_name in MUTATING_FILE_TOOLS and not target_path:
        return "deny", "AntiOS Security Guard: TargetFile must be a non-empty string. Failing closed.", "MALFORMED_INPUT", None

    # If tool is not modifying files and has no file path, allow
    if not target_path:
        return "allow", None, None, None

    # Allow platform conversation artifacts
    norm_target = path_resolver.canonicalize_path(target_path)
    if ".gemini" in norm_target and ("brain" in norm_target or "scratch" in norm_target):
        return "allow", None, None, None
    norm_target = path_resolver.canonicalize_path(target_path)
    if '.gemini' in norm_target and ('brain' in norm_target or 'scratch' in norm_target):
        return 'allow', None, None, None

    # Extract workspacePaths
    workspace_paths = input_data.get("workspacePaths")
    if not workspace_paths or not isinstance(workspace_paths, list) or len(workspace_paths) == 0:
        return "deny", "AntiOS Security Guard: workspacePaths must be a non-empty list. Failing closed.", "MALFORMED_INPUT", None

    # Resolve matching workspace root using longest-prefix matching
    matched_workspace, target_canonical = path_resolver.resolve_matching_workspace(
        target_path=target_path,
        workspace_paths=workspace_paths,
        cwd=os.getcwd(),
    )

    if not matched_workspace:
        # File path is outside all authorized workspace paths
        return (
            "deny",
            f"AntiOS Boundary Policy [PATH_OUTSIDE_WORKSPACE]: Modifying files outside authorized "
            f"workspace roots is strictly forbidden. Target: '{target_path}'. Failing closed.",
            "PATH_OUTSIDE_WORKSPACE",
            None,
        )

    repo_root = matched_workspace

    # Confinement check
    if not path_resolver.is_contained(target_canonical, repo_root):
        return (
            "deny",
            f"AntiOS Boundary Policy [PATH_OUTSIDE_WORKSPACE]: Path escapes workspace repository boundary. Target: '{target_path}'.",
            "PATH_OUTSIDE_WORKSPACE",
            repo_root,
        )

    # Load project adapter config for additional protected zones/domains
    config = load_adapter_config(repo_root)
    configured_zones = config.get("protected_zones", [])
    if not isinstance(configured_zones, list):
        configured_zones = []

    # Immutable Core Zones + Configured Zones
    all_protected_zones = list(dict.fromkeys(IMMUTABLE_CORE_ZONES + configured_zones))

    for zone in all_protected_zones:
        if not zone or not isinstance(zone, str):
            continue
        zone_canonical = path_resolver.canonicalize_path(os.path.join(repo_root, zone))
        if path_resolver.is_contained(target_canonical, zone_canonical):
            return (
                "deny",
                f"AntiOS Self-Protection Policy [PROTECTED_ZONE_VIOLATION]: Modifying AntiOS framework "
                f"governance files, hooks, or configurations ({zone}) is strictly forbidden. "
                f"DO NOT RETRY THIS ACTION.",
                "PROTECTED_ZONE_VIOLATION",
                repo_root,
            )

    # Windows 8.3 short filename alias protection
    rel_path = os.path.relpath(target_canonical, repo_root)
    parts = rel_path.replace("/", "\\").split("\\")

    alias_targets = ["agents", "antios", "framework", ".git"]
    for pz in configured_zones:
        first_segment = str(pz).replace("\\", "/").strip("/").split("/")[0].lower()
        if first_segment and first_segment not in alias_targets:
            alias_targets.append(first_segment)

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
                    f"AntiOS Boundary Policy [ALIAS_BYPASS_ATTEMPT]: 8.3 alias '{part}' targeting "
                    f"protected governance files is strictly forbidden. Failing closed.",
                    "ALIAS_BYPASS_ATTEMPT",
                    repo_root,
                )

    # Protected domain paths from antios.config.json
    protected_domain_paths = config.get("protected_domain_paths", [])
    if isinstance(protected_domain_paths, list):
        for pd in protected_domain_paths:
            if not pd or not isinstance(pd, str):
                continue
            pd_canon = path_resolver.canonicalize_path(os.path.join(repo_root, pd))
            if path_resolver.is_contained(target_canonical, pd_canon):
                return (
                    "deny",
                    f"AntiOS Boundary Policy [PROTECTED_DOMAIN_VIOLATION]: Modifying protected domain path '{pd}' is forbidden.",
                    "PROTECTED_DOMAIN_VIOLATION",
                    repo_root,
                )

    return "allow", None, None, repo_root


def main() -> None:
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            output_decision(
                "deny",
                "AntiOS Security Guard [MALFORMED_INPUT]: Empty hook payload received on stdin. Failing closed.",
                reason_code="MALFORMED_INPUT",
            )

        input_data = json.loads(raw_input)
        tool_name = input_data.get("toolCall", {}).get("name") if isinstance(input_data, dict) else None
        decision, reason, reason_code, repo_root = evaluate_pre_tool_use(input_data)
        output_decision(
            decision=decision,
            reason=reason,
            reason_code=reason_code,
            project_root=repo_root,
            tool_name=tool_name,
        )

    except Exception as e:
        # STRICT FAIL-CLOSED ON ANY UNEXPECTED EXCEPTION
        output_decision(
            "deny",
            f"AntiOS Security Guard internal error [INTERNAL_ERROR]: {str(e)}. Failing closed.",
            reason_code="INTERNAL_ERROR",
        )


if __name__ == "__main__":
    main()

