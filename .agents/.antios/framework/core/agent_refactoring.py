"""AntiOS 2.0 Agent-Native Refactoring Advisor.

Phase 77: Identifies repository structural patterns that create avoidable agent cognitive,
search, and token overhead. Translates structural friction into governed, reviewable
evolution proposals:
  STRUCTURAL ANALYSIS -> FRICTION COST ESTIMATION -> BENEFIT / RISK CALCULATION -> ADVISORY RECOMMENDATION -> GOVERNED PROPOSAL

Guarantees:
- STRICTLY ADVISORY: Does NOT execute autonomous broad refactoring.
- Every structural recommendation converts to a StructuredCapabilityProposal.
- Enforces NO_ACTION when refactoring blast radius or risk exceeds tangible agent benefit.
- Rejects recommendations attempting to mutate immutable Core paths (framework/core/, constitution).
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
    AgentFrictionDetector,
    AgentFrictionFinding,
    AgentFrictionReport,
    FrictionCategory,
    FrictionSeverity,
)
from framework.core.agent_improvement import ImprovementProposalEngine
from framework.core.evolution_governance import ControlledEvolutionGovernor
from framework.core.evolution_proposal import (
    ProposalApprovalState,
    StructuredCapabilityProposal,
    StructuredProposalType,
)


@dataclass
class RefactoringRecommendation:
    """An advisory recommendation for agent-native repository refactoring."""
    recommendation_id: str
    title: str
    target_category: str
    rationale: str
    current_friction_cost: str                       # LOW, MEDIUM, HIGH, CRITICAL
    expected_benefit: str
    risk_tier: str                                   # LOW, MEDIUM, HIGH, CRITICAL
    blast_radius: List[str]
    affected_paths: List[str]
    verification_cost: str                           # LOW, MEDIUM, HIGH
    rollback_strategy: str
    is_no_action: bool = False
    associated_proposal: Optional[StructuredCapabilityProposal] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "title": self.title,
            "target_category": self.target_category,
            "rationale": self.rationale,
            "current_friction_cost": self.current_friction_cost,
            "expected_benefit": self.expected_benefit,
            "risk_tier": self.risk_tier,
            "blast_radius": list(self.blast_radius),
            "affected_paths": list(self.affected_paths),
            "verification_cost": self.verification_cost,
            "rollback_strategy": self.rollback_strategy,
            "is_no_action": self.is_no_action,
            "associated_proposal": self.associated_proposal.to_dict() if self.associated_proposal else None,
        }


@dataclass
class RefactoringAdvisorReport:
    """Consolidated report from the Agent-Native Refactoring Advisor."""
    project_path: str
    timestamp: str
    recommendations: List[RefactoringRecommendation]
    total_recommendations: int
    executable_proposals_count: int
    no_action_count: int
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_path": self.project_path,
            "timestamp": self.timestamp,
            "total_recommendations": self.total_recommendations,
            "executable_proposals_count": self.executable_proposals_count,
            "no_action_count": self.no_action_count,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "summary": self.summary,
        }


class AgentRefactoringAdvisor:
    """Advisory engine that detects architectural friction and models safe refactoring proposals."""

    PROTECTED_PATTERNS = [
        "framework/",
        "framework\\",
        "antios_constitution.md",
        "antios_source_of_truth.md",
        "antios_v1.md",
        ".agents/hooks.json",
        ".git",
    ]

    @classmethod
    def analyze_repository(cls, repo_root: Union[str, Path] = ".") -> RefactoringAdvisorReport:
        """Analyzes a repository, detects agent friction, and produces prioritized refactoring advice."""
        root = Path(repo_root).resolve()
        friction_report = AgentFrictionDetector.detect_frictions(root)

        recommendations: List[RefactoringRecommendation] = []
        now_str = datetime.now(timezone.utc).isoformat()

        for finding in friction_report.findings:
            rec = cls._evaluate_friction_for_refactoring(finding, root)
            if rec is not None:
                recommendations.append(rec)

        executable_count = sum(1 for r in recommendations if not r.is_no_action)
        no_action_count = sum(1 for r in recommendations if r.is_no_action)

        summary = (
            f"Evaluated {len(friction_report.findings)} friction findings: "
            f"{executable_count} actionable refactoring proposals formulated, "
            f"{no_action_count} evaluated as NO_ACTION."
        )

        return RefactoringAdvisorReport(
            project_path=str(root),
            timestamp=now_str,
            recommendations=recommendations,
            total_recommendations=len(recommendations),
            executable_proposals_count=executable_count,
            no_action_count=no_action_count,
            summary=summary,
        )

    @classmethod
    def _evaluate_friction_for_refactoring(
        cls, finding: AgentFrictionFinding, root: Path
    ) -> Optional[RefactoringRecommendation]:
        """Maps an individual friction point to an advisory recommendation and proposal."""
        # 1. Check for protected path violation: If any affected path is in Core, advise NO_ACTION
        for path in finding.affected_paths:
            norm_path = path.replace("\\", "/").strip("/").lower()
            for prot in cls.PROTECTED_PATTERNS:
                clean_prot = prot.replace("\\", "/").strip("/").lower()
                if norm_path == clean_prot or norm_path.startswith(clean_prot + "/"):
                    return RefactoringRecommendation(
                        recommendation_id=f"REC-CORE-IMMUTABLE-{finding.friction_id}",
                        title=f"Core Immutability Preservation: {finding.category.value}",
                        target_category=finding.category.value,
                        rationale=f"Affected path '{path}' resides in immutable AntiOS Core. Broad refactoring is forbidden.",
                        current_friction_cost=finding.estimated_agent_cost.value,
                        expected_benefit="Zero benefit from unauthorized core mutation; protects stability.",
                        risk_tier="CRITICAL",
                        blast_radius=[path],
                        affected_paths=[path],
                        verification_cost="LOW",
                        rollback_strategy="None required",
                        is_no_action=True,
                        associated_proposal=None,
                    )

        # 2. Convert to governed proposal via ImprovementProposalEngine
        proposal = ImprovementProposalEngine.propose_from_friction(finding, root)

        is_no_action = proposal.proposal_type == StructuredProposalType.NO_ACTION

        rec_id = f"REC-{finding.category.value}-{finding.friction_id[:8]}"
        title = f"Refactoring Recommendation for {finding.category.value}"

        expected_benefit = str(proposal.metadata.get("expected_benefit", "Reduces agent cognitive overhead."))

        return RefactoringRecommendation(
            recommendation_id=rec_id,
            title=title,
            target_category=finding.category.value,
            rationale=finding.description,
            current_friction_cost=finding.estimated_agent_cost.value,
            expected_benefit=expected_benefit,
            risk_tier=proposal.risk_tier,
            blast_radius=proposal.blast_radius,
            affected_paths=proposal.affected_paths,
            verification_cost="LOW" if len(proposal.affected_paths) <= 2 else "MEDIUM",
            rollback_strategy="; ".join(proposal.rollback_plan) if proposal.rollback_plan else "git checkout",
            is_no_action=is_no_action,
            associated_proposal=proposal,
        )
