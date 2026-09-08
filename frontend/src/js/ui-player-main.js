import { fetchBookDetails, fetchUserProgress } from './api.js';
import {
    loadBook,
    getCurrentState,
    isPlaybackActive,
    skip,
    setPlaybackSpeed,
    setSleepTimer,
    clearSleepTimer,
    getCurrentChapterOfflineState,
    downloadCurrentChapter,
    deleteChapter,
    getCurrentLang,
    queueCurrentBookForOffline,
    removeCurrentBookOffline,
    toggleVocalBoost
} from './player.js';
import { getOfflineBook, OFFLINE_STATES } from './offline-shelf.js';
import { renderChapterList, toggleLangUI } from './ui-player-list.js';
import { applyChameleonTheme, renderComments, showToast } from './ui-player-helpers.js';
import { STORAGE_KEYS } from './config.js';
import { addBookmark, getBookmarks, getPersistentComments, removeBookmark } from './user-data.js';

window.addEventListener('player-state-change', (event) => {
    const { isPlaying, book, chapter } = event.detail;
    updateUI(isPlaying, book, chapter);
});

window.addEventListener('player-playback-error', (event) => {
    const { playbackOrigin } = event.detail || {};
    if (playbackOrigin === 'offline') {
        showToast("Offline audio couldn't be played. Trying to stream...");
    } else if (!navigator.onLine) {
        showToast("You're offline. Download books to listen without internet.");
    } else {
        showToast("Playback was interrupted. Tap play to retry.");
    }
});

let offlineUiRefreshQueued = false;

window.addEventListener('offline-shelf-change', () => {
    if (offlineUiRefreshQueued) return;
    offlineUiRefreshQueued = true;

    requestAnimationFrame(() => {
        offlineUiRefreshQueued = false;
        const state = getCurrentState();
        updateUI(state.isPlaying, state.book);
    });
});

const speeds = [1, 1.25, 1.5, 2, 0.95, 0.9, 0.8];
let currentSpeedIndex = Math.max(0, speeds.indexOf(Number(localStorage.getItem(STORAGE_KEYS.playbackSpeed) || 1)));
const sleepTimes = [0, 15, 30, 60];
let currentSleepIndex = 0;
let lastYouTubeHintSource = "";

function warmActiveBookOffline(book) {
    const bridge = window.VibePWA;
    if (!bridge?.primeOfflineResources || !book) return;

    const urls = [book.dataPath, book.cover]
        .map((value) => {
            try {
                return new URL(String(value || ''), window.location.href).href;
            } catch (error) {
                return '';
            }
        })
        .filter(Boolean);

    if (!urls.length) return;
    void bridge.primeOfflineResources(urls);
}

function formatStorageSize(bytes) {
    const safeBytes = Math.max(0, Number(bytes || 0));
    if (!safeBytes) return '0 MB';
    if (safeBytes >= 1024 ** 3) return `${(safeBytes / (1024 ** 3)).toFixed(1)} GB`;
    return `${Math.max(0.1, safeBytes / (1024 ** 2)).toFixed(safeBytes >= 1024 ** 2 ? 1 : 0)} MB`;
}

function formatRelativeLabel(value) {
    const stamp = Date.parse(value || 0);
    if (!Number.isFinite(stamp)) return 'recently';

    const delta = Date.now() - stamp;
    if (delta < 60 * 1000) return 'just now';

    const minutes = Math.floor(delta / (60 * 1000));
    if (minutes < 60) return `${minutes}m ago`;

    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;

    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}

function setButtonLoading(button, label) {
    if (!button) return;
    button.disabled = true;
    button.dataset.previousHtml = button.innerHTML;
    button.innerHTML = `<svg class="vibe-icon spin" aria-hidden="true"><use href="#icon-spinner"></use></svg> ${label}`;
}

function resetButtonLoading(button) {
    if (!button) return;
    if (button.dataset.previousHtml) {
        button.innerHTML = button.dataset.previousHtml;
        delete button.dataset.previousHtml;
    }
    button.disabled = false;
}

function buildBookSummary(book) {
    if (!book) return 'Pick a story and VibeAudio will keep your place across every listening session.';
    if (book.description) return String(book.description);

    const genre = book.genre || '';
    const filteredMoods = (Array.isArray(book.moods) ? book.moods : [])
        .filter((m) => String(m).toLowerCase() !== genre.toLowerCase())
        .slice(0, 2);
    const moods = filteredMoods.length ? filteredMoods.join(', ') : '';
    const genreLine = genre ? `${genre} listening` : 'Immersive listening';
    const moodLine = moods ? ` with ${moods} tones` : '';
    return `${genreLine} by ${book.author || 'a curated voice'}${moodLine}. Jump in, pause anywhere, and come back exactly where you left off.`;
}

function isYouTubeUrl(url) {
    if (!url) return false;
    return /(?:youtube\.com|youtu\.be)/i.test(String(url));
}

function renderDetailMeta(book) {
    const container = document.getElementById('detail-pills');
    if (!container || !book) return;

    container.innerHTML = '';
    const hasYouTube = (book.chapters || []).some((c) => isYouTubeUrl(c.url)) || (book.chapters_en || []).some((c) => isYouTubeUrl(c.url));
    const sourcePill = hasYouTube ? 'Streaming Only' : 'Direct Audio';

    const rawPills = [
        `${Number(book.totalChapters || book.chapters?.length || 0)} parts`,
        sourcePill,
        book.genre || '',
        ...(Array.isArray(book.moods) ? book.moods : []),
        book.chapters_en?.length ? 'Hindi + English' : 'Single Language'
    ].filter(Boolean);

    // Deduplicate case-insensitively while preserving order
    const seen = new Set();
    const uniquePills = [];
    rawPills.forEach((p) => {
        const key = String(p).trim().toLowerCase();
        if (key && !seen.has(key)) {
            seen.add(key);
            uniquePills.push(String(p).trim());
        }
    });

    uniquePills.forEach((label) => {
        const pill = document.createElement('span');
        pill.className = 'detail-pill';
        pill.textContent = String(label);
        container.appendChild(pill);
    });
}

function renderBookmarks(book) {
    const list = document.getElementById('bookmark-list');
    if (!list || !book) return;

    const bookmarks = getBookmarks(book.bookId);
    list.innerHTML = '';

    if (!bookmarks.length) {
        const empty = document.createElement('p');
        empty.className = 'bookmark-empty';
        empty.textContent = 'Save key moments here so you can jump back to them later.';
        list.appendChild(empty);
        return;
    }

    bookmarks.forEach((bookmark) => {
        const row = document.createElement('div');
        row.className = 'bookmark-item';

        const jumpButton = document.createElement('button');
        jumpButton.type = 'button';
        jumpButton.className = 'bookmark-jump';
        jumpButton.addEventListener('click', () => window.app.seekToComment(bookmark.time));

        const title = document.createElement('strong');
        title.textContent = bookmark.label || `Saved moment at ${bookmark.chapterName}`;
        const meta = document.createElement('span');
        meta.textContent = `${bookmark.chapterName} - ${Math.floor(Number(bookmark.time || 0) / 60)}:${Math.floor(Number(bookmark.time || 0) % 60).toString().padStart(2, '0')}`;
        jumpButton.appendChild(title);
        jumpButton.appendChild(meta);

        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'bookmark-remove';
        removeButton.textContent = 'Remove';
        removeButton.addEventListener('click', (event) => {
            event.stopPropagation();
            removeBookmark(book.bookId, bookmark.id);
            renderBookmarks(book);
            showToast('Saved moment removed');
        });

        row.appendChild(jumpButton);
        row.appendChild(removeButton);
        list.appendChild(row);
    });
}

function saveCurrentBookmark() {
    const state = getCurrentState();
    if (!state.book) {
        showToast('Start a story before saving a moment');
        return;
    }

    const chapter = state.book.activeChapters?.[state.currentChapterIndex];
    addBookmark(state.book, {
        chapterIndex: state.currentChapterIndex,
        chapterName: chapter?.name || `Part ${state.currentChapterIndex + 1}`,
        time: state.currentTime,
        label: `${chapter?.name || 'Current part'} - ${Math.floor(Number(state.currentTime || 0) / 60)}:${Math.floor(Number(state.currentTime || 0) % 60).toString().padStart(2, '0')}`
    });

    renderBookmarks(state.book);
    showToast('Moment saved to bookmarks');
}

function canKeepScreenAwake() {
    return Boolean(navigator.wakeLock?.request);
}

function openCurrentSourceInBrowser() {
    const sourceUrl = String(getCurrentState().sourceUrl || '').trim();
    if (!sourceUrl) {
        showToast("Source link is unavailable right now.");
        return;
    }

    showToast("Opening the source in your browser.");

    const openedWindow = window.open(sourceUrl, '_blank');
    if (openedWindow) {
        openedWindow.opener = null;
    } else {
        window.location.href = sourceUrl;
    }
}

function syncSourceSupportUI(state) {
    const note = document.getElementById('source-support-note');
    const noteText = document.getElementById('source-support-text');
    const noteButton = document.getElementById('source-support-open-btn');
    const miniButton = document.getElementById('open-source-btn');

    const hasSourceUrl = Boolean(state.book && state.sourceUrl);
    const isYouTubeSource = state.sourceType === 'youtube' && hasSourceUrl;

    if (note) {
        note.classList.toggle('hidden', !isYouTubeSource);
    }

    if (noteText && isYouTubeSource) {
        const wakeLockHint = canKeepScreenAwake()
            ? " VibeAudio may also request a wake lock to keep playback steadier while the tab stays active."
            : "";
        noteText.innerText = `This source is running in audio-only mode with the video hidden.${wakeLockHint} If playback stops in your browser, open the original source directly.`;
    } else if (noteText) {
        noteText.innerText = "";
    }

    if (noteButton) {
        noteButton.onclick = isYouTubeSource ? openCurrentSourceInBrowser : null;
    }

    if (miniButton) {
        miniButton.style.display = isYouTubeSource ? 'inline-flex' : 'none';
        miniButton.onclick = isYouTubeSource ? openCurrentSourceInBrowser : null;
        miniButton.title = isYouTubeSource ? "Open source in browser if playback stops" : "Open source in browser";
    }

    const nextHintSource = isYouTubeSource ? String(state.sourceUrl) : "";
    if (nextHintSource && nextHintSource !== lastYouTubeHintSource) {
        showToast("YouTube audio mode active.");
    }

    lastYouTubeHintSource = nextHintSource;
}

async function syncOfflineExperienceUI(book, chapter, state) {
    const chapterButton = document.getElementById('download-btn');
    const bookButton = document.getElementById('download-book-btn');
    const removeBookButton = document.getElementById('remove-offline-book-btn');
    const statusChip = document.getElementById('player-offline-status-chip');
    const statusSummary = document.getElementById('player-offline-summary');
    const statusMeta = document.getElementById('player-offline-meta');

    if (!chapterButton || !statusChip || !statusSummary || !statusMeta) return;

    const isYouTubeSource = state.sourceType === 'youtube';
    const offlineState = await getCurrentChapterOfflineState();
    const offlineBook = book ? await getOfflineBook(book.bookId, getCurrentLang()) : null;
    const savedCount = Number(offlineBook?.totalDownloadedChapters || 0);
    chapterButton.disabled = false;
    chapterButton.style.opacity = '';
    chapterButton.style.cursor = '';
    chapterButton.style.color = '';

    statusChip.dataset.state = offlineState.status;

    if (isYouTubeSource || offlineState.status === 'not_available') {
        chapterButton.innerHTML = `<svg class="vibe-icon" aria-hidden="true"><use href="#icon-ban"></use></svg>`;
        chapterButton.disabled = true;
        chapterButton.title = offlineState.reason || 'This chapter is not available for offline use.';
        chapterButton.style.opacity = '0.55';
        chapterButton.style.cursor = 'not-allowed';

        statusChip.textContent = 'Streaming Only';
        statusSummary.textContent = 'YouTube-backed chapters stay streaming-only in browser. Playback still works, but VibeAudio will not save this source offline.';
        statusMeta.textContent = 'Direct audio sources can be saved inside your browser for offline playback.';
        if (bookButton) bookButton.disabled = true;
        if (removeBookButton) removeBookButton.disabled = savedCount === 0 && queueCount === 0;
        return;
    }

    if (offlineState.status === OFFLINE_STATES.downloaded) {
        chapterButton.innerHTML = `<svg class="vibe-icon vibe-icon-success" aria-hidden="true"><use href="#icon-check"></use></svg>`;
        chapterButton.title = 'Remove this offline chapter';
        chapterButton.style.color = '#77d28c';
    } else if (offlineState.status === OFFLINE_STATES.updateAvailable) {
        chapterButton.innerHTML = `<svg class="vibe-icon" aria-hidden="true"><use href="#icon-sync"></use></svg>`;
        chapterButton.title = 'Refresh this offline chapter';
        chapterButton.style.color = '#ffd37b';
    } else if (offlineState.status === OFFLINE_STATES.downloading) {
        const progressPercent = Math.max(0, Math.round(Number(offlineState.record?.progressPercent || 0)));
        chapterButton.innerHTML = `<span>${progressPercent || 0}%</span>`;
        chapterButton.title = 'Chapter download in progress';
        chapterButton.disabled = true;
    } else if (offlineState.status === OFFLINE_STATES.queued) {
        chapterButton.innerHTML = `<svg class="vibe-icon" aria-hidden="true"><use href="#icon-chapters"></use></svg>`;
        chapterButton.title = 'Chapter is queued for download';
        chapterButton.disabled = true;
    } else if (offlineState.status === OFFLINE_STATES.failed) {
        chapterButton.innerHTML = `<svg class="vibe-icon vibe-icon-accent" aria-hidden="true"><use href="#icon-warning"></use></svg>`;
        chapterButton.title = offlineState.reason || 'Retry offline download';
    } else {
        chapterButton.innerHTML = `<svg class="vibe-icon" aria-hidden="true"><use href="#icon-download"></use></svg>`;
        chapterButton.title = 'Save this chapter for offline use';
    }

    if (state.playbackOrigin === 'offline') {
        statusChip.textContent = 'Playing Offline';
        statusSummary.textContent = 'This chapter is saved on this device. VibeAudio is playing the local copy seamlessly.';
    } else if (offlineState.status === OFFLINE_STATES.downloaded) {
        statusChip.textContent = 'Ready Offline';
        statusSummary.textContent = 'Saved to this browser shelf. Ready for instant offline playback anytime.';
    } else if (offlineState.status === OFFLINE_STATES.updateAvailable) {
        statusChip.textContent = 'Update Available';
        statusSummary.textContent = 'A saved copy exists, but the source was updated. Refresh once to keep it current.';
    } else if (offlineState.status === OFFLINE_STATES.downloading) {
        const progressPercent = Math.max(0, Math.round(Number(offlineState.record?.progressPercent || 0)));
        statusChip.textContent = 'Saving to Device…';
        statusSummary.textContent = progressPercent > 0
            ? `Saving this chapter locally. ${progressPercent}% complete.`
            : 'Saving this chapter locally.';
    } else if (offlineState.status === OFFLINE_STATES.queued) {
        statusChip.textContent = 'Queued';
        statusSummary.textContent = 'This chapter is in your offline queue and will continue automatically.';
    } else if (offlineState.status === OFFLINE_STATES.failed) {
        statusChip.textContent = 'Retry Needed';
        statusSummary.textContent = offlineState.reason || 'Download was interrupted. Tap retry to continue.';
    } else {
        statusChip.textContent = 'Save Offline';
        statusSummary.textContent = 'Save chapters or the full book inside your browser to listen anywhere without a connection.';
    }

    const metaParts = [];
    if (savedCount > 0 && totalParts > 0) metaParts.push(`${savedCount}/${totalParts} parts saved`);
    if (queueCount > 0) metaParts.push(`${queueCount} in queue`);
    if (offlineBook?.totalSizeBytes > 0) metaParts.push(sizeLabel);
    metaParts.push(`Validated ${validatedLabel}`);
    statusMeta.textContent = metaParts.join(' - ');

    if (bookButton) {
        bookButton.disabled = false;
        bookButton.innerHTML = queueCount > 0
            ? `<svg class="vibe-icon" aria-hidden="true"><use href="#icon-chapters"></use></svg> Queue running`
            : `<svg class="vibe-icon" aria-hidden="true"><use href="#icon-cloud-download"></use></svg> Download Book`;
    }

    if (removeBookButton) {
        removeBookButton.disabled = savedCount === 0 && queueCount === 0;
    }
}

export async function openPlayerUI(partialBook, allBooks, switchViewCallback) {
    switchViewCallback('player');

    document.getElementById('detail-cover').src = partialBook.cover;
    document.getElementById('detail-title').innerText = partialBook.title;
    document.getElementById('detail-author').innerText = partialBook.author;
    const summaryEl = document.getElementById('detail-summary');
    if (summaryEl) summaryEl.textContent = buildBookSummary(partialBook);
    const blurBg = document.getElementById('blur-bg');
    if (blurBg) {
        blurBg.style.setProperty('--player-cover-image', `url("${partialBook.cover}")`);
    }
    applyChameleonTheme(partialBook.cover);

    const chapterListEl = document.getElementById('chapter-list');
    chapterListEl.innerHTML = `
        <div class="skeleton-loader" style="padding: 20px; text-align: center; color: var(--theme-text-dim);">
            <svg class="vibe-icon spin" aria-hidden="true"><use href="#icon-spinner"></use></svg> Fetching chapters...
        </div>`;

    let finalBook = partialBook;

    if (!finalBook.chapters || finalBook.chapters.length === 0) {
        try {
            const fullBookDetails = await fetchBookDetails(partialBook.dataPath);
            if (!fullBookDetails) {
                chapterListEl.innerHTML = `<div class="empty-state" style="margin: 20px 0;"><p>Unable to load book chapters. Please check your connection and retry.</p></div>`;
                return;
            }

            finalBook = { ...partialBook, ...fullBookDetails };
            if (!finalBook.chapters && finalBook.chapters_en) {
                finalBook.chapters = finalBook.chapters_en;
            }

            const index = allBooks.findIndex((book) => book.bookId === partialBook.bookId);
            if (index !== -1) allBooks[index] = finalBook;
        } catch (error) {
            console.error("Failed to hydrate book details:", error);
            chapterListEl.innerHTML = `<div class="empty-state" style="margin: 20px 0;"><p>Unable to load book chapters. Please check your connection and retry.</p></div>`;
            return;
        }
    }

    if (summaryEl) summaryEl.textContent = buildBookSummary(finalBook);
    renderDetailMeta(finalBook);
    warmActiveBookOffline(finalBook);

    const langContainer = document.getElementById('lang-toggle-container');
    if (finalBook.chapters_en && finalBook.chapters_en.length > 0) {
        langContainer.innerHTML = `
            <div class="lang-switch">
                <button class="lang-btn ${getCurrentLang() === 'hi' ? 'active' : ''}" id="btn-hi">HINDI</button>
                <button class="lang-btn ${getCurrentLang() === 'en' ? 'active' : ''}" id="btn-en">ENG</button>
            </div>`;
        langContainer.classList.remove('hidden');
        document.getElementById('btn-hi').onclick = () => toggleLangUI('hi', finalBook);
        document.getElementById('btn-en').onclick = () => toggleLangUI('en', finalBook);
    } else {
        langContainer.classList.add('hidden');
        langContainer.innerHTML = '';
    }

    renderChapterList(finalBook);
    renderComments(getPersistentComments(finalBook.bookId, finalBook.comments || []));
    renderBookmarks(finalBook);
    setupPlayButton(finalBook);
    setupPlayerListeners();

    if (finalBook.savedState) {
        loadBook(finalBook, finalBook.savedState.chapterIndex, finalBook.savedState.currentTime);
        updateUI(isPlaybackActive(), finalBook);
        return;
    }

    const state = getCurrentState();
    if (state.book && state.book.bookId === finalBook.bookId) {
        updateUI(isPlaybackActive(), finalBook);
        return;
    }

    fetchUserProgress()
        .then((history) => {
            const saved = history.find((item) => item.bookId == finalBook.bookId);
            if (saved) loadBook(finalBook, saved.chapterIndex, saved.currentTime);
            else loadBook(finalBook, 0);

            updateUI(isPlaybackActive(), finalBook);
        })
        .catch((error) => {
            console.warn("Falling back to default chapter load.", error);
            loadBook(finalBook, 0);
            updateUI(isPlaybackActive(), finalBook);
        });
}

export function updateUI(isPlaying, book = null, chapter = null) {
    const playBtn = document.getElementById('play-btn');
    const miniPlayBtn = document.getElementById('mini-play-btn');
    const mainPlayBtn = document.getElementById('main-play-btn');
    const miniPlayer = document.getElementById('mini-player');
    const playerStatusBadge = document.getElementById('player-status-badge');
    const playerCurrentPart = document.getElementById('player-current-part');
    const playerTimeRemaining = document.getElementById('player-time-remaining');

    if (playBtn) {
        playBtn.innerHTML = isPlaying ? `<svg class="vibe-icon" aria-hidden="true"><use href="#icon-pause"></use></svg>` : `<svg class="vibe-icon" aria-hidden="true"><use href="#icon-play"></use></svg>`;
        playBtn.setAttribute('aria-label', isPlaying ? 'Pause' : 'Play');
        playBtn.title = isPlaying ? 'Pause' : 'Play';
    }
    if (miniPlayBtn) {
        miniPlayBtn.innerHTML = isPlaying ? `<svg class="vibe-icon" aria-hidden="true"><use href="#icon-pause"></use></svg>` : `<svg class="vibe-icon" aria-hidden="true"><use href="#icon-play"></use></svg>`;
        miniPlayBtn.setAttribute('aria-label', isPlaying ? 'Pause' : 'Play');
        miniPlayBtn.title = isPlaying ? 'Pause' : 'Play';
    }
    if (mainPlayBtn) {
        mainPlayBtn.innerHTML = isPlaying ? `<svg class="vibe-icon" aria-hidden="true"><use href="#icon-pause"></use></svg> Pause` : `<svg class="vibe-icon" aria-hidden="true"><use href="#icon-play"></use></svg> Resume`;
        mainPlayBtn.setAttribute('aria-label', isPlaying ? 'Pause' : 'Resume');
        mainPlayBtn.title = isPlaying ? 'Pause' : 'Resume';
    }
    if (playerStatusBadge) {
        playerStatusBadge.textContent = isPlaying ? 'NOW PLAYING' : 'AUDIOBOOK';
    }

    const state = getCurrentState();
    if (book && !chapter && state.book && state.book.bookId === book.bookId) {
        chapter = state.book.activeChapters
            ? state.book.activeChapters[state.currentChapterIndex]
            : book.chapters[state.currentChapterIndex];
    }

    if (book && chapter && miniPlayer) {
        const isPlayerActive = document.body.classList.contains('player-mode') || document.body.classList.contains('view-is-player') || window.location.hash === '#player';
        if (isPlayerActive) {
            miniPlayer.classList.add('hidden');
        } else {
            miniPlayer.classList.remove('hidden');
        }
        const miniCover = document.getElementById('mini-cover');
        const miniTitle = document.getElementById('mini-title');
        const miniChapter = document.getElementById('mini-chapter');

        if (miniCover) miniCover.src = book.cover;
        if (miniTitle) miniTitle.innerText = book.title;
        if (miniChapter) {
            miniChapter.innerText = chapter.name
                .replace(/^Chapter\s+\d+[:\s-]*/i, '')
                .replace(/^\d+[\.\s]+/, '')
                .trim() || `Part ${state.currentChapterIndex + 1}`;
        }
    }

    if (playerCurrentPart) {
        const totalParts = state.book?.activeChapters?.length || state.book?.chapters?.length || state.book?.totalChapters || 1;
        playerCurrentPart.innerText = `Part ${state.currentChapterIndex + 1} of ${totalParts}`;
    }

    if (playerTimeRemaining) {
        if (state.duration > 0 && Number.isFinite(state.currentTime)) {
            const remainingSec = Math.max(0, state.duration - state.currentTime);
            const remainingMin = Math.ceil(remainingSec / 60);
            playerTimeRemaining.innerText = remainingMin > 0 ? `${remainingMin} min left in part` : 'Part ending';
        } else {
            playerTimeRemaining.innerText = isPlaying ? 'Playing' : 'Ready to listen';
        }
    }

    syncSourceSupportUI(state);

    if (!state.book) return;

    const isYouTubeSource = state.sourceType === 'youtube';
    const boostBtn = document.getElementById('vocal-boost-btn');
    if (boostBtn) {
        boostBtn.disabled = isYouTubeSource;
        boostBtn.title = isYouTubeSource ? "Vocal boost is only available for direct audio sources." : "Vocal Clarity Booster";
        boostBtn.setAttribute('aria-pressed', boostBtn.classList.contains('active') ? 'true' : 'false');

        if (isYouTubeSource) {
            boostBtn.classList.remove('active');
            boostBtn.setAttribute('aria-pressed', 'false');
            boostBtn.style.color = "";
            boostBtn.style.boxShadow = "";
            boostBtn.style.opacity = "0.55";
            boostBtn.style.cursor = "not-allowed";
        } else {
            boostBtn.style.opacity = "";
            boostBtn.style.cursor = "";
        }
    }

    document.querySelectorAll('#chapter-list .chapter-item').forEach((li, idx) => {
        const status = li.querySelector('.chapter-status');
        if (idx === state.currentChapterIndex) {
            li.classList.add('active');
            li.setAttribute('aria-current', 'true');
            if (status) status.innerHTML = `<svg class="vibe-icon vibe-icon-sm vibe-icon-accent" aria-hidden="true"><use href="#icon-equalizer"></use></svg>`;
            return;
        }

        li.classList.remove('active');
        li.removeAttribute('aria-current');
        if (status) status.innerHTML = `<svg class="vibe-icon vibe-icon-xs" style="font-size: 0.8rem;" aria-hidden="true"><use href="#icon-play"></use></svg>`;
    });

    void syncOfflineExperienceUI(book || state.book, chapter || state.book?.activeChapters?.[state.currentChapterIndex], state);
}

// Store handlers to remove them before re-binding, preventing memory leaks.
const playerEventHandlers = {};

function setupPlayButton(book) {
    const mainBtn = document.getElementById('main-play-btn');
    if (!mainBtn) return;

    if (playerEventHandlers.mainPlay) {
        mainBtn.removeEventListener('click', playerEventHandlers.mainPlay);
    }

    playerEventHandlers.mainPlay = async () => {
        const state = getCurrentState();
        if (state.book && String(state.book.bookId) === String(book.bookId)) {
            window.app.togglePlay();
            return;
        }

        mainBtn.innerHTML = `<svg class="vibe-icon spin" aria-hidden="true"><use href="#icon-spinner"></use></svg> Loading...`;
        try {
            const history = await fetchUserProgress();
            const saved = history.find((item) => String(item.bookId) === String(book.bookId));
            loadBook(book, saved ? saved.chapterIndex : 0, saved ? saved.currentTime : 0);
            updateUI(isPlaybackActive(), book);
        } catch (error) {
            console.warn("Falling back to chapter 1 play start.", error);
            loadBook(book, 0);
            updateUI(isPlaybackActive(), book);
        }
    };
    mainBtn.addEventListener('click', playerEventHandlers.mainPlay);
}

let playerListenersBound = false;

export function setupPlayerListeners() {
    if (playerListenersBound) return;
    playerListenersBound = true;

    const speedBtnRef = document.getElementById('speed-btn');
    let speedPopover = document.getElementById('speed-popover-menu');
    if (!speedPopover && speedBtnRef?.parentNode) {
        speedPopover = document.createElement('div');
        speedPopover.id = 'speed-popover-menu';
        speedPopover.className = 'popover-menu hidden';
        speedPopover.setAttribute('role', 'menu');
        speedPopover.setAttribute('aria-label', 'Playback Speed Menu');
        speedPopover.innerHTML = `
            <span class="popover-title" role="presentation">Playback Speed</span>
            ${[0.8, 0.9, 1, 1.25, 1.5, 1.75, 2].map((s) => `
                <button class="popover-item-btn ${s === (speeds[currentSpeedIndex] || 1) ? 'active' : ''}" data-speed="${s}" role="menuitemradio" aria-checked="${s === (speeds[currentSpeedIndex] || 1) ? 'true' : 'false'}">
                    <span>${s}x</span>
                    ${s === 1 ? '<span style="font-size:0.75rem; opacity:0.7">Normal</span>' : ''}
                </button>
            `).join('')}
        `;
        document.body.appendChild(speedPopover);

        speedPopover.addEventListener('click', (event) => {
            const btn = event.target.closest('[data-speed]');
            if (!btn) return;
            const targetSpeed = Number(btn.dataset.speed || 1);
            const appliedSpeed = setPlaybackSpeed(targetSpeed);
            if (speedBtnRef) {
                speedBtnRef.innerText = `${appliedSpeed}x`;
                speedBtnRef.setAttribute('aria-expanded', 'false');
            }
            speedPopover.querySelectorAll('.popover-item-btn').forEach((b) => {
                const isActive = Number(b.dataset.speed) === appliedSpeed;
                b.classList.toggle('active', isActive);
                b.setAttribute('aria-checked', isActive ? 'true' : 'false');
            });
            speedPopover.classList.add('hidden');
            speedBtnRef?.focus();
            showToast(`Speed: ${appliedSpeed}x`);
        });
    }

    const closeSpeedMenu = () => {
        if (speedPopover && !speedPopover.classList.contains('hidden')) {
            speedPopover.classList.add('hidden');
            speedBtnRef?.setAttribute('aria-expanded', 'false');
        }
    };

    if (speedBtnRef) {
        const initialSpeed = speeds[currentSpeedIndex] || 1;
        speedBtnRef.innerText = `${initialSpeed}x`;
        speedBtnRef.setAttribute('aria-haspopup', 'true');
        speedBtnRef.setAttribute('aria-expanded', 'false');
        speedBtnRef.addEventListener('click', (event) => {
            event.stopPropagation();
            if (sleepPopover) {
                sleepPopover.classList.add('hidden');
                document.getElementById('sleep-timer-btn')?.setAttribute('aria-expanded', 'false');
            }
            if (speedPopover) {
                const isHidden = speedPopover.classList.toggle('hidden');
                speedBtnRef.setAttribute('aria-expanded', isHidden ? 'false' : 'true');
                if (!isHidden) {
                    const rect = speedBtnRef.getBoundingClientRect();
                    if (window.innerWidth <= 768) {
                        speedPopover.style.bottom = `${Math.max(80, window.innerHeight - rect.top + 10)}px`;
                        speedPopover.style.left = '50%';
                        speedPopover.style.right = 'auto';
                        speedPopover.style.transform = 'translateX(-50%)';
                    } else {
                        speedPopover.style.bottom = `${window.innerHeight - rect.top + 10}px`;
                        speedPopover.style.right = `${Math.max(10, window.innerWidth - rect.right)}px`;
                        speedPopover.style.left = 'auto';
                        speedPopover.style.transform = 'none';
                    }
                    speedPopover.querySelector('.popover-item-btn.active')?.focus();
                }
            }
        });
    }

    let boostBtn = document.getElementById('vocal-boost-btn');
    if (!boostBtn) {
        boostBtn = document.createElement('button');
        boostBtn.id = 'vocal-boost-btn';
        boostBtn.title = "Vocal Clarity Booster";
        boostBtn.setAttribute('aria-label', 'Toggle vocal clarity booster');
        boostBtn.setAttribute('aria-pressed', 'false');
        boostBtn.innerHTML = '<svg class="vibe-icon" aria-hidden="true"><use href="#icon-vocal-clarity"></use></svg>';
        const currentSpeedBtn = document.getElementById('speed-btn');
        if (currentSpeedBtn && currentSpeedBtn.parentNode) {
            currentSpeedBtn.parentNode.insertBefore(boostBtn, currentSpeedBtn);
        }
    }

    if (boostBtn && boostBtn.parentNode) {
        boostBtn.addEventListener('click', () => {
            if (getCurrentState().sourceType === 'youtube') {
                showToast("Vocal boost is not available for YouTube links");
                return;
            }

            const isBoosting = boostBtn.classList.toggle('active');
            const applied = toggleVocalBoost(isBoosting);
            boostBtn.setAttribute('aria-pressed', isBoosting ? 'true' : 'false');

            if (!applied) {
                boostBtn.classList.remove('active');
                boostBtn.setAttribute('aria-pressed', 'false');
                showToast("Vocal boost is not available for this source");
                return;
            }

            if (isBoosting) {
                boostBtn.style.color = "#ff4b1f";
                boostBtn.style.boxShadow = "0 0 15px rgba(255, 75, 31, 0.5)";
                showToast("Vocal boost active");
            } else {
                boostBtn.style.color = "";
                boostBtn.style.boxShadow = "";
                showToast("Normal sound");
            }
        });
    }

    const sleepBtn = document.getElementById('sleep-timer-btn');
    let sleepPopover = document.getElementById('sleep-popover-menu');
    if (!sleepPopover && sleepBtn?.parentNode) {
        sleepPopover = document.createElement('div');
        sleepPopover.id = 'sleep-popover-menu';
        sleepPopover.className = 'popover-menu hidden';
        sleepPopover.setAttribute('role', 'menu');
        sleepPopover.setAttribute('aria-label', 'Sleep Timer Menu');
        sleepPopover.innerHTML = `
            <span class="popover-title" role="presentation">Sleep Timer</span>
            <button class="popover-item-btn active" data-sleep-mins="0" role="menuitemradio" aria-checked="true">Off</button>
            <button class="popover-item-btn" data-sleep-mins="15" role="menuitemradio" aria-checked="false">15 Minutes</button>
            <button class="popover-item-btn" data-sleep-mins="30" role="menuitemradio" aria-checked="false">30 Minutes</button>
            <button class="popover-item-btn" data-sleep-mins="45" role="menuitemradio" aria-checked="false">45 Minutes</button>
            <button class="popover-item-btn" data-sleep-mins="60" role="menuitemradio" aria-checked="false">60 Minutes</button>
        `;
        document.body.appendChild(sleepPopover);

        sleepPopover.addEventListener('click', (event) => {
            const btn = event.target.closest('[data-sleep-mins]');
            if (!btn) return;
            const minutes = Number(btn.dataset.sleepMins || 0);

            setSleepTimer(minutes, () => {
                updateUI(false);
                if (sleepBtn) {
                    sleepBtn.innerHTML = `<svg class="vibe-icon" aria-hidden="true"><use href="#icon-sleep"></use></svg>`;
                    sleepBtn.style.color = "";
                }
            });

            sleepPopover.querySelectorAll('.popover-item-btn').forEach((b) => {
                const isActive = Number(b.dataset.sleepMins) === minutes;
                b.classList.toggle('active', isActive);
                b.setAttribute('aria-checked', isActive ? 'true' : 'false');
            });
            sleepPopover.classList.add('hidden');
            if (sleepBtn) sleepBtn.setAttribute('aria-expanded', 'false');
            sleepBtn?.focus();

            if (minutes > 0) {
                if (sleepBtn) {
                    sleepBtn.innerHTML = `<span style="font-size:0.8rem; font-weight:bold">${minutes}m</span>`;
                    sleepBtn.style.color = "var(--secondary)";
                }
                showToast(`Sleep timer set for ${minutes}m`);
            } else {
                if (sleepBtn) {
                    sleepBtn.innerHTML = `<svg class="vibe-icon" aria-hidden="true"><use href="#icon-sleep"></use></svg>`;
                    sleepBtn.style.color = "";
                }
                showToast("Sleep timer off");
            }
        });
    }

    const closeSleepMenu = () => {
        if (sleepPopover && !sleepPopover.classList.contains('hidden')) {
            sleepPopover.classList.add('hidden');
            sleepBtn?.setAttribute('aria-expanded', 'false');
        }
    };

    if (sleepBtn) {
        sleepBtn.setAttribute('aria-haspopup', 'true');
        sleepBtn.setAttribute('aria-expanded', 'false');
        sleepBtn.addEventListener('click', (event) => {
            event.stopPropagation();
            if (speedPopover) {
                speedPopover.classList.add('hidden');
                speedBtnRef?.setAttribute('aria-expanded', 'false');
            }
            if (sleepPopover) {
                const isHidden = sleepPopover.classList.toggle('hidden');
                sleepBtn.setAttribute('aria-expanded', isHidden ? 'false' : 'true');
                if (!isHidden) {
                    const rect = sleepBtn.getBoundingClientRect();
                    if (window.innerWidth <= 768) {
                        sleepPopover.style.bottom = `${Math.max(80, window.innerHeight - rect.top + 10)}px`;
                        sleepPopover.style.left = '50%';
                        sleepPopover.style.right = 'auto';
                        sleepPopover.style.transform = 'translateX(-50%)';
                    } else {
                        sleepPopover.style.bottom = `${window.innerHeight - rect.top + 10}px`;
                        sleepPopover.style.right = `${Math.max(10, window.innerWidth - rect.right)}px`;
                        sleepPopover.style.left = 'auto';
                        sleepPopover.style.transform = 'none';
                    }
                    sleepPopover.querySelector('.popover-item-btn.active')?.focus();
                }
            }
        });
    }

    document.addEventListener('click', (event) => {
        if (speedPopover && !speedPopover.contains(event.target) && event.target !== speedBtnRef) {
            closeSpeedMenu();
        }
        if (sleepPopover && !sleepPopover.contains(event.target) && event.target !== sleepBtn) {
            closeSleepMenu();
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            if (speedPopover && !speedPopover.classList.contains('hidden')) {
                closeSpeedMenu();
                speedBtnRef?.focus();
            }
            if (sleepPopover && !sleepPopover.classList.contains('hidden')) {
                closeSleepMenu();
                sleepBtn?.focus();
            }
        }
    });

    ['bookmark-btn', 'bookmark-current-btn'].forEach((buttonId) => {
        const bookmarkBtn = document.getElementById(buttonId);
        if (!bookmarkBtn || !bookmarkBtn.parentNode) return;

        bookmarkBtn.addEventListener('click', saveCurrentBookmark);
    });

    const dlBtn = document.getElementById('download-btn');
    if (dlBtn) {
        dlBtn.style.display = "inline-flex";

        dlBtn.addEventListener('click', async () => {
            const offlineState = await getCurrentChapterOfflineState();
            const state = getCurrentState();

            if (state.sourceType === 'youtube' || offlineState.status === 'not_available') {
                showToast(offlineState.reason || "This source cannot be downloaded in browser");
                return;
            }

            if (offlineState.status === OFFLINE_STATES.downloaded) {
                await deleteChapter();
                renderChapterList(state.book);
                updateUI(state.isPlaying, state.book);
                showToast("Chapter removed from offline shelf");
                return;
            }

            if (offlineState.status === OFFLINE_STATES.queued || offlineState.status === OFFLINE_STATES.downloading) {
                showToast("This chapter is already in your offline queue");
                return;
            }

            setButtonLoading(dlBtn, 'Saving');
            const result = await downloadCurrentChapter();
            resetButtonLoading(dlBtn);
            renderChapterList(state.book);
            updateUI(state.isPlaying, state.book);

            if (result?.queued) {
                showToast(window.AndroidInterface ? "Downloading for offline use" : "Chapter added to your offline queue");
            } else {
                showToast(result?.reason || "Offline download could not start");
            }
        });
    }

    const downloadBookBtn = document.getElementById('download-book-btn');
    if (downloadBookBtn && downloadBookBtn.parentNode) {
        downloadBookBtn.addEventListener('click', async () => {
            const state = getCurrentState();
            if (!state.book) return;

            setButtonLoading(downloadBookBtn, 'Queueing');
            const result = await queueCurrentBookForOffline();
            resetButtonLoading(downloadBookBtn);
            renderChapterList(state.book);
            updateUI(state.isPlaying, state.book);

            if (result?.queuedCount > 0) {
                showToast(`${result.queuedCount} parts added to your offline queue`);
            } else {
                showToast(result?.reason || "Book download queue could not start");
            }
        });
    }

    const removeBookBtn = document.getElementById('remove-offline-book-btn');
    if (removeBookBtn && removeBookBtn.parentNode) {
        removeBookBtn.addEventListener('click', async () => {
            const state = getCurrentState();
            if (!state.book) return;

            setButtonLoading(removeBookBtn, 'Removing');
            await removeCurrentBookOffline();
            resetButtonLoading(removeBookBtn);
            renderChapterList(state.book);
            updateUI(state.isPlaying, state.book);
            showToast("Offline copies cleared for this book");
        });
    }

    const shareBookBtn = document.getElementById('share-book-btn');
    if (shareBookBtn && shareBookBtn.parentNode) {
        shareBookBtn.addEventListener('click', async () => {
            const state = getCurrentState();
            if (!state.book) return;
            if (window.VibePWA?.shareAudiobook) {
                await window.VibePWA.shareAudiobook({
                    title: state.book.title,
                    author: state.book.author,
                    bookId: state.book.bookId
                });
            }
        });
    }
}
