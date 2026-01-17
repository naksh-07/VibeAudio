// --- PWA Smart Service Worker ---
const CACHE_NAME = 'vibe-audio-v2'; // Update hone par v3, v4 kar dena
const ASSETS_TO_CACHE = [
    './', './index.html', './style.css', './script.js', './books.json',
    './manifest.json', './pngs/logo.png',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap'
];

self.addEventListener('install', (event) => {
    self.skipWaiting(); // Turant install ho
    event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS_TO_CACHE)));
});

self.addEventListener('activate', (event) => {
    event.waitUntil(caches.keys().then(keys => Promise.all(
        keys.map(key => key !== CACHE_NAME ? caches.delete(key) : null)
    )));
    self.clients.claim(); // Turant control le
});

self.addEventListener('fetch', (event) => {
    if (event.request.url.includes('drive.google.com')) return; // Audio files cache mat karo
    event.respondWith(caches.match(event.request).then(res => res || fetch(event.request)));
});