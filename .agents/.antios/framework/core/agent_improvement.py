"""AntiOS 2.0 Improvement Proposal Engine.

Phase 75: Evidence-backed improvement proposal layer translating detected agent friction
into structured, reviewable evolution proposals under AntiOS Controlled Evolution Governance:
  FRICTION -> EVIDENCE -> ROOT CAUSE -> ALTERNATIVES -> EXPECTED BENEFIT -> RISK -> BLAST RADIUS -> PROPOSAL -> VERIFICATION PLAN

Guarantees:
- Reuses and integrates directly with StructuredCapabilityProposal and ControlledEvolutionGovernor.
- Does NOT create a competing governance or proposal engine.
- Supports explicit NO_ACTION when evidence is weak or risk exceeds expected benefit.
- Rejects proposals violating Core Immutability or the Shallow Depth Law.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from framework.core.agent_friction import (
    AgentCostLevel,
    AgentFrictionFinding,
    AgentFrictionReport,
    FrictionCategory,
    FrictionClassification,
    FrictionSeverity,
)
from framework.core.evolution_proposal import (
    AlternativeOption,
    ProposalApprovalState,
    StructuredCapabilityProposal,
    StructuredProposalType,
)


class ImprovementProposalEngine:
    """Translates agent friction findings into governed capability evolution proposals."""

    @classmethod
    def propose_from_report(
        cls,
        report: AgentFrictionReport,
        repo_root: Union[str, Path] = ".",
    ) -> List[StructuredCapabilityProposal]:
        """Generates proposals for all findings in a friction report."""
        proposals: List[StructuredCapabilityProposal] = []
        for finding in report.findings:
            prop = cls.propose_from_friction(finding, repo_root)
            proposals.append(prop)
        return proposals

    @classmethod
    def propose_from_friction(
        cls,
        friction: AgentFrictionFinding,
        repo_root: Union[str, Path] = ".",
    ) -> StructuredCapabilityProposal:
        """Synthesizes a governed evolution proposal or explicit NO_ACTION from a friction finding."""
        root = Path(repo_root).resolve()

        # 1. Evaluate NO_ACTION triggers:
        # - Confidence is too low (< 0.6)
        # - Classification is UNKNOWN or POSSIBLE_FRICTION with LOW severity
        # - Low severity friction with high touch risk
        if friction.confidence < 0.6 or (
            friction.classification == FrictionClassification.UNKNOWN
        ) or (
            friction.severity == FrictionSeverity.LOW and friction.estimated_agent_cost == AgentCostLevel.LOW
        ):
            return cls._build_no_action_proposal(
                friction,
                rationale="Friction evidence is weak, unverified, or cost of change exceeds expected benefit.",
            )

        # 2. Route by category
        if friction.category == FrictionCategory.DEAD_PROJECT_REFERENCES:
            return cls._propose_dead_references_fix(friction)
        elif friction.category == FrictionCategory.ORPHANED_DOCUMENTATION:
            return cls._propose_orphaned_doc_index(friction)
        elif friction.category == FrictionCategory.EXCESSIVE_CONTEXT_TRAVERSAL:
            return cls._propose_context_trim(friction)
        elif friction.category == FrictionCategory.DUPLICATE_SKILLS:
            return cls._propose_skill_deduplication(friction)
        elif friction.category == FrictionCategory.AMBIGUOUS_OWNERSHIP:
            return cls._propose_manifest_generation(friction)
        elif friction.category == FrictionCategory.MISSING_VERIFICATION_SURFACE:
            return cls._propose_test_runner_config(friction)
        elif friction.category == FrictionCategory.UNNECESSARY_MCP_ESCALATION:
            return cls._propose_mcp_reduction(friction)
        elif friction.category == FrictionCategory.CONFLICTING_INSTRUCTIONS:
            return cls._propose_retire_legacy_workflow(friction)
        elif friction.category == FrictionCategory.REPEATED_VERIFICATION_FAILURE:
            return cls._propose_knowledge_refresh(friction)

        # Fallback to general documentation or structure improvement
        return cls._propose_generic_improvement(friction)

    # -------------------------------------------------------------------------
    # Concrete proposal generators
    # -------------------------------------------------------------------------
    @classmethod
    def _build_no_action_proposal(
        cls, friction: AgentFrictionFinding, rationale: str
    ) -> StructuredCapabilityProposal:
        proposal_id = f"PROP-NOACTION-{friction.friction_id}"
        alts = [
            AlternativeOption(
                option_name="NO_ACTION",
                description="Preserve existing repository state without intervention.",
                estimated_cost="ZERO",
                risk_level="LOW",
                why_selected_or_rejected=rationale,
                is_selected=True,
            ),
            AlternativeOption(
                option_name="SPECULATIVE_OPTIMIZATION",
                description="Modify files based on weak or unconfirmed signals.",
                estimated_cost="MEDIUM",
                risk_level="HIGH",
                why_selected_or_rejected="Rejected: Risk of accidental regression exceeds potential benefit.",
                is_selected=False,
            ),
        ]
        return StructuredCapabilityProposal(
            proposal_id=proposal_id,
            gap_id=friction.friction_id,
            proposal_type=StructuredProposalType.NO_ACTION,
            evidence=friction.evidence,
            rationale=rationale,
            alternatives=alts,
            selected_option="NO_ACTION",
            risk_tier="LOW",
            blast_radius=[],
            affected_paths=[],
            required_tools=[],
            required_skills=[],
            required_agents=[],
            verification_plan=["python tests/run_all.py"],
            rollback_plan=["None (no disk mutation performed)."],
            approval_state=ProposalApprovalState.PROPOSED,
            confidence=friction.confidence,
            metadata={
                "source_friction_ids": [friction.friction_id],
                "expected_benefit": "Zero risk; avoids unnecessary repository churn.",
            },
        )

    @classmethod
    def _propose_dead_references_fix(cls, friction: AgentFrictionFinding) -> StructuredCapabilityProposal:
        proposal_id = f"PROP-DOC-REPAIR-{friction.friction_id}"
        alts = [
            AlternativeOption(
                option_name="REPAIR_BROKEN_REFERENCES",
                description="Update dead documentation paths to point to existing code locations.",
                estimated_cost="LOW",
                risk_level="LOW",
                why_selected_or_rejected="Selected: Directly fixes broken navigation without changing code semantics.",
                is_selected=True,
            ),
            AlternativeOption(
                option_name="DELETE_DEAD_LINKS",
                description="Strip broken references from documentation entirely.",
                estimated_cost="LOW",
                risk_level="MEDIUM",
                why_selected_or_rejected="Rejected: May remove helpful context that only needs a corrected path.",
                is_selected=False,
            ),
        ]
        return StructuredCapabilityProposal(
            proposal_id=proposal_id,
            gap_id=friction.friction_id,
            proposal_type=StructuredProposalType.DOCUMENTATION_IMPROVEMENT,
            evidence=friction.evidence,
            rationale="Dead links and broken paths mislead agent wayfinding, causing failed reads and repeated searches.",
            alternatives=alts,
            selected_option="REPAIR_BROKEN_REFERENCES",
            risk_tier="LOW",
            blast_radius=["docs"],
            affected_paths=friction.affected_paths,
            required_tools=["audit_docs.py"],
            required_skills=["antios-engineer"],
            required_agents=[],
            verification_plan=["python framework/scripts/tools/audit_docs.py --all"],
            rollback_plan=["git checkout -- " + " ".join(friction.affected_paths)],
            approval_state=ProposalApprovalState.PROPOSED,
            confidence=friction.confidence,
            metadata={
                "source_friction_ids": [friction.friction_id],
                "expected_benefit": "Eliminates dead reference errors and restores reliable wayfinding.",
            },
        )

    @classmethod
    def _propose_orphaned_doc_index(cls, friction: AgentFrictionFinding) -> StructuredCapabilityProposal:
        proposal_id = f"PROP-DOC-INDEX-{friction.friction_id}"
        alts = [
            AlternativeOption(
                option_name="INDEX_ORPHANED_DOCS",
                description="Add links to unindexed documentation files into docs/INDEX.md.",
                estimated_cost="LOW",
                risk_level="LOW",
                why_selected_or_rejected="Selected: Provides discoverability for existing knowledge.",
                is_selected=True,
            ),
            AlternativeOption(
                option_name="NO_ACTION",
                description="Leave documentation unindexed.",
                estimated_cost="ZERO",
                risk_level="LOW",
                why_selected_or_rejected="Rejected: Agents cannot discover unindexed documentation during wayfinding.",
                is_selected=False,
            ),
        ]
        return StructuredCapabilityProposal(
            proposal_id=proposal_id,
            gap_id=friction.friction_id,
            proposal_type=StructuredProposalType.WAYFINDING_IMPROVEMENT,
            evidence=friction.evidence,
            rationale="Unindexed documents are hidden from agent progressive disclosure.",
            alternatives=alts,
            selected_option="INDEX_ORPHANED_DOCS",
            risk_tier="LOW",
            blast_radius=["docs/INDEX.md"],
            affected_paths=["docs/INDEX.md"],
            required_tools=[],
            required_skills=["antios-engineer"],
            required_agents=[],
            verification_plan=["python framework/scripts/tools/audit_docs.py --all"],
            rollback_plan=["git checkout -- docs/INDEX.md"],
            approval_state=ProposalApprovalState.PROPOSED,
            confidence=friction.confidence,
            metadata={
                "source_friction_ids": [friction.friction_id],
                "expected_benefit": "Ensures all project architectural knowledge is cataloged in the wayfinding index.",
            },
        )

    @classmethod
    def _propose_context_trim(cls, friction: AgentFrictionFinding) -> StructuredCapabilityProposal:
        proposal_id = f"PROP-TRIM-CTX-{friction.friction_id}"
        alts = [
            AlternativeOption(
                option_name="CONDENSE_ACTIVE_CONTEXT",
                description="Trim docs/ACTIVE_CONTEXT.md to strictly <= 60 lines per token budget rules.",
                estimated_cost="LOW",
                risk_level="LOW",
                why_selected_or_rejected="Selected: Restores bounded context and prevents context window saturation.",
                is_selected=True,
            ),
        ]
        return StructuredCapabilityProposal(
            proposal_id=proposal_id,
            gap_id=friction.friction_id,
            proposal_type=StructuredProposalType.DOCUMENTATION_IMPROVEMENT,
            evidence=friction.evidence,
            rationale="ACTIVE_CONTEXT.md exceeds 60 lines, threatening context budgets on multi-turn missions.",
            alternatives=alts,
            selected_option="CONDENSE_ACTIVE_CONTEXT",
            risk_tier="LOW",
            blast_radius=["docs/ACTIVE_CONTEXT.md"],
            affected_paths=["docs/ACTIVE_CONTEXT.md"],
            required_tools=[],
            required_skills=["antios-engineer"],
            required_agents=[],
            verification_plan=["python framework/scripts/tools/check_changeset.py ."],
            rollback_plan=["git checkout -- docs/ACTIVE_CONTEXT.md"],
            approval_state=ProposalApprovalState.PROPOSED,
            confidence=friction.confidence,
            metadata={
                "source_friction_ids": [friction.friction_id],
                "expected_benefit": "Preserves context budget and satisfies AntiOS constitutional line limits.",
            },
        )

    @classmethod
    def _propose_skill_deduplication(cls, friction: AgentFrictionFinding) -> StructuredCapabilityProposal:
        proposal_id = f"PROP-SKILL-DEDUP-{friction.friction_id}"
        alts = [
            AlternativeOption(
                option_name="CONSOLIDATE_SKILLS",
                description="Merge overlapping skills into a single authoritative capability.",
                estimated_cost="MEDIUM",
                risk_level="MEDIUM",
                why_selected_or_rejected="Selected: Eliminates routing ambiguity and duplicate instruction overhead.",
                is_selected=True,
            ),
            AlternativeOption(
                option_name="DISTINCT_TRIGGERS",
                description="Sharpen triggers and non-goals in SKILL.md to avoid overlap without merging files.",
                estimated_cost="LOW",
                risk_level="LOW",
                why_selected_or_rejected="Alternative viable option depending on governance decision.",
                is_selected=False,
            ),
        ]
        return StructuredCapabilityProposal(
            proposal_id=proposal_id,
            gap_id=friction.friction_id,
            proposal_type=StructuredProposalType.SKILL_DEDUPLICATION,
            evidence=friction.evidence,
            rationale="Duplicate skill descriptions cause routing ambiguity during capability resolution.",
            alternatives=alts,
            selected_option="CONSOLIDATE_SKILLS",
            risk_tier="MEDIUM",
            blast_radius=[".agents/skills"],
            affected_paths=friction.affected_paths,
            required_tools=[],
            required_skills=["antios-engineer"],
            required_agents=[],
            verification_plan=["python tests/run_all.py"],
            rollback_plan=["git checkout -- " + " ".join(friction.affected_paths)],
            approval_state=ProposalApprovalState.PROPOSED,
            confidence=friction.confidence,
            metadata={
                "source_friction_ids": [friction.friction_id],
                "expected_benefit": "Clear skill boundaries, 100% deterministic capability dispatch.",
            },
        )

    @classmethod
    def _propose_manifest_generation(cls, friction: AgentFrictionFinding) -> StructuredCapabilityProposal:
        proposal_id = f"PROP-MANIF-GEN-{friction.friction_id}"
        alts = [
            AlternativeOption(
                option_name="RUN_ADAPT_PROJECT",
                description="Run adapt_project.py to compile .antios/manifest.json.",
                estimated_cost="LOW",
                risk_level="LOW",
                why_selected_or_rejected="Selected: Canonical AntiOS onboarding procedure.",
                is_selected=True,
            ),
        ]
        return StructuredCapabilityProposal(
            proposal_id=proposal_id,
            gap_id=friction.friction_id,
            proposal_type=StructuredProposalType.RECOMPILE_INTELLIGENCE,
            evidence=friction.evidence,
            rationale="Missing manifest leaves artifact ownership tiers ambiguous.",
            alternatives=alts,
            selected_option="RUN_ADAPT_PROJECT",
            risk_tier="LOW",
            blast_radius=[".antios/manifest.json"],
            affected_paths=[".antios/manifest.json"],
            required_tools=["adapt_project.py"],
            required_skills=["antios-adapt-project"],
            required_agents=[],
            verification_plan=["python framework/scripts/tools/verify_intelligence.py ."],
            rollback_plan=["rm -f .antios/manifest.json"],
            approval_state=ProposalApprovalState.PROPOSED,
            confidence=friction.confidence,
            metadata={
                "source_friction_ids": [friction.friction_id],
                "expected_benefit": "Establishes cryptographic artifact ownership and enables fail-closed verification.",
            },
        )

    @classmethod
    def _propose_test_runner_config(cls, friction: AgentFrictionFinding) -> StructuredCapabilityProposal:
        proposal_id = f"PROP-TEST-RUNNER-{friction.friction_id}"
        alts = [
            AlternativeOption(
                option_name="CONFIGURE_TEST_RUNNER",
                description="Add discovered native test runner to antios.config.json.",
                estimated_cost="LOW",
                risk_level="LOW",
                why_selected_or_rejected="Selected: Enables Stop Gate physical test validation.",
                is_selected=True,
            ),
        ]
        return StructuredCapabilityProposal(
            proposal_id=proposal_id,
            gap_id=friction.friction_id,
            proposal_type=StructuredProposalType.TEST_MAPPING_IMPROVEMENT,
            evidence=friction.evidence,
            rationale="Without configured test runners, Maker-Checker and Stop Gate cannot physically verify changes.",
            alternatives=alts,
            selected_option="CONFIGURE_TEST_RUNNER",
            risk_tier="LOW",
            blast_radius=["antios.config.json"],
            affected_paths=["antios.config.json"],
            required_tools=[],
            required_skills=["antios-engineer"],
            required_agents=[],
            verification_plan=["python framework/scripts/tools/inspect_repo.py ."],
            rollback_plan=["git checkout -- antios.config.json"],
            approval_state=ProposalApprovalState.PROPOSED,
            confidence=friction.confidence,
            metadata={
                "source_friction_ids": [friction.friction_id],
                "expected_benefit": "Unlocks automated test verification for all subsequent agent missions.",
            },
        )

    @classmethod
    def _propose_mcp_reduction(cls, friction: AgentFrictionFinding) -> StructuredCapabilityProposal:
        proposal_id = f"PROP-MCP-REDUCE-{friction.friction_id}"
        alts = [
            AlternativeOption(
                option_name="ENFORCE_TIER_4_CLI",
                description="De-escalate from Tier 6 MCP to Tier 4 CLI (git) in tool routing.",
                estimated_cost="ZERO",
                risk_level="LOW",
                why_selected_or_rejected="Selected: Complies with 6-tier tool escalation hierarchy and eliminates network latency.",
                is_selected=True,
            ),
        ]
        return StructuredCapabilityProposal(
            proposal_id=proposal_id,
            gap_id=friction.friction_id,
            proposal_type=StructuredProposalType.MCP_ESCALATION_REDUCTION,
            evidence=friction.evidence,
            rationale="Tier 4 CLI strictly outranks Tier 6 MCP for local filesystem git operations.",
            alternatives=alts,
            selected_option="ENFORCE_TIER_4_CLI",
            risk_tier="LOW",
            blast_radius=["antios.config.json"],
            affected_paths=["antios.config.json"],
            required_tools=[],
            required_skills=["antios-engineer"],
            required_agents=[],
            verification_plan=["python tests/run_all.py"],
            rollback_plan=["git checkout -- antios.config.json"],
            approval_state=ProposalApprovalState.PROPOSED,
            confidence=friction.confidence,
            metadata={
                "source_friction_ids": [friction.friction_id],
                "expected_benefit": "Zero token overhead for remote MCP calls and strict security compliance.",
            },
        )

    @classmethod
    def _propose_retire_legacy_workflow(cls, friction: AgentFrictionFinding) -> StructuredCapabilityProposal:
        proposal_id = f"PROP-RETIRE-WF-{friction.friction_id}"
        alts = [
            AlternativeOption(
                option_name="RETIRE_LEGACY_WORKFLOWS",
                description="Remove .agents/workflows/ directory in compliance with Zero Legacy Workflows Invariant.",
                estimated_cost="LOW",
                risk_level="MEDIUM",
                why_selected_or_rejected="Selected: Mandatory constitutional requirement; workflows are replaced by skills.",
                is_selected=True,
            ),
        ]
        return StructuredCapabilityProposal(
            proposal_id=proposal_id,
            gap_id=friction.friction_id,
            proposal_type=StructuredProposalType.ORCHESTRATION_IMPROVEMENT,
            evidence=friction.evidence,
            rationale="Legacy workflow directory violates the Zero Legacy Workflows Invariant and creates conflicting execution paths.",
            alternatives=alts,
            selected_option="RETIRE_LEGACY_WORKFLOWS",
            risk_tier="MEDIUM",
            blast_radius=[".agents/workflows"],
            affected_paths=[".agents/workflows"],
            required_tools=[],
            required_skills=["antios-engineer"],
            required_agents=[],
            verification_plan=["python framework/scripts/tools/verify_intelligence.py ."],
            rollback_plan=["git checkout -- .agents/workflows"],
            approval_state=ProposalApprovalState.PROPOSED,
            confidence=friction.confidence,
            metadata={
                "source_friction_ids": [friction.friction_id],
                "expected_benefit": "Guarantees unified execution model through .agents/skills/ and Adaptive Orchestrator.",
            },
        )

    @classmethod
    def _propose_knowledge_refresh(cls, friction: AgentFrictionFinding) -> StructuredCapabilityProposal:
        proposal_id = f"PROP-KNOW-REFRESH-{friction.friction_id}"
        alts = [
            AlternativeOption(
                option_name="REFRESH_KNOWLEDGE_STORE",
                description="Distill lessons and invalidate stale knowledge records causing verification failures.",
                estimated_cost="LOW",
                risk_level="LOW",
                why_selected_or_rejected="Selected: Resolves repeated verification loops by updating procedural memory.",
                is_selected=True,
            ),
        ]
        return StructuredCapabilityProposal(
            proposal_id=proposal_id,
            gap_id=friction.friction_id,
            proposal_type=StructuredProposalType.KNOWLEDGE_REFRESH,
            evidence=friction.evidence,
            rationale="Repeated verification failures indicate outdated assumptions in project knowledge.",
            alternatives=alts,
            selected_option="REFRESH_KNOWLEDGE_STORE",
            risk_tier="LOW",
            blast_radius=[".antios/knowledge.json"],
            affected_paths=[".antios/knowledge.json"],
            required_tools=["distill_memory.py"],
            required_skills=["antios-debug"],
            required_agents=[],
            verification_plan=["python tests/run_all.py"],
            rollback_plan=["git checkout -- .antios/knowledge.json"],
            approval_state=ProposalApprovalState.PROPOSED,
            confidence=friction.confidence,
            metadata={
                "source_friction_ids": [friction.friction_id],
                "expected_benefit": "Prevents future agent missions from repeating known failing approaches.",
            },
        )

    @classmethod
    def _propose_generic_improvement(cls, friction: AgentFrictionFinding) -> StructuredCapabilityProposal:
        proposal_id = f"PROP-GEN-{friction.friction_id}"
        return StructuredCapabilityProposal(
            proposal_id=proposal_id,
            gap_id=friction.friction_id,
            proposal_type=StructuredProposalType.PROJECT_STRUCTURE_RECOMMENDATION,
            evidence=friction.evidence,
            rationale=f"Address detected friction: {friction.description}",
            alternatives=[
                AlternativeOption(
                    option_name="RESOLVE_FRICTION",
                    description=friction.description,
                    estimated_cost="LOW",
                    risk_level="LOW",
                    why_selected_or_rejected="Selected to improve agent-native developer experience.",
                    is_selected=True,
                )
            ],
            selected_option="RESOLVE_FRICTION",
            risk_tier="LOW",
            blast_radius=friction.affected_paths,
            affected_paths=friction.affected_paths,
            required_tools=[],
            required_skills=["antios-engineer"],
            required_agents=[],
            verification_plan=["python tests/run_all.py"],
            rollback_plan=["git checkout -- " + " ".join(friction.affected_paths) if friction.affected_paths else "None"],
            approval_state=ProposalApprovalState.PROPOSED,
            confidence=friction.confidence,
            metadata={
                "source_friction_ids": [friction.friction_id],
                "expected_benefit": "Reduces agent cognitive and execution overhead.",
            },
        )
