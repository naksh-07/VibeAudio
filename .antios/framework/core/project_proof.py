"""AntiOS 2.0 Durable Project Proofs & Evidence Distillation (Phase 93).

Canonical project-level proof model, epistemic promotion rules, and physical grounding:
- Epistemic distillation axiom:
    MISSION EVIDENCE -> (validation) -> DURABLE PROJECT PROOF
    OBSERVATION      -X-> DURABLE PROJECT PROOF
    AGENT INFERENCE  -X-> DURABLE PROJECT PROOF
    UNVERIFIED CLAIM -X-> DURABLE PROJECT PROOF
- 13 canonical proof subjects (subsystems, file locations, architecture relations, invariants, etc.)
- 7 proof lifecycle states: CANDIDATE, VALIDATED, DURABLE, AGING, STALE, INVALIDATED, SUPERSEDED
- Physical grounding: tracked_paths and path_hashes bind proofs directly to on-disk reality
- Deterministic invalidation upon physical file modification, manifest drift, or contradictory evidence
- Bounded storage: MAX_DURABLE_PROOFS = 50, MAX_REFERENCES_PER_PROOF = 10
- Token-bounded ProjectProofCard (<= 25 lines)
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from framework.core.evidence import (
    ArtifactFingerprint,
    EpistemicCategory,
    EvidenceItem,
    EvidencePackage,
    EvidenceState,
)
from framework.core.mission_evaluation import EvaluationStatus, MissionEvaluationResult


# Canonical storage bounds
MAX_DURABLE_PROOFS = 50
MAX_REFERENCES_PER_PROOF = 10
MAX_TRACKED_PATHS_PER_PROOF = 10
MAX_STATEMENT_LENGTH = 300


class ProofSubject(str, Enum):
    """The 13 canonical project proof subject domains."""
    SUBSYSTEM_OWNERSHIP = "SUBSYSTEM_OWNERSHIP"
    VERIFIED_FILE_LOCATION = "VERIFIED_FILE_LOCATION"
    VALIDATED_ARCHITECTURE_RELATION = "VALIDATED_ARCHITECTURE_RELATION"
    CONFIRMED_TEST_OWNERSHIP = "CONFIRMED_TEST_OWNERSHIP"
    VERIFIED_COMMAND = "VERIFIED_COMMAND"
    VERIFIED_INVARIANT = "VERIFIED_INVARIANT"
    TOOL_CAPABILITY_MAPPING = "TOOL_CAPABILITY_MAPPING"
    REPOSITORY_CONVENTION = "REPOSITORY_CONVENTION"
    PROJECT_ADAPTER_ASSUMPTION = "PROJECT_ADAPTER_ASSUMPTION"
    RECURRING_FAILURE_SIGNATURE = "RECURRING_FAILURE_SIGNATURE"
    RECOVERY_PROCEDURE = "RECOVERY_PROCEDURE"
    DOCUMENTATION_OWNERSHIP = "DOCUMENTATION_OWNERSHIP"
    NAVIGATION_HINT = "NAVIGATION_HINT"


class ProofStatus(str, Enum):
    """The 7 canonical lifecycle states of a Project Proof."""
    CANDIDATE = "CANDIDATE"        # Initial extraction from mission evidence, awaiting promotion
    VALIDATED = "VALIDATED"        # Corroborated by independent verifier or passing mission
    DURABLE = "DURABLE"            # Established multi-run or constitutionally certified proof
    AGING = "AGING"                # Older proof nearing revalidation interval
    STALE = "STALE"                # Project context drifted; revalidation pending
    INVALIDATED = "INVALIDATED"    # Falsified by on-disk file change, test failure, or contradiction
    SUPERSEDED = "SUPERSEDED"      # Replaced by a more specific or newer authoritative proof


class RevalidationPolicy(str, Enum):
    """Trigger conditions for proof revalidation."""
    ON_FILE_CHANGE = "ON_FILE_CHANGE"              # Revalidate when any tracked path hash changes
    ON_MANIFEST_DRIFT = "ON_MANIFEST_DRIFT"        # Revalidate when project manifest changes
    ON_COMMIT_ADVANCE = "ON_COMMIT_ADVANCE"        # Revalidate when Git HEAD advances
    MANUAL = "MANUAL"                              # Revalidate only via explicit audit directive


@dataclass
class ProjectProof:
    """Canonical ProjectProof abstraction representing durable verified knowledge."""
    proof_id: str
    subject: ProofSubject
    statement: str
    origin_mission_id: str
    project_fingerprint: str
    evidence_references: List[Dict[str, Any]] = field(default_factory=list)
    validation_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: ProofStatus = ProofStatus.CANDIDATE
    owner: str = "AntiOS Proof Engine"
    revalidation_policy: RevalidationPolicy = RevalidationPolicy.ON_FILE_CHANGE
    tracked_paths: List[str] = field(default_factory=list)
    path_hashes: Dict[str, str] = field(default_factory=dict)
    superseded_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.proof_id or not self.proof_id.strip():
            raise ValueError("proof_id cannot be empty")
        if not self.statement or not self.statement.strip():
            raise ValueError("statement cannot be empty")
        if len(self.statement) > MAX_STATEMENT_LENGTH:
            self.statement = self.statement[:MAX_STATEMENT_LENGTH]
        if not self.origin_mission_id or not self.origin_mission_id.strip():
            raise ValueError("origin_mission_id cannot be empty")
        if not self.project_fingerprint or not self.project_fingerprint.strip():
            raise ValueError("project_fingerprint cannot be empty")
        if len(self.evidence_references) > MAX_REFERENCES_PER_PROOF:
            self.evidence_references = self.evidence_references[:MAX_REFERENCES_PER_PROOF]
        if len(self.tracked_paths) > MAX_TRACKED_PATHS_PER_PROOF:
            self.tracked_paths = self.tracked_paths[:MAX_TRACKED_PATHS_PER_PROOF]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "subject": self.subject.value,
            "statement": self.statement,
            "origin_mission_id": self.origin_mission_id,
            "project_fingerprint": self.project_fingerprint,
            "evidence_references": list(self.evidence_references),
            "validation_timestamp": self.validation_timestamp,
            "status": self.status.value,
            "owner": self.owner,
            "revalidation_policy": self.revalidation_policy.value,
            "tracked_paths": list(self.tracked_paths),
            "path_hashes": dict(self.path_hashes),
            "superseded_by": self.superseded_by,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProjectProof:
        return cls(
            proof_id=data["proof_id"],
            subject=ProofSubject(data["subject"]),
            statement=data["statement"],
            origin_mission_id=data["origin_mission_id"],
            project_fingerprint=data["project_fingerprint"],
            evidence_references=data.get("evidence_references", []),
            validation_timestamp=data.get("validation_timestamp", ""),
            status=ProofStatus(data.get("status", ProofStatus.CANDIDATE.value)),
            owner=data.get("owner", "AntiOS Proof Engine"),
            revalidation_policy=RevalidationPolicy(
                data.get("revalidation_policy", RevalidationPolicy.ON_FILE_CHANGE.value)
            ),
            tracked_paths=data.get("tracked_paths", []),
            path_hashes=data.get("path_hashes", {}),
            superseded_by=data.get("superseded_by"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ProjectProofCard:
    """Token-bounded diagnostic card summarizing active project proofs (<= 25 lines)."""
    project_fingerprint: str
    total_proofs: int
    durable_count: int
    validated_count: int
    stale_count: int
    invalidated_count: int
    superseded_count: int
    top_proofs: List[Tuple[str, str, str]] = field(default_factory=list)  # (id, subject, status)

    def format_card(self, max_lines: int = 25) -> str:
        lines = [
            "=== ANTIOS DURABLE PROJECT PROOFS ===",
            f"Fingerprint:   {self.project_fingerprint[:16]}...",
            f"Total Proofs:  {self.total_proofs} (Durable: {self.durable_count}, Validated: {self.validated_count})",
            f"Drift/Health:  Stale: {self.stale_count} | Invalidated: {self.invalidated_count} | Superseded: {self.superseded_count}",
            "--- Active Durable Proofs ---",
        ]
        for pid, subj, stat in self.top_proofs[:16]:
            lines.append(f"  [{stat:<11}] {pid:<22} ({subj})")
        if not self.top_proofs:
            lines.append("  (No active proofs recorded)")
        lines.append("=====================================")
        return "\n".join(lines[:max_lines])


class EvidenceDistillationEngine:
    """Deterministic extractor and promoter of reusable project proofs from mission evidence.
    
    Strictly enforces:
    MISSION EVIDENCE -> (validation) -> DURABLE PROJECT PROOF
    OBSERVATION      -X-> DURABLE PROJECT PROOF
    AGENT INFERENCE  -X-> DURABLE PROJECT PROOF
    UNVERIFIED CLAIM -X-> DURABLE PROJECT PROOF
    """

    @staticmethod
    def distill_proof(
        evidence_item: EvidenceItem,
        subject: ProofSubject,
        statement: str,
        project_fingerprint: str,
        workspace_root: str,
        tracked_paths: Optional[List[str]] = None,
        revalidation_policy: RevalidationPolicy = RevalidationPolicy.ON_FILE_CHANGE,
    ) -> ProjectProof:
        """Distills an initial candidate proof from an authoritative EvidenceItem."""
        # 1. Epistemic Separation Enforcement
        if evidence_item.epistemic_category != EpistemicCategory.EVIDENCE:
            raise ValueError(
                f"Epistemic Separation Violation: Cannot create ProjectProof from "
                f"{evidence_item.epistemic_category.value}. Only verified EVIDENCE can become proof."
            )

        # 2. State verification: evidence must be VERIFIED
        if evidence_item.state != EvidenceState.VERIFIED:
            raise ValueError(
                f"Invalid Evidence State: EvidenceItem must be VERIFIED to distill proof, "
                f"got {evidence_item.state.value}."
            )

        # 3. Provenance invariant
        if not evidence_item.provenance or not evidence_item.provenance.strip():
            raise ValueError("Stripped Provenance Violation: EvidenceItem missing provenance.")

        tracked_paths = tracked_paths or []
        path_hashes: Dict[str, str] = {}
        for p in tracked_paths:
            full_p = os.path.join(workspace_root, p) if not os.path.isabs(p) else p
            if os.path.isfile(full_p):
                try:
                    with open(full_p, "rb") as f:
                        path_hashes[p] = hashlib.sha256(f.read()).hexdigest()
                except Exception:
                    path_hashes[p] = "UNREADABLE"

        proof_id = f"proof-{subject.value.lower().replace('_', '-')}-{abs(hash(statement)) % 10000:04d}"
        ev_ref = {
            "evidence_id": evidence_item.evidence_id,
            "mission_id": evidence_item.mission_id,
            "epistemic_category": evidence_item.epistemic_category.value,
            "state": evidence_item.state.value,
            "provenance": evidence_item.provenance,
            "confidence": evidence_item.confidence,
        }

        return ProjectProof(
            proof_id=proof_id,
            subject=subject,
            statement=statement,
            origin_mission_id=evidence_item.mission_id,
            project_fingerprint=project_fingerprint,
            evidence_references=[ev_ref],
            status=ProofStatus.CANDIDATE,
            revalidation_policy=revalidation_policy,
            tracked_paths=tracked_paths,
            path_hashes=path_hashes,
        )

    @staticmethod
    def promote_proof(
        proof: ProjectProof,
        evaluation_result: MissionEvaluationResult,
        current_fingerprint: str,
        recurrence_count: int = 1,
    ) -> ProjectProof:
        """Deterministically promotes a ProjectProof through its lifecycle."""
        # 1. Fingerprint integrity
        if not current_fingerprint or current_fingerprint != proof.project_fingerprint:
            proof.status = ProofStatus.STALE
            proof.metadata["rejection_reason"] = "Project fingerprint mismatch or drift"
            return proof

        # 2. Mission evaluation must be PASS
        if evaluation_result.overall_status != EvaluationStatus.PASS:
            proof.status = ProofStatus.INVALIDATED
            proof.metadata["rejection_reason"] = (
                f"Mission evaluation was {evaluation_result.overall_status.value}"
            )
            return proof

        # 3. Check for contradictory evidence
        for ref in proof.evidence_references:
            if ref.get("state") == EvidenceState.CONFLICTING.value:
                proof.status = ProofStatus.INVALIDATED
                proof.metadata["rejection_reason"] = "Referenced evidence is conflicting"
                return proof

        # 4. Promotion ladder
        if proof.status == ProofStatus.CANDIDATE:
            proof.status = ProofStatus.VALIDATED
            proof.validation_timestamp = datetime.now(timezone.utc).isoformat()

        # Promotion to DURABLE requires independent verification or multi-task recurrence
        if proof.status == ProofStatus.VALIDATED:
            dims = getattr(evaluation_result, "dimension_evaluations", {}) or getattr(
                evaluation_result, "evaluation_dimensions", {}
            )
            has_independent_check = bool(dims.get("WORKFORCE_GOVERNANCE"))
            if recurrence_count >= 2 or has_independent_check:
                proof.status = ProofStatus.DURABLE
                proof.validation_timestamp = datetime.now(timezone.utc).isoformat()


        return proof


class ProjectProofStore:
    """Bounded filesystem store for durable project proofs.
    
    Enforces capacity bounds, physical invalidation checks, and token-bounded card emission.
    """

    def __init__(self, workspace_root: str, storage_dir: Optional[str] = None):
        self.workspace_root = workspace_root
        self.storage_dir = storage_dir or os.path.join(workspace_root, ".antios", "proofs")
        self.proofs_file = os.path.join(self.storage_dir, "proofs.json")
        self.proofs: Dict[str, ProjectProof] = {}
        self._load()

    def _load(self) -> None:
        if os.path.isfile(self.proofs_file):
            try:
                with open(self.proofs_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                items = data.get("proofs", [])
                for it in items:
                    p = ProjectProof.from_dict(it)
                    self.proofs[p.proof_id] = p
            except Exception:
                self.proofs = {}

    def save(self) -> None:
        os.makedirs(self.storage_dir, exist_ok=True)
        # Enforce MAX_DURABLE_PROOFS bound by retention priority
        if len(self.proofs) > MAX_DURABLE_PROOFS:
            # Retention priority: DURABLE > VALIDATED > CANDIDATE > AGING > STALE > SUPERSEDED > INVALIDATED
            priority = {
                ProofStatus.DURABLE: 6,
                ProofStatus.VALIDATED: 5,
                ProofStatus.CANDIDATE: 4,
                ProofStatus.AGING: 3,
                ProofStatus.STALE: 2,
                ProofStatus.SUPERSEDED: 1,
                ProofStatus.INVALIDATED: 0,
            }
            sorted_proofs = sorted(
                self.proofs.values(),
                key=lambda p: (priority.get(p.status, 0), p.validation_timestamp),
                reverse=True,
            )
            self.proofs = {p.proof_id: p for p in sorted_proofs[:MAX_DURABLE_PROOFS]}

        payload = {
            "version": "1.0",
            "count": len(self.proofs),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "proofs": [p.to_dict() for p in self.proofs.values()],
        }
        with open(self.proofs_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def add_or_update_proof(self, proof: ProjectProof) -> None:
        self.proofs[proof.proof_id] = proof
        self.save()

    def get_proof(self, proof_id: str) -> Optional[ProjectProof]:
        return self.proofs.get(proof_id)

    def list_proofs(
        self,
        subject: Optional[ProofSubject] = None,
        status: Optional[ProofStatus] = None,
    ) -> List[ProjectProof]:
        res = list(self.proofs.values())
        if subject:
            res = [p for p in res if p.subject == subject]
        if status:
            res = [p for p in res if p.status == status]
        return res

    def verify_physical_reality(self) -> List[Tuple[str, str]]:
        """Audits all tracked path hashes against physical on-disk files.
        
        Returns a list of (proof_id, invalidation_reason).
        """
        drifted: List[Tuple[str, str]] = []
        for proof in list(self.proofs.values()):
            if proof.status in (ProofStatus.INVALIDATED, ProofStatus.SUPERSEDED):
                continue

            for path, expected_hash in proof.path_hashes.items():
                full_path = (
                    os.path.join(self.workspace_root, path)
                    if not os.path.isabs(path)
                    else path
                )
                if not os.path.isfile(full_path):
                    reason = f"Tracked path missing: {path}"
                    proof.status = ProofStatus.INVALIDATED
                    proof.metadata["invalidation_reason"] = reason
                    drifted.append((proof.proof_id, reason))
                    break

                try:
                    with open(full_path, "rb") as f:
                        curr_hash = hashlib.sha256(f.read()).hexdigest()
                    if curr_hash != expected_hash:
                        reason = f"File content modified: {path}"
                        proof.status = ProofStatus.INVALIDATED
                        proof.metadata["invalidation_reason"] = reason
                        drifted.append((proof.proof_id, reason))
                        break
                except Exception as ex:
                    reason = f"File read error: {path} ({ex})"
                    proof.status = ProofStatus.INVALIDATED
                    proof.metadata["invalidation_reason"] = reason
                    drifted.append((proof.proof_id, reason))
                    break

        if drifted:
            self.save()
        return drifted

    def supersede_proof(self, old_proof_id: str, new_proof_id: str) -> bool:
        if old_proof_id in self.proofs and new_proof_id in self.proofs:
            self.proofs[old_proof_id].status = ProofStatus.SUPERSEDED
            self.proofs[old_proof_id].superseded_by = new_proof_id
            self.save()
            return True
        return False

    def emit_summary_card(self, project_fingerprint: str) -> ProjectProofCard:
        durable = sum(1 for p in self.proofs.values() if p.status == ProofStatus.DURABLE)
        validated = sum(1 for p in self.proofs.values() if p.status == ProofStatus.VALIDATED)
        stale = sum(1 for p in self.proofs.values() if p.status == ProofStatus.STALE)
        invalidated = sum(1 for p in self.proofs.values() if p.status == ProofStatus.INVALIDATED)
        superseded = sum(1 for p in self.proofs.values() if p.status == ProofStatus.SUPERSEDED)

        top_proofs = [
            (p.proof_id, p.subject.value, p.status.value)
            for p in sorted(self.proofs.values(), key=lambda x: x.validation_timestamp, reverse=True)
        ]
        return ProjectProofCard(
            project_fingerprint=project_fingerprint,
            total_proofs=len(self.proofs),
            durable_count=durable,
            validated_count=validated,
            stale_count=stale,
            invalidated_count=invalidated,
            superseded_count=superseded,
            top_proofs=top_proofs,
        )
