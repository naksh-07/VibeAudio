# VibeAudio Engineering Documentation System & Architecture Map

Welcome to the canonical engineering documentation system for **VibeAudio**.

This repository contains the complete architectural specifications, execution roadmaps, design system contracts, testing frameworks, and agent orchestration protocols for the evolution of VibeAudio into an AI-native, zero-build, offline-first audio sanctuary.

---

## 1. Navigable System Map & Document Taxonomy

All documentation within `docs/` is classified into three operational categories:
- **Authoritative (A)**: The canonical, binding engineering contracts and specifications that govern all implementation work.
- **Supporting (S)**: Reference guides, tool manuals, and research deep dives that provide architectural rationale.
- **Historical (H)**: Past milestone reports, audit logs, and deprecated specifications preserved for auditability.

```text
docs/
├── README.md                                                        [A] System Navigation Index (This File)
│
├── plans/
│   └── VibeAudio-AI-Native-Frontend-Backend-Stitch-Evolution-Master-Plan.md  [A] MP-VIBE-001: 7-Phase Master Plan
│
├── architecture/
│   ├── VibeAudio-Target-Architecture.md                             [A] ARCH-VIBE-001: Canonical Decoupled 4-Layer System
│   └── VibeAudio-Persistence-Abstraction.md                         [A] ARCH-VIBE-002: Storage-Agnostic Interface Contract
│
├── implementation/
│   ├── VibeAudio-Frontend-Evolution-Spec.md                         [A] SPEC-FE-001: Design Tokens, Stores & Web Components
│   ├── VibeAudio-Offline-First-Evolution-Spec.md                    [A] SPEC-OFFLINE-001: Guest Migration & Resumable Downloads
│   ├── VibeAudio-Backend-Hybrid-API-Spec.md                         [A] SPEC-API-001: /api/v1 Edge & Lambda Contract
│   ├── VibeAudio-API-Migration-Plan.md                              [A] PLAN-MIG-001: Phased Coexistence & Deprecation Strategy
│   ├── VibeAudio-Sanctuary-Vertical-Slice.md                        [A] SPEC-SLICE-001: First End-to-End Experiment
│   ├── VibeAudio-Execution-Roadmap.md                               [A] ROADMAP-001: 13-Phase Executable Roadmap
│   ├── VibeAudio-Implementation-Dependency-Graph.md                 [A] GRAPH-001: Cross-Phase Blocking & Parallel Tracks
│   ├── VibeAudio-Light-UI-Implementation.md                         [H] Historical Light UI Implementation Notes
│   └── VibeAudio-Light-UI-Roadmap.md                                [H] Historical Light UI Completed Milestones
│
├── security/
│   └── VibeAudio-Backend-Security-Baseline.md                       [A] SEC-BASE-001: Threat Catalog & Remediation Blueprints
│
├── design/
│   ├── VibeAudio-Stitch-Implementation-Verification.md              [A] SPEC-DESIGN-001: Continuous Stitch Visual QA Loop
│   ├── VibeAudio-Light-Design-System.md                             [S] Supporting Design System Guide
│   ├── VibeAudio-Component-Spec.md                                  [S] Supporting Component Specification
│   ├── VibeAudio-Screen-Spec.md                                     [S] Supporting Screen Specification
│   └── stitch-previews/                                             [S] Rendered Prototypes & Screenshots
│
├── qa/
│   ├── VibeAudio-Testing-Strategy.md                                [A] QA-STRAT-001: 7-Level Testing Pyramid & Invariants
│   ├── VibeAudio-Playwright-Test-Spec.md                            [A] QA-E2E-001: Multi-Browser Automation Specification
│   ├── VibeAudio-Release-Gates.md                                   [A] QA-GATES-001: Release Gates 0 through 9 Pass/Fail Criteria
│   ├── VibeAudio-Light-UI-Acceptance.md                             [H] Historical Phase 5 Acceptance Criteria
│   ├── VibeAudio-Light-UI-Visual-QA.md                              [H] Historical Visual Verification Audit
│   ├── VibeAudio-Light-UI-Implementation-QA.md                      [H] Historical Light UI Implementation QA
│   └── VibeAudio-PHASE-5-RELEASE-REPORT.md                          [H] Historical Phase 5 Production Release Report
│
├── agents/
│   ├── VibeAudio-Jules-Execution-Protocol.md                        [A] AGENT-JULES-001: Bounded Autonomous Engineer Protocol
│   └── VibeAudio-Jules-Task-Catalog.md                              [A] AGENT-CAT-001: 22-Task Catalog & Prompts (EXP 01-03)
│
├── research/
│   ├── VibeAudio-Frontend-Backend-Stitch-Architecture-Deep-Research.md [S] DOC-RES-001: Foundational Architecture Research
│   └── VibeAudio-Jules-Capability-And-Agent-Workflow-Deep-Research.md  [S] WF-VIBE-04: Foundational Agent Research
│
└── stitch/
    ├── 01-landing.md .. 08-mobile.md                                [A] Canonical Screen Specifications from Project 6063499620727826815
    └── VibeAudio-Stitch-Master-Brief.md                             [S] Master Stitch Brief
```

---

## 2. Core Architectural Principles (Non-Negotiable Invariants)

Every engineer, agent (including Google Jules), and reviewer must uphold these four architectural invariants:

1. **Zero-Build Vanilla PWA Architecture**:
   - VibeAudio does **NOT** use frontend build tools (no Vite, Webpack, Rollup, or Babel) or component frameworks (no React, Vue, Next.js, or Svelte).
   - The presentation layer is pure browser-native HTML5, modular CSS with design tokens, native ES Modules (`type="module"`), and Shadow-DOM-free Custom Elements (`<vibe-player-deck>`, `<vibe-mini-player>`).
   - *Rationale*: Guarantees instant local file execution, offline caching simplicity without hash churn, and 0 KB framework runtime overhead.

2. **Storage-Agnostic Persistence Abstraction**:
   - **Database engine selection is intentionally deferred** to a future research phase.
   - All backend compute handlers interact with data strictly through domain repository interfaces (`CatalogRepository`, `UserRepository`, `ProgressRepository`, `LibraryRepository`).
   - No code may introduce concrete database dependencies (DynamoDB, D1, Postgres) outside mock implementations.

3. **Hybrid Edge & Core Compute Topology**:
   - **Cloudflare Workers (Edge Gateway)**: Handle read-heavy, low-latency edge caching (`/api/v1/catalog`), signed media streaming proxying with RFC 7233 Range support, and edge rate limiting.
   - **AWS Lambda (Compute Core)**: Handle authenticated business logic, Clerk JWKS token verification, Last-Write-Wins (LWW) progress reconciliation, and offline sync batch ingestion.

4. **Stitch is the Visual Source of Truth**:
   - The visual design language is defined exclusively in `.stitch/DESIGN.md` and `docs/stitch/*.md` (Light Editorial Sanctuary, canvas `#F5F5F7`, surface `#FFFFFF`, terracotta accent `#C64E00`, typography: `Newsreader`, `Inter`, `JetBrains Mono`).
   - All frontend styling merges must pass Playwright visual regression gates (`diff < 0.5%`).

---

## 3. Authoritative Specifications Index

### 3.1 Master Planning & Architecture
* [**Evolution Master Plan** (MP-VIBE-001)](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/plans/VibeAudio-AI-Native-Frontend-Backend-Stitch-Evolution-Master-Plan.md)  
  High-level 7-phase evolution blueprint synthesizing research findings into concrete development milestones.
* [**Target Canonical Architecture** (ARCH-VIBE-001)](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/architecture/VibeAudio-Target-Architecture.md)  
  Complete 4-layer architectural decomposition: UI, Application State, Domain Services, and Infrastructure, with local-first and network subsystem specifications.
* [**Persistence Abstraction Contract** (ARCH-VIBE-002)](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/architecture/VibeAudio-Persistence-Abstraction.md)  
  Database-agnostic TypeScript repository interfaces, consistency models, and access patterns.

### 3.2 Client & Offline Implementation
* [**Frontend Evolution Specification** (SPEC-FE-001)](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/implementation/VibeAudio-Frontend-Evolution-Spec.md)  
  Detailed specifications for CSS modularization, reactive observable stores (`PlayerStore`, `LibraryStore`, `UserStore`, `SyncStore`, `UIStore`), domain services, and native Custom Elements.
* [**Offline-First Evolution Specification** (SPEC-OFFLINE-001)](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/implementation/VibeAudio-Offline-First-Evolution-Spec.md)  
  Complete algorithms and state machines for guest-to-user storage migration (`migrateGuestDataToUser`) and resumable audio downloads via HTTP Range (`.part` to `.bin`).
* [**Stitch Implementation Verification** (SPEC-DESIGN-001)](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/design/VibeAudio-Stitch-Implementation-Verification.md)  
  Visual QA feedback loop and 8-screen inspection rubric for Playwright screenshot comparison.

### 3.3 Backend, Security & API Implementation
* [**Backend Hybrid API Specification** (SPEC-API-001)](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/implementation/VibeAudio-Backend-Hybrid-API-Spec.md)  
  Full OpenAPI 3.1 contract for all 9 `/api/v1` REST endpoints across Cloudflare Workers and AWS Lambda.
* [**Backend Security Baseline** (SEC-BASE-001)](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/security/VibeAudio-Backend-Security-Baseline.md)  
  Remediation blueprints for the open SSRF proxy, unauthenticated progress writes (BOLA), hardcoded bypass credentials, wildcard CORS, and package dependencies.
* [**API Migration Plan** (PLAN-MIG-001)](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/implementation/VibeAudio-API-Migration-Plan.md)  
  4-phase zero-downtime migration strategy from raw Lambda URLs to the `/api/v1` edge router.
* [**Sanctuary Vertical Slice** (SPEC-SLICE-001)](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/implementation/VibeAudio-Sanctuary-Vertical-Slice.md)  
  End-to-end specification for the first testable integration experiment across edge catalog, authenticated progress, and media streaming.

### 3.4 Quality Assurance & Release Gates
* [**Testing Strategy** (QA-STRAT-001)](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/qa/VibeAudio-Testing-Strategy.md)  
  7-level testing pyramid, contract assertions, and subsystem invariant matrices.
* [**Playwright Test Specification** (QA-E2E-001)](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/qa/VibeAudio-Playwright-Test-Spec.md)  
  Browser matrix (Chromium, WebKit, Firefox, Mobile), static test server fixtures, network mocking, and test suite definitions.
* [**Release Gates** (QA-GATES-001)](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/qa/VibeAudio-Release-Gates.md)  
  Objective pass/fail criteria across Gates 0 through 9 governing production release readiness.

### 3.5 Agent Orchestration & Execution
* [**Jules Execution Protocol** (AGENT-JULES-001)](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/agents/VibeAudio-Jules-Execution-Protocol.md)  
  Contract schema, Antigravity $\leftrightarrow$ Jules collaboration lifecycle, stop triggers, and rejection rules for autonomous VM implementation.
* [**Jules Task Catalog & Initial Experiments** (AGENT-CAT-001)](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/agents/VibeAudio-Jules-Task-Catalog.md)  
  22 categorized tasks across 5 tracks with copy-paste prompts for the first 3 real Jules experiments (`EXP-01`, `EXP-02`, `EXP-03`).
* [**Execution Roadmap** (ROADMAP-001)](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/implementation/VibeAudio-Execution-Roadmap.md)  
  Phase 0 through Phase 12 execution plan with tasks, owners, test requirements, and exit criteria.
* [**Implementation Dependency Graph** (GRAPH-001)](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/implementation/VibeAudio-Implementation-Dependency-Graph.md)  
  Mermaid and ASCII dependency charts defining non-blocking parallel tracks (Security, Design System, Playwright, Jules).

---

## 4. How to Execute Work

Implementation proceeds strictly along the documented roadmap:

```text
[Phase 0: Security & Baseline] ──> [Phase 1: Design Tokens] ──> [Phase 2: Frontend Stores]
               │                                                          │
               ▼                                                          ▼
[Phase 4: Hybrid Backend Edge] <──────────────────────────── [Phase 3: Offline & Resumable]
               │
               ▼
[Phase 5: Playwright & E2E]    ──> [Phase 6: Vertical Slice] ──> [Phase 12: Production Hardening]
```

To dispatch tasks to **Google Jules**, consult [`docs/agents/VibeAudio-Jules-Task-Catalog.md`](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/agents/VibeAudio-Jules-Task-Catalog.md) and adhere to the contract schema defined in [`docs/agents/VibeAudio-Jules-Execution-Protocol.md`](file:///c:/Users/Suraj/Documents/Antigravity/VibeAudio/docs/agents/VibeAudio-Jules-Execution-Protocol.md).
