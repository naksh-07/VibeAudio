"""AntiOS 2.0 Authoritative Version & Release Channel Management.

Single authoritative source of truth for AntiOS Semantic Versioning:
MAJOR.MINOR.PATCH[-PRERELEASE]
e.g. 2.0.0-beta.1

Formal Release Channels:
- stable: Production releases (e.g. 2.0.0)
- rc: Release candidates (e.g. 2.0.0-rc.1)
- beta: Beta preview releases (e.g. 2.0.0-beta.1)
- development: Untagged or local development builds
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, Optional, Tuple

# Canonical single source of truth
ANTIOS_VERSION: str = "3.0.0"
CURRENT_SCHEMA_VERSION: str = "2.0.0"
ADAPTER_SCHEMA_VERSION: str = "1.0"


class ReleaseChannel(str, Enum):
    """Formal release channels for AntiOS distribution."""
    STABLE = "stable"
    RC = "rc"
    BETA = "beta"
    DEVELOPMENT = "development"


# Semantic version regex matching MAJOR.MINOR.PATCH[-PRERELEASE]
SEMVER_REGEX = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:alpha|beta|rc|dev)\.(?:0|[1-9]\d*)|(?:alpha|beta|rc|dev)))?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SemVer:
    """Structured Semantic Version representation."""
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    channel: ReleaseChannel = ReleaseChannel.STABLE

    @classmethod
    def parse(cls, version_str: str) -> SemVer:
        """Parses a version string into a structured SemVer object."""
        if not version_str or not isinstance(version_str, str):
            raise ValueError(f"Invalid version string: '{version_str}'")

        cleaned = version_str.strip().lstrip("v")
        match = SEMVER_REGEX.match(cleaned)
        if not match:
            raise ValueError(
                f"Version '{version_str}' does not conform to Semantic Versioning (MAJOR.MINOR.PATCH[-PRERELEASE])."
            )

        major = int(match.group("major"))
        minor = int(match.group("minor"))
        patch = int(match.group("patch"))
        prerelease = match.group("prerelease")

        channel = ReleaseChannel.STABLE
        if prerelease:
            pre_lower = prerelease.lower()
            if "beta" in pre_lower:
                channel = ReleaseChannel.BETA
            elif "rc" in pre_lower:
                channel = ReleaseChannel.RC
            elif "alpha" in pre_lower or "dev" in pre_lower:
                channel = ReleaseChannel.DEVELOPMENT

        return cls(
            major=major,
            minor=minor,
            patch=patch,
            prerelease=prerelease,
            channel=channel,
        )

    def to_tuple(self) -> Tuple[int, int, int, int, int]:
        """Convert to comparable numeric tuple: (major, minor, patch, pre_weight, pre_num)."""
        # Stable releases have pre_weight = 100 (higher than any prerelease)
        if not self.prerelease:
            return (self.major, self.minor, self.patch, 100, 0)

        pre_lower = self.prerelease.lower()
        pre_num = 0
        if "." in pre_lower:
            parts = pre_lower.split(".", 1)
            pre_type = parts[0]
            try:
                pre_num = int(parts[1])
            except ValueError:
                pre_num = 0
        else:
            pre_type = pre_lower

        weight_map = {
            "dev": 1,
            "alpha": 10,
            "beta": 20,
            "rc": 30,
        }
        pre_weight = weight_map.get(pre_type, 5)
        return (self.major, self.minor, self.patch, pre_weight, pre_num)

    def __lt__(self, other: SemVer) -> bool:
        return self.to_tuple() < other.to_tuple()

    def __le__(self, other: SemVer) -> bool:
        return self.to_tuple() <= other.to_tuple()

    def __gt__(self, other: SemVer) -> bool:
        return self.to_tuple() > other.to_tuple()

    def __ge__(self, other: SemVer) -> bool:
        return self.to_tuple() >= other.to_tuple()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return False
        return self.to_tuple() == other.to_tuple()

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            return f"{base}-{self.prerelease}"
        return base


def get_git_revision(repo_path: Optional[Path] = None) -> Optional[str]:
    """Retrieves current Git short revision and dirty flag if available."""
    try:
        cwd = str(repo_path) if repo_path else None
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if res.returncode == 0 and res.stdout.strip():
            sha = res.stdout.strip()
            # Check dirty
            dirty_res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=3,
            )
            if dirty_res.returncode == 0 and dirty_res.stdout.strip():
                return f"{sha}-dirty"
            return sha
    except Exception:
        pass
    return None


@dataclass
class VersionInfo:
    """Comprehensive version payload for CLI and machine consumers."""
    version: str
    channel: str
    schema_version: str
    adapter_schema_version: str
    git_revision: Optional[str]
    python_version: str
    platform: str
    is_prerelease: bool
    compatibility: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def format_human(self) -> str:
        lines = [
            f"AntiOS Version:         {self.version} ({self.channel})",
            f"Schema Version:         {self.schema_version}",
            f"Adapter Schema:         {self.adapter_schema_version}",
            f"Git Revision:           {self.git_revision or 'unknown'}",
            f"Python Runtime:         {self.python_version}",
            f"Platform:               {self.platform}",
            f"Prerelease:             {'Yes' if self.is_prerelease else 'No'}",
            "Compatibility Matrix:",
            f"  - Antigravity:        {self.compatibility.get('antigravity', 'Universal')}",
            f"  - Python Required:    {self.compatibility.get('python', '>=3.8')}",
            f"  - Git Required:       {self.compatibility.get('git', '>=2.20')}",
        ]
        return "\n".join(lines)


def get_version_info(repo_path: Optional[Path] = None) -> VersionInfo:
    """Constructs current VersionInfo object."""
    semver = SemVer.parse(ANTIOS_VERSION)
    git_rev = get_git_revision(repo_path)
    return VersionInfo(
        version=ANTIOS_VERSION,
        channel=semver.channel.value,
        schema_version=CURRENT_SCHEMA_VERSION,
        adapter_schema_version=ADAPTER_SCHEMA_VERSION,
        git_revision=git_rev,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        platform=sys.platform,
        is_prerelease=semver.prerelease is not None,
        compatibility={
            "antigravity": "2.0 (Native platform primitives)",
            "python": ">=3.8",
            "git": ">=2.20 (native CLI recommended)",
            "github_cli": ">=2.0 (optional external capability)",
        },
    )


def compare_versions(current_str: str, target_str: str) -> Dict[str, Any]:
    """Compares two version strings, determining if target is upgrade, downgrade, or identical."""
    cur = SemVer.parse(current_str)
    tgt = SemVer.parse(target_str)

    is_upgrade = tgt > cur
    is_downgrade = tgt < cur
    is_same = tgt == cur
    is_major_change = tgt.major != cur.major

    return {
        "current_version": str(cur),
        "target_version": str(tgt),
        "is_upgrade": is_upgrade,
        "is_downgrade": is_downgrade,
        "is_same": is_same,
        "is_major_change": is_major_change,
        "is_prerelease": tgt.prerelease is not None,
        "channel": tgt.channel.value,
    }
