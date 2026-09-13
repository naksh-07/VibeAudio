# Stitch Screen Prompt 05 — Profile & Storage Settings (`#view-profile`)

**Prompt ID:** `STITCH-SCR-005`  
**Screen Target:** Profile & Settings View (`#view-profile` in `src/pages/app.html`)  
**Viewport:** Desktop 1440×900 & Mobile 390×844  
**Design Reference:** Apple ID Settings / macOS Account Preferences  

---

## 1. Screen Objective
Synthesize the profile, listening statistics, and storage management view of VibeAudio. Demonstrates guest status (or authenticated Clerk account), listening milestones, detailed OPFS quota usage, and cache controls in a clean, dignified light-mode card.

---

## 2. Existing Product Context & Invariants
* **View Container:** `#view-profile` in `app.html`.
* **User Profile Header:** `#profile-avatar` (64×64px circular avatar), `#user-name-display` ("Guest Listener" or username), `#profile-top-genre` badge.
* **Listening Stats:** `#profile-stat-finished`, `#profile-stat-hours`, `#profile-stat-active`, `#profile-stat-bookmarks`.
* **Device Storage Panel:** `#offline-storage-used`, `#offline-storage-quota`, `#offline-storage-books`, `#offline-storage-chapters`.
* **Action Buttons:** Clear downloads trigger (`#clear-offline-downloads-btn`), Sync progress (`#sync-profile-btn`), and Sign out / Exit (`window.app.logout()`).

---

## 3. Visual Direction & Layout

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [Top Navigation Bar: Home | Library | On This Device]             [ 🔍 Search ] [👤*] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│                                 ACCOUNT & STORAGE                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │  (👤)  Guest Listener                           [ Guest Shelf Active ]           │  │
│  │        Your listening progress and moments are preserved automatically.          │  │
│  │        Local device storage active on this browser.                              │  │
│  │                                                                                  │  │
│  │   LISTENING STATS                                                                │  │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────┐ │  │
│  │  │ 3                │ │ 24h              │ │ 2                │ │ 12           │ │  │
│  │  │ Books Finished   │ │ Hours Listened   │ │ Active Stories   │ │ Saved Moments│ │  │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────┘ │  │
│  │                                                                                  │  │
│  │   DEVICE STORAGE (OPFS)                                                          │  │
│  │   Private offline audio saved on this device.     [ 🗑 Clear Offline Audio ]     │  │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────┐ │  │
│  │  │ 1.2 GB           │ │ 48.6 GB          │ │ 4                │ │ 76           │ │  │
│  │  │ Saved Locally    │ │ Available Quota  │ │ Saved Books      │ │ Saved Chaps  │ │  │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────┘ │  │
│  │                                                                                  │  │
│  │  [ ☁ Sync Progress ]     [ ⎋ Sign Out / Reset Session ]                          │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  [ Floating Mini-Player Dock                                  [ -15s ] ( ▶ ) [ +30s ] ]│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

* **Card Surface:** Large white `#FFFFFF` card (`.profile-card`), `24px` sheet radius, `0 10px 28px rgba(0, 0, 0, 0.05)` shadow, centered at `800px` max-width.
* **Listener Header:**
  * 64px round avatar with warm amber background and bold initial.
  * Username in `Newsreader` (24px bold).
  * Status chip: `#F2F2F7` pill badge with green status dot.
* **Metrics Grids:**
  * Two 4-column statistical card rows with pure white background, subtle border, and large numeral figures.
* **Storage Actions:**
  * Destructive action button `[ 🗑 Clear Offline Audio ]` styled in subtle danger tokens (`rgba(255, 59, 48, 0.1)` background with `#D70015` red text).
  * Primary sync button in secondary pill style.

---

## 4. Components & Tokens
* `Profile Card`: `max-width: 800px`, centered, `var(--color-surface-1)` with `var(--radius-sheet)`.
* `Stat Box`: `var(--color-surface-2)`, `10px` radius, tabular numerals.
* `Subtle Danger Button`: 40px height, pill radius, `#D70015` text.

---

## 5. Things Stitch Must Avoid
* ❌ Avoid complicated charts, billing tables, or credit balance displays.
* ❌ Avoid dark background cards.
* ❌ Avoid full-screen edge-to-edge stretched layouts; keep settings centered and focused.
