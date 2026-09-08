"""AntiOS 2.0 Project Learning & Safe Intelligence Evolution Engine.

Phases 61–66:
- Phase 61: Deterministic Project-Local Observation Capture
- Phase 62: Deterministic Lesson Distillation & Signature Deduplication
- Phase 63: Evidence Promotion Lifecycle (OBSERVED -> CANDIDATE -> VALIDATED -> DURABLE)
- Phase 64: Safe Skill & Knowledge Evolution (Learning -> Proposals, Never Silent Mutation)
- Phase 65: Knowledge Decay & Staleness Detection
- Phase 66: Learning Safety Gate & Certification Boundary

Core Principle: "Learning is evidence accumulation, not memory mutation."
The system NEVER treats an agent's statement or an LLM inference as permanent truth.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from framework.core.guard import IMMUTABLE_CORE_ZONES
from framework.core.memory import (
    DeterministicLessonMatcher,
    KnowledgeAuthority,
    LessonRecord,
)
from framework.core.verdict import VerificationVerdict


# -----------------------------------------------------------------------------
# Phase 61: Epistemic Classification & Observation Model
# -----------------------------------------------------------------------------

class EpistemicSource(str, Enum):
    """Rigorous classification of information origin.
    
    NEVER silently merge or conflate these epistemic categories.
    """
    OBSERVED_FACT = "OBSERVED_FACT"          # Physical reality: exit code 0, test failure, file existence, git diff (Weight 1.0)
    AGENT_INTERPRETATION = "AGENT_INTERPRETATION"  # Agent hypothesis, rationale, or inference (Weight 0.3)
    USER_ASSERTION = "USER_ASSERTION"        # Direct user instruction or explicit correction (Weight 0.9)
    DERIVED_INFERENCE = "DERIVED_INFERENCE"  # Logical deduction combining multiple observed facts (Weight 0.7)


EPISTEMIC_WEIGHTS: Dict[EpistemicSource, float] = {
    EpistemicSource.OBSERVED_FACT: 1.0,
    EpistemicSource.AGENT_INTERPRETATION: 0.3,
    EpistemicSource.USER_ASSERTION: 0.9,
    EpistemicSource.DERIVED_INFERENCE: 0.7,
}


class ObservationType(str, Enum):
    """The 13 canonical engineering observation types in AntiOS."""
    TASK_OUTCOME = "TASK_OUTCOME"
    TEST_FAILURE = "TEST_FAILURE"
    SUCCESSFUL_FIX = "SUCCESSFUL_FIX"
    USER_CORRECTION = "USER_CORRECTION"
    PROJECT_CONVENTION = "PROJECT_CONVENTION"
    ARCHITECTURAL_DISCOVERY = "ARCHITECTURAL_DISCOVERY"
    REPEATED_NAVIGATION_PATH = "REPEATED_NAVIGATION_PATH"
    TOOL_FAILURE = "TOOL_FAILURE"
    SPECIALIST_FINDING = "SPECIALIST_FINDING"
    VERIFICATION_RESULT = "VERIFICATION_RESULT"
    RECOVERY_EVENT = "RECOVERY_EVENT"
    CAPABILITY_GAP = "CAPABILITY_GAP"
    REJECTED_APPROACH = "REJECTED_APPROACH"


class KnowledgeState(str, Enum):
    """Lifecycle state of learned knowledge and observations."""
    ACTIVE = "ACTIVE"               # Grounded in current disk reality and manifest fingerprint
    STALE = "STALE"                 # Referenced files missing, manifest drifted, or unconfirmed
    SUPERSEDED = "SUPERSEDED"       # Replaced by a more comprehensive or recent validated lesson
    INVALIDATED = "INVALIDATED"     # Falsified by physical test failure or contradictory verdict
    RETIRED = "RETIRED"             # Archived historical record; cannot be used as authoritative facts


@dataclass
class Observation:
    """Structured, bounded engineering observation with complete provenance.
    
    Boundaries:
    - title: <= 120 chars
    - content: <= 1,000 chars
    - related_files: <= 10 paths
    """
    observation_id: str
    timestamp: str
    mission_id: str
    source: str
    epistemic_source: EpistemicSource
    observation_type: ObservationType
    title: str
    content: str
    affected_subsystem: str = "PROJECT_LOCAL"
    affected_component: str = ""
    related_files: List[str] = field(default_factory=list)
    evidence_references: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    project_fingerprint: str = ""
    status: KnowledgeState = KnowledgeState.ACTIVE
    created_by: str = "primary-engineer"
    recurrence_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Enforce hard bounded length limits
        if len(self.title) > 120:
            self.title = self.title[:117] + "..."
        if len(self.content) > 1000:
            self.content = self.content[:997] + "..."
        if len(self.related_files) > 10:
            self.related_files = self.related_files[:10]
        self.confidence = max(0.0, min(1.0, float(self.confidence)))

    @property
    def effective_weight(self) -> float:
        return EPISTEMIC_WEIGHTS.get(self.epistemic_source, 0.3) * self.confidence

    def compute_signature(self) -> str:
        """Deterministic signature for duplicate detection."""
        norm_title = " ".join(self.title.lower().split())
        norm_subsystem = self.affected_subsystem.strip().lower()
        norm_component = self.affected_component.strip().lower()
        sig_raw = f"{self.observation_type.value}|{norm_subsystem}|{norm_component}|{norm_title}"
        return hashlib.sha256(sig_raw.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "timestamp": self.timestamp,
            "mission_id": self.mission_id,
            "source": self.source,
            "epistemic_source": self.epistemic_source.value,
            "observation_type": self.observation_type.value,
            "title": self.title,
            "content": self.content,
            "affected_subsystem": self.affected_subsystem,
            "affected_component": self.affected_component,
            "related_files": self.related_files,
            "evidence_references": self.evidence_references,
            "confidence": round(self.confidence, 3),
            "project_fingerprint": self.project_fingerprint,
            "status": self.status.value,
            "created_by": self.created_by,
            "recurrence_count": self.recurrence_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Observation:
        return cls(
            observation_id=data["observation_id"],
            timestamp=data.get("timestamp", ""),
            mission_id=data.get("mission_id", ""),
            source=data.get("source", ""),
            epistemic_source=EpistemicSource(data.get("epistemic_source", EpistemicSource.OBSERVED_FACT.value)),
            observation_type=ObservationType(data.get("observation_type", ObservationType.TASK_OUTCOME.value)),
            title=data.get("title", ""),
            content=data.get("content", ""),
            affected_subsystem=data.get("affected_subsystem", "PROJECT_LOCAL"),
            affected_component=data.get("affected_component", ""),
            related_files=data.get("related_files", []),
            evidence_references=data.get("evidence_references", {}),
            confidence=data.get("confidence", 1.0),
            project_fingerprint=data.get("project_fingerprint", ""),
            status=KnowledgeState(data.get("status", KnowledgeState.ACTIVE.value)),
            created_by=data.get("created_by", "primary-engineer"),
            recurrence_count=data.get("recurrence_count", 1),
            metadata=data.get("metadata", {}),
        )


class ObservationStore:
    """Bounded, project-local observation storage.
    
    Prevents uncontrolled memory growth:
    - MAX_OBSERVATIONS = 100
    - MAX_STORAGE_BYTES = 200,000
    """
    MAX_OBSERVATIONS = 100
    MAX_STORAGE_BYTES = 200_000

    def __init__(self, observations: Optional[List[Observation]] = None):
        self._observations: Dict[str, Observation] = {}
        if observations:
            for obs in observations:
                self._observations[obs.observation_id] = obs
        self._enforce_bounds()

    def add_observation(self, obs: Observation) -> Tuple[Observation, bool]:
        """Adds or reinforces an observation.
        
        Returns:
            (observation, is_new: bool)
        """
        # Deduplication check by structural signature
        sig = obs.compute_signature()
        for existing in self._observations.values():
            if existing.status != KnowledgeState.RETIRED and existing.compute_signature() == sig:
                # Reinforce existing observation
                existing.recurrence_count += 1
                existing.timestamp = obs.timestamp
                existing.confidence = min(1.0, existing.confidence + 0.05)
                # Merge evidence references
                for k, v in obs.evidence_references.items():
                    if k not in existing.evidence_references:
                        existing.evidence_references[k] = v
                # Merge related files up to limit
                for f in obs.related_files:
                    if f not in existing.related_files and len(existing.related_files) < 10:
                        existing.related_files.append(f)
                return existing, False

        # New observation
        self._observations[obs.observation_id] = obs
        self._enforce_bounds()
        return obs, True

    def get(self, observation_id: str) -> Optional[Observation]:
        return self._observations.get(observation_id)

    def list_all(self) -> List[Observation]:
        return list(self._observations.values())

    def get_active(self) -> List[Observation]:
        return [o for o in self._observations.values() if o.status == KnowledgeState.ACTIVE]

    def get_by_subsystem(self, subsystem: str) -> List[Observation]:
        norm = subsystem.strip().lower()
        return [o for o in self._observations.values() if o.affected_subsystem.strip().lower() == norm]

    def _enforce_bounds(self) -> None:
        """Evicts oldest non-active or lowest-confidence items if budget exceeded."""
        if len(self._observations) <= self.MAX_OBSERVATIONS:
            return

        # Sort priority for retention: ACTIVE > STALE > SUPERSEDED > INVALIDATED > RETIRED
        state_priority = {
            KnowledgeState.ACTIVE: 4,
            KnowledgeState.STALE: 3,
            KnowledgeState.SUPERSEDED: 2,
            KnowledgeState.INVALIDATED: 1,
            KnowledgeState.RETIRED: 0,
        }

        sorted_items = sorted(
            self._observations.values(),
            key=lambda o: (state_priority.get(o.status, 0), o.effective_weight, o.recurrence_count, o.timestamp),
            reverse=False,  # lowest rank first
        )

        excess = len(self._observations) - self.MAX_OBSERVATIONS
        for item in sorted_items[:excess]:
            del self._observations[item.observation_id]

    def to_json(self, indent: int = 2) -> str:
        data = {
            "schema_version": "2.0.0",
            "total_observations": len(self._observations),
            "observations": [o.to_dict() for o in self._observations.values()],
        }
        return json.dumps(data, indent=indent)

    def save_to_file(self, path: Union[str, Path]) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        content = self.to_json()
        p.write_text(content, encoding="utf-8", newline="\n")

    @classmethod
    def load_from_file(cls, path: Union[str, Path]) -> ObservationStore:
        p = Path(path)
        if not p.is_file():
            return cls()
        try:
            raw = p.read_text(encoding="utf-8")
            data = json.loads(raw)
            obs_list = [Observation.from_dict(d) for d in data.get("observations", [])]
            return cls(obs_list)
        except Exception:
            return cls()


# -----------------------------------------------------------------------------
# Phase 62: Lesson Distillation Model
# -----------------------------------------------------------------------------

@dataclass
class CandidateLesson:
    """Provisional lesson distilled from engineering observations.
    
    Retains explicit evidence links to the observations that produced it.
    Authority begins strictly as CANDIDATE.
    """
    lesson_id: str
    title: str
    trigger_or_failure: str
    rule_or_action: str
    authority: KnowledgeAuthority = KnowledgeAuthority.CANDIDATE
    evidence_observation_ids: List[str] = field(default_factory=list)
    evidence: str = ""
    date: str = ""
    category: str = "DEVELOPMENT_CONVENTION"
    problem_pattern: str = ""
    verified_resolution: str = ""
    scope: str = "PROJECT_LOCAL"
    when_applies: str = ""
    when_not_applies: str = ""
    recurrence_count: int = 1
    task_ids: List[str] = field(default_factory=list)
    affected_subsystem: str = "PROJECT_LOCAL"
    affected_component: str = ""
    related_files: List[str] = field(default_factory=list)
    confidence: float = 0.5
    state: KnowledgeState = KnowledgeState.ACTIVE
    invalidation_reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_lesson_record(self) -> LessonRecord:
        """Converts to standard AntiOS LessonRecord."""
        rec = LessonRecord(
            lesson_id=self.lesson_id,
            title=self.title,
            trigger_or_failure=self.trigger_or_failure,
            rule_or_action=self.rule_or_action,
            authority=self.authority,
            evidence=self.evidence,
            date=self.date,
            category=self.category,
            metadata={
                **self.metadata,
                "evidence_observation_ids": self.evidence_observation_ids,
                "affected_subsystem": self.affected_subsystem,
                "affected_component": self.affected_component,
                "confidence": self.confidence,
                "state": self.state.value,
            },
            problem_pattern=self.problem_pattern,
            verified_resolution=self.verified_resolution,
            scope=self.scope,
            when_applies=self.when_applies,
            when_not_applies=self.when_not_applies,
            recurrence_count=self.recurrence_count,
            task_ids=self.task_ids,
        )
        return rec

    @classmethod
    def from_lesson_record(cls, record: LessonRecord) -> CandidateLesson:
        meta = record.metadata or {}
        return cls(
            lesson_id=record.lesson_id,
            title=record.title,
            trigger_or_failure=record.trigger_or_failure,
            rule_or_action=record.rule_or_action,
            authority=record.authority,
            evidence_observation_ids=meta.get("evidence_observation_ids", []),
            evidence=record.evidence,
            date=record.date,
            category=record.category,
            problem_pattern=record.problem_pattern,
            verified_resolution=record.verified_resolution,
            scope=record.scope,
            when_applies=record.when_applies,
            when_not_applies=record.when_not_applies,
            recurrence_count=record.recurrence_count,
            task_ids=record.task_ids,
            affected_subsystem=meta.get("affected_subsystem", "PROJECT_LOCAL"),
            affected_component=meta.get("affected_component", ""),
            related_files=meta.get("related_files", []),
            confidence=meta.get("confidence", 0.5),
            state=KnowledgeState(meta.get("state", KnowledgeState.ACTIVE.value)),
            metadata=meta,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lesson_id": self.lesson_id,
            "title": self.title,
            "trigger_or_failure": self.trigger_or_failure,
            "rule_or_action": self.rule_or_action,
            "authority": self.authority.value,
            "evidence_observation_ids": self.evidence_observation_ids,
            "evidence": self.evidence,
            "date": self.date,
            "category": self.category,
            "problem_pattern": self.problem_pattern,
            "verified_resolution": self.verified_resolution,
            "scope": self.scope,
            "when_applies": self.when_applies,
            "when_not_applies": self.when_not_applies,
            "recurrence_count": self.recurrence_count,
            "task_ids": self.task_ids,
            "affected_subsystem": self.affected_subsystem,
            "affected_component": self.affected_component,
            "related_files": self.related_files,
            "confidence": round(self.confidence, 3),
            "state": self.state.value,
            "invalidation_reason": self.invalidation_reason,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CandidateLesson:
        return cls(
            lesson_id=data["lesson_id"],
            title=data.get("title", ""),
            trigger_or_failure=data.get("trigger_or_failure", ""),
            rule_or_action=data.get("rule_or_action", ""),
            authority=KnowledgeAuthority(data.get("authority", KnowledgeAuthority.CANDIDATE.value)),
            evidence_observation_ids=data.get("evidence_observation_ids", []),
            evidence=data.get("evidence", ""),
            date=data.get("date", ""),
            category=data.get("category", "DEVELOPMENT_CONVENTION"),
            problem_pattern=data.get("problem_pattern", ""),
            verified_resolution=data.get("verified_resolution", ""),
            scope=data.get("scope", "PROJECT_LOCAL"),
            when_applies=data.get("when_applies", ""),
            when_not_applies=data.get("when_not_applies", ""),
            recurrence_count=data.get("recurrence_count", 1),
            task_ids=data.get("task_ids", []),
            affected_subsystem=data.get("affected_subsystem", "PROJECT_LOCAL"),
            affected_component=data.get("affected_component", ""),
            related_files=data.get("related_files", []),
            confidence=data.get("confidence", 0.5),
            state=KnowledgeState(data.get("state", KnowledgeState.ACTIVE.value)),
            invalidation_reason=data.get("invalidation_reason", ""),
            metadata=data.get("metadata", {}),
        )


class LessonDistiller:
    """Deterministic distillation of candidate lessons from observations.
    
    Transforms causal sequences of witnessed events into candidate lessons:
    e.g., TEST_FAILURE -> SUCCESSFUL_FIX -> VERIFICATION_RESULT (PASS)
    or: USER_CORRECTION -> SUCCESSFUL_FIX
    """

    @staticmethod
    def distill_from_observations(
        observations: List[Observation],
        existing_candidates: Optional[List[CandidateLesson]] = None,
    ) -> List[CandidateLesson]:
        candidates: List[CandidateLesson] = list(existing_candidates or [])

        # Group observations by task/mission
        by_mission: Dict[str, List[Observation]] = {}
        for obs in observations:
            if obs.status == KnowledgeState.ACTIVE:
                by_mission.setdefault(obs.mission_id or "unassigned", []).append(obs)

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        for mission_id, obs_list in by_mission.items():
            # Pattern 1: Test Failure -> Fix -> Verification Pass
            test_failures = [o for o in obs_list if o.observation_type == ObservationType.TEST_FAILURE]
            successful_fixes = [o for o in obs_list if o.observation_type == ObservationType.SUCCESSFUL_FIX]
            verification_passes = [
                o for o in obs_list
                if o.observation_type == ObservationType.VERIFICATION_RESULT
                and "PASS" in (o.title + " " + o.content).upper()
            ]

            if test_failures and successful_fixes:
                for tf in test_failures:
                    for fix in successful_fixes:
                        # Match component or subsystem
                        if tf.affected_subsystem == fix.affected_subsystem:
                            title = f"Fix for failure in {tf.affected_subsystem}: {fix.title}"
                            trigger = tf.content[:200]
                            action = fix.content[:200]
                            evidence_ids = [tf.observation_id, fix.observation_id]
                            if verification_passes:
                                evidence_ids.append(verification_passes[0].observation_id)

                            LessonDistiller._merge_or_append_candidate(
                                candidates=candidates,
                                title=title,
                                trigger=trigger,
                                action=action,
                                task_id=mission_id,
                                evidence_ids=evidence_ids,
                                evidence_str=f"Witnessed failure in task {mission_id}; resolved by {fix.title}",
                                subsystem=tf.affected_subsystem,
                                component=tf.affected_component or fix.affected_component,
                                related_files=list(set(tf.related_files + fix.related_files)),
                                date_str=now_str,
                                verified_res=fix.content[:150],
                            )

            # Pattern 2: User Correction -> Successful Fix
            user_corrections = [o for o in obs_list if o.observation_type == ObservationType.USER_CORRECTION]
            if user_corrections:
                for uc in user_corrections:
                    fix_match = successful_fixes[0] if successful_fixes else None
                    action = fix_match.content[:200] if fix_match else "Adhere strictly to user corrected rule"
                    evidence_ids = [uc.observation_id]
                    if fix_match:
                        evidence_ids.append(fix_match.observation_id)

                    LessonDistiller._merge_or_append_candidate(
                        candidates=candidates,
                        title=f"User correction regarding {uc.affected_subsystem}",
                        trigger=uc.content[:200],
                        action=action,
                        task_id=mission_id,
                        evidence_ids=evidence_ids,
                        evidence_str=f"Direct user correction in task {mission_id}: {uc.title}",
                        subsystem=uc.affected_subsystem,
                        component=uc.affected_component,
                        related_files=uc.related_files,
                        date_str=now_str,
                        verified_res=action,
                    )

            # Pattern 3: Discovered Project Convention
            conventions = [
                o for o in obs_list
                if o.observation_type in (ObservationType.PROJECT_CONVENTION, ObservationType.ARCHITECTURAL_DISCOVERY)
                and o.epistemic_source == EpistemicSource.OBSERVED_FACT
            ]
            for conv in conventions:
                LessonDistiller._merge_or_append_candidate(
                    candidates=candidates,
                    title=f"Discovered convention: {conv.title}",
                    trigger=f"When working with {conv.affected_subsystem}",
                    action=conv.content[:200],
                    task_id=mission_id,
                    evidence_ids=[conv.observation_id],
                    evidence_str=f"Observed on disk in task {mission_id}: {conv.title}",
                    subsystem=conv.affected_subsystem,
                    component=conv.affected_component,
                    related_files=conv.related_files,
                    date_str=now_str,
                    verified_res="",
                )

        return candidates

    @staticmethod
    def _merge_or_append_candidate(
        candidates: List[CandidateLesson],
        title: str,
        trigger: str,
        action: str,
        task_id: str,
        evidence_ids: List[str],
        evidence_str: str,
        subsystem: str,
        component: str,
        related_files: List[str],
        date_str: str,
        verified_res: str,
    ) -> None:
        # Check semantic duplicate with existing candidate
        for cand in candidates:
            if cand.state != KnowledgeState.ACTIVE:
                continue
            if DeterministicLessonMatcher.are_semantically_equivalent(cand.trigger_or_failure, trigger):
                # Update / reinforce existing candidate
                if task_id and task_id not in cand.task_ids:
                    cand.task_ids.append(task_id)
                cand.recurrence_count = max(cand.recurrence_count + 1, len(cand.task_ids))
                for eid in evidence_ids:
                    if eid not in cand.evidence_observation_ids:
                        cand.evidence_observation_ids.append(eid)
                if evidence_str and evidence_str not in cand.evidence:
                    cand.evidence = f"{cand.evidence}; {evidence_str}".strip("; ")
                if verified_res and not cand.verified_resolution:
                    cand.verified_resolution = verified_res
                cand.confidence = min(1.0, cand.confidence + 0.1)
                for f in related_files:
                    if f not in cand.related_files and len(cand.related_files) < 10:
                        cand.related_files.append(f)
                return

        # Create new candidate
        h = hashlib.sha256(f"{trigger}|{action}|{subsystem}".encode("utf-8")).hexdigest()[:8]
        lesson_id = f"les-{h}"
        new_cand = CandidateLesson(
            lesson_id=lesson_id,
            title=title[:120],
            trigger_or_failure=trigger,
            rule_or_action=action,
            authority=KnowledgeAuthority.CANDIDATE,
            evidence_observation_ids=evidence_ids,
            evidence=evidence_str,
            date=date_str,
            scope="PROJECT_LOCAL",
            problem_pattern=trigger[:100],
            verified_resolution=verified_res,
            recurrence_count=1,
            task_ids=[task_id] if task_id else [],
            affected_subsystem=subsystem,
            affected_component=component,
            related_files=related_files[:10],
            confidence=0.5,
            state=KnowledgeState.ACTIVE,
        )
        candidates.append(new_cand)


# -----------------------------------------------------------------------------
# Phase 63: Evidence Promotion Engine
# -----------------------------------------------------------------------------

class EvidencePromotionEngine:
    """Evaluates candidate lessons for promotion using deterministic evidence requirements.
    
    Promotion Lifecycle:
    OBSERVED -> CANDIDATE -> VALIDATED -> DURABLE
    
    Strong Evidence Requirements for VALIDATED:
    - Multi-task recurrence: distinct task_ids >= 2
    - Independent Verifier Verdict: PASS verdict covering the change
    - User Assertion: Explicit user confirmation
    - Physical project config / test evidence
    
    Weak Evidence (NEVER promotes):
    - Single agent statement / belief
    - Unverified LLM inference
    - Uncorroborated single run
    """

    @staticmethod
    def evaluate_promotion(
        candidate: CandidateLesson,
        observations: List[Observation],
        verifications: Optional[List[VerificationVerdict]] = None,
        min_recurrences: int = 2,
    ) -> Tuple[KnowledgeAuthority, str, float]:
        """Evaluates whether candidate warrants promotion.
        
        Returns:
            (promoted_authority, reason, updated_confidence)
        """
        # Rule 0: Inactive or conflicting lessons cannot be promoted
        if candidate.state != KnowledgeState.ACTIVE:
            return candidate.authority, f"Cannot promote lesson in state {candidate.state.value}", candidate.confidence

        # Correlate linked observations
        linked_obs = [o for o in observations if o.observation_id in candidate.evidence_observation_ids]
        has_user_assertion = any(o.epistemic_source == EpistemicSource.USER_ASSERTION for o in linked_obs)
        has_physical_fact = any(o.epistemic_source == EpistemicSource.OBSERVED_FACT for o in linked_obs)
        only_agent_interpretation = all(o.epistemic_source == EpistemicSource.AGENT_INTERPRETATION for o in linked_obs) if linked_obs else True

        # Check for independent verification pass
        has_verifier_pass = False
        if verifications:
            for v in verifications:
                if v.status == "PASS" and v.same_change_set_verified:
                    has_verifier_pass = True
                    break

        distinct_tasks = len(set(candidate.task_ids))

        # Check for weak-evidence denial
        if only_agent_interpretation and not has_user_assertion and not has_verifier_pass and distinct_tasks < min_recurrences:
            return (
                KnowledgeAuthority.CANDIDATE,
                "Promotion rejected: Agent interpretation alone does not constitute validatable project evidence.",
                0.3,
            )

        # Check promotion to DURABLE
        # Durable requires: distinct tasks >= 3 OR (user assertion + verifier pass + distinct tasks >= 2)
        if distinct_tasks >= 3 or (has_user_assertion and has_verifier_pass and distinct_tasks >= 2):
            new_conf = min(1.0, max(0.85, candidate.confidence + 0.2))
            return (
                KnowledgeAuthority.DURABLE,
                f"Promoted to DURABLE backed by strong multi-task evidence ({distinct_tasks} tasks) and verification.",
                new_conf,
            )

        # Check promotion to VALIDATED
        # Validated requires at least ONE strong evidence signal + confidence >= 0.6
        has_strong_evidence = (
            distinct_tasks >= min_recurrences
            or has_user_assertion
            or has_verifier_pass
            or (has_physical_fact and bool(candidate.verified_resolution))
        )

        if has_strong_evidence:
            new_conf = min(1.0, max(0.75, candidate.confidence + 0.15))
            reason = "Promoted to VALIDATED backed by "
            reasons = []
            if distinct_tasks >= min_recurrences:
                reasons.append(f"multi-task recurrence ({distinct_tasks} tasks)")
            if has_user_assertion:
                reasons.append("user-confirmed correction")
            if has_verifier_pass:
                reasons.append("independent verifier PASS verdict")
            if has_physical_fact and candidate.verified_resolution:
                reasons.append("physically verified resolution")
            reason += ", ".join(reasons) + "."
            return KnowledgeAuthority.VALIDATED, reason, new_conf

        return candidate.authority, "Candidate retained: Insufficient evidence accumulation for promotion.", candidate.confidence


# -----------------------------------------------------------------------------
# Phase 64: Safe Skill & Knowledge Evolution Model
# -----------------------------------------------------------------------------

class ProposalType(str, Enum):
    """Categorization of proposed project evolutions."""
    SKILL_UPDATE = "SKILL_UPDATE"
    SPECIALIST_CAPABILITY = "SPECIALIST_CAPABILITY"
    PROJECT_CONVENTION = "PROJECT_CONVENTION"
    DOCUMENTATION_UPDATE = "DOCUMENTATION_UPDATE"
    CAPABILITY_REFINEMENT = "CAPABILITY_REFINEMENT"


@dataclass
class EvolutionProposal:
    """Explicit, auditable proposal for project skill or knowledge evolution.
    
    ENFORCES: LEARNING -> PROPOSAL (NEVER LEARNING -> SILENT FILE MUTATION).
    """
    proposal_id: str
    proposal_type: ProposalType
    target_artifact: str
    what_should_change: str
    why: str
    evidence_observation_ids: List[str] = field(default_factory=list)
    confidence: float = 1.0
    affected_artifacts: List[str] = field(default_factory=list)
    risk_tier: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    blast_radius: List[str] = field(default_factory=list)
    verification_required: List[str] = field(default_factory=list)
    requires_human_approval: bool = True
    status: str = "PENDING_REVIEW"  # PENDING_REVIEW, APPROVED, REJECTED, APPLIED
    lesson_id: str = ""
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "proposal_type": self.proposal_type.value,
            "target_artifact": self.target_artifact,
            "what_should_change": self.what_should_change,
            "why": self.why,
            "evidence_observation_ids": self.evidence_observation_ids,
            "confidence": round(self.confidence, 3),
            "affected_artifacts": self.affected_artifacts,
            "risk_tier": self.risk_tier,
            "blast_radius": self.blast_radius,
            "verification_required": self.verification_required,
            "requires_human_approval": self.requires_human_approval,
            "status": self.status,
            "lesson_id": self.lesson_id,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvolutionProposal:
        return cls(
            proposal_id=data["proposal_id"],
            proposal_type=ProposalType(data.get("proposal_type", ProposalType.DOCUMENTATION_UPDATE.value)),
            target_artifact=data.get("target_artifact", ""),
            what_should_change=data.get("what_should_change", ""),
            why=data.get("why", ""),
            evidence_observation_ids=data.get("evidence_observation_ids", []),
            confidence=data.get("confidence", 1.0),
            affected_artifacts=data.get("affected_artifacts", []),
            risk_tier=data.get("risk_tier", "MEDIUM"),
            blast_radius=data.get("blast_radius", []),
            verification_required=data.get("verification_required", []),
            requires_human_approval=data.get("requires_human_approval", True),
            status=data.get("status", "PENDING_REVIEW"),
            lesson_id=data.get("lesson_id", ""),
            created_at=data.get("created_at", ""),
            metadata=data.get("metadata", {}),
        )


class EvolutionProposalEngine:
    """Generates structured proposals from validated and durable lessons."""

    @staticmethod
    def generate_proposal(
        lesson: CandidateLesson,
        repo_root: Union[str, Path],
    ) -> Optional[EvolutionProposal]:
        """Synthesizes a safe EvolutionProposal for a VALIDATED or DURABLE lesson."""
        if lesson.authority not in (KnowledgeAuthority.VALIDATED, KnowledgeAuthority.DURABLE):
            return None

        now_ts = datetime.now(timezone.utc).isoformat()
        h = hashlib.sha256(f"{lesson.lesson_id}|{lesson.title}".encode("utf-8")).hexdigest()[:8]
        prop_id = f"prop-{h}"

        # Determine proposal type & target artifact based on lesson category / subsystem
        if "skill" in lesson.category.lower() or "workflow" in lesson.category.lower():
            p_type = ProposalType.SKILL_UPDATE
            target = f".agents/skills/antios-{lesson.affected_subsystem.lower()}/SKILL.md"
            risk = "MEDIUM"
            verif = ["python framework/scripts/tools/verify_intelligence.py ."]
        elif "convention" in lesson.category.lower() or "config" in lesson.category.lower():
            p_type = ProposalType.PROJECT_CONVENTION
            target = "antios.config.json"
            risk = "LOW"
            verif = ["python framework/scripts/tools/check_worktree.py ."]
        elif "specialist" in lesson.category.lower():
            p_type = ProposalType.SPECIALIST_CAPABILITY
            target = ".antios/agent_topology.json"
            risk = "MEDIUM"
            verif = ["python framework/scripts/tools/verify_intelligence.py ."]
        else:
            p_type = ProposalType.DOCUMENTATION_UPDATE
            target = "docs/PROJECT_KNOWLEDGE.md"
            risk = "LOW"
            verif = ["python framework/scripts/tools/audit_docs.py ."]

        proposal = EvolutionProposal(
            proposal_id=prop_id,
            proposal_type=p_type,
            target_artifact=target,
            what_should_change=f"Incorporate lesson [{lesson.lesson_id}]: {lesson.rule_or_action}",
            why=f"Backed by validated lesson '{lesson.title}' ({lesson.recurrence_count} occurrences)",
            evidence_observation_ids=list(lesson.evidence_observation_ids),
            confidence=lesson.confidence,
            affected_artifacts=[target] + list(lesson.related_files[:3]),
            risk_tier=risk,
            blast_radius=[lesson.affected_subsystem],
            verification_required=verif,
            requires_human_approval=True,
            status="PENDING_REVIEW",
            lesson_id=lesson.lesson_id,
            created_at=now_ts,
        )

        # Safety Gate Check: Core immutability
        is_safe, denial_reason = LearningSafetyGate.validate_proposal(proposal, repo_root)
        if not is_safe:
            return None

        return proposal


# -----------------------------------------------------------------------------
# Phase 65: Knowledge Decay & Staleness Detection
# -----------------------------------------------------------------------------

@dataclass
class DecayReport:
    """Report detailing knowledge staleness, supersession, or invalidation."""
    active_count: int
    stale_count: int
    superseded_count: int
    invalidated_count: int
    decayed_items: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_count": self.active_count,
            "stale_count": self.stale_count,
            "superseded_count": self.superseded_count,
            "invalidated_count": self.invalidated_count,
            "decayed_items": self.decayed_items,
        }


class KnowledgeDecayEngine:
    """Detects when learned lessons, observations, or proposals are no longer valid."""

    @staticmethod
    def evaluate_decay(
        lessons: List[CandidateLesson],
        proposals: List[EvolutionProposal],
        repo_root: Union[str, Path],
        current_fingerprint: str = "",
        anatomy_subsystems: Optional[List[str]] = None,
    ) -> DecayReport:
        root = Path(os.path.normcase(os.path.abspath(repo_root)))
        decayed_items: List[Dict[str, str]] = []

        active_cnt = 0
        stale_cnt = 0
        superseded_cnt = 0
        invalidated_cnt = 0

        valid_subsystems = set(s.strip().lower() for s in (anatomy_subsystems or []))

        for lesson in lessons:
            if lesson.state in (KnowledgeState.INVALIDATED, KnowledgeState.RETIRED):
                invalidated_cnt += 1
                continue
            if lesson.state == KnowledgeState.SUPERSEDED:
                superseded_cnt += 1
                continue

            is_stale = False
            reasons: List[str] = []

            # 1. Check if referenced files were deleted
            for rel_path in lesson.related_files:
                target_file = root / rel_path
                if not target_file.exists():
                    is_stale = True
                    reasons.append(f"Referenced file '{rel_path}' no longer exists on disk")

            # 2. Check if affected subsystem was removed
            if valid_subsystems and lesson.affected_subsystem.strip().lower() not in valid_subsystems:
                if lesson.affected_subsystem not in ("PROJECT_LOCAL", "CORE"):
                    is_stale = True
                    reasons.append(f"Subsystem '{lesson.affected_subsystem}' is no longer present in project anatomy")

            if is_stale:
                lesson.state = KnowledgeState.STALE
                lesson.invalidation_reason = "; ".join(reasons)
                stale_cnt += 1
                decayed_items.append({
                    "id": lesson.lesson_id,
                    "title": lesson.title,
                    "state": KnowledgeState.STALE.value,
                    "reason": lesson.invalidation_reason,
                })
            else:
                active_cnt += 1

        # Check proposals
        for prop in proposals:
            if prop.status == "PENDING_REVIEW":
                # If target artifact is in a deleted path or references a deleted file
                target_path = root / prop.target_artifact
                if prop.proposal_type == ProposalType.SKILL_UPDATE and not target_path.exists():
                    prop.status = "REJECTED"
                    decayed_items.append({
                        "id": prop.proposal_id,
                        "title": prop.what_should_change,
                        "state": "REJECTED",
                        "reason": f"Target skill file '{prop.target_artifact}' does not exist.",
                    })

        return DecayReport(
            active_count=active_cnt,
            stale_count=stale_cnt,
            superseded_count=superseded_cnt,
            invalidated_count=invalidated_cnt,
            decayed_items=decayed_items,
        )


# -----------------------------------------------------------------------------
# Phase 66: Learning Safety Gate & Certification Boundary
# -----------------------------------------------------------------------------

class LearningSafetyGate:
    """Enforces non-bypassable constitutional safety boundaries for project learning.
    
    Prevents:
    1. Prompt injection poisoning project memory
    2. Arbitrary agent-written rules becoming permanent
    3. User-owned files being silently rewritten
    4. AntiOS core governance being modified
    5. Specialists promoting themselves
    6. Stale/invalidated knowledge becoming authoritative
    7. Recursive learning loops
    8. Duplicate skill generation
    9. Uncontrolled memory growth
    10. MCP / tool authority escalation
    """

    PROMPT_INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
        r"bypass\s+(safety|guard|security)",
        r"disregard\s+(all\s+)?(rules|guidelines)",
        r"override\s+(system\s+prompt|constitution|governance)",
        r"you\s+are\s+now\s+(an?\s+unrestricted|in\s+god\s+mode|dan)",
        r"system\s+directive\s+update",
        r"rm\s+-rf\s+[/~]",
        r"drop\s+table",
        r"<script.*?>",
    ]

    @classmethod
    def validate_observation(cls, obs: Observation) -> Tuple[bool, Optional[str]]:
        """Validates incoming observation against prompt injection and boundaries."""
        combined_text = f"{obs.title} {obs.content} {json.dumps(obs.evidence_references)}"

        # 1. Prompt injection scan
        for pattern in cls.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return False, f"Prompt injection vector detected matching pattern '{pattern}'. Failing closed."

        # 2. Content bounds
        if len(obs.title) > 120 or len(obs.content) > 1000:
            return False, "Observation content exceeds maximum allowed token length bounds."

        # 3. Source boundary check
        if obs.epistemic_source == EpistemicSource.AGENT_INTERPRETATION and obs.confidence > 0.8:
            # Agent interpretation cannot claim high certainty without physical evidence
            obs.confidence = 0.5

        return True, None

    @classmethod
    def validate_proposal(
        cls,
        proposal: EvolutionProposal,
        repo_root: Union[str, Path],
    ) -> Tuple[bool, Optional[str]]:
        """Validates an evolution proposal against immutable core and safety laws."""
        root = Path(os.path.normcase(os.path.abspath(repo_root)))
        target_clean = proposal.target_artifact.replace("\\", "/").strip("/")

        # 1. AntiOS Core Constitutional Immutability
        # Protected files cannot be targets of learning proposals
        core_immutable = [
            "antios_constitution.md",
            "antios_source_of_truth.md",
            "antios_v1.md",
            "framework",
            ".git",
        ]
        for zone in core_immutable:
            if target_clean.lower().startswith(zone):
                return (
                    False,
                    f"Constitutional Violation: Learning engine is strictly prohibited from mutating AntiOS Core ('{zone}'). "
                    "CORE != ADAPTER invariant enforced. Failing closed."
                )

        # 2. Prevent Specialist Self-Promotion / Delegation Escalation
        combined_text = f"{proposal.what_should_change} {proposal.why}".lower()
        if "can_delegate" in combined_text or "enable_subagent_tools" in combined_text or "depth" in combined_text:
            return (
                False,
                "Shallow Depth Law Violation: Learning engine cannot grant delegation authority to specialists. Failing closed."
            )

        # 3. Prevent Tool Authority Escalation
        if "mcp" in combined_text and ("grant" in combined_text or "enable" in combined_text or "bypass" in combined_text):
            return (
                False,
                "Authority Escalation Violation: Learning engine cannot escalate MCP or tool access policies. Failing closed."
            )

        # 4. Prevent Silent Mutation of Protected User-Owned Source
        if proposal.status == "APPLIED" and proposal.requires_human_approval:
            return (
                False,
                "Governance Violation: Proposals affecting project code require explicit human approval before being applied."
            )

        return True, None

    @classmethod
    def prevent_recursive_learning(
        cls,
        obs: Observation,
        current_mission_id: str,
        recent_observations: List[Observation],
    ) -> Tuple[bool, Optional[str]]:
        """Prevents recursive self-amplification loops where learning outputs feed back into themselves."""
        if obs.source.startswith("learning_engine") or obs.source.startswith("distiller"):
            # Check if this creates a self-referential cycle
            self_refs = [
                o for o in recent_observations
                if o.mission_id == current_mission_id and o.source == obs.source
            ]
            if len(self_refs) >= 3:
                return False, "Recursive learning cycle detected: Engine cannot reinforce its own synthetic outputs."
        return True, None


# -----------------------------------------------------------------------------
# Unified Facade: LearningEngine
# -----------------------------------------------------------------------------

class LearningEngine:
    """Unified Facade for AntiOS Project Learning & Safe Intelligence Evolution.
    
    Coordinates:
    - ObservationStore (.antios/learning_observations.json)
    - LessonDistiller (Distills candidate lessons)
    - EvidencePromotionEngine (Evaluates promotion ladder)
    - EvolutionProposalEngine (.antios/learning_proposals.json)
    - KnowledgeDecayEngine (Detects staleness and drift)
    - LearningSafetyGate (Fail-closed boundary enforcement)
    """

    VERSION = "2.0.0"

    def __init__(self, repo_root: Union[str, Path]):
        self.repo_root = Path(os.path.normcase(os.path.abspath(repo_root)))
        self.antios_dir = self.repo_root / ".antios"
        self.observations_file = self.antios_dir / "learning_observations.json"
        self.proposals_file = self.antios_dir / "learning_proposals.json"
        self.observation_store = ObservationStore.load_from_file(self.observations_file)

    def record_observation(self, obs: Observation) -> Tuple[bool, Observation, Optional[str]]:
        """Records a new engineering observation after safety validation."""
        # 1. Validate safety
        is_safe, reason = LearningSafetyGate.validate_observation(obs)
        if not is_safe:
            return False, obs, reason

        # 2. Check recursive loop
        recent = self.observation_store.list_all()[-10:]
        is_non_recursive, rec_reason = LearningSafetyGate.prevent_recursive_learning(obs, obs.mission_id, recent)
        if not is_non_recursive:
            return False, obs, rec_reason

        # 3. Add to store
        stored_obs, is_new = self.observation_store.add_observation(obs)
        self.observation_store.save_to_file(self.observations_file)
        return True, stored_obs, None

    def distill_and_promote(
        self,
        existing_lessons: Optional[List[CandidateLesson]] = None,
        verifications: Optional[List[VerificationVerdict]] = None,
    ) -> Tuple[List[CandidateLesson], List[EvolutionProposal], DecayReport]:
        """Runs the complete project learning lifecycle:
        1. Distills candidate lessons from active observations
        2. Evaluates evidence promotion for candidates
        3. Generates safe evolution proposals for validated/durable lessons
        4. Detects knowledge decay against disk reality
        """
        active_obs = self.observation_store.get_active()

        # 1. Distillation
        candidates = LessonDistiller.distill_from_observations(
            observations=active_obs,
            existing_candidates=existing_lessons or [],
        )

        # 2. Promotion
        proposals: List[EvolutionProposal] = self.load_proposals()
        for cand in candidates:
            if cand.authority in (KnowledgeAuthority.CANDIDATE, KnowledgeAuthority.VALIDATED):
                new_auth, reason, new_conf = EvidencePromotionEngine.evaluate_promotion(
                    candidate=cand,
                    observations=active_obs,
                    verifications=verifications,
                )
                if new_auth != cand.authority:
                    cand.authority = new_auth
                    cand.confidence = new_conf
                    cand.evidence = f"{cand.evidence}; {reason}".strip("; ")

                # 3. Generate proposals for promoted lessons
                if cand.authority in (KnowledgeAuthority.VALIDATED, KnowledgeAuthority.DURABLE):
                    existing_prop_ids = [p.lesson_id for p in proposals]
                    if cand.lesson_id not in existing_prop_ids:
                        new_prop = EvolutionProposalEngine.generate_proposal(cand, self.repo_root)
                        if new_prop:
                            proposals.append(new_prop)

        # Save proposals
        self.save_proposals(proposals)

        # 4. Decay Evaluation
        decay_report = KnowledgeDecayEngine.evaluate_decay(
            lessons=candidates,
            proposals=proposals,
            repo_root=self.repo_root,
        )

        return candidates, proposals, decay_report

    def load_proposals(self) -> List[EvolutionProposal]:
        if not self.proposals_file.is_file():
            return []
        try:
            data = json.loads(self.proposals_file.read_text(encoding="utf-8"))
            return [EvolutionProposal.from_dict(d) for d in data.get("proposals", [])]
        except Exception:
            return []

    def save_proposals(self, proposals: List[EvolutionProposal]) -> None:
        self.antios_dir.mkdir(parents=True, exist_ok=True)
        # Budget cap: max 20 proposals
        capped = proposals[-20:]
        data = {
            "schema_version": "2.0.0",
            "total_proposals": len(capped),
            "proposals": [p.to_dict() for p in capped],
        }
        self.proposals_file.write_text(json.dumps(data, indent=2), encoding="utf-8", newline="\n")
