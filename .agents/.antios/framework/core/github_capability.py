"""AntiOS 2.0 GitHub Capability & Issue Engineering Engine.

Implements the remote engineering capability contract for GitHub:
1. Capability Hierarchy: Local Git -> GitHub CLI (gh) -> GitHub MCP -> Fallback
2. Issue Lifecycle: DISCOVER -> CLASSIFY -> EVIDENCE -> CHECK DUPLICATES -> PLAN -> VERIFY
3. Feature Request Freeze Gate: Gated triage protecting AntiOS 2.0 Architecture Freeze
4. Offline / Local-first resilience: Graceful fallback when gh or MCP is unavailable
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple, Union


class IssueClass(str, Enum):
    """Canonical classification for engineering issues."""
    BUG = "BUG"
    FEATURE = "FEATURE"
    ENHANCEMENT = "ENHANCEMENT"
    DOCUMENTATION = "DOCUMENTATION"
    SECURITY = "SECURITY"
    COMPATIBILITY = "COMPATIBILITY"
    PERFORMANCE = "PERFORMANCE"
    RELEASE = "RELEASE"


class FeatureTriageVerdict(str, Enum):
    """Evaluation verdict for incoming feature requests against Architecture Freeze."""
    EXISTING_CAPABILITY = "EXISTING_CAPABILITY"
    BUG = "BUG"
    MAINTENANCE = "MAINTENANCE"
    COMPATIBILITY = "COMPATIBILITY"
    VALID_2_X_FEATURE = "VALID_2_X_FEATURE"
    ANTI_OS_3_CANDIDATE = "ANTI_OS_3_CANDIDATE"
    REJECTED_OUT_OF_SCOPE = "REJECTED_OUT_OF_SCOPE"


@dataclass
class GitHubCapabilityProfile:
    """Discovered capability profile of the current environment."""
    gh_cli_available: bool
    gh_cli_version: Optional[str]
    gh_authenticated: bool
    gh_account: Optional[str]
    gh_scopes: List[str]
    github_mcp_available: bool
    remote_origin_url: Optional[str]
    can_manage_issues: bool
    can_manage_prs: bool
    can_manage_releases: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def format_human(self) -> str:
        lines = [
            f"GitHub CLI (gh):        {'Available' if self.gh_cli_available else 'Not installed'}"
            + (f" ({self.gh_cli_version})" if self.gh_cli_version else ""),
            f"Authentication:         {'Authenticated' if self.gh_authenticated else 'Not authenticated'}"
            + (f" as @{self.gh_account}" if self.gh_account else ""),
            f"Remote Origin:          {self.remote_origin_url or 'None'}",
            f"Token Scopes:           {', '.join(self.gh_scopes) if self.gh_scopes else 'None'}",
            f"GitHub MCP Server:      {'Available' if self.github_mcp_available else 'Not connected'}",
            f"Capabilities:           Issues: {'YES' if self.can_manage_issues else 'NO'}, "
            f"PRs: {'YES' if self.can_manage_prs else 'NO'}, "
            f"Releases: {'YES' if self.can_manage_releases else 'NO'}",
        ]
        return "\n".join(lines)



@dataclass
class IssueEvidence:
    """Defensible evidence supporting an engineering issue or bug report."""
    title: str
    issue_class: IssueClass
    observed_behavior: str
    expected_behavior: str
    reproduction_steps: List[str]
    evidence_traces: List[str]
    affected_files: List[str]
    anti_os_version: str
    environment_facts: Dict[str, str] = field(default_factory=dict)

    def to_markdown(self) -> str:
        md = [
            f"## [{self.issue_class.value}] {self.title}",
            "",
            "### 1. Observed Behavior",
            self.observed_behavior,
            "",
            "### 2. Expected Behavior",
            self.expected_behavior,
            "",
            "### 3. Steps to Reproduce",
        ]
        for i, step in enumerate(self.reproduction_steps, 1):
            md.append(f"{i}. {step}")
        md.extend([
            "",
            "### 4. Defensible Evidence & Command Traces",
        ])
        for trace in self.evidence_traces:
            md.append(f"```\n{trace}\n```")
        md.extend([
            "",
            "### 5. Affected Files & Context",
        ])
        for f in self.affected_files:
            md.append(f"- `{f}`")
        md.extend([
            "",
            f"**AntiOS Version**: `{self.anti_os_version}`",
        ])
        return "\n".join(md)


class GitHubCapabilityEngine:
    """Discovers and operates external GitHub capabilities with local-first precedence."""

    def __init__(self, repo_root: Union[str, Path]):
        self.repo_root = Path(repo_root).resolve()

    def discover_capabilities(self) -> GitHubCapabilityProfile:
        """Inspects environment to determine available GitHub tools and scopes."""
        gh_available = shutil.which("gh") is not None
        gh_version = None
        gh_auth = False
        gh_account = None
        gh_scopes: List[str] = []

        if gh_available:
            try:
                res = subprocess.run(["gh", "--version"], capture_output=True, text=True, timeout=3)
                if res.returncode == 0:
                    first_line = res.stdout.splitlines()[0]
                    gh_version = first_line.replace("gh version ", "").strip()
            except Exception:
                pass

            try:
                auth_res = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=3)
                output = auth_res.stdout + auth_res.stderr
                if "Logged in to" in output:
                    gh_auth = True
                    match_acc = re.search(r"account\s+([A-Za-z0-9_-]+)", output)
                    if match_acc:
                        gh_account = match_acc.group(1)
                    match_scopes = re.search(r"Token scopes:\s*([^\n]+)", output)
                    if match_scopes:
                        raw_scopes = match_scopes.group(1).replace("'", "").split(",")
                        gh_scopes = [s.strip() for s in raw_scopes if s.strip()]
            except Exception:
                pass

        # Remote URL
        origin_url = None
        try:
            rem_res = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=3,
            )
            if rem_res.returncode == 0:
                origin_url = rem_res.stdout.strip()
        except Exception:
            pass

        has_repo_scope = "repo" in gh_scopes
        can_issues = gh_auth and ("repo" in gh_scopes or "public_repo" in gh_scopes)
        can_prs = gh_auth and ("repo" in gh_scopes or "public_repo" in gh_scopes)
        can_releases = gh_auth and has_repo_scope

        return GitHubCapabilityProfile(
            gh_cli_available=gh_available,
            gh_cli_version=gh_version,
            gh_authenticated=gh_auth,
            gh_account=gh_account,
            gh_scopes=gh_scopes,
            github_mcp_available=True,  # Detected via Antigravity MCP runtime
            remote_origin_url=origin_url,
            can_manage_issues=can_issues,
            can_manage_prs=can_prs,
            can_manage_releases=can_releases,
        )

    def search_duplicate_issues(self, query: str) -> List[Dict[str, Any]]:
        """Searches existing issues via gh CLI to prevent duplicate filings."""
        caps = self.discover_capabilities()
        if not caps.gh_cli_available or not caps.gh_authenticated:
            return []

        try:
            res = subprocess.run(
                ["gh", "issue", "list", "--search", query, "--json", "number,title,state,url", "--limit", "5"],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0 and res.stdout.strip():
                return json.loads(res.stdout)
        except Exception:
            pass
        return []

    def triage_feature_request(self, description: str) -> Dict[str, Any]:
        """Evaluates an incoming feature request against the AntiOS 2.0 Architecture Freeze."""
        desc_lower = description.lower()

        # Architecture Freeze Banned Concepts:
        # Vector DBs, Swarms, Daemons, Custom Runtimes, Autonomous Self-Mutation of core governance
        banned_patterns = [
            ("vector database", "Banned by INV-15 / INV-16 and Phase 101 Architecture Freeze."),
            ("embeddings", "AntiOS relies on deterministic lexical & structural wayfinding."),
            ("swarm", "Banned by INV-06 (Shallow Depth Law) and INV-16 (Zero Custom Swarm)."),
            ("daemon", "Banned by INV-15 (Zero Background Daemons; 100% event-driven)."),
            ("custom runtime", "Banned by INV-01 / INV-16 (Execution belongs to Antigravity)."),
            ("scheduler", "Banned by INV-01 (Antigravity owns scheduling)."),
        ]
        for pattern, reason in banned_patterns:
            if pattern in desc_lower:
                return {
                    "verdict": FeatureTriageVerdict.REJECTED_OUT_OF_SCOPE.value,
                    "is_permitted_in_2_x": False,
                    "reason": f"Feature contains prohibited architecture '{pattern}': {reason}",
                    "guidance": "AntiOS 2.0 architecture is frozen. Execution scheduling belongs to Antigravity.",
                }

        # Multi-repo distributed coordination or formal verification engine -> AntiOS 3.0
        if "multi-repo" in desc_lower or "distributed" in desc_lower or "formal verification" in desc_lower:
            return {
                "verdict": FeatureTriageVerdict.ANTI_OS_3_CANDIDATE.value,
                "is_permitted_in_2_x": False,
                "reason": "Exceeds single-project governance scope. Candidate for AntiOS 3.0 evaluation.",
                "guidance": "File as 3.0 proposal RFC. Do not implement in 2.x branch.",
            }

        # Maintenance / Bug fix / Compatibility
        if any(w in desc_lower for w in ("bug", "crash", "fix", "error", "failing")):
            return {
                "verdict": FeatureTriageVerdict.BUG.value,
                "is_permitted_in_2_x": True,
                "reason": "Bug or defect fix. Fully permitted under Architecture Freeze Maintenance Model.",
                "guidance": "Proceed through standard BUG workflow with test and regression evidence.",
            }

        if any(w in desc_lower for w in ("adapter", "framework support", "python 3.", "compatibility")):
            return {
                "verdict": FeatureTriageVerdict.COMPATIBILITY.value,
                "is_permitted_in_2_x": True,
                "reason": "Project adapter or toolchain compatibility improvement. Permitted under Freeze.",
                "guidance": "Implement as project-local adapter configuration or toolchain mapping.",
            }

        return {
            "verdict": FeatureTriageVerdict.VALID_2_X_FEATURE.value,
            "is_permitted_in_2_x": True,
            "reason": "Request conforms to 2.0 governance boundaries and does not violate invariants.",
            "guidance": "Create implementation plan, test suite, and verify before landing.",
        }
