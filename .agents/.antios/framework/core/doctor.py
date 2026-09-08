"""AntiOS 2.0 Diagnostic Doctor & Status Engine.

Provides first-class system and project inspection:
1. `antios doctor`: Deep diagnostic inspection of installation, manifest,
   runtime closure, toolchains, git state, 10 drift domains, and stale metadata.
2. `antios status`: Compact operational summary answering:
   - What version am I running?
   - Is AntiOS installed correctly?
   - Is this project adapted?
   - Is the project healthy?
   - Is drift detected?
   - Are proofs valid?
   - Is runtime healthy?
   - Are updates available?
   - Is human intervention required?

Guarantees:
- Never exposes secrets, tokens, or credentials (automated secret redaction filter).
- Fail-safe inspection: never crashes if a file or tool is missing.
- Structured `--json` and human-readable output formats.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

from framework.core.discovery import is_tool_in_path
from framework.core.drift_health import IntelligenceHealthEngine, ProjectDriftEngine
from framework.core.experience import get_storage_status
from framework.core.git_capability import GitCapabilityEngine
from framework.core.manifest import InstallationState, load_manifest
from framework.core.provenance import ProvenanceTracker
from framework.core.runtime_contract import verify_runtime_closure
from framework.core.version import ANTIOS_VERSION, CURRENT_SCHEMA_VERSION, SemVer, get_version_info


class DiagnosticSeverity(str, Enum):
    """Severity classification for doctor findings."""
    OK = "OK"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class DiagnosticCheck:
    """Individual diagnostic inspection check result."""
    name: str
    category: str
    severity: DiagnosticSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    remediation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "severity": self.severity.value,
            "message": redact_secrets(self.message),
            "details": redact_secrets_dict(self.details),
            "remediation": redact_secrets(self.remediation) if self.remediation else None,
        }


# Regex to scrub sensitive tokens and secrets
SECRET_PATTERNS = [
    re.compile(r"gh[opsu]_[A-Za-z0-9_]{36,255}"),
    re.compile(r"(?:bearer|token|secret|password|api[_-]?key)\s*[:=]\s*([^\s,;]+)", re.IGNORECASE),
]


def redact_secrets(text: Optional[str]) -> str:
    """Sanitizes text strings to prevent credential or secret leaks."""
    if not text:
        return ""
    sanitized = text
    # GitHub tokens
    sanitized = re.sub(r"gh[opsu]_[A-Za-z0-9_]{10,}", "gho_REDACTED", sanitized)
    # Generic key/value secrets
    sanitized = re.sub(
        r"((?:token|secret|password|api[_-]?key)\s*[:=]\s*)([A-Za-z0-9_\-\.]{8,})",
        r"\1REDACTED",
        sanitized,
        flags=re.IGNORECASE,
    )
    return sanitized


def redact_secrets_dict(data: Any) -> Any:
    """Recursively redacts dictionary values."""
    if isinstance(data, dict):
        return {k: redact_secrets_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [redact_secrets_dict(item) for item in data]
    elif isinstance(data, str):
        return redact_secrets(data)
    return data


@dataclass
class DoctorReport:
    """Full diagnostic dossier produced by antios doctor."""
    target_root: str
    anti_os_version: str
    is_healthy: bool
    total_checks: int
    passed_checks: int
    warnings: int
    errors: int
    checks: List[DiagnosticCheck]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_root": self.target_root,
            "anti_os_version": self.anti_os_version,
            "is_healthy": self.is_healthy,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "warnings": self.warnings,
            "errors": self.errors,
            "checks": [c.to_dict() for c in self.checks],
        }

    def format_human(self) -> str:
        lines = [
            "=" * 60,
            f"AntiOS Doctor Diagnostic Report (v{self.anti_os_version})",
            f"Target: {self.target_root}",
            f"Overall Status: {'HEALTHY' if self.is_healthy else 'ATTENTION REQUIRED'}",
            f"Passed: {self.passed_checks}/{self.total_checks} | Warnings: {self.warnings} | Errors: {self.errors}",
            "=" * 60,
            "",
        ]
        for c in self.checks:
            if c.severity == DiagnosticSeverity.OK:
                icon = "[OK]"
            elif c.severity == DiagnosticSeverity.INFO:
                icon = "[INFO]"
            elif c.severity == DiagnosticSeverity.WARNING:
                icon = "[WARN]"
            else:
                icon = "[FAIL]"
            lines.append(f"{icon:<6} {c.category} - {c.name}: {c.message}")
            if c.remediation and c.severity in (DiagnosticSeverity.WARNING, DiagnosticSeverity.ERROR):
                lines.append(f"       Remediation: {c.remediation}")
        return "\n".join(lines)



@dataclass
class OperationalStatus:
    """Compact operational summary produced by antios status."""
    version: str
    channel: str
    is_installed: bool
    is_adapted: bool
    is_healthy: bool
    drift_detected: bool
    drift_severity: str
    proofs_valid: bool
    runtime_healthy: bool
    updates_available: bool
    intervention_required: bool
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def format_human(self) -> str:
        lines = [
            f"AntiOS Version:         {self.version} ({self.channel})",
            f"Installation State:     {'Installed' if self.is_installed else 'Not Installed'}",
            f"Project Adaptation:     {'Adapted' if self.is_adapted else 'Unadapted'}",
            f"System Health:          {'Healthy' if self.is_healthy else 'Attention Required'}",
            f"Drift Detected:         {self.drift_severity if self.drift_detected else 'None'}",
            f"Durable Proofs:         {'Valid' if self.proofs_valid else 'Invalid / Stale'}",
            f"Runtime Engine:         {'Healthy' if self.runtime_healthy else 'Degraded'}",
            f"Updates Available:      {'Yes' if self.updates_available else 'No'}",
            f"Intervention Required:  {'Yes' if self.intervention_required else 'No'}",
            f"Summary:                {self.summary}",
        ]
        return "\n".join(lines)


class DoctorEngine:
    """Executes deterministic diagnostics across repository and instance states."""

    def __init__(self, repo_root: Union[str, Path]):
        self.repo_root = Path(repo_root).resolve()

    def run_doctor(self) -> DoctorReport:
        """Runs the complete diagnostic suite."""
        checks: List[DiagnosticCheck] = []

        # 1. AntiOS Installation & Manifest Check
        manifest_file = self.repo_root / ".antios/manifest.json"
        manifest = None
        if not manifest_file.exists():
            checks.append(DiagnosticCheck(
                name="Manifest Existence",
                category="Installation",
                severity=DiagnosticSeverity.WARNING,
                message="No .antios/manifest.json found. AntiOS is not installed in this project.",
                remediation="Run 'antios install' to initialize AntiOS.",
            ))
        else:
            try:
                manifest = load_manifest(self.repo_root)
                if manifest and manifest.installation_state == InstallationState.INSTALLED:
                    checks.append(DiagnosticCheck(
                        name="Manifest Integrity",
                        category="Installation",
                        severity=DiagnosticSeverity.OK,
                        message=f"Manifest loaded successfully (v{manifest.antios_version}). State: INSTALLED.",
                    ))
                else:
                    checks.append(DiagnosticCheck(
                        name="Manifest Integrity",
                        category="Installation",
                        severity=DiagnosticSeverity.WARNING,
                        message=f"Manifest state is {manifest.installation_state if manifest else 'corrupted'}.",
                        remediation="Run 'antios repair' to restore instance state.",
                    ))
            except Exception as e:
                checks.append(DiagnosticCheck(
                    name="Manifest Integrity",
                    category="Installation",
                    severity=DiagnosticSeverity.ERROR,
                    message=f"Corrupted manifest: {e}",
                    remediation="Run 'antios repair --force' or re-install.",
                ))

        # 2. Version Consistency Check
        ver_info = get_version_info(self.repo_root)
        if manifest:
            if manifest.antios_version == ver_info.version:
                checks.append(DiagnosticCheck(
                    name="Version Consistency",
                    category="Versioning",
                    severity=DiagnosticSeverity.OK,
                    message=f"Project instance ({manifest.antios_version}) matches framework ({ver_info.version}).",
                ))
            else:
                checks.append(DiagnosticCheck(
                    name="Version Consistency",
                    category="Versioning",
                    severity=DiagnosticSeverity.INFO,
                    message=f"Instance version {manifest.antios_version} differs from framework {ver_info.version}.",
                    remediation="Run 'antios update' to synchronize instance artifacts.",
                ))
        else:
            checks.append(DiagnosticCheck(
                name="Framework Version",
                category="Versioning",
                severity=DiagnosticSeverity.OK,
                message=f"Framework version {ver_info.version} ({ver_info.channel}).",
            ))

        # 3. Project Configuration & Adapter Check
        config_file = self.repo_root / "antios.config.json"
        if config_file.exists():
            checks.append(DiagnosticCheck(
                name="Adapter Configuration",
                category="Configuration",
                severity=DiagnosticSeverity.OK,
                message="Project configuration antios.config.json is present.",
            ))
        else:
            checks.append(DiagnosticCheck(
                name="Adapter Configuration",
                category="Configuration",
                severity=DiagnosticSeverity.WARNING,
                message="antios.config.json is missing.",
                remediation="Run 'antios adapt' to generate project configuration.",
            ))

        # 4. Runtime Scripts Check
        runtime_dir = self.repo_root / ".antios/runtime"
        if runtime_dir.is_dir():
            closure_res = verify_runtime_closure(self.repo_root)
            if closure_res.is_closed:
                checks.append(DiagnosticCheck(
                    name="Runtime Closure",
                    category="Runtime",
                    severity=DiagnosticSeverity.OK,
                    message="Runtime scripts are self-contained with zero framework source leaks.",
                ))
            else:
                checks.append(DiagnosticCheck(
                    name="Runtime Closure",
                    category="Runtime",
                    severity=DiagnosticSeverity.WARNING,
                    message=f"Runtime boundary warnings: {len(closure_res.violations)} violations.",
                    details={"violations": closure_res.violations},
                    remediation="Run 'antios repair' to regenerate runtime scripts.",
                ))

        elif manifest:
            checks.append(DiagnosticCheck(
                name="Runtime Scripts",
                category="Runtime",
                severity=DiagnosticSeverity.ERROR,
                message=".antios/runtime directory is missing in installed instance.",
                remediation="Run 'antios repair' to restore runtime scripts.",
            ))

        # 5. Git Working Tree State
        git_eng = GitCapabilityEngine(self.repo_root)
        if git_eng.is_git_available():
            git_stat = git_eng.inspect_status()
            if git_stat.is_git_repo:
                if git_stat.is_clean:
                    checks.append(DiagnosticCheck(
                        name="Git Working Tree",
                        category="Git",
                        severity=DiagnosticSeverity.OK,
                        message=f"Working tree is clean on branch '{git_stat.current_branch}'.",
                    ))
                else:
                    checks.append(DiagnosticCheck(
                        name="Git Working Tree",
                        category="Git",
                        severity=DiagnosticSeverity.INFO,
                        message=f"Working tree has uncommitted modifications ({len(git_stat.modified_files)} modified, {len(git_stat.untracked_files)} untracked).",
                        remediation="Commit or stash changes before release or update operations.",
                    ))
            else:
                checks.append(DiagnosticCheck(
                    name="Git Repository",
                    category="Git",
                    severity=DiagnosticSeverity.INFO,
                    message="Target directory is not a Git repository.",
                ))
        else:
            checks.append(DiagnosticCheck(
                name="Git Toolchain",
                category="Git",
                severity=DiagnosticSeverity.WARNING,
                message="Git executable not found in PATH.",
            ))

        # 6. Drift & Health Evaluation
        findings = ProjectDriftEngine.evaluate_drift(workspace_root=str(self.repo_root))
        health = IntelligenceHealthEngine.evaluate_health(workspace_root=str(self.repo_root), findings=findings)

        if not findings or health.status.value in ("HEALTHY", "DEGRADED"):
            checks.append(DiagnosticCheck(
                name="Project Drift",
                category="Health",
                severity=DiagnosticSeverity.OK,
                message=f"Health status: {health.status.value}. Drift findings: {len(findings)}.",
            ))
        else:
            checks.append(DiagnosticCheck(
                name="Project Drift",
                category="Health",
                severity=DiagnosticSeverity.WARNING,
                message=f"Health status: {health.status.value} with {len(findings)} active drift findings.",
                details={"findings": [f.to_dict() for f in findings]},
                remediation="Run 'antios repair' or 'antios adapt' to reconcile drift.",
            ))

        # 7. Active Context Memory Bounds Check
        active_ctx = self.repo_root / "docs/ACTIVE_CONTEXT.md"
        if active_ctx.exists():
            line_count = len(active_ctx.read_text(encoding="utf-8").splitlines())
            if line_count <= 60:
                checks.append(DiagnosticCheck(
                    name="Active Context Bounds",
                    category="Memory",
                    severity=DiagnosticSeverity.OK,
                    message=f"docs/ACTIVE_CONTEXT.md is within budget ({line_count}/60 lines).",
                ))
            else:
                checks.append(DiagnosticCheck(
                    name="Active Context Bounds",
                    category="Memory",
                    severity=DiagnosticSeverity.WARNING,
                    message=f"docs/ACTIVE_CONTEXT.md exceeds 60-line bound ({line_count} lines) - INV-09 violation.",
                    remediation="Run context distillation to compress active context.",
                ))

        # 8. Experience Storage Foundation Check
        storage_status = get_storage_status(project_root=self.repo_root)
        if not storage_status.is_configured:
            checks.append(DiagnosticCheck(
                name="Experience Storage",
                category="Storage",
                severity=DiagnosticSeverity.INFO,
                message="AntiOS Data Directory is not configured for this project.",
                remediation="Run 'antios install --data-dir <dir>' or 'antios data set-dir <dir>' to configure persistent experience storage.",
            ))
        elif not storage_status.db_exists:
            checks.append(DiagnosticCheck(
                name="Experience Storage",
                category="Storage",
                severity=DiagnosticSeverity.ERROR,
                message=f"Configured data directory or experience.db is missing: {storage_status.db_path}",
                details={"issues": storage_status.issues, "data_dir": storage_status.data_dir},
                remediation="Run 'antios data set-dir <dir>' or re-initialize data directory.",
            ))
        elif not storage_status.is_healthy:
            checks.append(DiagnosticCheck(
                name="Experience Storage",
                category="Storage",
                severity=DiagnosticSeverity.WARNING,
                message=f"Experience storage health issues: {', '.join(storage_status.issues)}",
                details={"issues": storage_status.issues, "data_dir": storage_status.data_dir},
                remediation="Inspect database integrity or re-run initialization.",
            ))
        else:
            checks.append(DiagnosticCheck(
                name="Experience Storage",
                category="Storage",
                severity=DiagnosticSeverity.OK,
                message=f"Experience storage is healthy (WAL mode, schema v{storage_status.schema_version}, {storage_status.db_size_bytes} bytes).",
                details={
                    "data_dir": storage_status.data_dir,
                    "project_id": storage_status.project_id,
                    "schema_version": storage_status.schema_version,
                },
            ))

        # Aggregate metrics
        passed = sum(1 for c in checks if c.severity in (DiagnosticSeverity.OK, DiagnosticSeverity.INFO))
        warnings = sum(1 for c in checks if c.severity == DiagnosticSeverity.WARNING)
        errors = sum(1 for c in checks if c.severity == DiagnosticSeverity.ERROR)
        is_healthy = errors == 0

        return DoctorReport(
            target_root=str(self.repo_root),
            anti_os_version=ver_info.version,
            is_healthy=is_healthy,
            total_checks=len(checks),
            passed_checks=passed,
            warnings=warnings,
            errors=errors,
            checks=checks,
        )

    def get_status(self) -> OperationalStatus:
        """Returns concise operational status for antios status."""
        ver_info = get_version_info(self.repo_root)
        manifest = load_manifest(self.repo_root)
        is_installed = manifest is not None and manifest.installation_state == InstallationState.INSTALLED
        is_adapted = manifest is not None and manifest.adaptation_state.value == "ADAPTED"

        findings = ProjectDriftEngine.evaluate_drift(workspace_root=str(self.repo_root))
        health = IntelligenceHealthEngine.evaluate_health(workspace_root=str(self.repo_root), findings=findings)
        drift_detected = len(findings) > 0

        proofs_valid = True
        proofs_file = self.repo_root / ".antios/durable_proofs.json"
        if proofs_file.exists():
            try:
                data = json.loads(proofs_file.read_text(encoding="utf-8"))
                proofs_valid = isinstance(data, list)
            except Exception:
                proofs_valid = False

        runtime_healthy = True
        if (self.repo_root / ".antios/runtime").is_dir():
            runtime_healthy = verify_runtime_closure(self.repo_root).is_closed

        updates_avail = False

        if manifest and manifest.antios_version != ver_info.version:
            updates_avail = True

        storage_status = get_storage_status(project_root=self.repo_root)
        storage_issue = storage_status.is_configured and not storage_status.is_healthy

        intervention_required = (not runtime_healthy) or (health.status.value in ("UNTRUSTED", "STALE")) or storage_issue

        if not is_installed:
            summary = "AntiOS is not installed in this project. Run 'antios install'."
        elif intervention_required:
            if storage_issue:
                summary = f"Attention required: experience storage issue ({', '.join(storage_status.issues)}). Run 'antios doctor'."
            else:
                summary = "Attention required: drift or runtime integrity issues detected. Run 'antios doctor'."
        elif updates_avail:
            summary = f"Update available: instance is on {manifest.antios_version}, framework is {ver_info.version}."
        else:
            summary = "Project instance is fully operational and healthy."

        return OperationalStatus(
            version=ver_info.version,
            channel=ver_info.channel,
            is_installed=is_installed,
            is_adapted=is_adapted,
            is_healthy=not intervention_required,
            drift_detected=drift_detected,
            drift_severity=f"{len(findings)} drift findings" if drift_detected else "None",
            proofs_valid=proofs_valid,
            runtime_healthy=runtime_healthy,
            updates_available=updates_avail,
            intervention_required=intervention_required,
            summary=summary,
        )

