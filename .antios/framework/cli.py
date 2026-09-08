"""AntiOS 2.0 Unified CLI Entrypoint.

The canonical control surface for AntiOS Project Agent OS:
  antios version [--json]
  antios status [--json]
  antios doctor [--json]
  antios install [--version <V>] [--force-downgrade] [--dry-run]
  antios update [--check] [--version <V>] [--dry-run]
  antios rollback [--version <V>] [--dry-run]
  antios repair [--check] [--plan] [--apply] [--dry-run]
  antios remove / antios uninstall [--dry-run]
  antios adapt [--dry-run]
  antios verify [--json]
  antios issue {discover,classify,create,triage}
  antios release {check,notes} [--json]
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

from framework.core.adapter import analyze_adaptation, apply_project_adaptation, verify_adapter
from framework.core.discovery import discover_project
from framework.core.doctor import DoctorEngine
from framework.core.experience import (
    AntiOSDataResolver,
    StorageError,
    backup_database,
    export_raw_experience,
    get_storage_status,
    init_data_directory,
    init_experience_db,
    purge_experience_data,
    register_project,
    restore_database,
    vacuum_database,
)
from framework.core.experience_analytics import (
    ExperienceAnalyticsEngine,
    ExperienceExporter,
)
from framework.core.git_capability import GitCapabilityEngine
from framework.core.github_capability import GitHubCapabilityEngine, IssueClass, IssueEvidence
from framework.core.installation import InstallationLifecycleManager
from framework.core.manifest import load_manifest, save_manifest
from framework.core.release_engine import ReleaseEngine
from framework.core.telemetry_bridge import (
    AntigravityEventBridge,
    TelemetryCollectionMode,
    TelemetryConfigResolver,
)
from framework.core.version import (
    ANTIOS_VERSION,
    compare_versions,
    get_version_info,
)


def _resolve_target(args: argparse.Namespace) -> Path:
    """Resolves target directory from CLI arguments or cwd."""
    p = getattr(args, "path", None)
    if p:
        return Path(p).resolve()
    return Path.cwd().resolve()


def _resolve_source() -> Path:
    """Resolves the root directory of the AntiOS framework."""
    # framework/cli.py -> framework/ -> repository root
    return Path(__file__).resolve().parent.parent


# ==========================================
# Command Handlers
# ==========================================

def cmd_version(args: argparse.Namespace) -> int:
    target = _resolve_target(args)
    info = get_version_info(target)
    if getattr(args, "json", False):
        print(json.dumps(info.to_dict(), indent=2))
    else:
        print(info.format_human())
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    target = _resolve_target(args)
    doc_eng = DoctorEngine(target)
    stat = doc_eng.get_status()
    if getattr(args, "json", False):
        print(json.dumps(stat.to_dict(), indent=2))
    else:
        print(stat.format_human())
    return 0 if stat.is_healthy else 1


def cmd_doctor(args: argparse.Namespace) -> int:
    target = _resolve_target(args)
    doc_eng = DoctorEngine(target)
    rep = doc_eng.run_doctor()
    if getattr(args, "json", False):
        print(json.dumps(rep.to_dict(), indent=2))
    else:
        print(rep.format_human())
    return 0 if rep.is_healthy else 1


def cmd_install(args: argparse.Namespace) -> int:
    target = _resolve_target(args)
    source = _resolve_source()
    mgr = InstallationLifecycleManager(source_root=source, target_root=target)

    res = mgr.install(
        dry_run=getattr(args, "dry_run", False),
        force=getattr(args, "force", False),
        target_version=getattr(args, "version", None),
        force_downgrade=getattr(args, "force_downgrade", False),
        data_dir=getattr(args, "data_dir", None),
    )

    if getattr(args, "json", False):
        print(json.dumps(res.to_dict(), indent=2))
    else:
        print(f"[{res.status}] {res.summary}")
        if res.issues:
            for issue in res.issues:
                print(f"  - Issue: {issue}")
    return 0 if res.status in ("SUCCESS", "IDEMPOTENT") else 1


def cmd_upgrade(args: argparse.Namespace) -> int:
    target = _resolve_target(args)
    source = _resolve_source()
    mgr = InstallationLifecycleManager(source_root=source, target_root=target)

    is_plan = getattr(args, "plan", False)
    is_check = getattr(args, "check", False)
    dry_run = getattr(args, "dry_run", False) or is_check
    force = getattr(args, "force", False)
    target_v = getattr(args, "version", None)

    res = mgr.upgrade(
        target_version=target_v,
        dry_run=dry_run,
        plan_only=is_plan,
        force=force,
    )

    if getattr(args, "json", False):
        print(json.dumps(res.to_dict(), indent=2))
    else:
        print(f"[{res.status}] {res.summary}")
        if res.conflicts:
            print("Conflicts:")
            for c in res.conflicts:
                print(f"  ! {c}")
        if res.issues:
            print("Issues:")
            for issue in res.issues:
                print(f"  - {issue}")
    return 0 if res.status in ("SUCCESS", "IDEMPOTENT") else 1

def cmd_update(args: argparse.Namespace) -> int:
    target = _resolve_target(args)
    source = _resolve_source()
    mgr = InstallationLifecycleManager(source_root=source, target_root=target)

    target_ver = getattr(args, "version", None)
    if getattr(args, "check", False):
        # Read-only update check
        doc_eng = DoctorEngine(target)
        stat = doc_eng.get_status()
        ver_info = get_version_info(target)
        if getattr(args, "json", False):
            print(json.dumps({
                "updates_available": stat.updates_available,
                "current_instance_version": stat.version,
                "framework_version": ver_info.version,
            }, indent=2))
        else:
            if stat.updates_available:
                print(f"Update available: {stat.version} -> {ver_info.version}. Run 'antios update'.")
            else:
                print(f"AntiOS is already up to date ({ver_info.version}).")
        return 0

    rev = f"v{target_ver}" if target_ver else None
    res = mgr.update(new_revision=rev, dry_run=getattr(args, "dry_run", False))

    if getattr(args, "json", False):
        print(json.dumps(res.to_dict(), indent=2))
    else:
        print(f"[{res.status}] {res.summary}")
        if res.issues:
            for issue in res.issues:
                print(f"  - {issue}")
    return 0 if res.status == "SUCCESS" else 1


def cmd_rollback(args: argparse.Namespace) -> int:
    target = _resolve_target(args)
    source = _resolve_source()
    mgr = InstallationLifecycleManager(source_root=source, target_root=target)

    res = mgr.rollback(
        target_version=getattr(args, "version", None),
        dry_run=getattr(args, "dry_run", False),
    )

    if getattr(args, "json", False):
        print(json.dumps(res.to_dict(), indent=2))
    else:
        print(f"[{res.status}] {res.summary}")
        if res.issues:
            for issue in res.issues:
                print(f"  - {issue}")
    return 0 if res.status == "SUCCESS" else 1


def cmd_repair(args: argparse.Namespace) -> int:
    target = _resolve_target(args)
    source = _resolve_source()
    mgr = InstallationLifecycleManager(source_root=source, target_root=target)

    is_apply = getattr(args, "apply", False)
    is_plan = getattr(args, "plan", False)
    is_check = getattr(args, "check", False)

    if is_apply and (is_plan or is_check):
        if getattr(args, "json", False):
            print(json.dumps({"status": "ERROR", "error": "--apply cannot be combined with --plan or --check."}, indent=2))
        else:
            print("Error: --apply cannot be combined with --plan or --check.")
        return 1

    plan_only = is_plan or is_check
    dry_run = getattr(args, "dry_run", False) or plan_only

    res = mgr.repair(dry_run=dry_run, plan_only=plan_only)

    if getattr(args, "json", False):
        print(json.dumps(res.to_dict(), indent=2))
    else:
        print(f"[{res.status}] {res.summary}")
        if res.written_files:
            print(f"Files affected: {len(res.written_files)}")
            for f in res.written_files[:10]:
                print(f"  - {f}")
    return 0 if res.status == "SUCCESS" else 1


def cmd_remove(args: argparse.Namespace) -> int:
    target = _resolve_target(args)
    source = _resolve_source()
    mgr = InstallationLifecycleManager(source_root=source, target_root=target)

    res = mgr.remove(dry_run=getattr(args, "dry_run", False))

    if getattr(args, "json", False):
        print(json.dumps(res.to_dict(), indent=2))
    else:
        print(f"[{res.status}] {res.summary}")
        if res.issues:
            for issue in res.issues:
                print(f"  - Warning: {issue}")
    return 0 if res.status == "SUCCESS" else 1


def cmd_adapt(args: argparse.Namespace) -> int:
    target = _resolve_target(args)
    source = _resolve_source()
    mgr = InstallationLifecycleManager(source_root=source, target_root=target)

    res = mgr.adapt(dry_run=getattr(args, "dry_run", False))

    if getattr(args, "json", False):
        print(json.dumps(res.to_dict(), indent=2))
    else:
        print(f"[{res.status}] {res.summary}")
    return 0 if res.status == "SUCCESS" else 1


def cmd_verify(args: argparse.Namespace) -> int:
    target = _resolve_target(args)
    source = _resolve_source()
    mgr = InstallationLifecycleManager(source_root=source, target_root=target)

    res = mgr.verify()

    if getattr(args, "json", False):
        print(json.dumps(res.to_dict(), indent=2))
    else:
        print(f"[{res.status}] {res.summary}")
        if res.issues:
            for issue in res.issues:
                print(f"  - {issue}")
    return 0 if res.status == "SUCCESS" else 1


def cmd_compile(args: argparse.Namespace) -> int:
    target = _resolve_target(args)
    check_mode = getattr(args, "check", False) or getattr(args, "dry_run", False)
    force = getattr(args, "force", False)
    as_json = getattr(args, "json", False)

    from framework.compiler.compiler import ProjectEnvironmentCompiler
    compiler = ProjectEnvironmentCompiler()
    result = compiler.compile(project_root=target, check=check_mode, force=force)

    if as_json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        status_label = "CHECK" if check_mode else ("SUCCESS" if result.success else "FAILED")
        print(f"[{status_label}] Project compiled: {result.project_id}")
        print(f"  Subsystems: {result.subsystems_count}")
        print(f"  Emitted artifacts: {len(result.emitted_files)}")
        for ef in result.emitted_files:
            print(f"    - {ef}")
        if result.warnings:
            print("  Warnings:")
            for w in result.warnings:
                print(f"    ! {w}")
        print(f"  Time: {result.elapsed_ms:.1f}ms")

    return 0 if result.success else 1


def cmd_issue(args: argparse.Namespace) -> int:
    target = _resolve_target(args)
    gh_eng = GitHubCapabilityEngine(target)
    sub = getattr(args, "issue_action", None)

    if sub == "triage":
        desc = getattr(args, "description", "")
        verdict = gh_eng.triage_feature_request(desc)
        if getattr(args, "json", False):
            print(json.dumps(verdict, indent=2))
        else:
            print(f"Feature Triage Verdict: {verdict['verdict']}")
            print(f"Permitted in 2.x:      {'Yes' if verdict['is_permitted_in_2_x'] else 'No'}")
            print(f"Reason:                {verdict['reason']}")
            print(f"Guidance:              {verdict['guidance']}")
        return 0

    if sub == "discover":
        query = getattr(args, "query", "")
        dups = gh_eng.search_duplicate_issues(query)
        if getattr(args, "json", False):
            print(json.dumps(dups, indent=2))
        else:
            if dups:
                print(f"Found {len(dups)} matching issue(s):")
                for d in dups:
                    print(f"  - #{d.get('number')}: {d.get('title')} ({d.get('state')})")
            else:
                print("No duplicate issues discovered.")
        return 0

    if sub == "create":
        title = getattr(args, "title", "Issue")
        iclass = getattr(args, "issue_class", "BUG").upper()
        try:
            ic = IssueClass(iclass)
        except ValueError:
            ic = IssueClass.BUG

        evidence = IssueEvidence(
            title=title,
            issue_class=ic,
            observed_behavior=getattr(args, "observed", "Observed failure."),
            expected_behavior=getattr(args, "expected", "Expected pass."),
            reproduction_steps=[getattr(args, "reproduce", "Run antios verify")],
            evidence_traces=[getattr(args, "trace", "Exit code 1")],
            affected_files=getattr(args, "files", []),
            anti_os_version=ANTIOS_VERSION,
        )
        print(evidence.to_markdown())
        return 0

    print("Usage: antios issue {discover,triage,create} ...")
    return 1


def cmd_release(args: argparse.Namespace) -> int:
    target = _resolve_target(args)
    rel_eng = ReleaseEngine(target)
    sub = getattr(args, "release_action", "check")

    if sub == "check":
        skip_tests = getattr(args, "skip_tests", False)
        rep = rel_eng.run_release_checks(skip_slow_tests=skip_tests)
        if getattr(args, "json", False):
            print(json.dumps(rep.to_dict(), indent=2))
        else:
            print(rep.format_human())
        return 0 if rep.is_ready_for_release else 1

    if sub == "notes":
        notes = rel_eng.generate_release_notes(getattr(args, "version", None))
        print(notes)
        return 0

    print("Usage: antios release {check,notes} ...")
    return 1


def cmd_data(args: argparse.Namespace) -> int:
    target = _resolve_target(args)
    action = getattr(args, "data_action", None) or "status"

    def _emit_error(msg: Any) -> int:
        if getattr(args, "json", False):
            print(json.dumps({"status": "ERROR", "error": str(msg)}, indent=2))
        else:
            print(f"Error: {msg}")
        return 1

    if action == "status":
        explicit_dd = getattr(args, "data_dir", None)
        stat = get_storage_status(data_dir=explicit_dd, project_root=target)
        if getattr(args, "json", False):
            print(json.dumps(stat.to_dict(), indent=2))
        else:
            print("=" * 60)
            print("AntiOS Local Engineering Intelligence: Storage Status")
            print("=" * 60)
            print(f"Configured:             {'Yes' if stat.is_configured else 'No'}")
            if stat.data_dir:
                print(f"Data Directory:         {stat.data_dir}")
            if stat.db_path:
                print(f"Experience Database:    {stat.db_path}")
            print(f"Database Exists:        {'Yes' if stat.db_exists else 'No'}")
            if stat.db_exists:
                print(f"Database Size:          {stat.db_size_bytes} bytes")
                print(f"Schema Version:         {stat.schema_version or 'unknown'}")
                print(f"Journal Mode:           {stat.journal_mode}")
                print(f"Synchronous:            {stat.synchronous}")
                print(f"Busy Timeout:           {stat.busy_timeout} ms")
                print(f"Foreign Keys:           {'ON' if stat.foreign_keys else 'OFF'}")
            if stat.project_id:
                print(f"Project Identity:       {stat.project_id} ({stat.project_name})")
                print(f"Project Registered:     {'Yes' if stat.project_registered else 'No'}")
            print(f"Backups Directory:      {'Present' if stat.backups_dir_exists else 'Missing'}")
            print(f"Exports Directory:      {'Present' if stat.exports_dir_exists else 'Missing'}")
            print(f"Config File:            {'Present' if stat.config_toml_exists else 'Missing'}")
            print(f"Storage Health:         {'HEALTHY' if stat.is_healthy else 'ATTENTION REQUIRED'}")
            if stat.table_counts:
                print("\nTable Statistics:")
                for tbl, cnt in stat.table_counts.items():
                    print(f"  - {tbl:<22}: {cnt} records")
            if stat.issues:
                print("\nIssues:")
                for issue in stat.issues:
                    print(f"  - {issue}")
            print("=" * 60)
        return 0 if stat.is_healthy else 1

    if action == "set-dir":
        new_dir = getattr(args, "directory", None)
        if not new_dir:
            return _emit_error("must specify directory path.")
        new_path = Path(new_dir).resolve()
        if new_path == target or target in new_path.parents:
            return _emit_error("AntiOS Data Directory cannot be located inside the target project repository.")

        # Establish directory & database
        target_dd, db_path = init_data_directory(new_path)
        init_experience_db(db_path)
        pid = register_project(db_path, target)

        # Update antios.config.json
        cfg_path = target / "antios.config.json"
        cfg_dict = {}
        if cfg_path.is_file():
            try:
                with open(cfg_path, "r", encoding="utf-8-sig") as f:
                    cfg_dict = json.load(f)
            except Exception:
                cfg_dict = {}
        cfg_dict["data_dir"] = str(target_dd)
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg_dict, f, indent=2)
        except Exception:
            pass

        # Update .antios/manifest.json if present
        manifest_file = target / ".antios" / "manifest.json"
        if manifest_file.is_file():
            try:
                manifest = load_manifest(target)
                if manifest:
                    manifest.metadata["data_dir"] = str(target_dd)
                    manifest.metadata["project_id"] = pid
                    if "antios.config.json" in manifest.managed_paths:
                        from framework.core.provenance import compute_file_sha256
                        manifest.managed_paths["antios.config.json"].sha256 = compute_file_sha256(cfg_path)
                    save_manifest(manifest, target)
            except Exception:
                pass

        if getattr(args, "json", False):
            print(json.dumps({
                "status": "SUCCESS",
                "data_dir": str(target_dd),
                "db_path": str(db_path),
                "project_id": pid,
            }, indent=2))
        else:
            print(f"[SUCCESS] Configured AntiOS Data Directory to: {target_dd}")
            print(f"Authoritative database: {db_path}")
            print(f"Project identity:       {pid}")
        return 0

    if action == "backup":
        try:
            context = AntiOSDataResolver.resolve_context(
                project_root=target,
                explicit_dir=getattr(args, "data_dir", None),
            )
        except Exception as e:
            return _emit_error(e)
        if not context.db_path.is_file():
            return _emit_error(f"Experience database does not exist: {context.db_path}")
        out = getattr(args, "output", None)
        try:
            result_path = backup_database(context.db_path, out)
            if getattr(args, "json", False):
                print(json.dumps({"status": "SUCCESS", "backup_path": str(result_path)}, indent=2))
            else:
                print(f"[SUCCESS] Backup created: {result_path}")
            return 0
        except Exception as e:
            return _emit_error(f"Backup failed: {e}")

    if action == "restore":
        try:
            context = AntiOSDataResolver.resolve_context(
                project_root=target,
                explicit_dir=getattr(args, "data_dir", None),
            )
        except Exception as e:
            return _emit_error(e)
        backup_file = getattr(args, "backup", None)
        if not backup_file:
            return _emit_error("--backup <path> is required for restore.")
        is_dry_run = getattr(args, "dry_run", False)
        is_confirmed = getattr(args, "confirm", False)
        try:
            result = restore_database(
                db_path=context.db_path,
                backup_path=backup_file,
                force=is_confirmed,
                dry_run=is_dry_run,
            )
            if getattr(args, "json", False):
                print(json.dumps(result, indent=2))
            else:
                if is_dry_run:
                    print("[DRY RUN] Restore preview:")
                    print(f"  Backup source:       {result['backup_source']}")
                    print(f"  Target database:     {result['target_db']}")
                    print(f"  Schema version:      {result['backup_schema_version']}")
                    if result.get("backup_size_bytes"):
                        print(f"  Backup size:         {result['backup_size_bytes']} bytes")
                else:
                    print(f"[SUCCESS] Database restored from: {result['backup_source']}")
                    if result.get("pre_restore_backup"):
                        print(f"  Pre-restore backup:  {result['pre_restore_backup']}")
            return 0
        except StorageError as e:
            return _emit_error(e)
        except Exception as e:
            return _emit_error(e)

    if action == "purge":
        try:
            context = AntiOSDataResolver.resolve_context(
                project_root=target,
                explicit_dir=getattr(args, "data_dir", None),
            )
        except Exception as e:
            return _emit_error(e)
        if not context.db_path.is_file():
            return _emit_error(f"Experience database does not exist: {context.db_path}")
        proj = getattr(args, "project", None)
        purge_all = getattr(args, "purge_all", False)
        older_than = getattr(args, "older_than", None)
        is_dry_run = getattr(args, "dry_run", False)
        is_confirmed = getattr(args, "confirm", False)
        try:
            result = purge_experience_data(
                db_path=context.db_path,
                project_id=proj,
                purge_all=purge_all,
                older_than_days=older_than,
                dry_run=is_dry_run,
                force=is_confirmed,
            )
            if getattr(args, "json", False):
                print(json.dumps(result, indent=2))
            else:
                if is_dry_run:
                    print("[DRY RUN] Purge preview:")
                    print(f"  Scope:               {result['scope']}")
                    if result['older_than_days']:
                        print(f"  Older than:          {result['older_than_days']} days")
                    print(f"  Affected records:")
                    for table, count in result['affected_counts'].items():
                        print(f"    - {table:<22}: {count}")
                    print(f"  Total:               {result['total_affected']}")
                else:
                    print(f"[SUCCESS] Purged {result['total_affected']} records (scope: {result['scope']})")
                    if result.get("pre_purge_backup"):
                        print(f"  Pre-purge backup:    {result['pre_purge_backup']}")
            return 0
        except StorageError as e:
            return _emit_error(e)
        except Exception as e:
            return _emit_error(e)

    if action == "vacuum":
        try:
            context = AntiOSDataResolver.resolve_context(
                project_root=target,
                explicit_dir=getattr(args, "data_dir", None),
            )
        except Exception as e:
            return _emit_error(e)
        if not context.db_path.is_file():
            return _emit_error(f"Experience database does not exist: {context.db_path}")
        is_full = getattr(args, "full", False)
        try:
            result = vacuum_database(context.db_path, full=is_full)
            if getattr(args, "json", False):
                print(json.dumps(result, indent=2))
            else:
                print(f"[SUCCESS] Vacuum completed ({result['mode']})")
                print(f"  Size before:         {result['size_before_bytes']} bytes")
                print(f"  Size after:          {result['size_after_bytes']} bytes")
                print(f"  Reclaimed:           {result['reclaimed_bytes']} bytes")
            return 0
        except Exception as e:
            return _emit_error(f"Vacuum failed: {e}")

    if action == "export":
        try:
            context = AntiOSDataResolver.resolve_context(
                project_root=target,
                explicit_dir=getattr(args, "data_dir", None),
            )
        except Exception as e:
            return _emit_error(e)
        if not context.db_path.is_file():
            return _emit_error(f"Experience database does not exist: {context.db_path}")
        proj = getattr(args, "project", None) or context.project_id
        out = getattr(args, "output", None)
        if not out:
            from datetime import datetime as _dt, timezone as _tz
            ts = _dt.now(_tz.utc).strftime("%Y%m%d_%H%M%S")
            out = context.data_dir / "exports" / f"raw_experience_{ts}.jsonl"
        try:
            result_path = export_raw_experience(context.db_path, out, project_id=proj)
            if getattr(args, "json", False):
                print(json.dumps({"status": "SUCCESS", "exported_path": str(result_path)}, indent=2))
            else:
                print(f"[SUCCESS] Raw experience exported to: {result_path}")
            return 0
        except Exception as e:
            return _emit_error(f"Export failed: {e}")

    print("Usage: antios data {status,set-dir,backup,restore,purge,vacuum,export} ...")
    return 1


def cmd_telemetry(args: argparse.Namespace) -> int:
    """Handles antios telemetry {status,enable,disable,ingest} commands."""
    target = _resolve_target(args)
    action = getattr(args, "telemetry_action", None) or "status"
    bridge = AntigravityEventBridge(project_root=target)

    if action == "status":
        mode = TelemetryConfigResolver.resolve_mode(project_root=target)
        status_info = {
            "telemetry_mode": mode.value,
            "is_enabled": mode == TelemetryCollectionMode.ON,
            "project_id": bridge.project_id,
            "project_name": bridge.project_name,
            "project_root": str(bridge.project_root),
        }
        if getattr(args, "json", False):
            print(json.dumps(status_info, indent=2))
        else:
            print("=" * 60)
            print("AntiOS Engineering Intelligence: Telemetry Status")
            print("=" * 60)
            print(f"Collection Mode:        {mode.value}")
            print(f"Collection Active:      {'YES' if mode == TelemetryCollectionMode.ON else 'NO (Default: OFF)'}")
            print(f"Project Identity:       {bridge.project_id} ({bridge.project_name})")
            print(f"Project Root:           {bridge.project_root}")
        return 0

    if action == "enable":
        cfg_file = target / "antios.config.json"
        cfg_data: Dict[str, Any] = {}
        if cfg_file.is_file():
            try:
                with open(cfg_file, "r", encoding="utf-8-sig") as f:
                    cfg_data = json.load(f)
            except Exception:
                cfg_data = {}
        if "telemetry" not in cfg_data or not isinstance(cfg_data["telemetry"], dict):
            cfg_data["telemetry"] = {}
        cfg_data["telemetry"]["enabled"] = True
        cfg_data["telemetry"]["mode"] = "ON"
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(cfg_data, f, indent=2)
        print(f"[SUCCESS] Telemetry collection ENABLED for project '{bridge.project_name}' in antios.config.json")
        return 0

    if action == "disable":
        cfg_file = target / "antios.config.json"
        cfg_data: Dict[str, Any] = {}
        if cfg_file.is_file():
            try:
                with open(cfg_file, "r", encoding="utf-8-sig") as f:
                    cfg_data = json.load(f)
            except Exception:
                cfg_data = {}
        if "telemetry" not in cfg_data or not isinstance(cfg_data["telemetry"], dict):
            cfg_data["telemetry"] = {}
        cfg_data["telemetry"]["enabled"] = False
        cfg_data["telemetry"]["mode"] = "OFF"
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(cfg_data, f, indent=2)
        print(f"[SUCCESS] Telemetry collection DISABLED for project '{bridge.project_name}' in antios.config.json")
        return 0

    if action == "ingest":
        transcript_path = getattr(args, "transcript", None)
        ndjson_path = getattr(args, "ndjson", None)

        if transcript_path:
            res = bridge.ingest_transcript(
                transcript_path=transcript_path,
                session_id=getattr(args, "session_id", None),
            )
        else:
            res = bridge.ingest_ndjson_telemetry(
                ndjson_path=ndjson_path,
                session_id=getattr(args, "session_id", None),
            )
        if getattr(args, "json", False):
            print(json.dumps(res.to_dict(), indent=2))
        else:
            print(f"Ingestion Status:       {'SUCCESS' if res.success else 'FAILED'}")
            print(f"Mode:                   {res.mode.value}")
            print(f"Events Ingested:        {res.events_ingested}")
            print(f"Tool Calls Ingested:    {res.tool_calls_ingested}")
            print(f"Turns Ingested:         {res.turns_ingested}")
            print(f"Bytes Processed:        {res.bytes_processed}")
            if res.error:
                print(f"Diagnostic Error:       {res.error}")
        return 0 if res.success else 1

    print("Usage: antios telemetry {status,enable,disable,ingest} ...")
    return 1


def cmd_experience(args: argparse.Namespace) -> int:
    """Handles antios experience {analyze,report,export} commands."""
    target = _resolve_target(args)
    action = getattr(args, "experience_action", None) or "analyze"
    explicit_dd = getattr(args, "data_dir", None)

    try:
        context = AntiOSDataResolver.resolve_context(
            project_root=target,
            explicit_dir=explicit_dd,
        )
    except Exception as e:
        if getattr(args, "json", False):
            print(json.dumps({"status": "ERROR", "error": str(e)}, indent=2))
        else:
            print(f"Error: Experience storage unavailable: {e}")
        return 1

    if not context.db_path.is_file():
        if getattr(args, "json", False):
            print(json.dumps({"status": "ERROR", "error": f"Database file not found: {context.db_path}"}, indent=2))
        else:
            print(f"Error: Experience database does not exist: {context.db_path}")
        return 1

    engine = ExperienceAnalyticsEngine(db_path=context.db_path)
    is_global = getattr(args, "is_global", False)
    project_id_arg = getattr(args, "project", None)

    if is_global:
        report = engine.analyze_global()
    elif project_id_arg:
        report = engine.analyze_project(project_id_arg)
    else:
        # Default to current project root identity
        report = engine.analyze_project(context.project_id)

    if action == "sync":
        bridge = AntigravityEventBridge(project_root=target, data_dir=explicit_dd)
        res = bridge.ingest_ndjson_telemetry()
        if getattr(args, "json", False):
            print(json.dumps(res.to_dict(), indent=2))
        else:
            print(f"[SUCCESS] Synchronized telemetry: {res.events_ingested} event(s) recorded to {context.db_path}")
        return 0 if res.success else 1

    if action == "analyze":
        if getattr(args, "json", False):
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print(report.to_text())
        return 0

    if action == "report":
        fmt = getattr(args, "format", "text") or "text"
        out_file = getattr(args, "output", None)

        if fmt == "json":
            out_content = json.dumps(report.to_dict(), indent=2)
        elif fmt in ("markdown", "md"):
            out_content = report.to_markdown()
        else:
            out_content = report.to_text()

        if out_file:
            out_path = Path(out_file).resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(out_content)
            print(f"[SUCCESS] Experience report saved to: {out_path}")
        else:
            print(out_content)
        return 0

    if action == "export":
        out_path = getattr(args, "output", None)
        if not out_path:
            # Default to <data-dir>/exports
            out_path = context.data_dir / "exports"
        fmt = getattr(args, "format", "json") or "json"
        try:
            saved_file = ExperienceExporter.export(
                report=report,
                output_path=out_path,
                export_format=fmt,
            )
            if getattr(args, "json", False):
                print(json.dumps({"status": "SUCCESS", "exported_path": str(saved_file)}, indent=2))
            else:
                print(f"[SUCCESS] Mined intelligence exported to: {saved_file}")
            return 0
        except Exception as e:
            if getattr(args, "json", False):
                print(json.dumps({"status": "ERROR", "error": str(e)}, indent=2))
            else:
                print(f"Error exporting intelligence: {e}")
            return 1

    print("Usage: antios experience {analyze,report,export} ...")
    return 1


# ==========================================
# CLI Parser Setup
# ==========================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="antios",
        description="AntiOS 2.1 - Project Agent OS for Universal Engineering Governance & Autonomous Development",
    )
    subparsers = parser.add_subparsers(dest="command", help="AntiOS commands")

    # version
    p_ver = subparsers.add_parser("version", help="Print AntiOS version, channel, and environment facts")
    p_ver.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_ver.add_argument("--path", help="Target project root directory")
    p_ver.set_defaults(func=cmd_version)

    # status
    p_stat = subparsers.add_parser("status", help="Print concise operational status")
    p_stat.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_stat.add_argument("--path", help="Target project root directory")
    p_stat.set_defaults(func=cmd_status)

    # doctor
    p_doc = subparsers.add_parser("doctor", help="Run comprehensive system and project diagnostics")
    p_doc.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_doc.add_argument("--path", help="Target project root directory")
    p_doc.set_defaults(func=cmd_doctor)

    # install
    p_inst = subparsers.add_parser("install", help="Install AntiOS into the target project")
    p_inst.add_argument("--version", help="Target AntiOS version to install")
    p_inst.add_argument("--force", action="store_true", help="Force overwrite of managed files")
    p_inst.add_argument("--force-downgrade", action="store_true", help="Explicitly allow downgrade to an older version")
    p_inst.add_argument("--dry-run", action="store_true", help="Preview installation without writing files")
    p_inst.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_inst.add_argument("--path", help="Target project root directory")
    p_inst.add_argument("--data-dir", help="Central AntiOS Data Directory path")
    p_inst.set_defaults(func=cmd_install)

    # upgrade
    p_upg = subparsers.add_parser("upgrade", help="Safely reconcile and upgrade AntiOS instance")
    p_upg.add_argument("--check", action="store_true", help="Check for upgrade without applying")
    p_upg.add_argument("--plan", action="store_true", help="Display reconciliation plan")
    p_upg.add_argument("--version", help="Target AntiOS version")
    p_upg.add_argument("--dry-run", action="store_true", help="Preview upgrade mutations")
    p_upg.add_argument("--force", action="store_true", help="Force overwrite in conflicts")
    p_upg.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_upg.add_argument("--path", help="Target project root directory")
    p_upg.set_defaults(func=cmd_upgrade)

    # update
    p_upd = subparsers.add_parser("update", help="Update AntiOS instance to a newer revision")
    p_upd.add_argument("--check", action="store_true", help="Check for available updates without applying")
    p_upd.add_argument("--version", help="Specific version to update to")
    p_upd.add_argument("--dry-run", action="store_true", help="Preview update without writing files")
    p_upd.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_upd.add_argument("--path", help="Target project root directory")
    p_upd.set_defaults(func=cmd_update)

    # rollback
    p_roll = subparsers.add_parser("rollback", help="Roll back AntiOS instance to a previous snapshot")
    p_roll.add_argument("--version", help="Specific snapshot version to restore")
    p_roll.add_argument("--dry-run", action="store_true", help="Preview rollback without writing files")
    p_roll.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_roll.add_argument("--path", help="Target project root directory")
    p_roll.set_defaults(func=cmd_rollback)

    # repair
    p_rep = subparsers.add_parser("repair", help="Repair damaged, missing, or drifted instance files")
    p_rep.add_argument("--check", action="store_true", help="Check for drift without repairing")
    p_rep.add_argument("--plan", action="store_true", help="Generate and display repair plan")
    p_rep.add_argument("--apply", action="store_true", help="Apply repair plan (default)")
    p_rep.add_argument("--dry-run", action="store_true", help="Simulate repair without modifying files")
    p_rep.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_rep.add_argument("--path", help="Target project root directory")
    p_rep.set_defaults(func=cmd_repair)

    # remove / uninstall
    p_rem = subparsers.add_parser("remove", help="Safely remove AntiOS instance files")
    p_rem.add_argument("--dry-run", action="store_true", help="Preview removal without unlinking files")
    p_rem.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_rem.add_argument("--path", help="Target project root directory")
    p_rem.set_defaults(func=cmd_remove)

    p_uninst = subparsers.add_parser("uninstall", help="Alias for remove")
    p_uninst.add_argument("--dry-run", action="store_true", help="Preview removal without unlinking files")
    p_uninst.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_uninst.add_argument("--path", help="Target project root directory")
    p_uninst.set_defaults(func=cmd_remove)

    # adapt
    p_adp = subparsers.add_parser("adapt", help="Re-discover and adapt target project")
    p_adp.add_argument("--dry-run", action="store_true", help="Simulate adaptation")
    p_adp.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_adp.add_argument("--path", help="Target project root directory")
    p_adp.set_defaults(func=cmd_adapt)

    # verify
    p_verf = subparsers.add_parser("verify", help="Verify instance integrity and runtime closure")
    p_verf.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_verf.add_argument("--path", help="Target project root directory")
    p_verf.set_defaults(func=cmd_verify)

    # compile
    p_comp = subparsers.add_parser("compile", help="Compile target repository into an Agent-Native Project Environment")
    p_comp.add_argument("--path", help="Target project root directory (defaults to cwd)")
    p_comp.add_argument("--check", "--dry-run", dest="check", action="store_true", help="Perform validation without writing files")
    p_comp.add_argument("--json", action="store_true", help="Output machine-readable compilation result")
    p_comp.add_argument("--force", action="store_true", help="Overwrite existing user-authored files without conflict fallback")
    p_comp.set_defaults(func=cmd_compile)

    # issue
    p_iss = subparsers.add_parser("issue", help="Issue and bug management workflow")
    p_iss_sub = p_iss.add_subparsers(dest="issue_action", help="Issue action")

    p_iss_triage = p_iss_sub.add_parser("triage", help="Triage a feature request against Architecture Freeze")
    p_iss_triage.add_argument("description", help="Feature request description")
    p_iss_triage.add_argument("--json", action="store_true")

    p_iss_disc = p_iss_sub.add_parser("discover", help="Search duplicate issues")
    p_iss_disc.add_argument("query", help="Search query")
    p_iss_disc.add_argument("--json", action="store_true")

    p_iss_create = p_iss_sub.add_parser("create", help="Generate structured issue evidence card")
    p_iss_create.add_argument("--title", required=True, help="Issue title")
    p_iss_create.add_argument("--class", dest="issue_class", default="BUG", help="Issue class (BUG/FEATURE/etc)")
    p_iss_create.add_argument("--observed", default="", help="Observed behavior")
    p_iss_create.add_argument("--expected", default="", help="Expected behavior")
    p_iss_create.add_argument("--reproduce", default="", help="Steps to reproduce")
    p_iss_create.add_argument("--trace", default="", help="Command output or error trace")
    p_iss_create.add_argument("--files", nargs="*", default=[], help="Affected files")

    p_iss.set_defaults(func=cmd_issue)

    # release
    p_rel = subparsers.add_parser("release", help="Release engineering and validation")
    p_rel_sub = p_rel.add_subparsers(dest="release_action", help="Release action")

    p_rel_chk = p_rel_sub.add_parser("check", help="Run pre-flight release validation checks")
    p_rel_chk.add_argument("--skip-tests", action="store_true", help="Skip slow test suite execution")
    p_rel_chk.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_rel_chk.add_argument("--path", help="Target project root directory")

    p_rel_not = p_rel_sub.add_parser("notes", help="Generate release notes")
    p_rel_not.add_argument("--version", help="Version override")

    p_rel.set_defaults(func=cmd_release)

    # data
    p_data = subparsers.add_parser("data", help="AntiOS Data Directory and experience storage inspection")
    p_data_sub = p_data.add_subparsers(dest="data_action", help="Data actions")

    p_data_stat = p_data_sub.add_parser("status", help="Inspect storage status and health")
    p_data_stat.add_argument("--data-dir", help="Explicit data directory override")
    p_data_stat.add_argument("--path", help="Target project root directory")
    p_data_stat.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    p_data_set = p_data_sub.add_parser("set-dir", help="Set or re-point project data directory")
    p_data_set.add_argument("directory", help="Target data directory path")
    p_data_set.add_argument("--path", help="Target project root directory")
    p_data_set.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    p_data_bak = p_data_sub.add_parser("backup", help="Create online hot backup of experience database")
    p_data_bak.add_argument("--output", help="Explicit backup destination path")
    p_data_bak.add_argument("--data-dir", help="Explicit data directory override")
    p_data_bak.add_argument("--path", help="Target project root directory")
    p_data_bak.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    p_data_rst = p_data_sub.add_parser("restore", help="Restore experience database from backup")
    p_data_rst.add_argument("--backup", required=True, help="Path to backup .db file")
    p_data_rst.add_argument("--confirm", action="store_true", help="Confirm destructive restore operation")
    p_data_rst.add_argument("--dry-run", action="store_true", help="Preview restore without modifying database")
    p_data_rst.add_argument("--data-dir", help="Explicit data directory override")
    p_data_rst.add_argument("--path", help="Target project root directory")
    p_data_rst.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    p_data_prg = p_data_sub.add_parser("purge", help="Purge experience data with mandatory scoping")
    p_data_prg.add_argument("--project", help="Purge data for specific project ID only")
    p_data_prg.add_argument("--all", dest="purge_all", action="store_true", help="Purge ALL experience data")
    p_data_prg.add_argument("--older-than", type=int, help="Only purge records older than N days")
    p_data_prg.add_argument("--confirm", action="store_true", help="Confirm destructive purge operation")
    p_data_prg.add_argument("--dry-run", action="store_true", help="Preview purge counts without deleting")
    p_data_prg.add_argument("--data-dir", help="Explicit data directory override")
    p_data_prg.add_argument("--path", help="Target project root directory")
    p_data_prg.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    p_data_vac = p_data_sub.add_parser("vacuum", help="Reclaim disk space in experience database")
    p_data_vac.add_argument("--full", action="store_true", help="Full VACUUM rebuild (slower but more thorough)")
    p_data_vac.add_argument("--data-dir", help="Explicit data directory override")
    p_data_vac.add_argument("--path", help="Target project root directory")
    p_data_vac.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    p_data_exp = p_data_sub.add_parser("export", help="Export raw experience data as JSONL")
    p_data_exp.add_argument("--project", help="Export data for specific project ID only")
    p_data_exp.add_argument("--output", help="Destination file path (defaults to <data-dir>/exports/)")
    p_data_exp.add_argument("--data-dir", help="Explicit data directory override")
    p_data_exp.add_argument("--path", help="Target project root directory")
    p_data_exp.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    p_data.set_defaults(func=cmd_data)

    # telemetry
    p_telem = subparsers.add_parser("telemetry", help="AntiOS Engineering Intelligence telemetry inspection & ingestion")
    p_telem_sub = p_telem.add_subparsers(dest="telemetry_action", help="Telemetry actions")

    p_telem_stat = p_telem_sub.add_parser("status", help="Inspect telemetry collection status and mode")
    p_telem_stat.add_argument("--path", help="Target project root directory")
    p_telem_stat.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    p_telem_en = p_telem_sub.add_parser("enable", help="Enable telemetry collection in project configuration")
    p_telem_en.add_argument("--path", help="Target project root directory")

    p_telem_dis = p_telem_sub.add_parser("disable", help="Disable telemetry collection in project configuration")
    p_telem_dis.add_argument("--path", help="Target project root directory")

    p_telem_ing = p_telem_sub.add_parser("ingest", help="Manually ingest Antigravity transcript or NDJSON file")
    p_telem_ing.add_argument("--transcript", help="Path to transcript.jsonl file")
    p_telem_ing.add_argument("--ndjson", help="Path to telemetry.ndjson file (defaults to .agents/telemetry.ndjson)")
    p_telem_ing.add_argument("--session-id", help="Explicit session/conversation ID override")
    p_telem_ing.add_argument("--path", help="Target project root directory")
    p_telem_ing.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    p_telem.set_defaults(func=cmd_telemetry)

    # experience
    p_exp = subparsers.add_parser("experience", help="AntiOS Experience Intelligence and analytics engine")
    p_exp_sub = p_exp.add_subparsers(dest="experience_action", help="Experience actions")

    # experience sync
    p_exp_sync = p_exp_sub.add_parser("sync", help="Synchronize pending telemetry into experience database")
    p_exp_sync.add_argument("--data-dir", help="Explicit data directory override")
    p_exp_sync.add_argument("--path", help="Target project root directory")
    p_exp_sync.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    # experience analyze
    p_exp_an = p_exp_sub.add_parser("analyze", help="Deterministically analyze recorded telemetry")
    p_exp_an.add_argument("--project", help="Target project ID (defaults to current project)")
    p_exp_an.add_argument("--global", dest="is_global", action="store_true", help="Cross-project global aggregation")
    p_exp_an.add_argument("--data-dir", help="Explicit data directory override")
    p_exp_an.add_argument("--path", help="Target project root directory")
    p_exp_an.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    # experience report
    p_exp_rep = p_exp_sub.add_parser("report", help="Generate engineering intelligence report")
    p_exp_rep.add_argument("--project", help="Target project ID (defaults to current project)")
    p_exp_rep.add_argument("--global", dest="is_global", action="store_true", help="Cross-project global aggregation")
    p_exp_rep.add_argument("--format", choices=["text", "markdown", "json"], default="text", help="Report output format")
    p_exp_rep.add_argument("--output", help="Write report to file path")
    p_exp_rep.add_argument("--data-dir", help="Explicit data directory override")
    p_exp_rep.add_argument("--path", help="Target project root directory")

    # experience export
    p_exp_exp = p_exp_sub.add_parser("export", help="Export machine-readable intelligence snapshot")
    p_exp_exp.add_argument("--project", help="Target project ID (defaults to current project)")
    p_exp_exp.add_argument("--global", dest="is_global", action="store_true", help="Cross-project global aggregation")
    p_exp_exp.add_argument("--output", help="Destination file or directory (defaults to <data-dir>/exports/)")
    p_exp_exp.add_argument("--format", choices=["json", "markdown"], default="json", help="Export format")
    p_exp_exp.add_argument("--data-dir", help="Explicit data directory override")
    p_exp_exp.add_argument("--path", help="Target project root directory")
    p_exp_exp.add_argument("--json", action="store_true", help="Output machine-readable status")

    p_exp.set_defaults(func=cmd_experience)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
