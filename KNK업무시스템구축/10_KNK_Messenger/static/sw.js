// KNK Messenger Service Worker — 정적 자원 캐시 + 오프라인 폴백
const CACHE = "knk-messenger-v1";
const PRECACHE = [
  "/static/css/style.css",
  "/static/js/app.js",
  "/static/manifest.json",
  "/static/icons/icon.svg",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  // API/소켓/업로드는 항상 네트워크
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/socket.io") || url.pathname.startsWith("/uploads/")) {
    return;
  }
  // 정적 자원: 네트워크 먼저, 실패 시 캐시
  if (e.request.method === "GET" && (url.pathname.startsWith("/static/") || url.pathname === "/chat" || url.pathname === "/login")) {
    e.respondWith(
      fetch(e.request)
        .then(res => {
          if (res.ok && url.pathname.startsWith("/static/")) {
            const copy = res.clone();
            caches.open(CACHE).then(c => c.put(e.request, copy));
          }
          return res;
        })
        .catch(() => caches.match(e.request))
    );
  }
});

// Push notifications 핸들러 (서버에서 push 보낼 때 사용)
self.addEventListener("push", (e) => {
  let data = {};
  try { data = e.data ? e.data.json() : {}; } catch (err) { data = { title: "KNK 메신저", body: e.data?.text() || "" }; }
  const title = data.title || "KNK 메신저";
  const opts = {
    body: data.body || "",
    icon: "/static/icons/icon-192.png",
    badge: "/static/icons/icon-192.png",
    data: data.url ? { url: data.url } : { url: "/chat" },
    tag: data.tag,
  };
  e.waitUntil(self.registration.showNotification(title, opts));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = e.notification.data?.url || "/chat";
  e.waitUntil(
    clients.matchAll({ type: "window" }).then(list => {
      for (const c of list) {
        if (c.url.includes(url) && "focus" in c) return c.focus();
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});
