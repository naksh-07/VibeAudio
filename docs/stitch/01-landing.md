# Stitch Screen Prompt 01 — Landing Page (`index.html`)

**Prompt ID:** `STITCH-SCR-001`  
**Screen Target:** VibeAudio Landing Page (`index.html`)  
**Viewport:** Desktop 1440×900 & Mobile 390×844  
**Design Reference:** Apple Books Marketing Pages / macOS Sequoia Product Overview  

---

## 1. Screen Objective
Synthesize a clean, editorial, light-minimalist landing page that introduces VibeAudio as an unabridged, offline-first personal audiobook sanctuary. It must inspire calm, reassure users with guest-first trust signals, and direct them straight into the listening experience without mandatory sign-up barriers.

---

## 2. Existing Product Context & Invariants
* **Brand Assets:** Uses custom locked brand mark vector (warm amber keystone glyph), subtitle *"Personal listening sanctuary"*.
* **Reassurance Signals:** "Guest & Offline Ready", "Works as a guest", "Saved on this device", "Cloud sync optional".
* **Key Call to Action:** "Start listening" solid action button linking to `./src/pages/app.html#home`.
* **Featured Spotlight:** Showcases a featured audiobook cover with story details and listening metrics.

---

## 3. Visual Direction & Hierarchy

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [Logo] VibeAudio              [✓ Guest & Offline Ready]  [Browse]  [ Start listening ] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   🎧 Personal Audiobook Sanctuary                 ┌────────────────────────────────┐   │
│   A calmer way to                                 │ ✨ Featured Story              │   │
│   listen.                                         │                                │   │
│                                                   │      [Cover Art 2:3]           │   │
│   Step into your personal listening shelf.        │                                │   │
│   Enjoy unabridged audiobooks directly in your    │   Harry Potter & Philosopher's │   │
│   browser, save stories to your device for        │   Stone                        │   │
│   offline playback, and pick up right where...    │   J.K. Rowling · 8h 22m        │   │
│                                                   │   [ ▶ Listen Now ]             │   │
│   [ ▶ Start listening ]  [ 📖 Browse library ]   └────────────────────────────────┘   │
│                                                                                        │
│   ✓ Works as a guest  ·  💾 Saved on device  ·  ☁ Cloud sync optional                  │
│                                                                                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ CURATED PREVIEW                                                                        │
│ Browse the shelf or listen right away                                [ Open library → ]│
│ [ Book Card ]     [ Book Card ]     [ Book Card ]     [ Book Card ]                    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

* **Canvas:** `#F5F5F7` background with very subtle ambient warm light glow in top left.
* **Hero Section (2-Column Grid):**
  * *Left Hero Card:* White `#FFFFFF` panel with 24px sheet radius. Eyebrow tag in uppercase warm amber (`#E65A00`). Display title *"A calmer way to listen."* set in `Newsreader` (italic accent on *"listen"*). Primary solid amber button with high-contrast white text, secondary ghost button.
  * *Right Spotlight Card:* Elevated white card featuring a large 2:3 vertical book cover with soft ambient drop shadow, title in Newsreader, author, and quick play CTA.
* **Curated Preview Grid:** 4-column card grid showing authentic book covers with 2:3 aspect ratio, subtle hairline borders, and category tags.
* **Feature Row:** 4 minimalist feature tiles (Listening Sanctuary, Private Offline Shelf, Saved Moments, Optional Cloud Sync) with thin stroke line icons.

---

## 4. Components & Tokens
* `Landing Topbar`: Sticky frosted glass (`background: rgba(255, 255, 255, 0.78); backdrop-filter: blur(20px); border-radius: 24px;`).
* `Primary Button`: `#E65A00` background, `#FFFFFF` bold text, pill radius, subtle warm shadow.
* `Trust Badges`: Pill chips with `#248A3D` checkmark icon and `#F2F2F7` background.
* `Book Cards`: Pure white `#FFFFFF` surface with hairline `rgba(0, 0, 0, 0.08)` border and `0 4px 18px rgba(0, 0, 0, 0.05)` shadow.

---

## 5. Visual Constraints & Avoid Rules
* ❌ Avoid dark background colors (`#0C0D11` or `#16181F`).
* ❌ Avoid pricing banners, fake discount percentages, or "Subscribe now" buttons.
* ❌ Avoid loud multi-color gradients. Keep colors grounded in `#F5F5F7`, `#FFFFFF`, and `#E65A00`.
* ❌ Avoid heavy drop shadows that appear dirty on light backgrounds.
