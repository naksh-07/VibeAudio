"""AntiOS Telemetry Hook Entrypoint (Phase 105).

Non-blocking lifecycle hook receiving Antigravity hook payloads on stdin.
Evaluates TelemetryBridge and returns immediately.
Telemetry failures never fail or block the host engineering task.
"""

from __future__ import annotations
import json
import os
import sys

# Ensure repository root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normcase(os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..")))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from framework.core.telemetry_bridge import AntigravityEventBridge


def main() -> None:
    try:
        raw_input = sys.stdin.read()
        if raw_input.strip():
            payload = json.loads(raw_input)
            bridge = AntigravityEventBridge(project_root=REPO_ROOT)
            if bridge.is_enabled():
                bridge.ingest_from_hook_payload(payload=payload, hook_type="PostToolUse")
    except Exception:
        # Non-blocking: Telemetry failure != task failure
        pass
    finally:
        # PostToolUse hooks require empty JSON object on stdout
        print(json.dumps({}))
        sys.exit(0)


if __name__ == "__main__":
    main()
