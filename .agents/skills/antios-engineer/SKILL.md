---
name: antios-engineer
description: >-
  Universal engineering workflow policy for projects under AntiOS governance.
  Use when planning, implementing, modifying, or verifying features, bug fixes,
  refactors, and maintenance tasks across any software stack.
---

# AntiOS Universal Engineering Policy

You operate under **AntiOS Core** governance. Follow this policy for all engineering tasks.

## 1. Safety Boundaries & Immutability
- **Self-Protection**: NEVER edit `.agents/` or `framework/` directly via IDE tools.
- **Upstream Immutability**: NEVER edit domain cores declared in `protected_domain_paths` in `antios.config.json`.
- **Same Change Set**: Code modifications and documentation updates MUST be committed together.

## 2. Risk Tiering & Delegation Matrix
Assess the risk tier before implementing:
- **Low Risk** (typos, markdown documentation, formatting): Solo execution allowed. Local test check; no subagent needed.
- **Medium Risk** (isolated UI fixes, standard feature additions): Primary agent implements and self-verifies with native tests.
- **High Risk** (state machines, persistence/schema, security hooks, packaging): **MANDATORY MAKER-CHECKER**.
  - Dispatch an independent verifier via `invoke_subagent` using `TypeName='self'`.
  - Pass minimal explicit dispatch contract:
    ```json
    {
      "dispatch_contract": {
        "task_type": "independent_verification",
        "target_subsystem": "<subsystem_name>",
        "touched_files": ["path/to/file.py"],
        "invariants": ["INV-03", "INV-04", "INV-10"],
        "proving_command": ["python", "-m", "unittest", "tests/..."],
        "instructions": "Audit working tree diff against invariants and execute proving command. Return structured verdict."
      }
    }
    ```
  - Verifier uses the `antios-verifier` skill and returns a structured JSON verdict.
  - **Shallow Depth Law**: Subagent depth must never exceed 2 (Parent -> Child). Subagents must NEVER spawn children.

## 3. The 4-Tier Progressive Wayfinding Ladder
Never perform unguided repository-wide searches (`grep_search`, `find_by_name`). Always proceed through the 4-tier wayfinding ladder:
- **L0: Orientation**: Read `./AGENTS.md` for the Turn-0 constitution, core invariants, verification law, and subsystem index (<250 tokens).
- **L1: Subsystem Navigation**: Query `.agents/routes.json` to identify the authoritative subsystem entrypoint, capabilities, and proving tests.
- **L2: Precision Localization**: Inspect the exact target implementation files and windowed AST symbol slices.
- **L3: Targeted Proving**: Run the subsystem's specific proving test command before and after modifications.

## 4. The Stop Gate Ratchet
Task completion triggers the AntiOS Stop hook, which dynamically discovers and executes configured or manifest-detected test runners across all authorized workspaces.
- Multi-workspace roots are fully supported; tests execute for each enrolled workspace repository.
- The task CANNOT complete unless all physical test processes exit with code 0.
- All unresolved git conflict markers (`<<<<<<< `, `=======`, `>>>>>>> `) must be cleared.

