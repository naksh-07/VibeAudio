"""AntiOS v1 Workspace Topology Detection and Member Representation.

Zero-external-dependency detection of monorepos and workspaces across:
- pnpm workspaces (pnpm-workspace.yaml)
- npm/yarn/bun workspaces (package.json)
- Cargo workspaces (Cargo.toml)
- Go workspaces (go.work or multiple go.mod)
- Python workspaces (pyproject.toml [tool.uv.workspace] or multiple pyproject.toml)
- Polyglot monorepos (combinations of multiple package types/workspaces)

Enforces safe traversal: NEVER enters node_modules, target, vendor, .git,
.agents, dist, build, .venv, etc.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from framework.core.profile import ToolFact

IGNORED_DIRS: Set[str] = {
    "node_modules",
    "target",
    "vendor",
    ".git",
    ".agents",
    "dist",
    "build",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".idea",
    ".vscode",
    ".turbo",
    ".next",
    ".nuxt",
}


class WorkspaceTopology(str, Enum):
    STANDALONE = "STANDALONE"
    PNPM_WORKSPACE = "PNPM_WORKSPACE"
    NPM_WORKSPACE = "NPM_WORKSPACE"
    CARGO_WORKSPACE = "CARGO_WORKSPACE"
    GO_WORKSPACE = "GO_WORKSPACE"
    PYTHON_WORKSPACE = "PYTHON_WORKSPACE"
    POLYGLOT_MONOREPO = "POLYGLOT_MONOREPO"


@dataclass
class WorkspaceMember:
    name: str
    relative_path: str  # e.g., "packages/core", "crates/engine", "services/api"
    package_type: str  # "typescript", "rust", "go", "python"
    manifest_path: str  # relative to repo_root
    tools: List[Any] = field(default_factory=list)  # List[ToolFact]
    dependencies: List[str] = field(default_factory=list)
    is_root: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "relative_path": self.relative_path,
            "package_type": self.package_type,
            "manifest_path": self.manifest_path,
            "tools": [t.to_dict() if hasattr(t, "to_dict") else t for t in self.tools],
            "dependencies": list(self.dependencies),
            "is_root": self.is_root,
        }


def is_safe_relative_path(rel_path: str) -> bool:
    """Ensure path does not enter any ignored directories."""
    parts = Path(rel_path).parts
    return not any(part in IGNORED_DIRS for part in parts)


def safe_read_text(path: Path, max_bytes: int = 250_000) -> str:
    """Read file safely with size limit and fallback encoding."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(max_bytes)
    except Exception:
        return ""


def safe_read_json(path: Path) -> Dict[str, Any]:
    """Safely parse JSON file with error fallback."""
    try:
        content = safe_read_text(path)
        if content:
            return json.loads(content)
    except Exception:
        pass
    return {}


def resolve_workspace_patterns(repo_root: Path, patterns: List[str]) -> List[Path]:
    """Resolve a list of glob or relative path patterns against repo_root safely."""
    matched_dirs: Set[Path] = set()
    exclude_patterns: List[str] = []

    for raw in patterns:
        p = raw.strip().strip("\"'").replace("\\", "/")
        if not p or p.startswith("#"):
            continue
        if p.startswith("!"):
            excl = p[1:].strip().strip("\"'").replace("\\", "/")
            if excl:
                exclude_patterns.append(excl)
            continue
        if p.startswith("./"):
            p = p[2:]
        p = p.rstrip("/")
        if not p:
            continue

        if any(c in p for c in ("*", "?")):
            try:
                for match in repo_root.glob(p):
                    if match.is_dir():
                        rel = match.relative_to(repo_root).as_posix()
                        if is_safe_relative_path(rel):
                            matched_dirs.add(match)
            except Exception:
                pass
        else:
            target = repo_root / p
            if target.is_dir():
                rel = target.relative_to(repo_root).as_posix()
                if is_safe_relative_path(rel):
                    matched_dirs.add(target)

    # Filter out exclusions
    import fnmatch
    final_dirs: List[Path] = []
    for d in matched_dirs:
        rel = d.relative_to(repo_root).as_posix()
        excluded = False
        for excl in exclude_patterns:
            if fnmatch.fnmatch(rel, excl) or fnmatch.fnmatch(d.name, excl):
                excluded = True
                break
        if not excluded:
            final_dirs.append(d)

    return sorted(final_dirs, key=lambda p: p.as_posix())


# -----------------------------------------------------------------------------
# Heuristics: pnpm
# -----------------------------------------------------------------------------
def _parse_pnpm_workspace(repo_root: Path) -> List[WorkspaceMember]:
    pnpm_file = repo_root / "pnpm-workspace.yaml"
    if not pnpm_file.is_file():
        pnpm_file = repo_root / "pnpm-workspace.yml"
    if not pnpm_file.is_file():
        return []

    content = safe_read_text(pnpm_file)
    patterns: List[str] = []
    in_packages = False
    for line in content.splitlines():
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("#"):
            continue
        if re.match(r"^packages\s*:", line_stripped):
            in_packages = True
            continue
        if in_packages:
            # Stop if another top-level key begins
            if not line.startswith(" ") and not line.startswith("\t") and not line_stripped.startswith("-"):
                break
            if line_stripped.startswith("-"):
                pat = line_stripped.lstrip("-").strip().strip("\"'")
                if pat:
                    patterns.append(pat)

    if not patterns:
        return []

    dirs = resolve_workspace_patterns(repo_root, patterns)
    members: List[WorkspaceMember] = []
    for d in dirs:
        pkg_json = d / "package.json"
        if pkg_json.is_file():
            rel_dir = d.relative_to(repo_root).as_posix()
            manifest_rel = pkg_json.relative_to(repo_root).as_posix()
            pkg_data = safe_read_json(pkg_json)
            name = pkg_data.get("name") or d.name
            deps = list(pkg_data.get("dependencies", {}).keys()) + list(pkg_data.get("devDependencies", {}).keys())
            members.append(
                WorkspaceMember(
                    name=name,
                    relative_path=rel_dir,
                    package_type="typescript",
                    manifest_path=manifest_rel,
                    dependencies=sorted(list(set(deps))),
                    is_root=False,
                )
            )
    return members


# -----------------------------------------------------------------------------
# Heuristics: npm / yarn / bun
# -----------------------------------------------------------------------------
def _parse_npm_workspace(repo_root: Path) -> List[WorkspaceMember]:
    pkg_json = repo_root / "package.json"
    if not pkg_json.is_file():
        return []
    pkg_data = safe_read_json(pkg_json)
    raw_workspaces = pkg_data.get("workspaces")
    if not raw_workspaces:
        return []

    patterns: List[str] = []
    if isinstance(raw_workspaces, list):
        patterns = [str(p) for p in raw_workspaces if isinstance(p, str)]
    elif isinstance(raw_workspaces, dict):
        pkg_patterns = raw_workspaces.get("packages", [])
        if isinstance(pkg_patterns, list):
            patterns = [str(p) for p in pkg_patterns if isinstance(p, str)]

    if not patterns:
        return []

    dirs = resolve_workspace_patterns(repo_root, patterns)
    members: List[WorkspaceMember] = []
    for d in dirs:
        member_pkg = d / "package.json"
        if member_pkg.is_file():
            rel_dir = d.relative_to(repo_root).as_posix()
            manifest_rel = member_pkg.relative_to(repo_root).as_posix()
            sub_data = safe_read_json(member_pkg)
            name = sub_data.get("name") or d.name
            deps = list(sub_data.get("dependencies", {}).keys()) + list(sub_data.get("devDependencies", {}).keys())
            members.append(
                WorkspaceMember(
                    name=name,
                    relative_path=rel_dir,
                    package_type="typescript",
                    manifest_path=manifest_rel,
                    dependencies=sorted(list(set(deps))),
                    is_root=False,
                )
            )
    return members


# -----------------------------------------------------------------------------
# Heuristics: Cargo
# -----------------------------------------------------------------------------
def _parse_cargo_dependencies(cargo_content: str) -> List[str]:
    deps: List[str] = []
    in_simple_deps = False
    for line in cargo_content.splitlines():
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("#"):
            continue
        # Section syntax: [dependencies.crate_name] or [target.'...'.dependencies.crate_name]
        section_dep_match = re.match(r"^\[.*dependencies\.([a-zA-Z0-9_\-]+)\]", line_stripped)
        if section_dep_match:
            deps.append(section_dep_match.group(1).strip())
            in_simple_deps = False
            continue
        # Standard table: [dependencies], [dev-dependencies], [build-dependencies]
        if re.match(r"^\[.*dependencies\]", line_stripped):
            in_simple_deps = True
            continue
        if line_stripped.startswith("["):
            in_simple_deps = False
            continue
        if in_simple_deps and "=" in line_stripped:
            dep_name = line_stripped.split("=", 1)[0].strip()
            if dep_name:
                deps.append(dep_name)
    return sorted(list(set(deps)))


def _parse_cargo_workspace(repo_root: Path) -> List[WorkspaceMember]:
    cargo_path = repo_root / "Cargo.toml"
    if not cargo_path.is_file():
        return []

    content = safe_read_text(cargo_path)
    if "[workspace]" not in content:
        return []

    patterns: List[str] = []
    match = re.search(r"members\s*=\s*\[(.*?)\]", content, re.DOTALL)
    if match:
        raw_list = match.group(1)
        patterns = re.findall(r'["\']([^"\']+)["\']', raw_list)

    if not patterns:
        return []

    dirs = resolve_workspace_patterns(repo_root, patterns)
    members: List[WorkspaceMember] = []
    for d in dirs:
        member_cargo = d / "Cargo.toml"
        if member_cargo.is_file():
            rel_dir = d.relative_to(repo_root).as_posix()
            manifest_rel = member_cargo.relative_to(repo_root).as_posix()
            cargo_text = safe_read_text(member_cargo)
            name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', cargo_text)
            name = name_match.group(1) if name_match else d.name
            deps = _parse_cargo_dependencies(cargo_text)
            members.append(
                WorkspaceMember(
                    name=name,
                    relative_path=rel_dir,
                    package_type="rust",
                    manifest_path=manifest_rel,
                    dependencies=deps,
                    is_root=False,
                )
            )
    return members


# -----------------------------------------------------------------------------
# Heuristics: Go
# -----------------------------------------------------------------------------
def _parse_go_dependencies(go_mod_content: str) -> List[str]:
    deps: List[str] = []
    in_require = False
    for line in go_mod_content.splitlines():
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("//"):
            continue
        if line_stripped.startswith("require ("):
            in_require = True
            continue
        if in_require:
            if line_stripped == ")":
                in_require = False
                continue
            parts = line_stripped.split()
            if parts:
                deps.append(parts[0])
        elif line_stripped.startswith("require "):
            parts = line_stripped.split()
            if len(parts) >= 2:
                deps.append(parts[1])
    return sorted(list(set(deps)))


def _parse_go_workspace(repo_root: Path) -> List[WorkspaceMember]:
    go_work = repo_root / "go.work"
    members: List[WorkspaceMember] = []

    if go_work.is_file():
        content = safe_read_text(go_work)
        use_paths: List[str] = []
        for block in re.finditer(r"use\s*\((.*?)\)", content, re.DOTALL):
            for line in block.group(1).splitlines():
                line = line.strip().strip("\"'")
                if line and not line.startswith("//"):
                    use_paths.append(line)
        for m in re.finditer(r"^use\s+([^\(\s][^\s]*)", content, re.MULTILINE):
            use_paths.append(m.group(1).strip().strip("\"'"))

        dirs = resolve_workspace_patterns(repo_root, use_paths)
        for d in dirs:
            mod_file = d / "go.mod"
            if mod_file.is_file():
                rel_dir = d.relative_to(repo_root).as_posix()
                manifest_rel = mod_file.relative_to(repo_root).as_posix()
                mod_text = safe_read_text(mod_file)
                mod_match = re.search(r"^module\s+([^\s]+)", mod_text, re.MULTILINE)
                name = mod_match.group(1) if mod_match else d.name
                deps = _parse_go_dependencies(mod_text)
                members.append(
                    WorkspaceMember(
                        name=name,
                        relative_path=rel_dir,
                        package_type="go",
                        manifest_path=manifest_rel,
                        dependencies=deps,
                        is_root=False,
                    )
                )
        return members

    # Scan subdirectories for multiple go.mod files
    sub_mods: List[Path] = []
    for root, dirs, files in os.walk(str(repo_root)):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        rel_root = os.path.relpath(root, str(repo_root))
        if rel_root != ".":
            depth = len(Path(rel_root).parts)
            if depth > 4:
                dirs.clear()
                continue
            if "go.mod" in files:
                sub_mods.append(Path(root))

    if len(sub_mods) >= 2 or (len(sub_mods) >= 1 and (repo_root / "go.mod").is_file()):
        for d in sub_mods:
            mod_file = d / "go.mod"
            rel_dir = d.relative_to(repo_root).as_posix()
            manifest_rel = mod_file.relative_to(repo_root).as_posix()
            mod_text = safe_read_text(mod_file)
            mod_match = re.search(r"^module\s+([^\s]+)", mod_text, re.MULTILINE)
            name = mod_match.group(1) if mod_match else d.name
            deps = _parse_go_dependencies(mod_text)
            members.append(
                WorkspaceMember(
                    name=name,
                    relative_path=rel_dir,
                    package_type="go",
                    manifest_path=manifest_rel,
                    dependencies=deps,
                    is_root=False,
                )
            )
    return members


# -----------------------------------------------------------------------------
# Heuristics: Python
# -----------------------------------------------------------------------------
def _parse_python_dependencies(pyproject_content: str) -> List[str]:
    deps: List[str] = []
    # Parse standard dependencies = [...] as well as optional and group dependencies
    for match in re.finditer(r"(?:dependencies|dependency-groups[a-zA-Z0-9_\-.]*)\s*=\s*\[(.*?)\]", pyproject_content, re.DOTALL):
        raw_list = match.group(1)
        for item in re.findall(r'["\']([^"\']+)["\']', raw_list):
            dep_name = re.split(r"[=><~^! ]", item)[0].strip()
            if dep_name:
                deps.append(dep_name)
    return sorted(list(set(deps)))


def _parse_python_workspace(repo_root: Path) -> List[WorkspaceMember]:
    pyproj = repo_root / "pyproject.toml"
    members: List[WorkspaceMember] = []

    if pyproj.is_file():
        content = safe_read_text(pyproj)
        if "[tool.uv.workspace]" in content:
            patterns: List[str] = []
            match = re.search(r"\[tool\.uv\.workspace\].*?members\s*=\s*\[(.*?)\]", content, re.DOTALL)
            if match:
                raw_list = match.group(1)
                patterns = re.findall(r'["\']([^"\']+)["\']', raw_list)
            if patterns:
                dirs = resolve_workspace_patterns(repo_root, patterns)
                for d in dirs:
                    sub_pyproj = d / "pyproject.toml"
                    if sub_pyproj.is_file():
                        rel_dir = d.relative_to(repo_root).as_posix()
                        manifest_rel = sub_pyproj.relative_to(repo_root).as_posix()
                        sub_text = safe_read_text(sub_pyproj)
                        name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', sub_text)
                        name = name_match.group(1) if name_match else d.name
                        deps = _parse_python_dependencies(sub_text)
                        members.append(
                            WorkspaceMember(
                                name=name,
                                relative_path=rel_dir,
                                package_type="python",
                                manifest_path=manifest_rel,
                                dependencies=deps,
                                is_root=False,
                            )
                        )
                return members

    # Scan subdirectories for multiple pyproject.toml files
    sub_pyprojs: List[Path] = []
    for root, dirs, files in os.walk(str(repo_root)):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        rel_root = os.path.relpath(root, str(repo_root))
        if rel_root != ".":
            depth = len(Path(rel_root).parts)
            if depth > 4:
                dirs.clear()
                continue
            if "pyproject.toml" in files:
                sub_pyprojs.append(Path(root))

    if len(sub_pyprojs) >= 2 or (len(sub_pyprojs) >= 1 and (repo_root / "pyproject.toml").is_file()):
        for d in sub_pyprojs:
            sub_pyproj = d / "pyproject.toml"
            rel_dir = d.relative_to(repo_root).as_posix()
            manifest_rel = sub_pyproj.relative_to(repo_root).as_posix()
            sub_text = safe_read_text(sub_pyproj)
            name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', sub_text)
            name = name_match.group(1) if name_match else d.name
            deps = _parse_python_dependencies(sub_text)
            members.append(
                WorkspaceMember(
                    name=name,
                    relative_path=rel_dir,
                    package_type="python",
                    manifest_path=manifest_rel,
                    dependencies=deps,
                    is_root=False,
                )
            )
    return members


# -----------------------------------------------------------------------------
# Top-level Detection Entrypoint
# -----------------------------------------------------------------------------
def detect_workspace_topology(repo_root: str) -> Tuple[WorkspaceTopology, List[WorkspaceMember]]:
    """Detect workspace topology and return (WorkspaceTopology, List[WorkspaceMember])."""
    root_path = Path(os.path.normcase(os.path.abspath(repo_root)))

    # 1. pnpm
    has_pnpm_manifest = (root_path / "pnpm-workspace.yaml").is_file() or (root_path / "pnpm-workspace.yml").is_file()
    pnpm_members = _parse_pnpm_workspace(root_path)

    # 2. npm / yarn / bun
    npm_members = _parse_npm_workspace(root_path)

    # 3. Cargo
    has_cargo_workspace = False
    cargo_file = root_path / "Cargo.toml"
    if cargo_file.is_file():
        has_cargo_workspace = "[workspace]" in safe_read_text(cargo_file)
    cargo_members = _parse_cargo_workspace(root_path)

    # 4. Go
    has_go_work = (root_path / "go.work").is_file()
    go_members = _parse_go_workspace(root_path)

    # 5. Python
    python_members = _parse_python_workspace(root_path)

    # Determine which ecosystems are active
    detected_ecosystems: Dict[str, List[WorkspaceMember]] = {}

    if has_pnpm_manifest or pnpm_members:
        detected_ecosystems["pnpm"] = pnpm_members
    elif npm_members:
        detected_ecosystems["npm"] = npm_members

    if has_cargo_workspace or cargo_members:
        detected_ecosystems["cargo"] = cargo_members

    if has_go_work or go_members:
        detected_ecosystems["go"] = go_members

    if python_members:
        detected_ecosystems["python"] = python_members

    if not detected_ecosystems:
        return WorkspaceTopology.STANDALONE, []

    # Check for polyglot monorepo (multiple ecosystems detected)
    if len(detected_ecosystems) > 1:
        combined_members: List[WorkspaceMember] = []
        seen_paths: Set[str] = set()
        for member_list in detected_ecosystems.values():
            for m in member_list:
                if m.relative_path not in seen_paths:
                    seen_paths.add(m.relative_path)
                    combined_members.append(m)
        return WorkspaceTopology.POLYGLOT_MONOREPO, combined_members

    # Single ecosystem detected
    eco_name, members = next(iter(detected_ecosystems.items()))
    package_types = {m.package_type for m in members}
    if len(package_types) > 1:
        return WorkspaceTopology.POLYGLOT_MONOREPO, members

    if eco_name == "pnpm":
        return WorkspaceTopology.PNPM_WORKSPACE, members
    elif eco_name == "npm":
        return WorkspaceTopology.NPM_WORKSPACE, members
    elif eco_name == "cargo":
        return WorkspaceTopology.CARGO_WORKSPACE, members
    elif eco_name == "go":
        return WorkspaceTopology.GO_WORKSPACE, members
    elif eco_name == "python":
        return WorkspaceTopology.PYTHON_WORKSPACE, members

    return WorkspaceTopology.STANDALONE, []
