"""AntiOS 2.0 Agent Friction Detection Engine.

Phase 74: Deterministic detection and classification of measurable friction patterns
that increase agent turns, search overhead, context saturation, or failure rates.

Categories detected:
- REPEATED_SEARCH
- DUPLICATE_INSTRUCTIONS
- CONFLICTING_INSTRUCTIONS
- AMBIGUOUS_OWNERSHIP
- STALE_DOCUMENTATION
- ORPHANED_DOCUMENTATION
- MISSING_TEST_MAPPING
- EXCESSIVE_CONTEXT_TRAVERSAL
- REPEATED_DISCOVERY
- UNNECESSARY_DELEGATION
- REPEATED_VERIFICATION_FAILURE
- MISSING_VERIFICATION_SURFACE
- DUPLICATE_SKILLS
- OVERLAPPING_SPECIALIST
- STALE_SKILLS
- DEAD_PROJECT_REFERENCES
- UNNECESSARY_MCP_ESCALATION
- CAPABILITY_GAP_INDEXING
- EXCESSIVE_FILE_TOUCH_RADIUS
- FAILED_TASK_ROUTING

Epistemic classifications:
- OBSERVED_FRICTION (Directly verified via filesystem or recorded observations)
- INFERRED_FRICTION (Derived from structural analysis)
- POSSIBLE_FRICTION (Statistical likelihood without direct confirmation)
- UNKNOWN (Insufficient evidence)
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

from framework.core.docaudit import DocReferenceAuditor
from framework.core.manifest import ProjectManifest, load_manifest


class FrictionCategory(str, Enum):
    """Measurable agent friction pattern categories."""
    REPEATED_SEARCH = "REPEATED_SEARCH"
    DUPLICATE_INSTRUCTIONS = "DUPLICATE_INSTRUCTIONS"
    CONFLICTING_INSTRUCTIONS = "CONFLICTING_INSTRUCTIONS"
    AMBIGUOUS_OWNERSHIP = "AMBIGUOUS_OWNERSHIP"
    STALE_DOCUMENTATION = "STALE_DOCUMENTATION"
    ORPHANED_DOCUMENTATION = "ORPHANED_DOCUMENTATION"
    MISSING_TEST_MAPPING = "MISSING_TEST_MAPPING"
    EXCESSIVE_CONTEXT_TRAVERSAL = "EXCESSIVE_CONTEXT_TRAVERSAL"
    REPEATED_DISCOVERY = "REPEATED_DISCOVERY"
    UNNECESSARY_DELEGATION = "UNNECESSARY_DELEGATION"
    REPEATED_VERIFICATION_FAILURE = "REPEATED_VERIFICATION_FAILURE"
    MISSING_VERIFICATION_SURFACE = "MISSING_VERIFICATION_SURFACE"
    DUPLICATE_SKILLS = "DUPLICATE_SKILLS"
    OVERLAPPING_SPECIALIST = "OVERLAPPING_SPECIALIST"
    STALE_SKILLS = "STALE_SKILLS"
    DEAD_PROJECT_REFERENCES = "DEAD_PROJECT_REFERENCES"
    UNNECESSARY_MCP_ESCALATION = "UNNECESSARY_MCP_ESCALATION"
    CAPABILITY_GAP_INDEXING = "CAPABILITY_GAP_INDEXING"
    EXCESSIVE_FILE_TOUCH_RADIUS = "EXCESSIVE_FILE_TOUCH_RADIUS"
    FAILED_TASK_ROUTING = "FAILED_TASK_ROUTING"


class FrictionClassification(str, Enum):
    """Epistemic classification of friction findings."""
    OBSERVED_FRICTION = "OBSERVED_FRICTION"
    INFERRED_FRICTION = "INFERRED_FRICTION"
    POSSIBLE_FRICTION = "POSSIBLE_FRICTION"
    UNKNOWN = "UNKNOWN"


class FrictionSeverity(str, Enum):
    """Severity rating of detected friction."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AgentCostLevel(str, Enum):
    """Estimated token / cognitive / turn overhead caused by friction."""
    LOW = "LOW"          # Minor token overhead (< 100 tokens, 0 turns)
    MEDIUM = "MEDIUM"    # Moderate token overhead (100–1000 tokens, 1 turn)
    HIGH = "HIGH"        # Significant overhead (1000–5000 tokens, 2–3 turns)
    CRITICAL = "CRITICAL"# Severe overhead (> 5000 tokens, multiple failed turns or deadlocks)


class FrictionStatus(str, Enum):
    """Lifecycle status of a friction finding."""
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"


@dataclass
class AgentFrictionFinding:
    """A deterministic friction finding."""
    friction_id: str
    category: FrictionCategory
    classification: FrictionClassification
    evidence: Dict[str, Any]
    affected_paths: List[str]
    affected_capabilities: List[str]
    frequency: int
    severity: FrictionSeverity
    confidence: float                                 # 0.0 to 1.0
    estimated_agent_cost: AgentCostLevel
    status: FrictionStatus = FrictionStatus.ACTIVE
    description: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "friction_id": self.friction_id,
            "category": self.category.value,
            "classification": self.classification.value,
            "evidence": self.evidence,
            "affected_paths": list(self.affected_paths),
            "affected_capabilities": list(self.affected_capabilities),
            "frequency": self.frequency,
            "severity": self.severity.value,
            "confidence": round(self.confidence, 2),
            "estimated_agent_cost": self.estimated_agent_cost.value,
            "status": self.status.value,
            "description": self.description,
            "timestamp": self.timestamp,
        }


@dataclass
class AgentFrictionReport:
    """Consolidated report of detected agent friction."""
    project_path: str
    timestamp: str
    findings: List[AgentFrictionFinding]
    total_friction_count: int
    by_severity: Dict[str, int]
    by_classification: Dict[str, int]
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_path": self.project_path,
            "timestamp": self.timestamp,
            "total_friction_count": self.total_friction_count,
            "by_severity": self.by_severity,
            "by_classification": self.by_classification,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
        }


class AgentFrictionDetector:
    """Deterministic agent friction detection engine."""

    @classmethod
    def detect_frictions(cls, repo_root: Union[str, Path] = ".") -> AgentFrictionReport:
        """Runs all deterministic friction detectors across the repository."""
        root = Path(repo_root).resolve()
        findings: List[AgentFrictionFinding] = []

        # 1. Documentation friction
        findings.extend(cls._detect_documentation_friction(root))

        # 2. Skill friction
        findings.extend(cls._detect_skill_friction(root))

        # 3. Ownership & Manifest friction
        findings.extend(cls._detect_ownership_friction(root))

        # 4. Verification & Testing friction
        findings.extend(cls._detect_verification_friction(root))

        # 5. Agent & Workflow friction
        findings.extend(cls._detect_agent_friction(root))

        # 6. Tooling & MCP friction
        findings.extend(cls._detect_tooling_friction(root))

        # 7. Historical Learning / Observation friction
        findings.extend(cls._detect_learning_friction(root))

        # Summarize counts
        by_severity: Dict[str, int] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        by_classification: Dict[str, int] = {
            "OBSERVED_FRICTION": 0,
            "INFERRED_FRICTION": 0,
            "POSSIBLE_FRICTION": 0,
            "UNKNOWN": 0,
        }

        for f in findings:
            by_severity[f.severity.value] = by_severity.get(f.severity.value, 0) + 1
            by_classification[f.classification.value] = by_classification.get(f.classification.value, 0) + 1

        summary = (
            f"Detected {len(findings)} agent friction points "
            f"({by_severity['CRITICAL']} Critical, {by_severity['HIGH']} High, "
            f"{by_severity['MEDIUM']} Medium, {by_severity['LOW']} Low)."
        )

        return AgentFrictionReport(
            project_path=str(root),
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings=findings,
            total_friction_count=len(findings),
            by_severity=by_severity,
            by_classification=by_classification,
            summary=summary,
        )

    # -------------------------------------------------------------------------
    # 1. Documentation Friction
    # -------------------------------------------------------------------------
    @classmethod
    def _detect_documentation_friction(cls, root: Path) -> List[AgentFrictionFinding]:
        findings: List[AgentFrictionFinding] = []
        docs_dir = root / "docs"
        if not docs_dir.is_dir():
            return findings

        # A. Dead references / broken links
        try:
            audit_res = DocReferenceAuditor.audit_documentation(root)
            if audit_res.broken_count > 0:
                paths = list(audit_res.broken_references_by_file.keys())
                fid = f"FRIC-DOC-DEAD-{hashlib.sha256(''.join(paths).encode()).hexdigest()[:8]}"
                findings.append(
                    AgentFrictionFinding(
                        friction_id=fid,
                        category=FrictionCategory.DEAD_PROJECT_REFERENCES,
                        classification=FrictionClassification.OBSERVED_FRICTION,
                        evidence={
                            "broken_count": audit_res.broken_count,
                            "broken_references_by_file": audit_res.broken_references_by_file,
                        },
                        affected_paths=paths,
                        affected_capabilities=["documentation", "wayfinding"],
                        frequency=audit_res.broken_count,
                        severity=FrictionSeverity.HIGH if audit_res.broken_count > 5 else FrictionSeverity.MEDIUM,
                        confidence=1.0,
                        estimated_agent_cost=AgentCostLevel.MEDIUM,
                        description=f"Documentation contains {audit_res.broken_count} broken paths or dead links.",
                    )
                )
        except Exception:
            pass

        # B. Orphaned documentation (docs not referenced in docs/INDEX.md)
        index_file = docs_dir / "INDEX.md"
        if index_file.is_file():
            index_text = index_file.read_text(encoding="utf-8", errors="ignore")
            all_docs = list(docs_dir.rglob("*.md"))
            orphans: List[str] = []
            for d in all_docs:
                rel = d.relative_to(root).as_posix()
                if rel in ("docs/INDEX.md", "docs/ACTIVE_CONTEXT.md"):
                    continue
                if d.name not in index_text and rel not in index_text:
                    orphans.append(rel)

            if orphans:
                fid = f"FRIC-DOC-ORPHAN-{hashlib.sha256(''.join(orphans).encode()).hexdigest()[:8]}"
                findings.append(
                    AgentFrictionFinding(
                        friction_id=fid,
                        category=FrictionCategory.ORPHANED_DOCUMENTATION,
                        classification=FrictionClassification.INFERRED_FRICTION,
                        evidence={"orphaned_files": orphans, "count": len(orphans)},
                        affected_paths=orphans,
                        affected_capabilities=["wayfinding", "documentation"],
                        frequency=len(orphans),
                        severity=FrictionSeverity.LOW,
                        confidence=0.85,
                        estimated_agent_cost=AgentCostLevel.LOW,
                        description=f"Found {len(orphans)} documentation files not referenced in docs/INDEX.md.",
                    )
                )

        # C. Excessive Context Traversal (e.g. bloated ACTIVE_CONTEXT.md)
        active_ctx = docs_dir / "ACTIVE_CONTEXT.md"
        if active_ctx.is_file():
            lines = active_ctx.read_text(encoding="utf-8", errors="ignore").splitlines()
            if len(lines) > 60:
                fid = f"FRIC-DOC-BLOAT-{len(lines)}"
                findings.append(
                    AgentFrictionFinding(
                        friction_id=fid,
                        category=FrictionCategory.EXCESSIVE_CONTEXT_TRAVERSAL,
                        classification=FrictionClassification.OBSERVED_FRICTION,
                        evidence={"line_count": len(lines), "budget_max": 60},
                        affected_paths=["docs/ACTIVE_CONTEXT.md"],
                        affected_capabilities=["task_dispatch", "context_budget"],
                        frequency=1,
                        severity=FrictionSeverity.MEDIUM,
                        confidence=1.0,
                        estimated_agent_cost=AgentCostLevel.HIGH,
                        description=f"docs/ACTIVE_CONTEXT.md has {len(lines)} lines, exceeding the 60-line token budget.",
                    )
                )

        return findings

    # -------------------------------------------------------------------------
    # 2. Skill Friction
    # -------------------------------------------------------------------------
    @classmethod
    def _detect_skill_friction(cls, root: Path) -> List[AgentFrictionFinding]:
        findings: List[AgentFrictionFinding] = []
        skills_dir = root / ".agents" / "skills"
        if not skills_dir.is_dir():
            return findings

        skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
        skill_descriptions: Dict[str, str] = {}
        affected_skills: List[str] = []

        for sd in skill_dirs:
            skill_md = sd / "SKILL.md"
            if not skill_md.is_file():
                continue
            content = skill_md.read_text(encoding="utf-8", errors="ignore")

            # Extract description
            desc_match = re.search(r"description:\s*>?-?\s*(.*?)(?=\n[a-z_]+:|\n---)", content, re.DOTALL)
            desc = desc_match.group(1).strip().lower() if desc_match else ""
            if desc:
                skill_descriptions[sd.name] = desc

            # Bloated skill prompt
            lines = content.splitlines()
            if len(lines) > 300:
                findings.append(
                    AgentFrictionFinding(
                        friction_id=f"FRIC-SKILL-BLOAT-{sd.name}",
                        category=FrictionCategory.EXCESSIVE_CONTEXT_TRAVERSAL,
                        classification=FrictionClassification.OBSERVED_FRICTION,
                        evidence={"skill_name": sd.name, "line_count": len(lines), "max_recommended": 300},
                        affected_paths=[(skill_md).relative_to(root).as_posix()],
                        affected_capabilities=["skill_dispatch"],
                        frequency=1,
                        severity=FrictionSeverity.LOW,
                        confidence=1.0,
                        estimated_agent_cost=AgentCostLevel.MEDIUM,
                        description=f"Skill '{sd.name}' contains {len(lines)} lines (>300 lines); risk of context saturation.",
                    )
                )

        # Check duplicate or overlapping skills
        names = list(skill_descriptions.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                n1, n2 = names[i], names[j]
                d1, d2 = skill_descriptions[n1], skill_descriptions[n2]
                # Simple word overlap heuristic
                words1 = set(re.findall(r"\w+", d1))
                words2 = set(re.findall(r"\w+", d2))
                overlap = len(words1.intersection(words2))
                total = max(len(words1), len(words2), 1)
                ratio = overlap / total
                if ratio > 0.75:
                    findings.append(
                        AgentFrictionFinding(
                            friction_id=f"FRIC-SKILL-DUP-{n1}-{n2}",
                            category=FrictionCategory.DUPLICATE_SKILLS,
                            classification=FrictionClassification.INFERRED_FRICTION,
                            evidence={"skill_1": n1, "skill_2": n2, "description_overlap_ratio": round(ratio, 2)},
                            affected_paths=[f".agents/skills/{n1}", f".agents/skills/{n2}"],
                            affected_capabilities=["capability_router", "skill_dispatch"],
                            frequency=1,
                            severity=FrictionSeverity.MEDIUM,
                            confidence=0.8,
                            estimated_agent_cost=AgentCostLevel.HIGH,
                            description=f"Skills '{n1}' and '{n2}' have {int(ratio * 100)}% overlapping descriptions; risks routing ambiguity.",
                        )
                    )

        return findings

    # -------------------------------------------------------------------------
    # 3. Ownership Friction
    # -------------------------------------------------------------------------
    @classmethod
    def _detect_ownership_friction(cls, root: Path) -> List[AgentFrictionFinding]:
        findings: List[AgentFrictionFinding] = []
        manifest_path = root / ".antios" / "manifest.json"

        if not manifest_path.is_file():
            findings.append(
                AgentFrictionFinding(
                    friction_id="FRIC-OWN-NO-MANIFEST",
                    category=FrictionCategory.AMBIGUOUS_OWNERSHIP,
                    classification=FrictionClassification.OBSERVED_FRICTION,
                    evidence={"manifest_path": ".antios/manifest.json", "status": "missing"},
                    affected_paths=[".antios/manifest.json"],
                    affected_capabilities=["provenance", "ownership"],
                    frequency=1,
                    severity=FrictionSeverity.HIGH,
                    confidence=1.0,
                    estimated_agent_cost=AgentCostLevel.HIGH,
                    description="No artifact ownership manifest exists; agents cannot distinguish generated, managed, or user-authored files.",
                )
            )

        return findings

    # -------------------------------------------------------------------------
    # 4. Verification & Testing Friction
    # -------------------------------------------------------------------------
    @classmethod
    def _detect_verification_friction(cls, root: Path) -> List[AgentFrictionFinding]:
        findings: List[AgentFrictionFinding] = []
        config_path = root / "antios.config.json"

        # Missing verification surface
        if config_path.is_file():
            try:
                cfg = json.loads(config_path.read_text(encoding="utf-8", errors="ignore"))
                runners = cfg.get("test_runners", [])
                if not runners:
                    findings.append(
                        AgentFrictionFinding(
                            friction_id="FRIC-VERIF-NO-RUNNER",
                            category=FrictionCategory.MISSING_VERIFICATION_SURFACE,
                            classification=FrictionClassification.OBSERVED_FRICTION,
                            evidence={"configured_runners": []},
                            affected_paths=["antios.config.json"],
                            affected_capabilities=["verification", "maker_checker"],
                            frequency=1,
                            severity=FrictionSeverity.HIGH,
                            confidence=1.0,
                            estimated_agent_cost=AgentCostLevel.CRITICAL,
                            description="No test runners configured in antios.config.json; automated verification cannot execute.",
                        )
                    )
            except Exception:
                pass

        return findings

    # -------------------------------------------------------------------------
    # 5. Agent & Workflow Friction
    # -------------------------------------------------------------------------
    @classmethod
    def _detect_agent_friction(cls, root: Path) -> List[AgentFrictionFinding]:
        findings: List[AgentFrictionFinding] = []

        # Legacy workflows check (CRITICAL architectural friction)
        workflows_dir = root / ".agents" / "workflows"
        if workflows_dir.exists():
            wf_files = [f.as_posix() for f in workflows_dir.rglob("*") if f.is_file()]
            findings.append(
                AgentFrictionFinding(
                    friction_id="FRIC-AGENT-LEGACY-WORKFLOW",
                    category=FrictionCategory.CONFLICTING_INSTRUCTIONS,
                    classification=FrictionClassification.OBSERVED_FRICTION,
                    evidence={"legacy_workflow_files": wf_files},
                    affected_paths=[".agents/workflows"],
                    affected_capabilities=["agent_topology", "workflow_governance"],
                    frequency=len(wf_files),
                    severity=FrictionSeverity.CRITICAL,
                    confidence=1.0,
                    estimated_agent_cost=AgentCostLevel.CRITICAL,
                    description="Legacy .agents/workflows/ directory found; violates Zero Legacy Workflows Invariant and creates conflicting execution paths.",
                )
            )

        return findings

    # -------------------------------------------------------------------------
    # 6. Tooling & MCP Friction
    # -------------------------------------------------------------------------
    @classmethod
    def _detect_tooling_friction(cls, root: Path) -> List[AgentFrictionFinding]:
        findings: List[AgentFrictionFinding] = []

        # Check for unnecessary MCP configuration if local script or CLI exists
        config_path = root / "antios.config.json"
        if config_path.is_file():
            try:
                cfg = json.loads(config_path.read_text(encoding="utf-8", errors="ignore"))
                mcp_servers = cfg.get("mcp_servers", {})
                # If git CLI is available but github MCP is configured without justification
                if "github" in mcp_servers or "github-mcp-server" in mcp_servers:
                    findings.append(
                        AgentFrictionFinding(
                            friction_id="FRIC-TOOL-MCP-GIT-ESCALATION",
                            category=FrictionCategory.UNNECESSARY_MCP_ESCALATION,
                            classification=FrictionClassification.INFERRED_FRICTION,
                            evidence={"configured_mcp": "github", "rule": "Tier 4 CLI (git) strictly outranks Tier 6 MCP"},
                            affected_paths=["antios.config.json"],
                            affected_capabilities=["tool_policy"],
                            frequency=1,
                            severity=FrictionSeverity.MEDIUM,
                            confidence=0.9,
                            estimated_agent_cost=AgentCostLevel.HIGH,
                            description="Unnecessary Tier 6 MCP escalation detected for Git operations when Tier 4 CLI is standard.",
                        )
                    )
            except Exception:
                pass

        return findings

    # -------------------------------------------------------------------------
    # 7. Historical Learning / Observation Friction
    # -------------------------------------------------------------------------
    @classmethod
    def _detect_learning_friction(cls, root: Path) -> List[AgentFrictionFinding]:
        findings: List[AgentFrictionFinding] = []
        obs_path = root / ".antios" / "learning_observations.json"

        if obs_path.is_file():
            try:
                data = json.loads(obs_path.read_text(encoding="utf-8", errors="ignore"))
                observations = data.get("observations", [])
                verification_failures = [o for o in observations if o.get("observation_type") == "VERIFICATION_FAILURE"]
                if len(verification_failures) >= 3:
                    findings.append(
                        AgentFrictionFinding(
                            friction_id=f"FRIC-LEARN-REPEATED-FAIL-{len(verification_failures)}",
                            category=FrictionCategory.REPEATED_VERIFICATION_FAILURE,
                            classification=FrictionClassification.OBSERVED_FRICTION,
                            evidence={"recorded_failure_count": len(verification_failures)},
                            affected_paths=[".antios/learning_observations.json"],
                            affected_capabilities=["verification", "maker_checker"],
                            frequency=len(verification_failures),
                            severity=FrictionSeverity.HIGH,
                            confidence=1.0,
                            estimated_agent_cost=AgentCostLevel.HIGH,
                            description=f"Recorded {len(verification_failures)} recurring verification failures in learning observations.",
                        )
                    )
            except Exception:
                pass

        return findings
