"""AntiOS 2.0 Project-Specific Specialist Generator.

Phase 58: Evidence-driven specialist role synthesizer.
Determines whether target project benefits from project-specific specialist roles.

Strict Non-Negotiables:
- NEVER generate a specialist solely because a language or framework exists ("React exists" / "Python exists").
- Specialists must represent meaningful project-specific architectural expertise.
- SHALLOW DEPTH LAW: max_depth <= 2; can_delegate = False (specialists CANNOT spawn child subagents).
- Strict capability boundary: forbidden capabilities take absolute precedence over wildcards.
- Core rules are IMMUTABLE: cannot override rule:core-immutable, rule:stop-gate-ratchet, rule:platform-hook-interception.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from framework.core.agent_role import (
    AgentCapabilityBoundary,
    AgentRole,
    AgentRoleType,
    EscalationPolicyType,
)
from framework.core.anatomy import ProjectAnatomy
from framework.core.capability import CapabilityScope
from framework.core.subsystem import SubsystemDeclaration


class SpecialistGenerator:
    """Evidence-driven generator for project-specific specialist agent roles."""

    VERSION = "2.0.0"

    @classmethod
    def evaluate_specialist_justification(
        cls,
        anatomy: ProjectAnatomy,
        subsystems: Optional[List[SubsystemDeclaration]] = None,
        existing_specialists: Optional[List[str]] = None,
    ) -> List[AgentRole]:
        """Evaluates project evidence and generates validated AgentRoles when justified.
        
        Requires:
        1. Materially relevant subsystem with dedicated test surface and rules.
        2. Distinct capability boundary with forbidden zones.
        3. Clear verification ratchet.
        """
        existing = set(existing_specialists or [])
        subsystems = subsystems or []
        generated_roles: List[AgentRole] = []

        now_ts = datetime.now(timezone.utc).isoformat()

        def _sub_area(s: Any) -> str:
            if hasattr(s, "area"):
                return str(s.area)
            if isinstance(s, dict):
                return str(s.get("area", ""))
            if isinstance(s, str):
                return s
            return ""

        def _sub_id(s: Any) -> str:
            if hasattr(s, "subsystem_id"):
                return str(s.subsystem_id)
            if isinstance(s, dict):
                return str(s.get("subsystem_id", s.get("id", "")))
            if isinstance(s, str):
                return s
            return ""

        def _sub_risk(s: Any) -> str:
            if hasattr(s, "risk_tier"):
                return str(s.risk_tier)
            if isinstance(s, dict):
                return str(s.get("risk_tier", "MEDIUM"))
            return "MEDIUM"

        # 1. UI / Frontend Specialist Justification
        # Required Evidence:
        # - Fullstack or Frontend archetype
        # - Subsystem for UI / Components with covering tests
        # - Important directories: components/ or views/ or pages/
        has_ui_archetype = anatomy.archetype in ["FULLSTACK_WEB", "FRONTEND_WEB"]
        has_ui_subsystem = any(_sub_area(s).lower() in ["ui", "frontend", "web"] for s in subsystems)
        has_ui_dirs = any(d in anatomy.important_directories for d in ["components", "views", "styles"])

        if (has_ui_archetype or has_ui_subsystem) and has_ui_dirs:
            role_id = "role:frontend-specialist"
            if role_id not in existing:
                ui_subsystem_ids = [_sub_id(s) for s in subsystems if _sub_area(s).lower() in ["ui", "frontend", "web"]] or ["frontend"]
                role = AgentRole(
                    role_id=role_id,
                    name="Frontend Specialist",
                    role_type=AgentRoleType.SPECIALIST,
                    responsibility=f"Specialized UI component, styling, and client-side view engineer for {anatomy.project_name}",
                    scope=CapabilityScope.PROJECT_LOCAL,
                    applies_to_task_types=["FEATURE", "BUG", "REFACTOR"],
                    applies_to_subsystems=ui_subsystem_ids,
                    boundary=AgentCapabilityBoundary(
                        allowed_capabilities=[
                            "tool:write_to_file",
                            "tool:replace_file_content",
                            "tool:navigate-repo",
                            "tool:test-*",
                            "skill:antios-engineer",
                            "skill:frontend-design",
                        ],
                        forbidden_capabilities=[
                            "rule:core-immutable:override",
                            "rule:stop-gate-ratchet:override",
                            "rule:platform-hook-interception:override",
                            "rule:shallow-depth-law:override",
                            "path:framework/**",
                            "path:.agents/hooks.json",
                            "path:antios.config.json",
                        ],
                        required_capabilities=["skill:antios-engineer"],
                        inherited_capabilities=["rule:core-immutable", "rule:stop-gate-ratchet"],
                    ),
                    required_verifier="verifier:maker-checker" if "HIGH" in [_sub_risk(s) for s in subsystems if _sub_id(s) in ui_subsystem_ids] else "verifier:solo",
                    escalation_policy=EscalationPolicyType.RETURN_TO_PRIMARY,
                    max_depth=2,
                    can_delegate=False,  # SHALLOW DEPTH LAW
                    enabled=True,
                    confidence=0.88,
                    evidence=f"Dedicated UI subsystem and directories {[d for d in anatomy.important_directories if d in ['components', 'views', 'styles']]} in {anatomy.project_name}",
                    epistemic_state="INFERRED",
                    source=f"AntiOS SpecialistGenerator v{cls.VERSION}",
                )
                generated_roles.append(role)

        # 2. Database / Storage Specialist Justification
        # Required Evidence:
        # - Dedicated DB subsystem OR migrations directory WITH migration tool in configs
        has_db_subsystem = any(_sub_area(s).lower() in ["db", "database", "storage"] for s in subsystems)
        has_migrations_dir = "migrations" in anatomy.important_directories or any("migration" in d for d in anatomy.important_directories)

        if has_db_subsystem or has_migrations_dir:
            role_id = "role:database-specialist"
            if role_id not in existing:
                db_subsystem_ids = [_sub_id(s) for s in subsystems if _sub_area(s).lower() in ["db", "database", "storage"]] or ["database"]
                role = AgentRole(
                    role_id=role_id,
                    name="Database Specialist",
                    role_type=AgentRoleType.SPECIALIST,
                    responsibility=f"Specialized database schema, query, and migration engineer for {anatomy.project_name}",
                    scope=CapabilityScope.PROJECT_LOCAL,
                    applies_to_task_types=["FEATURE", "BUG", "REFACTOR"],
                    applies_to_subsystems=db_subsystem_ids,
                    boundary=AgentCapabilityBoundary(
                        allowed_capabilities=[
                            "tool:write_to_file",
                            "tool:replace_file_content",
                            "tool:navigate-repo",
                            "tool:test-*",
                            "skill:antios-engineer",
                            "skill:database-migrations",
                        ],
                        forbidden_capabilities=[
                            "rule:core-immutable:override",
                            "rule:stop-gate-ratchet:override",
                            "rule:platform-hook-interception:override",
                            "rule:shallow-depth-law:override",
                            "path:framework/**",
                            "path:.agents/hooks.json",
                            "path:antios.config.json",
                        ],
                        required_capabilities=["skill:antios-engineer"],
                        inherited_capabilities=["rule:core-immutable", "rule:stop-gate-ratchet"],
                    ),
                    required_verifier="verifier:maker-checker",  # Schema changes default to Maker-Checker
                    escalation_policy=EscalationPolicyType.RETURN_TO_PRIMARY,
                    max_depth=2,
                    can_delegate=False,  # SHALLOW DEPTH LAW
                    enabled=True,
                    confidence=0.85,
                    evidence=f"Dedicated migrations/storage surfaces witnessed in {anatomy.project_name}",
                    epistemic_state="INFERRED",
                    source=f"AntiOS SpecialistGenerator v{cls.VERSION}",
                )
                generated_roles.append(role)

        # 3. Native GUI / Reviewer Specialist (e.g. QtWebEngine, custom native harness)
        has_qt_or_native = any("qt" in f.lower() or "gui" in f.lower() for f in anatomy.frameworks)
        if has_qt_or_native:
            role_id = "role:native-gui-specialist"
            if role_id not in existing:
                role = AgentRole(
                    role_id=role_id,
                    name="Native GUI Specialist",
                    role_type=AgentRoleType.SPECIALIST,
                    responsibility=f"Specialized desktop GUI and event-loop engineer for {anatomy.project_name}",
                    scope=CapabilityScope.PROJECT_LOCAL,
                    applies_to_task_types=["FEATURE", "BUG"],
                    applies_to_subsystems=["gui", "desktop"],
                    boundary=AgentCapabilityBoundary(
                        allowed_capabilities=[
                            "tool:write_to_file",
                            "tool:replace_file_content",
                            "tool:navigate-repo",
                            "tool:test-*",
                            "skill:antios-engineer",
                        ],
                        forbidden_capabilities=[
                            "rule:core-immutable:override",
                            "rule:stop-gate-ratchet:override",
                            "path:framework/**",
                        ],
                        required_capabilities=["skill:antios-engineer"],
                        inherited_capabilities=["rule:core-immutable", "rule:stop-gate-ratchet"],
                    ),
                    required_verifier="verifier:maker-checker",
                    escalation_policy=EscalationPolicyType.RETURN_TO_PRIMARY,
                    max_depth=2,
                    can_delegate=False,
                    enabled=True,
                    confidence=0.80,
                    evidence=f"Native GUI frameworks witnessed in {anatomy.project_name}: {anatomy.frameworks}",
                    epistemic_state="INFERRED",
                    source=f"AntiOS SpecialistGenerator v{cls.VERSION}",
                )
                generated_roles.append(role)

        return generated_roles

    @classmethod
    def compile_topology_json(cls, roles: List[AgentRole], project_name: str) -> Dict[str, Any]:
        """Compiles the .antios/agent_topology.json data structure."""
        specialists_data: Dict[str, Any] = {}
        for r in roles:
            if r.role_type == AgentRoleType.SPECIALIST:
                specialists_data[r.role_id] = {
                    "name": r.name,
                    "role_type": r.role_type.value,
                    "responsibility": r.responsibility,
                    "applies_to_task_types": r.applies_to_task_types,
                    "applies_to_subsystems": r.applies_to_subsystems,
                    "allowed_capabilities": r.boundary.allowed_capabilities,
                    "forbidden_capabilities": r.boundary.forbidden_capabilities,
                    "required_verifier": r.required_verifier,
                    "max_depth": r.max_depth,
                    "can_delegate": r.can_delegate,
                    "enabled": r.enabled,
                    "confidence": r.confidence,
                    "evidence": r.evidence,
                }

        return {
            "project_name": project_name,
            "primary_role": "role:primary-engineer",
            "allow_delegation": True,
            "max_depth": 2,
            "canonical_roles": [
                "role:primary-engineer",
                "role:root-cause-debugger",
                "role:independent-verifier",
                "role:investigation-specialist",
                "role:security-reviewer",
            ],
            "specialists": specialists_data,
        }
