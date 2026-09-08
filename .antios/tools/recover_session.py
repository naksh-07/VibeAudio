"""CLI Tool: AntiOS Session Recovery & Contradiction Resolution Inspector.

Usage:
    python framework/scripts/tools/recover_session.py <repo_root> [--json] [--apply]

Inspects recorded task state against Git working tree reality, detects contradictions,
evaluates verification staleness, and optionally applies deterministic recovery.
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

from framework.core.recovery import reconstruct_session_state, recover_session


def main() -> int:
    parser = argparse.ArgumentParser(description="AntiOS Session Recovery & Continuity Inspector")
    parser.add_argument("repo_root", nargs="?", default=".", help="Path to repository root")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")
    parser.add_argument("--apply", action="store_true", help="Apply recovery plan and synchronize docs/ACTIVE_CONTEXT.md")

    args = parser.parse_args()
    target_root = os.path.abspath(args.repo_root)

    if not os.path.isdir(target_root):
        print(f"Error: Target path '{target_root}' is not a valid directory.", file=sys.stderr)
        return 1

    plan, state = recover_session(target_root, apply_fix=args.apply)
    reconstructed = reconstruct_session_state(target_root)

    if args.json:
        payload = {
            "reconstructed": reconstructed,
            "applied": args.apply,
            "resulting_state": state.to_dict() if state and hasattr(state, "to_dict") else None,
        }
        print(json.dumps(payload, indent=2))
        return 0

    print("=" * 70)
    print(" AntiOS Session Recovery & Continuity Audit")
    print("=" * 70)
    print(f"Target Root:        {target_root}")
    print(f"Recorded Mission:   {state.mission_id if state else 'None'}")
    print(f"Recorded Stage:     {state.current_stage.value if state else 'None'}")
    print(f"Recorded Status:    {state.status.value if state else 'None'}")
    print(f"Dirty Files (Git):  {len(reconstructed['worktree_snapshot']['dirty_files'])}")
    for df in reconstructed['worktree_snapshot']['dirty_files'][:5]:
        print(f"  - {df}")

    print()
    print("-" * 70)
    print(f" Contradictions Detected: {len(reconstructed['contradictions'])}")
    print("-" * 70)
    if not reconstructed['contradictions']:
        print("  [OK] No contradictions detected between recorded state and Git reality.")
    else:
        for c in reconstructed['contradictions']:
            print(f"  ! [{c['severity']}] {c['type']}: {c['description']}")
            print(f"    Stale Claim: {c['stale_claim']}")
            print(f"    Git Reality: {c['physical_reality']}")

    if reconstructed['invalidation_reasons']:
        print()
        print("-" * 70)
        print(f" Verification Invalidation Reasons: {len(reconstructed['invalidation_reasons'])}")
        print("-" * 70)
        for r in reconstructed['invalidation_reasons']:
            print(f"  * {r}")

    print()
    print("=" * 70)
    print(f" Recovery Plan: {plan.action}")
    print("=" * 70)
    print(f"Recommended Stage:  {plan.recommended_stage.value}")
    print(f"Recommended Status: {plan.recommended_status.value}")
    print(f"Preserved Work:     {len(plan.preserved_work)} files safely preserved")
    print(f"Action Detail:      {plan.explanation}")

    if args.apply:
        print()
        print("[APPLIED] State synchronized to docs/ACTIVE_CONTEXT.md (<= 60 lines budget enforced).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
