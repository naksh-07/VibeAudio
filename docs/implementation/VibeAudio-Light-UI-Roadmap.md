# VibeAudio — Phased Implementation Roadmap: Light UI Redesign

**Document ID:** `DOC-IMP-002`  
**Status:** Canonical Implementation Roadmap  
**Author:** Principal Technical Project Lead & Systems Architect  
**Scope:** Sequential Execution Strategy (Phase 0 through Phase 10)  
**Cross-References:** [`DOC-IMP-001`](VibeAudio-Light-UI-Implementation.md), [`DOC-QA-001`](../qa/VibeAudio-Light-UI-Acceptance.md)  

---

## 1. Roadmap Architecture & Execution Flow

To ensure complete safety, zero regressions, and surgical execution, the implementation is decomposed into 11 distinct, test-gated phases:

```
┌─────────────────────────────────────────────────────────────┐
│                 PHASED IMPLEMENTATION ROADMAP               │
├─────────────────────────────────────────────────────────────┤
│ Phase 0  ──► Architectural Audit & Safety Baseline (DONE)   │
│ Phase 1  ──► Design Foundations & Token Migration (base.css)│
│ Phase 2  ──► Shared Component System (components.css)       │
│ Phase 3  ──► Application Shell & Section Grids (app-sections)│
│ Phase 4  ──► Landing Page Light Editorial Refresh (landing) │
│ Phase 5  ──► Floating Mini-Player Dock (player.css)         │
│ Phase 6  ──► Full Player & Hardware Transport Deck (player) │
│ Phase 7  ──► Responsive & Safe-Area Ergonomics (Mobile/PWA) │
│ Phase 8  ──► Accessibility (a11y) & Keyboard Navigation     │
│ Phase 9  ──► Visual QA & Stitch Reference Verification      │
│ Phase 10 ──► Production Hardening & Git Deployment          │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Phase Specifications

### Phase 0 — Architectural Audit & Safety Baseline (COMPLETED)
* **Objectives:** Forensically audit the repository, verify the 12 automated test suites, document DOM contracts, and produce the comprehensive documentation package.
* **Files Affected:** `docs/**` (No application code modified).
* **Exit Criteria:** All 12 test suites passing (116 tests); comprehensive documentation artifacts accepted.

---

### Phase 1 — Design Foundations & Token Migration
* **Objectives:** Migrate CSS custom properties in `base.css` to the luminous Apple light canvas (`#F5F5F7`), pure white surfaces (`#FFFFFF`), warm amber accent (`#C64E00`), and dark text hierarchy (`#1D1D1F`). Adapt `ui-player-helpers.js` light theme calculations.
* **Files Likely Affected:**
  * `frontend/src/css/base.css`
  * `frontend/src/js/ui-player-helpers.js`
* **Dependencies:** Phase 0.
* **Risks:** Dark mode text flashing or ColorThief extracting dark background tints.
* **Verification:** `npm test tests/accessibility.test.mjs`; verify CSS variable injection in browser.
* **Exit Criteria:** Viewport background is crisp `#F5F5F7`; typography renders in `Newsreader` and `Inter`.

---

### Phase 2 — Shared Component System
* **Objectives:** Restyle core UI components: `.book-card` with squircle radius and 2:3 aspect ratio, `.resume-hero-card`, `.solid-btn`, `.btn-secondary`, `.filter-btn` pills, and status badges.
* **Files Likely Affected:**
  * `frontend/src/css/components.css`
  * `frontend/src/css/cover-media.css`
* **Dependencies:** Phase 1.
* **Risks:** Broken 2:3 aspect ratio on covers or distorted badge positioning.
* **Verification:** Visual inspection of `.book-card` across Library and Home shelves.
* **Exit Criteria:** Cards display soft shadows, clean hairline borders, and tactile active press compression.

---

### Phase 3 — Application Shell & Section Grids
* **Objectives:** Modernize `.app-topbar` into a floating frosted glass navigation bar. Align `#view-home`, `#view-library`, `#view-offline`, and `#view-profile` view containers.
* **Files Likely Affected:**
  * `frontend/src/css/app-sections.css`
* **Dependencies:** Phase 2.
* **Risks:** Topbar sticky collision on mobile or broken search input interactions.
* **Verification:** `npm test tests/ui-contracts.test.mjs`.
* **Exit Criteria:** Floating topbar blurs smoothly over scrolling content; all views render cleanly without clipping.

---

### Phase 4 — Landing Page Light Editorial Refresh
* **Objectives:** Align the landing page (`index.html` & `landing.css`) with the light sanctuary theme. Refine hero 2-column layout, spotlight card, curated preview, and Clerk auth widget.
* **Files Likely Affected:**
  * `frontend/src/css/landing.css`
  * `frontend/index.html` (meta theme-color update only)
* **Dependencies:** Phase 2 & Phase 3.
* **Risks:** Font Awesome class leakage or broken guest transition links.
* **Verification:** `npm test tests/icon-system.test.mjs`.
* **Exit Criteria:** Landing page communicates the serene, light-minimalist character.

---

### Phase 5 — Floating Mini-Player Dock
* **Objectives:** Implement the macOS/iOS floating pill dock (`#mini-player`). Style the 2px accent progress line, 42×42px cover art, single-line text clamping, and tactile circular play button.
* **Files Likely Affected:**
  * `frontend/src/css/player.css`
* **Dependencies:** Phase 3.
* **Risks:** Mini player failing to hide on `#view-player` or blocking bottom view content.
* **Verification:** Verify dock hides on full player and renders seamlessly on Home and Library.
* **Exit Criteria:** Floating dock sits 16px above bottom with frosted glass blur and 44px touch targets.

---

### Phase 6 — Full Player & Hardware Transport Deck
* **Objectives:** Restyle the Full Player view (`#view-player`). Implement the luminous ambient cover bloom, 56px circular play button, 18px range scrubber thumb, chapter active indicator, and notes stack.
* **Files Likely Affected:**
  * `frontend/src/css/player.css`
  * `frontend/src/css/player-premium.css`
* **Dependencies:** Phase 5.
* **Risks:** Dark overlay scrim making the player look like dark mode; scrubber thumb sticking.
* **Verification:** `npm test tests/player-lifecycle-token.test.mjs`.
* **Exit Criteria:** Full player feels like a high-end audio instrument with smooth scrubbing and high contrast.

---

### Phase 7 — Responsive & Safe-Area Ergonomics
* **Objectives:** Optimize for iPhone (390×844) and iPad (1024×768). Enforce `env(safe-area-inset-bottom)`, refine mobile sidebar drawer (`#sidebar`), and ensure zero horizontal overflow.
* **Files Likely Affected:**
  * `frontend/src/css/base.css`
  * `frontend/src/css/player.css`
  * `frontend/src/css/app-sections.css`
* **Dependencies:** Phase 5 & Phase 6.
* **Risks:** Bottom home indicator overlapping the mini player dock on iOS devices.
* **Verification:** Mobile responsive emulation checks in browser.
* **Exit Criteria:** Zero layout clipping on 375px and 390px viewports; 44px minimum touch targets verified.

---

### Phase 8 — Accessibility (a11y) & Keyboard Navigation
* **Objectives:** Verify WCAG AA contrast compliance across all text. Ensure visible focus rings (`:focus-visible`) on all interactive controls. Verify ARIA live regions and screen reader attributes.
* **Files Likely Affected:**
  * `frontend/src/css/base.css`
* **Dependencies:** Phase 7.
* **Risks:** Faint focus rings or low contrast on secondary metadata.
* **Verification:** `npm test tests/accessibility.test.mjs`.
* **Exit Criteria:** 100% automated accessibility test pass; tab navigation seamlessly traverses all screens.

---

### Phase 9 — Visual QA & Stitch Reference Verification
* **Objectives:** Execute Playwright baseline captures across Desktop, Tablet, and Mobile. Compare against Stitch screen references (`docs/stitch/*.md`). Classify and resolve any visual deltas.
* **Files Likely Affected:**
  * Targeted CSS adjustments only.
* **Dependencies:** Phase 8.
* **Risks:** Visual drift from design specifications.
* **Verification:** Execution of Visual QA protocol (`DOC-QA-002`).
* **Exit Criteria:** Zero Severity 1 and zero Severity 2 defects.

---

### Phase 10 — Production Hardening & Git Deployment
* **Objectives:** Verify Service Worker precaching (`tests/pwa-manifest-sw.test.mjs`). Run the entire 12-suite regression test suite. Commit changes with clean conventional commit message and push to GitHub.
* **Files Likely Affected:**
  * Git repository commit and push.
* **Dependencies:** Phase 9.
* **Risks:** Service worker caching stale CSS files.
* **Verification:** Full `npm test` run (116 tests passing).
* **Exit Criteria:** Clean git working tree; all tests pass; deployed to GitHub `main`.
