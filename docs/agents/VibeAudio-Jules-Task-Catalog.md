# VibeAudio Jules Autonomous Task Catalog & Experiment Blueprint
## Document ID: `AGENT-CAT-001`

**Status:** Authoritative Engineering Baseline  
**Version:** 1.0.0  
**Date:** September 2026  
**Lead Authors:** Autonomous Workflow Architect, Senior Backend Lead, QA Automation Specialist  
**Target Repository:** `c:\Users\Suraj\Documents\Antigravity\VibeAudio`  
**Cross-References:** [`AGENT-JULES-001`](./VibeAudio-Jules-Execution-Protocol.md), [`QA-GATES-001`](../qa/VibeAudio-Release-Gates.md), [`ROADMAP-001`](../implementation/VibeAudio-Execution-Roadmap.md)

---

## 1. Task Classification & Safety Taxonomy

Every engineering task in VibeAudio is classified by risk tier to determine whether Google Jules may execute autonomously, requires mandatory Antigravity pre-review, or is strictly prohibited:

| Tier Symbol | Tier Name | Risk Level | Execution Policy |
| :--- | :--- | :--- | :--- |
| 🟢 | **Autonomous** | Low | Jules executes end-to-end, self-tests, and opens PR. Auto-merge if Gate 0-2 pass. |
| 🟡 | **Review Required**| Medium | Jules executes and opens PR. Antigravity performs manual line-by-line review. |
| 🟠 | **Experimental** | High | Architectural slice or multi-file refactor. Requires staging canary verification. |
| 🔴 | **Forbidden** | Critical | **PROHIBITED FOR JULES**. Violates invariants (bundlers, DB engine, credentials). |

---

## 2. Complete 22-Task Catalog

### Track A: Security & Core Infrastructure
1. **TASK-A01 🟢 [Autonomous]**: Remove Hardcoded Bypass Codes (`ADMIN_GOD`, `VIBE2026`) from `backend/lambda/auth.js`.
   - *Scope*: `backend/lambda/auth.js`
   - *Acceptance*: Master codes removed; manual login branch eliminated; 401 returned for unauthenticated calls.
   - *Test*: `node --test tests/auth-security.test.mjs`
2. **TASK-A02 🟡 [Review Required]**: Implement SSRF Domain Allowlist & Header Filtering in `backend/workers/proxymanager.js`.
   - *Scope*: `backend/workers/proxymanager.js`
   - *Acceptance*: Target URL must match allowlisted domains; HTTP 403 for private/unauthorized IPs; Range headers preserved.
   - *Test*: `node --test tests/ssrf-proxy.test.mjs`
3. **TASK-A03 🟡 [Review Required]**: Add Clerk JWKS Verification Middleware to Lambda Progress Handlers.
   - *Scope*: `backend/lambda/saveProgress.js`, `backend/lambda/getProgress.js`, `backend/shared/auth-middleware.js`
   - *Acceptance*: Identity derived strictly from JWT `claims.sub`; query `userId` overrides rejected.
   - *Test*: `node --test tests/progress-auth.test.mjs`
4. **TASK-A04 🟢 [Autonomous]**: Add Missing AWS SDK Dependencies to `backend/package.json`.
   - *Scope*: `backend/package.json`
   - *Acceptance*: `@aws-sdk/client-s3`, `@aws-sdk/s3-request-presigner`, and `jose` added to dependencies.
   - *Test*: `npm --prefix backend ls`
5. **TASK-A05 🟢 [Autonomous]**: Implement Centralized CORS Origin Allowlist Utility.
   - *Scope*: `backend/shared/cors.js`, `backend/lambda/*.js`
   - *Acceptance*: Replaces wildcard `*` with strict regex for `*.vibeaudio.pages.dev` and localhost in dev.
   - *Test*: `node --test tests/cors-policy.test.mjs`
6. **TASK-A06 🟢 [Autonomous]**: Implement Sanitized Error Envelope & Stack Masking Middleware.
   - *Scope*: `backend/shared/error-handler.js`, `backend/lambda/*.js`
   - *Acceptance*: Catch-all wrapper logs full error internally and returns opaque error JSON to caller.
   - *Test*: `node --test tests/error-masking.test.mjs`

### Track B: Design System & Styling (Stitch Alignment)
7. **TASK-B01 🟢 [Autonomous]**: CSS Custom Property Token Harmonization with `.stitch/DESIGN.md`.
   - *Scope*: `frontend/src/css/base.css`
   - *Acceptance*: Standardizes terracotta accent `#C64E00`, sanctuary background `#F5F5F7`, and font-family stacks.
   - *Test*: `node tools/verify-css-tokens.mjs`
8. **TASK-B02 🟢 [Autonomous]**: Remove Deprecated CSS Utilities & Dead Selectors.
   - *Scope*: `frontend/src/css/base.css`, `frontend/src/css/components.css`
   - *Acceptance*: Unused legacy utility classes removed; zero visual regression on home shelf.
   - *Test*: `node --test tests/ui-contracts.test.mjs`
9. **TASK-B03 🟡 [Review Required]**: Align Floating Mini-Player Dock Styling to Stitch Screen 7.
   - *Scope*: `frontend/src/css/player.css`
   - *Acceptance*: Fixed height 62px, 16px bottom float, 2px micro-scrubber, frosted glass backdrop blur.
   - *Test*: `node --test tests/ui-contracts.test.mjs`
10. **TASK-B04 🟡 [Review Required]**: Harmonize Full-Player Aspect Ratio & Scrubber Styling to Stitch Screen 5.
    - *Scope*: `frontend/src/css/player.css`
    - *Acceptance*: 2:3 aspect ratio cover, tactile thumb scrubber, JetBrains Mono timecodes.
    - *Test*: `node --test tests/ui-contracts.test.mjs`
11. **TASK-B05 🟢 [Autonomous]**: Audit and Standardize SVG Icons Sprite Stroke Width (1.85px).
    - *Scope*: `frontend/src/icons/icons.svg`
    - *Acceptance*: All 66 vector symbols adhere to 24x24 viewBox with consistent 1.85px stroke.
    - *Test*: `node --test tests/icon-system.test.mjs`

### Track C: QA Automation & Unit Test Expansion
12. **TASK-C01 🟢 [Autonomous]**: Expand Unit Tests for `progress-model.js` (LWW Freshness & Normalization).
    - *Scope*: `tests/progress-model.test.mjs`
    - *Acceptance*: 100% branch coverage for `compareProgressFreshness()`, `normalizeProgressEntry()`.
    - *Test*: `node --test tests/progress-model.test.mjs`
13. **TASK-C02 🟢 [Autonomous]**: Expand Unit Tests for `user-data.js` (Pending Queue & Storage Keys).
    - *Scope*: `tests/user-data.test.mjs`
    - *Acceptance*: Tests cover local bookmarking, history persistence, and sync queue isolation.
    - *Test*: `node --test tests/user-data.test.mjs`
14. **TASK-C03 🟡 [Review Required]**: Unit Tests for Lambda Handlers with Mock Repository Adapter.
    - *Scope*: `tests/lambda-handlers.test.mjs`
    - *Acceptance*: Simulates GET/PUT progress, catalog scan, and detail lookups against mock repository.
    - *Test*: `node --test tests/lambda-handlers.test.mjs`
15. **TASK-C04 🟡 [Review Required]**: Build Automated Contract Schema Validator for OpenAPI `/api/v1`.
    - *Scope*: `tests/api-contracts.test.mjs`
    - *Acceptance*: Validates request/response JSON payloads against canonical schemas in `SPEC-API-001`.
    - *Test*: `node --test tests/api-contracts.test.mjs`
16. **TASK-C05 🟠 [Experimental]**: Scaffold Playwright Local E2E Runner with Zero-Build Static Server.
    - *Scope*: `playwright.config.ts`, `tests/e2e/fixtures/*`
    - *Acceptance*: Playwright launches headless Chromium against `http-server` on port 8080.
    - *Test*: `npx playwright test --project=chromium-desktop`

### Track D: Frontend Client Modernization & Offline Storage
17. **TASK-D01 🟡 [Review Required]**: Implement Dual-Target API Client in `frontend/src/js/api.js`.
    - *Scope*: `frontend/src/js/api.js`, `frontend/src/js/config.js`
    - *Acceptance*: Supports feature flag toggling between legacy URLs and `/api/v1` with circuit breaker.
    - *Test*: `node --test tests/api-client.test.mjs`
18. **TASK-D02 🟡 [Review Required]**: Implement Guest-to-User Progress Migration Trigger in `auth.js`.
    - *Scope*: `frontend/src/js/auth.js`, `frontend/src/js/api.js`
    - *Acceptance*: On Clerk sign-in event, flushes guest progress to `/api/v1/user/migrate-guest`.
    - *Test*: `node --test tests/guest-migration.test.mjs`
19. **TASK-D03 🟡 [Review Required]**: Resumable Audio Download State Machine in `offline-shelf.js`.
    - *Scope*: `frontend/src/js/offline-shelf.js`
    - *Acceptance*: Resumes interrupted chunk downloads using `Range: bytes=offset-` without restarting.
    - *Test*: `node --test tests/download-state-machine.test.mjs`
20. **TASK-D04 🟢 [Autonomous]**: Service Worker Cache Versioning & Sensitive Route Bypass.
    - *Scope*: `frontend/service-worker.js`
    - *Acceptance*: Bypasses SW cache for `/api/v1/auth/*` and `/api/v1/user/progress`.
    - *Test*: `node --test tests/pwa-manifest-sw.test.mjs`

### Track E: Integration & Edge Gateway
21. **TASK-E01 🟠 [Experimental]**: Cloudflare Worker `/api/v1` Edge Router Implementation.
    - *Scope*: `backend/workers/edge-router.js`
    - *Acceptance*: Implements caching for `/catalog`, streaming proxy with token validation, and rate limiting.
    - *Test*: `node --test tests/edge-router.test.mjs`
22. **TASK-E02 🟠 [Experimental]**: Sanctuary Vertical Slice End-to-End Test Script.
    - *Scope*: `tests/sanctuary-vertical-slice.test.mjs`
    - *Acceptance*: End-to-end integration test verifying catalog fetch, stream seeking, and LWW progress persistence.
    - *Test*: `node --test tests/sanctuary-vertical-slice.test.mjs`

---

## 3. Fully Formed Prompts for the First Three Real Jules Experiments

---

### Experiment 1 (Low Risk): CSS Token Harmonization & Unused CSS Cleanup

```markdown
### TASK CONTRACT: EXP-01 - CSS Token Harmonization & Unused CSS Cleanup

#### 1. CONTEXT
VibeAudio's design system baseline is defined in `.stitch/DESIGN.md` under the "Light Editorial Sanctuary" aesthetic. The current stylesheet `frontend/src/css/base.css` contains legacy color tokens and redundant utility classes that conflict with the Stitch design specification.

#### 2. OBJECTIVE
Harmonize the CSS custom properties in `frontend/src/css/base.css` to match `.stitch/DESIGN.md` exact color hex codes and typography tokens, and remove unused legacy color overrides.

#### 3. FILES IN SCOPE
- frontend/src/css/base.css

#### 4. FILES OUT OF SCOPE
- frontend/src/css/player.css
- frontend/src/css/components.css
- frontend/src/js/*
- frontend/src/pages/app.html
- package.json
- .stitch/*

#### 5. CONSTRAINTS
- Zero build tools. Standard CSS only.
- Do NOT alter class names or IDs used by JavaScript DOM queries.
- Maintain full WCAG AA contrast ratio (> 4.5:1) for all text tokens.

#### 6. ACCEPTANCE CRITERIA
- [ ] Primary accent token `--color-accent` is set to `#C64E00` (Terracotta Amber).
- [ ] Sanctuary canvas token `--color-canvas` is set to `#F5F5F7`.
- [ ] Surface token `--color-surface` is set to `#FFFFFF`.
- [ ] Typography stacks `--font-editorial` and `--font-mono` match Stitch design specs ('Newsreader', serif and 'JetBrains Mono', monospace).
- [ ] Zero syntax errors or missing closing braces.

#### 7. TEST COMMANDS
node --test tests/ui-contracts.test.mjs

#### 8. SECURITY REQUIREMENTS
No external CDN `@import` statements may be introduced into CSS files.

#### 9. VISUAL REQUIREMENTS
Colors must strictly conform to `.stitch/DESIGN.md`:
- Canvas: #F5F5F7
- Surface: #FFFFFF
- Surface Secondary: #F2F2F7
- Text Primary: #1D1D1F
- Text Secondary: #86868B
- Accent: #C64E00

#### 10. DO NOT CHANGE
- Do not change `--player-height-dock: 62px;`
- Do not remove `--color-progress-fill`

#### 11. EXPECTED OUTPUT
- Branch: jules/exp-01-css-token-harmonization
- PR Title: style(tokens): harmonize CSS custom properties with Stitch design system
```

---

### Experiment 2 (Moderate Frontend/Test): Unit Test Suite for `progress-model.js` & `user-data.js`

```markdown
### TASK CONTRACT: EXP-02 - Unit Test Suite for progress-model.js & user-data.js

#### 1. CONTEXT
VibeAudio relies on `progress-model.js` for Last-Write-Wins (LWW) monotonic progress resolution and `user-data.js` for offline queue management. While `tests/progress-model.test.mjs` exists, branch coverage for edge-case timestamp comparisons and data sanitization is incomplete.

#### 2. OBJECTIVE
Expand `tests/progress-model.test.mjs` to achieve 100% branch and edge-case coverage for `compareProgressFreshness` and `normalizeProgressEntry` using Node.js native test runner.

#### 3. FILES IN SCOPE
- tests/progress-model.test.mjs

#### 4. FILES OUT OF SCOPE
- frontend/src/js/progress-model.js
- frontend/src/js/player.js
- frontend/src/js/user-data.js
- package.json

#### 5. CONSTRAINTS
- Zero external test dependencies. Use strictly `node:test` and `node:assert/strict`.
- Tests must be completely deterministic (mock `Date.now()` or provide explicit ISO timestamps).

#### 6. ACCEPTANCE CRITERIA
- [ ] Test case: Comparing identical timestamps returns 0.
- [ ] Test case: Newer ISO 8601 string evaluates as fresher than older string.
- [ ] Test case: Missing timestamp in entry A falls back safely against valid timestamp in entry B.
- [ ] Test case: `normalizeProgressEntry` clamps negative `currentTime` and `chapterIndex` to 0.
- [ ] Test case: Auto-completion flag `currentChapterFinished` sets to `true` when `currentTime >= totalDuration * 0.98`.
- [ ] 100% of tests pass cleanly.

#### 7. TEST COMMANDS
node --test tests/progress-model.test.mjs

#### 8. SECURITY REQUIREMENTS
Zero exposure of environment variables or sensitive tokens in test assertions.

#### 9. VISUAL REQUIREMENTS
N/A (Headless Unit Tests).

#### 10. DO NOT CHANGE
- Do not modify source file `frontend/src/js/progress-model.js` (this is a test-only task).

#### 11. EXPECTED OUTPUT
- Branch: jules/exp-02-progress-unit-tests
- PR Title: test(progress): comprehensive branch coverage for progress model and freshness
```

---

### Experiment 3 (Controlled Backend): Unit Tests & Parameter Validation for Lambda Handlers

```markdown
### TASK CONTRACT: EXP-03 - Lambda Handler Unit Tests & Input Validation with Mock DynamoDB

#### 1. CONTEXT
Backend Lambda handlers `saveProgress.js` and `getProgress.js` currently parse inputs without schema validation and rely on direct DynamoDB client connections. We need unit tests that verify parameter validation and error handling using a mock database client without touching real AWS services.

#### 2. OBJECTIVE
Create `tests/lambda-handlers.test.mjs` to test input validation, CORS headers, status codes, and error formatting for `saveProgress.js` and `getProgress.js` against mocked DynamoDB Document Client calls.

#### 3. FILES IN SCOPE
- tests/lambda-handlers.test.mjs

#### 4. FILES OUT OF SCOPE
- backend/lambda/saveProgress.js
- backend/lambda/getProgress.js
- backend/package.json
- frontend/*

#### 5. CONSTRAINTS
- Database selection is intentionally deferred. Use in-memory mocks for all database commands.
- Zero network calls during test execution.
- Use strictly native Node.js test runner (`node:test`, `node:assert/strict`).

#### 6. ACCEPTANCE CRITERIA
- [ ] Test case: Invoking `saveProgress` with empty body returns HTTP 400 with standard error schema.
- [ ] Test case: Invoking `saveProgress` with missing `bookId` returns HTTP 400.
- [ ] Test case: Invoking `getProgress` with missing `userId` returns HTTP 400.
- [ ] Test case: Database driver rejection simulates internal error and verifies error masking behavior.
- [ ] All test assertions pass without requiring AWS credentials or local server running.

#### 7. TEST COMMANDS
node --test tests/lambda-handlers.test.mjs

#### 8. SECURITY REQUIREMENTS
Never include real AWS access keys, secret keys, or tokens in test mocks.

#### 9. VISUAL REQUIREMENTS
N/A.

#### 10. DO NOT CHANGE
- Do not edit any files in `backend/lambda/` during this test-authoring task.

#### 11. EXPECTED OUTPUT
- Branch: jules/exp-03-lambda-unit-tests
- PR Title: test(backend): unit test suite and input validation assertions for lambda handlers
```
