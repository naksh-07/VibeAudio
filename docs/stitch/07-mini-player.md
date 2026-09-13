# Stitch Screen Prompt 07 — Persistent Mini-Player Dock in Application Shell Context (`#mini-player`)

**Prompt ID:** `STITCH-SCR-007`  
**Screen Target:** Floating Mini-Player Dock embedded in Application Shell (`#mini-player` in `src/pages/app.html`)  
**Viewport:** Desktop 1440×900 & Mobile 390×844  
**Design Reference:** Apple Music Floating Player Dock / macOS Sequoia Dynamic Media Pill in Living View  

---

## 1. Screen Objective
Synthesize the persistent, floating mini-player dock of VibeAudio **in realistic application shell context**.

> [!IMPORTANT]
> **Contextual Mandate for Stitch:**  
> The Mini Player must **NOT** be presented as an isolated floating component on a blank or empty canvas.  
> It must be shown as the persistent listening control bar hovering above living application content (e.g. the Audiobook Library or Home view shelf), demonstrating the full structural relationship:
> ```text
> Application Content (Library / Home Shelves)
>         ↓
> Persistent Frosted Mini-Player Dock
>         ↓
> Viewport Edge & Safe-Area Relationship
> ```

---

## 2. Existing Product Context & Invariants
* **Shell Architecture:** Mounted within `frontend/src/pages/app.html`.
* **Clearance Contract:** The scrollable content container enforces `padding-bottom: 120px`, ensuring catalog cards glide smoothly beneath the dock without obstruction.
* **Dock Container:** `#mini-player` (`.player-bar.mini-dock`).
* **Micro Progress Line:** `.mini-progress-line` (2px height) with `#mini-progress-line-fill` (dynamic width % in `#C64E00`).
* **Track Info Trigger:** `#mini-track-info` with `#mini-cover` (42×42px square cover), `#mini-title` in `Newsreader`, `#mini-chapter` in `Inter`, and upward chevron indicator. Tapping this entire hit area opens the Full Player (`#view-player`).
* **Micro Transport Controls:** `#mini-seek-back-btn` (jump -15s), `#mini-play-btn` (42px circular play/pause toggle in `#C64E00`), `#mini-seek-fwd-btn` (jump +30s).
* **Visibility Contract:** Hides immediately when `#view-player` is active.

---

## 3. Visual Direction & Hierarchy (Living Application Context)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [Top Navigation Bar: Home | Library* | On This Device]             [ 🔍 Search ] [👤] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   AUDIOBOOK LIBRARY (Scrollable Background Content Area)                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │ [Cover Art 2:3]  │  │ [Cover Art 2:3]  │  │ [Cover Art 2:3]  │  │ [Cover Art 2:3] │ │
│  │ Philosopher's    │  │ The Hobbit       │  │ Rich Dad Poor Dad│  │ The Last Wish   │ │
│  │ Stone            │  │ J.R.R. Tolkien   │  │ Robert Kiyosaki  │  │ Andrzej Sapkow..│
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  └─────────────────┘ │
│                                                                                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │ [Cover Art 2:3]  │  │ [Cover Art 2:3]  │  │ [Cover Art 2:3]  │  │ [Cover Art 2:3] │ │
│  │ DUNE             │  │ 1984             │  │ Sapiens          │  │ Atomic Habits   │ │
│  │ Frank Herbert    │  │ George Orwell    │  │ Yuval Noah Harari│  │ James Clear     │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  └─────────────────┘ │
│                                                                                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  ══════════════════════════════════════ 64% ═════════════════════════════════════════  │ ◄── 2px accent track
│  ┌──────┐                                                                              │
│  │Cover │  Harry Potter & The Half-Blood Prince         [ -15s ]   ( ▶ )   [ +30s ]    │ ◄── 62px Floating Dock
│  │ 42px │  Chapter 14: Felix Felicis  ▲                                                │
│  └──────┘                                                                              │
└────────────────────────────────────────────────────────────────────────────────────────┘ ◄── Viewport Bottom
```

* **Dock Dimensions & Materiality:**
  * Width: `min(1200px, calc(100% - 32px))` centered with `left: 50%; transform: translateX(-50%);`.
  * Height: `62px`.
  * Positioning: `position: fixed; bottom: max(16px, env(safe-area-inset-bottom, 16px)); z-index: 1000;`.
  * Surface Material: `rgba(255, 255, 255, 0.82)` with `backdrop-filter: blur(24px) saturate(190%)` and `-webkit-backdrop-filter: blur(24px) saturate(190%)`.
  * Hardware Edge: `1px solid rgba(0, 0, 0, 0.12)` (crisp hairline definition) and `isolation: isolate`.
  * Border Radius: `var(--radius-sheet)` (24px squircle pill shape).
  * Elevation: `0 16px 44px rgba(0, 0, 0, 0.10), 0 4px 12px rgba(0, 0, 0, 0.04)`.
* **Top Micro-Progress Line:**
  * 2px hairline along the top border. Track in `rgba(0, 0, 0, 0.06)`, active fill in solid `#C64E00`.
* **Track Info Trigger (`#mini-track-info`):**
  * 42×42px square book thumbnail with `6px` radius and subtle drop shadow.
  * Title in `Newsreader` (14.5px, bold, `#1D1D1F`, single line clamp).
  * Chapter in `Inter` (11.5px, `#6E6E73`, single line clamp).
  * Small upward chevron (`#icon-chevron-up`) indicating tap-to-expand.
* **Mini Transport Deck:**
  * Jump Backward 15s (`#mini-seek-back-btn`): 36px circular ghost button, `#6E6E73` icon.
  * Main Play/Pause Circle (`#mini-play-btn`): 42px circular button in solid warm amber (`#C64E00`), crisp `#FFFFFF` play/pause glyph (verified 4.67:1 WCAG AA contrast), subtle warm glow shadow `0 4px 14px rgba(198, 78, 0, 0.24)`.
  * Jump Forward 30s (`#mini-seek-fwd-btn`): 36px circular ghost button, `#6E6E73` icon.

---

## 4. Mobile Ergonomics (390×844)
* Dock expands to `calc(100% - 24px)`.
* Height remains 60px for easy single-thumb reach.
* Safe-area bottom padding respected (`env(safe-area-inset-bottom, 12px)`), sitting cleanly above the iOS Home Indicator.
* Track info text truncates cleanly with ellipsis to leave ample room for the 3 transport buttons.

---

## 5. Things Stitch Must Avoid
* ❌ **Do NOT render as an isolated widget on a blank canvas:** Must always display surrounding shelf content.
* ❌ Avoid opaque dark dock backgrounds (`#0C0D11` or `#16181F`).
* ❌ Avoid adding volume sliders or scrubber thumbs inside the mini dock; space must remain clean.
* ❌ Avoid square rectangular corners; dock must feature smooth 24px squircle pill curvature.
