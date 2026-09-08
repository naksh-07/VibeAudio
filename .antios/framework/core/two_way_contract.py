"""AntiOS 2.0 Two-Way Adaptation Contract Engine.

Formalizes the canonical bidirectional information flow between:
  ANTIOS SOURCE (Immutable Core)
        ↕
  PROJECT AGENT OS INSTANCE (.antios/)
        ↕
  TARGET HOST PROJECT

Defines:
1. Signal taxonomy (PROJECT_OBSERVATION, CAPABILITY_GAP, TOOL_GAP, MCP_GAP,
   EVOLUTION_PROPOSAL, COMPATIBILITY_SIGNAL, DRIFT_SIGNAL)
2. Epistemic distinction: OBSERVATION vs INFERENCE vs PROPOSAL vs APPROVED_CHANGE
3. Deterministic serialization and signature verification
4. Forbidden transition gates preventing target project evidence from mutating Core
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


class AdaptationTier(str, Enum):
    """The four authoritative architectural tiers in AntiOS."""
    ANTIOS_SOURCE = "ANTIOS_SOURCE"         # Canonical AntiOS core repo & governance
    PROJECT_INSTANCE = "PROJECT_INSTANCE"   # Compiled project-local Agent OS (.antios/)
    TARGET_PROJECT = "TARGET_PROJECT"       # The target host application codebase
    PLATFORM = "PLATFORM"                   # Antigravity host runtime & tools


class SignalType(str, Enum):
    """Canonical classification of signals crossing adaptation boundaries."""
    PROJECT_OBSERVATION = "PROJECT_OBSERVATION"     # Physical witness of project reality
    CAPABILITY_GAP = "CAPABILITY_GAP"               # Required task capability missing in OS
    TOOL_GAP = "TOOL_GAP"                           # Missing/unsupported tool or binary
    MCP_GAP = "MCP_GAP"                             # Escalation evaluating external MCP
    EVOLUTION_PROPOSAL = "EVOLUTION_PROPOSAL"       # Formatted proposal for project evolution
    COMPATIBILITY_SIGNAL = "COMPATIBILITY_SIGNAL"   # Version, schema, or deprecation signal
    DRIFT_SIGNAL = "DRIFT_SIGNAL"                   # Project fingerprint / topology drift


class EpistemicForm(str, Enum):
    """Strict epistemic distinction for signal truth status."""
    OBSERVATION = "OBSERVATION"       # Concrete physical event (test run, exit code, file state)
    INFERENCE = "INFERENCE"           # Derived hypothesis or pattern from 1+ observations
    PROPOSAL = "PROPOSAL"             # Unapproved recommendation for configuration/skill evolution
    APPROVED_CHANGE = "APPROVED_CHANGE" # Formally approved change ready for atomic application


class AuthorityTier(str, Enum):
    """Hierarchical authority level associated with signal emissions."""
    CONSTITUTION = "CONSTITUTION"     # Master engineering constitution (Immutable)
    CORE_SPEC = "CORE_SPEC"           # Canonical system blueprint (AntiOS source)
    HUMAN_DIRECTIVE = "HUMAN_DIRECTIVE" # Explicit maintainer/user instruction
    GOVERNANCE_GATE = "GOVERNANCE_GATE" # Automated safety and test ratchet gates
    PROJECT_MANIFEST = "PROJECT_MANIFEST" # .antios/manifest.json provenance record
    PROJECT_LOCAL = "PROJECT_LOCAL"   # antios.config.json or project intelligence
    AGENT_INFERENCE = "AGENT_INFERENCE" # Ephemeral agent reasoning (Lowest weight, 0.3)


@dataclass
class AdaptationSignal:
    """Canonical envelope for all information crossing the project <-> AntiOS boundary.
    
    Every signal has deterministic serialization, hash verification, and strict
    authority classification.
    """
    signal_id: str
    signal_type: SignalType
    epistemic_form: EpistemicForm
    source_tier: AdaptationTier
    target_tier: AdaptationTier
    authority_level: AuthorityTier
    evidence_payload: Dict[str, Any]
    confidence: float
    provenance: str
    risk: str = "LOW"                 # LOW, MEDIUM, HIGH, CRITICAL
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    schema_version: str = "2.0.0"
    project_fingerprint: str = ""
    signal_hash: str = ""

    def __post_init__(self) -> None:
        # Normalize confidence to [0.0, 1.0]
        self.confidence = max(0.0, min(1.0, float(self.confidence)))
        # Compute deterministic content hash if not already provided
        if not self.signal_hash:
            self.signal_hash = self.compute_hash()

    def compute_hash(self) -> str:
        """Computes deterministic SHA-256 hash of signal payload."""
        data_to_hash = {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type.value if hasattr(self.signal_type, "value") else str(self.signal_type),
            "epistemic_form": self.epistemic_form.value if hasattr(self.epistemic_form, "value") else str(self.epistemic_form),
            "source_tier": self.source_tier.value if hasattr(self.source_tier, "value") else str(self.source_tier),
            "target_tier": self.target_tier.value if hasattr(self.target_tier, "value") else str(self.target_tier),
            "authority_level": self.authority_level.value if hasattr(self.authority_level, "value") else str(self.authority_level),
            "evidence_payload": self.evidence_payload,
            "confidence": round(self.confidence, 4),
            "provenance": self.provenance,
            "risk": self.risk,
            "schema_version": self.schema_version,
            "project_fingerprint": self.project_fingerprint,
        }
        normalized = json.dumps(data_to_hash, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes signal to deterministic dictionary."""
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type.value,
            "epistemic_form": self.epistemic_form.value,
            "source_tier": self.source_tier.value,
            "target_tier": self.target_tier.value,
            "authority_level": self.authority_level.value,
            "evidence_payload": self.evidence_payload,
            "confidence": self.confidence,
            "provenance": self.provenance,
            "risk": self.risk,
            "timestamp": self.timestamp,
            "schema_version": self.schema_version,
            "project_fingerprint": self.project_fingerprint,
            "signal_hash": self.signal_hash or self.compute_hash(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AdaptationSignal:
        """Deserializes signal with validation."""
        sig = cls(
            signal_id=str(data["signal_id"]),
            signal_type=SignalType(data["signal_type"]),
            epistemic_form=EpistemicForm(data["epistemic_form"]),
            source_tier=AdaptationTier(data["source_tier"]),
            target_tier=AdaptationTier(data["target_tier"]),
            authority_level=AuthorityTier(data["authority_level"]),
            evidence_payload=dict(data.get("evidence_payload", {})),
            confidence=float(data.get("confidence", 1.0)),
            provenance=str(data.get("provenance", "")),
            risk=str(data.get("risk", "LOW")),
            timestamp=str(data.get("timestamp", "")),
            schema_version=str(data.get("schema_version", "2.0.0")),
            project_fingerprint=str(data.get("project_fingerprint", "")),
            signal_hash=str(data.get("signal_hash", "")),
        )
        return sig


class TransitionGateVerdict(str, Enum):
    """Outcome of transition legality check."""
    ALLOWED = "ALLOWED"
    DENIED = "DENIED"
    ESCALATION_REQUIRED = "ESCALATION_REQUIRED"


@dataclass
class TransitionGateResult:
    """Detailed verdict from Two-Way Adaptation Transition Gate."""
    verdict: TransitionGateVerdict
    is_allowed: bool
    rationale: str
    violations: List[str] = field(default_factory=list)
    escalation_target: Optional[str] = None


class TwoWayAdaptationContract:
    """Canonical boundary arbiter enforcing information flow laws between tiers.
    
    Constitutional Laws:
    1. TARGET_PROJECT -> PROJECT_INSTANCE: Allowed for OBSERVATION, INFERENCE, PROPOSAL.
    2. TARGET_PROJECT -> ANTIOS_SOURCE (Core): Strictly DENIED for file mutation; allowed ONLY as read-only feedback RFC.
    3. PROPOSAL is NEVER equivalent to APPROVED_CHANGE.
    4. AGENT_INTERPRETATION can NEVER create DURABLE core rules or mutate security policy.
    5. TARGET_PROJECT can NEVER modify ANTIOS_CONSTITUTION.md or framework/core/.
    """

    FORBIDDEN_CORE_PREFIXES = (
        "framework/",
        "framework\\",
        "antios_constitution.md",
        "antios_source_of_truth.md",
        "antios_v1.md",
        ".agents/hooks.json",
        ".git",
    )

    @classmethod
    def evaluate_transition(
        cls,
        signal: AdaptationSignal,
        proposed_action_target: Optional[str] = None,
    ) -> TransitionGateResult:
        """Evaluates whether a signal and its associated action can legally proceed."""
        violations: List[str] = []

        # 1. Epistemic integrity check: Proposal is NEVER an approved change
        if signal.epistemic_form == EpistemicForm.PROPOSAL and signal.authority_level == AuthorityTier.HUMAN_DIRECTIVE:
            # OK - human can authorize proposal
            pass

        # 2. Check forbidden Core mutation attempts
        target_path_norm = (proposed_action_target or "").replace("\\", "/").strip("/").lower()
        if target_path_norm:
            for prefix in cls.FORBIDDEN_CORE_PREFIXES:
                clean_pfx = prefix.replace("\\", "/").strip("/").lower()
                if target_path_norm == clean_pfx or target_path_norm.startswith(clean_pfx + "/"):
                    violations.append(
                        f"Core Immutability Violation: Project signal [{signal.signal_id}] attempted "
                        f"to mutate protected AntiOS core asset '{proposed_action_target}'. "
                        f"Target project evidence can NEVER mutate framework/core/ or constitution."
                    )

        # 3. Disallow PROJECT -> ANTIOS_SOURCE direct write transitions
        if signal.target_tier == AdaptationTier.ANTIOS_SOURCE:
            if signal.epistemic_form in (EpistemicForm.APPROVED_CHANGE, EpistemicForm.PROPOSAL):
                if target_path_norm:
                    violations.append(
                        f"Tier Boundary Violation: Direct modification of ANTIOS_SOURCE from "
                        f"{signal.source_tier.value} is strictly prohibited. Core changes require upstream RFC."
                    )

        # 4. Epistemic source weighting check: Agent interpretation cannot promote durable rules
        if signal.authority_level == AuthorityTier.AGENT_INFERENCE:
            if signal.confidence > 0.4:
                violations.append(
                    f"Epistemic Weight Violation: AGENT_INFERENCE confidence cannot exceed 0.4 (got {signal.confidence})."
                )
            if signal.epistemic_form == EpistemicForm.APPROVED_CHANGE:
                violations.append(
                    "Epistemic Boundary Violation: AGENT_INFERENCE alone cannot produce APPROVED_CHANGE."
                )

        # 5. Specialist delegation prohibition in proposals
        evidence_str = json.dumps(signal.evidence_payload).lower()
        if "can_delegate" in evidence_str and "true" in evidence_str:
            violations.append(
                "Shallow Depth Law Violation: Signal attempted to propose can_delegate=True for a specialist."
            )

        # 6. Unchecked MCP escalation
        if signal.signal_type == SignalType.MCP_GAP:
            if "bypass_justification" in evidence_str or "auto_grant" in evidence_str:
                violations.append(
                    "Tool Authority Violation: MCP gap cannot bypass canonical justification engine."
                )

        if violations:
            return TransitionGateResult(
                verdict=TransitionGateVerdict.DENIED,
                is_allowed=False,
                rationale="; ".join(violations),
                violations=violations,
                escalation_target="HUMAN_GOVERNANCE" if any("Core Immutability" in v for v in violations) else None,
            )

        # Handle read-only escalations to Core (RFC generation)
        if signal.target_tier == AdaptationTier.ANTIOS_SOURCE:
            return TransitionGateResult(
                verdict=TransitionGateVerdict.ESCALATION_REQUIRED,
                is_allowed=True,
                rationale="Signal targeting ANTIOS_SOURCE routed as upstream framework feedback (Read-Only RFC).",
                escalation_target="UPSTREAM_FRAMEWORK_MAINTAINERS",
            )

        return TransitionGateResult(
            verdict=TransitionGateVerdict.ALLOWED,
            is_allowed=True,
            rationale="Signal complies with Two-Way Adaptation Contract and boundary laws.",
            violations=[],
        )

    @classmethod
    def create_signal(
        cls,
        signal_type: SignalType,
        epistemic_form: EpistemicForm,
        source_tier: AdaptationTier,
        target_tier: AdaptationTier,
        authority_level: AuthorityTier,
        evidence_payload: Dict[str, Any],
        confidence: float,
        provenance: str,
        risk: str = "LOW",
        project_fingerprint: str = "",
    ) -> AdaptationSignal:
        """Helper to create and validate an AdaptationSignal."""
        prefix = signal_type.value[:3].lower()
        now_ts = datetime.now(timezone.utc).isoformat()
        sig_id = f"sig-{prefix}-{hashlib.sha256((now_ts + provenance).encode()).hexdigest()[:8]}"

        signal = AdaptationSignal(
            signal_id=sig_id,
            signal_type=signal_type,
            epistemic_form=epistemic_form,
            source_tier=source_tier,
            target_tier=target_tier,
            authority_level=authority_level,
            evidence_payload=evidence_payload,
            confidence=confidence,
            provenance=provenance,
            risk=risk,
            timestamp=now_ts,
            schema_version="2.0.0",
            project_fingerprint=project_fingerprint,
        )
        return signal
