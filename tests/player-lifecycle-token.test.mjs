import test, { describe, it } from 'node:test';
import assert from 'node:assert/strict';

describe('Player Lifecycle & Concurrency Invariants', () => {
    describe('Monotonic Load Token Concurrency', () => {
        it('should cancel late-resolving chapter loads when a newer load is issued', async () => {
            let currentLoadToken = 0;
            let resolvedChapter = null;
            let resolveLog = [];

            async function loadChapterAsync(chapterName, durationMs) {
                const thisToken = ++currentLoadToken;
                await new Promise((resolve) => setTimeout(resolve, durationMs));
                if (thisToken !== currentLoadToken) {
                    resolveLog.push(`cancelled:${chapterName}`);
                    return;
                }
                resolvedChapter = chapterName;
                resolveLog.push(`applied:${chapterName}`);
            }

            // Start Chapter 1 (slow, 60ms) and immediately start Chapter 2 (fast, 15ms)
            const p1 = loadChapterAsync('Chapter 1', 60);
            const p2 = loadChapterAsync('Chapter 2', 15);

            await Promise.all([p1, p2]);

            assert.equal(resolvedChapter, 'Chapter 2');
            assert.deepEqual(resolveLog, ['applied:Chapter 2', 'cancelled:Chapter 1']);
        });

        it('should handle rapid successive chapter navigation without race conditions', async () => {
            let currentLoadToken = 0;
            let activeState = null;

            async function rapidNavigate(chapterIndex, latencyMs) {
                const thisToken = ++currentLoadToken;
                await new Promise((resolve) => setTimeout(resolve, latencyMs));
                if (thisToken === currentLoadToken) {
                    activeState = { chapterIndex, token: thisToken };
                }
            }

            // Simulate user clicking next 5 times rapidly with varying network jitter
            const operations = [
                rapidNavigate(1, 50),
                rapidNavigate(2, 40),
                rapidNavigate(3, 30),
                rapidNavigate(4, 20),
                rapidNavigate(5, 10)
            ];

            await Promise.all(operations);

            assert.ok(activeState);
            assert.equal(activeState.chapterIndex, 5);
            assert.equal(activeState.token, 5);
        });

        it('should discard stale source switches when player source changes type', async () => {
            let currentLoadToken = 0;
            let currentActiveSource = null;

            async function resolveSource(sourceType, delayMs) {
                const thisToken = ++currentLoadToken;
                await new Promise((resolve) => setTimeout(resolve, delayMs));
                if (thisToken === currentLoadToken) {
                    currentActiveSource = sourceType;
                }
            }

            // Offline source starts resolving, user immediately switches to YouTube streaming
            const offlinePromise = resolveSource('offline:blob-1', 50);
            const streamPromise = resolveSource('stream:youtube-video', 10);

            await Promise.all([offlinePromise, streamPromise]);

            assert.equal(currentActiveSource, 'stream:youtube-video');
        });
    });

    describe('Sleep Timer State & Fadeout Lifecycle', () => {
        class MockSleepTimerController {
            constructor() {
                this.activeTimeout = null;
                this.activeFadeInterval = null;
                this.volume = 1.0;
                this.preFadeVolume = 1.0;
                this.isPaused = false;
                this.lifecycleLog = [];
            }

            clearTimer() {
                if (this.activeTimeout) {
                    clearTimeout(this.activeTimeout);
                    this.activeTimeout = null;
                    this.lifecycleLog.push('cleared_timeout');
                }
                if (this.activeFadeInterval) {
                    clearInterval(this.activeFadeInterval);
                    this.activeFadeInterval = null;
                    this.volume = this.preFadeVolume;
                    this.lifecycleLog.push('cleared_fade');
                }
            }

            setTimer(minutes, options = { fadeoutSeconds: 5 }) {
                this.clearTimer();
                if (minutes <= 0) return;

                this.preFadeVolume = this.volume;
                this.lifecycleLog.push(`scheduled:${minutes}m`);

                // For testing, convert minutes to simulated ms
                const totalMs = minutes; 
                this.activeTimeout = setTimeout(() => {
                    this.startFadeout(options.fadeoutSeconds);
                }, totalMs);
            }

            startFadeout(fadeSeconds) {
                this.lifecycleLog.push('start_fadeout');
                const steps = 5;
                let currentStep = steps;

                this.activeFadeInterval = setInterval(() => {
                    currentStep -= 1;
                    if (currentStep <= 0) {
                        clearInterval(this.activeFadeInterval);
                        this.activeFadeInterval = null;
                        this.isPaused = true;
                        this.volume = this.preFadeVolume; // restored for next play
                        this.lifecycleLog.push('paused_and_restored_volume');
                    } else {
                        this.volume = (currentStep / steps) * this.preFadeVolume;
                        this.lifecycleLog.push(`volume:${this.volume.toFixed(2)}`);
                    }
                }, 10);
            }
        }

        it('should clear existing timer when a new timer duration is selected', () => {
            const timer = new MockSleepTimerController();
            timer.setTimer(15);
            assert.ok(timer.activeTimeout !== null);

            timer.setTimer(30);
            assert.ok(timer.activeTimeout !== null);
            assert.ok(timer.lifecycleLog.includes('cleared_timeout'));
            assert.ok(timer.lifecycleLog.includes('scheduled:30m'));

            timer.clearTimer();
        });

        it('should cleanly turn timer off when set to 0', () => {
            const timer = new MockSleepTimerController();
            timer.setTimer(45);
            assert.ok(timer.activeTimeout !== null);

            timer.setTimer(0);
            assert.equal(timer.activeTimeout, null);
            assert.equal(timer.activeFadeInterval, null);
            assert.equal(timer.volume, 1.0);
        });

        it('should execute smooth fadeout, pause playback, and restore volume', async () => {
            const timer = new MockSleepTimerController();
            timer.setTimer(10); // 10ms

            await new Promise((resolve) => setTimeout(resolve, 100));

            assert.equal(timer.isPaused, true);
            assert.equal(timer.volume, 1.0, 'Volume must be restored to pre-fade level after pause');
            assert.ok(timer.lifecycleLog.includes('start_fadeout'));
            assert.ok(timer.lifecycleLog.includes('paused_and_restored_volume'));
        });
    });
});
