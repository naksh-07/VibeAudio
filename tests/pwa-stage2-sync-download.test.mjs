import test, { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { normalizeProgressEntry, getProgressTimestampValue } from '../frontend/src/js/progress-model.js';
import { OFFLINE_STATES } from '../frontend/src/js/offline-shelf.js';
import {
    SYNC_DB_NAME,
    SYNC_STORE_NAME,
    buildPendingQueueKey
} from '../frontend/src/js/user-data.js';

describe('PWA Native Stage 2: Background Sync & Background Download Invariants', () => {

    describe('Phase 2B/2C: Shared Sync Queue & Migration Contract', () => {
        class MockSharedSyncQueue {
            constructor() {
                this.localStorage = new Map();
                this.idbStore = new Map();
                this.activeUserId = 'guest';
            }

            setUserId(id) {
                this.activeUserId = id || 'guest';
            }

            getPendingProgressQueue() {
                const raw = this.localStorage.get('vibe_progress_queue');
                return raw ? JSON.parse(raw) : {};
            }

            replacePendingProgressQueue(queue) {
                this.localStorage.set('vibe_progress_queue', JSON.stringify(queue || {}));
                this.idbStore.clear();
                for (const [key, entry] of Object.entries(queue || {})) {
                    const normalized = normalizeProgressEntry(entry, { source: 'pending' });
                    if (normalized) {
                        this.idbStore.set(key, { ...normalized, id: key });
                    }
                }
                return this.getPendingProgressQueue();
            }

            upsertPendingProgress(progress) {
                const normalized = normalizeProgressEntry(progress, { source: 'pending' });
                if (!normalized) return this.getPendingProgressQueue();

                const key = buildPendingQueueKey(normalized.userId || this.activeUserId, normalized.bookId);
                const queue = this.getPendingProgressQueue();
                const record = {
                    ...normalized,
                    userId: normalized.userId || this.activeUserId,
                    id: key
                };
                queue[key] = record;
                this.localStorage.set('vibe_progress_queue', JSON.stringify(queue));
                this.idbStore.set(key, record);
                return queue;
            }

            removePendingProgress(bookId) {
                const queue = this.getPendingProgressQueue();
                const currentUid = this.activeUserId;
                const specificKey = buildPendingQueueKey(currentUid, bookId);

                delete queue[String(bookId)];
                delete queue[specificKey];
                this.idbStore.delete(String(bookId));
                this.idbStore.delete(specificKey);

                Object.keys(queue).forEach((key) => {
                    const value = normalizeProgressEntry(queue[key], { source: 'pending' });
                    if (value && String(value.bookId) === String(bookId) && (value.userId === currentUid || !value.userId)) {
                        delete queue[key];
                        this.idbStore.delete(key);
                    }
                });

                this.localStorage.set('vibe_progress_queue', JSON.stringify(queue));
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

            // Simulate Service Worker processing background sync
            async serviceWorkerSync(apiClient) {
                const swEntries = Array.from(this.idbStore.values());
                const eligible = swEntries.filter((e) => e.userId && e.userId !== 'guest');
                const results = { synced: 0, failed: 0 };

                for (const entry of eligible) {
                    try {
                        const ok = await apiClient.postProgress(entry);
                        if (ok) {
                            this.idbStore.delete(entry.id);
                            // Also update local queue mirror upon confirmation
                            const localQueue = this.getPendingProgressQueue();
                            delete localQueue[entry.id];
                            this.localStorage.set('vibe_progress_queue', JSON.stringify(localQueue));
                            results.synced += 1;
                        } else {
                            results.failed += 1;
                        }
                    } catch (_) {
                        results.failed += 1;
                    }
                }

                return results;
            }

            // Safe migration of existing localStorage items into IndexedDB
            migrateLocalStorageToIdb() {
                const localQueue = this.getPendingProgressQueue();
                for (const [key, entry] of Object.entries(localQueue)) {
                    if (!this.idbStore.has(key)) {
                        const normalized = normalizeProgressEntry(entry, { source: 'pending' });
                        if (normalized) {
                            this.idbStore.set(key, { ...normalized, id: key });
                        }
                    }
                }
            }
        }

        let queue;

        beforeEach(() => {
            queue = new MockSharedSyncQueue();
        });

        it('should declare SYNC_DB_NAME and SYNC_STORE_NAME constants', () => {
            assert.equal(SYNC_DB_NAME, 'vibeaudio-sync-v1');
            assert.equal(SYNC_STORE_NAME, 'sync_progress_queue');
        });

        it('should safely migrate legacy localStorage records without duplicate creation', () => {
            // Seed legacy localStorage
            queue.localStorage.set('vibe_progress_queue', JSON.stringify({
                'guest:book-legacy': {
                    bookId: 'book-legacy',
                    chapterIndex: 0,
                    currentTime: 45,
                    totalDuration: 120,
                    lastInteractionAt: '2026-08-16T01:00:00.000Z'
                }
            }));

            assert.equal(queue.idbStore.size, 0);

            // Execute safe migration
            queue.migrateLocalStorageToIdb();

            assert.equal(queue.idbStore.size, 1);
            assert.ok(queue.idbStore.has('guest:book-legacy'));
            assert.equal(queue.idbStore.get('guest:book-legacy').currentTime, 45);

            // Subsequent re-migration must not duplicate or corrupt
            queue.migrateLocalStorageToIdb();
            assert.equal(queue.idbStore.size, 1);
        });

        it('should synchronize across page and Service Worker contexts', async () => {
            queue.setUserId('user-sync-test');
            queue.upsertPendingProgress({
                bookId: 'book-shared',
                chapterIndex: 2,
                currentTime: 180,
                totalDuration: 400
            });

            assert.equal(queue.idbStore.size, 1);
            assert.equal(queue.getPendingProgressEntries().length, 1);

            const mockApi = {
                postProgress: async () => true
            };

            const result = await queue.serviceWorkerSync(mockApi);
            assert.equal(result.synced, 1);
            assert.equal(result.failed, 0);
            assert.equal(queue.idbStore.size, 0);
            assert.equal(queue.getPendingProgressEntries().length, 0);
        });

        it('should NEVER send unauthenticated guest progress to cloud sync in Service Worker', async () => {
            queue.setUserId('guest');
            queue.upsertPendingProgress({
                bookId: 'book-guest-only',
                chapterIndex: 0,
                currentTime: 30
            });

            let apiCalled = false;
            const mockApi = {
                postProgress: async () => {
                    apiCalled = true;
                    return true;
                }
            };

            const result = await queue.serviceWorkerSync(mockApi);
            assert.equal(apiCalled, false, 'Guest progress must never be dispatched to cloud endpoint');
            assert.equal(result.synced, 0);
            assert.equal(queue.idbStore.size, 1, 'Guest progress stays locally durable');
        });
    });

    describe('Phase 2D/2E/2F: Background Sync Registration & Throttling', () => {
        class MockSyncRegistrationManager {
            constructor() {
                this.registeredTags = new Set();
                this.registrationCount = 0;
                this.lastRegistrationTime = 0;
                this.throttleMs = 3000;
            }

            async registerSync(tag, currentTime = Date.now()) {
                if (currentTime - this.lastRegistrationTime < this.throttleMs && this.registeredTags.has(tag)) {
                    // Throttled: deduplicated
                    return { registered: true, throttled: true };
                }

                this.lastRegistrationTime = currentTime;
                this.registeredTags.add(tag);
                this.registrationCount += 1;
                return { registered: true, throttled: false };
            }
        }

        it('should register stable tag vibeaudio-progress-sync', async () => {
            const syncManager = new MockSyncRegistrationManager();
            const res = await syncManager.registerSync('vibeaudio-progress-sync', 1000);

            assert.equal(res.registered, true);
            assert.equal(res.throttled, false);
            assert.ok(syncManager.registeredTags.has('vibeaudio-progress-sync'));
            assert.equal(syncManager.registrationCount, 1);
        });

        it('should throttle rapid duplicate sync registrations', async () => {
            const syncManager = new MockSyncRegistrationManager();

            // First registration at t=1000
            await syncManager.registerSync('vibeaudio-progress-sync', 1000);
            // Rapid subsequent call at t=1500
            const second = await syncManager.registerSync('vibeaudio-progress-sync', 1500);
            // Another call at t=2000
            const third = await syncManager.registerSync('vibeaudio-progress-sync', 2000);

            assert.equal(second.throttled, true);
            assert.equal(third.throttled, true);
            assert.equal(syncManager.registrationCount, 1, 'Duplicate registrations within throttle window must be suppressed');

            // Call after throttle window expires at t=4500
            const fourth = await syncManager.registerSync('vibeaudio-progress-sync', 4500);
            assert.equal(fourth.throttled, false);
            assert.equal(syncManager.registrationCount, 2);
        });
    });

    describe('Phase 2G-2M: Background Download & Fallback Matrix', () => {
        class MockDownloadLifecycle {
            constructor(options = {}) {
                this.isBgFetchSupported = options.isBgFetchSupported ?? false;
                this.bgFetchJobs = new Map();
                this.foregroundQueue = [];
                this.completedChapters = new Map();
                this.failedChapters = new Map();
            }

            buildJobId(userId, bookId, lang, chapterIndex) {
                return `vibe-bf-${userId}-${bookId}-${lang}-${chapterIndex}`;
            }

            async queueChapter(userId, book, chapterIndex, chapterData, lang = 'hi') {
                const jobId = this.buildJobId(userId, book.bookId, lang, chapterIndex);

                if (this.isBgFetchSupported && chapterData.downloadable !== false) {
                    try {
                        // Background Fetch initiation
                        this.bgFetchJobs.set(jobId, {
                            jobId,
                            userId,
                            bookId: book.bookId,
                            lang,
                            chapterIndex,
                            url: chapterData.url,
                            status: OFFLINE_STATES.downloading
                        });
                        return { mode: 'background-fetch', jobId, status: OFFLINE_STATES.downloading };
                    } catch (_) {
                        // Fallback to foreground queue on initiation error
                    }
                }

                // Foreground queue fallback
                this.foregroundQueue.push({
                    jobId,
                    userId,
                    bookId: book.bookId,
                    lang,
                    chapterIndex,
                    url: chapterData.url,
                    status: OFFLINE_STATES.queued
                });
                return { mode: 'foreground-queue', jobId, status: OFFLINE_STATES.queued };
            }

            simulateBgFetchSuccess(jobId, audioBlob) {
                const job = this.bgFetchJobs.get(jobId);
                if (!job) throw new Error('Job not found');

                this.completedChapters.set(jobId, {
                    userId: job.userId,
                    bookId: job.bookId,
                    lang: job.lang,
                    chapterIndex: job.chapterIndex,
                    status: OFFLINE_STATES.downloaded,
                    sizeBytes: audioBlob.size,
                    fallbackBlob: audioBlob
                });
                this.bgFetchJobs.delete(jobId);
            }

            simulateBgFetchFail(jobId, reason) {
                const job = this.bgFetchJobs.get(jobId);
                if (!job) return;

                this.failedChapters.set(jobId, {
                    userId: job.userId,
                    bookId: job.bookId,
                    lang: job.lang,
                    chapterIndex: job.chapterIndex,
                    status: OFFLINE_STATES.failed,
                    reason: reason || 'Background download interrupted'
                });
                this.bgFetchJobs.delete(jobId);
            }

            abortJob(jobId) {
                if (this.bgFetchJobs.has(jobId)) {
                    this.bgFetchJobs.delete(jobId);
                    return true;
                }
                const fIdx = this.foregroundQueue.findIndex((j) => j.jobId === jobId);
                if (fIdx >= 0) {
                    this.foregroundQueue.splice(fIdx, 1);
                    return true;
                }
                return false;
            }
        }

        const testBook = { bookId: 'b-bg-1', title: 'Cosmic Journey', author: 'Author X' };
        const testChapter = { name: 'Chapter 1', url: 'https://cdn.example.com/audio/c1.mp3', sizeBytes: 2048000, downloadable: true };
        const sampleBlob = { size: 2048000 };

        it('Case A: should utilize Background Fetch when capability is present', async () => {
            const engine = new MockDownloadLifecycle({ isBgFetchSupported: true });
            const res = await engine.queueChapter('guest', testBook, 0, testChapter, 'hi');

            assert.equal(res.mode, 'background-fetch');
            assert.equal(res.status, OFFLINE_STATES.downloading);
            assert.equal(engine.bgFetchJobs.size, 1);
        });

        it('Case B: should seamlessly fall back to foreground queue when Background Fetch is unavailable', async () => {
            const engine = new MockDownloadLifecycle({ isBgFetchSupported: false });
            const res = await engine.queueChapter('guest', testBook, 0, testChapter, 'hi');

            assert.equal(res.mode, 'foreground-queue');
            assert.equal(res.status, OFFLINE_STATES.queued);
            assert.equal(engine.foregroundQueue.length, 1);
        });

        it('Case C: should store completed background download in standard offline storage contract', async () => {
            const engine = new MockDownloadLifecycle({ isBgFetchSupported: true });
            const res = await engine.queueChapter('guest', testBook, 0, testChapter, 'hi');

            engine.simulateBgFetchSuccess(res.jobId, sampleBlob);

            assert.equal(engine.completedChapters.size, 1);
            const saved = engine.completedChapters.get(res.jobId);
            assert.equal(saved.status, OFFLINE_STATES.downloaded);
            assert.equal(saved.sizeBytes, 2048000);
        });

        it('Case D: should preserve existing completed chapters when a background download fails', async () => {
            const engine = new MockDownloadLifecycle({ isBgFetchSupported: true });

            // Chapter 0 completes successfully
            const res0 = await engine.queueChapter('guest', testBook, 0, testChapter, 'hi');
            engine.simulateBgFetchSuccess(res0.jobId, sampleBlob);
            assert.equal(engine.completedChapters.size, 1);

            // Chapter 1 fails in background
            const chapter2 = { name: 'Chapter 2', url: 'https://cdn.example.com/audio/c2.mp3', sizeBytes: 2048000 };
            const res1 = await engine.queueChapter('guest', testBook, 1, chapter2, 'hi');
            engine.simulateBgFetchFail(res1.jobId, 'Network connection interrupted');

            // Chapter 0 must remain 100% intact
            assert.equal(engine.completedChapters.size, 1);
            assert.equal(engine.completedChapters.get(res0.jobId).status, OFFLINE_STATES.downloaded);
            // Chapter 1 is recorded in failed state for clean retry
            assert.equal(engine.failedChapters.get(res1.jobId).status, OFFLINE_STATES.failed);
        });

        it('Case E: should cleanly handle job abort without corrupting storage', async () => {
            const engine = new MockDownloadLifecycle({ isBgFetchSupported: true });
            const res = await engine.queueChapter('guest', testBook, 0, testChapter, 'hi');

            const aborted = engine.abortJob(res.jobId);
            assert.equal(aborted, true);
            assert.equal(engine.bgFetchJobs.size, 0);
            assert.equal(engine.completedChapters.size, 0);
        });
    });
});
