"""AntiOS 2.0 Constitutional Orchestration Engine & Adaptive Workforce Architecture.

Phases 83–86: Native Antigravity Orchestration & Teamwork-Grade Workforce Architecture.

Authoritative AntiOS mission orchestration layer implementing:
- Hard Constitutional Limits:
    MAX_ACTIVE_AGENTS_PER_WAVE = 10
    MAX_TOTAL_SPAWNED_AGENTS = 20 (across entire mission delegation tree)
    MAX_DELEGATION_DEPTH = 2 (Shallow Depth Law: Root=0 -> Child=1 -> Grandchild=2)
    MAX_WORKER_RETRIES_PER_ROLE = 2 (Anti-Hydra retry loop limit)
- Adaptive Workforce Sizing & Cost Reasoning:
    SOLO, FOCUSED, SMALL, PARALLEL, STAGED, HIERARCHICAL, MAX
    AdaptiveWorkforcePlanner evaluates 12 inputs and token-bounded cost reasoning
    (Why this workforce, Why not fewer workers, Why not more workers).
- Teamwork-Grade Wave Lifecycle:
    PLAN -> DISPATCH -> EXECUTE -> COLLECT -> RECONCILE -> VERIFY -> COLLAPSE -> NEXT_WAVE
    NEXT_WAVE is strictly blocked while active_total != 0.
- Anti-Hydra Protection:
    WorkerMetadata required for every spawn (mission_id, wave_id, parent_id,
    capability, purpose, write_boundary, risk_tier, expected_output, verification_requirement).
    Rejects anonymous workers, duplicate specialists, recursive spawning, and runaway retries.
- Controlled Parallel Writing:
    Single writer default. Parallel writing allowed only when file boundaries are proven disjoint.
    Overlapping boundaries automatically fall back to Controlled Single Writer (serialization).
- Wave State Persistence & Interrupted Mission Recovery:
    WavePersistenceEngine saves and restores mission state for deterministic recovery.
- Failure & Recovery Engine:
    Handles timeout, crash, partial result, conflicting result, duplicate result, stale result,
    verification failure, write collision, capability unavailable, MCP unavailable.
    Prefers RETRY_SAME_WORKER_CONTEXT over SPAWN_NEW_WORKER when safe.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union


# Constitutional Hard Limits
MAX_ACTIVE_AGENTS_PER_WAVE = 10
MAX_TOTAL_SPAWNED_AGENTS = 20
MAX_DELEGATION_DEPTH = 2
MAX_WORKER_RETRIES_PER_ROLE = 2


class OrchestrationBudgetExceeded(Exception):
    """Raised when an operation attempts to exceed constitutional agent limits."""
    pass


class WorkforceMode(str, Enum):
    """Adaptive workforce sizing modes."""
    SOLO = "SOLO"                     # 0 subagents (parent handles directly)
    FOCUSED = "FOCUSED"               # 1 specialist (focused investigation / implementation)
    SMALL = "SMALL"                   # 2 specialists (paired streams)
    PARALLEL = "PARALLEL"             # 2-4 specialists across independent streams
    STAGED = "STAGED"                 # Multi-wave staged progression
    HIERARCHICAL = "HIERARCHICAL"     # Coordinator with delegated leaf children
    MAX = "MAX"                       # Budget-capped ceiling (<=10 active, <=20 total)


class WaveState(str, Enum):
    """State of an execution wave."""
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    CONSOLIDATING = "CONSOLIDATING"
    COLLAPSED = "COLLAPSED"


class WaveLifecycleStage(str, Enum):
    """Canonical 8-step teamwork wave lifecycle."""
    PLAN = "PLAN"
    DISPATCH = "DISPATCH"
    EXECUTE = "EXECUTE"
    COLLECT = "COLLECT"
    RECONCILE = "RECONCILE"
    VERIFY = "VERIFY"
    COLLAPSE = "COLLAPSE"
    NEXT_WAVE = "NEXT_WAVE"


class CanonicalWave(str, Enum):
    """Canonical mission wave stages."""
    RECONNAISSANCE = "RECONNAISSANCE"
    PLANNING = "PLANNING"
    IMPLEMENTATION = "IMPLEMENTATION"
    VERIFICATION = "VERIFICATION"
    DELIVERY = "DELIVERY"


class CoordinationLevel(str, Enum):
    """Progressive coordination depth matching task complexity."""
    L0 = "L0"  # Tiny / Solo: No persistent coordination files
    L1 = "L1"  # Focused / Small: Lightweight structured summaries
    L2 = "L2"  # Multi-Wave: Artifact-based state (mission.md, progress.md, dead-ends.md)
    L3 = "L3"  # Large / Hierarchical: Full mission ledger, gates, and final audit


class WriteSafetyPolicy(str, Enum):
    """Policy governing concurrent write safety."""
    READ_ONLY = "READ_ONLY"
    CONTROLLED_SINGLE_WRITER = "CONTROLLED_SINGLE_WRITER"
    SAFELY_PARALLELIZABLE = "SAFELY_PARALLELIZABLE"
    UNSAFE_TO_PARALLELIZE = "UNSAFE_TO_PARALLELIZE"
    DISJOINT_BRANCHES = "DISJOINT_BRANCHES"


class DispatchGateType(str, Enum):
    """Types of mandatory dispatch gates."""
    PRE_PLANNING = "PRE_PLANNING"
    EXECUTION_DISPATCH = "EXECUTION_DISPATCH"


class GateDecision(str, Enum):
    """Outcomes of dispatch gate evaluation."""
    SOLO_AUTHORIZED = "SOLO_AUTHORIZED"
    DELEGATION_MANDATORY = "DELEGATION_MANDATORY"
    COORDINATOR_AUTHORIZED = "COORDINATOR_AUTHORIZED"
    BLOCKED = "BLOCKED"


class FailureType(str, Enum):
    """Failure classes encountered during autonomous execution."""
    TIMEOUT = "TIMEOUT"
    CRASH = "CRASH"
    PARTIAL_RESULT = "PARTIAL_RESULT"
    CONFLICTING_RESULT = "CONFLICTING_RESULT"
    DUPLICATE_RESULT = "DUPLICATE_RESULT"
    STALE_RESULT = "STALE_RESULT"
    VERIFICATION_FAILURE = "VERIFICATION_FAILURE"
    WRITE_COLLISION = "WRITE_COLLISION"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    MCP_UNAVAILABLE = "MCP_UNAVAILABLE"
    UNGROUNDED_EVIDENCE = "UNGROUNDED_EVIDENCE"


class RecoveryAction(str, Enum):
    """Deterministic recovery actions for execution failures."""
    RETRY_SAME_WORKER_CONTEXT = "RETRY_SAME_WORKER_CONTEXT"
    REASSIGN_WORKER = "REASSIGN_WORKER"
    SPAWN_NEW_WORKER = "SPAWN_NEW_WORKER"
    TAKEOVER_DIRECT = "TAKEOVER_DIRECT"
    FAIL_CLOSED = "FAIL_CLOSED"


@dataclass
class FailureRecoveryDecision:
    """Decision emitted by FailureRecoveryEngine."""
    failure_type: FailureType
    action: RecoveryAction
    worker_id: str
    rationale: str
    can_consume_budget: bool = False
    retry_prompt: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_type": self.failure_type.value,
            "action": self.action.value,
            "worker_id": self.worker_id,
            "rationale": self.rationale,
            "can_consume_budget": self.can_consume_budget,
            "retry_prompt": self.retry_prompt,
        }


@dataclass
class WorkerMetadata:
    """Non-negotiable deterministic metadata required for every worker spawn (Anti-Hydra Protection)."""
    mission_id: str
    wave_id: int
    parent_id: Optional[str]
    capability: str
    purpose: str = ""
    write_boundary: List[str] = field(default_factory=list)
    risk_tier: str = "MEDIUM"
    expected_output: str = ""
    verification_requirement: str = ""
    goal: Optional[str] = None

    def __post_init__(self) -> None:
        if self.goal and not self.purpose:
            self.purpose = self.goal
        elif self.purpose and not self.goal:
            self.goal = self.purpose

    def validate(self) -> Tuple[bool, List[str]]:
        """Validates that worker is fully specified (no anonymous workers)."""
        errors: List[str] = []
        if not self.mission_id or not self.mission_id.strip():
            errors.append("WorkerMetadata missing required 'mission_id'.")
        if self.wave_id <= 0:
            errors.append("WorkerMetadata 'wave_id' must be >= 1.")
        if not self.capability or not self.capability.strip():
            errors.append("WorkerMetadata missing required 'capability' (no capability-free workers).")
        if not self.purpose or not self.purpose.strip():
            errors.append("WorkerMetadata missing required 'purpose'.")
        if not self.expected_output or not self.expected_output.strip():
            errors.append("WorkerMetadata missing required 'expected_output'.")
        if not self.verification_requirement or not self.verification_requirement.strip():
            errors.append("WorkerMetadata missing required 'verification_requirement'.")
        return len(errors) == 0, errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "wave_id": self.wave_id,
            "parent_id": self.parent_id,
            "capability": self.capability,
            "purpose": self.purpose,
            "goal": self.purpose,
            "write_boundary": list(self.write_boundary),
            "risk_tier": self.risk_tier,
            "expected_output": self.expected_output,
            "verification_requirement": self.verification_requirement,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkerMetadata:
        return cls(
            mission_id=str(data.get("mission_id", "")),
            wave_id=int(data.get("wave_id", 1)),
            parent_id=data.get("parent_id"),
            capability=str(data.get("capability", "")),
            purpose=str(data.get("purpose", "")),
            write_boundary=list(data.get("write_boundary", [])),
            risk_tier=str(data.get("risk_tier", "MEDIUM")),
            expected_output=str(data.get("expected_output", "")),
            verification_requirement=str(data.get("verification_requirement", "")),
        )


@dataclass
class StructuredHandoff:
    """Standardized evidence handoff contract returned by specialists."""
    objective: str
    observations: List[str] = field(default_factory=list)
    logic_chain: str = ""
    evidence: List[str] = field(default_factory=list)
    caveats: List[str] = field(default_factory=list)
    conclusion: str = ""
    verification_method: str = ""
    next_owner: str = "primary-engineer"

    def validate(self) -> Tuple[bool, List[str]]:
        """Deterministically validates handoff completeness and evidence grounding."""
        errors: List[str] = []
        if not self.objective or not self.objective.strip():
            errors.append("Handoff missing required objective.")
        if not self.conclusion or not self.conclusion.strip():
            errors.append("Handoff missing required conclusion.")
        if not self.verification_method or not self.verification_method.strip():
            errors.append("Handoff missing required verification_method.")
        if not self.evidence or len(self.evidence) == 0:
            errors.append("Handoff missing concrete evidence (must include file paths, diffs, or commands).")
        else:
            has_grounding = any(
                any(marker in str(e) for marker in (":", "/", "\\", "diff", "exit", "test", "line", "def ", "class "))
                for e in self.evidence if isinstance(e, str)
            )
            if not has_grounding:
                errors.append("Evidence lacks grounding (no file paths, symbols, lines, or command outputs found).")
        return len(errors) == 0, errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective": self.objective,
            "observations": list(self.observations),
            "logic_chain": self.logic_chain,
            "evidence": list(self.evidence),
            "caveats": list(self.caveats),
            "conclusion": self.conclusion,
            "verification_method": self.verification_method,
            "next_owner": self.next_owner,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StructuredHandoff:
        return cls(
            objective=str(data.get("objective", "")),
            observations=list(data.get("observations", [])),
            logic_chain=str(data.get("logic_chain", "")),
            evidence=list(data.get("evidence", [])),
            caveats=list(data.get("caveats", [])),
            conclusion=str(data.get("conclusion", "")),
            verification_method=str(data.get("verification_method", "")),
            next_owner=str(data.get("next_owner", "primary-engineer")),
        )


@dataclass
class AgentRecord:
    """Tracking record for a spawned subagent in the mission tree."""
    agent_id: str
    role: str
    depth: int
    wave_number: int
    spawned_at: float = field(default_factory=time.time)
    terminated_at: Optional[float] = None
    is_active: bool = True
    handoff: Optional[StructuredHandoff] = None
    parent_id: Optional[str] = None
    is_coordinator: bool = False
    reserved_quota: int = 0
    actually_spawned: int = 0
    failure_reason: Optional[str] = None
    metadata: Optional[WorkerMetadata] = None


@dataclass
class WorkforceCostReasoning:
    """Multi-input cost reasoning explaining workforce mode selection (Phase 84)."""
    why_this_workforce: str = ""
    why_not_fewer: str = ""
    why_not_more: str = ""
    max_recommended_workers: int = 1
    mode: WorkforceMode = WorkforceMode.SOLO
    coordination_cost_tokens: int = 0
    write_collision_risk: str = "MINIMAL"
    decision_inputs: Dict[str, Any] = field(default_factory=dict)

    # Aliases for backwards compatibility with DualDispatchGates:
    selected_mode: Optional[WorkforceMode] = None
    recommended_workers: Optional[int] = None
    why_not_fewer_workers: Optional[str] = None
    why_not_more_workers: Optional[str] = None

    def __post_init__(self) -> None:
        if self.selected_mode is not None:
            self.mode = self.selected_mode
        elif self.mode and self.selected_mode is None:
            self.selected_mode = self.mode

        if self.recommended_workers is not None:
            self.max_recommended_workers = self.recommended_workers
        elif self.max_recommended_workers and self.recommended_workers is None:
            self.recommended_workers = self.max_recommended_workers

        if self.why_not_fewer_workers is not None and not self.why_not_fewer:
            self.why_not_fewer = self.why_not_fewer_workers
        elif self.why_not_fewer and self.why_not_fewer_workers is None:
            self.why_not_fewer_workers = self.why_not_fewer

        if self.why_not_more_workers is not None and not self.why_not_more:
            self.why_not_more = self.why_not_more_workers
        elif self.why_not_more and self.why_not_more_workers is None:
            self.why_not_more_workers = self.why_not_more

    def format_token_bounded(self, max_lines: int = 12) -> str:
        """Emits a concise rationale card strictly <= max_lines."""
        lines = [
            "--- WORKFORCE COST REASONING ---",
            f"Mode:          {self.mode.value} (Max: {self.max_recommended_workers})",
            f"Why This:      {self.why_this_workforce}",
            f"Why Not Fewer: {self.why_not_fewer}",
            f"Why Not More:  {self.why_not_more}",
            f"Coord Cost:    ~{self.coordination_cost_tokens} tokens",
            f"Collision Risk:{self.write_collision_risk}",
            "--------------------------------",
        ]
        return "\n".join(lines[:max_lines])

    def format_explanation_card(self, max_lines: int = 12) -> str:
        """Alias for format_token_bounded adhering to budget."""
        return self.format_token_bounded(max_lines=max_lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value if isinstance(self.mode, WorkforceMode) else str(self.mode),
            "selected_mode": self.mode.value if isinstance(self.mode, WorkforceMode) else str(self.mode),
            "max_recommended_workers": self.max_recommended_workers,
            "recommended_workers": self.max_recommended_workers,
            "why_this_workforce": self.why_this_workforce,
            "why_not_fewer": self.why_not_fewer,
            "why_not_more": self.why_not_more,
            "why_not_fewer_workers": self.why_not_fewer,
            "why_not_more_workers": self.why_not_more,
            "coordination_cost_tokens": self.coordination_cost_tokens,
            "write_collision_risk": self.write_collision_risk,
            "decision_inputs": dict(self.decision_inputs),
        }


@dataclass
class DispatchGateResult:
    """Structured evaluation from a Pre-Planning or Execution Dispatch Gate."""
    gate_type: DispatchGateType
    decision: GateDecision
    mode: WorkforceMode
    recommended_workers: int
    reasons: List[str]
    checklist: Dict[str, Any] = field(default_factory=dict)
    budget_reserved: int = 0
    cost_reasoning: Optional[WorkforceCostReasoning] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "gate_type": self.gate_type.value,
            "decision": self.decision.value,
            "mode": self.mode.value,
            "recommended_workers": self.recommended_workers,
            "reasons": list(self.reasons),
            "checklist": dict(self.checklist),
            "budget_reserved": self.budget_reserved,
        }
        if self.cost_reasoning:
            d["cost_reasoning"] = self.cost_reasoning.to_dict()
        return d


@dataclass
class MissionLedger:
    """Authoritative mission-wide resource ledger for AntiOS orchestration.
    
    Tracks global launches, active concurrency, coordinator reservations,
    wave states, worker outcomes, and enforces Anti-Hydra protection.
    """
    mission_id: str = "mission-001"
    max_active_per_wave: int = MAX_ACTIVE_AGENTS_PER_WAVE
    max_total_spawned: int = MAX_TOTAL_SPAWNED_AGENTS
    max_depth: int = MAX_DELEGATION_DEPTH
    max_retries_per_role: int = MAX_WORKER_RETRIES_PER_ROLE
    spawned_total: int = 0
    active_total: int = 0
    current_wave: int = 0
    current_depth: int = 0
    active_workers: List[str] = field(default_factory=list)
    worker_roles: Dict[str, str] = field(default_factory=dict)
    reserved_capacity: Dict[str, int] = field(default_factory=dict)
    completed_workers: List[str] = field(default_factory=list)
    failed_workers: List[str] = field(default_factory=list)
    collapsed_workers: List[str] = field(default_factory=list)
    records: Dict[str, AgentRecord] = field(default_factory=dict)

    @property
    def remaining_budget(self) -> int:
        """Global launches remaining across Root + Children."""
        return max(0, self.max_total_spawned - self.spawned_total)

    @property
    def available_active_slots(self) -> int:
        """Available concurrency slots in the current wave."""
        return max(0, self.max_active_per_wave - self.active_total)

    def can_spawn(
        self,
        depth: int = 1,
        parent_id: Optional[str] = None,
        role: Optional[str] = None,
        write_boundary: Optional[List[str]] = None,
        wave_number: Optional[int] = None,
        metadata: Optional["WorkerMetadata"] = None,
    ) -> Tuple[bool, str]:
        """Pre-spawn gate verifying all constitutional and Anti-Hydra constraints."""
        # 1. Shallow Depth Law
        if depth > self.max_depth:
            return False, f"Shallow Depth Law violation: depth {depth} exceeds constitutional limit {self.max_depth}"

        # 2. Grandchild delegation attempt (depth 2 cannot spawn depth 3)
        if parent_id and parent_id in self.records:
            parent_rec = self.records[parent_id]
            if parent_rec.depth >= 2:
                return False, f"Shallow Depth Law violation: leaf worker '{parent_id}' at depth {parent_rec.depth} cannot delegate"

        # 3. Constitutional launch ceilings
        if self.spawned_total >= self.max_total_spawned:
            return False, f"Constitutional ceiling reached: spawned {self.spawned_total}/{self.max_total_spawned} total agents"
        if self.active_total >= self.max_active_per_wave:
            return False, f"Wave concurrency limit reached: active {self.active_total}/{self.max_active_per_wave} agents"

        # 4. Coordinator quota checks
        if parent_id and parent_id in self.records:
            parent_rec = self.records[parent_id]
            if parent_rec.is_coordinator:
                reserved = self.reserved_capacity.get(parent_id, 0)
                if parent_rec.actually_spawned >= reserved:
                    return False, f"Coordinator '{parent_id}' exceeded reserved child quota ({reserved})"

        # 5. Anti-Hydra: Duplicate active specialist check in same wave
        if role and wave_number is not None and metadata is not None:
            active_same_role = [
                aid for aid in self.active_workers
                if aid in self.records and self.records[aid].role == role and self.records[aid].wave_number == wave_number
            ]
            for other_id in active_same_role:
                other_rec = self.records[other_id]
                if other_rec.metadata:
                    # Identical goal check
                    if (
                        other_rec.metadata.goal
                        and metadata.goal
                        and other_rec.metadata.goal.strip().lower() == metadata.goal.strip().lower()
                    ):
                        return False, f"Anti-Hydra Protection: Duplicate active specialist '{role}' with identical goal detected in wave {wave_number}"
                    # Overlapping write boundaries check
                    other_bounds = set(b.replace("\\", "/").strip().lower() for b in other_rec.metadata.write_boundary)
                    this_bounds = set(b.replace("\\", "/").strip().lower() for b in metadata.write_boundary)
                    if other_bounds and this_bounds and other_bounds.intersection(this_bounds):
                        return False, f"Anti-Hydra Protection: Duplicate active specialist '{role}' with overlapping write boundary detected in wave {wave_number}"

        # 6. Anti-Hydra: Runaway retry loop check
        if role:
            role_failures = sum(1 for rec in self.records.values() if rec.role == role and rec.failure_reason)
            if role_failures >= self.max_retries_per_role:
                return False, f"Anti-Hydra Protection: Retry limit reached for role '{role}' ({role_failures}/{self.max_retries_per_role}). Runaway retry loop prevented."

        # 7. Anti-Hydra: Write boundary collision check
        if write_boundary:
            norm_new_bounds = {b.replace("\\", "/").strip().lower() for b in write_boundary}
            for aid in self.active_workers:
                rec = self.records.get(aid)
                if rec and rec.metadata and rec.metadata.write_boundary:
                    existing_bounds = {b.replace("\\", "/").strip().lower() for b in rec.metadata.write_boundary}
                    collisions = norm_new_bounds.intersection(existing_bounds)
                    if collisions:
                        return False, f"Anti-Hydra Protection: Write collision with active worker '{aid}' on {collisions}"

        return True, "Spawn authorized within constitutional limits"

    def can_activate(self) -> Tuple[bool, str]:
        """Verifies whether a new worker can be activated concurrently."""
        if self.active_total >= self.max_active_per_wave:
            return False, f"Cannot activate: active total {self.active_total} at wave ceiling {self.max_active_per_wave}"
        return True, "Concurrency capacity available"

    def can_enter_next_wave(self, previous_wave_collapsed: bool) -> Tuple[bool, str]:
        """Enforces mandatory wave collapse before advancing."""
        if not previous_wave_collapsed:
            return False, "Previous wave has not been collapsed"
        if self.active_total > 0:
            return False, f"Cannot advance wave: {self.active_total} uncollapsed active workers remain"
        return True, "Next wave entry authorized"

    def can_retry(self, agent_id: str) -> Tuple[bool, str]:
        """Verifies whether an agent operation can be retried via new worker launch."""
        if self.remaining_budget <= 0:
            return False, "Cannot retry: mission launch budget exhausted (0 remaining)"
        if agent_id in self.records:
            role = self.records[agent_id].role
            role_failures = sum(1 for rec in self.records.values() if rec.role == role and rec.failure_reason)
            if role_failures >= self.max_retries_per_role:
                return False, f"Anti-Hydra Protection: Excessive failure retries for role '{role}' ({role_failures})"
        return True, "Retry authorized (will consume 1 launch slot)"

    def can_delegate(self, coordinator_id: str) -> Tuple[bool, str]:
        """Verifies if a coordinator has reserved delegation capacity."""
        if coordinator_id not in self.records:
            return False, f"Unknown coordinator '{coordinator_id}'"
        rec = self.records[coordinator_id]
        if not rec.is_coordinator:
            return False, f"Agent '{coordinator_id}' is not designated as a coordinator"
        quota = self.reserved_capacity.get(coordinator_id, 0)
        if rec.actually_spawned >= quota:
            return False, f"Coordinator quota exhausted ({rec.actually_spawned}/{quota})"
        if self.remaining_budget <= 0:
            return False, "Global mission budget exhausted"
        return True, "Delegation authorized"

    def reserve_capacity(self, coordinator_id: str, quota: int) -> Tuple[bool, str]:
        """Pre-allocates a local child quota for a coordinator from unreserved global budget."""
        if quota <= 0:
            return False, "Quota must be greater than zero"
        total_reserved = sum(self.reserved_capacity.values())
        unreserved_budget = self.remaining_budget - total_reserved
        if quota > unreserved_budget:
            return False, f"Requested quota {quota} exceeds unreserved budget {unreserved_budget}"
        if quota > 4:
            return False, "Coordinator quota cannot exceed 4 to ensure shallow, bounded execution"

        self.reserved_capacity[coordinator_id] = quota
        if coordinator_id in self.records:
            self.records[coordinator_id].is_coordinator = True
            self.records[coordinator_id].reserved_quota = quota
        return True, f"Reserved {quota} child slots for coordinator '{coordinator_id}'"

    def release_capacity(self, coordinator_id: str) -> int:
        """Reverts unused coordinator quota back to the unreserved mission pool."""
        if coordinator_id not in self.reserved_capacity:
            return 0
        quota = self.reserved_capacity.pop(coordinator_id)
        actually_used = 0
        if coordinator_id in self.records:
            actually_used = self.records[coordinator_id].actually_spawned
        unused = max(0, quota - actually_used)
        return unused

    def record_spawn(
        self,
        agent_id: str,
        role: str,
        depth: int,
        wave_number: int,
        parent_id: Optional[str] = None,
        is_coordinator: bool = False,
        metadata: Optional[WorkerMetadata] = None,
    ) -> AgentRecord:
        """Consumes a launch slot, validates metadata, and increments active count."""
        # Validate metadata if provided
        write_bounds = metadata.write_boundary if metadata else None
        if metadata:
            valid, errs = metadata.validate()
            if not valid:
                raise ValueError(f"Anti-Hydra Protection: Invalid worker metadata: {'; '.join(errs)}")

        can_do, reason = self.can_spawn(
            depth=depth,
            parent_id=parent_id,
            role=role,
            write_boundary=write_bounds,
            wave_number=wave_number,
            metadata=metadata,
        )
        if not can_do:
            raise OrchestrationBudgetExceeded(reason)

        record = AgentRecord(
            agent_id=agent_id,
            role=role,
            depth=depth,
            wave_number=wave_number,
            parent_id=parent_id,
            is_coordinator=is_coordinator,
            metadata=metadata,
        )
        self.records[agent_id] = record
        self.spawned_total += 1
        self.active_total += 1
        self.active_workers.append(agent_id)
        self.worker_roles[agent_id] = role
        self.current_depth = max(self.current_depth, depth)

        if parent_id and parent_id in self.records:
            self.records[parent_id].actually_spawned += 1

        return record

    def record_termination(self, agent_id: str, failure_reason: Optional[str] = None) -> None:
        """Marks an agent as terminated, decrementing active count."""
        if agent_id in self.records and self.records[agent_id].is_active:
            self.records[agent_id].is_active = False
            self.records[agent_id].terminated_at = time.time()
            if failure_reason:
                self.records[agent_id].failure_reason = failure_reason
            self.active_total = max(0, self.active_total - 1)
            if agent_id in self.active_workers:
                self.active_workers.remove(agent_id)
            if failure_reason:
                if agent_id in self.completed_workers:
                    self.completed_workers.remove(agent_id)
                if agent_id not in self.failed_workers:
                    self.failed_workers.append(agent_id)
            else:
                if agent_id not in self.completed_workers and agent_id not in self.failed_workers:
                    self.completed_workers.append(agent_id)

    def record_failure(self, agent_id: str, reason: str) -> None:
        """Records a worker failure."""
        self.record_termination(agent_id, failure_reason=reason)

    def collapse_all_active(self) -> int:
        """Aggressively collapses all active workers to 0."""
        collapsed_count = 0
        for aid in list(self.active_workers):
            if aid in self.records and self.records[aid].is_active:
                self.records[aid].is_active = False
                self.records[aid].terminated_at = time.time()
                collapsed_count += 1
                if aid not in self.collapsed_workers:
                    self.collapsed_workers.append(aid)
        self.active_workers.clear()
        self.active_total = 0
        return collapsed_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "spawned_total": self.spawned_total,
            "active_total": self.active_total,
            "remaining_budget": self.remaining_budget,
            "max_active_per_wave": self.max_active_per_wave,
            "max_total_spawned": self.max_total_spawned,
            "max_depth": self.max_depth,
            "max_retries_per_role": self.max_retries_per_role,
            "current_wave": self.current_wave,
            "current_depth": self.current_depth,
            "active_workers": list(self.active_workers),
            "worker_roles": dict(self.worker_roles),
            "reserved_capacity": dict(self.reserved_capacity),
            "completed_workers": list(self.completed_workers),
            "failed_workers": list(self.failed_workers),
            "collapsed_workers": list(self.collapsed_workers),
        }


# Backwards compatibility alias
OrchestrationBudget = MissionLedger


@dataclass
class Wave:
    """A single bounded execution wave within a mission."""
    wave_number: int
    name: str  # RECONNAISSANCE, PLANNING, IMPLEMENTATION, VERIFICATION, DELIVERY
    state: WaveState = WaveState.INITIALIZING
    agent_ids: List[str] = field(default_factory=list)
    handoffs: List[StructuredHandoff] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    collapsed_at: Optional[float] = None
    stage: WaveLifecycleStage = WaveLifecycleStage.PLAN

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wave_number": self.wave_number,
            "name": self.name,
            "state": self.state.value,
            "agent_ids": list(self.agent_ids),
            "handoff_count": len(self.handoffs),
            "created_at": self.created_at,
            "collapsed_at": self.collapsed_at,
            "stage": self.stage.value,
        }


class WaveManager:
    """Orchestrates waves, ensuring mandatory consolidation, collapse, and lifecycle stages."""

    def __init__(self, ledger: Optional[MissionLedger] = None, budget: Optional[MissionLedger] = None):
        self.ledger = ledger or budget or MissionLedger()
        self.waves: List[Wave] = []
        self.current_wave_idx: int = -1

    @property
    def budget(self) -> MissionLedger:
        """Alias for backwards compatibility."""
        return self.ledger

    @property
    def current_wave(self) -> Optional[Wave]:
        if 0 <= self.current_wave_idx < len(self.waves):
            return self.waves[self.current_wave_idx]
        return None

    def start_wave(self, name: str) -> Wave:
        """Begins a new wave. Strictly requires previous wave to be collapsed."""
        if self.current_wave and self.current_wave.state != WaveState.COLLAPSED:
            if self.ledger.active_total > 0:
                raise RuntimeError(
                    f"Cannot start wave '{name}': previous wave #{self.current_wave.wave_number} "
                    f"has {self.ledger.active_total} uncollapsed active workers."
                )
            self.current_wave.state = WaveState.COLLAPSED
            self.current_wave.collapsed_at = time.time()

        wave_num = len(self.waves) + 1
        wave = Wave(wave_number=wave_num, name=name, state=WaveState.ACTIVE, stage=WaveLifecycleStage.DISPATCH)
        self.waves.append(wave)
        self.current_wave_idx = len(self.waves) - 1
        self.ledger.current_wave = wave_num
        return wave

    def spawn_worker(
        self,
        agent_id: str,
        role: str,
        depth: int = 1,
        parent_id: Optional[str] = None,
        is_coordinator: bool = False,
        metadata: Optional[WorkerMetadata] = None,
    ) -> AgentRecord:
        """Spawns a worker inside the current wave with Anti-Hydra validation."""
        if not self.current_wave or self.current_wave.state != WaveState.ACTIVE:
            raise RuntimeError("Cannot spawn worker: no active wave started.")

        rec = self.ledger.record_spawn(
            agent_id=agent_id,
            role=role,
            depth=depth,
            wave_number=self.current_wave.wave_number,
            parent_id=parent_id,
            is_coordinator=is_coordinator,
            metadata=metadata,
        )
        self.current_wave.agent_ids.append(agent_id)
        self.current_wave.stage = WaveLifecycleStage.EXECUTE
        return rec

    def record_handoff(self, agent_id: str, handoff: StructuredHandoff) -> None:
        """Records structured evidence handoff from worker and terminates it."""
        if not self.current_wave:
            raise RuntimeError("No active wave.")

        valid, errs = handoff.validate()
        if not valid:
            raise ValueError(f"Invalid handoff from '{agent_id}': {'; '.join(errs)}")

        if agent_id in self.ledger.records:
            self.ledger.records[agent_id].handoff = handoff
        self.current_wave.handoffs.append(handoff)
        self.ledger.record_termination(agent_id)
        self.current_wave.stage = WaveLifecycleStage.COLLECT

    def collapse_wave(self) -> int:
        """Collapses the current wave: active workers -> 0, state -> COLLAPSED."""
        if not self.current_wave:
            return 0

        self.current_wave.state = WaveState.CONSOLIDATING
        self.current_wave.stage = WaveLifecycleStage.COLLAPSE
        collapsed = self.ledger.collapse_all_active()
        self.current_wave.state = WaveState.COLLAPSED
        self.current_wave.collapsed_at = time.time()
        return collapsed

class DualDispatchGates:
    """Evaluates Gate A (Pre-Planning) and Gate B (Execution Dispatch) with cost reasoning."""

    @staticmethod
    def evaluate_pre_planning(
        domain_count: int = 1,
        independent_lanes: int = 1,
        file_count: int = 1,
        module_count: int = 1,
        is_research_and_impl: bool = False,
        explicit_delegation_request: bool = False,
        is_high_risk_investigation: bool = False,
    ) -> DispatchGateResult:
        """Gate A: Evaluates reconnaissance delegation requirements before planning."""
        reasons: List[str] = []
        rec_workers = 0
        mode = WorkforceMode.SOLO

        # Trigger A: Multiple domains (3+)
        if domain_count >= 3:
            reasons.append(f"Touches {domain_count} distinct problem domains (Threshold >= 3)")
            rec_workers = max(rec_workers, 2)
            mode = WorkforceMode.PARALLEL

        # Trigger B: Multiple independent lanes (2+)
        if independent_lanes >= 2:
            reasons.append(f"Contains {independent_lanes} independent investigation lanes (Threshold >= 2)")
            rec_workers = max(rec_workers, 2)
            mode = WorkforceMode.PARALLEL if independent_lanes >= 3 else WorkforceMode.SMALL

        # Trigger C: Large multi-file scope (5+ files across 2+ modules)
        if file_count >= 5 and module_count >= 2:
            reasons.append(f"Touches {file_count} files across {module_count} modules (Threshold 5+ files, 2+ modules)")
            rec_workers = max(rec_workers, 2 if independent_lanes >= 2 else 1)
            mode = WorkforceMode.SMALL if independent_lanes >= 2 else WorkforceMode.FOCUSED

        # Trigger D: Substantial research + implementation
        if is_research_and_impl:
            reasons.append("Requires substantial research/investigation AND implementation")
            rec_workers = max(rec_workers, 1)
            if mode == WorkforceMode.SOLO:
                mode = WorkforceMode.FOCUSED

        # Trigger E: High-risk investigation
        if is_high_risk_investigation:
            reasons.append("High-risk or security-sensitive investigation warrants dedicated specialist")
            rec_workers = max(rec_workers, 1)
            if mode == WorkforceMode.SOLO:
                mode = WorkforceMode.FOCUSED

        # Trigger F: Explicit user delegation request
        if explicit_delegation_request:
            reasons.append("Explicit human user request for delegation/parallel execution")
            rec_workers = max(rec_workers, 2)
            mode = WorkforceMode.PARALLEL

        if reasons:
            decision = GateDecision.DELEGATION_MANDATORY
            why_fewer = "Mandatory delegation triggers (independent lanes / multi-domain / explicit user request) satisfied."
            why_more = "Initial reconnaissance capped to prevent premature swarm spawning."
        else:
            decision = GateDecision.SOLO_AUTHORIZED
            reasons.append("Task is focused and narrow; solo reconnaissance authorized")
            rec_workers = 0
            mode = WorkforceMode.SOLO
            why_fewer = "Already minimal workforce (0 subagents)."
            why_more = "Reconnaissance is narrow; parent handles exploration directly without subagent cost."

        cost_reasoning = WorkforceCostReasoning(
            selected_mode=mode,
            recommended_workers=rec_workers,
            why_this_workforce="; ".join(reasons),
            why_not_fewer_workers=why_fewer,
            why_not_more_workers=why_more,
            decision_inputs={
                "domain_count": domain_count,
                "independent_lanes": independent_lanes,
                "file_count": file_count,
                "module_count": module_count,
            },
        )

        return DispatchGateResult(
            gate_type=DispatchGateType.PRE_PLANNING,
            decision=decision,
            mode=mode,
            recommended_workers=rec_workers,
            reasons=reasons,
            checklist={
                "domain_count": domain_count,
                "independent_lanes": independent_lanes,
                "file_count": file_count,
                "module_count": module_count,
                "is_research_and_impl": is_research_and_impl,
                "explicit_delegation_request": explicit_delegation_request,
                "is_high_risk_investigation": is_high_risk_investigation,
            },
            budget_reserved=rec_workers,
            cost_reasoning=cost_reasoning,
        )

    @staticmethod
    def evaluate_execution_dispatch(
        workstream_count: int = 1,
        independent_streams: int = 1,
        is_tightly_coupled: bool = False,
        file_ownership_disjoint: bool = True,
        risk_tier: str = "LOW",
        remaining_budget: int = MAX_TOTAL_SPAWNED_AGENTS,
        active_capacity: int = MAX_ACTIVE_AGENTS_PER_WAVE,
    ) -> DispatchGateResult:
        """Gate B: Evaluates implementation delegation requirements from approved plan."""
        reasons: List[str] = []
        rec_workers = 0
        mode = WorkforceMode.SOLO

        if remaining_budget <= 0:
            return DispatchGateResult(
                gate_type=DispatchGateType.EXECUTION_DISPATCH,
                decision=GateDecision.BLOCKED,
                mode=WorkforceMode.SOLO,
                recommended_workers=0,
                reasons=["Mission budget exhausted (0 launches remaining)"],
                checklist={"budget_available": False},
                cost_reasoning=WorkforceCostReasoning(
                    selected_mode=WorkforceMode.SOLO,
                    recommended_workers=0,
                    why_this_workforce="Blocked: remaining budget is 0.",
                    why_not_fewer_workers="N/A",
                    why_not_more_workers="Budget ceiling reached.",
                ),
            )

        if is_tightly_coupled:
            reasons.append("Tightly coupled changes require Controlled Single Writer to prevent merge conflicts")
            mode = WorkforceMode.FOCUSED
            rec_workers = min(1, remaining_budget, active_capacity)
            decision = GateDecision.SOLO_AUTHORIZED
            why_fewer = "Single writer handles tightly coupled changes safely."
            why_more = "Overlapping code paths create merge collisions if parallelized."
        elif independent_streams >= 3:
            reasons.append(f"{independent_streams} independent implementation streams justify PARALLEL execution")
            rec_workers = min(independent_streams, 4, remaining_budget, active_capacity)
            mode = WorkforceMode.PARALLEL
            decision = GateDecision.DELEGATION_MANDATORY
            why_fewer = "Serializing 3+ independent streams would increase wall-clock time."
            why_more = "Parallel concurrency capped at 4 to control coordination overhead."
        elif independent_streams == 2:
            reasons.append("2 independent implementation streams mandate at least 2 workers (SOLO is forbidden)")
            rec_workers = min(2, remaining_budget, active_capacity)
            mode = WorkforceMode.SMALL
            decision = GateDecision.DELEGATION_MANDATORY
            why_fewer = "Gate B strictly forbids SOLO when 2 independent streams exist."
            why_more = "Only 2 independent streams exist; extra workers would be idle."
        else:
            reasons.append("Single implementation stream: controlled single writer (Parent or 1 Implementer)")
            mode = WorkforceMode.SOLO
            rec_workers = 0
            decision = GateDecision.SOLO_AUTHORIZED
            why_fewer = "Already minimal workforce."
            why_more = "Single stream offers no useful parallel progress."

        cost_reasoning = WorkforceCostReasoning(
            selected_mode=mode,
            recommended_workers=rec_workers,
            why_this_workforce="; ".join(reasons),
            why_not_fewer_workers=why_fewer,
            why_not_more_workers=why_more,
            decision_inputs={
                "independent_streams": independent_streams,
                "is_tightly_coupled": is_tightly_coupled,
                "risk_tier": risk_tier,
            },
        )

        return DispatchGateResult(
            gate_type=DispatchGateType.EXECUTION_DISPATCH,
            decision=decision,
            mode=mode,
            recommended_workers=rec_workers,
            reasons=reasons,
            checklist={
                "workstream_count": workstream_count,
                "independent_streams": independent_streams,
                "is_tightly_coupled": is_tightly_coupled,
                "file_ownership_disjoint": file_ownership_disjoint,
                "risk_tier": risk_tier,
                "remaining_budget": remaining_budget,
            },
            budget_reserved=rec_workers,
            cost_reasoning=cost_reasoning,
        )


class WriteSafetyEvaluator:
    """Evaluates task file targets and workstreams to enforce write safety."""

    @staticmethod
    def evaluate(
        target_files: List[str],
        worker_file_assignments: Optional[Dict[str, List[str]]] = None,
        is_read_only: bool = False,
    ) -> Tuple[WriteSafetyPolicy, str]:
        """Evaluates whether concurrent writing is safe, disjoint, or unsafe."""
        if is_read_only or len(target_files) == 0:
            return WriteSafetyPolicy.READ_ONLY, "Task is read-only; zero write hazards."

        if not worker_file_assignments or len(worker_file_assignments) <= 1:
            return WriteSafetyPolicy.CONTROLLED_SINGLE_WRITER, "Single writer owns all modifications."

        seen_files: Dict[str, str] = {}
        overlaps: List[str] = []
        for worker_id, files in worker_file_assignments.items():
            for f in files:
                norm_f = f.replace("\\", "/").strip().lower()
                if norm_f in seen_files:
                    overlaps.append(f"'{norm_f}' assigned to both '{seen_files[norm_f]}' and '{worker_id}'")
                else:
                    seen_files[norm_f] = worker_id

        if overlaps:
            return (
                WriteSafetyPolicy.UNSAFE_TO_PARALLELIZE,
                f"Overlapping writers detected: {'; '.join(overlaps)}. Fallback to CONTROLLED_SINGLE_WRITER.",
            )

        return (
            WriteSafetyPolicy.SAFELY_PARALLELIZABLE,
            f"All {len(worker_file_assignments)} workers have strictly disjoint file boundaries. Use isolated workspaces.",
        )


class WorkforceSizer:
    """Deterministically sizes workforce based on task classification and risk."""

    @staticmethod
    def select_mode(
        task_class: str,
        risk_tier: str,
        pre_gate: DispatchGateResult,
        exec_gate: Optional[DispatchGateResult] = None,
    ) -> WorkforceMode:
        """Selects the authoritative WorkforceMode optimizing useful progress per token."""
        if task_class.upper() == "DOCUMENTATION" and risk_tier.upper() == "LOW":
            return WorkforceMode.SOLO

        if exec_gate:
            return exec_gate.mode

        return pre_gate.mode


def determine_coordination_level(mode: WorkforceMode, wave_count: int = 1) -> CoordinationLevel:
    """Maps workforce sizing and wave count to coordination artifact level (L0-L3)."""
    if mode == WorkforceMode.SOLO:
        return CoordinationLevel.L0
    if mode in (WorkforceMode.FOCUSED, WorkforceMode.SMALL) and wave_count <= 2:
        return CoordinationLevel.L1
    if mode in (WorkforceMode.PARALLEL, WorkforceMode.STAGED) or (wave_count >= 3 and mode not in (WorkforceMode.HIERARCHICAL, WorkforceMode.MAX)):
        return CoordinationLevel.L2
    if mode in (WorkforceMode.HIERARCHICAL, WorkforceMode.MAX):
        return CoordinationLevel.L3
    return CoordinationLevel.L1





class AdaptiveWorkforcePlanner:
    """12-Input Adaptive Workforce Sizer & Cost Reasoning Engine (Phase 84).

    Inputs Evaluated:
      1. task_class: Complexity classification (BUG, FEATURE, REFACTOR, etc.)
      2. risk_tier: Security / blast radius (LOW, MEDIUM, HIGH)
      3. pre_planning_decision: Gate A reconnaissance decision
      4. execution_decision: Gate B execution decision
      5. write_policy: File write conflict assessment
      6. subsystem_count: Number of decoupled subsystems involved
      7. file_count: Number of concrete target files
      8. has_disjoint_boundaries: Whether worker file boundaries are disjoint
      9. remaining_mission_budget: Global mission budget remaining
      10. historical_worker_success_rate: Observed worker completion rate
      11. estimated_token_cost_budget: Mission token budget ceiling
      12. active_workers_in_wave: Concurrency already allocated
    """

    @classmethod
    def plan(
        cls,
        task_class: str,
        risk_tier: str,
        pre_planning_decision: Any,
        execution_decision: Optional[Any] = None,
        write_policy: Optional[WriteSafetyPolicy] = None,
        subsystem_count: int = 1,
        file_count: int = 1,
        has_disjoint_boundaries: bool = False,
        remaining_mission_budget: int = 20,
        historical_worker_success_rate: float = 1.0,
        estimated_token_cost_budget: int = 100000,
        active_workers_in_wave: int = 0,
    ) -> Tuple[WorkforceMode, WorkforceCostReasoning]:
        """Evaluates the 12 decision inputs and returns the authoritative WorkforceMode and Cost Reasoning."""
        task_class_norm = str(task_class or "").upper()
        risk_tier_norm = str(risk_tier or "").upper()

        # Check remaining budget constraint
        if remaining_mission_budget <= 2:
            reasoning = WorkforceCostReasoning(
                why_this_workforce="Near-exhausted mission budget (<3 remaining); solo execution avoids abort.",
                why_not_fewer="Solo primary is the minimum viable execution unit.",
                why_not_more=f"Remaining budget ({remaining_mission_budget}) strictly forbids parallel allocations.",
                max_recommended_workers=1,
                mode=WorkforceMode.SOLO,
                coordination_cost_tokens=0,
                write_collision_risk="NONE",
            )
            return WorkforceMode.SOLO, reasoning

        # 1. Low-risk / Documentation / Single localized task
        if (task_class_norm in ("DOCUMENTATION", "INVESTIGATION") and risk_tier_norm == "LOW") or (file_count <= 1 and subsystem_count <= 1 and risk_tier_norm == "LOW"):
            reasoning = WorkforceCostReasoning(
                why_this_workforce="Low-risk localized task; solo execution maximizes token efficiency with zero coordination overhead.",
                why_not_fewer="Solo primary is the minimum viable execution unit.",
                why_not_more="Single localized work surface; adding workers causes negative token ROI and context churn.",
                max_recommended_workers=1,
                mode=WorkforceMode.SOLO,
                coordination_cost_tokens=0,
                write_collision_risk="NONE",
            )
            return WorkforceMode.SOLO, reasoning

        # 2. Check if execution gate or disjoint files authorized PARALLEL
        exec_mode = getattr(execution_decision, "mode", None)
        exec_decision_val = getattr(execution_decision, "decision", execution_decision)
        exec_str = str(getattr(exec_decision_val, "value", exec_decision_val or "")).upper()

        if (
            exec_mode == WorkforceMode.PARALLEL
            or "PARALLEL" in exec_str
            or (
                has_disjoint_boundaries
                and file_count >= 2
                and write_policy in (WriteSafetyPolicy.SAFELY_PARALLELIZABLE, WriteSafetyPolicy.DISJOINT_BRANCHES)
            )
        ) and active_workers_in_wave <= 6:
            workers = min(4, max(file_count, 3), remaining_mission_budget)
            reasoning = WorkforceCostReasoning(
                why_this_workforce="Independent work streams / disjoint boundaries justify safe parallel execution.",
                why_not_fewer="Serializing independent streams increases latency without safety advantage.",
                why_not_more=f"Concurrency capped at {workers} to preserve wave ceiling and token efficiency.",
                max_recommended_workers=workers,
                mode=WorkforceMode.PARALLEL,
                coordination_cost_tokens=workers * 500,
                write_collision_risk="LOW",
            )
            return WorkforceMode.PARALLEL, reasoning

        # 3. High risk or Cross-subsystem work
        if risk_tier_norm == "HIGH" or subsystem_count >= 2:
            reasoning = WorkforceCostReasoning(
                why_this_workforce="High risk cross-subsystem scope requires focused primary engineer with independent verifier.",
                why_not_fewer="High risk triggers mandatory independent verification gate (Maker-Checker invariant).",
                why_not_more="Shared subsystem coupling makes wide parallel execution prone to merge conflicts.",
                max_recommended_workers=2,
                mode=WorkforceMode.FOCUSED,
                coordination_cost_tokens=1000,
                write_collision_risk="MODERATE",
            )
            return WorkforceMode.FOCUSED, reasoning

        # 4. Check execution decision
        exec_str = getattr(execution_decision, "value", str(execution_decision or "")).upper()
        if "PARALLEL" in exec_str:
            reasoning = WorkforceCostReasoning(
                why_this_workforce="Execution gate authorized multi-stream parallel execution.",
                why_not_fewer="Execution gate verified independent work surfaces exist.",
                why_not_more="Concurrency capped to prevent token exhaustion.",
                max_recommended_workers=3,
                mode=WorkforceMode.PARALLEL,
                coordination_cost_tokens=1500,
                write_collision_risk="LOW",
            )
            return WorkforceMode.PARALLEL, reasoning
        elif "SPECIALIST" in exec_str or "FOCUSED" in exec_str or "DELEGATION" in exec_str:
            reasoning = WorkforceCostReasoning(
                why_this_workforce="Focused specialist authorized for deep localized subsystem investigation.",
                why_not_fewer="Specialist capability needed beyond generalist primary role.",
                why_not_more="Task scope is bounded to single specialist domain.",
                max_recommended_workers=2,
                mode=WorkforceMode.FOCUSED,
                coordination_cost_tokens=800,
                write_collision_risk="LOW",
            )
            return WorkforceMode.FOCUSED, reasoning

        # Default: SOLO
        reasoning = WorkforceCostReasoning(
            why_this_workforce="Default bounded solo execution ensures strict token economy and low coordination overhead.",
            why_not_fewer="Solo primary is the minimum viable execution unit.",
            why_not_more="No evidence justifying delegation overhead for current task complexity.",
            max_recommended_workers=1,
            mode=WorkforceMode.SOLO,
            coordination_cost_tokens=0,
            write_collision_risk="MINIMAL",
        )
        return WorkforceMode.SOLO, reasoning

    @classmethod
    def plan_workforce(
        cls,
        task_complexity: str = "MODULAR",
        independent_work_surfaces: int = 1,
        dependency_graph_depth: int = 1,
        risk_tier: str = "LOW",
        verification_requirements: str = "SOLO_SANITY",
        project_topology_components: int = 1,
        available_capabilities: Optional[List[str]] = None,
        specialist_available: bool = True,
        expected_context_cost: str = "LOW",
        expected_coordination_cost: str = "LOW",
        write_collision_risk: str = "ZERO",
        native_antigravity_sufficient: bool = False,
        remaining_budget: int = MAX_TOTAL_SPAWNED_AGENTS,
        active_capacity: int = MAX_ACTIVE_AGENTS_PER_WAVE,
    ) -> Tuple[WorkforceMode, int, WorkforceCostReasoning]:
        """Dynamically selects minimal effective workforce and emits cost reasoning."""
        if remaining_budget <= 0:
            mode = WorkforceMode.SOLO
            rec_workers = 0
            reasoning = WorkforceCostReasoning(
                why_this_workforce="Mission launch budget exhausted (0 remaining); parent executes directly.",
                why_not_fewer="Already minimal workforce (SOLO).",
                why_not_more="Budget exhausted: constitutional ceiling (20 launches) strictly enforced.",
                max_recommended_workers=0,
                mode=mode,
            )
            return mode, rec_workers, reasoning

        if native_antigravity_sufficient or (task_complexity.upper() == "TINY" and independent_work_surfaces <= 1 and risk_tier.upper() == "LOW"):
            mode = WorkforceMode.SOLO
            rec_workers = 0
            reasoning = WorkforceCostReasoning(
                why_this_workforce="Native Antigravity primitives or parent execution directly satisfy narrow task.",
                why_not_fewer="Already minimal (0 subagents).",
                why_not_more="Sequential work; context overhead would dominate.",
                max_recommended_workers=0,
                mode=mode,
            )
            return mode, rec_workers, reasoning

        if write_collision_risk.upper() == "HIGH" or dependency_graph_depth > 2:
            mode = WorkforceMode.FOCUSED if risk_tier.upper() in ("HIGH", "CRITICAL") or verification_requirements != "SOLO_SANITY" else WorkforceMode.SOLO
            rec_workers = min(1, remaining_budget, active_capacity) if mode == WorkforceMode.FOCUSED else 0
            reasoning = WorkforceCostReasoning(
                why_this_workforce="Tightly coupled files mandate Controlled Single Writer.",
                why_not_fewer="High risk requires dedicated perspective." if mode == WorkforceMode.FOCUSED else "Already minimal.",
                why_not_more="Files overlap; additional workers would cause conflicts.",
                max_recommended_workers=rec_workers,
                mode=mode,
            )
            return mode, rec_workers, reasoning

        if task_complexity.upper() == "ENTERPRISE" and independent_work_surfaces >= 3 and project_topology_components >= 3:
            mode = WorkforceMode.HIERARCHICAL
            rec_workers = min(independent_work_surfaces, 4, remaining_budget, active_capacity)
            reasoning = WorkforceCostReasoning(
                why_this_workforce="Enterprise mission requires Coordinator leading bounded leaf workers.",
                why_not_fewer="Decomposable subsystems require dedicated leads.",
                why_not_more="Hierarchy strictly capped to depth-2 and coordinator quota <= 4.",
                max_recommended_workers=rec_workers,
                mode=mode,
            )
            return mode, rec_workers, reasoning

        if independent_work_surfaces >= 3:
            mode = WorkforceMode.PARALLEL
            rec_workers = min(independent_work_surfaces, 4, remaining_budget, active_capacity)
            reasoning = WorkforceCostReasoning(
                why_this_workforce=f"{independent_work_surfaces} independent work surfaces justify parallel execution.",
                why_not_fewer="Fewer workers would serialize independent tracks.",
                why_not_more="Active workers capped to 4 concurrent initial specialists.",
                max_recommended_workers=rec_workers,
                mode=mode,
            )
            return mode, rec_workers, reasoning

        if independent_work_surfaces == 2:
            mode = WorkforceMode.SMALL
            rec_workers = min(2, remaining_budget, active_capacity)
            reasoning = WorkforceCostReasoning(
                why_this_workforce="2 independent work surfaces justify paired specialists.",
                why_not_fewer="Gate B forbids SOLO when 2 independent surfaces exist.",
                why_not_more="Only 2 independent surfaces exist.",
                max_recommended_workers=rec_workers,
                mode=mode,
            )
            return mode, rec_workers, reasoning

        if risk_tier.upper() in ("HIGH", "CRITICAL") or verification_requirements != "SOLO_SANITY":
            mode = WorkforceMode.FOCUSED
            rec_workers = min(1, remaining_budget, active_capacity)
            why_fewer = "High risk tier requires dedicated verifier perspective."
        else:
            mode = WorkforceMode.SOLO
            rec_workers = 0
            why_fewer = "Already minimal workforce."

        reasoning = WorkforceCostReasoning(
            why_this_workforce="Single focused lane satisfies mission with minimal overhead.",
            why_not_fewer=why_fewer,
            why_not_more="Work is sequential; additional workers provide zero concurrency value.",
            max_recommended_workers=rec_workers,
            mode=mode,
        )
        return mode, rec_workers, reasoning



class FailureRecoveryEngine:
    """Deterministic failure recovery and retry decision authority (Phase 85)."""

    MAX_RETRIES_PER_ROLE = 2

    @classmethod
    def evaluate(
        cls,
        worker_id: str,
        failure_type: FailureType,
        consecutive_failures: int,
        can_retry_budget: bool,
        error_message: str = "",
    ) -> FailureRecoveryDecision:
        """Determines the exact recovery action based on failure type and retry history."""
        # Runaway retry limit
        if consecutive_failures >= cls.MAX_RETRIES_PER_ROLE:
            return FailureRecoveryDecision(
                failure_type=failure_type,
                action=RecoveryAction.FAIL_CLOSED,
                worker_id=worker_id,
                rationale=f"Anti-Hydra Protection: Consecutive failure threshold reached ({consecutive_failures}/{cls.MAX_RETRIES_PER_ROLE}). Aborting to prevent runaway retry loops.",
                can_consume_budget=False,
            )

        # Budget exhaustion
        if not can_retry_budget:
            return FailureRecoveryDecision(
                failure_type=failure_type,
                action=RecoveryAction.TAKEOVER_DIRECT,
                worker_id=worker_id,
                rationale="Mission launch budget exhausted; primary coordinator takes over directly without subagent launch.",
                can_consume_budget=False,
            )

        if failure_type == FailureType.UNGROUNDED_EVIDENCE:
            return FailureRecoveryDecision(
                failure_type=failure_type,
                action=RecoveryAction.RETRY_SAME_WORKER_CONTEXT,
                worker_id=worker_id,
                rationale="Handoff failed evidence grounding check; prompt worker with specific validation error.",
                can_consume_budget=False,
                retry_prompt=f"Evidence verification failed: {error_message}. Provide verified file paths, line numbers, or test outputs.",
            )

        if failure_type == FailureType.WRITE_COLLISION:
            return FailureRecoveryDecision(
                failure_type=failure_type,
                action=RecoveryAction.TAKEOVER_DIRECT,
                worker_id=worker_id,
                rationale="Write collision detected; serialize execution under single primary writer.",
                can_consume_budget=False,
            )

        if failure_type in (FailureType.TIMEOUT, FailureType.CRASH):
            return FailureRecoveryDecision(
                failure_type=failure_type,
                action=RecoveryAction.SPAWN_NEW_WORKER,
                worker_id=worker_id,
                rationale="Worker unresponsive or crashed; spawn fresh worker with clean context (consumes 1 launch slot).",
                can_consume_budget=True,
                retry_prompt=f"Previous worker failed with {failure_type.value}: {error_message}. Execute bounded task.",
            )

        if failure_type in (FailureType.MCP_UNAVAILABLE, FailureType.CAPABILITY_UNAVAILABLE):
            return FailureRecoveryDecision(
                failure_type=failure_type,
                action=RecoveryAction.TAKEOVER_DIRECT,
                worker_id=worker_id,
                rationale=f"Capability or MCP unavailable ({failure_type.value}); fallback to deterministic local tools.",
                can_consume_budget=False,
            )

        # Default: Direct Takeover
        return FailureRecoveryDecision(
            failure_type=failure_type,
            action=RecoveryAction.TAKEOVER_DIRECT,
            worker_id=worker_id,
            rationale=f"Deterministic fallback to primary coordinator takeover for {failure_type.value}.",
            can_consume_budget=False,
        )

    @classmethod
    def evaluate_recovery(
        cls,
        failure_type: FailureType,
        worker_id: str,
        ledger: Any = None,
        prior_retries: int = 0,
    ) -> FailureRecoveryDecision:
        """Backward-compatible wrapper for evaluate_recovery."""
        can_retry = True
        if ledger and hasattr(ledger, "can_spawn"):
            can_retry, _ = ledger.can_spawn(depth=1)
        return cls.evaluate(
            worker_id=worker_id,
            failure_type=failure_type,
            consecutive_failures=prior_retries,
            can_retry_budget=can_retry,
        )


class WavePersistenceEngine:
    """State persistence and crash recovery engine for teamwork wave execution (Phase 85 & 89)."""

    DEFAULT_STATE_FILE = ".antios/wave_state.json"

    @classmethod
    def save_state(
        cls,
        state: Any,
        workspace_root: str = ".",
        filepath: Optional[str] = None,
        wave_manager: Any = None,
        **kwargs: Any,
    ) -> str:
        """Persists active wave state to disk (supports dict state or MissionLedger)."""
        if isinstance(state, dict):
            target = filepath or os.path.join(workspace_root, cls.DEFAULT_STATE_FILE)
            os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
            serializable = dict(state)
            serializable["persisted_at"] = time.time()
            with open(target, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2)
            return target
        else:
            # Ledger + WaveManager compatibility
            ledger = state
            wm = wave_manager or kwargs.get("wave_manager") or workspace_root

            data = {
                "ledger": ledger.to_dict() if hasattr(ledger, "to_dict") else {},
                "records": {
                    aid: {
                        "agent_id": r.agent_id,
                        "role": r.role,
                        "depth": r.depth,
                        "wave_number": r.wave_number,
                        "spawned_at": r.spawned_at,
                        "terminated_at": r.terminated_at,
                        "is_active": r.is_active,
                        "is_coordinator": r.is_coordinator,
                        "parent_id": r.parent_id,
                        "failure_reason": r.failure_reason,
                        "metadata": r.metadata.to_dict() if getattr(r, "metadata", None) else None,
                        "handoff": r.handoff.to_dict() if getattr(r, "handoff", None) else None,
                    }
                    for aid, r in getattr(ledger, "records", {}).items()
                },
                "waves": [w.to_dict() if hasattr(w, "to_dict") else {} for w in getattr(wm, "waves", [])],
                "current_wave_idx": getattr(wm, "current_wave_idx", 0),
            }
            p = Path(filepath or os.path.join(".", cls.DEFAULT_STATE_FILE))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return str(p)

    @classmethod
    def load_state(
        cls,
        workspace_root: str = ".",
        filepath: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Loads persisted wave state from disk if present."""
        target = filepath or os.path.join(workspace_root, cls.DEFAULT_STATE_FILE)
        if not os.path.exists(target):
            return None
        try:
            with open(target, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    @classmethod
    def clear_state(
        cls,
        workspace_root: str = ".",
        filepath: Optional[str] = None,
    ) -> bool:
        """Removes persisted wave state upon successful mission completion."""
        target = filepath or os.path.join(workspace_root, cls.DEFAULT_STATE_FILE)
        if os.path.exists(target):
            try:
                os.remove(target)
                return True
            except OSError:
                return False
        return False

    @classmethod
    def recover_mission(
        cls,
        workspace_root: str = ".",
        filepath: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Recovers an interrupted mission from persisted state."""
        state = cls.load_state(workspace_root=workspace_root, filepath=filepath)
        if not state:
            return False, "No persisted wave state found to recover.", None

        wave_idx = state.get("current_wave_index", 0)
        active_workers = state.get("active_workers", [])
        total_spawned = state.get("total_spawned", 0)

        recovery_summary = (
            f"Recovered mission '{state.get('mission_id', 'unknown')}' at wave {wave_idx}. "
            f"Reconciled {len(active_workers)} active workers (total launched: {total_spawned})."
        )
        return True, recovery_summary, state

