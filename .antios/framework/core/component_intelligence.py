"""AntiOS 2.0 Component Intelligence Engine.

Phase 56: Answers "For this component, what do I need to know before modifying it?"
Resolves:
USER INTENT
    ↓
UI / LOGIC SUBSYSTEM
    ↓
AUTHORITATIVE COMPONENT
    ↓
DESIGN / PROJECT RULES
    ↓
RELEVANT CAPABILITY
    ↓
RELEVANT SPECIALIST
    ↓
TEST SURFACE
    ↓
CONSUMERS
    ↓
BLAST RADIUS
    ↓
VERIFICATION CONTRACT

Extends Phase 28-30 wayfinding without blind repository crawling.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import os
from typing import Any, Dict, List, Optional, Set, Tuple

from framework.core.subsystem import SubsystemDeclaration
from framework.core.knowledge import KnowledgeGraph
from framework.core.wayfinding import LocalityResolution, WayfindingEngine


@dataclass(frozen=True)
class ComponentIntelligenceReport:
    """Bounded, actionable intelligence for an agent prior to modifying code."""
    query: str
    component_id: str
    identity: str
    purpose: str
    authoritative_location: List[str]
    entrypoints: List[str]
    interfaces: List[str]
    dependencies: List[str]
    consumers: List[str]
    transitive_consumers: List[str]
    governing_rules: List[str]
    relevant_skills: List[str]
    relevant_specialists: List[str]
    covering_tests: List[str]
    test_commands: List[str]
    owner: Optional[str]
    owner_source: str
    owner_confidence: float
    risk_tier: str
    blast_radius: Dict[str, Any]
    verification_requirements: List[str]
    epistemic_provenance: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ComponentIntelligenceResolver:
    """Resolves comprehensive pre-modification intelligence for target components."""

    @staticmethod
    def resolve(
        query_or_path: str,
        wayfinding: WayfindingEngine,
        knowledge_graph: Optional[KnowledgeGraph] = None,
    ) -> Optional[ComponentIntelligenceReport]:
        """Resolves pre-modification intelligence from query or path."""
        loc = wayfinding.locate(query_or_path)
        if not loc:
            return None

        kg = knowledge_graph or wayfinding.knowledge_graph
        blast_info = kg.calculate_blast_radius(loc.matched_subsystem_id)

        # 1. Authoritative Location & Interfaces
        auth_loc = list(loc.authoritative_files)
        if not auth_loc and loc.entrypoints:
            auth_loc = list(loc.entrypoints)
        interfaces = list(loc.entrypoints)

        # 2. Governing Rules & Invariants
        governing_rules = list(loc.governing_rules) + list(loc.protected_invariants)

        # 3. Relevant Skills
        skills = list(loc.applicable_skills)
        if ".agents/skills/antios/SKILL.md" not in skills and "antios" not in skills:
            skills.insert(0, "antios")

        # 4. Relevant Specialists
        specialists: List[str] = []
        if loc.area.lower() in ["ui", "frontend", "web"]:
            specialists.append("frontend-specialist")
        elif loc.area.lower() in ["db", "database", "storage"]:
            specialists.append("database-specialist")
        elif loc.area.lower() in ["api", "service", "backend"]:
            specialists.append("api-specialist")
        # Default canonical roles
        specialists.append("role:primary-engineer")
        if loc.risk_tier in ["HIGH", "CRITICAL"]:
            specialists.append("role:independent-verifier")

        # 5. Verification Requirements
        verification_reqs: List[str] = []
        for cmd in loc.test_commands:
            verification_reqs.append(f"EXECUTE: {cmd}")
        if loc.risk_tier in ["HIGH", "CRITICAL"]:
            verification_reqs.append("RATCHET: Maker-Checker independent verification audit required")
        else:
            verification_reqs.append("RATCHET: Solo verification with clean exit code 0 required")

        # 6. Epistemic Provenance
        provenance = {
            "source_subsystem": loc.matched_subsystem_id,
            "match_confidence": loc.confidence,
            "epistemic_state": loc.epistemic_state,
            "owner_source": loc.owner_source,
            "owner_confidence": loc.owner_confidence,
        }

        return ComponentIntelligenceReport(
            query=query_or_path,
            component_id=loc.matched_subsystem_id,
            identity=loc.name,
            purpose=loc.purpose or loc.description,
            authoritative_location=auth_loc,
            entrypoints=loc.entrypoints,
            interfaces=interfaces,
            dependencies=loc.dependencies,
            consumers=loc.consumers,
            transitive_consumers=loc.transitive_consumers,
            governing_rules=governing_rules,
            relevant_skills=skills,
            relevant_specialists=specialists,
            covering_tests=loc.covering_tests,
            test_commands=loc.test_commands,
            owner=loc.owner,
            owner_source=loc.owner_source,
            owner_confidence=loc.owner_confidence,
            risk_tier=loc.risk_tier,
            blast_radius=blast_info,
            verification_requirements=verification_reqs,
            epistemic_provenance=provenance,
        )

    @staticmethod
    def render_card(report: ComponentIntelligenceReport) -> str:
        """Renders token-bounded Pre-Modification Intelligence Card (<= 25 lines)."""
        lines = [
            f"[Component Intelligence — {report.identity}] ({report.component_id})",
            f"Purpose:        {report.purpose[:70]}...",
            f"Location:       {', '.join(report.authoritative_location[:3]) if report.authoritative_location else 'Declared root'}",
            f"Risk Tier:      {report.risk_tier} | Owner: {report.owner or 'UNKNOWN'} ({report.owner_source})",
            f"Dependencies:   {', '.join(report.dependencies[:4]) if report.dependencies else 'None'}",
            f"Downstream:     {len(report.consumers)} direct, {len(report.transitive_consumers)} transitive consumers",
            f"Covering Tests: {', '.join(report.covering_tests[:3]) if report.covering_tests else 'None declared'}",
            f"Test Commands:  {'; '.join(report.test_commands[:2]) if report.test_commands else 'None declared'}",
            f"Governing:      {', '.join(report.governing_rules[:3]) if report.governing_rules else 'Standard policies'}",
            f"Skills/Roles:   Skills: {', '.join(report.relevant_skills[:2])} | Specialists: {', '.join(report.relevant_specialists[:2])}",
            f"Verification:   {'; '.join(report.verification_requirements[:2])}",
            f"Provenance:     Confidence={report.epistemic_provenance.get('match_confidence', 1.0)} | State={report.epistemic_provenance.get('epistemic_state', 'OBSERVED')}",
        ]
        return "\n".join(lines[:25])
