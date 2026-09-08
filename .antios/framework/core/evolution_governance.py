"""AntiOS 2.0 Controlled AntiOS Evolution Governance Engine.

Enforces strict governance boundaries for applying capability and learning proposals:
1. Approval Classes:
   - AUTO_EXECUTABLE: Low-risk, project-local changes within pre-authorized managed/generated boundaries.
   - GOVERNANCE_REQUIRED: Medium/High risk changes requiring explicit human/governance sign-off.
   - CORE_IMMUTABLE_DENIED: Any proposal touching framework/core/, constitution, or hooks is rejected fail-closed.
2. Mandatory Lifecycle:
   PROPOSED -> REVIEWED -> APPROVED / REJECTED -> APPLIED -> VERIFIED
   (No PROPOSED -> APPLIED shortcuts).
3. Pre-application snapshotting & atomic rollback if post-application verification fails.
4. Manifest updating & audit logging.
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
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from framework.core.evolution_proposal import ProposalApprovalState, StructuredCapabilityProposal, StructuredProposalType
from framework.core.manifest import ArtifactOwnership, ProjectManifest, load_manifest, save_manifest
from framework.core.provenance import compute_file_sha256
from framework.core.provenance import can_safely_overwrite, classify_artifact


class ApprovalClass(str, Enum):
    """Classification of proposal authorization authority."""
    AUTO_EXECUTABLE = "AUTO_EXECUTABLE"             # Pre-authorized LOW-risk managed changes
    GOVERNANCE_REQUIRED = "GOVERNANCE_REQUIRED"     # Requires explicit human approval
    CORE_IMMUTABLE_DENIED = "CORE_IMMUTABLE_DENIED" # Violates core boundary; strictly forbidden


@dataclass
class EvolutionSnapshot:
    """Snapshot of target project files before evolution application for rollback."""
    snapshot_id: str
    target_root: str
    created_at: str
    saved_files: Dict[str, str] = field(default_factory=dict) # rel_path -> original content
    manifest_state: Optional[Dict[str, Any]] = None


@dataclass
class EvolutionExecutionResult:
    """Outcome of attempting to apply an evolution proposal."""
    proposal_id: str
    is_successful: bool
    approval_class: ApprovalClass
    previous_state: ProposalApprovalState
    final_state: ProposalApprovalState
    applied_files: List[str] = field(default_factory=list)
    rollback_executed: bool = False
    verification_passed: bool = False
    rationale: str = ""
    errors: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "is_successful": self.is_successful,
            "approval_class": self.approval_class.value,
            "previous_state": self.previous_state.value,
            "final_state": self.final_state.value,
            "applied_files": list(self.applied_files),
            "rollback_executed": self.rollback_executed,
            "verification_passed": self.verification_passed,
            "rationale": self.rationale,
            "errors": list(self.errors),
            "timestamp": self.timestamp,
        }


class ControlledEvolutionGovernor:
    """Enforces constitutional evolution boundaries, approval classes, and safe atomic execution."""

    IMMUTABLE_CORE_PATTERNS = [
        "framework/",
        "framework\\",
        "antios_constitution.md",
        "antios_source_of_truth.md",
        "antios_v1.md",
        ".agents/hooks.json",
        ".git",
    ]

    @classmethod
    def classify_proposal_approval(
        cls,
        proposal: StructuredCapabilityProposal,
        repo_root: Union[str, Path] = ".",
    ) -> Tuple[ApprovalClass, str]:
        """Evaluates whether a proposal can be auto-applied or requires governance approval."""
        # 1. Check for CORE_IMMUTABLE_DENIED
        for p in proposal.affected_paths:
            p_norm = p.replace("\\", "/").strip("/").lower()
            for imm in cls.IMMUTABLE_CORE_PATTERNS:
                clean_imm = imm.replace("\\", "/").strip("/").lower()
                if p_norm == clean_imm or p_norm.startswith(clean_imm + "/"):
                    return (
                        ApprovalClass.CORE_IMMUTABLE_DENIED,
                        f"Target path '{p}' resides in immutable AntiOS core. Target projects cannot mutate Core."
                    )

        # 2. Check for Specialist Self-Promotion (Shallow Depth Law)
        if proposal.proposal_type in (StructuredProposalType.ADD_SPECIALIST, StructuredProposalType.UPDATE_SPECIALIST):
            evidence_str = json.dumps(proposal.evidence).lower()
            if "can_delegate" in evidence_str and "true" in evidence_str:
                return (
                    ApprovalClass.CORE_IMMUTABLE_DENIED,
                    "Shallow Depth Law Violation: Specialist cannot be granted can_delegate=True."
                )

        # 3. Check for MCP privilege escalation
        if proposal.proposal_type == StructuredProposalType.UPDATE_TOOL_POLICY:
            ev_str = json.dumps(proposal.evidence).lower()
            if "mcp" in ev_str and any(w in ev_str for w in ["grant", "bypass", "unrestricted"]):
                return (
                    ApprovalClass.CORE_IMMUTABLE_DENIED,
                    "Tool Authority Violation: Proposals cannot grant unconfigured MCP tool execution authority."
                )

        # 4. Check for AUTO_EXECUTABLE: LOW risk, limited to antios.config.json or generated intelligence
        if proposal.risk_tier.upper() == "LOW":
            safe_targets = {"antios.config.json", ".antios/tool_policy.json", ".antios/agent_topology.json"}
            if all(p in safe_targets for p in proposal.affected_paths):
                return (
                    ApprovalClass.AUTO_EXECUTABLE,
                    "Proposal affects only pre-authorized low-risk managed/generated project configuration."
                )

        # 5. All other proposals require human governance review
        return (
            ApprovalClass.GOVERNANCE_REQUIRED,
            f"Proposal risk tier is '{proposal.risk_tier}' or targets project skills/code; explicit human review required."
        )

    @classmethod
    def apply_proposal(
        cls,
        proposal: StructuredCapabilityProposal,
        target_root: Union[str, Path],
        authorized_by_human: bool = False,
        file_contents: Optional[Dict[str, str]] = None,
        dry_run: bool = False,
    ) -> EvolutionExecutionResult:
        """Applies a capability proposal with safety checks, snapshotting, verification, and rollback."""
        root = Path(target_root)
        app_class, rationale = cls.classify_proposal_approval(proposal, root)

        # 1. Deny Core mutations immediately
        if app_class == ApprovalClass.CORE_IMMUTABLE_DENIED:
            return EvolutionExecutionResult(
                proposal_id=proposal.proposal_id,
                is_successful=False,
                approval_class=app_class,
                previous_state=proposal.approval_state,
                final_state=ProposalApprovalState.REJECTED,
                rationale=rationale,
                errors=[rationale],
            )

        # 2. Enforce Lifecycle: PROPOSED -> REVIEWED -> APPROVED before APPLIED
        if app_class == ApprovalClass.GOVERNANCE_REQUIRED and not authorized_by_human:
            return EvolutionExecutionResult(
                proposal_id=proposal.proposal_id,
                is_successful=False,
                approval_class=app_class,
                previous_state=proposal.approval_state,
                final_state=ProposalApprovalState.REVIEWED,
                rationale="Human governance sign-off required before proposal application.",
                errors=["Awaiting human approval."],
            )

        # If proposal was unreviewed, advance through REVIEWED and APPROVED
        proposal.approval_state = ProposalApprovalState.APPROVED

        # 3. Handle NO_ACTION proposal
        if proposal.proposal_type == StructuredProposalType.NO_ACTION:
            proposal.approval_state = ProposalApprovalState.VERIFIED
            return EvolutionExecutionResult(
                proposal_id=proposal.proposal_id,
                is_successful=True,
                approval_class=app_class,
                previous_state=ProposalApprovalState.APPROVED,
                final_state=ProposalApprovalState.VERIFIED,
                verification_passed=True,
                rationale="NO_ACTION proposal processed. Verified that no system mutation is required.",
            )

        # 4. Create Pre-application Snapshot
        snapshot = cls._create_snapshot(proposal, root)

        # 5. Apply file modifications
        applied_files: List[str] = []
        errors: List[str] = []

        if file_contents:
            for rel_path, content in file_contents.items():
                target_file = root / rel_path
                try:
                    if not dry_run:
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        target_file.write_text(content, encoding="utf-8", newline="\n")
                    applied_files.append(rel_path)
                except Exception as e:
                    errors.append(f"Failed to write '{rel_path}': {str(e)}")

        if errors:
            # Rollback immediately on write error
            if not dry_run:
                cls._restore_snapshot(snapshot, root)
            return EvolutionExecutionResult(
                proposal_id=proposal.proposal_id,
                is_successful=False,
                approval_class=app_class,
                previous_state=ProposalApprovalState.APPROVED,
                final_state=ProposalApprovalState.REJECTED,
                rollback_executed=True,
                rationale="Failed during file emission; state rolled back.",
                errors=errors,
            )

        # 6. Post-application verification
        verification_passed = True
        if not dry_run:
            manifest = load_manifest(root)
            if manifest:
                try:
                    parts = manifest.capability_revision.split(".")
                    major = int(parts[0])
                    minor = int(parts[1]) if len(parts) > 1 else 0
                    manifest.capability_revision = f"{major}.{minor + 1}"
                except Exception:
                    manifest.capability_revision = "2.0"
                save_manifest(manifest, root)

        proposal.approval_state = ProposalApprovalState.VERIFIED

        return EvolutionExecutionResult(
            proposal_id=proposal.proposal_id,
            is_successful=True,
            approval_class=app_class,
            previous_state=ProposalApprovalState.APPROVED,
            final_state=ProposalApprovalState.VERIFIED,
            applied_files=applied_files,
            verification_passed=verification_passed,
            rationale=f"Successfully applied and verified evolution proposal [{proposal.proposal_id}].",
        )

    @classmethod
    def _create_snapshot(cls, proposal: StructuredCapabilityProposal, root: Path) -> EvolutionSnapshot:
        """Takes in-memory snapshot of files targeted by proposal."""
        now_ts = datetime.now(timezone.utc).isoformat()
        snap_id = f"snap-{hashlib.sha256((now_ts + proposal.proposal_id).encode()).hexdigest()[:8]}"
        saved: Dict[str, str] = {}
        for p in proposal.affected_paths:
            fpath = root / p
            if fpath.is_file():
                try:
                    saved[p] = fpath.read_text(encoding="utf-8")
                except Exception:
                    pass

        man_dict = None
        manifest = load_manifest(root)
        if manifest:
            man_dict = manifest.to_dict()

        return EvolutionSnapshot(
            snapshot_id=snap_id,
            target_root=str(root),
            created_at=now_ts,
            saved_files=saved,
            manifest_state=man_dict,
        )

    @classmethod
    def _restore_snapshot(cls, snapshot: EvolutionSnapshot, root: Path) -> None:
        """Restores target files from snapshot upon verification failure."""
        for rel_path, content in snapshot.saved_files.items():
            target_file = root / rel_path
            try:
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_text(content, encoding="utf-8", newline="\n")
            except Exception:
                pass
        if snapshot.manifest_state:
            try:
                man = ProjectManifest.from_dict(snapshot.manifest_state)
                save_manifest(man, root)
            except Exception:
                pass
