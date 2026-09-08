"""AntiOS Engineering Workflow Registry & Contracts.

Defines the 6 canonical universal engineering workflows:
FEATURE, BUG, REFACTOR, INVESTIGATION, DOCUMENTATION, RELEASE.
Composes Skills (HOW) with Workflows (WHEN + SEQUENCE).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

from framework.core.lifecycle import RiskTier, TaskClass, TaskStage


@dataclass
class WorkflowStep:
    stage: TaskStage
    name: str
    description: str
    composed_skill: Optional[str] = None
    required: bool = True


@dataclass
class WorkflowSpec:
    task_class: TaskClass
    name: str
    description: str
    default_risk: RiskTier
    entry_conditions: List[str]
    steps: List[WorkflowStep]
    completion_criteria: List[str]
    recovery_path: str
    composed_skills: List[str]


def _build_default_steps(task_class: TaskClass) -> List[WorkflowStep]:
    if task_class == TaskClass.BUG:
        return [
            WorkflowStep(TaskStage.INTAKE, "Bug Report Intake", "Ingest failure logs, user reports, or error stack traces."),
            WorkflowStep(TaskStage.UNDERSTAND, "Boundary Clarification", "Identify affected modules and immutable core boundaries."),
            WorkflowStep(TaskStage.INVESTIGATE, "Minimal Reproduction", "Author minimal reproduction test; isolate failure cause.", composed_skill="antios-debug"),
            WorkflowStep(TaskStage.PLAN, "Hypothesis & Patch Plan", "Formulate explicit root-cause hypothesis and minimal edit plan.", composed_skill="antios-engineer"),
            WorkflowStep(TaskStage.IMPLEMENT, "Surgical Patch", "Apply minimal surgical fix to application layer.", composed_skill="antios-engineer"),
            WorkflowStep(TaskStage.TEST, "Reproduction & Regression Run", "Run reproducing test and full project test suite.", composed_skill="antios-engineer"),
            WorkflowStep(TaskStage.VERIFY, "Verification Handoff", "Audit diff and execute physical tests via Maker-Checker if High Risk.", composed_skill="antios-verifier"),
            WorkflowStep(TaskStage.REVIEW, "Verdict & Diff Review", "Inspect structured JSON verdict and confirm zero regressions.", composed_skill="antios-engineer"),
            WorkflowStep(TaskStage.CONSOLIDATE, "Ledger & Conflict Check", "Sync docs/ACTIVE_CONTEXT.md, record dead-ends, verify clean diff.", composed_skill="antios-engineer"),
            WorkflowStep(TaskStage.COMPLETE, "Stop Gate Ratchet", "Physical Stop Gate executes tests with exit code 0.")
        ]
    elif task_class == TaskClass.INVESTIGATION:
        return [
            WorkflowStep(TaskStage.INTAKE, "Research Intake", "Define investigation objective, research question, or spike scope."),
            WorkflowStep(TaskStage.UNDERSTAND, "Scope & Constraints", "Identify knowledge domains and read-only boundaries."),
            WorkflowStep(TaskStage.INVESTIGATE, "Evidence Acquisition", "Explore codebase, inspect logs, benchmark options (read-only).", composed_skill="antios-engineer"),
            WorkflowStep(TaskStage.PLAN, "Hypothesis Evaluation", "Structure hypotheses and evidence claims."),
            WorkflowStep(TaskStage.IMPLEMENT, "Prototype in Scratch (Optional)", "Create temporary scripts strictly in scratch/."),
            WorkflowStep(TaskStage.TEST, "Evidence Verification", "Validate findings against physical code execution."),
            WorkflowStep(TaskStage.VERIFY, "Peer/Self Audit", "Verify claims against transcript and physical files."),
            WorkflowStep(TaskStage.REVIEW, "Synthesis Review", "Review findings, caveats, and recommendation."),
            WorkflowStep(TaskStage.CONSOLIDATE, "Artifact Output", "Document findings in report artifact; update ACTIVE_CONTEXT.md."),
            WorkflowStep(TaskStage.COMPLETE, "Investigation Complete", "Deliver structured report.")
        ]
    elif task_class == TaskClass.DOCUMENTATION:
        return [
            WorkflowStep(TaskStage.INTAKE, "Documentation Intake", "Identify doc targets (spec, architecture, guide, config)."),
            WorkflowStep(TaskStage.UNDERSTAND, "Factual Grounding", "Review actual codebase reality before drafting docs."),
            WorkflowStep(TaskStage.INVESTIGATE, "Documentation Audit", "Check existing docs for drift, stale info, or broken links."),
            WorkflowStep(TaskStage.PLAN, "Structure Plan", "Outline documentation changes adhering to token budgets."),
            WorkflowStep(TaskStage.IMPLEMENT, "Document Authoring", "Edit markdown specs and documentation files."),
            WorkflowStep(TaskStage.TEST, "Format & Link Check", "Validate markdown syntax, file links, and headers."),
            WorkflowStep(TaskStage.VERIFY, "Solo Sanity Check", "Low risk verification; confirm Same Change Set rules."),
            WorkflowStep(TaskStage.REVIEW, "Review Changes", "Inspect git diff to confirm no accidental code changes."),
            WorkflowStep(TaskStage.CONSOLIDATE, "Ledger Update", "Update docs/ACTIVE_CONTEXT.md with updated doc map."),
            WorkflowStep(TaskStage.COMPLETE, "Stop Gate Ratchet", "Clean working tree check and test runner pass.")
        ]
    elif task_class == TaskClass.REFACTOR:
        return [
            WorkflowStep(TaskStage.INTAKE, "Refactor Scope Intake", "Identify code to refactor and invariant external behavior."),
            WorkflowStep(TaskStage.UNDERSTAND, "Boundary & API Freeze", "Identify public APIs that must remain identical."),
            WorkflowStep(TaskStage.INVESTIGATE, "Baseline Verification", "Run full test suite to establish clean baseline before edits."),
            WorkflowStep(TaskStage.PLAN, "Refactor Migration Plan", "Draft implementation plan with explicit blast-radius limits."),
            WorkflowStep(TaskStage.IMPLEMENT, "Incremental Refactoring", "Apply modular edits preserving external interfaces."),
            WorkflowStep(TaskStage.TEST, "Continuous Regression Run", "Run tests after each incremental change."),
            WorkflowStep(TaskStage.VERIFY, "Independent Verification", "Fresh-context Checker verifies no behavior change.", composed_skill="antios-verifier"),
            WorkflowStep(TaskStage.REVIEW, "Diff Cleanliness Review", "Verify zero accidental edits or leftover debugging code."),
            WorkflowStep(TaskStage.CONSOLIDATE, "Doc Synchronization", "Update architectural docs in Same Change Set."),
            WorkflowStep(TaskStage.COMPLETE, "Stop Gate Ratchet", "Physical Stop Gate executes full test suite.")
        ]
    elif task_class == TaskClass.RELEASE:
        return [
            WorkflowStep(TaskStage.INTAKE, "Release / Maintenance Intake", "Review release scope, dependencies, or maintenance targets."),
            WorkflowStep(TaskStage.UNDERSTAND, "Release Criteria", "Identify version bump, changelog, and test matrix requirements."),
            WorkflowStep(TaskStage.INVESTIGATE, "Dependency & Security Audit", "Scan dependencies, changelog diffs, and security alerts."),
            WorkflowStep(TaskStage.PLAN, "Release Checklist Plan", "Draft release plan with rollback checkpoints."),
            WorkflowStep(TaskStage.IMPLEMENT, "Version & Config Bumps", "Update manifests, versions, and lockfiles."),
            WorkflowStep(TaskStage.TEST, "Full Matrix Test Run", "Execute full test suite across all configured runners."),
            WorkflowStep(TaskStage.VERIFY, "Mandatory Audit Verifier", "Independent Checker verifies clean tag state and tests.", composed_skill="antios-verifier"),
            WorkflowStep(TaskStage.REVIEW, "Changelog & Tag Review", "Inspect git diff for version tagging consistency."),
            WorkflowStep(TaskStage.CONSOLIDATE, "Release Ledger Finalization", "Finalize release notes and clean active context."),
            WorkflowStep(TaskStage.COMPLETE, "Stop Gate Ratchet", "Physical Stop Gate verifies exit code 0.")
        ]
    else:  # FEATURE (Default)
        return [
            WorkflowStep(TaskStage.INTAKE, "Feature Request Intake", "Ingest requirements, acceptance criteria, and user story."),
            WorkflowStep(TaskStage.UNDERSTAND, "Architecture Boundaries", "Map required changes against protected core zones."),
            WorkflowStep(TaskStage.INVESTIGATE, "Codebase Reconnaissance", "Inspect existing patterns, shared utilities, and extension points."),
            WorkflowStep(TaskStage.PLAN, "Implementation Plan", "Author implementation plan with risk tiering and Maker-Checker.", composed_skill="antios-engineer"),
            WorkflowStep(TaskStage.IMPLEMENT, "Guarded Implementation", "Apply guarded edits in Same Change Set.", composed_skill="antios-engineer"),
            WorkflowStep(TaskStage.TEST, "Unit & Integration Testing", "Execute native test runner locally.", composed_skill="antios-engineer"),
            WorkflowStep(TaskStage.VERIFY, "Independent Verification", "Dispatch Checker subagent if High Risk.", composed_skill="antios-verifier"),
            WorkflowStep(TaskStage.REVIEW, "Verdict & Diff Audit", "Review JSON verdict and fix any identified issues.", composed_skill="antios-engineer"),
            WorkflowStep(TaskStage.CONSOLIDATE, "Doc Sync & Conflict Check", "Sync docs/ACTIVE_CONTEXT.md and check conflict markers.", composed_skill="antios-engineer"),
            WorkflowStep(TaskStage.COMPLETE, "Stop Gate Ratchet", "Physical Stop Gate executes tests with exit code 0.")
        ]


WORKFLOW_REGISTRY: Dict[TaskClass, WorkflowSpec] = {
    TaskClass.FEATURE: WorkflowSpec(
        task_class=TaskClass.FEATURE,
        name="Feature Implementation Workflow",
        description="Standard end-to-end workflow for adding new functionality.",
        default_risk=RiskTier.MEDIUM,
        entry_conditions=["User request for new feature", "Clear acceptance criteria"],
        steps=_build_default_steps(TaskClass.FEATURE),
        completion_criteria=["All new and existing tests pass (exit code 0)", "Docs updated in same change set", "No merge conflict markers"],
        recovery_path="On test failure: transition to antios-debug. On verifier rejection: fix issues in IMPLEMENT stage.",
        composed_skills=["antios-engineer", "antios-verifier", "antios-debug"]
    ),
    TaskClass.BUG: WorkflowSpec(
        task_class=TaskClass.BUG,
        name="Systematic Bug-Fix Workflow",
        description="Root-cause debugging and minimal surgical patch workflow.",
        default_risk=RiskTier.MEDIUM,
        entry_conditions=["Failing test, crash log, or defect report"],
        steps=_build_default_steps(TaskClass.BUG),
        completion_criteria=["Reproducing test authors pass", "Full regression suite passes", "Root cause documented"],
        recovery_path="If hypothesis falsified: record in dead_ends, revert patch via git, formulate new hypothesis.",
        composed_skills=["antios-debug", "antios-engineer", "antios-verifier"]
    ),
    TaskClass.REFACTOR: WorkflowSpec(
        task_class=TaskClass.REFACTOR,
        name="Behavior-Preserving Refactor Workflow",
        description="Internal restructuring maintaining exact external behavior.",
        default_risk=RiskTier.HIGH,
        entry_conditions=["Clean baseline test pass", "Identified code debt or structural need"],
        steps=_build_default_steps(TaskClass.REFACTOR),
        completion_criteria=["100% regression tests pass", "Public APIs unchanged", "Diff cleanliness verified"],
        recovery_path="If regression introduced: git checkout to last clean commit. Do not add speculative fixes.",
        composed_skills=["antios-engineer", "antios-verifier", "antios-debug"]
    ),
    TaskClass.INVESTIGATION: WorkflowSpec(
        task_class=TaskClass.INVESTIGATION,
        name="Read-Only Architecture & Spike Investigation",
        description="Exploratory research and feasibility analysis without code modifications.",
        default_risk=RiskTier.LOW,
        entry_conditions=["Research query, architectural ambiguity, or spike mandate"],
        steps=_build_default_steps(TaskClass.INVESTIGATION),
        completion_criteria=["Structured findings report authored", "Evidence grounded in physical files", "Zero unintended code diffs"],
        recovery_path="If query blocked: record dead end in ACTIVE_CONTEXT.md and broaden investigation.",
        composed_skills=["antios-engineer"]
    ),
    TaskClass.DOCUMENTATION: WorkflowSpec(
        task_class=TaskClass.DOCUMENTATION,
        name="Documentation & Specification Workflow",
        description="Authoring and synchronizing specifications, guides, and architectural records.",
        default_risk=RiskTier.LOW,
        entry_conditions=["New architecture, API change, or outdated documentation"],
        steps=_build_default_steps(TaskClass.DOCUMENTATION),
        completion_criteria=["Markdown formatting valid", "File links verified", "Same Change Set compliant"],
        recovery_path="Fix syntax/links directly. Revert if git diff contains code changes.",
        composed_skills=["antios-engineer"]
    ),
    TaskClass.RELEASE: WorkflowSpec(
        task_class=TaskClass.RELEASE,
        name="Release & Maintenance Workflow",
        description="Version upgrades, dependency maintenance, and release verification.",
        default_risk=RiskTier.HIGH,
        entry_conditions=["Milestone completion or scheduled dependency update"],
        steps=_build_default_steps(TaskClass.RELEASE),
        completion_criteria=["Full matrix test pass", "Changelog finalized", "Clean git status"],
        recovery_path="Rollback package bump if dependency incompatibility detected.",
        composed_skills=["antios-engineer", "antios-verifier"]
    ),
}


def get_workflow(task_class: Union[TaskClass, str]) -> WorkflowSpec:
    """Retrieves a workflow specification by TaskClass enum or string name."""
    if isinstance(task_class, str):
        try:
            task_class = TaskClass(task_class.upper())
        except ValueError:
            task_class = TaskClass.FEATURE
    return WORKFLOW_REGISTRY.get(task_class, WORKFLOW_REGISTRY[TaskClass.FEATURE])


def list_workflows() -> List[WorkflowSpec]:
    """Returns all registered workflow specifications."""
    return list(WORKFLOW_REGISTRY.values())


def validate_workflow_step(task_class: TaskClass, current_stage: TaskStage) -> bool:
    """Validates if current_stage is a recognized step in the workflow."""
    spec = get_workflow(task_class)
    return any(step.stage == current_stage for step in spec.steps)
