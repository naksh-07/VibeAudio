"""AntiOS Project-Agnostic Same Change Set Integrity Engine.

Evaluates working tree modifications to ensure that code changes are accompanied
by expected synchronization (tests, documentation, or task state) without
hardcoding domain rules. Project adapters configure patterns and rules declaratively.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import fnmatch
import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ChangesetPolicy:
    """Configurable declarative policy for same-change-set synchronization."""
    enabled: bool = True
    code_patterns: List[str] = field(default_factory=lambda: [
        "*.py", "*.ts", "*.js", "*.tsx", "*.jsx", "*.rs", "*.go", "*.c", "*.cpp", "*.java", "*.dart"
    ])
    doc_patterns: List[str] = field(default_factory=lambda: [
        "docs/**", "*.md", "doc/**"
    ])
    test_patterns: List[str] = field(default_factory=lambda: [
        "tests/**", "test/**", "*_test.*", "*test.*", "*.spec.*", "tests/*"
    ])
    state_patterns: List[str] = field(default_factory=lambda: [
        "docs/ACTIVE_CONTEXT.md", "ACTIVE_CONTEXT.md"
    ])
    require_tests_on_code_change: bool = True
    require_docs_on_code_change: bool = False
    require_state_on_code_change: bool = False
    audit_documentation_references: bool = True


@dataclass
class ChangeSetEvaluation:
    """Structured evaluation result of working tree changes."""
    is_valid: bool
    code_changed: bool = False
    docs_changed: bool = False
    tests_changed: bool = False
    state_changed: bool = False
    code_files: List[str] = field(default_factory=list)
    doc_files: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    state_files: List[str] = field(default_factory=list)
    unmatched_files: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "code_changed": self.code_changed,
            "docs_changed": self.docs_changed,
            "tests_changed": self.tests_changed,
            "state_changed": self.state_changed,
            "code_files": self.code_files,
            "doc_files": self.doc_files,
            "test_files": self.test_files,
            "state_files": self.state_files,
            "unmatched_files": self.unmatched_files,
            "violations": self.violations,
            "summary": self.summary,
        }


def _matches_any_pattern(file_path: str, patterns: List[str]) -> bool:
    """Matches a file path against a list of glob patterns normalized to forward slashes."""
    norm_path = file_path.replace("\\", "/")
    filename = os.path.basename(norm_path)

    for pat in patterns:
        norm_pat = pat.replace("\\", "/")
        if fnmatch.fnmatch(norm_path, norm_pat) or fnmatch.fnmatch(filename, norm_pat):
            return True
        # Prefix directory glob match (e.g. docs/**)
        if norm_pat.endswith("/**"):
            dir_prefix = norm_pat[:-3]
            if norm_path == dir_prefix or norm_path.startswith(dir_prefix + "/"):
                return True
    return False


def get_git_changed_files(repo_root: str) -> Optional[List[str]]:
    """Retrieves all changed, staged, unstaged, and untracked files from git.
    Returns None if git status fails or times out in a git repository.
    Returns [] if repo_root is not a git repository.
    """
    is_git = os.path.exists(os.path.join(repo_root, ".git"))
    if not is_git:
        return []

    changed = set()
    try:
        # Check porcelain status (includes untracked and staged, with individual untracked files)
        res = subprocess.run(
            ["git", "status", "--porcelain", "-uall"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
            shell=True if os.name == "nt" else False
        )
        if res.returncode != 0:
            return None
        if res.stdout:
            for line in res.stdout.splitlines():
                line = line.strip()
                if len(line) >= 3:
                    # porcelain format: XY filename or XY orig -> new
                    file_part = line[2:].strip()
                    if " -> " in file_part:
                        file_part = file_part.split(" -> ")[-1].strip()
                    if file_part:
                        changed.add(file_part.replace("\\", "/"))
        return sorted(list(changed))
    except Exception:
        return None


def evaluate_changeset(
    repo_root: str,
    changed_files: Optional[List[str]] = None,
    policy: Optional[ChangesetPolicy] = None
) -> ChangeSetEvaluation:
    """Evaluates working tree changes against project Same Change Set policies.
    
    Returns a ChangeSetEvaluation indicating whether required synchronization was maintained.
    """
    if policy is None:
        policy = ChangesetPolicy()

    if not policy.enabled:
        return ChangeSetEvaluation(
            is_valid=True,
            summary="Same Change Set policy is disabled."
        )

    if changed_files is None:
        files = get_git_changed_files(repo_root)
        if files is None:
            return ChangeSetEvaluation(
                is_valid=False,
                violations=["Unable to inspect git status (git command failed, timed out, or repository unavailable)."],
                summary="Same Change Set evaluation failed closed: could not inspect git status."
            )
        changed_files = files

    if not changed_files:
        return ChangeSetEvaluation(
            is_valid=True,
            summary="Clean working tree: no changed files detected."
        )

    code_files: List[str] = []
    doc_files: List[str] = []
    test_files: List[str] = []
    state_files: List[str] = []
    unmatched_files: List[str] = []

    for f in changed_files:
        norm_f = f.replace("\\", "/")
        matched = False

        # Check tests first because test files often end in code extensions (e.g. test_foo.py)
        if _matches_any_pattern(norm_f, policy.test_patterns):
            test_files.append(norm_f)
            matched = True

        if _matches_any_pattern(norm_f, policy.state_patterns):
            state_files.append(norm_f)
            matched = True

        if _matches_any_pattern(norm_f, policy.doc_patterns):
            doc_files.append(norm_f)
            matched = True

        # Check code files if not classified purely as a test or doc
        if _matches_any_pattern(norm_f, policy.code_patterns):
            if not matched or norm_f not in test_files:
                code_files.append(norm_f)
                matched = True

        if not matched:
            unmatched_files.append(norm_f)

    code_changed = len(code_files) > 0
    docs_changed = len(doc_files) > 0
    tests_changed = len(test_files) > 0
    state_changed = len(state_files) > 0

    violations: List[str] = []

    if code_changed:
        if policy.require_tests_on_code_change and not tests_changed:
            violations.append(
                f"Same Change Set Violation: Code files were modified ({len(code_files)} files: {', '.join(code_files[:3])}), "
                f"but no accompanying test files were added or modified."
            )

        if policy.require_docs_on_code_change and not docs_changed:
            violations.append(
                f"Same Change Set Violation: Code files were modified, but no accompanying documentation updates "
                f"were included in the change set."
            )

        if policy.require_state_on_code_change and not state_changed:
            violations.append(
                f"Same Change Set Violation: Code files were modified, but active task state "
                f"was not synchronized in the change set."
            )

    # Staleguard Layer 1: Audit modified documentation files for dead links or broken paths
    if docs_changed and policy.audit_documentation_references:
        try:
            from framework.core.docaudit import audit_documentation_references
            for df in doc_files:
                norm_df = df.replace("\\", "/")
                if "templates/" in norm_df or "fixtures/" in norm_df:
                    continue
                abs_df = os.path.join(repo_root, df) if not os.path.isabs(df) else df
                if os.path.exists(abs_df) and df.endswith(".md"):
                    audit_res = audit_documentation_references(df, repo_root)
                    if not audit_res.is_clean:
                        violations.append(
                            f"Documentation Reference Drift: '{df}' contains {audit_res.broken_count} dead link(s) or invalid path reference(s)."
                        )
        except Exception:
            pass

    is_valid = len(violations) == 0
    summary = (
        "Same Change Set integrity verified."
        if is_valid
        else f"Same Change Set check failed with {len(violations)} violation(s)."
    )

    return ChangeSetEvaluation(
        is_valid=is_valid,
        code_changed=code_changed,
        docs_changed=docs_changed,
        tests_changed=tests_changed,
        state_changed=state_changed,
        code_files=code_files,
        doc_files=doc_files,
        test_files=test_files,
        state_files=state_files,
        unmatched_files=unmatched_files,
        violations=violations,
        summary=summary,
    )
