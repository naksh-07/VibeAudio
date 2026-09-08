"""AntiOS Tool Routing Pack.

Represents the compact, bounded, inspectable result of deterministic tool and
provider selection under AntiOS governance.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import json
import uuid
from typing import Any, Dict, List, Optional

from framework.core.tool import ProviderAvailability, ToolTier


@dataclass
class ToolRoutingPack:
    """Bounded, serializable representation of selected execution mechanism."""
    pack_id: str
    task_intent: str
    task_class: str
    matched_subsystems: List[str]
    capability_id: str
    agent_role_id: str
    selected_tool_id: Optional[str]
    selected_tool_name: str
    selected_provider_id: Optional[str]
    execution_tier: ToolTier
    why_selected: str
    alternatives_considered: List[Dict[str, Any]] = field(default_factory=list)
    why_alternatives_rejected: List[str] = field(default_factory=list)
    mcp_status: str = "NOT_NEEDED"
    mcp_justification: str = ""
    availability: ProviderAvailability = ProviderAvailability.AVAILABLE
    offline_mode: bool = False
    authorization_status: str = "AUTHORIZED"
    authorization_reason: str = ""
    evidence: str = ""
    confidence: float = 1.0
    epistemic_state: str = "OBSERVED"

    def format_card(self, max_lines: int = 25) -> str:
        """Render a compact Markdown card bounded strictly to max_lines."""
        lines = [
            f"### [Tool Routing: {self.pack_id[:8]}]",
            f"- **TASK**: {self.task_intent[:50]}",
            f"- **SUBSYSTEM**: {', '.join(self.matched_subsystems) or 'NONE'}",
            f"- **CAPABILITY**: {self.capability_id}",
            f"- **AGENT ROLE**: {self.agent_role_id}",
            f"- **SELECTED TOOL**: {self.selected_tool_name} (`{self.selected_tool_id}`)",
            f"- **PROVIDER**: {self.selected_provider_id} (Tier: {self.execution_tier.value})",
            f"- **WHY SELECTED**: {self.why_selected[:70]}",
            f"- **ALTERNATIVES**: {len(self.alternatives_considered)} considered",
            f"- **MCP STATUS**: {self.mcp_status}",
            f"- **AVAILABILITY**: {self.availability.value}",
            f"- **AUTHORIZATION**: {self.authorization_status}",
        ]
        if self.authorization_status == "BLOCKED":
            lines.append(f"- **BLOCK REASON**: {self.authorization_reason[:65]}")
        if self.mcp_justification:
            lines.append(f"- **MCP REASON**: {self.mcp_justification[:65]}")
        if self.evidence:
            lines.append(f"- **EVIDENCE**: {self.evidence[:65]}")

        # Strict line bounding
        return "\n".join(lines[:max_lines])

    def format_summary(self, max_lines: int = 15) -> str:
        """Render a high-level summary bounded strictly to max_lines."""
        lines = [
            f"**Tool Selection** [{self.execution_tier.value}]: {self.selected_tool_name}",
            f"  Provider: {self.selected_provider_id} | Capability: {self.capability_id}",
            f"  Agent: {self.agent_role_id} | Auth: {self.authorization_status}",
            f"  MCP: {self.mcp_status} | Availability: {self.availability.value}",
        ]
        return "\n".join(lines[:max_lines])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "task_intent": self.task_intent,
            "task_class": self.task_class,
            "matched_subsystems": list(self.matched_subsystems),
            "capability_id": self.capability_id,
            "agent_role_id": self.agent_role_id,
            "selected_tool_id": self.selected_tool_id,
            "selected_tool_name": self.selected_tool_name,
            "selected_provider_id": self.selected_provider_id,
            "execution_tier": self.execution_tier.value,
            "why_selected": self.why_selected,
            "alternatives_considered": self.alternatives_considered,
            "why_alternatives_rejected": list(self.why_alternatives_rejected),
            "mcp_status": self.mcp_status,
            "mcp_justification": self.mcp_justification,
            "availability": self.availability.value,
            "offline_mode": self.offline_mode,
            "authorization_status": self.authorization_status,
            "authorization_reason": self.authorization_reason,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "epistemic_state": self.epistemic_state,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ToolRoutingPack:
        tier_val = data.get("execution_tier", "SCRIPT")
        tier = ToolTier(tier_val) if isinstance(tier_val, str) else tier_val
        avail_val = data.get("availability", "AVAILABLE")
        avail = ProviderAvailability(avail_val) if isinstance(avail_val, str) else avail_val

        return cls(
            pack_id=data.get("pack_id", str(uuid.uuid4())),
            task_intent=data["task_intent"],
            task_class=data.get("task_class", "FEATURE"),
            matched_subsystems=data.get("matched_subsystems", []),
            capability_id=data["capability_id"],
            agent_role_id=data.get("agent_role_id", "role:primary-engineer"),
            selected_tool_id=data.get("selected_tool_id"),
            selected_tool_name=data.get("selected_tool_name", "Unknown"),
            selected_provider_id=data.get("selected_provider_id"),
            execution_tier=tier,
            why_selected=data.get("why_selected", ""),
            alternatives_considered=data.get("alternatives_considered", []),
            why_alternatives_rejected=data.get("why_alternatives_rejected", []),
            mcp_status=data.get("mcp_status", "NOT_NEEDED"),
            mcp_justification=data.get("mcp_justification", ""),
            availability=avail,
            offline_mode=data.get("offline_mode", False),
            authorization_status=data.get("authorization_status", "AUTHORIZED"),
            authorization_reason=data.get("authorization_reason", ""),
            evidence=data.get("evidence", ""),
            confidence=data.get("confidence", 1.0),
            epistemic_state=data.get("epistemic_state", "OBSERVED"),
        )
