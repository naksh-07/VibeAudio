# VibeAudio Active Context

## Project Status & Architecture
- **Application**: Offline-first, guest-first Progressive Web App (PWA) audiobook sanctuary.
- **Current Branch**: `antivibe`
- **Frontend Stack**: Native ES Modules, Service Worker precache (40 shell assets), OPFS & IndexedDB private device storage.
- **Backend Stack**: AWS DynamoDB sync workers and serverless endpoints.
- **Brand System**: Dark Obsidian theme, custom 66-icon SVG sprite (`frontend/src/icons/icons.svg`).

## Active Invariants & Quality Gates
- `npm test`: Node.js native test runner (`node --test tests/`). Current: 129 tests passing.
- `npm run test:all`: Unit tests + Phase 1 reliability invariants (6/6) + Phase 2 PWA invariants (7/7).
- Fail-Closed Gate: Zero conflict markers, strict pass required before conclusion.

## Recent Engineering Changes
- Fixed `getTimeStamp` in `frontend/src/js/ui-formatters.js` to correctly parse numeric epoch timestamps.
- Hardened `formatTime` in `frontend/src/js/ui-player-helpers.js` to prevent negative and non-finite duration drift.
- Added comprehensive regression test suite `tests/ui-formatters.test.mjs`.

## Governance
- Operating under AntiOS 3.0 governance with external experience storage in `Os-Collection`.
