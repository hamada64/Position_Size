// 1. Updated version name to force the browser to refresh the cache
const CACHE_NAME = 'bond-calc-v2'; 

const ASSETS = [
  'index.html',
  'manifest.json',
  'icon-512.png' // 2. Added your new icon to the cache list
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('Caching new assets');
      return cache.addAll(ASSETS);
    })
  );
});

// This helps the new service worker take control immediately
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            console.log('Deleting old cache');
            return caches.delete(cache);
          }
        })
      );
    })
  );
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then(res => res || fetch(e.request))
  );
});