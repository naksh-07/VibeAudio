"""AntiOS 3.0 Multi-Workspace Path Resolution Engine.

Provides deterministic, canonical path resolution, multi-workspace containment,
longest-prefix matching, and project-root discovery.
Pure Python standard library (zero external dependencies).
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple


def canonicalize_path(path: str) -> str:
    """Canonicalizes a path with case normalization, symlink resolution, and separator cleaning.

    Handles:
    - Traversal (../, ./)
    - Mixed separators (/ and \\)
    - Windows drive letter case normalization (c: vs C:)
    - Symlink / realpath resolution
    """
    if not path or not isinstance(path, str):
        return ""
    # Normalize separators and dots
    norm = os.path.normpath(path.strip())
    # Resolve absolute path and symlinks
    abs_path = os.path.abspath(norm)
    try:
        real_path = os.path.realpath(abs_path)
    except Exception:
        real_path = abs_path
    # Normalizes case on Windows/macOS, keeps case on Linux
    return os.path.normcase(real_path)


def is_contained(target_canonical: str, root_canonical: str) -> bool:
    """Safely checks whether target_canonical is within or equal to root_canonical.

    Guarantees:
    - Prevents sibling prefix collisions ('/work/repo' vs '/work/repo-extra')
    - Handles Windows drive differences cleanly (returns False, never raises)
    - Prevents directory traversal escape
    """
    if not target_canonical or not root_canonical:
        return False
    try:
        common = os.path.commonpath([target_canonical, root_canonical])
        return common == root_canonical
    except (ValueError, Exception):
        # Different Windows drives or invalid paths
        return False


def resolve_matching_workspace(
    target_path: str,
    workspace_paths: List[str],
    cwd: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Resolves a target path against an authorized workspace_paths list.

    Implements:
    - Canonicalization of all inputs
    - Relative path resolution (anchoring to matching workspace or cwd)
    - Longest-prefix matching among multiple enclosing workspace roots
    - Rejection of paths outside all workspaces

    Returns:
    - (matched_workspace_canonical, target_canonical) or (None, target_canonical)
    """
    if not target_path or not isinstance(target_path, str):
        return None, None
    if not workspace_paths or not isinstance(workspace_paths, list):
        return None, None

    # Canonicalize all valid workspace roots
    canonical_roots: List[Tuple[str, str]] = []  # (canonical, original)
    for ws in workspace_paths:
        if isinstance(ws, str) and ws.strip():
            c_ws = canonicalize_path(ws)
            if c_ws:
                canonical_roots.append((c_ws, ws))

    if not canonical_roots:
        return None, None

    # Handle relative target_path
    if not os.path.isabs(target_path):
        # Check if target matches relative to any existing workspace root
        matched_target_canonical: Optional[str] = None
        best_candidate_root: Optional[str] = None

        # If cwd is inside one of the workspaces, prefer anchoring to cwd's workspace
        norm_cwd = canonicalize_path(cwd or os.getcwd())
        cwd_workspaces = [c_root for c_root, _ in canonical_roots if is_contained(norm_cwd, c_root)]
        if cwd_workspaces:
            # Sort by longest prefix
            cwd_workspaces.sort(key=len, reverse=True)
            primary_root = cwd_workspaces[0]
            candidate_abs = os.path.abspath(os.path.join(primary_root, target_path))
            candidate_canon = canonicalize_path(candidate_abs)
            if is_contained(candidate_canon, primary_root):
                return primary_root, candidate_canon

        # Try anchoring to each workspace root to see if file exists
        for c_root, _ in canonical_roots:
            candidate_abs = os.path.abspath(os.path.join(c_root, target_path))
            candidate_canon = canonicalize_path(candidate_abs)
            if os.path.exists(candidate_canon) and is_contained(candidate_canon, c_root):
                matched_target_canonical = candidate_canon
                best_candidate_root = c_root
                break

        if matched_target_canonical and best_candidate_root:
            return best_candidate_root, matched_target_canonical

        # If file does not exist yet, anchor to the first workspace or longest matching cwd workspace
        default_root = canonical_roots[0][0]
        target_abs = os.path.abspath(os.path.join(default_root, target_path))
        target_canonical = canonicalize_path(target_abs)
    else:
        target_canonical = canonicalize_path(target_path)

    # Find all workspace roots that contain target_canonical
    containing_roots = [
        c_root for c_root, _ in canonical_roots
        if is_contained(target_canonical, c_root)
    ]

    if not containing_roots:
        return None, target_canonical

    # Longest-prefix match: sort by length descending to pick the most specific root
    containing_roots.sort(key=len, reverse=True)
    return containing_roots[0], target_canonical


def discover_project_root(
    starting_dir: Optional[str] = None,
    script_file: Optional[str] = None,
    workspace_paths: Optional[List[str]] = None,
) -> str:
    """Deterministically discovers the sovereign repository root.

    Does NOT assume cwd == project_root.
    Evaluates:
    1. Matching entry in workspace_paths if provided
    2. Upward directory walk from starting_dir or cwd looking for .git, antios.config.json, .agents/routes.json
    3. Upward walk from script_file location if provided
    4. Safe fallback to cwd or starting_dir
    """
    candidates_to_check: List[str] = []

    if starting_dir and os.path.isdir(starting_dir):
        candidates_to_check.append(starting_dir)

    cwd = os.getcwd()
    if cwd not in candidates_to_check:
        candidates_to_check.append(cwd)

    if script_file:
        try:
            s_dir = os.path.dirname(os.path.abspath(script_file))
            candidates_to_check.append(s_dir)
        except Exception:
            pass

    # If workspace_paths is given, check them
    if workspace_paths:
        for ws in workspace_paths:
            if isinstance(ws, str) and os.path.isdir(ws):
                c_ws = canonicalize_path(ws)
                if c_ws not in candidates_to_check:
                    candidates_to_check.append(c_ws)

    # Perform upward walk for each starting candidate
    for start in candidates_to_check:
        cur = os.path.abspath(start)
        while True:
            # Check for definitive markers
            if os.path.isdir(os.path.join(cur, ".git")):
                return canonicalize_path(cur)
            if os.path.isfile(os.path.join(cur, "antios.config.json")):
                return canonicalize_path(cur)
            if os.path.isfile(os.path.join(cur, ".agents", "routes.json")):
                return canonicalize_path(cur)

            parent = os.path.dirname(cur)
            if parent == cur:
                # Reached root of drive
                break
            cur = parent

    # Fallback: if starting_dir is valid, return it
    if starting_dir and os.path.isdir(starting_dir):
        return canonicalize_path(starting_dir)
    return canonicalize_path(cwd)
