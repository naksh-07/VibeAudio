"""AntiOS 3.0 PreInvocation Hook.

Fires immediately prior to LLM inference turn.
Establishes lightweight turn context, zero-daemon cryptographic repository
freshness checking (< 100ms), and non-blocking telemetry logging.

Runtime Invariants:
- INV-09: Exact cryptographic state only (zero vector databases).
- INV-10: 4-Zone ownership boundary.
- INV-11: Zero framework imports (pure stdlib + local hook helpers).
- INV-12: Sanitized telemetry emission.
- INV-15: Zero background daemons (synchronous turn-hook lifecycle execution).
- Bounded execution (< 100ms for clean turns).
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# Sibling import bootstrap (zero framework imports)
HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
if HOOK_DIR not in sys.path:
    sys.path.insert(0, HOOK_DIR)

import path_resolver
import emitter


def _compute_git_token_stdlib(repo_root: str, timeout: int = 5) -> Tuple[str, List[str], str, float]:
    """Pure stdlib Combined Git Token computation for target runtime isolation."""
    t0 = time.perf_counter()
    head_sha = "NO_HEAD"
    status_raw = ""
    dirty_files: List[str] = []

    try:
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
                    p = line[3:].strip()
                    if " -> " in p:
                        p = p.split(" -> ")[1].strip()
                    if p.startswith('"') and p.endswith('"'):
                        p = p[1:-1]
                    norm_p = p.replace("\\", "/").rstrip("/")
                    if (
                        norm_p.startswith(".agents/cache")
                        or norm_p == ".agents/telemetry.ndjson"
                        or norm_p == ".agents/telemetry.db"
                    ):
                        continue
                    dirty_files.append(p)
                    filtered_lines.append(line)
            status_raw = "\n".join(filtered_lines)
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        head_sha = "GIT_UNAVAILABLE"
        status_raw = "GIT_UNAVAILABLE"

    token = hashlib.sha256(f"{head_sha}\n{status_raw}".encode("utf-8")).hexdigest()[:16]
    dt_ms = (time.perf_counter() - t0) * 1000.0
    return token, dirty_files, head_sha, dt_ms


def check_and_sync_freshness(project_root: str) -> Dict[str, Any]:
    """Synchronously checks repository freshness and maintains cache."""
    cache_token_file = os.path.join(project_root, ".agents", "cache", "git_token")
    cached_token: Optional[str] = None
    if os.path.isfile(cache_token_file):
        try:
            with open(cache_token_file, "r", encoding="utf-8") as f:
                cached_token = f.read().strip()
        except OSError:
            cached_token = None

    current_token, dirty_files, head_sha, dt_ms = _compute_git_token_stdlib(project_root)

    is_fresh = (cached_token is not None and cached_token == current_token)

    if not is_fresh:
        # Update token cache atomically
        try:
            os.makedirs(os.path.dirname(cache_token_file), exist_ok=True)
            tmp_file = f"{cache_token_file}.tmp.{os.getpid()}"
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(current_token + "\n")
            if os.name == "nt" and os.path.exists(cache_token_file):
                os.replace(tmp_file, cache_token_file)
            else:
                os.replace(tmp_file, cache_token_file)
        except OSError:
            pass

        # Try incremental Merkle update if available
        merkle_cache_path = os.path.join(project_root, ".agents", "cache", "merkle_tree.json")
        if os.path.isfile(merkle_cache_path):
            try:
                # Add project root to sys.path to access framework.intelligence if present
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)
                merkle_mod = importlib.import_module("framework.intelligence.merkle")
                tree = merkle_mod.MerkleTree.load(project_root, cache_file_path=merkle_cache_path)
                if tree is not None:
                    tree.update_batch(dirty_files)
                    tree.save(cache_file_path=merkle_cache_path)
            except Exception:
                pass

    return {
        "is_fresh": is_fresh,
        "token": current_token,
        "dirty_count": len(dirty_files),
        "latency_ms": round(dt_ms, 2),
    }


def main() -> None:
    try:
        raw_input = sys.stdin.read()
        input_data = json.loads(raw_input) if raw_input.strip() else {}

        workspace_paths = input_data.get("workspacePaths", [])
        project_root = path_resolver.discover_project_root(
            starting_dir=os.getcwd(),
            script_file=__file__,
            workspace_paths=workspace_paths if isinstance(workspace_paths, list) else None,
        )

        freshness_info = {}
        if project_root and os.path.isdir(project_root):
            try:
                freshness_info = check_and_sync_freshness(project_root)
            except Exception:
                pass

        # Non-blocking telemetry
        try:
            emitter.emit_event(
                project_root=project_root,
                event_type="pre_invocation",
                payload={
                    "invocationNum": input_data.get("invocationNum", 0),
                    "freshness": freshness_info,
                },
            )
        except Exception:
            pass

        # Return standard empty injection (Turn-0 Constitution in AGENTS.md handles static steering)
        print(json.dumps({}))
        sys.exit(0)

    except Exception:
        # PreInvocation fails open by platform contract
        print(json.dumps({}))
        sys.exit(0)


if __name__ == "__main__":
    main()
