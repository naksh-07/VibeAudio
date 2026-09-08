"""AntiOS Maker-Checker Structured Verdict Protocol.

Defines the contract and parser for Independent Verifier subagent reports.
Ensures machine-readable, deterministic pass/fail accounting.
"""

from __future__ import annotations
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ResultItem:
    __test__ = False
    command: str
    exit_code: int
    passed: bool
    details: str = ""


# Alias for backward compatibility
TestResult = ResultItem
TestResult.__test__ = False


@dataclass
class VerificationVerdict:
    status: str  # "PASS", "FAIL", "BLOCK"
    risk_tier: str  # "LOW", "MEDIUM", "HIGH"
    files_audited: List[str] = field(default_factory=list)
    tests: List[ResultItem] = field(default_factory=list)
    same_change_set_verified: bool = True
    summary: str = ""
    issues: List[str] = field(default_factory=list)
    git_head: Optional[str] = None
    manifest_fingerprint: Optional[str] = None
    adapter_verified: bool = True
    timestamp: Optional[str] = None
    task_id: Optional[str] = None
    project_member: Optional[str] = None
    config_fingerprint: Optional[str] = None
    affected_dependents: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def is_current(
        self,
        repo_root: str,
        current_manifest_fingerprint: str = "",
        current_git_head: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """Evaluates whether this physical verdict is still current or has been invalidated."""
        reasons: List[str] = []
        if self.status != "PASS":
            return False, ["Verdict status is not PASS."]

        # Inspect working tree
        try:
            from framework.core.worktree import WorktreeSnapshot
            snapshot = WorktreeSnapshot.capture(repo_root)
            substantive_dirty = [
                f for f in snapshot.dirty_files
                if not f.endswith("ACTIVE_CONTEXT.md") and not f.startswith(".git")
            ]
            if substantive_dirty:
                reasons.append(
                    f"Working tree files modified after verification: {', '.join(substantive_dirty[:5])}"
                )
        except Exception:
            pass

        # Manifest drift
        if self.manifest_fingerprint and current_manifest_fingerprint:
            if self.manifest_fingerprint != current_manifest_fingerprint:
                reasons.append("Project manifests modified since verification (fingerprint drift).")

        # Git HEAD
        if self.git_head and current_git_head:
            if self.git_head != current_git_head:
                reasons.append(f"Git HEAD advanced from {self.git_head} to {current_git_head}.")

        return len(reasons) == 0, reasons


def parse_verdict(raw_text: str) -> VerificationVerdict:
    """Parses a structured verdict from raw verifier text or fenced JSON code block."""
    if not raw_text or not raw_text.strip():
        return VerificationVerdict(
            status="BLOCK",
            risk_tier="HIGH",
            summary="Empty verifier response received",
            issues=["No verdict payload emitted by verifier."]
        )

    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    payload_str = json_match.group(1) if json_match else raw_text.strip()

    try:
        data = json.loads(payload_str)
        if not isinstance(data, dict):
            raise ValueError("Root JSON must be an object")

        raw_status = str(data.get("status", "BLOCK")).upper()
        if raw_status not in ("PASS", "FAIL", "BLOCK"):
            raw_status = "BLOCK"

        raw_tier = str(data.get("risk_tier", "MEDIUM")).upper()
        if raw_tier not in ("LOW", "MEDIUM", "HIGH"):
            raw_tier = "MEDIUM"

        tests = []
        for t in data.get("tests", []):
            if isinstance(t, dict):
                tests.append(
                    ResultItem(
                        command=str(t.get("command", "")),
                        exit_code=int(t.get("exit_code", 0)),
                        passed=bool(t.get("passed", False)),
                        details=str(t.get("details", "")),
                    )
                )

        git_head = data.get("git_head")
        manifest_fingerprint = data.get("manifest_fingerprint")
        adapter_verified = bool(data.get("adapter_verified", True))
        timestamp = data.get("timestamp")
        task_id = data.get("task_id")
        project_member = data.get("project_member")
        config_fingerprint = data.get("config_fingerprint")
        affected_dependents = [str(d) for d in data.get("affected_dependents", [])]

        return VerificationVerdict(
            status=raw_status,
            risk_tier=raw_tier,
            files_audited=[str(f) for f in data.get("files_audited", [])],
            tests=tests,
            same_change_set_verified=bool(data.get("same_change_set_verified", True)),
            summary=str(data.get("summary", "")),
            issues=[str(i) for i in data.get("issues", [])],
            git_head=str(git_head) if git_head else None,
            manifest_fingerprint=str(manifest_fingerprint) if manifest_fingerprint else None,
            adapter_verified=adapter_verified,
            timestamp=str(timestamp) if timestamp else None,
            task_id=str(task_id) if task_id else None,
            project_member=str(project_member) if project_member else None,
            config_fingerprint=str(config_fingerprint) if config_fingerprint else None,
            affected_dependents=affected_dependents,
        )

    except Exception as e:
        status = "BLOCK"
        if "VERDICT: PASS" in raw_text.upper():
            status = "PASS"
        elif "VERDICT: FAIL" in raw_text.upper():
            status = "FAIL"

        return VerificationVerdict(
            status=status,
            risk_tier="HIGH",
            summary="Extracted via heuristic fallback",
            issues=[f"Failed to parse formal JSON verdict: {str(e)}"]
        )


def format_verdict(verdict: VerificationVerdict) -> str:
    """Formats a VerificationVerdict into a standardized markdown block."""
    return f"```json\n{verdict.to_json(indent=2)}\n```"


def prepare_checker_context(
    task_id: str,
    objective: str,
    risk_tier: str,
    changed_files: List[str],
    test_commands: List[str],
    target_member: Optional[str] = None,
    affected_dependents: Optional[List[str]] = None,
    protected_zones: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Prepares minimal, noise-free structured context for a fresh-context Checker subagent.

    Enforces:
    - Shallow Depth Law: Depth is capped at 2 (Parent -> Child); subagents must NEVER spawn children.
    - Minimal context passing: Passes only objective, changed files, test runners, and boundaries.
    - Physical verification mandate: Tests must be physically executed via run_command.
    """
    return {
        "task_id": task_id,
        "role": "INDEPENDENT_VERIFIER",
        "objective": objective,
        "risk_tier": risk_tier,
        "target_member": target_member,
        "affected_dependents": affected_dependents or [],
        "changed_files": changed_files,
        "test_commands": test_commands,
        "protected_zones": protected_zones or [".agents", "framework"],
        "invariants": {
            "shallow_depth_law": "Subagent depth is capped at 2. Calling invoke_subagent is strictly forbidden.",
            "physical_execution": "Zero trust in verbal claims. Test commands must be physically executed via run_command.",
            "boundary_defense": "Zero modifications allowed to protected zones (.agents/, framework/, antios.config.json).",
            "same_change_set": "Documentation and code modifications must be synchronized in the same change set.",
        },
        "verdict_schema": {
            "status": "PASS | FAIL | BLOCK",
            "risk_tier": risk_tier,
            "files_audited": changed_files,
            "tests": [{"command": "...", "exit_code": 0, "passed": True, "details": "..."}],
            "same_change_set_verified": True,
            "summary": "...",
            "issues": [],
            "project_member": target_member,
        }
    }


def evaluate_checker_verdict(
    verdict: VerificationVerdict,
    required_risk_tier: str = "HIGH"
) -> Tuple[bool, str]:
    """Validates whether a VerificationVerdict qualifies as an authoritative pass.

    Returns (is_approved, reason).
    """
    if verdict.status == "FAIL":
        issues_str = "; ".join(verdict.issues) if verdict.issues else "No details provided"
        return False, f"Checker rejected verification (status FAIL): {issues_str}"

    if verdict.status == "BLOCK":
        issues_str = "; ".join(verdict.issues) if verdict.issues else "Verifier blocked execution"
        return False, f"Checker blocked verification (status BLOCK): {issues_str}"

    if verdict.status != "PASS":
        return False, f"Unknown verdict status '{verdict.status}'. Failing closed."

    if not verdict.same_change_set_verified:
        return False, "Checker noted Same Change Set violation (code/doc desynchronization)."

    if any("Failed to parse formal JSON verdict" in issue for issue in verdict.issues):
        return False, "Checker verdict is malformed: extracted via heuristic fallback without verified JSON payload."

    if required_risk_tier.upper() in ("HIGH", "MEDIUM"):
        if not verdict.tests:
            return False, f"{required_risk_tier.upper()} risk task requires at least one executed physical test result in verdict."
        failing_tests = [t for t in verdict.tests if not t.passed or t.exit_code != 0]
        if failing_tests:
            return False, f"Checker verdict contained {len(failing_tests)} failing test(s)."

    return True, "Checker verdict verified and approved."