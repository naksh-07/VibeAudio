---
name: antios-debug
description: >-
  Systematic root-cause debugging skill for AntiOS projects.
  Use when diagnosing failing tests, runtime crashes, Stop Gate rejections,
  or complex bugs to isolate causes, reproduce deterministically, and apply minimal fixes.
---

# AntiOS Systematic Debugging Protocol

You are diagnosing an issue under **AntiOS Core** governance.
Follow this deterministic protocol to prevent speculative patching and regressions.

## 1. Safety & Boundary Rules
- **Never modify protected cores**: Governance (`.agents/`, `framework/`) and configured domain cores are immutable.
- **Fail-Closed Principle**: Do not assume environment errors are test passes.
- **Evidence Hierarchy**: A bug is only fixed when demonstrated by a passing test execution (Exit Code 0).

## 2. Five-Step Debugging Procedure
1. **Locate & Reproduce Deterministically**:
   - Run `python framework/scripts/tools/navigate_repo.py --query "<bug/error>"` to resolve the responsible subsystem and covering tests.
   - Run the covering test suite via `run_command` to observe the physical failure directly.
   - If no existing test reproduces the bug, author a minimal reproducing test case before altering code.
2. **Formulate Explicit Hypothesis**:
   - Inspect stack traces, exit codes, and variable states.
   - Write down the hypothesized root cause before modifying code.
3. **Isolate Minimal Cause**:
   - Trace data flow to the exact boundary or invariant failure.
   - Differentiate environment failures (`ENVIRONMENT_UNAVAILABLE`) from logical regressions.
4. **Apply Surgical Patch**:
   - Make the smallest possible edit that addresses the root cause directly.
   - Keep changes strictly within application layers.
5. **Verify & Regress-Check**:
   - Run the reproducing test to confirm the fix.
   - Run the entire project test suite to ensure no regressions.
   - Ensure `docs/ACTIVE_CONTEXT.md` logs the root cause and resolution.
