"""CLI Tool: AntiOS Project Intelligence & Universal Adapter Generator.

Usage:
    python framework/scripts/tools/adapt_project.py <repo_root> [--json] [--apply] [--dry-run]

Inspects an unfamiliar repository, constructs its canonical ProjectProfile,
evaluates adaptation needs against AntiOS Core, generates an AdaptationProposal,
and optionally applies safe project-local adapter configuration.
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

from framework.core.adapter import (
    analyze_adaptation,
    apply_project_adaptation,
    generate_adapter_config,
    verify_adapter,
)
from framework.core.config import load_config
from framework.core.discovery import discover_project


def main() -> int:
    parser = argparse.ArgumentParser(description="AntiOS Project Intelligence & Adapter Generator")
    parser.add_argument("repo_root", nargs="?", default=".", help="Path to repository root")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")
    parser.add_argument("--apply", action="store_true", help="Apply safe project-local adaptation to antios.config.json")
    parser.add_argument("--dry-run", action="store_true", help="Simulate applying adapter configuration without writing files")
    parser.add_argument("--verify", action="store_true", help="Verify adapter configuration against AntiOS Core invariants and manifest drift")

    args = parser.parse_args()
    target_root = os.path.abspath(args.repo_root)

    if not os.path.isdir(target_root):
        print(f"Error: Target path '{target_root}' is not a valid directory.", file=sys.stderr)
        return 1

    # Verification Mode
    if args.verify:
        verification = verify_adapter(target_root)
        if args.json:
            print(json.dumps(verification.to_dict(), indent=2))
            return 0 if verification.is_valid else 1
        print("=" * 70)
        print(" AntiOS Adapter Verification")
        print("=" * 70)
        print(f"Status:               {'VALID' if verification.is_valid else 'INVALID / DRIFT DETECTED'}")
        print(f"Manifest Fingerprint: {verification.manifest_fingerprint[:16]}..." if verification.manifest_fingerprint else "None")
        print(f"Passed Checks:        {len(verification.passed_checks)}")
        for p in verification.passed_checks:
            print(f"  [OK] {p}")
        if verification.issues:
            print(f"Issues / Violations:  {len(verification.issues)}")
            for issue in verification.issues:
                print(f"  [FAIL] {issue}")
        return 0 if verification.is_valid else 1

    # 1. Discover Project Intelligence
    profile = discover_project(target_root)
    current_config = load_config(target_root)

    # 2. Analyze Adaptation
    proposal = analyze_adaptation(profile, current_config)

    # 3. Apply if requested
    apply_result = None
    if args.apply or args.dry_run:
        success, msg = apply_project_adaptation(target_root, proposal, dry_run=args.dry_run)
        apply_result = {"success": success, "message": msg}

    if args.json:
        payload = {
            "profile": profile.to_dict(),
            "proposal": proposal.to_dict(),
            "apply_result": apply_result,
        }
        print(json.dumps(payload, indent=2))
        return 0 if (apply_result is None or apply_result.get("success", True)) else 1

    # Human-readable CLI summary
    print("=" * 70)
    print(f" AntiOS Project Intelligence Profile: {profile.identity.name}")
    print("=" * 70)
    print(f"Root:             {profile.identity.root_path}")
    print(f"Languages:        {', '.join(profile.identity.languages) or 'None detected'}")
    print(f"Frameworks:       {', '.join(profile.identity.frameworks) or 'None detected'}")
    print(f"Package Managers: {', '.join(profile.identity.package_managers) or 'None detected'}")
    print(f"Git Versioned:    {profile.identity.is_git_repo}")
    print()

    print(f"Observed Facts:   {len(profile.observed_facts)}")
    print(f"Inferred Facts:   {len(profile.inferred_facts)}")
    print(f"Discovered Tools: {len(profile.tools)}")
    for t in profile.tools:
        in_path = "[IN PATH]" if t.is_available_in_path else "[MISSING IN PATH]"
        print(f"  - [{t.category.value}] {t.name}: {' '.join(t.command)} {in_path}")

    if profile.conflicts:
        print()
        print(f"Conflicts Detected: {len(profile.conflicts)}")
        for c in profile.conflicts:
            print(f"  ! [{c.conflict_type.value}] {c.description}")
            print(f"    Winner: {c.winning_source} -> {c.resolution_recommendation}")

    if profile.unknown_fields:
        print()
        print(f"Unknowns / Gaps: {len(profile.unknown_fields)}")
        for u in profile.unknown_fields:
            blk = "[BLOCKING]" if u.is_blocking else "[INFO]"
            print(f"  ? {blk} {u.field_name}: {u.reason}")

    print()
    print("-" * 70)
    print(f" Adaptation Proposal: {len(proposal.items)} action items")
    print("-" * 70)
    for idx, item in enumerate(proposal.items, 1):
        print(f"{idx}. [{item.action.value}] ({item.target.value}) {item.component}")
        print(f"   {item.description}")
        print(f"   Reason: {item.reason}")
        print(f"   Risk: {item.risk.value} | Auto-Safe: {item.is_automated_safe}")

    if apply_result:
        print()
        print("=" * 70)
        status = "SUCCESS" if apply_result["success"] else "FAILED"
        print(f" Adaptation Apply Result: {status}")
        print("=" * 70)
        print(apply_result["message"])

    return 0


if __name__ == "__main__":
    sys.exit(main())
