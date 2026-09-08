import {
    fetchAllBooks,
    fetchUserProgress,
    flushPendingProgressQueue,
    getLocalUserProfile,
    invalidateProgressCache,
    syncUserProfile,
    saveUserProgress
} from './api.js';
import {
    buildOfflineBookFromSummary,
    clearAllOfflineDownloads,
    getOfflineStorageStats,
    importAudiobookFile,
    listOfflineBooks,
    resumePendingDownloads
} from './offline-shelf.js';
import { togglePlay, nextChapter, prevChapter, skip, seekTo, getCurrentState } from './player.js';
import * as LibraryUI from './ui-library.js';
import { openPlayerUI, updateUI } from './ui-player-main.js';
import { STORAGE_KEYS, SYNC_STATES } from './config.js';
import { formatTime, refreshThemeColors, renderSingleComment, setActiveThemeSurface, showToast } from './ui-player-helpers.js';
import { signOutCurrentUser } from './auth.js';
import { injectUiRuntimeStyles, setupImageObserver } from './ui-dom.js';
import { formatRelativeTime } from './ui-formatters.js';
import { renderLibraryInsightsPanel } from './ui-library-insights.js';
import {
    addPersistentComment,
    buildProfileSnapshot,
    getCatalogSnapshot,
    getCurrentUserName,
    getLastOpenedBook,
    getLastPlayerSession,
    getSyncStatus,
    getRecentSearches,
    clearRecentSearches,
    pushRecentSearch
} from './user-data.js';
import {
    compareProgressByRecency,
    getProgressPercent,
    getProgressTimestampValue,
    isBookFinishedProgress
} from './progress-model.js';

let allBooks = [];
let userHistory = [];
let offlineShelfSummaries = [];
let offlineStorageStats = null;
let currentViewId = 'home';
let currentCategory = 'All';
let currentSearchQuery = '';
let closeSidebarIfOpen = () => false;
let hasInitialized = false;
let offlineRefreshQueued = false;

const VALID_VIEWS = new Set(['home', 'library', 'history', 'offline', 'about', 'profile', 'player']);

function sortCatalogBooks(books) {
    return (Array.isArray(books) ? books : [])
        .slice()
        .sort((a, b) => {
            const numA = parseInt(String(a.bookId || '').replace(/\D/g, ''), 10) || 0;
            const numB = parseInt(String(b.bookId || '').replace(/\D/g, ''), 10) || 0;
            return numA - numB;
        })
        .map((book, index) => ({ ...book, catalogOrder: index }));
}

function getResolvedTheme() {
    try {
        const stored = localStorage.getItem(STORAGE_KEYS.theme);
        if (stored === 'light' || stored === 'dark') return stored;
    } catch (e) {}
    if (typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
        return 'light';
    }
    return 'dark';
}

function updateThemeUI(theme) {
    if (typeof document === 'undefined') return;
    const isLight = theme === 'light';

    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const themeToggleIcon = document.getElementById('theme-toggle-icon');
    if (themeToggleBtn) {
        themeToggleBtn.setAttribute('aria-label', isLight ? 'Switch to dark theme' : 'Switch to daylight theme');
        themeToggleBtn.setAttribute('title', isLight ? 'Switch to dark theme' : 'Switch to daylight theme');
    }
    if (themeToggleIcon) {
        themeToggleIcon.setAttribute('href', isLight ? '#icon-moon' : '#icon-sun');
    }

    const sidebarToggleIcon = document.getElementById('sidebar-theme-toggle-icon');
    const sidebarToggleLabel = document.getElementById('sidebar-theme-toggle-label');
    if (sidebarToggleIcon) {
        sidebarToggleIcon.setAttribute('href', isLight ? '#icon-moon' : '#icon-sun');
    }
    if (sidebarToggleLabel) {
        sidebarToggleLabel.textContent = isLight ? 'Dark Obsidian' : 'Daylight Mode';
    }

    document.querySelectorAll('.theme-choice-btn').forEach((btn) => {
        const matches = btn.dataset.themeChoice === theme;
        btn.classList.toggle('active', matches);
        btn.setAttribute('aria-checked', String(matches));
    });

    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
        meta.setAttribute('content', isLight ? '#F8F6F1' : '#0C0D11');
    }
}

export function applyTheme(theme, persist = true) {
    if (typeof document === 'undefined') return theme;
    const nextTheme = theme === 'light' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', nextTheme);

    if (persist) {
        try {
            localStorage.setItem(STORAGE_KEYS.theme, nextTheme);
        } catch (e) {}
    }

    updateThemeUI(nextTheme);
    refreshThemeColors();
    return nextTheme;
}

export function toggleTheme() {
    if (typeof document === 'undefined') return 'dark';
    const current = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
    const next = current === 'light' ? 'dark' : 'light';
    applyTheme(next, true);
    showToast(next === 'light' ? 'Warm Daylight sanctuary active' : 'Dark Obsidian sanctuary active');
    return next;
}

function renderSyncState(status = getSyncStatus()) {
    const banners = [
        document.getElementById('library-sync-banner'),
        document.getElementById('history-sync-banner')
    ].filter(Boolean);
    const profileNote = document.getElementById('profile-sync-note');
    const pendingCount = Number(status.pendingCount || 0);

    let message = 'Shelf synced. Your next listening session is ready to pick up cleanly.';
    if (status.status === SYNC_STATES.offline) {
        message = pendingCount > 0
            ? `Offline mode active. ${pendingCount} listening update${pendingCount === 1 ? '' : 's'} will sync later, while your saved shelf stays available.`
            : 'Offline mode active. Showing the shelf saved on this device.';
    } else if (status.status === SYNC_STATES.pending) {
        message = pendingCount > 0
            ? `${pendingCount} listening update${pendingCount === 1 ? '' : 's'} still need sync. Continue listening is using fresher device data.`
            : 'This device is slightly ahead of the cloud and will sync shortly.';
    } else if (status.lastSuccessfulSyncAt) {
        message = `Synced ${formatRelativeTime(status.lastSuccessfulSyncAt)}. Continue listening reflects your latest unfinished story.`;
    }

    banners.forEach((banner) => {
        banner.classList.remove('hidden');
        banner.dataset.status = status.status;
        banner.textContent = message;
    });

    if (profileNote) {
        profileNote.dataset.status = status.status;
        profileNote.textContent = message;
    }

    // New global indicator logic
    const indicator = document.getElementById('global-sync-indicator');
    if (!indicator) return;

    let indicatorText = 'Synced';
    let indicatorIconName = 'check-circle';
    let indicatorIconExtra = 'vibe-icon-success';
    let indicatorTitle = `Last synced: ${formatRelativeTime(status.lastSuccessfulSyncAt)}`;

    if (status.status === SYNC_STATES.offline) {
        indicatorText = pendingCount > 0 ? `Offline (${pendingCount})` : 'Offline';
        indicatorIconName = 'wifi-off';
        indicatorIconExtra = 'vibe-icon-dim';
        indicatorTitle = 'Offline. Click to attempt sync.';
    } else if (status.status === SYNC_STATES.pending) {
        indicatorText = `Syncing (${pendingCount})...`;
        indicatorIconName = 'sync';
        indicatorIconExtra = 'spin vibe-icon-accent';
        indicatorTitle = `${pendingCount} updates pending sync.`;
    } else if (!status.lastSuccessfulSyncAt) {
        indicatorText = 'Synced';
        indicatorIconName = 'check-circle';
        indicatorIconExtra = 'vibe-icon-success';
        indicatorTitle = 'Shelf is synced with the cloud.';
    }

    indicator.dataset.status = status.status;
    indicator.title = indicatorTitle;
    indicator.innerHTML = `<svg class="vibe-icon ${indicatorIconExtra}" aria-hidden="true"><use href="#icon-${indicatorIconName}"></use></svg> <span>${indicatorText}</span>`;
}

function getBookSignals(book) {
    const signals = [];

    if (book.genre) {
        signals.push({ key: String(book.genre).toLowerCase(), label: String(book.genre), weight: 1.8 });
    }

    (book.moods || []).forEach((mood) => {
        signals.push({ key: String(mood).toLowerCase(), label: String(mood), weight: 1.1 });
    });

    return signals;
}

function enrichBooksWithHistory(books, history) {
    const sortedHistory = [...history].sort(compareProgressByRecency);
    const historyByBook = new Map();

    sortedHistory.forEach((entry, index) => {
        const key = String(entry.bookId);
        if (!historyByBook.has(key)) {
            historyByBook.set(key, { ...entry, historyRank: index });
        }
    });

    const tasteProfile = new Map();
    books.forEach((book) => {
        const progress = historyByBook.get(String(book.bookId));
        if (!progress) return;

        const progressPercent = getProgressPercent(progress);
        const recencyWeight = Math.max(0.6, 1.7 - (progress.historyRank * 0.14));
        const depthWeight = 1 + (progressPercent / 100);
        const baseWeight = recencyWeight + depthWeight;

        getBookSignals(book).forEach((signal) => {
            tasteProfile.set(signal.key, (tasteProfile.get(signal.key) || 0) + (baseWeight * signal.weight));
        });
    });

    return books
        .map((book) => {
            const progress = historyByBook.get(String(book.bookId));
            const progressPercent = getProgressPercent(progress);
            const savedState = progress ? {
                chapterIndex: Number(progress.chapterIndex || 0),
                currentTime: Number(progress.currentTime || 0)
            } : null;
            const matchingSignals = getBookSignals(book)
                .filter((signal) => tasteProfile.has(signal.key))
                .sort((a, b) => (tasteProfile.get(b.key) || 0) - (tasteProfile.get(a.key) || 0));
            const preferenceScore = matchingSignals.reduce((sum, signal) => sum + (tasteProfile.get(signal.key) || 0), 0);
            const isFinished = isBookFinishedProgress(progress);
            const progressBoost = savedState && !isFinished ? 1600 + progressPercent : 0;
            const hasRecommendationMatch = preferenceScore > 0;

            return {
                ...book,
                savedState,
                progressPercent,
                lastInteractionAt: progress?.lastInteractionAt || null,
                historyRank: progress?.historyRank ?? Number.MAX_SAFE_INTEGER,
                isFinished,
                personalizedScore: progressBoost + preferenceScore + (isFinished ? 40 : 0),
                rankingBucket: savedState && !isFinished
                    ? 0
                    : hasRecommendationMatch && !savedState
                        ? 1
                        : !savedState
                            ? 2
                            : 3,
                recommendationReason: matchingSignals[0]?.label || '',
                topReasons: matchingSignals.slice(0, 3).map((signal) => signal.label)
            };
        })
        .sort((a, b) => {
            const bucketDiff = (a.rankingBucket || 0) - (b.rankingBucket || 0);
            if (bucketDiff) return bucketDiff;

            if (a.rankingBucket === 0 && b.rankingBucket === 0) {
                const recencyDiff = getProgressTimestampValue({ lastInteractionAt: b.lastInteractionAt })
                    - getProgressTimestampValue({ lastInteractionAt: a.lastInteractionAt });
                if (recencyDiff) return recencyDiff;
            }

            const scoreDiff = (b.personalizedScore || 0) - (a.personalizedScore || 0);
            if (scoreDiff) return scoreDiff;

            const recencyDiff = getProgressTimestampValue({ lastInteractionAt: b.lastInteractionAt })
                - getProgressTimestampValue({ lastInteractionAt: a.lastInteractionAt });
            if (recencyDiff) return recencyDiff;

            return (a.catalogOrder || 0) - (b.catalogOrder || 0);
        });
}

function applyOfflineSummariesToBooks(books, summaries = offlineShelfSummaries) {
    const summaryMap = new Map((Array.isArray(summaries) ? summaries : []).map((summary) => [String(summary.bookId), summary]));

    return (Array.isArray(books) ? books : []).map((book) => {
        const offlineSummary = summaryMap.get(String(book.bookId)) || null;
        return {
            ...book,
            offlineSummary,
            isOfflineAvailable: Boolean(offlineSummary?.totalDownloadedChapters)
        };
    });
}

function buildOfflineRenderableBooks() {
    const catalogMap = new Map(allBooks.map((book) => [String(book.bookId), book]));

    return offlineShelfSummaries.map((summary) => {
        const catalogBook = catalogMap.get(String(summary.bookId));
        const offlineBook = buildOfflineBookFromSummary(summary);
        return applyOfflineSummariesToBooks([
            catalogBook
                ? { ...catalogBook, ...offlineBook }
                : {
                    ...(offlineBook || {}),
                    bookId: summary.bookId,
                    title: summary.title,
                    author: summary.author,
                    cover: summary.cover,
                    totalChapters: summary.totalChapters
                }
        ], [summary])[0];
    });
}

function toAbsoluteUrl(value) {
    try {
        return new URL(String(value || ''), window.location.href).href;
    } catch (error) {
        return '';
    }
}

function warmOfflineCatalog(books = allBooks) {
    const bridge = window.VibePWA;
    if (!bridge?.primeOfflineResources) return;

    const prioritizedBooks = [];
    const seenBookIds = new Set();
    const pushBook = (book) => {
        if (!book?.bookId) return;
        const key = String(book.bookId);
        if (seenBookIds.has(key)) return;
        seenBookIds.add(key);
        prioritizedBooks.push(book);
    };

    const lastSession = getLastPlayerSession() || getLastOpenedBook();
    if (lastSession?.bookId) {
        pushBook((books || []).find((book) => String(book.bookId) === String(lastSession.bookId)));
    }

    // 2. Proactively cache top 3 personalized recommendations (unstarted books)
    const personalizedPicks = (Array.isArray(books) ? books : [])
        .filter(book => !book.savedState && book.personalizedScore > 0)
        .slice(0, 3);
    personalizedPicks.forEach(pushBook);

    // 3. Cache top 3 "continue listening" books (excluding last active one if already added)
    const continueListening = (Array.isArray(books) ? books : [])
        .filter(book => book.savedState && !book.isFinished);
    continueListening.slice(0, 3).forEach(pushBook);

    // 4. Cache any already downloaded books to keep them warm
    buildOfflineRenderableBooks().slice(0, 6).forEach(pushBook);
    // 5. Fallback: cache first few books from general catalog if list is still short
    (Array.isArray(books) ? books : []).slice(0, 5).forEach(pushBook);
    const urls = [
        '../../index.html',
        '../../app.webmanifest',
        '../pages/app.html',
        ...prioritizedBooks.flatMap((book) => [book?.dataPath, book?.cover])
    ]
        .map(toAbsoluteUrl)
        .filter(Boolean);

    void bridge.primeOfflineResources(urls);
}

function matchesBookFilters(book) {
    const query = currentSearchQuery.trim().toLowerCase();
    if (query) {
        const title = String(book.title || '').toLowerCase();
        const author = String(book.author || '').toLowerCase();
        const genre = String(book.genre || '').toLowerCase();
        const moods = (book.moods || []).join(' ').toLowerCase();

        if (!title.includes(query) && !author.includes(query) && !genre.includes(query) && !moods.includes(query)) {
            return false;
        }
    }

    if (currentCategory === 'All') return true;
    return book.genre === currentCategory || Boolean(book.moods?.includes(currentCategory));
}

function getVisibleBooks() {
    return allBooks.filter(matchesBookFilters);
}

function openBookFromCollection(book) {
    openPlayerUI(book, allBooks, switchView);
}

function renderHomeSurfaces() {
    const historyBooks = (Array.isArray(allBooks) ? allBooks : []).filter((book) => book.savedState && !book.isFinished);
    const lastOpenedState = getLastOpenedBook();
    const hasActiveListening = Boolean(lastOpenedState?.bookId || historyBooks.length > 0);

    LibraryUI.renderHomeResumeHero(allBooks, openBookFromCollection, {
        lastOpenedState,
        syncStatus: getSyncStatus()
    });

    const offlineBooks = buildOfflineRenderableBooks();
    LibraryUI.renderHomeOfflineShelf(offlineBooks, openBookFromCollection);
    LibraryUI.renderHomeCuratedShelf(allBooks, openBookFromCollection);
    LibraryUI.renderHomeEmptyState(hasActiveListening || offlineBooks.length > 0);
}

function renderLibrarySurfaces() {
    LibraryUI.renderCategoryFilters(allBooks);
    LibraryUI.renderLibrary(getVisibleBooks(), openBookFromCollection);
    LibraryUI.renderRecentSearches(getRecentSearches());
}

function queueOfflineShelfRefresh() {
    if (offlineRefreshQueued) return;
    offlineRefreshQueued = true;

    window.setTimeout(async () => {
        offlineRefreshQueued = false;
        await refreshOfflineShelfState();
        if (currentViewId === 'home') {
            renderHomeSurfaces();
        } else {
            renderLibrarySurfaces();
        }
    }, 180);
}

async function refreshOfflineShelfState() {
    try {
        const [summaries, stats] = await Promise.all([
            listOfflineBooks(),
            getOfflineStorageStats()
        ]);

        offlineShelfSummaries = Array.isArray(summaries) ? summaries : [];
        offlineStorageStats = stats;
        allBooks = applyOfflineSummariesToBooks(allBooks, offlineShelfSummaries);
        warmOfflineCatalog(allBooks);
    } catch (error) {
        console.warn("Unable to refresh offline shelf state.", error);
        offlineShelfSummaries = [];
        offlineStorageStats = null;
    }

    renderOfflineView();
    renderProfileStoragePanel();
}

async function refreshPersonalizedCatalog() {
    try {
        userHistory = await fetchUserProgress();
    } catch (error) {
        console.warn("Unable to refresh user history.", error);
        userHistory = [];
    }

    allBooks = applyOfflineSummariesToBooks(enrichBooksWithHistory(allBooks, userHistory), offlineShelfSummaries);
    renderHomeSurfaces();
    renderLibrarySurfaces();
    LibraryUI.renderHistory(allBooks, openBookFromCollection, userHistory);
    renderProfileSnapshot();
    renderSyncState();
}

function renderLibraryInsights() {
    renderLibraryInsightsPanel({
        currentSearchQuery,
        currentCategory,
        allBooks,
        visibleBooks: getVisibleBooks(),
        userHistory,
        isBookFinishedProgress
    });
}

function renderProfileSnapshot() {
    const snapshot = buildProfileSnapshot(userHistory, allBooks);

    const finishedEl = document.getElementById('profile-stat-finished');
    const hoursEl = document.getElementById('profile-stat-hours');
    const activeEl = document.getElementById('profile-stat-active');
    const bookmarksEl = document.getElementById('profile-stat-bookmarks');
    const summaryEl = document.getElementById('profile-summary-copy');
    const genreEl = document.getElementById('profile-top-genre');

    if (finishedEl) finishedEl.innerText = String(snapshot.finishedBooks);
    if (hoursEl) hoursEl.innerText = `${snapshot.totalHours.toFixed(snapshot.totalHours >= 10 ? 0 : 1)}h`;
    if (activeEl) activeEl.innerText = String(snapshot.activeBooks);
    if (bookmarksEl) bookmarksEl.innerText = String(snapshot.bookmarkCount);
    if (summaryEl) summaryEl.innerText = snapshot.summary;
    if (genreEl) genreEl.innerText = `Top lane: ${snapshot.topGenre}`;

    renderProfileStoragePanel();
    updateThemeUI(document.documentElement.getAttribute('data-theme') || 'dark');
}

function renderProfileStoragePanel() {
    const usedEl = document.getElementById('offline-storage-used');
    const quotaEl = document.getElementById('offline-storage-quota');
    const booksEl = document.getElementById('offline-storage-books');
    const chaptersEl = document.getElementById('offline-storage-chapters');
    const modeEl = document.getElementById('offline-storage-mode');
    const clearBtn = document.getElementById('clear-offline-downloads-btn');

    if (!usedEl || !quotaEl || !booksEl || !chaptersEl || !modeEl) return;

    const usedBytes = Number(offlineStorageStats?.downloadedBytes || 0);
    const quotaBytes = Number(offlineStorageStats?.browserQuotaBytes || 0);
    const formatSize = (value) => {
        if (!value) return '0 MB';
        if (value >= 1024 ** 3) return `${(value / (1024 ** 3)).toFixed(1)} GB`;
        return `${Math.max(0.1, value / (1024 ** 2)).toFixed(value >= 1024 ** 2 ? 1 : 0)} MB`;
    };

    usedEl.innerText = formatSize(usedBytes);
    quotaEl.innerText = quotaBytes ? formatSize(quotaBytes) : 'Browser managed';
    booksEl.innerText = String(offlineStorageStats?.downloadedBooks || 0);
    chaptersEl.innerText = String(offlineStorageStats?.downloadedChapters || 0);
    modeEl.innerText = offlineStorageStats?.storageMode === 'opfs' ? 'High-Performance Private Storage' : 'Secure Browser Storage';

    if (clearBtn) {
        clearBtn.disabled = !(offlineStorageStats?.downloadedBooks || offlineStorageStats?.pendingJobs);
    }
}

function renderOfflineView() {
    const subtitle = document.getElementById('offline-subtitle');
    const stats = document.getElementById('offline-insights');
    const offlineBooks = buildOfflineRenderableBooks();

    const downloadedBooks = Number(offlineStorageStats?.downloadedBooks || offlineBooks.length || 0);
    const downloadedChapters = Number(offlineStorageStats?.downloadedChapters || 0);
    const downloadedBytes = Number(offlineStorageStats?.downloadedBytes || 0);
    const pendingJobs = Number(offlineStorageStats?.pendingJobs || 0);

    const formatSize = (value) => {
        if (!value) return '0 MB';
        if (value >= 1024 ** 3) return `${(value / (1024 ** 3)).toFixed(1)} GB`;
        return `${Math.max(0.1, value / (1024 ** 2)).toFixed(value >= 1024 ** 2 ? 1 : 0)} MB`;
    };
    const sizeFormatted = formatSize(downloadedBytes);

    if (subtitle) {
        if (!offlineBooks.length) {
            subtitle.textContent = 'Save direct-audio stories from the player and they will gather here for offline listening.';
        } else {
            subtitle.textContent = `${downloadedBooks} ${downloadedBooks === 1 ? 'story' : 'stories'} · ${downloadedChapters} ${downloadedChapters === 1 ? 'chapter' : 'chapters'} · ${sizeFormatted} stored locally`;
        }
    }

    if (stats) {
        if (downloadedBooks > 0 || downloadedChapters > 0 || pendingJobs > 0) {
            stats.classList.remove('hidden');
            stats.innerHTML = `
                <div class="offline-summary-bar">
                    <div class="offline-summary-metric">
                        <span class="offline-metric-primary"><svg class="vibe-icon vibe-icon-success" style="color: var(--color-success);" aria-hidden="true"><use href="#icon-check-circle"></use></svg> ${downloadedBooks} ${downloadedBooks === 1 ? 'story' : 'stories'} · ${downloadedChapters} ${downloadedChapters === 1 ? 'chapter' : 'chapters'}</span>
                        <span class="offline-metric-secondary">${sizeFormatted} stored locally</span>
                    </div>
                    ${pendingJobs > 0 ? `<div class="offline-summary-badge"><svg class="vibe-icon spin" aria-hidden="true"><use href="#icon-cloud-download"></use></svg> ${pendingJobs} in queue</div>` : ''}
                </div>
            `;
        } else {
            stats.innerHTML = '';
            stats.classList.add('hidden');
        }
    }

    LibraryUI.renderOfflineShelf(offlineBooks, openBookFromCollection);
}

function restorePlayerSessionIfNeeded() {
    if (currentViewId !== 'player') return;

    const session = getLastPlayerSession() || getLastOpenedBook();
    if (!session?.bookId) {
        switchView('home', false);
        return;
    }

    const book = allBooks.find((item) => String(item.bookId) === String(session.bookId));
    const fallbackOfflineBook = buildOfflineRenderableBooks().find((item) => String(item.bookId) === String(session.bookId));
    const resolvedBook = book || fallbackOfflineBook;

    if (!resolvedBook) {
        switchView('home', false);
        return;
    }

    openPlayerUI({
        ...resolvedBook,
        savedState: {
            chapterIndex: Number(session.chapterIndex || 0),
            currentTime: Number(session.currentTime || 0)
        }
    }, allBooks, (viewId) => switchView(viewId, false));
}

window.app = {
    switchView: (id) => switchView(id),
    goBack: () => goBackInApp(),
    filterLibrary: (category) => filterLibraryLogic(category),
    toggleTheme: () => toggleTheme(),
    setTheme: (theme) => applyTheme(theme, true),

    togglePlay: () => {
        const isPlaying = togglePlay();
        updateUI(isPlaying);
    },

    nextChapter: () => {
        if (nextChapter()) updateUI(false);
    },

    prevChapter: () => {
        if (prevChapter()) updateUI(false);
    },

    seekToComment: (time) => {
        const state = getCurrentState();
        if (!state.duration) return;

        seekTo((time / state.duration) * 100);
        if (!state.isPlaying) {
            const isPlaying = togglePlay();
            updateUI(isPlaying);
        }
    },

    syncData: async () => {
        const btn = document.getElementById('sync-profile-btn') || document.querySelector('.btn-secondary');
        if (!btn) return;

        if (!navigator.onLine) {
            showToast("Offline mode is active. Sync will resume when the browser reconnects.");
            renderSyncState();
            return;
        }

        const originalText = btn.innerHTML;

        btn.innerHTML = `<svg class="vibe-icon spin" aria-hidden="true"><use href="#icon-sync"></use></svg> Syncing...`;
        btn.disabled = true;

        await syncUserProfile();
        await flushPendingProgressQueue();
        invalidateProgressCache();
        await refreshPersonalizedCatalog();

        btn.innerHTML = `<svg class="vibe-icon vibe-icon-success" aria-hidden="true"><use href="#icon-check"></use></svg> Synced!`;
        btn.style.borderColor = "#00ff00";
        btn.style.color = "#00ff00";
        showToast("Shelf synced with the cloud.");

        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
            btn.style.borderColor = "";
            btn.style.color = "";
        }, 3000);
    },

    clearOfflineDownloads: async () => {
        await clearAllOfflineDownloads();
        await refreshOfflineShelfState();
        renderLibrarySurfaces();
        showToast("Offline shelf cleared from this browser.");
    },

    logout: async () => {
        console.log("Logging out...");
        try {
            await signOutCurrentUser();
        } catch (error) {
            console.warn("Clerk signout issue:", error);
        }

        localStorage.removeItem("vibe_user_id");
        localStorage.removeItem("vibe_user_name");
        localStorage.removeItem(STORAGE_KEYS.lastPlayerSession);
        localStorage.removeItem(STORAGE_KEYS.lastOpenedBook);
        window.location.href = "../../index.html";
    }
};

async function init() {
    if (hasInitialized) return;
    hasInitialized = true;

    console.log("VibeAudio UI starting...");
    const initialTheme = (typeof document !== 'undefined' && document.documentElement.getAttribute('data-theme')) || getResolvedTheme();
    applyTheme(initialTheme, false);

    if (typeof window !== 'undefined' && window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            try {
                if (!localStorage.getItem(STORAGE_KEYS.theme)) {
                    applyTheme(e.matches ? 'dark' : 'light', false);
                }
            } catch (err) {}
        });
    }

    setupImageObserver();
    setupRouting();
    renderSyncState();
    await refreshOfflineShelfState();

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState !== "hidden") return;

        const state = getCurrentState();
        if (state.book && state.currentTime > 5) {
            console.log("App backgrounded. Saving progress...");
            saveUserProgress(
                state.book.bookId,
                state.currentChapterIndex,
                state.currentTime,
                state.duration,
                {
                    totalChapters: state.book.activeChapters?.length || state.book.chapters?.length || 0
                }
            );
        }
    });

    window.addEventListener('sync-status-change', (event) => {
        renderSyncState(event.detail);
    });
    window.addEventListener('offline-shelf-change', () => {
        queueOfflineShelfRefresh();
    });
    window.addEventListener('online', async () => {
        await resumePendingDownloads();
        await flushPendingProgressQueue();
        invalidateProgressCache();
        const freshBooks = await fetchAllBooks({ forceRefresh: true });
        if (freshBooks.length > 0) {
            allBooks = sortCatalogBooks(freshBooks);
            LibraryUI.renderCategoryFilters(allBooks);
        }
        await refreshPersonalizedCatalog();
    });
    window.addEventListener('offline', () => {
        renderSyncState();
    });

    const user = getLocalUserProfile();
    if (user.name) {
        const nameDisplay = document.getElementById('user-name-display');
        const avatar = document.getElementById('profile-avatar');
        if (nameDisplay) nameDisplay.innerText = user.name;
        if (avatar) {
            avatar.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(user.name)}&background=ff4b1f&color=fff&bold=true`;

            // Create and inject global sync indicator
            if (!document.getElementById('global-sync-indicator') && avatar.parentElement) {
                const indicator = document.createElement('div');
                indicator.id = 'global-sync-indicator';
                indicator.className = 'global-sync-indicator';
                indicator.title = 'Sync status';
                indicator.onclick = () => window.app.syncData();
                // Assuming avatar's parent is a flex container
                avatar.parentElement.appendChild(indicator);
            }
        }
    }

    syncUserProfile();

    const cachedCatalog = getCatalogSnapshot();
    if (cachedCatalog.books.length > 0) {
        allBooks = sortCatalogBooks(cachedCatalog.books);
        allBooks = applyOfflineSummariesToBooks(allBooks, offlineShelfSummaries);
        warmOfflineCatalog(allBooks);
        LibraryUI.renderCategoryFilters(allBooks);
        await refreshPersonalizedCatalog();
        restorePlayerSessionIfNeeded();
    }

    const freshBooks = await fetchAllBooks({ forceRefresh: true });
    allBooks = sortCatalogBooks(freshBooks);
    allBooks = applyOfflineSummariesToBooks(allBooks, offlineShelfSummaries);
    warmOfflineCatalog(allBooks);

    LibraryUI.renderCategoryFilters(allBooks);
    await refreshPersonalizedCatalog();
    restorePlayerSessionIfNeeded();
    setupListeners();
    handleIncomingDeepLinksOrShare();

    window.addEventListener('vibe-file-received', (event) => {
        const file = event.detail?.file;
        if (file) {
            handleUserAudioFileImport(file);
        }
    });

    window.addEventListener('vibe-launch-url', (event) => {
        handleIncomingDeepLinksOrShare();
    });
}

async function handleUserAudioFileImport(file) {
    if (!file) return;

    showToast('Importing local audiobook...');
    try {
        const result = await importAudiobookFile(file);
        if (result.success) {
            showToast(`Saved "${result.book.title}" to On This Device.`);
            await refreshOfflineShelfState();
            switchView('offline');
        } else {
            showToast(result.error || 'Could not import audio file.');
        }
    } catch (err) {
        console.warn('Error during file import:', err);
        showToast('Unable to import local file.');
    }
}

function handleIncomingDeepLinksOrShare() {
    let searchParams = null;
    try {
        searchParams = new URLSearchParams(window.location.search);
    } catch (_) {}

    const hash = window.location.hash || '';
    let hashQuery = '';
    if (hash.includes('?')) {
        hashQuery = hash.split('?')[1] || '';
    }

    let hashParams = null;
    try {
        if (hashQuery) hashParams = new URLSearchParams(hashQuery);
    } catch (_) {}

    const targetBookId = searchParams?.get('book') || hashParams?.get('book');
    const targetUrl = searchParams?.get('url') || hashParams?.get('url');
    const targetTitle = searchParams?.get('title') || hashParams?.get('title');
    const targetText = searchParams?.get('text') || hashParams?.get('text');

    let resolvedBookId = targetBookId;

    if (!resolvedBookId && targetUrl) {
        try {
            const parsed = new URL(targetUrl, window.location.origin);
            if (parsed.searchParams.has('book')) {
                resolvedBookId = parsed.searchParams.get('book');
            } else if (parsed.hash.includes('book=')) {
                const hParams = new URLSearchParams(parsed.hash.split('?')[1] || parsed.hash.replace(/^#/, ''));
                resolvedBookId = hParams.get('book');
            }
        } catch (_) {}
    }

    if (resolvedBookId) {
        const foundBook = allBooks.find((b) => String(b.bookId) === String(resolvedBookId));
        if (foundBook) {
            openPlayerUI(foundBook, allBooks, switchView);
            return true;
        }
    }

    const searchQuery = (targetTitle || targetText || '').trim();
    if (searchQuery) {
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.value = searchQuery;
            searchInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
        switchView('library');
        return true;
    }

    return false;
}

function normalizeViewId(id) {
    if (!id) return 'home';
    const cleanId = String(id).split('?')[0].replace(/^#/, '');
    if (cleanId === 'home' || !cleanId) return 'home';
    return VALID_VIEWS.has(cleanId) ? cleanId : 'home';
}

function setupRouting() {
    const syncViewFromLocation = (event) => {
        const nextView = normalizeViewId(event?.state?.view || window.location.hash.replace(/^#/, ''));
        switchView(nextView, false);
    };

    window.addEventListener('popstate', syncViewFromLocation);
    window.addEventListener('hashchange', syncViewFromLocation);

    const initialView = normalizeViewId(window.location.hash.replace(/^#/, ''));
    history.replaceState({ view: initialView }, null, `#${initialView}`);
    switchView(initialView, false);
}

function goBackInApp() {
    if (closeSidebarIfOpen()) return;

    if (currentViewId !== 'home') {
        const activeHash = window.location.hash || `#${currentViewId}`;

        if (activeHash !== '#home') {
            const viewBeforeBack = currentViewId;
            window.history.back();

            window.setTimeout(() => {
                if (currentViewId === viewBeforeBack) {
                    switchView('home', false);
                }
            }, 150);
        } else {
            switchView('home', false);
        }

        return;
    }

    window.history.back();
}

function switchView(id, pushHistory = true) {
    const nextView = normalizeViewId(id);

    if (pushHistory) {
        if (currentViewId === nextView && history.state?.view === nextView) {
            history.replaceState({ view: nextView }, null, `#${nextView}`);
        } else {
            history.pushState({ view: nextView }, null, `#${nextView}`);
        }
    } else if (window.location.hash !== `#${nextView}` || history.state?.view !== nextView) {
        history.replaceState({ view: nextView }, null, `#${nextView}`);
    }

    currentViewId = nextView;
    setActiveThemeSurface(nextView === 'history' || nextView === 'player' ? nextView : 'library');

    document.querySelectorAll('.view-section').forEach((el) => el.classList.add('hidden'));
    const view = document.getElementById(`view-${nextView}`);
    if (view) {
        view.classList.remove('hidden');
        if (window.gsap) {
            gsap.fromTo(view, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.3 });
        }
    }

    // Update Topbar Nav Buttons
    document.querySelectorAll('.topbar-nav-btn').forEach((btn) => {
        btn.classList.toggle('active', btn.dataset.navView === nextView);
    });

    // Update Drawer Buttons
    document.querySelectorAll('.sidebar-nav button').forEach((btn) => btn.classList.remove('active'));
    const activeBtn = document.querySelector(`.sidebar-nav button[onclick*="'${nextView}'"]`);
    if (activeBtn) activeBtn.classList.add('active');

    document.body.classList.toggle('player-mode', nextView === 'player');
    document.body.classList.toggle('view-is-player', nextView === 'player');
    if (typeof closeSidebarIfOpen === 'function') closeSidebarIfOpen();

    const miniPlayerEl = document.getElementById('mini-player');
    if (miniPlayerEl) {
        if (nextView === 'player') {
            miniPlayerEl.classList.add('hidden');
        } else {
            const curState = getCurrentState();
            if (curState && curState.book) {
                miniPlayerEl.classList.remove('hidden');
            }
        }
    }

    if (nextView !== 'player') {
        window.scrollTo({ top: 0, behavior: 'instant' });
    }

    if (nextView === 'home') {
        renderHomeSurfaces();
    }

    if (nextView === 'library') {
        renderLibrarySurfaces();
    }

    if (nextView === 'history') {
        refreshPersonalizedCatalog();
    }

    if (nextView === 'offline') {
        renderOfflineView();
    }

    if (nextView === 'profile') {
        renderProfileSnapshot();
    }
}

function filterLibraryLogic(category) {
    currentCategory = category;
    document.querySelectorAll('.filter-btn').forEach((btn) => btn.classList.remove('active'));

    const btnId = LibraryUI.getCategoryButtonId(category);
    const activeBtn = document.getElementById(btnId);
    if (activeBtn) activeBtn.classList.add('active');

    renderLibrarySurfaces();
}

function setupListeners() {
    const playBtn = document.getElementById('play-btn');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const seekBack = document.getElementById('seek-back-btn');
    const seekFwd = document.getElementById('seek-fwd-btn');
    const progress = document.getElementById('progress-bar');
    const postBtn = document.getElementById('post-comment-btn');
    const searchInput = document.getElementById('search-input');

    const searchClearBtn = document.getElementById('search-clear-btn');
    const menuBtn = document.getElementById('menu-btn');
    const closeBtn = document.getElementById('close-sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const sidebar = document.getElementById('sidebar');
    const syncBtn = document.getElementById('sync-profile-btn');
    const clearOfflineBtn = document.getElementById('clear-offline-downloads-btn');
    const filterContainer = document.getElementById('category-filters');
    const recentSearchesContainer = document.getElementById('recent-searches-panel');
    const importInput = document.getElementById('import-audiobook-input');

    if (importInput) {
        importInput.addEventListener('change', (event) => {
            const file = event.target.files?.[0];
            if (file) {
                handleUserAudioFileImport(file);
                importInput.value = '';
            }
        });
    }

    const toggleSidebar = (show) => {
        if (!sidebar || !overlay) return false;

        if (show) {
            sidebar.classList.add('active');
            overlay.classList.add('active');
            overlay.classList.remove('hidden');
            if (menuBtn) menuBtn.setAttribute('aria-expanded', 'true');
            closeBtn?.focus();
            return true;
        }

        const wasOpen = sidebar.classList.contains('active') || overlay.classList.contains('active');
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        if (menuBtn) menuBtn.setAttribute('aria-expanded', 'false');
        window.setTimeout(() => overlay.classList.add('hidden'), 300);
        return wasOpen;
    };

    closeSidebarIfOpen = () => toggleSidebar(false);

    if (menuBtn) {
        menuBtn.setAttribute('aria-haspopup', 'true');
        menuBtn.setAttribute('aria-expanded', 'false');
        menuBtn.onclick = () => toggleSidebar(true);
    }
    if (closeBtn) closeBtn.onclick = () => {
        toggleSidebar(false);
        menuBtn?.focus();
    };
    if (overlay) overlay.onclick = () => toggleSidebar(false);

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            if (toggleSidebar(false)) {
                menuBtn?.focus();
            }
        }
    });

    document.querySelectorAll('.sidebar-nav button').forEach((btn) => {
        btn.addEventListener('click', () => toggleSidebar(false));
    });

    document.querySelectorAll('.topbar-nav-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            const navView = btn.dataset.navView;
            if (navView) switchView(navView);
        });
    });

    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    if (themeToggleBtn) {
        themeToggleBtn.onclick = () => toggleTheme();
    }

    const sidebarThemeToggleBtn = document.getElementById('sidebar-theme-toggle-btn');
    if (sidebarThemeToggleBtn) {
        sidebarThemeToggleBtn.onclick = () => toggleTheme();
    }

    document.querySelectorAll('.theme-choice-btn').forEach((btn) => {
        btn.onclick = () => {
            const choice = btn.dataset.themeChoice;
            if (choice) applyTheme(choice, true);
        };
    });

    if (filterContainer) {
        filterContainer.addEventListener('click', (event) => {
            const target = event.target.closest('[data-category]');
            if (!target) return;
            filterLibraryLogic(String(target.dataset.category || 'All'));
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', (event) => {
            const query = String(event.target.value || '');
            currentSearchQuery = query;
            if (searchClearBtn) {
                searchClearBtn.classList.toggle('hidden', !query);
            }
            if (query.trim() && currentViewId !== 'library') {
                switchView('library', false);
            } else {
                renderLibrarySurfaces();
            }
        });
        searchInput.addEventListener('change', (event) => {
            pushRecentSearch(String(event.target.value || ''));
            renderLibrarySurfaces();
        });
        searchInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                pushRecentSearch(String(event.target.value || ''));
                renderLibrarySurfaces();
            }
        });
    }

    if (searchClearBtn) {
        searchClearBtn.addEventListener('click', () => {
            searchInput.value = '';
            currentSearchQuery = '';
            searchClearBtn.classList.add('hidden');
            renderLibrarySurfaces();
            searchInput.focus();
        });
    }

    if (recentSearchesContainer) {
        recentSearchesContainer.addEventListener('click', (event) => {
            const clearTrigger = event.target.closest('[data-clear-recent]');
            if (clearTrigger) {
                clearRecentSearches();
                renderLibrarySurfaces();
                if (searchInput) searchInput.focus();
                return;
            }

            const target = event.target.closest('[data-query]');
            if (!target) return;
            searchInput.value = target.dataset.query;
            searchInput.dispatchEvent(new Event('input', { bubbles: true }));
            searchInput.dispatchEvent(new Event('change', { bubbles: true }));
        });
    }

    if (postBtn) {
        postBtn.onclick = () => {
            const input = document.getElementById('comment-input');
            const text = String(input?.value || '').trim();
            if (!text) return;

            const state = getCurrentState();
            if (!state.book) return;
            const currentTime = Math.floor(state.currentTime || 0);
            const savedComment = addPersistentComment(state.book.bookId, {
                time: currentTime,
                user: getCurrentUserName(),
                text
            });
            renderSingleComment(savedComment);

            input.value = '';
            showToast('Comment saved on this device');
        };
    }

    const miniPlayBtn = document.getElementById('mini-play-btn');
    const miniSeekBack = document.getElementById('mini-seek-back-btn');
    const miniSeekFwd = document.getElementById('mini-seek-fwd-btn');

    if (playBtn) playBtn.onclick = window.app.togglePlay;
    if (miniPlayBtn) miniPlayBtn.onclick = window.app.togglePlay;
    if (prevBtn) prevBtn.onclick = window.app.prevChapter;
    if (nextBtn) nextBtn.onclick = window.app.nextChapter;
    if (seekBack) seekBack.onclick = () => skip(-15);
    if (seekFwd) seekFwd.onclick = () => skip(30);
    if (miniSeekBack) miniSeekBack.onclick = () => skip(-15);
    if (miniSeekFwd) miniSeekFwd.onclick = () => skip(30);
    if (syncBtn) syncBtn.onclick = window.app.syncData;
    if (clearOfflineBtn) clearOfflineBtn.onclick = window.app.clearOfflineDownloads;

    const miniTrackInfo = document.getElementById('mini-track-info') || document.querySelector('#mini-player .track-info');
    if (miniTrackInfo) {
        miniTrackInfo.onclick = (event) => {
            if (event.target.closest('button')) return;
            const state = getCurrentState();
            if (state?.book) {
                openPlayerUI(state.book, allBooks, switchView);
            } else {
                switchView('player');
            }
        };
        miniTrackInfo.onkeydown = (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                miniTrackInfo.click();
            }
        };
    }

    if (progress) {
        progress.addEventListener('input', (event) => {
            const pct = Number(event.target.value || 0);
            const state = getCurrentState();
            if (state.duration) {
                const targetTime = (pct / 100) * state.duration;
                const currentTimeEl = document.getElementById('current-time');
                if (currentTimeEl) currentTimeEl.innerText = formatTime(targetTime);
                progress.setAttribute('aria-valuenow', String(Math.round(pct)));
                progress.setAttribute('aria-valuetext', `${formatTime(targetTime)} of ${formatTime(state.duration)}`);
            }
            seekTo(pct);
            progress.style.backgroundSize = `${pct}% 100%`;
            const miniLineFill = document.getElementById('mini-progress-line-fill');
            if (miniLineFill) miniLineFill.style.width = `${pct}%`;
        });
    }

    const syncProgressUI = (state = getCurrentState()) => {
        if (!progress || !state.duration) return;

        const pct = Math.max(0, Math.min(100, (state.currentTime / state.duration) * 100));
        progress.value = pct;
        progress.style.backgroundSize = `${pct}% 100%`;
        progress.setAttribute('aria-valuenow', String(Math.round(pct)));
        progress.setAttribute('aria-valuetext', `${formatTime(state.currentTime)} of ${formatTime(state.duration)}`);

        const miniLineFill = document.getElementById('mini-progress-line-fill');
        if (miniLineFill) miniLineFill.style.width = `${pct}%`;

        const currentTimeEl = document.getElementById('current-time');
        const durationEl = document.getElementById('total-duration');
        if (currentTimeEl) currentTimeEl.innerText = formatTime(state.currentTime);
        if (durationEl) durationEl.innerText = formatTime(state.duration);

        const remainingEl = document.getElementById('player-time-remaining');
        if (remainingEl && state.duration > 0) {
            const remainingSec = Math.max(0, state.duration - state.currentTime);
            const remainingMin = Math.ceil(remainingSec / 60);
            remainingEl.innerText = remainingMin > 0 ? `${remainingMin} min left in part` : 'Part ending';
        }
    };

    window.addEventListener('player-time-update', (event) => syncProgressUI(event.detail));
    window.addEventListener('player-state-change', () => {
        const state = getCurrentState();
        if (!state.duration) {
            if (progress) {
                progress.value = 0;
                progress.style.backgroundSize = `0% 100%`;
                progress.setAttribute('aria-valuenow', '0');
                progress.removeAttribute('aria-valuetext');
            }

            const miniLineFill = document.getElementById('mini-progress-line-fill');
            if (miniLineFill) miniLineFill.style.width = `0%`;

            const currentTimeEl = document.getElementById('current-time');
            const durationEl = document.getElementById('total-duration');
            if (currentTimeEl) currentTimeEl.innerText = "00:00";
            if (durationEl) durationEl.innerText = "00:00";
            return;
        }

        syncProgressUI(state);
    });
}

injectUiRuntimeStyles();

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
