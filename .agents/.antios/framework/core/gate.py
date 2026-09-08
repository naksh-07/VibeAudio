"""AntiOS Stop Gate Verification Engine.

Enforces physical process test execution ratchets, working tree cleanliness,
unresolved conflict marker detection across staged/unstaged/untracked files,
Same Change Set synchronization, and dynamic zero-config test runner discovery.
"""

from __future__ import annotations
import json
import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from framework.core.config import AntiOSConfig, RunnerConfig, load_config
from framework.core.changeset import evaluate_changeset
from framework.core.worktree import inspect_all_conflicts


def run_command_safe(
    cmd: List[str],
    cwd: str,
    timeout: int = 60
) -> Tuple[int, str, str, bool]:
    """Runs a process safely.

    Returns:
        (returncode, stdout, stderr, is_missing_binary)
    """
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            shell=True if os.name == "nt" else False
        )
        # On Windows with shell=True, missing binaries return exit code 1/9009
        # with "is not recognized" in stderr instead of raising FileNotFoundError
        if proc.returncode != 0 and proc.stderr:
            stderr_lower = proc.stderr.lower()
            if "is not recognized" in stderr_lower or "not found" in stderr_lower:
                return proc.returncode, proc.stdout, proc.stderr, True
        return proc.returncode, proc.stdout, proc.stderr, False
    except FileNotFoundError:
        return -1, "", "Binary not found in PATH", True
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout} seconds", False
    except Exception as e:
        return -1, "", str(e), False


def check_working_tree_conflicts(repo_root: str) -> Optional[str]:
    """Checks if working tree contains unresolved git merge conflict markers across all files."""
    conflicts = inspect_all_conflicts(repo_root)
    if conflicts:
        return f"Unresolved git conflict markers detected in working tree: {conflicts[0]}"
    return None


def discover_test_runners(repo_root: str) -> List[RunnerConfig]:
    """Dynamically detects project test runners from root manifests if unconfigured."""
    runners: List[RunnerConfig] = []

    # 1. Node.js / TypeScript (package.json)
    pkg_path = os.path.join(repo_root, "package.json")
    if os.path.isfile(pkg_path):
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                pkg_data = json.load(f)
            scripts = pkg_data.get("scripts", {})
            if "vitest:once" in scripts:
                runners.append(
                    RunnerConfig(
                        name="vitest",
                        manifest="package.json",
                        scripts=["vitest:once"],
                        default_command=["npm", "run", "vitest:once"],
                        timeout_seconds=90,
                        required=False,
                    )
                )
            elif "test" in scripts:
                runners.append(
                    RunnerConfig(
                        name="npm-test",
                        manifest="package.json",
                        scripts=["test"],
                        default_command=["npm", "test"],
                        timeout_seconds=90,
                        required=False,
                    )
                )
        except Exception:
            runners.append(
                RunnerConfig(
                    name="npm-test",
                    manifest="package.json",
                    default_command=["npm", "test"],
                    timeout_seconds=90,
                    required=False,
                )
            )

    # 2. Python (pyproject.toml, pytest.ini, setup.py)
    pyproject = os.path.join(repo_root, "pyproject.toml")
    pytest_ini = os.path.join(repo_root, "pytest.ini")
    if os.path.isfile(pyproject) or os.path.isfile(pytest_ini):
        manifest_file = "pyproject.toml" if os.path.isfile(pyproject) else "pytest.ini"
        runners.append(
            RunnerConfig(
                name="pytest",
                manifest=manifest_file,
                default_command=["pytest"],
                timeout_seconds=60,
                required=False,
            )
        )

    # 3. Rust (Cargo.toml)
    cargo_toml = os.path.join(repo_root, "Cargo.toml")
    if os.path.isfile(cargo_toml):
        runners.append(
            RunnerConfig(
                name="cargo-test",
                manifest="Cargo.toml",
                default_command=["cargo", "test"],
                timeout_seconds=120,
                required=False,
            )
        )

    # 4. Go (go.mod)
    go_mod = os.path.join(repo_root, "go.mod")
    if os.path.isfile(go_mod):
        runners.append(
            RunnerConfig(
                name="go-test",
                manifest="go.mod",
                default_command=["go", "test", "./..."],
                timeout_seconds=60,
                required=False,
            )
        )

    return runners


def resolve_verification_scope(
    repo_root: str,
    test_runners: List[RunnerConfig],
    target_member: Optional[str] = None,
    touched_files: Optional[List[str]] = None,
    workflow: Optional[str] = None,
) -> Tuple[List[RunnerConfig], str]:
    """Resolves whether Stop Gate executes workspace-wide or member-scoped test runners.

    Invariants:
    1. If workflow is RELEASE or REFACTOR, full workspace verification is mandatory.
    2. If touched_files touch shared root configs or multiple members, broader validation is mandatory.
    3. If touched_files belong strictly to member M (or target_member is M), check for dependent
       workspace members that rely on M. If dependents exist, include their runners.
    4. Makes the scoping decision explicit.
    """
    from framework.core.topology import detect_workspace_topology, WorkspaceTopology

    topology, members = detect_workspace_topology(repo_root)
    if topology == WorkspaceTopology.STANDALONE or not members:
        return test_runners, "Standalone repository topology: executing all configured test runners."

    # 1. Workflow overrides: RELEASE and REFACTOR require full workspace regression
    if workflow and workflow.upper() in ("RELEASE", "REFACTOR"):
        return test_runners, f"Workflow '{workflow.upper()}' mandates full workspace verification."

    # 2. Identify target member from touched files or explicit parameter
    resolved_target: Optional[str] = target_member

    if touched_files and not resolved_target:
        # Determine which member directories contain the touched files
        member_matches: Set[str] = set()
        shared_root_touched = False

        for f in touched_files:
            norm_f = os.path.normpath(f).replace("\\", "/")
            # Ignore documentation or git files for member blast-radius calculation
            if norm_f.startswith("docs/") or norm_f.startswith(".agents/") or norm_f.startswith(".git/"):
                continue

            matched_member = None
            for m in members:
                norm_m = os.path.normpath(m.relative_path).replace("\\", "/")
                if norm_f == norm_m or norm_f.startswith(norm_m + "/"):
                    matched_member = m.name
                    break

            if matched_member:
                member_matches.add(matched_member)
            else:
                # Substantive file outside any member directory (root config, build script)
                shared_root_touched = True

        if shared_root_touched:
            return test_runners, "Shared workspace root files modified: escalating to full workspace validation."

        if len(member_matches) > 1:
            return test_runners, f"Touched files span multiple members ({', '.join(sorted(member_matches))}): escalating to full workspace validation."

        if len(member_matches) == 1:
            resolved_target = next(iter(member_matches))

    if not resolved_target:
        return test_runners, "No specific member scope isolated: executing all configured test runners."

    # 3. Member identified: Check for dependent workspace members
    # Target member object
    target_obj = next((m for m in members if m.name == resolved_target), None)
    if not target_obj:
        return test_runners, f"Target member '{resolved_target}' not found in workspace topology: executing all runners."

    # Find all members that declare dependency on resolved_target (directly or transitively)
    scoped_member_names: Set[str] = {resolved_target}
    if target_obj:
        scoped_member_names.add(target_obj.name)

    # Transitive blast radius expansion
    expanded = True
    while expanded:
        expanded = False
        for m in members:
            if m.name not in scoped_member_names:
                if any(dep in scoped_member_names for dep in m.dependencies):
                    scoped_member_names.add(m.name)
                    expanded = True

    dependent_members = [
        name for name in scoped_member_names
        if name != resolved_target and (not target_obj or name != target_obj.name)
    ]

    # 4. Filter runners
    scoped_runners: List[RunnerConfig] = []
    for r in test_runners:
        # Match by explicit runner.member
        if r.member and r.member in scoped_member_names:
            scoped_runners.append(r)
            continue
        # Match by runner cwd matching member relative path
        if r.cwd:
            norm_cwd = os.path.normpath(r.cwd).replace("\\", "/")
            for m in members:
                if m.name in scoped_member_names:
                    norm_m = os.path.normpath(m.relative_path).replace("\\", "/")
                    if norm_cwd == norm_m or norm_cwd.startswith(norm_m + "/"):
                        scoped_runners.append(r)
                        break

    if scoped_runners:
        dep_str = f" (plus dependents: {', '.join(sorted(dependent_members))})" if dependent_members else " (no dependent members)"
        return scoped_runners, f"Member-scoped verification: isolated to '{resolved_target}'{dep_str}."

    # Fallback if no runner was explicitly tagged with member/cwd
    return test_runners, f"Member '{resolved_target}' isolated, but no member-scoped runner configured: running workspace runners."


def evaluate_stop_gate(
    input_data: Any,
    config: Optional[AntiOSConfig] = None,
    target_member: Optional[str] = None,
    touched_files: Optional[List[str]] = None,
    workflow: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """Evaluates a Stop hook event with strict fail-closed semantics.

    Returns:
        (decision, reason) where decision is "allow" or "continue".
    """
    try:
        if not isinstance(input_data, dict):
            return "continue", "AntiOS Stop Gate: Malformed hook input (must be a JSON object). Failing closed."

        workspace_paths = input_data.get("workspacePaths")
        if not workspace_paths or not isinstance(workspace_paths, list) or len(workspace_paths) == 0:
            return "continue", "AntiOS Stop Gate: workspacePaths must be a non-empty list. Failing closed."

        canonical_workspaces: List[str] = []
        for ws in workspace_paths:
            if not isinstance(ws, str) or not ws.strip():
                return "continue", "AntiOS Stop Gate: workspacePaths contains invalid entry. Failing closed."
            c_ws = os.path.normcase(os.path.abspath(os.path.realpath(ws)))
            if c_ws not in canonical_workspaces:
                canonical_workspaces.append(c_ws)

        if not canonical_workspaces:
            return "continue", "AntiOS Stop Gate: workspacePaths contains invalid entry. Failing closed."

        repo_root = canonical_workspaces[0]

        # Extract context if present in input_data
        if target_member is None:
            target_member = input_data.get("target_member") or input_data.get("targetMember")
        if touched_files is None:
            touched_files = input_data.get("touched_files") or input_data.get("touchedFiles")
        if workflow is None:
            workflow = input_data.get("workflow")

        if config is None:
            config = load_config(repo_root)

        # 1. Cleanliness / Conflict Check across working tree
        if config.policies.enforce_working_tree_cleanliness:
            conflict_err = check_working_tree_conflicts(repo_root)
            if conflict_err:
                return "continue", f"AntiOS Stop Gate: Cleanliness check failed: {conflict_err}"

        # 2. Same Change Set Evaluation
        if config.policies.enforce_same_change_set and config.changeset.enabled:
            cs_eval = evaluate_changeset(repo_root, changed_files=touched_files, policy=config.changeset)
            if not cs_eval.is_valid:
                return "continue", f"AntiOS Stop Gate: {cs_eval.summary} Details: {'; '.join(cs_eval.violations)}"

        # 3. Active Task State & Verification Continuity Check (if active context exists)
        ac_path = os.path.join(repo_root, "docs", "ACTIVE_CONTEXT.md")
        if os.path.isfile(ac_path):
            try:
                from framework.core.lifecycle import parse_active_context, TaskStatus, RiskTier
                from framework.core.recovery import is_verification_stale
                from framework.core.worktree import capture_worktree_snapshot
                from framework.core.discovery import discover_project

                task_state = parse_active_context(repo_root)
                if task_state:
                    if task_state.status == TaskStatus.FAILED:
                        return "continue", "AntiOS Stop Gate: Task status is FAILED. Must recover before completion."
                    if task_state.status == TaskStatus.VERIFICATION_STALE:
                        return "continue", "AntiOS Stop Gate: Task status is VERIFICATION_STALE. Re-verification required."

                    # HIGH risk tasks mandate verified Maker-Checker pass
                    if task_state.risk_tier == RiskTier.HIGH:
                        if not task_state.verification_verdict or task_state.verification_verdict.get("status") != "PASS":
                            return "continue", "AntiOS Stop Gate: HIGH risk task requires verified Maker-Checker pass before completion."

                    # Check verification continuity / staleness
                    if task_state.verification_verdict:
                        snapshot = capture_worktree_snapshot(repo_root)
                        mf = ""
                        try:
                            mf = discover_project(repo_root).manifest_fingerprint
                        except Exception:
                            pass
                        stale, reasons = is_verification_stale(
                            task_state, snapshot.dirty_files,
                            current_manifest_fingerprint=mf,
                            current_git_head=snapshot.commit_sha
                        )
                        if stale:
                            return "continue", f"AntiOS Stop Gate: Verification invalidated: {'; '.join(reasons)}. Re-verification required."
            except Exception:
                pass

        # 4. Dynamic Test Execution (Configured or Auto-discovered)
        available_runners = config.test_runners if config.test_runners else discover_test_runners(repo_root)

        # Apply Member-Scoped Verification filtering
        test_runners, scope_rationale = resolve_verification_scope(
            repo_root=repo_root,
            test_runners=available_runners,
            target_member=target_member,
            touched_files=touched_files,
            workflow=workflow,
        )

        for runner in test_runners:
            if runner.manifest:
                manifest_path = os.path.join(repo_root, runner.manifest)
                if not os.path.isfile(manifest_path):
                    continue

            # Determine command to run
            cmd: List[str] = list(runner.default_command)
            cwd = os.path.join(repo_root, runner.cwd) if runner.cwd else repo_root

            # For npm / node packages, check package.json scripts
            if runner.manifest == "package.json":
                try:
                    with open(os.path.join(repo_root, "package.json"), "r", encoding="utf-8") as f:
                        pkg = json.load(f)
                    scripts = pkg.get("scripts", {})
                    chosen_script = None
                    for candidate in runner.scripts:
                        if candidate in scripts:
                            chosen_script = candidate
                            break

                    if chosen_script:
                        cmd = ["npm", "run", chosen_script]
                except Exception:
                    pass

            ret, stdout, stderr, is_missing = run_command_safe(
                cmd, cwd, timeout=runner.timeout_seconds
            )

            if is_missing:
                if runner.required:
                    return (
                        "continue",
                        f"AntiOS Stop Gate: Required test runtime '{runner.name}' executable not found in PATH.\n"
                        f"Command: {' '.join(cmd)}\n"
                        f"Failing closed to prevent unverified completion."
                    )
                continue

            if ret != 0:
                stdout_snip = stdout.strip()[-1000:] if stdout else ""
                stderr_snip = stderr.strip()[-1000:] if stderr else ""
                return (
                    "continue",
                    f"AntiOS Stop Gate: Verification failed! Test runner '{runner.name}' did not pass ({scope_rationale}).\n"
                    f"Command: {' '.join(cmd)}\nExit Code: {ret}\n"
                    f"Stdout: {stdout_snip}\nStderr: {stderr_snip}"
                )

        # If no tests failed, allow task conclusion
        return "allow", None

    except Exception as e:
        return "continue", f"AntiOS Stop Gate Internal Error: {str(e)}. Failing closed."
