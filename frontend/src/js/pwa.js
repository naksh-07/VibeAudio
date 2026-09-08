const SERVICE_WORKER_URL = new URL('../../service-worker.js', import.meta.url);
const SERVICE_WORKER_SCOPE = new URL('../../', import.meta.url);
const OFFLINE_READY_KEY = 'vibe_offline_shell_ready';
const SHELL_WARMUP_URLS = [
    './',
    './index.html',
    './app.webmanifest',
    './src/pages/app.html'
];

let deferredInstallPrompt = null;
let installDismissed = false;

function isStandaloneMode() {
    if (typeof window === 'undefined') return false;
    return window.matchMedia?.('(display-mode: standalone)')?.matches
        || window.matchMedia?.('(display-mode: minimal-ui)')?.matches
        || window.navigator?.standalone === true;
}

function isLikelyMobileDevice() {
    if (typeof window === 'undefined' || typeof navigator === 'undefined') return false;
    return /android|iphone|ipad|ipod/i.test(navigator.userAgent || '') || Boolean(window.matchMedia?.('(max-width: 920px)')?.matches);
}

function showPwaToast(message) {
    if (typeof document === 'undefined' || !document.body) return;

    const existing = document.querySelector('.vibe-pwa-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'vibe-pwa-toast';
    toast.textContent = message;
    toast.style.position = 'fixed';
    toast.style.left = '50%';
    toast.style.bottom = 'max(24px, calc(16px + env(safe-area-inset-bottom, 0px)))';
    toast.style.transform = 'translateX(-50%)';
    toast.style.padding = '12px 20px';
    toast.style.borderRadius = '12px';
    toast.style.background = 'rgba(22, 24, 31, 0.96)';
    toast.style.color = '#F5F6FA';
    toast.style.border = '1px solid rgba(229, 169, 60, 0.28)';
    toast.style.boxShadow = '0 16px 40px rgba(0, 0, 0, 0.55)';
    toast.style.zIndex = '5000';
    toast.style.fontSize = '0.88rem';
    toast.style.fontFamily = "'Inter', sans-serif";
    toast.style.letterSpacing = '0.01em';
    toast.style.pointerEvents = 'none';
    toast.style.transition = 'opacity 240ms ease, transform 240ms ease';
    document.body.appendChild(toast);

    window.setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-50%) translateY(8px)';
        window.setTimeout(() => toast.remove(), 260);
    }, 3200);
}

function readOfflineReadyState() {
    try {
        const raw = localStorage.getItem(OFFLINE_READY_KEY);
        if (!raw) return null;
        return JSON.parse(raw);
    } catch (error) {
        console.warn('Unable to read offline readiness state.', error);
        return null;
    }
}

function markOfflineReady(source = 'service-worker') {
    const payload = {
        ready: true,
        source,
        updatedAt: new Date().toISOString()
    };

    try {
        localStorage.setItem(OFFLINE_READY_KEY, JSON.stringify(payload));
    } catch (error) {
        console.warn('Unable to persist offline readiness state.', error);
    }

    window.dispatchEvent(new CustomEvent('vibe-pwa-ready', { detail: payload }));
    return payload;
}

function uniqueAbsoluteUrls(urls = []) {
    return Array.from(new Set(
        urls
            .map((value) => {
                try {
                    return new URL(String(value || ''), window.location.href).href;
                } catch (error) {
                    return '';
                }
            })
            .filter(Boolean)
    ));
}

async function getServiceWorkerTarget() {
    if (!('serviceWorker' in navigator)) return null;

    try {
        const registration = await navigator.serviceWorker.ready;
        return registration?.active || registration?.waiting || navigator.serviceWorker.controller || null;
    } catch (error) {
        console.warn('Service worker is not ready yet.', error);
        return navigator.serviceWorker.controller || null;
    }
}

async function sendServiceWorkerMessage(message) {
    const target = await getServiceWorkerTarget();
    if (!target) return false;

    target.postMessage(message);
    return true;
}

async function primeOfflineResources(urls = []) {
    const normalizedUrls = uniqueAbsoluteUrls([...SHELL_WARMUP_URLS, ...urls]);
    if (!normalizedUrls.length) return false;

    const sent = await sendServiceWorkerMessage({
        type: 'CACHE_URLS',
        urls: normalizedUrls
    });

    if (sent) {
        markOfflineReady('cache-message');
    }

    return sent;
}

function isOfflineShellLikelyReady() {
    if (navigator.serviceWorker?.controller) return true;
    return Boolean(readOfflineReadyState()?.ready);
}

async function requestPersistentStorage() {
    if (!navigator.storage?.persisted || !navigator.storage?.persist) return false;

    try {
        const alreadyPersisted = await navigator.storage.persisted();
        if (alreadyPersisted) {
            markOfflineReady('persistent-storage');
            return true;
        }

        const granted = await navigator.storage.persist();
        if (granted) {
            markOfflineReady('persistent-storage');
        }
        return granted;
    } catch (error) {
        console.warn('Persistent storage request skipped.', error);
        return false;
    }
}

let lastSyncRegistrationTime = 0;
const SYNC_REGISTRATION_THROTTLE_MS = 3000;

export function isBackgroundSyncSupported() {
    return typeof window !== 'undefined' && 'SyncManager' in window && 'serviceWorker' in navigator;
}

export function isBackgroundFetchSupported() {
    return typeof window !== 'undefined' && ('BackgroundFetchManager' in window || (typeof ServiceWorkerRegistration !== 'undefined' && 'backgroundFetch' in ServiceWorkerRegistration.prototype));
}

export function isFileHandlingSupported() {
    return typeof window !== 'undefined' && 'launchQueue' in window && typeof window.launchQueue?.setConsumer === 'function';
}

export function isWebShareSupported() {
    return typeof navigator !== 'undefined' && typeof navigator.share === 'function';
}

export function isBadgingSupported() {
    return typeof navigator !== 'undefined' && ('setAppBadge' in navigator || 'clearAppBadge' in navigator);
}

export function isLaunchHandlerSupported() {
    return typeof window !== 'undefined' && 'launchQueue' in window;
}

export async function updateAppBadge(count = 0) {
    if (typeof navigator === 'undefined') return false;
    const numericCount = Math.max(0, parseInt(count, 10) || 0);
    try {
        if (numericCount > 0 && typeof navigator.setAppBadge === 'function') {
            await navigator.setAppBadge(numericCount);
            return true;
        } else if (typeof navigator.clearAppBadge === 'function') {
            await navigator.clearAppBadge();
            return true;
        }
    } catch (error) {
        console.warn('App badge update skipped or unsupported.', error);
    }
    return false;
}

export async function clearAppBadge() {
    return updateAppBadge(0);
}

export async function shareAudiobook(options = {}) {
    const title = String(options.title || 'VibeAudio Audiobook').trim();
    const author = String(options.author || '').trim();
    const bookId = options.bookId ? String(options.bookId).trim() : '';

    let shareUrl = options.url || '';
    if (!shareUrl) {
        try {
            if (typeof window !== 'undefined' && window.location) {
                const base = new URL(window.location.href);
                base.hash = bookId ? `#player?book=${encodeURIComponent(bookId)}` : '#home';
                base.search = '';
                shareUrl = base.href;
            } else {
                shareUrl = bookId ? `https://vibeaudio.app/#player?book=${encodeURIComponent(bookId)}` : 'https://vibeaudio.app/#home';
            }
        } catch (_) {
            shareUrl = 'https://vibeaudio.app/#home';
        }
    }

    const shareText = author ? `Listen to "${title}" by ${author} on VibeAudio` : `Listen to "${title}" on VibeAudio`;

    if (isWebShareSupported()) {
        try {
            await navigator.share({
                title,
                text: shareText,
                url: shareUrl
            });
            return { shared: true, method: 'navigator.share' };
        } catch (error) {
            if (error?.name === 'AbortError') {
                return { shared: false, aborted: true, method: 'navigator.share' };
            }
            console.warn('Native share sheet failed, falling back to clipboard.', error);
        }
    }

    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        try {
            await navigator.clipboard.writeText(shareUrl);
            showPwaToast('Audiobook link copied to clipboard.');
            return { shared: true, method: 'clipboard' };
        } catch (clipboardErr) {
            console.warn('Clipboard copy failed.', clipboardErr);
        }
    }

    showPwaToast(`Share link: ${shareUrl}`);
    return { shared: false, method: 'prompt', url: shareUrl };
}

export async function requestProgressBackgroundSync() {
    if (!isBackgroundSyncSupported()) return false;
    const now = Date.now();
    if (now - lastSyncRegistrationTime < SYNC_REGISTRATION_THROTTLE_MS) return true;

    try {
        const registration = await navigator.serviceWorker.ready;
        if (registration && 'sync' in registration && typeof registration.sync.register === 'function') {
            await registration.sync.register('vibeaudio-progress-sync');
            lastSyncRegistrationTime = now;
            return true;
        }
    } catch (error) {
        console.warn('Background sync registration skipped or unsupported.', error);
    }
    return false;
}

function bindLaunchQueueConsumer() {
    if (typeof window === 'undefined' || !('launchQueue' in window) || window.__vibeLaunchQueueBound) return;
    window.__vibeLaunchQueueBound = true;

    try {
        window.launchQueue.setConsumer(async (launchParams) => {
            if (!launchParams) return;

            if (launchParams.files && launchParams.files.length) {
                for (const handle of launchParams.files) {
                    try {
                        const file = await handle.getFile();
                        window.dispatchEvent(new CustomEvent('vibe-file-received', { detail: { file, handle } }));
                    } catch (fileErr) {
                        console.warn('Error accessing launched file handle:', fileErr);
                    }
                }
            }

            if (launchParams.targetURL) {
                window.dispatchEvent(new CustomEvent('vibe-launch-url', { detail: { url: launchParams.targetURL } }));
            }
        });
    } catch (error) {
        console.warn('LaunchQueue registration skipped.', error);
    }
}

function bindServiceWorkerMessageBridge() {
    if (typeof navigator === 'undefined' || !('serviceWorker' in navigator) || window.__vibeSwMessageBridgeBound) return;
    window.__vibeSwMessageBridgeBound = true;

    navigator.serviceWorker.addEventListener('message', (event) => {
        const data = event.data || {};
        if (data.type === 'BACKGROUND_SYNC_COMPLETE') {
            window.dispatchEvent(new CustomEvent('vibe-background-sync-complete', { detail: data }));
        } else if (data.type === 'OFFLINE_DOWNLOAD_COMPLETE') {
            window.dispatchEvent(new CustomEvent('offline-shelf-change', {
                detail: {
                    type: 'background-download-complete',
                    bookId: data.bookId,
                    lang: data.lang,
                    chapterIndex: data.chapterIndex
                }
            }));
        }
    });
}

function exposePwaBridge() {
    bindServiceWorkerMessageBridge();
    bindLaunchQueueConsumer();
    window.VibePWA = {
        primeOfflineResources,
        isOfflineShellLikelyReady,
        requestPersistentStorage,
        isBackgroundSyncSupported,
        isBackgroundFetchSupported,
        requestProgressBackgroundSync,
        isFileHandlingSupported,
        isWebShareSupported,
        isBadgingSupported,
        isLaunchHandlerSupported,
        updateAppBadge,
        clearAppBadge,
        shareAudiobook,
        showPwaToast
    };
}

function getAllInstallButtons() {
    return Array.from(document.querySelectorAll('#install-app-btn, [data-install-btn]'));
}

function syncInstallButton() {
    const installBtns = getAllInstallButtons();
    const standalone = isStandaloneMode();
    document.body?.classList.toggle('is-standalone-app', standalone);

    installBtns.forEach((installBtn) => {
        if (!installBtn) return;

        const shouldShow = !standalone && !installDismissed && (Boolean(deferredInstallPrompt) || isLikelyMobileDevice());
        installBtn.hidden = !shouldShow;
        installBtn.classList.toggle('hidden', !shouldShow);

        if (!shouldShow) return;

        installBtn.disabled = false;
        installBtn.innerHTML = '<svg class="vibe-icon" aria-hidden="true"><use href="#icon-install"></use></svg> <span>Install App</span>';
        installBtn.title = deferredInstallPrompt
            ? 'Install VibeAudio on your device for offline listening'
            : 'Add VibeAudio to home screen for offline listening';
    });
}

async function handleInstallClick() {
    if (isStandaloneMode()) return;

    if (!deferredInstallPrompt) {
        showPwaToast('To install VibeAudio, use your browser\'s "Add to Home Screen" or "Install App" menu option.');
        return;
    }

    try {
        deferredInstallPrompt.prompt();
        const choice = await deferredInstallPrompt.userChoice;
        if (choice?.outcome === 'dismissed') {
            installDismissed = true;
        } else if (choice?.outcome === 'accepted') {
            showPwaToast('Installing VibeAudio...');
        }
    } catch (error) {
        console.warn('Install prompt was dismissed.', error);
    }

    deferredInstallPrompt = null;
    syncInstallButton();
}

function bindInstallButtons() {
    const installBtns = getAllInstallButtons();
    installBtns.forEach((installBtn) => {
        if (!installBtn || installBtn.dataset.pwaBound === 'true') return;
        installBtn.dataset.pwaBound = 'true';
        installBtn.addEventListener('click', handleInstallClick);
    });
}

async function registerServiceWorker() {
    if (!('serviceWorker' in navigator)) return;
    if (!/^https?:$/i.test(window.location.protocol)) return;

    try {
        const registration = await navigator.serviceWorker.register(SERVICE_WORKER_URL.href, { scope: SERVICE_WORKER_SCOPE.href });

        navigator.serviceWorker.addEventListener('controllerchange', () => {
            markOfflineReady('controller');
        });

        registration.addEventListener('updatefound', () => {
            const installingWorker = registration.installing;
            if (!installingWorker) return;

            installingWorker.addEventListener('statechange', () => {
                if (installingWorker.state === 'installed' && navigator.serviceWorker.controller) {
                    showPwaToast('VibeAudio updated in background. Ready for offline listening.');
                }
            });
        });

        await navigator.serviceWorker.ready;
        markOfflineReady('registration');
        await primeOfflineResources();

        if (registration.waiting) {
            registration.waiting.postMessage({ type: 'SKIP_WAITING' });
        }

        await requestPersistentStorage();
    } catch (error) {
        console.warn('Service worker registration skipped or failed.', error);
    }
}

if (typeof window !== 'undefined') {
    window.addEventListener('beforeinstallprompt', (event) => {
        event.preventDefault();
        deferredInstallPrompt = event;
        installDismissed = false;
        bindInstallButtons();
        syncInstallButton();
    });

    window.addEventListener('appinstalled', () => {
        deferredInstallPrompt = null;
        syncInstallButton();
        showPwaToast('VibeAudio installed! Launch from your home screen or shelf anytime.');
    });

    window.addEventListener('DOMContentLoaded', () => {
        exposePwaBridge();
        bindInstallButtons();
        syncInstallButton();
        registerServiceWorker();
    });

    window.matchMedia?.('(display-mode: standalone)')?.addEventListener?.('change', () => {
        syncInstallButton();
    });
}
