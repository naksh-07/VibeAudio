"""AntiOS Deterministic Changeset Checker.

Evaluates whether the current git working tree satisfies the Same Change Set
integrity policy (code + tests + docs travel together).

Usage:
    python framework/scripts/tools/check_changeset.py [repo_root]

Outputs structured JSON to stdout. Exits 0 if valid, 1 if violations found.
"""

from __future__ import annotations
import json
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normcase(os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..")))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from framework.core.config import load_config
from framework.core.changeset import evaluate_changeset


def get_changed_files(repo_root: str) -> list:
    """Returns list of changed files from git status --porcelain."""
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
            shell=True if os.name == "nt" else False
        )
        if proc.returncode != 0:
            return []
        files = []
        for line in proc.stdout.splitlines():
            if len(line) > 3:
                files.append(line[3:].strip())
        return files
    except Exception:
        return []


def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    config = load_config(repo)
    changed = get_changed_files(repo)

    result = evaluate_changeset(repo, changed_files=changed, policy=config.changeset)
    output = result.to_dict()
    output["changed_files"] = changed
    output["policy_enabled"] = config.changeset.enabled

    print(json.dumps(output, indent=2))
    sys.exit(0 if result.is_valid else 1)


if __name__ == "__main__":
    main()
