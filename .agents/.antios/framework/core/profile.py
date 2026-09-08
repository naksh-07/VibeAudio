"""AntiOS v1 Project Profile Model.

This module formalizes the canonical Project Profile for AntiOS.
It separates facts into three epistemological tiers:
- OBSERVED: Directly witnessed on disk (manifests, exact keys, files). Weight: 1.0.
- INFERRED: Derived heuristics with explicit rationale and confidence score (0.0 to 1.0).
- UNKNOWN / ENVIRONMENT_UNAVAILABLE: Gaps in knowledge, missing manifests, or unavailable tooling.

AntiOS never fabricates capabilities or presents guesses as facts.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from framework.core.topology import WorkspaceMember, WorkspaceTopology


class EvidenceTier(str, Enum):
    """Epistemological tier for discovered project intelligence."""
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"
    ENVIRONMENT_UNAVAILABLE = "ENVIRONMENT_UNAVAILABLE"


class ConfidenceLevel(str, Enum):
    """Confidence rating for inferred project facts."""
    CERTAIN = "CERTAIN"      # 1.00 (Reserved for OBSERVED)
    HIGH = "HIGH"            # 0.85 - 0.99
    MEDIUM = "MEDIUM"        # 0.60 - 0.84
    LOW = "LOW"              # < 0.60


class ToolCategory(str, Enum):
    """Category of developer tool."""
    TEST_RUNNER = "TEST_RUNNER"
    LINTER = "LINTER"
    FORMATTER = "FORMATTER"
    TYPECHECKER = "TYPECHECKER"
    BUILD_SYSTEM = "BUILD_SYSTEM"
    PACKAGE_MANAGER = "PACKAGE_MANAGER"


class ConflictType(str, Enum):
    """Canonical conflict detection taxonomy."""
    GUIDANCE_MANIFEST_DRIFT = "GUIDANCE_MANIFEST_DRIFT"        # Prose instructions claim command missing in manifest
    MANIFEST_CI_DRIFT = "MANIFEST_CI_DRIFT"                    # Manifest tool differs from CI workflow execution
    CONSTITUTIONAL_VIOLATION = "CONSTITUTIONAL_VIOLATION"      # Project requests mutation of AntiOS immutable core
    TOOLING_ENVIRONMENT_MISMATCH = "TOOLING_ENVIRONMENT_MISMATCH" # Toolchain configured but binary absent in PATH
    AMBIGUOUS_DUAL_TOOLING = "AMBIGUOUS_DUAL_TOOLING"          # Mutually conflicting package managers/runners


@dataclass
class EvidenceFact:
    """A directly witnessed fact from the physical filesystem."""
    path: str
    selector: str  # e.g., "scripts.test", "[tool.pytest]", "line 14"
    value: Any
    witness_type: str = "FILE_CONTENT"  # FILE_EXISTENCE, FILE_CONTENT, GIT_STATE
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": EvidenceTier.OBSERVED.value,
            "path": self.path,
            "selector": self.selector,
            "value": self.value,
            "witness_type": self.witness_type,
            "description": self.description,
        }


@dataclass
class InferredFact:
    """A deduction derived from one or more observed facts."""
    hypothesis: str
    confidence: float  # 0.0 to 1.0
    rationale: str
    underlying_evidence: List[str] = field(default_factory=list)  # References to EvidenceFact paths/selectors

    @property
    def confidence_level(self) -> ConfidenceLevel:
        if self.confidence >= 0.85:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 0.60:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": EvidenceTier.INFERRED.value,
            "hypothesis": self.hypothesis,
            "confidence": round(self.confidence, 2),
            "confidence_level": self.confidence_level.value,
            "rationale": self.rationale,
            "underlying_evidence": self.underlying_evidence,
        }


@dataclass
class UnknownFact:
    """An explicit representation of a knowledge gap or missing capability."""
    field_name: str
    reason: str
    required_action: str = ""
    is_blocking: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": EvidenceTier.UNKNOWN.value,
            "field_name": self.field_name,
            "reason": self.reason,
            "required_action": self.required_action,
            "is_blocking": self.is_blocking,
        }


@dataclass
class ToolFact:
    """Discovered executable toolchain capability."""
    name: str
    category: ToolCategory
    manifest_path: str
    command: List[str]
    timeout_seconds: int = 60
    required: bool = True
    cwd: Optional[str] = None
    is_available_in_path: bool = True
    non_interactive_flags: List[str] = field(default_factory=list)
    tier: EvidenceTier = EvidenceTier.OBSERVED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "manifest_path": self.manifest_path,
            "command": self.command,
            "timeout_seconds": self.timeout_seconds,
            "required": self.required,
            "cwd": self.cwd,
            "is_available_in_path": self.is_available_in_path,
            "non_interactive_flags": self.non_interactive_flags,
            "tier": self.tier.value,
        }


@dataclass
class GuidanceFact:
    """Discovered project instructions from documentation or CI."""
    source_file: str
    declared_commands: Dict[str, List[str]] = field(default_factory=dict)
    declared_constraints: List[str] = field(default_factory=list)
    target_rules: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_file": self.source_file,
            "declared_commands": self.declared_commands,
            "declared_constraints": self.declared_constraints,
            "target_rules": self.target_rules,
        }


@dataclass
class ConflictFact:
    """A discrepancy between sources of authority."""
    conflict_type: ConflictType
    description: str
    prose_claim: str
    physical_reality: str
    resolution_recommendation: str
    winning_source: str  # e.g., "MANIFEST", "CI_WORKFLOW", "ANTIOS_CORE_CONSTITUTION"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_type": self.conflict_type.value,
            "description": self.description,
            "prose_claim": self.prose_claim,
            "physical_reality": self.physical_reality,
            "resolution_recommendation": self.resolution_recommendation,
            "winning_source": self.winning_source,
        }


@dataclass
class ProjectIdentity:
    """Identity and baseline characteristics of a target codebase."""
    name: str
    root_path: str
    is_git_repo: bool = False
    head_commit: Optional[str] = None
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    package_managers: List[str] = field(default_factory=list)
    build_systems: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectProfile:
    """Canonical Project Profile representing structured project intelligence.
    
    Strictly categorizes data into:
    - identity: High-level naming, languages, repo status
    - observed_facts: Explicit file/key evidence
    - inferred_facts: Derived heuristics with confidence
    - unknown_fields: Gaps in project understanding
    - tools: Discovered test runners, linters, formatters, typecheckers
    - guidance: Extracted developer instructions
    - conflicts: Detected discrepancies between guidance and physical manifests
    - risk_zones: Sensitive, legacy, or protected areas identified in the repo
    """
    identity: ProjectIdentity
    observed_facts: List[EvidenceFact] = field(default_factory=list)
    inferred_facts: List[InferredFact] = field(default_factory=list)
    unknown_fields: List[UnknownFact] = field(default_factory=list)
    tools: List[ToolFact] = field(default_factory=list)
    guidance: List[GuidanceFact] = field(default_factory=list)
    conflicts: List[ConflictFact] = field(default_factory=list)
    risk_zones: List[str] = field(default_factory=list)
    protected_paths: List[str] = field(default_factory=list)
    forbidden_patterns: List[str] = field(default_factory=list)
    topology: WorkspaceTopology = WorkspaceTopology.STANDALONE
    workspace_members: List[WorkspaceMember] = field(default_factory=list)
    manifest_fingerprint: str = ""
    subsystems: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def add_observed(self, path: str, selector: str, value: Any, witness_type: str = "FILE_CONTENT", description: str = "") -> None:
        self.observed_facts.append(EvidenceFact(path, selector, value, witness_type, description))

    def add_inferred(self, hypothesis: str, confidence: float, rationale: str, underlying_evidence: Optional[List[str]] = None) -> None:
        self.inferred_facts.append(InferredFact(hypothesis, confidence, rationale, underlying_evidence or []))

    def add_unknown(self, field_name: str, reason: str, required_action: str = "", is_blocking: bool = False) -> None:
        self.unknown_fields.append(UnknownFact(field_name, reason, required_action, is_blocking))

    def add_tool(self, tool: ToolFact) -> None:
        self.tools.append(tool)

    def add_conflict(self, conflict: ConflictFact) -> None:
        self.conflicts.append(conflict)

    def get_test_runners(self) -> List[ToolFact]:
        return [t for t in self.tools if t.category == ToolCategory.TEST_RUNNER]

    def get_linters(self) -> List[ToolFact]:
        return [t for t in self.tools if t.category == ToolCategory.LINTER]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "topology": self.topology.value if hasattr(self.topology, "value") else str(self.topology),
            "workspace_members": [m.to_dict() if hasattr(m, "to_dict") else m for m in self.workspace_members],
            "manifest_fingerprint": self.manifest_fingerprint,
            "observed_facts": [f.to_dict() for f in self.observed_facts],
            "inferred_facts": [f.to_dict() for f in self.inferred_facts],
            "unknown_fields": [f.to_dict() for f in self.unknown_fields],
            "tools": [t.to_dict() for t in self.tools],
            "guidance": [g.to_dict() for g in self.guidance],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "risk_zones": self.risk_zones,
            "protected_paths": self.protected_paths,
            "forbidden_patterns": self.forbidden_patterns,
            "subsystems": self.subsystems,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
