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
                              │      LANDING PAGE       │
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
│   │  SCREEN 01:   │ │  SCREEN 02:   │ │  SCREEN 03:   │ │  SCREEN 04:   │ │SCREEN 05:│ │
│   │     HOME      │ │    LIBRARY    │ │   OFFLINE     │ │  FULL PLAYER  │ │ PROFILE  │ │
│   │  #view-home   │ │ #view-library │ │ #view-offline │ │  #view-player │ │#view-prof│ │
│   └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘ └──────────┘ │
│                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                    FLOATING MINI-PLAYER DOCK (#mini-player)                      │  │
│  │   [Cover] [Title - Chapter]                     [ 15s ]  [ ▶ / ❚❚ ]  [ 30s ]     │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
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

## 7. Screen 06: Persistent Mini-Player Dock (`#mini-player`)

### Purpose & User Goal
Provides continuous listening context while the listener browses other views. Always accessible, zero obstruction.

### Information Hierarchy & Layout:
1. **Micro Progress Line:** 2px high accent progress line along the top border (`#mini-progress-line-fill`).
2. **Track Info Zone (`#mini-track-info`):** Square book cover thumbnail (`#mini-cover`), story title (`#mini-title`), chapter name (`#mini-chapter`), and expand chevron. Tapping this entire hit area smoothly transitions to the Full Player (`#view-player`).
3. **Mini Transport Actions:**
   * Jump Backward 15s (`#mini-seek-back-btn`).
   * Circular Play/Pause button (`#mini-play-btn`).
   * Jump Forward 30s (`#mini-seek-fwd-btn`).

### Visibility & Interaction Rules:
* Automatically hidden when on the Full Player view (`#view-player:not(.hidden)`).
* Remains visible across Home, Library, Offline, History, and Profile views whenever a track is loaded.

---

## 8. Secondary Views: History, About, Profile

* **Listening History (`#view-history`):** Chronological timeline of listened books with last played timestamps and quick resume triggers.
* **About (`#view-about`):** Philosophy statement, version tag ("Listening-First Edition"), and links.
* **Profile & Storage Settings (`#view-profile`):** Listener avatar, listening metrics (Books Finished, Hours Listened, Active Stories), OPFS storage quota manager with "Clear Offline Audio" trigger, and Clerk auth controls.
