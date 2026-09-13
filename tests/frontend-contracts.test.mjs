import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { APP_CONFIG, STORAGE_KEYS, SYNC_STATES, CATALOG_URL } from '../frontend/src/js/config.js';
import { OFFLINE_STATES } from '../frontend/src/js/offline-shelf.js';
import {
    getProgressPercent,
    getProgressTimestampValue,
    getProgressTimestamp,
    isChapterFinishedProgress,
    isBookFinishedProgress,
    compareProgressFreshness,
    compareProgressByRecency,
    normalizeProgressEntry
} from '../frontend/src/js/progress-model.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

const appHtmlPath = path.resolve(rootDir, 'frontend/src/pages/app.html');
const uiPlayerMainPath = path.resolve(rootDir, 'frontend/src/js/ui-player-main.js');
const playerPath = path.resolve(rootDir, 'frontend/src/js/player.js');

describe('W1-D: Frontend Contracts — DOM & Accessibility', () => {
    let appHtml = '';

    test('Load app.html successfully', () => {
        appHtml = fs.readFileSync(appHtmlPath, 'utf8');
        assert.ok(appHtml.length > 0, 'app.html should not be empty');
    });

    test('Transport controls declare non-empty aria-label attributes', () => {
        const transportIds = [
            'speed-btn',
            'seek-back-btn',
            'play-btn',
            'seek-fwd-btn',
            'sleep-timer-btn'
        ];

        for (const id of transportIds) {
            const regex = new RegExp(`id="${id}"[^>]*aria-label="([^"]+)"`, 'i');
            const match = appHtml.match(regex);
            assert.ok(match, `Element with id="${id}" and aria-label should exist in app.html`);
            assert.ok(match[1].trim().length > 0, `aria-label for #${id} should not be empty`);
        }
    });

    test('Mini-player transport controls declare non-empty aria-label attributes', () => {
        const miniTransportIds = [
            'mini-seek-back-btn',
            'mini-play-btn',
            'mini-seek-fwd-btn'
        ];

        for (const id of miniTransportIds) {
            const regex = new RegExp(`id="${id}"[^>]*aria-label="([^"]+)"`, 'i');
            const match = appHtml.match(regex);
            assert.ok(match, `Mini element #${id} with aria-label should exist in app.html`);
            assert.ok(match[1].trim().length > 0, `aria-label for #${id} should not be empty`);
        }
    });

    test('Mini-player and full-player containers declare expected semantics', () => {
        assert.ok(appHtml.includes('id="mini-player"'), 'mini-player container (#mini-player) should exist');
        assert.ok(appHtml.includes('class="player-transport-deck"'), 'full-player transport deck should exist');
        
        // Mini player accessibility semantics
        const miniMatch = appHtml.match(/id="mini-player"[^>]*role="region"[^>]*aria-label="([^"]+)"/i);
        assert.ok(miniMatch, '#mini-player should have role="region" and an aria-label');
        assert.ok(miniMatch[1].trim().length > 0, '#mini-player aria-label should not be empty');
    });

    test('Navigation bar declares expected data-nav-view destinations', () => {
        const expectedViews = ['home', 'library', 'offline'];
        for (const view of expectedViews) {
            const viewPattern = new RegExp(`data-nav-view="${view}"`, 'i');
            assert.ok(viewPattern.test(appHtml), `Navigation view destination "${view}" should exist in app.html`);
        }
    });

    test('App navigation declares switchView actions for core routes', () => {
        const requiredRoutes = ['home', 'library', 'offline'];
        for (const route of requiredRoutes) {
            assert.ok(
                appHtml.includes(`window.app.switchView('${route}')`),
                `app.html should declare switchView handler for route '${route}'`
            );
        }
    });
});

describe('W1-D: Frontend Contracts — Player Presets & Invariants', () => {
    let uiPlayerMainCode = '';
    let playerCode = '';

    test('Load player source files successfully', () => {
        uiPlayerMainCode = fs.readFileSync(uiPlayerMainPath, 'utf8');
        playerCode = fs.readFileSync(playerPath, 'utf8');
        assert.ok(uiPlayerMainCode.length > 0, 'ui-player-main.js should not be empty');
        assert.ok(playerCode.length > 0, 'player.js should not be empty');
    });

    test('Playback speed presets stay within safe audio boundaries (0.75x to 2.0x)', () => {
        const speedMatch = uiPlayerMainCode.match(/const speeds\s*=\s*\[([^\]]+)\];/);
        assert.ok(speedMatch, 'Speed presets array (const speeds = [...]) should exist in ui-player-main.js');

        const speedValues = speedMatch[1].split(',').map(s => Number(s.trim()));
        assert.ok(speedValues.length >= 4, 'Should declare at least 4 speed preset options');
        assert.ok(speedValues.includes(1), 'Speed presets must include baseline 1.0x');

        for (const speed of speedValues) {
            assert.ok(!Number.isNaN(speed), `Speed preset value ${speed} must be a valid number`);
            assert.ok(speed >= 0.75, `Speed preset ${speed}x should be >= 0.75x`);
            assert.ok(speed <= 2.0, `Speed preset ${speed}x should be <= 2.0x`);
        }
    });

    test('Sleep timer popover menu declares valid preset durations', () => {
        const matches = [...uiPlayerMainCode.matchAll(/data-sleep-mins="(\d+)"/g)];
        assert.ok(matches.length >= 4, 'Sleep timer should declare at least 4 duration presets');

        const durations = matches.map(m => Number(m[1]));
        const requiredPresets = [0, 15, 30, 45, 60];

        for (const preset of requiredPresets) {
            assert.ok(durations.includes(preset), `Sleep timer presets must include ${preset} minutes`);
        }

        for (const min of durations) {
            assert.ok(min >= 0 && min <= 120, `Sleep duration ${min}m should be between 0 and 120 minutes`);
        }
    });

    test('Player module exports setSleepTimer and clearSleepTimer lifecycle functions', () => {
        assert.ok(
            playerCode.includes('export function setSleepTimer('),
            'player.js must export setSleepTimer'
        );
        assert.ok(
            playerCode.includes('export function clearSleepTimer('),
            'player.js must export clearSleepTimer'
        );
    });
});

describe('W1-D: Frontend Contracts — Configuration Contracts', () => {
    test('APP_CONFIG defines valid application identity and base URLs', () => {
        assert.equal(APP_CONFIG.appName, 'VibeAudio', 'Application name should be VibeAudio');
        assert.equal(APP_CONFIG.catalogBaseUrl, 'https://vibeaudio-db.pages.dev');
        assert.ok(APP_CONFIG.catalogBaseUrl.startsWith('https://'), 'Catalog URL must use secure HTTPS');
    });

    test('APP_CONFIG defines secure Lambda endpoints', () => {
        const requiredEndpoints = ['progressUrl', 'getProgressUrl', 'syncUserUrl'];
        for (const endpoint of requiredEndpoints) {
            const url = APP_CONFIG[endpoint];
            assert.ok(typeof url === 'string', `${endpoint} should be defined as a string`);
            assert.ok(url.startsWith('https://'), `${endpoint} must use secure HTTPS`);
            assert.ok(url.includes('.lambda-url.'), `${endpoint} must route to AWS Lambda URL`);
        }
    });

    test('STORAGE_KEYS follow strict namespace convention (vibe_*)', () => {
        const keyEntries = Object.entries(STORAGE_KEYS);
        assert.ok(keyEntries.length >= 8, 'STORAGE_KEYS should declare core storage keys');

        for (const [name, key] of keyEntries) {
            assert.ok(typeof key === 'string', `STORAGE_KEYS.${name} must be a string`);
            assert.ok(
                key.startsWith('vibe_'),
                `STORAGE_KEYS.${name} ("${key}") must start with namespace prefix "vibe_"`
            );
        }
    });

    test('SYNC_STATES declares standard synchronization lifecycle states', () => {
        assert.equal(SYNC_STATES.synced, 'synced');
        assert.equal(SYNC_STATES.pending, 'pending');
        assert.equal(SYNC_STATES.offline, 'offline');
    });

    test('CATALOG_URL is properly formatted from catalogBaseUrl', () => {
        assert.equal(CATALOG_URL, 'https://vibeaudio-db.pages.dev/catalog.json');
    });
});

describe('W1-D: Frontend Contracts — Storage & Offline State Constants', () => {
    test('OFFLINE_STATES declares complete download state machine', () => {
        const expectedStates = [
            'notDownloaded',
            'queued',
            'downloading',
            'downloaded',
            'failed'
        ];

        for (const state of expectedStates) {
            assert.ok(state in OFFLINE_STATES, `OFFLINE_STATES must define "${state}"`);
            assert.ok(
                typeof OFFLINE_STATES[state] === 'string' && OFFLINE_STATES[state].length > 0,
                `OFFLINE_STATES.${state} must be a non-empty string`
            );
        }

        // Verify values are distinct
        const values = Object.values(OFFLINE_STATES);
        const uniqueValues = new Set(values);
        assert.equal(values.length, uniqueValues.size, 'All OFFLINE_STATES values must be unique');
    });
});

describe('W1-D: Frontend Contracts — Progress Model Invariants', () => {
    describe('getProgressPercent', () => {
        test('calculates accurate percentages and clamps bounds [0, 100]', () => {
            assert.equal(getProgressPercent(null), 0, 'null progress should return 0');
            assert.equal(getProgressPercent(undefined), 0, 'undefined progress should return 0');
            assert.equal(getProgressPercent({ currentTime: 0, totalDuration: 100 }), 0);
            assert.equal(getProgressPercent({ currentTime: 50, totalDuration: 100 }), 50);
            assert.equal(getProgressPercent({ currentTime: 100, totalDuration: 100 }), 100);
            assert.equal(getProgressPercent({ currentTime: 150, totalDuration: 100 }), 100, 'Exceeding duration should clamp to 100');
            assert.equal(getProgressPercent({ currentTime: -20, totalDuration: 100 }), 0, 'Negative currentTime should clamp to 0');
        });

        test('handles zero or missing totalDuration safely without dividing by zero', () => {
            assert.equal(getProgressPercent({ currentTime: 0, totalDuration: 0 }), 0);
            assert.equal(getProgressPercent({ currentTime: 10, totalDuration: 0 }), 1, 'Positive currentTime with 0 duration returns 1%');
            assert.equal(getProgressPercent({ currentTime: 0, totalDuration: -50 }), 0);
        });
    });

    describe('isChapterFinishedProgress', () => {
        test('uses CHAPTER_COMPLETE_RATIO (98%) threshold correctly', () => {
            assert.equal(isChapterFinishedProgress(null), false);
            assert.equal(isChapterFinishedProgress({ currentTime: 50, totalDuration: 100 }), false);
            assert.equal(isChapterFinishedProgress({ currentTime: 97, totalDuration: 100 }), false);
            assert.equal(isChapterFinishedProgress({ currentTime: 98, totalDuration: 100 }), true);
            assert.equal(isChapterFinishedProgress({ currentTime: 99, totalDuration: 100 }), true);
            assert.equal(isChapterFinishedProgress({ currentTime: 100, totalDuration: 100 }), true);
            assert.equal(isChapterFinishedProgress({ currentTime: 50, totalDuration: 0 }), false);
        });
    });

    describe('isBookFinishedProgress', () => {
        test('reads boolean flags bookFinished or isFinished', () => {
            assert.equal(isBookFinishedProgress(null), false);
            assert.equal(isBookFinishedProgress({ bookFinished: true }), true);
            assert.equal(isBookFinishedProgress({ bookFinished: false }), false);
            assert.equal(isBookFinishedProgress({ isFinished: true }), true);
            assert.equal(isBookFinishedProgress({ isFinished: false }), false);
            assert.equal(isBookFinishedProgress({}), false);
        });
    });

    describe('normalizeProgressEntry', () => {
        test('normalizes valid progress payload and sanitizes fields', () => {
            const raw = {
                bookId: ' book-123 ',
                chapterIndex: '3',
                currentTime: '45.8',
                totalDuration: '180.2',
                totalChapters: '12'
            };

            const normalized = normalizeProgressEntry(raw);
            assert.ok(normalized, 'Should produce normalized entry');
            assert.equal(normalized.bookId, 'book-123', 'Should trim bookId whitespace');
            assert.equal(normalized.chapterIndex, 3, 'Should parse chapterIndex as integer');
            assert.equal(normalized.currentTime, 45.8, 'Should parse currentTime as float');
            assert.equal(normalized.totalDuration, 180.2, 'Should parse totalDuration as float');
            assert.equal(normalized.totalChapters, 12, 'Should parse totalChapters as integer');
        });

        test('returns null when bookId is missing or empty', () => {
            assert.equal(normalizeProgressEntry(null), null);
            assert.equal(normalizeProgressEntry({ bookId: '' }), null);
            assert.equal(normalizeProgressEntry({ bookId: '   ' }), null);
        });

        test('applies fallback values when entry fields are absent', () => {
            const fallback = {
                bookId: 'fallback-book',
                chapterIndex: 0,
                currentTime: 10
            };
            const normalized = normalizeProgressEntry({}, fallback);
            assert.ok(normalized);
            assert.equal(normalized.bookId, 'fallback-book');
            assert.equal(normalized.chapterIndex, 0);
            assert.equal(normalized.currentTime, 10);
        });
    });

    describe('compareProgressByRecency and compareProgressFreshness', () => {
        test('sorts entries descending by recency timestamp', () => {
            const older = {
                bookId: 'book-1',
                lastInteractionAt: '2026-09-01T10:00:00Z',
                chapterIndex: 1,
                currentTime: 20
            };
            const newer = {
                bookId: 'book-2',
                lastInteractionAt: '2026-09-10T10:00:00Z',
                chapterIndex: 1,
                currentTime: 20
            };

            // compareProgressByRecency: negative if left is newer (comes first in sort)
            assert.ok(compareProgressByRecency(newer, older) < 0, 'Newer entry should sort before older entry');
            assert.ok(compareProgressByRecency(older, newer) > 0, 'Older entry should sort after newer entry');

            const list = [older, newer];
            list.sort(compareProgressByRecency);
            assert.equal(list[0].bookId, 'book-2', 'List should have newer book first');
            assert.equal(list[1].bookId, 'book-1', 'List should have older book second');
        });

        test('falls back to chapterIndex and currentTime when timestamps are equal', () => {
            const entryA = { bookId: 'b', updatedAt: 1000, chapterIndex: 2, currentTime: 50 };
            const entryB = { bookId: 'b', updatedAt: 1000, chapterIndex: 1, currentTime: 50 };
            const entryC = { bookId: 'b', updatedAt: 1000, chapterIndex: 2, currentTime: 100 };

            // compareProgressFreshness: positive if left is fresher
            assert.ok(compareProgressFreshness(entryA, entryB) > 0, 'Higher chapterIndex is fresher');
            assert.ok(compareProgressFreshness(entryC, entryA) > 0, 'Higher currentTime is fresher');
        });
    });
});
