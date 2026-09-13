# Stitch Screen Prompt 07 — Full Player & Book Detail (`#view-player`)

**Prompt ID:** `STITCH-SCR-007`  
**Screen Target:** Full Audiobook Player (`#view-player` in `src/pages/app.html`)  
**Viewport:** Desktop 1440×900 & Tablet 1024×768  
**Design Reference:** Apple Podcasts / Books Full Player View in macOS & iPadOS  

---

## 1. Screen Objective
Synthesize the primary immersion view of VibeAudio. When a listener expands the player or starts an audiobook, this screen presents the book cover artwork with a luminous ambient bloom, literary typography, a high-precision hardware transport deck, chapter playlists, and timestamp-locked notes.

---

## 2. Existing Product Context & Invariants
* **View Container:** `#view-player` in `app.html`.
* **Top Actions:** Glass back button (`#back-btn`), Offline status chip (`#player-offline-status-chip`).
* **Header & Artwork Stage:** `.player-header-card`, ambient light bloom (`#blur-bg`), cover artwork (`#detail-cover`), book title (`#detail-title`), author (`#detail-author`), summary (`#detail-summary`), primary CTAs (`#main-play-btn`, `#download-book-btn`, `#share-book-btn`).
* **Transport Deck:** `.player-transport-deck`, position line (`#player-current-part`, `#player-time-remaining`), range scrubber (`#progress-bar`, `#current-time`, `#total-duration`), controls (`#speed-btn`, `#seek-back-btn`, `#play-btn`, `#seek-fwd-btn`, `#sleep-timer-btn`).
* **Two-Column Deck:** Left chapter playlist (`#chapter-list`), right side stack with saved moments (`#bookmark-list`) and timestamped notes (`#comments-list`).

---

## 3. Visual Direction & Layout

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [ ← Back to Shelf ]                                           [✓ Ready Offline Chip]   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ ┌─────────────────┐   AUDIOBOOK  ·  FANTASY                                      │  │
│  │ │                 │                                                              │  │
│  │ │  Cover Artwork  │   Harry Potter & The Half-Blood Prince                       │  │
│  │ │     (2:3)       │   J.K. Rowling                                               │  │
│  │ │                 │   The sixth year at Hogwarts brings new mysteries, memory    │  │
│  │ │                 │   trials, and the dark secret of Lord Voldemort's horcruxes. │  │
│  │ └─────────────────┘   [ ▶ Listen Now ]   [ 💾 Save Offline ]   [ ⤤ Share ]       │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │   Part 14: Felix Felicis                                34m 12s remaining        │  │
│  │                                                                                  │  │
│  │   14:28  ═══════════════════════════●═══════════════════════════════  48:40       │  │
│  │                                                                                  │  │
│  │           [ 1.25x ]      [ ↺ 15s ]      ( ▶ 56px )      [ ↻ 30s ]      [ 💤 ]    │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                        │
│  ┌─────────────────────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │ CHAPTERS (24 Parts)                     │  │ SAVED MOMENTS       [ + Save Moment]│  │
│  │ ┌─────────────────────────────────────┐ │  │ • 12:45 — Slughorn's Memory         │  │
│  │ │ 13. The Secret Riddle       22:15   │ │  │ • 34:10 — The Felix Felicis Toast   │  │
│  │ ├─────────────────────────────────────┤ │  ├─────────────────────────────────────┤  │
│  │ │ ▶ 14. Felix Felicis (Playing)48:40  │ │  │ NOTES & TIMESTAMPS                  │  │
│  │ ├─────────────────────────────────────┤ │  │ [ Write a note for this moment... ] │  │
│  │ │ 15. The Unbreakable Vow     36:10   │ │  │ • "Key line about Horace at 18:20"  │  │
│  │ └─────────────────────────────────────┘ │  └─────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

* **Header Card Presentation (`.player-header-card`):**
  * Solid white `#FFFFFF` surface with `24px` sheet radius and `0 10px 28px rgba(0, 0, 0, 0.05)` shadow.
  * Ambient Bloom Layer (`#blur-bg`): High-key pastel glow extracted from the cover art, soft blur (80px), opacity 0.12, no dark vignettes.
  * 180px wide cover with authentic 2:3 ratio and `14px` squircle corners.
  * Title in `Newsreader` (36px bold, `#1D1D1F`), author in `#6E6E73`.
  * CTA Row: Primary solid button `#E65A00` with white text, secondary outline buttons.
* **Transport Deck (`.player-transport-deck`):**
  * White `#FFFFFF` panel with `18px` radius and `1px solid rgba(0, 0, 0, 0.08)` border.
  * Timecodes in tabular monospace (`JetBrains Mono`, 12.5px, `#86868B`).
  * Scrubber Track: 6px height, `rgba(0, 0, 0, 0.06)` track, solid `#E65A00` fill, 18px pure white circular thumb with subtle drop shadow (`0 2px 8px rgba(0, 0, 0, 0.2)`).
  * Main Play Button (`#play-btn`): 56×56px round button in `#E65A00` with `#FFFFFF` play/pause glyph and warm ambient glow.
  * Step buttons (Back 15s, Forward 30s): Pill shape, `#F2F2F7` background with `#1D1D1F` text.
  * Secondary icons (Speed, Sleep timer): 40px circular ghost buttons.
* **Chapter Playlist & Moments (Two-Column):**
  * Left: Chapter items in `#F2F2F7` background; active playing chapter highlighted in soft amber `rgba(230, 90, 0, 0.08)` with 3px left amber border.
  * Right: Saved moments and inline timestamped note composer with rounded text input.

---

## 4. Things Stitch Must Avoid
* ❌ Avoid dark overlays that make the header card look like dark mode.
* ❌ Avoid thin, hard-to-tap scrubber lines; track must be 6px and thumb must be 18px.
* ❌ Avoid changing the canonical jump increments (-15s backward, +30s forward).
* ❌ Avoid complex visual equalizers that distract from listening.
