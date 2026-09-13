# VibeAudio — Stitch Master Design Brief: Light UI Redesign

**Document ID:** `DOC-STI-000`  
**Target Engine:** Google Stitch UI Synthesis & Design System  
**Role:** Master System Prompt for Stitch Screen Generation  
**Aesthetic Vision:** Apple Books + macOS/iOS-Inspired Light Minimalism (Audiobook Sanctuary)  
**Cross-References:** [`DOC-DES-001`](../design/VibeAudio-Light-Redesign-Brief.md), [`DOC-DES-002`](../design/VibeAudio-Light-Design-System.md), [`DOC-DES-004`](../design/VibeAudio-Component-Spec.md)  

---

## 1. Product Context & Identity

**VibeAudio** is a distraction-free, offline-first personal audiobook sanctuary built for the modern web and PWA. It is **guest-first** (no mandatory account), **privacy-first** (audio stored directly on user's device via OPFS), and **listening-first** (zero advertising, zero social algorithmic feeds, zero storefront upsells).

> **Master Directive for Stitch:**  
> Synthesize an authentic, premium light-mode user interface inspired by Apple Books, macOS Sequoia, and iPadOS audio utilities.  
> **Prioritize product-specific VibeAudio design.** Do NOT generate a generic "Apple-style audiobook app" or an iTunes/Audible clone. Every screen must reflect VibeAudio's unique features: guest continuity badges, local OPFS storage indicators, authentic 2:3 book proportions, and the floating tactile transport dock.

---

## 2. Core Visual Language & Design Tokens

### 2.1 Color Palette
* **Canvas Background:** `#F5F5F7` (Apple signature light gray, matte, calm, glare-free).
* **Primary Card Surface:** `#FFFFFF` (Pristine, crisp white).
* **Secondary Surface:** `#F2F2F7` (Subtle off-white for chips, chapter rows, and inputs).
* **Tertiary Hover Surface:** `#E5E5EA` (Interactive pressed and hover states).
* **Translucent Frosted Glass:** `rgba(255, 255, 255, 0.78)` with `backdrop-filter: blur(20px) saturate(180%)`.
* **Primary Text:** `#1D1D1F` (Authoritative dark charcoal, high contrast).
* **Secondary Text:** `#6E6E73` (Refined neutral gray for metadata and author bylines).
* **Tertiary Text / Timecodes:** `#86868B` (Tabular timecodes, part numbers).
* **Signature Accent:** `#E65A00` / `#FF9500` (Warm amber / terracotta, high contrast on light canvas).
* **Success (Downloaded / Synced):** `#248A3D` (Crisp dark green on light green chip `rgba(52, 199, 89, 0.12)`).
* **Hairline Borders:** `rgba(0, 0, 0, 0.08)`.

### 2.2 Typography
* **Editorial Book Headlines:** `Newsreader`, Georgia, serif — 600 weight, tight line-height (1.1), `-0.025em` tracking. Gives literary weight to book titles.
* **UI Controls & Metadata:** `Inter`, `-apple-system`, BlinkMacSystemFont, `SF Pro Text`, sans-serif — razor-sharp legibility.
* **Scrubbers & Timecodes:** `JetBrains Mono`, `SF Mono`, tabular numerals (`font-variant-numeric: tabular-nums`).

### 2.3 Radii & Elevation
* **Squircle Curvatures:** Cards (`14px`), Transport Panels (`18px`), Floating Shells (`24px`), Buttons/Pills (`999px`).
* **Multi-Layered Ambient Shadows:**
  * Card: `0 4px 18px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.02)`
  * Floating Dock: `0 16px 44px rgba(0, 0, 0, 0.10), 0 4px 12px rgba(0, 0, 0, 0.04)`

---

## 3. Structural Layout Rules

1. **Max Width & Spacing:** Max container width `1200px` centered with `24px` to `32px` gutter padding.
2. **Floating App Topbar:** Sticky `62px` high frosted glass bar (`.app-topbar`) hovering 14px below viewport top with pill-segmented navigation (`Home`, `Library`, `On This Device`).
3. **Floating Mini-Player Dock:** Persistent `62px` high frosted glass bar (`#mini-player`) floating above viewport bottom (`bottom: max(16px, env(safe-area-inset-bottom, 16px))`). Features micro-progress accent line along top edge, 42×42px cover art thumbnail, title/chapter text, and three tactile transport buttons (Back 15s, Play/Pause circle, Forward 30s).
4. **Hero Anchor on Home:** Dedicated "Continue Listening" editorial banner featuring 2:3 vertical cover art, chapter badge, and a prominent solid amber "Resume" button.
5. **Catalog Grid:** 4 columns on desktop (`≥ 1280px`), 3 columns on tablet (`1024px`), 2 columns on mobile (`390px`).

---

## 4. Master Do-Not-Do Rules for Stitch

* ❌ **Do NOT use dark backgrounds:** Do not produce dark mode or obsidian screens in this generation. Everything must strictly inhabit the `#F5F5F7` light canvas.
* ❌ **Do NOT copy Apple proprietary iconography or logos:** Never render the Apple logo, macOS red/yellow/green window dots, or simulated iOS home bars in web chrome.
* ❌ **Do NOT plaster glassmorphism across every surface:** Only the topbar, mini-player dock, and modal sheets may use `backdrop-filter`. All content cards and chapter lists must be solid, crisp white or secondary surface.
* ❌ **Do NOT add commercial e-commerce clutter:** Never add price tags ($19.99), "Buy Credit", review star counts, or shopping carts.
* ❌ **Do NOT use low-contrast gray text on white:** Body text must never be lighter than `#6E6E73`. Title text must be `#1D1D1F`.
* ❌ **Do NOT distort book cover art:** Book covers must always respect standard 2:3 vertical paperback/hardcover aspect ratios with `object-fit: cover`.
