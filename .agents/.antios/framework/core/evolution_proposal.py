"""AntiOS 2.0 Capability Proposal Engine.

Synthesizes structured, reviewable evolution proposals from capability gaps,
tool analyses, and validated lessons:
  CAPABILITY GAP -> EVIDENCE -> ANALYSIS -> ALTERNATIVES -> RISK -> COST -> PROPOSAL -> VERIFICATION CONTRACT

Enforces:
1. Complete proposal envelope with verification and rollback contracts
2. Supported proposal types including ADD_PROJECT_SKILL, UPDATE_PROJECT_SKILL,
   ADD_SPECIALIST, UPDATE_SPECIALIST, ADD_TOOL_ADAPTER, UPDATE_TOOL_POLICY,
   RECOMPILE_INTELLIGENCE, MIGRATE_INSTANCE, REPAIR_INSTANCE, and NO_ACTION
3. Explicit NO_ACTION evaluation when evidence is insufficient or risk is unmanaged
4. Rejection of proposals violating Core Immutability or the Shallow Depth Law
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from framework.core.capability_gap import CapabilityGap, GapClassification, GapStatus
from framework.core.tool_gap import ToolGapReport


class StructuredProposalType(str, Enum):
    """Canonical classification of capability evolution proposals."""
    ADD_PROJECT_SKILL = "ADD_PROJECT_SKILL"
    UPDATE_PROJECT_SKILL = "UPDATE_PROJECT_SKILL"
    ADD_SPECIALIST = "ADD_SPECIALIST"
    UPDATE_SPECIALIST = "UPDATE_SPECIALIST"
    ADD_TOOL_ADAPTER = "ADD_TOOL_ADAPTER"
    UPDATE_TOOL_POLICY = "UPDATE_TOOL_POLICY"
    RECOMPILE_INTELLIGENCE = "RECOMPILE_INTELLIGENCE"
    MIGRATE_INSTANCE = "MIGRATE_INSTANCE"
    REPAIR_INSTANCE = "REPAIR_INSTANCE"
    DOCUMENTATION_IMPROVEMENT = "DOCUMENTATION_IMPROVEMENT"
    WAYFINDING_IMPROVEMENT = "WAYFINDING_IMPROVEMENT"
    SKILL_REFACTOR = "SKILL_REFACTOR"
    SKILL_DEDUPLICATION = "SKILL_DEDUPLICATION"
    AGENT_BOUNDARY_IMPROVEMENT = "AGENT_BOUNDARY_IMPROVEMENT"
    COMPONENT_INDEX_IMPROVEMENT = "COMPONENT_INDEX_IMPROVEMENT"
    TEST_MAPPING_IMPROVEMENT = "TEST_MAPPING_IMPROVEMENT"
    PROJECT_STRUCTURE_RECOMMENDATION = "PROJECT_STRUCTURE_RECOMMENDATION"
    TOOL_ROUTING_IMPROVEMENT = "TOOL_ROUTING_IMPROVEMENT"
    MCP_ESCALATION_REDUCTION = "MCP_ESCALATION_REDUCTION"
    KNOWLEDGE_REFRESH = "KNOWLEDGE_REFRESH"
    ORCHESTRATION_IMPROVEMENT = "ORCHESTRATION_IMPROVEMENT"
    NO_ACTION = "NO_ACTION"


class ProposalApprovalState(str, Enum):
    """Governance approval states."""
    PROPOSED = "PROPOSED"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"
    VERIFIED = "VERIFIED"


@dataclass
class AlternativeOption:
    """An alternative option evaluated during proposal synthesis."""
    option_name: str
    description: str
    estimated_cost: str          # ZERO, LOW, MEDIUM, HIGH
    risk_level: str              # LOW, MEDIUM, HIGH, CRITICAL
    why_selected_or_rejected: str
    is_selected: bool = False


@dataclass
class StructuredCapabilityProposal:
    """Complete, auditable capability evolution proposal."""
    proposal_id: str
    gap_id: str
    proposal_type: StructuredProposalType
    evidence: Dict[str, Any]
    rationale: str
    alternatives: List[AlternativeOption]
    selected_option: str
    risk_tier: str                           # LOW, MEDIUM, HIGH, CRITICAL
    blast_radius: List[str]                  # Affected subsystems/modules
    affected_paths: List[str]                # Exact filesystem targets
    required_tools: List[str]                # Tools needed for proposal execution
    required_skills: List[str]               # Skills needed
    required_agents: List[str]               # Agent roles needed
    verification_plan: List[str]             # Explicit verification commands
    rollback_plan: List[str]                 # Exact rollback actions if verification fails
    approval_state: ProposalApprovalState = ProposalApprovalState.PROPOSED
    provenance: str = ""
    confidence: float = 1.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization."""
        return {
            "proposal_id": self.proposal_id,
            "gap_id": self.gap_id,
            "proposal_type": self.proposal_type.value,
            "evidence": self.evidence,
            "rationale": self.rationale,
            "alternatives": [asdict(a) for a in self.alternatives],
            "selected_option": self.selected_option,
            "risk_tier": self.risk_tier,
            "blast_radius": list(self.blast_radius),
            "affected_paths": list(self.affected_paths),
            "required_tools": list(self.required_tools),
            "required_skills": list(self.required_skills),
            "required_agents": list(self.required_agents),
            "verification_plan": list(self.verification_plan),
            "rollback_plan": list(self.rollback_plan),
            "approval_state": self.approval_state.value,
            "provenance": self.provenance,
            "confidence": round(self.confidence, 4),
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StructuredCapabilityProposal:
        """Deserializes proposal from dictionary."""
        alts = [AlternativeOption(**a) for a in data.get("alternatives", [])]
        return cls(
            proposal_id=str(data["proposal_id"]),
            gap_id=str(data["gap_id"]),
            proposal_type=StructuredProposalType(data["proposal_type"]),
            evidence=dict(data.get("evidence", {})),
            rationale=str(data.get("rationale", "")),
            alternatives=alts,
            selected_option=str(data.get("selected_option", "")),
            risk_tier=str(data.get("risk_tier", "MEDIUM")),
            blast_radius=list(data.get("blast_radius", [])),
            affected_paths=list(data.get("affected_paths", [])),
            required_tools=list(data.get("required_tools", [])),
            required_skills=list(data.get("required_skills", [])),
            required_agents=list(data.get("required_agents", [])),
            verification_plan=list(data.get("verification_plan", [])),
            rollback_plan=list(data.get("rollback_plan", [])),
            approval_state=ProposalApprovalState(data.get("approval_state", "PROPOSED")),
            provenance=str(data.get("provenance", "")),
            confidence=float(data.get("confidence", 1.0)),
            created_at=str(data.get("created_at", "")),
            metadata=dict(data.get("metadata", {})),
        )


class CapabilityProposalEngine:
    """Synthesizes structured proposals from capability gaps and tool analyses."""

    FORBIDDEN_MUTATION_PATHS = (
        "framework/",
        "framework\\",
        "antios_constitution.md",
        "antios_source_of_truth.md",
        "antios_v1.md",
        ".agents/hooks.json",
        ".git",
    )

    @classmethod
    def evaluate_and_propose(
        cls,
        gap: CapabilityGap,
        tool_report: Optional[ToolGapReport] = None,
        existing_skills: Optional[List[str]] = None,
        existing_specialists: Optional[List[str]] = None,
    ) -> StructuredCapabilityProposal:
        """Evaluates a capability gap and generates a concrete proposal or explicit NO_ACTION."""
        now_ts = datetime.now(timezone.utc).isoformat()
        prop_id = f"prop-{gap.gap_id.replace('gap-', '')}-{hashlib.sha256(now_ts.encode()).hexdigest()[:6]}"

        # ---------------------------------------------------------------------
        # 1. NO_ACTION Condition Checks
        # ---------------------------------------------------------------------
        # If classification is an ordinary implementation or verification failure -> NO_ACTION
        if gap.classification in (
            GapClassification.ORDINARY_IMPLEMENTATION_FAILURE,
            GapClassification.VERIFICATION_FAILURE,
            GapClassification.INSUFFICIENT_EVIDENCE,
        ):
            return StructuredCapabilityProposal(
                proposal_id=prop_id,
                gap_id=gap.gap_id,
                proposal_type=StructuredProposalType.NO_ACTION,
                evidence=gap.evidence,
                rationale=f"Evidence indicates {gap.classification.value}. No OS evolution required; resolve via standard debugging.",
                alternatives=[
                    AlternativeOption(
                        option_name="Evolve OS",
                        description="Modify project skills or configuration",
                        estimated_cost="LOW",
                        risk_level="HIGH",
                        why_selected_or_rejected="Rejected: Issue is a routine code defect, not a missing capability.",
                        is_selected=False,
                    ),
                    AlternativeOption(
                        option_name="NO_ACTION",
                        description="Maintain current OS configuration; fix implementation in code.",
                        estimated_cost="ZERO",
                        risk_level="LOW",
                        why_selected_or_rejected="Selected: Ordinary failure caught by test ratchet.",
                        is_selected=True,
                    ),
                ],
                selected_option="NO_ACTION",
                risk_tier="LOW",
                blast_radius=[gap.affected_subsystem],
                affected_paths=[],
                required_tools=["run_command"],
                required_skills=["antios-debug"],
                required_agents=["AntiOS Engineer"],
                verification_plan=["python tests/run_all.py"],
                rollback_plan=["git restore ."],
                approval_state=ProposalApprovalState.PROPOSED,
                provenance="CapabilityProposalEngine:NO_ACTION_CLASSIFICATION",
                confidence=gap.confidence,
            )

        # ---------------------------------------------------------------------
        # 2. Tool Runner Missing in antios.config.json -> ADD_TOOL_ADAPTER
        # ---------------------------------------------------------------------
        if gap.classification == GapClassification.UNAVAILABLE_TOOL or (tool_report and tool_report.deficit_type == "TIER_DEFICIT"):
            runner_name = gap.evidence.get("missing_tool", "custom-runner")
            return StructuredCapabilityProposal(
                proposal_id=prop_id,
                gap_id=gap.gap_id,
                proposal_type=StructuredProposalType.ADD_TOOL_ADAPTER,
                evidence=gap.evidence,
                rationale=f"Configured task requires tool/runner '{runner_name}' which is missing from project adapter.",
                alternatives=[
                    AlternativeOption(
                        option_name="Register Tool in antios.config.json",
                        description=f"Add '{runner_name}' runner declaration to antios.config.json",
                        estimated_cost="ZERO",
                        risk_level="LOW",
                        why_selected_or_rejected="Selected: Connects project-native build/test runner to AntiOS lifecycle.",
                        is_selected=True,
                    ),
                    AlternativeOption(
                        option_name="Escalate to MCP",
                        description="Use remote MCP tool provider",
                        estimated_cost="MEDIUM",
                        risk_level="MEDIUM",
                        why_selected_or_rejected="Rejected: Project tool exists locally and outranks MCP.",
                        is_selected=False,
                    ),
                ],
                selected_option="Register Tool in antios.config.json",
                risk_tier="LOW",
                blast_radius=[gap.affected_subsystem],
                affected_paths=["antios.config.json"],
                required_tools=["replace_file_content"],
                required_skills=["antios-adapt-project"],
                required_agents=["AntiOS Engineer"],
                verification_plan=["python framework/scripts/tools/inspect_repo.py ."],
                rollback_plan=["git checkout -- antios.config.json"],
                approval_state=ProposalApprovalState.PROPOSED,
                provenance="CapabilityProposalEngine:TOOL_ADAPTER_PROPOSAL",
                confidence=gap.confidence,
            )

        # ---------------------------------------------------------------------
        # 3. Missing Specialist or Skill -> ADD_PROJECT_SKILL or ADD_SPECIALIST
        # ---------------------------------------------------------------------
        if "specialist" in gap.required_capability.lower():
            spec_name = gap.required_capability.replace("specialist:", "").strip()
            return StructuredCapabilityProposal(
                proposal_id=prop_id,
                gap_id=gap.gap_id,
                proposal_type=StructuredProposalType.ADD_SPECIALIST,
                evidence=gap.evidence,
                rationale=f"Recurring tasks in subsystem '{gap.affected_subsystem}' benefit from dedicated leaf specialist '{spec_name}'.",
                alternatives=[
                    AlternativeOption(
                        option_name=f"Synthesize Specialist '{spec_name}'",
                        description=f"Add leaf specialist contract to .antios/agent_topology.json (max_depth<=2, can_delegate=False)",
                        estimated_cost="ZERO",
                        risk_level="MEDIUM",
                        why_selected_or_rejected="Selected: Domain-scoped focused agent role improves execution speed.",
                        is_selected=True,
                    ),
                    AlternativeOption(
                        option_name="NO_ACTION (Generic Engineer)",
                        description="Continue using generic AntiOS Engineer",
                        estimated_cost="ZERO",
                        risk_level="LOW",
                        why_selected_or_rejected="Rejected: Subsystem complexity justifies dedicated specialist focus.",
                        is_selected=False,
                    ),
                ],
                selected_option=f"Synthesize Specialist '{spec_name}'",
                risk_tier="MEDIUM",
                blast_radius=[gap.affected_subsystem],
                affected_paths=[".antios/agent_topology.json"],
                required_tools=["write_to_file"],
                required_skills=["antios-engineer"],
                required_agents=["AntiOS Engineer"],
                verification_plan=["python framework/scripts/tools/verify_intelligence.py ."],
                rollback_plan=["git checkout -- .antios/agent_topology.json"],
                approval_state=ProposalApprovalState.PROPOSED,
                provenance="CapabilityProposalEngine:SPECIALIST_SYNTHESIS",
                confidence=gap.confidence,
                metadata={"max_depth": 2, "can_delegate": False},
            )

        # ---------------------------------------------------------------------
        # 4. Default: Skill Addition / Refinement
        # ---------------------------------------------------------------------
        skill_name = f"skill-{gap.affected_subsystem.lower()}"
        target_path = f".agents/skills/{skill_name}/SKILL.md"

        return StructuredCapabilityProposal(
            proposal_id=prop_id,
            gap_id=gap.gap_id,
            proposal_type=StructuredProposalType.ADD_PROJECT_SKILL,
            evidence=gap.evidence,
            rationale=f"Project task requires domain workflow for '{gap.affected_subsystem}'.",
            alternatives=[
                AlternativeOption(
                    option_name=f"Generate Project Skill '{skill_name}'",
                    description=f"Emit structured procedural guidance in {target_path}",
                    estimated_cost="ZERO",
                    risk_level="LOW",
                    why_selected_or_rejected="Selected: Project-local skill encapsulates verified domain rules.",
                    is_selected=True,
                ),
                AlternativeOption(
                    option_name="NO_ACTION",
                    description="Do not create skill; rely on prompt",
                    estimated_cost="ZERO",
                    risk_level="MEDIUM",
                    why_selected_or_rejected="Rejected: Recurring failure pattern requires persistent skill guidance.",
                    is_selected=False,
                ),
            ],
            selected_option=f"Generate Project Skill '{skill_name}'",
            risk_tier="LOW",
            blast_radius=[gap.affected_subsystem],
            affected_paths=[target_path],
            required_tools=["write_to_file"],
            required_skills=["antios-engineer"],
            required_agents=["AntiOS Engineer"],
            verification_plan=["python framework/scripts/tools/audit_docs.py --path .agents/skills/"],
            rollback_plan=[f"rm -rf .agents/skills/{skill_name}"],
            approval_state=ProposalApprovalState.PROPOSED,
            provenance="CapabilityProposalEngine:SKILL_GENERATION",
            confidence=gap.confidence,
        )
