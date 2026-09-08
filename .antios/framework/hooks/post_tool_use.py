"""AntiOS 3.0 PostToolUse Hook.

Fires immediately after tool execution.
Captures observable step execution metadata and emits sanitized telemetry
to .agents/telemetry.ndjson.

Runtime Invariants:
- Platform Contract: Must strictly output `{}` on stdout. Non-empty output fails step.
- INV-10: 4-Zone ownership boundary.
- INV-11: Zero framework imports (pure stdlib + local hook helpers).
- INV-12: Sanitized telemetry emission.
- Non-blocking: Telemetry failure never impedes platform execution.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Optional

# Sibling import bootstrap (zero framework imports)
HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
if HOOK_DIR not in sys.path:
    sys.path.insert(0, HOOK_DIR)

import path_resolver
import emitter


def main() -> None:
    try:
        raw_input = sys.stdin.read()
        input_data = json.loads(raw_input) if raw_input.strip() else {}

        workspace_paths = input_data.get("workspacePaths", [])
        project_root = path_resolver.discover_project_root(
            cwd=os.getcwd(),
            script_file=__file__,
            workspace_paths=workspace_paths if isinstance(workspace_paths, list) else None,
        )

        step_idx = input_data.get("stepIdx")
        error_val = input_data.get("error")

        # Emit non-blocking telemetry event
        try:
            metadata: Dict[str, Any] = {}
            if step_idx is not None:
                metadata["stepIdx"] = step_idx
            if error_val is not None:
                metadata["has_error"] = True

            emitter.emit_event(
                project_root=project_root,
                event_type="post_tool_use",
                payload=metadata,
                decision="completed" if not error_val else "errored",
            )
        except Exception:
            pass

    except Exception:
        pass
    finally:
        # Platform contract: STRICTLY output {} on stdout
        print(json.dumps({}))
        sys.exit(0)


if __name__ == "__main__":
    main()
