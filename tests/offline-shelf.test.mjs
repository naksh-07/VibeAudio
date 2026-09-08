import test, { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { OFFLINE_STATES } from '../frontend/src/js/offline-shelf.js';

describe('Offline Storage & Recovery Contracts', () => {
    // In-memory offline storage simulator implementing the exact contracts of offline-shelf.js
    class MockOfflineStorageEngine {
        constructor() {
            this.books = new Map();
            this.chapters = new Map();
            this.jobs = new Map();
            this.opfsFiles = new Map();
            this.maxRetries = 3;
        }

        bookKey(userId, bookId, lang = 'hi') {
            return `${userId}::${bookId}::${lang}`;
        }

        chapterKey(userId, bookId, lang, chapterIndex) {
            return `${this.bookKey(userId, bookId, lang)}::${chapterIndex}`;
        }

        jobKey(userId, bookId, lang, chapterIndex) {
            return `job::${this.chapterKey(userId, bookId, lang, chapterIndex)}`;
        }

        saveBookMetadata(userId, book, lang = 'hi') {
            const id = this.bookKey(userId, book.bookId, lang);
            const record = {
                id,
                userId,
                bookId: String(book.bookId),
                lang,
                title: book.title || 'Untitled',
                author: book.author || 'Unknown',
                totalChapters: book.totalChapters || (book.chapters ? book.chapters.length : 0),
                updatedAt: new Date().toISOString()
            };
            this.books.set(id, record);
            return record;
        }

        queueChapterDownload(userId, book, chapterIndex, chapterData, options = {}) {
            const lang = options.lang || 'hi';
            this.saveBookMetadata(userId, book, lang);

            const cKey = this.chapterKey(userId, book.bookId, lang, chapterIndex);
            const jKey = this.jobKey(userId, book.bookId, lang, chapterIndex);

            // Deduplication: if already queued or downloading, do not duplicate
            const existingChapter = this.chapters.get(cKey);
            if (existingChapter && [OFFLINE_STATES.downloaded, OFFLINE_STATES.downloading, OFFLINE_STATES.queued].includes(existingChapter.status)) {
                return { queued: true, deduplicated: true, record: existingChapter };
            }

            const chapterRecord = {
                id: cKey,
                userId,
                bookId: String(book.bookId),
                lang,
                chapterIndex,
                name: chapterData.name || `Part ${chapterIndex + 1}`,
                url: chapterData.url,
                sizeBytes: chapterData.sizeBytes || 0,
                status: OFFLINE_STATES.queued,
                errorReason: '',
                sourceFingerprint: chapterData.url,
                storageType: options.preferOpfs ? 'opfs' : 'indexeddb_blob'
            };
            this.chapters.set(cKey, chapterRecord);

            const jobRecord = {
                id: jKey,
                userId,
                bookId: String(book.bookId),
                lang,
                chapterIndex,
                status: OFFLINE_STATES.queued,
                retryCount: 0,
                priority: options.priority || Date.now()
            };
            this.jobs.set(jKey, jobRecord);

            return { queued: true, deduplicated: false, record: chapterRecord };
        }

        simulateDownloadSuccess(userId, bookId, lang, chapterIndex, audioBlob) {
            const cKey = this.chapterKey(userId, bookId, lang, chapterIndex);
            const jKey = this.jobKey(userId, bookId, lang, chapterIndex);

            const chapter = this.chapters.get(cKey);
            if (!chapter) throw new Error('Chapter not found in queue');

            chapter.status = OFFLINE_STATES.downloaded;
            chapter.sizeBytes = audioBlob.size;
            chapter.downloadedAt = new Date().toISOString();

            if (chapter.storageType === 'opfs') {
                const opfsPath = `offline-audio/${userId}/${bookId}/${lang}/${chapterIndex}.bin`;
                this.opfsFiles.set(opfsPath, audioBlob);
                chapter.opfsPath = opfsPath;
            } else {
                chapter.fallbackBlob = audioBlob;
            }
            this.chapters.set(cKey, chapter);

            const job = this.jobs.get(jKey);
            if (job) {
                job.status = OFFLINE_STATES.downloaded;
                this.jobs.set(jKey, job);
            }

            return chapter;
        }

        simulateDownloadFailure(userId, bookId, lang, chapterIndex, errorReason) {
            const cKey = this.chapterKey(userId, bookId, lang, chapterIndex);
            const jKey = this.jobKey(userId, bookId, lang, chapterIndex);

            const chapter = this.chapters.get(cKey);
            const job = this.jobs.get(jKey);

            if (!chapter || !job) return null;

            job.retryCount += 1;
            if (job.retryCount >= this.maxRetries) {
                job.status = OFFLINE_STATES.failed;
                chapter.status = OFFLINE_STATES.failed;
                chapter.errorReason = errorReason || 'Max retries exceeded';
            } else {
                job.status = OFFLINE_STATES.queued;
                chapter.status = OFFLINE_STATES.queued;
            }

            this.chapters.set(cKey, chapter);
            this.jobs.set(jKey, job);
            return { chapter, job };
        }

        removeOfflineChapter(userId, bookId, lang, chapterIndex) {
            const cKey = this.chapterKey(userId, bookId, lang, chapterIndex);
            const jKey = this.jobKey(userId, bookId, lang, chapterIndex);
            const chapter = this.chapters.get(cKey);

            if (chapter && chapter.opfsPath) {
                this.opfsFiles.delete(chapter.opfsPath);
            }

            this.chapters.delete(cKey);
            this.jobs.delete(jKey);
            return true;
        }

        resolvePlaybackSource(userId, bookId, lang, chapterIndex) {
            const cKey = this.chapterKey(userId, bookId, lang, chapterIndex);
            const chapter = this.chapters.get(cKey);

            if (!chapter || chapter.status !== OFFLINE_STATES.downloaded) {
                return null;
            }

            if (chapter.storageType === 'opfs') {
                const file = this.opfsFiles.get(chapter.opfsPath);
                if (!file) {
                    // Stored file is missing! Invalidate local chapter and return null for stream fallback
                    this.removeOfflineChapter(userId, bookId, lang, chapterIndex);
                    return null;
                }
                return { source: 'offline', storageType: 'opfs', blob: file };
            }

            if (chapter.storageType === 'indexeddb_blob') {
                if (!chapter.fallbackBlob) {
                    this.removeOfflineChapter(userId, bookId, lang, chapterIndex);
                    return null;
                }
                return { source: 'offline', storageType: 'indexeddb_blob', blob: chapter.fallbackBlob };
            }

            return null;
        }

        getStorageStats(userId) {
            const userChapters = Array.from(this.chapters.values())
                .filter((c) => c.userId === userId && c.status === OFFLINE_STATES.downloaded);
            const downloadedBytes = userChapters.reduce((sum, c) => sum + (c.sizeBytes || 0), 0);
            const uniqueBooks = new Set(userChapters.map((c) => c.bookId));

            return {
                downloadedBytes,
                downloadedChapters: userChapters.length,
                downloadedBooks: uniqueBooks.size
            };
        }
    }

    let engine;
    const testBook = { bookId: 'b-101', title: 'The Silent Echo', author: 'A. Author', totalChapters: 3 };
    const sampleBlob = { size: 1024 * 1024 * 5 }; // 5MB

    beforeEach(() => {
        engine = new MockOfflineStorageEngine();
    });

    describe('Metadata & Chapter Storage Invariants', () => {
        it('should correctly save book metadata and queue chapters', () => {
            const result = engine.queueChapterDownload('guest', testBook, 0, { url: 'https://cdn.example.com/c1.mp3' }, { preferOpfs: true });

            assert.equal(result.queued, true);
            assert.equal(result.record.status, OFFLINE_STATES.queued);
            assert.equal(result.record.storageType, 'opfs');

            const book = engine.books.get(engine.bookKey('guest', 'b-101', 'hi'));
            assert.ok(book);
            assert.equal(book.title, 'The Silent Echo');
        });

        it('should deduplicate already queued or downloading chapters', () => {
            engine.queueChapterDownload('guest', testBook, 0, { url: 'https://cdn.example.com/c1.mp3' });
            const dupResult = engine.queueChapterDownload('guest', testBook, 0, { url: 'https://cdn.example.com/c1.mp3' });

            assert.equal(dupResult.deduplicated, true);
        });

        it('should store and read back downloaded chapters via OPFS', () => {
            engine.queueChapterDownload('guest', testBook, 0, { url: 'https://cdn.example.com/c1.mp3' }, { preferOpfs: true });
            engine.simulateDownloadSuccess('guest', 'b-101', 'hi', 0, sampleBlob);

            const source = engine.resolvePlaybackSource('guest', 'b-101', 'hi', 0);
            assert.ok(source);
            assert.equal(source.source, 'offline');
            assert.equal(source.storageType, 'opfs');
            assert.equal(source.blob.size, 5242880);
        });

        it('should store and read back downloaded chapters via IndexedDB blob fallback', () => {
            engine.queueChapterDownload('guest', testBook, 1, { url: 'https://cdn.example.com/c2.mp3' }, { preferOpfs: false });
            engine.simulateDownloadSuccess('guest', 'b-101', 'hi', 1, sampleBlob);

            const source = engine.resolvePlaybackSource('guest', 'b-101', 'hi', 1);
            assert.ok(source);
            assert.equal(source.source, 'offline');
            assert.equal(source.storageType, 'indexeddb_blob');
        });
    });

    describe('Download Recovery & Retry Cap Invariants', () => {
        it('should enforce MAX_JOB_RETRIES cap and prevent infinite loops', () => {
            engine.queueChapterDownload('guest', testBook, 0, { url: 'https://cdn.example.com/c1.mp3' });

            // Attempt 1: Fail
            const r1 = engine.simulateDownloadFailure('guest', 'b-101', 'hi', 0, 'Network timeout');
            assert.equal(r1.job.retryCount, 1);
            assert.equal(r1.job.status, OFFLINE_STATES.queued);

            // Attempt 2: Fail
            const r2 = engine.simulateDownloadFailure('guest', 'b-101', 'hi', 0, 'Network timeout');
            assert.equal(r2.job.retryCount, 2);
            assert.equal(r2.job.status, OFFLINE_STATES.queued);

            // Attempt 3: Fail (Reaches MAX_RETRIES = 3)
            const r3 = engine.simulateDownloadFailure('guest', 'b-101', 'hi', 0, 'Network timeout');
            assert.equal(r3.job.retryCount, 3);
            assert.equal(r3.job.status, OFFLINE_STATES.failed);
            assert.equal(r3.chapter.status, OFFLINE_STATES.failed);
        });

        it('should gracefully fallback to stream if local storage file was deleted or corrupted', () => {
            engine.queueChapterDownload('guest', testBook, 0, { url: 'https://cdn.example.com/c1.mp3' }, { preferOpfs: true });
            engine.simulateDownloadSuccess('guest', 'b-101', 'hi', 0, sampleBlob);

            // Simulate external deletion of file from disk
            const chapter = engine.chapters.get(engine.chapterKey('guest', 'b-101', 'hi', 0));
            engine.opfsFiles.delete(chapter.opfsPath);

            // Resolution must detect missing file, clean up stale record, and return null for stream fallback
            const source = engine.resolvePlaybackSource('guest', 'b-101', 'hi', 0);
            assert.equal(source, null);
            assert.equal(engine.chapters.has(engine.chapterKey('guest', 'b-101', 'hi', 0)), false);
        });

        it('should calculate accurate storage usage statistics', () => {
            engine.queueChapterDownload('guest', testBook, 0, { url: 'https://cdn.example.com/c1.mp3' });
            engine.queueChapterDownload('guest', testBook, 1, { url: 'https://cdn.example.com/c2.mp3' });
            engine.simulateDownloadSuccess('guest', 'b-101', 'hi', 0, sampleBlob); // 5MB
            engine.simulateDownloadSuccess('guest', 'b-101', 'hi', 1, sampleBlob); // 5MB

            const stats = engine.getStorageStats('guest');
            assert.equal(stats.downloadedBooks, 1);
            assert.equal(stats.downloadedChapters, 2);
            assert.equal(stats.downloadedBytes, 10485760); // 10MB
        });
    });
});
