# Stitch Screen Prompt 06 — Floating Mini-Player Dock (`#mini-player`)

**Prompt ID:** `STITCH-SCR-006`  
**Screen Target:** Floating Mini-Player Dock (`#mini-player` in `src/pages/app.html`)  
**Viewport:** Desktop 1440×900, Tablet 1024×768, Mobile 390×844  
**Design Reference:** Apple Music Floating Player Dock / macOS Sequoia Dynamic Media Pill  

---

## 1. Screen Objective
Synthesize the floating, persistent mini-player dock of VibeAudio. This component hovers seamlessly over bottom content across Home, Library, Offline, and Profile views, giving the listener instant control over playback and progress without interrupting exploration.

---

## 2. Existing Product Context & Invariants
* **Container:** `#mini-player` (`.player-bar.mini-dock`).
* **Progress Track:** `.mini-progress-line` (2px height) with `#mini-progress-line-fill` (dynamic width %).
* **Track Info Zone:** `#mini-track-info` with `#mini-cover` (42×42px), `#mini-title`, `#mini-chapter`, and `#icon-chevron-up`.
* **Transport Controls:** `#mini-seek-back-btn` (jump -15s), `#mini-play-btn` (play/pause toggle), `#mini-seek-fwd-btn` (jump +30s).
* **Contract:** Must hide immediately when `#view-player` is active.

---

## 3. Visual Direction & Anatomy

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ══════════════════════════════════════ 64% ═══════════════════════════════════════════ │ ◄── 2px accent track
│ ┌──────┐                                                                               │
│ │Cover │  Harry Potter & The Half-Blood Prince         [ -15s ]   ( ▶ )   [ +30s ]     │
│ │ 42px │  Chapter 14: Felix Felicis  ▲                                                 │
│ └──────┘                                                                               │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

* **Dock Dimensions & Materiality:**
  * Width: `min(1200px, calc(100% - 32px))` centered with `left: 50%; transform: translateX(-50%);`.
  * Height: `62px`.
  * Positioning: `position: fixed; bottom: max(16px, env(safe-area-inset-bottom, 16px)); z-index: 1000;`.
  * Surface Material: `rgba(255, 255, 255, 0.82)` with `backdrop-filter: blur(24px) saturate(190%)`.
  * Border: `1px solid rgba(0, 0, 0, 0.12)` (crisp hairline definition).
  * Border Radius: `var(--radius-sheet)` (24px pill shape).
  * Elevation: `0 16px 44px rgba(0, 0, 0, 0.10), 0 4px 12px rgba(0, 0, 0, 0.04)`.
* **Top Progress Line:**
  * 2px hairline along the top border. Track in `rgba(0, 0, 0, 0.06)`, active fill in solid `#E65A00`.
* **Track Info Trigger (`#mini-track-info`):**
  * 42×42px square book thumbnail with `6px` radius and subtle drop shadow.
  * Title in `Newsreader` (14.5px, bold, `#1D1D1F`, single line clamp).
  * Chapter in `Inter` (11.5px, `#6E6E73`, single line clamp).
  * Small upward chevron (`#icon-chevron-up`) indicating click-to-expand.
* **Mini Transport Deck:**
  * Jump Backward 15s (`#mini-seek-back-btn`): 36px circular ghost button, `#6E6E73` icon.
  * Main Play/Pause Circle (`#mini-play-btn`): 42px circular button in solid warm amber (`#E65A00`), crisp `#FFFFFF` play/pause symbol, subtle warm glow shadow.
  * Jump Forward 30s (`#mini-seek-fwd-btn`): 36px circular ghost button, `#6E6E73` icon.

---

## 4. Mobile Ergonomics (390×844)
* Dock expands to `calc(100% - 24px)`.
* Height remains 60px for easy thumb tapping.
* Safe-area bottom padding respected (`env(safe-area-inset-bottom)`).
* Track info text truncates cleanly with ellipsis to leave ample room for the 3 transport buttons.

---

## 5. Things Stitch Must Avoid
* ❌ Avoid opaque dark dock backgrounds (`#0C0D11` or `#16181F`).
* ❌ Avoid adding volume sliders or scrubber thumbs inside the mini dock; space must remain clean.
* ❌ Avoid square rectangular corners; dock must feature smooth pill curvature.
