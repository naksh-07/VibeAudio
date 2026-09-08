import test, { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { STORAGE_KEYS } from '../frontend/src/js/config.js';
import { buildTheme } from '../frontend/src/js/ui-player-helpers.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

const baseCssPath = path.join(rootDir, 'frontend', 'src', 'css', 'base.css');
const componentsCssPath = path.join(rootDir, 'frontend', 'src', 'css', 'components.css');
const playerCssPath = path.join(rootDir, 'frontend', 'src', 'css', 'player.css');
const appSectionsCssPath = path.join(rootDir, 'frontend', 'src', 'css', 'app-sections.css');
const appHtmlPath = path.join(rootDir, 'frontend', 'src', 'pages', 'app.html');
const indexHtmlPath = path.join(rootDir, 'frontend', 'index.html');
const uiDomJsPath = path.join(rootDir, 'frontend', 'src', 'js', 'ui-dom.js');
const swJsPath = path.join(rootDir, 'frontend', 'service-worker.js');
const manifestPath = path.join(rootDir, 'frontend', 'app.webmanifest');

// Utility: parse hex color to relative luminance for WCAG contrast
function hexToRgb(hex) {
    const clean = hex.replace('#', '');
    const num = parseInt(clean, 16);
    return [
        (num >> 16) & 255,
        (num >> 8) & 255,
        num & 255
    ];
}

function relativeLuminance([r, g, b]) {
    const srgb = [r, g, b].map((val) => {
        const c = val / 255;
        return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * srgb[0] + 0.7152 * srgb[1] + 0.0722 * srgb[2];
}

function contrastRatio(hexA, hexB) {
    const lumA = relativeLuminance(hexToRgb(hexA));
    const lumB = relativeLuminance(hexToRgb(hexB));
    const brighter = Math.max(lumA, lumB);
    const darker = Math.min(lumA, lumB);
    return (brighter + 0.05) / (darker + 0.05);
}

describe('VibeAudio Theme System Invariants', () => {
    describe('1. CSS Design Tokens & Contrast Verification', () => {
        const baseCss = fs.readFileSync(baseCssPath, 'utf8');

        it('should declare complete daylight tokens under [data-theme="light"]', () => {
            assert.ok(baseCss.includes('data-theme="light"'), 'Must define [data-theme="light"] block');
            assert.ok(baseCss.includes('--color-canvas: #F8F6F1'), 'Daylight canvas token must be warm parchment');
            assert.ok(baseCss.includes('--color-surface-1: #FFFFFF'), 'Surface-1 must be clean linen white');
            assert.ok(baseCss.includes('--color-surface-2: #EFECE4'), 'Surface-2 must be warm parchment layer');
            assert.ok(baseCss.includes('--color-surface-3: #E3DDD0'), 'Surface-3 must be deep stone parchment layer');
            assert.ok(baseCss.includes('--color-text-primary: #1A1815'), 'Primary text must be deep warm ink');
            assert.ok(baseCss.includes('--color-accent: #C67D0A'), 'Accent must be warm dark amber');
            assert.ok(baseCss.includes('--theme-progress-track'), 'Daylight theme progress track must be defined');
            assert.ok(baseCss.includes('--theme-player-overlay'), 'Daylight player overlay must be defined');
        });

        it('should declare prefers-color-scheme: light media query', () => {
            assert.ok(baseCss.includes('@media (prefers-color-scheme: light)'), 'Media query for prefers-color-scheme: light must exist');
            assert.ok(baseCss.includes('--color-canvas: #F8F6F1'), 'Parchment canvas in prefers-color-scheme query');
        });

        it('should satisfy WCAG AA contrast for text against canvas and surfaces', () => {
            const canvas = '#F8F6F1';
            const surface1 = '#FFFFFF';
            const surface2 = '#EFECE4';
            const textPrimary = '#1A1815';
            const textSecondary = '#2C2823';
            const textSoft = '#544C44';

            // WCAG AA requires at least 4.5:1 for normal body text
            const contrastPrimaryOnCanvas = contrastRatio(textPrimary, canvas);
            const contrastSecondaryOnCanvas = contrastRatio(textSecondary, canvas);
            const contrastSoftOnCanvas = contrastRatio(textSoft, canvas);
            const contrastPrimaryOnSurface1 = contrastRatio(textPrimary, surface1);
            const contrastPrimaryOnSurface2 = contrastRatio(textPrimary, surface2);

            assert.ok(contrastPrimaryOnCanvas >= 7.0, `Primary text on canvas must meet WCAG AAA (got ${contrastPrimaryOnCanvas.toFixed(2)}:1)`);
            assert.ok(contrastSecondaryOnCanvas >= 7.0, `Secondary text on canvas must meet WCAG AAA (got ${contrastSecondaryOnCanvas.toFixed(2)}:1)`);
            assert.ok(contrastSoftOnCanvas >= 4.5, `Soft text on canvas must meet WCAG AA (got ${contrastSoftOnCanvas.toFixed(2)}:1)`);
            assert.ok(contrastPrimaryOnSurface1 >= 7.0, `Primary text on surface-1 must meet WCAG AAA (got ${contrastPrimaryOnSurface1.toFixed(2)}:1)`);
            assert.ok(contrastPrimaryOnSurface2 >= 7.0, `Primary text on surface-2 must meet WCAG AAA (got ${contrastPrimaryOnSurface2.toFixed(2)}:1)`);
        });

        it('should style appearance panel and theme pickers in app-sections.css', () => {
            const sectionsCss = fs.readFileSync(appSectionsCssPath, 'utf8');
            assert.ok(sectionsCss.includes('.appearance-panel'), 'Must style appearance panel');
            assert.ok(sectionsCss.includes('.theme-picker-group'), 'Must style theme picker group');
            assert.ok(sectionsCss.includes('.theme-choice-btn'), 'Must style theme choice buttons');
            assert.ok(sectionsCss.includes('.theme-choice-swatch'), 'Must style swatches');
            assert.ok(sectionsCss.includes('.light-swatch'), 'Must style light swatch');
            assert.ok(sectionsCss.includes('.dark-swatch'), 'Must style dark swatch');
        });
    });

    describe('2. DOM Contracts & Zero-FOUC Implementation', () => {
        const appHtml = fs.readFileSync(appHtmlPath, 'utf8');
        const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');

        it('app.html should contain zero-FOUC theme boot script in head', () => {
            const headMatch = appHtml.match(/<head>([\s\S]*?)<\/head>/i);
            assert.ok(headMatch, '<head> must exist in app.html');
            const headContent = headMatch[1];
            assert.ok(headContent.includes("localStorage.getItem('vibe_theme')"), 'Head script must inspect vibe_theme in localStorage');
            assert.ok(headContent.includes('data-theme'), 'Head script must set data-theme attribute on documentElement');
        });

        it('index.html should contain zero-FOUC theme boot script in head', () => {
            const headMatch = indexHtml.match(/<head>([\s\S]*?)<\/head>/i);
            assert.ok(headMatch, '<head> must exist in index.html');
            const headContent = headMatch[1];
            assert.ok(headContent.includes("localStorage.getItem('vibe_theme')"), 'Index head script must inspect vibe_theme');
            assert.ok(headContent.includes('data-theme'), 'Index head script must set data-theme attribute');
        });

        it('app.html must provide theme toggle controls in topbar, sidebar, and profile', () => {
            assert.ok(appHtml.includes('id="theme-toggle-btn"'), 'Topbar theme toggle button (#theme-toggle-btn)');
            assert.ok(appHtml.includes('id="sidebar-theme-toggle-btn"'), 'Sidebar theme toggle button (#sidebar-theme-toggle-btn)');
            assert.ok(appHtml.includes('class="appearance-panel"'), 'Profile appearance panel (.appearance-panel)');
            assert.ok(appHtml.includes('data-theme-choice="light"'), 'Light theme choice button');
            assert.ok(appHtml.includes('data-theme-choice="dark"'), 'Dark theme choice button');
            assert.ok(appHtml.includes('id="icon-sun"'), 'Icon sprite must declare icon-sun');
            assert.ok(appHtml.includes('id="icon-moon"'), 'Icon sprite must declare icon-moon');
        });

        it('index.html must provide landing theme toggle and icon symbols', () => {
            assert.ok(indexHtml.includes('id="landing-theme-toggle-btn"'), 'Landing topbar theme toggle button');
            assert.ok(indexHtml.includes('id="icon-sun"'), 'Landing icon sprite must declare icon-sun');
            assert.ok(indexHtml.includes('id="icon-moon"'), 'Landing icon sprite must declare icon-moon');
        });

        it('STORAGE_KEYS must declare theme storage key', () => {
            assert.equal(STORAGE_KEYS.theme, 'vibe_theme', 'STORAGE_KEYS.theme must be vibe_theme');
        });
    });

    describe('3. Dynamic Theme Engine & Chameleon Palette Logic', () => {
        it('buildTheme should produce dark theme values when data-theme is dark or unset', () => {
            const darkTheme = buildTheme([[229, 169, 60], [155, 161, 176], [30, 35, 43], [12, 13, 17]], 'player');
            assert.ok(darkTheme['--theme-title'].includes('248'), 'Dark theme title should be bright parchment');
            assert.ok(darkTheme['--theme-progress-track'], 'Dark theme progress track exists');
        });

        it('buildTheme should produce ink typography and parchment overlays in daylight mode', () => {
            const originalDoc = global.document;
            global.document = {
                documentElement: {
                    getAttribute: (attr) => (attr === 'data-theme' ? 'light' : null),
                    style: { setProperty: () => {} }
                },
                querySelector: () => null
            };

            try {
                const lightTheme = buildTheme([[229, 169, 60], [155, 161, 176], [30, 35, 43], [12, 13, 17]], 'player');
                assert.ok(lightTheme['--theme-title'].includes('26, 24, 21'), 'Light theme title must be deep warm ink #1A1815');
                assert.ok(lightTheme['--theme-text'].includes('44, 40, 35'), 'Light theme text must be warm ink #2C2823');
                assert.ok(lightTheme['--theme-title-gradient-start'] === '#1A1815', 'Gradient start must be ink');
                assert.ok(lightTheme['--theme-player-overlay'].includes('255, 255, 255'), 'Overlay must use translucent white paper bloom');
            } finally {
                global.document = originalDoc;
            }
        });

        it('ui-dom.js injectUiRuntimeStyles must use semantic variables instead of hardcoded dark colors', () => {
            const uiDomContent = fs.readFileSync(uiDomJsPath, 'utf8');
            assert.ok(!uiDomContent.includes('rgba(255, 250, 239, 0.035)'), 'Must not use hardcoded obsidian tint in skeleton');
            assert.ok(!uiDomContent.includes('rgba(255, 250, 239, 0.04)'), 'Must not use hardcoded obsidian tint in sync indicator');
            assert.ok(uiDomContent.includes('var(--color-surface-2)'), 'Must use semantic var(--color-surface-2)');
            assert.ok(uiDomContent.includes('var(--color-border)'), 'Must use semantic var(--color-border)');
        });
    });

    describe('4. AntiOS Invariant & Asset Shell Protection', () => {
        it('app.webmanifest must preserve original theme_color and background_color', () => {
            const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
            assert.equal(manifest.theme_color, '#0C0D11', 'Webmanifest theme_color must remain #0C0D11');
            assert.equal(manifest.background_color, '#0C0D11', 'Webmanifest background_color must remain #0C0D11');
        });

        it('service-worker.js precache list must remain intact at exactly 40 assets', () => {
            const swContent = fs.readFileSync(swJsPath, 'utf8');
            const precacheMatch = swContent.match(/const PRECACHE_URLS = \[([\s\S]*?)\];/);
            assert.ok(precacheMatch, 'PRECACHE_URLS array must exist in service-worker.js');
            const assets = precacheMatch[1]
                .split('\n')
                .map((line) => line.trim().replace(/^['"]|['"],?$/g, ''))
                .filter(Boolean);
            assert.equal(assets.length, 40, `PRECACHE_URLS must contain exactly 40 assets (found ${assets.length})`);
        });
    });
});
