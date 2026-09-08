"""AntiOS 2.0 Artifact Ownership & Provenance Engine.

Formalizes ownership tiers:
- GENERATED: Compiled by AntiOS, safe to regenerate if unmodified
- MANAGED: Initialized by AntiOS, may incorporate project adaptations
- USER_AUTHORED: Authored or customized by human maintainers, strictly protected
- PROJECT_PROTECTED: Declared project immutable zones
- ANTIOS_IMMUTABLE: AntiOS core governance files

Enforces the Fundamental Provenance Law:
"AntiOS must never overwrite user-owned project configuration merely because
its generated version differs. If ownership cannot be determined safely:
UNKNOWN -> DO NOT OVERWRITE -> SURFACE CONFLICT"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from framework.core.manifest import (
    ArtifactOwnership,
    ArtifactRecord,
    ProjectManifest,
)


@dataclass
class ProvenanceConflict:
    """Represents an artifact ownership or modification conflict."""
    path: str
    conflict_type: str  # USER_MODIFIED, UNTRACKED_COLLISION, STALE_REMOVAL, PROTECTED_COLLISION
    description: str
    on_disk_sha256: Optional[str] = None
    manifest_sha256: Optional[str] = None
    suggested_action: str = "SURFACE_CONFLICT"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "conflict_type": self.conflict_type,
            "description": self.description,
            "on_disk_sha256": self.on_disk_sha256,
            "manifest_sha256": self.manifest_sha256,
            "suggested_action": self.suggested_action,
        }


def compute_file_sha256(file_path: Union[str, Path]) -> Optional[str]:
    """Computes deterministic SHA-256 digest of a file with normalized LF newlines."""
    p = Path(file_path)
    if not p.is_file():
        return None
    try:
        raw_bytes = p.read_bytes()
        normalized = raw_bytes.replace(b"\r\n", b"\n")
        return hashlib.sha256(normalized).hexdigest()
    except Exception:
        return None


def classify_artifact(
    rel_path: str,
    manifest: Optional[ProjectManifest],
    target_root: Union[str, Path],
) -> Tuple[ArtifactOwnership, str]:
    """Classifies the ownership of an artifact path against manifest and disk state.

    Returns:
        (ArtifactOwnership, rationale)
    """
    norm_path = rel_path.replace("\\", "/").strip("/")
    abs_path = Path(target_root) / norm_path

    # 0. External System B / External Artifacts
    try:
        resolved_root = Path(target_root).resolve()
        resolved_abs = abs_path.resolve()
        if resolved_abs != resolved_root and resolved_root not in resolved_abs.parents:
            return ArtifactOwnership.EXTERNAL, "Path resides outside project repository boundary (External System B data)"
    except Exception:
        pass

    # 1. AntiOS Core Governance (Immutable)
    core_prefixes = (".agents/hooks.json", "framework/", "framework")
    if norm_path == "framework" or norm_path.startswith("framework/") or norm_path == ".agents/hooks.json":
        return ArtifactOwnership.ANTIOS_IMMUTABLE, "AntiOS core framework governance file"

    # 2. Check if path is in protected project zones
    if manifest:
        for pz in manifest.protected_paths:
            norm_pz = pz.replace("\\", "/").strip("/")
            if norm_path == norm_pz or norm_path.startswith(norm_pz + "/"):
                return ArtifactOwnership.PROJECT_PROTECTED, f"Declared protected path: '{pz}'"

    # 3. Check explicit user-owned paths
    if manifest and norm_path in manifest.user_owned_paths:
        return ArtifactOwnership.USER_AUTHORED, "Explicitly recorded as user-authored artifact"

    # 4. Check manifest managed paths
    if manifest and norm_path in manifest.managed_paths:
        rec = manifest.managed_paths[norm_path]
        if abs_path.is_file():
            current_sha = compute_file_sha256(abs_path)
            if current_sha and current_sha != rec.sha256:
                return ArtifactOwnership.USER_AUTHORED, "Managed artifact was modified by user"
        return ArtifactOwnership.MANAGED, "Tracked as AntiOS-managed artifact"

    # 5. Check manifest generated paths
    if manifest and norm_path in manifest.generated_paths:
        rec = manifest.generated_paths[norm_path]
        if abs_path.is_file():
            current_sha = compute_file_sha256(abs_path)
            if current_sha and current_sha != rec.sha256:
                return ArtifactOwnership.USER_AUTHORED, "Generated artifact was modified by user"
        return ArtifactOwnership.GENERATED, "Tracked as AntiOS-generated artifact"

    # 6. Pre-existing file not tracked in manifest -> USER_AUTHORED
    if abs_path.exists():
        return ArtifactOwnership.USER_AUTHORED, "Pre-existing untracked project artifact"

    # 7. Unborn / prospective path
    return ArtifactOwnership.GENERATED, "New uncommitted artifact candidate"


def can_safely_overwrite(
    rel_path: str,
    manifest: Optional[ProjectManifest],
    target_root: Union[str, Path],
    proposed_content_sha: Optional[str] = None,
) -> Tuple[bool, str]:
    """Determines whether AntiOS can safely write or overwrite an artifact.

    Enforces fail-closed protection against silent data destruction.
    """
    norm_path = rel_path.replace("\\", "/").strip("/")
    abs_path = Path(target_root) / norm_path

    # If no manifest exists:
    if manifest is None:
        if abs_path.exists():
            return False, f"File '{norm_path}' already exists on disk without AntiOS manifest (USER_AUTHORED). Failing closed."
        return True, "File does not exist on disk and no manifest exists; safe to create"

    # Check user-owned paths
    if norm_path in manifest.user_owned_paths:
        return False, f"Path '{norm_path}' is explicitly marked as USER_AUTHORED. Overwrite blocked."

    # Check if this path is an AntiOS managed or generated artifact
    is_antios_artifact = (
        norm_path == ".antios/manifest.json"
        or norm_path in manifest.managed_paths
        or norm_path in manifest.generated_paths
    )

    if is_antios_artifact:
        # If file does not exist yet on disk, safe to write
        if not abs_path.exists():
            return True, f"AntiOS artifact '{norm_path}' does not exist on disk; safe to create"

        current_disk_sha = compute_file_sha256(abs_path)

        if norm_path == ".antios/manifest.json":
            return True, "Manifest file safe to update"

        if norm_path in manifest.managed_paths:
            rec = manifest.managed_paths[norm_path]
            if current_disk_sha and current_disk_sha != rec.sha256:
                return False, f"Managed file '{norm_path}' was modified by the user (SHA mismatch). Overwrite blocked."
            return True, f"Managed file '{norm_path}' matches recorded AntiOS baseline; safe to update"

        if norm_path in manifest.generated_paths:
            rec = manifest.generated_paths[norm_path]
            if current_disk_sha and current_disk_sha != rec.sha256:
                return False, f"Generated file '{norm_path}' was modified by the user (SHA mismatch). Overwrite blocked."
            return True, f"Generated file '{norm_path}' matches recorded AntiOS baseline; safe to regenerate"

    # For non-AntiOS artifacts: check protected zones
    for pz in manifest.protected_paths:
        norm_pz = pz.replace("\\", "/").strip("/")
        if norm_path == norm_pz or norm_path.startswith(norm_pz + "/"):
            return False, f"Protected project path: '{pz}' cannot be modified or overwritten"

    if not abs_path.exists():
        return True, "New unmanaged file; safe to create"

    # File exists on disk but is NOT tracked by manifest -> UNKNOWN
    return False, f"File '{norm_path}' exists on disk but is not tracked by AntiOS manifest (UNKNOWN ownership). Failing closed."


class ProvenanceTracker:
    """Audits and tracks artifact provenance across a target project."""

    def __init__(self, target_root: Union[str, Path], manifest: Optional[ProjectManifest] = None):
        self.target_root = Path(target_root)
        self.manifest = manifest

    def audit_artifacts(self) -> List[ProvenanceConflict]:
        """Audits all manifest-tracked and key project paths for provenance conflicts."""
        conflicts: List[ProvenanceConflict] = []
        if not self.manifest:
            return conflicts

        # Check managed paths
        for rel_path, rec in self.manifest.managed_paths.items():
            abs_path = self.target_root / rel_path
            if not abs_path.is_file():
                conflicts.append(
                    ProvenanceConflict(
                        path=rel_path,
                        conflict_type="MISSING_MANAGED",
                        description=f"Managed artifact '{rel_path}' is missing from disk",
                        manifest_sha256=rec.sha256,
                        suggested_action="REPAIR",
                    )
                )
            else:
                current_sha = compute_file_sha256(abs_path)
                if current_sha and current_sha != rec.sha256:
                    rec.is_user_modified = True
                    conflicts.append(
                        ProvenanceConflict(
                            path=rel_path,
                            conflict_type="USER_MODIFIED",
                            description=f"Managed artifact '{rel_path}' was modified by user",
                            on_disk_sha256=current_sha,
                            manifest_sha256=rec.sha256,
                            suggested_action="PRESERVE_USER_MODIFICATION",
                        )
                    )

        # Check generated paths
        for rel_path, rec in self.manifest.generated_paths.items():
            abs_path = self.target_root / rel_path
            if not abs_path.is_file():
                conflicts.append(
                    ProvenanceConflict(
                        path=rel_path,
                        conflict_type="MISSING_GENERATED",
                        description=f"Generated artifact '{rel_path}' is missing from disk",
                        manifest_sha256=rec.sha256,
                        suggested_action="REGENERATE",
                    )
                )
            else:
                current_sha = compute_file_sha256(abs_path)
                if current_sha and current_sha != rec.sha256:
                    rec.is_user_modified = True
                    conflicts.append(
                        ProvenanceConflict(
                            path=rel_path,
                            conflict_type="USER_MODIFIED",
                            description=f"Generated artifact '{rel_path}' was modified by user",
                            on_disk_sha256=current_sha,
                            manifest_sha256=rec.sha256,
                            suggested_action="SURFACE_CONFLICT",
                        )
                    )

        # Check stale paths
        for rel_path in self.manifest.stale_paths:
            abs_path = self.target_root / rel_path
            if abs_path.exists():
                conflicts.append(
                    ProvenanceConflict(
                        path=rel_path,
                        conflict_type="STALE_REMNANT",
                        description=f"Stale artifact '{rel_path}' remains on disk",
                        suggested_action="SAFE_REMOVE",
                    )
                )

        return conflicts
