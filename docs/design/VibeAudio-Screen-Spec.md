# VibeAudio — Screen & Information Architecture Specification

**Document ID:** `DOC-DES-003`  
**Status:** Canonical Screen Specification  
**Author:** Principal UX Architect  
**Scope:** Complete Screen & View Inventory across Web App and Landing  
**Cross-References:** [`DOC-DES-001`](VibeAudio-Light-Redesign-Brief.md), [`DOC-DES-002`](VibeAudio-Light-Design-System.md), [`DOC-DES-004`](VibeAudio-Component-Spec.md)  

---

## 1. Global Navigation Architecture

VibeAudio uses a dual-layer navigation model:
1. **Desktop / Tablet:** A sticky, floating frosted topbar (`.app-topbar`) featuring brand identity, primary segmented view tabs (`Home`, `Library`, `On This Device`), integrated search bar, and account profile trigger.
2. **Mobile:** Compact topbar with hamburger button triggering a side drawer (`#sidebar`), combined with the persistent floating bottom mini-player dock (`#mini-player`).

```
                              ┌─────────────────────────┐
                              │   SCREEN 01: LANDING    │
                              │      (index.html)       │
                              └────────────┬────────────┘
                                           │ "Start Listening"
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 APPLICATION SHELL                                      │
│                             (src/pages/app.html)                                       │
│                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              TOP NAVIGATION BAR                                  │  │
│  │   [Brand]        [ Home ]   [ Library ]   [ On This Device ]     [Search] [Acc]  │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                        │
│   ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌──────────┐ │
│   │  SCREEN 02:   │ │  SCREEN 03:   │ │  SCREEN 04:   │ │  SCREEN 05:   │ │SCREEN 06:│ │
│   │     HOME      │ │    LIBRARY    │ │   OFFLINE     │ │  FULL PLAYER  │ │ PROFILE  │ │
│   │  #view-home   │ │ #view-library │ │ #view-offline │ │  #view-player │ │#view-prof│ │
│   └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘ └──────────┘ │
│                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │              SCREEN 07: PERSISTENT FLOATING MINI-PLAYER DOCK (#mini-player)      │  │
│  │   [Cover] [Title - Chapter]                     [ 15s ]  [ ▶ / ❚❚ ]  [ 30s ]     │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                        │
│  SCREEN 08: MOBILE ADAPTATIONS (390×844 Portrait Sanctuary — Drawer, Touch, Insets)   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Screen 01: Landing Page (`index.html`)

### Purpose & User Goal
Welcomes new listeners, introduces VibeAudio's guest-first, offline-ready philosophy, showcases featured stories, and routes users directly to the active shelf without mandatory onboarding hurdles.

### Information Hierarchy & Sections:
1. **Landing Topbar:** Brand mark, reassurance chip ("Guest & Offline Ready"), "Browse library" anchor, and "Start listening" solid action.
2. **Hero Sanctuary Stage (2-Column):**
   * *Left Main Panel:* Eyebrow tag, display title (*"A calmer way to listen."*), reassuring narrative, primary CTA ("Start listening"), trust badges ("Works as a guest", "Saved on this device", "Cloud sync optional"), and dynamic metrics (`#hero-stats`).
   * *Right Spotlight Anchor:* Large spotlight card displaying the active featured audiobook cover (`#featured-cover`) and story synopsis (`#featured-spotlight`).
3. **Curated Preview Section:** Grid preview of available audiobooks (`#library-preview`).
4. **Sanctuary Feature Row:** Four clean architectural cards (Listening Sanctuary, Private Offline Shelf, Saved Moments & Notes, Optional Cloud Sync).
5. **Optional Cloud Sync Panel:** Guest callout and Clerk sign-in stage (`#sign-in-container`).
6. **Listening Lanes:** Exploratory tag cluster by mood/genre (`#category-spotlight`).
7. **Footer & Install Prompt:** PWA install trigger (`#install-app-btn`) and footer credentials.

### States:
* **Initial Loading:** Skeleton placeholders for metrics and preview cards.
* **Populated:** Real-time catalog preview populated from backend DynamoDB/API cache.

---

## 3. Screen 02: Home Shelf (`#view-home`)

### Purpose & User Goal
The personal home base for returning listeners. Prioritizes instant continuity—allowing the user to resume their active story in exactly one click.

### Information Hierarchy & Layout:
1. **Continue Listening Hero Anchor (`#home-resume-hero`):**
   * Prominent editorial banner displaying the currently active book cover (2:3 aspect ratio), status tags ("Active Story", sync pill), book title, author, current chapter pill, progress percentage, scrubber bar, and prominent "Resume Listening" CTA.
2. **On This Device Shelf (`#home-offline-shelf`):**
   * Horizontal scrollable shelf (`#home-offline-grid`) displaying audiobooks stored locally in OPFS with green downloaded check chips.
3. **Curated Discovery Row (`#home-curated-shelf`):**
   * Single restrained row (`#home-curated-grid`) of suggested audiobooks for variety without algorithmic noise.
4. **Welcoming Empty State (`#home-empty-state`):**
   * Displayed when the listener has zero listening history. Calm illustration, friendly welcoming copy, and a primary CTA routing to the Library.

### Responsive Behavior:
* **Desktop:** Resume hero renders as a spacious 2-column card (artwork + metadata).
* **Mobile:** Stacked card with full-width artwork preview and sticky action row.

---

## 4. Screen 03: Audiobook Library (`#view-library`)

### Purpose & User Goal
Comprehensive catalog discovery. Allows listeners to filter by category/mood, search by title/author, and examine unabridged audiobook cards.

### Information Hierarchy & Layout:
1. **Header Row:** Section title ("Audiobook Library"), subtitle, and asynchronous sync status banner (`#library-sync-banner`).
2. **Category Filter Toolbar (`#category-filters`):**
   * Horizontally scrollable row of segmented pill buttons (All, Fiction, Self-Help, Sci-Fi, Fantasy, etc.).
3. **Recent Searches Panel (`#recent-searches-panel`):**
   * Quick chips for recent queries, easily dismissible.
4. **Catalog Grid (`#book-grid`):**
   * Responsive grid (4 columns on desktop, 2-3 on tablet, 2 on mobile) of interactive `.book-card` components.

### States:
* **Loading:** Pulsing light skeleton cards (`.loading-spinner`).
* **Empty / Filter Zero-State:** "No audiobooks match this filter" message with a reset filter button.
* **Populated:** Cards showing authentic 2:3 book covers, duration badges, author byline, and local download status chips.

---

## 5. Screen 04: On This Device / Offline Shelf (`#view-offline`)

### Purpose & User Goal
Dedicated management of locally saved audiobooks. Ensures complete peace of mind that media is stored on-device and ready for air travel or subway commutes without Wi-Fi.

### Information Hierarchy & Layout:
1. **Header Row:** Title ("On This Device"), descriptive subtitle, and "Import Audio" file picker trigger (`#import-audiobook-input`).
2. **Storage Insights Summary (`#offline-insights`):**
   * Clean metric strip displaying: Total Storage Used (MB/GB), Available Quota, Saved Books count, and Chapter tally.
3. **Offline Grid (`#offline-grid`):**
   * Catalog cards restricted exclusively to books verified in local OPFS storage.

### States:
* **Empty State:** Distinct illustration explaining how to download audiobooks for offline use.
* **Active Storage:** Live quota gauge updating as audiobooks are saved or removed.

---

## 6. Screen 05: Full Player & Book Detail (`#view-player`)

### Purpose & User Goal
The heart of VibeAudio. Deep, immersive, uninterrupted listening with high-resolution artwork, tactile transport deck, chapter navigation, and timestamped notes.

### Information Hierarchy & Layout:
1. **Top Actions Bar:** Glass back button (`#back-btn`) to return to shelf; offline readiness badge (`#player-offline-status-chip`).
2. **Detail & Hero Presentation Card (`.player-header-card`):**
   * High-resolution book cover artwork (`#detail-cover`) with subtle ambient bloom (`#blur-bg`).
   * Book Title (`#detail-title`) set in dignified literary serif `Newsreader`.
   * Author byline (`#detail-author`), genre pill tags (`#detail-pills`), and narrative summary (`#detail-summary`).
   * Primary action row: "Listen Now" (`#main-play-btn`), "Save for Offline" (`#download-book-btn`), and "Share" (`#share-book-btn`).
3. **Dedicated Transport Deck (`.player-transport-deck`):**
   * **Position Indicator Line:** Current chapter part name (`#player-current-part`) and calculated time remaining (`#player-time-remaining`).
   * **Tactile Range Scrubber (`.player-scrubber-container`):** Elapsed timecode (`#current-time`), interactive slider (`#progress-bar`), and total duration (`#total-duration`).
   * **Apple-Inspired Transport Controls (`.player-transport-controls`):**
     * Speed selector pill (`#speed-btn`) — cycle 0.5x, 1.0x, 1.25x, 1.5x, 2.0x.
     * Jump Backward 15s (`#seek-back-btn`).
     * Large circular Play/Pause toggle (`#play-btn`).
     * Jump Forward 30s (`#seek-fwd-btn`).
     * Sleep Timer popover toggle (`#sleep-timer-btn`).
4. **Two-Column Secondary Zone (`.player-two-column`):**
   * *Left Column:* Chapter Playlist (`#chapter-list`) with part badges, active playing indicators, and individual chapter download icons.
   * *Right Side Stack:*
     * Saved Moments / Bookmarks (`#bookmark-list`) with one-click "Save moment" trigger (`#bookmark-current-btn`).
     * Timestamped Notes (`#comments-list`) with inline composer (`#comment-input`, `#post-comment-btn`).

---

## 7. Screen 06: Profile, Storage & Sync (`#view-profile`)

### Purpose & User Goal
Personal identity, listening achievements, and on-device storage hygiene. Enables listeners to inspect guest listening continuity (or authenticate with Clerk), view milestones, inspect local OPFS storage quota, and safely purge device downloads without touching cloud progress.

### Information Hierarchy & Layout:
1. **User Identity Header:** 64×64px avatar with warm initial (`#profile-avatar`), display name (`#user-name-display`, "Guest Listener" or Clerk username), and status chip ("Guest Shelf Active" or "Synced").
2. **Listening Milestones Grid:** 4-column metric strip (`#profile-stat-finished` Books Finished, `#profile-stat-hours` Hours Listened, `#profile-stat-active` Active Stories, `#profile-stat-bookmarks` Saved Moments).
3. **OPFS Storage Management Panel:**
   * Quota gauges: `#offline-storage-used` (e.g. "1.2 GB Saved Locally"), `#offline-storage-quota` (e.g. "48.6 GB Available"), `#offline-storage-books` (Saved Books count), `#offline-storage-chapters` (Saved Chapters count).
   * Destructive action button: "Clear Offline Audio" (`#clear-offline-downloads-btn`) styled in subtle danger tokens (`rgba(255, 59, 48, 0.10)` background, `#D70015` text).
4. **Session & Sync Controls:**
   * "Sync Progress" button (`#sync-profile-btn`) to trigger on-demand sync with AWS DynamoDB (for signed-in users).
   * "Sign Out / Reset Session" button (`window.app.logout()`).

---

## 8. Screen 07: Persistent Mini-Player Dock (`#mini-player`)

### Purpose & User Goal
Provides continuous, uninterrupted listening context while the listener browses Home, Library, Offline, or Profile views. Positioned fixed at the bottom of the viewport directly above safe-area insets.

### Information Hierarchy & Layout (Embedded in Living App Shell):
1. **Micro Progress Line:** 2px high accent progress line along the top border (`#mini-progress-line-fill`) in `#C64E00`.
2. **Track Info Zone (`#mini-track-info`):** Square book cover thumbnail (`#mini-cover`, 42×42px, 6px radius), story title in `Newsreader` (`#mini-title`), chapter name in `Inter` (`#mini-chapter`), and upward chevron indicator. Tapping anywhere in this hit area smoothly opens the Full Player (`#view-player`).
3. **Mini Transport Deck:**
   * Jump Backward 15s (`#mini-seek-back-btn`): 36px circular ghost button.
   * Circular Play/Pause button (`#mini-play-btn`): 42px solid accent button (`#C64E00`) with pure white `#FFFFFF` play/pause glyph and subtle warm ambient glow.
   * Jump Forward 30s (`#mini-seek-fwd-btn`): 36px circular ghost button.

### Shell Relationship & Invariants:
* **Clearance:** Content views maintain `padding-bottom: 120px` so that the mini dock never obstructs cards or interactive controls.
* **Hiding Invariant:** Automatically hidden via CSS whenever the Full Player (`#view-player:not(.hidden)`) is active.

---

## 9. Screen 08: Mobile Adaptations (390×844 Portrait Sanctuary)

### Purpose & User Goal
Establishes the mobile adaptation strategy using the Home view (`#view-home`) as the canonical reference. Optimizes the entire listening experience for one-handed thumb ergonomics, iOS safe areas, and compact vertical rhythm.

### Information Hierarchy & Layout (Mobile Portrait 390×844):
1. **Compact Frosted Topbar:** 54px height, sticky at top with safe-area inset. Features hamburger button (`#menu-btn`, 44×44px hit area), brand lockup, catalog search trigger, and account profile icon. Center navigation tabs collapse into the slide drawer.
2. **Slide Navigation Drawer (`#sidebar`):** 280px width, slides smoothly from the left over a dimmed backdrop (`#sidebar-overlay`). Hosts primary view links (`Home`, `Library`, `On This Device`, `Listening History`, `About`, `Install App`).
3. **Mobile Continue Listening Hero:** Reconfigured into a vertical stack with a 120px 2:3 cover preview, chapter pill, progress track, and full-width "Resume Listening" touch target (48px height).
4. **Mobile Catalog Grid:** 2-column grid (`repeat(2, 1fr)`) with 12px gap, 44px minimum tap targets, and clean two-line title clamping.
5. **Safe-Area Dock Integration:** Mini-player dock expands to `calc(100% - 24px)` with `bottom: max(12px, env(safe-area-inset-bottom, 12px))` to ensure zero collision with the iOS home swipe indicator.

---

## 10. Secondary Utility Views

* **Listening History (`#view-history`):** Chronological timeline of listened audiobooks with last played timestamps, progress percentages, and quick resume triggers.
* **About Sanctuary (`#view-about`):** Manifesto on distraction-free listening, architecture highlights (zero build step, OPFS storage, privacy-first design), version tag ("Listening-First Edition"), and open source credits.

