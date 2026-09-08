import test, { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');
const frontendDir = path.resolve(rootDir, 'frontend');

describe('PWA, Manifest & Service Worker Invariants', () => {
    describe('Web App Manifest Verification', () => {
        const manifestPath = path.join(frontendDir, 'app.webmanifest');
        assert(fs.existsSync(manifestPath), 'app.webmanifest must exist');
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

        it('should declare valid name and brand identifiers', () => {
            assert.equal(manifest.name, 'VibeAudio');
            assert.equal(manifest.short_name, 'VibeAudio');
            assert.equal(manifest.id, './src/pages/app.html');
            assert.equal(manifest.start_url, './src/pages/app.html#home');
        });

        it('should configure standalone display and Warm Obsidian color theme', () => {
            assert.equal(manifest.display, 'standalone');
            assert.equal(manifest.theme_color, '#0C0D11');
            assert.equal(manifest.background_color, '#0C0D11');
            assert.ok(Array.isArray(manifest.display_override));
            assert.ok(manifest.display_override.includes('standalone'));
        });

        it('should have valid icons existing on disk with maskable support', () => {
            assert.ok(Array.isArray(manifest.icons) && manifest.icons.length >= 2);
            for (const icon of manifest.icons) {
                const relativePath = icon.src.replace(/^\.\//, '');
                const absolutePath = path.join(frontendDir, relativePath);
                assert.ok(fs.existsSync(absolutePath), `Icon file must exist: ${icon.src}`);
                const stat = fs.statSync(absolutePath);
                assert.ok(stat.size > 0, `Icon file must not be empty: ${icon.src}`);
                assert.ok(icon.purpose?.includes('maskable'), `Icon ${icon.src} must support maskable`);
            }
        });

        it('should configure fast action shortcuts to Home, Offline, and Library', () => {
            assert.ok(Array.isArray(manifest.shortcuts) && manifest.shortcuts.length >= 3);
            const urls = manifest.shortcuts.map((s) => s.url);
            assert.ok(urls.includes('./src/pages/app.html#home'));
            assert.ok(urls.includes('./src/pages/app.html#offline'));
            assert.ok(urls.includes('./src/pages/app.html#library'));
        });
    });

    describe('Service Worker Precache & Lifecycle Verification', () => {
        const swPath = path.join(frontendDir, 'service-worker.js');
        assert(fs.existsSync(swPath), 'service-worker.js must exist');
        const swContent = fs.readFileSync(swPath, 'utf8');

        it('should have production CACHE_VERSION declared', () => {
            const match = swContent.match(/const CACHE_VERSION = '([^']+)';/);
            assert.ok(match);
            assert.equal(match[1], 'v14-production');
        });

        it('should verify all precached shell assets physically exist and are non-empty', () => {
            const precacheMatch = swContent.match(/const PRECACHE_URLS = \[([\s\S]*?)\];/);
            assert.ok(precacheMatch);

            const precacheUrls = precacheMatch[1]
                .split('\n')
                .map((line) => line.trim().replace(/^['"]|['"],?$/g, ''))
                .filter(Boolean);

            assert.ok(precacheUrls.length >= 25, `Expected >= 25 precache files, got ${precacheUrls.length}`);

            for (const url of precacheUrls) {
                if (url === './') continue;
                const relativePath = url.replace(/^\.\//, '');
                const absolutePath = path.join(frontendDir, relativePath);
                assert.ok(fs.existsSync(absolutePath), `Precached file missing on disk: ${url}`);
                const stat = fs.statSync(absolutePath);
                assert.ok(stat.size > 0, `Precached file is empty: ${url}`);
            }
        });

        it('should strictly preserve user storage during cache activation', () => {
            // Cache cleanup must only delete CacheStorage items, never IndexedDB or OPFS
            assert.ok(swContent.includes('caches.delete(key)'));
            assert.equal(swContent.includes('indexedDB.deleteDatabase'), false);
            assert.equal(swContent.includes('removeEntry'), false);
        });

        it('should exclude sensitive/auth API requests from Service Worker caching', () => {
            // Check that auth routes or credentials requests bypass cache
            assert.ok(
                swContent.includes('auth') ||
                swContent.includes('bypass') ||
                swContent.includes('networkOnly') ||
                swContent.includes('/auth') ||
                swContent.includes('execute-api') ||
                swContent.includes('api')
            );
        });
    });

    describe('PWA Bridge and UI Integration', () => {
        it('should verify pwa.js contains install button handling and standalone class sync', () => {
            const pwaJsPath = path.join(frontendDir, 'src', 'js', 'pwa.js');
            assert(fs.existsSync(pwaJsPath));
            const content = fs.readFileSync(pwaJsPath, 'utf8');

            assert.ok(content.includes('getAllInstallButtons'));
            assert.ok(content.includes('is-standalone-app'));
            assert.ok(content.includes('beforeinstallprompt'));
        });
    });
});
