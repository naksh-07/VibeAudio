"""AntiOS Capability Pack Data Model & Formatting Engine.

Defines the compact, agent-facing capability bundle emitted for a specific task.
Guarantees strict token budgets:
- Summary card <= 15 lines
- Full Capability Pack card <= 25 lines
- Complete JSON emission for tool/script programmatic consumers
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
import json
from typing import Any, Dict, List, Optional


@dataclass
class CapabilityPack:
    """Bounded, agent-facing capability resolution result for a specific task."""
    pack_id: str
    project_name: str
    task_intent: str
    task_class: str
    risk_tier: str
    matched_subsystems: List[str]
    matched_components: List[str]
    workflow: Dict[str, Any]
    skills: List[Dict[str, Any]]
    rules: List[Dict[str, Any]]
    tools: List[Dict[str, Any]]
    verifier: Dict[str, Any]
    specialists: List[Dict[str, Any]]
    providers: List[Dict[str, Any]]
    mcp_decision: Dict[str, Any]
    why_selected: Dict[str, str]
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    unknowns: List[Dict[str, Any]] = field(default_factory=list)
    evidence: str = ""
    confidence: float = 1.0
    epistemic_state: str = "OBSERVED"
    irrelevant_capabilities_filtered: int = 0

    def format_card(self, max_lines: int = 25) -> str:
        """Renders a token-bounded text card adhering to token budget (<= max_lines)."""
        subs_str = ", ".join(self.matched_subsystems) if self.matched_subsystems else "UNKNOWN"
        comps_str = ", ".join(self.matched_components[:2]) if self.matched_components else "None"
        wf_name = self.workflow.get("name", "Unknown Workflow")
        
        skill_names = [s.get("name", s.get("capability_id", "")) for s in self.skills]
        skills_str = ", ".join(skill_names[:2]) if skill_names else "antios-engineer"

        rule_summaries = [r.get("name", r.get("capability_id", "")) for r in self.rules]
        rules_str = "; ".join(rule_summaries[:2]) if rule_summaries else "Core invariants"

        tool_names = [t.get("name", t.get("capability_id", "")) for t in self.tools]
        tools_str = ", ".join(tool_names[:2]) if tool_names else "tests/run_all.py"

        verif_name = self.verifier.get("name", self.verifier.get("capability_id", "Solo Verifier"))
        vtype = self.verifier.get("metadata", {}).get("verifier_type", "SOLO_VERIFIER")
        verif_str = f"{verif_name} ({vtype})"

        spec_name = self.specialists[0].get("name", "Core Engineer") if self.specialists else "Core Engineer"
        
        mcp_status = self.mcp_decision.get("status", "NOT_NEEDED")
        mcp_summary = f"{mcp_status}: {self.mcp_decision.get('justification', '')[:40]}"

        # Compact rationale summary
        why_items = [f"{k}->{v}" for k, v in list(self.why_selected.items())[:2]]
        why_str = "; ".join(why_items) if why_items else "Matched task class & locality"

        lines = [
            "=== ANTIOS CAPABILITY PACK ===",
            f"Project:      {self.project_name}",
            f"Task Class:   {self.task_class} [Risk: {self.risk_tier}]",
            f"Subsystem:    {subs_str} (Component: {comps_str})",
            f"Workflow:     {wf_name}",
            f"Skills:       {skills_str}",
            f"Rules:        {rules_str}",
            f"Tools:        {tools_str}",
            f"Verifier:     {verif_str}",
            f"Specialist:   {spec_name}",
            f"MCP Decision: {mcp_summary}",
            f"Selection:    {why_str}",
        ]

        if self.conflicts:
            c_desc = self.conflicts[0].get("description", "Rule conflict surfaced")
            lines.append(f"Conflicts:    [SURFACED] {c_desc[:50]}")
        else:
            lines.append("Conflicts:    None detected (Rules consistent)")

        if self.unknowns:
            u_field = self.unknowns[0].get("field", "UNKNOWN")
            lines.append(f"Gaps:         [UNKNOWN] {u_field}")
        else:
            lines.append(f"Filtered:     {self.irrelevant_capabilities_filtered} irrelevant capabilities excluded")

        lines.append(f"Epistemic:    {self.epistemic_state} (Confidence: {self.confidence:.2f})")
        lines.append("==============================")

        # Enforce hard line limit
        return "\n".join(lines[:max_lines])

    def format_summary(self) -> str:
        """Renders an ultra-compact summary card (<= 15 lines)."""
        subs_str = ", ".join(self.matched_subsystems) if self.matched_subsystems else "UNKNOWN"
        wf_name = self.workflow.get("name", "Unknown Workflow")
        skills_str = ", ".join([s.get("capability_id", "") for s in self.skills[:2]])
        verif_name = self.verifier.get("name", "Solo Verifier")

        return "\n".join([
            "=== ANTIOS CAPABILITY SUMMARY ===",
            f"Task:       {self.task_intent[:50]}",
            f"Class/Risk: {self.task_class} | {self.risk_tier}",
            f"Subsystem:  {subs_str}",
            f"Workflow:   {wf_name}",
            f"Skills:     {skills_str}",
            f"Verifier:   {verif_name}",
            f"Confidence: {self.confidence:.2f} ({self.epistemic_state})",
            "=================================",
        ])

    def to_dict(self) -> Dict[str, Any]:
        """Serializes capability pack to dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serializes capability pack to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CapabilityPack:
        """Deserializes capability pack from dictionary."""
        return cls(**data)
