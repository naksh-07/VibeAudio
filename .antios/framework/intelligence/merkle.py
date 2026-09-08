"""AntiOS 3.0 Hierarchical Merkle Tree Engine.

Maintains cryptographic hash trees of repository working trees with
sub-millisecond bubble-up recalculation (< 0.1 ms / 100 µs) along dirty paths.

Constitutional Invariants:
- INV-09: Exact cryptographic Merkle state only (zero vector databases).
- INV-10: 4-Zone ownership boundary.
- INV-11: Standard library only (hashlib, json, os, time, typing).
- INV-15: Zero background daemons; purely synchronous recalculation.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional, Set, Tuple

DEFAULT_IGNORE_DIRS: Set[str] = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    ".cache",
    "sandbox",
}

DEFAULT_IGNORE_FILES: Set[str] = {
    ".DS_Store",
    "Thumbs.db",
}


class MerkleNode:
    """Represents a directory node in the hierarchical Merkle tree."""

    __slots__ = ("rel_path", "file_hashes", "children", "node_hash")

    def __init__(self, rel_path: str = ""):
        self.rel_path: str = rel_path.replace("\\", "/").strip("/")
        self.file_hashes: Dict[str, str] = {}
        self.children: Dict[str, MerkleNode] = {}
        self.node_hash: str = ""

    def compute_hash(self) -> str:
        """Calculates SHA-256 digest over sorted child files and subdirectories."""
        h = hashlib.sha256()
        for fname in sorted(self.file_hashes.keys()):
            h.update(f"F:{fname}:{self.file_hashes[fname]}\n".encode("utf-8"))
        for cname in sorted(self.children.keys()):
            h.update(f"D:{cname}:{self.children[cname].node_hash}\n".encode("utf-8"))
        self.node_hash = h.hexdigest()
        return self.node_hash

    def to_dict(self) -> Dict[str, Any]:
        """Serializes node to recursive dictionary."""
        return {
            "p": self.rel_path,
            "h": self.node_hash,
            "f": self.file_hashes,
            "c": {name: child.to_dict() for name, child in self.children.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MerkleNode:
        """Deserializes node from dictionary."""
        node = cls(data.get("p", ""))
        node.node_hash = data.get("h", "")
        node.file_hashes = data.get("f", {})
        raw_children = data.get("c", {})
        for name, c_data in raw_children.items():
            node.children[name] = cls.from_dict(c_data)
        return node


class MerkleTree:
    """Hierarchical Merkle tree root for an entire repository workspace."""

    def __init__(self, root_dir: str):
        self.root_dir: str = os.path.abspath(root_dir)
        self.root_node: MerkleNode = MerkleNode("")
        self.last_built: float = 0.0

    @property
    def root_hash(self) -> str:
        return self.root_node.node_hash

    def build(
        self,
        ignore_dirs: Optional[Set[str]] = None,
        ignore_files: Optional[Set[str]] = None,
    ) -> Tuple[str, float]:
        """Builds full Merkle tree by walking repository filesystem.

        Returns:
            (root_hash, build_latency_ms)
        """
        t0 = time.perf_counter()
        ignored_d = DEFAULT_IGNORE_DIRS if ignore_dirs is None else ignore_dirs
        ignored_f = DEFAULT_IGNORE_FILES if ignore_files is None else ignore_files

        norm_root = os.path.normpath(self.root_dir)
        nodes: Dict[str, MerkleNode] = {norm_root: MerkleNode("")}

        for dirpath, dirnames, filenames in os.walk(norm_root):
            # Prune ignored directory trees
            dirnames[:] = [d for d in dirnames if d not in ignored_d and not d.startswith(".agents")]
            rel_dir = os.path.relpath(dirpath, norm_root)
            curr_rel = "" if rel_dir == "." else rel_dir.replace("\\", "/")
            curr_node = nodes.setdefault(dirpath, MerkleNode(curr_rel))

            for f in filenames:
                if f in ignored_f or f.endswith(".tmp") or f.endswith(".pyc"):
                    continue
                file_full = os.path.join(dirpath, f)
                try:
                    with open(file_full, "rb") as fp:
                        content = fp.read()
                        curr_node.file_hashes[f] = hashlib.sha256(content).hexdigest()
                except (OSError, IOError):
                    pass

            for d in dirnames:
                child_full = os.path.join(dirpath, d)
                child_rel = f"{curr_rel}/{d}".strip("/")
                nodes[child_full] = MerkleNode(child_rel)
                curr_node.children[d] = nodes[child_full]

        # Post-order computation of hashes (deepest directories first)
        for dpath in sorted(nodes.keys(), key=lambda x: len(x), reverse=True):
            nodes[dpath].compute_hash()

        self.root_node = nodes[norm_root]
        self.last_built = time.time()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return self.root_hash, dt_ms

    def update_file(
        self,
        rel_path: str,
        content: Optional[bytes] = None,
        is_deleted: bool = False,
    ) -> Tuple[str, float]:
        """Incrementally recalculates hash tree along a single file path.

        Performs sub-millisecond (< 0.1 ms / 100 µs) bubble-up recalculation
        from leaf to root.

        Returns:
            (new_root_hash, update_latency_ms)
        """
        t0 = time.perf_counter()
        clean_rel = rel_path.replace("\\", "/").strip("/")
        parts = clean_rel.split("/")
        filename = parts[-1]
        dir_parts = parts[:-1]

        # Compute or fetch new file hash
        new_file_hash: Optional[str] = None
        if not is_deleted:
            if content is not None:
                new_file_hash = hashlib.sha256(content).hexdigest()
            else:
                full_path = os.path.join(self.root_dir, *parts)
                try:
                    with open(full_path, "rb") as fp:
                        new_file_hash = hashlib.sha256(fp.read()).hexdigest()
                except (OSError, IOError):
                    # If file doesn't exist on disk, treat as deleted
                    is_deleted = True

        # Traverse from root down to parent node, building path stack
        curr = self.root_node
        path_stack: List[MerkleNode] = [curr]
        accumulated_rel = ""

        for part in dir_parts:
            accumulated_rel = f"{accumulated_rel}/{part}".strip("/")
            if part not in curr.children:
                new_child = MerkleNode(accumulated_rel)
                curr.children[part] = new_child
            curr = curr.children[part]
            path_stack.append(curr)

        # Update leaf file hash
        if is_deleted:
            curr.file_hashes.pop(filename, None)
        else:
            if new_file_hash is not None:
                curr.file_hashes[filename] = new_file_hash

        # Bubble up recalculation from parent of leaf to root
        for node in reversed(path_stack):
            node.compute_hash()

        dt_ms = (time.perf_counter() - t0) * 1000.0
        return self.root_hash, dt_ms

    def update_batch(
        self,
        dirty_rel_paths: List[str],
    ) -> Tuple[str, float]:
        """Incrementally recalculates hash tree for multiple modified files."""
        t0 = time.perf_counter()
        for rel_p in dirty_rel_paths:
            self.update_file(rel_p)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return self.root_hash, dt_ms

    def save(self, cache_file_path: Optional[str] = None) -> bool:
        """Serializes Merkle tree to JSON cache."""
        target_path = cache_file_path or os.path.join(
            self.root_dir, ".agents", "cache", "merkle_tree.json"
        )
        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            tmp_path = f"{target_path}.tmp.{os.getpid()}"
            payload = {
                "version": "3.0",
                "root_dir": self.root_dir,
                "timestamp": self.last_built or time.time(),
                "root": self.root_node.to_dict(),
            }
            with open(tmp_path, "w", encoding="utf-8") as fp:
                json.dump(payload, fp, separators=(",", ":"))
            if os.name == "nt" and os.path.exists(target_path):
                os.replace(tmp_path, target_path)
            else:
                os.replace(tmp_path, target_path)
            return True
        except (OSError, IOError):
            return False

    @classmethod
    def load(cls, repo_root: str, cache_file_path: Optional[str] = None) -> Optional[MerkleTree]:
        """Loads Merkle tree from JSON cache. Rebuilds if corrupted or missing."""
        target_path = cache_file_path or os.path.join(
            repo_root, ".agents", "cache", "merkle_tree.json"
        )
        if not os.path.isfile(target_path):
            return None

        try:
            with open(target_path, "r", encoding="utf-8") as fp:
                data = json.load(fp)

            if not isinstance(data, dict) or data.get("version") != "3.0":
                return None

            tree = cls(repo_root)
            tree.last_built = float(data.get("timestamp", 0.0))
            raw_root = data.get("root")
            if not isinstance(raw_root, dict):
                return None
            tree.root_node = MerkleNode.from_dict(raw_root)
            return tree
        except Exception:
            # Corrupted cache: safely return None to trigger clean rebuild
            try:
                if os.path.exists(target_path):
                    os.remove(target_path)
            except OSError:
                pass
            return None
