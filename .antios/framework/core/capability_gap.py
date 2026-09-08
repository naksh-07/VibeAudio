"""AntiOS 2.0 Capability Gap Detection Engine.

Detects, classifies, and manages genuine engineering capability gaps while
rigorously distinguishing them from ordinary implementation failures,
verification failures, missing knowledge, stale intelligence, and wrong routing.

Enforces:
1. Strict failure taxonomy segregation
2. Bounded task signature deduplication
3. Lifecycle state machine: DETECTED -> VALIDATING -> CONFIRMED -> PROPOSED -> RESOLVED -> REJECTED -> STALE
4. Integration with CapabilityRegistry and ObservationStore
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from framework.core.capability import CapabilityScope, CapabilityType
from framework.core.two_way_contract import AdaptationSignal, AdaptationTier, EpistemicForm, SignalType, TwoWayAdaptationContract


class GapClassification(str, Enum):
    """Rigorous classification of task deficits and failures."""
    MISSING_CAPABILITY = "MISSING_CAPABILITY"             # Genuine gap: OS lacks required capability
    MISSING_KNOWLEDGE = "MISSING_KNOWLEDGE"               # Code/docs exist on disk but unindexed
    STALE_INTELLIGENCE = "STALE_INTELLIGENCE"             # .antios/ intelligence out of sync with disk
    WRONG_ROUTING = "WRONG_ROUTING"                       # Task classifier sent task to wrong role/skill
    UNAVAILABLE_TOOL = "UNAVAILABLE_TOOL"                 # Tool is configured but binary missing in host PATH
    UNAUTHORIZED_TOOL = "UNAUTHORIZED_TOOL"               # Tool exists but rejected by security policy
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"       # Vague agent claim lacking physical witness
    ORDINARY_IMPLEMENTATION_FAILURE = "ORDINARY_IMPLEMENTATION_FAILURE" # Normal coding/syntax error by agent
    VERIFICATION_FAILURE = "VERIFICATION_FAILURE"         # Test caught a real defect (system working as intended)


class GapStatus(str, Enum):
    """Lifecycle states of a detected capability gap."""
    DETECTED = "DETECTED"         # Initial signal recorded
    VALIDATING = "VALIDATING"     # Cross-checking against repository reality & tools
    CONFIRMED = "CONFIRMED"       # Empirical evidence confirmed genuine gap
    PROPOSED = "PROPOSED"         # Evolution proposal emitted for this gap
    RESOLVED = "RESOLVED"         # Remediated via skill/adapter update
    REJECTED = "REJECTED"         # Falsified or classified as ordinary implementation failure
    STALE = "STALE"               # Project context changed, rendering gap obsolete


@dataclass
class CapabilityGap:
    """Canonical record of a genuine project capability deficit."""
    gap_id: str
    task_signature: str
    required_capability: str
    current_capabilities: List[str]
    evidence: Dict[str, Any]
    confidence: float
    affected_subsystem: str
    risk: str = "MEDIUM"          # LOW, MEDIUM, HIGH, CRITICAL
    recommended_next_analysis: str = ""
    status: GapStatus = GapStatus.DETECTED
    classification: GapClassification = GapClassification.MISSING_CAPABILITY
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None
    recurrence_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic dictionary serialization."""
        return {
            "gap_id": self.gap_id,
            "task_signature": self.task_signature,
            "required_capability": self.required_capability,
            "current_capabilities": list(self.current_capabilities),
            "evidence": self.evidence,
            "confidence": round(self.confidence, 4),
            "affected_subsystem": self.affected_subsystem,
            "risk": self.risk,
            "recommended_next_analysis": self.recommended_next_analysis,
            "status": self.status.value,
            "classification": self.classification.value,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "recurrence_count": self.recurrence_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CapabilityGap:
        """Deserializes CapabilityGap from dictionary."""
        return cls(
            gap_id=str(data["gap_id"]),
            task_signature=str(data["task_signature"]),
            required_capability=str(data["required_capability"]),
            current_capabilities=list(data.get("current_capabilities", [])),
            evidence=dict(data.get("evidence", {})),
            confidence=float(data.get("confidence", 1.0)),
            affected_subsystem=str(data.get("affected_subsystem", "core")),
            risk=str(data.get("risk", "MEDIUM")),
            recommended_next_analysis=str(data.get("recommended_next_analysis", "")),
            status=GapStatus(data.get("status", "DETECTED")),
            classification=GapClassification(data.get("classification", "MISSING_CAPABILITY")),
            created_at=str(data.get("created_at", "")),
            resolved_at=data.get("resolved_at"),
            recurrence_count=int(data.get("recurrence_count", 1)),
            metadata=dict(data.get("metadata", {})),
        )


class CapabilityGapDetector:
    """Deterministic capability-gap detection and triage engine.
    
    Evaluates execution failures, router unknowns, and tool deficits to separate
    genuine capability gaps from normal developer/agent errors.
    """

    @staticmethod
    def compute_task_signature(task_intent: str, subsystem: str, target_files: Optional[List[str]] = None) -> str:
        """Computes deterministic normalized hash signature for a task signature."""
        clean_intent = re.sub(r"[^a-zA-Z0-9_]", " ", (task_intent or "").lower()).split()
        sorted_tokens = sorted(list(set(clean_intent)))
        norm_files = sorted([f.replace("\\", "/").strip("/") for f in (target_files or [])])
        raw_repr = f"{subsystem.lower()}:{'-'.join(sorted_tokens[:8])}:{','.join(norm_files[:4])}"
        return hashlib.sha256(raw_repr.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def classify_deficit(
        cls,
        task_intent: str,
        failure_evidence: Dict[str, Any],
        available_capabilities: List[str],
        available_tools: List[str],
        is_syntax_or_unit_test_failure: bool = False,
        is_binary_missing: bool = False,
        is_policy_denied: bool = False,
        is_knowledge_unindexed: bool = False,
        is_intelligence_stale: bool = False,
        is_routing_mismatch: bool = False,
    ) -> Tuple[GapClassification, str]:
        """Deterministically classifies whether a task issue is a genuine capability gap."""
        # 1. Ordinary syntax / implementation failure
        if is_syntax_or_unit_test_failure:
            # Check if this was simply a failing test assertion or Python syntax error
            error_msg = str(failure_evidence.get("error", "")).lower()
            if any(w in error_msg for w in ["syntaxerror", "indentationerror", "assertionerror", "indexerror", "keyerror"]):
                return (
                    GapClassification.ORDINARY_IMPLEMENTATION_FAILURE,
                    "Ordinary implementation failure: agent code or patch contained syntax/logical defect."
                )
            if failure_evidence.get("exit_code") not in (None, 0):
                return (
                    GapClassification.VERIFICATION_FAILURE,
                    "Verification failure: existing test suite caught code regression (ratchet functioning properly)."
                )

        # 2. Host environment binary missing
        if is_binary_missing:
            return (
                GapClassification.UNAVAILABLE_TOOL,
                "Tool unavailable: configured runner or tool is missing from host PATH."
            )

        # 3. Policy denial
        if is_policy_denied:
            return (
                GapClassification.UNAUTHORIZED_TOOL,
                "Unauthorized tool: tool invocation was intentionally blocked by security boundary policy."
            )

        # 4. Stale intelligence
        if is_intelligence_stale:
            return (
                GapClassification.STALE_INTELLIGENCE,
                "Stale intelligence: target repository has changed, requiring intelligence re-adaptation."
            )

        # 5. Missing knowledge (unindexed files)
        if is_knowledge_unindexed:
            return (
                GapClassification.MISSING_KNOWLEDGE,
                "Missing knowledge: project possesses the relevant code/docs, but wayfinding index needs updating."
            )

        # 6. Wrong routing
        if is_routing_mismatch:
            return (
                GapClassification.WRONG_ROUTING,
                "Wrong routing: task was assigned to an incompatible agent role or specialist."
            )

        # 7. Check evidence substantiation
        if not failure_evidence or failure_evidence.get("unsubstantiated", False):
            return (
                GapClassification.INSUFFICIENT_EVIDENCE,
                "Insufficient evidence: failure claim lacks physical witness or reproducible command trace."
            )

        # 8. Genuine capability gap
        return (
            GapClassification.MISSING_CAPABILITY,
            "Genuine capability gap: project task demands a skill, tool, or verifier absent in Project Agent OS."
        )

    @classmethod
    def create_gap(
        cls,
        task_intent: str,
        subsystem: str,
        required_capability: str,
        current_capabilities: List[str],
        failure_evidence: Dict[str, Any],
        confidence: float = 1.0,
        risk: str = "MEDIUM",
        target_files: Optional[List[str]] = None,
        recommended_analysis: str = "",
        classification: GapClassification = GapClassification.MISSING_CAPABILITY,
    ) -> CapabilityGap:
        """Creates a structured CapabilityGap."""
        sig = cls.compute_task_signature(task_intent, subsystem, target_files)
        gap_id = f"gap-{subsystem.lower()[:4]}-{sig[:8]}"

        gap = CapabilityGap(
            gap_id=gap_id,
            task_signature=sig,
            required_capability=required_capability,
            current_capabilities=current_capabilities,
            evidence=failure_evidence,
            confidence=confidence,
            affected_subsystem=subsystem,
            risk=risk,
            recommended_next_analysis=recommended_analysis or f"Evaluate tool and skill alternatives for {required_capability}",
            status=GapStatus.DETECTED,
            classification=classification,
        )
        return gap


class GapLifecycleEngine:
    """Manages progression of capability gaps through formal validation states."""

    LEGAL_TRANSITIONS = {
        GapStatus.DETECTED: {GapStatus.VALIDATING, GapStatus.REJECTED},
        GapStatus.VALIDATING: {GapStatus.CONFIRMED, GapStatus.REJECTED, GapStatus.STALE},
        GapStatus.CONFIRMED: {GapStatus.PROPOSED, GapStatus.REJECTED, GapStatus.STALE},
        GapStatus.PROPOSED: {GapStatus.RESOLVED, GapStatus.REJECTED, GapStatus.STALE},
        GapStatus.RESOLVED: set(),  # Terminal state
        GapStatus.REJECTED: set(),  # Terminal state
        GapStatus.STALE: {GapStatus.VALIDATING}, # Can re-evaluate if project context reappears
    }

    def __init__(self) -> None:
        self._gaps: Dict[str, CapabilityGap] = {}

    def register_gap(self, gap: CapabilityGap) -> CapabilityGap:
        """Registers a gap or increments recurrence if duplicate signature exists."""
        for existing in self._gaps.values():
            if existing.task_signature == gap.task_signature and existing.required_capability == gap.required_capability:
                existing.recurrence_count += 1
                existing.confidence = min(1.0, existing.confidence + 0.1)
                existing.evidence.update(gap.evidence)
                return existing

        self._gaps[gap.gap_id] = gap
        return gap

    def transition_gap(
        self,
        gap_id: str,
        target_status: GapStatus,
        reason: str = "",
    ) -> Tuple[bool, str, Optional[CapabilityGap]]:
        """Safely transitions a gap through its lifecycle."""
        if gap_id not in self._gaps:
            return False, f"Gap '{gap_id}' not found in registry.", None

        gap = self._gaps[gap_id]
        allowed = self.LEGAL_TRANSITIONS.get(gap.status, set())
        if target_status not in allowed:
            return False, f"Illegal transition from {gap.status.value} to {target_status.value}.", gap

        gap.status = target_status
        gap.metadata[f"transition_to_{target_status.value.lower()}_at"] = datetime.now(timezone.utc).isoformat()
        if reason:
            gap.metadata[f"transition_to_{target_status.value.lower()}_reason"] = reason

        if target_status == GapStatus.RESOLVED:
            gap.resolved_at = datetime.now(timezone.utc).isoformat()

        return True, f"Transitioned gap '{gap_id}' to {target_status.value}.", gap

    def list_gaps(self, status: Optional[GapStatus] = None) -> List[CapabilityGap]:
        """Lists registered gaps with optional status filtering."""
        if status:
            return [g for g in self._gaps.values() if g.status == status]
        return list(self._gaps.values())

    def get_gap(self, gap_id: str) -> Optional[CapabilityGap]:
        return self._gaps.get(gap_id)
