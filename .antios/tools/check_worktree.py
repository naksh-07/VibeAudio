"""AntiOS Deterministic Working Tree Inspector.

Captures a snapshot of git working tree state and audits for conflicts,
unexpected dirty state, and conflict markers.

Usage:
    python framework/scripts/tools/check_worktree.py [repo_root]

Outputs structured JSON to stdout. Exits 0 if acceptable, 1 if not.
"""

from __future__ import annotations
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normcase(os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..")))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from framework.core.worktree import (
    audit_worktree,
    inspect_all_conflicts,
    capture_worktree_snapshot,
)


def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

    snapshot = capture_worktree_snapshot(repo)
    conflicts = inspect_all_conflicts(repo)
    audit = audit_worktree(repo)

    output = {
        "repo_root": repo,
        "snapshot": {
            "timestamp": snapshot.timestamp,
            "commit_sha": snapshot.commit_sha,
            "staged_files": snapshot.staged_files,
            "unstaged_files": snapshot.unstaged_files,
            "untracked_files": snapshot.untracked_files,
        },
        "conflicts": conflicts,
        "audit": audit.to_dict(),
    }

    print(json.dumps(output, indent=2))
    sys.exit(0 if audit.is_acceptable else 1)


if __name__ == "__main__":
    main()
