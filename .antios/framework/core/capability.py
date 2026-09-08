"""AntiOS Canonical Capability Domain Models & Contracts.

Defines the core taxonomy, enums, data models, and contracts for the
Project Capability Layer (Phase 31–33).

Differentiates:
- PROJECT KNOWLEDGE (What the project is and where things are)
- PROJECT CAPABILITY (How agents should work on the project)
- TASK ROUTING (Which capabilities are relevant to the current task)
- CAPABILITY PACK (Bounded agent-facing bundle for the task)
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Set, Union

from framework.core.lifecycle import RiskTier, TaskClass
from framework.core.tool import ToolTier


class CapabilityType(str, Enum):
    """Canonical classification of engineering capabilities."""
    SKILL = "SKILL"                            # Procedural engineering policy / guidance
    RULE = "RULE"                              # Governing constraint, invariant, or boundary
    WORKFLOW = "WORKFLOW"                      # Sequence of lifecycle stages / steps
    TOOL = "TOOL"                              # Deterministic mechanism / CLI executable
    VERIFIER = "VERIFIER"                      # Verification policy / test runner contract
    SPECIALIST = "SPECIALIST"                  # Specialist agent role definition
    EXTERNAL_PROVIDER = "EXTERNAL_PROVIDER"    # External service or remote resource
    MCP_PROVIDER = "MCP_PROVIDER"              # Model Context Protocol provider


class CapabilityScope(str, Enum):
    """Scope of capability authority and definition."""
    CORE = "CORE"                              # Universal AntiOS governance (immutable)
    ADAPTER = "ADAPTER"                        # Declarative project adapter configuration
    PROJECT_LOCAL = "PROJECT_LOCAL"            # Target project-local asset / script / rule
    SUBSYSTEM = "SUBSYSTEM"                    # Subsystem-specific capability
    COMPONENT = "COMPONENT"                    # Component-specific capability


class RulePrecedence(int, Enum):
    """Precedence hierarchy for governing rules and invariants.
    
    Lower numerical rank indicates higher authority.
    """
    PLATFORM_HOOK = 1                          # Hook IPC interception (highest precedence)
    CORE_INVARIANT = 2                         # Universal core self-protection & Stop Gate
    ADAPTER_POLICY = 3                         # Project adapter configuration policies
    SUBSYSTEM_INVARIANT = 4                    # Subsystem protected invariants
    PROJECT_GUIDANCE = 5                       # Target repository documentation / CI rules


class RuleConflictStatus(str, Enum):
    """Status of conflict evaluation across rules."""
    NO_CONFLICT = "NO_CONFLICT"
    CONFLICT_DETECTED = "CONFLICT_DETECTED"
    OVERRIDDEN = "OVERRIDDEN"


class VerifierType(str, Enum):
    """Verification model required by risk tier and boundary contracts."""
    SOLO_VERIFIER = "SOLO_VERIFIER"            # Low risk: direct test execution & sanity check
    MAKER_CHECKER = "MAKER_CHECKER"            # Medium/High risk: fresh-context subagent audit
    INDEPENDENT_AUDITOR = "INDEPENDENT_AUDITOR"# Critical risk: adversarial auditor pass


class MCPStatus(str, Enum):
    """Decision status for MCP provider evaluation under ANTIOS_MCP_POLICY.md."""
    NATIVE_PREFERRED = "NATIVE_PREFERRED"      # Antigravity native tool already satisfies need
    SCRIPT_PREFERRED = "SCRIPT_PREFERRED"      # Deterministic local script satisfies need
    PROJECT_TOOL_PREFERRED = "PROJECT_TOOL_PREFERRED" # Project-local toolchain satisfies need
    USEFUL = "USEFUL"                          # Permitted MCP under policy (e.g. devtools/playwright)
    OPTIONAL = "OPTIONAL"                      # Conditionally permitted (e.g. remote PR only)
    REJECTED = "REJECTED"                      # Explicitly forbidden under policy
    NOT_NEEDED = "NOT_NEEDED"                  # No provider required for this task


@dataclass
class Capability:
    """Canonical representation of an engineering capability in AntiOS."""
    capability_id: str                         # Unique ID, e.g. 'skill:antios-engineer'
    type: CapabilityType                       # SKILL, RULE, WORKFLOW, etc.
    name: str                                  # Human-readable name
    purpose: str                               # Concise functional purpose
    scope: CapabilityScope = CapabilityScope.CORE
    applies_to_subsystems: List[str] = field(default_factory=lambda: ["*"])
    applies_to_task_types: List[str] = field(default_factory=lambda: ["*"])
    prerequisites: List[str] = field(default_factory=list)
    related_rules: List[str] = field(default_factory=list)
    related_workflows: List[str] = field(default_factory=list)
    related_tools: List[str] = field(default_factory=list)
    verifier: Optional[str] = None
    enabled: bool = True
    risk: str = "LOW"                          # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    evidence: str = ""                         # Provenance rationale or source text
    confidence: float = 1.0                    # 0.0 to 1.0 confidence score
    epistemic_state: str = "OBSERVED"          # "OBSERVED", "INFERRED", "UNKNOWN"
    source: str = ""                           # File path or origin declaration
    negative_applicability: List[str] = field(default_factory=list) # Conditions where capability must NOT apply
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_applicable_to_subsystem(self, subsystem_id: str) -> bool:
        """Determines if this capability applies to the given subsystem."""
        if not self.enabled:
            return False
        clean_sub = subsystem_id.strip().lower()
        if "*" in self.applies_to_subsystems:
            return True
        return any(clean_sub == s.strip().lower() for s in self.applies_to_subsystems)

    def is_applicable_to_task(self, task_type: Union[TaskClass, str]) -> bool:
        """Determines if this capability applies to the given task class."""
        if not self.enabled:
            return False
        task_str = task_type.value if isinstance(task_type, TaskClass) else str(task_type).upper()
        if "*" in self.applies_to_task_types:
            return True
        return any(task_str == t.strip().upper() for t in self.applies_to_task_types)

    def is_negatively_applicable(self, context: Dict[str, Any]) -> bool:
        """Checks if negative applicability conditions fire for the given context."""
        if not self.negative_applicability:
            return False
        current_task = str(context.get("task_class", "")).upper()
        current_stage = str(context.get("stage", "")).upper()
        current_role = str(context.get("role", "")).upper()

        for neg in self.negative_applicability:
            neg_clean = neg.strip().upper()
            if neg_clean.startswith("NOT_TASK:"):
                prohibited = neg_clean.replace("NOT_TASK:", "").strip()
                if current_task == prohibited:
                    return True
            elif neg_clean.startswith("NOT_STAGE:"):
                prohibited = neg_clean.replace("NOT_STAGE:", "").strip()
                if current_stage == prohibited:
                    return True
            elif neg_clean.startswith("NOT_ROLE:"):
                prohibited = neg_clean.replace("NOT_ROLE:", "").strip()
                if current_role == prohibited:
                    return True
            elif neg_clean == f"NOT_{current_task}":
                return True
            elif neg_clean == f"NOT_{current_role}":
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Converts capability to a clean dictionary."""
        return {
            "capability_id": self.capability_id,
            "type": self.type.value,
            "name": self.name,
            "purpose": self.purpose,
            "scope": self.scope.value,
            "applies_to_subsystems": self.applies_to_subsystems,
            "applies_to_task_types": self.applies_to_task_types,
            "prerequisites": self.prerequisites,
            "related_rules": self.related_rules,
            "related_workflows": self.related_workflows,
            "related_tools": self.related_tools,
            "verifier": self.verifier,
            "enabled": self.enabled,
            "risk": self.risk,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "epistemic_state": self.epistemic_state,
            "source": self.source,
            "negative_applicability": self.negative_applicability,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Capability:
        """Reconstructs capability from dictionary."""
        if not isinstance(data, dict):
            raise ValueError("Capability requires dictionary")
        cap_id = data.get("capability_id")
        if not cap_id or not isinstance(cap_id, str):
            raise ValueError("Capability requires non-empty 'capability_id'")
        
        cap_type_raw = data.get("type", CapabilityType.TOOL.value)
        cap_type = CapabilityType(cap_type_raw) if isinstance(cap_type_raw, str) else cap_type_raw
        
        scope_raw = data.get("scope", CapabilityScope.CORE.value)
        scope = CapabilityScope(scope_raw) if isinstance(scope_raw, str) else scope_raw

        return cls(
            capability_id=cap_id.strip(),
            type=cap_type,
            name=str(data.get("name", cap_id)).strip(),
            purpose=str(data.get("purpose", "")).strip(),
            scope=scope,
            applies_to_subsystems=list(data.get("applies_to_subsystems", ["*"])),
            applies_to_task_types=list(data.get("applies_to_task_types", ["*"])),
            prerequisites=list(data.get("prerequisites", [])),
            related_rules=list(data.get("related_rules", [])),
            related_workflows=list(data.get("related_workflows", [])),
            related_tools=list(data.get("related_tools", [])),
            verifier=str(data["verifier"]).strip() if data.get("verifier") else None,
            enabled=bool(data.get("enabled", True)),
            risk=str(data.get("risk", "LOW")).strip().upper(),
            evidence=str(data.get("evidence", "")).strip(),
            confidence=float(data.get("confidence", 1.0)),
            epistemic_state=str(data.get("epistemic_state", "OBSERVED")).strip().upper(),
            source=str(data.get("source", "")).strip(),
            negative_applicability=list(data.get("negative_applicability", [])),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class RuleCapability:
    """Specialized representation of a governing rule or invariant."""
    rule_id: str
    name: str
    statement: str
    precedence: RulePrecedence
    scope: CapabilityScope
    rule_source: str                           # Origin, e.g. "HOOK_GUARD", "ANTIOS_CORE", "PROJECT_CONFIG"
    applies_to_subsystems: List[str] = field(default_factory=lambda: ["*"])
    applies_to_task_types: List[str] = field(default_factory=lambda: ["*"])
    conflict_status: RuleConflictStatus = RuleConflictStatus.NO_CONFLICT
    overridden_by: Optional[str] = None
    evidence: str = ""

    def to_capability(self) -> Capability:
        return Capability(
            capability_id=self.rule_id if self.rule_id.startswith("rule:") else f"rule:{self.rule_id}",
            type=CapabilityType.RULE,
            name=self.name,
            purpose=self.statement,
            scope=self.scope,
            applies_to_subsystems=self.applies_to_subsystems,
            applies_to_task_types=self.applies_to_task_types,
            evidence=self.evidence,
            metadata={
                "statement": self.statement,
                "precedence": self.precedence.value,
                "precedence_name": self.precedence.name,
                "rule_source": self.rule_source,
                "conflict_status": self.conflict_status.value,
                "overridden_by": self.overridden_by,
            }
        )


@dataclass
class SpecialistCapability:
    """Specialized agent role definition complying with Shallow Depth Law."""
    role_id: str
    role_name: str
    responsibility: str
    scope: CapabilityScope
    applicable_tasks: List[str]
    applicable_subsystems: List[str]
    allowed_capabilities: List[str]
    required_verifier: str
    escalation_path: str
    max_nesting_depth: int = 2                 # Strictly <= 2 under Shallow Depth Law

    def to_capability(self) -> Capability:
        return Capability(
            capability_id=self.role_id if self.role_id.startswith("specialist:") else f"specialist:{self.role_id}",
            type=CapabilityType.SPECIALIST,
            name=self.role_name,
            purpose=self.responsibility,
            scope=self.scope,
            applies_to_subsystems=self.applicable_subsystems,
            applies_to_task_types=self.applicable_tasks,
            verifier=self.required_verifier,
            metadata={
                "role_name": self.role_name,
                "responsibility": self.responsibility,
                "allowed_capabilities": self.allowed_capabilities,
                "required_verifier": self.required_verifier,
                "escalation_path": self.escalation_path,
                "max_nesting_depth": self.max_nesting_depth,
            }
        )


@dataclass
class MCPDecision:
    """Outcome of MCP provider evaluation under ANTIOS_MCP_POLICY.md."""
    provider_id: str
    status: MCPStatus
    justification: str
    suggested_alternative: str = ""
    is_permitted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "status": self.status.value,
            "justification": self.justification,
            "suggested_alternative": self.suggested_alternative,
            "is_permitted": self.is_permitted,
        }
