import test, { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { getTimeStamp, formatRelativeTime } from '../frontend/src/js/ui-formatters.js';

describe('UI Formatters Invariants', () => {
    describe('getTimeStamp', () => {
        it('should correctly parse numeric epoch timestamps', () => {
            const now = Date.now();
            assert.equal(getTimeStamp(now), now);
            assert.equal(getTimeStamp(1700000000000), 1700000000000);
        });

        it('should correctly parse Date objects', () => {
            const date = new Date('2026-09-08T10:00:00Z');
            assert.equal(getTimeStamp(date), date.getTime());
        });

        it('should correctly parse ISO date strings', () => {
            const iso = '2026-09-08T10:00:00Z';
            assert.equal(getTimeStamp(iso), Date.parse(iso));
        });

        it('should parse numeric string timestamps', () => {
            assert.equal(getTimeStamp('1700000000000'), 1700000000000);
        });

        it('should return 0 for falsy, negative, non-finite, or invalid inputs', () => {
            assert.equal(getTimeStamp(null), 0);
            assert.equal(getTimeStamp(undefined), 0);
            assert.equal(getTimeStamp(0), 0);
            assert.equal(getTimeStamp(-500), 0);
            assert.equal(getTimeStamp(NaN), 0);
            assert.equal(getTimeStamp('invalid-date-string'), 0);
            assert.equal(getTimeStamp({}), 0);
        });
    });

    describe('formatRelativeTime', () => {
        it('should return "just now" for timestamps less than 60 seconds old', () => {
            const now = Date.now();
            assert.equal(formatRelativeTime(now), 'just now');
            assert.equal(formatRelativeTime(now - 30 * 1000), 'just now');
        });

        it('should return "Xm ago" for timestamps between 1 and 59 minutes old', () => {
            const now = Date.now();
            assert.equal(formatRelativeTime(now - 5 * 60 * 1000), '5m ago');
            assert.equal(formatRelativeTime(now - 59 * 60 * 1000), '59m ago');
        });

        it('should return "Xh ago" for timestamps between 1 and 23 hours old', () => {
            const now = Date.now();
            assert.equal(formatRelativeTime(now - 2 * 60 * 60 * 1000), '2h ago');
            assert.equal(formatRelativeTime(now - 23 * 60 * 60 * 1000), '23h ago');
        });

        it('should return "Xd ago" for timestamps 24 hours or older', () => {
            const now = Date.now();
            assert.equal(formatRelativeTime(now - 48 * 60 * 60 * 1000), '2d ago');
            assert.equal(formatRelativeTime(now - 7 * 24 * 60 * 60 * 1000), '7d ago');
        });

        it('should return "recently" for invalid or missing timestamps', () => {
            assert.equal(formatRelativeTime(null), 'recently');
            assert.equal(formatRelativeTime(undefined), 'recently');
            assert.equal(formatRelativeTime('invalid'), 'recently');
        });
    });

    describe('formatTime (Player Duration & Position)', async () => {
        const { formatTime } = await import('../frontend/src/js/ui-player-helpers.js');

        it('should format seconds into mm:ss for durations under an hour', () => {
            assert.equal(formatTime(0), '00:00');
            assert.equal(formatTime(5), '0:05');
            assert.equal(formatTime(65), '1:05');
            assert.equal(formatTime(599), '9:59');
            assert.equal(formatTime(3599), '59:59');
        });

        it('should format seconds into h:mm:ss for durations of an hour or more', () => {
            assert.equal(formatTime(3600), '1:00:00');
            assert.equal(formatTime(3665), '1:01:05');
            assert.equal(formatTime(7325), '2:02:05');
        });

        it('should gracefully clamp negative, non-finite, or null values to 00:00', () => {
            assert.equal(formatTime(-1), '00:00');
            assert.equal(formatTime(-100), '00:00');
            assert.equal(formatTime(NaN), '00:00');
            assert.equal(formatTime(null), '00:00');
            assert.equal(formatTime(undefined), '00:00');
            assert.equal(formatTime('invalid'), '00:00');
        });
    });
});
