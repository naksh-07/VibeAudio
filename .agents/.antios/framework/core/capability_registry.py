"""AntiOS Canonical Capability Registry.

Maintains the deterministic in-memory index of all engineering capabilities
in AntiOS across skills, rules, workflows, tools, verifiers, specialists,
and external/MCP providers.

Answers:
1. "What capabilities exist?"
2. "Which capabilities apply here?"
"""

from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional, Set, Union

from framework.core.capability import (
    Capability,
    CapabilityScope,
    CapabilityType,
    RuleConflictStatus,
    RulePrecedence,
    VerifierType,
    MCPStatus,
)
from framework.core.lifecycle import RiskTier, TaskClass
from framework.core.workflow import WORKFLOW_REGISTRY


class CapabilityRegistry:
    """Canonical in-memory registry and deterministic index of capabilities."""

    def __init__(self) -> None:
        self._capabilities: Dict[str, Capability] = {}
        self._by_type: Dict[CapabilityType, List[str]] = {t: [] for t in CapabilityType}
        self._by_subsystem: Dict[str, List[str]] = {}
        self._by_task_type: Dict[str, List[str]] = {}

    def register(self, cap: Capability, overwrite: bool = True) -> None:
        """Registers a capability and updates secondary lookup indices."""
        cid = cap.capability_id.strip()
        if cid in self._capabilities and not overwrite:
            raise ValueError(f"Capability '{cid}' already registered")

        # Clean existing index references if overwriting
        if cid in self._capabilities:
            old_cap = self._capabilities[cid]
            if cid in self._by_type[old_cap.type]:
                self._by_type[old_cap.type].remove(cid)
            for sub in old_cap.applies_to_subsystems:
                sub_clean = sub.strip().lower()
                if sub_clean in self._by_subsystem and cid in self._by_subsystem[sub_clean]:
                    self._by_subsystem[sub_clean].remove(cid)
            for tt in old_cap.applies_to_task_types:
                tt_clean = tt.strip().upper()
                if tt_clean in self._by_task_type and cid in self._by_task_type[tt_clean]:
                    self._by_task_type[tt_clean].remove(cid)

        self._capabilities[cid] = cap
        self._by_type[cap.type].append(cid)

        for sub in cap.applies_to_subsystems:
            sub_clean = sub.strip().lower()
            if sub_clean not in self._by_subsystem:
                self._by_subsystem[sub_clean] = []
            if cid not in self._by_subsystem[sub_clean]:
                self._by_subsystem[sub_clean].append(cid)

        for tt in cap.applies_to_task_types:
            tt_clean = tt.strip().upper()
            if tt_clean not in self._by_task_type:
                self._by_task_type[tt_clean] = []
            if cid not in self._by_task_type[tt_clean]:
                self._by_task_type[tt_clean].append(cid)

    def get(self, capability_id: str) -> Optional[Capability]:
        """Retrieves capability by ID."""
        return self._capabilities.get(capability_id.strip())

    def list_all(
        self,
        cap_type: Optional[CapabilityType] = None,
        scope: Optional[CapabilityScope] = None,
        enabled_only: bool = True,
    ) -> List[Capability]:
        """Lists all registered capabilities with optional filtering."""
        caps = list(self._capabilities.values())
        if cap_type:
            caps = [c for c in caps if c.type == cap_type]
        if scope:
            caps = [c for c in caps if c.scope == scope]
        if enabled_only:
            caps = [c for c in caps if c.enabled]
        return sorted(caps, key=lambda c: (c.type.value, c.name))

    def find_by_subsystem(self, subsystem_id: str, enabled_only: bool = True) -> List[Capability]:
        """Finds capabilities mapped to a subsystem ID or wildcard '*'."""
        clean_sub = subsystem_id.strip().lower()
        ids: Set[str] = set()
        if "*" in self._by_subsystem:
            ids.update(self._by_subsystem["*"])
        if clean_sub in self._by_subsystem:
            ids.update(self._by_subsystem[clean_sub])

        res = [self._capabilities[cid] for cid in ids if cid in self._capabilities]
        if enabled_only:
            res = [c for c in res if c.enabled]
        return sorted(res, key=lambda c: (c.type.value, c.name))

    def find_by_task_type(self, task_type: Union[TaskClass, str], enabled_only: bool = True) -> List[Capability]:
        """Finds capabilities mapped to a task class or wildcard '*'."""
        tt_str = task_type.value if isinstance(task_type, TaskClass) else str(task_type).upper()
        ids: Set[str] = set()
        if "*" in self._by_task_type:
            ids.update(self._by_task_type["*"])
        if tt_str in self._by_task_type:
            ids.update(self._by_task_type[tt_str])

        res = [self._capabilities[cid] for cid in ids if cid in self._capabilities]
        if enabled_only:
            res = [c for c in res if c.enabled]
        return sorted(res, key=lambda c: (c.type.value, c.name))

    def check_rule_conflicts(self, applicable_rules: List[Capability]) -> List[Dict[str, Any]]:
        """Identifies conflicting rule claims and evaluates precedence.
        
        Platform Hook (Rank 1) > Core Invariant (Rank 2) > Adapter Policy (Rank 3) 
        > Subsystem Invariant (Rank 4) > Project Guidance (Rank 5).
        """
        conflicts: List[Dict[str, Any]] = []
        if len(applicable_rules) < 2:
            return conflicts

        # Compare pairs for potential conflict heuristics (e.g. skip test vs require test)
        for i in range(len(applicable_rules)):
            for j in range(i + 1, len(applicable_rules)):
                r1 = applicable_rules[i]
                r2 = applicable_rules[j]

                p1 = r1.metadata.get("precedence", RulePrecedence.PROJECT_GUIDANCE.value)
                p2 = r2.metadata.get("precedence", RulePrecedence.PROJECT_GUIDANCE.value)

                # Heuristic keyword conflict detection
                t1 = (r1.purpose + " " + r1.name).lower()
                t2 = (r2.purpose + " " + r2.name).lower()

                is_test_conflict = ("skip test" in t1 and "require test" in t2) or ("skip test" in t2 and "require test" in t1)
                is_write_conflict = ("allow write" in t1 and "immutable" in t2) or ("allow write" in t2 and "immutable" in t1)

                if is_test_conflict or is_write_conflict:
                    winner = r1 if p1 <= p2 else r2
                    loser = r2 if p1 <= p2 else r1
                    conflicts.append({
                        "rule_a": r1.capability_id,
                        "rule_b": r2.capability_id,
                        "description": f"Conflict between '{r1.name}' (Rank {p1}) and '{r2.name}' (Rank {p2})",
                        "status": RuleConflictStatus.CONFLICT_DETECTED.value,
                        "winning_rule": winner.capability_id,
                        "winning_precedence": min(p1, p2),
                        "resolution_note": f"Rule '{winner.name}' prevails by authoritative precedence (Rank {min(p1, p2)} <= Rank {max(p1, p2)}).",
                    })

        return conflicts

    def to_dict(self) -> Dict[str, Any]:
        """Serializes registry to dict."""
        return {
            "total_capabilities": len(self._capabilities),
            "capabilities": [c.to_dict() for c in self.list_all(enabled_only=False)],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CapabilityRegistry:
        """Constructs registry from dict."""
        reg = cls()
        for cdata in data.get("capabilities", []):
            cap = Capability.from_dict(cdata)
            reg.register(cap)
        return reg


def build_default_registry(
    workspace_root: Optional[str] = None,
    config_dict: Optional[Dict[str, Any]] = None,
    profile: Optional[Any] = None,
) -> CapabilityRegistry:
    """Constructs the canonical default capability registry for AntiOS.
    
    Unifies Core skills, workflows, invariants, tools/scripts, verifiers,
    specialist roles, adapter runners, and MCP policies without disk crawling bloat.
    """
    reg = CapabilityRegistry()

    # -------------------------------------------------------------------------
    # 1. Canonical Core Skills
    # -------------------------------------------------------------------------
    reg.register(Capability(
        capability_id="skill:antios-engineer",
        type=CapabilityType.SKILL,
        name="AntiOS Universal Engineering Skill",
        purpose="Injects universal engineering lifecycle, 3-tier risk matrix, shallow depth law, and Stop Gate discipline.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["FEATURE", "BUG", "REFACTOR", "INVESTIGATION", "DOCUMENTATION", "RELEASE"],
        related_rules=["rule:core-fail-closed", "rule:stop-gate-ratchet", "rule:same-change-set"],
        related_workflows=["workflow:feature", "workflow:refactor", "workflow:release"],
        verifier="verifier:maker-checker",
        risk="MEDIUM",
        evidence="Canonical skill in .agents/skills/antios-engineer/SKILL.md",
        source=".agents/skills/antios-engineer/SKILL.md",
    ))

    reg.register(Capability(
        capability_id="skill:antios-verifier",
        type=CapabilityType.SKILL,
        name="AntiOS Independent Verifier Skill",
        purpose="Injects fresh-context Checker contract, physical diff audit, test execution, and structured JSON verdict reporting.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["FEATURE", "BUG", "REFACTOR", "RELEASE"],
        prerequisites=["skill:antios-engineer"],
        related_rules=["rule:shallow-depth-law", "rule:fresh-context-checker", "rule:stop-gate-ratchet"],
        verifier="verifier:maker-checker",
        risk="HIGH",
        evidence="Canonical skill in .agents/skills/antios-verifier/SKILL.md",
        source=".agents/skills/antios-verifier/SKILL.md",
        negative_applicability=["NOT_STAGE:IMPLEMENT", "NOT_ROLE:MAKER", "NOT_TASK:INVESTIGATION"],
    ))

    reg.register(Capability(
        capability_id="skill:antios-debug",
        type=CapabilityType.SKILL,
        name="AntiOS Root-Cause Debugging Skill",
        purpose="Injects deterministic 5-step debugging procedure: Reproduce -> Hypothesize -> Isolate -> Patch -> Verify.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["BUG"],
        related_rules=["rule:stop-gate-ratchet"],
        related_workflows=["workflow:bug"],
        verifier="verifier:maker-checker",
        risk="MEDIUM",
        evidence="Canonical skill in .agents/skills/antios-debug/SKILL.md",
        source=".agents/skills/antios-debug/SKILL.md",
        negative_applicability=["NOT_TASK:DOCUMENTATION", "NOT_TASK:INVESTIGATION", "NOT_TASK:RELEASE"],
    ))

    reg.register(Capability(
        capability_id="skill:antios-adapt-project",
        type=CapabilityType.SKILL,
        name="AntiOS Universal Project Adaptation Skill",
        purpose="Injects 9-step project adaptation procedure to discover traits, audit guidance, and configure adapter without touching Core.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["MAINTENANCE", "INVESTIGATION", "FEATURE"],
        related_rules=["rule:core-immutable", "rule:adapter-boundary"],
        verifier="verifier:solo",
        risk="LOW",
        evidence="Canonical skill in .agents/skills/antios-adapt-project/SKILL.md",
        source=".agents/skills/antios-adapt-project/SKILL.md",
    ))

    # -------------------------------------------------------------------------
    # 2. Canonical Engineering Workflows
    # -------------------------------------------------------------------------
    for t_class, w_spec in WORKFLOW_REGISTRY.items():
        w_id = f"workflow:{t_class.value.lower()}"
        reg.register(Capability(
            capability_id=w_id,
            type=CapabilityType.WORKFLOW,
            name=w_spec.name,
            purpose=w_spec.description,
            scope=CapabilityScope.CORE,
            applies_to_subsystems=["*"],
            applies_to_task_types=[t_class.value],
            related_rules=["rule:stop-gate-ratchet"],
            related_tools=["tool:tests-run-all"],
            verifier="verifier:maker-checker" if w_spec.default_risk == RiskTier.HIGH else "verifier:solo",
            risk=w_spec.default_risk.value,
            evidence="Codified in framework/core/workflow.py WORKFLOW_REGISTRY",
            source="framework/core/workflow.py",
            metadata={
                "task_class": t_class.value,
                "step_count": len(w_spec.steps),
                "composed_skills": w_spec.composed_skills,
                "entry_conditions": w_spec.entry_conditions,
                "completion_criteria": w_spec.completion_criteria,
            }
        ))

    # -------------------------------------------------------------------------
    # 3. Canonical Governing Rules & Invariants
    # -------------------------------------------------------------------------
    reg.register(Capability(
        capability_id="rule:platform-hook-interception",
        type=CapabilityType.RULE,
        name="Platform Hook IPC Interception",
        purpose="Host PreToolUse and Stop stdio hooks are authoritative interceptors and cannot be bypassed.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["*"],
        evidence="ANTIOS_SOURCE_OF_TRUTH.md Rank 1 Authority",
        source="ANTIOS_SOURCE_OF_TRUTH.md",
        metadata={
            "precedence": RulePrecedence.PLATFORM_HOOK.value,
            "precedence_name": RulePrecedence.PLATFORM_HOOK.name,
            "rule_source": "PLATFORM_HOOK_IPC",
        }
    ))

    reg.register(Capability(
        capability_id="rule:core-immutable",
        type=CapabilityType.RULE,
        name="AntiOS Immutable Core Self-Protection",
        purpose="Directories .agents/, framework/, and antios.config.json are protected from tool mutations during ordinary domain tasks.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["*"],
        evidence="Enforced by framework/core/guard.py",
        source="framework/core/guard.py",
        metadata={
            "precedence": RulePrecedence.CORE_INVARIANT.value,
            "precedence_name": RulePrecedence.CORE_INVARIANT.name,
            "rule_source": "CORE_GUARD",
        }
    ))

    reg.register(Capability(
        capability_id="rule:stop-gate-ratchet",
        type=CapabilityType.RULE,
        name="Physical Stop Gate Verification Ratchet",
        purpose="No task completion without physical execution of test runner subprocess returning OS exit code 0.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["*"],
        evidence="Enforced by framework/core/gate.py",
        source="framework/core/gate.py",
        metadata={
            "precedence": RulePrecedence.CORE_INVARIANT.value,
            "precedence_name": RulePrecedence.CORE_INVARIANT.name,
            "rule_source": "STOP_GATE",
        }
    ))

    reg.register(Capability(
        capability_id="rule:same-change-set",
        type=CapabilityType.RULE,
        name="Atomic Same Change Set Policy",
        purpose="Code modifications, covering tests, and documentation must be committed in the same atomic change set.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["FEATURE", "BUG", "REFACTOR", "RELEASE"],
        evidence="Enforced by framework/core/changeset.py",
        source="framework/core/changeset.py",
        metadata={
            "precedence": RulePrecedence.CORE_INVARIANT.value,
            "precedence_name": RulePrecedence.CORE_INVARIANT.name,
            "rule_source": "CHANGESET_POLICY",
        }
    ))

    reg.register(Capability(
        capability_id="rule:shallow-depth-law",
        type=CapabilityType.RULE,
        name="Shallow Subagent Depth Law",
        purpose="Subagent nesting depth is strictly bounded to depth <= 2 (Root -> Child). Subagents cannot spawn child swarms.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["*"],
        evidence="ANTIOS_V1.md Section 4 & verdict.py prepare_checker_context",
        source="ANTIOS_V1.md",
        metadata={
            "precedence": RulePrecedence.CORE_INVARIANT.value,
            "precedence_name": RulePrecedence.CORE_INVARIANT.name,
            "rule_source": "ARCHITECTURAL_CONSTITUTION",
        }
    ))

    reg.register(Capability(
        capability_id="rule:clean-working-tree",
        type=CapabilityType.RULE,
        name="Clean Working Tree & Conflict Marker Prohibition",
        purpose="Working trees must be free of unresolved git merge conflicts (<<<<<<<, =======, >>>>>>>).",
        scope=CapabilityScope.ADAPTER,
        applies_to_subsystems=["*"],
        applies_to_task_types=["*"],
        evidence="Enforced by framework/core/worktree.py",
        source="framework/core/worktree.py",
        metadata={
            "precedence": RulePrecedence.ADAPTER_POLICY.value,
            "precedence_name": RulePrecedence.ADAPTER_POLICY.name,
            "rule_source": "WORKTREE_POLICY",
        }
    ))

    # -------------------------------------------------------------------------
    # 4. Canonical Verifiers
    # -------------------------------------------------------------------------
    reg.register(Capability(
        capability_id="verifier:solo",
        type=CapabilityType.VERIFIER,
        name="Solo Direct Test Verifier",
        purpose="Runs configured test suite directly via run_command; verifies process exit code 0 for LOW risk tasks.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["INVESTIGATION", "DOCUMENTATION"],
        risk="LOW",
        evidence="gate.py test runner execution",
        source="framework/core/gate.py",
        metadata={"verifier_type": VerifierType.SOLO_VERIFIER.value}
    ))

    reg.register(Capability(
        capability_id="verifier:maker-checker",
        type=CapabilityType.VERIFIER,
        name="Maker-Checker Independent Verifier",
        purpose="Dispatches fresh-context Checker subagent (TypeName='self') to audit diffs and execute physical tests for MEDIUM/HIGH risk tasks.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["FEATURE", "BUG", "REFACTOR"],
        risk="HIGH",
        evidence="verdict.py structured JSON verdict contract",
        source="framework/core/verdict.py",
        metadata={"verifier_type": VerifierType.MAKER_CHECKER.value}
    ))

    reg.register(Capability(
        capability_id="verifier:independent-auditor",
        type=CapabilityType.VERIFIER,
        name="Independent Adversarial Auditor",
        purpose="Dispatches fresh-context auditor to perform edge-case fuzzing, victory audit, and regression checks on CRITICAL risk tasks.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["RELEASE", "REFACTOR"],
        risk="CRITICAL",
        evidence="Adaptive Orchestrator v4 Section 9 & Stop Gate",
        source="framework/core/verdict.py",
        metadata={"verifier_type": VerifierType.INDEPENDENT_AUDITOR.value}
    ))

    # -------------------------------------------------------------------------
    # 5. Deterministic Tools & Local Scripts
    # -------------------------------------------------------------------------
    reg.register(Capability(
        capability_id="tool:navigate-repo",
        type=CapabilityType.TOOL,
        name="Repository Navigation & Wayfinding CLI",
        purpose="Locates files, subsystems, components, impact, blast radius, and capabilities with progressive disclosure L0-L5.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["*"],
        evidence="Implemented in framework/scripts/tools/navigate_repo.py",
        source="framework/scripts/tools/navigate_repo.py",
        metadata={"entrypoint": "python framework/scripts/tools/navigate_repo.py", "tier": "SCRIPT"}
    ))

    reg.register(Capability(
        capability_id="tool:audit-docs",
        type=CapabilityType.TOOL,
        name="Syntactic Documentation Auditor",
        purpose="Scans markdown docs and skills for broken file/heading references, dead links, and token budget drift.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["DOCUMENTATION", "MAINTENANCE"],
        evidence="Implemented in framework/scripts/tools/audit_docs.py",
        source="framework/scripts/tools/audit_docs.py",
        metadata={"entrypoint": "python framework/scripts/tools/audit_docs.py", "tier": "SCRIPT"}
    ))

    reg.register(Capability(
        capability_id="tool:adapt-project",
        type=CapabilityType.TOOL,
        name="Project Discovery & Adaptation CLI",
        purpose="Inspects target codebase, identifies toolchains/subsystems, and proposes safe project adapter configurations.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["MAINTENANCE", "INVESTIGATION"],
        evidence="Implemented in framework/scripts/tools/adapt_project.py",
        source="framework/scripts/tools/adapt_project.py",
        metadata={"entrypoint": "python framework/scripts/tools/adapt_project.py", "tier": "SCRIPT"}
    ))

    reg.register(Capability(
        capability_id="tool:distill-memory",
        type=CapabilityType.TOOL,
        name="Memory Distillation CLI",
        purpose="Audits candidate lessons and promotes recurring patterns (recurrence >= 2) to durable project memory.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["MAINTENANCE", "CONSOLIDATE"],
        evidence="Implemented in framework/scripts/tools/distill_memory.py",
        source="framework/scripts/tools/distill_memory.py",
        metadata={"entrypoint": "python framework/scripts/tools/distill_memory.py", "tier": "SCRIPT"}
    ))

    reg.register(Capability(
        capability_id="tool:recover-session",
        type=CapabilityType.TOOL,
        name="Session State Recovery CLI",
        purpose="Detects discrepancies between recorded context claims and physical git working tree reality.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["*"],
        evidence="Implemented in framework/scripts/tools/recover_session.py",
        source="framework/scripts/tools/recover_session.py",
        metadata={"entrypoint": "python framework/scripts/tools/recover_session.py", "tier": "SCRIPT"}
    ))

    # -------------------------------------------------------------------------
    # 6. Specialist Agent Models (Shallow Depth Law <= 2)
    # -------------------------------------------------------------------------
    reg.register(Capability(
        capability_id="specialist:core-engineer",
        type=CapabilityType.SPECIALIST,
        name="AntiOS Core Engineer",
        purpose="Primary implementer responsible for scoped edits, test authoring, and diff preparation.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["FEATURE", "REFACTOR", "BUG"],
        verifier="verifier:maker-checker",
        metadata={
            "role_name": "Core Engineer",
            "responsibility": "Feature implementation, refactoring, and test creation",
            "allowed_capabilities": ["skill:antios-engineer", "tool:navigate-repo", "tool:audit-docs"],
            "required_verifier": "verifier:maker-checker",
            "escalation_path": "Root Orchestrator",
            "max_nesting_depth": 2,
        }
    ))

    reg.register(Capability(
        capability_id="specialist:independent-verifier",
        type=CapabilityType.SPECIALIST,
        name="AntiOS Independent Verifier",
        purpose="Fresh-context Checker subagent executing physical tests, auditing git diffs, and emitting structured JSON verdicts.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["FEATURE", "BUG", "REFACTOR", "RELEASE"],
        verifier="verifier:maker-checker",
        metadata={
            "role_name": "Independent Verifier",
            "responsibility": "Independent verification and diff auditing in fresh context",
            "allowed_capabilities": ["skill:antios-verifier", "tool:navigate-repo"],
            "required_verifier": "verifier:maker-checker",
            "escalation_path": "Root Orchestrator",
            "max_nesting_depth": 2,
        }
    ))

    reg.register(Capability(
        capability_id="specialist:root-cause-debugger",
        type=CapabilityType.SPECIALIST,
        name="AntiOS Root-Cause Debugger",
        purpose="Investigates failing tests, crashes, and regressions by formulating hypotheses and minimal reproducing tests.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["*"],
        applies_to_task_types=["BUG"],
        verifier="verifier:maker-checker",
        metadata={
            "role_name": "Root-Cause Debugger",
            "responsibility": "Minimal test reproduction and isolated patch generation",
            "allowed_capabilities": ["skill:antios-debug", "skill:antios-engineer", "tool:recover-session"],
            "required_verifier": "verifier:maker-checker",
            "escalation_path": "Root Orchestrator",
            "max_nesting_depth": 2,
        }
    ))

    # -------------------------------------------------------------------------
    # 7. MCP Providers under ANTIOS_MCP_POLICY.md
    # -------------------------------------------------------------------------
    reg.register(Capability(
        capability_id="mcp:chrome-devtools",
        type=CapabilityType.MCP_PROVIDER,
        name="Chrome DevTools MCP",
        purpose="Deep browser DOM inspection, accessibility trees, console errors, visual snapshots for web/frontend components.",
        scope=CapabilityScope.ADAPTER,
        applies_to_subsystems=["ui", "frontend", "web", "client"],
        applies_to_task_types=["FEATURE", "BUG", "INVESTIGATION"],
        evidence="ANTIOS_MCP_POLICY.md: USEFUL tier for frontend UI inspection",
        source="ANTIOS_MCP_POLICY.md",
        metadata={"mcp_status": MCPStatus.USEFUL.value, "server_name": "chrome-devtools-mcp"}
    ))

    reg.register(Capability(
        capability_id="mcp:playwright",
        type=CapabilityType.MCP_PROVIDER,
        name="Playwright Headless Browser MCP",
        purpose="Automated end-to-end headless browser interaction, UI flow testing, and click/fill interaction.",
        scope=CapabilityScope.ADAPTER,
        applies_to_subsystems=["ui", "frontend", "web", "e2e"],
        applies_to_task_types=["FEATURE", "BUG", "INVESTIGATION"],
        evidence="ANTIOS_MCP_POLICY.md: USEFUL tier for automated browser e2e testing",
        source="ANTIOS_MCP_POLICY.md",
        metadata={"mcp_status": MCPStatus.USEFUL.value, "server_name": "playwright"}
    ))

    reg.register(Capability(
        capability_id="mcp:gemini-api-docs",
        type=CapabilityType.MCP_PROVIDER,
        name="Gemini API Docs MCP",
        purpose="Official upstream Gemini SDK and API documentation search and chunk retrieval.",
        scope=CapabilityScope.CORE,
        applies_to_subsystems=["ai", "model", "gemini", "sdk"],
        applies_to_task_types=["FEATURE", "INVESTIGATION"],
        evidence="ANTIOS_MCP_POLICY.md: USEFUL tier for model integration API lookup",
        source="ANTIOS_MCP_POLICY.md",
        metadata={"mcp_status": MCPStatus.USEFUL.value, "server_name": "gemini-api-docs"}
    ))

    reg.register(Capability(
        capability_id="mcp:github",
        type=CapabilityType.MCP_PROVIDER,
        name="GitHub MCP Server",
        purpose="Remote PR creation, remote branch listing, and issue tracking. FORBIDDEN for local git operations.",
        scope=CapabilityScope.ADAPTER,
        applies_to_subsystems=["*"],
        applies_to_task_types=["RELEASE"],
        evidence="ANTIOS_MCP_POLICY.md: OPTIONAL tier strictly restricted to remote PR creation",
        source="ANTIOS_MCP_POLICY.md",
        metadata={"mcp_status": MCPStatus.OPTIONAL.value, "server_name": "github-mcp-server"}
    ))

    # Explicitly register REJECTED MCP candidates to prevent architectural drift
    for rejected_mcp in ["notion-mcp-server", "postman-mcp-server", "posthog", "unauthorized-external-mcp"]:
        reg.register(Capability(
            capability_id=f"mcp:{rejected_mcp}",
            type=CapabilityType.MCP_PROVIDER,
            name=f"Rejected MCP: {rejected_mcp}",
            purpose="Formally rejected from AntiOS engineering governance under ANTIOS_MCP_POLICY.md.",
            scope=CapabilityScope.CORE,
            enabled=False,
            evidence="ANTIOS_MCP_POLICY.md: REJECTED tier",
            source="ANTIOS_MCP_POLICY.md",
            metadata={"mcp_status": MCPStatus.REJECTED.value, "server_name": rejected_mcp}
        ))

    # -------------------------------------------------------------------------
    # 8. Ingest Project Adapter Configuration (antios.config.json)
    # -------------------------------------------------------------------------
    if config_dict:
        # Register configured test runners
        for runner in config_dict.get("test_runners", []):
            r_name = runner.get("name", "configured-runner")
            r_cmd = runner.get("default_command", [])
            cmd_str = " ".join(r_cmd) if isinstance(r_cmd, list) else str(r_cmd)
            r_id = f"tool:runner-{r_name}"
            reg.register(Capability(
                capability_id=r_id,
                type=CapabilityType.TOOL,
                name=f"Project Test Runner ({r_name})",
                purpose=f"Configured project test runner executing '{cmd_str}'",
                scope=CapabilityScope.ADAPTER,
                applies_to_subsystems=["*"],
                applies_to_task_types=["*"],
                evidence=f"Declared in antios.config.json test_runners",
                source="antios.config.json",
                metadata={"command": r_cmd, "tier": "PROJECT_TOOL"}
            ))

        # Register configured capabilities section if present
        caps_cfg = config_dict.get("capabilities", {})
        if isinstance(caps_cfg, dict):
            # Disabled capabilities
            for dis_id in caps_cfg.get("disabled_capabilities", []):
                existing = reg.get(dis_id)
                if existing:
                    existing.enabled = False

            # Project rules
            for pr in caps_cfg.get("project_rules", []):
                pr_id = pr.get("id", f"rule:project-{len(reg.list_all(CapabilityType.RULE))}")
                reg.register(Capability(
                    capability_id=pr_id if pr_id.startswith("rule:") else f"rule:{pr_id}",
                    type=CapabilityType.RULE,
                    name=pr.get("name", "Project Rule"),
                    purpose=pr.get("statement", pr.get("purpose", "")),
                    scope=CapabilityScope.PROJECT_LOCAL,
                    applies_to_subsystems=pr.get("applies_to_subsystems", ["*"]),
                    applies_to_task_types=pr.get("applies_to_task_types", ["*"]),
                    evidence="Declared in antios.config.json capabilities.project_rules",
                    source="antios.config.json",
                    metadata={
                        "precedence": RulePrecedence.PROJECT_GUIDANCE.value,
                        "precedence_name": RulePrecedence.PROJECT_GUIDANCE.name,
                        "rule_source": "PROJECT_CONFIG",
                    }
                ))

    return reg
