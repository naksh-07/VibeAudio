"""AntiOS 3.0 Epistemic Engineering Memory Framework.

Manages 8 canonical categories of Git-versioned Markdown engineering memory,
the 4-tier epistemic ladder, SHA-256 target code binding, automatic
[STALE_EVIDENCE] suppression, and strict context budgeting (<= 300 tokens).

Constitutional Invariants:
- INV-09: Zero vector databases (deterministic tag/subsystem indexing).
- INV-10: 4-Zone ownership boundary.
- INV-11: Zero third-party dependencies (pure standard library only).
- INV-13: System A / System B strict decoupling.
"""

from __future__ import annotations

import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class EpistemicGrade(str, Enum):
    VERIFIED_FACT = "VERIFIED_FACT"
    ARCHITECTURAL_DECISION = "ARCHITECTURAL_DECISION"
    TESTED_NEGATIVE = "TESTED_NEGATIVE"
    WORKING_HYPOTHESIS = "WORKING_HYPOTHESIS"
    STALE_EVIDENCE = "STALE_EVIDENCE"


class MemoryCategory(str, Enum):
    ADR = "adr"
    DEAD_ENDS = "dead_ends"
    RCA = "rca"
    ENVIRONMENT = "environment"
    HAZARDS = "hazards"
    RUNBOOKS = "runbooks"
    BASELINES = "baselines"
    PREFERENCES = "preferences"


@dataclass
class MemoryRecord:
    record_id: str
    category: str
    title: str
    epistemic_status: str
    timestamp: str
    target_subsystem: str = ""
    target_file: Optional[str] = None
    target_content_hash: Optional[str] = None
    content: str = ""
    tags: List[str] = field(default_factory=list)

    def is_stale(self, repo_root: str) -> bool:
        """Verifies if the referenced code has drifted from target_content_hash."""
        if not self.target_file or not self.target_content_hash:
            return False

        full_path = os.path.join(repo_root, self.target_file.replace("/", os.sep))
        if not os.path.isfile(full_path):
            return True

        try:
            with open(full_path, "rb") as fp:
                current_hash = hashlib.sha256(fp.read()).hexdigest()
            return current_hash.lower() != self.target_content_hash.lower()
        except (OSError, IOError):
            return True

    def get_effective_status(self, repo_root: str) -> str:
        """Returns current epistemic status, promoting to STALE_EVIDENCE if code drifted."""
        if self.is_stale(repo_root):
            return EpistemicGrade.STALE_EVIDENCE.value
        return self.epistemic_status

    def to_markdown(self) -> str:
        """Renders record to canonical Markdown snippet."""
        lines = [
            f"### {self.record_id}: {self.title}",
            f"- **Status**: [{self.epistemic_status}]",
            f"- **Timestamp**: {self.timestamp}",
        ]
        if self.target_subsystem:
            lines.append(f"- **Target Subsystem**: `{self.target_subsystem}`")
        if self.target_file:
            lines.append(f"- **Target File**: `{self.target_file}`")
        if self.target_content_hash:
            lines.append(f"- **Target SHA-256**: `{self.target_content_hash}`")
        if self.tags:
            lines.append(f"- **Tags**: {', '.join(self.tags)}")
        lines.append("")
        lines.append(self.content.strip())
        lines.append("")
        return "\n".join(lines)


class MemoryStore:
    """Git-tracked Markdown memory store in docs/memory/."""

    def __init__(self, repo_root: str):
        self.repo_root = os.path.abspath(repo_root)
        self.memory_dir = os.path.join(self.repo_root, "docs", "memory")

    def initialize_store(self) -> None:
        """Initializes docs/memory/ directory structure and category files."""
        os.makedirs(os.path.join(self.memory_dir, "adr"), exist_ok=True)
        os.makedirs(os.path.join(self.memory_dir, "rca"), exist_ok=True)

        standard_files = {
            "dead_ends.md": "# AntiOS Engineering Memory: Failed Hypotheses & Dead Ends\n\n",
            "environment.md": "# AntiOS Engineering Memory: Environment Quirks & Host Workarounds\n\n",
            "hazards.md": "# AntiOS Engineering Memory: Tool Hazards & Forbidden Operations\n\n",
            "runbooks.md": "# AntiOS Engineering Memory: Verification Runbooks & Target Matrices\n\n",
            "baselines.md": "# AntiOS Engineering Memory: Performance Baselines & Latency Budgets\n\n",
            "preferences.md": "# AntiOS Engineering Memory: User Preferences & Project Idioms\n\n",
        }

        for filename, initial_header in standard_files.items():
            fpath = os.path.join(self.memory_dir, filename)
            if not os.path.isfile(fpath):
                try:
                    with open(fpath, "w", encoding="utf-8") as fp:
                        fp.write(initial_header)
                except OSError:
                    pass

    def compute_file_hash(self, rel_path: str) -> Optional[str]:
        """Calculates SHA-256 of target file relative to repo root."""
        full_path = os.path.join(self.repo_root, rel_path.replace("/", os.sep))
        if os.path.isfile(full_path):
            try:
                with open(full_path, "rb") as fp:
                    return hashlib.sha256(fp.read()).hexdigest()
            except (OSError, IOError):
                return None
        return None

    def parse_markdown_records(self, filepath: str, category: str) -> List[MemoryRecord]:
        """Parses structured MemoryRecord entries from a Markdown file."""
        if not os.path.isfile(filepath):
            return []

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as fp:
                text = fp.read()
        except OSError:
            return []

        records: List[MemoryRecord] = []
        # Pattern matches ### ID: Title headers
        sections = re.split(r"\n(?=###\s+)", text)

        for sec in sections:
            sec = sec.strip()
            if not sec.startswith("###"):
                continue

            lines = sec.splitlines()
            header_line = lines[0][3:].strip()
            # Split ID and title
            m = re.match(r"^([A-Za-z0-9_\-]+)\s*:\s*(.+)$", header_line)
            if m:
                rec_id, title = m.group(1).strip(), m.group(2).strip()
            else:
                rec_id = f"REC-{len(records)+1:03d}"
                title = header_line

            epistemic_status = EpistemicGrade.VERIFIED_FACT.value
            timestamp = ""
            subsystem = ""
            target_file = None
            target_hash = None
            tags: List[str] = []
            content_lines: List[str] = []

            for line in lines[1:]:
                line_str = line.strip()
                if line_str.startswith("- **Status**:"):
                    st = line_str.split(":", 1)[1].strip(" *[]")
                    epistemic_status = st
                elif line_str.startswith("- **Timestamp**:"):
                    timestamp = line_str.split(":", 1)[1].strip(" *`")
                elif line_str.startswith("- **Target Subsystem**:"):
                    subsystem = line_str.split(":", 1)[1].strip(" *`")
                elif line_str.startswith("- **Target File**:"):
                    target_file = line_str.split(":", 1)[1].strip(" *`")
                elif line_str.startswith("- **Target SHA-256**:") or line_str.startswith("- **Target Content Hash**:"):
                    target_hash = line_str.split(":", 1)[1].strip(" *`")
                elif line_str.startswith("- **Tags**:"):
                    raw_tags = line_str.split(":", 1)[1].strip()
                    tags = [t.strip(" `*") for t in raw_tags.split(",") if t.strip()]
                else:
                    content_lines.append(line)

            records.append(
                MemoryRecord(
                    record_id=rec_id,
                    category=category,
                    title=title,
                    epistemic_status=epistemic_status,
                    timestamp=timestamp,
                    target_subsystem=subsystem,
                    target_file=target_file,
                    target_content_hash=target_hash,
                    content="\n".join(content_lines).strip(),
                    tags=tags,
                )
            )

        return records

    def load_all_records(self) -> List[MemoryRecord]:
        """Loads all engineering memory records from docs/memory/."""
        all_records: List[MemoryRecord] = []

        category_map = {
            "dead_ends.md": MemoryCategory.DEAD_ENDS.value,
            "environment.md": MemoryCategory.ENVIRONMENT.value,
            "hazards.md": MemoryCategory.HAZARDS.value,
            "runbooks.md": MemoryCategory.RUNBOOKS.value,
            "baselines.md": MemoryCategory.BASELINES.value,
            "preferences.md": MemoryCategory.PREFERENCES.value,
        }

        for fname, cat in category_map.items():
            fpath = os.path.join(self.memory_dir, fname)
            all_records.extend(self.parse_markdown_records(fpath, cat))

        # Scan adr/ directory
        adr_dir = os.path.join(self.memory_dir, "adr")
        if os.path.isdir(adr_dir):
            for f in os.listdir(adr_dir):
                if f.endswith(".md"):
                    all_records.extend(
                        self.parse_markdown_records(os.path.join(adr_dir, f), MemoryCategory.ADR.value)
                    )

        # Scan rca/ directory
        rca_dir = os.path.join(self.memory_dir, "rca")
        if os.path.isdir(rca_dir):
            for f in os.listdir(rca_dir):
                if f.endswith(".md"):
                    all_records.extend(
                        self.parse_markdown_records(os.path.join(rca_dir, f), MemoryCategory.RCA.value)
                    )

        return all_records

    def query(
        self,
        subsystem_or_tag: str,
        max_records: int = 2,
        max_tokens: int = 300,
    ) -> List[Tuple[MemoryRecord, str]]:
        """Gated retrieval of relevant memory records with epistemic verification.

        Returns:
            List of (MemoryRecord, formatted_text)

        Suppression Rules:
        - Rejects records where epistemic_status == WORKING_HYPOTHESIS.
        - Automatically marks code-drifted records as [STALE_EVIDENCE] and suppresses them.
        - Caps injected context to max_records and <= max_tokens (~1,200 chars).
        """
        all_recs = self.load_all_records()
        normalized_query = subsystem_or_tag.lower().strip()

        matched: List[MemoryRecord] = []

        for rec in all_recs:
            # 1. Epistemic Hygiene: Discard unproven hypotheses
            if rec.epistemic_status == EpistemicGrade.WORKING_HYPOTHESIS.value:
                continue

            # 2. Match subsystem, file, tags, or title
            subsystem_match = normalized_query in rec.target_subsystem.lower()
            file_match = bool(rec.target_file and normalized_query in rec.target_file.lower())
            tag_match = any(normalized_query in t.lower() for t in rec.tags)
            title_match = normalized_query in rec.title.lower()

            if subsystem_match or file_match or tag_match or title_match:
                # 3. Target Code Binding check
                if rec.is_stale(self.repo_root):
                    # Stale evidence: suppressed from prompt context to avoid pollution
                    continue
                matched.append(rec)

        # Sort by specificity (ADR and TESTED_NEGATIVE prioritized)
        def priority_key(r: MemoryRecord) -> int:
            if r.epistemic_status == EpistemicGrade.ARCHITECTURAL_DECISION.value:
                return 0
            if r.epistemic_status == EpistemicGrade.TESTED_NEGATIVE.value:
                return 1
            return 2

        matched.sort(key=priority_key)

        results: List[Tuple[MemoryRecord, str]] = []
        char_budget = max_tokens * 4  # ~4 chars per token
        consumed_chars = 0

        for r in matched[:max_records]:
            md = r.to_markdown()
            if consumed_chars + len(md) > char_budget and results:
                break
            results.append((r, md))
            consumed_chars += len(md)

        return results
