"""AntiOS PreToolUse Hook Entrypoint.

Intercepts write_to_file and replace_file_content tool calls.
Delegates evaluation to framework.core.guard with fail-closed guarantee.
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

from framework.core.guard import evaluate_tool_call


def output_decision(decision: str, reason: str = None) -> None:
    payload = {"decision": decision}
    if reason:
        payload["reason"] = reason
    print(json.dumps(payload))
    sys.exit(0)


def main() -> None:
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            output_decision("deny", "AntiOS Security Guard: Empty hook payload received. Failing closed.")

        input_data = json.loads(raw_input)
        decision, reason = evaluate_tool_call(input_data)
        output_decision(decision, reason)

    except Exception as e:
        # STRICT FAIL-CLOSED ON ANY EXCEPTION
        output_decision("deny", f"AntiOS Security Guard internal error: {str(e)}. Failing closed.")


if __name__ == "__main__":
    main()
