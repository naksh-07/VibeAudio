# VibeAudio — Product Requirements Document (PRD): Light UI Redesign

**Document ID:** `DOC-PRD-001`  
**Status:** Approved Requirements  
**Author:** Technical Product Architect & UX Engineer  
**Scope:** Frontend UI/UX Redesign (Landing, App Shell, Component Architecture)  
**Cross-References:** [`DOC-DES-001`](../design/VibeAudio-Light-Redesign-Brief.md), [`DOC-DES-002`](../design/VibeAudio-Light-Design-System.md)  

---

## 1. Product Objectives & Business Context

VibeAudio is a lightweight, offline-first Progressive Web App designed as a distraction-free personal audiobook sanctuary. Following the migration to DynamoDB and enhanced OPFS storage capabilities, the product is transitioning its visual interface from a dark obsidian aesthetic to a **light, tactile, Apple-inspired editorial sanctuary**.

### Primary Goals:
1. **Luminous Light Aesthetic:** Deliver a crisp, glare-free light interface inspired by Apple Books and macOS Sequoia, utilizing an off-white canvas (`#F5F5F7`) and pure white card surfaces (`#FFFFFF`).
2. **Elevated Tactility & Material Depth:** Introduce subtle, hardware-grade micro-interactions, spring animations, and selective frosted glass materials (`backdrop-filter`) without visual clutter.
3. **Flawless Functional Preservation:** Guarantee 100% preservation of all existing playback engines, offline OPFS mechanisms, guest session logic, sync queues, and accessibility invariants.
4. **Enhanced Mobile & Tablet Ergonomics:** Establish a floating, thumb-reachable mini-dock and full player modal sheet optimized for iOS Safari and mobile PWA standalone mode.

### Non-Goals:
* **No Architecture Rewrite:** No migration to React, Vue, Svelte, or any heavy frontend framework. The codebase remains zero-build vanilla ES modules.
* **No Backend or Database Alterations:** AWS Lambda handlers, DynamoDB tables, and Cloudflare workers remain unchanged.
* **No Icon System Overhaul:** The 66-symbol custom SVG sprite (`frontend/src/icons/icons.svg`) and locked vector brand mark remain canonical.
* **No Commercial Storefront Features:** No shopping cart, credit bundles, ratings systems, or algorithmic recommendation carousels.

---

## 2. Functional Preservation Contract (The Immutable Core)

The UI redesign is strictly visual and structural. Under no circumstances may a styling or DOM enhancement alter, break, or regress any of the following core functional systems:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   FUNCTIONAL PRESERVATION CONTRACT                      │
├──────────────────────┬───────────────────────────────────────────────────┤
│ Subsystem            │ Mandatory Invariant Behavior                      │
├──────────────────────┼───────────────────────────────────────────────────┤
│ 1. Playback Engine   │ HTML5 audio element (`#audio-element`) lifecycle, │
│                      │ monotonic load token race condition prevention,   │
│                      │ auto-play token validation, YouTube audio host.   │
├──────────────────────┼───────────────────────────────────────────────────┤
│ 2. Scrubber & Seek   │ Bidirectional progress sync between audio time    │
│                      │ and range input (`#progress-bar`), jump -15s/30s. │
├──────────────────────┼───────────────────────────────────────────────────┤
│ 3. Speed & Sleep     │ Variable speed options (0.5x to 2.0x), sleep      │
│                      │ timer with smooth exponential audio fadeout.      │
├──────────────────────┼───────────────────────────────────────────────────┤
│ 4. OPFS Offline      │ Multi-part chunked download state machine, local  │
│                      │ chapter streaming from OPFS via file handles.     │
├──────────────────────┼───────────────────────────────────────────────────┤
│ 5. Guest Continuity  │ Zero sign-in gate. Guest progress, bookmarks,     │
│                      │ and downloads preserved deterministically.        │
├──────────────────────┼───────────────────────────────────────────────────┤
│ 6. Cloud Sync        │ Background sync queue, deduplication, conflict    │
│                      │ resolution, and Clerk auth session resumption.    │
├──────────────────────┼───────────────────────────────────────────────────┤
│ 7. Moments & Notes   │ Timestamp-locked bookmark creation and note       │
│                      │ insertion into chapter timeline without pause.    │
├──────────────────────┼───────────────────────────────────────────────────┤
│ 8. PWA & Native      │ Web App Manifest, Service Worker offline caching, │
│                      │ Media Session API, App Badging, OS Share Target.  │
├──────────────────────┼───────────────────────────────────────────────────┤
│ 9. a11y Contracts    │ All 14 contracted `aria-label` attributes, focus  │
│                      │ indicators, and live regions from tests.          │
└──────────────────────┴───────────────────────────────────────────────────┘
```

---

## 3. User Experience & Flow Requirements

### 3.1 Flow A: First-Time Guest Listener
* **Entry:** User navigates to `/` (Landing) or `/src/pages/app.html#home`.
* **Expectation:** Immediate browsing without login modals or cookie walls.
* **Redesign Requirement:** Clear visual indicators demonstrating guest status ("Guest Shelf Active"), transparent reassurance badges ("Works as a guest", "Saved on this device").

### 3.2 Flow B: Active Listening Continuity (One-Tap Resume)
* **Entry:** Returning user opens `/src/pages/app.html#home`.
* **Expectation:** If an in-progress book exists, the "Continue Listening" hero anchor is immediately visible at the top of the Home view.
* **Redesign Requirement:** A prominent editorial hero card featuring the audiobook cover, exact elapsed chapter, visual progress bar, and an unmistakable primary "Resume" button.

### 3.3 Flow C: Exploration to Playback Transition
* **Trigger:** Listener taps an audiobook card in the Library grid.
* **Transition:** Smooth transition to `#view-player`.
* **Redesign Requirement:** The full player header card presents high-resolution book cover artwork with a subtle, non-intrusive ambient light bloom, complete metadata, and a dedicated transport deck.

### 3.4 Flow D: Floating Mini-Player Dock Continuity
* **Trigger:** Listener starts playback and navigates back to Home, Library, or On This Device.
* **Expectation:** A persistent floating dock stays anchored to the viewport bottom.
* **Redesign Requirement:** Frosted glass dock with a 2px top progress bar, responsive tap-to-expand hit area, and tactile play/pause and jump buttons. Must automatically hide when the full player view is active.

---

## 4. Platform & Responsive Requirements

| Breakpoint Tier | Viewport Width | Target Devices | Layout Archetype |
|---|---|---|---|
| **Desktop Large** | `≥ 1440px` | iMac, Studio Display, External Monitors | Centered 1200px shell, 4-column catalog, 2-column player layout |
| **Desktop Standard**| `1280px - 1439px` | MacBook Pro 14"/16", Laptops | Centered 1200px shell, 3-to-4 column catalog, 2-column player |
| **Tablet Landscape**| `1024px - 1279px` | iPad Pro 11"/12.9", iPad Air | Fluid grid, 3-column catalog, side-by-side player deck |
| **Tablet Portrait** | `768px - 1023px` | iPad Mini, Tablet portrait | 2-to-3 column catalog, stacked player columns |
| **Mobile Standard** | `375px - 430px` | iPhone 13/14/15/16 Pro, Galaxy S | Single/2-column catalog, full-width modal sheet player, mobile navigation drawer |

### Safe Area & PWA Constraints:
* Full support for `env(safe-area-inset-top)` and `env(safe-area-inset-bottom)` to accommodate the dynamic island, home indicator, and notch.
* Mini-player bottom positioning: `bottom: max(16px, env(safe-area-inset-bottom, 16px))`.

---

## 5. Accessibility (a11y) Requirements

1. **Color Contrast:** All body text (`#1D1D1F`) against background (`#F5F5F7` / `#FFFFFF`) must achieve a contrast ratio `≥ 7.0:1` (exceeding WCAG AAA). Secondary text (`#6E6E73`) must achieve `≥ 4.5:1` (WCAG AA).
2. **Touch Targets:** Every interactive element (transport buttons, filter pills, close triggers) must feature a minimum clickable bounding box of `44 × 44px`.
3. **Visible Focus:** Clear focus ring (`2px solid var(--color-accent)`, outline-offset `2px`) on `:focus-visible` for keyboard navigation across all interactive elements.
4. **Motion Preference:** Immediate compliance with `@media (prefers-reduced-motion: reduce)`. All CSS animations and transitions set to zero duration or subtle opacity fades.
5. **Screen Readers:** ARIA live regions (`aria-live="polite"`) maintained on sync banners and download progress chips.

---

## 6. Browser Compatibility Matrix

* **Safari (iOS & iPadOS 16+ / macOS Ventura+):** Full support for OPFS, Web Audio API, Service Workers, Backdrop Filter, Safe Area Insets.
* **Chrome / Chromium (v110+):** Full support for Badging API, Media Session, Background Fetch, OPFS.
* **Firefox (v115+ ESR / Latest):** IndexedDB fallback for OPFS where needed, full CSS custom property support.
* **Edge (v110+):** Full Windows desktop PWA standalone support.
