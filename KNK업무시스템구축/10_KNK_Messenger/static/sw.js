// KNK Messenger Service Worker — pass-through (no caching)
// 빠른 반복 개발 단계에서는 캐시 비활성화로 항상 최신 코드 보장.
const CACHE = "knk-messenger-v4-passthrough";

self.addEventListener("install", (e) => {
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// 모든 fetch는 그대로 네트워크 통과 (캐시 안 함)
self.addEventListener("fetch", (e) => {
  // 기본 동작 = 네트워크. 아무것도 안 함.
});

// Push notifications 핸들러
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
