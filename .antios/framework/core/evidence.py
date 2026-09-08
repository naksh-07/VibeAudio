"""AntiOS 2.0 Evidence Architecture (Phase 90).

Foundational epistemic model, evidence packaging, and provenance enforcement:
- Epistemic Category segregation: OBSERVATION != EVIDENCE != VERDICT != INFERENCE != DECISION
- 6 Evidence states: OBSERVED, VERIFIED, INVALIDATED, SUPERSEDED, MISSING, CONFLICTING
- Deterministic EvidenceItem and ArtifactFingerprint
- Deterministic, bounded EvidencePackage container (<= 50 artifacts, <= 100 evidence items)
- ToolOutputClassifier integration for bounding oversized outputs with SHA-256
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from framework.core.mission_state import ToolOutputClassifier, ToolOutputEvidence


class EpistemicCategory(str, Enum):
    """Rigorous epistemic category segregation.
    
    Axiom: OBSERVATION != EVIDENCE != VERDICT != INFERENCE != DECISION.
    An agent's assertion that a task succeeded must NEVER be classified as EVIDENCE.
    """
    OBSERVATION = "OBSERVATION"  # Raw perception of reality (process output, tool read, exit code emitted)
    EVIDENCE = "EVIDENCE"        # Corroborated physical ground truth tied directly to an acceptance criterion
    VERDICT = "VERDICT"          # Formal evaluation emitted by an independent evaluator or gate
    INFERENCE = "INFERENCE"      # Deductive or inductive hypothesis synthesized by an agent
    DECISION = "DECISION"        # Explicit operational commitment to an action, architecture, or policy


class EvidenceState(str, Enum):
    """The 6 canonical evidence lifecycle states in AntiOS."""
    OBSERVED = "OBSERVED"        # Raw proof recorded, pending criteria evaluation
    VERIFIED = "VERIFIED"        # Proven valid, meeting criteria on the final unmodified working tree
    INVALIDATED = "INVALIDATED"  # Falsified by test failure, regression, or working tree drift
    SUPERSEDED = "SUPERSEDED"    # Replaced by more authoritative evidence from a subsequent wave
    MISSING = "MISSING"          # Required by an acceptance criterion or invariant, but physical proof is absent
    CONFLICTING = "CONFLICTING"  # Contradictory evidence exists between tools, verifiers, or runs


@dataclass
class ArtifactFingerprint:
    """Cryptographic tracking of a changed physical repository artifact."""
    path: str
    sha256_before: str = ""
    sha256_after: str = ""
    byte_size: int = 0
    ownership_tier: str = "PROJECT_LOCAL"
    is_substantive: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_modified(self) -> bool:
        """Determines if the artifact underwent substantive content alteration."""
        if not self.sha256_before and self.sha256_after:
            return True  # Created
        if self.sha256_before and not self.sha256_after:
            return True  # Deleted
        return self.sha256_before != self.sha256_after

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "sha256_before": self.sha256_before,
            "sha256_after": self.sha256_after,
            "byte_size": self.byte_size,
            "ownership_tier": self.ownership_tier,
            "is_substantive": self.is_substantive,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ArtifactFingerprint:
        return cls(
            path=str(data.get("path", "")),
            sha256_before=str(data.get("sha256_before", "")),
            sha256_after=str(data.get("sha256_after", "")),
            byte_size=int(data.get("byte_size", 0)),
            ownership_tier=str(data.get("ownership_tier", "PROJECT_LOCAL")),
            is_substantive=bool(data.get("is_substantive", True)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class EvidenceItem:
    """Canonical, bounded evidence representation with enforced provenance.
    
    Invariants:
    - Must possess non-empty provenance.
    - An agent's assertion of success CANNOT be created with category EVIDENCE.
    - Large tool outputs (>2000 chars) are stored as bounded excerpts + SHA-256.
    """
    evidence_id: str
    mission_id: str
    intent: str
    provenance: str
    epistemic_category: EpistemicCategory = EpistemicCategory.EVIDENCE
    state: EvidenceState = EvidenceState.OBSERVED
    acceptance_criteria_keys: List[str] = field(default_factory=list)
    workstream_id: Optional[str] = None
    source_fingerprint: str = ""
    worker_identity: Optional[str] = None
    worker_role: Optional[str] = None
    capability_used: Optional[str] = None
    workforce_wave: int = 1
    context_provenance: Optional[str] = None
    freshness_state: str = "FRESH"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    commands_executed: List[str] = field(default_factory=list)
    command_exit_codes: Dict[str, int] = field(default_factory=dict)
    test_results: List[Dict[str, Any]] = field(default_factory=list)
    verification_verdicts: List[Dict[str, Any]] = field(default_factory=list)
    invariant_checks: List[Dict[str, Any]] = field(default_factory=list)
    decision_refs: List[str] = field(default_factory=list)
    recovery_events: List[str] = field(default_factory=list)
    reviewer_verifier_identity: Optional[str] = None
    confidence: float = 1.0
    payload: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Enforce non-empty provenance
        if not self.provenance or not self.provenance.strip():
            raise ValueError("EvidenceItem rejected: provenance is required and cannot be empty.")

        # Enforce Epistemic Separation Law:
        # Agent assertions cannot pose as physical EVIDENCE without physical backing.
        if (
            self.epistemic_category == EpistemicCategory.EVIDENCE
            and self.worker_identity
            and not (
                self.commands_executed
                or self.test_results
                or self.verification_verdicts
                or self.invariant_checks
                or self.payload.get("artifact_hashes")
            )
        ):
            raise ValueError(
                f"Epistemic Separation Violation: Agent assertion from '{self.worker_identity}' "
                f"cannot be registered as EVIDENCE without physical verification artifacts."
            )

        # Ensure bounded string lengths
        if len(self.intent) > 500:
            self.intent = self.intent[:497] + "..."
        if len(self.provenance) > 200:
            self.provenance = self.provenance[:197] + "..."

        # Bounded lists
        if len(self.acceptance_criteria_keys) > 20:
            self.acceptance_criteria_keys = self.acceptance_criteria_keys[:20]
        if len(self.commands_executed) > 20:
            self.commands_executed = self.commands_executed[:20]
        if len(self.test_results) > 50:
            self.test_results = self.test_results[:50]
        if len(self.invariant_checks) > 20:
            self.invariant_checks = self.invariant_checks[:20]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "mission_id": self.mission_id,
            "intent": self.intent,
            "provenance": self.provenance,
            "epistemic_category": self.epistemic_category.value,
            "state": self.state.value,
            "acceptance_criteria_keys": list(self.acceptance_criteria_keys),
            "workstream_id": self.workstream_id,
            "source_fingerprint": self.source_fingerprint,
            "worker_identity": self.worker_identity,
            "worker_role": self.worker_role,
            "capability_used": self.capability_used,
            "workforce_wave": self.workforce_wave,
            "context_provenance": self.context_provenance,
            "freshness_state": self.freshness_state,
            "timestamp": self.timestamp,
            "commands_executed": list(self.commands_executed),
            "command_exit_codes": dict(self.command_exit_codes),
            "test_results": [dict(t) for t in self.test_results],
            "verification_verdicts": [dict(v) for v in self.verification_verdicts],
            "invariant_checks": [dict(i) for i in self.invariant_checks],
            "decision_refs": list(self.decision_refs),
            "recovery_events": list(self.recovery_events),
            "reviewer_verifier_identity": self.reviewer_verifier_identity,
            "confidence": float(self.confidence),
            "payload": dict(self.payload),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvidenceItem:
        cat_str = str(data.get("epistemic_category", EpistemicCategory.EVIDENCE.value))
        try:
            cat = EpistemicCategory(cat_str)
        except ValueError:
            cat = EpistemicCategory.EVIDENCE

        st_str = str(data.get("state", EvidenceState.OBSERVED.value))
        try:
            st = EvidenceState(st_str)
        except ValueError:
            st = EvidenceState.OBSERVED

        return cls(
            evidence_id=str(data.get("evidence_id", "")),
            mission_id=str(data.get("mission_id", "")),
            intent=str(data.get("intent", "")),
            provenance=str(data.get("provenance", "")),
            epistemic_category=cat,
            state=st,
            acceptance_criteria_keys=list(data.get("acceptance_criteria_keys", [])),
            workstream_id=data.get("workstream_id"),
            source_fingerprint=str(data.get("source_fingerprint", "")),
            worker_identity=data.get("worker_identity"),
            worker_role=data.get("worker_role"),
            capability_used=data.get("capability_used"),
            workforce_wave=int(data.get("workforce_wave", 1)),
            context_provenance=data.get("context_provenance"),
            freshness_state=str(data.get("freshness_state", "FRESH")),
            timestamp=str(data.get("timestamp", datetime.now(timezone.utc).isoformat())),
            commands_executed=list(data.get("commands_executed", [])),
            command_exit_codes={k: int(v) for k, v in data.get("command_exit_codes", {}).items()},
            test_results=list(data.get("test_results", [])),
            verification_verdicts=list(data.get("verification_verdicts", [])),
            invariant_checks=list(data.get("invariant_checks", [])),
            decision_refs=list(data.get("decision_refs", [])),
            recovery_events=list(data.get("recovery_events", [])),
            reviewer_verifier_identity=data.get("reviewer_verifier_identity"),
            confidence=float(data.get("confidence", 1.0)),
            payload=dict(data.get("payload", {})),
        )


@dataclass
class EvidencePackage:
    """Deterministic, bounded evidence package produced by a completed mission.
    
    Contains:
    1. Mission identity
    2. Intent
    3. Acceptance criteria
    4. Files/artifacts changed
    5. Artifact fingerprints
    6. Commands/tests executed
    7. Verification results
    8. Invariant checks
    9. Workforce summary
    10. Context summary
    11. Recovery events if any
    12. Final verdict
    13. Evidence provenance
    14. Any unresolved uncertainty
    
    Enforced bounds:
    - changed_artifacts: <= 50
    - evidence_items: <= 100
    - invariant_checks: <= 30
    - unresolved_uncertainty: <= 10
    """
    mission_id: str
    intent: str
    acceptance_criteria: List[str]
    package_id: str = field(default_factory=lambda: hashlib.sha256(os.urandom(16)).hexdigest()[:16])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    changed_artifacts: List[str] = field(default_factory=list)
    artifact_fingerprints: Dict[str, ArtifactFingerprint] = field(default_factory=dict)
    commands_executed: List[str] = field(default_factory=list)
    test_results: List[Dict[str, Any]] = field(default_factory=list)
    verification_verdicts: List[Dict[str, Any]] = field(default_factory=list)
    invariant_checks: List[Dict[str, Any]] = field(default_factory=list)
    workforce_summary: Dict[str, Any] = field(default_factory=dict)
    context_summary: Dict[str, Any] = field(default_factory=dict)
    recovery_events: List[str] = field(default_factory=list)
    final_verdict: str = "INCONCLUSIVE"
    evidence_items: List[EvidenceItem] = field(default_factory=list)
    evidence_provenance: str = "AntiOS Evidence Architecture v1"
    unresolved_uncertainty: List[str] = field(default_factory=list)
    project_fingerprint: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Enforce bounds
        if len(self.changed_artifacts) > 50:
            self.changed_artifacts = self.changed_artifacts[:50]
        if len(self.evidence_items) > 100:
            self.evidence_items = self.evidence_items[:100]
        if len(self.invariant_checks) > 30:
            self.invariant_checks = self.invariant_checks[:30]
        if len(self.unresolved_uncertainty) > 10:
            self.unresolved_uncertainty = self.unresolved_uncertainty[:10]

    def add_artifact(self, fingerprint: ArtifactFingerprint) -> None:
        """Adds or updates an artifact fingerprint with bounded list enforcement."""
        if fingerprint.path not in self.changed_artifacts:
            if len(self.changed_artifacts) < 50:
                self.changed_artifacts.append(fingerprint.path)
        self.artifact_fingerprints[fingerprint.path] = fingerprint

    def add_evidence_item(self, item: EvidenceItem) -> None:
        """Appends an evidence item respecting the 100-item cap."""
        if len(self.evidence_items) < 100:
            self.evidence_items.append(item)

    def record_command(self, cmd: str, exit_code: int, stdout_stderr: str = "") -> ToolOutputEvidence:
        """Executes bounding on command output via ToolOutputClassifier and records evidence."""
        classified = ToolOutputClassifier.process_output(
            tool_name="run_command",
            command_or_path=cmd,
            stdout=stdout_stderr,
            exit_code=exit_code,
        )
        if cmd not in self.commands_executed and len(self.commands_executed) < 50:
            self.commands_executed.append(cmd)
        return classified

    def record_invariant(self, name: str, passed: bool, details: str = "") -> None:
        """Records an invariant check."""
        if len(self.invariant_checks) < 30:
            self.invariant_checks.append({
                "name": name,
                "passed": passed,
                "details": details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    def get_items_by_state(self, state: EvidenceState) -> List[EvidenceItem]:
        """Filters evidence items by lifecycle state."""
        return [it for it in self.evidence_items if it.state == state]

    def has_conflicting_evidence(self) -> bool:
        """Returns True if any item has CONFLICTING state."""
        return any(it.state == EvidenceState.CONFLICTING for it in self.evidence_items)

    def compute_evidence_hash(self) -> str:
        """Computes a deterministic digest of all verified evidence items."""
        serialized = json.dumps(
            [it.to_dict() for it in sorted(self.evidence_items, key=lambda x: x.evidence_id)],
            sort_keys=True,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "package_id": self.package_id,
            "mission_id": self.mission_id,
            "intent": self.intent,
            "acceptance_criteria": list(self.acceptance_criteria),
            "timestamp": self.timestamp,
            "changed_artifacts": list(self.changed_artifacts),
            "artifact_fingerprints": {
                p: fp.to_dict() for p, fp in self.artifact_fingerprints.items()
            },
            "commands_executed": list(self.commands_executed),
            "test_results": [dict(t) for t in self.test_results],
            "verification_verdicts": [dict(v) for v in self.verification_verdicts],
            "invariant_checks": [dict(i) for i in self.invariant_checks],
            "workforce_summary": dict(self.workforce_summary),
            "context_summary": dict(self.context_summary),
            "recovery_events": list(self.recovery_events),
            "final_verdict": self.final_verdict,
            "evidence_items": [it.to_dict() for it in self.evidence_items],
            "evidence_provenance": self.evidence_provenance,
            "unresolved_uncertainty": list(self.unresolved_uncertainty),
            "project_fingerprint": self.project_fingerprint,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvidencePackage:
        fps = {}
        for p, fp_data in data.get("artifact_fingerprints", {}).items():
            fps[p] = ArtifactFingerprint.from_dict(fp_data)

        items = []
        for it_data in data.get("evidence_items", []):
            try:
                items.append(EvidenceItem.from_dict(it_data))
            except Exception:
                pass

        return cls(
            package_id=str(data.get("package_id", "")),
            mission_id=str(data.get("mission_id", "")),
            intent=str(data.get("intent", "")),
            acceptance_criteria=list(data.get("acceptance_criteria", [])),
            timestamp=str(data.get("timestamp", datetime.now(timezone.utc).isoformat())),
            changed_artifacts=list(data.get("changed_artifacts", [])),
            artifact_fingerprints=fps,
            commands_executed=list(data.get("commands_executed", [])),
            test_results=list(data.get("test_results", [])),
            verification_verdicts=list(data.get("verification_verdicts", [])),
            invariant_checks=list(data.get("invariant_checks", [])),
            workforce_summary=dict(data.get("workforce_summary", {})),
            context_summary=dict(data.get("context_summary", {})),
            recovery_events=list(data.get("recovery_events", [])),
            final_verdict=str(data.get("final_verdict", "INCONCLUSIVE")),
            evidence_items=items,
            evidence_provenance=str(data.get("evidence_provenance", "AntiOS Evidence Architecture v1")),
            unresolved_uncertainty=list(data.get("unresolved_uncertainty", [])),
            project_fingerprint=str(data.get("project_fingerprint", "")),
            metadata=dict(data.get("metadata", {})),
        )

    def save(self, file_path: str) -> None:
        """Persists the evidence package to an auditable JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, sort_keys=True)

    @classmethod
    def load(cls, file_path: str) -> EvidencePackage:
        """Loads and deserializes an evidence package from disk."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"EvidencePackage file not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


class EvidenceBuilder:
    """Convenience builder to safely construct deterministic EvidencePackages."""

    def __init__(
        self,
        mission_id: str,
        intent: str,
        acceptance_criteria: List[str],
        project_fingerprint: str = "",
        evidence_provenance: str = "AntiOS Evidence Builder v1",
    ):
        self.package = EvidencePackage(
            mission_id=mission_id,
            intent=intent,
            acceptance_criteria=acceptance_criteria,
            project_fingerprint=project_fingerprint,
            evidence_provenance=evidence_provenance,
        )

    def track_file_change(
        self,
        path: str,
        content_before: Optional[str] = None,
        content_after: Optional[str] = None,
        ownership_tier: str = "PROJECT_LOCAL",
    ) -> ArtifactFingerprint:
        """Computes SHA-256 for before and after states and registers with package."""
        sha_before = hashlib.sha256(content_before.encode("utf-8")).hexdigest() if content_before is not None else ""
        sha_after = hashlib.sha256(content_after.encode("utf-8")).hexdigest() if content_after is not None else ""
        size = len(content_after.encode("utf-8")) if content_after is not None else 0
        
        fp = ArtifactFingerprint(
            path=path,
            sha256_before=sha_before,
            sha256_after=sha_after,
            byte_size=size,
            ownership_tier=ownership_tier,
            is_substantive=(sha_before != sha_after),
        )
        self.package.add_artifact(fp)
        return fp

    def add_command_evidence(
        self,
        command: str,
        exit_code: int,
        stdout_stderr: str = "",
        provenance: str = "CLI execution",
        criteria_keys: Optional[List[str]] = None,
        worker_identity: Optional[str] = None,
    ) -> EvidenceItem:
        """Registers a deterministic command run as an EvidenceItem."""
        ev_output = self.package.record_command(command, exit_code, stdout_stderr)
        state = EvidenceState.VERIFIED if exit_code == 0 else EvidenceState.INVALIDATED
        
        item = EvidenceItem(
            evidence_id=f"cmd-{hashlib.sha256(command.encode()).hexdigest()[:10]}",
            mission_id=self.package.mission_id,
            intent=f"Execute: {command[:80]}",
            provenance=provenance,
            epistemic_category=EpistemicCategory.EVIDENCE,
            state=state,
            acceptance_criteria_keys=criteria_keys or [],
            worker_identity=worker_identity,
            commands_executed=[command],
            command_exit_codes={command: exit_code},
            payload={
                "classification": ev_output.classification.value,
                "compact_summary": ev_output.compact_summary,
                "raw_sha256": ev_output.raw_sha256,
            },
        )
        self.package.add_evidence_item(item)
        return item

    def build(self, final_verdict: str = "INCONCLUSIVE") -> EvidencePackage:
        """Finalizes and returns the package."""
        self.package.final_verdict = final_verdict
        return self.package
