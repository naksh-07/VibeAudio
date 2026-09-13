# Stitch Screen Prompt 02 — Home Shelf (`#view-home`)

**Prompt ID:** `STITCH-SCR-002`  
**Screen Target:** Application Home View (`#view-home` in `src/pages/app.html`)  
**Viewport:** Desktop 1440×900 & Tablet 1024×768  
**Design Reference:** Apple Books "Reading Now" Tab / macOS Media Dashboard  

---

## 1. Screen Objective
Synthesize the primary home view of VibeAudio. The core design job of this screen is **single-tap listening continuity**. Returning listeners must immediately see their in-progress story, their locally downloaded offline audiobooks, and a restrained selection of curated recommendations.

---

## 2. Existing Product Context & Invariants
* **View Container:** `#view-home` inside the 1200px `.glass-container`.
* **Continue Listening Hero:** `#home-resume-hero` (dynamic banner with book cover, chapter, progress bar, and "Resume" action).
* **On This Device Shelf:** `#home-offline-shelf` with horizontal scrollable track `#home-offline-grid`.
* **Curated Discovery Row:** `#home-curated-shelf` with discovery grid `#home-curated-grid`.
* **Mini-Player Dock:** Floats at the bottom whenever an active track is playing.

---

## 3. Visual Direction & Layout

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [Top Navigation Bar: Home* | Library | On This Device]             [ 🔍 Search ] [👤] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   CONTINUE LISTENING                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ ┌──────────────┐   ACTIVE STORY  ·  [✓ Synced]                                   │  │
│  │ │              │                                                                 │  │
│  │ │  Cover Art   │   Harry Potter & The Half-Blood Prince                          │  │
│  │ │   (2:3)      │   J.K. Rowling                                                  │  │
│  │ │              │   [ Chapter 14: Felix Felicis ]   ·   54% completed             │  │
│  │ │ [✓ Offline]  │   ═════════════════════════════════ 54% ════════════════════    │  │
│  │ └──────────────┘   [ ▶ Resume Listening ]   [ Chapter List ]                     │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                        │
│   SAVED LOCALLY                                                        [ View All → ]  │
│   On This Device                                                                       │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐             │
│  │ [Cover]      │   │ [Cover]      │   │ [Cover]      │   │ [Cover]      │             │
│  │ Title        │   │ Title        │   │ Title        │   │ Title        │             │
│  │ [✓ In OPFS]  │   │ [✓ In OPFS]  │   │ [✓ In OPFS]  │   │ [✓ In OPFS]  │             │
│  └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘             │
│                                                                                        │
│   CURATED DISCOVERY                                                    [ Full Shelf → ]│
│   Picked for You                                                                       │
│  [ Book Card ]       [ Book Card ]       [ Book Card ]       [ Book Card ]             │
│                                                                                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  [ Floating Mini-Player Dock: HP & Half-Blood Prince — Ch 14    [ -15s ] ( ▶ ) [ +30s ]│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

* **Hero Banner (`.resume-hero-card`):**
  * Solid white `#FFFFFF` surface with `18px` panel radius, `1px solid rgba(0, 0, 0, 0.1)` border, and `0 6px 20px rgba(0, 0, 0, 0.05)` shadow.
  * 140px wide 2:3 vertical book cover with squircle radius and green offline badge.
  * Headline in `Newsreader` (28px bold), author byline, chapter pill tag (`#F2F2F7` background), and 5px high orange accent progress track.
  * Primary "Resume Listening" button in solid warm amber (`#E65A00`) with high-contrast white text.
* **On This Device Shelf (`.home-shelf-section`):**
  * Section title with green `#248A3D` checkmark icon.
  * Horizontal scrolling track with momentum scroll (`-webkit-overflow-scrolling: touch`) and thin scrollbar thumb.
  * Mini cards with prominent downloaded badges.
* **Picked for You Shelf:**
  * Clean 4-column catalog grid with generous spacing (24px gap).

---

## 4. Components & Tokens
* `Background Canvas`: `#F5F5F7`
* `Resume Button`: Pill shape, `#E65A00` solid, white text, 44px touch height.
* `Offline Pill`: `#248A3D` text on `rgba(52, 199, 89, 0.12)` chip.
* `Mini-Player Dock`: Floating frosted glass bar docked 16px above viewport bottom.

---

## 5. Things Stitch Must Avoid
* ❌ Avoid turning the whole screen into a massive carousel or Netflix-style infinite wall of posters.
* ❌ Avoid obscuring the resume hero with promotional banners.
* ❌ Avoid dark card backgrounds.
* ❌ Avoid generic placeholder icons instead of VibeAudio's custom stroke symbols.
