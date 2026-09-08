"""AntiOS Task-to-Capability Router.

Central engine for Phase 31–33 Project Capability Layer.
Answers the foundational question:
> "Given this project, this subsystem, this component, and this task,
> what engineering capabilities should the agent use?"

Resolution Pipeline:
TASK -> TASK CLASS -> SUBSYSTEM -> COMPONENT -> WORKFLOW -> SKILLS -> RULES -> TOOLS -> VERIFIER -> SPECIALIST -> MCP
"""

from __future__ import annotations
from dataclasses import dataclass, field
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from framework.core.capability import (
    Capability,
    CapabilityScope,
    CapabilityType,
    MCPDecision,
    MCPStatus,
    RuleConflictStatus,
    RulePrecedence,
    VerifierType,
)
from framework.core.capability_pack import CapabilityPack
from framework.core.capability_registry import CapabilityRegistry, build_default_registry
from framework.core.lifecycle import RiskTier, TaskClass
from framework.core.subsystem import SubsystemDeclaration
from framework.core.wayfinding import LocalityResolution, WayfindingEngine
from framework.core.workflow import WorkflowSpec, get_workflow
from framework.core.agent_routing_pack import AgentRoutingPack
from framework.core.agent_router import AgentRouter


@dataclass
class TaskIntent:
    """Parsed and classified intent from user prompt or target files."""
    raw_intent: str
    task_class: TaskClass
    confidence: float
    target_files: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    is_ambiguous: bool = False
    is_unknown: bool = False


class CapabilityRouter:
    """Deterministic resolver mapping task intent and project knowledge to capabilities."""

    def __init__(
        self,
        registry: Optional[CapabilityRegistry] = None,
        wayfinding_engine: Optional[WayfindingEngine] = None,
        project_name: str = "AntiOS",
        workspace_root: Optional[str] = None,
        config_dict: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.workspace_root = workspace_root
        self.project_name = project_name
        self.config_dict = config_dict or {}
        self.registry = registry or build_default_registry(workspace_root, self.config_dict)
        self.wayfinder = wayfinding_engine
        self.agent_router = AgentRouter(project_name=self.project_name)

    def resolve_agent_routing(
        self,
        task_intent: str,
        target_files: Optional[List[str]] = None,
        task_class_hint: Optional[Union[TaskClass, str]] = None,
    ) -> AgentRoutingPack:
        """Resolves capability pack and determines optimal agent role and delegation policy."""
        pack = self.resolve_capabilities(task_intent, target_files, task_class_hint)
        return self.agent_router.route_task(pack, target_files=target_files)

    def classify_task_intent(
        self,
        intent_str: str,
        target_files: Optional[List[str]] = None,
        task_class_hint: Optional[Union[TaskClass, str]] = None,
    ) -> TaskIntent:
        """Deterministically classifies a task description into a canonical TaskClass."""
        files = target_files or []
        clean_intent = (intent_str or "").strip()

        # Handle explicit hint
        if task_class_hint:
            t_class = task_class_hint if isinstance(task_class_hint, TaskClass) else TaskClass(str(task_class_hint).upper())
            return TaskIntent(
                raw_intent=clean_intent,
                task_class=t_class,
                confidence=1.0,
                target_files=files,
            )

        # Empty or gibberish check
        if not clean_intent and not files:
            return TaskIntent(
                raw_intent=clean_intent,
                task_class=TaskClass.FEATURE,
                confidence=0.0,
                is_unknown=True,
            )

        # Check for non-word gibberish (e.g. 'asdfghjk', '!@#$%^')
        words = re.findall(r"\b[a-zA-Z]{2,}\b", clean_intent.lower())
        if not words and not files:
            return TaskIntent(
                raw_intent=clean_intent,
                task_class=TaskClass.FEATURE,
                confidence=0.0,
                is_unknown=True,
            )

        # File-based hints
        has_doc_files = any(f.endswith((".md", ".rst", ".txt", ".adoc")) or "docs/" in f.replace("\\", "/") for f in files)
        has_test_files = any("test" in f.lower() for f in files)

        lower_intent = clean_intent.lower()
        extracted_keywords: List[str] = []

        # Keyword mapping rules
        bug_words = ["bug", "fix", "crash", "error", "broken", "failing", "fail", "defect", "exception", "reproduce", "timeout", "regression"]
        refactor_words = ["refactor", "clean", "restructure", "modernize", "simplify", "reorganize", "decouple", "extract", "inline"]
        doc_words = ["doc", "docs", "documentation", "spec", "readme", "guide", "comment", "audit_docs", "specification", "manual"]
        investigate_words = ["investigate", "research", "explore", "spike", "audit", "analyze", "survey", "benchmark", "why", "where", "how does", "what governs"]
        release_words = ["release", "version", "bump", "tag", "publish", "deploy", "changelog", "maintenance", "upgrade package"]

        bug_score = sum(1 for w in bug_words if w in lower_intent)
        refactor_score = sum(1 for w in refactor_words if w in lower_intent)
        doc_score = sum(1 for w in doc_words if w in lower_intent) + (2 if has_doc_files and len(files) == 1 else 0)
        investigate_score = sum(1 for w in investigate_words if w in lower_intent)
        release_score = sum(1 for w in release_words if w in lower_intent)

        scores = {
            TaskClass.BUG: bug_score,
            TaskClass.REFACTOR: refactor_score,
            TaskClass.DOCUMENTATION: doc_score,
            TaskClass.INVESTIGATION: investigate_score,
            TaskClass.RELEASE: release_score,
        }

        best_class = max(scores, key=scores.get) # type: ignore
        best_score = scores[best_class]

        if best_score > 0:
            confidence = min(0.95, 0.7 + (best_score * 0.1))
            return TaskIntent(
                raw_intent=clean_intent,
                task_class=best_class,
                confidence=confidence,
                target_files=files,
                keywords=words,
            )

        # Default fallback to FEATURE
        confidence = 0.8 if ("add" in lower_intent or "create" in lower_intent or "implement" in lower_intent or "change" in lower_intent or "new" in lower_intent) else 0.5
        return TaskIntent(
            raw_intent=clean_intent,
            task_class=TaskClass.FEATURE,
            confidence=confidence,
            target_files=files,
            keywords=words,
            is_ambiguous=(confidence < 0.6),
        )

    def evaluate_mcp_justification(
        self,
        task_intent: str,
        matched_subsystems: List[str],
        has_native: bool = True,
        has_script: bool = True,
    ) -> MCPDecision:
        """Evaluates whether an external MCP provider is justified under ANTIOS_MCP_POLICY.md."""
        lower = task_intent.lower()

        # Rule 1: Check for explicitly rejected MCP candidates
        for rej in ["notion", "postman", "posthog", "unauthorized-external-mcp"]:
            if rej in lower:
                return MCPDecision(
                    provider_id=f"mcp:{rej}",
                    status=MCPStatus.REJECTED,
                    justification=f"'{rej}' is permanently REJECTED under AntiOS MCP governance (ANTIOS_MCP_POLICY.md).",
                    suggested_alternative="Native CLI or local markdown files",
                    is_permitted=False,
                )

        # Rule 2: Browser DOM / UI inspection / Accessibility
        is_ui_inspection = any(w in lower for w in ["browser dom", "dom inspection", "accessibility tree", "a11y", "visual snapshot", "browser layout"])
        is_ui_sub = any(s in ["ui", "frontend", "web", "client"] for s in matched_subsystems)
        if is_ui_inspection or (is_ui_sub and "inspect" in lower):
            return MCPDecision(
                provider_id="mcp:chrome-devtools",
                status=MCPStatus.USEFUL,
                justification="Browser DOM/a11y inspection requires active Chrome DevTools protocol; permitted under ANTIOS_MCP_POLICY.md.",
                is_permitted=True,
            )

        # Rule 3: Browser end-to-end automation
        is_e2e = any(w in lower for w in ["playwright", "e2e test", "browser click", "headless browser", "ui automation"])
        if is_e2e:
            return MCPDecision(
                provider_id="mcp:playwright",
                status=MCPStatus.USEFUL,
                justification="Headless browser flow automation justified under ANTIOS_MCP_POLICY.md.",
                is_permitted=True,
            )

        # Rule 4: Upstream Gemini SDK documentation search
        is_gemini_lookup = any(w in lower for w in ["gemini sdk", "gemini api", "model docs", "upstream gemini"])
        if is_gemini_lookup:
            return MCPDecision(
                provider_id="mcp:gemini-api-docs",
                status=MCPStatus.USEFUL,
                justification="Upstream Gemini SDK doc search justified under ANTIOS_MCP_POLICY.md.",
                is_permitted=True,
            )

        # Rule 5: Remote GitHub PR operations (Strict boundary: local git MUST use CLI)
        is_remote_pr = any(w in lower for w in ["create pr", "open pull request", "remote pr", "github issue"])
        if is_remote_pr:
            return MCPDecision(
                provider_id="mcp:github",
                status=MCPStatus.OPTIONAL,
                justification="Remote GitHub PR creation permitted; local working tree operations must use native CLI.",
                is_permitted=True,
            )

        # Default: Local Native / Script / Project tool suffices
        return MCPDecision(
            provider_id="none",
            status=MCPStatus.NOT_NEEDED,
            justification="Task is fully addressed by Antigravity native tools and local CLI scripts. No external MCP required.",
            is_permitted=False,
        )

    def resolve_capabilities(
        self,
        task_intent: str,
        target_files: Optional[List[str]] = None,
        task_class_hint: Optional[Union[TaskClass, str]] = None,
    ) -> CapabilityPack:
        """Resolves the complete, bounded CapabilityPack for a task."""
        files = target_files or []
        intent = self.classify_task_intent(task_intent, files, task_class_hint)

        matched_subsystems: List[str] = []
        matched_components: List[str] = []
        covering_tests: List[str] = []
        test_commands: List[str] = []
        sub_governing_rules: List[str] = []
        sub_skills: List[str] = []
        risk_tier = "LOW"
        epistemic_state = "OBSERVED"
        why_selected: Dict[str, str] = {}
        unknowns: List[Dict[str, Any]] = []

        # ---------------------------------------------------------------------
        # 1. Wayfinding & Subsystem Locality
        # ---------------------------------------------------------------------
        loc_res: Optional[LocalityResolution] = None
        if self.wayfinder:
            if files:
                for f in files:
                    res = self.wayfinder.resolve_file(f)
                    if res:
                        matched_subsystems.append(res.matched_subsystem_id)
                        matched_components.append(res.name)
                        covering_tests.extend(res.covering_tests)
                        test_commands.extend(res.test_commands)
                        sub_governing_rules.extend(res.governing_rules)
                        sub_skills.extend(res.applicable_skills)
                        risk_tier = res.risk_tier
            elif task_intent:
                # Query wayfinder with intent text
                loc_res = self.wayfinder.locate(task_intent)
                if loc_res and loc_res.matched_subsystem_id != "UNKNOWN":
                    matched_subsystems.append(loc_res.matched_subsystem_id)
                    matched_components.append(loc_res.name)
                    covering_tests.extend(loc_res.covering_tests)
                    test_commands.extend(loc_res.test_commands)
                    sub_governing_rules.extend(loc_res.governing_rules)
                    sub_skills.extend(loc_res.applicable_skills)
                    risk_tier = loc_res.risk_tier

        # Deduplicate matched subsystems & components
        matched_subsystems = sorted(list(set(matched_subsystems)))
        matched_components = sorted(list(set(matched_components)))

        # Fallback if unknown
        if not matched_subsystems:
            # Check if intent keywords hint at a domain
            intent_lower = task_intent.lower()
            if any(w in intent_lower for w in ["button", "login", "ui", "modal", "page", "css", "html", "style"]):
                matched_subsystems = ["ui"]
                matched_components = ["ui-components"]
                why_selected["subsystem"] = "Inferred UI domain from intent keywords"
                epistemic_state = "INFERRED"
            elif any(w in intent_lower for w in ["schema", "database", "migration", "table", "sqlite", "sql", "column"]):
                matched_subsystems = ["database"]
                matched_components = ["database-migrations"]
                why_selected["subsystem"] = "Inferred database domain from intent keywords"
                epistemic_state = "INFERRED"
            elif any(w in intent_lower for w in ["api", "endpoint", "route", "http", "controller"]):
                matched_subsystems = ["api"]
                matched_components = ["api-endpoints"]
                why_selected["subsystem"] = "Inferred API domain from intent keywords"
                epistemic_state = "INFERRED"
            else:
                matched_subsystems = ["UNKNOWN"]
                unknowns.append({
                    "field": "subsystem",
                    "reason": f"No subsystem mapped to '{task_intent}' or specified files.",
                    "required_action": "Inspect directory structure or run adapt_project.py to discover subsystems."
                })
                epistemic_state = "UNKNOWN"

        # Check intent unknown
        if intent.is_unknown:
            unknowns.append({
                "field": "task_class",
                "reason": "Task intent was empty or unintelligible gibberish.",
                "required_action": "Clarify task requirements."
            })
            epistemic_state = "UNKNOWN"

        # ---------------------------------------------------------------------
        # 2. Workflow Routing
        # ---------------------------------------------------------------------
        wf_spec = get_workflow(intent.task_class)
        wf_id = f"workflow:{intent.task_class.value.lower()}"
        why_selected["workflow"] = f"Governs task class '{intent.task_class.value}'"

        # Escalate risk if critical subsystems or files
        if any(s in ["core", "core-governance", "database"] for s in matched_subsystems) or "schema" in task_intent.lower():
            if risk_tier in ("LOW", "MEDIUM"):
                risk_tier = "HIGH"
        if intent.task_class in (TaskClass.RELEASE, TaskClass.REFACTOR):
            if risk_tier != "CRITICAL":
                risk_tier = "HIGH"

        # ---------------------------------------------------------------------
        # 3. Skill Routing & Negative Applicability Filtering
        # ---------------------------------------------------------------------
        selected_skills: List[Capability] = []
        all_skills = self.registry.list_all(CapabilityType.SKILL)

        eval_ctx = {
            "task_class": intent.task_class.value,
        }

        for skill in all_skills:
            if not skill.enabled:
                continue
            # Negative applicability check
            if skill.is_negatively_applicable(eval_ctx):
                continue
            # Check task applicability
            if not skill.is_applicable_to_task(intent.task_class):
                continue
            # Check subsystem applicability
            is_sub_match = any(skill.is_applicable_to_subsystem(s) for s in matched_subsystems)
            
            # Explicit selection criteria
            if skill.capability_id == "skill:antios-engineer":
                selected_skills.append(skill)
                why_selected["skill:antios-engineer"] = "Universal baseline engineering lifecycle policy"
            elif skill.capability_id == "skill:antios-debug" and intent.task_class == TaskClass.BUG:
                selected_skills.append(skill)
                why_selected["skill:antios-debug"] = "Mandated root-cause debugging procedure for BUG tasks"
            elif skill.capability_id == "skill:antios-verifier" and risk_tier in ("HIGH", "CRITICAL"):
                selected_skills.append(skill)
                why_selected["skill:antios-verifier"] = f"Mandated fresh-context audit for {risk_tier} risk task"
            elif skill.capability_id == "skill:antios-adapt-project" and (intent.task_class in (TaskClass.INVESTIGATION, TaskClass.RELEASE_MAINTENANCE) or intent.task_class.value in ("MAINTENANCE", "RELEASE_MAINTENANCE")):
                selected_skills.append(skill)
                why_selected["skill:antios-adapt-project"] = "Mandated procedure for repository adaptation"
            elif is_sub_match and skill.scope == CapabilityScope.PROJECT_LOCAL:
                selected_skills.append(skill)
                why_selected[skill.capability_id] = f"Project-local skill scoped to subsystem '{matched_subsystems[0]}'"

        # Deduplicate skills
        selected_skills = sorted(list({s.capability_id: s for s in selected_skills}.values()), key=lambda s: s.capability_id)

        # ---------------------------------------------------------------------
        # 4. Rule Resolution & Precedence Conflict Checking
        # ---------------------------------------------------------------------
        selected_rules: List[Capability] = []
        all_rules = self.registry.list_all(CapabilityType.RULE)

        for rule in all_rules:
            if not rule.enabled:
                continue
            if rule.is_applicable_to_task(intent.task_class):
                # Check subsystem or wildcard
                if any(rule.is_applicable_to_subsystem(s) for s in matched_subsystems) or "*" in rule.applies_to_subsystems:
                    selected_rules.append(rule)

        # Ingest Subsystem-specific rules as dynamic capabilities if declared
        for sr in sub_governing_rules:
            sr_cap = Capability(
                capability_id=f"rule:subsystem-{len(selected_rules)}",
                type=CapabilityType.RULE,
                name=sr[:30],
                purpose=sr,
                scope=CapabilityScope.SUBSYSTEM,
                applies_to_subsystems=matched_subsystems,
                metadata={
                    "precedence": RulePrecedence.SUBSYSTEM_INVARIANT.value,
                    "precedence_name": RulePrecedence.SUBSYSTEM_INVARIANT.name,
                    "rule_source": "SUBSYSTEM_MANIFEST",
                }
            )
            selected_rules.append(sr_cap)

        # Sort rules by precedence (Rank 1 to 5)
        selected_rules.sort(key=lambda r: r.metadata.get("precedence", RulePrecedence.PROJECT_GUIDANCE.value))
        rule_conflicts = self.registry.check_rule_conflicts(selected_rules)

        # ---------------------------------------------------------------------
        # 5. Tool & Script Resolution
        # ---------------------------------------------------------------------
        selected_tools: List[Capability] = []
        all_tools = self.registry.list_all(CapabilityType.TOOL)

        for tool in all_tools:
            if not tool.enabled:
                continue
            if tool.capability_id == "tool:navigate-repo":
                selected_tools.append(tool)
            elif tool.capability_id == "tool:audit-docs" and intent.task_class == TaskClass.DOCUMENTATION:
                selected_tools.append(tool)
            elif tool.capability_id == "tool:recover-session" and intent.task_class == TaskClass.BUG:
                selected_tools.append(tool)
            elif tool.scope == CapabilityScope.ADAPTER and tool.capability_id.startswith("tool:runner-"):
                selected_tools.append(tool)

        # Add custom covering tests if discovered
        if test_commands:
            for i, tc in enumerate(test_commands[:2]):
                cmd_parts = tc.split()
                selected_tools.append(Capability(
                    capability_id=f"tool:test-subsystem-{i}",
                    type=CapabilityType.TOOL,
                    name=f"Subsystem Test ({tc[:25]})",
                    purpose=f"Covering test runner: {tc}",
                    scope=CapabilityScope.SUBSYSTEM,
                    metadata={"command": cmd_parts, "tier": "PROJECT_TOOL"}
                ))

        # ---------------------------------------------------------------------
        # 6. Verifier Selection
        # ---------------------------------------------------------------------
        if risk_tier == "CRITICAL":
            verifier = self.registry.get("verifier:independent-auditor")
            why_selected["verifier"] = "Critical risk mandates adversarial auditor"
        elif risk_tier == "HIGH":
            verifier = self.registry.get("verifier:maker-checker")
            why_selected["verifier"] = "High risk mandates Maker-Checker independent verification"
        elif intent.task_class in (TaskClass.FEATURE, TaskClass.BUG, TaskClass.REFACTOR):
            verifier = self.registry.get("verifier:maker-checker")
            why_selected["verifier"] = "Code-modifying workflows default to Maker-Checker"
        else:
            verifier = self.registry.get("verifier:solo")
            why_selected["verifier"] = "Read-only or doc task uses solo direct test execution"

        verifier_dict = verifier.to_dict() if verifier else {"name": "Default Solo Verifier", "type": "VERIFIER"}

        # ---------------------------------------------------------------------
        # 7. Specialist Agent Selection (Shallow Depth Law <= 2)
        # ---------------------------------------------------------------------
        selected_specialists: List[Capability] = []
        if intent.task_class == TaskClass.BUG:
            spec = self.registry.get("specialist:root-cause-debugger")
            if spec:
                selected_specialists.append(spec)
        elif risk_tier in ("HIGH", "CRITICAL"):
            spec = self.registry.get("specialist:independent-verifier")
            if spec:
                selected_specialists.append(spec)
        else:
            spec = self.registry.get("specialist:core-engineer")
            if spec:
                selected_specialists.append(spec)

        # ---------------------------------------------------------------------
        # 8. MCP Justification Engine
        # ---------------------------------------------------------------------
        mcp_decision = self.evaluate_mcp_justification(task_intent, matched_subsystems)

        # ---------------------------------------------------------------------
        # 9. Irrelevant Capabilities Accounting
        # ---------------------------------------------------------------------
        total_in_reg = len(self.registry.list_all(enabled_only=False))
        total_selected = len(selected_skills) + len(selected_rules) + len(selected_tools) + (1 if verifier else 0) + len(selected_specialists)
        irrelevant_filtered = max(0, total_in_reg - total_selected)

        # Confidence calculation
        confidence = intent.confidence
        if epistemic_state == "UNKNOWN":
            confidence = 0.0
        elif epistemic_state == "INFERRED":
            confidence = min(0.75, confidence)

        pack_id = f"pack-{abs(hash(task_intent + ''.join(files))) % 1000000:06d}"

        return CapabilityPack(
            pack_id=pack_id,
            project_name=self.project_name,
            task_intent=task_intent,
            task_class=intent.task_class.value,
            risk_tier=risk_tier,
            matched_subsystems=matched_subsystems,
            matched_components=matched_components,
            workflow={
                "id": wf_id,
                "name": wf_spec.name,
                "description": wf_spec.description,
                "step_count": len(wf_spec.steps),
                "composed_skills": wf_spec.composed_skills,
            },
            skills=[s.to_dict() for s in selected_skills],
            rules=[r.to_dict() for r in selected_rules],
            tools=[t.to_dict() for t in selected_tools],
            verifier=verifier_dict,
            specialists=[sp.to_dict() for sp in selected_specialists],
            providers=[],
            mcp_decision=mcp_decision.to_dict(),
            why_selected=why_selected,
            conflicts=rule_conflicts,
            unknowns=unknowns,
            evidence=f"Resolved via CapabilityRouter for task '{task_intent}'",
            confidence=confidence,
            epistemic_state=epistemic_state,
            irrelevant_capabilities_filtered=irrelevant_filtered,
        )
