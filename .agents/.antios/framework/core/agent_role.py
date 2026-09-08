"""AntiOS Canonical Agent Role Domain Models & Contracts.

Defines the core taxonomy, enums, data models, and contracts for the
Agent Topology & Project-Specific Specialist Layer (Phase 34–36).

Establishes:
- AGENT ROLE MODEL: Smallest useful canonical model for Primary, Specialist, and Checker agents.
- AGENT CAPABILITY BOUNDARY: Explicit Allowed, Forbidden, Required, and Inherited boundaries.
- DELEGATION POLICY: Deterministic delegation decisions (NO_DELEGATION, DELEGATE_SPECIALIST, etc.).
- SHALLOW DEPTH LAW: Enforces nesting depth <= 2 and prohibits sub-specialist spawning.
- AGENT HANDOFF CONTRACT: Token-bounded context transfer between Primary and Specialist.
- SPECIALIST CANDIDATE: Discovery proposal lifecycle (DISCOVER -> PROPOSE -> VALIDATE -> ENABLE).
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Set, Union

from framework.core.capability import CapabilityScope
from framework.core.lifecycle import TaskClass


class AgentRoleType(str, Enum):
    """Canonical classification of agent roles."""
    PRIMARY = "PRIMARY"          # Owns overall task completion, orchestrates subtasks
    SPECIALIST = "SPECIALIST"    # Performs bounded domain-specific subtask (depth <= 2)
    CHECKER = "CHECKER"          # Independently verifies results in fresh context
    CANDIDATE = "CANDIDATE"      # Discovered candidate role, awaiting validation/enablement


class DelegationDecisionType(str, Enum):
    """Deterministic delegation decision types."""
    NO_DELEGATION = "NO_DELEGATION"                    # Primary handles task directly (efficient default)
    DELEGATE_SPECIALIST = "DELEGATE_SPECIALIST"        # Bounded domain specialist dispatched
    DELEGATE_MAKER_CHECKER = "DELEGATE_MAKER_CHECKER"  # Primary makes, independent Checker verifies
    DELEGATE_INVESTIGATION = "DELEGATE_INVESTIGATION"  # Read-only reconnaissance specialist dispatched
    BLOCKED = "BLOCKED"                                # Task blocked due to conflict or safety violation


class EscalationPolicyType(str, Enum):
    """Escalation policies when a specialist encounters blockers, scope mismatch, or failures."""
    RETURN_TO_PRIMARY = "RETURN_TO_PRIMARY"            # Safely fall back to primary agent
    FAIL_CLOSED = "FAIL_CLOSED"                        # Block immediately on critical violation
    REQUIRE_CHECKER = "REQUIRE_CHECKER"                # Escalate to independent verification


@dataclass
class AgentCapabilityBoundary:
    """Explicit capability authorization boundary for an agent role.
    
    Authority is NEVER inferred from role name alone.
    Every capability accessed by the agent must satisfy:
    1. Not in forbidden_capabilities
    2. In allowed_capabilities (or inherited)
    """
    allowed_capabilities: List[str] = field(default_factory=lambda: ["*"])
    forbidden_capabilities: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)
    inherited_capabilities: List[str] = field(default_factory=list)

    def is_capability_allowed(self, capability_id: str) -> bool:
        """Determines if a capability ID is permitted under this boundary."""
        cap_clean = capability_id.strip()

        # 1. Check forbidden list (takes absolute precedence)
        for forb in self.forbidden_capabilities:
            forb_clean = forb.strip()
            if forb_clean == "*" or cap_clean == forb_clean:
                return False
            if forb_clean.endswith("*") and cap_clean.startswith(forb_clean[:-1]):
                return False

        # 2. Check allowed list
        for allow in self.allowed_capabilities:
            allow_clean = allow.strip()
            if allow_clean == "*" or cap_clean == allow_clean:
                return True
            if allow_clean.endswith("*") and cap_clean.startswith(allow_clean[:-1]):
                return True

        # 3. Check inherited list
        for inh in self.inherited_capabilities:
            inh_clean = inh.strip()
            if inh_clean == "*" or cap_clean == inh_clean:
                return True
            if inh_clean.endswith("*") and cap_clean.startswith(inh_clean[:-1]):
                return True

        return False

    def validate_capability_access(self, capability_id: str) -> tuple[bool, str]:
        """Validates capability access returning status and explanatory rationale."""
        if not self.is_capability_allowed(capability_id):
            # Identify if explicitly forbidden or simply not allowed
            for forb in self.forbidden_capabilities:
                forb_clean = forb.strip()
                if forb_clean == "*" or capability_id.strip() == forb_clean or (forb_clean.endswith("*") and capability_id.strip().startswith(forb_clean[:-1])):
                    return False, f"Capability '{capability_id}' is explicitly FORBIDDEN by role boundary"
            return False, f"Capability '{capability_id}' is not in allowed or inherited capabilities"
        return True, f"Capability '{capability_id}' is permitted by role boundary"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed_capabilities": self.allowed_capabilities,
            "forbidden_capabilities": self.forbidden_capabilities,
            "required_capabilities": self.required_capabilities,
            "inherited_capabilities": self.inherited_capabilities,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentCapabilityBoundary:
        return cls(
            allowed_capabilities=list(data.get("allowed_capabilities", ["*"])),
            forbidden_capabilities=list(data.get("forbidden_capabilities", [])),
            required_capabilities=list(data.get("required_capabilities", [])),
            inherited_capabilities=list(data.get("inherited_capabilities", [])),
        )


@dataclass
class AgentRole:
    """Canonical domain model for an Agent Role in AntiOS."""
    role_id: str                               # Unique ID, e.g. 'role:primary-engineer', 'role:frontend-specialist'
    name: str                                  # Human-readable name, e.g. 'Frontend Specialist'
    role_type: AgentRoleType                   # PRIMARY, SPECIALIST, CHECKER, CANDIDATE
    responsibility: str                        # Concise core responsibility
    scope: CapabilityScope = CapabilityScope.CORE
    applies_to_task_types: List[str] = field(default_factory=lambda: ["*"])
    applies_to_subsystems: List[str] = field(default_factory=lambda: ["*"])
    boundary: AgentCapabilityBoundary = field(default_factory=AgentCapabilityBoundary)
    required_verifier: str = "verifier:solo"   # 'verifier:solo', 'verifier:maker-checker', 'verifier:independent-auditor'
    escalation_policy: EscalationPolicyType = EscalationPolicyType.RETURN_TO_PRIMARY
    max_depth: int = 2                         # Strictly <= 2 under Shallow Depth Law
    can_delegate: bool = False                 # Only PRIMARY can delegate; specialists cannot spawn children
    enabled: bool = True
    confidence: float = 1.0                    # 0.0 to 1.0 confidence
    evidence: str = ""                         # Evidence / rationale for role definition
    epistemic_state: str = "OBSERVED"          # "OBSERVED", "INFERRED", "CANDIDATE", "DURABLE"
    source: str = ""                           # Origin, e.g. "ANTIOS_CORE", "PROJECT_ADAPTER"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Shallow Depth Law invariant: max_depth must be <= 2
        if self.max_depth > 2:
            raise ValueError(f"Shallow Depth Law violation: max_depth for {self.role_id} is {self.max_depth}, must be <= 2")
        # Specialists cannot delegate
        if self.role_type in (AgentRoleType.SPECIALIST, AgentRoleType.CHECKER) and self.can_delegate:
            raise ValueError(f"Shallow Depth Law violation: {self.role_type.value} role '{self.role_id}' cannot have can_delegate=True")
        if isinstance(self.boundary, dict):
            self.boundary = AgentCapabilityBoundary.from_dict(self.boundary)

    def is_applicable_to_subsystem(self, subsystem_id: str) -> bool:
        """Checks if this role applies to the given subsystem."""
        if not self.enabled:
            return False
        sub_clean = subsystem_id.strip().lower()
        if "*" in self.applies_to_subsystems:
            return True
        return any(sub_clean == s.strip().lower() for s in self.applies_to_subsystems)

    def is_applicable_to_task(self, task_type: Union[TaskClass, str]) -> bool:
        """Checks if this role applies to the given task class."""
        if not self.enabled:
            return False
        task_str = task_type.value if isinstance(task_type, TaskClass) else str(task_type).upper()
        if "*" in self.applies_to_task_types:
            return True
        return any(task_str == t.strip().upper() for t in self.applies_to_task_types)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "name": self.name,
            "role_type": self.role_type.value,
            "responsibility": self.responsibility,
            "scope": self.scope.value,
            "applies_to_task_types": self.applies_to_task_types,
            "applies_to_subsystems": self.applies_to_subsystems,
            "boundary": self.boundary.to_dict(),
            "required_verifier": self.required_verifier,
            "escalation_policy": self.escalation_policy.value,
            "max_depth": self.max_depth,
            "can_delegate": self.can_delegate,
            "enabled": self.enabled,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "epistemic_state": self.epistemic_state,
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentRole:
        role_type_raw = data.get("role_type", AgentRoleType.SPECIALIST.value)
        role_type = AgentRoleType(role_type_raw) if isinstance(role_type_raw, str) else role_type_raw

        scope_raw = data.get("scope", CapabilityScope.CORE.value)
        scope = CapabilityScope(scope_raw) if isinstance(scope_raw, str) else scope_raw

        escalation_raw = data.get("escalation_policy", EscalationPolicyType.RETURN_TO_PRIMARY.value)
        escalation = EscalationPolicyType(escalation_raw) if isinstance(escalation_raw, str) else escalation_raw

        raw_boundary = data.get("boundary", {})
        boundary = AgentCapabilityBoundary.from_dict(raw_boundary) if isinstance(raw_boundary, dict) else raw_boundary

        return cls(
            role_id=str(data.get("role_id", "")).strip(),
            name=str(data.get("name", "")).strip(),
            role_type=role_type,
            responsibility=str(data.get("responsibility", "")).strip(),
            scope=scope,
            applies_to_task_types=list(data.get("applies_to_task_types", ["*"])),
            applies_to_subsystems=list(data.get("applies_to_subsystems", ["*"])),
            boundary=boundary,
            required_verifier=str(data.get("required_verifier", "verifier:solo")),
            escalation_policy=escalation,
            max_depth=int(data.get("max_depth", 2)),
            can_delegate=bool(data.get("can_delegate", False)),
            enabled=bool(data.get("enabled", True)),
            confidence=float(data.get("confidence", 1.0)),
            evidence=str(data.get("evidence", "")),
            epistemic_state=str(data.get("epistemic_state", "OBSERVED")),
            source=str(data.get("source", "")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class AgentHandoffContract:
    """Compact, token-bounded handoff contract between Primary and Specialist."""
    contract_id: str
    task: str
    target_files: List[str]
    target_subsystems: List[str]
    allowed_capabilities: List[str]
    forbidden_capabilities: List[str]
    constraints: List[str]
    expected_output: str
    verification_requirement: str
    delegated_role_id: str
    timeout_seconds: int = 120

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentHandoffContract:
        return cls(**data)


@dataclass
class SpecialistResultReport:
    """Structured return payload from a specialist back to the Primary Agent."""
    contract_id: str
    specialist_role_id: str
    status: str                                # "SUCCESS", "FAILED", "PARTIAL", "BLOCKED"
    work_performed: str
    files_touched: List[str]
    decisions: List[str]
    unresolved_issues: List[str]
    evidence: str
    verification_result: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SpecialistCandidate:
    """Discovered candidate role awaiting human or adapter validation."""
    candidate_id: str
    suggested_name: str
    domain_subsystem: str
    recurring_capabilities: List[str]
    rationale: str
    discovered_from: str
    confidence: float = 0.6
    epistemic_state: str = "CANDIDATE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
