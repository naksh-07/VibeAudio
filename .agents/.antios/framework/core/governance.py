"""AntiOS Governance Model Primitives.

Formalizes the architectural distinctions between:
- RULE: High-level cognitive directive and behavioral invariant (prompt text in docs/AGENTS.md)
- SKILL: Procedural capability guidance ("HOW") in .agents/skills/
- WORKFLOW: Declarative stage sequence ("WHEN + SEQUENCE") in framework/core/workflow.py (legacy .agents/workflows/ retired)
- HOOK: Deterministic process interceptor outside LLM context in .agents/hooks.json and framework/scripts/hooks/
- TOOL: Executable capability primitive (Antigravity native, local script, or external MCP)
- ADAPTER: Project-specific declarative binding in antios.config.json

Ensures these concepts are cleanly defined, inspectable, and non-overlapping.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class GovernancePrimitiveType(str, Enum):
    RULE = "RULE"
    SKILL = "SKILL"
    WORKFLOW = "WORKFLOW"
    HOOK = "HOOK"
    TOOL = "TOOL"
    ADAPTER = "ADAPTER"


@dataclass(frozen=True)
class GovernancePrimitiveDefinition:
    """Formal definition and boundary specification for a governance primitive."""
    primitive_type: GovernancePrimitiveType
    definition: str
    physical_location: str
    execution_context: str
    invariants: List[str] = field(default_factory=list)
    anti_patterns: List[str] = field(default_factory=list)


GOVERNANCE_TAXONOMY: Dict[GovernancePrimitiveType, GovernancePrimitiveDefinition] = {
    GovernancePrimitiveType.RULE: GovernancePrimitiveDefinition(
        primitive_type=GovernancePrimitiveType.RULE,
        definition="High-level cognitive directive and behavioral invariant presented to the LLM.",
        physical_location="docs/AGENTS.md (Project Constitution)",
        execution_context="Prompt text / System context (inside LLM context window)",
        invariants=[
            "Strictly bounded in size (<= 80 lines, target <= 30 lines in Core).",
            "Must never contain procedural code, test commands, or tool scripts.",
            "Recognized under Axiom 4 as soft cognitive orientation, NOT hard security enforcement.",
        ],
        anti_patterns=[
            "Duplicating tool execution commands inside prompt rules.",
            "Relying on prompt rules alone for boundary enforcement.",
        ],
    ),
    GovernancePrimitiveType.SKILL: GovernancePrimitiveDefinition(
        primitive_type=GovernancePrimitiveType.SKILL,
        definition="Procedural capability guidance specifying HOW to perform specific engineering activities.",
        physical_location=".agents/skills/<name>/SKILL.md",
        execution_context="Dynamically activated procedural context (inside LLM context window)",
        invariants=[
            "Strictly bounded to <= 60 lines (~2,000 bytes).",
            "Must reside in .agents/skills/ for platform discovery.",
            "Never duplicates Antigravity native planning mode or IDE features.",
        ],
        anti_patterns=[
            "Creating fine-grained micro-skills for every trivial sub-step.",
            "Hardcoding project-specific paths inside Core skills.",
        ],
    ),
    GovernancePrimitiveType.WORKFLOW: GovernancePrimitiveDefinition(
        primitive_type=GovernancePrimitiveType.WORKFLOW,
        definition="Declarative temporal sequence specifying WHEN stages occur and how skills compose.",
        physical_location="framework/core/workflow.py (codified contracts; legacy .agents/workflows/*.md retired to archive)",
        execution_context="Lifecycle state engine and operational orchestration",
        invariants=[
            "Governs ordered progression through the 10-step lifecycle.",
            "Maps default risk tier (Low, Medium, High).",
            "Defines entry conditions, completion criteria, and recovery paths.",
        ],
        anti_patterns=[
            "Skipping lifecycle stages or permitting unverified transitions on High-Risk tasks.",
            "Embedding code modifications directly into workflow definitions.",
        ],
    ),
    GovernancePrimitiveType.HOOK: GovernancePrimitiveDefinition(
        primitive_type=GovernancePrimitiveType.HOOK,
        definition="Deterministic process-level interceptor executing outside the LLM context.",
        physical_location=".agents/hooks.json & framework/scripts/hooks/",
        execution_context="Antigravity stdio JSON-RPC IPC / Subprocess boundary",
        invariants=[
            "Strict fail-closed semantics on any error, exception, or invalid input.",
            "Sub-100ms execution latency with zero external package dependencies.",
            "Immutable self-protection of framework and governance configurations.",
            "Physical process test execution ratchets required for Stop events.",
        ],
        anti_patterns=[
            "Failing open on unexpected exceptions.",
            "Attempting fuzzy semantic evaluation or LLM prompting inside hooks.",
        ],
    ),
    GovernancePrimitiveType.TOOL: GovernancePrimitiveDefinition(
        primitive_type=GovernancePrimitiveType.TOOL,
        definition="Executable capability primitive to inspect or alter system state.",
        physical_location="Antigravity native tools, framework/scripts/tools/, or external MCP",
        execution_context="OS process, IDE runtime, or MCP JSON-RPC transport",
        invariants=[
            "Follows 3-tier selection policy: 1. Native -> 2. Local Script -> 3. MCP.",
            "Standardized result model: status, exit code, stdout/stderr, evidence.",
            "Zero hidden state; project-agnostic inputs and outputs.",
        ],
        anti_patterns=[
            "Wrapping native tools unnecessarily.",
            "Introducing MCP servers when local scripts execute faster and offline.",
        ],
    ),
    GovernancePrimitiveType.ADAPTER: GovernancePrimitiveDefinition(
        primitive_type=GovernancePrimitiveType.ADAPTER,
        definition="Declarative project binding translating generic governance to a concrete repository.",
        physical_location="antios.config.json",
        execution_context="Configuration loader (framework/core/config.py)",
        invariants=[
            "Pure data schema (JSON); zero Python code required from target projects.",
            "Declares domain protected paths, test runners, linters, and changeset policies.",
            "Enables AntiOS Core to remain 100% domain-agnostic.",
        ],
        anti_patterns=[
            "Hardcoding project domain terms into AntiOS Core source files.",
            "Allowing adapter configs to disable immutable Core self-protection.",
        ],
    ),
}


def get_governance_primitive(primitive_type: GovernancePrimitiveType) -> GovernancePrimitiveDefinition:
    """Retrieve the formal definition and invariants for a governance primitive."""
    return GOVERNANCE_TAXONOMY[primitive_type]


def validate_governance_boundaries() -> Dict[str, bool]:
    """Validates that governance primitive locations and invariants conform to specification."""
    results = {}
    for ptype, pdef in GOVERNANCE_TAXONOMY.items():
        results[ptype.value] = (
            len(pdef.definition) > 0
            and len(pdef.physical_location) > 0
            and len(pdef.invariants) > 0
        )
    return results
