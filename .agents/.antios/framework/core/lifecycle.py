"""AntiOS Task Lifecycle & State Engine.

Formalizes the 10-step lifecycle progression, state transitions, interruption/recovery,
and bounded synchronization with docs/ACTIVE_CONTEXT.md.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import os
import re
from typing import Any, Dict, List, Optional, Tuple


class TaskStage(str, Enum):
    INTAKE = "INTAKE"
    UNDERSTAND = "UNDERSTAND"
    INVESTIGATE = "INVESTIGATE"
    PLAN = "PLAN"
    IMPLEMENT = "IMPLEMENT"
    TEST = "TEST"
    VERIFY = "VERIFY"
    REVIEW = "REVIEW"
    CONSOLIDATE = "CONSOLIDATE"
    COMPLETE = "COMPLETE"


class TaskStatus(str, Enum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"
    COMPLETED = "COMPLETED"
    VERIFYING = "VERIFYING"
    VERIFICATION_STALE = "VERIFICATION_STALE"


class TaskClass(str, Enum):
    FEATURE = "FEATURE"
    BUG = "BUG"
    REFACTOR = "REFACTOR"
    INVESTIGATION = "INVESTIGATION"
    DOCUMENTATION = "DOCUMENTATION"
    RELEASE = "RELEASE"
    RELEASE_MAINTENANCE = "RELEASE_MAINTENANCE"


class RiskTier(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


ORDERED_STAGES = [
    TaskStage.INTAKE,
    TaskStage.UNDERSTAND,
    TaskStage.INVESTIGATE,
    TaskStage.PLAN,
    TaskStage.IMPLEMENT,
    TaskStage.TEST,
    TaskStage.VERIFY,
    TaskStage.REVIEW,
    TaskStage.CONSOLIDATE,
    TaskStage.COMPLETE,
]


@dataclass
class TaskState:
    mission_id: str
    task_class: TaskClass = TaskClass.FEATURE
    risk_tier: RiskTier = RiskTier.MEDIUM
    current_stage: TaskStage = TaskStage.INTAKE
    status: TaskStatus = TaskStatus.ACTIVE
    active_checklist: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    dead_ends: List[str] = field(default_factory=list)
    verification_verdict: Optional[Dict[str, Any]] = None
    next_action: str = ""
    changed_files: List[str] = field(default_factory=list)
    verification_state: str = "UNVERIFIED"
    target_member: Optional[str] = None
    active_subsystem: Optional[str] = None
    pending_decisions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


def create_task(
    mission_id: str,
    task_class: TaskClass = TaskClass.FEATURE,
    risk_tier: RiskTier = RiskTier.MEDIUM,
    checklist: Optional[List[str]] = None,
    next_action: str = "",
    target_member: Optional[str] = None,
    changed_files: Optional[List[str]] = None,
    verification_state: str = "UNVERIFIED",
    pending_decisions: Optional[List[str]] = None,
    active_subsystem: Optional[str] = None,
) -> TaskState:
    """Initializes a new task state at INTAKE stage."""
    return TaskState(
        mission_id=mission_id,
        task_class=task_class,
        risk_tier=risk_tier,
        current_stage=TaskStage.INTAKE,
        status=TaskStatus.ACTIVE,
        active_checklist=checklist or [],
        next_action=next_action or "Understand boundaries and constraints.",
        target_member=target_member,
        active_subsystem=active_subsystem,
        changed_files=changed_files or [],
        verification_state=verification_state,
        pending_decisions=pending_decisions or [],
    )


def transition_stage(
    state: TaskState,
    target_stage: TaskStage,
    evidence: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str, TaskState]:
    """Transitions the task state to target_stage following deterministic rules.

    Returns:
        (success, message, updated_state)
    """
    if state.status == TaskStatus.FAILED:
        return False, "Cannot transition failed task. Must recover first.", state

    if state.status == TaskStatus.VERIFICATION_STALE and target_stage == TaskStage.COMPLETE:
        return False, "Cannot complete task in VERIFICATION_STALE state. Re-verification required.", state

    current_idx = ORDERED_STAGES.index(state.current_stage)
    target_idx = ORDERED_STAGES.index(target_stage)

    # 1. Forward single-step progression
    if target_idx == current_idx + 1:
        # Gate checks
        if target_stage == TaskStage.COMPLETE:
            # Requires verified evidence or passing verdict
            if state.risk_tier == RiskTier.HIGH:
                if not state.verification_verdict or state.verification_verdict.get("status") != "PASS":
                    return False, "High-risk task requires verified verdict before COMPLETE.", state
            elif state.verification_verdict and state.verification_verdict.get("status") in ("FAIL", "BLOCK"):
                return False, f"Cannot complete task with failing verifier verdict ({state.verification_verdict.get('status')}).", state

        state.current_stage = target_stage
        if target_stage == TaskStage.COMPLETE:
            state.status = TaskStatus.COMPLETED
        elif target_stage == TaskStage.VERIFY:
            state.status = TaskStatus.VERIFYING
        else:
            state.status = TaskStatus.ACTIVE

        if evidence:
            state.metadata.update(evidence)
        return True, f"Transitioned to {target_stage.value}", state

    # 2. Backward transitions (Recovery / Re-attempt)
    if target_idx < current_idx:
        state.current_stage = target_stage
        state.status = TaskStatus.ACTIVE
        if evidence:
            state.metadata.update(evidence)
        return True, f"Reverted stage to {target_stage.value} for recovery/re-iteration", state

    # 3. Same stage (update)
    if target_idx == current_idx:
        if evidence:
            state.metadata.update(evidence)
        return True, f"Updated stage {target_stage.value}", state

    # 4. Disallowed multi-step skipping
    return False, f"Invalid stage transition: cannot jump from {state.current_stage.value} to {target_stage.value} (must follow progression)", state


def interrupt_task(state: TaskState, reason: str) -> TaskState:
    """Marks task as interrupted while preserving stage and state."""
    state.status = TaskStatus.INTERRUPTED
    if reason and reason not in state.blockers:
        state.blockers.append(reason)
    state.next_action = f"Resume from {state.current_stage.value}: {reason}"
    return state


def block_task(state: TaskState, reason: str) -> TaskState:
    """Marks task as blocked."""
    state.status = TaskStatus.BLOCKED
    if reason and reason not in state.blockers:
        state.blockers.append(reason)
    state.next_action = f"Unblock {state.current_stage.value}: {reason}"
    return state


def recover_task(state: TaskState, recovery_action: str) -> TaskState:
    """Recovers an interrupted or blocked task to ACTIVE."""
    state.status = TaskStatus.ACTIVE
    state.next_action = recovery_action
    return state


def fail_task(state: TaskState, reason: str) -> TaskState:
    """Marks task as failed and logs reason to dead ends."""
    state.status = TaskStatus.FAILED
    state.dead_ends.append(reason)
    state.next_action = f"Resolve failure in {state.current_stage.value}: {reason}"
    return state


def sync_to_active_context(state: TaskState, repo_root: str) -> str:
    """Serializes TaskState to docs/ACTIVE_CONTEXT.md adhering strictly to <= 60 lines budget."""
    docs_dir = os.path.join(repo_root, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    target_path = os.path.join(docs_dir, "ACTIVE_CONTEXT.md")

    # Header lines
    header_lines = [
        "# Active Context (`docs/ACTIVE_CONTEXT.md`)",
        "",
        f"**Mission**: {state.mission_id}",
        f"**Class**: {state.task_class.value} | **Risk**: {state.risk_tier.value}",
        f"**Stage**: {state.current_stage.value} | **Status**: {state.status.value}",
    ]
    if state.target_member:
        header_lines.append(f"**Target Member**: {state.target_member}")
    if state.active_subsystem:
        header_lines.append(f"**Subsystem**: {state.active_subsystem}")

    # 1. Active Checklist (capped to 8 items to stay within budget)
    checklist_items = state.active_checklist[:8] if state.active_checklist else ["[ ] Initial task execution"]
    checklist_lines = [
        f"- [{'x' if item.startswith('[x]') or item.startswith('- [x]') else ' '}] {item.replace('- [x]', '').replace('- [ ]', '').replace('[x]', '').replace('[ ]', '').strip()}"
        for item in checklist_items
    ]

    # 2. Blockers & Invariants (including pending decisions if any)
    blocker_lines = []
    if state.pending_decisions:
        for dec in state.pending_decisions[:3]:
            blocker_lines.append(f"- [Pending Decision] {dec}")
    if state.blockers:
        for b in state.blockers[:5]:
            blocker_lines.append(f"- {b}")
    if not blocker_lines:
        blocker_lines = ["- None"]

    # 3. Changed Files & Verification State
    changed_lines = [f"- Verification State: {state.verification_state}"]
    if state.changed_files:
        changed_lines.append("- Changed Files:")
        for cf in state.changed_files:
            changed_lines.append(f"  - {cf}")
    else:
        changed_lines.append("- Changed Files: None")

    if state.verification_verdict:
        v_status = state.verification_verdict.get('status', 'UNKNOWN')
        v_summary = state.verification_verdict.get('summary', '')
        extra = []
        if state.verification_verdict.get('git_head'):
            extra.append(f"head:{state.verification_verdict['git_head']}")
        if state.verification_verdict.get('manifest_fingerprint'):
            extra.append(f"fp:{state.verification_verdict['manifest_fingerprint']}")
        tag = f" [{', '.join(extra)}]" if extra else ""
        changed_lines.append(f"- Verdict: {v_status} ({v_summary}){tag}")

    # 4. Dead-End Memory & Candidate Lessons
    dead_end_lines = [f"- {d}" for d in state.dead_ends[:5]] if state.dead_ends else ["- None"]

    # 5. Next Immediate Action
    action_text = state.next_action or f"Execute {state.current_stage.value} stage."

    sep = "\n"
    sections = [
        sep.join(header_lines),
        "",
        "## 1. Active Checklist",
        sep.join(checklist_lines),
        "",
        "## 2. Blockers & Invariants",
        sep.join(blocker_lines),
        "",
        "## 3. Changed Files & Verification State",
        sep.join(changed_lines),
        "",
        "## 4. Dead-End Memory & Candidate Lessons",
        sep.join(dead_end_lines),
        "",
        "## 5. Next Immediate Action",
        action_text,
    ]
    content = "\n".join(sections).strip() + "\n"
    lines = content.splitlines()
    if len(lines) > 60:
        lines = lines[:60]
        content = "\n".join(lines) + "\n"

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
    return target_path


def parse_active_context(repo_root: str) -> Optional[TaskState]:
    """Parses docs/ACTIVE_CONTEXT.md back into TaskState during session resumption."""
    target_path = os.path.join(repo_root, "docs", "ACTIVE_CONTEXT.md")
    if not os.path.isfile(target_path):
        return None

    try:
        with open(target_path, "r", encoding="utf-8-sig") as f:
            text = f.read()

        mission_match = re.search(r"\*\*(?:Current )?Mission\*\*:\s*([^\n]+)", text)
        mission_id = mission_match.group(1).strip() if mission_match else "Recovered-Mission"

        class_match = re.search(r"\*\*Class\*\*:\s*([A-Z_]+)", text)
        task_class = TaskClass(class_match.group(1).strip()) if class_match and class_match.group(1).strip() in TaskClass.__members__ else TaskClass.FEATURE

        risk_match = re.search(r"\*\*Risk\*\*:\s*([A-Z_]+)", text)
        risk_tier = RiskTier(risk_match.group(1).strip()) if risk_match and risk_match.group(1).strip() in RiskTier.__members__ else RiskTier.MEDIUM

        stage_match = re.search(r"\*\*Stage\*\*:\s*([A-Z_]+)", text)
        stage = TaskStage(stage_match.group(1).strip()) if stage_match and stage_match.group(1).strip() in TaskStage.__members__ else TaskStage.INTAKE

        status_match = re.search(r"\*\*Status\*\*:\s*([A-Z_]+)", text)
        status = TaskStatus(status_match.group(1).strip()) if status_match and status_match.group(1).strip() in TaskStatus.__members__ else TaskStatus.ACTIVE

        member_match = re.search(r"\*\*Target Member\*\*:\s*([^\n]+)", text)
        target_member = None
        if member_match:
            val = member_match.group(1).strip()
            if val and val.lower() != "none":
                target_member = val

        subsystem_match = re.search(r"\*\*Subsystem\*\*:\s*([^\n]+)", text)
        active_subsystem = None
        if subsystem_match:
            val = subsystem_match.group(1).strip()
            if val and val.lower() != "none":
                active_subsystem = val

        # Verification state
        verif_state_match = re.search(r"(?:-\s*Verification State|\*\*Verification State\*\*):\s*([A-Z_]+)", text, re.IGNORECASE)
        verification_state = verif_state_match.group(1).strip() if verif_state_match else "UNVERIFIED"

        # Changed files
        changed_files: List[str] = []
        cf_block_match = re.search(r"-\s*Changed Files:\s*\n((?:\s+-\s+[^\n]+\n*)+)", text)
        if cf_block_match:
            for line in cf_block_match.group(1).splitlines():
                line = line.strip()
                if line.startswith("- "):
                    fpath = line[2:].strip()
                    if fpath and not fpath.startswith("...") and fpath.lower() != "none":
                        changed_files.append(fpath)
        else:
            # Inline check: - Changed Files: foo.py, bar.py
            cf_inline_match = re.search(r"-\s*Changed Files:\s*([^\n]+)", text)
            if cf_inline_match:
                val = cf_inline_match.group(1).strip()
                if val.lower() != "none":
                    changed_files = [p.strip() for p in val.split(",") if p.strip() and not p.strip().startswith("...")]

        # Pending decisions & blockers from Section 2
        pending_decisions: List[str] = []
        blockers: List[str] = []
        sec2_match = re.search(r"## 2\. Blockers & Invariants\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
        if sec2_match:
            for b_line in sec2_match.group(1).splitlines():
                b_line = b_line.strip()
                if not b_line.startswith("- "):
                    continue
                content = b_line[2:].strip()
                if content.lower() == "none":
                    continue
                if content.startswith("[Pending Decision]"):
                    dec_name = content.replace("[Pending Decision]", "").strip()
                    if dec_name:
                        pending_decisions.append(dec_name)
                else:
                    blockers.append(content)

        # Check for header pending decisions if not in section 2
        if not pending_decisions:
            hdr_dec_match = re.search(r"\*\*Pending Decisions?\*\*:\s*([^\n]+)", text)
            if hdr_dec_match:
                d_val = hdr_dec_match.group(1).strip()
                if d_val.lower() != "none":
                    pending_decisions = [d.strip() for d in d_val.split(",") if d.strip()]

        # Active checklist from Section 1
        active_checklist: List[str] = []
        sec1_match = re.search(r"## 1\. Active (?:Checklist|Tasks|Objective)\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
        if sec1_match:
            for c_line in sec1_match.group(1).splitlines():
                c_line = c_line.strip()
                if c_line.startswith("- ["):
                    active_checklist.append(c_line)

        # Dead ends from Section 4
        dead_ends: List[str] = []
        sec4_match = re.search(r"## 4\. Dead-End Memory[^\n]*\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
        if sec4_match:
            for d_line in sec4_match.group(1).splitlines():
                d_line = d_line.strip()
                if d_line.startswith("- ") and d_line[2:].strip().lower() != "none":
                    dead_ends.append(d_line[2:].strip())

        # Verification verdict
        verification_verdict = None
        verdict_match = re.search(r"-\s*Verdict:\s*([A-Z_]+)\s*(?:\(([^)]*)\))?(?:\s*\[([^\]]*)\])?", text)
        if verdict_match:
            v_status = verdict_match.group(1).strip()
            v_summary = verdict_match.group(2).strip() if verdict_match.group(2) else ""
            verification_verdict = {"status": v_status, "summary": v_summary}
            if verdict_match.group(3):
                tags_str = verdict_match.group(3).strip()
                for tag in tags_str.split(","):
                    if ":" in tag:
                        k, v = tag.split(":", 1)
                        k = k.strip()
                        v = v.strip()
                        if k == "head":
                            verification_verdict["git_head"] = v
                        elif k == "fp":
                            verification_verdict["manifest_fingerprint"] = v

        action_match = re.search(r"## 5\. Next Immediate Action\s*\n([^\n#]+)", text)
        next_action = action_match.group(1).strip() if action_match else ""

        return TaskState(
            mission_id=mission_id,
            task_class=task_class,
            risk_tier=risk_tier,
            current_stage=stage,
            status=status,
            active_checklist=active_checklist,
            blockers=blockers,
            dead_ends=dead_ends,
            verification_verdict=verification_verdict,
            next_action=next_action,
            changed_files=changed_files,
            verification_state=verification_state,
            target_member=target_member,
            active_subsystem=active_subsystem,
            pending_decisions=pending_decisions,
        )
    except Exception:
        return None
