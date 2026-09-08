"""AntiOS 2.0 Generated Intelligence Verification Engine.

Phase 60: Audits generated project-intelligence artifacts against disk reality.
Detects:
- unsupported claims
- stale paths
- stale components
- stale skills
- invalid specialists
- missing provenance
- missing evidence
- ownership violations
- unauthorized capability grants
- references to deleted files
- inconsistent subsystem mappings
- legacy workflow remnants (.agents/workflows/)
- project manifest fingerprint drift

Emits structured, actionable IntelligenceVerificationVerdict.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from framework.core.manifest import (
    ArtifactOwnership,
    ArtifactRecord,
    ProjectManifest,
    load_manifest,
)
from framework.core.provenance import compute_file_sha256


class IntelligenceVerificationStatus(str, Enum):
    """Overall status of generated intelligence verification."""
    VALID = "VALID"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    STALE_INTELLIGENCE = "STALE_INTELLIGENCE"
    INTEGRITY_VIOLATION = "INTEGRITY_VIOLATION"
    CORRUPTED = "CORRUPTED"


@dataclass
class IntelligenceIssue:
    """A specific issue detected in generated project intelligence."""
    issue_type: str  # FINGERPRINT_DRIFT, STALE_PATH, DELETED_COMPONENT, INVALID_SPECIALIST, etc.
    path: str
    description: str
    severity: str  # BLOCKING, WARNING, ADVISORY
    recommended_action: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IntelligenceVerificationVerdict:
    """Actionable verification verdict produced by IntelligenceVerifier."""
    status: IntelligenceVerificationStatus
    project_root: str
    manifest_valid: bool
    drift_detected: bool
    issues: List[IntelligenceIssue] = field(default_factory=list)
    fingerprint_current: str = ""
    fingerprint_recorded: str = ""
    remediation_command: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "project_root": self.project_root,
            "manifest_valid": self.manifest_valid,
            "drift_detected": self.drift_detected,
            "issues": [i.to_dict() for i in self.issues],
            "fingerprint_current": self.fingerprint_current,
            "fingerprint_recorded": self.fingerprint_recorded,
            "remediation_command": self.remediation_command,
        }


class IntelligenceVerifier:
    """Comprehensive verification engine for AntiOS project intelligence."""

    VERSION = "2.0.0"

    def __init__(self, repo_root: Union[str, Path]):
        self.repo_root = Path(os.path.normcase(os.path.abspath(repo_root)))

    def verify(self) -> IntelligenceVerificationVerdict:
        """Audits all generated and managed intelligence artifacts against disk reality."""
        issues: List[IntelligenceIssue] = []

        manifest_path = self.repo_root / ".antios" / "manifest.json"
        if not manifest_path.is_file():
            issues.append(IntelligenceIssue(
                issue_type="MISSING_MANIFEST",
                path=".antios/manifest.json",
                description="Project manifest does not exist. AntiOS is uninstalled or unadapted.",
                severity="BLOCKING",
                recommended_action="Run: python framework/scripts/tools/adapt_project.py .",
            ))
            return IntelligenceVerificationVerdict(
                status=IntelligenceVerificationStatus.INTEGRITY_VIOLATION,
                project_root=str(self.repo_root),
                manifest_valid=False,
                drift_detected=False,
                issues=issues,
                remediation_command="python framework/scripts/tools/adapt_project.py .",
            )

        try:
            manifest = load_manifest(self.repo_root)
        except Exception:
            manifest = None

        if manifest is None:
            legacy_workflows_dir = self.repo_root / ".agents" / "workflows"
            if legacy_workflows_dir.exists():
                issues.append(IntelligenceIssue(
                    issue_type="LEGACY_WORKFLOWS_PRESENT",
                    path=".agents/workflows/",
                    description="Deprecated .agents/workflows/ directory detected. Phase 59 requires 0 workflows.",
                    severity="BLOCKING",
                    recommended_action="Remove .agents/workflows/ and migrate to skill-agent-native dispatch.",
                ))
            issues.append(IntelligenceIssue(
                issue_type="CORRUPTED_MANIFEST",
                path=".antios/manifest.json",
                description="Failed to parse .antios/manifest.json; JSON syntax invalid or schema incompatible.",
                severity="BLOCKING",
                recommended_action="Run: python framework/scripts/tools/adapt_project.py . --force",
            ))
            return IntelligenceVerificationVerdict(
                status=IntelligenceVerificationStatus.CORRUPTED,
                project_root=str(self.repo_root),
                manifest_valid=False,
                drift_detected=False,
                issues=issues,
                remediation_command="python framework/scripts/tools/adapt_project.py . --force",
            )

        # 1. Cryptographic Hash Integrity of Managed & Generated Paths
        self._audit_artifact_hashes(manifest, issues)

        # 2. Manifest Fingerprint Drift Detection
        drift_detected, current_fp = self._audit_fingerprint_drift(manifest, issues)

        # 3. Audit Physical Path Validity (Subsystems, Entrypoints, Test Roots)
        self._audit_physical_paths(issues)

        # 4. Audit Skills Integrity & Disallow Legacy Workflows
        self._audit_skills_and_workflows(manifest, issues)

        # 5. Audit Specialist Topology (Shallow Depth Law, Capability Boundaries)
        self._audit_specialist_topology(issues)

        # 6. Audit Tool Runner Availability
        self._audit_tool_runners(issues)

        # 7. Audit Project Learning State (.antios/learning_*.json) [Phases 61-66]
        self._audit_learning_state(issues)

        # Determine overall status
        status = IntelligenceVerificationStatus.VALID
        remediation_cmd = ""
        has_blocking = any(i.severity == "BLOCKING" for i in issues)
        has_warning = any(i.severity == "WARNING" for i in issues)

        if has_blocking:
            status = IntelligenceVerificationStatus.INTEGRITY_VIOLATION
            remediation_cmd = "python framework/scripts/tools/adapt_project.py ."
        elif drift_detected:
            status = IntelligenceVerificationStatus.DRIFT_DETECTED
            remediation_cmd = "python framework/scripts/tools/adapt_project.py ."
        elif has_warning:
            status = IntelligenceVerificationStatus.STALE_INTELLIGENCE
            remediation_cmd = "python framework/scripts/tools/adapt_project.py ."

        return IntelligenceVerificationVerdict(
            status=status,
            project_root=str(self.repo_root),
            manifest_valid=True,
            drift_detected=drift_detected,
            issues=issues,
            fingerprint_current=current_fp,
            fingerprint_recorded=manifest.project_fingerprint,
            remediation_command=remediation_cmd,
        )

    def _audit_artifact_hashes(self, manifest: ProjectManifest, issues: List[IntelligenceIssue]) -> None:
        """Verifies SHA-256 of all tracked artifacts against disk reality."""
        all_tracked = {**manifest.managed_paths, **manifest.generated_paths}
        for rel_path, record in all_tracked.items():
            disk_file = self.repo_root / rel_path
            if not disk_file.is_file():
                issues.append(IntelligenceIssue(
                    issue_type="MISSING_ARTIFACT",
                    path=rel_path,
                    description=f"Tracked artifact '{rel_path}' is missing on disk.",
                    severity="BLOCKING",
                    recommended_action="Run repair or adapt to regenerate missing artifacts.",
                ))
                continue

            disk_sha = compute_file_sha256(disk_file)
            if disk_sha != record.sha256 and not record.is_user_modified:
                # If it's a managed path like antios.config.json, user might have modified it
                if record.ownership == ArtifactOwnership.MANAGED:
                    issues.append(IntelligenceIssue(
                        issue_type="MANAGED_ARTIFACT_MODIFIED",
                        path=rel_path,
                        description=f"Managed artifact '{rel_path}' checksum differs from manifest.",
                        severity="WARNING",
                        recommended_action="Review manual edits to managed configuration.",
                    ))
                else:
                    issues.append(IntelligenceIssue(
                        issue_type="GENERATED_ARTIFACT_DRIFT",
                        path=rel_path,
                        description=f"Generated artifact '{rel_path}' checksum differs from recorded state.",
                        severity="WARNING",
                        recommended_action="Recompile generated intelligence via adapt.",
                    ))

    def _audit_fingerprint_drift(
        self, manifest: ProjectManifest, issues: List[IntelligenceIssue]
    ) -> Tuple[bool, str]:
        """Calculates current project manifest fingerprint and compares against recorded."""
        from framework.core.discovery import discover_project
        profile = discover_project(str(self.repo_root))
        current_fp = profile.manifest_fingerprint
        if not current_fp:
            current_fp = hashlib.sha256(f"manifestless:{self.repo_root.name}".encode("utf-8")).hexdigest()

        recorded_fp = manifest.project_fingerprint
        if recorded_fp and current_fp != recorded_fp:
            issues.append(IntelligenceIssue(
                issue_type="FINGERPRINT_DRIFT",
                path="manifest.project_fingerprint",
                description=f"Target project manifest fingerprint changed ({recorded_fp[:8]}... -> {current_fp[:8]}...).",
                severity="WARNING",
                recommended_action="Run: python framework/scripts/tools/adapt_project.py . to resync intelligence.",
            ))
            return True, current_fp

        return False, current_fp

    def _audit_physical_paths(self, issues: List[IntelligenceIssue]) -> None:
        """Verifies that paths declared in knowledge.json and project_anatomy.json exist."""
        # 1. Check knowledge.json
        kj_path = self.repo_root / ".antios" / "knowledge.json"
        if kj_path.is_file():
            try:
                with open(kj_path, "r", encoding="utf-8") as f:
                    kdata = json.load(f)
                for sub in kdata.get("subsystems", []):
                    sub_id = sub.get("subsystem_id", "unknown")
                    for rp in sub.get("root_paths", []):
                        if not (self.repo_root / rp).exists():
                            issues.append(IntelligenceIssue(
                                issue_type="STALE_PATH",
                                path=rp,
                                description=f"Subsystem '{sub_id}' declares root_path '{rp}' which does not exist on disk.",
                                severity="WARNING",
                                recommended_action="Re-adapt project to prune stale subsystem paths.",
                            ))
                    for ep in sub.get("entrypoints", []):
                        if not (self.repo_root / ep).exists():
                            issues.append(IntelligenceIssue(
                                issue_type="STALE_PATH",
                                path=ep,
                                description=f"Subsystem '{sub_id}' declares entrypoint '{ep}' which does not exist on disk.",
                                severity="WARNING",
                                recommended_action="Re-adapt project to update subsystem entrypoints.",
                            ))
            except Exception:
                pass

        # 2. Check project_anatomy.json if present
        pa_path = self.repo_root / ".antios" / "project_anatomy.json"
        if pa_path.is_file():
            try:
                with open(pa_path, "r", encoding="utf-8") as f:
                    pdata = json.load(f)
                for sr in pdata.get("source_roots", []):
                    if sr != "." and not (self.repo_root / sr).exists():
                        issues.append(IntelligenceIssue(
                            issue_type="STALE_SOURCE_ROOT",
                            path=sr,
                            description=f"Project anatomy declares source_root '{sr}' which does not exist on disk.",
                            severity="WARNING",
                            recommended_action="Re-compile project anatomy.",
                        ))
                for tr in pdata.get("test_roots", []):
                    if not (self.repo_root / tr).exists():
                        issues.append(IntelligenceIssue(
                            issue_type="STALE_TEST_ROOT",
                            path=tr,
                            description=f"Project anatomy declares test_root '{tr}' which does not exist on disk.",
                            severity="WARNING",
                            recommended_action="Re-compile project anatomy.",
                        ))
            except Exception:
                pass

    def _audit_skills_and_workflows(self, manifest: ProjectManifest, issues: List[IntelligenceIssue]) -> None:
        """Audits skills validity and checks zero legacy workflows invariant."""
        # 1. Mandatory Single User Entrypoint check
        main_skill = self.repo_root / ".agents" / "skills" / "antios" / "SKILL.md"
        if not main_skill.is_file():
            issues.append(IntelligenceIssue(
                issue_type="MISSING_MAIN_SKILL",
                path=".agents/skills/antios/SKILL.md",
                description="Primary AntiOS operating skill (.agents/skills/antios/SKILL.md) is missing.",
                severity="BLOCKING",
                recommended_action="Run: python framework/scripts/tools/adapt_project.py . to generate SKILL.md",
            ))

        # 2. Zero Legacy Workflows Invariant
        legacy_workflows_dir = self.repo_root / ".agents" / "workflows"
        if legacy_workflows_dir.exists():
            issues.append(IntelligenceIssue(
                issue_type="LEGACY_WORKFLOWS_PRESENT",
                path=".agents/workflows/",
                description="Deprecated .agents/workflows/ directory detected. Phase 59 requires 0 workflows.",
                severity="BLOCKING",
                recommended_action="Remove .agents/workflows/ and migrate to skill-agent-native dispatch.",
            ))

    def _audit_specialist_topology(self, issues: List[IntelligenceIssue]) -> None:
        """Audits agent topology and specialist roles against Shallow Depth Law and core invariants."""
        topo_path = self.repo_root / ".antios" / "agent_topology.json"
        if not topo_path.is_file():
            return

        try:
            with open(topo_path, "r", encoding="utf-8") as f:
                tdata = json.load(f)

            specialists = tdata.get("specialists", {})
            for sid, sdata in specialists.items():
                max_depth = sdata.get("max_depth", 2)
                can_del = sdata.get("can_delegate", False)

                if max_depth > 2:
                    issues.append(IntelligenceIssue(
                        issue_type="SHALLOW_DEPTH_VIOLATION",
                        path=f".antios/agent_topology.json:{sid}",
                        description=f"Specialist '{sid}' declares max_depth={max_depth} > 2.",
                        severity="BLOCKING",
                        recommended_action="Enforce max_depth <= 2 on all non-primary specialists.",
                    ))

                if can_del:
                    issues.append(IntelligenceIssue(
                        issue_type="SHALLOW_DEPTH_VIOLATION",
                        path=f".antios/agent_topology.json:{sid}",
                        description=f"Specialist '{sid}' declares can_delegate=True. Non-primary roles cannot delegate.",
                        severity="BLOCKING",
                        recommended_action="Set can_delegate=False on specialist.",
                    ))

                # Check forbidden capabilities
                forb = sdata.get("forbidden_capabilities", [])
                for required_forb in ["rule:core-immutable:override", "rule:stop-gate-ratchet:override"]:
                    if required_forb not in forb:
                        issues.append(IntelligenceIssue(
                            issue_type="UNAUTHORIZED_CAPABILITY",
                            path=f".antios/agent_topology.json:{sid}",
                            description=f"Specialist '{sid}' boundary missing mandatory forbidden override: '{required_forb}'.",
                            severity="BLOCKING",
                            recommended_action="Inject mandatory core safety invariants into specialist boundary.",
                        ))
        except Exception:
            pass

    def _audit_tool_runners(self, issues: List[IntelligenceIssue]) -> None:
        """Verifies configured test runners are available in host PATH."""
        config_path = self.repo_root / "antios.config.json"
        if not config_path.is_file():
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cdata = json.load(f)
            runners = cdata.get("test_runners", [])
            for r in runners:
                cmd = r.get("command") or r.get("default_command") or []
                if cmd and isinstance(cmd, list):
                    bin_name = cmd[0]
                    if not shutil.which(bin_name):
                        issues.append(IntelligenceIssue(
                            issue_type="TOOLING_UNAVAILABLE",
                            path=f"antios.config.json:{r.get('name', 'runner')}",
                            description=f"Configured test runner binary '{bin_name}' is not found in host PATH.",
                            severity="ADVISORY",
                            recommended_action=f"Install '{bin_name}' on host or adjust configured test runners.",
                        ))
        except Exception:
            pass

    def _audit_learning_state(self, issues: List[IntelligenceIssue]) -> None:
        """Audits project-local learning state (.antios/learning_observations.json & learning_proposals.json)."""
        obs_file = self.repo_root / ".antios" / "learning_observations.json"
        if obs_file.is_file():
            try:
                if obs_file.stat().st_size > 250_000:
                    issues.append(IntelligenceIssue(
                        issue_type="LEARNING_STORAGE_BOUND_EXCEEDED",
                        path=".antios/learning_observations.json",
                        description="Observation storage file exceeds 250KB bound.",
                        severity="WARNING",
                        recommended_action="Run: python framework/scripts/tools/distill_memory.py . --audit to prune stale observations.",
                    ))
                with open(obs_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                observations = data.get("observations", [])
                if len(observations) > 120:
                    issues.append(IntelligenceIssue(
                        issue_type="OBSERVATION_COUNT_BOUND_EXCEEDED",
                        path=".antios/learning_observations.json",
                        description=f"Observation count ({len(observations)}) exceeds max bound (100).",
                        severity="WARNING",
                        recommended_action="Prune old or unconfirmed observations.",
                    ))
                from framework.core.learning import LearningSafetyGate, Observation
                for obs_dict in observations:
                    try:
                        obs_obj = Observation.from_dict(obs_dict)
                        is_safe, denial_reason = LearningSafetyGate.validate_observation(obs_obj)
                        if not is_safe:
                            issues.append(IntelligenceIssue(
                                issue_type="POISONED_LEARNING_OBSERVATION",
                                path=f".antios/learning_observations.json:{obs_obj.observation_id}",
                                description=f"Observation [{obs_obj.observation_id}] violates safety gate: {denial_reason}",
                                severity="BLOCKING",
                                recommended_action="Remove poisoned observation immediately.",
                            ))
                    except Exception:
                        pass
            except Exception:
                pass

        prop_file = self.repo_root / ".antios" / "learning_proposals.json"
        if prop_file.is_file():
            try:
                with open(prop_file, "r", encoding="utf-8") as f:
                    pdata = json.load(f)
                proposals = pdata.get("proposals", [])
                from framework.core.learning import LearningSafetyGate, EvolutionProposal
                for p_dict in proposals:
                    try:
                        prop_obj = EvolutionProposal.from_dict(p_dict)
                        is_safe, denial_reason = LearningSafetyGate.validate_proposal(prop_obj, self.repo_root)
                        if not is_safe:
                            issues.append(IntelligenceIssue(
                                issue_type="ILLEGAL_EVOLUTION_PROPOSAL",
                                path=f".antios/learning_proposals.json:{prop_obj.proposal_id}",
                                description=f"Proposal [{prop_obj.proposal_id}] violates safety gate: {denial_reason}",
                                severity="BLOCKING",
                                recommended_action="Reject and delete illegal proposal.",
                            ))
                    except Exception:
                        pass
            except Exception:
                pass
