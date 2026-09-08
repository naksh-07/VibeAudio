"""AntiOS 2.1 Local Engineering Intelligence — Storage & Data Directory Foundation.

Authoritative local persistence layer for AntiOS 2.1:
- User-configurable Central AntiOS Data Directory (<data-dir>/experience.db).
- Zero database files inside target project repositories (INV-10).
- Pure Python standard library sqlite3 (zero third-party dependencies).
- Concurrency-ready SQLite WAL mode with synchronous=NORMAL and busy_timeout=5000.
- Strict project/tenant scoping (GLOBAL -> PROJECT -> SESSION -> MISSION -> TURN -> TOOL_CALL -> ENGINEERING_EVENT).
- Deterministic project identity derivation and verification.
- Forward-only atomic schema versioning and migrations.
- Short-lived, transaction-safe connection lifecycle management.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
from typing import Any, Dict, Generator, List, Optional, Set, Tuple, Union

from framework.core.sanitizer import SafeEngineeringEvent, SafeToolCall

# Current storage schema version
CURRENT_STORAGE_SCHEMA_VERSION = "2.1.0"
DEFAULT_BUSY_TIMEOUT_MS = 5000


class StorageError(Exception):
    """Base exception for AntiOS experience storage errors."""
    pass


class DataDirectoryNotConfiguredError(StorageError):
    """Raised when no central data directory has been configured."""
    pass


class DataDirectoryNotFoundError(StorageError):
    """Raised when configured data directory does not exist on disk."""
    pass


class TenantIsolationViolationError(StorageError):
    """Raised when an operation attempts to breach project tenant isolation."""
    pass


class MigrationError(StorageError):
    """Raised when database schema migration fails."""
    pass


@dataclass
class StorageContext:
    """Answers the three fundamental governance questions of the AntiOS Data Resolver."""
    data_dir: Path
    db_path: Path
    project_id: str
    project_name: str
    project_root: Path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_dir": str(self.data_dir),
            "db_path": str(self.db_path),
            "project_id": self.project_id,
            "project_name": self.project_name,
            "project_root": str(self.project_root),
        }


@dataclass
class StorageStatus:
    """Comprehensive diagnostic status of the AntiOS Experience Storage foundation."""
    is_configured: bool
    data_dir: Optional[str] = None
    db_path: Optional[str] = None
    db_exists: bool = False
    db_size_bytes: int = 0
    schema_version: Optional[str] = None
    applied_migrations: List[str] = field(default_factory=list)
    journal_mode: Optional[str] = None
    synchronous: Optional[int] = None
    busy_timeout: Optional[int] = None
    foreign_keys: bool = False
    project_registered: bool = False
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    table_counts: Dict[str, int] = field(default_factory=dict)
    backups_dir_exists: bool = False
    exports_dir_exists: bool = False
    config_toml_exists: bool = False
    is_healthy: bool = False
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =====================================================================
# Authoritative Data Directory Resolver
# =====================================================================

class AntiOSDataResolver:
    """Authoritative singleton resolver answering:
    1. Where is AntiOS's persistent data directory?
    2. Which experience database is authoritative?
    3. Which project is currently being operated on?
    """

    @staticmethod
    def normalize_path(path: Union[str, Path]) -> str:
        """Normalizes a filesystem path across Windows and POSIX deterministically."""
        p = Path(path).resolve()
        norm = str(p).replace("\\", "/")
        # On Windows, normalize drive letter to lowercase
        if len(norm) >= 2 and norm[1] == ":":
            norm = norm[0].lower() + norm[1:]
        return norm

    @classmethod
    def resolve_project_identity(
        cls,
        project_root: Union[str, Path],
        manifest_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """Resolves deterministic, stable project_id and project_name.

        Formula:
        If project has metadata.project_id stored in .antios/manifest.json, use it.
        Otherwise: proj_{sha256(canonical_root_path)[:16]}
        """
        root_path = Path(project_root).resolve()
        canonical_path = cls.normalize_path(root_path)
        project_name = root_path.name or "root"

        # Check existing manifest if available
        if manifest_data and isinstance(manifest_data, dict):
            metadata = manifest_data.get("metadata", {})
            if isinstance(metadata, dict) and metadata.get("project_id"):
                return str(metadata["project_id"]), project_name

        manifest_file = root_path / ".antios" / "manifest.json"
        if manifest_file.is_file():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    metadata = data.get("metadata", {})
                    if isinstance(metadata, dict) and metadata.get("project_id"):
                        return str(metadata["project_id"]), project_name
            except Exception:
                pass

        # Deterministic fallback based on canonical path
        digest = hashlib.sha256(canonical_path.encode("utf-8")).hexdigest()[:16]
        return f"proj_{digest}", project_name

    @classmethod
    def resolve_data_dir(
        cls,
        project_root: Optional[Union[str, Path]] = None,
        explicit_dir: Optional[Union[str, Path]] = None,
    ) -> Path:
        """Resolves the authoritative central AntiOS Data Directory.

        Precedence:
        1. Explicit argument (`explicit_dir`, e.g. from CLI `--data-dir`).
        2. Environment variable: `ANTIOS_DATA_DIR`.
        3. Project config: `antios.config.json` -> `data_dir`.
        4. Project manifest: `.antios/manifest.json` -> `metadata.data_dir`.
        5. Fail-closed: No silent defaults, no project-local databases.
        """
        # 1. Explicit argument
        if explicit_dir is not None and str(explicit_dir).strip():
            candidate = Path(explicit_dir).resolve()
            return candidate

        # 2. Environment variable
        env_val = os.environ.get("ANTIOS_DATA_DIR")
        if env_val and env_val.strip():
            return Path(env_val).resolve()

        # 3. Project-side configuration
        if project_root is not None:
            proj = Path(project_root).resolve()
            # 3a. antios.config.json
            config_file = proj / "antios.config.json"
            if config_file.is_file():
                try:
                    with open(config_file, "r", encoding="utf-8-sig") as f:
                        cfg_data = json.load(f)
                        if isinstance(cfg_data, dict) and cfg_data.get("data_dir"):
                            return Path(cfg_data["data_dir"]).resolve()
                except Exception:
                    pass

            # 3b. .antios/manifest.json
            manifest_file = proj / ".antios" / "manifest.json"
            if manifest_file.is_file():
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        man_data = json.load(f)
                        metadata = man_data.get("metadata", {})
                        if isinstance(metadata, dict) and metadata.get("data_dir"):
                            return Path(metadata["data_dir"]).resolve()
                except Exception:
                    pass

        # 4. Fail-closed: require explicit configuration
        raise DataDirectoryNotConfiguredError(
            "AntiOS Data Directory is not configured. "
            "Please specify --data-dir, set the ANTIOS_DATA_DIR environment variable, "
            "or configure 'data_dir' in antios.config.json."
        )

    @classmethod
    def resolve_experience_db(cls, data_dir: Union[str, Path]) -> Path:
        """Returns the authoritative path to the central experience database."""
        return Path(data_dir).resolve() / "experience.db"

    @classmethod
    def resolve_context(
        cls,
        project_root: Optional[Union[str, Path]] = None,
        explicit_dir: Optional[Union[str, Path]] = None,
    ) -> StorageContext:
        """Resolves the complete storage context."""
        root = Path(project_root or Path.cwd()).resolve()
        data_dir = cls.resolve_data_dir(project_root=root, explicit_dir=explicit_dir)
        db_path = cls.resolve_experience_db(data_dir)
        proj_id, proj_name = cls.resolve_project_identity(root)

        return StorageContext(
            data_dir=data_dir,
            db_path=db_path,
            project_id=proj_id,
            project_name=proj_name,
            project_root=root,
        )


# =====================================================================
# Directory Structure & File Initialization
# =====================================================================

DEFAULT_CONFIG_TOML_CONTENT = """# AntiOS 2.1 Experience Data Directory Configuration
version = "2.1.0"

[storage]
max_database_bytes = 52428800 # 50 MB ceiling
busy_timeout_ms = 5000
wal_autocheckpoint = 1000

[retention]
max_missions_per_project = 500
prune_older_than_days = 90
"""


def init_data_directory(data_dir: Union[str, Path]) -> Tuple[Path, Path]:
    """Establishes the central AntiOS Data Directory structure:
    <data-dir>/
        experience.db
        config.toml
        backups/
        exports/

    Returns (data_dir_path, db_path).
    """
    target = Path(data_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)

    backups_dir = target / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    exports_dir = target / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    config_file = target / "config.toml"
    if not config_file.exists():
        config_file.write_text(DEFAULT_CONFIG_TOML_CONTENT, encoding="utf-8")

    db_path = target / "experience.db"
    return target, db_path


# =====================================================================
# Database Connection & Lifecycle Management
# =====================================================================

def get_db_connection(
    db_path: Union[str, Path],
    timeout: float = 5.0,
    enforce_foreign_keys: bool = True,
) -> sqlite3.Connection:
    """Establishes an ACID-compliant, standard-library sqlite3 connection.

    Applies mandatory AntiOS PRAGMAs:
    - journal_mode = WAL (Write-Ahead Log)
    - synchronous = NORMAL (safe, durable, high throughput)
    - busy_timeout = 5000 (resilient lock acquisition)
    - foreign_keys = ON (relational integrity)
    - auto_vacuum = INCREMENTAL (page reclamation)
    """
    path_obj = Path(db_path).resolve()
    path_obj.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(path_obj),
        timeout=timeout,
        isolation_level=None,  # Autocommit mode by default; manual transactions via BEGIN
    )
    conn.row_factory = sqlite3.Row

    # Apply PRAGMAs
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute(f"PRAGMA busy_timeout = {int(timeout * 1000)};")
    if enforce_foreign_keys:
        conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA auto_vacuum = INCREMENTAL;")

    return conn


# =====================================================================
# Schema & Migration Engine
# =====================================================================

INITIAL_SCHEMA_DDL = """
-- Schema Migrations Ledger
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL,
    checksum TEXT NOT NULL,
    description TEXT
);

-- Projects Entity
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    project_name TEXT NOT NULL,
    canonical_path TEXT NOT NULL UNIQUE,
    ecosystem TEXT,
    first_observed_at TEXT NOT NULL,
    last_active_at TEXT NOT NULL,
    metadata_json TEXT DEFAULT '{}'
);

-- Sessions Entity
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    surface TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    total_turns INTEGER DEFAULT 0,
    token_usage_json TEXT DEFAULT '{}',
    metadata_json TEXT DEFAULT '{}'
);

-- Missions Entity
CREATE TABLE IF NOT EXISTS missions (
    mission_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    intent_query TEXT,
    task_class TEXT,
    risk_tier TEXT,
    workforce_mode TEXT,
    status TEXT NOT NULL,
    stop_gate_exit_code INTEGER,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    metadata_json TEXT DEFAULT '{}'
);

-- Turns Entity
CREATE TABLE IF NOT EXISTS turns (
    turn_id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(mission_id) ON DELETE CASCADE,
    step_idx INTEGER NOT NULL,
    agent_role TEXT NOT NULL,
    agent_conversation_id TEXT,
    duration_ms INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    metadata_json TEXT DEFAULT '{}'
);

-- Tool Calls Entity
CREATE TABLE IF NOT EXISTS tool_calls (
    call_id TEXT PRIMARY KEY,
    turn_id TEXT NOT NULL REFERENCES turns(turn_id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    sanitized_args_json TEXT DEFAULT '{}',
    exit_code INTEGER,
    status TEXT NOT NULL,
    output_sha256 TEXT,
    output_summary TEXT,
    duration_ms INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

-- Engineering Events Entity
CREATE TABLE IF NOT EXISTS engineering_events (
    event_id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(mission_id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    epistemic_grade TEXT NOT NULL,
    affected_file TEXT,
    event_signature TEXT,
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);

-- Ingestion Checkpoints Entity (Phase 105)
CREATE TABLE IF NOT EXISTS ingestion_checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    source_path TEXT NOT NULL,
    last_byte_offset INTEGER DEFAULT 0,
    last_step_idx INTEGER DEFAULT -1,
    file_sha256 TEXT,
    file_size_bytes INTEGER DEFAULT 0,
    records_ingested INTEGER DEFAULT 0,
    updated_at TEXT NOT NULL
);

-- Relational Foreign Key B-Tree Indexes
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_missions_session ON missions(session_id);
CREATE INDEX IF NOT EXISTS idx_missions_project ON missions(project_id);
CREATE INDEX IF NOT EXISTS idx_missions_status ON missions(project_id, status);
CREATE INDEX IF NOT EXISTS idx_turns_mission ON turns(mission_id);
CREATE INDEX IF NOT EXISTS idx_tool_calls_turn ON tool_calls(turn_id);
CREATE INDEX IF NOT EXISTS idx_tool_calls_tool_status ON tool_calls(tool_name, status);
CREATE INDEX IF NOT EXISTS idx_events_mission ON engineering_events(mission_id);
CREATE INDEX IF NOT EXISTS idx_events_project ON engineering_events(project_id);
CREATE INDEX IF NOT EXISTS idx_events_project_type_time ON engineering_events(project_id, event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_events_signature ON engineering_events(event_signature);
CREATE INDEX IF NOT EXISTS idx_checkpoints_session ON ingestion_checkpoints(session_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_project ON ingestion_checkpoints(project_id);
"""


def _compute_ddl_checksum(ddl: str) -> str:
    """Computes a normalized SHA-256 checksum for DDL scripts."""
    cleaned = "".join(ddl.split())
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def init_experience_db(db_path: Union[str, Path]) -> None:
    """Transaction-safe, idempotent initialization and migration of the experience database."""
    target_path = Path(db_path).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with closing(get_db_connection(target_path)) as conn:
        cursor = conn.cursor()

        # Check if schema_migrations table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations';"
        )
        has_migrations_table = cursor.fetchone() is not None

        already_applied = False
        if has_migrations_table:
            cursor.execute(
                "SELECT version FROM schema_migrations WHERE version = ?;",
                (CURRENT_STORAGE_SCHEMA_VERSION,),
            )
            already_applied = cursor.fetchone() is not None

        if already_applied:
            # Ensure ingestion_checkpoints table and indexes exist for existing databases
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='ingestion_checkpoints';"
            )
            if not cursor.fetchone():
                cursor.executescript("""
                CREATE TABLE IF NOT EXISTS ingestion_checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
                    source_type TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    last_byte_offset INTEGER DEFAULT 0,
                    last_step_idx INTEGER DEFAULT -1,
                    file_sha256 TEXT,
                    file_size_bytes INTEGER DEFAULT 0,
                    records_ingested INTEGER DEFAULT 0,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_checkpoints_session ON ingestion_checkpoints(session_id);
                CREATE INDEX IF NOT EXISTS idx_checkpoints_project ON ingestion_checkpoints(project_id);
                """)
            return  # Idempotent no-op

        # Execute migration atomically
        checksum = _compute_ddl_checksum(INITIAL_SCHEMA_DDL)
        now_utc = datetime.now(timezone.utc).isoformat()

        try:
            cursor.executescript(INITIAL_SCHEMA_DDL)
            cursor.execute(
                """INSERT OR REPLACE INTO schema_migrations 
                   (version, applied_at, checksum, description) 
                   VALUES (?, ?, ?, ?);""",
                (
                    CURRENT_STORAGE_SCHEMA_VERSION,
                    now_utc,
                    checksum,
                    "AntiOS 2.1 Initial Telemetry Storage Foundation Schema",
                ),
            )
        except Exception as e:
            raise MigrationError(f"Failed to initialize experience database at {db_path}: {e}") from e


# =====================================================================
# Project Registration & Tenant Scoping Primitives
# =====================================================================

def register_project(
    db_path: Union[str, Path],
    project_root: Union[str, Path],
    project_id: Optional[str] = None,
    ecosystem: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Registers or updates project identity in the authoritative database.

    Enforces deterministic project_id and canonical path uniqueness.
    """
    root = Path(project_root).resolve()
    resolved_id, project_name = AntiOSDataResolver.resolve_project_identity(root)
    pid = project_id or resolved_id
    canonical_path = AntiOSDataResolver.normalize_path(root)
    now_utc = datetime.now(timezone.utc).isoformat()
    meta_json = json.dumps(metadata or {})

    with closing(get_db_connection(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE;")
        try:
            cursor.execute(
                "SELECT project_id, first_observed_at FROM projects WHERE canonical_path = ?;",
                (canonical_path,),
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing
                cursor.execute(
                    """UPDATE projects 
                       SET last_active_at = ?, project_name = ?, ecosystem = COALESCE(?, ecosystem), metadata_json = ?
                       WHERE canonical_path = ?;""",
                    (now_utc, project_name, ecosystem, meta_json, canonical_path),
                )
                pid = existing["project_id"]
            else:
                cursor.execute(
                    """INSERT INTO projects 
                       (project_id, project_name, canonical_path, ecosystem, first_observed_at, last_active_at, metadata_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?);""",
                    (pid, project_name, canonical_path, ecosystem, now_utc, now_utc, meta_json),
                )
            cursor.execute("COMMIT;")
        except Exception as e:
            cursor.execute("ROLLBACK;")
            raise StorageError(f"Failed to register project in {db_path}: {e}") from e

    return pid


def verify_project_isolation(
    db_path: Union[str, Path],
    project_a_id: str,
    project_b_id: str,
) -> bool:
    """Verifies that queries scoped to project_a_id strictly exclude project_b_id records."""
    with closing(get_db_connection(db_path)) as conn:
        cursor = conn.cursor()

        # Check sessions
        cursor.execute(
            "SELECT count(*) as cnt FROM sessions WHERE project_id = ? AND project_id = ?;",
            (project_a_id, project_b_id),
        )
        if cursor.fetchone()["cnt"] > 0:
            return False

        # Query all records under project_a
        cursor.execute("SELECT session_id FROM sessions WHERE project_id = ?;", (project_a_id,))
        a_sessions = {row["session_id"] for row in cursor.fetchall()}

        cursor.execute("SELECT session_id FROM sessions WHERE project_id = ?;", (project_b_id,))
        b_sessions = {row["session_id"] for row in cursor.fetchall()}

        if not a_sessions.isdisjoint(b_sessions):
            return False

        cursor.execute("SELECT mission_id FROM missions WHERE project_id = ?;", (project_a_id,))
        a_missions = {row["mission_id"] for row in cursor.fetchall()}

        cursor.execute("SELECT mission_id FROM missions WHERE project_id = ?;", (project_b_id,))
        b_missions = {row["mission_id"] for row in cursor.fetchall()}

        if not a_missions.isdisjoint(b_missions):
            return False

        cursor.execute("SELECT event_id FROM engineering_events WHERE project_id = ?;", (project_a_id,))
        a_events = {row["event_id"] for row in cursor.fetchall()}

        cursor.execute("SELECT event_id FROM engineering_events WHERE project_id = ?;", (project_b_id,))
        b_events = {row["event_id"] for row in cursor.fetchall()}

        if not a_events.isdisjoint(b_events):
            return False

    return True


# =====================================================================
# Online Hot Backup Utility
# =====================================================================

def backup_database(
    db_path: Union[str, Path],
    target_path: Optional[Union[str, Path]] = None,
) -> Path:
    """Performs an online, non-blocking ACID hot backup using sqlite3.backup()."""
    source = Path(db_path).resolve()
    if not source.is_file():
        raise StorageError(f"Cannot backup non-existent database: {source}")

    if target_path:
        dest = Path(target_path).resolve()
    else:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        dest = source.parent / "backups" / f"experience_backup_{timestamp}.db"

    dest.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(str(source))) as src_conn:
        with closing(sqlite3.connect(str(dest))) as dst_conn:
            src_conn.backup(dst_conn)

    return dest


# =====================================================================
# Database Restore Utility
# =====================================================================

def restore_database(
    db_path: Union[str, Path],
    backup_path: Union[str, Path],
    force: bool = False,
    create_pre_restore_backup: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Restores the experience database from a backup file.

    Safety guarantees:
    - Requires force=True as explicit confirmation.
    - Validates backup integrity before restore (PRAGMA quick_check).
    - Creates automatic pre-restore backup unless disabled.
    - Uses sqlite3.backup() for atomic restore.

    Returns:
        Dict with status, paths, and diagnostic information.
    """
    source_backup = Path(backup_path).resolve()
    target_db = Path(db_path).resolve()

    if not source_backup.is_file():
        raise StorageError(f"Backup file not found: {source_backup}")

    # Validate backup is a valid SQLite database
    try:
        with closing(sqlite3.connect(str(source_backup))) as check_conn:
            check_conn.row_factory = sqlite3.Row
            cursor = check_conn.cursor()
            cursor.execute("PRAGMA quick_check;")
            check_result = cursor.fetchone()
            if check_result is None or str(check_result[0]).lower() != "ok":
                raise StorageError(f"Backup file failed integrity check: {source_backup}")

            # Verify it has our schema_migrations table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations';"
            )
            if cursor.fetchone() is None:
                raise StorageError(
                    f"Backup file does not contain AntiOS experience schema: {source_backup}"
                )

            cursor.execute("SELECT version FROM schema_migrations ORDER BY applied_at DESC LIMIT 1;")
            version_row = cursor.fetchone()
            backup_version = str(version_row["version"]) if version_row else "unknown"
    except sqlite3.DatabaseError as e:
        raise StorageError(f"Backup file is not a valid SQLite database: {e}") from e

    result: Dict[str, Any] = {
        "status": "DRY_RUN" if dry_run else "PENDING",
        "backup_source": str(source_backup),
        "target_db": str(target_db),
        "backup_schema_version": backup_version,
        "target_exists": target_db.is_file(),
        "pre_restore_backup": None,
    }

    if dry_run:
        result["status"] = "DRY_RUN"
        if target_db.is_file():
            result["target_size_bytes"] = target_db.stat().st_size
        result["backup_size_bytes"] = source_backup.stat().st_size
        return result

    if not force:
        raise StorageError(
            "Restore requires explicit confirmation. Pass force=True or use --confirm flag."
        )

    # Pre-restore backup
    if create_pre_restore_backup and target_db.is_file():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        pre_restore_path = target_db.parent / "backups" / f"pre_restore_{timestamp}.db"
        pre_restore_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            pre_backup = backup_database(target_db, pre_restore_path)
            result["pre_restore_backup"] = str(pre_backup)
        except Exception as e:
            raise StorageError(
                f"Pre-restore backup failed — aborting restore for safety: {e}"
            ) from e

    # Perform atomic restore using sqlite3.backup()
    try:
        with closing(sqlite3.connect(str(source_backup))) as src_conn:
            with closing(sqlite3.connect(str(target_db))) as dst_conn:
                src_conn.backup(dst_conn)
        result["status"] = "SUCCESS"
        result["restored_size_bytes"] = target_db.stat().st_size
    except Exception as e:
        raise StorageError(f"Restore operation failed: {e}") from e

    return result


# =====================================================================
# Experience Data Purge & Retention
# =====================================================================

def purge_experience_data(
    db_path: Union[str, Path],
    project_id: Optional[str] = None,
    purge_all: bool = False,
    older_than_days: Optional[int] = None,
    dry_run: bool = False,
    force: bool = False,
    create_backup: bool = True,
) -> Dict[str, Any]:
    """Purges experience data with mandatory tenant scoping and safety guarantees.

    Safety guarantees:
    - Requires explicit project_id or purge_all=True (no default-all).
    - Requires force=True as explicit confirmation (unless dry_run).
    - Creates pre-purge backup before any deletion.
    - Transactional deletion with foreign key cascade.
    - Post-purge incremental vacuum.

    Returns:
        Dict with affected counts and status.
    """
    db = Path(db_path).resolve()
    if not db.is_file():
        raise StorageError(f"Database not found: {db}")

    if not project_id and not purge_all:
        raise StorageError(
            "Purge requires explicit --project <id> or --all flag. "
            "Refusing to purge without explicit scope."
        )

    # Build WHERE clauses for tenant scoping
    where_clauses: Dict[str, str] = {}
    where_params: Dict[str, List[Any]] = {}

    if project_id and not purge_all:
        for table in ["sessions", "missions", "engineering_events", "ingestion_checkpoints"]:
            where_clauses[table] = "WHERE project_id = ?"
            where_params[table] = [project_id]
    else:
        for table in ["sessions", "missions", "engineering_events", "ingestion_checkpoints"]:
            where_clauses[table] = ""
            where_params[table] = []

    # Add time-based filter if specified
    if older_than_days is not None and older_than_days > 0:
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
        for table in ["sessions", "missions", "engineering_events"]:
            time_col = "started_at" if table == "sessions" else "created_at"
            if where_clauses[table]:
                where_clauses[table] += f" AND {time_col} < ?"
            else:
                where_clauses[table] = f"WHERE {time_col} < ?"
            where_params[table].append(cutoff)

    # Count affected rows
    counts: Dict[str, int] = {}
    with closing(get_db_connection(db)) as conn:
        cursor = conn.cursor()
        for table in ["sessions", "missions", "engineering_events", "ingestion_checkpoints"]:
            wc = where_clauses.get(table, "")
            p = where_params.get(table, [])
            cursor.execute(f"SELECT count(*) as cnt FROM {table} {wc};", p)
            counts[table] = cursor.fetchone()["cnt"]

        # Count turns and tool_calls via mission scope
        mission_wc = where_clauses.get("missions", "")
        mission_p = where_params.get("missions", [])
        if mission_wc:
            cursor.execute(
                f"SELECT count(*) as cnt FROM turns WHERE mission_id IN "
                f"(SELECT mission_id FROM missions {mission_wc});",
                mission_p,
            )
            counts["turns"] = cursor.fetchone()["cnt"]
            cursor.execute(
                f"SELECT count(*) as cnt FROM tool_calls WHERE turn_id IN "
                f"(SELECT turn_id FROM turns WHERE mission_id IN "
                f"(SELECT mission_id FROM missions {mission_wc}));",
                mission_p,
            )
            counts["tool_calls"] = cursor.fetchone()["cnt"]
        else:
            cursor.execute("SELECT count(*) as cnt FROM turns;")
            counts["turns"] = cursor.fetchone()["cnt"]
            cursor.execute("SELECT count(*) as cnt FROM tool_calls;")
            counts["tool_calls"] = cursor.fetchone()["cnt"]

    result: Dict[str, Any] = {
        "status": "DRY_RUN" if dry_run else "PENDING",
        "scope": project_id or "ALL",
        "older_than_days": older_than_days,
        "affected_counts": counts,
        "total_affected": sum(counts.values()),
        "pre_purge_backup": None,
    }

    if dry_run:
        return result

    if not force:
        raise StorageError(
            "Purge requires explicit confirmation. Pass force=True or use --confirm flag."
        )

    # Pre-purge backup
    if create_backup:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        pre_purge_path = db.parent / "backups" / f"pre_purge_{timestamp}.db"
        pre_purge_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            backup_path_result = backup_database(db, pre_purge_path)
            result["pre_purge_backup"] = str(backup_path_result)
        except Exception as e:
            raise StorageError(
                f"Pre-purge backup failed — aborting purge for safety: {e}"
            ) from e

    # Execute transactional deletion
    with closing(get_db_connection(db)) as conn:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE;")
        try:
            # Delete in dependency order: tool_calls -> turns -> events -> missions -> sessions -> checkpoints
            if mission_wc:
                cursor.execute(
                    f"DELETE FROM tool_calls WHERE turn_id IN "
                    f"(SELECT turn_id FROM turns WHERE mission_id IN "
                    f"(SELECT mission_id FROM missions {mission_wc}));",
                    mission_p,
                )
                cursor.execute(
                    f"DELETE FROM turns WHERE mission_id IN "
                    f"(SELECT mission_id FROM missions {mission_wc});",
                    mission_p,
                )
            else:
                cursor.execute("DELETE FROM tool_calls;")
                cursor.execute("DELETE FROM turns;")

            for table in ["engineering_events", "missions", "sessions", "ingestion_checkpoints"]:
                wc = where_clauses.get(table, "")
                p = where_params.get(table, [])
                cursor.execute(f"DELETE FROM {table} {wc};", p)

            # Purge-all also clears the projects table
            if purge_all and not project_id:
                cursor.execute("DELETE FROM projects;")

            cursor.execute("COMMIT;")
        except Exception as e:
            cursor.execute("ROLLBACK;")
            raise StorageError(f"Purge operation failed: {e}") from e

        # Post-purge space reclamation
        try:
            cursor.execute("PRAGMA incremental_vacuum;")
        except Exception:
            pass

    result["status"] = "SUCCESS"
    return result


# =====================================================================
# Database Vacuum & Maintenance
# =====================================================================

def vacuum_database(
    db_path: Union[str, Path],
    full: bool = False,
) -> Dict[str, Any]:
    """Runs vacuum/maintenance on the experience database.

    Args:
        db_path: Path to experience.db.
        full: If True, runs VACUUM (full rebuild). Otherwise PRAGMA incremental_vacuum.

    Returns:
        Dict with size_before, size_after, and reclaimed_bytes.
    """
    db = Path(db_path).resolve()
    if not db.is_file():
        raise StorageError(f"Database not found: {db}")

    size_before = db.stat().st_size

    with closing(sqlite3.connect(str(db))) as conn:
        cursor = conn.cursor()
        if full:
            cursor.execute("VACUUM;")
        else:
            cursor.execute("PRAGMA incremental_vacuum;")

    size_after = db.stat().st_size
    return {
        "status": "SUCCESS",
        "db_path": str(db),
        "mode": "FULL_VACUUM" if full else "INCREMENTAL_VACUUM",
        "size_before_bytes": size_before,
        "size_after_bytes": size_after,
        "reclaimed_bytes": max(0, size_before - size_after),
    }


# =====================================================================
# Raw Experience Data Export
# =====================================================================

def export_raw_experience(
    db_path: Union[str, Path],
    output_path: Union[str, Path],
    project_id: Optional[str] = None,
) -> Path:
    """Exports raw experience data as JSONL (one JSON object per line).

    Exports sessions, missions, turns, tool_calls, and engineering_events
    in a portable, inspectable format.

    Args:
        db_path: Path to experience.db.
        output_path: Destination file path (will be created/overwritten).
        project_id: Optional project scope filter.

    Returns:
        Path to the created export file.
    """
    db = Path(db_path).resolve()
    if not db.is_file():
        raise StorageError(f"Database not found: {db}")

    out = Path(output_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    tables_and_scopes = [
        ("projects", "project_id"),
        ("sessions", "project_id"),
        ("missions", "project_id"),
        ("turns", None),
        ("tool_calls", None),
        ("engineering_events", "project_id"),
        ("ingestion_checkpoints", "project_id"),
    ]

    with closing(get_db_connection(db)) as conn:
        cursor = conn.cursor()
        with open(out, "w", encoding="utf-8") as f:
            for table_name, scope_col in tables_and_scopes:
                if project_id and scope_col:
                    cursor.execute(
                        f"SELECT * FROM {table_name} WHERE {scope_col} = ? ORDER BY rowid;",
                        (project_id,),
                    )
                elif project_id and table_name == "turns":
                    cursor.execute(
                        "SELECT t.* FROM turns t JOIN missions m ON t.mission_id = m.mission_id "
                        "WHERE m.project_id = ? ORDER BY t.rowid;",
                        (project_id,),
                    )
                elif project_id and table_name == "tool_calls":
                    cursor.execute(
                        "SELECT tc.* FROM tool_calls tc JOIN turns t ON tc.turn_id = t.turn_id "
                        "JOIN missions m ON t.mission_id = m.mission_id "
                        "WHERE m.project_id = ? ORDER BY tc.rowid;",
                        (project_id,),
                    )
                else:
                    cursor.execute(f"SELECT * FROM {table_name} ORDER BY rowid;")

                for row in cursor.fetchall():
                    record = {"_table": table_name}
                    record.update(dict(row))
                    f.write(json.dumps(record, default=str) + "\n")

    return out




def get_storage_status(
    data_dir: Optional[Union[str, Path]] = None,
    project_root: Optional[Union[str, Path]] = None,
) -> StorageStatus:
    """Inspects the storage configuration and database health."""
    issues: List[str] = []

    # 1. Resolve data directory
    resolved_dir: Optional[Path] = None
    try:
        resolved_dir = AntiOSDataResolver.resolve_data_dir(
            project_root=project_root,
            explicit_dir=data_dir,
        )
    except DataDirectoryNotConfiguredError:
        return StorageStatus(
            is_configured=False,
            is_healthy=False,
            issues=["No AntiOS Data Directory configured. Specify --data-dir, set ANTIOS_DATA_DIR, or configure antios.config.json."],
        )
    except Exception as e:
        return StorageStatus(
            is_configured=False,
            is_healthy=False,
            issues=[f"Error resolving data directory: {e}"],
        )

    str_data_dir = str(resolved_dir)
    db_path = AntiOSDataResolver.resolve_experience_db(resolved_dir)
    str_db_path = str(db_path)

    if not resolved_dir.is_dir():
        return StorageStatus(
            is_configured=True,
            data_dir=str_data_dir,
            db_path=str_db_path,
            db_exists=False,
            is_healthy=False,
            issues=[f"Configured data directory does not exist on disk: {str_data_dir}"],
        )

    backups_exists = (resolved_dir / "backups").is_dir()
    exports_exists = (resolved_dir / "exports").is_dir()
    config_toml_exists = (resolved_dir / "config.toml").is_file()

    if not backups_exists:
        issues.append("Missing 'backups/' directory.")
    if not exports_exists:
        issues.append("Missing 'exports/' directory.")
    if not config_toml_exists:
        issues.append("Missing 'config.toml' configuration file.")

    if not db_path.is_file():
        issues.append(f"Authoritative experience.db not found at: {str_db_path}")
        return StorageStatus(
            is_configured=True,
            data_dir=str_data_dir,
            db_path=str_db_path,
            db_exists=False,
            backups_dir_exists=backups_exists,
            exports_dir_exists=exports_exists,
            config_toml_exists=config_toml_exists,
            is_healthy=False,
            issues=issues,
        )

    db_size = db_path.stat().st_size
    journal_mode = None
    synchronous = None
    busy_timeout = None
    foreign_keys = False
    schema_ver = None
    applied_migrations: List[str] = []
    table_counts: Dict[str, int] = {}
    project_registered = False
    proj_id = None
    proj_name = None

    try:
        with closing(get_db_connection(db_path)) as conn:
            cursor = conn.cursor()

            # Check PRAGMAs
            cursor.execute("PRAGMA journal_mode;")
            row = cursor.fetchone()
            journal_mode = row[0].upper() if row else None

            cursor.execute("PRAGMA synchronous;")
            row = cursor.fetchone()
            synchronous = int(row[0]) if row else None

            cursor.execute("PRAGMA busy_timeout;")
            row = cursor.fetchone()
            busy_timeout = int(row[0]) if row else None

            cursor.execute("PRAGMA foreign_keys;")
            row = cursor.fetchone()
            foreign_keys = bool(row[0]) if row else False

            # Verify journal mode
            if journal_mode != "WAL":
                issues.append(f"Database journal_mode is '{journal_mode}', expected 'WAL'.")

            # Check schema migrations
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations';"
            )
            if cursor.fetchone():
                cursor.execute("SELECT version FROM schema_migrations ORDER BY applied_at ASC;")
                applied_migrations = [r["version"] for r in cursor.fetchall()]
                if applied_migrations:
                    schema_ver = applied_migrations[-1]
            else:
                issues.append("schema_migrations table missing.")

            # Table counts
            standard_tables = [
                "projects",
                "sessions",
                "missions",
                "turns",
                "tool_calls",
                "engineering_events",
            ]
            for tbl in standard_tables:
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name = ?;", (tbl,)
                )
                if cursor.fetchone():
                    cursor.execute(f"SELECT count(*) as cnt FROM {tbl};")
                    table_counts[tbl] = cursor.fetchone()["cnt"]
                else:
                    issues.append(f"Required table '{tbl}' is missing.")

            # Project registration check
            if project_root:
                root = Path(project_root).resolve()
                proj_id, proj_name = AntiOSDataResolver.resolve_project_identity(root)
                canonical_path = AntiOSDataResolver.normalize_path(root)
                cursor.execute(
                    "SELECT project_id FROM projects WHERE canonical_path = ? OR project_id = ?;",
                    (canonical_path, proj_id),
                )
                reg_row = cursor.fetchone()
                project_registered = reg_row is not None
                if not project_registered:
                    issues.append(f"Project '{proj_name}' ({proj_id}) is not registered in experience.db.")

    except Exception as e:
        issues.append(f"Database inspection error: {e}")

    is_healthy = len(issues) == 0

    return StorageStatus(
        is_configured=True,
        data_dir=str_data_dir,
        db_path=str_db_path,
        db_exists=True,
        db_size_bytes=db_size,
        schema_version=schema_ver,
        applied_migrations=applied_migrations,
        journal_mode=journal_mode,
        synchronous=synchronous,
        busy_timeout=busy_timeout,
        foreign_keys=foreign_keys,
        project_registered=project_registered,
        project_id=proj_id,
        project_name=proj_name,
        table_counts=table_counts,
        backups_dir_exists=backups_exists,
        exports_dir_exists=exports_exists,
        config_toml_exists=config_toml_exists,
        is_healthy=is_healthy,
        issues=issues,
    )


# =====================================================================
# Ingestion Checkpoint & Experience Repository (Phase 105)
# =====================================================================

@dataclass
class IngestionCheckpoint:
    """Tracks incremental ingestion position for a transcript source."""
    checkpoint_id: str
    project_id: str
    session_id: str
    source_type: str  # transcript_jsonl, transcript_full_jsonl, hook_metadata, cli_stream
    source_path: str
    last_byte_offset: int = 0
    last_step_idx: int = -1
    file_sha256: Optional[str] = None
    file_size_bytes: int = 0
    records_ingested: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExperienceRepository:
    """ACID-compliant repository for persisting and querying engineering telemetry."""

    def __init__(self, db_path: Union[str, Path], timeout: float = 5.0):
        self.db_path = Path(db_path).resolve()
        self.timeout = timeout
        # Ensure database and tables exist
        init_experience_db(self.db_path)

    def record_session(
        self,
        session_id: str,
        project_id: str,
        surface: str = "DESKTOP",
        started_at: Optional[str] = None,
        ended_at: Optional[str] = None,
        total_turns: int = 0,
        token_usage_json: str = "{}",
        metadata_json: str = "{}",
    ) -> None:
        """Upserts a session record."""
        now_utc = datetime.now(timezone.utc).isoformat()
        start = started_at or now_utc

        with closing(get_db_connection(self.db_path, timeout=self.timeout)) as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                cursor.execute(
                    """INSERT INTO sessions 
                       (session_id, project_id, surface, started_at, ended_at, total_turns, token_usage_json, metadata_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(session_id) DO UPDATE SET
                           ended_at = COALESCE(excluded.ended_at, sessions.ended_at),
                           total_turns = MAX(sessions.total_turns, excluded.total_turns),
                           token_usage_json = CASE WHEN excluded.token_usage_json != '{}' THEN excluded.token_usage_json ELSE sessions.token_usage_json END,
                           metadata_json = CASE WHEN excluded.metadata_json != '{}' THEN excluded.metadata_json ELSE sessions.metadata_json END;""",
                    (session_id, project_id, surface, start, ended_at, total_turns, token_usage_json, metadata_json),
                )
                cursor.execute("COMMIT;")
            except Exception as e:
                cursor.execute("ROLLBACK;")
                raise StorageError(f"Failed to record session {session_id}: {e}") from e

    def record_mission(
        self,
        mission_id: str,
        session_id: str,
        project_id: str,
        intent_query: Optional[str] = None,
        task_class: Optional[str] = None,
        risk_tier: Optional[str] = None,
        workforce_mode: Optional[str] = None,
        status: str = "ACTIVE",
        stop_gate_exit_code: Optional[int] = None,
        created_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        metadata_json: str = "{}",
    ) -> None:
        """Upserts a mission record."""
        now_utc = datetime.now(timezone.utc).isoformat()
        created = created_at or now_utc

        with closing(get_db_connection(self.db_path, timeout=self.timeout)) as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                cursor.execute(
                    """INSERT INTO missions 
                       (mission_id, session_id, project_id, intent_query, task_class, risk_tier, workforce_mode, status, stop_gate_exit_code, created_at, completed_at, metadata_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(mission_id) DO UPDATE SET
                           status = excluded.status,
                           stop_gate_exit_code = COALESCE(excluded.stop_gate_exit_code, missions.stop_gate_exit_code),
                           completed_at = COALESCE(excluded.completed_at, missions.completed_at),
                           metadata_json = CASE WHEN excluded.metadata_json != '{}' THEN excluded.metadata_json ELSE missions.metadata_json END;""",
                    (mission_id, session_id, project_id, intent_query, task_class, risk_tier, workforce_mode, status, stop_gate_exit_code, created, completed_at, metadata_json),
                )
                cursor.execute("COMMIT;")
            except Exception as e:
                cursor.execute("ROLLBACK;")
                raise StorageError(f"Failed to record mission {mission_id}: {e}") from e

    def record_turn(
        self,
        turn_id: str,
        mission_id: str,
        step_idx: int,
        agent_role: str = "PrimaryEngineer",
        agent_conversation_id: Optional[str] = None,
        duration_ms: int = 0,
        created_at: Optional[str] = None,
        metadata_json: str = "{}",
    ) -> None:
        """Upserts a turn record."""
        now_utc = datetime.now(timezone.utc).isoformat()
        created = created_at or now_utc

        with closing(get_db_connection(self.db_path, timeout=self.timeout)) as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                cursor.execute(
                    """INSERT INTO turns 
                       (turn_id, mission_id, step_idx, agent_role, agent_conversation_id, duration_ms, created_at, metadata_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(turn_id) DO UPDATE SET
                           duration_ms = MAX(turns.duration_ms, excluded.duration_ms),
                           metadata_json = CASE WHEN excluded.metadata_json != '{}' THEN excluded.metadata_json ELSE turns.metadata_json END;""",
                    (turn_id, mission_id, step_idx, agent_role, agent_conversation_id, duration_ms, created, metadata_json),
                )
                cursor.execute("COMMIT;")
            except Exception as e:
                cursor.execute("ROLLBACK;")
                raise StorageError(f"Failed to record turn {turn_id}: {e}") from e

    def record_tool_call(self, tool_call: SafeToolCall) -> bool:
        """Records a single sanitized tool call. Returns True if inserted, False if already existed."""
        with closing(get_db_connection(self.db_path, timeout=self.timeout)) as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                cursor.execute(
                    """INSERT OR IGNORE INTO tool_calls 
                       (call_id, turn_id, tool_name, sanitized_args_json, exit_code, status, output_sha256, output_summary, duration_ms, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                    (
                        tool_call.call_id,
                        tool_call.turn_id,
                        tool_call.tool_name,
                        tool_call.sanitized_args_json,
                        tool_call.exit_code,
                        tool_call.status,
                        tool_call.output_sha256,
                        tool_call.output_summary,
                        tool_call.duration_ms,
                        tool_call.created_at,
                    ),
                )
                inserted = cursor.rowcount > 0
                cursor.execute("COMMIT;")
                return inserted
            except Exception as e:
                cursor.execute("ROLLBACK;")
                raise StorageError(f"Failed to record tool call {tool_call.call_id}: {e}") from e

    def record_tool_calls(self, tool_calls: List[SafeToolCall]) -> int:
        """Batch records sanitized tool calls. Returns count of newly inserted records."""
        if not tool_calls:
            return 0
        inserted_count = 0
        with closing(get_db_connection(self.db_path, timeout=self.timeout)) as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                for tc in tool_calls:
                    cursor.execute(
                        """INSERT OR IGNORE INTO tool_calls 
                           (call_id, turn_id, tool_name, sanitized_args_json, exit_code, status, output_sha256, output_summary, duration_ms, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                        (
                            tc.call_id,
                            tc.turn_id,
                            tc.tool_name,
                            tc.sanitized_args_json,
                            tc.exit_code,
                            tc.status,
                            tc.output_sha256,
                            tc.output_summary,
                            tc.duration_ms,
                            tc.created_at,
                        ),
                    )
                    if cursor.rowcount > 0:
                        inserted_count += 1
                cursor.execute("COMMIT;")
            except Exception as e:
                cursor.execute("ROLLBACK;")
                raise StorageError(f"Failed to record batch tool calls: {e}") from e
        return inserted_count

    def record_engineering_event(self, event: SafeEngineeringEvent) -> bool:
        """Records a single sanitized engineering event with deterministic deduplication.
        
        Returns True if inserted, False if duplicate.
        """
        with closing(get_db_connection(self.db_path, timeout=self.timeout)) as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                # Deduplication check via event_signature if present
                if event.event_signature:
                    cursor.execute(
                        "SELECT 1 FROM engineering_events WHERE project_id = ? AND event_signature = ?;",
                        (event.project_id, event.event_signature),
                    )
                    if cursor.fetchone():
                        cursor.execute("COMMIT;")
                        return False

                cursor.execute(
                    """INSERT OR IGNORE INTO engineering_events 
                       (event_id, mission_id, project_id, event_type, epistemic_grade, affected_file, event_signature, payload_json, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                    (
                        event.event_id,
                        event.mission_id,
                        event.project_id,
                        event.event_type,
                        event.epistemic_grade,
                        event.affected_file,
                        event.event_signature,
                        event.payload_json,
                        event.created_at,
                    ),
                )
                inserted = cursor.rowcount > 0
                cursor.execute("COMMIT;")
                return inserted
            except Exception as e:
                cursor.execute("ROLLBACK;")
                raise StorageError(f"Failed to record engineering event {event.event_id}: {e}") from e

    def record_engineering_events(self, events: List[SafeEngineeringEvent]) -> int:
        """Batch records sanitized engineering events with signature deduplication.
        
        Returns count of newly inserted events.
        """
        if not events:
            return 0
        inserted_count = 0
        with closing(get_db_connection(self.db_path, timeout=self.timeout)) as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                for ev in events:
                    if ev.event_signature:
                        cursor.execute(
                            "SELECT 1 FROM engineering_events WHERE project_id = ? AND event_signature = ?;",
                            (ev.project_id, ev.event_signature),
                        )
                        if cursor.fetchone():
                            continue

                    cursor.execute(
                        """INSERT OR IGNORE INTO engineering_events 
                           (event_id, mission_id, project_id, event_type, epistemic_grade, affected_file, event_signature, payload_json, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                        (
                            ev.event_id,
                            ev.mission_id,
                            ev.project_id,
                            ev.event_type,
                            ev.epistemic_grade,
                            ev.affected_file,
                            ev.event_signature,
                            ev.payload_json,
                            ev.created_at,
                        ),
                    )
                    if cursor.rowcount > 0:
                        inserted_count += 1
                cursor.execute("COMMIT;")
            except Exception as e:
                cursor.execute("ROLLBACK;")
                raise StorageError(f"Failed to record batch engineering events: {e}") from e
        return inserted_count

    def save_checkpoint(self, checkpoint: IngestionCheckpoint) -> None:
        """Persists or updates an ingestion checkpoint."""
        with closing(get_db_connection(self.db_path, timeout=self.timeout)) as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                cursor.execute(
                    """INSERT INTO ingestion_checkpoints 
                       (checkpoint_id, project_id, session_id, source_type, source_path, last_byte_offset, last_step_idx, file_sha256, file_size_bytes, records_ingested, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(checkpoint_id) DO UPDATE SET
                           last_byte_offset = excluded.last_byte_offset,
                           last_step_idx = excluded.last_step_idx,
                           file_sha256 = excluded.file_sha256,
                           file_size_bytes = excluded.file_size_bytes,
                           records_ingested = excluded.records_ingested,
                           updated_at = excluded.updated_at;""",
                    (
                        checkpoint.checkpoint_id,
                        checkpoint.project_id,
                        checkpoint.session_id,
                        checkpoint.source_type,
                        checkpoint.source_path,
                        checkpoint.last_byte_offset,
                        checkpoint.last_step_idx,
                        checkpoint.file_sha256,
                        checkpoint.file_size_bytes,
                        checkpoint.records_ingested,
                        checkpoint.updated_at or datetime.now(timezone.utc).isoformat(),
                    ),
                )
                cursor.execute("COMMIT;")
            except Exception as e:
                cursor.execute("ROLLBACK;")
                raise StorageError(f"Failed to save checkpoint {checkpoint.checkpoint_id}: {e}") from e

    def load_checkpoint(self, checkpoint_id: str) -> Optional[IngestionCheckpoint]:
        """Loads an ingestion checkpoint by ID."""
        with closing(get_db_connection(self.db_path, timeout=self.timeout)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT checkpoint_id, project_id, session_id, source_type, source_path, 
                          last_byte_offset, last_step_idx, file_sha256, file_size_bytes, records_ingested, updated_at
                   FROM ingestion_checkpoints WHERE checkpoint_id = ?;""",
                (checkpoint_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return IngestionCheckpoint(
                checkpoint_id=row["checkpoint_id"],
                project_id=row["project_id"],
                session_id=row["session_id"],
                source_type=row["source_type"],
                source_path=row["source_path"],
                last_byte_offset=row["last_byte_offset"],
                last_step_idx=row["last_step_idx"],
                file_sha256=row["file_sha256"],
                file_size_bytes=row["file_size_bytes"],
                records_ingested=row["records_ingested"],
                updated_at=row["updated_at"],
            )

    def load_session_checkpoint(
        self, session_id: str, source_type: str = "transcript_jsonl"
    ) -> Optional[IngestionCheckpoint]:
        """Loads the most recent checkpoint for a given session and source type."""
        with closing(get_db_connection(self.db_path, timeout=self.timeout)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT checkpoint_id, project_id, session_id, source_type, source_path, 
                          last_byte_offset, last_step_idx, file_sha256, file_size_bytes, records_ingested, updated_at
                   FROM ingestion_checkpoints 
                   WHERE session_id = ? AND source_type = ?
                   ORDER BY updated_at DESC LIMIT 1;""",
                (session_id, source_type),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return IngestionCheckpoint(
                checkpoint_id=row["checkpoint_id"],
                project_id=row["project_id"],
                session_id=row["session_id"],
                source_type=row["source_type"],
                source_path=row["source_path"],
                last_byte_offset=row["last_byte_offset"],
                last_step_idx=row["last_step_idx"],
                file_sha256=row["file_sha256"],
                file_size_bytes=row["file_size_bytes"],
                records_ingested=row["records_ingested"],
                updated_at=row["updated_at"],
            )

    def query_events(
        self,
        project_id: str,
        event_type: Optional[str] = None,
        session_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Queries engineering events with mandatory project tenant scoping."""
        query = ["SELECT * FROM engineering_events WHERE project_id = ?"]
        params: List[Any] = [project_id]

        if event_type:
            query.append("AND event_type = ?")
            params.append(event_type)
        if mission_id:
            query.append("AND mission_id = ?")
            params.append(mission_id)
        if session_id:
            query.append("AND mission_id IN (SELECT mission_id FROM missions WHERE session_id = ?)")
            params.append(session_id)

        query.append("ORDER BY created_at ASC LIMIT ?;")
        params.append(limit)

        with closing(get_db_connection(self.db_path, timeout=self.timeout)) as conn:
            cursor = conn.cursor()
            cursor.execute(" ".join(query), params)
            return [dict(row) for row in cursor.fetchall()]

    def query_tool_calls(
        self,
        turn_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Queries tool calls."""
        query = ["SELECT * FROM tool_calls WHERE 1=1"]
        params: List[Any] = []

        if turn_id:
            query.append("AND turn_id = ?")
            params.append(turn_id)
        if tool_name:
            query.append("AND tool_name = ?")
            params.append(tool_name)
        if status:
            query.append("AND status = ?")
            params.append(status)

        query.append("ORDER BY created_at ASC LIMIT ?;")
        params.append(limit)

        with closing(get_db_connection(self.db_path, timeout=self.timeout)) as conn:
            cursor = conn.cursor()
            cursor.execute(" ".join(query), params)
            return [dict(row) for row in cursor.fetchall()]

    def query_sessions(self, project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Queries sessions scoped to project_id."""
        with closing(get_db_connection(self.db_path, timeout=self.timeout)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions WHERE project_id = ? ORDER BY started_at DESC LIMIT ?;",
                (project_id, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def query_missions(
        self, project_id: str, session_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Queries missions scoped to project_id."""
        query = ["SELECT * FROM missions WHERE project_id = ?"]
        params: List[Any] = [project_id]

        if session_id:
            query.append("AND session_id = ?")
            params.append(session_id)

        query.append("ORDER BY created_at DESC LIMIT ?;")
        params.append(limit)

        with closing(get_db_connection(self.db_path, timeout=self.timeout)) as conn:
            cursor = conn.cursor()
            cursor.execute(" ".join(query), params)
            return [dict(row) for row in cursor.fetchall()]

    def query_turns(self, mission_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Queries turns scoped to mission_id."""
        with closing(get_db_connection(self.db_path, timeout=self.timeout)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM turns WHERE mission_id = ? ORDER BY step_idx ASC LIMIT ?;",
                (mission_id, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def count_records(self, table_name: str, project_id: Optional[str] = None) -> int:
        """Returns record count for a table, optionally filtered by project_id."""
        allowed_tables = {
            "projects",
            "sessions",
            "missions",
            "turns",
            "tool_calls",
            "engineering_events",
            "ingestion_checkpoints",
        }
        if table_name not in allowed_tables:
            raise StorageError(f"Table '{table_name}' is not an allowed telemetry table.")

        with closing(get_db_connection(self.db_path, timeout=self.timeout)) as conn:
            cursor = conn.cursor()
            if project_id and table_name in {"sessions", "missions", "engineering_events", "ingestion_checkpoints"}:
                cursor.execute(f"SELECT count(*) as cnt FROM {table_name} WHERE project_id = ?;", (project_id,))
            else:
                cursor.execute(f"SELECT count(*) as cnt FROM {table_name};")
            return cursor.fetchone()["cnt"]

