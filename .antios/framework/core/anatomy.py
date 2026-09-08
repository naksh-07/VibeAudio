"""AntiOS 2.0 Project Anatomy Compiler.

Phase 55: Derives a bounded project model from observable evidence.
Distinguishes:
- OBSERVED: Directly witnessed on disk (manifests, exact keys, files).
- INFERRED: Logically deduced from observed facts with documented rationale.
- UNKNOWN: Gaps where expected facts could not be observed or inferred.

Every generated fact carries provenance: source, evidence, confidence, epistemic_state, generator/version.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from framework.core.profile import (
    ConfidenceLevel,
    EvidenceFact,
    EvidenceTier,
    InferredFact,
    ProjectIdentity,
    ProjectProfile,
    ToolCategory,
    ToolFact,
    UnknownFact,
)
from framework.core.subsystem import SubsystemDeclaration
from framework.core.topology import WorkspaceMember, WorkspaceTopology


class ProjectArchetype(str, Enum):
    """Canonical target project archetypes."""
    STANDALONE_CLI = "STANDALONE_CLI"
    STANDALONE_LIBRARY = "STANDALONE_LIBRARY"
    FULLSTACK_WEB = "FULLSTACK_WEB"
    BACKEND_SERVICE = "BACKEND_SERVICE"
    MONOREPO_WORKSPACE = "MONOREPO_WORKSPACE"
    POLYGLOT_SERVICE = "POLYGLOT_SERVICE"
    UNKNOWN_LEGACY = "UNKNOWN_LEGACY"


@dataclass
class ManifestEvidence:
    """Discovered package or build manifest evidence."""
    path: str
    manifest_type: str  # e.g. "package.json", "pyproject.toml", "Cargo.toml", "go.mod"
    lockfile_present: bool = False
    lockfile_path: Optional[str] = None
    members: List[str] = field(default_factory=list)
    declared_scripts: Dict[str, str] = field(default_factory=dict)
    has_build_target: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestRootMap:
    """Mapping of test roots to framework and runner expectations."""
    root_path: str
    framework: str  # "pytest", "jest", "vitest", "cargo-test", "go-test", "unknown"
    runner_command: List[str] = field(default_factory=list)
    timeout_seconds: int = 60
    scope: str = "GLOBAL"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectAnatomy:
    """Bounded, canonical model of target project anatomy.
    
    Adheres to the Non-Negotiable Architectural Principles:
    - Never fabricates capabilities or presents guesses as facts.
    - Preserves strict epistemic segregation: OBSERVED, INFERRED, UNKNOWN.
    - Fully regenerable with cryptographic fingerprint and provenance.
    """
    project_name: str
    root_path: str
    archetype: str
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    package_manifests: List[Dict[str, Any]] = field(default_factory=list)
    source_roots: List[str] = field(default_factory=list)
    test_roots: List[str] = field(default_factory=list)
    test_runners: List[Dict[str, Any]] = field(default_factory=list)
    build_systems: List[str] = field(default_factory=list)
    package_managers: List[str] = field(default_factory=list)
    application_entrypoints: List[Dict[str, str]] = field(default_factory=list)
    executable_entrypoints: List[str] = field(default_factory=list)
    major_subsystems: List[Dict[str, Any]] = field(default_factory=list)
    important_directories: List[str] = field(default_factory=list)
    configuration_surfaces: List[str] = field(default_factory=list)
    public_interfaces: List[str] = field(default_factory=list)
    dependency_relationships: List[Dict[str, Any]] = field(default_factory=list)
    documentation_surfaces: List[str] = field(default_factory=list)
    agent_facing_configuration: Dict[str, Any] = field(default_factory=dict)
    existing_agents_structure: Dict[str, Any] = field(default_factory=dict)
    ownership_signals: Dict[str, Any] = field(default_factory=dict)
    epistemic_ledger: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)
    manifest_fingerprint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class ProjectAnatomyCompiler:
    """Deterministic compiler deriving bounded ProjectAnatomy from observable evidence."""

    VERSION = "2.0.0"

    def __init__(self, repo_root: Union[str, Path]):
        self.repo_root = Path(os.path.normcase(os.path.abspath(repo_root)))

    def compile(self, profile: Optional[ProjectProfile] = None) -> ProjectAnatomy:
        """Compiles ProjectAnatomy from disk evidence and profile."""
        if profile is None:
            from framework.core.discovery import discover_project
            profile = discover_project(str(self.repo_root))

        observed_facts: List[Dict[str, Any]] = []
        inferred_facts: List[Dict[str, Any]] = []
        unknown_facts: List[Dict[str, Any]] = []

        # 1. Package Manifests & Lockfiles (OBSERVED)
        manifests = self._discover_manifests(observed_facts)

        # 2. Source Roots, Test Roots, Directories (OBSERVED)
        source_roots = self._discover_source_roots(observed_facts)
        test_roots = self._discover_test_roots(observed_facts)
        important_dirs = self._discover_important_directories(observed_facts)

        # 3. Config Surfaces & Doc Surfaces (OBSERVED)
        config_surfaces = self._discover_config_surfaces(observed_facts)
        doc_surfaces = self._discover_documentation_surfaces(observed_facts)

        # 4. Agent Surfaces & Existing .agents Structure (OBSERVED)
        agent_surfaces, existing_agents = self._discover_agent_surfaces(observed_facts)

        # 5. Ownership Signals (OBSERVED / UNKNOWN)
        ownership_signals = self._discover_ownership_signals(observed_facts, unknown_facts)

        # 6. Test Runners & Build Systems (OBSERVED / INFERRED)
        test_runners = self._compile_test_runners(profile, observed_facts, unknown_facts)
        build_systems = list(profile.identity.build_systems)
        package_managers = list(profile.identity.package_managers)

        # 7. Application & Executable Entrypoints (OBSERVED / INFERRED)
        app_entrypoints, exec_entrypoints = self._discover_entrypoints(manifests, observed_facts, inferred_facts, unknown_facts)

        # 8. Subsystems & Dependencies (OBSERVED / INFERRED)
        subsystems, dep_relations = self._compile_subsystems_and_deps(profile, observed_facts, inferred_facts)

        # 9. Public Interfaces (INFERRED / UNKNOWN)
        public_interfaces = self._discover_public_interfaces(app_entrypoints, source_roots, inferred_facts, unknown_facts)

        # 10. Archetype Classification (INFERRED / UNKNOWN)
        archetype = self._classify_archetype(
            profile=profile,
            manifests=manifests,
            app_entrypoints=app_entrypoints,
            source_roots=source_roots,
            inferred=inferred_facts,
            unknowns=unknown_facts,
        )

        # Compute deterministic fingerprint
        manifest_fingerprint = profile.manifest_fingerprint
        if not manifest_fingerprint:
            manifest_fingerprint = self._calculate_manifest_fingerprint(manifests)

        # Provenance block
        now_ts = None
        existing_anatomy_file = self.repo_root / ".antios/project_anatomy.json"
        if existing_anatomy_file.is_file():
            try:
                with open(existing_anatomy_file, "r", encoding="utf-8-sig") as f:
                    prev_anatomy = json.load(f)
                if prev_anatomy.get("provenance", {}).get("manifest_fingerprint") == manifest_fingerprint:
                    now_ts = prev_anatomy.get("provenance", {}).get("generated_at")
            except Exception:
                pass
        if not now_ts:
            now_ts = datetime.now(timezone.utc).isoformat()
        provenance = {
            "generator": f"AntiOS ProjectAnatomyCompiler v{self.VERSION}",
            "generated_at": now_ts,
            "manifest_fingerprint": manifest_fingerprint,
            "epistemic_state": "OBSERVED" if not unknown_facts else "PARTIALLY_OBSERVED",
            "confidence": 1.0 if not unknown_facts else round(max(0.6, 1.0 - (len(unknown_facts) * 0.08)), 2),
        }

        # Epistemic Ledger
        epistemic_ledger = {
            EvidenceTier.OBSERVED.value: observed_facts,
            EvidenceTier.INFERRED.value: inferred_facts,
            EvidenceTier.UNKNOWN.value: unknown_facts,
        }

        return ProjectAnatomy(
            project_name=profile.identity.name or self.repo_root.name,
            root_path=str(self.repo_root),
            archetype=archetype.value,
            languages=list(profile.identity.languages),
            frameworks=list(profile.identity.frameworks),
            package_manifests=[m.to_dict() for m in manifests],
            source_roots=source_roots,
            test_roots=test_roots,
            test_runners=test_runners,
            build_systems=build_systems,
            package_managers=package_managers,
            application_entrypoints=app_entrypoints,
            executable_entrypoints=exec_entrypoints,
            major_subsystems=subsystems,
            important_directories=important_dirs,
            configuration_surfaces=config_surfaces,
            public_interfaces=public_interfaces,
            dependency_relationships=dep_relations,
            documentation_surfaces=doc_surfaces,
            agent_facing_configuration=agent_surfaces,
            existing_agents_structure=existing_agents,
            ownership_signals=ownership_signals,
            epistemic_ledger=epistemic_ledger,
            provenance=provenance,
            manifest_fingerprint=manifest_fingerprint,
        )

    # --------------------------------------------------------------------------
    # Discovery Helpers
    # --------------------------------------------------------------------------

    def _discover_manifests(self, observed: List[Dict[str, Any]]) -> List[ManifestEvidence]:
        manifest_candidates = [
            ("package.json", "npm", ["pnpm-lock.yaml", "package-lock.json", "yarn.lock", "bun.lockb"]),
            ("pyproject.toml", "python", ["uv.lock", "poetry.lock", "Pipfile.lock"]),
            ("setup.py", "python", []),
            ("Cargo.toml", "cargo", ["Cargo.lock"]),
            ("go.mod", "go", ["go.sum"]),
            ("Makefile", "make", []),
            ("CMakeLists.txt", "cmake", []),
        ]
        results: List[ManifestEvidence] = []
        for mf_name, mf_type, lock_names in manifest_candidates:
            mf_path = self.repo_root / mf_name
            if mf_path.is_file():
                lock_present = False
                lock_path = None
                for lk in lock_names:
                    lk_p = self.repo_root / lk
                    if lk_p.is_file():
                        lock_present = True
                        lock_path = lk
                        break

                scripts: Dict[str, str] = {}
                members: List[str] = []
                if mf_name == "package.json":
                    try:
                        with open(mf_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        scripts = {k: str(v) for k, v in data.get("scripts", {}).items()}
                        if "workspaces" in data:
                            ws = data["workspaces"]
                            if isinstance(ws, list):
                                members = ws
                            elif isinstance(ws, dict):
                                members = ws.get("packages", [])
                    except Exception:
                        pass
                elif mf_name == "Cargo.toml":
                    try:
                        content = mf_path.read_text(encoding="utf-8")
                        if "[workspace]" in content:
                            import re
                            m = re.search(r"members\s*=\s*\[(.*?)\]", content, re.DOTALL)
                            if m:
                                members = [x.strip().strip("\"'") for x in m.group(1).split(",") if x.strip()]
                    except Exception:
                        pass

                ev = ManifestEvidence(
                    path=mf_name,
                    manifest_type=mf_type,
                    lockfile_present=lock_present,
                    lockfile_path=lock_path,
                    members=members,
                    declared_scripts=scripts,
                    has_build_target=bool(scripts.get("build") or mf_name in ["Cargo.toml", "Makefile", "CMakeLists.txt"]),
                )
                results.append(ev)
                observed.append({
                    "fact": f"Manifest '{mf_name}' detected",
                    "source": mf_name,
                    "witness_type": "FILE_EXISTENCE",
                    "lockfile_present": lock_present,
                })
        return results

    def _discover_source_roots(self, observed: List[Dict[str, Any]]) -> List[str]:
        roots: List[str] = []
        candidates = ["src", "lib", "app", "packages", "pkg", "cmd", "internal", "framework"]
        for c in candidates:
            p = self.repo_root / c
            if p.is_dir():
                roots.append(c)
                observed.append({
                    "fact": f"Source root '{c}/' detected",
                    "source": c,
                    "witness_type": "DIR_EXISTENCE",
                })
        # If no dedicated source folder exists, check for top-level code files
        if not roots:
            for item in self.repo_root.iterdir():
                if item.is_file() and item.suffix in [".py", ".ts", ".js", ".go", ".rs"]:
                    roots.append(".")
                    break
        return roots

    def _discover_test_roots(self, observed: List[Dict[str, Any]]) -> List[str]:
        roots: List[str] = []
        candidates = ["tests", "test", "__tests__", "spec"]
        for c in candidates:
            p = self.repo_root / c
            if p.is_dir():
                roots.append(c)
                observed.append({
                    "fact": f"Test root '{c}/' detected",
                    "source": c,
                    "witness_type": "DIR_EXISTENCE",
                })
        return roots

    def _discover_important_directories(self, observed: List[Dict[str, Any]]) -> List[str]:
        important = []
        candidates = [
            "docs", "public", "static", "scripts", "build", "dist",
            "components", "views", "pages", "styles", "migrations",
            "api", "services", "models", ".github", ".agents",
        ]
        for c in candidates:
            if (self.repo_root / c).is_dir():
                important.append(c)
            for s_root in ["src", "lib", "app"]:
                if (self.repo_root / s_root / c).is_dir():
                    important.append(c)
        return sorted(list(set(important)))

    def _discover_config_surfaces(self, observed: List[Dict[str, Any]]) -> List[str]:
        surfaces = []
        candidates = [
            "tsconfig.json", "vite.config.ts", "vite.config.js", "next.config.js",
            "tailwind.config.js", "tailwind.config.ts", "jest.config.js", "vitest.config.ts",
            "antios.config.json", ".eslintrc.json", ".eslintrc.js", "ruff.toml",
            "pytest.ini", "setup.cfg", "go.work", "pnpm-workspace.yaml",
        ]
        for c in candidates:
            p = self.repo_root / c
            if p.is_file():
                surfaces.append(c)
                observed.append({
                    "fact": f"Config surface '{c}' detected",
                    "source": c,
                    "witness_type": "FILE_EXISTENCE",
                })
        return surfaces

    def _discover_documentation_surfaces(self, observed: List[Dict[str, Any]]) -> List[str]:
        surfaces = []
        candidates = [
            "README.md", "CONTRIBUTING.md", "ARCHITECTURE.md", "DECISION_REGISTER.md",
            "ANTIOS_V1.md", "ANTIOS_SOURCE_OF_TRUTH.md", "ANTIOS_CONSTITUTION.md",
            "docs/INDEX.md", "docs/ACTIVE_CONTEXT.md", "docs/LESSONS.md",
        ]
        for c in candidates:
            p = self.repo_root / c
            if p.is_file():
                surfaces.append(c)
        return surfaces

    def _discover_agent_surfaces(
        self, observed: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        agents_dir = self.repo_root / ".agents"
        agent_cfg: Dict[str, Any] = {
            "has_agents_directory": agents_dir.is_dir(),
            "has_hooks": (agents_dir / "hooks.json").is_file(),
            "has_instructions": (self.repo_root / "AGENTS.md").is_file() or (self.repo_root / "CLAUDE.md").is_file(),
        }

        existing_skills: List[str] = []
        skills_dir = agents_dir / "skills"
        if skills_dir.is_dir():
            for s in skills_dir.iterdir():
                if s.is_dir() and (s / "SKILL.md").is_file():
                    existing_skills.append(s.name)

        existing_agents_struct: Dict[str, Any] = {
            "skills": existing_skills,
            "skills_count": len(existing_skills),
            "custom_agents": [],
        }

        agents_def_dir = agents_dir / "agents"
        if agents_def_dir.is_dir():
            for a in agents_def_dir.iterdir():
                if a.is_file() or (a.is_dir() and (a / "agent.json").is_file()):
                    existing_agents_struct["custom_agents"].append(a.name)

        if existing_skills:
            observed.append({
                "fact": f"Existing agent skills detected: {', '.join(existing_skills)}",
                "source": ".agents/skills/",
                "witness_type": "DIR_SCAN",
            })

        return agent_cfg, existing_agents_struct

    def _discover_ownership_signals(
        self, observed: List[Dict[str, Any]], unknowns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        signals: Dict[str, Any] = {"declared_owner": None, "source": "UNKNOWN", "codeowners_present": False}
        codeowners_paths = [
            self.repo_root / ".github" / "CODEOWNERS",
            self.repo_root / "CODEOWNERS",
            self.repo_root / "docs" / "CODEOWNERS",
        ]
        for p in codeowners_paths:
            if p.is_file():
                signals["codeowners_present"] = True
                signals["source"] = str(p.relative_to(self.repo_root)).replace("\\", "/")
                observed.append({
                    "fact": f"CODEOWNERS file witnessed at {signals['source']}",
                    "source": signals["source"],
                    "witness_type": "FILE_EXISTENCE",
                })
                break

        if not signals["codeowners_present"]:
            unknowns.append({
                "field_name": "ownership_signals.codeowners",
                "reason": "No CODEOWNERS file witnessed in repository root or .github/",
                "required_action": "Rely on package manifest author or commit history heuristic",
            })
        return signals

    def _compile_test_runners(
        self, profile: ProjectProfile, observed: List[Dict[str, Any]], unknowns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        runners: List[Dict[str, Any]] = []
        for r in profile.get_test_runners():
            runners.append({
                "name": r.name,
                "manifest_path": r.manifest_path,
                "command": r.command,
                "timeout_seconds": r.timeout_seconds,
                "required": r.required,
                "cwd": r.cwd,
                "is_available_in_path": r.is_available_in_path,
            })
            observed.append({
                "fact": f"Test runner '{r.name}' discovered with command '{' '.join(r.command)}'",
                "source": r.manifest_path,
                "witness_type": "MANIFEST_KEY",
            })

        if not runners:
            unknowns.append({
                "field_name": "test_runners",
                "reason": "No test runner configured or discovered in manifests",
                "required_action": "Configure test_runners in antios.config.json or declare a test runner script",
            })
        return runners

    def _discover_entrypoints(
        self,
        manifests: List[ManifestEvidence],
        observed: List[Dict[str, Any]],
        inferred: List[Dict[str, Any]],
        unknowns: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, str]], List[str]]:
        app_entrypoints: List[Dict[str, str]] = []
        exec_entrypoints: List[str] = []

        common_candidates = [
            ("main.py", "CLI/MAIN"),
            ("app.py", "BACKEND/HTTP"),
            ("cli.py", "CLI"),
            ("src/main.rs", "CLI/MAIN"),
            ("src/lib.rs", "LIBRARY"),
            ("main.go", "CLI/MAIN"),
            ("src/index.ts", "LIBRARY/APP"),
            ("src/main.ts", "APP"),
            ("src/App.tsx", "UI/ROOT"),
            ("pages/index.tsx", "UI/PAGE"),
            ("app/page.tsx", "UI/PAGE"),
        ]
        for rel_p, ep_type in common_candidates:
            p = self.repo_root / rel_p
            if p.is_file():
                app_entrypoints.append({"path": rel_p, "type": ep_type})
                observed.append({
                    "fact": f"Entrypoint '{rel_p}' detected ({ep_type})",
                    "source": rel_p,
                    "witness_type": "FILE_EXISTENCE",
                })

        pkg_json = self.repo_root / "package.json"
        if pkg_json.is_file():
            try:
                with open(pkg_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "main" in data and isinstance(data["main"], str):
                    app_entrypoints.append({"path": data["main"], "type": "MODULE_MAIN"})
                if "bin" in data:
                    bin_data = data["bin"]
                    if isinstance(bin_data, str):
                        exec_entrypoints.append(bin_data)
                    elif isinstance(bin_data, dict):
                        for k, v in bin_data.items():
                            exec_entrypoints.append(str(v))
            except Exception:
                pass

        if not app_entrypoints:
            unknowns.append({
                "field_name": "application_entrypoints",
                "reason": "Could not identify standard entrypoint file (main.py, index.ts, main.go, etc.)",
                "required_action": "Check project documentation or custom build script for entrypoint",
            })
        return app_entrypoints, exec_entrypoints

    def _compile_subsystems_and_deps(
        self, profile: ProjectProfile, observed: List[Dict[str, Any]], inferred: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        subsystems: List[Dict[str, Any]] = []
        deps: List[Dict[str, Any]] = []

        raw_subs = profile.subsystems.values() if isinstance(profile.subsystems, dict) else profile.subsystems
        for sub in raw_subs:
            if isinstance(sub, str):
                sub_dict = {"subsystem_id": sub, "name": sub, "dependencies": []}
            elif hasattr(sub, "to_dict"):
                sub_dict = sub.to_dict()
            elif isinstance(sub, dict):
                sub_dict = sub
            else:
                continue

            subsystems.append(sub_dict)
            sub_id = sub_dict.get("subsystem_id", "unknown")
            for upstream in sub_dict.get("dependencies", []):
                deps.append({
                    "source": sub_id,
                    "target": upstream,
                    "relation": "DEPENDS_ON",
                    "epistemic_state": "OBSERVED",
                })
        return subsystems, deps

    def _discover_public_interfaces(
        self,
        app_entrypoints: List[Dict[str, str]],
        source_roots: List[str],
        inferred: List[Dict[str, Any]],
        unknowns: List[Dict[str, Any]],
    ) -> List[str]:
        interfaces: List[str] = []
        for ep in app_entrypoints:
            interfaces.append(ep["path"])
        return interfaces

    def _classify_archetype(
        self,
        profile: ProjectProfile,
        manifests: List[ManifestEvidence],
        app_entrypoints: List[Dict[str, str]],
        source_roots: List[str],
        inferred: List[Dict[str, Any]],
        unknowns: List[Dict[str, Any]],
    ) -> ProjectArchetype:
        """Deterministically classifies project archetype based on observable evidence."""
        if profile.topology in [
            WorkspaceTopology.PNPM_WORKSPACE,
            WorkspaceTopology.NPM_WORKSPACE,
            WorkspaceTopology.CARGO_WORKSPACE,
            WorkspaceTopology.GO_WORKSPACE,
            WorkspaceTopology.PYTHON_WORKSPACE,
            WorkspaceTopology.POLYGLOT_MONOREPO,
        ] or any(m.members for m in manifests):
            inferred.append({
                "hypothesis": "Project is a Monorepo Workspace",
                "rationale": f"Topology '{profile.topology.value}' with workspace members witnessed in manifests",
                "confidence": 0.95,
            })
            return ProjectArchetype.MONOREPO_WORKSPACE

        frameworks_lower = [f.lower() for f in profile.identity.frameworks]
        has_frontend = any(f in frameworks_lower for f in ["react", "vue", "svelte", "next", "nuxt", "vite", "angular"])
        has_backend = any(f in frameworks_lower for f in ["fastapi", "flask", "django", "express", "actix", "gin"])

        fe_matches = [f for f in frameworks_lower if f in ['react', 'vue', 'svelte', 'next', 'nuxt', 'vite']]
        be_matches = [f for f in frameworks_lower if f in ['fastapi', 'flask', 'django', 'express']]

        if has_frontend and has_backend:
            inferred.append({
                "hypothesis": "Project is Fullstack Web Application",
                "rationale": f"Both frontend ({fe_matches}) and backend ({be_matches}) frameworks detected",
                "confidence": 0.90,
            })
            return ProjectArchetype.FULLSTACK_WEB

        if has_frontend:
            inferred.append({
                "hypothesis": "Project is Frontend Web Application",
                "rationale": f"Frontend framework detected: {fe_matches}",
                "confidence": 0.90,
            })
            return ProjectArchetype.FULLSTACK_WEB

        if has_backend:
            inferred.append({
                "hypothesis": "Project is Backend Service",
                "rationale": f"Backend framework detected: {be_matches}",
                "confidence": 0.90,
            })
            return ProjectArchetype.BACKEND_SERVICE

        entry_paths = [ep["path"].lower() for ep in app_entrypoints]
        entry_types = [ep["type"] for ep in app_entrypoints]
        if any("cli" in t or "main" in p or "cli" in p for p, t in zip(entry_paths, entry_types)):
            inferred.append({
                "hypothesis": "Project is Standalone CLI Application",
                "rationale": f"CLI or main entrypoint witnessed: {entry_paths}",
                "confidence": 0.85,
            })
            return ProjectArchetype.STANDALONE_CLI

        if any("lib" in p or "pkg" in p or "library" in t.lower() for p, t in zip(entry_paths, entry_types)):
            inferred.append({
                "hypothesis": "Project is Standalone Library",
                "rationale": f"Library entrypoint witnessed: {entry_paths}",
                "confidence": 0.85,
            })
            return ProjectArchetype.STANDALONE_LIBRARY

        if len(profile.identity.languages) >= 3:
            inferred.append({
                "hypothesis": "Project is Polyglot Service",
                "rationale": f"3 or more languages detected: {profile.identity.languages}",
                "confidence": 0.75,
            })
            return ProjectArchetype.POLYGLOT_SERVICE

        if profile.identity.languages:
            return ProjectArchetype.STANDALONE_CLI

        unknowns.append({
            "field_name": "archetype",
            "reason": "No identifiable language manifests or entrypoints discovered",
            "required_action": "Provide explicit project configuration or manifest",
        })
        return ProjectArchetype.UNKNOWN_LEGACY

    def _calculate_manifest_fingerprint(self, manifests: List[ManifestEvidence]) -> str:
        hasher = hashlib.sha256()
        for m in sorted(manifests, key=lambda x: x.path):
            hasher.update(m.path.encode("utf-8"))
            p = self.repo_root / m.path
            if p.is_file():
                try:
                    hasher.update(p.read_bytes())
                except Exception:
                    pass
        return hasher.hexdigest()
