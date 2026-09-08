"""AntiOS 2.0 Project Boundary Compiler.

Compiles AntiOS Source into a target Project Agent OS Instance (.antios/).
Does NOT blindly copy the AntiOS repository into the target project.
Distinguishes:
- UNIVERSAL CORE: Reference policies and immutable governance contracts
- PROJECT ADAPTER: antios.config.json
- GENERATED PROJECT INTELLIGENCE: .antios/ (profile, knowledge, topology, tool policy)
- ANTIGRAVITY-FACING ASSETS: .agents/skills/antios/SKILL.md, .agents/hooks.json
- HISTORICAL / DEVELOPMENT MATERIAL: Strictly excluded from installation

Preserves the universal-core boundary; target instance never becomes a
forked copy of AntiOS internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from framework.core.adapter import generate_adapter_config
from framework.core.anatomy import ProjectAnatomy, ProjectAnatomyCompiler
from framework.core.config import AntiOSConfig, load_config
from framework.core.discovery import discover_project
from framework.core.manifest import (
    AdaptationState,
    ArtifactOwnership,
    ArtifactRecord,
    CURRENT_ANTIOS_VERSION,
    CURRENT_SCHEMA_VERSION,
    InstallationState,
    ProjectManifest,
)
from framework.core.profile import ProjectProfile
from framework.core.provenance import can_safely_overwrite, compute_file_sha256
from framework.core.skill_generator import SkillGenerator
from framework.core.specialist_generator import SpecialistGenerator


@dataclass
class CompilationResult:
    """Outcome of the Project Boundary Compilation."""
    manifest: ProjectManifest
    compiled_files: Dict[str, str] = field(default_factory=dict)  # rel_path -> file content
    skipped_files: Dict[str, str] = field(default_factory=dict)   # rel_path -> reason
    conflicts: List[str] = field(default_factory=list)
    success: bool = True
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "summary": self.summary,
            "manifest": self.manifest.to_dict(),
            "compiled_files": list(self.compiled_files.keys()),
            "skipped_files": self.skipped_files,
            "conflicts": self.conflicts,
        }


class ProjectBoundaryCompiler:
    """Compiles AntiOS Source intelligence into a target Project Agent OS Instance."""

    def __init__(
        self,
        source_root: Union[str, Path],
        target_root: Union[str, Path],
        source_revision: str = "v2.0.0",
    ):
        self.source_root = Path(source_root).resolve()
        self.target_root = Path(target_root).resolve()
        self.source_revision = source_revision

    def compile(
        self,
        existing_manifest: Optional[ProjectManifest] = None,
        profile_override: Optional[ProjectProfile] = None,
        config_override: Optional[AntiOSConfig] = None,
    ) -> CompilationResult:
        """Executes boundary compilation, generating files and manifest in memory."""
        conflicts: List[str] = []
        skipped_files: Dict[str, str] = {}
        compiled_files: Dict[str, str] = {}

        # 1. Discover target project traits
        profile = profile_override or discover_project(str(self.target_root))
        project_fingerprint = profile.manifest_fingerprint
        if not project_fingerprint:
            # Deterministic fallback for repos with no package manifests
            project_fingerprint = hashlib.sha256(f"manifestless:{self.target_root.name}".encode("utf-8")).hexdigest()

        # 2. Derive adapter configuration
        config_path = self.target_root / "antios.config.json"
        if config_override:
            adapter_config = config_override
        elif config_path.is_file():
            adapter_config = load_config(str(self.target_root))
        else:
            from framework.core.adapter import analyze_adaptation, generate_adapter_config
            proposal = analyze_adaptation(profile)
            adapter_config = generate_adapter_config(profile, proposal)

        # Ensure core protected zones exist in config (.agents and .antios)
        for zone in [".agents", ".antios"]:
            if zone not in adapter_config.protected_zones:
                adapter_config.protected_zones.append(zone)

        # Protect framework only when compiling within the AntiOS source repository itself
        if self.target_root == self.source_root and "framework" not in adapter_config.protected_zones:
            adapter_config.protected_zones.append("framework")

        # 3. Compile Project Profile (.antios/project_profile.json)
        profile_content = json.dumps(profile.to_dict(), indent=2)
        compiled_files[".antios/project_profile.json"] = profile_content

        # 3b. Compile Project Anatomy (.antios/project_anatomy.json) [Phase 55]
        anatomy = ProjectAnatomyCompiler(self.target_root).compile(profile=profile)
        compiled_files[".antios/project_anatomy.json"] = anatomy.to_json()

        # 4. Compile Knowledge Graph (.antios/knowledge.json)
        top = getattr(profile, "topology", None) or getattr(profile, "workspace_topology", None)
        top_str = top.value if hasattr(top, "value") else (str(top) if top else "STANDALONE")
        knowledge_data = {
            "project_identity": profile.identity.to_dict(),
            "workspace_topology": top_str,
            "subsystems": [s.to_dict() if hasattr(s, "to_dict") else s for s in profile.subsystems],
            "workspace_members": [m.to_dict() if hasattr(m, "to_dict") else m for m in profile.workspace_members],
            "risk_zones": list(profile.risk_zones),
            "protected_paths": list(profile.protected_paths),
            "protected_domain_paths": list(adapter_config.protected_domain_paths),
            "manifest_fingerprint": project_fingerprint,
        }
        compiled_files[".antios/knowledge.json"] = json.dumps(knowledge_data, indent=2)

        # 5. Compile Agent Topology (.antios/agent_topology.json) [Phase 58]
        specialist_roles = SpecialistGenerator.evaluate_specialist_justification(
            anatomy=anatomy,
            subsystems=profile.subsystems,
        )
        topology_data = SpecialistGenerator.compile_topology_json(
            roles=specialist_roles,
            project_name=profile.identity.name or "Target-Project",
        )
        compiled_files[".antios/agent_topology.json"] = json.dumps(topology_data, indent=2)

        # 6. Compile Tool Policy (.antios/tool_policy.json)
        from dataclasses import asdict
        runners_list = []
        for r in adapter_config.test_runners:
            if hasattr(r, "to_dict"):
                runners_list.append(r.to_dict())
            elif hasattr(r, "__dataclass_fields__"):
                runners_list.append(asdict(r))
            else:
                runners_list.append(r)

        tool_data = {
            "tier_preference": ["NATIVE", "SCRIPT", "PROJECT", "EXTERNAL", "SERVICE", "MCP"],
            "configured_runners": runners_list,
            "linters": getattr(adapter_config, "linters", []),
            "policies": asdict(adapter_config.policies) if hasattr(adapter_config.policies, "__dataclass_fields__") else {},
        }
        compiled_files[".antios/tool_policy.json"] = json.dumps(tool_data, indent=2)

        # 7. Compile antios.config.json
        config_dict = asdict(adapter_config) if hasattr(adapter_config, "__dataclass_fields__") else adapter_config.to_dict()
        config_content = json.dumps(config_dict, indent=2)
        compiled_files["antios.config.json"] = config_content

        # 8. Compile .agents/skills/antios/SKILL.md & project-specific skills [Phases 57, 82]
        template_skill_path = self.source_root / "framework/templates/skills/antios/SKILL.md"
        if template_skill_path.is_file():
            main_skill_content = template_skill_path.read_text(encoding="utf-8")
        else:
            main_skill_content = SkillGenerator.compile_main_skill(anatomy)
        compiled_files[".agents/skills/antios/SKILL.md"] = main_skill_content

        # Evidence-driven specialist skill generation
        existing_skills = list(anatomy.existing_agents_structure.get("skills", []))
        skill_specs = SkillGenerator.evaluate_skill_justification(anatomy, existing_skills=existing_skills)
        generated_skill_paths: List[str] = []
        for spec in skill_specs:
            sp = f".agents/skills/{spec.name}/SKILL.md"
            compiled_files[sp] = SkillGenerator.generate_skill_content(spec, anatomy)
            generated_skill_paths.append(sp)

        # 9. Compile .antios/runtime/ assets & .agents/hooks.json [Phases 80–81]
        runtime_dir = self.source_root / "framework/templates/runtime"
        runtime_script_names = [
            "pre_tool_guard.py",
            "stop_gate.py",
            "inspect_instance.py",
            "verify_runtime.py",
        ]
        for sname in runtime_script_names:
            src_script = runtime_dir / sname
            if src_script.is_file():
                compiled_files[f".antios/runtime/{sname}"] = src_script.read_text(encoding="utf-8")

        hooks_data = {
            "antios-guard": {
                "PreToolUse": [
                    {
                        "matcher": "write_to_file|replace_file_content",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "python .antios/runtime/pre_tool_guard.py"
                            }
                        ]
                    }
                ],
                "Stop": [
                    {
                        "type": "command",
                        "command": "python .antios/runtime/stop_gate.py"
                    }
                ]
            }
        }
        compiled_files[".agents/hooks.json"] = json.dumps(hooks_data, indent=2)

        # Phase 59: Zero Legacy Workflows Invariant
        # Ensure compiled_files never contains .agents/workflows/
        for p in list(compiled_files.keys()):
            if p.startswith(".agents/workflows"):
                del compiled_files[p]

        # Phase 61-66: Project Learning Stores
        compiled_files[".antios/learning_observations.json"] = json.dumps({
            "schema_version": "2.0.0",
            "total_observations": 0,
            "observations": [],
        }, indent=2)
        compiled_files[".antios/learning_proposals.json"] = json.dumps({
            "schema_version": "2.0.0",
            "total_proposals": 0,
            "proposals": [],
        }, indent=2)

        # 10. Build Artifact Records & Project Manifest
        now_ts = datetime.now(timezone.utc).isoformat()
        managed_paths: Dict[str, ArtifactRecord] = {}
        generated_paths: Dict[str, ArtifactRecord] = {}

        # Managed paths (adapter configuration & hooks)
        managed_keys = {"antios.config.json", ".agents/hooks.json"}
        for k in managed_keys:
            if k in compiled_files:
                content = compiled_files[k]
                sha = hashlib.sha256(content.replace("\r\n", "\n").encode("utf-8")).hexdigest()
                managed_paths[k] = ArtifactRecord(
                    path=k,
                    ownership=ArtifactOwnership.MANAGED,
                    sha256=sha,
                    source_revision=self.source_revision,
                    generated_at=now_ts,
                    source_template=k,
                )

        # Generated paths (intelligence, runtime scripts, and operating skills)
        generated_keys = {
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
        }
        for gsp in generated_skill_paths:
            generated_keys.add(gsp)

        for k in generated_keys:
            if k in compiled_files:
                content = compiled_files[k]
                sha = hashlib.sha256(content.replace("\r\n", "\n").encode("utf-8")).hexdigest()
                generated_paths[k] = ArtifactRecord(
                    path=k,
                    ownership=ArtifactOwnership.GENERATED,
                    sha256=sha,
                    source_revision=self.source_revision,
                    generated_at=now_ts,
                )

        # Protected paths from adapter config
        protected_paths = list(adapter_config.protected_zones) + list(adapter_config.protected_domain_paths)
        if ".antios" not in protected_paths:
            protected_paths.append(".antios")

        # Preserve user owned paths from existing manifest if present
        user_owned: List[str] = []
        if existing_manifest:
            user_owned = list(existing_manifest.user_owned_paths)

        manifest = ProjectManifest(
            antios_version=CURRENT_ANTIOS_VERSION,
            schema_version=CURRENT_SCHEMA_VERSION,
            project_fingerprint=project_fingerprint,
            source_revision=self.source_revision,
            generated_at=now_ts,
            adaptation_state=AdaptationState.ADAPTED,
            installation_state=InstallationState.INSTALLED,
            managed_paths=managed_paths,
            generated_paths=generated_paths,
            user_owned_paths=user_owned,
            protected_paths=protected_paths,
            stale_paths=[],
            project_profile_reference=".antios/project_profile.json",
        )

        # Add manifest itself to compiled files
        compiled_files[".antios/manifest.json"] = manifest.to_json(indent=2)

        return CompilationResult(
            manifest=manifest,
            compiled_files=compiled_files,
            skipped_files=skipped_files,
            conflicts=conflicts,
            success=len(conflicts) == 0,
            summary=f"Compiled AntiOS 2.0 instance ({len(compiled_files)} artifacts prepared).",
        )

    def emit(
        self,
        result: CompilationResult,
        existing_manifest: Optional[ProjectManifest] = None,
        dry_run: bool = False,
    ) -> Tuple[bool, List[str], List[str]]:
        """Emits compiled files to target root respecting artifact ownership.

        Returns:
            (success, written_paths, conflict_errors)
        """
        written_paths: List[str] = []
        conflict_errors: List[str] = []

        for rel_path, content in result.compiled_files.items():
            content_sha = hashlib.sha256(content.replace("\r\n", "\n").encode("utf-8")).hexdigest()
            can_overwrite, reason = can_safely_overwrite(
                rel_path=rel_path,
                manifest=existing_manifest,
                target_root=self.target_root,
                proposed_content_sha=content_sha,
            )

            if not can_overwrite:
                conflict_errors.append(f"Refused to write '{rel_path}': {reason}")
                continue

            if not dry_run:
                target_file = self.target_root / rel_path
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_text(content, encoding="utf-8", newline="\n")
            written_paths.append(rel_path)

        success = len(conflict_errors) == 0
        return success, written_paths, conflict_errors
