// Saralash service worker. Kesh nomi har buildda yangilanadi.
const VERSION = "__VERSION__";
const SHELL = "shell-" + VERSION;
const DATA = "data-v1";
const ASSETS = __ASSETS__;

self.addEventListener("install", (e) => {
  // Biror fayl yuklanmasa o'rnatish muvaffaqiyatsiz bo'ladi va keyinroq qayta uriniladi (yarim kesh qolmaydi)
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(ASSETS)));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k.startsWith("shell-") && k !== SHELL).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("message", (e) => { if (e.data === "skip-waiting") self.skipWaiting(); });

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.includes("/data/")) {
    // Ma'lumot: avval tarmoq (yangi tahlil), bo'lmasa keshdagi oxirgi nusxa (offline)
    e.respondWith(fetch(e.request).then((r) => {
      if (r.ok) { const copy = r.clone(); caches.open(DATA).then((c) => c.put(e.request, copy)); }
      return r;
    }).catch(() => caches.match(e.request).then((m) => m || Response.error())));
    return;
  }
  e.respondWith(caches.match(e.request, { ignoreSearch: true }).then((m) => m || fetch(e.request).catch(() => caches.match("./"))));
});
