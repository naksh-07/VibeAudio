"""AntiOS 2.0 Native Git Capability Engine.

Provides clean, fail-closed integration with the native Git CLI.
Does NOT reinvent Git: wraps native subprocess execution for deterministic
operational diagnostics, safety checks, and guarded release operations.

Distinguishes:
- READ-ONLY operations (inspect status, branch, rev, tags, diffs, clean tree)
- MUTATING operations (create tag, rollback branch, stash/checkout) - requires explicit guard
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple, Union


class GitMutationPolicy(str, Enum):
    """Guards governing mutating Git operations."""
    DENIED = "DENIED"                   # Mutation strictly forbidden
    GUARDED = "GUARDED"                 # Allowed only if working tree is clean and explicitly confirmed
    PERMITTED = "PERMITTED"             # Permitted operational step (e.g. creating a release tag)


@dataclass
class GitWorktreeStatus:
    """Operational summary of Git repository working tree state."""
    is_git_repo: bool
    is_clean: bool
    current_branch: str
    current_commit: Optional[str]
    modified_files: List[str]
    untracked_files: List[str]
    staged_files: List[str]
    latest_tag: Optional[str]
    tags: List[str]
    ahead_commits: int = 0
    behind_commits: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def format_human(self) -> str:
        if not self.is_git_repo:
            return "Git Status: Not a Git repository."
        lines = [
            f"Git Branch:             {self.current_branch}",
            f"Head Commit:            {self.current_commit or 'none'}",
            f"Working Tree Clean:     {'Yes' if self.is_clean else 'No (modifications present)'}",
            f"Modified Files:         {len(self.modified_files)}",
            f"Untracked Files:        {len(self.untracked_files)}",
            f"Staged Files:           {len(self.staged_files)}",
            f"Latest Tag:             {self.latest_tag or 'none'}",
        ]
        if self.ahead_commits > 0:
            lines.append(f"Branch Ahead:           {self.ahead_commits} commit(s)")
        return "\n".join(lines)


class GitCapabilityEngine:
    """Deterministic Git operational capability wrapper."""

    def __init__(self, repo_root: Union[str, Path]):
        self.repo_root = Path(repo_root).resolve()

    def is_git_available(self) -> bool:
        """Checks if the native git executable exists in system PATH."""
        return shutil.which("git") is not None

    def _run_git(self, args: List[str], timeout: int = 5) -> Tuple[int, str, str]:
        """Executes a git command in the repository root."""
        if not self.is_git_available():
            return 127, "", "git executable not found in PATH"
        try:
            res = subprocess.run(
                ["git"] + args,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except Exception as e:
            return 1, "", str(e)

    # ==========================================
    # READ-ONLY Git Operations
    # ==========================================

    def inspect_status(self) -> GitWorktreeStatus:
        """Inspects current working tree, branch, commit, and tags."""
        code, out, _ = self._run_git(["rev-parse", "--is-inside-work-tree"])
        if code != 0 or out != "true":
            return GitWorktreeStatus(
                is_git_repo=False,
                is_clean=False,
                current_branch="unknown",
                current_commit=None,
                modified_files=[],
                untracked_files=[],
                staged_files=[],
                latest_tag=None,
                tags=[],
            )

        # Branch
        _, branch_out, _ = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        current_branch = branch_out or "HEAD"

        # Commit
        _, commit_out, _ = self._run_git(["rev-parse", "--short", "HEAD"])
        current_commit = commit_out or None

        # Tags
        _, tag_out, _ = self._run_git(["tag", "-l"])
        tags = [t.strip() for t in tag_out.splitlines() if t.strip()]

        # Latest tag
        _, latest_tag_out, _ = self._run_git(["describe", "--tags", "--abbrev=0"])
        latest_tag = latest_tag_out if latest_tag_out else (tags[-1] if tags else None)

        # Status porcelain
        _, status_out, _ = self._run_git(["status", "--porcelain"])
        modified: List[str] = []
        untracked: List[str] = []
        staged: List[str] = []

        for line in status_out.splitlines():
            if not line:
                continue
            idx_status = line[0]
            work_status = line[1]
            file_path = line[3:].strip()
            if idx_status in ("M", "A", "D", "R", "C"):
                staged.append(file_path)
            if work_status == "M":
                modified.append(file_path)
            elif idx_status == "?" and work_status == "?":
                untracked.append(file_path)

        is_clean = len(modified) == 0 and len(untracked) == 0 and len(staged) == 0

        # Ahead / Behind
        ahead = 0
        behind = 0
        code, rev_count, _ = self._run_git(["rev-list", "--left-right", "--count", "@{upstream}...HEAD"])
        if code == 0 and rev_count:
            parts = rev_count.split()
            if len(parts) == 2:
                behind = int(parts[0])
                ahead = int(parts[1])

        return GitWorktreeStatus(
            is_git_repo=True,
            is_clean=is_clean,
            current_branch=current_branch,
            current_commit=current_commit,
            modified_files=modified,
            untracked_files=untracked,
            staged_files=staged,
            latest_tag=latest_tag,
            tags=tags,
            ahead_commits=ahead,
            behind_commits=behind,
        )

    def has_tag(self, tag_name: str) -> bool:
        """Checks if an exact tag exists in the repository."""
        code, out, _ = self._run_git(["tag", "-l", tag_name])
        return code == 0 and bool(out.strip())

    def get_diff_summary(self) -> Dict[str, Any]:
        """Returns statistical summary of unstaged and staged diffs."""
        _, diff_stat, _ = self._run_git(["diff", "--stat"])
        _, staged_stat, _ = self._run_git(["diff", "--cached", "--stat"])
        return {
            "working_tree_diff": diff_stat,
            "staged_diff": staged_stat,
        }

    # ==========================================
    # GUARDED MUTATING Git Operations
    # ==========================================

    def create_release_tag(
        self,
        tag_name: str,
        message: str,
        policy: GitMutationPolicy = GitMutationPolicy.GUARDED,
    ) -> Dict[str, Any]:
        """Creates an annotated git tag with fail-closed checks."""
        if policy == GitMutationPolicy.DENIED:
            return {"success": False, "error": "Git mutation denied by policy."}

        status = self.inspect_status()
        if not status.is_git_repo:
            return {"success": False, "error": "Target is not a git repository."}

        if policy == GitMutationPolicy.GUARDED and not status.is_clean:
            return {
                "success": False,
                "error": "Cannot create release tag on dirty working tree. Commit or stash changes first.",
                "status": status.to_dict(),
            }

        if self.has_tag(tag_name):
            return {"success": False, "error": f"Tag '{tag_name}' already exists."}

        code, out, err = self._run_git(["tag", "-a", tag_name, "-m", message])
        if code != 0:
            return {"success": False, "error": f"Git tag creation failed: {err}"}

        return {
            "success": True,
            "tag": tag_name,
            "commit": status.current_commit,
            "message": message,
        }
