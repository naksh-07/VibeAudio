"""AntiOS Deterministic Tool & Provider Registry.

Provides in-memory, deterministic indexing and lookup for all execution mechanisms:
- Antigravity Native Tools
- Local Deterministic Scripts
- Project-Local Tools
- Standard External CLIs
- MCP Providers
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from framework.core.tool import (
    CostHint,
    ExecutionMode,
    LatencyHint,
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


class ToolRegistry:
    """In-memory deterministic registry for tools and capability providers."""

    def __init__(self, project_name: str = "AntiOS-Core") -> None:
        self.project_name = project_name
        self._tools: Dict[str, ToolDefinition] = {}
        self._providers: Dict[str, ProviderDefinition] = {}

        # Indices for tools
        self._tools_by_tier: Dict[ToolTier, List[str]] = {tier: [] for tier in ToolTier}
        self._tools_by_capability: Dict[str, List[str]] = {}
        self._tools_by_task_type: Dict[str, List[str]] = {}
        self._tools_by_subsystem: Dict[str, List[str]] = {}
        self._tools_by_provider: Dict[str, List[str]] = {}
        self._tools_by_availability: Dict[ProviderAvailability, List[str]] = {
            avail: [] for avail in ProviderAvailability
        }

        # Indices for providers
        self._providers_by_type: Dict[ProviderType, List[str]] = {ptype: [] for ptype in ProviderType}
        self._providers_by_capability: Dict[str, List[str]] = {}

    def register_tool(self, tool: ToolDefinition, overwrite: bool = True) -> None:
        """Register a tool and update multi-dimensional lookup indices."""
        tid = tool.tool_id
        if tid in self._tools and not overwrite:
            return

        if tid in self._tools:
            self._remove_tool_from_indices(tid)

        self._tools[tid] = tool
        self._tools_by_tier[tool.tier].append(tid)
        self._tools_by_availability[tool.availability].append(tid)

        if tool.provider_id not in self._tools_by_provider:
            self._tools_by_provider[tool.provider_id] = []
        self._tools_by_provider[tool.provider_id].append(tid)

        for cap in tool.capability_ids:
            if cap not in self._tools_by_capability:
                self._tools_by_capability[cap] = []
            self._tools_by_capability[cap].append(tid)

        for task in tool.supported_task_types:
            t_upper = task.upper()
            if t_upper not in self._tools_by_task_type:
                self._tools_by_task_type[t_upper] = []
            self._tools_by_task_type[t_upper].append(tid)

        for sub in tool.supported_subsystems:
            if sub not in self._tools_by_subsystem:
                self._tools_by_subsystem[sub] = []
            self._tools_by_subsystem[sub].append(tid)

    def _remove_tool_from_indices(self, tool_id: str) -> None:
        """Cleanly remove a tool id from all secondary indices."""
        for t_list in self._tools_by_tier.values():
            if tool_id in t_list:
                t_list.remove(tool_id)
        for a_list in self._tools_by_availability.values():
            if tool_id in a_list:
                a_list.remove(tool_id)
        for p_list in self._tools_by_provider.values():
            if tool_id in p_list:
                p_list.remove(tool_id)
        for c_list in self._tools_by_capability.values():
            if tool_id in c_list:
                c_list.remove(tool_id)
        for tt_list in self._tools_by_task_type.values():
            if tool_id in tt_list:
                tt_list.remove(tool_id)
        for s_list in self._tools_by_subsystem.values():
            if tool_id in s_list:
                s_list.remove(tool_id)

    def register_provider(self, provider: ProviderDefinition, overwrite: bool = True) -> None:
        """Register an execution provider and index its capabilities."""
        pid = provider.provider_id
        if pid in self._providers and not overwrite:
            return

        if pid in self._providers:
            self._remove_provider_from_indices(pid)

        self._providers[pid] = provider
        self._providers_by_type[provider.provider_type].append(pid)

        for cap in provider.capabilities:
            if cap not in self._providers_by_capability:
                self._providers_by_capability[cap] = []
            self._providers_by_capability[cap].append(pid)

    def _remove_provider_from_indices(self, provider_id: str) -> None:
        for pt_list in self._providers_by_type.values():
            if provider_id in pt_list:
                pt_list.remove(provider_id)
        for c_list in self._providers_by_capability.values():
            if provider_id in c_list:
                c_list.remove(provider_id)

    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        return self._tools.get(tool_id)

    def get_provider(self, provider_id: str) -> Optional[ProviderDefinition]:
        return self._providers.get(provider_id)

    def list_tools(
        self, tier: Optional[ToolTier] = None, enabled_only: bool = True
    ) -> List[ToolDefinition]:
        if tier is not None:
            tids = self._tools_by_tier.get(tier, [])
            tools = [self._tools[tid] for tid in tids if tid in self._tools]
        else:
            tools = list(self._tools.values())

        if enabled_only:
            tools = [t for t in tools if t.enabled]
        return tools

    def list_providers(
        self, provider_type: Optional[ProviderType] = None, enabled_only: bool = True
    ) -> List[ProviderDefinition]:
        if provider_type is not None:
            pids = self._providers_by_type.get(provider_type, [])
            providers = [self._providers[pid] for pid in pids if pid in self._providers]
        else:
            providers = list(self._providers.values())

        if enabled_only:
            providers = [p for p in providers if p.enabled]
        return providers

    def find_tools_by_capability(
        self, capability_id: str, enabled_only: bool = True, available_only: bool = True
    ) -> List[ToolDefinition]:
        """Find all tools registered for a capability or matching wildcard."""
        matching_ids = set()
        for cap, tids in self._tools_by_capability.items():
            if cap == "*" or cap == capability_id:
                matching_ids.update(tids)
            elif cap.endswith("*") and capability_id.startswith(cap[:-1]):
                matching_ids.update(tids)

        tools = [self._tools[tid] for tid in matching_ids if tid in self._tools]
        if enabled_only:
            tools = [t for t in tools if t.enabled]
        if available_only:
            tools = [t for t in tools if t.availability == ProviderAvailability.AVAILABLE]
        return tools

    def find_tools_by_subsystem(
        self, subsystem_id: str, enabled_only: bool = True
    ) -> List[ToolDefinition]:
        matching_ids = set()
        for sub, tids in self._tools_by_subsystem.items():
            if sub == "*" or sub == subsystem_id:
                matching_ids.update(tids)

        tools = [self._tools[tid] for tid in matching_ids if tid in self._tools]
        if enabled_only:
            tools = [t for t in tools if t.enabled]
        return tools

    def find_tools_by_task_type(
        self, task_type: str, enabled_only: bool = True
    ) -> List[ToolDefinition]:
        t_upper = task_type.upper()
        matching_ids = set()
        for task, tids in self._tools_by_task_type.items():
            if task == "*" or task == t_upper:
                matching_ids.update(tids)

        tools = [self._tools[tid] for tid in matching_ids if tid in self._tools]
        if enabled_only:
            tools = [t for t in tools if t.enabled]
        return tools

    def find_providers_by_capability(
        self, capability_id: str, enabled_only: bool = True
    ) -> List[ProviderDefinition]:
        matching_pids = set()
        for cap, pids in self._providers_by_capability.items():
            if cap == "*" or cap == capability_id:
                matching_pids.update(pids)
            elif cap.endswith("*") and capability_id.startswith(cap[:-1]):
                matching_pids.update(pids)

        providers = [self._providers[pid] for pid in matching_pids if pid in self._providers]
        if enabled_only:
            providers = [p for p in providers if p.enabled]
        return providers

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "tool_count": len(self._tools),
            "provider_count": len(self._providers),
            "tools": {tid: t.to_dict() for tid, t in self._tools.items()},
            "providers": {pid: p.to_dict() for pid, p in self._providers.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ToolRegistry:
        registry = cls(project_name=data.get("project_name", "AntiOS-Core"))
        for pdata in data.get("providers", {}).values():
            registry.register_provider(ProviderDefinition.from_dict(pdata))
        for tdata in data.get("tools", {}).values():
            registry.register_tool(ToolDefinition.from_dict(tdata))
        return registry


def build_default_tool_registry(
    workspace_root: Optional[str] = None, config: Optional[Any] = None
) -> ToolRegistry:
    """Construct the canonical default Tool & Provider Registry for AntiOS.
    
    Registers:
    - Native Antigravity runtime tools
    - Local deterministic AntiOS scripts
    - Standard external tools (Git CLI, Python)
    - Project-local tools
    - Permitted MCP providers (Chrome DevTools, Playwright, Gemini Docs, GitHub remote)
    - Forbidden/Rejected MCPs (Notion, Postman, PostHog, Unauthorized)
    """
    registry = ToolRegistry(project_name="AntiOS-Core")

    # =========================================================================
    # 1. PROVIDERS
    # =========================================================================

    # 1.1 Native Provider
    registry.register_provider(
        ProviderDefinition(
            provider_id="provider:antigravity-native",
            name="Antigravity Native Tool Provider",
            provider_type=ProviderType.NATIVE,
            locality=Locality.LOCAL,
            availability=ProviderAvailability.AVAILABLE,
            offline_capable=True,
            requires_network=False,
            policy_status=ProviderPolicyStatus.PERMITTED,
            capabilities=[
                "tool:run-command",
                "tool:view-file",
                "tool:replace-file-content",
                "tool:write-file",
                "tool:grep-search",
                "tool:list-dir",
                "tool:git-cli",
                "git:status",
                "git:diff",
                "git:log",
                "file:read",
                "file:write",
                "search:grep",
            ],
            exposed_tools=[
                "tool:native-run-command",
                "tool:native-view-file",
                "tool:native-replace-content",
                "tool:native-write-file",
                "tool:native-grep-search",
                "tool:native-list-dir",
                "tool:native-git-cli",
            ],
            justification="Antigravity native execution runtime (highest precedence, zero overhead).",
            source="platform",
        )
    )

    # 1.2 Local Deterministic Script Provider
    registry.register_provider(
        ProviderDefinition(
            provider_id="provider:local-script",
            name="AntiOS Deterministic Local Script Provider",
            provider_type=ProviderType.LOCAL_SCRIPT,
            locality=Locality.LOCAL,
            availability=ProviderAvailability.AVAILABLE,
            offline_capable=True,
            requires_network=False,
            policy_status=ProviderPolicyStatus.PERMITTED,
            capabilities=[
                "tool:navigate-repo",
                "tool:audit-docs",
                "tool:check-changeset",
                "tool:check-worktree",
                "tool:adapt-project",
                "tool:distill-memory",
                "tool:recover-session",
                "wayfinding:subsystem",
                "staleguard:layer1",
                "changeset:check",
            ],
            exposed_tools=[
                "tool:navigate-repo",
                "tool:audit-docs",
                "tool:check-changeset",
                "tool:check-worktree",
                "tool:adapt-project",
                "tool:distill-memory",
                "tool:recover-session",
            ],
            justification="Deterministic local Python scripts under framework/scripts/tools/.",
            source="framework/scripts/tools",
        )
    )

    # 1.3 Project-Local Tool Provider
    registry.register_provider(
        ProviderDefinition(
            provider_id="provider:project-local",
            name="Target Project Tool Provider",
            provider_type=ProviderType.PROJECT,
            locality=Locality.LOCAL,
            availability=ProviderAvailability.AVAILABLE,
            offline_capable=True,
            requires_network=False,
            policy_status=ProviderPolicyStatus.PERMITTED,
            capabilities=[
                "tool:project-test-runner",
                "tool:project-linter",
                "test:run",
                "lint:run",
            ],
            exposed_tools=[
                "tool:project-test-runner",
                "tool:project-linter",
            ],
            justification="Project-local test runners, linters, and verification commands.",
            source="adapter:antios.config.json",
        )
    )

    # 1.4 Standard External CLI Provider
    registry.register_provider(
        ProviderDefinition(
            provider_id="provider:external-cli",
            name="Standard External CLI Provider",
            provider_type=ProviderType.EXTERNAL,
            locality=Locality.LOCAL,
            availability=ProviderAvailability.AVAILABLE,
            offline_capable=True,
            requires_network=False,
            policy_status=ProviderPolicyStatus.PERMITTED,
            capabilities=[
                "tool:external-git",
                "tool:external-python",
                "git:local-branch",
                "git:commit",
            ],
            exposed_tools=[
                "tool:external-git",
                "tool:external-python",
            ],
            justification="Standard system binaries installed on PATH (git, python).",
            source="system:path",
        )
    )

    # 1.5 Permitted MCP Providers (under ANTIOS_MCP_POLICY.md)
    registry.register_provider(
        ProviderDefinition(
            provider_id="provider:chrome-devtools",
            name="Chrome DevTools MCP",
            provider_type=ProviderType.MCP,
            locality=Locality.LOCAL,
            availability=ProviderAvailability.AVAILABLE,
            offline_capable=True,
            requires_network=False,
            policy_status=ProviderPolicyStatus.PERMITTED,
            capabilities=[
                "browser:dom-inspection",
                "browser:a11y-audit",
                "browser:layout-debug",
                "browser:console-logs",
            ],
            exposed_tools=["tool:mcp-chrome-inspect"],
            justification="Unique browser DOM, accessibility tree, and CSS layout inspection unavailable via local scripts.",
            source="ANTIOS_MCP_POLICY.md",
        )
    )

    registry.register_provider(
        ProviderDefinition(
            provider_id="provider:playwright",
            name="Playwright Headless Browser MCP",
            provider_type=ProviderType.MCP,
            locality=Locality.LOCAL,
            availability=ProviderAvailability.AVAILABLE,
            offline_capable=True,
            requires_network=False,
            policy_status=ProviderPolicyStatus.PERMITTED,
            capabilities=[
                "browser:e2e-automation",
                "browser:screenshot",
                "browser:interaction",
            ],
            exposed_tools=["tool:mcp-playwright-exec"],
            justification="Irreplaceable headless browser automation and screenshot capture for end-to-end user flows.",
            source="ANTIOS_MCP_POLICY.md",
        )
    )

    registry.register_provider(
        ProviderDefinition(
            provider_id="provider:gemini-api-docs",
            name="Gemini API Docs MCP",
            provider_type=ProviderType.MCP,
            locality=Locality.REMOTE,
            availability=ProviderAvailability.AVAILABLE,
            offline_capable=False,
            requires_network=True,
            policy_status=ProviderPolicyStatus.PERMITTED,
            capabilities=[
                "docs:gemini-api-search",
                "docs:upstream-sdk-reference",
            ],
            exposed_tools=["tool:mcp-gemini-search-docs"],
            justification="Authoritative upstream documentation retrieval for Google Gemini API and SDK.",
            source="ANTIOS_MCP_POLICY.md",
        )
    )

    registry.register_provider(
        ProviderDefinition(
            provider_id="provider:github",
            name="GitHub Remote MCP",
            provider_type=ProviderType.MCP,
            locality=Locality.REMOTE,
            availability=ProviderAvailability.AVAILABLE,
            offline_capable=False,
            requires_network=True,
            policy_status=ProviderPolicyStatus.RESTRICTED,
            capabilities=[
                "github:create-pull-request",
                "github:list-pull-requests",
                "github:issue-comment",
            ],
            exposed_tools=["tool:mcp-github-create-pr"],
            allowed_tasks=["CREATE_PR", "LIST_PRS", "REMOTE_PR_MANAGEMENT"],
            forbidden_tasks=["GIT_STATUS", "GIT_DIFF", "GIT_LOG", "GIT_BRANCH", "LOCAL_REPO_INSPECTION"],
            justification="Strictly restricted to remote GitHub PR operations; local git operations MUST use native git CLI.",
            source="ANTIOS_MCP_POLICY.md",
        )
    )

    # 1.6 Explicitly Rejected MCP Providers (Anti-Sprawl & Security Guardrails)
    for rej_id, rej_name, rej_reason in [
        ("provider:notion", "Notion MCP Server", "Project tracking out of scope for agent engineering runtime"),
        ("provider:postman", "Postman MCP Server", "Redundant with native curl and deterministic test scripts"),
        ("provider:posthog", "PostHog MCP Server", "Analytics telemetry out of scope for agent engineering OS"),
        ("provider:unauthorized-external-mcp", "Unauthorized External MCP", "Strictly blocked by AntiOS security governance"),
    ]:
        registry.register_provider(
            ProviderDefinition(
                provider_id=rej_id,
                name=rej_name,
                provider_type=ProviderType.MCP,
                locality=Locality.REMOTE,
                availability=ProviderAvailability.POLICY_BLOCKED,
                offline_capable=False,
                requires_network=True,
                policy_status=ProviderPolicyStatus.REJECTED,
                enabled=False,
                justification=f"REJECTED: {rej_reason}",
                source="ANTIOS_MCP_POLICY.md",
            )
        )

    # =========================================================================
    # 2. TOOLS
    # =========================================================================

    # 2.1 Native Tools
    native_tools = [
        ToolDefinition(
            tool_id="tool:native-run-command",
            name="Native Command Execution",
            purpose="Executes terminal commands with timeout and capture via Antigravity runtime",
            tier=ToolTier.NATIVE,
            provider_id="provider:antigravity-native",
            capability_ids=["tool:run-command", "exec:command"],
            risk="HIGH",
            cost_hint=CostHint.ZERO,
            latency_hint=LatencyHint.SUB_SECOND,
            offline_capable=True,
        ),
        ToolDefinition(
            tool_id="tool:native-view-file",
            name="Native File Viewer",
            purpose="Reads file contents with line slicing via Antigravity runtime",
            tier=ToolTier.NATIVE,
            provider_id="provider:antigravity-native",
            capability_ids=["tool:view-file", "file:read"],
            risk="LOW",
            cost_hint=CostHint.ZERO,
            latency_hint=LatencyHint.SUB_SECOND,
            offline_capable=True,
        ),
        ToolDefinition(
            tool_id="tool:native-replace-content",
            name="Native File Edit",
            purpose="Applies contiguous single-block edits to target files",
            tier=ToolTier.NATIVE,
            provider_id="provider:antigravity-native",
            capability_ids=["tool:replace-file-content", "file:edit"],
            risk="MEDIUM",
            cost_hint=CostHint.ZERO,
            latency_hint=LatencyHint.SUB_SECOND,
            offline_capable=True,
        ),
        ToolDefinition(
            tool_id="tool:native-write-file",
            name="Native File Writer",
            purpose="Creates new files with content in workspace",
            tier=ToolTier.NATIVE,
            provider_id="provider:antigravity-native",
            capability_ids=["tool:write-file", "file:write"],
            risk="HIGH",
            cost_hint=CostHint.ZERO,
            latency_hint=LatencyHint.SUB_SECOND,
            offline_capable=True,
        ),
        ToolDefinition(
            tool_id="tool:native-grep-search",
            name="Native Grep Search",
            purpose="Searches text patterns using ripgrep via Antigravity runtime",
            tier=ToolTier.NATIVE,
            provider_id="provider:antigravity-native",
            capability_ids=["tool:grep-search", "search:grep"],
            risk="LOW",
            cost_hint=CostHint.ZERO,
            latency_hint=LatencyHint.SUB_SECOND,
            offline_capable=True,
        ),
        ToolDefinition(
            tool_id="tool:native-list-dir",
            name="Native Directory Lister",
            purpose="Lists directory contents and file sizes",
            tier=ToolTier.NATIVE,
            provider_id="provider:antigravity-native",
            capability_ids=["tool:list-dir", "dir:list"],
            risk="LOW",
            cost_hint=CostHint.ZERO,
            latency_hint=LatencyHint.SUB_SECOND,
            offline_capable=True,
        ),
        ToolDefinition(
            tool_id="tool:native-git-cli",
            name="Native Git CLI",
            purpose="Authoritative local Git operations (status, diff, log) via local git process",
            tier=ToolTier.NATIVE,
            provider_id="provider:antigravity-native",
            capability_ids=["git:status", "git:diff", "git:log", "tool:git-cli"],
            supported_task_types=["*"],
            risk="LOW",
            cost_hint=CostHint.ZERO,
            latency_hint=LatencyHint.SUB_SECOND,
            offline_capable=True,
            evidence="ANTIOS_MCP_POLICY.md: Local Git CLI executes in <50ms with 0 token cost and 100% offline accuracy.",
        ),
    ]
    for nt in native_tools:
        registry.register_tool(nt)

    # 2.2 Local Deterministic Script Tools
    script_tools = [
        ToolDefinition(
            tool_id="tool:navigate-repo",
            name="Repository Navigator",
            purpose="Deterministic wayfinding, change-intent, progressive disclosure, and capability routing",
            tier=ToolTier.SCRIPT,
            provider_id="provider:local-script",
            capability_ids=["tool:navigate-repo", "wayfinding:subsystem", "repo:navigate"],
            risk="LOW",
            cost_hint=CostHint.ZERO,
            latency_hint=LatencyHint.SUB_SECOND,
            offline_capable=True,
        ),
        ToolDefinition(
            tool_id="tool:audit-docs",
            name="Documentation Auditor",
            purpose="Staleguard Layer 1 syntactic documentation auditor for broken links and manifests",
            tier=ToolTier.SCRIPT,
            provider_id="provider:local-script",
            capability_ids=["tool:audit-docs", "docs:audit", "staleguard:layer1"],
            risk="LOW",
            cost_hint=CostHint.ZERO,
            latency_hint=LatencyHint.SUB_SECOND,
            offline_capable=True,
        ),
        ToolDefinition(
            tool_id="tool:check-changeset",
            name="Changeset Checker",
            purpose="Verifies Same Change Set policy (code + tests + docs travel together)",
            tier=ToolTier.SCRIPT,
            provider_id="provider:local-script",
            capability_ids=["tool:check-changeset", "changeset:check"],
            risk="LOW",
            cost_hint=CostHint.ZERO,
            latency_hint=LatencyHint.SUB_SECOND,
            offline_capable=True,
        ),
        ToolDefinition(
            tool_id="tool:check-worktree",
            name="Worktree Checker",
            purpose="Verifies git working tree status and untracked artifacts",
            tier=ToolTier.SCRIPT,
            provider_id="provider:local-script",
            capability_ids=["tool:check-worktree", "worktree:check"],
            risk="LOW",
            cost_hint=CostHint.ZERO,
            latency_hint=LatencyHint.SUB_SECOND,
            offline_capable=True,
        ),
        ToolDefinition(
            tool_id="tool:adapt-project",
            name="Project Adapter Tool",
            purpose="Proposes and validates project-specific adaptation without modifying AntiOS Core",
            tier=ToolTier.SCRIPT,
            provider_id="provider:local-script",
            capability_ids=["tool:adapt-project", "adaptation:generate"],
            risk="MEDIUM",
            cost_hint=CostHint.ZERO,
            latency_hint=LatencyHint.SECONDS,
            offline_capable=True,
        ),
        ToolDefinition(
            tool_id="tool:distill-memory",
            name="Memory Distiller",
            purpose="Extracts durable architectural lessons into memory store",
            tier=ToolTier.SCRIPT,
            provider_id="provider:local-script",
            capability_ids=["tool:distill-memory", "memory:distill"],
            risk="LOW",
            cost_hint=CostHint.ZERO,
            latency_hint=LatencyHint.SUB_SECOND,
            offline_capable=True,
        ),
        ToolDefinition(
            tool_id="tool:recover-session",
            name="Session Recovery",
            purpose="Recovers AntiOS session context from transcripts and memory",
            tier=ToolTier.SCRIPT,
            provider_id="provider:local-script",
            capability_ids=["tool:recover-session", "session:recover"],
            risk="LOW",
            cost_hint=CostHint.ZERO,
            latency_hint=LatencyHint.SUB_SECOND,
            offline_capable=True,
        ),
    ]
    for st in script_tools:
        registry.register_tool(st)

    # 2.3 Project-Local Tools
    project_tools = [
        ToolDefinition(
            tool_id="tool:project-test-runner",
            name="Project Test Runner",
            purpose="Executes project-local test suite (e.g. pytest, npm test, cargo test)",
            tier=ToolTier.PROJECT,
            provider_id="provider:project-local",
            capability_ids=["tool:project-test-runner", "test:run"],
            risk="MEDIUM",
            cost_hint=CostHint.ZERO,
            latency_hint=LatencyHint.SECONDS,
            offline_capable=True,
        ),
        ToolDefinition(
            tool_id="tool:project-linter",
            name="Project Linter",
            purpose="Executes project-local linter / formatter (e.g. flake8, eslint, clippy)",
            tier=ToolTier.PROJECT,
            provider_id="provider:project-local",
            capability_ids=["tool:project-linter", "lint:run"],
            risk="LOW",
            cost_hint=CostHint.ZERO,
            latency_hint=LatencyHint.SECONDS,
            offline_capable=True,
        ),
    ]
    for pt in project_tools:
        registry.register_tool(pt)

    # 2.4 External Tools
    external_tools = [
        ToolDefinition(
            tool_id="tool:external-git",
            name="External Git Binary",
            purpose="Invokes system Git binary for local repository operations",
            tier=ToolTier.EXTERNAL,
            provider_id="provider:external-cli",
            capability_ids=["tool:external-git", "git:status", "git:diff", "git:log", "git:branch"],
            risk="LOW",
            cost_hint=CostHint.ZERO,
            latency_hint=LatencyHint.SUB_SECOND,
            offline_capable=True,
        ),
        ToolDefinition(
            tool_id="tool:external-python",
            name="External Python Interpreter",
            purpose="Invokes system Python interpreter for standalone verification scripts",
            tier=ToolTier.EXTERNAL,
            provider_id="provider:external-cli",
            capability_ids=["tool:external-python", "python:exec"],
            risk="MEDIUM",
            cost_hint=CostHint.ZERO,
            latency_hint=LatencyHint.SUB_SECOND,
            offline_capable=True,
        ),
    ]
    for et in external_tools:
        registry.register_tool(et)

    # 2.5 MCP Tools
    mcp_tools = [
        ToolDefinition(
            tool_id="tool:mcp-chrome-inspect",
            name="Chrome DevTools DOM Inspector",
            purpose="Inspects browser DOM, styles, accessibility nodes, and layout",
            tier=ToolTier.MCP,
            provider_id="provider:chrome-devtools",
            capability_ids=["browser:dom-inspection", "browser:a11y-audit", "browser:layout-debug"],
            risk="LOW",
            cost_hint=CostHint.MEDIUM,
            latency_hint=LatencyHint.SECONDS,
            offline_capable=True,
            evidence="ANTIOS_MCP_POLICY.md: Chrome DevTools MCP provides irreplaceable live DOM & a11y inspection.",
        ),
        ToolDefinition(
            tool_id="tool:mcp-playwright-exec",
            name="Playwright Browser Runner",
            purpose="Automates browser interactions and takes visual snapshots",
            tier=ToolTier.MCP,
            provider_id="provider:playwright",
            capability_ids=["browser:e2e-automation", "browser:screenshot", "browser:interaction"],
            risk="MEDIUM",
            cost_hint=CostHint.HIGH,
            latency_hint=LatencyHint.SECONDS,
            offline_capable=True,
            evidence="ANTIOS_MCP_POLICY.md: Playwright MCP provides headless browser automation.",
        ),
        ToolDefinition(
            tool_id="tool:mcp-gemini-search-docs",
            name="Gemini API Docs Retriever",
            purpose="Retrieves current upstream Google Gemini API & SDK documentation",
            tier=ToolTier.MCP,
            provider_id="provider:gemini-api-docs",
            capability_ids=["docs:gemini-api-search", "docs:upstream-sdk-reference"],
            locality=Locality.REMOTE,
            risk="LOW",
            cost_hint=CostHint.LOW,
            latency_hint=LatencyHint.SECONDS,
            offline_capable=False,
            evidence="ANTIOS_MCP_POLICY.md: Upstream SDK reference retrieval.",
        ),
        ToolDefinition(
            tool_id="tool:mcp-github-create-pr",
            name="GitHub Remote PR Creator",
            purpose="Creates and manages remote pull requests on GitHub",
            tier=ToolTier.MCP,
            provider_id="provider:github",
            capability_ids=["github:create-pull-request", "github:list-pull-requests"],
            supported_task_types=["CREATE_PR", "LIST_PRS", "REMOTE_PR_MANAGEMENT"],
            locality=Locality.REMOTE,
            risk="HIGH",
            cost_hint=CostHint.HIGH,
            latency_hint=LatencyHint.SECONDS,
            offline_capable=False,
            evidence="ANTIOS_MCP_POLICY.md: Strictly for remote PR management; local git remains native.",
        ),
    ]
    for mt in mcp_tools:
        registry.register_tool(mt)

    # 2.6 Explicitly Forbidden / Rejected MCP Tools
    for rej_tool_id, rej_name, rej_prov, rej_cap in [
        ("tool:mcp-notion-api", "Notion API Tool", "provider:notion", "tool:mcp-notion"),
        ("tool:mcp-postman-api", "Postman API Tool", "provider:postman", "tool:mcp-postman"),
        ("tool:mcp-posthog-api", "PostHog Analytics Tool", "provider:posthog", "tool:mcp-posthog"),
    ]:
        registry.register_tool(
            ToolDefinition(
                tool_id=rej_tool_id,
                name=rej_name,
                purpose=f"REJECTED: {rej_name} is forbidden under AntiOS policy",
                tier=ToolTier.MCP,
                provider_id=rej_prov,
                capability_ids=[rej_cap],
                locality=Locality.REMOTE,
                availability=ProviderAvailability.POLICY_BLOCKED,
                risk="CRITICAL",
                cost_hint=CostHint.HIGH,
                latency_hint=LatencyHint.SECONDS,
                offline_capable=False,
                enabled=False,
                policy_status=ToolPolicyStatus.FORBIDDEN,
                evidence="ANTIOS_MCP_POLICY.md: Unauthorized MCP server strictly forbidden.",
            )
        )

    # =========================================================================
    # 3. ADAPTER MERGE (antios.config.json)
    # =========================================================================
    if config is not None:
        _apply_adapter_tool_config(registry, config)

    return registry


def _apply_adapter_tool_config(registry: ToolRegistry, config: Any) -> None:
    """Safely merge project adapter tool configurations without violating core invariants."""
    # Read tool config if present
    tool_conf = getattr(config, "tools", None)
    if tool_conf is None and isinstance(config, dict):
        tool_conf = config.get("tools", {})
    elif tool_conf is not None and hasattr(tool_conf, "__dict__"):
        tool_conf = tool_conf.__dict__
    elif tool_conf is None:
        tool_conf = {}

    # 1. Disabled tools
    disabled_tools = tool_conf.get("disabled_tools", [])
    for tid in disabled_tools:
        # Invariant: Core native tools and core scripts cannot be disabled by adapter
        if tid in ["tool:native-run-command", "tool:navigate-repo", "tool:audit-docs", "tool:check-changeset"]:
            continue  # Protection of core invariant tools
        tool = registry.get_tool(tid)
        if tool:
            tool.enabled = False
            tool.policy_status = ToolPolicyStatus.RESTRICTED

    # 2. Preferred tools
    preferred_tools = tool_conf.get("preferred_tools", {})
    for cap_id, preferred_tid in preferred_tools.items():
        tool = registry.get_tool(preferred_tid)
        if tool and tool.enabled:
            tool.metadata["adapter_preferred_for"] = cap_id
