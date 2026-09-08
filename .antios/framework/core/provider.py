"""AntiOS Canonical Provider Abstraction.

Defines execution providers exposing capabilities and tools across:
- Antigravity Native Tooling
- Local Deterministic Scripts
- Project-Local Tools
- Standard External CLI / SDK
- Model Context Protocol (MCP) Transports
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from framework.core.tool import Locality, ProviderAvailability


class ProviderType(str, Enum):
    """Transport / execution category of capability providers."""
    NATIVE = "NATIVE"
    LOCAL_SCRIPT = "LOCAL_SCRIPT"
    PROJECT = "PROJECT"
    EXTERNAL = "EXTERNAL"
    MCP = "MCP"


class ProviderPolicyStatus(str, Enum):
    """Constitutional policy classification for a provider under AntiOS governance."""
    PERMITTED = "PERMITTED"
    RESTRICTED = "RESTRICTED"
    REJECTED = "REJECTED"


@dataclass
class ProviderDefinition:
    """Canonical model for a capability/tool execution provider."""
    provider_id: str
    name: str
    provider_type: ProviderType
    capabilities: List[str] = field(default_factory=list)
    exposed_tools: List[str] = field(default_factory=list)
    locality: Locality = Locality.LOCAL
    availability: ProviderAvailability = ProviderAvailability.AVAILABLE
    offline_capable: bool = True
    requires_network: bool = False
    permissions_required: List[str] = field(default_factory=list)
    policy_status: ProviderPolicyStatus = ProviderPolicyStatus.PERMITTED
    allowed_tasks: List[str] = field(default_factory=lambda: ["*"])
    forbidden_tasks: List[str] = field(default_factory=list)
    project_scope: str = "*"
    fallback_provider_id: Optional[str] = None
    justification: str = ""
    source: str = ""
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_task_allowed(self, task_type: str) -> bool:
        """Evaluate if the task type is permitted for this provider."""
        t_upper = task_type.upper()
        # Check forbidden first
        for forbidden in self.forbidden_tasks:
            if forbidden == "*" or forbidden.upper() == t_upper:
                return False
        if "*" in self.allowed_tasks:
            return True
        return t_upper in [a.upper() for a in self.allowed_tasks]

    def is_capability_exposed(self, capability_id: str) -> bool:
        """Check if this provider exposes the given capability."""
        if "*" in self.capabilities:
            return True
        return capability_id in self.capabilities

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "name": self.name,
            "provider_type": self.provider_type.value,
            "capabilities": list(self.capabilities),
            "exposed_tools": list(self.exposed_tools),
            "locality": self.locality.value,
            "availability": self.availability.value,
            "offline_capable": self.offline_capable,
            "requires_network": self.requires_network,
            "permissions_required": list(self.permissions_required),
            "policy_status": self.policy_status.value,
            "allowed_tasks": list(self.allowed_tasks),
            "forbidden_tasks": list(self.forbidden_tasks),
            "project_scope": self.project_scope,
            "fallback_provider_id": self.fallback_provider_id,
            "justification": self.justification,
            "source": self.source,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProviderDefinition:
        pt_val = data.get("provider_type", "NATIVE")
        ptype = ProviderType(pt_val) if isinstance(pt_val, str) else pt_val
        locality_val = data.get("locality", "LOCAL")
        locality = Locality(locality_val) if isinstance(locality_val, str) else locality_val
        avail_val = data.get("availability", "AVAILABLE")
        avail = ProviderAvailability(avail_val) if isinstance(avail_val, str) else avail_val
        pol_val = data.get("policy_status", "PERMITTED")
        pol = ProviderPolicyStatus(pol_val) if isinstance(pol_val, str) else pol_val

        return cls(
            provider_id=data["provider_id"],
            name=data["name"],
            provider_type=ptype,
            capabilities=data.get("capabilities", []),
            exposed_tools=data.get("exposed_tools", []),
            locality=locality,
            availability=avail,
            offline_capable=data.get("offline_capable", True),
            requires_network=data.get("requires_network", False),
            permissions_required=data.get("permissions_required", []),
            policy_status=pol,
            allowed_tasks=data.get("allowed_tasks", ["*"]),
            forbidden_tasks=data.get("forbidden_tasks", []),
            project_scope=data.get("project_scope", "*"),
            fallback_provider_id=data.get("fallback_provider_id"),
            justification=data.get("justification", ""),
            source=data.get("source", ""),
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {}),
        )
