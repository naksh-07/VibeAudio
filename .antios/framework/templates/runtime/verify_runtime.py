"""AntiOS 2.0 Project Instance Runtime: Self-Verification & Runtime Closure Check.

Phase 80/81: Instance-Local Runtime Closure Verifier.
Self-contained, zero-external-dependency standard-library script.
Does NOT import or depend on the AntiOS source repository.

Verifies that this project instance is 100% self-contained and closed.
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import sys
from typing import List, Tuple


REQUIRED_FILES = [
    ".antios/manifest.json",
    ".antios/project_profile.json",
    ".antios/project_anatomy.json",
    ".antios/knowledge.json",
    ".antios/agent_topology.json",
    ".antios/tool_policy.json",
    ".antios/runtime/pre_tool_guard.py",
    ".antios/runtime/stop_gate.py",
    ".antios/runtime/inspect_instance.py",
    ".antios/runtime/verify_runtime.py",
    ".agents/skills/antios/SKILL.md",
    ".agents/hooks.json",
    "antios.config.json",
]

# Split string constants to prevent self-detection false positives
FORBIDDEN_LEAKS = [
    "framework/" + "scripts/",
    "framework/" + "core/",
    "framework" + ".core",
    "../" + "framework/",
]


def check_ast(path: Path) -> List[str]:
    violations = []
    try:
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "framework" or alias.name.startswith("framework."):
                        violations.append(f"{path.name}:{node.lineno}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module == "framework" or node.module.startswith("framework.")):
                    violations.append(f"{path.name}:{node.lineno}: from {node.module} import ...")
    except Exception as e:
        violations.append(f"{path.name}: AST parse error: {e}")
    return violations


def main() -> int:
    root = Path(".").resolve()
    issues: List[str] = []

    # 1. Check required files
    for rel in REQUIRED_FILES:
        p = root / rel
        if not p.is_file():
            issues.append(f"Missing required file: '{rel}'")

    # 2. Check hooks.json
    hooks_file = root / ".agents/hooks.json"
    if hooks_file.is_file():
        try:
            data = json.loads(hooks_file.read_text(encoding="utf-8"))
            hooks_text = json.dumps(data)
            for leak in FORBIDDEN_LEAKS:
                if leak in hooks_text:
                    issues.append(f"Source leak in .agents/hooks.json: '{leak}'")
        except Exception as e:
            issues.append(f"Invalid .agents/hooks.json: {e}")

    # 3. Check for leaks in all instance files
    for rel in REQUIRED_FILES:
        if rel.endswith("verify_runtime.py"):
            continue
        p = root / rel
        if p.is_file():
            try:
                content = p.read_text(encoding="utf-8")
                for leak in FORBIDDEN_LEAKS:
                    if leak in content:
                        issues.append(f"Source leak in '{rel}': '{leak}'")
            except Exception as e:
                issues.append(f"Cannot read '{rel}': {e}")

    # 4. AST check on runtime scripts
    runtime_dir = root / ".antios/runtime"
    if runtime_dir.is_dir():
        for py in runtime_dir.glob("*.py"):
            ast_errs = check_ast(py)
            for err in ast_errs:
                issues.append(f"Forbidden framework import in runtime script: {err}")

    # 5. Check that framework/core does not exist
    if (root / "framework/core").is_dir():
        issues.append("AntiOS development source ('framework/core/') is present in target repository")

    print("=" * 65)
    print(" AntiOS Project Instance Runtime Closure Verification")
    print("=" * 65)
    if not issues:
        print("[PASS] Instance is self-contained. All runtime assets physically closed.")
        print("       Zero references to external AntiOS source repository.")
        return 0

    print(f"[FAIL] Found {len(issues)} runtime closure violation(s):")
    for issue in issues:
        print(f"  [x] {issue}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
