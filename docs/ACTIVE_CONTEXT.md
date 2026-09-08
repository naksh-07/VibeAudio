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
- Built Warm Parchment / Daylight theme counterpart to Obsidian Sanctuary with zero-FOUC boot and WCAG AAA/AA contrast.
- Added theme switching via topbar, mobile drawer nav, and Profile Appearance radio panel with persistent preference.
- Hardened dynamic chameleon cover palette generation to blend against parchment in daylight mode.
- Created `tests/theme-system.test.mjs` verifying tokens, contrast, contracts, and shell invariants.

## Governance
- Operating under AntiOS 3.0 governance with external experience storage in `Os-Collection`.

