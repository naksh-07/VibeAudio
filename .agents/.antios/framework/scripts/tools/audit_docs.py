"""AntiOS Staleguard Layer 1 Syntactic Documentation Reference Audit Tool.

Audits documentation files and subsystem manifests for broken file references,
invalid links, and dead test commands against the physical workspace.

Usage:
    python framework/scripts/tools/audit_docs.py --path docs/
    python framework/scripts/tools/audit_docs.py --file README.md
    python framework/scripts/tools/audit_docs.py --all
    python framework/scripts/tools/audit_docs.py --all --json

Exits 0 if 100% clean, exits 1 if any broken reference is detected.
"""

from __future__ import annotations
import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normcase(os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..")))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from framework.core.docaudit import audit_documentation_references, audit_all_documentation


def main() -> None:
    parser = argparse.ArgumentParser(description="AntiOS Syntactic Documentation Reference Auditor")
    parser.add_argument("--file", "-f", help="Specific markdown file to audit")
    parser.add_argument("--path", "-p", help="Directory of markdown files to audit")
    parser.add_argument("--all", "-a", action="store_true", help="Audit all documentation across docs/ and .agents/")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--repo-root", default=REPO_ROOT, help="Repository root directory")

    args = parser.parse_args()
    repo_root = os.path.normcase(os.path.abspath(args.repo_root))

    results = {}
    if args.file:
        res = audit_documentation_references(args.file, repo_root)
        results[args.file] = res
    elif args.path:
        results = audit_all_documentation(repo_root, target_dirs=[args.path])
    elif args.all:
        results = audit_all_documentation(repo_root)
    else:
        results = audit_all_documentation(repo_root)

    total_files = len(results)
    clean_files = sum(1 for r in results.values() if r.is_clean)
    broken_files = total_files - clean_files
    total_broken_refs = sum(r.broken_count for r in results.values())

    if args.json:
        payload = {
            "total_files": total_files,
            "clean_files": clean_files,
            "broken_files": broken_files,
            "total_broken_references": total_broken_refs,
            "results": {p: r.to_dict() for p, r in results.items()},
        }
        print(json.dumps(payload, indent=2))
    else:
        print("=== ANTIOS SYNTACTIC DOCUMENTATION AUDIT ===")
        print(f"Scanned {total_files} files: {clean_files} clean, {broken_files} with broken references.")
        print(f"Total broken references detected: {total_broken_refs}")
        print("---------------------------------------------")

        for path, res in results.items():
            if not res.is_clean:
                print(f"[FAIL] {path} ({res.broken_count} broken):")
                for ref in res.references:
                    if not ref.is_valid:
                        print(f"  - Line {ref.line_number}: {ref.raw_text} -> {ref.error_message}")
            else:
                if not args.all:
                    print(f"[PASS] {path} ({res.valid_count} valid references)")

        print("=============================================")

    sys.exit(0 if total_broken_refs == 0 else 1)


if __name__ == "__main__":
    main()
