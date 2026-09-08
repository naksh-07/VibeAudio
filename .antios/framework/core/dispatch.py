"""AntiOS 2.0 Canonical Task Dispatch Pipeline.

Wires the canonical end-to-end execution flow:
USER TASK
   ↓
MAIN `ANTIOS` SKILL
   ↓
TASK CLASSIFIER
   ↓
PROJECT CONTEXT & WAYFINDING
   ↓
CAPABILITY RESOLUTION
   ↓
AGENT ROUTING
   ↓
ADAPTIVE ORCHESTRATOR
   ↓
TOOL / PROVIDER POLICY
   ↓
EXECUTION STRATEGY
   ↓
VERIFICATION GATES
   ↓
MEMORY DISTILLATION
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from framework.core.agent_role import AgentRoleType
from framework.core.agent_router import AgentRouter
from framework.core.agent_routing_pack import AgentRoutingPack
from framework.core.capability_pack import CapabilityPack
from framework.core.capability_router import CapabilityRouter
from framework.core.config import AntiOSConfig, load_config
from framework.core.context_budget import (
    ContextBudgetGovernor,
    ContextSourceItem,
    ContextSourceType,
)
from framework.core.context_freshness import FreshnessEvaluator
from framework.core.lifecycle import RiskTier, TaskClass
from framework.core.mission_state import (
    MissionPersistenceMode,
    MissionStateStore,
)
from framework.core.evidence import (
    EpistemicCategory,
    EvidenceItem,
    EvidencePackage,
    EvidenceState,
)
from framework.core.mission_evaluation import (
    EvaluationStatus,
    MissionEvaluationEngine,
    MissionEvaluationResult,
)
from framework.core.learning import (
    EpistemicSource,
    Observation,
    ObservationType,
)
from framework.core.project_proof import (
    EvidenceDistillationEngine,
    ProjectProofStore,
    ProofStatus,
    ProofSubject,
)
from framework.core.drift_health import (
    DriftAction,
    DriftSeverity,
    ProjectDriftEngine,
)


from framework.core.orchestration import (
    AdaptiveWorkforcePlanner,
    CanonicalWave,
    CoordinationLevel,
    DispatchGateResult,
    DispatchGateType,
    DualDispatchGates,
    GateDecision,
    MissionLedger,
    StructuredHandoff,
    WaveManager,
    WorkforceCostReasoning,
    WorkforceMode,
    WorkforceSizer,
    WriteSafetyEvaluator,
    WriteSafetyPolicy,
    determine_coordination_level,
)
from framework.core.subsystem import SubsystemDeclaration
from framework.core.wayfinding import LocalityResolution, WayfindingEngine


@dataclass
class TaskClassificationResult:
    """Outcome of deterministic task intent classification."""
    intent: str
    task_class: TaskClass
    risk_tier: RiskTier
    domains: List[str] = field(default_factory=list)
    file_mentions: List[str] = field(default_factory=list)
    is_research_and_impl: bool = False
    explicit_delegation: bool = False
    is_high_risk_investigation: bool = False


@dataclass
class MissionPlan:
    """Comprehensive resolved execution plan for an AntiOS mission."""
    mission_id: str
    task_intent: str
    task_class: str
    risk_tier: str
    matched_subsystems: List[str]
    matched_components: List[str]
    workforce_mode: WorkforceMode
    coordination_level: CoordinationLevel
    write_policy: WriteSafetyPolicy
    pre_planning_gate: DispatchGateResult
    execution_gate: DispatchGateResult
    primary_role: str
    assigned_specialists: List[str]
    configured_test_command: str
    verification_method: str
    capability_pack: Dict[str, Any]
    agent_routing: Dict[str, Any]
    initial_waves: List[str]
    reasons: List[str]
    cost_reasoning: Optional[Dict[str, Any]] = None
    workforce_planner_decision: Optional[Dict[str, Any]] = None
    context_budget_card: Optional[Dict[str, Any]] = None
    loaded_context: Optional[str] = None
    mission_state_mode: Optional[str] = None

    def format_card(self, max_lines: int = 25) -> str:
        """Emits a token-bounded summary card adhering to token budget (<= max_lines)."""
        subs_str = ", ".join(self.matched_subsystems) if self.matched_subsystems else "STANDALONE"
        specs_str = ", ".join(self.assigned_specialists) if self.assigned_specialists else "None (Solo Primary)"
        reasons_str = "; ".join(self.reasons[:2]) if self.reasons else "Deterministic pipeline resolution"

        lines = [
            "=== ANTIOS MISSION DISPATCH CARD ===",
            f"Mission ID:   {self.mission_id}",
            f"Task Class:   {self.task_class} [Risk: {self.risk_tier}]",
            f"Subsystem:    {subs_str}",
            f"Workforce:    {self.workforce_mode.value} (Coordination: {self.coordination_level.value})",
            f"Gate A Recon: {self.pre_planning_gate.decision.value} ({self.pre_planning_gate.recommended_workers} rec)",
            f"Gate B Exec:  {self.execution_gate.decision.value} ({self.execution_gate.recommended_workers} rec)",
            f"Primary:      {self.primary_role}",
            f"Specialists:  {specs_str}",
            f"Write Safety: {self.write_policy.value}",
            f"Test Runner:  {self.configured_test_command}",
            f"Verification: {self.verification_method}",
            f"Waves:        {' -> '.join(self.initial_waves)}",
            f"Rationale:    {reasons_str[:60]}",
        ]
        if self.context_budget_card:
            lines.append(f"Context:      {self.context_budget_card.get('total_allocated_tokens', 0)}/{self.context_budget_card.get('budget_limit', 0)} tok ({self.context_budget_card.get('selected_count', 0)} sel)")
        if self.cost_reasoning:
            lines.append(f"Cost Reason:  {self.cost_reasoning.get('why_this_workforce', '')[:60]}")
        lines.append("-------------------------------------")
        return "\n".join(lines[:max_lines])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "task_intent": self.task_intent,
            "task_class": self.task_class,
            "risk_tier": self.risk_tier,
            "matched_subsystems": list(self.matched_subsystems),
            "matched_components": list(self.matched_components),
            "workforce_mode": self.workforce_mode.value,
            "coordination_level": self.coordination_level.value,
            "write_policy": self.write_policy.value,
            "pre_planning_gate": self.pre_planning_gate.to_dict(),
            "execution_gate": self.execution_gate.to_dict(),
            "primary_role": self.primary_role,
            "assigned_specialists": list(self.assigned_specialists),
            "configured_test_command": self.configured_test_command,
            "verification_method": self.verification_method,
            "initial_waves": list(self.initial_waves),
            "reasons": list(self.reasons),
            "capability_pack": dict(self.capability_pack),
            "agent_routing": dict(self.agent_routing),
            "cost_reasoning": dict(self.cost_reasoning) if self.cost_reasoning else None,
            "workforce_planner_decision": dict(self.workforce_planner_decision) if self.workforce_planner_decision else None,
            "context_budget_card": dict(self.context_budget_card) if self.context_budget_card else None,
            "loaded_context": self.loaded_context,
            "mission_state_mode": self.mission_state_mode,
        }



class TaskDispatchPipeline:
    """Deterministic, end-to-end mission dispatch pipeline for AntiOS."""

    def __init__(
        self,
        workspace_root: str = ".",
        config: Optional[AntiOSConfig] = None,
    ):
        self.workspace_root = os.path.normcase(os.path.abspath(workspace_root))
        self.config = config or load_config(self.workspace_root)
        self.wayfinding = WayfindingEngine(workspace_root=self.workspace_root)
        self._populate_wayfinding()
        
        cfg_dict = {}
        if self.config:
            if hasattr(self.config, "__dataclass_fields__"):
                cfg_dict = asdict(self.config)
            elif hasattr(self.config, "to_dict"):
                cfg_dict = self.config.to_dict()

        self.cap_router = CapabilityRouter(
            workspace_root=self.workspace_root,
            config_dict=cfg_dict,
            project_name=getattr(self.config, "name", "AntiOS"),
        )
        self.agent_router = AgentRouter(config=self.config, project_name=getattr(self.config, "name", "AntiOS"))

    def _populate_wayfinding(self) -> None:
        """Populates wayfinding components from config or standard discovery."""
        if hasattr(self.config, "components") and self.config.components:
            for sub_id, data in self.config.components.items():
                if isinstance(data, dict):
                    data["subsystem_id"] = sub_id
                    decl = SubsystemDeclaration.from_dict(data)
                    self.wayfinding.register_subsystem(decl)

    def classify_task(self, query: str) -> TaskClassificationResult:
        """Deterministically classifies natural language task query."""
        q_lower = query.lower()

        # Detect explicit delegation request
        explicit_delegation = any(
            w in q_lower for w in ["parallel", "swarm", "delegate", "subagent", "teamwork", "multiple agents"]
        )

        # Detect file path mentions
        file_mentions = re.findall(r"[\w\-\./\\]+\.[a-zA-Z0-9]+", query)

        # Determine Task Class
        if any(w in q_lower for w in ["bug", "fix", "error", "fail", "crash", "traceback", "exception", "broken"]):
            task_class = TaskClass.BUG
        elif any(w in q_lower for w in ["refactor", "restructure", "clean up", "reorganize"]):
            task_class = TaskClass.REFACTOR
        elif any(w in q_lower for w in ["doc", "docs", "readme", "specification", "guide", "comment"]):
            task_class = TaskClass.DOCUMENTATION
        elif any(w in q_lower for w in ["release", "publish", "bump", "version", "deploy"]):
            task_class = TaskClass.RELEASE
        elif any(w in q_lower for w in ["investigate", "audit", "research", "spike", "evaluate", "explore"]):
            task_class = TaskClass.INVESTIGATION
        else:
            task_class = TaskClass.FEATURE

        # Determine Risk Tier
        if any(w in q_lower for w in ["security", "auth", "secret", "token", "password", "crypto", "vulnerability"]):
            risk_tier = RiskTier.HIGH
        elif task_class in (TaskClass.REFACTOR, TaskClass.RELEASE) or any(
            w in q_lower for w in ["database", "schema", "persistence", "migration", "payment", "governance"]
        ):
            risk_tier = RiskTier.HIGH
        elif task_class == TaskClass.DOCUMENTATION:
            risk_tier = RiskTier.LOW
        else:
            risk_tier = RiskTier.MEDIUM

        is_research_and_impl = (
            task_class in (TaskClass.FEATURE, TaskClass.REFACTOR)
            and any(w in q_lower for w in ["investigate", "research", "spike", "explore", "evaluate"])
        )
        is_high_risk_investigation = (
            task_class == TaskClass.INVESTIGATION and risk_tier == RiskTier.HIGH
        )

        # Extract domain hints
        domains = []
        for d in ["auth", "database", "api", "frontend", "backend", "governance", "ui", "worker", "storage"]:
            if d in q_lower:
                domains.append(d)

        return TaskClassificationResult(
            intent=query,
            task_class=task_class,
            risk_tier=risk_tier,
            domains=domains,
            file_mentions=file_mentions,
            is_research_and_impl=is_research_and_impl,
            explicit_delegation=explicit_delegation,
            is_high_risk_investigation=is_high_risk_investigation,
        )

    def dispatch(
        self,
        task_query: str,
        target_files: Optional[List[str]] = None,
        explicit_mode: Optional[str] = None,
        workstream_count: int = 1,
        independent_streams: int = 1,
        is_tightly_coupled: bool = False,
    ) -> MissionPlan:
        """Executes the full canonical dispatch pipeline and produces an authoritative MissionPlan."""
        target_files = target_files or []

        # 1. Classify Task
        classification = self.classify_task(task_query)

        # 2. Wayfinding / Locality Resolution
        query_text = task_query
        if target_files:
            query_text += f" {' '.join(target_files)}"
        locality = self.wayfinding.locate(query_text)
        if locality:
            matched_subs = [locality.matched_subsystem_id]
            matched_comps = locality.entrypoints + locality.authoritative_files[:2]
        else:
            matched_subs = ["core"] if "core" in task_query.lower() else ["general"]
            matched_comps = []

        # 3. Capability Resolution
        cap_pack = self.cap_router.resolve_capabilities(
            task_intent=task_query,
            target_files=target_files,
            task_class_hint=classification.task_class,
        )

        # 4. Agent Routing
        routing_pack = self.agent_router.route_task(
            capability_pack=cap_pack,
            target_files=target_files,
        )

        # 5. Dual Dispatch Gates Evaluation
        domain_count = max(len(classification.domains), len(matched_subs), 1)
        file_count = max(len(target_files), len(classification.file_mentions), 1)
        module_count = max(len(matched_subs), 1)

        pre_gate = DualDispatchGates.evaluate_pre_planning(
            domain_count=domain_count,
            independent_lanes=independent_streams,
            file_count=file_count,
            module_count=module_count,
            is_research_and_impl=classification.is_research_and_impl,
            explicit_delegation_request=classification.explicit_delegation,
            is_high_risk_investigation=classification.is_high_risk_investigation,
        )

        exec_gate = DualDispatchGates.evaluate_execution_dispatch(
            workstream_count=workstream_count,
            independent_streams=independent_streams,
            is_tightly_coupled=is_tightly_coupled,
            file_ownership_disjoint=True,
            risk_tier=classification.risk_tier.value,
            remaining_budget=20,
            active_capacity=10,
        )

        # 6. Workforce Sizing Mode
        if explicit_mode:
            try:
                mode = WorkforceMode(explicit_mode.upper())
            except ValueError:
                mode = WorkforceSizer.select_mode(
                    task_class=classification.task_class.value,
                    risk_tier=classification.risk_tier.value,
                    pre_gate=pre_gate,
                    exec_gate=exec_gate,
                )
        else:
            mode = WorkforceSizer.select_mode(
                task_class=classification.task_class.value,
                risk_tier=classification.risk_tier.value,
                pre_gate=pre_gate,
                exec_gate=exec_gate,
            )

        # 7. Write Safety Policy
        is_read_only = classification.task_class == TaskClass.INVESTIGATION
        worker_assignments: Dict[str, List[str]] = {}
        if target_files:
            worker_assignments["primary-engineer"] = target_files
        write_policy, _ = WriteSafetyEvaluator.evaluate(
            target_files=target_files,
            worker_file_assignments=worker_assignments,
            is_read_only=is_read_only,
        )

        # 8. Adaptive Workforce Planning (Phase 84 12-input evaluation)
        planner_mode, cost_reasoning = AdaptiveWorkforcePlanner.plan(
            task_class=classification.task_class.value,
            risk_tier=classification.risk_tier.value,
            pre_planning_decision=pre_gate,
            execution_decision=exec_gate,
            write_policy=write_policy,
            subsystem_count=len(matched_subs),
            file_count=len(target_files),
            has_disjoint_boundaries=(write_policy in (WriteSafetyPolicy.SAFELY_PARALLELIZABLE, WriteSafetyPolicy.DISJOINT_BRANCHES)),
            remaining_mission_budget=20,
            historical_worker_success_rate=1.0,
            estimated_token_cost_budget=100000,
            active_workers_in_wave=0,
        )
        if not explicit_mode and not classification.explicit_delegation:
            mode = planner_mode

        # 9. Adaptive Waves Selection
        if mode == WorkforceMode.SOLO:
            initial_waves = [CanonicalWave.PLANNING.value, CanonicalWave.IMPLEMENTATION.value, CanonicalWave.VERIFICATION.value]
        else:
            initial_waves = [
                CanonicalWave.RECONNAISSANCE.value,
                CanonicalWave.PLANNING.value,
                CanonicalWave.IMPLEMENTATION.value,
                CanonicalWave.VERIFICATION.value,
                CanonicalWave.DELIVERY.value,
            ]

        coordination_lvl = determine_coordination_level(mode, wave_count=len(initial_waves))

        # 10. Tool & Verification Wiring
        primary_runner = self.config.test_runners[0] if self.config.test_runners else None
        test_cmd = " ".join(primary_runner.default_command) if primary_runner else "python tests/run_all.py"
        verification_method = f"Maker-Checker ({routing_pack.required_verifier}) + Stop Gate (exit code 0)"

        assigned_specialists: List[str] = []
        if routing_pack.selected_specialist:
            assigned_specialists.append(routing_pack.selected_specialist.get("name", "Specialist"))

        reasons = list(pre_gate.reasons)
        if exec_gate.reasons:
            reasons.extend(exec_gate.reasons)

        # Stage 2: CHECK STATE - Audit Drift & Project Proofs
        proof_store = ProjectProofStore(self.workspace_root)
        drift_findings = ProjectDriftEngine.evaluate_drift(
            workspace_root=self.workspace_root,
            proof_store=proof_store,
        )
        for df in drift_findings:
            if df.severity == DriftSeverity.CRITICAL_DRIFT:
                reasons.append(f"CRITICAL DRIFT: {df.description}")
            elif df.severity == DriftSeverity.SIGNIFICANT_DRIFT:
                reasons.append(f"Drift Alert: {df.description}")

        mission_id = f"mission-{abs(hash(task_query)) % 10000:04d}"

        # 11. Context Budget Governance & Freshness (Stage 7: BUILD CONTEXT)
        candidate_sources: List[ContextSourceItem] = []
        candidate_sources.append(
            ContextSourceItem.create(
                source_id="constitutional-invariants",
                source_type=ContextSourceType.CONSTITUTIONAL_POLICY,
                title="Constitutional Safety Invariants",
                content="Immutable core zones: framework/, .agents/hooks.json, antios.config.json. Shallow depth <= 2. Max active <= 10. Max launches <= 20.",
                is_safety_critical=True,
                provenance="AntiOS Constitution",
                epistemic_weight=1.0,
            )
        )
        for sub in matched_subs:
            candidate_sources.append(
                ContextSourceItem.create(
                    source_id=f"subsystem-{sub}",
                    source_type=ContextSourceType.COMPONENT_INTELLIGENCE,
                    title=f"Subsystem Intelligence: {sub}",
                    content=f"Subsystem '{sub}' relevant to query '{task_query}'. Matched components: {', '.join(matched_comps) if matched_comps else 'none'}.",
                    is_safety_critical=False,
                    provenance=f"framework/core/subsystems/{sub}",
                    epistemic_weight=0.9,
                    target_files=target_files,
                )
            )

        active_context_path = os.path.join(self.workspace_root, "docs", "ACTIVE_CONTEXT.md")
        if os.path.exists(active_context_path):
            try:
                with open(active_context_path, "r", encoding="utf-8") as f:
                    act_content = f.read()
                candidate_sources.append(
                    ContextSourceItem.create(
                        source_id="active-context-md",
                        source_type=ContextSourceType.ACTIVE_MISSION_STATE,
                        title="Active Context Ledger",
                        content=act_content,
                        is_safety_critical=True,
                        provenance="docs/ACTIVE_CONTEXT.md",
                        epistemic_weight=1.0,
                    )
                )
            except Exception:
                pass

        # Inject valid Durable Project Proofs (excluding invalidated/stale)
        proof_store.verify_physical_reality()
        for proof in proof_store.list_proofs():
            if proof.status in (ProofStatus.DURABLE, ProofStatus.VALIDATED):
                candidate_sources.append(
                    ContextSourceItem.create(
                        source_id=f"proof-{proof.proof_id}",
                        source_type=ContextSourceType.COMPONENT_INTELLIGENCE,
                        title=f"Durable Proof: {proof.subject.value}",
                        content=f"{proof.statement} [Proof: {proof.proof_id}]",
                        is_safety_critical=(proof.subject == ProofSubject.VERIFIED_INVARIANT),
                        provenance=f"origin_mission:{proof.origin_mission_id}",
                        epistemic_weight=1.0,
                        target_files=proof.tracked_paths,
                    )
                )

        budget_governor = ContextBudgetGovernor()
        context_result = budget_governor.evaluate(
            task_intent=task_query,
            sources=candidate_sources,
            active_files=target_files,
            risk_tier=classification.risk_tier.value,
        )

        persistence_mode = MissionStateStore.evaluate_persistence_threshold(
            task_intent=task_query,
            file_count=len(target_files),
            wave_count=len(initial_waves),
            risk_tier=classification.risk_tier.value,
            workforce_mode=mode.value,
        )

        return MissionPlan(
            mission_id=mission_id,
            task_intent=task_query,
            task_class=classification.task_class.value,
            risk_tier=classification.risk_tier.value,
            matched_subsystems=matched_subs,
            matched_components=matched_comps,
            workforce_mode=mode,
            coordination_level=coordination_lvl,
            write_policy=write_policy,
            pre_planning_gate=pre_gate,
            execution_gate=exec_gate,
            primary_role=routing_pack.primary_role.get("name", "AntiOS Engineer"),
            assigned_specialists=assigned_specialists,
            configured_test_command=test_cmd,
            verification_method=verification_method,
            capability_pack=cap_pack.to_dict() if hasattr(cap_pack, "to_dict") else {},
            agent_routing=routing_pack.to_dict(),
            initial_waves=initial_waves,
            reasons=reasons,
            cost_reasoning=cost_reasoning.to_dict(),
            workforce_planner_decision={
                "mode": planner_mode.value,
                "cost_reasoning": cost_reasoning.to_dict(),
            },
            context_budget_card=asdict(context_result.card),
            loaded_context=context_result.loaded_context,
            mission_state_mode=persistence_mode.value,
        )

    def dispatch_task(
        self,
        task_query: str,
        target_files: Optional[List[str]] = None,
        mission_id: Optional[str] = None,
        **kwargs: Any,
    ) -> MissionPlan:
        """Convenience dispatcher supporting explicit mission_id and forwarding kwargs."""
        plan = self.dispatch(task_query=task_query, target_files=target_files, **kwargs)
        if mission_id:
            plan.mission_id = mission_id
        return plan

    def verify_mission(
        self,
        plan: MissionPlan,
        evidence_package: EvidencePackage,
        maker_identity: Optional[str] = None,
        checker_identity: Optional[str] = None,
        is_independent_checker: bool = True,
    ) -> MissionEvaluationResult:
        """Stage 9 (VERIFY): Produces authoritative Mission Evaluation + Evidence Package."""
        maker_id = maker_identity or plan.primary_role
        eval_result = MissionEvaluationEngine.evaluate(
            evidence_package=evidence_package,
            risk_tier=plan.risk_tier,
            maker_identity=maker_id,
            checker_identity=checker_identity,
            is_independent_checker=is_independent_checker,
        )
        evidence_package.final_verdict = eval_result.overall_status.value
        return eval_result

    def remember_mission(
        self,
        plan: MissionPlan,
        evaluation_result: MissionEvaluationResult,
        evidence_package: EvidencePackage,
        lessons: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Stage 10 (REMEMBER): Stores bounded references to validated evidence, durable lessons,
        and distills verified knowledge into Durable Project Proofs.
        
        Strictly preserves the invariant: Never duplicate entire mission history into project learning.
        """
        lessons = lessons or []
        epistemic = (
            EpistemicSource.OBSERVED_FACT
            if evaluation_result.overall_status == EvaluationStatus.PASS
            else EpistemicSource.AGENT_INTERPRETATION
        )

        obs_refs = []
        for i, lesson in enumerate(lessons[:5]):  # Bounded to at most 5 lessons
            obs = Observation(
                observation_id=f"obs-{plan.mission_id}-{i+1}",
                timestamp=evaluation_result.timestamp,
                mission_id=plan.mission_id,
                source=f"mission:{plan.mission_id}",
                epistemic_source=epistemic,
                observation_type=ObservationType.TASK_OUTCOME,
                title=f"Lesson: {lesson[:100]}",
                content=lesson[:500],
                affected_subsystem=plan.matched_subsystems[0] if plan.matched_subsystems else "core",
                related_files=plan.matched_components[:5],
                evidence_references={
                    "evidence_hash": evaluation_result.evidence_hash,
                    "package_id": evidence_package.package_id,
                    "verdict": evaluation_result.overall_status.value,
                },
                confidence=1.0 if evaluation_result.overall_status == EvaluationStatus.PASS else 0.5,
            )
            obs_refs.append(obs.observation_id)

        # Distill verified evidence into durable project proofs
        proof_refs = []
        if evaluation_result.overall_status == EvaluationStatus.PASS:
            proof_store = ProjectProofStore(self.workspace_root)
            for item in evidence_package.evidence_items:
                if (
                    item.state == EvidenceState.VERIFIED
                    and item.epistemic_category == EpistemicCategory.EVIDENCE
                ):
                    try:
                        candidate = EvidenceDistillationEngine.distill_proof(
                            evidence_item=item,
                            subject=(
                                ProofSubject.VERIFIED_FILE_LOCATION
                                if item.artifact_hashes
                                else ProofSubject.VERIFIED_COMMAND
                            ),
                            statement=f"Verified execution: {item.intent[:200] if item.intent else 'operation'}",
                            project_fingerprint=evaluation_result.evidence_hash or "clean-fingerprint",
                            workspace_root=self.workspace_root,
                            tracked_paths=list(item.artifact_hashes.keys()) if item.artifact_hashes else [],
                        )
                        durable = EvidenceDistillationEngine.promote_proof(
                            proof=candidate,
                            evaluation_result=evaluation_result,
                            current_fingerprint=evaluation_result.evidence_hash or "clean-fingerprint",
                            recurrence_count=2,
                        )
                        proof_store.add_or_update_proof(durable)
                        proof_refs.append(durable.proof_id)
                    except Exception:
                        pass

        return {
            "mission_id": plan.mission_id,
            "overall_status": evaluation_result.overall_status.value,
            "evidence_hash": evaluation_result.evidence_hash,
            "lessons_recorded": len(obs_refs),
            "observation_refs": obs_refs,
            "proofs_distilled": len(proof_refs),
            "proof_refs": proof_refs,
            "stored_bounded_references": True,
        }



