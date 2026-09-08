"""AntiOS 2.0 Agent-Native Repository Certification CLI Tool.

Phase 78: Formally evaluates and certifies repository agent-native quality against
observable filesystem evidence, manifest verification, and friction detection.

Usage:
    python framework/scripts/tools/certify_agent_native.py [path]
    python framework/scripts/tools/certify_agent_native.py [path] --json
    python framework/scripts/tools/certify_agent_native.py [path] --strict

Exit Code:
    0: Certified pass (meets required certification threshold)
    1: NOT_READY or failed strict certification criteria
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normcase(os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..")))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from framework.core.agent_native_certification import (
    AgentNativeCertificationEngine,
    CertificationLevel,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="AntiOS 2.0 Agent-Native Repository Certification Tool")
    parser.add_argument("target", nargs="?", default=".", help="Target repository root path (default: .)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--strict", action="store_true", help="Fail if not AGENT_READY or higher")

    args = parser.parse_args()
    target_root = os.path.normcase(os.path.abspath(args.target))

    try:
        cert = AgentNativeCertificationEngine.certify(target_root)
    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e), "is_certified": False}, indent=2))
        else:
            print(f"ERROR: Certification failed to execute: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(cert.to_dict(), indent=2))
    else:
        print(cert.to_formal_report())

    # Exit code determination
    if cert.certification_level == CertificationLevel.NOT_READY:
        return 1

    if args.strict and not cert.is_certified:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
