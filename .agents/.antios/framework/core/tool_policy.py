"""AntiOS Canonical Tool Selection Policy & MCP Justification Authority.

Implements:
1. Canonical MCP Justification Authority (answers the 8 canonical questions)
2. Strict 6-Tier Tool Preference:
   NATIVE (1) -> SCRIPT (2) -> PROJECT (3) -> EXTERNAL (4) -> SERVICE (5) -> MCP (6)
3. Tool Authorization Enforcement against AgentCapabilityBoundary
4. Offline / Degraded Execution Resolution
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from framework.core.tool import (
    HybridCapabilityTier,
    Locality,
    ProviderAvailability,
    ToolDefinition,
    ToolPolicyStatus,
    ToolTier,
)
from framework.core.provider import (
    ProviderDefinition,
    ProviderPolicyStatus,
    ProviderType,
)
from framework.core.tool_registry import ToolRegistry


@dataclass
class MCPJustificationReport:
    """Answers the 8 canonical MCP justification questions plus the 7-field escalation audit."""
    provider_id: str
    status: str  # NOT_NEEDED, USEFUL, OPTIONAL, REJECTED, UNAVAILABLE
    is_needed: bool = False
    is_permitted: bool = False
    why: str = ""
    local_alternatives: List[str] = field(default_factory=list)
    why_insufficient: str = ""
    fallback: str = ""
    on_unavailable: str = "FAIL_CLOSED"

    # Phase 86: 7 Canonical MCP Escalation Protocol Fields
    capability_sought: str = ""
    why_native_failed: str = ""
    least_privilege_scope: List[str] = field(default_factory=list)
    risk_assessment: str = "MINIMAL"
    rollback_plan: str = ""
    user_approval_required: bool = False
    audit_trail_entry: Dict[str, Any] = field(default_factory=dict)

    def validate_escalation_audit(self) -> Tuple[bool, List[str]]:
        """Validates that all 7 required escalation audit fields are populated if MCP is needed."""
        errors: List[str] = []
        if self.is_needed and self.status in ["USEFUL", "OPTIONAL"]:
            if not self.capability_sought.strip():
                errors.append("Missing required field: capability_sought")
            if not self.why_native_failed.strip():
                errors.append("Missing required field: why_native_failed")
            if not self.least_privilege_scope:
                errors.append("Missing required field: least_privilege_scope")
            if not self.risk_assessment.strip():
                errors.append("Missing required field: risk_assessment")
            if not self.rollback_plan.strip():
                errors.append("Missing required field: rollback_plan")
            if not isinstance(self.user_approval_required, bool):
                errors.append("Invalid field: user_approval_required must be a bool")
            if not self.audit_trail_entry:
                errors.append("Missing required field: audit_trail_entry")
        return (len(errors) == 0, errors)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "status": self.status,
            "is_needed": self.is_needed,
            "is_permitted": self.is_permitted,
            "why": self.why,
            "local_alternatives": list(self.local_alternatives),
            "why_insufficient": self.why_insufficient,
            "fallback": self.fallback,
            "on_unavailable": self.on_unavailable,
            "capability_sought": self.capability_sought,
            "why_native_failed": self.why_native_failed,
            "least_privilege_scope": list(self.least_privilege_scope),
            "risk_assessment": self.risk_assessment,
            "rollback_plan": self.rollback_plan,
            "user_approval_required": self.user_approval_required,
            "audit_trail_entry": dict(self.audit_trail_entry),
        }


class MCPJustificationEngine:
    """Canonical, single source of truth for MCP selection and justification in AntiOS."""

    REJECTED_PROVIDERS = {
        "provider:notion": "Notion MCP is out of scope for agent engineering runtime",
        "provider:postman": "Postman MCP is redundant with native curl and deterministic test scripts",
        "provider:posthog": "PostHog analytics MCP is out of scope for agent engineering runtime",
        "provider:unauthorized-external-mcp": "Unauthorized external MCP is strictly forbidden",
    }

    @classmethod
    def evaluate(
        cls,
        task_intent: str,
        capability_id: Any,
        target_files: Optional[List[str]] = None,
        registry: Optional[ToolRegistry] = None,
    ) -> MCPJustificationReport:
        """Evaluate task intent and capability to answer the 8 canonical MCP questions."""
        intent_lower = (task_intent or "").lower()
        if isinstance(capability_id, dict):
            cap_id_str = capability_id.get("capability_id", str(capability_id))
        else:
            cap_id_str = str(capability_id or "")
        cap_lower = cap_id_str.lower()
        target_files = target_files or []

        # 1. Check for explicitly rejected MCP candidates
        for rej_id, reason in cls.REJECTED_PROVIDERS.items():
            short_name = rej_id.replace("provider:", "")
            if short_name in intent_lower or short_name in cap_lower:
                return MCPJustificationReport(
                    provider_id=rej_id,
                    status="REJECTED",
                    is_needed=False,
                    is_permitted=False,
                    why=f"REJECTED: {reason}",
                    local_alternatives=["tool:native-run-command", "tool:navigate-repo"],
                    why_insufficient="Not applicable; provider is untrusted or out of scope.",
                    fallback="NONE",
                    on_unavailable="FAIL_CLOSED",
                    capability_sought=cap_id_str or task_intent,
                    why_native_failed="Native tools (Tiers 1-6) preferred; candidate rejected by security policy",
                    least_privilege_scope=[],
                    risk_assessment=f"CRITICAL: {reason}",
                    rollback_plan="FAIL_CLOSED immediately",
                    user_approval_required=True,
                    audit_trail_entry={"provider": rej_id, "status": "REJECTED", "reason": reason},
                )

        # 2. Local Git Operations: STRICT ENFORCEMENT of Native Git > GitHub MCP
        git_local_tokens = ["git status", "git diff", "git log", "git branch", "working tree", "local commit"]
        if any(tok in intent_lower for tok in git_local_tokens) or "git:status" in cap_lower or "git:diff" in cap_lower:
            return MCPJustificationReport(
                provider_id="provider:github",
                status="NOT_NEEDED",
                is_needed=False,
                is_permitted=False,
                why="Local Git CLI is authoritative, 100% offline, zero tokens, and executes in <50ms. GitHub MCP is strictly forbidden for local repository inspection.",
                local_alternatives=["tool:native-git-cli", "tool:external-git"],
                why_insufficient="Local Git CLI is strictly superior to GitHub MCP for all local operations.",
                fallback="tool:external-git",
                on_unavailable="CONTINUE_LOCAL_CLI",
                capability_sought=cap_id_str or task_intent,
                why_native_failed="Local Git CLI (Tier 6) satisfies all local inspection without network latency",
                least_privilege_scope=[],
                risk_assessment="ZERO: Native local tool execution",
                rollback_plan="Use git CLI status/diff/restore",
                user_approval_required=False,
                audit_trail_entry={"provider": "provider:github", "status": "NOT_NEEDED"},
            )

        # 3. Local file inspection / repository wayfinding
        local_inspect_tokens = ["read file", "view file", "inspect file", "find symbol", "navigate", "grep", "repo structure"]
        if any(tok in intent_lower for tok in local_inspect_tokens) or "wayfinding" in cap_lower or "file:read" in cap_lower:
            return MCPJustificationReport(
                provider_id="none",
                status="NOT_NEEDED",
                is_needed=False,
                is_permitted=False,
                why="Local Antigravity native tools and deterministic scripts fully satisfy repository inspection without external transport.",
                local_alternatives=["tool:native-view-file", "tool:native-grep-search", "tool:navigate-repo"],
                why_insufficient="Native tools are zero-latency and 100% accurate on disk.",
                fallback="tool:native-view-file",
                on_unavailable="FAIL_CLOSED",
                capability_sought=cap_id_str or task_intent,
                why_native_failed="Local native tools (Tier 1) fully satisfy repository inspection",
                least_privilege_scope=[],
                risk_assessment="ZERO: Native read-only operations",
                rollback_plan="None required",
                user_approval_required=False,
                audit_trail_entry={"provider": "none", "status": "NOT_NEEDED"},
            )

        # 4. Remote GitHub PR Management
        pr_tokens = [
            "create pr", "create pull request", "open pr", "merge pr", "github pr",
            "remote pr", "pull request", "pull_request", "pull-request",
        ]
        if (
            any(tok in intent_lower for tok in pr_tokens)
            or any(tok in cap_lower for tok in ["github:create-pull-request", "create_pull_request", "pull_request"])
        ):
            # Check availability if registry provided
            avail = True
            if registry:
                p = registry.get_provider("provider:github")
                if p and p.availability != ProviderAvailability.AVAILABLE:
                    avail = False

            if not avail:
                return MCPJustificationReport(
                    provider_id="provider:github",
                    status="UNAVAILABLE",
                    is_needed=True,
                    is_permitted=True,
                    why="Remote GitHub PR creation requires GitHub API transport, but provider is currently UNAVAILABLE.",
                    local_alternatives=["tool:native-git-cli (prepares local branch/commit only)"],
                    why_insufficient="Local Git cannot create remote pull requests on github.com.",
                    fallback="NONE",
                    on_unavailable="FAIL_CLOSED",
                    capability_sought=cap_id_str or "Remote GitHub PR creation",
                    why_native_failed="Local Git CLI lacks remote GitHub PR REST/GraphQL endpoints",
                    least_privilege_scope=["create_pull_request"],
                    risk_assessment="LOW: remote repository metadata read/write",
                    rollback_plan="Re-verify provider availability and credentials",
                    user_approval_required=False,
                    audit_trail_entry={"provider": "provider:github", "status": "UNAVAILABLE"},
                )

            return MCPJustificationReport(
                provider_id="provider:github",
                status="OPTIONAL",
                is_needed=True,
                is_permitted=True,
                why="GitHub remote PR operations cannot be performed locally; remote API transport is justified for PR creation after local preparation.",
                local_alternatives=["tool:native-git-cli (prepares local branch/commit only)"],
                why_insufficient="Local Git cannot create remote pull requests on github.com without remote API transport.",
                fallback="NONE",
                on_unavailable="FAIL_CLOSED",
                capability_sought=cap_id_str or "Remote GitHub PR creation",
                why_native_failed="Local Git CLI lacks remote GitHub PR REST/GraphQL endpoints",
                least_privilege_scope=["create_pull_request", "pull_request_read"],
                risk_assessment="LOW: remote repository metadata read/write",
                rollback_plan="Close opened PR or delete branch via git push --delete",
                user_approval_required=False,
                audit_trail_entry={"provider": "provider:github", "operation": "create_pull_request", "timestamp": "audit"},
            )

        # 5. Live Browser DOM / Accessibility Layout Inspection
        dom_tokens = ["dom", "browser layout", "accessibility tree", "a11y", "chrome devtools", "css inspection", "inspect browser"]
        if any(tok in intent_lower for tok in dom_tokens) or "browser:dom" in cap_lower or "browser:a11y" in cap_lower:
            avail = True
            if registry:
                p = registry.get_provider("provider:chrome-devtools")
                if p and p.availability != ProviderAvailability.AVAILABLE:
                    avail = False

            if not avail:
                return MCPJustificationReport(
                    provider_id="provider:chrome-devtools",
                    status="UNAVAILABLE",
                    is_needed=True,
                    is_permitted=True,
                    why="Browser DOM and accessibility layout inspection require Chrome DevTools, but provider is UNAVAILABLE.",
                    local_alternatives=["tool:native-view-file (inspects raw HTML template only)"],
                    why_insufficient="Static HTML files do not reflect computed CSS layout, active JavaScript DOM mutations, or rendered a11y trees.",
                    fallback="NONE",
                    on_unavailable="FAIL_CLOSED",
                    capability_sought=cap_id_str or "Live Browser DOM & Accessibility Tree Inspection",
                    why_native_failed="Static HTML file inspection cannot compute layout, CSS cascade, or live a11y trees",
                    least_privilege_scope=["take_snapshot"],
                    risk_assessment="MINIMAL: read-only local browser inspection",
                    rollback_plan="Fallback to static DOM inspection",
                    user_approval_required=False,
                    audit_trail_entry={"provider": "provider:chrome-devtools", "status": "UNAVAILABLE"},
                )

            return MCPJustificationReport(
                provider_id="provider:chrome-devtools",
                status="USEFUL",
                is_needed=True,
                is_permitted=True,
                why="Chrome DevTools provides live computed styles, DOM nodes, and rendered accessibility tree inspection unavailable via static source tools.",
                local_alternatives=["tool:native-view-file (inspects raw HTML template only)"],
                why_insufficient="Static HTML files do not reflect computed CSS layout, active JavaScript DOM mutations, or rendered a11y trees.",
                fallback="NONE",
                on_unavailable="FAIL_CLOSED",
                capability_sought=cap_id_str or "Live Browser DOM & Accessibility Tree Inspection",
                why_native_failed="Static HTML file inspection cannot compute layout, CSS cascade, or live a11y trees",
                least_privilege_scope=["take_snapshot", "get_console_message"],
                risk_assessment="MINIMAL: read-only local browser inspection",
                rollback_plan="Close browser page session",
                user_approval_required=False,
                audit_trail_entry={"provider": "provider:chrome-devtools", "operation": "inspect_a11y", "timestamp": "audit"},
            )

        # 6. Browser E2E Automation
        e2e_tokens = ["playwright", "e2e automation", "browser automation", "click and assert", "headless browser flow"]
        if any(tok in intent_lower for tok in e2e_tokens) or "browser:e2e" in cap_lower:
            return MCPJustificationReport(
                provider_id="provider:playwright",
                status="USEFUL",
                is_needed=True,
                is_permitted=True,
                why="Playwright MCP provides active browser driving, element interaction, and visual snapshots for user flows.",
                local_alternatives=["tool:project-test-runner (if project has local playwright tests installed)"],
                why_insufficient="Command-line scripts without browser runtime cannot perform interactive browser step automation.",
                fallback="tool:project-test-runner",
                on_unavailable="FAIL_CLOSED",
                capability_sought=cap_id_str or "Interactive Browser E2E Automation",
                why_native_failed="Local CLI tools without headless browser runtime cannot drive interactive DOM flows",
                least_privilege_scope=["playwright_navigate", "playwright_click", "playwright_screenshot"],
                risk_assessment="LOW: local browser test execution",
                rollback_plan="Terminate browser session and clean test artifacts",
                user_approval_required=False,
                audit_trail_entry={"provider": "provider:playwright", "operation": "e2e_automation", "timestamp": "audit"},
            )

        # 7. Upstream Gemini API / SDK Documentation
        sdk_tokens = ["gemini api docs", "upstream gemini sdk", "gemini documentation", "google-genai docs"]
        if any(tok in intent_lower for tok in sdk_tokens) or "docs:gemini" in cap_lower:
            return MCPJustificationReport(
                provider_id="provider:gemini-api-docs",
                status="USEFUL",
                is_needed=True,
                is_permitted=True,
                why="Authoritative real-time upstream SDK reference search preventing outdated LLM hallucinations.",
                local_alternatives=["tool:native-view-file (for local vendored markdown docs)"],
                why_insufficient="Local repo does not store upstream Google Gemini SDK release documentation.",
                fallback="NONE",
                on_unavailable="FAIL_CLOSED",
                capability_sought=cap_id_str or "Upstream Gemini SDK Documentation",
                why_native_failed="Local repository does not vendor latest upstream Google Gemini SDK release docs",
                least_privilege_scope=["gemini_search_docs", "gemini_get_doc"],
                risk_assessment="ZERO: read-only documentation search",
                rollback_plan="Fallback to local offline references",
                user_approval_required=False,
                audit_trail_entry={"provider": "provider:gemini-api-docs", "operation": "search_docs", "timestamp": "audit"},
            )

        # Default: MCP is NOT needed
        return MCPJustificationReport(
            provider_id="none",
            status="NOT_NEEDED",
            is_needed=False,
            is_permitted=False,
            why="Standard local tools and deterministic scripts satisfy the capability requirement with lower latency and zero remote risk.",
            local_alternatives=["tool:native-run-command", "tool:navigate-repo"],
            why_insufficient="Local tools are sufficient.",
            fallback="NONE",
            on_unavailable="FAIL_CLOSED",
            capability_sought=cap_id_str or task_intent,
            why_native_failed="Native tools (Tiers 1-6) fully satisfy requirements",
            least_privilege_scope=[],
            risk_assessment="ZERO: local execution",
            rollback_plan="Use deterministic local tools",
            user_approval_required=False,
            audit_trail_entry={"provider": "none", "status": "NOT_NEEDED"},
        )


class DeterministicToolSelector:
    """Selects the safest, smallest, most appropriate execution mechanism for a capability."""

    # Preference ranking: lower number = higher preference
    TIER_RANKING = {
        ToolTier.NATIVE: 1,
        ToolTier.SCRIPT: 2,
        ToolTier.PROJECT: 3,
        ToolTier.EXTERNAL: 4,
        ToolTier.MCP: 6,
    }

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def select_tool(
        self,
        task_intent: str,
        capability_id: Any,
        task_class: str = "FEATURE",
        subsystem_id: str = "*",
        agent_role: Optional[Any] = None,
        target_files: Optional[List[str]] = None,
        offline_mode: bool = False,
    ) -> Dict[str, Any]:
        """Execute deterministic tool selection with authorization and availability checks."""
        if isinstance(capability_id, dict):
            capability_id = capability_id.get("capability_id", str(capability_id))
        else:
            capability_id = str(capability_id or "")

        target_files = target_files or []
        mcp_report = MCPJustificationEngine.evaluate(
            task_intent=task_intent,
            capability_id=capability_id,
            target_files=target_files,
            registry=self.registry,
        )

        # 1. Find all candidate tools exposing this capability
        candidates = self.registry.find_tools_by_capability(capability_id, enabled_only=False, available_only=False)

        # If MCP is justified and permitted, include its exposed tools as candidates
        if mcp_report.is_needed and mcp_report.provider_id:
            prov = self.registry.get_provider(mcp_report.provider_id)
            if prov:
                for tid in prov.exposed_tools:
                    t = self.registry.get_tool(tid)
                    if t and t not in candidates:
                        candidates.append(t)

        # If no specific capability match, try task-matching tools
        if not candidates:
            candidates = self.registry.find_tools_by_task_type(task_class, enabled_only=False)

        # Sort candidates according to strict tier hierarchy and availability
        def candidate_sort_key(t: ToolDefinition) -> Tuple[int, int, int]:
            # Enabled first
            enabled_rank = 0 if t.enabled else 1
            # Available first
            avail_rank = 0 if t.availability == ProviderAvailability.AVAILABLE else 1
            # Preference tier
            tier_rank = self.TIER_RANKING.get(t.tier, 99)
            return (enabled_rank, avail_rank, tier_rank)

        sorted_candidates = sorted(candidates, key=candidate_sort_key)

        selected_tool: Optional[ToolDefinition] = None
        selected_provider: Optional[ProviderDefinition] = None
        alternatives_considered: List[Dict[str, Any]] = []
        why_selected = ""
        why_alternatives_rejected: List[str] = []

        # 2. Iterate through sorted candidates and select first permitted & matching
        for cand in sorted_candidates:
            cand_prov = self.registry.get_provider(cand.provider_id)
            alt_info = {
                "tool_id": cand.tool_id,
                "tier": cand.tier.value,
                "provider_id": cand.provider_id,
                "availability": cand.availability.value,
                "enabled": cand.enabled,
            }

            # Check if candidate is explicitly forbidden/rejected
            if not cand.enabled or cand.policy_status == ToolPolicyStatus.FORBIDDEN:
                alt_info["rejected_reason"] = "Tool is disabled or forbidden by policy"
                alternatives_considered.append(alt_info)
                why_alternatives_rejected.append(f"{cand.tool_id}: Disabled/Forbidden by policy")
                continue

            if cand_prov and (not cand_prov.enabled or cand_prov.policy_status == ProviderPolicyStatus.REJECTED):
                alt_info["rejected_reason"] = f"Provider {cand_prov.provider_id} is rejected under ANTIOS_MCP_POLICY.md"
                alternatives_considered.append(alt_info)
                why_alternatives_rejected.append(f"{cand.tool_id}: Provider rejected under AntiOS policy")
                continue

            # If tool is MCP, check MCP justification
            if cand.tier == ToolTier.MCP:
                if not mcp_report.is_needed or not mcp_report.is_permitted:
                    alt_info["rejected_reason"] = f"MCP not justified: {mcp_report.why}"
                    alternatives_considered.append(alt_info)
                    why_alternatives_rejected.append(f"{cand.tool_id}: MCP not justified ({mcp_report.status})")
                    continue

            # If offline mode requested, filter out tools that require network
            if offline_mode and (not cand.offline_capable or (cand_prov and cand_prov.requires_network)):
                alt_info["rejected_reason"] = "Tool requires network connectivity, but offline mode is active"
                alternatives_considered.append(alt_info)
                why_alternatives_rejected.append(f"{cand.tool_id}: Requires network in offline mode")
                continue

            # Candidate selected!
            if selected_tool is None:
                selected_tool = cand
                selected_provider = cand_prov
                why_selected = (
                    f"Selected {cand.name} ({cand.tier.value}) as highest-priority permitted mechanism "
                    f"for capability '{capability_id}'."
                )
            else:
                alt_info["rejected_reason"] = (
                    f"Lower tier ({cand.tier.value}) than selected tool ({selected_tool.tier.value})"
                )
                alternatives_considered.append(alt_info)
                why_alternatives_rejected.append(
                    f"{cand.tool_id}: Lower tier than selected {selected_tool.tool_id}"
                )

        # 3. Tool Authorization Check against Agent Boundary
        auth_status = "AUTHORIZED"
        auth_reason = "Tool execution permitted under active agent governance."

        if selected_tool is not None and agent_role is not None:
            boundary = getattr(agent_role, "boundary", None)
            if boundary is not None:
                # Check capability access via boundary
                is_allowed, reason = boundary.validate_capability_access(capability_id)
                if not is_allowed:
                    auth_status = "BLOCKED"
                    auth_reason = f"Agent boundary violation: {reason}"
                else:
                    # Check if tool itself is forbidden by boundary
                    tool_cap = f"tool:{selected_tool.tool_id.replace('tool:', '')}"
                    t_allowed, t_reason = boundary.validate_capability_access(tool_cap)
                    if not t_allowed:
                        auth_status = "BLOCKED"
                        auth_reason = f"Agent boundary violation: Tool {selected_tool.tool_id} is explicitly forbidden for role {getattr(agent_role, 'role_id', 'unknown')}."

            # Check protected core zones if specialist
            role_type = getattr(agent_role, "role_type", None)
            role_type_val = getattr(role_type, "value", str(role_type))
            if role_type_val in ["SPECIALIST", "CHECKER"]:
                # Specialists are forbidden from mutating protected AntiOS core files
                for tf in target_files:
                    tf_norm = tf.replace("\\", "/").strip("/")
                    if tf_norm.startswith("framework/") or tf_norm.startswith(".agents/") or tf_norm == "antios.config.json":
                        if selected_tool.tool_id in ["tool:native-write-file", "tool:native-replace-content"]:
                            auth_status = "BLOCKED"
                            auth_reason = f"Constitutional Violation: Specialist role {getattr(agent_role, 'role_id', 'unknown')} cannot mutate protected AntiOS file '{tf}'."

        # 4. Handle tool unavailable status
        availability = ProviderAvailability.AVAILABLE
        if selected_tool is not None:
            availability = selected_tool.availability
            if selected_provider and selected_provider.availability != ProviderAvailability.AVAILABLE:
                availability = selected_provider.availability

        return {
            "selected_tool": selected_tool,
            "selected_provider": selected_provider,
            "execution_tier": selected_tool.tier if selected_tool else ToolTier.SCRIPT,
            "why_selected": why_selected or "No available tool matched capability requirements.",
            "alternatives_considered": alternatives_considered,
            "why_alternatives_rejected": why_alternatives_rejected,
            "mcp_report": mcp_report,
            "availability": availability,
            "offline_mode": offline_mode,
            "authorization_status": auth_status,
            "authorization_reason": auth_reason,
        }


@dataclass
class HybridResolutionResult:
    """Result of resolving a capability against the 8-tier matrix."""
    resolved_tier: HybridCapabilityTier
    tier_name: str
    target_identifier: str
    is_authorized: bool
    requires_approval: bool = False
    justification_report: Optional[MCPJustificationReport] = None
    audit_trail: Dict[str, Any] = field(default_factory=dict)
    rejection_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resolved_tier": self.resolved_tier.value,
            "tier_name": self.tier_name,
            "target_identifier": self.target_identifier,
            "is_authorized": self.is_authorized,
            "requires_approval": self.requires_approval,
            "justification_report": self.justification_report.to_dict() if self.justification_report else None,
            "audit_trail": dict(self.audit_trail),
            "rejection_reason": self.rejection_reason,
        }


class HybridCapabilityExecutionMatrix:
    """8-Tier Hybrid Capability Execution Matrix under Phase 86.

    Strict Resolution Order:
      Tier 1: Native Antigravity Built-in Tool
      Tier 2: Project-Native Skill (.agents/skills/)
      Tier 3: Project Tool / Script
      Tier 4: AntiOS Core Runtime Service
      Tier 5: Antigravity Built-in Specialist Agent
      Tier 6: Standard CLI Execution
      Tier 7: User-Approved External Service
      Tier 8: Managed MCP Tool (highest barrier, mandatory 7-field escalation audit)
    """

    TIER_NAMES = {
        HybridCapabilityTier.TIER_1_NATIVE_BUILTIN: "Native Antigravity Built-in Tool",
        HybridCapabilityTier.TIER_2_PROJECT_NATIVE_SKILL: "Project-Native Skill",
        HybridCapabilityTier.TIER_3_PROJECT_TOOL_SCRIPT: "Project Tool / Script",
        HybridCapabilityTier.TIER_4_ANTIOS_CORE_RUNTIME: "AntiOS Core Runtime Service",
        HybridCapabilityTier.TIER_5_SPECIALIST_AGENT: "Antigravity Specialist Agent",
        HybridCapabilityTier.TIER_6_STANDARD_CLI: "Standard CLI Execution",
        HybridCapabilityTier.TIER_7_EXTERNAL_SERVICE: "User-Approved External Service",
        HybridCapabilityTier.TIER_8_MANAGED_MCP: "Managed MCP Tool",
    }

    NATIVE_TOOLS = {
        "view_file", "write_to_file", "replace_file_content",
        "run_command", "read_url_content", "search_web",
        "find_by_name", "grep_search", "list_dir",
        "ask_question", "invoke_subagent", "manage_subagents",
        "schedule", "manage_task", "send_message",
    }

    KNOWN_PROJECT_SKILLS = {
        "antios", "antios-engineer", "antios-debug",
        "antios-verifier", "antios-adapt-project",
    }

    SPECIALIST_AGENTS = {
        "research", "flutter_a11y_agent", "self",
    }

    ANTIOS_SERVICES = {
        "wayfinder", "stop_gate", "pre_tool_guard", "wave_manager",
        "runtime_closure", "discovery_engine", "learning_engine",
        "workforce_planner", "failure_recovery",
    }

    STANDARD_CLI_BINARIES = {
        "git", "python", "pip", "node", "npm", "cargo", "docker", "pytest", "ruff",
    }

    EXTERNAL_SERVICES = {
        "cloud_storage", "bigquery", "external_api",
    }

    def __init__(self, registry: Optional[ToolRegistry] = None) -> None:
        self.registry = registry

    def resolve(
        self,
        capability_sought: str,
        task_intent: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> HybridResolutionResult:
        """Resolves capability in strict priority order (Tier 1 -> Tier 8)."""
        ctx = context or {}
        cap_clean = (capability_sought or "").strip().lower()
        intent_clean = (task_intent or "").strip().lower()

        # Tier 1: Native Built-in Tool
        if cap_clean in self.NATIVE_TOOLS or any(
            nt in cap_clean for nt in [
                "view_file", "write_to_file", "replace_content", "replace_file_content",
                "grep_search", "find_by_name", "list_dir", "read_url_content", "search_web"
            ]
        ):
            matched = cap_clean if cap_clean in self.NATIVE_TOOLS else "run_command"
            return HybridResolutionResult(
                resolved_tier=HybridCapabilityTier.TIER_1_NATIVE_BUILTIN,
                tier_name=self.TIER_NAMES[HybridCapabilityTier.TIER_1_NATIVE_BUILTIN],
                target_identifier=f"native:{matched}",
                is_authorized=True,
                audit_trail={"tier": 1, "mechanism": "NATIVE_BUILTIN", "target": matched},
            )

        # Tier 2: Project-Native Skill
        available_skills = sorted(
            set(ctx.get("available_skills", [])) | self.KNOWN_PROJECT_SKILLS,
            key=lambda s: len(s),
            reverse=True,
        )
        for skill in available_skills:
            if skill.lower() in cap_clean or skill.lower() in intent_clean:
                return HybridResolutionResult(
                    resolved_tier=HybridCapabilityTier.TIER_2_PROJECT_NATIVE_SKILL,
                    tier_name=self.TIER_NAMES[HybridCapabilityTier.TIER_2_PROJECT_NATIVE_SKILL],
                    target_identifier=f"skill:{skill}",
                    is_authorized=True,
                    audit_trail={"tier": 2, "mechanism": "PROJECT_NATIVE_SKILL", "target": skill},
                )

        # Tier 3: Project Tool / Script
        project_tools = sorted(
            ctx.get("project_tools", ["tests/run_all.py", "pytest", "npm test"]),
            key=lambda s: len(s),
            reverse=True,
        )
        for pt in project_tools:
            if pt.lower() in cap_clean or pt.lower() in intent_clean:
                return HybridResolutionResult(
                    resolved_tier=HybridCapabilityTier.TIER_3_PROJECT_TOOL_SCRIPT,
                    tier_name=self.TIER_NAMES[HybridCapabilityTier.TIER_3_PROJECT_TOOL_SCRIPT],
                    target_identifier=f"script:{pt}",
                    is_authorized=True,
                    audit_trail={"tier": 3, "mechanism": "PROJECT_TOOL_SCRIPT", "target": pt},
                )

        # Tier 4: AntiOS Core Runtime Service
        for svc in sorted(self.ANTIOS_SERVICES, key=lambda s: len(s), reverse=True):
            if svc in cap_clean or svc in intent_clean:
                return HybridResolutionResult(
                    resolved_tier=HybridCapabilityTier.TIER_4_ANTIOS_CORE_RUNTIME,
                    tier_name=self.TIER_NAMES[HybridCapabilityTier.TIER_4_ANTIOS_CORE_RUNTIME],
                    target_identifier=f"runtime:{svc}",
                    is_authorized=True,
                    audit_trail={"tier": 4, "mechanism": "ANTIOS_CORE_RUNTIME", "target": svc},
                )

        # Tier 5: Antigravity Built-in Specialist Agent
        for spec in sorted(self.SPECIALIST_AGENTS, key=lambda s: len(s), reverse=True):
            if spec in cap_clean or (f"agent:{spec}" in cap_clean) or (f"subagent:{spec}" in intent_clean):
                return HybridResolutionResult(
                    resolved_tier=HybridCapabilityTier.TIER_5_SPECIALIST_AGENT,
                    tier_name=self.TIER_NAMES[HybridCapabilityTier.TIER_5_SPECIALIST_AGENT],
                    target_identifier=f"specialist:{spec}",
                    is_authorized=True,
                    audit_trail={"tier": 5, "mechanism": "SPECIALIST_AGENT", "target": spec},
                )

        # Tier 6: Standard CLI Execution (skip if caller specifically requested MCP provider)
        if not (cap_clean.startswith("mcp:") or "provider:" in cap_clean):
            for cli in sorted(self.STANDARD_CLI_BINARIES, key=lambda s: len(s), reverse=True):
                tokens = cap_clean.split()
                if cli in tokens or (f"cli:{cli}" in cap_clean) or (cap_clean == cli):
                    return HybridResolutionResult(
                        resolved_tier=HybridCapabilityTier.TIER_6_STANDARD_CLI,
                        tier_name=self.TIER_NAMES[HybridCapabilityTier.TIER_6_STANDARD_CLI],
                        target_identifier=f"cli:{cli}",
                        is_authorized=True,
                        audit_trail={"tier": 6, "mechanism": "STANDARD_CLI", "target": cli},
                    )

        # Tier 7: User-Approved External Service
        for ext in self.EXTERNAL_SERVICES:
            if ext in cap_clean or ext in intent_clean:
                user_approved = ctx.get("user_approval_granted", False)
                return HybridResolutionResult(
                    resolved_tier=HybridCapabilityTier.TIER_7_EXTERNAL_SERVICE,
                    tier_name=self.TIER_NAMES[HybridCapabilityTier.TIER_7_EXTERNAL_SERVICE],
                    target_identifier=f"service:{ext}",
                    is_authorized=user_approved,
                    requires_approval=True,
                    rejection_reason=None if user_approved else f"External service '{ext}' requires user approval",
                    audit_trail={"tier": 7, "mechanism": "EXTERNAL_SERVICE", "target": ext, "approved": user_approved},
                )

        # Tier 8: Managed MCP Tool (Highest barrier, mandatory 7-field escalation report)
        mcp_report = MCPJustificationEngine.evaluate(
            task_intent=task_intent,
            capability_id=capability_sought,
            registry=self.registry,
        )

        if mcp_report.status == "REJECTED":
            return HybridResolutionResult(
                resolved_tier=HybridCapabilityTier.TIER_8_MANAGED_MCP,
                tier_name=self.TIER_NAMES[HybridCapabilityTier.TIER_8_MANAGED_MCP],
                target_identifier=f"mcp:{mcp_report.provider_id}",
                is_authorized=False,
                justification_report=mcp_report,
                rejection_reason=mcp_report.why,
                audit_trail={"tier": 8, "status": "REJECTED", "report": mcp_report.to_dict()},
            )

        if not mcp_report.is_needed or mcp_report.status == "NOT_NEEDED":
            return HybridResolutionResult(
                resolved_tier=HybridCapabilityTier.TIER_8_MANAGED_MCP,
                tier_name=self.TIER_NAMES[HybridCapabilityTier.TIER_8_MANAGED_MCP],
                target_identifier=f"mcp:{mcp_report.provider_id}",
                is_authorized=False,
                justification_report=mcp_report,
                rejection_reason="Managed MCP not needed: lower-tier native or CLI tools suffice.",
                audit_trail={"tier": 8, "status": "NOT_NEEDED", "report": mcp_report.to_dict()},
            )

        # Validate complete 7-field escalation report
        valid_audit, audit_errs = mcp_report.validate_escalation_audit()
        if not valid_audit:
            return HybridResolutionResult(
                resolved_tier=HybridCapabilityTier.TIER_8_MANAGED_MCP,
                tier_name=self.TIER_NAMES[HybridCapabilityTier.TIER_8_MANAGED_MCP],
                target_identifier=f"mcp:{mcp_report.provider_id}",
                is_authorized=False,
                justification_report=mcp_report,
                rejection_reason=f"MCP Escalation Audit Incomplete: {'; '.join(audit_errs)}",
                audit_trail={"tier": 8, "status": "AUDIT_FAILED", "errors": audit_errs},
            )

        return HybridResolutionResult(
            resolved_tier=HybridCapabilityTier.TIER_8_MANAGED_MCP,
            tier_name=self.TIER_NAMES[HybridCapabilityTier.TIER_8_MANAGED_MCP],
            target_identifier=f"mcp:{mcp_report.provider_id}",
            is_authorized=True,
            requires_approval=mcp_report.user_approval_required,
            justification_report=mcp_report,
            audit_trail={"tier": 8, "status": "AUTHORIZED", "report": mcp_report.to_dict()},
        )

    def evaluate_full(
        self,
        capability_sought: str,
        task_intent: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Evaluates all 8 tiers systematically and produces comprehensive execution dossier."""
        res = self.resolve(capability_sought=capability_sought, task_intent=task_intent, context=context)
        evaluations = []
        for tier in HybridCapabilityTier:
            name = self.TIER_NAMES[tier]
            is_match = (tier == res.resolved_tier)
            evaluations.append({
                "tier_number": tier.value,
                "tier_name": name,
                "selected": is_match,
                "authorized": res.is_authorized if is_match else False,
            })
        return {
            "capability_sought": capability_sought,
            "task_intent": task_intent,
            "resolved_tier": res.resolved_tier.value,
            "tier_name": res.tier_name,
            "target_identifier": res.target_identifier,
            "is_authorized": res.is_authorized,
            "requires_approval": res.requires_approval,
            "justification_report": res.justification_report.to_dict() if res.justification_report else None,
            "rejection_reason": res.rejection_reason,
            "audit_trail": res.audit_trail,
            "tier_evaluations": evaluations,
        }
