import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const ROOT_DIR = process.cwd();
const FRONTEND_DIR = path.join(ROOT_DIR, 'frontend');

test('Brand and Icon System Suite', async (t) => {

    await t.test('Locked Brand Mark Master Assets exist and are valid SVGs', () => {
        const brandMarkSvgPath = path.join(FRONTEND_DIR, 'public', 'icons', 'brand-mark.svg');
        const monochromeSvgPath = path.join(FRONTEND_DIR, 'public', 'icons', 'brand-mark-monochrome.svg');
        const lockupHorizontalPath = path.join(FRONTEND_DIR, 'public', 'icons', 'brand-lockup-horizontal.svg');
        const lockupCompactPath = path.join(FRONTEND_DIR, 'public', 'icons', 'brand-lockup-compact.svg');
        const lockupStackedPath = path.join(FRONTEND_DIR, 'public', 'icons', 'brand-lockup-stacked.svg');
        const faviconSvgPath = path.join(FRONTEND_DIR, 'src', 'icons', 'favicon.svg');

        const brandFiles = [
            brandMarkSvgPath,
            monochromeSvgPath,
            lockupHorizontalPath,
            lockupCompactPath,
            lockupStackedPath,
            faviconSvgPath
        ];

        for (const file of brandFiles) {
            assert.ok(fs.existsSync(file), `File should exist: ${file}`);
            const content = fs.readFileSync(file, 'utf8');
            assert.ok(content.length > 50, `File should not be empty: ${file}`);
            assert.match(content, /<svg[^>]*>/, `File should contain SVG element: ${file}`);
        }

        const brandMarkContent = fs.readFileSync(brandMarkSvgPath, 'utf8');
        assert.match(brandMarkContent, /viewBox="0 0 24 24"/, 'Master brand mark must have 24x24 viewBox');
        assert.match(brandMarkContent, /stroke-width="1\.85"/, 'Master brand mark must have 1.85px stroke width');
    });

    await t.test('Master SVG icon sprite contains all required canonical symbols', () => {
        const spritePath = path.join(FRONTEND_DIR, 'src', 'icons', 'icons.svg');
        assert.ok(fs.existsSync(spritePath), 'Master icons.svg sprite must exist');
        const content = fs.readFileSync(spritePath, 'utf8');

        const canonicalSymbols = [
            // Brand & Navigation
            'icon-brand-mark', 'icon-home', 'icon-library', 'icon-offline', 'icon-device',
            'icon-history', 'icon-account', 'icon-user', 'icon-menu', 'icon-search',
            'icon-clear', 'icon-close',

            // Playback & Transport
            'icon-play', 'icon-pause', 'icon-seek-back', 'icon-seek-forward', 'icon-speed',
            'icon-sleep', 'icon-vocal-clarity', 'icon-waveform', 'icon-equalizer',

            // Storage & Offline
            'icon-download', 'icon-cloud-download', 'icon-downloaded', 'icon-cloud-sync',
            'icon-import', 'icon-storage', 'icon-sync',

            // Feedback & Utility
            'icon-bookmark', 'icon-note', 'icon-check', 'icon-check-circle', 'icon-share',
            'icon-trash', 'icon-arrow-left', 'icon-arrow-right', 'icon-chevron-down',
            'icon-chevron-up', 'icon-chevron-right', 'icon-spinner', 'icon-send',
            'icon-logout', 'icon-open-external', 'icon-info', 'icon-warning', 'icon-ban',
            'icon-chapters', 'icon-install', 'icon-sparkles', 'icon-book-open',
            'icon-user-check', 'icon-shield', 'icon-lanes'
        ];

        for (const sym of canonicalSymbols) {
            assert.ok(content.includes(`id="${sym}"`), `Sprite must contain symbol id="${sym}"`);
        }
    });

    await t.test('Optimized raster brand, favicon, and PWA assets exist and meet budget', () => {
        const rasterFiles = [
            { path: path.join(FRONTEND_DIR, 'src', 'icons', 'favicon-16.png'), maxKb: 5 },
            { path: path.join(FRONTEND_DIR, 'src', 'icons', 'favicon-32.png'), maxKb: 5 },
            { path: path.join(FRONTEND_DIR, 'src', 'icons', 'favicon.ico'), maxKb: 10 },
            { path: path.join(FRONTEND_DIR, 'src', 'icons', 'favicon.png'), maxKb: 50 },
            { path: path.join(FRONTEND_DIR, 'public', 'icons', 'icon-192.png'), maxKb: 30 },
            { path: path.join(FRONTEND_DIR, 'public', 'icons', 'icon-512.png'), maxKb: 50 },
            { path: path.join(FRONTEND_DIR, 'public', 'icons', 'icon-maskable-512.png'), maxKb: 50 },
            { path: path.join(FRONTEND_DIR, 'public', 'icons', 'apple-touch-icon.png'), maxKb: 30 },
            { path: path.join(FRONTEND_DIR, 'public', 'icons', 'logo.png'), maxKb: 50 }
        ];

        for (const item of rasterFiles) {
            assert.ok(fs.existsSync(item.path), `Raster asset should exist: ${item.path}`);
            const stats = fs.statSync(item.path);
            const sizeKb = stats.size / 1024;
            assert.ok(stats.size > 0, `Raster asset should not be empty: ${item.path}`);
            assert.ok(sizeKb <= item.maxKb, `Raster asset ${path.basename(item.path)} (${sizeKb.toFixed(1)} KB) exceeds budget (${item.maxKb} KB)`);
        }
    });

    await t.test('Zero legacy Font Awesome CDN stylesheets or glyph classes in HTML templates', () => {
        const indexHtml = fs.readFileSync(path.join(FRONTEND_DIR, 'index.html'), 'utf8');
        const appHtml = fs.readFileSync(path.join(FRONTEND_DIR, 'src', 'pages', 'app.html'), 'utf8');

        assert.ok(!indexHtml.includes('font-awesome'), 'index.html must not reference Font Awesome');
        assert.ok(!indexHtml.includes('all.min.css'), 'index.html must not link Font Awesome CSS');
        assert.ok(!indexHtml.includes('fas fa-'), 'index.html must not use Font Awesome classes');

        assert.ok(!appHtml.includes('font-awesome'), 'app.html must not reference Font Awesome');
        assert.ok(!appHtml.includes('all.min.css'), 'app.html must not link Font Awesome CSS');
        assert.ok(!appHtml.includes('fas fa-'), 'app.html must not use Font Awesome classes');
    });

    await t.test('Zero legacy Font Awesome glyph classes in JS UI renderers', () => {
        const jsFiles = [
            path.join(FRONTEND_DIR, 'src', 'js', 'ui.js'),
            path.join(FRONTEND_DIR, 'src', 'js', 'ui-player-main.js'),
            path.join(FRONTEND_DIR, 'src', 'js', 'ui-player-list.js'),
            path.join(FRONTEND_DIR, 'src', 'js', 'ui-library.js'),
            path.join(FRONTEND_DIR, 'src', 'js', 'pwa.js'),
            path.join(FRONTEND_DIR, 'src', 'js', 'landing.js')
        ];

        for (const file of jsFiles) {
            const content = fs.readFileSync(file, 'utf8');
            assert.ok(!content.includes('fas fa-'), `${path.basename(file)} must not contain "fas fa-" classes`);
            assert.ok(!content.includes('fa-spin'), `${path.basename(file)} must not contain "fa-spin" classes`);
        }
    });

    await t.test('PWA manifest and Service Worker reference new brand and icon assets', () => {
        const manifest = JSON.parse(fs.readFileSync(path.join(FRONTEND_DIR, 'app.webmanifest'), 'utf8'));
        const swContent = fs.readFileSync(path.join(FRONTEND_DIR, 'service-worker.js'), 'utf8');

        assert.ok(manifest.icons.length >= 3, 'Manifest must declare at least 3 icon sizes');
        for (const icon of manifest.icons) {
            const iconDiskPath = path.join(FRONTEND_DIR, icon.src.replace(/^\.\//, ''));
            assert.ok(fs.existsSync(iconDiskPath), `Manifest icon must exist on disk: ${icon.src}`);
        }

        assert.ok(swContent.includes('./public/icons/brand-mark.svg'), 'SW must precache brand-mark.svg');
        assert.ok(swContent.includes('./src/icons/icons.svg'), 'SW must precache icons.svg');
        assert.ok(swContent.includes('./src/icons/favicon.svg'), 'SW must precache favicon.svg');
    });
});
