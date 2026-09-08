"""AntiOS 3.0 Freshness & Drift Detection Engine.

Embeds zero-daemon cryptographic repository freshness checking via
the Combined Git Token protocol:
    Token = SHA-256(git rev-parse HEAD + "\\n" + git status --porcelain)[:16]

Constitutional Invariants:
- INV-09: Exact cryptographic state only (zero vector embeddings).
- INV-10: 4-Zone ownership boundary.
- INV-11: Standard library only (hashlib, os, subprocess, sys, time, typing).
- INV-15: Zero background daemons; executes synchronously in turn lifecycle (< 100ms).
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time
from typing import List, Optional, Tuple


def compute_git_token(repo_root: str, timeout: int = 5) -> Tuple[str, List[str], str, float]:
    """Computes the Combined Git Token and list of dirty files.

    Returns:
        (combined_token, dirty_files, head_sha, latency_ms)
    """
    t0 = time.perf_counter()
    head_sha = ""
    status_raw = ""
    dirty_files: List[str] = []

    try:
        # 1. git rev-parse HEAD
        p_head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True if os.name == "nt" else False,
        )
        if p_head.returncode == 0:
            head_sha = p_head.stdout.strip()
        else:
            head_sha = "NO_HEAD"

        # 2. git status --porcelain
        p_status = subprocess.run(
            ["git", "status", "--porcelain", "-uall"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True if os.name == "nt" else False,
        )
        if p_status.returncode == 0:
            status_raw = p_status.stdout.rstrip()
            filtered_lines: List[str] = []
            for line in status_raw.splitlines():
                if len(line) > 3:
                    path_part = line[3:].strip()
                    # Handle renames e.g. R  old -> new
                    if " -> " in path_part:
                        path_part = path_part.split(" -> ")[1].strip()
                    if path_part.startswith('"') and path_part.endswith('"'):
                        path_part = path_part[1:-1]
                    norm_part = path_part.replace("\\", "/").rstrip("/")
                    if (
                        norm_part.startswith(".agents/cache")
                        or norm_part == ".agents/telemetry.ndjson"
                        or norm_part == ".agents/telemetry.db"
                    ):
                        continue
                    dirty_files.append(path_part)
                    filtered_lines.append(line)
            status_raw = "\n".join(filtered_lines)
        else:
            status_raw = "NO_STATUS"

    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        head_sha = "GIT_UNAVAILABLE"
        status_raw = "GIT_UNAVAILABLE"

    token_material = f"{head_sha}\n{status_raw}".encode("utf-8")
    combined_token = hashlib.sha256(token_material).hexdigest()[:16]
    latency_ms = (time.perf_counter() - t0) * 1000.0

    return combined_token, dirty_files, head_sha, latency_ms


def get_cache_token_path(repo_root: str) -> str:
    """Returns canonical path to cached git token."""
    return os.path.join(repo_root, ".agents", "cache", "git_token")


def read_cached_token(repo_root: str) -> Optional[str]:
    """Reads cached git token from .agents/cache/git_token if it exists."""
    token_path = get_cache_token_path(repo_root)
    if os.path.isfile(token_path):
        try:
            with open(token_path, "r", encoding="utf-8") as f:
                val = f.read().strip()
                return val if val else None
        except OSError:
            return None
    return None


def write_cached_token(repo_root: str, token: str) -> bool:
    """Atomically writes git token to .agents/cache/git_token."""
    token_path = get_cache_token_path(repo_root)
    cache_dir = os.path.dirname(token_path)
    try:
        os.makedirs(cache_dir, exist_ok=True)
        tmp_path = f"{token_path}.tmp.{os.getpid()}"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(token + "\n")
        # Atomic rename on POSIX, replace on Windows
        if os.name == "nt":
            if os.path.exists(token_path):
                os.replace(tmp_path, token_path)
            else:
                os.rename(tmp_path, token_path)
        else:
            os.replace(tmp_path, token_path)
        return True
    except OSError:
        return False


def check_freshness(repo_root: str) -> Tuple[bool, str, List[str], float]:
    """Synchronously checks repository freshness against cached token.

    Returns:
        (is_fresh, current_token, dirty_files, latency_ms)

    - If is_fresh is True: current working tree + HEAD match cache; 0ms NO-OP downstream.
    - If is_fresh is False: repo has committed or uncommitted changes; requires incremental update.
    """
    cached_token = read_cached_token(repo_root)
    current_token, dirty_files, _head_sha, latency_ms = compute_git_token(repo_root)

    if cached_token is not None and cached_token == current_token:
        return True, current_token, dirty_files, latency_ms

    return False, current_token, dirty_files, latency_ms
