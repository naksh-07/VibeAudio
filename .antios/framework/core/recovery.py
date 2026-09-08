"""AntiOS Session Recovery and Verification Continuity Engine.

Provides deterministic session recovery across context wipes, agent restarts,
and workflow interruptions.

Guiding Law: REALITY > STALE STATE
Reconstructs state from:
1. Project Constitution
2. Bounded Active Context (docs/ACTIVE_CONTEXT.md)
3. Git Working Tree Reality (worktree.py)
4. Adapter Configuration (antios.config.json + manifest fingerprint)
5. Recent Verification State (verdict.py)

Detects contradictions:
- File drift (Active context claims changes Git doesn't show)
- Verification drift (Files or manifests changed after verification)
- Adapter drift (Config altered after verification)
- Premature completion (Task marked COMPLETE without verified verdict)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import os
from typing import Any, Dict, List, Optional, Tuple

from framework.core.config import AntiOSConfig, load_config
from framework.core.lifecycle import (
    RiskTier,
    TaskClass,
    TaskStage,
    TaskStatus,
    TaskState,
    parse_active_context,
    sync_to_active_context,
)
from framework.core.worktree import WorktreeSnapshot, capture_worktree_snapshot, inspect_all_conflicts


class ContradictionType(str, Enum):
    """Taxonomy of contradictions between stale memory and physical reality."""
    FILE_STATE_CONTRADICTION = "FILE_STATE_CONTRADICTION"
    VERIFICATION_STALE_WORKING_TREE = "VERIFICATION_STALE_WORKING_TREE"
    VERIFICATION_STALE_ADAPTER = "VERIFICATION_STALE_ADAPTER"
    PREMATURE_COMPLETION = "PREMATURE_COMPLETION"
    UNREGISTERED_WORK_IN_TREE = "UNREGISTERED_WORK_IN_TREE"
    UNRESOLVED_CONFLICT_MARKERS = "UNRESOLVED_CONFLICT_MARKERS"


@dataclass
class Contradiction:
    """A detected contradiction between recorded memory and physical repository reality."""
    type: ContradictionType
    description: str
    stale_claim: str
    physical_reality: str
    severity: str = "CRITICAL"  # "CRITICAL" | "WARNING"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "description": self.description,
            "stale_claim": self.stale_claim,
            "physical_reality": self.physical_reality,
            "severity": self.severity,
        }


@dataclass
class RecoveryPlan:
    """Deterministic recovery strategy generated upon session resumption or context loss."""
    action: str  # "RESUME_STAGE", "RE_VERIFY", "UNBLOCK", "REVERT_TO_VERIFY", "RECOVER_FROM_FAILURE", "INITIALIZE_TASK"
    recommended_stage: TaskStage
    recommended_status: TaskStatus
    preserved_work: List[str] = field(default_factory=list)
    contradictions: List[Contradiction] = field(default_factory=list)
    invalidation_reasons: List[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "recommended_stage": self.recommended_stage.value,
            "recommended_status": self.recommended_status.value,
            "preserved_work": self.preserved_work,
            "contradictions": [c.to_dict() for c in self.contradictions],
            "invalidation_reasons": self.invalidation_reasons,
            "explanation": self.explanation,
        }


def is_verification_stale(
    state: TaskState,
    dirty_files: List[str],
    current_manifest_fingerprint: str = "",
    current_git_head: Optional[str] = None
) -> Tuple[bool, List[str]]:
    """Evaluates whether a prior verification verdict has become stale due to subsequent mutations."""
    verdict = state.verification_verdict
    reasons: List[str] = []

    # If verification was marked VERIFIED in state or status
    has_prior_pass = (
        state.verification_state in ("VERIFIED", "PASS")
        or (verdict and verdict.get("status") == "PASS")
    )
    if not has_prior_pass:
        return False, []

    # 1. Working tree modifications
    # Filter out ACTIVE_CONTEXT.md which changes on state updates
    substantive_dirty = [
        f for f in dirty_files
        if not f.endswith("ACTIVE_CONTEXT.md") and not f.startswith(".git")
    ]
    if substantive_dirty:
        reasons.append(
            f"Working tree files modified after verification: {', '.join(substantive_dirty[:5])}"
        )

    # 2. Manifest fingerprint drift
    if verdict and verdict.get("manifest_fingerprint") and current_manifest_fingerprint:
        if verdict["manifest_fingerprint"] != current_manifest_fingerprint:
            reasons.append(
                f"Project manifests modified since verification (fingerprint drift)."
            )

    # 3. Git head advancement
    if verdict and verdict.get("git_head") and current_git_head:
        if verdict["git_head"] != current_git_head:
            reasons.append(
                f"Git HEAD moved from {verdict['git_head']} to {current_git_head}."
            )

    return len(reasons) > 0, reasons


def detect_state_contradictions(
    state: TaskState,
    snapshot: WorktreeSnapshot,
    manifest_fingerprint: str = "",
    current_git_head: Optional[str] = None
) -> List[Contradiction]:
    """Audits recorded task state against physical git reality and detects contradictions."""
    contradictions: List[Contradiction] = []
    repo_root = snapshot.repo_root

    # 0. Check for unresolved git conflict markers
    conflicts = inspect_all_conflicts(repo_root)
    if conflicts:
        contradictions.append(
            Contradiction(
                type=ContradictionType.UNRESOLVED_CONFLICT_MARKERS,
                description="Unresolved git merge conflict markers present in working tree.",
                stale_claim=f"Stage: {state.current_stage.value}",
                physical_reality=f"Conflict in: {conflicts[0]}",
                severity="CRITICAL",
            )
        )

    # 1. File state contradictions (files claimed changed but don't exist and are clean)
    for f in state.changed_files:
        full_path = os.path.join(repo_root, f)
        if not os.path.exists(full_path) and f not in snapshot.dirty_files:
            contradictions.append(
                Contradiction(
                    type=ContradictionType.FILE_STATE_CONTRADICTION,
                    description=f"Recorded changed file '{f}' does not exist on disk and is clean in git.",
                    stale_claim=f"changed_files includes '{f}'",
                    physical_reality="File absent from filesystem and git index",
                    severity="WARNING",
                )
            )

    # 2. Premature completion without verified verdict
    if state.current_stage == TaskStage.COMPLETE:
        has_verified_verdict = (
            state.verification_verdict
            and state.verification_verdict.get("status") == "PASS"
        )
        if state.risk_tier == RiskTier.HIGH and not has_verified_verdict:
            contradictions.append(
                Contradiction(
                    type=ContradictionType.PREMATURE_COMPLETION,
                    description=f"Task marked COMPLETE at {state.risk_tier.value} risk, but lacks verified passing verdict.",
                    stale_claim="Stage: COMPLETE",
                    physical_reality=f"Verification verdict is {state.verification_verdict.get('status') if state.verification_verdict else 'MISSING'}",
                    severity="CRITICAL",
                )
            )
        elif state.risk_tier == RiskTier.MEDIUM and state.verification_verdict and state.verification_verdict.get("status") in ("FAIL", "BLOCK"):
            contradictions.append(
                Contradiction(
                    type=ContradictionType.PREMATURE_COMPLETION,
                    description="Task marked COMPLETE at MEDIUM risk, but contains failing/blocking verification verdict.",
                    stale_claim="Stage: COMPLETE",
                    physical_reality=f"Verification verdict is {state.verification_verdict.get('status')}",
                    severity="CRITICAL",
                )
            )
        # Working tree dirty when complete
        substantive_dirty = [
            f for f in snapshot.dirty_files
            if not f.endswith("ACTIVE_CONTEXT.md") and not f.startswith(".git")
        ]
        if substantive_dirty:
            contradictions.append(
                Contradiction(
                    type=ContradictionType.VERIFICATION_STALE_WORKING_TREE,
                    description="Task claims COMPLETE, but working tree contains uncommitted substantive changes.",
                    stale_claim="Stage: COMPLETE",
                    physical_reality=f"Dirty files: {', '.join(substantive_dirty[:3])}",
                    severity="CRITICAL",
                )
            )

    # 3. Verification Stale detection
    stale, reasons = is_verification_stale(
        state, snapshot.dirty_files, manifest_fingerprint, current_git_head
    )
    if stale:
        c_type = ContradictionType.VERIFICATION_STALE_WORKING_TREE
        if any("fingerprint" in r.lower() or "manifest" in r.lower() or "adapter" in r.lower() for r in reasons):
            c_type = ContradictionType.VERIFICATION_STALE_ADAPTER
        contradictions.append(
            Contradiction(
                type=c_type,
                description=f"Verification invalidated: {'; '.join(reasons)}",
                stale_claim=f"verification_state: {state.verification_state}",
                physical_reality="Subsequent repository modifications invalidated prior test results",
                severity="CRITICAL",
            )
        )

    # 4. Unregistered work in tree
    for df in snapshot.dirty_files:
        if (
            df not in state.changed_files
            and not df.endswith("ACTIVE_CONTEXT.md")
            and not df.startswith(".git")
        ):
            contradictions.append(
                Contradiction(
                    type=ContradictionType.UNREGISTERED_WORK_IN_TREE,
                    description=f"Working tree has modified file '{df}' not tracked in active task changed_files.",
                    stale_claim=f"changed_files: {state.changed_files}",
                    physical_reality=f"File '{df}' is modified in git working tree",
                    severity="WARNING",
                )
            )

    return contradictions


def generate_recovery_plan(
    state: Optional[TaskState],
    snapshot: WorktreeSnapshot,
    contradictions: List[Contradiction],
    invalidation_reasons: List[str]
) -> RecoveryPlan:
    """Synthesizes physical reality and contradictions into an actionable, safe RecoveryPlan."""
    preserved = list(snapshot.dirty_files)

    # Scenario 0: No prior task state exists
    if state is None:
        return RecoveryPlan(
            action="INITIALIZE_TASK",
            recommended_stage=TaskStage.INTAKE,
            recommended_status=TaskStatus.ACTIVE,
            preserved_work=preserved,
            contradictions=contradictions,
            invalidation_reasons=invalidation_reasons,
            explanation="No prior active context found on disk. Initialized fresh task at INTAKE stage.",
        )

    # Scenario 1: Unresolved git conflicts exist
    has_conflict = any(c.type == ContradictionType.UNRESOLVED_CONFLICT_MARKERS for c in contradictions)
    if has_conflict:
        return RecoveryPlan(
            action="RESOLVE_MERGE_CONFLICTS",
            recommended_stage=TaskStage.INVESTIGATE,
            recommended_status=TaskStatus.BLOCKED,
            preserved_work=preserved,
            contradictions=contradictions,
            invalidation_reasons=invalidation_reasons,
            explanation="Unresolved git conflict markers detected. Must resolve merge conflicts before proceeding.",
        )

    # Scenario 2: Verification Stale
    has_stale_verification = (
        len(invalidation_reasons) > 0
        or any(c.type in (ContradictionType.VERIFICATION_STALE_WORKING_TREE, ContradictionType.VERIFICATION_STALE_ADAPTER) for c in contradictions)
    )
    if has_stale_verification:
        return RecoveryPlan(
            action="RE_VERIFY",
            recommended_stage=TaskStage.VERIFY if state.current_stage in (TaskStage.VERIFY, TaskStage.REVIEW, TaskStage.CONSOLIDATE, TaskStage.COMPLETE) else state.current_stage,
            recommended_status=TaskStatus.VERIFICATION_STALE,
            preserved_work=preserved,
            contradictions=contradictions,
            invalidation_reasons=invalidation_reasons,
            explanation="Prior verification was invalidated by subsequent code or manifest changes. Re-testing required.",
        )

    # Scenario 3: Premature Completion
    has_premature = any(c.type == ContradictionType.PREMATURE_COMPLETION for c in contradictions)
    if has_premature:
        return RecoveryPlan(
            action="REVERT_TO_VERIFY",
            recommended_stage=TaskStage.VERIFY,
            recommended_status=TaskStatus.ACTIVE,
            preserved_work=preserved,
            contradictions=contradictions,
            invalidation_reasons=invalidation_reasons,
            explanation="Task was recorded as COMPLETE without verified passing evidence. Demoting to VERIFY stage.",
        )

    # Scenario 4: Task was INTERRUPTED
    if state.status == TaskStatus.INTERRUPTED:
        return RecoveryPlan(
            action="RESUME_STAGE",
            recommended_stage=state.current_stage,
            recommended_status=TaskStatus.ACTIVE,
            preserved_work=preserved,
            contradictions=contradictions,
            invalidation_reasons=invalidation_reasons,
            explanation=f"Resuming interrupted task safely at {state.current_stage.value} stage with {len(preserved)} preserved files.",
        )

    # Scenario 5: Task was BLOCKED
    if state.status == TaskStatus.BLOCKED:
        return RecoveryPlan(
            action="UNBLOCK",
            recommended_stage=state.current_stage,
            recommended_status=TaskStatus.BLOCKED,
            preserved_work=preserved,
            contradictions=contradictions,
            invalidation_reasons=invalidation_reasons,
            explanation=f"Task is blocked: {'; '.join(state.blockers[:3]) if state.blockers else 'Unspecified blocker'}.",
        )

    # Scenario 6: Task FAILED
    if state.status == TaskStatus.FAILED:
        return RecoveryPlan(
            action="RECOVER_FROM_FAILURE",
            recommended_stage=TaskStage.INVESTIGATE,
            recommended_status=TaskStatus.ACTIVE,
            preserved_work=preserved,
            contradictions=contradictions,
            invalidation_reasons=invalidation_reasons,
            explanation=f"Task previously failed. Resetting to INVESTIGATE to evaluate failures: {'; '.join(state.dead_ends[:2]) if state.dead_ends else 'Unknown failure'}.",
        )

    # Default / Clean Resume
    return RecoveryPlan(
        action="RESUME_WORK",
        recommended_stage=state.current_stage,
        recommended_status=TaskStatus.ACTIVE,
        preserved_work=preserved,
        contradictions=contradictions,
        invalidation_reasons=invalidation_reasons,
        explanation=f"State verified against physical git reality. Proceeding with {state.current_stage.value} stage.",
    )


def reconstruct_session_state(repo_root: str) -> Dict[str, Any]:
    """Reconstructs complete system state across Constitution, Active Context, Git, and Adapter."""
    state = parse_active_context(repo_root)
    snapshot = capture_worktree_snapshot(repo_root)
    config = load_config(repo_root)

    manifest_fingerprint = ""
    try:
        from framework.core.discovery import discover_project
        profile = discover_project(repo_root)
        manifest_fingerprint = profile.manifest_fingerprint
    except Exception:
        manifest_fingerprint = config.manifest_fingerprint

    contradictions: List[Contradiction] = []
    invalidation_reasons: List[str] = []
    if state:
        stale, reasons = is_verification_stale(state, snapshot.dirty_files, manifest_fingerprint)
        invalidation_reasons.extend(reasons)
        contradictions = detect_state_contradictions(state, snapshot, manifest_fingerprint)

    plan = generate_recovery_plan(state, snapshot, contradictions, invalidation_reasons)

    return {
        "repo_root": repo_root,
        "task_state": asdict(state) if state else None,
        "worktree_snapshot": snapshot.to_dict(),
        "adapter_config": asdict(config),
        "manifest_fingerprint": manifest_fingerprint,
        "contradictions": [c.to_dict() for c in contradictions],
        "invalidation_reasons": invalidation_reasons,
        "recovery_plan": plan.to_dict(),
    }


def recover_session(repo_root: str, apply_fix: bool = False) -> Tuple[RecoveryPlan, Optional[TaskState]]:
    """Performs deterministic session recovery.
    
    If apply_fix=True:
    - Automatically updates TaskState to match recommended_stage/status
    - Incorporates unrecorded working tree files into changed_files
    - Marks status as VERIFICATION_STALE if invalidations exist
    - Syncs updated state back to docs/ACTIVE_CONTEXT.md (strictly <= 60 lines)
    """
    state = parse_active_context(repo_root)
    snapshot = capture_worktree_snapshot(repo_root)
    config = load_config(repo_root)

    manifest_fingerprint = ""
    try:
        from framework.core.discovery import discover_project
        profile = discover_project(repo_root)
        manifest_fingerprint = profile.manifest_fingerprint
    except Exception:
        manifest_fingerprint = config.manifest_fingerprint

    contradictions: List[Contradiction] = []
    invalidation_reasons: List[str] = []
    if state:
        stale, reasons = is_verification_stale(state, snapshot.dirty_files, manifest_fingerprint)
        invalidation_reasons.extend(reasons)
        contradictions = detect_state_contradictions(state, snapshot, manifest_fingerprint)

    plan = generate_recovery_plan(state, snapshot, contradictions, invalidation_reasons)

    if apply_fix:
        if state is None:
            from framework.core.lifecycle import create_task
            state = create_task(
                mission_id="Recovered-Session",
                task_class=TaskClass.FEATURE,
                risk_tier=RiskTier.MEDIUM,
                next_action=plan.explanation
            )
        else:
            state.current_stage = plan.recommended_stage
            state.status = plan.recommended_status
            if plan.invalidation_reasons:
                state.verification_state = "VERIFICATION_STALE"
            # Incorporate substantive dirty files
            for df in snapshot.dirty_files:
                if (
                    df not in state.changed_files
                    and not df.endswith("ACTIVE_CONTEXT.md")
                    and not df.startswith(".git")
                ):
                    state.changed_files.append(df)
            state.next_action = f"{plan.action}: {plan.explanation}"

        sync_to_active_context(state, repo_root)

    return plan, state
