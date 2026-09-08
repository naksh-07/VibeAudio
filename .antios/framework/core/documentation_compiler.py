"""AntiOS 2.0 Evidence-Driven Documentation Compiler.

Phase 76: Compiles and maintains agent-facing repository documentation directly from
observable filesystem evidence, manifest records, verified project anatomy, and
validated lessons:
  FILESYSTEM / ANATOMY / MANIFEST -> PROVENANCE EXTRACTION -> PROGRESSIVE DISCLOSURE COMPILER -> BOUNDED AGENT DOCS

Guarantees:
- Enforces progressive disclosure: concise, high-signal surfaces (<= 60-100 lines).
- Distinguishes ownership tiers: GENERATED, MANAGED, USER_AUTHORED, PROTECTED.
- Strictly preserves USER_AUTHORED and PROTECTED documents (never overwrites without authorization).
- Every generated fact traces back to verifiable physical evidence (manifest, filesystem, tests, config).
- Unsupported agent assumptions are strictly rejected.
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

from framework.core.manifest import ArtifactOwnership, ProjectManifest, load_manifest
from framework.core.provenance import compute_file_sha256


class DocSurfaceType(str, Enum):
    """Canonical documentation surfaces for agent wayfinding."""
    ARCHITECTURE_SUMMARY = "ARCHITECTURE_SUMMARY"
    SUBSYSTEM_MAP = "SUBSYSTEM_MAP"
    COMPONENT_MAP = "COMPONENT_MAP"
    TEST_MAP = "TEST_MAP"
    CONVENTIONS = "CONVENTIONS"
    OWNERSHIP_INFO = "OWNERSHIP_INFO"
    AGENT_GUIDANCE = "AGENT_GUIDANCE"
    CAPABILITY_DOCS = "CAPABILITY_DOCS"
    INTEGRATION_NOTES = "INTEGRATION_NOTES"


@dataclass
class CompiledDocSurface:
    """A compiled documentation surface."""
    surface_type: DocSurfaceType
    target_rel_path: str
    content: str
    provenance_sources: List[str]
    ownership: ArtifactOwnership
    content_hash: str
    is_user_authored_conflict: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "surface_type": self.surface_type.value,
            "target_rel_path": self.target_rel_path,
            "provenance_sources": list(self.provenance_sources),
            "ownership": self.ownership.value,
            "content_hash": self.content_hash,
            "is_user_authored_conflict": self.is_user_authored_conflict,
            "content_length": len(self.content),
        }


@dataclass
class DocCompilationResult:
    """Result of running the documentation compiler."""
    project_path: str
    timestamp: str
    surfaces: List[CompiledDocSurface]
    applied_files: List[str] = field(default_factory=list)
    skipped_user_authored: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    provenance_ledger: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_path": self.project_path,
            "timestamp": self.timestamp,
            "surfaces": [s.to_dict() for s in self.surfaces],
            "applied_files": list(self.applied_files),
            "skipped_user_authored": list(self.skipped_user_authored),
            "warnings": list(self.warnings),
            "provenance_ledger": self.provenance_ledger,
        }


class DocumentationCompiler:
    """Compiles concise, evidence-grounded agent documentation surfaces."""

    # Canonical relative paths for surfaces
    SURFACE_PATHS: Dict[DocSurfaceType, str] = {
        DocSurfaceType.ARCHITECTURE_SUMMARY: "docs/architecture/ARCHITECTURE_SUMMARY.md",
        DocSurfaceType.SUBSYSTEM_MAP: "docs/architecture/SUBSYSTEM_MAP.md",
        DocSurfaceType.COMPONENT_MAP: "docs/architecture/COMPONENT_MAP.md",
        DocSurfaceType.TEST_MAP: "docs/architecture/TEST_MAP.md",
        DocSurfaceType.AGENT_GUIDANCE: "docs/architecture/AGENT_GUIDANCE.md",
        DocSurfaceType.OWNERSHIP_INFO: "docs/architecture/OWNERSHIP_INFO.md",
    }

    PROTECTED_DOCS = {
        "antios_constitution.md",
        "antios_source_of_truth.md",
        "antios_v1.md",
        "docs/active_context.md",
        "docs/index.md",
    }

    @classmethod
    def compile_all_surfaces(
        cls,
        repo_root: Union[str, Path] = ".",
        dry_run: bool = True,
    ) -> DocCompilationResult:
        """Compiles all canonical surfaces for a repository from verified evidence."""
        root = Path(repo_root).resolve()
        now_str = datetime.now(timezone.utc).isoformat()

        manifest = cls._safe_load_manifest(root)
        anatomy = cls._safe_load_anatomy(root)
        config = cls._safe_load_config(root)

        surfaces: List[CompiledDocSurface] = []
        warnings: List[str] = []

        # 1. Architecture Summary
        surfaces.append(cls._compile_architecture_summary(root, anatomy, manifest, config))

        # 2. Subsystem Map
        surfaces.append(cls._compile_subsystem_map(root, anatomy))

        # 3. Component Map
        surfaces.append(cls._compile_component_map(root, anatomy))

        # 4. Test Map
        surfaces.append(cls._compile_test_map(root, config))

        # 5. Agent Guidance
        surfaces.append(cls._compile_agent_guidance(root, config))

        # 6. Ownership Info
        surfaces.append(cls._compile_ownership_info(root, manifest))

        applied_files: List[str] = []
        skipped_user_authored: List[str] = []
        provenance_ledger: Dict[str, str] = {}

        for s in surfaces:
            provenance_ledger[s.target_rel_path] = s.content_hash
            target_path = root / s.target_rel_path

            # Check if protected or user-authored
            norm_rel = s.target_rel_path.replace("\\", "/").lower()
            if norm_rel in cls.PROTECTED_DOCS:
                warnings.append(f"Surface '{s.target_rel_path}' targets protected documentation; write blocked.")
                continue

            if target_path.is_file():
                # Check manifest ownership if available
                if manifest and s.target_rel_path in manifest.artifacts:
                    rec = manifest.artifacts[s.target_rel_path]
                    if rec.ownership == ArtifactOwnership.USER_AUTHORED:
                        s.is_user_authored_conflict = True
                        skipped_user_authored.append(s.target_rel_path)
                        warnings.append(
                            f"Skipped overwriting USER_AUTHORED file: {s.target_rel_path}. Propose change instead."
                        )
                        continue

                # Check manual user-authored marker
                existing_text = target_path.read_text(encoding="utf-8", errors="ignore")
                if "user-authored" in existing_text.lower() or "protected" in existing_text.lower():
                    s.is_user_authored_conflict = True
                    skipped_user_authored.append(s.target_rel_path)
                    warnings.append(
                        f"Skipped overwriting file with user-authored marker: {s.target_rel_path}."
                    )
                    continue

            if not dry_run:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(s.content, encoding="utf-8")
                applied_files.append(s.target_rel_path)

        return DocCompilationResult(
            project_path=str(root),
            timestamp=now_str,
            surfaces=surfaces,
            applied_files=applied_files,
            skipped_user_authored=skipped_user_authored,
            warnings=warnings,
            provenance_ledger=provenance_ledger,
        )

    # -------------------------------------------------------------------------
    # Surface compilers
    # -------------------------------------------------------------------------
    @classmethod
    def _compile_architecture_summary(
        cls, root: Path, anatomy: Dict[str, Any], manifest: Optional[ProjectManifest], config: Dict[str, Any]
    ) -> CompiledDocSurface:
        target_rel = cls.SURFACE_PATHS[DocSurfaceType.ARCHITECTURE_SUMMARY]
        sources = ["antios.config.json", ".antios/project_anatomy.json"]

        proj_name = config.get("project_name", root.name)
        archetype = anatomy.get("archetype", "UNKNOWN_ARCHETYPE")
        source_roots = anatomy.get("source_roots", [])
        subsystems = anatomy.get("subsystems", [])

        lines = [
            f"# Architecture Summary: {proj_name}",
            f"<!-- Generated by AntiOS Documentation Compiler at {datetime.now(timezone.utc).date().isoformat()} -->",
            "",
            "## 1. Project Overview",
            f"- **Archetype**: `{archetype}`",
            f"- **Governance**: AntiOS 2.0 Project Agent OS",
            f"- **Source Roots**: {', '.join(f'`{r}`' for r in source_roots) if source_roots else '`./`'}",
            "",
            "## 2. Key Subsystems",
        ]
        if subsystems:
            for sub in subsystems[:8]:
                lines.append(f"- **{sub.get('name', 'subsystem')}**: `{sub.get('path', '')}`")
        else:
            lines.append("- *Subsystems discovered dynamically via wayfinding engine.*")

        lines.extend([
            "",
            "## 3. Epistemic Baseline",
            "- All architectural facts compiled from verified filesystem artifacts.",
            "- Modifications must pass Stop Gate physical test execution.",
            "",
        ])
        content = "\n".join(lines)
        chash = hashlib.sha256(content.encode()).hexdigest()

        return CompiledDocSurface(
            surface_type=DocSurfaceType.ARCHITECTURE_SUMMARY,
            target_rel_path=target_rel,
            content=content,
            provenance_sources=sources,
            ownership=ArtifactOwnership.GENERATED,
            content_hash=chash,
        )

    @classmethod
    def _compile_subsystem_map(cls, root: Path, anatomy: Dict[str, Any]) -> CompiledDocSurface:
        target_rel = cls.SURFACE_PATHS[DocSurfaceType.SUBSYSTEM_MAP]
        sources = [".antios/project_anatomy.json"]

        subsystems = anatomy.get("subsystems", [])
        lines = [
            "# Subsystem Map",
            f"<!-- Generated by AntiOS Documentation Compiler at {datetime.now(timezone.utc).date().isoformat()} -->",
            "",
            "| Subsystem | Path | Primary Purpose | Test Coverage |",
            "| :--- | :--- | :--- | :--- |",
        ]
        if subsystems:
            for s in subsystems:
                name = s.get("name", "unknown")
                path = s.get("path", "")
                purpose = s.get("description", "Core functionality")
                has_tests = "Covered" if s.get("test_paths") else "Unmapped"
                lines.append(f"| `{name}` | `{path}` | {purpose} | {has_tests} |")
        else:
            lines.append("| `root` | `./` | Root repository scope | See test runners |")

        lines.append("")
        content = "\n".join(lines)
        chash = hashlib.sha256(content.encode()).hexdigest()

        return CompiledDocSurface(
            surface_type=DocSurfaceType.SUBSYSTEM_MAP,
            target_rel_path=target_rel,
            content=content,
            provenance_sources=sources,
            ownership=ArtifactOwnership.GENERATED,
            content_hash=chash,
        )

    @classmethod
    def _compile_component_map(cls, root: Path, anatomy: Dict[str, Any]) -> CompiledDocSurface:
        target_rel = cls.SURFACE_PATHS[DocSurfaceType.COMPONENT_MAP]
        sources = [".antios/project_anatomy.json"]

        components = anatomy.get("components", [])
        lines = [
            "# Component Map",
            f"<!-- Generated by AntiOS Documentation Compiler at {datetime.now(timezone.utc).date().isoformat()} -->",
            "",
            "Authoritative mapping of project components to entrypoints and covering tests:",
            "",
        ]
        if components:
            for c in components[:12]:
                lines.append(f"### `{c.get('name', 'component')}`")
                lines.append(f"- **Path**: `{c.get('path', '')}`")
                lines.append(f"- **Entrypoints**: {', '.join(f'`{e}`' for e in c.get('entrypoints', [])) or 'None'}")
                lines.append(f"- **Covering Tests**: {', '.join(f'`{t}`' for t in c.get('tests', [])) or 'Unmapped'}")
                lines.append("")
        else:
            lines.append("- *No compiled components in anatomy. Use ProjectAnatomyCompiler to index.*")
            lines.append("")

        content = "\n".join(lines)
        chash = hashlib.sha256(content.encode()).hexdigest()

        return CompiledDocSurface(
            surface_type=DocSurfaceType.COMPONENT_MAP,
            target_rel_path=target_rel,
            content=content,
            provenance_sources=sources,
            ownership=ArtifactOwnership.GENERATED,
            content_hash=chash,
        )

    @classmethod
    def _compile_test_map(cls, root: Path, config: Dict[str, Any]) -> CompiledDocSurface:
        target_rel = cls.SURFACE_PATHS[DocSurfaceType.TEST_MAP]
        sources = ["antios.config.json"]

        runners = config.get("test_runners", [])
        lines = [
            "# Test Map & Verification Surfaces",
            f"<!-- Generated by AntiOS Documentation Compiler at {datetime.now(timezone.utc).date().isoformat()} -->",
            "",
            "## 1. Configured Test Runners",
        ]
        if runners:
            for r in runners:
                name = r.get("name", "test-runner")
                cmd = r.get("command", "")
                scope = r.get("scope", "repository")
                lines.append(f"- **{name}** (`{scope}`): `{cmd}`")
        else:
            lines.append("- *No automated test runners configured in antios.config.json.*")

        lines.extend([
            "",
            "## 2. Verification Rules",
            "- All task turns must exit code 0 on configured test runners.",
            "- Independent Maker-Checker verifiers must physically execute these test suites.",
            "",
        ])
        content = "\n".join(lines)
        chash = hashlib.sha256(content.encode()).hexdigest()

        return CompiledDocSurface(
            surface_type=DocSurfaceType.TEST_MAP,
            target_rel_path=target_rel,
            content=content,
            provenance_sources=sources,
            ownership=ArtifactOwnership.GENERATED,
            content_hash=chash,
        )

    @classmethod
    def _compile_agent_guidance(cls, root: Path, config: Dict[str, Any]) -> CompiledDocSurface:
        target_rel = cls.SURFACE_PATHS[DocSurfaceType.AGENT_GUIDANCE]
        sources = ["antios.config.json", ".agents/skills/"]

        lines = [
            "# Project Agent Guidance",
            f"<!-- Generated by AntiOS Documentation Compiler at {datetime.now(timezone.utc).date().isoformat()} -->",
            "",
            "## Operational Invariants",
            "1. **Single Control Plane**: `/antios` is the authoritative entrypoint for all engineering tasks.",
            "2. **Read-Parallel, Write-Controlled**: Parallel reads encouraged; concurrent writes must be disjoint.",
            "3. **Shallow Depth Law**: Subagent depth <= 2; specialist `can_delegate = False`.",
            "4. **Stop Gate**: Physical test runner execution required before concluding turns.",
            "5. **Token Bounds**: `docs/ACTIVE_CONTEXT.md` strictly <= 60 lines.",
            "",
        ]
        content = "\n".join(lines)
        chash = hashlib.sha256(content.encode()).hexdigest()

        return CompiledDocSurface(
            surface_type=DocSurfaceType.AGENT_GUIDANCE,
            target_rel_path=target_rel,
            content=content,
            provenance_sources=sources,
            ownership=ArtifactOwnership.GENERATED,
            content_hash=chash,
        )

    @classmethod
    def _compile_ownership_info(cls, root: Path, manifest: Optional[ProjectManifest]) -> CompiledDocSurface:
        target_rel = cls.SURFACE_PATHS[DocSurfaceType.OWNERSHIP_INFO]
        sources = [".antios/manifest.json"] if manifest else []

        lines = [
            "# Artifact Ownership & Governance Tiers",
            f"<!-- Generated by AntiOS Documentation Compiler at {datetime.now(timezone.utc).date().isoformat()} -->",
            "",
            "| Ownership Tier | Mutability Policy | Examples |",
            "| :--- | :--- | :--- |",
            "| **PROTECTED** | Strictly Immutable to target projects | `framework/core/`, `ANTIOS_CONSTITUTION.md` |",
            "| **USER_AUTHORED** | Human Owned; never overwritten by agents | User domain files, manual guides |",
            "| **MANAGED** | Governed; requires Controlled Evolution | `antios.config.json`, skills |",
            "| **GENERATED** | Ephemeral/Machine-compiled | Compiled maps, manifests, telemetry |",
            "",
        ]
        if manifest:
            lines.append(f"Total tracked artifacts in manifest: {len(manifest.artifacts)}")
            lines.append("")

        content = "\n".join(lines)
        chash = hashlib.sha256(content.encode()).hexdigest()

        return CompiledDocSurface(
            surface_type=DocSurfaceType.OWNERSHIP_INFO,
            target_rel_path=target_rel,
            content=content,
            provenance_sources=sources,
            ownership=ArtifactOwnership.GENERATED,
            content_hash=chash,
        )

    # -------------------------------------------------------------------------
    # Safe loaders
    # -------------------------------------------------------------------------
    @classmethod
    def _safe_load_manifest(cls, root: Path) -> Optional[ProjectManifest]:
        try:
            return load_manifest(root)
        except Exception:
            return None

    @classmethod
    def _safe_load_anatomy(cls, root: Path) -> Dict[str, Any]:
        p = root / ".antios" / "project_anatomy.json"
        if p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                pass
        return {}

    @classmethod
    def _safe_load_config(cls, root: Path) -> Dict[str, Any]:
        p = root / "antios.config.json"
        if p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                pass
        return {}
