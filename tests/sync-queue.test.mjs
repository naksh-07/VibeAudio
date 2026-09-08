import test, { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { normalizeProgressEntry, getProgressTimestampValue } from '../frontend/src/js/progress-model.js';

describe('User Data & Sync Queue Invariants', () => {
    // Isolated in-memory Sync Queue Engine testing user-data.js contracts
    class MockSyncQueueEngine {
        constructor() {
            this.storage = new Map();
            this.activeUserId = 'guest';
        }

        setUserId(id) {
            this.activeUserId = id || 'guest';
        }

        buildQueueKey(userId, bookId) {
            const safeUserId = String(userId || this.activeUserId || 'guest').trim();
            return `${safeUserId}:${String(bookId || '').trim()}`;
        }

        getPendingProgressQueue() {
            const raw = this.storage.get('vibe_progress_queue');
            return raw ? JSON.parse(raw) : {};
        }

        replacePendingProgressQueue(queue) {
            this.storage.set('vibe_progress_queue', JSON.stringify(queue || {}));
            return this.getPendingProgressQueue();
        }

        upsertPendingProgress(progress) {
            const normalized = normalizeProgressEntry(progress, { source: 'pending' });
            if (!normalized) return this.getPendingProgressQueue();

            const queue = this.getPendingProgressQueue();
            const key = this.buildQueueKey(normalized.userId || this.activeUserId, normalized.bookId);
            queue[key] = {
                ...normalized,
                userId: normalized.userId || this.activeUserId
            };
            this.replacePendingProgressQueue(queue);
            return queue;
        }

        getPendingProgressEntries() {
            const queue = this.getPendingProgressQueue();
            return Object.values(queue)
                .map((entry) => normalizeProgressEntry(entry, { source: 'pending' }))
                .filter((entry) => !entry?.userId || entry.userId === this.activeUserId)
                .filter(Boolean)
                .sort((a, b) => getProgressTimestampValue(b) - getProgressTimestampValue(a));
        }

        removePendingProgress(bookId) {
            const queue = this.getPendingProgressQueue();
            const key = this.buildQueueKey(this.activeUserId, bookId);
            delete queue[key];
            delete queue[String(bookId)];
            this.replacePendingProgressQueue(queue);
            return queue;
        }

        async flushSyncQueue(apiClient) {
            const entries = this.getPendingProgressEntries();
            const results = { synced: 0, failed: 0 };

            for (const entry of entries) {
                try {
                    const success = await apiClient.saveProgress(entry);
                    if (success) {
                        this.removePendingProgress(entry.bookId);
                        results.synced += 1;
                    } else {
                        results.failed += 1;
                    }
                } catch (error) {
                    // Critical Invariant: On network failure, do NOT remove entry from queue
                    results.failed += 1;
                }
            }

            return results;
        }
    }

    let queueEngine;

    beforeEach(() => {
        queueEngine = new MockSyncQueueEngine();
    });

    describe('Pending Progress Enqueue & Deduplication', () => {
        it('should enqueue and normalize progress updates', () => {
            queueEngine.upsertPendingProgress({
                bookId: 'book-42',
                chapterIndex: 1,
                currentTime: 85.0,
                totalDuration: 200,
                lastInteractionAt: '2026-08-16T02:00:00.000Z'
            });

            const entries = queueEngine.getPendingProgressEntries();
            assert.equal(entries.length, 1);
            assert.equal(entries[0].bookId, 'book-42');
            assert.equal(entries[0].currentTime, 85.0);
        });

        it('should deduplicate multiple progress updates for the same book', () => {
            // First update
            queueEngine.upsertPendingProgress({
                bookId: 'book-42',
                chapterIndex: 1,
                currentTime: 85.0,
                totalDuration: 200,
                lastInteractionAt: '2026-08-16T02:00:00.000Z'
            });

            // Second update for same book
            queueEngine.upsertPendingProgress({
                bookId: 'book-42',
                chapterIndex: 1,
                currentTime: 140.0,
                totalDuration: 200,
                lastInteractionAt: '2026-08-16T02:05:00.000Z'
            });

            const entries = queueEngine.getPendingProgressEntries();
            assert.equal(entries.length, 1, 'Queue must contain exactly one consolidated record per book');
            assert.equal(entries[0].currentTime, 140.0);
            assert.equal(entries[0].lastInteractionAt, '2026-08-16T02:05:00.000Z');
        });

        it('should order pending items by timestamp recency', () => {
            queueEngine.upsertPendingProgress({
                bookId: 'book-older',
                chapterIndex: 0,
                currentTime: 10,
                lastInteractionAt: '2026-08-16T01:00:00.000Z'
            });

            queueEngine.upsertPendingProgress({
                bookId: 'book-newer',
                chapterIndex: 2,
                currentTime: 50,
                lastInteractionAt: '2026-08-16T03:00:00.000Z'
            });

            const entries = queueEngine.getPendingProgressEntries();
            assert.equal(entries.length, 2);
            assert.equal(entries[0].bookId, 'book-newer');
            assert.equal(entries[1].bookId, 'book-older');
        });
    });

    describe('Flush and Local Data Preservation Invariants', () => {
        it('should delete entry from pending queue only upon successful sync', async () => {
            queueEngine.upsertPendingProgress({
                bookId: 'book-sync-ok',
                chapterIndex: 1,
                currentTime: 20
            });

            const mockApi = {
                saveProgress: async () => true
            };

            const results = await queueEngine.flushSyncQueue(mockApi);
            assert.equal(results.synced, 1);
            assert.equal(results.failed, 0);
            assert.equal(queueEngine.getPendingProgressEntries().length, 0);
        });

        it('CRITICAL: should NEVER delete local progress if sync fails or throws', async () => {
            queueEngine.upsertPendingProgress({
                bookId: 'book-vital-progress',
                chapterIndex: 3,
                currentTime: 250,
                totalDuration: 300,
                lastInteractionAt: '2026-08-16T03:30:00.000Z'
            });

            const failingApi = {
                saveProgress: async () => {
                    throw new TypeError('Network connection interrupted');
                }
            };

            const results = await queueEngine.flushSyncQueue(failingApi);
            assert.equal(results.synced, 0);
            assert.equal(results.failed, 1);

            // Verify queue still safely holds user progress
            const preserved = queueEngine.getPendingProgressEntries();
            assert.equal(preserved.length, 1);
            assert.equal(preserved[0].bookId, 'book-vital-progress');
            assert.equal(preserved[0].currentTime, 250);
        });

        it('should isolate guest queue entries from authenticated user sessions', () => {
            // Guest progress
            queueEngine.setUserId('guest');
            queueEngine.upsertPendingProgress({ bookId: 'book-guest', currentTime: 10 });

            // User signs in as user-123
            queueEngine.setUserId('user-123');
            queueEngine.upsertPendingProgress({ bookId: 'book-auth', currentTime: 90 });

            // In user-123 context, only user-123 entry is listed
            const authEntries = queueEngine.getPendingProgressEntries();
            assert.equal(authEntries.length, 1);
            assert.equal(authEntries[0].bookId, 'book-auth');

            // Switch back to guest context
            queueEngine.setUserId('guest');
            const guestEntries = queueEngine.getPendingProgressEntries();
            assert.equal(guestEntries.length, 1);
            assert.equal(guestEntries[0].bookId, 'book-guest');
        });
    });
});
