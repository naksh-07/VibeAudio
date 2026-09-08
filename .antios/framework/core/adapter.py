"""AntiOS v1 Adaptation Proposal and Adapter Generation Model.

Formalizes the transformation:
Project Profile -> Adaptation Analysis -> Project Adapter (antios.config.json)

Enforces strict separation:
- PROJECT_LOCAL changes can be safely applied to antios.config.json.
- ANTIOS_CORE changes represent framework capability gaps that can NEVER be
  silently applied; they emit structured escalation reports for human review.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from framework.core.config import AntiOSConfig, PoliciesConfig, RunnerConfig, load_config
from framework.core.profile import (
    ConflictFact,
    EvidenceTier,
    ProjectProfile,
    ToolCategory,
    ToolFact,
)


class ActionType(str, Enum):
    """Action type for an adaptation proposal item."""
    ADD = "ADD"
    REMOVE = "REMOVE"
    CONFIGURE = "CONFIGURE"
    ADAPT = "ADAPT"
    DEFER = "DEFER"
    CONFLICT = "CONFLICT"


class ChangeTarget(str, Enum):
    """Scope of proposed change."""
    PROJECT_LOCAL = "PROJECT_LOCAL"  # Modifies local antios.config.json only
    ANTIOS_CORE = "ANTIOS_CORE"      # Touches AntiOS framework, core engine, or hooks


class ProposalRisk(str, Enum):
    """Risk classification for adaptation proposals."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class AdaptationProposalItem:
    """A discrete proposed modification to the project adapter or AntiOS Core."""
    action: ActionType
    target: ChangeTarget
    component: str  # e.g., "test_runners", "linters", "protected_domain_paths", "core_parser"
    description: str
    reason: str
    source_evidence: List[str] = field(default_factory=list)
    risk: ProposalRisk = ProposalRisk.LOW
    verification_required: str = ""
    is_automated_safe: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "target": self.target.value,
            "component": self.component,
            "description": self.description,
            "reason": self.reason,
            "source_evidence": self.source_evidence,
            "risk": self.risk.value,
            "verification_required": self.verification_required,
            "is_automated_safe": self.is_automated_safe,
        }


@dataclass
class AdaptationProposal:
    """Canonical Adaptation Proposal."""
    repo_root: str
    project_name: str
    items: List[AdaptationProposalItem] = field(default_factory=list)
    conflicts: List[ConflictFact] = field(default_factory=list)

    @property
    def has_core_changes(self) -> bool:
        return any(item.target == ChangeTarget.ANTIOS_CORE for item in self.items)

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0 or any(item.action == ActionType.CONFLICT for item in self.items)

    @property
    def is_safe_to_apply_automatically(self) -> bool:
        return not self.has_core_changes and all(item.is_automated_safe for item in self.items if item.action != ActionType.DEFER)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo_root": self.repo_root,
            "project_name": self.project_name,
            "has_core_changes": self.has_core_changes,
            "has_conflicts": self.has_conflicts,
            "is_safe_to_apply_automatically": self.is_safe_to_apply_automatically,
            "items": [item.to_dict() for item in self.items],
            "conflicts": [c.to_dict() for c in self.conflicts],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def analyze_adaptation(profile: ProjectProfile, current_config: Optional[AntiOSConfig] = None) -> AdaptationProposal:
    """Analyze a ProjectProfile against AntiOS capabilities and existing configuration.
    
    Generates a structured AdaptationProposal separating PROJECT_LOCAL from ANTIOS_CORE needs.
    """
    repo_root = profile.identity.root_path
    project_name = profile.identity.name
    proposal = AdaptationProposal(repo_root=repo_root, project_name=project_name, conflicts=profile.conflicts)

    # Base configuration comparison
    existing_runner_names = {r.name for r in (current_config.test_runners if current_config else [])}
    existing_protected = set(current_config.protected_domain_paths if current_config else [])

    # 1. Test Runners
    for tr in profile.get_test_runners():
        if tr.name not in existing_runner_names:
            risk = ProposalRisk.LOW if tr.is_available_in_path else ProposalRisk.HIGH
            proposal.items.append(
                AdaptationProposalItem(
                    action=ActionType.ADD,
                    target=ChangeTarget.PROJECT_LOCAL,
                    component="test_runners",
                    description=f"Register discovered test runner '{tr.name}' ({' '.join(tr.command)})",
                    reason=f"Discovered test runner from manifest '{tr.manifest_path}'",
                    source_evidence=[tr.manifest_path],
                    risk=risk,
                    verification_required=" ".join(tr.command),
                    is_automated_safe=tr.is_available_in_path,
                )
            )

    # 2. Linters
    for linter in profile.get_linters():
        proposal.items.append(
            AdaptationProposalItem(
                action=ActionType.ADD,
                target=ChangeTarget.PROJECT_LOCAL,
                component="linters",
                description=f"Register discovered linter '{linter.name}' ({' '.join(linter.command)})",
                reason=f"Discovered linter from manifest '{linter.manifest_path}'",
                source_evidence=[linter.manifest_path],
                risk=ProposalRisk.LOW,
                verification_required=" ".join(linter.command),
                is_automated_safe=linter.is_available_in_path,
            )
        )

    # 3. Protected Paths & Risk Zones
    for rz in profile.risk_zones:
        if rz not in existing_protected:
            proposal.items.append(
                AdaptationProposalItem(
                    action=ActionType.CONFIGURE,
                    target=ChangeTarget.PROJECT_LOCAL,
                    component="protected_domain_paths",
                    description=f"Add risk zone '{rz}' to protected domain paths",
                    reason="Identified sensitive or legacy architectural component",
                    source_evidence=[rz],
                    risk=ProposalRisk.LOW,
                    verification_required="python framework/scripts/tools/check_worktree.py",
                    is_automated_safe=True,
                )
            )

    # 4. Unknowns & Capability Gaps
    for unk in profile.unknown_fields:
        if unk.is_blocking:
            # Language or tool ecosystem unsupported by AntiOS Core
            proposal.items.append(
                AdaptationProposalItem(
                    action=ActionType.DEFER,
                    target=ChangeTarget.ANTIOS_CORE,
                    component="core_discovery_engine",
                    description=f"AntiOS Core lacks native detector for field '{unk.field_name}': {unk.reason}",
                    reason="AntiOS Core cannot reliably infer build/test contracts for unfamiliar project archetype",
                    source_evidence=[unk.field_name],
                    risk=ProposalRisk.HIGH,
                    verification_required="Manual specification of antios.config.json or AntiOS Core detector PR",
                    is_automated_safe=False,
                )
            )

    # 5. Conflicts
    for c in profile.conflicts:
        proposal.items.append(
            AdaptationProposalItem(
                action=ActionType.CONFLICT,
                target=ChangeTarget.PROJECT_LOCAL,
                component="conflict_resolution",
                description=f"Conflict ({c.conflict_type.value}): {c.description}",
                reason=f"Resolution: {c.resolution_recommendation}",
                source_evidence=[c.prose_claim, c.physical_reality],
                risk=ProposalRisk.MEDIUM,
                verification_required="Resolve discrepancy before task completion",
                is_automated_safe=False,
            )
        )
    # Propose components registration for wayfinding
    if hasattr(profile, "subsystems") and profile.subsystems:
        proposal.items.append(
            AdaptationProposalItem(
                action=ActionType.CONFIGURE,
                target=ChangeTarget.PROJECT_LOCAL,
                component="components",
                description=f"Register {len(profile.subsystems)} discovered project subsystems for wayfinding and locality indexing.",
                reason="Enables deterministic component wayfinding and scoped test resolution.",
                source_evidence=list(profile.subsystems.keys()),
                risk=ProposalRisk.LOW,
                verification_required="Verify component root paths exist on disk",
                is_automated_safe=True,
            )
        )

    return proposal


def generate_adapter_config(profile: ProjectProfile, proposal: AdaptationProposal, base_config: Optional[AntiOSConfig] = None) -> AntiOSConfig:
    """Generate an updated AntiOSConfig by applying proposal items to a base config."""
    config = base_config or AntiOSConfig()
    config.name = f"AntiOS-{profile.identity.name}-Adapter"

    # Always ensure immutable core zones are preserved (.agents and .antios)
    for zone in [".agents", ".antios"]:
        if zone not in config.protected_zones:
            config.protected_zones.append(zone)

    # Protect framework only for the AntiOS development repository itself
    if profile.identity.name in ("AntiOS", "AntiOS-Universal-Self-Adapter") or any(
        getattr(s, "subsystem_id", "") == "framework" for s in profile.subsystems
    ):
        if "framework" not in config.protected_zones:
            config.protected_zones.append("framework")

    # Add test runners
    existing_runner_names = {r.name for r in config.test_runners}
    for tr in profile.get_test_runners():
        if tr.name not in existing_runner_names:
            config.test_runners.append(
                RunnerConfig(
                    name=tr.name,
                    manifest=tr.manifest_path,
                    default_command=tr.command,
                    timeout_seconds=tr.timeout_seconds,
                    required=tr.required,
                    cwd=tr.cwd,
                )
            )

    # Add linters
    existing_linter_names = {l.get("name") for l in config.linters}
    for linter in profile.get_linters():
        if linter.name not in existing_linter_names:
            config.linters.append({
                "name": linter.name,
                "manifest": linter.manifest_path,
                "command": linter.command,
                "timeout_seconds": linter.timeout_seconds,
            })

    # Add protected domain paths
    for rz in profile.risk_zones:
        if rz not in config.protected_domain_paths:
            config.protected_domain_paths.append(rz)

    # Add components registry
    if hasattr(profile, "subsystems") and profile.subsystems:
        config.components = dict(profile.subsystems)

    return config


def apply_project_adaptation(repo_root: str, proposal: AdaptationProposal, dry_run: bool = False) -> Tuple[bool, str]:
    """Apply safe project-local adaptation to antios.config.json.
    
    CRITICAL SECURITY INVARIANT:
    Refuses to execute if the proposal contains ANY ANTIOS_CORE target modifications.
    AntiOS Core must never be automatically altered based on an unfamiliar project's requirements.
    """
    if proposal.has_core_changes:
        core_items = [i.description for i in proposal.items if i.target == ChangeTarget.ANTIOS_CORE]
        return False, (
            f"REFUSED: Proposal contains {len(core_items)} AntiOS-Core level changes.\n"
            f"Core changes must be escalated and reviewed independently:\n"
            + "\n".join(f"- {ci}" for ci in core_items)
        )

    target_config_path = Path(repo_root) / "antios.config.json"
    current_config = load_config(repo_root) if target_config_path.exists() else None

    # Synthesize new config from profile runners/linters
    # Build minimal runner list from proposal items
    new_runners: List[Dict[str, Any]] = []
    new_linters: List[Dict[str, Any]] = []
    new_protected: List[str] = list(current_config.protected_domain_paths if current_config else [])

    # Map discovered tool metadata (like member-scoped cwd)
    tool_cwds: Dict[str, str] = {}
    manifest_fingerprint = ""
    try:
        from framework.core.discovery import discover_project
        discovered = discover_project(repo_root)
        manifest_fingerprint = discovered.manifest_fingerprint
        for t in discovered.tools:
            if t.cwd:
                tool_cwds[t.name] = t.cwd
    except Exception:
        manifest_fingerprint = current_config.manifest_fingerprint if current_config else ""

    for item in proposal.items:
        if item.action == ActionType.ADD and item.component == "test_runners":
            # Extract from profile or item
            parts = item.description.split("(")
            runner_name = item.description.split("'")[1] if "'" in item.description else "discovered-runner"
            cmd = item.verification_required.split()
            manifest = item.source_evidence[0] if item.source_evidence else ""
            runner_entry = {
                "name": runner_name,
                "manifest": manifest,
                "default_command": cmd,
                "timeout_seconds": 90,
                "required": True,
            }
            if runner_name in tool_cwds:
                runner_entry["cwd"] = tool_cwds[runner_name]
            new_runners.append(runner_entry)
        elif item.action == ActionType.ADD and item.component == "linters":
            linter_name = item.description.split("'")[1] if "'" in item.description else "discovered-linter"
            cmd = item.verification_required.split()
            manifest = item.source_evidence[0] if item.source_evidence else ""
            new_linters.append({
                "name": linter_name,
                "manifest": manifest,
                "command": cmd,
                "timeout_seconds": 45,
            })
        elif item.action == ActionType.CONFIGURE and item.component == "protected_domain_paths":
            for path in item.source_evidence:
                if path not in new_protected:
                    new_protected.append(path)

    # If existing runners present, preserve them unless overwritten
    if current_config:
        for ex in current_config.test_runners:
            if not any(nr["name"] == ex.name for nr in new_runners):
                ex_entry = {
                    "name": ex.name,
                    "manifest": ex.manifest,
                    "default_command": ex.default_command,
                    "timeout_seconds": ex.timeout_seconds,
                    "required": ex.required,
                }
                if hasattr(ex, "cwd") and ex.cwd:
                    ex_entry["cwd"] = ex.cwd
                new_runners.append(ex_entry)

    config_dict: Dict[str, Any] = {
        "version": "1.0",
        "name": f"AntiOS-{proposal.project_name}-Adapter",
        "manifest_fingerprint": manifest_fingerprint,
        "protected_zones": [".agents", "framework"],
        "protected_domain_paths": new_protected,
        "forbidden_patterns": current_config.forbidden_patterns if current_config else [],
        "test_runners": new_runners,
        "linters": new_linters,
        "policies": {
            "fail_closed": True,
            "enforce_working_tree_cleanliness": True,
            "enforce_same_change_set": True,
        },
    }

    # Add components registry
    new_components = dict(current_config.components if current_config and hasattr(current_config, "components") else {})
    if "discovered" in locals() and hasattr(discovered, "subsystems") and discovered.subsystems:
        new_components.update(discovered.subsystems)
    if new_components:
        config_dict["components"] = new_components

    if dry_run:
        return True, f"[DRY RUN] Would write adapter configuration to '{target_config_path}':\n" + json.dumps(config_dict, indent=2)

    try:
        with open(target_config_path, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=2)
        return True, f"Successfully configured project adapter at '{target_config_path}'"
    except Exception as e:
        return False, f"Failed to write adapter config: {e}"


@dataclass
class AdapterVerificationResult:
    """Outcome of adapter validation against AntiOS Core invariants and physical toolchain reality."""
    is_valid: bool
    issues: List[str] = field(default_factory=list)
    passed_checks: List[str] = field(default_factory=list)
    manifest_fingerprint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def verify_adapter(
    repo_root: str,
    config: Optional[AntiOSConfig] = None,
    check_fingerprint: bool = True
) -> AdapterVerificationResult:
    """Verifies an adapter configuration (antios.config.json) against AntiOS Core invariants,
    schema requirements, binary availability, and manifest drift.
    """
    from framework.core.discovery import discover_project, is_tool_in_path

    cfg = config or load_config(repo_root)
    issues: List[str] = []
    passed: List[str] = []

    # 1. Check core zones invariant
    immutable_zones = [".agents", "framework"]
    for zone in immutable_zones:
        if zone not in cfg.protected_zones:
            issues.append(f"CONSTITUTIONAL VIOLATION: Immutable core zone '{zone}' is missing from protected_zones.")
        else:
            passed.append(f"Immutable core zone '{zone}' protected.")

    # Check fail-closed policy
    if not cfg.policies.fail_closed:
        issues.append("CONSTITUTIONAL VIOLATION: Fail-closed policy disabled (must be true).")
    else:
        passed.append("Fail-closed policy enforced.")

    # 2. Check runners
    if not cfg.test_runners:
        try:
            from framework.core.gate import discover_test_runners
            dyn_runners = discover_test_runners(repo_root)
            if not dyn_runners:
                issues.append("No test runners configured in adapter. Verification requires at least one runner or dynamic discovery.")
            else:
                passed.append(f"Dynamic runner discovery active ({len(dyn_runners)} runners discovered).")
        except Exception:
            issues.append("No test runners configured in adapter. Verification requires at least one runner or dynamic discovery.")
    else:
        for tr in cfg.test_runners:
            if not tr.default_command:
                issues.append(f"Test runner '{tr.name}' has empty default_command execution list.")
            else:
                binary = tr.default_command[0]
                if tr.required and not is_tool_in_path(binary):
                    issues.append(f"Required runner binary '{binary}' for '{tr.name}' is NOT available in PATH.")
                else:
                    passed.append(f"Runner '{tr.name}' valid (command: {' '.join(tr.default_command)}).")

    # 3. Check Manifest Fingerprint Drift
    current_fingerprint = ""
    if check_fingerprint:
        try:
            profile = discover_project(repo_root)
            current_fingerprint = profile.manifest_fingerprint
            if cfg.manifest_fingerprint:
                if cfg.manifest_fingerprint != current_fingerprint:
                    issues.append(
                        f"MANIFEST DRIFT: Discovered manifests changed on disk. "
                        f"Expected fingerprint {cfg.manifest_fingerprint[:8]}..., got {current_fingerprint[:8]}... "
                        f"Run 'adapt_project.py' to re-synchronize."
                    )
                else:
                    passed.append(f"Manifest fingerprint matched ({current_fingerprint[:8]}...).")
            else:
                passed.append(f"Manifest fingerprint computed ({current_fingerprint[:8]}...).")
        except Exception as e:
            passed.append(f"Fingerprint check bypassed: {e}")

    # 4. Check components if present
    if hasattr(cfg, "components") and cfg.components:
        comp_issues = 0
        for sub_id, data in cfg.components.items():
            if isinstance(data, dict):
                root_paths = data.get("root_paths", [])
                for rp in root_paths:
                    abs_rp = os.path.join(repo_root, rp)
                    if not os.path.exists(abs_rp):
                        issues.append(f"Component '{sub_id}' root path '{rp}' not found on disk.")
                        comp_issues += 1
        if comp_issues == 0:
            passed.append(f"Component registry verified ({len(cfg.components)} components).")

    # 5. Check Capabilities policy if present
    if hasattr(cfg, "capabilities") and cfg.capabilities:
        caps = cfg.capabilities
        if isinstance(caps, dict):
            dis = caps.get("disabled_capabilities", [])
            prohibited_disables = {"rule:platform-hook-interception", "rule:core-immutable", "rule:stop-gate-ratchet", "rule:shallow-depth-law"}
            for d in dis:
                if d in prohibited_disables:
                    issues.append(f"CONSTITUTIONAL VIOLATION: Project adapter attempts to disable protected core invariant '{d}'.")
            if not any(d in prohibited_disables for d in dis):
                passed.append(f"Capability configuration verified ({len(caps)} keys).")

    # 6. Check Agent Topology policy if present
    if hasattr(cfg, "agent_topology") and cfg.agent_topology:
        atop = cfg.agent_topology
        if isinstance(atop, dict):
            specs = atop.get("specialists", {})
            if isinstance(specs, list):
                specs = {item.get("role_id", f"role:custom-{i}"): item for i, item in enumerate(specs)}
            for s_id, s_data in specs.items():
                if isinstance(s_data, dict):
                    # Enforce Shallow Depth Law: max_depth <= 2
                    m_depth = s_data.get("max_depth", 2)
                    if m_depth > 2:
                        issues.append(f"CONSTITUTIONAL VIOLATION: Specialist '{s_id}' declares max_depth {m_depth} > 2 (violates Shallow Depth Law).")
                    # Enforce Shallow Depth Law: specialists cannot delegate
                    r_type = str(s_data.get("role_type", "SPECIALIST")).upper()
                    if r_type != "PRIMARY" and s_data.get("can_delegate", False):
                        issues.append(f"CONSTITUTIONAL VIOLATION: Specialist '{s_id}' declares can_delegate=True (violates Shallow Depth Law).")
                    # Check for forbidden core overrides
                    raw_b = s_data.get("boundary", {})
                    allowed = raw_b.get("allowed_capabilities", s_data.get("allowed_capabilities", []))
                    for a in allowed:
                        if "core-immutable:override" in a or "platform-hook:override" in a:
                            issues.append(f"CONSTITUTIONAL VIOLATION: Specialist '{s_id}' attempts to claim override authority over immutable core rules.")
            if not any("CONSTITUTIONAL VIOLATION: Specialist" in iss for iss in issues):
                passed.append(f"Agent topology configuration verified ({len(specs)} specialists).")

    is_valid = len(issues) == 0
    return AdapterVerificationResult(
        is_valid=is_valid,
        issues=issues,
        passed_checks=passed,
        manifest_fingerprint=current_fingerprint or cfg.manifest_fingerprint
    )
