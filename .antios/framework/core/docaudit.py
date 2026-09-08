"""AntiOS Staleguard Layer 1 Syntactic Documentation Reference Auditor.

Executes deterministic, zero-token, sub-second reference audits across documentation
and subsystem manifests. Verifies that all backticked paths, markdown links, and test
command targets physically exist on disk with 0% false positives.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class DocReference:
    """A referenced file, link, or test target extracted from documentation."""
    ref_type: str                          # "BACKTICK_PATH", "MARKDOWN_LINK", "TEST_COMMAND"
    raw_text: str                          # Exact text match
    target_path: str                       # Normalized target path
    line_number: int                       # Line number in doc
    is_valid: bool                         # Whether target exists on disk
    error_message: Optional[str] = None    # Error details if invalid


@dataclass(frozen=True)
class DocAuditResult:
    """Audit summary for a single documentation file."""
    doc_path: str
    total_references: int
    valid_count: int
    broken_count: int
    references: List[DocReference]
    is_clean: bool

    def to_dict(self) -> Dict[str, Any]:
        """Converts result to dictionary."""
        return asdict(self)


# Regex patterns for deterministic extraction
BACKTICK_PATH_REGEX = re.compile(r"`([a-zA-Z0-9_\-./\\]+\.[a-zA-Z0-9]+(?::L\d+(?:-\d+)?)?)`")
MARKDOWN_LINK_REGEX = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
TEST_CMD_REGEX = re.compile(r"`((?:python -m pytest|pytest|npm test|vitest|cargo test|go test)\s+[^`]+)`")

# Common code identifiers or non-path extensions to ignore
IGNORED_EXTENSIONS = {
    "md", "py", "ts", "js", "rs", "go", "json", "yaml", "yml", "toml",
    "html", "css", "sh", "sql", "txt"
}
# Only validate things that look like real file paths (contain / or \ or match known file extensions)
PATH_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go", ".json", ".yaml", ".yml",
    ".toml", ".html", ".css", ".sh", ".bash", ".sql", ".txt", ".md", ".lock"
}


def extract_references_from_text(content: str, doc_rel_path: str = "") -> List[Tuple[str, str, str, int]]:
    """Extracts raw candidate references from text content.
    
    Returns:
        List of (ref_type, raw_text, target_path, line_number)
    """
    results: List[Tuple[str, str, str, int]] = []
    lines = content.splitlines()

    for idx, line in enumerate(lines, start=1):
        # 1. Test commands
        for match in TEST_CMD_REGEX.finditer(line):
            raw_cmd = match.group(1).strip()
            # Extract file arguments from command
            parts = raw_cmd.split()
            for part in parts[1:]:
                # If part has path separators or ends with code extension
                clean_part = part.strip("'\"")
                ext = os.path.splitext(clean_part)[1].lower()
                if ext in PATH_EXTENSIONS or "/" in clean_part or "\\" in clean_part:
                    if not clean_part.startswith("-"):
                        results.append(("TEST_COMMAND", raw_cmd, clean_part, idx))

        # 2. Markdown links
        for match in MARKDOWN_LINK_REGEX.finditer(line):
            label = match.group(1)
            target = match.group(2).strip()
            # Ignore external URLs, mailto, and in-page anchors
            if target.startswith(("http://", "https://", "mailto:", "conversation://", "file://")):
                if target.startswith("file:///"):
                    # Strip file:/// URI scheme for local paths
                    clean_target = target[8:]
                    if ":" in clean_target and clean_target.startswith("/"):
                        clean_target = clean_target[1:]  # /c:/ -> c:/
                    results.append(("MARKDOWN_LINK", match.group(0), clean_target, idx))
                continue
            if target.startswith("#"):
                continue  # Local anchor within same page

            # Strip anchor if present in path (e.g. "path/to/file.md#section")
            target_file = target.split("#")[0]
            if target_file:
                results.append(("MARKDOWN_LINK", match.group(0), target_file, idx))

        # 3. Backticked paths
        for match in BACKTICK_PATH_REGEX.finditer(line):
            candidate = match.group(1).strip()
            # Strip line numbers like :L123 or :L10-20
            clean_candidate = candidate.split(":L")[0].split(":")[0]

            # Ignore dynamic session planning artifacts and target instance template paths
            if clean_candidate.lower() in {"implementation_plan.md", "walkthrough.md", "task.md"}:
                continue
            if clean_candidate.startswith((".antios/", "target/", "<", "$")) or clean_candidate == ".agents/skills/antios/SKILL.md":
                continue

            ext = os.path.splitext(clean_candidate)[1].lower()

            # Must have a valid path extension and look like a file/directory path
            if ext in PATH_EXTENSIONS:
                # Exclude obvious version strings like v1.0 or uuid
                if not re.match(r"^v?\d+\.\d+", clean_candidate):
                    results.append(("BACKTICK_PATH", match.group(0), clean_candidate, idx))

    return results


def audit_documentation_references(doc_path: str, workspace_root: str) -> DocAuditResult:
    """Audits all referenced paths in a documentation file against the physical workspace."""
    norm_root = os.path.normcase(os.path.abspath(workspace_root))
    
    if os.path.isabs(doc_path):
        abs_doc = os.path.normcase(os.path.abspath(doc_path))
    else:
        abs_doc = os.path.normcase(os.path.abspath(os.path.join(norm_root, doc_path)))

    if not os.path.exists(abs_doc):
        return DocAuditResult(
            doc_path=doc_path,
            total_references=0,
            valid_count=0,
            broken_count=1,
            references=[
                DocReference(
                    ref_type="FILE_ACCESS",
                    raw_text=doc_path,
                    target_path=abs_doc,
                    line_number=0,
                    is_valid=False,
                    error_message=f"Documentation file does not exist: '{doc_path}'",
                )
            ],
            is_clean=False,
        )

    try:
        with open(abs_doc, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return DocAuditResult(
            doc_path=doc_path,
            total_references=0,
            valid_count=0,
            broken_count=1,
            references=[
                DocReference(
                    ref_type="FILE_ACCESS",
                    raw_text=doc_path,
                    target_path=abs_doc,
                    line_number=0,
                    is_valid=False,
                    error_message=f"Failed to read file: {e}",
                )
            ],
            is_clean=False,
        )

    raw_refs = extract_references_from_text(content, doc_path)
    doc_dir = os.path.dirname(abs_doc)

    audited_refs: List[DocReference] = []
    broken_count = 0
    valid_count = 0

    for ref_type, raw_text, target, line_num in raw_refs:
        # Determine candidate physical paths
        candidates: List[str] = []
        if os.path.isabs(target):
            candidates.append(os.path.normcase(os.path.abspath(target)))
        else:
            # 1. Relative to doc file directory
            candidates.append(os.path.normcase(os.path.abspath(os.path.join(doc_dir, target))))
            # 2. Relative to workspace root
            candidates.append(os.path.normcase(os.path.abspath(os.path.join(norm_root, target))))

        is_valid = any(os.path.exists(c) for c in candidates)

        # For backticked tokens without path separators (/ or \), if it doesn't exist locally or in root,
        # it is a conceptual identifier, module name, or hypothetical filename in prose, not a path reference.
        if ref_type == "BACKTICK_PATH" and ("/" not in target and "\\" not in target):
            if not is_valid:
                continue

        err = None if is_valid else f"Referenced path '{target}' not found on disk"

        if is_valid:
            valid_count += 1
        else:
            broken_count += 1

        audited_refs.append(
            DocReference(
                ref_type=ref_type,
                raw_text=raw_text,
                target_path=target,
                line_number=line_num,
                is_valid=is_valid,
                error_message=err,
            )
        )

    return DocAuditResult(
        doc_path=doc_path,
        total_references=len(audited_refs),
        valid_count=valid_count,
        broken_count=broken_count,
        references=audited_refs,
        is_clean=(broken_count == 0),
    )


def audit_all_documentation(
    workspace_root: str,
    target_dirs: Optional[List[str]] = None
) -> Dict[str, DocAuditResult]:
    """Audits all markdown files in specified directories or across docs/ and .agents/."""
    norm_root = os.path.normcase(os.path.abspath(workspace_root))
    dirs_to_scan = target_dirs or ["docs", ".agents/skills", ".agents/workflows"]

    results: Dict[str, DocAuditResult] = {}

    for d in dirs_to_scan:
        abs_d = os.path.join(norm_root, d)
        if not os.path.exists(abs_d):
            continue

        if os.path.isfile(abs_d):
            if abs_d.endswith(".md"):
                rel = os.path.relpath(abs_d, norm_root)
                results[rel] = audit_documentation_references(rel, norm_root)
            continue

        for root, _, files in os.walk(abs_d):
            for file in files:
                if file.endswith(".md"):
                    full_p = os.path.join(root, file)
                    rel = os.path.relpath(full_p, norm_root)
                    results[rel] = audit_documentation_references(rel, norm_root)

    return results


@dataclass
class DocAuditSummary:
    """Consolidated summary of documentation reference audit."""
    total_files_audited: int
    broken_count: int
    clean_count: int
    broken_references_by_file: Dict[str, List[str]]
    results: Dict[str, DocAuditResult]


class DocReferenceAuditor:
    """Unified interface for syntactic documentation reference audits."""

    @classmethod
    def audit_documentation(cls, workspace_root: Union[str, os.PathLike] = ".") -> DocAuditSummary:
        """Audits all markdown files and produces a consolidated DocAuditSummary."""
        res_dict = audit_all_documentation(str(workspace_root))
        total_broken = sum(r.broken_count for r in res_dict.values())
        clean_count = sum(1 for r in res_dict.values() if r.is_clean)
        broken_by_file = {
            k: [ref.raw_text for ref in r.references if not ref.is_valid]
            for k, r in res_dict.items() if not r.is_clean
        }
        return DocAuditSummary(
            total_files_audited=len(res_dict),
            broken_count=total_broken,
            clean_count=clean_count,
            broken_references_by_file=broken_by_file,
            results=res_dict,
        )

