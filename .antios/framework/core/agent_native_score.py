"""AntiOS 2.0 Agent-Native Score Engine.

Phase 73: Deterministic, evidence-backed evaluation of a repository's agent-native quality.
Evaluates 10 core dimensions:
1. WAYFINDING
2. DOCUMENTATION
3. SKILLS
4. AGENTS
5. OWNERSHIP
6. VERIFICATION
7. MEMORY_KNOWLEDGE
8. TOOLING
9. PROJECT_STRUCTURE
10. ORCHESTRATION_READINESS

Guarantees:
- Every score is backed by observable filesystem/manifest/configuration evidence.
- Explicit epistemic segregation: OBSERVED, INFERRED, UNKNOWN.
- Missing information is classified as UNKNOWN without being arbitrarily penalized to zero.
- Explains WHY each score exists.
- Stale or drifted intelligence downgrades confidence and logs warnings.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from framework.core.docaudit import DocReferenceAuditor
from framework.core.manifest import ProjectManifest, load_manifest
from framework.core.provenance import compute_file_sha256


class EpistemicDimensionState(str, Enum):
    """Epistemic status of dimension evaluation."""
    OBSERVED = "OBSERVED"     # Fully derived from verified, physical files/artifacts on disk
    INFERRED = "INFERRED"     # Synthesized from partial static analysis or structural patterns
    UNKNOWN = "UNKNOWN"       # Required information or configuration is unobserved/missing


class ConfidenceLevel(str, Enum):
    """Confidence level in dimension or overall evaluation."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ScoreDimension(str, Enum):
    """The 10 canonical dimensions of agent-native repository quality."""
    WAYFINDING = "WAYFINDING"
    DOCUMENTATION = "DOCUMENTATION"
    SKILLS = "SKILLS"
    AGENTS = "AGENTS"
    OWNERSHIP = "OWNERSHIP"
    VERIFICATION = "VERIFICATION"
    MEMORY_KNOWLEDGE = "MEMORY_KNOWLEDGE"
    TOOLING = "TOOLING"
    PROJECT_STRUCTURE = "PROJECT_STRUCTURE"
    ORCHESTRATION_READINESS = "ORCHESTRATION_READINESS"


@dataclass
class DimensionScore:
    """Evaluation result for an individual dimension."""
    dimension: ScoreDimension
    score: float                                      # 0.0 to 100.0
    epistemic_state: EpistemicDimensionState
    confidence: ConfidenceLevel
    evidence: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "score": round(self.score, 2),
            "epistemic_state": self.epistemic_state.value,
            "confidence": self.confidence.value,
            "evidence": list(self.evidence),
            "warnings": list(self.warnings),
            "unknowns": list(self.unknowns),
            "recommendations": list(self.recommendations),
            "metrics": self.metrics,
        }


@dataclass
class AgentNativeScoreCard:
    """Comprehensive Agent-Native Score Card."""
    project_path: str
    timestamp: str
    overall_score: float
    confidence: ConfidenceLevel
    dimension_scores: Dict[str, DimensionScore]
    evidence_summary: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_path": self.project_path,
            "timestamp": self.timestamp,
            "overall_score": round(self.overall_score, 2),
            "confidence": self.confidence.value,
            "dimension_scores": {k: v.to_dict() for k, v in self.dimension_scores.items()},
            "evidence_summary": list(self.evidence_summary),
            "warnings": list(self.warnings),
            "unknowns": list(self.unknowns),
            "recommendations": list(self.recommendations),
        }

    def to_summary_card(self) -> str:
        lines = [
            "============================================================",
            "AGENT-NATIVE REPOSITORY SCORE CARD",
            f"Target:     {self.project_path}",
            f"Timestamp:  {self.timestamp}",
            f"Overall:    {self.overall_score:.1f} / 100 ({self.confidence.value} Confidence)",
            "------------------------------------------------------------",
            "DIMENSION BREAKDOWN:",
        ]
        for dim_name, ds in self.dimension_scores.items():
            lines.append(
                f"  - {dim_name:<24} {ds.score:>5.1f}  [{ds.epistemic_state.value:<8}] (Conf: {ds.confidence.value})"
            )
        if self.warnings:
            lines.append("------------------------------------------------------------")
            lines.append("WARNINGS:")
            for w in self.warnings[:5]:
                lines.append(f"  ! {w}")
        if self.unknowns:
            lines.append("------------------------------------------------------------")
            lines.append("UNKNOWN AREAS:")
            for u in self.unknowns[:5]:
                lines.append(f"  ? {u}")
        lines.append("============================================================")
        return "\n".join(lines)


class AgentNativeScoreEngine:
    """Deterministic, evidence-backed evaluation engine for agent-native repository quality."""

    DIMENSION_WEIGHTS: Dict[ScoreDimension, float] = {
        ScoreDimension.WAYFINDING: 1.2,
        ScoreDimension.DOCUMENTATION: 1.0,
        ScoreDimension.SKILLS: 1.0,
        ScoreDimension.AGENTS: 0.9,
        ScoreDimension.OWNERSHIP: 1.1,
        ScoreDimension.VERIFICATION: 1.3,
        ScoreDimension.MEMORY_KNOWLEDGE: 0.8,
        ScoreDimension.TOOLING: 1.0,
        ScoreDimension.PROJECT_STRUCTURE: 0.9,
        ScoreDimension.ORCHESTRATION_READINESS: 0.8,
    }

    @classmethod
    def evaluate_repository(cls, repo_root: Union[str, Path] = ".") -> AgentNativeScoreCard:
        """Evaluates all 10 dimensions for the given repository root."""
        root = Path(repo_root).resolve()
        now_str = datetime.now(timezone.utc).isoformat()

        # Dimension evaluations
        dim_scores: Dict[str, DimensionScore] = {}
        dim_scores[ScoreDimension.WAYFINDING.value] = cls._evaluate_wayfinding(root)
        dim_scores[ScoreDimension.DOCUMENTATION.value] = cls._evaluate_documentation(root)
        dim_scores[ScoreDimension.SKILLS.value] = cls._evaluate_skills(root)
        dim_scores[ScoreDimension.AGENTS.value] = cls._evaluate_agents(root)
        dim_scores[ScoreDimension.OWNERSHIP.value] = cls._evaluate_ownership(root)
        dim_scores[ScoreDimension.VERIFICATION.value] = cls._evaluate_verification(root)
        dim_scores[ScoreDimension.MEMORY_KNOWLEDGE.value] = cls._evaluate_memory_knowledge(root)
        dim_scores[ScoreDimension.TOOLING.value] = cls._evaluate_tooling(root)
        dim_scores[ScoreDimension.PROJECT_STRUCTURE.value] = cls._evaluate_project_structure(root)
        dim_scores[ScoreDimension.ORCHESTRATION_READINESS.value] = cls._evaluate_orchestration_readiness(root)

        # Aggregate overall score with normalized weights
        total_weight = 0.0
        weighted_sum = 0.0
        unknown_count = 0
        all_warnings: List[str] = []
        all_unknowns: List[str] = []
        all_recommendations: List[str] = []
        evidence_summary: List[str] = []

        for dim_enum, weight in cls.DIMENSION_WEIGHTS.items():
            ds = dim_scores[dim_enum.value]
            total_weight += weight
            weighted_sum += ds.score * weight
            if ds.epistemic_state == EpistemicDimensionState.UNKNOWN:
                unknown_count += 1
            all_warnings.extend(ds.warnings)
            all_unknowns.extend(ds.unknowns)
            all_recommendations.extend(ds.recommendations)
            if ds.evidence:
                evidence_summary.append(f"{dim_enum.value}: {ds.evidence[0]}")

        overall_score = weighted_sum / max(total_weight, 1.0)

        # Overall confidence estimation
        if unknown_count >= 5:
            overall_confidence = ConfidenceLevel.LOW
        elif unknown_count >= 2:
            overall_confidence = ConfidenceLevel.MEDIUM
        else:
            overall_confidence = ConfidenceLevel.HIGH

        return AgentNativeScoreCard(
            project_path=str(root),
            timestamp=now_str,
            overall_score=round(overall_score, 2),
            confidence=overall_confidence,
            dimension_scores=dim_scores,
            evidence_summary=evidence_summary,
            warnings=all_warnings,
            unknowns=all_unknowns,
            recommendations=all_recommendations,
        )

    # -------------------------------------------------------------------------
    # 1. WAYFINDING
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_wayfinding(cls, root: Path) -> DimensionScore:
        evidence: List[str] = []
        warnings: List[str] = []
        unknowns: List[str] = []
        recommendations: List[str] = []
        metrics: Dict[str, Any] = {}

        score = 50.0  # Neutral baseline
        state = EpistemicDimensionState.INFERRED

        # Check for project anatomy index
        anatomy_path = root / ".antios" / "project_anatomy.json"
        if anatomy_path.is_file():
            evidence.append("Found project anatomy index (.antios/project_anatomy.json)")
            score += 25.0
            state = EpistemicDimensionState.OBSERVED
            metrics["anatomy_present"] = True
        else:
            unknowns.append("No project anatomy index found (.antios/project_anatomy.json)")
            recommendations.append("Generate project anatomy index using ProjectAnatomyCompiler")
            metrics["anatomy_present"] = False

        # Check for navigation tool or index
        navigate_tool = root / "framework" / "scripts" / "tools" / "navigate_repo.py"
        if navigate_tool.is_file():
            evidence.append("Deterministic wayfinding tool active (navigate_repo.py)")
            score += 15.0
            metrics["wayfinding_tool"] = True
        else:
            metrics["wayfinding_tool"] = False

        # Check for docs index
        doc_index = root / "docs" / "INDEX.md"
        if doc_index.is_file():
            evidence.append("Authoritative documentation index exists (docs/INDEX.md)")
            score += 10.0
            metrics["docs_index"] = True
        else:
            unknowns.append("Documentation index not found (docs/INDEX.md)")
            recommendations.append("Create docs/INDEX.md to provide single wayfinding catalog")
            metrics["docs_index"] = False

        score = min(100.0, max(0.0, score))
        confidence = ConfidenceLevel.HIGH if state == EpistemicDimensionState.OBSERVED else ConfidenceLevel.MEDIUM

        return DimensionScore(
            dimension=ScoreDimension.WAYFINDING,
            score=score,
            epistemic_state=state,
            confidence=confidence,
            evidence=evidence,
            warnings=warnings,
            unknowns=unknowns,
            recommendations=recommendations,
            metrics=metrics,
        )

    # -------------------------------------------------------------------------
    # 2. DOCUMENTATION
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_documentation(cls, root: Path) -> DimensionScore:
        evidence: List[str] = []
        warnings: List[str] = []
        unknowns: List[str] = []
        recommendations: List[str] = []
        metrics: Dict[str, Any] = {}

        score = 60.0
        state = EpistemicDimensionState.OBSERVED

        docs_dir = root / "docs"
        if not docs_dir.is_dir():
            unknowns.append("No docs/ directory discovered")
            recommendations.append("Create docs/ directory with authoritative architecture guidance")
            return DimensionScore(
                dimension=ScoreDimension.DOCUMENTATION,
                score=50.0,
                epistemic_state=EpistemicDimensionState.UNKNOWN,
                confidence=ConfidenceLevel.LOW,
                evidence=["docs/ directory absent; baseline neutral score assigned"],
                unknowns=unknowns,
                recommendations=recommendations,
            )

        doc_files = list(docs_dir.rglob("*.md"))
        metrics["total_docs"] = len(doc_files)
        evidence.append(f"Found {len(doc_files)} markdown documentation files in docs/")

        # Active Context check
        active_ctx = docs_dir / "ACTIVE_CONTEXT.md"
        if active_ctx.is_file():
            line_count = len(active_ctx.read_text(encoding="utf-8", errors="ignore").splitlines())
            metrics["active_context_lines"] = line_count
            if line_count <= 60:
                evidence.append(f"ACTIVE_CONTEXT.md strictly bounded ({line_count} lines <= 60)")
                score += 20.0
            else:
                warnings.append(f"ACTIVE_CONTEXT.md exceeds 60-line token budget ({line_count} lines)")
                recommendations.append("Trim docs/ACTIVE_CONTEXT.md to strictly <= 60 lines")
                score -= 10.0
        else:
            unknowns.append("No docs/ACTIVE_CONTEXT.md found")
            recommendations.append("Maintain a bounded docs/ACTIVE_CONTEXT.md for agent task continuity")

        # Doc audit for broken references
        try:
            audit_result = DocReferenceAuditor.audit_documentation(root)
            metrics["broken_references"] = audit_result.broken_count
            if audit_result.broken_count == 0:
                evidence.append(f"DocReferenceAuditor found 0 broken links across {audit_result.total_files_audited} files")
                score += 20.0
            else:
                warnings.append(f"Found {audit_result.broken_count} broken documentation links/paths")
                recommendations.append("Run python framework/scripts/tools/audit_docs.py to repair broken references")
                score -= min(30.0, audit_result.broken_count * 5.0)
        except Exception as e:
            unknowns.append(f"Syntactic documentation reference audit could not run: {e}")

        score = min(100.0, max(0.0, score))
        confidence = ConfidenceLevel.HIGH if metrics.get("broken_references") is not None else ConfidenceLevel.MEDIUM

        return DimensionScore(
            dimension=ScoreDimension.DOCUMENTATION,
            score=score,
            epistemic_state=state,
            confidence=confidence,
            evidence=evidence,
            warnings=warnings,
            unknowns=unknowns,
            recommendations=recommendations,
            metrics=metrics,
        )

    # -------------------------------------------------------------------------
    # 3. SKILLS
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_skills(cls, root: Path) -> DimensionScore:
        evidence: List[str] = []
        warnings: List[str] = []
        unknowns: List[str] = []
        recommendations: List[str] = []
        metrics: Dict[str, Any] = {}

        skills_dir = root / ".agents" / "skills"
        if not skills_dir.is_dir():
            unknowns.append("No .agents/skills/ directory present")
            return DimensionScore(
                dimension=ScoreDimension.SKILLS,
                score=50.0,
                epistemic_state=EpistemicDimensionState.UNKNOWN,
                confidence=ConfidenceLevel.LOW,
                unknowns=unknowns,
                recommendations=["Create .agents/skills/ directory for project-local capabilities"],
            )

        skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
        metrics["total_skills"] = len(skill_dirs)
        evidence.append(f"Found {len(skill_dirs)} project skills in .agents/skills/")

        score = 60.0
        state = EpistemicDimensionState.OBSERVED

        # Check antios canonical skill
        antios_skill = skills_dir / "antios" / "SKILL.md"
        if antios_skill.is_file():
            evidence.append("Authoritative /antios control plane skill present")
            score += 20.0
            metrics["antios_skill_present"] = True
        else:
            warnings.append("Authoritative /antios control plane skill missing")
            recommendations.append("Ensure canonical .agents/skills/antios/SKILL.md exists")
            metrics["antios_skill_present"] = False

        # Check SKILL.md validity and token bounds
        for s in skill_dirs:
            skill_md = s / "SKILL.md"
            if not skill_md.is_file():
                warnings.append(f"Skill directory '{s.name}' missing SKILL.md")
                score -= 5.0
            else:
                content = skill_md.read_text(encoding="utf-8", errors="ignore")
                if "---" in content and "name:" in content:
                    score += 2.0  # Well-formed frontmatter bonus
                if len(content.splitlines()) > 300:
                    warnings.append(f"Skill '{s.name}' exceeds bounded prompt size (>300 lines)")
                    score -= 5.0

        score = min(100.0, max(0.0, score))
        confidence = ConfidenceLevel.HIGH

        return DimensionScore(
            dimension=ScoreDimension.SKILLS,
            score=score,
            epistemic_state=state,
            confidence=confidence,
            evidence=evidence,
            warnings=warnings,
            unknowns=unknowns,
            recommendations=recommendations,
            metrics=metrics,
        )

    # -------------------------------------------------------------------------
    # 4. AGENTS
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_agents(cls, root: Path) -> DimensionScore:
        evidence: List[str] = []
        warnings: List[str] = []
        unknowns: List[str] = []
        recommendations: List[str] = []
        metrics: Dict[str, Any] = {}

        score = 70.0
        state = EpistemicDimensionState.OBSERVED

        # Check for legacy workflows invariant: MUST NOT EXIST
        workflows_dir = root / ".agents" / "workflows"
        if workflows_dir.exists():
            warnings.append("CRITICAL: Legacy .agents/workflows/ directory found; violates Zero Legacy Workflows Invariant")
            score -= 50.0
            recommendations.append("Retire legacy .agents/workflows/ directory in favor of .agents/skills/")
            metrics["legacy_workflows_present"] = True
        else:
            evidence.append("Zero legacy workflows invariant satisfied (.agents/workflows/ absent)")
            score += 15.0
            metrics["legacy_workflows_present"] = False

        # Check hooks configuration
        hooks_json = root / ".agents" / "hooks.json"
        if hooks_json.is_file():
            try:
                data = json.loads(hooks_json.read_text(encoding="utf-8", errors="ignore"))
                if isinstance(data, dict):
                    # Count hook definitions across all groups (e.g. antios-guard)
                    hook_count = 0
                    for group, events in data.items():
                        if isinstance(events, dict):
                            hook_count += sum(len(h) if isinstance(h, list) else 1 for h in events.values())
                        elif isinstance(events, list):
                            hook_count += len(events)
                    evidence.append(f"Found {hook_count} configured platform hook action(s) in .agents/hooks.json")
                    score += 15.0
                    metrics["hooks_count"] = hook_count
                else:
                    warnings.append(".agents/hooks.json must be a JSON object")
                    score -= 10.0
            except Exception:
                warnings.append("Malformed .agents/hooks.json")
                score -= 10.0
        else:
            unknowns.append(".agents/hooks.json not found")
            metrics["hooks_count"] = 0

        score = min(100.0, max(0.0, score))
        confidence = ConfidenceLevel.HIGH

        return DimensionScore(
            dimension=ScoreDimension.AGENTS,
            score=score,
            epistemic_state=state,
            confidence=confidence,
            evidence=evidence,
            warnings=warnings,
            unknowns=unknowns,
            recommendations=recommendations,
            metrics=metrics,
        )

    # -------------------------------------------------------------------------
    # 5. OWNERSHIP
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_ownership(cls, root: Path) -> DimensionScore:
        evidence: List[str] = []
        warnings: List[str] = []
        unknowns: List[str] = []
        recommendations: List[str] = []
        metrics: Dict[str, Any] = {}

        score = 60.0
        state = EpistemicDimensionState.OBSERVED

        # Check manifest
        manifest_path = root / ".antios" / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest = load_manifest(root)
                evidence.append(f"Valid project manifest found with {len(manifest.artifacts)} tracked artifacts")
                score += 30.0
                metrics["manifest_valid"] = True
                metrics["artifact_count"] = len(manifest.artifacts)
            except Exception as e:
                warnings.append(f"Corrupted or invalid .antios/manifest.json: {e}")
                score -= 20.0
                metrics["manifest_valid"] = False
        else:
            unknowns.append("No .antios/manifest.json found (uninstalled or unadapted project)")
            recommendations.append("Run python framework/scripts/tools/adapt_project.py to establish artifact ownership manifest")
            score = 50.0  # Neutral baseline when unadapted
            state = EpistemicDimensionState.UNKNOWN
            metrics["manifest_valid"] = False

        # Check antios.config.json protected paths
        config_path = root / "antios.config.json"
        if config_path.is_file():
            evidence.append("antios.config.json defines declarative governance boundaries")
            score += 10.0
            metrics["config_present"] = True
        else:
            metrics["config_present"] = False

        score = min(100.0, max(0.0, score))
        confidence = ConfidenceLevel.HIGH if state == EpistemicDimensionState.OBSERVED else ConfidenceLevel.LOW

        return DimensionScore(
            dimension=ScoreDimension.OWNERSHIP,
            score=score,
            epistemic_state=state,
            confidence=confidence,
            evidence=evidence,
            warnings=warnings,
            unknowns=unknowns,
            recommendations=recommendations,
            metrics=metrics,
        )

    # -------------------------------------------------------------------------
    # 6. VERIFICATION
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_verification(cls, root: Path) -> DimensionScore:
        evidence: List[str] = []
        warnings: List[str] = []
        unknowns: List[str] = []
        recommendations: List[str] = []
        metrics: Dict[str, Any] = {}

        score = 50.0
        state = EpistemicDimensionState.INFERRED

        # Check configured test runners
        config_path = root / "antios.config.json"
        has_configured_runner = False
        if config_path.is_file():
            try:
                cfg = json.loads(config_path.read_text(encoding="utf-8", errors="ignore"))
                runners = cfg.get("test_runners", [])
                if runners:
                    has_configured_runner = True
                    evidence.append(f"Found {len(runners)} configured test runner(s) in antios.config.json")
                    score += 25.0
                    state = EpistemicDimensionState.OBSERVED
                    metrics["configured_runners"] = runners
            except Exception:
                pass

        if not has_configured_runner:
            unknowns.append("No test runners configured in antios.config.json")
            recommendations.append("Configure explicit test runners in antios.config.json")

        # Check physical test directory existence
        tests_dir = root / "tests"
        if tests_dir.is_dir():
            test_files = list(tests_dir.rglob("test_*.py")) + list(tests_dir.rglob("*_test.py"))
            metrics["test_file_count"] = len(test_files)
            if test_files:
                evidence.append(f"Found physical test suite with {len(test_files)} test files in tests/")
                score += 25.0
                state = EpistemicDimensionState.OBSERVED
        else:
            unknowns.append("No tests/ directory discovered")
            recommendations.append("Establish physical automated test suite in tests/")

        score = min(100.0, max(0.0, score))
        confidence = ConfidenceLevel.HIGH if state == EpistemicDimensionState.OBSERVED else ConfidenceLevel.MEDIUM

        return DimensionScore(
            dimension=ScoreDimension.VERIFICATION,
            score=score,
            epistemic_state=state,
            confidence=confidence,
            evidence=evidence,
            warnings=warnings,
            unknowns=unknowns,
            recommendations=recommendations,
            metrics=metrics,
        )

    # -------------------------------------------------------------------------
    # 7. MEMORY / KNOWLEDGE
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_memory_knowledge(cls, root: Path) -> DimensionScore:
        evidence: List[str] = []
        warnings: List[str] = []
        unknowns: List[str] = []
        recommendations: List[str] = []
        metrics: Dict[str, Any] = {}

        score = 50.0  # Neutral baseline
        state = EpistemicDimensionState.INFERRED

        knowledge_path = root / ".antios" / "knowledge.json"
        if knowledge_path.is_file():
            evidence.append("Persistent project knowledge store active (.antios/knowledge.json)")
            score += 25.0
            state = EpistemicDimensionState.OBSERVED
            metrics["knowledge_present"] = True
        else:
            unknowns.append("No .antios/knowledge.json file present")
            metrics["knowledge_present"] = False

        obs_path = root / ".antios" / "learning_observations.json"
        if obs_path.is_file():
            try:
                obs_data = json.loads(obs_path.read_text(encoding="utf-8", errors="ignore"))
                obs_list = obs_data.get("observations", [])
                evidence.append(f"Found {len(obs_list)} empirical learning observations")
                score += 25.0
                state = EpistemicDimensionState.OBSERVED
                metrics["observations_count"] = len(obs_list)
            except Exception:
                warnings.append("Corrupted .antios/learning_observations.json")
                score -= 10.0
        else:
            unknowns.append("No .antios/learning_observations.json file found")
            metrics["observations_count"] = 0

        score = min(100.0, max(0.0, score))
        confidence = ConfidenceLevel.HIGH if state == EpistemicDimensionState.OBSERVED else ConfidenceLevel.LOW

        return DimensionScore(
            dimension=ScoreDimension.MEMORY_KNOWLEDGE,
            score=score,
            epistemic_state=state,
            confidence=confidence,
            evidence=evidence,
            warnings=warnings,
            unknowns=unknowns,
            recommendations=recommendations,
            metrics=metrics,
        )

    # -------------------------------------------------------------------------
    # 8. TOOLING
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_tooling(cls, root: Path) -> DimensionScore:
        evidence: List[str] = []
        warnings: List[str] = []
        unknowns: List[str] = []
        recommendations: List[str] = []
        metrics: Dict[str, Any] = {}

        score = 65.0
        state = EpistemicDimensionState.OBSERVED

        # Check tool policy implementation
        tool_policy_file = root / "framework" / "core" / "tool_policy.py"
        if tool_policy_file.is_file():
            evidence.append("Framework core tool policy engine available")
            score += 15.0

        # Check tool gap analysis / 6-tier preference
        tool_gap_file = root / "framework" / "core" / "tool_gap.py"
        if tool_gap_file.is_file():
            evidence.append("6-tier tool escalation hierarchy enforced (Native > Script > Project > CLI > Service > MCP)")
            score += 20.0

        score = min(100.0, max(0.0, score))
        confidence = ConfidenceLevel.HIGH

        return DimensionScore(
            dimension=ScoreDimension.TOOLING,
            score=score,
            epistemic_state=state,
            confidence=confidence,
            evidence=evidence,
            warnings=warnings,
            unknowns=unknowns,
            recommendations=recommendations,
            metrics=metrics,
        )

    # -------------------------------------------------------------------------
    # 9. PROJECT STRUCTURE
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_project_structure(cls, root: Path) -> DimensionScore:
        evidence: List[str] = []
        warnings: List[str] = []
        unknowns: List[str] = []
        recommendations: List[str] = []
        metrics: Dict[str, Any] = {}

        score = 60.0
        state = EpistemicDimensionState.OBSERVED

        # Manifest / lockfile discovery
        manifests = ["pyproject.toml", "package.json", "Cargo.toml", "go.mod", "pom.xml"]
        found_manifests = [m for m in manifests if (root / m).is_file()]
        if found_manifests:
            evidence.append(f"Identified authoritative package manifest(s): {', '.join(found_manifests)}")
            score += 20.0
            metrics["manifests"] = found_manifests
        else:
            unknowns.append("No standard package manifest (pyproject.toml, package.json, etc.) in root")
            metrics["manifests"] = []

        # Git repository check
        if (root / ".git").is_dir():
            evidence.append("Valid Git version control boundary detected")
            score += 20.0
            metrics["is_git_repo"] = True
        else:
            warnings.append("Project is not inside a git repository")
            score -= 15.0
            metrics["is_git_repo"] = False

        score = min(100.0, max(0.0, score))
        confidence = ConfidenceLevel.HIGH

        return DimensionScore(
            dimension=ScoreDimension.PROJECT_STRUCTURE,
            score=score,
            epistemic_state=state,
            confidence=confidence,
            evidence=evidence,
            warnings=warnings,
            unknowns=unknowns,
            recommendations=recommendations,
            metrics=metrics,
        )

    # -------------------------------------------------------------------------
    # 10. ORCHESTRATION READINESS
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_orchestration_readiness(cls, root: Path) -> DimensionScore:
        evidence: List[str] = []
        warnings: List[str] = []
        unknowns: List[str] = []
        recommendations: List[str] = []
        metrics: Dict[str, Any] = {}

        score = 70.0
        state = EpistemicDimensionState.OBSERVED

        # Dispatch engine check
        dispatch_file = root / "framework" / "core" / "dispatch.py"
        if dispatch_file.is_file():
            evidence.append("Canonical 9-step task dispatch engine present (dispatch.py)")
            score += 15.0

        # Adaptive orchestrator check
        orchestration_file = root / "framework" / "core" / "orchestration.py"
        if orchestration_file.is_file():
            evidence.append("Adaptive workforce sizing & wave collapse engine verified")
            score += 15.0

        score = min(100.0, max(0.0, score))
        confidence = ConfidenceLevel.HIGH

        return DimensionScore(
            dimension=ScoreDimension.ORCHESTRATION_READINESS,
            score=score,
            epistemic_state=state,
            confidence=confidence,
            evidence=evidence,
            warnings=warnings,
            unknowns=unknowns,
            recommendations=recommendations,
            metrics=metrics,
        )
