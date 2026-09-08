#!/usr/bin/env python3
"""AntiOS 2.0 Generated Intelligence Verification CLI.

Audits target project intelligence artifacts against disk reality:
- Verifies SHA-256 cryptographic integrity
- Detects manifest fingerprint drift
- Identifies stale or deleted paths/components
- Verifies Shallow Depth Law (max_depth <= 2, can_delegate == False)
- Enforces Zero Legacy Workflows Invariant (no .agents/workflows/)

Exit codes:
  0: Intelligence VALID (or only advisory notices)
  1: DRIFT_DETECTED, STALE_INTELLIGENCE, or INTEGRITY_VIOLATION
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Add repo root to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from framework.core.intelligence_verifier import (
    IntelligenceVerificationStatus,
    IntelligenceVerifier,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify AntiOS Generated Intelligence integrity and drift.")
    parser.add_argument("repo_root", nargs="?", default=".", help="Target repository root path (default: current directory)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    target_path = Path(args.repo_root).resolve()
    verifier = IntelligenceVerifier(target_path)
    verdict = verifier.verify()

    if args.json:
        print(json.dumps(verdict.to_dict(), indent=2))
    else:
        print(f"=== ANTIOS INTELLIGENCE VERIFICATION ===")
        print(f"Target:      {verdict.project_root}")
        print(f"Status:      {verdict.status.value}")
        print(f"Drift:       {'DETECTED' if verdict.drift_detected else 'NONE'}")
        if verdict.fingerprint_current:
            print(f"Fingerprint: {verdict.fingerprint_current[:16]}... (Recorded: {verdict.fingerprint_recorded[:16]}...)")
        print(f"Issues:      {len(verdict.issues)}")
        for i, issue in enumerate(verdict.issues, 1):
            print(f"  {i}. [{issue.severity}] {issue.issue_type}: {issue.description} ({issue.path})")
            if issue.recommended_action:
                print(f"     Action: {issue.recommended_action}")
        if verdict.remediation_command:
            print(f"Remediation: {verdict.remediation_command}")
        print("========================================")

    if verdict.status in [
        IntelligenceVerificationStatus.INTEGRITY_VIOLATION,
        IntelligenceVerificationStatus.CORRUPTED,
    ]:
        return 1
    elif verdict.status in [
        IntelligenceVerificationStatus.DRIFT_DETECTED,
        IntelligenceVerificationStatus.STALE_INTELLIGENCE,
    ]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
