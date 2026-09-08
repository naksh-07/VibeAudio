"""CLI Tool: AntiOS 2.0 Project Agent OS Installer & Lifecycle Manager.

Usage:
    python framework/scripts/tools/install_project.py <target_root> [OPTIONS]

Options:
    --install       Install AntiOS Project Agent OS into target repository (default)
    --adapt         Re-discover target project and synchronize intelligence
    --update        Update AntiOS instance to newer source revision
    --repair        Repair missing or damaged instance artifacts
    --remove        Safely remove AntiOS instance while preserving user code
    --verify        Verify installation health, manifest validity, and checksums
    --json          Output raw JSON report
    --dry-run       Simulate operations without writing or deleting files
    --force         Force installation even if conflicts exist
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Ensure repository root is on sys.path
REPO_ROOT = os.path.normcase(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from framework.core.installation import InstallationLifecycleManager


def main() -> int:
    parser = argparse.ArgumentParser(description="AntiOS 2.0 Project Agent OS Installer & Lifecycle Manager")
    parser.add_argument("target_root", nargs="?", default=".", help="Path to target repository root")
    parser.add_argument("--install", action="store_true", help="Install AntiOS Project Agent OS into target repository")
    parser.add_argument("--adapt", action="store_true", help="Re-discover and synchronize project intelligence")
    parser.add_argument("--update", action="store_true", help="Update AntiOS instance to newer source revision")
    parser.add_argument("--repair", action="store_true", help="Repair damaged or missing instance artifacts")
    parser.add_argument("--remove", action="store_true", help="Safely remove AntiOS instance")
    parser.add_argument("--verify", action="store_true", help="Verify installation health and manifest integrity")
    parser.add_argument("--revision", default="v2.0.0", help="AntiOS source revision tag")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without mutating filesystem")
    parser.add_argument("--force", action="store_true", help="Force operation despite non-blocking warnings")

    args = parser.parse_args()
    target_root = os.path.abspath(args.target_root)

    if not os.path.isdir(target_root):
        print(f"Error: Target path '{target_root}' is not a valid directory.", file=sys.stderr)
        return 1

    manager = InstallationLifecycleManager(
        source_root=REPO_ROOT,
        target_root=target_root,
        source_revision=args.revision,
    )

    # Determine operation (default is --install if no action flag specified)
    if args.verify:
        result = manager.verify()
    elif args.adapt:
        result = manager.adapt(dry_run=args.dry_run)
    elif args.update:
        result = manager.update(new_revision=args.revision, dry_run=args.dry_run)
    elif args.repair:
        result = manager.repair(dry_run=args.dry_run)
    elif args.remove:
        result = manager.remove(dry_run=args.dry_run)
    else:
        # Default: install
        result = manager.install(dry_run=args.dry_run, force=args.force)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return 0 if result.status in ("SUCCESS", "IDEMPOTENT") else 1

    # Human-readable output
    print("=" * 70)
    print(f" AntiOS 2.0 Project Agent OS ? {result.operation}")
    print("=" * 70)
    print(f"Target Repository:    {target_root}")
    print(f"Operation:            {result.operation}")
    print(f"Status:               {result.status}")
    print(f"Installation State:   {result.installation_state.value}")
    print(f"Adaptation State:     {result.adaptation_state.value}")
    print(f"Summary:              {result.summary}")

    if result.written_files:
        print(f"\nFiles Written ({len(result.written_files)}):")
        for f in result.written_files:
            print(f"  [+] {f}")

    if result.removed_files:
        print(f"\nFiles Removed ({len(result.removed_files)}):")
        for f in result.removed_files:
            print(f"  [-] {f}")

    if result.conflicts:
        print(f"\nConflicts ({len(result.conflicts)}):")
        for c in result.conflicts:
            print(f"  [!] {c}")

    if result.issues:
        print(f"\nIssues / Blockers ({len(result.issues)}):")
        for issue in result.issues:
            print(f"  [x] {issue}")

    return 0 if result.status in ("SUCCESS", "IDEMPOTENT") else 1


if __name__ == "__main__":
    sys.exit(main())
