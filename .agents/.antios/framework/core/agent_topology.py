"""AntiOS Agent Topology Engine & Registry.

Manages the canonical and project-specific Agent Topology:
- AgentTopologyRegistry: Deterministic multi-key index for agent roles.
- Canonical Core Roles: Primary Engineer, Root Cause Debugger, Independent Verifier,
  Investigation Specialist, Security Reviewer.
- Adapter Role Integration: Project-local specialist declarations in antios.config.json.
- SpecialistCandidate Discovery: Deterministic candidate proposal engine (DISCOVER -> PROPOSE -> VALIDATE -> ENABLE).

Preserves the Shallow Depth Law (depth <= 2) and Core Invariants.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import os
from typing import Any, Dict, List, Optional, Set, Union

from framework.core.agent_role import (
    AgentRole,
    AgentRoleType,
    AgentCapabilityBoundary,
    DelegationDecisionType,
    EscalationPolicyType,
    SpecialistCandidate,
)
from framework.core.capability import CapabilityScope
from framework.core.config import AntiOSConfig
from framework.core.lifecycle import TaskClass
from framework.core.subsystem import SubsystemDeclaration


class AgentTopologyRegistry:
    """Deterministic in-memory registry for Agent Roles and Topology."""

    def __init__(self, project_name: str = "AntiOS-Core"):
        self.project_name = project_name
        self._roles: Dict[str, AgentRole] = {}
        self._by_type: Dict[AgentRoleType, List[str]] = {t: [] for t in AgentRoleType}
        self._by_subsystem: Dict[str, List[str]] = {}
        self._by_task_type: Dict[str, List[str]] = {}

    def register(self, role: AgentRole, overwrite: bool = True) -> None:
        """Registers an agent role maintaining multi-key indexes."""
        if not isinstance(role, AgentRole):
            raise TypeError(f"Expected AgentRole, got {type(role)}")

        rid = role.role_id
        if rid in self._roles and not overwrite:
            raise ValueError(f"Agent role '{rid}' is already registered")

        if rid in self._roles:
            self._remove_from_indices(rid)

        self._roles[rid] = role

        # Index by role type
        if role.role_type not in self._by_type:
            self._by_type[role.role_type] = []
        self._by_type[role.role_type].append(rid)

        # Index by subsystem
        for sub in role.applies_to_subsystems:
            sub_clean = sub.strip().lower()
            if sub_clean not in self._by_subsystem:
                self._by_subsystem[sub_clean] = []
            self._by_subsystem[sub_clean].append(rid)

        # Index by task type
        for task in role.applies_to_task_types:
            task_clean = task.strip().upper()
            if task_clean not in self._by_task_type:
                self._by_task_type[task_clean] = []
            self._by_task_type[task_clean].append(rid)

    def _remove_from_indices(self, role_id: str) -> None:
        old_role = self._roles[role_id]
        if old_role.role_type in self._by_type and role_id in self._by_type[old_role.role_type]:
            self._by_type[old_role.role_type].remove(role_id)

        for sub in old_role.applies_to_subsystems:
            sub_clean = sub.strip().lower()
            if sub_clean in self._by_subsystem and role_id in self._by_subsystem[sub_clean]:
                self._by_subsystem[sub_clean].remove(role_id)

        for task in old_role.applies_to_task_types:
            task_clean = task.strip().upper()
            if task_clean in self._by_task_type and role_id in self._by_task_type[task_clean]:
                self._by_task_type[task_clean].remove(role_id)

    def get(self, role_id: str) -> Optional[AgentRole]:
        """Retrieves an agent role by its ID."""
        return self._roles.get(role_id)

    def list_all(self, enabled_only: bool = True) -> List[AgentRole]:
        """Lists all registered agent roles."""
        if enabled_only:
            return [r for r in self._roles.values() if r.enabled]
        return list(self._roles.values())

    def find_by_type(self, role_type: AgentRoleType, enabled_only: bool = True) -> List[AgentRole]:
        """Finds all roles matching a given role type."""
        ids = self._by_type.get(role_type, [])
        roles = [self._roles[rid] for rid in ids if rid in self._roles]
        if enabled_only:
            return [r for r in roles if r.enabled]
        return roles

    def find_by_subsystem(self, subsystem_id: str, enabled_only: bool = True) -> List[AgentRole]:
        """Finds all roles applicable to the given subsystem ID."""
        sub_clean = subsystem_id.strip().lower()
        matching_ids = set(self._by_subsystem.get(sub_clean, []))
        matching_ids.update(self._by_subsystem.get("*", []))

        roles = [self._roles[rid] for rid in matching_ids if rid in self._roles]
        if enabled_only:
            return [r for r in roles if r.enabled]
        return roles

    def find_by_task_type(self, task_type: Union[TaskClass, str], enabled_only: bool = True) -> List[AgentRole]:
        """Finds all roles applicable to the given task type."""
        task_str = task_type.value if isinstance(task_type, TaskClass) else str(task_type).upper()
        matching_ids = set(self._by_task_type.get(task_str, []))
        matching_ids.update(self._by_task_type.get("*", []))

        roles = [self._roles[rid] for rid in matching_ids if rid in self._roles]
        if enabled_only:
            return [r for r in roles if r.enabled]
        return roles

    def get_primary_agent(self) -> AgentRole:
        """Retrieves the default primary agent."""
        primaries = self.find_by_type(AgentRoleType.PRIMARY)
        if primaries:
            return primaries[0]
        # Fallback safe primary
        return AgentRole(
            role_id="role:primary-engineer",
            name="AntiOS Engineer",
            role_type=AgentRoleType.PRIMARY,
            responsibility="Default Primary Agent owning overall task completion",
            can_delegate=True,
            max_depth=2,
        )


def build_default_agent_topology(config: Optional[AntiOSConfig] = None) -> AgentTopologyRegistry:
    """Builds the canonical AntiOS Agent Topology Registry and merges adapter configs."""
    reg = AgentTopologyRegistry(project_name=config.name if config else "AntiOS-Core")

    # 1. Primary Agent: AntiOS Engineer
    primary = AgentRole(
        role_id="role:primary-engineer",
        name="AntiOS Engineer",
        role_type=AgentRoleType.PRIMARY,
        responsibility="Owns overall engineering lifecycle, task decomposition, and execution coordination",
        scope=CapabilityScope.CORE,
        applies_to_task_types=["*"],
        applies_to_subsystems=["*"],
        boundary=AgentCapabilityBoundary(
            allowed_capabilities=["*"],
            forbidden_capabilities=[],
            required_capabilities=["skill:antios-engineer"],
            inherited_capabilities=[],
        ),
        required_verifier="verifier:maker-checker",
        escalation_policy=EscalationPolicyType.RETURN_TO_PRIMARY,
        max_depth=2,
        can_delegate=True,
        enabled=True,
        confidence=1.0,
        evidence="Canonical primary role for universal AntiOS engineering",
        epistemic_state="OBSERVED",
        source="framework/core/agent_topology.py",
    )
    reg.register(primary)

    # 2. Bug Specialist: Root Cause Debugger
    debugger = AgentRole(
        role_id="role:root-cause-debugger",
        name="Root Cause Debugger",
        role_type=AgentRoleType.SPECIALIST,
        responsibility="Systematic root-cause diagnosis, deterministic reproduction, and minimal fix isolation",
        scope=CapabilityScope.CORE,
        applies_to_task_types=["BUG"],
        applies_to_subsystems=["*"],
        boundary=AgentCapabilityBoundary(
            allowed_capabilities=[
                "skill:antios-debug",
                "skill:antios-engineer",
                "tool:navigate-repo",
                "tool:test-*",
                "rule:*",
            ],
            forbidden_capabilities=[
                "workflow:release",
                "rule:core-immutable:override",
            ],
            required_capabilities=["skill:antios-debug"],
            inherited_capabilities=["rule:core-immutable", "rule:stop-gate-ratchet"],
        ),
        required_verifier="verifier:maker-checker",
        escalation_policy=EscalationPolicyType.RETURN_TO_PRIMARY,
        max_depth=2,
        can_delegate=False,
        enabled=True,
        confidence=1.0,
        evidence="Canonical bug isolation specialist governed by antios-debug skill",
        epistemic_state="OBSERVED",
        source="framework/core/agent_topology.py",
    )
    reg.register(debugger)

    # 3. Independent Checker: Verifier Subagent
    checker = AgentRole(
        role_id="role:independent-verifier",
        name="Independent Verifier",
        role_type=AgentRoleType.CHECKER,
        responsibility="Fresh-context independent verification of working tree diffs, test suites, and boundaries",
        scope=CapabilityScope.CORE,
        applies_to_task_types=["*"],
        applies_to_subsystems=["*"],
        boundary=AgentCapabilityBoundary(
            allowed_capabilities=[
                "skill:antios-verifier",
                "tool:navigate-repo",
                "tool:audit-docs",
                "tool:test-*",
                "rule:*",
            ],
            forbidden_capabilities=[
                "tool:write_to_file",
                "tool:replace_file_content",
                "workflow:release",
                "workflow:feature",
            ],
            required_capabilities=["skill:antios-verifier"],
            inherited_capabilities=["rule:core-immutable", "rule:stop-gate-ratchet", "rule:shallow-depth-law"],
        ),
        required_verifier="verifier:maker-checker",
        escalation_policy=EscalationPolicyType.FAIL_CLOSED,
        max_depth=2,
        can_delegate=False,
        enabled=True,
        confidence=1.0,
        evidence="Canonical independent verification role for Maker-Checker and Stop Gate ratchets",
        epistemic_state="OBSERVED",
        source="framework/core/agent_topology.py",
    )
    reg.register(checker)

    # 4. Reconnaissance Specialist: Investigation Specialist
    investigator = AgentRole(
        role_id="role:investigation-specialist",
        name="Investigation Specialist",
        role_type=AgentRoleType.SPECIALIST,
        responsibility="Bounded read-only codebase exploration, evidence acquisition, and architectural discovery",
        scope=CapabilityScope.CORE,
        applies_to_task_types=["INVESTIGATION"],
        applies_to_subsystems=["*"],
        boundary=AgentCapabilityBoundary(
            allowed_capabilities=[
                "tool:navigate-repo",
                "tool:audit-docs",
                "tool:view_file",
                "tool:grep_search",
                "rule:*",
            ],
            forbidden_capabilities=[
                "tool:write_to_file",
                "tool:replace_file_content",
            ],
            required_capabilities=["tool:navigate-repo"],
            inherited_capabilities=["rule:core-immutable"],
        ),
        required_verifier="verifier:solo",
        escalation_policy=EscalationPolicyType.RETURN_TO_PRIMARY,
        max_depth=2,
        can_delegate=False,
        enabled=True,
        confidence=1.0,
        evidence="Canonical read-only reconnaissance specialist",
        epistemic_state="OBSERVED",
        source="framework/core/agent_topology.py",
    )
    reg.register(investigator)

    # 5. Security & Governance Specialist: Security Reviewer
    sec_reviewer = AgentRole(
        role_id="role:security-reviewer",
        name="Security Reviewer",
        role_type=AgentRoleType.SPECIALIST,
        responsibility="Audits security hooks, Stop Gate invariants, and protected zone boundaries",
        scope=CapabilityScope.CORE,
        applies_to_task_types=["REFACTOR", "BUG", "FEATURE"],
        applies_to_subsystems=["core", "governance", "security", "hooks"],
        boundary=AgentCapabilityBoundary(
            allowed_capabilities=[
                "skill:antios-verifier",
                "tool:audit-docs",
                "tool:navigate-repo",
                "rule:*",
            ],
            forbidden_capabilities=[
                "rule:core-immutable:override",
                "rule:platform-hook-interception:override",
            ],
            required_capabilities=["skill:antios-verifier"],
            inherited_capabilities=["rule:core-immutable", "rule:stop-gate-ratchet"],
        ),
        required_verifier="verifier:independent-auditor",
        escalation_policy=EscalationPolicyType.FAIL_CLOSED,
        max_depth=2,
        can_delegate=False,
        enabled=True,
        confidence=1.0,
        evidence="Canonical governance and security reviewer for core modifications",
        epistemic_state="OBSERVED",
        source="framework/core/agent_topology.py",
    )
    reg.register(sec_reviewer)

    # 6. Load Project-Local Specialists from Adapter Configuration
    if config:
        _load_adapter_topology(reg, config)

    return reg


def _load_adapter_topology(registry: AgentTopologyRegistry, config: AntiOSConfig) -> None:
    """Safely loads and validates project-specific specialist roles from adapter configuration."""
    adapter_topology = getattr(config, "agent_topology", {})
    if not isinstance(adapter_topology, dict):
        return

    # Process custom specialists
    specialists_data = adapter_topology.get("specialists", {})
    if isinstance(specialists_data, list):
        # Convert list of dicts to map
        specialists_data = {item.get("role_id", f"role:custom-{i}"): item for i, item in enumerate(specialists_data)}

    for role_id, rdata in specialists_data.items():
        if not isinstance(rdata, dict):
            continue

        rid = role_id if role_id.startswith("role:") else f"role:{role_id}"
        role_type_str = str(rdata.get("role_type", "SPECIALIST")).upper()
        role_type = AgentRoleType(role_type_str) if role_type_str in AgentRoleType.__members__ else AgentRoleType.SPECIALIST

        # HARD SAFETY INVARIANT: Project adapter cannot create a specialist with can_delegate=True or depth > 2
        max_depth = min(2, int(rdata.get("max_depth", 2)))
        can_delegate = False if role_type != AgentRoleType.PRIMARY else bool(rdata.get("can_delegate", False))

        # Build boundary
        raw_boundary = rdata.get("boundary", {})
        allowed = list(raw_boundary.get("allowed_capabilities", rdata.get("allowed_capabilities", ["*"])))
        forbidden = list(raw_boundary.get("forbidden_capabilities", rdata.get("forbidden_capabilities", [])))
        
        # Mandatory project-local forbidden boundaries
        if "rule:core-immutable:override" not in forbidden:
            forbidden.append("rule:core-immutable:override")
        if "rule:stop-gate-ratchet:override" not in forbidden:
            forbidden.append("rule:stop-gate-ratchet:override")

        boundary = AgentCapabilityBoundary(
            allowed_capabilities=allowed,
            forbidden_capabilities=forbidden,
            required_capabilities=list(raw_boundary.get("required_capabilities", rdata.get("required_capabilities", []))),
            inherited_capabilities=list(raw_boundary.get("inherited_capabilities", ["rule:core-immutable", "rule:stop-gate-ratchet"])),
        )

        role = AgentRole(
            role_id=rid,
            name=str(rdata.get("name", rid)).strip(),
            role_type=role_type,
            responsibility=str(rdata.get("responsibility", "Project-local specialist")).strip(),
            scope=CapabilityScope.PROJECT_LOCAL,
            applies_to_task_types=list(rdata.get("applies_to_task_types", ["*"])),
            applies_to_subsystems=list(rdata.get("applies_to_subsystems", ["*"])),
            boundary=boundary,
            required_verifier=str(rdata.get("required_verifier", "verifier:maker-checker")),
            escalation_policy=EscalationPolicyType.RETURN_TO_PRIMARY,
            max_depth=max_depth,
            can_delegate=can_delegate,
            enabled=bool(rdata.get("enabled", True)),
            confidence=float(rdata.get("confidence", 0.9)),
            evidence=str(rdata.get("evidence", "Declared in antios.config.json agent_topology")),
            epistemic_state="OBSERVED",
            source="antios.config.json",
        )
        registry.register(role, overwrite=True)


class SpecialistDiscoveryEngine:
    """Discovers recurring specialist candidates from project subsystem boundaries.
    
    Adheres to: DISCOVER -> PROPOSE -> VALIDATE -> ENABLE.
    NEVER silently activates or creates an active agent.
    """

    @staticmethod
    def discover_candidates(subsystems: List[SubsystemDeclaration]) -> List[SpecialistCandidate]:
        """Identifies domain candidates based on specialized subsystem traits."""
        candidates: List[SpecialistCandidate] = []

        domain_keywords = {
            "ui": ("Frontend Specialist", ["skill:antios-engineer", "tool:navigate-repo"], "Dedicated frontend/UI subsystem with component tests"),
            "frontend": ("Frontend Specialist", ["skill:antios-engineer", "tool:navigate-repo"], "Dedicated frontend subsystem with component tests"),
            "database": ("Database Specialist", ["skill:antios-engineer", "tool:test-*"], "Database migrations and schema storage subsystem"),
            "db": ("Database Specialist", ["skill:antios-engineer", "tool:test-*"], "Database migrations and schema storage subsystem"),
            "api": ("Backend API Specialist", ["skill:antios-engineer", "tool:test-*"], "REST/gRPC backend service subsystem with endpoint tests"),
            "packaging": ("Packaging Specialist", ["tool:navigate-repo"], "Release, build, and package management subsystem"),
        }

        for sub in subsystems:
            sub_id_clean = sub.subsystem_id.lower().strip()
            area_clean = sub.area.lower().strip()

            for key, (suggested_name, caps, rationale) in domain_keywords.items():
                if key in sub_id_clean or key in area_clean or key in sub.keywords:
                    cid = f"candidate:{key}-specialist"
                    if not any(c.candidate_id == cid for c in candidates):
                        candidates.append(
                            SpecialistCandidate(
                                candidate_id=cid,
                                suggested_name=suggested_name,
                                domain_subsystem=sub.subsystem_id,
                                recurring_capabilities=caps,
                                rationale=rationale,
                                discovered_from=f"Subsystem '{sub.subsystem_id}' ({sub.area})",
                                confidence=0.75,
                                epistemic_state="CANDIDATE",
                            )
                        )

        return candidates
