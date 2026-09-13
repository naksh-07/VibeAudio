# Stitch Screen Prompt 03 — Audiobook Library (`#view-library`)

**Prompt ID:** `STITCH-SCR-003`  
**Screen Target:** Application Library View (`#view-library` in `src/pages/app.html`)  
**Viewport:** Desktop 1440×900 & Mobile 390×844  
**Design Reference:** Apple Books Library / iPadOS Books Catalog  

---

## 1. Screen Objective
Synthesize the complete catalog discovery view for VibeAudio. Listeners explore unabridged audiobooks, filter by genre or mood tags, search titles and authors, and inspect story cards with clear offline and progress indicators.

---

## 2. Existing Product Context & Invariants
* **View Container:** `#view-library` in `app.html`.
* **Category Filters:** `#category-filters` (horizontal pill toolbar: All, Fiction, Fantasy, Self-Help, etc.).
* **Search Integration:** Search query triggers real-time filtering in `#book-grid`; recent searches appear in `#recent-searches-panel`.
* **Sync Status:** `#library-sync-banner` with `aria-live="polite"`.
* **Catalog Grid:** `#book-grid` rendering `.book-card` elements.

---

## 3. Visual Direction & Layout

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [Top Navigation Bar: Home | Library* | On This Device]             [ 🔍 Potter ] [👤] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   DISCOVER STORIES                                                                     │
│   Audiobook Library                                                                    │
│   Find and explore unabridged audiobooks ready for your browser.                       │
│                                                                                        │
│   [ All* ]  [ Fiction ]  [ Fantasy ]  [ Philosophy ]  [ Adventure ]  [ Mystery ]       │
│                                                                                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │ [Cover Art 2:3]  │  │ [Cover Art 2:3]  │  │ [Cover Art 2:3]  │  │ [Cover Art 2:3] │ │
│  │ [✓ In OPFS]      │  │                  │  │                  │  │ [✓ In OPFS]     │ │
│  │ FANTASY          │  │ CLASSIC          │  │ SELF HELP        │  │ ADVENTURE       │ │
│  │ Philosopher's    │  │ The Hobbit       │  │ Rich Dad Poor Dad│  │ The Last Wish   │ │
│  │ Stone            │  │ J.R.R. Tolkien   │  │ Robert Kiyosaki  │  │ Andrzej Sapkowski│
│  │ J.K. Rowling     │  │                  │  │                  │  │                 │ │
│  │ ═════════ 100%   │  │ ═════ 24%        │  │                  │  │ ════════ 65%    │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  └─────────────────┘ │
│                                                                                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │ [Book Card]      │  │ [Book Card]      │  │ [Book Card]      │  │ [Book Card]     │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  └─────────────────┘ │
│                                                                                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  [ Floating Mini-Player Dock                                  [ -15s ] ( ▶ ) [ +30s ] ]│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

* **Header Hierarchy:**
  * Eyebrow: `DISCOVER STORIES` (11px, 700 uppercase, letter-spacing `0.12em`, `#C64E00`).
  * Headline: `Audiobook Library` (28px `Newsreader` bold, `#1D1D1F`).
  * Subtitle: 15px `Inter` (`#6E6E73`).
* **Category Filter Toolbar:**
  * Segmented pill bar with horizontal scroll.
  * Active pill: `#C64E00` solid background with pure `#FFFFFF` bold text and subtle shadow.
  * Inactive pills: White `#FFFFFF` background, `1px solid rgba(0, 0, 0, 0.08)` border, `#6E6E73` text.
* **Audiobook Card (`.book-card`):**
  * Solid white `#FFFFFF` surface with `14px` squircle radius and `0 4px 18px rgba(0, 0, 0, 0.05)` shadow.
  * Cover media in authentic 2:3 aspect ratio with no dark scrim overlays.
  * Literary title in `Newsreader` (18px, 2-line clamp).
  * Author byline in `#6E6E73`.
  * Progress track (if started): 4px accent line (`#C64E00`) with percentage label.
  * Offline badge (if in OPFS): Green checkmark chip at bottom-left corner of the cover.

---

## 4. Zero Search Results Empty State Specification

When a listener searches or filters with no matches:
* **Trigger Condition:** Query in `#search-input` yields zero matches in catalog.
* **Visual Hierarchy & Layout:**
  * Centered card container occupying the full width of the `#book-grid` zone (`max-width: 580px`, margin: `64px auto`).
  * Surface: Solid white `#FFFFFF`, `20px` radius, `1px solid rgba(0, 0, 0, 0.08)` hairline border, soft ambient shadow.
  * Padding: `48px 32px`.
* **Icon Treatment:**
  * 52×52px circular badge in `var(--color-surface-2)` (`#F2F2F7`).
  * Centered search-slash icon (`#icon-search` with gentle diagonal slash) in `1.85px` stroke (`#86868B`).
* **Concise Copy:**
  * Headline: *"No stories found"* in `Newsreader` (24px bold, `#1D1D1F`).
  * Subtitle: *"We couldn't find any audiobooks matching your current query or filter. Try searching for a different author, title, or reset your filters."* in `Inter` (14.5px, `#6E6E73`, line-height 1.5).
* **Primary Action:**
  * Secondary pill button: *"Clear Search & Filters"* (`#F2F2F7` background, `#1D1D1F` text, `1px solid rgba(0, 0, 0, 0.08)` border, min-height 42px, padding `10px 20px`). Triggers `#search-clear-btn` and resets category pills to "All".
* **Relationship to Navigation:**
  * Category pill bar remains visible above the empty state so users can quickly switch genres.
* **What Should NOT Be Shown:**
  * ❌ No broken image placeholders or error exclamation marks.
  * ❌ No web-wide external search suggestions.

---

## 5. Components & Tokens
* `Grid System`: CSS Grid `repeat(auto-fill, minmax(220px, 1fr))` on desktop (4 columns), 2 columns on mobile.
* `Card Hover`: Subtle lift (`transform: translateY(-3px)`) and image scale (`1.03`).
* `Filter Pill`: 38px height, 999px pill radius.

---

## 6. Things Stitch Must Avoid
* ❌ Avoid dense, crowded text lists; VibeAudio is visually anchored by cover artwork.
* ❌ Avoid ugly, visible horizontal scrollbars on the filter pills.
* ❌ Avoid dark card backgrounds.
* ❌ Avoid arbitrary card sizes or stretched covers that violate the 2:3 ratio.
