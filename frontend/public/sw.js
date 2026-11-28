const CACHE_NAME = 'vistazo-shell-v2';
const SHELL_URLS = [
  '/',
  '/manifest.webmanifest',
  '/brand/vistazo-icon.png',
  '/brand/vistazo-logo.png',
  '/icons/icon-192.png',
  '/icons/favicon-64.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_URLS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET' || event.request.url.includes('/api/')) {
    return;
  }
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});

self.addEventListener('push', (event) => {
  const payload = event.data ? event.data.json() : {};
  const title = payload.title || 'Vistazo LMS';
  const options = {
    body: payload.body || 'Tienes repasos espaciados pendientes hoy.',
    icon: '/icons/icon-192.png',
    badge: '/icons/favicon-64.png',
  };
  event.waitUntil(self.registration.showNotification(title, options));
});
