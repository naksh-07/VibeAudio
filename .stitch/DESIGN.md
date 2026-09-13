---
name: VibeAudio
description: Distraction-free, personal audiobook sanctuary (Light Editorial Sanctuary)
colors:
  primary: "#C64E00"
  primary-hover: "#A84200"
  primary-active: "#8F3900"
  surface: "#FFFFFF"
  surface-secondary: "#F2F2F7"
  surface-tertiary: "#E5E5EA"
  canvas: "#F5F5F7"
  text-primary: "#1D1D1F"
  text-secondary: "#6E6E73"
  text-tertiary: "#86868B"
  text-muted: "#AEAEB2"
  success: "#248A3D"
  warning: "#C96E00"
  error: "#D70015"
typography:
  display-hero:
    fontFamily: Newsreader
    fontSize: 48px
    fontWeight: 600
    lineHeight: 1.06
    letterSpacing: -0.035em
  title-player:
    fontFamily: Newsreader
    fontSize: 36px
    fontWeight: 600
    lineHeight: 1.10
    letterSpacing: -0.025em
  title-shelf:
    fontFamily: Inter
    fontSize: 22px
    fontWeight: 600
    lineHeight: 1.18
    letterSpacing: -0.02em
  title-card:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: 600
    lineHeight: 1.20
    letterSpacing: -0.015em
  body-standard:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: 400
    lineHeight: 1.60
    letterSpacing: -0.01em
  body-medium:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: 500
    lineHeight: 1.50
    letterSpacing: -0.01em
  label-author:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 500
    lineHeight: 1.40
    letterSpacing: 0
  label-timecode:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: 500
    lineHeight: 1.20
    letterSpacing: 0.02em
  label-kicker:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: 700
    lineHeight: 1.10
    letterSpacing: 0.12em
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
rounded:
  sm: 6px
  md: 10px
  card: 14px
  panel: 18px
  sheet: 24px
  full: 999px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#FFFFFF"
    rounded: "{rounded.full}"
    padding: 10px 22px
    height: 44px
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-primary-active:
    backgroundColor: "{colors.primary-active}"
  button-secondary:
    backgroundColor: "{colors.surface-secondary}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.full}"
    padding: 10px 20px
    height: 44px
  card-book:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.card}"
  dock-mini-player:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.sheet}"
    height: 62px
  canvas-viewport:
    backgroundColor: "{colors.canvas}"
  shelf-divider:
    backgroundColor: "{colors.surface-tertiary}"
  body-copy:
    textColor: "{colors.text-secondary}"
  caption-meta:
    textColor: "{colors.text-tertiary}"
  control-disabled:
    textColor: "{colors.text-muted}"
  indicator-success:
    textColor: "{colors.success}"
  indicator-warning:
    textColor: "{colors.warning}"
  indicator-destructive:
    textColor: "{colors.error}"
---

# Design System: VibeAudio (Light Editorial Sanctuary)

**Document ID:** `STITCH-DS-001`  
**Specification Standard:** Google Stitch Semantic Design System (`DESIGN.md`)  
**Target Engine:** Google Stitch Canvas & Antigravity Implementation  
**Stitch Project ID:** `6063499620727826815`  
**Stitch Design System Asset ID:** `3782265180cc4ca5b6153874396ac6c9`  
**Status:** Canonical Visual Design Source of Truth  

---

## 1. Visual Theme & Atmosphere

VibeAudio is a distraction-free, personal audiobook sanctuary. The interface atmosphere is **luminous, literary, and calm**—reminiscent of an airy private reading room or luxury hardcover edition rather than a commercial audio storefront.

* **Density:** Balanced Daily Listening (Score: 5/10). Generous whitespace that breathes, giving priority to cover artwork and typographic legibility.
* **Variance:** Offset Editorial Asymmetry (Score: 6/10). Asymmetric hero resume stage, structured 4-column catalog grids, and tactile bottom transport dock.
* **Motion:** Fluid Tactile Restraint (Score: 5/10). Subtle spring-physics button compressions, gentle card hover elevations, and smooth sheet transitions. No decorative distraction.
* **Aesthetic Anchors:** Apple Books + macOS Sequoia + iOS HIG lightness paired with classic transitional serif editorial typography (`Newsreader`).

---

## 2. Color Palette & Roles

Every color role is calibrated for high legibility, zero screen glare, and strict WCAG 2.1 AA accessibility. Pure black (`#000000`) and artificial neon glows are strictly forbidden.

### 2.1 Canvas & Neutral Surfaces
* **Canvas Light Gray** (`#F5F5F7`) — The universal viewport canvas background. Calm, glare-free, matte.
* **Pure Surface White** (`#FFFFFF`) — Primary content cards, audiobook catalog cards, modal dialogs, chapter containers.
* **Secondary Soft Tint** (`#F2F2F7`) — Secondary surfaces, chapter list items, search inputs, inactive filter pills, stat boxes.
* **Tertiary Hover Tone** (`#E5E5EA`) — Hover state for secondary surfaces, subtle card dividers, pressed states.
* **Translucent Frosted Surface** (`rgba(255, 255, 255, 0.78)`) — Floating top navigation bar and floating mini-player dock (paired with `backdrop-filter: blur(24px)`).
* **Backdrop Dimmer Scrim** (`rgba(245, 245, 247, 0.85)`) — Modal dialog and mobile drawer backdrop dimmers.

### 2.2 Typographic Contrast Hierarchy
* **Deep Carbon Black** (`#1D1D1F`) — Primary text, book titles, section headlines, active transport play icons, active tab labels. **Contrast ratio: 13.5:1 on white / 12.8:1 on canvas** (Exceeds WCAG AAA).
* **Apple Stone Gray** (`#6E6E73`) — Secondary text, author bylines, section subtitles, time remaining, body copy. **Contrast ratio: 4.9:1 on white / 4.6:1 on canvas** (Exceeds WCAG AA).
* **Medium Charcoal** (`#48484A`) — Medium-emphasis labels, secondary button text, active category pill text. **Contrast ratio: 8.2:1 on white** (Exceeds WCAG AAA).
* **Dim Slate Gray** (`#86868B`) — Timecodes, part numbers, inactive icons, placeholder text. (Exceeds 3:1 for large/graphical elements).
* **Hairline Muted** (`#AEAEB2`) — Disabled controls, subtle decorative dividers.

### 2.3 Canonical Primary Accent (Terracotta Amber)
* **Primary Accent** (`#C64E00`) — Primary call-to-action buttons, active play state, scrubber fill, active badge kickers, focus rings.
  * **WCAG 2.1 AA Contrast Rationale:** Pure white text (`#FFFFFF`) on `#C64E00` yields **4.67:1**, strictly exceeding the mandatory 4.5:1 threshold for normal text (< 18.66px bold / < 24px regular). On `#F5F5F7` canvas it yields **4.28:1** (> 3:1 for graphical UI objects and large headlines).
  * **Accent Hover:** `#A84200` (Deepens contrast to 5.6:1 on button hover).
  * **Accent Pressed / Active:** `#8F3900` (Tactile press feedback, 7.0:1 contrast).
  * **Accent Soft Tint:** `rgba(198, 78, 0, 0.08)` (Background for active category pills, active chapter rows, subtle badges).
  * **Accent Border:** `rgba(198, 78, 0, 0.24)` (Border for active items, selected chips, focus outlines).
  * **Accent Ambient Glow:** `rgba(198, 78, 0, 0.12)` (Soft, warm aura around the 56px main play button).

> [!IMPORTANT]
> **Accent Usage Guardrail:**
> `#C64E00` must be used for buttons (with pure white text), active scrubber tracks, active tab indicators, and kicker eyebrows. It must **NEVER** be used as running body text, author bylines, or lengthy paragraphs.

### 2.4 Semantic Status Tokens
* **Success (Downloaded / Synced):** `#248A3D` (Apple Dark Green, > 4.5:1). Soft background: `rgba(52, 199, 89, 0.12)`. Border: `rgba(52, 199, 89, 0.28)`.
* **Warning (Pending Sync / Action Required):** `#C96E00`. Soft background: `rgba(255, 149, 0, 0.12)`.
* **Destructive (Failed / Delete Offline Audio):** `#D70015` (Apple Red). Soft background: `rgba(255, 59, 48, 0.10)`. Border: `rgba(255, 59, 48, 0.24)`.
* **Information (Browser Local / Notes):** `#0062CC`. Soft background: `rgba(0, 122, 255, 0.10)`.

### 2.5 Borders & Dividers
* **Hairline Border:** `rgba(0, 0, 0, 0.08)` (Crisp edge definition on white cards).
* **Strong Border:** `rgba(0, 0, 0, 0.14)` (Card hover, active states, modal borders).
* **Subtle Shelf Separator:** `rgba(0, 0, 0, 0.04)`.
* **Divider Line:** `rgba(0, 0, 0, 0.06)`.

---

## 3. Typography Architecture

The typography pairs classic literary serif tradition with modern operating-system UI crispness:

```
Newsreader (Transitional Serif) ──► Audiobook Titles, Section Eyebrows, Metric Numbers
Inter (Modern Grotesque)       ──► UI Controls, Metadata, Navigation, Author Bylines
JetBrains Mono (Tabular Mono)  ──► Scrubber Timecodes, Chapter Tallies, Storage Figures
```

### 3.1 Typeface Stacks
* **Display / Literary Serif:** `'Newsreader', Georgia, 'Times New Roman', serif`
* **UI / Body / Functional:** `'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif`
* **Monospace / Timecodes:** `'JetBrains Mono', 'SF Mono', ui-monospace, Menlo, Monaco, Consolas, monospace`

### 3.2 Typographic Hierarchy & Application
* **Display Hero:** `clamp(2.4rem, 4.4vw, 3.8rem)` | Weight: 600 | Line-height: 1.06 | Tracking: `-0.035em` | Application: Landing page headline.
* **Title 1 (Player Sanctuary):** `clamp(1.8rem, 3.2vw, 2.75rem)` | Weight: 600 | Line-height: 1.10 | Tracking: `-0.025em` | Application: Book title in Full Player.
* **Title 2 (Shelf Header):** `1.35rem (21.6px)` | Weight: 600 | Line-height: 1.18 | Tracking: `-0.02em` | Application: Shelf titles ("Continue Listening", "Picked for You").
* **Title 3 (Card Headline):** `1.15rem (18.4px)` | Weight: 600 | Line-height: 1.20 | Tracking: `-0.015em` | Application: Audiobook title on cards (2-line clamp).
* **Body Standard:** `0.94rem (15px)` | Weight: 400 | Line-height: 1.60 | Tracking: `-0.01em` | Application: Book summaries, landing copy.
* **Body Medium / Actions:** `0.94rem (15px)` | Weight: 500 | Line-height: 1.50 | Tracking: `-0.01em` | Application: Button text, table headers.
* **Author Subtitle:** `0.84rem (13.5px)` | Weight: 500 | Line-height: 1.40 | Tracking: `0` | Application: Card author bylines (`#6E6E73`).
* **Timecode / Tabular:** `0.78rem (12.5px)` | Weight: 500 | Line-height: 1.20 | Tracking: `0.02em` | Application: Scrubber elapsed/total times (`font-variant-numeric: tabular-nums`).
* **Kicker / Eyebrow:** `0.70rem (11.2px)` | Weight: 700 | Line-height: 1.10 | Tracking: `0.12em` | Uppercase | Application: Category tags, status pills.

---

## 4. Spacing Scale (4pt / 8pt Discipline)

* `--space-1` (4px): Internal badge padding, micro gaps.
* `--space-2` (8px): Button icon gaps, tag cluster spacing.
* `--space-3` (12px): List item internal padding, small card gaps.
* `--space-4` (16px): Standard card content padding, grid gaps.
* `--space-5` (20px): Topbar padding, player transport gaps.
* `--space-6` (24px): Section padding, container horizontal margins.
* `--space-8` (32px): Card grid row gaps, hero spacing.
* `--space-12` (48px): Major view section separation.

---

## 5. Border Radius System (Squircle Curvature)

Organic hardware-inspired squircle curvature:
* **Small (`6px`):** Source type badges, small chips, tooltip bubbles.
* **Medium (`10px`):** Chapter list items, search input fields, mini-player artwork.
* **Card (`14px`):** Audiobook catalog cards, resume hero artwork.
* **Panel (`18px`):** Full player transport deck, chapter container panel.
* **Sheet (`24px`):** Topbar floating shell, mini-player dock, profile modal sheet.
* **Pill (`999px`):** Buttons, filter category pills, offline status tags, scrubber thumb.

---

## 6. Depth, Elevation & Glass Materiality

### 6.1 Shadow Architecture
In light theme, shadows represent ambient light occlusion rather than dark halos:
* **Subtle Resting Shadow:** `0 2px 8px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02)` (Catalog cards).
* **Card Interactive Shadow:** `0 6px 20px rgba(0, 0, 0, 0.05), 0 1px 4px rgba(0, 0, 0, 0.02)` (Elevated cards on hover).
* **Elevated Panel Shadow:** `0 12px 32px rgba(0, 0, 0, 0.08), 0 2px 6px rgba(0, 0, 0, 0.03)` (Full player transport deck, modals).
* **Floating Dock Shadow:** `0 16px 44px rgba(0, 0, 0, 0.10), 0 4px 12px rgba(0, 0, 0, 0.04)` (Floating mini-player dock).
* **Focus Ring:** `0 0 0 3px rgba(198, 78, 0, 0.28)` (Keyboard accessible focus).

### 6.2 Strict Glass Materiality Rules
* **Allowed Glass Surfaces (Only 3):**
  1. **Floating App Topbar (`.app-topbar`):** `background: rgba(255, 255, 255, 0.78); backdrop-filter: blur(20px) saturate(180%); -webkit-backdrop-filter: blur(20px) saturate(180%);`
  2. **Floating Mini-Player Dock (`.player-bar.mini-dock`):** `background: rgba(255, 255, 255, 0.82); backdrop-filter: blur(24px) saturate(190%); -webkit-backdrop-filter: blur(24px) saturate(190%); isolation: isolate;`
  3. **Modal & Sidebar Backdrop (`.modal-backdrop`):** `background: rgba(245, 245, 247, 0.75); backdrop-filter: blur(16px);`
* **Prohibited Glass Surfaces (Strictly Banned):**
  * ❌ Audiobook catalog cards (must be opaque `#FFFFFF`).
  * ❌ Chapter playlist items (must be solid `#F2F2F7` or `#FFFFFF`).
  * ❌ Main canvas background (must be solid `#F5F5F7`).

---

## 7. Component Stylings

### 7.1 Buttons & Controls
* **Primary Solid Button:** Min-height 44px, padding 10px 22px, border-radius 999px pill. Background `#C64E00`, pure white `#FFFFFF` text (weight 600), zero border, subtle warm shadow `0 4px 14px rgba(198, 78, 0, 0.24)`. Active state: `transform: scale(0.97)`.
* **Secondary Button:** Min-height 44px, pill radius. Background `#F2F2F7`, text `#1D1D1F`, border `1px solid rgba(0, 0, 0, 0.08)`. Hover: background `#E5E5EA`.
* **Ghost / Icon Button:** 44×44px circular tap target. Background transparent, icon stroke `#6E6E73`. Hover: background `rgba(0, 0, 0, 0.05)`, stroke `#1D1D1F`.
* **Destructive Button:** Min-height 40px, pill radius. Background `rgba(255, 59, 48, 0.10)`, text `#D70015`, border `1px solid rgba(255, 59, 48, 0.24)`.

### 7.2 Audiobook Cover Cards (`.book-card`)
* **Aspect Ratio:** Authentic 2:3 vertical proportion strictly maintained (`aspect-ratio: 2 / 3; object-fit: cover`).
* **Surface:** Solid `#FFFFFF`, `14px` squircle radius, `1px solid rgba(0, 0, 0, 0.08)` hairline border.
* **Hover:** Lift `translateY(-3px)`, shadow `0 6px 20px rgba(0, 0, 0, 0.05)`, cover scales subtly (`1.02`).
* **Badges:** Top-left genre kicker, bottom-left offline download status chip (`#248A3D` checkmark).

### 7.3 Interactive Range Scrubber (`.player-scrubber-container`)
* **Track:** 6px height, rounded pill ends, background `rgba(0, 0, 0, 0.06)`, active filled track `#C64E00`.
* **Thumb:** 18px diameter pure white `#FFFFFF` circle, subtle elevation shadow `0 2px 8px rgba(0, 0, 0, 0.18)`, expands to 22px on hover/drag for effortless touch manipulation.

### 7.4 Floating Mini-Player Dock (`#mini-player`)
* **Dimensions:** Height 62px, width `min(1200px, calc(100% - 32px))`, centered horizontally.
* **Position:** Fixed at bottom `max(16px, env(safe-area-inset-bottom, 16px))`, `z-index: 1000`.
* **Anatomy:** 2px top accent line (`#C64E00`), 42×42px square book thumbnail with 6px radius, single-line clamped title and chapter, 3 tactile transport buttons (Back 15s, 42px Play circle, Forward 30s).
* **Invariant:** Hides immediately when Full Player (`#view-player`) is active.

### 7.5 Empty States
* **Philosophy:** Calm, welcoming, useful. Clean line-drawing iconography from the 66-symbol sprite, clear single sentence explanation, and exactly one high-contrast action. No noisy illustrations.

---

## 8. Motion & Spring Physics

* **Spring Physics Baseline:** `stiffness: 120, damping: 18` — tactile, weighty, responsive feel without overshoot.
* **Transition Tokens:**
  * `--transition-fast`: `150ms cubic-bezier(0.2, 0, 0, 1)` (Button press, hover, focus).
  * `--transition-base`: `240ms cubic-bezier(0.2, 0, 0, 1)` (Card lift, tab toggle, filter switch).
  * `--transition-smooth`: `350ms cubic-bezier(0.4, 0, 0.2, 1)` (Drawer expand, player view transition).
* **Hardware Acceleration:** All animations strictly operate on `transform` and `opacity`. Never animate `top`, `left`, `width`, or `height`.
* **Reduced Motion:** When `prefers-reduced-motion: reduce` is active, transitions drop to `0.01ms`.

---

## 9. Layout Principles & Responsive Architecture

* **Container Constraint:** Maximum width `1200px` centered with `24px` to `32px` gutter padding.
* **Grid Hierarchy:**
  * Desktop (≥ 1024px): 4-column catalog grid (`repeat(4, 1fr)`), 24px gap.
  * Tablet (768px–1023px): 3-column catalog grid, 20px gap.
  * Mobile (< 768px): Strict single-column view flow with 2-column catalog grid (`repeat(2, 1fr)`), 12px gap.
* **Bottom Clearance:** All scrollable views must maintain `padding-bottom: 120px` to prevent the floating mini dock from occluding content.
* **Full Height Views:** Must use `min-h-[100dvh]` or `100vh` with safe-area fallback; avoid raw `100vh` on mobile to prevent iOS URL bar jump.

---

## 10. Anti-Patterns (Explicitly Banned)

* ❌ **No Emojis Anywhere:** All icons must originate exclusively from the custom 66-symbol `icons.svg` sprite.
* ❌ **No Pure Black (`#000000`):** Use Apple Dark Carbon (`#1D1D1F`) for text and contrast.
* ❌ **No AI-Purple / Neon Glows:** Cyan, electric violet, or magenta button glows are strictly banned.
* ❌ **No E-Commerce Storefront Clutter:** No prices ($19.99), "Buy credits", review star counts, or shopping carts.
* ❌ **No Fabricated Statistics:** Never invent listening streaks, XP points, gamification badges, or fake uptime SLAs.
* ❌ **No Glassmorphism on Content Cards:** Catalog cards and chapter lists must be crisp, solid `#FFFFFF` or `#F2F2F7`.
* ❌ **No Distorted Artwork:** Book covers must strictly preserve 2:3 vertical paperback proportions.
* ❌ **No Low-Contrast Body Text:** Text on white or canvas must never fall below `#6E6E73` (4.9:1 AA contrast).
