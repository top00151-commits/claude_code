// KNK Messenger Service Worker — pass-through + 강제 네트워크
// v8-force-net-js-css: app.js / style.css 도 항상 네트워크에서 받음 (PWA 캐시로 옛 코드 잔존 차단)
const CACHE = "knk-messenger-v8-force-net-js-css";
// 하위 경로 배포(/msg) 지원 — 등록 시 ?base= 쿼리로 전달받은 접두어
const BASE = (new URL(self.location).searchParams.get("base") || "");

self.addEventListener("install", (e) => {
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// HTML navigation + JS/CSS → 강제 네트워크 (옛 코드 잔존 차단)
// 이미지·아이콘은 기본 동작 (캐시 OK, ?v=쿼리로 무효화).
self.addEventListener("fetch", (e) => {
  const req = e.request;
  const accept = req.headers.get("accept") || "";
  const url = (() => { try { return new URL(req.url); } catch (_) { return null; } })();
  const path = url ? url.pathname : "";
  const isHtml = req.mode === "navigate" || accept.includes("text/html");
  const isJs   = path.endsWith(".js")  || accept.includes("javascript");
  const isCss  = path.endsWith(".css") || accept.includes("text/css");
  if (req.method === "GET" && (isHtml || isJs || isCss)) {
    e.respondWith(
      fetch(req, { cache: "no-store" }).catch(() => fetch(req))
    );
    return;
  }
  // 그 외는 기본 네트워크 동작
});

// Push notifications 핸들러 — 휴대폰 PWA 가 백그라운드/종료 상태에서도 OS 알림 + 앱 배지
self.addEventListener("push", (e) => {
  let data = {};
  try { data = e.data ? e.data.json() : {}; } catch (err) { data = { title: "KNK 메신저", body: e.data?.text() || "" }; }
  const title = data.title || "KNK 메신저";
  const opts = {
    body: data.body || "",
    icon: BASE + "/static/icons/icon-192.png",
    badge: BASE + "/static/icons/icon-192.png",
    data: data.url ? { url: data.url } : { url: BASE + "/chat" },
    tag: data.tag,
    requireInteraction: false,
    vibrate: [200, 100, 200],          // 휴대폰 진동 패턴
    renotify: true,                     // 같은 tag 라도 다시 알림
  };
  // PWA 홈화면 아이콘 배지 갱신 (지원 브라우저 — Chrome Android 81+, Edge)
  const updateBadge = (async () => {
    if ("setAppBadge" in self.navigator) {
      try {
        // 정확한 unread 카운트를 모르므로 +1 누적. clearAppBadge 는 클라이언트 열릴 때.
        await self.navigator.setAppBadge();
      } catch (e) { /* ignore */ }
    }
  })();
  e.waitUntil(Promise.all([
    self.registration.showNotification(title, opts),
    updateBadge,
  ]));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  let url = e.notification.data?.url || (BASE + "/chat");
  // 서버가 BASE_PATH 없이 "/chat?room=4" 같은 경로만 보내는 경우 자동으로 BASE 접두 추가.
  // 이중 적용 방지 — 이미 BASE 로 시작하면 그대로.
  if (BASE && !url.startsWith(BASE) && url.startsWith("/")) {
    url = BASE + url;
  }
  // 알림 클릭 시 PWA 앱 배지 해제 (사용자가 열어서 봤으니까)
  if ("clearAppBadge" in self.navigator) {
    try { self.navigator.clearAppBadge(); } catch (e) {}
  }
  e.waitUntil(
    clients.matchAll({ type: "window" }).then(list => {
      for (const c of list) {
        if (c.url.includes(url) && "focus" in c) return c.focus();
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});
