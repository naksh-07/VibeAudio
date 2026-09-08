"""AntiOS 3.0 Zero-Dependency NDJSON Telemetry Emitter.

Provides a lightweight, non-blocking bridge from native Antigravity lifecycle hooks
to the Experience Plane via append-only .agents/telemetry.ndjson.

Invariants:
- INV-10 (4-Zone Boundary): Pure System B event logging, zero runtime imports.
- INV-11 (Zero Framework Imports): Standard library only (json, os, sys, time, re, uuid).
- INV-12 (Telemetry Sanitization): Scrubs API keys, secrets, and user home paths.
- INV-13 (System A/B Firewall): Never touches experience.db, never mutates project code.
- Non-blocking: Telemetry failure NEVER impedes hook governance or tool execution.
"""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, Optional


# Sanitization regex patterns for secrets and tokens
SECRET_PATTERNS = [
    # Generic API Keys / Tokens
    (re.compile(r"sk-[a-zA-Z0-9_-]{20,}", re.IGNORECASE), "[REDACTED_API_KEY]"),
    (re.compile(r"AIza[0-9A-Za-z-_]{35}", re.IGNORECASE), "[REDACTED_GOOGLE_KEY]"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}", re.IGNORECASE), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{16,}", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    (re.compile(r"(password|secret|passwd|token|api_key)\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE), r"\1='[REDACTED]'"),
    (re.compile(r"AKIA[0-9A-Z]{16}", re.IGNORECASE), "[REDACTED_AWS_KEY]"),
]


def sanitize_string(value: str) -> str:
    """Sanitizes user home paths, system paths, and API credentials from strings."""
    if not isinstance(value, str) or not value:
        return ""

    sanitized = value

    # Scrub user home directory
    user_home = str(Path.home())
    if user_home and len(user_home) > 2:
        # Check both forward and backward slashes
        sanitized = sanitized.replace(user_home, "~")
        sanitized = sanitized.replace(user_home.replace("\\", "/"), "~")
        sanitized = sanitized.replace(user_home.lower(), "~")

    # Scrub secrets
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized


def sanitize_value(val: Any) -> Any:
    """Recursively sanitizes data structures for telemetry emission."""
    if isinstance(val, str):
        return sanitize_string(val)
    elif isinstance(val, dict):
        # Filter out blacklisted high-risk keys
        sanitized_dict = {}
        for k, v in val.items():
            k_lower = str(k).lower()
            if any(b in k_lower for b in ("secret", "token", "password", "auth", "credential", "prompt", "raw_content", "code_content")):
                sanitized_dict[k] = "[FILTERED_KEY]"
            else:
                sanitized_dict[k] = sanitize_value(v)
        return sanitized_dict
    elif isinstance(val, (list, tuple)):
        return [sanitize_value(x) for x in val]
    elif isinstance(val, (int, float, bool)) or val is None:
        return val
    else:
        return sanitize_string(str(val))


def emit_event(
    project_root: str,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    decision: Optional[str] = None,
    reason_code: Optional[str] = None,
    tool_class: Optional[str] = None,
) -> bool:
    """Emits a sanitized NDJSON event to .agents/telemetry.ndjson.

    NON-BLOCKING GUARANTEE:
    This function wraps all execution in a catch-all block.
    Any exception returns False and is silently discarded.
    """
    try:
        if not project_root or not isinstance(project_root, str):
            return False

        agents_dir = os.path.join(project_root, ".agents")
        telemetry_file = os.path.join(agents_dir, "telemetry.ndjson")

        # Project ID extraction from directory name
        project_id = os.path.basename(os.path.normpath(project_root)) or "unknown_project"

        # Determine timestamp in ISO 8601 UTC
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Build canonical sanitized record
        record: Dict[str, Any] = {
            "schema_version": 1,
            "event": sanitize_string(str(event_type)),
            "timestamp": now_utc,
            "project_id": sanitize_string(project_id),
        }

        if tool_class:
            record["tool_class"] = sanitize_string(str(tool_class))
        if decision:
            record["decision"] = sanitize_string(str(decision))
        if reason_code:
            record["reason_code"] = sanitize_string(str(reason_code))

        if payload and isinstance(payload, dict):
            # Only include sanitized payload fields
            record["metadata"] = sanitize_value(payload)

        line = json.dumps(record, ensure_ascii=False) + "\n"

        # Ensure .agents exists
        try:
            os.makedirs(agents_dir, exist_ok=True)
        except OSError:
            pass

        # Write in append mode
        with open(telemetry_file, "a", encoding="utf-8") as f:
            f.write(line)

        return True
    except Exception:
        # Strict non-blocking: Telemetry failure must never fail hook execution
        return False
