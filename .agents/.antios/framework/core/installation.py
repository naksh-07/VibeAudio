"""AntiOS 2.0 Installation Lifecycle Engine.

Governs the deterministic, ownership-aware lifecycle:
INSTALL -> ADAPT -> VERIFY -> READY
UPDATE -> RE-ADAPT -> VERIFY
REPAIR -> VERIFY
REMOVE -> VERIFY

Handles all lifecycle states:
- First installation
- Already-installed instance (idempotent, zero unnecessary mutations)
- Partially installed instance recovery
- Stale instance detection (manifest drift)
- Newer AntiOS source / Older AntiOS instance migration
- Corrupted manifest (fail-closed, diagnostic error)
- Conflicting .agents configuration (preserves pre-existing user assets)
- User-modified generated/managed file (blocks silent overwrite)
- Removed project component (flags stale paths)
- Unsupported project topology (graceful degradation)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from framework.core.compiler import CompilationResult, ProjectBoundaryCompiler
from framework.core.config import AntiOSConfig, load_config
from framework.core.discovery import discover_project, is_tool_in_path
from framework.core.experience import (
    AntiOSDataResolver,
    init_data_directory,
    init_experience_db,
    register_project,
)
from framework.core.manifest import (
    AdaptationState,
    ArtifactOwnership,
    ArtifactRecord,
    CURRENT_ANTIOS_VERSION,
    CURRENT_SCHEMA_VERSION,
    InstallationState,
    ProjectManifest,
    load_manifest,
    save_manifest,
)
from framework.core.reconciliation import (
    ArtifactReconciliation,
    ReconciliationAction,
    ReconciliationEngine,
    ReconciliationPlan,
)
from framework.core.provenance import (
    ProvenanceConflict,
    ProvenanceTracker,
    compute_file_sha256,
)
from framework.core.version import ANTIOS_VERSION, compare_versions



@dataclass
class LifecycleResult:
    """Structured result for an AntiOS lifecycle operation."""
    operation: str  # INSTALL, ADAPT, UPDATE, REPAIR, REMOVE, VERIFY
    status: str     # SUCCESS, IDEMPOTENT, BLOCKED, CONFLICT, ERROR, STALE
    installation_state: InstallationState
    adaptation_state: AdaptationState
    manifest: Optional[ProjectManifest] = None
    written_files: List[str] = field(default_factory=list)
    removed_files: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "status": self.status,
            "installation_state": self.installation_state.value if isinstance(self.installation_state, InstallationState) else str(self.installation_state),
            "adaptation_state": self.adaptation_state.value if isinstance(self.adaptation_state, AdaptationState) else str(self.adaptation_state),
            "manifest": self.manifest.to_dict() if self.manifest else None,
            "written_files": self.written_files,
            "removed_files": self.removed_files,
            "conflicts": self.conflicts,
            "issues": self.issues,
            "summary": self.summary,
        }


def _resolve_project_fingerprint(profile: Any, target_root: Path) -> str:
    fp = getattr(profile, "manifest_fingerprint", "")
    if not fp:
        return hashlib.sha256(f"manifestless:{target_root.name}".encode("utf-8")).hexdigest()
    return fp


class InstallationLifecycleManager:
    """Manages the lifecycle operations for Project Agent OS instances."""

    def __init__(
        self,
        source_root: Union[str, Path],
        target_root: Union[str, Path],
        source_revision: Optional[str] = None,
    ):
        self.source_root = Path(source_root).resolve()
        self.target_root = Path(target_root).resolve()
        self.source_revision = source_revision or f"v{ANTIOS_VERSION}"
        self.compiler = ProjectBoundaryCompiler(
            source_root=self.source_root,
            target_root=self.target_root,
            source_revision=self.source_revision,
        )

    def install(
        self,
        dry_run: bool = False,
        force: bool = False,
        target_version: Optional[str] = None,
        force_downgrade: bool = False,
        data_dir: Optional[str] = None,
    ) -> LifecycleResult:
        """Installs AntiOS into target project. Idempotent if already installed."""
        # 0. Validate data directory location if provided
        effective_data_dir = data_dir or os.environ.get("ANTIOS_DATA_DIR")
        resolved_dd: Optional[Path] = None
        if effective_data_dir:
            resolved_dd = Path(effective_data_dir).resolve()
            if resolved_dd == self.target_root or self.target_root in resolved_dd.parents:
                return LifecycleResult(
                    operation="INSTALL",
                    status="BLOCKED",
                    installation_state=InstallationState.UNINSTALLED,
                    adaptation_state=AdaptationState.UNADAPTED,
                    issues=["AntiOS Data Directory cannot be located inside the target project repository."],
                    summary="Installation blocked: data directory cannot be located inside the project repository.",
                )

        # 1. Check if manifest already exists
        manifest_path = self.target_root / ".antios/manifest.json"
        existing_manifest: Optional[ProjectManifest] = None

        if manifest_path.is_file():
            try:
                existing_manifest = load_manifest(self.target_root)
            except Exception as e:
                # Corrupted manifest -> fail closed
                return LifecycleResult(
                    operation="INSTALL",
                    status="BLOCKED",
                    installation_state=InstallationState.ERROR,
                    adaptation_state=AdaptationState.CONFLICT,
                    issues=[f"Corrupted manifest detected: {e}. Run 'repair' or inspect .antios/manifest.json."],
                    summary="Installation blocked by corrupted manifest.",
                )

        # 2. Prevent silent downgrade
        if existing_manifest and not force:
            effective_target = target_version or ANTIOS_VERSION
            try:
                cmp = compare_versions(existing_manifest.antios_version, effective_target)
                if cmp["is_downgrade"] and not force_downgrade:
                    return LifecycleResult(
                        operation="INSTALL",
                        status="BLOCKED",
                        installation_state=existing_manifest.installation_state,
                        adaptation_state=existing_manifest.adaptation_state,
                        manifest=existing_manifest,
                        issues=[
                            f"Downgrade rejected: Installed version ({existing_manifest.antios_version}) is newer than requested ({effective_target}). Pass force_downgrade=True to override."
                        ],
                        summary="Installation blocked to prevent silent downgrade.",
                    )
            except Exception:
                pass

        # 3. If valid manifest already exists and not forced, check idempotency
        if existing_manifest and not force:
            # Check manifest fingerprint against current disk manifests
            current_profile = discover_project(str(self.target_root))
            current_fp = _resolve_project_fingerprint(current_profile, self.target_root)
            if existing_manifest.project_fingerprint == current_fp:

                # Perfectly matching fingerprint: verify files on disk
                verification = self.verify()
                if verification.status == "SUCCESS":
                    if resolved_dd and not dry_run:
                        _, db_p = init_data_directory(resolved_dd)
                        init_experience_db(db_p)
                        pid = register_project(db_p, self.target_root)
                        existing_manifest.metadata["data_dir"] = str(resolved_dd)
                        existing_manifest.metadata["project_id"] = pid

                        cfg_path = self.target_root / "antios.config.json"
                        if cfg_path.is_file():
                            try:
                                with open(cfg_path, "r", encoding="utf-8-sig") as f:
                                    cfg_dict = json.load(f)
                                cfg_dict["data_dir"] = str(resolved_dd)
                                with open(cfg_path, "w", encoding="utf-8") as f:
                                    json.dump(cfg_dict, f, indent=2)
                                if "antios.config.json" in existing_manifest.managed_paths:
                                    existing_manifest.managed_paths["antios.config.json"].sha256 = compute_file_sha256(cfg_path)
                            except Exception:
                                pass
                        save_manifest(existing_manifest, self.target_root)

                    return LifecycleResult(
                        operation="INSTALL",
                        status="IDEMPOTENT",
                        installation_state=existing_manifest.installation_state,
                        adaptation_state=existing_manifest.adaptation_state,
                        manifest=existing_manifest,
                        summary="AntiOS is already installed and up to date (idempotent no-op).",
                    )
            else:
                # Fingerprint changed: project was modified -> needs adapt
                return LifecycleResult(
                    operation="INSTALL",
                    status="STALE",
                    installation_state=existing_manifest.installation_state,
                    adaptation_state=AdaptationState.STALE,
                    manifest=existing_manifest,
                    issues=["Target manifests have changed since last installation. Re-adaptation required."],
                    summary="Existing installation is stale. Run 'adapt' to synchronize.",
                )

        # 3. Detect pre-existing user assets in .agents/
        user_owned_paths: List[str] = []
        agents_dir = self.target_root / ".agents"
        if agents_dir.is_dir():
            for p in agents_dir.rglob("*"):
                if p.is_file():
                    rel = str(p.relative_to(self.target_root)).replace("\\", "/")
                    if rel != ".agents/hooks.json":
                        user_owned_paths.append(rel)

        # 4. Compile boundary assets
        compilation = self.compiler.compile(existing_manifest=existing_manifest)
        if user_owned_paths:
            for u in user_owned_paths:
                if u not in compilation.manifest.user_owned_paths:
                    compilation.manifest.user_owned_paths.append(u)

        # 5. Emit files to disk
        emit_ok, written, conflicts = self.compiler.emit(
            compilation,
            existing_manifest=existing_manifest,
            dry_run=dry_run,
        )

        if not emit_ok and not force:
            return LifecycleResult(
                operation="INSTALL",
                status="CONFLICT",
                installation_state=InstallationState.PARTIAL,
                adaptation_state=AdaptationState.CONFLICT,
                manifest=compilation.manifest,
                conflicts=conflicts,
                summary="Installation blocked by artifact ownership conflicts.",
            )

        if not dry_run:
            if resolved_dd:
                _, db_p = init_data_directory(resolved_dd)
                init_experience_db(db_p)
                pid = register_project(db_p, self.target_root)
                compilation.manifest.metadata["data_dir"] = str(resolved_dd)
                compilation.manifest.metadata["project_id"] = pid

                cfg_path = self.target_root / "antios.config.json"
                if cfg_path.is_file():
                    try:
                        with open(cfg_path, "r", encoding="utf-8-sig") as f:
                            cfg_dict = json.load(f)
                        cfg_dict["data_dir"] = str(resolved_dd)
                        with open(cfg_path, "w", encoding="utf-8") as f:
                            json.dump(cfg_dict, f, indent=2)
                        if "antios.config.json" in compilation.manifest.managed_paths:
                            compilation.manifest.managed_paths["antios.config.json"].sha256 = compute_file_sha256(cfg_path)
                    except Exception:
                        pass

            compilation.manifest.installation_state = InstallationState.INSTALLED
            compilation.manifest.adaptation_state = AdaptationState.ADAPTED
            save_manifest(compilation.manifest, self.target_root)

            try:
                from framework.compiler.compiler import compile_project
                compile_project(self.target_root)
            except Exception:
                pass

        return LifecycleResult(
            operation="INSTALL",
            status="SUCCESS",
            installation_state=InstallationState.INSTALLED,
            adaptation_state=AdaptationState.ADAPTED,
            manifest=compilation.manifest,
            written_files=written,
            conflicts=conflicts,
            summary=f"Installed AntiOS 2.0 Project Agent OS ({len(written)} files written).",
        )

    def adapt(self, dry_run: bool = False) -> LifecycleResult:
        """Re-discovers target project and updates generated intelligence."""
        manifest = load_manifest(self.target_root)
        if not manifest:
            return LifecycleResult(
                operation="ADAPT",
                status="ERROR",
                installation_state=InstallationState.UNINSTALLED,
                adaptation_state=AdaptationState.UNADAPTED,
                issues=["Cannot adapt: AntiOS is not installed in this project."],
                summary="AntiOS is not installed.",
            )

        # Run fresh discovery
        fresh_profile = discover_project(str(self.target_root))
        manifest.project_fingerprint = _resolve_project_fingerprint(fresh_profile, self.target_root)

        # Recompile boundary
        compilation = self.compiler.compile(
            existing_manifest=manifest,
            profile_override=fresh_profile,
        )

        # Emit files
        emit_ok, written, conflicts = self.compiler.emit(
            compilation,
            existing_manifest=manifest,
            dry_run=dry_run,
        )

        if not dry_run:
            compilation.manifest.adaptation_state = AdaptationState.ADAPTED
            save_manifest(compilation.manifest, self.target_root)

        status = "SUCCESS" if emit_ok else "CONFLICT"
        return LifecycleResult(
            operation="ADAPT",
            status=status,
            installation_state=compilation.manifest.installation_state,
            adaptation_state=compilation.manifest.adaptation_state,
            manifest=compilation.manifest,
            written_files=written,
            conflicts=conflicts,
            summary=f"Adapted AntiOS 2.0 instance ({len(written)} files updated).",
        )

    def _create_snapshot(self, manifest: ProjectManifest, label: str = "snapshot") -> Optional[Path]:
        """Creates a restorable snapshot of AntiOS instance files before update or repair."""
        try:
            backup_dir = self.target_root / ".antios/backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            snap_file = backup_dir / f"snapshot_{ts}_{manifest.antios_version}_{label}.json"

            files_map: Dict[str, str] = {}
            for p in list(manifest.generated_paths.keys()) + list(manifest.managed_paths.keys()):
                abs_p = self.target_root / p
                if abs_p.is_file() and not manifest.is_artifact_user_owned(p):
                    try:
                        files_map[p] = abs_p.read_text(encoding="utf-8")
                    except Exception:
                        pass

            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "antios_version": manifest.antios_version,
                "label": label,
                "manifest": manifest.to_dict(),
                "files": files_map,
            }
            snap_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return snap_file
        except Exception:
            return None

    def upgrade(
        self,
        target_version: Optional[str] = None,
        dry_run: bool = False,
        plan_only: bool = False,
        force: bool = False,
    ) -> LifecycleResult:
        """Executes a safe, ownership-aware, idempotent instance upgrade.

        detect existing AntiOS instance
        → read manifest (and migrate manifest schema if needed)
        → compare versions / schema / profile
        → inspect current project state
        → calculate reconciliation plan
        → if plan_only or dry_run, return plan summary
        → create pre-upgrade snapshot
        → reap obsolete unmodified generated artifacts
        → regenerate AntiOS-owned generated artifacts (preserving user modifications)
        → preserve user-owned and user-modified artifacts
        → update manifest
        → recompile static environment
        → run verification
        → declare upgrade successful
        """
        manifest_path = self.target_root / ".antios/manifest.json"
        if not manifest_path.is_file():
            return LifecycleResult(
                operation="UPGRADE",
                status="ERROR",
                installation_state=InstallationState.UNINSTALLED,
                adaptation_state=AdaptationState.UNADAPTED,
                issues=["Cannot upgrade: AntiOS instance is not installed in this project."],
                summary="AntiOS is not installed in this project.",
            )

        try:
            manifest = load_manifest(self.target_root)
        except Exception as e:
            return LifecycleResult(
                operation="UPGRADE",
                status="BLOCKED",
                installation_state=InstallationState.ERROR,
                adaptation_state=AdaptationState.CONFLICT,
                issues=[f"Corrupted manifest detected: {e}. Run 'repair' or inspect .antios/manifest.json."],
                summary="Upgrade blocked by corrupted manifest.",
            )

        if not manifest:
            return LifecycleResult(
                operation="UPGRADE",
                status="ERROR",
                installation_state=InstallationState.UNINSTALLED,
                adaptation_state=AdaptationState.UNADAPTED,
                issues=["Cannot upgrade: Failed to load manifest."],
                summary="Upgrade failed: manifest missing.",
            )

        target_ver = target_version or ANTIOS_VERSION

        # Check for downgrade unless forced
        if not force:
            try:
                cmp_res = compare_versions(manifest.antios_version, target_ver)
                if cmp_res.get("is_downgrade"):
                    return LifecycleResult(
                        operation="UPGRADE",
                        status="BLOCKED",
                        installation_state=manifest.installation_state,
                        adaptation_state=manifest.adaptation_state,
                        manifest=manifest,
                        issues=[f"Downgrade rejected: Installed version ({manifest.antios_version}) is newer than requested ({target_ver}). Pass force=True to override."],
                        summary="Upgrade blocked to prevent silent downgrade.",
                    )
            except Exception:
                pass

        # Ensure static project environment is current before boundary compilation
        if not dry_run and not plan_only:
            try:
                from framework.compiler.compiler import compile_project
                compile_project(self.target_root)
            except Exception:
                pass

        # 1. Compile proposed target state in-memory
        compilation = self.compiler.compile(existing_manifest=manifest)

        # 2. Calculate deterministic reconciliation plan
        plan = ReconciliationEngine.calculate_plan(
            target_root=self.target_root,
            current_manifest=manifest,
            compiled_files=compilation.compiled_files,
            target_version=target_ver,
            force=force,
        )

        # 3. Handle plan_only, dry_run, or idempotency
        if plan_only:
            return LifecycleResult(
                operation="UPGRADE",
                status="SUCCESS" if plan.can_safely_apply else "CONFLICT",
                installation_state=manifest.installation_state,
                adaptation_state=manifest.adaptation_state,
                manifest=manifest,
                conflicts=[c.path for c in plan.conflicts],
                issues=plan.issues,
                summary=plan.summary,
            )

        if plan.is_idempotent and not force:
            return LifecycleResult(
                operation="UPGRADE",
                status="IDEMPOTENT",
                installation_state=manifest.installation_state,
                adaptation_state=manifest.adaptation_state,
                manifest=manifest,
                summary="AntiOS instance is already up to date (idempotent no-op).",
            )

        if not plan.can_safely_apply and not force:
            return LifecycleResult(
                operation="UPGRADE",
                status="CONFLICT",
                installation_state=manifest.installation_state,
                adaptation_state=manifest.adaptation_state,
                manifest=manifest,
                conflicts=[c.path for c in plan.conflicts],
                issues=plan.issues,
                summary=plan.summary,
            )

        if dry_run:
            return LifecycleResult(
                operation="UPGRADE",
                status="SUCCESS" if plan.can_safely_apply else "CONFLICT",
                installation_state=manifest.installation_state,
                adaptation_state=manifest.adaptation_state,
                manifest=manifest,
                conflicts=[c.path for c in plan.conflicts],
                issues=plan.issues,
                summary=f"[DRY RUN] {plan.summary}",
            )

        # 4. Create pre-upgrade snapshot
        self._create_snapshot(manifest, "pre-upgrade")

        # 5. Execute reconciliation plan
        written_files: List[str] = []
        removed_files: List[str] = []

        # 5a. Reap obsolete unmodified artifacts
        for item in plan.reaped_obsolete:
            target_file = self.target_root / item.path
            if target_file.is_file():
                try:
                    target_file.unlink()
                    removed_files.append(item.path)
                except Exception:
                    pass

        # 5b. Write regenerations, creations, and restorations
        write_targets = plan.regenerations + plan.creations
        for item in write_targets:
            if item.path in compilation.compiled_files:
                target_file = self.target_root / item.path
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_text(compilation.compiled_files[item.path], encoding="utf-8", newline="\n")
                written_files.append(item.path)

        # 5c. Preserve user modifications
        for item in plan.preserved_user_modified:
            if item.path not in compilation.manifest.user_owned_paths:
                compilation.manifest.user_owned_paths.append(item.path)
            if item.path in compilation.manifest.generated_paths:
                compilation.manifest.generated_paths[item.path].is_user_modified = True
            if item.path in compilation.manifest.managed_paths:
                compilation.manifest.managed_paths[item.path].is_user_modified = True

        # 5d. Remove reaped items from manifest
        for item in plan.reaped_obsolete:
            if item.path in compilation.manifest.generated_paths:
                del compilation.manifest.generated_paths[item.path]

        # 6. Update manifest metadata & versions
        compilation.manifest.antios_version = target_ver
        compilation.manifest.source_revision = f"v{target_ver}"
        compilation.manifest.schema_version = plan.target_schema_version
        compilation.manifest.installation_state = InstallationState.INSTALLED
        compilation.manifest.adaptation_state = AdaptationState.ADAPTED
        compilation.manifest.reconciliation_state = plan.to_dict()
        save_manifest(compilation.manifest, self.target_root)

        # 7. Recompile static project environment
        try:
            from framework.compiler.compiler import compile_project
            compile_project(self.target_root)
        except Exception:
            pass

        # 8. Run verification
        verification = self.verify()
        v_issues = verification.issues if verification else []

        status = "SUCCESS" if len(v_issues) == 0 else "PARTIAL"
        return LifecycleResult(
            operation="UPGRADE",
            status=status,
            installation_state=InstallationState.INSTALLED,
            adaptation_state=AdaptationState.ADAPTED,
            manifest=compilation.manifest,
            written_files=written_files,
            removed_files=removed_files,
            conflicts=[c.path for c in plan.conflicts],
            issues=v_issues,
            summary=f"Upgraded AntiOS to {target_ver} ({len(written_files)} updated/created, {len(removed_files)} obsolete reaped, {len(plan.preserved_user_modified)} user modifications preserved).",
        )

    def update(self, new_revision: Optional[str] = None, dry_run: bool = False) -> LifecycleResult:
        """Updates AntiOS instance to a newer source revision with pre-update snapshotting."""
        manifest = load_manifest(self.target_root)
        if not manifest:
            return self.install(dry_run=dry_run)

        revision = new_revision or f"v{ANTIOS_VERSION}"

        # 1. Snapshot state before mutating
        if not dry_run:
            self._create_snapshot(manifest, "pre-update")

        # 2. Update source revision and recompile
        self.source_revision = revision
        self.compiler.source_revision = revision

        compilation = self.compiler.compile(existing_manifest=manifest)
        emit_ok, written, conflicts = self.compiler.emit(
            compilation,
            existing_manifest=manifest,
            dry_run=dry_run,
        )

        if not dry_run:
            compilation.manifest.source_revision = revision
            compilation.manifest.antios_version = ANTIOS_VERSION
            save_manifest(compilation.manifest, self.target_root)

        return LifecycleResult(
            operation="UPDATE",
            status="SUCCESS" if emit_ok else "CONFLICT",
            installation_state=compilation.manifest.installation_state,
            adaptation_state=compilation.manifest.adaptation_state,
            manifest=compilation.manifest,
            written_files=written,
            conflicts=conflicts,
            summary=f"Updated AntiOS to revision '{revision}'. Pre-update snapshot preserved in .antios/backups/.",
        )


    def rollback(self, target_version: Optional[str] = None, dry_run: bool = False) -> LifecycleResult:
        """Rolls back AntiOS instance to a prior snapshot. Strictly preserves user code."""
        backup_dir = self.target_root / ".antios/backups"
        if not backup_dir.is_dir():
            return LifecycleResult(
                operation="ROLLBACK",
                status="BLOCKED",
                installation_state=InstallationState.INSTALLED,
                adaptation_state=AdaptationState.ADAPTED,
                issues=["No rollback points available: .antios/backups directory does not exist."],
                summary="Rollback unavailable: No prior snapshot recorded.",
            )

        snaps = sorted(list(backup_dir.glob("snapshot_*.json")), reverse=True)
        if not snaps:
            return LifecycleResult(
                operation="ROLLBACK",
                status="BLOCKED",
                installation_state=InstallationState.INSTALLED,
                adaptation_state=AdaptationState.ADAPTED,
                issues=["No snapshot files found in .antios/backups."],
                summary="Rollback unavailable: No prior snapshot recorded.",
            )

        selected_snap: Optional[Path] = None
        selected_data: Optional[Dict[str, Any]] = None

        for s in snaps:
            try:
                data = json.loads(s.read_text(encoding="utf-8"))
                if target_version:
                    if data.get("antios_version") == target_version or target_version in s.name:
                        selected_snap = s
                        selected_data = data
                        break
                else:
                    selected_snap = s
                    selected_data = data
                    break
            except Exception:
                continue

        if not selected_snap or not selected_data:
            return LifecycleResult(
                operation="ROLLBACK",
                status="BLOCKED",
                installation_state=InstallationState.INSTALLED,
                adaptation_state=AdaptationState.ADAPTED,
                issues=[f"No matching snapshot found for version '{target_version}'." if target_version else "Failed to parse snapshots."],
                summary=f"Rollback failed: No compatible snapshot for '{target_version}'.",
            )

        restored_files: List[str] = []
        files_map = selected_data.get("files", {})
        for rel_path, content in files_map.items():
            abs_p = self.target_root / rel_path
            if not dry_run:
                abs_p.parent.mkdir(parents=True, exist_ok=True)
                abs_p.write_text(content, encoding="utf-8")
            restored_files.append(rel_path)

        restored_manifest_dict = selected_data.get("manifest")
        restored_manifest = None
        if restored_manifest_dict and not dry_run:
            restored_manifest = ProjectManifest.from_dict(restored_manifest_dict)
            save_manifest(restored_manifest, self.target_root)

        return LifecycleResult(
            operation="ROLLBACK",
            status="SUCCESS",
            installation_state=InstallationState.INSTALLED,
            adaptation_state=AdaptationState.ADAPTED,
            manifest=restored_manifest,
            written_files=restored_files,
            summary=f"Rolled back AntiOS to version {selected_data.get('antios_version')} ({len(restored_files)} files restored). User application code was preserved.",
        )

    def repair(self, dry_run: bool = False, plan_only: bool = False) -> LifecycleResult:
        """Repairs damaged or missing AntiOS instance artifacts."""
        manifest = load_manifest(self.target_root)
        if not manifest:
            return self.install(dry_run=dry_run)

        tracker = ProvenanceTracker(self.target_root, manifest)
        conflicts = tracker.audit_artifacts()

        written: List[str] = []
        issues: List[str] = []

        compilation = self.compiler.compile(existing_manifest=manifest)

        # Identify repairable missing files
        for conf in conflicts:
            if conf.conflict_type in ("MISSING_MANAGED", "MISSING_GENERATED"):
                rel_path = conf.path
                if rel_path in compilation.compiled_files:
                    if not dry_run and not plan_only:
                        target_file = self.target_root / rel_path
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        target_file.write_text(compilation.compiled_files[rel_path], encoding="utf-8")
                    written.append(rel_path)

        if plan_only:
            return LifecycleResult(
                operation="REPAIR",
                status="SUCCESS",
                installation_state=manifest.installation_state,
                adaptation_state=manifest.adaptation_state,
                manifest=manifest,
                written_files=written,
                summary=f"Repair plan: {len(written)} missing artifacts scheduled for restoration.",
            )

        if not dry_run:
            manifest.installation_state = InstallationState.INSTALLED
            save_manifest(manifest, self.target_root)

        return LifecycleResult(
            operation="REPAIR",
            status="SUCCESS",
            installation_state=InstallationState.INSTALLED,
            adaptation_state=manifest.adaptation_state,
            manifest=manifest,
            written_files=written,
            issues=issues,
            summary=f"Repaired AntiOS instance ({len(written)} files restored).",
        )

    def remove(self, dry_run: bool = False) -> LifecycleResult:
        """Safely removes AntiOS instance files while preserving user code."""
        manifest = load_manifest(self.target_root)
        removed: List[str] = []

        # Target files to remove: only managed and generated files from manifest
        paths_to_remove: List[str] = []
        if manifest:
            paths_to_remove.append(".antios/manifest.json")
            paths_to_remove.extend(list(manifest.generated_paths.keys()))
            paths_to_remove.extend(list(manifest.managed_paths.keys()))
        else:
            paths_to_remove = [
                ".antios/manifest.json",
                ".antios/project_profile.json",
                ".antios/project_anatomy.json",
                ".antios/knowledge.json",
                ".antios/agent_topology.json",
                ".antios/tool_policy.json",
                ".antios/runtime/pre_tool_guard.py",
                ".antios/runtime/stop_gate.py",
                ".antios/runtime/inspect_instance.py",
                ".antios/runtime/verify_runtime.py",
                ".agents/skills/antios/SKILL.md",
                "antios.config.json",
            ]

        for rel_path in paths_to_remove:
            if manifest and manifest.is_artifact_user_owned(rel_path):
                continue
            abs_path = self.target_root / rel_path
            if abs_path.is_file():
                if not dry_run:
                    abs_path.unlink()
                removed.append(rel_path)

        # Clean empty runtime directory if present
        runtime_dir = self.target_root / ".antios/runtime"
        if runtime_dir.is_dir() and not dry_run:
            try:
                if not any(runtime_dir.iterdir()):
                    runtime_dir.rmdir()
                    removed.append(".antios/runtime/")
            except Exception:
                pass

        # Clean .antios/backups directory if present
        backup_dir = self.target_root / ".antios/backups"
        if backup_dir.is_dir() and not dry_run:
            try:
                shutil.rmtree(backup_dir)
            except Exception:
                pass

        # Remove .antios directory if empty or contains only non-user files
        antios_dir = self.target_root / ".antios"
        if antios_dir.is_dir():
            remaining_files = [p for p in antios_dir.rglob("*") if p.is_file()]
            if not remaining_files:
                if not dry_run:
                    try:
                        shutil.rmtree(antios_dir)
                    except Exception:
                        pass
                removed.append(".antios/")

        # Remove .agents/skills/antios directory if empty
        skill_antios_dir = self.target_root / ".agents/skills/antios"
        if skill_antios_dir.is_dir():
            if not dry_run:
                try:
                    shutil.rmtree(skill_antios_dir)
                except Exception:
                    pass
            removed.append(".agents/skills/antios/")

        # Verify removal
        residuals: List[str] = []
        if not dry_run:
            if (self.target_root / ".antios").exists():
                antios_files = [p for p in (self.target_root / ".antios").rglob("*") if p.is_file()]
                unexpected = []
                for af in antios_files:
                    rel = str(af.relative_to(self.target_root)).replace("\\", "/")
                    if not (manifest and manifest.is_artifact_user_owned(rel)):
                        unexpected.append(rel)
                if unexpected:
                    residuals.append(f".antios ({len(unexpected)} unexpected files)")
            if (self.target_root / "antios.config.json").exists():
                if not (manifest and manifest.is_artifact_user_owned("antios.config.json")):
                    residuals.append("antios.config.json")

        status = "SUCCESS" if len(residuals) == 0 else "PARTIAL"
        return LifecycleResult(
            operation="REMOVE",
            status=status,
            installation_state=InstallationState.REMOVED,
            adaptation_state=AdaptationState.UNADAPTED,
            removed_files=removed,
            issues=[f"Residual artifacts detected: {', '.join(residuals)}"] if residuals else [],
            summary=f"Removed AntiOS instance ({len(removed)} artifacts removed)." if not residuals else "Removed AntiOS with residuals.",
        )


    def verify(self) -> LifecycleResult:
        """Verifies installation health, manifest validity, and checksums."""
        issues: List[str] = []
        conflicts: List[str] = []

        manifest = load_manifest(self.target_root)
        if not manifest:
            return LifecycleResult(
                operation="VERIFY",
                status="ERROR",
                installation_state=InstallationState.UNINSTALLED,
                adaptation_state=AdaptationState.UNADAPTED,
                issues=["AntiOS is not installed: .antios/manifest.json not found."],
                summary="Verification failed: instance not installed.",
            )

        # 1. Validate manifest schema
        is_valid, schema_issues = manifest.validate()
        if not is_valid:
            issues.extend(schema_issues)

        # 2. Check checksums of all tracked artifacts
        tracker = ProvenanceTracker(self.target_root, manifest)
        provenance_conflicts = tracker.audit_artifacts()
        for pc in provenance_conflicts:
            if pc.conflict_type in ("MISSING_MANAGED", "MISSING_GENERATED"):
                issues.append(pc.description)
            elif pc.conflict_type == "USER_MODIFIED":
                conflicts.append(pc.description)

        # 3. Check manifest fingerprint staleness
        try:
            current_profile = discover_project(str(self.target_root))
            current_fp = _resolve_project_fingerprint(current_profile, self.target_root)
            if manifest.project_fingerprint != current_fp:
                issues.append("Manifest fingerprint drift: target manifests have changed since last adaptation.")
        except Exception as e:
            issues.append(f"Failed to verify manifest fingerprint: {e}")

        # 4. Check runtime closure (Phases 79–82)
        try:
            from framework.core.runtime_contract import verify_runtime_closure
            closure_res = verify_runtime_closure(self.target_root)
            if not closure_res.is_closed:
                for viol in closure_res.violations:
                    if viol not in issues:
                        issues.append(viol)
        except Exception as e:
            issues.append(f"Failed to verify runtime closure: {e}")

        status = "SUCCESS" if len(issues) == 0 else "ERROR"
        if status == "SUCCESS" and len(conflicts) > 0:
            status = "CONFLICT"

        return LifecycleResult(
            operation="VERIFY",
            status=status,
            installation_state=manifest.installation_state,
            adaptation_state=manifest.adaptation_state,
            manifest=manifest,
            conflicts=conflicts,
            issues=issues,
            summary=f"Verification complete: {status} ({len(issues)} issues, {len(conflicts)} conflicts).",
        )
