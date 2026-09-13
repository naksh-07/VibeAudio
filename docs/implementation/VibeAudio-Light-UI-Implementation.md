# VibeAudio — Technical Implementation Specification: Light UI Redesign

**Document ID:** `DOC-IMP-001`  
**Status:** Implementation Architecture & Safety Blueprint  
**Author:** Principal UX Engineer & Systems Architect  
**Scope:** File Mapping, DOM Contracts, JS Coupling, and CSS Migration Architecture  
**Cross-References:** [`DOC-PRD-001`](../product/VibeAudio-Light-UI-PRD.md), [`DOC-DES-002`](../design/VibeAudio-Light-Design-System.md)  

---

## 1. Architectural Codebase Mapping

The redesign maps strictly into the existing modular stylesheet architecture without altering the ES module hierarchy or backend endpoints:

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        CSS CODEBASE MAPPING LAYER                          │
├──────────────────────────┬─────────────────────────────────────────────────┤
│ Target Stylesheet        │ Functional Scope & Redesign Responsibility       │
├──────────────────────────┼─────────────────────────────────────────────────┤
│ 1. base.css              │ Design tokens, light theme custom properties,   │
│                          │ typography, reset, shell grid, focus rings.     │
├──────────────────────────┼─────────────────────────────────────────────────┤
│ 2. components.css        │ Shared .book-card, resume hero, buttons,        │
│                          │ filter pills, badges, status chips, search box. │
├──────────────────────────┼─────────────────────────────────────────────────┤
│ 3. app-sections.css      │ View layouts (#view-home, #view-library,        │
│                          │ #view-offline, #view-profile), empty states.    │
├──────────────────────────┼─────────────────────────────────────────────────┤
│ 4. player.css            │ Dedicated transport deck, scrubber input,       │
│                          │ chapter list, mini-player dock (#mini-player).  │
├──────────────────────────┼─────────────────────────────────────────────────┤
│ 5. player-premium.css    │ Micro-interactions, scrubber focus states,      │
│                          │ tactile chapter active borders.                 │
├──────────────────────────┼─────────────────────────────────────────────────┤
│ 6. landing.css           │ Landing page hero, preview grid, features, auth.│
├──────────────────────────┼─────────────────────────────────────────────────┤
│ 7. cover-media.css       │ 2:3 aspect ratio enforcement, ambient bloom.    │
└──────────────────────────┴─────────────────────────────────────────────────┘
```

---

## 2. DOM & Contract Invariants (Do Not Break)

The test suite (`tests/ui-contracts.test.mjs`) strictly asserts the presence of specific DOM IDs and structure in `app.html` and `index.html`. During the redesign, **these IDs must remain untouched in HTML**:

### 2.1 View Containers (Routing Contract)
* `#view-home` — Main home shelf.
* `#view-library` — Full catalog view.
* `#view-offline` — On this device offline view.
* `#view-history` — Listening history view.
* `#view-profile` — Account and storage management.
* `#view-about` — About information card.
* `#view-player` — Full player and book detail view.

### 2.2 Home View Structural IDs
* `#home-resume-hero` — Populated dynamically by `ui.js`.
* `#home-offline-shelf` & `#home-offline-grid` — Populated by `offline-shelf.js`.
* `#home-curated-shelf` & `#home-curated-grid` — Populated by `ui.js`.
* `#home-empty-state` — Toggled when no books have progress.

### 2.3 Navigation & Search IDs
* `[data-nav-view="home"]`, `[data-nav-view="library"]`, `[data-nav-view="offline"]` — Navigation destination buttons.
* `#search-input` & `#search-clear-btn` — Search input and clear button.
* `#menu-btn`, `#sidebar`, `#close-sidebar` — Mobile drawer controls.

### 2.4 Mini-Player Dock IDs
* `#mini-player` — Persistent container.
* `#mini-track-info` — Expandable click trigger.
* `#mini-cover`, `#mini-title`, `#mini-chapter` — Metadata display.
* `#mini-progress-line-fill` — Micro progress track.
* `#mini-seek-back-btn`, `#mini-play-btn`, `#mini-seek-fwd-btn` — Transport buttons.

### 2.5 Full Player Transport Deck IDs
* `#back-btn` — Back to shelf button.
* `#detail-cover`, `#detail-title`, `#detail-author`, `#detail-summary`, `#detail-pills`.
* `#main-play-btn`, `#download-book-btn`, `#remove-offline-book-btn`, `#share-book-btn`.
* `#progress-bar` — Range scrubber input.
* `#current-time`, `#total-duration` — Tabular timecodes.
* `#speed-btn`, `#seek-back-btn`, `#play-btn`, `#seek-fwd-btn`, `#sleep-timer-btn`.
* `#chapter-list`, `#total-chapters` — Playlist container and tally.
* `#bookmark-list`, `#bookmark-current-btn` — Saved moments.
* `#comments-list`, `#comment-input`, `#post-comment-btn` — Notes and timestamps.
* `#audio-element` — Native HTML5 audio element.

---

## 3. JavaScript to CSS Coupling (Interaction Invariants)

Several JavaScript modules dynamically manipulate CSS classes and inline custom properties. The redesign must accommodate these bindings:

### 3.1 Adaptive Theming Hook (`ui-player-helpers.js`)
* **Mechanism:** When an audiobook plays, `extractPaletteFromImage()` extracts color tokens via ColorThief and invokes `setCssVariables()`.
* **Coupling Risk:** Previously, `buildTheme()` calculated dark background colors:
  ```javascript
  const depth = mixColor(depthBase, [0, 0, 0], 0.48);
  const shell = mixColor(depth, [8, 12, 18], 0.6);
  ```
* **Required Light Adaptation:** The JS theme builder must blend extracted colors into a light canvas palette:
  * Blend shell with `[245, 245, 247]` instead of `[8, 12, 18]`.
  * Ensure `--theme-title` and `--theme-text` output dark legible values (`#1D1D1F`) rather than white text.
  * Ensure `--theme-player-overlay` produces a gentle high-key bloom rather than a dark vignette.

### 3.2 View Switching (`ui.js` & `ui-dom.js`)
* Views are toggled via the `.hidden` class:
  ```javascript
  element.classList.add('hidden');
  element.classList.remove('hidden');
  ```
* `body.player-mode` or `body.view-is-player` is added when the full player opens to hide the mini-player:
  ```css
  body.player-mode #mini-player,
  #view-player:not(.hidden) ~ #mini-player {
      display: none !important;
  }
  ```
  This CSS rule must be preserved verbatim.

### 3.3 Offline Download State Machine Attributes
* Cards dynamically receive `data-status` attributes:
  * `[data-status="downloaded"]`
  * `[data-status="queued"]`
  * `[data-status="downloading"]`
  * `[data-status="update_available"]`
  * `[data-status="failed"]`
* CSS selectors must style each state according to the light semantic status colors.

---

## 4. Accessibility (a11y) Invariants

The following HTML attributes are verified by automated tests (`tests/accessibility.test.mjs`) and must never be altered or removed:

```html
<!-- Contracted ARIA Labels -->
<button id="menu-btn" aria-label="Open navigation menu"></button>
<input id="search-input" aria-label="Search audiobooks">
<button id="search-clear-btn" aria-label="Clear search"></button>
<button id="main-play-btn" aria-label="Listen Now"></button>
<button id="download-book-btn" aria-label="Save for offline"></button>
<button id="speed-btn" aria-label="Playback speed options"></button>
<button id="seek-back-btn" aria-label="Jump backward 15 seconds"></button>
<button id="play-btn" aria-label="Play or Pause"></button>
<button id="seek-fwd-btn" aria-label="Jump forward 30 seconds"></button>
<button id="sleep-timer-btn" aria-label="Sleep timer options"></button>
<div id="mini-track-info" aria-label="Open full player view"></div>
<button id="mini-seek-back-btn" aria-label="Jump backward 15 seconds"></button>
<button id="mini-play-btn" aria-label="Play or Pause"></button>
<button id="mini-seek-fwd-btn" aria-label="Jump forward 30 seconds"></button>

<!-- Contracted Range Attributes -->
<input type="range" id="progress-bar" aria-label="Playback progress" aria-valuemin="0" aria-valuemax="100">

<!-- Contracted Live Regions -->
<div id="library-sync-banner" aria-live="polite"></div>
<div id="history-sync-banner" aria-live="polite"></div>
```

---

## 5. PWA & Service Worker Safe Area Constraints

1. **Precache Inventory:** `service-worker.js` caches 40 local assets. Renaming existing CSS or JS files breaks Service Worker precaching. All styling updates must happen in-place within the existing files.
2. **Viewport Meta & Theme Color:**
   * In `index.html` and `app.html`, `<meta name="theme-color" content="#F5F5F7">` aligns the mobile browser URL bar and notch background with the canvas.
   * `<meta name="apple-mobile-web-app-status-bar-style" content="default">` ensures crisp black icons on the iOS status bar.
