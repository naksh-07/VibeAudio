"""AntiOS Agent Routing Pack Data Model & Formatting Engine.

Defines the compact, agent-facing topology and delegation bundle emitted for a specific task.
Guarantees strict token budgets:
- Summary card <= 15 lines
- Full Agent Routing Pack card <= 25 lines
- Complete JSON emission for tool/CLI programmatic consumers
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
import json
from typing import Any, Dict, List, Optional


@dataclass
class AgentRoutingPack:
    """Bounded, agent-facing agent role resolution and delegation bundle."""
    routing_id: str
    task_intent: str
    task_class: str
    risk_tier: str
    matched_subsystems: List[str]
    primary_role: Dict[str, Any]
    delegation_decision: str                   # NO_DELEGATION, DELEGATE_SPECIALIST, etc.
    delegation_reason: str
    selected_specialist: Optional[Dict[str, Any]] = None
    why_selected: str = ""
    why_not_others: Dict[str, str] = field(default_factory=dict)
    capability_boundary: Dict[str, Any] = field(default_factory=dict)
    required_verifier: str = "verifier:solo"
    escalation_policy: str = "RETURN_TO_PRIMARY"
    handoff_contract: Optional[Dict[str, Any]] = None
    confidence: float = 1.0
    evidence: str = ""
    epistemic_state: str = "OBSERVED"

    def format_card(self, max_lines: int = 25) -> str:
        """Renders a token-bounded text card adhering to token budget (<= max_lines)."""
        subs_str = ", ".join(self.matched_subsystems) if self.matched_subsystems else "UNKNOWN"
        primary_name = self.primary_role.get("name", "AntiOS Engineer")
        specialist_name = self.selected_specialist.get("name", "None (Direct Execution)") if self.selected_specialist else "None (Direct Execution)"
        
        # Capability boundary summary
        allowed = self.capability_boundary.get("allowed_capabilities", ["*"])
        forbidden = self.capability_boundary.get("forbidden_capabilities", [])
        allowed_str = ", ".join(allowed[:2]) if allowed else "Standard"
        forbidden_str = ", ".join(forbidden[:2]) if forbidden else "None"

        # Why not others summary
        why_not_items = [f"{k}: {v}" for k, v in list(self.why_not_others.items())[:2]]
        why_not_str = "; ".join(why_not_items) if why_not_items else "No alternative specialists applicable"

        lines = [
            "=== ANTIOS AGENT ROUTING PACK ===",
            f"Task Class:   {self.task_class} [Risk: {self.risk_tier}]",
            f"Subsystem:    {subs_str}",
            f"Primary:      {primary_name}",
            f"Delegation:   {self.delegation_decision}",
            f"Specialist:   {specialist_name}",
            f"Reason:       {self.delegation_reason[:60]}",
            f"Why Selected: {self.why_selected[:60]}",
            f"Why Not:      {why_not_str[:60]}",
            f"Allowed Caps: {allowed_str}",
            f"Forbidden:    {forbidden_str}",
            f"Verifier:     {self.required_verifier}",
            f"Escalation:   {self.escalation_policy}",
            f"Confidence:   {self.confidence:.2f} ({self.epistemic_state})",
            "---------------------------------"
        ]

        if self.handoff_contract:
            c_id = self.handoff_contract.get("contract_id", "contract-001")
            lines.insert(len(lines) - 2, f"Handoff:      Bounded contract [{c_id}] generated")

        # Enforce hard line limit
        return "\n".join(lines[:max_lines])

    def format_summary(self, max_lines: int = 15) -> str:
        """Renders an ultra-compact summary card (<= 15 lines)."""
        subs_str = ", ".join(self.matched_subsystems) if self.matched_subsystems else "UNKNOWN"
        specialist_name = self.selected_specialist.get("name", "None") if self.selected_specialist else "None"

        lines = [
            "=== ANTIOS AGENT ROUTING SUMMARY ===",
            f"Task:        {self.task_intent[:45]}",
            f"Class/Risk:  {self.task_class} | {self.risk_tier}",
            f"Subsystem:   {subs_str}",
            f"Delegation:  {self.delegation_decision}",
            f"Specialist:  {specialist_name}",
            f"Verifier:    {self.required_verifier}",
            f"Confidence:  {self.confidence:.2f} ({self.epistemic_state})",
            "------------------------------------"
        ]
        return "\n".join(lines[:max_lines])

    def to_dict(self) -> Dict[str, Any]:
        """Serializes agent routing pack to dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serializes agent routing pack to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentRoutingPack:
        """Deserializes agent routing pack from dictionary."""
        return cls(**data)
