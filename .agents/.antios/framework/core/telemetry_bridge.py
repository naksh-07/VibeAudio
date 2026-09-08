"""AntiOS 2.1 Local Engineering Intelligence — Antigravity Event Bridge.

Connects AntiOS to Antigravity runtime surfaces (hooks, append-only transcripts, CLI stream)
without reimplementing the Antigravity runtime, without background daemons (INV-15),
and without bypassing the Phase 104 Telemetry Sanitizer boundary.

Constitutional Invariants & Governance:
- PIPELINE: Antigravity -> Event Bridge -> Telemetry Sanitizer -> Safe Event -> Experience Store.
- ZERO BYPASS: No event reaches SQLite without passing through TelemetrySanitizer.
- COLLECTION MODES: OFF (default) and ON. Collection is explicit and non-invasive.
- FAIL-SAFE: Telemetry failure != engineering task failure. Telemetry errors never block execution.
- CHECKPOINTED & RESTART-SAFE: Incremental transcript ingestion using byte offsets and file signatures.
- DEDUPLICATION: Idempotent event ingestion via event signatures and call IDs.
- TENANT SCOPED: Every persisted record is strictly scoped to canonical project_id.
- INERT DATA: Telemetry remains passive observational data only.
- ZERO THIRD-PARTY DEPENDENCIES: Pure Python standard library only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from framework.core.experience import (
    AntiOSDataResolver,
    DataDirectoryNotConfiguredError,
    ExperienceRepository,
    IngestionCheckpoint,
    StorageContext,
    StorageError,
    register_project,
)
from framework.core.sanitizer import (
    PathClassification,
    SafeEngineeringEvent,
    SafeToolCall,
    SanitizerDecision,
    TelemetrySanitizer,
)

# Bridge version
TELEMETRY_BRIDGE_VERSION = "2.1.0"


# =====================================================================
# Collection Modes & Configuration
# =====================================================================

class TelemetryCollectionMode(str, Enum):
    """Telemetry collection state."""
    OFF = "OFF"
    ON = "ON"


@dataclass
class TelemetryConfig:
    """Configuration governing telemetry collection and ingestion limits."""
    mode: Optional[TelemetryCollectionMode] = None
    max_read_bytes_per_turn: int = 10 * 1024 * 1024  # 10 MB per read window
    max_steps_per_turn: int = 1000
    track_navigation_paths: bool = True
    deduplicate_events: bool = True


class TelemetryConfigResolver:
    """Authoritative resolver for telemetry collection mode and settings.
    
    Precedence:
    1. Explicit parameter passed to bridge
    2. Environment variable: ANTIOS_TELEMETRY_MODE ("ON" / "OFF")
       or ANTIOS_TELEMETRY_ENABLED ("1", "true", "yes", "on")
    3. Project configuration: antios.config.json -> telemetry.mode / telemetry.enabled
    4. Central data directory configuration: config.toml -> [telemetry] mode / enabled
    5. Default: OFF (strict fail-closed default)
    """

    @classmethod
    def resolve_mode(
        cls,
        project_root: Optional[Union[str, Path]] = None,
        explicit_mode: Optional[Union[str, TelemetryCollectionMode]] = None,
    ) -> TelemetryCollectionMode:
        """Resolves active telemetry collection mode following strict precedence."""
        # 1. Explicit argument
        if explicit_mode is not None:
            if isinstance(explicit_mode, TelemetryCollectionMode):
                return explicit_mode
            val = str(explicit_mode).strip().upper()
            if val in ("ON", "TRUE", "1", "YES", "ENABLED"):
                return TelemetryCollectionMode.ON
            return TelemetryCollectionMode.OFF

        # 2. Environment variables
        env_mode = os.environ.get("ANTIOS_TELEMETRY_MODE")
        if env_mode:
            val = env_mode.strip().upper()
            if val in ("ON", "TRUE", "1", "YES", "ENABLED"):
                return TelemetryCollectionMode.ON
            if val in ("OFF", "FALSE", "0", "NO", "DISABLED"):
                return TelemetryCollectionMode.OFF

        env_enabled = os.environ.get("ANTIOS_TELEMETRY_ENABLED")
        if env_enabled:
            val = env_enabled.strip().lower()
            if val in ("1", "true", "yes", "on"):
                return TelemetryCollectionMode.ON
            if val in ("0", "false", "no", "off"):
                return TelemetryCollectionMode.OFF

        # 3. Project configuration (antios.config.json)
        if project_root is not None:
            p_root = Path(project_root).resolve()
            config_file = p_root / "antios.config.json"
            if config_file.is_file():
                try:
                    with open(config_file, "r", encoding="utf-8-sig") as f:
                        data = json.load(f)
                        telem = data.get("telemetry", {})
                        if isinstance(telem, dict):
                            if "mode" in telem:
                                m_val = str(telem["mode"]).strip().upper()
                                return TelemetryCollectionMode.ON if m_val == "ON" else TelemetryCollectionMode.OFF
                            if "enabled" in telem:
                                return TelemetryCollectionMode.ON if bool(telem["enabled"]) else TelemetryCollectionMode.OFF
                        elif "telemetry_enabled" in data:
                            return TelemetryCollectionMode.ON if bool(data["telemetry_enabled"]) else TelemetryCollectionMode.OFF
                except Exception:
                    pass

        # 4. Data directory configuration (config.toml)
        try:
            data_dir = AntiOSDataResolver.resolve_data_dir(project_root=project_root)
            config_toml = data_dir / "config.toml"
            if config_toml.is_file():
                try:
                    content = config_toml.read_text(encoding="utf-8")
                    for line in content.splitlines():
                        line = line.strip()
                        if line.startswith("mode") and "=" in line:
                            val = line.split("=", 1)[1].strip().strip('"\'').upper()
                            return TelemetryCollectionMode.ON if val == "ON" else TelemetryCollectionMode.OFF
                        if line.startswith("enabled") and "=" in line:
                            val = line.split("=", 1)[1].strip().lower()
                            return TelemetryCollectionMode.ON if val in ("true", "1", "yes") else TelemetryCollectionMode.OFF
                except Exception:
                    pass
        except Exception:
            pass

        # 5. Fail-closed default: OFF
        return TelemetryCollectionMode.OFF


# =====================================================================
# Ingestion Result & Step Representation
# =====================================================================

@dataclass
class IngestionResult:
    """Detailed outcome of an ingestion operation."""
    success: bool
    mode: TelemetryCollectionMode
    session_id: Optional[str] = None
    project_id: Optional[str] = None
    events_ingested: int = 0
    tool_calls_ingested: int = 0
    turns_ingested: int = 0
    bytes_processed: int = 0
    checkpoint_offset: int = 0
    error: Optional[str] = None
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["mode"] = self.mode.value
        return res


@dataclass
class TranscriptStep:
    """Internal normalized representation of a single parsed line in transcript.jsonl."""
    step_index: int
    source: str  # USER_EXPLICIT, MODEL, SYSTEM
    step_type: str  # USER_INPUT, PLANNER_RESPONSE, GENERIC
    status: str  # DONE, ERROR
    created_at: str
    content: Optional[str] = None
    thinking: Optional[str] = None  # PROHIBITED FROM PERSISTENCE — dropped during sanitization
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    raw_json: str = ""


# =====================================================================
# Transcript Parser (Append-Only Incremental Reader)
# =====================================================================

class TranscriptParser:
    """Incremental, restart-safe reader for Antigravity transcript files.
    
    Guarantees:
    - Incremental read starting from byte offset.
    - Safe handling of incomplete/trailing lines (mid-stream writes).
    - Malformed JSONL line tolerance (skips bad line without crashing).
    - File truncation/replacement detection (resets offset if file size shrunk).
    - Bounded memory read ceiling.
    - Zero full-file reload on every event.
    """

    @staticmethod
    def compute_file_signature(path: Union[str, Path]) -> Tuple[str, int]:
        """Computes SHA-256 hash of the first 8KB and total file size."""
        p = Path(path).resolve()
        if not p.is_file():
            return "", 0
        size = p.stat().st_size
        try:
            with open(p, "rb") as f:
                header = f.read(8192)
                h = hashlib.sha256(header).hexdigest()
                return h, size
        except Exception:
            return "", size

    @classmethod
    def parse_incremental(
        cls,
        transcript_path: Union[str, Path],
        start_byte_offset: int = 0,
        max_bytes: int = 10 * 1024 * 1024,
        max_steps: int = 1000,
    ) -> Tuple[List[TranscriptStep], int, str, int]:
        """Parses newly appended steps from a transcript file.
        
        Returns:
            (steps, new_byte_offset, file_sha256, file_size)
        """
        p = Path(transcript_path).resolve()
        if not p.is_file():
            return [], 0, "", 0

        file_sig, file_size = cls.compute_file_signature(p)

        # File shrunk or replaced unexpectedly: reset to beginning
        offset = start_byte_offset
        if offset > file_size:
            offset = 0

        steps: List[TranscriptStep] = []
        new_offset = offset

        try:
            with open(p, "rb") as f:
                f.seek(offset)
                read_bytes = 0

                while read_bytes < max_bytes and len(steps) < max_steps:
                    line_start_pos = f.tell()
                    raw_line = f.readline()
                    if not raw_line:
                        # End of file reached
                        break

                    # Check if line has complete newline termination
                    # If not, file might be actively being written; leave unconsumed for next cycle
                    if not raw_line.endswith(b"\n") and not raw_line.endswith(b"\r"):
                        f.seek(line_start_pos)
                        break

                    read_bytes += len(raw_line)
                    new_offset = f.tell()

                    line_str = raw_line.decode("utf-8", errors="replace").strip()
                    if not line_str:
                        continue

                    # Strip UTF-8 BOM if at offset 0
                    if line_start_pos == 0 and line_str.startswith("\ufeff"):
                        line_str = line_str[1:]

                    try:
                        record = json.loads(line_str)
                        if not isinstance(record, dict):
                            continue

                        step = TranscriptStep(
                            step_index=record.get("step_index", len(steps)),
                            source=str(record.get("source", "UNKNOWN")),
                            step_type=str(record.get("type", "GENERIC")),
                            status=str(record.get("status", "DONE")),
                            created_at=str(record.get("created_at", "")),
                            content=record.get("content"),
                            thinking=record.get("thinking"),  # Will be dropped during normalization
                            tool_calls=record.get("tool_calls", []) if isinstance(record.get("tool_calls"), list) else [],
                            raw_json=line_str,
                        )
                        steps.append(step)
                    except json.JSONDecodeError:
                        # Malformed line: skip and advance offset
                        continue

        except Exception:
            return steps, new_offset, file_sig, file_size

        return steps, new_offset, file_sig, file_size


# =====================================================================
# Event Normalizer (Platform -> Safe Contracts via Sanitizer)
# =====================================================================

class EventNormalizer:
    """Normalizes Antigravity transcript steps into canonical SafeToolCall
    and SafeEngineeringEvent records passing strictly through TelemetrySanitizer.
    """

    # Test runner command patterns for detecting TEST_RESULT facts
    _TEST_RUNNER_PATTERNS = [
        re.compile(r"\bpytest\b", re.IGNORECASE),
        re.compile(r"\bpython\s+-m\s+unittest\b", re.IGNORECASE),
        re.compile(r"\bpython\s+tests[\\/]run_all\.py\b", re.IGNORECASE),
        re.compile(r"\bnpm\s+test\b", re.IGNORECASE),
        re.compile(r"\bcargo\s+test\b", re.IGNORECASE),
        re.compile(r"\bgo\s+test\b", re.IGNORECASE),
        re.compile(r"\bscripts[\\/]test\.(?:bat|sh)\b", re.IGNORECASE),
    ]

    def __init__(self, project_root: Union[str, Path]):
        self.project_root = Path(project_root).resolve()
        self._prior_test_failed: bool = False
        self._last_viewed_files: List[str] = []

    def normalize_trajectory(
        self,
        steps: List[TranscriptStep],
        session_id: str,
        project_id: str,
        mission_id: str,
    ) -> Tuple[List[SafeToolCall], List[SafeEngineeringEvent]]:
        """Transforms a sequence of parsed steps into sanitized tool calls and events."""
        safe_tool_calls: List[SafeToolCall] = []
        safe_events: List[SafeEngineeringEvent] = []

        # Map steps by index for fast lookup of outputs
        steps_by_idx: Dict[int, TranscriptStep] = {s.step_index: s for s in steps}

        for i, step in enumerate(steps):
            turn_id = f"turn_{session_id}_{step.step_index}"

            # -------------------------------------------------------------
            # 1. USER_INPUT Normalization (Raw prompt dropped, intent extracted)
            # -------------------------------------------------------------
            if step.step_type == "USER_INPUT" and step.content:
                norm_intent = TelemetrySanitizer.normalize_intent(step.content)
                intent_sig = hashlib.sha256(
                    f"{project_id}|{mission_id}|{step.step_index}|{norm_intent.get('task_category')}".encode("utf-8")
                ).hexdigest()[:16]

                ev = SafeEngineeringEvent(
                    event_id=f"evt_{intent_sig}",
                    mission_id=mission_id,
                    project_id=project_id,
                    event_type="MISSION_START" if i == 0 else "TURN",
                    epistemic_grade="FACT",
                    event_signature=intent_sig,
                    payload_json=json.dumps(norm_intent),
                    created_at=step.created_at or datetime.now(timezone.utc).isoformat(),
                    session_id=session_id,
                    turn_id=turn_id,
                    normalized_intent=norm_intent.get("normalized_intent"),
                )
                safe_events.append(ev)

                # Check if prompt represents a USER_CORRECTION following previous failure
                if self._prior_test_failed or (i > 0 and steps[i - 1].status == "ERROR"):
                    corr_sig = hashlib.sha256(f"user_corr|{project_id}|{step.step_index}".encode("utf-8")).hexdigest()[:16]
                    safe_events.append(
                        SafeEngineeringEvent(
                            event_id=f"evt_{corr_sig}",
                            mission_id=mission_id,
                            project_id=project_id,
                            event_type="USER_CORRECTION",
                            epistemic_grade="FACT",
                            event_signature=corr_sig,
                            payload_json=json.dumps({"correction_step": step.step_index, "task_category": norm_intent.get("task_category")}),
                            created_at=step.created_at or datetime.now(timezone.utc).isoformat(),
                            session_id=session_id,
                            turn_id=turn_id,
                        )
                    )

            # -------------------------------------------------------------
            # 2. PLANNER_RESPONSE Normalization (Tool calls)
            # -------------------------------------------------------------
            elif step.step_type == "PLANNER_RESPONSE":
                # Raw chain-of-thought is categorically dropped (step.thinking is NOT used)
                for call_idx, raw_call in enumerate(step.tool_calls):
                    tool_name = raw_call.get("name", "unknown_tool")
                    raw_args = raw_call.get("args", {})
                    call_id = f"call_{turn_id}_{call_idx}"

                    # Pair tool call with next step output if available
                    output_content: Optional[str] = None
                    tool_exit_code: Optional[int] = None
                    tool_status = "SUCCESS" if step.status == "DONE" else "ERROR"

                    # Look ahead for matching output step (usually step_index + 1)
                    next_step = steps_by_idx.get(step.step_index + 1)
                    if next_step and next_step.content:
                        output_content = next_step.content
                        if next_step.status == "ERROR":
                            tool_status = "ERROR"

                    # Extract exit code for run_command if present in output or status
                    if tool_name == "run_command" and output_content:
                        code_match = re.search(r"exited with code\s+(-?\d+)", output_content)
                        if code_match:
                            try:
                                tool_exit_code = int(code_match.group(1))
                                if tool_exit_code != 0:
                                    tool_status = "ERROR"
                            except Exception:
                                pass

                    # Pass through TelemetrySanitizer (Mandatory Phase 104 Boundary)
                    safe_tc = TelemetrySanitizer.sanitize_tool_call(
                        call_id=call_id,
                        turn_id=turn_id,
                        tool_name=tool_name,
                        raw_args=raw_args,
                        project_root=self.project_root,
                        raw_output=output_content,
                        exit_code=tool_exit_code,
                        status=tool_status,
                        created_at=step.created_at or datetime.now(timezone.utc).isoformat(),
                    )
                    safe_tool_calls.append(safe_tc)

                    # Derive canonical engineering events from tool execution facts
                    self._extract_tool_events(
                        safe_tc=safe_tc,
                        raw_args=raw_args,
                        session_id=session_id,
                        project_id=project_id,
                        mission_id=mission_id,
                        turn_id=turn_id,
                        output_content=output_content,
                        safe_events=safe_events,
                    )

            # -------------------------------------------------------------
            # 3. GENERIC Step Error Normalization
            # -------------------------------------------------------------
            elif step.status == "ERROR":
                err_sig = hashlib.sha256(f"err|{project_id}|{step.step_index}".encode("utf-8")).hexdigest()[:16]
                san_err = TelemetrySanitizer.sanitize_error(step.content or "Unknown runtime step error", self.project_root)
                safe_events.append(
                    SafeEngineeringEvent(
                        event_id=f"evt_{err_sig}",
                        mission_id=mission_id,
                        project_id=project_id,
                        event_type="TOOL_FAILURE",
                        epistemic_grade="FACT",
                        event_signature=err_sig,
                        payload_json=json.dumps(san_err),
                        created_at=step.created_at or datetime.now(timezone.utc).isoformat(),
                        session_id=session_id,
                        turn_id=turn_id,
                        error_category=san_err.get("error_category"),
                    )
                )

        return safe_tool_calls, safe_events

    def _extract_tool_events(
        self,
        safe_tc: SafeToolCall,
        raw_args: Dict[str, Any],
        session_id: str,
        project_id: str,
        mission_id: str,
        turn_id: str,
        output_content: Optional[str],
        safe_events: List[SafeEngineeringEvent],
    ) -> None:
        """Derives structured events (TEST_RESULT, ARTIFACT_CHANGE, TOOL_FAILURE) from tool call."""
        # A. Tool Call event
        tc_sig = hashlib.sha256(f"tc|{project_id}|{safe_tc.call_id}|{safe_tc.tool_name}".encode("utf-8")).hexdigest()[:16]
        safe_events.append(
            SafeEngineeringEvent(
                event_id=f"evt_{tc_sig}",
                mission_id=mission_id,
                project_id=project_id,
                event_type="TOOL_CALL",
                epistemic_grade="FACT",
                event_signature=tc_sig,
                payload_json=json.dumps({"tool_name": safe_tc.tool_name, "status": safe_tc.status}),
                created_at=safe_tc.created_at,
                session_id=session_id,
                turn_id=turn_id,
                outcome=safe_tc.status,
                exit_code=safe_tc.exit_code,
            )
        )

        # B. Tool Failure
        if safe_tc.status == "ERROR" or (safe_tc.exit_code is not None and safe_tc.exit_code != 0):
            fail_sig = hashlib.sha256(f"fail|{project_id}|{safe_tc.call_id}".encode("utf-8")).hexdigest()[:16]
            san_err = TelemetrySanitizer.sanitize_error(output_content or "Tool execution failed", self.project_root)
            safe_events.append(
                SafeEngineeringEvent(
                    event_id=f"evt_{fail_sig}",
                    mission_id=mission_id,
                    project_id=project_id,
                    event_type="TOOL_FAILURE",
                    epistemic_grade="FACT",
                    event_signature=fail_sig,
                    payload_json=json.dumps(san_err),
                    created_at=safe_tc.created_at,
                    session_id=session_id,
                    turn_id=turn_id,
                    error_category=san_err.get("error_category"),
                    exit_code=safe_tc.exit_code,
                )
            )

        # C. Test Runner Execution (TEST_RESULT, TEST_FAILURE, SUCCESSFUL_FIX)
        if safe_tc.tool_name == "run_command":
            cmd = str(raw_args.get("CommandLine", "") or raw_args.get("command", ""))
            is_test_run = any(pat.search(cmd) for pat in self._TEST_RUNNER_PATTERNS)

            if is_test_run:
                exit_zero = safe_tc.exit_code == 0
                test_sig = hashlib.sha256(f"test|{project_id}|{safe_tc.call_id}|{exit_zero}".encode("utf-8")).hexdigest()[:16]

                safe_events.append(
                    SafeEngineeringEvent(
                        event_id=f"evt_{test_sig}",
                        mission_id=mission_id,
                        project_id=project_id,
                        event_type="TEST_RESULT",
                        epistemic_grade="FACT",
                        event_signature=test_sig,
                        payload_json=json.dumps({
                            "exit_code": safe_tc.exit_code,
                            "passed": exit_zero,
                            "summary": safe_tc.output_summary,
                        }),
                        created_at=safe_tc.created_at,
                        session_id=session_id,
                        turn_id=turn_id,
                        outcome="PASS" if exit_zero else "FAIL",
                        exit_code=safe_tc.exit_code,
                    )
                )

                if not exit_zero:
                    self._prior_test_failed = True
                    tf_sig = hashlib.sha256(f"tf|{project_id}|{safe_tc.call_id}".encode("utf-8")).hexdigest()[:16]
                    safe_events.append(
                        SafeEngineeringEvent(
                            event_id=f"evt_{tf_sig}",
                            mission_id=mission_id,
                            project_id=project_id,
                            event_type="TEST_FAILURE",
                            epistemic_grade="FACT",
                            event_signature=tf_sig,
                            payload_json=json.dumps({"exit_code": safe_tc.exit_code, "output_sha256": safe_tc.output_sha256}),
                            created_at=safe_tc.created_at,
                            session_id=session_id,
                            turn_id=turn_id,
                            exit_code=safe_tc.exit_code,
                        )
                    )
                elif self._prior_test_failed and exit_zero:
                    # Previous test failure was followed by verified passing test -> SUCCESSFUL_FIX
                    fix_sig = hashlib.sha256(f"fix|{project_id}|{safe_tc.call_id}".encode("utf-8")).hexdigest()[:16]
                    safe_events.append(
                        SafeEngineeringEvent(
                            event_id=f"evt_{fix_sig}",
                            mission_id=mission_id,
                            project_id=project_id,
                            event_type="SUCCESSFUL_FIX",
                            epistemic_grade="FACT",
                            event_signature=fix_sig,
                            payload_json=json.dumps({"exit_code": 0, "previous_failure_resolved": True}),
                            created_at=safe_tc.created_at,
                            session_id=session_id,
                            turn_id=turn_id,
                            outcome="SUCCESS",
                        )
                    )
                    self._prior_test_failed = False

        # D. Artifact / Code Modification (ARTIFACT_CHANGE)
        if safe_tc.tool_name in ("write_to_file", "replace_file_content"):
            target_path = raw_args.get("TargetFile") or raw_args.get("path")
            if target_path:
                cls_res, rel_path = TelemetrySanitizer.classify_path(str(target_path), self.project_root)
                if cls_res == PathClassification.SAFE_PROJECT_PATH and rel_path:
                    change_sig = hashlib.sha256(f"art_change|{project_id}|{rel_path}|{safe_tc.call_id}".encode("utf-8")).hexdigest()[:16]
                    safe_events.append(
                        SafeEngineeringEvent(
                            event_id=f"evt_{change_sig}",
                            mission_id=mission_id,
                            project_id=project_id,
                            event_type="ARTIFACT_CHANGE",
                            epistemic_grade="FACT",
                            affected_file=rel_path,
                            event_signature=change_sig,
                            payload_json=json.dumps({"tool": safe_tc.tool_name, "file": rel_path}),
                            created_at=safe_tc.created_at,
                            session_id=session_id,
                            turn_id=turn_id,
                            relative_files=[rel_path],
                        )
                    )

        # E. File Inspection Tracking (REPEATED_NAVIGATION_PATH)
        if safe_tc.tool_name == "view_file":
            target_path = raw_args.get("AbsolutePath") or raw_args.get("path")
            if target_path:
                cls_res, rel_path = TelemetrySanitizer.classify_path(str(target_path), self.project_root)
                if cls_res == PathClassification.SAFE_PROJECT_PATH and rel_path:
                    self._last_viewed_files.append(rel_path)
                    if len(self._last_viewed_files) >= 2:
                        if self._last_viewed_files[-1] == self._last_viewed_files[-2]:
                            rep_sig = hashlib.sha256(f"rep_nav|{project_id}|{rel_path}|{turn_id}".encode("utf-8")).hexdigest()[:16]
                            safe_events.append(
                                SafeEngineeringEvent(
                                    event_id=f"evt_{rep_sig}",
                                    mission_id=mission_id,
                                    project_id=project_id,
                                    event_type="REPEATED_NAVIGATION_PATH",
                                    epistemic_grade="FACT",
                                    affected_file=rel_path,
                                    event_signature=rep_sig,
                                    payload_json=json.dumps({"repeated_file": rel_path, "consecutive_views": 2}),
                                    created_at=safe_tc.created_at,
                                    session_id=session_id,
                                    turn_id=turn_id,
                                )
                            )


# =====================================================================
# Antigravity Event Bridge (Ingestion Coordinator)
# =====================================================================

class AntigravityEventBridge:
    """Production-grade Antigravity Event Bridge & Experience Ingestion Coordinator.
    
    Responsibilities:
    1. Receive hook payloads, transcript paths, or CLI streaming events.
    2. Enforce explicit telemetry collection mode (OFF by default).
    3. Checkpoint incremental ingestion positions (byte offset, step index).
    4. Parse NDJSON transcripts safely with malformed-line and truncation tolerance.
    5. Pass all perceptions through TelemetrySanitizer (Phase 104 security boundary).
    6. Persist structured SafeToolCall and SafeEngineeringEvent records to Experience Store (Phase 103).
    7. Guarantee fail-safe non-blocking execution: Telemetry failures never break the host task.
    """

    def __init__(
        self,
        project_root: Optional[Union[str, Path]] = None,
        data_dir: Optional[Union[str, Path]] = None,
        config: Optional[TelemetryConfig] = None,
        timeout: float = 5.0,
        project_id: Optional[str] = None,
        mode: Optional[Union[str, TelemetryCollectionMode]] = None,
    ):
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.explicit_data_dir = Path(data_dir).resolve() if data_dir else None
        self.config = config or TelemetryConfig()
        if mode is not None:
            self.config.mode = TelemetryConfigResolver.resolve_mode(explicit_mode=mode)
        self.timeout = timeout

        # Resolve project identity deterministically
        resolved_id, self.project_name = AntiOSDataResolver.resolve_project_identity(self.project_root)
        self.project_id = project_id or resolved_id

    def is_enabled(self) -> bool:
        """Returns True if telemetry collection is currently active."""
        mode = TelemetryConfigResolver.resolve_mode(
            project_root=self.project_root,
            explicit_mode=self.config.mode,
        )
        return mode == TelemetryCollectionMode.ON

    def ingest_transcript(
        self,
        transcript_path: Union[str, Path],
        session_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        surface: str = "DESKTOP",
    ) -> IngestionResult:
        """Ingests new content from an Antigravity transcript file incrementally.
        
        Guarantees:
        - If collection mode is OFF, returns immediately (~0ms).
        - If data directory is unconfigured, returns clean diagnostic without crashing.
        - Failures are captured in IngestionResult and never raised.
        """
        start_time = time.perf_counter()
        mode = TelemetryConfigResolver.resolve_mode(
            project_root=self.project_root,
            explicit_mode=self.config.mode,
        )

        if mode != TelemetryCollectionMode.ON:
            return IngestionResult(
                success=True,
                mode=TelemetryCollectionMode.OFF,
                session_id=session_id,
                project_id=self.project_id,
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )

        t_path = Path(transcript_path).resolve()
        if not t_path.is_file():
            return IngestionResult(
                success=False,
                mode=mode,
                session_id=session_id,
                project_id=self.project_id,
                error=f"Transcript file not found: {t_path}",
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )

        # Resolve session ID: use parameter, or extract from path (e.g. brain/<session_id>/...)
        resolved_session_id = session_id
        if not resolved_session_id:
            resolved_session_id = self._extract_session_id_from_path(t_path)
        if not resolved_session_id:
            resolved_session_id = f"sess_{hashlib.sha256(str(t_path).encode('utf-8')).hexdigest()[:16]}"

        resolved_mission_id = mission_id or f"m_{resolved_session_id[:12]}"

        # Resolve storage repository
        try:
            context = AntiOSDataResolver.resolve_context(
                project_root=self.project_root,
                explicit_dir=self.explicit_data_dir,
            )
            repo = ExperienceRepository(context.db_path, timeout=self.timeout)
            self.project_id = register_project(
                db_path=context.db_path,
                project_root=self.project_root,
                project_id=self.project_id,
            )
        except DataDirectoryNotConfiguredError as e:
            return IngestionResult(
                success=False,
                mode=mode,
                session_id=resolved_session_id,
                project_id=self.project_id,
                error=str(e),
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )
        except Exception as e:
            return IngestionResult(
                success=False,
                mode=mode,
                session_id=resolved_session_id,
                project_id=self.project_id,
                error=f"Storage resolution error: {e}",
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )

        # Load checkpoint
        source_type = "transcript_full_jsonl" if "transcript_full" in t_path.name else "transcript_jsonl"
        checkpoint = repo.load_session_checkpoint(resolved_session_id, source_type=source_type)
        last_offset = checkpoint.last_byte_offset if checkpoint else 0

        # Incremental parse
        steps, new_offset, file_sha, file_size = TranscriptParser.parse_incremental(
            transcript_path=t_path,
            start_byte_offset=last_offset,
            max_bytes=self.config.max_read_bytes_per_turn,
            max_steps=self.config.max_steps_per_turn,
        )

        if not steps:
            return IngestionResult(
                success=True,
                mode=mode,
                session_id=resolved_session_id,
                project_id=self.project_id,
                checkpoint_offset=new_offset,
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )

        # Normalize and sanitize steps
        try:
            normalizer = EventNormalizer(self.project_root)
            safe_tool_calls, safe_events = normalizer.normalize_trajectory(
                steps=steps,
                session_id=resolved_session_id,
                project_id=self.project_id,
                mission_id=resolved_mission_id,
            )

            # Record session and mission headers
            repo.record_session(
                session_id=resolved_session_id,
                project_id=self.project_id,
                surface=surface,
                total_turns=len(steps),
            )
            repo.record_mission(
                mission_id=resolved_mission_id,
                session_id=resolved_session_id,
                project_id=self.project_id,
                status="ACTIVE",
            )

            # Record turns
            for step in steps:
                turn_id = f"turn_{resolved_session_id}_{step.step_index}"
                repo.record_turn(
                    turn_id=turn_id,
                    mission_id=resolved_mission_id,
                    step_idx=step.step_index,
                    agent_role="PrimaryEngineer" if step.source == "MODEL" else "User",
                    created_at=step.created_at,
                )

            # Record tool calls
            tc_inserted = repo.record_tool_calls(safe_tool_calls)

            # Record engineering events with deduplication
            ev_inserted = repo.record_engineering_events(safe_events)

            # Save updated checkpoint
            max_step_idx = max((s.step_index for s in steps), default=-1)
            checkpoint_id = f"chk_{resolved_session_id}_{source_type}"
            updated_checkpoint = IngestionCheckpoint(
                checkpoint_id=checkpoint_id,
                project_id=self.project_id,
                session_id=resolved_session_id,
                source_type=source_type,
                source_path=str(t_path),
                last_byte_offset=new_offset,
                last_step_idx=max_step_idx,
                file_sha256=file_sha,
                file_size_bytes=file_size,
                records_ingested=(checkpoint.records_ingested if checkpoint else 0) + len(steps),
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            repo.save_checkpoint(updated_checkpoint)

            return IngestionResult(
                success=True,
                mode=mode,
                session_id=resolved_session_id,
                project_id=self.project_id,
                events_ingested=ev_inserted,
                tool_calls_ingested=tc_inserted,
                turns_ingested=len(steps),
                bytes_processed=new_offset - last_offset if new_offset >= last_offset else new_offset,
                checkpoint_offset=new_offset,
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )

        except Exception as e:
            # Telemetry failure MUST NOT fail engineering execution
            return IngestionResult(
                success=False,
                mode=mode,
                session_id=resolved_session_id,
                project_id=self.project_id,
                error=f"Ingestion persistence error: {e}",
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )

    def ingest_ndjson_telemetry(
        self,
        ndjson_path: Optional[Union[str, Path]] = None,
        session_id: Optional[str] = None,
    ) -> IngestionResult:
        """Ingests events from .agents/telemetry.ndjson incrementally into experience.db.

        Guarantees:
        - If collection mode is OFF, returns immediately (~0ms).
        - Checkpointed by byte offset (source_type="telemetry_ndjson").
        - Strictly non-blocking: Never raises exceptions.
        """
        start_time = time.perf_counter()
        mode = TelemetryConfigResolver.resolve_mode(
            project_root=self.project_root,
            explicit_mode=self.config.mode,
        )

        if mode != TelemetryCollectionMode.ON:
            return IngestionResult(
                success=True,
                mode=TelemetryCollectionMode.OFF,
                session_id=session_id,
                project_id=self.project_id,
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )

        resolved_path = Path(ndjson_path).resolve() if ndjson_path else self.project_root / ".agents" / "telemetry.ndjson"
        if not resolved_path.is_file():
            return IngestionResult(
                success=True,
                mode=mode,
                session_id=session_id,
                project_id=self.project_id,
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )

        try:
            context = AntiOSDataResolver.resolve_context(
                project_root=self.project_root,
                explicit_dir=self.explicit_data_dir,
            )
            repo = ExperienceRepository(context.db_path, timeout=self.timeout)
            self.project_id = register_project(
                db_path=context.db_path,
                project_root=self.project_root,
                project_id=self.project_id,
            )

            resolved_sess = session_id or f"ndjson_{self.project_id[:12]}"
            source_type = "telemetry_ndjson"
            checkpoint = repo.load_session_checkpoint(resolved_sess, source_type=source_type)
            last_offset = checkpoint.last_byte_offset if checkpoint else 0

            file_size = resolved_path.stat().st_size
            if last_offset > file_size:
                last_offset = 0

            safe_events: List[SafeEngineeringEvent] = []
            new_offset = last_offset
            mission_id = f"m_{resolved_sess[:12]}"

            with open(resolved_path, "rb") as f:
                f.seek(last_offset)
                while True:
                    line_start = f.tell()
                    raw_line = f.readline()
                    if not raw_line:
                        break
                    if not raw_line.endswith(b"\n") and not raw_line.endswith(b"\r"):
                        # Incomplete line mid-write
                        f.seek(line_start)
                        break
                    new_offset = f.tell()
                    line_str = raw_line.decode("utf-8", errors="replace").strip()
                    if not line_str:
                        continue
                    try:
                        record = json.loads(line_str)
                        if not isinstance(record, dict):
                            continue
                        event_name = str(record.get("event", "UNKNOWN_EVENT"))
                        ts = record.get("timestamp") or datetime.now(timezone.utc).isoformat()
                        sig = hashlib.sha256(f"ndjson|{self.project_id}|{line_str}".encode("utf-8")).hexdigest()[:16]

                        # Classify event
                        epistemic = "FACT"
                        event_type = "HOOK_DECISION"
                        if event_name in ("stop", "Stop"):
                            event_type = "STOP_GATE_RESULT"
                        elif event_name in ("post_tool_use", "tool_call"):
                            event_type = "TOOL_CALL"
                        elif event_name in ("pre_invocation",):
                            event_type = "TURN_CONTEXT"

                        # Sanitize metadata payload
                        san_meta, _ = TelemetrySanitizer.sanitize_text(
                            json.dumps(record.get("metadata", record)),
                            max_length=2000,
                        )

                        ev = SafeEngineeringEvent(
                            event_id=f"evt_{sig}",
                            mission_id=mission_id,
                            project_id=self.project_id,
                            event_type=event_type,
                            epistemic_grade=epistemic,
                            event_signature=sig,
                            payload_json=san_meta,
                            created_at=ts,
                            session_id=resolved_sess,
                            outcome=record.get("decision"),
                        )
                        safe_events.append(ev)
                    except json.JSONDecodeError:
                        continue

            events_inserted = 0
            if safe_events:
                repo.record_session(resolved_sess, self.project_id, surface="NDJSON_HOOKS")
                repo.record_mission(mission_id, resolved_sess, self.project_id)
                events_inserted = repo.record_engineering_events(safe_events)

            # Update checkpoint
            header_sha = hashlib.sha256(str(file_size).encode("utf-8")).hexdigest()
            updated_checkpoint = IngestionCheckpoint(
                checkpoint_id=f"chk_{resolved_sess}_{source_type}",
                project_id=self.project_id,
                session_id=resolved_sess,
                source_type=source_type,
                source_path=str(resolved_path),
                last_byte_offset=new_offset,
                last_step_idx=0,
                file_sha256=header_sha,
                file_size_bytes=file_size,
                records_ingested=(checkpoint.records_ingested if checkpoint else 0) + len(safe_events),
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            repo.save_checkpoint(updated_checkpoint)

            return IngestionResult(
                success=True,
                mode=mode,
                session_id=resolved_sess,
                project_id=self.project_id,
                events_ingested=events_inserted,
                bytes_processed=new_offset - last_offset if new_offset >= last_offset else new_offset,
                checkpoint_offset=new_offset,
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )
        except Exception as e:
            return IngestionResult(
                success=False,
                mode=mode,
                error=f"NDJSON ingestion error: {e}",
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )

    def ingest_from_hook_payload(
        self,
        payload: Dict[str, Any],
        hook_type: str = "Stop",
        stop_gate_decision: Optional[str] = None,
        stop_gate_reason: Optional[str] = None,
    ) -> IngestionResult:
        """Ingests telemetry from an Antigravity lifecycle hook payload on stdin.
        
        Expected payload fields:
        - conversationId (str)
        - workspacePaths (list of str)
        - transcriptPath (str, optional)
        - modelName (str, optional)
        """
        start_time = time.perf_counter()
        mode = TelemetryConfigResolver.resolve_mode(
            project_root=self.project_root,
            explicit_mode=self.config.mode,
        )

        if mode != TelemetryCollectionMode.ON:
            return IngestionResult(
                success=True,
                mode=TelemetryCollectionMode.OFF,
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )

        try:
            conv_id = str(payload.get("conversationId", "") or payload.get("conversation_id", ""))
            transcript_path = payload.get("transcriptPath") or payload.get("transcript_path")
            workspace_paths = payload.get("workspacePaths") or payload.get("workspace_paths") or []

            # If workspace path is provided and different from current, adapt
            if workspace_paths and isinstance(workspace_paths, list):
                first_ws = Path(workspace_paths[0]).resolve()
                if first_ws.is_dir() and first_ws != self.project_root:
                    self.project_root = first_ws
                    self.project_id, self.project_name = AntiOSDataResolver.resolve_project_identity(self.project_root)

            # If transcript path is provided and file exists, perform incremental transcript ingestion
            result: Optional[IngestionResult] = None
            if transcript_path and Path(transcript_path).is_file():
                result = self.ingest_transcript(transcript_path, session_id=conv_id)

            # If this is a Stop hook, also record the stop gate outcome event
            if hook_type == "Stop" and stop_gate_decision:
                self._record_stop_gate_event(
                    conversation_id=conv_id,
                    decision=stop_gate_decision,
                    reason=stop_gate_reason,
                )

            if result:
                return result

            return IngestionResult(
                success=True,
                mode=mode,
                session_id=conv_id,
                project_id=self.project_id,
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )

        except Exception as e:
            # Telemetry failure must degrade telemetry, not engineering execution
            return IngestionResult(
                success=False,
                mode=mode,
                error=f"Hook ingestion error: {e}",
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )

    def ingest_cli_event(
        self,
        event_dict: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> IngestionResult:
        """Adapts and ingests a CLI stream-json NDJSON event."""
        start_time = time.perf_counter()
        mode = TelemetryConfigResolver.resolve_mode(
            project_root=self.project_root,
            explicit_mode=self.config.mode,
        )

        if mode != TelemetryCollectionMode.ON:
            return IngestionResult(
                success=True,
                mode=TelemetryCollectionMode.OFF,
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )

        try:
            context = AntiOSDataResolver.resolve_context(
                project_root=self.project_root,
                explicit_dir=self.explicit_data_dir,
            )
            repo = ExperienceRepository(context.db_path, timeout=self.timeout)
            self.project_id = register_project(
                db_path=context.db_path,
                project_root=self.project_root,
                project_id=self.project_id,
            )
            sess_id = session_id or str(event_dict.get("session_id", "cli_session"))
            mission_id = f"m_{sess_id[:12]}"

            event_type = str(event_dict.get("type", "CLI_EVENT"))
            now_utc = datetime.now(timezone.utc).isoformat()

            # Pass payload through TelemetrySanitizer
            san_text, _ = TelemetrySanitizer.sanitize_text(json.dumps(event_dict), max_length=1000)
            cli_sig = hashlib.sha256(f"cli|{self.project_id}|{sess_id}|{now_utc}|{event_type}".encode("utf-8")).hexdigest()[:16]

            ev = SafeEngineeringEvent(
                event_id=f"evt_{cli_sig}",
                mission_id=mission_id,
                project_id=self.project_id,
                event_type=event_type,
                epistemic_grade="FACT",
                event_signature=cli_sig,
                payload_json=san_text,
                created_at=now_utc,
                session_id=sess_id,
            )

            repo.record_session(sess_id, self.project_id, surface="CLI_HEADLESS")
            repo.record_mission(mission_id, sess_id, self.project_id)
            inserted = repo.record_engineering_event(ev)

            return IngestionResult(
                success=True,
                mode=mode,
                session_id=sess_id,
                project_id=self.project_id,
                events_ingested=1 if inserted else 0,
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )

        except Exception as e:
            return IngestionResult(
                success=False,
                mode=mode,
                error=f"CLI ingestion error: {e}",
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )

    def _record_stop_gate_event(
        self,
        conversation_id: str,
        decision: str,
        reason: Optional[str],
    ) -> None:
        """Records a STOP_GATE_RESULT event into the database safely."""
        try:
            context = AntiOSDataResolver.resolve_context(
                project_root=self.project_root,
                explicit_dir=self.explicit_data_dir,
            )
            repo = ExperienceRepository(context.db_path, timeout=self.timeout)
            self.project_id = register_project(
                db_path=context.db_path,
                project_root=self.project_root,
                project_id=self.project_id,
            )
            sess_id = conversation_id or "stop_gate_session"
            mission_id = f"m_{sess_id[:12]}"
            now_utc = datetime.now(timezone.utc).isoformat()

            repo.record_session(
                session_id=sess_id,
                project_id=self.project_id,
                surface="STOP_GATE",
            )
            repo.record_mission(
                mission_id=mission_id,
                session_id=sess_id,
                project_id=self.project_id,
                status="COMPLETED",
            )

            san_reason = ""
            if reason:
                san_reason, _ = TelemetrySanitizer.sanitize_text(reason, max_length=500)

            gate_sig = hashlib.sha256(f"stop_gate|{self.project_id}|{sess_id}|{decision}".encode("utf-8")).hexdigest()[:16]

            ev = SafeEngineeringEvent(
                event_id=f"evt_{gate_sig}",
                mission_id=mission_id,
                project_id=self.project_id,
                event_type="STOP_GATE_RESULT",
                epistemic_grade="FACT",
                event_signature=gate_sig,
                payload_json=json.dumps({"decision": decision, "reason": san_reason}),
                created_at=now_utc,
                session_id=sess_id,
                outcome=decision,
            )
            repo.record_engineering_event(ev)
        except Exception:
            pass

    @staticmethod
    def _extract_session_id_from_path(transcript_path: Path) -> Optional[str]:
        """Extracts conversationId UUID from path like brain/<conversationId>/.system_generated/logs/..."""
        parts = transcript_path.parts
        for i, part in enumerate(parts):
            if part == "brain" and i + 1 < len(parts):
                candidate = parts[i + 1]
                # Validate UUID format loosely (8-4-4-4-12 hex or alphanumeric)
                if len(candidate) >= 16:
                    return candidate
        return None
