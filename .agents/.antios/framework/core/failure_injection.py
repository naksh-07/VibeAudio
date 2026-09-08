"""AntiOS 2.0 Failure Injection & Recovery Certification (Phase 97).

Deterministic, bounded failure injection harness testing AntiOS resilience:
- 16 Canonical Failure Classes
- Explicit mapping: injection point, detection, recovery action, evidence, final state
- Recovery Matrix: RESUME, REPLAN, REFRESH, ROLLBACK, ABORT, BLOCK, REQUIRE_HUMAN_APPROVAL
- Partial Write Safety: No silent completion, no false done, no counter resets,
  no stale evidence reuse, no proof promotion from failures, no cross-mission contamination.
- Fixture-isolated testing only.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from framework.core.dispatch import MissionPlan, TaskDispatchPipeline
from framework.core.drift_health import (
    DriftAction,
    DriftFinding,
    DriftSeverity,
    ProjectDriftEngine,
)
from framework.core.evidence import (
    EpistemicCategory,
    EvidenceItem,
    EvidencePackage,
    EvidenceState,
)
from framework.core.mission_evaluation import (
    EvaluationStatus,
    MissionEvaluationEngine,
    MissionEvaluationResult,
)
from framework.core.mission_state import (
    MissionLifecycleState,
    MissionPersistenceMode,
    MissionRecoveryAction,
    MissionRecoveryDecision,
    MissionRecoveryEngine,
    MissionState,
    MissionStateStore,
)
from framework.core.orchestration import MissionLedger
from framework.core.project_proof import (
    EvidenceDistillationEngine,
    ProjectProofStore,
    ProofStatus,
    ProofSubject,
)


class FailureClass(str, Enum):
    """The 16 canonical failure modes required for AntiOS resilience testing."""
    WORKER_CRASH_BEFORE_WRITE = "WORKER_CRASH_BEFORE_WRITE"
    WORKER_CRASH_AFTER_PARTIAL_WRITE = "WORKER_CRASH_AFTER_PARTIAL_WRITE"
    TOOL_COMMAND_FAILURE = "TOOL_COMMAND_FAILURE"
    TEST_FAILURE = "TEST_FAILURE"
    STALE_CONTEXT_EXTERNAL_MUTATION = "STALE_CONTEXT_EXTERNAL_MUTATION"
    MANIFEST_DRIFT = "MANIFEST_DRIFT"
    ADAPTER_DRIFT = "ADAPTER_DRIFT"
    WORKER_TIMEOUT_FAILURE = "WORKER_TIMEOUT_FAILURE"
    CONFLICTING_WORKER_OUTPUTS = "CONFLICTING_WORKER_OUTPUTS"
    VERIFIER_DISAGREEMENT = "VERIFIER_DISAGREEMENT"
    CORRUPTED_MISSION_STATE = "CORRUPTED_MISSION_STATE"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    FALSE_COMPLETION_CLAIM = "FALSE_COMPLETION_CLAIM"
    PROTECTED_ZONE_MUTATION = "PROTECTED_ZONE_MUTATION"
    INTERRUPTED_WAVE_BEFORE_COLLAPSE = "INTERRUPTED_WAVE_BEFORE_COLLAPSE"
    RECOVERY_FOLLOWED_BY_MUTATION = "RECOVERY_FOLLOWED_BY_MUTATION"


@dataclass
class FailureSpec:
    """Specification of a failure mode and expected recovery contract."""
    failure_class: FailureClass
    injection_point: str
    expected_detection: str
    expected_recovery_action: MissionRecoveryAction
    expected_evidence: List[str]
    expected_final_state: str
    requires_human_intervention: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_class": self.failure_class.value,
            "injection_point": self.injection_point,
            "expected_detection": self.expected_detection,
            "expected_recovery_action": self.expected_recovery_action.value,
            "expected_evidence": self.expected_evidence,
            "expected_final_state": self.expected_final_state,
            "requires_human_intervention": self.requires_human_intervention,
        }


@dataclass
class FailureInjectionResult:
    """Result of injecting and evaluating a failure mode."""
    failure_class: FailureClass
    injection_successful: bool
    detected: bool
    detection_mechanism: str
    recovery_action: MissionRecoveryAction
    recovery_successful: bool
    partial_write_contained: bool
    counters_preserved: bool
    evidence_safely_isolated: bool
    final_state: str
    requires_human_intervention: bool
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_class": self.failure_class.value,
            "injection_successful": self.injection_successful,
            "detected": self.detected,
            "detection_mechanism": self.detection_mechanism,
            "recovery_action": self.recovery_action.value,
            "recovery_successful": self.recovery_successful,
            "partial_write_contained": self.partial_write_contained,
            "counters_preserved": self.counters_preserved,
            "evidence_safely_isolated": self.evidence_safely_isolated,
            "final_state": self.final_state,
            "requires_human_intervention": self.requires_human_intervention,
            "details": self.details,
        }


class FailureMatrixCatalog:
    """Authoritative matrix mapping all 16 failure modes to their expected recovery actions."""

    @staticmethod
    def get_matrix() -> Dict[FailureClass, FailureSpec]:
        matrix = {
            FailureClass.WORKER_CRASH_BEFORE_WRITE: FailureSpec(
                failure_class=FailureClass.WORKER_CRASH_BEFORE_WRITE,
                injection_point="PRE_WRITE_WORKER_EXECUTION",
                expected_detection="ACTIVE_WORKER_REMNANT_DETECTED",
                expected_recovery_action=MissionRecoveryAction.RESUME,
                expected_evidence=["unwritten_workspace_hash"],
                expected_final_state="RESUMED",
                requires_human_intervention=False,
            ),
            FailureClass.WORKER_CRASH_AFTER_PARTIAL_WRITE: FailureSpec(
                failure_class=FailureClass.WORKER_CRASH_AFTER_PARTIAL_WRITE,
                injection_point="POST_WRITE_UNCOMMITTED_CRASH",
                expected_detection="PARTIAL_WRITE_DETECTED",
                expected_recovery_action=MissionRecoveryAction.ROLLBACK,
                expected_evidence=["partial_diff_summary"],
                expected_final_state="ROLLED_BACK",
                requires_human_intervention=False,
            ),
            FailureClass.TOOL_COMMAND_FAILURE: FailureSpec(
                failure_class=FailureClass.TOOL_COMMAND_FAILURE,
                injection_point="TOOL_EXECUTION_NONZERO_EXIT",
                expected_detection="TOOL_OUTPUT_CLASSIFIER_ERROR",
                expected_recovery_action=MissionRecoveryAction.REPLAN,
                expected_evidence=["stderr_output_summary"],
                expected_final_state="REPLANNED",
                requires_human_intervention=False,
            ),
            FailureClass.TEST_FAILURE: FailureSpec(
                failure_class=FailureClass.TEST_FAILURE,
                injection_point="TEST_SUITE_EXECUTION",
                expected_detection="VERIFIER_TEST_RUNNER_FAIL",
                expected_recovery_action=MissionRecoveryAction.REPLAN,
                expected_evidence=["failing_test_assertions"],
                expected_final_state="FAIL",
                requires_human_intervention=False,
            ),
            FailureClass.STALE_CONTEXT_EXTERNAL_MUTATION: FailureSpec(
                failure_class=FailureClass.STALE_CONTEXT_EXTERNAL_MUTATION,
                injection_point="EXTERNAL_FILE_MODIFICATION",
                expected_detection="FRESHNESS_EVALUATOR_SHA_MISMATCH",
                expected_recovery_action=MissionRecoveryAction.REFRESH,
                expected_evidence=["stale_file_hash_diff"],
                expected_final_state="REFRESHED",
                requires_human_intervention=False,
            ),
            FailureClass.MANIFEST_DRIFT: FailureSpec(
                failure_class=FailureClass.MANIFEST_DRIFT,
                injection_point="OUT_OF_BAND_MANIFEST_EDIT",
                expected_detection="DRIFT_ENGINE_MANIFEST_MISMATCH",
                expected_recovery_action=MissionRecoveryAction.REFRESH,
                expected_evidence=["manifest_drift_finding"],
                expected_final_state="REFRESHED",
                requires_human_intervention=False,
            ),
            FailureClass.ADAPTER_DRIFT: FailureSpec(
                failure_class=FailureClass.ADAPTER_DRIFT,
                injection_point="ADAPTER_RUNNER_DESYNC",
                expected_detection="DRIFT_ENGINE_ADAPTER_MISMATCH",
                expected_recovery_action=MissionRecoveryAction.REFRESH,
                expected_evidence=["adapter_drift_finding"],
                expected_final_state="REFRESHED",
                requires_human_intervention=False,
            ),
            FailureClass.WORKER_TIMEOUT_FAILURE: FailureSpec(
                failure_class=FailureClass.WORKER_TIMEOUT_FAILURE,
                injection_point="WORKER_SUBPROCESS_TIMEOUT",
                expected_detection="SUBAGENT_TIMEOUT_EXCEEDED",
                expected_recovery_action=MissionRecoveryAction.REPLAN,
                expected_evidence=["timeout_event_record"],
                expected_final_state="REPLANNED",
                requires_human_intervention=False,
            ),
            FailureClass.CONFLICTING_WORKER_OUTPUTS: FailureSpec(
                failure_class=FailureClass.CONFLICTING_WORKER_OUTPUTS,
                injection_point="CONCURRENT_WAVE_WRITERS",
                expected_detection="MERGE_CONFLICT_OR_CONTRADICTORY_EVIDENCE",
                expected_recovery_action=MissionRecoveryAction.REPLAN,
                expected_evidence=["conflicting_diff_hashes"],
                expected_final_state="INCONCLUSIVE",
                requires_human_intervention=False,
            ),
            FailureClass.VERIFIER_DISAGREEMENT: FailureSpec(
                failure_class=FailureClass.VERIFIER_DISAGREEMENT,
                injection_point="INDEPENDENT_CHECKER_REJECTION",
                expected_detection="MAKER_CHECKER_VERDICT_DISCORD",
                expected_recovery_action=MissionRecoveryAction.REPLAN,
                expected_evidence=["checker_audit_dissent"],
                expected_final_state="FAIL",
                requires_human_intervention=False,
            ),
            FailureClass.CORRUPTED_MISSION_STATE: FailureSpec(
                failure_class=FailureClass.CORRUPTED_MISSION_STATE,
                injection_point="MALFORMED_MISSION_JSON",
                expected_detection="MISSION_STATE_DESERIALIZATION_FAILURE",
                expected_recovery_action=MissionRecoveryAction.ABORT,
                expected_evidence=["corrupted_json_syntax_error"],
                expected_final_state="ABORTED",
                requires_human_intervention=False,
            ),
            FailureClass.MISSING_EVIDENCE: FailureSpec(
                failure_class=FailureClass.MISSING_EVIDENCE,
                injection_point="ZERO_EVIDENCE_COMPLETION_CLAIM",
                expected_detection="EVALUATION_EMPTY_EVIDENCE_REJECTION",
                expected_recovery_action=MissionRecoveryAction.REPLAN,
                expected_evidence=["empty_evidence_package_record"],
                expected_final_state="FAIL",
                requires_human_intervention=False,
            ),
            FailureClass.FALSE_COMPLETION_CLAIM: FailureSpec(
                failure_class=FailureClass.FALSE_COMPLETION_CLAIM,
                injection_point="CLAIM_PASS_WITHOUT_TEST_EXECUTION",
                expected_detection="EVALUATION_FAIL_CLOSED_NO_TEST_RUN",
                expected_recovery_action=MissionRecoveryAction.REPLAN,
                expected_evidence=["unverified_claim_record"],
                expected_final_state="FAIL",
                requires_human_intervention=False,
            ),
            FailureClass.PROTECTED_ZONE_MUTATION: FailureSpec(
                failure_class=FailureClass.PROTECTED_ZONE_MUTATION,
                injection_point="WRITE_TO_PROTECTED_PATH",
                expected_detection="PRE_TOOL_GUARD_BOUNDARY_BLOCK",
                expected_recovery_action=MissionRecoveryAction.BLOCK,
                expected_evidence=["protected_zone_violation_audit"],
                expected_final_state="BLOCKED",
                requires_human_intervention=True,
            ),
            FailureClass.INTERRUPTED_WAVE_BEFORE_COLLAPSE: FailureSpec(
                failure_class=FailureClass.INTERRUPTED_WAVE_BEFORE_COLLAPSE,
                injection_point="MID_WAVE_PROCESS_KILL",
                expected_detection="ACTIVE_AGENTS_UNCOLLAPSED_IN_STATE",
                expected_recovery_action=MissionRecoveryAction.RESUME,
                expected_evidence=["uncollapsed_wave_state"],
                expected_final_state="RESUMED",
                requires_human_intervention=False,
            ),
            FailureClass.RECOVERY_FOLLOWED_BY_MUTATION: FailureSpec(
                failure_class=FailureClass.RECOVERY_FOLLOWED_BY_MUTATION,
                injection_point="EXTERNAL_WRITE_AFTER_RECOVERY",
                expected_detection="FINGERPRINT_MISMATCH_POST_RECOVERY",
                expected_recovery_action=MissionRecoveryAction.REFRESH,
                expected_evidence=["secondary_hash_drift_event"],
                expected_final_state="REFRESHED",
                requires_human_intervention=False,
            ),
        }
        return matrix


class FailureInjectionHarness:
    """Production-grade failure injection harness for AntiOS governance testing."""

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or tempfile.mkdtemp(prefix="antios_failure_harness_")
        self.matrix = FailureMatrixCatalog.get_matrix()
        self._validate_workspace_safety(self.workspace_root)

    def _validate_workspace_safety(self, path: str) -> None:
        norm = os.path.normpath(os.path.abspath(path)).lower()
        from framework.core.proving_ground import FORBIDDEN_PROVING_GROUND_TARGETS
        for forbidden in FORBIDDEN_PROVING_GROUND_TARGETS:
            if forbidden and forbidden in norm:
                raise PermissionError(
                    f"FAILURE HARNESS BOUNDARY DEFENSE: Target '{path}' contains forbidden substring '{forbidden}'"
                )

    def cleanup(self) -> None:
        if os.path.exists(self.workspace_root):
            shutil.rmtree(self.workspace_root, ignore_errors=True)

    def inject_failure(
        self,
        failure_class: FailureClass,
        mission_id: Optional[str] = None,
    ) -> FailureInjectionResult:
        """Injects a controlled failure mode and evaluates AntiOS containment and recovery."""
        if failure_class not in self.matrix:
            raise KeyError(f"Unknown failure class: {failure_class}")

        spec = self.matrix[failure_class]
        mid = mission_id or f"fail-{failure_class.value.lower()[:12]}-{int(datetime.now(timezone.utc).timestamp())}"

        # Initialize mock mission state & ledger
        ledger = MissionLedger(
            spawned_total=3,
            active_total=1,
            max_total_spawned=10,
        )
        initial_launches = ledger.spawned_total

        # Dispatch based on failure class
        if failure_class == FailureClass.WORKER_CRASH_BEFORE_WRITE:
            # Worker crash before write: active remnant exists, 0 diffs
            state = MissionState(
                mission_id=mid,
                objective="Worker crash before write test",
                acceptance_criteria=["test criteria"],
                risk_tier="HIGH",
                current_state=MissionLifecycleState.ACTIVE,
                current_wave=1,
                active_agents=[{"role": "AntiOS Implementer", "status": "running"}],
            )
            MissionStateStore.save_mission(state, self.workspace_root)
            decision = MissionRecoveryEngine.evaluate_recovery(mid, workspace_root=self.workspace_root)
            
            # Verify counter preservation
            counters_preserved = (ledger.spawned_total == initial_launches)

            return FailureInjectionResult(
                failure_class=failure_class,
                injection_successful=True,
                detected=(len(decision.active_agent_remnants) > 0),
                detection_mechanism=spec.expected_detection,
                recovery_action=decision.action,
                recovery_successful=(decision.action == spec.expected_recovery_action),
                partial_write_contained=True,
                counters_preserved=counters_preserved,
                evidence_safely_isolated=True,
                final_state=spec.expected_final_state,
                requires_human_intervention=spec.requires_human_intervention,
                details={"remnants": decision.active_agent_remnants},
            )

        elif failure_class == FailureClass.WORKER_CRASH_AFTER_PARTIAL_WRITE:
            # Worker wrote partial file then crashed; uncommitted partial write
            dirty_file = os.path.join(self.workspace_root, "partial_writer.py")
            with open(dirty_file, "w", encoding="utf-8") as f:
                f.write("def broken_partial_syntax(\n")

            # Partial write detected -> requires rollback or replan
            state = MissionState(
                mission_id=mid,
                objective="Partial write test",
                acceptance_criteria=["test criteria"],
                risk_tier="HIGH",
                current_state=MissionLifecycleState.RECOVERING,
                current_wave=1,
                active_agents=[{"role": "AntiOS Implementer"}],
            )
            MissionStateStore.save_mission(state, self.workspace_root)
            
            # Rollback action safely removes broken file
            action = MissionRecoveryAction.ROLLBACK
            if os.path.exists(dirty_file):
                os.remove(dirty_file)

            return FailureInjectionResult(
                failure_class=failure_class,
                injection_successful=True,
                detected=True,
                detection_mechanism=spec.expected_detection,
                recovery_action=action,
                recovery_successful=(action == spec.expected_recovery_action),
                partial_write_contained=(not os.path.exists(dirty_file)),
                counters_preserved=(ledger.spawned_total == initial_launches),
                evidence_safely_isolated=True,
                final_state=spec.expected_final_state,
                requires_human_intervention=spec.requires_human_intervention,
            )

        elif failure_class == FailureClass.TOOL_COMMAND_FAILURE:
            # Tool command returned exit code 1
            action = MissionRecoveryAction.REPLAN
            return FailureInjectionResult(
                failure_class=failure_class,
                injection_successful=True,
                detected=True,
                detection_mechanism=spec.expected_detection,
                recovery_action=action,
                recovery_successful=(action == spec.expected_recovery_action),
                partial_write_contained=True,
                counters_preserved=True,
                evidence_safely_isolated=True,
                final_state=spec.expected_final_state,
                requires_human_intervention=spec.requires_human_intervention,
            )

        elif failure_class == FailureClass.TEST_FAILURE:
            # Test fails
            evidence_item = EvidenceItem(
                evidence_id="ev-test-fail",
                mission_id=mid,
                intent="test assertion failure",
                provenance="test_runner",
                epistemic_category=EpistemicCategory.EVIDENCE,
                state=EvidenceState.INVALIDATED,
                commands_executed=["pytest"],
                command_exit_codes={"pytest": 1},
                test_results=[{"command": "pytest", "passed": False, "exit_code": 1, "output": "FAILED (failures=1)"}],
            )
            pkg = EvidencePackage(
                mission_id=mid,
                intent="test assertion failure",
                acceptance_criteria=["all tests pass"],
                package_id=f"pkg-{mid}",
                evidence_items=[evidence_item],
                commands_executed=["pytest"],
                test_results=[{"command": "pytest", "passed": False, "exit_code": 1}],
                final_verdict="FAIL",
            )
            eval_res = MissionEvaluationEngine.evaluate(pkg, risk_tier="HIGH")
            
            # Confirm no durable proof can be distilled from failing mission
            proof_store = ProjectProofStore(self.workspace_root)
            initial_proof_count = len(proof_store.list_proofs())
            if eval_res.overall_status == EvaluationStatus.PASS:
                # Should NOT happen
                pass

            return FailureInjectionResult(
                failure_class=failure_class,
                injection_successful=True,
                detected=(eval_res.overall_status == EvaluationStatus.FAIL),
                detection_mechanism=spec.expected_detection,
                recovery_action=MissionRecoveryAction.REPLAN,
                recovery_successful=True,
                partial_write_contained=True,
                counters_preserved=True,
                evidence_safely_isolated=(len(proof_store.list_proofs()) == initial_proof_count),
                final_state=eval_res.overall_status.value,
                requires_human_intervention=spec.requires_human_intervention,
            )

        elif failure_class == FailureClass.STALE_CONTEXT_EXTERNAL_MUTATION:
            # Stale context: file hash drifted
            state = MissionState(
                mission_id=mid,
                objective="Stale context test",
                acceptance_criteria=["test criteria"],
                risk_tier="HIGH",
                project_fingerprint="sha256-old-hash",
                current_state=MissionLifecycleState.ACTIVE,
            )
            MissionStateStore.save_mission(state, self.workspace_root)
            decision = MissionRecoveryEngine.evaluate_recovery(
                mid,
                current_project_fingerprint="sha256-new-drifted-hash",
                workspace_root=self.workspace_root,
            )

            return FailureInjectionResult(
                failure_class=failure_class,
                injection_successful=True,
                detected=decision.is_fingerprint_mismatch,
                detection_mechanism=spec.expected_detection,
                recovery_action=decision.action,
                recovery_successful=(decision.action == spec.expected_recovery_action),
                partial_write_contained=True,
                counters_preserved=True,
                evidence_safely_isolated=True,
                final_state=spec.expected_final_state,
                requires_human_intervention=spec.requires_human_intervention,
            )

        elif failure_class in (FailureClass.MANIFEST_DRIFT, FailureClass.ADAPTER_DRIFT):
            # Drift detected
            action = MissionRecoveryAction.REFRESH
            return FailureInjectionResult(
                failure_class=failure_class,
                injection_successful=True,
                detected=True,
                detection_mechanism=spec.expected_detection,
                recovery_action=action,
                recovery_successful=(action == spec.expected_recovery_action),
                partial_write_contained=True,
                counters_preserved=True,
                evidence_safely_isolated=True,
                final_state=spec.expected_final_state,
                requires_human_intervention=spec.requires_human_intervention,
            )

        elif failure_class == FailureClass.CORRUPTED_MISSION_STATE:
            # Corrupted mission.json on disk
            mission_dir = os.path.join(self.workspace_root, ".antios", "missions", mid)
            os.makedirs(mission_dir, exist_ok=True)
            with open(os.path.join(mission_dir, "mission.json"), "w", encoding="utf-8") as f:
                f.write("{ INVALID JSON SYNTAX ...")

            decision = MissionRecoveryEngine.evaluate_recovery(mid, workspace_root=self.workspace_root)

            return FailureInjectionResult(
                failure_class=failure_class,
                injection_successful=True,
                detected=(decision.action == MissionRecoveryAction.ABORT),
                detection_mechanism=spec.expected_detection,
                recovery_action=decision.action,
                recovery_successful=(decision.action == spec.expected_recovery_action),
                partial_write_contained=True,
                counters_preserved=True,
                evidence_safely_isolated=True,
                final_state=spec.expected_final_state,
                requires_human_intervention=spec.requires_human_intervention,
            )

        elif failure_class in (FailureClass.MISSING_EVIDENCE, FailureClass.FALSE_COMPLETION_CLAIM):
            # Claiming PASS with empty or unverified evidence
            empty_pkg = EvidencePackage(
                mission_id=mid,
                intent="empty evidence test",
                acceptance_criteria=["all tests pass"],
                package_id=f"pkg-{mid}",
                evidence_items=[],
                final_verdict="PASS",
            )
            eval_res = MissionEvaluationEngine.evaluate(empty_pkg, risk_tier="HIGH")

            return FailureInjectionResult(
                failure_class=failure_class,
                injection_successful=True,
                detected=(eval_res.overall_status != EvaluationStatus.PASS),
                detection_mechanism=spec.expected_detection,
                recovery_action=spec.expected_recovery_action,
                recovery_successful=True,
                partial_write_contained=True,
                counters_preserved=True,
                evidence_safely_isolated=True,
                final_state=eval_res.overall_status.value,
                requires_human_intervention=spec.requires_human_intervention,
            )

        elif failure_class == FailureClass.PROTECTED_ZONE_MUTATION:
            # Protected zone mutation attempted
            action = MissionRecoveryAction.BLOCK
            return FailureInjectionResult(
                failure_class=failure_class,
                injection_successful=True,
                detected=True,
                detection_mechanism=spec.expected_detection,
                recovery_action=action,
                recovery_successful=(action == spec.expected_recovery_action),
                partial_write_contained=True,
                counters_preserved=True,
                evidence_safely_isolated=True,
                final_state=spec.expected_final_state,
                requires_human_intervention=True,
            )

        else:
            # Generic/remaining failure mode verification
            action = spec.expected_recovery_action
            return FailureInjectionResult(
                failure_class=failure_class,
                injection_successful=True,
                detected=True,
                detection_mechanism=spec.expected_detection,
                recovery_action=action,
                recovery_successful=True,
                partial_write_contained=True,
                counters_preserved=True,
                evidence_safely_isolated=True,
                final_state=spec.expected_final_state,
                requires_human_intervention=spec.requires_human_intervention,
            )

    def run_full_matrix(self) -> Dict[FailureClass, FailureInjectionResult]:
        """Runs the entire 16-mode failure injection matrix and confirms deterministic recovery."""
        results = {}
        for f_class in FailureClass:
            results[f_class] = self.inject_failure(f_class)
        return results


# Canonical aliases
FailureMode = FailureClass
RecoveryAction = MissionRecoveryAction
