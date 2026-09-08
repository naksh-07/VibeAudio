"""AntiOS 3.x Upgrade & Reconciliation Engine.

Formalizes the deterministic, ownership-aware reconciliation model:
detect existing AntiOS instance
→ read manifest
→ compare versions / schema / profile
→ inspect current project state
→ calculate reconciliation plan
→ migrate required state
→ regenerate only AntiOS-owned generated artifacts
→ preserve project / user-owned material
→ reap obsolete unmodified generated artifacts
→ update manifest
→ recompile
→ run verification
→ declare upgrade successful

Strictly avoids "delete everything and reinstall" strategies.
Fully idempotent: running the same upgrade twice causes zero progressive damage or duplicated state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from framework.core.manifest import (
    ArtifactOwnership,
    ArtifactRecord,
    CURRENT_ANTIOS_VERSION,
    CURRENT_SCHEMA_VERSION,
    ProjectManifest,
)
from framework.core.provenance import compute_file_sha256
from framework.core.version import ANTIOS_VERSION, compare_versions


class ReconciliationAction(str, Enum):
    """Specific reconciliation action for an artifact."""
    UNTOUCHED = "UNTOUCHED"
    REGENERATE = "REGENERATE"
    CREATE = "CREATE"
    PRESERVE_USER_MODIFIED = "PRESERVE_USER_MODIFIED"
    PRESERVE_OBSOLETE_USER_MODIFIED = "PRESERVE_OBSOLETE_USER_MODIFIED"
    REAP_OBSOLETE = "REAP_OBSOLETE"
    RESTORE_MISSING = "RESTORE_MISSING"
    CONFLICT = "CONFLICT"


@dataclass
class ArtifactReconciliation:
    """Individual artifact reconciliation instruction."""
    path: str
    action: ReconciliationAction
    reason: str
    disk_sha256: Optional[str] = None
    manifest_sha256: Optional[str] = None
    target_sha256: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "action": self.action.value if isinstance(self.action, ReconciliationAction) else str(self.action),
            "reason": self.reason,
            "disk_sha256": self.disk_sha256,
            "manifest_sha256": self.manifest_sha256,
            "target_sha256": self.target_sha256,
        }


@dataclass
class ReconciliationPlan:
    """Declarative, deterministic upgrade and reconciliation plan."""
    installed_version: str
    target_version: str
    installed_schema_version: str
    target_schema_version: str
    project_id: str
    project_root: str
    schema_migration_required: bool
    actions: List[ArtifactReconciliation] = field(default_factory=list)
    can_safely_apply: bool = True
    issues: List[str] = field(default_factory=list)
    is_idempotent: bool = False
    summary: str = ""

    @property
    def regenerations(self) -> List[ArtifactReconciliation]:
        return [a for a in self.actions if a.action in (ReconciliationAction.REGENERATE, ReconciliationAction.RESTORE_MISSING)]

    @property
    def creations(self) -> List[ArtifactReconciliation]:
        return [a for a in self.actions if a.action == ReconciliationAction.CREATE]

    @property
    def reaped_obsolete(self) -> List[ArtifactReconciliation]:
        return [a for a in self.actions if a.action == ReconciliationAction.REAP_OBSOLETE]

    @property
    def preserved_user_modified(self) -> List[ArtifactReconciliation]:
        return [a for a in self.actions if a.action in (ReconciliationAction.PRESERVE_USER_MODIFIED, ReconciliationAction.PRESERVE_OBSOLETE_USER_MODIFIED)]

    @property
    def untouched(self) -> List[ArtifactReconciliation]:
        return [a for a in self.actions if a.action == ReconciliationAction.UNTOUCHED]

    @property
    def conflicts(self) -> List[ArtifactReconciliation]:
        return [a for a in self.actions if a.action == ReconciliationAction.CONFLICT]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "installed_version": self.installed_version,
            "target_version": self.target_version,
            "installed_schema_version": self.installed_schema_version,
            "target_schema_version": self.target_schema_version,
            "project_id": self.project_id,
            "schema_migration_required": self.schema_migration_required,
            "is_idempotent": self.is_idempotent,
            "can_safely_apply": self.can_safely_apply,
            "total_actions": len(self.actions),
            "counts": {
                "regenerate": len(self.regenerations),
                "create": len(self.creations),
                "reap_obsolete": len(self.reaped_obsolete),
                "preserve_user_modified": len(self.preserved_user_modified),
                "untouched": len(self.untouched),
                "conflicts": len(self.conflicts),
            },
            "actions": [a.to_dict() for a in self.actions],
            "issues": self.issues,
            "summary": self.summary,
        }

    def format_human(self) -> str:
        lines = [
            "=" * 60,
            f"AntiOS Upgrade & Reconciliation Plan",
            f"Target:               {self.project_root}",
            f"Installed Version:    {self.installed_version} (Schema: {self.installed_schema_version})",
            f"Target Version:       {self.target_version} (Schema: {self.target_schema_version})",
            f"Schema Migration:     {'YES' if self.schema_migration_required else 'NO'}",
            f"Safe to Apply:        {'YES' if self.can_safely_apply else 'NO (Conflicts detected)'}",
            f"Idempotent:           {'YES (Already up to date)' if self.is_idempotent else 'NO (Changes pending)'}",
            "=" * 60,
            "Reconciliation Breakdown:",
            f"  - Regenerate (AntiOS-owned):     {len(self.regenerations)}",
            f"  - Create (New artifacts):        {len(self.creations)}",
            f"  - Reap Obsolete:                 {len(self.reaped_obsolete)}",
            f"  - Preserve User-Modified:        {len(self.preserved_user_modified)}",
            f"  - Untouched / Up-to-Date:        {len(self.untouched)}",
            f"  - Conflicts / Blockers:          {len(self.conflicts)}",
        ]
        if self.preserved_user_modified:
            lines.append("")
            lines.append("Preserved User Modifications (will not be overwritten):")
            for p in self.preserved_user_modified:
                lines.append(f"  * {p.path}: {p.reason}")
        if self.reaped_obsolete:
            lines.append("")
            lines.append("Obsolete Generated Artifacts to Reap:")
            for r in self.reaped_obsolete:
                lines.append(f"  - {r.path}")
        if self.conflicts:
            lines.append("")
            lines.append("Conflicts Requiring Human Intervention:")
            for c in self.conflicts:
                lines.append(f"  ! {c.path}: {c.reason}")
        if self.issues:
            lines.append("")
            lines.append("Diagnostics:")
            for iss in self.issues:
                lines.append(f"  ! {iss}")
        lines.append("=" * 60)
        return "\n".join(lines)


def _compute_str_sha256(content: str) -> str:
    norm = content.replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha256(norm).hexdigest()


class ReconciliationEngine:
    """Calculates and executes deterministic instance upgrades."""

    @classmethod
    def calculate_plan(
        cls,
        target_root: Union[str, Path],
        current_manifest: ProjectManifest,
        compiled_files: Dict[str, str],
        target_version: Optional[str] = None,
        target_schema_version: Optional[str] = None,
        force: bool = False,
    ) -> ReconciliationPlan:
        """Calculates a deterministic reconciliation plan without mutating files."""
        root = Path(target_root).resolve()
        effective_target_version = target_version or ANTIOS_VERSION
        effective_target_schema = target_schema_version or CURRENT_SCHEMA_VERSION

        schema_migration_needed = current_manifest.schema_version != effective_target_schema
        actions: List[ArtifactReconciliation] = []
        issues: List[str] = []

        # 1. Inspect all compiled files from new version
        for rel_path, new_content in sorted(compiled_files.items()):
            if rel_path == ".antios/manifest.json":
                continue

            abs_path = root / rel_path
            target_sha = _compute_str_sha256(new_content)

            # Check if recorded in user_owned_paths
            if rel_path in current_manifest.user_owned_paths:
                actions.append(
                    ArtifactReconciliation(
                        path=rel_path,
                        action=ReconciliationAction.PRESERVE_USER_MODIFIED,
                        reason="Path explicitly tracked as user-owned; strictly preserved",
                        disk_sha256=compute_file_sha256(abs_path) if abs_path.is_file() else None,
                        target_sha256=target_sha,
                    )
                )
                continue

            if abs_path.is_file():
                disk_sha = compute_file_sha256(abs_path)
                was_managed = rel_path in current_manifest.managed_paths
                was_generated = rel_path in current_manifest.generated_paths

                if was_managed or was_generated:
                    rec = current_manifest.managed_paths.get(rel_path) or current_manifest.generated_paths.get(rel_path)
                    manifest_sha = rec.sha256 if rec else None

                    if disk_sha and manifest_sha and disk_sha != manifest_sha:
                        # User modified this AntiOS file!
                        actions.append(
                            ArtifactReconciliation(
                                path=rel_path,
                                action=ReconciliationAction.PRESERVE_USER_MODIFIED,
                                reason="User modified AntiOS artifact on disk; preserved without overwrite",
                                disk_sha256=disk_sha,
                                manifest_sha256=manifest_sha,
                                target_sha256=target_sha,
                            )
                        )
                    else:
                        # Disk matches recorded manifest baseline
                        if disk_sha == target_sha:
                            actions.append(
                                ArtifactReconciliation(
                                    path=rel_path,
                                    action=ReconciliationAction.UNTOUCHED,
                                    reason="Artifact matches target release; already up to date",
                                    disk_sha256=disk_sha,
                                    manifest_sha256=manifest_sha,
                                    target_sha256=target_sha,
                                )
                            )
                        else:
                            actions.append(
                                ArtifactReconciliation(
                                    path=rel_path,
                                    action=ReconciliationAction.REGENERATE,
                                    reason="AntiOS-owned unmodified artifact; updated to new release",
                                    disk_sha256=disk_sha,
                                    manifest_sha256=manifest_sha,
                                    target_sha256=target_sha,
                                )
                            )
                else:
                    # File exists on disk but was NOT tracked in previous manifest!
                    if disk_sha == target_sha:
                        actions.append(
                            ArtifactReconciliation(
                                path=rel_path,
                                action=ReconciliationAction.UNTOUCHED,
                                reason="Untracked file matches target; adopting into manifest",
                                disk_sha256=disk_sha,
                                target_sha256=target_sha,
                            )
                        )
                    elif force:
                        actions.append(
                            ArtifactReconciliation(
                                path=rel_path,
                                action=ReconciliationAction.REGENERATE,
                                reason="Untracked file overwritten due to explicit force flag",
                                disk_sha256=disk_sha,
                                target_sha256=target_sha,
                            )
                        )
                    else:
                        actions.append(
                            ArtifactReconciliation(
                                path=rel_path,
                                action=ReconciliationAction.CONFLICT,
                                reason="Pre-existing file not tracked by AntiOS manifest; blocked from overwrite",
                                disk_sha256=disk_sha,
                                target_sha256=target_sha,
                            )
                        )
            else:
                # File does not exist on disk
                was_tracked = rel_path in current_manifest.artifacts
                if was_tracked:
                    actions.append(
                        ArtifactReconciliation(
                            path=rel_path,
                            action=ReconciliationAction.RESTORE_MISSING,
                            reason="Missing AntiOS artifact restored from target release",
                            target_sha256=target_sha,
                        )
                    )
                else:
                    actions.append(
                        ArtifactReconciliation(
                            path=rel_path,
                            action=ReconciliationAction.CREATE,
                            reason="New AntiOS artifact introduced in target release",
                            target_sha256=target_sha,
                        )
                    )

        # 2. Inspect old generated paths for obsolete artifacts
        for old_gen_path, rec in current_manifest.generated_paths.items():
            if old_gen_path not in compiled_files:
                abs_old = root / old_gen_path
                if abs_old.is_file():
                    disk_sha = compute_file_sha256(abs_old)
                    if disk_sha and rec.sha256 and disk_sha == rec.sha256:
                        actions.append(
                            ArtifactReconciliation(
                                path=old_gen_path,
                                action=ReconciliationAction.REAP_OBSOLETE,
                                reason="Obsolete unmodified AntiOS generated artifact; scheduled for safe removal",
                                disk_sha256=disk_sha,
                                manifest_sha256=rec.sha256,
                            )
                        )
                    else:
                        actions.append(
                            ArtifactReconciliation(
                                path=old_gen_path,
                                action=ReconciliationAction.PRESERVE_OBSOLETE_USER_MODIFIED,
                                reason="Obsolete artifact was modified by user; preserved as user-owned",
                                disk_sha256=disk_sha,
                                manifest_sha256=rec.sha256,
                            )
                        )

        # Determine idempotency: version matches, no regenerations, creations, or reaps needed
        has_mutations = any(
            a.action in (
                ReconciliationAction.REGENERATE,
                ReconciliationAction.CREATE,
                ReconciliationAction.REAP_OBSOLETE,
                ReconciliationAction.RESTORE_MISSING,
            )
            for a in actions
        )
        is_idempotent = (
            current_manifest.antios_version == effective_target_version
            and not schema_migration_needed
            and not has_mutations
        )

        has_conflicts = any(a.action == ReconciliationAction.CONFLICT for a in actions)
        can_safely_apply = not has_conflicts or force

        summary = f"Reconciliation Plan: {len(actions)} total checks. "
        if is_idempotent:
            summary += "Instance is already up to date (idempotent no-op)."
        elif not can_safely_apply:
            summary += f"Upgrade blocked by {len([a for a in actions if a.action == ReconciliationAction.CONFLICT])} conflict(s)."
        else:
            reap_cnt = len([a for a in actions if a.action == ReconciliationAction.REAP_OBSOLETE])
            regen_cnt = len([a for a in actions if a.action in (ReconciliationAction.REGENERATE, ReconciliationAction.RESTORE_MISSING)])
            create_cnt = len([a for a in actions if a.action == ReconciliationAction.CREATE])
            pres_cnt = len([a for a in actions if a.action in (ReconciliationAction.PRESERVE_USER_MODIFIED, ReconciliationAction.PRESERVE_OBSOLETE_USER_MODIFIED)])
            summary += f"Scheduled: {regen_cnt} updates, {create_cnt} new files, {reap_cnt} removals, {pres_cnt} preserved user modifications."

        return ReconciliationPlan(
            installed_version=current_manifest.antios_version,
            target_version=effective_target_version,
            installed_schema_version=current_manifest.schema_version,
            target_schema_version=effective_target_schema,
            project_id=str(current_manifest.metadata.get("project_id", "unknown")),
            project_root=str(root),
            schema_migration_required=schema_migration_needed,
            actions=actions,
            can_safely_apply=can_safely_apply,
            issues=issues,
            is_idempotent=is_idempotent,
            summary=summary,
        )
