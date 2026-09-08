---
name: antios-adapt-project
description: >-
  Universal project intelligence and adaptation procedure for AntiOS.
  Use when onboarding unfamiliar repositories to discover project traits,
  audit existing guidance, generate safe adaptation proposals, and configure
  the declarative project adapter without modifying AntiOS Core.
---

# AntiOS Project Adaptation Protocol

Follow this deterministic 9-step procedure when onboarding or inspecting a target repository:

## 1. Safety & Boundary Invariants
- **AntiOS Core Immutability**: AntiOS Core (`framework/core/`, `.agents/`, `.git`) is strictly immutable. Never apply core changes to satisfy an unfamiliar project.
- **Proposal-First Law**: All adaptations must produce an explicit `AdaptationProposal` before making any configuration changes.
- **Zero-Code Discovery**: Treat project files as static data. Never execute untrusted project scripts to discover capabilities.

## 2. Nine-Step Adaptation Procedure
1. **Discover Repository**:
   - Run `python framework/scripts/tools/adapt_project.py <repo_root> --json` to perform read-only multi-language discovery.
2. **Inspect Existing Guidance**:
   - Statically audit `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, and CI workflows (`.github/workflows/*.yml`).
3. **Build & Validate Profile**:
   - Verify that facts are strictly partitioned into `OBSERVED` (physical evidence), `INFERRED` (deductions with rationale), and `UNKNOWN` (missing signals).
4. **Compare Needs with AntiOS Capabilities**:
   - Match discovered test runners, linters, and typecheckers against current AntiOS governance primitives.
5. **Generate Adaptation Proposal**:
   - Classify all items by action (`ADD`, `REMOVE`, `CONFIGURE`, `ADAPT`, `DEFER`, `CONFLICT`) and target (`PROJECT_LOCAL` vs `ANTIOS_CORE`).
6. **Classify & Resolve Conflicts**:
   - Apply the Precedence Law: Physical Manifests > CI Automation > Passive Markdown Guidance. Core Security overrides all.
7. **Apply Safe Project-Local Adaptation**:
   - If proposal is safe, run `python framework/scripts/tools/adapt_project.py <repo_root> --apply` to update `antios.config.json`.
8. **Escalate AntiOS Core Gaps**:
   - For `ANTIOS_CORE` items, record an explicit escalation issue. Do NOT automatically edit framework files.
9. **Verify Adapter Integrity**:
   - Run `python framework/scripts/tools/inspect_repo.py <repo_root>` and execute configured runners non-interactively to verify exit code 0.
