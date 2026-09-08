"""
AntiOS 3.0 Project Environment Compiler — Project Model & Signal Discovery

Defines the normalized internal representation of target projects, discovered capabilities,
and repository signals across Python, TypeScript/JavaScript, Rust, Go, and mixed repositories.
"""

from __future__ import annotations

import os
import re
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class SignalKind(str, Enum):
    MANIFEST = "manifest"
    SOURCE_ROOT = "source_root"
    TEST_ROOT = "test_root"
    PACKAGE_ROOT = "package_root"
    CONFIG = "config"
    ENTRYPOINT = "entrypoint"
    BOUNDARY = "boundary"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


@dataclass
class DiscoveredSignal:
    kind: SignalKind
    path: str  # POSIX relative path
    source: str
    confidence: Confidence
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind.value,
            "path": self.path,
            "source": self.source,
            "confidence": self.confidence.value,
            "details": self.details,
        }


@dataclass
class SubsystemCandidate:
    name: str
    root_dir: str  # POSIX relative path
    description: str
    entrypoint: str  # POSIX relative path
    test_suite: List[str]
    capabilities: List[str]
    invariants: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    confidence: Confidence = Confidence.HIGH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "root_dir": self.root_dir,
            "description": self.description,
            "entrypoint": self.entrypoint,
            "test_suite": self.test_suite,
            "capabilities": self.capabilities,
            "invariants": self.invariants,
            "dependencies": self.dependencies,
            "confidence": self.confidence.value,
        }


@dataclass
class ProjectModel:
    repository_root: str  # Absolute path for compiler execution context
    project_id: str
    compiler_version: str = "3.0.0"
    languages: List[str] = field(default_factory=list)
    signals: List[DiscoveredSignal] = field(default_factory=list)
    manifests: List[str] = field(default_factory=list)
    source_roots: List[str] = field(default_factory=list)
    test_roots: List[str] = field(default_factory=list)
    package_roots: List[str] = field(default_factory=list)
    probable_entrypoints: List[str] = field(default_factory=list)
    subsystem_candidates: Dict[str, SubsystemCandidate] = field(default_factory=dict)
    test_bindings: Dict[str, List[str]] = field(default_factory=dict)
    protected_paths: List[str] = field(default_factory=list)
    workspace_roots: List[str] = field(default_factory=list)
    git_roots: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "compiler_version": self.compiler_version,
            "languages": sorted(self.languages),
            "manifests": sorted(self.manifests),
            "source_roots": sorted(self.source_roots),
            "test_roots": sorted(self.test_roots),
            "package_roots": sorted(self.package_roots),
            "probable_entrypoints": sorted(self.probable_entrypoints),
            "subsystems": {k: v.to_dict() for k, v in sorted(self.subsystem_candidates.items())},
            "protected_paths": sorted(self.protected_paths),
            "workspace_roots": sorted(self.workspace_roots),
        }


# Standard directory ignore patterns for bounded traversal
IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "dist",
    "build",
    "target",
    "bin",
    "obj",
    "coverage",
    ".turbo",
    ".next",
    ".nuxt",
    ".agents",
    ".antios",
}


def normalize_posix(path: str | Path) -> str:
    """Normalize any path to POSIX forward slashes, removing leading ./ and drive prefixes if relative."""
    p_str = str(path).replace("\\", "/")
    if p_str.startswith("./"):
        p_str = p_str[2:]
    return p_str.rstrip("/")


def derive_project_id(repo_root: Path) -> str:
    """
    Deterministically derive project identity without absolute paths or timestamps.
    Order of precedence:
    1. pyproject.toml [project.name] or [tool.poetry.name]
    2. package.json name
    3. Cargo.toml [package.name]
    4. go.mod module name
    5. Directory basename
    """
    # 1. pyproject.toml
    pyproject_file = repo_root / "pyproject.toml"
    if pyproject_file.is_file():
        try:
            content = pyproject_file.read_text(encoding="utf-8")
            m = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            if m:
                return m.group(1).strip().lower().replace("_", "-")
        except Exception:
            pass

    # 2. package.json
    pkg_file = repo_root / "package.json"
    if pkg_file.is_file():
        try:
            data = json.loads(pkg_file.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "name" in data and isinstance(data["name"], str):
                name = data["name"].strip().lower()
                # strip scope if present, e.g. @scope/name -> name
                if "/" in name:
                    name = name.split("/")[-1]
                return name.replace("_", "-")
        except Exception:
            pass

    # 3. Cargo.toml
    cargo_file = repo_root / "Cargo.toml"
    if cargo_file.is_file():
        try:
            content = cargo_file.read_text(encoding="utf-8")
            m = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            if m:
                return m.group(1).strip().lower().replace("_", "-")
        except Exception:
            pass

    # 4. go.mod
    go_mod = repo_root / "go.mod"
    if go_mod.is_file():
        try:
            content = go_mod.read_text(encoding="utf-8")
            m = re.search(r'module\s+([^\s\r\n]+)', content)
            if m:
                mod = m.group(1).strip().lower()
                return mod.split("/")[-1].replace("_", "-")
        except Exception:
            pass

    # Fallback to directory basename
    name = repo_root.name.lower().replace("_", "-")
    return name if name else "project"


class ProjectInspector:
    """
    Inspects repository files with bounded traversal and deterministic signal detection.
    Zero third-party dependencies, standard library only.
    """

    def __init__(self, repo_root: str | Path, max_depth: int = 4):
        self.repo_root = Path(repo_root).resolve()
        self.max_depth = max_depth

    def inspect(self) -> ProjectModel:
        project_id = derive_project_id(self.repo_root)
        model = ProjectModel(
            repository_root=str(self.repo_root),
            project_id=project_id,
        )

        # Check git root
        if (self.repo_root / ".git").exists():
            model.git_roots.append(".")

        # Discover top-level manifests & signals
        self._discover_manifests(model)
        self._discover_structure(model)
        self._detect_languages(model)
        self._discover_adapter_config(model)

        return model

    def _discover_manifests(self, model: ProjectModel) -> None:
        """Look for common ecosystem manifests at repo root and immediate subdirs."""
        candidates = [
            ("pyproject.toml", SignalKind.MANIFEST, "python", Confidence.HIGH),
            ("setup.py", SignalKind.MANIFEST, "python", Confidence.HIGH),
            ("setup.cfg", SignalKind.MANIFEST, "python", Confidence.HIGH),
            ("requirements.txt", SignalKind.MANIFEST, "python", Confidence.MEDIUM),
            ("Pipfile", SignalKind.MANIFEST, "python", Confidence.HIGH),
            ("package.json", SignalKind.MANIFEST, "javascript/typescript", Confidence.HIGH),
            ("tsconfig.json", SignalKind.CONFIG, "typescript", Confidence.HIGH),
            ("Cargo.toml", SignalKind.MANIFEST, "rust", Confidence.HIGH),
            ("go.mod", SignalKind.MANIFEST, "go", Confidence.HIGH),
            ("go.sum", SignalKind.MANIFEST, "go", Confidence.MEDIUM),
        ]

        for filename, kind, lang_hint, conf in candidates:
            filepath = self.repo_root / filename
            if filepath.is_file():
                rel_posix = filename
                model.manifests.append(rel_posix)
                model.signals.append(
                    DiscoveredSignal(
                        kind=kind,
                        path=rel_posix,
                        source=filename,
                        confidence=conf,
                        details={"language_hint": lang_hint},
                    )
                )

    def _discover_structure(self, model: ProjectModel) -> None:
        """Scan top-level and 1st-level directories for sources, tests, and packages."""
        if not self.repo_root.is_dir():
            return

        try:
            top_entries = sorted(os.listdir(self.repo_root))
        except OSError:
            return

        for entry in top_entries:
            if entry in IGNORED_DIRS or entry.startswith("."):
                continue

            entry_path = self.repo_root / entry
            if not entry_path.is_dir():
                # Top level entrypoint files
                if entry in ("main.py", "cli.py", "app.py", "index.ts", "index.js", "main.go"):
                    model.probable_entrypoints.append(entry)
                    model.signals.append(
                        DiscoveredSignal(
                            kind=SignalKind.ENTRYPOINT,
                            path=entry,
                            source="filesystem",
                            confidence=Confidence.HIGH,
                        )
                    )
                continue

            # Identify test roots
            if entry in ("tests", "test", "__tests__", "spec"):
                model.test_roots.append(entry)
                model.signals.append(
                    DiscoveredSignal(
                        kind=SignalKind.TEST_ROOT,
                        path=entry,
                        source="directory_convention",
                        confidence=Confidence.HIGH,
                    )
                )
                continue

            # Identify source roots
            if entry in ("src", "lib", "packages", "apps", "framework", "pkg", "cmd"):
                model.source_roots.append(entry)
                model.signals.append(
                    DiscoveredSignal(
                        kind=SignalKind.SOURCE_ROOT,
                        path=entry,
                        source="directory_convention",
                        confidence=Confidence.HIGH,
                    )
                )
                # Check for packages inside src/ or framework/
                self._scan_package_children(entry_path, entry, model)
            else:
                # Potential standalone package or subsystem directory
                if (entry_path / "__init__.py").is_file():
                    model.package_roots.append(entry)
                    model.signals.append(
                        DiscoveredSignal(
                            kind=SignalKind.PACKAGE_ROOT,
                            path=entry,
                            source="python_init",
                            confidence=Confidence.HIGH,
                        )
                    )
                elif (entry_path / "package.json").is_file():
                    model.package_roots.append(entry)
                    model.workspace_roots.append(entry)
                    model.signals.append(
                        DiscoveredSignal(
                            kind=SignalKind.PACKAGE_ROOT,
                            path=entry,
                            source="package_json",
                            confidence=Confidence.HIGH,
                        )
                    )
                elif (entry_path / "Cargo.toml").is_file():
                    model.package_roots.append(entry)
                    model.workspace_roots.append(entry)
                    model.signals.append(
                        DiscoveredSignal(
                            kind=SignalKind.PACKAGE_ROOT,
                            path=entry,
                            source="cargo_toml",
                            confidence=Confidence.HIGH,
                        )
                    )

    def _scan_package_children(self, dir_path: Path, prefix: str, model: ProjectModel) -> None:
        """Inspect one level deep inside source containers like src/ or framework/."""
        try:
            children = sorted(os.listdir(dir_path))
        except OSError:
            return

        for child in children:
            if child in IGNORED_DIRS or child.startswith("."):
                continue
            child_path = dir_path / child
            if not child_path.is_dir():
                continue

            rel_posix = f"{prefix}/{child}"
            if (child_path / "__init__.py").is_file():
                model.package_roots.append(rel_posix)
                model.signals.append(
                    DiscoveredSignal(
                        kind=SignalKind.PACKAGE_ROOT,
                        path=rel_posix,
                        source="python_init",
                        confidence=Confidence.HIGH,
                    )
                )
            elif (child_path / "package.json").is_file():
                model.package_roots.append(rel_posix)
                model.workspace_roots.append(rel_posix)
                model.signals.append(
                    DiscoveredSignal(
                        kind=SignalKind.PACKAGE_ROOT,
                        path=rel_posix,
                        source="package_json",
                        confidence=Confidence.HIGH,
                    )
                )

    def _detect_languages(self, model: ProjectModel) -> None:
        """Infer languages present in the repository from discovered signals and manifests."""
        languages: Set[str] = set()

        # Check manifests
        for manifest in model.manifests:
            if manifest in ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile"):
                languages.add("python")
            elif manifest in ("package.json",):
                languages.add("javascript")
            elif manifest in ("tsconfig.json",):
                languages.add("typescript")
            elif manifest in ("Cargo.toml",):
                languages.add("rust")
            elif manifest in ("go.mod", "go.sum"):
                languages.add("go")

        # Fallback shallow extension sample if manifests absent
        if not languages:
            ext_counts: Dict[str, int] = {}
            for root, dirs, files in os.walk(self.repo_root):
                # prune ignored dirs
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
                # depth control
                rel_depth = len(Path(root).relative_to(self.repo_root).parts)
                if rel_depth > self.max_depth:
                    dirs[:] = []
                    continue
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext:
                        ext_counts[ext] = ext_counts.get(ext, 0) + 1

            if ext_counts.get(".py", 0) > 0:
                languages.add("python")
            if ext_counts.get(".ts", 0) > 0 or ext_counts.get(".tsx", 0) > 0:
                languages.add("typescript")
            if ext_counts.get(".js", 0) > 0 or ext_counts.get(".jsx", 0) > 0:
                languages.add("javascript")
            if ext_counts.get(".rs", 0) > 0:
                languages.add("rust")
            if ext_counts.get(".go", 0) > 0:
                languages.add("go")

        model.languages = sorted(languages)

    def _discover_adapter_config(self, model: ProjectModel) -> None:
        """Check for existing antios.config.json or .agents boundaries."""
        adapter_file = self.repo_root / "antios.config.json"
        if adapter_file.is_file():
            model.signals.append(
                DiscoveredSignal(
                    kind=SignalKind.CONFIG,
                    path="antios.config.json",
                    source="project_adapter",
                    confidence=Confidence.HIGH,
                )
            )
            try:
                data = json.loads(adapter_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    if "protected_paths" in data and isinstance(data["protected_paths"], list):
                        model.protected_paths.extend([normalize_posix(p) for p in data["protected_paths"]])
            except Exception:
                pass

        if (self.repo_root / ".agents").is_dir():
            model.signals.append(
                DiscoveredSignal(
                    kind=SignalKind.BOUNDARY,
                    path=".agents",
                    source="antios_boundary",
                    confidence=Confidence.HIGH,
                )
            )
            model.protected_paths.append(".agents")
