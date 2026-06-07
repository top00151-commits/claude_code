// KNK 메신저 — 로그인/게스트로그인 페이지 설치 유도. (대표 지시 2026-05-30)
//  ① 카카오톡 등 '인앱 브라우저' → '기본 브라우저로 열기' 안내 배너.
//  ② 진짜 브라우저(크롬·삼성·엣지·웨일 등) → '📲 앱으로 설치' 버튼(beforeinstallprompt).
//  로그인 전에 표시. window.__BASE__ 가 있는 페이지(로그인)에서만 설치 SW 등록.
(function () {
  function pick(ko, vi, en) {
    var l = window.KNK_LANG;
    if (!l) { var n = (navigator.language || "").toLowerCase(); l = n.indexOf("vi") === 0 ? "vi" : (n.indexOf("en") === 0 ? "en" : "ko"); }
    return l === "vi" ? vi : (l === "en" ? en : ko);
  }
  function isStandalone() {
    return (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) || window.navigator.standalone === true;
  }
  function isInApp(ua) {
    if (/Whale|SamsungBrowser|Edg|FxiOS|CriOS/i.test(ua)) return false;        // 진짜 브라우저
    if (/KAKAOTALK/i.test(ua)) return true;
    if (/\bwv\b/i.test(ua)) return true;                                        // Android System WebView
    return /(NAVER|Line\/|FBAN|FBAV|FB_IAB|Instagram|DaumApps|; ?Band)/i.test(ua);
  }
  function isIOSdev(ua) {
    return /iPad|iPhone|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  }
  function _copy(text) {
    try {
      var ta = document.createElement("textarea");
      ta.value = text; ta.style.cssText = "position:fixed;left:-9999px;top:0;";
      document.body.appendChild(ta); ta.focus(); ta.select();
      document.execCommand("copy"); document.body.removeChild(ta);
    } catch (e) {}
  }

  // ── ① 인앱 브라우저 안내 ──
  function showInAppGuide(ua) {
    if (document.getElementById("preInAppGuide")) return;
    var iOS = isIOSdev(ua);
    var title = pick("📲 앱으로 설치하면 알림까지 받아요", "📲 Cài làm ứng dụng để nhận cả thông báo", "📲 Install as an app to also get notifications");
    var desc, btn;
    if (iOS) {
      desc = pick(
        "아이폰: 카톡 화면 <b>아래 나침반(Safari) 아이콘</b>을 누르면 사파리로 열려요.<br>(또는 <b>‘링크 복사’</b> 후 사파리 주소창에 붙여넣기)",
        "iPhone: nhấn <b>biểu tượng la bàn (Safari) ở dưới</b> để mở bằng Safari.<br>(hoặc <b>‘Sao chép link’</b> rồi dán vào Safari)",
        "iPhone: tap the <b>compass (Safari) icon at the bottom</b> to open in Safari.<br>(or <b>‘Copy link’</b> and paste into Safari)");
      btn = pick("링크<br>복사", "Sao chép<br>link", "Copy<br>link");
    } else {
      desc = pick(
        "<b>크롬·삼성인터넷·엣지</b>로 열면 설치돼요.<br>아래 <b>‘브라우저로 열기’</b>를 누르세요.<br>(안 되면 카톡 메뉴 → <b>‘다른 브라우저로 열기’</b>)",
        "Mở bằng <b>Chrome, Samsung Internet, Edge</b>.<br>Nhấn <b>‘Mở trình duyệt’</b>.<br>(Nếu không: menu KakaoTalk → <b>‘Mở bằng trình duyệt khác’</b>)",
        "Open in <b>Chrome, Samsung Internet, Edge</b>.<br>Tap <b>‘Open in browser’</b>.<br>(If not: KakaoTalk menu → <b>‘Open in another browser’</b>)");
      btn = pick("브라우저로<br>열기", "Mở<br>trình duyệt", "Open in<br>browser");
    }
    var bar = _mkBar("preInAppGuide", title, desc, btn);
    bar.btn.addEventListener("click", function () {
      var url = location.href;
      if (iOS) {
        var mark = function () { bar.btn.innerHTML = pick("복사됨", "Đã chép", "Copied"); };
        if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(url).then(mark).catch(function () { _copy(url); mark(); }); }
        else { _copy(url); mark(); }
      } else {
        try { var u = new URL(url); window.location.href = "intent://" + u.host + u.pathname + u.search + u.hash + "#Intent;scheme=https;package=com.android.chrome;end"; } catch (e) {}
      }
    });
  }

  // ── ② 진짜 브라우저 → '앱으로 설치' 버튼 ──
  function setupInstall(ua) {
    var BASE = (typeof window.__BASE__ === "string") ? window.__BASE__ : "";
    if ("serviceWorker" in navigator) {
      try { navigator.serviceWorker.register(BASE + "/sw.js?base=" + BASE, { scope: BASE + "/" }).catch(function () {}); } catch (e) {}
    }
    var deferred = null, promptFired = false;
    window.addEventListener("beforeinstallprompt", function (e) {
      e.preventDefault(); deferred = e; promptFired = true;
      if (document.getElementById("preInstallBar")) return;
      var title = pick("📲 KNK를 앱으로 설치할까요?", "📲 Cài KNK làm ứng dụng?", "📲 Install KNK as an app?");
      var desc = pick("한 번 클릭으로 설치 — 독립 창 + 알림을 받습니다.", "Cài 1 lần — cửa sổ riêng + nhận thông báo.", "One-click install — own window + notifications.");
      var btn = pick("설치", "Cài đặt", "Install");
      var bar = _mkBar("preInstallBar", title, desc, btn);
      bar.btn.addEventListener("click", function () {
        if (!deferred) { bar.el.remove(); return; }
        bar.btn.disabled = true;
        try { deferred.prompt(); var uc = deferred.userChoice; if (uc && uc.finally) uc.finally(function () { deferred = null; try { bar.el.remove(); } catch (e) {} }); else { deferred = null; } } catch (e) { try { bar.el.remove(); } catch (e2) {} }
      });
    });
    window.addEventListener("appinstalled", function () {
      var b = document.getElementById("preInstallBar"); if (b) b.remove();
      try { showInstalledNudge(); } catch (e) {}   // 설치 완료 → '홈화면 앱으로 들어오세요' 안내 (대표 지시 2026-05-31)
    });
    // 🤖 안드로이드 실브라우저 — beforeinstallprompt 가 늦거나 안 뜨면 수동 '홈 화면에 추가' 안내를 빨리 표시 (대표 지시 2026-05-31)
    if (!isIOSdev(ua)) {
      setTimeout(function () {
        if (promptFired) return;
        if (document.getElementById("preInstallBar") || document.getElementById("preInAppGuide")) return;
        var t2 = pick("📲 앱으로 설치하면 알림까지 받아요", "📲 Cài làm ứng dụng để nhận cả thông báo", "📲 Install as an app to also get notifications");
        var d2 = pick("브라우저 메뉴(⋮) → <b>‘홈 화면에 추가’</b> 또는 <b>‘앱 설치’</b> 를 누르세요.",
                      "Menu trình duyệt (⋮) → <b>‘Thêm vào MH chính’</b> hoặc <b>‘Cài ứng dụng’</b>.",
                      "Browser menu (⋮) → <b>‘Add to Home screen’</b> or <b>‘Install app’</b>.");
        _mkBar("preInstallBar", t2, d2, null);
      }, 2200);
    }
    // 🍎 iOS Safari(인앱 아님) — beforeinstallprompt 미지원 → 공유→홈화면 안내 (1회)
    if (isIOSdev(ua)) {
      setTimeout(function () {
        if (document.getElementById("preInstallBar") || document.getElementById("preInAppGuide")) return;
        var title = pick("📲 앱으로 설치하기", "📲 Cài làm ứng dụng", "📲 Install as an app");
        var desc = pick("하단 <b>공유(⬆️)</b> → <b>‘홈 화면에 추가’</b> 를 누르세요.", "Nhấn <b>Chia sẻ (⬆️)</b> → <b>‘Thêm vào MH chính’</b>.", "Tap <b>Share (⬆️)</b> → <b>‘Add to Home Screen’</b>.");
        _mkBar("preInstallBar", title, desc, null);
      }, 1400);
    }
  }

  // 공용 배너 생성 — { el, btn }
  function _mkBar(id, title, desc, btnTxt) {
    var bar = document.createElement("div");
    bar.id = id;
    bar.style.cssText = "position:fixed;left:8px;right:8px;bottom:8px;z-index:99999;max-width:480px;margin:0 auto;" +
      "background:#1F2937;color:#fff;border-radius:12px;padding:13px 15px;box-shadow:0 6px 24px rgba(0,0,0,0.35);font-size:13px;line-height:1.55;";
    var btnHtml = btnTxt ? '<button type="button" class="pg-act" style="background:#A5282C;border:0;color:#fff;font-weight:700;font-size:12px;padding:8px 12px;border-radius:8px;cursor:pointer;white-space:nowrap;line-height:1.25;text-align:center;">' + btnTxt + '</button>' : '';
    bar.innerHTML =
      '<div style="display:flex;align-items:flex-start;gap:10px;">' +
        '<div style="flex:1;min-width:0;">' +
          '<div style="font-weight:700;margin-bottom:4px;">' + title + '</div>' +
          '<div style="color:#D1D5DB;font-size:12px;">' + desc + '</div>' +
        '</div>' + btnHtml +
        '<button type="button" class="pg-close" style="background:transparent;border:0;color:#9ca3af;font-size:20px;cursor:pointer;padding:0 2px;line-height:1;">✕</button>' +
      '</div>';
    document.body.appendChild(bar);
    var closeBtn = bar.querySelector(".pg-close");
    if (closeBtn) closeBtn.addEventListener("click", function () { try { bar.remove(); } catch (e) {} });
    return { el: bar, btn: bar.querySelector(".pg-act") };
  }

  // ── 설치 완료 안내 — 브라우저 창은 코드로 못 닫으므로(보안), '홈화면 앱으로 들어오세요' 안내만. (대표 지시 2026-05-31) ──
  function showInstalledNudge() {
    if (document.getElementById("pgInstalledNudge")) return;
    var ov = document.createElement("div");
    ov.id = "pgInstalledNudge";
    ov.style.cssText = "position:fixed;inset:0;z-index:100000;background:rgba(17,24,39,0.94);display:flex;align-items:center;justify-content:center;padding:24px;";
    var title = pick("✅ 앱이 설치되었어요", "✅ Đã cài đặt ứng dụng", "✅ App installed");
    var desc = pick(
      "이 브라우저 창을 닫고 <b>홈 화면에 새로 생긴 앱 아이콘</b>으로 들어오세요.<br>알림까지 받으려면 꼭 <b>앱</b>으로 사용하세요.",
      "Đóng cửa sổ này và mở bằng <b>biểu tượng ứng dụng mới trên màn hình chính</b>.<br>Hãy dùng <b>ứng dụng</b> để nhận thông báo.",
      "Close this tab and open the <b>new app icon on your home screen</b>.<br>Use the <b>app</b> to also receive notifications.");
    var ok = pick("확인", "OK", "OK");
    ov.innerHTML =
      '<div style="max-width:360px;width:100%;background:#1F2937;border:1px solid rgba(255,255,255,0.12);border-radius:16px;padding:24px 20px;text-align:center;box-shadow:0 16px 48px rgba(0,0,0,0.5);color:#fff;">' +
        '<div style="font-size:44px;margin-bottom:8px;">🏠</div>' +
        '<div style="font-weight:800;font-size:17px;margin-bottom:10px;">' + title + '</div>' +
        '<div style="color:#D1D5DB;font-size:13.5px;line-height:1.75;margin-bottom:18px;">' + desc + '</div>' +
        '<button type="button" id="pgInstalledOk" style="background:#A5282C;border:0;color:#fff;font-weight:700;font-size:14px;padding:12px 22px;border-radius:10px;cursor:pointer;width:100%;">' + ok + '</button>' +
      '</div>';
    document.body.appendChild(ov);
    var ob = document.getElementById("pgInstalledOk");
    if (ob) ob.addEventListener("click", function () { try { ov.remove(); } catch (e) {} });
  }

  function init() {
    try {
      var ua = navigator.userAgent || "";
      if (isStandalone()) return;                 // 이미 설치된 앱
      if (isInApp(ua)) { showInAppGuide(ua); return; }
      // 진짜 브라우저 — 로그인 페이지(__BASE__ 정의)에서만 설치 SW 등록 + 버튼
      if (typeof window.__BASE__ === "string") setupInstall(ua);
    } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
