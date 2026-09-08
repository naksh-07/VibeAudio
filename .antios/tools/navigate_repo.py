"""AntiOS Deterministic Repository Wayfinding & Navigation Tool.

Resolves a task intent, natural language query, or file path to its owning
subsystem, entrypoints, covering test suites, invariants, and blast radius.

Usage:
    python framework/scripts/tools/navigate_repo.py --query "auth"
    python framework/scripts/tools/navigate_repo.py --file "src/auth/service.py"
    python framework/scripts/tools/navigate_repo.py --list
    python framework/scripts/tools/navigate_repo.py --query "auth" --json

Outputs locator card to stdout. Exits 0 on successful resolution.
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

from framework.core.config import load_config
from framework.core.discovery import discover_project
from framework.core.knowledge import (
    ProgressiveDisclosureLevel,
    ProgressiveDisclosureEngine,
)
from framework.core.subsystem import SubsystemDeclaration
from framework.core.wayfinding import WayfindingEngine, LocalityResolution


def build_engine(repo_root: str) -> WayfindingEngine:
    """Builds a WayfindingEngine populated from config or automated discovery."""
    engine = WayfindingEngine(workspace_root=repo_root)
    config = load_config(repo_root)

    # 1. Load components from config if present
    registered = False
    if hasattr(config, "components") and config.components:
        for sub_id, data in config.components.items():
            if isinstance(data, dict):
                data["subsystem_id"] = sub_id
                decl = SubsystemDeclaration.from_dict(data)
                engine.register_subsystem(decl)
                registered = True

    # 2. If no components in config, run discovery to populate
    if not registered:
        try:
            profile = discover_project(repo_root)
            if hasattr(profile, "subsystems") and profile.subsystems:
                for sub_id, data in profile.subsystems.items():
                    if isinstance(data, dict):
                        data["subsystem_id"] = sub_id
                        decl = SubsystemDeclaration.from_dict(data)
                        engine.register_subsystem(decl)
        except Exception:
            pass

    return engine


def main() -> None:
    parser = argparse.ArgumentParser(description="AntiOS Repository Wayfinding & Navigation")
    parser.add_argument("--task", "-t", help="Task description / intent to resolve engineering capabilities for")
    parser.add_argument("--query", "-q", help="Task query, intent, or keyword")
    parser.add_argument("--file", "-f", help="Target file path to locate subsystem for")
    parser.add_argument("--component", "-c", help="Component or subsystem ID to inspect")
    parser.add_argument("--subsystem", "-s", help="Subsystem ID to inspect (alias for --component)")
    parser.add_argument("--impact", "-i", nargs="+", help="File path(s) to analyze change intent and systemic blast radius")
    parser.add_argument("--capabilities", help="Target subsystem or file to inspect governing capabilities")
    parser.add_argument("--level", "-L", type=int, choices=[0, 1, 2, 3, 4, 5], default=None, help="Progressive context disclosure level (0 to 5)")
    parser.add_argument("--list", "-l", action="store_true", help="List all registered subsystems")
    parser.add_argument("--agent-routing", action="store_true", help="Resolve agent role, delegation decision, boundaries, and handoff for task")
    parser.add_argument("--tools", action="store_true", help="List registered execution tools or resolve tools for task")
    parser.add_argument("--providers", action="store_true", help="List registered execution providers")
    parser.add_argument("--tool-selection", action="store_true", help="Resolve tool & provider execution mechanism for task")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--repo-root", default=REPO_ROOT, help="Repository root directory")

    args = parser.parse_args()
    repo_root = os.path.normcase(os.path.abspath(args.repo_root))
    engine = build_engine(repo_root)

    # 1. Level 0: Project Identity (can run without specific query)
    if args.level == 0:
        config = load_config(repo_root)
        subsystems = engine.list_subsystems()
        proj_info = {
            "name": getattr(config, "name", os.path.basename(repo_root)),
            "archetype": "monorepo" if len(subsystems) > 3 else "standalone",
            "total_subsystems": len(subsystems),
            "primary_tech": "Python / Multi-Language",
        }
        if args.json:
            print(json.dumps(proj_info, indent=2))
        else:
            print(ProgressiveDisclosureEngine.render(ProgressiveDisclosureLevel.L0_PROJECT_IDENTITY, proj_info))
        sys.exit(0)

    # 2. List all subsystems
    if args.list:
        subsystems = engine.list_subsystems()
        if args.json:
            print(json.dumps([s.to_dict() for s in subsystems], indent=2))
        else:
            print(f"=== ANTIOS REGISTERED SUBSYSTEMS ({len(subsystems)}) ===")
            for s in subsystems:
                owner_info = f" [Owner: {s.owner} ({s.owner_source})]" if s.owner else ""
                print(f"- {s.subsystem_id} [{s.area}]: {s.name} ({s.description}){owner_info}")
                print(f"  Entrypoints: {', '.join(s.entrypoints)}")
                print(f"  Tests:       {', '.join(s.covering_tests)}")
            print("==============================================")
        sys.exit(0)

    # 2b. List all providers
    if args.providers:
        from framework.core.tool_registry import build_default_tool_registry
        config = load_config(repo_root)
        registry = build_default_tool_registry(workspace_root=repo_root, config=config)
        providers = registry.list_providers(enabled_only=False)
        if args.json:
            print(json.dumps([p.to_dict() for p in providers], indent=2))
        else:
            print(f"=== ANTIOS REGISTERED PROVIDERS ({len(providers)}) ===")
            for p in providers:
                status_str = f"[{p.policy_status.value}]"
                avail_str = f"({p.availability.value})"
                print(f"- {p.provider_id} [{p.provider_type.value}]: {p.name} {status_str} {avail_str}")
                print(f"  Capabilities: {', '.join(p.capabilities[:6])}")
            print("============================================")
        sys.exit(0)

    # 2c. List all tools (without task)
    if args.tools and not args.task:
        from framework.core.tool_registry import build_default_tool_registry
        config = load_config(repo_root)
        registry = build_default_tool_registry(workspace_root=repo_root, config=config)
        tools = registry.list_tools(enabled_only=False)
        if args.json:
            print(json.dumps([t.to_dict() for t in tools], indent=2))
        else:
            print(f"=== ANTIOS REGISTERED TOOLS ({len(tools)}) ===")
            for t in tools:
                status_str = f"[{t.policy_status.value}]"
                print(f"- {t.tool_id} [{t.tier.value}]: {t.name} {status_str}")
                print(f"  Provider: {t.provider_id} | Risk: {t.risk} | Latency: {t.latency_hint.value}")
            print("=======================================")
        sys.exit(0)

    # 3. Change Intent / Impact Analysis
    if args.impact and not args.task:
        intent = engine.analyze_change(args.impact)
        if args.json:
            print(json.dumps(intent.to_dict(), indent=2))
        else:
            print(engine.change_analyzer.format_change_intent_card(intent))
        sys.exit(0)

    # 4. Task Routing (Capabilities / Agent / Tools)
    if args.task:
        from framework.core.capability_router import CapabilityRouter
        from framework.core.tool_registry import build_default_tool_registry
        from framework.core.tool_policy import DeterministicToolSelector
        from framework.core.tool_pack import ToolRoutingPack
        from framework.core.tool import ToolTier
        import uuid

        target_files = args.impact or ([args.file] if args.file else [])
        config = load_config(repo_root)
        router = CapabilityRouter(wayfinding_engine=engine, workspace_root=repo_root)

        # 4a. Tool Selection
        if args.tool_selection or (args.tools and args.task):
            cap_pack = router.resolve_capabilities(args.task, target_files=target_files)
            agent_pack = router.resolve_agent_routing(args.task, target_files=target_files)
            tool_reg = build_default_tool_registry(workspace_root=repo_root, config=config)
            selector = DeterministicToolSelector(tool_reg)

            # Resolve primary capability
            task_lower = args.task.lower()
            cap_id = "general:execution"
            mcp_dec = getattr(cap_pack, "mcp_decision", {})
            mcp_prov = mcp_dec.get("provider_id", "") if isinstance(mcp_dec, dict) else ""
            pr_tokens = ["pull request", "create pr", "open pr", "merge pr", "github pr", "remote pr"]
            if any(t in task_lower for t in ["git status", "git diff", "git log", "working tree"]):
                cap_id = "git:status"
            elif any(t in task_lower for t in pr_tokens) or "github" in mcp_prov:
                cap_id = "github:create-pull-request"
            elif "chrome-devtools" in mcp_prov or any(t in task_lower for t in ["dom", "a11y", "browser layout"]):
                cap_id = "browser:dom-inspection"
            elif "playwright" in mcp_prov or any(t in task_lower for t in ["e2e", "browser automation"]):
                cap_id = "browser:e2e-automation"
            elif "gemini-api-docs" in mcp_prov or any(t in task_lower for t in ["gemini docs", "gemini api"]):
                cap_id = "docs:gemini-api-search"
            elif cap_pack.tools:
                first_tool = cap_pack.tools[0]
                cap_id = first_tool.get("capability_id") if isinstance(first_tool, dict) else str(first_tool)
            elif cap_pack.skills:
                first_skill = cap_pack.skills[0]
                cap_id = first_skill.get("capability_id") if isinstance(first_skill, dict) else str(first_skill)

            agent_role = None
            agent_role_id = "role:primary-engineer"
            from framework.core.agent_topology import build_default_agent_topology
            top_reg = build_default_agent_topology(config)
            if agent_pack.selected_specialist:
                spec_dict = agent_pack.selected_specialist
                spec_id = spec_dict.get("role_id") if isinstance(spec_dict, dict) else str(spec_dict)
                agent_role = top_reg.get(spec_id)
                agent_role_id = spec_id
            elif agent_pack.primary_role:
                prim_dict = agent_pack.primary_role
                prim_id = prim_dict.get("role_id") if isinstance(prim_dict, dict) else str(prim_dict)
                agent_role = top_reg.get(prim_id)
                agent_role_id = prim_id

            sub_id = cap_pack.matched_subsystems[0] if cap_pack.matched_subsystems else "*"
            sel_result = selector.select_tool(
                task_intent=args.task,
                capability_id=cap_id,
                task_class=cap_pack.task_class,
                subsystem_id=sub_id,
                agent_role=agent_role,
                target_files=target_files,
            )

            sel_tool = sel_result["selected_tool"]
            sel_prov = sel_result["selected_provider"]
            mcp_rep = sel_result["mcp_report"]

            tool_pack = ToolRoutingPack(
                pack_id=str(uuid.uuid4()),
                task_intent=args.task,
                task_class=cap_pack.task_class,
                matched_subsystems=cap_pack.matched_subsystems,
                capability_id=cap_id,
                agent_role_id=agent_role_id,
                selected_tool_id=sel_tool.tool_id if sel_tool else None,
                selected_tool_name=sel_tool.name if sel_tool else "None",
                selected_provider_id=sel_prov.provider_id if sel_prov else None,
                execution_tier=sel_tool.tier if sel_tool else ToolTier.SCRIPT,
                why_selected=sel_result["why_selected"],
                alternatives_considered=sel_result["alternatives_considered"],
                why_alternatives_rejected=sel_result["why_alternatives_rejected"],
                mcp_status=mcp_rep.status,
                mcp_justification=mcp_rep.why,
                availability=sel_result["availability"],
                offline_mode=sel_result["offline_mode"],
                authorization_status=sel_result["authorization_status"],
                authorization_reason=sel_result["authorization_reason"],
                evidence=sel_tool.evidence if sel_tool else "",
            )

            if args.json:
                full_result = {
                    "tool_routing": tool_pack.to_dict(),
                    "agent_routing": agent_pack.to_dict(),
                    "capability_pack": cap_pack.to_dict(),
                }
                print(json.dumps(full_result, indent=2))
            else:
                print(tool_pack.format_card())
            sys.exit(0)

        # 4b. Agent Routing
        if args.agent_routing:
            routing_pack = router.resolve_agent_routing(args.task, target_files=target_files)
            if args.json:
                print(routing_pack.to_json())
            else:
                print(routing_pack.format_card())
            sys.exit(0)

        # 4c. Capability Routing (default)
        pack = router.resolve_capabilities(args.task, target_files=target_files)
        if args.json:
            print(pack.to_json())
        elif args.level == 4:
            print(ProgressiveDisclosureEngine.render(ProgressiveDisclosureLevel.L4_CAPABILITIES, pack))
        else:
            print(pack.format_card())
        sys.exit(0)

    # 5. Capabilities Inspection
    if args.capabilities:
        caps = engine.get_capabilities(args.capabilities)
        if args.json:
            print(json.dumps(caps, indent=2))
        else:
            print("=== ANTIOS GOVERNING CAPABILITIES ===")
            print(f"Target:    {caps['target']} (Subsystem: {caps.get('subsystem_id', 'Unknown')})")
            print(f"Skills:    {', '.join(caps['skills'])}")
            print(f"Workflows: {', '.join(caps['workflows'])}")
            print(f"Rules:     {'; '.join(caps['rules']) if caps['rules'] else 'Standard project rules'}")
            print(f"Tests:     {', '.join(caps['covering_tests']) if caps['covering_tests'] else 'Default runner'}")
            print(f"Runners:   {'; '.join(caps['test_commands']) if caps['test_commands'] else 'tests/run_all.py'}")
            print("=====================================")
        sys.exit(0)

    # 5. Component / File / Query Resolution
    resolution: Optional[LocalityResolution] = None
    target_param = args.component or args.subsystem or args.file or args.query

    if args.component or args.subsystem:
        resolution = engine.resolve_component(args.component or args.subsystem)
    elif args.file:
        resolution = engine.resolve_file(args.file)
    elif args.query:
        resolution = engine.locate(args.query)
    else:
        parser.print_help()
        sys.exit(1)

    if not resolution:
        if args.json:
            print(json.dumps({"error": "No subsystem matched", "query": target_param}))
        else:
            print(f"AntiOS Wayfinding: No specific subsystem found for query '{target_param}'.")
            print("Fallback: Use root test runners and antios-engineer skill.")
        sys.exit(1)

    # Format output according to requested level
    if args.json:
        if args.level is not None:
            # Render specific level JSON
            level_enum = ProgressiveDisclosureLevel(args.level)
            if level_enum == ProgressiveDisclosureLevel.L5_DETAILED_EVIDENCE:
                decl = engine.get_subsystem(resolution.matched_subsystem_id)
                print(json.dumps(decl.to_dict() if decl else resolution.to_dict(), indent=2))
            else:
                print(json.dumps(resolution.to_dict(), indent=2))
        else:
            print(json.dumps(resolution.to_dict(), indent=2))
    else:
        if args.level is not None:
            level_enum = ProgressiveDisclosureLevel(args.level)
            decl = engine.get_subsystem(resolution.matched_subsystem_id)
            target_obj = decl if level_enum == ProgressiveDisclosureLevel.L5_DETAILED_EVIDENCE and decl else resolution
            print(ProgressiveDisclosureEngine.render(level_enum, target_obj, engine.knowledge_graph))
        else:
            print(engine.format_locator_card(resolution))

    sys.exit(0)


if __name__ == "__main__":
    main()
