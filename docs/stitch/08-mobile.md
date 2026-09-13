# Stitch Screen Prompt 08 — Mobile Adaptation Strategy (Home Sanctuary 390×844)

**Prompt ID:** `STITCH-SCR-008`  
**Screen Target:** Mobile Viewport Adaptation using Home Shelf (`#view-home` in `src/pages/app.html`) as Canonical Reference  
**Viewport:** Mobile 390×844 (iPhone 13/14/15/16 Pro portrait)  
**Design Reference:** iOS Apple Books Mobile App & iOS HIG Single-Thumb Ergonomics  

---

## 1. Screen Objective
Synthesize the **mobile adaptation strategy** of VibeAudio using the **Home view experience** as the canonical design reference.

> [!IMPORTANT]
> **Focused Scope Mandate:**  
> Prompt 08 must **NOT** attempt to render three separate application screens (drawer, home, and full player) simultaneously on one canvas.  
> Instead, it establishes the unified mobile architectural rules on a single cohesive mobile viewport (390×844):
> 1. Top safe-area clearance & compact frosted navigation bar
> 2. Vertically stacked Continue Listening hero card
> 3. Two-column responsive catalog rhythm
> 4. Persistent floating mini-player dock resting above the bottom Home Indicator safe-area inset
> 5. 44×44px minimum thumb tap targets throughout

All other views (Library, Offline, Profile, Full Player) inherit responsive behavior directly from `.stitch/DESIGN.md` and component specifications.

---

## 2. Existing Product Context & Invariants
* **Mobile Topbar:** Sticky 54px bar with hamburger trigger (`#menu-btn`), brand lockup, search button, and account trigger. Center desktop navigation tabs are hidden.
* **Mobile Content Shell:** Single-column scroll container with `16px` horizontal margin and `padding-bottom: 120px` to clear the floating dock.
* **Continue Listening Hero:** Vertically stacked card (`#home-resume-hero`) with 2:3 vertical artwork, chapter tag, progress bar, and 48px high "Resume Listening" action button.
* **On This Device Shelf:** Horizontal scrollable shelf (`#home-offline-grid`) with touch momentum.
* **Catalog Discovery Shelf:** Compact 2-column grid (`repeat(2, 1fr)`) with 12px gap.
* **Floating Mini Dock:** Persistent bar (`#mini-player`) fixed at `bottom: max(12px, env(safe-area-inset-bottom, 12px))`.

---

## 3. Visual Direction & Layout (Mobile Portrait 390×844)

```
┌───────────────────────────────────────┐  ▲ Status Bar Safe Area (env(safe-area-inset-top))
│ [☰]  VibeAudio              [🔍] [👤] │  ◄── Compact Frosted Topbar (54px height)
├───────────────────────────────────────┤
│                                       │
│ CONTINUE LISTENING                    │
│ ┌───────────────────────────────────┐ │
│ │ ┌──────────┐  Harry Potter &      │ │
│ │ │ Cover    │  Half-Blood Prince   │ │  ◄── Stacked Hero Card (#FFFFFF)
│ │ │ (2:3)    │  J.K. Rowling        │ │
│ │ └──────────┘  Ch 14 · 54%         │ │
│ │ ════════════════ 54% ════════════ │ │  ◄── Accent progress track (#C64E00)
│ │ [ ▶ Resume Listening            ] │ │  ◄── Full-width 48px touch CTA
│ └───────────────────────────────────┘ │
│                                       │
│ ON THIS DEVICE           [ View All ] │
│ ┌────────────┐  ┌────────────┐        │
│ │ [Cover]    │  │ [Cover]    │        │  ◄── Horizontal scrollable shelf
│ │ [✓ OPFS]   │  │ [✓ OPFS]   │        │
│ │ Title      │  │ Title      │        │
│ └────────────┘  └────────────┘        │
│                                       │
│ PICKED FOR YOU                        │
│ ┌────────────┐  ┌────────────┐        │
│ │ [Cover]    │  │ [Cover]    │        │  ◄── 2-column catalog grid (12px gap)
│ │ The Hobbit │  │ Last Wish  │        │
│ └────────────┘  └────────────┘        │
│                                       │
├───────────────────────────────────────┤
│ ═════════════════ 54% ═══════════════ │  ◄── 2px accent line (#C64E00)
│ [Cover 40px] HP & Half-Blood [↺] (▶)  │  ◄── Floating Mini Dock (60px height)
└───────────────────────────────────────┘  ▼ Home Indicator Safe Area (env(safe-area-inset-bottom))
```

---

## 4. Mobile Ergonomics & Spacing Strategy

* **Viewport Dimensions:** 390px width × 844px height (iPhone 14/15/16 reference).
* **Safe-Area Padding Rules:**
  ```css
  .app-topbar {
      top: max(8px, env(safe-area-inset-top, 8px));
  }
  .player-bar.mini-dock {
      bottom: max(12px, env(safe-area-inset-bottom, 12px));
      width: calc(100% - 24px);
      left: 12px;
      right: 12px;
  }
  .main-content {
      padding-bottom: 120px;
  }
  ```
* **Touch Targets:**
  * All interactive triggers (hamburger, search, account, play/pause, step buttons): **Minimum 44 × 44px**.
  * Primary resume action button: 48px height, full-width within hero card.
* **Typography Scaling:**
  * Section Eyebrow: `11px`, 700 uppercase, letter-spacing `0.12em`.
  * Hero Book Title: `20px` `Newsreader` bold (2-line clamp).
  * Card Titles: `15px` `Newsreader` bold.
  * Metadata & Author: `13px` `Inter` (`#6E6E73`).
* **Grid Spacing Rhythm:**
  * Section vertical gap: `24px`.
  * Catalog card gap: `12px`.
  * Screen horizontal margins: `16px`.

---

## 5. Components & Tokens
* `Canvas Background`: `#F5F5F7`
* `Card Surfaces`: Pristine `#FFFFFF` with `14px` squircle corners and `1px solid rgba(0, 0, 0, 0.08)` border.
* `Primary Accent`: `#C64E00` (verified 4.67:1 WCAG AA contrast).
* `Mini Dock Glass`: `rgba(255, 255, 255, 0.85)` with `backdrop-filter: blur(20px)` and `-webkit-backdrop-filter: blur(20px)`.

---

## 6. Things Stitch Must Avoid
* ❌ **Do NOT generate multiple screen states side-by-side in this prompt:** Focus strictly on the single mobile Home viewport.
* ❌ Avoid tiny touch targets (< 44px) or cramped buttons near screen edges.
* ❌ Avoid horizontal overflow or multi-column text that causes scrolling bugs.
* ❌ Avoid overlapping the bottom Home Indicator safe area.
* ❌ Avoid dark background mode.
