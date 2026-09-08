"""AntiOS v1 Project Discovery & Intelligence Engine.

This module provides deterministic, read-only, zero-code-execution inspection
of unfamiliar repositories across multiple ecosystems:
- Python (pyproject.toml, setup.py, requirements, uv/poetry/pipenv lockfiles)
- TypeScript / JavaScript (package.json, pnpm/yarn/npm/bun lockfiles, tsconfig, vitest, jest, eslint)
- Go (go.mod, go.sum, *_test.go, golangci-lint)
- Rust (Cargo.toml, Cargo.lock, src/lib.rs, tests/, clippy)

Strictly respects the AntiOS Single Authority Law:
Physical Manifests & Git State > CI Automation > Passive Markdown Guidance.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import tomllib  # Python 3.11+ stdlib
except ImportError:
    tomllib = None  # Fallback handled via regex

from framework.core.topology import (
    WorkspaceMember,
    WorkspaceTopology,
    detect_workspace_topology,
    safe_read_json,
)

from framework.core.profile import (
    ConfidenceLevel,
    ConflictFact,
    ConflictType,
    EvidenceFact,
    EvidenceTier,
    GuidanceFact,
    InferredFact,
    ProjectIdentity,
    ProjectProfile,
    ToolCategory,
    ToolFact,
    UnknownFact,
)

IMMUTABLE_CORE_ZONES = [".agents", "framework", "antios.config.json", ".git"]


def is_tool_in_path(cmd_name: str) -> bool:
    """Check if an executable binary is present in host PATH."""
    return shutil.which(cmd_name) is not None


def safe_read_text(path: Path, max_bytes: int = 250_000) -> str:
    """Read file content safely with size limits to avoid unbounded memory."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(max_bytes)
    except Exception:
        return ""


def parse_simple_toml(content: str) -> Dict[str, Any]:
    """Parse TOML content safely via tomllib if available, or lightweight regex fallback."""
    if tomllib is not None:
        try:
            return tomllib.loads(content)
        except Exception:
            pass
    # Basic fallback for key sections if tomllib fails or unavailable
    result: Dict[str, Any] = {}
    current_section = ""
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        sec_match = re.match(r"^\[(.*)\]$", line)
        if sec_match:
            current_section = sec_match.group(1).strip()
            result.setdefault(current_section, {})
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("\"'")
            if current_section:
                result.setdefault(current_section, {})[k] = v
            else:
                result[k] = v
    return result


class ProjectDiscoveryEngine:
    """Zero-dependency, read-only project intelligence discovery engine."""

    def __init__(
        self,
        repo_root: str,
        topology: Optional[WorkspaceTopology] = None,
        members: Optional[List[WorkspaceMember]] = None,
    ):
        self.repo_root = Path(os.path.normcase(os.path.abspath(repo_root)))
        if topology is not None:
            self.topology = topology
            self.workspace_members = members if members is not None else []
        else:
            self.topology, self.workspace_members = detect_workspace_topology(str(self.repo_root))

        self.observed: List[EvidenceFact] = []
        self.inferred: List[InferredFact] = []
        self.unknowns: List[UnknownFact] = []
        self.tools: List[ToolFact] = []
        self.guidance: List[GuidanceFact] = []
        self.conflicts: List[ConflictFact] = []
        self.languages: Set[str] = set()
        self.frameworks: Set[str] = set()
        self.package_managers: Set[str] = set()
        self.build_systems: Set[str] = set()
        self.protected_paths: Set[str] = set()
        self.forbidden_patterns: Set[str] = set()
        self.risk_zones: Set[str] = set()
        self.subsystems: Dict[str, Dict[str, Any]] = {}

    def discover(self) -> ProjectProfile:
        """Execute full read-only discovery and return a canonical ProjectProfile."""
        repo_name = self.repo_root.name or "unknown-project"
        is_git = (self.repo_root / ".git").is_dir()
        head_commit = None

        if is_git:
            head_file = self.repo_root / ".git" / "HEAD"
            if head_file.exists():
                head_ref = safe_read_text(head_file).strip()
                if head_ref.startswith("ref:"):
                    ref_path = self.repo_root / ".git" / head_ref.split(":", 1)[1].strip()
                    if ref_path.exists():
                        head_commit = safe_read_text(ref_path).strip()[:10]
                elif len(head_ref) >= 7:
                    head_commit = head_ref[:10]
            self.observed.append(
                EvidenceFact(
                    path=".git",
                    selector="directory",
                    value="present",
                    witness_type="FILE_EXISTENCE",
                    description="Repository is git version controlled",
                )
            )
        else:
            self.unknowns.append(
                UnknownFact(
                    field_name="git_repository",
                    reason="Directory has no .git folder",
                    required_action="Initialize git repository for complete change tracking",
                    is_blocking=False,
                )
            )

        # Workspace topology integration
        if self.topology and self.topology != WorkspaceTopology.STANDALONE:
            self._record_workspace_facts()
            self._discover_member_tools()

        # 1. Multi-ecosystem manifest discovery
        self._discover_python()
        self._discover_typescript_javascript()
        self._discover_go()
        self._discover_rust()

        # 2. Existing guidance static discovery
        self._discover_guidance()

        # 3. Detect conflicts between guidance, manifests, CI, and AntiOS Core
        self._detect_conflicts()

        # 4. Synthesize unknowns if no recognized languages found
        if not self.languages and not self.workspace_members:
            self.unknowns.append(
                UnknownFact(
                    field_name="project_language",
                    reason="No recognized language manifests or source code files detected",
                    required_action="Provide language configuration or add package manifest",
                    is_blocking=True,
                )
            )

        # 5. Discover project subsystems & components for wayfinding
        self._discover_subsystems()

        # Compute deterministic manifest_fingerprint
        manifest_fingerprint = self._compute_manifest_fingerprint()

        # 6. Assemble and return canonical ProjectProfile
        identity = ProjectIdentity(
            name=repo_name,
            root_path=str(self.repo_root),
            is_git_repo=is_git,
            head_commit=head_commit,
            languages=sorted(list(self.languages)),
            frameworks=sorted(list(self.frameworks)),
            package_managers=sorted(list(self.package_managers)),
            build_systems=sorted(list(self.build_systems)),
        )

        return ProjectProfile(
            identity=identity,
            observed_facts=self.observed,
            inferred_facts=self.inferred,
            unknown_fields=self.unknowns,
            tools=self.tools,
            guidance=self.guidance,
            conflicts=self.conflicts,
            risk_zones=sorted(list(self.risk_zones)),
            protected_paths=sorted(list(self.protected_paths)),
            forbidden_patterns=sorted(list(self.forbidden_patterns)),
            topology=self.topology or WorkspaceTopology.STANDALONE,
            workspace_members=self.workspace_members,
            manifest_fingerprint=manifest_fingerprint,
            subsystems=self.subsystems,
        )

    def _record_workspace_facts(self) -> None:
        """Record observed and inferred facts regarding workspace topology."""
        manifest_path = "workspace"
        if (self.repo_root / "pnpm-workspace.yaml").is_file():
            manifest_path = "pnpm-workspace.yaml"
        elif (self.repo_root / "pnpm-workspace.yml").is_file():
            manifest_path = "pnpm-workspace.yml"
        elif (self.repo_root / "go.work").is_file():
            manifest_path = "go.work"
        elif (self.repo_root / "Cargo.toml").is_file() and "[workspace]" in safe_read_text(self.repo_root / "Cargo.toml"):
            manifest_path = "Cargo.toml"
        elif (self.repo_root / "package.json").is_file() and "workspaces" in safe_read_json(self.repo_root / "package.json"):
            manifest_path = "package.json"
        elif (self.repo_root / "pyproject.toml").is_file() and "[tool.uv.workspace]" in safe_read_text(self.repo_root / "pyproject.toml"):
            manifest_path = "pyproject.toml"

        self.observed.append(
            EvidenceFact(
                path=manifest_path,
                selector="workspace",
                value=self.topology.value,
                witness_type="FILE_CONTENT",
                description=f"Workspace topology '{self.topology.value}' with {len(self.workspace_members)} members",
            )
        )
        self.inferred.append(
            InferredFact(
                hypothesis=f"Project is structured as {self.topology.value}",
                confidence=1.0,
                rationale=f"Detected workspace topology with {len(self.workspace_members)} members",
                underlying_evidence=[m.manifest_path for m in self.workspace_members],
            )
        )

    def _discover_member_tools(self) -> None:
        """Discover member-specific tools and attach them with cwd=member.relative_path."""
        for member in self.workspace_members:
            member_dir = self.repo_root / member.relative_path

            if member.package_type == "typescript":
                self.languages.add("TypeScript / JavaScript")
                member_pkg = member_dir / "package.json"
                pkg_data = safe_read_json(member_pkg) if member_pkg.is_file() else {}
                scripts = pkg_data.get("scripts", {})

                pkg_mgr = "pnpm" if (self.repo_root / "pnpm-workspace.yaml").is_file() or (self.repo_root / "pnpm-lock.yaml").is_file() else "npm"
                self.package_managers.add(pkg_mgr)

                # Test runner
                for cand in ["test:ci", "vitest:once", "test:once", "test:unit", "test"]:
                    if cand in scripts:
                        s_val = scripts[cand]
                        cmd = [pkg_mgr, "run", cand] if pkg_mgr != "npm" or cand != "test" else ["npm", "test"]
                        flags: List[str] = []
                        if "vitest" in s_val and "--run" not in s_val:
                            flags.append("--run")
                        elif "jest" in s_val and "--watchAll=false" not in s_val:
                            flags.append("--watchAll=false")

                        tool = ToolFact(
                            name=f"{member.name}-test-runner",
                            category=ToolCategory.TEST_RUNNER,
                            manifest_path=member.manifest_path,
                            command=cmd,
                            timeout_seconds=90,
                            required=True,
                            cwd=member.relative_path,
                            is_available_in_path=is_tool_in_path(pkg_mgr),
                            non_interactive_flags=flags,
                        )
                        member.tools.append(tool)
                        self.tools.append(tool)
                        break

                # Linter
                for cand in ["lint:check", "lint", "eslint"]:
                    if cand in scripts:
                        tool = ToolFact(
                            name=f"{member.name}-linter",
                            category=ToolCategory.LINTER,
                            manifest_path=member.manifest_path,
                            command=[pkg_mgr, "run", cand],
                            timeout_seconds=60,
                            required=False,
                            cwd=member.relative_path,
                            is_available_in_path=is_tool_in_path(pkg_mgr),
                        )
                        member.tools.append(tool)
                        self.tools.append(tool)
                        break

            elif member.package_type == "rust":
                self.languages.add("Rust")
                self.build_systems.add("cargo")
                test_tool = ToolFact(
                    name=f"{member.name}-cargo-test",
                    category=ToolCategory.TEST_RUNNER,
                    manifest_path=member.manifest_path,
                    command=["cargo", "test", "-p", member.name, "--no-fail-fast"],
                    timeout_seconds=120,
                    required=True,
                    cwd=member.relative_path,
                    is_available_in_path=is_tool_in_path("cargo"),
                    non_interactive_flags=["--no-fail-fast"],
                )
                member.tools.append(test_tool)
                self.tools.append(test_tool)

                clippy_tool = ToolFact(
                    name=f"{member.name}-cargo-clippy",
                    category=ToolCategory.LINTER,
                    manifest_path=member.manifest_path,
                    command=["cargo", "clippy", "-p", member.name, "--", "-D", "warnings"],
                    timeout_seconds=60,
                    required=False,
                    cwd=member.relative_path,
                    is_available_in_path=is_tool_in_path("cargo"),
                    non_interactive_flags=["--", "-D", "warnings"],
                )
                member.tools.append(clippy_tool)
                self.tools.append(clippy_tool)

            elif member.package_type == "go":
                self.languages.add("Go")
                self.build_systems.add("go")
                test_tool = ToolFact(
                    name=f"{member.name}-go-test",
                    category=ToolCategory.TEST_RUNNER,
                    manifest_path=member.manifest_path,
                    command=["go", "test", "-v", "./..."],
                    timeout_seconds=90,
                    required=True,
                    cwd=member.relative_path,
                    is_available_in_path=is_tool_in_path("go"),
                    non_interactive_flags=["-v"],
                )
                member.tools.append(test_tool)
                self.tools.append(test_tool)

                if (member_dir / ".golangci.yml").is_file() or (self.repo_root / ".golangci.yml").is_file():
                    lint_tool = ToolFact(
                        name=f"{member.name}-golangci-lint",
                        category=ToolCategory.LINTER,
                        manifest_path=member.manifest_path,
                        command=["golangci-lint", "run"],
                        timeout_seconds=60,
                        required=False,
                        cwd=member.relative_path,
                        is_available_in_path=is_tool_in_path("golangci-lint"),
                    )
                    member.tools.append(lint_tool)
                    self.tools.append(lint_tool)

            elif member.package_type == "python":
                self.languages.add("Python")
                self.build_systems.add("python")
                test_tool = ToolFact(
                    name=f"{member.name}-pytest",
                    category=ToolCategory.TEST_RUNNER,
                    manifest_path=member.manifest_path,
                    command=["pytest", "-o", "console_output_style=classic", "--capture=no"],
                    timeout_seconds=90,
                    required=True,
                    cwd=member.relative_path,
                    is_available_in_path=is_tool_in_path("pytest"),
                    non_interactive_flags=["-o", "console_output_style=classic", "--capture=no"],
                )
                member.tools.append(test_tool)
                self.tools.append(test_tool)

                lint_tool = ToolFact(
                    name=f"{member.name}-ruff-check",
                    category=ToolCategory.LINTER,
                    manifest_path=member.manifest_path,
                    command=["ruff", "check", "."],
                    timeout_seconds=30,
                    required=False,
                    cwd=member.relative_path,
                    is_available_in_path=is_tool_in_path("ruff"),
                )
                member.tools.append(lint_tool)
                self.tools.append(lint_tool)

    def _compute_manifest_fingerprint(self) -> str:
        """Compute deterministic SHA-256 hash of all discovered manifest file contents."""
        candidate_paths: Set[str] = set()

        for member in self.workspace_members:
            if member.manifest_path:
                candidate_paths.add(member.manifest_path.replace("\\", "/"))

        manifest_extensions = (
            ".json", ".toml", ".yaml", ".yml", ".mod", ".work",
            ".sum", ".lock", ".lockb", ".ini", ".cfg", ".txt",
        )
        for fact in self.observed:
            p = fact.path.replace("\\", "/")
            if any(p.endswith(ext) for ext in manifest_extensions):
                candidate_paths.add(p)

        known_root_manifests = [
            "pnpm-workspace.yaml", "pnpm-workspace.yml", "package.json",
            "pnpm-lock.yaml", "package-lock.json", "yarn.lock", "bun.lockb",
            "Cargo.toml", "Cargo.lock",
            "go.work", "go.work.sum", "go.mod", "go.sum",
            "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
            "uv.lock", "poetry.lock", "Pipfile.lock", "pytest.ini", "ruff.toml",
            "tsconfig.json", "golangci.yml", ".golangci.yml"
        ]
        for km in known_root_manifests:
            if (self.repo_root / km).is_file():
                candidate_paths.add(km)

        valid_manifests: List[Tuple[str, Path]] = []
        for rel in sorted(candidate_paths):
            target = self.repo_root / rel
            if target.is_file():
                valid_manifests.append((rel, target))

        if not valid_manifests:
            return ""

        hasher = hashlib.sha256()
        for rel_name, full_path in valid_manifests:
            hasher.update(rel_name.encode("utf-8"))
            try:
                with open(full_path, "rb") as f:
                    hasher.update(f.read())
            except Exception:
                pass

        return hasher.hexdigest()


    # -------------------------------------------------------------------------
    # Python Ecosystem
    # -------------------------------------------------------------------------
    def _discover_python(self) -> None:
        pyproject_path = self.repo_root / "pyproject.toml"
        setup_py_path = self.repo_root / "setup.py"
        setup_cfg_path = self.repo_root / "setup.cfg"
        reqs_path = self.repo_root / "requirements.txt"
        uv_lock = self.repo_root / "uv.lock"
        poetry_lock = self.repo_root / "poetry.lock"
        pipfile_lock = self.repo_root / "Pipfile.lock"
        pytest_ini = self.repo_root / "pytest.ini"
        ruff_toml = self.repo_root / "ruff.toml"

        is_python = any([
            pyproject_path.exists(),
            setup_py_path.exists(),
            setup_cfg_path.exists(),
            reqs_path.exists(),
            uv_lock.exists(),
            poetry_lock.exists(),
            pytest_ini.exists(),
            any(self.repo_root.glob("*.py")),
        ])

        if not is_python:
            return

        self.languages.add("Python")
        pkg_prefix: List[str] = []

        if uv_lock.exists():
            self.package_managers.add("uv")
            self.observed.append(EvidenceFact("uv.lock", "file", "present", "FILE_EXISTENCE", "Astral uv lockfile"))
            pkg_prefix = ["uv", "run"]
        elif poetry_lock.exists():
            self.package_managers.add("poetry")
            self.observed.append(EvidenceFact("poetry.lock", "file", "present", "FILE_EXISTENCE", "Poetry lockfile"))
            pkg_prefix = ["poetry", "run"]
        elif pipfile_lock.exists():
            self.package_managers.add("pipenv")
            self.observed.append(EvidenceFact("Pipfile.lock", "file", "present", "FILE_EXISTENCE", "Pipenv lockfile"))
            pkg_prefix = ["pipenv", "run"]
        elif reqs_path.exists():
            self.package_managers.add("pip")
            self.observed.append(EvidenceFact("requirements.txt", "file", "present", "FILE_EXISTENCE", "pip requirements file"))

        # Inspect pyproject.toml
        has_pytest = pytest_ini.exists()
        has_ruff = ruff_toml.exists()
        has_mypy = (self.repo_root / "mypy.ini").exists()

        if pyproject_path.exists():
            content = safe_read_text(pyproject_path)
            data = parse_simple_toml(content)
            self.observed.append(EvidenceFact("pyproject.toml", "file", "present", "FILE_EXISTENCE", "Python PEP 518/621 project manifest"))
            
            # Framework hints
            content_lower = content.lower()
            if "fastapi" in content_lower:
                self.frameworks.add("FastAPI")
            if "django" in content_lower:
                self.frameworks.add("Django")
            if "flask" in content_lower:
                self.frameworks.add("Flask")

            # Test runner
            if "pytest" in content_lower or "tool.pytest" in content:
                has_pytest = True
                self.observed.append(EvidenceFact("pyproject.toml", "[tool.pytest]", "configured", "FILE_CONTENT", "pytest configuration found in pyproject.toml"))

            # Linter / Formatter
            if "ruff" in content_lower or "tool.ruff" in content:
                has_ruff = True
                self.observed.append(EvidenceFact("pyproject.toml", "[tool.ruff]", "configured", "FILE_CONTENT", "ruff linter configuration found in pyproject.toml"))

            if "mypy" in content_lower or "tool.mypy" in content:
                has_mypy = True
                self.observed.append(EvidenceFact("pyproject.toml", "[tool.mypy]", "configured", "FILE_CONTENT", "mypy typechecker configuration found in pyproject.toml"))

        # Test runner registration
        if has_pytest:
            cmd = pkg_prefix + ["pytest", "-o", "console_output_style=classic", "--capture=no"] if pkg_prefix else ["pytest", "-o", "console_output_style=classic", "--capture=no"]
            in_path = is_tool_in_path(cmd[0])
            self.tools.append(
                ToolFact(
                    name="pytest",
                    category=ToolCategory.TEST_RUNNER,
                    manifest_path="pyproject.toml" if pyproject_path.exists() else "pytest.ini",
                    command=cmd,
                    timeout_seconds=90,
                    required=True,
                    is_available_in_path=in_path,
                    non_interactive_flags=["-o", "console_output_style=classic", "--capture=no"],
                )
            )
            self.inferred.append(
                InferredFact(
                    hypothesis="Project uses pytest for test execution",
                    confidence=0.95,
                    rationale="Discovered pytest manifest configuration and conventions",
                    underlying_evidence=["pyproject.toml" if pyproject_path.exists() else "pytest.ini"],
                )
            )
        elif (self.repo_root / "tests").is_dir():
            # Fallback to standard library unittest
            cmd = ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]
            self.tools.append(
                ToolFact(
                    name="python-unittest",
                    category=ToolCategory.TEST_RUNNER,
                    manifest_path="tests/",
                    command=cmd,
                    timeout_seconds=60,
                    required=True,
                    is_available_in_path=is_tool_in_path("python"),
                )
            )
            self.inferred.append(
                InferredFact(
                    hypothesis="Project uses Python standard library unittest",
                    confidence=0.75,
                    rationale="Found tests/ directory without explicit pytest configuration",
                    underlying_evidence=["tests/"],
                )
            )

        # Linter registration
        if has_ruff:
            cmd = pkg_prefix + ["ruff", "check", "."] if pkg_prefix else ["ruff", "check", "."]
            self.tools.append(
                ToolFact(
                    name="ruff-check",
                    category=ToolCategory.LINTER,
                    manifest_path="pyproject.toml" if pyproject_path.exists() else "ruff.toml",
                    command=cmd,
                    timeout_seconds=30,
                    required=False,
                    is_available_in_path=is_tool_in_path(cmd[0]),
                )
            )

        # Typechecker registration
        if has_mypy:
            cmd = pkg_prefix + ["mypy", "."] if pkg_prefix else ["mypy", "."]
            self.tools.append(
                ToolFact(
                    name="mypy-typecheck",
                    category=ToolCategory.TYPECHECKER,
                    manifest_path="pyproject.toml" if pyproject_path.exists() else "mypy.ini",
                    command=cmd,
                    timeout_seconds=60,
                    required=False,
                    is_available_in_path=is_tool_in_path(cmd[0]),
                )
            )

    # -------------------------------------------------------------------------
    # TypeScript / JavaScript Ecosystem
    # -------------------------------------------------------------------------
    def _discover_typescript_javascript(self) -> None:
        pkg_json_path = self.repo_root / "package.json"
        if not pkg_json_path.exists():
            return

        self.languages.add("TypeScript / JavaScript")
        pkg_content = safe_read_text(pkg_json_path)
        try:
            pkg_data = json.loads(pkg_content)
        except Exception:
            pkg_data = {}

        self.observed.append(EvidenceFact("package.json", "file", "present", "FILE_EXISTENCE", "Node.js package manifest"))

        # Lockfile & package manager
        pnpm_lock = self.repo_root / "pnpm-lock.yaml"
        yarn_lock = self.repo_root / "yarn.lock"
        npm_lock = self.repo_root / "package-lock.json"
        bun_lock = self.repo_root / "bun.lockb"

        if pnpm_lock.exists():
            self.package_managers.add("pnpm")
            self.observed.append(EvidenceFact("pnpm-lock.yaml", "file", "present", "FILE_EXISTENCE", "pnpm lockfile"))
        if yarn_lock.exists():
            self.package_managers.add("yarn")
            self.observed.append(EvidenceFact("yarn.lock", "file", "present", "FILE_EXISTENCE", "yarn lockfile"))
        if bun_lock.exists():
            self.package_managers.add("bun")
            self.observed.append(EvidenceFact("bun.lockb", "file", "present", "FILE_EXISTENCE", "bun lockfile"))
        if npm_lock.exists():
            self.package_managers.add("npm")
            self.observed.append(EvidenceFact("package-lock.json", "file", "present", "FILE_EXISTENCE", "npm package-lock file"))

        # Default preferred execution manager
        pkg_mgr = "pnpm" if pnpm_lock.exists() else ("yarn" if yarn_lock.exists() else ("bun" if bun_lock.exists() else "npm"))
        if not self.package_managers:
            self.package_managers.add("npm")

        scripts = pkg_data.get("scripts", {})
        deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}

        # Framework indicators
        if "react" in deps or "react-dom" in deps:
            self.frameworks.add("React")
        if "svelte" in deps:
            self.frameworks.add("Svelte")
        if "vue" in deps:
            self.frameworks.add("Vue")
        if "next" in deps:
            self.frameworks.add("Next.js")
        if "express" in deps:
            self.frameworks.add("Express")

        # Test runner selection
        # Look for non-interactive scripts first: test:ci, vitest:once, test:once, test
        target_script = None
        for candidate in ["test:ci", "vitest:once", "test:once", "test:unit", "test"]:
            if candidate in scripts:
                target_script = candidate
                break

        if target_script:
            script_val = scripts[target_script]
            self.observed.append(EvidenceFact("package.json", f"scripts.{target_script}", script_val, "FILE_CONTENT", f"Test script '{target_script}'"))
            
            # Formulate non-interactive command
            cmd = [pkg_mgr, "run", target_script] if pkg_mgr != "npm" or target_script != "test" else ["npm", "test"]
            non_interactive_flags = []
            
            # Check if vitest or jest is invoked directly without non-interactive flags
            if "vitest" in script_val and "--run" not in script_val:
                non_interactive_flags.append("--run")
            elif "jest" in script_val and "--watchAll=false" not in script_val:
                non_interactive_flags.append("--watchAll=false")

            self.tools.append(
                ToolFact(
                    name="node-test-runner",
                    category=ToolCategory.TEST_RUNNER,
                    manifest_path="package.json",
                    command=cmd,
                    timeout_seconds=90,
                    required=True,
                    is_available_in_path=is_tool_in_path(pkg_mgr),
                    non_interactive_flags=non_interactive_flags,
                )
            )
            self.inferred.append(
                InferredFact(
                    hypothesis=f"Project executes tests via '{' '.join(cmd)}'",
                    confidence=0.95,
                    rationale=f"Found '{target_script}' script in package.json",
                    underlying_evidence=[f"package.json#scripts.{target_script}"],
                )
            )

        # Typechecker
        if (self.repo_root / "tsconfig.json").exists():
            self.observed.append(EvidenceFact("tsconfig.json", "file", "present", "FILE_EXISTENCE", "TypeScript configuration file"))
            self.tools.append(
                ToolFact(
                    name="typescript-check",
                    category=ToolCategory.TYPECHECKER,
                    manifest_path="tsconfig.json",
                    command=[pkg_mgr, "exec", "tsc", "--noEmit"] if pkg_mgr != "npm" else ["npx", "tsc", "--noEmit"],
                    timeout_seconds=60,
                    required=False,
                    is_available_in_path=is_tool_in_path(pkg_mgr),
                )
            )

        # Linter
        if "lint" in scripts:
            self.tools.append(
                ToolFact(
                    name="node-linter",
                    category=ToolCategory.LINTER,
                    manifest_path="package.json",
                    command=[pkg_mgr, "run", "lint"],
                    timeout_seconds=45,
                    required=False,
                    is_available_in_path=is_tool_in_path(pkg_mgr),
                )
            )

    # -------------------------------------------------------------------------
    # Go Ecosystem
    # -------------------------------------------------------------------------
    def _discover_go(self) -> None:
        go_mod_path = self.repo_root / "go.mod"
        if not go_mod_path.exists() and not any(self.repo_root.glob("*.go")):
            return

        self.languages.add("Go")
        self.build_systems.add("go")
        in_path = is_tool_in_path("go")

        if go_mod_path.exists():
            content = safe_read_text(go_mod_path)
            mod_match = re.search(r"^module\s+([^\s]+)", content, re.MULTILINE)
            module_name = mod_match.group(1) if mod_match else "unknown_go_module"
            self.observed.append(EvidenceFact("go.mod", "module", module_name, "FILE_CONTENT", "Go module manifest"))

        # Test runner
        self.tools.append(
            ToolFact(
                name="go-test-runner",
                category=ToolCategory.TEST_RUNNER,
                manifest_path="go.mod" if go_mod_path.exists() else "main.go",
                command=["go", "test", "-v", "-count=1", "./..."],
                timeout_seconds=120,
                required=True,
                is_available_in_path=in_path,
                non_interactive_flags=["-count=1"],
            )
        )
        self.inferred.append(
            InferredFact(
                hypothesis="Project tests with 'go test -v -count=1 ./...'",
                confidence=0.90,
                rationale="Go module conventions enforce canonical go test invocation",
                underlying_evidence=["go.mod" if go_mod_path.exists() else "Go files"],
            )
        )

        # Linter
        golangci_files = [".golangci.yml", ".golangci.yaml", ".golangci.toml"]
        has_golangci = any((self.repo_root / f).exists() for f in golangci_files)
        if has_golangci:
            self.tools.append(
                ToolFact(
                    name="golangci-lint",
                    category=ToolCategory.LINTER,
                    manifest_path=".golangci.yml",
                    command=["golangci-lint", "run", "./..."],
                    timeout_seconds=60,
                    required=False,
                    is_available_in_path=is_tool_in_path("golangci-lint"),
                )
            )
        else:
            self.tools.append(
                ToolFact(
                    name="go-vet",
                    category=ToolCategory.LINTER,
                    manifest_path="go.mod",
                    command=["go", "vet", "./..."],
                    timeout_seconds=30,
                    required=False,
                    is_available_in_path=in_path,
                )
            )

    # -------------------------------------------------------------------------
    # Rust Ecosystem
    # -------------------------------------------------------------------------
    def _discover_rust(self) -> None:
        cargo_path = self.repo_root / "Cargo.toml"
        if not cargo_path.exists():
            return

        self.languages.add("Rust")
        self.build_systems.add("cargo")
        self.package_managers.add("cargo")
        in_path = is_tool_in_path("cargo")

        content = safe_read_text(cargo_path)
        data = parse_simple_toml(content)
        pkg_name = data.get("package", {}).get("name", "unknown_crate")
        self.observed.append(EvidenceFact("Cargo.toml", "package.name", pkg_name, "FILE_CONTENT", "Rust Cargo crate manifest"))

        if (self.repo_root / "Cargo.lock").exists():
            self.observed.append(EvidenceFact("Cargo.lock", "file", "present", "FILE_EXISTENCE", "Rust Cargo lockfile"))

        # Test runner
        self.tools.append(
            ToolFact(
                name="cargo-test-runner",
                category=ToolCategory.TEST_RUNNER,
                manifest_path="Cargo.toml",
                command=["cargo", "test", "--workspace", "--no-fail-fast"],
                timeout_seconds=180,
                required=True,
                is_available_in_path=in_path,
                non_interactive_flags=["--no-fail-fast"],
            )
        )
        self.inferred.append(
            InferredFact(
                hypothesis="Project executes tests via 'cargo test --workspace --no-fail-fast'",
                confidence=0.95,
                rationale="Cargo.toml manifest present at repository root",
                underlying_evidence=["Cargo.toml"],
            )
        )

        # Linter (Clippy)
        self.tools.append(
            ToolFact(
                name="cargo-clippy",
                category=ToolCategory.LINTER,
                manifest_path="Cargo.toml",
                command=["cargo", "clippy", "--workspace", "--", "-D", "warnings"],
                timeout_seconds=120,
                required=False,
                is_available_in_path=in_path,
            )
        )

        # Formatter (rustfmt)
        self.tools.append(
            ToolFact(
                name="rustfmt-check",
                category=ToolCategory.FORMATTER,
                manifest_path="Cargo.toml",
                command=["cargo", "fmt", "--all", "--", "--check"],
                timeout_seconds=30,
                required=False,
                is_available_in_path=in_path,
            )
        )

    # -------------------------------------------------------------------------
    # Static Guidance Discovery (Zero Code Execution)
    # -------------------------------------------------------------------------
    def _discover_guidance(self) -> None:
        guidance_targets = [
            "AGENTS.md",
            "docs/AGENTS.md",
            ".agents/rules/project_rules.md",
            "README.md",
            "CONTRIBUTING.md",
        ]

        for rel_path in guidance_targets:
            file_path = self.repo_root / rel_path
            if not file_path.exists():
                continue

            content = safe_read_text(file_path)
            self.observed.append(EvidenceFact(rel_path, "file", "present", "FILE_EXISTENCE", f"Guidance document: {rel_path}"))

            commands: Dict[str, List[str]] = {"test": [], "lint": [], "build": []}
            constraints: List[str] = []

            # Extract code blocks under test/lint/build sections
            current_category = ""
            for line in content.splitlines():
                header_match = re.match(r"^#+\s*(.*)", line)
                if header_match:
                    h_text = header_match.group(1).lower()
                    if any(w in h_text for w in ["test", "testing", "verification", "check"]):
                        current_category = "test"
                    elif any(w in h_text for w in ["lint", "format", "style"]):
                        current_category = "lint"
                    elif any(w in h_text for w in ["build", "compile"]):
                        current_category = "build"
                    else:
                        current_category = ""

                # Look for shell command backticks or constraints
                if current_category:
                    cmd_match = re.findall(r"`([^`]+)`", line)
                    for c in cmd_match:
                        c_clean = c.strip()
                        if any(c_clean.startswith(prefix) for prefix in ["pytest", "npm", "pnpm", "yarn", "go test", "cargo", "python"]):
                            commands[current_category].append(c_clean)

                # Look for explicit constraints (e.g., "do not modify", "protected", "immutable", or instructions about core zones)
                if re.search(r"(?i)(do not modify|must not touch|immutable|protected path|forbidden|modify \.agents|edit \.agents|modify framework|edit framework)", line):
                    constraints.append(line.strip())

            self.guidance.append(
                GuidanceFact(
                    source_file=rel_path,
                    declared_commands=commands,
                    declared_constraints=constraints[:10],
                )
            )

        # Inspect CI Workflows statically
        ci_dir = self.repo_root / ".github" / "workflows"
        if ci_dir.is_dir():
            for yml_file in ci_dir.glob("*.yml"):
                rel_ci = str(yml_file.relative_to(self.repo_root))
                content = safe_read_text(yml_file)
                self.observed.append(EvidenceFact(rel_ci, "file", "present", "FILE_EXISTENCE", f"CI workflow file: {rel_ci}"))

                ci_cmds: List[str] = []
                for line in content.splitlines():
                    run_match = re.match(r"^\s*run:\s*(.*)", line)
                    if run_match:
                        cmd_val = run_match.group(1).strip()
                        if cmd_val and not cmd_val.startswith("|"):
                            ci_cmds.append(cmd_val)

                if ci_cmds:
                    self.guidance.append(
                        GuidanceFact(
                            source_file=rel_ci,
                            declared_commands={"ci_steps": ci_cmds[:10]},
                            declared_constraints=[],
                        )
                    )

    # -------------------------------------------------------------------------
    # Conflict Detection Taxonomy
    # -------------------------------------------------------------------------
    def _detect_conflicts(self) -> None:
        # Conflict Type 1: Guidance vs Manifest Drift
        # Example: README claims 'npm test' but manifest has no 'test' script or uses vitest
        for g in self.guidance:
            for declared_test in g.declared_commands.get("test", []):
                for runner in self.get_test_runners():
                    runner_cmd_str = " ".join(runner.command)
                    if declared_test != runner_cmd_str:
                        self.conflicts.append(
                            ConflictFact(
                                conflict_type=ConflictType.GUIDANCE_MANIFEST_DRIFT,
                                description=f"Guidance in '{g.source_file}' specifies test command '{declared_test}', but physical manifest configured '{runner_cmd_str}'.",
                                prose_claim=declared_test,
                                physical_reality=runner_cmd_str,
                                resolution_recommendation="Prioritize physical manifest over documentation. Update documentation to reflect actual executable runner.",
                                winning_source="MANIFEST",
                            )
                        )

        # Conflict Type 2: Manifest vs CI Drift
        ci_steps: List[str] = []
        for g in self.guidance:
            ci_steps.extend(g.declared_commands.get("ci_steps", []))

        for runner in self.get_test_runners():
            runner_base = runner.command[0]
            for step in ci_steps:
                # If CI runs a completely different package manager or runner
                if ("npm" in step and runner_base == "pnpm") or ("yarn" in step and runner_base == "npm"):
                    self.conflicts.append(
                        ConflictFact(
                            conflict_type=ConflictType.MANIFEST_CI_DRIFT,
                            description=f"Local manifest runner uses '{runner_base}', but CI workflow executes '{step}'.",
                            prose_claim=step,
                            physical_reality=runner_base,
                            resolution_recommendation="CI workflow represents automated production truth. Align local runner with CI runner.",
                            winning_source="CI_WORKFLOW",
                        )
                    )

        # Conflict Type 3: Constitutional Boundary Violation
        # If project guidance attempts to declare an AntiOS Core immutable zone as mutable
        for g in self.guidance:
            for constraint in g.declared_constraints:
                for zone in IMMUTABLE_CORE_ZONES:
                    if f"modify {zone}" in constraint.lower() or f"edit {zone}" in constraint.lower():
                        self.conflicts.append(
                            ConflictFact(
                                conflict_type=ConflictType.CONSTITUTIONAL_VIOLATION,
                                description=f"Guidance in '{g.source_file}' permits modifying AntiOS Core zone '{zone}'.",
                                prose_claim=constraint,
                                physical_reality=f"Zone '{zone}' is an immutable core invariant of AntiOS.",
                                resolution_recommendation="AntiOS Core Security overrides project guidance unconditionally. Deny mutation.",
                                winning_source="ANTIOS_CORE_CONSTITUTION",
                            )
                        )

        # Conflict Type 4: Tooling vs Environment (Missing Runtime in PATH)
        for t in self.tools:
            if t.required and not t.is_available_in_path:
                self.conflicts.append(
                    ConflictFact(
                        conflict_type=ConflictType.TOOLING_ENVIRONMENT_MISMATCH,
                        description=f"Manifest specifies required tool '{t.name}' ('{t.command[0]}'), but binary is not found in system PATH.",
                        prose_claim=f"Executable '{t.command[0]}' declared in {t.manifest_path}",
                        physical_reality="Binary not present in host environment",
                        resolution_recommendation="Fail-closed Stop Gate with ENVIRONMENT_UNAVAILABLE. Do not report as broken application code.",
                        winning_source="PHYSICAL_ENVIRONMENT",
                    )
                )

        # Conflict Type 5: Ambiguous Dual-Tooling (e.g. multiple lockfiles)
        js_mgrs = self.package_managers & {"pnpm", "yarn", "npm", "bun"}
        if len(js_mgrs) > 1:
            self.conflicts.append(
                ConflictFact(
                    conflict_type=ConflictType.AMBIGUOUS_DUAL_TOOLING,
                    description=f"Multiple package manager lockfiles detected in repository root (e.g. pnpm-lock.yaml, package-lock.json): {sorted(list(js_mgrs))}.",
                    prose_claim="Multiple package managers configured",
                    physical_reality=f"Dual lockfiles present on disk: {sorted(list(js_mgrs))}",
                    resolution_recommendation="Inspect CI workflow or mtime to select active package manager. Default to pnpm if present.",
                    winning_source="CI_WORKFLOW_OR_MTIME",
                )
            )

    def _discover_subsystems(self) -> None:
        """Heuristically discovers project subsystems, component directories, entrypoints, and tests."""
        standard_dirs = ["src", "lib", "packages", "apps", "services", "modules", "pkg", "internal", "framework"]
        tool_names = [t.name for t in self.tools]

        from framework.core.knowledge import OwnershipDeriver
        owner_deriver = OwnershipDeriver(str(self.repo_root))
        owner_deriver.scan()

        # 1. Monorepo workspace members
        for member in self.workspace_members:
            mem_path = member.relative_path.replace("\\", "/").strip("/")
            sub_id = member.name.replace("@", "").replace("/", "-").lower()
            entrypoints = []
            covering_tests = []
            test_commands = []

            abs_mem = self.repo_root / member.relative_path
            for candidate in ["index.ts", "index.js", "main.ts", "main.js", "src/index.ts", "src/main.ts", "lib.rs", "main.go", "setup.py", "__init__.py"]:
                if (abs_mem / candidate).exists():
                    entrypoints.append(f"{mem_path}/{candidate}")
                    break

            for t_candidate in [f"tests/{sub_id}", f"{mem_path}/tests", f"{mem_path}/test"]:
                if (self.repo_root / t_candidate).exists():
                    covering_tests.append(t_candidate)
                    break

            own_res = owner_deriver.resolve_path(mem_path)

            self.subsystems[sub_id] = {
                "subsystem_id": sub_id,
                "name": member.name,
                "description": f"Workspace package {member.name}",
                "area": "monorepo_member",
                "root_paths": [mem_path],
                "entrypoints": entrypoints or [mem_path],
                "authoritative_files": entrypoints or [mem_path],
                "covering_tests": covering_tests,
                "test_commands": [f"npm test --prefix {mem_path}"] if getattr(member, "package_type", "") in ("typescript", "javascript", "npm") else [],
                "applicable_skills": ["antios-engineer"],
                "applicable_workflows": ["FEATURE", "BUG"],
                "governing_rules": [],
                "protected_invariants": [],
                "dependencies": member.dependencies,
                "consumers": [],
                "documentation_paths": [f"{mem_path}/README.md"] if (abs_mem / "README.md").exists() else [],
                "keywords": [sub_id, member.name.lower()],
                "purpose": f"Workspace package {member.name}",
                "authoritative_interfaces": entrypoints or [mem_path],
                "risk_tier": "HIGH" if len(member.dependencies) > 3 else "MEDIUM",
                "owner": own_res.owner,
                "owner_source": own_res.source,
                "owner_confidence": own_res.confidence,
                "epistemic_state": "OBSERVED",
                "documentation_categories": {"component": [f"{mem_path}/README.md"]} if (abs_mem / "README.md").exists() else {},
            }

        # 2. Standard directory scan
        for s_dir in standard_dirs:
            abs_dir = self.repo_root / s_dir
            if abs_dir.is_dir():
                try:
                    for child in abs_dir.iterdir():
                        if child.is_dir() and not child.name.startswith((".", "_")):
                            sub_name = child.name.lower()
                            rel_child = f"{s_dir}/{child.name}"

                            entrypoints = []
                            for ep in ["__init__.py", "service.py", "index.ts", "index.js", "main.go", "lib.rs", "mod.rs", "app.py"]:
                                if (child / ep).exists():
                                    entrypoints.append(f"{rel_child}/{ep}")

                            covering_tests = []
                            test_commands = []
                            for tc in [f"tests/test_{sub_name}.py", f"tests/test_{sub_name}.ts", f"tests/{sub_name}", f"test/{sub_name}", f"{rel_child}/tests"]:
                                if (self.repo_root / tc).exists():
                                    covering_tests.append(tc)
                                    if "pytest" in tool_names:
                                        test_commands.append(f"pytest {tc}")
                                    elif "npm" in tool_names or "vitest" in tool_names:
                                        test_commands.append(f"npm test -- {tc}")

                            sub_id = f"{s_dir}-{sub_name}" if s_dir in ["apps", "services"] else sub_name
                            if sub_id not in self.subsystems:
                                own_res = owner_deriver.resolve_path(rel_child)
                                doc_p = f"docs/subsystems/{sub_name}.md"
                                has_doc = (self.repo_root / doc_p).exists()
                                self.subsystems[sub_id] = {
                                    "subsystem_id": sub_id,
                                    "name": f"{sub_name.capitalize()} Subsystem",
                                    "description": f"Component at {rel_child}",
                                    "area": s_dir,
                                    "root_paths": [rel_child],
                                    "entrypoints": entrypoints or [rel_child],
                                    "authoritative_files": entrypoints or [rel_child],
                                    "covering_tests": covering_tests,
                                    "test_commands": test_commands,
                                    "applicable_skills": ["antios-engineer"],
                                    "applicable_workflows": ["FEATURE", "BUG"],
                                    "governing_rules": [],
                                    "protected_invariants": [],
                                    "dependencies": [],
                                    "consumers": [],
                                    "documentation_paths": [doc_p] if has_doc else [],
                                    "keywords": [sub_name, s_dir],
                                    "purpose": f"Core component for {sub_name} under {s_dir}",
                                    "authoritative_interfaces": entrypoints or [rel_child],
                                    "risk_tier": "MEDIUM",
                                    "owner": own_res.owner,
                                    "owner_source": own_res.source,
                                    "owner_confidence": own_res.confidence,
                                    "epistemic_state": "INFERRED",
                                    "documentation_categories": {"component": [doc_p]} if has_doc else {},
                                }
                except Exception:
                    pass

    def get_test_runners(self) -> List[ToolFact]:
        return [t for t in self.tools if t.category == ToolCategory.TEST_RUNNER]


def discover_project(repo_root: str) -> ProjectProfile:
    """Public functional entrypoint for project discovery."""
    topology, members = detect_workspace_topology(repo_root)
    engine = ProjectDiscoveryEngine(repo_root, topology=topology, members=members)
    return engine.discover()
