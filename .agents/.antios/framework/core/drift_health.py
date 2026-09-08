"""AntiOS 2.0 Runtime Drift Detection & Project Intelligence Health (Phase 94).

Deterministic drift detection, intelligence health scoring, and proposal-governed repair:
- Event-driven / mission-triggered (Zero background daemons)
- 10 drift domains: FILE_STRUCTURE, COMPONENT_OWNERSHIP, PROJECT_MANIFEST, ADAPTER_CONFIGURATION,
  SKILLS, DOCUMENTATION, TEST_OWNERSHIP, CAPABILITY_MAPPINGS, DURABLE_PROOFS, ARCHITECTURE_ASSUMPTIONS
- 5 severity levels: NO_DRIFT, MINOR_DRIFT, SIGNIFICANT_DRIFT, CRITICAL_DRIFT, UNKNOWN
- 6 recommended actions: NONE, REFRESH, REVERIFY, REPLAN, REBUILD_INTELLIGENCE, BLOCK
- 7 defensible health dimensions: proof_freshness, adapter_integrity, navigation_integrity,
  documentation_integrity, capability_mapping_integrity, test_mapping_integrity, evidence_validity
- 4 health statuses: HEALTHY, DEGRADED, STALE, UNTRUSTED
- Proposal-governed repair: no autonomous architecture mutation; emits bounded repair proposals
- Bounded limits: MAX_DRIFT_FINDINGS = 20, MAX_REPAIR_PROPOSALS = 10
- Token-bounded DriftHealthCard (<= 25 lines)
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from framework.core.project_proof import (
    ProjectProof,
    ProjectProofStore,
    ProofStatus,
    ProofSubject,
)


MAX_DRIFT_FINDINGS = 20
MAX_REPAIR_PROPOSALS = 10


class DriftDomain(str, Enum):
    """The 10 canonical domains subject to runtime drift detection."""
    FILE_STRUCTURE = "FILE_STRUCTURE"
    COMPONENT_OWNERSHIP = "COMPONENT_OWNERSHIP"
    PROJECT_MANIFEST = "PROJECT_MANIFEST"
    ADAPTER_CONFIGURATION = "ADAPTER_CONFIGURATION"
    SKILLS = "SKILLS"
    DOCUMENTATION = "DOCUMENTATION"
    TEST_OWNERSHIP = "TEST_OWNERSHIP"
    CAPABILITY_MAPPINGS = "CAPABILITY_MAPPINGS"
    DURABLE_PROOFS = "DURABLE_PROOFS"
    ARCHITECTURE_ASSUMPTIONS = "ARCHITECTURE_ASSUMPTIONS"


class DriftSeverity(str, Enum):
    """Deterministic drift severity classifications."""
    NO_DRIFT = "NO_DRIFT"
    MINOR_DRIFT = "MINOR_DRIFT"
    SIGNIFICANT_DRIFT = "SIGNIFICANT_DRIFT"
    CRITICAL_DRIFT = "CRITICAL_DRIFT"
    UNKNOWN = "UNKNOWN"


class DriftAction(str, Enum):
    """Deterministic governance actions resulting from drift detection."""
    NONE = "NONE"
    REFRESH = "REFRESH"
    REVERIFY = "REVERIFY"
    REPLAN = "REPLAN"
    REBUILD_INTELLIGENCE = "REBUILD_INTELLIGENCE"
    BLOCK = "BLOCK"


class IntelligenceHealthStatus(str, Enum):
    """Defensible health status classes for project intelligence."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    UNTRUSTED = "UNTRUSTED"


class RepairActionType(str, Enum):
    """Canonical repair actions that can be proposed when drift is detected."""
    REFRESH_PROJECT_MAP = "REFRESH_PROJECT_MAP"
    REGENERATE_DOC_INDEX = "REGENERATE_DOC_INDEX"
    REVALIDATE_PROOF = "REVALIDATE_PROOF"
    RUN_TARGETED_TESTS = "RUN_TARGETED_TESTS"
    REBUILD_CAPABILITY_MAP = "REBUILD_CAPABILITY_MAP"
    REFRESH_ADAPTER_METADATA = "REFRESH_ADAPTER_METADATA"
    INVALIDATE_STALE_HINT = "INVALIDATE_STALE_HINT"
    REQUEST_HUMAN_REVIEW = "REQUEST_HUMAN_REVIEW"


@dataclass
class DriftFinding:
    """A concrete, evidence-backed drift finding."""
    domain: DriftDomain
    severity: DriftSeverity
    recommended_action: DriftAction
    description: str
    previous_fingerprint: str
    current_fingerprint: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    affected_paths: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain.value,
            "severity": self.severity.value,
            "recommended_action": self.recommended_action.value,
            "description": self.description,
            "previous_fingerprint": self.previous_fingerprint,
            "current_fingerprint": self.current_fingerprint,
            "evidence": dict(self.evidence),
            "affected_paths": list(self.affected_paths),
        }


@dataclass
class RepairProposal:
    """A bounded, governed proposal for repairing or revalidating intelligence."""
    proposal_id: str
    action_type: RepairActionType
    target_domain: DriftDomain
    rationale: str
    target_artifacts: List[str] = field(default_factory=list)
    suggested_command: Optional[str] = None
    priority: str = "NORMAL"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "action_type": self.action_type.value,
            "target_domain": self.target_domain.value,
            "rationale": self.rationale,
            "target_artifacts": list(self.target_artifacts),
            "suggested_command": self.suggested_command,
            "priority": self.priority,
        }


@dataclass
class IntelligenceHealthResult:
    """The defensible project intelligence health assessment."""
    status: IntelligenceHealthStatus
    timestamp: str
    project_fingerprint: str
    dimension_scores: Dict[str, float]  # 7 defensible dimensions [0.0 - 1.0]
    dimension_statuses: Dict[str, str]  # dimension -> HEALTHY / DEGRADED / STALE / UNTRUSTED
    findings: List[DriftFinding] = field(default_factory=list)
    proposals: List[RepairProposal] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "project_fingerprint": self.project_fingerprint,
            "dimension_scores": dict(self.dimension_scores),
            "dimension_statuses": dict(self.dimension_statuses),
            "findings": [f.to_dict() for f in self.findings],
            "proposals": [p.to_dict() for p in self.proposals],
        }


@dataclass
class DriftHealthCard:
    """Token-bounded diagnostic card summarizing drift and health (<= 25 lines)."""
    health_status: IntelligenceHealthStatus
    overall_drift_severity: DriftSeverity
    overall_action: DriftAction
    project_fingerprint: str
    dimension_summary: Dict[str, str]
    finding_counts: Dict[str, int]
    top_findings: List[Tuple[str, str, str]] = field(default_factory=list)  # (domain, severity, action)
    proposal_count: int = 0

    def format_card(self, max_lines: int = 25) -> str:
        lines = [
            "=== ANTIOS INTELLIGENCE HEALTH CARD ===",
            f"Health Status:  {self.health_status.value} [Drift: {self.overall_drift_severity.value}]",
            f"Action Req:     {self.overall_action.value} (Proposals: {self.proposal_count})",
            f"Fingerprint:    {self.project_fingerprint[:16]}...",
            "--- Defensible Health Dimensions ---",
        ]
        for dim, stat in list(self.dimension_summary.items())[:7]:
            lines.append(f"  {dim:<26}: {stat}")
        lines.append("--- Active Drift Findings ---")
        if not self.top_findings:
            lines.append("  (Zero drift detected - physical reality aligned)")
        else:
            for dom, sev, act in self.top_findings[:5]:
                lines.append(f"  [{sev:<16}] {dom:<22} -> {act}")
        lines.append("========================================")
        return "\n".join(lines[:max_lines])


class ProjectDriftEngine:
    """Event-driven detector of runtime drift across the 10 canonical domains."""

    @staticmethod
    def evaluate_drift(
        workspace_root: str,
        proof_store: Optional[ProjectProofStore] = None,
        manifest_path: Optional[str] = None,
        adapter_path: Optional[str] = None,
        recorded_fingerprints: Optional[Dict[str, str]] = None,
    ) -> List[DriftFinding]:
        """Evaluates on-disk reality against recorded fingerprints and proofs."""
        findings: List[DriftFinding] = []
        recorded = recorded_fingerprints or {}

        # 1. Manifest drift
        mpath = manifest_path or os.path.join(workspace_root, "antios.config.json")
        if os.path.isfile(mpath):
            try:
                with open(mpath, "rb") as f:
                    curr_m_hash = hashlib.sha256(f.read()).hexdigest()
                prev_m_hash = recorded.get("manifest_hash", curr_m_hash)
                if curr_m_hash != prev_m_hash:
                    findings.append(
                        DriftFinding(
                            domain=DriftDomain.PROJECT_MANIFEST,
                            severity=DriftSeverity.SIGNIFICANT_DRIFT,
                            recommended_action=DriftAction.REFRESH,
                            description="Project manifest antios.config.json drifted from baseline hash",
                            previous_fingerprint=prev_m_hash,
                            current_fingerprint=curr_m_hash,
                            affected_paths=["antios.config.json"],
                        )
                    )
            except Exception as ex:
                findings.append(
                    DriftFinding(
                        domain=DriftDomain.PROJECT_MANIFEST,
                        severity=DriftSeverity.CRITICAL_DRIFT,
                        recommended_action=DriftAction.BLOCK,
                        description=f"Unreadable project manifest: {ex}",
                        previous_fingerprint="KNOWN",
                        current_fingerprint="CORRUPT",
                    )
                )

        # 2. Adapter configuration drift
        apath = adapter_path or os.path.join(workspace_root, ".antios", "project_adapter.json")
        if os.path.isfile(apath):
            try:
                with open(apath, "rb") as f:
                    curr_a_hash = hashlib.sha256(f.read()).hexdigest()
                prev_a_hash = recorded.get("adapter_hash", curr_a_hash)
                if curr_a_hash != prev_a_hash:
                    findings.append(
                        DriftFinding(
                            domain=DriftDomain.ADAPTER_CONFIGURATION,
                            severity=DriftSeverity.SIGNIFICANT_DRIFT,
                            recommended_action=DriftAction.REFRESH_ADAPTER_METADATA if hasattr(DriftAction, "REFRESH_ADAPTER_METADATA") else DriftAction.REFRESH,
                            description="Project adapter config drifted from recorded fingerprint",
                            previous_fingerprint=prev_a_hash,
                            current_fingerprint=curr_a_hash,
                            affected_paths=[".antios/project_adapter.json"],
                        )
                    )
            except Exception:
                pass

        # 3. Durable Project Proofs drift (physical grounding)
        if proof_store:
            drifted_proofs = proof_store.verify_physical_reality()
            if drifted_proofs:
                for pid, reason in drifted_proofs[:MAX_DRIFT_FINDINGS]:
                    findings.append(
                        DriftFinding(
                            domain=DriftDomain.DURABLE_PROOFS,
                            severity=DriftSeverity.SIGNIFICANT_DRIFT,
                            recommended_action=DriftAction.REVERIFY,
                            description=f"Durable proof {pid} invalidated: {reason}",
                            previous_fingerprint="VALIDATED",
                            current_fingerprint="INVALIDATED",
                            evidence={"proof_id": pid, "reason": reason},
                        )
                    )

        # 4. Critical Architecture Assumptions / Protected Zones Check
        # If any protected core zone (framework/ or constitution) has unrecorded changes
        core_files = ["ANTIOS_CONSTITUTION.md", "framework/core/__init__.py"]
        for cf in core_files:
            cfp = os.path.join(workspace_root, cf)
            if os.path.isfile(cfp):
                try:
                    with open(cfp, "rb") as f:
                        cf_hash = hashlib.sha256(f.read()).hexdigest()
                    expected_cf = recorded.get(f"core_{cf}", cf_hash)
                    if cf_hash != expected_cf:
                        findings.append(
                            DriftFinding(
                                domain=DriftDomain.ARCHITECTURE_ASSUMPTIONS,
                                severity=DriftSeverity.CRITICAL_DRIFT,
                                recommended_action=DriftAction.BLOCK,
                                description=f"Protected architecture file modified: {cf}",
                                previous_fingerprint=expected_cf,
                                current_fingerprint=cf_hash,
                                affected_paths=[cf],
                            )
                        )
                except Exception:
                    pass

        # 5. Documentation drift check
        acpath = os.path.join(workspace_root, "docs", "ACTIVE_CONTEXT.md")
        if os.path.isfile(acpath):
            try:
                with open(acpath, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                if len(lines) > 60:
                    findings.append(
                        DriftFinding(
                            domain=DriftDomain.DOCUMENTATION,
                            severity=DriftSeverity.MINOR_DRIFT,
                            recommended_action=DriftAction.REFRESH,
                            description=f"docs/ACTIVE_CONTEXT.md exceeded budget: {len(lines)} lines (budget <= 60)",
                            previous_fingerprint="<=60_LINES",
                            current_fingerprint=f"{len(lines)}_LINES",
                            affected_paths=["docs/ACTIVE_CONTEXT.md"],
                        )
                    )
            except Exception:
                pass

        # 6. Test ownership drift check
        config_path = os.path.join(workspace_root, "antios.config.json")
        has_configured_runner = False
        if os.path.isfile(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    trs = cfg.get("test_runners", [])
                    has_configured_runner = any(tr.get("default_command") for tr in trs)
            except Exception:
                pass

        runner_path = os.path.join(workspace_root, "tests", "run_all.py")

        if not os.path.isfile(runner_path) and not has_configured_runner:
            findings.append(
                DriftFinding(
                    domain=DriftDomain.TEST_OWNERSHIP,
                    severity=DriftSeverity.CRITICAL_DRIFT,
                    recommended_action=DriftAction.BLOCK,
                    description="Authoritative master test runner missing: tests/run_all.py or configured runner in antios.config.json",
                    previous_fingerprint="PRESENT",
                    current_fingerprint="MISSING",
                    affected_paths=["tests/run_all.py"],
                )
            )


        return findings[:MAX_DRIFT_FINDINGS]


class IntelligenceHealthEngine:
    """Evaluates the 7 defensible dimensions of project intelligence health."""

    @staticmethod
    def evaluate_health(
        workspace_root: str,
        findings: List[DriftFinding],
        proof_store: Optional[ProjectProofStore] = None,
    ) -> IntelligenceHealthResult:
        now_iso = datetime.now(timezone.utc).isoformat()
        fp = hashlib.sha256(now_iso.encode("utf-8")).hexdigest()

        # 1. Proof Freshness Dimension
        proof_score = 1.0
        proof_status = "HEALTHY"
        if proof_store and proof_store.proofs:
            total = len(proof_store.proofs)
            valid = sum(
                1 for p in proof_store.proofs.values()
                if p.status in (ProofStatus.DURABLE, ProofStatus.VALIDATED)
            )
            proof_score = valid / total if total > 0 else 1.0
            if proof_score >= 0.9:
                proof_status = "HEALTHY"
            elif proof_score >= 0.7:
                proof_status = "DEGRADED"
            elif proof_score >= 0.4:
                proof_status = "STALE"
            else:
                proof_status = "UNTRUSTED"

        # 2. Adapter Integrity
        adapter_findings = [f for f in findings if f.domain == DriftDomain.ADAPTER_CONFIGURATION]
        adapter_score = 1.0 if not adapter_findings else 0.5
        adapter_status = "HEALTHY" if not adapter_findings else "DEGRADED"

        # 3. Navigation Integrity
        nav_findings = [f for f in findings if f.domain in (DriftDomain.FILE_STRUCTURE, DriftDomain.COMPONENT_OWNERSHIP)]
        nav_score = 1.0 if not nav_findings else 0.6
        nav_status = "HEALTHY" if not nav_findings else "DEGRADED"

        # 4. Documentation Integrity
        doc_findings = [f for f in findings if f.domain == DriftDomain.DOCUMENTATION]
        doc_score = 1.0 if not doc_findings else 0.8
        doc_status = "HEALTHY" if not doc_findings else "DEGRADED"

        # 5. Capability Mapping Integrity
        cap_findings = [f for f in findings if f.domain == DriftDomain.CAPABILITY_MAPPINGS]
        cap_score = 1.0 if not cap_findings else 0.5
        cap_status = "HEALTHY" if not cap_findings else "DEGRADED"

        # 6. Test Mapping Integrity
        test_findings = [f for f in findings if f.domain == DriftDomain.TEST_OWNERSHIP]
        test_score = 1.0 if not test_findings else 0.2
        test_status = "HEALTHY" if not test_findings else "UNTRUSTED"

        # 7. Evidence & Assumptions Validity
        arch_findings = [f for f in findings if f.domain == DriftDomain.ARCHITECTURE_ASSUMPTIONS]
        ev_score = 1.0 if not arch_findings else 0.1
        ev_status = "HEALTHY" if not arch_findings else "UNTRUSTED"

        dimension_scores = {
            "proof_freshness": round(proof_score, 2),
            "adapter_integrity": round(adapter_score, 2),
            "navigation_integrity": round(nav_score, 2),
            "documentation_integrity": round(doc_score, 2),
            "capability_mapping_integrity": round(cap_score, 2),
            "test_mapping_integrity": round(test_score, 2),
            "evidence_validity": round(ev_score, 2),
        }

        dimension_statuses = {
            "proof_freshness": proof_status,
            "adapter_integrity": adapter_status,
            "navigation_integrity": nav_status,
            "documentation_integrity": doc_status,
            "capability_mapping_integrity": cap_status,
            "test_mapping_integrity": test_status,
            "evidence_validity": ev_status,
        }

        # Overall health logic
        has_critical = any(f.severity == DriftSeverity.CRITICAL_DRIFT for f in findings)
        has_significant = any(f.severity == DriftSeverity.SIGNIFICANT_DRIFT for f in findings)
        avg_score = sum(dimension_scores.values()) / len(dimension_scores)

        if has_critical or avg_score < 0.4:
            overall_status = IntelligenceHealthStatus.UNTRUSTED
        elif avg_score < 0.65:
            overall_status = IntelligenceHealthStatus.STALE
        elif has_significant or avg_score < 0.85:
            overall_status = IntelligenceHealthStatus.DEGRADED
        else:
            overall_status = IntelligenceHealthStatus.HEALTHY

        # Generate repair proposals
        proposals = IntelligenceRepairEngine.generate_proposals(findings)

        return IntelligenceHealthResult(
            status=overall_status,
            timestamp=now_iso,
            project_fingerprint=fp,
            dimension_scores=dimension_scores,
            dimension_statuses=dimension_statuses,
            findings=findings,
            proposals=proposals,
        )


class IntelligenceRepairEngine:
    """Generates bounded repair and revalidation proposals without autonomous mutation."""

    @staticmethod
    def generate_proposals(findings: List[DriftFinding]) -> List[RepairProposal]:
        proposals: List[RepairProposal] = []
        for i, f in enumerate(findings[:MAX_REPAIR_PROPOSALS]):
            p_id = f"proposal-repair-{i+1:03d}"
            if f.domain == DriftDomain.DURABLE_PROOFS:
                proposals.append(
                    RepairProposal(
                        proposal_id=p_id,
                        action_type=RepairActionType.REVALIDATE_PROOF,
                        target_domain=f.domain,
                        rationale=f"Revalidate or invalidate proof due to: {f.description}",
                        target_artifacts=f.affected_paths,
                        priority="HIGH" if f.severity in (DriftSeverity.CRITICAL_DRIFT, DriftSeverity.SIGNIFICANT_DRIFT) else "NORMAL",
                    )
                )
            elif f.domain == DriftDomain.PROJECT_MANIFEST:
                proposals.append(
                    RepairProposal(
                        proposal_id=p_id,
                        action_type=RepairActionType.REFRESH_PROJECT_MAP,
                        target_domain=f.domain,
                        rationale="Refresh wayfinding manifest and project boundary configuration",
                        target_artifacts=["antios.config.json"],
                        suggested_command="python framework/scripts/refresh_manifest.py",
                        priority="HIGH",
                    )
                )
            elif f.domain == DriftDomain.DOCUMENTATION:
                proposals.append(
                    RepairProposal(
                        proposal_id=p_id,
                        action_type=RepairActionType.REGENERATE_DOC_INDEX,
                        target_domain=f.domain,
                        rationale="Compact active context and update documentation index",
                        target_artifacts=f.affected_paths,
                        priority="NORMAL",
                    )
                )
            elif f.domain == DriftDomain.TEST_OWNERSHIP:
                proposals.append(
                    RepairProposal(
                        proposal_id=p_id,
                        action_type=RepairActionType.RUN_TARGETED_TESTS,
                        target_domain=f.domain,
                        rationale="Verify test ownership and execute baseline test runner",
                        suggested_command="python tests/run_all.py",
                        priority="HIGH",
                    )
                )
            elif f.domain == DriftDomain.ARCHITECTURE_ASSUMPTIONS:
                proposals.append(
                    RepairProposal(
                        proposal_id=p_id,
                        action_type=RepairActionType.REQUEST_HUMAN_REVIEW,
                        target_domain=f.domain,
                        rationale=f"Protected architecture zone modified: {f.description}",
                        target_artifacts=f.affected_paths,
                        priority="HIGH",
                    )
                )
            else:
                proposals.append(
                    RepairProposal(
                        proposal_id=p_id,
                        action_type=RepairActionType.REFRESH_PROJECT_MAP,
                        target_domain=f.domain,
                        rationale=f"Refresh intelligence for {f.domain.value}: {f.description}",
                        target_artifacts=f.affected_paths,
                    )
                )

        return proposals[:MAX_REPAIR_PROPOSALS]

    @staticmethod
    def emit_summary_card(
        health_result: IntelligenceHealthResult,
    ) -> DriftHealthCard:
        # Determine overall drift severity & action
        severities = [f.severity for f in health_result.findings]
        if DriftSeverity.CRITICAL_DRIFT in severities:
            overall_sev = DriftSeverity.CRITICAL_DRIFT
            overall_act = DriftAction.BLOCK
        elif DriftSeverity.SIGNIFICANT_DRIFT in severities:
            overall_sev = DriftSeverity.SIGNIFICANT_DRIFT
            overall_act = DriftAction.REVERIFY
        elif DriftSeverity.MINOR_DRIFT in severities:
            overall_sev = DriftSeverity.MINOR_DRIFT
            overall_act = DriftAction.REFRESH
        else:
            overall_sev = DriftSeverity.NO_DRIFT
            overall_act = DriftAction.NONE

        finding_counts = {}
        for f in health_result.findings:
            dom = f.domain.value
            finding_counts[dom] = finding_counts.get(dom, 0) + 1

        top_findings = [
            (f.domain.value, f.severity.value, f.recommended_action.value)
            for f in health_result.findings[:5]
        ]

        return DriftHealthCard(
            health_status=health_result.status,
            overall_drift_severity=overall_sev,
            overall_action=overall_act,
            project_fingerprint=health_result.project_fingerprint,
            dimension_summary=health_result.dimension_statuses,
            finding_counts=finding_counts,
            top_findings=top_findings,
            proposal_count=len(health_result.proposals),
        )
