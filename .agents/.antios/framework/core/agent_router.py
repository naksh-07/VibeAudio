"""AntiOS Deterministic Agent Router.

Connects CapabilityPack to the Agent Topology Layer.
Evaluates delegation signals:
- Subsystem specialization
- Task complexity & risk tier
- Capability requirements & boundary constraints
- Cross-subsystem touch containment (prevention of swarms)
- Explicit project adapter policy

Answers:
"Who should perform this work, what capabilities may they use, what are their
boundaries, and when is delegation justified?"

Default is strictly NO_DELEGATION (SOLO) unless specialization provides measurable value.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Set, Tuple

from framework.core.agent_role import (
    AgentRole,
    AgentRoleType,
    AgentCapabilityBoundary,
    DelegationDecisionType,
    EscalationPolicyType,
    AgentHandoffContract,
)
from framework.core.agent_routing_pack import AgentRoutingPack
from framework.core.agent_topology import (
    AgentTopologyRegistry,
    build_default_agent_topology,
)
from framework.core.capability_pack import CapabilityPack
from framework.core.config import AntiOSConfig
from framework.core.lifecycle import TaskClass


class AgentRouter:
    """Deterministic routing engine assigning agent roles and delegation policies."""

    def __init__(
        self,
        topology_registry: Optional[AgentTopologyRegistry] = None,
        config: Optional[AntiOSConfig] = None,
        project_name: str = "AntiOS-Core",
    ):
        self.config = config
        self.project_name = project_name
        self.registry = topology_registry or build_default_agent_topology(config)

    def route_task(
        self,
        capability_pack: CapabilityPack,
        target_files: Optional[List[str]] = None,
        explicit_policy: Optional[Dict[str, Any]] = None,
    ) -> AgentRoutingPack:
        """Resolves agent role, delegation decision, boundaries, and handoffs from a CapabilityPack."""
        task_intent = capability_pack.task_intent
        task_class = capability_pack.task_class
        risk_tier = capability_pack.risk_tier
        matched_subsystems = list(capability_pack.matched_subsystems)
        target_files = target_files or []

        primary_role = self.registry.get_primary_agent()

        # Check adapter-level delegation policy override
        adapter_allows_delegation = True
        if self.config and hasattr(self.config, "agent_topology") and isinstance(self.config.agent_topology, dict):
            adapter_allows_delegation = self.config.agent_topology.get("allow_delegation", True)

        why_not_others: Dict[str, str] = {}
        candidate_specialists: List[AgentRole] = []

        # Find candidate specialists
        all_specialists = self.registry.find_by_type(AgentRoleType.SPECIALIST, enabled_only=False)
        for spec in all_specialists:
            if not spec.enabled:
                why_not_others[spec.name] = "Specialist is disabled in registry"
                continue

            # Check task class applicability
            if not spec.is_applicable_to_task(task_class):
                why_not_others[spec.name] = f"Task class '{task_class}' does not match specialist domain"
                continue

            # Check subsystem applicability
            sub_matches = any(spec.is_applicable_to_subsystem(sub) for sub in matched_subsystems) if matched_subsystems else spec.is_applicable_to_subsystem("*")
            if not sub_matches:
                why_not_others[spec.name] = f"Subsystems {matched_subsystems} outside specialist domain"
                continue

            candidate_specialists.append(spec)

        # ---------------------------------------------------------------------
        # Delegation Decision Logic (Deterministic Signal Matrix)
        # ---------------------------------------------------------------------
        delegation_decision = DelegationDecisionType.NO_DELEGATION
        selected_specialist: Optional[AgentRole] = None
        delegation_reason = "Default solo execution by Primary Agent"
        why_selected = f"Primary Agent '{primary_role.name}' handles task directly"

        # Signal 1: Adapter policy blocks delegation
        if not adapter_allows_delegation:
            delegation_decision = DelegationDecisionType.NO_DELEGATION
            delegation_reason = "Adapter policy explicitly disables specialist delegation (allow_delegation: false)"
            why_selected = "Adapter policy mandates solo primary execution"
            for spec in candidate_specialists:
                why_not_others[spec.name] = "Delegation disabled by adapter policy"
            candidate_specialists = []

        # Signal 2: Documentation or Read-Only trivial tasks -> NO_DELEGATION
        elif task_class == TaskClass.DOCUMENTATION.value:
            delegation_decision = DelegationDecisionType.NO_DELEGATION
            delegation_reason = "Documentation tasks are executed directly by Primary Agent with solo verifier"
            why_selected = "Primary Agent owns project documentation; delegation provides no measurable benefit"
            for spec in candidate_specialists:
                why_not_others[spec.name] = "Specialist delegation adds overhead for documentation tasks"
            candidate_specialists = []

        # Signal 3: Cross-subsystem features touching 3+ subsystems -> NO_DELEGATION (Prevent swarm!)
        elif len(matched_subsystems) >= 3 and task_class == TaskClass.FEATURE.value:
            delegation_decision = DelegationDecisionType.NO_DELEGATION
            delegation_reason = f"Cross-subsystem scope ({len(matched_subsystems)} subsystems) requires unified Primary coordination to prevent multi-agent swarm"
            why_selected = "Primary Agent retains unified ownership across multi-subsystem feature"
            for spec in candidate_specialists:
                why_not_others[spec.name] = "Cross-subsystem feature requires unified ownership; multi-agent swarm prohibited"
            candidate_specialists = []

        # Signal 4: Core Governance / Security Modification
        elif any(sub in ("core", "governance", "security", "hooks") for sub in matched_subsystems) or risk_tier == "CRITICAL":
            sec_spec = self.registry.get("role:security-reviewer")
            if sec_spec and sec_spec.enabled:
                selected_specialist = sec_spec
                delegation_decision = DelegationDecisionType.DELEGATE_SPECIALIST
                delegation_reason = "Core governance or security-sensitive paths mandate dedicated security review"
                why_selected = f"Specialist '{sec_spec.name}' selected for governance and security compliance"
            else:
                delegation_decision = DelegationDecisionType.NO_DELEGATION
                delegation_reason = "Security reviewer specialist unavailable; Primary retains execution under critical risk policy"
                why_selected = "Primary executes with mandatory independent Checker"

        # Signal 5: Investigation task
        elif task_class == TaskClass.INVESTIGATION.value:
            inv_spec = self.registry.get("role:investigation-specialist")
            if inv_spec and inv_spec.enabled:
                selected_specialist = inv_spec
                delegation_decision = DelegationDecisionType.DELEGATE_INVESTIGATION
                delegation_reason = "Investigation task warrants bounded read-only reconnaissance specialist"
                why_selected = f"Specialist '{inv_spec.name}' selected for evidence acquisition and exploration"
            else:
                delegation_decision = DelegationDecisionType.NO_DELEGATION
                delegation_reason = "Investigation specialist not configured; Primary investigates directly"
                why_selected = "Primary handles investigation directly"

        # Signal 6: Bug task -> Root Cause Debugger
        elif task_class == TaskClass.BUG.value:
            dbg_spec = self.registry.get("role:root-cause-debugger")
            if dbg_spec and dbg_spec.enabled:
                selected_specialist = dbg_spec
                delegation_decision = DelegationDecisionType.DELEGATE_SPECIALIST
                delegation_reason = "Bug task warrants systematic root-cause isolation by debugger specialist"
                why_selected = f"Specialist '{dbg_spec.name}' selected for deterministic reproduction and diagnosis"
            else:
                delegation_decision = DelegationDecisionType.NO_DELEGATION
                delegation_reason = "Debugger specialist not configured; Primary fixes bug directly"
                why_selected = "Primary handles bug directly"

        # Signal 7: Domain-specific specialist (e.g. UI / Database from adapter or registry)
        elif candidate_specialists:
            # Pick highest confidence specialist matching specific subsystem
            specialist_candidates = [
                s for s in candidate_specialists
                if not any(sub == "*" for sub in s.applies_to_subsystems)
            ]
            if specialist_candidates:
                chosen = specialist_candidates[0]
                # Check capability boundary compatibility
                is_compatible, check_msg = self._check_boundary_compatibility(chosen, capability_pack)
                if is_compatible:
                    selected_specialist = chosen
                    delegation_decision = DelegationDecisionType.DELEGATE_SPECIALIST
                    delegation_reason = f"Subsystem '{matched_subsystems}' has dedicated domain specialist '{chosen.name}'"
                    why_selected = f"Specialist '{chosen.name}' matches subsystem '{matched_subsystems[0]}' and task '{task_class}'"
                else:
                    delegation_decision = DelegationDecisionType.NO_DELEGATION
                    delegation_reason = f"Specialist '{chosen.name}' scope mismatch: {check_msg}"
                    why_selected = "Primary handles task directly due to specialist scope mismatch"
                    why_not_others[chosen.name] = f"Scope mismatch: {check_msg}"
            else:
                # Generic specialists do not justify delegation over Primary Agent
                delegation_decision = DelegationDecisionType.NO_DELEGATION
                delegation_reason = "No specialized domain specialist found; generic primary execution is more efficient"
                why_selected = "Primary handles task directly"

        # Signal 8: Unknown domain fallback
        if capability_pack.epistemic_state == "UNKNOWN" or not matched_subsystems:
            delegation_decision = DelegationDecisionType.NO_DELEGATION
            delegation_reason = "Unknown domain or unmapped subsystem; fallback to Primary Agent to prevent ungrounded delegation"
            why_selected = "Primary Agent executes unknown tasks using safe baseline discovery"
            selected_specialist = None

        # Clean up why_not_others to exclude selected specialist
        if selected_specialist:
            why_not_others.pop(selected_specialist.name, None)

        # ---------------------------------------------------------------------
        # Capability Boundary Synthesis
        # ---------------------------------------------------------------------
        active_role = selected_specialist if selected_specialist else primary_role
        boundary_dict = active_role.boundary.to_dict()

        # ---------------------------------------------------------------------
        # Required Verifier & Escalation Policy
        # ---------------------------------------------------------------------
        required_verifier = active_role.required_verifier
        if risk_tier == "CRITICAL":
            required_verifier = "verifier:independent-auditor"
        elif risk_tier == "HIGH" or task_class in (TaskClass.FEATURE.value, TaskClass.BUG.value, TaskClass.REFACTOR.value):
            required_verifier = "verifier:maker-checker"
        elif task_class == TaskClass.DOCUMENTATION.value:
            required_verifier = "verifier:solo"

        escalation_policy = active_role.escalation_policy.value

        # ---------------------------------------------------------------------
        # Handoff Contract Construction (if delegated)
        # ---------------------------------------------------------------------
        handoff_contract: Optional[Dict[str, Any]] = None
        if delegation_decision != DelegationDecisionType.NO_DELEGATION and selected_specialist:
            contract_obj = AgentHandoffContract(
                contract_id=f"contract-{abs(hash(task_intent + selected_specialist.role_id)) % 100000:05d}",
                task=task_intent,
                target_files=target_files,
                target_subsystems=matched_subsystems,
                allowed_capabilities=active_role.boundary.allowed_capabilities,
                forbidden_capabilities=active_role.boundary.forbidden_capabilities,
                constraints=[
                    "Preserve Shallow Depth Law (depth <= 2; do NOT spawn child subagents)",
                    "Adhere strictly to assigned capability boundary",
                    f"Required verification ratchet: {required_verifier}",
                ],
                expected_output=f"Bounded deliverable for {task_intent} with verification evidence",
                verification_requirement=required_verifier,
                delegated_role_id=selected_specialist.role_id,
            )
            handoff_contract = contract_obj.to_dict()

        routing_id = f"routing-{abs(hash(task_intent + active_role.role_id)) % 100000:05d}"

        return AgentRoutingPack(
            routing_id=routing_id,
            task_intent=task_intent,
            task_class=task_class,
            risk_tier=risk_tier,
            matched_subsystems=matched_subsystems,
            primary_role=primary_role.to_dict(),
            delegation_decision=delegation_decision.value,
            delegation_reason=delegation_reason,
            selected_specialist=selected_specialist.to_dict() if selected_specialist else None,
            why_selected=why_selected,
            why_not_others=why_not_others,
            capability_boundary=boundary_dict,
            required_verifier=required_verifier,
            escalation_policy=escalation_policy,
            handoff_contract=handoff_contract,
            confidence=capability_pack.confidence,
            evidence=f"Resolved via AgentRouter for task '{task_intent}'",
            epistemic_state=capability_pack.epistemic_state,
        )

    def _check_boundary_compatibility(
        self,
        specialist: AgentRole,
        pack: CapabilityPack,
    ) -> Tuple[bool, str]:
        """Validates that the specialist's capability boundary does not forbid required pack capabilities."""
        # Check required skills from pack
        for skill_dict in pack.skills:
            skill_id = skill_dict.get("capability_id", "")
            if not specialist.boundary.is_capability_allowed(skill_id):
                return False, f"Requires capability '{skill_id}' which is forbidden or unpermitted for '{specialist.name}'"

        return True, "Specialist boundary is compatible with required capabilities"
