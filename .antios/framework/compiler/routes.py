"""
AntiOS 3.0 Project Environment Compiler — Subsystem Route Map Generator

Generates the canonical .agents/routes.json Level 1 Subsystem Route Map.
Connects user intent and high-level questions directly to authoritative implementation code
and proving test suites.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .project_model import Confidence, ProjectModel, SubsystemCandidate, normalize_posix


def _find_authoritative_entrypoint(dir_path: Path, rel_dir: str) -> str:
    """
    Find the authoritative primary entrypoint file for a subsystem directory.
    Prefers domain logic files over generic index/init files where meaningful.
    Disqualifies masking files like version.py, changelog, etc.
    """
    try:
        files = sorted(os.listdir(dir_path))
    except OSError:
        return rel_dir

    disqualified = {"version.py", "changes.md", "changelog.md", "setup.py", "conftest.py"}
    candidates = []

    # Priority candidate stems
    dir_stem = Path(rel_dir).name.lower()
    priority_names = [
        f"{dir_stem}.py",
        "compiler.py",
        "gate.py",
        "service.py",
        "engine.py",
        "client.py",
        "main.py",
        "cli.py",
        "app.py",
        "index.ts",
        "main.rs",
        "mod.rs",
        "lib.rs",
        "main.go",
        "__init__.py",
        "index.js",
    ]

    for p in priority_names:
        if p in files and p.lower() not in disqualified:
            return f"{rel_dir}/{p}"

    # Fallback to any python or source file in directory
    for f in files:
        if f.lower() in disqualified:
            continue
        if f.endswith((".py", ".ts", ".rs", ".go", ".js")):
            return f"{rel_dir}/{f}"

    return rel_dir


def _bind_test_suite(
    repo_root: Path,
    subsystem_name: str,
    entrypoint: str,
    project_model: ProjectModel,
) -> List[str]:
    """
    Deterministically bind proving test suite commands for a subsystem.
    Checks for exact test files matching the subsystem name or entrypoint stem,
    falling back to project-configured test runners or default test conventions.
    """
    entrypoint_stem = Path(entrypoint).stem

    # Possible test file names
    test_candidates = [
        f"tests/test_{subsystem_name}.py",
        f"tests/test_{entrypoint_stem}.py",
        f"test/test_{subsystem_name}.py",
        f"tests/{subsystem_name}_test.py",
        f"tests/{subsystem_name}.test.ts",
        f"tests/{subsystem_name}.spec.ts",
    ]

    for tc in test_candidates:
        if (repo_root / tc).is_file():
            if tc.endswith(".py"):
                return ["python", "-m", "unittest", tc.replace("/", ".").rstrip(".py")]
            elif tc.endswith((".ts", ".js")):
                return ["npm", "test", "--", tc]

    # Check for test directory matching subsystem
    if (repo_root / f"tests/{subsystem_name}").is_dir():
        return ["python", "-m", "unittest", "discover", f"tests/{subsystem_name}"]

    # Fallback to configured test runner from antios.config.json if available
    adapter_file = repo_root / "antios.config.json"
    if adapter_file.is_file():
        try:
            import json

            cfg = json.loads(adapter_file.read_text(encoding="utf-8"))
            if "test_runners" in cfg and isinstance(cfg["test_runners"], list) and cfg["test_runners"]:
                default_cmd = cfg["test_runners"][0].get("default_command")
                if default_cmd and isinstance(default_cmd, list):
                    return [str(c) for c in default_cmd]
        except Exception:
            pass

    # Language-specific default fallbacks
    if "python" in project_model.languages:
        if (repo_root / "tests/run_all.py").is_file():
            return ["python", "tests/run_all.py"]
        return ["python", "-m", "unittest", "discover", "tests"]
    elif "rust" in project_model.languages:
        return ["cargo", "test"]
    elif "go" in project_model.languages:
        return ["go", "test", "./..."]
    elif "typescript" in project_model.languages or "javascript" in project_model.languages:
        return ["npm", "test"]

    return ["python", "tests/run_all.py"]


def _extract_capabilities_and_invariants(
    repo_root: Path,
    entrypoint: str,
) -> tuple[List[str], List[str]]:
    """Extract key capabilities and invariant tags from the entrypoint source."""
    capabilities: List[str] = []
    invariants: List[str] = []
    full_path = repo_root / entrypoint

    if not full_path.is_file():
        return ["execute"], []

    try:
        content = full_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ["execute"], []

    # Invariants (e.g. INV-01, INV-10)
    inv_matches = set(re.findall(r"\b(INV-\d+)\b", content))
    invariants = sorted(inv_matches)

    # Capabilities from top-level defs or methods
    func_matches = re.findall(r"def\s+([a-zA-Z0-9_]+)\s*\(", content)
    meaningful = [
        f for f in func_matches
        if not f.startswith("_") and f not in ("main", "setUp", "tearDown")
    ]

    if meaningful:
        capabilities = sorted(set(meaningful[:6]))
    else:
        # Heuristic fallback based on filename
        stem = Path(entrypoint).stem
        capabilities = [f"run_{stem}"]

    return capabilities, invariants


class RouteMapGenerator:
    """Generates the authoritative subsystem route map from project model and repository structure."""

    def __init__(self, project_model: ProjectModel):
        self.model = project_model
        self.repo_root = Path(project_model.repository_root)

    def generate(self) -> Dict[str, Any]:
        subsystems: Dict[str, SubsystemCandidate] = {}

        # 1. Discover subsystem candidate directories
        candidate_dirs: List[str] = []

        # Check containers: framework/, src/, packages/, apps/, lib/
        containers = ["framework", "src", "packages", "apps", "lib", "pkg"]
        for c in containers:
            c_path = self.repo_root / c
            if c_path.is_dir():
                try:
                    entries = sorted(os.listdir(c_path))
                    for e in entries:
                        sub_path = c_path / e
                        if sub_path.is_dir() and not e.startswith((".", "_")) and e not in ("__pycache__", "node_modules"):
                            candidate_dirs.append(f"{c}/{e}")
                except OSError:
                    pass

        # Also consider top-level package roots if no containers found
        if not candidate_dirs:
            for pr in self.model.package_roots:
                candidate_dirs.append(pr)

        # 2. Build SubsystemCandidate for each directory
        for rel_dir in sorted(set(candidate_dirs)):
            dir_path = self.repo_root / rel_dir
            name = Path(rel_dir).name

            # Skip tests directory itself as a subsystem candidate
            if name in ("tests", "test", "__tests__", "spec", "fixtures"):
                continue

            entrypoint = _find_authoritative_entrypoint(dir_path, rel_dir)
            test_suite = _bind_test_suite(self.repo_root, name, entrypoint, self.model)
            caps, invs = _extract_capabilities_and_invariants(self.repo_root, entrypoint)

            description = f"{name.capitalize()} subsystem implementation and domain logic."
            if "compiler" in name:
                description = "Static project compiler, intelligence extraction, and agent environment generator."
            elif "hook" in name or "gate" in name:
                description = "Platform lifecycle interception hooks and physical validation gates."
            elif "work" in name or "worktree" in name:
                description = "Workspace management, working tree inspection, and isolation."
            elif "core" in name:
                description = "Foundational domain primitives, configuration, and internal utilities."
            elif "cli" in name:
                description = "Command-line interface and command dispatchers."

            candidate = SubsystemCandidate(
                name=name,
                root_dir=rel_dir,
                description=description,
                entrypoint=entrypoint,
                test_suite=test_suite,
                capabilities=caps,
                invariants=invs,
                dependencies=[],
                confidence=Confidence.HIGH,
            )
            subsystems[name] = candidate

        # Store in model
        self.model.subsystem_candidates = subsystems

        # 3. Format into canonical schema
        routes_doc = {
            "$schema": "https://antios.dev/schemas/v3/routes.json",
            "project_id": self.model.project_id,
            "version": "3.0.0",
            "subsystems": {
                name: {
                    "root_dir": candidate.root_dir,
                    "description": candidate.description,
                    "entrypoint": candidate.entrypoint,
                    "test_suite": candidate.test_suite,
                    "capabilities": candidate.capabilities,
                    "invariants": candidate.invariants,
                    "dependencies": candidate.dependencies,
                }
                for name, candidate in sorted(subsystems.items())
            },
        }

        return routes_doc
