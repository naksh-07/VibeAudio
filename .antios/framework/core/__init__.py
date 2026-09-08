"""AntiOS 2.0 Core Framework Package.

This package provides the governance and capability primitives for AntiOS:
- config: Declarative adapter configuration and defaults
- guard: Deterministic path protection and boundary enforcement
- gate: Dynamic test runner execution and verification ratchets
- verdict: Structured verifier verdict data model and parsing
- governance: Governance model primitives (RULE/SKILL/WORKFLOW/HOOK/TOOL/ADAPTER)
- tool: Minimal tool abstraction with selection policy and failure taxonomy
- changeset: Same Change Set integrity evaluation engine
- worktree: Git working tree state inspection and conflict detection
- version: Authoritative SemVer versioning and release channel management
"""

from framework.core.version import (
    ANTIOS_VERSION,
    CURRENT_SCHEMA_VERSION,
    ADAPTER_SCHEMA_VERSION,
    ReleaseChannel,
    SemVer,
    VersionInfo,
    get_version_info,
    compare_versions,
)

__version__ = ANTIOS_VERSION


from framework.core.config import AntiOSConfig, load_config
from framework.core.guard import evaluate_tool_call
from framework.core.gate import evaluate_stop_gate, resolve_verification_scope
from framework.core.verdict import (
    VerificationVerdict,
    parse_verdict,
    format_verdict,
    prepare_checker_context,
    evaluate_checker_verdict,
)
from framework.core.governance import (
    GovernancePrimitiveType,
    GovernancePrimitiveDefinition,
    GOVERNANCE_TAXONOMY,
    get_governance_primitive,
    validate_governance_boundaries,
)
from framework.core.tool import (
    ToolTier,
    ToolStatus,
    FailureClass,
    ToolIdentity,
    ToolResult,
    ToolSelectionPolicy,
)
from framework.core.changeset import (
    ChangesetPolicy,
    ChangeSetEvaluation,
    evaluate_changeset,
)
from framework.core.worktree import (
    WorktreeDisposition,
    WorktreeSnapshot,
    WorktreeAuditResult,
    capture_worktree_snapshot,
    inspect_all_conflicts,
    audit_worktree,
)
from framework.core.profile import (
    EvidenceTier,
    ConfidenceLevel,
    ToolCategory,
    ConflictType,
    EvidenceFact,
    InferredFact,
    UnknownFact,
    ToolFact,
    GuidanceFact,
    ConflictFact,
    ProjectIdentity,
    ProjectProfile,
)
from framework.core.discovery import (
    ProjectDiscoveryEngine,
    discover_project,
)
from framework.core.adapter import (
    ActionType,
    ChangeTarget,
    ProposalRisk,
    AdaptationProposalItem,
    AdaptationProposal,
    AdapterVerificationResult,
    analyze_adaptation,
    generate_adapter_config,
    apply_project_adaptation,
    verify_adapter,
)
from framework.core.lifecycle import (
    TaskStage,
    TaskStatus,
    TaskClass,
    RiskTier,
    TaskState,
    create_task,
    transition_stage,
    interrupt_task,
    block_task,
    recover_task,
    fail_task,
    sync_to_active_context,
    parse_active_context,
)
from framework.core.workflow import (
    WorkflowSpec,
    WORKFLOW_REGISTRY,
    get_workflow,
    list_workflows,
)
from framework.core.topology import (
    WorkspaceTopology,
    WorkspaceMember,
    detect_workspace_topology,
)
from framework.core.memory import (
    MemoryCategory,
    KnowledgeAuthority,
    MemoryRecord,
    ProjectKnowledgeFact,
    DecisionRecord,
    LessonRecord,
    HistoricalRecord,
    MemoryWritePolicy,
    sync_project_knowledge,
    parse_project_knowledge,
    sync_lessons,
    parse_lessons,
    sync_historical_record,
    parse_historical_record,
    sync_decision_register,
    parse_decision_register,
    DeterministicLessonMatcher,
    DistillationResult,
    LessonDistillationEngine,
)
from framework.core.recovery import (
    ContradictionType,
    Contradiction,
    RecoveryPlan,
    reconstruct_session_state,
    detect_state_contradictions,
    is_verification_stale,
    generate_recovery_plan,
    recover_session,
)
from framework.core.telemetry import (
    ExecutionTelemetryRecord,
    record_telemetry,
    load_telemetry,
    summarize_telemetry,
)
from framework.core.subsystem import (
    SubsystemDeclaration,
    validate_subsystem_declaration,
)
from framework.core.wayfinding import (
    WayfindingEngine,
    LocalityResolution,
)
from framework.core.docaudit import (
    DocReference,
    DocAuditResult,
    audit_documentation_references,
    audit_all_documentation,
)
from framework.core.knowledge import (
    KnowledgeEpistemicTier,
    RelationshipType,
    KnowledgeEdge,
    KnowledgeGraph,
    OwnershipResolution,
    OwnershipDeriver,
    DocCategory,
    DocArtifactFact,
    DocKnowledgeClassifier,
    ChangeIntent,
    ChangeIntentAnalyzer,
    ProgressiveDisclosureLevel,
    ProgressiveDisclosureEngine,
)
from framework.core.capability import (
    Capability,
    CapabilityType,
    CapabilityScope,
    RulePrecedence,
    RuleConflictStatus,
    VerifierType,
    MCPStatus,
    RuleCapability,
    SpecialistCapability,
    MCPDecision,
)
from framework.core.capability_registry import (
    CapabilityRegistry,
    build_default_registry,
)
from framework.core.capability_router import (
    CapabilityRouter,
    TaskIntent,
)
from framework.core.capability_pack import (
    CapabilityPack,
)
from framework.core.agent_role import (
    AgentRole,
    AgentRoleType,
    AgentCapabilityBoundary,
    DelegationDecisionType,
    EscalationPolicyType,
    AgentHandoffContract,
    SpecialistResultReport,
    SpecialistCandidate,
)
from framework.core.agent_topology import (
    AgentTopologyRegistry,
    build_default_agent_topology,
    SpecialistDiscoveryEngine,
)
from framework.core.agent_routing_pack import (
    AgentRoutingPack,
)
from framework.core.agent_router import (
    AgentRouter,
)
from framework.core.tool import (
    ExecutionMode,
    Locality,
    ProviderAvailability,
    CostHint,
    LatencyHint,
    ToolPolicyStatus,
    ToolDefinition,
)
from framework.core.provider import (
    ProviderType,
    ProviderPolicyStatus,
    ProviderDefinition,
)
from framework.core.tool_registry import (
    ToolRegistry,
    build_default_tool_registry,
)
from framework.core.tool_policy import (
    MCPJustificationReport,
    MCPJustificationEngine,
    DeterministicToolSelector,
)
from framework.core.tool_pack import (
    ToolRoutingPack,
)


# Phase 43-48: Project Agent OS Foundation, Manifest, Provenance, Compilation, Installation & Orchestration
from framework.core.manifest import (
    CURRENT_ANTIOS_VERSION,
    CURRENT_SCHEMA_VERSION,
    InstallationState,
    AdaptationState,
    ArtifactOwnership,
    ArtifactRecord,
    ProjectManifest,
    load_manifest,
    save_manifest,
)
from framework.core.provenance import (
    ProvenanceConflict,
    ProvenanceTracker,
    classify_artifact,
    can_safely_overwrite,
    compute_file_sha256,
)
from framework.core.compiler import (
    CompilationResult,
    ProjectBoundaryCompiler,
)
from framework.core.installation import (
    LifecycleResult,
    InstallationLifecycleManager,
)
from framework.core.orchestration import (
    OrchestrationBudgetExceeded,
    WaveState,
    StructuredHandoff,
    AgentRecord,
    OrchestrationBudget,
    Wave,
    WaveManager,
)

# Phase 55-60: Project Anatomy & Intelligence Synthesis
from framework.core.anatomy import (
    ProjectArchetype,
    ProjectAnatomy,
    ProjectAnatomyCompiler,
)
from framework.core.component_intelligence import (
    ComponentIntelligenceReport,
    ComponentIntelligenceResolver,
)
from framework.core.skill_generator import (
    SkillGenerator,
)
from framework.core.specialist_generator import (
    SpecialistGenerator,
)
from framework.core.intelligence_verifier import (
    IntelligenceVerificationStatus,
    IntelligenceIssue,
    IntelligenceVerificationVerdict,
    IntelligenceVerifier,
)

# Phase 61-66: Project Learning & Safe Intelligence Evolution
from framework.core.learning import (
    EpistemicSource,
    ObservationType,
    KnowledgeState,
    Observation,
    ObservationStore,
    CandidateLesson,
    LessonDistiller,
    EvidencePromotionEngine,
    ProposalType,
    EvolutionProposal,
    EvolutionProposalEngine,
    DecayReport,
    KnowledgeDecayEngine,
    LearningSafetyGate,
    LearningEngine,
)

# Phase 67: Two-Way Adaptation Contract
from framework.core.two_way_contract import (
    AdaptationTier,
    SignalType,
    EpistemicForm,
    AuthorityTier,
    AdaptationSignal,
    TransitionGateVerdict,
    TransitionGateResult,
    TwoWayAdaptationContract,
)

# Phase 68: Capability Gap Detection
from framework.core.capability_gap import (
    GapClassification,
    GapStatus,
    CapabilityGap,
    CapabilityGapDetector,
    GapLifecycleEngine,
)

# Phase 69: Tool / MCP Gap Analysis
from framework.core.tool_gap import (
    ToolEscalationTier,
    ToolAlternativeEvaluation,
    ToolGapReport,
    ToolGapAnalyzer,
)

# Phase 70: Capability Proposal Engine
from framework.core.evolution_proposal import (
    StructuredProposalType,
    ProposalApprovalState,
    AlternativeOption,
    StructuredCapabilityProposal,
    CapabilityProposalEngine,
)

# Phase 71: Controlled AntiOS Evolution
from framework.core.evolution_governance import (
    ApprovalClass,
    EvolutionSnapshot,
    EvolutionExecutionResult,
    ControlledEvolutionGovernor,
)

# Phase 72: Compatibility & Migration Contract
from framework.core.migration import (
    CompatibilityState,
    MigrationStep,
    MigrationPlan,
    MigrationResult,
    MigrationEngine,
)

# Phase 73: Agent-Native Score Engine
from framework.core.agent_native_score import (
    EpistemicDimensionState,
    ConfidenceLevel,
    ScoreDimension,
    DimensionScore,
    AgentNativeScoreCard,
    AgentNativeScoreEngine,
)

# Phase 74: Agent Friction Detection Engine
from framework.core.agent_friction import (
    FrictionCategory,
    FrictionClassification,
    FrictionSeverity,
    AgentCostLevel,
    FrictionStatus,
    AgentFrictionFinding,
    AgentFrictionReport,
    AgentFrictionDetector,
)

# Phase 75: Improvement Proposal Engine
from framework.core.agent_improvement import (
    ImprovementProposalEngine,
)

# Phase 76: Evidence-Driven Documentation Compiler
from framework.core.documentation_compiler import (
    DocSurfaceType,
    CompiledDocSurface,
    DocCompilationResult,
    DocumentationCompiler,
)

# Phase 77: Agent-Native Refactoring Advisor
from framework.core.agent_refactoring import (
    RefactoringRecommendation,
    RefactoringAdvisorReport,
    AgentRefactoringAdvisor,
)

# Phase 78: Agent-Native Certification Engine
from framework.core.agent_native_certification import (
    CertificationLevel,
    AgentNativeCertification,
    AgentNativeCertificationEngine,
)

from framework.core.docaudit import (
    DocAuditSummary,
    DocReferenceAuditor,
)

# Phase 79: Project Instance Runtime Closure Contract
from framework.core.runtime_contract import (
    REQUIRED_INSTANCE_ARTIFACTS,
    REQUIRED_RUNTIME_SCRIPTS,
    FORBIDDEN_SOURCE_PATTERNS,
    RuntimeClosureResult,
    verify_runtime_closure,
)

# Phase 83: Native Workforce Contract
from framework.core.workforce_contract import (
    ResponsibilityDomain,
    ResponsibilityAllocation,
    CapabilityHierarchyStep,
    WorkforceContract,
    DEFAULT_WORKFORCE_CONTRACT,
)

# Phase 84 & 85: Adaptive Workforce Planner & Teamwork Orchestration
from framework.core.orchestration import (
    WorkerMetadata,
    WorkforceCostReasoning,
    AdaptiveWorkforcePlanner,
    WavePersistenceEngine,
    FailureType,
    RecoveryAction,
    FailureRecoveryDecision,
    FailureRecoveryEngine,
)

# Phase 86: 8-Tier Hybrid Capability Execution Matrix
from framework.core.tool import (
    HybridCapabilityTier,
)
from framework.core.tool_policy import (
    MCPJustificationReport,
    HybridResolutionResult,
    HybridCapabilityExecutionMatrix,
)

# Phase 87: Context Budget Governor
from framework.core.context_budget import (
    ContextClassification,
    GovernorAction,
    ContextSourceType,
    ContextSourceItem,
    ContextSelectionDecision,
    ContextBudgetCard,
    ContextBudgetResult,
    ContextBudgetGovernor,
)

# Phase 88: Context Freshness & Safe Compaction
from framework.core.context_freshness import (
    ContextFreshnessState,
    FreshnessEvaluation,
    FreshnessEvaluator,
    CompactedFact,
    SafeContextCompactor,
)

# Phase 89: Mission State Continuity & Output Bounding
from framework.core.mission_state import (
    MissionPersistenceMode,
    MissionLifecycleState,
    MissionRecoveryAction,
    ToolOutputClassification,
    ToolOutputEvidence,
    ToolOutputClassifier,
    MissionState,
    MissionStateStore,
    MissionRecoveryDecision,
    MissionRecoveryEngine,
)

# Phase 90: Evidence Architecture
from framework.core.evidence import (
    EpistemicCategory,
    EvidenceState,
    ArtifactFingerprint,
    EvidenceItem,
    EvidencePackage,
    EvidenceBuilder,
)

# Phase 91: Mission Evaluation Engine
from framework.core.mission_evaluation import (
    EvaluationStatus,
    MissionEvaluationDimension,
    DimensionEvaluation,
    MissionEvaluationCard,
    MissionEvaluationResult,
    IndependentVerifierContract,
    MissionEvaluationEngine,
)

# Phase 92: Agent-Native Mission Benchmark
from framework.core.mission_benchmark import (
    ComparisonOutcome,
    ScenarioId,
    BenchmarkProxyMetric,
    BenchmarkTrace,
    BenchmarkReportCard,
    ProvingGroundScenario,
    ProvingGroundScenarioRegistry,
    MissionBenchmarkEngine,
)

# Phase 93: Durable Project Proofs
from framework.core.project_proof import (
    MAX_DURABLE_PROOFS,
    MAX_REFERENCES_PER_PROOF,
    MAX_TRACKED_PATHS_PER_PROOF,
    ProofSubject,
    ProofStatus,
    RevalidationPolicy,
    ProjectProof,
    ProjectProofCard,
    EvidenceDistillationEngine,
    ProjectProofStore,
)

# Phase 94: Runtime Drift Detection & Intelligence Health
from framework.core.drift_health import (
    MAX_DRIFT_FINDINGS,
    MAX_REPAIR_PROPOSALS,
    DriftDomain,
    DriftSeverity,
    DriftAction,
    IntelligenceHealthStatus,
    RepairActionType,
    DriftFinding,
    RepairProposal,
    IntelligenceHealthResult,
    DriftHealthCard,
    ProjectDriftEngine,
    IntelligenceHealthEngine,
    IntelligenceRepairEngine,
)

# Phase 95: Long-Horizon Release Certification
from framework.core.release_certification import (
    MAX_CERTIFICATION_MISSIONS,
    CertificationLevel,
    CertificationDimension,
    CertificationWindow,
    LongHorizonCertificationCard,
    CertificationResult,
    ReleaseCertificationEngine,
)

# Phase 96: Real Antigravity Proving Ground
from framework.core.proving_ground import (
    EngineeringScenario,
    ExecutionMode,
    MissionTrace,
    ProvingGroundResult,
    RealProvingGround,
    ScenarioCatalog,
)

# Phase 97: Failure Injection & Recovery Matrix
from framework.core.failure_injection import (
    FailureClass,
    FailureInjectionHarness,
    FailureInjectionResult,
    FailureMatrixCatalog,
    FailureMode,
    FailureSpec,
    RecoveryAction,
)

# Phase 98: Long-Horizon Adaptive Evaluation
from framework.core.long_horizon import (
    EvaluationSequence,
    LongHorizonEvaluationEngine,
    LongHorizonSequenceId,
    LongHorizonSequenceReport,
    LongHorizonStepResult,
    StepEvaluation,
)

# Phase 99: Full System Certification Audit
from framework.core.certification_audit import (
    AreaAuditResult,
    AuditArea,
    AuditFinding,
    AuditStatus,
    SystemCertificationAuditCard,
    SystemCertificationAuditEngine,
    SystemCertificationAuditReport,
)

# Phase 100: Fresh Project Universal Adoption Proving Ground
from framework.core.universal_adoption import (
    AdoptionStepResult,
    ExecutionLabel,
    TwoWayAdaptationAudit,
    UniversalAdoptionCard,
    UniversalAdoptionProvingGround,
    UniversalAdoptionReport,
)

# Phase 101: Production Readiness & Architecture Freeze
from framework.core.architecture_freeze import (
    ArchitectureFreezeValidator,
    CriticalInvariant,
    DimensionEvaluation as FreezeDimensionEvaluation,
    InvariantRegistry,
    InvariantStatus,
    ProductionReadinessCard,
    ProductionReadinessEngine,
    ProductionReadinessReport,
    ReadinessDimension,
    ReadinessStatus,
)

# Phase 103: Storage & Data Directory Foundation
from framework.core.experience import (
    CURRENT_STORAGE_SCHEMA_VERSION,
    StorageError,
    DataDirectoryNotConfiguredError,
    DataDirectoryNotFoundError,
    TenantIsolationViolationError,
    MigrationError,
    StorageContext,
    StorageStatus,
    AntiOSDataResolver,
    init_data_directory,
    get_db_connection,
    init_experience_db,
    register_project,
    verify_project_isolation,
    backup_database,
    get_storage_status,
)

# Phase 104: Telemetry Sanitizer & Privacy Engine
from framework.core.sanitizer import (
    SANITIZER_VERSION,
    MAX_OUTPUT_SUMMARY_CHARS,
    MAX_EVENT_PAYLOAD_CHARS,
    MAX_ARG_STRING_CHARS,
    SanitizerDecision,
    SanitizerReason,
    PathClassification,
    SafeToolCall,
    SafeEngineeringEvent,
    SanitizationAuditRecord,
    TelemetrySanitizer,
)

# Phase 105: Telemetry Ingestion Bridge & Event Normalization
from framework.core.experience import (
    ExperienceRepository,
    IngestionCheckpoint,
)
from framework.core.telemetry_bridge import (
    AntigravityEventBridge,
    TelemetryCollectionMode,
    TelemetryConfigResolver,
    TranscriptParser,
    EventNormalizer,
    IngestionResult,
)

# Phase 106: Experience Intelligence Engine
from framework.core.experience_analytics import (
    MetricStatus,
    MetricValue,
    FailurePattern,
    FrictionPattern,
    SuccessfulStrategy,
    CapabilityStats,
    SubagentStats,
    ExperienceReport,
    ExperienceAnalyticsEngine,
    ExperienceExporter,
)

# Phase 107: Experience Operations, Hardening & Certification
from framework.core.experience import (
    restore_database,
    purge_experience_data,
    vacuum_database,
    export_raw_experience,
)

__all__ = [

    # Phase 12-15
    "AntiOSConfig",
    "load_config",
    "evaluate_tool_call",
    "evaluate_stop_gate",
    "VerificationVerdict",
    "parse_verdict",
    "format_verdict",
    "TaskStage",
    "TaskStatus",
    "TaskClass",
    "RiskTier",
    "TaskState",
    "create_task",
    "transition_stage",
    "interrupt_task",
    "block_task",
    "recover_task",
    "fail_task",
    "sync_to_active_context",
    "parse_active_context",
    "WorkflowSpec",
    "WORKFLOW_REGISTRY",
    "get_workflow",
    "list_workflows",
    # Phase 16-18: Governance
    "GovernancePrimitiveType",
    "GovernancePrimitiveDefinition",
    "GOVERNANCE_TAXONOMY",
    "get_governance_primitive",
    "validate_governance_boundaries",
    # Phase 16-18: Tool
    "ToolTier",
    "ToolStatus",
    "FailureClass",
    "ToolIdentity",
    "ToolResult",
    "ToolSelectionPolicy",
    # Phase 16-18: Changeset
    "ChangesetPolicy",
    "ChangeSetEvaluation",
    "evaluate_changeset",
    # Phase 16-18: Worktree
    "WorktreeDisposition",
    "WorktreeSnapshot",
    "WorktreeAuditResult",
    "capture_worktree_snapshot",
    "inspect_all_conflicts",
    "audit_worktree",
    # Phase 19-20: Project Intelligence & Adaptation
    "EvidenceTier",
    "ConfidenceLevel",
    "ToolCategory",
    "ConflictType",
    "EvidenceFact",
    "InferredFact",
    "UnknownFact",
    "ToolFact",
    "GuidanceFact",
    "ConflictFact",
    "ProjectIdentity",
    "ProjectProfile",
    "ProjectDiscoveryEngine",
    "discover_project",
    "ActionType",
    "ChangeTarget",
    "ProposalRisk",
    "AdaptationProposalItem",
    "AdaptationProposal",
    "AdapterVerificationResult",
    "analyze_adaptation",
    "generate_adapter_config",
    "apply_project_adaptation",
    "verify_adapter",
    # Phase 21-22: Workspace Topology, Memory & Recovery
    "WorkspaceTopology",
    "WorkspaceMember",
    "detect_workspace_topology",
    "MemoryCategory",
    "KnowledgeAuthority",
    "MemoryRecord",
    "ProjectKnowledgeFact",
    "DecisionRecord",
    "LessonRecord",
    "HistoricalRecord",
    "MemoryWritePolicy",
    "sync_project_knowledge",
    "parse_project_knowledge",
    "sync_lessons",
    "parse_lessons",
    "sync_historical_record",
    "parse_historical_record",
    "sync_decision_register",
    "parse_decision_register",
    "DeterministicLessonMatcher",
    "DistillationResult",
    "LessonDistillationEngine",
    "prepare_checker_context",
    "evaluate_checker_verdict",
    "resolve_verification_scope",
    "ContradictionType",
    "Contradiction",
    "RecoveryPlan",
    "reconstruct_session_state",
    "detect_state_contradictions",
    "is_verification_stale",
    "generate_recovery_plan",
    "recover_session",
    "ExecutionTelemetryRecord",
    "record_telemetry",
    "load_telemetry",
    "summarize_telemetry",
    # Phase 27: Wayfinding, Subsystems & Doc Audit
    "SubsystemDeclaration",
    "validate_subsystem_declaration",
    "WayfindingEngine",
    "LocalityResolution",
    "DocReference",
    "DocAuditResult",
    "audit_documentation_references",
    "audit_all_documentation",
    # Phase 28-30: Project Knowledge & Wayfinding
    "KnowledgeEpistemicTier",
    "RelationshipType",
    "KnowledgeEdge",
    "KnowledgeGraph",
    "OwnershipResolution",
    "OwnershipDeriver",
    "DocCategory",
    "DocArtifactFact",
    "DocKnowledgeClassifier",
    "ChangeIntent",
    "ChangeIntentAnalyzer",
    "ProgressiveDisclosureLevel",
    "ProgressiveDisclosureEngine",
    # Phase 31-33: Project Capability Layer
    "Capability",
    "CapabilityType",
    "CapabilityScope",
    "RulePrecedence",
    "RuleConflictStatus",
    "VerifierType",
    "MCPStatus",
    "RuleCapability",
    "SpecialistCapability",
    "MCPDecision",
    "CapabilityRegistry",
    "build_default_registry",
    "CapabilityRouter",
    "TaskIntent",
    "CapabilityPack",
    # Phase 34-36: Agent Topology & Specialist Layer
    "AgentRole",
    "AgentRoleType",
    "AgentCapabilityBoundary",
    "DelegationDecisionType",
    "EscalationPolicyType",
    "AgentHandoffContract",
    "SpecialistResultReport",
    "SpecialistCandidate",
    "AgentTopologyRegistry",
    "build_default_agent_topology",
    "SpecialistDiscoveryEngine",
    "AgentRoutingPack",
    "AgentRouter",
    # Phase 37-39: Tool, Provider & MCP Architecture
    "ExecutionMode",
    "Locality",
    "ProviderAvailability",
    "CostHint",
    "LatencyHint",
    "ToolPolicyStatus",
    "ToolDefinition",
    "ProviderType",
    "ProviderPolicyStatus",
    "ProviderDefinition",
    "ToolRegistry",
    "build_default_tool_registry",
    "MCPJustificationReport",
    "MCPJustificationEngine",
    "DeterministicToolSelector",
    "ToolRoutingPack",
    # Phase 43-48: Project Agent OS
    "CURRENT_ANTIOS_VERSION",
    "CURRENT_SCHEMA_VERSION",
    "InstallationState",
    "AdaptationState",
    "ArtifactOwnership",
    "ArtifactRecord",
    "ProjectManifest",
    "load_manifest",
    "save_manifest",
    "ProvenanceConflict",
    "ProvenanceTracker",
    "classify_artifact",
    "can_safely_overwrite",
    "compute_file_sha256",
    "CompilationResult",
    "ProjectBoundaryCompiler",
    "LifecycleResult",
    "InstallationLifecycleManager",
    "OrchestrationBudgetExceeded",
    "WaveState",
    "StructuredHandoff",
    "AgentRecord",
    "OrchestrationBudget",
    "Wave",
    "WaveManager",
    # Phase 55-60: Project Anatomy & Intelligence Synthesis
    "ProjectArchetype",
    "ProjectAnatomy",
    "ProjectAnatomyCompiler",
    "ComponentIntelligenceReport",
    "ComponentIntelligenceResolver",
    "SkillGenerator",
    "SpecialistGenerator",
    "IntelligenceVerificationStatus",
    "IntelligenceIssue",
    "IntelligenceVerificationVerdict",
    "IntelligenceVerifier",
    # Phase 61-66: Project Learning & Safe Intelligence Evolution
    "EpistemicSource",
    "ObservationType",
    "KnowledgeState",
    "Observation",
    "ObservationStore",
    "CandidateLesson",
    "LessonDistiller",
    "EvidencePromotionEngine",
    "ProposalType",
    "EvolutionProposal",
    "EvolutionProposalEngine",
    "DecayReport",
    "KnowledgeDecayEngine",
    "LearningSafetyGate",
    "LearningEngine",
    # Phase 67: Two-Way Adaptation Contract
    "AdaptationTier",
    "SignalType",
    "EpistemicForm",
    "AuthorityTier",
    "AdaptationSignal",
    "TransitionGateVerdict",
    "TransitionGateResult",
    "TwoWayAdaptationContract",
    # Phase 68: Capability Gap Detection
    "GapClassification",
    "GapStatus",
    "CapabilityGap",
    "CapabilityGapDetector",
    "GapLifecycleEngine",
    # Phase 69: Tool / MCP Gap Analysis
    "ToolEscalationTier",
    "ToolAlternativeEvaluation",
    "ToolGapReport",
    "ToolGapAnalyzer",
    # Phase 70: Capability Proposal Engine
    "StructuredProposalType",
    "ProposalApprovalState",
    "AlternativeOption",
    "StructuredCapabilityProposal",
    "CapabilityProposalEngine",
    # Phase 71: Controlled AntiOS Evolution
    "ApprovalClass",
    "EvolutionSnapshot",
    "EvolutionExecutionResult",
    "ControlledEvolutionGovernor",
    # Phase 72: Compatibility & Migration Contract
    "CompatibilityState",
    "MigrationStep",
    "MigrationPlan",
    "MigrationResult",
    "MigrationEngine",
    # Phase 73: Agent-Native Score Engine
    "EpistemicDimensionState",
    "ConfidenceLevel",
    "ScoreDimension",
    "DimensionScore",
    "AgentNativeScoreCard",
    "AgentNativeScoreEngine",
    # Phase 74: Agent Friction Detection Engine
    "FrictionCategory",
    "FrictionClassification",
    "FrictionSeverity",
    "AgentCostLevel",
    "FrictionStatus",
    "AgentFrictionFinding",
    "AgentFrictionReport",
    "AgentFrictionDetector",
    # Phase 75: Improvement Proposal Engine
    "ImprovementProposalEngine",
    # Phase 76: Evidence-Driven Documentation Compiler
    "DocSurfaceType",
    "CompiledDocSurface",
    "DocCompilationResult",
    "DocumentationCompiler",
    # Phase 77: Agent-Native Refactoring Advisor
    "RefactoringRecommendation",
    "RefactoringAdvisorReport",
    "AgentRefactoringAdvisor",
    # Phase 78: Agent-Native Certification Engine
    "CertificationLevel",
    "AgentNativeCertification",
    "AgentNativeCertificationEngine",
    "DocAuditSummary",
    "DocReferenceAuditor",
    # Phase 79: Project Instance Runtime Closure Contract
    "REQUIRED_INSTANCE_ARTIFACTS",
    "REQUIRED_RUNTIME_SCRIPTS",
    "FORBIDDEN_SOURCE_PATTERNS",
    "RuntimeClosureResult",
    "verify_runtime_closure",
    # Phase 83: Native Workforce Contract
    "ResponsibilityDomain",
    "ResponsibilityAllocation",
    "CapabilityHierarchyStep",
    "WorkforceContract",
    "DEFAULT_WORKFORCE_CONTRACT",
    # Phase 84 & 85: Adaptive Workforce Planner & Teamwork Orchestration
    "WorkerMetadata",
    "WorkforceCostReasoning",
    "AdaptiveWorkforcePlanner",
    "WavePersistenceEngine",
    "FailureType",
    "RecoveryAction",
    "FailureRecoveryDecision",
    "FailureRecoveryEngine",
    # Phase 86: 8-Tier Hybrid Capability Execution Matrix
    "HybridCapabilityTier",
    "MCPJustificationReport",
    "HybridResolutionResult",
    "HybridCapabilityExecutionMatrix",
    # Phase 87: Context Budget Governor
    "ContextClassification",
    "GovernorAction",
    "ContextSourceType",
    "ContextSourceItem",
    "ContextSelectionDecision",
    "ContextBudgetCard",
    "ContextBudgetResult",
    "ContextBudgetGovernor",
    # Phase 88: Context Freshness & Safe Compaction
    "ContextFreshnessState",
    "FreshnessEvaluation",
    "FreshnessEvaluator",
    "CompactedFact",
    "SafeContextCompactor",
    # Phase 89: Mission State Continuity & Output Bounding
    "MissionPersistenceMode",
    "MissionLifecycleState",
    "MissionRecoveryAction",
    "ToolOutputClassification",
    "ToolOutputEvidence",
    "ToolOutputClassifier",
    "MissionState",
    "MissionStateStore",
    "MissionRecoveryDecision",
    "MissionRecoveryEngine",
    # Phase 90: Evidence Architecture
    "EpistemicCategory",
    "EvidenceState",
    "ArtifactFingerprint",
    "EvidenceItem",
    "EvidencePackage",
    "EvidenceBuilder",
    # Phase 91: Mission Evaluation Engine
    "EvaluationStatus",
    "MissionEvaluationDimension",
    "DimensionEvaluation",
    "MissionEvaluationCard",
    "MissionEvaluationResult",
    "IndependentVerifierContract",
    "MissionEvaluationEngine",
    # Phase 92: Agent-Native Mission Benchmark
    "ComparisonOutcome",
    "ScenarioId",
    "BenchmarkProxyMetric",
    "BenchmarkTrace",
    "BenchmarkReportCard",
    "ProvingGroundScenario",
    "ProvingGroundScenarioRegistry",
    "MissionBenchmarkEngine",
    # Phase 93: Durable Project Proofs
    "MAX_DURABLE_PROOFS",
    "MAX_REFERENCES_PER_PROOF",
    "MAX_TRACKED_PATHS_PER_PROOF",
    "ProofSubject",
    "ProofStatus",
    "RevalidationPolicy",
    "ProjectProof",
    "ProjectProofCard",
    "EvidenceDistillationEngine",
    "ProjectProofStore",
    # Phase 94: Runtime Drift Detection & Intelligence Health
    "MAX_DRIFT_FINDINGS",
    "MAX_REPAIR_PROPOSALS",
    "DriftDomain",
    "DriftSeverity",
    "DriftAction",
    "IntelligenceHealthStatus",
    "RepairActionType",
    "DriftFinding",
    "RepairProposal",
    "IntelligenceHealthResult",
    "DriftHealthCard",
    "ProjectDriftEngine",
    "IntelligenceHealthEngine",
    "IntelligenceRepairEngine",
    # Phase 95: Long-Horizon Release Certification
    "MAX_CERTIFICATION_MISSIONS",
    "CertificationLevel",
    "CertificationDimension",
    "CertificationWindow",
    "LongHorizonCertificationCard",
    "CertificationResult",
    "ReleaseCertificationEngine",
    # Phase 96: Real Antigravity Proving Ground
    "EngineeringScenario",
    "ExecutionMode",
    "MissionTrace",
    "ProvingGroundResult",
    "RealProvingGround",
    "ScenarioCatalog",
    # Phase 97: Failure Injection & Recovery Matrix
    "FailureClass",
    "FailureInjectionHarness",
    "FailureInjectionResult",
    "FailureMatrixCatalog",
    "FailureMode",
    "FailureSpec",
    "RecoveryAction",
    # Phase 98: Long-Horizon Adaptive Evaluation
    "EvaluationSequence",
    "LongHorizonEvaluationEngine",
    "LongHorizonSequenceId",
    "LongHorizonSequenceReport",
    "LongHorizonStepResult",
    "StepEvaluation",
    # Phase 99: Full System Certification Audit
    "AreaAuditResult",
    "AuditArea",
    "AuditFinding",
    "AuditStatus",
    "SystemCertificationAuditCard",
    "SystemCertificationAuditEngine",
    "SystemCertificationAuditReport",
    # Phase 100: Fresh Project Universal Adoption Proving Ground
    "AdoptionStepResult",
    "ExecutionLabel",
    "TwoWayAdaptationAudit",
    "UniversalAdoptionCard",
    "UniversalAdoptionProvingGround",
    "UniversalAdoptionReport",
    # Phase 101: Production Readiness & Architecture Freeze
    "ArchitectureFreezeValidator",
    "CriticalInvariant",
    "FreezeDimensionEvaluation",
    "InvariantRegistry",
    "InvariantStatus",
    "ProductionReadinessCard",
    "ProductionReadinessEngine",
    "ProductionReadinessReport",
    "ReadinessDimension",
    "ReadinessStatus",
    # Phase 103: Storage Foundation
    "CURRENT_STORAGE_SCHEMA_VERSION",
    "StorageError",
    "DataDirectoryNotConfiguredError",
    "DataDirectoryNotFoundError",
    "TenantIsolationViolationError",
    "MigrationError",
    "StorageContext",
    "StorageStatus",
    "AntiOSDataResolver",
    "init_data_directory",
    "get_db_connection",
    "init_experience_db",
    "register_project",
    "verify_project_isolation",
    "backup_database",
    "get_storage_status",
    # Phase 104: Telemetry Sanitizer & Privacy Engine
    "SANITIZER_VERSION",
    "MAX_OUTPUT_SUMMARY_CHARS",
    "MAX_EVENT_PAYLOAD_CHARS",
    "MAX_ARG_STRING_CHARS",
    "SanitizerDecision",
    "SanitizerReason",
    "PathClassification",
    "SafeToolCall",
    "SafeEngineeringEvent",
    "SanitizationAuditRecord",
    "TelemetrySanitizer",
    # Phase 105: Telemetry Ingestion Bridge & Event Normalization
    "ExperienceRepository",
    "IngestionCheckpoint",
    "AntigravityEventBridge",
    "TelemetryCollectionMode",
    "TelemetryConfigResolver",
    "TranscriptParser",
    "EventNormalizer",
    "IngestionResult",
    # Phase 106: Experience Intelligence Engine
    "MetricStatus",
    "MetricValue",
    "FailurePattern",
    "FrictionPattern",
    "SuccessfulStrategy",
    "CapabilityStats",
    "SubagentStats",
    "ExperienceReport",
    "ExperienceAnalyticsEngine",
    "ExperienceExporter",
    # Phase 107: Experience Operations, Hardening & Certification
    "restore_database",
    "purge_experience_data",
    "vacuum_database",
    "export_raw_experience",
]




