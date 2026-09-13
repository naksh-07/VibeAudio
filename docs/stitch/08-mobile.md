# Stitch Screen Prompt 08 — Mobile PWA Experience (390×844)

**Prompt ID:** `STITCH-SCR-008`  
**Screen Target:** Mobile Viewports & iOS PWA Standalone Mode  
**Viewport:** Mobile 390×844 (iPhone 13/14/15/16 Pro)  
**Design Reference:** iOS Apple Books Mobile App & Apple Podcasts Sheet Navigation  

---

## 1. Screen Objective
Synthesize the complete mobile smartphone experience of VibeAudio. The design must accommodate single-thumb ergonomics, bottom safe-area insets (Home Indicator and Notch/Dynamic Island), compact navigation drawer, and an iOS-style bottom sheet player transition.

---

## 2. Existing Product Context & Invariants
* **Mobile Topbar:** Hamburger button (`#menu-btn`), brand lockup, search trigger, and account button. Center desktop nav pills are hidden.
* **Side Navigation Drawer:** `#sidebar` and `#sidebar-overlay` with navigation items (`Home`, `Library`, `On This Device`, `Listening History`, `About`, `Install App`, `My Account`).
* **Floating Mini Dock:** Fixed at bottom: `bottom: max(16px, env(safe-area-inset-bottom, 16px));`.
* **Full Player Mobile Layout:** Stacks header card, transport deck, and chapter list into a fluid vertical scroll sheet.

---

## 3. Visual Direction & Layout (Mobile Portrait)

```
┌───────────────────────────────────────┐  ▲ Status Bar (Dark Text on #F5F5F7)
│ [☰]  VibeAudio              [🔍] [👤] │  ◄── Compact Frosted Topbar
├───────────────────────────────────────┤
│                                       │
│ CONTINUE LISTENING                    │
│ ┌───────────────────────────────────┐ │
│ │ ┌──────────┐  Harry Potter &      │ │
│ │ │ Cover    │  Half-Blood Prince   │ │
│ │ │ (2:3)    │  J.K. Rowling        │ │
│ │ └──────────┘  Ch 14 · 54%         │ │
│ │ ════════════════ 54% ════════════ │ │
│ │ [ ▶ Resume ]        [ Chapters ]  │ │
│ └───────────────────────────────────┘ │
│                                       │
│ ON THIS DEVICE           [ View All ] │
│ ┌────────────┐  ┌────────────┐        │
│ │ [Cover]    │  │ [Cover]    │        │
│ │ [✓ OPFS]   │  │ [✓ OPFS]   │        │
│ │ Title      │  │ Title      │        │
│ └────────────┘  └────────────┘        │
│                                       │
│ PICKED FOR YOU                        │
│ ┌────────────┐  ┌────────────┐        │
│ │ [Cover]    │  │ [Cover]    │        │
│ │ The Hobbit │  │ Last Wish  │        │
│ └────────────┘  └────────────┘        │
│                                       │
├───────────────────────────────────────┤
│ ═════════════════ 54% ═══════════════ │ ◄── Floating Mini Dock
│ [Cover 40px] HP & Half-Blood [↺] (▶)  │
└───────────────────────────────────────┘  ▼ Home Indicator Safe Area
```

* **Mobile Navigation Bar:**
  * Height: 54px, sticky at top 8px.
  * Frosted glass: `background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(20px); border-radius: 18px;`.
  * Hamburger button `#menu-btn` with 44×44px hit area.
* **Side Drawer Navigation (`#sidebar`):**
  * Slides smoothly from left edge (`transform: translateX(0)`), width `280px`.
  * White surface `#FFFFFF` with `0 0 40px rgba(0, 0, 0, 0.15)` drop shadow.
  * Navigation items with generous 48px row height, custom SVG icons, and active amber accent indicator.
* **Mobile Card Grids:**
  * 2-column catalog grid (`repeat(2, 1fr)`) with `12px` gap.
  * Audiobook cards display crisp covers, single-line clamped title in `Newsreader` (15px), and offline badges.
* **Mobile Full Player:**
  * Header card stacks cover art to centered 140px width.
  * Large, easily pressable transport deck: 56px play button, 42px step buttons.
  * Scrubber slider thumb enlarged to 22px for easy touch grabbing without precision frustration.

---

## 4. Mobile Touch & Ergonomics Targets
* Minimum touch target for all clickable controls: **44 × 44px**.
* Bottom padding on scrollable view sections: `padding-bottom: 120px` to ensure the floating mini dock never covers content or buttons.
* Safe-area compliance:
```css
.player-bar.mini-dock {
    bottom: max(12px, env(safe-area-inset-bottom, 12px));
    width: calc(100% - 24px);
}
```

---

## 5. Things Stitch Must Avoid
* ❌ Avoid tiny touch targets or cramped buttons close to screen edges.
* ❌ Avoid blocking the iOS bottom home swipe indicator.
* ❌ Avoid multi-column text that causes horizontal viewport overflow.
* ❌ Avoid fixed desktop widths; all widths must be percentage or `clamp()` based.
