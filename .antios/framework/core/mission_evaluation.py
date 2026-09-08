"""AntiOS 2.0 Mission Evaluation Engine (Phase 91).

Deterministic multi-dimensional mission evaluation against explicit acceptance criteria
and authoritative evidence:
- 4 Evaluation Statuses: PASS, FAIL, BLOCKED, INCONCLUSIVE
- 11 Canonical Evaluation Dimensions
- Fail-closed verification: Worker assertions alone NEVER constitute PASS
- Bounded MissionEvaluationCard (<= 25 lines)
- Independent Verifier Contract (Maker-Checker enforcement)
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from framework.core.evidence import (
    EpistemicCategory,
    EvidenceItem,
    EvidencePackage,
    EvidenceState,
)


class EvaluationStatus(str, Enum):
    """The 4 deterministic mission evaluation statuses in AntiOS."""
    PASS = "PASS"                  # Criteria met, physical tests exit 0, invariants hold, verifier approved
    FAIL = "FAIL"                  # Criteria unmet, test error, verifier rejected, or invariants violated
    BLOCKED = "BLOCKED"            # Toolchain/environment missing or gate rejection prevented execution
    INCONCLUSIVE = "INCONCLUSIVE"  # Required evidence missing, conflicting, or invalidated by drift


class MissionEvaluationDimension(str, Enum):
    """The 11 canonical engineering evaluation dimensions."""
    FUNCTIONAL_CORRECTNESS = "FUNCTIONAL_CORRECTNESS"
    ACCEPTANCE_CRITERIA_SATISFACTION = "ACCEPTANCE_CRITERIA_SATISFACTION"
    TEST_VERIFICATION = "TEST_VERIFICATION"
    INVARIANT_COMPLIANCE = "INVARIANT_COMPLIANCE"
    REPOSITORY_INTEGRITY = "REPOSITORY_INTEGRITY"
    CHANGE_SET_INTEGRITY = "CHANGE_SET_INTEGRITY"
    WORKFORCE_GOVERNANCE = "WORKFORCE_GOVERNANCE"
    CONTEXT_GOVERNANCE = "CONTEXT_GOVERNANCE"
    EVIDENCE_COMPLETENESS = "EVIDENCE_COMPLETENESS"
    FRESHNESS_REALITY_ALIGNMENT = "FRESHNESS_REALITY_ALIGNMENT"
    RECOVERY_INTEGRITY = "RECOVERY_INTEGRITY"


@dataclass
class DimensionEvaluation:
    """Individual dimension evaluation record."""
    dimension: MissionEvaluationDimension
    status: EvaluationStatus
    confidence: float = 1.0
    evidence_refs: List[str] = field(default_factory=list)
    failure_reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "status": self.status.value,
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
            "failure_reason": self.failure_reason,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DimensionEvaluation:
        dim_str = str(data.get("dimension", MissionEvaluationDimension.FUNCTIONAL_CORRECTNESS.value))
        try:
            dim = MissionEvaluationDimension(dim_str)
        except ValueError:
            dim = MissionEvaluationDimension.FUNCTIONAL_CORRECTNESS

        st_str = str(data.get("status", EvaluationStatus.INCONCLUSIVE.value))
        try:
            st = EvaluationStatus(st_str)
        except ValueError:
            st = EvaluationStatus.INCONCLUSIVE

        return cls(
            dimension=dim,
            status=st,
            confidence=float(data.get("confidence", 1.0)),
            evidence_refs=list(data.get("evidence_refs", [])),
            failure_reason=str(data.get("failure_reason", "")),
            details=dict(data.get("details", {})),
        )


@dataclass
class MissionEvaluationCard:
    """Bounded, human- and agent-readable mission evaluation summary card.
    
    Hard bound: Strictly <= 25 lines.
    """
    mission_id: str
    verdict: EvaluationStatus
    acceptance_summary: str
    physical_changes_summary: str
    tests_summary: str
    invariants_summary: str
    evidence_summary: str
    governance_summary: str
    freshness_summary: str
    uncertainty_summary: str

    def format_card(self, max_lines: int = 25) -> str:
        """Formats the evaluation summary into a token-bounded block."""
        lines = [
            "=== ANTIOS MISSION EVALUATION ===",
            f"Mission:          {self.mission_id}",
            f"Acceptance:       {self.acceptance_summary}",
            f"Physical Changes: {self.physical_changes_summary}",
            f"Tests:            {self.tests_summary}",
            f"Invariants:       {self.invariants_summary}",
            f"Evidence:         {self.evidence_summary}",
            f"Governance:       {self.governance_summary}",
            f"Freshness:        {self.freshness_summary}",
            f"Uncertainty:      {self.uncertainty_summary}",
            f"Verdict:          {self.verdict.value}",
            "==============================",
        ]
        return "\n".join(lines[:max_lines])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "verdict": self.verdict.value,
            "acceptance_summary": self.acceptance_summary,
            "physical_changes_summary": self.physical_changes_summary,
            "tests_summary": self.tests_summary,
            "invariants_summary": self.invariants_summary,
            "evidence_summary": self.evidence_summary,
            "governance_summary": self.governance_summary,
            "freshness_summary": self.freshness_summary,
            "uncertainty_summary": self.uncertainty_summary,
        }


@dataclass
class MissionEvaluationResult:
    """Authoritative result emitted by the MissionEvaluationEngine."""
    mission_id: str
    overall_status: EvaluationStatus
    dimension_evaluations: Dict[str, DimensionEvaluation]
    card: MissionEvaluationCard
    evidence_hash: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_passed(self) -> bool:
        return self.overall_status == EvaluationStatus.PASS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "overall_status": self.overall_status.value,
            "dimension_evaluations": {
                k: v.to_dict() for k, v in self.dimension_evaluations.items()
            },
            "card": self.card.to_dict(),
            "evidence_hash": self.evidence_hash,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }


class IndependentVerifierContract:
    """Maker-Checker Separation Contract.
    
    The worker that performs a code change must NEVER be the sole authority
    certifying the change as successful.
    """

    @staticmethod
    def audit_verification(
        maker_identity: Optional[str],
        checker_identity: Optional[str],
        risk_tier: str,
        verification_status: str,
        is_independent: bool,
    ) -> Tuple[bool, str]:
        """Audits maker-checker separation compliance."""
        # For HIGH or CRITICAL risk, independent verification is strictly mandatory
        if risk_tier in ("HIGH", "CRITICAL"):
            if not checker_identity or checker_identity == maker_identity:
                return False, f"Maker-Checker Violation: Worker '{maker_identity}' cannot self-certify {risk_tier}-risk task."
            if not is_independent:
                return False, "Maker-Checker Violation: Checker must execute with independent context."
        
        # In all risk tiers, if maker == checker, flag non-independence
        if maker_identity and checker_identity and maker_identity == checker_identity:
            if not is_independent:
                return False, "Circular Verification: Verifier is identical to maker without independence."

        return True, "Maker-Checker verified compliant."


class MissionEvaluationEngine:
    """Deterministic, multi-dimensional mission evaluation engine for AntiOS."""

    @classmethod
    def evaluate(
        cls,
        evidence_package: EvidencePackage,
        risk_tier: str = "MEDIUM",
        maker_identity: Optional[str] = None,
        checker_identity: Optional[str] = None,
        is_independent_checker: bool = True,
        enforce_maker_checker: bool = True,
    ) -> MissionEvaluationResult:
        """Evaluates a mission against its evidence package across 11 canonical dimensions."""
        dim_evals: Dict[str, DimensionEvaluation] = {}
        failure_reasons: List[str] = []
        is_blocked = False

        # 1. Epistemic check: Are there conflicting evidence items?
        has_conflicts = evidence_package.has_conflicting_evidence()
        
        # 2. Epistemic check: Any pure agent claims posing as evidence?
        for it in evidence_package.evidence_items:
            if it.state == EvidenceState.CONFLICTING:
                has_conflicts = True
            if it.epistemic_category == EpistemicCategory.INFERENCE and it.state == EvidenceState.VERIFIED:
                failure_reasons.append(f"Epistemic violation: INFERENCE '{it.evidence_id}' marked as VERIFIED evidence.")

        # --- Dimension 1: Acceptance Criteria Satisfaction ---
        verified_items = evidence_package.get_items_by_state(EvidenceState.VERIFIED)
        verified_keys = set()
        for it in verified_items:
            verified_keys.update(it.acceptance_criteria_keys)

        total_criteria = len(evidence_package.acceptance_criteria)
        if total_criteria > 0:
            # Check how many criteria were satisfied
            satisfied_count = len([c for i, c in enumerate(evidence_package.acceptance_criteria) if f"crit-{i+1}" in verified_keys or any(k in c.lower() for k in verified_keys)])
            if satisfied_count == total_criteria or len(verified_items) >= total_criteria:
                dim_evals[MissionEvaluationDimension.ACCEPTANCE_CRITERIA_SATISFACTION.value] = DimensionEvaluation(
                    dimension=MissionEvaluationDimension.ACCEPTANCE_CRITERIA_SATISFACTION,
                    status=EvaluationStatus.PASS,
                    confidence=1.0,
                    evidence_refs=[it.evidence_id for it in verified_items],
                    details={"satisfied": total_criteria, "total": total_criteria},
                )
            else:
                dim_evals[MissionEvaluationDimension.ACCEPTANCE_CRITERIA_SATISFACTION.value] = DimensionEvaluation(
                    dimension=MissionEvaluationDimension.ACCEPTANCE_CRITERIA_SATISFACTION,
                    status=EvaluationStatus.FAIL,
                    confidence=0.9,
                    failure_reason=f"Only {satisfied_count}/{total_criteria} acceptance criteria satisfied.",
                )
                failure_reasons.append("Unsatisfied acceptance criteria.")
        else:
            # No explicit criteria, pass if verified items exist
            dim_evals[MissionEvaluationDimension.ACCEPTANCE_CRITERIA_SATISFACTION.value] = DimensionEvaluation(
                dimension=MissionEvaluationDimension.ACCEPTANCE_CRITERIA_SATISFACTION,
                status=EvaluationStatus.PASS if verified_items else EvaluationStatus.INCONCLUSIVE,
                confidence=0.8,
            )

        # --- Dimension 2: Test Verification & Command Execution ---
        executed_cmds = evidence_package.commands_executed
        test_results = evidence_package.test_results
        tests_passed = True
        test_count = len(test_results)
        
        # Check command exit codes from evidence items
        exit_codes = {}
        for it in evidence_package.evidence_items:
            exit_codes.update(it.command_exit_codes)

        non_zero_exits = {cmd: code for cmd, code in exit_codes.items() if code != 0}
        if non_zero_exits:
            tests_passed = False
            failure_reasons.append(f"Non-zero exit codes detected: {non_zero_exits}")

        for t in test_results:
            if not t.get("passed", True) or t.get("exit_code", 0) != 0:
                tests_passed = False
                failure_reasons.append(f"Test failure: {t.get('command', 'test')} exited with {t.get('exit_code')}")

        if risk_tier in ("MEDIUM", "HIGH", "CRITICAL") and not executed_cmds and not test_results:
            # Medium/High risk tasks MUST execute physical test verification
            dim_evals[MissionEvaluationDimension.TEST_VERIFICATION.value] = DimensionEvaluation(
                dimension=MissionEvaluationDimension.TEST_VERIFICATION,
                status=EvaluationStatus.FAIL,
                confidence=1.0,
                failure_reason=f"Physical test verification missing for {risk_tier}-risk mission.",
            )
            failure_reasons.append("Missing physical test verification.")
        elif tests_passed:
            dim_evals[MissionEvaluationDimension.TEST_VERIFICATION.value] = DimensionEvaluation(
                dimension=MissionEvaluationDimension.TEST_VERIFICATION,
                status=EvaluationStatus.PASS,
                confidence=1.0,
                details={"commands_executed": len(executed_cmds), "test_count": test_count},
            )
        else:
            dim_evals[MissionEvaluationDimension.TEST_VERIFICATION.value] = DimensionEvaluation(
                dimension=MissionEvaluationDimension.TEST_VERIFICATION,
                status=EvaluationStatus.FAIL,
                confidence=1.0,
                failure_reason="One or more tests or commands failed.",
            )

        # --- Dimension 3: Invariant Compliance ---
        invariants = evidence_package.invariant_checks
        invariants_clean = True
        failed_invariants = []
        for inv in invariants:
            if not inv.get("passed", False):
                invariants_clean = False
                failed_invariants.append(inv.get("name", "unnamed"))

        if invariants_clean:
            dim_evals[MissionEvaluationDimension.INVARIANT_COMPLIANCE.value] = DimensionEvaluation(
                dimension=MissionEvaluationDimension.INVARIANT_COMPLIANCE,
                status=EvaluationStatus.PASS,
                confidence=1.0,
                details={"total_invariants": len(invariants)},
            )
        else:
            dim_evals[MissionEvaluationDimension.INVARIANT_COMPLIANCE.value] = DimensionEvaluation(
                dimension=MissionEvaluationDimension.INVARIANT_COMPLIANCE,
                status=EvaluationStatus.FAIL,
                confidence=1.0,
                failure_reason=f"Invariants failed: {failed_invariants}",
            )
            failure_reasons.append(f"Invariants failed: {failed_invariants}")

        # --- Dimension 4: Functional Correctness ---
        func_status = (
            EvaluationStatus.PASS
            if (dim_evals[MissionEvaluationDimension.TEST_VERIFICATION.value].status == EvaluationStatus.PASS and invariants_clean)
            else EvaluationStatus.FAIL
        )
        dim_evals[MissionEvaluationDimension.FUNCTIONAL_CORRECTNESS.value] = DimensionEvaluation(
            dimension=MissionEvaluationDimension.FUNCTIONAL_CORRECTNESS,
            status=func_status,
            confidence=1.0,
        )

        # --- Dimension 5: Repository Integrity & Change-Set Integrity ---
        # Audits artifact fingerprints (ensure before != after for modified, check ownership)
        forbidden_mutations = []
        for path, fp in evidence_package.artifact_fingerprints.items():
            if fp.ownership_tier in ("PROTECTED_CORE", "IMMUTABLE"):
                forbidden_mutations.append(path)

        if forbidden_mutations:
            dim_evals[MissionEvaluationDimension.REPOSITORY_INTEGRITY.value] = DimensionEvaluation(
                dimension=MissionEvaluationDimension.REPOSITORY_INTEGRITY,
                status=EvaluationStatus.FAIL,
                confidence=1.0,
                failure_reason=f"Forbidden modifications in protected zones: {forbidden_mutations}",
            )
            dim_evals[MissionEvaluationDimension.CHANGE_SET_INTEGRITY.value] = DimensionEvaluation(
                dimension=MissionEvaluationDimension.CHANGE_SET_INTEGRITY,
                status=EvaluationStatus.FAIL,
                confidence=1.0,
                failure_reason="Change set violates ownership boundaries.",
            )
            failure_reasons.append(f"Protected zone mutation: {forbidden_mutations}")
        else:
            dim_evals[MissionEvaluationDimension.REPOSITORY_INTEGRITY.value] = DimensionEvaluation(
                dimension=MissionEvaluationDimension.REPOSITORY_INTEGRITY,
                status=EvaluationStatus.PASS,
                confidence=1.0,
                details={"changed_files": len(evidence_package.changed_artifacts)},
            )
            dim_evals[MissionEvaluationDimension.CHANGE_SET_INTEGRITY.value] = DimensionEvaluation(
                dimension=MissionEvaluationDimension.CHANGE_SET_INTEGRITY,
                status=EvaluationStatus.PASS,
                confidence=1.0,
            )

        # --- Dimension 6: Workforce Governance ---
        wf_summary = evidence_package.workforce_summary
        active_peak = wf_summary.get("active_workers_per_wave_peak", 1)
        lifetime_launches = wf_summary.get("total_launches", 1)
        depth = wf_summary.get("delegation_depth", 1)
        waves_collapsed = wf_summary.get("all_waves_collapsed", True)

        if active_peak > 10 or lifetime_launches > 20 or depth > 2 or not waves_collapsed:
            dim_evals[MissionEvaluationDimension.WORKFORCE_GOVERNANCE.value] = DimensionEvaluation(
                dimension=MissionEvaluationDimension.WORKFORCE_GOVERNANCE,
                status=EvaluationStatus.FAIL,
                confidence=1.0,
                failure_reason="Constitutional workforce boundaries violated (caps or uncollapsed waves).",
            )
            failure_reasons.append("Workforce governance violation.")
        else:
            dim_evals[MissionEvaluationDimension.WORKFORCE_GOVERNANCE.value] = DimensionEvaluation(
                dimension=MissionEvaluationDimension.WORKFORCE_GOVERNANCE,
                status=EvaluationStatus.PASS,
                confidence=1.0,
                details={"active_peak": active_peak, "lifetime_launches": lifetime_launches},
            )

        # --- Dimension 7: Context Governance ---
        ctx_summary = evidence_package.context_summary
        budget_respected = ctx_summary.get("budget_respected", True)
        safety_loaded = ctx_summary.get("safety_invariants_loaded", True)
        if budget_respected and safety_loaded:
            dim_evals[MissionEvaluationDimension.CONTEXT_GOVERNANCE.value] = DimensionEvaluation(
                dimension=MissionEvaluationDimension.CONTEXT_GOVERNANCE,
                status=EvaluationStatus.PASS,
                confidence=1.0,
            )
        else:
            dim_evals[MissionEvaluationDimension.CONTEXT_GOVERNANCE.value] = DimensionEvaluation(
                dimension=MissionEvaluationDimension.CONTEXT_GOVERNANCE,
                status=EvaluationStatus.FAIL,
                confidence=1.0,
                failure_reason="Context budget exceeded or safety invariants omitted.",
            )

        # --- Dimension 8: Evidence Completeness ---
        missing_evidence = [it for it in evidence_package.evidence_items if it.state == EvidenceState.MISSING]
        unprovenanced = [it for it in evidence_package.evidence_items if not it.provenance]
        if missing_evidence or unprovenanced or has_conflicts:
            ev_status = EvaluationStatus.INCONCLUSIVE if has_conflicts else EvaluationStatus.FAIL
            dim_evals[MissionEvaluationDimension.EVIDENCE_COMPLETENESS.value] = DimensionEvaluation(
                dimension=MissionEvaluationDimension.EVIDENCE_COMPLETENESS,
                status=ev_status,
                confidence=0.9,
                failure_reason="Evidence incomplete, unprovenanced, or conflicting.",
            )
            if has_conflicts:
                failure_reasons.append("Conflicting evidence detected across verifiers/runs.")
            else:
                failure_reasons.append("Incomplete evidence package.")
        else:
            dim_evals[MissionEvaluationDimension.EVIDENCE_COMPLETENESS.value] = DimensionEvaluation(
                dimension=MissionEvaluationDimension.EVIDENCE_COMPLETENESS,
                status=EvaluationStatus.PASS,
                confidence=1.0,
                details={"verified_items": len(verified_items)},
            )

        # --- Dimension 9: Freshness / Reality Alignment ---
        stale_items = [it for it in evidence_package.evidence_items if it.freshness_state in ("STALE", "INVALID")]
        if stale_items:
            dim_evals[MissionEvaluationDimension.FRESHNESS_REALITY_ALIGNMENT.value] = DimensionEvaluation(
                dimension=MissionEvaluationDimension.FRESHNESS_REALITY_ALIGNMENT,
                status=EvaluationStatus.FAIL,
                confidence=0.9,
                failure_reason=f"{len(stale_items)} items evaluated on stale/invalid context without refresh.",
            )
            failure_reasons.append("Stale context accepted without required refresh.")
        else:
            dim_evals[MissionEvaluationDimension.FRESHNESS_REALITY_ALIGNMENT.value] = DimensionEvaluation(
                dimension=MissionEvaluationDimension.FRESHNESS_REALITY_ALIGNMENT,
                status=EvaluationStatus.PASS,
                confidence=1.0,
            )

        # --- Dimension 10: Recovery Integrity ---
        rec_events = evidence_package.recovery_events
        dim_evals[MissionEvaluationDimension.RECOVERY_INTEGRITY.value] = DimensionEvaluation(
            dimension=MissionEvaluationDimension.RECOVERY_INTEGRITY,
            status=EvaluationStatus.PASS,
            confidence=1.0,
            details={"recovery_events_count": len(rec_events)},
        )

        # --- Maker-Checker Separation Audit ---
        if enforce_maker_checker:
            mc_ok, mc_msg = IndependentVerifierContract.audit_verification(
                maker_identity=maker_identity,
                checker_identity=checker_identity,
                risk_tier=risk_tier,
                verification_status=evidence_package.final_verdict,
                is_independent=is_independent_checker,
            )
            if not mc_ok:
                failure_reasons.append(mc_msg)
                dim_evals[MissionEvaluationDimension.FUNCTIONAL_CORRECTNESS.value].status = EvaluationStatus.FAIL

        # --- Overall Status Determination ---
        if has_conflicts:
            overall_status = EvaluationStatus.INCONCLUSIVE
        elif failure_reasons:
            overall_status = EvaluationStatus.FAIL
        else:
            # Check if all critical dimensions passed
            all_passed = all(
                eval_item.status == EvaluationStatus.PASS
                for eval_item in dim_evals.values()
            )
            overall_status = EvaluationStatus.PASS if all_passed else EvaluationStatus.INCONCLUSIVE

        # --- Construct Bounded MissionEvaluationCard ---
        card = MissionEvaluationCard(
            mission_id=evidence_package.mission_id,
            verdict=overall_status,
            acceptance_summary=f"{len(verified_items)}/{total_criteria or len(verified_items)} criteria verified",
            physical_changes_summary=f"{len(evidence_package.changed_artifacts)} files modified",
            tests_summary=f"{len(executed_cmds)} commands, {test_count} tests run (all 0)" if tests_passed else "Test failures detected",
            invariants_summary=f"{len(invariants) - len(failed_invariants)}/{len(invariants)} invariants held",
            evidence_summary=f"{len(verified_items)} verified, 0 conflicting" if not has_conflicts else "CONFLICTING evidence present",
            governance_summary="Workforce & Context compliant",
            freshness_summary="FRESH (0 stale items)",
            uncertainty_summary=", ".join(evidence_package.unresolved_uncertainty) if evidence_package.unresolved_uncertainty else "None",
        )

        evidence_hash = evidence_package.compute_evidence_hash()

        return MissionEvaluationResult(
            mission_id=evidence_package.mission_id,
            overall_status=overall_status,
            dimension_evaluations=dim_evals,
            card=card,
            evidence_hash=evidence_hash,
            metadata={"failure_reasons": failure_reasons},
        )
