"""AntiOS 2.0 Project Instance Runtime Closure Contract.

Phase 79: Runtime Closure Contract & Verification Engine.

Enforces the constitutional invariant SOURCE ≠ INSTANCE:
- The AntiOS source repository is the compiler and authority.
- The compiled Project Agent OS instance must be independently operational inside
  the target repository without requiring the AntiOS source repository, its framework/,
  tests/, docs/, or development-only assets.
- No installed artifact may import, invoke, or reference absent source paths.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple, Union


# Required artifacts for a completely closed Project Agent OS instance
REQUIRED_INSTANCE_ARTIFACTS: List[str] = [
    ".antios/manifest.json",
    ".antios/project_profile.json",
    ".antios/project_anatomy.json",
    ".antios/knowledge.json",
    ".antios/agent_topology.json",
    ".antios/tool_policy.json",
    ".antios/learning_observations.json",
    ".antios/learning_proposals.json",
    ".antios/runtime/pre_tool_guard.py",
    ".antios/runtime/stop_gate.py",
    ".antios/runtime/inspect_instance.py",
    ".antios/runtime/verify_runtime.py",
    ".agents/skills/antios/SKILL.md",
    ".agents/hooks.json",
    "antios.config.json",
]

# Required runtime scripts in .antios/runtime/
REQUIRED_RUNTIME_SCRIPTS: List[str] = [
    ".antios/runtime/pre_tool_guard.py",
    ".antios/runtime/stop_gate.py",
    ".antios/runtime/inspect_instance.py",
    ".antios/runtime/verify_runtime.py",
]

# Forbidden source leak patterns in compiled target instance artifacts
FORBIDDEN_SOURCE_PATTERNS: List[Tuple[str, str]] = [
    ("framework/scripts/", "Reference to AntiOS source development scripts"),
    ("framework/core/", "Reference to AntiOS source core directory"),
    ("framework.core", "Python import of uninstalled AntiOS framework package"),
    ("../framework/", "Relative path traversal back to AntiOS source repository"),
    ("tests/run_all.py", "Reference to AntiOS source development test harness"),
]


@dataclass
class RuntimeClosureResult:
    """Outcome of verifying Project Instance Runtime Closure."""
    is_closed: bool
    checked_artifacts: List[str] = field(default_factory=list)
    missing_artifacts: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    verified_hooks: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_closed": self.is_closed,
            "checked_artifacts": self.checked_artifacts,
            "missing_artifacts": self.missing_artifacts,
            "violations": self.violations,
            "verified_hooks": self.verified_hooks,
            "summary": self.summary,
        }


def check_ast_for_framework_imports(file_path: Path) -> List[str]:
    """Inspects Python file AST to ensure zero imports from 'framework'."""
    violations: List[str] = []
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "framework" or alias.name.startswith("framework."):
                        violations.append(
                            f"{file_path.name}: Line {node.lineno} imports '{alias.name}' from absent framework package"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module == "framework" or node.module.startswith("framework.")):
                    violations.append(
                        f"{file_path.name}: Line {node.lineno} imports from '{node.module}'"
                    )
    except Exception as e:
        violations.append(f"{file_path.name}: AST parsing error: {e}")
    return violations


def verify_runtime_closure(
    target_root: Union[str, Path],
    execute_guards: bool = False,
) -> RuntimeClosureResult:
    """Verifies that an installed AntiOS instance is 100% self-contained.

    Checks:
    1. All required instance artifacts exist on disk.
    2. All required runtime scripts exist in .antios/runtime/.
    3. Zero forbidden source patterns in instance files.
    4. Zero 'framework' package imports in Python runtime scripts.
    5. .agents/hooks.json commands resolve to existing local scripts.
    6. Target repository does not contain a copied AntiOS framework development tree.
    7. Optionally executes guards in clean subprocess with zero PYTHONPATH.
    """
    root = Path(target_root).resolve()
    checked: List[str] = []
    missing: List[str] = []
    violations: List[str] = []
    verified_hooks: List[str] = []

    # 1. Check required instance artifacts
    for rel_path in REQUIRED_INSTANCE_ARTIFACTS:
        p = root / rel_path
        checked.append(rel_path)
        if not p.is_file():
            missing.append(rel_path)
            violations.append(f"Missing required instance artifact: {rel_path}")

    # 2. Check that target does not contain copied framework/ development directory
    # (unless it was pre-existing target application code)
    if (root / "framework/core").is_dir():
        violations.append(
            "Target repository contains 'framework/core/': AntiOS development source was leaked or copied into instance."
        )

    # 3. Audit .agents/hooks.json
    hooks_file = root / ".agents/hooks.json"
    if hooks_file.is_file():
        try:
            hooks_data = json.loads(hooks_file.read_text(encoding="utf-8"))
            for guard_group, events in hooks_data.items():
                if not isinstance(events, dict):
                    continue
                for event_name, hook_list in events.items():
                    if not isinstance(hook_list, list):
                        continue
                    for hook_entry in hook_list:
                        # Extract command string
                        cmd = hook_entry.get("command", "")
                        if not cmd:
                            hooks_arr = hook_entry.get("hooks", [])
                            for h in hooks_arr:
                                cmd = h.get("command", "")
                                if cmd:
                                    break
                        if cmd:
                            # Verify command does not reference framework/scripts or ../
                            if "framework/scripts" in cmd:
                                violations.append(
                                    f"Hook command leaks source path: '{cmd}'"
                                )
                            if "../" in cmd:
                                violations.append(
                                    f"Hook command contains relative traversal: '{cmd}'"
                                )

                            # Extract referenced script path (e.g. 'python .antios/runtime/pre_tool_guard.py')
                            parts = cmd.split()
                            script_candidates = [p for p in parts if p.endswith(".py")]
                            for sc in script_candidates:
                                script_path = root / sc
                                if not script_path.is_file():
                                    violations.append(
                                        f"Hook command references non-existent script: '{sc}' (resolved to {script_path})"
                                    )
                                else:
                                    verified_hooks.append(f"{event_name} -> {sc}")
        except Exception as e:
            violations.append(f"Failed to parse .agents/hooks.json: {e}")

    # 4. Check for forbidden source patterns in instance files
    scan_targets = list(REQUIRED_INSTANCE_ARTIFACTS)
    for rel_path in scan_targets:
        p = root / rel_path
        if not p.is_file():
            continue
        try:
            content = p.read_text(encoding="utf-8")
            for pattern, reason in FORBIDDEN_SOURCE_PATTERNS:
                # If the target project's own config declares tests/run_all.py, that's allowed in antios.config.json
                if pattern == "tests/run_all.py" and rel_path == "antios.config.json":
                    continue
                # verify_runtime.py implements leak detection itself; its AST is checked below
                if rel_path.endswith("verify_runtime.py"):
                    continue
                if pattern in content:
                    violations.append(
                        f"Forbidden source leak in '{rel_path}': found '{pattern}' ({reason})"
                    )
        except Exception as e:
            violations.append(f"Error reading '{rel_path}' for leak scan: {e}")

    # 5. AST import check for Python runtime scripts
    for rel_path in REQUIRED_RUNTIME_SCRIPTS:
        p = root / rel_path
        if p.is_file():
            ast_issues = check_ast_for_framework_imports(p)
            violations.extend(ast_issues)

    # 6. Physical execution test if requested
    if execute_guards and not violations:
        # Test pre_tool_guard
        guard_script = root / ".antios/runtime/pre_tool_guard.py"
        if guard_script.is_file():
            test_payload = json.dumps({
                "toolCall": {
                    "name": "write_to_file",
                    "args": {"TargetFile": "src/app.py"},
                },
                "workspacePaths": [str(root)],
            })
            clean_env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
            clean_env["PYTHONPATH"] = ""
            try:
                proc = subprocess.run(
                    [sys.executable, str(guard_script)],
                    input=test_payload,
                    capture_output=True,
                    text=True,
                    cwd=str(root),
                    timeout=15,
                    env=clean_env,
                )
                if proc.returncode != 0:
                    violations.append(
                        f"pre_tool_guard execution test failed (exit code {proc.returncode}): {proc.stderr}"
                    )
                else:
                    decision_data = json.loads(proc.stdout.strip())
                    if decision_data.get("decision") not in ("allow", "deny"):
                        violations.append(f"pre_tool_guard emitted invalid decision: {proc.stdout}")
            except Exception as e:
                violations.append(f"Failed to execute pre_tool_guard in isolation: {e}")

    is_closed = len(violations) == 0 and len(missing) == 0
    status_str = "CLOSED" if is_closed else "BROKEN"
    summary = (
        f"Runtime Closure: {status_str} ({len(checked)} artifacts checked, "
        f"{len(missing)} missing, {len(violations)} violations, {len(verified_hooks)} hooks verified)."
    )

    return RuntimeClosureResult(
        is_closed=is_closed,
        checked_artifacts=checked,
        missing_artifacts=missing,
        violations=violations,
        verified_hooks=verified_hooks,
        summary=summary,
    )
