# VibeAudio — Visual QA Workflow & Verification Protocol

**Document ID:** `DOC-QA-002`  
**Status:** Operational Verification Workflow  
**Author:** Quality Assurance Architect & UX Engineer  
**Scope:** Step-by-Step Visual QA, Playwright Screenshot Automation, and Regression Protocol  
**Cross-References:** [`DOC-QA-001`](VibeAudio-Light-UI-Acceptance.md), [`DOC-IMP-002`](../implementation/VibeAudio-Light-UI-Roadmap.md)  

---

## 1. Visual QA Pipeline Overview

To achieve Apple-grade visual precision without regressions, all redesign work follows a deterministic, closed-loop verification workflow:

```
┌─────────────────────────────────────────────────────────────┐
│                 VISUAL QA REPEATABLE WORKFLOW               │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
                        1. BASELINE CAPTURE
                        (Snapshot current state)
                               │
                               ▼
                        2. STITCH SYNTHESIS
                        (Generate design reference)
                               │
                               ▼
                        3. IMPLEMENTATION
                        (CSS/DOM updates in Antigravity)
                               │
                               ▼
                        4. AUTOMATED SCREENSHOT
                        (Playwright headless capture)
                               │
                               ▼
                        5. VISUAL COMPARISON
                        (Diff against Stitch reference)
                               │
                               ▼
                        6. ISSUE CLASSIFICATION
                        (Layout, Type, Space, Material)
                               │
                               ▼
                        7. SURGICAL FIX
                        (Targeted CSS token adjustment)
                               │
                               ▼
                        8. REGRESSION CHECK
                        (npm test + re-snapshot)
```

---

## 2. Visual Review Taxonomy & Categories

During the Visual Comparison step, every visual delta is classified under one of the following 9 quality axes:

| Category | Inspection Criteria | Example Issue | Resolution Directive |
|---|---|---|---|
| **1. Layout** | Grid alignment, container centering, element flow. | Card grid wrapping unevenly at 1280px. | Adjust `grid-template-columns` minmax bounds. |
| **2. Typography** | Font family, line height, font weight, letter spacing. | Book title using system sans instead of `Newsreader`. | Ensure `font-family: var(--font-display)` applied. |
| **3. Spacing** | Padding discipline, margins, gutters between cards. | Filter pills touching header text without 14px gap. | Standardize to `--space-3` (12px) or `--space-4` (16px). |
| **4. Color & Contrast**| Hex compliance, WCAG contrast ratio, no dirty dark blobs.| Author byline too faint (`#AEAEB2`) on white. | Upgrade to `--color-text-secondary` (`#6E6E73`). |
| **5. Material & Glass**| Blur radius, saturation, border hairline, opacity. | Topbar blur missing or border blending into canvas. | Verify `backdrop-filter: blur(20px)` and border token. |
| **6. Component Uniformity**| Button shapes, corner radii, shadow consistency. | Primary button has square corners instead of pill. | Apply `border-radius: var(--radius-pill)`. |
| **7. Responsiveness** | Viewport adaptivity, touch hit areas, no horizontal leak.| Mini player too wide on 375px mobile screen. | Set `width: min(var(--shell-width), calc(100% - 24px))`. |
| **8. Interaction & Motion**| Hover state, press scale, focus ring visibility. | Missing `transform: scale(0.97)` on button press. | Add `:active` tactile micro-interaction rule. |
| **9. Accessibility** | High-contrast focus rings, screen reader visibility. | Scrubber thumb lacks visible keyboard focus indicator. | Add `outline: 2px solid var(--color-accent)`. |

---

## 3. Automation Protocol: Playwright Screenshot Capture

Visual verification uses automated Playwright headless scripts to produce standardized PNG screenshots across the 3 target device viewports:

### 3.1 Device Emulation Presets:
1. **Desktop Standard:** `1440 × 900`, `deviceScaleFactor: 2` (Retina emulation).
2. **Tablet Landscape:** `1024 × 768`, `deviceScaleFactor: 2`.
3. **Mobile Portrait:** `390 × 844` (iPhone 14/15 Pro emulation), touch enabled, `hasTouch: true`.

### 3.2 Automated Test Script Pattern:
```javascript
// tools/capture-visual-baselines.mjs
import { chromium } from 'playwright';

const viewports = [
    { name: 'desktop-1440', width: 1440, height: 900 },
    { name: 'tablet-1024', width: 1024, height: 768 },
    { name: 'mobile-390', width: 390, height: 844, isMobile: true }
];

const screens = [
    { url: 'http://localhost:8080/index.html', name: 'landing' },
    { url: 'http://localhost:8080/src/pages/app.html#home', name: 'app-home' },
    { url: 'http://localhost:8080/src/pages/app.html#library', name: 'app-library' },
    { url: 'http://localhost:8080/src/pages/app.html#offline', name: 'app-offline' },
    { url: 'http://localhost:8080/src/pages/app.html#player', name: 'app-player' }
];
```

---

## 4. Defect Severity & Exit Criteria

* **Severity 1 (Blocker):** Broken playback, broken audio controls, failing contract tests (`npm test`), unreadable text (contrast `< 4.5:1`), horizontal page overflow.
* **Severity 2 (Major):** Broken layout alignment, misplaced floating mini dock, missing focus ring, distorted cover artwork aspect ratio.
* **Severity 3 (Minor):** Slight spacing deviation (e.g. 18px vs 16px), non-standard animation easing curve, minor shadow opacity variance.

### Exit Gate:
Phase sign-off requires **zero Severity 1 and zero Severity 2 defects**, and 100% pass on all 12 test suites in `tests/`.
