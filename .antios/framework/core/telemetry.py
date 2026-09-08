"""AntiOS Lightweight Execution & Verification Telemetry.

Provides zero-overhead, file-backed audit logging of agent execution,
Maker-Checker dispatch decisions, verification durations, detected failures, and verdicts.
"""

from __future__ import annotations
from dataclasses import asdict, dataclass, field
import datetime
import json
import os
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionTelemetryRecord:
    task_id: str
    task_risk: str  # "LOW", "MEDIUM", "HIGH"
    checker_dispatched: bool
    verification_duration_ms: float
    failures_detected_by_checker: int = 0
    retries: int = 0
    final_verdict: str = "PASS"  # "PASS", "FAIL", "BLOCK"
    scoped_members: List[str] = field(default_factory=list)
    tested_files: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def record_telemetry(repo_root: str, record: ExecutionTelemetryRecord) -> str:
    """Saves an ExecutionTelemetryRecord to reports/telemetry/{task_id}.json."""
    telemetry_dir = os.path.join(repo_root, "reports", "telemetry")
    os.makedirs(telemetry_dir, exist_ok=True)

    filename = f"{record.task_id.replace('/', '_').replace(':', '_')}.json"
    target_path = os.path.join(telemetry_dir, filename)

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(record.to_json(indent=2))

    return target_path


def load_telemetry(repo_root: str, task_id: str) -> Optional[ExecutionTelemetryRecord]:
    """Loads a specific ExecutionTelemetryRecord from reports/telemetry/."""
    telemetry_dir = os.path.join(repo_root, "reports", "telemetry")
    filename = f"{task_id.replace('/', '_').replace(':', '_')}.json"
    target_path = os.path.join(telemetry_dir, filename)

    if not os.path.isfile(target_path):
        return None

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ExecutionTelemetryRecord(**data)
    except Exception:
        return None


def summarize_telemetry(repo_root: str) -> Dict[str, Any]:
    """Summarizes all telemetry records found in reports/telemetry/."""
    telemetry_dir = os.path.join(repo_root, "reports", "telemetry")
    if not os.path.isdir(telemetry_dir):
        return {
            "total_tasks": 0,
            "checker_dispatched_count": 0,
            "pass_rate": 1.0,
            "avg_verification_duration_ms": 0.0,
            "total_failures_caught": 0,
        }

    records: List[ExecutionTelemetryRecord] = []
    for fname in os.listdir(telemetry_dir):
        if fname.endswith(".json"):
            rec = load_telemetry(repo_root, fname[:-5])
            if rec:
                records.append(rec)

    if not records:
        return {
            "total_tasks": 0,
            "checker_dispatched_count": 0,
            "pass_rate": 1.0,
            "avg_verification_duration_ms": 0.0,
            "total_failures_caught": 0,
        }

    checker_count = sum(1 for r in records if r.checker_dispatched)
    pass_count = sum(1 for r in records if r.final_verdict == "PASS")
    failures_caught = sum(r.failures_detected_by_checker for r in records)
    avg_duration = sum(r.verification_duration_ms for r in records) / len(records)

    return {
        "total_tasks": len(records),
        "checker_dispatched_count": checker_count,
        "pass_rate": pass_count / len(records),
        "avg_verification_duration_ms": round(avg_duration, 2),
        "total_failures_caught": failures_caught,
    }
