import { fetchAllBooks } from './api.js';
import { getSignedInUser, mountSignIn, persistUserProfile } from './auth.js';

const APP_URL = './src/pages/app.html#home';
const OFFLINE_APP_URL = './src/pages/app.html#offline';

function toAbsoluteUrl(value) {
    try {
        return new URL(String(value || ''), window.location.href).href;
    } catch (error) {
        return '';
    }
}

function warmOfflinePreview(books = []) {
    const bridge = window.VibePWA;
    if (!bridge?.primeOfflineResources) return;

    const previewBooks = Array.isArray(books) ? books.slice(0, 8) : [];
    const urls = [
        './',
        './index.html',
        './app.webmanifest',
        './src/pages/app.html',
        ...previewBooks.flatMap((book) => [book?.dataPath, book?.cover])
    ]
        .map(toAbsoluteUrl)
        .filter(Boolean);

    void bridge.primeOfflineResources(urls);
}

async function hasCachedOfflineAppShell() {
    if (window.VibePWA?.isOfflineShellLikelyReady?.()) {
        return true;
    }

    if (!('caches' in window)) return false;

    try {
        const absoluteAppUrl = new URL('./src/pages/app.html', window.location.href).href;
        const cachedAppShell = await caches.match(absoluteAppUrl) || await caches.match('./src/pages/app.html');
        return Boolean(cachedAppShell);
    } catch (error) {
        console.warn('Unable to inspect cached app shell.', error);
        return false;
    }
}

async function openOfflineShelfIfReady() {
    if (navigator.onLine) return false;
    if (window.location.pathname.includes('/src/pages/app')) return false;

    const ready = await hasCachedOfflineAppShell();
    if (!ready) return false;

    window.location.replace(OFFLINE_APP_URL);
    return true;
}

function escapeHTML(value) {
    return String(value || '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function setGreeting() {
    const hour = new Date().getHours();
    const greetingEl = document.getElementById('landing-greeting');
    if (!greetingEl) return;

    if (hour < 12) {
        greetingEl.textContent = 'Morning listening lands better when the next chapter is ready for you. Step into your personal shelf with zero distractions.';
    } else if (hour < 18) {
        greetingEl.textContent = 'Afternoons move faster when your next standout story is kept close. Enjoy uninterrupted offline-ready listening in your browser.';
    } else {
        greetingEl.textContent = 'Evenings deserve immersive stories, quiet atmosphere, and a shelf worth returning to. Pick up right where you left off.';
    }
}

function pickFeaturedBook(books = []) {
    return [...books]
        .filter((book) => book?.cover && book?.title)
        .sort((left, right) => {
            const chapterDiff = Number(right.totalChapters || 0) - Number(left.totalChapters || 0);
            if (chapterDiff) return chapterDiff;
            return String(left.title || '').localeCompare(String(right.title || ''));
        })[0] || books[0] || null;
}

function renderHeroStats(books) {
    const statsEl = document.getElementById('hero-stats');
    if (!statsEl) return;

    const genreCount = new Set(books.map((book) => String(book.genre || '').trim()).filter(Boolean)).size;
    const chapterCount = books.reduce((sum, book) => sum + Number(book.totalChapters || 0), 0);
    const offlineReady = window.VibePWA?.isOfflineShellLikelyReady?.() ? 'Ready' : 'Warming';

    statsEl.innerHTML = `
        <div class="metric-card">
            <strong>${books.length}</strong>
            <span>Stories ready to play</span>
        </div>
        <div class="metric-card">
            <strong>${chapterCount || 0}</strong>
            <span>Catalog chapters</span>
        </div>
        <div class="metric-card">
            <strong>${genreCount || 'Curated'}</strong>
            <span>Genres &amp; moods</span>
        </div>
        <div class="metric-card">
            <strong>${offlineReady}</strong>
            <span>Browser shelf</span>
        </div>
    `;
}

function renderSpotlight(books) {
    const spotlightEl = document.getElementById('featured-spotlight');
    const coverEl = document.getElementById('featured-cover');
    if (!spotlightEl || !coverEl) return;

    const featuredBook = pickFeaturedBook(books);
    if (!featuredBook) {
        spotlightEl.innerHTML = '<div class="spotlight-kicker">Featured pick</div><h3 class="spotlight-title">Catalog warming up</h3><p class="spotlight-desc">Your standout cover story will appear here as soon as the browser shelf is ready.</p>';
        coverEl.hidden = true;
        return;
    }

    coverEl.hidden = false;
    coverEl.src = featuredBook.cover || './public/icons/logo.png';
    coverEl.alt = featuredBook.title || 'Featured audiobook';

    const moodText = Array.isArray(featuredBook.moods) && featuredBook.moods.length
        ? featuredBook.moods.slice(0, 2).join(' / ')
        : (featuredBook.genre || 'Curated audio story');

    spotlightEl.innerHTML = `
        <div class="spotlight-kicker">${escapeHTML(featuredBook.genre || 'Featured pick')}</div>
        <h3 class="spotlight-title">${escapeHTML(featuredBook.title || 'VibeAudio select')}</h3>
        <p class="spotlight-author">by ${escapeHTML(featuredBook.author || 'Curated author')}</p>
        <p class="spotlight-desc">${escapeHTML(moodText)} atmosphere with ${Number(featuredBook.totalChapters || 0)} chapters ready for listening.</p>
        <div class="spotlight-actions">
            <a href="${APP_URL}" class="solid-btn spotlight-btn" role="button"><svg class="vibe-icon" aria-hidden="true"><use href="#icon-play"></use></svg> Listen now</a>
        </div>
    `;
}

function renderPreviewGrid(books) {
    const previewEl = document.getElementById('library-preview');
    if (!previewEl) return;

    if (!books.length) {
        previewEl.innerHTML = '<div class="empty-preview">The shelf preview is unavailable right now. Refresh once the catalog is reachable.</div>';
        return;
    }

    previewEl.innerHTML = books.slice(0, 4).map((book) => {
        const meta = Array.isArray(book.moods) && book.moods.length
            ? book.moods.slice(0, 2).join(' / ')
            : (book.genre || 'Curated listening');

        return `
            <a href="./src/pages/app.html#library" class="preview-card" role="button" aria-label="Open ${escapeHTML(book.title || 'audiobook')} in library">
                <img src="${escapeHTML(book.cover || './public/icons/logo.png')}" alt="${escapeHTML(book.title || 'Audiobook cover')}">
                <div class="preview-copy">
                    <span class="preview-kicker">${escapeHTML(book.genre || 'Curated')}</span>
                    <strong>${escapeHTML(book.title || 'Untitled')}</strong>
                    <span>${escapeHTML(book.author || 'Unknown author')}</span>
                    <p>${escapeHTML(meta)} · ${Number(book.totalChapters || 0)} parts</p>
                </div>
            </a>
        `;
    }).join('');
}

function renderCategoryTags(books) {
    const tagEl = document.getElementById('category-spotlight');
    if (!tagEl) return;

    const tagCounts = new Map();
    books.forEach((book) => {
        if (book.genre) {
            const genre = String(book.genre);
            tagCounts.set(genre, (tagCounts.get(genre) || 0) + 2);
        }
        (book.moods || []).forEach((mood) => {
            const label = String(mood);
            tagCounts.set(label, (tagCounts.get(label) || 0) + 1);
        });
    });

    const picked = Array.from(tagCounts.entries())
        .sort((left, right) => right[1] - left[1])
        .map(([label]) => label)
        .filter(Boolean)
        .slice(0, 10);
    if (!picked.length) {
        tagEl.innerHTML = '<span>Late-night listening</span><span>Slow-burn fantasy</span><span>Comfort replay</span>';
        return;
    }

    tagEl.innerHTML = picked.map((tag) => `<span>${escapeHTML(tag)}</span>`).join('');
}

function bindScrollActions() {
    document.querySelectorAll('[data-open-auth="true"]').forEach((button) => {
        if (button.dataset.boundScroll === 'true') return;
        button.dataset.boundScroll = 'true';
        button.addEventListener('click', async () => {
            if (!navigator.onLine) {
                const redirected = await openOfflineShelfIfReady();
                if (!redirected) {
                    const statusEl = document.getElementById('auth-status');
                    if (statusEl) {
                        statusEl.classList.add('is-ready');
                        statusEl.textContent = 'Offline shelf is warming up. Open the app once online, then it will launch here offline too.';
                    }
                }
                return;
            }
            document.getElementById('auth-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });

    document.querySelectorAll('[data-scroll-target]').forEach((button) => {
        if (button.dataset.boundTarget === 'true') return;
        button.dataset.boundTarget = 'true';
        button.addEventListener('click', () => {
            const target = document.querySelector(button.dataset.scrollTarget || '');
            target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });
}

async function bootAuthPanel() {
    const signInContainer = document.getElementById('sign-in-container');
    const statusEl = document.getElementById('auth-status');
    if (!signInContainer || !statusEl) return;

    if (!navigator.onLine) {
        const redirected = await openOfflineShelfIfReady();
        statusEl.textContent = redirected
            ? 'Offline mode active. Opening your saved browser shelf.'
            : 'Offline mode active. Your saved shelf will open here once the app shell has been cached.';
        statusEl.classList.add('is-ready');
        return;
    }

    try {
        const currentUser = await getSignedInUser();
        if (currentUser) {
            persistUserProfile(currentUser);
            window.location.replace(APP_URL);
            return;
        }

        statusEl.textContent = 'Sign in to continue your listening position across devices. Or start listening immediately as a guest.';
        statusEl.classList.add('is-ready');

        await mountSignIn(signInContainer, {
            afterSignInUrl: APP_URL,
            afterSignUpUrl: APP_URL,
            appearance: {
                layout: {
                    socialButtonsPlacement: 'top',
                    showOptionalFields: false
                },
                variables: {
                    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, sans-serif',
                    colorPrimary: '#E5A93C',
                    colorText: '#F5F6FA',
                    colorBackground: 'transparent',
                    colorInputBackground: 'rgba(255,255,255,0.06)',
                    colorInputText: '#F5F6FA',
                    borderRadius: '12px'
                },
                elements: {
                    card: 'shadow-none bg-transparent p-0',
                    headerTitle: 'hidden',
                    headerSubtitle: 'hidden',
                    footer: 'hidden'
                }
            }
        });
    } catch (error) {
        console.error('Clerk panel initialization notice:', error);
        statusEl.textContent = 'Sign-in is currently resting. You can start listening immediately using the guest shelf above.';
    }
}

async function initLanding() {
    if (!navigator.onLine && await openOfflineShelfIfReady()) {
        return;
    }

    setGreeting();

    const books = await fetchAllBooks();
    renderHeroStats(books);
    renderSpotlight(books);
    renderPreviewGrid(books);
    renderCategoryTags(books);
    warmOfflinePreview(books);
    bindScrollActions();
    await bootAuthPanel();
}

document.addEventListener('DOMContentLoaded', initLanding);
