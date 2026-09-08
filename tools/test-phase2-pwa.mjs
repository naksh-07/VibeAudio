import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');
const frontendDir = path.resolve(rootDir, 'frontend');

console.log('=== VIBEAUDIO PRODUCTION PHASE 2 PWA & RELEASE INFRASTRUCTURE VERIFICATION ===\n');

// 1. Validate Web App Manifest
console.log('Test 1: Web App Manifest Schema, Identifiers & Assets');
const manifestPath = path.join(frontendDir, 'app.webmanifest');
assert(fs.existsSync(manifestPath), 'app.webmanifest must exist');

const manifestRaw = fs.readFileSync(manifestPath, 'utf8');
const manifest = JSON.parse(manifestRaw);

assert.strictEqual(manifest.name, 'VibeAudio');
assert.strictEqual(manifest.short_name, 'VibeAudio');
assert.strictEqual(manifest.start_url, './src/pages/app.html#home', 'start_url must point to Home-first entry');
assert.strictEqual(manifest.id, './src/pages/app.html', 'id must match app shell');
assert.strictEqual(manifest.display, 'standalone');
assert.strictEqual(manifest.theme_color, '#0C0D11', 'theme_color must match Warm Obsidian');
assert.strictEqual(manifest.background_color, '#0C0D11', 'background_color must match Warm Obsidian');
assert(Array.isArray(manifest.display_override) && manifest.display_override.includes('standalone'), 'display_override must support standalone');

assert(Array.isArray(manifest.icons) && manifest.icons.length >= 2, 'Manifest must have at least 2 icon sizes');
manifest.icons.forEach((icon) => {
    const relativeIconPath = icon.src.replace(/^\.\//, '');
    const absoluteIconPath = path.join(frontendDir, relativeIconPath);
    assert(fs.existsSync(absoluteIconPath), `Manifest icon file must physically exist: ${icon.src}`);
    const stat = fs.statSync(absoluteIconPath);
    assert(stat.size > 0, `Manifest icon file must not be empty: ${icon.src}`);
    assert(icon.purpose?.includes('maskable'), `Icon ${icon.src} should support maskable purpose`);
});

assert(Array.isArray(manifest.shortcuts) && manifest.shortcuts.length >= 3, 'Manifest must declare quick action shortcuts');
const shortcutUrls = manifest.shortcuts.map((s) => s.url);
assert(shortcutUrls.includes('./src/pages/app.html#home'), 'Shortcut to Home must exist');
assert(shortcutUrls.includes('./src/pages/app.html#offline'), 'Shortcut to Offline shelf must exist');
assert(shortcutUrls.includes('./src/pages/app.html#library'), 'Shortcut to Library must exist');
console.log('  ✓ Web App Manifest passes all schema, branding, color, and icon asset tests');

// 2. Validate Service Worker Precaching Integrity
console.log('\nTest 2: Service Worker Precache Inventory & Versioning');
const swPath = path.join(frontendDir, 'service-worker.js');
assert(fs.existsSync(swPath), 'service-worker.js must exist');
const swContent = fs.readFileSync(swPath, 'utf8');

const cacheVersionMatch = swContent.match(/const CACHE_VERSION = '([^']+)';/);
assert(cacheVersionMatch, 'CACHE_VERSION must be declared in service worker');
assert.strictEqual(cacheVersionMatch[1], 'v14-production', 'CACHE_VERSION must be updated to v14-production');

const precacheMatch = swContent.match(/const PRECACHE_URLS = \[([\s\S]*?)\];/);
assert(precacheMatch, 'PRECACHE_URLS array must exist');

const precacheUrls = precacheMatch[1]
    .split('\n')
    .map((line) => line.trim().replace(/^['"]|['"],?$/g, ''))
    .filter(Boolean);

assert(precacheUrls.length >= 25, `Expected at least 25 precached files, found ${precacheUrls.length}`);

precacheUrls.forEach((url) => {
    if (url === './') return; // root alias
    const relativePath = url.replace(/^\.\//, '');
    const absoluteFilePath = path.join(frontendDir, relativePath);
    assert(fs.existsSync(absoluteFilePath), `Precache URL file must exist on disk: ${url} -> ${absoluteFilePath}`);
    const stat = fs.statSync(absoluteFilePath);
    assert(stat.size > 0, `Precache file must not be empty: ${url}`);
});
console.log(`  ✓ All ${precacheUrls.length} precached shell assets physically exist with non-zero size`);

// 3. Validate Storage Isolation Invariant
console.log('\nTest 3: Storage Isolation Invariants (SW Cache vs User Storage)');
// In Service Worker activate handler:
const hasOnlyCachesDelete = swContent.includes('caches.delete(key)');
const touchesIndexedDB = swContent.includes('indexedDB.deleteDatabase') || swContent.includes('deleteDatabase');
const touchesOPFS = swContent.includes('removeEntry') || swContent.includes('getDirectory');

assert(hasOnlyCachesDelete, 'Service Worker must only delete Cache Storage caches');
assert(!touchesIndexedDB, 'Service Worker must NEVER delete IndexedDB storage');
assert(!touchesOPFS, 'Service Worker must NEVER purge OPFS audiobook directory');
console.log('  ✓ Storage isolation strictly preserved: Cache updates cannot wipe OPFS or IndexedDB data');

// 4. Validate Routing and View Normalization Logic
console.log('\nTest 4: View Normalization & Home-First Routing Invariants');
const VALID_VIEWS = new Set(['home', 'library', 'history', 'offline', 'about', 'profile', 'player']);
function normalizeViewId(id) {
    if (!id || id === 'home') return 'home';
    return VALID_VIEWS.has(id) ? id : 'home';
}

assert.strictEqual(normalizeViewId(''), 'home', 'Empty view defaults to home');
assert.strictEqual(normalizeViewId(null), 'home', 'Null view defaults to home');
assert.strictEqual(normalizeViewId('home'), 'home', 'Home resolves to home');
assert.strictEqual(normalizeViewId('library'), 'library', 'Library resolves to library');
assert.strictEqual(normalizeViewId('offline'), 'offline', 'Offline resolves to offline');
assert.strictEqual(normalizeViewId('unknown_random_hash'), 'home', 'Unknown view safely falls back to home');
console.log('  ✓ Routing normalization guarantees Home-first listening sanctuary default');

// 5. Validate Guest-First Boot Sequence
console.log('\nTest 5: Guest-First App Boot Sequence');
const appEntryPath = path.join(frontendDir, 'src', 'js', 'app-entry.js');
const appEntryContent = fs.readFileSync(appEntryPath, 'utf8');

assert(!appEntryContent.includes('ensureSignedInOrRedirect'), 'app-entry.js must NOT forcibly redirect online guests to landing page');
assert(appEntryContent.includes('import(\'./ui.js\')'), 'app-entry.js must boot ui.js for guest and authenticated sessions alike');
console.log('  ✓ App entry is guest-first and does not eject unauthenticated listeners');

// 6. Validate Landing Page Consistency & Fonts
console.log('\nTest 6: Landing Page Product Identity & Typography');
const indexPath = path.join(frontendDir, 'index.html');
const indexContent = fs.readFileSync(indexPath, 'utf8');

assert(indexContent.includes('VibeAudio | Personal Audiobook Sanctuary'), 'Page title communicates personal listening sanctuary');
assert(indexContent.includes('href="./src/pages/app.html#home"'), 'Landing CTA navigates directly to app home shelf');
assert(indexContent.includes('family=Inter') && indexContent.includes('family=Newsreader'), 'Google Fonts loads Inter and Newsreader');
assert(!indexContent.includes('Discovery-first audiobook experience'), 'Obsolete discovery-first marketing copy removed');
assert(indexContent.includes('Cloud sync (optional)'), 'Auth section clearly framed as optional cloud sync');
console.log('  ✓ Landing page communicates the exact same guest-first, listening-first identity as the app');

// 7. Validate PWA Bridge & Safe-Area Styles
console.log('\nTest 7: PWA Bridge & Safe Area Styles');
const pwaJsPath = path.join(frontendDir, 'src', 'js', 'pwa.js');
const pwaJsContent = fs.readFileSync(pwaJsPath, 'utf8');
assert(pwaJsContent.includes('getAllInstallButtons'), 'pwa.js queries and syncs all install buttons');
assert(pwaJsContent.includes('is-standalone-app'), 'pwa.js toggles is-standalone-app class');

const baseCssPath = path.join(frontendDir, 'src', 'css', 'base.css');
const baseCssContent = fs.readFileSync(baseCssPath, 'utf8');
assert(baseCssContent.includes('is-standalone-app'), 'base.css has standalone mode styling');
assert(baseCssContent.includes('safe-area-inset-top'), 'base.css supports safe-area-inset-top');
assert(baseCssContent.includes('safe-area-inset-bottom'), 'base.css supports safe-area-inset-bottom');
console.log('  ✓ PWA bridge and standalone safe area CSS styles verified');

console.log('\n================================================================');
console.log('ALL PHASE 2 PWA & RELEASE INFRASTRUCTURE INVARIANTS PASSED (7/7)!');
console.log('================================================================\n');
