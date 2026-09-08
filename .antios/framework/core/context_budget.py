"""AntiOS 2.0 Context Budget Governor (Phase 87).

Implements deterministic task-time context budgeting and allocation.
Enforces the fundamental law:
"Optimize USEFUL INFORMATION / CONTEXT COST, not MINIMUM TOKENS AT ANY COST."

Preserves:
- Architecture relationships
- Ownership tiers
- Invariants & immutable core boundaries
- Verification requirements
- Evidence provenance
- Active task state
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple


class ContextClassification(str, Enum):
    """Epistemic classification of candidate context sources."""
    MANDATORY = "MANDATORY"      # Safety invariants, acceptance criteria, active blockers
    RELEVANT = "RELEVANT"        # Targeted component models, covering tests, direct dependencies
    OPTIONAL = "OPTIONAL"        # Historical background, indirect consumers, optional guides
    STALE = "STALE"              # Fingerprint mismatch, modified files, unconfirmed claims
    REDUNDANT = "REDUNDANT"      # Duplicate observations, duplicate summaries, identical skills
    UNKNOWN = "UNKNOWN"          # Unverified or unclassified sources


class GovernorAction(str, Enum):
    """Deterministic allocation decision executed by the governor."""
    LOAD = "LOAD"                # Inject complete bounded context into mission prompt
    DEFER = "DEFER"              # Exclude from initial turn; load on-demand when wave deepens
    SUMMARIZE = "SUMMARIZE"      # Compact via safe summarization, preserving facts & provenance
    DISCARD = "DISCARD"          # Completely omit from context (irrelevant, redundant, or noise)
    REFRESH = "REFRESH"          # Invalidate stale cache; reload fresh from physical disk/manifest


class ContextSourceType(str, Enum):
    """Categorization of candidate context origins."""
    CONSTITUTIONAL_POLICY = "CONSTITUTIONAL_POLICY"
    ACTIVE_MISSION_STATE = "ACTIVE_MISSION_STATE"
    PROJECT_ANATOMY = "PROJECT_ANATOMY"
    COMPONENT_INTELLIGENCE = "COMPONENT_INTELLIGENCE"
    PROJECT_SKILL = "PROJECT_SKILL"
    SPECIALIST_DEFINITION = "SPECIALIST_DEFINITION"
    VALIDATED_KNOWLEDGE = "VALIDATED_KNOWLEDGE"
    PREVIOUS_EVIDENCE = "PREVIOUS_EVIDENCE"
    TOOL_OUTPUT = "TOOL_OUTPUT"
    WORKER_HANDOFF = "WORKER_HANDOFF"


@dataclass
class ContextSourceItem:
    """A candidate context artifact or snippet proposed for injection."""
    source_id: str
    source_type: ContextSourceType
    title: str
    content: str
    token_estimate: int
    is_safety_critical: bool = False
    provenance: str = ""
    epistemic_weight: float = 1.0
    is_stale: bool = False
    target_files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        source_id: str,
        source_type: ContextSourceType,
        title: str,
        content: str,
        is_safety_critical: bool = False,
        provenance: str = "",
        epistemic_weight: float = 1.0,
        is_stale: bool = False,
        target_files: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContextSourceItem:
        # Approximate tokens ~ 4 characters per token
        token_estimate = max(1, len(content) // 4)
        return cls(
            source_id=source_id,
            source_type=source_type,
            title=title,
            content=content,
            token_estimate=token_estimate,
            is_safety_critical=is_safety_critical,
            provenance=provenance,
            epistemic_weight=epistemic_weight,
            is_stale=is_stale,
            target_files=list(target_files or []),
            metadata=dict(metadata or {}),
        )


@dataclass
class ContextSelectionDecision:
    """Individual source allocation decision."""
    source_id: str
    title: str
    classification: ContextClassification
    action: GovernorAction
    allocated_tokens: int
    utility_score: float
    rationale: str


@dataclass
class ContextBudgetCard:
    """Compact, token-bounded reasoning card (<= 16 lines)."""
    budget_limit: int
    total_requested_tokens: int
    total_allocated_tokens: int
    selected_count: int
    deferred_count: int
    discarded_count: int
    refreshes_required: List[str]
    selected_sources: List[str]
    rationale: str

    def format_card(self) -> str:
        """Formats reasoning card strictly <= 16 lines."""
        refreshes = ", ".join(self.refreshes_required[:3]) if self.refreshes_required else "none"
        selected = ", ".join(self.selected_sources[:4]) if self.selected_sources else "none"
        lines = [
            "=== ANTIOS CONTEXT BUDGET CARD ===",
            f"Budget Ceiling:       {self.budget_limit} tokens",
            f"Requested / Allocated: {self.total_requested_tokens} / {self.total_allocated_tokens} tokens",
            f"Selected / Deferred:   {self.selected_count} / {self.deferred_count}",
            f"Discarded / Redundant: {self.discarded_count}",
            f"Refreshes Required:    {refreshes}",
            f"Active Injections:     {selected}",
            f"Governance Rationale:  {self.rationale[:80]}",
            "==================================",
        ]
        return "\n".join(lines)


@dataclass
class ContextBudgetResult:
    """Full outcome of a context budgeting run."""
    card: ContextBudgetCard
    decisions: List[ContextSelectionDecision]
    loaded_context: str
    is_budget_exceeded: bool = False


class ContextBudgetGovernor:
    """Deterministic Context Budget Governor for AntiOS missions."""

    DEFAULT_BUDGET = 4000  # Default prompt context allocation for engineering tasks

    def __init__(self, token_budget: int = DEFAULT_BUDGET):
        self.token_budget = token_budget

    def evaluate(
        self,
        task_intent: str,
        sources: List[ContextSourceItem],
        active_files: Optional[List[str]] = None,
        risk_tier: str = "MEDIUM",
        allow_summarization: bool = True,
    ) -> ContextBudgetResult:
        """Deterministically classifies and budgets candidate context sources."""
        active_files_set = set(active_files or [])
        intent_lower = task_intent.lower()
        decisions: List[ContextSelectionDecision] = []

        seen_fingerprints: Set[str] = set()
        refreshes_required: List[str] = []

        # Pass 1: Epistemic & Relevance Classification
        for item in sources:
            content_hash = hashlib.sha256(item.content.strip().encode("utf-8")).hexdigest()

            # Rule 1: Stale context requires refresh
            if item.is_stale:
                classification = ContextClassification.STALE
                action = GovernorAction.REFRESH
                refreshes_required.append(item.source_id)
                utility = 0.0
                rationale = "Context source is marked stale or out of sync with disk reality."
                decisions.append(ContextSelectionDecision(
                    source_id=item.source_id,
                    title=item.title,
                    classification=classification,
                    action=action,
                    allocated_tokens=0,
                    utility_score=utility,
                    rationale=rationale,
                ))
                continue

            # Rule 2: Redundant / Duplicate content
            if content_hash in seen_fingerprints:
                classification = ContextClassification.REDUNDANT
                action = GovernorAction.DISCARD
                utility = 0.0
                rationale = "Identical content already incorporated in context budget."
                decisions.append(ContextSelectionDecision(
                    source_id=item.source_id,
                    title=item.title,
                    classification=classification,
                    action=action,
                    allocated_tokens=0,
                    utility_score=utility,
                    rationale=rationale,
                ))
                continue
            seen_fingerprints.add(content_hash)

            # Rule 3: Safety-critical context is unconditionally MANDATORY
            if item.is_safety_critical or item.source_type == ContextSourceType.CONSTITUTIONAL_POLICY:
                classification = ContextClassification.MANDATORY
                action = GovernorAction.LOAD
                utility = 100.0 * item.epistemic_weight
                rationale = "Safety invariant or constitutional constraint: unconditionally mandatory."
                decisions.append(ContextSelectionDecision(
                    source_id=item.source_id,
                    title=item.title,
                    classification=classification,
                    action=action,
                    allocated_tokens=item.token_estimate,
                    utility_score=utility,
                    rationale=rationale,
                ))
                continue

            # Rule 4: Active mission state & active blockers
            if item.source_type == ContextSourceType.ACTIVE_MISSION_STATE:
                classification = ContextClassification.MANDATORY
                action = GovernorAction.LOAD
                utility = 90.0 * item.epistemic_weight
                rationale = "Active operational ledger and uncompleted criteria."
                decisions.append(ContextSelectionDecision(
                    source_id=item.source_id,
                    title=item.title,
                    classification=classification,
                    action=action,
                    allocated_tokens=item.token_estimate,
                    utility_score=utility,
                    rationale=rationale,
                ))
                continue

            # Rule 5: Task-relevance computation
            matches_active_file = any(f in active_files_set for f in item.target_files) if item.target_files else False
            tokens_in_intent = any(tok in intent_lower for tok in item.title.lower().split() if len(tok) > 3)

            if matches_active_file or tokens_in_intent:
                classification = ContextClassification.RELEVANT
                # Score utility by relevance, epistemic weight, discounted by token cost
                utility = (50.0 + (30.0 if matches_active_file else 10.0)) * item.epistemic_weight
                action = GovernorAction.LOAD
                rationale = "Directly relevant to active files or task intent terms."
            else:
                classification = ContextClassification.OPTIONAL
                utility = 15.0 * item.epistemic_weight
                action = GovernorAction.DEFER
                rationale = "Peripheral or background information: candidate for deferred loading."

            decisions.append(ContextSelectionDecision(
                source_id=item.source_id,
                title=item.title,
                classification=classification,
                action=action,
                allocated_tokens=item.token_estimate,
                utility_score=utility,
                rationale=rationale,
            ))

        # Pass 2: Bounded Allocation & Token Budget Enforcement
        source_by_id = {s.source_id: s for s in sources}
        total_requested = sum(s.token_estimate for s in sources)
        
        # Mandatory sources are locked in first
        allocated_tokens = 0
        final_decisions: List[ContextSelectionDecision] = []
        loaded_chunks: List[str] = []

        mandatory = [d for d in decisions if d.classification == ContextClassification.MANDATORY and d.action == GovernorAction.LOAD]
        for m in mandatory:
            allocated_tokens += m.allocated_tokens
            final_decisions.append(m)
            item = source_by_id[m.source_id]
            loaded_chunks.append(f"### [{m.classification.value}] {item.title}\n{item.content}")

        # Relevant candidates sorted by utility descending
        candidates = [d for d in decisions if d.classification == ContextClassification.RELEVANT]
        candidates.sort(key=lambda x: x.utility_score, reverse=True)

        for cand in candidates:
            item = source_by_id[cand.source_id]
            if allocated_tokens + item.token_estimate <= self.token_budget:
                allocated_tokens += item.token_estimate
                cand.action = GovernorAction.LOAD
                final_decisions.append(cand)
                loaded_chunks.append(f"### [{cand.classification.value}] {item.title}\n{item.content}")
            else:
                # Can we summarize?
                if allow_summarization and item.token_estimate > 100:
                    summarized_content = self._safe_summarize(item.content, item.provenance)
                    summarized_tokens = max(1, len(summarized_content) // 4)
                    if allocated_tokens + summarized_tokens <= self.token_budget:
                        allocated_tokens += summarized_tokens
                        cand.action = GovernorAction.SUMMARIZE
                        cand.allocated_tokens = summarized_tokens
                        final_decisions.append(cand)
                        loaded_chunks.append(f"### [SUMMARIZED: {cand.classification.value}] {item.title}\n{summarized_content}")
                        continue

                # Otherwise defer
                cand.action = GovernorAction.DEFER
                cand.allocated_tokens = 0
                final_decisions.append(cand)

        # Optional items remain deferred (progressive disclosure)
        optional_items = [d for d in decisions if d.classification == ContextClassification.OPTIONAL]
        for opt in optional_items:
            opt.action = GovernorAction.DEFER
            opt.allocated_tokens = 0
            final_decisions.append(opt)


        # Append discarded, stale, or redundant decisions
        others = [d for d in decisions if d.classification in (ContextClassification.STALE, ContextClassification.REDUNDANT, ContextClassification.UNKNOWN)]
        final_decisions.extend(others)

        selected = [d.source_id for d in final_decisions if d.action in (GovernorAction.LOAD, GovernorAction.SUMMARIZE)]
        deferred = [d.source_id for d in final_decisions if d.action == GovernorAction.DEFER]
        discarded = [d.source_id for d in final_decisions if d.action == GovernorAction.DISCARD]

        budget_exceeded = allocated_tokens > self.token_budget

        card = ContextBudgetCard(
            budget_limit=self.token_budget,
            total_requested_tokens=total_requested,
            total_allocated_tokens=allocated_tokens,
            selected_count=len(selected),
            deferred_count=len(deferred),
            discarded_count=len(discarded),
            refreshes_required=refreshes_required,
            selected_sources=selected,
            rationale=f"Allocated {allocated_tokens} tokens under budget {self.token_budget} with {len(selected)} active sources.",
        )

        return ContextBudgetResult(
            card=card,
            decisions=final_decisions,
            loaded_context="\n\n".join(loaded_chunks),
            is_budget_exceeded=budget_exceeded,
        )

    def _safe_summarize(self, content: str, provenance: str) -> str:
        """Deterministic compaction preserving facts, invariants, line references, and provenance."""
        lines = content.splitlines()
        preserved: List[str] = []
        for line in lines:
            stripped = line.strip()
            # Preserve headers, bullet facts, definitions, rules, and invariants
            if (
                stripped.startswith("#")
                or stripped.startswith("-")
                or stripped.startswith("*")
                or any(k in stripped.lower() for k in ["invariant", "rule", "must", "never", "error", "exit code", "status:"])
            ):
                preserved.append(line)
        if not preserved:
            preserved = lines[:5]
        
        summary = "\n".join(preserved)
        if provenance:
            summary += f"\n*(Compacted summary — Provenance: {provenance})*"
        return summary
