"""AntiOS Working Tree State and Conflict Inspection Engine.

Provides ground-truth Git working tree inspection, conflict marker detection across
staged, unstaged, and untracked files, and a practical universal policy for distinguishing:
- CLEAN: No uncommitted changes
- PRE_EXISTING_DIRTY: Changes that were already present when the task began
- EXPECTED_DIRTY: Changes made intentionally as part of the active task
- UNEXPECTED_DIRTY: Changes outside the active task's declared scope
- FORBIDDEN_DIRTY: Changes containing unresolved conflict markers or modifying protected zones
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import fnmatch
import os
import subprocess
import time
from typing import Any, Dict, List, Optional, Set, Tuple


class WorktreeDisposition(str, Enum):
    CLEAN = "CLEAN"
    EXPECTED_DIRTY = "EXPECTED_DIRTY"
    PRE_EXISTING_DIRTY = "PRE_EXISTING_DIRTY"
    UNEXPECTED_DIRTY = "UNEXPECTED_DIRTY"
    FORBIDDEN_DIRTY = "FORBIDDEN_DIRTY"


@dataclass
class WorktreeSnapshot:
    """Snapshot of working tree state taken at a specific point in time (e.g. at task intake)."""
    timestamp: float = 0.0
    commit_sha: str = "UNKNOWN"
    staged_files: List[str] = field(default_factory=list)
    unstaged_files: List[str] = field(default_factory=list)
    untracked_files: List[str] = field(default_factory=list)
    repo_root: str = ""
    is_clean: bool = True
    dirty_files: Optional[List[str]] = None

    def __post_init__(self):
        if self.dirty_files is not None:
            self.unstaged_files = list(self.dirty_files)
            self.is_clean = len(self.dirty_files) == 0
        else:
            self.dirty_files = sorted(list(set(self.staged_files + self.unstaged_files + self.untracked_files)))
            self.is_clean = len(self.dirty_files) == 0

    @property
    def all_dirty_files(self) -> Set[str]:
        return set(self.dirty_files or [])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "commit_sha": self.commit_sha,
            "staged_files": self.staged_files,
            "unstaged_files": self.unstaged_files,
            "untracked_files": self.untracked_files,
            "dirty_files": self.dirty_files or [],
            "repo_root": self.repo_root,
            "is_clean": self.is_clean,
        }


@dataclass
class WorktreeAuditResult:
    """Result of an audit of the current working tree state."""
    disposition: WorktreeDisposition
    is_acceptable: bool
    conflict_markers_found: List[str] = field(default_factory=list)
    forbidden_files_modified: List[str] = field(default_factory=list)
    pre_existing_files: List[str] = field(default_factory=list)
    task_modified_files: List[str] = field(default_factory=list)
    unexpected_files: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "disposition": self.disposition.value,
            "is_acceptable": self.is_acceptable,
            "conflict_markers_found": self.conflict_markers_found,
            "forbidden_files_modified": self.forbidden_files_modified,
            "pre_existing_files": self.pre_existing_files,
            "task_modified_files": self.task_modified_files,
            "unexpected_files": self.unexpected_files,
            "summary": self.summary,
        }


def _run_git(cmd: List[str], repo_root: str, timeout: int = 10) -> Tuple[int, str, str]:
    """Runs a git command safely."""
    try:
        proc = subprocess.run(
            ["git"] + cmd,
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            shell=True if os.name == "nt" else False
        )
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as e:
        return -1, "", str(e)


def capture_worktree_snapshot(repo_root: str) -> WorktreeSnapshot:
    """Captures the current state of git working tree as a baseline."""
    commit_sha = "UNKNOWN"
    ret, out, _ = _run_git(["rev-parse", "HEAD"], repo_root, timeout=5)
    if ret == 0 and out.strip():
        commit_sha = out.strip()

    staged: List[str] = []
    unstaged: List[str] = []
    untracked: List[str] = []

    ret, out, _ = _run_git(["status", "--porcelain"], repo_root, timeout=5)
    if ret == 0 and out:
        for line in out.splitlines():
            if len(line) < 3:
                continue
            code = line[:2]
            filename = line[3:].strip().replace("\\", "/")
            if " -> " in filename:
                filename = filename.split(" -> ")[-1].strip()

            if code == "??":
                untracked.append(filename)
            else:
                if code[0] != " ":
                    staged.append(filename)
                if code[1] != " ":
                    unstaged.append(filename)

    return WorktreeSnapshot(
        timestamp=time.time(),
        commit_sha=commit_sha,
        staged_files=sorted(staged),
        unstaged_files=sorted(unstaged),
        untracked_files=sorted(untracked),
    )


def find_conflict_markers_in_untracked(repo_root: str) -> List[str]:
    """Scans untracked text files for unresolved conflict markers."""
    conflicts = []
    ret, out, _ = _run_git(["ls-files", "--others", "--exclude-standard"], repo_root, timeout=5)
    if ret != 0 or not out:
        return conflicts

    for rel_path in out.splitlines():
        rel_path = rel_path.strip()
        if not rel_path:
            continue
        full_path = os.path.join(repo_root, rel_path)
        if not os.path.isfile(full_path):
            continue

        try:
            # Check file size to avoid reading massive binary blobs
            if os.path.getsize(full_path) > 1_000_000:
                continue
            with open(full_path, "rb") as f:
                content = f.read()
                has_conflict = False
                token = b""
                if b"<<<<<<< " in content:
                    has_conflict = True
                    token = b"<<<<<<< "
                elif b">>>>>>> " in content:
                    has_conflict = True
                    token = b">>>>>>> "
                elif (
                    b"\n=======\n" in content
                    or b"\r\n=======\r\n" in content
                    or b"\n=======\r\n" in content
                    or content.startswith(b"=======\n")
                    or content.startswith(b"=======\r\n")
                ):
                    has_conflict = True
                    token = b"======="

                if has_conflict:
                    conflicts.append(f"Untracked file '{rel_path}' contains conflict marker '{token.decode()}'")
        except Exception:
            pass

    return conflicts


def inspect_all_conflicts(repo_root: str) -> List[str]:
    """Inspects staged, unstaged, and untracked files for git conflict markers."""
    git_dir = os.path.join(repo_root, ".git")
    if not os.path.exists(git_dir):
        return []

    ret, out, err = _run_git(["rev-parse", "--is-inside-work-tree"], repo_root, timeout=5)
    if ret != 0 or "true" not in out.lower():
        return []

    conflicts: List[str] = []

    # 1. Unstaged tracked files
    ret, out, err = _run_git(["diff", "--check"], repo_root, timeout=5)
    if ret != 0:
        for line in (out + "\n" + err).splitlines():
            line = line.strip()
            if "leftover conflict marker" in line.lower():
                conflicts.append(f"Unstaged conflict: {line}")

    # 2. Staged tracked files
    ret, out, err = _run_git(["diff", "--cached", "--check"], repo_root, timeout=5)
    if ret != 0:
        for line in (out + "\n" + err).splitlines():
            line = line.strip()
            if "leftover conflict marker" in line.lower():
                conflicts.append(f"Staged conflict: {line}")

    # 3. Untracked files
    untracked_conflicts = find_conflict_markers_in_untracked(repo_root)
    conflicts.extend(untracked_conflicts)

    return conflicts


def audit_worktree(
    repo_root: str,
    baseline_snapshot: Optional[WorktreeSnapshot] = None,
    expected_scope_patterns: Optional[List[str]] = None,
    protected_patterns: Optional[List[str]] = None,
) -> WorktreeAuditResult:
    """Audits current working tree state against baseline and safety rules."""
    current = capture_worktree_snapshot(repo_root)
    conflicts = inspect_all_conflicts(repo_root)

    # If conflict markers exist anywhere, it is strictly forbidden
    if conflicts:
        return WorktreeAuditResult(
            disposition=WorktreeDisposition.FORBIDDEN_DIRTY,
            is_acceptable=False,
            conflict_markers_found=conflicts,
            summary=f"Audit failed: {len(conflicts)} unresolved conflict marker(s) detected.",
        )

    current_dirty = current.all_dirty_files

    if not current_dirty:
        return WorktreeAuditResult(
            disposition=WorktreeDisposition.CLEAN,
            is_acceptable=True,
            summary="Clean working tree: zero uncommitted changes.",
        )

    # Check for forbidden modifications (e.g. .agents/, framework/, antios.config.json)
    if protected_patterns is None:
        protected_patterns = [".agents/**", "framework/**", "antios.config.json", ".git/**"]

    forbidden_modified: List[str] = []
    for f in current_dirty:
        norm_f = f.replace("\\", "/")
        for pat in protected_patterns:
            norm_pat = pat.replace("\\", "/")
            if norm_pat.endswith("/**"):
                prefix = norm_pat[:-3]
                if norm_f == prefix or norm_f.startswith(prefix + "/"):
                    forbidden_modified.append(norm_f)
                    break
            elif fnmatch.fnmatch(norm_f, norm_pat):
                forbidden_modified.append(norm_f)
                break

    if forbidden_modified:
        return WorktreeAuditResult(
            disposition=WorktreeDisposition.FORBIDDEN_DIRTY,
            is_acceptable=False,
            forbidden_files_modified=sorted(forbidden_modified),
            summary=f"Audit failed: modifications detected in protected governance zones ({len(forbidden_modified)} files).",
        )

    # Separate pre-existing dirty files from task-modified files
    baseline_dirty = baseline_snapshot.all_dirty_files if baseline_snapshot else set()
    pre_existing = sorted(list(current_dirty.intersection(baseline_dirty)))
    task_modified = sorted(list(current_dirty.difference(baseline_dirty)))

    # If only pre-existing files are dirty, and no task files modified:
    if not task_modified and pre_existing:
        return WorktreeAuditResult(
            disposition=WorktreeDisposition.PRE_EXISTING_DIRTY,
            is_acceptable=True,
            pre_existing_files=pre_existing,
            summary=f"Working tree has {len(pre_existing)} pre-existing dirty file(s); no task changes made.",
        )

    # If task files were modified, check against expected scope patterns if provided
    unexpected: List[str] = []
    if expected_scope_patterns:
        for f in task_modified:
            norm_f = f.replace("\\", "/")
            in_scope = False
            for pat in expected_scope_patterns:
                norm_pat = pat.replace("\\", "/")
                if norm_pat.endswith("/**"):
                    prefix = norm_pat[:-3]
                    if norm_f == prefix or norm_f.startswith(prefix + "/"):
                        in_scope = True
                        break
                elif fnmatch.fnmatch(norm_f, norm_pat):
                    in_scope = True
                    break
            if not in_scope:
                unexpected.append(norm_f)

    if unexpected:
        return WorktreeAuditResult(
            disposition=WorktreeDisposition.UNEXPECTED_DIRTY,
            is_acceptable=False,
            pre_existing_files=pre_existing,
            task_modified_files=task_modified,
            unexpected_files=sorted(unexpected),
            summary=f"Working tree contains {len(unexpected)} unexpected file modification(s) outside declared scope.",
        )

    return WorktreeAuditResult(
        disposition=WorktreeDisposition.EXPECTED_DIRTY,
        is_acceptable=True,
        pre_existing_files=pre_existing,
        task_modified_files=task_modified,
        summary=f"Working tree has {len(task_modified)} expected modification(s) from current task.",
    )
