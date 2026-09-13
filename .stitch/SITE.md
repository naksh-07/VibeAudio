# VibeAudio — Product & Site Context (`SITE.md`)

**Document ID:** `STITCH-SITE-001`  
**Standard:** Google Stitch Project Constitution & Site Context (`SITE.md`)  
**Product Title:** VibeAudio — Personal Audiobook Sanctuary  
**Stitch Project ID:** `6063499620727826815`  
**Canonical Design System Asset ID:** `3782265180cc4ca5b6153874396ac6c9`  
**Status:** Canonical Product Architecture & Generation Guide  

---

## 1. Product Overview & Identity

**VibeAudio** is an unabridged, offline-first personal audiobook sanctuary built for the modern web and Progressive Web App (PWA).

It stands in direct contrast to commercial audiobook storefronts and algorithmic engagement feeds. VibeAudio is not a store, not an ad-supported player, and not a gamified social app. It is a tranquil, distraction-free private shelf where listeners immerse themselves in long-form spoken literature.

### Core Product Philosophy:
1. **Listening-First:** Zero promotional popups, zero marketing banners, zero review counts, zero store upsells. Every interaction leads to playback.
2. **Offline-First:** Unabridged audio and artwork are stored directly on the listener's local device in the sandboxed Origin Private File System (OPFS). Fully functional on planes, subways, and off-grid.
3. **Guest-First (Zero Mandatory Onboarding):** Anyone can open the app, browse the complete catalog, stream audio, save books offline, and keep local listening progress with no account required. Optional cloud backup via Clerk exists strictly for users who want multi-device sync.
4. **Low Cognitive Load:** Calm, generous whitespace, disciplined contrast, and tactile physical controls inspired by classic hardware audio players.
5. **Editorial & Literary Character:** Grounded in transitional serif typography (`Newsreader`) and authentic 2:3 vertical book proportions, honoring the heritage of printed literature.

---

## 2. Core User Journey

```text
    ┌────────────────────────┐
    │  Open VibeAudio App    │ (Guest or Returning)
    └───────────┬────────────┘
                │
                ▼
    ┌────────────────────────┐
    │  Home / Library Shelf  │ ──► Instant continuity via "Resume Listening" Hero
    └───────────┬────────────┘     or category search & filter
                │
                ▼
    ┌────────────────────────┐
    │    Select Audiobook    │ ──► Inspect synopsis, chapters & local download status
    └───────────┬────────────┘
                │
                ▼
    ┌────────────────────────┐
    │ Play & Immerse (Full)  │ ──► Full-screen Sanctuary with tactile transport deck,
    └───────────┬────────────┘     ambient cover bloom, and chapter navigation
                │
                ▼
    ┌────────────────────────┐
    │ Save Moments & Notes   │ ──► Bookmark timestamped lines and reflections
    └───────────┬────────────┘
                │
                ▼
    ┌────────────────────────┐
    │ Minimize & Browse      │ ──► Full Player folds into persistent 62px Mini-Dock
    └───────────┬────────────┘     hovering above shelf navigation
                │
                ▼
    ┌────────────────────────┐
    │  Resume Later Anytime  │ ──► Progress stored on-device; 1-click resume
    └────────────────────────┘
```

---

## 3. Canonical Sitemap & Screen Inventory

The canonical screen taxonomy defines the 8 essential screens for Stitch canvas synthesis:

| Screen ID | Canonical Name | Target Element / Route | Primary Role |
|---|---|---|---|
| **01** | **Landing Page** | `frontend/index.html` | Welcoming public introduction, trust signals ("Guest & Offline Ready"), curated catalog preview, and "Start listening" direct CTA. |
| **02** | **Home** | `#view-home` | Personal home base: prominent "Resume Listening" hero card, "On This Device" offline shelf, curated recommendations, and fresh user empty state. |
| **03** | **Library** | `#view-library` | Comprehensive catalog discovery: category pill toolbar, real-time search, responsive 4-column book card grid, and zero-results state. |
| **04** | **Offline** | `#view-offline` | Dedicated on-device storage sanctuary: OPFS storage metrics (Used/Quota), local audio importer, downloaded shelf, and zero-downloads state. |
| **05** | **Full Player** | `#view-player` | Immersive playback sanctuary: 2:3 cover art with ambient bloom, literary title, hardware transport deck (scrubber, speed, -15s/+30s), chapters & notes. |
| **06** | **Profile** | `#view-profile` | Listener identity & device control: Guest status / Clerk auth, listening milestones, OPFS storage quota manager, and destructive cache reset. |
| **07** | **Mini Player** | `#mini-player` (in App Shell) | Persistent 62px frosted glass dock: micro-progress line, 42px cover art thumbnail, title/chapter, and 3 transport controls floating above navigation. |
| **08** | **Mobile Adaptations** | Mobile Viewport (390×844) | Mobile-specific ergonomics using Home view as baseline: compact frosted topbar, thumb-friendly 44px tap targets, 2-column grid, and safe-area dock. |

---

## 4. Application Shell Breakdown

The VibeAudio application shell (`frontend/src/pages/app.html`) consists of four primary structural layers:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. FLOATING APP TOPBAR (Fixed Top, Frosted Glass, 62px Height, 24px Radius)            │
│    [Logo + Lockup]      [ Home ]   [ Library ]   [ On This Device ]    [Search] [User] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│ 2. MAIN SCROLLABLE CONTENT AREA (Max 1200px Centered Container, Padding-Bottom 120px)  │
│    Active View: #view-home | #view-library | #view-offline | #view-profile             │
│                                                                                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. PERSISTENT FLOATING MINI-PLAYER DOCK (Fixed Bottom, 62px, Frosted Glass, 24px Rad)  │
│    [Cover 42px] [Title - Chapter]                              [ -15s ] ( ▶ ) [ +30s ] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. FULL-SCREEN SANCTUARY OVERLAY (#view-player — Replaces Shell when Active)           │
│    [← Back]                                                            [✓ Offline Chip]│
│    [Cover + Title + Author]                                                            │
│    [Transport Deck: Speed, -15s, 56px Play, +30s, Sleep Timer]                         │
│    [Chapters Playlist (Left)  |  Saved Moments & Notes (Right)]                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

* **Clearance Invariant:** The scrollable content container always enforces `padding-bottom: 120px` across desktop and mobile, ensuring cards and controls are never occluded by the floating mini-player dock.
* **Full Player Overlay Invariant:** When `#view-player` is active, the mini-player dock (`#mini-player`) and topbar navigation pills are hidden via CSS to provide uninterrupted immersion.

---

## 5. Design Intent (What Stitch Should Optimize For)

When synthesizing screens for VibeAudio, Stitch should optimize for:
1. **Airy, Quiet Elegance:** Use generous spacing (`24px`–`48px`) and luminous `#F5F5F7` canvas tones that let cover art and typography speak.
2. **High-Tactility Hardware Feel:** Design controls that look satisfying to touch—soft ambient shadows, crisp 0.5px/1px hairline borders, and squircle pill buttons.
3. **Effortless Continuity:** Make the active story immediately apparent. A returning listener should be able to resume playback within 500ms of opening the application.
4. **Authentic Book Proportions:** Audiobook covers must always honor standard 2:3 vertical proportions. Never stretch, distort, or letterbox book covers.
5. **Legibility & Comfort:** Ensure high contrast against light surfaces (`#1D1D1F` text on white/canvas), with clear visual differentiation between titles (`Newsreader` serif) and functional UI (`Inter`).

---

## 6. Anti-Goals (What Stitch Must NEVER Do)

* ❌ **Do NOT design a commercial SaaS dashboard:** No analytics graphs, MRR charts, uptime gauges, or user conversion funnels.
* ❌ **Do NOT design an e-commerce storefront:** No price tags ("$14.99"), shopping cart icons, promotional coupons, "Buy Credits", or star rating summaries.
* ❌ **Do NOT overuse glassmorphism:** Only the floating topbar, floating mini dock, and modal backdrops may be translucent. Content cards, book items, and chapter lists must be crisp, solid `#FFFFFF` or `#F2F2F7`.
* ❌ **Do NOT use dark Obsidian mode in this phase:** Everything must strictly inhabit the light canvas (`#F5F5F7` / `#FFFFFF`).
* ❌ **Do NOT invent gamification or fake stats:** No listening streaks ("🔥 7 day streak!"), level-up badges, XP counters, or fake user metrics.
* ❌ **Do NOT use generic placeholder icons or font-awesome classes:** All iconography must reflect clean stroke-line geometry compatible with VibeAudio's custom 66-symbol sprite.
* ❌ **Do NOT invent arbitrary screen flows or popups:** Preserve the existing single-page architecture and view IDs.

---

## 7. Creative Freedom Boundaries

Stitch has explicit creative freedom within the boundaries established by `.stitch/DESIGN.md`:

* **Where Stitch Has Freedom:**
  * **Composition & Spatial Rhythm:** Fine-tuning whitespace balance, card grid padding, and visual hierarchy within the 1200px container.
  * **Editorial Typography Nuances:** Styling quote callouts, author credits, and chapter layout headers.
  * **Visual Presentation of Details:** Exploring refined card hover elevations, ambient light bloom softness behind book artwork, and subtle dividers.
  * **Empty State Compositions:** Creating elegant, literary empty-state compositions that feel calm and encouraging.
* **Where Stitch Is Strictly Bound:**
  * **Color Tokens:** Must strictly use `--color-canvas: #F5F5F7`, `--color-surface-1: #FFFFFF`, `--color-accent: #C64E00`, and `--color-text-primary: #1D1D1F`.
  * **Font Families:** `Newsreader` for titles, `Inter` for UI, `JetBrains Mono` for timecodes.
  * **Canonical 01–08 Screen Taxonomy:** Exact screen IDs, roles, and purposes.
  * **DOM & Functional Invariants:** Must respect contracted IDs (`#mini-player`, `#view-home`, `#detail-cover`, etc.).
