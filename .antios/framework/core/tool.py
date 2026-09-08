"""AntiOS Minimal Tool Abstraction.

Defines a clean, lightweight abstraction for tool identity, capability tiers,
standardized execution results, structured failure classification, and tool
selection policy without wrapping native Antigravity tools or creating an
artificial agent runtime.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ToolTier(str, Enum):
    """Tier of tool capability under AntiOS tool selection policy."""
    NATIVE = "NATIVE"      # Antigravity native tool (highest priority)
    SCRIPT = "SCRIPT"      # Deterministic local script (framework/scripts/tools/)
    PROJECT = "PROJECT"    # Project-local tool (project test runners, linters, scripts)
    EXTERNAL = "EXTERNAL"  # Standard external CLI / SDK (git CLI, python binary)
    MCP = "MCP"            # Model Context Protocol external server (selective)


class HybridCapabilityTier(int, Enum):
    """The 8 canonical capability tiers under Phase 86 strict priority hierarchy.

    Strict Resolution Order:
      1. Native Antigravity Built-in Tool
      2. Project-Native Skill (.agents/skills/)
      3. Project Tool / Script
      4. AntiOS Core Runtime Service
      5. Antigravity Built-in Specialist Agent
      6. Standard CLI Execution
      7. User-Approved External Service
      8. Managed MCP Tool (highest barrier, mandatory 7-field escalation audit)
    """
    TIER_1_NATIVE_BUILTIN = 1
    TIER_2_PROJECT_NATIVE_SKILL = 2
    TIER_3_PROJECT_TOOL_SCRIPT = 3
    TIER_4_ANTIOS_CORE_RUNTIME = 4
    TIER_5_SPECIALIST_AGENT = 5
    TIER_6_STANDARD_CLI = 6
    TIER_7_EXTERNAL_SERVICE = 7
    TIER_8_MANAGED_MCP = 8


class ExecutionMode(str, Enum):
    """Execution mode of a tool."""
    SYNCHRONOUS = "SYNCHRONOUS"
    ASYNC = "ASYNC"
    DAEMON = "DAEMON"


class Locality(str, Enum):
    """Locality of execution."""
    LOCAL = "LOCAL"
    REMOTE = "REMOTE"


class ProviderAvailability(str, Enum):
    """Operational availability status of a tool provider."""
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    MISCONFIGURED = "MISCONFIGURED"


class CostHint(str, Enum):
    """Estimated token / resource cost level."""
    ZERO = "ZERO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class LatencyHint(str, Enum):
    """Estimated execution latency."""
    SUB_SECOND = "SUB_SECOND"
    SECONDS = "SECONDS"
    MINUTES = "MINUTES"
    UNKNOWN = "UNKNOWN"


class ToolPolicyStatus(str, Enum):
    """Policy classification for tool usage."""
    PERMITTED = "PERMITTED"
    RESTRICTED = "RESTRICTED"
    FORBIDDEN = "FORBIDDEN"


class ToolStatus(str, Enum):
    """Standardized tool execution status."""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    DENIED = "DENIED"
    TIMEOUT = "TIMEOUT"


class FailureClass(str, Enum):
    """Structured failure taxonomy for tool execution and verification."""
    NONE = "NONE"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    TIMEOUT = "TIMEOUT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    POLICY_DENIED = "POLICY_DENIED"
    ENVIRONMENT_MISSING = "ENVIRONMENT_MISSING"
    EXECUTION_FAILED = "EXECUTION_FAILED"


@dataclass(frozen=True)
class ToolIdentity:
    """Identity and metadata for an executable tool capability."""
    tool_id: str
    name: str
    tier: ToolTier
    description: str
    entrypoint: str
    applicable_platforms: List[str] = field(default_factory=lambda: ["win32", "linux", "darwin"])
    requires_network: bool = False
    is_deterministic: bool = True


@dataclass
class ToolDefinition:
    """Canonical executable tool model under AntiOS governance."""
    tool_id: str
    name: str
    purpose: str
    tier: ToolTier
    provider_id: str
    capability_ids: List[str] = field(default_factory=list)
    supported_task_types: List[str] = field(default_factory=lambda: ["*"])
    supported_subsystems: List[str] = field(default_factory=lambda: ["*"])
    execution_mode: ExecutionMode = ExecutionMode.SYNCHRONOUS
    locality: Locality = Locality.LOCAL
    availability: ProviderAvailability = ProviderAvailability.AVAILABLE
    prerequisites: List[str] = field(default_factory=list)
    risk: str = "LOW"
    cost_hint: CostHint = CostHint.LOW
    latency_hint: LatencyHint = LatencyHint.SUB_SECOND
    offline_capable: bool = True
    evidence: str = ""
    source: str = ""
    enabled: bool = True
    policy_status: ToolPolicyStatus = ToolPolicyStatus.PERMITTED
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_applicable_to_subsystem(self, subsystem_id: str) -> bool:
        if "*" in self.supported_subsystems:
            return True
        return subsystem_id in self.supported_subsystems

    def is_applicable_to_task(self, task_type: str) -> bool:
        if "*" in self.supported_task_types:
            return True
        return task_type.upper() in [t.upper() for t in self.supported_task_types]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "purpose": self.purpose,
            "tier": self.tier.value,
            "provider_id": self.provider_id,
            "capability_ids": list(self.capability_ids),
            "supported_task_types": list(self.supported_task_types),
            "supported_subsystems": list(self.supported_subsystems),
            "execution_mode": self.execution_mode.value,
            "locality": self.locality.value,
            "availability": self.availability.value,
            "prerequisites": list(self.prerequisites),
            "risk": self.risk,
            "cost_hint": self.cost_hint.value,
            "latency_hint": self.latency_hint.value,
            "offline_capable": self.offline_capable,
            "evidence": self.evidence,
            "source": self.source,
            "enabled": self.enabled,
            "policy_status": self.policy_status.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ToolDefinition:
        tier_val = data.get("tier", "SCRIPT")
        tier = ToolTier(tier_val) if isinstance(tier_val, str) else tier_val
        exec_mode_val = data.get("execution_mode", "SYNCHRONOUS")
        exec_mode = ExecutionMode(exec_mode_val) if isinstance(exec_mode_val, str) else exec_mode_val
        locality_val = data.get("locality", "LOCAL")
        locality = Locality(locality_val) if isinstance(locality_val, str) else locality_val
        avail_val = data.get("availability", "AVAILABLE")
        avail = ProviderAvailability(avail_val) if isinstance(avail_val, str) else avail_val
        cost_val = data.get("cost_hint", "LOW")
        cost = CostHint(cost_val) if isinstance(cost_val, str) else cost_val
        latency_val = data.get("latency_hint", "SUB_SECOND")
        latency = LatencyHint(latency_val) if isinstance(latency_val, str) else latency_val
        pol_val = data.get("policy_status", "PERMITTED")
        pol = ToolPolicyStatus(pol_val) if isinstance(pol_val, str) else pol_val

        return cls(
            tool_id=data["tool_id"],
            name=data["name"],
            purpose=data.get("purpose", ""),
            tier=tier,
            provider_id=data.get("provider_id", "provider:native"),
            capability_ids=data.get("capability_ids", []),
            supported_task_types=data.get("supported_task_types", ["*"]),
            supported_subsystems=data.get("supported_subsystems", ["*"]),
            execution_mode=exec_mode,
            locality=locality,
            availability=avail,
            prerequisites=data.get("prerequisites", []),
            risk=data.get("risk", "LOW"),
            cost_hint=cost,
            latency_hint=latency,
            offline_capable=data.get("offline_capable", True),
            evidence=data.get("evidence", ""),
            source=data.get("source", ""),
            enabled=data.get("enabled", True),
            policy_status=pol,
            metadata=data.get("metadata", {}),
        )


@dataclass
class ToolResult:
    """Standardized result emitted by tool executions."""
    status: ToolStatus
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    data: Optional[Dict[str, Any]] = None
    failure_class: FailureClass = FailureClass.NONE
    failure_reason: Optional[str] = None
    evidence: List[str] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        return self.status == ToolStatus.SUCCESS and self.exit_code == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "data": self.data or {},
            "failure_class": self.failure_class.value,
            "failure_reason": self.failure_reason,
            "evidence": self.evidence,
        }

    @classmethod
    def success(cls, stdout: str = "", data: Optional[Dict[str, Any]] = None, evidence: Optional[List[str]] = None) -> ToolResult:
        return cls(
            status=ToolStatus.SUCCESS,
            exit_code=0,
            stdout=stdout,
            data=data or {},
            evidence=evidence or [],
        )

    @classmethod
    def failure(
        cls,
        failure_class: FailureClass,
        reason: str,
        exit_code: int = 1,
        stdout: str = "",
        stderr: str = "",
        evidence: Optional[List[str]] = None,
    ) -> ToolResult:
        return cls(
            status=ToolStatus.FAILURE,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            failure_class=failure_class,
            failure_reason=reason,
            evidence=evidence or [],
        )

    @classmethod
    def denied(cls, reason: str, evidence: Optional[List[str]] = None) -> ToolResult:
        return cls(
            status=ToolStatus.DENIED,
            exit_code=126,
            failure_class=FailureClass.POLICY_DENIED,
            failure_reason=reason,
            evidence=evidence or [],
        )

    @classmethod
    def timeout(cls, seconds: int, evidence: Optional[List[str]] = None) -> ToolResult:
        return cls(
            status=ToolStatus.TIMEOUT,
            exit_code=124,
            failure_class=FailureClass.TIMEOUT,
            failure_reason=f"Tool execution timed out after {seconds} seconds",
            evidence=evidence or [],
        )


class ToolSelectionPolicy:
    """AntiOS 3-Tier Tool Selection Policy:
    
    1. Prefer Antigravity native capability.
    2. If unavailable, prefer a deterministic local script.
    3. Use MCP only when a separate process/tool protocol gives meaningful capability.
    """

    @staticmethod
    def select_tool_tier(has_native: bool, has_script: bool, mcp_justified: bool) -> ToolTier:
        if has_native:
            return ToolTier.NATIVE
        if has_script:
            return ToolTier.SCRIPT
        if mcp_justified:
            return ToolTier.MCP
        return ToolTier.SCRIPT
