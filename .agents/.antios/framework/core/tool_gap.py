"""AntiOS 2.0 Tool & MCP Gap Analysis Engine.

Extends the deterministic 6-tier tool/provider hierarchy:
  Tier 1: NATIVE         (Antigravity platform primitives)
  Tier 2: LOCAL SCRIPT   (Deterministic AntiOS scripts in framework/scripts/tools/)
  Tier 3: PROJECT TOOL   (Project-local binaries: pytest, vitest, cargo, etc.)
  Tier 4: STANDARD CLI   (Host system CLI binaries: git, python, etc.)
  Tier 5: EXTERNAL SERVICE (Local background daemon or system service)
  Tier 6: MCP PROVIDER   (Model Context Protocol remote/external tools)

When a tool deficit or capability gap is encountered, evaluates alternative tiers
in strict preference order, enforcing:
1. Native first, MCP last (Escalation ONLY, never default).
2. Structured escalation ledgers recording alternatives, rejections, cost, latency,
   network requirements, and security implications.
3. Reuse of MCPJustificationEngine and DeterministicToolSelector without duplication.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from framework.core.capability import Capability, CapabilityType
from framework.core.capability_gap import CapabilityGap, GapClassification
from framework.core.tool import FailureClass, ToolTier
from framework.core.tool_policy import DeterministicToolSelector, MCPJustificationEngine, MCPJustificationReport
from framework.core.tool_registry import ToolRegistry


class ToolEscalationTier(int, Enum):
    """The 6 canonical escalation tiers in ascending escalation order."""
    TIER_1_NATIVE = 1
    TIER_2_LOCAL_SCRIPT = 2
    TIER_3_PROJECT_TOOL = 3
    TIER_4_STANDARD_CLI = 4
    TIER_5_EXTERNAL_SERVICE = 5
    TIER_6_MCP = 6


@dataclass
class ToolAlternativeEvaluation:
    """Evaluation record for a specific tool tier alternative."""
    tier: ToolEscalationTier
    tier_name: str
    candidates_considered: List[str]
    is_viable: bool
    rejection_reason: Optional[str] = None
    estimated_cost: str = "ZERO"          # ZERO, LOW, MEDIUM, HIGH
    estimated_latency_ms: int = 10        # In milliseconds
    requires_network: bool = False
    security_risk: str = "MINIMAL"        # MINIMAL, LOW, MEDIUM, HIGH, CRITICAL


@dataclass
class ToolGapReport:
    """Comprehensive, auditable report for a tool or MCP gap."""
    gap_id: str
    required_capability_id: str
    task_intent: str
    deficit_type: str                     # TIER_DEFICIT, PATH_MISSING, MCP_UNAVAILABLE, POLICY_BLOCKED
    lowest_viable_tier: Optional[ToolEscalationTier]
    recommended_tool_id: Optional[str]
    alternatives_evaluated: List[ToolAlternativeEvaluation]
    rejected_alternatives: Dict[str, str] # tool_id -> reason
    mcp_justification: Optional[Dict[str, Any]] = None
    escalation_justified: bool = False
    escalation_reason: str = ""
    security_boundaries_respected: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serializes report to dictionary."""
        return {
            "gap_id": self.gap_id,
            "required_capability_id": self.required_capability_id,
            "task_intent": self.task_intent,
            "deficit_type": self.deficit_type,
            "lowest_viable_tier": self.lowest_viable_tier.value if self.lowest_viable_tier else None,
            "recommended_tool_id": self.recommended_tool_id,
            "alternatives_evaluated": [asdict(a) for a in self.alternatives_evaluated],
            "rejected_alternatives": self.rejected_alternatives,
            "mcp_justification": self.mcp_justification,
            "escalation_justified": self.escalation_justified,
            "escalation_reason": self.escalation_reason,
            "security_boundaries_respected": self.security_boundaries_respected,
            "created_at": self.created_at,
        }


class ToolGapAnalyzer:
    """Analyzes tool capability deficits across the 6-tier preference hierarchy.
    
    Reuses MCPJustificationEngine and DeterministicToolSelector.
    """

    def __init__(self, tool_registry: Optional[ToolRegistry] = None) -> None:
        self.tool_registry = tool_registry or ToolRegistry()
        self.selector = DeterministicToolSelector(self.tool_registry)

    def analyze_tool_deficit(
        self,
        capability_id: str,
        task_intent: str,
        gap: Optional[CapabilityGap] = None,
        available_tools: Optional[List[str]] = None,
        offline_mode: bool = False,
    ) -> ToolGapReport:
        """Evaluates whether an existing local/native tool can satisfy the capability
        before escalating to external services or MCP.
        """
        gap_id = gap.gap_id if gap else f"tool-gap-{hashlib.sha256(capability_id.encode()).hexdigest()[:8]}"
        intent = task_intent.lower()

        evaluations: List[ToolAlternativeEvaluation] = []
        rejected: Dict[str, str] = {}
        lowest_viable_tier: Optional[ToolEscalationTier] = None
        recommended_tool: Optional[str] = None

        # ---------------------------------------------------------------------
        # Tier 1: Native Antigravity Primitives
        # ---------------------------------------------------------------------
        native_candidates = ["view_file", "write_to_file", "replace_file_content", "grep_search", "find_by_name", "run_command"]
        is_native_viable = False
        native_reason = "Native tools alone cannot satisfy specialized external interaction or deep domain execution."
        is_script_domain = any(w in intent for w in ["wayfinding", "locate", "blast radius", "doc audit", "broken link", "changeset", "verify intelligence"])
        if not is_script_domain and any(w in intent for w in ["read", "view", "search", "find", "grep", "inspect file", "list directory"]):
            is_native_viable = True
            native_reason = None
            lowest_viable_tier = ToolEscalationTier.TIER_1_NATIVE
            recommended_tool = "tool:antigravity-native"

        evaluations.append(ToolAlternativeEvaluation(
            tier=ToolEscalationTier.TIER_1_NATIVE,
            tier_name="NATIVE",
            candidates_considered=native_candidates,
            is_viable=is_native_viable,
            rejection_reason=native_reason,
            estimated_cost="ZERO",
            estimated_latency_ms=5,
            requires_network=False,
            security_risk="MINIMAL",
        ))

        # ---------------------------------------------------------------------
        # Tier 2: Local AntiOS Scripts
        # ---------------------------------------------------------------------
        script_candidates = ["navigate_repo.py", "audit_docs.py", "inspect_repo.py", "verify_intelligence.py", "check_changeset.py"]
        is_script_viable = False
        script_reason = "No deterministic local script matches the required task domain."
        if any(w in intent for w in ["wayfinding", "locate", "blast radius", "doc audit", "broken link", "changeset", "verify intelligence"]):
            is_script_viable = True
            script_reason = None
            if lowest_viable_tier is None:
                lowest_viable_tier = ToolEscalationTier.TIER_2_LOCAL_SCRIPT
                recommended_tool = "tool:antios-script"

        evaluations.append(ToolAlternativeEvaluation(
            tier=ToolEscalationTier.TIER_2_LOCAL_SCRIPT,
            tier_name="LOCAL_SCRIPT",
            candidates_considered=script_candidates,
            is_viable=is_script_viable,
            rejection_reason=script_reason,
            estimated_cost="ZERO",
            estimated_latency_ms=25,
            requires_network=False,
            security_risk="MINIMAL",
        ))

        # ---------------------------------------------------------------------
        # Tier 3: Project-Native Tools (npm, pytest, cargo)
        # ---------------------------------------------------------------------
        project_candidates = ["pytest", "vitest", "npm-test", "cargo-test", "ruff", "mypy", "eslint"]
        is_project_viable = False
        project_reason = "No project-native manifest or test runner configured for this task."
        if any(w in intent for w in ["test", "lint", "typecheck", "build", "compile"]):
            is_project_viable = True
            project_reason = None
            if lowest_viable_tier is None:
                lowest_viable_tier = ToolEscalationTier.TIER_3_PROJECT_TOOL
                recommended_tool = "tool:project-runner"

        evaluations.append(ToolAlternativeEvaluation(
            tier=ToolEscalationTier.TIER_3_PROJECT_TOOL,
            tier_name="PROJECT_TOOL",
            candidates_considered=project_candidates,
            is_viable=is_project_viable,
            rejection_reason=project_reason,
            estimated_cost="ZERO",
            estimated_latency_ms=150,
            requires_network=False,
            security_risk="LOW",
        ))

        # ---------------------------------------------------------------------
        # Tier 4: Standard Host CLI (git, python)
        # ---------------------------------------------------------------------
        cli_candidates = ["git", "python", "curl", "tar", "zip"]
        is_cli_viable = False
        cli_reason = "Standard CLI tools insufficient for task requirements."
        if "git" in intent:
            # Local Git CLI outranks any remote GitHub MCP!
            is_cli_viable = True
            cli_reason = None
            if lowest_viable_tier is None:
                lowest_viable_tier = ToolEscalationTier.TIER_4_STANDARD_CLI
                recommended_tool = "tool:native-git-cli"
            rejected["provider:github-mcp"] = "Local Git operations MUST use local git CLI rather than remote GitHub MCP."

        evaluations.append(ToolAlternativeEvaluation(
            tier=ToolEscalationTier.TIER_4_STANDARD_CLI,
            tier_name="STANDARD_CLI",
            candidates_considered=cli_candidates,
            is_viable=is_cli_viable,
            rejection_reason=cli_reason,
            estimated_cost="ZERO",
            estimated_latency_ms=80,
            requires_network=False,
            security_risk="LOW",
        ))

        # ---------------------------------------------------------------------
        # Tier 5: External System Service
        # ---------------------------------------------------------------------
        evaluations.append(ToolAlternativeEvaluation(
            tier=ToolEscalationTier.TIER_5_EXTERNAL_SERVICE,
            tier_name="EXTERNAL_SERVICE",
            candidates_considered=["docker-daemon", "system-db"],
            is_viable=False,
            rejection_reason="No external system service required or configured.",
            estimated_cost="LOW",
            estimated_latency_ms=500,
            requires_network=False,
            security_risk="MEDIUM",
        ))

        # ---------------------------------------------------------------------
        # Tier 6: MCP Provider (Escalation via MCPJustificationEngine)
        # ---------------------------------------------------------------------
        mcp_report = MCPJustificationEngine.evaluate(
            capability_id=capability_id,
            task_intent=task_intent,
        )

        is_mcp_viable = False
        mcp_reason = "MCP not justified; local alternatives exist or provider is rejected."
        if mcp_report.is_needed and mcp_report.is_permitted and not offline_mode:
            is_mcp_viable = True
            mcp_reason = None
            if lowest_viable_tier is None:
                lowest_viable_tier = ToolEscalationTier.TIER_6_MCP
                recommended_tool = f"mcp:{mcp_report.provider_id}"
        else:
            rejected[f"mcp:{mcp_report.provider_id}"] = mcp_report.why

        evaluations.append(ToolAlternativeEvaluation(
            tier=ToolEscalationTier.TIER_6_MCP,
            tier_name="MCP_PROVIDER",
            candidates_considered=[mcp_report.provider_id],
            is_viable=is_mcp_viable,
            rejection_reason=mcp_reason,
            estimated_cost="MEDIUM",
            estimated_latency_ms=800,
            requires_network=True,
            security_risk="MEDIUM",
        ))

        deficit_type = "TIER_DEFICIT"
        if lowest_viable_tier is None:
            deficit_type = "CAPABILITY_UNSATISFIED"
        elif lowest_viable_tier == ToolEscalationTier.TIER_6_MCP:
            deficit_type = "MCP_ESCALATION_JUSTIFIED"
        else:
            deficit_type = "RESOLVED_LOCAL_TIER"

        return ToolGapReport(
            gap_id=gap_id,
            required_capability_id=capability_id,
            task_intent=task_intent,
            deficit_type=deficit_type,
            lowest_viable_tier=lowest_viable_tier,
            recommended_tool_id=recommended_tool,
            alternatives_evaluated=evaluations,
            rejected_alternatives=rejected,
            mcp_justification=mcp_report.to_dict() if mcp_report else None,
            escalation_justified=(lowest_viable_tier == ToolEscalationTier.TIER_6_MCP),
            escalation_reason=mcp_report.why if (lowest_viable_tier == ToolEscalationTier.TIER_6_MCP) else "Resolved at local tier without MCP escalation.",
            security_boundaries_respected=True,
        )
