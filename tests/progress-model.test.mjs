import test, { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
    getProgressPercent,
    getProgressTimestampValue,
    getProgressTimestamp,
    isChapterFinishedProgress,
    isBookFinishedProgress,
    compareProgressFreshness,
    compareProgressByRecency,
    normalizeProgressEntry,
    buildProgressStorageKey
} from '../frontend/src/js/progress-model.js';

describe('Progress Model & Normalization Contract Tests', () => {
    describe('normalizeProgressEntry()', () => {
        it('should correctly normalize a standard progress payload', () => {
            const entry = normalizeProgressEntry({
                bookId: 'book-001',
                chapterIndex: 3,
                currentTime: 120.4,
                totalDuration: 300,
                totalChapters: 8,
                lastInteractionAt: '2026-08-16T01:00:00.000Z'
            }, { source: 'local' });

            assert.ok(entry);
            assert.equal(entry.bookId, 'book-001');
            assert.equal(entry.chapterIndex, 3);
            assert.equal(entry.currentTime, 120.4);
            assert.equal(entry.totalDuration, 300);
            assert.equal(entry.totalChapters, 8);
            assert.equal(entry.source, 'local');
            assert.equal(entry.bookFinished, false);
            assert.equal(entry.currentChapterFinished, false);
        });

        it('should return null when bookId is missing or empty', () => {
            assert.equal(normalizeProgressEntry({ bookId: '' }), null);
            assert.equal(normalizeProgressEntry({ bookId: '   ' }), null);
            assert.equal(normalizeProgressEntry({}), null);
            assert.equal(normalizeProgressEntry(null), null);
            assert.equal(normalizeProgressEntry(undefined), null);
        });

        it('should apply fallback fields when primary entry is sparse', () => {
            const entry = normalizeProgressEntry({
                bookId: 'book-sparse'
            }, {
                chapterIndex: 2,
                currentTime: 50,
                totalDuration: 100,
                totalChapters: 4,
                source: 'fallback-source'
            });

            assert.ok(entry);
            assert.equal(entry.bookId, 'book-sparse');
            assert.equal(entry.chapterIndex, 2);
            assert.equal(entry.currentTime, 50);
            assert.equal(entry.totalDuration, 100);
            assert.equal(entry.totalChapters, 4);
            assert.equal(entry.source, 'fallback-source');
        });

        it('should sanitize negative and non-numeric values safely', () => {
            const entry = normalizeProgressEntry({
                bookId: 'book-invalid-nums',
                chapterIndex: -5,
                currentTime: -99,
                totalDuration: -500,
                totalChapters: 'invalid'
            });

            assert.ok(entry);
            assert.equal(entry.chapterIndex, 0);
            assert.equal(entry.currentTime, 0);
            assert.equal(entry.totalDuration, 0);
            assert.equal(entry.totalChapters, undefined);
        });

        it('should automatically infer bookFinished when on final chapter past threshold', () => {
            const entry = normalizeProgressEntry({
                bookId: 'book-fin',
                chapterIndex: 4,
                currentTime: 295,
                totalDuration: 300,
                totalChapters: 5
            });

            assert.ok(entry);
            assert.equal(entry.currentChapterFinished, true);
            assert.equal(entry.bookFinished, true);
        });

        it('should respect explicit bookFinished boolean flag', () => {
            const entryFalse = normalizeProgressEntry({
                bookId: 'book-flag',
                chapterIndex: 4,
                currentTime: 295,
                totalDuration: 300,
                totalChapters: 5,
                bookFinished: false
            });
            assert.equal(entryFalse.bookFinished, false);

            const entryTrue = normalizeProgressEntry({
                bookId: 'book-flag',
                chapterIndex: 0,
                currentTime: 10,
                totalDuration: 300,
                totalChapters: 5,
                bookFinished: true
            });
            assert.equal(entryTrue.bookFinished, true);
        });
    });

    describe('getProgressPercent()', () => {
        it('should return correct rounded percentage', () => {
            assert.equal(getProgressPercent({ currentTime: 50, totalDuration: 100 }), 50);
            assert.equal(getProgressPercent({ currentTime: 33.3, totalDuration: 100 }), 33);
            assert.equal(getProgressPercent({ currentTime: 99.9, totalDuration: 100 }), 100);
        });

        it('should clamp values between 0 and 100', () => {
            assert.equal(getProgressPercent({ currentTime: -20, totalDuration: 100 }), 0);
            assert.equal(getProgressPercent({ currentTime: 150, totalDuration: 100 }), 100);
        });

        it('should handle zero duration gracefully', () => {
            assert.equal(getProgressPercent(null), 0);
            assert.equal(getProgressPercent({ currentTime: 0, totalDuration: 0 }), 0);
            assert.equal(getProgressPercent({ currentTime: 10, totalDuration: 0 }), 1);
        });
    });

    describe('Freshness and Recency Comparisons', () => {
        it('should rank newer timestamp ahead of older timestamp', () => {
            const older = { lastInteractionAt: '2026-08-15T10:00:00.000Z' };
            const newer = { lastInteractionAt: '2026-08-16T10:00:00.000Z' };

            assert.ok(compareProgressFreshness(newer, older) > 0);
            assert.ok(compareProgressFreshness(older, newer) < 0);
            assert.ok(compareProgressByRecency(newer, older) < 0); // recency sort: newer first
        });

        it('should break ties with chapterIndex when timestamps are identical', () => {
            const entryCh1 = { lastInteractionAt: '2026-08-16T00:00:00.000Z', chapterIndex: 1, currentTime: 50 };
            const entryCh2 = { lastInteractionAt: '2026-08-16T00:00:00.000Z', chapterIndex: 2, currentTime: 10 };

            assert.ok(compareProgressFreshness(entryCh2, entryCh1) > 0);
        });

        it('should break ties with currentTime when timestamps and chapterIndex are identical', () => {
            const entryT10 = { lastInteractionAt: '2026-08-16T00:00:00.000Z', chapterIndex: 1, currentTime: 10 };
            const entryT50 = { lastInteractionAt: '2026-08-16T00:00:00.000Z', chapterIndex: 1, currentTime: 50 };

            assert.ok(compareProgressFreshness(entryT50, entryT10) > 0);
        });

        it('should return 0 when records are completely equal in progress and time', () => {
            const entryA = { lastInteractionAt: '2026-08-16T00:00:00.000Z', chapterIndex: 1, currentTime: 10 };
            const entryB = { lastInteractionAt: '2026-08-16T00:00:00.000Z', chapterIndex: 1, currentTime: 10 };

            assert.equal(compareProgressFreshness(entryA, entryB), 0);
        });

        it('should handle missing and malformed timestamp fields', () => {
            assert.equal(getProgressTimestampValue(null), 0);
            assert.equal(getProgressTimestampValue({ lastInteractionAt: 'not-a-date' }), 0);
            assert.equal(getProgressTimestamp(null), null);
            assert.equal(getProgressTimestamp({ updatedAt: '2026-08-16T00:00:00.000Z' }), '2026-08-16T00:00:00.000Z');
        });
    });

    describe('Chapter and Book Completion Checks', () => {
        it('should detect chapter finish at or above 98% duration', () => {
            assert.equal(isChapterFinishedProgress({ currentTime: 97, totalDuration: 100 }), false);
            assert.equal(isChapterFinishedProgress({ currentTime: 98, totalDuration: 100 }), true);
            assert.equal(isChapterFinishedProgress({ currentTime: 99.5, totalDuration: 100 }), true);
            assert.equal(isChapterFinishedProgress({ currentTime: 0, totalDuration: 0 }), false);
        });

        it('should check book finish flags accurately', () => {
            assert.equal(isBookFinishedProgress({ bookFinished: true }), true);
            assert.equal(isBookFinishedProgress({ isFinished: true }), true);
            assert.equal(isBookFinishedProgress({ bookFinished: false }), false);
            assert.equal(isBookFinishedProgress({ isFinished: false }), false);
            assert.equal(isBookFinishedProgress(null), false);
        });
    });

    describe('buildProgressStorageKey()', () => {
        it('should build user-scoped and global progress keys', () => {
            assert.equal(buildProgressStorageKey('book-100', 'user-42'), 'vibe_progress_user-42_book-100');
            assert.equal(buildProgressStorageKey('book-100', 'guest'), 'vibe_progress_guest_book-100');
            assert.equal(buildProgressStorageKey('book-100', ''), 'vibe_progress_book-100');
            assert.equal(buildProgressStorageKey('book-100', null), 'vibe_progress_book-100');
        });
    });
});
