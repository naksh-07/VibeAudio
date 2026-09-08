"""AntiOS 2.0 Project Instance Runtime: Stop Gate Verification Engine.

Phase 80/81: Instance-Local Stop Gate Hook.
Self-contained, zero-external-dependency standard-library script.
Does NOT import or depend on the AntiOS source repository.

Enforces physical process test execution ratchets, working tree cleanliness,
unresolved conflict marker detection, and dynamic project test runner discovery.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


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


def check_working_tree_conflicts(repo_root: str) -> Optional[str]:
    """Scans working tree files for unresolved git merge conflict markers."""
    ignore_dirs = {".git", ".venv", "node_modules", "__pycache__", "dist", "build", ".pytest_cache"}
    conflict_markers = ["<" * 7 + " ", "=" * 7, ">" * 7 + " "]

    try:
        # Check files modified or untracked via git if git is present
        git_proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
            shell=True if os.name == "nt" else False,
        )
        if git_proc.returncode == 0:
            changed_files = []
            for line in git_proc.stdout.splitlines():
                if len(line) > 3:
                    file_path = line[3:].strip()
                    # Strip quotes if git quoted the path
                    if file_path.startswith('"') and file_path.endswith('"'):
                        file_path = file_path[1:-1]
                    changed_files.append(file_path)

            for rel_file in changed_files:
                full_path = os.path.join(repo_root, rel_file)
                if os.path.isfile(full_path):
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            for i, file_line in enumerate(f, 1):
                                for marker in conflict_markers:
                                    if file_line.startswith(marker):
                                        return f"Unresolved conflict marker '{marker.strip()}' in '{rel_file}:{i}'"
                    except Exception:
                        pass
        else:
            for root_dir, dirs, files in os.walk(repo_root):
                dirs[:] = [d for d in dirs if d not in ignore_dirs]
                for fname in files:
                    full_path = os.path.join(root_dir, fname)
                    rel_file = os.path.relpath(full_path, repo_root)
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            for i, file_line in enumerate(f, 1):
                                for marker in conflict_markers:
                                    if file_line.startswith(marker):
                                        return f"Unresolved conflict marker '{marker.strip()}' in '{rel_file}:{i}'"
                    except Exception:
                        pass
    except Exception:
        pass

    return None


def discover_test_runners(repo_root: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Resolves test runners from adapter config or dynamically from project manifests."""
    # 1. Configured runners in antios.config.json
    configured = config.get("test_runners", [])
    if configured:
        return configured

    runners: List[Dict[str, Any]] = []

    # 2. Dynamic discovery: Node.js (package.json)
    pkg_path = os.path.join(repo_root, "package.json")
    if os.path.isfile(pkg_path):
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                pkg_data = json.load(f)
            scripts = pkg_data.get("scripts", {})
            if "test" in scripts:
                runners.append({
                    "name": "npm-test",
                    "default_command": ["npm", "test"],
                    "timeout_seconds": 90,
                    "required": True,
                })
            elif "vitest:once" in scripts:
                runners.append({
                    "name": "vitest",
                    "default_command": ["npm", "run", "vitest:once"],
                    "timeout_seconds": 90,
                    "required": True,
                })
        except Exception:
            pass

    # 3. Dynamic discovery: Python (pyproject.toml, pytest.ini, tests/)
    has_pyproject = os.path.isfile(os.path.join(repo_root, "pyproject.toml"))
    has_pytest_ini = os.path.isfile(os.path.join(repo_root, "pytest.ini"))
    has_tests_dir = os.path.isdir(os.path.join(repo_root, "tests"))

    if has_pyproject or has_pytest_ini or has_tests_dir:
        runners.append({
            "name": "pytest",
            "default_command": ["pytest"],
            "timeout_seconds": 60,
            "required": True,
        })

    # 4. Dynamic discovery: Rust (Cargo.toml)
    if os.path.isfile(os.path.join(repo_root, "Cargo.toml")):
        runners.append({
            "name": "cargo-test",
            "default_command": ["cargo", "test"],
            "timeout_seconds": 120,
            "required": True,
        })

    # 5. Dynamic discovery: Go (go.mod)
    if os.path.isfile(os.path.join(repo_root, "go.mod")):
        runners.append({
            "name": "go-test",
            "default_command": ["go", "test", "./..."],
            "timeout_seconds": 60,
            "required": True,
        })

    return runners


def run_test_runner(runner: Dict[str, Any], repo_root: str) -> Tuple[int, str, str]:
    """Executes a test runner command safely."""
    cmd = runner.get("default_command") or runner.get("command")
    if not cmd:
        return 0, "", ""

    timeout = runner.get("timeout_seconds", 60)
    try:
        proc = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True if os.name == "nt" else False,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        return -1, "", str(e)


def evaluate_stop_gate(input_data: Any) -> Tuple[str, Optional[str]]:
    """Evaluates the Stop hook payload against git cleanliness and physical test passes."""
    workspace_paths = input_data.get("workspacePaths", []) if isinstance(input_data, dict) else []
    if not workspace_paths or not isinstance(workspace_paths, list):
        return "continue", "AntiOS Stop Gate: Missing workspacePaths. Failing closed."

    repo_root = os.path.normcase(os.path.abspath(os.path.realpath(workspace_paths[0])))

    # 1. Inspect working tree conflicts
    conflict_err = check_working_tree_conflicts(repo_root)
    if conflict_err:
        return (
            "continue",
            f"AntiOS Stop Gate Ratchet: {conflict_err}. Resolve merge conflicts before concluding turn."
        )

    # 2. Discover and execute test runners
    config = load_adapter_config(repo_root)
    runners = discover_test_runners(repo_root, config)

    if not runners:
        # No test runners found in project
        return "approve", None

    for runner in runners:
        runner_name = runner.get("name", "unnamed-runner")
        is_required = runner.get("required", True)

        returncode, stdout, stderr = run_test_runner(runner, repo_root)

        if returncode != 0:
            details = (stderr.strip() or stdout.strip() or f"Process exited with code {returncode}")
            # Truncate details if very long
            if len(details) > 800:
                details = details[:800] + "... [truncated]"

            if is_required:
                return (
                    "continue",
                    f"AntiOS Stop Gate Ratchet: Physical test runner '{runner_name}' failed with exit code {returncode}.\n"
                    f"Details:\n{details}\n"
                    f"In accordance with Constitutional Invariant 4, all tests must pass before concluding."
                )

    return "approve", None


def main() -> None:
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            output_decision("continue", "AntiOS Stop Gate: Empty input received on stdin. Failing closed.")
            return

        input_data = json.loads(raw_input)
        decision, reason = evaluate_stop_gate(input_data)
        output_decision(decision, reason)

    except Exception as e:
        # Strict fail-closed on any unhandled exception
        output_decision("continue", f"AntiOS Stop Gate internal error: {str(e)}. Failing closed.")


if __name__ == "__main__":
    main()
