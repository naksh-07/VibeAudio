const CACHE_VERSION = 'v14-production';
const STATIC_CACHE_NAME = `vibeaudio-static-${CACHE_VERSION}`;
const RUNTIME_CACHE_NAME = `vibeaudio-runtime-${CACHE_VERSION}`;
const DATA_CACHE_NAME = `vibeaudio-data-${CACHE_VERSION}`;
const IMAGE_CACHE_NAME = `vibeaudio-images-${CACHE_VERSION}`;
const CACHE_NAMES = [STATIC_CACHE_NAME, RUNTIME_CACHE_NAME, DATA_CACHE_NAME, IMAGE_CACHE_NAME];
const MAX_WARM_URLS = 24;

const PRECACHE_URLS = [
    './',
    './index.html',
    './app.webmanifest',
    './src/pages/app.html',
    './src/css/base.css',
    './src/css/app-sections.css',
    './src/css/components.css',
    './src/css/cover-media.css',
    './src/css/landing.css',
    './src/css/player.css',
    './src/css/player-premium.css',
    './src/js/api.js',
    './src/js/app-entry.js',
    './src/js/auth.js',
    './src/js/config.js',
    './src/js/landing.js',
    './src/js/offline-shelf.js',
    './src/js/player.js',
    './src/js/progress-model.js',
    './src/js/pwa.js',
    './src/js/ui-dom.js',
    './src/js/ui-formatters.js',
    './src/js/ui.js',
    './src/js/ui-library.js',
    './src/js/ui-library-insights.js',
    './src/js/ui-player-helpers.js',
    './src/js/ui-player-list.js',
    './src/js/ui-player-main.js',
    './src/js/user-data.js',
    './src/icons/favicon.png',
    './src/icons/favicon.svg',
    './src/icons/favicon-16.png',
    './src/icons/favicon-32.png',
    './src/icons/icons.svg',
    './public/icons/logo.png',
    './public/icons/brand-mark.svg',
    './public/icons/icon-192.png',
    './public/icons/icon-512.png',
    './public/icons/icon-maskable-512.png',
    './public/icons/apple-touch-icon.png'
];

function normalizePathname(value) {
    const pathname = String(value || '/').replace(/\/+$/, '');
    return pathname || '/';
}

function isAppShellPath(pathname) {
    const normalized = normalizePathname(pathname);
    return normalized.endsWith('/src/pages/app') || normalized.endsWith('/src/pages/app.html');
}

function isLandingPath(pathname) {
    const normalized = normalizePathname(pathname);
    return normalized === '/' || normalized.endsWith('/index.html');
}

function isSensitiveOrAuthUrl(url) {
    const hostname = String(url.hostname || '').toLowerCase();
    const pathname = String(url.pathname || '').toLowerCase();

    if (hostname.includes('clerk') || hostname.includes('accounts.dev')) {
        return true;
    }

    if (pathname.includes('progress') || pathname.includes('sync-user') || pathname.includes('user-data')) {
        return true;
    }

    return false;
}

function isJsonLikeRequest(request, url) {
    if (isSensitiveOrAuthUrl(url)) return false;

    const accept = String(request.headers.get('accept') || '').toLowerCase();
    return url.pathname.toLowerCase().endsWith('.json')
        || accept.includes('application/json')
        || accept.includes('text/json');
}

function looksLikeImageUrl(url) {
    return /\.(png|jpe?g|webp|gif|svg|avif|ico)(?:$|\?)/i.test(url.pathname);
}

function isImageRequest(request, url) {
    return request.destination === 'image' || looksLikeImageUrl(url);
}

function isStyleScriptOrFontRequest(request, url) {
    if (['style', 'script', 'font'].includes(request.destination)) {
        return true;
    }
    return /\.(css|js|mjs|woff2?|ttf|otf|eot)(?:$|\?)/i.test(url.pathname);
}

function isCacheableStaticRequest(request, url) {
    if (isSensitiveOrAuthUrl(url)) return false;

    if (url.origin === self.location.origin && isStyleScriptOrFontRequest(request, url)) {
        return true;
    }

    if (request.destination === 'manifest') return true;
    if (url.origin !== self.location.origin && isStyleScriptOrFontRequest(request, url)) {
        return true;
    }

    return false;
}

function canCacheResponse(response) {
    return Boolean(response) && (response.ok || response.type === 'opaque');
}

async function getCanonicalAppShell(cache) {
    return (await cache.match('./src/pages/app.html'))
        || (await cache.match(new Request(new URL('./src/pages/app.html', self.location.href).href)))
        || (await cache.match(new Request(new URL('./src/pages/app', self.location.href).href)));
}

async function putAppShellAliases(cache, response) {
    await cache.put('./src/pages/app.html', response.clone());
    await cache.put(new Request(new URL('./src/pages/app.html', self.location.href).href), response.clone());
    await cache.put(new Request(new URL('./src/pages/app', self.location.href).href), response.clone());
}

async function warmPrecacheShell() {
    const cache = await caches.open(STATIC_CACHE_NAME);
    await Promise.allSettled(PRECACHE_URLS.map((url) => cache.add(url)));

    const appShell = await cache.match('./src/pages/app.html');
    if (appShell) {
        await putAppShellAliases(cache, appShell.clone());
    }
}

function resolveRuntimeCacheName(request, url) {
    if (isSensitiveOrAuthUrl(url)) return null;
    if (isJsonLikeRequest(request, url)) return DATA_CACHE_NAME;
    if (isImageRequest(request, url)) return IMAGE_CACHE_NAME;
    if (isCacheableStaticRequest(request, url)) return RUNTIME_CACHE_NAME;
    return null;
}

async function cacheRuntimeResponse(request, url, response) {
    const cacheName = resolveRuntimeCacheName(request, url);
    if (!cacheName || !canCacheResponse(response)) return;

    const cache = await caches.open(cacheName);
    await cache.put(request, response.clone());
}

async function networkFirst(request, url) {
    const cacheName = resolveRuntimeCacheName(request, url);
    const cache = cacheName ? await caches.open(cacheName) : null;

    try {
        const response = await fetch(request);
        if (cache && canCacheResponse(response)) {
            await cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        if (cache) {
            const cached = await cache.match(request);
            if (cached) return cached;
        }
        return Response.error();
    }
}

async function staleWhileRevalidate(request, url, event) {
    const cacheName = resolveRuntimeCacheName(request, url);
    if (!cacheName) {
        try {
            return await fetch(request);
        } catch (error) {
            return Response.error();
        }
    }

    const cache = await caches.open(cacheName);
    const cached = await cache.match(request);
    const networkPromise = fetch(request)
        .then(async (response) => {
            if (canCacheResponse(response)) {
                await cache.put(request, response.clone());
            }
            return response;
        })
        .catch(() => null);

    if (cached) {
        event.waitUntil(networkPromise);
        return cached;
    }

    const fresh = await networkPromise;
    return fresh || Response.error();
}

async function cacheNavigationResponse(request, response) {
    if (!canCacheResponse(response)) return;

    const cache = await caches.open(STATIC_CACHE_NAME);
    const requestUrl = new URL(request.url);
    const responseUrl = new URL(response.url || request.url);

    if (isAppShellPath(requestUrl.pathname) || isAppShellPath(responseUrl.pathname)) {
        await putAppShellAliases(cache, response.clone());
        return;
    }

    if (isLandingPath(requestUrl.pathname) || isLandingPath(responseUrl.pathname)) {
        await cache.put('./index.html', response.clone());
        return;
    }

    await cache.put(request, response.clone());
}

async function handleNavigationRequest(request) {
    const cache = await caches.open(STATIC_CACHE_NAME);
    const url = new URL(request.url);

    try {
        const response = await fetch(request);
        await cacheNavigationResponse(request, response.clone());
        return response;
    } catch (error) {
        const directMatch = await cache.match(request);
        if (directMatch) return directMatch;

        if (isAppShellPath(url.pathname)) {
            return (await getCanonicalAppShell(cache))
                || (await cache.match('./src/pages/app.html'))
                || (await cache.match('./index.html'))
                || Response.error();
        }

        return (await cache.match('./index.html'))
            || (await getCanonicalAppShell(cache))
            || (await cache.match('./src/pages/app.html'))
            || Response.error();
    }
}

async function warmUrls(urls = []) {
    const uniqueUrls = Array.from(new Set(
        urls
            .map((value) => {
                try {
                    return new URL(String(value || ''), self.location.href).href;
                } catch (error) {
                    return '';
                }
            })
            .filter(Boolean)
    )).slice(0, MAX_WARM_URLS);

    await Promise.allSettled(uniqueUrls.map(async (urlValue) => {
        const url = new URL(urlValue);
        if (isSensitiveOrAuthUrl(url)) return;

        const isRemoteImage = url.origin !== self.location.origin && /\.(png|jpe?g|webp|gif|svg|avif)(?:$|\?)/i.test(url.pathname);
        const request = new Request(urlValue, {
            method: 'GET',
            mode: isRemoteImage ? 'no-cors' : 'cors'
        });
        const response = await fetch(request);

        if (!canCacheResponse(response)) return;

        if (url.origin === self.location.origin && isAppShellPath(url.pathname)) {
            const cache = await caches.open(STATIC_CACHE_NAME);
            await putAppShellAliases(cache, response.clone());
            return;
        }

        if (url.origin === self.location.origin && isLandingPath(url.pathname)) {
            const cache = await caches.open(STATIC_CACHE_NAME);
            await cache.put('./index.html', response.clone());
            return;
        }

        await cacheRuntimeResponse(request, url, response.clone());
    }));
}

self.addEventListener('install', (event) => {
    self.skipWaiting();
    event.waitUntil(warmPrecacheShell());
});

self.addEventListener('activate', (event) => {
    event.waitUntil((async () => {
        const keys = await caches.keys();
        await Promise.all(keys.filter((key) => !CACHE_NAMES.includes(key)).map((key) => caches.delete(key)));
        await self.clients.claim();
    })());
});

self.addEventListener('message', (event) => {
    const data = event.data || {};

    if (data.type === 'SKIP_WAITING') {
        self.skipWaiting();
        return;
    }

    if (data.type === 'CACHE_URLS' && Array.isArray(data.urls)) {
        event.waitUntil?.(warmUrls(data.urls));
    }
});

self.addEventListener('fetch', (event) => {
    const { request } = event;
    if (request.method !== 'GET') return;

    if (request.mode === 'navigate') {
        event.respondWith(handleNavigationRequest(request));
        return;
    }

    const url = new URL(request.url);
    if (isSensitiveOrAuthUrl(url)) return;

    const cacheName = resolveRuntimeCacheName(request, url);
    if (!cacheName) return;

    if (isJsonLikeRequest(request, url)) {
        event.respondWith(networkFirst(request, url));
        return;
    }

    event.respondWith(staleWhileRevalidate(request, url, event));
});

/* ==========================================
   PWA NATIVE STAGE 2: BACKGROUND SYNC & FETCH
   ========================================== */

const SW_SYNC_DB_NAME = 'vibeaudio-sync-v1';
const SW_SYNC_STORE_NAME = 'sync_progress_queue';
const SW_OFFLINE_DB_NAME = 'vibeaudio-offline-v1';
const PROGRESS_LAMBDA_URL = 'https://rrsv2aw64zkkgpdhkamz57ftr40tchro.lambda-url.ap-south-1.on.aws/';

function openSwSyncDb() {
    return new Promise((resolve, reject) => {
        try {
            const req = indexedDB.open(SW_SYNC_DB_NAME, 1);
            req.onerror = () => reject(req.error || new Error('Failed to open sync DB'));
            req.onupgradeneeded = () => {
                const db = req.result;
                if (!db.objectStoreNames.contains(SW_SYNC_STORE_NAME)) {
                    const store = db.createObjectStore(SW_SYNC_STORE_NAME, { keyPath: 'id' });
                    store.createIndex('by_user', 'userId');
                    store.createIndex('by_updated', 'lastInteractionAt');
                }
            };
            req.onsuccess = () => resolve(req.result);
        } catch (error) {
            reject(error);
        }
    });
}

function openSwOfflineDb() {
    return new Promise((resolve, reject) => {
        try {
            const req = indexedDB.open(SW_OFFLINE_DB_NAME, 1);
            req.onerror = () => reject(req.error || new Error('Failed to open offline DB'));
            req.onsuccess = () => resolve(req.result);
        } catch (error) {
            reject(error);
        }
    });
}

async function handleBackgroundProgressSync() {
    let db;
    try {
        db = await openSwSyncDb();
    } catch (err) {
        console.warn('[SW Sync] Unable to open sync database:', err);
        return;
    }

    const entries = await new Promise((resolve) => {
        try {
            const tx = db.transaction(SW_SYNC_STORE_NAME, 'readonly');
            const store = tx.objectStore(SW_SYNC_STORE_NAME);
            const req = store.getAll();
            req.onsuccess = () => resolve(Array.isArray(req.result) ? req.result : []);
            req.onerror = () => resolve([]);
        } catch (_) {
            resolve([]);
        }
    });

    if (!entries.length) return;

    const eligible = entries.filter((e) => e.userId && e.userId !== 'guest');
    if (!eligible.length) return;

    let hadErrors = false;

    for (const entry of eligible) {
        try {
            const response = await fetch(PROGRESS_LAMBDA_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(entry)
            });

            if (response.ok) {
                await new Promise((resolve) => {
                    try {
                        const tx = db.transaction(SW_SYNC_STORE_NAME, 'readwrite');
                        const store = tx.objectStore(SW_SYNC_STORE_NAME);
                        const req = store.delete(entry.id);
                        req.onsuccess = () => resolve(true);
                        req.onerror = () => resolve(false);
                    } catch (_) {
                        resolve(false);
                    }
                });
            } else {
                hadErrors = true;
            }
        } catch (netErr) {
            hadErrors = true;
        }
    }

    try {
        const clients = await self.clients.matchAll({ type: 'window' });
        for (const client of clients) {
            client.postMessage({
                type: 'BACKGROUND_SYNC_COMPLETE',
                success: !hadErrors
            });
        }
    } catch (_) {}

    if (hadErrors) {
        throw new Error('Background progress sync encountered network errors.');
    }
}

self.addEventListener('sync', (event) => {
    if (event.tag === 'vibeaudio-progress-sync') {
        event.waitUntil(handleBackgroundProgressSync());
    }
});

self.addEventListener('backgroundfetchsuccess', (event) => {
    event.waitUntil((async () => {
        const bgFetch = event.registration;
        const jobId = bgFetch.id;
        const match = jobId.match(/^vibe-bf-(.+)-(.+)-([a-z]{2})-(\d+)$/);
        if (!match) return;

        const userId = decodeURIComponent(match[1]);
        const bookId = decodeURIComponent(match[2]);
        const lang = match[3];
        const chapterIndex = Number(match[4]);
        const chapterId = `${userId}::${bookId}::${lang}::${chapterIndex}`;
        const jId = `job::${chapterId}`;

        const records = await bgFetch.matchAll();
        if (!records.length) return;

        let blob = null;
        let mimeType = 'audio/mpeg';

        for (const record of records) {
            try {
                const response = await record.responseReady;
                if (response && response.ok) {
                    blob = await response.blob();
                    mimeType = response.headers.get('content-type') || mimeType;
                    break;
                }
            } catch (_) {}
        }

        if (!blob || blob.size === 0) return;

        try {
            const db = await openSwOfflineDb();
            const tx = db.transaction(['offline_chapters', 'offline_jobs'], 'readwrite');
            const chStore = tx.objectStore('offline_chapters');
            const jobStore = tx.objectStore('offline_jobs');

            const existingChapter = await new Promise((res) => {
                const req = chStore.get(chapterId);
                req.onsuccess = () => res(req.result || null);
                req.onerror = () => res(null);
            });

            const now = new Date().toISOString();
            const nextChapter = {
                ...existingChapter,
                id: chapterId,
                userId,
                bookId,
                lang,
                chapterIndex,
                status: 'downloaded',
                storageType: 'indexeddb_blob',
                fallbackBlob: blob,
                sizeBytes: blob.size,
                mimeType,
                downloadedAt: now,
                validatedAt: now,
                progressBytes: blob.size,
                progressPercent: 100,
                errorReason: '',
                lastTouchedAt: now
            };

            chStore.put(nextChapter);
            jobStore.delete(jId);

            await new Promise((res, rej) => {
                tx.oncomplete = () => res();
                tx.onerror = () => rej(tx.error);
            });

            const clients = await self.clients.matchAll({ type: 'window' });
            clients.forEach((client) => {
                client.postMessage({
                    type: 'OFFLINE_DOWNLOAD_COMPLETE',
                    bookId,
                    lang,
                    chapterIndex
                });
            });
        } catch (dbErr) {
            console.warn('[SW BgFetch] Error writing downloaded chapter:', dbErr);
        }
    })());
});

self.addEventListener('backgroundfetchfail', (event) => {
    event.waitUntil((async () => {
        const bgFetch = event.registration;
        const match = bgFetch.id.match(/^vibe-bf-(.+)-(.+)-([a-z]{2})-(\d+)$/);
        if (!match) return;

        const userId = decodeURIComponent(match[1]);
        const bookId = decodeURIComponent(match[2]);
        const lang = match[3];
        const chapterIndex = Number(match[4]);
        const chapterId = `${userId}::${bookId}::${lang}::${chapterIndex}`;
        const jId = `job::${chapterId}`;

        try {
            const db = await openSwOfflineDb();
            const tx = db.transaction(['offline_chapters', 'offline_jobs'], 'readwrite');
            const chStore = tx.objectStore('offline_chapters');
            const jobStore = tx.objectStore('offline_jobs');

            const existingChapter = await new Promise((res) => {
                const req = chStore.get(chapterId);
                req.onsuccess = () => res(req.result || null);
                req.onerror = () => res(null);
            });

            if (existingChapter && existingChapter.status !== 'downloaded') {
                chStore.put({
                    ...existingChapter,
                    status: 'failed',
                    errorReason: 'Background download interrupted',
                    lastTouchedAt: new Date().toISOString()
                });
            }

            const existingJob = await new Promise((res) => {
                const req = jobStore.get(jId);
                req.onsuccess = () => res(req.result || null);
                req.onerror = () => res(null);
            });

            if (existingJob) {
                jobStore.put({
                    ...existingJob,
                    status: 'failed',
                    errorReason: 'Background download interrupted',
                    updatedAt: new Date().toISOString()
                });
            }
        } catch (_) {}
    })());
});

self.addEventListener('backgroundfetchabort', (event) => {
    event.waitUntil((async () => {
        const bgFetch = event.registration;
        const match = bgFetch.id.match(/^vibe-bf-(.+)-(.+)-([a-z]{2})-(\d+)$/);
        if (!match) return;

        const userId = decodeURIComponent(match[1]);
        const bookId = decodeURIComponent(match[2]);
        const lang = match[3];
        const chapterIndex = Number(match[4]);
        const chapterId = `${userId}::${bookId}::${lang}::${chapterIndex}`;
        const jId = `job::${chapterId}`;

        try {
            const db = await openSwOfflineDb();
            const tx = db.transaction(['offline_chapters', 'offline_jobs'], 'readwrite');
            const chStore = tx.objectStore('offline_chapters');
            const jobStore = tx.objectStore('offline_jobs');

            const existingChapter = await new Promise((res) => {
                const req = chStore.get(chapterId);
                req.onsuccess = () => res(req.result || null);
                req.onerror = () => res(null);
            });

            if (existingChapter && existingChapter.status !== 'downloaded') {
                chStore.put({
                    ...existingChapter,
                    status: 'queued',
                    errorReason: 'Download paused',
                    lastTouchedAt: new Date().toISOString()
                });
            }

            const existingJob = await new Promise((res) => {
                const req = jobStore.get(jId);
                req.onsuccess = () => res(req.result || null);
                req.onerror = () => res(null);
            });

            if (existingJob) {
                jobStore.put({
                    ...existingJob,
                    status: 'queued',
                    errorReason: 'Download paused',
                    updatedAt: new Date().toISOString()
                });
            }
        } catch (_) {}
    })());
});

self.addEventListener('backgroundclick', (event) => {
    event.waitUntil((async () => {
        const clients = await self.clients.matchAll({ type: 'window' });
        for (const client of clients) {
            if (client.url.includes('/src/pages/app') && 'focus' in client) {
                return client.focus();
            }
        }
        if (self.clients.openWindow) {
            return self.clients.openWindow('./src/pages/app.html#offline');
        }
    })());
});
