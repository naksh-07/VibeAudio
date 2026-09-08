import { fetchUserProgress } from './api.js';
import { applyHistoryTheme, applyLibraryTheme } from './ui-player-helpers.js';
import {
    compareProgressByRecency,
    getProgressPercent,
    getProgressTimestampValue,
    isBookFinishedProgress
} from './progress-model.js';

function escapeHTML(value) {
    return String(value || '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function normalizeCategoryKey(value) {
    return String(value || '')
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '') || 'all';
}

export function getCategoryButtonId(category) {
    return `filter-${normalizeCategoryKey(category)}`;
}

function getDisplayProgressPercent(progressOrBook) {
    if (!progressOrBook) return 0;

    if (typeof progressOrBook.progressPercent === 'number') {
        return Math.max(0, Math.min(100, Math.round(progressOrBook.progressPercent)));
    }

    return getProgressPercent(progressOrBook);
}

function getSavedState(book) {
    if (!book?.savedState) return null;

    return {
        chapterIndex: Number(book.savedState.chapterIndex || 0),
        currentTime: Number(book.savedState.currentTime || 0)
    };
}

function getResumeText(book) {
    const savedState = getSavedState(book);
    if (!savedState) return "";

    if (book.isFinished) return "Listened recently";
    return `Part ${savedState.chapterIndex + 1}`;
}

function getOpenPayload(book) {
    const savedState = getSavedState(book);
    return savedState ? { ...book, savedState } : { ...book };
}

function getOfflineBadgeCopy(book) {
    const summary = book?.offlineSummary;
    if (!summary) return '';

    if (summary.overallStatus === 'downloading') return 'Saving…';
    if (summary.overallStatus === 'queued') return 'Queued';
    if (summary.overallStatus === 'update_available') return 'Update';
    if (summary.overallStatus === 'failed') return 'Retry';
    if (summary.totalDownloadedChapters > 0 || summary.overallStatus === 'downloaded') return 'Ready Offline';
    return '';
}

function getBookAccentLabel(book) {
    if (book?.savedState && !book?.isFinished) {
        return 'Continue';
    }

    if (book?.isFinished) {
        return 'Finished';
    }

    if (book?.genre) {
        return String(book.genre);
    }

    if (Array.isArray(book?.moods) && book.moods.length) {
        return String(book.moods[0]);
    }

    return 'Audiobook';
}

function isYouTubeUrl(url) {
    if (!url) return false;
    return /(?:youtube\.com|youtu\.be)/i.test(String(url));
}

function getSourceTypeBadge(book) {
    if (book?.offlineSummary?.overallStatus === 'downloaded' || book?.isOfflineAvailable) {
        return '<span class="source-type-badge offline-badge"><svg class="vibe-icon vibe-icon-success" aria-hidden="true"><use href="#icon-check"></use></svg> Ready Offline</span>';
    }

    const hasYouTube = (book?.chapters || []).some((c) => isYouTubeUrl(c.url))
        || (book?.chapters_en || []).some((c) => isYouTubeUrl(c.url));

    if (hasYouTube) {
        return '<span class="source-type-badge yt-badge"><svg class="vibe-icon" aria-hidden="true"><use href="#icon-video"></use></svg> YouTube</span>';
    }

    return '<span class="source-type-badge audio-badge"><svg class="vibe-icon" aria-hidden="true"><use href="#icon-headphones"></use></svg> Direct Audio</span>';
}

function createLibraryCard(book, openPlayerCallback, placeholder) {
    const accentLabel = getBookAccentLabel(book);
    const progressPercent = getDisplayProgressPercent(book);
    const savedState = getSavedState(book);
    const progressHTML = savedState ? `
        <div class="card-progress-block">
            <div class="card-progress-track">
                <div class="card-progress-fill" style="width: ${progressPercent}%"></div>
            </div>
            <p class="card-progress-text">${escapeHTML(getResumeText(book))} • ${progressPercent}%</p>
        </div>` : '';

    const offlineBadgeCopy = getOfflineBadgeCopy(book);
    const offlineBadge = offlineBadgeCopy ? `
        <div class="card-offline-badge" data-status="${escapeHTML(book.offlineSummary?.overallStatus || 'downloaded')}">
            ${escapeHTML(offlineBadgeCopy)}
        </div>` : '';

    const activityBadge = savedState || book.isFinished ? `
        <div class="card-activity-badge ${book.isFinished ? 'finished' : 'continue'}">
            ${book.isFinished ? 'Finished' : `Part ${(savedState?.chapterIndex || 0) + 1}`}
        </div>` : '';

    const partsCount = Number(book.totalChapters || book.chapters?.length || book.chapters_en?.length || 1);
    const utilityLine = savedState
        ? `${escapeHTML(book.author)}`
        : `${escapeHTML(book.author)} • ${partsCount} ${partsCount === 1 ? 'part' : 'parts'}`;

    const sourceTypeBadge = getSourceTypeBadge(book);

    const card = document.createElement('div');
    card.className = `book-card ${savedState ? 'has-progress' : ''} ${book.isFinished ? 'is-finished' : ''}`;
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.setAttribute('aria-label', `${book.title} by ${book.author}`);
    card.innerHTML = `
        <div class="book-card-media">
            <img class="lazy-img" src="${placeholder}" data-src="${escapeHTML(book.cover)}" alt="${escapeHTML(book.title)}">
            <div class="book-badge">${partsCount} ${partsCount === 1 ? 'Part' : 'Parts'}</div>
            ${activityBadge}
            ${offlineBadge}
        </div>
        <div class="card-content">
            <div class="card-kicker-row">
                <span class="card-kicker">${escapeHTML(accentLabel)}</span>
                ${sourceTypeBadge}
            </div>
            <h3>${escapeHTML(book.title)}</h3>
            <p class="card-author">${utilityLine}</p>
            ${progressHTML}
        </div>`;

    card.onclick = () => openPlayerCallback(getOpenPayload(book));
    card.onkeydown = (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            openPlayerCallback(getOpenPayload(book));
        }
    };

    return card;
}

function formatUpdatedText(updatedAt) {
    const deltaMs = Date.now() - getProgressTimestampValue({ lastInteractionAt: updatedAt });
    if (!deltaMs || deltaMs < 0) return "Recently";

    const hours = Math.floor(deltaMs / (1000 * 60 * 60));
    if (hours < 1) return "Just now";
    if (hours < 24) return `${hours}h ago`;

    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d ago`;
    return "Earlier";
}

function createHistoryCard(book, progress, openPlayerCallback) {
    const percent = getDisplayProgressPercent(progress);
    const chapterNumber = Number(progress.chapterIndex || 0) + 1;
    const finished = isBookFinishedProgress(progress);

    const card = document.createElement('div');
    card.className = 'history-card';
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.setAttribute('aria-label', `Resume ${book.title}`);
    card.innerHTML = `
        <div class="history-layout">
            <img src="${escapeHTML(book.cover)}" alt="${escapeHTML(book.title)}" loading="lazy" class="history-cover">
            <div class="history-info">
                <h3>${escapeHTML(book.title)}</h3>
                <div class="chapter-badge">
                    <svg class="vibe-icon vibe-icon-sm vibe-icon-accent" aria-hidden="true"><use href="#icon-bookmark"></use></svg>
                    <span>${finished ? 'Finished recently' : `Part ${chapterNumber}`}</span>
                </div>
                <div class="progress-container">
                    <div class="mini-progress-track">
                        <div class="mini-progress-fill" style="width: ${percent}%"></div>
                    </div>
                    <span class="progress-text">${percent}% completed • ${formatUpdatedText(progress.lastInteractionAt)}</span>
                </div>
            </div>
            <div class="history-play-btn" aria-hidden="true"><svg class="vibe-icon vibe-icon-xs" aria-hidden="true"><use href="#icon-play"></use></svg></div>
        </div>`;

    card.onclick = () => {
        openPlayerCallback({
            ...book,
            savedState: {
                chapterIndex: Number(progress.chapterIndex || 0),
                currentTime: Number(progress.currentTime || 0)
            }
        });
    };
    card.onkeydown = (event) => {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        card.click();
    };

    return card;
}

export function renderCategoryFilters(allBooks) {
    const container = document.getElementById('category-filters');
    if (!container) return;

    const counts = new Map([
        ['All', Number.MAX_SAFE_INTEGER],
        ['In Progress', Number.MAX_SAFE_INTEGER - 1],
        ['Downloaded', Number.MAX_SAFE_INTEGER - 2]
    ]);

    allBooks.forEach((book) => {
        if (book.genre) counts.set(book.genre, (counts.get(book.genre) || 0) + 2);
    });

    const orderedCategories = Array.from(counts.entries())
        .sort((left, right) => right[1] - left[1])
        .map(([label]) => label)
        .slice(0, 8);

    container.innerHTML = orderedCategories.map((cat) => `
        <button class="filter-btn ${cat === 'All' ? 'active' : ''}" 
                id="${getCategoryButtonId(cat)}"
                data-category="${escapeHTML(cat)}"
                type="button">
            ${escapeHTML(cat)}
        </button>
    `).join('');
}

export function renderHomeResumeHero(books, openPlayerCallback, options = {}) {
    const container = document.getElementById('home-resume-hero');
    if (!container) return;

    const historyBooks = (Array.isArray(books) ? books : [])
        .filter((book) => book.savedState && !book.isFinished)
        .sort((a, b) => getProgressTimestampValue({ lastInteractionAt: b.lastInteractionAt })
            - getProgressTimestampValue({ lastInteractionAt: a.lastInteractionAt }));

    const lastOpenedState = options.lastOpenedState || null;
    const lastOpenedBook = lastOpenedState?.bookId
        ? (books || []).find((book) => String(book.bookId) === String(lastOpenedState.bookId))
        : null;

    const activeBook = lastOpenedBook || historyBooks[0] || null;
    if (!activeBook) {
        container.classList.add('hidden');
        container.innerHTML = '';
        return;
    }

    const savedState = getSavedState(activeBook);
    const progressPercent = getDisplayProgressPercent(activeBook);
    const chapterNum = (savedState?.chapterIndex || 0) + 1;
    const totalChapters = activeBook.totalChapters || activeBook.chapters?.length || activeBook.chapters_en?.length || 1;
    const isOffline = activeBook.offlineSummary?.overallStatus === 'downloaded' || activeBook.isOfflineAvailable;

    // Remaining time estimate if available
    let timeRemainingCopy = `${progressPercent}% completed`;
    const currentTimeSec = Number(savedState?.currentTime || 0);
    if (currentTimeSec > 0) {
        const estPartMinutes = 20; // fallback standard chapter estimate
        const elapsedMinutes = Math.floor(currentTimeSec / 60);
        const remainingMinutes = Math.max(1, estPartMinutes - elapsedMinutes);
        timeRemainingCopy = `${remainingMinutes} min left in Part ${chapterNum}`;
    }

    container.classList.remove('hidden');
    container.innerHTML = `
        <div class="resume-hero-card">
            <div class="resume-hero-art-wrap">
                <img src="${escapeHTML(activeBook.cover)}" alt="${escapeHTML(activeBook.title)}" class="resume-hero-cover">
                ${isOffline ? '<span class="resume-offline-tag"><svg class="vibe-icon vibe-icon-success" aria-hidden="true"><use href="#icon-check"></use></svg> Ready Offline</span>' : ''}
            </div>
            <div class="resume-hero-content">
                <div class="resume-hero-badges">
                    <span class="personalized-kicker"><svg class="vibe-icon vibe-icon-accent" aria-hidden="true"><use href="#icon-waveform"></use></svg> CONTINUE LISTENING</span>
                </div>
                <h2 class="resume-hero-title">${escapeHTML(activeBook.title)}</h2>
                <p class="resume-hero-author">by ${escapeHTML(activeBook.author)}</p>
                <div class="resume-hero-meta">
                    <span class="resume-chapter-pill">Part ${chapterNum} of ${totalChapters}</span>
                    <span class="resume-pct-label">${escapeHTML(timeRemainingCopy)}</span>
                </div>
                <div class="resume-track">
                    <div class="resume-track-fill" style="width: ${progressPercent}%"></div>
                </div>
                <div class="resume-hero-actions">
                    <button class="action-btn resume-main-btn" type="button" data-resume-hero="true" aria-label="Resume listening">
                        <svg class="vibe-icon" aria-hidden="true"><use href="#icon-play"></use></svg> Resume Listening
                    </button>
                    <button class="ghost-btn resume-chapters-btn" type="button" data-open-chapters="true" aria-label="View chapters">
                        <svg class="vibe-icon" aria-hidden="true"><use href="#icon-chapters"></use></svg> Chapters
                    </button>
                </div>
            </div>
        </div>
    `;

    const resumeBtn = container.querySelector('[data-resume-hero="true"]');
    if (resumeBtn) {
        resumeBtn.onclick = () => {
            openPlayerCallback(getOpenPayload(activeBook));
        };
    }

    const chaptersBtn = container.querySelector('[data-open-chapters="true"]');
    if (chaptersBtn) {
        chaptersBtn.onclick = () => {
            openPlayerCallback(getOpenPayload(activeBook));
        };
    }
}

export function renderHomeOfflineShelf(offlineBooks = [], openPlayerCallback) {
    const section = document.getElementById('home-offline-shelf');
    const grid = document.getElementById('home-offline-grid');
    if (!section || !grid) return;

    const books = Array.isArray(offlineBooks) ? offlineBooks.filter((b) => b && (b.totalDownloadedChapters > 0 || b.isOfflineAvailable || b.offlineSummary?.totalDownloadedChapters > 0)) : [];
    if (!books.length) {
        section.classList.add('hidden');
        grid.innerHTML = '';
        return;
    }

    section.classList.remove('hidden');
    grid.innerHTML = books.map((book) => {
        const partsCount = book.offlineSummary?.totalDownloadedChapters || book.totalDownloadedChapters || book.totalChapters || 1;
        return `
            <div class="horizontal-shelf-card" data-offline-book-id="${escapeHTML(book.bookId)}" role="button" tabindex="0" aria-label="${escapeHTML(book.title)}">
                <div class="shelf-card-cover-wrap">
                    <img src="${escapeHTML(book.cover || '')}" alt="${escapeHTML(book.title)}" loading="lazy">
                    <span class="shelf-offline-badge"><svg class="vibe-icon vibe-icon-success" aria-hidden="true"><use href="#icon-check"></use></svg> Ready Offline</span>
                </div>
                <div class="shelf-card-info">
                    <h4>${escapeHTML(book.title)}</h4>
                    <p>${escapeHTML(book.author)} • ${partsCount} ${partsCount === 1 ? 'part' : 'parts'}</p>
                </div>
            </div>
        `;
    }).join('');

    grid.querySelectorAll('[data-offline-book-id]').forEach((card) => {
        card.onclick = () => {
            const bookId = card.dataset.offlineBookId;
            const book = books.find((item) => String(item.bookId) === String(bookId));
            if (book) openPlayerCallback(getOpenPayload(book));
        };
        card.onkeydown = (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                card.click();
            }
        };
    });
}

export function renderHomeCuratedShelf(books = [], openPlayerCallback) {
    const section = document.getElementById('home-curated-shelf');
    const grid = document.getElementById('home-curated-grid');
    if (!section || !grid) return;

    const curatedPicks = (Array.isArray(books) ? books : [])
        .filter((book) => !book.savedState || book.isFinished)
        .slice(0, 3);

    if (!curatedPicks.length) {
        section.classList.add('hidden');
        grid.innerHTML = '';
        return;
    }

    section.classList.remove('hidden');
    grid.innerHTML = curatedPicks.map((book) => `
        <div class="discovery-card" data-curated-book-id="${escapeHTML(book.bookId)}" role="button" tabindex="0" aria-label="${escapeHTML(book.title)}">
            <img src="${escapeHTML(book.cover)}" alt="${escapeHTML(book.title)}" loading="lazy">
            <div class="discovery-info">
                <strong>${escapeHTML(book.title)}</strong>
                <span>${escapeHTML(book.author)} • ${escapeHTML(book.genre || 'Curated Pick')}</span>
            </div>
        </div>
    `).join('');

    grid.querySelectorAll('[data-curated-book-id]').forEach((card) => {
        card.onclick = () => {
            const bookId = card.dataset.curatedBookId;
            const book = books.find((item) => String(item.bookId) === String(bookId));
            if (book) openPlayerCallback(getOpenPayload(book));
        };
        card.onkeydown = (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                card.click();
            }
        };
    });
}

export function renderHomeEmptyState(hasActiveContent = false) {
    const emptyEl = document.getElementById('home-empty-state');
    if (!emptyEl) return;

    emptyEl.classList.toggle('hidden', hasActiveContent);
}

export function renderLibrary(books, openPlayerCallback) {
    const grid = document.getElementById('book-grid');
    if (!grid) return;

    if (!books.length) {
        grid.innerHTML = '<div class="empty-state"><p>No audiobooks matched this search. Try a different title, author, or filter.</p></div>';
        return;
    }

    applyLibraryTheme(null, true);

    const placeholder = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
    grid.innerHTML = '';

    books.forEach((book) => {
        const card = createLibraryCard(book, openPlayerCallback, placeholder);
        grid.appendChild(card);

        const img = card.querySelector('img');
        if (window.imageObserver) window.imageObserver.observe(img);
    });

    if (window.matchMedia("(min-width: 768px)").matches && window.VanillaTilt) {
        window.VanillaTilt.init(document.querySelectorAll("#book-grid .book-card"), {
            max: 4, speed: 300, glare: false, scale: 1.01
        });
    }
}

export function renderRecentSearches(searches = []) {
    const panel = document.getElementById('recent-searches-panel');
    if (!panel) return;

    const items = Array.isArray(searches) ? searches.filter(Boolean) : [];
    if (!items.length) {
        panel.innerHTML = '';
        panel.classList.add('hidden');
        return;
    }

    panel.classList.remove('hidden');
    panel.innerHTML = `
        <div class="recent-searches-header">
            <span>Recent Searches</span>
            <button class="clear-recent-btn" type="button" data-clear-recent="true" aria-label="Clear recent searches">Clear</button>
        </div>
        <div class="recent-searches-tags">
            ${items.map((query) => `
                <button class="recent-search-tag" type="button" data-query="${escapeHTML(query)}">${escapeHTML(query)}</button>
            `).join('')}
        </div>
    `;
}

export function renderOfflineShelf(books, openPlayerCallback) {
    const grid = document.getElementById('offline-grid');
    if (!grid) return;

    if (!books.length) {
        grid.innerHTML = '<div class="empty-state"><p>Nothing saved here yet. Save an audiobook from the library and it will be ready whenever you are.</p></div>';
        return;
    }

    const placeholder = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
    grid.innerHTML = '';

    books.forEach((book) => {
        const card = createLibraryCard(book, openPlayerCallback, placeholder);
        grid.appendChild(card);

        const img = card.querySelector('img');
        if (window.imageObserver) window.imageObserver.observe(img);
    });
}

export async function renderHistory(allBooks, openPlayerCallback, historyData = null) {
    const grid = document.getElementById('history-grid');
    if (!grid) return;

    grid.innerHTML = '<div class="loading-spinner">Loading listening history...</div>';

    try {
        const history = Array.isArray(historyData) ? historyData : await fetchUserProgress();
        const sortedHistory = [...history].sort(compareProgressByRecency);

        if (!sortedHistory.length) {
            grid.innerHTML = '<p class="empty-msg">No listening history yet. Start your first audiobook to see it here.</p>';
            return;
        }

        grid.innerHTML = '';
        sortedHistory.forEach((progress) => {
            const book = allBooks.find((item) => String(item.bookId) === String(progress.bookId));
            if (!book) return;

            grid.appendChild(createHistoryCard(book, progress, openPlayerCallback));
        });

        applyHistoryTheme(null, document.body?.dataset.themeSurface === 'history');
    } catch (error) {
        console.error("History Render Error:", error);
        grid.innerHTML = '<p class="empty-msg">Unable to load history right now.</p>';
    }
}
