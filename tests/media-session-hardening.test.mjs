import test, { describe, it } from 'node:test';
import assert from 'node:assert/strict';

describe('Media Session & OS Audio Native Hardening Invariants', () => {

    describe('Metadata Construction & Audiobook Formatting', () => {
        function buildMediaSessionArtwork(imageUrl, baseUrl = 'https://vibeaudio.app/') {
            let resolvedUrl = imageUrl || 'public/icons/logo.png';
            try {
                resolvedUrl = new URL(resolvedUrl, baseUrl).href;
            } catch (error) {
                try {
                    resolvedUrl = new URL('public/icons/logo.png', baseUrl).href;
                } catch (_) {
                    return [];
                }
            }

            return [
                { src: resolvedUrl, sizes: '96x96', type: 'image/png' },
                { src: resolvedUrl, sizes: '128x128', type: 'image/png' },
                { src: resolvedUrl, sizes: '192x192', type: 'image/png' },
                { src: resolvedUrl, sizes: '256x256', type: 'image/png' },
                { src: resolvedUrl, sizes: '384x384', type: 'image/png' },
                { src: resolvedUrl, sizes: '512x512', type: 'image/png' }
            ];
        }

        function formatChapterTitle(chapter, chapterIndex = 0) {
            if (!chapter) return `Chapter ${chapterIndex + 1}`;
            const rawName = String(chapter.name || '').trim();
            if (!rawName) return `Chapter ${chapterIndex + 1}`;
            return rawName;
        }

        it('should format chapter title without producing empty strings for plain chapter names', () => {
            assert.equal(formatChapterTitle({ name: 'Chapter 1' }, 0), 'Chapter 1');
            assert.equal(formatChapterTitle({ name: 'Chapter 1: The Beginning' }, 0), 'Chapter 1: The Beginning');
            assert.equal(formatChapterTitle({ name: '01 - Prologue' }, 0), '01 - Prologue');
            assert.equal(formatChapterTitle({ name: '   ' }, 2), 'Chapter 3');
            assert.equal(formatChapterTitle(null, 4), 'Chapter 5');
        });

        it('should structure audiobook metadata with distinct title, author/artist, and book album', () => {
            const book = {
                title: 'The Great Gatsby',
                author: 'F. Scott Fitzgerald',
                cover: 'https://example.com/gatsby.jpg'
            };
            const chapter = { name: 'Chapter 1: In my younger and more vulnerable years' };

            const title = formatChapterTitle(chapter, 0);
            const artist = book.author || 'Vibe Audio';
            const album = book.title;
            const artwork = buildMediaSessionArtwork(book.cover);

            assert.equal(title, 'Chapter 1: In my younger and more vulnerable years');
            assert.equal(artist, 'F. Scott Fitzgerald');
            assert.equal(album, 'The Great Gatsby');
            assert.equal(artwork.length, 6);
            assert.equal(artwork[0].sizes, '96x96');
            assert.equal(artwork[5].sizes, '512x512');
            assert.equal(artwork[0].src, 'https://example.com/gatsby.jpg');
        });

        it('should fall back safely when author or cover is missing', () => {
            const book = { title: 'Unknown Classic' };
            const chapter = { name: 'Introduction' };

            const artist = book.author || 'Vibe Audio';
            const album = book.title || 'VibeAudio Audiobook';
            const artwork = buildMediaSessionArtwork(book.cover, 'https://vibeaudio.app/');

            assert.equal(artist, 'Vibe Audio');
            assert.equal(album, 'Unknown Classic');
            assert.ok(artwork[0].src.includes('public/icons/logo.png'));
        });
    });

    describe('OS Native Transport Control Handlers & Seek Invariants', () => {
        class MockMediaSession {
            constructor() {
                this.metadata = null;
                this.playbackState = 'none';
                this.positionState = null;
                this.handlers = new Map();
            }

            setActionHandler(action, handler) {
                if (handler) {
                    this.handlers.set(action, handler);
                } else {
                    this.handlers.delete(action);
                }
            }

            setPositionState(state) {
                if (!state) {
                    this.positionState = null;
                    return;
                }
                const { duration, position, playbackRate } = state;
                if (!Number.isFinite(duration) || duration <= 0) {
                    throw new TypeError('duration must be a positive finite number');
                }
                if (!Number.isFinite(position) || position < 0 || position > duration) {
                    throw new TypeError('position must be between 0 and duration');
                }
                if (!Number.isFinite(playbackRate) || playbackRate <= 0) {
                    throw new TypeError('playbackRate must be a positive finite number');
                }
                this.positionState = { duration, position, playbackRate };
            }
        }

        it('should register all standard OS transport actions including seekto', () => {
            const mediaSession = new MockMediaSession();
            const registeredActions = [];

            const actionHandlers = [
                ['play', () => {}],
                ['pause', () => {}],
                ['stop', () => {}],
                ['previoustrack', () => {}],
                ['nexttrack', () => {}],
                ['seekbackward', () => {}],
                ['seekforward', () => {}],
                ['seekto', () => {}]
            ];

            for (const [action, handler] of actionHandlers) {
                mediaSession.setActionHandler(action, handler);
                registeredActions.push(action);
            }

            assert.equal(registeredActions.length, 8);
            assert.ok(mediaSession.handlers.has('play'));
            assert.ok(mediaSession.handlers.has('pause'));
            assert.ok(mediaSession.handlers.has('stop'));
            assert.ok(mediaSession.handlers.has('previoustrack'));
            assert.ok(mediaSession.handlers.has('nexttrack'));
            assert.ok(mediaSession.handlers.has('seekbackward'));
            assert.ok(mediaSession.handlers.has('seekforward'));
            assert.ok(mediaSession.handlers.has('seekto'));
        });

        it('should seek backward 15s by default or honor explicit seekOffset details', () => {
            let skippedDelta = 0;
            function skip(seconds) {
                skippedDelta = seconds;
            }

            function seekBackwardHandler(details) {
                const offset = (details && typeof details.seekOffset === 'number' && details.seekOffset > 0)
                    ? details.seekOffset
                    : 15;
                skip(-offset);
            }

            // Default OS seek backward trigger (no detail parameter)
            seekBackwardHandler();
            assert.equal(skippedDelta, -15);

            // Detailed OS seek backward trigger (e.g. 10s custom offset)
            seekBackwardHandler({ seekOffset: 10 });
            assert.equal(skippedDelta, -10);
        });

        it('should seek forward 30s by default or honor explicit seekOffset details', () => {
            let skippedDelta = 0;
            function skip(seconds) {
                skippedDelta = seconds;
            }

            function seekForwardHandler(details) {
                const offset = (details && typeof details.seekOffset === 'number' && details.seekOffset > 0)
                    ? details.seekOffset
                    : 30;
                skip(offset);
            }

            // Default OS seek forward trigger
            seekForwardHandler();
            assert.equal(skippedDelta, 30);

            // Detailed OS seek forward trigger
            seekForwardHandler({ seekOffset: 45 });
            assert.equal(skippedDelta, 45);
        });

        it('should handle seekto action with exact seconds and clamp to duration bounds', () => {
            let targetSeekTime = null;
            let targetFastSeek = false;

            const duration = 1200; // 20 minutes

            function seekToSeconds(seconds, fastSeek = false) {
                const safeTime = Math.max(0, Number(seconds) || 0);
                targetSeekTime = Math.min(duration, safeTime);
                targetFastSeek = Boolean(fastSeek);
            }

            function seekToHandler(details) {
                if (details && typeof details.seekTime === 'number') {
                    seekToSeconds(details.seekTime, Boolean(details.fastSeek));
                }
            }

            seekToHandler({ seekTime: 350.5, fastSeek: true });
            assert.equal(targetSeekTime, 350.5);
            assert.equal(targetFastSeek, true);

            // Clamp past end of audio
            seekToHandler({ seekTime: 9999 });
            assert.equal(targetSeekTime, 1200);

            // Negative seek clamped to 0
            seekToHandler({ seekTime: -50 });
            assert.equal(targetSeekTime, 0);
        });
    });

    describe('Position State Validation & Throttling', () => {
        it('should safely validate position state dictionary parameters', () => {
            function validateAndSetPosition(mediaSession, { currentTime, duration, playbackRate }) {
                if (
                    Number.isFinite(duration) &&
                    duration > 0 &&
                    Number.isFinite(currentTime) &&
                    currentTime >= 0 &&
                    Number.isFinite(playbackRate) &&
                    playbackRate > 0
                ) {
                    const safePosition = Math.min(currentTime, duration);
                    mediaSession.setPositionState({
                        duration,
                        playbackRate,
                        position: safePosition
                    });
                    return true;
                }
                return false;
            }

            const session = {
                state: null,
                setPositionState(s) { this.state = s; }
            };

            // Valid state
            const valid = validateAndSetPosition(session, { currentTime: 45, duration: 180, playbackRate: 1.25 });
            assert.equal(valid, true);
            assert.deepEqual(session.state, { duration: 180, position: 45, playbackRate: 1.25 });

            // Invalid duration (NaN / 0)
            const invalidDuration = validateAndSetPosition(session, { currentTime: 0, duration: 0, playbackRate: 1 });
            assert.equal(invalidDuration, false);

            // Invalid playbackRate (0 / negative)
            const invalidRate = validateAndSetPosition(session, { currentTime: 10, duration: 100, playbackRate: 0 });
            assert.equal(invalidRate, false);
        });

        it('should avoid redundant positionState updates when drift is negligible', () => {
            let callCount = 0;
            let lastState = { position: -1, duration: -1, playbackRate: -1 };

            function updatePositionThrottled(currentTime, duration, playbackRate, force = false) {
                if (!Number.isFinite(duration) || duration <= 0) return;
                const safePos = Math.min(currentTime, duration);

                if (
                    !force &&
                    Math.abs(lastState.position - safePos) < 0.75 &&
                    lastState.duration === duration &&
                    lastState.playbackRate === playbackRate
                ) {
                    return;
                }

                lastState = { position: safePos, duration, playbackRate };
                callCount++;
            }

            updatePositionThrottled(10.0, 300, 1.0);
            assert.equal(callCount, 1);

            // Minor 0.2s drift within 0.75s threshold -> skipped
            updatePositionThrottled(10.2, 300, 1.0);
            assert.equal(callCount, 1);

            // 1.0s drift -> processed
            updatePositionThrottled(11.2, 300, 1.0);
            assert.equal(callCount, 2);

            // Playback speed change -> processed immediately
            updatePositionThrottled(11.3, 300, 1.5);
            assert.equal(callCount, 3);
        });
    });

    describe('Progressive Enhancement & Graceful Degradation', () => {
        it('should function seamlessly without throwing when mediaSession is absent', () => {
            // Emulate environment without navigator.mediaSession
            const mockNavigator = {};

            function updateMediaSessionSafe() {
                if (!('mediaSession' in mockNavigator)) return false;
                mockNavigator.mediaSession.metadata = {};
                return true;
            }

            function setupMediaHandlersSafe() {
                if (!('mediaSession' in mockNavigator)) return false;
                mockNavigator.mediaSession.setActionHandler('play', () => {});
                return true;
            }

            assert.equal(updateMediaSessionSafe(), false);
            assert.equal(setupMediaHandlersSafe(), false);
        });

        it('should ignore unsupported individual action handlers gracefully', () => {
            const session = {
                setActionHandler(action) {
                    if (action === 'unsupportedaction') {
                        throw new TypeError(`Action ${action} is not supported`);
                    }
                }
            };

            let caughtErrors = 0;
            const actions = ['play', 'unsupportedaction', 'pause'];

            for (const action of actions) {
                try {
                    session.setActionHandler(action, () => {});
                } catch (error) {
                    caughtErrors++;
                }
            }

            assert.equal(caughtErrors, 1);
        });
    });

    describe('Chapter Transitions, Race Prevention & State Sync', () => {
        it('should maintain synchronized metadata during rapid chapter switching', async () => {
            let activeChapterMetadata = null;
            let currentLoadToken = 0;

            const chapters = [
                { name: 'Chapter 1: The Gathering' },
                { name: 'Chapter 2: The Journey' },
                { name: 'Chapter 3: The Sanctuary' }
            ];

            async function switchChapter(index, delayMs) {
                const token = ++currentLoadToken;
                await new Promise((resolve) => setTimeout(resolve, delayMs));
                if (token !== currentLoadToken) return;

                activeChapterMetadata = {
                    title: chapters[index].name,
                    token
                };
            }

            // Rapid switching: start 0 (slow), start 1 (medium), start 2 (fast)
            const p0 = switchChapter(0, 40);
            const p1 = switchChapter(1, 20);
            const p2 = switchChapter(2, 5);

            await Promise.all([p0, p1, p2]);

            assert.ok(activeChapterMetadata);
            assert.equal(activeChapterMetadata.title, 'Chapter 3: The Sanctuary');
            assert.equal(activeChapterMetadata.token, 3);
        });

        it('should update mediaSession playbackState to paused on chapter completion if no next chapter', () => {
            let playbackState = 'playing';

            function onAudioEnded(hasNextChapter) {
                if (hasNextChapter) {
                    // loads next chapter, remains playing
                    playbackState = 'playing';
                } else {
                    // final chapter ends
                    playbackState = 'paused';
                }
            }

            onAudioEnded(true);
            assert.equal(playbackState, 'playing');

            onAudioEnded(false);
            assert.equal(playbackState, 'paused');
        });
    });
});
