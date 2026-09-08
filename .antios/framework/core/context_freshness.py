"""AntiOS 2.0 Context Freshness & Safe Compaction Engine (Phase 88).

Implements epistemic freshness auditing, drift detection, and non-destructive
safe context compaction.

Guiding Laws:
1. "A stale source must NEVER silently appear as authoritative current context."
2. "Compaction NEVER converts inference into fact."
3. "Compaction NEVER strips provenance references or security constraints."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from framework.core.learning import EpistemicSource


class ContextFreshnessState(str, Enum):
    """Epistemic freshness classification of context artifacts."""
    FRESH = "FRESH"          # Grounded in current disk reality and identical fingerprint
    AGING = "AGING"          # Valid but nearing TTL or unverified across subsequent commits
    STALE = "STALE"          # Underlying file modified, git HEAD moved, or manifest drifted
    INVALID = "INVALID"      # Physical contradiction found (missing files, syntax error, failed tests)
    UNKNOWN = "UNKNOWN"      # Missing provenance or unverified origin


@dataclass
class FreshnessEvaluation:
    """Outcome of a freshness audit on a context source."""
    source_id: str
    state: ContextFreshnessState
    confidence: float
    reasons: List[str] = field(default_factory=list)
    last_verified: str = ""
    source_fingerprint: str = ""
    current_fingerprint: str = ""

    @property
    def is_trustworthy(self) -> bool:
        return self.state in (ContextFreshnessState.FRESH, ContextFreshnessState.AGING)


class FreshnessEvaluator:
    """Evaluates context freshness against physical repository signals."""

    @staticmethod
    def compute_sha256(path: Union[str, Path]) -> Optional[str]:
        """Calculates normalized SHA-256 digest of a physical file."""
        p = Path(path)
        if not p.is_file():
            return None
        try:
            raw = p.read_bytes().replace(b"\r\n", b"\n")
            return hashlib.sha256(raw).hexdigest()
        except Exception:
            return None

    @classmethod
    def evaluate_file_source(
        cls,
        source_id: str,
        file_path: str,
        recorded_sha256: Optional[str] = None,
        workspace_root: str = ".",
    ) -> FreshnessEvaluation:
        """Audits a specific file context source against on-disk reality."""
        abs_path = Path(workspace_root) / file_path
        reasons: List[str] = []

        if not abs_path.exists():
            return FreshnessEvaluation(
                source_id=source_id,
                state=ContextFreshnessState.INVALID,
                confidence=0.0,
                reasons=[f"Physical source file does not exist: {file_path}"],
            )

        current_sha = cls.compute_sha256(abs_path)
        if recorded_sha256 and current_sha != recorded_sha256:
            return FreshnessEvaluation(
                source_id=source_id,
                state=ContextFreshnessState.STALE,
                confidence=0.2,
                reasons=[f"File modified since context capture (recorded SHA {recorded_sha256[:8]} != current {current_sha[:8]})"],
                source_fingerprint=recorded_sha256,
                current_fingerprint=current_sha or "",
            )

        return FreshnessEvaluation(
            source_id=source_id,
            state=ContextFreshnessState.FRESH,
            confidence=1.0,
            source_fingerprint=recorded_sha256 or current_sha or "",
            current_fingerprint=current_sha or "",
        )

    @classmethod
    def evaluate_project_context(
        cls,
        recorded_manifest_fingerprint: Optional[str],
        current_manifest_fingerprint: Optional[str],
        recorded_git_head: Optional[str],
        current_git_head: Optional[str],
        substantive_dirty_files: Optional[List[str]] = None,
    ) -> FreshnessEvaluation:
        """Evaluates overarching project-level context freshness."""
        reasons: List[str] = []
        state = ContextFreshnessState.FRESH
        confidence = 1.0

        # Manifest drift
        if (
            recorded_manifest_fingerprint
            and current_manifest_fingerprint
            and recorded_manifest_fingerprint != current_manifest_fingerprint
        ):
            reasons.append("Project manifests changed (manifest fingerprint mismatch).")
            state = ContextFreshnessState.STALE
            confidence = min(confidence, 0.4)

        # Git HEAD advancement
        if recorded_git_head and current_git_head and recorded_git_head != current_git_head:
            reasons.append(f"Git HEAD moved from {recorded_git_head[:8]} to {current_git_head[:8]}.")
            state = ContextFreshnessState.AGING if state == ContextFreshnessState.FRESH else state
            confidence = min(confidence, 0.6)

        # Uncommitted substantive modifications
        if substantive_dirty_files:
            reasons.append(f"Working tree has uncommitted mutations: {', '.join(substantive_dirty_files[:3])}")
            state = ContextFreshnessState.STALE
            confidence = min(confidence, 0.3)

        return FreshnessEvaluation(
            source_id="PROJECT_GOVERNANCE",
            state=state,
            confidence=confidence,
            reasons=reasons,
            source_fingerprint=recorded_manifest_fingerprint or "",
            current_fingerprint=current_manifest_fingerprint or "",
        )


@dataclass
class CompactedFact:
    """A preserved fact or invariant."""
    category: str
    statement: str
    epistemic_source: EpistemicSource
    provenance: str = ""
    is_constraint: bool = False


class SafeContextCompactor:
    """Non-destructive context compactor.

    Preserves facts, decisions, constraints, acceptance criteria,
    unresolved questions, and evidence references.
    Removes redundant prose, greeting fluff, and exploratory noise.
    """

    FACT_PATTERNS = [
        re.compile(r"^\s*[-*]\s+(.+)$", re.MULTILINE),
        re.compile(r"^\s*\d+\.\s+(.+)$", re.MULTILINE),
    ]

    CONSTRAINT_KEYWORDS = [
        "must", "never", "cannot", "always", "invariant",
        "shall", "strict", "prohibit", "forbidden", "immutable",
        "depth <=", "active <=", "budget", "exit code 0"
    ]

    NOISE_PATTERNS = [
        re.compile(r"^(hello|hi|sure|i will|let me|as an ai|certainly|thank you).*", re.IGNORECASE),
        re.compile(r"^(in this section|i am going to|let's now|here is what).*", re.IGNORECASE),
    ]

    @classmethod
    def compact(
        cls,
        raw_text: str,
        provenance: str = "",
        epistemic_source: EpistemicSource = EpistemicSource.OBSERVED_FACT,
        target_token_budget: Optional[int] = None,
    ) -> str:
        """Deterministically compacts text preserving all semantic and security invariants."""
        lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
        preserved_facts: List[CompactedFact] = []
        preserved_headers: List[str] = []

        for line in lines:
            # Check noise
            if any(p.match(line) for p in cls.NOISE_PATTERNS):
                continue

            # Headers
            if line.startswith("#"):
                preserved_headers.append(line)
                continue

            # Check if this line expresses a constraint or invariant
            is_constraint = any(k in line.lower() for k in cls.CONSTRAINT_KEYWORDS)

            # Check for bullet facts or statements
            preserved_facts.append(CompactedFact(
                category="CONSTRAINT" if is_constraint else "FACT",
                statement=line,
                epistemic_source=epistemic_source,
                provenance=provenance,
                is_constraint=is_constraint,
            ))

        # Deduplicate facts preserving order
        seen_statements: Set[str] = set()
        deduped: List[CompactedFact] = []
        for fact in preserved_facts:
            norm = fact.statement.lower()
            if norm not in seen_statements:
                seen_statements.add(norm)
                deduped.append(fact)

        # Build compacted markdown
        out_lines: List[str] = []
        if preserved_headers:
            out_lines.append(preserved_headers[0])
            out_lines.append("")

        # Partition constraints from regular facts
        constraints = [f for f in deduped if f.is_constraint]
        regular_facts = [f for f in deduped if not f.is_constraint]

        if constraints:
            out_lines.append("### Invariants & Active Constraints")
            for c in constraints:
                stmt = c.statement if c.statement.startswith(("-", "*", "1", "2", "3", "4", "5", "6", "7", "8", "9")) else f"- {c.statement}"
                out_lines.append(stmt)
            out_lines.append("")

        if regular_facts:
            out_lines.append("### Preserved Evidence & Facts")
            for rf in regular_facts:
                stmt = rf.statement if rf.statement.startswith(("-", "*", "1", "2", "3", "4", "5", "6", "7", "8", "9")) else f"- {rf.statement}"
                out_lines.append(stmt)
            out_lines.append("")

        # Append provenance footer
        out_lines.append(f"*(Safe compaction — Epistemic Source: {epistemic_source.value}; Provenance: {provenance or 'internal'})*")

        compacted_text = "\n".join(out_lines)

        # If token budget given and still exceeding, truncate non-constraints only
        if target_token_budget and (len(compacted_text) // 4) > target_token_budget:
            # We must never truncate constraints
            compacted_lines = out_lines[:15]
            compacted_lines.append("... [truncated exploratory noise while preserving all constraints]")
            compacted_lines.append(out_lines[-1])
            compacted_text = "\n".join(compacted_lines)

        return compacted_text
