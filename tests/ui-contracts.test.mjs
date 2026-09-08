import test, { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');
const appHtmlPath = path.join(rootDir, 'frontend', 'src', 'pages', 'app.html');

describe('UI & DOM Contract Regression Invariants', () => {
    assert(fs.existsSync(appHtmlPath), 'app.html must exist');
    const html = fs.readFileSync(appHtmlPath, 'utf8');

    function assertElementExists(id, description = '') {
        const idRegex = new RegExp(`id=["']${id}["']`);
        assert.ok(idRegex.test(html), `Required UI DOM contract missing: #${id} (${description})`);
    }

    function assertClassExists(className, description = '') {
        const classRegex = new RegExp(`class=["'][^"']*\\b${className}\\b[^"']*["']`);
        assert.ok(classRegex.test(html), `Required UI CSS class missing: .${className} (${description})`);
    }

    describe('Primary View Sections Contracts', () => {
        it('should declare all primary application screens', () => {
            assertElementExists('view-home', 'Home screen container');
            assertElementExists('view-library', 'Library screen container');
            assertElementExists('view-offline', 'On This Device offline screen container');
            assertElementExists('view-history', 'Listening history screen container');
            assertElementExists('view-profile', 'User profile & storage settings screen container');
            assertElementExists('view-about', 'About screen container');
            assertElementExists('view-player', 'Full player screen container');
        });
    });

    describe('Home Sanctuary Layout Contracts', () => {
        it('should declare essential Home visual hierarchy elements', () => {
            assertElementExists('home-resume-hero', 'Continue listening hero visual anchor');
            assertElementExists('home-offline-shelf', 'Saved locally shelf container');
            assertElementExists('home-offline-grid', 'Offline audiobooks horizontal shelf grid');
            assertElementExists('home-curated-shelf', 'Curated picks shelf container');
            assertElementExists('home-curated-grid', 'Curated picks grid');
            assertElementExists('home-empty-state', 'Welcoming empty shelf state');
        });
    });

    describe('Navigation & Topbar Contracts', () => {
        it('should declare topbar navigation buttons and search controls', () => {
            assert.ok(html.includes('data-nav-view="home"'), 'Topbar must have Home nav destination');
            assert.ok(html.includes('data-nav-view="library"'), 'Topbar must have Library nav destination');
            assert.ok(html.includes('data-nav-view="offline"'), 'Topbar must have On This Device nav destination');
            assertElementExists('search-input', 'Global search input field');
            assertElementExists('search-clear-btn', 'Clear search query button');
            assertElementExists('menu-btn', 'Mobile menu hamburger button');
            assertElementExists('sidebar', 'Navigation sidebar drawer');
            assertElementExists('close-sidebar', 'Close sidebar button');
        });
    });

    describe('Mini-Player Dock Contracts', () => {
        it('should declare the persistent mini-player dock and interaction controls', () => {
            assertElementExists('mini-player', 'Persistent mini-player container');
            assertElementExists('mini-track-info', 'Expandable track info trigger');
            assertElementExists('mini-cover', 'Mini cover image element');
            assertElementExists('mini-title', 'Mini track title element');
            assertElementExists('mini-chapter', 'Mini chapter subtitle element');
            assertElementExists('mini-progress-line-fill', 'Mini player progress fill bar');
            assertElementExists('mini-seek-back-btn', 'Mini player back 15s button');
            assertElementExists('mini-play-btn', 'Mini player play/pause toggle button');
            assertElementExists('mini-seek-fwd-btn', 'Mini player forward 30s button');
        });
    });

    describe('Full Player Transport Deck Contracts', () => {
        it('should declare full player controls, scrubber, and secondary drawers', () => {
            assertElementExists('back-btn', 'Back to shelf button');
            assertElementExists('detail-cover', 'Audiobook cover art image');
            assertElementExists('detail-title', 'Audiobook title headline');
            assertElementExists('detail-author', 'Audiobook author byline');
            assertElementExists('main-play-btn', 'Header primary Listen Now button');
            assertElementExists('download-book-btn', 'Save for offline button');
            assertElementExists('remove-offline-book-btn', 'Remove offline copy button');

            // Scrubber and Transport Deck
            assertElementExists('progress-bar', 'Range scrubber input');
            assertElementExists('current-time', 'Scrubber elapsed timecode');
            assertElementExists('total-duration', 'Scrubber total duration timecode');
            assertElementExists('speed-btn', 'Playback speed selector button');
            assertElementExists('seek-back-btn', 'Transport jump backward 15s');
            assertElementExists('play-btn', 'Transport main play/pause button');
            assertElementExists('seek-fwd-btn', 'Transport jump forward 30s');
            assertElementExists('sleep-timer-btn', 'Transport sleep timer button');

            // Chapters and Notes
            assertElementExists('chapter-list', 'Interactive chapter playlist container');
            assertElementExists('bookmark-list', 'Saved moments bookmark list container');
            assertElementExists('bookmark-current-btn', 'Save moment action button');
            assertElementExists('comments-list', 'Notes and timestamps comments list');
            assertElementExists('comment-input', 'Moment note input');
            assertElementExists('post-comment-btn', 'Submit moment note button');

            // Audio Element
            assertElementExists('audio-element', 'Primary HTML5 audio element');
        });
    });
});
