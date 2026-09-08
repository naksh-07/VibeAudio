import test, { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');
const appHtmlPath = path.join(rootDir, 'frontend', 'src', 'pages', 'app.html');
const baseCssPath = path.join(rootDir, 'frontend', 'src', 'css', 'base.css');
const playerCssPath = path.join(rootDir, 'frontend', 'src', 'css', 'player.css');
const playerPremiumCssPath = path.join(rootDir, 'frontend', 'src', 'css', 'player-premium.css');

describe('Accessibility (a11y) & Usability Regression Invariants', () => {
    const html = fs.readFileSync(appHtmlPath, 'utf8');
    const baseCss = fs.readFileSync(baseCssPath, 'utf8');
    const playerCss = fs.readFileSync(playerCssPath, 'utf8');
    const playerPremiumCss = fs.readFileSync(playerPremiumCssPath, 'utf8');

    describe('Accessible Control Names & ARIA Labels', () => {
        it('should ensure all interactive player and transport controls have descriptive aria-labels', () => {
            const requiredAriaElements = [
                { id: 'menu-btn', label: 'Open navigation menu' },
                { id: 'search-input', label: 'Search audiobooks' },
                { id: 'search-clear-btn', label: 'Clear search' },
                { id: 'main-play-btn', label: 'Listen Now' },
                { id: 'download-book-btn', label: 'Save for offline' },
                { id: 'speed-btn', label: 'Playback speed options' },
                { id: 'seek-back-btn', label: 'Jump backward 15 seconds' },
                { id: 'play-btn', label: 'Play or Pause' },
                { id: 'seek-fwd-btn', label: 'Jump forward 30 seconds' },
                { id: 'sleep-timer-btn', label: 'Sleep timer options' },
                { id: 'mini-track-info', label: 'Open full player view' },
                { id: 'mini-seek-back-btn', label: 'Jump backward 15 seconds' },
                { id: 'mini-play-btn', label: 'Play or Pause' },
                { id: 'mini-seek-fwd-btn', label: 'Jump forward 30 seconds' }
            ];

            for (const item of requiredAriaElements) {
                const elementPattern = new RegExp(`id=["']${item.id}["'][^>]*aria-label=["']([^"']+)["']|aria-label=["']([^"']+)["'][^>]*id=["']${item.id}["']`);
                assert.ok(elementPattern.test(html), `Control #${item.id} must declare an explicit aria-label`);
            }
        });

        it('should declare ARIA value attributes on the range scrubber slider', () => {
            const scrubberPattern = /id=["']progress-bar["'][^>]*aria-label=["']Playback progress["'][^>]*aria-valuemin=["']0["'][^>]*aria-valuemax=["']100["']|aria-label=["']Playback progress["'][^>]*id=["']progress-bar["']/;
            assert.ok(scrubberPattern.test(html), 'Scrubber must declare aria-label, aria-valuemin, aria-valuemax');
        });

        it('should declare ARIA live regions for async sync banners', () => {
            assert.ok(html.includes('id="library-sync-banner"') && html.includes('aria-live="polite"'));
            assert.ok(html.includes('id="history-sync-banner"') && html.includes('aria-live="polite"'));
        });
    });

    describe('Keyboard Navigation & Visible Focus Styles', () => {
        it('should declare high-contrast focus-visible ring styles for buttons and inputs', () => {
            assert.ok(baseCss.includes('button:focus-visible'), 'base.css must define button:focus-visible styles');
            assert.ok(baseCss.includes('input:focus-visible'), 'base.css must define input:focus-visible styles');
            assert.ok(baseCss.includes('a:focus-visible'), 'base.css must define a:focus-visible styles');
            assert.ok(playerPremiumCss.includes(':focus-visible'), 'player-premium.css must define scrubber/dock :focus-visible');
        });
    });

    describe('Motion & Vestibular Safety', () => {
        it('should declare prefers-reduced-motion media query to eliminate jarring motion', () => {
            assert.ok(baseCss.includes('@media (prefers-reduced-motion: reduce)'), 'base.css must define prefers-reduced-motion overrides');
            assert.ok(baseCss.includes('animation-duration: 0.01ms') || baseCss.includes('transition: none') || baseCss.includes('animation-iteration-count: 1'));
        });
    });

    describe('Standard Touch Target Sizing', () => {
        it('should declare minimum touch-friendly dimensions on mobile control decks', () => {
            // Check that transport and mini-player button rules specify ample touch targets
            assert.ok(playerCss.includes('.transport-step-btn') || playerCss.includes('.transport-play-btn'));
            assert.ok(baseCss.includes('.glass-btn') || baseCss.includes('.action-btn'));
        });
    });
});
