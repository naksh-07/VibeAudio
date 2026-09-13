# VibeAudio — Component Specification: Light Design System

**Document ID:** `DOC-DES-004`  
**Status:** Component Architecture Specification  
**Author:** Principal Design Systems Engineer  
**Scope:** Reusable UI Component Library  
**Cross-References:** [`DOC-DES-002`](VibeAudio-Light-Design-System.md), [`DOC-IMP-001`](../implementation/VibeAudio-Light-UI-Implementation.md)  

---

## 1. Component 01: Floating App Topbar (`.app-topbar`)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [Brand Mark + Title]   [ Home* ]  [ Library ]  [ On This Device ]   [ 🔍 Search... ] [👤] │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

* **Purpose:** Primary application navigation, destination switcher, search entry point, and profile trigger.
* **Anatomy:**
  * Left: Mobile drawer trigger (`#menu-btn`), Brand lockup with custom SVG logo and subtitle.
  * Center: Segmented destination pills (`[data-nav-view="home|library|offline"]`).
  * Right: Search shell (`#search-input`, `#search-clear-btn`), Profile avatar trigger.
* **Material & Dimensions:**
  * Height: 62px
  * Background: `var(--color-surface-translucent)` (`rgba(255, 255, 255, 0.78)`)
  * Backdrop Filter: `blur(20px) saturate(180%)`
  * Border: `1px solid var(--color-border)` (`rgba(0, 0, 0, 0.08)`)
  * Radius: `var(--radius-sheet)` (24px)
  * Shadow: `var(--shadow-card)`
* **States & Interactions:**
  * Inactive Nav Item: Color `var(--color-text-secondary)`, no background.
  * Active Nav Item: Color `var(--color-text-primary)`, background `var(--color-surface-2)`, font weight 600.
  * Focus Visible: `2px solid var(--color-accent)`.
* **Mobile Behavior:** Center navigation pills hide; mobile hamburger icon (`#menu-btn`) reveals left navigation drawer (`#sidebar`).

---

## 2. Component 02: Audiobook Catalog Card (`.book-card`)

```
┌────────────────────────┐
│ [Book Cover Image]     │ ◄── 2:3 authentic aspect ratio
│ [Genre Badge] [Offline]│
├────────────────────────┤
│ KICKER / GENRE         │
│ Audiobook Title        │ ◄── Newsreader serif, 2-line clamp
│ Author Byline          │
│ ══════════ 45%         │ ◄── Progress track (if active)
└────────────────────────┘
```

* **Purpose:** The core discovery artifact. Represents a single audiobook across Library, Search, and Offline grids.
* **Anatomy:**
  * Cover Media (`.book-card-media`): 2:3 vertical aspect ratio, squircle border radius.
  * Badges: Activity badge (Top-Left), Offline status chip (Bottom-Left), Source type (Top-Right).
  * Content Block (`.card-content`): Genre kicker, Title (`<h3>`), Author (`.card-author`), optional Progress Bar.
* **Dimensions & Styles:**
  * Background: `var(--color-surface-1)` (`#FFFFFF`)
  * Border: `1px solid var(--color-border)` (`rgba(0, 0, 0, 0.08)`)
  * Radius: `var(--radius-card)` (14px)
  * Shadow: `var(--shadow-subtle)`
* **States:**
  * **Hover:** `transform: translateY(-3px)`, shadow `var(--shadow-card)`, border `var(--color-border-strong)`. Cover image scales to `1.03` with smooth transition.
  * **Active / Pressed:** `transform: translateY(-1px) scale(0.99)`.
  * **In Progress (`.has-progress`):** Displays a 4px high accent progress track (`.card-progress-track`).
  * **Finished (`.is-finished`):** Displays a subtle success checkmark badge.
* **Accessibility:** Full card wrapped in accessible keyboard focus ring; `tabindex="0"`, `role="button"`.

---

## 3. Component 03: One-Tap Resume Hero Card (`.resume-hero-card`)

* **Purpose:** Primary visual anchor on the Home view. Provides instant, single-click resumption of the active audiobook.
* **Anatomy:**
  * Left: High-resolution artwork cover (140px wide, 2:3 aspect ratio) with offline status badge.
  * Right: Kicker ("ACTIVE STORY"), Sync status pill, Title in `Newsreader`, Author byline, Chapter pill ("Chapter 4"), Progress text ("48% complete"), 5px high progress bar, and primary "Resume Listening" action button.
* **Dimensions & Styles:**
  * Background: `var(--color-surface-1)` (`#FFFFFF`)
  * Border: `1px solid var(--color-border-strong)` (`rgba(0, 0, 0, 0.12)`)
  * Radius: `var(--radius-panel)` (18px)
  * Shadow: `var(--shadow-card)`
  * Subtle Ambient Accent: Low-opacity radial warm gradient in top right corner.
* **Mobile Behavior:** Stacks vertically into single-column presentation; button expands to full width.

---

## 4. Component 04: Button System

```
[ Primary Action ]   [ Secondary Button ]   [ (▶) Round 56px ]   [ Pill Filter ]
```

### 4.1 Primary Solid Button (`.solid-btn`, `.action-btn`)
* **Purpose:** High-priority actions ("Start Listening", "Listen Now", "Resume").
* **Dimensions:** Min-height 44px, padding 10px 22px, border-radius 999px.
* **Colors:** Background `var(--color-accent)` (`#E65A00`), text `#FFFFFF`, border none.
* **Shadow:** `0 4px 14px rgba(230, 90, 0, 0.28)`.
* **Hover:** Background `var(--color-accent-hover)` (`#CC4E00`), `transform: translateY(-1px)`, shadow `0 6px 20px rgba(230, 90, 0, 0.36)`.
* **Active:** `transform: scale(0.97)`.

### 4.2 Secondary Button (`.btn-secondary`, `.ghost-btn`)
* **Purpose:** Secondary actions ("Save for Offline", "Share", "Browse Library").
* **Colors:** Background `var(--color-surface-2)` (`#F2F2F7`), text `var(--color-text-primary)` (`#1D1D1F`), border `1px solid var(--color-border)`.
* **Hover:** Background `var(--color-surface-3)` (`#E5E5EA`), border `var(--color-border-strong)`.

### 4.3 Danger Button (`.btn-danger`, `.subtle-danger`)
* **Purpose:** Destructive actions ("Clear Offline Audio", "Remove Download").
* **Colors:** Background `var(--color-danger-soft)` (`rgba(255, 59, 48, 0.1)`), text `var(--color-danger)` (`#D70015`), border `1px solid var(--color-danger-border)`.

---

## 5. Component 05: Category Filter Pills (`.filter-btn`)

* **Purpose:** Instant category/genre filtering in Library and Discovery views.
* **Dimensions:** Min-height 38px, padding 8px 16px, border-radius 999px.
* **Inactive State:** Background `var(--color-surface-1)`, text `var(--color-text-secondary)`, border `1px solid var(--color-border)`.
* **Active State (`.active`):** Background `var(--color-accent)` (`#E65A00`), text `#FFFFFF`, font-weight 600, border none, shadow `var(--shadow-subtle)`.
* **Interaction:** Horizontal scroll without scrollbar clutter (`scrollbar-width: none`).

---

## 6. Component 06: Floating Mini-Player Dock (`.player-bar.mini-dock`)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ═════════════════════════════════ 62% ═══════════════════════════════════════════════ │ ◄── 2px accent track
│ [Cover 42px]  Title of the Book - Chapter 3          [ -15s ]   ( ▶ )   [ +30s ]    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

* **Purpose:** Persistent listening control bar fixed to viewport bottom.
* **Dimensions & Materials:**
  * Width: `min(1200px, calc(100% - 32px))`
  * Height: 62px
  * Positioning: `position: fixed; bottom: max(16px, env(safe-area-inset-bottom, 16px)); left: 50%; transform: translateX(-50%);`
  * Background: `rgba(255, 255, 255, 0.82)` with `backdrop-filter: blur(24px) saturate(190%)`
  * Border: `1px solid var(--color-border-strong)` (`rgba(0, 0, 0, 0.12)`)
  * Radius: `var(--radius-sheet)` (24px)
  * Shadow: `var(--shadow-sheet)` (`0 16px 44px rgba(0, 0, 0, 0.10)`)
* **Interactive Elements:**
  * Top progress indicator (`.mini-progress-line`): 2px height, accent fill.
  * Track info trigger (`#mini-track-info`): Covers 42×42px thumbnail, title, chapter. Entire area clickable to open Full Player.
  * Transport buttons: Back 15s (`#mini-seek-back-btn`), Play Circle (`#mini-play-btn`, 42px solid accent circle with white icon), Forward 30s (`#mini-seek-fwd-btn`).
* **Contract:** Must be completely hidden when `#view-player` is active.

---

## 7. Component 07: Dedicated Full Player Transport Deck (`.player-transport-deck`)

* **Purpose:** High-precision audio playback controls inside the Full Player view.
* **Anatomy:**
  1. Position Line: Chapter indicator (`#player-current-part`) and Time remaining countdown (`#player-time-remaining`).
  2. Scrubber Container:
     * Current timecode (`#current-time`, tabular mono).
     * Input Range Slider (`#progress-bar`): 6px height track, 18px circular white thumb with shadow.
     * Total duration timecode (`#total-duration`, tabular mono).
  3. Control Deck:
     * Speed selector (`#speed-btn`): 40px rounded button.
     * Jump -15s (`#seek-back-btn`): Pill button with step icon and label.
     * Main Play/Pause (`#play-btn`): 56×56px circular accent button with elevated drop shadow.
     * Jump +30s (`#seek-fwd-btn`): Pill button with forward icon and label.
     * Sleep Timer (`#sleep-timer-btn`): 40px circular button.
* **Background & Surface:** Solid white `var(--color-surface-1)` with `1px solid var(--color-border)` and `var(--radius-panel)` (18px).

---

## 8. Component 08: Chapter Playlist Row (`.chapter-item`)

* **Purpose:** Displays individual parts/chapters of the loaded audiobook.
* **Anatomy:**
  * Chapter Number: Tabular mono ("01", "02").
  * Chapter Title: Primary title and duration subtitle.
  * Right Action: Individual chapter download state icon.
* **Dimensions & Styles:**
  * Padding: 12px 14px
  * Background: `var(--color-surface-2)` (`#F2F2F7`)
  * Border: `1px solid var(--color-border)`
  * Radius: `var(--radius-md)` (10px)
* **Active Playing State (`.active`):**
  * Background: `var(--color-accent-soft)` (`rgba(230, 90, 0, 0.08)`)
  * Border Color: `var(--color-accent-border)`
  * Indicator: Inset 3px accent bar on left border; chapter title text turns `var(--color-accent)`.

---

## 9. Component 09: Status Badges & Chips

* **Offline Status Chip (`.card-offline-badge`, `[data-status="downloaded"]`):**
  * Background: `var(--color-success-soft)` (`rgba(52, 199, 89, 0.12)`)
  * Border: `1px solid var(--color-success-border)`
  * Text: `var(--color-success)` (`#248A3D`), 11px uppercase bold.
  * Icon: `#icon-check-circle`.
* **Activity Badge (`.card-activity-badge.continue`):**
  * Background: `var(--color-accent-soft)`
  * Border: `1px solid var(--color-accent-border)`
  * Text: `var(--color-accent)`.
* **Source Badge (`.source-type-badge.yt-badge`):**
  * Background: `rgba(230, 90, 0, 0.08)`
  * Text: `var(--color-accent)`.
