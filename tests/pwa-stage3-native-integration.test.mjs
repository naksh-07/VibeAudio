import test, { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
    validateImportableAudioFile,
    OFFLINE_STATES
} from '../frontend/src/js/offline-shelf.js';
import {
    isFileHandlingSupported,
    isWebShareSupported,
    isBadgingSupported,
    isLaunchHandlerSupported,
    shareAudiobook,
    updateAppBadge,
    clearAppBadge
} from '../frontend/src/js/pwa.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');
const frontendDir = path.resolve(rootDir, 'frontend');

describe('PWA Native Stage 3: OS File, Share, Launch & Native Experience Invariants', () => {

    describe('Phase 3A/3C/3D/3F: Web App Manifest Native Declarations', () => {
        const manifestPath = path.join(frontendDir, 'app.webmanifest');
        assert.ok(fs.existsSync(manifestPath), 'app.webmanifest must exist');
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

        it('should declare file_handlers for .m4b and .mp3 audiobook files', () => {
            assert.ok(Array.isArray(manifest.file_handlers), 'Manifest must declare file_handlers array');
            assert.ok(manifest.file_handlers.length > 0, 'file_handlers must not be empty');

            const handler = manifest.file_handlers[0];
            assert.equal(handler.action, './src/pages/app.html#offline', 'File handler action must target offline shelf');
            assert.ok(handler.accept, 'File handler must specify accept object');

            const acceptMap = handler.accept;
            assert.ok(acceptMap['audio/mp4']?.includes('.m4b') || acceptMap['audio/x-m4b']?.includes('.m4b'), 'Must accept .m4b files');
            assert.ok(acceptMap['audio/mpeg']?.includes('.mp3'), 'Must accept .mp3 files');
            assert.equal(handler.launch_type, 'single-client', 'Must use single-client launch_type');
        });

        it('should declare Web Share Target configuration', () => {
            assert.ok(manifest.share_target, 'Manifest must declare share_target');
            assert.equal(manifest.share_target.action, './src/pages/app.html', 'Share target action must route to app shell');
            assert.equal(manifest.share_target.method, 'GET', 'Share target method should be GET for safe handling');
            assert.ok(manifest.share_target.params, 'Share target must define param mappings');
            assert.equal(manifest.share_target.params.title, 'title');
            assert.equal(manifest.share_target.params.text, 'text');
            assert.equal(manifest.share_target.params.url, 'url');
        });

        it('should declare launch_handler with focus-existing navigation capture', () => {
            assert.ok(manifest.launch_handler, 'Manifest must declare launch_handler');
            const clientMode = manifest.launch_handler.client_mode;
            assert.ok(Array.isArray(clientMode), 'client_mode must be an array');
            assert.ok(clientMode.includes('focus-existing'), 'launch_handler must include focus-existing');
        });
    });

    describe('Phase 3B/3C: File Validation & Import Pipeline Invariants', () => {
        it('should accept valid .m4b and .mp3 files', () => {
            const validM4b = { name: 'Great_Gatsby.m4b', size: 45_000_000, type: 'audio/mp4' };
            const validMp3 = { name: 'Pride_and_Prejudice.mp3', size: 30_000_000, type: 'audio/mpeg' };

            const resM4b = validateImportableAudioFile(validM4b);
            assert.equal(resM4b.valid, true);
            assert.equal(resM4b.extension, '.m4b');

            const resMp3 = validateImportableAudioFile(validMp3);
            assert.equal(resMp3.valid, true);
            assert.equal(resMp3.extension, '.mp3');
        });

        it('should reject unsupported file extensions and types gracefully', () => {
            const exeFile = { name: 'virus.exe', size: 1024, type: 'application/x-msdownload' };
            const pdfFile = { name: 'book.pdf', size: 2048, type: 'application/pdf' };
            const txtFile = { name: 'notes.txt', size: 500, type: 'text/plain' };

            assert.equal(validateImportableAudioFile(exeFile).valid, false);
            assert.equal(validateImportableAudioFile(pdfFile).valid, false);
            assert.equal(validateImportableAudioFile(txtFile).valid, false);
        });

        it('should reject empty files and oversized files', () => {
            const emptyFile = { name: 'empty.mp3', size: 0, type: 'audio/mpeg' };
            const oversizedFile = { name: 'huge.m4b', size: 3 * 1024 * 1024 * 1024, type: 'audio/mp4' }; // 3 GB

            const emptyRes = validateImportableAudioFile(emptyFile);
            assert.equal(emptyRes.valid, false);
            assert.ok(emptyRes.error.toLowerCase().includes('empty'));

            const overRes = validateImportableAudioFile(oversizedFile);
            assert.equal(overRes.valid, false);
            assert.ok(overRes.error.includes('2 GB'));
        });
    });

    describe('Phase 3C/3J/3O: Local Storage Integrity & Deterministic Deduplication Contract', () => {
        class MockOfflineStorageSimulator {
            constructor() {
                this.books = new Map();
                this.chapters = new Map();
                this.userId = 'guest';
            }

            bookKey(bookId) {
                return `${this.userId}::${bookId}::hi`;
            }

            chapterKey(bookId, chapterIndex = 0) {
                return `${this.bookKey(bookId)}::${chapterIndex}`;
            }

            importFile(file, options = {}) {
                const validation = validateImportableAudioFile(file);
                if (!validation.valid) {
                    return { success: false, error: validation.error };
                }

                const cleanTitle = String(file.name || 'Local Audiobook')
                    .replace(/\.(m4b|mp3)$/i, '')
                    .replace(/[-_]+/g, ' ')
                    .trim();

                const safeSlug = cleanTitle.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'audiobook';
                const bookId = `local_${safeSlug}`;
                const bKey = this.bookKey(bookId);
                const cKey = this.chapterKey(bookId, 0);
                const now = new Date().toISOString();

                const bookRecord = {
                    id: bKey,
                    userId: this.userId,
                    bookId,
                    title: cleanTitle,
                    author: options.author || 'Local File',
                    totalChapters: 1,
                    isImported: true,
                    updatedAt: now
                };
                this.books.set(bKey, bookRecord);

                const existingChapter = this.chapters.get(cKey);
                const chapterRecord = {
                    ...existingChapter,
                    id: cKey,
                    userId: this.userId,
                    bookId,
                    lang: 'hi',
                    title: cleanTitle,
                    chapterIndex: 0,
                    status: OFFLINE_STATES.downloaded,
                    storageType: 'indexeddb_blob',
                    sizeBytes: file.size,
                    progressBytes: file.size,
                    progressPercent: 100,
                    sourceFingerprint: `local:${file.name}:${file.size}`,
                    lastTouchedAt: now
                };
                this.chapters.set(cKey, chapterRecord);

                return {
                    success: true,
                    bookId,
                    book: bookRecord,
                    record: chapterRecord
                };
            }
        }

        it('should store imported file in standard offline storage contract with status downloaded', () => {
            const storage = new MockOfflineStorageSimulator();
            const file = { name: 'Sherlock_Holmes.mp3', size: 15_000_000, type: 'audio/mpeg' };

            const result = storage.importFile(file);
            assert.equal(result.success, true);
            assert.equal(result.bookId, 'local_sherlock-holmes');
            assert.equal(result.book.title, 'Sherlock Holmes');
            assert.equal(result.record.status, OFFLINE_STATES.downloaded);
            assert.equal(result.record.progressPercent, 100);
            assert.equal(storage.books.size, 1);
            assert.equal(storage.chapters.size, 1);
        });

        it('should safely deduplicate identical re-imports without creating orphan books', () => {
            const storage = new MockOfflineStorageSimulator();
            const file = { name: 'Sherlock_Holmes.mp3', size: 15_000_000, type: 'audio/mpeg' };

            const firstResult = storage.importFile(file);
            const secondResult = storage.importFile(file);

            assert.equal(firstResult.bookId, secondResult.bookId);
            assert.equal(storage.books.size, 1, 'Books map must have exactly 1 record');
            assert.equal(storage.chapters.size, 1, 'Chapters map must have exactly 1 record');
        });
    });

    describe('Phase 3D/3P: Share Target & URL Security Validation', () => {
        function parseShareTargetInput(urlString, origin = 'https://vibeaudio.app') {
            const url = new URL(urlString, origin);
            const params = url.searchParams;

            const targetBookId = params.get('book');
            const targetUrl = params.get('url');
            const targetTitle = params.get('title');
            const targetText = params.get('text');

            let resolvedBookId = targetBookId;

            if (!resolvedBookId && targetUrl) {
                try {
                    // Security check: validate scheme
                    const parsedTarget = new URL(targetUrl, origin);
                    if (!['http:', 'https:'].includes(parsedTarget.protocol)) {
                        return { safe: false, reason: 'Invalid URL scheme' };
                    }
                    if (parsedTarget.searchParams.has('book')) {
                        resolvedBookId = parsedTarget.searchParams.get('book');
                    } else if (parsedTarget.hash.includes('book=')) {
                        const hashParams = new URLSearchParams(parsedTarget.hash.split('?')[1] || parsedTarget.hash.replace(/^#/, ''));
                        resolvedBookId = hashParams.get('book');
                    }
                } catch (_) {
                    return { safe: false, reason: 'Malformed URL' };
                }
            }

            return {
                safe: true,
                resolvedBookId: resolvedBookId || null,
                searchQuery: (targetTitle || targetText || '').trim() || null
            };
        }

        it('should resolve shared VibeAudio deep links to bookId', () => {
            const input1 = parseShareTargetInput('https://vibeaudio.app/src/pages/app.html?book=42');
            assert.equal(input1.safe, true);
            assert.equal(input1.resolvedBookId, '42');

            const input2 = parseShareTargetInput('https://vibeaudio.app/src/pages/app.html?url=https%3A%2F%2Fvibeaudio.app%2Fsrc%2Fpages%2Fapp.html%23player%3Fbook%3D7');
            assert.equal(input2.safe, true);
            assert.equal(input2.resolvedBookId, '7');
        });

        it('should resolve shared text or title as search query', () => {
            const input = parseShareTargetInput('https://vibeaudio.app/src/pages/app.html?title=Dune&text=Great%20sci-fi');
            assert.equal(input.safe, true);
            assert.equal(input.searchQuery, 'Dune');
        });

        it('should reject unsafe URL schemes like javascript: or data:', () => {
            const dangerous1 = parseShareTargetInput('https://vibeaudio.app/src/pages/app.html?url=javascript%3Aalert(1)');
            assert.equal(dangerous1.safe, false);

            const dangerous2 = parseShareTargetInput('https://vibeaudio.app/src/pages/app.html?url=data%3Atext%2Fhtml%2Cevil');
            assert.equal(dangerous2.safe, false);
        });
    });

    describe('Phase 3E: Web Share & Clipboard Fallback Invariants', () => {
        let originalNavigator;

        beforeEach(() => {
            originalNavigator = globalThis.navigator;
        });

        it('should utilize navigator.share when available', async () => {
            let sharedData = null;
            globalThis.navigator = {
                share: async (data) => {
                    sharedData = data;
                    return true;
                }
            };

            assert.equal(isWebShareSupported(), true);
            const result = await shareAudiobook({
                title: 'The Hobbit',
                author: 'J.R.R. Tolkien',
                bookId: 'hobbit-1',
                url: 'https://vibeaudio.app/#player?book=hobbit-1'
            });

            assert.equal(result.shared, true);
            assert.equal(result.method, 'navigator.share');
            assert.equal(sharedData?.title, 'The Hobbit');
            assert.ok(sharedData?.text.includes('J.R.R. Tolkien'));
        });

        it('should fall back to clipboard copy when navigator.share is unsupported', async () => {
            let copiedText = '';
            globalThis.navigator = {
                clipboard: {
                    writeText: async (text) => {
                        copiedText = text;
                        return true;
                    }
                }
            };

            assert.equal(isWebShareSupported(), false);
            const result = await shareAudiobook({
                title: '1984',
                author: 'George Orwell',
                bookId: '1984',
                url: 'https://vibeaudio.app/#player?book=1984'
            });

            assert.equal(result.shared, true);
            assert.equal(result.method, 'clipboard');
            assert.equal(copiedText, 'https://vibeaudio.app/#player?book=1984');
        });

        it('should cleanly handle share sheet abort without error', async () => {
            globalThis.navigator = {
                share: async () => {
                    const err = new Error('Share canceled');
                    err.name = 'AbortError';
                    throw err;
                }
            };

            const result = await shareAudiobook({ title: 'Test' });
            assert.equal(result.shared, false);
            assert.equal(result.aborted, true);
        });
    });

    describe('Phase 3G: Actionable App Badging Contract', () => {
        it('should update badge count when active downloads are pending', async () => {
            let badgeSet = null;
            globalThis.navigator = {
                setAppBadge: async (count) => { badgeSet = count; },
                clearAppBadge: async () => { badgeSet = 0; }
            };

            assert.equal(isBadgingSupported(), true);

            await updateAppBadge(3);
            assert.equal(badgeSet, 3);

            await updateAppBadge(0);
            assert.equal(badgeSet, 0);

            await clearAppBadge();
            assert.equal(badgeSet, 0);
        });

        it('should handle unsupported badge environments without throwing', async () => {
            globalThis.navigator = {};
            assert.equal(isBadgingSupported(), false);

            const res1 = await updateAppBadge(2);
            assert.equal(res1, false);

            const res2 = await clearAppBadge();
            assert.equal(res2, false);
        });
    });

    describe('Phase 3H/3I: Capability Detection Matrix & Progressive Enhancement', () => {
        it('should expose all capability query functions cleanly', () => {
            assert.equal(typeof isFileHandlingSupported, 'function');
            assert.equal(typeof isWebShareSupported, 'function');
            assert.equal(typeof isBadgingSupported, 'function');
            assert.equal(typeof isLaunchHandlerSupported, 'function');
        });
    });
});
