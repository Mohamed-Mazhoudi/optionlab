// Service worker de l'appli OptionLab (servi sur /sw.js pour couvrir tout le site).
// Stratégie « réseau d'abord » : en ligne, on sert toujours la dernière version déployée ;
// hors ligne, on retombe sur la copie en cache (le simulateur passe alors en prix simulés).
// L'API (/api/...) n'est jamais mise en cache : comptes, portefeuille et cours restent en direct.
const CACHE = "optionlab-v1";
const SHELL = [
  "/", "/labo",
  "/static/style.css", "/static/app.js", "/static/lessons.js", "/static/portfolio.js",
  "/static/icons/icon-192.png", "/manifest.webmanifest",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/")
      || url.pathname === "/docs" || url.pathname === "/openapi.json") {
    return;  // laissé au navigateur, sans cache
  }
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok && res.type === "basic") {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(url.pathname === "/" ? "/" : req, copy));
        }
        return res;
      })
      .catch(async () => {
        const cached = await caches.match(req, { ignoreSearch: req.mode === "navigate" });
        if (cached) return cached;
        if (req.mode === "navigate") return caches.match("/");
        return Response.error();
      })
  );
});
