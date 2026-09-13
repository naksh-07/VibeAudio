# VibeAudio — Visual QA & Acceptance Criteria Specification

**Document ID:** `DOC-QA-001`  
**Status:** Verification & QA Acceptance Standard  
**Author:** Principal QA Architect & Design Systems Engineer  
**Target Matrix:** Desktop, Tablet, Mobile (Cross-Browser)  
**Cross-References:** [`DOC-DES-002`](../design/VibeAudio-Light-Design-System.md), [`DOC-QA-002`](VibeAudio-Light-UI-Visual-QA.md)  

---

## 1. Quality Philosophy & Verification Objective

The light UI redesign must satisfy strict visual, ergonomic, accessibility, and functional acceptance criteria across all supported viewports. A release candidate is accepted only when all automated contracts pass and visual inspections confirm pixel-level fidelity to the Apple Books/macOS light minimalist design standard.

---

## 2. Viewport Matrix & Acceptance Thresholds

```
┌─────────────────┬────────────────┬──────────────────────────┬────────────────────────┐
│ Device Tier     │ Resolution     │ Primary Inspection Focus │ Minimum Pass Criteria  │
├─────────────────┼────────────────┼──────────────────────────┼────────────────────────┤
│ Desktop Large   │ 1440 × 900     │ 1200px Shell, 4-Col Grid,│ Zero horizontal scroll,│
│                 │                │ 2-Col Player Layout      │ smooth glass blur.     │
├─────────────────┼────────────────┼──────────────────────────┼────────────────────────┤
│ Desktop Laptop  │ 1280 × 800     │ Topbar centering, search │ Compact navigation,    │
│                 │                │ input focus, card hover  │ balanced hero margins. │
├─────────────────┼────────────────┼──────────────────────────┼────────────────────────┤
│ Tablet          │ 1024 × 768     │ Touch hit areas, 3-Col   │ Fluid grid wrap,       │
│                 │                │ Library grid, player deck│ 44px min touch target. │
├─────────────────┼────────────────┼──────────────────────────┼────────────────────────┤
│ Mobile Standard │ 390 × 844      │ Drawer nav, single-thumb │ Safe area insets,      │
│                 │ (iPhone 14/15) │ mini dock, stacked hero  │ no content truncation. │
├─────────────────┼────────────────┼──────────────────────────┼────────────────────────┤
│ Mobile Compact  │ 375 × 812      │ Mini dock width, chapter │ Tight text clamping,   │
│                 │ (iPhone SE/Mini│ text clamp, touch targets│ 44×44px hit bounds.    │
└─────────────────┴────────────────┴──────────────────────────┴────────────────────────┘
```

---

## 3. Comprehensive Acceptance Checklists

### 3.1 Layout & Visual Alignment
* [ ] **Canvas Color:** Background across all views is strictly `#F5F5F7`. Zero leftover obsidian or pure black background patches.
* [ ] **Card Alignment:** All `.book-card` elements align to a uniform CSS Grid with 24px column and row gaps on desktop.
* [ ] **Artwork Ratio:** Book cover images strictly enforce a 2:3 vertical aspect ratio without stretching or distortion.
* [ ] **Floating Dock Centering:** Mini-player dock is horizontally centered (`left: 50%; transform: translateX(-50%)`) with equal margins.
* [ ] **No Content Clipping:** Bottom view content includes at least `120px` padding so floating dock never obstructs interactive elements.

### 3.2 Typography & Text Legibility
* [ ] **Font Pairing:** Literary titles render in `Newsreader` serif; all UI labels, metadata, and buttons render in `Inter` / system-ui.
* [ ] **No Gray-on-Gray Low Contrast:**
  * Primary text (`#1D1D1F`) achieves `≥ 13:1` contrast on `#FFFFFF` and `#F5F5F7`.
  * Secondary text (`#6E6E73`) achieves `≥ 4.5:1` contrast (WCAG AA compliant).
* [ ] **Tabular Numerals:** Scrubber elapsed time (`#current-time`), total duration (`#total-duration`), and chapter numbers use tabular figures to prevent horizontal jitter during playback.
* [ ] **Text Clamping:** Book card titles clamp to exactly 2 lines; author bylines clamp to 1 line with ellipsis (`text-overflow: ellipsis`).

### 3.3 Tactile Interaction & Focus States
* [ ] **Touch Target Sizing:** All interactive buttons (`#main-play-btn`, `#seek-back-btn`, `#play-btn`, `#mini-play-btn`, filter pills) have an active hit area `≥ 44 × 44px`.
* [ ] **Physical Press Compression:** Active state on buttons and cards triggers `transform: scale(0.97)` for immediate tactile feedback.
* [ ] **Visible Focus Ring:** Keyboard tab navigation displays an unambiguous `2px solid var(--color-accent)` focus ring with `outline-offset: 2px`.
* [ ] **Scrubber Drag Response:** Scrubbing on `#progress-bar` provides instantaneous visual thumb tracking and updates `#current-time` smoothly without lag.

### 3.4 Frosted Glass & Progressive Fallback
* [ ] **Backdrop Filter Execution:** Topbar and mini-player dock demonstrate crisp translucent glass (`blur(20px) saturate(180%)`) over scrolling content.
* [ ] **Hairline Border Definition:** Glass surfaces feature a distinct 1px border (`rgba(0, 0, 0, 0.08)`) that prevents edge blending with the background.
* [ ] **Fallback Verification:** In browsers where `backdrop-filter` is unsupported or disabled, surfaces fall back cleanly to solid `#FFFFFF` with standard card shadows.
* [ ] **Glass Discipline:** Content cards, chapter lists, and modals do NOT use glassmorphism; they remain clean, solid `#FFFFFF` or `#F2F2F7`.

### 3.5 Safe-Area & Mobile Ergonomics
* [ ] **iOS Notch & Dynamic Island:** Viewport top margin accounts for status bar; topbar does not collide with notch.
* [ ] **Home Indicator Clearance:** Mini-player dock honors `env(safe-area-inset-bottom)`:
  `bottom: max(16px, env(safe-area-inset-bottom, 16px));`
* [ ] **Drawer Gesture:** Mobile sidebar drawer `#sidebar` slides smoothly from off-screen left and covers background with `#sidebar-overlay`.
* [ ] **Zero Horizontal Body Overflow:** `overflow-x: hidden` enforced; swipe gestures do not cause accidental horizontal page shifting.

### 3.6 Motion & Vestibular Safety
* [ ] **Transition Timing:** Normal animations are fast and physics-damped (150ms–240ms, `cubic-bezier(0.2, 0, 0, 1)`).
* [ ] **Prefers Reduced Motion:** When OS reduced motion is active, all transitions, scales, and transforms are disabled or reduced to instant opacity fades.

---

## 4. Contractual Pass/Fail Criteria

| Test Identifier | Criteria Description | Mandatory Contract |
|---|---|---|
| `QA-CR-01` | Automated Invariant Suite (`npm test`) | 100% Pass (12/12 suites, 116/116 tests) |
| `QA-CR-02` | WCAG 2.1 Contrast Check | Zero color contrast violations across all text |
| `QA-CR-03` | View Switching Regression | Toggling `#view-home`, `#view-library`, `#view-player` leaves no orphan DOM elements |
| `QA-CR-04` | Mini-Player Visibility | Dock hides automatically on `#view-player` and displays on all other views when loaded |
| `QA-CR-05` | Offline Shelf Integrity | Downloaded audiobooks display green status chip and stream without network connection |
