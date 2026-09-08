"""AntiOS 2.0 Native Workforce Contract & Responsibility Demarcation.

Phase 83: Formal AntiOS-to-Antigravity Workforce Contract.

Establishes:
1. Clear demarcation between AntiOS governance and Antigravity execution.
   - AntiOS: intent, classification, intelligence, capability selection,
     risk analysis, workforce planning, delegation policy, evidence requirements,
     verification, memory.
   - Antigravity: actual agent execution, native skill discovery/loading,
     native subagent lifecycle, native tool execution, native MCP execution,
     native CLI execution, native context/session mechanics, native background execution.
2. Explicit 11-Step Capability Execution Hierarchy:
   USER -> /antios -> MISSION UNDERSTANDING -> PROJECT INTELLIGENCE ->
   CAPABILITY SELECTION -> WORKFORCE PLAN -> NATIVE ANTIGRAVITY EXECUTION ->
   SPECIALIST / SUBAGENT -> NATIVE TOOL / CLI / MCP -> EVIDENCE ->
   VERIFICATION -> MEMORY.
3. Prohibits AntiOS from emulating capabilities natively owned by Antigravity.
4. Preserves /antios as the single, authoritative user-facing control plane.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class ResponsibilityDomain(str, Enum):
    """Authority domain for engineering functions."""
    ANTIOS = "ANTIOS"
    ANTIGRAVITY = "ANTIGRAVITY"
    SHARED_BOUNDARY = "SHARED_BOUNDARY"


class CapabilityHierarchyStep(str, Enum):
    """The 11 canonical steps in the AntiOS-to-Antigravity capability execution hierarchy."""
    STEP_01_USER = "USER"
    STEP_02_CONTROL_PLANE = "CONTROL_PLANE_ANTIOS"
    STEP_03_MISSION_UNDERSTANDING = "MISSION_UNDERSTANDING"
    STEP_04_PROJECT_INTELLIGENCE = "PROJECT_INTELLIGENCE"
    STEP_05_CAPABILITY_SELECTION = "CAPABILITY_SELECTION"
    STEP_06_WORKFORCE_PLAN = "WORKFORCE_PLAN"
    STEP_07_NATIVE_EXECUTION = "NATIVE_ANTIGRAVITY_EXECUTION"
    STEP_08_SPECIALIST_SUBAGENT = "SPECIALIST_SUBAGENT"
    STEP_09_TOOL_CLI_MCP = "NATIVE_TOOL_CLI_MCP"
    STEP_10_EVIDENCE_COLLECTION = "EVIDENCE_COLLECTION"
    STEP_11_VERIFICATION_MEMORY = "VERIFICATION_AND_MEMORY"


@dataclass(frozen=True)
class ResponsibilityAllocation:
    """Explicit allocation of a specific responsibility to AntiOS or Antigravity."""
    responsibility: str
    owner: ResponsibilityDomain
    rationale: str
    anti_patterns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "responsibility": self.responsibility,
            "owner": self.owner.value,
            "rationale": self.rationale,
            "anti_patterns": list(self.anti_patterns),
        }


# Authoritative allocations defining the canonical boundary
CANONICAL_RESPONSIBILITY_ALLOCATIONS: List[ResponsibilityAllocation] = [
    # AntiOS Responsibilities
    ResponsibilityAllocation(
        responsibility="user_intent_clarification",
        owner=ResponsibilityDomain.ANTIOS,
        rationale="AntiOS formalizes and constrains user intent against project boundaries and non-goals.",
        anti_patterns=["Unconstrained LLM conversational assumptions without project context."],
    ),
    ResponsibilityAllocation(
        responsibility="task_classification",
        owner=ResponsibilityDomain.ANTIOS,
        rationale="AntiOS deterministically categorizes TaskClass and RiskTier.",
        anti_patterns=["Treating all tasks as homogeneous feature requests."],
    ),
    ResponsibilityAllocation(
        responsibility="project_intelligence",
        owner=ResponsibilityDomain.ANTIOS,
        rationale="AntiOS indexes project anatomy, components, test mappings, and epistemic state.",
        anti_patterns=["Dynamic prompt-time scraping of entire repositories."],
    ),
    ResponsibilityAllocation(
        responsibility="capability_selection",
        owner=ResponsibilityDomain.ANTIOS,
        rationale="AntiOS selects appropriate skills, rules, and tools via CapabilityRouter.",
        anti_patterns=["Blindly enabling every tool or defaulting to remote MCP."],
    ),
    ResponsibilityAllocation(
        responsibility="risk_analysis",
        owner=ResponsibilityDomain.ANTIOS,
        rationale="AntiOS determines risk tiers (LOW, MEDIUM, HIGH, CRITICAL) and enforces Stop Gate rules.",
        anti_patterns=["Bypassing verification because an agent claims code is safe."],
    ),
    ResponsibilityAllocation(
        responsibility="workforce_planning",
        owner=ResponsibilityDomain.ANTIOS,
        rationale="AntiOS evaluates workforce sizing (SOLO to MAX) and decides agent count based on cost/risk.",
        anti_patterns=["Spawning maximum agent swarms by default."],
    ),
    ResponsibilityAllocation(
        responsibility="delegation_policy",
        owner=ResponsibilityDomain.ANTIOS,
        rationale="AntiOS enforces Shallow Depth Law (depth <= 2) and forbids specialist self-delegation.",
        anti_patterns=["Unbounded recursive agent trees (Agent -> Agent -> Agent)."],
    ),
    ResponsibilityAllocation(
        responsibility="evidence_requirements",
        owner=ResponsibilityDomain.ANTIOS,
        rationale="AntiOS mandates grounded StructuredHandoff with file paths, diffs, and verification commands.",
        anti_patterns=["Accepting conversational 'Looks Good To Me' (LGTM) handoffs."],
    ),
    ResponsibilityAllocation(
        responsibility="verification_governance",
        owner=ResponsibilityDomain.ANTIOS,
        rationale="AntiOS enforces Maker-Checker separation and physical Stop Gate test exit 0.",
        anti_patterns=["Self-certification by the primary author agent."],
    ),
    ResponsibilityAllocation(
        responsibility="memory_and_learning",
        owner=ResponsibilityDomain.ANTIOS,
        rationale="AntiOS distills durable lessons from observations and updates active context (<= 60 lines).",
        anti_patterns=["Unfiltered prompt memory mutations and hallucinated durable knowledge."],
    ),

    # Antigravity Responsibilities (Native Platform Substrate)
    ResponsibilityAllocation(
        responsibility="agent_execution_runtime",
        owner=ResponsibilityDomain.ANTIGRAVITY,
        rationale="Antigravity provides the LLM inference loop, reasoning tokens, and execution context.",
        anti_patterns=["AntiOS attempting to run custom local LLM loops or emulating an agent broker."],
    ),
    ResponsibilityAllocation(
        responsibility="skill_discovery_and_loading",
        owner=ResponsibilityDomain.ANTIGRAVITY,
        rationale="Antigravity natively discovers, parses YAML frontmatter, and activates SKILL.md files.",
        anti_patterns=["AntiOS maintaining custom skill loading daemons or non-native workflow directories."],
    ),
    ResponsibilityAllocation(
        responsibility="subagent_lifecycle",
        owner=ResponsibilityDomain.ANTIGRAVITY,
        rationale="Antigravity natively manages invoke_subagent, manage_subagents, and subagent process state.",
        anti_patterns=["AntiOS spawning separate OS processes or threads to pretend to be subagents."],
    ),
    ResponsibilityAllocation(
        responsibility="tool_execution_transport",
        owner=ResponsibilityDomain.ANTIGRAVITY,
        rationale="Antigravity executes view_file, write_to_file, replace_file_content, grep_search, and run_command.",
        anti_patterns=["AntiOS bypassing native tools to directly mutate files via custom sockets."],
    ),
    ResponsibilityAllocation(
        responsibility="mcp_transport",
        owner=ResponsibilityDomain.ANTIGRAVITY,
        rationale="Antigravity provides JSON-RPC / MCP client protocol connections to external providers.",
        anti_patterns=["AntiOS implementing raw MCP network sockets or unauthorized external scrapers."],
    ),
    ResponsibilityAllocation(
        responsibility="cli_execution_sandbox",
        owner=ResponsibilityDomain.ANTIGRAVITY,
        rationale="Antigravity runs shell commands via run_command with platform paging and security boundaries.",
        anti_patterns=["AntiOS executing raw unmonitored background subprocess daemons."],
    ),
    ResponsibilityAllocation(
        responsibility="context_and_session_mechanics",
        owner=ResponsibilityDomain.ANTIGRAVITY,
        rationale="Antigravity manages context windows, session transcripts, tool call serialization, and turn events.",
        anti_patterns=["AntiOS attempting to hijack or truncate the platform context window."],
    ),
    ResponsibilityAllocation(
        responsibility="background_execution",
        owner=ResponsibilityDomain.ANTIGRAVITY,
        rationale="Antigravity natively handles non-blocking background tasks and reactive wakeup notifications.",
        anti_patterns=["AntiOS running custom while(True) sleep polling loops."],
    ),
]


@dataclass
class WorkforceContract:
    """The authoritative AntiOS-to-Antigravity Workforce Contract.
    
    Acts as the constitutional agreement establishing what AntiOS owns,
    what Antigravity owns, and the non-negotiable execution pipeline.
    """
    version: str = "2.0.0"
    allocations: List[ResponsibilityAllocation] = field(
        default_factory=lambda: list(CANONICAL_RESPONSIBILITY_ALLOCATIONS)
    )
    control_plane_skill: str = "/antios"
    max_active_agents_per_wave: int = 10
    max_lifetime_spawns_per_mission: int = 20
    max_delegation_depth: int = 2

    def get_owner(self, responsibility: str) -> Optional[ResponsibilityDomain]:
        """Retrieves the authoritative owner for an engineering responsibility."""
        clean_resp = responsibility.strip().lower()
        for alloc in self.allocations:
            if alloc.responsibility.lower() == clean_resp:
                return alloc.owner
        return None

    def is_antios_responsibility(self, responsibility: str) -> bool:
        return self.get_owner(responsibility) == ResponsibilityDomain.ANTIOS

    def is_antigravity_responsibility(self, responsibility: str) -> bool:
        return self.get_owner(responsibility) == ResponsibilityDomain.ANTIGRAVITY

    def validate_capability_hierarchy(self, steps_executed: List[str]) -> Tuple[bool, List[str]]:
        """Validates that execution strictly followed the canonical 11-step hierarchy."""
        canonical_order = [
            CapabilityHierarchyStep.STEP_01_USER.value,
            CapabilityHierarchyStep.STEP_02_CONTROL_PLANE.value,
            CapabilityHierarchyStep.STEP_03_MISSION_UNDERSTANDING.value,
            CapabilityHierarchyStep.STEP_04_PROJECT_INTELLIGENCE.value,
            CapabilityHierarchyStep.STEP_05_CAPABILITY_SELECTION.value,
            CapabilityHierarchyStep.STEP_06_WORKFORCE_PLAN.value,
            CapabilityHierarchyStep.STEP_07_NATIVE_EXECUTION.value,
            CapabilityHierarchyStep.STEP_08_SPECIALIST_SUBAGENT.value,
            CapabilityHierarchyStep.STEP_09_TOOL_CLI_MCP.value,
            CapabilityHierarchyStep.STEP_10_EVIDENCE_COLLECTION.value,
            CapabilityHierarchyStep.STEP_11_VERIFICATION_MEMORY.value,
        ]

        violations = []
        last_index = -1
        for step in steps_executed:
            norm_step = step.strip().upper()
            if norm_step not in canonical_order:
                violations.append(f"Unrecognized execution step: '{step}'")
                continue
            idx = canonical_order.index(norm_step)
            if idx < last_index:
                violations.append(
                    f"Execution sequence inversion: '{norm_step}' appeared after "
                    f"'{canonical_order[last_index]}'"
                )
            last_index = idx

        return len(violations) == 0, violations

    def check_emulation_violation(self, proposed_action: str) -> Tuple[bool, str]:
        """Detects whether AntiOS is attempting to emulate native Antigravity capabilities."""
        action_lower = proposed_action.lower().strip()
        emulation_triggers = {
            "custom_daemon": "AntiOS must not spawn background daemon processes; rely on native Antigravity execution.",
            "workflow_engine": "AntiOS must not implement a custom workflow engine; Antigravity Skills are the native standard.",
            "agent_runtime": "AntiOS must not implement an agent execution runtime; Antigravity owns LLM inference and turns.",
            "mcp_broker": "AntiOS must not implement custom MCP sockets; Antigravity provides native MCP transport.",
            "polling_loop": "AntiOS must not run sleep/poll loops; Antigravity provides reactive wakeup notifications.",
            "subagent_spawner": "AntiOS must not launch raw OS sub-processes as agents; use native invoke_subagent.",
        }

        for trigger, warning in emulation_triggers.items():
            if trigger in action_lower:
                return True, f"Contract Violation: {warning}"

        return False, "Action complies with Workforce Contract responsibility boundary."

    def validate(self) -> Tuple[bool, List[str]]:
        """Validates contract invariants and boundary non-usurpation."""
        errors: List[str] = []
        if not self.version:
            errors.append("Contract version missing.")
        if self.max_active_agents_per_wave > 10:
            errors.append("Constitutional ceiling exceeded: max_active_agents_per_wave must be <= 10.")
        if self.max_lifetime_spawns_per_mission > 20:
            errors.append("Constitutional ceiling exceeded: max_lifetime_spawns_per_mission must be <= 20.")
        if self.max_delegation_depth > 2:
            errors.append("Shallow Depth Law violation: max_delegation_depth must be <= 2.")

        # Ensure AntiOS does not claim platform primitives
        for alloc in self.allocations:
            if alloc.owner == ResponsibilityDomain.ANTIOS:
                if any(k in alloc.responsibility.lower() for k in ["invoke_subagent", "agent_execution", "mcp_transport", "cli_execution_sandbox", "background_execution"]):
                    errors.append(f"Usurpation violation: AntiOS cannot claim native platform primitive '{alloc.responsibility}'.")

        return len(errors) == 0, errors

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkforceContract:
        allocs = []
        for a in data.get("allocations", []):
            allocs.append(
                ResponsibilityAllocation(
                    responsibility=a["responsibility"],
                    owner=ResponsibilityDomain(a["owner"]),
                    rationale=a["rationale"],
                    anti_patterns=list(a.get("anti_patterns", [])),
                )
            )
        return cls(
            version=data.get("version", "2.0.0"),
            control_plane_skill=data.get("control_plane_skill", "/antios"),
            max_active_agents_per_wave=data.get("max_active_agents_per_wave", 10),
            max_lifetime_spawns_per_mission=data.get("max_lifetime_spawns_per_mission", 20),
            max_delegation_depth=data.get("max_delegation_depth", 2),
            allocations=allocs if allocs else list(CANONICAL_RESPONSIBILITY_ALLOCATIONS),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "control_plane_skill": self.control_plane_skill,
            "max_active_agents_per_wave": self.max_active_agents_per_wave,
            "max_lifetime_spawns_per_mission": self.max_lifetime_spawns_per_mission,
            "max_delegation_depth": self.max_delegation_depth,
            "allocations": [a.to_dict() for a in self.allocations],
            "canonical_hierarchy": [s.value for s in CapabilityHierarchyStep],
        }


# Singleton contract instance
DEFAULT_WORKFORCE_CONTRACT = WorkforceContract()
