# VibeAudio — Light Design System Specification

**Document ID:** `DOC-DES-002`  
**Status:** Design System Specification  
**Author:** Design Systems Architect  
**Aesthetic Foundation:** Apple Books + macOS/iOS-Inspired Light Minimalism  
**Target Core:** CSS Custom Properties (`frontend/src/css/base.css`)  
**Cross-References:** [`DOC-DES-001`](VibeAudio-Light-Redesign-Brief.md), [`DOC-IMP-001`](../implementation/VibeAudio-Light-UI-Implementation.md)  

---

## 1. Design Token Architecture

The VibeAudio Light Design System replaces the monolithic Dark Obsidian palette with a semantic, layered token architecture. Every color, dimension, and elevation level is expressed as an accessible CSS custom property.

```
┌─────────────────────────────────────────────────────────────┐
│                 SEMANTIC TOKEN ARCHITECTURE                 │
├─────────────────┬─────────────────┬─────────────────────────┤
│ Tier 1: Global  │ Tier 2: Surface │ Tier 3: Component       │
│ Base Primitives │ Semantic Roles  │ Specific Applications   │
│ (#F5F5F7, etc.) │ (--color-canvas)│ (.book-card background) │
└─────────────────┴─────────────────┴─────────────────────────┘
```

---

## 2. Color System: Luminous Apple Light Canvas

```
[ Canvas: #F5F5F7 ]
  └── [ Surface 1: #FFFFFF ] (Cards, Panels)
        └── [ Surface 2: #F2F2F7 ] (Secondary Chips, Inputs)
              └── [ Surface 3: #E5E5EA ] (Hover, Borders)
```

### 2.1 Canvas & Surfaces
| Token Name | Hex / RGBA Value | Semantic Usage |
|---|---|---|
| `--color-canvas` | `#F5F5F7` | The global viewport canvas (neutral light gray, no screen glare). |
| `--color-surface-1` | `#FFFFFF` | Primary content panels, audiobook cards, modal dialogs, chapter container. |
| `--color-surface-2` | `#F2F2F7` | Secondary surfaces, chapter list items, search inputs, inactive filter pills. |
| `--color-surface-3` | `#E5E5EA` | Hover state for secondary surfaces, subtle card dividers, pressed states. |
| `--color-surface-translucent`| `rgba(255, 255, 255, 0.78)` | Floating top navigation bar, floating mini-player dock (paired with blur). |
| `--color-surface-overlay` | `rgba(245, 245, 247, 0.85)` | Modal backdrop dimmers and mobile drawer sheet underlays. |

### 2.2 Text Hierarchy & Contrast Ratios
| Token Name | Hex Value | WCAG Contrast (on Canvas/Surface) | Usage |
|---|---|---|---|
| `--color-text-primary` | `#1D1D1F` | **13.5:1** (AAA) | Book titles, primary headings, transport play icon, active tab labels. |
| `--color-text-secondary` | `#6E6E73` | **4.9:1** (AA) | Author bylines, section descriptions, time remaining, body copy. |
| `--color-text-soft` | `#48484A` | **8.2:1** (AAA) | Medium-emphasis labels, secondary button text, filter pill text. |
| `--color-text-dim` | `#86868B` | **3.5:1** (Large text AA)| Timecodes, part numbers, inactive icons, placeholder text. |
| `--color-text-muted` | `#AEAEB2` | **2.2:1** (Non-text / subtle)| Disabled elements, hairline decorative dividers. |

### 2.3 Brand Accent: Warm Amber & Coral (Audiobook Signature)
In a light interface, standard yellow/amber washes out. VibeAudio uses an Apple Books-inspired warm terracotta/coral amber calibrated for crisp light-mode readability and strict WCAG 2.1 AA compliance:

| Token Name | Value | Purpose |
|---|---|---|
| `--color-accent` | `#C64E00` | Primary action buttons, active play state, scrubber fill, active badge kicker. |
| `--color-accent-hover` | `#A84200` | Hover state for primary buttons and interactive accents (deepens contrast to 5.6:1). |
| `--color-accent-active` | `#8F3900` | Pressed state for primary action buttons (7.0:1 contrast). |
| `--color-accent-soft` | `rgba(198, 78, 0, 0.08)` | Background for active filter pills, active chapter rows, subtle badges. |
| `--color-accent-border` | `rgba(198, 78, 0, 0.24)` | Border for active items, selected chips, and focus rings. |
| `--color-accent-glow` | `rgba(198, 78, 0, 0.12)` | Subtle ambient aura around the full player play button. |

#### Contrast Verification (WCAG 2.1 AA):
* **Text on Accent (Buttons):** Pure white text (`#FFFFFF`) on `#C64E00` yields **4.67:1** contrast ratio, strictly exceeding the minimum **4.5:1** requirement for normal text (< 18.66px bold / < 24px regular).
* **Accent on Canvas:** `#C64E00` on `#F5F5F7` yields **4.28:1** contrast ratio, exceeding the 3.0:1 requirement for large text, icons, and UI components.
* **Usage Rules:**
  * **Allowed:** Primary CTA buttons (with white text), active tab indicators, scrubber fill line, active chapter highlight bars, focus indicator rings, and category kicker tags.
  * **Prohibited:** Must **NEVER** be used as running body copy, author bylines, or lengthy descriptive paragraphs on white or canvas backgrounds.
* **Disabled Treatment:** When an accent button is disabled, background becomes `rgba(0, 0, 0, 0.08)` with `--color-text-muted` (`#AEAEB2`) or `rgba(198, 78, 0, 0.35)` with `pointer-events: none; opacity: 0.5; box-shadow: none;`.

### 2.4 Semantic Status Tokens
* **Success (Downloaded / Synced):**
  * `--color-success`: `#248A3D` (Apple Dark Green for light bg)
  * `--color-success-soft`: `rgba(52, 199, 89, 0.12)`
  * `--color-success-border`: `rgba(52, 199, 89, 0.28)`
* **Warning (Pending Sync / Update Available):**
  * `--color-warning`: `#C96E00`
  * `--color-warning-soft`: `rgba(255, 149, 0, 0.12)`
  * `--color-warning-border`: `rgba(255, 149, 0, 0.28)`
* **Danger (Failed Download / Remove):**
  * `--color-danger`: `#D70015`
  * `--color-danger-soft`: `rgba(255, 59, 48, 0.1)`
  * `--color-danger-border`: `rgba(255, 59, 48, 0.24)`
* **Information (Browser Source / Note):**
  * `--color-info`: `#0062CC`
  * `--color-info-soft`: `rgba(0, 122, 255, 0.1)`

### 2.5 Borders & Dividers
* `--color-border`: `rgba(0, 0, 0, 0.08)` (Hairline definition on white cards)
* `--color-border-strong`: `rgba(0, 0, 0, 0.14)` (Card hover, active states)
* `--color-border-subtle`: `rgba(0, 0, 0, 0.04)` (Internal shelf separators)
* `--color-divider`: `rgba(0, 0, 0, 0.06)`

---

## 3. Typography System

The typographic pairing honors the classic literary heritage of audiobooks while maintaining modern Apple-level interface crispness.

```
Newsreader (Literary Serif)  ──►  Audiobook Titles, Editorial Eyebrows, Big Numbers
Inter / system-ui (Modern)   ──►  UI Controls, Metadata, Navigation, Transports
SF Mono / Tabular (Monospace)──►  Timecodes, Chapters, Percentages, Storage
```

### 3.1 Typeface Stacks
* **Display / Literary Serif:**  
  `--font-display: 'Newsreader', Georgia, 'Times New Roman', serif;`
* **UI / Body / Functional:**  
  `--font-body: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;`
* **Monospace / Timecodes:**  
  `--font-mono: 'JetBrains Mono', 'SF Mono', ui-monospace, Menlo, Monaco, Consolas, monospace;`

### 3.2 Typographic Hierarchy
| Style Level | Font Family | Size | Weight | Line Height | Tracking | Application |
|---|---|---|---|---|---|---|
| **Display Hero** | Display | `clamp(2.4rem, 4.4vw, 3.8rem)` | 600 | 1.06 | `-0.035em` | Landing headline |
| **Title 1 (Player)**| Display | `clamp(1.8rem, 3.2vw, 2.75rem)`| 600 | 1.10 | `-0.025em` | Book title in Full Player |
| **Title 2 (Shelf)** | Display | `1.35rem (21.6px)` | 600 | 1.18 | `-0.02em` | Section titles ("Picked for You") |
| **Title 3 (Card)**  | Display | `1.15rem (18.4px)` | 600 | 1.20 | `-0.015em`| Audiobook title on cards |
| **Body Standard**   | Body | `0.94rem (15px)` | 400 | 1.60 | `-0.01em` | Book summaries, landing copy |
| **Body Medium**     | Body | `0.94rem (15px)` | 500 | 1.50 | `-0.01em` | Button text, table cells |
| **Author Subtitle** | Body | `0.84rem (13.5px)` | 500 | 1.40 | `0` | Card author bylines |
| **Timecode / Tabular**| Mono | `0.78rem (12.5px)` | 500 | 1.20 | `0.02em` | Scrubber times (`tabular-nums`) |
| **Kicker / Eyebrow**| Body | `0.70rem (11.2px)` | 700 | 1.10 | `0.12em` | Uppercase category tags |

---

## 4. Spacing Scale (4pt / 8pt Discipline)

| Token | Value | Pixel Representation | Canonical Application |
|---|---|---|---|
| `--space-1` | `0.25rem` | 4px | Internal badge padding, micro gaps. |
| `--space-2` | `0.50rem` | 8px | Button icon gaps, tag cluster spacing. |
| `--space-3` | `0.75rem` | 12px | List item internal padding, small card gap. |
| `--space-4` | `1.00rem` | 16px | Standard card content padding, grid gaps. |
| `--space-5` | `1.25rem` | 20px | Topbar padding, player transport gap. |
| `--space-6` | `1.50rem` | 24px | Section padding, container horizontal margin. |
| `--space-8` | `2.00rem` | 32px | Card grid row gaps, hero spacing. |
| `--space-12`| `3.00rem` | 48px | Major view section separation. |

---

## 5. Border Radius System (Apple Squircle Aesthetics)

Apple interfaces utilize squircle curvature for organic, friendly hardware feel:

| Token | Value | Application |
|---|---|---|
| `--radius-sm` | `6px` | Source type badges, small chips, tooltip bubbles. |
| `--radius-md` | `10px` | Chapter list items, search input fields, mini-player artwork. |
| `--radius-card` | `14px` | Audiobook catalog cards, resume hero artwork. |
| `--radius-panel`| `18px` | Full player transport deck, chapter container panel. |
| `--radius-sheet`| `24px` | Topbar floating shell, mini-player dock, profile modal sheet. |
| `--radius-pill` | `999px` | Buttons, filter category pills, offline status tags, scrubber thumb. |

---

## 6. Elevation & Light Shadows

In light theme, shadows must never be harsh, black, or blurry blobs. They are constructed as multi-layered, low-opacity ambient light occlusions:

```css
/* Subtle Card Resting State */
--shadow-subtle: 0 2px 8px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);

/* Elevated Interactive Card */
--shadow-card: 0 6px 20px rgba(0, 0, 0, 0.05), 0 1px 4px rgba(0, 0, 0, 0.02);

/* Prominent Floating Panel / Modal */
--shadow-elevated: 0 12px 32px rgba(0, 0, 0, 0.08), 0 2px 6px rgba(0, 0, 0, 0.03);

/* Floating Mini-Player Dock / Bottom Sheet */
--shadow-sheet: 0 16px 44px rgba(0, 0, 0, 0.10), 0 4px 12px rgba(0, 0, 0, 0.04);

/* Keyboard Focus Ring */
--shadow-focus: 0 0 0 3px rgba(198, 78, 0, 0.28);
```

---

## 7. Frosted Glass (Materiality Discipline)

Frosted glass (`backdrop-filter`) is a signature Apple material, but it must be used with **strict architectural restraint**:

### Allowed Glass Surfaces:
1. **Floating App Topbar:** `background: rgba(255, 255, 255, 0.78); backdrop-filter: blur(20px) saturate(180%);`
2. **Floating Mini-Player Dock:** `background: rgba(255, 255, 255, 0.82); backdrop-filter: blur(24px) saturate(190%);`
3. **Modal & Sidebar Backdrop:** `background: rgba(245, 245, 247, 0.75); backdrop-filter: blur(16px);`

### Prohibited Glass Surfaces (Anti-Patterns):
* ❌ **Audiobook Cards:** Must be solid `#FFFFFF` to ensure high contrast against book covers.
* ❌ **Chapter List Items:** Must be solid `#F2F2F7` or `#FFFFFF` to prevent text shimmering during scrolling.
* ❌ **Global View Body:** Must be solid `--color-canvas` (`#F5F5F7`).

### Progressive Enhancement Fallback:
```css
@supports not (backdrop-filter: blur(20px)) {
    .app-topbar,
    .player-bar.mini-dock {
        background: #FFFFFF;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
    }
}
```

---

## 8. Motion & Micro-Interactions

* **Transition Speed Tokens:**
  * `--transition-fast`: `150ms cubic-bezier(0.2, 0, 0, 1)` (Hover, focus, button press)
  * `--transition-base`: `240ms cubic-bezier(0.2, 0, 0, 1)` (Card elevate, tab switch, filter toggle)
  * `--transition-smooth`: `350ms cubic-bezier(0.4, 0, 0.2, 1)` (Modal drawer expand, player view change)
* **Press Scale Feedback:** `transform: scale(0.97)` on `:active` for buttons, pills, and transport controls.
* **Prefers Reduced Motion Contract:**
```css
@media (prefers-reduced-motion: reduce) {
    *, ::before, ::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }
}
```

---

## 9. Design Source-of-Truth Hierarchy

To guarantee architectural consistency across generative AI canvases and production code, all design and implementation artifacts adhere to a strict source-of-truth hierarchy:

```text
PRODUCT REQUIREMENTS (PRD)
        ↓
DESIGN PRINCIPLES (Redesign Brief)
        ↓
.stitch/DESIGN.md (Canonical Visual Language)
        ↓
.stitch/SITE.md (Canonical Product Context & Sitemap)
        ↓
COMPONENT SPEC (Reusable Component Library)
        ↓
SCREEN SPECS (Information Architecture)
        ↓
STITCH VISUAL DESIGN (Generative Exploration)
        ↓
SELECTED VISUAL REFERENCE (Approved Screens)
        ↓
ANTIGRAVITY IMPLEMENTATION (Codebase Styling)
        ↓
VISUAL QA (Playwright Regression Checks)
```

> [!IMPORTANT]
> **Functional Invariant Rule:**
> Existing functional and runtime contracts (DOM IDs, 12 test suites, OPFS storage, guest progress isolation, Media Session API) override visual design whenever there is an apparent conflict. Visual styling adapts to functional contracts—never the reverse.

