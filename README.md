# VibeAudio

**A Personal Audiobook Sanctuary.** A calm, lightweight, and immersive audiobook listening experience built for the modern web — offline-first, guest-first, and beautifully minimal.

---

## Introduction

**VibeAudio** is a listening-first Progressive Web App that puts your audiobooks front and center with zero friction. Open it, press play — no account required. It features a tactile **Dark Obsidian** design system, adaptive theming that harmonizes with book cover art, completely private device storage via OPFS & IndexedDB, and optional cloud sync across devices.

**No bloat. No forced sign-in. Just vibes.**

---

## Key Features

### 🎧 Listening Sanctuary
Distraction-free player with variable speed (0.5×–2.0×), smooth sleep timer with volume fadeout, smart seek (15s back / 30s forward), and a full chapter timeline.

### 💾 Offline Shelf — "On This Device"
Download unabridged audiobooks directly to private browser storage (OPFS + IndexedDB) for complete offline listening. No network dependency once downloaded.

### ✨ Instant Guest Listening
Listen the moment you arrive. Progress, bookmarks, and downloads are stored locally on your device with no account needed.

### ☁️ Optional Cloud Sync
Sign in with Clerk to back up progress and notes to AWS DynamoDB and resume seamlessly across all your devices.

### 📱 Full PWA Experience
Installable Progressive Web App with standalone display mode, maskable adaptive icons, Service Worker precaching, background fetch, OS share target, and safe-area inset support.

### 🔖 Saved Moments & Notes
Pin favorite timestamped scenes and personal notes directly to the chapter timeline.

### 🎨 Chameleon Theming
Dynamic visual ambiance that adapts subtly to each book's cover artwork via *Color Thief*.

### 🔇 Vocal Clarity Booster
Optional audio processing that enhances speech clarity for spoken-word listening comfort.

### 🎵 YouTube & Direct Audio Sources
Seamlessly streams audiobooks from YouTube audio or direct MP3/M4B sources with smart chapter resolution.

---

## Brand & Design System

VibeAudio uses a fully custom, **zero-CDN** icon and brand system.

### Brand Mark — Hybrid 1 Warm Minimal

The locked brand mark is a 24×24 vector mark with a **1.85px stroke**, rounded terminals, organic outer-page curvature, and a resonant V-keystone negative space chamber — warm amber `#C9852A` on Dark Obsidian.

### Custom SVG Icon Sprite

All UI icons are served from a single embedded SVG sprite (`icons.svg`) with **66 fully custom semantic symbols** — zero external icon font dependencies.

| Property | Value |
|---|---|
| Sprite file | `frontend/src/icons/icons.svg` |
| Symbol count | 66 |
| File size | 18.3 KB |
| CDN dependencies | **None** |
| Offline available | ✅ Precached by Service Worker |

### Asset Bundle

| Asset | Size |
|---|---|
| Brand mark SVG | 0.5 KB |
| Monochrome brand mark SVG | 0.4 KB |
| Horizontal / compact / stacked lockup SVGs | ~0.9 KB each |
| Adaptive favicon SVG | 0.5 KB |
| PWA icon 192×192 | 2.9 KB |
| PWA icon 512×512 | 8.8 KB |
| Maskable icon 512×512 | 8.0 KB |
| Apple Touch Icon 180×180 | 2.8 KB |

---

## Tech Stack

### Frontend
- **Core:** Vanilla HTML5 · CSS3 · Native ES Modules (no build step, no framework)
- **Design System:** CSS Custom Properties · Dark Obsidian theme · `.vibe-icon` SVG sizing system
- **Typography:** Newsreader (display) · Inter (UI)
- **Offline & Storage:** Origin Private File System (OPFS) · IndexedDB · Cache Storage API · Service Worker
- **PWA:** Web App Manifest · Maskable icons · OS Share Target · Background Fetch · App Badging
- **Auth (optional):** Clerk Authentication SDK with full guest fallback
- **Audio:** HTML5 Audio Engine · YouTube audio stream compatibility · Web Audio API (vocal clarity)
- **Theming:** Color Thief

### Backend (Optional — Cloud Sync)
- **Runtime:** Node.js on AWS Lambda (serverless REST endpoints)
- **Database:** AWS DynamoDB (progress sync, catalog)
- **Edge:** Cloudflare Workers (optional routing layer)

---

## Project Structure

```
VibeAudio/
├── backend/                        # Serverless Backend (read-only in local dev)
│   ├── lambda/                     # AWS Lambda Functions (catalog, progress, auth)
│   └── package.json
├── frontend/                       # Web Application & PWA
│   ├── app.webmanifest             # PWA Manifest (icons, shortcuts, share target)
│   ├── index.html                  # Landing Page (embedded SVG sprite)
│   ├── service-worker.js           # Offline Precache & Fetch Handler (40 assets)
│   ├── public/
│   │   └── icons/                  # Brand mark vectors & raster PWA icons
│   └── src/
│       ├── css/                    # Modular Stylesheets
│       │   ├── base.css            # Design tokens, typography, vibe-icon system
│       │   ├── components.css      # Shared UI components
│       │   ├── app-sections.css    # Home, Library, On-Device views
│       │   ├── player.css          # Full player & transport deck
│       │   ├── landing.css         # Landing page styles
│       │   └── cover-media.css     # Cover art & chameleon theme
│       ├── icons/                  # SVG sprite, favicons & app icons
│       │   ├── icons.svg           # 66-symbol custom SVG sprite
│       │   ├── favicon.svg         # Adaptive vector favicon
│       │   ├── favicon-16.png      # 16×16 raster favicon
│       │   ├── favicon-32.png      # 32×32 raster favicon
│       │   └── favicon.ico         # Multi-size ICO for legacy browsers
│       ├── js/                     # Modular ES6 Logic
│       │   ├── api.js              # AWS catalog & sync API client
│       │   ├── auth.js             # Clerk auth + guest session manager
│       │   ├── player.js           # Core audio engine & Media Session API
│       │   ├── offline-shelf.js    # OPFS download manager & shelf state
│       │   ├── user-data.js        # Progress model, sync queue, bookmarks
│       │   ├── progress-model.js   # Recency comparison & normalization
│       │   ├── pwa.js              # PWA install, badging, share & file handling
│       │   ├── landing.js          # Landing page interactivity & spotlight
│       │   ├── ui.js               # Main app UI orchestration
│       │   ├── ui-library.js       # Library catalog, filters & source badges
│       │   ├── ui-player-main.js   # Full player transport deck UI
│       │   ├── ui-player-list.js   # Chapter list & timeline UI
│       │   ├── ui-player-helpers.js# Formatting & player helpers
│       │   ├── ui-dom.js           # DOM query cache & selectors
│       │   ├── ui-formatters.js    # Time & number formatters
│       │   ├── ui-library-insights.js # Library statistics panel
│       │   ├── config.js           # Environment configuration
│       │   └── app-entry.js        # Application bootstrap
│       └── pages/
│           └── app.html            # Main App Shell (embedded SVG sprite)
├── tests/                          # Automated Contract & Invariant Tests (12 suites)
│   ├── icon-system.test.mjs        # Brand mark & SVG icon system verification
│   ├── offline-shelf.test.mjs      # OPFS storage & download state machine
│   ├── sync-queue.test.mjs         # Progress sync queue invariants
│   ├── progress-model.test.mjs     # Recency model & normalization
│   ├── player-lifecycle-token.test.mjs  # Monotonic load token race conditions
│   ├── media-session-hardening.test.mjs # Media Session API contracts
│   ├── pwa-manifest-sw.test.mjs    # PWA manifest & Service Worker integrity
│   ├── pwa-stage2-sync-download.test.mjs  # Background sync & download phase
│   ├── pwa-stage3-native-integration.test.mjs # OS file, share & native features
│   ├── download-state-machine.test.mjs  # Download lifecycle state transitions
│   ├── accessibility.test.mjs      # ARIA, semantic HTML & a11y contracts
│   └── ui-contracts.test.mjs       # DOM structure regression invariants
├── tools/                          # Supplementary Verification Scripts
│   ├── test-reliability.mjs        # Phase 1 reliability invariants
│   ├── test-phase2-pwa.mjs         # Phase 2 PWA & release infrastructure
│   └── serve.mjs                   # Local static dev server (port 4173)
├── package.json                    # Scripts & dependencies
└── README.md
```

---

## Getting Started

### Prerequisites

- **Node.js** v18 or later
- A modern browser with OPFS + Service Worker support (Chrome 86+, Edge 86+, Safari 15.2+, Firefox 111+)

### 1. Clone the Repository

```bash
git clone https://github.com/naveenamre/VibeAudio.git
cd VibeAudio
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Run the Test Suite

```bash
# Run all 12 contract & invariant test suites (116 tests)
npm test

# Run the full suite including reliability and PWA verification
npm run test:all
```

Expected output: **116 tests, 0 failures** across 12 suites.

### 4. Start the Local Dev Server

```bash
node tools/serve.mjs
```

Then open:

| URL | View |
|---|---|
| `http://localhost:4173` | Landing page |
| `http://localhost:4173/src/pages/app.html#home` | Home — listening sanctuary |
| `http://localhost:4173/src/pages/app.html#library` | Library catalog |
| `http://localhost:4173/src/pages/app.html#device` | On This Device (offline shelf) |

Start listening immediately as a guest — no setup required.

---

## Test Suite Overview

VibeAudio maintains a comprehensive automated test suite using Node.js's built-in test runner (`node --test`).

| Suite | Coverage |
|---|---|
| `icon-system` | Brand mark assets, 66-symbol SVG sprite, raster budgets, zero Font Awesome |
| `offline-shelf` | OPFS import pipeline, deduplication, file validation, storage contracts |
| `sync-queue` | Pending queue enqueue/dedup, flush invariants, guest isolation |
| `progress-model` | Recency normalization, finished-book threshold, timestamp comparison |
| `player-lifecycle-token` | Monotonic load token race condition cancellation |
| `media-session-hardening` | Media Session API contracts, metadata, action handlers |
| `pwa-manifest-sw` | Manifest schema, SW precache inventory (40 assets), versioning |
| `pwa-stage2-sync-download` | Background sync, download phases, badge state |
| `pwa-stage3-native-integration` | OS file handling, share target, launch queue, badging |
| `download-state-machine` | Download lifecycle transitions, retry, cancellation |
| `accessibility` | ARIA roles, semantic HTML contracts, keyboard nav |
| `ui-contracts` | DOM structure regression invariants across all views |

**Total: 116 tests · 0 failures**

---

## Architecture Principles

- **Zero build step** — plain HTML, CSS, and native ES modules served directly
- **Offline-first** — all shell assets precached; audiobooks playable without network
- **Guest-first** — the app boots and works fully without authentication
- **No CDN dependencies** — all icons, fonts loaded locally or embedded
- **Privacy-preserving** — all user data lives in OPFS/IndexedDB on the user's device; cloud sync is strictly opt-in
- **Progressive enhancement** — every feature degrades gracefully when APIs are unavailable

---

## Contributing

1. Fork the project
2. Create your feature branch: `git checkout -b feature/AmazingFeature`
3. Ensure all tests pass: `npm run test:all`
4. Commit your changes: `git commit -m 'Add AmazingFeature'`
5. Push to the branch: `git push origin feature/AmazingFeature`
6. Open a Pull Request

---

## License

Distributed under the ISC License. See `LICENSE` for more information.

---

### Author

**Naveen Amre** — *Code, Vibe, Repeat.*
