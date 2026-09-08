"""AntiOS 2.0 Project Instance Runtime: PreToolUse Security Guard.

Phase 80/81: Instance-Local PreToolUse Guard Hook.
Self-contained, zero-external-dependency standard-library script.
Does NOT import or depend on the AntiOS source repository.

Enforces deterministic boundary protection, framework self-protection,
path canonicalization, and workspace boundary confinement with strict fail-closed semantics.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple


# Immutable Core Zones that CANNOT be modified via IDE tool calls
IMMUTABLE_CORE_ZONES: List[str] = [
    ".agents",
    ".antios",
    "antios.config.json",
    ".git",
]


def output_decision(decision: str, reason: Optional[str] = None) -> None:
    """Outputs structured JSON decision to stdout and exits cleanly."""
    payload = {"decision": decision}
    if reason:
        payload["reason"] = reason
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


def evaluate_payload(input_data: Any) -> Tuple[str, Optional[str]]:
    """Evaluates the Antigravity PreToolUse hook payload."""
    if not isinstance(input_data, dict):
        return "deny", "AntiOS Security Guard: Invalid JSON root type (must be object). Failing closed."

    tool_call = input_data.get("toolCall")
    if not isinstance(tool_call, dict):
        return "deny", "AntiOS Security Guard: Missing or malformed toolCall object. Failing closed."

    args = tool_call.get("args")
    if not isinstance(args, dict):
        return "deny", "AntiOS Security Guard: Missing or malformed tool args. Failing closed."

    target_file = args.get("TargetFile")
    if not target_file or not isinstance(target_file, str):
        return "deny", "AntiOS Security Guard: TargetFile must be a non-empty string. Failing closed."

    workspace_paths = input_data.get("workspacePaths")
    if not workspace_paths or not isinstance(workspace_paths, list) or len(workspace_paths) == 0:
        return "deny", "AntiOS Security Guard: workspacePaths must be a non-empty list. Failing closed."

    first_workspace = workspace_paths[0]
    if not isinstance(first_workspace, str) or not first_workspace.strip():
        return "deny", "AntiOS Security Guard: workspacePaths contains invalid entry. Failing closed."

    repo_root = os.path.normcase(os.path.abspath(os.path.realpath(first_workspace)))

    # Canonicalize TargetFile anchored strictly to workspace root
    if not os.path.isabs(target_file):
        target_abs = os.path.abspath(os.path.join(repo_root, target_file))
    else:
        target_abs = os.path.abspath(target_file)
    target_resolved = os.path.normcase(os.path.realpath(target_abs))

    # Confinement Check: TargetFile must reside within repo_root
    try:
        if os.path.commonpath([target_resolved, repo_root]) != repo_root:
            return (
                "deny",
                f"AntiOS Boundary Policy: Modifying files outside the workspace repository ({repo_root}) "
                f"is strictly forbidden. Target: '{target_file}'. Failing closed."
            )
    except ValueError:
        return (
            "deny",
            f"AntiOS Boundary Policy: Cross-drive paths outside workspace repository are forbidden. Target: '{target_file}'. Failing closed."
        )

    # Load adapter configuration
    config = load_adapter_config(repo_root)
    configured_zones = config.get("protected_zones", [])
    configured_domain_paths = config.get("protected_domain_paths", [])

    all_protected = list(dict.fromkeys(IMMUTABLE_CORE_ZONES + configured_zones + configured_domain_paths))

    # Check against protected zones
    for zone in all_protected:
        zone_clean = zone.replace("\\", "/").strip("/")
        if not zone_clean:
            continue
        zone_abs = os.path.normcase(os.path.abspath(os.path.join(repo_root, zone_clean)))
        # File match
        if os.path.isfile(zone_abs) and target_resolved == zone_abs:
            return (
                "deny",
                f"AntiOS Self-Protection Policy: Direct tool modifications to protected file '{zone_clean}' "
                f"are strictly forbidden. Failing closed."
            )
        # Directory prefix match
        try:
            if os.path.commonpath([target_resolved, zone_abs]) == zone_abs:
                return (
                    "deny",
                    f"AntiOS Self-Protection Policy: Direct tool modifications within protected zone '{zone_clean}' "
                    f"are strictly forbidden. Failing closed."
                )
        except ValueError:
            pass

    # Windows 8.3 Short-name bypass mitigation
    target_lower = target_file.lower().replace("\\", "/")
    if "~" in target_lower:
        segments = target_lower.split("/")
        for seg in segments:
            for forbidden in [".agents", ".antios", "antios.config"]:
                clean_f = forbidden.lstrip(".")
                prefix = clean_f[:5]
                if seg.startswith(prefix) and "~" in seg:
                    return (
                        "deny",
                        f"AntiOS Boundary Policy: Short-name (8.3) alias match '{seg}' targeting protected '{forbidden}' "
                        f"is strictly forbidden. Failing closed."
                    )

    return "allow", None


def main() -> None:
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            output_decision("deny", "AntiOS Security Guard: Empty hook payload received. Failing closed.")
            return

        input_data = json.loads(raw_input)
        decision, reason = evaluate_payload(input_data)
        output_decision(decision, reason)

    except Exception as e:
        # Strict fail-closed on any unhandled exception
        output_decision("deny", f"AntiOS Security Guard internal error: {str(e)}. Failing closed.")


if __name__ == "__main__":
    main()
