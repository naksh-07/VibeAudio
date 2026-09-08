"""
AntiOS 3.0 Project Environment Compiler — Core Orchestrator & Public API

Main entrypoint for static compilation of arbitrary repositories into compact, deterministic,
agent-native project environments.
Zero third-party dependencies, standard library only.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ast_extractor import ASTSymbolExtractor, FileSymbolOutline
from .emit import ArtifactEmitter, EmissionRecord
from .project_model import ProjectInspector, ProjectModel
from .routes import RouteMapGenerator


@dataclass
class CompilationResult:
    success: bool
    project_id: str
    emitted_files: List[str] = field(default_factory=list)
    records: List[EmissionRecord] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    elapsed_ms: float = 0.0
    subsystems_count: int = 0
    agents_md_lines: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "project_id": self.project_id,
            "emitted_files": sorted(self.emitted_files),
            "warnings": self.warnings,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "subsystems_count": self.subsystems_count,
            "agents_md_lines": self.agents_md_lines,
        }


class ProjectEnvironmentCompiler:
    """
    Static compiler that transforms an arbitrary target repository into an
    Agent-Native Project Environment.
    """

    def __init__(self, max_discovery_depth: int = 4):
        self.max_discovery_depth = max_discovery_depth

    def compile(
        self,
        project_root: str | Path,
        check: bool = False,
        force: bool = False,
    ) -> CompilationResult:
        """
        Compile target repository into canonical .agents/ environment.
        - check: When True, performs dry-run validation without writing files.
        - force: When True, overwrites existing user-authored files without conflict fallback.
        """
        start_time = time.perf_counter()
        root = Path(project_root).resolve()
        warnings: List[str] = []

        if not root.is_dir():
            return CompilationResult(
                success=False,
                project_id="unknown",
                warnings=[f"Target path does not exist or is not a directory: {project_root}"],
                elapsed_ms=0.0,
            )

        # 1. Project Discovery & Modeling
        inspector = ProjectInspector(repo_root=root, max_depth=self.max_discovery_depth)
        model = inspector.inspect()

        # 2. Subsystem Route Map Generation
        route_gen = RouteMapGenerator(project_model=model)
        routes_doc = route_gen.generate()

        # 3. AST Outline Extraction for Key Subsystem Files
        ast_outlines: Dict[str, Any] = {
            "$schema": "https://antios.dev/schemas/v3/ast_outlines.json",
            "version": "3.0.0",
            "files": {},
        }

        subsystems = routes_doc.get("subsystems", {})
        for sub_name, sub_info in sorted(subsystems.items()):
            ep = sub_info.get("entrypoint")
            if ep and ep.endswith(".py"):
                ep_file = root / ep
                if ep_file.is_file():
                    outline = ASTSymbolExtractor.extract_file(ep_file, ep)
                    ast_outlines["files"][ep] = outline.to_dict()

        # Also extract outlines for probable entrypoints
        for prob_ep in sorted(model.probable_entrypoints):
            if prob_ep.endswith(".py") and prob_ep not in ast_outlines["files"]:
                ep_file = root / prob_ep
                if ep_file.is_file():
                    outline = ASTSymbolExtractor.extract_file(ep_file, prob_ep)
                    ast_outlines["files"][prob_ep] = outline.to_dict()

        # 4. Safe Emission
        emitter = ArtifactEmitter(project_root=root, check_mode=check, force=force)

        # Emit .agents/routes.json
        r_rec = emitter.emit_json(".agents/routes.json", routes_doc)
        if r_rec.warning:
            warnings.append(r_rec.warning)

        # Emit .agents/cache/ast_outlines.json
        ast_rec = emitter.emit_json(".agents/cache/ast_outlines.json", ast_outlines)
        if ast_rec.warning:
            warnings.append(ast_rec.warning)

        # Emit Turn-0 AGENTS.md
        md_rec, md_content = emitter.emit_agents_md(model, routes_doc)
        if md_rec.warning:
            warnings.append(md_rec.warning)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        emitted_paths = [rec.path for rec in emitter.records if rec.action != "failed"]

        return CompilationResult(
            success=all(r.action != "failed" for r in emitter.records),
            project_id=model.project_id,
            emitted_files=emitted_paths,
            records=emitter.records,
            warnings=warnings,
            elapsed_ms=elapsed_ms,
            subsystems_count=len(subsystems),
            agents_md_lines=len(md_content.strip().split("\n")),
        )


def compile_project(
    project_root: str | Path,
    check: bool = False,
    force: bool = False,
) -> CompilationResult:
    """Convenience function to compile a project environment."""
    compiler = ProjectEnvironmentCompiler()
    return compiler.compile(project_root=project_root, check=check, force=force)
