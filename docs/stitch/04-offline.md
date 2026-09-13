# Stitch Screen Prompt 04 — On This Device / Offline Shelf (`#view-offline`)

**Prompt ID:** `STITCH-SCR-004`  
**Screen Target:** Offline Storage View (`#view-offline` in `src/pages/app.html`)  
**Viewport:** Desktop 1440×900 & Tablet 1024×768  
**Design Reference:** Apple macOS Storage Management / iOS Files App Utility  

---

## 1. Screen Objective
Synthesize the dedicated offline storage view of VibeAudio. This screen gives listeners total certainty and control over media stored locally on their device via OPFS (Origin Private File System). It highlights storage consumption, allows local file importing (`.m4b`, `.mp3`), and lists fully downloaded audiobooks.

---

## 2. Existing Product Context & Invariants
* **View Container:** `#view-offline` in `app.html`.
* **Action Trigger:** "Import Audio" file picker button (`#import-audiobook-input`).
* **Insights Panel:** `#offline-insights` (live storage metric cards: Used MB, Available Quota, Saved Books, Chapters).
* **Offline Grid:** `#offline-grid` (only audiobooks verified in local OPFS storage).

---

## 3. Visual Direction & Layout

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [Top Navigation Bar: Home | Library | On This Device*]             [ 🔍 Search ] [👤] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   SAVED FOR OFFLINE                                                                    │
│   On This Device                                                 [ 📥 Import Audio ]   │
│   Audiobooks saved locally and ready to play anywhere without internet.                │
│                                                                                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │ 1.2 GB           │  │ 48.6 GB          │  │ 4                │  │ 76              │ │
│  │ Audio Saved      │  │ Available Quota  │  │ Saved Books      │  │ Saved Chapters  │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  └─────────────────┘ │
│                                                                                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │ [Cover Art 2:3]  │  │ [Cover Art 2:3]  │  │ [Cover Art 2:3]  │  │ [Cover Art 2:3] │ │
│  │ [✓ Ready Offline]│  │ [✓ Ready Offline]│  │ [✓ Ready Offline]│  │ [✓ Ready Offline]│ │
│  │ Harry Potter     │  │ The Last Wish    │  │ The Hobbit       │  │ Rich Dad Poor   │ │
│  │ J.K. Rowling     │  │ Andrzej Sapkowski│  │ J.R.R. Tolkien   │  │ Robert Kiyosaki │ │
│  │ 8h 22m · 450 MB  │  │ 10h 15m · 510 MB │  │ 11h 05m · 240 MB │  │ 6h 12m · 120 MB │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  └─────────────────┘ │
│                                                                                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  [ Floating Mini-Player Dock                                  [ -15s ] ( ▶ ) [ +30s ] ]│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

* **Header Actions:** Title with a secondary button `[ 📥 Import Audio ]` (pill shape, `#F2F2F7` background with `#1D1D1F` text) allowing drag-and-drop or file selection.
* **Storage Metrics Grid (`.library-insights`):**
  * 4 compact, minimalist statistic cards.
  * Big numbers set in `Newsreader` or bold tabular mono (24px, `#1D1D1F`).
  * Sub-label in uppercase `#86868B` (11px, bold).
* **Audiobook Grid (`#offline-grid`):**
  * Same premium 2:3 squircle cards as the Library, but distinguished by an unmistakable green offline badge (`#248A3D` text on light green pill) in the cover's top-left corner.
  * Card meta includes audio duration and local file size footprint ("450 MB").

---

## 4. Components & Tokens
* `Storage Stat Card`: White `#FFFFFF` surface, `10px` radius, `1px solid rgba(0, 0, 0, 0.06)` border.
* `Import Button`: 44px min-height, pill radius, secondary surface token (`--color-surface-2`).
* `Offline Readiness Chip`: Green `#248A3D` with `#icon-check-circle` icon.

---

## 5. Things Stitch Must Avoid
* ❌ Avoid complicated partition graphs or technical disk utility diagrams.
* ❌ Avoid warning or red error states unless storage is genuinely full.
* ❌ Avoid dark surfaces; maintain the luminous `#F5F5F7` canvas.
