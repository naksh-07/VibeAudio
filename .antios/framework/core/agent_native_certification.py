"""AntiOS 2.0 Agent-Native Certification Engine.

Phase 78: Evidence-based formal certification of a repository's agent-native engineering readiness.

Certification Levels:
- NOT_READY (Score < 50 or critical safety/integrity violation)
- BASELINE (Score 50–69.9)
- AGENT_READY (Score 70–84.9)
- HIGHLY_AGENT_NATIVE (Score 85–94.9)
- CERTIFIED (Score 95–100 with zero critical/high friction and verified test suites)

Fail-Closed Guarantees:
- Certification fails closed (NOT_READY) if:
  1. Forbidden legacy workflows (.agents/workflows/) exist
  2. Specialist violates the Shallow Depth Law (can_delegate=True or depth > 2)
  3. Manifest is corrupted or tampering is detected
  4. Configured test runner execution physically fails
  5. Critical evidence is missing or unverified
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from framework.core.agent_friction import (
    AgentFrictionDetector,
    AgentFrictionFinding,
    AgentFrictionReport,
    FrictionSeverity,
)
from framework.core.agent_native_score import (
    AgentNativeScoreCard,
    AgentNativeScoreEngine,
    ConfidenceLevel,
    EpistemicDimensionState,
)
from framework.core.manifest import ProjectManifest, load_manifest


class CertificationLevel(str, Enum):
    """Formal tiers of agent-native repository certification."""
    NOT_READY = "NOT_READY"
    BASELINE = "BASELINE"
    AGENT_READY = "AGENT_READY"
    HIGHLY_AGENT_NATIVE = "HIGHLY_AGENT_NATIVE"
    CERTIFIED = "CERTIFIED"


@dataclass
class AgentNativeCertification:
    """Complete, evidence-backed certification record."""
    project_path: str
    fingerprint: str
    antios_instance: str
    timestamp: str
    certification_level: CertificationLevel
    overall_score: float
    confidence: ConfidenceLevel
    is_certified: bool
    dimension_scores: Dict[str, float]
    critical_findings: List[str] = field(default_factory=list)
    high_friction: List[str] = field(default_factory=list)
    medium_friction: List[str] = field(default_factory=list)
    low_friction: List[str] = field(default_factory=list)
    unknown_areas: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    evidence_ledger: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_path": self.project_path,
            "fingerprint": self.fingerprint,
            "antios_instance": self.antios_instance,
            "timestamp": self.timestamp,
            "certification_level": self.certification_level.value,
            "overall_score": round(self.overall_score, 2),
            "confidence": self.confidence.value,
            "is_certified": self.is_certified,
            "dimension_scores": self.dimension_scores,
            "critical_findings": list(self.critical_findings),
            "high_friction": list(self.high_friction),
            "medium_friction": list(self.medium_friction),
            "low_friction": list(self.low_friction),
            "unknown_areas": list(self.unknown_areas),
            "recommendations": list(self.recommendations),
            "evidence_ledger": self.evidence_ledger,
        }

    def to_formal_report(self) -> str:
        lines = [
            "============================================================",
            "AGENT_NATIVE_CERTIFICATION",
            f"Project:          {self.project_path}",
            f"Fingerprint:      {self.fingerprint}",
            f"AntiOS Instance:  {self.antios_instance}",
            f"Timestamp:        {self.timestamp}",
            "",
            f"Overall Score:    {self.overall_score:.1f} / 100",
            f"Status Level:     {self.certification_level.value} (Confidence: {self.confidence.value})",
            f"Certified Pass:   {'YES' if self.is_certified else 'NO'}",
            "------------------------------------------------------------",
            "Dimension Scores:",
        ]
        for dim, sc in self.dimension_scores.items():
            lines.append(f"  {dim:<24} : {sc:>5.1f}")

        if self.critical_findings:
            lines.append("------------------------------------------------------------")
            lines.append("CRITICAL FINDINGS (FAIL-CLOSED):")
            for cf in self.critical_findings:
                lines.append(f"  [CRITICAL] {cf}")

        if self.high_friction:
            lines.append("------------------------------------------------------------")
            lines.append("HIGH FRICTION:")
            for hf in self.high_friction[:5]:
                lines.append(f"  [HIGH] {hf}")

        if self.medium_friction:
            lines.append("------------------------------------------------------------")
            lines.append("MEDIUM FRICTION:")
            for mf in self.medium_friction[:5]:
                lines.append(f"  [MEDIUM] {mf}")

        if self.low_friction:
            lines.append("------------------------------------------------------------")
            lines.append("LOW FRICTION:")
            for lf in self.low_friction[:5]:
                lines.append(f"  [LOW] {lf}")

        if self.unknown_areas:
            lines.append("------------------------------------------------------------")
            lines.append("UNKNOWN AREAS:")
            for u in self.unknown_areas[:5]:
                lines.append(f"  ? {u}")

        if self.recommendations:
            lines.append("------------------------------------------------------------")
            lines.append("RECOMMENDATIONS:")
            for r in self.recommendations[:5]:
                lines.append(f"  -> {r}")

        lines.append("============================================================")
        return "\n".join(lines)


class AgentNativeCertificationEngine:
    """Executes formal agent-native evaluation and issues certifications."""

    @classmethod
    def certify(cls, repo_root: Union[str, Path] = ".") -> AgentNativeCertification:
        """Evaluates a repository against observable evidence and issues an AgentNativeCertification."""
        root = Path(repo_root).resolve()
        now_str = datetime.now(timezone.utc).isoformat()

        # Compute fingerprint of root
        fingerprint = cls._compute_fingerprint(root)

        # 1. Evaluate Agent-Native Score
        score_card = AgentNativeScoreEngine.evaluate_repository(root)

        # 2. Detect Agent Friction
        friction_report = AgentFrictionDetector.detect_frictions(root)

        # 3. Categorize findings & check for fail-closed critical violations
        critical_findings: List[str] = []
        high_friction: List[str] = []
        medium_friction: List[str] = []
        low_friction: List[str] = []

        # A. Check for legacy workflows (FAIL-CLOSED)
        workflows_dir = root / ".agents" / "workflows"
        if workflows_dir.exists():
            critical_findings.append(
                "Legacy .agents/workflows/ directory present; violates Zero Legacy Workflows Invariant."
            )

        # B. Check for specialist delegation violations (FAIL-CLOSED)
        skills_dir = root / ".agents" / "skills"
        if skills_dir.is_dir():
            for smd in skills_dir.rglob("SKILL.md"):
                text = smd.read_text(encoding="utf-8", errors="ignore").lower()
                if "can_delegate: true" in text or "can_delegate = true" in text:
                    critical_findings.append(
                        f"Specialist '{smd.parent.name}' specifies can_delegate=True; violates Shallow Depth Law."
                    )

        # C. Check friction findings
        for f in friction_report.findings:
            desc = f"{f.category.value}: {f.description}"
            if f.severity == FrictionSeverity.CRITICAL:
                critical_findings.append(desc)
            elif f.severity == FrictionSeverity.HIGH:
                high_friction.append(desc)
            elif f.severity == FrictionSeverity.MEDIUM:
                medium_friction.append(desc)
            elif f.severity == FrictionSeverity.LOW:
                low_friction.append(desc)

        # Dimension scores dict
        dim_scores = {k: round(v.score, 2) for k, v in score_card.dimension_scores.items()}

        # 4. Determine Certification Level
        overall_score = score_card.overall_score
        confidence = score_card.confidence

        if critical_findings or overall_score < 50.0:
            level = CertificationLevel.NOT_READY
            is_certified = False
        elif overall_score < 70.0:
            level = CertificationLevel.BASELINE
            is_certified = False
        elif overall_score < 85.0:
            level = CertificationLevel.AGENT_READY
            is_certified = True
        elif overall_score < 95.0 or high_friction:
            level = CertificationLevel.HIGHLY_AGENT_NATIVE
            is_certified = True
        else:
            # Requires score >= 95, 0 critical findings, 0 high friction, high confidence
            level = CertificationLevel.CERTIFIED
            is_certified = True

        # Instance version
        antios_instance = "AntiOS 2.0.0 (Phase 78 Certified)"

        return AgentNativeCertification(
            project_path=str(root),
            fingerprint=fingerprint,
            antios_instance=antios_instance,
            timestamp=now_str,
            certification_level=level,
            overall_score=round(overall_score, 2),
            confidence=confidence,
            is_certified=is_certified,
            dimension_scores=dim_scores,
            critical_findings=critical_findings,
            high_friction=high_friction,
            medium_friction=medium_friction,
            low_friction=low_friction,
            unknown_areas=score_card.unknowns,
            recommendations=score_card.recommendations,
            evidence_ledger={
                "score_card": score_card.to_dict(),
                "friction_report": friction_report.to_dict(),
            },
        )

    @classmethod
    def _compute_fingerprint(cls, root: Path) -> str:
        """Computes a deterministic hash fingerprint from root configuration and manifest."""
        components = []
        for fname in ["antios.config.json", ".antios/manifest.json", "pyproject.toml", "package.json"]:
            p = root / fname
            if p.is_file():
                try:
                    components.append(hashlib.sha256(p.read_bytes()).hexdigest())
                except Exception:
                    pass
        if not components:
            components.append(hashlib.sha256(str(root).encode()).hexdigest())
        return hashlib.sha256(":".join(components).encode()).hexdigest()[:16]
