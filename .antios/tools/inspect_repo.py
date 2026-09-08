"""AntiOS Deterministic Repository Inspector.

Inspects a repository for framework integrity, manifest detection,
test runner availability, and governance configuration state.

Usage:
    python framework/scripts/tools/inspect_repo.py [repo_root]

Outputs structured JSON to stdout. Exits 0 on success.
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

from framework.core.adapter import verify_adapter
from framework.core.config import load_config
from framework.core.gate import discover_test_runners
from framework.core.topology import detect_workspace_topology


def inspect_repo(repo_root: str) -> dict:
    """Inspects a repository and returns a structured report."""
    result = {
        "repo_root": repo_root,
        "exists": os.path.isdir(repo_root),
        "is_git_repo": os.path.exists(os.path.join(repo_root, ".git")),
        "has_antios_config": os.path.isfile(os.path.join(repo_root, "antios.config.json")),
        "has_agents_dir": os.path.isdir(os.path.join(repo_root, ".agents")),
        "has_framework_dir": os.path.isdir(os.path.join(repo_root, "framework")),
        "has_hooks_json": os.path.isfile(os.path.join(repo_root, ".agents", "hooks.json")),
        "workspace_topology": "STANDALONE",
        "workspace_members": [],
        "manifests_detected": [],
        "configured_runners": [],
        "discovered_runners": [],
        "adapter_health": None,
        "git_status": "unknown",
    }

    if not result["exists"]:
        return result

    # Check topology
    try:
        topo, members = detect_workspace_topology(repo_root)
        result["workspace_topology"] = topo.value
        result["workspace_members"] = [m.to_dict() for m in members]
    except Exception:
        pass

    # Check manifests
    for m in ["package.json", "pyproject.toml", "Cargo.toml", "go.mod", "pytest.ini", "pnpm-workspace.yaml", "go.work"]:
        if os.path.isfile(os.path.join(repo_root, m)):
            result["manifests_detected"].append(m)

    # Load config and verify adapter
    config = load_config(repo_root)
    result["configured_runners"] = [r.name for r in config.test_runners]
    if result["has_antios_config"]:
        try:
            verif = verify_adapter(repo_root, config, check_fingerprint=False)
            result["adapter_health"] = {
                "is_valid": verif.is_valid,
                "issues": verif.issues,
                "passed_checks": len(verif.passed_checks),
            }
        except Exception as e:
            result["adapter_health"] = {"is_valid": False, "error": str(e)}

    # Discover additional runners
    discovered = discover_test_runners(repo_root)
    result["discovered_runners"] = [r.name for r in discovered]

    # Git status
    if result["is_git_repo"]:
        try:
            proc = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=5,
                shell=True if os.name == "nt" else False
            )
            if proc.returncode == 0:
                lines = [l for l in proc.stdout.splitlines() if l.strip()]
                result["git_status"] = "clean" if len(lines) == 0 else f"dirty ({len(lines)} files)"
        except Exception:
            result["git_status"] = "error"

    return result


def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    report = inspect_repo(repo)
    print(json.dumps(report, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
