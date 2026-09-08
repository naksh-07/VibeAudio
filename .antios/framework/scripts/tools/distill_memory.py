#!/usr/bin/env python3
"""AntiOS Memory Distillation CLI Tool.

Inspects, audits, and promotes cross-session candidate lessons in docs/LESSONS.md
based on deterministic recurrence thresholds, verified task evidence, and semantic conflict detection.
"""

from __future__ import annotations
import argparse
import json
import os
import sys
from typing import Any, Dict, List

# Ensure repository root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT_FALLBACK = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
if REPO_ROOT_FALLBACK not in sys.path:
    sys.path.insert(0, REPO_ROOT_FALLBACK)

from framework.core.memory import (
    LessonDistillationEngine,
    parse_lessons,
    sync_lessons,
    parse_historical_record,
)


def extract_task_evidence_from_history(repo_root: str) -> List[Dict[str, Any]]:
    """Extracts task execution evidence from docs/HISTORICAL_RECORD.md if present."""
    hist_path = os.path.join(repo_root, "docs", "HISTORICAL_RECORD.md")
    if not os.path.isfile(hist_path):
        return []

    records = parse_historical_record(hist_path)
    evidence: List[Dict[str, Any]] = []
    for r in records:
        evidence.append({
            "task_id": r.record_id,
            "failure_pattern": r.description,
            "verdict": "PASS" if "verified" in r.verification_summary.lower() or "pass" in r.verification_summary.lower() else "UNKNOWN",
            "resolution": r.verification_summary,
            "category": "Historical Milestone",
        })
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AntiOS Cross-Session Lesson Distillation CLI"
    )
    parser.add_argument(
        "repo_root",
        nargs="?",
        default=".",
        help="Path to repository root (default: current directory)"
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Audit candidate lessons and report promotion readiness without modifying disk"
    )
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Apply evidence-backed promotions and write updated docs/LESSONS.md"
    )
    parser.add_argument(
        "--min-recurrences",
        type=int,
        default=2,
        help="Minimum verified task recurrences required for promotion (default: 2)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON report"
    )

    args = parser.parse_args()
    repo_root = os.path.normcase(os.path.abspath(args.repo_root))
    lessons_path = os.path.join(repo_root, "docs", "LESSONS.md")

    if not os.path.isfile(lessons_path):
        if args.json:
            print(json.dumps({"error": f"docs/LESSONS.md not found in '{repo_root}'"}, indent=2))
        else:
            print(f"[-] AntiOS Distill: docs/LESSONS.md not found in '{repo_root}'.")
        return 1

    lessons = parse_lessons(lessons_path)
    task_evidence = extract_task_evidence_from_history(repo_root)

    # Standard distillation
    updated_lessons, result = LessonDistillationEngine.distill(
        lessons=lessons,
        task_evidence=task_evidence,
        min_recurrences=args.min_recurrences
    )

    # Phase 61-66 Project Learning Engine integration
    learning_proposals = []
    decay_report_data = {}
    try:
        from framework.core.learning import LearningEngine, CandidateLesson
        engine = LearningEngine(repo_root)
        cand_lessons = [CandidateLesson.from_lesson_record(l) for l in updated_lessons]
        cand_lessons, proposals, decay = engine.distill_and_promote(existing_lessons=cand_lessons)
        learning_proposals = [p.to_dict() for p in proposals]
        decay_report_data = decay.to_dict()
        # Merge any updated candidates back into updated_lessons
        updated_lessons = [c.to_lesson_record() for c in cand_lessons]
    except Exception:
        pass

    if args.promote and result.promoted_lessons:
        sync_lessons(updated_lessons, repo_root)

    if args.json:
        output_payload = {
            "repo_root": repo_root,
            "total_lessons": len(lessons),
            "promoted_count": len(result.promoted_lessons),
            "retained_count": len(result.retained_candidates),
            "conflicts_count": len(result.conflicts_detected),
            "distillation": result.to_dict(),
            "applied": bool(args.promote and result.promoted_lessons),
            "learning_proposals": learning_proposals,
            "decay_report": decay_report_data,
        }
        print(json.dumps(output_payload, indent=2))
        return 0

    print("=" * 65)
    print(" AntiOS Cross-Session Memory Distillation")
    print("=" * 65)
    print(f"Repository Root:    {repo_root}")
    print(f"Total Lessons:      {len(lessons)}")
    print(f"Candidates Retained:{len(result.retained_candidates)}")
    print(f"Promoted to Durable:{len(result.promoted_lessons)}")
    print(f"Conflicts Detected: {len(result.conflicts_detected)}")

    if result.conflicts_detected:
        print("\n[!] Conflicts Flagged for Human Review:")
        for c in result.conflicts_detected:
            print(f"    - {c}")

    if result.promoted_lessons:
        print("\n[+] Promoted Lessons:")
        for p in result.promoted_lessons:
            print(f"    - [{p.lesson_id}] {p.title} (Authority: {p.authority.value}, Recurrences: {p.recurrence_count})")
        if args.promote:
            print(f"\n[OK] docs/LESSONS.md updated on disk.")
        else:
            print(f"\n[*] Run with --promote to write updates to docs/LESSONS.md.")

    if result.rejected_promotions and not result.promoted_lessons:
        print("\n[-] Reasons Candidates Were Not Promoted:")
        for r in result.rejected_promotions[:5]:
            print(f"    - {r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
