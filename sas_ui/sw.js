/* SAS service worker — app shell cache + live-first API. */
const CACHE = "sas-v1";
const SHELL = ["/dashboard", "/icon.svg", "/icon-maskable.svg", "/manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;

  // Live data (/api, /health) and auth: always network, never cache.
  if (url.pathname.startsWith("/api") || url.pathname === "/health" ||
      url.pathname === "/login" || url.pathname === "/logout") {
    return;
  }

  // App shell: cache-first, fall back to network, then offline shell.
  e.respondWith(
    caches.match(e.request).then((hit) =>
      hit ||
      fetch(e.request)
        .then((resp) => {
          const copy = resp.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
          return resp;
        })
        .catch(() => caches.match("/dashboard"))
    )
  );
});
