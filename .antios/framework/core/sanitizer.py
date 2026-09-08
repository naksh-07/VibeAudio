"""AntiOS 2.1 Local Engineering Intelligence — Telemetry Sanitizer & Privacy Engine.

Deterministic, fail-closed privacy and security boundary for AntiOS telemetry.
Ensures that all runtime events, tool calls, and execution facts are scrubbed
of sensitive credentials, personal paths, raw prompts, and model chain-of-thought
before persistence in the Central Experience Store.

Constitutional Invariants & Governance:
- FAIL-CLOSED: If safety cannot be proven, REDACT or DROP. Never STORE_RAW.
- COLLECTION REDLINES: No passwords, API keys, tokens, cookies, auth headers,
  .env secrets, private keys, out-of-workspace files, raw prompts, or CoT.
- EPISTEMIC BOUNDARY: Sanitized events are observations (FACT), never durable proof.
- INERT DATA: Telemetry is passive data; never executed or interpreted as policy.
- ZERO DEPENDENCIES: Pure Python standard library only.
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
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Version of the Sanitizer & Safe Event schema
SANITIZER_VERSION = "2.1.0"

# Size and bounding limits
MAX_OUTPUT_SUMMARY_CHARS = 500
MAX_EVENT_PAYLOAD_CHARS = 1000
MAX_ARG_STRING_CHARS = 2000
MAX_RELATIVE_FILES = 20
MAX_STACK_TRACE_FRAMES = 15
MAX_ERROR_MESSAGE_CHARS = 500


# =====================================================================
# Enums & Decision Auditing
# =====================================================================

class SanitizerDecision(str, Enum):
    """Authoritative decision emitted by the sanitizer for a field or event."""
    ALLOW = "ALLOW"
    REDACT = "REDACT"
    HASH = "HASH"
    SUMMARIZE = "SUMMARIZE"
    DROP = "DROP"


class SanitizerReason(str, Enum):
    """Categorical audit justification explaining a sanitization decision."""
    SAFE_STRUCTURED_FIELD = "SAFE_STRUCTURED_FIELD"
    SECRET_DETECTED = "SECRET_DETECTED"
    SENSITIVE_PATH = "SENSITIVE_PATH"
    OUTSIDE_PROJECT = "OUTSIDE_PROJECT"
    OVERSIZED = "OVERSIZED"
    UNSUPPORTED_CONTENT = "UNSUPPORTED_CONTENT"
    CHAIN_OF_THOUGHT_EXCLUDED = "CHAIN_OF_THOUGHT_EXCLUDED"
    RAW_PROMPT_NORMALIZED = "RAW_PROMPT_NORMALIZED"
    PROMPT_INJECTION_DEFANGED = "PROMPT_INJECTION_DEFANGED"


class PathClassification(str, Enum):
    """Classification of filesystem paths against project governance boundary."""
    SAFE_PROJECT_PATH = "SAFE_PROJECT_PATH"
    SENSITIVE_PROJECT_PATH = "SENSITIVE_PROJECT_PATH"
    OUTSIDE_PROJECT = "OUTSIDE_PROJECT"
    UNKNOWN_PATH = "UNKNOWN_PATH"


# =====================================================================
# Data Contracts: Safe Event & Safe Tool Call
# =====================================================================

@dataclass
class SafeToolCall:
    """Bounded, sanitized tool call suitable for experience.db persistence."""
    call_id: str
    turn_id: str
    tool_name: str
    sanitized_args_json: str = "{}"
    exit_code: Optional[int] = None
    status: str = "SUCCESS"  # SUCCESS, ERROR, DENIED_BY_GUARD, TIMED_OUT
    output_sha256: Optional[str] = None
    output_summary: str = ""
    duration_ms: int = 0
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SafeEngineeringEvent:
    """Canonical sanitized engineering event matching experience.db schema."""
    event_id: str
    mission_id: str
    project_id: str
    event_type: str
    epistemic_grade: str  # FACT, INFERENCE, ASSUMPTION
    affected_file: Optional[str] = None
    event_signature: str = ""
    payload_json: str = "{}"
    created_at: str = ""
    # Extended bounded telemetry metadata
    session_id: Optional[str] = None
    turn_id: Optional[str] = None
    source: str = "runtime_telemetry"
    tool_category: Optional[str] = None
    normalized_intent: Optional[str] = None
    relative_files: List[str] = field(default_factory=list)
    outcome: Optional[str] = None
    error_category: Optional[str] = None
    duration_ms: int = 0
    exit_code: Optional[int] = None
    retry_count: int = 0
    sanitizer_version: str = SANITIZER_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_db_row(self) -> Dict[str, Any]:
        """Returns row dict directly insertable into experience.db engineering_events."""
        return {
            "event_id": self.event_id,
            "mission_id": self.mission_id,
            "project_id": self.project_id,
            "event_type": self.event_type,
            "epistemic_grade": self.epistemic_grade,
            "affected_file": self.affected_file,
            "event_signature": self.event_signature,
            "payload_json": self.payload_json,
            "created_at": self.created_at,
        }


@dataclass
class SanitizationAuditRecord:
    """Audit trail explaining what decisions were applied without saving secrets."""
    field_name: str
    decision: SanitizerDecision
    reason: SanitizerReason
    redaction_count: int = 0


# =====================================================================
# Telemetry Sanitizer & Privacy Engine
# =====================================================================

class TelemetrySanitizer:
    """Authoritative fail-closed Telemetry Sanitizer & Privacy Engine.

    Features:
    1. Multi-tier deterministic secret scrubber (API keys, tokens, JWT, PEM, URIs, env).
    2. Path relativizer with canonical workspace boundary containment.
    3. Sensitive path & file shield (.env, credentials, keys, profile dirs).
    4. Chain-of-thought & raw prompt exclusion.
    5. Anti-poisoning & prompt injection defanging.
    6. Engineering error sanitization (compiler errors, test failures).
    7. Hard bounded envelopes for SQLite persistence.
    """

    # -------------------------------------------------------------
    # Secret Detection Patterns (Compiled Regex)
    # -------------------------------------------------------------

    # Provider-specific high-entropy keys
    _REGEX_GOOGLE_API_KEY = re.compile(r"\bAIza[0-9A-Za-z-_]{30,45}\b")
    _REGEX_GITHUB_TOKEN = re.compile(
        r"\b(?:ghp|gho|ghu|ghs|ghr)_[0-9A-Za-z]{30,255}\b|\bgithub_pat_[0-9A-Za-z_]{70,100}\b"
    )
    _REGEX_ANTHROPIC_KEY = re.compile(r"\bsk-ant-(?:api[0-9]{2}-)?[0-9A-Za-z-_]{20,}\b")
    _REGEX_OPENAI_KEY = re.compile(r"\bsk-(?!ant-)(?:proj-)?[0-9A-Za-z-_]{25,}\b")
    _REGEX_AWS_ACCESS_KEY = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
    _REGEX_SLACK_TOKEN = re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")

    # Private key blocks (RSA, EC, DSA, OPENSSH, PGP)
    _REGEX_PRIVATE_KEY_BLOCK = re.compile(
        r"-----BEGIN [A-Z0-9 ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]+PRIVATE KEY-----",
        re.MULTILINE,
    )
    _REGEX_SSH_PRIVATE_KEY_INLINE = re.compile(
        r"\b(?:ssh-rsa|ssh-ed25519|ecdsa-sha2-nistp\d+)\s+[A-Za-z0-9+/=]{100,}\b"
    )

    # JSON Web Tokens (JWT)
    _REGEX_JWT = re.compile(
        r"\beyJ[A-Za-z0-9-_=]+\.eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]+\b"
    )

    # HTTP Auth Headers & Bearer tokens
    _REGEX_AUTH_HEADER = re.compile(
        r"(?i)\b(?:authorization|proxy-authorization)\s*:\s*(?:bearer|basic|token)\s+[A-Za-z0-9\-._~+/]+=*",
    )
    _REGEX_BEARER_TOKEN = re.compile(
        r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]{20,}\b"
    )

    # HTTP Cookies & Set-Cookie headers
    _REGEX_COOKIE_HEADER = re.compile(
        r"(?i)\b(?:cookie|set-cookie)\s*:\s*[^\r\n]+",
    )

    # Database / Network URIs with embedded credentials (e.g. postgres://user:pass@host:5432/db)
    _REGEX_CREDENTIAL_URI = re.compile(
        r"\b(?:postgres|postgresql|mysql|mongodb|redis|amqp|amqps|http|https)://(?P<user>[^:\s/@]+):(?P<pass>[^@\s]+)@(?P<host>[^\s/]+)",
        re.IGNORECASE,
    )

    # Generic Key-Value secret assignments (in JSON, YAML, .env, CLI args, etc.)
    # e.g., password = "secret", "api_key": "xyz", --password=xyz, export SECRET="xyz"
    _REGEX_KV_SECRET = re.compile(
        r"(?i)\b(?:[A-Za-z0-9_]*_)?(?P<key>password|passwd|secret|api[_-]?key|auth[_-]?token|access[_-]?token|refresh[_-]?token|private[_-]?key|client[_-]?secret|session[_-]?token)\s*(?P<op>[:=]|=>)\s*(?P<val>['\"][^'\"\r\n]{3,}['\"]|[^\s,;'\"]{6,})",
    )

    # CLI flag secret assignments (e.g. --password=xyz, -password xyz)
    _REGEX_CLI_FLAG_SECRET = re.compile(
        r"(?i)(?:--?(?:password|token|api-key|secret|auth-token))\s*(=|\s+)\s*([^\s]{4,})",
    )

    # -------------------------------------------------------------
    # Sensitive Paths & Prohibited Names
    # -------------------------------------------------------------
    SENSITIVE_PATH_PATTERNS = [
        re.compile(r"(^|[/\\])\.env(\.[^/\\]*)?$"),
        re.compile(r"(^|[/\\])credentials(\.[^/\\]*)?$"),
        re.compile(r"(^|[/\\])secrets(\.[^/\\]*)?$"),
        re.compile(r"\.(?:pem|key|p12|pfx|kdbx)$"),
        re.compile(r"(^|[/\\])id_(?:rsa|dsa|ecdsa|ed25519)(\.pub)?$"),
        re.compile(r"(^|[/\\])\.npmrc$"),
        re.compile(r"(^|[/\\])\.pypirc$"),
        re.compile(r"(^|[/\\])\.netrc$"),
        re.compile(r"(^|[/\\])\.dockercfg$"),
        re.compile(r"(^|[/\\])config\.json$"),  # e.g. ~/.docker/config.json
        re.compile(r"(^|[/\\])(?:service[-_]account|google[-_]credentials)[^/\\]*\.json$"),
    ]

    USER_PROFILE_CREDENTIAL_DIRS = [
        ".ssh",
        ".aws",
        ".azure",
        ".config/gcloud",
        ".docker",
        ".gnupg",
        ".kube",
    ]

    # -------------------------------------------------------------
    # Prompt Injection & Poisoning Patterns
    # -------------------------------------------------------------
    PROMPT_INJECTION_PATTERNS = [
        re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions"),
        re.compile(r"(?i)bypass\s+(safety|guard|security|stop[-_ ]gate)"),
        re.compile(r"(?i)disregard\s+(all\s+)?(rules|guidelines|invariants)"),
        re.compile(r"(?i)override\s+(system\s+prompt|constitution|governance)"),
        re.compile(r"(?i)you\s+are\s+now\s+(an?\s+unrestricted|in\s+god\s+mode|dan)"),
        re.compile(r"(?i)system\s+directive\s+update"),
        re.compile(r"(?i)elevate\s+permissions?"),
        re.compile(r"(?i)grant\s+root\s+access"),
    ]

    # Keys that must be dropped entirely from dictionaries (Chain-of-thought, private conversations)
    PROHIBITED_DICT_KEYS = {
        "thinking",
        "thought",
        "thoughts",
        "reasoning",
        "reasoning_content",
        "internal_reasoning",
        "chain_of_thought",
        "cot",
        "raw_prompt",
        "user_prompt",
        "prompt",
        "system_prompt",
        "conversation_history",
        "transcript",
    }

    # -------------------------------------------------------------
    # Core Public Methods
    # -------------------------------------------------------------

    @classmethod
    def sanitize_text(
        cls,
        text: Optional[str],
        max_length: Optional[int] = None,
    ) -> Tuple[str, List[SanitizationAuditRecord]]:
        """Sanitizes text by removing all detected secrets and credential patterns.

        Guarantees deterministic, fail-closed redaction.
        Never reveals the original secret in audit records.
        """
        if text is None:
            return "", []

        audit: List[SanitizationAuditRecord] = []
        result = str(text)

        # 1. Private key blocks
        if "-----BEGIN" in result and "PRIVATE KEY-----" in result:
            count = len(cls._REGEX_PRIVATE_KEY_BLOCK.findall(result))
            if count > 0:
                result = cls._REGEX_PRIVATE_KEY_BLOCK.sub("[REDACTED_PRIVATE_KEY]", result)
                audit.append(SanitizationAuditRecord(
                    field_name="text",
                    decision=SanitizerDecision.REDACT,
                    reason=SanitizerReason.SECRET_DETECTED,
                    redaction_count=count,
                ))

        # 2. SSH inline keys
        ssh_matches = cls._REGEX_SSH_PRIVATE_KEY_INLINE.findall(result)
        if ssh_matches:
            result = cls._REGEX_SSH_PRIVATE_KEY_INLINE.sub("[REDACTED_SSH_KEY]", result)
            audit.append(SanitizationAuditRecord(
                field_name="text",
                decision=SanitizerDecision.REDACT,
                reason=SanitizerReason.SECRET_DETECTED,
                redaction_count=len(ssh_matches),
            ))

        # 3. Provider-specific tokens
        for pattern, token_name in [
            (cls._REGEX_GOOGLE_API_KEY, "GOOGLE_API_KEY"),
            (cls._REGEX_GITHUB_TOKEN, "GITHUB_TOKEN"),
            (cls._REGEX_ANTHROPIC_KEY, "ANTHROPIC_API_KEY"),
            (cls._REGEX_OPENAI_KEY, "OPENAI_API_KEY"),
            (cls._REGEX_AWS_ACCESS_KEY, "AWS_ACCESS_KEY"),
            (cls._REGEX_SLACK_TOKEN, "SLACK_TOKEN"),
        ]:
            matches = pattern.findall(result)
            if matches:
                result = pattern.sub(f"[REDACTED_{token_name}]", result)
                audit.append(SanitizationAuditRecord(
                    field_name="text",
                    decision=SanitizerDecision.REDACT,
                    reason=SanitizerReason.SECRET_DETECTED,
                    redaction_count=len(matches),
                ))

        # 4. JSON Web Tokens (JWT)
        jwt_matches = cls._REGEX_JWT.findall(result)
        if jwt_matches:
            result = cls._REGEX_JWT.sub("[REDACTED_JWT]", result)
            audit.append(SanitizationAuditRecord(
                field_name="text",
                decision=SanitizerDecision.REDACT,
                reason=SanitizerReason.SECRET_DETECTED,
                redaction_count=len(jwt_matches),
            ))

        # 5. Auth headers & Bearer tokens
        auth_matches = cls._REGEX_AUTH_HEADER.findall(result)
        if auth_matches:
            result = cls._REGEX_AUTH_HEADER.sub("Authorization: [REDACTED_AUTH_HEADER]", result)
            audit.append(SanitizationAuditRecord(
                field_name="text",
                decision=SanitizerDecision.REDACT,
                reason=SanitizerReason.SECRET_DETECTED,
                redaction_count=len(auth_matches),
            ))

        bearer_matches = cls._REGEX_BEARER_TOKEN.findall(result)
        if bearer_matches:
            result = cls._REGEX_BEARER_TOKEN.sub("Bearer [REDACTED_BEARER_TOKEN]", result)
            audit.append(SanitizationAuditRecord(
                field_name="text",
                decision=SanitizerDecision.REDACT,
                reason=SanitizerReason.SECRET_DETECTED,
                redaction_count=len(bearer_matches),
            ))

        # 6. Cookies & session tokens
        cookie_matches = cls._REGEX_COOKIE_HEADER.findall(result)
        if cookie_matches:
            result = cls._REGEX_COOKIE_HEADER.sub("Cookie: [REDACTED_COOKIE]", result)
            audit.append(SanitizationAuditRecord(
                field_name="text",
                decision=SanitizerDecision.REDACT,
                reason=SanitizerReason.SECRET_DETECTED,
                redaction_count=len(cookie_matches),
            ))

        # 7. Connection URIs with embedded credentials
        def _replace_uri_creds(m: re.Match) -> str:
            proto = m.group(0).split("://")[0]
            host = m.group("host")
            return f"{proto}://[REDACTED_USER]:[REDACTED_PASS]@{host}"

        uri_matches = cls._REGEX_CREDENTIAL_URI.findall(result)
        if uri_matches:
            result = cls._REGEX_CREDENTIAL_URI.sub(_replace_uri_creds, result)
            audit.append(SanitizationAuditRecord(
                field_name="text",
                decision=SanitizerDecision.REDACT,
                reason=SanitizerReason.SECRET_DETECTED,
                redaction_count=len(uri_matches),
            ))

        # 8. CLI flag secret assignments (--password=xyz)
        cli_flag_matches = cls._REGEX_CLI_FLAG_SECRET.findall(result)
        if cli_flag_matches:
            result = cls._REGEX_CLI_FLAG_SECRET.sub(r"\1 [REDACTED_SECRET]", result)
            audit.append(SanitizationAuditRecord(
                field_name="text",
                decision=SanitizerDecision.REDACT,
                reason=SanitizerReason.SECRET_DETECTED,
                redaction_count=len(cli_flag_matches),
            ))

        # 9. Key-value secret assignments
        def _replace_kv(m: re.Match) -> str:
            val = m.group("val")
            if "[REDACTED_" in val:
                return m.group(0)
            k = m.group("key")
            op = m.group("op")
            return f"{k}{op}[REDACTED_SECRET]"

        kv_matches = cls._REGEX_KV_SECRET.findall(result)
        if kv_matches:
            result = cls._REGEX_KV_SECRET.sub(_replace_kv, result)
            audit.append(SanitizationAuditRecord(
                field_name="text",
                decision=SanitizerDecision.REDACT,
                reason=SanitizerReason.SECRET_DETECTED,
                redaction_count=len(kv_matches),
            ))

        # 10. Prompt injection defanging
        for inj_pattern in cls._REGEX_INJECTION_LIST():
            if inj_pattern.search(result):
                result = inj_pattern.sub("[DEFANGED_INJECTION_DIRECTIVE]", result)
                audit.append(SanitizationAuditRecord(
                    field_name="text",
                    decision=SanitizerDecision.REDACT,
                    reason=SanitizerReason.PROMPT_INJECTION_DEFANGED,
                    redaction_count=1,
                ))

        # 11. Bounding / truncation
        if max_length is not None and len(result) > max_length:
            result = result[: max_length - 3] + "..."
            audit.append(SanitizationAuditRecord(
                field_name="text",
                decision=SanitizerDecision.SUMMARIZE,
                reason=SanitizerReason.OVERSIZED,
                redaction_count=1,
            ))

        return result, audit

    @classmethod
    def _REGEX_INJECTION_LIST(cls) -> List[re.Pattern]:
        return cls.PROMPT_INJECTION_PATTERNS

    # -------------------------------------------------------------
    # Path Security & Normalization
    # -------------------------------------------------------------

    @classmethod
    def normalize_path(cls, path: Union[str, Path, None]) -> str:
        """Normalizes a filesystem path across Windows and POSIX deterministically."""
        if path is None:
            return ""
        p_str = str(path).strip()
        if not p_str or p_str == "None":
            return ""
        # Standardize separators
        norm = p_str.replace("\\", "/")
        # Clean double slashes and resolve relative . components
        parts = [part for part in norm.split("/") if part and part != "."]

        # Reconstruct path
        is_abs = norm.startswith("/") or (len(norm) >= 2 and norm[1] == ":")
        reconstructed = "/".join(parts)
        if norm.startswith("/") and not reconstructed.startswith("/"):
            reconstructed = "/" + reconstructed

        # Lowercase drive letter on Windows (e.g. C: -> c:)
        if len(reconstructed) >= 2 and reconstructed[1] == ":":
            reconstructed = reconstructed[0].lower() + reconstructed[1:]

        return reconstructed

    @classmethod
    def is_sensitive_path(cls, path: Union[str, Path]) -> bool:
        """Checks whether a path references a sensitive file, key, or credential."""
        norm = cls.normalize_path(path)
        if not norm:
            return False

        # Check sensitive patterns
        for pat in cls.SENSITIVE_PATH_PATTERNS:
            if pat.search(norm):
                return True

        # Check user profile credential directories
        norm_lower = norm.lower()
        for d in cls.USER_PROFILE_CREDENTIAL_DIRS:
            if f"/{d}/" in norm_lower or norm_lower.endswith(f"/{d}"):
                return True

        return False

    @classmethod
    def classify_path(
        cls,
        path: Union[str, Path],
        project_root: Union[str, Path],
    ) -> Tuple[PathClassification, Optional[str]]:
        """Classifies a path against the project root boundary.

        Returns:
            (classification, safe_rel_path_or_none)
        """
        if not path or not project_root:
            return PathClassification.UNKNOWN_PATH, None

        root_norm = cls.normalize_path(project_root)
        path_norm = cls.normalize_path(path)

        # 1. First check if it is inherently a sensitive path
        if cls.is_sensitive_path(path_norm):
            return PathClassification.SENSITIVE_PROJECT_PATH, None

        # 2. Check path traversal attack escaping boundary
        if ".." in path_norm.split("/"):
            try:
                resolved_target = os.path.normpath(
                    os.path.join(str(project_root), str(path))
                )
                target_norm = cls.normalize_path(resolved_target)
            except Exception:
                return PathClassification.OUTSIDE_PROJECT, None
        else:
            target_norm = path_norm

        # 3. Check if target is inside project root
        root_abs = os.path.normcase(os.path.abspath(str(project_root)))
        try:
            target_abs = os.path.normcase(
                os.path.abspath(
                    str(path)
                    if os.path.isabs(str(path))
                    else os.path.join(str(project_root), str(path))
                )
            )
            common = os.path.commonpath([target_abs, root_abs])
            if common != root_abs:
                return PathClassification.OUTSIDE_PROJECT, None
        except (ValueError, Exception):
            # ValueError occurs on Windows if paths are on different drives
            return PathClassification.OUTSIDE_PROJECT, None

        # 4. Compute clean relative path
        try:
            rel = os.path.relpath(target_abs, root_abs)
            rel_norm = cls.normalize_path(rel)
            if rel_norm == ".":
                rel_norm = ""
            if rel_norm.startswith("../") or rel_norm == "..":
                return PathClassification.OUTSIDE_PROJECT, None

            # Re-check sensitive path on the resulting relative path
            if cls.is_sensitive_path(rel_norm):
                return PathClassification.SENSITIVE_PROJECT_PATH, None

            return PathClassification.SAFE_PROJECT_PATH, rel_norm
        except Exception:
            return PathClassification.UNKNOWN_PATH, None

    @classmethod
    def relativize_path(
        cls,
        path: Union[str, Path],
        project_root: Union[str, Path],
    ) -> Optional[str]:
        """Relativizes a path if it is safe and inside the project root.

        Returns:
            Relative POSIX path if safe, or None if sensitive/outside.
        """
        classification, rel_path = cls.classify_path(path, project_root)
        if classification == PathClassification.SAFE_PROJECT_PATH:
            return rel_path
        return None

    # -------------------------------------------------------------
    # Prompt & Intent Normalization
    # -------------------------------------------------------------

    @classmethod
    def normalize_intent(
        cls,
        raw_prompt: Optional[str],
        default_category: str = "ENGINEERING_TASK",
    ) -> Dict[str, str]:
        """Extracts safe, high-level task intent without saving raw prompt text.

        Guarantees:
        - Raw prompt text is dropped.
        - Returns high-level task_category, subsystem, and normalized_intent snippet.
        """
        if not raw_prompt:
            return {
                "task_category": default_category,
                "subsystem": "general",
                "normalized_intent": "unspecified",
            }

        text = str(raw_prompt).strip()

        # Classify task category
        category = default_category
        text_lower = text.lower()
        if any(k in text_lower for k in ["fix", "bug", "error", "fail", "broken", "crash"]):
            category = "BUG_FIX"
        elif any(k in text_lower for k in ["test", "verify", "audit", "check", "benchmark"]):
            category = "VERIFICATION"
        elif any(k in text_lower for k in ["refactor", "cleanup", "reorganize"]):
            category = "REFACTOR"
        elif any(k in text_lower for k in ["feat", "add", "implement", "create", "support"]):
            category = "FEATURE_IMPLEMENTATION"
        elif any(k in text_lower for k in ["doc", "readme", "architecture"]):
            category = "DOCUMENTATION"

        # Detect subsystem if present
        subsystem = "general"
        for candidate in ["auth", "storage", "governance", "api", "database", "cli", "telemetry", "test"]:
            if candidate in text_lower:
                subsystem = candidate
                break

        # Bounded normalized intent description: NEVER stores raw user prompt
        normalized_intent = f"{category} on {subsystem}"

        return {
            "task_category": category,
            "subsystem": subsystem,
            "normalized_intent": normalized_intent,
        }

    # -------------------------------------------------------------
    # Error Sanitization
    # -------------------------------------------------------------

    @classmethod
    def sanitize_error(
        cls,
        raw_error: Union[str, Exception, Dict[str, Any]],
        project_root: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """Normalizes and scrubs errors into structured, safe engineering facts.

        Preserves:
        - error_category
        - exception_type
        - normalized_message (secrets and absolute user paths scrubbed)
        - affected_file (relativized if inside project)
        - test_name (if identified)

        Removes:
        - secrets & credentials
        - personal user profile paths
        - environment dumps
        """
        error_str = ""
        if isinstance(raw_error, Exception):
            error_str = f"{type(raw_error).__name__}: {str(raw_error)}"
        elif isinstance(raw_error, dict):
            error_str = json.dumps(raw_error)
        else:
            error_str = str(raw_error)

        # Classify category
        category = "UNKNOWN_ERROR"
        if any(w in error_str for w in ["SyntaxError", "IndentationError", "compile", "Syntax"]):
            category = "SYNTAX_ERROR"
        elif any(w in error_str for w in ["AssertionError", "FAILED", "FAIL:", "pytest", "unittest"]):
            category = "TEST_FAILURE"
        elif any(w in error_str for w in ["PermissionError", "EACCES", "AccessDenied"]):
            category = "PERMISSION_DENIED"
        elif any(w in error_str for w in ["TimeoutError", "timed out", "TIMEOUT"]):
            category = "TIMEOUT"
        elif any(w in error_str for w in ["FileNotFoundError", "NoSuchFile", "ModuleNotFoundError", "ImportError"]):
            category = "MISSING_RESOURCE"
        elif any(w in error_str for w in ["Command", "exit code", "returncode"]):
            category = "COMMAND_FAILURE"
        else:
            category = "RUNTIME_EXCEPTION"

        # Extract exception type
        exc_match = re.search(r"\b([A-Za-z0-9_]+(?:Error|Exception))\b", error_str)
        exception_type = exc_match.group(1) if exc_match else None

        # Extract test name if present (e.g. test_something in test_file.py)
        test_match = re.search(r"\b(test_[A-Za-z0-9_]+)\b", error_str)
        test_name = test_match.group(1) if test_match else None

        # Scrub secrets from the error message
        scrubbed_msg, _ = cls.sanitize_text(error_str)

        # Relativize paths inside the error message
        if project_root:
            root_norm = cls.normalize_path(project_root)
            scrubbed_msg = scrubbed_msg.replace(root_norm + "/", "")
            scrubbed_msg = scrubbed_msg.replace(str(project_root) + "\\", "")
            scrubbed_msg = scrubbed_msg.replace(str(project_root) + "/", "")

        # Strip user home directory traces (e.g. C:/Users/Name/ or /home/name/)
        user_home = str(Path.home())
        if user_home and len(user_home) > 3:
            scrubbed_msg = scrubbed_msg.replace(user_home, "~")
            scrubbed_msg = scrubbed_msg.replace(cls.normalize_path(user_home), "~")

        # Bound message size
        if len(scrubbed_msg) > MAX_ERROR_MESSAGE_CHARS:
            scrubbed_msg = scrubbed_msg[: MAX_ERROR_MESSAGE_CHARS - 3] + "..."

        # Detect affected file
        affected_file: Optional[str] = None
        if project_root:
            file_match = re.search(
                r'(?:File "([^"]+\.(?:py|ts|js|rs|go|json|md))"|([A-Za-z0-9_./\\]+\.(?:py|ts|js|rs|go|json|md))[:",])',
                error_str,
            )
            if file_match:
                candidate = file_match.group(1) or file_match.group(2)
                cls_type, safe_rel = cls.classify_path(candidate, project_root)
                if cls_type == PathClassification.SAFE_PROJECT_PATH:
                    affected_file = safe_rel

        return {
            "error_category": category,
            "exception_type": exception_type,
            "normalized_message": scrubbed_msg,
            "affected_file": affected_file,
            "test_name": test_name,
        }

    # -------------------------------------------------------------
    # Tool Call Sanitization
    # -------------------------------------------------------------

    @classmethod
    def sanitize_tool_call(
        cls,
        call_id: str,
        turn_id: str,
        tool_name: str,
        raw_args: Union[Dict[str, Any], str],
        project_root: Union[str, Path],
        exit_code: Optional[int] = None,
        status: str = "SUCCESS",
        raw_output: Optional[str] = None,
        duration_ms: int = 0,
        created_at: Optional[str] = None,
    ) -> SafeToolCall:
        """Sanitizes raw tool call inputs and outputs into a SafeToolCall contract.

        Guarantees:
        - Arguments scrubbed of secrets.
        - File paths inside arguments relativized or dropped if sensitive/outside.
        - Output bounded to MAX_OUTPUT_SUMMARY_CHARS.
        - Output SHA-256 computed over scrubbed representation.
        - Chain-of-thought keys dropped.
        """
        now_utc = created_at or datetime.now(timezone.utc).isoformat()

        # 1. Parse and sanitize arguments
        args_dict: Dict[str, Any] = {}
        if isinstance(raw_args, str):
            try:
                args_dict = json.loads(raw_args)
            except Exception:
                scrubbed, _ = cls.sanitize_text(raw_args, max_length=MAX_ARG_STRING_CHARS)
                args_dict = {"raw_payload": scrubbed}
        elif isinstance(raw_args, dict):
            args_dict = raw_args
        else:
            args_dict = {"unsupported_payload": str(type(raw_args))}

        sanitized_args = cls._sanitize_data_structure(args_dict, project_root)
        sanitized_args_json = json.dumps(sanitized_args, sort_keys=True)

        # 2. Compute output summary and SHA-256
        output_summary = ""
        output_sha256 = None
        if raw_output is not None:
            scrubbed_out, _ = cls.sanitize_text(raw_output)
            output_sha256 = hashlib.sha256(scrubbed_out.encode("utf-8")).hexdigest()
            if len(scrubbed_out) > MAX_OUTPUT_SUMMARY_CHARS:
                output_summary = scrubbed_out[: MAX_OUTPUT_SUMMARY_CHARS - 3] + "..."
            else:
                output_summary = scrubbed_out

        return SafeToolCall(
            call_id=call_id,
            turn_id=turn_id,
            tool_name=tool_name,
            sanitized_args_json=sanitized_args_json,
            exit_code=exit_code,
            status=status,
            output_sha256=output_sha256,
            output_summary=output_summary,
            duration_ms=max(0, int(duration_ms)),
            created_at=now_utc,
        )

    # -------------------------------------------------------------
    # Engineering Event Sanitization
    # -------------------------------------------------------------

    @classmethod
    def sanitize_event(
        cls,
        raw_event: Dict[str, Any],
        project_root: Union[str, Path],
        project_id: str,
        mission_id: str,
    ) -> SafeEngineeringEvent:
        """Sanitizes an incoming raw engineering event into a SafeEngineeringEvent.

        Guarantees:
        - Collection redlines enforced (no CoT, no secrets, no raw prompt).
        - Relative files validated and bound.
        - Payload JSON bounded to MAX_EVENT_PAYLOAD_CHARS.
        - Deterministic event_id and event_signature.
        """
        now_utc = raw_event.get("created_at") or datetime.now(timezone.utc).isoformat()
        event_type = raw_event.get("event_type", "GENERIC_EVENT")
        epistemic_grade = raw_event.get("epistemic_grade", "FACT")

        # Affected file
        raw_file = raw_event.get("affected_file")
        affected_file: Optional[str] = None
        if raw_file:
            cls_type, safe_rel = cls.classify_path(raw_file, project_root)
            if cls_type == PathClassification.SAFE_PROJECT_PATH:
                affected_file = safe_rel
            elif cls_type == PathClassification.SENSITIVE_PROJECT_PATH:
                affected_file = "[REDACTED_SENSITIVE_PATH]"
            else:
                affected_file = "[OUT_OF_WORKSPACE_PATH]"

        # Relative files list
        raw_files = raw_event.get("relative_files") or []
        safe_relative_files: List[str] = []
        if isinstance(raw_files, list):
            for f in raw_files[:MAX_RELATIVE_FILES]:
                cls_type, safe_rel = cls.classify_path(f, project_root)
                if cls_type == PathClassification.SAFE_PROJECT_PATH and safe_rel:
                    safe_relative_files.append(safe_rel)

        # Intent
        raw_intent = raw_event.get("normalized_intent") or raw_event.get("prompt")
        intent_info = cls.normalize_intent(raw_intent)
        normalized_intent = intent_info.get("normalized_intent")

        # Sanitize payload
        payload_data = raw_event.get("payload", {})
        if not isinstance(payload_data, dict):
            payload_data = {"data": str(payload_data)}
        sanitized_payload = cls._sanitize_data_structure(payload_data, project_root)
        payload_json = json.dumps(sanitized_payload, sort_keys=True)
        if len(payload_json) > MAX_EVENT_PAYLOAD_CHARS:
            payload_json = payload_json[: MAX_EVENT_PAYLOAD_CHARS - 3] + "..."

        # Signature & ID
        sig_base = f"{event_type}|{project_id}|{mission_id}|{affected_file or ''}|{now_utc}"
        event_signature = hashlib.sha256(sig_base.encode("utf-8")).hexdigest()[:32]
        event_id = f"evt_{hashlib.sha256((sig_base + payload_json).encode('utf-8')).hexdigest()[:16]}"

        return SafeEngineeringEvent(
            event_id=event_id,
            mission_id=mission_id,
            project_id=project_id,
            event_type=event_type,
            epistemic_grade=epistemic_grade,
            affected_file=affected_file,
            event_signature=event_signature,
            payload_json=payload_json,
            created_at=now_utc,
            session_id=raw_event.get("session_id"),
            turn_id=raw_event.get("turn_id"),
            source=raw_event.get("source", "runtime_telemetry"),
            tool_category=raw_event.get("tool_category"),
            normalized_intent=normalized_intent,
            relative_files=safe_relative_files,
            outcome=raw_event.get("outcome"),
            error_category=raw_event.get("error_category"),
            duration_ms=max(0, int(raw_event.get("duration_ms", 0))),
            exit_code=raw_event.get("exit_code"),
            retry_count=max(0, int(raw_event.get("retry_count", 0))),
        )

    # -------------------------------------------------------------
    # Recursive Data Structure Scrubber
    # -------------------------------------------------------------

    @classmethod
    def _sanitize_data_structure(
        cls,
        item: Any,
        project_root: Union[str, Path],
        depth: int = 0,
    ) -> Any:
        """Recursively sanitizes a JSON-compatible dictionary or list.

        Enforces:
        - Drops prohibited keys (CoT, prompts).
        - Redacts secrets in all strings.
        - Relativizes file paths in strings matching project files.
        - Bounds recursion depth (max 10).
        """
        if depth > 10:
            return "[NESTING_LIMIT_EXCEEDED]"

        if isinstance(item, dict):
            clean_dict: Dict[str, Any] = {}
            for k, v in item.items():
                k_str = str(k).lower().strip()
                # 1. Drop prohibited keys completely
                if k_str in cls.PROHIBITED_DICT_KEYS:
                    continue
                # 2. Check if key itself indicates a sensitive secret
                if any(sec_term in k_str for sec_term in ["password", "passwd", "secret", "token", "api_key", "auth"]):
                    clean_dict[k] = "[REDACTED_SECRET]"
                    continue
                # 3. Recurse value
                clean_dict[k] = cls._sanitize_data_structure(v, project_root, depth + 1)
            return clean_dict

        elif isinstance(item, list):
            return [
                cls._sanitize_data_structure(elem, project_root, depth + 1)
                for elem in item[:50]  # Cap arrays to 50 items
            ]

        elif isinstance(item, str):
            # Check if this string is directly a sensitive path/file
            if cls.is_sensitive_path(item):
                return "[REDACTED_SENSITIVE_PATH]"

            # Check if this string looks like a discrete file path (not multi-token command or text)
            looks_like_path = ("/" in item or "\\" in item) and len(item) < 300 and not any(c in item for c in "\n\r\t")
            if looks_like_path:
                tokens = item.strip().split()
                # A path is either a single token or an existing filesystem path
                if len(tokens) == 1 or (len(tokens) > 1 and Path(item).exists()):
                    cls_type, safe_rel = cls.classify_path(item, project_root)
                    if cls_type == PathClassification.SAFE_PROJECT_PATH and safe_rel:
                        scrubbed_path, _ = cls.sanitize_text(safe_rel)
                        return scrubbed_path
                    elif cls_type == PathClassification.SENSITIVE_PROJECT_PATH:
                        return "[REDACTED_SENSITIVE_PATH]"
                    elif cls_type == PathClassification.OUTSIDE_PROJECT:
                        return "[OUT_OF_WORKSPACE_PATH]"

            # Sanitize string content for secrets
            scrubbed, _ = cls.sanitize_text(item, max_length=MAX_ARG_STRING_CHARS)
            return scrubbed

        elif isinstance(item, (int, float, bool)) or item is None:
            return item

        else:
            # Unsupported complex types: stringify and scrub
            scrubbed, _ = cls.sanitize_text(str(item), max_length=500)
            return scrubbed
