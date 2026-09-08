# VibeAudio Active Context

## Project Status & Architecture
- **Application**: Offline-first, guest-first Progressive Web App (PWA) audiobook sanctuary.
- **Current Branch**: `antivibe`
- **Frontend Stack**: Native ES Modules, Service Worker precache (40 shell assets), OPFS & IndexedDB private device storage.
- **Backend Stack**: AWS DynamoDB sync workers and serverless endpoints.
- **Theme System**: Dual Sanctuary — Nocturnal Dark Obsidian & Warm Parchment Daylight with dynamic chameleon cover extraction.
- **Icon System**: Custom 68-icon SVG sprite (`frontend/src/icons/icons.svg`) with `icon-sun` and `icon-moon`.

## Active Invariants & Quality Gates
- `npm test`: Node.js native test runner (`node --test tests/`). Current: 143 tests passing (14 suites).
- `npm run test:all`: Unit tests + Phase 1 reliability invariants (6/6) + Phase 2 PWA invariants (7/7).
- Fail-Closed Gate: Zero conflict markers, strict pass required before conclusion.

## Recent Engineering Changes
- Performed production visual and interaction audit of Light Theme (Daylight) and Dark Obsidian sanctuary.
- Fixed 9 audit defects: cover badge contrast in light mode, streak popup background and button contrast, Clerk sign-in form token adaptability, vocal boost and language toggle button styling, saved moments bookmarks UI layout, out-of-palette hex codes in callbacks, invalid `@media` selector list syntax, fail-closed zero-FOUC head scripts, universal button `:disabled` styles, and discovery card mobile grid overflow.
- All 143 unit tests passing across 14 test suites; Phase 1 (6/6) and Phase 2 (7/7) invariant checks pass. Precache shell verified at 40 assets.

## Governance
- Operating under AntiOS 3.0 governance with external experience storage in `Os-Collection`.


