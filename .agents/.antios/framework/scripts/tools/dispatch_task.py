"""CLI Tool: AntiOS 2.0 Task Dispatch & Mission Orchestration Inspector.

Resolves a task intent query through the full canonical dispatch pipeline:
Task -> Classifier -> Wayfinding -> Capabilities -> Agents -> Orchestrator -> Tools -> Verification.

Usage:
    python framework/scripts/tools/dispatch_task.py "Fix null pointer in payment service"
    python framework/scripts/tools/dispatch_task.py "Add Button padding" --json
    python framework/scripts/tools/dispatch_task.py "Refactor whole auth and database subsystem" --mode PARALLEL
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Ensure repository root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normcase(os.path.abspath(os.path.join(SCRIPT_DIR, "../../..")))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from framework.core.dispatch import TaskDispatchPipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="AntiOS 2.0 Task Dispatch & Mission Orchestration Inspector")
    parser.add_argument("query", help="Task query, issue description, or prompt text")
    parser.add_argument("--target-files", nargs="*", default=[], help="Target files or modules to modify")
    parser.add_argument("--mode", default=None, help="Explicit workforce mode override (SOLO, FOCUSED, PARALLEL, etc.)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")
    parser.add_argument("--streams", type=int, default=1, help="Count of independent implementation streams")
    parser.add_argument("--tightly-coupled", action="store_true", help="Mark streams as tightly coupled")

    args = parser.parse_args()

    pipeline = TaskDispatchPipeline(workspace_root=REPO_ROOT)
    plan = pipeline.dispatch(
        task_query=args.query,
        target_files=args.target_files,
        explicit_mode=args.mode,
        independent_streams=args.streams,
        is_tightly_coupled=args.tightly_coupled,
    )

    if args.json:
        print(json.dumps(plan.to_dict(), indent=2))
        return 0

    print(plan.format_card())
    return 0


if __name__ == "__main__":
    sys.exit(main())
