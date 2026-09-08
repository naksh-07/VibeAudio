"""AntiOS 2.1 Experience Intelligence Engine.

Deterministic, local-first analytics layer over the AntiOS Experience Store (experience.db).
Transforms stored telemetry into useful, auditable engineering intelligence WITHOUT
modifying AntiOS behavior, project learning, memory, or governance.

ABSOLUTE SEPARATION RULE:
- System A (Project Learning & Memory): Learns ABOUT THE TARGET PROJECT.
- System B (Experience Intelligence): Learns ABOUT ANTIOS ITSELF.
- Strictly prohibited from automatically feeding into learning.py, memory.py,
  lessons, project knowledge, skills, rules, or adapters.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from contextlib import closing
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from framework.core.experience import (
    AntiOSDataResolver,
    ExperienceRepository,
    StorageError,
    get_db_connection,
)


class MetricStatus(str, Enum):
    """Epistemic status of an engineering metric."""
    OBSERVED = "OBSERVED"   # Directly witnessed from recorded telemetry counts
    DERIVED = "DERIVED"     # Deterministically computed ratio or rate
    UNKNOWN = "UNKNOWN"     # Telemetry insufficient or denominator is zero


@dataclass
class MetricValue:
    """Represents a bounded, epistemic metric value."""
    name: str
    value: Union[int, float, str, None]
    status: MetricStatus
    unit: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "status": self.status.value,
            "unit": self.unit,
            "notes": self.notes,
        }


@dataclass
class FailurePattern:
    """Bounded representation of a recurring engineering failure pattern."""
    category: str
    occurrence_count: int
    affected_projects: List[str] = field(default_factory=list)
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    related_tools: List[str] = field(default_factory=list)
    recurrence_ratio: float = 0.0
    confidence: str = "OBSERVED"
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "occurrence_count": self.occurrence_count,
            "affected_projects": sorted(list(set(self.affected_projects))),
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "related_tools": sorted(list(set(self.related_tools))),
            "recurrence_ratio": round(self.recurrence_ratio, 4),
            "confidence": self.confidence,
            "summary": self.summary,
        }


@dataclass
class FrictionPattern:
    """Bounded representation of observed navigation or workflow friction."""
    friction_type: str
    occurrence_count: int
    description: str
    affected_targets: List[str] = field(default_factory=list)
    confidence: str = "DERIVED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "friction_type": self.friction_type,
            "occurrence_count": self.occurrence_count,
            "description": self.description,
            "affected_targets": sorted(list(set(self.affected_targets)))[:10],
            "confidence": self.confidence,
        }


@dataclass
class SuccessfulStrategy:
    """Bounded representation of a recurring successful execution trajectory."""
    task_category: str
    tool_sequence: List[str]
    occurrence_count: int
    success_rate: float
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_category": self.task_category,
            "tool_sequence": self.tool_sequence,
            "occurrence_count": self.occurrence_count,
            "success_rate": round(self.success_rate, 4),
            "summary": self.summary,
        }


@dataclass
class CapabilityStats:
    """Usage and reliability statistics for a tool or capability."""
    capability_name: str
    total_calls: int
    success_calls: int
    error_calls: int
    failure_rate: float
    avg_duration_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability_name": self.capability_name,
            "total_calls": self.total_calls,
            "success_calls": self.success_calls,
            "error_calls": self.error_calls,
            "failure_rate": round(self.failure_rate, 4),
            "avg_duration_ms": round(self.avg_duration_ms, 1),
        }


@dataclass
class SubagentStats:
    """Aggregated statistics for subagent activity."""
    total_subagent_turns: int = 0
    roles_observed: Dict[str, int] = field(default_factory=dict)
    conversation_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_subagent_turns": self.total_subagent_turns,
            "roles_observed": dict(self.roles_observed),
            "conversation_count": self.conversation_count,
        }


@dataclass
class ExperienceReport:
    """Comprehensive, structured engineering intelligence report."""
    scope: str  # "PROJECT" or "GLOBAL"
    project_id: Optional[str]
    project_name: Optional[str]
    generated_at: str
    data_directory: str
    database_path: str
    core_metrics: Dict[str, MetricValue] = field(default_factory=dict)
    failure_intelligence: List[FailurePattern] = field(default_factory=list)
    friction_patterns: List[FrictionPattern] = field(default_factory=list)
    successful_strategies: List[SuccessfulStrategy] = field(default_factory=list)
    capability_statistics: List[CapabilityStats] = field(default_factory=list)
    subagent_statistics: SubagentStats = field(default_factory=SubagentStats)
    data_coverage: Dict[str, int] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)
    cross_project_summary: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope": self.scope,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "data_directory": self.data_directory,
            "database_path": self.database_path,
            "core_metrics": {k: v.to_dict() for k, v in self.core_metrics.items()},
            "failure_intelligence": [f.to_dict() for f in self.failure_intelligence],
            "friction_patterns": [f.to_dict() for f in self.friction_patterns],
            "successful_strategies": [s.to_dict() for s in self.successful_strategies],
            "capability_statistics": [c.to_dict() for c in self.capability_statistics],
            "subagent_statistics": self.subagent_statistics.to_dict(),
            "data_coverage": self.data_coverage,
            "limitations": self.limitations,
            "cross_project_summary": self.cross_project_summary,
        }

    def to_markdown(self) -> str:
        lines: List[str] = []
        lines.append(f"# AntiOS Experience Intelligence Report ({self.scope})")
        lines.append("")
        lines.append(f"- **Generated At**: `{self.generated_at}`")
        if self.project_id:
            lines.append(f"- **Project ID**: `{self.project_id}` ({self.project_name or 'unnamed'})")
        lines.append(f"- **Storage Path**: `{self.database_path}`")
        lines.append("")

        lines.append("## 1. Data Coverage & Telemetry Bounds")
        lines.append("")
        for k, v in self.data_coverage.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

        lines.append("## 2. Core Engineering Metrics")
        lines.append("")
        lines.append("| Metric | Value | Epistemic Status | Notes |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for k, m in self.core_metrics.items():
            val_str = f"{m.value}{' ' + m.unit if m.unit else ''}" if m.value is not None else "N/A"
            lines.append(f"| `{m.name}` | **{val_str}** | `{m.status.value}` | {m.notes or '-'} |")
        lines.append("")

        lines.append("## 3. Failure Intelligence")
        lines.append("")
        if not self.failure_intelligence:
            lines.append("*No recurring failure patterns detected in current telemetry snapshot.*")
        else:
            for f in self.failure_intelligence:
                lines.append(f"### Pattern: {f.category} ({f.occurrence_count} occurrences)")
                lines.append(f"- **Summary**: {f.summary}")
                lines.append(f"- **Confidence**: `{f.confidence}`")
                if f.related_tools:
                    lines.append(f"- **Related Capabilities/Tools**: {', '.join(f.related_tools)}")
                if f.first_seen and f.last_seen:
                    lines.append(f"- **Window**: `{f.first_seen}` to `{f.last_seen}`")
                lines.append("")

        lines.append("## 4. Navigation & Workflow Friction")
        lines.append("")
        if not self.friction_patterns:
            lines.append("*No significant workflow friction observed.*")
        else:
            for fr in self.friction_patterns:
                lines.append(f"- **{fr.friction_type}** ({fr.occurrence_count} times): {fr.description}")
                if fr.affected_targets:
                    lines.append(f"  - Affected targets: {', '.join(fr.affected_targets)}")
            lines.append("")

        lines.append("## 5. Successful Execution Strategies")
        lines.append("")
        if not self.successful_strategies:
            lines.append("*Insufficient successful mission trajectories to derive recurring patterns.*")
        else:
            for s in self.successful_strategies:
                seq_str = " -> ".join(s.tool_sequence)
                lines.append(f"- **Category `{s.task_category}`** ({s.occurrence_count} missions, success rate: {round(s.success_rate * 100, 1)}%)")
                lines.append(f"  - Canonical sequence: `{seq_str}`")
                lines.append(f"  - Summary: {s.summary}")
            lines.append("")

        lines.append("## 6. Capability Usage & Reliability")
        lines.append("")
        if not self.capability_statistics:
            lines.append("*No tool invocations recorded.*")
        else:
            lines.append("| Capability / Tool | Invocations | Success | Error | Failure Rate | Avg Duration |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for c in self.capability_statistics:
                lines.append(
                    f"| `{c.capability_name}` | {c.total_calls} | {c.success_calls} | {c.error_calls} | "
                    f"{round(c.failure_rate * 100, 1)}% | {c.avg_duration_ms} ms |"
                )
            lines.append("")

        if self.cross_project_summary:
            lines.append("## 7. Cross-Project Global Overview")
            lines.append("")
            for pk, pv in self.cross_project_summary.items():
                lines.append(f"- **{pk}**: {pv}")
            lines.append("")

        if self.limitations:
            lines.append("## 8. Epistemic Limitations & Data Boundaries")
            lines.append("")
            for lim in self.limitations:
                lines.append(f"> [!NOTE]\n> {lim}\n")

        return "\n".join(lines)

    def to_text(self) -> str:
        sep = "=" * 68
        thin_sep = "-" * 68
        lines: List[str] = [
            sep,
            f"  AntiOS 2.1 Experience Intelligence Report [{self.scope}]",
            sep,
            f"Generated At:    {self.generated_at}",
        ]
        if self.project_id:
            lines.append(f"Project Scope:   {self.project_id} ({self.project_name or 'unnamed'})")
        lines.append(f"Storage DB:      {self.database_path}")
        lines.append(thin_sep)
        lines.append("DATA COVERAGE:")
        for k, v in self.data_coverage.items():
            lines.append(f"  - {k:<24}: {v}")
        lines.append(thin_sep)
        lines.append("CORE METRICS:")
        for k, m in self.core_metrics.items():
            val_str = f"{m.value}{' ' + m.unit if m.unit else ''}" if m.value is not None else "N/A"
            status_tag = f"[{m.status.value}]"
            lines.append(f"  - {m.name:<26}: {val_str:<16} {status_tag}")
        lines.append(thin_sep)
        lines.append("FAILURE PATTERNS:")
        if not self.failure_intelligence:
            lines.append("  (None observed in telemetry snapshot)")
        else:
            for f in self.failure_intelligence:
                lines.append(f"  * {f.category:<24}: {f.occurrence_count} times [{f.confidence}]")
                lines.append(f"    Summary: {f.summary}")
        lines.append(thin_sep)
        lines.append("WORKFLOW & NAVIGATION FRICTION:")
        if not self.friction_patterns:
            lines.append("  (None observed)")
        else:
            for fr in self.friction_patterns:
                lines.append(f"  * {fr.friction_type} ({fr.occurrence_count}x): {fr.description}")
        lines.append(thin_sep)
        lines.append("CAPABILITY USAGE:")
        if not self.capability_statistics:
            lines.append("  (No tool calls recorded)")
        else:
            for c in self.capability_statistics[:10]:
                lines.append(
                    f"  * {c.capability_name:<20}: {c.total_calls} calls, "
                    f"err_rate={round(c.failure_rate * 100, 1)}%, "
                    f"avg={c.avg_duration_ms}ms"
                )
        if self.cross_project_summary:
            lines.append(thin_sep)
            lines.append("CROSS-PROJECT SUMMARY:")
            for k, v in self.cross_project_summary.items():
                lines.append(f"  - {k}: {v}")
        lines.append(sep)
        return "\n".join(lines)


class ExperienceAnalyticsEngine:
    """Deterministic analytics engine operating over experience.db."""

    def __init__(self, db_path: Union[str, Path], timeout: float = 5.0):
        self.db_path = Path(db_path).resolve()
        self.timeout = timeout
        if not self.db_path.is_file():
            raise StorageError(f"Experience database does not exist: {self.db_path}")

    # =========================================================================
    # Public API: Project-Scoped and Global Analysis
    # =========================================================================

    def analyze_project(self, project_id: str) -> ExperienceReport:
        """Runs deterministic analysis scoped to a specific project_id."""
        with closing(get_db_connection(self.db_path, timeout=self.timeout)) as conn:
            # Verify project exists
            cursor = conn.cursor()
            cursor.execute("SELECT project_id, project_name FROM projects WHERE project_id = ?;", (project_id,))
            prow = cursor.fetchone()
            project_name = prow["project_name"] if prow else None

            return self._build_report(
                conn=conn,
                scope="PROJECT",
                project_id=project_id,
                project_name=project_name,
            )

    def analyze_global(self) -> ExperienceReport:
        """Runs cross-project aggregation without leaking sensitive project file paths."""
        with closing(get_db_connection(self.db_path, timeout=self.timeout)) as conn:
            return self._build_report(
                conn=conn,
                scope="GLOBAL",
                project_id=None,
                project_name=None,
            )

    # =========================================================================
    # Internal Deterministic Pipeline
    # =========================================================================

    def _build_report(
        self,
        conn: sqlite3.Connection,
        scope: str,
        project_id: Optional[str],
        project_name: Optional[str],
    ) -> ExperienceReport:
        now_utc = datetime.now(timezone.utc).isoformat()
        data_dir = str(self.db_path.parent)

        # 1. Coverage
        coverage = self._compute_coverage(conn, project_id)

        # 2. Core Metrics
        metrics = self._compute_core_metrics(conn, project_id, coverage)

        # 3. Failure Intelligence
        failures = self._compute_failure_intelligence(conn, project_id)

        # 4. Friction Intelligence
        friction = self._compute_friction_patterns(conn, project_id)

        # 5. Successful Strategies
        strategies = self._compute_successful_strategies(conn, project_id)

        # 6. Capability Statistics
        caps = self._compute_capability_stats(conn, project_id)

        # 7. Subagent Stats
        subagents = self._compute_subagent_stats(conn, project_id)

        # 8. Cross-Project Summary (if GLOBAL)
        cross_proj_summary = self._compute_cross_project_summary(conn) if scope == "GLOBAL" else None

        # 9. Limitations & Disclaimers
        limitations = [
            "Experience Intelligence is an external analytical layer; it does not alter AntiOS runtime behavior.",
            "All findings are passive empirical metrics and do not constitute automatic project learning or durable proofs.",
            "Metrics marked [UNKNOWN] indicate insufficient data or zero denominators; no heuristic guesses are made.",
        ]
        if coverage.get("missions", 0) == 0:
            limitations.append("Experience database has 0 recorded missions; analysis reflects an unpopulated store.")

        return ExperienceReport(
            scope=scope,
            project_id=project_id,
            project_name=project_name,
            generated_at=now_utc,
            data_directory=data_dir,
            database_path=str(self.db_path),
            core_metrics=metrics,
            failure_intelligence=failures,
            friction_patterns=friction,
            successful_strategies=strategies,
            capability_statistics=caps,
            subagent_statistics=subagents,
            data_coverage=coverage,
            limitations=limitations,
            cross_project_summary=cross_proj_summary,
        )

    def _compute_coverage(self, conn: sqlite3.Connection, project_id: Optional[str]) -> Dict[str, int]:
        cursor = conn.cursor()
        tables = ["sessions", "missions", "turns", "tool_calls", "engineering_events", "projects"]
        counts: Dict[str, int] = {}
        for tbl in tables:
            if tbl == "projects":
                cursor.execute("SELECT count(*) as cnt FROM projects;")
                counts["projects"] = cursor.fetchone()["cnt"]
            elif project_id and tbl in {"sessions", "missions", "engineering_events"}:
                cursor.execute(f"SELECT count(*) as cnt FROM {tbl} WHERE project_id = ?;", (project_id,))
                counts[tbl] = cursor.fetchone()["cnt"]
            elif project_id and tbl == "turns":
                cursor.execute(
                    "SELECT count(*) as cnt FROM turns WHERE mission_id IN (SELECT mission_id FROM missions WHERE project_id = ?);",
                    (project_id,),
                )
                counts[tbl] = cursor.fetchone()["cnt"]
            elif project_id and tbl == "tool_calls":
                cursor.execute(
                    """SELECT count(*) as cnt FROM tool_calls 
                       WHERE turn_id IN (
                           SELECT turn_id FROM turns WHERE mission_id IN (
                               SELECT mission_id FROM missions WHERE project_id = ?
                           )
                       );""",
                    (project_id,),
                )
                counts[tbl] = cursor.fetchone()["cnt"]
            else:
                cursor.execute(f"SELECT count(*) as cnt FROM {tbl};")
                counts[tbl] = cursor.fetchone()["cnt"]
        return counts

    def _compute_core_metrics(
        self,
        conn: sqlite3.Connection,
        project_id: Optional[str],
        coverage: Dict[str, int],
    ) -> Dict[str, MetricValue]:
        cursor = conn.cursor()
        metrics: Dict[str, MetricValue] = {}

        # 1. Raw volume counts (OBSERVED)
        missions_cnt = coverage.get("missions", 0)
        sessions_cnt = coverage.get("sessions", 0)
        turns_cnt = coverage.get("turns", 0)
        calls_cnt = coverage.get("tool_calls", 0)

        metrics["mission_count"] = MetricValue("mission_count", missions_cnt, MetricStatus.OBSERVED, notes="Total missions recorded")
        metrics["session_count"] = MetricValue("session_count", sessions_cnt, MetricStatus.OBSERVED, notes="Total sessions recorded")
        metrics["turn_count"] = MetricValue("turn_count", turns_cnt, MetricStatus.OBSERVED, notes="Total turns recorded")
        metrics["tool_call_count"] = MetricValue("tool_call_count", calls_cnt, MetricStatus.OBSERVED, notes="Total sanitized tool invocations")

        # 2. Mission Outcomes (OBSERVED & DERIVED)
        p_filter = "WHERE project_id = ?" if project_id else ""
        p_param = (project_id,) if project_id else ()

        cursor.execute(f"SELECT status, count(*) as cnt FROM missions {p_filter} GROUP BY status;", p_param)
        status_counts = {row["status"]: row["cnt"] for row in cursor.fetchall()}

        completed_cnt = status_counts.get("COMPLETED", 0)
        failed_cnt = status_counts.get("FAILED", 0)
        active_cnt = status_counts.get("ACTIVE", 0)

        metrics["missions_completed"] = MetricValue("missions_completed", completed_cnt, MetricStatus.OBSERVED)
        metrics["missions_failed"] = MetricValue("missions_failed", failed_cnt, MetricStatus.OBSERVED)
        metrics["missions_active"] = MetricValue("missions_active", active_cnt, MetricStatus.OBSERVED)

        if missions_cnt > 0:
            success_rate = completed_cnt / missions_cnt
            failure_rate = failed_cnt / missions_cnt
            metrics["success_rate"] = MetricValue("success_rate", round(success_rate, 4), MetricStatus.DERIVED, unit="ratio", notes="completed / total missions")
            metrics["failure_rate"] = MetricValue("failure_rate", round(failure_rate, 4), MetricStatus.DERIVED, unit="ratio", notes="failed / total missions")
        else:
            metrics["success_rate"] = MetricValue("success_rate", None, MetricStatus.UNKNOWN, notes="Insufficient mission data")
            metrics["failure_rate"] = MetricValue("failure_rate", None, MetricStatus.UNKNOWN, notes="Insufficient mission data")

        # 3. Tool Call Reliability (DERIVED)
        if calls_cnt > 0:
            cursor.execute(
                f"""SELECT status, count(*) as cnt FROM tool_calls 
                   WHERE turn_id IN (
                       SELECT turn_id FROM turns WHERE mission_id IN (
                           SELECT mission_id FROM missions {p_filter}
                       )
                   ) GROUP BY status;""",
                p_param,
            )
            tool_status_counts = {row["status"]: row["cnt"] for row in cursor.fetchall()}
            tool_err_cnt = tool_status_counts.get("ERROR", 0) + tool_status_counts.get("DENIED_BY_GUARD", 0)
            metrics["tool_failure_rate"] = MetricValue(
                "tool_failure_rate",
                round(tool_err_cnt / calls_cnt, 4),
                MetricStatus.DERIVED,
                unit="ratio",
                notes=f"{tool_err_cnt} errors out of {calls_cnt} tool calls",
            )
        else:
            metrics["tool_failure_rate"] = MetricValue("tool_failure_rate", None, MetricStatus.UNKNOWN, notes="No tool calls recorded")

        # 4. Recovery Rate (DERIVED)
        # Recovery rate = missions with at least one failure (TEST_FAILURE or TOOL_FAILURE) that later had SUCCESSFUL_FIX or ended COMPLETED
        ev_p_filter = "WHERE project_id = ?" if project_id else ""
        cursor.execute(
            f"""SELECT mission_id, event_type FROM engineering_events 
               {ev_p_filter} 
               ORDER BY created_at ASC;""",
            p_param,
        )
        mission_events = defaultdict(list)
        for r in cursor.fetchall():
            mission_events[r["mission_id"]].append(r["event_type"])

        missions_with_failure = 0
        missions_recovered = 0
        for m_id, ev_types in mission_events.items():
            has_failure = any(et in ("TEST_FAILURE", "TOOL_FAILURE") for et in ev_types)
            if has_failure:
                missions_with_failure += 1
                if "SUCCESSFUL_FIX" in ev_types:
                    missions_recovered += 1
                else:
                    # Check if mission ultimately succeeded
                    cursor.execute("SELECT status FROM missions WHERE mission_id = ?;", (m_id,))
                    row = cursor.fetchone()
                    if row and row["status"] == "COMPLETED":
                        missions_recovered += 1

        if missions_with_failure > 0:
            rec_rate = missions_recovered / missions_with_failure
            metrics["recovery_rate"] = MetricValue(
                "recovery_rate",
                round(rec_rate, 4),
                MetricStatus.DERIVED,
                unit="ratio",
                notes=f"{missions_recovered} recovered out of {missions_with_failure} failed missions",
            )
        else:
            metrics["recovery_rate"] = MetricValue("recovery_rate", None, MetricStatus.UNKNOWN, notes="No mission failures recorded")

        # 5. Retry Rate (DERIVED)
        # Retry rate = consecutive identical tool calls on the same turn or adjacent turns
        cursor.execute(
            f"""SELECT t.mission_id, tc.turn_id, tc.tool_name, tc.sanitized_args_json, tc.status 
               FROM tool_calls tc
               JOIN turns t ON tc.turn_id = t.turn_id
               WHERE t.mission_id IN (SELECT mission_id FROM missions {p_filter})
               ORDER BY tc.created_at ASC;""",
            p_param,
        )
        tool_rows = cursor.fetchall()
        retry_count = 0
        last_sig = None
        for tr in tool_rows:
            # Deterministic signature of tool and sanitized args
            sig = f"{tr['tool_name']}:{tr['sanitized_args_json']}"
            if sig == last_sig:
                retry_count += 1
            last_sig = sig

        if calls_cnt > 0:
            retry_rate = retry_count / calls_cnt
            metrics["retry_rate"] = MetricValue(
                "retry_rate",
                round(retry_rate, 4),
                MetricStatus.DERIVED,
                unit="ratio",
                notes=f"{retry_count} immediate retries out of {calls_cnt} calls",
            )
        else:
            metrics["retry_rate"] = MetricValue("retry_rate", None, MetricStatus.UNKNOWN, notes="No tool calls recorded")

        # 6. Verification Pass/Fail Rate (DERIVED)
        # Count TEST_RESULT events
        cursor.execute(
            f"""SELECT payload_json FROM engineering_events 
               WHERE event_type = 'TEST_RESULT' {'AND project_id = ?' if project_id else ''};""",
            p_param,
        )
        test_rows = cursor.fetchall()
        test_pass_cnt = 0
        test_total_cnt = len(test_rows)
        for tr in test_rows:
            try:
                pj = json.loads(tr["payload_json"])
                if pj.get("passed") is True or pj.get("exit_code") == 0:
                    test_pass_cnt += 1
            except Exception:
                pass

        if test_total_cnt > 0:
            metrics["verification_pass_rate"] = MetricValue(
                "verification_pass_rate",
                round(test_pass_cnt / test_total_cnt, 4),
                MetricStatus.DERIVED,
                unit="ratio",
                notes=f"{test_pass_cnt} passes out of {test_total_cnt} test runs",
            )
        else:
            metrics["verification_pass_rate"] = MetricValue("verification_pass_rate", None, MetricStatus.UNKNOWN, notes="No test execution events")

        # 7. Navigation Efficiency (DERIVED)
        # Ratio of unique file views to total view_file calls
        cursor.execute(
            f"""SELECT tc.sanitized_args_json FROM tool_calls tc
               JOIN turns t ON tc.turn_id = t.turn_id
               WHERE tc.tool_name = 'view_file' 
               AND t.mission_id IN (SELECT mission_id FROM missions {p_filter});""",
            p_param,
        )
        view_rows = cursor.fetchall()
        total_views = len(view_rows)
        if total_views > 0:
            viewed_paths: Set[str] = set()
            for vr in view_rows:
                try:
                    args = json.loads(vr["sanitized_args_json"])
                    p = args.get("AbsolutePath") or args.get("file_path") or args.get("path") or ""
                    if p:
                        viewed_paths.add(p)
                except Exception:
                    pass
            unique_views = len(viewed_paths)
            nav_eff = unique_views / total_views
            metrics["navigation_efficiency"] = MetricValue(
                "navigation_efficiency",
                round(nav_eff, 4),
                MetricStatus.DERIVED,
                unit="ratio",
                notes=f"{unique_views} unique targets viewed across {total_views} view operations",
            )
        else:
            metrics["navigation_efficiency"] = MetricValue("navigation_efficiency", None, MetricStatus.UNKNOWN, notes="No view_file calls recorded")

        # 8. Execution Timing (OBSERVED/DERIVED)
        cursor.execute(
            f"""SELECT avg(duration_ms) as avg_ms, max(duration_ms) as max_ms FROM tool_calls 
               WHERE duration_ms > 0 AND turn_id IN (
                   SELECT turn_id FROM turns WHERE mission_id IN (SELECT mission_id FROM missions {p_filter})
               );""",
            p_param,
        )
        t_row = cursor.fetchone()
        avg_call_ms = t_row["avg_ms"] if t_row and t_row["avg_ms"] else None
        if avg_call_ms is not None:
            metrics["avg_tool_duration_ms"] = MetricValue(
                "avg_tool_duration_ms",
                round(avg_call_ms, 1),
                MetricStatus.DERIVED,
                unit="ms",
                notes="Average execution duration for timed tool calls",
            )
        else:
            metrics["avg_tool_duration_ms"] = MetricValue("avg_tool_duration_ms", None, MetricStatus.UNKNOWN, notes="Timing data unrecorded")

        return metrics

    def _compute_failure_intelligence(
        self,
        conn: sqlite3.Connection,
        project_id: Optional[str],
    ) -> List[FailurePattern]:
        cursor = conn.cursor()
        p_filter = "AND e.project_id = ?" if project_id else ""
        p_param = (project_id,) if project_id else ()

        # Query events related to failures
        cursor.execute(
            f"""SELECT e.event_id, e.mission_id, e.project_id, e.event_type, e.affected_file, e.payload_json, e.created_at
               FROM engineering_events e
               WHERE e.event_type IN ('TOOL_FAILURE', 'TEST_FAILURE', 'REPEATED_NAVIGATION_PATH', 'STOP_GATE_RESULT')
               {p_filter}
               ORDER BY e.created_at ASC;""",
            p_param,
        )
        rows = cursor.fetchall()

        # Categorize patterns
        category_counts: Dict[str, int] = Counter()
        category_projects: Dict[str, Set[str]] = defaultdict(set)
        category_first: Dict[str, str] = {}
        category_last: Dict[str, str] = {}
        category_tools: Dict[str, Set[str]] = defaultdict(set)
        category_details: Dict[str, List[str]] = defaultdict(list)

        for r in rows:
            etype = r["event_type"]
            cat = etype
            tool = None
            try:
                pj = json.loads(r["payload_json"])
            except Exception:
                pj = {}

            if etype == "TOOL_FAILURE":
                cat = pj.get("error_category") or pj.get("exception_type") or "TOOL_ERROR"
                tool = pj.get("tool_name")
            elif etype == "TEST_FAILURE":
                cat = "VERIFICATION_TEST_FAILURE"
            elif etype == "REPEATED_NAVIGATION_PATH":
                cat = "REPEATED_NAVIGATION_FRICTION"
            elif etype == "STOP_GATE_RESULT":
                if pj.get("decision") == "continue":
                    cat = "STOP_GATE_VERIFICATION_REJECTION"
                else:
                    continue  # Passing stop gate is not a failure

            category_counts[cat] += 1
            category_projects[cat].add(r["project_id"])
            if tool:
                category_tools[cat].add(tool)

            ts = r["created_at"]
            if cat not in category_first:
                category_first[cat] = ts
            category_last[cat] = ts

            aff = r["affected_file"]
            if aff:
                category_details[cat].append(aff)

        # Also inspect tool_calls directly for status == ERROR / DENIED_BY_GUARD
        t_filter = "AND t.mission_id IN (SELECT mission_id FROM missions WHERE project_id = ?)" if project_id else ""
        cursor.execute(
            f"""SELECT tc.tool_name, tc.status, count(*) as cnt 
               FROM tool_calls tc
               JOIN turns t ON tc.turn_id = t.turn_id
               WHERE tc.status IN ('ERROR', 'DENIED_BY_GUARD', 'TIMED_OUT')
               {t_filter}
               GROUP BY tc.tool_name, tc.status;""",
            p_param,
        )
        for tr in cursor.fetchall():
            tool_cat = f"{tr['tool_name']}_{tr['status']}"
            category_counts[tool_cat] += tr["cnt"]
            category_tools[tool_cat].add(tr["tool_name"])

        # Compute recurrence ratios and assemble FailurePattern items
        total_fail_events = sum(category_counts.values()) or 1
        patterns: List[FailurePattern] = []

        for cat, cnt in category_counts.most_common(15):
            ratio = cnt / total_fail_events
            summary_desc = f"Observed {cnt} failure instance(s) under category '{cat}'."
            if category_tools[cat]:
                summary_desc += f" Correlated with tool(s): {', '.join(sorted(category_tools[cat]))}."

            patterns.append(
                FailurePattern(
                    category=cat,
                    occurrence_count=cnt,
                    affected_projects=list(category_projects[cat]),
                    first_seen=category_first.get(cat),
                    last_seen=category_last.get(cat),
                    related_tools=list(category_tools[cat]),
                    recurrence_ratio=ratio,
                    confidence="OBSERVED",
                    summary=summary_desc,
                )
            )

        return patterns

    def _compute_friction_patterns(
        self,
        conn: sqlite3.Connection,
        project_id: Optional[str],
    ) -> List[FrictionPattern]:
        cursor = conn.cursor()
        p_filter = "WHERE project_id = ?" if project_id else ""
        p_param = (project_id,) if project_id else ()

        friction_list: List[FrictionPattern] = []

        # 1. Repeated Navigation Friction (from REPEATED_NAVIGATION_PATH events)
        cursor.execute(
            f"""SELECT affected_file, payload_json, count(*) as cnt 
               FROM engineering_events 
               WHERE event_type = 'REPEATED_NAVIGATION_PATH' {'AND project_id = ?' if project_id else ''}
               GROUP BY affected_file;""",
            p_param,
        )
        rep_nav_rows = cursor.fetchall()
        total_rep_nav = sum(r["cnt"] for r in rep_nav_rows)
        if total_rep_nav > 0:
            targets = [r["affected_file"] for r in rep_nav_rows if r["affected_file"]]
            friction_list.append(
                FrictionPattern(
                    friction_type="REPEATED_NAVIGATION_INSPECTION",
                    occurrence_count=total_rep_nav,
                    description=f"Consecutive redundant file views observed {total_rep_nav} times across target components.",
                    affected_targets=targets,
                    confidence="OBSERVED",
                )
            )

        # 2. Search Thrashing before View
        # Detect sequences of 3+ grep/find calls before a view/edit in the same turn/mission
        cursor.execute(
            f"""SELECT t.mission_id, tc.turn_id, tc.tool_name, tc.created_at 
               FROM tool_calls tc
               JOIN turns t ON tc.turn_id = t.turn_id
               WHERE t.mission_id IN (SELECT mission_id FROM missions {p_filter})
               ORDER BY tc.created_at ASC;""",
            p_param,
        )
        search_thrash_count = 0
        consecutive_searches = 0
        for r in cursor.fetchall():
            if r["tool_name"] in ("grep_search", "find_by_name"):
                consecutive_searches += 1
            else:
                if consecutive_searches >= 3:
                    search_thrash_count += 1
                consecutive_searches = 0
        if consecutive_searches >= 3:
            search_thrash_count += 1

        if search_thrash_count > 0:
            friction_list.append(
                FrictionPattern(
                    friction_type="SEARCH_THRASHING_BEFORE_NAVIGATION",
                    occurrence_count=search_thrash_count,
                    description=f"Observed {search_thrash_count} clusters of 3+ consecutive search operations before navigating to files.",
                    affected_targets=["grep_search", "find_by_name"],
                    confidence="DERIVED",
                )
            )

        # 3. Tool Loop / Retry Friction
        cursor.execute(
            f"""SELECT tc.tool_name, tc.sanitized_args_json, count(*) as cnt 
               FROM tool_calls tc
               JOIN turns t ON tc.turn_id = t.turn_id
               WHERE t.mission_id IN (SELECT mission_id FROM missions {p_filter})
               GROUP BY tc.tool_name, tc.sanitized_args_json
               HAVING count(*) >= 3;""",
            p_param,
        )
        retry_loop_rows = cursor.fetchall()
        if retry_loop_rows:
            total_loops = sum(r["cnt"] for r in retry_loop_rows)
            loop_tools = list({r["tool_name"] for r in retry_loop_rows})
            friction_list.append(
                FrictionPattern(
                    friction_type="TOOL_RETRY_LOOP",
                    occurrence_count=total_loops,
                    description=f"Identified {len(retry_loop_rows)} tool configurations repeated 3 or more times ({total_loops} total calls).",
                    affected_targets=loop_tools,
                    confidence="DERIVED",
                )
            )

        # 4. Long Execution Paths (Trajectory Friction)
        cursor.execute(
            f"""SELECT m.mission_id, count(t.turn_id) as turn_cnt 
               FROM missions m
               JOIN turns t ON m.mission_id = t.mission_id
               { 'WHERE m.project_id = ?' if project_id else ''}
               GROUP BY m.mission_id
               HAVING turn_cnt > 10;""",
            p_param,
        )
        long_missions = cursor.fetchall()
        if long_missions:
            friction_list.append(
                FrictionPattern(
                    friction_type="HIGH_TURN_TRAJECTORY_LENGTH",
                    occurrence_count=len(long_missions),
                    description=f"{len(long_missions)} mission(s) required > 10 turns to reach completion or conclusion.",
                    affected_targets=[r["mission_id"] for r in long_missions],
                    confidence="OBSERVED",
                )
            )

        # 5. Verification Gap (Test failure followed by recovery)
        cursor.execute(
            f"""SELECT count(*) as cnt FROM engineering_events 
               WHERE event_type = 'SUCCESSFUL_FIX' {'AND project_id = ?' if project_id else ''};""",
            p_param,
        )
        fix_row = cursor.fetchone()
        fix_cnt = fix_row["cnt"] if fix_row else 0
        if fix_cnt > 0:
            friction_list.append(
                FrictionPattern(
                    friction_type="VERIFICATION_RECOVERY_CYCLE",
                    occurrence_count=fix_cnt,
                    description=f"{fix_cnt} test failure(s) successfully resolved through an engineering recovery cycle.",
                    affected_targets=["test_runner"],
                    confidence="OBSERVED",
                )
            )

        return friction_list

    def _compute_successful_strategies(
        self,
        conn: sqlite3.Connection,
        project_id: Optional[str],
    ) -> List[SuccessfulStrategy]:
        cursor = conn.cursor()
        p_filter = "AND m.project_id = ?" if project_id else ""
        p_param = (project_id,) if project_id else ()

        # Get completed missions
        cursor.execute(
            f"""SELECT m.mission_id, m.task_class, m.intent_query 
               FROM missions m
               WHERE m.status = 'COMPLETED' {p_filter};""",
            p_param,
        )
        completed_missions = cursor.fetchall()
        if not completed_missions:
            return []

        # For each completed mission, extract the primary ordered sequence of distinct tool invocations
        strategy_counts: Dict[Tuple[str, Tuple[str, ...]], int] = Counter()

        for cm in completed_missions:
            mid = cm["mission_id"]
            tclass = cm["task_class"] or "GENERAL_ENGINEERING"

            cursor.execute(
                """SELECT tc.tool_name FROM tool_calls tc
                   JOIN turns t ON tc.turn_id = t.turn_id
                   WHERE t.mission_id = ?
                   ORDER BY tc.created_at ASC;""",
                (mid,),
            )
            raw_tools = [r["tool_name"] for r in cursor.fetchall()]
            if not raw_tools:
                continue

            # Deduplicate adjacent tools to capture canonical stage sequence
            compressed_seq: List[str] = []
            for t in raw_tools:
                if not compressed_seq or compressed_seq[-1] != t:
                    compressed_seq.append(t)

            # Cap sequence length for bounded pattern representation
            bounded_seq = tuple(compressed_seq[:6])
            strategy_counts[(tclass, bounded_seq)] += 1

        strategies: List[SuccessfulStrategy] = []
        for (tclass, seq), count in strategy_counts.most_common(10):
            seq_display = " -> ".join(seq)
            strategies.append(
                SuccessfulStrategy(
                    task_category=tclass,
                    tool_sequence=list(seq),
                    occurrence_count=count,
                    success_rate=1.0,  # Grouped from completed missions
                    summary=f"Recurring trajectory for {tclass} tasks: {seq_display} ({count} successful missions).",
                )
            )

        return strategies

    def _compute_capability_stats(
        self,
        conn: sqlite3.Connection,
        project_id: Optional[str],
    ) -> List[CapabilityStats]:
        cursor = conn.cursor()
        p_filter = "WHERE t.mission_id IN (SELECT mission_id FROM missions WHERE project_id = ?)" if project_id else ""
        p_param = (project_id,) if project_id else ()

        cursor.execute(
            f"""SELECT tc.tool_name,
                      count(*) as total_cnt,
                      sum(CASE WHEN tc.status = 'SUCCESS' THEN 1 ELSE 0 END) as succ_cnt,
                      sum(CASE WHEN tc.status IN ('ERROR', 'DENIED_BY_GUARD', 'TIMED_OUT') THEN 1 ELSE 0 END) as err_cnt,
                      avg(CASE WHEN tc.duration_ms > 0 THEN tc.duration_ms ELSE NULL END) as avg_ms
               FROM tool_calls tc
               JOIN turns t ON tc.turn_id = t.turn_id
               {p_filter}
               GROUP BY tc.tool_name
               ORDER BY total_cnt DESC;""",
            p_param,
        )
        stats: List[CapabilityStats] = []
        for r in cursor.fetchall():
            tot = r["total_cnt"]
            err = r["err_cnt"] or 0
            succ = r["succ_cnt"] or 0
            rate = err / tot if tot > 0 else 0.0
            avg_dur = r["avg_ms"] or 0.0
            stats.append(
                CapabilityStats(
                    capability_name=r["tool_name"],
                    total_calls=tot,
                    success_calls=succ,
                    error_calls=err,
                    failure_rate=rate,
                    avg_duration_ms=avg_dur,
                )
            )
        return stats

    def _compute_subagent_stats(
        self,
        conn: sqlite3.Connection,
        project_id: Optional[str],
    ) -> SubagentStats:
        cursor = conn.cursor()
        p_filter = "WHERE t.mission_id IN (SELECT mission_id FROM missions WHERE project_id = ?)" if project_id else ""
        p_param = (project_id,) if project_id else ()

        cursor.execute(
            f"""SELECT t.agent_role, t.agent_conversation_id, count(*) as cnt 
               FROM turns t
               {p_filter}
               GROUP BY t.agent_role, t.agent_conversation_id;""",
            p_param,
        )
        rows = cursor.fetchall()
        role_counts: Dict[str, int] = Counter()
        conversations: Set[str] = set()
        subagent_turn_count = 0

        for r in rows:
            role = r["agent_role"]
            cnt = r["cnt"]
            role_counts[role] += cnt
            if r["agent_conversation_id"]:
                conversations.add(r["agent_conversation_id"])
            if role not in ("PrimaryEngineer", "User"):
                subagent_turn_count += cnt

        return SubagentStats(
            total_subagent_turns=subagent_turn_count,
            roles_observed=dict(role_counts),
            conversation_count=len(conversations),
        )

    def _compute_cross_project_summary(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) as cnt FROM projects;")
        total_projects = cursor.fetchone()["cnt"]

        cursor.execute(
            """SELECT p.project_id, count(m.mission_id) as mission_cnt
               FROM projects p
               LEFT JOIN missions m ON p.project_id = m.project_id
               GROUP BY p.project_id;"""
        )
        proj_missions = [r["mission_cnt"] for r in cursor.fetchall()]
        avg_missions = sum(proj_missions) / len(proj_missions) if proj_missions else 0.0

        return {
            "total_registered_projects": total_projects,
            "average_missions_per_project": round(avg_missions, 2),
            "privacy_boundary": "Cross-project metrics aggregate high-level volume and patterns; zero project source paths leaked.",
        }


class ExperienceExporter:
    """Exports structured Experience Intelligence to disk in JSON or Markdown format."""

    @staticmethod
    def export(
        report: ExperienceReport,
        output_path: Union[str, Path],
        export_format: str = "json",
    ) -> Path:
        target = Path(output_path).resolve()
        fmt = export_format.lower().strip()

        if target.is_dir() or target.suffix == "":
            target.mkdir(parents=True, exist_ok=True)
            scope_slug = f"project_{report.project_id}" if report.project_id else "global"
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            ext = "md" if fmt in ("markdown", "md") else "json"
            target = target / f"antios_experience_report_{scope_slug}_{timestamp}.{ext}"
        else:
            target.parent.mkdir(parents=True, exist_ok=True)

        if fmt in ("markdown", "md"):
            content = report.to_markdown()
        else:
            content = json.dumps(report.to_dict(), indent=2, sort_keys=True)

        with open(target, "w", encoding="utf-8") as f:
            f.write(content)

        return target
