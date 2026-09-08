#!/usr/bin/env python3
"""AntiOS 2.0 Instance Migration & Evolution Certification CLI.

Inspects target project AntiOS instances, evaluates compatibility with
current framework releases, plans migrations, and certifies upgrade safety.

Usage:
  python framework/scripts/tools/migrate_instance.py [repo_root] --check
  python framework/scripts/tools/migrate_instance.py [repo_root] --plan
  python framework/scripts/tools/migrate_instance.py [repo_root] --apply [--dry-run]
  python framework/scripts/tools/migrate_instance.py [repo_root] --certify

Exit codes:
  0: Compatible, certified, or migration successful
  1: Incompatible, corrupted, or migration failed
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

# Ensure repository root is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from framework.core.manifest import CURRENT_ANTIOS_VERSION, CURRENT_SCHEMA_VERSION
from framework.core.migration import CompatibilityState, MigrationEngine


def main() -> int:
    parser = argparse.ArgumentParser(description="AntiOS Instance Migration & Certification CLI")
    parser.add_argument("repo_root", nargs="?", default=".", help="Path to target project repository root")
    parser.add_argument("--check", action="store_true", help="Check compatibility state against current AntiOS version")
    parser.add_argument("--plan", action="store_true", help="Generate dry-run migration plan")
    parser.add_argument("--apply", action="store_true", help="Execute migration plan")
    parser.add_argument("--dry-run", action="store_true", help="Simulate migration without modifying files")
    parser.add_argument("--certify", action="store_true", help="Run full compatibility and provenance certification")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    target_root = Path(args.repo_root).resolve()

    if not target_root.exists():
        print(f"Error: Target path '{target_root}' does not exist.", file=sys.stderr)
        return 1

    # 1. Compatibility Check
    if args.check or (not args.plan and not args.apply and not args.certify):
        state, rationale, manifest = MigrationEngine.assess_compatibility(target_root)
        if args.json:
            print(json.dumps({
                "target_root": str(target_root),
                "compatibility_state": state.value,
                "rationale": rationale,
                "instance_version": manifest.antios_version if manifest else None,
                "current_antios_version": CURRENT_ANTIOS_VERSION,
                "current_schema_version": CURRENT_SCHEMA_VERSION,
            }, indent=2))
        else:
            print("=== ANTIOS INSTANCE COMPATIBILITY CHECK ===")
            print(f"Target:      {target_root}")
            print(f"State:       {state.value}")
            print(f"Rationale:   {rationale}")
            if manifest:
                print(f"Instance:    v{manifest.antios_version} (schema {manifest.schema_version})")
            print(f"Framework:   v{CURRENT_ANTIOS_VERSION} (schema {CURRENT_SCHEMA_VERSION})")
            print("==========================================")
        return 0 if state in (CompatibilityState.COMPATIBLE, CompatibilityState.UPGRADE_AVAILABLE) else 1

    # 2. Migration Plan
    if args.plan:
        plan = MigrationEngine.plan_migration(target_root)
        if args.json:
            print(json.dumps(plan.to_dict(), indent=2))
        else:
            print("=== ANTIOS MIGRATION PLAN ===")
            print(f"Plan ID:      {plan.plan_id}")
            print(f"Target:       {plan.target_root}")
            print(f"Status:       {plan.compatibility_state.value}")
            print(f"Executable:   {plan.is_executable}")
            print(f"Steps ({len(plan.steps)}):")
            for i, step in enumerate(plan.steps, 1):
                print(f"  {i}. [{step.action}] {step.target_path} ({step.description})")
            if plan.conflicts:
                print(f"Conflicts ({len(plan.conflicts)}):")
                for c in plan.conflicts:
                    print(f"  - [CONFLICT] {c}")
            print(f"User Preserved ({len(plan.user_owned_preserved)}):")
            for u in plan.user_owned_preserved:
                print(f"  - [USER_OWNED] {u}")
            print("=============================")
        return 0 if plan.is_executable else 1

    # 3. Apply Migration
    if args.apply:
        plan = MigrationEngine.plan_migration(target_root)
        if not plan.is_executable:
            print(f"Refusing migration: plan is not executable ({len(plan.conflicts)} conflicts).", file=sys.stderr)
            return 1
        result = MigrationEngine.execute_migration(plan, dry_run=args.dry_run)
        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print("=== ANTIOS MIGRATION EXECUTION ===")
            print(f"Plan ID:     {result.plan_id}")
            print(f"Success:     {result.is_successful}")
            print(f"Initial:     {result.initial_state.value}")
            print(f"Final:       {result.final_state.value}")
            print(f"Steps:       {len(result.executed_steps)} executed")
            if result.errors:
                print(f"Errors:      {result.errors}")
            print(f"Summary:     {result.summary}")
            print("==================================")
        return 0 if result.is_successful else 1

    # 4. Certify
    if args.certify:
        state, rationale, manifest = MigrationEngine.assess_compatibility(target_root)
        is_clean = state == CompatibilityState.COMPATIBLE
        if args.json:
            print(json.dumps({
                "target_root": str(target_root),
                "certified": is_clean,
                "compatibility_state": state.value,
                "rationale": rationale,
            }, indent=2))
        else:
            print("=== ANTIOS EVOLUTION CERTIFICATION ===")
            print(f"Target:     {target_root}")
            print(f"Certified:  {'YES' if is_clean else 'NO'}")
            print(f"State:      {state.value}")
            print(f"Rationale:  {rationale}")
            print("======================================")
        return 0 if is_clean else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
