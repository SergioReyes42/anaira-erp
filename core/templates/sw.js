// core/static/sw.js
const CACHE_NAME = 'anaira-erp-v1';
const urlsToCache = [
  '/',
  '/static/css/bootstrap.min.css',
  '/static/img/logo-icon.png'
];

self.addEventListener('install', event => {
  // Instalación del Service Worker
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  // Responder con caché si existe, sino ir a internet
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});