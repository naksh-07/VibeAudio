"""AntiOS 3.0 Stop Gate Verification Hook.

Intercepts task conclusion requests (Stop event) to enforce physical process
test execution, working tree cleanliness, 6-dimension MVR verification,
unresolved conflict marker detection (including diff3 base markers),
and multi-workspace repository verification.

Runtime Invariants:
- INV-03: Physical verification required (exit code 0).
- INV-04: Fail-closed boundary enforcement.
- INV-10: 4-Zone ownership boundary (SOURCE != INSTANCE != PROJECT != ANTIGRAVITY).
- INV-11: Zero framework imports (pure stdlib + local hook helpers).
- INV-12: Sanitized telemetry emission.
- INV-15: Zero background daemons (synchronous execution).
- Multi-workspace root support without hardcoded index 0.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# Sibling import bootstrap (zero framework imports)
HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
if HOOK_DIR not in sys.path:
    sys.path.insert(0, HOOK_DIR)

import path_resolver
import emitter

# Conflict markers: standard git (<<<, ===, >>>) and diff3 base (|||)
CONFLICT_MARKERS: List[str] = [
    "<" * 7 + " ",
    "=" * 7,
    ">" * 7 + " ",
    "|" * 7 + " ",
]

MVR_FAIL_FAST_ORDER: List[str] = [
    "lint",
    "typecheck",
    "build",
    "unit_test",
    "integration_test",
    "security_scan",
]


def sanitize_command(cmd: List[str]) -> List[str]:
    """Ensures test commands do not hang in interactive or watch modes."""
    sanitized: List[str] = list(cmd)
    cmd_str = " ".join(cmd).lower()

    # Prevent interactive watch mode for Jest / Vitest / npm
    if "vitest" in cmd_str:
        if "--run" not in sanitized and "--watch=false" not in sanitized:
            sanitized.append("--run")
    elif "jest" in cmd_str:
        if "--watchAll=false" not in sanitized and "--watch=false" not in sanitized:
            sanitized.append("--watchAll=false")
    elif "npm" in cmd_str and "test" in cmd_str:
        if "--" not in sanitized:
            sanitized.extend(["--", "--watchAll=false"])

    # Remove bare --watch or -w flags
    cleaned = []
    for arg in sanitized:
        if arg in ("--watch", "-w"):
            cleaned.append("--watch=false")
        else:
            cleaned.append(arg)

    return cleaned


def output_decision(
    decision: str,
    reason: Optional[str] = None,
    reason_code: Optional[str] = None,
    project_root: Optional[str] = None,
) -> None:
    """Emits JSON decision to stdout and non-blocking telemetry."""
    payload: Dict[str, Any] = {"decision": decision}
    if reason:
        payload["reason"] = reason

    if project_root:
        try:
            emitter.emit_event(
                project_root=project_root,
                event_type="stop",
                decision=decision,
                reason_code=reason_code,
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


def check_working_tree_conflicts(repo_root: str) -> Optional[str]:
    """Scans working tree for unresolved git merge conflict markers.

    Evaluates standard git markers (<, =, >) and diff3 base markers (|||||||).
    """
    ignore_dirs = {".git", ".venv", "node_modules", "__pycache__", "dist", "build", ".pytest_cache"}

    try:
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
                    if " -> " in file_path:
                        file_path = file_path.split(" -> ")[1].strip()
                    if file_path.startswith('"') and file_path.endswith('"'):
                        file_path = file_path[1:-1]
                    changed_files.append(file_path)

            for rel_file in changed_files:
                full_path = os.path.join(repo_root, rel_file)
                if os.path.isfile(full_path):
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            for i, file_line in enumerate(f, 1):
                                for marker in CONFLICT_MARKERS:
                                    if file_line.startswith(marker):
                                        return f"Unresolved conflict marker '{marker.strip()}' in '{rel_file}:{i}'"
                    except Exception:
                        pass
        else:
            for root_dir, dirs, files in os.walk(repo_root):
                dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".agents")]
                for fname in files:
                    full_path = os.path.join(root_dir, fname)
                    rel_file = os.path.relpath(full_path, repo_root)
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            for i, file_line in enumerate(f, 1):
                                for marker in CONFLICT_MARKERS:
                                    if file_line.startswith(marker):
                                        return f"Unresolved conflict marker '{marker.strip()}' in '{rel_file}:{i}'"
                    except Exception:
                        pass
    except Exception:
        pass

    return None


def discover_test_runners(repo_root: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Resolves test runners from adapter config or project manifests.

    Evaluates 6-dimension MVR verification schema in strict fail-fast order:
    1. lint -> 2. typecheck -> 3. build -> 4. unit_test -> 5. integration_test -> 6. security_scan.
    Falls back to legacy test_runners or manifest discovery.
    """
    # 1. 6-Dimension MVR Verification block
    verification = config.get("verification")
    if verification and isinstance(verification, dict):
        mvr_runners: List[Dict[str, Any]] = []
        for dim in MVR_FAIL_FAST_ORDER:
            dim_cfg = verification.get(dim)
            if isinstance(dim_cfg, dict):
                cmd = dim_cfg.get("command")
                if cmd and isinstance(cmd, list) and len(cmd) > 0:
                    mvr_runners.append({
                        "name": dim_cfg.get("name", dim),
                        "dimension": dim,
                        "command": sanitize_command(cmd),
                        "timeout_seconds": dim_cfg.get("timeout_seconds", 60),
                        "required": dim_cfg.get("required", False),
                    })
        if mvr_runners:
            return mvr_runners

    # 2. Configured test_runners block
    configured = config.get("test_runners", [])
    if configured and isinstance(configured, list) and len(configured) > 0:
        sanitized_runners: List[Dict[str, Any]] = []
        for r in configured:
            if isinstance(r, dict):
                rc = dict(r)
                cmd = rc.get("command") or rc.get("default_command")
                if cmd and isinstance(cmd, list):
                    rc["command"] = sanitize_command(cmd)
                    sanitized_runners.append(rc)
        if sanitized_runners:
            return sanitized_runners

    # 3. Dynamic manifest heuristics
    runners: List[Dict[str, Any]] = []

    # AntiOS source self-test harness
    if os.path.isfile(os.path.join(repo_root, "tests", "run_all.py")):
        runners.append({
            "name": "antios-run-all",
            "dimension": "unit_test",
            "command": ["python", "tests/run_all.py"],
            "timeout_seconds": 120,
            "required": True,
        })
        return runners

    # Node.js (package.json)
    pkg_path = os.path.join(repo_root, "package.json")
    if os.path.isfile(pkg_path):
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                pkg_data = json.load(f)
            scripts = pkg_data.get("scripts", {})
            if "vitest:once" in scripts:
                runners.append({
                    "name": "vitest",
                    "dimension": "unit_test",
                    "command": ["npm", "run", "vitest:once"],
                    "timeout_seconds": 90,
                    "required": True,
                })
            elif "test" in scripts:
                runners.append({
                    "name": "npm-test",
                    "dimension": "unit_test",
                    "command": sanitize_command(["npm", "test"]),
                    "timeout_seconds": 90,
                    "required": True,
                })
        except Exception:
            pass

    # Python (pyproject.toml, pytest.ini, tests/)
    has_pyproject = os.path.isfile(os.path.join(repo_root, "pyproject.toml"))
    has_pytest_ini = os.path.isfile(os.path.join(repo_root, "pytest.ini"))
    has_tests_dir = os.path.isdir(os.path.join(repo_root, "tests"))

    if has_pyproject or has_pytest_ini:
        runners.append({
            "name": "pytest",
            "dimension": "unit_test",
            "command": ["pytest"],
            "timeout_seconds": 60,
            "required": False,
        })
    elif has_tests_dir:
        runners.append({
            "name": "unittest",
            "dimension": "unit_test",
            "command": ["python", "-m", "unittest"],
            "timeout_seconds": 60,
            "required": False,
        })

    # Rust (Cargo.toml)
    if os.path.isfile(os.path.join(repo_root, "Cargo.toml")):
        runners.append({
            "name": "cargo-test",
            "dimension": "unit_test",
            "command": ["cargo", "test"],
            "timeout_seconds": 120,
            "required": False,
        })

    # Go (go.mod)
    if os.path.isfile(os.path.join(repo_root, "go.mod")):
        runners.append({
            "name": "go-test",
            "dimension": "unit_test",
            "command": ["go", "test", "./..."],
            "timeout_seconds": 60,
            "required": False,
        })

    return runners


def run_command_safe(
    cmd: List[str], cwd: str, timeout: int = 60
) -> Tuple[int, str, str, bool, float]:
    """Executes verification command safely in subprocess.

    Returns:
        (returncode, stdout, stderr, is_missing, duration_ms)
    """
    t0 = time.perf_counter()
    env = os.environ.copy()
    env["PAGER"] = "cat"
    env["GIT_PAGER"] = "cat"
    env["PYTHONUNBUFFERED"] = "1"

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True if os.name == "nt" else False,
            env=env,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        missing = False

        if os.name == "nt":
            if proc.returncode == 9009 or "is not recognized as an internal or external command" in stderr:
                missing = True
        else:
            if proc.returncode == 127:
                missing = True

        dt_ms = (time.perf_counter() - t0) * 1000.0
        return proc.returncode, stdout, stderr, missing, dt_ms
    except subprocess.TimeoutExpired:
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return -1, "", f"Command timed out after {timeout} seconds", False, dt_ms
    except FileNotFoundError:
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return 127, "", f"Executable '{cmd[0]}' not found", True, dt_ms
    except Exception as e:
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return -1, "", str(e), False, dt_ms


def save_verification_report(repo_root: str, report: Dict[str, Any]) -> None:
    """Atomically caches last verification report to .agents/cache/last_verification_report.json."""
    cache_path = os.path.join(repo_root, ".agents", "cache", "last_verification_report.json")
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        tmp_path = f"{cache_path}.tmp.{os.getpid()}"
        with open(tmp_path, "w", encoding="utf-8") as fp:
            json.dump(report, fp, indent=2)
        if os.name == "nt" and os.path.exists(cache_path):
            os.replace(tmp_path, cache_path)
        else:
            os.replace(tmp_path, cache_path)
    except OSError:
        pass


def evaluate_stop_gate(input_data: Any) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """Evaluates Stop hook payload across all authorized workspaces.

    Enforces 6-dimension MVR fail-fast execution and conflict marker checks.

    Returns:
        (decision, reason, reason_code, primary_project_root)
    """
    if not isinstance(input_data, dict):
        return "continue", "AntiOS Stop Gate [MALFORMED_INPUT]: Invalid JSON root type. Failing closed.", "MALFORMED_INPUT", None

    workspace_paths = input_data.get("workspacePaths")
    canonical_workspaces: List[str] = []

    if isinstance(workspace_paths, list) and len(workspace_paths) > 0:
        for ws in workspace_paths:
            if isinstance(ws, str) and ws.strip():
                c_ws = path_resolver.canonicalize_path(ws)
                if c_ws and os.path.isdir(c_ws) and c_ws not in canonical_workspaces:
                    canonical_workspaces.append(c_ws)

    # Fallback to deterministic discovery if workspacePaths is omitted or empty
    if not canonical_workspaces:
        discovered = path_resolver.discover_project_root(starting_dir=os.getcwd(), script_file=__file__)
        if discovered and os.path.isdir(discovered):
            canonical_workspaces.append(discovered)

    if not canonical_workspaces:
        return "continue", "AntiOS Stop Gate [NO_WORKSPACE]: Unable to resolve repository root. Failing closed.", "NO_WORKSPACE", None

    primary_root = canonical_workspaces[0]

    # Iterate over all workspace roots
    for repo_root in canonical_workspaces:
        # 1. Check working tree conflict markers (standard + diff3)
        conflict_err = check_working_tree_conflicts(repo_root)
        if conflict_err:
            return (
                "continue",
                f"AntiOS Stop Gate [CONFLICT_MARKERS]: Task completion rejected. {conflict_err} in workspace '{repo_root}'.\n"
                f"Resolve all merge conflict markers before completing.",
                "CONFLICT_MARKERS",
                repo_root,
            )

        # 2. Load config and discover test runners (MVR 6-dimension fail-fast)
        config = load_adapter_config(repo_root)
        test_runners = discover_test_runners(repo_root, config)

        report_data: Dict[str, Any] = {
            "timestamp": time.time(),
            "workspace": repo_root,
            "verdict": "pending",
            "executed_runners": [],
        }

        # 3. Execute physical test runners in fail-fast order
        for runner in test_runners:
            cmd = runner.get("command") or runner.get("default_command")
            if not cmd or not isinstance(cmd, list):
                continue

            timeout_sec = runner.get("timeout_seconds", 60)
            runner_name = runner.get("name", "test")
            runner_dim = runner.get("dimension", "unit_test")
            is_required = runner.get("required", False)

            ret, stdout, stderr, is_missing, dt_ms = run_command_safe(cmd, cwd=repo_root, timeout=timeout_sec)

            runner_report = {
                "name": runner_name,
                "dimension": runner_dim,
                "command": cmd,
                "exit_code": ret,
                "latency_ms": round(dt_ms, 2),
                "required": is_required,
            }
            report_data["executed_runners"].append(runner_report)

            if is_missing:
                if is_required:
                    report_data["verdict"] = "continue"
                    save_verification_report(repo_root, report_data)
                    return (
                        "continue",
                        f"AntiOS Stop Gate [MISSING_TEST_RUNNER]: Required test runner '{runner_name}' ({runner_dim}) "
                        f"executable not found in PATH for workspace '{repo_root}'.\n"
                        f"Command: {' '.join(cmd)}\nFailing closed to prevent unverified completion.",
                        "MISSING_TEST_RUNNER",
                        repo_root,
                    )
                continue

            if ret != 0:
                stdout_snip = stdout.strip()[-1000:] if stdout else ""
                stderr_snip = stderr.strip()[-1000:] if stderr else ""
                report_data["verdict"] = "continue"
                save_verification_report(repo_root, report_data)
                return (
                    "continue",
                    f"AntiOS Stop Gate [TEST_FAILURE]: Physical verification failed in workspace '{repo_root}'!\n"
                    f"Dimension: {runner_dim}\n"
                    f"Test Runner: {runner_name}\n"
                    f"Command: {' '.join(cmd)}\nExit Code: {ret}\n"
                    f"Stdout: {stdout_snip}\nStderr: {stderr_snip}",
                    "TEST_FAILURE",
                    repo_root,
                )

        # Record passed report
        report_data["verdict"] = "allow"
        save_verification_report(repo_root, report_data)

    # All checks passed across all workspaces
    return "allow", None, None, primary_root


def main() -> None:
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            output_decision(
                "continue",
                "AntiOS Stop Gate [MALFORMED_INPUT]: Empty input received on stdin. Failing closed.",
                reason_code="MALFORMED_INPUT",
            )

        input_data = json.loads(raw_input)
        decision, reason, reason_code, repo_root = evaluate_stop_gate(input_data)
        output_decision(
            decision=decision,
            reason=reason,
            reason_code=reason_code,
            project_root=repo_root,
        )

    except Exception as e:
        # STRICT FAIL-CLOSED ON ANY EXCEPTION
        output_decision(
            "continue",
            f"AntiOS Stop Gate internal error [INTERNAL_ERROR]: {str(e)}. Failing closed.",
            reason_code="INTERNAL_ERROR",
        )


if __name__ == "__main__":
    main()
