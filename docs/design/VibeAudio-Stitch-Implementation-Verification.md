# VibeAudio Stitch Implementation Verification Specification

**Document ID:** `SPEC-DESIGN-001`  
**Status:** Canonical Visual Verification & QA Specification  
**Version:** 1.0.0  
**Date:** September 13, 2026  
**Authors:** Senior Design Technologist & Visual QA Lead, Antigravity Architecture Board  
**Target Repository:** `c:\Users\Suraj\Documents\Antigravity\VibeAudio`  
**Cross-References:** [`STITCH-DS-001`](../../.stitch/DESIGN.md), [`STITCH-SITE-001`](../../.stitch/SITE.md), [`MP-VIBE-001`](../plans/VibeAudio-AI-Native-Frontend-Backend-Stitch-Evolution-Master-Plan.md), [`SPEC-FE-001`](../implementation/VibeAudio-Frontend-Evolution-Spec.md)

---

## 1. The Continuous Visual Verification Loop

To prevent visual drift between Google Stitch design specifications and live browser runtime, VibeAudio establishes a closed-loop **Visual Verification & QA Harness**.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   CONTINUOUS VISUAL VERIFICATION LOOP                  │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Stitch Source of Truth:                                             │
│    .stitch/DESIGN.md, .stitch/SITE.md, and 8 canonical screen specs    │
├────────────────────────────────────────────────────────────────────────┤
│ 2. Scoped Code Implementation:                                         │
│    Jules / Antigravity updates CSS variables and Web Component markup │
├────────────────────────────────────────────────────────────────────────┤
│ 3. Headless Browser Rendering:                                         │
│    Playwright captures multi-viewport golden screenshots:              │
│    Desktop (1280×800), Tablet (768×1024), Mobile (375×812)            │
├────────────────────────────────────────────────────────────────────────┤
│ 4. Automated Pixel & Token Diffing:                                    │
│    pixelmatch compares rendered snapshots against Stitch references    │
├────────────────────────────────────────────────────────────────────────┤
│ 5. Architectural Evaluation & Verdict:                                 │
│    Antigravity Architecture Board assigns verdict:                     │
│    [ KEEP ]    Diff < 0.5%, all contrast ratios pass WCAG 2.1 AA       │
│    [ REFINE ]  0.5% <= Diff <= 2.0%, minor spacing or font weight shift│
│    [ REJECT ]  Diff > 2.0%, layout break, dark mode leak, FOIT failure │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Measurable Review Criteria & Verification Rubric

Every screen and component must satisfy six objective, measurable quality dimensions before merging into `main`:

| Dimension | Verification Method | Pass Threshold / Acceptance Target | Critical Failure Condition |
|---|---|---|---|
| **1. Color Fidelity** | Headless DOM computed style inspection | 100% token match with `.stitch/DESIGN.md`: Canvas `#F5F5F7`, Surface `#FFFFFF`, Accent `#C64E00`, Text `#1D1D1F`. | Any occurrence of pure black `#000000` or neon button glow. |
| **2. Contrast Ratios** | Automated axe-core / Playwright evaluation | $\ge 12.8:1$ on headings, $\ge 4.67:1$ on primary button labels, $\ge 4.5:1$ on running copy. | Any text element failing WCAG 2.1 AA ($<4.5:1$). |
| **3. Typography Scale** | Font-family and line-height inspection | `Newsreader` for titles, `Inter` for UI, `JetBrains Mono` for timecodes. Correct weights (400, 500, 600). | Flash of Invisible Text (FOIT) while offline; generic fallback serif. |
| **4. Spacing & Geometry** | Bounding box measurement | Strict 4pt/8pt grid steps: 4px, 8px, 12px, 16px, 20px, 24px, 32px, 48px. Container max-width 1200px. | Elements overlapping floating mini dock; cards deviating from 2:3 ratio. |
| **5. Responsive Grids** | Viewport testing across 375px, 768px, 1280px | Desktop 4-col, Tablet 3-col, Mobile 2-col. Touch targets $\ge 44\times 44\text{px}$. | Horizontal viewport scrolling on mobile; clipped action buttons. |
| **6. Motion & Physics** | CSS transition property audit | Timing functions matching `cubic-bezier(0.2, 0, 0, 1)`. Duration $\le 350\text{ms}$. Zero-time on reduced motion. | Layout-thrashing animations animating `top`, `left`, `width`, or `height`. |

---

## 3. Screen-by-Screen Visual Checkpoints & Rubric

### Screen 01: Landing Page (`frontend/index.html`)
* **Primary Role:** Public welcoming sanctuary, trust signals, and direct guest CTA.
* **Visual Checkpoints:**
  1. **Hero Stage:** Headline in `Newsreader` (48px / weight 600 / line-height 1.06). Deep carbon text `#1D1D1F`.
  2. **Call to Action:** Pill button (`height: 44px`, background `#C64E00`, text `#FFFFFF`, radius 999px). Subtitle specifies "Guest & Offline Ready — No Account Required".
  3. **Curated Showcase:** 3 featured titles with 2:3 aspect ratio paperback covers, subtle ambient tilt, and no storefront prices.
  4. **Trust Badges:** Three calm value propositions with custom SVG icons (Zero Ads, Origin Private File System, Monotonic Cloud Sync).

### Screen 02: Home Base (`#view-home`)
* **Primary Role:** Personal home shelf with instant listening continuity.
* **Visual Checkpoints:**
  1. **"Resume Listening" Hero Stage:** Asymmetrical hero banner featuring active audiobook cover, progress bar filled with terracotta accent (`#C64E00`), remaining time in `JetBrains Mono`, and 56px play button with soft ambient halo (`rgba(198, 78, 0, 0.12)`).
  2. **"On This Device" Shelf:** Horizontal carousel displaying locally downloaded audiobooks with `#248A3D` green checkmark status badges.
  3. **Curated Recommendations Shelf:** 4-column book grid with squircle cards (`14px` radius) on solid white surfaces.
  4. **Fresh User Empty State:** When no book is in progress, the hero stage transitions into an inviting editorial welcome card with a "Discover Literature" primary button.

### Screen 03: Library Discovery (`#view-library`)
* **Primary Role:** Comprehensive catalog browsing, genre filtering, and search.
* **Visual Checkpoints:**
  1. **Category Filter Toolbar:** Horizontal pill row with terracotta active indicator (`rgba(198, 78, 0, 0.08)` background, `#C64E00` border and text).
  2. **Instant Search Input:** Clean field with `10px` radius, background `#F2F2F7`, search glyph, and clear button.
  3. **Book Grid:** Strict 4-column desktop layout (`24px` gap) collapsing to 3 columns on tablet and 2 columns on mobile (`12px` gap).
  4. **Zero Results State:** Clean line-drawing icon, single-line explanation, and "Reset Filters" action button.

### Screen 04: Offline Vault (`#view-offline`)
* **Primary Role:** Dedicated on-device storage sanctuary and local file importer.
* **Visual Checkpoints:**
  1. **Storage Telemetry Panel:** Squircle card displaying OPFS used bytes vs quota, progress bar, and "Make Storage Persistent" action.
  2. **Local Audio Importer:** Drag-and-drop target accepting `.mp3` and `.m4b` files up to 2 GB.
  3. **Downloaded Shelf:** Clean list of downloaded books with byte sizes, chapter counts, and destructive "Remove Download" button styled in subtle muted red (`rgba(255, 59, 48, 0.10)`).
  4. **Zero Downloads State:** Welcoming illustration explaining how to download audiobooks for flights and subways.

### Screen 05: Full Player Sanctuary (`#view-player`)
* **Primary Role:** Immersive full-screen distraction-free listening environment.
* **Visual Checkpoints:**
  1. **Top Bar:** Subtle back arrow and offline indicator chip (`#248A3D` green).
  2. **Cover Sanctuary:** 2:3 vertical aspect ratio cover with mathematical ColorThief ambient bloom clamped to $S \le 35\%$ and $L \ge 85\%$.
  3. **Literary Metadata:** Book title rendered in `Newsreader` (`clamp(1.8rem, 3.2vw, 2.75rem)`), author in `Inter` (`#6E6E73`).
  4. **Tactile Scrubber Deck:** 6px track height, terracotta fill, 18px white thumb expanding to 22px on touch, with `JetBrains Mono` timecodes.
  5. **Hardware Transport Deck:** Speed pill (0.75x–2.0x), -15s jump, 56px play circle with warm aura, +30s jump, and sleep timer icon.
  6. **Dual Tab Lower Panel:** Segmented switch toggling between "Chapters" playlist (with active chapter highlighted) and "Bookmarks & Notes".

### Screen 06: Profile & Device Settings (`#view-profile`)
* **Primary Role:** Listener identity, cloud sync controls, and storage reset.
* **Visual Checkpoints:**
  1. **Account Status Card:** Clear indication of "Guest Mode (Local Only)" or authenticated Clerk profile.
  2. **Cloud Sync Action:** Status indicator reflecting sync health with manual "Sync Device Now" button.
  3. **Destructive Reset Option:** "Clear All Local Audio" button with warning confirmation dialog.

### Screen 07: Persistent Mini-Player Dock (`#mini-player`)
* **Primary Role:** Unobtrusive floating audio control dock.
* **Visual Checkpoints:**
  1. **Dock Dimensions & Materiality:** Fixed 62px height, squircle `24px` border radius, frosted glass (`rgba(255, 255, 255, 0.82)` with `backdrop-filter: blur(24px)`).
  2. **Positioning & Insets:** Centered horizontally (`width: min(1200px, calc(100% - 32px))`), elevated above bottom safe area: `bottom: max(16px, env(safe-area-inset-bottom, 16px))`.
  3. **Micro Progress Line:** 2px accent track running along the top rim.
  4. **Transport Controls:** 42×42px cover art, single-line clamped text, -15s button, 42px play button, +30s button.
  5. **Overlay Invariant:** Completely disappears when Full Player (`#view-player`) is open.

### Screen 08: Mobile Viewport Adaptations (375×812 & 390×844)
* **Primary Role:** Mobile ergonomics and touch comfort.
* **Visual Checkpoints:**
  1. **Tap Targets:** All buttons and interactive controls strictly measure $\ge 44\times 44\text{px}$.
  2. **Safe Area Clearance:** Mini-player dock and bottom drawers respect `env(safe-area-inset-bottom)`.
  3. **Scroll Clearance:** Scrollable content enforces `padding-bottom: 120px` to guarantee zero occlusion by the floating dock.
  4. **Mobile Topbar:** Compact frosted topbar with sliding drawer navigation.

---

## 4. Headless Visual Verification Execution

The visual verification suite executes via Playwright in CI:

```bash
# Execute visual snapshot comparison across all 8 screens
node tools/capture-visual.mjs --compare-baseline
```

### Review Decision Matrix:
* **[ KEEP ]**: All visual checkpoints verified; layout diff $< 0.5\%$; zero accessibility lints.
* **[ REFINE ]**: Layout diff between $0.5\%$ and $2.0\%$; issue non-breaking (e.g. minor text margin); task assigned to Jules for token adjustment.
* **[ REJECT ]**: Layout diff $> 2.0\%$; visual breakage, incorrect typography fallback, or missing safe-area padding; pull request blocked.
