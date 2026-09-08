"""AntiOS 2.0 Project Instance Runtime: Instance Inspector & Wayfinding Helper.

Phase 80/82: Instance-Local Architecture Inspector & Wayfinder.
Self-contained, zero-external-dependency standard-library script.
Does NOT import or depend on the AntiOS source repository.

Provides wayfinding, subsystem resolution, and test runner inspection
for the /antios control plane inside target projects.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Set


def load_json_safe(path: Path) -> Dict[str, Any]:
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def match_subsystem(query: str, subsystems: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Simple deterministic keyword overlap matching for wayfinding."""
    if not query or not subsystems:
        return None

    words = set(query.lower().replace("-", " ").replace("_", " ").replace("/", " ").split())
    best_match = None
    best_score = 0

    for sub in subsystems:
        sub_id = str(sub.get("subsystem_id") or sub.get("name") or "").lower()
        sub_paths = [str(p).lower() for p in sub.get("paths", [])]
        sub_desc = str(sub.get("description", "")).lower()

        score = 0
        for w in words:
            if len(w) < 2:
                continue
            if w in sub_id:
                score += 3
            for p in sub_paths:
                if w in p:
                    score += 2
            if w in sub_desc:
                score += 1

        if score > best_score:
            best_score = score
            best_match = sub

    return best_match if best_score > 0 else (subsystems[0] if len(subsystems) == 1 else None)


def main() -> int:
    parser = argparse.ArgumentParser(description="AntiOS Project Instance Inspector & Wayfinder")
    parser.add_argument("--query", "-q", default=None, help="Query intent to resolve responsible subsystem")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--summary", action="store_true", help="Output JSON summary of instance")
    args = parser.parse_args()

    repo_root = Path(".").resolve()
    antios_dir = repo_root / ".antios"

    manifest_data = load_json_safe(antios_dir / "manifest.json")
    anatomy_data = load_json_safe(antios_dir / "project_anatomy.json")
    knowledge_data = load_json_safe(antios_dir / "knowledge.json")
    topology_data = load_json_safe(antios_dir / "agent_topology.json")
    config_data = load_json_safe(repo_root / "antios.config.json")

    project_name = config_data.get("project_name") or anatomy_data.get("project_name") or config_data.get("name") or repo_root.name
    archetype = anatomy_data.get("archetype", "UNKNOWN")
    source_roots = anatomy_data.get("source_roots", ["."])
    test_roots = anatomy_data.get("test_roots", ["tests"])
    test_runners = config_data.get("test_runners", []) or anatomy_data.get("test_runners", [])
    protected_zones = config_data.get("protected_zones", [".agents", ".antios", "antios.config.json", ".git"])
    protected_domain = config_data.get("protected_domain_paths", [])

    subsystems = knowledge_data.get("subsystems", []) or anatomy_data.get("subsystems", [])

    matched = None
    if args.query:
        matched = match_subsystem(args.query, subsystems)

    report: Dict[str, Any] = {
        "project_name": project_name,
        "archetype": archetype,
        "source_roots": source_roots,
        "test_roots": test_roots,
        "test_runners": test_runners,
        "protected_zones": protected_zones,
        "protected_domain_paths": protected_domain,
        "total_subsystems": len(subsystems),
        "query": args.query,
        "matched_subsystem": matched,
    }

    if args.json or args.summary:
        print(json.dumps(report, indent=2))
        return 0

    print("=" * 65)
    print(f" AntiOS Project Instance: {project_name} ({archetype})")
    print("=" * 65)
    print(f"Source Roots:    {', '.join(source_roots)}")
    print(f"Test Roots:      {', '.join(test_roots)}")
    print(f"Protected Zones: {', '.join(protected_zones)}")
    if protected_domain:
        print(f"Domain Cores:    {', '.join(protected_domain)}")

    if test_runners:
        print("\nConfigured Test Runners:")
        for tr in test_runners:
            name = tr.get("name", "runner")
            cmd = " ".join(tr.get("default_command") or tr.get("command") or [])
            print(f"  - {name}: `{cmd}`")

    if args.query:
        print(f"\nWayfinding Query: '{args.query}'")
        if matched:
            sid = matched.get("subsystem_id") or matched.get("name")
            paths = ", ".join(matched.get("paths", []))
            tests = ", ".join(matched.get("covering_tests", []))
            print(f"  -> Responsible Subsystem: {sid}")
            print(f"     Paths:          {paths}")
            print(f"     Covering Tests: {tests}")
        else:
            print("  -> No specific subsystem matched. Inspect root project structure.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
