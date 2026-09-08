"""AntiOS 2.0 Mission State Continuity & Evidence Ledger (Phase 89).

Implements bounded persistent mission state for complex multi-wave tasks,
deterministic ephemeral-vs-persistent thresholds, crash recovery, and
tool output bounding.

Guiding Laws:
1. "Do NOT persist trivial tasks; maintain bounded state only when justified."
2. "Crash/restart must NEVER silently reset mission state."
3. "Recovery decisions are strictly grounded in physical evidence."
4. "Tool outputs must be token-bounded without losing verification reproducibility."
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class MissionPersistenceMode(str, Enum):
    """Persistence mode for a mission."""
    EPHEMERAL = "EPHEMERAL"      # Single file or trivial task: in-memory state only
    PERSISTENT = "PERSISTENT"    # Multi-file, multi-wave, or high-risk task: on-disk state


class MissionLifecycleState(str, Enum):
    """Canonical lifecycle progression of a mission."""
    CREATED = "CREATED"
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    RECOVERING = "RECOVERING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class MissionRecoveryAction(str, Enum):
    """Deterministic recovery strategy emitted on interrupted mission resumption."""
    RESUME = "RESUME"            # Clean interruption: resume current wave with active workers
    REPLAN = "REPLAN"            # Unresolvable progress or structural conflict: regenerate plan
    REFRESH = "REFRESH"          # Fingerprint drift or clean file changes: refresh context & continue
    ROLLBACK = "ROLLBACK"        # Partial/corrupted writes detected: revert uncommitted changes
    ABORT = "ABORT"              # Tampering, security violation, or unrecoverable corruption
    BLOCK = "BLOCK"              # Hard stop on security boundary or governance violation
    REQUIRE_HUMAN_APPROVAL = "REQUIRE_HUMAN_APPROVAL"  # Escalation requiring explicit operator approval


class ToolOutputClassification(str, Enum):
    """Classification of raw tool execution output."""
    RAW = "RAW"                  # Unprocessed output kept in-memory
    RELEVANT = "RELEVANT"        # Informative output needed for active step
    SUMMARIZED = "SUMMARIZED"    # Large output compacted to bounded lines + SHA reference
    DISCARDED = "DISCARDED"      # Noise or trivial output dropped from context


@dataclass
class ToolOutputEvidence:
    """Token-bounded representation of a tool output with content SHA-256."""
    tool_name: str
    command_or_path: str
    exit_code: int
    classification: ToolOutputClassification
    compact_summary: str
    raw_sha256: str
    raw_size_bytes: int
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ToolOutputClassifier:
    """Classifies and bounds large tool execution outputs."""

    MAX_RELEVANT_CHARS = 2000

    @classmethod
    def process_output(
        cls,
        tool_name: str,
        command_or_path: str,
        stdout: str,
        stderr: str = "",
        exit_code: int = 0,
    ) -> ToolOutputEvidence:
        """Classifies stdout/stderr, compacts if oversized, and calculates SHA-256."""
        combined = f"{stdout}\n{stderr}".strip()
        raw_bytes = combined.encode("utf-8")
        raw_sha = hashlib.sha256(raw_bytes).hexdigest()
        raw_len = len(combined)

        # Empty or trivial
        if raw_len == 0:
            return ToolOutputEvidence(
                tool_name=tool_name,
                command_or_path=command_or_path,
                exit_code=exit_code,
                classification=ToolOutputClassification.DISCARDED,
                compact_summary="Empty output.",
                raw_sha256=raw_sha,
                raw_size_bytes=0,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # Small output fits directly
        if raw_len <= cls.MAX_RELEVANT_CHARS:
            return ToolOutputEvidence(
                tool_name=tool_name,
                command_or_path=command_or_path,
                exit_code=exit_code,
                classification=ToolOutputClassification.RELEVANT,
                compact_summary=combined,
                raw_sha256=raw_sha,
                raw_size_bytes=raw_len,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # Large output: compact into bounded summary
        lines = combined.splitlines()
        head = lines[:10]
        tail = lines[-10:]
        compact = "\n".join(head + [f"... [{len(lines) - 20} lines truncated — SHA-256: {raw_sha[:12]}] ..."] + tail)

        return ToolOutputEvidence(
            tool_name=tool_name,
            command_or_path=command_or_path,
            exit_code=exit_code,
            classification=ToolOutputClassification.SUMMARIZED,
            compact_summary=compact,
            raw_sha256=raw_sha,
            raw_size_bytes=raw_len,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def classify(
        cls,
        tool_name: str,
        command_or_path: str,
        exit_code: int = 0,
        raw_stdout: str = "",
        raw_stderr: str = "",
    ) -> ToolOutputEvidence:
        """Convenience alias for process_output."""
        return cls.process_output(
            tool_name=tool_name,
            command_or_path=command_or_path,
            stdout=raw_stdout,
            stderr=raw_stderr,
            exit_code=exit_code,
        )


@dataclass
class MissionState:
    """Comprehensive state of an AntiOS mission."""
    mission_id: str
    objective: str
    acceptance_criteria: List[str]
    risk_tier: str
    current_state: MissionLifecycleState
    current_wave: int = 1
    active_workstreams: List[str] = field(default_factory=list)
    completed_workstreams: List[str] = field(default_factory=list)
    pending_workstreams: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    evidence_refs: List[Dict[str, Any]] = field(default_factory=list)
    handoff_refs: List[Dict[str, Any]] = field(default_factory=list)
    verification_state: str = "PENDING"
    learning_refs: List[str] = field(default_factory=list)
    last_verified_revision: Optional[str] = None
    project_fingerprint: str = ""
    active_agents: List[Dict[str, Any]] = field(default_factory=list)
    total_spawned_agents: int = 0
    max_active_agents: int = 10
    max_lifetime_agents: int = 20
    created_at: str = ""
    updated_at: str = ""

    def to_mission_json(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "objective": self.objective,
            "acceptance_criteria": self.acceptance_criteria,
            "risk_tier": self.risk_tier,
            "created_at": self.created_at,
            "project_fingerprint": self.project_fingerprint,
        }

    def to_progress_json(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "current_state": self.current_state.value,
            "current_wave": self.current_wave,
            "active_workstreams": self.active_workstreams,
            "completed_workstreams": self.completed_workstreams,
            "pending_workstreams": self.pending_workstreams,
            "active_agents": self.active_agents,
            "total_spawned_agents": self.total_spawned_agents,
            "updated_at": self.updated_at,
        }

    def to_evidence_json(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "decisions": self.decisions,
            "evidence_refs": self.evidence_refs,
            "verification_state": self.verification_state,
            "last_verified_revision": self.last_verified_revision,
            "learning_refs": self.learning_refs,
        }

    def attach_evidence_package(self, package: Any) -> None:
        """Binds a deterministic EvidencePackage to this mission's state."""
        pkg_dict = package.to_dict() if hasattr(package, "to_dict") else dict(package)
        ev_hash = package.compute_evidence_hash() if hasattr(package, "compute_evidence_hash") else ""
        self.evidence_refs.append({
            "package_id": pkg_dict.get("package_id"),
            "evidence_hash": ev_hash,
            "final_verdict": pkg_dict.get("final_verdict", "INCONCLUSIVE"),
            "item_count": len(pkg_dict.get("evidence_items", [])),
        })
        self.verification_state = pkg_dict.get("final_verdict", "INCONCLUSIVE")

    def to_handoffs_json(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "handoff_refs": self.handoff_refs,
        }


class MissionStateStore:
    """Manages persistent mission storage under `.antios/missions/<mission_id>/`."""

    MISSIONS_DIR = ".antios/missions"

    @classmethod
    def evaluate_persistence_threshold(
        cls,
        task_intent: str,
        file_count: int,
        wave_count: int,
        risk_tier: str,
        workforce_mode: str,
    ) -> MissionPersistenceMode:
        """Determines if a task requires persistent disk state or ephemeral memory."""
        # Trivial: 1 file, 1 wave, LOW risk, SOLO mode
        if (
            file_count <= 1
            and wave_count <= 1
            and risk_tier == "LOW"
            and workforce_mode in ("SOLO", "FOCUSED")
        ):
            return MissionPersistenceMode.EPHEMERAL

        # Complex: multi-file, staged waves, HIGH risk, or parallel workers
        return MissionPersistenceMode.PERSISTENT

    @classmethod
    def get_mission_dir(cls, mission_id: str, workspace_root: str = ".") -> Path:
        return Path(workspace_root) / cls.MISSIONS_DIR / mission_id

    @classmethod
    def save_mission(
        cls,
        state: MissionState,
        workspace_root: str = ".",
    ) -> Path:
        """Persists mission state into the 4 canonical files."""
        m_dir = cls.get_mission_dir(state.mission_id, workspace_root)
        m_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        state.updated_at = now
        if not state.created_at:
            state.created_at = now

        # 1. mission.json
        (m_dir / "mission.json").write_text(
            json.dumps(state.to_mission_json(), indent=2), encoding="utf-8"
        )
        # 2. progress.json
        (m_dir / "progress.json").write_text(
            json.dumps(state.to_progress_json(), indent=2), encoding="utf-8"
        )
        # 3. evidence.json
        (m_dir / "evidence.json").write_text(
            json.dumps(state.to_evidence_json(), indent=2), encoding="utf-8"
        )
        # 4. handoffs.json
        (m_dir / "handoffs.json").write_text(
            json.dumps(state.to_handoffs_json(), indent=2), encoding="utf-8"
        )
        return m_dir

    @classmethod
    def load_mission(
        cls,
        mission_id: str,
        workspace_root: str = ".",
    ) -> Optional[MissionState]:
        """Loads mission state from disk if present."""
        m_dir = cls.get_mission_dir(mission_id, workspace_root)
        m_file = m_dir / "mission.json"
        p_file = m_dir / "progress.json"
        e_file = m_dir / "evidence.json"
        h_file = m_dir / "handoffs.json"

        if not (m_file.exists() and p_file.exists()):
            return None

        try:
            m_data = json.loads(m_file.read_text(encoding="utf-8"))
            p_data = json.loads(p_file.read_text(encoding="utf-8"))
            e_data = json.loads(e_file.read_text(encoding="utf-8")) if e_file.exists() else {}
            h_data = json.loads(h_file.read_text(encoding="utf-8")) if h_file.exists() else {}

            return MissionState(
                mission_id=m_data.get("mission_id", mission_id),
                objective=m_data.get("objective", ""),
                acceptance_criteria=m_data.get("acceptance_criteria", []),
                risk_tier=m_data.get("risk_tier", "MEDIUM"),
                current_state=MissionLifecycleState(p_data.get("current_state", "ACTIVE")),
                current_wave=p_data.get("current_wave", 1),
                active_workstreams=p_data.get("active_workstreams", []),
                completed_workstreams=p_data.get("completed_workstreams", []),
                pending_workstreams=p_data.get("pending_workstreams", []),
                active_agents=p_data.get("active_agents", []),
                total_spawned_agents=p_data.get("total_spawned_agents", 0),
                decisions=e_data.get("decisions", []),
                evidence_refs=e_data.get("evidence_refs", []),
                verification_state=e_data.get("verification_state", "PENDING"),
                last_verified_revision=e_data.get("last_verified_revision"),
                learning_refs=e_data.get("learning_refs", []),
                handoff_refs=h_data.get("handoff_refs", []),
                project_fingerprint=m_data.get("project_fingerprint", ""),
                created_at=m_data.get("created_at", ""),
                updated_at=p_data.get("updated_at", ""),
            )
        except Exception:
            return None

    @classmethod
    def list_missions(cls, workspace_root: str = ".") -> List[str]:
        """Lists active and stored mission IDs."""
        root = Path(workspace_root) / cls.MISSIONS_DIR
        if not root.exists():
            return []
        return [p.name for p in root.iterdir() if p.is_dir() and (p / "mission.json").exists()]

    @classmethod
    def archive_mission(cls, mission_id: str, workspace_root: str = ".") -> bool:
        """Transitions mission state to ARCHIVED."""
        state = cls.load_mission(mission_id, workspace_root)
        if not state:
            return False
        state.current_state = MissionLifecycleState.ARCHIVED
        cls.save_mission(state, workspace_root)
        return True


@dataclass
class MissionRecoveryDecision:
    """Actionable decision and explanation for restoring an interrupted mission."""
    mission_id: str
    action: MissionRecoveryAction
    reconciled_wave: int
    active_agent_remnants: List[str]
    stale_handoff_count: int
    is_fingerprint_mismatch: bool
    rationale: str
    preserved_evidence_count: int


class MissionRecoveryEngine:
    """Audits persisted mission state against repository reality on restart."""

    @classmethod
    def evaluate_recovery(
        cls,
        mission_id: str,
        current_project_fingerprint: str = "",
        workspace_root: str = ".",
    ) -> MissionRecoveryDecision:
        """Audits an interrupted mission and produces a deterministic recovery action."""
        state = MissionStateStore.load_mission(mission_id, workspace_root)
        if not state:
            return MissionRecoveryDecision(
                mission_id=mission_id,
                action=MissionRecoveryAction.ABORT,
                reconciled_wave=1,
                active_agent_remnants=[],
                stale_handoff_count=0,
                is_fingerprint_mismatch=False,
                rationale="Mission files absent or corrupted on disk.",
                preserved_evidence_count=0,
            )

        # Check fingerprint drift
        fp_mismatch = bool(
            state.project_fingerprint
            and current_project_fingerprint
            and state.project_fingerprint != current_project_fingerprint
        )

        agent_remnants = [a.get("role", a.get("agent_id", "unknown")) for a in state.active_agents]
        stale_handoffs = [h for h in state.handoff_refs if h.get("is_stale", False)]

        # Scenario 1: Fingerprint mismatch requires REFRESH / REPLAN
        if fp_mismatch:
            return MissionRecoveryDecision(
                mission_id=mission_id,
                action=MissionRecoveryAction.REFRESH,
                reconciled_wave=state.current_wave,
                active_agent_remnants=agent_remnants,
                stale_handoff_count=len(stale_handoffs),
                is_fingerprint_mismatch=True,
                rationale="Project manifest or adapter changed during interruption. Context refresh required.",
                preserved_evidence_count=len(state.evidence_refs),
            )

        # Scenario 2: Active agent remnants from uncollapsed wave require wave consolidation
        if agent_remnants:
            return MissionRecoveryDecision(
                mission_id=mission_id,
                action=MissionRecoveryAction.RESUME,
                reconciled_wave=state.current_wave,
                active_agent_remnants=agent_remnants,
                stale_handoff_count=len(stale_handoffs),
                is_fingerprint_mismatch=False,
                rationale=f"Resuming interrupted wave {state.current_wave} with {len(agent_remnants)} pending active workers.",
                preserved_evidence_count=len(state.evidence_refs),
            )

        # Scenario 3: Clean state at completion or verify
        if state.current_state in (MissionLifecycleState.VERIFYING, MissionLifecycleState.ACTIVE):
            return MissionRecoveryDecision(
                mission_id=mission_id,
                action=MissionRecoveryAction.RESUME,
                reconciled_wave=state.current_wave,
                active_agent_remnants=[],
                stale_handoff_count=0,
                is_fingerprint_mismatch=False,
                rationale=f"Clean resumption of mission {mission_id} at {state.current_state.value}.",
                preserved_evidence_count=len(state.evidence_refs),
            )

        # Default clean resume
        return MissionRecoveryDecision(
            mission_id=mission_id,
            action=MissionRecoveryAction.RESUME,
            reconciled_wave=state.current_wave,
            active_agent_remnants=[],
            stale_handoff_count=0,
            is_fingerprint_mismatch=False,
            rationale="Deterministic resumption from persistent mission state.",
            preserved_evidence_count=len(state.evidence_refs),
        )
