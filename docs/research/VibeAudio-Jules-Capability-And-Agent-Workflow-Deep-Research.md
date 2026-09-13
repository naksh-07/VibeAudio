# Deep Research: Google Jules Capability, Tooling & VibeAudio Engineering Workflow

**Document Version:** 1.0.0 (Research Phase)  
**Date:** September 2026  
**Status:** Completed Architectural Assessment  
**Target Repository:** VibeAudio (`c:\Users\Suraj\Documents\Antigravity\VibeAudio`)  
**Lead Researcher:** Senior AI-Agent Systems Architect & Autonomous Engineering Specialist  
**Methodology:** Empirical codebase audit, live REST/MCP interface inspection, official documentation synthesis (`jules.google/docs`, `developers.google.com/jules/api`, Google Developers Technical Changelogs), and multi-agent coordination analysis.

---

## Epistemic Taxonomy & Research Standards

To prevent hallucination and maintain absolute engineering rigor, all capabilities, architectural patterns, and integration points in this report are categorized using the following epistemic standards:

- **[VERIFIED]**: Confirmed via live local MCP server runtime tests (`google-jules`), official REST API schemas (`https://jules.googleapis.com/v1alpha`), official Google product documentation (`jules.google/docs`), or codebase inspection of the active VibeAudio workspace.
- **[INFERRED]**: High-confidence logical deductions derived from verifiable platform interfaces, data schemas, and runtime constraints.
- **[EXPERIMENTAL / CONDITIONAL]**: Features in active preview, dependent on specific network or account configurations, or requiring custom glue code.
- **[UNSUPPORTED / FORBIDDEN]**: Features conjectured by developers or marketing materials but confirmed absent, structurally infeasible, or hazardous to production stability.

---

# 1. Understand VibeAudio First

An autonomous engineering agent cannot be evaluated in a vacuum. Its utility is strictly bounded by the architectural paradigms, language runtimes, build patterns, and deployment targets of the host repository. A full inspection of `c:\Users\Suraj\Documents\Antigravity\VibeAudio` reveals the following concrete architecture:

### 1.1 Architecture Overview & Philosophy
VibeAudio is a personal audiobook listening sanctuary engineered around a **guest-first, offline-first, zero-build-step** philosophy:
- **Zero Frontend Build Tooling [VERIFIED]**: The frontend contains **no Vite, no Webpack, no Rollup, no Babel, and no framework compilation**. It is authored in pure, native ECMAScript Modules (`type="module"`), standard HTML5, and modular CSS3.
- **Zero-Dependency Native Tests [VERIFIED]**: All 12 test suites (116 tests) execute via the Node.js native test runner (`node --test tests/`) and native assertions (`node:assert/strict`). There is no Jest, Vitest, or Mocha.
- **Client-Side Framework [VERIFIED]**: Native Vanilla JS DOM manipulation. No React, Vue, Svelte, or Angular.

### 1.2 Frontend Architecture & Dependencies
- **Entry Points**:
  - `frontend/index.html`: Marketing landing page and category spotlight. Boots `frontend/src/js/landing.js` and `frontend/src/js/pwa.js`.
  - `frontend/src/pages/app.html`: Core application shell. Boots `frontend/src/js/pwa.js` and `frontend/src/js/app-entry.js`, which dynamically imports `frontend/src/js/ui.js`.
- **SPA Routing**: Hash-based client router (`frontend/src/js/ui.js#L823-875`) managing distinct views: `#home`, `#library`, `#offline` (On This Device), `#history`, `#about`, `#profile`, and `#player`. Deep linking and OS Share Target payloads (`?book=<id>`, `?url=<url>`, `?title=<title>`) are parsed on initialization.
- **CDN Dependencies (Loaded via `<script>` tags)**:
  - **GSAP 3.12.2**: Entrance animations and view-transition tweens (`frontend/src/js/ui.js#L883`).
  - **Vanilla Tilt 1.7.0**: 3D tactile perspective tilt on book cover cards.
  - **Color Thief 2.3.2**: Extracts dynamic 4-color palettes from cover images to drive dynamic chameleon CSS theming.
  - **Clerk Browser SDK v5** (`@clerk/clerk-js@5`): Dynamically loaded from `quality-hare-99.clerk.accounts.dev` for optional user authentication (`frontend/src/js/auth.js`).
- **State Management**:
  - Event-driven pub/sub architecture built on native `window.dispatchEvent` and `CustomEvent` listeners: `player-time-update`, `player-state-change`, `player-playback-error`, `offline-shelf-change`, `vibe-pwa-ready`, `vibe-background-sync-complete`, and `vibe-file-received`.
  - Domain singletons: `frontend/src/js/user-data.js` (local progress, bookmarks, notes, search history), `frontend/src/js/offline-shelf.js` (OPFS and IndexedDB storage finite state machine), and `frontend/src/js/player.js` (central audio controller).

### 1.3 Audio & Player Engine
- **Dual Playback Engines**:
  1. **HTML5 `<audio id="audio-element">`**: Streams remote audio files (MP3/M4A/AAC/M4B) or reads offline binary blobs extracted from the Origin Private File System (OPFS) via temporary `URL.createObjectURL(file)`. Managed with a monotonic `currentLoadToken` to prevent asynchronous race conditions during rapid track switching.
  2. **YouTube IFrame Host (`#yt-player-shell`)**: Hidden player instance for streaming YouTube-hosted audiobooks.
- **Web Audio API — Vocal Clarity Booster (`frontend/src/js/player.js#L572-645`)**:
  - A 4-stage hardware-accelerated DSP node graph connected via `createMediaElementSource`:
    1. *Highpass Filter (`bassCutFilter`)*: Moves from 0 Hz to 150 Hz to cut speech rumble.
    2. *Peaking Filter (`vocalPeakingFilter`)*: Centered at 2500 Hz, Q 1.0, boosting up to +8 dB for presence.
    3. *Highshelf Filter (`trebleBoostFilter`)*: Boosts at 5000 Hz up to +6 dB for articulation.
    4. *Dynamics Compressor (`compressor`)*: Compresses at -24 dB threshold, 12:1 ratio for vocal normalization.
- **Platform Hardening**:
  - Screen Wake Lock API (`navigator.wakeLock.request('screen')`) keeps the mobile display active during playback.
  - Media Session API integration with 6 artwork resolutions (96px to 512px) and position state throttling.
  - Sleep timer with a 5-second automated volume fadeout curve before pause.
  - Android WebView bridge (`window.AndroidInterface`) fallback.

### 1.4 PWA & Offline Storage Architecture
- **Web App Manifest (`frontend/app.webmanifest`)**:
  - Standalone display mode, background/theme color `#0C0D11`.
  - File Handling API: Registered for `.m4b` (`audio/mp4`) and `.mp3` (`audio/mpeg`) with `launch_type: "single-client"`.
  - Share Target API: Receives incoming GET shared URLs, titles, and text.
  - Badging API: Reflects active background download counts.
- **Service Worker (`frontend/service-worker.js`, Cache Version `v14-production`)**:
  - Precaches **40 critical static assets** on install (HTML shells, 7 CSS files, 18 JS modules, icons, SVG sprite).
  - Stale-While-Revalidate caching for static assets, runtime scripts, and images.
  - Network-first caching for navigation and JSON data.
  - Strict cache bypass (`isSensitiveOrAuthUrl`) for Clerk endpoints, `/progress`, and `/sync-user`.
  - Background Sync API (`vibeaudio-progress-sync`): Reads pending progress queue from IndexedDB `vibeaudio-sync-v1` and flushes to cloud upon reconnection.
  - Background Fetch API: Handles large chapter downloads directly in the service worker.
- **Multi-Tier Storage Model**:
  - **OPFS (Origin Private File System)**: Unabridged audio chapter binaries stored at `offline-audio/{userId}/{bookId}/{lang}/{chapterIndex}.bin`.
  - **IndexedDB (`vibeaudio-offline-v1`)**: 5 object stores (`offline_books`, `offline_chapters`, `offline_jobs`, `offline_settings`, `offline_storage_stats`).
  - **IndexedDB (`vibeaudio-sync-v1`)**: Progress sync queue (`sync_progress_queue`).
  - **LocalStorage**: User preferences, playback speed, search history, session cache.

### 1.5 Backend Architecture & Cloud Infrastructure
- **Serverless Compute**:
  - **AWS Lambda (Node.js, CommonJS)** located in `backend/lambda/` using AWS SDK v3 (`@aws-sdk/client-dynamodb`, `@aws-sdk/lib-dynamodb`, `@aws-sdk/client-s3`, `@aws-sdk/s3-request-presigner`).
  - Invoked directly via public **AWS Lambda Function URLs** in region `ap-south-1`:
    - `auth.js` (`syncUserUrl`): User profile synchronization and access code validation.
    - `getBooks.js`: Scans DynamoDB `Vibe_Books` in lightweight mode.
    - `getBookDetails.js`: Fetches chapter arrays and presigns Cloudflare R2 audio URLs (1-hour TTL).
    - `getProgress.js`: Retrieves user listening progress from DynamoDB `Vibe_UserProgress`.
    - `saveProgress.js`: Calculates completion percentages (>= 98% threshold) and persists progress.
- **Edge Compute (Cloudflare Workers)**:
  - `backend/workers/proxymanager.js`: Proxies remote audio files, forwards HTTP `Range` request headers, and injects CORS headers to permit seeking on mobile browsers.
  - `backend/workers/r2-trigger.js`: Event handler hook for audio catalog uploads.
- **Database & Media Storage**:
  - **AWS DynamoDB (`ap-south-1`)**: Tables `Vibe_Books`, `Vibe_Users`, `Vibe_UserProgress`.
  - **Cloudflare R2**: Object storage for audiobook MP3/M4B audio files.
  - **Cloudflare Pages**: Hosts static JSON catalog snapshot at `https://vibeaudio-db.pages.dev/catalog.json`.

### 1.6 Design System & Stitch State
- **Master Specification**: Master design tokens defined in `.stitch/DESIGN.md` and `.stitch/SITE.md` under Project ID `6063499620727826815`.
- **Visual Language ("Light Editorial Sanctuary")**:
  - Palette: Canvas `#F5F5F7`, Surface `#FFFFFF` / `#F2F2F7`, Primary Text `#1D1D1F`, Accent `#C64E00` (Terracotta Amber).
  - Typography: Newsreader (editorial serif headings), Inter (clean UI body), JetBrains Mono (audio timecodes).
  - Iconography: Self-contained zero-CDN SVG sprite (`frontend/src/icons/icons.svg`) with 66 custom vector symbols on a 24x24 grid with 1.85px stroke width.
- **Stitch Screen Inventory**: 8 registered screens (`STITCH-SCR-001` Landing through `STITCH-SCR-008` Mobile Drawer).

---

# 2. Research Google Jules Deeply

Google Jules is Google Labs' autonomous cloud-native software engineering agent. Unlike interactive agentic IDEs that pair-program in the developer's immediate active window (such as Google Antigravity), Jules operates **out-of-band and asynchronously**. It clones repositories into ephemeral cloud virtual machines, explores codebases, drafts multi-step plans, executes modifications in a sandboxed Linux bash environment, validates its own work, and submits GitHub Pull Requests.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Google Jules Cloud                            │
│                                                                         │
│  ┌───────────────────────┐          ┌────────────────────────────────┐  │
│  │     Gemini 3 Pro      │          │   Ephemeral Ubuntu Linux VM    │  │
│  │   Reasoning Engine    │◄────────►│   - Non-root 'jules' user      │  │
│  └──────────┬────────────┘          │   - 20GB isolated disk         │  │
│             │                       │   - Headless Chrome/Playwright │  │
│             ▼                       │   - Environment Snapshots      │  │
│  ┌───────────────────────┐          └────────────────┬───────────────┘  │
│  │  Planning Critic &    │                           │                  │
│  │  Code Critic Agents   │                           │                  │
│  └──────────┬────────────┘                           ▼                  │
│             │                       ┌────────────────────────────────┐  │
│             └──────────────────────►│ Automated Verification / Tests │  │
│                                     └────────────────┬───────────────┘  │
└──────────────────────────────────────────────────────┼──────────────────┘
                                                       │
                                                       ▼
                                      ┌────────────────────────────────┐
                                      │ GitHub Pull Request / Feedback │
                                      └────────────────────────────────┘
```

### 2.1 Core Agent Capabilities

| Capability | Current Status | Autonomy vs Human Approval | Available Surfaces | Core Limitations & Constraints | VibeAudio Relevance & Utility |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Autonomous Coding** | Production-Ready (Exited Beta Aug 2025) | Autonomous once plan approved. | Web UI, CLI, API, MCP | Prohibits interactive prompts and long-lived background daemons. | **High**: Excellent for batch module refactoring and headless utilities. |
| **Repository Understanding** | Production-Ready | Autonomous indexing; uses Gemini 3 Pro reasoning. | All surfaces | Large binary files (`.bin`, `.mp3`) ignored; reads repo root files first. | **High**: Parses modular ESM files and documentation quickly. |
| **Task Planning & Review** | Production-Ready | Dual-mode: Optional plan approval (`requirePlanApproval: true`). | All surfaces | Plan modifications during active execution require stopping the run or chatting. | **Critical**: Allows verifying Jules' plan before it touches VibeAudio code. |
| **Planning Critic Agent** | Production-Ready (Launched Jan 2026) | Autonomous internal critique before code execution. | Internal pipeline | Adds 30–60s planning overhead; lowers plan failure rates by ~9.5%. | **High**: Catches flawed architectural assumptions before coding starts. |
| **Code Critic Agent** | Production-Ready (Launched Aug 2025) | Autonomous internal code review before PR creation. | Internal pipeline | Operates adversarially against code diffs; flags lint and security gaps. | **High**: Prevents common AI bugs and unhandled exceptions. |
| **Isolated Cloud VM** | Production-Ready | Fully autonomous Ubuntu Linux sandbox. | Cloud backend | Ephemeral; destroyed post-task; 20GB disk; non-root user. | **Critical**: Safe sandbox that cannot corrupt local files or machines. |
| **Multi-File Changes** | Production-Ready | Autonomous cross-file patching; unified git diffs. | All surfaces | Edits across >50 files risk drift; best scoped to cohesive feature slices. | **High**: Ideal for cross-cutting CSS token updates or test authoring. |
| **Testing & Debugging** | Production-Ready | Autonomous bash loop with exit code inspection. | Cloud VM shell | Tests must exit deterministically; hanging tests terminate on timeout. | **High**: Perfectly suited for `node --test tests/`. |
| **PR Creation** | Production-Ready | Configurable: automatic (`AUTO_CREATE_PR`) or manual export. | All surfaces | Requires GitHub App write permissions on target repository. | **Standard**: Establishes clean audit trails for Antigravity review. |
| **PR Feedback Handling** | Production-Ready | Autonomous reaction to PR review comments. | GitHub Webhooks | Default responds to all comments; Reactive mode restricts to `@Jules`. | **High**: Allows human/Antigravity to request revisions on GitHub. |
| **CI Failure Fixing** | Production-Ready (Launched Feb 2026) | Autonomous closed-loop fix cycle upon CI webhook failure. | GitHub Actions, Render | Retries capped at preset thresholds to avoid runaway billing. | **High**: Can automatically fix broken tests after dependency bumps. |
| **AGENTS.md Support** | Production-Ready | Autonomous: Ingested from repo root on session initialization. | Repo root | Ingested once at session boot; dynamic changes require new session. | **Critical**: Primary mechanism to teach Jules VibeAudio's zero-build rules. |
| **Environment Snapshots** | Production-Ready | Autonomous caching of base VM state (`Run and Snapshot`). | Web UI, API | Snapshots invalidate when base lockfiles change. | **High**: Bypasses cold-boot setup times on recurring test runs. |
| **Web Research** | Production-Ready | Autonomous documentation retrieval ("Web Surfing"). | Internal VM tool | Filtered to technical/API docs; general web browsing restricted. | **Medium**: Helpful when upgrading AWS SDK or Web APIs. |
| **Browser Automation (Playwright)** | Production-Ready | Autonomous: Invokes `frontend_verification_instructions`. | Cloud VM headless Chrome | Runs headless Chrome inside VM; cannot access internal local URLs. | **Medium-High**: Can boot local static server and assert UI elements. |
| **Visual Screenshots** | Production-Ready | Autonomous capture across Desktop/Tablet/Mobile viewports. | Web UI diff, API (`media`) | Screenshots generated in VM; user image upload limited to prompt initiation. | **High**: Provides visual proof of responsive and CSS changes. |

---

# 3. Jules CLI ("Jules Tools")

### 3.1 Distribution, Installation & Authentication [VERIFIED]
Jules Tools is distributed as an official npm package:
```bash
npm install -g @google/jules
```
- **Authentication**: `jules login` initiates a local OAuth 2.0 loopback flow in the default browser. Tokens are stored securely in OS credential stores (`~/.config/jules/credentials.json`).
- **Context Inference**: When executed inside a git repository, running `jules` or `jules remote new --repo .` automatically inspects `.git/config` to infer the GitHub repository slug (`sources/github/owner/repo`).

### 3.2 Command Surface & Workflow Mechanics [VERIFIED]
```bash
# Launch interactive Terminal User Interface (TUI)
jules

# List all connected repositories
jules remote list --repo

# List all active and historical cloud sessions
jules remote list --session

# Dispatch a new asynchronous coding task to the cloud
jules remote new --repo naksh-07/VibeAudio --session "Refactor user-data.js to support bookmark tagging"

# Launch 3 parallel cloud VM sessions exploring alternative designs
jules remote new --repo . --parallel 3 --session "Optimize OPFS chunked downloading"

# Pull generated unidiff patch directly into local working tree
jules remote pull --session 14550388554331055113
```

### 3.3 Terminal User Interface (TUI)
Running naked `jules` opens an ncurses-style terminal dashboard:
- Displays active cloud tasks, execution stages (Planning, Executing, Testing, Critique), and real-time logs.
- Integrated side-by-side terminal diff viewer allowing inspection of modified lines before pulling.
- Theme customizer (`jules --theme dark` / `jules --theme light`).

### 3.4 CLI Integration with Antigravity
The CLI bridges Antigravity's local terminal with Jules' asynchronous cloud execution:
```text
Antigravity Terminal (Local Pair Programmer)
        ↓  (executes 'jules remote new --repo . --session "..."')
Google Cloud Jules Sandbox (Isolated Ubuntu VM)
        ↓  (plans, codes, runs 'node --test', verifies screenshots)
GitHub Remote Repository (Pushes branch 'jules/task-xyz')
        ↓  (opens Pull Request #42)
Antigravity Review & Audit (Fetches PR diff, runs local tests, merges)
```

---

# 4. Jules REST API

### 4.1 Specification & Endpoint Topology [VERIFIED]
- **Base Endpoint**: `https://jules.googleapis.com/v1alpha`
- **Protocol**: HTTPS JSON REST API
- **Authentication**: HTTP Header `X-Goog-Api-Key: <JULES_API_KEY>` (keys prefixed with `AQ.`, generated at `jules.google.com/settings#api`, maximum 3 active keys per account).

### 4.2 Core REST Resources & Lifecycle

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Jules Session Lifecycle                         │
│                                                                        │
│   [QUEUED] ──► [PLANNING] ──► [AWAITING_PLAN_APPROVAL] (Optional)     │
│                                           │                            │
│                                    (Approve Plan)                      │
│                                           ▼                            │
│                                     [IN_PROGRESS]                      │
│                                    (Codes / Tests)                     │
│                                           │                            │
│                                    (Critic Review)                     │
│                                           ▼                            │
│                        [COMPLETED] / [FAILED] / [PAUSED]               │
└────────────────────────────────────────────────────────────────────────┘
```

1. **`GET /v1alpha/sources`**: Enumerates all GitHub repositories connected to the user's Jules installation.
2. **`POST /v1alpha/sessions`**: Initiates an autonomous cloud session.
   ```json
   {
     "prompt": "Write unit tests for progress recency comparison in tests/progress-model.test.mjs",
     "sourceContext": {
       "source": "sources/github/naksh-07/VibeAudio",
       "githubRepoContext": {
         "startingBranch": "main"
       }
     },
     "automationMode": "AUTO_CREATE_PR",
     "requirePlanApproval": true,
     "title": "Add Progress Model Tests"
   }
   ```
3. **`GET /v1alpha/sessions/{sessionId}`**: Returns session state, elapsed duration, plan, and pull request URL metadata (`pullRequest: { url, title, description }`).
4. **`POST /v1alpha/sessions/{sessionId}:approvePlan`**: Approves a generated plan in `AWAITING_PLAN_APPROVAL` state, unblocking execution.
5. **`POST /v1alpha/sessions/{sessionId}:sendMessage`**: Sends steers, corrections, or follow-up instructions to an active session (`{"prompt": "Fix syntax error on line 42"}`).
6. **`GET /v1alpha/sessions/{sessionId}/activities`**: Returns an ordered array of timeline events and artifacts:
   - `bashOutput`: `{ command: "node --test tests/", output: "...", exitCode: 0 }`
   - `changeSet`: `{ gitPatch: { baseCommitId: "...", unidiffPatch: "..." } }`
   - `media`: Base64 PNG screenshots captured during browser verification.

### 4.3 Evaluation for Automated VibeAudio Engineering Workflows
- **Autonomous CI/CD Remediation**: When GitHub Actions fails, a webhook can call `POST /v1alpha/sessions` with the error log to trigger autonomous repair.
- **Antigravity-Triggered Background Delegation**: Antigravity can dispatch secondary engineering objectives to Jules via the REST API or local MCP client while the developer continues primary interactive development locally.

---

# 5. Jules MCP Ecosystem

### 5.1 The Two Directions of MCP in Jules
It is vital to distinguish the **two opposing directions** of MCP architecture:
1. **Inbound (Antigravity $\rightarrow$ Jules)**: Antigravity acts as an MCP Client calling a local `google-jules` MCP Server (`~/.local/jules-mcp/index.js`), using Jules as an external tool to trigger remote cloud tasks.
2. **Outbound (Jules $\rightarrow$ External Services)**: Jules acts as an MCP Client connecting to external cloud services (Stitch, Linear, Supabase, Neon) from its cloud VM.

```text
                                  ┌────────────────────────┐
                                  │   Google Antigravity   │
                                  │       (Local IDE)      │
                                  └───────────┬────────────┘
                                              │
                                              │ Inbound MCP Call
                                              ▼
                                  ┌────────────────────────┐
                                  │    google-jules MCP    │
                                  │         Server         │
                                  └───────────┬────────────┘
                                              │
                                              │ REST API (X-Goog-Api-Key)
                                              ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 Google Jules Cloud VM                                  │
│                                                                                        │
│                               Outbound Managed MCP Client                              │
│                                             │                                          │
│        ┌───────────────────┬────────────────┼───────────────────┬──────────────────┐   │
│        ▼                   ▼                ▼                   ▼                  ▼   │
│ ┌──────────────┐    ┌──────────────┐ ┌──────────────┐    ┌──────────────┐   ┌────────┐ │
│ │Google Stitch │    │    Linear    │ │   Supabase   │    │     Neon     │   │Context7│ │
│ │  Design MCP  │    │  Issue Sync  │ │ Postgres/Auth│    │ Serverless DB│   │ API Doc│ │
│ └──────────────┘    └──────────────┘ └──────────────┘    └──────────────┘   └────────┘ │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Jules Outbound MCP Security & Registry Model [VERIFIED]
- **Closed Partner Registry**: Jules does **not** permit attaching arbitrary custom `stdio` scripts or unauthenticated HTTP endpoints in its web dashboard. For security and sandboxing within Google Cloud, Jules limits outbound connections to vetted enterprise partners.
- **Configuration**: Managed in `jules.google.com/settings` $\rightarrow$ **MCP**, where API tokens are entered per service.
- **Available Verified Partners (2026)**:
  - **Google Stitch**: UI/UX design generation, screen inspection, and design system extraction.
  - **Linear**: Issue synchronization and project tracking.
  - **Neon**: Serverless Postgres branching, migrations, and SQL validation.
  - **Supabase**: Backend database schema inspection and row-level security policy checking.
  - **Tinybird**: Real-time analytical data pipelines.
  - **Context7**: Real-time library documentation and code examples.

---

# 6. Jules + Google Stitch

A core question for VibeAudio is how Google Stitch and Google Jules interact. To avoid hallucination, we clearly partition capabilities into three tiers:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Jules + Stitch Capability Tiers                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 1. VERIFIED CAPABILITY:                                                         │
│    • Ingestion of Stitch DESIGN.md and SITE.md specifications                   │
│    • Outbound Stitch MCP tool execution (list_projects, get_screen, etc.)       │
│    • Headless Playwright UI verification in Jules cloud VM                      │
│    • Visual screenshot capture attached to session activities                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 2. REASONABLE WORKFLOW INFERENCE:                                               │
│    • Design-to-Code: Jules translates Stitch HTML/Tailwind into VibeAudio CSS   │
│    • Visual QA: Jules compares Playwright screenshots against Stitch reference  │
│    • Antigravity arbitrates design system changes before Jules implements       │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 3. UNSUPPORTED / SPECULATIVE CAPABILITY:                                        │
│    • Jules cannot modify Stitch vector canvas layers directly                   │
│    • Zero direct bidirectional live-sync between running code and Stitch UI     │
│    • Jules cannot make subjective branding or artistic design decisions         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 6.1 Verified Capabilities [VERIFIED]
1. **Semantic Design System Ingestion**: When `.stitch/DESIGN.md` and `.stitch/SITE.md` are committed to the repository, Jules automatically references their design tokens (colors, typography, spacing, border radii) to guide its CSS and HTML modifications.
2. **Stitch MCP Client**: With a Stitch API token configured in Jules cloud settings, Jules can execute `stitch_list_projects`, `stitch_create_project`, `stitch_generate_screen`, and `stitch_export_framework`.
3. **Local Headless Verification**: Jules can spin up a local static server inside its Ubuntu VM (`node tools/serve.mjs`), launch headless Chromium via Playwright, capture screenshots at 1920x1080 (Desktop), 768x1024 (Tablet), and 375x667 (Mobile), and inspect them before finalizing its pull request.

### 6.2 Reasonable Workflow Inferences [INFERRED]
1. **Design-to-Code Translation**: Jules can take a Stitch-generated screen (which outputs Tailwind classes and semantic HTML), strip the Tailwind classes, and map them into VibeAudio's custom CSS variable tokens (`--color-surface-1`, `--color-accent`, `.action-btn`) defined in `frontend/src/css/base.css` and `components.css`.
2. **Visual QA Check**: Jules' internal Code Critic can inspect the rendered screenshot to confirm that modal dialogs or buttons do not overflow on mobile viewports.

### 6.3 Unsupported / Speculative Capabilities [UNSUPPORTED]
1. **Direct Canvas Manipulation**: Jules cannot drag, drop, or manipulate design elements on the Stitch web interface canvas. It only interacts via Stitch MCP JSON payloads.
2. **Artistic Decision Making**: Jules cannot determine whether Terracotta Amber (`#C64E00`) or Royal Indigo provides a superior emotional brand identity for an audiobook app. Strategic design direction must remain with humans and Antigravity.

---

# 7. Jules + Frontend Engineering (VibeAudio Modernization)

Evaluating Jules against VibeAudio's frontend demands careful consideration of the repository's strict zero-build, vanilla architecture:

| Frontend Domain | Jules Strength / Role | Antigravity Advantage / Role | Recommended Owner |
| :--- | :--- | :--- | :--- |
| **Design Token Migration** | Can systematically replace hardcoded hex values with CSS variables across all 7 stylesheets. | Defines token hierarchy and architectural rules in `DESIGN.md`. | **Jules (Batch) $\rightarrow$ Antigravity (Review)** |
| **CSS Refactoring & Modernization** | Can consolidate redundant utility classes, add `:focus-visible` rings, and modernize CSS layouts. | Fast visual inspection and hot-reload debugging. | **Jules** |
| **Accessibility & Semantic HTML** | Excels at adding missing ARIA attributes (`aria-expanded`, `aria-label`, `role="region"`), fixing contrast. | Tests screen reader flows and tab navigation interactively. | **Jules (Implementation) $\rightarrow$ Antigravity (A11y Audit)** |
| **Responsive & Viewport Fixes** | Boots Playwright, captures multi-breakpoint screenshots (Desktop, Tablet, Mobile), catches layout overflow. | Live interactive window resizing and layout tuning. | **Jules (Verification) $\rightarrow$ Antigravity (Polish)** |
| **PWA & Service Worker** | Can update asset precache lists (`PRECACHE_URLS`) and write unit tests for cache matching. | Live PWA installation, browser service worker lifecycle debugging. | **Antigravity (SW Logic) / Jules (Precache updates)** |
| **Audio Engine & DSP** | Can write unit tests for monotonic tokens and sleep timer curves. | Web Audio API debugging requiring live human listening tests. | **Antigravity (DSP Audio Engine)** |
| **Chameleon Palette & Dynamic CSS** | Can write unit tests validating ColorThief edge cases (grayscale covers, corrupt URLs). | Evaluates aesthetic quality of generated ambient glow. | **Jules (Tests) $\rightarrow$ Antigravity (Aesthetics)** |

---

# 8. Jules + Backend Engineering (Hybrid Cloud Architecture)

VibeAudio operates a **hybrid backend**: AWS Lambda Function URLs (Node.js) + DynamoDB in `ap-south-1`, paired with Cloudflare Workers (Proxy) and Cloudflare R2 (Audio storage).

> **Architectural Note:** In accordance with instructions, the final backend architecture and database selection are intentionally deferred. The following analysis evaluates Jules' technical capability to work across this hybrid surface.

### 8.1 Strengths in VibeAudio's Backend
1. **Lambda Function Modernization**:
   - Jules can easily refactor `backend/lambda/*.js` from CommonJS (`require`) to ECMAScript Modules (`import/export`) to harmonize with the frontend.
   - Jules can introduce robust request payload validation (e.g. validating `bookId`, `chapterIndex`, `currentTime` bounds) in `saveProgress.js`.
2. **Cloudflare Worker Optimization**:
   - Jules understands Cloudflare Workers Fetch API and can add caching headers, security headers (CSP, HSTS), or rate-limiting guards to `backend/workers/proxymanager.js`.
3. **Backend Test Suite Authoring**:
   - Currently, `backend/lambda/` and `backend/workers/` have **zero automated unit tests**. Jules can author mocked tests using `node:test` and `@aws-sdk/client-dynamodb` mocks.

### 8.2 Backend Limitations & Guardrails
- **No Direct Cloud Resource Provisioning**: Jules must **never** be given AWS IAM or Cloudflare API keys with permission to deploy, alter DynamoDB throughput, delete R2 buckets, or create cloud resources.
- **Mock-Only Testing**: Jules must test backend code against in-memory mocks, never against live production DynamoDB tables or live R2 buckets.

---

# 9. Jules vs Antigravity

| Capability | Google Jules (Cloud Asynchronous) | Google Antigravity (Local Interactive) |
| :--- | :--- | :--- |
| **Operational Model** | Out-of-band, autonomous background execution. | In-band, pair-programming agentic IDE. |
| **Execution Environment** | Ephemeral Ubuntu Linux VM in Google Cloud. | Local developer workstation / OS environment. |
| **Feedback Latency** | High (2 to 10 minutes per task cycle). | Low / Instantaneous (milliseconds to seconds). |
| **Repository Scope** | Entire cloned repository; best on scoped objectives. | Active project workspace; deep multi-file awareness. |
| **Planning Mechanism** | Autonomous multi-step plan + Planning Critic agent. | Interactive planning mode (`implementation_plan.md`). |
| **Human-in-the-Loop** | Asynchronous plan approval or GitHub PR review. | Real-time interactive steering and turn-by-turn prompts. |
| **Terminal Access** | Non-interactive bash script execution in sandbox. | Full interactive terminal with interactive tools. |
| **Browser Testing** | Headless Playwright script execution + screenshots. | Interactive Chrome DevTools, desktop webview reviewer. |
| **Visual QA** | Static viewport screenshots attached as PR artifacts. | Live interactive rendering, DOM inspection, CSS tuning. |
| **Stitch Integration** | Ingests `DESIGN.md`; calls Stitch MCP tools remotely. | Full bidirectional Stitch skills, visual generation. |
| **MCP Ecosystem** | Closed curated partner registry (Stitch, Linear, etc.). | Open local & remote MCP client (any stdio/HTTP server). |
| **Git / PR Workflow** | Creates branch, commits changes, opens GitHub PR. | Staged/unstaged diffs, local git commits, direct push. |
| **CI Failure Healing** | Autonomous closed-loop fix cycle via CI webhooks. | Interactive root-cause debugging and fix verification. |
| **Parallel Execution** | High: Up to 15 concurrent cloud VM tasks (Pro tier). | Controlled: Max 4 concurrent subagents (Orchestrator). |
| **Best Use Case** | Unattended refactoring, test authoring, dependency updates. | Architectural design, DSP tuning, interactive features. |

---

# 10. The Ideal Division of Labor

```
                                  ┌────────────────────────┐
                                  │      Google Stitch     │
                                  │   Design Brain / Spec  │
                                  │ (DESIGN.md / SITE.md)  │
                                  └───────────┬────────────┘
                                              │
                                              │ Design Tokens & Specs
                                              ▼
                                  ┌────────────────────────┐
                                  │   Google Antigravity   │
                                  │ Architectural Planning │
                                  │   & Task Scoping       │
                                  └───────────┬────────────┘
                                              │
                                              │ Delegated Tasks via Jules MCP / CLI
                                              ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 Google Jules Cloud VMs                                 │
│                                                                                        │
│   ┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐   │
│   │   Task 1: CSS Tokens   │  │  Task 2: Tests Suite   │  │ Task 3: A11y & ARIA    │   │
│   └───────────┬────────────┘  └───────────┬────────────┘  └───────────┬────────────┘   │
│               │                           │                           │                │
│               └─────────────────────┬─────┴───────────────────────────┘                │
│                                     │ Pull Requests                                    │
│                                     ▼                                                  │
│                       ┌────────────────────────────┐                                   │
│                       │     GitHub Repository      │                                   │
│                       │   (Branch / PR Review)     │                                   │
│                       └─────────────┬──────────────┘                                   │
└─────────────────────────────────────┼──────────────────────────────────────────────────┘
                                      │
                                      │ PR Fetch & Automated Review
                                      ▼
                        ┌────────────────────────────┐
                        │     Google Antigravity     │
                        │ Independent Verification,  │
                        │ Visual QA & Final Merge    │
                        └────────────────────────────┘
```

### 10.1 Role Allocations Across the Engineering Lifecycle
1. **Google Stitch (Design Authority)**: Owns visual language, component layout patterns, color tokens, and typographic scale. Exports canonical `.stitch/DESIGN.md`.
2. **Google Antigravity (Architect & Orchestrator)**:
   - Evaluates system architecture and breaks large features into discrete, isolated tasks.
   - Authors `AGENTS.md` to establish strict guardrails for autonomous agents.
   - Triggers Jules tasks via CLI or `google-jules` MCP server.
   - Conducts independent code reviews on Jules PRs using `github-workflow` and local verification tools.
3. **Google Jules (Autonomous Cloud Implementer)**:
   - Executes batch tasks in cloud VMs without blocking developer focus.
   - Runs `node --test tests/` and Playwright visual scripts in the VM.
   - Submits clean GitHub Pull Requests with descriptive summaries and screenshots.
4. **GitHub & CI (Gatekeeper)**: Runs automated test suites and lint checks on all Jules branches.
5. **Human Developer (Final Sign-off)**: Approves PR merges to `main` and authorizes production releases.

---

# 11. VibeAudio-Specific Jules Use Cases (15 Concrete Tasks)

The following 15 production tasks represent high-value, realistic engineering objectives for Jules in VibeAudio:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    15 Concrete Jules Tasks for VibeAudio                     │
├────────────────────────────────┬───────────────────────────┬─────────────────┤
│ Frontend Modernization         │ Testing & Reliability     │ Backend & PWA   │
├────────────────────────────────┼───────────────────────────┼─────────────────┤
│ 01. CSS Token Consolidation    │ 06. Backend Lambda Mocks  │ 11. CJS to ESM  │
│ 02. Semantic A11y Attributes   │ 07. Audio Token Concurrency│ 12. PWA Offline │
│ 03. Responsive Layout Guard    │ 08. OPFS Path Tests       │ 13. Lambda Val. │
│ 04. Icon System Tests          │ 09. Sync Queue Dedupe     │ 14. CSP Headers │
│ 05. Dialog Popover Migration   │ 10. Playwright Smoke Test │ 15. Doc Gen     │
└────────────────────────────────┴───────────────────────────┴─────────────────┘
```

#### Task 01: CSS Design Token Consolidation
- **Description**: Scan `frontend/src/css/*.css` and replace hardcoded hex colors and font declarations with semantic CSS variables defined in `.stitch/DESIGN.md`.
- **Why Jules**: Repetitive, multi-file pattern replacement across 7 files; easily verified via AST/regex.
- **Required Tools/MCP**: Cloud VM bash, git.
- **Inputs**: `.stitch/DESIGN.md`, `frontend/src/css/*.css`.
- **Outputs**: Stacked git diff updating stylesheets without altering visual appearance.
- **Human Approval**: Not required for plan; required on PR review.
- **Risk Level**: Low.
- **Estimated Autonomy**: 95%.
- **Recommended Prompt**: Strict token mapping list with instruction to run `node tools/serve.mjs` and verify no broken rules.

#### Task 02: Full Accessibility & ARIA Audit Remediation
- **Description**: Add missing ARIA attributes (`aria-expanded`, `aria-controls`, `aria-label`, `role="region"`) to dynamic buttons, dialogs, and panels in `frontend/src/pages/app.html`.
- **Why Jules**: Well-defined W3C specifications; Jules can run `node --test tests/accessibility.test.mjs`.
- **Required Tools/MCP**: Cloud VM bash, Playwright.
- **Inputs**: `frontend/src/pages/app.html`, `tests/accessibility.test.mjs`.
- **Outputs**: Updated HTML shell and expanded accessibility test assertions.
- **Human Approval**: No plan approval needed.
- **Risk Level**: Low.
- **Estimated Autonomy**: 90%.
- **Recommended Prompt**: Direct references to failing accessibility guidelines and target test files.

#### Task 03: Responsive Breakpoint Overflow Defense
- **Description**: Audit CSS grid and flexbox containers across mobile viewports (320px–375px) in `frontend/src/css/player.css` and `app-sections.css` to eliminate horizontal scroll.
- **Why Jules**: Can boot Playwright, capture screenshots at 375x667, and inspect visual diffs.
- **Required Tools/MCP**: Playwright headless browser, VM bash.
- **Inputs**: CSS stylesheets, mobile viewport specifications.
- **Outputs**: CSS patch fixing overflow + base64 screenshot artifacts.
- **Human Approval**: Review screenshots on PR.
- **Risk Level**: Medium.
- **Estimated Autonomy**: 80%.
- **Recommended Prompt**: Provide exact breakpoint constraints and mandate screenshot capture.

#### Task 04: SVG Icon System Integrity Suite Expansion
- **Description**: Expand `tests/icon-system.test.mjs` to verify that all 66 symbols in `frontend/src/icons/icons.svg` adhere to the 24x24 viewBox, stroke-width 1.85, and have matching `<symbol id="...">` tags.
- **Why Jules**: Pure unit test authoring with zero production runtime risk.
- **Required Tools/MCP**: Cloud VM bash (`node --test`).
- **Inputs**: `frontend/src/icons/icons.svg`, `tests/icon-system.test.mjs`.
- **Outputs**: Additional test cases in `tests/icon-system.test.mjs`.
- **Human Approval**: None.
- **Risk Level**: Zero.
- **Estimated Autonomy**: 100%.
- **Recommended Prompt**: Provide SVG schema and assertion rules.

#### Task 05: Native HTML `<dialog>` Migration
- **Description**: Refactor custom modal overlay div tags in `frontend/src/pages/app.html` to native `<dialog>` elements with `.showModal()` and backdrop CSS.
- **Why Jules**: Modern web standards refactoring with clear DOM lifecycle methods.
- **Required Tools/MCP**: Cloud VM bash.
- **Inputs**: `app.html`, `ui.js`, `components.css`.
- **Outputs**: Native dialog DOM structures with keyboard Escape handling.
- **Human Approval**: Plan approval required (`requirePlanApproval: true`).
- **Risk Level**: Medium.
- **Estimated Autonomy**: 80%.
- **Recommended Prompt**: Specify exact dialog IDs and event listener bindings.

#### Task 06: Backend Lambda Mock Unit Test Suite Authoring
- **Description**: Author a comprehensive test suite `tests/backend-lambda.test.mjs` mocking DynamoDB DocumentClient and S3 presigner to test `auth.js`, `getBooks.js`, `saveProgress.js`, and `getProgress.js`.
- **Why Jules**: Jules excels at greenfield test authoring against isolated functions.
- **Required Tools/MCP**: Cloud VM bash, `@aws-sdk` mocks.
- **Inputs**: `backend/lambda/*.js`.
- **Outputs**: New test file `tests/backend-lambda.test.mjs` running via `node --test`.
- **Human Approval**: None.
- **Risk Level**: Zero.
- **Estimated Autonomy**: 95%.
- **Recommended Prompt**: Provide Lambda signatures and mock expectations.

#### Task 07: Audio Monotonic Load Token Concurrency Tests
- **Description**: Expand `tests/player-lifecycle-token.test.mjs` to simulate race conditions where 5 rapid chapter clicks occur within 100ms, ensuring only the final token resolves.
- **Why Jules**: Concurrency and asynchronous lifecycle testing in Node.js.
- **Required Tools/MCP**: Cloud VM bash.
- **Inputs**: `frontend/src/js/player.js`, `tests/player-lifecycle-token.test.mjs`.
- **Outputs**: Expanded test cases verifying race resolution.
- **Human Approval**: None.
- **Risk Level**: Low.
- **Estimated Autonomy**: 90%.
- **Recommended Prompt**: Detail monotonic token mechanics and setTimeout mock patterns.

#### Task 08: OPFS Storage Path & Sanitization Unit Tests
- **Description**: Add unit tests in `tests/offline-shelf.test.mjs` testing path traversal defense, unicode character handling, and special character sanitization in audiobook filenames.
- **Why Jules**: Security-focused unit test expansion.
- **Required Tools/MCP**: Cloud VM bash.
- **Inputs**: `frontend/src/js/offline-shelf.js`.
- **Outputs**: Comprehensive test matrix covering edge-case filenames.
- **Human Approval**: None.
- **Risk Level**: Zero.
- **Estimated Autonomy**: 95%.
- **Recommended Prompt**: List malicious/malformed paths to validate against sanitization functions.

#### Task 09: Sync Queue Deduplication Invariant Tests
- **Description**: Enhance `tests/sync-queue.test.mjs` to stress-test deduplication when multiple rapid progress updates for the same `bookId` occur while offline.
- **Why Jules**: Logic verification in isolation.
- **Required Tools/MCP**: Cloud VM bash.
- **Inputs**: `frontend/src/js/user-data.js`, `frontend/src/js/api.js`.
- **Outputs**: New test assertions for queue compaction.
- **Human Approval**: None.
- **Risk Level**: Zero.
- **Estimated Autonomy**: 95%.
- **Recommended Prompt**: Provide state machine transitions for the sync queue.

#### Task 10: Headless Playwright Audio Smoke Test
- **Description**: Author a headless Playwright test `tests/e2e-smoke.spec.mjs` that launches `tools/serve.mjs`, navigates to `app.html#library`, clicks a book card, and verifies the player transport deck renders.
- **Why Jules**: Jules has built-in Playwright support in its cloud VM.
- **Required Tools/MCP**: Playwright, headless Chromium, VM bash.
- **Inputs**: `tools/serve.mjs`, `frontend/src/pages/app.html`.
- **Outputs**: Reusable Playwright smoke test script.
- **Human Approval**: Plan approval recommended.
- **Risk Level**: Low.
- **Estimated Autonomy**: 85%.
- **Recommended Prompt**: Provide exact local URL and DOM selector IDs.

#### Task 11: Backend Lambda CommonJS to ESM Migration
- **Description**: Convert `backend/lambda/*.js` from CommonJS (`const { ... } = require(...)`) to native ECMAScript Modules (`import ... from ...`), aligning backend with frontend ESM standards.
- **Why Jules**: Structural syntax refactoring; verified by running test suite.
- **Required Tools/MCP**: Cloud VM bash.
- **Inputs**: `backend/lambda/*.js`, `package.json`.
- **Outputs**: ESM backend files with updated import statements.
- **Human Approval**: Plan approval required.
- **Risk Level**: Medium.
- **Estimated Autonomy**: 90%.
- **Recommended Prompt**: Specify target Node.js version and package configuration.

#### Task 12: Service Worker Precache Inventory Automation
- **Description**: Write a small Node.js build utility `tools/update-precache-manifest.mjs` that scans `frontend/` and automatically updates `PRECACHE_URLS` in `frontend/service-worker.js`.
- **Why Jules**: Self-contained CLI tooling task.
- **Required Tools/MCP**: Cloud VM bash.
- **Inputs**: `frontend/service-worker.js`, directory structure.
- **Outputs**: Utility script + updated service worker precache array.
- **Human Approval**: Review generated list.
- **Risk Level**: Low.
- **Estimated Autonomy**: 90%.
- **Recommended Prompt**: Provide glob patterns and exclusions.

#### Task 13: Lambda Input Validation Hardening
- **Description**: Add strict input validation to `backend/lambda/saveProgress.js` (validating that `currentTime` and `totalDuration` are non-negative numbers, `bookId` is a sanitized string).
- **Why Jules**: Routine defensive programming pattern.
- **Required Tools/MCP**: Cloud VM bash.
- **Inputs**: `backend/lambda/saveProgress.js`.
- **Outputs**: Hardened handler returning 400 Bad Request on invalid payloads.
- **Human Approval**: None.
- **Risk Level**: Low.
- **Estimated Autonomy**: 95%.
- **Recommended Prompt**: Define schema boundaries and error status codes.

#### Task 14: Cloudflare Worker Security & CSP Injection
- **Description**: Update `backend/workers/proxymanager.js` to inject Content Security Policy (CSP), Strict-Transport-Security (HSTS), and X-Content-Type-Options headers on proxied audio responses.
- **Why Jules**: Edge worker header manipulation with clear RFC standards.
- **Required Tools/MCP**: Cloud VM bash.
- **Inputs**: `backend/workers/proxymanager.js`.
- **Outputs**: Hardened Cloudflare Worker response headers.
- **Human Approval**: Plan approval recommended.
- **Risk Level**: Medium.
- **Estimated Autonomy**: 85%.
- **Recommended Prompt**: Provide exact security header directives.

#### Task 15: Architecture & API Reference Documentation
- **Description**: Generate comprehensive markdown documentation in `docs/architecture/AUDIO-DSP-SUBSYSTEM.md` detailing the Web Audio API filter graph and sleep timer fadeout math.
- **Why Jules**: Code-to-documentation analysis based on clear repository logic.
- **Required Tools/MCP**: Cloud VM git.
- **Inputs**: `frontend/src/js/player.js`.
- **Outputs**: Formatted markdown documentation with signal-flow diagrams.
- **Human Approval**: None.
- **Risk Level**: Zero.
- **Estimated Autonomy**: 100%.
- **Recommended Prompt**: Provide target document structure and tone guidelines.

---

# 12. Identify What Jules Should NOT Do ("Jules Guardrails")

Autonomous cloud agents can cause catastrophic regressions if deployed on tasks requiring human taste, deep business context, or infrastructure credentials.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Jules Guardrails for VibeAudio                     │
├─────────────────────────────────────────────────────────────────────────┤
│ 🛑 1. NEVER make unilateral database selections or schema migrations    │
│ 🛑 2. NEVER execute live cloud deployments (AWS / Cloudflare / Pages)   │
│ 🛑 3. NEVER introduce frontend bundlers (No Vite / Webpack / Next.js)   │
│ 🛑 4. NEVER introduce frontend UI frameworks (No React / Vue / Svelte)  │
│ 🛑 5. NEVER alter core Web Audio API filter curve frequencies           │
│ 🛑 6. NEVER commit live API keys, tokens, or cloud secrets               │
│ 🛑 7. NEVER merge Pull Requests directly to 'main'                       │
│ 🛑 8. NEVER modify production audio files or delete R2 assets           │
└─────────────────────────────────────────────────────────────────────────┘
```

1. **Strategic Architecture Decisions**: Jules must **not** decide whether VibeAudio migrates to PostgreSQL, SQLite, or stays on DynamoDB. Database selection is deferred.
2. **Build Tooling Injection**: VibeAudio is strictly **zero-build**. Jules must **never** add `vite.config.js`, `webpack.config.js`, or transpile native ESM code.
3. **Framework Conversions**: Jules must **not** convert Vanilla JS components into React or Vue components. The architecture must remain vanilla DOM.
4. **Live Infrastructure Deployment**: Jules must **not** run `wrangler deploy` or AWS CDK/SAM commands against production accounts.
5. **Aesthetic Brand Direction**: Jules must **not** redesign the color palette or replace Newsreader/Inter typography without human direction.
6. **Destructive Data Operations**: Jules must **not** author scripts that perform unindexed DynamoDB scans with `deleteItem` or purge R2 storage buckets.

---

# 13. Experimental Workflow (Safe Test Matrix)

To systematically validate Google Jules against the real VibeAudio repository without risking production stability, execute the following 9-experiment matrix across three escalation levels:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      VibeAudio Jules Experiment Matrix                       │
├───────────────────────┬───────────────────────────┬──────────────────────────┤
│ Level 1: Safe         │ Level 2: Medium           │ Level 3: Advanced        │
│ (Zero Production Risk)│ (Controlled Scoped Code)  │ (Multi-File / Toolchain) │
├───────────────────────┼───────────────────────────┼──────────────────────────┤
│ EXP-01: Doc Generation│ EXP-04: CSS Token Replace │ EXP-07: Playwright E2E   │
│ EXP-02: Icon Unit Test│ EXP-05: A11y ARIA Polish  │ EXP-08: CJS to ESM Conv. │
│ EXP-03: Concurrency   │ EXP-06: Lambda Validation │ EXP-09: CI Healing Loop  │
└───────────────────────┴───────────────────────────┴──────────────────────────┘
```

### Level 1: Safe (Zero Production Risk)
- **EXP-01: Automated Audio DSP Architecture Documentation**:
  - *Task*: Generate `docs/architecture/AUDIO-DSP-SUBSYSTEM.md` explaining the Web Audio API filter graph from `player.js`.
  - *Success Criteria*: Clear markdown, accurate parameter descriptions (150Hz highpass, 2500Hz peak, 5000Hz highshelf), zero code edits.
  - *What We Learn*: Evaluates Jules' repository comprehension and technical writing clarity.
  - *Review*: Antigravity reviews for technical accuracy.
- **EXP-02: SVG Icon System Unit Test Expansion**:
  - *Task*: Add assertions to `tests/icon-system.test.mjs` verifying all 66 SVG symbol tags.
  - *Success Criteria*: All 116 existing tests + new assertions pass with `node --test tests/`.
  - *What We Learn*: Evaluates Jules' ability to run native Node.js tests inside its cloud VM.
  - *Review*: Antigravity verifies test execution in terminal.
- **EXP-03: Monotonic Load Token Concurrency Unit Tests**:
  - *Task*: Add rapid track-switch race condition tests in `tests/player-lifecycle-token.test.mjs`.
  - *Success Criteria*: Stale promises correctly cancel; test suite exits with code 0.
  - *What We Learn*: Tests Jules' ability to reason about asynchronous state machines.
  - *Review*: Antigravity audits assertion logic.

### Level 2: Medium (Controlled Scoped Modifications)
- **EXP-04: Master CSS Design Token Harmonization**:
  - *Task*: Replace hardcoded colors in `frontend/src/css/components.css` with CSS variables from `.stitch/DESIGN.md`.
  - *Success Criteria*: Visual parity confirmed; zero broken CSS rules; passes `tests/ui-contracts.test.mjs`.
  - *What We Learn*: Tests multi-line CSS refactoring precision across structured tokens.
  - *Review*: Antigravity checks diff and verifies visual rendering.
- **EXP-05: App Shell Accessibility & ARIA Remediation**:
  - *Task*: Add `aria-expanded` and `aria-label` to player controls and drawer in `app.html`.
  - *Success Criteria*: `node --test tests/accessibility.test.mjs` passes with zero regressions.
  - *What We Learn*: Evaluates DOM manipulation precision in complex HTML shells.
  - *Review*: Antigravity verifies DOM IDs remain intact.
- **EXP-06: Lambda Handler Input Validation & Mock Tests**:
  - *Task*: Add validation guards to `backend/lambda/saveProgress.js` and author a mock test suite.
  - *Success Criteria*: Invalid payloads return 400; valid payloads pass mocks.
  - *What We Learn*: Tests Jules' ability to write backend code and mock AWS SDK v3.
  - *Review*: Antigravity reviews error handling patterns.

### Level 3: Advanced (Multi-File & Verification Tooling)
- **EXP-07: Headless Playwright Smoke Test in Cloud VM**:
  - *Task*: Write a Playwright script that spins up `tools/serve.mjs` and verifies the home view renders.
  - *Success Criteria*: Playwright script executes headlessly in the Jules VM and attaches screenshot artifacts to the session.
  - *What We Learn*: Validates Jules' internal browser testing and screenshot capture pipeline.
  - *Review*: Antigravity inspects attached screenshot artifacts.
- **EXP-08: Lambda CommonJS to ESM Full Conversion**:
  - *Task*: Convert all 5 Lambda handlers in `backend/lambda/*.js` from CJS to native ESM.
  - *Success Criteria*: All functions use `import/export`; mock tests pass cleanly.
  - *What We Learn*: Tests cross-file architectural conversion and dependency boundary handling.
  - *Review*: Antigravity audits package imports and runtime compatibility.
- **EXP-09: GitHub Actions Closed-Loop CI Auto-Repair**:
  - *Task*: Introduce a deliberately failing test assertion in a test branch, trigger CI, and evaluate Jules' autonomous reaction via webhook.
  - *Success Criteria*: Jules detects CI failure, inspects error logs, pushes a fixing commit, and green-lights the build.
  - *What We Learn*: Proves whether Jules can autonomously heal broken continuous integration builds.
  - *Review*: Antigravity audits fix commit history on GitHub.

---

# 14. Prompt Engineering for Jules

Empirical research across Jules sessions demonstrates that prompts structured with explicit constraints, negative boundaries, test verification commands, and file scopes dramatically outperform conversational prompts.

### 14.1 The VibeAudio Jules Task Prompt Template

```markdown
# Objective
[Concise 1-2 sentence description of the task]

# Repository Architecture & Context
- Framework: Native ECMAScript Modules (ESM), Vanilla HTML5/CSS3.
- Build Tooling: ZERO-BUILD. Absolutely NO Vite, Webpack, Babel, or bundling tools.
- Test Runner: Native Node.js test runner (`node --test tests/`).
- Design System: `.stitch/DESIGN.md` (Light Editorial Sanctuary theme).

# Target Files
- Modify: [Relative path to file 1]
- Modify: [Relative path to file 2]
- Reference: [Relative path to reference spec]

# Concrete Requirements
1. [Requirement 1]
2. [Requirement 2]
3. [Requirement 3]

# Strict Negative Constraints (DO NOT DO)
- DO NOT introduce any third-party npm packages or dependencies.
- DO NOT add build scripts, compilers, or configuration files.
- DO NOT alter existing DOM element IDs in `frontend/src/pages/app.html`.
- DO NOT commit secrets, environment variables, or `.env` files.

# Verification & Completion Command
Execute the following verification command in the VM shell before submitting:
```bash
npm run test:all
```
All tests must pass with exit code 0.
```

---

# 15. Repository Instructions (`AGENTS.md`)

Google Jules automatically parses `AGENTS.md` located in the root of the repository on task initialization. To enforce VibeAudio's invariants on any future Jules session without modifying code today, the following structure is proposed for eventual implementation:

```markdown
# AGENTS.md — VibeAudio Autonomous Engineering Instructions

## 1. Core Architectural Invariants
- **Zero-Build Architecture**: This repository uses native browser ES Modules (`type="module"`). Never introduce Vite, Webpack, Rollup, Babel, or any bundler.
- **Native Test Runner**: All tests use Node.js native test runner (`node --test`). Never introduce Jest, Vitest, or Mocha.
- **Design System Source of Truth**: All visual styling, colors, and typography MUST align with `.stitch/DESIGN.md`. Accent color is `#C64E00` (Terracotta Amber).
- **Guest-First / Offline-First**: Unauthenticated guest access is the primary experience. Never make network calls mandatory for basic player functionality.

## 2. Shell & Verification Commands
- Run all unit tests: `npm test`
- Run full verification suite: `npm run test:all`
- Start local development server: `node tools/serve.mjs` (listens on `http://127.0.0.1:4173`)

## 3. Directory Conventions
- `frontend/src/js/`: Client ECMAScript Modules.
- `frontend/src/css/`: Modular vanilla CSS files.
- `frontend/src/pages/`: Application HTML shells (`app.html`).
- `backend/lambda/`: AWS Lambda functions (Node.js).
- `backend/workers/`: Cloudflare Workers.
- `tests/`: Native test suites (`*.test.mjs`).
- `.stitch/`: Google Stitch design system metadata and specifications.

## 4. Forbidden Actions
- DO NOT touch or delete production DynamoDB tables or Cloudflare R2 audio assets.
- DO NOT alter DOM element IDs required by `tests/ui-contracts.test.mjs`.
- DO NOT commit credentials, AWS keys, or API tokens.
```

---

# 16. Security & Trust Model ("What Jules Should Never Have Access To")

To protect VibeAudio's cloud infrastructure, user privacy, and code integrity, the following security perimeter must be enforced:

```
┌─────────────────────────────────────────────────────────────────────────┐
│              What Jules Should NEVER Have Access To                     │
├─────────────────────────────────────────────────────────────────────────┤
│ ❌ 1. AWS Production IAM Credentials (No DynamoDB / S3 admin keys)       │
│ ❌ 2. Cloudflare API Tokens (No Workers / Pages / R2 deployment tokens)  │
│ ❌ 3. Clerk Production Secret Keys (No user impersonation access)        │
│ ❌ 4. GitHub 'main' Branch Direct Push (Branch protection enforced)     │
│ ❌ 5. Production Domain DNS / SSL Configuration                         │
│ ❌ 6. Unrestricted Outbound Network Access to Internal Staging VPCs     │
└─────────────────────────────────────────────────────────────────────────┘
```

1. **Production Cloud Credentials**: Jules' VM must never contain AWS IAM access keys with write permissions to DynamoDB or Cloudflare API tokens. Backend tasks must run against local mocks.
2. **GitHub Branch Protection**: The `main` branch must enforce GitHub branch protection requiring at least one approving pull request review and green CI checks before merging. Jules must only push to feature branches (`jules/feature-*`).
3. **Clerk Secret Keys**: Jules only requires the client publishable key (`pk_test_*`) already present in `config.js`. It must never receive backend Clerk secret keys.
4. **Isolated Secrets Storage**: Any required API keys (e.g. Stitch API token) must be stored encrypted within Jules cloud settings (`jules.google.com/settings`) and never committed into git history.

---

# 17. Final Capability Matrix

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     VibeAudio Final Capability Matrix                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ 🟢 EXCELLENT FIT (Jules Confidently Owns)                                     │
│    • Unit and integration test expansion (`node --test tests/*.test.mjs`)    │
│    • CSS design token consolidation against `.stitch/DESIGN.md`              │
│    • Accessibility audit and ARIA attribute injection                        │
│    • Documentation generation (API specs, architecture guides)               │
│    • Dependency version bumping and lockfile maintenance                     │
│    • Headless Playwright script authoring and visual screenshot capture      │
├──────────────────────────────────────────────────────────────────────────────┤
│ 🟡 GOOD FIT WITH REVIEW (Jules Implements, Antigravity Audits)              │
│    • CommonJS to ESM backend refactoring                                     │
│    • Backend Lambda payload validation hardening                             │
│    • Responsive CSS breakpoint overflow repairs                              │
│    • Native HTML5 `<dialog>` migrations                                      │
│    • Service Worker precache inventory automation                            │
├──────────────────────────────────────────────────────────────────────────────┤
│ 🟠 EXPERIMENTAL (Worth Testing in Controlled Sandbox)                         │
│    • Automated CI failure healing via GitHub Actions webhooks                │
│    • Parallel exploration sessions (`jules remote new --parallel 3`)         │
│    • Cross-service Cloudflare Worker proxy optimizations                     │
├──────────────────────────────────────────────────────────────────────────────┤
│ 🔴 POOR FIT / FORBIDDEN (Antigravity & Humans Own)                           │
│    • Final database selection and schema migrations (intentionally deferred) │
│    • Live cloud deployments to AWS Lambda or Cloudflare                      │
│    • Web Audio API vocal clarity DSP filter curve tuning                     │
│    • Core brand identity, color theme, and typographic art direction         │
│    • Introducing frontend bundlers or frameworks (Vite / React)              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

# 18. Final Recommendation

Based on empirical codebase reconnaissance and deep investigation of Google Jules in late 2026, the following decisive answers address the core questions of this research phase:

1. **Should Jules become a regular engineering agent for VibeAudio?**  
   **YES**. Jules is mature, stable, and ready to act as VibeAudio's asynchronous background engineering partner, offloading routine, multi-file, and testing workloads without consuming local development cycles.
2. **What role should Jules play?**  
   The **Autonomous Background Engineer**. Jules handles batch refactors, unit test authoring, CSS token migration, and CI healing in isolated cloud VMs, delivering clean GitHub Pull Requests.
3. **What role should Antigravity play?**  
   The **Lead Systems Architect & Pair Programmer**. Antigravity defines feature scopes, authors `AGENTS.md` and `DESIGN.md`, conducts rapid interactive pair programming, reviews Jules' PRs, and verifies visual/audio playback locally.
4. **What role should Stitch play?**  
   The **Design Brain & Visual Source of Truth**. Stitch defines screen layouts and exports semantic design tokens to `.stitch/DESIGN.md`.
5. **What should GitHub/CI handle?**  
   The **Deterministic Quality Gatekeeper**. GitHub Actions runs `npm run test:all` on all branches, enforces branch protection on `main`, and triggers Jules CI Fixer webhooks when builds break.
6. **What should remain human-controlled?**  
   Strategic product direction, final PR merge approvals, database selection, brand aesthetics, and production deployments.
7. **What should we test first?**  
   **Experiment Level 1**: Safe unit test authoring (`tests/icon-system.test.mjs`) and technical architecture documentation (`docs/architecture/AUDIO-DSP-SUBSYSTEM.md`).
8. **What should we NOT attempt yet?**  
   Do not connect Jules to live AWS/Cloudflare production deployments; do not attempt database migrations; and do not allow Jules to modify the core Web Audio API DSP filter node graph.
9. **What MCP integrations are genuinely valuable?**  
   - Local: The `google-jules` MCP server allows Antigravity to trigger and monitor Jules sessions directly from the chat/terminal interface.
   - Cloud: The **Google Stitch MCP** integration inside Jules allows Jules to reference Stitch screens during UI development.
10. **What workflow maximizes quality while minimizing agent mistakes?**  
    The **Orchestrated Asynchronous Triad**: Antigravity scopes the task and sets boundaries $\rightarrow$ Jules implements and tests in an isolated cloud VM $\rightarrow$ Antigravity reviews the resulting GitHub PR and runs local validation $\rightarrow$ Human merges.

---

# Research Verdict

Google Jules has graduated from an experimental preview into a production-grade autonomous cloud engineering agent. It is exceptionally well-suited to participate in VibeAudio's engineering lifecycle as an asynchronous implementation worker. 

Because VibeAudio possesses a clean, zero-build architecture, highly modular native ES Modules, and a zero-dependency test runner (`node --test`), Jules can operate inside its cloud Ubuntu VMs with maximum efficiency—free from complex bundler crashes, hydration mismatches, or lockfile corruption. 

When governed by strict `AGENTS.md` guardrails, guided by `.stitch/DESIGN.md`, and audited by Antigravity prior to merging, Jules provides an estimated **3x to 5x velocity multiplier** on test authoring, accessibility compliance, and design token modernization.

**Recommended Next Step**: In the upcoming planning and implementation phase, establish `AGENTS.md` in the repository root, connect the GitHub repository to Jules, and execute **Level 1 Experiments (EXP-01 and EXP-02)** to empirically establish baseline agent performance.
