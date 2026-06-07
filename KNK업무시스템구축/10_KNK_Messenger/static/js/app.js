// KNK Messenger — client (Phase A+B+C+D)
(() => {
  const app = document.getElementById("app");
  const meId = parseInt(app.dataset.meId, 10);
  // 동적 문구 다국어 헬퍼 — 키가 i18n 에 있으면 번역, 없으면 한국어 폴백 (대표 지시 2026-06-05 다국어 누락 전수). 내부전용 키는 ko/vi/en, 고객도 보는 키는 +zh.
  const _kt = (k, ko) => { try { const v = window.KNK_t ? window.KNK_t(k) : null; return (v && v !== k) ? v : ko; } catch (e) { return ko; } };
  // 내 역할 — 서버가 페이지에 심어줌 (관리자 'ceo' / 일반 'staff'). 부팅 즉시 설정해
  // 관리자 전용 UI(🆔 직원등록 등)를 users 목록 로드 전에도 정확히 토글. (대표 지시 2026-05-20)
  window._meRole = (app.dataset.meRole || "staff");
  // 최고관리자(소유자) 여부 — 서버가 페이지에 심어줌 (대표 지시 2026-05-21)
  window._meIsOwner = (app.dataset.meOwner === "1");
  // 팀장 여부 — 채널 생성·관리 권한 (대표 지시 2026-05-21)
  window._meIsTeamLead = (app.dataset.meTeamlead === "1");
  // 채널 생성 권한 — 관리자·대표이사·임원(전무·상무·이사)·팀장·법인장 (대표 지시 2026-05-24)
  window._meCanCreateChannel = (app.dataset.meCancreatechannel === "1");
  // 고객사 게스트(외부 사용자) 여부 — true 면 AI/이력/디렉터리/새방생성 등 차단 (대표 지시 2026-05-28)
  window._meIsGuest = (app.dataset.meGuest === "1");
  window._meGuestRoomId = parseInt(app.dataset.meGuestRoom || "0", 10) || null;
  window._meGuestCompany = (app.dataset.meGuestCompany || "");
  // 게스트 외부 브라우저 재진입용 초대 토큰 — 방 URL 에 ?g=토큰 으로 달아둠 (외부 브라우저로 열어도 자동 재인증). (대표 지시 2026-05-30)
  window._meGuestToken = (app.dataset.meGuestToken || "");
  // 하위 경로 배포(/msg) 지원 — 모든 fetch/소켓/링크 경로에 접두어로 사용
  const BASE = (window.__BASE__ || "");

  // ───────── 단독창(solo) 모드 — room-list 더블클릭으로 띄운 분리창 ─────────
  // URL: /msg/chat?solo=1&room=<id>
  //   - 사이드바 숨김(CSS), chat-pane 만 풀화면
  //   - 부팅 후 자동으로 그 방 열기
  //   - 디버그 디아이제스트 자동노출 등 메인 창 전용 동작 스킵
  const _SOLO_PARAMS = new URLSearchParams(location.search);
  const SOLO_MODE = _SOLO_PARAMS.get("solo") === "1";
  const SOLO_ROOM_ID = SOLO_MODE ? parseInt(_SOLO_PARAMS.get("room") || "0", 10) : 0;
  if (SOLO_MODE) {
    document.body.classList.add("solo-window");
  }

  // 분리(단독) 창 features — 카톡 정도 크기(400×700) + 메인 창 '위(중앙)'에 열기 (대표 지시 2026-06-02)
  function _soloFeatures() {
    var w = 400, h = 700;
    var bx = (typeof window.screenX === "number" ? window.screenX : (window.screenLeft || 0));
    var by = (typeof window.screenY === "number" ? window.screenY : (window.screenTop || 0));
    var ow = window.outerWidth || 1200, oh = window.outerHeight || 800;
    var left = Math.max(0, Math.round(bx + (ow - w) / 2));
    var top  = Math.max(0, Math.round(by + (oh - h) / 2));
    return "width=" + w + ",height=" + h + ",left=" + left + ",top=" + top +
           ",resizable=yes,scrollbars=yes,menubar=no,toolbar=no,location=no,status=no";
  }

  const $ = (id) => document.getElementById(id);
  const els = {
    roomList: $("roomList"),
    chatTitle: $("chatTitle"),
    itemMeta: $("itemMeta"),
    itemEditBtn: $("itemEditBtn"),
    requestsBtn: $("requestsBtn"),
    requestsBadge: $("requestsBadge"),
    myTasksBadge: $("myTasksBadge"),
    mentionsBtn: $("mentionsBtn"),
    mentionsBadge: $("mentionsBadge"),
    mentionsDialog: $("mentionsDialog"),
    mentionsList: $("mentionsList"),
    mentionsCount: $("mentionsCount"),
    mentionsReadAllBtn: $("mentionsReadAllBtn"),
    mentionsDeleteAllBtn: $("mentionsDeleteAllBtn"),
    mentionsPanel: $("mentionsPanel"),
    roomThreadsBtn: $("roomThreadsBtn"),
    roomSearchBtn: $("roomSearchBtn"),
    roomThreadsDialog: $("roomThreadsDialog"),
    roomThreadsRoomName: $("roomThreadsRoomName"),
    roomThreadsBody: $("roomThreadsBody"),
    galleryBtn: $("galleryBtn"),
    exportBtn: $("exportBtn"),
    guestInviteBtn: $("guestInviteBtn"),
    guestInviteDialog: $("guestInviteDialog"),
    guestInviteRoomName: $("guestInviteRoomName"),
    leaveRoomBtn: $("leaveRoomBtn"),
    leaveRoomDialog: $("leaveRoomDialog"),
    leaveMyName: $("leaveMyName"),
    leaveWithExportBtn: $("leaveWithExportBtn"),
    leaveJustBtn: $("leaveJustBtn"),
    leavePurgeBtn: $("leavePurgeBtn"),
    starredBtn: $("starredBtn"),
    starredDialog: $("starredDialog"),
    starredList: $("starredList"),
    headMoreBtn: $("headMoreBtn"),
    headMoreMenu: $("headMoreMenu"),
    hmmRequestsBadge: $("hmmRequestsBadge"),
    versionsDialog: $("versionsDialog"),
    versionsList: $("versionsList"),
    composerLangbar: $("composerLangbar"),
    composerLangHint: $("composerLangHint"),
    messages: $("messages"),
    composer: $("composer"),
    msgInput: $("msgInput"),
    sendBtn: $("sendBtn"),
    backBtn: $("backBtn"),
    attachBtn: $("attachBtn"),
    captureBtn: $("captureBtn"),
    mpPreview: $("mpPreview"),
    comboBar: $("comboBar"),
    layoutToggleBtn: $("layoutToggleBtn"),
    bottomBarHandle: $("bottomBarHandle"),
    multiShareBtn: $("multiShareBtn"),
    emojiBtn: $("emojiBtn"),
    emojiPicker: $("emojiPicker"),
    stickerBtn: $("stickerBtn"),
    stickerPicker: $("stickerPicker"),
    fileInput: $("fileInput"),
    newRoomBtn: $("newRoomBtn"),
    newRoomDialog: $("newRoomDialog"),
    newRoomForm: $("newRoomForm"),
    userPicker: $("userPicker"),
    itemUserPicker: $("itemUserPicker"),
    roomName: $("roomName"),
    cancelNewRoom: $("cancelNewRoom"),
    filterBar: $("filterBar"),
    globalSearch: $("globalSearch"),
    searchResults: $("searchResults"),
    myTasks: $("myTasks"),
    chatPane: $("chatPane"),
    // item form
    itemCustomer: $("itemCustomer"),
    itemCode: $("itemCode"),
    itemName: $("itemName"),
    itemStatus: $("itemStatus"),
    itemDue: $("itemDue"),
    // edit dialog
    itemEditDialog: $("itemEditDialog"),
    itemEditForm: $("itemEditForm"),
    editCustomer: $("editCustomer"),
    editCode: $("editCode"),
    editName: $("editName"),
    editStatus: $("editStatus"),
    editDue: $("editDue"),
    editKeepForever: $("editKeepForever"),
    cancelEdit: $("cancelEdit"),
    // gallery
    galleryDialog: $("galleryDialog"),
    galleryTitle: $("galleryTitle"),
    galleryContent: $("galleryContent"),
    closeGallery: $("closeGallery"),
    // lightbox
    lightbox: $("lightbox"),
    lightboxImg: $("lightboxImg"),
    lightboxMeta: $("lightboxMeta"),
    closeLightbox: $("closeLightbox"),
    // requests
    requestsDialog: $("requestsDialog"),
    requestsList: $("requestsList"),
    requestsCount: $("requestsCount"),
    closeRequests: $("closeRequests"),
    newRequestBtn: $("newRequestBtn"),
    newRequestDialog: $("newRequestDialog"),
    newRequestForm: $("newRequestForm"),
    newReqSourceHint: $("newReqSourceHint"),
    reqTitle: $("reqTitle"),
    reqDescription: $("reqDescription"),
    reqAssignedTo: $("reqAssignedTo"),
    reqDueDate: $("reqDueDate"),
    reqPriority: $("reqPriority"),
    cancelNewRequest: $("cancelNewRequest"),
    digestBtn: $("digestBtn"),
    digestDialog: $("digestDialog"),
    digestContent: $("digestContent"),
    closeDigest: $("closeDigest"),
    // AI 요약·작성 도움 (Claude Haiku)
    aiSummaryBtn: $("aiSummaryBtn"),
    aiSummaryDialog: $("aiSummaryDialog"),
    aiSummaryRoomName: $("aiSummaryRoomName"),
    aiSummaryBody: $("aiSummaryBody"),
    aiSummaryMeta: $("aiSummaryMeta"),
    aiSummaryGenBtn: $("aiSummaryGenBtn"),
    aiSummaryRegenBtn: $("aiSummaryRegenBtn"),
    aiSummaryCopyBtn: $("aiSummaryCopyBtn"),
    aiRewriteBtn: $("aiRewriteBtn"),
    aiRewriteMenu: $("aiRewriteMenu"),
    // 사이드바 탭 + 사용자 목록
    sidebarTabs: $("sidebarTabs"),
    userListToolbar: $("userListToolbar"),
    newUserBtn: $("newUserBtn"),
    newUserDialog: $("newUserDialog"),
    // 본사(KOR) 입력
    nuKEmployeeNo: $("nuKEmployeeNo"),
    nuKDisplayName: $("nuKDisplayName"),
    nuKDisplayNameEn: $("nuKDisplayNameEn"),
    nuKPhone: $("nuKPhone"),
    nuKEmail: $("nuKEmail"),
    nuKTitle: $("nuKTitle"),
    nuKDept: $("nuKDept"),
    nuKRoleCeo: $("nuKRoleCeo"),
    // 베트남(VN) 입력
    nuVEmployeeNo: $("nuVEmployeeNo"),
    nuVDisplayName: $("nuVDisplayName"),
    nuVDisplayNameVn: $("nuVDisplayNameVn"),
    nuVDisplayNameEn: $("nuVDisplayNameEn"),
    nuVPhone: $("nuVPhone"),
    nuVEmail: $("nuVEmail"),
    nuVTitle: $("nuVTitle"),
    nuVDept: $("nuVDept"),
    nuVRoleCeo: $("nuVRoleCeo"),
    nuSaveBtn: $("nuSaveBtn"),
    nuResult: $("nuResult"),
    changePwDialog: $("changePwDialog"),
    cpwCurrent: $("cpwCurrent"),
    cpwNew: $("cpwNew"),
    cpwNew2: $("cpwNew2"),
    cpwError: $("cpwError"),
    cpwSaveBtn: $("cpwSaveBtn"),
    userList: $("userList"),
    userInfoDialog: $("userInfoDialog"),
    uiName: $("uiName"),
    uiHint: $("uiHint"),
    uiTitle: $("uiTitle"),
    uiEmployeeNo: $("uiEmployeeNo"),
    uiDeptSelect: $("uiDeptSelect"),
    uiDeptCustom: $("uiDeptCustom"),
    uiEmail: $("uiEmail"),
    uiPhone: $("uiPhone"),
    uiCeoFields: $("uiCeoFields"),
    uiDisplayName: $("uiDisplayName"),
    uiRoleCeo: $("uiRoleCeo"),
    uiActive: $("uiActive"),
    uiSaveBtn: $("uiSaveBtn"),
    // 프로젝트 이력
    projectHistoryBtn: $("projectHistoryBtn"),
    projectHistoryDialog: $("projectHistoryDialog"),
    phRoomName: $("phRoomName"),
    phList: $("phList"),
    phGenerateBtn: $("phGenerateBtn"),
    phCopyAllBtn: $("phCopyAllBtn"),
    // 상태·캘린더
    meInfoArea: $("meInfoArea"),
    myStatusDot: $("myStatusDot"),
    myStatusText: $("myStatusText"),
    statusDialog: $("statusDialog"),
    statusOptionsArea: $("statusOptionsArea"),
    statusCustomText: $("statusCustomText"),
    statusUntilAt: $("statusUntilAt"),
    statusUntilArea: $("statusUntilArea"),
    statusUntilLabel: $("statusUntilLabel"),
    statusUntilTime: $("statusUntilTime"),
    statusUntilDate: $("statusUntilDate"),
    statusSaveBtn: $("statusSaveBtn"),
    calTitle: $("calTitle"),
    calStart: $("calStart"),
    calEnd: $("calEnd"),
    calKind: $("calKind"),
    calAddBtn: $("calAddBtn"),
    calEventList: $("calEventList"),
  };

  const STATUS_LABEL = { active: "진행중", hold: "보류", done: "완료", cancelled: "취소" };
  const REQ_STATUS_LABEL = { open: "열림", in_progress: "진행중", done: "완료", cancelled: "취소", on_hold: "보류" };
  // 프로젝트 상태 라벨 — 다국어. (대표 지시 2026-05-26)
  function _itemStatusLabel(s){ return s ? (window.KNK_t ? window.KNK_t("item." + s) : (STATUS_LABEL[s] || s)) : ""; }

  // ===== 모달 폴리필: <dialog> 네이티브 API를 .modal div에서 동일하게 동작 =====
  // 모든 .modal 요소가 .showModal() / .close() / .open 인터페이스를 가짐 → 기존 코드 그대로 작동
  document.querySelectorAll(".modal").forEach(m => {
    if (m._polyfilled) return;
    m._polyfilled = true;
    m.showModal = function() { m.classList.add("open"); document.body.style.overflow = "hidden"; };
    m.show      = function() { m.classList.add("open"); };
    m.close     = function() { m.classList.remove("open"); if (!document.querySelector(".modal.open")) document.body.style.overflow = ""; };
    try {
      Object.defineProperty(m, "open", {
        configurable: true,
        get() { return m.classList.contains("open"); },
      });
    } catch (e) { /* 이미 정의돼 있어도 무시 */ }
  });

  // ===== 글로벌 닫기 위임 =====
  // 1) [data-close] 버튼 클릭 → 부모 .modal 닫기
  // 2) .modal 자체 클릭(=백드롭 영역) → 닫기 (.modal-content 클릭은 정지)
  //
  // 모바일 long-press 텍스트 selection 보호 — mousedown/touchstart 위치 추적해서
  // 시작 위치가 .modal-content 안이었으면 click 시점에 backdrop close 안 함.
  // (드래그 selection 끝나는 시점에 손 떼면 클릭 이벤트의 e.target 이 .modal 로 잡히면서 잘못 닫힘)
  let _modalDownInside = false;
  const _trackDown = (e) => {
    _modalDownInside = !!(e.target && e.target.closest && e.target.closest(".modal-content"));
  };
  document.addEventListener("mousedown", _trackDown, true);
  document.addEventListener("touchstart", _trackDown, true);

  document.addEventListener("click", (e) => {
    const closeTrigger = e.target.closest("[data-close]");
    if (closeTrigger) {
      const modal = closeTrigger.closest(".modal");
      if (modal) { modal.close(); e.stopPropagation(); return; }
    }
    if (e.target.classList && e.target.classList.contains("modal")) {
      // mousedown 이 modal-content 안에서 일어났으면 backdrop click 무시
      if (_modalDownInside) { _modalDownInside = false; return; }
      e.target.close();
    }
  }, true);

  // 3) ESC 키 → 가장 위 열린 모달 1개만 닫기
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const opens = document.querySelectorAll(".modal.open");
      if (opens.length) opens[opens.length - 1].close();
    }
  });

  let socket = null;
  let _socketConnectedOnce = false;   // 첫 연결 이후 재연결 구분용 (재연결 시 메시지 재동기화)
  let _lastRoomResync = 0;            // 재동기화 쓰로틀
  let activeRoom = null;
  let rooms = [];
  let users = [];
  let roomReadStatus = { members: [], total: 0 };  // 현재 방의 읽음 상태
  let _lastMsgDateStr = null;  // 마지막으로 렌더된 메시지의 날짜(toDateString) — 날짜 바뀐 첫 메시지 판별용
  let activeFilter = "all";
  let activeTab = "item";
  let activeGalleryTab = "image";
  let activeReqTab = "open";
  let _reqMineOnly = false;   // 요청 목록 범위: true=내 요청만(요청자/담당자=나), false=방 전체 (대표 지시 2026-05-22)
  let pendingReqMessage = null;     // 요청 등록 시 원본 메시지

  // ---------- helpers ----------
  const escapeHtml = (s) =>
    String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  // 시:분만 — "오후 3:38"
  const _clockStr = (d) => {
    const h = d.getHours();
    const ap = h < 12 ? "오전" : "오후";
    const h12 = (h % 12) || 12;
    const mm = String(d.getMinutes()).padStart(2, "0");
    return `${ap} ${h12}:${mm}`;
  };
  const fmtTime = (iso) => {
    const d = new Date(iso);
    if (isNaN(d)) return "";
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    // 컴팩트 형식 — 같은 날 "오후 3:38", 다른 날 "5.20 오후 3:38"
    return sameDay ? _clockStr(d) : `${d.getMonth() + 1}.${d.getDate()} ${_clockStr(d)}`;
  };
  // 메시지 버블 전용 — 날짜가 바뀐 첫 메시지만 월.일+시:분, 이후는 시:분만
  const fmtMsgTime = (iso, showDate) => {
    const d = new Date(iso);
    if (isNaN(d)) return "";
    return showDate ? `${d.getMonth() + 1}.${d.getDate()} ${_clockStr(d)}` : _clockStr(d);
  };

  const fmtDate = (iso) => {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleDateString("ko-KR", { month: "2-digit", day: "2-digit" });
  };

  const fmtSize = (b) => {
    if (b == null) return "";
    if (b < 1024) return b + " B";
    if (b < 1024 * 1024) return (b / 1024).toFixed(1) + " KB";
    if (b < 1024 * 1024 * 1024) return (b / (1024 * 1024)).toFixed(1) + " MB";
    return (b / (1024 * 1024 * 1024)).toFixed(2) + " GB";
  };

  // 이름 첫 글자 추출 — Unicode-aware (서러게이트 쌍 통합, 국기 이모지 두 글자 쌍 보존)
  const initial = (name) => {
    if (!name || !name.length) return "?";
    const chars = [...name]; // 코드포인트 단위 분리 → 서러게이트 쌍(이모지)도 1개 요소
    if (!chars[0]) return "?";
    // 국기 이모지 = Regional Indicator Symbol 두 글자 쌍 (U+1F1E6–U+1F1FF)
    // 예: 🇰🇷 = 🇰 + 🇷 → chars[0]='🇰', chars[1]='🇷'
    const cp0 = chars[0].codePointAt(0);
    if (cp0 >= 0x1F1E6 && cp0 <= 0x1F1FF && chars.length >= 2) {
      const cp1 = chars[1].codePointAt(0);
      if (cp1 >= 0x1F1E6 && cp1 <= 0x1F1FF) return chars[0] + chars[1]; // 전체 국기
    }
    return chars[0]; // 일반 글자 or 단독 이모지
  };

  // 이미지 파일 → 정사각형 size×size PNG Blob (중앙 크롭 + 리사이즈). (대표 지시 2026-05-20)
  // 어떤 크기·형식(png/jpg/webp/heic 등)이든 작은 PNG 로 통일 → 업로드 크기·형식 문제 제거.
  function _resizeImageToSquareBlob(file, size) {
    return new Promise((resolve, reject) => {
      try {
        const url = URL.createObjectURL(file);
        const img = new Image();
        img.onload = () => {
          try {
            const s = Math.min(img.naturalWidth, img.naturalHeight);
            if (!s) { URL.revokeObjectURL(url); reject(new Error("빈 이미지")); return; }
            const sx = (img.naturalWidth - s) / 2;
            const sy = (img.naturalHeight - s) / 2;
            const canvas = document.createElement("canvas");
            canvas.width = size; canvas.height = size;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(img, sx, sy, s, s, 0, 0, size, size);
            URL.revokeObjectURL(url);
            canvas.toBlob(b => b ? resolve(b) : reject(new Error("변환 실패")), "image/png");
          } catch (e) { URL.revokeObjectURL(url); reject(e); }
        };
        img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("이미지를 읽을 수 없습니다")); };
        img.src = url;
      } catch (e) { reject(e); }
    });
  }

  // 메시지 인라인 편집 (대표 지시 2026-05-19) — 본인 텍스트 메시지만
  function startMessageEdit(li) {
    if (!li) return;
    const mid = parseInt(li.dataset.msgId, 10);
    if (!mid) return;
    if (li.querySelector(".msg-edit-area")) return;   // 이미 편집 중
    const bubble = li.querySelector(".bubble");
    if (!bubble) return;
    const original = bubble.textContent.trim();
    // bubble 을 편집 영역으로 교체
    const wrap = document.createElement("div");
    wrap.className = "msg-edit-area";
    wrap.innerHTML = `
      <textarea class="msg-edit-input" rows="2" maxlength="4000">${escapeHtml(original)}</textarea>
      <div class="msg-edit-actions">
        <span class="msg-edit-hint">Enter 저장 · Esc 취소</span>
        <button type="button" class="msg-edit-cancel">취소</button>
        <button type="button" class="msg-edit-save">저장</button>
      </div>`;
    bubble.style.display = "none";
    bubble.insertAdjacentElement("afterend", wrap);
    const ta = wrap.querySelector(".msg-edit-input");
    const saveBtn = wrap.querySelector(".msg-edit-save");
    const cancelBtn = wrap.querySelector(".msg-edit-cancel");
    // 포커스 + 커서 끝으로
    ta.focus();
    ta.setSelectionRange(ta.value.length, ta.value.length);
    // 자동 높이 조절
    const autoGrow = () => {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 240) + "px";
    };
    autoGrow();
    ta.addEventListener("input", autoGrow);
    const cleanup = () => {
      wrap.remove();
      bubble.style.display = "";
    };
    const save = async () => {
      const newContent = ta.value.trim();
      if (!newContent) { alert(window.KNK_t("alert.emptyContent")); return; }
      if (newContent === original) { cleanup(); return; }   // 변경 없으면 그냥 닫기
      try {
        saveBtn.disabled = true;
        const r = await fetch(`${BASE}/api/messages/${mid}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: newContent }),
        }).then(x => x.json());
        if (r.error) { alert(r.error); saveBtn.disabled = false; return; }
        // socketio broadcast 가 처리하지만 fallback 으로 즉시 갱신
        _applyMessageEdit(mid, r.content, r.edited_at);
        cleanup();
      } catch (err) {
        alert(window.KNK_t("alert.editFail","편집 실패") + ": " + (err.message || err));
        saveBtn.disabled = false;
      }
    };
    saveBtn.addEventListener("click", save);
    cancelBtn.addEventListener("click", cleanup);
    ta.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") { ev.preventDefault(); cleanup(); }
      else if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); save(); }
      // Shift+Enter = 줄바꿈 (기본 동작)
    });
  }

  // 편집된 메시지 화면에 반영 — socketio 'message_edited' 수신 시 호출
  function _applyMessageEdit(messageId, newContent, editedAt) {
    const li = document.querySelector(`.msg[data-msg-id="${messageId}"]`);
    if (!li) return;
    // 편집 중이면 무시 (사용자가 입력 중)
    if (li.querySelector(".msg-edit-area")) return;
    const bubble = li.querySelector(".bubble");
    if (bubble) bubble.textContent = newContent;
    // '✏ 편집됨 HH:mm' 라벨 추가 (이미 있으면 갱신)
    const timeEl = li.querySelector(".time");
    if (timeEl) {
      let badge = timeEl.querySelector(".edited-badge");
      if (!badge) {
        badge = document.createElement("span");
        badge.className = "edited-badge";
        timeEl.insertBefore(badge, timeEl.firstChild);
      }
      badge.textContent = `✏ 편집됨 ${fmtTime(editedAt)}`;
      // 원본 시각 정보 보존 — bubble data 또는 li 의 data-attribute 활용
      const origTime = li.dataset.createdAt || "";
      badge.title = origTime ? `원본: ${fmtTime(origTime)} · 편집: ${fmtTime(editedAt)}` : `편집 시각: ${fmtTime(editedAt)}`;
    }
  }

  // 읽음/안읽음 명단 다이얼로그 (대표 지시 2026-05-19)
  //   본인 메시지 옆 read-badge 클릭 → 누가 읽었고 안 읽었는지 명단
  async function openReadStatusDialog(messageId) {
    try {
      const r = await fetch(`${BASE}/api/messages/${messageId}/read_status`).then(x => x.json());
      if (r.error) { alert(r.error); return; }
      // 기존 다이얼로그 있으면 제거
      document.querySelectorAll(".read-status-modal").forEach(el => el.remove());
      const dlg = document.createElement("div");
      dlg.className = "read-status-modal";
      const renderUser = (u, withTime) => {
        const avatar = u.avatar_url
          ? `<img class="avatar-img" src="${escapeHtml(u.avatar_url)}" alt="">`
          : escapeHtml(initial(u.display_name));
        // users 캐시에서 title·department 보강 (대표 지시 2026-05-19)
        const cached = (Array.isArray(users) ? users.find(x => x.id === u.user_id) : null) || {};
        const title = cached.title || u.title || "";
        const department = cached.department || u.department || "";
        const metaParts = [];
        if (title) metaParts.push(escapeHtml(title));
        if (department) {
          const deptLabel = (typeof deptDisplayLabel === "function") ? deptDisplayLabel(department) : department;
          metaParts.push(escapeHtml(deptLabel));
        }
        const metaLine = metaParts.length
          ? `<div class="rs-user-meta">${metaParts.join(" · ")}</div>`
          : "";
        const timeText = withTime && u.last_read_at ? `<span class="rs-time">${fmtTime(u.last_read_at)}</span>` : "";
        return `<div class="rs-user-row">
          <div class="rs-avatar" style="background:${u.avatar_color || '#3b82f6'};">${avatar}</div>
          <div class="rs-user-block">
            <div class="rs-user-name">${escapeHtml(u.display_name)}</div>
            ${metaLine}
          </div>
          ${timeText}
        </div>`;
      };
      const readHtml = r.read.length
        ? r.read.map(u => renderUser(u, true)).join("")
        : `<div class="rs-empty">아직 아무도 읽지 않았습니다.</div>`;
      const unreadHtml = r.unread.length
        ? r.unread.map(u => renderUser(u, false)).join("")
        : `<div class="rs-empty">모두 읽었습니다 🎉</div>`;
      dlg.innerHTML = `
        <div class="read-status-card">
          <div class="rs-head">
            <h3>📨 메시지 확인 현황</h3>
            <button type="button" class="rs-close" aria-label="닫기">✕</button>
          </div>
          <div class="rs-tabs">
            <button type="button" class="rs-tab active" data-tab="unread">⬜ 안 읽음 (${r.unread.length})</button>
            <button type="button" class="rs-tab" data-tab="read">✅ 읽음 (${r.read.length})</button>
          </div>
          <div class="rs-list" data-tab-pane="unread">${unreadHtml}</div>
          <div class="rs-list" data-tab-pane="read" hidden>${readHtml}</div>
          <div class="rs-foot">전체 ${r.total_members}명 중 ${r.read_count}명 읽음</div>
        </div>`;
      document.body.appendChild(dlg);
      // 탭 전환
      dlg.querySelectorAll(".rs-tab").forEach(t => {
        t.addEventListener("click", () => {
          dlg.querySelectorAll(".rs-tab").forEach(x => x.classList.toggle("active", x === t));
          const tab = t.dataset.tab;
          dlg.querySelectorAll(".rs-list").forEach(l => l.hidden = (l.dataset.tabPane !== tab));
        });
      });
      // 닫기 (X 버튼·배경 클릭·ESC)
      const close = () => dlg.remove();
      dlg.querySelector(".rs-close")?.addEventListener("click", close);
      dlg.addEventListener("click", (e) => { if (e.target === dlg) close(); });
      const onKey = (e) => { if (e.key === "Escape") { close(); document.removeEventListener("keydown", onKey); } };
      document.addEventListener("keydown", onKey);
    } catch (err) {
      alert(window.KNK_t("alert.checkStatusFail","확인 현황 조회 실패") + ": " + (err.message || err));
    }
  }

  // 메시지를 '삭제된 메시지' 로 화면 갱신 (대표 지시 2026-05-19)
  //   서버 'message_deleted' broadcast 또는 본인 삭제 직후 호출.
  //   li 요소를 찾아 bubble 내용·첨부·액션 버튼 모두 회색 placeholder 로 교체.
  function _markMessageAsDeleted(messageId) {
    const li = document.querySelector(`.msg[data-msg-id="${messageId}"]`);
    if (!li) return;
    // 메모장(self) — 혼자 보는 방이라 삭제 시 '삭제된 메시지' 자리표시 없이 즉시 제거
    if (activeRoom && activeRoom.type === "self") { li.remove(); return; }
    // 클래스 추가 — CSS 로 회색 처리
    li.classList.add("msg-deleted");
    // bubble 내용 교체
    const bubble = li.querySelector(".bubble");
    if (bubble) {
      bubble.innerHTML = `<span class="deleted-placeholder">🗑️ 삭제된 메시지</span>`;
    }
    // 이미지·파일 첨부 영역 제거 + AI 번역 박스도 같이 제거 (대표 지시 2026-05-28).
    //   .msg-translation 은 bubble 옆/아래에 별도 노드로 붙어, bubble.innerHTML 만 갈아쳐도 잔존하던 버그.
    li.querySelectorAll(".image-wrap, .file-wrap, .album-grid, .forward-card, .quote-card, .whisper-header, .msg-translation").forEach(el => el.remove());
    // 액션 버튼들 숨김 (반응·요청·번역 등 의미 없어짐)
    const actionBar = li.querySelector(".msg-action-bar");
    if (actionBar) actionBar.style.display = "none";
    const reactBar = li.querySelector(".react-bar");
    if (reactBar) reactBar.style.display = "none";
  }

  // 사용자 상태 → 아바타 원형을 '상태 색상 배경 + 상태 이모지'로 꽉 채우는 오버레이 HTML (없으면 null).
  //   절대위치(inset:0)로 부모 원을 덮으므로, 위치별 배경색이 따로 지정돼 있어도 일관 적용됨. (대표 지시 2026-05-22)
  function _statusFillHtml(uid) {
    // 2026-06-03 대표 지시: 아바타에 상태(색 채움)를 표시하지 않음. 아바타는 사진/이름 첫글자(신원)만,
    //   상태는 사용자 목록 이름옆 글자(.user-status-text)로 확인. (예전: 상태색 원+이모지로 아바타를 덮었음 — 부담↑·식별↓)
    return null;
  }

  // 아바타 inner — 상태를 알면 '상태색 원 + 상태 이모지'로 채움 (대표 지시 2026-05-22).
  //   상태 없을 때 폴백: avatar_url 사진 → 이름 첫 글자(국기 이모지 포함).
  function _avatarBody(u) {
    // 사용자 id 우선순위: user_id(메시지·읽음명단의 발신자) → id(사용자 객체). 메시지의 m.id 는 메시지 id 라 오인 금지.
    const uid = u && (u.user_id || u.id);
    // 표시 우선순위 (대표 지시 2026-06-03): 개인 아바타(직원 셀프) > 인사카드 사진(avatar_url, 관리자) > 이름 첫글자
    const _self = (uid && window._selfAvatarMap) ? window._selfAvatarMap[uid] : null;
    const photo = _self || (u && u.avatar_url) || null;
    if (photo) {
      return `<img class="avatar-img" src="${escapeHtml(photo)}" alt="" loading="lazy" onerror="this.style.display='none';this.parentElement.classList.add('avatar-img-failed');">`;
    }
    const ini = initial((u && u.display_name) || "?");
    const cp0 = ini.codePointAt(0);
    if (cp0 >= 0x1F1E6 && cp0 <= 0x1F1FF) {
      // 국기 이모지 → 20px span, CSS 이모지 폰트로 렌더 (Windows Chrome 포함)
      return `<span style="font-size:calc(20px + var(--fs-add-ui));line-height:1">${escapeHtml(ini)}</span>`;
    }
    return escapeHtml(ini);
  }

  // 이미지를 Canvas 로 리사이즈·압축 — 아바타용 (정사각 cover, 최대 512×512, JPEG q=0.85)
  // 클라이언트에서 자동 변환 → 서버 5MB 제한 신경 안 써도 됨 (대표 지시 2026-05-19)
  function _resizeImageForAvatar(file, maxSize = 512, quality = 0.85) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error("파일을 읽지 못했습니다"));
      reader.onload = (e) => {
        const img = new Image();
        img.onerror = () => reject(new Error("이미지 형식을 인식할 수 없습니다"));
        img.onload = () => {
          try {
            // cover (center-crop) — 짧은 쪽이 maxSize 에 맞춰지도록 src 영역 계산
            const srcW = img.naturalWidth, srcH = img.naturalHeight;
            const side = Math.min(srcW, srcH);
            const sx = (srcW - side) / 2;
            const sy = (srcH - side) / 2;
            // 출력 크기 — 원본이 maxSize 보다 작으면 그 크기 유지 (확대 X)
            const out = Math.min(maxSize, side);
            const canvas = document.createElement("canvas");
            canvas.width = out; canvas.height = out;
            const ctx = canvas.getContext("2d");
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = "high";
            ctx.drawImage(img, sx, sy, side, side, 0, 0, out, out);
            // 항상 JPEG 로 저장 (투명도 필요한 PNG/WEBP 도 통일 — 아바타는 배경 있어도 OK)
            canvas.toBlob(
              (blob) => {
                if (!blob) { reject(new Error("이미지 변환 실패")); return; }
                resolve(blob);
              },
              "image/jpeg",
              quality
            );
          } catch (err) { reject(err); }
        };
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);
    });
  }

  // 크롭 다이얼로그 — 사용자가 사진의 영역(정사각/원)을 드래그·줌으로 직접 선택 (대표 지시 2026-05-26)
  //   resolve(blob)   : 사용자가 '저장' 선택 → 잘린 512×512 JPEG blob
  //   resolve(null)   : 사용자가 '취소' 선택
  function _openAvatarCropDialog(file) {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onerror = () => { alert(window.KNK_t ? window.KNK_t("crop.errRead") : "파일을 읽지 못했습니다"); resolve(null); };
      reader.onload = (e) => {
        const img = new Image();
        img.onerror = () => { alert(window.KNK_t ? window.KNK_t("crop.errImg") : "이미지 형식을 인식할 수 없습니다"); resolve(null); };
        img.onload = () => _buildCropUI(img);
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);

      function _buildCropUI(img) {
        const T = (k, fallback) => (window.KNK_t ? window.KNK_t(k) : fallback);
        // 오버레이
        const overlay = document.createElement("div");
        overlay.className = "avatar-crop-overlay";
        overlay.innerHTML = `
          <div class="avatar-crop-card" role="dialog" aria-modal="true">
            <div class="avatar-crop-title">${T("crop.title", "사진 위치 조정")}</div>
            <div class="avatar-crop-hint">${T("crop.hint", "사진을 드래그해서 원 안의 위치를 맞추세요. 확대/축소는 슬라이더 사용.")}</div>
            <div class="avatar-crop-stage" data-crop-stage>
              <canvas class="avatar-crop-canvas" data-crop-canvas></canvas>
              <div class="avatar-crop-mask"></div>
            </div>
            <div class="avatar-crop-zoom">
              <span class="avatar-crop-zoom-label">${T("crop.zoomSmall", "작게")}</span>
              <input type="range" class="avatar-crop-zoom-input" data-crop-zoom min="0.4" max="4" step="0.01" value="1">
              <span class="avatar-crop-zoom-label">${T("crop.zoomLarge", "크게")}</span>
            </div>
            <div class="avatar-crop-actions">
              <button type="button" class="btn-secondary" data-crop-cancel>${T("crop.cancel", "취소")}</button>
              <button type="button" class="btn-primary" data-crop-save>${T("crop.save", "저장")}</button>
            </div>
          </div>
        `;
        document.body.appendChild(overlay);

        const stage = overlay.querySelector("[data-crop-stage]");
        const canvas = overlay.querySelector("[data-crop-canvas]");
        const zoomInput = overlay.querySelector("[data-crop-zoom]");
        const cancelBtn = overlay.querySelector("[data-crop-cancel]");
        const saveBtn = overlay.querySelector("[data-crop-save]");
        const ctx = canvas.getContext("2d");

        // 무대(stage) 정사각형 크기 — 카드 폭에 맞춰 결정 (실제 픽셀)
        function _stageSize() {
          const rect = stage.getBoundingClientRect();
          return Math.floor(Math.min(rect.width, rect.height));
        }
        let stagePx = _stageSize();
        canvas.width = stagePx; canvas.height = stagePx;

        // 카메라 변환 상태:
        //   scale = 이미지 비율 (1 = 짧은 변이 무대 크기에 fit)
        //   offset = 이미지가 무대 좌상단 기준 어디에 그려질지 (캔버스 좌표계)
        const baseScale = stagePx / Math.min(img.naturalWidth, img.naturalHeight);  // 1배율 (이미지를 cover로 채움)
        let scale = baseScale;   // 실제 그릴 때 사용 (= baseScale × user_zoom)
        let userZoom = 1;
        // 이미지를 정중앙 정렬 시작
        let offX = (stagePx - img.naturalWidth * scale) / 2;
        let offY = (stagePx - img.naturalHeight * scale) / 2;

        function _clampOffset() {
          // 이미지가 무대 밖으로 빠져나가지 않게 (검은 여백 방지)
          const drawW = img.naturalWidth * scale;
          const drawH = img.naturalHeight * scale;
          const minX = stagePx - drawW;   // 음수: 이미지가 더 큼
          const minY = stagePx - drawH;
          if (drawW <= stagePx) offX = (stagePx - drawW) / 2;
          else offX = Math.min(0, Math.max(minX, offX));
          if (drawH <= stagePx) offY = (stagePx - drawH) / 2;
          else offY = Math.min(0, Math.max(minY, offY));
        }

        function _redraw() {
          ctx.clearRect(0, 0, stagePx, stagePx);
          ctx.imageSmoothingEnabled = true;
          ctx.imageSmoothingQuality = "high";
          ctx.drawImage(img, offX, offY, img.naturalWidth * scale, img.naturalHeight * scale);
        }
        _clampOffset();
        _redraw();

        // 드래그(마우스/터치)로 이동
        let dragging = false, lastX = 0, lastY = 0;
        function _onDown(ev) {
          dragging = true;
          const t = ev.touches ? ev.touches[0] : ev;
          lastX = t.clientX; lastY = t.clientY;
          ev.preventDefault();
        }
        function _onMove(ev) {
          if (!dragging) return;
          const t = ev.touches ? ev.touches[0] : ev;
          offX += (t.clientX - lastX);
          offY += (t.clientY - lastY);
          lastX = t.clientX; lastY = t.clientY;
          _clampOffset();
          _redraw();
          ev.preventDefault();
        }
        function _onUp() { dragging = false; }
        canvas.addEventListener("mousedown", _onDown);
        window.addEventListener("mousemove", _onMove);
        window.addEventListener("mouseup", _onUp);
        canvas.addEventListener("touchstart", _onDown, { passive: false });
        canvas.addEventListener("touchmove", _onMove, { passive: false });
        canvas.addEventListener("touchend", _onUp);

        // 줌 슬라이더
        function _applyZoom(nextZoom) {
          // 무대 중앙을 기준으로 zoom in/out (사진의 보이는 중심 유지)
          const cx = stagePx / 2, cy = stagePx / 2;
          const imgCxBefore = (cx - offX) / scale;
          const imgCyBefore = (cy - offY) / scale;
          userZoom = nextZoom;
          scale = baseScale * userZoom;
          offX = cx - imgCxBefore * scale;
          offY = cy - imgCyBefore * scale;
          _clampOffset();
          _redraw();
        }
        zoomInput.addEventListener("input", () => _applyZoom(parseFloat(zoomInput.value) || 1));

        // 휠 줌 (PC) — 미세 조절 (min=0.4 — 사용자가 사진을 stage보다 작게 만들 수 있게 — 대표 지시 2026-05-26)
        canvas.addEventListener("wheel", (ev) => {
          ev.preventDefault();
          const dir = ev.deltaY < 0 ? 0.08 : -0.08;
          const next = Math.max(0.4, Math.min(4, userZoom + dir));
          zoomInput.value = next;
          _applyZoom(next);
        }, { passive: false });

        // 핀치 줌 (모바일) — 두 손가락 거리 추적
        let pinchStartDist = 0, pinchStartZoom = 1;
        canvas.addEventListener("touchstart", (ev) => {
          if (ev.touches.length === 2) {
            const dx = ev.touches[0].clientX - ev.touches[1].clientX;
            const dy = ev.touches[0].clientY - ev.touches[1].clientY;
            pinchStartDist = Math.hypot(dx, dy);
            pinchStartZoom = userZoom;
            dragging = false;
          }
        }, { passive: false });
        canvas.addEventListener("touchmove", (ev) => {
          if (ev.touches.length === 2 && pinchStartDist) {
            const dx = ev.touches[0].clientX - ev.touches[1].clientX;
            const dy = ev.touches[0].clientY - ev.touches[1].clientY;
            const dist = Math.hypot(dx, dy);
            const next = Math.max(0.4, Math.min(4, pinchStartZoom * (dist / pinchStartDist)));
            zoomInput.value = next;
            _applyZoom(next);
            ev.preventDefault();
          }
        }, { passive: false });
        canvas.addEventListener("touchend", (ev) => {
          if (ev.touches.length < 2) pinchStartDist = 0;
        });

        // 닫기
        function _cleanup() {
          window.removeEventListener("mousemove", _onMove);
          window.removeEventListener("mouseup", _onUp);
          if (overlay.parentElement) overlay.parentElement.removeChild(overlay);
        }
        function _onEsc(ev) { if (ev.key === "Escape") { _cleanup(); document.removeEventListener("keydown", _onEsc); resolve(null); } }
        document.addEventListener("keydown", _onEsc);

        cancelBtn.addEventListener("click", () => {
          document.removeEventListener("keydown", _onEsc);
          _cleanup();
          resolve(null);
        });
        saveBtn.addEventListener("click", () => {
          // 현재 캔버스를 512×512로 다운샘플 (또는 stagePx가 이미 작으면 그대로)
          const out = 512;
          const tgt = document.createElement("canvas");
          tgt.width = out; tgt.height = out;
          const tctx = tgt.getContext("2d");
          tctx.imageSmoothingEnabled = true;
          tctx.imageSmoothingQuality = "high";
          tctx.drawImage(canvas, 0, 0, stagePx, stagePx, 0, 0, out, out);
          tgt.toBlob((blob) => {
            document.removeEventListener("keydown", _onEsc);
            _cleanup();
            if (!blob) { alert(T("crop.errSave", "이미지 변환 실패")); resolve(null); return; }
            resolve(blob);
          }, "image/jpeg", 0.85);
        });
      }
    });
  }

  // 아바타 업로드 trigger — file input 동적 생성 + 사용자 크롭 + 업로드 (대표 지시 2026-05-26 크롭 UI 추가)
  async function _triggerAvatarUpload(userId, isSelf) {
    return new Promise((resolve) => {
      const fi = document.createElement("input");
      fi.type = "file";
      fi.accept = "image/*";   // HEIC 등 다양한 포맷 허용 — Canvas 가 못 읽으면 에러로 폴백
      fi.style.display = "none";
      document.body.appendChild(fi);
      fi.addEventListener("change", async () => {
        const f = fi.files && fi.files[0];
        document.body.removeChild(fi);
        if (!f) { resolve(); return; }
        try {
          // 1) 사용자가 크롭 영역을 직접 선택 (취소 시 resolve null → 업로드 안 함)
          let blob = null;
          try {
            blob = await _openAvatarCropDialog(f);
          } catch (err) {
            console.warn("[avatar] crop UI 실패, 자동 cover-crop 사용:", err);
            blob = null;
          }
          if (!blob) {
            // 크롭 UI 실패 또는 취소 → 자동 cover-crop 으로 폴백 (사진 안 잃게)
            //   단, 사용자가 명시적으로 '취소' 버튼을 눌렀다면 아예 업로드 안 함.
            //   취소 vs UI 실패 구분이 어려워, 안전 동작은 '취소'로 간주 → 업로드 안 함.
            resolve(); return;
          }
          if (blob.size > 1024 * 1024) {
            // 결과가 1MB 초과면 더 강한 압축으로 한 번 더 (cover-crop 폴백 사용)
            try {
              const re = await _resizeImageForAvatar(new File([blob], "crop.jpg", { type: "image/jpeg" }), 512, 0.7);
              if (re) blob = re;
            } catch (e) { /* 무시 — 원본 그대로 업로드 시도 */ }
          }
          // 2) 업로드 — 본인 개인 아바타(/api/me/avatar) vs 인사카드 사진(관리자, /api/users/<id>/avatar)
          const fd = new FormData();
          fd.append("file", blob, "avatar.jpg");
          const _ep = isSelf ? `${BASE}/api/me/avatar` : `${BASE}/api/users/${userId}/avatar`;
          const res = await fetch(_ep, { method: "POST", body: fd }).then(r => r.json());
          if (res.error) { alert(res.error); resolve(); return; }
          if (isSelf) {
            // 개인 아바타 — _selfAvatarMap 즉시 반영 + 화면 갱신 (대표 지시 2026-06-03)
            try { _selfAvatarMap[meId] = res.self_avatar || null; window._selfAvatarMap = _selfAvatarMap; } catch (e) {}
            if (typeof renderUserList === "function") renderUserList();
            try { _refreshMyHeaderAvatar(); } catch (e) {}
            try { _refreshMsgAvatars(); } catch (e) {}
            try { await refreshRooms(); } catch (e) {}
          } else {
            // 3) 사용자 목록 캐시 갱신 (서버 broadcast 도 받지만 즉시 반영)
            if (Array.isArray(_usersCache)) {
              const idx = _usersCache.findIndex(x => x.id === userId);
              if (idx >= 0) _usersCache[idx].avatar_url = res.avatar_url;
            }
            if (Array.isArray(users)) {
              const idx2 = users.findIndex(x => x.id === userId);
              if (idx2 >= 0) users[idx2].avatar_url = res.avatar_url;
            }
            if (typeof renderUserList === "function") renderUserList();
            try { closeUserContextMenu(); } catch (e) {}
          }
          resolve();
        } catch (err) {
          alert(window.KNK_t("alert.uploadFail","업로드 실패") + ": " + (err && err.message ? err.message : err));
          resolve();
        }
      });
      fi.click();
    });
  }

  // 아바타 사진 제거 → 기본(이름 첫 글자) 아이콘으로 복귀. 본인 또는 관리자. (대표 지시 2026-05-20)
  async function _triggerAvatarDelete(userId) {
    try {
      const res = await fetch(`${BASE}/api/users/${userId}/avatar`, { method: "DELETE" })
        .then(r => r.json()).catch(() => ({ error: "삭제 실패" }));
      if (res.error) { alert(res.error); return; }
      // 캐시 즉시 갱신 (서버 broadcast 도 오지만 동작 클라이언트는 즉시 반영)
      if (Array.isArray(_usersCache)) { const i = _usersCache.findIndex(x => x.id === userId); if (i >= 0) _usersCache[i].avatar_url = null; }
      if (Array.isArray(users)) { const i2 = users.findIndex(x => x.id === userId); if (i2 >= 0) users[i2].avatar_url = null; }
      if (typeof renderUserList === "function") renderUserList();
      if (userId === meId) { try { _updateHeaderAvatar(null); } catch (e) {} }
      try { await refreshRooms(); } catch (e) {}   // 1:1 방 아이콘 등도 함께 갱신
    } catch (err) {
      alert(window.KNK_t("alert.removePhotoFail","사진 제거 실패") + ": " + (err && err.message ? err.message : err));
    }
  }

  // ── 본인 개인 아바타(self_avatar) — 직원 셀프 등록/변경/제거 (대표 지시 2026-06-03) ──
  async function _triggerSelfAvatarDelete() {
    try {
      const res = await fetch(`${BASE}/api/me/avatar`, { method: "DELETE" }).then(r => r.json()).catch(() => ({ error: "삭제 실패" }));
      if (res.error) { alert(res.error); return; }
      try { _selfAvatarMap[meId] = null; window._selfAvatarMap = _selfAvatarMap; } catch (e) {}
      if (typeof renderUserList === "function") renderUserList();
      try { _refreshMyHeaderAvatar(); } catch (e) {}
      try { _refreshMsgAvatars(); } catch (e) {}
      try { await refreshRooms(); } catch (e) {}
    } catch (err) { alert(window.KNK_t("alert.removePhotoFail","사진 제거 실패")); }
  }

  function _openSelfAvatarMenu(anchor) {
    document.querySelectorAll(".self-avatar-menu").forEach(m => m.remove());
    const hasPhoto = !!((window._selfAvatarMap || {})[meId]);
    const menu = document.createElement("div");
    menu.className = "self-avatar-menu";
    menu.innerHTML =
      `<button type="button" data-act="up">📷 내 사진 ${hasPhoto ? "변경" : "등록"}</button>` +
      (hasPhoto ? `<button type="button" data-act="del">🗑 제거</button>` : "");
    document.body.appendChild(menu);
    const r = anchor.getBoundingClientRect();
    let left = Math.round(r.left); const top = Math.round(r.bottom + 4);
    if (left + 180 > window.innerWidth) left = window.innerWidth - 188;
    menu.style.left = Math.max(8, left) + "px";
    menu.style.top = top + "px";
    const close = () => { try { menu.remove(); } catch (e) {} document.removeEventListener("click", close); };
    const up = menu.querySelector('[data-act="up"]');
    if (up) up.addEventListener("click", (e) => { e.stopPropagation(); close(); _triggerAvatarUpload(meId, true); });
    const del = menu.querySelector('[data-act="del"]');
    if (del) del.addEventListener("click", async (e) => {
      e.stopPropagation(); close();
      if (!confirm(window.KNK_t("confirm.removeMyPhoto","내 사진을 제거할까요? (인사카드 사진은 그대로입니다)"))) return;
      await _triggerSelfAvatarDelete();
    });
    setTimeout(() => document.addEventListener("click", close), 0);
  }

  // 헤더 좌상단 본인 아바타 클릭 → 개인 아바타 메뉴 (게스트·단독창 제외)
  (function initSelfAvatarClick() {
    try {
      if (typeof SOLO_MODE !== "undefined" && SOLO_MODE) return;
      if (window._meIsGuest) return;
      const ha = document.getElementById("meHeaderAvatar");
      if (!ha) return;
      ha.style.cursor = "pointer";
      ha.title = "클릭해서 내 사진 등록/변경";
      ha.addEventListener("click", (ev) => { ev.stopPropagation(); _openSelfAvatarMenu(ha); });
    } catch (e) {}
  })();

  // 헤더 좌상단 아바타 갱신 — 본인 사진 변경 시 즉시 반영
  function _updateHeaderAvatar(avatarUrl) {
    const headerAvatar = document.getElementById("meHeaderAvatar");
    if (!headerAvatar) return;
    // status-dot 보존
    const dot = headerAvatar.querySelector(".status-dot");
    if (avatarUrl) {
      headerAvatar.innerHTML = `<img class="avatar-img" src="${escapeHtml(avatarUrl)}" alt="" onerror="this.style.display='none';">`;
    } else {
      // 사진 제거 → 이름 첫 글자로 복귀
      const name = (window._meDisplayName || "?")[0] || "?";
      headerAvatar.innerHTML = escapeHtml(name);
    }
    if (dot) headerAvatar.appendChild(dot);
  }

  // 헤더 좌상단 본인 아바타 — 개인 아바타 > 인사카드 사진 > 이름 첫글자 (대표 지시 2026-06-03)
  function _refreshMyHeaderAvatar() {
    const ha = document.getElementById("meHeaderAvatar");
    if (!ha) return;
    const _self = (window._selfAvatarMap || {})[meId] || null;
    let photo = _self;
    if (!photo) { try { const mu = (Array.isArray(users) ? users.find(u => u.id === meId) : null); photo = (mu && mu.avatar_url) || null; } catch (e) {} }
    const dot = ha.querySelector(".status-dot");
    if (photo) ha.innerHTML = `<img class="avatar-img" src="${escapeHtml(photo)}" alt="" onerror="this.style.display='none';">`;
    else ha.innerHTML = escapeHtml((window._meDisplayName || "?")[0] || "?");
    if (dot) ha.appendChild(dot);
  }

  // 헤더 본인 정보(이름·직급 / 부서) 갱신 — users 캐시에서 최신값 가져와 적용 (2026-05-20)
  function _updateMeHeaderInfo() {
    try {
      const meCached = (Array.isArray(users) ? users.find(u => u.id === meId) : null);
      if (!meCached) return;
      const nameTitleEl = document.getElementById("meNameTitle");
      const deptEl = document.getElementById("meDeptText");
      const sepEl = document.getElementById("meMetaSep");
      if (nameTitleEl) {
        const parts = [meCached.display_name || ""];
        if (meCached.title) parts.push(meCached.title);
        nameTitleEl.textContent = parts.join(" ");
      }
      if (deptEl && sepEl) {
        if (meCached.department) {
          const dl = (typeof deptDisplayLabel === "function") ? deptDisplayLabel(meCached.department) : meCached.department;
          deptEl.textContent = dl;
          deptEl.hidden = false;
          sepEl.hidden = false;
        } else {
          deptEl.textContent = "";
          deptEl.hidden = true;
          sepEl.hidden = true;
        }
      }
      // 헤더 '🆔 직원 등록' 버튼은 설정 → 관리자 탭 으로 이동 (대표 지시 2026-05-26).
      //   백엔드 핸들러는 그대로 유지 — newUserOpenBtn(관리자 탭) 이 트리거함.
      //   따라서 헤더 버튼은 항상 숨김 (display:none 처럼 동작).
      try {
        const newUserBtnEl = document.getElementById("newUserBtn");
        if (newUserBtnEl) newUserBtnEl.hidden = true;
      } catch(_) {}
    } catch(e) { /* noop */ }
  }
  window._updateMeHeaderInfo = _updateMeHeaderInfo;

  const daysUntil = (iso) => {
    if (!iso) return null;
    const d = new Date(iso);
    if (isNaN(d)) return null;
    const today = new Date(); today.setHours(0,0,0,0);
    const target = new Date(d); target.setHours(0,0,0,0);
    return Math.round((target - today) / 86400000);
  };

  const debounce = (fn, ms) => {
    let t;
    return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
  };

  // ---------- API ----------
  const api = {
    rooms: () => fetch(BASE + "/api/rooms").then(r => r.json()),
    users: () => fetch(BASE + "/api/users").then(r => r.json()),
    usersCounts: () => fetch(BASE + "/api/users/counts").then(r => r.json()),
    messages: (rid) => fetch(`${BASE}/api/rooms/${rid}/messages`).then(r => r.json()),
    // ----- 멘션함 (@ 내게 온 멘션) -----
    mentions: (limit) => fetch(`${BASE}/api/mentions${limit ? `?limit=${limit}` : ""}`).then(r => r.json()),
    roomThreadsMy: (rid, limit) => fetch(`${BASE}/api/rooms/${rid}/threads/my${limit ? `?limit=${limit}` : ""}`).then(r => r.json()),
    roomThreadsAll: (rid, limit) => fetch(`${BASE}/api/rooms/${rid}/threads/all${limit ? `?limit=${limit}` : ""}`).then(r => r.json()),
    mentionsUnreadCount: () => fetch(`${BASE}/api/mentions/unread_count`).then(r => r.json()),
    mentionRead: (id) => fetch(`${BASE}/api/mentions/${id}/read`, { method: "POST" }).then(r => r.json()),
    mentionsReadAll: () => fetch(`${BASE}/api/mentions/read_all`, { method: "POST" }).then(r => r.json()),
    mentionDelete: (id) => fetch(`${BASE}/api/mentions/${id}`, { method: "DELETE" }).then(r => r.json()),
    mentionsDeleteAll: () => fetch(`${BASE}/api/mentions/delete_all`, { method: "POST" }).then(r => r.json()),
    createRoom: (payload) => fetch(BASE + "/api/rooms", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }).then(r => r.json()),
    createItem: (payload) => fetch(BASE + "/api/items", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }).then(r => r.json()),
    getItem: (rid) => fetch(`${BASE}/api/items/${rid}`).then(r => r.json()),
    updateItem: (rid, payload) => fetch(`${BASE}/api/items/${rid}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }).then(r => r.json()),
    // ----- 방 권한 관리 -----
    roomMembers: (rid) => fetch(`${BASE}/api/rooms/${rid}/members`).then(r => r.json()),
    setRoomAlias: (rid, alias) => fetch(`${BASE}/api/rooms/${rid}/alias`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ alias }) }).then(r => r.json()),
    clearRoomAlias: (rid) => fetch(`${BASE}/api/rooms/${rid}/alias`, { method: "DELETE" }).then(r => r.json()),
    renameRoom: (rid, name, locked) => fetch(`${BASE}/api/rooms/${rid}/name`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, name_locked: locked }) }).then(r => r.json()),
    setRoomRetention: (rid, days) => fetch(`${BASE}/api/rooms/${rid}/retention`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ retention_days: days }) }).then(r => r.json()),
    setRoomInvitePolicy: (rid, policy) => fetch(`${BASE}/api/rooms/${rid}/invite_policy`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ invite_policy: policy }) }).then(r => r.json()),
    getSelfRoom: () => fetch(`${BASE}/api/me/self_room`).then(r => r.json()),
    setMemberRole: (rid, uid, role) => fetch(`${BASE}/api/rooms/${rid}/members/${uid}/role`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ role }) }).then(r => r.json()),
    transferHost: (rid, toUid) => fetch(`${BASE}/api/rooms/${rid}/transfer-host`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ to_user_id: toUid }) }).then(r => r.json()),
    inviteToRoom: (rid, uids) => fetch(`${BASE}/api/rooms/${rid}/invite`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ user_ids: uids }) }).then(r => r.json()),
    kickMember: (rid, uid) => fetch(`${BASE}/api/rooms/${rid}/members/${uid}/kick`, { method: "POST" }).then(r => r.json()),
    markRead: (rid, opts) => fetch(`${BASE}/api/rooms/${rid}/read${(opts && opts.noClearPush) ? '?clear=0' : ''}`, { method: "POST" }),
    upload: (rid, file, onProgress, albumId, threadParentId) => {
      // XHR 사용 — 진행률 이벤트 받으려면 fetch 대신 XHR (Stream API 미흡)
      return new Promise((resolve, reject) => {
        const fd = new FormData();
        fd.append("room_id", rid);
        fd.append("file", file);
        if (albumId) fd.append("album_id", albumId);
        if (threadParentId) fd.append("thread_parent_id", threadParentId);
        const xhr = new XMLHttpRequest();
        xhr.open("POST", BASE + "/api/upload");
        // ★ 멈춤 감지(stall watchdog) — 로밍·해외 와이파이에서 전송이 조용히 멈추면
        //   60초간 바이트가 안 움직일 때 중단하고 명확히 안내. (느린 업로드는 진행이 있으니 오중단 없음) (대표 지시 2026-05-23)
        let _lastMove = Date.now();
        const _stall = setInterval(() => {
          if (Date.now() - _lastMove > 60000) {
            clearInterval(_stall);
            try { xhr.abort(); } catch (e) {}
            reject({ error: "전송이 60초간 멈췄습니다 (네트워크 불안정). 다시 시도해 주세요." });
          }
        }, 5000);
        const _done = () => clearInterval(_stall);
        if (xhr.upload) {
          xhr.upload.addEventListener("progress", (e) => {
            _lastMove = Date.now();
            if (onProgress && e.lengthComputable) {
              onProgress(Math.round((e.loaded / e.total) * 100), e.loaded, e.total);
            }
          });
        }
        xhr.onload = () => {
          _done();
          // JSON 응답이면 그대로 — 서버가 보낸 친절한 에러 메시지(error 필드) 우선
          try {
            const data = JSON.parse(xhr.responseText);
            if (xhr.status >= 200 && xhr.status < 300) resolve(data);
            else reject(data);
            return;
          } catch (err) { /* 비JSON → 아래 status 별 분기 */ }
          // 비JSON 응답 (nginx 502 페이지, 빈 응답 등) — status 별로 친절 메시지
          let msg;
          if (xhr.status === 413) msg = "파일이 너무 큽니다 (서버 한도 초과)";
          else if (xhr.status === 502 || xhr.status === 503 || xhr.status === 504) {
            msg = `서버 일시 오류 (HTTP ${xhr.status}). 잠시 후 다시 시도해 주세요.`;
          }
          else if (xhr.status === 0) msg = "네트워크 오류 — 연결을 확인해 주세요";
          else if (xhr.status >= 400 && xhr.status < 500) msg = `요청 거부 (HTTP ${xhr.status})`;
          else msg = `오류 (HTTP ${xhr.status})`;
          reject({ error: msg });
        };
        xhr.onerror = () => { _done(); reject({ error: "네트워크 오류 — 연결을 확인해 주세요" }); };
        xhr.onabort = () => { _done(); };
        xhr.send(fd);
      });
    },
    attachments: (rid, kind) => fetch(`${BASE}/api/rooms/${rid}/attachments?kind=${kind}`).then(r => r.json()),
    requests: (rid, status) => {
      const q = status && status !== "all" ? `?status=${status}` : "";
      return fetch(`${BASE}/api/rooms/${rid}/requests${q}`).then(r => r.json());
    },
    summary: (rid) => fetch(`${BASE}/api/rooms/${rid}/summary`).then(r => r.json()),
    timeline: (rid) => fetch(`${BASE}/api/rooms/${rid}/timeline`).then(r => r.json()),
    readStatus: (rid) => fetch(`${BASE}/api/rooms/${rid}/read_status`).then(r => r.json()),
    digest: () => fetch(BASE + "/api/digest").then(r => r.json()),
    createRequest: (payload) => fetch(BASE + "/api/requests", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }).then(r => r.json()),
    updateRequest: (id, payload) => fetch(`${BASE}/api/requests/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }).then(r => r.json()),
    myRequests: () => fetch(BASE + "/api/my/requests").then(r => r.json()),
    search: (q) => fetch(`${BASE}/api/search?q=${encodeURIComponent(q)}`).then(r => r.json()),
  };

  // ---------- render rooms ----------
  function filteredRooms() {
    if (activeFilter === "all") return rooms;
    if (activeFilter === "my-tasks") return [];
    if (activeFilter === "mentions") return [];
    return rooms.filter(r => r.type === activeFilter);
  }

  // 필터 칩에 방 개수(파란 배지) 표기 — 미읽음(적색)과 구분, 방이 몇 개인지 확인용 (대표 지시 2026-05-24)
  function _updateFilterCounts() {
    if (!els.filterBar) return;
    const counts = { all: 0, item: 0, direct: 0, group: 0, channel: 0 };
    (rooms || []).forEach(r => {
      if (r.type === "self") return;        // 내 메모(나에게 보내기)는 방 수에서 제외 — 합계 정확히 (대표 지시 2026-05-24)
      counts.all++;
      if (counts[r.type] !== undefined) counts[r.type]++;
    });
    Object.keys(counts).forEach(k => {
      const el = els.filterBar.querySelector('.chip-count[data-count-for="' + k + '"]');
      if (el) el.textContent = counts[k];
    });
  }

  // 방 표시 이름 계산 — 목록·검색결과 공통 (1:1 방이 검색에서 빈 줄로 보이던 문제 해결, 대표 지시 2026-06-06)
  //  self=메모장 / 채널(scope)=고정명 / 1:1(direct)=상대 'peer_id'로 찾아 '이름 직급님-부서' / 일반=언어별 이름
  function roomDisplayName(r) {
    if (!r) return "";
    const isSelf = r.type === "self";
    let name;
    if (isSelf) {
      name = window.KNK_t ? window.KNK_t("room.selfNote") : "📝 내 메모장";
    } else if (r.channel_scope === "all") {
      name = window.KNK_t ? window.KNK_t("room.knkWorld") : (r.name || "🌏 KNK WORLD");
    } else if (r.channel_scope === "hq") {
      name = window.KNK_t ? window.KNK_t("room.hqChannel") : (r.name || "🇰🇷 본사채널");
    } else if (r.channel_scope === "vn") {
      name = window.KNK_t ? window.KNK_t("room.vnChannel") : (r.name || "🇻🇳 베트남채널");
    } else {
      // 일반 방 — 사용자가 입력한 이름 그대로. name_vi/en/zh 캐시가 있으면 사용.
      const _lang = (typeof window.KNK_curLang === "function") ? window.KNK_curLang() : "ko";
      if (_lang === "ko" && r.name_ko) name = r.name_ko;
      else if (_lang === "vi" && r.name_vi) name = r.name_vi;
      else if (_lang === "en" && r.name_en) name = r.name_en;
      else if (_lang === "zh" && r.name_zh) name = r.name_zh;
      else name = r.name || (window.KNK_t ? window.KNK_t("room.unnamed") : "(이름없음)");
    }
    if (r.type === "direct" && Array.isArray(users) && users.length) {
      try {
        // 상대를 고유번호(peer_id)로 찾음 — 동명이인 오표시 방지. peer_id 없는 옛 캐시만 이름 매칭 fallback.
        const cached = (r.peer_id != null ? users.find(u => u.id === r.peer_id)
                                          : users.find(u => u.display_name === r.name)) || {};
        if (cached.display_name) {
          const _en = _useEnNames();
          let nm = _dispName(cached);
          const _t = _dispTitle(cached);
          if (_t) nm += _en ? ` ${_t}` : ` ${_t}님`;
          else if (!_en) nm += "님";
          const dept = _en ? _dispDept(cached)
                           : (cached.department ? ((typeof deptShortLabel === "function") ? deptShortLabel(cached.department) : cached.department) : "");
          name = dept ? `${nm}-${dept}` : nm;
        }
      } catch(e) {}
    }
    return name;
  }

  function renderRoomList() {
    _updateFilterCounts();
    const list = filteredRooms();
    // 전체보기(all)일 때만 방 종류별 강조 차등 적용 (대표 지시 2026-05-31)
    if (els.roomList) els.roomList.classList.toggle("rl-all", activeFilter === "all");
    // 사이드바 탭이 '사용자' 이면 방 목록 표시 안 함 (refresh·socket 이벤트 시에도 유지)
    // 아래 모든 분기에서 들어가도 hidden 유지하려면 여기서 조기 반환은 안 됨 — DOM 은 그려두되 .hidden 만 true.
    const onUsersTab = (typeof _sidebarTab !== "undefined" && _sidebarTab === "users");
    // 하단 콤보바(대표 미리보기)는 매 렌더 기본 숨김 — 아래 실제 방목록 렌더 경로에서만 노출 (대표 지시 2026-06-06)
    if (els.comboBar) els.comboBar.hidden = true;
    // 전체 검색 결과를 보는 중이면 방 목록을 다시 띄우지 않음 — 백그라운드(소켓·상태 갱신)가 검색결과를 덮어쓰지 않게 (대표 지시 2026-06-06)
    if (els.globalSearch && els.globalSearch.value.trim() && els.searchResults && !els.searchResults.hidden) {
      els.roomList.hidden = true;
      return;
    }
    if (activeFilter === "my-tasks") {
      els.roomList.hidden = true;
      els.searchResults.hidden = true;
      if (els.mentionsPanel) els.mentionsPanel.hidden = true;
      els.myTasks.hidden = onUsersTab ? true : false;
      if (!onUsersTab) renderMyTasks();
      return;
    }
    if (activeFilter === "mentions") {
      els.roomList.hidden = true;
      els.searchResults.hidden = true;
      els.myTasks.hidden = true;
      if (els.mentionsPanel) els.mentionsPanel.hidden = onUsersTab ? true : false;
      if (!onUsersTab) openMentions();   // 멘션을 인라인 패널에 렌더
      return;
    }
    els.myTasks.hidden = true;
    if (els.mentionsPanel) els.mentionsPanel.hidden = true;
    els.roomList.hidden = onUsersTab ? true : false;
    if (!list.length) {
      els.roomList.innerHTML = `<li class="empty-state" style="padding:32px;font-size:calc(13px + var(--fs-add-ui));">${rooms.length ? (window.KNK_t ? window.KNK_t("room.emptyFilter") : "이 필터에 해당하는 항목이 없습니다.") : (window.KNK_t ? window.KNK_t("room.emptyAll") : "대화가 없습니다.<br>＋ 버튼으로 새 프로젝트를 시작하세요.")}</li>`;
      return;
    }
    // ── 맨 위 고정 "같은 칸" — 내메모장 + 메신저불편사항 (좌우 2칸, 아바타 없음) (대표 지시 2026-06-03)
    //   '전체' 보기에서만 상단에 합친 칸으로. 두 방은 아래 일반 목록에서 제외해 중복 방지.
    let _comboHtml = "";
    let _renderList = list;
    // 대화방 만들기 — 헤더에서 이 콤보 줄 맨 앞으로 이동, 필터와 무관하게 항상 (게스트 제외) (대표 지시 2026-06-06)
    const _newRoomLabel = window.KNK_t ? window.KNK_t("btn.newRoom") : "대화방만들기";
    const _newRoomHalf = window._meIsGuest ? "" :
      `<div class="combo-half combo-new" data-act="new-room" role="button" tabindex="0"><span class="combo-label">✏️ ${escapeHtml(_newRoomLabel)}</span></div>`;
    let _comboHalves = _newRoomHalf;
    if (activeFilter === "all") {
      const _selfR = list.find(x => x.type === "self") || null;
      const _bugR  = window.__BUG_ROOM_ID__ ? (list.find(x => x.id === window.__BUG_ROOM_ID__) || null) : null;
      if (_selfR || _bugR) {
        _renderList = list.filter(x => x !== _selfR && x !== _bugR);
        const _comboHalf = (room, label, allowUnread) => {
          if (!room) return "";
          const _act = (activeRoom && activeRoom.id === room.id) ? " active" : "";
          const _ub = (allowUnread && room.unread > 0)
            ? `<span class="unread-badge">${room.unread > 99 ? "99+" : room.unread}</span>` : "";
          return `<div class="combo-half${_act}" data-room-id="${room.id}" role="button" tabindex="0">`
               + `<span class="combo-label">${escapeHtml(label)}</span>${_ub}</div>`;
        };
        const _selfLabel = window.KNK_t ? window.KNK_t("room.selfNote") : "📝 내 메모장";
        const _bugLabel  = "🙋 불편신고";   // 표시 명칭 단축 (대표 지시 2026-06-06)
        _comboHalves += _comboHalf(_selfR, _selfLabel, false) + _comboHalf(_bugR, _bugLabel, true);
      }
    }
    if (_comboHalves) _comboHtml = `<li class="room-combo-cell" aria-label="고정">${_comboHalves}</li>`;
    // 검색·만들기 줄 '아래 배치' 미리보기(대표 전용): 콤보를 하단 바(#comboBar)로, 아니면 목록 맨 위로 (대표 지시 2026-06-06)
    const _comboBottom = !!(window._searchBottomLayout && els.comboBar);
    if (_comboBottom) {
      els.comboBar.innerHTML = _comboHtml;
      els.comboBar.hidden = !_comboHtml || onUsersTab;
    } else if (els.comboBar) {
      els.comboBar.innerHTML = "";   // 하단배치 OFF — 잔여 내용 제거(평소엔 빈 채로 숨김)
    }
    // 검색결과에서 방을 클릭해 들어온 경우 그 방을 목록 맨 위로 고정 (필터 칩 누르면 해제) (대표 지시 2026-06-06)
    if (window._searchTopRoomId) {
      const _ti = _renderList.findIndex(x => x.id === window._searchTopRoomId);
      if (_ti > 0) _renderList = [_renderList[_ti]].concat(_renderList.slice(0, _ti), _renderList.slice(_ti + 1));
    }
    els.roomList.innerHTML = (_comboBottom ? "" : _comboHtml) + '<div class="room-scroll">' + _renderList.map(r => {
      const isSelf = r.type === "self";
      // 방 표시 이름 — 목록·검색 공통 로직(roomDisplayName)으로 통일 (1:1 빈줄 문제 해결, 대표 지시 2026-06-06)
      const name = roomDisplayName(r);
      // 방 종류별 원형 색상 (대표 지시 2026-05-20):
      //  메모장=주황(기존) / 프로젝트=녹색 / 채널=KNK색 / 그룹=보라(추천) / 1:1=기존(상대색 또는 파랑)
      const color =
        isSelf                 ? "#f59e0b" :
        r.type === "item"      ? "#16A34A" :   // 프로젝트 = 녹색
        r.type === "channel"   ? "#A5282C" :   // 채널 = 케이엔케이 색
        r.type === "group"     ? "#7C3AED" :   // 그룹 = 보라 (빅터 추천)
                                 (r.avatar_color || "#3b82f6");  // 1:1(direct) = 기존
      // 마지막 메시지 미리보기 — 방 목록에는 표시 안 함 (대표 지시 2026-05-27)
      //   미읽음 카운트 배지로 충분하고, 목록이 더 깔끔해짐. 메시지 내용은 방 열어서 확인.
      const time = r.last_at ? fmtTime(r.last_at) : "";
      const hasUnread = !isSelf && r.unread > 0;
      const unread = hasUnread ? `<span class="unread-badge">${r.unread > 99 ? "99+" : r.unread}</span>` : "";
      const active = activeRoom && activeRoom.id === r.id ? "active" : "";

      let chips = "";
      if (r.type === "item") {
        if (r.item_customer) chips += `<span class="customer-chip">${escapeHtml(r.item_customer)}</span>`;
        if (r.item_code) chips += `<span class="code-chip">${escapeHtml(r.item_code)}</span>`;
        if (r.item_status) chips += `<span class="status-pill status-${r.item_status}">${_itemStatusLabel(r.item_status)}</span>`;
      }
      // self 방은 이름 자체가 "📝 메모" 라 별도 칩 불필요
      // 자동삭제 설정된 방은 ⏱ 아이콘 (WhatsApp 식)
      const retentionIcon = (r.retention_days && r.retention_days > 0)
        ? `<span class="room-retention-icon" title="자동삭제 ${r.retention_days===1?'24시간':r.retention_days+'일'} 후">⏱</span>`
        : "";

      const mutedIcon = notifySettings.isRoomMuted(r.id) ? `<span class="room-muted-icon" title="이 방 알림 음소거 중">🔕</span>` : "";
      // 핀 고정 표시
      const pinnedIcon = r.pinned ? `<span class="room-pinned-icon" title="여기 고정됨">📌</span>` : "";
      // 고객사(게스트)가 참여한 방 — 이름 앞 "(고객)" 표시 (대표 지시 2026-05-29)
      const guestTag = (r.has_guest && !isSelf)
        ? `<span class="room-guest-tag" title="외부 고객사 참여 방">${window.KNK_t ? window.KNK_t("room.guestPrefix") : "(고객)"}</span> `
        : "";
      // 원형아이콘 — 자동채널은 실제 국기·지구 이모지 (Noto 폰트로 이미지 렌더, 대표 지시 2026-05-21)
      let avatarText = initial(name);
      let avatarFlag = false;
      let avatarStatusFill = null;
      if (isSelf) avatarText = "✏️";                                       // 📝 내 메모장 = 연필
      else if (r.channel_scope === "all") { avatarText = "🌏"; avatarFlag = true; }  // KNK WORLD = 아시아 지구
      else if (r.channel_scope === "hq")  { avatarText = "🇰🇷"; avatarFlag = true; }  // 본사 = 태극기
      else if (r.channel_scope === "vn")  { avatarText = "🇻🇳"; avatarFlag = true; }  // 베트남 = 베트남국기
      else if (r.type === "direct") {                                       // 1:1 = 상대방 사진/이름 첫글자 (상태 채움 폐지, 대표 지시 2026-06-03)
        const _other = Array.isArray(users)
          ? (r.peer_id != null ? users.find(u => u.id === r.peer_id)
                               : users.find(u => u.display_name === r.name))
          : null;
        avatarStatusFill = _other ? _avatarBody(_other) : null;
      }
      // 방/채널 아바타 — 상태 채움(1:1) > 관리자 이미지(avatar_url) > 글자/이모지
      const avatarInner = avatarStatusFill
        ? avatarStatusFill
        : (r.avatar_url
          ? `<img class="avatar-img" src="${escapeHtml(r.avatar_url)}" alt="" loading="lazy" onerror="this.style.display='none';this.parentElement.classList.add('avatar-img-failed');">`
          : escapeHtml(avatarText));
      // 방 종류 뱃지 (대표 지시 2026-05-29) — 아바타 우하단 작은 표시로 한눈에 종류 구분.
      //   🏭 프로젝트 · 📢 채널 · 👥 그룹 / 1:1·메모는 사람·✏️ 로 이미 구분돼 생략.
      let typeBadge = "", typeBadgeLabel = "";
      if (!isSelf) {
        if (r.type === "item")         { typeBadge = "🏭"; typeBadgeLabel = (window.KNK_t ? window.KNK_t("roomType.project") : "프로젝트"); }
        else if (r.type === "channel") { typeBadge = "📢"; typeBadgeLabel = (window.KNK_t ? window.KNK_t("roomType.channel") : "채널"); }
        else if (r.type === "group")   { typeBadge = "👥"; typeBadgeLabel = (window.KNK_t ? window.KNK_t("roomType.group") : "그룹"); }
      }
      const typeBadgeHtml = typeBadge
        ? `<span class="room-type-badge" title="${escapeHtml(typeBadgeLabel)}" aria-label="${escapeHtml(typeBadgeLabel)}">${typeBadge}</span>`
        : "";
      const rowClass = [active, "room-type-" + r.type, r.type === "item" ? "item-row" : "", isSelf ? "self-row" : "", r.pinned ? "pinned-row" : "", hasUnread ? "room-unread" : ""].filter(Boolean).join(" ");
      return `
        <li data-room-id="${r.id}" class="${rowClass}">
          <div class="room-avatar-wrap">
            <div class="avatar${avatarFlag ? ' room-flag-avatar' : ''}" style="background:${color}">${avatarInner}</div>${typeBadgeHtml}
          </div>
          <div class="room-info">
            <div class="room-name-line">
              ${chips}
              <div class="room-name">${pinnedIcon}${guestTag}${escapeHtml(name)}${retentionIcon}${mutedIcon}</div>
            </div>
          </div>
          <div class="room-meta">
            <div class="room-time">${time}</div>
            ${unread}
          </div>
        </li>`;
    }).join("") + '</div>';
    els.roomList.querySelectorAll("li[data-room-id]").forEach(li => {
      li.addEventListener("click", () => {
        const rid = parseInt(li.dataset.roomId, 10);
        // 이미 열려 보고 있는 방을 다시 클릭하면 재렌더 안 함 → 깜빡임 방지 (대표 지시 2026-05-20)
        if (activeRoom && activeRoom.id === rid && app.classList.contains("viewing-chat")) return;
        if (_openRoomOrPopout(rid)) return;   // 접힘(슬림) → 새 창 팝업 (대표 지시 2026-06-03)
        openRoom(rooms.find(r => r.id === rid));
      });
      // 더블클릭 → 그 방만 새 창(팝업)으로 분리 — PC 메신저 식 멀티윈도우
      // 같은 방을 두 번 더블클릭하면 같은 창(name) 재사용해서 새 창 안 생김.
      li.addEventListener("dblclick", (e) => {
        e.preventDefault();
        // 솔로창 안에서는 동작 불필요 (사이드바 자체가 없지만 안전)
        if (SOLO_MODE) return;
        const rid = parseInt(li.dataset.roomId, 10);
        const url = BASE + `/chat?solo=1&room=${rid}`;
        const winName = `knk_room_${rid}`;
        // 분리창 좁고 긴 비율 — 사용자가 모서리 드래그로 자유롭게 리사이즈 가능
        const features = _soloFeatures();
        const w = window.open(url, winName, features);
        if (w) {
          try { w.focus(); } catch(_) {}
        }
        // 더블클릭으로 텍스트 선택되는 것 방지
        try { window.getSelection().removeAllRanges(); } catch(_) {}
      });
      // 우클릭 → 방 컨텍스트 메뉴 (순서·고정·나가기·설정)
      li.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        const rid = parseInt(li.dataset.roomId, 10);
        showRoomContextMenu(rid, e.clientX, e.clientY);
      });
      // 모바일 롱프레스 — 650ms (iOS 시스템 콜아웃 500ms 보다 길게 → CSS 차단과 병행)
      let _rlPressTimer = null, _rlTouchXY = { x: 0, y: 0 };
      li.addEventListener("touchstart", (e) => {
        const t = e.touches[0];
        _rlTouchXY = { x: t.clientX, y: t.clientY };
        _rlPressTimer = setTimeout(() => {
          _rlPressTimer = null;
          const rid = parseInt(li.dataset.roomId, 10);
          showRoomContextMenu(rid, _rlTouchXY.x, _rlTouchXY.y);
        }, 650);
      }, { passive: true });
      li.addEventListener("touchmove", (e) => {
        const t = e.touches[0];
        const dx = Math.abs(t.clientX - _rlTouchXY.x);
        const dy = Math.abs(t.clientY - _rlTouchXY.y);
        if (dx > 10 || dy > 10) {
          // 이동 → 롱프레스 취소 (스크롤 의도)
          if (_rlPressTimer) { clearTimeout(_rlPressTimer); _rlPressTimer = null; }
        }
      }, { passive: true });
      li.addEventListener("touchend", () => {
        if (_rlPressTimer) { clearTimeout(_rlPressTimer); _rlPressTimer = null; }
      }, { passive: true });
      li.addEventListener("touchcancel", () => {
        if (_rlPressTimer) { clearTimeout(_rlPressTimer); _rlPressTimer = null; }
      }, { passive: true });
    });
    // 상단 "같은 칸" 두 칸 클릭 — 각 방 열기 (아바타 없는 고정칸, 대표 지시 2026-06-03)
    // 콤보는 하단 배치(대표 미리보기)면 #comboBar 에, 아니면 roomList 에 있음 (대표 지시 2026-06-06)
    const _comboHost = (window._searchBottomLayout && els.comboBar && !els.comboBar.hidden) ? els.comboBar : els.roomList;
    _comboHost.querySelectorAll(".combo-half[data-room-id]").forEach(half => {
      half.addEventListener("click", () => {
        const rid = parseInt(half.dataset.roomId, 10);
        if (activeRoom && activeRoom.id === rid && app.classList.contains("viewing-chat")) return;
        if (_openRoomOrPopout(rid)) return;
        openRoom(rooms.find(r => r.id === rid));
      });
    });
    // 콤보 줄의 '대화방 만들기' — 헤더에서 이동된 버튼 (대표 지시 2026-06-06)
    const _newHalf = _comboHost.querySelector('.combo-half[data-act="new-room"]');
    if (_newHalf) _newHalf.addEventListener("click", () => { try { openNewRoom(); } catch (e) {} });
  }

  // ============================================================
  // 방 목록 우클릭/롱프레스 컨텍스트 메뉴
  // ============================================================
  function closeRoomContextMenu() {
    document.querySelectorAll(".room-context-menu").forEach(m => m.remove());
  }

  function showRoomContextMenu(roomId, clientX, clientY) {
    closeRoomContextMenu();
    const r = rooms.find(x => x.id === roomId);
    if (!r) return;
    const isSelf = r.type === "self";
    const isDirect = r.type === "direct";
    const isMuted = notifySettings.isRoomMuted(roomId);
    const isPinned = !!r.pinned;
    const items = [];
    // self 방은 순서/나가기 모두 의미 없음 → 음소거만
    if (isSelf) {
      items.push({ icon: isMuted ? "🔔" : "🔕", label: isMuted ? "알림 받기" : "음소거", act: "mute_toggle" });
    } else {
      items.push({ section: true, label: "순서" });
      items.push({ icon: isPinned ? "📍" : "📌", label: isPinned ? "고정 해제" : "여기 고정", act: isPinned ? "unpin" : "pin" });
      items.push({ icon: "⏏", label: "맨 위로", act: "top" });
      items.push({ icon: "↑", label: "한 칸 위로", act: "up" });
      items.push({ icon: "↓", label: "한 칸 아래로", act: "down" });
      items.push({ icon: "⬇", label: "맨 아래로", act: "bottom" });
      items.push({ icon: "🔓", label: "정렬 해제 (자동)", act: "reset" });
      items.push({ divider: true });
      items.push({ icon: isMuted ? "🔔" : "🔕", label: isMuted ? "알림 받기" : "음소거", act: "mute_toggle" });
      items.push({ icon: "🪟", label: "새 창으로 열기", act: "popout" });
      items.push({ divider: true });
      items.push({ icon: "⚙", label: "방 설정", act: "settings" });
      // 대화방 나가기 — 단, 자동 채널(KNK WORLD/본사/베트남)은 나가기 금지 → 항목 숨김 (2026-05-20)
      if (!r.channel_scope) {
        items.push({ divider: true });
        items.push({ icon: "🚪", label: "대화방 나가기", act: "leave", danger: true });
      }
    }
    const menu = document.createElement("div");
    menu.className = "msg-context-menu room-context-menu";   // 같은 스타일 재사용
    menu.innerHTML = items.map(it => {
      if (it.divider) return `<div class="mcm-divider"></div>`;
      if (it.section) return `<div class="mcm-section-label">${escapeHtml(it.label)}</div>`;
      const cls = it.danger ? "mcm-item mcm-danger" : "mcm-item";
      return `<button type="button" class="${cls}" data-act="${it.act}">
        <span class="mcm-icon">${escapeHtml(it.icon)}</span>
        <span>${escapeHtml(it.label)}</span>
      </button>`;
    }).join("");
    document.body.appendChild(menu);
    // 위치 — viewport 벗어나지 않게
    const w = menu.offsetWidth, h = menu.offsetHeight;
    let x = clientX, y = clientY;
    if (x + w > window.innerWidth - 8) x = window.innerWidth - w - 8;
    if (y + h > window.innerHeight - 8) y = window.innerHeight - h - 8;
    if (x < 8) x = 8; if (y < 8) y = 8;
    menu.style.left = x + "px"; menu.style.top = y + "px";
    menu.querySelectorAll(".mcm-item").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const act = btn.dataset.act;
        closeRoomContextMenu();
        await handleRoomContextAction(roomId, act);
      });
    });
  }

  async function handleRoomContextAction(roomId, act) {
    // 전체 try/catch 로 감싸서 에러가 발생해도 후속 이벤트가 멈추지 않게.
    try {
      const r = rooms.find(x => x.id === roomId);
      if (!r) return;
      if (act === "mute_toggle") {
        notifySettings.toggleRoomMute(roomId);
        renderRoomList();
        return;
      }
      if (act === "popout") {
        if (SOLO_MODE) return;
        const url = BASE + `/chat?solo=1&room=${roomId}`;
        const features = _soloFeatures();
        const w = window.open(url, `knk_room_${roomId}`, features);
        if (w) try { w.focus(); } catch(_) {}
        return;
      }
      if (act === "settings") {
        // 현재 방으로 굳이 전환할 필요 없음 — 다이얼로그는 roomId 만으로 동작.
        // 이전에 openRoom + setTimeout 으로 했더니 종종 안 열리는 문제 발생.
        await openRoomSettings(roomId);
        return;
      }
      if (act === "leave") {
        // 헤더 '나가기'와 동일하게 — '내용 정리해서 저장 후 나가기 / 그냥 나가기' 다이얼로그 표시.
        // 다이얼로그·doLeaveRoom 이 activeRoom 기준이라, 먼저 그 방을 연 뒤 동일 다이얼로그를 띄움.
        try { await openRoom(r); } catch (_) {}
        try { els.leaveMyName.textContent = (app.dataset.meName || "나"); } catch (_) {}
        // 🗑 완전 삭제 옵션 — 소유자(대표 본인) + 1:1 방에서만 노출 (헤더 나가기 경로와 동일, 대표 지시 2026-06-05)
        if (els.leavePurgeBtn) {
          els.leavePurgeBtn.hidden = !(window._meIsOwner && activeRoom && activeRoom.type === "direct");
        }
        if (els.leaveRoomDialog) els.leaveRoomDialog.classList.add("open");
        return;
      }
      // 순서 조정
      if (["pin", "unpin", "top", "bottom", "up", "down", "reset"].includes(act)) {
        const res = await fetch(`${BASE}/api/rooms/${roomId}/order`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: act }),
        }).then(x => x.json()).catch(() => ({ error: "네트워크 오류" }));
        if (res.error) { alert(res.error); return; }
        await refreshRooms();
        return;
      }
    } catch (err) {
      console.error("[room context action]", act, err);
      alert(window.KNK_t("alert.actionFail","동작 실패") + ": " + (err && err.message ? err.message : err));
    }
  }

  // 바깥 클릭·ESC 닫기
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".room-context-menu")) closeRoomContextMenu();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeRoomContextMenu();
  });

  // ---------- render messages ----------
  // 연속된 같은 album_id 인 image 메시지를 1개 묶음으로 그룹화.
  function groupAlbums(msgs) {
    const out = [];
    let i = 0;
    while (i < msgs.length) {
      const m = msgs[i];
      const isAlbum = m.album_id && m.kind === "image" && m.file_path;
      if (isAlbum) {
        const group = [m];
        let j = i + 1;
        while (j < msgs.length) {
          const n = msgs[j];
          if (n.album_id === m.album_id && n.kind === "image" && n.file_path && n.user_id === m.user_id) {
            group.push(n);
            j++;
          } else break;
        }
        if (group.length >= 2) {
          out.push({
            ...m,
            _album: group.map(g => ({
              id: g.id, file_path: g.file_path, file_name: g.file_name
            })),
          });
          i = j;
          continue;
        }
      }
      out.push(m);
      i++;
    }
    return out;
  }

  // 날짜가 바뀐 첫 메시지에만 월.일 표기. (시스템 메시지는 시간 표기가 없으므로 날짜 기준에서 제외)
  function _markShowDates(list) {
    let prev = null;
    for (const gm of list) {
      if (gm.kind === "system") { gm._showDate = false; continue; }
      const ds = new Date(gm.created_at).toDateString();
      gm._showDate = (ds !== prev);
      prev = ds;
    }
    _lastMsgDateStr = prev;
  }

  // 2줄 이상으로 줄바꿈된 텍스트 메시지는 읽음·시각을 말풍선 아래로 내려 본문을 넓게 사용 (대표 지시 2026-05-29)
  //   텍스트 본문(.bubble-orig)의 줄 수를 측정 → 2줄↑이면 .msg 에 .wide-msg 부여 (사진·파일·스티커는 .bubble-orig 가 없어 제외)
  function _applyWideMsgLayout() {
    if (!els.messages) return;
    const origs = els.messages.querySelectorAll(".msg .bubble-orig");
    const marks = [];
    origs.forEach(o => {
      const cs = getComputedStyle(o);
      let lh = parseFloat(cs.lineHeight);
      if (!lh || isNaN(lh)) lh = (parseFloat(cs.fontSize) || 14) * 1.45;
      const lines = o.clientHeight / lh;     // 읽기 단계 (한 번에 측정)
      const msg = o.closest(".msg");
      if (msg) marks.push([msg, lines >= 1.8]);
    });
    marks.forEach(([msg, multi]) => msg.classList.toggle("wide-msg", multi));  // 쓰기 단계
  }

  // ───────── 카톡식 날짜 구분선 + '여기까지 읽었습니다' 읽음 경계 (대표 지시 2026-06-04) ─────────
  let _entryLastReadId = 0;        // 방 진입 시점의 내 마지막 읽은 메시지 id (markRead 로 갱신되기 전 스냅샷)
  let _scrollToUnreadOnce = false; // 방 열 때 1회만 '여기까지' 줄로 스크롤
  const _DIVIDER_LOCALE = { ko: "ko-KR", vi: "vi-VN", en: "en-US", zh: "zh-CN" };
  // 가운데 날짜 띠 — 예: '📅 2026년 6월 4일 목요일' (화면 언어에 맞춰 자동 현지화)
  function _dateDividerHtml(iso) {
    const d = new Date(iso);
    if (isNaN(d)) return "";
    const lang = (typeof _curLang === "function") ? _curLang() : "ko";
    let label;
    try {
      label = d.toLocaleDateString(_DIVIDER_LOCALE[lang] || "ko-KR",
        { year: "numeric", month: "long", day: "numeric", weekday: "long" });
    } catch (e) {
      const wd = ["일","월","화","수","목","금","토"][d.getDay()];
      label = `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일 ${wd}요일`;
    }
    return `<div class="date-divider"><span>📅 ${escapeHtml(label)}</span></div>`;
  }
  // 읽음 경계 줄 — '여기까지 읽었습니다' (안 읽은 메시지가 시작되는 자리)
  function _unreadDividerHtml() {
    const L = { ko: "여기까지 읽었습니다", vi: "Đã đọc đến đây", en: "You have read up to here", zh: "已读到此处" };
    const lang = (typeof _curLang === "function") ? _curLang() : "ko";
    return `<div class="unread-divider"><span>${escapeHtml(L[lang] || L.ko)}</span></div>`;
  }
  // 메시지 목록 HTML — 날짜가 바뀌는 자리에 날짜 띠, 진입 시 첫 안읽음 앞에 읽음 경계 줄 삽입
  function _buildMessagesHtml(grouped) {
    // 읽음 경계: 진입 시 내 마지막 읽은 id 다음의 첫 '남이 보낸' 메시지 앞. 위에 읽은 메시지가 있을 때만(맨 위는 제외).
    let unreadIdx = -1;
    if (_entryLastReadId > 0) {
      for (let i = 0; i < grouped.length; i++) {
        const gm = grouped[i];
        if (gm.id > _entryLastReadId && gm.user_id !== meId && gm.kind !== "system" && gm.kind !== "deleted") { unreadIdx = i; break; }
      }
    }
    const showUnread = unreadIdx > 0;
    const _GAP = 5 * 60 * 1000;   // 5분 — 넘으면 새 묶음 (대표 지시 2026-06-05)
    const _isG = (x) => x && x.kind !== "system";
    return grouped.map((m, i) => {
      let pre = "";
      if (m._showDate) pre += _dateDividerHtml(m.created_at);
      if (showUnread && i === unreadIdx) pre += _unreadDividerHtml();
      // 연속 메시지 묶기: 같은 사람 5분 이내 연속 → 아바타·이름·중간 시간 생략
      const _p = grouped[i - 1], _n = grouped[i + 1];
      const cont = _isG(m) && _isG(_p) && _p.user_id === m.user_id
        && !m._showDate && !(showUnread && i === unreadIdx)
        && (_msgTsMs(m) - _msgTsMs(_p) < _GAP);
      const runmid = _isG(m) && _isG(_n) && _n.user_id === m.user_id
        && !_n._showDate && !(showUnread && (i + 1) === unreadIdx)
        && (_msgTsMs(_n) - _msgTsMs(m) < _GAP);
      return pre + msgHtml(m, { cont, runmid });
    }).join("");
  }

  function renderMessages(msgs) {
    // 메모장(self) — 혼자 보는 방: 삭제 자리표시 + 시스템 메시지(방 이름 변경 등) 숨김 (대표 지시 2026-05-20)
    if (activeRoom && activeRoom.type === "self") {
      msgs = (msgs || []).filter(m => m.kind !== "deleted" && m.kind !== "system");
    }
    if (!msgs.length) {
      els.messages.innerHTML = `<div class="empty-state">${window.KNK_t("msg.emptyChat", "아직 메시지가 없습니다.<br>첫 메시지를 보내보세요.")}</div>`;
      _lastMsgDateStr = null;
      return;
    }
    const grouped = groupAlbums(msgs);
    _markShowDates(grouped);
    els.messages.innerHTML = _buildMessagesHtml(grouped);   // 날짜 띠 + 읽음 경계 줄 포함 (대표 지시 2026-06-04)
    wireMessageActions();
    _applyWideMsgLayout();     // 2줄↑ 메시지는 읽음·시각을 아래로 → 본문 넓게
    // 방 진입 시 안 읽은 메시지가 있으면 '여기까지 읽었습니다' 줄로, 아니면 최하단 (대표 지시 2026-06-04 카톡식)
    if (_scrollToUnreadOnce && els.messages.querySelector(".unread-divider")) {
      _scrollToUnreadOnce = false;
      _scrollMessagesToUnread();
    } else {
      _scrollToUnreadOnce = false;
      _forceMessagesToBottom();  // 방 처음 열 때 / 메시지 전체 재로드 시 무조건 최하단 (컴포저 높이 반영)
    }
  }

  function renderTextWithMentions(text) {
    const escaped = escapeHtml(text);
    // 이모지 시퀀스를 <span class="chat-emoji"> 로 래핑 → CSS font-size:130% 적용
    // ZWJ 시퀀스·국기(Regional Indicator 쌍)·변형선택자·수정자 포함
    const withEmoji = escaped.replace(
      /(?:\p{Regional_Indicator}{2}|\p{Extended_Pictographic}(?:[︎️]|⃣|\p{Emoji_Modifier})?(?:‍\p{Extended_Pictographic}(?:[︎️]|⃣|\p{Emoji_Modifier})?)*)/gu,
      e => `<span class="chat-emoji">${e}</span>`
    );
    // URL 자동 링크 — http(s):// 를 클릭 가능한 링크로 (새 탭, 대표 지시 2026-06-05).
    //   이미 escapeHtml 된 뒤라 안전(< > 없음). 끝의 문장부호(. , ! ? ) ])는 링크에서 제외.
    const withLinks = withEmoji.replace(/https?:\/\/[^\s<]+/g, (u0) => {
      let url = u0, trail = "";
      const t = url.match(/([)\].,!?]+)$/);
      if (t) { trail = t[1]; url = url.slice(0, -trail.length); }
      return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="msg-link">${url}</a>` + trail;
    });
    // @ 가 '맨 앞이거나 공백/이모지 뒤'일 때만 멘션으로 표시 → 이메일(글자@도메인)은 멘션 처리 안 함. (대표 지시 2026-06-02)
    return withLinks.replace(/(^|[\s>])@([\w가-힣]{1,30})/g, (full, b, name) => {
      const u = users.find(x => x.username === name || x.display_name === name);
      const isMe = u && u.id === meId;
      // 멘션은 '이름 직급 부서'로 표시 (저장은 @이름, 표시 때 보강) — 대표 지시 2026-05-22
      let label = name;
      if (u) {
        const t = u.title || "";
        const d = u.department ? (typeof deptShortLabel === "function" ? deptShortLabel(u.department) : u.department) : "";
        label = [u.display_name, t, d].filter(Boolean).join(" ");
      }
      return b + `<span class="mention${isMe ? ' me' : ''}">@${escapeHtml(label)}</span>`;
    });
  }

  // 시스템 메시지의 사람 이름([...] / "by 이름")을 '이름 직급 부서'로 보강 표시 (대표 지시 2026-05-22)
  //   사용자 display_name 과 정확히 일치하는 토큰만 보강 → 프로젝트명·요청명 등 비-이름은 그대로.
  function _enrichSystemNames(text) {
    if (!text || !Array.isArray(users) || !users.length) return text;
    const enrich = (nm) => {
      const name = (nm || "").trim();
      const u = users.find(x => x.display_name === name);
      if (!u) return nm;
      const t = u.title || "";
      const d = u.department ? (typeof deptShortLabel === "function" ? deptShortLabel(u.department) : u.department) : "";
      return [u.display_name, t, d].filter(Boolean).join(" ");
    };
    let out = text.replace(/\[([^\]]+)\]/g, (m0, inner) =>
      "[" + inner.split(",").map(s => enrich(s)).join(", ") + "]"
    );
    out = out.replace(/by\s+([^)]+)\)/g, (m0, nm) => "by " + enrich(nm) + ")");
    return out;
  }

  // 메시지 시각(ms) — 연속 메시지 묶기 시간 비교용 (대표 지시 2026-06-05)
  function _msgTsMs(m) {
    if (!m || !m.created_at) return 0;
    const t = Date.parse(String(m.created_at).replace(" ", "T"));
    return isFinite(t) ? t : 0;
  }
  function msgHtml(m, opts) {
    if (m.kind === "system") {
      return `<li class="msg system" data-msg-id="${m.id}"><div class="body"><div class="bubble">${escapeHtml(_enrichSystemNames(m.content))}</div></div></li>`;
    }
    const mine = m.user_id === meId;
    let cls = mine ? "msg mine" : "msg";
    if (m.starred_by_me) cls += " starred";
    const _grp = opts || {};
    if (_grp.cont) cls += " cont";       // 같은 사람 연속 — 아바타·이름 숨김 (대표 지시 2026-06-05)
    if (_grp.runmid) cls += " runmid";   // 묶음의 마지막이 아님 — 시간·읽음 숨김

    // 인용 답장 카드 — 원본 메시지 미니
    let quoteCard = "";
    if (m.quoted_message_id && m.quoted) {
      if (m.quoted.deleted) {
        quoteCard = `<div class="quote-card quote-card-deleted">↪ 원본 메시지가 삭제됨</div>`;
      } else {
        const q = m.quoted;
        let qBody = "";
        if (q.kind === "image") qBody = "[사진]" + (q.file_name ? " " + q.file_name : "");
        else if (q.kind === "file") qBody = "[파일] " + (q.file_name || "");
        else if (q.kind === "sticker") qBody = "[스티커] " + (q.content || "");
        else qBody = (q.content || "").slice(0, 100);
        quoteCard = `
          <div class="quote-card" data-quote-mid="${q.id}" title="클릭하면 원본으로 이동">
            <div class="quote-card-bar" style="background:${q.avatar_color || '#3b82f6'}"></div>
            <div class="quote-card-body">
              <div class="quote-card-author">${escapeHtml(q.display_name || '')}</div>
              <div class="quote-card-text">${escapeHtml(qBody)}</div>
            </div>
          </div>`;
      }
    }

    // 전달(Forward) 카드 — 출처 메타데이터
    let forwardCard = "";
    if (m.forwarded_from_message_id) {
      const fAuthor = m.forwarded_from_name || "(알 수 없음)";
      const fRoom = m.forwarded_from_room_name || "";
      const fAt = m.forwarded_from_created_at ? fmtTime(m.forwarded_from_created_at) : "";
      forwardCard = `
        <div class="forward-card">
          <div class="forward-card-head">↗ <b>${escapeHtml(fAuthor)}</b> 의 메시지 전달${fRoom ? ` · <span class="forward-room">${escapeHtml(fRoom)}</span>` : ""}</div>
          ${fAt ? `<div class="forward-card-time">원본 시각 ${fAt}</div>` : ""}
        </div>`;
    }

    // 👥 여러 방 공유 배지 — 글쓴이 본인에게만 작게 표시(받는 사람에겐 숨김) + 클릭 시 '공유된 방 목록' (대표 지시 2026-06-04)
    let shareCard = "";
    if (m.share_count && m.share_count >= 2 && m.user_id === meId) {
      shareCard = `<button type="button" class="share-card" data-act="share-targets" title="이 글이 공유된 방 보기">👥 ${m.share_count}곳에 공유 ›</button>`;
    }

    // 파일 버전 배지
    const verBadge = (m.version_no && m.version_no > 0)
      ? `<span class="ver-badge ${m.is_latest_version ? 'latest' : ''}" title="${m.is_latest_version ? '최신 버전' : '이전 버전'} - 클릭해서 모든 버전 보기" data-act="versions">v${m.version_no}</span>`
      : "";

    let bubble = "";
    if (m.kind === "image" && m._album && m._album.length >= 2) {
      // ★ 앨범 묶음 — 사진 N장을 1개 그리드 메시지로
      cls += " image album";
      const photos = m._album;
      const display = photos.slice(0, 4);
      const more = photos.length > 4 ? photos.length - 4 : 0;
      const tiles = display.map((p, idx) => {
        const moreOverlay = (idx === 3 && more > 0)
          ? `<div class="album-more">+${more}</div>` : "";
        return `<a class="album-tile" href="${BASE}/uploads/${escapeHtml(p.file_path)}" target="_blank" data-img="1" data-msg-id="${p.id}">
          <img src="${BASE}/uploads/${escapeHtml(p.file_path)}" alt="${escapeHtml(p.file_name || "")}" loading="lazy">
          ${moreOverlay}
        </a>`;
      }).join("");
      bubble = `<div class="bubble album-bubble"><div class="album-grid album-grid-${Math.min(photos.length, 4)}">${tiles}</div></div>`;
    } else if (m.kind === "image" && m.file_path) {
      cls += " image";
      // album_id 가 있으면 (실시간 첫 도착 등) li 에 표식만 박아두고 외형은 그대로
      bubble = `<a class="bubble" href="${BASE}/uploads/${escapeHtml(m.file_path)}" target="_blank" data-img="1"><img src="${BASE}/uploads/${escapeHtml(m.file_path)}" alt="${escapeHtml(m.file_name || "")}" loading="lazy"></a>`;
    } else if (m.kind === "file" && m.file_path) {
      cls += " file";
      bubble = `
        <div class="bubble">
          <div class="file-icon">${fileIcon(m.file_name)}</div>
          <div class="file-info">
            <div class="file-name">${escapeHtml(m.file_name || "파일")}${verBadge}</div>
            <div class="file-size">${fmtSize(m.file_size)}</div>
          </div>
          <a class="file-link" href="${BASE}/uploads/${escapeHtml(m.file_path)}?dl=1" download="${escapeHtml(m.file_name || "")}">받기</a>
        </div>`;
    } else if (m.kind === "sticker" && m.file_name) {
      cls += " sticker";
      // loading="eager": 스티커는 항상 최하단 → lazy 로딩 시 높이 0으로 잘못된 스크롤 계산 발생 (iOS)
      bubble = `<div class="bubble sticker-bubble"><img class="sticker-img" src="${BASE}/static/stickers/${encodeURIComponent(m.file_name)}" alt="${escapeHtml(m.content || "스티커")}" title="${escapeHtml(m.content || "")}" loading="eager"></div>`;
    } else if (m.kind === "multipart" && Array.isArray(m.parts) && m.parts.length) {
      // 묶음 메시지 — 글+그림을 원본 순서대로 한 말풍선 안에 차곡차곡 (대표 지시 2026-06-06)
      cls += " multipart";
      const _mpHtml = m.parts.map(p => {
        if (p && p.type === "text") {
          const _t = String(p.text || "").replace(/\s+$/, "");
          return _t ? `<div class="bubble-orig mp-text">${renderTextWithMentions(_t)}</div>` : "";
        }
        if (p && p.type === "image" && p.file_path) {
          return `<a class="mp-image" href="${BASE}/uploads/${escapeHtml(p.file_path)}" target="_blank" data-img="1"><img src="${BASE}/uploads/${escapeHtml(p.file_path)}" alt="${escapeHtml(p.file_name || "")}" loading="lazy"></a>`;
        }
        return "";
      }).join("");
      bubble = `<div class="bubble multipart-bubble">${_mpHtml}</div>`;
    } else {
      // 텍스트 메시지 — 원문 + 번역(있으면) 을 같은 bubble 안에 묶음 (대표 지시 2026-05-28 안 A)
      // ⚠ .bubble 은 white-space: pre-wrap 이라 template literal 의 줄바꿈/들여쓰기 공백도 그대로 화면에 보임 → 한 줄로 압축 필수
      const _trsForBubble = m.translations || {};
      const _trKeys = Object.keys(_trsForBubble);
      let _trInside = "";
      if (_trKeys.length > 0) {
        _trInside = _trKeys.map(lang =>
          `<div class="bubble-translation" data-lang="${lang}"><span class="tr-lang-chip">🌐 ${lang.toUpperCase()}</span><span class="tr-text">${escapeHtml(_trsForBubble[lang])}</span></div>`
        ).join("");
      }
      // 원문 내용 끝의 trailing 공백/줄바꿈도 제거 (pre-wrap 때문에 빈 줄로 보임)
      const _origText = (m.content || "").replace(/\s+$/, "");
      bubble = `<div class="bubble"><div class="bubble-orig">${renderTextWithMentions(_origText)}</div>${_trInside}</div>`;
    }
    // 반응 집계
    const rxAgg = {};
    (m.reactions || []).forEach(r => {
      if (!rxAgg[r.emoji]) rxAgg[r.emoji] = { count: 0, by: [], byMe: false };
      rxAgg[r.emoji].count++;
      rxAgg[r.emoji].by.push(r.display_name);
      if (r.user_id === meId) rxAgg[r.emoji].byMe = true;
    });
    const rxHtml = Object.entries(rxAgg).map(([e, info]) =>
      `<button type="button" class="rx-chip ${info.byMe ? 'mine' : ''}" data-emoji="${escapeHtml(e)}" title="${escapeHtml(info.by.join(', '))}">${escapeHtml(e)} ${info.count}</button>`
    ).join("");

    // 전달확인(ack) 기능은 ✅ reaction 으로 통합 — 우클릭 메뉴에서 ✅ 선택.
    // 메시지 버블 아래의 별도 "확인" 버튼은 화면 정리를 위해 표시하지 않음.
    // (옛 ack 데이터는 DB 에 남아있지만 UI 에 노출하지 않음)
    const ackHtml = "";

    // 읽음/안읽음 — 모든 메시지에 표시 (내 것 + 남의 것). 누가 확인/미확인인지 전원 파악 (대표 지시 2026-05-29)
    // 안 읽은 사람 카운트는 '그 메시지 작성자'를 제외 (작성자는 당연히 읽음).
    // 귓속말이면 수신자 1명만 카운트 (다른 멤버는 메시지를 보지도 못 함).
    let readBadge = "";
    if (roomReadStatus.members && roomReadStatus.members.length > 1 && (!activeRoom || activeRoom.id !== window.__BUG_ROOM_ID__)) {   // (신고)채널은 읽음/참여자 표시 안 함 (대표 지시 2026-06-03)
      const senderId = m.user_id;
      let others;
      // 비활성(잠금)된 계정은 '안 읽은 사람' 계산에서 제외 (대표 지시 2026-06-05) — 퇴사자 잠금 시 '1' 이 안 사라지던 문제 방지.
      //   (삭제된 계정은 read_status 가 users 와 INNER JOIN 이라 이미 자동 제외됨)
      if (m.whisper_to_user_id) {
        others = roomReadStatus.members.filter(mb => mb.user_id === m.whisper_to_user_id && mb.active !== 0);
      } else {
        others = roomReadStatus.members.filter(mb => mb.user_id !== senderId && mb.active !== 0);
      }
      const unreadBy = others.filter(mb => (mb.last_read_message_id || 0) < m.id);
      if (others.length === 0) {
        // 귓속말인데 수신자 정보 미상 — 표시 안 함
      } else if (unreadBy.length > 0) {
        const unreadNames = unreadBy.map(mb => mb.display_name).join(", ");
        // 클릭 가능 (대표 지시 2026-05-19) — 누가 읽고 안 읽었는지 명단 다이얼로그
        readBadge = `<span class="read-badge unread clickable" data-read-status-mid="${m.id}" title="${escapeHtml('클릭: 읽음/안읽음 명단 보기 (안 읽음: ' + unreadNames + ')')}">${unreadBy.length}</span>`;
      } else {
        // 모두 읽음 — '읽음' 글자를 표시하지 않음(시간만 남김). 안 읽은 사람이 있을 때만 숫자 배지를 보여줌.
        //   읽음 표시가 너무 많아 복잡해 보여 제거 (대표 지시 2026-06-05). 카톡식 — 전원 읽으면 표시가 사라짐.
        readBadge = "";
      }
    }

    const starBtnCls = m.starred_by_me ? "star-btn starred" : "star-btn";

    // 번역 표시 — 텍스트 메시지면 bubble 안에 합쳐서 표시 (대표 지시 2026-05-28 안 A)
    // 텍스트가 아닌 메시지(이미지·파일 등)의 경우 외부 trHtml 로 표시 (bubble 안에 못 들어감)
    let trHtml = "";
    const trs = m.translations || {};
    const trKeys = Object.keys(trs);
    if (trKeys.length > 0 && !(m.kind === "text" || !m.kind)) {
      // 비 텍스트 메시지 — 캡션 번역 등이 있다면 외부에
      trHtml = trKeys.map(lang => `
        <div class="msg-translation" data-lang="${lang}">
          <span class="tr-lang">🌐 ${lang.toUpperCase()}</span>
          <span class="tr-text">${escapeHtml(trs[lang])}</span>
        </div>
      `).join("");
    }
    // 텍스트 메시지에만 번역 버튼 노출
    const trBtn = (m.kind === "text" || !m.kind)
      ? `<button type="button" class="msg-action-btn" data-act="translate" title="베트남어/영어/한국어로 번역">🌐</button>`
      : "";

    // 스레드 — 답글 카운트 배지
    let threadHtml = "";
    if (m.thread_reply_count && m.thread_reply_count > 0) {
      const cnt = m.thread_reply_count;
      const lastAt = m.thread_last_at ? fmtTime(m.thread_last_at) : "";
      threadHtml = `<button type="button" class="thread-reply-badge" data-act="open_thread" title="스레드 열기">
        💬 답글 ${cnt}${lastAt ? ` · 마지막 ${lastAt}` : ""}
      </button>`;
    }

    // 귓속말 — 메시지 자체에 노란 카드 + 🤫 + 대상자 표시
    const isWhisper = !!m.whisper_to_user_id;
    if (isWhisper) cls += " whisper-msg";
    let whisperHeader = "";
    if (isWhisper) {
      const targetName = m.whisper_to_name || `사용자 #${m.whisper_to_user_id}`;
      const fromTo = mine
        ? `→ ${escapeHtml(targetName)} 에게만 보임`
        : `${escapeHtml(m.display_name)} → 나에게만`;
      whisperHeader = `<div class="whisper-header">🤫 귓속말 · ${fromTo}</div>`;
    }

    return `
      <li class="${cls}" data-msg-id="${m.id}" data-parent-msg-id="${m.parent_message_id || ""}" data-uid="${m.user_id || ""}" data-ts="${_msgTsMs(m)}" data-whisper-to="${m.whisper_to_user_id || ""}" data-album-id="${m.album_id || ""}">
        <div class="avatar" style="background:${m.avatar_color || "#3b82f6"}">${_avatarBody(m)}</div>
        <div class="body">
          ${mine ? "" : (() => {
            // 메시지 작성자 — 이름 + (작게·연하게) 직급·부서 인라인 표시 (대표 지시 2026-05-22)
            //   본사: '구매팀' (숫자코드 없음) / 베트남: '12-VN01 관리팀' → 'VN관리팀'
            // 직원은 users 디렉터리 캐시, 게스트(외부)는 이 방 멤버 메타 캐시에서 직책·부서 보강 (대표 지시 2026-05-30)
            const _cached = (Array.isArray(users) ? users.find(x => x.id === m.user_id) : null)
                            || (window._roomMemberMeta && window._roomMemberMeta[m.user_id])
                            || {};
            const _isGuestAuthor = !!_cached.is_guest;
            // 게스트는 보는 사람이 지정한 '대화방 표현'(view_alias)이 있으면 이름 자체를 그걸로 교체 (대표 지시 2026-05-30, 내 화면에서만)
            const _viewAlias = _isGuestAuthor ? (_cached.view_alias || "") : "";
            const _origName = _dispName(_cached) || m.display_name || "";
            const _nm = _viewAlias || _origName;
            const _t = _dispTitle(_cached) || m.title || "";
            const _d = _cached.department || m.department || "";
            const _enDept = (_useEnNames() && _cached.department_en) ? _cached.department_en : "";
            // 게스트 부서는 자유 입력 텍스트라 코드 라벨 변환(deptShortLabel) 없이 원문 그대로
            const _shortDept = _isGuestAuthor
              ? _d
              : (_enDept || (_d ? (typeof deptShortLabel === "function" ? deptShortLabel(_d) : _d) : ""));
            // 게스트(외부 고객)는 '이름 직책 회사 부서' 형식 — 회사명을 직책과 부서 사이에 표시 (대표 지시 2026-05-30)
            const _guestCompany = _isGuestAuthor ? (_cached.guest_company || "") : "";
            const _inline = [];
            if (_t) _inline.push(_t);
            if (_guestCompany) _inline.push(_guestCompany);
            if (_shortDept) _inline.push(_shortDept);
            // 표현(별칭)이 설정되면 자동 메타(직책·회사·부서)는 숨김 — 사용자가 적은 이름표만 깔끔히 표시
            const _metaInline = _viewAlias ? "" : _inline.join(" ");
            // hover 툴팁 — 부서는 공식 코드 형태(deptDisplayLabel)로
            const _tipMeta = [];
            if (_t) _tipMeta.push(_t);
            if (_guestCompany) _tipMeta.push(_guestCompany);
            if (_d) _tipMeta.push(_enDept || (typeof deptDisplayLabel === "function" ? deptDisplayLabel(_d) : _d));
            const _tip = _viewAlias
              ? `${_viewAlias} · 원래 ${_origName}${_tipMeta.length ? ` (${_tipMeta.join(" · ")})` : ""}`
              : (_tipMeta.length ? `${_nm} (${_tipMeta.join(" · ")})` : "");
            return `<div class="author" data-uid="${m.user_id || ""}" title="${escapeHtml(_tip)}">${escapeHtml(_nm)}${_metaInline ? `<span class="author-meta">${escapeHtml(_metaInline)}</span>` : ""}</div>`;
          })()}
          ${whisperHeader}
          ${forwardCard}
          ${shareCard}
          ${quoteCard}
          <div class="bubble-row">${bubble}<div class="time">${m.edited_at ? `<span class="edited-badge" title="원본: ${fmtTime(m.created_at)} · 편집: ${fmtTime(m.edited_at)}">✏ 편집됨 ${fmtTime(m.edited_at)}</span>` : ""}${readBadge}${fmtMsgTime(m.created_at, false)}</div></div>
          ${trHtml}
          ${rxHtml ? `<div class="reactions">${rxHtml}</div>` : ""}
          ${ackHtml}
          ${threadHtml}
        </div>
        <div class="msg-action-bar">
          <button type="button" class="msg-action-btn" data-act="rx" data-emoji="👍" title="좋아요">👍</button>
          <button type="button" class="msg-action-btn" data-act="rx" data-emoji="✅" title="확인">✅</button>
          <button type="button" class="msg-action-btn" data-act="rx" data-emoji="❤" title="응원">❤</button>
          ${trBtn}
          <button type="button" class="${starBtnCls}" data-act="star" title="중요 결정으로 별표">${m.starred_by_me ? "★" : "☆"}</button>
          <button type="button" class="msg-action-btn" data-act="request" title="이 메시지를 요청으로 등록">📌 요청</button>
          ${(mine || window._meRole === "ceo") && m.kind !== "deleted" ? `<button type="button" class="msg-action-btn msg-action-delete" data-act="delete" title="메시지 삭제 (대표 지시 2026-05-19)">🗑️</button>` : ""}
        </div>
      </li>`;
  }

  function fileIcon(name) {
    const ext = (name || "").split(".").pop().toLowerCase();
    if (["pdf"].includes(ext)) return "📄";
    if (["doc","docx","hwp","hwpx"].includes(ext)) return "📝";
    if (["xls","xlsx","csv"].includes(ext)) return "📊";
    if (["ppt","pptx"].includes(ext)) return "🎯";
    if (["zip","7z","rar"].includes(ext)) return "🗜";
    if (["dwg","dxf","step","stp","stl"].includes(ext)) return "📐";
    if (["mp4","mov","avi","mkv"].includes(ext)) return "🎬";
    if (["mp3","wav"].includes(ext)) return "🎵";
    return "📎";
  }

  // ─── 앨범 디바운스 재렌더 ───
  // 같은 album_id 의 사진 N장이 거의 동시에 socket 으로 도착하므로,
  // 200ms 디바운스 후 메시지 전체 재로드 → groupAlbums 가 그리드 1개로 묶음.
  let _albumRerenderTimer = null;
  let _albumRerenderForce = false;
  function scheduleAlbumRerender(forceScroll) {
    if (forceScroll) _albumRerenderForce = true;
    if (_albumRerenderTimer) clearTimeout(_albumRerenderTimer);
    _albumRerenderTimer = setTimeout(async () => {
      _albumRerenderTimer = null;
      const force = _albumRerenderForce;
      _albumRerenderForce = false;
      if (!activeRoom) return;
      try {
        const msgs = await api.messages(activeRoom.id);
        if (!msgs.length) return;
        const grouped = groupAlbums(msgs);
        _markShowDates(grouped);
        els.messages.innerHTML = _buildMessagesHtml(grouped);   // 날짜 띠 + 읽음 경계 줄 포함
        wireMessageActions();
        _applyWideMsgLayout();
        scrollToBottom({ force });
      } catch (e) {}
    }, 200);
  }

  // forceScroll=true: 본인 메시지 전송 직후 등 무조건 최하단으로.
  // 기본: 사용자가 위쪽 보고 있으면 위치 유지, 맨 아래 근처면 자동 스크롤.
  function appendMessage(m, forceScroll) {
    if (!els.messages.querySelector(".msg")) {
      els.messages.innerHTML = "";
    }
    // 앨범 사진은 디바운스 재렌더 — N장 합쳐서 그리드 1개로 그림
    if (m.album_id && m.kind === "image" && m.file_path) {
      scheduleAlbumRerender(forceScroll);
      return;
    }
    // 날짜가 바뀐 첫 메시지면 월.일 표기 (직전 렌더 메시지 날짜와 비교)
    if (m.kind !== "system") {
      const ds = new Date(m.created_at).toDateString();
      m._showDate = (ds !== _lastMsgDateStr);
      _lastMsgDateStr = ds;
    } else {
      m._showDate = false;
    }
    // 연속 메시지 묶기 — 직전 메시지가 같은 사람·5분 이내면 이어붙임 (대표 지시 2026-06-05)
    let _cont = false;
    if (m.kind !== "system" && !m._showDate) {
      const _le = els.messages.lastElementChild;
      if (_le && _le.classList.contains("msg") && !_le.classList.contains("system")
          && _le.dataset.uid && parseInt(_le.dataset.uid, 10) === (m.user_id || 0)) {
        const _lt = parseInt(_le.dataset.ts || "0", 10);
        if (_lt && (_msgTsMs(m) - _lt) < 5 * 60 * 1000) {
          _cont = true;
          _le.classList.add("runmid");   // 이전 메시지: 이제 묶음 중간 → 시간 숨김
        }
      }
    }
    els.messages.insertAdjacentHTML("beforeend", (m._showDate ? _dateDividerHtml(m.created_at) : "") + msgHtml(m, { cont: _cont, runmid: false }));
    wireMessageActions();
    _applyWideMsgLayout();
    scrollToBottom({ force: forceScroll === true });

    // 이미지/스티커/파일 첨부 — 이미지 로드 완료 후 재스크롤 (iOS 핵심 수정)
    // 문제: insertAdjacentHTML 직후 img.height=0 → scrollHeight 과소평가 → 이미지 화면 밖 잘림
    // 해법: 새로 삽입된 li 안의 img에 onload/onerror 걸어 로드 완료 시점에 다시 스크롤
    if (m.kind === "image" || m.kind === "sticker" || m.kind === "file") {
      const lastLi = els.messages.lastElementChild;
      if (lastLi) {
        const imgs = lastLi.querySelectorAll("img");
        const _reScroll = () => scrollToBottom({ force: forceScroll === true });
        imgs.forEach(img => {
          if (!img.complete || img.naturalHeight === 0) {
            img.addEventListener("load",  _reScroll, { once: true });
            img.addEventListener("error", _reScroll, { once: true });
          }
        });
        // 안전망: 500ms 후에도 한 번 더 (이미지 없는 파일 첨부 포함)
        if (forceScroll === true) {
          setTimeout(_reScroll, 500);
        }
      }
    }
  }

  // 단일 메시지 부분 갱신 (반응·ack·별표 등 변경 시)
  async function refreshSingleMessage(messageId) {
    if (!activeRoom) return;
    const msgs = await api.messages(activeRoom.id);
    const target = msgs.find(m => m.id === messageId);
    if (!target) return;
    const li = els.messages.querySelector(`.msg[data-msg-id="${messageId}"]`);
    if (li) {
      const tmp = document.createElement("div");
      tmp.innerHTML = msgHtml(target, { cont: li.classList.contains("cont"), runmid: li.classList.contains("runmid") });
      li.replaceWith(tmp.firstElementChild);
      wireMessageActions();
    }
  }

  // 파일 버전 체인 다이얼로그
  async function showVersionsDialog(messageId) {
    if (!els.versionsDialog) return;
    const versions = await fetch(`${BASE}/api/files/${messageId}/versions`).then(r => r.json());
    if (!versions || !versions.length) {
      els.versionsList.innerHTML = `<div class="empty-state">버전 정보가 없습니다.</div>`;
    } else {
      els.versionsList.innerHTML = versions.map(v => `
        <div class="version-row" style="display:flex;align-items:center;gap:10px;padding:10px;border-bottom:1px solid var(--border);">
          <span class="ver-badge ${v.version_no === versions[0].version_no ? 'latest' : ''}">v${v.version_no}</span>
          <div style="flex:1;min-width:0;">
            <div style="font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(v.file_name)}</div>
            <div style="font-size:calc(11px + var(--fs-add-ui));color:var(--text-soft);">${escapeHtml(v.display_name)} · ${fmtDate(v.created_at)} · ${fmtSize(v.file_size)}</div>
          </div>
          <a href="${BASE}/uploads/${escapeHtml(v.file_path)}?dl=1" download="${escapeHtml(v.file_name)}" class="file-link">받기</a>
        </div>
      `).join("");
    }
    els.versionsDialog.showModal();
  }

  // 여러 방 공유 — '이 글이 어느 방들에 함께 보내졌는지' 목록 (글쓴이 전용). 배지 클릭 시 호출 (대표 지시 2026-06-04)
  async function showShareTargets(mid) {
    let data;
    try {
      data = await fetch(`${BASE}/api/messages/${mid}/share_targets`).then(r => r.json());
    } catch (e) {
      alert(window.KNK_t("alert.sharedRoomsLoadFail","공유한 방 목록을 불러오지 못했습니다."));
      return;
    }
    if (!data || data.error) { alert((data && data.error) || "불러오기 실패"); return; }
    const list = data.rooms || [];
    let dlg = document.getElementById("shareTargetsDialog");
    if (!dlg) {
      dlg = document.createElement("div");
      dlg.id = "shareTargetsDialog";
      dlg.className = "modal";
      dlg.setAttribute("data-modal", "");
      dlg.innerHTML = `
        <div class="modal-content" style="max-width:360px;">
          <button type="button" class="close-x modal-close-x" data-close>✕</button>
          <h3 style="margin-top:0;">👥 이 글을 공유한 방</h3>
          <p class="dialog-hint" id="shareTargetsHint" style="margin-top:2px;"></p>
          <div id="shareTargetsList" style="max-height:340px;overflow-y:auto;"></div>
          <div class="dialog-actions">
            <button type="button" data-close class="primary-btn">확인</button>
          </div>
        </div>`;
      document.body.appendChild(dlg);
      if (typeof dlg.showModal !== "function") {
        dlg.showModal = function() { dlg.classList.add("open"); document.body.style.overflow = "hidden"; };
        dlg.close = function() { dlg.classList.remove("open"); document.body.style.overflow = ""; };
      }
      dlg.querySelectorAll("[data-close]").forEach(b => b.addEventListener("click", () => dlg.close()));
      dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
    }
    const curId = (activeRoom && activeRoom.id) || 0;   // 지금 보고 있는(눌러서 연) 방
    const hint = dlg.querySelector("#shareTargetsHint");
    if (hint) hint.textContent = `이 글은 아래 ${list.length}개 방에 함께 보내졌습니다. 다른 방을 누르면 이동합니다.`;
    const listEl = dlg.querySelector("#shareTargetsList");
    if (listEl) {
      listEl.innerHTML = list.length
        ? list.map(r => {
            const isCur = (r.id === curId);
            const tags = (r.is_origin ? '<span class="share-tag share-tag-origin">✏️ 작성한 방</span>' : '')
                       + (isCur ? '<span class="share-tag share-tag-cur">📍 지금 방</span>' : '');
            return `
            <div class="share-target-row${isCur ? ' is-cur' : ''}" data-room-id="${r.id}" title="${isCur ? '지금 보고 있는 방' : '이 방으로 이동'}">
              <span class="share-target-main"><span class="share-target-name">${escapeHtml(r.name)}</span>${tags}</span>
              ${isCur ? '' : '<span class="share-target-go">이동 ›</span>'}
            </div>`;
          }).join("")
        : `<div style="padding:18px;text-align:center;color:var(--text-soft);">공유한 방 정보가 없습니다.</div>`;
      listEl.querySelectorAll(".share-target-row").forEach(row => {
        row.addEventListener("click", () => {
          const rid = parseInt(row.dataset.roomId, 10);
          dlg.close();
          if (rid === curId) return;   // 이미 보고 있는 방이면 이동 안 함
          const rm = (rooms || []).find(x => x.id === rid);
          if (rm) openRoom(rm);
        });
      });
    }
    try { dlg.showModal(); } catch (_) {}
  }

  // 별표 (중요 결정) 모음 다이얼로그
  async function showStarredDialog() {
    if (!els.starredDialog || !activeRoom) return;
    const list = await fetch(`${BASE}/api/rooms/${activeRoom.id}/starred`).then(r => r.json());
    if (!list || !list.length) {
      els.starredList.innerHTML = `<div class="empty-state">별표한 메시지가 없습니다.<br>중요 결정·합의는 메시지에서 ★ 버튼으로 표시하세요.</div>`;
    } else {
      els.starredList.innerHTML = list.map(s => {
        let body = "";
        if (s.kind === "image" && s.file_path) {
          body = `<a href="${BASE}/uploads/${escapeHtml(s.file_path)}" target="_blank">[사진] ${escapeHtml(s.file_name || "")}</a>`;
        } else if (s.kind === "file" && s.file_path) {
          body = `<a href="${BASE}/uploads/${escapeHtml(s.file_path)}?dl=1" download="${escapeHtml(s.file_name || "")}">[파일] ${escapeHtml(s.file_name || "")}</a>`;
        } else {
          body = escapeHtml(s.content || "");
        }
        return `
          <div class="starred-row" style="padding:10px;border-bottom:1px solid var(--border);">
            <div style="font-size:calc(11px + var(--fs-add-ui));color:var(--text-soft);margin-bottom:4px;">★ ${escapeHtml(s.display_name)} · ${fmtDate(s.created_at)}</div>
            <div style="font-size:calc(13px + var(--fs-add-ui));line-height:1.5;">${body}</div>
          </div>
        `;
      }).join("");
    }
    els.starredDialog.showModal();
  }

  // ---------- 번역 (Claude Haiku) ----------
  let _translateStatus = null;  // { enabled, languages, ... }

  async function getTranslateStatus() {
    if (_translateStatus) return _translateStatus;
    try {
      _translateStatus = await fetch(BASE + "/api/translate/status").then(r => r.json());
    } catch (e) {
      _translateStatus = { enabled: false, languages: { vi: "Tiếng Việt", ko: "한국어", en: "English" } };
    }
    return _translateStatus;
  }

  async function openTranslateMenu(anchor, messageId) {
    // anchor: DOM 요소(가시 🌐 버튼) 또는 좌표 객체 { x, y } (우클릭 메뉴에서 호출 시).
    //   가시 버튼이 없거나 hidden 이면 getBoundingClientRect 가 0,0 → 좌상단으로 튀던 버그 수정.
    //   (대표 지시 2026-05-28)
    // 기존 popup 정리
    document.querySelectorAll(".translate-menu").forEach(p => p.remove());

    const status = await getTranslateStatus();
    const popup = document.createElement("div");
    popup.className = "translate-menu";
    if (!status.enabled) {
      popup.innerHTML = `
        <div class="tm-disabled">
          🌐 번역 기능 미설정<br>
          <small>관리자가 ANTHROPIC_API_KEY 설정 후 사용 가능</small>
        </div>`;
    } else {
      const langs = status.languages || { vi: "Tiếng Việt", ko: "한국어", en: "English" };
      popup.innerHTML = `
        <div class="tm-title">번역할 언어</div>
        ${Object.entries(langs).map(([code, name]) =>
          `<button type="button" data-lang="${code}">${escapeHtml(name)}</button>`
        ).join("")}
      `;
    }
    document.body.appendChild(popup);
    // 위치 계산
    let leftPx = 0, topPx = 0;
    const isCoord = anchor && typeof anchor === "object" && ("x" in anchor) && ("y" in anchor);
    if (isCoord) {
      leftPx = anchor.x; topPx = anchor.y;
    } else if (anchor && typeof anchor.getBoundingClientRect === "function") {
      const rect = anchor.getBoundingClientRect();
      // 요소가 hidden 또는 사라진 상태 → 0,0,0,0. fallback 으로 뷰포트 중앙.
      if (rect.width === 0 && rect.height === 0) {
        leftPx = Math.max(8, (window.innerWidth - 200) / 2);
        topPx  = Math.max(8, window.innerHeight / 2);
      } else {
        leftPx = rect.left;
        topPx  = rect.bottom + 4;
      }
    } else {
      leftPx = Math.max(8, (window.innerWidth - 200) / 2);
      topPx  = Math.max(8, window.innerHeight / 2);
    }
    popup.style.position = "fixed";
    // 화면 우측·하단 벗어남 방지
    const w = popup.offsetWidth || 200;
    const h = popup.offsetHeight || 180;
    if (leftPx + w > window.innerWidth - 8) leftPx = window.innerWidth - w - 8;
    if (topPx  + h > window.innerHeight - 8) topPx  = window.innerHeight - h - 8;
    if (leftPx < 8) leftPx = 8;
    if (topPx  < 8) topPx  = 8;
    popup.style.left = leftPx + "px";
    popup.style.top  = topPx  + "px";

    const close = (e) => {
      if (popup.contains(e.target)) return;
      popup.remove();
      document.removeEventListener("click", close, true);
    };
    setTimeout(() => document.addEventListener("click", close, true), 50);

    popup.querySelectorAll("button[data-lang]").forEach(b => {
      b.addEventListener("click", async (e) => {
        e.stopPropagation();
        const lang = b.dataset.lang;
        b.disabled = true;
        b.textContent = "...";
        try {
          const r = await fetch(`${BASE}/api/messages/${messageId}/translate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ target_lang: lang }),
          }).then(r => r.json());
          if (r.error) {
            alert(window.KNK_t("alert.translateFail","번역 실패") + ": " + r.error + "\n\n" + (r.hint || ""));
          } else {
            await refreshSingleMessage(messageId);
          }
        } catch (err) {
          alert(window.KNK_t("alert.translateReqFail","번역 요청 실패") + ": " + err);
        }
        popup.remove();
      });
    });
  }

  // 모바일에서 메시지 탭 시 액션바 토글. 데스크탑은 hover 로 자동.
  function wireMessageTapToggle() {
    if (window.innerWidth > 720) return;
    els.messages.querySelectorAll(".msg:not([data-tap-wired])").forEach(li => {
      li.setAttribute("data-tap-wired", "1");
      const bubble = li.querySelector(".bubble");
      if (!bubble) return;
      bubble.addEventListener("click", (e) => {
        // 링크·이미지 등 본래 클릭은 그대로
        if (e.target.closest("a, button, img, [data-img]")) return;
        // 다른 메시지의 show-actions 제거 (한 번에 한 메시지만)
        els.messages.querySelectorAll(".msg.show-actions").forEach(other => {
          if (other !== li) other.classList.remove("show-actions");
        });
        li.classList.toggle("show-actions");
      });
    });
  }

  // ───────── 메시지 컨텍스트 메뉴 (PC 메신저 스타일) ─────────
  function closeMessageContextMenu() {
    document.querySelectorAll(".msg-context-menu").forEach(m => m.remove());
  }
  function showMessageContextMenu(li, clientX, clientY) {
    closeMessageContextMenu();
    if (!li) return;
    const mid = parseInt(li.dataset.msgId, 10);
    if (!mid) return;
    const isMine = li.classList.contains("mine");
    const isText = !li.classList.contains("image") && !li.classList.contains("file") && !li.classList.contains("system");
    const isStarred = li.classList.contains("starred");
    const isSystem = li.classList.contains("system");

    if (isSystem) return;   // 시스템 메시지는 메뉴 없음

    // 우클릭/롱프레스 시점의 '선택된 텍스트' 캡처 — 메뉴 버튼 클릭 순간 선택이 풀리므로 지금 잡아둠.
    // 이 말풍선 안의 선택일 때만 인정. "텍스트 복사" 시 선택분만 복사(키보드 Ctrl+C 와 동일). (대표 지시 2026-06-02)
    let _ctxSelectedText = "";
    try {
      const _sel = window.getSelection();
      if (_sel && !_sel.isCollapsed) {
        const _bubble = li.querySelector(".bubble");
        const _raw = _sel.toString();
        if (_bubble && _raw.trim() && (_bubble.contains(_sel.anchorNode) || _bubble.contains(_sel.focusNode))) {
          _ctxSelectedText = _raw;   // 선택 그대로(트림 안 함) — 키보드 복사와 동일하게
        }
      }
    } catch (_) {}

    // 메뉴 항목 정의
    const items = [
      { label: window.KNK_t("menu.reactions"), section: true },
      { icon: "👍", label: window.KNK_t("menu.like"),    act: "rx", data: "👍" },
      { icon: "✅", label: window.KNK_t("menu.confirm"), act: "rx", data: "✅" },
      { icon: "❤",  label: window.KNK_t("menu.cheer"),  act: "rx", data: "❤" },
      { divider: true },
    ];
    if (isText) {
      items.push({ icon: "🌐", label: window.KNK_t("menu.translate"), act: "translate" });
      items.push({ icon: "📋", label: window.KNK_t("menu.copy"),      act: "copy" });
      items.push({ icon: "✂️", label: window.KNK_t("menu.selectCopy"), act: "select_copy" });
    }
    items.push({ icon: "💬", label: window.KNK_t("menu.threadReply"), act: "thread_reply" });
    items.push({ icon: "↪", label: window.KNK_t("menu.quoteReply"), act: "quote_reply" });
    items.push({ icon: "↗", label: window.KNK_t("menu.forward"), act: "forward" });
    items.push({ icon: "📤", label: window.KNK_t("menu.shareExt"), act: "share_ext" });
    items.push({ icon: isStarred ? "★" : "☆", label: isStarred ? window.KNK_t("menu.starOff") : window.KNK_t("menu.starOn"), act: "star" });
    items.push({ icon: "📌", label: window.KNK_t("menu.request"), act: "request" });
    // 본인 텍스트 메시지 → 편집 (대표 지시 2026-05-19) — 사진·파일은 X, 삭제된 메시지도 X
    const isDeleted = li.classList.contains("msg-deleted");
    if (isMine && isText && !isDeleted) {
      items.push({ divider: true });
      items.push({ icon: "✏️", label: window.KNK_t("menu.edit"), act: "edit" });
    }
    // 본인 메시지 OR 관리자 → 삭제 (대표 지시 2026-05-19)
    if ((isMine || window._meRole === "ceo") && !isDeleted) {
      if (!isMine || !isText) items.push({ divider: true });   // 편집 항목 없을 때만 divider 추가
      items.push({ icon: "🗑️", label: window.KNK_t("menu.delete"), act: "delete", danger: true });
    }

    // DOM 생성
    const menu = document.createElement("div");
    menu.className = "msg-context-menu";
    menu.innerHTML = items.map(it => {
      if (it.divider) return `<div class="mcm-divider"></div>`;
      if (it.section) return `<div class="mcm-section-label">${escapeHtml(it.label)}</div>`;
      const cls = it.danger ? "mcm-item mcm-danger" : "mcm-item";
      return `<button type="button" class="${cls}" data-act="${it.act}" ${it.data ? `data-emoji="${escapeHtml(it.data)}"` : ""}>
        <span class="mcm-icon">${escapeHtml(it.icon)}</span>
        <span>${escapeHtml(it.label)}</span>
      </button>`;
    }).join("");
    document.body.appendChild(menu);

    // 위치 — viewport 벗어나지 않게
    const w = menu.offsetWidth;
    const h = menu.offsetHeight;
    let x = clientX;
    let y = clientY;
    if (x + w > window.innerWidth - 8) x = window.innerWidth - w - 8;
    if (y + h > window.innerHeight - 8) y = window.innerHeight - h - 8;
    if (x < 8) x = 8;
    if (y < 8) y = 8;
    menu.style.left = x + "px";
    menu.style.top = y + "px";

    // 항목 클릭 핸들러 → 기존 동작 디스패치
    menu.querySelectorAll(".mcm-item").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const act = btn.dataset.act;
        closeMessageContextMenu();
        if (act === "rx") {
          await fetch(`${BASE}/api/messages/${mid}/react`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ emoji: btn.dataset.emoji }),
          });
        } else if (act === "star") {
          const r = await fetch(`${BASE}/api/messages/${mid}/star`, { method: "POST" }).then(x => x.json());
          if (r.action === "added") li.classList.add("starred");
          else li.classList.remove("starred");
        } else if (act === "edit") {
          // 메시지 인라인 편집 — 본인 텍스트만 (대표 지시 2026-05-19)
          startMessageEdit(li);
        } else if (act === "delete") {
          // 메시지 삭제 (본인 또는 관리자) — 대표 지시 2026-05-19
          if (!confirm(window.KNK_t("confirm.deleteMsg"))) return;
          try {
            const r = await fetch(`${BASE}/api/messages/${mid}`, { method: "DELETE" }).then(x => x.json());
            if (r.error) { alert(r.error); return; }
            // socketio 'message_deleted' broadcast 가 화면 갱신 처리. fallback 으로 본 화면도 즉시 갱신.
            _markMessageAsDeleted(parseInt(mid, 10));
          } catch (err) {
            alert(window.KNK_t("alert.deleteFail","삭제 실패") + ": " + (err.message || err));
          }
        } else if (act === "translate") {
          // 우클릭(컨텍스트) 위치를 그대로 anchor 로 사용 — 가시 🌐 버튼이 hidden 이라
          // getBoundingClientRect 가 0,0 으로 잡혀 메뉴가 좌상단으로 튀던 버그 수정 (대표 지시 2026-05-28)
          await openTranslateMenu({ x: clientX, y: clientY }, mid);
        } else if (act === "copy") {
          // 선택된 텍스트가 있으면 그 부분만(키보드 Ctrl+C 와 동일), 없으면 말풍선 전체 (대표 지시 2026-06-02)
          const txt = _ctxSelectedText || (li.querySelector(".bubble")?.textContent?.trim() || "");
          try { await navigator.clipboard.writeText(txt); } catch (_) {}
        } else if (act === "select_copy") {
          // 텍스트 선택 복사 — 말풍선을 선택모드로 전환 + 전체를 선택해 둠 → 손잡이로 범위를 줄여 원하는 부분만 복사 (대표 지시 2026-06-03)
          // 휴대폰 기본 선택 UI(손잡이·복사)는 이 항목 누를 때만 뜸 — 그냥 길게누르기엔 안 뜸(직전 수정 유지). 기존 2단계 부분선택 코드 재사용.
          const bub = li.querySelector(".bubble");
          if (bub) {
            setTimeout(() => {
              // 말풍선을 화면 가운데로 보내 OS 선택막대(복사·번역…)가 뜰 위쪽 공간 확보 → 선택글 안 가림 (대표 지시 2026-06-03)
              try { bub.scrollIntoView({ block: "center" }); } catch (_) {}
              bub.classList.add("lp-selectable");
              try {
                const sel = window.getSelection();
                sel.removeAllRanges();
                const range = document.createRange();
                range.selectNodeContents(bub);
                sel.addRange(range);
              } catch (_) {}
              if (navigator.vibrate) try { navigator.vibrate(20); } catch (_) {}
            }, 60);
          }
        } else if (act === "request") {
          let content;
          if (li.classList.contains("image")) {
            const fname = li.querySelector("img")?.alt || "사진";
            content = `[사진] ${fname}`;
          } else if (li.classList.contains("file")) {
            const fname = li.querySelector(".file-name")?.textContent?.trim() || "파일";
            content = `[파일] ${fname}`;
          } else {
            content = li.querySelector(".bubble")?.textContent?.trim() || "";
          }
          openNewRequest({ messageId: mid, sourceContent: content });
        } else if (act === "thread_reply") {
          openThreadPanel(mid);
        } else if (act === "quote_reply") {
          startQuoteReply(mid, li);
        } else if (act === "forward") {
          openForwardDialog(mid);
        } else if (act === "share_ext") {
          await _shareMessageExternal(li);
        }
      });
    });
  }
  // 바깥 클릭·ESC 로 메뉴 닫기
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".msg-context-menu")) closeMessageContextMenu();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeMessageContextMenu();
  });
  // 다른 메시지 contextmenu 이벤트가 발화되면 기존 메뉴 닫고 새로 띄움 (위 showMessageContextMenu 첫 줄에서 처리됨)

  // ============================================================
  // 스레드(Threaded Reply) — 사이드 패널
  // ============================================================
  let _activeThreadParentId = null;
  let _threadPending = [];   // 스레드 '보낼 첨부' 담기 목록 — 보내기/Enter 로 전송 (대표 지시 2026-06-04)

  function _renderThreadPending() {
    const bar = document.getElementById("threadPendingBar");
    if (!bar) return;
    if (!_threadPending.length) { bar.hidden = true; bar.innerHTML = ""; return; }
    bar.hidden = false;
    const tiles = _threadPending.map((f, i) => {
      const isImg = (f.type || "").startsWith("image/");
      const thumb = isImg
        ? `<img src="${URL.createObjectURL(f)}" alt="">`
        : `<span class="tpa-ico">📎</span>`;
      return `<div class="tpa-tile" title="${escapeHtml(f.name)}">${thumb}<span class="tpa-name">${escapeHtml(f.name)}</span><button type="button" class="tpa-x" data-idx="${i}" aria-label="빼기">✕</button></div>`;
    }).join("");
    bar.innerHTML = `<div class="tpa-head">📎 보낼 첨부 <b>${_threadPending.length}</b></div><div class="tpa-tiles">${tiles}</div>`;
    bar.querySelectorAll(".tpa-x").forEach(b => b.addEventListener("click", () => {
      const i = parseInt(b.getAttribute("data-idx"), 10);
      _threadPending.splice(i, 1);
      _renderThreadPending();
    }));
  }
  function _stageThreadFiles(files) {
    const arr = Array.from(files || []).filter(Boolean);
    if (!arr.length) return;
    _threadPending.push(...arr);
    _renderThreadPending();
  }
  function _clearThreadPending() { _threadPending = []; _renderThreadPending(); }

  async function openThreadPanel(parentId) {
    _activeThreadParentId = parentId;
    let panel = document.getElementById("threadPanel");
    if (!panel) {
      panel = document.createElement("div");
      panel.id = "threadPanel";
      panel.className = "thread-panel";
      panel.innerHTML = `
        <header class="thread-panel-head">
          <div class="thread-title">💬 스레드</div>
          <button type="button" class="thread-close-btn" id="threadCloseBtn" title="닫기">✕</button>
        </header>
        <div id="threadBody" class="thread-body"></div>
        <div id="threadPendingBar" class="thread-pending-bar" hidden></div>
        <form id="threadComposer" class="thread-composer">
          <input type="file" id="threadFileInput" multiple hidden>
          <button type="button" class="thread-attach-btn" id="threadAttachBtn" title="사진·파일 첨부" aria-label="사진·파일 첨부">
            <svg viewBox="0 0 24 24" width="19" height="19" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
            </svg>
          </button>
          <textarea id="threadInput" rows="2" placeholder="스레드에 답글…" maxlength="4000"></textarea>
          <button type="submit" class="thread-send-btn" title="전송" aria-label="전송">
            <svg class="send-icon" viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" focusable="false">
              <path fill="currentColor" d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
          </button>
        </form>
      `;
      document.body.appendChild(panel);
      document.getElementById("threadCloseBtn").addEventListener("click", closeThreadPanel);
      const form = document.getElementById("threadComposer");
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const ta = document.getElementById("threadInput");
        const text = (ta.value || "").trim();
        const hasFiles = _threadPending.length > 0;
        if ((!text && !hasFiles) || !_activeThreadParentId) return;
        // 1) 담긴 첨부(사진·파일) 먼저 전송
        if (hasFiles) {
          const files = _threadPending.slice();
          _clearThreadPending();
          await uploadThreadFiles(files);
        }
        // 2) 글 전송
        if (text) {
          const res = await fetch(`${BASE}/api/messages/${_activeThreadParentId}/reply`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content: text }),
          }).then(r => r.json()).catch(() => ({ error: "네트워크 오류" }));
          if (res.error) { alert(res.error); return; }
          ta.value = "";
          // 새 답글은 socket 의 thread_reply 이벤트로 자동 반영. 안전망으로 재로드.
          await renderThreadPanel(_activeThreadParentId);
        }
      });
      // 📎 첨부 — 사진·파일을 스레드 답글로 전송 (대표 지시 2026-06-04)
      const _tFile = document.getElementById("threadFileInput");
      document.getElementById("threadAttachBtn").addEventListener("click", () => {
        if (!_activeThreadParentId) return;
        _tFile.click();
      });
      _tFile.addEventListener("change", () => {
        const picked = Array.from(_tFile.files || []);
        _tFile.value = "";
        if (picked.length) _stageThreadFiles(picked);   // 즉시 전송 X → 담기
      });
      // 끌어다놓기(드래그&드롭) → '보낼 첨부'에 담기 (대표 지시 2026-06-04)
      panel.addEventListener("dragover", (e) => { e.preventDefault(); panel.classList.add("thread-drag"); });
      panel.addEventListener("dragleave", (e) => { if (e.target === panel) panel.classList.remove("thread-drag"); });
      panel.addEventListener("drop", (e) => {
        e.preventDefault();
        panel.classList.remove("thread-drag");
        const files = Array.from(e.dataTransfer?.files || []);
        if (files.length) _stageThreadFiles(files);
      });
      // Enter 발송 / Shift+Enter 줄바꿈
      const ta = document.getElementById("threadInput");
      ta.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
          e.preventDefault();
          document.getElementById("threadComposer").requestSubmit();
        }
      });
      // 키보드 대응 — 입력창 포커스 시 뷰포트 재계산 트리거 → 스레드 패널 높이(--vvh) 갱신
      // → 입력창이 키보드 위로 올라옴. 키보드 애니메이션 단계별로 여러 번 재계산.
      ta.addEventListener("focus", () => {
        [50, 200, 400, 700].forEach(ms => setTimeout(() => {
          try { window.dispatchEvent(new Event("resize")); } catch (e) {}
        }, ms));
      });
    }
    panel.classList.add("open");
    _clearThreadPending();   // 스레드 열 때 '보낼 첨부' 초기화 (대표 지시 2026-06-04)
    // 🧠 AI 요약 버튼 — 테스트 기간 방장·PM·관리자만 (대표 지시 2026-05-27)
    const _aiAllowedThread = (window._meRole === "ceo")
      || (activeRoom && (activeRoom.my_role === "host" || activeRoom.my_role === "sub_host"));
    if (_aiAllowedThread && typeof window._addThreadSummarizeBtn === "function") {
      window._addThreadSummarizeBtn(parentId);
    }
    // 이전 스레드 요약 박스 제거 (새 부모로 열렸을 때)
    const oldBox = document.getElementById("threadAiSumBox");
    if (oldBox) oldBox.remove();
    await renderThreadPanel(parentId);
    setTimeout(() => document.getElementById("threadInput")?.focus(), 50);
  }

  // 스레드 답글로 사진·파일 업로드 — 메인 첨부와 같은 검증·진행률 재사용 (대표 지시 2026-06-04)
  async function uploadThreadFiles(files) {
    if (!_activeThreadParentId || !activeRoom || !files || !files.length) return;
    const list = Array.from(files);
    const PER_FILE_LIMIT = 500 * 1024 * 1024;     // 500MB
    const TOTAL_LIMIT    = 1000 * 1024 * 1024;    // 1GB
    const COUNT_LIMIT    = 30;
    const oversize = list.filter(f => f.size > PER_FILE_LIMIT);
    if (oversize.length) {
      alert(window.KNK_t("alert.fileOver500","다음 파일이 500MB 를 초과하여 업로드할 수 없습니다:") + "\n\n"
        + oversize.map(f => `• ${f.name} (${(f.size/1024/1024).toFixed(1)}MB)`).join("\n"));
      return;
    }
    if (list.length > COUNT_LIMIT) {
      alert(window.KNK_t("alert.attachCountLimit","한 번에 최대 {limit}개까지 첨부 가능합니다. (선택: {n}개)").replace("{limit}", COUNT_LIMIT).replace("{n}", list.length));
      return;
    }
    const totalSize = list.reduce((s, f) => s + f.size, 0);
    if (totalSize > TOTAL_LIMIT) {
      alert(window.KNK_t("alert.attachTotalLimit","첨부 합계가 1GB 를 초과합니다 (현재 {mb}MB).").replace("{mb}", (totalSize/1024/1024).toFixed(1)));
      return;
    }
    const parentId = _activeThreadParentId;
    const progBar = document.createElement("div");
    progBar.className = "upload-progress";
    progBar.innerHTML = `<div class="up-name"></div><div class="up-track"><div class="up-fill"></div></div><div class="up-pct">0%</div>`;
    document.body.appendChild(progBar);
    const $name = progBar.querySelector(".up-name");
    const $fill = progBar.querySelector(".up-fill");
    const $pct  = progBar.querySelector(".up-pct");
    const fmtMB = (b) => (b / 1024 / 1024).toFixed(1);
    let idx = 0;
    for (const f of list) {
      idx++;
      $name.textContent = `[${idx}/${list.length}] ${f.name} (${fmtMB(f.size)} MB)`;
      $fill.style.width = "0%";
      $pct.textContent = "0%";
      try {
        const res = await api.upload(activeRoom.id, f, (pct, loaded, total) => {
          $fill.style.width = pct + "%";
          $pct.textContent = `${pct}%  (${fmtMB(loaded)}/${fmtMB(total)} MB)`;
        }, null, parentId);
        if (res && res.error) alert(window.KNK_t("alert.uploadFailFile","업로드 실패: {name}").replace("{name}", f.name) + "\n" + res.error);
      } catch (e) {
        const msg = (e && e.error) || "네트워크 오류 — 연결을 확인해 주세요";
        alert(window.KNK_t("alert.uploadFailFile","업로드 실패: {name}").replace("{name}", f.name) + "\n" + msg);
      }
    }
    progBar.remove();
    // 같은 스레드가 아직 열려 있으면 다시 그려 새 사진 반영 (socket 안전망)
    if (_activeThreadParentId === parentId) await renderThreadPanel(parentId);
  }

  function closeThreadPanel() {
    _activeThreadParentId = null;
    _clearThreadPending();
    const panel = document.getElementById("threadPanel");
    if (panel) panel.classList.remove("open");
  }

  async function renderThreadPanel(parentId) {
    const body = document.getElementById("threadBody");
    if (!body) return;
    body.innerHTML = `<div class="thread-loading">${window.KNK_t("thread.loading", "불러오는 중…")}</div>`;
    let data;
    try {
      data = await fetch(`${BASE}/api/messages/${parentId}/thread`).then(r => r.json());
    } catch (e) {
      body.innerHTML = `<div class="thread-error">${window.KNK_t("thread.loadFail", "스레드 로드 실패")}</div>`;
      return;
    }
    if (data.error) {
      body.innerHTML = `<div class="thread-error">${escapeHtml(data.error)}</div>`;
      return;
    }
    const p = data.parent;
    const replies = data.replies || [];
    // 스레드 메시지 본문 — 사진은 미리보기(클릭 확대), 파일은 받기, 그 외 텍스트 (대표 지시 2026-06-04)
    const _threadMsgBody = (m) => {
      if (m.kind === "image" && m.file_path) {
        return `<a class="thread-img-link" href="${BASE}/uploads/${escapeHtml(m.file_path)}" target="_blank" data-img="1"><img src="${BASE}/uploads/${escapeHtml(m.file_path)}" alt="${escapeHtml(m.file_name || "")}" loading="lazy"></a>`;
      }
      if (m.kind === "file" && m.file_path) {
        const _nm = escapeHtml(m.file_name || "파일");
        const _sz = m.file_size ? ` <span class="thread-file-size">(${(m.file_size/1024).toFixed(0)} KB)</span>` : "";
        return `<div class="thread-file-card"><span class="thread-file-ico">📎</span><span class="thread-file-name">${_nm}</span>${_sz}<a class="thread-file-dl" href="${BASE}/uploads/${escapeHtml(m.file_path)}?dl=1" download="${_nm}">받기</a></div>`;
      }
      return `<div class="thread-msg-content">${escapeHtml(m.content || '').replace(/\n/g,'<br>')}</div>`;
    };
    // 스레드 작성자 메타 — 직급·부서 작은 회색 (대표 지시 2026-05-22)
    //   본사: 숫자코드 없이 / 베트남: '12-VN01 관리팀' → 'VN관리팀'
    const _threadAuthorMeta = (u) => {
      const cached = (Array.isArray(users) ? users.find(x => x.id === u.user_id) : null)
                     || (window._roomMemberMeta && window._roomMemberMeta[u.user_id]) || {};
      const _isG = !!cached.is_guest;
      const _t = cached.title || u.title || "";
      const _d = cached.department || u.department || "";
      const _sd = _isG ? _d : (_d ? (typeof deptShortLabel === "function" ? deptShortLabel(_d) : _d) : "");
      const parts = [];
      if (_t) parts.push(escapeHtml(_t));
      if (_sd) parts.push(escapeHtml(_sd));
      return parts.length ? `<span class="thread-author-meta">${parts.join(" ")}</span>` : "";
    };
    const parentHtml = `
      <div class="thread-parent">
        <div class="thread-msg-row">
          <div class="avatar" style="background:${p.avatar_color || '#3b82f6'}">${_avatarBody(p)}</div>
          <div class="thread-msg-body">
            <div class="thread-msg-author">${escapeHtml(p.display_name)}${_threadAuthorMeta(p)} <span class="thread-msg-time">${fmtTime(p.created_at)}</span></div>
            ${_threadMsgBody(p)}
          </div>
        </div>
      </div>
      <div class="thread-divider">답글 ${replies.length}개</div>
    `;
    const repliesHtml = replies.map(r => `
      <div class="thread-msg-row">
        <div class="avatar" style="background:${r.avatar_color || '#3b82f6'}">${_avatarBody(r)}</div>
        <div class="thread-msg-body">
          <div class="thread-msg-author">${escapeHtml(r.display_name)}${_threadAuthorMeta(r)} <span class="thread-msg-time">${fmtTime(r.created_at)}</span></div>
          ${_threadMsgBody(r)}
        </div>
      </div>
    `).join("");
    body.innerHTML = parentHtml + repliesHtml;
    body.scrollTop = body.scrollHeight;
    // 스레드 사진 클릭 → 라이트박스(확대·줌) — 메인 타임라인과 동일 (대표 지시 2026-06-04)
    body.querySelectorAll("a[data-img='1']").forEach(a => {
      if (a._wired) return;
      a._wired = true;
      a.addEventListener("click", (e) => {
        e.preventDefault();
        const img = a.querySelector("img");
        if (img) _viewImage([{ src: img.src, name: img.alt || "" }], 0, null);
      });
    });
  }

  // ============================================================
  // 🤫 귓속말 (Whisper) — 대화방 안에서 1명에게만 보이는 메시지
  // ============================================================
  let _pendingWhisperUid = null;

  function startWhisperMode(uid, name) {
    if (!activeRoom) {
      alert(window.KNK_t("alert.selectRoomFirst"));
      return;
    }
    _pendingWhisperUid = uid;
    let bar = document.getElementById("whisperPreviewBar");
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "whisperPreviewBar";
      bar.className = "whisper-preview-bar";
      const composerArea = document.getElementById("composerArea");
      const composer = document.getElementById("composer");
      if (composerArea && composer) composerArea.insertBefore(bar, composer);
    }
    bar.innerHTML = `
      <div class="whisper-preview-left">
        <div class="whisper-preview-label">🤫 귓속말 모드 — 이 방에서 ${escapeHtml(name)} 에게만 보임</div>
        <div class="whisper-preview-body">다른 멤버에게는 표시되지 않습니다.</div>
      </div>
      <button type="button" id="whisperCancelBtn" class="quote-cancel-btn" title="귓속말 취소">✕</button>
    `;
    document.getElementById("whisperCancelBtn").addEventListener("click", cancelWhisperMode);
    setTimeout(() => els.msgInput?.focus(), 50);
  }

  function cancelWhisperMode() {
    _pendingWhisperUid = null;
    const bar = document.getElementById("whisperPreviewBar");
    if (bar) bar.remove();
  }

  // ============================================================
  // 인용 답장 (Quote Reply) — 본 채널에 답글 + 원본 미니 카드 표시
  // ============================================================
  let _pendingQuoteMid = null;

  function startQuoteReply(mid, li) {
    _pendingQuoteMid = mid;
    // composer 위에 인용 미리보기 영역 표시
    let prevBar = document.getElementById("quotePreviewBar");
    if (!prevBar) {
      prevBar = document.createElement("div");
      prevBar.id = "quotePreviewBar";
      prevBar.className = "quote-preview-bar";
      const composerArea = document.getElementById("composerArea");
      const composer = document.getElementById("composer");
      if (composerArea && composer) composerArea.insertBefore(prevBar, composer);
    }
    // 원본 메시지 정보 — DOM 에서 추출 (네트워크 호출 없이)
    const author = li.querySelector(".author")?.textContent?.trim()
                || (li.classList.contains("mine") ? "(나)" : "");
    let body = "";
    if (li.classList.contains("image")) body = "[사진]";
    else if (li.classList.contains("file")) {
      const fn = li.querySelector(".file-name")?.textContent?.trim();
      body = fn ? `[파일] ${fn}` : "[파일]";
    } else {
      body = li.querySelector(".bubble")?.textContent?.trim()?.slice(0, 100) || "";
    }
    prevBar.innerHTML = `
      <div class="quote-preview-left">
        <div class="quote-preview-label">↪ 인용 답장</div>
        <div class="quote-preview-author">${escapeHtml(author)}</div>
        <div class="quote-preview-body">${escapeHtml(body)}</div>
      </div>
      <button type="button" id="quoteCancelBtn" class="quote-cancel-btn" title="인용 취소">✕</button>
    `;
    document.getElementById("quoteCancelBtn").addEventListener("click", cancelQuoteReply);
    // 작성창 포커스
    setTimeout(() => els.msgInput?.focus(), 50);
  }

  function cancelQuoteReply() {
    _pendingQuoteMid = null;
    const bar = document.getElementById("quotePreviewBar");
    if (bar) bar.remove();
  }

  // ============================================================
  // 전달(Forward) — 출처 보존 + 방 선택 다이얼로그
  // ============================================================
  let _forwardSourceMid = null;
  let _forwardSelected = new Set();
  let _forwardActiveTab = "all";   // 책갈피: all|item|direct|group|channel (대표 지시 2026-06-06)

  async function openForwardDialog(mid) {
    _forwardSourceMid = mid;
    _forwardSelected = new Set();
    _forwardActiveTab = "all";
    let dlg = document.getElementById("forwardDialog");
    if (!dlg) {
      dlg = document.createElement("div");
      dlg.id = "forwardDialog";
      dlg.className = "modal";
      dlg.setAttribute("data-modal", "");
      dlg.innerHTML = `
        <div class="modal-content">
          <button type="button" class="close-x modal-close-x" data-close>✕</button>
          <h3>↗ 다른 방으로 전달</h3>
          <p class="dialog-hint">원본의 작성자·시각·방 정보가 그대로 보존됩니다.</p>
          <input type="text" id="forwardSearchInput" placeholder="🔍 방 이름 검색" style="width:100%;padding:8px 10px;border:1px solid var(--border);border-radius:6px;margin-bottom:8px;font-size:calc(13px + var(--fs-add-ui));">
          <div id="forwardSelfRow"></div>
          <div id="forwardTabs" class="forward-tabs">
            <button type="button" class="forward-tab active" data-ftab="all">🗂️ 전체</button>
            <button type="button" class="forward-tab" data-ftab="item">🏭 프로젝트</button>
            <button type="button" class="forward-tab" data-ftab="direct">👤 1:1</button>
            <button type="button" class="forward-tab" data-ftab="group">👥 그룹</button>
            <button type="button" class="forward-tab" data-ftab="channel">📢 채널</button>
          </div>
          <div id="forwardRoomList" style="height:240px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;padding:6px;"></div>
          <div style="margin-top:10px;">
            <label style="font-size:calc(12px + var(--fs-add-ui));color:var(--text-soft);display:block;margin-bottom:4px;">코멘트 (선택 — 전달과 함께 보낼 메모)</label>
            <textarea id="forwardComment" rows="2" maxlength="300" placeholder="예: 확인 부탁드립니다" style="width:100%;padding:8px;border:1px solid var(--border);border-radius:6px;font-size:calc(13px + var(--fs-add-ui));resize:vertical;"></textarea>
          </div>
          <div class="dialog-actions">
            <button type="button" data-close>취소</button>
            <button type="button" id="forwardConfirmBtn" class="primary-btn">↗ <span id="forwardCount">0</span>개 방에 전달</button>
          </div>
        </div>
      `;
      document.body.appendChild(dlg);
      // 폴리필 모달 등록
      if (typeof dlg.showModal !== "function") {
        dlg.showModal = function() { dlg.classList.add("open"); document.body.style.overflow = "hidden"; };
        dlg.close = function() { dlg.classList.remove("open"); document.body.style.overflow = ""; };
      }
      // 닫기 버튼
      dlg.querySelectorAll("[data-close]").forEach(b => {
        b.addEventListener("click", () => dlg.close());
      });
      document.getElementById("forwardSearchInput").addEventListener("input", _renderForwardRooms);
      document.getElementById("forwardConfirmBtn").addEventListener("click", _confirmForward);
      // 책갈피 탭 클릭 — 해당 종류만 표시(검색어는 비움) (대표 지시 2026-06-06)
      dlg.querySelectorAll("#forwardTabs .forward-tab").forEach(b => {
        b.addEventListener("click", () => {
          _forwardActiveTab = b.dataset.ftab || "all";
          const si = document.getElementById("forwardSearchInput");
          if (si) si.value = "";
          _renderForwardRooms();
        });
      });
    }
    _renderForwardRooms();
    try { dlg.showModal(); } catch (_) {}
  }

  // 전달 다이얼로그 방 1줄 HTML — 방 목록(renderRooms)과 동일한 아바타 색·국기·뱃지 (대표 지시 2026-05-29)
  function _forwardRowHtml(r, isSelf) {
    isSelf = isSelf || r.type === "self";
    const checked = _forwardSelected.has(r.id) ? "checked" : "";
    const typeLabel = isSelf ? "내메모장"
      : r.type === "item" ? "프로젝트" : r.type === "direct" ? "1:1" : r.type === "channel" ? "채널" : "그룹";
    const color = isSelf ? "#f59e0b"
      : r.type === "item" ? "#16A34A"
      : r.type === "channel" ? "#A5282C"
      : r.type === "group" ? "#7C3AED"
      : (r.avatar_color || "#3b82f6");
    let avatarText = initial(r.name || "?");
    let avatarFlag = false;
    if (isSelf) avatarText = "✏️";
    else if (r.channel_scope === "all") { avatarText = "🌏"; avatarFlag = true; }
    else if (r.channel_scope === "hq")  { avatarText = "🇰🇷"; avatarFlag = true; }
    else if (r.channel_scope === "vn")  { avatarText = "🇻🇳"; avatarFlag = true; }
    const avatarInner = r.avatar_url
      ? `<img class="avatar-img" src="${escapeHtml(r.avatar_url)}" alt="">`
      : escapeHtml(avatarText);
    let typeBadge = "";
    if (r.type === "item") typeBadge = "🏭";
    else if (r.type === "channel") typeBadge = "📢";
    else if (r.type === "group") typeBadge = "👥";
    const badgeHtml = typeBadge ? `<span class="room-type-badge">${typeBadge}</span>` : "";
    const displayName = isSelf ? "내메모장" : (r.name || "(이름없음)");
    const sub = isSelf ? "나만 보는 메모" : (typeLabel + (r.item_customer ? " · " + escapeHtml(r.item_customer) : ""));
    return `
      <label class="forward-room-row${isSelf ? ' forward-self-row' : ''}" style="display:flex;align-items:center;gap:8px;padding:8px;border-radius:6px;cursor:pointer;">
        <input type="checkbox" data-rid="${r.id}" ${checked}>
        <span class="room-avatar-wrap">
          <div class="avatar${avatarFlag ? ' room-flag-avatar' : ''}" style="width:29px;height:29px;font-size:calc(13px + var(--fs-add-ui));background:${color}">${avatarInner}</div>${badgeHtml}
        </span>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:600;font-size:calc(13px + var(--fs-add-ui));color:var(--text);">${escapeHtml(displayName)}</div>
          <div style="font-size:calc(11px + var(--fs-add-ui));color:var(--text-soft);">${sub}</div>
        </div>
      </label>
    `;
  }

  function _bindForwardCheckboxes(container) {
    if (!container) return;
    container.querySelectorAll("input[type=checkbox]").forEach(cb => {
      cb.addEventListener("change", () => {
        const rid = parseInt(cb.dataset.rid, 10);
        if (cb.checked) _forwardSelected.add(rid);
        else _forwardSelected.delete(rid);
        const _c = document.getElementById("forwardCount");
        if (_c) _c.textContent = _forwardSelected.size;
      });
    });
  }

  function _renderForwardRooms() {
    const list = document.getElementById("forwardRoomList");
    const selfWrap = document.getElementById("forwardSelfRow");
    const q = (document.getElementById("forwardSearchInput")?.value || "").trim().toLowerCase();

    // 책갈피 탭 active 표시
    document.querySelectorAll("#forwardTabs .forward-tab").forEach(b => {
      b.classList.toggle("active", (b.dataset.ftab || "all") === _forwardActiveTab);
    });

    // 내메모장(self) — 탭/검색과 무관하게 항상 상단 고정 (대표 지시 2026-06-06)
    const selfRoom = (rooms || []).find(r => r.type === "self");
    if (selfWrap) selfWrap.innerHTML = selfRoom ? _forwardRowHtml(selfRoom, true) : "";

    // 나머지 방: 검색어 있으면 탭 무관 전체 이름검색, 없으면 활성 책갈피로 필터
    const candidates = (rooms || []).filter(r => {
      if (r.type === "self") return false;   // 내메모장은 위에 고정
      if (q) return (r.name || "").toLowerCase().includes(q);
      if (_forwardActiveTab === "all") return true;
      return r.type === _forwardActiveTab;
    });
    if (!candidates.length) {
      list.innerHTML = `<div style="padding:20px;text-align:center;color:var(--text-soft);font-size:calc(13px + var(--fs-add-ui));">${q ? "검색 결과가 없습니다." : "이 분류에 방이 없습니다."}</div>`;
    } else {
      list.innerHTML = candidates.map(r => _forwardRowHtml(r, false)).join("");
    }

    _bindForwardCheckboxes(selfWrap);
    _bindForwardCheckboxes(list);
    const _cnt = document.getElementById("forwardCount");
    if (_cnt) _cnt.textContent = _forwardSelected.size;
  }

  async function _confirmForward() {
    if (!_forwardSourceMid || _forwardSelected.size === 0) {
      alert(window.KNK_t("alert.forwardPickRoom"));
      return;
    }
    const comment = (document.getElementById("forwardComment")?.value || "").trim();
    const btn = document.getElementById("forwardConfirmBtn");
    // textContent 로 글자를 바꾸면 버튼 안의 <span id="forwardCount"> 요소가 통째로 사라져,
    // 다음번에 전달 창을 열 때 _renderForwardRooms 가 그 span 을 찾다 에러나며 창이 안 열림.
    // → innerHTML 통째로 저장/복원해서 span 요소까지 원래대로 되돌린다 (2026-06-01 버그수정).
    const prevHTML = btn.innerHTML;
    btn.disabled = true;
    btn.textContent = "전달 중…";
    try {
      const res = await fetch(`${BASE}/api/messages/${_forwardSourceMid}/forward`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          to_room_ids: Array.from(_forwardSelected),
          add_comment: comment,
        }),
      }).then(r => r.json());
      if (res.error) {
        alert(`❌ ${res.error}`);
        return;
      }
      const dlg = document.getElementById("forwardDialog");
      if (dlg) dlg.close();
      alert(window.KNK_t("alert.forwardDone","✅ {n}개 방으로 전달 완료").replace("{n}", res.count));
    } catch (e) {
      alert(window.KNK_t("alert.networkError"));
    } finally {
      btn.disabled = false;
      btn.innerHTML = prevHTML;   // span#forwardCount 포함 원래 버튼 내용 복원
    }
  }

  function wireMessageActions() {
    // 이미지 우클릭 시 크롬 기본 메뉴 차단 — 메시지 컨텍스트 메뉴 강제 표시 (대표 지시 2026-05-19)
    els.messages.querySelectorAll(".msg img, .album-grid img, .image-wrap img").forEach(img => {
      if (img._noCtx) return;
      img._noCtx = true;
      img.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        e.stopPropagation();
        // 우클릭한 이미지가 속한 메시지의 컨텍스트 메뉴 띄움
        const li = img.closest(".msg");
        if (li) showMessageContextMenu(li, e.clientX, e.clientY);
        return false;
      });
      // 드래그 시 브라우저 기본 동작 (이미지 드래그) 도 일관성 위해 차단
      img.addEventListener("dragstart", (e) => e.preventDefault());
    });
    // 읽음/안읽음 배지 클릭 — 명단 다이얼로그 (대표 지시 2026-05-19)
    els.messages.querySelectorAll(".read-badge.clickable").forEach(el => {
      if (el._wired) return;
      el._wired = true;
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        const mid = parseInt(el.dataset.readStatusMid, 10);
        if (mid) openReadStatusDialog(mid);
      });
    });
    els.messages.querySelectorAll(".msg-action-btn[data-act='request']").forEach(b => {
      if (b._wired) return;
      b._wired = true;
      b.addEventListener("click", (e) => {
        e.stopPropagation();
        const li = b.closest(".msg");
        const mid = parseInt(li.dataset.msgId, 10);
        let content;
        if (li.classList.contains("image")) {
          const fname = li.querySelector("img")?.alt || "사진";
          content = `[사진] ${fname}`;
        } else if (li.classList.contains("file")) {
          const fname = li.querySelector(".file-name")?.textContent?.trim() || "파일";
          content = `[파일] ${fname}`;
        } else {
          content = li.querySelector(".bubble")?.textContent?.trim() || "";
        }
        openNewRequest({ messageId: mid, sourceContent: content });
      });
    });
    els.messages.querySelectorAll(".msg-action-btn[data-act='rx']").forEach(b => {
      if (b._wired) return;
      b._wired = true;
      b.addEventListener("click", async (e) => {
        e.stopPropagation();
        const li = b.closest(".msg");
        const mid = parseInt(li.dataset.msgId, 10);
        await fetch(`${BASE}/api/messages/${mid}/react`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ emoji: b.dataset.emoji }),
        });
      });
    });
    // 토글: 이미 단 반응 칩 클릭 시 제거 (서버 토글)
    els.messages.querySelectorAll(".rx-chip").forEach(c => {
      if (c._wired) return;
      c._wired = true;
      c.addEventListener("click", async (e) => {
        e.stopPropagation();
        const li = c.closest(".msg");
        const mid = parseInt(li.dataset.msgId, 10);
        await fetch(`${BASE}/api/messages/${mid}/react`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ emoji: c.dataset.emoji }),
        });
      });
    });

    // 전달확인 (ack)
    els.messages.querySelectorAll(".ack-btn").forEach(b => {
      if (b._wired) return;
      b._wired = true;
      b.addEventListener("click", async (e) => {
        e.stopPropagation();
        const li = b.closest(".msg");
        const mid = parseInt(li.dataset.msgId, 10);
        await fetch(`${BASE}/api/messages/${mid}/ack`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ack_type: "ok" }),
        });
      });
    });

    // 별표 (중요 결정 마킹)
    els.messages.querySelectorAll("[data-act='star']").forEach(b => {
      if (b._wired) return;
      b._wired = true;
      b.addEventListener("click", async (e) => {
        e.stopPropagation();
        const li = b.closest(".msg");
        const mid = parseInt(li.dataset.msgId, 10);
        const r = await fetch(`${BASE}/api/messages/${mid}/star`, { method: "POST" }).then(x => x.json());
        if (r.action === "added") {
          li.classList.add("starred");
          b.classList.add("starred");
          b.textContent = "★";
        } else {
          li.classList.remove("starred");
          b.classList.remove("starred");
          b.textContent = "☆";
        }
      });
    });

    // 파일 버전 배지 클릭 → 버전 목록 다이얼로그
    els.messages.querySelectorAll(".ver-badge").forEach(b => {
      if (b._wired) return;
      b._wired = true;
      b.addEventListener("click", async (e) => {
        e.stopPropagation();
        e.preventDefault();
        const li = b.closest(".msg");
        const mid = parseInt(li.dataset.msgId, 10);
        await showVersionsDialog(mid);
      });
    });

    // 여러 방 공유 배지(글쓴이) 클릭 → 공유된 방 목록 팝업 (대표 지시 2026-06-04)
    els.messages.querySelectorAll(".share-card[data-act='share-targets']").forEach(b => {
      if (b._wired) return;
      b._wired = true;
      b.addEventListener("click", async (e) => {
        e.stopPropagation();
        e.preventDefault();
        const li = b.closest(".msg");
        const mid = parseInt(li.dataset.msgId, 10);
        if (mid) await showShareTargets(mid);
      });
    });

    // 번역 버튼 (🌐) — 언어 선택 popup → 번역 호출 → 메시지 갱신
    els.messages.querySelectorAll("[data-act='translate']").forEach(b => {
      if (b._wired) return;
      b._wired = true;
      b.addEventListener("click", async (e) => {
        e.stopPropagation();
        const li = b.closest(".msg");
        const mid = parseInt(li.dataset.msgId, 10);
        await openTranslateMenu(b, mid);
      });
    });

    // 스레드 답글 배지 클릭 → 스레드 패널 열기
    els.messages.querySelectorAll("[data-act='open_thread']").forEach(b => {
      if (b._wired) return;
      b._wired = true;
      b.addEventListener("click", (e) => {
        e.stopPropagation();
        const li = b.closest(".msg");
        const mid = parseInt(li.dataset.msgId, 10);
        if (mid) openThreadPanel(mid);
      });
    });

    // 작성자 이름 우클릭/롱프레스 → 사용자 컨텍스트 메뉴 (귓속말 옵션 포함)
    els.messages.querySelectorAll(".author[data-uid]").forEach(authorEl => {
      if (authorEl._userCtxWired) return;
      authorEl._userCtxWired = true;
      authorEl.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const uid = parseInt(authorEl.dataset.uid, 10);
        if (uid) showUserContextMenu(uid, e.clientX, e.clientY);
      });
      // 모바일 롱프레스 (650ms — iOS 시스템 콜아웃 500ms 보다 길게 + CSS 차단 병행)
      let _pt = null, _pxy = { x: 0, y: 0 };
      authorEl.addEventListener("touchstart", (e) => {
        e.stopPropagation();   // 메시지 li 의 long-press 핸들러로 버블 안 가게
        const t = e.touches[0];
        _pxy = { x: t.clientX, y: t.clientY };
        authorEl.classList.add("author-pressing");
        _pt = setTimeout(() => {
          _pt = null;
          authorEl.classList.remove("author-pressing");
          if (navigator.vibrate) try { navigator.vibrate(40); } catch (_) {}
          const uid = parseInt(authorEl.dataset.uid, 10);
          if (uid) showUserContextMenu(uid, _pxy.x, _pxy.y);
        }, 650);
      }, { passive: true });
      authorEl.addEventListener("touchmove", (e) => {
        const t = e.touches[0];
        if (Math.abs(t.clientX - _pxy.x) > 10 || Math.abs(t.clientY - _pxy.y) > 10) {
          if (_pt) { clearTimeout(_pt); _pt = null; }
          authorEl.classList.remove("author-pressing");
        }
      }, { passive: true });
      const _endPress = () => {
        if (_pt) { clearTimeout(_pt); _pt = null; }
        authorEl.classList.remove("author-pressing");
      };
      authorEl.addEventListener("touchend", _endPress, { passive: true });
      authorEl.addEventListener("touchcancel", _endPress, { passive: true });
    });

    // 인용 카드 클릭 → 원본 메시지로 스크롤 + 강조
    els.messages.querySelectorAll(".quote-card[data-quote-mid]").forEach(card => {
      if (card._wired) return;
      card._wired = true;
      card.addEventListener("click", (e) => {
        e.stopPropagation();
        const qid = parseInt(card.dataset.quoteMid, 10);
        const target = els.messages.querySelector(`.msg[data-msg-id="${qid}"]`);
        if (target) {
          target.scrollIntoView({ behavior: "smooth", block: "center" });
          target.classList.add("highlight-flash");
          setTimeout(() => target.classList.remove("highlight-flash"), 1500);
        } else {
          // 원본이 화면 밖 (스크롤 위쪽) 인 경우 — 별도 처리 없이 안내
          alert(window.KNK_t("alert.originNotInRange","원본 메시지가 현재 보이는 범위에 없습니다. 위로 스크롤해 주세요."));
        }
      });
    });
    // 모바일에서 메시지 버블 탭하면 액션바 토글
    wireMessageTapToggle();


    // ─── 우클릭/long-press 컨텍스트 메뉴 ───
    // 선택(드래그)이 해제되면 선택모드 클래스도 정리 → 다음 길게누름은 다시 앱 메뉴부터 (대표 지시 2026-05-23)
    if (!window._lpSelectionWired) {
      window._lpSelectionWired = true;
      document.addEventListener("selectionchange", () => {
        const s = window.getSelection();
        if (!s || s.isCollapsed) {
          document.querySelectorAll(".messages .msg .bubble.lp-selectable").forEach(b => b.classList.remove("lp-selectable"));
        }
      });
    }
    els.messages.querySelectorAll(".msg").forEach(li => {
      if (li._ctxWired) return;
      li._ctxWired = true;
      // 데스크톱: 우클릭
      li.addEventListener("contextmenu", (e) => {
        // 링크·input·textarea·작성자 이름 위에서는 메시지 메뉴 스킵
        // (.author 는 자체 사용자 컨텍스트 메뉴 — 귓속말 등)
        if (e.target.closest("a, input, textarea, .it-close, button.rx-chip, .author")) return;
        // ★ 이미지 위에서 우클릭 — 크롬 기본 메뉴 차단 + 메시지 컨텍스트 메뉴 표시 (대표 지시 2026-05-19)
        e.preventDefault();
        showMessageContextMenu(li, e.clientX, e.clientY);
      });
      // 모바일 long-press 2단계 (대표 지시 2026-05-23):
      //  0.6초 = 앱 컨텍스트 메뉴 / 계속 더 길게(1.3초) = 브라우저 기본 텍스트 선택(부분 복사·번역).
      //  말풍선은 평소 user-select:none → 기본 복사 메뉴가 앱 메뉴보다 먼저 뜨는 충돌 방지.
      let touchTimer = null;
      let selectTimer = null;
      let touchStartXY = null;
      li.addEventListener("touchstart", (e) => {
        // .author 는 자체 long-press 로 사용자 메뉴 (귓속말·정보 등)
        if (e.target.closest("a, button, input, textarea, .author")) return;
        const bub = li.querySelector(".bubble");
        // 이미 선택모드인 말풍선이면 — 네이티브 선택 핸들 조작 중이므로 간섭하지 않음
        if (bub && bub.classList.contains("lp-selectable")) return;
        // 새 누름 시작 — 이전 선택모드/선택 해제
        try {
          document.querySelectorAll(".messages .msg .bubble.lp-selectable").forEach(b => b.classList.remove("lp-selectable"));
          const s0 = window.getSelection(); if (s0 && !s0.isCollapsed) s0.removeAllRanges();
        } catch (_) {}
        const t = e.touches[0];
        touchStartXY = { x: t.clientX, y: t.clientY };
        li.classList.add("long-pressing");
        // 1단계 (0.6초): 앱 컨텍스트 메뉴
        touchTimer = setTimeout(() => {
          touchTimer = null;
          li.classList.remove("long-pressing");
          // 햅틱 — Android vibrate. iOS 는 vibrate 미지원이라 long-press 시각 효과(scale)로만 피드백.
          if (navigator.vibrate) try { navigator.vibrate(40); } catch (_) {}
          showMessageContextMenu(li, touchStartXY.x, touchStartXY.y);
        }, 600);
        // 2단계 (1.3초): 계속 누르고 있으면 브라우저 기본 텍스트 선택으로 전환 (부분 복사·번역)
        const isText = !li.classList.contains("image") && !li.classList.contains("file") && !li.classList.contains("system");
        if (isText && bub) {
          selectTimer = setTimeout(() => {
            selectTimer = null;
            if (touchTimer) { clearTimeout(touchTimer); touchTimer = null; }
            try { closeMessageContextMenu(); } catch (_) {}
            li.classList.remove("long-pressing");
            bub.classList.add("lp-selectable");
            try {
              const sel = window.getSelection();
              sel.removeAllRanges();
              const range = document.createRange();
              range.selectNodeContents(bub);
              sel.addRange(range);
            } catch (_) {}
            if (navigator.vibrate) try { navigator.vibrate([15, 35, 15]); } catch (_) {}
          }, 1300);
        }
      }, { passive: true });
      const cancelLongPress = () => {
        if (touchTimer) { clearTimeout(touchTimer); touchTimer = null; }
        if (selectTimer) { clearTimeout(selectTimer); selectTimer = null; }
        li.classList.remove("long-pressing");
      };
      li.addEventListener("touchend", cancelLongPress, { passive: true });
      li.addEventListener("touchcancel", cancelLongPress, { passive: true });
      li.addEventListener("touchmove", (e) => {
        if (!touchStartXY || (!touchTimer && !selectTimer)) return;
        const t = e.touches[0];
        const dx = Math.abs(t.clientX - touchStartXY.x);
        const dy = Math.abs(t.clientY - touchStartXY.y);
        if (dx > 10 || dy > 10) cancelLongPress();
      }, { passive: true });
    });

    els.messages.querySelectorAll("a[data-img='1']").forEach(a => {
      if (a._wired) return;
      a._wired = true;
      a.addEventListener("click", (e) => {
        e.preventDefault();
        // 앨범 li 안의 타일이면 같은 앨범의 사진들을 모두 묶어서 라이트박스에 전달.
        // 사용자는 좌우 화살표/키보드로 같은 앨범 내 다른 사진을 넘겨볼 수 있다.
        const albumLi = a.closest("li.msg.album[data-album-id]");
        if (albumLi) {
          const albumId = albumLi.getAttribute("data-album-id");
          const tiles = Array.from(albumLi.querySelectorAll("a.album-tile"));
          const items = tiles.map(t => {
            const img = t.querySelector("img");
            return {
              src: img.src,
              name: img.alt || "",
              message_id: t.dataset.msgId || null,
            };
          });
          const startIdx = Math.max(0, tiles.indexOf(a));
          _viewImage(items, startIdx, albumId);
        } else {
          // 단일 사진
          const img = a.querySelector("img");
          _viewImage([{ src: img.src, name: img.alt || "" }], 0, null);
        }
      });
    });
  }

  // ---------- 라이트박스 상태 + 조작 ----------
  const _lb = { items: [], index: 0, albumId: null };
  // 모바일 뒤로가기로 미리보기 닫기 — 컨텍스트 메뉴와 동일 패턴 (대표 지시 2026-06-01)
  //   열 때 history 한 칸 push → 뒤로가기(popstate)면 미리보기만 닫힘(방 유지),
  //   X·배경탭·ESC 로 닫으면 history.back 으로 그 한 칸을 정리.
  let _lbStatePushed = false;   // 미리보기 열 때 history 상태를 넣었는지
  let _lbIgnorePop = false;     // 수동 닫기로 우리가 history.back 한 popstate 는 무시
  let _lbClosingFromPop = false; // popstate(뒤로가기)로 닫는 중 — close() 가 history.back 추가호출 안 하도록

  // ── 사진 '별도 새 창' 뷰어 (PC) — 카톡처럼 사진 보면서 메신저 동시 사용 (대표 지시 2026-06-05) ──
  //    PC(마우스)면 새 창 뷰어, 휴대폰(터치)이면 기존 전체화면 미리보기(라이트박스) 유지.
  function _imgUseWindow() {
    try { return !window.matchMedia("(pointer: coarse)").matches; } catch (e) { return true; }
  }
  function _imgWinFeatures() {
    var w = 920, h = 720;
    var bx = (typeof window.screenX === "number" ? window.screenX : (window.screenLeft || 0));
    var by = (typeof window.screenY === "number" ? window.screenY : (window.screenTop || 0));
    var ow = window.outerWidth || 1200;
    var sw = (window.screen && window.screen.availWidth) || 1920;
    var left = Math.max(0, Math.min(sw - w, bx + ow - 60));   // 메신저 오른쪽 옆에 띄우기
    var top = Math.max(0, by + 40);
    return "width=" + w + ",height=" + h + ",left=" + left + ",top=" + top +
           ",resizable=yes,scrollbars=yes,menubar=no,toolbar=no,location=no,status=no";
  }
  function _imgViewerHtml(payload) {
    return `<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>사진</title>
<style>
*{margin:0;box-sizing:border-box}
html,body{height:100%;background:#1b1b1d;overflow:hidden;font-family:'Malgun Gothic','맑은 고딕',sans-serif}
#bar{height:46px;display:flex;align-items:center;gap:2px;padding:0 10px;background:#2a2a2e;color:#eaeaec;border-bottom:1px solid #111}
#fn{flex:1;font-size:13px;color:#cfcfd2;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-right:8px}
#bar button{background:transparent;border:0;color:#dcdce0;width:34px;height:34px;border-radius:7px;cursor:pointer;font-size:18px;line-height:1;display:flex;align-items:center;justify-content:center}
#bar button:hover{background:rgba(255,255,255,.13)}
#nav{font-size:12px;color:#9a9aa0;min-width:50px;text-align:center}
#stage{position:absolute;top:46px;left:0;right:0;bottom:0;overflow:auto;display:flex;align-items:center;justify-content:center}
#stage.zoom{display:block}
#img{display:block;-webkit-user-drag:none;user-select:none}
#stage:not(.zoom) #img{max-width:100%;max-height:100%;margin:auto}
#stage.grab{cursor:grab}#stage.grabbing{cursor:grabbing}
.sep{width:1px;height:22px;background:#444;margin:0 4px}
</style></head><body>
<div id="bar">
<span id="fn"></span>
<button id="prev" title="이전 (←)">‹</button><span id="nav"></span><button id="next" title="다음 (→)">›</button>
<span class="sep"></span>
<button id="zo" title="축소 (−)">−</button><button id="zi" title="확대 (+)">＋</button><button id="fit" title="화면맞춤 (0)">⤢</button>
<span class="sep"></span>
<button id="dl" title="저장">⤓</button><button id="cl" title="닫기 (Esc)">✕</button>
</div>
<div id="stage" class="grab"><img id="img" alt=""></div>
<script>
var DATA=${payload};
var i=DATA.index||0,scale=0,fitMode=true;
var stage=document.getElementById('stage'),img=document.getElementById('img'),fn=document.getElementById('fn'),nav=document.getElementById('nav');
function cur(){return DATA.items[i];}
function applyFit(){fitMode=true;scale=0;stage.classList.remove('zoom');img.style.width='';img.style.height='';}
function applyScale(s){fitMode=false;scale=s;stage.classList.add('zoom');img.style.width=(img.naturalWidth*s)+'px';img.style.height='auto';}
function show(){var c=cur();img.src=c.src;fn.textContent=c.name||'사진';document.title=c.name||'사진';var multi=DATA.items.length>1;nav.textContent=multi?((i+1)+' / '+DATA.items.length):'';document.getElementById('prev').style.display=document.getElementById('next').style.display=multi?'':'none';applyFit();}
img.addEventListener('load',function(){if(!fitMode)applyScale(scale);});
function zoom(dir){var base=scale>0?scale:((img.clientWidth/img.naturalWidth)||1);applyScale(Math.min(8,Math.max(0.1,base*(dir>0?1.25:0.8))));}
document.getElementById('zi').onclick=function(){zoom(1);};
document.getElementById('zo').onclick=function(){zoom(-1);};
document.getElementById('fit').onclick=function(){applyFit();};
document.getElementById('prev').onclick=function(){if(DATA.items.length>1){i=(i-1+DATA.items.length)%DATA.items.length;show();}};
document.getElementById('next').onclick=function(){if(DATA.items.length>1){i=(i+1)%DATA.items.length;show();}};
document.getElementById('cl').onclick=function(){window.close();};
document.getElementById('dl').onclick=function(){var c=cur();var a=document.createElement('a');a.href=c.src+(c.src.indexOf('?')<0?'?dl=1':'&dl=1');a.download=c.name||'';document.body.appendChild(a);a.click();a.remove();};
img.addEventListener('click',function(){if(fitMode)applyScale(1);else applyFit();});
stage.addEventListener('wheel',function(e){e.preventDefault();zoom(e.deltaY<0?1:-1);},{passive:false});
var dg=false,sx,sy,sl,st;
stage.addEventListener('mousedown',function(e){if(fitMode)return;dg=true;sx=e.clientX;sy=e.clientY;sl=stage.scrollLeft;st=stage.scrollTop;stage.classList.add('grabbing');e.preventDefault();});
window.addEventListener('mousemove',function(e){if(!dg)return;stage.scrollLeft=sl-(e.clientX-sx);stage.scrollTop=st-(e.clientY-sy);});
window.addEventListener('mouseup',function(){dg=false;stage.classList.remove('grabbing');});
window.addEventListener('keydown',function(e){if(e.key==='Escape')window.close();else if(e.key==='+'||e.key==='=')zoom(1);else if(e.key==='-')zoom(-1);else if(e.key==='0')applyFit();else if(e.key==='ArrowLeft')document.getElementById('prev').click();else if(e.key==='ArrowRight')document.getElementById('next').click();});
show();
</script></body></html>`;
  }
  function _openImageViewer(items, startIndex, albumId) {
    try {
      const w = window.open("", "knk_img_viewer", _imgWinFeatures());
      if (!w) { openLightbox(items, startIndex, albumId); return; }   // 팝업 차단 시 폴백
      const payload = JSON.stringify({ items: items, index: Math.max(0, Math.min(startIndex || 0, items.length - 1)) }).replace(/</g, "\\u003c");
      w.document.open(); w.document.write(_imgViewerHtml(payload)); w.document.close();
      try { w.focus(); } catch (e) {}
    } catch (e) { openLightbox(items, startIndex, albumId); }
  }
  // 사진 열기 진입점 — PC면 새 창 뷰어, 모바일이면 라이트박스
  function _viewImage(items, startIndex, albumId) {
    if (_imgUseWindow()) _openImageViewer(items, startIndex, albumId);
    else openLightbox(items, startIndex, albumId);
  }

  // ── 외부 앱 공유 (카톡 등) — 휴대폰=OS 공유시트 / PC=복사·다운로드 (대표 지시 2026-06-05) ──
  function _toast(msg) {
    try {
      let t = document.getElementById("knkToast");
      if (!t) { t = document.createElement("div"); t.id = "knkToast"; t.className = "knk-toast"; document.body.appendChild(t); }
      t.textContent = msg;
      t.classList.add("show");
      clearTimeout(t._hideT);
      t._hideT = setTimeout(function () { t.classList.remove("show"); }, 2800);
    } catch (e) {}
  }
  function _downloadUrl(url, name) {
    try { const a = document.createElement("a"); a.href = url; a.download = name || ""; document.body.appendChild(a); a.click(); a.remove(); } catch (e) {}
  }
  function _blobToPngBlob(blob) {
    return new Promise(function (resolve) {
      try {
        const url = URL.createObjectURL(blob);
        const im = new Image();
        im.onload = function () {
          try {
            const c = document.createElement("canvas");
            c.width = im.naturalWidth; c.height = im.naturalHeight;
            c.getContext("2d").drawImage(im, 0, 0);
            c.toBlob(function (b) { URL.revokeObjectURL(url); resolve(b); }, "image/png");
          } catch (e) { URL.revokeObjectURL(url); resolve(null); }
        };
        im.onerror = function () { URL.revokeObjectURL(url); resolve(null); };
        im.src = url;
      } catch (e) { resolve(null); }
    });
  }
  async function _copyImageToClipboard(blob) {
    try {
      if (!navigator.clipboard || !window.ClipboardItem) return false;
      let out = blob;
      if (!blob.type || blob.type !== "image/png") { out = await _blobToPngBlob(blob); }
      if (!out) return false;
      await navigator.clipboard.write([new ClipboardItem({ "image/png": out })]);
      return true;
    } catch (e) { return false; }
  }
  function _isTouchDevice() {
    try { return window.matchMedia("(pointer: coarse)").matches; } catch (e) { return false; }
  }
  function _shareFileName(name, mime, defExt) {
    let n = ((name || "").trim()) || "file";
    if (n.indexOf(".") < 0) {
      let ext = defExt || "";
      if (mime && mime.indexOf("/") > 0) ext = mime.split("/")[1].split("+")[0];
      if (ext) n = n + "." + ext;
    }
    return n;
  }
  // 메시지(사진·파일·글)를 외부 앱으로 공유 — 기기별 최선
  async function _shareMessageExternal(li) {
    try {
      const isImg = li.classList.contains("image");
      const isFile = li.classList.contains("file");
      const mobile = _isTouchDevice();
      if (isImg) {
        const imgEl = li.querySelector("img");
        const aEl = li.querySelector("a[data-img]");
        const url = (aEl && aEl.getAttribute("href")) || (imgEl && imgEl.src);
        const name = (imgEl && imgEl.getAttribute("alt")) || "photo.jpg";
        if (!url) { _toast(_kt("share.noPhoto", "공유할 사진을 찾지 못했습니다")); return; }
        const blob = await fetch(url).then(function (r) { return r.blob(); });
        if (mobile && navigator.canShare) {
          const f = new File([blob], _shareFileName(name, blob.type, "png"), { type: blob.type || "image/png" });
          if (navigator.canShare({ files: [f] })) { await navigator.share({ files: [f] }); return; }
        }
        if (await _copyImageToClipboard(blob)) { _toast(_kt("share.imgCopied", "이미지를 복사했어요 — 카톡 등에서 Ctrl+V 로 붙여넣으세요")); return; }
        _downloadUrl(url + (url.indexOf("?") < 0 ? "?dl=1" : "&dl=1"), name);
        _toast(_kt("share.imgSaved", "사진을 받았어요 — 카톡 등에 첨부하세요"));
      } else if (isFile) {
        const fa = li.querySelector(".file-link");
        const url = fa && fa.getAttribute("href");
        const nameEl = li.querySelector(".file-name");
        const name = (nameEl && nameEl.textContent.trim()) || "file";
        if (!url) { _toast(_kt("share.noFile", "공유할 파일을 찾지 못했습니다")); return; }
        if (mobile && navigator.canShare) {
          try {
            const blob = await fetch(url).then(function (r) { return r.blob(); });
            const f = new File([blob], name, { type: blob.type || "application/octet-stream" });
            if (navigator.canShare({ files: [f] })) { await navigator.share({ files: [f] }); return; }
          } catch (e) {}
        }
        _downloadUrl(url, name);
        _toast(_kt("share.fileSaved", "파일을 받았어요 — 카톡 등에 첨부하세요"));
      } else {
        const bub = li.querySelector(".bubble");
        const text = (bub && bub.textContent.trim()) || "";
        if (!text) { _toast(_kt("share.noText", "공유할 내용이 없습니다")); return; }
        if (mobile && navigator.share) {
          try { await navigator.share({ text: text }); return; } catch (e) { if (e && e.name === "AbortError") return; }
        }
        try { await navigator.clipboard.writeText(text); _toast(_kt("share.textCopied", "내용을 복사했어요 — 카톡 등에 Ctrl+V 로 붙여넣으세요")); }
        catch (e) { _toast(_kt("share.copyFail", "복사 실패 — 메시지를 길게 눌러 직접 복사해 주세요")); }
      }
    } catch (e) {
      if (e && e.name === "AbortError") return;   // 사용자가 공유를 취소
      _toast(_kt("share.shareFail", "공유 실패") + ": " + ((e && e.message) || e));
    }
  }

  function openLightbox(items, startIndex, albumId) {
    if (!items || !items.length) return;
    _lb.items = items;
    _lb.index = Math.max(0, Math.min(startIndex || 0, items.length - 1));
    _lb.albumId = albumId || null;

    const isMulti = items.length > 1;
    const prev = document.getElementById("lbPrev");
    const next = document.getElementById("lbNext");
    const saveAll = document.getElementById("lbSaveAll");
    if (prev) prev.hidden = !isMulti;
    if (next) next.hidden = !isMulti;
    if (saveAll) saveAll.hidden = !albumId;

    renderLightboxItem();
    els.lightbox.showModal();
    // 모바일 뒤로가기로 닫을 수 있게 history 한 칸 추가 (열려 있는 동안 1칸만)
    if (!_lbStatePushed) {
      try { history.pushState({ knkLightbox: true }, ""); _lbStatePushed = true; } catch (e) {}
    }
    setupLightboxZoom();   // 최초 1회만 wire-up. 이후 무시. (대표 지시 2026-05-27)
  }

  function renderLightboxItem() {
    const item = _lb.items[_lb.index];
    if (!item) return;
    els.lightboxImg.src = item.src;
    els.lightboxImg.alt = item.name || "";
    els.lightboxMeta.textContent = item.name || "";
    const counter = document.getElementById("lbCounter");
    if (counter) counter.textContent = `${_lb.index + 1} / ${_lb.items.length}`;
    // 이미지 전환 시 줌 리셋 (대표 지시 2026-05-27)
    if (typeof _lbZoomReset === "function") _lbZoomReset();
    // 라이트박스 이미지 우클릭 시 크롬 메뉴 차단 (대표 지시 2026-05-19)
    if (!els.lightboxImg._noCtx) {
      els.lightboxImg._noCtx = true;
      els.lightboxImg.addEventListener("contextmenu", (e) => e.preventDefault());
      els.lightboxImg.addEventListener("dragstart", (e) => e.preventDefault());
    }
  }

  function lbNav(dir) {
    if (_lb.items.length < 2) return;
    _lb.index = (_lb.index + dir + _lb.items.length) % _lb.items.length;
    renderLightboxItem();
  }

  // 단일 사진 저장 — 같은 origin 이라 anchor download 가능
  function lbSaveCurrent() {
    const item = _lb.items[_lb.index];
    if (!item) return;
    const a = document.createElement("a");
    // ?dl=1 — 서버가 원본 파일명으로 Content-Disposition 지정(휴대폰에서 a.download 무시 대비). (대표 지시 2026-06-02)
    a.href = item.src + (item.src.indexOf("?") >= 0 ? "&" : "?") + "dl=1";
    a.download = item.name || "image.jpg";
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    setTimeout(() => a.remove(), 100);
  }

  // 앨범 전체 ZIP 저장 — 서버가 /api/albums/<id>/zip 으로 zip 생성해서 다운로드
  function lbSaveAlbum() {
    if (!_lb.albumId) return;
    const url = `${BASE}/api/albums/${encodeURIComponent(_lb.albumId)}/zip`;
    // 같은 탭의 location 변경 = 다운로드. 새 탭으로 띄울 필요 없음
    // (location.href = url 도 OK, 더 호환성 좋게 anchor 사용)
    const a = document.createElement("a");
    a.href = url;
    a.download = "";   // 서버가 Content-Disposition 으로 파일명 지정
    document.body.appendChild(a);
    a.click();
    setTimeout(() => a.remove(), 100);
  }

  // ===== 라이트박스 확대·축소 (대표 지시 2026-05-27) =====
  //   PC: 마우스 휠 줌 + 드래그 팬 + 더블클릭 토글
  //   모바일: 핀치 줌 + 드래그 팬 + 더블탭 토글
  //   이미지 전환·닫기 시 자동 리셋. scale=1 일 때는 기존 스와이프(좌우 nav) 그대로 작동.
  const _lbZoom = { scale: 1, tx: 0, ty: 0, min: 1, max: 5, step: 1.25 };
  let _lbZoomWired = false;
  let _lbDrag = null;     // { startX, startY, tx0, ty0 }
  let _lbPinch = null;    // { startDist, startScale, midX, midY }
  let _lbLastTap = 0;     // 더블탭 감지

  function _lbApply(smooth) {
    if (!els.lightboxImg) return;
    const img = els.lightboxImg;
    if (smooth) img.classList.add("smooth");
    else img.classList.remove("smooth");
    img.style.transform = `translate(${_lbZoom.tx}px, ${_lbZoom.ty}px) scale(${_lbZoom.scale})`;
    img.classList.toggle("zoomed", _lbZoom.scale > 1.001);
    const lvl = document.getElementById("lbZoomLevel");
    if (lvl) lvl.textContent = `${Math.round(_lbZoom.scale * 100)}%`;
    if (smooth) setTimeout(() => img.classList.remove("smooth"), 220);
  }

  function _lbZoomReset() {
    _lbZoom.scale = 1; _lbZoom.tx = 0; _lbZoom.ty = 0;
    _lbApply(true);
  }

  // pivot (clientX/Y) 기준 줌 — 휠/핀치 양쪽에서 사용. 핵심: 같은 화면점이 줌 후에도 같은 화면점에 있게 tx/ty 보정.
  function _lbZoomTo(newScale, pivotX, pivotY, smooth) {
    const s0 = _lbZoom.scale;
    const s1 = Math.max(_lbZoom.min, Math.min(_lbZoom.max, newScale));
    if (Math.abs(s1 - s0) < 0.0001) return;
    if (pivotX != null && pivotY != null && els.lightboxImg) {
      const rect = els.lightboxImg.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      // 화면점(pivot)이 줌 후에도 같은 화면점이 되도록 tx/ty 보정:
      //   tx' = pivot - cx - (pivot - cx - tx) * k   (k = s1/s0)
      const k = s1 / s0;
      _lbZoom.tx = pivotX - cx - (pivotX - cx - _lbZoom.tx) * k;
      _lbZoom.ty = pivotY - cy - (pivotY - cy - _lbZoom.ty) * k;
    }
    _lbZoom.scale = s1;
    if (s1 <= 1.001) { _lbZoom.tx = 0; _lbZoom.ty = 0; }   // 1배 이하 — 위치 리셋
    _lbApply(smooth !== false);
  }

  function _lbZoomBtnIn()    { _lbZoomTo(_lbZoom.scale * _lbZoom.step, null, null, true); }
  function _lbZoomBtnOut()   { _lbZoomTo(_lbZoom.scale / _lbZoom.step, null, null, true); }
  function _lbZoomBtnReset() { _lbZoomReset(); }

  // 줌·팬 핸들러 1회 등록. lightbox 가 처음 열릴 때 호출.
  function setupLightboxZoom() {
    if (_lbZoomWired || !els.lightbox || !els.lightboxImg) return;
    _lbZoomWired = true;
    const stage = document.getElementById("lbStage") || els.lightbox.querySelector(".lb-stage");
    const img = els.lightboxImg;
    // 휠 줌
    stage?.addEventListener("wheel", (e) => {
      e.preventDefault();
      const dir = e.deltaY < 0 ? 1 : -1;
      const factor = dir > 0 ? 1.15 : 1 / 1.15;
      _lbZoomTo(_lbZoom.scale * factor, e.clientX, e.clientY, false);
    }, { passive: false });
    // 더블클릭 → 1배 ↔ 2배 토글
    img.addEventListener("dblclick", (e) => {
      e.preventDefault();
      if (_lbZoom.scale > 1.001) _lbZoomReset();
      else _lbZoomTo(2, e.clientX, e.clientY, true);
    });
    // 드래그 팬 (PC) — scale > 1 일 때만
    img.addEventListener("pointerdown", (e) => {
      if (e.pointerType === "touch") return;   // 터치는 별도 핸들러
      if (_lbZoom.scale <= 1.001) return;
      _lbDrag = { startX: e.clientX, startY: e.clientY, tx0: _lbZoom.tx, ty0: _lbZoom.ty };
      img.classList.add("dragging");
      try { img.setPointerCapture(e.pointerId); } catch (_) {}
    });
    img.addEventListener("pointermove", (e) => {
      if (!_lbDrag || e.pointerType === "touch") return;
      _lbZoom.tx = _lbDrag.tx0 + (e.clientX - _lbDrag.startX);
      _lbZoom.ty = _lbDrag.ty0 + (e.clientY - _lbDrag.startY);
      _lbApply(false);
    });
    const endDrag = (e) => {
      if (!_lbDrag) return;
      _lbDrag = null;
      img.classList.remove("dragging");
      try { img.releasePointerCapture(e.pointerId); } catch (_) {}
    };
    img.addEventListener("pointerup", endDrag);
    img.addEventListener("pointercancel", endDrag);
    img.addEventListener("pointerleave", endDrag);

    // 모바일: 핀치(2손가락) 줌 + 단일터치 팬(줌 상태) + 더블탭
    stage?.addEventListener("touchstart", (e) => {
      if (e.touches.length === 2) {
        const a = e.touches[0], b = e.touches[1];
        const dx = b.clientX - a.clientX, dy = b.clientY - a.clientY;
        _lbPinch = {
          startDist: Math.hypot(dx, dy),
          startScale: _lbZoom.scale,
          midX: (a.clientX + b.clientX) / 2,
          midY: (a.clientY + b.clientY) / 2,
        };
        _lbDrag = null;
      } else if (e.touches.length === 1 && _lbZoom.scale > 1.001) {
        const t = e.touches[0];
        _lbDrag = { startX: t.clientX, startY: t.clientY, tx0: _lbZoom.tx, ty0: _lbZoom.ty };
        img.classList.add("dragging");
      } else if (e.touches.length === 1) {
        // 더블탭 감지 — 1배일 때만
        const now = Date.now();
        if (now - _lbLastTap < 320) {
          const t = e.touches[0];
          _lbZoomTo(2, t.clientX, t.clientY, true);
          _lbLastTap = 0;
        } else {
          _lbLastTap = now;
        }
      }
    }, { passive: true });
    stage?.addEventListener("touchmove", (e) => {
      if (_lbPinch && e.touches.length === 2) {
        e.preventDefault();
        const a = e.touches[0], b = e.touches[1];
        const dist = Math.hypot(b.clientX - a.clientX, b.clientY - a.clientY);
        const newScale = _lbPinch.startScale * (dist / _lbPinch.startDist);
        _lbZoomTo(newScale, _lbPinch.midX, _lbPinch.midY, false);
      } else if (_lbDrag && e.touches.length === 1 && _lbZoom.scale > 1.001) {
        const t = e.touches[0];
        _lbZoom.tx = _lbDrag.tx0 + (t.clientX - _lbDrag.startX);
        _lbZoom.ty = _lbDrag.ty0 + (t.clientY - _lbDrag.startY);
        _lbApply(false);
      }
    }, { passive: false });
    stage?.addEventListener("touchend", () => {
      _lbPinch = null;
      if (_lbDrag) { _lbDrag = null; img.classList.remove("dragging"); }
    });

    // 버튼
    document.getElementById("lbZoomIn")?.addEventListener("click", _lbZoomBtnIn);
    document.getElementById("lbZoomOut")?.addEventListener("click", _lbZoomBtnOut);
    document.getElementById("lbZoomReset")?.addEventListener("click", _lbZoomBtnReset);

    // 키보드 + - 0 (lightbox 열려 있을 때만)
    document.addEventListener("keydown", (e) => {
      if (!els.lightbox || !els.lightbox.classList.contains("open")) return;
      if (e.key === "+" || e.key === "=") { e.preventDefault(); _lbZoomBtnIn(); }
      else if (e.key === "-" || e.key === "_") { e.preventDefault(); _lbZoomBtnOut(); }
      else if (e.key === "0") { e.preventDefault(); _lbZoomBtnReset(); }
    });
  }

  // 사용자가 위로 스크롤한 상태면 자동으로 맨 아래로 끌고 가지 않음 (채팅 UX 표준).
  //   opts.force=true 면 무조건 맨 아래 (예: 방 처음 열 때, 본인 메시지 전송 직후).
  //   기본(force=false): 이미 맨 아래 근처(150px 이내)일 때만 자동 스크롤.
  function scrollToBottom(opts) {
    const force = opts && opts.force === true;
    requestAnimationFrame(() => {
      const m = els.messages;
      if (!m) return;
      if (!force) {
        const distFromBottom = m.scrollHeight - m.scrollTop - m.clientHeight;
        if (distFromBottom > 150) return;  // 사용자가 위쪽 보고 있음 — 건드리지 않음
      }
      m.scrollTop = m.scrollHeight;
    });
  }

  // 사용자가 메시지 영역을 직접 만졌는지(스크롤 의도) — 방 열기 직후 강제 스냅이 사용자를 방해하지 않게.
  let _userTouchedMessages = false;
  // 특정 메시지로 '점프' 중이면 그 메시지 id — 이 동안은 모든 '맨 아래로 강제 스크롤'을 끔(멘션 점프가 안 덮이게). (대표 지시 2026-06-02)
  let _jumpTargetMsgId = null;
  let _msgTouchWired = false;
  function _wireMsgTouchOnce() {
    if (_msgTouchWired || !els.messages) return;
    _msgTouchWired = true;
    const mark = () => { _userTouchedMessages = true; };
    els.messages.addEventListener('touchstart', mark, { passive: true });
    els.messages.addEventListener('wheel', mark, { passive: true });
    els.messages.addEventListener('pointerdown', mark, { passive: true });
  }

  // 방 열기/메시지 재로드 시 최하단으로 — '흔들림' 없는 조용한 버전 (대표 지시 2026-05-20):
  //   - 즉시 1회 + 다음 프레임 1회 + 250ms 1회, 총 3번만 (반복 인터벌 제거 → 흔들림 없음)
  //   - 250ms 보정은 번역바·이미지 등 늦게 들어오는 레이아웃 1회 대응용
  //   - 사용자가 직접 스크롤 시작하면 중단
  function _forceMessagesToBottom() {
    const m = els.messages;
    if (!m) return;
    _wireMsgTouchOnce();
    _userTouchedMessages = false;   // 새 방/재렌더 → 스크롤 의도 초기화
    if (_jumpTargetMsgId) return;   // 특정 메시지로 점프 중 — 하단 강제 스크롤 안 함(점프 로직이 그 메시지로 이동) (대표 지시 2026-06-02)
    const toBottom = () => {
      if (_userTouchedMessages) return;
      try {
        const area = document.getElementById('composerArea');
        if (area && area.offsetHeight > 0) {
          document.documentElement.style.setProperty('--composer-area-h', area.offsetHeight + 'px');
        }
      } catch (e) {}
      m.scrollTop = m.scrollHeight + 9999;  // 절대 최하단 (초과분 자동 clamp)
    };
    toBottom();
    requestAnimationFrame(toBottom);
    setTimeout(toBottom, 250);
    // iOS 보정: 방 재로드 시 마지막 메시지에 이미지(스티커/첨부)가 있으면 로드 후 재스크롤
    // 250ms 만으로는 iOS Safari 의 느린 이미지 디코딩을 커버하지 못하는 경우가 있음
    setTimeout(() => {
      if (_userTouchedMessages) return;
      const imgs = m.querySelectorAll("img:not([data-scroll-wired])");
      imgs.forEach(img => {
        img.dataset.scrollWired = "1";
        if (!img.complete || img.naturalHeight === 0) {
          img.addEventListener("load",  () => { if (!_userTouchedMessages) toBottom(); }, { once: true });
          img.addEventListener("error", () => { if (!_userTouchedMessages) toBottom(); }, { once: true });
        }
      });
    }, 100);
  }

  // 방 진입 시 '여기까지 읽었습니다' 줄을 화면 위쪽(56px 아래)으로 — 안 읽은 첫 메시지부터 보이게 (대표 지시 2026-06-04 카톡식)
  //   _forceMessagesToBottom 과 동일하게 즉시+다음프레임+250ms 다중 패스, 사용자가 직접 스크롤하면 중단.
  function _scrollMessagesToUnread() {
    const m = els.messages;
    if (!m) return;
    _wireMsgTouchOnce();
    _userTouchedMessages = false;
    if (_jumpTargetMsgId) return;
    const go = () => {
      if (_userTouchedMessages) return;
      const ud = m.querySelector(".unread-divider");
      if (!ud) { m.scrollTop = m.scrollHeight + 9999; return; }
      try {
        const cTop = m.getBoundingClientRect().top;
        const dTop = ud.getBoundingClientRect().top;
        m.scrollTop += (dTop - cTop) - 56;   // 줄을 화면 상단에서 56px 아래에
      } catch (e) { m.scrollTop = m.scrollHeight + 9999; }
    };
    go();
    requestAnimationFrame(go);
    setTimeout(go, 250);
  }

  async function renderItemMeta(room) {
    const isItem = room.type === "item";
    // 헤더 메타 '기본부'(프로젝트 칩) 계산. ⚠ 깜빡임 방지(대표 지시 2026-05-20, preview 실측):
    //   itemMeta 를 미리 비우거나 숨기지 않는다 — 요약까지 모은 뒤 '한 번에' 교체(중간 빈 상태 X → 헤더가 줄었다 커지지 않음).
    let basePart = "";
    // 📑 프로젝트 정보 수정 — 프로젝트 방 + 방장·PM·관리자만 (대표 지시 2026-05-27)
    //   일반 멤버가 '방 설정(🛠️)' 으로 오해해서 누르는 사고 방지 차원에서 권한 제한.
    const _itemEditAllowed = !window._meIsGuest && ((window._meRole === "ceo") || (room.my_role === "host" || room.my_role === "sub_host"));
    if (isItem) {
      const parts = [];
      if (room.item_customer) parts.push(`<span class="customer-chip">${escapeHtml(room.item_customer)}</span>`);
      if (room.item_code) parts.push(`<span class="code-chip">${escapeHtml(room.item_code)}</span>`);
      if (room.item_status) parts.push(`<span class="status-pill status-${room.item_status}">${_itemStatusLabel(room.item_status)}</span>`);
      if (room.item_due) parts.push(`<span class="meta-due">납기 ${fmtDate(room.item_due)}</span>`);
      basePart = parts.join("");
      els.itemEditBtn.hidden = !_itemEditAllowed;
    } else {
      els.itemEditBtn.hidden = true;
    }
    els.galleryBtn.hidden = false;
    els.requestsBtn.hidden = false;
    // 📥 이력 다운로드 — 게스트는 차단 (대표 지시 2026-05-28)
    if (els.exportBtn) els.exportBtn.hidden = !!window._meIsGuest;
    // 🤝 고객사 초대 — 그룹·프로젝트 방에서만, 방장/PM/관리자. (대표 지시 2026-05-30)
    //   1:1·채널·메모는 초대 불가 → 버튼 자체 숨김. (1:1은 사적대화라 외부 초대 시 과거대화 노출 방지)
    if (els.guestInviteBtn) {
      const t = room.type;
      const roleOk = (window._meRole === "ceo" || room.my_role === "host" || room.my_role === "sub_host");
      const canShow = !window._meIsGuest && roleOk && (t === "group" || t === "item");
      els.guestInviteBtn.hidden = !canShow;
    }
    // 자동 채널(전사/소속)은 나가기 금지 → 나가기 버튼 숨김 (대표 지시 2026-05-20)
    if (els.leaveRoomBtn) els.leaveRoomBtn.hidden = !!room.channel_scope;
    if (els.starredBtn) els.starredBtn.hidden = false;
    // 🧠 AI 요약 / 📚 프로젝트 이력 — 테스트 기간 방장·PM·관리자만 (대표 지시 2026-05-27)
    // + 게스트(외부 사용자) 는 무조건 차단 (대표 지시 2026-05-28)
    const _aiAllowed = !window._meIsGuest && ((window._meRole === "ceo") || (room.my_role === "host" || room.my_role === "sub_host"));
    // 📚 프로젝트 이력 — 게스트(외부)는 사용 불가 (대표 지시 2026-05-30). 방장·PM·관리자만.
    const _historyView = _aiAllowed;
    // 🧠 AI 요약 진입 — 저장본 '보기'는 방 멤버 전체(게스트만 제외), '생성'만 권한자 (대표 지시 2026-06-01, 비용 절감)
    if (els.aiSummaryBtn) els.aiSummaryBtn.hidden = !!window._meIsGuest;
    if (els.aiRewriteBtn) els.aiRewriteBtn.disabled = false;
    // 📚 프로젝트 이력 — 프로젝트 방 + (권한자 또는 게스트)
    if (els.projectHistoryBtn) els.projectHistoryBtn.hidden = (room.type !== "item") || !_historyView;
    // 🧵 이 방의 스레드 — 모든 멤버 (조회만, 비용 없음). 자기 메모방은 의미 없으니 숨김.
    if (els.roomThreadsBtn) els.roomThreadsBtn.hidden = (room.type === "self");
    // 🔍 대화 검색 — 모든 방에서 가능 (현재 방 메시지에서 단어 찾기) 대표 지시 2026-06-06
    if (els.roomSearchBtn) els.roomSearchBtn.hidden = false;
    // 모바일 더보기 메뉴의 AI 항목 + 스레드 항목 + 프로젝트 정보 수정 항목 동기화
    if (els.headMoreMenu) {
      const _mAi   = els.headMoreMenu.querySelector('button[data-act="ai_summary"]');
      const _mHist = els.headMoreMenu.querySelector('button[data-act="project_history"]');
      const _mThr  = els.headMoreMenu.querySelector('button[data-act="room_threads"]');
      const _mSrch = els.headMoreMenu.querySelector('button[data-act="room_search"]');
      const _mEdit = els.headMoreMenu.querySelector('button[data-act="edit"]');
      if (_mAi)   _mAi.hidden   = !!window._meIsGuest;   // AI 요약 보기는 멤버 전체(게스트만 제외) (대표 지시 2026-06-01)
      if (_mHist) _mHist.hidden = (room.type !== "item") || !_historyView;
      if (_mThr)  _mThr.hidden  = (room.type === "self");
      if (_mSrch) _mSrch.hidden = false;   // 검색은 항상 가능
      if (_mEdit) _mEdit.hidden = !isItem || !_itemEditAllowed;
    }
    const rsBtn = document.getElementById('roomSettingsBtn');
    if (rsBtn) rsBtn.hidden = (room.type === 'direct') || !!window._meIsGuest;  // 1:1 방·게스트는 방설정 X (대표 지시 2026-05-29)
    if (els.headMoreBtn) els.headMoreBtn.hidden = false;  // ⋮ 더보기(아이콘 설명/추가메뉴)
    // 자동번역 토글바 — 번역 기능이 설정돼 있을 때만 노출
    if (els.composerLangbar) {
      const status = await getTranslateStatus();
      els.composerLangbar.hidden = !status.enabled;
      if (status.enabled) applyComposerLangUI();
    }
    refreshRequestsBadge();
    // 요약(멤버수·파일 등) 계산 후 기본부와 합쳐 '한 번에' 교체
    let summaryHtml = "";
    try {
      const s = await api.summary(room.id);
      const items = [];
      // 사진·파일·멤버 → 클릭 시 해당 화면 바로 열기 (대표 지시 2026-05-21)
      if (s.image_count) items.push(`<button type="button" class="sm-item sm-item-btn" data-sm-act="gallery-image" title="이 방의 사진 보기">📷 ${s.image_count}</button>`);
      if (s.file_count)  items.push(`<button type="button" class="sm-item sm-item-btn" data-sm-act="gallery-file"  title="이 방의 파일 보기">📎 ${s.file_count}</button>`);
      if (s.open_requests)   items.push(`<button type="button" class="sm-item sm-item-btn attn" data-sm-act="requests-open" title="이 방의 전체 요청 목록 보기">📌 ${s.open_requests} 열림</button>`);
      if (s.active_requests) items.push(`<button type="button" class="sm-item sm-item-btn" data-sm-act="requests-prog" title="이 방의 진행중 요청 보기">⚙ ${s.active_requests} 진행중</button>`);
      if (s.members && room.id !== window.__BUG_ROOM_ID__) items.push(`<button type="button" class="sm-item sm-item-btn" data-sm-act="members" title="참여자 보기">👥 ${s.members}</button>`);   // (신고)채널은 참여자 표시 안 함 (대표 지시 2026-06-03)
      if (items.length) summaryHtml = `<div class="summary-mini" style="width:100%">${items.join("")}</div>`;
    } catch (e) { /* ignore */ }
    // 그새 다른 방으로 바뀌었으면 새 방 헤더를 덮어쓰지 않음 (빠른 전환 경쟁 방지)
    if (!activeRoom || activeRoom.id !== room.id) return;
    const full = basePart + summaryHtml;
    els.itemMeta.innerHTML = full;
    els.itemMeta.hidden = (full === "");
    // sm-item 클릭 핸들러 연결
    els.itemMeta.querySelectorAll("[data-sm-act]").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const act = btn.dataset.smAct;
        if (act === "gallery-image") openGallery("image");
        else if (act === "gallery-file") openGallery("file");
        else if (act === "members") openRoomSettings(activeRoom && activeRoom.id);
        else if (act === "requests-open") openRequests();              // 방 전체 요청목록 (열림 탭)
        else if (act === "requests-prog") openRequests("in_progress"); // 방 전체 요청목록 (진행중 탭)
      });
    });
  }

  async function refreshRequestsBadge() {
    if (!activeRoom) return;
    try {
      const reqs = await api.requests(activeRoom.id, "open");
      const count = reqs.filter(r => r.status === "open" || r.status === "in_progress").length;
      els.requestsBadge.hidden = count === 0;
      els.requestsBadge.textContent = count > 9 ? "9+" : count;
    } catch (e) { /* ignore */ }
  }

  // ---------- room actions ----------
  async function openRoom(room, opts) {
    if (!room) return;
    opts = opts || {};
    _jumpTargetMsgId = opts.jumpToMsgId || null;   // 특정 메시지로 점프해 열기(멘션 등) → 하단 강제 스크롤·자동포커스 억제
    try { closeMessageContextMenu(); } catch (_) {}   // 방 전환 시 떠 있던 길게누름 메뉴 닫기
    // ※ emit("leave") 안 함 — 한 번 join 한 방은 계속 join 유지.
    // 다른 방으로 전환해도 그 방의 새 메시지 알림(소리·토스트·사이드바 깜빡임)을 받기 위함.
    // 서버 connect 핸들러가 모든 방 자동 join 하므로 명시적 emit("join") 도 보험 차원만.
    activeRoom = room;
    app.classList.add("viewing-chat");
    // 접힘(목록만) 상태에서 방 1번클릭 = 선택만(자동으로 펼치지 않음). 보려면 더블클릭(새 창) 또는 펼치기 탭(❯). (대표 지시 2026-06-02)
    // 1:1 방 제목 — '이름 직급님-부서' 형식 (대표 지시 2026-05-19)
    await ensureUsers();
    _setChatTitleFor(room);
    // 헤더 메타는 비동기로 갱신(중간에 비우지 않아 헤더 안 흔들림). 메시지 렌더를 막지 않음 → 빠른 전환.
    renderItemMeta(room);
    els.msgInput.disabled = false;
    els.sendBtn.disabled = false;
    els.attachBtn.disabled = false;
    if (els.captureBtn) els.captureBtn.disabled = false;
    if (els.multiShareBtn) els.multiShareBtn.disabled = false;
    if (els.emojiBtn) els.emojiBtn.disabled = false;
    if (els.stickerBtn) els.stickerBtn.disabled = false;
    // 모바일에서 키보드 자동 띄움 방지 — 사용자가 입력창 누를 때만 열림.
    // ★ 점프(멘션 등)로 열 땐 자동포커스 안 함 — 포커스가 onInputFocus 의 '맨 아래로 강제' 타이머 6개를
    //   발동시켜 점프 위치를 1.2초간 계속 덮어쓰기 때문(깜빡임·위치실패 원인). (대표 지시 2026-06-02)
    if (window.innerWidth > 720 && !_jumpTargetMsgId) els.msgInput.focus();
    // URL 에 ?room=X 기록 — SW 가 클라이언트 URL 보고 활성 방 판정 (Chrome PWA visibilityState 버그 우회)
    //  (옛: 모바일만. 현: 데스크톱·모바일 둘 다 — SW 가 모든 클라이언트 URL 검사) (대표 지시 2026-05-26)
    if (!(history.state && history.state.knkRoom === room.id)) {
      // 게스트는 ?g=토큰 도 같이 — 외부 브라우저로 열면 자동 재인증되어 방으로 들어감 (직원은 ?room 만, 동일 동작). (대표 지시 2026-05-30)
      const _gq = (window._meIsGuest && window._meGuestToken) ? `&g=${encodeURIComponent(window._meGuestToken)}` : "";
      try { history.pushState({ knkRoom: room.id }, "", `?room=${room.id}${_gq}`); } catch(e) {}
    }
    socket.emit("join", { room_id: room.id });
    // 메시지 + 읽음 상태 병렬 로드
    const [msgs, rs] = await Promise.all([
      api.messages(room.id),
      api.readStatus(room.id).catch(() => ({ members: [], total: 0 })),
    ]);
    roomReadStatus = rs || { members: [], total: 0 };
    // 카톡식 '여기까지 읽었습니다' — 이 방 진입 시점의 내 마지막 읽은 메시지 id 스냅샷 (아래 markRead 로 갱신되기 전). (대표 지시 2026-06-04)
    {
      const _myMem = (roomReadStatus.members || []).find(mm => mm && mm.user_id === meId);
      _entryLastReadId = _myMem ? (_myMem.last_read_message_id || 0) : 0;
      _scrollToUnreadOnce = true;
    }
    // 게스트(디렉터리에 없는 외부 사용자)도 작성자 줄에 직책·부서 표시 — 이 방 멤버 메타 캐시.
    //   read_status 가 멤버별 title·department·is_guest 를 주므로 추가 fetch 없이 재사용. (대표 지시 2026-05-30)
    window._roomMemberMeta = {};
    (roomReadStatus.members || []).forEach(mm => {
      if (mm && mm.user_id != null) window._roomMemberMeta[mm.user_id] = mm;
    });
    // 🌐 법인별 자동 번역 — 이 방에서 번역을 직접 정한 적 없으면 소속(부서) 기반으로 자동 (대표 지시 2026-06-04)
    //   본사 직원 → VN(베트남어), 베트남 직원 → KR(한국어). 사용자가 칩을 바꾼 방(manual)은 건드리지 않음.
    try {
      if (!localStorage.getItem("knkmsg.tr.manual." + room.id)) {
        setRoomTranslateMode(room.id, computeAutoTranslateLang(room));
      }
    } catch (e) {}
    if (typeof applyComposerLangUI === "function") applyComposerLangUI();
    // 1:1 방 제목 정확도 보강 — readStatus 의 멤버 정보 반영 (대표 지시 2026-05-19)
    _setChatTitleFor(room);
    renderMessages(msgs);
    await api.markRead(room.id);
    _clearRoomNotifications(room.id);   // 이 방을 열어 확인 → 이 기기의 이 방 알림 즉시 닫기
    _notifySWActiveRoom(room.id);       // SW 에 활성 방 알림 — 새 메시지 도착 시 알림 생략 (대표 지시 2026-05-26)
    loadNotices(room.id);               // 📢 이 방 공지사항 로드 (대표 지시 2026-05-29)
    await refreshRooms();
  }

  async function refreshReadStatus() {
    if (!activeRoom) return;
    try {
      roomReadStatus = await api.readStatus(activeRoom.id);
      // 메시지 다시 그리기 (읽음 배지 갱신)
      const currentMsgs = [...els.messages.querySelectorAll(".msg")].map(li => li.dataset.msgId);
      if (currentMsgs.length) {
        const msgs = await api.messages(activeRoom.id);
        renderMessages(msgs);
      }
    } catch (e) { /* ignore */ }
  }

  // 재연결·네트워크 복귀 시 '보고 있는 방'의 놓친 메시지 재동기화. (대표 지시 2026-05-23)
  //   끊긴 동안 못 받은 new_message 를 메시지 목록 재조회로 채우고, 읽음 처리·알림 정리.
  //   force=false 면 3초 쓰로틀(중복 호출 방지). 네트워크 아직 불안정하면 조용히 실패 → 다음 기회.
  async function _resyncActiveRoom(force) {
    if (!activeRoom) return;
    const now = Date.now();
    if (!force && (now - _lastRoomResync < 3000)) return;
    _lastRoomResync = now;
    try {
      const msgs = await api.messages(activeRoom.id);
      renderMessages(msgs);
      try { await api.markRead(activeRoom.id); } catch (e) {}
      try { _clearRoomNotifications(activeRoom.id); } catch (e) {}
    } catch (e) { /* 네트워크 아직 불안정 — 다음 재연결/복귀 때 재시도 */ }
  }

  // ========================= 📢 방 공지사항 (대표 지시 2026-05-29) =========================
  // 평소: 최신 1건 고정 / 펼치기: 과거 전부 / 접기: 알약으로 축소(방별 기억) / 삭제: 등록자·방장·PM·관리자
  let _notices = [];            // 현재 방 공지 (최신순)
  let _noticesExpanded = false; // 지난 공지 펼침 여부
  const _nt = (k, fb) => (window.KNK_t ? window.KNK_t(k) : fb);
  const _noticeCollapseKey = (rid) => "knkmsg.notice.collapsed." + rid;
  // 저장값 3가지: "1"=사용자가 직접 접음 / "0"=직접 폄 / null=미설정
  function _noticePref(rid) {
    try { return localStorage.getItem(_noticeCollapseKey(rid)); } catch (e) { return null; }
  }
  function _setNoticeCollapsed(rid, on) {
    try { localStorage.setItem(_noticeCollapseKey(rid), on ? "1" : "0"); } catch (e) {}
  }
  // 접힘 여부 결정: 사용자가 직접 설정했으면 그 값 유지(지속),
  // 미설정이면 기본값 — 공지 없으면 접고, 있으면 폄 (대표 지시 2026-05-29)
  function _noticeShouldCollapse(rid) {
    const pref = _noticePref(rid);
    if (pref === "1") return true;
    if (pref === "0") return false;
    return _notices.length === 0;
  }
  function _hideNoticeBar() {
    const bar = document.getElementById("noticeBar");
    if (bar) bar.hidden = true;
    const headBtn = document.getElementById("noticeHeadBtn");
    if (headBtn) headBtn.hidden = true;
    const headBadge = document.getElementById("noticeHeadBadge");
    if (headBadge) headBadge.hidden = true;
  }
  // 헤더 📢 또는 ⋮ 메뉴에서 호출 — 공지 있으면 막대 펼침/접힘 토글, 없으면 등록창 열기
  function toggleNoticeFromHeader() {
    if (!activeRoom) return;
    const rid = activeRoom.id;
    if (_notices.length === 0) { openNoticeAddDialog(); return; }
    const collapsed = _noticeShouldCollapse(rid);
    _setNoticeCollapsed(rid, !collapsed);   // 보이면 접고, 접혀있으면 펴기
    if (collapsed) _noticesExpanded = false;
    renderNoticeBar(rid);
  }
  function openNoticeAddDialog() {
    const dlg = document.getElementById("noticeAddDialog");
    const input = document.getElementById("noticeAddInput");
    if (input) input.value = "";
    if (dlg) { try { dlg.showModal(); } catch (_) { dlg.classList.add("open"); } setTimeout(() => { try { if (input) input.focus(); } catch (e) {} }, 60); }
  }
  function _fmtNoticeTime(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return "";
      const p = (n) => String(n).padStart(2, "0");
      return `${d.getFullYear()}.${p(d.getMonth() + 1)}.${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
    } catch (e) { return ""; }
  }
  async function loadNotices(roomId) {
    const bar = document.getElementById("noticeBar");
    if (!bar) return;
    _noticesExpanded = false;
    try {
      const res = await fetch(`${BASE}/api/rooms/${roomId}/notices`);
      const data = await res.json();
      _notices = (data && data.items) ? data.items : [];
    } catch (e) { _notices = []; }
    // 응답 도착 시점에 방이 바뀌었으면 무시
    if (activeRoom && activeRoom.id === roomId) renderNoticeBar(roomId);
  }
  function _addNoticeLocal(notice) {
    if (!notice || _notices.some(n => n.id === notice.id)) return;
    _notices.unshift(notice);
  }
  function renderNoticeBar(roomId) {
    const bar = document.getElementById("noticeBar");
    // 헤더 진입 버튼(📢) — 방 열려 있으면 노출(모바일은 CSS로 숨고 ⋮ 메뉴에서 접근), 개수 뱃지
    const headBtn = document.getElementById("noticeHeadBtn");
    const headBadge = document.getElementById("noticeHeadBadge");
    const hmmBadge = document.getElementById("hmmNoticeBadge");
    const count = _notices.length;
    const badgeTxt = count > 0 ? (count > 99 ? "99+" : String(count)) : "";
    if (headBtn) headBtn.hidden = !activeRoom;
    if (headBadge) { headBadge.textContent = badgeTxt; headBadge.hidden = (count === 0); }
    if (hmmBadge) { hmmBadge.textContent = badgeTxt; hmmBadge.hidden = (count === 0); }
    if (!bar) return;
    const body = document.getElementById("noticeBody");
    const list = document.getElementById("noticeList");
    const moreCount = document.getElementById("noticeMoreCount");
    const expandBtn = document.getElementById("noticeExpandBtn");
    const expandCaret = document.getElementById("noticeExpandCaret");
    const expandLabel = document.getElementById("noticeExpandLabel");
    // 공지가 없거나 접힘이면 막대 숨김 — 헤더 📢(PC)/⋮ 메뉴(모바일)로만 접근
    if (count === 0 || _noticeShouldCollapse(roomId)) {
      bar.hidden = true;
      return;
    }
    bar.hidden = false;
    if (body) body.hidden = false;
    const shown = _noticesExpanded ? _notices : _notices.slice(0, 1);
    if (list) {
      list.innerHTML = shown.map((n, idx) => {
        const meta = [escapeHtml(n.author || ""), n.author_title ? escapeHtml(n.author_title) : "", _fmtNoticeTime(n.created_at)].filter(Boolean).join(" · ");
        const latestTag = (idx === 0 && !_noticesExpanded && _notices.length > 1)
          ? `<span class="notice-latest-tag">${escapeHtml(_nt("notice.latest", "최신"))}</span>` : "";
        const delBtn = n.can_delete
          ? `<button type="button" class="notice-del" data-notice-id="${n.id}" title="${escapeHtml(_nt("notice.delete", "삭제"))}">🗑</button>` : "";
        return `<li class="notice-item">
          <div class="notice-item-top">${latestTag}<span class="notice-meta">${meta}</span>${delBtn}</div>
          <div class="notice-content">${escapeHtml(n.content)}</div>
        </li>`;
      }).join("");
    }
    const older = _notices.length - 1;
    if (expandBtn) {
      if (older > 0) {
        expandBtn.style.display = "";
        if (moreCount) moreCount.textContent = _noticesExpanded ? "" : ` (+${older})`;
        if (expandLabel) expandLabel.textContent = _noticesExpanded ? _nt("notice.collapseList", "접기") : _nt("notice.expand", "지난 공지");
        if (expandCaret) expandCaret.textContent = _noticesExpanded ? "▴" : "▾";
      } else {
        expandBtn.style.display = "none";
      }
    }
  }
  async function submitNotice() {
    const input = document.getElementById("noticeAddInput");
    const dlg = document.getElementById("noticeAddDialog");
    if (!input || !activeRoom) return;
    const content = (input.value || "").trim();
    if (!content) { alert(_nt("notice.emptyAlert", "공지 내용을 입력하세요.")); return; }
    const rid = activeRoom.id;
    try {
      const res = await fetch(`${BASE}/api/rooms/${rid}/notices`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) { alert((data && data.error) || _nt("notice.saveFail", "공지 등록에 실패했습니다.")); return; }
      _addNoticeLocal(data.notice);
      _setNoticeCollapsed(rid, false);   // 새 공지 올리면 펼쳐 보이게
      if (activeRoom && activeRoom.id === rid) renderNoticeBar(rid);
      if (dlg) dlg.close();
      input.value = "";
    } catch (e) { alert(_nt("notice.saveFail", "공지 등록에 실패했습니다.")); }
  }
  async function deleteNotice(noticeId) {
    if (!activeRoom) return;
    if (!confirm(_nt("notice.confirmDelete", "이 공지를 삭제할까요? (목록에서 사라집니다)"))) return;
    const rid = activeRoom.id;
    try {
      const res = await fetch(`${BASE}/api/rooms/${rid}/notices/${noticeId}`, { method: "DELETE" });
      const data = await res.json();
      if (!res.ok || !data.ok) { alert((data && data.error) || _nt("notice.delFail", "삭제에 실패했습니다.")); return; }
      _notices = _notices.filter(n => n.id !== noticeId);
      if (activeRoom && activeRoom.id === rid) renderNoticeBar(rid);
    } catch (e) { alert(_nt("notice.delFail", "삭제에 실패했습니다.")); }
  }
  // 버튼 연결 (로드 시 1회)
  (function wireNotice() {
    const headBtn = document.getElementById("noticeHeadBtn");
    const addBtn = document.getElementById("noticeAddBtn");
    const expandBtn = document.getElementById("noticeExpandBtn");
    const collapseBtn = document.getElementById("noticeCollapseBtn");
    const list = document.getElementById("noticeList");
    const submit = document.getElementById("noticeAddSubmit");
    if (headBtn) headBtn.addEventListener("click", toggleNoticeFromHeader);
    if (addBtn) addBtn.addEventListener("click", openNoticeAddDialog);
    if (expandBtn) expandBtn.addEventListener("click", () => {
      _noticesExpanded = !_noticesExpanded;
      if (activeRoom) renderNoticeBar(activeRoom.id);
    });
    if (collapseBtn) collapseBtn.addEventListener("click", () => {
      if (!activeRoom) return;
      _setNoticeCollapsed(activeRoom.id, true);
      renderNoticeBar(activeRoom.id);
    });
    if (list) list.addEventListener("click", (e) => {
      const del = e.target.closest(".notice-del");
      if (del) { const id = parseInt(del.getAttribute("data-notice-id"), 10); if (id) deleteNotice(id); }
    });
    if (submit) submit.addEventListener("click", submitNotice);
  })();

  // 활성 방 제목 갱신 — 1:1 방은 '이름 직급님-부서' 형식, 그 외는 room.name (대표 지시 2026-05-19)
  // 자동 채널·self 방은 사용자 언어에 맞춰 i18n / 일반 방은 name_vi·name_en 캐시 사용 (대표 지시 2026-05-28)
  function _setChatTitleFor(room) {
    if (!room) return;
    let title = room.name || (window.KNK_t ? window.KNK_t("room.unnamed") : "(이름없음)");
    if (room.type === "self") {
      title = window.KNK_t ? window.KNK_t("room.selfNote") : "📝 내 메모장";
    } else if (room.channel_scope === "all") {
      title = window.KNK_t ? window.KNK_t("room.knkWorld") : title;
    } else if (room.channel_scope === "hq") {
      title = window.KNK_t ? window.KNK_t("room.hqChannel") : title;
    } else if (room.channel_scope === "vn") {
      title = window.KNK_t ? window.KNK_t("room.vnChannel") : title;
    } else if (room.type !== "direct") {
      // 일반 방 — 다국어 캐시 사용
      const _lang = (typeof window.KNK_curLang === "function") ? window.KNK_curLang() : "ko";
      if (_lang === "ko" && room.name_ko) title = room.name_ko;
      else if (_lang === "vi" && room.name_vi) title = room.name_vi;
      else if (_lang === "en" && room.name_en) title = room.name_en;
      else if (_lang === "zh" && room.name_zh) title = room.name_zh;
    }
    if (room.type === "direct") {
      try {
        // readStatus 캐시(roomReadStatus) 또는 users 캐시에서 상대방 정보 추출
        let other = null;
        if (roomReadStatus && roomReadStatus.members) {
          other = roomReadStatus.members.find(u => u && u.user_id !== meId);
        }
        const cached = other ? (users.find(u => u.id === other.user_id) || {})
                             : ((room.peer_id != null ? users.find(u => u.id === room.peer_id)
                                                      : users.find(u => u.display_name === room.name)) || {});
        const dispName = _dispName(cached) || (other && other.display_name) || room.name || "";
        const titleStr = _dispTitle(cached) || (other && other.title) || "";
        const department = cached.department || (other && other.department) || "";
        if (dispName) {
          let name = dispName;
          const hon = _useEnNames() ? "" : "님";   // 영어/베트남어 화면에선 '님' 생략
          if (titleStr) name += ` ${titleStr}${hon}`;
          else name += hon;
          const dept = (_useEnNames() && cached.department_en) ? cached.department_en
                     : (department ? ((typeof deptShortLabel === "function") ? deptShortLabel(department) : department) : "");
          title = dept ? `${name}-${dept}` : name;
        }
      } catch(e) {}
    }
    els.chatTitle.textContent = title;
    els.chatTitle.title = title;
  }

  async function refreshRooms() {
    rooms = await api.rooms();
    try { _syncAppBadge(); } catch (e) {}   // 앱 아이콘 배지 = 전체 안 읽은 합 (읽으면 감소 반영)
    try { refreshMyTasksBadge(); } catch (e) {}   // 📌 내 요청 칩 배지 갱신
    try { _refreshUsersTabCount(); } catch (e) {} // 👥 사용자 탭 옆 본사·베트남 카운트 (대표 지시 2026-05-27)
    if (!els.searchResults.hidden) return;
    renderRoomList();
    if (activeRoom) {
      const updated = rooms.find(r => r.id === activeRoom.id);
      if (updated) {
        activeRoom = updated;
        _setChatTitleFor(updated);   // 1:1 방 형식 유지 (가벼움, 흔들림 없음)
        // ⚠ renderItemMeta(updated) 는 여기서 호출하지 않음 (대표 지시 2026-05-20, preview 실측):
        //   refreshRooms 는 새 메시지·상태 이벤트마다 빈번히 불리는데, renderItemMeta 가
        //   itemMeta 를 '숨김 → api.summary await → 표시' 하면서 헤더 높이가 81↔100 반복 → 화면 흔들림.
        //   헤더 메타(요약·칩)는 방 열 때(openRoom)만 갱신한다.
      }
    }
  }

  // 앱 아이콘 배지 동기화 — 전체 방 안 읽은 메시지 합. (2026-05-20)
  //  앱이 열려있을 때 메시지 읽으면 배지가 정확히 줄어들도록.
  //  (push 시점엔 sw.js 가 서버 badge 값으로 설정, 앱 내에서는 여기서 갱신)
  function _syncAppBadge() {
    if (!("setAppBadge" in navigator)) return;
    try {
      const total = (Array.isArray(rooms) ? rooms : []).reduce((s, r) => s + (r.unread || 0), 0);
      if (total > 0) navigator.setAppBadge(total);
      else navigator.clearAppBadge();
    } catch (e) { /* noop */ }
  }

  // 특정 방의 OS 푸시 알림(tag=room_<id>)을 닫음. (대표 지시 2026-05-20, 2026-05-26 강화)
  //  같은 기기에서 그 방을 열어/보고 확인하면, 알림을 직접 누르지 않아도 자동으로 사라지게.
  //  (다른 기기 — 백그라운드 휴대폰 — 는 서버가 보내는 clear 푸시를 sw.js 가 받아서 닫음)
  //  v16: Samsung Internet 호환 — SW message 채널로도 닫기 요청 (페이지 쪽 close() 가 OS 트레이까지 안 닿는 경우 대비)
  //  v17: 50/200ms 후 재스캔 — 누적 알림(2+) 잔존 시 1차 close 가 비동기 지연되는 경우 대비
  function _clearRoomNotifications(roomId) {
    if (!roomId || !("serviceWorker" in navigator)) return;
    const tag = "room_" + roomId;
    const doSweep = () => {
      navigator.serviceWorker.getRegistration().then(reg => {
        if (!reg) return;
        // 방법 1 — 페이지에서 직접 close() (대부분의 브라우저)
        if (reg.getNotifications) {
          const closeMatching = (notes) => notes.forEach(n => {
            if (n.tag === tag) { try { n.close(); } catch (e) {} }
          });
          reg.getNotifications({ tag }).then(closeMatching).catch(() => {});
          reg.getNotifications().then(closeMatching).catch(() => {});
        }
        // 방법 2 — SW 에 부탁 (이중 안전망)
        if (reg.active) {
          try { reg.active.postMessage({ type: "clear_room", roomId, tag }); } catch (e) {}
        }
      }).catch(() => {});
    };
    try {
      doSweep();                              // 즉시 1차
      setTimeout(doSweep, 60);                // 60ms 후 2차 (close 비동기 지연 대비)
      setTimeout(doSweep, 250);               // 250ms 후 3차 (Samsung Internet 일부 버전)
    } catch (e) {}
  }

  // SW 에 현재 활성 방 알림 — push 도착 시 같은 방이면 알림 생략하라고 (대표 지시 2026-05-26)
  // 모바일 OS 가 알림 close 권한 약해서 → 처음부터 안 띄우는 전략으로 우회.
  // ★ 서버에도 socket 이벤트로 알림 — Chrome PWA clients.matchAll 버그 우회. 서버가 푸시 자체를 막음.
  function _notifySWActiveRoom(roomId) {
    // (A) SW 에 알리기 — SW 가 클라이언트를 잘 보면 그 자체로 충분
    if ("serviceWorker" in navigator) {
      try {
        navigator.serviceWorker.getRegistration().then(reg => {
          if (!reg || !reg.active) return;
          try {
            reg.active.postMessage({
              type: roomId ? "set_active_room" : "clear_active_room",
              roomId: roomId || null,
            });
          } catch (e) {}
        }).catch(() => {});
      } catch (e) {}
    }
    // (B) 서버에 socket.io 이벤트로도 알리기 — Chrome PWA 버그 우회 (서버측 차단)
    try {
      if (typeof socket !== "undefined" && socket && socket.connected) {
        socket.emit("set_active_room", { room_id: roomId || null });
      }
    } catch (e) {}
  }

  // v20: SW 하트비트 — 2초마다 "나 살아있고 X방 보는 중" 통보. SW 가 재시작돼도 즉시 회복.
  //  visibilityState=hidden 이면 보내지 않음 — SW 가 "활성 아님" 으로 자연 만료시키도록.
  function _sendHeartbeatToSW() {
    if (!("serviceWorker" in navigator)) return;
    if (document.visibilityState !== "visible") return;
    try {
      navigator.serviceWorker.getRegistration().then(reg => {
        if (!reg || !reg.active) return;
        try {
          reg.active.postMessage({
            type: "heartbeat",
            roomId: (activeRoom && activeRoom.id) || null,
          });
        } catch (e) {}
      }).catch(() => {});
    } catch (e) {}
  }
  setInterval(_sendHeartbeatToSW, 2000);   // 2초 간격 — SW 재시작 후 8초 안에 회복
  _sendHeartbeatToSW();                     // 즉시 1회

  // 모든 알림 일괄 닫기 — 앱 포커스 복귀·로그인 직후 등에 사용 (대표 지시 2026-05-26)
  function _clearAllNotifications() {
    if (!("serviceWorker" in navigator)) return;
    try {
      navigator.serviceWorker.getRegistration().then(reg => {
        if (!reg) return;
        if (reg.getNotifications) {
          reg.getNotifications().then(notes => {
            notes.forEach(n => { try { n.close(); } catch (e) {} });
          }).catch(() => {});
        }
        if (reg.active) {
          try { reg.active.postMessage({ type: "clear_all" }); } catch (e) {}
        }
      }).catch(() => {});
    } catch (e) {}
  }

  // 앱 visibility 변화 — visible 일 때만 현재 방 활성으로, hidden 이면 클리어 (대표 지시 2026-05-26)
  document.addEventListener("visibilitychange", () => {
    try {
      if (document.visibilityState === "visible") {
        // 활성 방 알림 → SW 가 같은 방 푸시 시 알림 생략
        if (activeRoom && activeRoom.id) {
          _notifySWActiveRoom(activeRoom.id);
          _clearRoomNotifications(activeRoom.id);
        } else {
          _notifySWActiveRoom(null);
          _clearAllNotifications();
        }
      } else {
        // 페이지 hidden — SW 가 모든 방 알림을 정상 발생시키도록 활성 방 클리어
        _notifySWActiveRoom(null);
      }
    } catch (e) {}
  });
  // 윈도우 포커스 — 데스크톱 알림 잔존 시
  window.addEventListener("focus", () => {
    try {
      if (activeRoom && activeRoom.id) {
        _notifySWActiveRoom(activeRoom.id);
        _clearRoomNotifications(activeRoom.id);
      }
    } catch (e) {}
  });
  // 윈도우 blur (다른 앱·탭으로 이동) — SW 활성 방 클리어
  window.addEventListener("blur", () => {
    try { _notifySWActiveRoom(null); } catch (e) {}
  });

  // 방별 자동번역 모드 (localStorage 영속화)
  // 값: "" (OFF) | "vi" | "en" | "ko"
  function getRoomTranslateMode(roomId) {
    try { return localStorage.getItem(`knkmsg.tr.room.${roomId}`) || ""; }
    catch (e) { return ""; }
  }
  function setRoomTranslateMode(roomId, lang) {
    try { localStorage.setItem(`knkmsg.tr.room.${roomId}`, lang || ""); }
    catch (e) { }
  }

  // 부서명 → 법인 ("KOR" 본사 / "VN" 베트남 / "" 그 외) (대표 지시 2026-06-04)
  function _corpOfDept(d) {
    var sk = (typeof deptSortKey === "function") ? deptSortKey(d || "") : (d || "");
    if (sk.indexOf("01_KOR/") === 0) return "KOR";
    if (sk.indexOf("02_VN/") === 0) return "VN";
    return "";
  }
  // 법인별 자동 번역 언어 — 본사 직원↔베트남 직원이 함께 있는 방(1:1 포함)에서만 ON.
  //   본사(KOR) 직원 → 'vi'(베트남어), 베트남(VN) 직원 → 'ko'(한국어). 그 외/외부 게스트/중국 섞이면 "" (대표 지시 2026-06-04)
  function computeAutoTranslateLang(room) {
    // '메신저 불편 신고' 채널은 자동번역 안 함 — 기본 OFF (사용자가 직접 켜면 manual 플래그로 유지) (대표 지시 2026-06-04)
    if (room && window.__BUG_ROOM_ID__ && room.id === window.__BUG_ROOM_ID__) return "";
    var members = (roomReadStatus && roomReadStatus.members) || [];
    var meMember = members.find(function (m) { return m && m.user_id === meId; });
    var _app = document.getElementById("app");
    var myDept = (meMember && meMember.department) || (_app && _app.dataset ? _app.dataset.meDept : "") || "";
    var myCorp = _corpOfDept(myDept);
    if (myCorp !== "KOR" && myCorp !== "VN") return "";       // 내 법인 불명 → 자동 없음
    var others = members.filter(function (m) { return m && m.user_id !== meId; });
    if (!others.length) return "";                            // 멤버 정보 없음 / 나뿐
    // 나 외 전원이 본사·베트남 직원이고 외부 게스트가 없을 때만 (외부·중국 섞이면 자동 안 함)
    var pure = others.every(function (m) { return !m.is_guest && (_corpOfDept(m.department) === "KOR" || _corpOfDept(m.department) === "VN"); });
    if (!pure) return "";
    var hasVN = others.some(function (m) { return _corpOfDept(m.department) === "VN"; });
    var hasKOR = others.some(function (m) { return _corpOfDept(m.department) === "KOR"; });
    if (myCorp === "KOR") return hasVN ? "vi" : "";           // 본사 나 + 베트남 상대 → 베트남어
    return hasKOR ? "ko" : "";                                 // 베트남 나 + 본사 상대 → 한국어
  }

  function applyComposerLangUI() {
    if (!activeRoom || !els.composerLangbar) return;
    // 中文 칩 — 직원·고객 모두 표시 (대표 지시 2026-06-01, 어제 '고객사 전용' 한정 해제)
    const _zhChip = els.composerLangbar.querySelector('.cl-chip[data-lang="zh"]');
    if (_zhChip) _zhChip.style.display = "";
    const mode = getRoomTranslateMode(activeRoom.id);
    els.composerLangbar.querySelectorAll(".cl-chip").forEach(c => {
      c.dataset.active = (c.dataset.lang === mode) ? "1" : "0";
    });
    // 컴포저 보더 색 — 시각적 안전망
    const composer = $("composer");
    composer.classList.remove("tr-vi", "tr-en", "tr-ko");
    if (mode) composer.classList.add("tr-" + mode);
    // 힌트 텍스트 — UI 언어로 표시 (대표 지시 2026-05-29). t() 는 치환 미지원이라 {lang} 직접 교체.
    const _T = (k, fb) => (window.KNK_t ? window.KNK_t(k, fb) : fb);
    const _langFb = { vi: "베트남어", en: "영어", ko: "한국어", zh: "中文" };
    const langName = mode ? _T("lang." + mode, _langFb[mode] || mode) : "";
    const hint = mode
      ? _T("composer.autoHint", "🌐 자동 번역 ON ({lang}) — 원문+번역이 함께 발송").replace("{lang}", langName)
      : "";
    if (els.composerLangHint) els.composerLangHint.innerHTML = hint ? ('<span class="cl-pill">' + escapeHtml(hint) + '</span>') : "";
    // placeholder 도 UI 언어로
    els.msgInput.placeholder = mode
      ? _T("composer.placeholderTr", "메시지 입력... (자동 번역 ON)")
      : _T("composer.placeholder", "메시지 입력...");
  }

  // 메시지 입력 textarea 의 높이를 콘텐츠에 맞춰 자동 조절.
  // 데스크톱 max 240px(약 10줄) / 모바일 max 200px. 그 이상은 textarea 내부 스크롤.
  function autoGrowMsgInput() {
    const ta = els.msgInput;
    if (!ta || ta.tagName !== "TEXTAREA") return;
    ta.style.height = "auto";              // 일단 초기화해야 scrollHeight 가 정확
    const max = window.matchMedia("(pointer: coarse)").matches ? 200 : 240;
    ta.style.height = Math.min(ta.scrollHeight, max) + "px";
  }

  async function send() {
    // 스티커 미리보기가 열려 있으면 Enter·보내기 버튼 → 스티커 전송 (텍스트 전송 무시)
    if (typeof _spPreviewFile !== "undefined" && _spPreviewFile) {
      sendSticker(_spPreviewFile);
      _hideStickerPreview();
      return;
    }
    const text = els.msgInput.value.trim();

    // 📎 담긴 첨부가 있으면 먼저 전송 (확인 후 보내기 — 대표 지시 2026-05-29)
    if (_pendingFiles && _pendingFiles.length) {
      if (!activeRoom) return;
      const files = _pendingFiles.slice();
      const albumMode = _pendingAlbumMode;
      _clearPendingFiles();
      const imgCount = files.filter(f => (f.type || "").startsWith("image/")).length;
      if (albumMode && imgCount >= 2) {
        const albumId = (window.crypto && crypto.randomUUID)
          ? crypto.randomUUID()
          : `alb_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
        await uploadFiles(files, { albumId });
      } else {
        await uploadFiles(files);
      }
      if (!text) return;   // 파일만 → 종료. 텍스트도 있으면 아래로 이어서 전송
    }

    if (!text || !activeRoom) return;

    const mode = getRoomTranslateMode(activeRoom.id);

    if (!mode) {
      // 평소 동작 — 빠른 socket 송신 (인용 답장이면 quoted_message_id 포함)
      const payload = { room_id: activeRoom.id, content: text };
      if (_pendingQuoteMid) payload.quoted_message_id = _pendingQuoteMid;
      if (_pendingWhisperUid) payload.whisper_to_user_id = _pendingWhisperUid;
      // ★ 전송 확인(ack) — 서버가 받으면 콜백. 8초 내 확인 없으면 경고 + 텍스트 복원. (대표 지시 2026-05-23)
      //   네트워크 끊긴 순간 전송돼 유실되거나, 보낸 줄 알았는데 실제 미전송되는 경우 방지.
      const _sentText = text;
      let _ackDone = false;
      const _ackTimer = setTimeout(() => {
        if (_ackDone) return;
        _ackDone = true;
        // 입력창이 비어 있을 때만 복원 (그새 새로 타이핑했으면 덮어쓰지 않음)
        if (!els.msgInput.value.trim()) { els.msgInput.value = _sentText; autoGrowMsgInput(); }
        alert(window.KNK_t("alert.sendUnconfirmed"));
      }, 8000);
      try {
        socket.emit("send", payload, () => { _ackDone = true; clearTimeout(_ackTimer); });
      } catch (e) {
        _ackDone = true; clearTimeout(_ackTimer);
      }
      els.msgInput.value = "";
      autoGrowMsgInput();              // 높이 초기화
      cancelQuoteReply();               // 인용 미리보기 영역 제거
      cancelWhisperMode();              // 귓속말 모드 해제
      els.msgInput.focus();
      return;
    }

    // 자동 번역 모드 — REST 로 동기 호출 (1-3초 소요, 번역 비용 발생)
    els.sendBtn.disabled = true;
    const origPlaceholder = els.msgInput.placeholder;
    els.msgInput.placeholder = `번역 중... (${mode.toUpperCase()})`;
    els.msgInput.value = "";
    autoGrowMsgInput();              // 높이 초기화

    try {
      // 자동 번역 모드 — 인용 답장 / 귓속말 메타데이터를 같이 보내야 함 (대표 지시 2026-05-28 버그 수정).
      //   이전엔 payload 가 content + translate_to 만 있어 quote/whisper 가 사라져, 인용한 메시지가
      //   일반 텍스트로 전송되던 버그.
      const _sendPayload = { room_id: activeRoom.id, content: text, translate_to: [mode] };
      if (_pendingQuoteMid)  _sendPayload.quoted_message_id  = _pendingQuoteMid;
      if (_pendingWhisperUid) _sendPayload.whisper_to_user_id = _pendingWhisperUid;
      const r = await fetch(BASE + "/api/messages/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(_sendPayload),
      });
      const data = await r.json();
      if (!r.ok) {
        const errMsg = data.error || `HTTP ${r.status}`;
        // 번역 서비스 미설정 — langbar 자동 숨김 + 친절한 안내 (대표 지시 2026-05-19)
        if (errMsg.includes("번역") || errMsg.includes("ANTHROPIC") || errMsg.includes("translat")) {
          alert(window.KNK_t("alert.translateDisabled","번역 기능을 사용할 수 없습니다.\n\n관리자가 번역 API 를 설정한 후 사용할 수 있습니다.\n원문은 번역 없이 전송됩니다."));
          // langbar OFF 로 자동 전환
          try {
            _translateStatus = null;   // 캐시 클리어 → 다음 방 열 때 재조회
            if (els.composerLangbar) els.composerLangbar.hidden = true;
            // OFF 모드로 강제 전환
            if (typeof setComposerLang === "function") setComposerLang("");
          } catch(e) {}
          // 번역 없이 원문만 socketio 로 전송 (fallback)
          try {
            if (socket && socket.connected) {
              socket.emit("send", { room_id: activeRoom.id, content: text });
            }
          } catch(e) {}
        } else {
          alert(window.KNK_t("alert.sendFail","전송 실패") + ": " + errMsg + "\n" + (data.hint || ""));
          // 실패 시 원문 복원
          els.msgInput.value = text;
          autoGrowMsgInput();
        }
      }
      // 성공 시: socket new_message 가 자동으로 화면에 추가하므로 별도 처리 X.
      //   인용/귓속말 미리보기는 명시적으로 해제 (전송된 메시지에 이미 메타데이터 포함됨).
      if (r.ok) {
        cancelQuoteReply();
        cancelWhisperMode();
      }
    } catch (e) {
      alert(window.KNK_t("alert.sendFailed"));
      els.msgInput.value = text;
      autoGrowMsgInput();
    } finally {
      els.sendBtn.disabled = false;
      els.msgInput.placeholder = origPlaceholder;
      applyComposerLangUI();
      els.msgInput.focus();
    }
  }

  // ---------- 첨부 미리보기 + 묶음/개별 선택 ----------
  // 반환: { mode: 'album' | 'individual' | 'cancel' }
  // 사진 2장 이상 + 미리보기 다이얼로그 존재 시 사용자에게 묻는다. 아니면 'individual' 즉시 반환.
  function chooseAttachMode(files) {
    const dlg = document.getElementById("attachPreviewDialog");
    if (!dlg) return Promise.resolve({ mode: "individual" });
    const images = files.filter(f => (f.type || "").startsWith("image/"));
    const others = files.filter(f => !((f.type || "").startsWith("image/")));
    // 사진 2장 미만이면 묶을 게 없음 → 그냥 개별
    if (images.length < 2) return Promise.resolve({ mode: "individual" });

    const grid = dlg.querySelector("#apGrid");
    const summary = dlg.querySelector("#apSummary");
    const othersHint = dlg.querySelector("#apOthersHint");
    const btnIndiv = dlg.querySelector("#apIndividual");
    const btnAlbum = dlg.querySelector("#apAlbum");

    // 썸네일 그리드 채우기 — Object URL 로 즉시 미리보기 (업로드 후 revoke)
    const urls = [];
    grid.innerHTML = images.map((f, idx) => {
      const url = URL.createObjectURL(f);
      urls.push(url);
      return `<div class="ap-tile"><img src="${url}" alt="${escapeHtml(f.name)}" loading="lazy"></div>`;
    }).join("");
    summary.textContent = `사진 ${images.length}장${others.length ? ` + 다른 파일 ${others.length}개` : ""}`;
    othersHint.hidden = others.length === 0;
    btnIndiv.textContent = `개별 ${files.length}개 보내기`;
    btnAlbum.textContent = `📷 사진 ${images.length}장 앨범으로 묶기`;

    return new Promise(resolve => {
      let settled = false;
      const cleanup = () => {
        urls.forEach(u => { try { URL.revokeObjectURL(u); } catch (e) {} });
        btnIndiv.removeEventListener("click", onIndiv);
        btnAlbum.removeEventListener("click", onAlbum);
        dlg.removeEventListener("close-cancelled", onCancel);
        dlg.querySelectorAll("[data-close]").forEach(b => b.removeEventListener("click", onCancel));
      };
      const onIndiv = () => { if (settled) return; settled = true; dlg.close(); cleanup(); resolve({ mode: "individual" }); };
      const onAlbum = () => { if (settled) return; settled = true; dlg.close(); cleanup(); resolve({ mode: "album" }); };
      const onCancel = () => { if (settled) return; settled = true; dlg.close(); cleanup(); resolve({ mode: "cancel" }); };
      btnIndiv.addEventListener("click", onIndiv);
      btnAlbum.addEventListener("click", onAlbum);
      // .modal 의 [data-close] 버튼들 — 취소 처리
      dlg.querySelectorAll("[data-close]").forEach(b => b.addEventListener("click", onCancel));
      dlg.showModal();
    });
  }

  // ---------- file upload (with progress) ----------
  // opts.albumId — 있으면 이미지 파일들만 같은 album_id 로 묶어 업로드 (그리드 1메시지)
  // ─── 📎 첨부 대기(staging) — 선택 즉시 전송 대신 글틀 위에 담고 보내기/Enter 로 전송 (대표 지시 2026-05-29) ───
  let _pendingFiles = [];
  let _pendingAlbumMode = false;
  let _pendingUrls = [];   // 썸네일 ObjectURL — 정리용
  const _atT = (k, fb) => (window.KNK_t ? window.KNK_t(k, fb) : fb);
  function _revokePendingUrls() {
    _pendingUrls.forEach(u => { try { URL.revokeObjectURL(u); } catch (e) {} });
    _pendingUrls = [];
  }
  function _clearPendingFiles() {
    _pendingFiles = [];
    _pendingAlbumMode = false;
    renderPendingAttach();   // 내부에서 URL revoke + 바 숨김
  }
  function _stageFiles(files, albumMode) {
    _pendingFiles = Array.from(files);
    _pendingAlbumMode = !!albumMode;
    renderPendingAttach();
    try { els.msgInput.focus(); } catch (e) {}
  }

  // ===== 화면 캡처 + 붙여넣기 자동 이미지화 (대표 지시 2026-06-06) =====
  // 파일명용 타임스탬프 (브라우저 JS — new Date() 사용 가능)
  function _tsName() {
    const d = new Date();
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
  }
  // 입력창 커서 위치에 텍스트 삽입 (자동 이미지화 실패 시 텍스트 폴백용)
  function _insertTextAtCursor(ta, text) {
    if (!ta || !text) return;
    const s = (ta.selectionStart != null) ? ta.selectionStart : ta.value.length;
    const e2 = (ta.selectionEnd != null) ? ta.selectionEnd : ta.value.length;
    ta.value = ta.value.slice(0, s) + text + ta.value.slice(e2);
    const pos = s + text.length;
    try { ta.selectionStart = ta.selectionEnd = pos; } catch (_) {}
    try { ta.dispatchEvent(new Event("input", { bubbles: true })); } catch (_) {}
    try { ta.focus(); } catch (_) {}
  }
  // MediaStream 에서 한 프레임을 PNG blob 으로 (ImageCapture 미지원 브라우저 폴백)
  function _grabFrameViaVideo(stream) {
    return new Promise((resolve) => {
      try {
        const v = document.createElement("video");
        v.muted = true; v.playsInline = true; v.srcObject = stream;
        const done = (blob) => { try { v.pause(); } catch (_) {} resolve(blob); };
        v.onloadedmetadata = () => {
          v.play().then(() => {
            // 한 프레임 더 기다렸다가 그림 (검은 화면 방지)
            setTimeout(() => {
              try {
                const w = v.videoWidth || 1280, h = v.videoHeight || 720;
                const cv = document.createElement("canvas");
                cv.width = w; cv.height = h;
                cv.getContext("2d").drawImage(v, 0, 0, w, h);
                cv.toBlob((b) => done(b), "image/png");
              } catch (_) { done(null); }
            }, 220);
          }).catch(() => done(null));
        };
        v.onerror = () => done(null);
      } catch (_) { resolve(null); }
    });
  }
  // 클립보드 HTML 이 '시각적'인지 — 표/이미지/SVG/스타일 박스가 있으면 그림화 대상. 평범한 글자는 텍스트 유지.
  function _htmlLooksVisual(html) {
    if (!html) return false;
    const h = html.toLowerCase();
    if (/<(table|img|svg|figure|canvas|video)[\s>]/.test(h)) return true;
    const styledBoxes = (h.match(/style\s*=\s*["'][^"']*(background|border|grid-template|display\s*:\s*(flex|grid))/g) || []).length;
    return styledBoxes >= 2;
  }
  // 붙여넣은 HTML 조각에서 위험 요소 제거
  function _sanitizeHtmlFragment(html) {
    try {
      const doc = new DOMParser().parseFromString(html, "text/html");
      doc.querySelectorAll("script,style,link,meta,iframe,object,embed,noscript,title,base").forEach((n) => n.remove());
      doc.querySelectorAll("*").forEach((el) => {
        Array.prototype.slice.call(el.attributes).forEach((a) => {
          const n = a.name.toLowerCase();
          if (n.indexOf("on") === 0 || n === "srcset") el.removeAttribute(a.name);
        });
      });
      return doc.body ? doc.body.innerHTML : "";
    } catch (_) { return ""; }
  }
  // HTML -> PNG blob (브라우저 내장 SVG foreignObject + canvas, 외부 라이브러리 없음)
  //  한계: 복사된 HTML 은 원본 페이지의 CSS 가 안 따라오므로 인라인 스타일만 적용됨.
  //  외부(타 출처) 이미지가 섞이면 canvas 보안제약으로 실패 → 호출부에서 텍스트 폴백.
  async function _renderHtmlToPng(html) {
    const clean = _sanitizeHtmlFragment(html);
    if (!clean || !clean.trim()) return null;
    const W = 380;
    const embedStyle = `width:${W}px;padding:14px;box-sizing:border-box;background:#ffffff;color:#111827;font-family:'Noto Sans KR',system-ui,-apple-system,sans-serif;font-size:14px;line-height:1.6;word-break:break-word;`;
    const box = document.createElement("div");
    box.setAttribute("style", "position:fixed;left:-99999px;top:0;" + embedStyle);
    box.innerHTML = clean;
    document.body.appendChild(box);
    let H = 40;
    try { H = Math.min(4000, Math.max(40, box.scrollHeight)); } catch (_) {}
    // 임베드용 클론(화면밖 위치 스타일 제거)을 직렬화 — 원본은 화면밖 유지하다 제거(깜빡임 방지)
    const clone = box.cloneNode(true);
    clone.setAttribute("style", embedStyle);
    try { document.body.removeChild(box); } catch (_) {}
    let xhtml = "";
    try { xhtml = new XMLSerializer().serializeToString(clone); } catch (_) { xhtml = ""; }
    if (!xhtml) return null;
    if (xhtml.indexOf('xmlns="http://www.w3.org/1999/xhtml"') === -1) {
      xhtml = xhtml.replace(/^<([a-zA-Z0-9]+)/, '<$1 xmlns="http://www.w3.org/1999/xhtml"');
    }
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}"><foreignObject x="0" y="0" width="${W}" height="${H}">${xhtml}</foreignObject></svg>`;
    const url = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
    const img = new Image();
    await new Promise((resolve, reject) => { img.onload = resolve; img.onerror = reject; img.src = url; });
    const scale = 2;
    const cv = document.createElement("canvas");
    cv.width = W * scale; cv.height = H * scale;
    const ctx = cv.getContext("2d");
    ctx.fillStyle = "#ffffff"; ctx.fillRect(0, 0, cv.width, cv.height);
    ctx.scale(scale, scale);
    ctx.drawImage(img, 0, 0);
    // toBlob 은 오염(외부이미지)된 canvas 에서 예외 → 호출부 try 가 잡아 텍스트 폴백
    return await new Promise((resolve, reject) => {
      try { cv.toBlob((b) => resolve(b), "image/png"); } catch (err) { reject(err); }
    });
  }
  // 붙여넣은 HTML 을 그림으로 변환해 첨부. 실패하면 평범 텍스트로 폴백.
  async function _htmlToImageAttach(html, plainText) {
    try {
      const blob = await _renderHtmlToPng(html);
      if (blob && blob.size > 0) {
        const f = new File([blob], `붙여넣기_${_tsName()}.png`, { type: "image/png" });
        _stageFiles([..._pendingFiles, f], _pendingAlbumMode);
        try { _toast("붙여넣은 내용을 그림으로 첨부했어요. 전송을 누르면 보내집니다."); } catch (_) {}
        return;
      }
    } catch (_) {}
    // 폴백 — 텍스트로 (그림 변환 실패: 외부이미지 보안제약 등)
    _insertTextAtCursor(els.msgInput, plainText || "");
  }
  // 화면 캡처 한 프레임 → PNG File 로 첨부 (버튼·공통)
  async function _captureScreenAttach() {
    if (!activeRoom) return;
    if (!(navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia)) {
      try { _toast("이 기기·브라우저는 화면 캡처를 지원하지 않습니다. Win+Shift+S 로 캡처 후 붙여넣기 하세요."); } catch (_) {}
      return;
    }
    let stream = null;
    try {
      stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
      const track = stream.getVideoTracks()[0];
      let blob = null;
      try {
        if (window.ImageCapture && track) {
          const bmp = await new ImageCapture(track).grabFrame();
          const cv = document.createElement("canvas");
          cv.width = bmp.width; cv.height = bmp.height;
          cv.getContext("2d").drawImage(bmp, 0, 0);
          blob = await new Promise((res) => cv.toBlob(res, "image/png"));
        }
      } catch (_) { blob = null; }
      if (!blob) blob = await _grabFrameViaVideo(stream);
      if (blob) {
        const f = new File([blob], `캡처_${_tsName()}.png`, { type: "image/png" });
        _stageFiles([..._pendingFiles, f], _pendingAlbumMode);
        try { _toast("화면을 캡처했어요. 전송을 누르면 보내집니다."); } catch (_) {}
      } else {
        try { _toast("캡처에 실패했어요. 다시 시도해 주세요."); } catch (_) {}
      }
    } catch (err) {
      // 사용자가 공유 취소(NotAllowedError/AbortError)면 조용히 무시
      if (err && err.name !== "NotAllowedError" && err.name !== "AbortError") {
        try { _toast("화면 캡처 실패: " + (err.message || err.name)); } catch (_) {}
      }
    } finally {
      try { if (stream) stream.getTracks().forEach((t) => t.stop()); } catch (_) {}
    }
  }

  // 📷 별도 캡처 창 열기 — 화면 잡기 + 영역 잘라내기. 결과는 message 이벤트로 받아 첨부. (대표 지시 2026-06-06)
  function _openCaptureWindow() {
    if (!activeRoom) { try { _toast("먼저 대화방을 열어주세요."); } catch (_) {} return; }
    try {
      const sw = (window.screen && screen.availWidth) || 1200;
      const sh = (window.screen && screen.availHeight) || 800;
      const w = Math.min(1100, Math.round(sw * 0.7));
      const h = Math.min(820, Math.round(sh * 0.82));
      const left = Math.round((sw - w) / 2), top = Math.round((sh - h) / 3);
      const feat = `width=${w},height=${h},left=${left},top=${top},menubar=no,toolbar=no,location=no,status=no,resizable=yes,scrollbars=yes`;
      const win = window.open(BASE + "/capture", "knk_capture", feat);
      if (!win) { try { _toast("팝업이 차단됐어요. 이 사이트의 팝업을 허용한 뒤 다시 눌러주세요."); } catch (_) {} return; }
      try { win.focus(); } catch (_) {}
    } catch (e) { try { _toast("캡처 창 열기 실패: " + e); } catch (_) {} }
  }

  // 하단 배치일 때 검색·만들기 줄을 접기/펼치기 (대표 지시 2026-06-06)
  function _applyBottomCollapse(collapsed) {
    const sb = document.querySelector(".sidebar");
    if (sb) sb.classList.toggle("bottom-collapsed", !!collapsed);
    try { localStorage.setItem("knk_bottom_collapsed", collapsed ? "1" : "0"); } catch (e) {}
    const lab = document.getElementById("bottomBarHandleLabel");
    // 다국어 — i18n 키로 (대표 지시 2026-06-07). '불편신고'와 '펼치기' 여백 22px + 화살표 이모지.
    const _bt = (k, fb) => (window.KNK_t ? window.KNK_t(k, fb) : fb);
    if (lab) lab.innerHTML = collapsed
      ? _bt("bar.items", "✏️ 방만들기 · 📝 내메모장 · 🔍 검색 · 🙋 불편신고") + '<span style="margin-left:22px;">' + _bt("bar.expand", "펼치기") + ' 🔼</span>'
      : _bt("bar.collapse", "접기") + ' 🔽';
  }
  // 검색·만들기 줄 '아래 배치' 미리보기 전환 — 대표(사번5)만, 내 브라우저(localStorage)에만 적용 (대표 지시 2026-06-06)
  function _applySearchBottomLayout(on) {
    window._searchBottomLayout = !!on;
    try { localStorage.setItem("knk_search_bottom", on ? "1" : "0"); } catch (e) {}
    const sb = document.querySelector(".sidebar");
    if (sb) sb.classList.toggle("layout-search-bottom", !!on);
    if (els.layoutToggleBtn) els.layoutToggleBtn.classList.toggle("on", !!on);
    if (els.bottomBarHandle) els.bottomBarHandle.style.display = on ? "flex" : "none";
    if (on) {
      let _col = false;
      try { _col = localStorage.getItem("knk_bottom_collapsed") === "1"; } catch (e) {}
      _applyBottomCollapse(_col);
    } else if (sb) {
      sb.classList.remove("bottom-collapsed");
    }
    try { if (typeof renderRoomList === "function") renderRoomList(); } catch (e) {}
  }

  // ===== 묶음 메시지(글+그림 한 말풍선) — 붙여넣기 → 조각 → 미리보기 → 전송 (대표 지시 2026-06-06) =====
  let _mpParts = [];   // [{type:'text', text} | {type:'image', blob, url, name, mime, size}]

  // 클립보드 HTML 에 글과 섞인 '진짜 그림'(img/svg/canvas)이 있는지.
  //   표(table)·엑셀 붙여넣기는 글로 유지(번역·편집 보호) — 묶음 모드로 안 보냄. (대표 지시 2026-06-06)
  function _htmlHasEmbeddedVisual(html) {
    return !!html && /<(img|svg|canvas)[\s>]/i.test(html);
  }
  function _mpIsBlockTag(tag) {
    return /^(P|DIV|LI|UL|OL|H[1-6]|BLOCKQUOTE|PRE|SECTION|ARTICLE|HEADER|FOOTER|TR|THEAD|TBODY|HR|DD|DT|DL)$/.test(tag);
  }
  // HTML 을 순서 유지한 채 [텍스트런 / 시각노드] 로 조각냄
  function _splitHtmlToParts(html) {
    const doc = new DOMParser().parseFromString(html, "text/html");
    doc.querySelectorAll("script,style,link,meta,noscript,iframe,object,embed").forEach((n) => n.remove());
    const VISUAL = { IMG: 1, SVG: 1, CANVAS: 1 };   // 표/figure 는 글로 유지(엑셀 보호)
    const parts = [];
    let buf = "";
    const flush = () => {
      const t = buf.replace(/ /g, " ").replace(/[ \t]+/g, " ").replace(/ *\n */g, "\n").replace(/\n{3,}/g, "\n\n").trim();
      if (t) parts.push({ type: "text", text: t });
      buf = "";
    };
    const walk = (node) => {
      node.childNodes.forEach((child) => {
        if (child.nodeType === 3) { buf += child.nodeValue; return; }
        if (child.nodeType !== 1) return;
        const tag = child.tagName;
        if (tag === "BR") { buf += "\n"; return; }
        if (VISUAL[tag]) { flush(); parts.push({ type: "visual", node: child }); return; }
        const hasVisual = child.querySelector && child.querySelector("img,svg,canvas");
        if (hasVisual) {
          if (_mpIsBlockTag(tag)) buf += "\n";
          walk(child);
          if (_mpIsBlockTag(tag)) buf += "\n";
        } else {
          if (_mpIsBlockTag(tag)) buf += "\n";
          buf += child.textContent || "";
          if (_mpIsBlockTag(tag)) buf += "\n";
        }
      });
    };
    walk(doc.body || doc.documentElement);
    flush();
    return parts;
  }
  // <img> 노드에서 '진짜' 이미지 주소 고르기 — srcset(가장 큰 것)·data-src(게으른로딩)·src 순, 절대주소화
  function _bestImgUrl(node) {
    let best = node.currentSrc || node.getAttribute("src") || "";
    const dsrc = node.getAttribute("data-src") || node.getAttribute("data-original") || node.getAttribute("data-lazy-src") || "";
    const ss = node.getAttribute("srcset") || node.getAttribute("data-srcset") || "";
    if (ss) {
      let maxW = -1, maxUrl = "";
      ss.split(",").forEach((part) => {
        const seg = part.trim().split(/\s+/);
        const u = seg[0];
        const w = parseInt(String(seg[1] || "").replace(/[^\d]/g, ""), 10) || 0;
        if (u && w >= maxW) { maxW = w; maxUrl = u; }
      });
      if (maxUrl) best = maxUrl;
    }
    // src 가 1px 플레이스홀더(작은 data: gif/svg)면 data-src 사용
    if ((!best || /^data:image\/(gif|svg)/i.test(best) || best.length < 12) && dsrc) best = dsrc;
    try { best = new URL(best, node.baseURI || document.baseURI).href; } catch (_) {}
    return best;
  }
  // 이미지 주소 → blob. data:는 바로 / 같은출처·CORS는 직접 / 외부(CORS 막힘)는 서버 프록시
  async function _imgSrcToBlob(src) {
    if (!src) return null;
    if (/^data:/i.test(src)) {
      try { const r = await fetch(src); const b = await r.blob(); return (b && b.size > 0) ? b : null; } catch (_) { return null; }
    }
    try {
      const r = await fetch(src, { mode: "cors" });
      if (r.ok) { const b = await r.blob(); if (b && b.size > 0) return b; }
    } catch (_) {}
    if (/^https?:/i.test(src)) {
      try {
        const r = await fetch(BASE + "/api/fetch_remote_image?url=" + encodeURIComponent(src));
        if (r.ok) { const b = await r.blob(); if (b && b.size > 0 && (b.type || "").indexOf("image/") === 0) return b; }
      } catch (_) {}
    }
    return null;
  }
  // 시각노드 → 이미지 blob (img=주소 가져오기(+프록시) / 그 외=foreignObject 렌더)
  async function _visualNodeToBlob(node) {
    try {
      if (node.tagName === "IMG") {
        const b = await _imgSrcToBlob(_bestImgUrl(node));
        if (b && b.size > 0) return b;
        return null;   // img 인데 못 가져오면 foreignObject 는 오염으로 실패하므로 바로 null
      }
      return await _renderHtmlToPng(node.outerHTML);
    } catch (_) { return null; }
  }
  function _mpClear() {
    try { _mpParts.forEach((p) => { if (p.url) URL.revokeObjectURL(p.url); }); } catch (_) {}
    _mpParts = [];
    if (els.mpPreview) { els.mpPreview.hidden = true; els.mpPreview.innerHTML = ""; }
  }
  // 붙여넣기 → 조각 → 미리보기 시작
  async function _startMultipartPaste(html) {
    const raw = _splitHtmlToParts(html);
    if (!raw.length) return;
    _mpClear();
    let failedVisual = 0;
    for (const seg of raw) {
      if (seg.type === "text") {
        _mpParts.push({ type: "text", text: seg.text });
      } else if (seg.type === "visual") {
        const blob = await _visualNodeToBlob(seg.node);
        if (blob && blob.size > 0) {
          let ext = (blob.type && blob.type.split("/")[1]) || "png";
          if (ext === "jpeg") ext = "jpg";
          _mpParts.push({ type: "image", blob, url: URL.createObjectURL(blob), name: `붙여넣기_${_tsName()}.${ext}`, mime: blob.type || "image/png", size: blob.size });
        } else {
          failedVisual++;
        }
      }
    }
    const hasImage = _mpParts.some((p) => p.type === "image");
    if (!hasImage) {
      // 시각요소를 하나도 못 가져옴 → 그냥 텍스트 붙여넣기 (묶음 의미 없음)
      const joined = _mpParts.filter((p) => p.type === "text").map((p) => p.text).join("\n");
      _mpClear();
      _insertTextAtCursor(els.msgInput, joined);
      if (failedVisual > 0) { try { _toast("그림은 가져오지 못했어요. 📷 캡처 버튼을 쓰면 화면 그대로 넣을 수 있어요."); } catch (_) {} }
      return;
    }
    if (failedVisual > 0) { try { _toast(`일부 그림(${failedVisual}개)은 못 가져왔어요. 그건 📷 캡처로 넣어주세요.`); } catch (_) {} }
    _renderMpPreview();
  }
  function _renderMpPreview() {
    if (!els.mpPreview) return;
    if (!_mpParts.length) { _mpClear(); return; }
    const rows = _mpParts.map((p, i) => {
      const body = (p.type === "image")
        ? `<img class="mpp-thumb" src="${p.url}" alt="">`
        : `<div class="mpp-text">${escapeHtml(p.text)}</div>`;
      const tag = (p.type === "image") ? "🖼 그림" : "📝 글";
      return `<div class="mpp-row" data-idx="${i}"><span class="mpp-tag">${tag}</span>${body}<button type="button" class="mpp-del" data-idx="${i}" title="빼기">✕</button></div>`;
    }).join("");
    els.mpPreview.innerHTML =
      `<div class="mpp-head"><span class="mpp-title">📦 보낼 묶음 <b>${_mpParts.length}</b>조각 — 순서대로 한 말풍선으로 전송</span>` +
      `<span class="mpp-actions"><button type="button" class="mpp-cancel">취소</button><button type="button" class="mpp-send">보내기 ▶</button></span></div>` +
      `<div class="mpp-list">${rows}</div>`;
    els.mpPreview.hidden = false;
    els.mpPreview.querySelectorAll(".mpp-del").forEach((b) => b.addEventListener("click", () => {
      const idx = parseInt(b.dataset.idx, 10);
      const p = _mpParts[idx];
      if (p && p.url) { try { URL.revokeObjectURL(p.url); } catch (_) {} }
      _mpParts.splice(idx, 1);
      if (_mpParts.length) _renderMpPreview(); else _mpClear();
    }));
    const _c = els.mpPreview.querySelector(".mpp-cancel"); if (_c) _c.addEventListener("click", () => _mpClear());
    const _s = els.mpPreview.querySelector(".mpp-send"); if (_s) _s.addEventListener("click", () => _sendMultipart());
  }
  async function _sendMultipart() {
    if (!activeRoom || !_mpParts.length) return;
    const sendBtn = els.mpPreview ? els.mpPreview.querySelector(".mpp-send") : null;
    if (sendBtn) { sendBtn.disabled = true; sendBtn.textContent = "보내는 중…"; }
    try {
      const outParts = [];
      for (const p of _mpParts) {
        if (p.type === "text") {
          outParts.push({ type: "text", text: p.text });
        } else if (p.type === "image" && p.blob) {
          const fd = new FormData();
          fd.append("room_id", String(activeRoom.id));
          fd.append("file", p.blob, p.name || `img_${_tsName()}.png`);
          const resp = await fetch(BASE + "/api/upload_part", { method: "POST", body: fd });
          if (!resp.ok) throw new Error("그림 업로드 실패");
          const meta = await resp.json();
          if (meta.error) throw new Error(meta.error);
          outParts.push({ type: "image", file_path: meta.file_path, file_name: meta.file_name, file_size: meta.file_size, file_mime: meta.file_mime });
        }
      }
      if (!outParts.length) { _mpClear(); return; }
      const resp2 = await fetch(BASE + `/api/rooms/${activeRoom.id}/messages/multipart`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ parts: outParts }),
      });
      if (!resp2.ok) {
        let _msg = "전송 실패";
        try { const j = await resp2.json(); if (j && j.error) _msg = j.error; } catch (_) {}
        throw new Error(_msg);
      }
      _mpClear();   // 소켓 new_message 로 본인에게도 렌더됨
    } catch (err) {
      if (sendBtn) { sendBtn.disabled = false; sendBtn.textContent = "보내기 ▶"; }
      try { _toast("묶음 전송 실패: " + (err && err.message ? err.message : err)); } catch (_) {}
    }
  }
  function _fmtAttachSize(b) {
    if (b < 1024) return b + " B";
    if (b < 1024 * 1024) return (b / 1024).toFixed(0) + " KB";
    return (b / 1024 / 1024).toFixed(1) + " MB";
  }
  function renderPendingAttach() {
    const bar = document.getElementById("pendingAttach");
    if (!bar) return;
    _revokePendingUrls();
    if (!_pendingFiles.length) {
      bar.hidden = true;
      bar.innerHTML = "";
      return;
    }
    const imgCount = _pendingFiles.filter(f => (f.type || "").startsWith("image/")).length;
    const albumTag = (_pendingAlbumMode && imgCount >= 2)
      ? `<span class="pa-album">📷 ${escapeHtml(_atT("attach.albumTag", "앨범"))}</span>` : "";
    const tiles = _pendingFiles.map((f, i) => {
      const isImg = (f.type || "").startsWith("image/");
      let thumb;
      if (isImg) {
        const u = URL.createObjectURL(f); _pendingUrls.push(u);
        thumb = `<img class="pa-thumb" src="${u}" alt="">`;
      } else {
        thumb = `<span class="pa-fileicon">📄</span>`;
      }
      return `<div class="pa-item" title="${escapeHtml(f.name)}">
        ${thumb}
        <span class="pa-name">${escapeHtml(f.name)}</span>
        <span class="pa-size">${escapeHtml(_fmtAttachSize(f.size))}</span>
        <button type="button" class="pa-del" data-idx="${i}" title="${escapeHtml(_atT("attach.remove", "빼기"))}">✕</button>
      </div>`;
    }).join("");
    bar.innerHTML = `<div class="pa-head">📎 <span>${escapeHtml(_atT("attach.pendingLabel", "보낼 첨부"))}</span> <b>${_pendingFiles.length}</b>${albumTag}
        <button type="button" class="pa-clear">${escapeHtml(_atT("attach.clearAll", "전체 취소"))}</button></div>
      <div class="pa-list">${tiles}</div>`;
    bar.hidden = false;
  }

  async function uploadFiles(files, opts) {
    if (!activeRoom || !files || !files.length) return;
    // ★ FileList 류는 live 컬렉션일 수 있어 await 도중 항목이 사라질 수 있다.
    //   진입 시점에 정적 배열로 한 번 더 동결.
    const list = Array.from(files);
    files = list;
    const albumId = (opts && opts.albumId) || null;

    // 🛡️ 클라이언트 사전 검증 (대표 지시 2026-05-19 갱신) — 서버 거절 전에 미리 안내
    //   단일 파일 500MB, 요청당 전체 1GB, 동시 첨부 30개 (사진 일괄 업로드 고려)
    const PER_FILE_LIMIT = 500 * 1024 * 1024;    // 500MB
    const TOTAL_LIMIT    = 1000 * 1024 * 1024;   // 1GB (nginx client_max_body_size 와 정합)
    const COUNT_LIMIT    = 30;
    const oversize = files.filter(f => f.size > PER_FILE_LIMIT);
    if (oversize.length > 0) {
      const names = oversize.map(f => `• ${f.name} (${(f.size/1024/1024).toFixed(1)}MB)`).join("\n");
      alert(window.KNK_t("alert.fileOver500","다음 파일이 500MB 를 초과하여 업로드할 수 없습니다:") + "\n\n" + names + "\n\n" + window.KNK_t("alert.fileSplitHint","파일을 압축하거나 분할 후 다시 시도하세요."));
      return;
    }
    if (files.length > COUNT_LIMIT) {
      alert(window.KNK_t("alert.attachCountLimit","한 번에 최대 {limit}개까지 첨부 가능합니다. (선택: {n}개)").replace("{limit}", COUNT_LIMIT).replace("{n}", files.length) + "\n\n" + window.KNK_t("alert.splitSendHint","나눠서 보내주세요."));
      return;
    }
    const totalSize = files.reduce((s, f) => s + f.size, 0);
    if (totalSize > TOTAL_LIMIT) {
      alert(window.KNK_t("alert.attachTotalLimit","첨부 합계가 1GB 를 초과합니다 (현재 {mb}MB).").replace("{mb}", (totalSize/1024/1024).toFixed(1)) + "\n\n" + window.KNK_t("alert.splitSendHint","나눠서 보내주세요."));
      return;
    }

    // 진행률 표시 영역 — 메시지 영역 위에 떠있는 토스트
    const progBar = document.createElement("div");
    progBar.className = "upload-progress";
    progBar.innerHTML = `
      <div class="up-name"></div>
      <div class="up-track"><div class="up-fill"></div></div>
      <div class="up-pct">0%</div>
    `;
    document.body.appendChild(progBar);
    const $name = progBar.querySelector(".up-name");
    const $fill = progBar.querySelector(".up-fill");
    const $pct  = progBar.querySelector(".up-pct");

    const fmtMB = (b) => (b / 1024 / 1024).toFixed(1);

    let idx = 0;
    for (const f of files) {
      idx++;
      $name.textContent = `[${idx}/${files.length}] ${f.name} (${fmtMB(f.size)} MB)`;
      $fill.style.width = "0%";
      $pct.textContent = "0%";
      try {
        // 앨범 모드면 이미지 파일에만 album_id 부여 (서버도 image 만 album 적용)
        const isImage = (f.type || "").startsWith("image/");
        const fileAlbumId = (albumId && isImage) ? albumId : null;
        const res = await api.upload(activeRoom.id, f, (pct, loaded, total) => {
          $fill.style.width = pct + "%";
          $pct.textContent = `${pct}%  (${fmtMB(loaded)}/${fmtMB(total)} MB)`;
        }, fileAlbumId);
        if (res && res.error) {
          alert(window.KNK_t("alert.uploadFailFile","업로드 실패: {name}").replace("{name}", f.name) + "\n" + res.error);
        }
      } catch (e) {
        // e.error 가 이미 친절한 메시지(서버 응답 또는 status 별 안내) — 그대로 표시
        const msg = (e && e.error) || "네트워크 오류 — 연결을 확인해 주세요";
        alert(window.KNK_t("alert.uploadFailFile","업로드 실패: {name}").replace("{name}", f.name) + "\n" + msg);
      }
    }
    progBar.remove();
  }

  // ---------- new room dialog ----------
  function setTab(tab) {
    activeTab = tab;
    els.newRoomDialog.querySelectorAll(".tab").forEach(t => {
      t.classList.toggle("active", t.dataset.tab === tab);
    });
    els.newRoomDialog.querySelectorAll(".tab-pane").forEach(p => {
      p.classList.toggle("active", p.dataset.tabPane === tab);
    });
  }

  function userPickerHtml(u) {
    // 검색 필터링용 data 속성에 이름·직급·부서·username 평문 모두 포함 (대소문자 무관 검색)
    const dept = u.department || "";
    const deptLabel = dept ? (typeof deptDisplayLabel === "function" ? deptDisplayLabel(dept) : dept) : "";
    // 검색은 한/영 모두 매칭, 표시는 화면 언어 기준 (대표 지시 2026-05-25)
    const dTitle = _dispTitle(u), dDept = _dispDept(u), dName = _dispName(u);
    const haystack = [u.display_name, u.display_name_en, u.title, u.title_en, dept, deptLabel, u.department_en, u.username || ""].filter(Boolean).join(" ").toLowerCase();
    // 메타 라인 — '직급 · 부서' / 둘 다 없으면 username
    const metaParts = [];
    if (dTitle) metaParts.push(escapeHtml(dTitle));
    if (dDept) metaParts.push(escapeHtml(dDept));
    const metaText = metaParts.length ? metaParts.join(" · ") : escapeHtml(u.username || "");
    return `
      <label data-search="${escapeHtml(haystack)}">
        <input type="checkbox" value="${u.id}">
        <div class="avatar" style="width:27px;height:27px;font-size:calc(13px + var(--fs-add-ui));background:${u.avatar_color}">${_avatarBody(u)}</div>
        <div class="user-picker-info">
          <div class="user-picker-name">${escapeHtml(dName)}</div>
          <div class="user-picker-meta">${metaText}</div>
        </div>
      </label>`;
  }

  // 사용자 picker 를 '본사 / 베트남법인' 두 묶음으로 나눠 렌더 (대표 지시 2026-06-04)
  //   기준: 등록된 부서(_corpOfDept). VN = 베트남법인, 그 외(KOR·미분류) = 본사.
  //   입력 list 는 이미 부서순 정렬돼 있다고 가정 → 묶음 안 순서 유지. 한 묶음이 비면 그 헤더는 안 그림.
  function _groupedPickerHtml(list) {
    const arr = Array.isArray(list) ? list : [];
    const kor = [], vn = [];
    arr.forEach(u => {
      const corp = (typeof _corpOfDept === "function") ? _corpOfDept((u && u.department) || "") : "";
      (corp === "VN" ? vn : kor).push(u);
    });
    // 본사/베트남법인 '책갈피(탭)'로 분리 — 한 리스트에 안 나열 (대표 지시 2026-06-05)
    const korFirst = (kor.length > 0) || (vn.length === 0);   // 본사 우선, 본사 없으면 베트남
    const _tab = (key, label, n, active) =>
      `<button type="button" class="pick-tab${active ? " active" : ""}" data-pick-tab="${key}">${label} <span class="pick-tab-n">${n}</span></button>`;
    const _pane = (key, items, active) =>
      `<div class="pick-pane" data-pick-pane="${key}"${active ? "" : " hidden"}>${
        items.length ? items.map(userPickerHtml).join("") : '<div class="rs-hint" style="padding:14px;">해당 인원이 없습니다.</div>'
      }</div>`;
    return `<div class="pick-tabs">${_tab("kor", "🇰🇷 본사", kor.length, korFirst)}${_tab("vn", "🇻🇳 베트남법인", vn.length, !korFirst)}</div>`
         + `<div class="pick-scroll">` + _pane("kor", kor, korFirst) + _pane("vn", vn, !korFirst) + `</div>`;
  }

  // 사용자 picker 검색 필터 — 입력에 따라 행 hidden 토글 + 매칭 카운트 표시
  function _wireUserPickerSearch(searchInputId, pickerId, countId) {
    const input = document.getElementById(searchInputId);
    const picker = document.getElementById(pickerId);
    const countEl = document.getElementById(countId);
    if (!input || !picker) return;
    // 책갈피(탭) 구조면 '활성 탭(보이는 pane)' 안에서만 검색·필터 (없으면 picker 전체)
    const _activeScope = () => picker.querySelector(".pick-pane:not([hidden])") || picker;
    const update = () => {
      const q = input.value.trim().toLowerCase();
      const scope = _activeScope();
      const labels = scope.querySelectorAll("label[data-search]");
      let visible = 0;
      const total = labels.length;
      labels.forEach(lb => {
        const hay = lb.getAttribute("data-search") || "";
        const match = !q || hay.includes(q);
        lb.style.display = match ? "" : "none";
        if (match) visible++;
      });
      // 선택 인원 — 양쪽 탭(전체 picker) 합산 (탭 전환해도 선택 유지)
      const checked = picker.querySelectorAll('label[data-search] input:checked').length;
      if (countEl) {
        countEl.textContent = checked > 0
          ? `${checked}명 선택${q ? ` · 검색 ${visible}/${total}` : ""}`
          : (q ? `${visible}/${total}명` : `${total}명`);
      }
    };
    // 입력·체크 변화 시 카운트 갱신
    input.addEventListener("input", update);
    picker.addEventListener("change", update);
    // 책갈피 탭 전환 — 위임으로 1회 바인딩(picker innerHTML 교체돼도 유지) (대표 지시 2026-06-05)
    picker.addEventListener("click", (e) => {
      const tab = e.target.closest(".pick-tab");
      if (!tab || !picker.contains(tab)) return;
      const key = tab.getAttribute("data-pick-tab");
      picker.querySelectorAll(".pick-tab").forEach(t => t.classList.toggle("active", t === tab));
      picker.querySelectorAll(".pick-pane").forEach(p => { p.hidden = (p.getAttribute("data-pick-pane") !== key); });
      update();
    });
    // 최초 렌더 후 1회 카운트 표시
    requestAnimationFrame(update);
  }

  async function ensureUsers() {
    if (!users.length) users = await api.users();
    try { _updateMeHeaderInfo(); } catch(e) {}
    try { _refreshUsersTabCount(); } catch(e) {}
    return users;
  }

  // 👥 사용자 탭 인원수 — 총원(업무대화방 탭에서만) + 법인별 한국/베트남(사용자 탭에서만) (대표 지시 2026-06-06)
  // 호출 시점: ensureUsers() / 사용자 추가·삭제 후 / 페이지 로드 직후 / 사용자 탭 진입 시
  async function _refreshUsersTabCount() {
    try {
      const d = await api.usersCounts();
      _usersCorpCounts = { kor: d.kor || 0, vn: d.vn || 0, total: d.total || 0 };
    } catch (e) {
      _usersCorpCounts = { kor: null, vn: null, total: null };
    }
    try { _updateUsersTabCorp(); } catch (e) {}
  }

  async function openNewRoom() {
    await ensureUsers();
    // 사용자 목록을 부서 코드 → 이름 가나다 순으로 정렬
    // '_deleted_user' 플레이스홀더 + 비활성(퇴사) 사용자는 picker 에서 제외 (대표 지시 2026-05-20)
    const others = users.filter(u =>
      u.id !== meId
      && u.username !== "_deleted_user"
      && u.active !== 0
    ).slice().sort((a, b) => {
      const sa = (typeof deptSortKey === "function" ? deptSortKey(a.department || "") : (a.department || "zz"));
      const sb = (typeof deptSortKey === "function" ? deptSortKey(b.department || "") : (b.department || "zz"));
      if (sa !== sb) return sa.localeCompare(sb);
      return String(a.display_name || "").localeCompare(String(b.display_name || ""), "ko");
    });
    const html = _groupedPickerHtml(others);   // 본사/베트남법인 묶음 (대표 지시 2026-06-04)
    els.userPicker.innerHTML = html;
    els.itemUserPicker.innerHTML = html;
    { const chp = document.getElementById('channelUserPicker'); if (chp) chp.innerHTML = html; }
    els.roomName.value = "";
    // 입력·체크박스 초기화 — 직전 상태 잔존 방지
    { const _rnl = document.getElementById('roomNameLock'); if (_rnl) _rnl.checked = false;
      const _cn = document.getElementById('channelName'); if (_cn) _cn.value = "";
      const _cnl = document.getElementById('channelNameLock'); if (_cnl) _cnl.checked = true;
      const _cs = document.getElementById('channelUserSearch'); if (_cs) _cs.value = ""; }
    els.itemCustomer.value = "";
    els.itemCode.value = "";
    els.itemName.value = "";
    els.itemStatus.value = "active";
    els.itemDue.value = "";
    // 검색 입력 초기화 + wire (양쪽 picker)
    const us = document.getElementById("userSearch");
    const ius = document.getElementById("itemUserSearch");
    if (us) us.value = "";
    if (ius) ius.value = "";
    _wireUserPickerSearch("userSearch", "userPicker", "userPickerCount");
    _wireUserPickerSearch("itemUserSearch", "itemUserPicker", "itemUserPickerCount");
    _wireUserPickerSearch("channelUserSearch", "channelUserPicker", "channelUserPickerCount");
    // 관리번호 자동완성 wire — 1회만 바인딩
    if (typeof _setupItemCodeAutocomplete === "function") _setupItemCodeAutocomplete();
    // 모바일 검색 input focus 시 다이얼로그 자동 스크롤 wire (2026-05-20)
    if (typeof _setupMobilePickerAutoScroll === "function") _setupMobilePickerAutoScroll();
    // 채널 탭 — 관리자·대표이사·임원·팀장·법인장만 노출 (대표 지시 2026-05-24)
    const _chTab = els.newRoomDialog.querySelector('[data-tab="channel"]');
    if (_chTab) _chTab.style.display = window._meCanCreateChannel ? "" : "none";
    setTab("item");
    els.newRoomDialog.showModal();
    // 🚀 부서 퀵 만들기 — 채널 탭 부서 칩 렌더 (대표 지시 2026-05-28)
    if (typeof _renderDeptQuickChips === "function") _renderDeptQuickChips();
    // 프로젝트 탭 열린 후 검색 입력에 포커스 (바로 타이핑 가능)
    // 모바일에서는 자동 포커스 안 함 — 키보드가 즉시 올라와 다이얼로그를 가리는 문제 회피.
    // 사용자가 의도적으로 검색창 탭하면 그때 자동 스크롤.
    if (!window.matchMedia("(max-width: 720px)").matches) {
      setTimeout(() => { try { document.getElementById("itemUserSearch")?.focus(); } catch(e){} }, 50);
    }
  }

  // 🚀 부서 퀵 만들기 — 채널 다이얼로그 (대표 지시 2026-05-28)
  // 부서 칩 클릭 → 채널 이름 = 부서명, 멤버 = 그 부서 전원 + 본인 (체크박스 자동 체크)
  function _renderDeptQuickChips() {
    const grid = document.getElementById("deptQuickGrid");
    if (!grid) return;
    // 활성 사용자에서 부서별 그룹핑
    const deptMap = {};   // dept code -> { count, label, isVN }
    (users || []).forEach(u => {
      if (!u.active || u.username === "_deleted_user" || u.is_guest) return;
      const dept = u.department || "";
      if (!dept) return;
      if (!deptMap[dept]) {
        // 부서명 짧게 (예: '01_KOR/04_설계팀' → '설계팀')
        const short = dept.includes("/") ? dept.split("/").pop().replace(/^\d+_/, "") : dept;
        const isVN = (typeof _user_is_vietnam_dept === "function")
          ? _user_is_vietnam_dept(dept)
          : (dept.startsWith("02_VN/") || dept.startsWith("12-VN"));
        deptMap[dept] = { count: 0, label: short, isVN, code: dept };
      }
      deptMap[dept].count += 1;
    });
    // 정렬 — 본사 먼저 → 베트남, 그 안에서 부서 코드 순
    const depts = Object.values(deptMap).sort((a, b) => {
      if (a.isVN !== b.isVN) return a.isVN ? 1 : -1;
      return a.code.localeCompare(b.code);
    });
    grid.innerHTML = depts.map(d => `
      <button type="button" class="dept-quick-chip" data-dept-code="${escapeHtml(d.code)}" data-dept-label="${escapeHtml(d.label)}">
        <span class="dept-quick-flag">${d.isVN ? "🇻🇳" : "🇰🇷"}</span>
        <span class="dept-quick-name">${escapeHtml(d.label)}</span>
        <span class="dept-quick-count">${d.count}명</span>
      </button>
    `).join("");
    // 칩 클릭
    grid.querySelectorAll(".dept-quick-chip").forEach(btn => {
      btn.addEventListener("click", () => {
        const code = btn.dataset.deptCode;
        const label = btn.dataset.deptLabel;
        // 채널명 자동 입력
        const cn = document.getElementById("channelName");
        if (cn) cn.value = label;
        // 멤버 자동 체크 — 그 부서원 + 본인은 별도 자동 (체크리스트엔 안 보이지만 서버가 만든 사람을 호스트로 추가)
        const picker = document.getElementById("channelUserPicker");
        if (picker) {
          picker.querySelectorAll("input[type='checkbox']").forEach(cb => {
            const uid = parseInt(cb.value, 10);
            const u = (users || []).find(x => x.id === uid);
            cb.checked = !!(u && u.department === code);
          });
          // 검색 박스 비우기
          const cs = document.getElementById("channelUserSearch");
          if (cs) {
            cs.value = "";
            cs.dispatchEvent(new Event("input"));
          }
        }
        // 활성 chip 표시
        grid.querySelectorAll(".dept-quick-chip").forEach(b => b.classList.toggle("active", b === btn));
        // 안내문
        const pickedEl = document.getElementById("deptQuickPicked");
        if (pickedEl) {
          const cnt = (users || []).filter(u => u.department === code && u.active && u.username !== "_deleted_user" && !u.is_guest).length;
          pickedEl.textContent = `✓ "${label}" 부서원 ${cnt}명 자동 선택됨 — 추가·제외 가능`;
        }
      });
    });
  }

  // 모바일에서 참여자 검색 input focus 시 다이얼로그가 키보드 위로 자동 스크롤 (2026-05-20)
  //  v2: visualViewport API 로 키보드 높이를 정확히 측정 → 다이얼로그를 키보드 위 공간에 딱 맞춤.
  //      dvh(dynamic viewport height) 만으로는 안드로이드 일부 브라우저에서 키보드를 못 빼서
  //      참여자 박스가 한 줄만 보이는 문제 → visualViewport.height 로 강제 height 설정.
  let _vvKeyboardHandler = null;

  function _applyKeyboardAwareHeight() {
    const dlg = document.getElementById("newRoomDialog");
    if (!dlg || !dlg.open) return;
    if (!window.matchMedia || !window.matchMedia("(max-width: 720px)").matches) return;
    const content = dlg.querySelector(".modal-content");
    if (!content) return;
    if (window.visualViewport) {
      // visualViewport.height = 키보드 제외한 실제 보이는 높이
      // CSS 의 height:100dvh !important 를 이기려면 setProperty 로 important 부여 필수.
      const h = Math.round(window.visualViewport.height);
      content.style.setProperty("height", h + "px", "important");
      content.style.setProperty("max-height", h + "px", "important");
    }
  }

  function _resetKeyboardAwareHeight() {
    const dlg = document.getElementById("newRoomDialog");
    if (!dlg) return;
    const content = dlg.querySelector(".modal-content");
    if (!content) return;
    content.style.removeProperty("height");
    content.style.removeProperty("max-height");
  }

  function _setupMobilePickerAutoScroll() {
    if (!window.matchMedia || !window.matchMedia("(max-width: 720px)").matches) return;
    // visualViewport resize/scroll → 다이얼로그 height 동적 재계산 (1회만 바인딩)
    if (window.visualViewport && !_vvKeyboardHandler) {
      _vvKeyboardHandler = () => _applyKeyboardAwareHeight();
      window.visualViewport.addEventListener("resize", _vvKeyboardHandler);
      window.visualViewport.addEventListener("scroll", _vvKeyboardHandler);
    }
    ["itemUserSearch", "userSearch"].forEach(id => {
      const inp = document.getElementById(id);
      if (!inp || inp.dataset._mobScrollWired === "1") return;
      inp.dataset._mobScrollWired = "1";
      inp.addEventListener("focus", () => {
        // 키보드 올라오는 시간(약 300ms) 대기 후 height 재계산 + 검색창 위로 스크롤
        setTimeout(() => {
          _applyKeyboardAwareHeight();
          try {
            inp.scrollIntoView({ behavior: "smooth", block: "start" });
          } catch(_) {
            try { inp.scrollIntoView(); } catch(__) {}
          }
        }, 350);
      });
    });
  }

  // ============================================================
  // 📦 관리번호 자동완성 (대표 지시 2026-05-19)
  //   같은 관리번호이 이미 등록된 프로젝트에서 → 고객사·이름 자동 채움
  //   향후 HAIST WORKS 시스템 연동 시 백엔드 lookup endpoint 만 교체.
  // ============================================================
  let _itemCodeLookupSeq = 0;
  let _itemCodeLookupTimer = null;
  function _setupItemCodeAutocomplete() {
    const input = document.getElementById("itemCode");
    const box = document.getElementById("itemCodeSuggest");
    if (!input || !box) return;
    if (input._autoBound) return;   // 중복 wire 방지
    input._autoBound = true;

    const hide = () => { box.hidden = true; box.innerHTML = ""; };
    const fillFrom = (rec) => {
      // 클릭 시 3개 필드 자동 채움 — 사용자가 이미 입력 중인 값이 있어도 덮어씀
      if (els.itemCustomer && rec.customer) els.itemCustomer.value = rec.customer;
      if (els.itemCode && rec.code) els.itemCode.value = rec.code;
      if (els.itemName && rec.name) els.itemName.value = rec.name;
      // 상태·납기는 안전상 자동 채움 X (새 프로젝트은 새 상태로 시작)
      hide();
    };

    input.addEventListener("input", () => {
      const q = input.value.trim();
      clearTimeout(_itemCodeLookupTimer);
      if (q.length < 1) { hide(); return; }
      const seq = ++_itemCodeLookupSeq;
      _itemCodeLookupTimer = setTimeout(async () => {
        try {
          const url = `${BASE}/api/items/lookup?code=${encodeURIComponent(q)}&limit=8`;
          const res = await fetch(url).then(r => r.json());
          if (seq !== _itemCodeLookupSeq) return;   // 더 새 쿼리가 있으면 폐기
          if (!Array.isArray(res) || !res.length) { hide(); return; }
          box.innerHTML = res.map((rec, i) => {
            const customer = rec.customer || "(고객사 미정)";
            const name = rec.name || "";
            const src = rec.source === "haist_works" ? "🌐 HAIST" : "📁 메신저";
            return `<div class="code-suggest-item" data-idx="${i}">
              <div class="cs-code">${escapeHtml(rec.code || "")}</div>
              <div class="cs-meta">
                <span class="cs-customer">${escapeHtml(customer)}</span>
                <span class="cs-name">${escapeHtml(name)}</span>
                <span class="cs-source">${src}</span>
              </div>
            </div>`;
          }).join("");
          box.hidden = false;
          // 각 항목 클릭 → fillFrom
          box.querySelectorAll(".code-suggest-item").forEach(el => {
            el.addEventListener("mousedown", (ev) => {
              ev.preventDefault();   // blur 전에 처리되도록
              const idx = parseInt(el.dataset.idx, 10);
              if (!isNaN(idx) && res[idx]) fillFrom(res[idx]);
            });
          });
        } catch (e) { /* noop */ }
      }, 250);   // debounce 250ms
    });
    // blur 시 잠시 후 닫기 (mousedown 으로 클릭 처리 우선)
    input.addEventListener("blur", () => { setTimeout(hide, 150); });
    // ESC 로 닫기
    input.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") { hide(); }
    });
  }

  async function createRoom(e) {
    e.preventDefault();
    if (activeTab === "item") {
      const name = els.itemName.value.trim();
      if (!name) { alert(window.KNK_t("alert.projectNameRequired")); return; }
      const checked = [...els.itemUserPicker.querySelectorAll("input:checked")].map(c => parseInt(c.value, 10));
      const payload = {
        name,
        customer: els.itemCustomer.value.trim() || null,
        code: els.itemCode.value.trim() || null,
        status: els.itemStatus.value,
        due_date: els.itemDue.value || null,
        user_ids: [...checked, meId],
      };
      const res = await api.createItem(payload);
      if (res.error) { alert(res.error); return; }
      els.newRoomDialog.close();
      await refreshRooms();
      const room = rooms.find(r => r.id === res.room_id);
      if (room) openRoom(room);
    } else if (activeTab === "channel") {
      // 📢 채널 — 관리자만 생성 가능 (대표 지시 2026-05-20). 멤버 골라 채널(type=channel)로 생성, 이름 필수.
      if (!window._meCanCreateChannel) { alert(window.KNK_t("alert.channelPermDenied")); return; }
      const checked = [...document.querySelectorAll('#channelUserPicker input:checked')].map(c => parseInt(c.value, 10));
      if (!checked.length) { alert(window.KNK_t("alert.channelPickPeople")); return; }
      const nm = (document.getElementById('channelName')?.value || "").trim();
      if (!nm) { alert(window.KNK_t("alert.channelNameRequired")); return; }
      const payload = { user_ids: [...checked, meId], type: "channel", name: nm };
      if (document.getElementById('channelNameLock')?.checked) payload.name_locked = true;
      const res = await api.createRoom(payload);
      if (res.error) { alert(res.error); return; }
      els.newRoomDialog.close();
      await refreshRooms();
      const room = rooms.find(r => r.id === res.id);
      if (room) openRoom(room);
    } else {
      // 그룹 — 2명 이상 선택 필수. 1:1 은 사용자 목록 이름 클릭으로만 (대표 지시 2026-05-30)
      const checked = [...els.userPicker.querySelectorAll("input:checked")].map(c => parseInt(c.value, 10));
      if (checked.length < 2) {
        alert(window.KNK_t("alert.groupMin2", "그룹은 2명 이상 선택해야 합니다.\n1:1 대화는 사용자 목록에서 상대 이름을 눌러 시작하세요."));
        return;
      }
      const payload = { user_ids: [...checked, meId] };
      if (checked.length >= 2 && els.roomName.value.trim()) {
        payload.name = els.roomName.value.trim();
        // 이름 고정 체크박스 (그룹방만, 1:1 은 서버에서 무시)
        const lockEl = document.getElementById('roomNameLock');
        if (lockEl && lockEl.checked) payload.name_locked = true;
      }
      const res = await api.createRoom(payload);
      if (res.error) { alert(res.error); return; }
      els.newRoomDialog.close();
      await refreshRooms();
      const room = rooms.find(r => r.id === res.id);
      if (room) openRoom(room);
    }
  }

  // ---------- item edit ----------
  async function openItemEdit() {
    if (!activeRoom || activeRoom.type !== "item") return;
    const it = await api.getItem(activeRoom.id);
    if (it.error) { alert(it.error); return; }
    els.editCustomer.value = it.customer || "";
    els.editCode.value = it.code || "";
    els.editName.value = it.name || "";
    els.editStatus.value = it.status || "active";
    els.editDue.value = it.due_date ? it.due_date.slice(0, 10) : "";
    if (els.editKeepForever) els.editKeepForever.checked = !!it.keep_forever;
    els.itemEditDialog.showModal();
  }

  async function saveItemEdit(e) {
    e.preventDefault();
    if (!activeRoom) return;
    const payload = {
      customer: els.editCustomer.value.trim() || null,
      code: els.editCode.value.trim() || null,
      name: els.editName.value.trim() || activeRoom.name,
      status: els.editStatus.value,
      due_date: els.editDue.value || null,
      keep_forever: els.editKeepForever?.checked ? 1 : 0,
    };
    const res = await api.updateItem(activeRoom.id, payload);
    if (res.error) { alert(res.error); return; }
    els.itemEditDialog.close();
    await refreshRooms();
  }

  // ---------- 방 설정 (이름·별명·멤버·권한) ----------
  let _currentRoomSettings = null;  // { room, members, my_role, my_alias }

  function _badgeForRole(role) {
    if (role === 'host') return '<span class="rs-badge rs-host">' + window.KNK_t("rs.badgeHost") + '</span>';
    if (role === 'sub_host') return '<span class="rs-badge rs-sub">⭐ PM</span>';
    return '';
  }

  function _renderRoomSettings() {
    const data = _currentRoomSettings;
    if (!data) return;
    const { room, members, my_role, my_alias } = data;
    const isHost = my_role === 'host';   // effective — 채널에선 관리자(ceo)도 host 로 옴 (멤버관리·사진 등 공용)
    const iAmRealHost = (members || []).some(m => m.id === meId && m.role === 'host');   // 실제 이 방의 방장 본인 — '방 이름 변경'은 이걸로만 판단 (대표 지시 2026-06-04)
    const isCeo = (window._meRole === "ceo");   // 관리자
    const isSub = my_role === 'sub_host';
    const canInvite = isHost || isSub;
    const dlg = document.getElementById('roomSettingsDialog');
    const typeLabel = document.getElementById('rsRoomTypeLabel');
    typeLabel.textContent = room.type === 'item' ? window.KNK_t("rs.typeItem") : (room.type === 'direct' ? window.KNK_t("room.direct1to1") : window.KNK_t("rs.typeGroup"));

    // 이름 영역 — 맨 위에 음소거 토글 행 (모든 방 공통)
    const nameArea = document.getElementById('rsNameArea');
    const isMuted = notifySettings.isRoomMuted(room.id);
    let nameHtml = `
      <div class="rs-mute-row" style="display:flex;align-items:center;gap:10px;padding:10px 12px;background:${isMuted ? '#FEF2F2' : 'var(--surface)'};color:${isMuted ? '#1F2937' : 'var(--text)'};border:1px solid var(--border);border-radius:8px;margin-bottom:14px;cursor:pointer;" id="rsMuteRow">
        <span style="font-size:calc(22px + var(--fs-add-ui));">${isMuted ? '🔕' : '🔔'}</span>
        <div style="flex:1;">
          <div style="font-weight:600;font-size:calc(13px + var(--fs-add-ui));">${isMuted ? window.KNK_t("rs.muteOnTitle") : window.KNK_t("rs.muteOffTitle")}</div>
          <div style="font-size:calc(11.5px + var(--fs-add-ui));color:var(--text-soft);">${isMuted ? window.KNK_t("rs.muteOnDesc") : window.KNK_t("rs.muteOffDesc")}</div>
        </div>
        <button type="button" class="primary-btn" id="rsMuteToggleBtn" style="background:${isMuted ? '#10b981' : 'var(--accent)'};">${isMuted ? window.KNK_t("rs.muteOnBtn") : window.KNK_t("rs.muteOffBtn")}</button>
      </div>
    `;
    if (room.type === 'direct') {
      nameHtml += `<div class="rs-readonly">${window.KNK_t("rs.directNote")}</div>`;
    } else if (room.type === 'self') {
      // 내 메모장 — 이름은 고정(📝 내 메모장). 이름 입력란 미표시 (대표 지시 2026-05-20)
    } else if (iAmRealHost) {
      // 실제 방장 — 방 이름 변경 (정식). 이름 고정도 방장 권한. (대표 지시 2026-06-04: 방 이름은 방장만)
      nameHtml += `
        <div class="rs-name-row">
          <input id="rsRoomNameInput" type="text" maxlength="100" value="${escapeHtml(room.name || '')}" placeholder="방 이름">
          <button type="button" id="rsRenameBtn" class="primary-btn rs-save-btn">저장</button>
        </div>
        <label class="rs-checkbox">
          <input id="rsNameLockCheck" type="checkbox" ${room.name_locked ? 'checked' : ''}>
          <span>이름 고정 (멤버 별명 금지)</span>
        </label>
        <div class="rs-hint">방장 권한으로 모든 멤버에게 보이는 이름을 변경합니다.</div>
      `;
    } else if (isCeo) {
      // 관리자(방장 아님) — 강제 변경만 가능. 변경 시 방장에게 통보(방에 기록)됨. (대표 지시 2026-06-04)
      nameHtml += `
        <div class="rs-readonly">방 이름: <b>${escapeHtml(room.name || '(이름없음)')}</b></div>
        <div class="rs-name-row">
          <input id="rsRoomNameInput" type="text" maxlength="100" value="${escapeHtml(room.name || '')}" placeholder="방 이름">
          <button type="button" id="rsRenameBtn" class="primary-btn rs-save-btn" data-force="1" style="background:#b45309;">강제 변경</button>
        </div>
        <div class="rs-hint">🔒 <b>관리자 전용</b> — 방 이름은 원래 <b>방장만</b> 바꿀 수 있습니다. 관리자가 강제로 바꾸면 이 방에 기록이 남아 <b>방장에게 통보</b>됩니다.</div>
      `;
    } else if (!room.name_locked) {
      // 멤버 — 별명 가능
      nameHtml += `
        <div class="rs-readonly">원본 이름: <b>${escapeHtml(room.name || '(이름없음)')}</b></div>
        <div class="rs-form">
          <input id="rsAliasInput" type="text" maxlength="50" value="${escapeHtml(my_alias || '')}" placeholder="내 화면에서만 보일 별명">
          <button type="button" id="rsAliasSaveBtn" class="primary-btn">별명 저장</button>
          ${my_alias ? '<button type="button" id="rsAliasClearBtn" class="secondary-btn">초기화</button>' : ''}
        </div>
        <div class="rs-hint">내 화면에서만 보입니다. 다른 멤버에겐 영향 없음.</div>
      `;
    } else {
      // name_locked 멤버
      nameHtml += `<div class="rs-readonly">방 이름: <b>${escapeHtml(room.name || '')}</b><br><span class="rs-hint">이름 고정 — 방장만 변경 가능</span></div>`;
    }
    // 채널/방 아이콘 사진 — 방장 + 관리자 (대표 지시 2026-06-04: 방장도 가능하게)
    if ((isHost || isCeo) && room.type !== 'direct' && room.type !== 'self') {
      const curAv = room.avatar_url
        ? `<img src="${escapeHtml(room.avatar_url)}" style="width:46px;height:46px;border-radius:50%;object-fit:cover;border:1px solid var(--border);">`
        : `<div style="width:46px;height:46px;border-radius:50%;background:#e5e7eb;display:grid;place-items:center;font-size:10px;color:#9ca3af;text-align:center;line-height:1.1;">사진<br>없음</div>`;
      nameHtml += `
        <div class="rs-avatar-row">
          <div id="rsRoomAvatarPreview">${curAv}</div>
          <input type="file" id="rsRoomAvatarFile" accept="image/*" style="display:none;">
          <button type="button" id="rsRoomAvatarBtn" class="primary-btn rs-save-btn">사진 ${room.avatar_url ? '변경' : '올리기'}</button>
          ${room.avatar_url ? '<button type="button" id="rsRoomAvatarDelBtn" class="secondary-btn">제거</button>' : ''}
          <span class="rs-hint rs-hint-inline">🔒 방장·관리자만 변경 (jpg·png·webp·gif, 5MB)</span>
        </div>
      `;
    }
    nameArea.innerHTML = nameHtml;

    // 멤버 목록
    document.getElementById('rsMemberCount').textContent = members.length;
    const memberList = document.getElementById('rsMemberList');
    // (신고)채널 — 누구나 들어오고 로그인하면 무조건 보이는 열린 방이라 참여자 목록 섹션을 통째로 숨김 (대표 지시 2026-06-03)
    const _rsMemSec = document.getElementById('rsMemberSection');
    if (_rsMemSec) _rsMemSec.style.display = (room.id === window.__BUG_ROOM_ID__) ? 'none' : '';
    // 게스트(외부) 내보내기 권한 — 직원 kick 과 별개. _can_invite_guest 와 동일 규칙:
    //   direct(1:1) → 방 멤버 누구나 / group·item → 방장·PM·관리자 (대표 지시 2026-05-30)
    const canManageGuests = !window._meIsGuest && (isCeo || isHost || isSub || room.type === 'direct');
    const renderMemberRow = (m) => {
      const isMe = m.id === meId;
      const isGuestMember = !!m.is_guest;
      const canManage = isHost || isSub;   // 방장·PM 권한 동일 (대표 지시 2026-05-21)
      let actions = '';
      if (isGuestMember) {
        // ✏️ 대화방 표현 — 보는 사람 누구나(본인 화면 별칭). 클릭 시 입력칸 펼침. (대표 지시 2026-05-30 접기식)
        actions += `<button class="rs-act-btn rs-galias-edit-btn" data-act="galias-edit" data-uid="${m.id}" title="이 외부 사용자를 내 화면에서 부를 이름 지정">✏️<span class="rs-kick-txt"> 표현</span></button>`;
        // 외부(고객) 멤버 — '내보내기'(초대 회수 + 방 제거 + 계정 비활성)
        if (!isMe && canManageGuests) {
          actions += `<button class="rs-act-btn rs-danger" data-act="guest-remove" data-uid="${m.id}" title="외부(고객) 사용자를 방에서 내보내기 (초대 회수)">🚪<span class="rs-kick-txt"> 내보내기</span></button>`;
        }
      } else if (!isMe && canManage && m.role !== 'host') {
        // 방장(host) 대상은 강등·제외 불가 (위임으로만). 그 외 멤버는 방장·PM 이 관리.
        if (m.role === 'sub_host') {
          actions += `<button class="rs-act-btn" data-act="demote" data-uid="${m.id}" title="일반 멤버로 강등">⭐→👤</button>`;
        } else if (m.role === 'member') {
          actions += `<button class="rs-act-btn" data-act="promote" data-uid="${m.id}" title="PM 지정">⭐ PM</button>`;
        }
        // 방장 위임은 현재 방장(host)만 가능
        if (isHost) {
          actions += `<button class="rs-act-btn rs-danger" data-act="transfer" data-uid="${m.id}" title="방장 위임">👑 위임</button>`;
        }
        actions += `<button class="rs-act-btn rs-danger" data-act="kick" data-uid="${m.id}" title="이 멤버를 방에서 내보내기">🚪<span class="rs-kick-txt"> 제외</span></button>`;
      }
      // 직급·부서 메타 라인 (대표 지시 2026-05-19) — users 캐시에서 보강
      const cached = (Array.isArray(users) ? users.find(u => u.id === m.id) : null) || {};
      // 이름 — 한국어 모드에서 베트남 직원은 '베트남어 (한국식)' 병기 (대표 지시 2026-06-04). users 캐시에 display_name_vn 포함.
      const dispNm = (cached && cached.id) ? _dispName(cached) : (m.display_name || "");
      const metaTitle = cached.title || m.title || "";
      const metaDept = cached.department || m.department || "";
      const metaParts = [];
      if (metaTitle) metaParts.push(escapeHtml(metaTitle));
      if (metaDept) {
        const deptLabel = (typeof deptDisplayLabel === "function") ? deptDisplayLabel(metaDept) : metaDept;
        metaParts.push(escapeHtml(deptLabel));
      }
      const metaLine = metaParts.length ? `<div class="rs-member-meta">${metaParts.join(" · ")}</div>` : "";
      // 게스트(외부) '대화방 표현' — 보는 사람 본인 화면에서만 적용되는 개인 별칭 입력칸 (대표 지시 2026-05-30)
      //   직원은 다국어 이름/직급/부서가 자동 변환되지만 게스트는 안 돼서, 알아보기 쉽게 직접 적게 함.
      //   평소엔 접힘(.rs-guest-member 에 .editing 없을 때 CSS 로 숨김), ✏️ 표현 누르면 펼침.
      const guestAliasBox = isGuestMember ? `
        <div class="rs-guest-alias">
          <input type="text" class="rs-galias-input" data-uid="${m.id}" maxlength="40"
                 value="${escapeHtml(m.view_alias || '')}" data-orig="${escapeHtml(m.view_alias || '')}"
                 placeholder="대화방 표현 (내 화면에서만)"
                 autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false">
          <button type="button" class="rs-act-btn rs-galias-save" data-act="galias-save" data-uid="${m.id}">저장</button>
          <button type="button" class="rs-act-btn rs-galias-cancel" data-act="galias-cancel" data-uid="${m.id}">취소</button>
        </div>
        <div class="rs-galias-hint">💡 내 화면에서만 이 이름으로 보입니다. 다른 멤버·고객 본인에겐 영향 없음.</div>
      ` : '';
      // 별칭이 있으면 이름 옆에 작게 미리보기 (접힘 상태에서도 누구인지 알아보게)
      const _aliasPreview = isGuestMember
        ? ` <span class="rs-galias-preview"${m.view_alias ? '' : ' style="display:none;"'}>${m.view_alias ? '→ ' + escapeHtml(m.view_alias) : ''}</span>`
        : '';
      return `
        <div class="rs-member${isGuestMember ? ' rs-guest-member' : ''}">
          <div class="rs-member-info">
            <span class="avatar" style="background:${m.avatar_color};width:25px;height:25px;font-size:calc(12px + var(--fs-add-ui))">${_avatarBody(m)}</span>
            <div style="min-width:0;flex:1;">
              <div class="rs-member-name">${escapeHtml(dispNm)}${isGuestMember ? ' <span style="font-size:10px;color:#fff;background:#d4860a;border-radius:4px;padding:1px 5px;vertical-align:middle;">외부</span>' : ''}${isMe ? ' <span class="rs-me">(나)</span>' : ''}${_aliasPreview}</div>
              ${metaLine}
              <div class="rs-member-role">${_badgeForRole(m.role)}</div>
              ${guestAliasBox}
            </div>
          </div>
          ${actions ? `<div class="rs-member-actions">${actions}</div>` : ''}
        </div>
      `;
    };
    // ── 멤버 책갈피: 고객사(외부) / 케이엔케이 분리 (대표 지시 2026-05-31, 라벨 우리직원→케이엔케이) ──
    //   고객사(외부)가 한 명이라도 있는 방에서만 탭 표시. 기본 탭 = 고객사.
    //   외부 없는 일반 사내방은 지금처럼 단일 목록. data-act 버튼 이벤트는
    //   아래 memberList.querySelectorAll('[data-act]') 가 두 그룹 모두 연결.
    //   고객사(외부) / 본사 / 베트남 분리 (대표 지시 2026-06-05 — 케이엔케이를 본사·베트남으로 세분).
    //   비어있지 않은 그룹만 탭으로. 그룹 2개 이상 + 1:1·개인방 아닐 때만 탭, 아니면 단일 목록.
    //   data-act 버튼 이벤트는 아래 memberList.querySelectorAll('[data-act]') 가 모든 그룹을 한번에 연결.
    const _guestMembers = members.filter(m => m.is_guest);
    const _staffMembers = members.filter(m => !m.is_guest);
    const _memIsVn = (m) => {
      const _c = (Array.isArray(users) ? users.find(u => u.id === m.id) : null);
      const _dep = (_c && _c.department) || m.department || "";
      const _sk = (typeof deptSortKey === "function") ? deptSortKey(_dep) : _dep;
      return String(_sk).startsWith("02_VN/");
    };
    const _staffHq = _staffMembers.filter(m => !_memIsVn(m));
    const _staffVn = _staffMembers.filter(m => _memIsVn(m));
    const _memberTabs = document.getElementById('rsMemberTabs');
    const _mgroups = [];
    if (_guestMembers.length) _mgroups.push({ key: 'guest', label: '🤝 고객사', rows: _guestMembers });
    if (_staffHq.length)      _mgroups.push({ key: 'hq',    label: '🇰🇷 본사',  rows: _staffHq });
    if (_staffVn.length)      _mgroups.push({ key: 'vn',    label: '🇻🇳 베트남', rows: _staffVn });
    const _isDirectish = (room.type === 'direct' || room.type === 'self');
    if (_mgroups.length >= 2 && !_isDirectish && _memberTabs) {
      _memberTabs.style.display = 'flex';
      _memberTabs.innerHTML = _mgroups.map((g, i) =>
        `<button type="button" class="rs-mtab${i === 0 ? ' active' : ''}" data-mtab="${g.key}">${g.label} <span class="rs-mtab-n">${g.rows.length}</span></button>`
      ).join('');
      memberList.innerHTML = _mgroups.map((g, i) =>
        `<div class="rs-mgroup" data-mgroup="${g.key}"${i === 0 ? '' : ' style="display:none;"'}>${g.rows.map(renderMemberRow).join('')}</div>`
      ).join('');
      _memberTabs.querySelectorAll('.rs-mtab').forEach(tab => {
        tab.onclick = () => {
          const which = tab.dataset.mtab;
          _memberTabs.querySelectorAll('.rs-mtab').forEach(t => t.classList.toggle('active', t === tab));
          memberList.querySelectorAll('.rs-mgroup').forEach(g => {
            g.style.display = (g.dataset.mgroup === which) ? '' : 'none';
          });
        };
      });
    } else {
      if (_memberTabs) { _memberTabs.style.display = 'none'; _memberTabs.innerHTML = ''; }
      memberList.innerHTML = members.map(renderMemberRow).join('');
    }

    // 초대 버튼 — 1:1·self 방은 추가 불가. 그 외에는 invite_policy 에 따라:
    //   invite_policy === 'host_only' → host/sub_host 만
    //   invite_policy === 'all' (기본) → 모든 멤버 가능
    const policy = room.invite_policy || 'all';
    const canInviteByPolicy = (policy === 'host_only')
      ? (isHost || isSub)
      : true;  // 'all' — 모든 멤버 가능
    const showInviteBtn = canInviteByPolicy && room.type !== 'self' && room.type !== 'direct';
    document.getElementById('rsInviteArea').style.display = showInviteBtn ? 'block' : 'none';

    // 메시지 자동 삭제 (retention_days) — direct·self 제외 모든 방
    // 방장만 변경, 멤버는 현재값만 표시
    const retSec = document.getElementById('rsRetentionSection');
    const retArea = document.getElementById('rsRetentionArea');
    if (room.type === 'direct') {
      retSec.style.display = 'none';
    } else {
      retSec.style.display = '';
      const cur = (typeof room.retention_days === 'number' && room.retention_days > 0) ? room.retention_days : 0;
      const opts = [
        { v: 0,  label: '영구 보존', desc: '자동삭제 안 함' },
        { v: 1,  label: '24시간 후', desc: 'WhatsApp 식 — 보안용' },
        { v: 7,  label: '7일 후',    desc: '주간 정리' },
        { v: 30, label: '30일 후',   desc: '한 달 보존' },
        { v: 90, label: '90일 후',   desc: '분기 보존' },
      ];
      if (isHost) {
        retArea.innerHTML = `
          <div class="rs-form" style="flex-direction:column;align-items:stretch;gap:8px;">
            <select id="rsRetentionSelect" style="padding:8px;border:1px solid var(--border);border-radius:6px;font-size:calc(13px + var(--fs-add-ui));">
              ${opts.map(o => `<option value="${o.v}" ${o.v===cur?'selected':''}>${o.label} — ${o.desc}</option>`).join('')}
            </select>
            <button type="button" id="rsRetentionSaveBtn" class="primary-btn">자동삭제 정책 저장</button>
          </div>
          <div class="rs-hint">⚠ 설정 즉시 적용. 이미 지난 메시지는 다음 일일 정리에서 삭제됩니다.</div>
        `;
        document.getElementById('rsRetentionSaveBtn').onclick = async () => {
          const v = parseInt(document.getElementById('rsRetentionSelect').value, 10);
          const send = (v === 0) ? null : v;
          const res = await api.setRoomRetention(room.id, send);
          if (res && res.error) { alert(res.error); return; }
          await refreshRooms();
          await openRoomSettings(room.id);
        };
      } else {
        const o = opts.find(x => x.v === cur) || opts[0];
        retArea.innerHTML = `<div class="rs-readonly">현재 정책: <b>${o.label}</b> <span class="rs-hint">(방장만 변경 가능)</span></div>`;
      }
    }

    // 초대 권한 정책 — 1:1 / self 제외 모든 방
    const ipSec = document.getElementById('rsInvitePolicySection');
    const ipArea = document.getElementById('rsInvitePolicyArea');
    if (ipSec && ipArea) {
      if (room.type === 'direct' || room.type === 'self') {
        ipSec.style.display = 'none';
      } else {
        ipSec.style.display = '';
        const curPolicy = room.invite_policy || 'all';
        const labelOf = (p) => p === 'host_only' ? '👑 방장·PM만' : '👥 모든 멤버 가능 (기본)';
        if (canInvite) {
          ipArea.innerHTML = `
            <div class="rs-form" style="flex-direction:column;align-items:stretch;gap:8px;">
              <label class="rs-checkbox" style="display:flex;align-items:flex-start;gap:8px;cursor:pointer;padding:8px 10px;border:2px solid ${curPolicy === 'all' ? 'var(--accent)' : 'var(--border)'};border-radius:6px;background:${curPolicy === 'all' ? '#FEF2F2' : 'var(--surface)'};color:${curPolicy === 'all' ? '#1F2937' : 'var(--text)'};">
                <input type="radio" name="rsIp" value="all" ${curPolicy === 'all' ? 'checked' : ''} style="margin-top:3px;">
                <span>
                  <div style="font-weight:600;font-size:calc(13px + var(--fs-add-ui));">👥 모든 멤버 초대 가능 <span style="font-size:calc(11px + var(--fs-add-ui));color:var(--text-soft);">(기본)</span></div>
                  <div style="font-size:calc(11.5px + var(--fs-add-ui));color:var(--text-soft);">방의 누구나 새 멤버를 초대할 수 있음</div>
                </span>
              </label>
              <label class="rs-checkbox" style="display:flex;align-items:flex-start;gap:8px;cursor:pointer;padding:8px 10px;border:2px solid ${curPolicy === 'host_only' ? 'var(--accent)' : 'var(--border)'};border-radius:6px;background:${curPolicy === 'host_only' ? '#FEF2F2' : 'var(--surface)'};color:${curPolicy === 'host_only' ? '#1F2937' : 'var(--text)'};">
                <input type="radio" name="rsIp" value="host_only" ${curPolicy === 'host_only' ? 'checked' : ''} style="margin-top:3px;">
                <span>
                  <div style="font-weight:600;font-size:calc(13px + var(--fs-add-ui));">👑 방장·PM만 초대 가능</div>
                  <div style="font-size:calc(11.5px + var(--fs-add-ui));color:var(--text-soft);">일반 멤버는 초대 불가 — 폐쇄형 방</div>
                </span>
              </label>
              <button type="button" id="rsIpSaveBtn" class="primary-btn">초대 권한 저장</button>
            </div>
            <div class="rs-hint">⚠ 내보내기 권한은 항상 방장·PM만 가능 (이 설정과 무관).</div>
          `;
          document.getElementById('rsIpSaveBtn').onclick = async () => {
            const picked = document.querySelector('input[name="rsIp"]:checked')?.value || 'all';
            const res = await api.setRoomInvitePolicy(room.id, picked);
            if (res && res.error) { alert(res.error); return; }
            await refreshRooms();
            await openRoomSettings(room.id);
          };
        } else {
          ipArea.innerHTML = `<div class="rs-readonly">현재 정책: <b>${labelOf(curPolicy)}</b> <span class="rs-hint">(방장만 변경 가능)</span></div>`;
        }
      }
    }

    // 이벤트 wiring
    const renameBtn = document.getElementById('rsRenameBtn');
    if (renameBtn) renameBtn.onclick = async () => {
      const newName = document.getElementById('rsRoomNameInput').value.trim();
      if (!newName) { alert(window.KNK_t("alert.nameRequired")); return; }
      // 관리자 강제 변경(방장 아님) → 방장 통보 안내·확인 (대표 지시 2026-06-04)
      if (renameBtn.dataset.force === "1") {
        if (!confirm(window.KNK_t("confirm.forceRoomName","⚠️ 방 이름은 방장이 정하는 항목입니다.\n관리자 권한으로 강제 변경하면 이 방에 '관리자가 변경함' 기록이 남아 방장에게 통보됩니다.\n\n그래도 변경할까요?"))) return;
      }
      // 관리자 강제 변경 화면엔 '이름 고정' 체크박스가 없음 → 기존 값 유지
      const lockEl = document.getElementById('rsNameLockCheck');
      const locked = lockEl ? lockEl.checked : !!room.name_locked;
      const res = await api.renameRoom(room.id, newName, locked);
      if (res.error) { alert(res.error); return; }
      await refreshRooms();
      await openRoomSettings(room.id);  // 재로드
    };

    // 채널/방 아이콘 사진 업로드·제거 — 관리자 전용 (대표 지시 2026-05-20)
    const avBtn = document.getElementById('rsRoomAvatarBtn');
    const avFile = document.getElementById('rsRoomAvatarFile');
    if (avBtn && avFile) {
      avBtn.onclick = () => avFile.click();
      avFile.onchange = async () => {
        const file = avFile.files && avFile.files[0];
        if (!file) return;
        avBtn.disabled = true; avBtn.textContent = "처리 중...";
        try {
          // 어떤 사진이든 브라우저에서 정사각형 256px PNG 로 자동 리사이즈 → 크기·형식 걱정 없음
          let blob, fname;
          try { blob = await _resizeImageToSquareBlob(file, 256); fname = "avatar.png"; }
          catch (e) { blob = file; fname = file.name || "avatar.png"; }  // 리사이즈 불가 시 원본 업로드
          const fd = new FormData(); fd.append('file', blob, fname);
          const res = await fetch(`${BASE}/api/rooms/${room.id}/avatar`, { method: 'POST', body: fd })
            .then(r => r.json()).catch(() => ({ error: '업로드 실패' }));
          if (res.error) { alert(res.error); avBtn.disabled = false; avBtn.textContent = "아이콘 사진 올리기"; return; }
        } catch (e) {
          alert(window.KNK_t("alert.uploadError","업로드 오류") + ": " + (e.message || e));
          avBtn.disabled = false; avBtn.textContent = "아이콘 사진 올리기"; return;
        }
        await refreshRooms();
        await openRoomSettings(room.id);
      };
    }
    const avDel = document.getElementById('rsRoomAvatarDelBtn');
    if (avDel) avDel.onclick = async () => {
      if (!confirm(window.KNK_t("confirm.removeRoomIcon","아이콘 사진을 제거할까요? (기본 색 아이콘으로 돌아감)"))) return;
      const res = await fetch(`${BASE}/api/rooms/${room.id}/avatar`, { method: 'DELETE' })
        .then(r => r.json()).catch(() => ({ error: '삭제 실패' }));
      if (res.error) { alert(res.error); return; }
      await refreshRooms();
      await openRoomSettings(room.id);
    };

    const aliasSave = document.getElementById('rsAliasSaveBtn');
    if (aliasSave) aliasSave.onclick = async () => {
      const v = document.getElementById('rsAliasInput').value.trim();
      const res = v ? await api.setRoomAlias(room.id, v) : await api.clearRoomAlias(room.id);
      if (res.error) { alert(res.error); return; }
      await refreshRooms();
      await openRoomSettings(room.id);
    };
    const aliasClear = document.getElementById('rsAliasClearBtn');
    if (aliasClear) aliasClear.onclick = async () => {
      await api.clearRoomAlias(room.id);
      await refreshRooms();
      await openRoomSettings(room.id);
    };

    // 채널 삭제 (관리자 전용, 자동채널 제외) — 규칙 6 (대표 지시 2026-05-21)
    const chDelSec = document.getElementById('rsChannelDeleteSection');
    const chDelBtn = document.getElementById('rsChannelDeleteBtn');
    if (chDelSec && chDelBtn) {
      const roomFull = (rooms || []).find(r => r.id === room.id) || room;
      const canDeleteChannel = (roomFull.type === 'channel') && !roomFull.channel_scope
        && (isCeo || (window._meCanCreateChannel && room.created_by === meId));
      chDelSec.style.display = canDeleteChannel ? "" : "none";
      chDelBtn.onclick = async () => {
        const nm = roomFull.name || room.name || '이 채널';
        // 관리자가 '본인이 만들지 않은' 채널을 강제 삭제하면 방장 통보 안내 (대표 지시 2026-06-04)
        const _delForce = isCeo && !(window._meCanCreateChannel && room.created_by === meId);
        if (!confirm(window.KNK_t("confirm.deleteChannel","⚠ 채널 \"{name}\" 을(를) 영구 삭제할까요?\n모든 대화·첨부가 사라지며 되돌릴 수 없습니다.").replace("{name}", nm) + (_delForce ? window.KNK_t("confirm.deleteChannelForce","\n\n🔒 관리자 강제 삭제 — 방장에게 통보됩니다.") : ""))) return;
        const res = await fetch(`${BASE}/api/rooms/${room.id}`, { method: 'DELETE' }).then(r => r.json()).catch(e => ({ error: String(e) }));
        if (res.error) { alert("❌ " + res.error); return; }
        alert(window.KNK_t("alert.channelDeleted","✅ 채널이 삭제되었습니다") + ": " + res.deleted);
        document.getElementById('roomSettingsDialog')?.classList.remove('open');
        if (activeRoom && activeRoom.id === room.id) { activeRoom = null; app.classList.remove("viewing-chat"); }
        await refreshRooms();
      };
    }

    memberList.querySelectorAll('[data-act]').forEach(btn => {
      btn.onclick = async () => {
        const act = btn.dataset.act;
        const uid = parseInt(btn.dataset.uid, 10);
        const member = members.find(m => m.id === uid);
        if (!member) return;
        if (act === 'galias-edit') {
          // ✏️ 표현 — 입력칸 펼치고 포커스 (접기식, 대표 지시 2026-05-30)
          const row = btn.closest('.rs-member');
          if (row) {
            row.classList.add('editing');
            const inp = row.querySelector('.rs-galias-input');
            if (inp) { inp.focus(); inp.select(); }
          }
          return;
        }
        if (act === 'galias-cancel') {
          // 취소 — 원래값 복원하고 접기
          const row = btn.closest('.rs-member');
          if (row) {
            const inp = row.querySelector('.rs-galias-input');
            if (inp) inp.value = inp.dataset.orig || '';
            row.classList.remove('editing');
          }
          return;
        }
        if (act === 'galias-save') {
          // 게스트 '대화방 표현' 저장 — 내 화면에서만 적용. 저장 후 미리보기·채팅 작성자 줄 즉시 반영 + 접기. (대표 지시 2026-05-30)
          const row = btn.closest('.rs-member');
          const inp = row ? row.querySelector('.rs-galias-input') : memberList.querySelector(`.rs-galias-input[data-uid="${uid}"]`);
          const val = inp ? inp.value.trim() : '';
          btn.disabled = true;
          const res = await fetch(`${BASE}/api/rooms/${room.id}/guest_alias`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ guest_user_id: uid, alias: val }),
          }).then(r => r.json()).catch(e => ({ error: String(e) }));
          btn.disabled = false;
          if (res && res.error) { alert('❌ ' + res.error); return; }
          const saved = res.alias || '';
          // 이 방 멤버메타 갱신 → 열려있는 대화 작성자 줄 다시 그림
          if (window._roomMemberMeta && window._roomMemberMeta[uid]) window._roomMemberMeta[uid].view_alias = saved;
          if (member) member.view_alias = saved;
          // 미리보기(이름 옆 → 별칭) 갱신 + 접기
          if (row) {
            if (inp) inp.dataset.orig = saved;
            const pv = row.querySelector('.rs-galias-preview');
            if (pv) {
              if (saved) { pv.textContent = '→ ' + saved; pv.style.display = ''; }
              else { pv.textContent = ''; pv.style.display = 'none'; }
            }
            row.classList.remove('editing');
          }
          if (activeRoom && activeRoom.id === room.id) {
            try { const msgs = await api.messages(room.id); renderMessages(msgs); } catch (e) {}
          }
          return;   // 설정창 유지 (전체 재렌더 안 함)
        }
        if (act === 'promote') {
          await api.setMemberRole(room.id, uid, 'sub_host');
        } else if (act === 'demote') {
          await api.setMemberRole(room.id, uid, 'member');
        } else if (act === 'transfer') {
          if (!confirm(window.KNK_t("confirm.delegateOwner","[{name}] 님에게 방장을 위임합니다. 본인은 일반 멤버가 됩니다. 진행할까요?").replace("{name}", member.display_name))) return;
          await api.transferHost(room.id, uid);
        } else if (act === 'kick') {
          if (!confirm(window.KNK_t("confirm.kickMember","[{name}] 님을 방에서 내보낼까요?").replace("{name}", member.display_name))) return;
          await api.kickMember(room.id, uid);
        } else if (act === 'guest-remove') {
          if (!confirm(window.KNK_t("confirm.kickGuest","외부(고객) [{name}] 님을 방에서 내보낼까요?\n초대가 회수되어 같은 링크로 다시 들어올 수 없습니다.").replace("{name}", member.display_name))) return;
          const res = await fetch(`${BASE}/api/rooms/${room.id}/guest_members/${uid}`, { method: 'DELETE' })
            .then(r => r.json()).catch(e => ({ error: String(e) }));
          if (res && res.error) { alert('❌ ' + res.error); return; }
          await refreshRooms();
        }
        await openRoomSettings(room.id);
      };
    });

    // 👥 멤버 초대 — 게스트(외부)는 초대 권한 없음 + 초대정책 'host_only' 면 방장·PM만 (대표 지시 2026-05-30)
    const _rsInviteBtn = document.getElementById('rsInviteBtn');
    if (_rsInviteBtn) {
      const _policy = room.invite_policy || 'all';
      const _canInviteMember = !window._meIsGuest && (_policy === 'host_only' ? (isHost || isSub) : true);
      _rsInviteBtn.style.display = _canInviteMember ? '' : 'none';
      _rsInviteBtn.onclick = _canInviteMember ? (() => openInviteDialog(room.id, members)) : null;
    }

    // 음소거 토글 버튼 wire
    const muteBtn = document.getElementById('rsMuteToggleBtn');
    if (muteBtn) {
      muteBtn.onclick = () => {
        notifySettings.toggleRoomMute(room.id);
        renderRoomList();              // 사이드바 🔕 아이콘 갱신
        _renderRoomSettings();         // 다이얼로그 자체도 다시 그려서 상태 반영
      };
    }
    // 음소거 행 전체 클릭도 토글 (큰 영역 hit target)
    const muteRow = document.getElementById('rsMuteRow');
    if (muteRow) {
      muteRow.addEventListener('click', (e) => {
        if (e.target.closest('button')) return;   // 버튼 클릭 시는 위 onclick 가 처리
        notifySettings.toggleRoomMute(room.id);
        renderRoomList();
        _renderRoomSettings();
      });
    }

    if (!dlg.open) dlg.showModal();
  }

  async function openRoomSettings(roomId) {
    if (!roomId && activeRoom) roomId = activeRoom.id;
    if (!roomId) return;
    const data = await api.roomMembers(roomId);
    if (data.error) { alert(data.error); return; }
    _currentRoomSettings = data;
    _renderRoomSettings();
  }

  let _inviteSearchWired = false;   // 초대 검색창 이벤트 1회만 바인딩
  async function openInviteDialog(roomId, existingMembers) {
    const allUsers = await api.users();
    const existingIds = new Set(existingMembers.map(m => m.id));
    const candidates = allUsers.filter(u =>
      !existingIds.has(u.id) && u.id !== meId
      && u.username !== "_deleted_user" && u.active !== 0
    ).slice().sort((a, b) => {
      // 새 방 만들기 picker 와 동일 정렬 — 부서코드 → 이름 가나다
      const sa = (typeof deptSortKey === "function" ? deptSortKey(a.department || "") : (a.department || "zz"));
      const sb = (typeof deptSortKey === "function" ? deptSortKey(b.department || "") : (b.department || "zz"));
      if (sa !== sb) return sa.localeCompare(sb);
      return String(a.display_name || "").localeCompare(String(b.display_name || ""), "ko");
    });
    const picker = document.getElementById('invitePicker');
    if (!candidates.length) {
      picker.innerHTML = '<div class="rs-hint">초대 가능한 사용자가 없습니다 (모두 이미 멤버).</div>';
    } else {
      // 이름만이 아니라 직급·부서까지 함께 표기 (대표 지시 2026-05-20) — 새 방 picker 와 동일 포맷
      // 본사/베트남법인 묶음으로 구분 (대표 지시 2026-06-04)
      picker.innerHTML = _groupedPickerHtml(candidates);
    }
    // 멤버 검색창 — 열 때마다 초기화 + 검색 필터 연결 (1회만 바인딩) (대표 지시 2026-05-22)
    const inviteSearch = document.getElementById('inviteSearch');
    if (inviteSearch) inviteSearch.value = '';
    if (!_inviteSearchWired) {
      _wireUserPickerSearch('inviteSearch', 'invitePicker', 'invitePickerCount');
      _inviteSearchWired = true;
    } else if (inviteSearch) {
      inviteSearch.dispatchEvent(new Event('input'));   // 카운트·표시 갱신
    }
    const dlg = document.getElementById('inviteDialog');
    const confirmBtn = document.getElementById('confirmInvite');
    confirmBtn.onclick = async () => {
      const ids = [...picker.querySelectorAll('input:checked')].map(c => parseInt(c.value, 10));
      if (!ids.length) { alert(window.KNK_t("alert.invitePickPeople")); return; }
      const res = await api.inviteToRoom(roomId, ids);
      if (res.error) { alert(res.error); return; }
      dlg.close();
      await openRoomSettings(roomId);
    };
    dlg.showModal();
  }

  // ---------- gallery ----------
  async function openGallery(tab = "image") {
    if (!activeRoom) return;
    activeGalleryTab = tab;
    els.galleryTitle.textContent = `${activeRoom.name} — 사진·파일·타임라인`;
    els.galleryDialog.querySelectorAll(".gtab").forEach(t => {
      t.classList.toggle("active", t.dataset.gtab === tab);
    });
    if (tab === "timeline") {
      await renderTimeline();
      if (!els.galleryDialog.open) els.galleryDialog.showModal();
      return;
    }
    const data = await api.attachments(activeRoom.id, tab);
    if (!data.length) {
      els.galleryContent.innerHTML = `<div class="empty-state">${tab === "image" ? "사진이 없습니다." : "파일이 없습니다."}</div>`;
    } else if (tab === "image") {
      els.galleryContent.innerHTML = `<div class="gallery-grid">${data.map(m => `
        <div class="gallery-tile" data-src="${BASE}/uploads/${escapeHtml(m.file_path)}" data-name="${escapeHtml(m.file_name || "")}">
          <img src="${BASE}/uploads/${escapeHtml(m.file_path)}" loading="lazy" alt="${escapeHtml(m.file_name || "")}">
          <div class="tile-meta">${escapeHtml(m.display_name)} · ${fmtTime(m.created_at)}</div>
        </div>`).join("")}</div>`;
      // 갤러리 탭 — 모든 사진을 라이트박스 items 로 묶어 좌우 넘기기 가능하게
      const galleryTiles = Array.from(els.galleryContent.querySelectorAll(".gallery-tile"));
      const galleryItems = galleryTiles.map(t => ({
        src: t.dataset.src,
        name: t.dataset.name || "",
      }));
      galleryTiles.forEach((t, idx) => {
        t.addEventListener("click", () => {
          openLightbox(galleryItems, idx, null);
        });
      });
    } else {
      els.galleryContent.innerHTML = `<div class="gallery-files">${data.map(m => `
        <div class="gallery-file-row">
          <div class="file-icon">${fileIcon(m.file_name)}</div>
          <div class="file-info">
            <div class="file-name">${escapeHtml(m.file_name || "파일")}</div>
            <div class="file-meta">${escapeHtml(m.display_name)} · ${fmtTime(m.created_at)} · ${fmtSize(m.file_size)}</div>
          </div>
          <a href="${BASE}/uploads/${escapeHtml(m.file_path)}?dl=1" download="${escapeHtml(m.file_name || "")}">받기</a>
        </div>`).join("")}</div>`;
    }
    if (!els.galleryDialog.open) els.galleryDialog.showModal();
  }

  async function renderTimeline() {
    const data = await api.timeline(activeRoom.id);
    const events = [];
    for (const m of data.messages) {
      if (m.kind === "system") {
        events.push({ at: m.created_at, icon: "⚙", text: m.content, who: m.display_name });
      } else if (m.kind === "image") {
        events.push({ at: m.created_at, icon: "📷", text: `사진 — ${m.file_name || ""}`, who: m.display_name });
      } else if (m.kind === "file") {
        events.push({ at: m.created_at, icon: "📎", text: `파일 — ${m.file_name || ""}`, who: m.display_name });
      } else if (m.kind === "text") {
        const t = (m.content || "").slice(0, 100);
        events.push({ at: m.created_at, icon: "💬", text: t, who: m.display_name, type: "text" });
      }
    }
    for (const r of data.requests) {
      events.push({ at: r.created_at, icon: "📌", text: `요청 등록 — ${r.title}` + (r.assigned_to_name ? ` (담당 ${r.assigned_to_name})` : ""), who: r.requested_by_name });
      if (r.closed_at) {
        events.push({ at: r.closed_at, icon: "✅", text: `요청 ${r.status === "done" ? "완료" : "취소"} — ${r.title}`, who: r.assigned_to_name || r.requested_by_name });
      }
    }
    events.sort((a,b) => a.at.localeCompare(b.at));
    // 텍스트 메시지는 너무 많을 수 있어 같은 날 같은 사람은 1개만 표시
    const dayMap = new Map();
    for (const e of events) {
      const day = (e.at || "").slice(0, 10);
      if (!dayMap.has(day)) dayMap.set(day, []);
      dayMap.get(day).push(e);
    }
    if (dayMap.size === 0) {
      els.galleryContent.innerHTML = `<div class="empty-state">아직 활동이 없습니다.</div>`;
      return;
    }
    const days = [...dayMap.keys()].sort().reverse();
    els.galleryContent.innerHTML = `<div class="timeline">${days.map(day => {
      const list = dayMap.get(day);
      const dateLabel = new Date(day).toLocaleDateString("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit", weekday: "short" });
      // 같은 날 텍스트 메시지는 처음 5개만
      const filtered = [];
      let textCount = 0;
      for (const e of list) {
        if (e.type === "text") {
          textCount++;
          if (textCount <= 5) filtered.push(e);
        } else {
          filtered.push(e);
        }
      }
      const more = textCount > 5 ? `<div class="timeline-event"><div class="event-icon">…</div><div class="event-text" style="color:var(--text-soft)">+ 일반 메시지 ${textCount - 5}개 더</div></div>` : "";
      return `
        <div class="timeline-day">
          <div class="timeline-date">${dateLabel}</div>
          <div class="timeline-events">
            ${filtered.map(e => `
              <div class="timeline-event">
                <div class="event-icon">${e.icon}</div>
                <div class="event-text"><span class="who">${escapeHtml(e.who || "")}</span>${escapeHtml(e.text)}</div>
              </div>`).join("")}
            ${more}
          </div>
        </div>`;
    }).join("")}</div>`;
  }

  // ---------- digest ----------
  // "오늘 더 이상 열지 않기" — localStorage 에 날짜 저장. 같은 날(재실행·재로그인 포함) 자동 노출 차단,
  //  날짜 바뀌면 다시 뜸. (대표 지시 2026-05-23) — 수동 🌅 버튼은 이 설정과 무관하게 항상 열림.
  const DIGEST_DISMISS_KEY = "knkmsg.digestDismissDate";
  function _todayStr() {
    const d = new Date();
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }
  function _digestDismissedToday() {
    try { return localStorage.getItem(DIGEST_DISMISS_KEY) === _todayStr(); } catch (e) { return false; }
  }
  function _dismissDigestToday() {
    try { localStorage.setItem(DIGEST_DISMISS_KEY, _todayStr()); } catch (e) {}
  }
  async function openDigest(silent = false) {
    const d = await api.digest();
    const total = d.overdue.length + d.today_due.length + d.upcoming.length + d.requested_open.length;
    if (silent && total === 0) return;
    const sec = (title, items, cls = "") =>
      `<div class="digest-section">
        <h4>${title}</h4>
        ${items.length ? items.map(q => digestItemHtml(q, cls)).join("") : `<div class="digest-empty">없음</div>`}
      </div>`;
    let html = "";
    if (d.overdue.length) html += sec(`🔴 지연 ${d.overdue.length}건 — 먼저 처리하세요`, d.overdue, "overdue");
    if (d.today_due.length) html += sec(`🟠 오늘 마감 ${d.today_due.length}건`, d.today_due, "due-today");
    if (d.upcoming.length) html += sec(`🟡 이번 주 마감 ${d.upcoming.length}건`, d.upcoming, "upcoming");
    if (d.no_due_count) html += `<div class="digest-section"><h4>마감일 없는 내 작업</h4><div class="digest-empty">${d.no_due_count}건 — 📌 내 요청 탭에서 확인</div></div>`;
    if (d.requested_open.length) html += sec(`💜 내가 보낸 요청 — 진행 대기 ${d.requested_open.length}건`, d.requested_open, "requested");
    if (d.stale_items.length) html += sec(`💤 7일 이상 조용한 프로젝트`, d.stale_items.map(it => ({ id: 0, title: it.name, due_date: null, room_id: it.room_id, room_name: it.name, customer: it.customer, code: it.code })));
    if (!html) html = `<div class="empty-state" style="padding:32px;color:var(--text-soft)">오늘 챙길 항목이 없습니다. 🎉</div>`;
    els.digestContent.innerHTML = html;
    els.digestContent.querySelectorAll(".digest-item").forEach(li => {
      li.addEventListener("click", () => {
        const rid = parseInt(li.dataset.roomId, 10);
        const room = rooms.find(r => r.id === rid);
        els.digestDialog.close();
        if (room) openRoom(room);
      });
    });
    if (!els.digestDialog.open) els.digestDialog.showModal();
  }

  function digestItemHtml(q, cls) {
    const days = daysUntil(q.due_date);
    let dueText = "";
    if (q.due_date) {
      if (days < 0) dueText = `납기 ${fmtDate(q.due_date)} (${-days}일 지남)`;
      else if (days === 0) dueText = `오늘 마감!`;
      else if (days === 1) dueText = `내일 마감`;
      else dueText = `D-${days} (${fmtDate(q.due_date)})`;
    }
    const chips = [];
    if (q.customer) chips.push(`<span class="customer-chip">${escapeHtml(q.customer)}</span>`);
    if (q.code) chips.push(`<span class="code-chip">${escapeHtml(q.code)}</span>`);
    if (q.assigned_to_name) chips.push(`<span style="color:var(--text-soft)">담당 ${escapeHtml(q.assigned_to_name)}</span>`);
    return `
      <div class="digest-item ${cls}" data-room-id="${q.room_id}">
        <div class="digest-item-title">${escapeHtml(q.title)}</div>
        <div class="digest-item-meta">
          ${chips.join("")}
          <span style="font-weight:600">${escapeHtml(q.room_name || "")}</span>
          ${dueText ? `<span style="margin-left:auto">${dueText}</span>` : ""}
        </div>
      </div>`;
  }

  // ---------- requests ----------
  // ==========================================================
  //  멘션함 (@ 내게 온 멘션) — 대표 지시 2026-05-22
  //  헤더 @ 버튼 → 목록 → 항목 클릭 시 읽음 처리 + 해당 방·메시지로 이동·강조
  // ==========================================================
  function _setMentionBadge(count) {
    if (!els.mentionsBadge) return;
    const n = parseInt(count, 10) || 0;
    els.mentionsBadge.hidden = n === 0;
    els.mentionsBadge.textContent = n > 99 ? "99+" : n;
  }

  async function refreshMentionBadge() {
    try {
      const res = await api.mentionsUnreadCount();
      if (res && typeof res.unread_count === "number") _setMentionBadge(res.unread_count);
    } catch (e) { /* ignore */ }
  }

  // 📌 내 요청 칩 배지 — 나에게 배정된(받은) 미완료(진행 전·진행중) 요청 수 (대표 지시 2026-05-23)
  function _setMyTasksBadge(count) {
    if (!els.myTasksBadge) return;
    const n = parseInt(count, 10) || 0;
    els.myTasksBadge.hidden = n === 0;
    els.myTasksBadge.textContent = n > 99 ? "99+" : n;
  }
  async function refreshMyTasksBadge() {
    try {
      const data = await api.myRequests();
      if (!Array.isArray(data)) return;
      const n = data.filter(q => q.assigned_to === meId &&
        (q.status === "open" || q.status === "in_progress")).length;
      _setMyTasksBadge(n);
    } catch (e) { /* ignore */ }
  }

  function _mentionItemHtml(m) {
    const unread = !m.read_at;
    const dept = m.sender_dept ? (typeof deptShortLabel === "function" ? deptShortLabel(m.sender_dept) : m.sender_dept) : "";
    const sender = [m.sender_name, m.sender_title, dept].filter(Boolean).join(" ");
    const room = m.room_name || (m.room_type === "direct" ? window.KNK_t("room.direct1to1") : window.KNK_t("room.generic"));
    const when = m.created_at ? fmtTime(m.created_at) : "";
    const preview = (typeof renderTextWithMentions === "function")
      ? renderTextWithMentions(m.preview || "")
      : escapeHtml(m.preview || "");
    return `
      <div class="mention-item${unread ? ' unread' : ''}" data-mention-id="${m.id}">
        <div class="mention-main">
          <div class="mention-top">
            ${unread ? '<span class="mention-dot" title="안 읽음"></span>' : ''}
            <span class="mention-sender">${escapeHtml(sender)}</span>
            <span class="mention-room">📍 ${escapeHtml(room)}</span>
            <span class="mention-time">${escapeHtml(when)}</span>
          </div>
          <div class="mention-preview">${preview}</div>
        </div>
        <button type="button" class="mention-del" data-mention-del="${m.id}" title="이 멘션을 목록에서 삭제 (대화방 내용은 유지)">🗑</button>
      </div>`;
  }

  // 멘션함 — 사이드바 인라인 패널(#mentionsPanel)에 렌더. (대표 지시 2026-05-24: 팝업→페이지 통일)
  async function openMentions() {
    const panel = els.mentionsPanel;
    if (!panel) return;
    await ensureUsers();
    let data = null;
    try { data = await api.mentions(100); } catch (e) { data = null; }
    const items = (data && data.items) || [];
    const unread = (data && typeof data.unread_count === "number") ? data.unread_count : 0;
    _setMentionBadge(unread);
    const headerHtml = `
      <div class="mt-section-label" style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
        <span>${window.KNK_t("mention.title")} (${window.KNK_t("mention.unreadFmt").replace("{n}", unread)})</span>
        ${items.length ? `<span style="display:flex;gap:6px;flex-shrink:0;">
          <button type="button" class="secondary-btn" data-mp-readall style="font-size:calc(11px + var(--fs-add-ui));padding:3px 8px;">${window.KNK_t("mention.readAll")}</button>
          <button type="button" class="secondary-btn" data-mp-delall style="font-size:calc(11px + var(--fs-add-ui));padding:3px 8px;">${window.KNK_t("mention.delAll")}</button>
        </span>` : ``}
      </div>`;
    if (!items.length) {
      const myName = (((typeof users !== "undefined" && users) || []).find(u => u.id === meId) || {}).display_name || "내 이름";
      panel.innerHTML = headerHtml + `<div class="search-empty">${window.KNK_t("mention.empty")}<br><span style="font-size:calc(12px + var(--fs-add-ui));">${window.KNK_t("mention.emptyHint").replace("{name}", escapeHtml(myName))}</span></div>`;
    } else {
      panel.innerHTML = headerHtml + items.map(_mentionItemHtml).join("");
      // 행 클릭 → 해당 메시지로 이동 (삭제 버튼 클릭은 제외)
      panel.querySelectorAll("[data-mention-id]").forEach(row => {
        row.addEventListener("click", (e) => {
          if (e.target.closest("[data-mention-del]")) return;
          const m = items.find(x => x.id === parseInt(row.dataset.mentionId, 10));
          if (m) _gotoMention(m);
        });
      });
      // 삭제 버튼 → 안내 후 목록에서만 삭제 (대화방 내용은 유지)
      panel.querySelectorAll("[data-mention-del]").forEach(btn => {
        btn.addEventListener("click", async (e) => {
          e.stopPropagation();
          const id = parseInt(btn.dataset.mentionDel, 10);
          if (!confirm(window.KNK_t("mention.delConfirm"))) return;
          try {
            const res = await api.mentionDelete(id);
            if (res && typeof res.unread_count === "number") _setMentionBadge(res.unread_count);
          } catch (err) {}
          await openMentions();
        });
      });
    }
    // 헤더 — 모두 읽음 / 모두 삭제
    const _ra = panel.querySelector("[data-mp-readall]");
    if (_ra) _ra.addEventListener("click", async () => {
      try { const res = await api.mentionsReadAll(); _setMentionBadge((res && res.unread_count) || 0); } catch (e) {}
      await openMentions();
    });
    const _da = panel.querySelector("[data-mp-delall]");
    if (_da) _da.addEventListener("click", async () => {
      if (!confirm(window.KNK_t("mention.delAllConfirm"))) return;
      try { const res = await api.mentionsDeleteAll(); _setMentionBadge((res && res.unread_count) || 0); } catch (e) {}
      await openMentions();
    });
  }

  async function _gotoMention(m) {
    // 1) 읽음 처리 (배지 갱신)
    try {
      const res = await api.mentionRead(m.id);
      if (res && typeof res.unread_count === "number") _setMentionBadge(res.unread_count);
    } catch (e) {}
    // 2) 멘션함 닫기
    if (els.mentionsDialog && els.mentionsDialog.open) els.mentionsDialog.close();
    // 3) 해당 방 열기
    let room = (rooms || []).find(r => r.id === m.room_id);
    if (!room) { try { await refreshRooms(); } catch (e) {} room = (rooms || []).find(r => r.id === m.room_id); }
    if (!room) { alert(window.KNK_t("alert.mentionRoomNotFound","이 멘션이 있는 대화방을 찾을 수 없습니다 (방에서 나갔을 수 있습니다).")); return; }
    await openRoom(room, { jumpToMsgId: m.message_id });
    // 4) 해당 메시지로 점프 + 강조.
    //    openRoom 이 점프 모드라 '맨 아래로 강제 스크롤·입력창 자동포커스'를 안 함 → 더는 바닥으로 끌려가지
    //    않으므로 한 번만 이동해도 정확히 안착(깜빡임 없음). 첨부 이미지 로드로 위쪽이 밀리면 '멈춘 뒤 1번만'
    //    부드럽게 보정. _jumpTargetMsgId 가 풀리는 2.5초까지가 점프 창. (대표 지시 2026-06-02)
    const _sel = `.msg[data-msg-id="${m.message_id}"]`;
    let _flashed = false, _settleT = null;
    const _center = (smooth) => {
      const t = els.messages.querySelector(_sel);
      if (!t) return false;
      _userTouchedMessages = true;
      t.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "center" });
      if (!_flashed) {
        _flashed = true;
        t.classList.add("highlight-flash");
        setTimeout(() => { try { t.classList.remove("highlight-flash"); } catch (_) {} }, 2200);
      }
      return true;
    };
    if (!_center(false)) {                                  // 즉시 이동 (렌더 직후 없으면 잠깐 재시도)
      let _n = 0;
      const _iv = setInterval(() => { _n++; if (_center(false) || _n >= 15) clearInterval(_iv); }, 80);
    }
    const _reCenterSoon = () => {                           // 첨부 이미지 로드로 밀리면 '멈춘 뒤 1번만' 부드럽게
      if (!_jumpTargetMsgId) return;
      if (_settleT) clearTimeout(_settleT);
      _settleT = setTimeout(() => { if (_jumpTargetMsgId) _center(true); }, 120);
    };
    els.messages.querySelectorAll(".bubble img").forEach(img => {
      if (!img.complete || img.naturalHeight === 0) {
        img.addEventListener("load", _reCenterSoon, { once: true });
        img.addEventListener("error", _reCenterSoon, { once: true });
      }
    });
    setTimeout(() => { _jumpTargetMsgId = null; }, 2500);   // 점프 창 종료 → 정상 동작 복귀
  }

  // ===== 이 방의 스레드함 — 모달로 표시 (대표 지시 2026-05-27 재배치 / 2026-05-28 탭 2개로 확장) =====
  //   - 내 스레드 탭: 내가 답글 단 + 내 부모 메시지에 답글 달린 스레드
  //   - 방 전체 탭: 이 방 안의 모든 스레드 (답글 1개 이상)
  let _activeThreadTab = "my"; // 'my' | 'all'
  let _threadItemsCache = {};  // { parent_id: itemObj } — 🗑 핸들러가 t 정보 참조용

  function _downloadThreadXlsx(pid) {
    const url = `${BASE}/api/threads/${encodeURIComponent(pid)}/export.xlsx`;
    const a = document.createElement("a");
    a.href = url; a.style.display = "none";
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { try { a.remove(); } catch (_) {} }, 1000);
  }

  // 스레드 관리(연장/백업/삭제) 다이얼로그 — 대표 지시 2026-05-28 옵션 ②
  function openThreadManageDialog(parentId) {
    const t = _threadItemsCache[parentId];
    if (!t) return;
    // 상황 안내문 작성
    const lastWhen = t.last_reply_at || t.parent_created_at;
    const daysIdle = (() => {
      if (!lastWhen) return 0;
      const d = new Date(lastWhen);
      if (isNaN(d)) return 0;
      return Math.max(0, Math.floor((Date.now() - d.getTime()) / 86400000));
    })();
    const tt = (k, fb) => (window.KNK_t ? window.KNK_t(k) : fb);
    const title  = tt("thread.manage", "스레드 관리");
    const intro1 = (tt("thread.manageIntro", "이 스레드는 마지막 활동 후 {n}일이 지났습니다.")).replace("{n}", daysIdle);
    const intro2 = t.can_delete
      ? tt("thread.manageIntroDeletable", "보관 기간이 지나 삭제할 수 있습니다.")
      : tt("thread.manageIntroNotDeletable", "보관 기간이 아직 지나지 않아 지금은 삭제할 수 없습니다. 보관 연장만 가능합니다.");

    // 기존 다이얼로그 제거
    const existing = document.getElementById("threadManageDialog");
    if (existing) { try { existing.remove(); } catch (_) {} }
    const dlg = document.createElement("div");
    dlg.id = "threadManageDialog";
    dlg.className = "modal";
    dlg.setAttribute("data-modal", "");
    // 동적 생성된 모달에는 앱 초기화 시 박힌 close 메서드가 없음 → 직접 polyfill
    dlg.close = () => {
      dlg.classList.remove("open");
      dlg.removeAttribute("open");
      try { dlg.remove(); } catch (_) {}
    };
    try {
      Object.defineProperty(dlg, "open", {
        configurable: true,
        get() { return dlg.classList.contains("open"); },
      });
    } catch (_) {}
    dlg.showModal = () => { dlg.classList.add("open"); };
    const titleSafe = escapeHtml((t.parent_preview || "").slice(0, 80));
    dlg.innerHTML = `
      <div class="modal-content" style="max-width:480px;">
        <button type="button" class="close-x modal-close-x" data-close>✕</button>
        <h3>🗑 ${escapeHtml(title)}</h3>
        <div style="margin:10px 0 6px 0;font-size:calc(13.5px + var(--fs-add-ui));color:var(--text);line-height:1.5;">
          <div style="font-weight:600;margin-bottom:6px;">"${titleSafe}"</div>
          <div>${escapeHtml(intro1)}</div>
          <div style="margin-top:4px;color:var(--text-soft);">${escapeHtml(intro2)}</div>
        </div>
        <div style="display:grid;gap:8px;margin-top:16px;">
          ${t.can_extend ? `<button type="button" id="thrMgrExtend" class="thr-mgr-btn thr-mgr-extend">📅 ${escapeHtml(tt("thread.actExtend", "+30일 보관 연장"))}</button>` : ""}
          <button type="button" id="thrMgrBackup" class="thr-mgr-btn thr-mgr-backup">⬇ ${escapeHtml(tt("thread.actBackup", "엑셀로 백업"))}</button>
          ${t.can_delete ? `<button type="button" id="thrMgrDelete" class="thr-mgr-btn thr-mgr-delete">🗑 ${escapeHtml(tt("thread.actDelete", "삭제"))}</button>` : ""}
          <button type="button" data-close class="thr-mgr-btn thr-mgr-cancel">${escapeHtml(tt("btn.cancel", "취소"))}</button>
        </div>
      </div>`;
    document.body.appendChild(dlg);
    try { dlg.showModal(); } catch (_) { dlg.classList.add("open"); }

    // ✕ 버튼 + 취소 버튼 — 동적 다이얼로그라서 글로벌 [data-close] 위임이 안 잡힘 → 직접 바인딩
    dlg.querySelectorAll("[data-close]").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        try { dlg.close(); } catch (_) { dlg.remove(); }
      });
    });

    // 액션 바인딩
    const $ext = dlg.querySelector("#thrMgrExtend");
    if ($ext) {
      $ext.addEventListener("click", async () => {
        try {
          const res = await fetch(`${BASE}/api/threads/${encodeURIComponent(parentId)}/extend`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
          }).then(r => r.json());
          if (res && res.ok) {
            try { dlg.close(); } catch (_) { dlg.classList.remove("open"); }
            alert(tt("thread.extendDone", "보관 기간이 30일 연장되었습니다."));
            openRoomThreadsDialog(); // 목록 새로고침
          } else {
            alert((res && res.error) || tt("thread.extendFail", "연장 실패"));
          }
        } catch (e) {
          alert(tt("thread.extendFail", "연장 실패"));
        }
      });
    }
    const $bak = dlg.querySelector("#thrMgrBackup");
    if ($bak) {
      $bak.addEventListener("click", () => {
        _downloadThreadXlsx(parentId);
      });
    }
    const $del = dlg.querySelector("#thrMgrDelete");
    if ($del) {
      $del.addEventListener("click", async () => {
        const confirmMsg = tt("thread.confirmDelete", "이 스레드를 목록에서 숨길까요?\n대화 내용과 답글은 그대로 보존되고, 스레드 목록에서만 사라집니다.");
        if (!confirm(confirmMsg)) return;
        try {
          const res = await fetch(`${BASE}/api/threads/${encodeURIComponent(parentId)}`, {
            method: "DELETE",
          }).then(r => r.json());
          if (res && res.ok) {
            try { dlg.close(); } catch (_) { dlg.classList.remove("open"); }
            alert(tt("thread.deleteDone", "스레드를 목록에서 숨겼습니다. (대화 내용은 보존됨)"));
            openRoomThreadsDialog();
          } else {
            alert((res && res.error) || tt("thread.deleteFail", "삭제 실패"));
          }
        } catch (e) {
          alert(tt("thread.deleteFail", "삭제 실패"));
        }
      });
    }
  }

  function _threadRoleBadge(role) {
    if (role === "both")    return `<span class="thr-tag thr-both"   title="내가 작성하고 내가 답글도 단 스레드">✍️+💬</span>`;
    if (role === "author")  return `<span class="thr-tag thr-author" title="내 메시지에 답글이 달림">✍️</span>`;
    if (role === "replier") return `<span class="thr-tag thr-replier" title="내가 답글 단 스레드">💬</span>`;
    return                        `<span class="thr-tag thr-other"   title="방 전체 스레드">🧵</span>`;
  }

  // 상대 시간 — "오늘 시작" / "3일 전 시작" / "2개월 전 시작"
  function _relativeStartLabel(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d)) return "";
    const now = new Date();
    const diffMs = now - d;
    const diffDay = Math.floor(diffMs / 86400000);
    if (diffDay <= 0) return window.KNK_t ? window.KNK_t("thread.startedToday") : "오늘 시작";
    if (diffDay < 30) return (window.KNK_t ? window.KNK_t("thread.startedNDays") : "{n}일 전 시작").replace("{n}", diffDay);
    const diffMon = Math.floor(diffDay / 30);
    if (diffMon < 12) return (window.KNK_t ? window.KNK_t("thread.startedNMonths") : "{n}개월 전 시작").replace("{n}", diffMon);
    const diffYr = Math.floor(diffDay / 365);
    return (window.KNK_t ? window.KNK_t("thread.startedNYears") : "{n}년 전 시작").replace("{n}", diffYr);
  }

  function _threadItemHtml(t) {
    const author = t.parent_author || "";
    const startWhen = t.parent_created_at ? fmtTime(t.parent_created_at) : "";
    const startRel  = _relativeStartLabel(t.parent_created_at);
    const lastWhen  = t.last_reply_at ? fmtTime(t.last_reply_at) : "";
    const last      = t.last_reply_author || "";
    // 제목 (부모 메시지 내용) — 멘션 렌더 적용
    const titleHtml = (typeof renderTextWithMentions === "function")
      ? renderTextWithMentions(t.parent_preview || "")
      : escapeHtml(t.parent_preview || "");
    const titleSafe = titleHtml || (window.KNK_t ? window.KNK_t("thread.untitled") : "(내용 없음)");
    const replyLabel = window.KNK_t ? window.KNK_t("thread.replyCount").replace("{n}", t.reply_count || 0) : `답글 ${t.reply_count || 0}`;
    const lastByLabel = window.KNK_t ? window.KNK_t("thread.lastBy") : "최근";
    const dlTitle = window.KNK_t ? window.KNK_t("thread.download") : "이 스레드 다운로드 (엑셀)";
    return `
      <div class="mention-item thread-row" data-thread-parent-id="${t.parent_id}">
        <div class="mention-main">
          <div class="thread-title-row">
            ${_threadRoleBadge(t.my_role)}
            <span class="thread-title-text">${titleSafe}</span>
          </div>
          <div class="thread-meta-row">
            <span class="thread-meta-author">✍️ ${escapeHtml(author)}</span>
            <span class="thread-meta-sep">·</span>
            <span class="thread-meta-start" title="${escapeHtml(startWhen)}">📅 ${escapeHtml(startWhen)}${startRel ? ` <span class="thread-meta-rel">(${escapeHtml(startRel)})</span>` : ""}</span>
            <span class="thread-meta-sep">·</span>
            <span class="thread-meta-replies">💬 ${escapeHtml(replyLabel)}</span>
            ${last ? `<span class="thread-meta-sep">·</span><span class="thread-meta-last">${escapeHtml(lastByLabel)} ${escapeHtml(lastWhen)} ${escapeHtml(last)}</span>` : ""}
          </div>
        </div>
        <div class="thread-row-actions">
          <button type="button" class="thread-dl-btn" data-thread-dl="${t.parent_id}" title="${escapeHtml(dlTitle)}" aria-label="${escapeHtml(dlTitle)}">⬇</button>
          ${(t.can_delete || t.can_extend) ? `<button type="button" class="thread-del-btn" data-thread-del="${t.parent_id}" title="${escapeHtml(window.KNK_t ? window.KNK_t("thread.manage") : "스레드 관리(연장/삭제)")}" aria-label="스레드 관리">🗑</button>` : ""}
        </div>
      </div>`;
  }

  async function openRoomThreadsDialog(tab) {
    if (!activeRoom) return;
    const body = els.roomThreadsBody;
    const dlg = els.roomThreadsDialog;
    if (!dlg || !body) return;
    if (tab === "my" || tab === "all") _activeThreadTab = tab;
    if (els.roomThreadsRoomName) {
      els.roomThreadsRoomName.textContent = `📍 ${activeRoom.name || ""}`;
    }
    // 탭 활성화 표시
    const tabsBar = document.getElementById("roomThreadsTabs");
    if (tabsBar) {
      tabsBar.querySelectorAll("[data-thr-tab]").forEach(b => {
        b.classList.toggle("active", b.dataset.thrTab === _activeThreadTab);
      });
    }
    body.innerHTML = `<div style="text-align:center;color:var(--text-soft);padding:20px;">⏳ ${window.KNK_t ? window.KNK_t("thread.loading") : "불러오는 중..."}</div>`;
    // 안전망: 이전 세션에서 inline style.display="none" 이 박혀 있으면 다음 showModal 이 막힘
    try { dlg.style.removeProperty("display"); } catch (_) {}
    try { dlg.showModal(); } catch (_) { dlg.classList.add("open"); }
    let data = null;
    try {
      data = (_activeThreadTab === "all")
        ? await api.roomThreadsAll(activeRoom.id, 300)
        : await api.roomThreadsMy(activeRoom.id, 200);
    } catch (e) { data = null; }
    const items = (data && data.items) || [];
    const sectionKey = (_activeThreadTab === "all") ? "thread.titleAll" : "thread.titleMy";
    const sectionDefault = (_activeThreadTab === "all") ? "🧵 이 방 전체 스레드" : "🧵 이 방의 내 스레드";
    const sectionLabel = window.KNK_t ? window.KNK_t(sectionKey) : sectionDefault;
    const countLabel = `${sectionLabel} (${items.length})`;
    if (!items.length) {
      const emptyKey = (_activeThreadTab === "all") ? "thread.emptyAll" : "thread.empty";
      const emptyDefault = (_activeThreadTab === "all") ? "이 방에 아직 스레드가 없습니다." : "이 방에서 참여한 스레드가 없습니다.";
      const emptyMsg = window.KNK_t ? window.KNK_t(emptyKey) : emptyDefault;
      body.innerHTML =
        `<div class="mt-section-label" style="margin-bottom:8px;">${countLabel}</div>` +
        `<div class="search-empty">${emptyMsg}<br><span style="font-size:calc(12px + var(--fs-add-ui));">${window.KNK_t ? window.KNK_t("thread.emptyHint") : "메시지 옆 💬 를 눌러 답글을 달면 여기에 모입니다."}</span></div>`;
      return;
    }
    body.innerHTML =
      `<div class="mt-section-label" style="margin-bottom:8px;">${countLabel}</div>` +
      items.map(_threadItemHtml).join("");
    // 항목 캐시 (🗑 핸들러가 t 정보 조회용)
    const itemById = {};
    items.forEach(it => { itemById[it.parent_id] = it; });
    _threadItemsCache = itemById;

    // ⬇ 다운로드 버튼 (행 클릭과 분리)
    body.querySelectorAll("[data-thread-dl]").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const pid = btn.dataset.threadDl;
        if (!pid) return;
        _downloadThreadXlsx(pid);
      });
    });
    // 🗑 스레드 관리 버튼 (연장/삭제)
    body.querySelectorAll("[data-thread-del]").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const pid = parseInt(btn.dataset.threadDel, 10);
        openThreadManageDialog(pid);
      });
    });
    // 행 클릭 — 부모 점프 + 스레드 패널 + 답글창 포커스
    body.querySelectorAll("[data-thread-parent-id]").forEach(row => {
      row.addEventListener("click", (e) => {
        // ⬇ 버튼 클릭은 위 핸들러가 처리. 행 클릭에서는 무시.
        if (e.target.closest("[data-thread-dl]")) return;
        const pid = parseInt(row.dataset.threadParentId, 10);
        try { dlg.close(); } catch (_) { dlg.classList.remove("open"); }
        // 같은 방 안이므로 곧바로 부모 메시지로 점프 + 스레드 패널 자동 오픈 + 답글창 포커스
        setTimeout(() => {
          // 1) 부모 메시지가 DOM 에 있으면 스크롤·강조
          const target = els.messages && els.messages.querySelector(`.msg[data-msg-id="${pid}"]`);
          if (target) {
            target.scrollIntoView({ behavior: "smooth", block: "center" });
            target.classList.add("highlight-flash");
            setTimeout(() => target.classList.remove("highlight-flash"), 1800);
          }
          // 2) 스레드 패널 오픈 (답글 곧바로 입력 가능)
          try { openThreadPanel(pid); } catch (e2) {}
          // 3) 답글창 포커스 (모바일에서도 키보드 즉시 표출)
          setTimeout(() => {
            const ta = document.getElementById("threadInput");
            if (ta) { try { ta.focus(); } catch (_) {} }
          }, 220);
        }, 80);
      });
    });
  }

  async function openRequests(tab, highlightReqId, mineOnly) {
    if (!activeRoom) return;
    _reqMineOnly = !!mineOnly;   // 내 요청 패널 진입 시에만 본인것만. 압정 진입은 방 전체.
    // 탭이 지정되면 그 탭으로 — 없거나 매칭 안 되면 '열림'. cancelled 등은 '전체'로.
    const VALID_TABS = ["open", "in_progress", "on_hold", "done", "all"];
    activeReqTab = VALID_TABS.includes(tab) ? tab : (tab ? "all" : "open");
    els.requestsDialog.querySelectorAll(".gtab").forEach(t => {
      t.classList.toggle("active", t.dataset.rtab === activeReqTab);
    });
    await renderRequests();
    if (!els.requestsDialog.open) els.requestsDialog.showModal();
    // 특정 요청으로 스크롤 + 잠깐 강조 (내 요청 패널에서 진입 시)
    if (highlightReqId) {
      const el = els.requestsList.querySelector(`[data-req-id="${highlightReqId}"]`);
      if (el) {
        el.scrollIntoView({ block: "center", behavior: "smooth" });
        el.classList.add("req-flash");
        setTimeout(() => el.classList.remove("req-flash"), 2000);
      }
    }
  }

  async function renderRequests() {
    if (!activeRoom) return;
    let data = await api.requests(activeRoom.id, activeReqTab);
    // 내 요청 패널 진입 시 — 본인것만(요청자=나 또는 담당자=나) (대표 지시 2026-05-22)
    if (_reqMineOnly) data = data.filter(q => q.requested_by === meId || q.assigned_to === meId);
    els.requestsCount.textContent = data.length;
    const scopeEl = document.getElementById("reqScopeLabel");
    if (scopeEl) scopeEl.textContent = _reqMineOnly ? " · 내 요청만" : "";
    if (!data.length) {
      els.requestsList.innerHTML = `<div class="empty-state" style="padding:32px;color:var(--text-soft);">${_reqMineOnly ? "이 방에 내 요청이 없습니다." : (activeReqTab === "open" ? "열린 요청이 없습니다. 일반 메신저와 다르게 — 묻혀서 잃어버리는 요청은 이제 없습니다." : "해당 상태의 요청이 없습니다.")}</div>`;
      return;
    }
    els.requestsList.innerHTML = data.map(reqItemHtml).join("");
    els.requestsList.querySelectorAll("[data-req-act]").forEach(b => {
      b.addEventListener("click", async () => {
        const id = parseInt(b.dataset.reqId, 10);
        b.disabled = true;
        const ok = await _doRequestAction(id, b.dataset.reqAct);
        b.disabled = false;
        if (ok) { await renderRequests(); await refreshRequestsBadge(); }
      });
    });
  }

  // 서버가 내려준 권한 플래그(can_*) 기반 액션 버튼. ns=data 속성 네임스페이스("req"|"mt")
  function _requestActionButtons(q, ns) {
    const b = [];
    if (q.can_start)    b.push(`<button class="req-action-btn primary" data-${ns}-act="start" data-${ns}-id="${q.id}">시작</button>`);
    if (q.can_complete) b.push(`<button class="req-action-btn primary" data-${ns}-act="done" data-${ns}-id="${q.id}">완료</button>`);
    if (q.can_hold)     b.push(`<button class="req-action-btn" data-${ns}-act="hold" data-${ns}-id="${q.id}">보류</button>`);
    if (q.can_unhold)   b.push(`<button class="req-action-btn" data-${ns}-act="unhold" data-${ns}-id="${q.id}">보류 해제</button>`);
    if (q.can_cancel)   b.push(`<button class="req-action-btn" data-${ns}-act="cancel" data-${ns}-id="${q.id}">취소</button>`);
    if (q.can_reopen)   b.push(`<button class="req-action-btn" data-${ns}-act="reopen" data-${ns}-id="${q.id}">다시 열기</button>`);
    return b.join("");
  }

  // 요청 액션 실행 — 완료는 메시지 필수(요청자에게 전달). 성공 시 true.
  async function _doRequestAction(id, act) {
    let payload = null;
    if (act === "start") payload = { status: "in_progress" };
    else if (act === "done") {
      const msg = (prompt("완료 메시지를 입력하세요 (요청자에게 전달됩니다)\n예: 도면 메일로 보냈습니다") || "").trim();
      if (!msg) return false;   // 취소·빈값 → 중단 (완료 메시지 필수)
      payload = { status: "done", message: msg };
    }
    else if (act === "hold") payload = { status: "on_hold" };
    else if (act === "unhold") payload = { status: "open" };
    else if (act === "reopen") payload = { status: "open" };
    else if (act === "cancel") {
      if (!confirm(window.KNK_t("confirm.cancelRequest"))) return false;
      payload = { status: "cancelled" };
    }
    if (!payload) return false;
    try {
      const res = await api.updateRequest(id, payload);
      if (res && res.error) { alert(res.error); return false; }
      return true;
    } catch (e) {
      alert(window.KNK_t("alert.processFailed"));
      return false;
    }
  }

  function reqItemHtml(q) {
    const days = daysUntil(q.due_date);
    let cls = `req-item req-${q.status}`;
    let dueText = "";
    if (q.due_date) {
      if (days < 0) { cls += " req-overdue"; dueText = `<span class="req-overdue-text">납기 ${fmtDate(q.due_date)} (${-days}일 지남)</span>`; }
      else if (days <= 1) { cls += " req-due-soon"; dueText = `<span class="req-due-soon-text">납기 ${fmtDate(q.due_date)} ${days === 0 ? "(오늘!)" : "(내일)"}</span>`; }
      else dueText = `<span>납기 ${fmtDate(q.due_date)} (D-${days})</span>`;
    }
    const assigned = q.assigned_to
      ? `<span>👤 ${escapeHtml(_reqPersonLabel(q.assigned_to, q.assigned_to_name))}</span>`
      : `<span style="color:#d97706;font-weight:700">👤 미지정</span>`;
    const priority = q.priority === "high" ? `<span class="req-priority-high">긴급</span>` : "";
    const actions = _requestActionButtons(q, "req");
    return `
      <div class="${cls}" data-req-id="${q.id}">
        <div class="req-head">
          <div class="req-title">${priority} ${escapeHtml(q.title)}</div>
          <span class="req-status req-status-${q.status}">${REQ_STATUS_LABEL[q.status] || q.status}</span>
        </div>
        ${q.description ? `<div class="req-desc">${escapeHtml(q.description)}</div>` : ""}
        <div class="req-meta">
          <span>요청 ${escapeHtml(_reqPersonLabel(q.requested_by, q.requested_by_name))}</span>
          ${assigned}
          ${dueText}
          <span style="color:#9ca3af">· ${fmtTime(q.created_at)}</span>
        </div>
        <div class="req-actions">${actions}</div>
      </div>`;
  }

  // ---- 요청 담당자 검색 피커 (현재 방 멤버만) ----
  let _reqRoomMembers = [];       // 현재 방 멤버 후보 [{id,name,meta,label}]
  let _reqAssigneeBound = false;  // 피커 이벤트 1회만 바인딩

  function _renderAssigneeOptions(filter) {
    const dropEl = document.getElementById("reqAssigneeDropdown");
    if (!dropEl) return;
    const q = (filter || "").trim().toLowerCase();
    const list = q ? _reqRoomMembers.filter(m => m.label.toLowerCase().includes(q)) : _reqRoomMembers.slice();
    let html = `<div class="assignee-opt" data-uid="">(미지정)</div>`;
    html += list.map(m => `<div class="assignee-opt" data-uid="${m.id}">${escapeHtml(m.label)}</div>`).join("");
    if (q && !list.length) html += `<div class="assignee-empty">일치하는 방 멤버 없음</div>`;
    dropEl.innerHTML = html;
    dropEl.hidden = false;
  }

  function _bindAssigneePicker() {
    if (_reqAssigneeBound) return;
    _reqAssigneeBound = true;
    const searchEl = document.getElementById("reqAssigneeSearch");
    const dropEl = document.getElementById("reqAssigneeDropdown");
    if (!searchEl || !dropEl) return;
    searchEl.addEventListener("focus", () => _renderAssigneeOptions(searchEl.value));
    searchEl.addEventListener("input", () => {
      els.reqAssignedTo.value = "";   // 타이핑 중엔 선택 해제 → 목록에서 다시 선택해야 확정
      _renderAssigneeOptions(searchEl.value);
    });
    dropEl.addEventListener("click", (e) => {
      const opt = e.target.closest(".assignee-opt");
      if (!opt) return;
      const uid = opt.dataset.uid || "";
      els.reqAssignedTo.value = uid;
      searchEl.value = uid ? opt.textContent : "";
      dropEl.hidden = true;
    });
    document.addEventListener("click", (e) => {
      const picker = document.getElementById("reqAssigneePicker");
      if (picker && !picker.contains(e.target)) dropEl.hidden = true;
    });
  }

  async function openNewRequest({ messageId = null, sourceContent = "" } = {}) {
    if (!activeRoom) return;
    await ensureUsers();
    pendingReqMessage = messageId;

    // 담당자 후보 = 현재 방 멤버만 (전체 사용자 X). 직급·부서는 users 캐시에서 보강.
    _reqRoomMembers = [];
    try {
      const res = await api.roomMembers(activeRoom.id);
      const mem = (res && Array.isArray(res.members)) ? res.members : [];
      _reqRoomMembers = mem
        .filter(m => m.username !== "_deleted_user")
        .map(m => {
          const u = (Array.isArray(users) ? users.find(x => x.id === m.id) : null) || {};
          const title = u.title || "";
          const dept = u.department || "";
          const deptLabel = dept ? ((typeof deptDisplayLabel === "function") ? deptDisplayLabel(dept) : dept) : "";
          const meta = [title, deptLabel].filter(Boolean).join(" · ");
          return { id: m.id, name: m.display_name, meta, label: meta ? `${m.display_name} (${meta})` : m.display_name };
        });
    } catch (e) { _reqRoomMembers = []; }

    // 피커 초기화 (미지정 상태)
    els.reqAssignedTo.value = "";
    const searchEl = document.getElementById("reqAssigneeSearch");
    const dropEl = document.getElementById("reqAssigneeDropdown");
    if (searchEl) searchEl.value = "";
    if (dropEl) { dropEl.hidden = true; dropEl.innerHTML = ""; }
    _bindAssigneePicker();

    els.reqTitle.value = sourceContent ? sourceContent.slice(0, 100) : "";
    els.reqDescription.value = "";
    els.reqDueDate.value = "";
    els.reqPriority.value = "normal";
    if (sourceContent) {
      els.newReqSourceHint.hidden = false;
      els.newReqSourceHint.innerHTML = `📌 원본 메시지: <em style="color:var(--text-soft)">${escapeHtml(sourceContent.slice(0, 80))}${sourceContent.length > 80 ? "..." : ""}</em>`;
    } else {
      els.newReqSourceHint.hidden = true;
    }
    els.newRequestDialog.showModal();
  }

  async function saveNewRequest(e) {
    e.preventDefault();
    if (!activeRoom) return;
    const title = els.reqTitle.value.trim();
    if (!title) { alert(window.KNK_t("alert.titleRequired")); return; }
    const payload = {
      room_id: activeRoom.id,
      message_id: pendingReqMessage,
      title,
      description: els.reqDescription.value.trim() || null,
      assigned_to: els.reqAssignedTo.value ? parseInt(els.reqAssignedTo.value, 10) : null,
      due_date: els.reqDueDate.value || null,
      priority: els.reqPriority.value,
    };
    const res = await api.createRequest(payload);
    if (res.error) { alert(res.error); return; }
    els.newRequestDialog.close();
    pendingReqMessage = null;
    if (els.requestsDialog.open) await renderRequests();
    await refreshRequestsBadge();
  }

  // ---------- search ----------
  function highlight(text, q) {
    if (!q) return escapeHtml(text);
    const tokens = q.match(/[\w가-힣]+/g) || [];
    let out = escapeHtml(text);
    tokens.forEach(t => {
      const re = new RegExp(`(${t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
      out = out.replace(re, "<mark>$1</mark>");
    });
    return out;
  }

  // 방 열기 — 접힘(슬림) 상태면 새 창(solo 팝업), 펼침이면 그 자리 대화방 (대표 지시 2026-06-03).
  // 접힘 땐 대화칸 폭이 0px라 그 자리에 열면 안 보임 → 기존 solo 팝업 코드를 재사용해 새 창으로.
  // 반환: true = 새 창으로 열었음(호출측은 openRoom 생략) / false = 호출측이 openRoom 진행.
  function _openRoomOrPopout(rid) {
    if (SOLO_MODE) return false;
    if (!app || !app.classList.contains("chat-collapsed")) return false;
    try {
      const url = BASE + `/chat?solo=1&room=${rid}`;
      const w = window.open(url, `knk_room_${rid}`, _soloFeatures());
      if (w) { try { w.focus(); } catch (_) {} }
      return true;
    } catch (_) { return false; }
  }

  async function runSearch(q) {
    q = q.trim();
    const onUsersTab = (typeof _sidebarTab !== "undefined" && _sidebarTab === "users");
    if (!q) {
      // 검색어 비움 → 현재 탭 기본 화면으로 복귀
      els.searchResults.hidden = true;
      window._userListQuery = "";
      if (onUsersTab) {
        els.roomList.hidden = true;
        if (els.userList) els.userList.hidden = false;
        if (typeof renderUserList === "function") renderUserList();
      } else {
        els.roomList.hidden = false;
      }
      return;
    }
    // 업무대화방·사용자 — 어느 탭이든 똑같은 '통합 검색' 결과를 토출 (대표 지시 2026-06-06)
    const data = await api.search(q);
    els.roomList.hidden = true;
    if (els.userList) els.userList.hidden = true;   // 사용자 탭에서도 통합 결과 표시
    els.myTasks.hidden = true;
    els.searchResults.hidden = false;
    if (!data.length) {
      els.searchResults.innerHTML = `<div class="search-empty">"${escapeHtml(q)}" 결과 없음</div>`;
      return;
    }
    // 통합 검색 결과 — 묶음(👤 사용자 / 💬 대화방 / 📝 대화 내용) 머리글로 그룹화 (대표 지시 2026-06-06)
    function _renderSearchItem(m) {
      if (m.result_type === "user") {
        // 사용자 — 클릭하면 사용자 정보 보기
        const sub = [m.user_title, m.user_department].filter(Boolean).join(" · ");
        return `
          <div class="search-result-item" data-user-id="${m.user_id}">
            <div class="search-result-content"><strong>${highlight(m.display_name || "", q)}</strong>${sub ? ` <span style="color:var(--text-soft)">${escapeHtml(sub)}</span>` : ""}</div>
          </div>`;
      }
      if (m.result_type === "room") {
        // 참여 대화방 — 클릭하면 그 방 열기.
        //   1:1(direct) 방은 DB r.name 이 비어 있어 빈 줄로 보이던 문제 → 목록과 동일한
        //   roomDisplayName(상대 '이름 직급님-부서')으로 표시 (대표 지시 2026-06-06)
        const _r = (Array.isArray(rooms) ? rooms.find(x => x.id === m.room_id) : null);
        const _rn = (_r ? roomDisplayName(_r) : "") || m.room_name || (window.KNK_t ? window.KNK_t("room.unnamed") : "(이름없음)");
        return `
          <div class="search-result-item" data-room-id="${m.room_id}">
            <div class="search-result-content"><strong>${highlight(_rn, q)}</strong></div>
          </div>`;
      }
      if (m.result_type === "item") {
        // 요청(프로젝트) — 📋 요청 묶음. 클릭하면 그 방 열기 (내가 멤버인 방만 서버에서 내려옴)
        const chips = [];
        if (m.item_customer) chips.push(`<span class="customer-chip">${escapeHtml(m.item_customer)}</span>`);
        if (m.item_code) chips.push(`<span class="code-chip">${escapeHtml(m.item_code)}</span>`);
        const status = m.item_status ? `<span class="status-pill status-${m.item_status}">${STATUS_LABEL[m.item_status]}</span>` : "";
        return `
          <div class="search-result-item" data-room-id="${m.room_id}" style="border-left:3px solid #7c3aed;padding-left:9px">
            ${(chips.length || status) ? `<div class="search-result-room">${chips.join("")}${status}</div>` : ""}
            <div class="search-result-content"><strong>${highlight(m.room_name || "", q)}</strong>${m.item_desc ? ` — ${highlight(String(m.item_desc).slice(0,100), q)}` : ""}</div>
          </div>`;
      }
      // 대화 내용(메시지) / 스레드(답글) — result_type 으로 구분, 스레드는 ↳ 표시 (대표 지시 2026-06-06)
      const _isThread = (m.result_type === "thread");
      const content = m.kind === "image" ? `🖼 ${escapeHtml(m.file_name || "사진")}` :
                      m.kind === "file" ? `📎 ${escapeHtml(m.file_name || "파일")}` :
                      m.kind === "sticker" ? `🐶 ${escapeHtml(m.content || "스티커")}` :
                      highlight(String(m.content || "").slice(0, 200), q);
      return `
        <div class="search-result-item" data-room-id="${m.room_id}">
          <div class="search-result-room">
            <span style="font-weight:600">${escapeHtml(m.room_name || "")}</span>
            <span style="margin-left:auto">${fmtTime(m.created_at)}</span>
          </div>
          <div class="search-result-content">${_isThread ? '<span style="color:var(--text-soft)">↳ </span>' : ''}<strong>${escapeHtml(m.display_name)}:</strong> ${content}</div>
        </div>`;
    }
    // 5개 묶음 분리 (대표 지시 2026-06-06): 1.사용자 2.대화방 3.대화내용 4.스레드 5.요청
    const _grpOf = (m) => (m.result_type === "user") ? "user"
                        : (m.result_type === "room") ? "room"
                        : (m.result_type === "thread") ? "thread"
                        : (m.result_type === "item") ? "item" : "msg";
    const _grpHead = { user: "👤 사용자", room: "💬 대화방", msg: "📝 대화 내용", thread: "🧵 스레드", item: "📋 요청" };
    let _curGrp = "", _searchHtml = "";
    for (const m of data) {
      const g = _grpOf(m);
      if (g !== _curGrp) { _curGrp = g; _searchHtml += `<div class="search-group-head">${_grpHead[g]}</div>`; }
      _searchHtml += _renderSearchItem(m);
    }
    els.searchResults.innerHTML = _searchHtml;
    els.searchResults.querySelectorAll(".search-result-item").forEach(li => {
      li.addEventListener("click", (e) => {
        // 사람 결과 → 사용자 정보 '카드'(1:1채팅·이메일·전화·정보수정 등)로 열기 (대표 지시 2026-06-06, 사용자 목록 클릭과 동일)
        if (li.dataset.userId) {
          e.stopPropagation();   // 바깥클릭 닫기(document)가 이 클릭으로 방금 연 카드를 즉시 닫지 않게
          const uid = parseInt(li.dataset.userId, 10);
          const _cx = (e && e.clientX) || 0, _cy = (e && e.clientY) || 0;
          const _showCard = () => { try { showUserContextMenu(uid, _cx, _cy); } catch (_) {} };
          // 카드는 _usersCache 를 참조 — 검색은 어느 탭에서나 가능해 캐시가 비어있을 수 있으니 보장 후 표시
          if (_usersCache && _usersCache.some(x => x.id === uid)) _showCard();
          else (typeof refreshUserList === "function" ? refreshUserList() : ensureUsers()).then(_showCard);
          return;
        }
        const rid = parseInt(li.dataset.roomId, 10);
        const room = rooms.find(r => r.id === rid);
        if (room) {
          els.globalSearch.value = "";
          els.searchResults.hidden = true;
          window._searchTopRoomId = rid;     // 클릭한 방을 목록 맨 위로 고정 (renderRoomList)
          activeFilter = "all";              // 전체 방 리스트가 뜨게 (대표 지시 2026-06-06)
          if (els.filterBar) els.filterBar.querySelectorAll(".chip").forEach(x => x.classList.toggle("active", x.dataset.filter === "all"));
          if (!_openRoomOrPopout(rid)) openRoom(room);   // 접힘 → 새 창 / 펼침 → 그 자리 (대표 지시 2026-06-03)
          setSidebarTab("rooms");            // 사용자 탭에서 검색했어도 방 목록 탭으로 전환 → 왼쪽에 전체 리스트(클릭 방 최상단·강조) 표시
        }
      });
    });
  }

  // 요청 패널 사람 표기 — '이름 직급 부서(short)'. users 캐시에서 직급·부서 보강.
  //   부서는 deptShortLabel 사용 → 본사 숫자코드 없음 / 베트남 'VN..' / '총괄'은 숨김 (대표 지시 2026-05-22)
  function _reqPersonLabel(uid, fallbackName) {
    const u = (Array.isArray(users) && uid) ? (users.find(x => x.id === uid) || {}) : {};
    const nm = _dispName(u) || fallbackName || "";
    const t = _dispTitle(u) || "";
    const d = (_useEnNames() && u.department_en) ? u.department_en
            : (u.department ? ((typeof deptShortLabel === "function") ? deptShortLabel(u.department) : u.department) : "");
    return [nm, t, d].filter(Boolean).join(" ");
  }

  // ---------- my tasks (내 요청 종합 — 받은 요청 + 보낸 요청) ----------
  function _myTaskItemHtml(q, mode) {
    // mode: 'received'(나에게 배정) | 'sent'(내가 요청·위임)
    const days = daysUntil(q.due_date);
    let dueCls = "";
    let dueText = q.due_date ? `납기 ${fmtDate(q.due_date)}` : "";
    if (days != null) {
      if (days < 0) { dueCls = "overdue"; dueText = `납기 ${fmtDate(q.due_date)} (${-days}일 지남)`; }
      else if (days <= 1) { dueCls = "due-soon"; dueText = `납기 ${fmtDate(q.due_date)} ${days === 0 ? "(오늘!)" : "(내일)"}`; }
      else dueText = `납기 ${fmtDate(q.due_date)} (D-${days})`;
    }
    const chips = [];
    if (q.item_customer) chips.push(`<span class="customer-chip">${escapeHtml(q.item_customer)}</span>`);
    if (q.item_code) chips.push(`<span class="code-chip">${escapeHtml(q.item_code)}</span>`);
    // 상대방 표시 — 받은 요청이면 '요청자', 보낸 요청이면 '담당자' (이름 직급 부서)
    const who = mode === "received"
      ? `요청 ${escapeHtml(_reqPersonLabel(q.requested_by, q.requested_by_name))}`
      : `담당 ${q.assigned_to ? escapeHtml(_reqPersonLabel(q.assigned_to, q.assigned_to_name)) : "미지정"}`;
    // 인라인 상태 변경 버튼 — 서버 권한 플래그(can_*) 기반. 방에 안 들어가도 바로 처리.
    const actions = _requestActionButtons(q, "mt");
    // 줄 분리(태블릿 가독성, 대표 지시 2026-05-22):
    //   1줄=제목 / 2줄=방이름(+상태배지) / 3줄=요청자·담당자(+납기)
    return `
      <div class="task-row ${dueCls}" data-room-id="${q.room_id}" data-req-id="${q.id}" data-req-status="${q.status}">
        <div class="task-title">${escapeHtml(q.title)}</div>
        <div class="task-meta task-meta-room">
          ${chips.join("")}
          <span class="task-room-name">${escapeHtml(q.room_name || "")}</span>
          <span class="req-status req-status-${q.status}" style="margin-left:auto">${REQ_STATUS_LABEL[q.status] || q.status}</span>
        </div>
        <div class="task-meta task-meta-person">
          <span>${who}</span>
          ${dueText ? `<span class="task-due">${dueText}</span>` : ""}
        </div>
        <div class="req-actions mt-actions">${actions}</div>
      </div>`;
  }

  async function renderMyTasks() {
    await ensureUsers();   // 사람 라벨(직급·부서) 보강용 캐시 보장
    const data = await api.myRequests();
    if (!data.length) {
      els.myTasks.innerHTML = `<div class="search-empty">받은 요청도 보낸 요청도 없습니다. 🎉</div>`;
      return;
    }
    // 받은 요청 = 나에게 배정 / 보낸 요청 = 내가 요청했고 담당이 내가 아님(위임)
    const received = data.filter(q => q.assigned_to === meId);
    const sent = data.filter(q => q.requested_by === meId && q.assigned_to !== meId);
    let html = "";
    if (received.length) {
      html += `<div class="mt-section-label">📥 받은 요청 (${received.length})</div>`;
      html += received.map(q => _myTaskItemHtml(q, "received")).join("");
    }
    if (sent.length) {
      html += `<div class="mt-section-label">📤 보낸 요청 (${sent.length})</div>`;
      html += sent.map(q => _myTaskItemHtml(q, "sent")).join("");
    }
    els.myTasks.innerHTML = html;
    // 상태 변경 버튼 — 서버 권한 기반. 행 클릭(방 이동)과 분리하기 위해 전파 차단.
    els.myTasks.querySelectorAll("[data-mt-act]").forEach(b => {
      b.addEventListener("click", async (e) => {
        e.stopPropagation();
        const id = parseInt(b.dataset.mtId, 10);
        b.disabled = true;
        const ok = await _doRequestAction(id, b.dataset.mtAct);
        b.disabled = false;
        if (ok) await renderMyTasks();
      });
    });
    // 행 클릭 → 해당 방 열기 + 요청 목록 다이얼로그에서 그 요청을 강조 표시 (액션 버튼 외 영역)
    els.myTasks.querySelectorAll(".task-row").forEach(li => {
      li.addEventListener("click", async () => {
        const rid = parseInt(li.dataset.roomId, 10);
        const room = rooms.find(r => r.id === rid);
        if (!room) return;
        await openRoom(room);
        const reqId = parseInt(li.dataset.reqId, 10);
        const status = li.dataset.reqStatus || "open";
        await openRequests(status, reqId, true);   // 본인것만 — 요청 내용을 바로 확인
      });
    });
  }

  // ---------- drag & drop ----------
  function setupDropzone() {
    let dragCounter = 0;
    const overlay = document.createElement("div");
    overlay.className = "dropzone-overlay";
    overlay.textContent = "📥 파일을 놓으세요";
    overlay.style.display = "none";
    els.chatPane.style.position = "relative";
    els.chatPane.appendChild(overlay);

    els.chatPane.addEventListener("dragenter", (e) => {
      if (!activeRoom) return;
      e.preventDefault();
      dragCounter++;
      overlay.style.display = "grid";
    });
    els.chatPane.addEventListener("dragleave", (e) => {
      e.preventDefault();
      dragCounter--;
      if (dragCounter <= 0) { dragCounter = 0; overlay.style.display = "none"; }
    });
    els.chatPane.addEventListener("dragover", (e) => e.preventDefault());
    els.chatPane.addEventListener("drop", async (e) => {
      e.preventDefault();
      dragCounter = 0;
      overlay.style.display = "none";
      if (!activeRoom) return;
      // dataTransfer.files 도 FileList → 정적 배열로 복사 후 넘긴다.
      const files = Array.from(e.dataTransfer.files || []);
      if (!files.length) return;
      // 즉시 전송하지 않고 글틀 위 '보낼 첨부'에 담음(기존에 담긴 것에 '더하기')
      //   → 글 입력 후 보내기/Enter 로 전송. 첨부버튼·붙여넣기와 동일 동작. (대표 지시 2026-06-03)
      //   사진 2장 이상이면 chooseAttachMode 로 개별/앨범 묶기 선택창 유지.
      const choice = await chooseAttachMode(files);
      if (choice.mode === "cancel") return;
      _stageFiles([..._pendingFiles, ...files], _pendingAlbumMode || choice.mode === "album");
    });

    // 클립보드에서 '파일(이미지 등)' 붙여넣기 — 바로 보내지 말고 '보낼 첨부'에 담기(기존 담긴 것에 추가).
    //   → 보내기 버튼/엔터로 전송. 텍스트 붙여넣기는 입력창 기본 동작 유지. (대표 지시 2026-06-02)
    document.addEventListener("paste", (e) => {
      // 스레드 패널이 열려있고 포커스가 그 안이면 → 스레드 '보낼 첨부'로 담기 (대표 지시 2026-06-04)
      const _tp = document.getElementById("threadPanel");
      if (_tp && _tp.classList.contains("open") && _tp.contains(document.activeElement)) {
        const titems = e.clipboardData?.items || [];
        const tfiles = [];
        for (const it of titems) {
          if (it.kind === "file") { const f = it.getAsFile(); if (f) tfiles.push(f); }
        }
        if (!tfiles.length) return;
        e.preventDefault();
        _stageThreadFiles(tfiles);
        return;
      }
      if (!activeRoom) return;
      const cd = e.clipboardData;
      const items = (cd && cd.items) || [];
      const files = [];
      for (const it of items) {
        if (it.kind === "file") {
          const f = it.getAsFile();
          if (f) files.push(f);
        }
      }
      if (!files.length) {
        // 글+그림이 섞인 HTML(그림/표/도형 포함) → '묶음 미리보기'로 (대표 지시 2026-06-06)
        //   순수 글은 입력창 기본 붙여넣기 그대로(텍스트 유지·번역 보호).
        const _html = cd ? cd.getData("text/html") : "";
        if (_html && _htmlHasEmbeddedVisual(_html)) {
          e.preventDefault();
          _startMultipartPaste(_html);
        }
        return;
      }
      e.preventDefault();
      _stageFiles([..._pendingFiles, ...files], _pendingAlbumMode);   // 진짜 이미지/파일 → 담기
    });
  }

  // ---------- socket ----------
  function connectSocket() {
    // polling 먼저 연결(확실) → 가능하면 websocket 으로 자동 업그레이드.
    // websocket 을 먼저 두면 /msg 하위 경로에서 WS 업그레이드 실패 시 연결 자체가 끊김.
    socket = io({ path: BASE + "/socket.io", transports: ["polling", "websocket"] });

    // ─── Presence (PC 활성 시 모바일 푸시 자동 억제) ───
    // device 판정: pointer:coarse 면 mobile, 그 외 pc.
    // active 판정: !document.hidden && document.hasFocus()
    //   → 사용자가 실제로 보고 있는 상태에서만 PC active 로 인정
    //   → blur(다른 앱) / hidden(탭 전환) 이면 모바일에 푸시 보냄
    const _presenceIsTouch = window.matchMedia('(pointer: coarse)').matches;
    const _presenceDevice = _presenceIsTouch ? 'mobile' : 'pc';
    let _presenceLastActive = null;  // 마지막 전송값 캐시 (중복 방지)
    let _presenceLastIdle = null;
    // 자동 자리비움 — 앱은 보고 있으나(visible+focus) 일정시간 조작이 없으면 'away'. (대표 지시 2026-05-23)
    // 무조작 → 자리비움 임계값. 회사 공통 설정값(관리자 15/30분)을 서버가 주입(window.KNK_AWAY_MIN).
    const IDLE_AWAY_MS = (Number(window.KNK_AWAY_MIN) || 15) * 60 * 1000;
    let _lastInteractAt = Date.now();
    // 활성 판정 — 터치 기기(태블릿·폰)는 화면 키보드가 document.hasFocus()를 false 로 만들어
    //   '보고 있는 중'에도 비활성으로 보고됨 → 보고 있는 방인데 푸시가 옴.
    //   따라서 터치는 visibility(!hidden) 만으로 판정. 데스크탑은 멀티윈도우 위해 hasFocus 까지.
    //   (대표 지시 2026-05-21)
    function _isViewingActive() {
      return _presenceIsTouch ? !document.hidden : (!document.hidden && document.hasFocus());
    }
    function _isIdleAway() {
      return _isViewingActive() && (Date.now() - _lastInteractAt >= IDLE_AWAY_MS);
    }
    // 조작 감지 → 마지막 조작시각 갱신 + 자리비움이었으면 즉시 활성 복귀 알림
    ["pointerdown", "keydown", "touchstart", "mousemove", "scroll", "click", "wheel"].forEach(ev =>
      document.addEventListener(ev, () => {
        _lastInteractAt = Date.now();
        if (_presenceLastIdle) sendPresence();
      }, { passive: true, capture: true })
    );
    function sendPresence() {
      try {
        if (!socket || !socket.connected) return;
        const active = _isViewingActive();
        const idle = _isIdleAway();
        // 같은 값 중복 전송 방지 (블러·포커스 폭주 시 트래픽 감소)
        if (_presenceLastActive === active && _presenceLastIdle === idle) return;
        _presenceLastActive = active;
        _presenceLastIdle = idle;
        socket.emit('presence', { device: _presenceDevice, active, idle });
      } catch (e) { /* noop */ }
    }
    // 연결 즉시 전송 (서버는 connect 시 active=true 로 기본 등록하지만 device 미상 상태)
    // + SocketIO 연결되면 statuses 재호출 (race condition 회피: API 가 connect 전 호출됐다면
    //   본인이 offline 으로 잘못 표시될 수 있음) — 대표 지시 2026-05-19
    socket.on('connect', () => {
      _presenceLastActive = null;
      sendPresence();
      // 100ms 지연 — 서버의 presence_register 완료 후 statuses 재조회
      setTimeout(() => {
        try { if (typeof refreshAllUserStatuses === 'function') refreshAllUserStatuses(); } catch(e) {}
        // 헤더 본인 정보·권한(🆔 직원 등록 버튼) 초기 동기화 (2026-05-20)
        try { if (typeof refreshUserList === 'function') refreshUserList(); } catch(e) {}
      }, 200);
      // ★ 재연결(첫 연결 제외) 시 — 끊긴 동안 놓친 메시지 재동기화. (대표 지시 2026-05-23)
      //   휴대폰 기지국 전환·로밍·해외 와이파이·LTE↔WiFi 전환 등으로 잠깐 끊겼다 붙을 때,
      //   '보고 있는 방'의 그 사이 도착 메시지를 다시 불러오고 방 목록도 갱신.
      if (_socketConnectedOnce) {
        try { refreshRooms(); } catch(e) {}
        _resyncActiveRoom(true);
      }
      _socketConnectedOnce = true;
      // ★ 연결·재연결 시 서버에 현재 활성 방 알림 — 푸시 차단 정확도 보장 (대표 지시 2026-05-26)
      //   서버측 active_room 상태가 서버 재시작·소켓 끊김으로 초기화될 수 있어 매번 다시 통보.
      try {
        const rid = (typeof activeRoom !== "undefined" && activeRoom) ? activeRoom.id : null;
        socket.emit("set_active_room", { room_id: rid });
      } catch (e) {}
    });
    if (socket.connected) sendPresence();
    // 가시성 변경
    document.addEventListener('visibilitychange', sendPresence);
    window.addEventListener('focus', sendPresence);
    window.addEventListener('blur', sendPresence);
    // pageshow (bfcache 복원 시 active 재인식)
    window.addEventListener('pageshow', sendPresence);
    // ★ 네트워크 복귀(offline→online) 시에도 재동기화 — 소켓 재연결 신호를 놓쳐도 보강. (대표 지시 2026-05-23)
    window.addEventListener('online', () => {
      try { if (socket && !socket.connected) socket.connect(); } catch(e) {}
      _resyncActiveRoom(true);
    });
    // 화면 복귀(탭/앱 다시 봄) 시 — 소켓이 끊겨 있었다면 재동기화 (백그라운드 절전으로 놓친 경우 보강)
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden && socket && !socket.connected) _resyncActiveRoom(true);
    });

    // 다른 사람 상태도 '화면 볼 때' 즉시 갱신 — 1분 폴링 기다리지 않게. (2026-05-20)
    //  앱 열기/탭 복귀/포커스 시점에 statuses 재조회 (과도호출 방지 15초 쓰로틀).
    let _lastStatusRefresh = 0;
    const _refreshStatusesThrottled = () => {
      const now = Date.now();
      if (now - _lastStatusRefresh < 15000) return;
      _lastStatusRefresh = now;
      try { if (typeof refreshAllUserStatuses === 'function') refreshAllUserStatuses(); } catch (e) {}
    };
    document.addEventListener('visibilitychange', () => { if (!document.hidden) _refreshStatusesThrottled(); });
    window.addEventListener('focus', _refreshStatusesThrottled);
    window.addEventListener('pageshow', _refreshStatusesThrottled);

    // 활성 heartbeat — 30초마다 (서버 _PC_ACTIVE_STALE_SEC=60 보다 짧게). (2026-05-21 태블릿·폰도 적용)
    //  PC·태블릿·폰 모두 — 앱을 보고 있는 동안 presence(active=true) 재전송 → 서버 ts 갱신 →
    //  보는 동안 OS 푸시 억제 유지. 자리비움·절전·잠금·백그라운드면 heartbeat 멈춤 →
    //  60초 후 서버가 '비활성' 판정 → 푸시 정상 발송. (PC 켜둬도 자리 비우면 휴대폰 알림 오게)
    setInterval(() => {
      try {
        if (!socket || !socket.connected) return;
        if (_isViewingActive()) {
          // active 상태 강제 재전송 (중복 방지 캐시 우회 — ts 갱신 목적) + 현재 idle(자리비움) 동봉
          const idle = _isIdleAway();
          _presenceLastActive = true; _presenceLastIdle = idle;   // 캐시 동기화
          socket.emit('presence', { device: _presenceDevice, active: true, idle });
        }
      } catch (e) { /* noop */ }
    }, 30000);

    // 메시지 삭제 실시간 알림 — 대표 지시 2026-05-19
    // 강제 로그아웃 — (1) 같은 종류 기기로 새 로그인됨, 또는 (2) 휴대폰에서 로그아웃(완전 로그아웃).
    // '이 기기만' 로그아웃(/logout_local)으로 — 푸시 구독은 보존해 다른 기기 알림은 유지.
    socket.on("force_logout", (e) => {
      const reason = (e && e.reason) || "";
      const byPhone = reason.indexOf("휴대폰") >= 0;
      const msg = byPhone
        ? "휴대폰에서 로그아웃하여 이 PC도 함께 로그아웃됩니다."
        : "다른 기기에서 로그인되어 이 기기는 로그아웃됩니다.\n(동시 사용은 휴대폰 1대 + PC 1대까지)";
      try { alert(msg); } catch (_) {}
      try { if ('clearAppBadge' in navigator) navigator.clearAppBadge(); } catch (_) {}
      window.location.href = BASE + "/logout_local?r=" + encodeURIComponent(reason);
    });

    socket.on("message_deleted", (data) => {
      try {
        if (!data || !data.message_id) return;
        // 활성 방의 메시지면 즉시 화면 갱신
        if (activeRoom && data.room_id === activeRoom.id) {
          _markMessageAsDeleted(data.message_id);
        }
      } catch (e) {}
    });

    // 스레드가 목록에서 숨겨짐(삭제) — 메시지 내용·답글은 그대로 보존, 목록에서만 제거 (대표 지시 2026-05-29)
    socket.on("thread_deleted", (data) => {
      try {
        if (!data || !data.parent_id) return;
        // 스레드 목록 다이얼로그가 열려 있으면 새로고침 → 숨겨진 항목이 목록에서 사라짐
        try {
          if (els.roomThreadsDialog && els.roomThreadsDialog.open) openRoomThreadsDialog();
        } catch (_) {}
        // 이 부모로 스레드 답글 패널이 열려 있으면 닫기 (목록에서 제거됨)
        try { if (_activeThreadParentId === data.parent_id) closeThreadPanel(); } catch (_) {}
      } catch (e) {}
    });

    // 📢 공지 실시간 반영 (대표 지시 2026-05-29)
    socket.on("notice_added", (data) => {
      try {
        if (!data || !activeRoom || data.room_id !== activeRoom.id) return;
        _addNoticeLocal(data.notice);
        renderNoticeBar(activeRoom.id);
      } catch (e) {}
    });
    socket.on("notice_deleted", (data) => {
      try {
        if (!data || !activeRoom || data.room_id !== activeRoom.id) return;
        _notices = _notices.filter(n => n.id !== data.notice_id);
        renderNoticeBar(activeRoom.id);
      } catch (e) {}
    });

    // 채널/방 아이콘 사진 변경 — 방 목록 즉시 갱신 (대표 지시 2026-05-20)
    socket.on("room_avatar_changed", () => { try { refreshRooms(); } catch (e) {} });

    // 채널 삭제 — 멤버 화면 즉시 갱신 (대표 지시 2026-05-21, 규칙 6)
    socket.on("room_deleted", (data) => {
      try {
        const rid = data && data.room_id;
        if (activeRoom && rid && activeRoom.id === rid) {
          activeRoom = null;
          app.classList.remove("viewing-chat");
        }
        refreshRooms();
      } catch (e) {}
    });

    // 메시지 편집 실시간 알림 — 대표 지시 2026-05-19
    socket.on("message_edited", (data) => {
      try {
        if (!data || !data.message_id) return;
        if (activeRoom && data.room_id === activeRoom.id) {
          _applyMessageEdit(data.message_id, data.content, data.edited_at);
        }
      } catch (e) {}
    });

    socket.on("new_message", (m) => {
      if (activeRoom && m.room_id === activeRoom.id) {
        // 내가 보낸 메시지면 무조건 최하단 (내 발화 보러 가는 게 자연스러움).
        // 남이 보낸 메시지면 nearBottom 가드 — 위쪽 보고 있으면 위치 유지.
        const isMine = m.user_id === meId;
        appendMessage(m, isMine);
        // 새 메시지가 활성 방에 들어옴 → 로컬 close + 서버 clear 푸시 (모바일 OS 알림 회수)
        // 옛 로직: noClearPush:true 로 푸시 생략했으나 모바일에서 페이지 close() 가 안 먹혀
        //         알림 잔존 → 서버 clear 푸시도 같이 보내도록 변경 (대표 지시 2026-05-26)
        api.markRead(activeRoom.id);
        _clearRoomNotifications(activeRoom.id);
      }
      refreshRooms();
      // ===== 알림 분기 (notify.trigger 내부에서 설정·음소거 추가 분기) =====
      // 🚫 DND 모드 → 모든 알림 차단 (배지·미읽기 카운트는 그대로 보임)
      if (window.KNK_DND_ACTIVE) return;
      // 기본: 창이 안 보이거나 다른 방에 있으면 알림.
      // 추가: 사용자가 "현재 방에서도 소리" 설정 켜면 → 같은 방 활성 상태에서도 소리만 재생.
      if (m.user_id !== meId && m.kind !== 'system') {
        const isThisRoomActive = activeRoom && m.room_id === activeRoom.id;
        // ★ 터치 기기(태블릿·폰): document.hasFocus()가 화면 키보드/PWA 때문에
        //   '보고 있는 중'에도 false 가 되어, 현재 방 메시지인데도 알림이 떠서 안 사라지던 문제.
        //   → 터치 기기는 '방 열림 + 화면 보임(!hidden)' 이면 보는 중으로 간주하고 알림 억제.
        //   데스크탑(마우스)은 멀티윈도우 고려해 hasFocus 까지 확인. (대표 지시 2026-05-21)
        const isTouch = window.matchMedia('(pointer: coarse)').matches;
        const viewingThisRoom = isThisRoomActive && !document.hidden
                                && (isTouch || document.hasFocus());
        if (!viewingThisRoom) {
          notify.trigger(m);
        } else {
          // 보고 있는 방 → 시스템 알림·토스트 없음. 혹시 떠 있는 알림도 즉시 정리.
          _clearRoomNotifications(m.room_id);
          if (notifySettings.get('currentRoomSound')
              && notifySettings.get('soundEnabled')
              && !notifySettings.isRoomMuted(m.room_id)) {
            // 현재 방 활성 + currentRoomSound ON + soundEnabled ON → 소리만 (배지·토스트·시스템알림 없이)
            notify.preview();
          }
        }
      }
    });
    // 스레드 답글 실시간 — 현재 열려있는 패널이 같은 부모면 다시 그리기
    socket.on("thread_reply", (e) => {
      if (_activeThreadParentId && e.parent_message_id === _activeThreadParentId) {
        renderThreadPanel(_activeThreadParentId);
      }
    });
    // 스레드 카운트 변경 — 메인 타임라인의 답글 N 배지 갱신
    socket.on("thread_count_changed", async (e) => {
      if (!activeRoom || e.room_id !== activeRoom.id) return;
      // 단순화: 해당 부모 메시지를 다시 조회해 카운트 갱신
      await refreshSingleMessage(e.parent_id);
    });
    socket.on("requests_updated", (e) => {
      if (activeRoom && e.room_id === activeRoom.id) {
        refreshRequestsBadge();
        if (els.requestsDialog.open) renderRequests();
      }
      refreshMyTasksBadge();   // 📌 내 요청 칩 배지 — 모든 방의 요청 변경 반영
      // 내 요청 패널이 열려 있으면 갱신 — 다른 방의 요청 변경(받은·보낸)도 실시간 반영
      if (els.myTasks && !els.myTasks.hidden) {
        renderMyTasks();
      }
    });
    // 내게 온 @멘션 — 실시간 배지 갱신 (서버는 멘션된 본인에게만 emit) (대표 지시 2026-05-22)
    socket.on("mention_added", () => {
      refreshMentionBadge();
      if (activeFilter === "mentions" && els.mentionsPanel && !els.mentionsPanel.hidden) openMentions();   // 멘션 패널 보고 있으면 즉시 갱신
    });
    socket.on("reaction_updated", async (e) => {
      if (!activeRoom || e.room_id !== activeRoom.id) return;
      await refreshSingleMessage(e.message_id);
    });
    socket.on("ack_updated", async (e) => {
      if (!activeRoom) return;
      await refreshSingleMessage(e.message_id);
    });
    // 다른 사람이 메시지를 읽으면 → 내 화면의 "안 읽음 N" 숫자 갱신
    socket.on("read_status", (e) => {
      if (!activeRoom || e.room_id !== activeRoom.id) return;
      // 메모리 상태만 빠르게 업데이트 (API 재호출 없이)
      const m = roomReadStatus.members.find(x => x.user_id === e.user_id);
      if (m) m.last_read_message_id = e.last_read;
      // 모든 메시지의 read-badge 다시 그리기 (내 것 + 남의 것) — 작성자 제외, 귓속말은 수신자 1명만 기준
      els.messages.querySelectorAll(".msg").forEach(li => {
        const mid = parseInt(li.dataset.msgId, 10);
        const badge = li.querySelector(".read-badge");
        if (!badge) return;
        const whisperTo = parseInt(li.dataset.whisperTo, 10);
        const senderId = parseInt(li.dataset.uid, 10);
        let others;
        if (whisperTo) {
          others = roomReadStatus.members.filter(mb => mb.user_id === whisperTo);
        } else {
          others = roomReadStatus.members.filter(mb => mb.user_id !== senderId);
        }
        const unreadBy = others.filter(mb => (mb.last_read_message_id || 0) < mid);
        if (others.length === 0) {
          badge.remove();
          return;
        }
        if (unreadBy.length === 0) {
          badge.className = "read-badge all-read";
          badge.textContent = "읽음";
          badge.title = "모두 읽음";
        } else {
          badge.className = "read-badge unread";
          badge.textContent = unreadBy.length;
          badge.title = "안 읽음: " + unreadBy.map(x => x.display_name).join(", ");
        }
      });
    });
  }

  // ============================================================
  // 알림 시스템 — 창 비활성/최소화 시에도 새 메시지 인지 (4중망)
  //   1. Web Notification API (시스템 토스트)
  //   2. 페이지 제목 깜빡임 ("(3) KNK 메신저")
  //   3. Favicon 빨간 점 (작업표시줄 아이콘 배지)
  //   4. PWA 배지 (navigator.setAppBadge 지원 브라우저)
  //   5. 소리 (Web Audio - ding/chime/soft 3종 + 음량 조절)
  //   6. 화면 내 토스트 (우상단 미리보기 5초)
  //   7. 사이드바 방 항목 깜빡임 (5회 펄스)
  // 사용자 설정: notifySettings 모듈 — localStorage 저장, 데스크톱·모바일 동일.
  // ============================================================

  // ─── 알림 설정 — localStorage 영속 + 방별 음소거 지원 ───
  const NS_KEY = 'knkmsg.notifySettings';
  const NS_DEFAULTS = {
    soundEnabled: true,
    volume: 0.5,                // 0.0 ~ 1.0
    soundType: 'ding',           // 'ding' | 'chime' | 'soft'
    currentRoomSound: false,     // 현재 보고 있는 방에서도 소리
    systemNotification: true,    // OS 시스템 알림 토스트
    // titleBlink·inlineToast·sidebarBlink 제거됨 (2026-05-26) — 실효성 없음 (모바일 무의미·중복 등)
    mutedRooms: [],              // 음소거 방 ID 배열
  };
  const notifySettings = {
    _data: null,
    load() {
      if (this._data) return this._data;
      try {
        const s = localStorage.getItem(NS_KEY);
        // 기존 knkmsg.soundEnabled 키에서 마이그레이션
        const legacy = localStorage.getItem('knkmsg.soundEnabled');
        const init = legacy !== null ? { ...NS_DEFAULTS, soundEnabled: legacy !== '0' } : { ...NS_DEFAULTS };
        this._data = s ? Object.assign({}, init, JSON.parse(s)) : init;
      } catch (e) { this._data = { ...NS_DEFAULTS }; }
      return this._data;
    },
    save() {
      try { localStorage.setItem(NS_KEY, JSON.stringify(this._data)); } catch (e) {}
    },
    get(k) { return this.load()[k]; },
    set(k, v) { this.load()[k] = v; this.save(); },
    isRoomMuted(roomId) {
      return (this.load().mutedRooms || []).includes(roomId);
    },
    toggleRoomMute(roomId) {
      const d = this.load();
      d.mutedRooms = d.mutedRooms || [];
      const i = d.mutedRooms.indexOf(roomId);
      if (i >= 0) d.mutedRooms.splice(i, 1);
      else d.mutedRooms.push(roomId);
      this.save();
      return d.mutedRooms.includes(roomId);
    },
  };

  // ─── 휴대폰 PWA 호환 — WAV blob 런타임 생성 (HTMLAudio 폴백용) ───
  // Web Audio API 가 휴대폰 PWA 에서 작동 안 하는 케이스가 있어, WAV 파일로 변환해서
  // <audio> 태그로 재생. <audio> 는 미디어 볼륨 채널을 명시적으로 사용 → 더 안정적.
  function makeNotificationWav(type, vol) {
    const sampleRate = 22050;
    let duration, samples;
    const segments = [];
    if (type === 'chime') {
      // C5 → E5 두 음 (각 0.25초씩, 0.05초 간격)
      duration = 0.55;
      samples = Math.floor(sampleRate * duration);
      const buf = new Float32Array(samples);
      const notes = [{ f: 523.25, start: 0 }, { f: 659.25, start: 0.10 }];
      notes.forEach(n => {
        const startIdx = Math.floor(n.start * sampleRate);
        for (let i = 0; i < sampleRate * 0.4 && startIdx + i < samples; i++) {
          const t = i / sampleRate;
          const env = Math.exp(-t * 4);   // exponential decay
          buf[startIdx + i] += vol * 0.5 * env * Math.sin(2 * Math.PI * n.f * t);
        }
      });
      segments.push(buf);
    } else if (type === 'soft') {
      // triangle 800Hz 부드러운 fade in/out
      duration = 0.6;
      samples = Math.floor(sampleRate * duration);
      const buf = new Float32Array(samples);
      for (let i = 0; i < samples; i++) {
        const t = i / sampleRate;
        let env;
        if (t < 0.05) env = t / 0.05;          // 50ms fade in
        else env = Math.exp(-(t - 0.05) * 4);   // exp decay
        // triangle wave
        const phase = (800 * t) % 1;
        const tri = phase < 0.5 ? (4 * phase - 1) : (3 - 4 * phase);
        buf[i] = vol * 0.4 * env * tri;
      }
      segments.push(buf);
    } else {
      // ding — 880Hz → 440Hz exponential glide
      duration = 0.35;
      samples = Math.floor(sampleRate * duration);
      const buf = new Float32Array(samples);
      for (let i = 0; i < samples; i++) {
        const t = i / sampleRate;
        const env = Math.exp(-t * 6);
        const freq = 880 * Math.pow(0.5, t * 4);  // 880 → ~440 exp
        buf[i] = vol * 0.6 * env * Math.sin(2 * Math.PI * freq * t);
      }
      segments.push(buf);
    }
    const float = segments[0];
    // PCM 16-bit mono WAV header (44 bytes) + data
    const dataLen = float.length * 2;
    const buffer = new ArrayBuffer(44 + dataLen);
    const view = new DataView(buffer);
    // RIFF chunk descriptor
    [82, 73, 70, 70].forEach((b, i) => view.setUint8(i, b));         // "RIFF"
    view.setUint32(4, 36 + dataLen, true);
    [87, 65, 86, 69].forEach((b, i) => view.setUint8(8 + i, b));     // "WAVE"
    // fmt chunk
    [102, 109, 116, 32].forEach((b, i) => view.setUint8(12 + i, b)); // "fmt "
    view.setUint32(16, 16, true);                // PCM chunk size
    view.setUint16(20, 1, true);                  // format=PCM
    view.setUint16(22, 1, true);                  // mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);     // byte rate
    view.setUint16(32, 2, true);                  // block align
    view.setUint16(34, 16, true);                 // bits per sample
    // data chunk
    [100, 97, 116, 97].forEach((b, i) => view.setUint8(36 + i, b)); // "data"
    view.setUint32(40, dataLen, true);
    // PCM samples
    for (let i = 0; i < float.length; i++) {
      const s = Math.max(-1, Math.min(1, float[i]));
      view.setInt16(44 + i * 2, Math.floor(s * 32767), true);
    }
    return new Blob([buffer], { type: 'audio/wav' });
  }

  const notify = (() => {
    let unreadCount = 0;
    let lastNotifyAt = {};  // room_id -> timestamp (스팸 방지)
    let audioCtx = null;
    let originalFaviconUrl = null;
    let permissionAsked = false;

    // ----- 권한 요청 (1회) -----
    async function ensurePermission() {
      if (!('Notification' in window)) return false;
      if (Notification.permission === 'granted') return true;
      if (Notification.permission === 'denied') return false;
      if (permissionAsked) return false;
      permissionAsked = true;
      try {
        const result = await Notification.requestPermission();
        return result === 'granted';
      } catch (e) { return false; }
    }

    // ----- 페이지 제목 변경 — 2026-05-26 옵션 제거되어 NO-OP (호출처는 그대로 두어 안전) -----
    function updateTitle() { /* removed */ }

    // ----- Favicon 빨간 점 -----
    function setFaviconBadge(show) {
      try {
        const linkEls = document.querySelectorAll('link[rel*="icon"]');
        if (!originalFaviconUrl && linkEls.length) {
          originalFaviconUrl = linkEls[0].href;
        }
        if (!show) {
          if (originalFaviconUrl) {
            linkEls.forEach(l => l.href = originalFaviconUrl);
          }
          return;
        }
        // 빨간 점 그려진 favicon 동적 생성
        const canvas = document.createElement('canvas');
        canvas.width = 64; canvas.height = 64;
        const ctx = canvas.getContext('2d');
        // 배경 (KNK 로고 대체 — 파란 원)
        ctx.fillStyle = '#A5282C';
        ctx.beginPath();
        ctx.arc(32, 32, 28, 0, Math.PI * 2);
        ctx.fill();
        // K 글자
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 32px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('K', 32, 34);
        // 빨간 점 (우상단)
        ctx.fillStyle = '#ef4444';
        ctx.beginPath();
        ctx.arc(50, 14, 12, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 14px sans-serif';
        ctx.fillText(unreadCount > 9 ? '9+' : String(unreadCount), 50, 15);
        const url = canvas.toDataURL('image/png');
        linkEls.forEach(l => { if (!l.rel.includes('apple')) l.href = url; });
      } catch (e) { /* ignore */ }
    }

    // ----- PWA 배지 (App Badge API) -----
    function setAppBadge(n) {
      if ('setAppBadge' in navigator) {
        navigator.setAppBadge(n).catch(() => {});
      }
    }

    // ----- 소리 (Web Audio) — 3종(ding/chime/soft) + 음량 -----
    // 휴대폰/PWA 에서 AudioContext 가 'suspended' 상태로 시작되거나 백그라운드 복귀 시
    // suspend 되는 케이스 대응 — 매 호출마다 state 체크 후 resume.
    async function ensureCtx() {
      if (!audioCtx) {
        try {
          audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        } catch (e) {
          console.log("AudioContext 생성 실패:", e);
          return null;
        }
      }
      if (audioCtx.state === "suspended") {
        try { await audioCtx.resume(); } catch (e) { console.log("AudioContext resume 실패:", e); }
      }
      return audioCtx;
    }
    function playDing(vol) {
      const ctx = audioCtx;
      if (!ctx) return;
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.type = 'sine';
      o.frequency.setValueAtTime(880, ctx.currentTime);
      o.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.15);
      g.gain.setValueAtTime(vol * 0.3, ctx.currentTime);
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
      o.start();
      o.stop(ctx.currentTime + 0.3);
    }
    function playChime(vol) {
      // C5 → E5 두 음 연달아 (밝고 부드러움)
      const ctx = audioCtx;
      if (!ctx) return;
      [523.25, 659.25].forEach((freq, i) => {
        const o = ctx.createOscillator(), g = ctx.createGain();
        o.connect(g); g.connect(ctx.destination);
        o.type = 'sine';
        const t0 = ctx.currentTime + i * 0.1;
        o.frequency.setValueAtTime(freq, t0);
        g.gain.setValueAtTime(0, t0);
        g.gain.linearRampToValueAtTime(vol * 0.25, t0 + 0.02);
        g.gain.exponentialRampToValueAtTime(0.001, t0 + 0.4);
        o.start(t0);
        o.stop(t0 + 0.4);
      });
    }
    function playSoft(vol) {
      // triangle 800Hz 약한 attack — 부드러운 알림
      const ctx = audioCtx;
      if (!ctx) return;
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.type = 'triangle';
      o.frequency.setValueAtTime(800, ctx.currentTime);
      g.gain.setValueAtTime(0, ctx.currentTime);
      g.gain.linearRampToValueAtTime(vol * 0.22, ctx.currentTime + 0.05);
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
      o.start();
      o.stop(ctx.currentTime + 0.6);
    }
    async function playSound(forcePreview) {
      const s = notifySettings.load();
      if (!forcePreview && !s.soundEnabled) return;
      const vol = (typeof s.volume === 'number') ? s.volume : 0.5;
      const t = s.soundType || 'ding';
      let webAudioOk = false;
      // 1) Web Audio 우선 시도
      try {
        await ensureCtx();
        if (audioCtx && audioCtx.state === "running") {
          if (t === 'chime') playChime(vol);
          else if (t === 'soft') playSoft(vol);
          else playDing(vol);
          webAudioOk = true;
        }
      } catch (e) { console.log("Web Audio 실패:", e); }
      // 2) Web Audio 안 됐으면 HTMLAudio fallback (휴대폰 PWA 호환)
      if (!webAudioOk) {
        try {
          const blob = makeNotificationWav(t, vol);
          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          audio.volume = Math.min(1.0, vol * 1.5);
          await audio.play();
          audio.addEventListener('ended', () => URL.revokeObjectURL(url));
        } catch (e) { console.log("HTMLAudio fallback 실패:", e); }
      }
    }

    // (옛 화면 안 토스트 / blinkSidebarRoom — 2026-05-26 옵션 자체 제거)

    // ----- 트리거 -----
    async function trigger(msg) {
      // 방 음소거: unread 카운트만 올리고 알림 동작 모두 스킵
      if (notifySettings.isRoomMuted(msg.room_id)) {
        unreadCount++;
        updateTitle();
        setFaviconBadge(true);
        setAppBadge(unreadCount);
        return;
      }
      unreadCount++;
      updateTitle();
      setFaviconBadge(true);
      setAppBadge(unreadCount);
      // 같은 방 연속 메시지 5초 내 중복 알림 차단
      // (사이드바 깜빡임 옵션은 시각 효과 미미·안읽음 뱃지와 중복으로 2026-05-26 제거)
      const now = Date.now();
      const last = lastNotifyAt[msg.room_id] || 0;
      if (now - last < 5000) return;
      lastNotifyAt[msg.room_id] = now;

      // 소리
      playSound();

      const senderName = msg.display_name || '누군가';
      const room = rooms.find(r => r.id === msg.room_id);
      const roomName = room ? (room.name || '대화방') : '대화방';
      const body = msg.kind === 'text' ? (msg.content || '').slice(0, 100) :
                   msg.kind === 'image' ? '📷 사진' :
                   msg.kind === 'file' ? '📎 파일' :
                   msg.kind === 'sticker' ? '🐶 ' + (msg.content || '스티커') : msg.content;

      // 🔒 알림 내용 숨기기 — 켜져 있으면 발신자·내용 가리고 'KNK message' 만 (대표 지시 2026-05-26)
      const hidePreview = !!notifySettings.get('hidePreview');
      const dispBody    = hidePreview ? '' : body;

      // 시스템 알림 (OS 토스트) — 옛 inlineToast 옵션은 2026-05-26 옵션 자체 제거됨
      if (!notifySettings.get('systemNotification')) return;
      const ok = await ensurePermission();
      if (!ok) return;
      try {
        const sysTitle = hidePreview ? 'KNK message' : `${senderName} — ${roomName}`;
        const n = new Notification(sysTitle, {
          body: dispBody,
          icon: BASE + '/static/icons/icon-192.png',
          badge: BASE + '/static/icons/icon-192.png',
          tag: `room_${msg.room_id}`,
          renotify: false,
          requireInteraction: false,
        });
        n.onclick = () => {
          window.focus();
          n.close();
          const r = rooms.find(x => x.id === msg.room_id);
          if (r) openRoom(r);
        };
        setTimeout(() => { try { n.close(); } catch (e) {} }, 7000);
      } catch (e) { /* ignore */ }
    }

    // ----- 창 활성 시 정리 -----
    function clearAll() {
      unreadCount = 0;
      updateTitle();
      setFaviconBadge(false);
      setAppBadge(0);
      lastNotifyAt = {};
      // 창이 다시 보이면(화면 켜짐/포커스) 지금 보고 있는 방의 OS 알림도 닫음 — 직접 누르지 않아도 사라지게
      try { if (activeRoom) _clearRoomNotifications(activeRoom.id); } catch (e) {}
    }

    // ----- 소리 on/off (레거시 호환) -----
    function toggleSound() {
      const cur = notifySettings.get('soundEnabled');
      notifySettings.set('soundEnabled', !cur);
      return !cur;
    }

    // 창 다시 보이면 미읽기 카운트 초기화
    window.addEventListener('focus', clearAll);
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) clearAll();
    });

    return {
      trigger, clearAll, toggleSound, ensurePermission,
      isSoundOn: () => notifySettings.get('soundEnabled'),
      preview: () => playSound(true),    // 미리듣기 (설정 OFF 여도 강제 재생)
      getAudioState: () => audioCtx,     // 진단용 (state, sampleRate 등 노출)
    };
  })();

  // 첫 로드 후 3초 뒤 권한 요청 (사용자에게 즉시 안 묻고 자연스럽게)
  // 자동 권한 요청 — iOS Safari 는 user activation 없이 호출 시 즉시 거부됨.
  // iOS 가 아니거나 PWA standalone 모드에서만 자동 요청. 그 외에는 사용자가 🔔 클릭할 때만.
  setTimeout(() => {
    const env = detectIOS();
    if (!env.isIOS || env.isStandalone) {
      notify.ensurePermission();
    }
    // iOS Safari 일반 모드: 자동 호출 안 함 → 사용자가 🔔 버튼 클릭 시 (3079, 3193) 자연스럽게 요청
  }, 3000);

  // ---------- wire ----------
  els.composer.addEventListener("submit", (e) => { e.preventDefault(); send(); });

  // ─── 메시지 입력 textarea — Enter 전송 / Shift+Enter 줄바꿈 / 자동 높이 조절 ───
  // 1) 키다운: 데스크톱 Enter = 전송, Shift+Enter = 줄바꿈.
  //    한국어 IME 조합 중 Enter 는 조합 완료용이라 무시(오발송 방지) — 표준 동작.
  //    모바일(터치)은 Enter = 줄바꿈, 전송은 ▶ 버튼 (모바일 가상 키보드 표준).
  els.msgInput.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    if (e.isComposing || e.keyCode === 229) return;  // IME 조합 중 — 그대로 둠
    if (e.shiftKey) return;                          // Shift+Enter → 줄바꿈 (기본)
    if (window.matchMedia("(pointer: coarse)").matches) return;  // 모바일 → 줄바꿈
    // 멘션 자동완성 팝업 떠 있으면 Enter = 멘션 선택 (그쪽 핸들러에 위임)
    if (document.querySelector(".mention-popup")) return;
    e.preventDefault();                              // 데스크톱 Enter → 전송
    send();
  });
  // 2) input 이벤트: 글자 입력·삭제·붙여넣기 등 모든 변경에 반응해 높이 자동 조절.
  els.msgInput.addEventListener("input", autoGrowMsgInput);
  // 3) 초기 1회 — 페이지 로드 직후(빈 상태) 높이 셋업
  autoGrowMsgInput();

  // 채팅방 -> 방목록 복귀 (헤더 ← 버튼 또는 브라우저 뒤로가기)
  function leaveRoomView(opts) {
    opts = opts || {};
    try { closeMessageContextMenu(); } catch (_) {}   // 길게누름 메뉴가 떠 있으면 닫고 나가기 (대표 지시 2026-05-23)
    app.classList.remove("viewing-chat");
    try { _hideNoticeBar(); } catch (e) {}   // 📢 방 나갈 때 공지 막대 숨김
    try { _clearPendingFiles(); } catch (e) {}   // 📎 담긴 첨부 비움
    // ※ emit("leave") 안 함 — 모든 방 join 유지해서 알림 받음. activeRoom 만 null 처리.
    activeRoom = null;
    // ★ 서버·SW 의 active_room 도 클리어 — 안 그러면 서버가 그 방 푸시 계속 차단 (왔다 안왔다 원인)
    try { _notifySWActiveRoom(null); } catch (e) {}
    els.chatTitle.textContent = "대화를 선택하세요";
    els.itemMeta.hidden = true;
    els.itemMeta.innerHTML = "";
    els.itemEditBtn.hidden = true;
    els.galleryBtn.hidden = true;
    els.requestsBtn.hidden = true;
    els.requestsBadge.hidden = true;
    if (els.exportBtn) els.exportBtn.hidden = true;
    if (els.leaveRoomBtn) els.leaveRoomBtn.hidden = true;
    if (els.starredBtn) els.starredBtn.hidden = true;
    if (els.aiSummaryBtn) els.aiSummaryBtn.hidden = true;
    if (els.aiRewriteBtn) els.aiRewriteBtn.disabled = true;
    if (els.emojiBtn) els.emojiBtn.disabled = true;
    if (els.stickerBtn) els.stickerBtn.disabled = true;
    if (els.projectHistoryBtn) els.projectHistoryBtn.hidden = true;
    if (els.roomThreadsBtn) els.roomThreadsBtn.hidden = true;
    if (els.roomSearchBtn) els.roomSearchBtn.hidden = true;
    if (window._closeChatSearch) { try { window._closeChatSearch(); } catch (_) {} }
    const _rsBtn = document.getElementById('roomSettingsBtn');
    if (_rsBtn) _rsBtn.hidden = true;
    if (els.headMoreBtn) els.headMoreBtn.hidden = true;
    if (els.headMoreMenu) els.headMoreMenu.hidden = true;
    if (els.composerLangbar) els.composerLangbar.hidden = true;
    const composer = $("composer");
    composer.classList.remove("tr-vi", "tr-en", "tr-ko");
    els.msgInput.disabled = true;
    els.sendBtn.disabled = true;
    els.attachBtn.disabled = true;
    els.messages.innerHTML = "";
    // 모바일: 헤더 ← 클릭이면 history 도 뒤로 (popstate 호출), popstate 트리거이면 이미 history 가 뒤로 가 있음
    if (!opts.fromPopstate && history.state && history.state.knkRoom) {
      try { history.back(); } catch(e) {}
    }
    refreshRooms();
  }
  els.backBtn.addEventListener("click", () => leaveRoomView());
  // 번역 줄 오른쪽 끝 뒤로가기 — 입력 중 가까이서 누름 (대표 지시 2026-05-23)
  const _lbBack = document.getElementById("langbarBackBtn");
  if (_lbBack) _lbBack.addEventListener("click", () => leaveRoomView());

  // 브라우저 뒤로가기 = 방목록으로 (로그아웃 X)
  window.addEventListener("popstate", () => {
    // 0. 첨부 미리보기(라이트박스)가 열려 있으면 그것부터 닫기 — 뒤로 1회 = 미리보기만 닫힘(방 유지).
    if (_lbIgnorePop) { _lbIgnorePop = false; return; }   // 수동 닫기로 우리가 한 back → 무시
    if (_lbStatePushed) {
      _lbClosingFromPop = true;
      try { els.lightbox.close(); } catch (e) {}
      _lbClosingFromPop = false;
      return;
    }
    // 1. 수동 닫기로 우리가 history.back 한 popstate → 무시 (이미 메뉴 닫힘)
    if (_ctxIgnorePop) { _ctxIgnorePop = false; return; }
    // 2. 컨텍스트 메뉴가 열려 있으면 먼저 닫기 — 뒤로 1회 = 메뉴만 닫힘, 2회째에 창 이동
    if (_ctxMenuStatePushed) {
      _ctxMenuStatePushed = false;
      closeUserContextMenu({ fromPopstate: true });
      return;
    }
    // 3. 방 보는 중이면 방 목록으로
    if (app.classList.contains("viewing-chat")) {
      leaveRoomView({ fromPopstate: true });
    }
  });

  // ===== 모바일 키보드 가림 방지 (visualViewport 정밀 처리) =====
  // iOS Safari / Android Chrome 의 키보드가 올라올 때:
  //   - visualViewport.height: 키보드 뺀 실제 가시 영역
  //   - visualViewport.offsetTop: 페이지 자체가 스크롤된 만큼
  // chat-app 의 height 를 vvh 로 잡으면 키보드 위만큼만 차지 → composer 자동으로 보임
  // ===== VirtualKeyboard API (Chrome 94+) =====
  // overlaysContent = false 로 명시 — 키보드가 콘텐츠를 '덮지' 않고 '밀어올림(resize)'.
  //  뷰포트 메타의 interactive-widget=resizes-content 와 일치시켜 키보드가 뜨면
  //  layout/visual viewport(innerHeight·100dvh·visualViewport.height) 가 함께 줄어듦
  //  → 흐름 안의 입력창이 자동으로 키보드 위로. (이전 overlaysContent=true 는 메타와 충돌해
  //   화면이 안 줄고 입력창 버튼줄이 키보드에 가려지던 원인. 대표 지시 2026-05-21)
  if ('virtualKeyboard' in navigator) {
    try { navigator.virtualKeyboard.overlaysContent = false; } catch (e) {}
  }

  // composer-area 는 position:fixed; bottom:0; 으로 layout viewport 하단 고정
  // 키보드 올라오면 visual viewport 가 줄어들지만 layout viewport(window.innerHeight)는 유지됨 (Samsung 등)
  // → 그 차이만큼 composer-area 를 transform: translateY(-gap) 으로 위로 밀어 키보드 바로 위 배치
  const updateViewport = () => {
    const vv = window.visualViewport;
    // 핀치 줌(두 손가락 확대) 중에는 visualViewport 가 줄어드는데 이를 '키보드'로 오인해
    // 레이아웃을 줄이면 줌이 깨짐 → 줌 중(scale>1)에는 높이 재계산을 스킵해 줌을 그대로 둠 (대표 지시 2026-06-07)
    if (vv && (vv.scale || 1) > 1.01) return;
    const innerH = window.innerHeight;
    const vvHeight = vv ? Math.round(vv.height) : innerH;
    let vvOffsetTop = vv ? Math.round(vv.offsetTop) : 0;

    // ===== 키보드 높이 계산 — 두 측정값 중 '더 큰' 값 채택 =====
    // 입력창이 키보드(특히 삼성 키보드의 상단 추천·아이콘 툴바)에 살짝 가려지는 문제 보정.
    //  · kbFromVV  : visualViewport 가 줄어든 양 = innerH - vv.height - offsetTop
    //                (브라우저가 키보드+툴바 전체를 반영 → 보통 가장 정확)
    //  · kbFromAPI : VirtualKeyboard API boundingRect (overlaysContent=true 일 때만 값 나옴)
    //                일부 키보드는 상단 툴바를 빼고 보고 → 더 작게 나와 입력창이 가려짐.
    // → 둘 중 큰 값을 키보드 높이로 써서 입력창을 확실히 키보드 위로. (대표 지시 2026-05-21)
    const kbFromVV = vv ? Math.max(0, innerH - vvHeight - vvOffsetTop) : 0;
    let kbFromAPI = 0;
    if ('virtualKeyboard' in navigator && navigator.virtualKeyboard.boundingRect) {
      kbFromAPI = Math.round(navigator.virtualKeyboard.boundingRect.height || 0);
    }
    const kbH = Math.max(kbFromVV, kbFromAPI);
    // 키보드가 떠 있으면 innerH-kbH, 아니면 visualViewport 높이 그대로.
    let vvH = kbH > 0 ? (innerH - kbH) : vvHeight;

    document.documentElement.style.setProperty('--vvh', vvH + 'px');
    // body·chat-app 의 inline height 강제는 진짜 모바일(터치)만.
    // ★ 핵심: pointer:coarse 단독으로 판정. (max-width:720px OR 는 PC 의 좁은 PWA 창도
    //   모바일로 잘못 매칭해서 zoom 0.72 환경의 CSS calc 를 덮어쓰게 됨 → 빈 영역 발생.)
    const isMobileEnv = window.matchMedia('(pointer: coarse)').matches;
    // 폰 레이아웃(단일 화면 + composer position:fixed)인지 — 태블릿(coarse+넓은화면=2단 레이아웃)과 구분.
    // composer 의 translateY 키보드 보정은 position:fixed 인 폰에서만 의미 있음.
    const isPhoneLayout = window.matchMedia('(max-width: 720px) and (pointer: coarse)').matches;
    if (isMobileEnv && document.body.classList.contains('chat-body')) {
      document.body.style.height = vvH + 'px';
      // 휴대폰 최상단 브랜드 띠(.mobile-top-brand)는 #app 위에 있으므로, 그 높이만큼 빼야
      // 하단(접기 메뉴 등)이 안 잘림. 띠가 없으면(데스크탑·태블릿=display:none) offsetHeight 0. (대표 지시 2026-06-07)
      const _brandEl = document.querySelector('.mobile-top-brand');
      const _brandH = (_brandEl && _brandEl.offsetHeight) ? _brandEl.offsetHeight : 0;
      const _chatApp = document.querySelector('.chat-app');
      if (_chatApp) _chatApp.style.height = (vvH - _brandH) + 'px';
    } else if (document.body.classList.contains('chat-body')) {
      // PC: 이전에 잘못 박힌 inline style 이 남아있으면 제거 → CSS calc(100dvh/0.72) 복귀
      if (document.body.style.height) document.body.style.height = '';
      const _chatApp = document.querySelector('.chat-app');
      if (_chatApp && _chatApp.style.height) _chatApp.style.height = '';
    }
    // 페이지가 키보드 때문에 스크롤되었으면 강제로 위로 복귀 (Android 일부에서 발생)
    if (vv && vv.offsetTop !== 0) {
      window.scrollTo(0, 0);
      vvOffsetTop = 0;
    }
    // ----- composer-area 위치 보정 -----
    const area = document.getElementById('composerArea');
    if (area) {
      // composer 위치 보정(translateY)은 composer 가 position:fixed 인 '폰 레이아웃'에서만.
      //  · 폰(max-width:720px + coarse): composer 가 fixed → layout viewport 하단에 고정되므로
      //    키보드 높이(gap)만큼 위로 translateY 해야 키보드 바로 위에 붙음.
      //  · 태블릿(coarse + 넓은화면): 2단 레이아웃에서 composer 가 flex 흐름 안(고정 아님).
      //    chat-app.height=vvh 로 이미 키보드 위로 올라와 있어서 translateY 주면 중간으로 떠오름(버그).
      //  · 데스크탑(마우스): 가로 스크롤바 등으로 gap 생겨 흔들릴 수 있어 미적용. (대표 지시 2026-05-20)
      if (isPhoneLayout) {
        const layoutBottom = innerH;
        const visualBottom = vvOffsetTop + vvH;
        const gap = Math.max(0, Math.round(layoutBottom - visualBottom));
        area.style.transform = gap > 0 ? `translateY(-${gap}px)` : 'translateY(0)';
      } else if (area.style.transform) {
        area.style.transform = '';
      }
      // padding-bottom = composer-area 자체 높이만.
      // 키보드 영역은 body.height=vvh 로 이미 잘려 있음 (chat-app/chat-pane 도 vvh 안에 들어감).
      // gap 을 padding 에 더하면 messages scrollable 영역 안에 빈 여백이 생겨서
      // 사용자가 위로 스크롤 시 메시지 사라지고 빈 공간만 보임 → 추가 금지.
      const areaH = area.offsetHeight;
      if (areaH > 0) {
        document.documentElement.style.setProperty('--composer-area-h', areaH + 'px');
      }
    }
    // 메시지 영역을 가장 아래로 — 사용자가 맨 아래 근처면 force, 위쪽 보고 있으면 유지.
    // ★ 단, 사용자가 직접 스크롤(휠·터치) 중이면 건드리지 않음 — 250ms 폴링이 스크롤을 다시
    //   바닥으로 끌어내리던 문제 수정(올렸다 내려옴). 새 메시지 자동하단·키보드 따라가기는 별도 경로. (대표 지시 2026-06-02)
    if (els.messages && els.messages.scrollHeight > 0 && !_userTouchedMessages && !_jumpTargetMsgId) {
      const m = els.messages;
      const distFromBottom = m.scrollHeight - m.scrollTop - m.clientHeight;
      if (distFromBottom <= 150) m.scrollTop = m.scrollHeight;
    }
  };

  // VirtualKeyboard API 이벤트도 같이 구독
  if ('virtualKeyboard' in navigator) {
    try {
      navigator.virtualKeyboard.addEventListener('geometrychange', updateViewport);
    } catch (e) {}
  }
  // window resize/scroll 도 안전망으로 구독
  window.addEventListener('resize', () => requestAnimationFrame(updateViewport));
  window.addEventListener('scroll', () => requestAnimationFrame(updateViewport), { passive: true });
  // composer-area 높이 변화 추적 (langbar 표시·숨김, 줄바꿈 등) → --composer-area-h 즉시 갱신
  const _composerArea = document.getElementById('composerArea');
  if (_composerArea && window.ResizeObserver) {
    new ResizeObserver(() => {
      const h = _composerArea.offsetHeight;
      if (h > 0) {
        document.documentElement.style.setProperty('--composer-area-h', h + 'px');
        // 컴포저가 커지면(번역바 표시·여러 줄 입력) 하단 패딩이 늘어 마지막 메시지가 가려질 수 있음
        // → 사용자가 맨 아래 근처를 보고 있으면 다시 최하단으로 (위쪽 보고 있으면 유지)
        if (els.messages && !_userTouchedMessages && !_jumpTargetMsgId) {   // 사용자가 직접 스크롤 중·점프 중이면 건드리지 않음
          const m = els.messages;
          const dist = m.scrollHeight - m.scrollTop - m.clientHeight;
          if (dist <= 200) m.scrollTop = m.scrollHeight;
        }
      }
    }).observe(_composerArea);
  }
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', updateViewport);
    window.visualViewport.addEventListener('scroll', updateViewport);
    updateViewport();
  } else {
    // Fallback: orientation/resize
    window.addEventListener('resize', () => {
      document.documentElement.style.setProperty('--vvh', window.innerHeight + 'px');
    });
    document.documentElement.style.setProperty('--vvh', window.innerHeight + 'px');
  }

  // 입력창 focus 시 키보드 올라온 후 약간 대기 후 메시지 영역 최하단으로
  // Samsung Internet 등 일부 안드로이드 브라우저는 visualViewport.resize 가 늦거나 한 번만 발생 → 다중 시점에서 재측정 + 폴링
  let _focusPollTimer = null;
  const onInputFocus = () => {
    // 즉시 한 번
    requestAnimationFrame(() => updateViewport());
    // 키보드 애니메이션 중간 단계들 — 사용자가 입력 focus 한 직후라 무조건 최하단으로
    // (updateViewport 안의 padding 보정 + 여기서 force 스크롤 = 마지막 메시지 입력창 바로 위에 표시)
    [50, 150, 300, 500, 800, 1200].forEach(ms => {
      setTimeout(() => {
        updateViewport();
        if (els.messages) {
          els.messages.scrollTop = els.messages.scrollHeight;
        }
      }, ms);
    });
    // 폴링 안전망 — focus 상태 동안 250ms 마다 재측정
    if (_focusPollTimer) clearInterval(_focusPollTimer);
    _focusPollTimer = setInterval(updateViewport, 250);
  };
  const onInputBlur = () => {
    if (_focusPollTimer) { clearInterval(_focusPollTimer); _focusPollTimer = null; }
    // blur 후 100ms 후 한 번 더 (키보드 닫히는 애니메이션 반영)
    setTimeout(updateViewport, 100);
  };
  els.msgInput.addEventListener('focus', onInputFocus);
  els.msgInput.addEventListener('blur', onInputBlur);

  // iOS 의 input focus 시 페이지가 jump 하는 현상 방지 — 미리 scrollTo(0,0)
  els.msgInput.addEventListener('touchstart', () => { window.scrollTo(0, 0); });

  // pinch zoom 차단 (viewport meta 보조 — gesture 이벤트 차단)
  document.addEventListener('gesturestart', (e) => e.preventDefault(), { passive: false });
  document.addEventListener('gesturechange', (e) => e.preventDefault(), { passive: false });
  // 더블탭 zoom 차단
  let lastTouch = 0;
  document.addEventListener('touchend', (e) => {
    const now = Date.now();
    if (now - lastTouch < 350) {
      e.preventDefault();
    }
    lastTouch = now;
  }, { passive: false });
  els.newRoomBtn.addEventListener("click", openNewRoom);
  // 게스트(고객사)는 방 만들기 불가 — 버튼 숨김 (대표 지시 2026-05-29)
  if (window._meIsGuest && els.newRoomBtn) { els.newRoomBtn.hidden = true; els.newRoomBtn.style.display = "none"; }
  // 게스트(고객사)는 📊 프로젝트 대시보드 · 🌅 오늘할일 다이제스트 사용 불가 — 아이콘 숨김 (대표 지시 2026-05-30)
  if (window._meIsGuest) {
    const _gHide = (el) => { if (el) { el.hidden = true; el.style.display = "none"; } };
    _gHide(document.getElementById("dashboardLink"));
    _gHide(els.digestBtn);
  }
  els.cancelNewRoom.addEventListener("click", () => els.newRoomDialog.close());
  els.newRoomForm.addEventListener("submit", createRoom);
  // 다이얼로그 닫힐 때 키보드 적응 height 원복 (2026-05-20)
  els.newRoomDialog.addEventListener("close", () => {
    try { if (typeof _resetKeyboardAwareHeight === "function") _resetKeyboardAwareHeight(); } catch(e) {}
  });

  els.newRoomDialog.querySelectorAll(".tab").forEach(t => {
    t.addEventListener("click", () => setTab(t.dataset.tab));
  });

  els.filterBar.querySelectorAll(".chip").forEach(c => {
    c.addEventListener("click", () => {
      // 사용자 탭에서 방 필터 칩(전체/프로젝트/1:1/그룹/채널/내 요청/멘션)을 누르면
      // 자동으로 '방' 탭으로 전환 (대표 지시 2026-05-20)
      if (typeof _sidebarTab !== "undefined" && _sidebarTab !== "rooms") {
        setSidebarTab("rooms");
      }
      activeFilter = c.dataset.filter;
      window._searchTopRoomId = null;   // 필터를 직접 고르면 검색-맨위고정 해제 → 정상 순서 (대표 지시 2026-06-06)
      els.filterBar.querySelectorAll(".chip").forEach(x => x.classList.toggle("active", x === c));
      els.searchResults.hidden = true;
      els.globalSearch.value = "";
      renderRoomList();
    });
  });

  els.itemEditBtn.addEventListener("click", openItemEdit);
  els.cancelEdit.addEventListener("click", () => els.itemEditDialog.close());
  els.itemEditForm.addEventListener("submit", saveItemEdit);

  // 방 설정 버튼 (데스크탑 헤더 직접 + 모바일 ⋮ 메뉴)
  const _rsBtnEl = document.getElementById('roomSettingsBtn');
  if (_rsBtnEl) _rsBtnEl.addEventListener('click', () => openRoomSettings());

  els.attachBtn.addEventListener("click", () => els.fileInput.click());
  // 📷 화면 캡처 버튼 — 별도 캡처 창(/capture)을 띄워 화면 잡기 + 영역 잘라내기 → 채팅에 첨부.
  //   메인 채팅창은 그대로 사용 가능. (대표 지시 2026-06-06)
  if (els.captureBtn) {
    if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) els.captureBtn.hidden = false;
    els.captureBtn.addEventListener("click", () => { _openCaptureWindow(); });
  }
  // 검색·만들기 줄 '아래 배치' — 전 직원 표준(고정). 위↔아래 토글 버튼은 삭제 (대표 지시 2026-06-06)
  {
    _applySearchBottomLayout(true);   // 하단 배치 항상 적용 — 토글 제거로 이전 저장값(0/1)은 무시
    if (els.bottomBarHandle) {
      els.bottomBarHandle.addEventListener("click", () => {
        const sb = document.querySelector(".sidebar");
        _applyBottomCollapse(!(sb && sb.classList.contains("bottom-collapsed")));
      });
    }
  }
  // 캡처 창(팝업)에서 보낸 이미지 받기 — 같은 출처만 허용, blob 을 '보낼 첨부'로 담음.
  window.addEventListener("message", (e) => {
    if (e.origin !== window.location.origin) return;
    const d = e.data || {};
    if (d.type === "knk-capture-image" && d.blob) {
      try {
        const f = new File([d.blob], d.name || `캡처_${_tsName()}.png`, { type: (d.blob.type || "image/png") });
        _stageFiles([..._pendingFiles, f], _pendingAlbumMode);
        try { window.focus(); } catch (_) {}
        try { _toast("캡처한 부분을 첨부했어요. 전송을 누르면 보내집니다."); } catch (_) {}
      } catch (_) {}
    }
  });

  // 📢 여러 방 동시 공유 — 한 내용을 여러 방에 + 공유 묶음 저장 (대표 지시 2026-06-04)
  if (els.multiShareBtn) els.multiShareBtn.addEventListener("click", () => openMultiShare(els.msgInput ? els.msgInput.value : ""));
  function openMultiShare(prefill) {
    var ex = document.getElementById("msOverlay"); if (ex) ex.remove();
    var curId = (activeRoom && activeRoom.id) ? activeRoom.id : null;   // 지금 글을 쓰고 있는 '현재 방'
    var BUGID = window.__BUG_ROOM_ID__ || 0;   // '메신저 불편 신고' 채널 — 공유 대상에서 제외 (대표 지시 2026-06-04)
    // 내 메모장(self)은 포함, 1:1(direct)·신고 채널은 제외 (대표 지시 2026-06-04)
    var sendable = (Array.isArray(rooms) ? rooms : []).filter(function (r) { return r && r.type !== "direct" && r.id !== BUGID; });
    // 현재 방이 목록에 없으면(1:1 등) 맨 앞에 추가하고, 항상 맨 위로 정렬 (단 신고 채널은 제외)
    if (curId && curId !== BUGID && activeRoom && !sendable.some(function (r) { return r.id === curId; })) sendable.unshift(activeRoom);
    sendable.sort(function (a, b) { return (b.id === curId ? 1 : 0) - (a.id === curId ? 1 : 0); });
    var ov = document.createElement("div");
    ov.id = "msOverlay"; ov.className = "ms-overlay";
    ov.innerHTML =
      '<div class="ms-panel">'
      + '<div class="ms-head"><span>👥 여러 방에 공유</span><button type="button" class="ms-x" id="msX" aria-label="닫기">✕</button></div>'
      + '<textarea class="ms-text" id="msText" placeholder="보낼 내용을 입력하세요"></textarea>'
      + '<div class="ms-tabbar"><button type="button" class="ms-tab on" data-mstab="rooms">방 선택</button><button type="button" class="ms-tab" data-mstab="bundles">📦 공유 묶음</button></div>'
      + '<input type="text" class="ms-search" id="msSearch" placeholder="🔍 방 이름 검색">'
      + '<div class="ms-list" id="msRoomList"></div>'
      + '<div class="ms-list" id="msBundleList" hidden></div>'
      + '<div class="ms-savebar" id="msSaveBar"><input type="text" class="ms-bname" id="msBName" maxlength="40" placeholder="이 조합을 묶음으로 저장 (이름)"><button type="button" class="ms-bsave" id="msBSave">저장</button></div>'
      + '<div class="ms-foot"><span class="ms-count" id="msCount"></span><button type="button" class="ms-cancel" id="msCancel">취소</button><button type="button" class="ms-send" id="msSend" disabled>보내기</button></div>'
      + '</div>';
    document.body.appendChild(ov);
    ov.querySelector("#msText").value = prefill || "";
    var selected = new Set();
    if (curId && curId !== BUGID) selected.add(curId);   // 작성한 '현재 방'도 자동 포함 (신고 채널은 제외)
    var roomListEl = ov.querySelector("#msRoomList");
    var sendBtn = ov.querySelector("#msSend");
    var countEl = ov.querySelector("#msCount");
    function refresh() {
      var n = selected.size;
      sendBtn.disabled = !n;
      sendBtn.textContent = n ? (n + "개 방에 보내기") : "보내기";
      countEl.textContent = n ? (n + "개 선택") : "";
    }
    function renderRooms(q) {
      q = (q || "").toLowerCase();
      var items = sendable.filter(function (r) { return r.id === curId || !q || (r.name || "").toLowerCase().indexOf(q) >= 0; });
      roomListEl.innerHTML = items.length
        ? items.map(function (r) { var rnm = (r.type === "self") ? "📝 내 메모장" : (r.name || "(이름없음)"); return '<label class="ms-room"><input type="checkbox" data-rid="' + r.id + '"' + (selected.has(r.id) ? " checked" : "") + '><span>' + escapeHtml(rnm) + (r.id === curId ? ' <span class="ms-cur">현재 방</span>' : '') + '</span></label>'; }).join("")
        : '<div class="ms-empty">보낼 수 있는 방이 없습니다</div>';
      roomListEl.querySelectorAll("input[type=checkbox]").forEach(function (cb) {
        cb.onchange = function () {
          var id = parseInt(cb.dataset.rid, 10);
          if (cb.checked) selected.add(id); else selected.delete(id);
          refresh();
        };
      });
    }
    renderRooms(""); refresh();
    ov.querySelector("#msSearch").oninput = function (e) { renderRooms(e.target.value); };
    ov.querySelectorAll(".ms-tab").forEach(function (t) {
      t.onclick = async function () {
        ov.querySelectorAll(".ms-tab").forEach(function (x) { x.classList.remove("on"); });
        t.classList.add("on");
        var isRooms = t.dataset.mstab === "rooms";
        ov.querySelector("#msRoomList").hidden = !isRooms;
        ov.querySelector("#msSearch").hidden = !isRooms;
        ov.querySelector("#msSaveBar").hidden = !isRooms;
        var bl = ov.querySelector("#msBundleList");
        bl.hidden = isRooms;
        if (!isRooms) {
          bl.innerHTML = '<div class="ms-empty">불러오는 중…</div>';
          var bundles = [];
          try { bundles = await fetch(BASE + "/api/me/share_bundles").then(function (r) { return r.json(); }); } catch (e) {}
          bl.innerHTML = (Array.isArray(bundles) && bundles.length)
            ? bundles.map(function (b) { return '<div class="ms-bundle"><button type="button" class="ms-bpick" data-ids="' + (b.room_ids || []).join(",") + '">📦 ' + escapeHtml(b.name) + ' <small>(' + (b.room_ids || []).length + '곳)</small></button><button type="button" class="ms-bdel" data-bid="' + b.id + '" title="삭제">🗑</button></div>'; }).join("")
            : '<div class="ms-empty">저장된 묶음이 없습니다.<br>방을 고른 뒤 \'방 선택\' 탭에서 저장하세요.</div>';
          bl.querySelectorAll(".ms-bpick").forEach(function (btn) {
            btn.onclick = function () {
              selected.clear();
              if (curId && curId !== BUGID) selected.add(curId);   // 묶음을 불러와도 현재 방은 유지(신고 채널 제외)
              (btn.dataset.ids || "").split(",").filter(Boolean).forEach(function (x) { selected.add(parseInt(x, 10)); });
              ov.querySelector('.ms-tab[data-mstab="rooms"]').click();
              renderRooms(""); refresh();
            };
          });
          bl.querySelectorAll(".ms-bdel").forEach(function (btn) {
            btn.onclick = async function () {
              if (!confirm(window.KNK_t("confirm.deleteBundle", "이 묶음을 삭제할까요?"))) return;
              try { await fetch(BASE + "/api/me/share_bundles/" + btn.dataset.bid, { method: "DELETE" }); } catch (e) {}
              t.click();
            };
          });
        }
      };
    });
    ov.querySelector("#msBSave").onclick = async function () {
      var name = ov.querySelector("#msBName").value.trim();
      if (!name) { alert(window.KNK_t("alert.bundleNameRequired", "묶음 이름을 입력하세요")); return; }
      if (!selected.size) { alert(window.KNK_t("alert.pickAtLeastOneRoom", "방을 1개 이상 선택하세요")); return; }
      var res = {};
      try { res = await fetch(BASE + "/api/me/share_bundles", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: name, room_ids: Array.from(selected) }) }).then(function (r) { return r.json(); }); } catch (e) { res = { error: window.KNK_t("alert.saveFail", "저장 실패") }; }
      if (res.error) { alert(res.error); return; }
      ov.querySelector("#msBName").value = "";
      alert(window.KNK_t("alert.bundleSaved", "✅ 묶음 저장됨: ") + name);
    };
    var close = function () { ov.remove(); };
    ov.querySelector("#msX").onclick = close;
    ov.querySelector("#msCancel").onclick = close;
    ov.addEventListener("click", function (e) { if (e.target === ov) close(); });
    sendBtn.onclick = async function () {
      var content = ov.querySelector("#msText").value.trim();
      if (!content) { alert(window.KNK_t("alert.contentRequired", "내용을 입력하세요")); return; }
      if (!selected.size) { alert(window.KNK_t("alert.pickRoom", "방을 선택하세요")); return; }
      sendBtn.disabled = true; sendBtn.textContent = window.KNK_t("send.sending", "보내는 중…");
      var res = {};
      try { res = await fetch(BASE + "/api/messages/broadcast", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: content, to_room_ids: Array.from(selected), origin_room_id: curId }) }).then(function (r) { return r.json(); }); } catch (e) { res = { error: window.KNK_t("alert.sendFail", "전송 실패") }; }
      if (res.error) { alert(res.error); sendBtn.disabled = false; refresh(); return; }
      if (els.msgInput) { els.msgInput.value = ""; }   // 보냈으니 입력창 비움
      close();
      alert(window.KNK_t("alert.sharedToRooms", "👥 {n}개 방에 공유했습니다").replace("{n}", (res.count || selected.size)));
    };
  }
  els.fileInput.addEventListener("change", async () => {
    // ★ input.files 는 live FileList — input.value="" 직후 비워짐.
    //   uploadFiles 가 async 라 await 중에 두번째 파일을 잃지 않도록
    //   먼저 정적 배열로 복사한 뒤 input.value 를 초기화한다.
    const picked = Array.from(els.fileInput.files);
    els.fileInput.value = "";
    if (!picked.length) return;
    const choice = await chooseAttachMode(picked);
    if (choice.mode === "cancel") return;
    // 즉시 전송하지 않고 글틀 위 '첨부 대기'에 담음 → 보내기/Enter 로 전송 (대표 지시 2026-05-29)
    _stageFiles(picked, choice.mode === "album");
  });
  // 첨부 대기 바 — 항목 ✕ 빼기 / 전체 취소
  {
    const _pa = document.getElementById("pendingAttach");
    if (_pa) _pa.addEventListener("click", (e) => {
      if (e.target.closest(".pa-clear")) { _clearPendingFiles(); return; }
      const del = e.target.closest(".pa-del");
      if (del) {
        const idx = parseInt(del.getAttribute("data-idx"), 10);
        if (!isNaN(idx)) {
          _pendingFiles.splice(idx, 1);
          if (!_pendingFiles.length) _pendingAlbumMode = false;
          renderPendingAttach();
        }
      }
    });
  }

  if (els.exportBtn) {
    els.exportBtn.addEventListener("click", () => {
      if (!activeRoom) return;
      openRoomExportDialog(activeRoom.id, activeRoom.name);
    });
  }

  // 🤝 고객사 게스트 초대 (대표 지시 2026-05-28). 채널은 초대 불가 — 누르면 안내. (대표 지시 2026-05-29)
  if (els.guestInviteBtn) {
    els.guestInviteBtn.addEventListener("click", () => {
      if (!activeRoom) return;
      if (activeRoom.type === "channel") {
        alert(window.KNK_t ? window.KNK_t("guest.notInChannel")
                           : "채널에서는 고객사를 초대할 수 없습니다.\n그룹·프로젝트 방에서만 초대할 수 있어요.");
        return;
      }
      openGuestInviteDialog(activeRoom.id, activeRoom.name);
    });
  }

  function _renderQrCode(text, container) {
    if (!container) return;
    container.innerHTML = "";
    if (typeof qrcode !== "function") {
      container.textContent = "QR 라이브러리 로드 실패";
      return;
    }
    try {
      const qr = qrcode(0, "M");  // type 0 = auto, error correction Medium
      qr.addData(text);
      qr.make();
      const imgTag = qr.createImgTag(5, 8);  // cellSize 5, margin 8
      container.innerHTML = imgTag;
      const img = container.querySelector("img");
      if (img) {
        // 다이얼로그 높이를 넘지 않게 — 화면이 낮으면 QR 도 자동 축소(스크롤 방지). (대표 지시 2026-05-30)
        img.style.display = "block";
        img.style.width = "min(170px, 32vh)";
        img.style.maxWidth = "170px";
        img.style.height = "auto";
      }
    } catch (e) {
      container.textContent = "QR 생성 실패";
    }
  }

  // ── 👥 직원 초대 (설정 → 초대 탭) — 우리 직원에게 메신저 접속 링크 공유. 새 계정 생성 없음(직원은 사번 계정 보유).
  //   QR + 링크 복사 + 카톡용 메시지 복사. 게스트는 섹션 자체가 없음(서버 {% if not me_is_guest %}). (대표 지시 2026-06-01)
  let _empInviteWired = false;
  let _empInviteLang = null;   // 초대용 선택 언어(대시보드 UI 언어와 별개). null=현재 UI 언어 따름.
  function _empInviteCurLang() {
    if (_empInviteLang) return _empInviteLang;
    try { if (window.KNK_curLang) return window.KNK_curLang(); } catch (_) {}
    return (window.KNK_LANG || "ko");
  }
  // /login?staff=1 — 게스트 쿠키(knk_gt) 있는 기기도 '직원 사번 로그인' 강제(고객사 페이지로 안 튕김).
  //   &lang=<선택> — QR 로 들어온 로그인창이 그 언어로 열림. (대표 지시 2026-06-01)
  function _empInviteUrl(lang) {
    const l = lang || _empInviteCurLang();
    return location.origin + BASE + "/login?staff=1&lang=" + encodeURIComponent(l);
  }
  function _empInviteMsg(lang) {
    const l = lang || _empInviteCurLang();
    const url = _empInviteUrl(l);
    const M = {
      ko: "[KNK 이음 초대]\n안녕하세요 👋 KNK 이음입니다.\n아래 링크로 접속해 본인 사번으로 로그인하세요.\n\n🔗 " + url + "\n\n· 로그인 ID: 본인 사번\n· 첫 비밀번호: 본사=휴대폰번호 / 베트남=9999 (첫 로그인 시 변경)\n· 휴대폰은 브라우저 메뉴 → '홈 화면에 추가' 하면 앱처럼 사용",
      vi: "[Lời mời KNK Eum nội bộ]\nXin chào 👋 Đây là messenger nội bộ của KNK.\nVui lòng mở liên kết bên dưới và đăng nhập bằng mã nhân viên của bạn.\n\n🔗 " + url + "\n\n· ID đăng nhập: Mã nhân viên của bạn\n· Mật khẩu đầu tiên: 9999 (đổi khi đăng nhập lần đầu)\n· Trên điện thoại: menu trình duyệt → 'Thêm vào màn hình chính' để dùng như ứng dụng",
      en: "[KNK Eum invitation]\nHello 👋 This is KNK's internal messenger.\nOpen the link below and log in with your employee number.\n\n🔗 " + url + "\n\n· Login ID: your employee number\n· First password: HQ = your phone number / Vietnam = 9999 (change on first login)\n· On mobile: browser menu → 'Add to Home Screen' to use it like an app",
      zh: "[KNK Eum 邀请]\n您好 👋 这是 KNK Eum。\n请打开下面的链接，用本人工号登录。\n\n🔗 " + url + "\n\n· 登录 ID：本人工号\n· 初始密码：总部=手机号码 / 越南=9999（首次登录时修改）\n· 手机：浏览器菜单 →「添加到主屏幕」即可像 App 一样使用",
    };
    return M[l] || M.ko;
  }
  function _syncEmpInviteSection() {
    const qrBox = document.getElementById("empInviteQr");
    if (!qrBox) return;   // 게스트 등 섹션 없음
    const lang = _empInviteCurLang();
    const urlBox = document.getElementById("empInviteUrl");
    if (urlBox) urlBox.textContent = _empInviteUrl(lang);
    _renderQrCode(_empInviteUrl(lang), qrBox);
    // 언어 버튼 active 표시
    document.querySelectorAll("#empInviteLangs .ei-lang").forEach(function (b) {
      b.dataset.active = (b.dataset.eilang === lang) ? "1" : "0";
    });
    if (_empInviteWired) return;
    _empInviteWired = true;
    const _copy = async (text, btn) => {
      try {
        await navigator.clipboard.writeText(text);
      } catch (_) {
        const ta = document.createElement("textarea");
        ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
        document.body.appendChild(ta); ta.focus(); ta.select();
        try { document.execCommand("copy"); } catch (e) {}
        ta.remove();
      }
      if (btn) {
        const o = btn.textContent;
        btn.textContent = "✅ " + (window.KNK_t ? window.KNK_t("common.copied", "복사됨!") : "복사됨!");
        setTimeout(() => { btn.textContent = o; }, 1500);
      }
    };
    // 언어 선택 버튼 — 초대용 언어만 바꿈(대시보드 UI 언어 불변)
    document.querySelectorAll("#empInviteLangs .ei-lang").forEach(function (b) {
      b.addEventListener("click", function () {
        _empInviteLang = b.dataset.eilang;
        _syncEmpInviteSection();   // QR·링크·active 재렌더 (가드로 재와이어는 안 됨)
      });
    });
    const msgBtn = document.getElementById("empInviteCopyMsg");
    const linkBtn = document.getElementById("empInviteCopyLink");
    if (msgBtn) msgBtn.addEventListener("click", () => _copy(_empInviteMsg(), msgBtn));
    if (linkBtn) linkBtn.addEventListener("click", () => _copy(_empInviteUrl(), linkBtn));
  }

  // 책갈피 탭 전환 — 'invite'(게스트 입력) / 'list'(활성 목록). 발행 버튼은 입력 탭에서만. (대표 지시 2026-05-30)
  function _switchGuestTab(tab) {
    const isList = (tab === "list");
    const pInv = document.getElementById("guestPaneInvite");
    const pList = document.getElementById("guestPaneList");
    const createBtn = document.getElementById("guestInviteCreateBtn");
    if (pInv) pInv.hidden = isList;
    if (pList) pList.hidden = !isList;
    document.querySelectorAll("#guestInviteDialog .gi-tab").forEach(b => {
      b.classList.toggle("active", b.dataset.giTab === tab);
    });
    if (createBtn) createBtn.style.display = isList ? "none" : "";
  }
  document.querySelectorAll("#guestInviteDialog .gi-tab").forEach(btn => {
    btn.addEventListener("click", () => _switchGuestTab(btn.dataset.giTab));
  });

  async function openGuestInviteDialog(roomId, roomName) {
    const dlg = els.guestInviteDialog;
    if (!dlg) return;
    if (els.guestInviteRoomName) els.guestInviteRoomName.textContent = `📍 ${roomName || ""}`;
    // 폼 초기화 + 결과 숨김
    const form = document.getElementById("guestInviteForm");
    const result = document.getElementById("guestInviteResult");
    if (form) form.style.display = "grid";
    if (result) result.hidden = true;
    document.getElementById("guestName").value = "";
    document.getElementById("guestCompany").value = "";
    const _gT = document.getElementById("guestTitle"); if (_gT) _gT.value = "";
    const _gD = document.getElementById("guestDept"); if (_gD) _gD.value = "";
    const _gDu = document.getElementById("guestDuty"); if (_gDu) _gDu.value = "";
    const _gE = document.getElementById("guestEmail"); if (_gE) _gE.value = "";
    const _gN = document.getElementById("guestNote"); if (_gN) _gN.value = "";
    document.getElementById("guestPhone").value = "";
    document.getElementById("guestExpires").value = "7";
    const _gL = document.getElementById("guestLang"); if (_gL) _gL.value = "ko";
    // 브라우저 자동완성(이전 입력값 저장) 차단 재무장 — 다시 열 때 readonly 복원 (대표 지시 2026-05-30)
    ["guestName","guestCompany","guestDept","guestTitle","guestDuty","guestEmail","guestPhone","guestNote"].forEach(_id => {
      const _el = document.getElementById(_id);
      if (_el) _el.setAttribute("readonly", "");
    });
    // 초대 권한 판정 — 채널·메모방 또는 권한 없으면 발행 비활성 + 사유 표시 (대표 지시 2026-05-30)
    //   서버 _can_invite_guest 와 동일 규칙: 1:1=멤버 누구나 / 그룹·프로젝트=방장·PM·관리자 / 채널·메모=불가
    const _room = activeRoom || {};
    const _rt = _room.type;
    let _canInvite = true, _why = "";
    if (window._meIsGuest) { _canInvite = false; _why = "외부 사용자는 고객사를 초대할 수 없습니다."; }
    else if (_rt === "self") { _canInvite = false; _why = "메모방에는 초대할 수 없습니다."; }
    else if (_rt === "direct") { _canInvite = false; _why = "1:1 방에는 고객사를 초대할 수 없습니다. 그룹·프로젝트 방을 만들어 초대하세요. (1:1은 사적 대화라 외부인이 과거 대화를 모두 보게 되는 문제 방지)"; }
    else if (_rt === "channel") { _canInvite = false; _why = "채널(전사·본사·베트남)에는 고객사를 초대할 수 없습니다. 그룹·프로젝트 방에서 초대하세요."; }
    else { // group / item
      _canInvite = (window._meRole === "ceo" || _room.my_role === "host" || _room.my_role === "sub_host");
      if (!_canInvite) _why = "이 방의 방장·PM·관리자만 고객사를 초대할 수 있습니다.";
    }
    const _noPermEl = document.getElementById("guestInviteNoPerm");
    const _createBtn = document.getElementById("guestInviteCreateBtn");
    if (_noPermEl) { _noPermEl.hidden = _canInvite; _noPermEl.textContent = _canInvite ? "" : ("🚫 " + _why); }
    if (form) form.style.display = _canInvite ? "grid" : "none";
    if (_createBtn) {
      _createBtn.disabled = !_canInvite;
      _createBtn.style.opacity = _canInvite ? "" : "0.45";
      _createBtn.style.cursor = _canInvite ? "" : "not-allowed";
    }
    _switchGuestTab("invite");   // 열 때 항상 입력 탭부터
    try { dlg.showModal(); } catch (_) { dlg.classList.add("open"); }
    // 활성 초대 목록 로드 — 권한 있는 방에서만(없으면 목록 endpoint 가 403 이라 '로드 실패' 표시 방지)
    if (_canInvite) {
      _refreshGuestInviteList(roomId);
    } else {
      const _wrap = document.getElementById("guestInviteList");
      if (_wrap) _wrap.innerHTML = "";
    }
  }

  async function _refreshGuestInviteList(roomId) {
    const wrap = document.getElementById("guestInviteList");
    if (!wrap) return;
    wrap.innerHTML = `<div class="dialog-hint" style="font-size:calc(12px + var(--fs-add-ui));color:var(--text-soft);text-align:center;padding:10px;">불러오는 중...</div>`;
    try {
      const data = await fetch(`${BASE}/api/rooms/${roomId}/guest_invites`).then(r => r.json());
      const items = (data && data.items) || [];
      const _cntEl = document.getElementById("giListCount");
      if (_cntEl) _cntEl.textContent = items.length ? `(${items.length})` : "";
      if (!items.length) {
        wrap.innerHTML = `<div class="dialog-hint" style="font-size:calc(12px + var(--fs-add-ui));color:var(--text-soft);text-align:center;padding:10px;">활성 초대 없음</div>`;
        return;
      }
      // 상세 한 줄 (값 있을 때만)
      const _giRow = (label, val) => val
        ? `<div style="display:flex;gap:6px;padding:2px 0;"><span style="color:var(--text-soft);min-width:62px;flex-shrink:0;">${label}</span><span style="color:var(--text);word-break:break-all;white-space:pre-wrap;">${escapeHtml(String(val))}</span></div>`
        : "";
      const _giById = {};
      items.forEach(x => { _giById[x.id] = x; });
      wrap.innerHTML = items.map(it => {
        const exp = it.expires_at ? (it.expired ? "만료됨" : `만료 ${it.expires_at.slice(0, 10)}`) : "무제한";
        const used = it.first_used_at ? "사용중 ✓" : "미사용";
        const titleChip = it.guest_title ? ` <span style="color:var(--text-soft);font-weight:400;">${escapeHtml(it.guest_title)}</span>` : "";
        const detail = [
          _giRow("회사명", it.guest_company),
          _giRow("부서명", it.guest_department),
          _giRow("직책", it.guest_title),
          _giRow("담당업무", it.guest_duty),
          _giRow("이메일", it.guest_email),
          _giRow("전화번호", it.guest_phone),
          _giRow("참고사항", it.guest_note),
          _giRow("만료", exp),
          _giRow("상태", used),
          _giRow("초대자", it.invited_by_name),
        ].join("");
        return `<div style="border-bottom:1px solid var(--border);font-size:calc(12px + var(--fs-add-ui));">
          <div style="display:flex;gap:8px;align-items:center;padding:8px;">
            <button type="button" data-gi-toggle="${it.id}" style="flex:1;min-width:0;text-align:left;background:none;border:none;cursor:pointer;padding:0;font-family:inherit;">
              <div style="font-weight:600;color:var(--text);"><span data-gi-arrow="${it.id}" style="display:inline-block;width:12px;color:var(--text-soft);">▸</span>${escapeHtml(it.guest_name)}${titleChip} <span style="color:var(--text-soft);font-weight:400;">· ${escapeHtml(it.guest_company)}</span></div>
              <div style="color:var(--text-soft);font-size:calc(11px + var(--fs-add-ui));padding-left:12px;">${escapeHtml(it.guest_phone)} · ${escapeHtml(exp)} · ${used}</div>
            </button>
            ${it.expired ? "" : `<button type="button" class="secondary-btn" data-gi-qr="${it.id}" style="padding:4px 8px;font-size:calc(11px + var(--fs-add-ui));flex-shrink:0;" title="기존 QR 다시 보기 (분실 시 재전달)">📱 QR</button>`}
            <button type="button" class="secondary-btn" data-revoke-invite="${it.id}" data-gi-name="${escapeHtml(it.guest_name)}" style="padding:4px 10px;font-size:calc(11px + var(--fs-add-ui));border-color:var(--accent);color:var(--accent);flex-shrink:0;">🗑 회수</button>
          </div>
          <div data-gi-detail="${it.id}" hidden style="padding:6px 10px 10px 20px;background:var(--surface);border-radius:6px;margin:0 8px 8px;">${detail}</div>
        </div>`;
      }).join("");
      // 이름 클릭 → 상세 펼침/접힘
      wrap.querySelectorAll("[data-gi-toggle]").forEach(btn => {
        btn.addEventListener("click", () => {
          const id = btn.dataset.giToggle;
          const det = wrap.querySelector(`[data-gi-detail="${id}"]`);
          const arr = wrap.querySelector(`[data-gi-arrow="${id}"]`);
          if (!det) return;
          const willOpen = det.hasAttribute("hidden");
          if (willOpen) det.removeAttribute("hidden"); else det.setAttribute("hidden", "");
          if (arr) arr.textContent = willOpen ? "▾" : "▸";
        });
      });
      // 📱 QR 다시보기 (만료 전만 버튼 노출) — 분실 시 기존 QR/링크 재전달
      wrap.querySelectorAll("[data-gi-qr]").forEach(btn => {
        btn.addEventListener("click", () => {
          const it = _giById[btn.dataset.giQr];
          if (it) _showGuestInviteQr(it);
        });
      });
      wrap.querySelectorAll("[data-revoke-invite]").forEach(btn => {
        btn.addEventListener("click", async () => {
          const gname = btn.dataset.giName || window.KNK_t("guest.thisCustomer","이 고객");
          if (!confirm(window.KNK_t("confirm.kickGuestRevoke","{name} 님을 방에서 내보내고 초대를 회수할까요?\n· 방 멤버에서 즉시 제거됩니다\n· 같은 QR/링크로 다시 들어올 수 없습니다\n· 방에 \"나갔습니다\" 안내가 표시됩니다").replace("{name}", gname))) return;
          const iid = btn.dataset.revokeInvite;
          try {
            const r = await fetch(`${BASE}/api/guest_invites/${iid}`, { method: "DELETE" }).then(x => x.json());
            if (r && r.ok) {
              _refreshGuestInviteList(roomId);
            } else {
              alert((r && r.error) || window.KNK_t("alert.revokeFail","회수 실패"));
            }
          } catch (e) { alert(window.KNK_t("alert.revokeFail","회수 실패")); }
        });
      });
    } catch (e) {
      wrap.innerHTML = `<div class="dialog-hint" style="font-size:calc(12px + var(--fs-add-ui));color:var(--accent);text-align:center;padding:10px;">로드 실패: ${escapeHtml(String(e))}</div>`;
    }
  }

  // 📱 기존 QR 다시 표시 (분실 시 재전달) — 발행결과 패널 재사용. 만료 전 항목만 호출됨.
  function _showGuestInviteQr(it) {
    // 결과(QR) 영역은 '초대' 탭 안에 있다. 목록 탭에서 눌렀으면 초대 탭으로 전환해야 보인다.
    //   (이게 빠져서 목록에서 QR 눌러도 숨겨진 초대 탭에 그려져 아무것도 안 보였음. 대표 지시 2026-05-30)
    _switchGuestTab("invite");
    const form = document.getElementById("guestInviteForm");
    const result = document.getElementById("guestInviteResult");
    const titleEl = document.getElementById("guestResultTitle");
    if (form) form.style.display = "none";
    if (result) result.hidden = false;
    if (titleEl) titleEl.textContent = "📱 기존 QR — 분실 시 고객에게 다시 전달하세요";
    _renderQrCode(it.url, document.getElementById("guestQrBox"));
    const parts = [it.guest_name];
    if (it.guest_title) parts.push(it.guest_title);
    parts.push(it.guest_company);
    parts.push(it.guest_phone);
    document.getElementById("guestResultPerson").textContent = parts.join(" · ");
    document.getElementById("guestResultExpiry").textContent =
      it.expires_at ? `📅 만료 ${it.expires_at.slice(0, 10)}` : "📅 무제한";
    document.getElementById("guestResultUrl").value = it.url;
    window._guestInviteMsg = _buildGuestKakaoMsg(it.guest_name, it.guest_company, it.url, it.guest_lang || "ko");
    try { result.scrollIntoView({ block: "nearest" }); } catch (_) {}
  }

  // 💬 혜택 중심 카톡 초대메시지 — 고객에게 복사·전달용. (대표 지시 2026-05-31)
  function _buildGuestKakaoMsg(name, company, url, lang) {
    // 고객사 언어(ko/vi/en/zh)로 카톡 초대 메시지 생성 (대표 지시 2026-05-31)
    const room = (activeRoom && activeRoom.name) ? activeRoom.name : "";
    const _app = document.getElementById("app");
    const inviter = (_app && _app.dataset.meName) ? _app.dataset.meName : "KNK";
    const who = `${company ? company + " " : ""}${name || ""}`.trim();
    lang = (["ko", "vi", "en", "zh"].indexOf(lang) >= 0) ? lang : "ko";
    const T = {
      ko: {
        head: `[KNK 이음 초대] ${who}님`,
        hi: `안녕하세요, KNK ${inviter}입니다.`,
        body: room ? `'${room}' 관련 소통을 위해 메신저로 초대드립니다.` : "업무 소통을 위해 메신저로 초대드립니다.",
        b1: "✅ 설치·가입 없이 바로 입장",
        b2: "🌐 실시간 자동 번역 · 📎 파일 공유 · 💬 대화 기록",
        enter: `▶ 입장하기: ${url}`,
        verify: "(초대 시 등록하신 휴대폰 번호로 본인 확인)",
      },
      vi: {
        head: `[Lời mời KNK Eum] ${who}`,
        hi: `Xin chào, tôi là ${inviter} từ KNK.`,
        body: room ? `Mời quý khách vào messenger để trao đổi về '${room}'.` : "Mời quý khách vào messenger để trao đổi công việc.",
        b1: "✅ Dùng ngay — không cần cài đặt / đăng ký",
        b2: "🌐 Dịch tự động · 📎 Chia sẻ tệp · 💬 Lưu hội thoại",
        enter: `▶ Vào phòng: ${url}`,
        verify: "(Xác minh bằng số điện thoại đã đăng ký khi mời)",
      },
      en: {
        head: `[KNK Eum Invitation] ${who}`,
        hi: `Hello, this is ${inviter} from KNK.`,
        body: room ? `You're invited to our messenger to discuss '${room}'.` : "You're invited to our messenger for business communication.",
        b1: "✅ Start instantly — no install or sign-up",
        b2: "🌐 Live auto-translation · 📎 File sharing · 💬 Chat history",
        enter: `▶ Enter: ${url}`,
        verify: "(Verified by the phone number registered at invitation)",
      },
      zh: {
        head: `[KNK Eum 邀请] ${who}`,
        hi: `您好，我是 KNK 的 ${inviter}。`,
        body: room ? `诚邀您加入通讯，就 '${room}' 相关事宜进行沟通。` : "诚邀您加入通讯进行业务沟通。",
        b1: "✅ 无需安装·注册，立即进入",
        b2: "🌐 实时自动翻译 · 📎 文件共享 · 💬 对话记录",
        enter: `▶ 进入：${url}`,
        verify: "（通过邀请时登记的手机号码进行本人确认）",
      },
    };
    const m = T[lang];
    return [m.head, "", m.hi, m.body, "", m.b1, m.b2, "", m.enter, m.verify].join("\n");
  }

  // ← 목록으로 (발행결과/QR다시보기 → 폼으로 복귀)
  const _guestBackBtn = document.getElementById("guestResultBackBtn");
  if (_guestBackBtn) {
    _guestBackBtn.addEventListener("click", () => {
      const form = document.getElementById("guestInviteForm");
      const result = document.getElementById("guestInviteResult");
      if (result) result.hidden = true;
      if (form) form.style.display = "grid";
      _switchGuestTab("list");   // 발행/QR 본 뒤 '활성 목록' 탭으로
    });
  }

  // 발행 버튼
  // 📷 고객사 로고 업로드(선택) — 클라이언트에서 최대 200px 로 축소 후 data URL 로 전송. (대표 지시 2026-05-31)
  window._guestLogoData = "";
  function _setGuestLogo(dataUrl) {
    window._guestLogoData = dataUrl || "";
    const pv = document.getElementById("guestLogoPreview");
    const clr = document.getElementById("guestLogoClearBtn");
    if (pv) pv.innerHTML = dataUrl ? `<img src="${dataUrl}" style="width:100%;height:100%;object-fit:contain;">` : window.KNK_t("guest.logoNone","로고<br>없음");
    if (clr) clr.style.display = dataUrl ? "" : "none";
  }
  function _readGuestLogoFile(file) {
    if (!file) return;
    if (file.size > 4 * 1024 * 1024) { alert(window.KNK_t("alert.logoTooBig","로고 파일이 너무 큽니다 (4MB 이하).")); return; }
    if (file.type === "image/svg+xml") {
      const r = new FileReader();
      r.onload = () => _setGuestLogo(r.result);
      r.readAsDataURL(file);
      return;
    }
    const r = new FileReader();
    r.onload = () => {
      const img = new Image();
      img.onload = () => {
        const max = 200;
        let w = img.width || max, h = img.height || max;
        if (w > max || h > max) { const s = max / Math.max(w, h); w = Math.round(w * s); h = Math.round(h * s); }
        try {
          const cv = document.createElement("canvas");
          cv.width = w; cv.height = h;
          cv.getContext("2d").drawImage(img, 0, 0, w, h);
          _setGuestLogo(cv.toDataURL("image/png"));
        } catch (e) { _setGuestLogo(r.result); }
      };
      img.onerror = () => _setGuestLogo(r.result);
      img.src = r.result;
    };
    r.readAsDataURL(file);
  }
  (function _wireGuestLogo() {
    const _lb = document.getElementById("guestLogoBtn");
    const _lf = document.getElementById("guestLogoFile");
    const _lc = document.getElementById("guestLogoClearBtn");
    if (_lb && _lf) _lb.addEventListener("click", () => _lf.click());
    if (_lf) _lf.addEventListener("change", () => { _readGuestLogoFile(_lf.files && _lf.files[0]); _lf.value = ""; });
    if (_lc) _lc.addEventListener("click", () => _setGuestLogo(""));
  })();

  const _guestCreateBtn = document.getElementById("guestInviteCreateBtn");
  if (_guestCreateBtn) {
    _guestCreateBtn.addEventListener("click", async () => {
      if (!activeRoom) return;
      const name = document.getElementById("guestName").value.trim();
      const company = document.getElementById("guestCompany").value.trim();
      const titleVal = (document.getElementById("guestTitle")?.value || "").trim();
      const department = (document.getElementById("guestDept")?.value || "").trim();
      const duty = (document.getElementById("guestDuty")?.value || "").trim();
      const email = (document.getElementById("guestEmail")?.value || "").trim();
      const note = (document.getElementById("guestNote")?.value || "").trim();
      const phone = document.getElementById("guestPhone").value.trim();
      const expires_days = parseInt(document.getElementById("guestExpires").value, 10);
      const lang = (document.getElementById("guestLang")?.value || "ko");   // 고객사 언어 (대표 지시 2026-05-31)
      if (!name || !company || !phone) {
        alert(window.KNK_t("alert.guestFieldsRequired","고객명·회사명·전화번호를 모두 입력하세요."));
        return;
      }
      try {
        const r = await fetch(`${BASE}/api/rooms/${activeRoom.id}/guest_invites`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, company, title: titleVal, department, duty, email, note, phone, expires_days, lang, logo: (window._guestLogoData || "") }),
        }).then(x => x.json());
        if (!(r && r.ok)) {
          alert((r && r.error) || "발행 실패");
          return;
        }
        // 결과 표시
        const form = document.getElementById("guestInviteForm");
        const result = document.getElementById("guestInviteResult");
        if (form) form.style.display = "none";
        if (result) result.hidden = false;
        const _titleEl = document.getElementById("guestResultTitle");
        if (_titleEl) _titleEl.textContent = r.reused
          ? "✅ 기존 초대 재사용 — 아래 QR/링크 전달"
          : "✅ 발행 완료 — 아래 QR/링크를 고객에게 전달";
        _renderQrCode(r.url, document.getElementById("guestQrBox"));
        const _personParts = [r.name];
        if (r.title) _personParts.push(r.title);
        _personParts.push(r.company);
        _personParts.push(r.phone);
        document.getElementById("guestResultPerson").textContent = _personParts.join(" · ");
        const expText = r.expires_at
          ? `📅 만료 ${r.expires_at.slice(0, 10)} (${r.expires_days}일)`
          : `📅 무제한`;
        document.getElementById("guestResultExpiry").textContent = expText;
        document.getElementById("guestResultUrl").value = r.url;
        window._guestInviteMsg = _buildGuestKakaoMsg(r.name, r.company, r.url, r.lang || lang);
        try { _setGuestLogo(""); } catch (e) {}   // 다음 발행 위해 로고 입력 초기화
        // 목록 갱신
        _refreshGuestInviteList(activeRoom.id);
      } catch (e) {
        alert(window.KNK_t("alert.issueFail","발행 실패"));
      }
    });
  }

  // URL 복사
  const _guestCopyBtn = document.getElementById("guestCopyUrlBtn");
  if (_guestCopyBtn) {
    _guestCopyBtn.addEventListener("click", async () => {
      const inp = document.getElementById("guestResultUrl");
      if (!inp || !inp.value) return;
      try {
        await navigator.clipboard.writeText(inp.value);
        _guestCopyBtn.textContent = "✓ 복사됨";
        setTimeout(() => { _guestCopyBtn.textContent = "📋 복사"; }, 1500);
      } catch (e) {
        inp.select();
        document.execCommand("copy");
        _guestCopyBtn.textContent = "✓ 복사됨";
        setTimeout(() => { _guestCopyBtn.textContent = "📋 복사"; }, 1500);
      }
    });
  }

  // 💬 카톡 초대메시지 복사 (혜택 중심 문구 + 링크). (대표 지시 2026-05-31)
  const _guestCopyMsgBtn = document.getElementById("guestCopyMsgBtn");
  if (_guestCopyMsgBtn) {
    _guestCopyMsgBtn.addEventListener("click", async () => {
      const msg = window._guestInviteMsg || "";
      if (!msg) return;
      const _done = () => {
        _guestCopyMsgBtn.textContent = "✓ 복사됨 — 카톡에 붙여넣기";
        setTimeout(() => { _guestCopyMsgBtn.textContent = "💬 카톡 초대메시지 복사"; }, 2200);
      };
      try {
        await navigator.clipboard.writeText(msg);
        _done();
      } catch (e) {
        const ta = document.createElement("textarea");
        ta.value = msg; ta.style.cssText = "position:fixed;left:-9999px;top:0;";
        document.body.appendChild(ta); ta.focus(); ta.select();
        try { document.execCommand("copy"); } catch (_) {}
        document.body.removeChild(ta);
        _done();
      }
    });
  }

  // 대화방 엑셀 내보내기 — 기간 선택 다이얼로그 (대표 지시 2026-05-28)
  //   - 기본: 최근 2주
  //   - 빠른 선택 7개 + 직접 날짜 입력
  //   - 사용자가 직접 날짜를 만지면 빠른 선택 active 해제
  function openRoomExportDialog(roomId, roomName) {
    const tt = (k, fb) => (window.KNK_t ? window.KNK_t(k) : fb);
    // YYYY-MM-DD 헬퍼 (로컬 시간 기준)
    const fmtYMD = (d) => {
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, "0");
      const dd = String(d.getDate()).padStart(2, "0");
      return `${y}-${m}-${dd}`;
    };
    const today = new Date();
    const twoWeeksAgo = new Date(today.getTime() - 14 * 86400000);

    // 기존 다이얼로그 제거
    const existing = document.getElementById("roomExportDialog");
    if (existing) { try { existing.remove(); } catch (_) {} }
    const dlg = document.createElement("div");
    dlg.id = "roomExportDialog";
    dlg.className = "modal";
    dlg.setAttribute("data-modal", "");
    // 동적 모달 polyfill (스레드 관리 다이얼로그와 동일 패턴)
    dlg.close = () => {
      dlg.classList.remove("open");
      dlg.removeAttribute("open");
      try { dlg.remove(); } catch (_) {}
    };
    try {
      Object.defineProperty(dlg, "open", {
        configurable: true,
        get() { return dlg.classList.contains("open"); },
      });
    } catch (_) {}
    dlg.showModal = () => { dlg.classList.add("open"); };

    const ranges = [
      { key: "1w",  days: 7,    label: tt("export.range1w",  "1주일") },
      { key: "2w",  days: 14,   label: tt("export.range2w",  "2주") },
      { key: "1m",  days: 30,   label: tt("export.range1m",  "1개월") },
      { key: "3m",  days: 90,   label: tt("export.range3m",  "3개월") },
      { key: "6m",  days: 180,  label: tt("export.range6m",  "6개월") },
      { key: "1y",  days: 365,  label: tt("export.range1y",  "1년") },
      { key: "all", days: null, label: tt("export.rangeAll", "전체") },
    ];
    const titleLbl  = tt("export.title", "📥 대화내용 다운로드");
    const periodLbl = tt("export.period", "기간 선택");
    const customLbl = tt("export.custom", "또는 직접 날짜");
    const fromLbl   = tt("export.from", "시작일");
    const toLbl     = tt("export.to", "종료일");
    const dlBtnLbl  = tt("export.btnDownload", "다운로드");
    const cancelLbl = tt("btn.cancel", "취소");

    dlg.innerHTML = `
      <div class="modal-content" style="max-width:480px;">
        <button type="button" class="close-x modal-close-x" data-close>✕</button>
        <h3>${escapeHtml(titleLbl)}</h3>
        <div style="margin:6px 0 14px;font-size:calc(13px + var(--fs-add-ui));color:var(--text-soft);">📍 ${escapeHtml(roomName || "")}</div>

        <div style="font-size:calc(12.5px + var(--fs-add-ui));font-weight:600;color:var(--text);margin-bottom:6px;">${escapeHtml(periodLbl)}</div>
        <div class="export-range-grid" id="exportRangeGrid">
          ${ranges.map(r => `<button type="button" class="export-range-btn ${r.key === '2w' ? 'active' : ''}" data-range="${r.key}" data-days="${r.days === null ? '' : r.days}">${escapeHtml(r.label)}</button>`).join("")}
        </div>

        <div style="font-size:calc(12.5px + var(--fs-add-ui));font-weight:600;color:var(--text);margin:14px 0 6px;">${escapeHtml(customLbl)}</div>
        <div style="display:flex;gap:8px;align-items:center;font-size:calc(13px + var(--fs-add-ui));">
          <label style="display:flex;flex-direction:column;gap:4px;flex:1;">
            <span style="color:var(--text-soft);font-size:calc(11.5px + var(--fs-add-ui));">${escapeHtml(fromLbl)}</span>
            <input type="text" readonly class="knk-date" id="exportFromDate" value="${fmtYMD(twoWeeksAgo)}" max="${fmtYMD(today)}" placeholder="${tt("ph.dateSelect","날짜 선택")}" style="padding:8px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-family:inherit;cursor:pointer;">
          </label>
          <span style="color:var(--text-soft);font-size:calc(18px + var(--fs-add-ui));align-self:flex-end;padding-bottom:6px;">~</span>
          <label style="display:flex;flex-direction:column;gap:4px;flex:1;">
            <span style="color:var(--text-soft);font-size:calc(11.5px + var(--fs-add-ui));">${escapeHtml(toLbl)}</span>
            <input type="text" readonly class="knk-date" id="exportToDate" value="${fmtYMD(today)}" max="${fmtYMD(today)}" placeholder="${tt("ph.dateSelect","날짜 선택")}" style="padding:8px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-family:inherit;cursor:pointer;">
          </label>
        </div>

        <div style="display:flex;gap:8px;margin-top:18px;justify-content:flex-end;">
          <button type="button" data-close class="thr-mgr-btn thr-mgr-cancel" style="min-width:80px;">${escapeHtml(cancelLbl)}</button>
          <button type="button" id="exportConfirmBtn" class="thr-mgr-btn thr-mgr-extend" style="min-width:120px;">📥 ${escapeHtml(dlBtnLbl)}</button>
        </div>
      </div>`;
    document.body.appendChild(dlg);
    dlg.showModal();

    const $fromInput = dlg.querySelector("#exportFromDate");
    const $toInput   = dlg.querySelector("#exportToDate");
    const $grid      = dlg.querySelector("#exportRangeGrid");

    // 빠른 선택 클릭 → 시작·종료일 자동 채움
    $grid.querySelectorAll(".export-range-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        $grid.querySelectorAll(".export-range-btn").forEach(b => b.classList.toggle("active", b === btn));
        const days = btn.dataset.days;
        if (days === "") {
          // 전체 — 시작일 비우기, 종료일은 오늘
          $fromInput.value = "";
          $toInput.value = fmtYMD(today);
        } else {
          const d = new Date(today.getTime() - parseInt(days, 10) * 86400000);
          $fromInput.value = fmtYMD(d);
          $toInput.value = fmtYMD(today);
        }
      });
    });

    // 사용자가 직접 날짜 입력하면 빠른 선택 active 해제
    [$fromInput, $toInput].forEach(inp => {
      inp.addEventListener("input", () => {
        $grid.querySelectorAll(".export-range-btn").forEach(b => b.classList.remove("active"));
      });
    });

    // ✕ / 취소
    dlg.querySelectorAll("[data-close]").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.preventDefault(); e.stopPropagation();
        try { dlg.close(); } catch (_) { dlg.remove(); }
      });
    });

    // 다운로드
    dlg.querySelector("#exportConfirmBtn").addEventListener("click", () => {
      const fromVal = $fromInput.value.trim();
      const toVal = $toInput.value.trim();
      // URL 빌드
      const params = new URLSearchParams();
      if (fromVal) params.append("from", fromVal);
      if (toVal) params.append("to", toVal);
      const qs = params.toString();
      const url = `${BASE}/api/rooms/${encodeURIComponent(roomId)}/export.xlsx${qs ? "?" + qs : ""}`;
      const a = document.createElement("a");
      a.href = url; a.style.display = "none";
      document.body.appendChild(a);
      a.click();
      setTimeout(() => { try { a.remove(); } catch (_) {} }, 1000);
      try { dlg.close(); } catch (_) { dlg.remove(); }
    });
  }

  // 방 나가기 — 정리 옵션 다이얼로그 노출
  async function doLeaveRoom(withExport) {
    if (!activeRoom) return;
    const rid = activeRoom.id;
    if (withExport) {
      // Excel 다운로드 (브라우저가 알아서 받음)
      const a = document.createElement("a");
      a.href = `${BASE}/api/rooms/${rid}/export.xlsx`;
      a.click();
      // 다운로드 트리거 후 약간 대기
      await new Promise(r => setTimeout(r, 1200));
    }
    let res;
    try {
      const resp = await fetch(`${BASE}/api/rooms/${rid}/membership`, { method: "DELETE" });
      if (!resp.ok) {
        const txt = await resp.text();
        const isHtml = txt.trim().startsWith("<");
        // JSON 오류({"error":...})면 메시지만 깔끔히 표시 (예: 진행중 요청 있어 나가기 차단)
        let parsed = null;
        try { parsed = JSON.parse(txt); } catch (_) {}
        if (parsed && parsed.error) { alert(parsed.error); return; }
        alert(
          `나가기 실패 (HTTP ${resp.status})\n\n` +
          (isHtml
            ? "서버에 새 엔드포인트가 아직 없습니다.\n\n👉 검은 CMD 창에서 Ctrl+C 한 번 → 메신저START.bat 다시 더블클릭으로 서버 재시작해주세요."
            : txt.slice(0, 300))
        );
        return;
      }
      res = await resp.json();
    } catch (e) {
      alert(window.KNK_t("alert.leaveFail","나가기 실패") + ": " + e.message + "\n\n" + window.KNK_t("alert.serverRestartHint","서버 재시작이 필요할 수 있습니다."));
      return;
    }
    if (res.error) { alert(res.error); return; }
    els.leaveRoomDialog.close();
    // 사이드바로 복귀
    if (socket) socket.emit("leave", { room_id: rid });
    activeRoom = null;
    app.classList.remove("viewing-chat");
    els.chatTitle.textContent = "대화를 선택하세요";
    els.itemMeta.hidden = true; els.itemMeta.innerHTML = "";
    els.itemEditBtn.hidden = true; els.galleryBtn.hidden = true;
    els.requestsBtn.hidden = true; els.requestsBadge.hidden = true;
    if (els.exportBtn) els.exportBtn.hidden = true;
    if (els.leaveRoomBtn) els.leaveRoomBtn.hidden = true;
    if (els.starredBtn) els.starredBtn.hidden = true;
    if (els.headMoreBtn) els.headMoreBtn.hidden = true;
    if (els.headMoreMenu) els.headMoreMenu.hidden = true;
    if (els.composerLangbar) els.composerLangbar.hidden = true;
    const composer = $("composer");
    composer.classList.remove("tr-vi", "tr-en", "tr-ko");
    els.msgInput.disabled = true; els.sendBtn.disabled = true; els.attachBtn.disabled = true;
    els.messages.innerHTML = "";
    await refreshRooms();
  }

  if (els.leaveRoomBtn) {
    els.leaveRoomBtn.addEventListener("click", () => {
      if (!activeRoom) return;
      els.leaveMyName.textContent = (app.dataset.meName || "나");
      // 🗑 완전 삭제 옵션 — 소유자(대표 본인) + 1:1 방에서만 노출 (대표 지시 2026-06-05)
      if (els.leavePurgeBtn) {
        els.leavePurgeBtn.hidden = !(window._meIsOwner && activeRoom.type === "direct");
      }
      els.leaveRoomDialog.classList.add("open");
    });
  }
  if (els.leaveWithExportBtn) els.leaveWithExportBtn.addEventListener("click", () => doLeaveRoom(true));
  if (els.leaveJustBtn) els.leaveJustBtn.addEventListener("click", () => {
    if (!confirm(window.KNK_t("confirm.leaveJust"))) return;
    doLeaveRoom(false);
  });
  // 🗑 1:1 대화 완전 삭제 — 소유자(대표 본인) 전용. 메시지·첨부·방 영구삭제(양쪽 화면에서 사라짐). (대표 지시 2026-06-05)
  if (els.leavePurgeBtn) els.leavePurgeBtn.addEventListener("click", async () => {
    if (!activeRoom || activeRoom.type !== "direct" || !window._meIsOwner) return;
    const rid = activeRoom.id;
    const peerName = (els.chatTitle.textContent || "상대").trim();
    if (!confirm("⚠️ [" + peerName + "] 와의 1:1 대화를 완전히 삭제합니다.\n\n· 모든 메시지·첨부가 영구 삭제됩니다 (복구 불가)\n· 상대 화면에서도 이 대화가 사라집니다\n\n계속할까요?")) return;
    if (!confirm(window.KNK_t("confirm.deleteIrreversible","정말 삭제할까요? 이 작업은 되돌릴 수 없습니다."))) return;
    let res;
    try {
      const resp = await fetch(`${BASE}/api/rooms/${rid}/purge`, { method: "POST" });
      res = await resp.json().catch(() => ({}));
      if (!resp.ok || (res && res.error)) { alert((res && res.error) || ("삭제 실패 (HTTP " + resp.status + ")")); return; }
    } catch (e) { alert(window.KNK_t("alert.deleteFail","삭제 실패") + ": " + (e.message || e)); return; }
    // 화면 정리 → 사이드바 복귀 (doLeaveRoom 과 동일 흐름)
    try { els.leaveRoomDialog.close(); } catch (_) {}
    els.leaveRoomDialog.classList.remove("open");
    if (socket) socket.emit("leave", { room_id: rid });
    activeRoom = null;
    app.classList.remove("viewing-chat");
    els.chatTitle.textContent = "대화를 선택하세요";
    if (els.itemMeta) { els.itemMeta.hidden = true; els.itemMeta.innerHTML = ""; }
    els.msgInput.disabled = true; els.sendBtn.disabled = true; els.attachBtn.disabled = true;
    els.messages.innerHTML = "";
    if (els.leaveRoomBtn) els.leaveRoomBtn.hidden = true;
    if (els.headMoreMenu) els.headMoreMenu.hidden = true;
    await refreshRooms();
    alert(window.KNK_t("alert.convDeleted","✅ 대화를 완전히 삭제했습니다."));
  });
  els.galleryBtn.addEventListener("click", () => openGallery("image"));
  els.closeGallery.addEventListener("click", () => els.galleryDialog.close());
  els.galleryDialog.querySelectorAll(".gtab").forEach(t => {
    t.addEventListener("click", () => openGallery(t.dataset.gtab));
  });
  els.requestsBtn.addEventListener("click", () => openRequests());
  if (els.starredBtn) els.starredBtn.addEventListener("click", showStarredDialog);
  // 멘션함은 이제 필터 칩(@ 멘션)으로 인라인 패널에 표시되며,
  // '모두 읽음/모두 삭제'는 openMentions() 패널 헤더에서 처리됨. (대표 지시 2026-05-24)

  // 모바일 ⋮ 더보기 메뉴 — 클릭 시 토글, 항목 클릭 시 해당 기존 버튼 트리거
  if (els.headMoreBtn && els.headMoreMenu) {
    let backdrop = null;
    const openMenu = () => {
      // hidden 안 된 버튼만 메뉴에 표시
      els.headMoreMenu.querySelectorAll("button[data-act]").forEach(b => {
        // PC 헤더 버튼과 1:1 미러링 — 빠진 항목(스레드·AI·이력·초대) 있어서 휴대폰 메뉴에서 누락됐던 버그 수정 (대표 지시 2026-05-30)
        const map = { requests: "requestsBtn", starred: "starredBtn", gallery: "galleryBtn", export: "exportBtn", edit: "itemEditBtn", leave: "leaveRoomBtn", room_threads: "roomThreadsBtn", room_search: "roomSearchBtn", ai_summary: "aiSummaryBtn", project_history: "projectHistoryBtn", guest_invite: "guestInviteBtn" };
        if (b.dataset.act === 'notice') {
          // 📢 공지사항 — 방이 열려 있으면 노출
          const nb = document.getElementById('noticeHeadBtn');
          b.style.display = (nb && !nb.hidden) ? "flex" : "none";
          return;
        }
        if (b.dataset.act === 'settings') {
          // 방 설정 — 1:1 외 모든 방에서 노출
          const rsBtn = document.getElementById('roomSettingsBtn');
          b.style.display = (rsBtn && !rsBtn.hidden) ? "flex" : "none";
          return;
        }
        const targetId = map[b.dataset.act];
        const targetBtn = targetId ? els[targetId] : null;
        b.style.display = (targetBtn && !targetBtn.hidden) ? "flex" : "none";
      });
      // 요청 뱃지 동기화
      if (els.requestsBadge && els.hmmRequestsBadge) {
        els.hmmRequestsBadge.textContent = els.requestsBadge.textContent;
        els.hmmRequestsBadge.hidden = els.requestsBadge.hidden;
      }
      els.headMoreMenu.hidden = false;
      // 백드롭
      backdrop = document.createElement("div");
      backdrop.className = "head-more-backdrop";
      document.body.appendChild(backdrop);
      backdrop.addEventListener("click", closeMenu, { once: true });
    };
    const closeMenu = () => {
      els.headMoreMenu.hidden = true;
      if (backdrop) { backdrop.remove(); backdrop = null; }
    };
    els.headMoreBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      els.headMoreMenu.hidden ? openMenu() : closeMenu();
    });
    // 메뉴 항목 클릭 → 해당 헤더 버튼 click 위임
    els.headMoreMenu.addEventListener("click", (e) => {
      const b = e.target.closest("button[data-act]");
      if (!b) return;
      closeMenu();
      if (b.dataset.act === 'notice') {
        const nb = document.getElementById('noticeHeadBtn');
        if (nb) nb.click();
        return;
      }
      if (b.dataset.act === 'settings') {
        openRoomSettings();
        return;
      }
      const map = { requests: "requestsBtn", starred: "starredBtn", gallery: "galleryBtn", export: "exportBtn", edit: "itemEditBtn", leave: "leaveRoomBtn", ai_summary: "aiSummaryBtn", project_history: "projectHistoryBtn", room_threads: "roomThreadsBtn", room_search: "roomSearchBtn", guest_invite: "guestInviteBtn" };
      const targetBtn = els[map[b.dataset.act]];
      if (targetBtn && !targetBtn.hidden) targetBtn.click();
    });
  }

  // 자동번역 토글 칩
  if (els.composerLangbar) {
    els.composerLangbar.querySelectorAll(".cl-chip").forEach(c => {
      c.addEventListener("click", () => {
        if (!activeRoom) return;
        setRoomTranslateMode(activeRoom.id, c.dataset.lang || "");
        try { localStorage.setItem("knkmsg.tr.manual." + activeRoom.id, "1"); } catch (e) {}   // 직접 정함 → 법인 자동이 안 덮어씀 (대표 지시 2026-06-04)
        applyComposerLangUI();
      });
    });
  }

  // ===== 명시적 닫기 핸들러 (옛/새 HTML 모두 호환) =====
  // [data-close] 위임이 안 잡히는 옛 HTML에 대비해 ID 기반으로도 wire-up
  const wireClose = (btnId, modalRef) => {
    const btn = document.getElementById(btnId);
    if (btn && modalRef) btn.addEventListener("click", (e) => {
      e.preventDefault(); e.stopPropagation();
      try { modalRef.close(); } catch(_) {}
      // 폴리필 미적용 옛 dialog도 강제로 숨기기
      if (modalRef.classList) modalRef.classList.remove("open");
      modalRef.removeAttribute("open");
      modalRef.style.display = "none";
    });
  };
  wireClose("closeRequests", els.requestsDialog);
  wireClose("closeGallery", els.galleryDialog);
  wireClose("closeDigest", els.digestDialog);
  wireClose("closeLightbox", els.lightbox);
  // 라이트박스 close() 를 한 번만 감싸 history 정리 — X 버튼·배경탭·ESC·프로그램 닫기 모두 이 경로를 거침.
  //   미리보기 열 때 넣어둔 history 한 칸을, 수동으로 닫으면 history.back 으로 정리한다.
  //   popstate(뒤로가기)로 닫힌 경우는 이미 pop 됐으므로 _lbClosingFromPop=true 로 추가 back 을 막는다. (대표 지시 2026-06-01)
  if (els.lightbox && !els.lightbox._lbCloseWrapped) {
    els.lightbox._lbCloseWrapped = true;
    const _lbBaseClose = els.lightbox.close.bind(els.lightbox);
    els.lightbox.close = function() {
      _lbBaseClose();
      if (_lbStatePushed) {
        _lbStatePushed = false;
        if (!_lbClosingFromPop) {
          _lbIgnorePop = true;
          try { history.back(); } catch (e) { _lbIgnorePop = false; }
        }
      }
    };
  }
  // 라이트박스 좌우 화살표 + 저장 버튼
  document.getElementById("lbPrev")?.addEventListener("click", () => lbNav(-1));
  document.getElementById("lbNext")?.addEventListener("click", () => lbNav(1));
  document.getElementById("lbSaveOne")?.addEventListener("click", lbSaveCurrent);
  document.getElementById("lbSaveAll")?.addEventListener("click", lbSaveAlbum);
  // 키보드 ← → ESC (ESC 는 .modal 이 이미 처리)
  document.addEventListener("keydown", (e) => {
    if (!els.lightbox || !els.lightbox.classList.contains("open")) return;
    if (e.key === "ArrowLeft") { e.preventDefault(); lbNav(-1); }
    else if (e.key === "ArrowRight") { e.preventDefault(); lbNav(1); }
    else if (e.key === "s" && (e.ctrlKey || e.metaKey)) {
      // Ctrl/Cmd+S — 현재 사진 저장
      e.preventDefault();
      lbSaveCurrent();
    }
  });
  // 모바일 스와이프 (좌우 50px 이상) — 줌 상태(scale>1)에서는 비활성화 (대표 지시 2026-05-27, 줌 팬과 충돌 방지)
  (function() {
    const stage = els.lightbox?.querySelector(".lb-stage");
    if (!stage) return;
    let sx = 0, sy = 0, tracking = false;
    stage.addEventListener("touchstart", (e) => {
      if (e.touches.length !== 1) { tracking = false; return; }
      if (_lbZoom.scale > 1.001) { tracking = false; return; }   // 줌 중에는 nav 스와이프 X
      sx = e.touches[0].clientX; sy = e.touches[0].clientY;
      tracking = true;
    }, { passive: true });
    stage.addEventListener("touchend", (e) => {
      if (!tracking) return;
      tracking = false;
      if (_lbZoom.scale > 1.001) return;
      const t = (e.changedTouches && e.changedTouches[0]);
      if (!t) return;
      const dx = t.clientX - sx;
      const dy = t.clientY - sy;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) {
        if (dx > 0) lbNav(-1);   // 오른쪽 스와이프 → 이전
        else lbNav(1);             // 왼쪽 스와이프 → 다음
      }
    }, { passive: true });
  })();
  wireClose("cancelEdit", els.itemEditDialog);
  wireClose("cancelNewRoom", els.newRoomDialog);
  wireClose("cancelNewRequest", els.newRequestDialog);
  // 옛 HTML의 하단 닫기 버튼들 (있으면)
  wireClose("closeRequestsBottom", els.requestsDialog);
  wireClose("closeGalleryBottom", els.galleryDialog);
  wireClose("closeDigestBottom", els.digestDialog);

  // (2026-05-28 제거) 우클릭으로 모달 강제 닫기 핸들러
  //   - 정상 사용 중 우클릭만 해도 모달이 닫혀 버리고
  //   - style.display="none" 이 인라인으로 박혀 다음 showModal() 까지 망가뜨림
  //   - 닫기 수단은 ESC / ✕ / 백드롭 클릭 으로 충분
  els.requestsDialog.querySelectorAll(".gtab").forEach(t => {
    t.addEventListener("click", async () => {
      activeReqTab = t.dataset.rtab;
      els.requestsDialog.querySelectorAll(".gtab").forEach(x => x.classList.toggle("active", x === t));
      await renderRequests();
    });
  });
  els.newRequestBtn.addEventListener("click", () => openNewRequest());
  els.cancelNewRequest.addEventListener("click", () => els.newRequestDialog.close());
  els.newRequestForm.addEventListener("submit", saveNewRequest);

  els.globalSearch.addEventListener("input", debounce((e) => runSearch(e.target.value), 250));

  // 🔍 검색 필터 도움말 버튼 (ⓘ)
  const _searchHelpBtn = document.getElementById("searchHelpBtn");
  const _searchHelpDialog = document.getElementById("searchHelpDialog");
  if (_searchHelpBtn && _searchHelpDialog) {
    _searchHelpBtn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      try { _searchHelpDialog.showModal(); } catch (_) {}
    });
  }

  // ============================================================
  // 🧠 AI 요약 + ✨ 작성 도움
  // ============================================================
  let _aiSummaryActiveRoom = null;     // 어느 방을 요약 중인지
  let _aiSummaryActiveParams = null;   // 마지막 사용 파라미터 (재생성용)

  // 범위 버튼 선택 표시 — 클릭한 버튼만 active 로 두고 유지 (대표 지시 2026-05-31)
  function _setActiveRangeBtn(btn) {
    document.querySelectorAll(".ai-range-btn").forEach(b => {
      b.classList.toggle("active", b === btn);
      b.setAttribute("aria-pressed", b === btn ? "true" : "false");
    });
  }

  async function openAiSummary(roomId, roomName) {
    if (!roomId) return;
    _aiSummaryActiveRoom = roomId;
    _aiSummaryActiveParams = { limit: 80 };   // 기본 범위 (자동 생성 X)
    if (els.aiSummaryRoomName) els.aiSummaryRoomName.textContent = `📍 ${roomName || ""}`;
    if (els.aiSummaryMeta) els.aiSummaryMeta.textContent = "";
    _setActiveRangeBtn(document.querySelector('.ai-range-btn[data-limit="80"]'));
    try { els.aiSummaryDialog.showModal(); } catch (_) {}
    // 자동 AI 호출 X — 저장된 요약만 조회(무료). 없으면 '요약하기' 안내. (대표 지시 2026-06-01, 비용 절감)
    await _loadSavedSummary(_aiSummaryActiveParams);
  }

  // 저장본 조회(무료) — 같은 방 사용자끼리 공유, AI 호출 없음 (peek)
  async function _loadSavedSummary(params) {
    if (!_aiSummaryActiveRoom || !els.aiSummaryBody) return;
    _aiSummaryActiveParams = params;
    els.aiSummaryBody.textContent = "💾 저장된 요약 확인 중…";
    els.aiSummaryMeta.textContent = "";
    try {
      const res = await fetch(`${BASE}/api/rooms/${_aiSummaryActiveRoom}/summarize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...params, peek: true }),
      }).then(r => r.json());
      if (res.error) { els.aiSummaryBody.textContent = `❌ ${res.error}`; return; }
      if (!res.has_saved) {
        els.aiSummaryBody.textContent = "아직 이 범위의 저장된 요약이 없습니다.\n\n‘🧠 요약하기’를 누르면 AI가 새로 만들어 저장합니다.\n(만든 요약은 같은 방 사용자 모두가 볼 수 있어요.)";
        els.aiSummaryMeta.textContent = "";
        return;
      }
      els.aiSummaryBody.textContent = res.summary || "(빈 응답)";
      let meta = `💾 저장됨: ${(res.cached_at || "").slice(0, 16).replace("T", " ")}`;
      if (res.model) meta += ` · ${res.model}`;
      if (res.new_messages_since > 0) meta += ` · 그 뒤 새 메시지 ${res.new_messages_since}개 — ‘다시 생성’으로 최신화`;
      els.aiSummaryMeta.textContent = meta;
    } catch (e) {
      els.aiSummaryBody.textContent = `❌ 네트워크 오류: ${e.message || e}`;
    }
  }

  // 생성(AI 실행, 비용) — 권한 없으면 서버가 403 메시지 반환 → 그대로 표시
  async function _genAiSummary(force) {
    if (!_aiSummaryActiveRoom || !els.aiSummaryBody) return;
    const params = { ...(_aiSummaryActiveParams || { limit: 80 }), force: !!force };
    els.aiSummaryBody.textContent = "🧠 AI가 요약하는 중… (수 초 소요)";
    els.aiSummaryMeta.textContent = "";
    try {
      const res = await fetch(`${BASE}/api/rooms/${_aiSummaryActiveRoom}/summarize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      }).then(r => r.json());
      if (res.error) { els.aiSummaryBody.textContent = `❌ ${res.error}`; return; }
      els.aiSummaryBody.textContent = res.summary || "(빈 응답)";
      let meta = `대상 메시지: ${res.message_count}개`;
      if (res.cached) {
        meta += ` · 💾 이미 최신 (저장: ${(res.cached_at || "").slice(0, 16).replace("T", " ")})`;
      } else {
        if (res.model) meta += ` · 모델: ${res.model}`;
        if (res.cost_usd) meta += ` · 비용: $${res.cost_usd.toFixed(4)}`;
      }
      els.aiSummaryMeta.textContent = meta;
    } catch (e) {
      els.aiSummaryBody.textContent = `❌ 네트워크 오류: ${e.message || e}`;
    }
  }

  // 범위 선택 버튼 — 선택 시 저장본만 조회(무료). 생성은 '요약하기' 버튼으로.
  document.querySelectorAll(".ai-range-btn").forEach(b => {
    b.addEventListener("click", () => {
      _setActiveRangeBtn(b);
      const limit = b.dataset.limit ? parseInt(b.dataset.limit, 10) : null;
      const since = b.dataset.since;
      const params = {};
      if (limit) {
        params.limit = limit;
      } else if (since) {
        const now = new Date();
        let target;
        if (since === "today") target = now;
        else if (since === "yesterday") target = new Date(now.getTime() - 86400000);
        else if (since === "week") target = new Date(now.getTime() - 7 * 86400000);
        if (target) params.since = target.toISOString().slice(0, 10);
      }
      _loadSavedSummary(params);
    });
  });

  // 🧠 요약하기 — 생성(권한자만, 비용). 없으면/최신화 필요 시 누름.
  if (els.aiSummaryGenBtn) {
    els.aiSummaryGenBtn.addEventListener("click", () => _genAiSummary(false));
  }
  // 🔄 다시 생성 — 강제 재생성(권한자만, 비용)
  if (els.aiSummaryRegenBtn) {
    els.aiSummaryRegenBtn.addEventListener("click", () => _genAiSummary(true));
  }
  if (els.aiSummaryCopyBtn) {
    els.aiSummaryCopyBtn.addEventListener("click", async () => {
      const text = els.aiSummaryBody?.textContent || "";
      try { await navigator.clipboard.writeText(text); els.aiSummaryCopyBtn.textContent = "✓ 복사됨"; setTimeout(() => els.aiSummaryCopyBtn.textContent = "📋 복사", 1500); } catch (_) {}
    });
  }

  // 헤더 🧠 버튼
  if (els.aiSummaryBtn) {
    els.aiSummaryBtn.addEventListener("click", () => {
      if (activeRoom) openAiSummary(activeRoom.id, activeRoom.name);
    });
  }

  // 헤더 🧵 버튼 — 이 방의 스레드 (대표 지시 2026-05-27, 2026-05-28 탭 2개로 확장)
  if (els.roomThreadsBtn) {
    els.roomThreadsBtn.addEventListener("click", () => openRoomThreadsDialog());
  }

  // ─── 🔍 대화 검색 (카톡식: 현재 방 메시지에서 단어 찾기) — 대표 지시 2026-06-06 ───
  //   서버 호출 없음. 이미 화면에 올라온 메시지(귓속말은 서버가 이미 가림)만 검색 → 프라이버시 안전.
  //   검색 대상: 보낸사람 이름(.author) + 본문·파일이름(.bubble). 내 메시지는 이름 미표시라 내 이름 보강.
  (function bindChatSearch() {
    const bar = document.getElementById('chatSearchBar');
    const input = document.getElementById('chatSearchInput');
    const countEl = document.getElementById('chatSearchCount');
    const prevBtn = document.getElementById('chatSearchPrev');
    const nextBtn = document.getElementById('chatSearchNext');
    const closeBtn = document.getElementById('chatSearchClose');
    if (!bar || !input) return;
    let _hits = [];     // 일치 .msg (오래된→최신)
    let _idx = -1;
    const _meName = () => {
      const u = (Array.isArray(users) ? users.find(x => x.id === meId) : null);
      return u ? ((typeof _dispName === 'function' ? _dispName(u) : (u.display_name || '')) || '') : '';
    };
    const _clearMarks = () => {
      if (!els.messages) return;
      els.messages.querySelectorAll('.search-hit, .search-current').forEach(el => el.classList.remove('search-hit', 'search-current'));
    };
    const _hay = (li) => {
      let s = '';
      const au = li.querySelector('.author');
      if (au) s += ' ' + (au.textContent || '');
      else if (!li.classList.contains('system')) s += ' ' + _meName();
      const bub = li.querySelector('.bubble');
      if (bub) s += ' ' + (bub.textContent || '');
      return s.toLowerCase();
    };
    function _focus() {
      if (_idx < 0 || _idx >= _hits.length) return;
      els.messages.querySelectorAll('.search-current').forEach(el => el.classList.remove('search-current'));
      const t = _hits[_idx];
      t.classList.add('search-current');
      _userTouchedMessages = true;
      try { t.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (_) {}
      if (countEl) countEl.textContent = (_idx + 1) + ' / ' + _hits.length;
    }
    function _runSearch() {
      const q = (input.value || '').trim().toLowerCase();
      _clearMarks();
      _hits = []; _idx = -1;
      if (countEl) countEl.classList.remove('csb-none');
      if (!q) { if (countEl) countEl.textContent = ''; return; }
      const all = els.messages ? els.messages.querySelectorAll('.msg[data-msg-id]') : [];
      all.forEach(li => { if (_hay(li).indexOf(q) >= 0) { _hits.push(li); li.classList.add('search-hit'); } });
      if (!_hits.length) {
        if (countEl) { countEl.textContent = (window.KNK_t ? window.KNK_t('search.none') : '결과 없음'); countEl.classList.add('csb-none'); }
        return;
      }
      _idx = _hits.length - 1;   // 가장 최근(맨 아래) 일치부터
      _focus();
    }
    function _step(dir) {        // +1 다음(아래/최신), -1 이전(위/오래된)
      if (!_hits.length) return;
      _idx = (_idx + dir + _hits.length) % _hits.length;
      _focus();
    }
    function _open() { bar.hidden = false; try { input.focus(); } catch (_) {} if (input.value.trim()) _runSearch(); }
    function _close() { bar.hidden = true; input.value = ''; _clearMarks(); _hits = []; _idx = -1; if (countEl) { countEl.textContent = ''; countEl.classList.remove('csb-none'); } }
    let _deb = null;
    input.addEventListener('input', () => { clearTimeout(_deb); _deb = setTimeout(_runSearch, 150); });
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); _step(e.shiftKey ? -1 : +1); }
      else if (e.key === 'Escape') { e.preventDefault(); _close(); }
    });
    if (prevBtn) prevBtn.addEventListener('click', () => _step(-1));
    if (nextBtn) nextBtn.addEventListener('click', () => _step(+1));
    if (closeBtn) closeBtn.addEventListener('click', () => _close());
    if (els.roomSearchBtn) els.roomSearchBtn.addEventListener('click', () => { bar.hidden ? _open() : _close(); });
    window._closeChatSearch = _close;   // 방 전환·나가기 시 외부에서 닫기
  })();
  // 스레드함 모달 탭 클릭 (내 스레드 / 방 전체)
  (function bindRoomThreadsTabs() {
    const tabsBar = document.getElementById("roomThreadsTabs");
    if (!tabsBar) return;
    tabsBar.querySelectorAll("[data-thr-tab]").forEach(btn => {
      btn.addEventListener("click", () => {
        const t = btn.dataset.thrTab;
        if (!t || t === _activeThreadTab) return;
        openRoomThreadsDialog(t);
      });
    });
  })();

  // ─── ✨ 작성 도움 (재작성 톤 메뉴) ───
  function showRewriteMenu(anchorEl) {
    if (!els.aiRewriteMenu) return;
    const menu = els.aiRewriteMenu;
    // 위치
    const rect = anchorEl.getBoundingClientRect();
    menu.style.display = "block";
    menu.style.left = "0px"; menu.style.top = "0px";   // 측정용
    const mw = menu.offsetWidth, mh = menu.offsetHeight;
    let x = rect.left;
    let y = rect.top - mh - 8;
    if (y < 8) y = rect.bottom + 8;
    if (x + mw > window.innerWidth - 8) x = window.innerWidth - mw - 8;
    if (x < 8) x = 8;
    menu.style.left = x + "px"; menu.style.top = y + "px";
  }
  function hideRewriteMenu() {
    if (els.aiRewriteMenu) els.aiRewriteMenu.style.display = "none";
  }
  if (els.aiRewriteBtn) {
    els.aiRewriteBtn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const text = (els.msgInput?.value || "").trim();
      if (!text) {
        alert(window.KNK_t("alert.rewriteNeedText","✨ 작성 도움\n\n다듬을 텍스트를 먼저 입력하세요."));
        return;
      }
      showRewriteMenu(els.aiRewriteBtn);
    });
  }
  if (els.aiRewriteMenu) {
    els.aiRewriteMenu.querySelectorAll(".mcm-item").forEach(item => {
      item.addEventListener("click", async (e) => {
        e.stopPropagation();
        const tone = item.dataset.tone;
        hideRewriteMenu();
        const original = (els.msgInput?.value || "").trim();
        if (!original) return;
        // 시각 피드백
        const prevValue = original;
        els.msgInput.value = "✨ Claude 가 다듬는 중…";
        els.msgInput.disabled = true;
        try {
          const res = await fetch(`${BASE}/api/ai/rewrite`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: prevValue, tone }),
          }).then(r => r.json());
          if (res.error) {
            els.msgInput.value = prevValue;
            alert(`❌ ${res.error}`);
            return;
          }
          els.msgInput.value = res.text || prevValue;
          // textarea autogrow trigger
          els.msgInput.dispatchEvent(new Event("input", { bubbles: true }));
        } catch (err) {
          els.msgInput.value = prevValue;
          alert(window.KNK_t("alert.networkError"));
        } finally {
          els.msgInput.disabled = false;
          els.msgInput.focus();
        }
      });
    });
  }
  // 메뉴 바깥 클릭으로 닫기
  document.addEventListener("click", (e) => {
    if (els.aiRewriteMenu && els.aiRewriteMenu.style.display === "block") {
      if (!els.aiRewriteMenu.contains(e.target) && e.target !== els.aiRewriteBtn) {
        hideRewriteMenu();
      }
    }
  });

  // ============================================================
  // 😀 이모지 피커 — 자체 구현 (외부 라이브러리 0개, 라이센스 청정)
  //   · 7개 카테고리 + 최근 사용 + 키워드 검색
  //   · textarea cursor 위치에 삽입, 팝업 유지(연속 선택)
  // ============================================================
  const EMOJI_DATA = {
    "최근":     [],   // localStorage 에서 동적 로드
    "표정":     ["😀","😃","😄","😁","😆","😅","🤣","😂","🙂","🙃","😉","😊","😇","🥰","😍","🤩","😘","😗","😚","😙","😋","😛","😜","😝","🤪","🤨","🧐","🤓","😎","🥳","😏","😒","😞","😔","😟","😕","🙁","☹️","😣","😖","😫","😩","🥺","😢","😭","😤","😠","😡","🤬","🤯","😳","😱","😨","😰","😥","😓","🤗","🤔","🤭","🤫","🤥","😶","😐","😑","😬","🙄","😯","😦","😧","😮","😲","🥱","😴","🤤","😪","🥴","😵","🤐","🤢","🤮","🤧","😷","🤒","🤕","🤑","🤠","😈","👿","👻","💀","☠️","👽","👾","🤖","💩","🎃"],
    "손짓":     ["👍","👎","👏","🙌","🙏","🤝","💪","✋","🤚","🖐","🖖","👋","🤙","🤘","🤞","🤟","🤜","🤛","✊","👊","✌️","👌","🤌","🤏","👈","👉","👆","👇","☝️","🫡","🫶","👀","👁","👄","👅","💋","🧠","🦷","🦴","👂","👃","🦻","🦾","🦿"],
    "동물":     ["🐶","🐱","🐭","🐹","🐰","🦊","🐻","🐼","🐨","🐯","🦁","🐮","🐷","🐸","🐵","🙈","🙉","🙊","🐒","🐔","🐧","🐦","🐤","🦆","🦅","🦉","🐺","🐗","🐴","🦄","🐝","🐛","🦋","🐌","🐞","🐜","🪲","🐢","🐍","🦎","🐙","🦑","🦞","🦀","🐡","🐠","🐟","🐬","🐳","🐋","🦈","🐊","🐅","🐆","🦓","🦍","🐘","🦏","🦛","🐪","🐫","🦒","🦘","🐃","🐂","🐄","🐎","🐖","🐏","🐑","🦙","🐐","🦌","🐕","🐩","🦮","🐈","🐓","🦃","🦤","🦚","🦜","🦢","🕊","🐇","🦝","🦨","🦡","🦫","🦦","🦥","🐁","🐀","🐿","🦔"],
    "음식":     ["🍏","🍎","🍐","🍊","🍋","🍌","🍉","🍇","🍓","🫐","🍈","🍒","🍑","🥭","🍍","🥥","🥝","🍅","🍆","🥑","🥦","🥬","🥒","🌶","🫑","🌽","🥕","🫒","🧄","🧅","🥔","🍠","🥐","🥯","🍞","🥖","🥨","🧀","🥚","🍳","🥞","🧇","🥓","🥩","🍗","🍖","🌭","🍔","🍟","🍕","🥪","🥙","🧆","🌮","🌯","🥗","🍝","🍜","🍲","🍛","🍣","🍱","🥟","🍤","🍙","🍚","🍘","🍥","🥮","🍢","🍡","🍧","🍨","🍦","🥧","🧁","🍰","🎂","🍮","🍭","🍬","🍫","🍿","🍩","🍪","🌰","🥜","🍯","🥛","🍼","☕","🍵","🧃","🥤","🧋","🍶","🍺","🍻","🥂","🍷","🥃","🍸","🍹","🧉","🍾"],
    "활동":     ["⚽","🏀","🏈","⚾","🥎","🎾","🏐","🏉","🥏","🎱","🪀","🏓","🏸","🥅","🏒","🏑","🥍","🏏","🪃","🥊","🥋","🎯","⛳","⛸","🎿","🛷","🥌","🪁","🎮","🕹","🎲","🧩","♟","🎭","🎨","🎪","🎬","🎤","🎧","🎼","🎹","🥁","🎷","🎺","🎸","🪕","🎻","🎲","♠","♣","♥","♦","🃏","🎴","🀄","🎯","🎳"],
    "여행":     ["🚗","🚕","🚙","🚌","🚎","🏎","🚓","🚑","🚒","🚐","🛻","🚚","🚛","🚜","🛴","🚲","🛵","🏍","🛺","🚍","🚘","🚖","🚂","🚆","🚇","🚊","🚉","✈️","🛫","🛬","🛩","💺","🛰","🚀","🛸","🚁","🛶","⛵","🚤","🛥","🛳","⛴","🚢","⚓","⛽","🚧","🚦","🚥","🗺","🗿","🗽","🗼","🏰","🏯","🏟","🎡","🎢","🎠","⛲","⛱","🏖","🏝","🏜","🌋","⛰","🏔","🗻","🏕","⛺","🏠","🏡","🏢","🏬","🏥","🏦","🏨","🏪","🏫","💒","⛪","🛤","🛣","🗾","🎑","🌅","🌄","🌠","🎇","🎆","🌇","🌆","🏙","🌃","🌌","🌉","🌁"],
    "기호":     ["❤️","🧡","💛","💚","💙","💜","🖤","🤍","🤎","💔","❣️","💕","💞","💓","💗","💖","💘","💝","💟","✅","☑️","✔️","❌","⭕","🛑","⛔","🚫","💯","💢","♨️","❗","❕","❓","❔","‼️","⁉️","🔅","🔆","⚠️","🚸","☢️","☣️","🔱","⚜️","🔰","♻️","🆗","🆙","🆒","🆓","🔝","🔙","🔜","🔚","🆖","✨","⭐","🌟","💫","⚡","🔥","💥","☄","💢","💦","💧","🌊","🎵","🎶","♿","🅿️","🚹","🚺","🚻","➕","➖","➗","✖","💰","💵","💴","💶","💷","💳","💎","⌛","⏳","⏰","⏱","⏲","🕐","📅","📆","🗓","🔔","🔕","📣","📢","💬","💭","🗯","🔍","🔎","🔒","🔓","🔏","🔐","🗝","🔑","🛎"],
  };

  // 키워드 검색 + 자동완성 매핑 (한글) — 자주 쓰는 단어 위주
  const EMOJI_KEYWORDS = {
    // 표정·감정
    "웃음": ["😀","😃","😄","😁","😆","😅","🤣","😂","🙂"],
    "웃겨": ["😂","🤣","😆","😹"],
    "ㅋㅋ": ["😂","🤣","😆"],
    "하하": ["😄","😆","😂"],
    "슬픔": ["😢","😭","😔","☹️","🙁","😞","🥺"],
    "슬퍼": ["😢","😭","😔","🥺"],
    "눈물": ["😢","😭","🥲"],
    "우울": ["😔","😞","😟"],
    "화남": ["😠","😡","🤬","😤"],
    "화나": ["😠","😡","🤬","😤"],
    "짜증": ["😤","😠","😩","🙄"],
    "사랑": ["❤️","🧡","💛","💚","💙","💜","💕","💞","💓","💖","💝","🥰","😍","😘"],
    "하트": ["❤️","🧡","💛","💚","💙","💜","💖","💕","💝"],
    "뽀뽀": ["😘","💋"],
    "윙크": ["😉"],
    "부끄": ["😳","☺️","😊"],
    "놀람": ["😱","😮","😲","😯"],
    "충격": ["😱","😨","🤯"],
    "헐": ["😱","😮","😲"],
    "대박": ["😱","🔥","💯","👏"],
    "졸려": ["😴","🥱","😪"],
    "졸림": ["😴","🥱","😪"],
    "피곤": ["😩","😫","😮‍💨","🥱"],
    "잠": ["😴","💤"],
    "아파": ["🤒","🤕","😷"],
    "아픔": ["🤒","🤕","😷"],
    "더워": ["🥵","🔥","☀️"],
    "추워": ["🥶","❄️","🧊"],
    "천사": ["😇"],
    "악마": ["😈","👿"],
    // 손짓·반응
    "손": ["👍","👎","👏","🙌","🙏","✋","👋","✌️","👌","💪"],
    "엄지": ["👍","👎"],
    "따봉": ["👍"],
    "좋아": ["👍","😍","🔥","💯"],
    "좋다": ["👍","😊","🔥"],
    "굿": ["👍","👌","✨"],
    "최고": ["👍","🔥","💯","🏆"],
    "짱": ["👍","🔥","💯"],
    "박수": ["👏","🙌"],
    "감사": ["🙏","😊","🙇"],
    "고마워": ["🙏","😊"],
    "땡큐": ["🙏","😊"],
    "제발": ["🙏"],
    "기도": ["🙏"],
    "화이팅": ["💪","🔥","✊"],
    "파이팅": ["💪","🔥","✊"],
    "힘내": ["💪","🔥","✊","🙏"],
    "안녕": ["👋","🙇"],
    "하이": ["👋"],
    "잘가": ["👋"],
    "백점": ["💯"],
    "만점": ["💯","🏆"],
    // 기호·업무
    "체크": ["✅","☑️","✔️"],
    "확인": ["✅","☑️","✔️","👌"],
    "완료": ["✅","🎉","👌"],
    "끝": ["✅","🏁"],
    "오케이": ["👌","✅"],
    "엑스": ["❌","⛔","🚫","🛑"],
    "안돼": ["❌","🚫","🙅"],
    "주의": ["⚠️","❗","❕","‼️"],
    "경고": ["⚠️","🚨","❗"],
    "급함": ["🔥","⚡","‼️","⏰"],
    "물음표": ["❓","❔","⁉️"],
    "질문": ["❓","🙋"],
    "별": ["⭐","🌟","💫","✨"],
    "불": ["🔥"],
    "핫": ["🔥","🥵"],
    "물": ["💧","💦","🌊"],
    "꽃": ["🌸","🌺","🌻","🌹","🥀","🌷","💐"],
    "선물": ["🎁","🎀"],
    "축하": ["🎉","🎊","🥳","🎂","🍰"],
    "추카": ["🎉","🎊","🥳"],
    "생일": ["🎂","🥳","🎉","🎈"],
    "폭죽": ["🎆","🎇","🎉"],
    "트로피": ["🏆","🥇"],
    "우승": ["🏆","🥇","🎉"],
    "메달": ["🥇","🥈","🥉"],
    "이별": ["💔"],
    // 사물·업무도구
    "돈": ["💰","💵","💴","💶","💷","💳","💎"],
    "월급": ["💰","💵","🤑"],
    "회의": ["📅","🗓️","📝"],
    "미팅": ["📅","🤝","📝"],
    "전화": ["☎️","📞","📱"],
    "메일": ["📧","✉️","📨"],
    "이메일": ["📧","✉️","📨"],
    "시계": ["⏰","⏱️","⏲️","🕐","⌛","⏳"],
    "시간": ["⏰","⌛","⏳","🕐"],
    "알림": ["🔔","📢","📣"],
    "벨": ["🔔"],
    "검색": ["🔍","🔎"],
    "잠금": ["🔒","🔑","🔐"],
    "보안": ["🔒","🔐","🛡️"],
    "열쇠": ["🔑","🗝️"],
    "박스": ["📦"],
    "택배": ["📦","🚚"],
    "책": ["📚","📖","✏️"],
    "공부": ["📚","✏️","🤓"],
    "컴퓨터": ["💻","🖥️"],
    "노트북": ["💻"],
    "휴대폰": ["📱"],
    "사진": ["📷","📸","🖼️"],
    "카메라": ["📷","📸"],
    "생각": ["💭","🤔"],
    "대화": ["💬","🗨️"],
    "말": ["💬","🗯️"],
    // 음식·휴식
    "커피": ["☕","🥤"],
    "밥": ["🍚","🍱","🍙"],
    "식사": ["🍚","🍽️","🍱"],
    "맛집": ["😋","🍔","🍜"],
    "맛있": ["😋","🤤","👍"],
    "치킨": ["🍗","🍺"],
    "피자": ["🍕"],
    "햄버거": ["🍔"],
    "라면": ["🍜"],
    "케이크": ["🎂","🍰","🧁"],
    "맥주": ["🍺","🍻"],
    "소주": ["🍶","🥂"],
    "술": ["🍺","🍻","🍶","🍷","🥂"],
    "회식": ["🍻","🍶","🍗"],
    // 날씨·자연
    "비": ["🌧️","☔","💧"],
    "우산": ["☔","🌂"],
    "눈오": ["❄️","⛄","🌨️"],
    "눈사람": ["⛄"],
    "맑음": ["☀️","🌤️"],
    "해님": ["☀️"],
    "달": ["🌙","🌕"],
    "무지개": ["🌈"],
    "번개": ["⚡","🌩️"],
    "지구": ["🌏","🌍","🌎"],
    "세계": ["🌏","🌍","🌐"],
    "크리스마스": ["🎄","🎅","🎁"],
    "산타": ["🎅","🎄"],
    // 동물
    "고양이": ["🐱","😺","😸","😹","😻","😼","😽","🙀","😿","😾"],
    "강아지": ["🐶","🐕","🦮","🐩"],
    "개": ["🐶","🐕"],
    "토끼": ["🐰","🐇"],
    "곰": ["🐻","🐻‍❄️","🧸"],
    // 활동·취미
    "음악": ["🎵","🎶","🎼"],
    "노래": ["🎵","🎶","🎤"],
    "게임": ["🎮","🕹️"],
    "운동": ["💪","🏋️","🏃"],
    "헬스": ["💪","🏋️"],
    "축구": ["⚽"],
    "야구": ["⚾"],
    "농구": ["🏀"],
    "여행": ["✈️","🧳","🗺️"],
    "비행기": ["✈️"],
    "자동차": ["🚗","🚙"],
    "차": ["🚗","🚙"],
    "집": ["🏠","🏡"],
    "회사": ["🏢","🏬"],
    "건물": ["🏢","🏬","🏠"],
    // 기타 캐릭터
    "로봇": ["🤖"],
    "유령": ["👻"],
    "해골": ["💀","☠️"],
    "외계인": ["👽","👾"],
    "똥": ["💩"],
  };

  const RECENT_KEY = "knkmsg.emojiRecent";
  function loadRecentEmojis() {
    try {
      const s = localStorage.getItem(RECENT_KEY);
      if (!s) return [];
      const arr = JSON.parse(s);
      return Array.isArray(arr) ? arr.slice(0, 24) : [];
    } catch (e) { return []; }
  }
  function pushRecentEmoji(emoji) {
    try {
      const cur = loadRecentEmojis().filter(e => e !== emoji);
      cur.unshift(emoji);
      localStorage.setItem(RECENT_KEY, JSON.stringify(cur.slice(0, 24)));
    } catch (e) {}
  }

  let _epCategory = "표정";
  function renderEmojiTabs() {
    const tabs = document.getElementById("epTabs");
    if (!tabs) return;
    const cats = Object.keys(EMOJI_DATA);
    tabs.innerHTML = cats.map(c => {
      const icon = { "최근":"🕒", "표정":"😀", "손짓":"👍", "동물":"🐶", "음식":"🍔", "활동":"⚽", "여행":"✈️", "기호":"❤️" }[c] || c;
      const active = c === _epCategory ? " active" : "";
      return `<button type="button" class="ep-tab${active}" data-ep-cat="${c}" title="${c}">${icon}</button>`;
    }).join("");
    tabs.querySelectorAll(".ep-tab").forEach(b => {
      b.addEventListener("click", (e) => {
        // 탭 재렌더(innerHTML 교체)로 클릭된 버튼이 DOM에서 사라지면,
        // 이 클릭이 document 바깥클릭 핸들러까지 버블링되어 피커가 닫히는 문제 방지
        e.preventDefault();
        e.stopPropagation();
        _epCategory = b.dataset.epCat;
        const search = document.getElementById("epSearch");
        if (search) search.value = "";
        renderEmojiTabs();
        renderEmojiGrid();
      });
    });
  }
  function renderEmojiGrid(filter) {
    const grid = document.getElementById("epGrid");
    if (!grid) return;
    let list;
    if (filter && filter.trim()) {
      const q = filter.trim().toLowerCase();
      const set = new Set();
      // 키워드 매핑에서 찾기
      Object.entries(EMOJI_KEYWORDS).forEach(([kw, arr]) => {
        if (kw.includes(q) || q.includes(kw)) arr.forEach(e => set.add(e));
      });
      list = Array.from(set);
      if (list.length === 0) {
        grid.innerHTML = `<div class="ep-empty">"${escapeHtml(filter)}" 결과 없음. (예: 웃음, 손, 별, 체크, 사랑)</div>`;
        return;
      }
    } else if (_epCategory === "최근") {
      list = loadRecentEmojis();
      if (list.length === 0) {
        grid.innerHTML = `<div class="ep-empty">최근 사용한 이모지가 없습니다.<br>다른 탭에서 골라 사용하면 여기에 모입니다.</div>`;
        return;
      }
    } else {
      list = EMOJI_DATA[_epCategory] || [];
    }
    grid.innerHTML = list.map(e =>
      `<button type="button" class="ep-emoji" data-emoji="${e}">${e}</button>`
    ).join("");
    grid.querySelectorAll(".ep-emoji").forEach(b => {
      b.addEventListener("click", () => insertEmojiAtCursor(b.dataset.emoji));
    });
  }
  function insertEmojiAtCursor(emoji) {
    const ta = els.msgInput;
    if (!ta || ta.disabled) return;
    const start = ta.selectionStart || 0;
    const end = ta.selectionEnd || 0;
    const before = ta.value.substring(0, start);
    const after = ta.value.substring(end);
    ta.value = before + emoji + after;
    const caret = start + emoji.length;
    ta.focus();
    ta.setSelectionRange(caret, caret);
    // 입력 이벤트 트리거 — autoGrowMsgInput / send 버튼 활성화 등 반응
    ta.dispatchEvent(new Event("input", { bubbles: true }));
    pushRecentEmoji(emoji);
  }
  function toggleEmojiPicker(forceOpen) {
    const p = els.emojiPicker;
    if (!p) return;
    const willOpen = forceOpen !== undefined ? forceOpen : p.hidden;
    if (willOpen) {
      // 스티커 패널이 열려 있으면 닫기 (겹침 방지)
      if (els.stickerPicker && !els.stickerPicker.hidden) els.stickerPicker.hidden = true;
      // 최근 항목 새로 로드 + 첫 렌더
      EMOJI_DATA["최근"] = loadRecentEmojis();
      _epCategory = (EMOJI_DATA["최근"].length > 0) ? "최근" : "표정";
      const search = document.getElementById("epSearch");
      if (search) search.value = "";
      renderEmojiTabs();
      renderEmojiGrid();
      p.hidden = false;
    } else {
      p.hidden = true;
    }
  }
  if (els.emojiBtn) {
    els.emojiBtn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      toggleEmojiPicker();
    });
  }
  // 검색 입력
  const _epSearch = document.getElementById("epSearch");
  if (_epSearch) {
    _epSearch.addEventListener("input", () => {
      renderEmojiGrid(_epSearch.value);
    });
  }
  // 바깥 클릭으로 닫기 (단, 피커 안 / 버튼 클릭은 제외)
  document.addEventListener("click", (e) => {
    if (!els.emojiPicker || els.emojiPicker.hidden) return;
    if (els.emojiPicker.contains(e.target)) return;
    if (e.target === els.emojiBtn) return;
    toggleEmojiPicker(false);
  });
  // ESC 로 닫기
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && els.emojiPicker && !els.emojiPicker.hidden) {
      toggleEmojiPicker(false);
    }
  });

  // ============================================================
  // ✨ 이모지 자동완성 — 입력 중 단어가 키워드와 맞으면 추천 바 표시,
  //    클릭 시 그 단어를 이모지로 교체. 다음 글자/스페이스로 이어가면 자동으로 사라짐.
  // ============================================================
  const _emojiSuggestEl = document.getElementById("emojiSuggest");
  let _suggestApplying = false;
  // 단어 인식: 한글(완성/자모)·영문·숫자 연속. 커서 바로 앞 토큰만.
  const _WORD_RE = /([0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ]+)$/;

  function _currentWordBeforeCaret() {
    const ta = els.msgInput;
    if (!ta) return "";
    const pos = ta.selectionStart || 0;
    const before = ta.value.slice(0, pos);
    const m = before.match(_WORD_RE);
    return m ? m[1] : "";
  }

  function _matchEmojisForWord(word) {
    if (!word) return [];
    const seen = new Set();
    const out = [];
    const add = (arr) => { (arr || []).forEach(e => { if (!seen.has(e)) { seen.add(e); out.push(e); } }); };
    // 1) 정확히 일치 (예: "축하")
    if (EMOJI_KEYWORDS[word]) add(EMOJI_KEYWORDS[word]);
    // 2) 입력이 키워드의 앞부분 (예: "축" → "축하")
    Object.keys(EMOJI_KEYWORDS).forEach(kw => {
      if (kw !== word && kw.startsWith(word)) add(EMOJI_KEYWORDS[kw]);
    });
    // 3) 키워드가 입력 단어의 앞부분 (예: "축하해" → "축하"). 2자 이상 키워드만 — 잡음 방지.
    Object.keys(EMOJI_KEYWORDS).forEach(kw => {
      if (kw.length >= 2 && kw !== word && word.startsWith(kw)) add(EMOJI_KEYWORDS[kw]);
    });
    return out.slice(0, 8);
  }

  function hideEmojiSuggest() {
    if (_emojiSuggestEl && !_emojiSuggestEl.hidden) {
      _emojiSuggestEl.hidden = true;
      _emojiSuggestEl.innerHTML = "";
    }
  }

  // 입력 단어가 (1) 스티커 라벨에 포함되거나 (2) 동의어 키워드(STICKER_KEYWORDS)와 맞으면 추천. 2자 이상만.
  function _matchStickersForWord(word) {
    if (!word || word.length < 2) return [];
    if (!_stickersLoaded) { loadStickers(); return []; }
    const seen = new Set();
    const out = [];
    // 1) 라벨에 단어 포함 (예: "회의" → "회의 중입니다")
    for (const s of _stickerList) {
      if ((s.label || "").includes(word) && !seen.has(s.file)) { seen.add(s.file); out.push(s); }
    }
    // 2) 동의어 키워드 매칭 (예: "땡큐" → 감사합니다, "하이" → 안녕하세요)
    if (typeof STICKER_KEYWORDS !== "undefined") {
      for (const s of _stickerList) {
        if (seen.has(s.file)) continue;
        const kws = STICKER_KEYWORDS[s.file];
        if (!kws) continue;
        if (kws.some(kw => kw === word || kw.startsWith(word) || word.startsWith(kw))) {
          seen.add(s.file); out.push(s);
        }
      }
    }
    return out.slice(0, 6);
  }

  function updateEmojiSuggest() {
    if (!_emojiSuggestEl) return;
    const ta = els.msgInput;
    if (!ta || ta.disabled) { hideEmojiSuggest(); return; }
    // 이모지 피커/스티커 패널이 열려 있으면 겹치지 않게 표시 안 함
    if (els.emojiPicker && !els.emojiPicker.hidden) { hideEmojiSuggest(); return; }
    if (els.stickerPicker && !els.stickerPicker.hidden) { hideEmojiSuggest(); return; }
    const word = _currentWordBeforeCaret();
    const emojis = _matchEmojisForWord(word);
    const stickers = _matchStickersForWord(word);
    if (emojis.length === 0 && stickers.length === 0) { hideEmojiSuggest(); return; }
    let html = `<span class="es-label">${escapeHtml(word)}</span>`;
    // 내가 만든 스티커를 기본 이모지보다 먼저 표시 (우선순위)
    html += stickers.map(s => `<button type="button" class="es-sticker" data-file="${escapeHtml(s.file)}" data-label="${escapeHtml(s.label)}" title="스티커: ${escapeHtml(s.label)}"><img src="${BASE}/static/stickers/${encodeURIComponent(s.file)}" alt="${escapeHtml(s.label)}" loading="lazy"></button>`).join("");
    html += emojis.map(e => `<button type="button" class="es-chip" data-emoji="${e}" title="${escapeHtml(word)} → ${e}">${e}</button>`).join("");
    _emojiSuggestEl.innerHTML = html;
    _emojiSuggestEl.hidden = false;
  }

  function applyEmojiSuggestion(emoji) {
    const ta = els.msgInput;
    if (!ta) return;
    const pos = ta.selectionStart || 0;
    const before = ta.value.slice(0, pos);
    const after = ta.value.slice(pos);
    const m = before.match(_WORD_RE);
    const word = m ? m[1] : "";
    // 트리거 단어를 이모지로 교체 (대표 확정: 단어 → 이모지 교체)
    const newBefore = before.slice(0, before.length - word.length) + emoji;
    _suggestApplying = true;
    ta.value = newBefore + after;
    const caret = newBefore.length;
    ta.focus();
    ta.setSelectionRange(caret, caret);
    ta.dispatchEvent(new Event("input", { bubbles: true }));
    pushRecentEmoji(emoji);
    _suggestApplying = false;
    hideEmojiSuggest();
  }

  // 추천 스티커 클릭 — 트리거 단어를 입력창에서 지우고 스티커 미리보기 팝업 표시
  function applyStickerSuggestion(file, label) {
    if (!file) return;
    const ta = els.msgInput;
    if (ta) {
      const pos = ta.selectionStart || 0;
      const before = ta.value.slice(0, pos);
      const after = ta.value.slice(pos);
      const m = before.match(_WORD_RE);
      const word = m ? m[1] : "";
      const newBefore = before.slice(0, before.length - word.length);
      _suggestApplying = true;
      ta.value = newBefore + after;
      const caret = newBefore.length;
      ta.focus();
      ta.setSelectionRange(caret, caret);
      ta.dispatchEvent(new Event("input", { bubbles: true }));
      _suggestApplying = false;
    }
    hideEmojiSuggest();
    // 자동완성에서 선택해도 미리보기 팝업으로 먼저 확인 (직접 전송 금지)
    if (els.stickerPicker) {
      toggleStickerPicker(true);          // 패널 열기 (그리드 상태로 리셋)
      _showStickerPreview(file, label || file);  // 곧바로 미리보기 모드로 전환
    } else {
      sendSticker(file);  // 폴백 (stickerPicker 요소 없을 경우)
    }
  }

  if (_emojiSuggestEl) {
    // 칩을 누를 때 textarea 가 blur 되지 않도록 — 포커스·커서 유지
    _emojiSuggestEl.addEventListener("mousedown", (e) => e.preventDefault());
    _emojiSuggestEl.addEventListener("click", (e) => {
      const chip = e.target.closest(".es-chip");
      if (chip) {
        e.preventDefault();
        e.stopPropagation();
        applyEmojiSuggestion(chip.dataset.emoji);
        return;
      }
      const st = e.target.closest(".es-sticker");
      if (st) {
        e.preventDefault();
        e.stopPropagation();
        applyStickerSuggestion(st.dataset.file, st.dataset.label);
        return;
      }
    });
  }
  if (els.msgInput) {
    els.msgInput.addEventListener("input", () => {
      if (_suggestApplying) return;
      updateEmojiSuggest();
    });
    els.msgInput.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && _emojiSuggestEl && !_emojiSuggestEl.hidden) {
        hideEmojiSuggest();
        e.stopPropagation();
      }
      // 스페이스/엔터로 단어를 마무리하면 다음 input 에서 단어 토큰이 사라져 자동으로 닫힘
    });
    els.msgInput.addEventListener("blur", () => {
      // 칩 클릭(mousedown preventDefault) 이 아닌 실제 포커스 이탈 시 닫기
      setTimeout(hideEmojiSuggest, 120);
    });
  }

  // ============================================================
  // 🐶 스티커 — 패널에서 고르면 그림 한 장이 메시지로 전송 (kind='sticker')
  // ============================================================
  // 스티커 동의어 키워드 — 라벨에 없는 일상어로도 자동완성 추천되게. (파일명 → 키워드 목록)
  const STICKER_KEYWORDS = {
    "01.png": ["넵","넹","오케이","ok","알겠","알겠습니다","알았","체크","컨펌"],
    "02.png": ["감사","고마워","고맙","땡큐","ㄳ","ㄱㅅ","thank"],
    "03.png": ["처리","바로","진행","할게","하겠"],
    "04.png": ["검토","보는중","살펴"],
    "05.png": ["공유","보내줘","전달부탁"],
    "06.png": ["회의","미팅"],
    "07.png": ["잠시","잠깐","기다","ㄱㄷ"],
    "08.png": ["완료","끝","다했","끝났","마무리"],
    "09.png": ["승인","결재","사인","컨펌"],
    "10.png": ["퇴근","칼퇴","들어가"],
    "11.png": ["수정","반영","고쳤"],
    "12.png": ["재확인","다시확인"],
    "13.png": ["원인","분석"],
    "14.png": ["테스트","시험","검사"],
    "15.png": ["이슈","문제","에러","오류","장애","버그"],
    "16.png": ["로그","기록"],
    "17.png": ["일정","스케줄","날짜"],
    "18.png": ["자료","전달","파일"],
    "19.png": ["버전","업데이트","업뎃","패치"],
    "20.png": ["현장","대응"],
    "21.png": ["도면","캐드","cad"],
    "22.png": ["회로","기판","pcb"],
    "23.png": ["프로그램","코드","코딩","개발"],
    "24.png": ["재부팅","리부팅","껐다"],
    "25.png": ["셋업","세팅","설치"],
    "26.png": ["불량","ng","분석"],
    "27.png": ["부품","입고","자재"],
    "28.png": ["샘플","측정"],
    "29.png": ["치수","사이즈","이상없","정상"],
    "30.png": ["양산","적용"],
    "31.png": ["수고","고생","수고하","고생하","ㅅㄱ"],
    "32.png": ["힘내","힘냅","으쌰","기운"],
    "33.png": ["함께","같이","우리"],
    "34.png": ["회의하","회의할","미팅하"],
    "35.png": ["어서오","환영","웰컴","welcome"],
    "36.png": ["커피","카페","아메","아아"],
    "37.png": ["휴식","쉬자","쉴게","브레이크"],
    "38.png": ["안녕","하이","ㅎㅇ","hi","hello","인사"],
    "39.png": ["반가","반갑"],
    "40.png": ["좋은아침","굿모닝","아침","morning"],
    "41.png": ["부탁","잘부탁"],
    "42.png": ["고마워","고맙","감사","땡큐"],
    "43.png": ["미안","죄송","쏘리","sorry","ㅈㅅ"],
    "44.png": ["괜찮","괜춘","문제없","노프라블"],
    "45.png": ["최고","짱","대박","베스트"],
    "46.png": ["좋아","따봉","like","조아","굿"],
    "47.png": ["축하","추카","ㅊㅋ"],
    "48.png": ["배고","점심","배꼽","허기","밥"],
    "49.png": ["졸려","졸림","피곤","노곤","하품"],
    "50.png": ["심심","지루","노잼"],
    "51.png": ["행복","기뻐","신나"],
    "52.png": ["깜짝","놀랐","헐","깜놀"],
    "53.png": ["감동","감격","뭉클"],
    "54.png": ["화이팅","파이팅","아자","ㅎㅇㅌ","fighting"],
    "55.png": ["응원","응원해"],
    "56.png": ["잠깐","잠시","기다","ㄱㄷ"],
    "57.png": ["쉬는","휴식","쉬자"],
    "58.png": ["도착","왔어","도착했"],
    "59.png": ["출발","갈게","떠나"],
    "60.png": ["곧갈","가는중","곧도착"],
    "61.png": ["집에","귀가","집가"],
    "62.png": ["다녀","외출","나갔다"],
    "63.png": ["맛있게","식사","드세요","맛점","맛저"],
    "64.png": ["커피","카페"],
    "65.png": ["놀러","놀자","나가자"],
    "66.png": ["조심","잘가","살펴"],
    "67.png": ["잘자","굿나잇","굿밤","자요","ㅈㅈ"],
    "68.png": ["조립","어셈"],
    "69.png": ["포장","패킹"],
    "70.png": ["테스트","검사","시험"],
    "71.png": ["청소","정리"],
  };
  let _stickersLoaded = false;
  let _stickerList = [];
  async function loadStickers() {
    if (_stickersLoaded) return;
    try {
      const res = await fetch(`${BASE}/static/stickers/manifest.json`, { cache: "no-cache" });
      _stickerList = await res.json();
    } catch (e) { _stickerList = []; }
    _stickersLoaded = true;
    renderStickerGrid();
  }
  function renderStickerGrid() {
    const grid = document.getElementById("spGrid");
    if (!grid) return;
    if (!_stickerList.length) {
      grid.innerHTML = `<div class="sp-empty">스티커가 없습니다.</div>`;
      return;
    }
    grid.innerHTML = _stickerList.map(s =>
      `<button type="button" class="sp-item" data-file="${escapeHtml(s.file)}" title="${escapeHtml(s.label || "")}">
         <img src="${BASE}/static/stickers/${encodeURIComponent(s.file)}" alt="${escapeHtml(s.label || "")}" loading="lazy">
       </button>`
    ).join("");
  }
  function toggleStickerPicker(forceOpen) {
    const p = els.stickerPicker;
    if (!p) return;
    const willOpen = forceOpen !== undefined ? forceOpen : p.hidden;
    if (willOpen) {
      // 이모지 피커/추천바가 열려 있으면 닫기 (겹침 방지)
      if (els.emojiPicker && !els.emojiPicker.hidden) toggleEmojiPicker(false);
      hideEmojiSuggest();
      loadStickers();
      _hideStickerPreview();   // 미리보기 초기화 후 그리드 상태로 열기
      p.hidden = false;
    } else {
      _hideStickerPreview();   // 닫을 때도 미리보기 초기화
      p.hidden = true;
    }
  }
  function sendSticker(file) {
    if (!file) return;
    if (!activeRoom || !activeRoom.id) return;
    if (els.msgInput && els.msgInput.disabled) return;
    socket.emit("send", { room_id: activeRoom.id, sticker: file });
    toggleStickerPicker(false);
  }
  if (els.stickerBtn) {
    els.stickerBtn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      toggleStickerPicker();
    });
  }
  // ── 스티커 미리보기 ──
  let _spPreviewFile = null;   // 현재 미리보기 중인 스티커 파일명
  function _showStickerPreview(file, label) {
    const panel = els.stickerPicker;
    const prev  = document.getElementById("spPreview");
    const img   = document.getElementById("spPrevImg");
    const lbl   = document.getElementById("spPrevLabel");
    if (!panel || !prev || !img) return;
    _spPreviewFile = file;
    img.src = `${BASE}/static/stickers/${encodeURIComponent(file)}`;
    img.alt = label || "";
    if (lbl) lbl.textContent = label || "";
    // 그리드 숨기고 미리보기 표시
    panel.classList.add("sp-mode-preview");
    prev.hidden = false;
  }
  function _hideStickerPreview() {
    const panel = els.stickerPicker;
    const prev  = document.getElementById("spPreview");
    if (!panel || !prev) return;
    _spPreviewFile = null;
    panel.classList.remove("sp-mode-preview");
    prev.hidden = true;
  }
  // 스티커 그리드 클릭 → 미리보기
  if (els.stickerPicker) {
    els.stickerPicker.addEventListener("click", (e) => {
      // 그리드 아이템 클릭
      const btn = e.target.closest(".sp-item");
      if (btn) {
        e.preventDefault();
        e.stopPropagation();
        _showStickerPreview(btn.dataset.file, btn.title || btn.dataset.file);
        return;
      }
    });
  }
  // 미리보기 — "보내기" 버튼
  const _spSendBtn = document.getElementById("spPrevSend");
  if (_spSendBtn) {
    _spSendBtn.addEventListener("click", (e) => {
      e.preventDefault(); e.stopPropagation();
      if (_spPreviewFile) {
        sendSticker(_spPreviewFile);
        _hideStickerPreview();
      }
    });
  }
  // 미리보기 — "취소" 버튼
  const _spCancelBtn = document.getElementById("spPrevCancel");
  if (_spCancelBtn) {
    _spCancelBtn.addEventListener("click", (e) => {
      e.preventDefault(); e.stopPropagation();
      _hideStickerPreview();
    });
  }
  // 미리보기 — "← 뒤로" 버튼 (그리드로 복귀)
  const _spBackBtn = document.getElementById("spPrevBack");
  if (_spBackBtn) {
    _spBackBtn.addEventListener("click", (e) => {
      e.preventDefault(); e.stopPropagation();
      _hideStickerPreview();
    });
  }
  // 바깥 클릭으로 닫기
  document.addEventListener("click", (e) => {
    if (!els.stickerPicker || els.stickerPicker.hidden) return;
    if (els.stickerPicker.contains(e.target)) return;
    if (e.target === els.stickerBtn) return;
    // 미리보기 중 보내기 버튼 클릭 → form submit 이 스티커 전송을 처리하므로 여기서 닫지 않음
    if (_spPreviewFile && els.sendBtn && els.sendBtn.contains(e.target)) return;
    toggleStickerPicker(false);
  });
  // ESC 로 닫기
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && els.stickerPicker && !els.stickerPicker.hidden) {
      toggleStickerPicker(false);
    }
  });
  // 스티커 미리보기 중 Enter → 포커스 위치에 관계없이 스티커 전송
  // (그리드 직접 클릭 시 msgInput 포커스가 빠지므로 document 레벨에서 잡아야 함)
  document.addEventListener("keydown", (e) => {
    if (!_spPreviewFile) return;
    if (e.key !== "Enter" || e.shiftKey || e.isComposing || e.keyCode === 229) return;
    if (document.querySelector(".modal.open")) return;  // 모달 열려 있으면 무시
    // msgInput 포커스 있을 때는 msgInput.keydown → send() 에서 처리하므로 중복 방지
    if (document.activeElement === els.msgInput) return;
    e.preventDefault();
    const file = _spPreviewFile;
    sendSticker(file);
    _hideStickerPreview();
  });
  // 자동완성에서 즉시 추천하려면 스티커 목록을 미리 로드해 둔다.
  loadStickers();

  // ============================================================
  // 👥 사이드바 탭 — 방 목록 / 사용자 목록 토글
  // ============================================================
  let _sidebarTab = "rooms";   // 'rooms' | 'users'
  let _usersCache = [];

  function setSidebarTab(tab) {
    if (tab !== "rooms" && tab !== "users") return;
    _sidebarTab = tab;
    // 탭 active 상태
    if (els.sidebarTabs) {
      els.sidebarTabs.querySelectorAll(".sb-tab").forEach(b => {
        b.classList.toggle("active", b.dataset.tab === tab);
      });
      // 사용자 탭일 때만 업무대화방 칸을 좁히고 사용자 칸을 한 줄로 (대표 지시 2026-06-06)
      els.sidebarTabs.classList.toggle("users-active", tab === "users");
    }
    // 탭 전환 시 검색 입력 초기화 — 사용자 탭 검색어가 방 탭으로 넘어가지 않게 (대표 지시 2026-05-19)
    if (els.globalSearch) els.globalSearch.value = "";
    window._userListQuery = "";
    // placeholder — 통합검색이라 어느 탭이든 동일하게 (사용자·방·대화내용 한 번에) (대표 지시 2026-06-06)
    if (els.globalSearch) {
      els.globalSearch.placeholder = window.KNK_t ? window.KNK_t("ph.search") : "🔍 이름·방·내용 검색";
    }
    if (tab === "rooms") {
      if (els.userList) els.userList.hidden = true;
      if (els.userListToolbar) els.userListToolbar.hidden = true;
      if (els.filterBar) els.filterBar.hidden = false;
      if (els.searchResults) els.searchResults.hidden = true;
      // 방 목록 보이기 — renderRoomList 가 my-tasks/empty 등 분기 처리
      renderRoomList();
    } else {
      // 사용자 탭 — 방 관련 모든 패널 강제 숨김
      if (els.roomList) els.roomList.hidden = true;
      if (els.filterBar) els.filterBar.hidden = true;
      if (els.searchResults) els.searchResults.hidden = true;
      if (els.myTasks) els.myTasks.hidden = true;
      if (els.mentionsPanel) els.mentionsPanel.hidden = true;   // 멘션 패널도 숨김 — 사용자 탭과 겹침 방지 (대표 지시 2026-05-25)
      if (els.userList) els.userList.hidden = false;
      // 툴바는 비어있지만 향후 확장용으로 유지 (현재 hidden 가능)
      if (els.userListToolbar) els.userListToolbar.hidden = true;
      // 직원 등록 버튼은 헤더(.head-actions)로 이동 — 권한 체크는 별도 시점에서 처리
      renderUserList();
      try { _refreshUsersTabCount(); } catch (e) {}   // 법인별 인원수 최신화 — 첫 진입/추가·삭제 반영 (대표 지시 2026-06-06)
    }
    try { _updateUsersTabCorp(); } catch (e) {}   // 사용자 탭이면 현재 법인(한국/베트남) 표시, 아니면 숨김 (대표 지시 2026-06-06)
  }

  // ── 사용자 탭 법인(한국/베트남) 순환 — 탭 재클릭 또는 00_총괄 줄 토글 공통 (대표 지시 2026-06-06) ──
  let _usersCorpKeys = ["01_KOR", "02_VN"];
  let _curActiveCorp = "01_KOR";
  let _usersCorpCounts = { kor: null, vn: null, total: null };   // /api/users/counts 캐시
  function _corpLabelShort(k) {
    const en = (typeof _useEnNames === "function") ? _useEnNames() : false;
    if (k === "02_VN") return en ? "🇻🇳 VN" : "🇻🇳 베트남";
    if (k === "(미지정)") return en ? "❓ N/A" : "❓ 미지정";
    return en ? "🇰🇷 KR" : "🇰🇷 한국";
  }
  function _corpCountFor(k) {
    if (k === "02_VN") return _usersCorpCounts.vn;
    if (k === "01_KOR") return _usersCorpCounts.kor;
    return null;
  }
  // 사용자 탭 배지: 총원(132)은 업무대화방 탭에서만 / 법인별 한국·베트남 인원은 사용자 탭에서만 (대표 지시 2026-06-06)
  function _updateUsersTabCorp() {
    const inUsers = (_sidebarTab === "users");
    const tot = document.getElementById("usersTabCount");
    if (tot) {
      if (!inUsers && _usersCorpCounts.total != null) {
        tot.textContent = "(" + _usersCorpCounts.total + ")";
        tot.hidden = false;
      } else {
        tot.hidden = true;
      }
    }
    const el = document.getElementById("usersTabCorp");
    if (el) {
      if (inUsers && _usersCorpKeys.length) {
        let txt = _corpLabelShort(_curActiveCorp);
        const c = _corpCountFor(_curActiveCorp);
        if (c != null) txt += " " + c;
        el.textContent = txt;
        el.hidden = false;
      } else {
        el.hidden = true;
      }
    }
  }
  function _setActiveCorp(k) {
    _curActiveCorp = k;
    try { _saveActiveCorp(k); } catch (e) {}
    if (els.userList) els.userList.querySelectorAll(".user-corp-pane").forEach(p => { p.hidden = (p.getAttribute("data-corp-pane") !== k); });
    _updateUsersTabCorp();
  }

  // 부서별 색상 (자동 — 사용자가 부서 추가하면 색상 자동 매핑)
  const _DEPT_PALETTE = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16", "#a5282c", "#6366f1", "#f97316"];
  function _deptColor(dept) {
    if (!dept) return "#9ca3af";
    let h = 0;
    for (let i = 0; i < dept.length; i++) h = (h * 31 + dept.charCodeAt(i)) >>> 0;
    return _DEPT_PALETTE[h % _DEPT_PALETTE.length];
  }

  async function refreshUserList() {
    try {
      const all = await fetch(`${BASE}/api/users`).then(r => r.json());
      // '_deleted_user' 플레이스홀더는 디렉터리에서 숨김 (메시지 작성자 표시용으로만 존재)
      _usersCache = (Array.isArray(all) ? all : []).filter(u => u.username !== "_deleted_user");
      // users 캐시도 동기화 (헤더 본인 정보 source)
      if (Array.isArray(all)) {
        users = all.filter(u => u.username !== "_deleted_user");
        try { _updateMeHeaderInfo(); } catch(e) {}
      }
      if (_sidebarTab === "users") renderUserList();
    } catch (e) { /* noop */ }
  }

  // 부서 그룹 접기 상태 — localStorage 에 저장해 잦은 재렌더(상태 갱신)에도 보존
  function _loadCollapsedDepts() {
    try { return new Set(JSON.parse(localStorage.getItem("knkmsg.collapsedDepts") || "[]")); } catch (e) { return new Set(); }
  }
  let _collapsedDepts = _loadCollapsedDepts();
  function _saveCollapsedDepts() {
    try { localStorage.setItem("knkmsg.collapsedDepts", JSON.stringify([..._collapsedDepts])); } catch (e) {}
  }
  // 법인 접기 상태 (KOR/VN 단위 일괄 접기) — 대표 지시 2026-05-26
  function _loadCollapsedCorps() {
    try { return new Set(JSON.parse(localStorage.getItem("knkmsg.collapsedCorps") || "[]")); } catch (e) { return new Set(); }
  }
  let _collapsedCorps = _loadCollapsedCorps();
  function _saveCollapsedCorps() {
    try { localStorage.setItem("knkmsg.collapsedCorps", JSON.stringify([..._collapsedCorps])); } catch (e) {}
  }
  // 직원 디렉터리 활성 법인 책갈피(본사/베트남) — 대표 지시 2026-06-05
  function _loadActiveCorp() { try { return localStorage.getItem("knkmsg.activeCorp") || ""; } catch (e) { return ""; } }
  function _saveActiveCorp(k) { try { localStorage.setItem("knkmsg.activeCorp", k); } catch (e) {} }
  // 정식 부서 목록 — 등록인원 없어도 항상 표시 (대표 지시 2026-05-26)
  const CORP_DEPTS = {
    "01_KOR": [
      "00_총괄","01_기술영업팀","02_검사기팀","03_품질팀",
      "04_설계팀","05_소프트웨어팀","06_전장설계팀",
      "07_제조기술1팀","08_제조기술2팀","09_가공팀","10_구매팀",
      "11_관리팀","12_개발혁신팀","21_라이프밸류팀",
    ],
    "02_VN": [
      "00_총괄","01_기술팀","02_설계팀","03_소프트웨어팀","04_가공팀",
      "05_조립팀","06_전장팀","07_품질팀","08_관리팀","09_구매팀",
    ],
  };
  const _CANONICAL_DEPTS = new Set();
  Object.keys(CORP_DEPTS).forEach(c => CORP_DEPTS[c].forEach(d => _CANONICAL_DEPTS.add(c + "/" + d)));
  // 옛 부서명 → 새 정식 부서명 (사용자 목록 그룹핑 시 자동 통합). DB 자체는 그대로 — 다음 엑셀 업로드로 영구 정리. (대표 지시 2026-05-26)
  const _LEGACY_DEPT_MAP = {
    "총괄":                "01_KOR/00_총괄",
    "기술영업팀":          "01_KOR/01_기술영업팀",
    "검사기팀":            "01_KOR/02_검사기팀",
    "검사기팀(연구소)":    "01_KOR/02_검사기팀",
    "품질팀":              "01_KOR/03_품질팀",
    "설계팀(자동화)":      "01_KOR/04_설계팀",
    "설계팀(검사기)":      "01_KOR/04_설계팀",
    "설계팀(연구소)":      "01_KOR/04_설계팀",
    "설계팀":              "01_KOR/04_설계팀",
    "01_KOR/04_설계팀(검사기/자동화)": "01_KOR/04_설계팀",   // 이미 새 형식이지만 옛 명칭으로 저장된 경우
    "소프트웨어팀":        "01_KOR/05_소프트웨어팀",
    "소프트웨어팀(연구소)": "01_KOR/05_소프트웨어팀",
    "전장설계팀":          "01_KOR/06_전장설계팀",
    "전장설계팀(연구소)":  "01_KOR/06_전장설계팀",
    "제조기술1팀":         "01_KOR/07_제조기술1팀",
    "제조기술2팀":         "01_KOR/08_제조기술2팀",
    "가공팀":              "01_KOR/09_가공팀",
    "구매팀":              "01_KOR/10_구매팀",
    "관리팀":              "01_KOR/11_관리팀",
    "개발혁신팀":          "01_KOR/12_개발혁신팀",
    "개발혁신팀(연구소)":  "01_KOR/12_개발혁신팀",
    "라이프밸류팀":        "01_KOR/21_라이프밸류팀",
    "라이프밸류팀(연구소)": "01_KOR/21_라이프밸류팀",
    "베트남법인":          "02_VN/00_총괄",
    "12 베트남법인":       "02_VN/00_총괄",
  };
  function renderUserList() {
    if (!els.userList) return;
    if (!_usersCache.length) {
      els.userList.innerHTML = `<div class="empty-state" style="padding:32px;font-size:calc(13px + var(--fs-add-ui));">사용자가 없습니다.</div>`;
      return;
    }
    // 검색 필터 (globalSearch 입력) — 이름·직급·부서·부서코드라벨·이메일 매칭 (대표 지시 2026-05-19)
    const q = (window._userListQuery || "").trim().toLowerCase();
    let filtered = _usersCache;
    if (q) {
      filtered = _usersCache.filter(u => {
        const dept = u.department || "";
        const deptLabel = dept ? (typeof deptDisplayLabel === "function" ? deptDisplayLabel(dept) : dept) : "";
        const hay = [
          u.display_name || "", u.title || "", dept, deptLabel,
          u.username || "", u.email || "", u.employee_no || ""
        ].join(" ").toLowerCase();
        return hay.includes(q);
      });
      if (!filtered.length) {
        els.userList.innerHTML = `<div class="empty-state" style="padding:32px;font-size:calc(13px + var(--fs-add-ui));">검색 결과 없음 — "${escapeHtml(q)}"</div>`;
        return;
      }
    }
    // ── 고객(게스트) 화면 — 멤버 목록을 단순 2구역으로 (대표 지시 2026-05-31) ──
    //   상단: 고객 (고객사명별)  ·  하단: 우리 직원 (케이엔케이 본사 / 케이엔케이 VN, 부서 구분 없이 일괄)
    //   직원 본인 화면(디렉터리)은 아래 기존 법인→부서 구조 그대로 유지.
    //   서버 /api/users 가 게스트에겐 '자기 방 멤버'만 반환하므로 여기 filtered = 이 방 참여자.
    if (window._meIsGuest) {
      const _ko = (typeof _curLang !== "function") || _curLang() === "ko";
      const _lang = (typeof _curLang === "function") ? _curLang() : "ko";
      const _isG = (u) => (u.is_guest === 1 || u.is_guest === true);
      const _nameSort = (a, b) =>
        (a.id === meId ? -1 : b.id === meId ? 1
          : String(a.display_name || "").localeCompare(String(b.display_name || ""), "ko"));
      const _card = (u) => {
        const isMe = u.id === meId;
        const inactive = !u.active;
        const si = (window._userStatusMap && window._userStatusMap[u.id]) || null;
        const dot = si ? _dispStatusColor(si.status) : "#9ca3af";
        const sl = si ? (_dispStatusLabel(si.status) + _dispOfficeSuffix(si)) : "";
        const ct = si && si.custom_text ? ` · ${escapeHtml(si.custom_text)}` : "";
        const _until = si ? _statusUntilText(si) : "";
        const _untilChip = _until ? ` <span class="user-until-chip">${_until}</span>` : "";
        const _ttl = _dispTitle(u);
        const ttl = _ttl ? `<span class="user-title-chip">${escapeHtml(_ttl)}</span>` : "";
        return `
          <div class="user-card ${inactive ? 'user-inactive-row' : ''}" data-uid="${u.id}" ${inactive ? 'data-inactive="1"' : ''}>
            <div class="user-card-avatar" style="background:${u.avatar_color || '#3b82f6'}">${_avatarBody(u)}</div>
            <div class="user-card-info">
              <div class="user-card-name">${escapeHtml(_dispName(u))}${isMe ? ' <span class="rs-me">' + window.KNK_t("umenu.me") + '</span>' : ''}</div>
              <div class="user-card-meta">${ttl}<span class="user-status-text" style="color:${dot};">${escapeHtml(sl)}${_untilChip}${ct}</span></div>
            </div>
            <button type="button" class="user-card-menu-btn" data-uid="${u.id}" title="${window.KNK_t("title.userMenu")}">⋮</button>
          </div>`;
      };
      let gh = "";
      // 상단: 고객 (고객사명별) — 지금까지 부서명이던 헤더를 '고객사명'으로
      const _guests = filtered.filter(_isG);
      if (_guests.length) {
        const byCo = {};
        _guests.forEach(u => {
          const c = ((u.guest_company || "").trim()) || (_ko ? "고객사" : "Customer");
          (byCo[c] = byCo[c] || []).push(u);
        });
        Object.keys(byCo).sort((a, b) => a.localeCompare(b, "ko")).forEach(co => {
          byCo[co].sort(_nameSort);
          gh += `<div class="user-dept-head" style="border-left:3px solid #DE2910;"><span>🏢 ${escapeHtml(co)}</span> <span class="user-dept-count">${byCo[co].length}</span></div>`;
          gh += `<div class="user-dept-body">` + byCo[co].map(_card).join("") + `</div>`;
        });
      }
      // 하단: 우리 직원 — 부서 구분 없이 본사 / VN 두 그룹으로만 일괄
      const _staff = filtered.filter(u => !_isG(u));
      const _isVN = (u) => deptSortKey(u.department || "").startsWith("02_VN/");
      const _unit = (n) => _ko ? "명" : (_lang === "vi" ? " người" : " people");
      const _grp = (label, arr) => {
        if (!arr.length) return "";
        arr.sort(_nameSort);
        return `<div class="user-corp-head" style="background:#1f2937;color:#fff;padding:8px 14px;font-size:calc(13px + var(--fs-add-ui));font-weight:700;margin-top:12px;border-radius:6px 6px 0 0;display:flex;align-items:center;justify-content:space-between;"><span>${escapeHtml(label)}</span><span style="opacity:.75;font-weight:500;font-size:calc(12px + var(--fs-add-ui));">${arr.length}${_unit(arr.length)}</span></div>`
          + `<div class="user-dept-body">` + arr.map(_card).join("") + `</div>`;
      };
      const _hqLabel = _ko ? "🇰🇷 케이엔케이 본사" : "🇰🇷 KNK HQ";
      const _vnLabel = _ko ? "🇻🇳 케이엔케이 VN" : "🇻🇳 KNK Vietnam";
      gh += _grp(_hqLabel, _staff.filter(u => !_isVN(u)));
      gh += _grp(_vnLabel, _staff.filter(u => _isVN(u)));
      els.userList.innerHTML = gh || `<div class="empty-state" style="padding:32px;font-size:calc(13px + var(--fs-add-ui));">${_ko ? "표시할 멤버가 없습니다." : "No members to show."}</div>`;
      _bindUserCardEvents();
      return;
    }
    // 사용자 카드 1개 HTML — 부서 트리·검색 결과 양쪽에서 재사용 (대표 지시 2026-06-04)
    //   showDept=true (검색 결과) 면 어느 팀 소속인지 보이도록 부서명 칩을 함께 표기
    function _userCardHtml(u, showDept) {
      const isMe = u.id === meId;
      const inactive = !u.active;
      const statusInfo = (window._userStatusMap && window._userStatusMap[u.id]) || null;
      const dotColor = statusInfo ? _dispStatusColor(statusInfo.status) : "#9ca3af";
      const statusLabel = statusInfo ? _dispStatusLabel(statusInfo.status) : "";
      const customText = statusInfo && statusInfo.custom_text ? ` · ${escapeHtml(statusInfo.custom_text)}` : "";
      const officeText = _dispOfficeSuffix(statusInfo);
      const untilTxt = statusInfo ? _statusUntilText(statusInfo) : "";
      const untilChip = untilTxt ? ` <span class="user-until-chip">${untilTxt}</span>` : "";
      const _ttl = _dispTitle(u);
      const title = _ttl ? `<span class="user-title-chip">${escapeHtml(_ttl)}</span>` : "";
      const ceoBadge = (window._meRole === "ceo")
        ? (u.is_owner ? `<span class="user-ceo-badge user-owner-badge">${window.KNK_t("umenu.owner")}</span>`
                      : (u.role === "ceo" ? `<span class="user-ceo-badge">${window.KNK_t("badge.admin")}</span>` : ""))
        : "";
      const inactiveLabel = inactive ? `<span class="user-inactive">${window.KNK_t("badge.inactive")}</span>` : "";
      const aiAllowed = (u.ai_summary_allowed === 1 || u.ai_summary_allowed === true);
      const worksAllowed = (u.works_access === 1 || u.works_access === true);
      const aiwBadges = (aiAllowed || worksAllowed)
        ? `<span class="user-ai-badge${aiAllowed ? '' : ' ub-off'}" title="${window.KNK_t ? window.KNK_t("badge.aiAllowed") : "AI 사용 가능"}">AI</span>`
          + `<span class="user-works-badge${worksAllowed ? '' : ' ub-off'}" title="${window.KNK_t ? window.KNK_t("badge.worksAllowed") : "WORKS 사용 가능"}">W</span>`
        : "";
      const isGuestUser = (u.is_guest === 1 || u.is_guest === true);
      const guestCompanyText = isGuestUser && u.guest_company ? ` (${u.guest_company})` : "";
      const guestBadge = isGuestUser ? `<span class="user-guest-badge" title="외부 사용자">🏢 외부${escapeHtml(guestCompanyText)}</span>` : "";
      // 부서명 칩 — 검색 결과(평탄 목록)에서만. 어느 팀 소속인지 바로 구분되게 (대표 지시 2026-06-04)
      const _deptRaw = u.department || "";
      const _deptLbl = _deptRaw ? ((_useEnNames() && u.department_en) ? u.department_en : (typeof deptDisplayLabel === "function" ? deptDisplayLabel(_deptRaw) : _deptRaw)) : "";
      const deptChip = (showDept && _deptLbl) ? `<span class="user-dept-chip">${escapeHtml(_deptLbl)}</span>` : "";
      return `
        <div class="user-card ${inactive ? 'user-inactive-row' : ''}" data-uid="${u.id}" ${inactive ? 'data-inactive="1"' : ''}>
          <div class="user-card-avatar" style="background:${u.avatar_color || '#3b82f6'}">${_avatarBody(u)}</div>
          <div class="user-card-info">
            <div class="user-card-name">${escapeHtml(_dispName(u))}${isMe ? ' <span class="rs-me">' + window.KNK_t("umenu.me") + '</span>' : ''} ${ceoBadge} ${inactiveLabel}</div>
            <div class="user-card-meta">${deptChip}${title}<span class="user-status-text" style="color:${dotColor};">${escapeHtml(statusLabel)}${officeText}${untilChip}${customText}</span><span class="user-card-badges">${aiwBadges}${guestBadge}</span></div>
          </div>
          <button type="button" class="user-card-menu-btn" data-uid="${u.id}" title="${window.KNK_t("title.userMenu")}">⋮</button>
        </div>`;
    }
    // 🔍 검색 중에는 부서 트리를 접고, 매칭된 사용자만 평탄한 목록으로 맨 위에 표시 (대표 지시 2026-06-04)
    //   → 이름 검색 시 그 사람이 부서 위치와 상관없이 바로 보임. 검색어 지우면 아래 부서 트리로 복귀.
    if (q) {
      const _hits = filtered.slice().sort((a, b) => {
        if (a.id === meId) return -1;
        if (b.id === meId) return 1;
        return String(a.display_name || "").localeCompare(String(b.display_name || ""), "ko");
      });
      let _sh = `<div class="user-dept-head user-search-head" style="border-left:3px solid #A5282C;"><span>🔍 검색 결과</span> <span class="user-dept-count">${_hits.length}</span></div>`;
      _sh += `<div class="user-dept-body">` + _hits.map(u => _userCardHtml(u, true)).join("") + `</div>`;
      els.userList.innerHTML = _sh;
      _bindUserCardEvents();
      return;
    }
    // 부서별 그룹핑
    const groups = {};
    filtered.forEach(u => {
      let key = u.department || "(미지정)";
      // 옛 부서명 → 새 정식 부서명 자동 통합 (검사기팀(연구소) → 02_검사기팀, 베트남법인 → 02_VN/00_총괄 등)
      if (_LEGACY_DEPT_MAP[key]) key = _LEGACY_DEPT_MAP[key];
      if (!groups[key]) groups[key] = [];
      groups[key].push(u);
    });
    // 정식 부서 목록을 빈 그룹으로 미리 채움 — 등록인원 없어도 표시 (대표 지시 2026-05-26)
    _CANONICAL_DEPTS.forEach(d => { if (!groups[d]) groups[d] = []; });
    const myDept = (_usersCache.find(u => u.id === meId) || {}).department || "(미지정)";
    // 표시할 부서: 정식 부서(항상) 또는 등록인원 있는 부서. 둘 다 아니면(=옛 빈 부서) 숨김.
    const deptKeys = Object.keys(groups).filter(d => _CANONICAL_DEPTS.has(d) || (groups[d] && groups[d].length > 0)).sort((a, b) => {
      if (a === myDept && b !== myDept) return -1;   // 내 부서 최상위
      if (b === myDept && a !== myDept) return 1;
      if (a === "(미지정)") return 1; if (b === "(미지정)") return -1;
      const ca = deptSortKey(a);
      const cb = deptSortKey(b);
      if (ca !== cb) return ca.localeCompare(cb);
      return a.localeCompare(b);
    });
    // 부서 내 사용자 정렬 우선순위 (대표 지시 2026-05-19 갱신)
    //   0 팀장 > 1 파트장 > 2 상무 > 3 이사 > 4 매니저 > 5 프로 > 6 사원 > 9 그 외
    //   동순위는 display_name 가나다순 (한국어 collation)
    function _titleRank(t) {
      const s = String(t || "");
      if (s.includes("팀장"))   return 0;
      if (s.includes("파트장")) return 1;
      if (s.includes("상무"))   return 2;
      if (s.includes("이사"))   return 3;
      if (s.includes("매니저")) return 4;
      if (s.includes("프로"))   return 5;
      if (s.includes("사원"))   return 6;
      return 9;
    }
    const isCeo = (window._meRole === "ceo");
    // 법인 판정(새 체계 정렬키 기반) — 옛 데이터도 deptSortKey 가 새 형식으로 매핑 (대표 지시 2026-05-26)
    const _corpOf = (d) => {
      const sk = deptSortKey(d);
      if (sk.startsWith("01_KOR/")) return "01_KOR";
      if (sk.startsWith("02_VN/")) return "02_VN";
      return "(미지정)";
    };
    // 본사/베트남 전체 인원 집계
    let _hqCount = 0, _vnCount = 0;
    filtered.forEach(u => {
      const d = u.department || "";
      if (!d) return;
      const c = _corpOf(d);
      if (c === "02_VN") _vnCount++;
      else if (c === "01_KOR") _hqCount++;
    });
    // ── 본사/베트남 '책갈피(탭)' — 법인을 상단 탭으로 분리 (대표 지시 2026-06-05) ──
    //   기존: 인라인 법인 접기 헤더 → 변경: 상단 탭 [본사][베트남](+미지정), 부서 그룹은 각 탭 안에 유지.
    const _enN = _useEnNames();
    let _unCount = 0;
    filtered.forEach(u => { const d = u.department || ""; if (!d || _corpOf(d) === "(미지정)") _unCount++; });
    // 법인별 부서 그룹 HTML 버킷
    const corpBuckets = { "01_KOR": "", "02_VN": "", "(미지정)": "" };
    deptKeys.forEach((dept) => {
      const _corp = _corpOf(dept);
      const color = _deptColor(dept);
      // 부서 라벨 — 영어/베트남 모드면 department_en 사용 (대표 지시 2026-05-27)
      let deptLabel;
      if (dept === "(미지정)") {
        deptLabel = dept;
      } else if (_enN) {
        const _sample = groups[dept].find(u => u.department_en);
        deptLabel = _sample ? _sample.department_en : deptDisplayLabel(dept);
      } else {
        deptLabel = deptDisplayLabel(dept);
      }
      // 부서 내부 정렬 — 팀장(0) → 파트장(1) → 그 외 → 동일 순위는 display_name 가나다순
      groups[dept].sort((a, b) => {
        if (a.id === meId) return -1;   // 본인은 자기 부서 안에서 항상 맨 위
        if (b.id === meId) return 1;
        const ra = _titleRank(a.title);
        const rb = _titleRank(b.title);
        if (ra !== rb) return ra - rb;
        return String(a.display_name || "").localeCompare(String(b.display_name || ""), "ko");
      });
      const _deptCollapsed = _collapsedDepts.has(dept);
      let _h = `<div class="user-dept-head${_deptCollapsed ? ' collapsed' : ''}" data-dept="${escapeHtml(dept)}" style="border-left:3px solid ${color};"><span class="dept-arrow">▾</span>${escapeHtml(deptLabel)} <span class="user-dept-count">${groups[dept].length}</span></div>`;
      _h += `<div class="user-dept-body"${_deptCollapsed ? ' hidden' : ''}>`;
      _h += groups[dept].map(u => _userCardHtml(u, false)).join("");
      _h += `</div>`;   // /user-dept-body
      corpBuckets[_corp] += _h;
    });
    // 표시할 법인 탭: 본사·베트남(항상) + 미지정(인원 있을 때만)
    const _corpDefs = [
      { key: "01_KOR", label: _enN ? "🇰🇷 HQ" : "🇰🇷 본사", n: _hqCount },
      { key: "02_VN",  label: _enN ? "🇻🇳 VN" : "🇻🇳 베트남", n: _vnCount },
    ];
    if (_unCount > 0 || corpBuckets["(미지정)"]) _corpDefs.push({ key: "(미지정)", label: _enN ? "❓ N/A" : "❓ 미지정", n: _unCount });
    // 활성 탭 결정: 저장값 → 내 법인 → 본사
    const _myCorp = _corpOf(myDept);
    let _activeCorp = _loadActiveCorp();
    if (!_corpDefs.some(c => c.key === _activeCorp)) _activeCorp = (_corpDefs.some(c => c.key === _myCorp) ? _myCorp : "01_KOR");
    const _panesHtml = _corpDefs.map(c =>
      `<div class="user-corp-pane" data-corp-pane="${escapeHtml(c.key)}"${c.key === _activeCorp ? '' : ' hidden'}>${
        corpBuckets[c.key] || `<div class="empty-state" style="padding:24px;font-size:calc(12px + var(--fs-add-ui));color:var(--text-soft);">${_enN ? 'No members' : '해당 법인 직원이 없습니다.'}</div>`
      }</div>`
    ).join("");
    // 본사/베트남 — 별도 탭 줄 없이, 각 법인 pane 첫 부서(00_총괄) 헤더 오른쪽에 '순환 토글' 하나.
    //   현재 법인 표시 + 클릭하면 다음 법인으로 전환 (본사 ↔ 베트남). (대표 지시 2026-06-06)
    els.userList.innerHTML = _panesHtml;
    // 법인 순환 상태 공유 — 법인 전환은 '사용자' 탭 재클릭으로만 (00_총괄 줄 토글은 제거, 대표 지시 2026-06-06)
    _usersCorpKeys = _corpDefs.map(c => c.key);
    _curActiveCorp = _activeCorp;
    try { _updateUsersTabCorp(); } catch (e) {}
    // 부서 헤더 클릭 → 그 부서 접기/펼치기 (탭 안에서 동작, 상태 localStorage 보존)
    els.userList.querySelectorAll(".user-dept-head").forEach(head => {
      head.addEventListener("click", () => {
        const dept = head.dataset.dept;
        if (!dept) return;
        const nowCollapsed = !_collapsedDepts.has(dept);
        if (nowCollapsed) _collapsedDepts.add(dept); else _collapsedDepts.delete(dept);
        _saveCollapsedDepts();
        head.classList.toggle("collapsed", nowCollapsed);
        const body = head.nextElementSibling;
        if (body && body.classList.contains("user-dept-body")) body.hidden = nowCollapsed;
      });
    });
    // 이벤트: 카드 클릭 → 컨텍스트 메뉴 (실수 클릭으로 방이 만들어지는 사고 방지, 대표 지시 2026-05-27)
    //  · 1:1 방 생성은 메뉴의 "💬 1:1 대화" 항목을 거쳐야 함 (좌클릭/우클릭/⋮/롱프레스 모두 동일 메뉴 진입)
    //  · ⋮ 버튼은 별도 핸들러 (아래) — 카드 클릭 이벤트는 통과
    //  · 함수로 추출 — 일반 디렉터리 / 고객(게스트) 단순목록 양쪽에서 재사용 (대표 지시 2026-05-31)
    function _bindUserCardEvents() {
    els.userList.querySelectorAll(".user-card").forEach(card => {
      card.addEventListener("click", (e) => {
        if (e.target.closest(".user-card-menu-btn")) return;   // 메뉴 버튼은 별도
        const uid = parseInt(card.dataset.uid, 10);
        if (card.dataset.inactive === "1") {
          alert(window.KNK_t("alert.inactiveDm"));
          return;
        }
        // 좌클릭 → 컨텍스트 메뉴 (자신·타인 동일). 메뉴에서 "💬 1:1 대화" 선택 시에만 방 생성.
        showUserContextMenu(uid, e.clientX, e.clientY);
      });
    });
    els.userList.querySelectorAll(".user-card-menu-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const uid = parseInt(btn.dataset.uid, 10);
        showUserContextMenu(uid, e.clientX, e.clientY);
      });
    });
    // 우클릭 (PC) — 사용자 기본 정보 + 액션
    els.userList.querySelectorAll(".user-card").forEach(card => {
      card.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        const uid = parseInt(card.dataset.uid, 10);
        showUserContextMenu(uid, e.clientX, e.clientY);
      });
      // 모바일 롱프레스 (0.5초)
      let _upTimer = null, _upXY = { x: 0, y: 0 };
      card.addEventListener("touchstart", (e) => {
        const t = e.touches[0];
        _upXY = { x: t.clientX, y: t.clientY };
        _upTimer = setTimeout(() => {
          _upTimer = null;
          const uid = parseInt(card.dataset.uid, 10);
          showUserContextMenu(uid, _upXY.x, _upXY.y);
        }, 500);
      }, { passive: true });
      card.addEventListener("touchmove", (e) => {
        const t = e.touches[0];
        if (Math.abs(t.clientX - _upXY.x) > 10 || Math.abs(t.clientY - _upXY.y) > 10) {
          if (_upTimer) { clearTimeout(_upTimer); _upTimer = null; }
        }
      }, { passive: true });
      card.addEventListener("touchend", () => {
        if (_upTimer) { clearTimeout(_upTimer); _upTimer = null; }
      }, { passive: true });
      card.addEventListener("touchcancel", () => {
        if (_upTimer) { clearTimeout(_upTimer); _upTimer = null; }
      }, { passive: true });
    });
    }   // /_bindUserCardEvents
    _bindUserCardEvents();
  }

  // ─── 사용자 카드 컨텍스트 메뉴 (우클릭/롱프레스) ───
  // 모바일 뒤로가기: 메뉴 열렸을 때 뒤로 = 메뉴만 닫기(1회), 한 번 더 = 창 이동 (대표 지시 2026-05-24)
  let _ctxMenuStatePushed = false;   // 메뉴 열 때 history 상태를 넣었는지
  let _ctxIgnorePop = false;         // 수동 닫기로 우리가 history.back 한 popstate 는 무시
  function _ctxPushState() {
    if (_ctxMenuStatePushed) return;
    try { history.pushState({ knkCtxMenu: true }, ""); _ctxMenuStatePushed = true; } catch (e) {}
  }
  function closeUserContextMenu(opts) {
    document.querySelectorAll(".user-context-menu").forEach(m => m.remove());
    if (opts && opts.keepHistory) return;   // 재오픈 — history 상태 그대로 유지
    // 수동 닫기(클릭·외부·ESC)면 넣어둔 history 상태를 정리. popstate 로 닫힌 경우는 이미 pop 됨.
    if (_ctxMenuStatePushed && !(opts && opts.fromPopstate)) {
      _ctxMenuStatePushed = false;
      _ctxIgnorePop = true;
      try { history.back(); } catch (e) { _ctxIgnorePop = false; }
    }
  }
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".user-context-menu")) closeUserContextMenu();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeUserContextMenu();
  });

  // 🔍 관리자 전용 — 사용자 접속/알림 진단 결과 팝업 (읽기 전용, 인라인 스타일) (대표 지시 2026-05-25)
  function _showUserDiag(d) {
    const u = d.user || {}, L = d.live || {};
    const sess = d.active_sessions || [], push = d.push_subscriptions || [];
    let interp;
    if (L.online && L.has_pc_connection) interp = "지금 💻 컴퓨터로 접속 중입니다.";
    else if (L.online && L.active_device === "mobile") interp = "지금 📱 휴대폰으로 접속 중입니다.";
    else if (L.online) interp = "지금 접속 중입니다.";
    else if (push.length) interp = "미접속 상태이지만 휴대폰 알림 등록이 남아 있어 '📱 휴대폰'으로 표시됩니다. (실제 사용 중이 아니라 — 알림만 받을 수 있는 상태)";
    else interp = "완전히 오프라인입니다 (접속·알림 등록 모두 없음) → '⚫ 오프라인'으로 표시됩니다.";
    const fmt = (s) => (s || s === 0) ? escapeHtml(String(s)) : "—";
    const sessHtml = sess.length
      ? sess.map(s => `<li>[${fmt(s.device_type)}] ${fmt(s.created_at)} · ip ${fmt(s.ip)}<br><span style="color:#9ca3af;font-size:calc(11px + var(--fs-add-ui));">${fmt(s.user_agent)}</span></li>`).join("")
      : `<li style="color:#9ca3af;">접속 세션 없음</li>`;
    const pushHtml = push.length
      ? push.map(p => `<li>등록 ${fmt(p.created_at)} · 최근 ${fmt(p.last_used)}<br><span style="color:#9ca3af;font-size:calc(11px + var(--fs-add-ui));">${fmt(p.user_agent)}</span></li>`).join("")
      : `<li style="color:#9ca3af;">알림 등록 없음</li>`;
    const ov = document.createElement("div");
    ov.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:9999;display:flex;align-items:center;justify-content:center;padding:16px;";
    ov.innerHTML = `
      <div style="background:#fff;max-width:440px;width:100%;max-height:86vh;overflow:auto;border-radius:14px;padding:18px 18px 14px;box-shadow:0 12px 40px rgba(0,0,0,.25);font-size:calc(13px + var(--fs-add-ui));line-height:1.6;color:#1a1a1a;">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px;">
          <strong style="font-size:calc(15px + var(--fs-add-ui));">🔍 접속 진단 — ${fmt(u.display_name)}</strong>
          <button type="button" data-diag-close style="border:none;background:#f1f1f1;border-radius:8px;padding:4px 10px;cursor:pointer;font-size:calc(14px + var(--fs-add-ui));">✕</button>
        </div>
        <div style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:10px;padding:10px 12px;margin-bottom:10px;">
          <div style="font-weight:700;margin-bottom:4px;">현재 표시 상태: ${fmt(L.computed_label)} ${L.at_office ? '· 🏢 회사망' : ''}</div>
          <div>${escapeHtml(interp)}</div>
        </div>
        <div style="margin-bottom:8px;"><b>실시간 접속</b>: ${L.online ? '🟢 접속 중' : '⚫ 미접속'} &nbsp;|&nbsp; PC연결: ${L.has_pc_connection ? '있음' : '없음'} &nbsp;|&nbsp; 사용기기: ${fmt(L.active_device)}</div>
        <div style="margin-bottom:6px;"><b>접속 세션 (${sess.length})</b></div>
        <ul style="margin:0 0 10px;padding-left:18px;">${sessHtml}</ul>
        <div style="margin-bottom:6px;"><b>휴대폰 알림 등록 (${push.length})</b></div>
        <ul style="margin:0 0 6px;padding-left:18px;">${pushHtml}</ul>
        <div style="color:#9ca3af;font-size:calc(11px + var(--fs-add-ui));margin-top:8px;">아이디 ${fmt(u.username)} · 저장된 상태 ${fmt(u.saved_status)}</div>
      </div>`;
    document.body.appendChild(ov);
    const close = () => ov.remove();
    ov.addEventListener("click", (e) => { if (e.target === ov) close(); });
    ov.querySelector("[data-diag-close]").addEventListener("click", close);
    document.addEventListener("keydown", function esc(e){ if (e.key === "Escape") { close(); document.removeEventListener("keydown", esc); } });
  }

  function showUserContextMenu(uid, clientX, clientY) {
    closeUserContextMenu({ keepHistory: true });   // 이전 메뉴 DOM 만 정리, history 상태는 재사용
    const u = _usersCache.find(x => x.id === uid);
    if (!u) return;
    const me = _usersCache.find(x => x.id === meId);
    const isCeo = me && me.role === "ceo";
    const isSelf = uid === meId;
    const statusInfo = (window._userStatusMap && window._userStatusMap[uid]) || null;
    const dotColor = statusInfo ? _dispStatusColor(statusInfo.status) : "#9ca3af";
    const statusLabel = statusInfo ? (_dispStatusLabel(statusInfo.status) + _dispOfficeSuffix(statusInfo)) : _statusLabel("notConnected");
    const customText = statusInfo && statusInfo.custom_text ? statusInfo.custom_text : "";

    const menu = document.createElement("div");
    menu.className = "msg-context-menu user-context-menu";
    menu.innerHTML = `
      <div class="ucm-card">
        <div class="ucm-avatar" style="background:${u.avatar_color || '#3b82f6'}" data-uid="${u.id}">${_avatarBody(u)}</div>
        <div class="ucm-body">
          <div class="ucm-name">${escapeHtml(_dispName(u))}${isSelf ? ' <span class="ucm-me">' + window.KNK_t("umenu.me") + '</span>' : ''}${u.is_owner ? ' <span class="ucm-ceo">' + window.KNK_t("umenu.owner") + '</span>' : ((u.role === 'ceo' && isSelf) ? ' <span class="ucm-ceo">' + window.KNK_t("umenu.admin") + '</span>' : '')}${!u.active ? ' <span class="ucm-inactive">' + window.KNK_t("umenu.inactive") + '</span>' : ''}</div>
          ${window._meIsGuest ? '' : `<div class="ucm-row"><span class="ucm-label">${window.KNK_t("umenu.empNo")}</span><span class="ucm-value">${escapeHtml(u.employee_no || window.KNK_t("umenu.unset"))}</span></div>`}
          <div class="ucm-row"><span class="ucm-label">${window.KNK_t("umenu.title")}</span><span class="ucm-value">${escapeHtml(_dispTitle(u) || window.KNK_t("umenu.unset"))}</span></div>
          <div class="ucm-row"><span class="ucm-label">${window.KNK_t("umenu.dept")}</span><span class="ucm-value">${escapeHtml(_dispDept(u) || window.KNK_t("umenu.unset"))}</span></div>
          <div class="ucm-row"><span class="ucm-label">${window.KNK_t("umenu.email")}</span><span class="ucm-value">${u.email ? `<a href="mailto:${escapeHtml(u.email)}" class="ucm-link" title="${window.KNK_t("umenu.emailSend")}">${escapeHtml(u.email)}</a>` : `<span class="ucm-unset">${window.KNK_t("umenu.unset")}</span>`}</span></div>
          <div class="ucm-row"><span class="ucm-label">${window.KNK_t("umenu.phone")}</span><span class="ucm-value">${u.phone ? `<a href="tel:${escapeHtml((u.phone||'').replace(/[^0-9+]/g,''))}" class="ucm-link" title="${window.KNK_t("umenu.phoneCall")}">${escapeHtml(u.phone)}</a>` : `<span class="ucm-unset">${window.KNK_t("umenu.unset")}</span>`}</span></div>
          <div class="ucm-row"><span class="ucm-label">${window.KNK_t("umenu.status")}</span><span class="ucm-value" style="color:${dotColor};font-weight:600;">${escapeHtml(statusLabel)}</span></div>
          ${customText ? `<div class="ucm-row"><span class="ucm-label">${window.KNK_t("umenu.memo")}</span><span class="ucm-value">${escapeHtml(customText)}</span></div>` : ''}
          ${window._meIsGuest ? '' : `<div class="ucm-row"><span class="ucm-label">${window.KNK_t("umenu.id")}</span><span class="ucm-value ucm-mono">${escapeHtml(u.username || '')}</span></div>`}
        </div>
      </div>
      ${(u.avatar_url || isCeo) ? `
      <div class="ucm-photo-section">
        <div class="ucm-photo-title">${window.KNK_t("umenu.photo")}</div>
        ${u.avatar_url
          ? `<img class="ucm-photo" src="${escapeHtml(u.avatar_url)}" alt="${window.KNK_t("umenu.photo")}"${isCeo ? ` data-photo-upload title="${window.KNK_t("umenu.photoChangeTitle")}"` : ''}>`
          : `<div class="ucm-photo-empty"${isCeo ? ' data-photo-upload' : ''}>${isCeo ? window.KNK_t("umenu.photoRegister") : window.KNK_t("umenu.photoNone")}</div>`}
        ${isCeo ? `<div class="ucm-photo-actions"><button type="button" class="ucm-photo-btn" data-photo-upload>${u.avatar_url ? window.KNK_t("umenu.photoChangeBtn") : window.KNK_t("umenu.photoAddBtn")}</button>${u.avatar_url ? `<button type="button" class="ucm-photo-btn ucm-photo-del" data-photo-remove>${window.KNK_t("umenu.photoRemoveBtn")}</button>` : ''}</div>` : ''}
      </div>
      ` : ''}
      <div class="mcm-divider"></div>
      ${!isSelf && u.active && !window._meIsGuest ? `<button type="button" class="mcm-item" data-act="dm"><span class="mcm-icon">💬</span><span>${window.KNK_t("umenu.dm")}</span></button>` : ''}
      ${!isSelf && u.active && activeRoom && activeRoom.type !== 'direct' && activeRoom.type !== 'self' ? `<button type="button" class="mcm-item" data-act="whisper"><span class="mcm-icon">🤫</span><span>${window.KNK_t("umenu.whisper")}</span></button>` : ''}
      ${u.email ? `<div class="mcm-row">
        <button type="button" class="mcm-item mcm-row-main" data-act="email"><span class="mcm-icon">📧</span><span>${window.KNK_t("umenu.emailSend")}</span></button>
        <button type="button" class="mcm-copy-btn" data-act="copy_email" title="${window.KNK_t("umenu.copyEmailTitle")}">${window.KNK_t("umenu.copyBtn")}</button>
      </div>` : ''}
      ${u.phone ? `<div class="mcm-row">
        <button type="button" class="mcm-item mcm-row-main" data-act="phone"><span class="mcm-icon">📞</span><span>${window.KNK_t("umenu.phoneCall")}</span></button>
        <button type="button" class="mcm-copy-btn" data-act="copy_phone" title="${window.KNK_t("umenu.copyPhoneTitle")}">${window.KNK_t("umenu.copyBtn")}</button>
      </div>` : ''}
      ${isCeo ? `<button type="button" class="mcm-item" data-act="edit"><span class="mcm-icon">✏</span><span>${window.KNK_t("umenu.editInfo")}</span></button>` : ''}
      ${isCeo && !isSelf && !(u.is_owner && !window._meIsOwner) ? `<button type="button" class="mcm-item" data-act="reset_password"><span class="mcm-icon">🔑</span><span>${window.KNK_t("umenu.resetPw")}</span></button>` : ''}
      ${isCeo ? `<button type="button" class="mcm-item" data-act="userdiag"><span class="mcm-icon">🔍</span><span>접속 진단</span></button>` : ''}
      ${!isSelf ? `<button type="button" class="mcm-item" data-act="mention"><span class="mcm-icon">@</span><span>${window.KNK_t("umenu.mention")}</span></button>` : ''}
    `;
    document.body.appendChild(menu);
    const w = menu.offsetWidth, h = menu.offsetHeight;
    let x = clientX, y = clientY;
    if (x + w > window.innerWidth - 8) x = window.innerWidth - w - 8;
    if (y + h > window.innerHeight - 8) y = window.innerHeight - h - 8;
    if (x < 8) x = 8; if (y < 8) y = 8;
    menu.style.left = x + "px"; menu.style.top = y + "px";
    // 별도 '얼굴 사진' 공간 — 업로드(자동 512px 리사이즈) / 제거 (관리자만, 사진 보기는 전체 사용자). 아바타는 상태표시 그대로. (대표 지시 2026-05-22)
    menu.querySelectorAll("[data-photo-upload]").forEach(el => {
      el.style.cursor = "pointer";
      el.addEventListener("click", (ev) => { ev.stopPropagation(); _triggerAvatarUpload(uid); });
    });
    const _photoRemoveBtn = menu.querySelector("[data-photo-remove]");
    if (_photoRemoveBtn) {
      _photoRemoveBtn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        if (!confirm(window.KNK_t("confirm.removePhoto"))) return;
        closeUserContextMenu();
        await _triggerAvatarDelete(uid);
      });
    }
    menu.querySelectorAll(".mcm-item, .mcm-copy-btn").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const act = btn.dataset.act;
        // 복사 동작은 메뉴를 닫지 않고 유지 — 연속 복사·확인 편의 (대표 지시 2026-05-24)
        if (act !== "copy_email" && act !== "copy_phone") closeUserContextMenu();
        if (act === "dm") {
          const res = await fetch(`${BASE}/api/rooms/direct/${uid}`, { method: "POST" }).then(r => r.json());
          if (res.error) { alert(res.error); return; }
          await refreshRooms();
          setSidebarTab("rooms");
          const r = rooms.find(x => x.id === res.room_id);
          if (r) openRoom(r);
        } else if (act === "edit") {
          openUserInfoDialog(uid);
        } else if (act === "reset_password") {
          // 🔑 관리자 비밀번호 초기화 — 전화번호(숫자만)로 초기화 + 첫 로그인 시 새 비번 강제 (규칙 5)
          const phoneDigits = (u.phone || "").replace(/\D/g, "");
          if (!phoneDigits) { alert(window.KNK_t("alert.noPhoneForReset","이 사용자의 전화번호가 없어 초기화할 수 없습니다.\n먼저 '정보 수정'에서 전화번호를 입력·저장한 뒤 다시 시도하세요.")); return; }
          if (!confirm(window.KNK_t("confirm.resetPwd","{name} 님의 비밀번호를 전화번호({phone})로 초기화할까요?\n\n초기화 후 사용자는 첫 로그인 시 새 비밀번호를 설정합니다.").replace("{name}", u.display_name).replace("{phone}", phoneDigits))) return;
          try {
            const res = await fetch(`${BASE}/api/users/${uid}/reset_password`, { method: "POST" }).then(r => r.json());
            if (res.error) { alert("❌ " + res.error); return; }
            alert(window.KNK_t("alert.pwdResetDone","✅ 비밀번호가 초기화되었습니다.\n임시 비밀번호(전화번호): {pw}\n\n사용자에게 전달하세요. 첫 로그인 시 새 비밀번호를 설정하게 됩니다.").replace("{pw}", res.temp_password));
          } catch (e) { alert(window.KNK_t("alert.networkError","❌ 네트워크 오류") + ": " + (e.message || e)); }
        } else if (act === "userdiag") {
          // 🔍 관리자 전용 — 사용자 접속/알림 현황 진단 (읽기 전용) (대표 지시 2026-05-25)
          try {
            const d = await fetch(`${BASE}/api/admin/user_diag/${uid}`).then(r => r.json());
            if (d.error) { alert("❌ " + d.error); return; }
            _showUserDiag(d);
          } catch (e) { alert(window.KNK_t("alert.networkError","❌ 네트워크 오류") + ": " + (e.message || e)); }
        } else if (act === "remove_photo") {
          if (!confirm(window.KNK_t("confirm.removeProfilePhoto","프로필 사진을 제거하고 기본 아이콘으로 되돌릴까요?"))) return;
          await _triggerAvatarDelete(uid);
        } else if (act === "whisper") {
          startWhisperMode(uid, u.display_name);
        } else if (act === "email" && u.email) {
          window.location.href = "mailto:" + u.email;
        } else if (act === "phone" && u.phone) {
          const digits = u.phone.replace(/[^0-9+]/g, "");
          window.location.href = "tel:" + digits;
        } else if (act === "copy_phone" && u.phone) {
          try {
            await navigator.clipboard.writeText(u.phone);
            // 임시 토스트 (간단)
            const t = document.createElement("div");
            t.textContent = "📋 " + u.phone + " 복사됨";
            t.style.cssText = "position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#10B981;color:#fff;padding:10px 16px;border-radius:8px;font-size:calc(13px + var(--fs-add-ui));z-index:99999;box-shadow:0 4px 12px rgba(0,0,0,0.2);";
            document.body.appendChild(t);
            setTimeout(() => t.remove(), 1500);
          } catch (e) { alert(window.KNK_t("alert.copyFail","복사 실패") + ": " + (e.message || e)); }
        } else if (act === "copy_email" && u.email) {
          try {
            await navigator.clipboard.writeText(u.email);
            const t = document.createElement("div");
            t.textContent = "📋 " + u.email + " 복사됨";
            t.style.cssText = "position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#10B981;color:#fff;padding:10px 16px;border-radius:8px;font-size:calc(13px + var(--fs-add-ui));z-index:99999;box-shadow:0 4px 12px rgba(0,0,0,0.2);";
            document.body.appendChild(t);
            setTimeout(() => t.remove(), 1500);
          } catch (e) { alert(window.KNK_t("alert.copyFail","복사 실패") + ": " + (e.message || e)); }
        } else if (act === "mention") {
          if (!activeRoom) {
            alert(window.KNK_t("alert.selectRoomFirst"));
            return;
          }
          const tag = "@" + (u.display_name || u.username);   // 이름으로 멘션 (이메일 X) — 대표 지시 2026-05-22
          const input = els.msgInput;
          if (input) {
            const start = input.selectionStart || input.value.length;
            const end = input.selectionEnd || input.value.length;
            input.value = input.value.slice(0, start) + tag + " " + input.value.slice(end);
            const pos = start + tag.length + 1;
            input.selectionStart = input.selectionEnd = pos;
            input.focus();
            try { input.dispatchEvent(new Event("input", { bubbles: true })); } catch (_) {}
          }
        }
      });
    });
    // 모바일: 메뉴가 열리면 history 상태 1개 추가 → 뒤로가기 1회 = 메뉴만 닫힘, 2회째 = 창 이동
    if (window.innerWidth <= 720) _ctxPushState();
  }

  function _getStatusColor(status) {
    const map = {
      online: "#10B981", away: "#9CA3AF", busy: "#EF4444",
      meeting: "#F59E0B", external: "#8B5CF6", dnd: "#DC2626", offline: "#6B7280",
    };
    return map[status] || "#9ca3af";
  }

  // ── 상태표시 상세(기기·회사망) on/off — 관리자 설정(window._presenceDetail). 표시만 제어 ──
  //  OFF(기본): 접속(online/mobile)을 '🟢 접속' 하나로 — 컴퓨터/휴대폰 구분·(회사) 꼬리표 숨김.
  //  ON: 기존처럼 💻 컴퓨터/📱 휴대폰 + (회사). 특수상태(회의·외근·휴가 등)는 양쪽 동일. (대표 지시 2026-06-01)
  function _presenceDetail() { return window._presenceDetail === true; }
  function _isConnStatus(s) { return s === "online" || s === "mobile"; }
  // 표시용 라벨 — 단순모드 + 접속이면 '🟢 접속'(i18n status.connected), 그 외엔 평소 라벨
  function _dispStatusLabel(status) {
    if (!_presenceDetail() && _isConnStatus(status)) {
      if (window.KNK_t) { const v = window.KNK_t("status.connected"); if (v && v !== "status.connected") return v; }
      return "🟢 접속";
    }
    return _statusLabel(status);
  }
  // 표시용 색 — 단순모드 + 접속이면 녹색 고정
  function _dispStatusColor(status) {
    if (!_presenceDetail() && _isConnStatus(status)) return "#10B981";
    return _getStatusColor(status);
  }
  // (회사) 꼬리표 — 상세모드 + 회사망 + 접속일 때만 표시
  function _dispOfficeSuffix(st) {
    if (!st) return "";
    return (_presenceDetail() && st.at_office && _isConnStatus(st.status)) ? " (회사)" : "";
  }

  // ── 상태 기한(until_at) — 회의중·외근=오늘 시각 / 해외·국내출장·휴가=종료일 (대표 지시 2026-06-06) ──
  const _STATUS_UNTIL_TIME = { meeting: 1, external: 1 };               // 시간 입력(오늘)
  const _STATUS_UNTIL_DATE = { overseas: 1, domestic: 1, vacation: 1 }; // 날짜 입력(종료일)
  function _ymdLocal(d) {
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }
  function _hmLocal(d) {
    return String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
  }
  // 사용자 목록 이름 옆 표시용 — '🕒 ~15:00'(시간) 또는 '📅 ~6/10'(날짜). 해당 상태 + 기한 있을 때만.
  function _statusUntilText(st) {
    if (!st || !st.until_at) return "";
    const s = st.status;
    const isTime = !!_STATUS_UNTIL_TIME[s], isDate = !!_STATUS_UNTIL_DATE[s];
    if (!isTime && !isDate) return "";
    let d;
    try { d = new Date(st.until_at); } catch (e) { return ""; }
    if (!d || isNaN(d.getTime())) return "";
    return isTime ? ("🕒 ~" + _hmLocal(d)) : ("📅 ~" + (d.getMonth() + 1) + "/" + d.getDate());
  }
  // 상태창 — 선택 상태에 따라 시간/날짜 입력칸 토글 + 비어있으면 기본값(시간=+1h, 날짜=오늘)
  function _syncStatusUntilUI(key) {
    const area = els.statusUntilArea, tIn = els.statusUntilTime, dIn = els.statusUntilDate, lab = els.statusUntilLabel;
    if (!area) return;
    const isTime = !!_STATUS_UNTIL_TIME[key], isDate = !!_STATUS_UNTIL_DATE[key];
    if (!isTime && !isDate) { area.style.display = "none"; return; }
    area.style.display = "";
    if (tIn) {
      tIn.style.display = isTime ? "" : "none";
      if (isTime && !tIn.value) { const n = new Date(); n.setHours(n.getHours() + 1, 0, 0, 0); tIn.value = _hmLocal(n); }
    }
    if (dIn) {
      dIn.style.display = isDate ? "" : "none";
      if (isDate) {
        const todayY = _ymdLocal(new Date());
        dIn.setAttribute("min", todayY);
        if (!dIn.value) dIn.value = todayY;
      }
    }
    if (lab) {
      lab.textContent = isTime
        ? ((window.KNK_t && window.KNK_t("label.statusUntilTime")) || "오늘 몇 시까지?")
        : ((window.KNK_t && window.KNK_t("label.statusUntilDate")) || "언제까지? (종료일)");
    }
  }
  // 저장용 — 선택된 상태 카드 안의 입력칸 값을 until_at(ISO UTC)로 변환. KST(로컬)→UTC 정확 변환. (대표 지시 2026-06-07 카드 내 입력)
  function _collectStatusUntil(statusKey) {
    const area = els.statusOptionsArea;
    if (!area) return null;
    const card = area.querySelector('.status-option-card[data-status="' + statusKey + '"]');
    const inp = card && card.querySelector(".sc-until-input");
    const val = inp && inp.value;
    if (!val) return null;
    if (_STATUS_UNTIL_TIME[statusKey]) {
      if (/^\d{1,2}:\d{2}$/.test(val)) {
        const parts = val.split(":");
        const d = new Date();
        d.setHours(parseInt(parts[0], 10), parseInt(parts[1], 10), 0, 0);
        return d.toISOString();
      }
    } else if (_STATUS_UNTIL_DATE[statusKey]) {
      if (/^\d{4}-\d{2}-\d{2}$/.test(val)) {
        const p = val.split("-").map(Number);
        const d = new Date(p[0], p[1] - 1, p[2], 23, 59, 59, 0);  // 그 날 끝까지(로컬)
        return d.toISOString();
      }
    }
    return null;
  }

  // 사용자 정보 수정 다이얼로그
  function openUserInfoDialog(uid) {
    const u = _usersCache.find(x => x.id === uid);
    if (!u) return;
    const me = _usersCache.find(x => x.id === meId);
    const isCeo = me && me.role === "ceo";
    const isSelf = uid === meId;
    if (!isCeo) {
      // 정보 수정은 관리자(ceo)만 — 비관리자(본인 포함)는 읽기 전용 미리보기. 권한(role) 은 노출 안 함.
      const lines = [
        `이름: ${u.display_name}`,
        `직급: ${u.title || '(미설정)'}`,
        `부서: ${u.department || '(미설정)'}`,
        u.active ? "" : "⚠ 비활성 계정 (퇴사 등)",
      ].filter(Boolean);
      alert(lines.join("\n"));
      return;
    }
    // 다이얼로그 채우기
    if (els.uiName) els.uiName.textContent = u.display_name + (isSelf ? " (내 정보)" : "");
    if (els.uiHint) els.uiHint.textContent = isCeo && !isSelf
      ? "관리자 권한으로 다른 사용자 정보를 변경합니다."
      : "본인 정보를 변경합니다.";
    if (els.uiTitle) els.uiTitle.value = u.title || "";
    if (els.uiEmployeeNo) els.uiEmployeeNo.value = u.employee_no || "";
    // 부서 — select 옵션에 있으면 select 사용, 없으면 기타 + 직접 입력
    const knownDepts = Array.from(els.uiDeptSelect?.options || []).map(o => o.value);
    if (u.department && knownDepts.includes(u.department)) {
      els.uiDeptSelect.value = u.department;
      els.uiDeptCustom.style.display = "none";
      els.uiDeptCustom.value = "";
    } else if (u.department) {
      els.uiDeptSelect.value = "기타";
      els.uiDeptCustom.style.display = "";
      els.uiDeptCustom.value = u.department;
    } else {
      els.uiDeptSelect.value = "";
      els.uiDeptCustom.style.display = "none";
      els.uiDeptCustom.value = "";
    }
    // 부서 select 변경 시 "기타" 면 입력란 노출
    els.uiDeptSelect.onchange = () => {
      els.uiDeptCustom.style.display = els.uiDeptSelect.value === "기타" ? "" : "none";
    };
    // 이메일·전화번호 채우기
    if (els.uiEmail) els.uiEmail.value = u.email || "";
    if (els.uiPhone) els.uiPhone.value = u.phone || "";
    // 본인 정보일 때만 비밀번호 변경 버튼 노출
    const pwBtn = document.getElementById("uiChangePwBtn");
    if (pwBtn) {
      pwBtn.hidden = !isSelf;
      pwBtn.onclick = () => {
        try { els.userInfoDialog.close(); } catch (_) {}
        openChangePasswordDialog();
      };
    }
    // CEO 전용 필드
    if (els.uiCeoFields) {
      els.uiCeoFields.style.display = isCeo ? "" : "none";
      if (isCeo && els.uiDisplayName) els.uiDisplayName.value = u.display_name || "";
      if (isCeo && els.uiRoleCeo) els.uiRoleCeo.checked = u.role === "ceo";
      if (isCeo && els.uiActive) els.uiActive.checked = !!u.active;
      // 권한(관리자 선정·해지)은 최고관리자만 — 일반 관리자에겐 숨김 (규칙 1)
      const roleRow = document.getElementById("uiRoleRow");
      if (roleRow) roleRow.style.display = window._meIsOwner ? "" : "none";
      // 📱 전화번호로 비밀번호 초기화 (관리자) — 최고관리자 계정은 본인만 (규칙 5)
      const resetPwBtn = document.getElementById("uiResetPwBtn");
      if (resetPwBtn) {
        resetPwBtn.style.display = (u.is_owner && !window._meIsOwner) ? "none" : "";
        resetPwBtn.onclick = async () => {
          const phoneDigits = (u.phone || "").replace(/\D/g, "");
          if (!phoneDigits) { alert(window.KNK_t("alert.noPhoneForReset2","이 사용자의 전화번호가 없어 초기화할 수 없습니다. 먼저 전화번호를 입력·저장하세요.")); return; }
          if (!confirm(window.KNK_t("confirm.resetPwd","{name} 님의 비밀번호를 전화번호({phone})로 초기화할까요?\n\n초기화 후 사용자는 첫 로그인 시 새 비밀번호를 설정합니다.").replace("{name}", u.display_name).replace("{phone}", phoneDigits))) return;
          try {
            const res = await fetch(`${BASE}/api/users/${uid}/reset_password`, { method: "POST" }).then(r => r.json());
            if (res.error) { alert("❌ " + res.error); return; }
            alert(window.KNK_t("alert.pwdResetDone","✅ 비밀번호가 초기화되었습니다.\n임시 비밀번호(전화번호): {pw}\n\n사용자에게 전달하세요. 첫 로그인 시 새 비밀번호를 설정하게 됩니다.").replace("{pw}", res.temp_password));
          } catch (e) { alert(window.KNK_t("alert.networkError","❌ 네트워크 오류") + ": " + (e.message || e)); }
        };
      }
      // 🗑 삭제 버튼 — 본인 또는 id=1 은 노출 안 함 (서버도 차단하지만 UI 에서 명확)
      const delBtn = document.getElementById("uiDeleteBtn");
      if (delBtn) {
        const canDelete = isCeo && !isSelf && uid !== 1;
        delBtn.style.display = canDelete ? "" : "none";
        delBtn.onclick = async () => {
          const confirmMsg = `🗑 계정 완전 삭제\n\n사용자: ${u.display_name}\nID: ${u.username || u.email || '?'}\n\n이 작업은 되돌릴 수 없습니다.\n메시지·이력은 "(삭제된 사용자)" 로 표시됩니다.\n\n정말 삭제하시겠습니까?`;
          if (!confirm(confirmMsg)) return;
          // 2차 확인 — 이름 직접 입력
          const typed = prompt(`확실하게 진행하려면 사용자 이름을 정확히 입력하세요:\n\n[${u.display_name}]`);
          if (typed !== u.display_name) {
            if (typed !== null) alert(window.KNK_t("alert.nameMismatchCancel","이름이 일치하지 않습니다. 삭제 취소."));
            return;
          }
          delBtn.disabled = true;
          delBtn.textContent = "삭제 중…";
          try {
            const res = await fetch(`${BASE}/api/users/${uid}`, { method: "DELETE" }).then(r => r.json());
            if (res.error) { alert("❌ " + res.error); return; }
            alert(window.KNK_t("alert.accountDeleted","✅ {name} 님의 계정이 삭제되었습니다.").replace("{name}", res.display_name));
            try { els.userInfoDialog.close(); } catch (_) {}
            await refreshUserList();
          } catch (e) {
            alert(window.KNK_t("alert.networkError","❌ 네트워크 오류") + ": " + (e.message || e));
          } finally {
            delBtn.disabled = false;
            delBtn.textContent = "🗑 이 계정 완전 삭제";
          }
        };
      }
    }
    // 저장
    els.uiSaveBtn.onclick = async () => {
      const payload = {
        title: els.uiTitle.value.trim(),
        department: els.uiDeptSelect.value === "기타"
          ? els.uiDeptCustom.value.trim()
          : els.uiDeptSelect.value,
        email: els.uiEmail ? els.uiEmail.value.trim() : "",
        phone: els.uiPhone ? els.uiPhone.value.trim() : "",
        employee_no: els.uiEmployeeNo ? els.uiEmployeeNo.value.trim() : "",
      };
      if (isCeo) {
        const newName = els.uiDisplayName?.value?.trim();
        if (newName) payload.display_name = newName;
        payload.active = els.uiActive?.checked ? 1 : 0;
        // 관리자 권한(role) 변경은 최고관리자만 전송 — 일반 관리자는 role 미포함 (규칙 1, 서버 403 방지)
        if (window._meIsOwner) {
          payload.role = els.uiRoleCeo?.checked ? "ceo" : "staff";
          // 본인을 강등하려는 경우 한 번 더 확인
          if (uid === meId && payload.role === "staff" && u.role === "ceo") {
            if (!confirm(window.KNK_t("confirm.revokeMyAdmin","⚠ 본인의 관리자 권한을 해제하시겠습니까?\n\n해제하면 직원 등록·다른 사용자 정보 수정 등 관리 기능이 차단됩니다. 진행할까요?"))) {
              return;
            }
          }
        }
      }
      const res = await fetch(`${BASE}/api/users/${uid}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).then(r => r.json());
      if (res.error) { alert(res.error); return; }
      els.userInfoDialog.close();
      await refreshUserList();
    };
    try { els.userInfoDialog.showModal(); } catch (_) {}
  }

  // 탭 클릭 wire
  if (els.sidebarTabs) {
    els.sidebarTabs.addEventListener("click", (e) => {
      const b = e.target.closest(".sb-tab");
      if (!b) return;
      const tab = b.dataset.tab;
      // 이미 '사용자' 탭이면 클릭할 때마다 법인 순환(한국 ↔ 베트남), '사용자 (N)' 뒤에 표시 (대표 지시 2026-06-06)
      if (tab === "users" && _sidebarTab === "users") {
        if (_usersCorpKeys.length > 1) {
          const i = Math.max(0, _usersCorpKeys.indexOf(_curActiveCorp));
          _setActiveCorp(_usersCorpKeys[(i + 1) % _usersCorpKeys.length]);
        }
        return;
      }
      setSidebarTab(tab);
    });
  }

  // ─── ➕ 직원 등록 (관리자 전용) ───
  if (els.newUserBtn && els.newUserDialog) {
    // 헤더 버튼은 항상 숨김 — 설정 → 🛠 관리자 탭의 '🆔 직원 등록' 으로 진입 (대표 지시 2026-05-26)
    els.newUserBtn.hidden = true;
    els.newUserBtn.addEventListener("click", () => {
      // 관리자 전용 가드 — 버튼이 어떤 이유로 보이더라도 일반 직원은 진입 차단 (서버도 403)
      if (window._meRole !== "ceo") { alert(window.KNK_t("alert.adminOnly","관리자 전용 기능입니다.")); return; }
      // 폼 초기화 — 본사·베트남 양쪽 모두 (대표 지시 2026-05-26 사번=ID 분리)
      ["nuKEmployeeNo","nuKDisplayName","nuKDisplayNameEn","nuKPhone","nuKEmail","nuKTitle","nuKDept",
       "nuVEmployeeNo","nuVDisplayName","nuVDisplayNameVn","nuVDisplayNameEn","nuVPhone","nuVEmail","nuVTitle","nuVDept"
      ].forEach(k => { if (els[k]) els[k].value = ""; });
      if (els.nuKRoleCeo) els.nuKRoleCeo.checked = false;
      if (els.nuVRoleCeo) els.nuVRoleCeo.checked = false;
      if (els.nuResult) els.nuResult.textContent = "";
      // 서브탭 기본 = 본사
      _setNuSubTab("kor");
      // 일괄 탭 초기화
      const bulkResult = document.getElementById("nuBulkResult");
      if (bulkResult) bulkResult.innerHTML = "";
      const bulkFile = document.getElementById("nuBulkFile");
      if (bulkFile) bulkFile.value = "";
      // 기본 탭: 1명 등록
      _setNuTab("single");
      try { els.newUserDialog.showModal(); } catch (_) {}
    });
    // 탭 토글
    function _setNuTab(tab) {
      document.querySelectorAll(".nu-tab").forEach(b => {
        b.classList.toggle("active", b.dataset.nuTab === tab);
      });
      const single = document.getElementById("nuPaneSingle");
      const bulk = document.getElementById("nuPaneBulk");
      if (single) single.hidden = (tab !== "single");
      if (bulk) bulk.hidden = (tab !== "bulk");
    }
    document.querySelectorAll(".nu-tab").forEach(b => {
      b.addEventListener("click", () => _setNuTab(b.dataset.nuTab));
    });
    // 본사 ↔ 베트남 서브탭 (1명 등록 안쪽)
    function _setNuSubTab(sub) {
      document.querySelectorAll(".nu-sub-tab").forEach(b => {
        b.classList.toggle("active", b.dataset.nuSub === sub);
      });
      const kor = document.getElementById("nuSubKor");
      const vn = document.getElementById("nuSubVn");
      if (kor) kor.hidden = (sub !== "kor");
      if (vn) vn.hidden = (sub !== "vn");
      // 결과 박스 초기화 (탭 전환 시 옛 결과 잔존 방지)
      if (els.nuResult) els.nuResult.textContent = "";
    }
    document.querySelectorAll(".nu-sub-tab").forEach(b => {
      b.addEventListener("click", () => _setNuSubTab(b.dataset.nuSub));
    });
    // 양식 다운로드
    const tplBtn = document.getElementById("nuTplDownloadBtn");
    if (tplBtn) {
      tplBtn.addEventListener("click", () => {
        // 새 탭 안 열고 다운로드 트리거
        const a = document.createElement("a");
        a.href = `${BASE}/api/users/bulk/template`;
        a.download = "KNK_직원등록_양식.xlsx";
        document.body.appendChild(a);
        a.click();
        a.remove();
      });
    }
    // 엑셀 업로드 + 일괄 등록
    const upBtn = document.getElementById("nuBulkUploadBtn");
    if (upBtn) {
      upBtn.addEventListener("click", async () => {
        const fInput = document.getElementById("nuBulkFile");
        const resultBox = document.getElementById("nuBulkResult");
        if (!fInput || !fInput.files || !fInput.files[0]) {
          alert(window.KNK_t("alert.excelSelect"));
          return;
        }
        const file = fInput.files[0];
        if (!file.name.toLowerCase().endsWith(".xlsx") && !file.name.toLowerCase().endsWith(".xlsm")) {
          alert(window.KNK_t("alert.excelOnly"));
          return;
        }
        const fd = new FormData();
        fd.append("file", file);
        upBtn.disabled = true;
        const prevText = upBtn.textContent;
        upBtn.textContent = "업로드 중…";
        if (resultBox) resultBox.innerHTML = `<div style="padding:12px;text-align:center;color:var(--text-soft);">📤 처리 중…</div>`;
        try {
          const res = await fetch(`${BASE}/api/users/bulk`, { method: "POST", body: fd }).then(r => r.json());
          if (res.error) {
            if (resultBox) resultBox.innerHTML = `<div style="padding:12px;color:#dc2626;">❌ ${escapeHtml(res.error)}</div>`;
            return;
          }
          // 결과 렌더
          let html = `
            <div style="background:#ECFDF5;border:1px solid #10B981;border-radius:8px;padding:12px;margin-bottom:8px;">
              <div style="font-weight:700;color:#065F46;font-size:calc(14px + var(--fs-add-ui));">
                ✅ 일괄 처리 완료 — 신규 ${res.created_count}건 · 수정 ${res.updated_count || 0}건 · 스킵 ${res.skipped_count}건 · 오류 ${res.error_count}건
              </div>
            </div>`;
          if (res.created && res.created.length) {
            html += `<details style="margin-bottom:6px;"><summary style="cursor:pointer;font-weight:600;color:#065F46;font-size:calc(12.5px + var(--fs-add-ui));">✅ 신규 등록 ${res.created.length}건 (펼쳐서 확인)</summary>`;
            html += `<div style="max-height:200px;overflow-y:auto;font-size:calc(11.5px + var(--fs-add-ui));padding:6px;border:1px solid #D1FAE5;border-radius:6px;margin-top:4px;">`;
            res.created.forEach(c => {
              html += `<div style="padding:2px 0;"><b>${escapeHtml(c.name)}</b> · ${escapeHtml(c.email)} · 초기PW: <code>${escapeHtml(c.phone_initial_pw)}</code></div>`;
            });
            html += `</div></details>`;
          }
          if (res.updated && res.updated.length) {
            html += `<details style="margin-bottom:6px;"><summary style="cursor:pointer;font-weight:600;color:#1D4ED8;font-size:calc(12.5px + var(--fs-add-ui));">✏ 정보 수정 ${res.updated.length}건 (기존 직원 — 펼쳐서 확인)</summary>`;
            html += `<div style="max-height:200px;overflow-y:auto;font-size:calc(11.5px + var(--fs-add-ui));padding:6px;border:1px solid #BFDBFE;border-radius:6px;margin-top:4px;">`;
            res.updated.forEach(u => {
              html += `<div style="padding:2px 0;"><b>${escapeHtml(u.name)}</b> · ${escapeHtml(u.email)}</div>`;
            });
            html += `</div></details>`;
          }
          if (res.skipped && res.skipped.length) {
            html += `<details style="margin-bottom:6px;"><summary style="cursor:pointer;font-weight:600;color:#92400E;font-size:calc(12.5px + var(--fs-add-ui));">⏭ 스킵 ${res.skipped.length}건 (이미 등록·예시 행)</summary>`;
            html += `<div style="max-height:160px;overflow-y:auto;font-size:calc(11.5px + var(--fs-add-ui));padding:6px;border:1px solid #FDE68A;border-radius:6px;margin-top:4px;">`;
            res.skipped.forEach(s => {
              html += `<div style="padding:2px 0;">행 ${s.row}: <b>${escapeHtml(s.name)}</b> — ${escapeHtml(s.reason)}</div>`;
            });
            html += `</div></details>`;
          }
          if (res.errors && res.errors.length) {
            html += `<details open style="margin-bottom:6px;"><summary style="cursor:pointer;font-weight:600;color:#991B1B;font-size:calc(12.5px + var(--fs-add-ui));">❌ 오류 ${res.errors.length}건 (수정 후 재업로드 필요)</summary>`;
            html += `<div style="max-height:160px;overflow-y:auto;font-size:calc(11.5px + var(--fs-add-ui));padding:6px;border:1px solid #FCA5A5;border-radius:6px;margin-top:4px;">`;
            res.errors.forEach(e => {
              html += `<div style="padding:2px 0;">행 ${e.row}: <b>${escapeHtml(e.name)}</b> — ${escapeHtml(e.error)}</div>`;
            });
            html += `</div></details>`;
          }
          if (resultBox) resultBox.innerHTML = html;
          await refreshUserList();
        } catch (e) {
          if (resultBox) resultBox.innerHTML = `<div style="padding:12px;color:#dc2626;">❌ 네트워크 오류: ${escapeHtml(String(e))}</div>`;
        } finally {
          upBtn.disabled = false;
          upBtn.textContent = prevText;
        }
      });
    }
    if (els.nuSaveBtn) {
      els.nuSaveBtn.addEventListener("click", async () => {
        // 현재 활성 서브탭 확인 (kor / vn)
        const activeSubTab = document.querySelector(".nu-sub-tab.active");
        const mode = activeSubTab?.dataset?.nuSub === "vn" ? "vn" : "kor";

        let payload = null;
        let pwHintLabel = "";
        if (mode === "kor") {
          const employee_no = els.nuKEmployeeNo?.value?.trim() || "";
          const display_name = els.nuKDisplayName?.value?.trim() || "";
          const phone = els.nuKPhone?.value?.trim() || "";
          const email = (els.nuKEmail?.value?.trim() || "").toLowerCase();
          const title = els.nuKTitle?.value || "";
          const department = els.nuKDept?.value || "";
          const display_name_en = els.nuKDisplayNameEn?.value?.trim() || "";
          const role = els.nuKRoleCeo?.checked ? "ceo" : "staff";
          if (!employee_no) { alert(window.KNK_t("alert.employeeNoRequired","사번 필수 (사번이 로그인 ID 입니다)")); return; }
          if (!display_name) { alert(window.KNK_t("alert.nameRequired")); return; }
          if (!phone) { alert(window.KNK_t("alert.phoneRequired")); return; }
          const digits = phone.replace(/\D/g, "");
          if (digits.length < 9) { alert(window.KNK_t("alert.phoneShort")); return; }
          if (!department) { alert(window.KNK_t("alert.deptRequired","부서를 선택해 주세요.")); return; }
          payload = { mode: "kor", employee_no, display_name, phone, email, title, department, display_name_en, role };
          pwHintLabel = "휴대폰 번호 숫자";
        } else {
          const employee_no = els.nuVEmployeeNo?.value?.trim() || "";
          const display_name = els.nuVDisplayName?.value?.trim() || "";
          const display_name_vn = els.nuVDisplayNameVn?.value?.trim() || "";
          const display_name_en = els.nuVDisplayNameEn?.value?.trim() || "";
          const phone = els.nuVPhone?.value?.trim() || "";
          const email = (els.nuVEmail?.value?.trim() || "").toLowerCase();
          const title = els.nuVTitle?.value || "";
          const department = els.nuVDept?.value || "";
          const role = els.nuVRoleCeo?.checked ? "ceo" : "staff";
          if (!employee_no) { alert(window.KNK_t("alert.employeeNoRequiredVn","사번 필수 ('VN'은 자동 부착됩니다)")); return; }
          if (!display_name) { alert(window.KNK_t("alert.nameKrRequired","이름 (한국식 발음) 필수")); return; }
          if (!display_name_en) { alert(window.KNK_t("alert.nameEnRequired","이름 (영문) 필수")); return; }
          if (!department) { alert(window.KNK_t("alert.deptRequired","부서를 선택해 주세요.")); return; }
          payload = { mode: "vn", employee_no, display_name, display_name_vn, display_name_en,
                      phone, email, title, department, role };
          pwHintLabel = "베트남 공통";
        }

        els.nuSaveBtn.disabled = true;
        const prevText = els.nuSaveBtn.textContent;
        els.nuSaveBtn.textContent = "등록 중…";
        try {
          const res = await fetch(`${BASE}/api/users`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          }).then(r => r.json());
          if (res.error) {
            if (els.nuResult) els.nuResult.innerHTML = `<span style="color:#dc2626;">❌ ${escapeHtml(res.error)}</span>`;
            return;
          }
          if (els.nuResult) {
            els.nuResult.innerHTML = `
              <div style="background:#ECFDF5;border:1px solid #10B981;border-radius:8px;padding:10px;color:#065F46;">
                ✅ 등록 완료 — <b>${escapeHtml(payload.display_name)}</b><br>
                <div style="margin-top:6px;font-size:calc(11.5px + var(--fs-add-ui));line-height:1.6;">
                  • <b>로그인 ID (= 사번)</b>: <code>${escapeHtml(res.username || "")}</code><br>
                  • <b>초기 비밀번호</b>: <code>${escapeHtml(res.initial_password || "")}</code> (${escapeHtml(pwHintLabel)})<br>
                  • 본인에게 위 정보를 전달해 주세요. 첫 로그인 시 비밀번호 변경이 강제됩니다.
                </div>
              </div>`;
          }
          await refreshUserList();
        } catch (e) {
          if (els.nuResult) els.nuResult.innerHTML = `<span style="color:#dc2626;">❌ 네트워크 오류: ${escapeHtml(String(e))}</span>`;
        } finally {
          els.nuSaveBtn.disabled = false;
          els.nuSaveBtn.textContent = prevText;
        }
      });
    }
  }

  // ─── 🔒 마스킹 미지원 브라우저 안전망 ───
  // .knk-masked 는 type=text + CSS(-webkit-text-security) 로 ●●● 처리.
  // 만약 브라우저가 이 CSS 를 지원 안 하면 비번이 평문 노출되므로, 진짜 password 칸으로 환원.
  // (대다수 Chromium/WebKit 은 지원 → 이 분기는 거의 안 탐. 환원 시 검색칸 자동완성 차단 효과만 일부 손실)
  try {
    var _maskOK = !!(window.CSS && CSS.supports &&
      (CSS.supports("-webkit-text-security", "disc") || CSS.supports("text-security", "disc")));
    if (!_maskOK) {
      document.querySelectorAll("input.knk-masked").forEach(function (el) {
        el.type = "password";
        el.classList.remove("knk-masked");
        el.dataset.knkFallback = "1";
      });
    }
  } catch (e) { /* ignore */ }

  // ─── 🔐 비밀번호 보기/숨기기 토글 (👁) — 전역 1회 wire ───
  document.querySelectorAll(".pw-toggle").forEach((btn) => {
    if (btn._pwWired) return;
    btn._pwWired = true;
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-pw-toggle-for");
      const inp = document.getElementById(id);
      if (!inp) return;
      var revealed;
      if (inp.dataset.knkFallback === "1") {
        // 미지원 브라우저 안전망: 진짜 password 칸 — 기존 type 전환 방식
        revealed = inp.type === "text";
        inp.type = revealed ? "password" : "text";
      } else {
        // 기본: type=text 유지 + 마스킹 클래스 토글 (페이지에 password 칸을 안 남겨 검색칸 자동완성 차단)
        revealed = !inp.classList.contains("knk-masked");   // 현재 평문 노출 중?
        inp.classList.toggle("knk-masked", revealed);       // 노출 중이면 가림, 아니면 보임
      }
      btn.textContent = revealed ? "👁" : "🙈";
      btn.classList.toggle("shown", !revealed);
      btn.setAttribute("aria-label", revealed ? "비밀번호 보기" : "비밀번호 숨기기");
    });
  });

  // ─── 🔐 비밀번호 변경 다이얼로그 (수동 호출용) ───
  function openChangePasswordDialog() {
    if (!els.changePwDialog) return;
    // 폼 초기화
    if (els.cpwCurrent) els.cpwCurrent.value = "";
    if (els.cpwNew) els.cpwNew.value = "";
    if (els.cpwNew2) els.cpwNew2.value = "";
    // 👁 토글이 평문 노출 상태였을 수도 — 닫고 다시 열 때 안전하게 마스킹 상태로 환원
    ["cpwCurrent", "cpwNew", "cpwNew2"].forEach((id) => {
      const inp = document.getElementById(id);
      if (inp) {
        if (inp.dataset.knkFallback === "1") { inp.type = "password"; }  // 미지원 브라우저 안전망
        else { inp.classList.add("knk-masked"); }
      }
      const tog = document.querySelector(`.pw-toggle[data-pw-toggle-for="${id}"]`);
      if (tog) { tog.textContent = "👁"; tog.classList.remove("shown"); tog.setAttribute("aria-label", "비밀번호 보기"); }
    });
    if (els.cpwError) { els.cpwError.textContent = ""; els.cpwError.style.display = "none"; }
    // 강제 모달이 아닌 일반 모드 — 헤더 안내 메시지 + 닫기 버튼 보이게
    const head = els.changePwDialog.querySelector(".dialog-hint");
    if (head) head.textContent = "현재 비밀번호와 새 비밀번호를 입력해 주세요. (6자 이상)";
    // 닫기 버튼이 강제 모드에선 없으므로 동적으로 추가 (있으면 패스)
    const actions = els.changePwDialog.querySelector(".dialog-actions");
    if (actions && !actions.querySelector("[data-close]")) {
      const cancelBtn = document.createElement("button");
      cancelBtn.type = "button";
      cancelBtn.setAttribute("data-close", "");
      cancelBtn.textContent = "취소";
      actions.insertBefore(cancelBtn, actions.firstChild);
      cancelBtn.addEventListener("click", () => { try { els.changePwDialog.close(); } catch (_) {} });
    }
    try { els.changePwDialog.showModal(); } catch (_) {}
  }

  // ─── 🔐 비밀번호 변경 강제 다이얼로그 (첫 로그인 시) ───
  async function checkMustChangePassword() {
    try {
      const res = await fetch(`${BASE}/api/me/must_change_password`).then(r => r.json());
      if (res.must_change) {
        // 강제: ESC·바깥 클릭으로 닫히지 않게 따로 처리
        try { els.changePwDialog.showModal(); } catch (_) {}
        // 백드롭 클릭·ESC 막기
        els.changePwDialog.addEventListener("click", (e) => {
          if (e.target === els.changePwDialog) e.preventDefault();
        });
      }
    } catch (e) { /* noop */ }
  }
  if (els.cpwSaveBtn) {
    els.cpwSaveBtn.addEventListener("click", async () => {
      const cur = els.cpwCurrent?.value || "";
      const newPw = els.cpwNew?.value || "";
      const newPw2 = els.cpwNew2?.value || "";
      const showErr = (msg) => {
        if (!els.cpwError) return;
        els.cpwError.textContent = "❌ " + msg;
        els.cpwError.style.display = "";
      };
      if (els.cpwError) els.cpwError.style.display = "none";
      if (!cur) return showErr("현재 비밀번호(휴대폰 번호)를 입력하세요.");
      if (newPw.length < 6) return showErr("새 비밀번호는 6자 이상이어야 합니다.");
      if (newPw !== newPw2) return showErr("새 비밀번호 확인이 일치하지 않습니다.");
      els.cpwSaveBtn.disabled = true;
      els.cpwSaveBtn.textContent = "변경 중…";
      try {
        const res = await fetch(`${BASE}/api/me/password`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ current_password: cur, new_password: newPw }),
        }).then(r => r.json());
        if (res.error) { showErr(res.error); return; }
        // 성공 — 다이얼로그 닫고 메신저 사용 시작
        try { els.changePwDialog.close(); } catch (_) {}
        alert(window.KNK_t("alert.pwChanged"));
      } catch (e) {
        showErr("네트워크 오류");
      } finally {
        els.cpwSaveBtn.disabled = false;
        els.cpwSaveBtn.textContent = "🔐 비밀번호 저장 후 시작";
      }
    });
  }
  // 페이지 진입 직후 한 번 체크
  setTimeout(checkMustChangePassword, 800);

  // socket: 사용자 정보 변경 broadcast 수신 → 목록 갱신
  function _wireUserInfoSocket() {
    if (!window.socket) return setTimeout(_wireUserInfoSocket, 300);
    socket.on("user_info_changed", (u) => {
      const idx = _usersCache.findIndex(x => x.id === u.id);
      if (idx >= 0) _usersCache[idx] = u;
      else _usersCache.push(u);
      if (_sidebarTab === "users") renderUserList();
    });
    socket.on("user_deleted", (e) => {
      const idx = _usersCache.findIndex(x => x.id === e.user_id);
      if (idx >= 0) _usersCache.splice(idx, 1);
      if (_sidebarTab === "users") renderUserList();
    });
  }
  setTimeout(_wireUserInfoSocket, 800);
  // 최초 로드 + 5분 주기 갱신
  setTimeout(refreshUserList, 1200);
  setInterval(refreshUserList, 5 * 60 * 1000);

  // ============================================================
  // 📚 프로젝트 이력 (HAIST WORKS 연동 대비)
  //   - 하루 1회 자동 + 수동 즉시 갱신
  //   - 프로젝트 방에서만 노출
  // ============================================================
  let _phActiveRoom = null;

  async function openProjectHistory(roomId, roomName) {
    _phActiveRoom = roomId;
    if (els.phRoomName) els.phRoomName.textContent = `📍 ${roomName || ""}`;
    if (els.phList) els.phList.innerHTML = `<div style="text-align:center;color:var(--text-soft);padding:24px;">불러오는 중…</div>`;
    try { els.projectHistoryDialog.showModal(); } catch (_) {}
    await refreshProjectHistory();
  }

  async function refreshProjectHistory() {
    if (!_phActiveRoom || !els.phList) return;
    try {
      const list = await fetch(`${BASE}/api/rooms/${_phActiveRoom}/history`).then(r => r.json());
      if (!Array.isArray(list) || !list.length) {
        els.phList.innerHTML = `
          <div style="text-align:center;color:var(--text-soft);padding:36px 16px;font-size:calc(13.5px + var(--fs-add-ui));">
            아직 생성된 이력이 없습니다.<br>
            대화가 어느 정도 쌓이면 매일 자동으로 요약·정리되며,<br>
            <b>"✨ 지금 갱신"</b> 버튼으로 즉시 만들 수도 있습니다.
          </div>`;
        return;
      }
      els.phList.innerHTML = list.map(h => {
        const periodStart = h.period_start ? h.period_start.slice(5, 16).replace("T", " ") : "";
        const periodEnd = h.period_end ? h.period_end.slice(5, 16).replace("T", " ") : "";
        const isAuto = h.created_mode === "auto";
        const authorPill = isAuto
          ? `<span class="ph-pill ph-pill-auto">🤖 자동</span>`
          : `<span class="ph-pill ph-pill-manual">✋ ${escapeHtml(h.created_by_name || "수동")}</span>`;
        const costPill = (h.cost_usd && h.cost_usd > 0) ? `<span class="ph-pill ph-pill-cost">$${h.cost_usd.toFixed(4)}</span>` : "";
        const syncPill = h.synced_to_hw ? `<span class="ph-pill ph-pill-synced" title="HAIST WORKS 전송됨 ${escapeHtml(h.synced_at || '')}">📤 WORKS 전송됨</span>` : "";
        const atts = (h.attachments || []).map(a => `
          <a href="${escapeHtml(a.url)}" target="_blank" class="ph-att">
            <span class="ph-att-icon">${a.mime && a.mime.startsWith('image/') ? '🖼' : '📎'}</span>
            <span class="ph-att-info">
              <span class="ph-att-name">${escapeHtml(a.name || '')}</span>
              <span class="ph-att-meta">${escapeHtml(a.sender || '')}${a.sent_at ? ' · ' + a.sent_at.slice(5, 16).replace('T',' ') : ''}${a.size ? ' · ' + (Math.round(a.size/1024)+ 'KB') : ''}</span>
            </span>
          </a>`).join("");
        return `
          <div class="ph-card" data-hid="${h.id}">
            <div class="ph-card-head">
              <div class="ph-card-period">📅 ${periodStart} ~ ${periodEnd}</div>
              <div class="ph-card-pills">
                ${authorPill}
                <span class="ph-pill">💬 ${h.message_count}</span>
                ${h.attachment_count > 0 ? `<span class="ph-pill">📎 ${h.attachment_count}</span>` : ''}
                ${costPill}
                ${syncPill}
              </div>
            </div>
            <div class="ph-card-section-label">📝 요약</div>
            <div class="ph-card-body">${escapeHtml(h.summary_text || '').replace(/\n/g, '<br>')}</div>
            ${atts ? `<div class="ph-card-atts"><div class="ph-card-atts-title">📎 첨부 ${h.attachment_count}개</div>${atts}</div>` : ''}
            <div class="ph-card-actions">
              <button type="button" class="secondary-btn ph-copy-btn" data-hid="${h.id}">📋 이 항목만 복사</button>
            </div>
          </div>
        `;
      }).join("");
      els.phList.querySelectorAll(".ph-copy-btn").forEach(b => {
        b.addEventListener("click", () => {
          const hid = parseInt(b.dataset.hid, 10);
          const h = list.find(x => x.id === hid);
          if (!h) return;
          const text = _phHistoryToText(h);
          navigator.clipboard.writeText(text).then(() => {
            b.textContent = "✓ 복사됨";
            setTimeout(() => b.textContent = "📋 이 항목만 복사", 1500);
          });
        });
      });
      // 전체 복사 버튼
      if (els.phCopyAllBtn) {
        els.phCopyAllBtn.onclick = () => {
          const text = list.map(_phHistoryToText).join("\n\n" + "═".repeat(60) + "\n\n");
          navigator.clipboard.writeText(text).then(() => {
            els.phCopyAllBtn.textContent = "✓ 전체 복사됨";
            setTimeout(() => els.phCopyAllBtn.textContent = "📋 전체 복사", 1800);
          });
        };
      }
    } catch (e) {
      els.phList.innerHTML = `<div style="text-align:center;color:#DC2626;padding:24px;">❌ 이력 로드 실패: ${escapeHtml(String(e))}</div>`;
    }
  }

  function _phHistoryToText(h) {
    const lines = [];
    const ps = h.period_start ? h.period_start.slice(0, 16).replace("T", " ") : "";
    const pe = h.period_end ? h.period_end.slice(0, 16).replace("T", " ") : "";
    lines.push(`[프로젝트 이력] ${ps} ~ ${pe}`);
    lines.push(`(메시지 ${h.message_count}개, 첨부 ${h.attachment_count || 0}개)`);
    lines.push("");
    lines.push(h.summary_text || "");
    if (h.attachments && h.attachments.length) {
      lines.push("");
      lines.push("[첨부]");
      h.attachments.forEach(a => {
        lines.push(`- ${a.name || ""} (${a.sender || ""}) ${a.url || ""}`);
      });
    }
    return lines.join("\n");
  }

  // 지금 갱신 버튼
  if (els.phGenerateBtn) {
    els.phGenerateBtn.addEventListener("click", async () => {
      if (!_phActiveRoom) return;
      els.phGenerateBtn.disabled = true;
      const prevText = els.phGenerateBtn.textContent;
      els.phGenerateBtn.textContent = "🧠 Claude 가 요약하는 중…";
      try {
        const res = await fetch(`${BASE}/api/rooms/${_phActiveRoom}/history/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        }).then(r => r.json());
        if (res.no_new || res.too_few) {
          alert(`ℹ ${res.error}`);
        } else if (res.error) {
          alert(`❌ ${res.error}`);
        } else {
          await refreshProjectHistory();
        }
      } catch (e) {
        alert(window.KNK_t("alert.networkError"));
      } finally {
        els.phGenerateBtn.disabled = false;
        els.phGenerateBtn.textContent = prevText;
      }
    });
  }

  // 헤더 📚 버튼
  if (els.projectHistoryBtn) {
    els.projectHistoryBtn.addEventListener("click", () => {
      if (activeRoom) openProjectHistory(activeRoom.id, activeRoom.name);
    });
  }

  // ============================================================
  // 🟢 사용자 상태 + 📅 캘린더 자동 동기화
  // ============================================================
  // ============================================================
  // 🏢 KNK 부서 코드 (대표 지시 2026-05-20 갱신) — 본사 14 + 베트남법인 9
  //   value (DB 저장) = 부서명 그대로. 시각 표시:
  //     · 본사 부서: 'NN 부서명' (예: 01 기술영업팀) — DB는 부서명만, 표시에서 코드 prefix 추가
  //     · VN 법인 부서: '12-VNNN 부서명' (예: 12-VN01 기술팀) — DB 값에 코드 포함, 그대로 표시
  //       (대표 지시 2026-05-20: 베트남부서 DB값 = '12-VNNN 부서명' 통째로 / 한국법인 12 가 앞)
  //   정렬 키: DEPT_CODES 의 value 는 정렬 전용. 베트남은 'VN12-NN' 으로 두어 한국 14 다음에 옴.
  // ============================================================
  const DEPT_CODES = {
    // 임원 (1) — '총괄' 코드 00 (사용자 목록 정렬·그룹핑 전용. 대화/요청 표시는 deptShortLabel 이 숨김) — 대표 지시 2026-05-22
    "총괄": "00",
    // 본사 (14) — 대표 지시 2026-05-19 갱신:
    //   12번은 베트남법인 prefix 전용 → 한국 부서엔 12 없음
    //   설계팀(자동화)·설계팀(검사기) 는 둘 다 04 (서브부서)
    "기술영업팀":     "01",
    "검사기팀":       "02",
    "품질팀":         "03",
    "설계팀(자동화)": "04",
    "설계팀(검사기)": "04",
    "소프트웨어팀":   "05",
    "전장설계팀":     "06",
    "제조기술1팀":    "07",
    "제조기술2팀":    "08",
    "가공팀":         "09",
    "구매팀":         "10",
    "관리팀":         "11",
    "개발혁신팀":     "13",
    "라이프밸류팀":   "14",
    // 실제 부서명 변형(연구소 표기 포함) — 명단 엑셀 기준 보강 (대표 지시 2026-05-26)
    "검사기팀(연구소)":   "02",
    "설계팀(연구소)":     "04",
    "소프트웨어팀(연구소)": "05",
    "전장설계팀(연구소)": "06",
    "개발혁신팀(연구소)": "13",
    "라이프밸류팀(연구소)": "14",
    // 베트남법인 (9) — 표시·DB 키: '12-VNNN 부서명' / 정렬 키: 'VN12-NN' (한국 14 뒤에 자연 정렬)
    "12-VN01 기술팀":      "VN12-01",
    "12-VN02 조립팀":      "VN12-02",
    "12-VN03 전장팀":      "VN12-03",
    "12-VN04 설계팀":      "VN12-04",
    "12-VN05 소프트웨어팀": "VN12-05",
    "12-VN06 가공팀":      "VN12-06",
    "12-VN07 품질팀":      "VN12-07",
    "12-VN08 구매팀":      "VN12-08",
    "12-VN09 관리팀":      "VN12-09",
  };
  // 부서 정렬 우선 키 — 04 동률(자동화·검사기) 명시적 sub-order
  function deptSortKey(name) {
    if (!name) return "ZZ_unset";
    // 새 체계 (2026-05-26 대표 지시): "01_KOR/NN_부서" / "02_VN/NN_부서" — 그대로 자연정렬
    if (/^0[12]_(KOR|VN)\//.test(name)) return name;
    // 옛 체계 호환 — 새 체계 가상키로 매핑 (혼용 시에도 일관 정렬)
    if (name === "베트남법인") return "02_VN/00_총괄";
    let m = name.match(/^12-VN(\d{2})\s+(.+)$/);
    if (m) return "02_VN/" + m[1] + "_" + m[2];
    m = name.match(/^VN12-(\d{2})\s+(.+)$/);
    if (m) return "02_VN/" + m[1] + "_" + m[2];
    if (name === "설계팀(자동화)") return "01_KOR/04.1_설계팀(자동화)";
    if (name === "설계팀(검사기)") return "01_KOR/04.2_설계팀(검사기)";
    const code = DEPT_CODES[name];
    if (code && /^\d{2}$/.test(code)) return "01_KOR/" + code + "_" + name;
    return "ZZ_" + name;
  }
  function deptDisplayLabel(name) {
    if (!name) return "";
    // 베트남법인 — DB 값에 이미 코드 포함 → 그대로 표시
    // 새 포맷: '12-VNNN 부서명' / legacy: 'VN12-NN 부서명' (둘 다 그대로 표시)
    // 새 체계: "01_KOR/03_품질팀" → 부서 헤더는 "03_품질팀" (법인은 상위 헤더에서 표시) (대표 지시 2026-05-26)
    const mNew = name.match(/^0[12]_(KOR|VN)\/(.+)$/);
    if (mNew) return mNew[2];
    if (/^12-VN\d{2}\s+/.test(name)) return name;
    if (/^VN12-\d{2}\s+/.test(name)) return name;
    if (name === "베트남법인" || name === "12 베트남법인") return "00_총괄";   // 옛 데이터 → 02_VN/00_총괄로 통합 (대표 지시 2026-05-26)
    const code = DEPT_CODES[name];
    if (!code) return name;
    return `${code} ${name}`;
  }
  // 사용자 풀 라벨 — '이름 직급 · 부서' (대표 지시 2026-05-19)
  //   모든 다이얼로그·목록에서 동일하게 사용. cache fallback 으로 최신 title·dept 보장.
  function userFullLabel(u) {
    if (!u) return "";
    // users 캐시에서 최신 정보 (서버 응답이 이미 포함했어도 캐시가 더 최신일 수 있음)
    const cached = (Array.isArray(users) ? (users.find(x => x.id === (u.id || u.user_id)) || {}) : {});
    const displayName = u.display_name || cached.display_name || "";
    const title = cached.title || u.title || "";
    const department = cached.department || u.department || "";
    const parts = [escapeHtml(displayName)];
    if (title) parts.push(escapeHtml(title));
    let html = `<span class="u-name">${parts.join(" ")}</span>`;
    if (department) {
      const deptLabel = (typeof deptDisplayLabel === "function") ? deptDisplayLabel(department) : department;
      html += ` <span class="u-meta">· ${escapeHtml(deptLabel)}</span>`;
    }
    return html;
  }

  // 짧은 부서 라벨 — 1:1 방 제목용 (대표 지시 2026-05-20 갱신)
  //   한국: '관리팀' → '관리팀' (코드 prefix 없음)
  //   베트남: '12-VN09 관리팀' → 'VN관리팀' (VN 만 prefix 로)
  //   legacy 'VN12-NN 부서명' 도 지원 (혹시 남아있다면)
  function deptShortLabel(name) {
    if (!name) return "";
    // 새 체계: "01_KOR/NN_부서" → "부서", "02_VN/NN_부서" → "VN부서" (대표 지시 2026-05-26)
    //   KOR 총괄만 숨김(임원 컨텍스트). VN 총괄은 "VN총괄" 로 표시 유지.
    const mNew = name.match(/^(0[12])_(KOR|VN)\/\d{2}(?:\.\d)?_(.+)$/);
    if (mNew) {
      const corp = mNew[2];
      const dept = mNew[3];
      if (corp === "KOR" && dept === "총괄") return "";
      return corp === "VN" ? "VN" + dept : dept;
    }
    // 임원 '총괄'은 대화창·요청 등 대화 컨텍스트에서 숨김
    if (name === "총괄") return "";
    // 옛 베트남법인 데이터 — VN 총괄로 표시 (대표 지시 2026-05-26)
    if (name === "베트남법인" || name === "12 베트남법인") return "VN총괄";
    let m = name.match(/^\d{2}-VN\d{2}\s+(.+)$/);
    if (m) return "VN" + m[1];
    m = name.match(/^VN\d{2}-\d{2}\s+(.+)$/);
    if (m) return "VN" + m[1];
    return name;
  }

  // 대표 지시 2026-05-19: 온라인→회사 라벨 변경, 방해금지 제거,
  // 해외출장·국내출장·휴가 신규 추가.
  const STATUS_INFO = {
    online:   { color: "#10B981", label: "💻 컴퓨터",     desc: "PC 접속 중 (대화 가능)" },
    mobile:   { color: "#84CC16", label: "📱 휴대폰",     desc: "휴대폰만 접속 (알림 받음)" },
    away:     { color: "#9CA3AF", label: "🪑 자리비움",   desc: "잠시 자리에 없음" },
    busy:     { color: "#EF4444", label: "🔴 바쁨",       desc: "응답 어려움" },
    meeting:  { color: "#F59E0B", label: "🤝 회의 중",    desc: "회의·통화" },
    external: { color: "#8B5CF6", label: "🚗 외근",       desc: "사무실 외" },
    overseas: { color: "#3B82F6", label: "✈️ 해외출장",   desc: "해외 출장 중" },
    domestic: { color: "#06B6D4", label: "🚆 국내출장",   desc: "국내 출장 중" },
    vacation: { color: "#EC4899", label: "🌴 휴가",       desc: "휴가 중" },
    offwork:  { color: "#64748B", label: "🏠 퇴근",       desc: "퇴근 — 업무 종료 (다음에 컴퓨터로 접속하거나 회사망에 접속하면 자동 복귀)" },
    // 💼 업무 — UI 전용 키. 누르면 online 으로 저장돼 회의중·외근 등 수동상태를 풀고 '접속(자동)'으로 복귀 (대표 지시 2026-06-04)
    work:     { color: "#10B981", label: "💼 업무",       desc: "수동 상태 해제 — 접속(자동)으로 복귀" },
    offline:  { color: "#6B7280", label: "⚫ 오프라인",   desc: "로그아웃 — 알림 안 옴" },
  };
  // 상태 라벨/설명 — 현재 화면 언어(i18n)로 반환. 서버가 준 한국어 label 대신 상태 '키' 기반 번역. (대표 지시 2026-05-25 다국어)
  function _statusLabel(key) {
    if (window.KNK_t) { const v = window.KNK_t("status." + key); if (v && v !== "status." + key) return v; }
    return (STATUS_INFO[key] && STATUS_INFO[key].label) || key;
  }
  function _statusDesc(key) {
    if (window.KNK_t) { const v = window.KNK_t("status.desc." + key); if (v && v !== "status.desc." + key) return v; }
    return (STATUS_INFO[key] && STATUS_INFO[key].desc) || "";
  }
  // 사용자 이름·직급·부서 — 화면 언어가 한국어가 아니고 영문값이 있으면 영문으로 표시 (대표 지시 2026-05-25). 영문 없으면 한글 폴백.
  function _useEnNames() { return !!(window.KNK_curLang && window.KNK_curLang() !== "ko"); }
  function _curLang() { return (window.KNK_curLang && window.KNK_curLang()) || "ko"; }
  // 베트남 직원 이름 3종 (대표 지시 2026-05-26):
  //   display_name      = 한국식 발음 한글 (본사: 한글 그대로 / 베트남: 응우옌 반 아)
  //   display_name_vn   = 베트남어 원어 (베트남 직원만, 본사 직원은 NULL)
  //   display_name_en   = 영문
  // 표시 규칙 (언어 모드별):
  //   ko : 본사 → display_name / 베트남 → '{vn} ({한국식})' 병기
  //   vi : 베트남 직원 → vn / 그 외 → en (영문 우선) → ko (최종 fallback) (대표 지시 2026-05-27)
  //   en : 영문 있으면 → en
  //        영문 공백 + 베트남 → '{vn} ({한국식})' (대표 지시 2026-05-26: 영문 공백 fallback)
  //        영문 공백 + 본사  → display_name (한글 그대로)
  function _dispName(u) {
    if (!u) return "";
    const lang = _curLang();
    const vn = (u.display_name_vn || "").trim();
    const ko = (u.display_name || "");
    const en = (u.display_name_en || "").trim();
    if (lang === "ko") {
      return vn ? `${vn} (${ko})` : ko;
    }
    if (lang === "vi") {
      // 베트남 직원 → vn, 본사 직원 → 영문 (vn 없는 본사는 한국어 노출 X), en 도 없으면 ko
      if (vn) return vn;
      if (en) return en;
      return ko;
    }
    // en 또는 기타
    if (en) return en;
    // 영문 공백 fallback
    return vn ? `${vn} (${ko})` : ko;
  }
  // 한글 직급 → i18n 키 (대표 지시 2026-06-07: 베트남어 선택 시 공식 베트남 직급 표시)
  var _TITLE_I18N = {"대표이사":"title.ceo","전무이사":"title.smd","상무이사":"title.md","이사":"title.director","이사(팀장)":"title.directorTL","매니저":"title.manager","매니저(팀장)":"title.managerTL","프로":"title.pro","프로(팀장)":"title.proTL","사원":"title.staff","법인장":"title.corpHead","부장":"title.gm","차장":"title.dgm","과장":"title.mgr2","대리":"title.amgr","주임":"title.supervisor","반장":"title.lineSupervisor","조장":"title.sectionLeader"};
  function _dispTitle(u) {
    if (!u) return "";
    var ko = u.title || "";
    var k = _TITLE_I18N[ko];
    if (k && window.KNK_t) return window.KNK_t(k, ko);   // ko→한글 · vi→베트남 공식 · en→표준 영문
    return (_useEnNames() && u.title_en) ? u.title_en : ko;   // 매핑 외 직급은 기존 폴백
  }
  function _dispDept(u) {
    if (_useEnNames() && u && u.department_en) return u.department_en;
    return (u && u.department) ? deptDisplayLabel(u.department) : "";
  }
  let _userStatusMap = {};   // uid -> status info
  window._userStatusMap = _userStatusMap;
  let _selfAvatarMap = {};   // uid -> 개인 아바타 URL (직원 셀프). 없으면 인사카드(avatar_url) 폴백 (대표 지시 2026-06-03)
  window._selfAvatarMap = _selfAvatarMap;
  let _myCurrentStatus = "online";

  // 메시지 영역의 작성자 이름·직급·부서 라벨을 현재 언어로 즉시 갱신 (대표 지시 2026-05-27)
  // 메시지 다시 fetch 안 하고 DOM 안의 .author 노드만 in-place 업데이트 (가벼움·깜빡임 X)
  function _refreshMsgAuthors() {
    if (!els.messages) return;
    els.messages.querySelectorAll(".msg:not(.mine) .author[data-uid]").forEach(el => {
      const uid = parseInt(el.dataset.uid || "0", 10);
      if (!uid) return;
      const u = Array.isArray(users) ? users.find(x => x.id === uid) : null;
      if (!u) return;
      const _nm = _dispName(u);
      const _t = _dispTitle(u);
      const _d = u.department || "";
      const _enDept = (_useEnNames() && u.department_en) ? u.department_en : "";
      const _shortDept = _enDept || (_d ? (typeof deptShortLabel === "function" ? deptShortLabel(_d) : _d) : "");
      const _inline = [];
      if (_t) _inline.push(_t);
      if (_shortDept) _inline.push(_shortDept);
      const _metaInline = _inline.join(" ");
      // 텍스트 + author-meta span 재구성
      el.textContent = _nm;
      if (_metaInline) {
        const sp = document.createElement("span");
        sp.className = "author-meta";
        sp.textContent = _metaInline;
        el.appendChild(sp);
      }
      // hover 툴팁
      const _tipMeta = [];
      if (_t) _tipMeta.push(_t);
      if (_d) _tipMeta.push(_enDept || (typeof deptDisplayLabel === "function" ? deptDisplayLabel(_d) : _d));
      el.title = _tipMeta.length ? `${_nm} (${_tipMeta.join(" · ")})` : "";
    });
  }

  // 화면 언어 전환 시 동적 영역(사용자목록·방목록·내 상태배지·메시지 아바타·작성자 이름·헤더 제목) 즉시 재렌더 (대표 지시 2026-05-25/2026-05-27 다국어)
  document.addEventListener("knk-lang-changed", function () {
    try { if (typeof renderUserList === "function") renderUserList(); } catch (e) {}
    try { if (typeof renderRoomList === "function") renderRoomList(); } catch (e) {}
    try { const _me = _userStatusMap[meId]; if (_me) _renderMyStatusBadge(_me); } catch (e) {}
    try { if (typeof _refreshMsgAvatars === "function") _refreshMsgAvatars(); } catch (e) {}
    try { _refreshMsgAuthors(); } catch (e) {}     // 대화창 메시지 작성자 이름 즉시 반영
    try { _refreshUsersTabCount(); } catch (e) {}  // 사용자 탭 카운트 (필요 시 라벨)
    // 대화방 헤더 제목 — 1:1 방이면 상대 이름이 들어가므로 언어 따라 영문 fallback (대표 지시 2026-05-27)
    try { if (activeRoom) _setChatTitleFor(activeRoom); } catch (e) {}
  });

  async function refreshAllUserStatuses() {
    try {
      const list = await fetch(`${BASE}/api/users/statuses`).then(r => r.json());
      list.forEach(u => { _userStatusMap[u.user_id] = u; if ("self_avatar" in u) _selfAvatarMap[u.user_id] = u.self_avatar || null; });
      window._userStatusMap = _userStatusMap;
      window._selfAvatarMap = _selfAvatarMap;
      try { _refreshMyHeaderAvatar(); } catch (e) {}
      // 내 상태 표시 갱신
      const me = _userStatusMap[meId];
      if (me) {
        _myCurrentStatus = me.status;
        _renderMyStatusBadge(me);
        _applyDndIfNeeded(me.status);
      }
      // 메시지 발신자 아바타 — 상태 이모지로 갱신 (대표 지시 2026-05-22)
      _refreshMsgAvatars();
      try { _refreshPickerAvatars(); } catch (e4) { /* noop */ }
      // 방 목록(1:1 상대 상태) 갱신
      try { if (typeof renderRoomList === "function") renderRoomList(); } catch (e2) { /* noop */ }
    } catch (e) { /* noop */ }
  }

  // 열려있는 대화창의 발신자 아바타를 현재 상태 이모지로 즉시 교체 (대표 지시 2026-05-22)
  function _refreshMsgAvatars() {
    els.messages?.querySelectorAll(".msg:not(.mine) .avatar").forEach(av => {
      const li = av.closest(".msg");
      if (!li) return;
      const uid = parseInt(li.dataset.uid, 10);
      if (!uid) return;
      const u = (Array.isArray(users) ? users.find(x => x.id === uid) : null) || { id: uid };
      av.innerHTML = _avatarBody(u);   // 개인 아바타>인사카드>첫글자 (대표 지시 2026-06-03)
    });
  }

  // 열려있는 참여자 선택(picker) 아바타도 현재 상태로 갱신 — picker 는 열 때 1회만 렌더돼
  // 상태가 바뀌어도 옛 아바타가 남던 문제 해결(사이드바와 불일치). (대표 지시 2026-05-24)
  function _refreshPickerAvatars() {
    document.querySelectorAll('label[data-search]').forEach(lab => {
      if (lab.offsetParent === null) return;   // 닫혀있는(숨김) picker 는 스킵
      const cb = lab.querySelector('input[type="checkbox"]');
      const av = lab.querySelector('.avatar');
      if (!cb || !av) return;
      const uid = parseInt(cb.value, 10);
      if (!uid) return;
      const u = (Array.isArray(_usersCache) ? _usersCache.find(x => x.id === uid) : null)
             || (Array.isArray(users) ? users.find(x => x.id === uid) : null)
             || { id: uid };
      av.innerHTML = _avatarBody(u);
    });
  }

  function _renderMyStatusBadge(s) {
    if (els.myStatusDot) {
      els.myStatusDot.className = "status-dot status-" + s.status;
      els.myStatusDot.style.background = _dispStatusColor(s.status);
    }
    if (els.myStatusText) {
      const customSuffix = s.custom_text ? ` · ${s.custom_text}` : "";
      // (회사) 꼬리표 — 상세표시 ON + 회사망 + 접속일 때만 (대표 지시 2026-05-25 / 2026-06-01 토글)
      const officeSuffix = _dispOfficeSuffix(s);
      els.myStatusText.textContent = _dispStatusLabel(s.status) + officeSuffix + customSuffix;
    }
    // 헤더 좌상단 본인 아바타 — 상태색이 아니라 신원(개인 아바타>인사카드>첫글자)으로 (대표 지시 2026-06-03)
    try { _refreshMyHeaderAvatar(); } catch (e) {}
  }

  function _applyDndIfNeeded(status) {
    // DND 시 알림 시스템 강제 차단 — notifySettings 와 별개로 작동
    window.KNK_DND_ACTIVE = (status === "dnd");
  }

  function openStatusDialog() {
    if (!els.statusDialog || !els.statusOptionsArea) return;
    // 상태 옵션 카드 렌더 — 컴퓨터·휴대폰은 '쓰는 기기'로 자동 표시되므로 수동 메뉴에서 제외.
    //  대신 'online' 키를 '🔄 자동'으로 보여줘 회의중·휴가 등 수동상태를 풀고 자동으로 복귀하는 용도.
    //  나머지 6종(회의중·외근·해외출장·국내출장·휴가·퇴근)은 수동 우선순위.
    //  '바쁨' 은 의미 모호하고 다른 상태와 중복되어 제거 (대표 지시 2026-05-28).
    // 컴팩트 1줄 카드 — 설명은 hover 툴팁. 2열 그리드라 한 화면에 다 보임.
    // '💼 업무'(work) 카드를 맨 끝에 추가 — 누르면 online 저장 → 접속(자동) 복귀 = 수동상태 해제 (대표 지시 2026-06-04)
    const _pickerOrder = ["online", "meeting", "external", "overseas", "domestic", "vacation", "offwork", "work"];
    const _WORK_LABEL = { ko: "💼 업무", vi: "💼 Làm việc", en: "💼 Working", zh: "💼 工作中" };
    const _WORK_DESC  = { ko: "수동 상태 해제 — 접속(자동)으로 복귀", vi: "Bỏ trạng thái thủ công — về Trực tuyến (tự động)", en: "Clear manual status — back to online (auto)", zh: "解除手动状态 — 恢复在线(自动)" };
    const _pickerLabel = (k, v) => k === "online" ? _statusLabel("clockIn") : (k === "work" ? (_WORK_LABEL[_curLang()] || _WORK_LABEL.ko) : _statusLabel(k));
    const _pickerDesc  = (k, v) => k === "online" ? _statusDesc("clockIn") : (k === "work" ? (_WORK_DESC[_curLang()] || _WORK_DESC.ko) : _statusDesc(k));
    // 자동(컴퓨터/휴대폰=접속) 상태면 '업무' 카드를 강조 (출근 카드는 비활성이라 강조 대상 아님)
    const _autoMode = (_myCurrentStatus === "online" || _myCurrentStatus === "mobile");
    const _highlightKey = _autoMode ? "work" : _myCurrentStatus;
    els.statusOptionsArea.innerHTML = _pickerOrder.filter(k => STATUS_INFO[k]).map(k => {
      const v = STATUS_INFO[k];
      const _dis = (k === "online");   // '🟢 출근(자동)' 카드 — 일단 비활성화: 클릭X + 흑백 (없애진 않음) (대표 지시 2026-06-03)
      const _hl = (!_dis && k === _highlightKey);
      // 카드 안에 기한 입력칸 — 회의·외근=시간 / 출장·휴가=날짜. 카드 선택 시에만 노출(아래 _initCardUntil/click) (대표 지시 2026-06-07 "카드 안에서 바로 입력")
      const _isTimeK = (k === "meeting" || k === "external");
      const _isDateK = (k === "overseas" || k === "domestic" || k === "vacation");
      const _untilHtml = (_isTimeK || _isDateK)
        ? `<input type="${_isTimeK ? 'time' : 'date'}" class="sc-until-input" data-untilkind="${_isTimeK ? 'time' : 'date'}" style="display:none;flex:1 1 100%;margin-top:6px;padding:5px 6px;border:1px solid var(--border);border-radius:6px;font-size:calc(12px + var(--fs-add-ui));background:var(--bg);color:var(--text);box-sizing:border-box;min-width:0;">`
        : "";
      return `
      <div role="button" tabindex="${_dis ? '-1' : '0'}" class="status-option-card${_dis ? ' is-disabled' : ''}" data-status="${k}" aria-disabled="${_dis ? 'true' : 'false'}" title="${_dis ? '일시 비활성화' : escapeHtml(_pickerDesc(k, v))}" style="display:flex;flex-wrap:wrap;align-items:center;gap:0 6px;text-align:left;padding:8px 10px;border:2px solid ${_hl ? v.color : 'var(--border)'};background:${_hl ? 'var(--bg)' : 'var(--surface)'};color:var(--text);border-radius:8px;cursor:${_dis ? 'not-allowed' : 'pointer'};min-width:0;${_dis ? 'filter:grayscale(1);opacity:0.5;' : ''}">
        <span style="font-weight:600;font-size:calc(13px + var(--fs-add-ui));color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${_pickerLabel(k, v)}</span>${_untilHtml}
      </div>`;
    }).join("");
    // 저장 로직 헬퍼 (대표 지시 2026-05-19) — 더블클릭·저장 버튼 양쪽에서 호출
    async function _saveStatus(statusKey, opts = {}) {
      // '업무'(work)는 UI 전용 키 — 백엔드엔 online 으로 저장(자동표시 규칙이 접속/컴퓨터/휴대폰으로 환산) (대표 지시 2026-06-04)
      const _backendStatus = (statusKey === "work") ? "online" : statusKey;
      const body = {
        status: _backendStatus,
        custom_text: els.statusCustomText?.value?.trim() || null,
        // 회의중·외근=오늘 시각 / 해외·국내출장·휴가=종료일 → until_at(ISO UTC). 그 외 상태는 null. (대표 지시 2026-06-06)
        until_at: _collectStatusUntil(statusKey),
      };
      const res = await fetch(`${BASE}/api/me/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).then(r => r.json()).catch(() => ({ error: "네트워크 오류" }));
      if (res.error) {
        // 백엔드 raw 오류 대신 사용자 친화 메시지
        const msg = res.error.includes("status") ? "상태 선택이 올바르지 않습니다. 카드에서 상태를 선택한 뒤 저장해 주세요." : res.error;
        alert(msg); return false;
      }
      _myCurrentStatus = res.current.status;
      _userStatusMap[meId] = res.current;
      window._userStatusMap = _userStatusMap;
      _renderMyStatusBadge(res.current);
      _applyDndIfNeeded(res.current.status);
      // ★ 사이드바 사용자 목록·메시지 아바타 색점 즉시 갱신 (대표 지시 2026-05-19)
      try { if (typeof renderUserList === "function") renderUserList(); } catch(e) {}
      if (opts.closeDialog !== false) {
        try { els.statusDialog.close(); } catch(e) {}
      }
      return true;
    }
    // 카드 단일 클릭 → 현재 선택 변경 (강조만, 저장 X — 사용자가 custom_text·until 입력할 시간)
    // mobile·offline 은 자동 판정 상태라 수동 저장 불가 → "online" 으로 보정
    // online 은 비활성(흑백) 카드라 선택 대상에서 제외 — 대신 'work'(💼 업무) 가 접속 복귀를 담당 (대표 지시 2026-06-04)
    const _SELECTABLE_STATUSES = ["meeting","external","overseas","domestic","vacation","offwork","work"];   // '바쁨' 제거 (대표 지시 2026-05-28)
    let pickedStatus = (_myCurrentStatus === "online" || _myCurrentStatus === "mobile") ? "work"
                     : (_SELECTABLE_STATUSES.includes(_myCurrentStatus) ? _myCurrentStatus : "work");
    els.statusOptionsArea.querySelectorAll(".status-option-card").forEach(b => {
      if (b.classList.contains("is-disabled")) return;   // 출근(자동) 카드 — 선택·저장 불가
      b.addEventListener("click", () => {
        pickedStatus = b.dataset.status;
        els.statusOptionsArea.querySelectorAll(".status-option-card").forEach(c => {
          const k = c.dataset.status;
          const sel = (k === pickedStatus);
          // 처음 그릴 때와 동일한 테마 변수 — 하드코딩 흰색 금지(다크 테마) (대표 지시 2026-06-06)
          c.style.borderColor = sel ? STATUS_INFO[k].color : "var(--border)";
          c.style.background = sel ? "var(--bg)" : "var(--surface)";
          const ci = c.querySelector(".sc-until-input");
          if (ci) ci.style.display = sel ? "block" : "none";   // 선택된 카드 안 입력칸만 노출 (대표 지시 2026-06-07)
        });
        const inp = b.querySelector(".sc-until-input");   // 클릭 즉시 입력칸 포커스 → 바로 입력
        if (inp) { try { inp.focus(); } catch (e) {} }
      });
      // ★ 더블클릭 → 즉시 저장 + 다이얼로그 닫기 (대표 지시 2026-05-19)
      b.addEventListener("dblclick", async (ev) => {
        ev.preventDefault();
        const k = b.dataset.status;
        // 시각 피드백 — 클릭 즉시 깜빡
        b.style.transform = "scale(0.96)";
        setTimeout(() => { b.style.transform = ""; }, 120);
        await _saveStatus(k, { closeDialog: true });
      });
      // 카드 안 입력칸 상호작용은 카드 선택·저장(더블클릭)으로 전파 안 되게 (대표 지시 2026-06-07)
      const _inp = b.querySelector(".sc-until-input");
      if (_inp) { ["click", "dblclick", "mousedown"].forEach(ev => _inp.addEventListener(ev, e => e.stopPropagation())); }
      // 터치 디바이스용 — title 에 안내 추가
      b.setAttribute("title", `더블클릭(또는 더블탭): 즉시 적용`);
    });
    // 현재 사용자정의 문구·기한 채우기
    const cur = _userStatusMap[meId] || {};
    if (els.statusCustomText) els.statusCustomText.value = cur.custom_text || "";
    // 카드 안 기한 입력칸 초기화 — 각 카드에 기본값(시간 +1h / 날짜 오늘), 현재 상태와 같으면 기존값. 선택된 카드만 노출. (대표 지시 2026-06-07)
    (function _initCardUntil() {
      let cd = null;
      if (cur.until_at) { try { cd = new Date(cur.until_at); if (isNaN(cd.getTime())) cd = null; } catch (e) { cd = null; } }
      const n1 = new Date(); n1.setHours(n1.getHours() + 1, 0, 0, 0);   // 기본 시간 = +1시간
      const todayY = _ymdLocal(new Date());
      els.statusOptionsArea.querySelectorAll(".sc-until-input").forEach(inp => {
        const card = inp.closest(".status-option-card");
        const k = card && card.dataset.status;
        if (inp.getAttribute("data-untilkind") === "time") {
          inp.value = (cd && _STATUS_UNTIL_TIME[cur.status] && k === cur.status) ? _hmLocal(cd) : _hmLocal(n1);
        } else {
          inp.setAttribute("min", todayY);
          inp.value = (cd && _STATUS_UNTIL_DATE[cur.status] && k === cur.status) ? _ymdLocal(cd) : todayY;
        }
        inp.style.display = (k === pickedStatus) ? "block" : "none";
      });
    })();
    // 저장 버튼
    if (els.statusSaveBtn) {
      els.statusSaveBtn.onclick = () => _saveStatus(pickedStatus, { closeDialog: true });
    }
    // 캘린더 일정 로드·렌더
    _refreshCalendarEvents();
    // 캘린더 추가 버튼
    if (els.calAddBtn) {
      els.calAddBtn.onclick = async () => {
        const title = els.calTitle?.value?.trim();
        const start = els.calStart?.value;
        const end = els.calEnd?.value;
        const kind = els.calKind?.value || "meeting";
        if (!title || !start || !end) { alert(window.KNK_t("alert.calFieldsRequired")); return; }
        // datetime-local(로컬/KST 벽시계) → 정확한 UTC. '+:00.000Z' 단순 부착은 9시간 오차 (대표 지시 2026-06-06 시간대 일관성)
        const startISO = new Date(start).toISOString();
        const endISO = new Date(end).toISOString();
        const res = await fetch(`${BASE}/api/me/calendar`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, start_at: startISO, end_at: endISO, kind }),
        }).then(r => r.json());
        if (res.error) { alert(res.error); return; }
        els.calTitle.value = ""; els.calStart.value = ""; els.calEnd.value = "";
        _refreshCalendarEvents();
      };
    }
    try { els.statusDialog.showModal(); } catch (_) {}
  }

  async function _refreshCalendarEvents() {
    if (!els.calEventList) return;
    try {
      const list = await fetch(`${BASE}/api/me/calendar`).then(r => r.json());
      if (!list.length) {
        els.calEventList.innerHTML = `<div style="font-size:calc(12px + var(--fs-add-ui));color:var(--text-soft);padding:8px;text-align:center;">예약된 일정 없음</div>`;
        return;
      }
      els.calEventList.innerHTML = list.map(e => {
        const startShort = e.start_at?.slice(5, 16).replace("T", " ");
        const endShort = e.end_at?.slice(5, 16).replace("T", " ");
        const stateIcon = e.applied === 2 ? "✅" : e.applied === 1 ? "🔄" : "⏰";
        const kindIcon = e.kind === "external" ? "🚗" : e.kind === "busy" ? "🔴" : "🤝";
        return `
          <div class="cal-event-row" style="display:flex;align-items:center;gap:8px;padding:6px 8px;border-bottom:1px solid #F3F4F6;font-size:calc(12px + var(--fs-add-ui));">
            <span>${stateIcon}</span><span>${kindIcon}</span>
            <span style="flex:1;font-weight:600;">${escapeHtml(e.title)}</span>
            <span style="color:var(--text-soft);">${startShort} ~ ${endShort}</span>
            <button type="button" class="rs-act-btn rs-danger" data-cal-del="${e.id}" style="padding:2px 6px;">🗑</button>
          </div>
        `;
      }).join("");
      els.calEventList.querySelectorAll("[data-cal-del]").forEach(b => {
        b.addEventListener("click", async () => {
          if (!confirm(window.KNK_t("confirm.deleteSchedule"))) return;
          await fetch(`${BASE}/api/me/calendar/${b.dataset.calDel}`, { method: "DELETE" });
          _refreshCalendarEvents();
        });
      });
    } catch (e) { /* noop */ }
  }

  // 사용자 정보 영역 클릭 → 상태 다이얼로그
  if (els.meInfoArea) {
    els.meInfoArea.addEventListener("click", openStatusDialog);
  }

  // ===== 글씨 크기 조절 (앱 전체 · 이 기기에 저장) — 대표 지시 2026-05-20, 5단계 2026-05-21 =====
  // 더작게(0)=+0 / 작게(1)=+1 / 표준(2)=+2 / 크게(3)=+4 / 더크게(4)=+6. body 클래스로 CSS 변수(--fs-add) 조정.
  function applyFontScale(n) {
    n = parseInt(n, 10); if (isNaN(n) || n < 0 || n > 5) n = 0;
    document.body.classList.remove("fs-1", "fs-2", "fs-3", "fs-4", "fs-5");
    if (n >= 1 && n <= 5) document.body.classList.add("fs-" + n);
    try { localStorage.setItem("knk_font_scale", String(n)); } catch (e) {}
    document.querySelectorAll("#fontSizeOptions .fs-opt").forEach(function (b) {
      b.classList.toggle("active", parseInt(b.dataset.fs, 10) === n);
    });
  }
  (function initFontScale() {
    var saved = 0;
    try { saved = parseInt(localStorage.getItem("knk_font_scale") || "0", 10) || 0; } catch (e) {}
    applyFontScale(saved);
    document.querySelectorAll("#fontSizeOptions .fs-opt").forEach(function (b) {
      b.addEventListener("click", function () { applyFontScale(b.dataset.fs); });
    });
  })();

  // ===== 대화창 접기/펼치기 (데스크탑) — 대표 지시 2026-06-02 =====
  //  · 접힘 = 오른쪽 대화방 숨김 + 창(window)을 방 목록 폭으로 줄여 오른쪽 빈 영역 자체를 제거
  //  · 펼침 = 원래 창 너비 복원 + 대화방 다시 표시. 방을 열면 자동 펼침(openRoom).
  //  · 창 크기 조절(resizeTo)은 설치형 단독 창(PWA)에서만 동작 — 일반 브라우저 탭은 막혀서 무시됨.
  //  · 새로고침 시엔 펼친 상태로 시작(창 크기 자동변경 혼란 방지). 휴대폰·단독창(solo)은 무관.
  var _winExpandedW = 0;   // 펼침 상태의 창 바깥 너비(복원용)
  var _collapseScroll = null;   // 접기 직전 대화 스크롤 위치 { roomId, top } — 펼칠 때 그대로 복원
  function _applyCollapsedUI(on) {
    app.classList.toggle("chat-collapsed", on);
    // 대화창 인라인 숨김(확실하게) — CSS 규칙이 어딘가에서 덮여도 안전(접으면 none, 펼치면 '' 로 되돌림). (대표 지시 2026-06-02)
    try { if (els.chatPane) els.chatPane.style.display = on ? "none" : ""; } catch (e) {}
    var btn = document.getElementById("chatCollapseBtn");
    if (btn) {
      btn.textContent = on ? "❯" : "❮";
      btn.title = on ? "펼치기 — 대화방 다시 보기" : "접기 — 대화방 숨기고 방 목록 넓게 보기";
      btn.classList.toggle("is-collapsed", on);
    }
  }
  function _resizeWindowForCollapse(on, sidebarW) {
    try {
      if (on) {
        // .chat-app.chat-collapsed { min-width:0 } 로 데스크탑 470px 최소폭을 풀었으므로
        // 창이 정보창 폭(sidebarW)까지 그대로 줄어듦 → 정보창 안 커지고 오른쪽 띠도 없음.
        var chromeW = Math.max(0, window.outerWidth - window.innerWidth);
        window.resizeTo((sidebarW || 360) + chromeW, window.outerHeight);
      } else if (_winExpandedW) {
        window.resizeTo(_winExpandedW, window.outerHeight);
      }
    } catch (e) { /* resizeTo 미지원/차단(일반 탭) — 무시 */ }
  }
  function _setChatCollapsed(on) {
    on = !!on;
    var was = app.classList.contains("chat-collapsed");
    if (on === was) { _applyCollapsedUI(on); return; }
    if (on) {
      // ── 접기 ── 정보창은 '고정 폭 그대로'(1fr 안 씀 → 안 커짐). 보던 대화 스크롤 위치를 저장.
      try {
        if (els.messages && activeRoom) _collapseScroll = { roomId: activeRoom.id, top: els.messages.scrollTop };
        else _collapseScroll = null;
      } catch (e) { _collapseScroll = null; }
      _winExpandedW = window.outerWidth;                 // 줄이기 전 현재(펼침) 창 너비 기억
      var sb = document.querySelector(".sidebar");
      var sidebarW = sb ? Math.ceil(sb.getBoundingClientRect().width) : 360;
      _applyCollapsedUI(true);
      _resizeWindowForCollapse(true, sidebarW);
    } else {
      // ── 펼치기 ── 창 복원 후, 접기 전 보던 스크롤 위치를 그대로 복원(같은 방). 방 바뀐 경우 하단.
      _applyCollapsedUI(false);
      _resizeWindowForCollapse(false);
      var saved = _collapseScroll; _collapseScroll = null;
      var sameRoom = !!(saved && activeRoom && activeRoom.id === saved.roomId);
      var finish = function () {
        try {
          if (sameRoom) els.messages.scrollTop = saved.top;
          else if (typeof _forceMessagesToBottom === "function") _forceMessagesToBottom();
        } catch (e) {}
      };
      finish(); setTimeout(finish, 60); setTimeout(finish, 220);
    }
    try { localStorage.setItem("knk_chat_collapsed", on ? "1" : "0"); } catch (e) {}
  }
  (function initChatCollapse() {
    if (SOLO_MODE) return;   // 단독창은 사이드바(방 목록)가 없어 접기 의미 없음
    // 새로고침 시엔 항상 펼친 상태로 시작 (창 크기 자동 변경 혼란 방지). 토글은 세션 중 동작.
    var btn = document.getElementById("chatCollapseBtn");
    if (btn) btn.addEventListener("click", function () {
      _setChatCollapsed(!app.classList.contains("chat-collapsed"));
    });
  })();

  // ===== 화면 테마 (대표 지시 2026-05-28) =====
  //  · 서버: users.ui_theme — 모든 기기 동기화
  //  · 클라이언트: localStorage 캐시로 첫 페이지 로드 시 깜빡임 방지
  //  · 5개 테마: light(기본) / dark / sage / cream / sky
  const KNK_THEMES = ["light", "dark", "sage", "cream", "sky"];
  function _applyTheme(theme) {
    if (!KNK_THEMES.includes(theme)) theme = "light";
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("knk_ui_theme", theme); } catch (e) {}
    document.querySelectorAll("#themeOptions .theme-opt").forEach(function (b) {
      b.classList.toggle("active", b.dataset.themeId === theme);
    });
  }
  (function initTheme() {
    // 1) 서버가 <html data-theme="..."> 로 이미 설정한 값이 우선 (no-flash)
    var current = document.documentElement.dataset.theme || "light";
    // 2) localStorage 캐시도 있으면, 서버값과 다르면 서버값 우선 (서버가 진실)
    try {
      var cached = localStorage.getItem("knk_ui_theme");
      if (cached && KNK_THEMES.includes(cached) && cached !== current) {
        // 서버와 다르면 캐시 갱신만 (이미 서버 값으로 그려져 있음)
        localStorage.setItem("knk_ui_theme", current);
      }
    } catch (e) {}
    _applyTheme(current);
    // 3) 카드 클릭 → 즉시 적용 + DB 저장
    document.querySelectorAll("#themeOptions .theme-opt").forEach(function (b) {
      b.addEventListener("click", async function () {
        const t = b.dataset.themeId;
        _applyTheme(t);
        try {
          await fetch(`${BASE}/api/me/theme`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ theme: t }),
          });
        } catch (e) { /* 네트워크 실패해도 다음 새로고침 때 서버 응답으로 교정됨 */ }
      });
    });
  })();
  // 설정 → 🔒 보안 탭 안의 🔐 비밀번호 변경 버튼 — 설정창 닫고 비밀번호 변경창 열기 (대표 지시 2026-05-24)
  const _secCpwBtn = document.getElementById("secChangePwBtn");
  if (_secCpwBtn) {
    _secCpwBtn.addEventListener("click", () => {
      const dlg = document.getElementById("notifySettingsDialog");
      try { if (dlg) dlg.close(); } catch (_) {}
      openChangePasswordDialog();
    });
  }

  // socket: 상태 변경 broadcast 수신
  function _wireStatusSocket() {
    if (!window.socket) return setTimeout(_wireStatusSocket, 200);
    socket.on("user_status_changed", (e) => {
      _userStatusMap[e.user_id] = {
        user_id: e.user_id,
        status: e.status,
        custom_text: e.custom_text,
        emoji: e.emoji,
        label: e.label,
        at_office: !!e.at_office,
        until_at: e.until_at || null,   // 기한(회의·외근 시각 / 출장·휴가 날짜) 실시간 반영 (대표 지시 2026-06-06)
      };
      window._userStatusMap = _userStatusMap;
      if (e.user_id === meId) {
        _myCurrentStatus = e.status;
        _renderMyStatusBadge(_userStatusMap[meId]);
        _applyDndIfNeeded(e.status);
      }
      // 사이드바 사용자 목록 색점 즉시 갱신 (대표 지시 2026-05-19)
      try { if (typeof renderUserList === "function") renderUserList(); } catch(err) {}
      // 아바타 상태 이모지 즉시 갱신 — 방 목록(1:1) + 열린 대화창 발신자 (대표 지시 2026-05-22)
      try { if (typeof renderRoomList === "function") renderRoomList(); } catch(err) {}
      try { _refreshMsgAvatars(); } catch(err) {}
      try { _refreshPickerAvatars(); } catch(err) {}
    });
    // 상태표시 상세 on/off 가 관리자에 의해 바뀌면 즉시 반영 (새로고침 불필요) — 대표 지시 2026-06-01
    socket.on("presence_detail_changed", (e) => {
      window._presenceDetail = !!(e && (e.detail === 1 || e.detail === true));
      try { if (typeof renderUserList === "function") renderUserList(); } catch(err) {}
      try { if (typeof renderRoomList === "function") renderRoomList(); } catch(err) {}
      try { _refreshMsgAvatars(); } catch(err) {}
      try { _refreshPickerAvatars(); } catch(err) {}
      try { const _me = _userStatusMap[meId]; if (_me) _renderMyStatusBadge(_me); } catch(err) {}
      // 관리자 설정창이 열려 있으면 토글 상태도 동기화
      try { const t = document.getElementById("presenceDetailToggle"); if (t) t.checked = window._presenceDetail; } catch(err) {}
    });
    // 개인 아바타 변경 실시간 반영 (대표 지시 2026-06-03)
    socket.on("self_avatar_changed", (e) => {
      try {
        if (!e || e.user_id == null) return;
        _selfAvatarMap[e.user_id] = e.self_avatar || null;
        window._selfAvatarMap = _selfAvatarMap;
        if (typeof renderUserList === "function") renderUserList();
        if (typeof renderRoomList === "function") renderRoomList();
        try { _refreshMsgAvatars(); } catch (e2) {}
        try { _refreshPickerAvatars(); } catch (e2) {}
        if (e.user_id === meId) { try { _refreshMyHeaderAvatar(); } catch (e2) {} }
      } catch (err) {}
    });
  }
  setTimeout(_wireStatusSocket, 500);
  // 최초 로드 + 1분 주기 갱신 (실시간 broadcast 를 놓쳤을 때 안전망). (2026-05-20: 5분→1분)
  setTimeout(refreshAllUserStatuses, 1500);
  setInterval(refreshAllUserStatuses, 60 * 1000);

  // ── 새 버전 배포 감지 → '새로고침' 안내 배너 (대표 지시 2026-05-24) ──
  //  서버 버전(STATIC_VERSION)이 로드 시 버전과 달라지면(=재배포됨) 상단에 안내 배너 표시.
  //  화면 다시 볼 때 + 소켓 재접속 + 5분 주기로 확인. 작업 흐름은 끊지 않음(수동 새로고침).
  let _updateBannerShown = false;
  let _autoUpdating = false;
  // SW 해제 + 모든 캐시 삭제 (옛 코드 잔재 완전 제거)
  async function _nukeCaches() {
    try {
      if ("serviceWorker" in navigator) {
        const regs = await navigator.serviceWorker.getRegistrations();
        await Promise.all(regs.map(r => r.unregister()));
      }
      if ("caches" in window) {
        const keys = await caches.keys();
        await Promise.all(keys.map(k => caches.delete(k)));
      }
    } catch (e) { /* noop */ }
  }
  // HTML 까지 확실히 새로 받도록 캐시버스트 쿼리 붙여 reload (reload() 만으론 HTML 이 옛것일 수 있음)
  function _reloadFresh() {
    try {
      const u = new URL(location.href);
      u.searchParams.set("_v", String(Date.now()));
      location.replace(u.toString());
    } catch (e) {
      try { location.reload(); } catch (e2) { location.href = location.pathname + location.search; }
    }
  }
  // 작성 중(메시지칸에 글자)이거나 창(dialog)이 열려 있으면 자동 새로고침으로 끊지 않음
  function _isSafeToAutoReload() {
    try {
      const ta = document.querySelector(".composer textarea");
      if (ta && ta.value && String(ta.value).trim()) return false;
      if (document.querySelector("dialog[open]")) return false;
      const ae = document.activeElement;
      if (ae && (ae.tagName === "TEXTAREA" || ae.tagName === "INPUT") && ae.value && String(ae.value).trim()) return false;
      return true;
    } catch (e) { return false; }
  }
  async function _checkAppVersion() {
    if (_updateBannerShown || _autoUpdating) return;
    try {
      const r = await fetch(BASE + "/api/version", { cache: "no-store" });
      if (!r.ok) return;
      const d = await r.json();
      const loaded = String(window.KNK_VERSION || "");
      if (!(d && d.version && loaded && String(d.version) !== loaded)) return;
      // 같은 새 버전으로 최근 90초 내 이미 자동 새로고침했는데도 또 감지되면(=안 바뀜) 루프 방지 → 배너만
      let recentlyTried = false;
      try {
        const prev = JSON.parse(sessionStorage.getItem("knk_autoupd") || "null");
        if (prev && prev.v === String(d.version) && (Date.now() - prev.t) < 90000) recentlyTried = true;
      } catch (e) {}
      if (recentlyTried || !_isSafeToAutoReload()) { _showUpdateBanner(); return; }
      // 자동 업데이트: 캐시 비우고 새로 받기 (작성 중·창 열림 아닐 때만 여기 옴)
      _autoUpdating = true;
      try { sessionStorage.setItem("knk_autoupd", JSON.stringify({ v: String(d.version), t: Date.now() })); } catch (e) {}
      await _nukeCaches();
      _reloadFresh();
    } catch (e) { /* noop */ }
  }
  function _showUpdateBanner() {
    if (_updateBannerShown) return;
    _updateBannerShown = true;
    const bar = document.createElement("div");
    bar.id = "updateBanner";
    bar.innerHTML = `<span>🆕 새 버전이 나왔어요</span><button type="button" id="updateReloadBtn">🔄 지금 적용</button>`;
    document.body.appendChild(bar);
    const btn = document.getElementById("updateReloadBtn");
    if (btn) btn.addEventListener("click", async () => { try { await _nukeCaches(); } catch (e) {} _reloadFresh(); });
  }
  document.addEventListener("visibilitychange", () => { if (!document.hidden) _checkAppVersion(); });
  setInterval(_checkAppVersion, 3 * 60 * 1000);
  try { if (typeof socket !== "undefined" && socket) socket.on("connect", () => { setTimeout(_checkAppVersion, 1500); }); } catch (e) {}

  // 스레드 패널에 🧠 요약 버튼 동적 추가
  // (openThreadPanel 에서 호출됨 — 별도 함수)
  window._addThreadSummarizeBtn = function(parentId) {
    const head = document.querySelector(".thread-panel-head");
    if (!head || head.querySelector(".thread-summarize-btn")) return;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "thread-summarize-btn";
    const _aiOn = !!document.querySelector(".ai-avatar.on");
    btn.title = "스레드 AI 요약";
    btn.innerHTML = `<span class="ai-avatar sm ${_aiOn ? "on" : "off"}">AI</span>`;
    btn.style.cssText = "background:transparent;border:0;cursor:pointer;padding:4px 6px;border-radius:6px;margin-right:6px;display:inline-flex;align-items:center;";
    btn.addEventListener("click", async () => {
      const body = document.getElementById("threadBody");
      if (!body) return;
      // 임시 결과 영역
      let box = document.getElementById("threadAiSumBox");
      if (!box) {
        box = document.createElement("div");
        box.id = "threadAiSumBox";
        box.style.cssText = "background:#FEF3C7;border:1px solid #F59E0B;border-radius:8px;padding:10px;margin-bottom:10px;font-size:calc(13px + var(--fs-add-ui));line-height:1.7;white-space:pre-wrap;color:#92400E;";
        body.insertBefore(box, body.firstChild);
      }
      box.innerHTML = `<span class="ai-mark ${_aiOn ? "on" : "off"}">AI</span> 가 스레드를 요약하는 중…`;
      try {
        const res = await fetch(`${BASE}/api/messages/${parentId}/summarize_thread`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        }).then(r => r.json());
        if (res.error) { box.textContent = `❌ ${res.error}`; return; }
        box.innerHTML = `<div style="font-weight:700;margin-bottom:4px;display:flex;align-items:center;gap:6px;"><span class="ai-mark ${_aiOn ? "on" : "off"}">AI</span> 요약 (${res.message_count}개 메시지)</div>` +
                        `<div>${escapeHtml(res.summary || "")}</div>` +
                        `<div style="font-size:10.5px;color:#92400E;opacity:0.7;margin-top:6px;">${res.cached ? "💾 캐시" : (res.model || "")}</div>`;
      } catch (e) {
        box.textContent = "❌ 네트워크 오류";
      }
    });
    // close 버튼 앞에 삽입
    const closeBtn = document.getElementById("threadCloseBtn");
    if (closeBtn) head.insertBefore(btn, closeBtn);
    else head.appendChild(btn);
  };

  els.digestBtn.addEventListener("click", () => openDigest(false));
  els.closeDigest.addEventListener("click", () => els.digestDialog.close());
  // 오늘 더 이상 열지 않기 — 오늘은 자동 노출 차단 (날짜 바뀌면 다시) (대표 지시 2026-05-23)
  const _digestDismissBtn = document.getElementById("digestDismissToday");
  if (_digestDismissBtn) _digestDismissBtn.addEventListener("click", () => {
    _dismissDigestToday();
    try { els.digestDialog.close(); } catch (e) {}
  });

  // 🔄 강제 새로고침 버튼 — SW unregister + 모든 cache 삭제 + 강제 reload
  const _hardReloadBtn = document.getElementById("hardReloadBtn");
  if (_hardReloadBtn) {
    _hardReloadBtn.addEventListener("click", async () => {
      if (!confirm(window.KNK_t("confirm.hardReload","🔄 강제 새로고침\n\n캐시를 모두 비우고 최신 버전을 받습니다. 진행할까요?"))) return;
      await _nukeCaches();   // SW 해제 + 모든 캐시 삭제 (위 자동업데이트와 동일 로직)
      _reloadFresh();        // 캐시버스트 쿼리 붙여 새로 받기
    });
  }

  // 🔗 HAIST WORKS 열기 — 권한 있는 직원만 버튼 노출(서버 템플릿). 클릭 시 메신저 SSO 로 토큰 발급 후 WORKS 로 자동 로그인. (대표 지시 2026-05-31)
  const _worksBtn = document.getElementById("worksOpenBtn");
  if (_worksBtn) {
    _worksBtn.addEventListener("click", () => {
      const land = (_worksBtn.dataset.worksUrl || "").trim();
      if (!land) { alert(window.KNK_t("alert.worksNotSet","WORKS 주소가 설정되지 않았습니다. 관리자에게 문의하세요.")); return; }
      // 메신저에 로그인된 상태이므로 /sso/login 이 즉시 토큰 발급 후 WORKS 랜딩으로 리다이렉트.
      const url = BASE + "/sso/login?redirect_uri=" + encodeURIComponent(land);
      // 고정 이름 창("knk_works") — 이미 열려 있으면 그 창을 재사용·앞으로 가져옴(매번 새 창 X). (대표 지시 2026-05-31)
      const w = window.open(url, "knk_works");
      if (w) { try { w.focus(); } catch (_) {} } else { location.href = url; }  // 팝업 차단 시 같은 탭으로
    });
  }

  // boot 시 SW 자동 update 시도 (백그라운드) — 새 버전 있으면 다음 reload 때 적용
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.getRegistrations().then(regs => {
      regs.forEach(r => { try { r.update(); } catch (_) {} });
    });
  }

  // ─── 🔔 알림 설정 다이얼로그 wire ───
  function syncNotifySettingsUI() {
    const s = notifySettings.load();
    const $ = (id) => document.getElementById(id);
    if ($('nsSound')) $('nsSound').checked = !!s.soundEnabled;
    if ($('nsVolume')) {
      $('nsVolume').value = Math.round((s.volume || 0.5) * 100);
      if ($('nsVolumePct')) $('nsVolumePct').textContent = $('nsVolume').value + '%';
    }
    if ($('nsSoundType')) $('nsSoundType').value = s.soundType || 'ding';
    if ($('nsCurrentRoomSound')) $('nsCurrentRoomSound').checked = !!s.currentRoomSound;
    if ($('nsSystem')) $('nsSystem').checked = !!s.systemNotification;
    // nsTitleBlink·nsInlineToast·nsSidebarBlink 제거됨 (2026-05-26)
    if ($('nsHidePreview')) $('nsHidePreview').checked = !!s.hidePreview;  // 🔒 알림 내용 숨기기 (대표 지시 2026-05-26)
  }
  // iOS 환경 감지 (Safari + iOS) + PWA standalone 여부
  function detectIOS() {
    const ua = navigator.userAgent || '';
    const isIOS = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
    const isSafari = /^((?!chrome|android).)*safari/i.test(ua);
    return { isIOS, isStandalone, isSafari };
  }

  // ─── 📱 휴대폰 푸시 진단 ───
  async function refreshPushDiagnostic() {
    const $status = document.getElementById('nsPushStatus');
    if (!$status) return;
    const lines = [];
    // iOS 사용자 사전 안내 — PWA 설치 안 했으면 Push 자체 불가능
    const env = detectIOS();
    if (env.isIOS) {
      if (!env.isStandalone) {
        lines.push(`<strong style="color:#A5282C;">📱 iOS 알림 사용 안내</strong>`);
        lines.push(`<span style="color:#1F2937;">현재 Safari 브라우저 모드 — 푸시 알림 미지원.</span>`);
        lines.push(`<span style="color:#1F2937;">✅ Safari 하단 <strong>공유 버튼(⬆) → "홈 화면에 추가"</strong> 로 앱 설치 후 푸시 알림 활성화 가능 (iOS 16.4 이상).</span>`);
        lines.push(`<hr style="margin:6px 0;border:none;border-top:1px dashed #E5E7EB;">`);
      } else {
        lines.push(`✅ iOS PWA 모드 (홈 화면에서 실행) — 푸시 알림 지원 가능`);
      }
    }
    if (!("serviceWorker" in navigator)) {
      lines.push('❌ Service Worker 미지원');
    } else {
      try {
        const reg = await navigator.serviceWorker.ready;
        lines.push(`✅ Service Worker: 활성 (scope: ${reg.scope.replace(location.origin, '')})`);
      } catch (e) {
        lines.push('❌ Service Worker 미등록');
      }
    }
    lines.push("PushManager" in window ? '✅ Push API 지원' : '❌ Push API 미지원');
    if ('Notification' in window) {
      const p = Notification.permission;
      lines.push(p === 'granted' ? '✅ 알림 권한: 허용됨' : `❌ 알림 권한: ${p === 'denied' ? '거부됨 (휴대폰 설정 확인)' : '미요청'}`);
    } else {
      lines.push('❌ Notification API 미지원');
    }
    try {
      if ("serviceWorker" in navigator && "PushManager" in window) {
        const reg = await navigator.serviceWorker.ready;
        const sub = await reg.pushManager.getSubscription();
        if (sub) {
          lines.push(`✅ 푸시 구독: 등록됨<br><span style="color:var(--text-soft);font-size:calc(11px + var(--fs-add-ui));">${sub.endpoint.slice(0, 70)}...</span>`);
        } else {
          lines.push('⚠️ 푸시 구독: 미등록 — "🔄 푸시 재구독" 버튼 누르세요');
        }
      }
    } catch (e) { lines.push('❌ 푸시 구독 조회 실패: ' + e.message); }
    try {
      const cfg = await fetch(BASE + "/api/push/vapid_public").then(r => r.ok ? r.json() : null);
      if (cfg && cfg.public_key && cfg.enabled) lines.push('✅ 서버 VAPID 키: 정상');
      else lines.push('❌ 서버 VAPID 키 미설정');
    } catch (e) { lines.push('❌ 서버 VAPID 조회 실패'); }
    // 서버 측 구독 상태 — DB 에 내 endpoint 가 실제로 저장됐는지
    try {
      const diag = await fetch(BASE + "/api/push/diag").then(r => r.ok ? r.json() : null);
      if (diag) {
        lines.push(diag.pywebpush_ok ? '✅ 서버 pywebpush 모듈: 로드됨' : '❌ 서버 pywebpush 모듈 미설치');
        if (diag.subscription_count > 0) {
          lines.push(`✅ 서버 DB 내 푸시 구독 (uid=${diag.user_id}): <strong>${diag.subscription_count}개</strong>`);
          diag.subscriptions.forEach((s, i) => {
            lines.push(`<span style="color:var(--text-soft);font-size:calc(11px + var(--fs-add-ui));">  · #${s.id} ${s.endpoint}<br>    ua: ${s.user_agent} (${s.created})</span>`);
          });
        } else {
          lines.push(`❌ <strong>서버 DB 내 푸시 구독: 0개</strong> — 클라이언트 측 구독은 됐지만 서버 등록 실패`);
        }
      }
    } catch (e) { lines.push('❌ 서버 진단 API 조회 실패: ' + e.message); }
    $status.innerHTML = lines.join('<br>');
  }

  const _notifyBtn = document.getElementById('notifySettingsBtn');
  const _notifyDlg = document.getElementById('notifySettingsDialog');
  if (_notifyBtn && _notifyDlg) {
    _notifyBtn.addEventListener('click', async () => {
      syncNotifySettingsUI();
      if (typeof lkSyncUI === 'function') { try { lkSyncUI(); } catch (e) {} }
      _syncNewUserSection();     // 🆔 직원 등록 — 관리자에게만 표시 (대표 지시 2026-05-26 헤더→탭 이동)
      _syncOfficeNetSection();   // 🏢 회사 네트워크 — 관리자에게만 표시·로딩
      _syncNotifOffSection();    // 🔔 알림 미설정 직원 — 관리자에게만 표시·로딩
      _syncAwayTimeoutSection(); // 🪑 자리비움 전환 시간 — 관리자에게만 표시·로딩
      _syncAiUsageSection();     // 🤖 AI 번역 사용량 — 관리자에게만 표시 (대표 지시 2026-05-27)
      _syncBugAdminSection();    // 🐞 버그 신고 관리 — 유지보수관리자(김정락)에게만 표시 (대표 지시 2026-06-03)
      _syncUsageSection();       // 📊 사용 현황 — 유지보수관리자(김정락)에게만 표시 (대표 지시 2026-06-03)
      _syncConsentSection();     // 📋 사용동의 현황 — 관리자에게만 표시 (대표 지시 2026-06-05)
      _syncRoomTransSection();   // 🌐 방 이름 자동 번역 — 유지보수관리자에게만 표시 (대표 지시 2026-06-05)
      _syncOpsAdminSection();    // 👤 운영 담당자 지정 — 대표님(유지보수 owner)만 (대표 지시 2026-06-03)
      _syncSysConfigSection();   // 🔧 시스템 설정 토글 — 유지보수(대표님·운영자) (대표 지시 2026-06-03 권한→유지보수 이동)
      if (typeof _syncPermSection === "function") _syncPermSection();  // 🔐 권한 통합 표(채널·WORKS·AI) — 관리자 전용 (대표 지시 2026-05-31 재편)
      _syncEmpInviteSection();   // 👥 직원 초대 — QR·링크·메시지 채움 (게스트는 섹션 없음) (대표 지시 2026-06-01)
      // 🛠 관리자 책갈피 — 관리자(ceo) 또는 유지보수(대표님·운영자)에게 노출 (대표 지시 2026-06-03)
      const _adminTab = document.getElementById('settingsTabAdmin');
      const _isCeo = (window._meRole === 'ceo');
      const _isMaint = !!window.__IS_MAINTENANCE__;
      if (_adminTab) _adminTab.hidden = !(_isCeo || _isMaint);
      // 서브탭 가시성: 👥직원·🔐권한 = 관리자(ceo) / 🔧유지보수 = 유지보수(대표님·운영자)
      const _stStaff = document.getElementById('adminSubtabStaff');
      const _stPerm = document.getElementById('adminSubtabPerm');
      const _stMaint = document.getElementById('adminSubtabMaint');
      if (_stStaff) _stStaff.hidden = !_isCeo;
      if (_stPerm) _stPerm.hidden = !_isCeo;
      if (_stMaint) _stMaint.hidden = !_isMaint;
      // 🖼️ 시작화면(광고) 편집 섹션 — 대표(사번5)만 노출·로드 (대표 지시 2026-06-06)
      const _splSec = document.getElementById('splashAdminSection');
      if (_splSec) _splSec.hidden = !window.__IS_MAINT_OWNER__;
      if (window.__IS_MAINT_OWNER__) { try { _initSplashAdminOnce(); _loadSplashAdmin(); } catch (e) {} }
      _refreshAllDrill();         // 각 탭/서브탭 항목을 '목록'으로 구성 + 메뉴 모드로 (대표 지시 2026-06-03)
      _setSettingsTab('notify');  // 열 때마다 첫 책갈피(알림)로 초기화
      // 관리자면 직원부터, (관리자 아닌) 유지보수 전용이면 바로 🔧유지보수(ops) 서브탭
      if (typeof _setAdminSubtab === 'function') _setAdminSubtab(_isCeo ? 'staff' : 'ops');
      _notifyDlg.showModal();
      await notify.ensurePermission();
      refreshPushDiagnostic();
    });
    // ── 설정 책갈피(탭) 전환 ──
    function _setSettingsTab(name) {
      _notifyDlg.querySelectorAll('.dialog-tabs .tab').forEach(function (b) {
        b.classList.toggle('active', b.dataset.tab === name);
      });
      _notifyDlg.querySelectorAll('.tab-pane').forEach(function (p) {
        p.classList.toggle('active', p.dataset.tabPane === name);
      });
      // 탭 전환 시 그 탭은 항상 '목록'부터 보이게 (대표 지시 2026-06-03 드릴다운)
      const _ap = _notifyDlg.querySelector('.tab-pane[data-tab-pane="' + name + '"]');
      if (_ap) _drillReset(_ap);
    }
    // ── 🛠 관리자 탭 안의 서브탭 (👥 직원 / 🌐 시스템 / 🤖 AI·비용) — 대표 지시 2026-05-27 ──
    function _setAdminSubtab(name) {
      _notifyDlg.querySelectorAll('.admin-subtabs .admin-subtab').forEach(function (b) {
        b.classList.toggle('active', b.dataset.subtab === name);
      });
      _notifyDlg.querySelectorAll('.admin-subpane').forEach(function (p) {
        p.hidden = (p.dataset.subpane !== name);
      });
      // 서브탭 전환 시 그 서브탭은 항상 '목록'부터 (대표 지시 2026-06-03 드릴다운)
      const _sp = _notifyDlg.querySelector('.admin-subpane[data-subpane="' + name + '"]');
      if (_sp) _drillReset(_sp);
    }
    _notifyDlg.querySelectorAll('.admin-subtabs .admin-subtab').forEach(function (b) {
      b.addEventListener('click', function () { _setAdminSubtab(b.dataset.subtab); });
    });

    // ── 🖼️ 시작화면(광고) 편집 — 대표(사번5)만. 설정 저장은 app_settings, 적용은 다음 앱 실행 (대표 지시 2026-06-06) ──
    var _splInit = false;
    var _splCfg = null;
    function _splMsg(t, ok) { var m = document.getElementById('splMsg'); if (m) { m.textContent = t || ''; m.style.color = ok ? '#16A34A' : 'var(--accent)'; } }
    function _splMode() { var r = document.querySelector('input[name="splMode"]:checked'); return r ? r.value : 'logo'; }
    function _splSyncModeFields() { var lf = document.getElementById('splLogoFields'); if (lf) lf.style.display = (_splMode() === 'full') ? 'none' : 'flex'; }
    function _splFill(cfg) {
      _splCfg = cfg || {};
      var $ = function (id) { return document.getElementById(id); };
      if ($('splEnabled')) $('splEnabled').checked = !!cfg.enabled;
      var mr = document.querySelector('input[name="splMode"][value="' + (cfg.mode === 'full' ? 'full' : 'logo') + '"]');
      if (mr) mr.checked = true;
      if ($('splTitle')) $('splTitle').value = cfg.title || '';
      if ($('splTagline')) $('splTagline').value = cfg.tagline || '';
      if ($('splBg')) $('splBg').value = cfg.bg_color || '#ffffff';
      if ($('splTitleColor')) $('splTitleColor').value = cfg.title_color || '#a5282c';
      if ($('splTagColor')) $('splTagColor').value = cfg.tagline_color || '#6b7280';
      if ($('splTitleSize')) $('splTitleSize').value = cfg.title_size || 26;
      if ($('splTagSize')) $('splTagSize').value = cfg.tagline_size || 14;
      if ($('splDur')) $('splDur').value = ((cfg.duration_ms || 1000) / 1000);
      var pv = $('splImagePreview');
      if (pv) { pv.src = cfg.image_url || ''; pv.style.display = (cfg.image_url ? 'inline-block' : 'none'); }
      _splSyncModeFields();
    }
    function _loadSplashAdmin() {
      fetch(BASE + '/api/admin/splash', { credentials: 'same-origin' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (cfg) { if (cfg) _splFill(cfg); })
        .catch(function () {});
    }
    function _splCollect() {
      var $ = function (id) { return document.getElementById(id); };
      var durSec = parseFloat($('splDur') && $('splDur').value) || 1;
      return {
        enabled: ($('splEnabled') && $('splEnabled').checked) ? 1 : 0,
        mode: _splMode(),
        title: ($('splTitle') && $('splTitle').value) || '',
        tagline: ($('splTagline') && $('splTagline').value) || '',
        bg_color: ($('splBg') && $('splBg').value) || '#ffffff',
        title_color: ($('splTitleColor') && $('splTitleColor').value) || '#a5282c',
        tagline_color: ($('splTagColor') && $('splTagColor').value) || '#6b7280',
        title_size: parseInt(($('splTitleSize') && $('splTitleSize').value), 10) || 26,
        tagline_size: parseInt(($('splTagSize') && $('splTagSize').value), 10) || 14,
        duration_ms: Math.round(Math.max(0.5, Math.min(10, durSec)) * 1000),
      };
    }
    function _splPreview() {
      var c = _splCollect();
      var imgUrl = (_splCfg && _splCfg.image_url) || (BASE + '/static/icons/logo.png');
      var ov = document.createElement('div');
      ov.setAttribute('style', 'position:fixed;inset:0;z-index:200000;display:flex;align-items:center;justify-content:center;overflow:hidden;transition:opacity .4s;background:' + c.bg_color);
      if (c.mode === 'full') {
        var im = document.createElement('img');
        im.setAttribute('style', 'position:absolute;inset:0;width:100%;height:100%;object-fit:cover');
        im.src = imgUrl; ov.appendChild(im);
      } else {
        var inner = document.createElement('div');
        inner.setAttribute('style', 'text-align:center;padding:24px;max-width:92vw');
        var lg = document.createElement('img'); lg.src = imgUrl;
        lg.setAttribute('style', 'width:min(58vw,200px);height:auto;display:block;margin:0 auto 18px');
        inner.appendChild(lg);
        if (c.title) { var t = document.createElement('div'); t.textContent = c.title; t.setAttribute('style', 'font-size:' + c.title_size + 'px;font-weight:800;letter-spacing:.5px;color:' + c.title_color); inner.appendChild(t); }
        if (c.tagline) { var g = document.createElement('div'); g.textContent = c.tagline; g.setAttribute('style', 'margin-top:8px;font-size:' + c.tagline_size + 'px;font-weight:500;line-height:1.5;color:' + c.tagline_color); inner.appendChild(g); }
        ov.appendChild(inner);
      }
      var done = false;
      var kill = function () { if (done) return; done = true; try { ov.style.opacity = '0'; } catch (e) {} setTimeout(function () { try { if (ov.parentNode) ov.parentNode.removeChild(ov); } catch (e) {} }, 450); };
      ov.addEventListener('click', kill);
      document.body.appendChild(ov);
      setTimeout(kill, c.duration_ms);   // 미리보기도 설정 시간만큼 (클릭하면 즉시 닫힘)
    }
    function _splSave() {
      _splMsg('저장 중… (자동 번역 포함, 잠시만요)');
      fetch(BASE + '/api/admin/splash', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(_splCollect()) })
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
        .then(function (res) { if (res.ok && res.j && res.j.ok) { _splFill(res.j.splash); _splMsg('저장됨 ✓ — 보는 사람 언어로 자동 번역되어 표시됩니다 (다음 앱 실행 시)', true); } else { _splMsg((res.j && res.j.error) || '저장 실패'); } })
        .catch(function () { _splMsg('저장 실패 (네트워크)'); });
    }
    function _splUpload() {
      var fi = document.getElementById('splImageFile');
      if (!fi || !fi.files || !fi.files[0]) { _splMsg('이미지 파일을 먼저 고르세요.'); return; }
      var fd = new FormData(); fd.append('file', fi.files[0]);
      _splMsg('업로드 중…');
      fetch(BASE + '/api/admin/splash/image', { method: 'POST', credentials: 'same-origin', body: fd })
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
        .then(function (res) { if (res.ok && res.j && res.j.ok) { _splFill(res.j.splash); fi.value = ''; _splMsg('이미지 적용됨 ✓ (글자·방식도 바꿨으면 저장을 누르세요)', true); } else { _splMsg((res.j && res.j.error) || '업로드 실패'); } })
        .catch(function () { _splMsg('업로드 실패 (네트워크)'); });
    }
    function _splClearImage() {
      _splMsg('기본 로고로 되돌리는 중…');
      var body = _splCollect(); body.clear_image = 1;
      fetch(BASE + '/api/admin/splash', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
        .then(function (r) { return r.json(); })
        .then(function (j) { if (j && j.ok) { _splFill(j.splash); _splMsg('기본 로고로 되돌렸어요 ✓', true); } else { _splMsg('실패'); } })
        .catch(function () { _splMsg('실패 (네트워크)'); });
    }
    function _initSplashAdminOnce() {
      if (_splInit) return; _splInit = true;
      var on = function (id, ev, fn) { var el = document.getElementById(id); if (el) el.addEventListener(ev, fn); };
      on('splSaveBtn', 'click', _splSave);
      on('splPreviewBtn', 'click', _splPreview);
      on('splImageUploadBtn', 'click', _splUpload);
      on('splImageClearBtn', 'click', _splClearImage);
      document.querySelectorAll('input[name="splMode"]').forEach(function (r) { r.addEventListener('change', _splSyncModeFields); });
    }

    // ── 설정 드릴다운 (목차 → 항목 진입) — 대표 지시 2026-06-03 ──
    //   탭/서브탭 안 항목이 많아 스크롤하던 것을: 탭 누르면 항목 '목록'만 →
    //   항목 누르면 그 화면으로 '들어가기' + '‹ 뒤로'. 기존 .ns-section 을 읽어 목록 자동 생성.
    //   권한으로 숨겨진(hidden) 항목은 목록에서 제외. 항목 2개 미만이면 드릴 안 함(그냥 표시).
    function _drillContainers() {
      const out = [];
      if (!_notifyDlg) return out;
      _notifyDlg.querySelectorAll('.tab-pane').forEach(function (p) {
        if (p.dataset.tabPane !== 'admin') out.push(p);   // admin 은 서브탭(subpane)별로 따로
      });
      _notifyDlg.querySelectorAll('.admin-subpane').forEach(function (sp) { out.push(sp); });
      return out;
    }
    function _drillTitleEl(section) {
      return section.querySelector('h4') || section.querySelector('summary');
    }
    function _drillLabel(section, i) {
      const el = _drillTitleEl(section);
      let label = (el ? el.textContent : ('항목 ' + (i + 1))).trim();
      while (label && '▶▾▸▼▿ '.indexOf(label.charAt(0)) >= 0) label = label.slice(1);
      const pi = label.lastIndexOf(' (');
      if (pi > 0 && label.charAt(label.length - 1) === ')') label = label.slice(0, pi);
      return label.trim() || ('항목 ' + (i + 1));
    }
    function _buildDrill(container) {
      let menu = container.querySelector(':scope > .drill-menu');
      let back = container.querySelector(':scope > .drill-back');
      if (!menu) {
        back = document.createElement('div');
        back.className = 'drill-back';
        back.innerHTML = '<button type="button" class="drill-back-btn">‹ 뒤로</button><span class="drill-back-title"></span>';
        menu = document.createElement('div');
        menu.className = 'drill-menu';
        container.insertBefore(back, container.firstChild);
        container.insertBefore(menu, container.firstChild);
        back.querySelector('.drill-back-btn').addEventListener('click', function () { _drillShowMenu(container); });
      }
      const sections = Array.prototype.slice.call(container.querySelectorAll(':scope > .ns-section')).filter(function (s) { return !s.hidden; });
      if (sections.length < 2) {
        container.classList.remove('drill-on', 'drill-detail');
        menu.innerHTML = '';
        return;
      }
      container.classList.add('drill-on');
      menu.innerHTML = sections.map(function (s, i) {
        return '<button type="button" class="drill-item" data-idx="' + i + '">' +
          '<span class="drill-item-lbl">' + escapeHtml(_drillLabel(s, i)) + '</span><span class="drill-arrow">›</span></button>';
      }).join('');
      menu.querySelectorAll('.drill-item').forEach(function (btn) {
        btn.addEventListener('click', function () {
          const idx = parseInt(btn.getAttribute('data-idx'), 10);
          _drillShowSection(container, sections[idx]);
        });
      });
      _drillShowMenu(container);
    }
    function _drillShowMenu(container) {
      container.classList.remove('drill-detail');
      container.querySelectorAll(':scope > .ns-section').forEach(function (s) { s.classList.remove('drill-active'); });
    }
    function _drillShowSection(container, section) {
      if (!section) return;
      container.querySelectorAll(':scope > .ns-section').forEach(function (s) { s.classList.toggle('drill-active', s === section); });
      const back = container.querySelector(':scope > .drill-back');
      if (back) {
        const t = back.querySelector('.drill-back-title');
        const el = _drillTitleEl(section);
        if (t) t.textContent = el ? el.textContent.trim() : '';
      }
      if (section.tagName === 'DETAILS') { try { section.open = true; } catch (e) {} }
      container.classList.add('drill-detail');
      try { if (_notifyDlg) _notifyDlg.scrollTop = 0; } catch (e) {}
    }
    function _drillReset(container) {
      if (container && container.classList.contains('drill-on')) _drillShowMenu(container);
    }
    function _refreshAllDrill() {
      _drillContainers().forEach(_buildDrill);
    }

    _notifyDlg.querySelectorAll('.dialog-tabs .tab').forEach(function (b) {
      b.addEventListener('click', function () { _setSettingsTab(b.dataset.tab); });
    });
    // ── 🪑 자리비움 자동 전환 시간 (관리자 전용) ──
    let _awayTimeoutWired = false;
    function _syncAwayTimeoutSection() {
      const sec = document.getElementById('awayTimeoutSection');
      if (!sec) return;
      if (window._meRole !== 'ceo') { sec.hidden = true; return; }
      sec.hidden = false;
      const sel = document.getElementById('awayTimeoutSelect');
      const stat = document.getElementById('awayTimeoutStatus');
      // 현재값 로딩
      fetch(BASE + '/api/admin/away_timeout').then(r => r.json()).then(d => {
        if (sel && d && d.minutes) sel.value = String(d.minutes);
        if (stat) stat.textContent = '현재: ' + ((d && d.minutes) || 15) + '분 후 자리비움';
      }).catch(() => {});
      // 변경 핸들러 1회만 바인딩
      if (sel && !_awayTimeoutWired) {
        _awayTimeoutWired = true;
        sel.addEventListener('change', async () => {
          const m = parseInt(sel.value, 10);
          if (stat) stat.textContent = '저장 중…';
          try {
            const r = await fetch(BASE + '/api/admin/away_timeout', {
              method: 'PUT', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ minutes: m }),
            });
            const d = await r.json();
            if (!r.ok) { if (stat) stat.textContent = '❌ ' + (d.error || r.status); return; }
            if (stat) stat.textContent = '✅ ' + d.minutes + '분으로 저장됨 (각 기기는 새로고침 시 완전 반영)';
          } catch (e) { if (stat) stat.textContent = '❌ 네트워크 오류'; }
        });
      }
    }
    // ── 🆔 직원 등록 (관리자 전용) — 헤더 newUserBtn 의 백업 진입점 (대표 지시 2026-05-26) ──
    let _newUserOpenWired = false;
    function _syncNewUserSection() {
      const sec = document.getElementById('newUserSection');
      if (!sec) return;
      if (window._meRole !== 'ceo') { sec.hidden = true; return; }
      sec.hidden = false;
      // 버튼 1회만 바인딩 — 클릭 시 기존 newUserBtn 의 동작을 그대로 트리거
      if (!_newUserOpenWired) {
        _newUserOpenWired = true;
        const btn = document.getElementById('newUserOpenBtn');
        if (btn) {
          btn.addEventListener('click', () => {
            try { _notifyDlg.close(); } catch(_) {}
            const headerBtn = document.getElementById('newUserBtn');
            if (headerBtn) headerBtn.click();
          });
        }
      }
    }
    // ── 🏢 회사 네트워크 관리 (관리자 전용) ──
    function _syncOfficeNetSection() {
      const sec = document.getElementById('officeNetSection');
      if (!sec) return;
      if (!window.__IS_MAINTENANCE__) { sec.hidden = true; return; }   // 🔧유지보수로 이동 (대표 지시 2026-06-03)
      sec.hidden = false;
      _refreshOfficeNetUI();
    }
    async function _refreshOfficeNetUI() {
      const cur = document.getElementById('officeNetCurrent');
      const listEl = document.getElementById('officeNetList');
      try {
        const data = await fetch(BASE + '/api/office_networks').then(r => r.json());
        if (cur) cur.textContent = '현재 내 접속 IP: ' + (data.current_ip || '(확인 불가)');
        const nets = (data && data.networks) || [];
        if (listEl) {
          listEl.innerHTML = nets.length
            ? nets.map(n => `<div style="display:flex;align-items:center;gap:8px;justify-content:space-between;font-size:calc(12px + var(--fs-add-ui));background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:6px 8px;">
                 <span>🏢 ${escapeHtml(n.ip)}${n.label ? ' · ' + escapeHtml(n.label) : ''}</span>
                 <button type="button" class="ns-preview-btn office-net-del" data-id="${n.id}" style="border-color:#A5282C;color:#A5282C;padding:2px 8px;">삭제</button>
               </div>`).join('')
            : '<div class="dialog-hint" style="font-size:calc(11px + var(--fs-add-ui));color:var(--text-soft);">등록된 회사망이 없습니다. 회사에서 위 버튼을 눌러 등록하세요.</div>';
        }
      } catch (e) {
        if (cur) cur.textContent = '회사망 목록을 불러오지 못했습니다.';
      }
    }
    const _officeAddBtn = document.getElementById('officeNetAddBtn');
    if (_officeAddBtn) _officeAddBtn.addEventListener('click', async () => {
      _officeAddBtn.disabled = true;
      try {
        const r = await fetch(BASE + '/api/office_networks', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}'
        });
        const d = await r.json();
        if (!r.ok) { alert(window.KNK_t("alert.registerFail","등록 실패") + ": " + (d.error || r.status)); }
        else { _refreshOfficeNetUI(); }
      } catch (e) { alert(window.KNK_t("alert.registerFail","등록 실패") + ": " + (e.message || e)); }
      _officeAddBtn.disabled = false;
    });
    const _officeListEl = document.getElementById('officeNetList');
    if (_officeListEl) _officeListEl.addEventListener('click', async (e) => {
      const btn = e.target.closest('.office-net-del');
      if (!btn) return;
      if (!confirm(window.KNK_t("confirm.deleteCompanyNet","이 회사망 등록을 삭제할까요? (해당 망에서 접속해도 🏢 회사 표시가 사라집니다)"))) return;
      try {
        await fetch(BASE + '/api/office_networks/' + btn.dataset.id, { method: 'DELETE' });
        _refreshOfficeNetUI();
      } catch (e2) { alert(window.KNK_t("alert.deleteFail","삭제 실패")); }
    });
    // ── 🔔 알림 미설정 직원 (관리자 전용) ──
    let _notifOffCollapsed = true;   // 기본 접힘 — 명단이 길어 화면 차지 방지 (대표 지시 2026-05-29)
    let _notifOffCount = 0;
    function _applyNotifOffCollapse() {
      const listEl = document.getElementById('notifOffList');
      const toggleBtn = document.getElementById('notifOffToggle');
      if (!listEl || !toggleBtn) return;
      if (_notifOffCount <= 0) {            // 알림 OFF 0명 — 토글 숨기고 빈상태(✅) 메시지 노출
        toggleBtn.style.display = 'none';
        listEl.style.display = 'flex';
        return;
      }
      toggleBtn.style.display = '';
      listEl.style.display = _notifOffCollapsed ? 'none' : 'flex';
      const expand = window.KNK_t ? window.KNK_t('notifOff.expand') : '명단 펼치기';
      const collapse = window.KNK_t ? window.KNK_t('notifOff.collapse') : '명단 접기';
      toggleBtn.textContent = _notifOffCollapsed ? `▾ ${expand} (${_notifOffCount})` : `▴ ${collapse}`;
    }
    function _syncNotifOffSection() {
      const sec = document.getElementById('notifOffSection');
      if (!sec) return;
      if (window._meRole !== 'ceo') { sec.hidden = true; return; }
      sec.hidden = false;
      _refreshNotifOffUI();
    }
    async function _refreshNotifOffUI() {
      const sum = document.getElementById('notifOffSummary');
      const listEl = document.getElementById('notifOffList');
      try {
        const d = await fetch(BASE + '/api/admin/notif_off').then(r => r.json());
        const off = (d && d.off) || [];
        _notifOffCount = off.length;
        if (sum) sum.textContent = `전체 ${d.total_active}명 중 알림 OFF ${d.off_count}명`;
        if (listEl) {
          listEl.innerHTML = off.length
            ? off.map(u => {
                const dept = u.department ? (typeof deptDisplayLabel === 'function' ? deptDisplayLabel(u.department) : u.department) : '';
                const meta = [u.title, dept].filter(Boolean).join(' · ');
                return `<div style="font-size:calc(12px + var(--fs-add-ui));background:#FEF2F2;color:#1F2937;border:1px solid #FECACA;border-radius:6px;padding:6px 8px;">
                  🔕 <b>${escapeHtml(u.display_name)}</b>${meta ? ` <span style="color:var(--text-soft);">${escapeHtml(meta)}</span>` : ''}</div>`;
              }).join('')
            : '<div class="dialog-hint" style="font-size:calc(11px + var(--fs-add-ui));color:#10B981;">✅ 모든 직원이 알림을 켰습니다.</div>';
        }
        _applyNotifOffCollapse();
      } catch (e) {
        if (sum) sum.textContent = '목록을 불러오지 못했습니다.';
      }
    }
    const _notifOffRefreshBtn = document.getElementById('notifOffRefreshBtn');
    if (_notifOffRefreshBtn) _notifOffRefreshBtn.addEventListener('click', _refreshNotifOffUI);
    const _notifOffToggleBtn = document.getElementById('notifOffToggle');
    if (_notifOffToggleBtn) _notifOffToggleBtn.addEventListener('click', () => {
      _notifOffCollapsed = !_notifOffCollapsed;
      _applyNotifOffCollapse();
    });

    // ── 🤖 AI 번역 사용량 (관리자 전용) — 대표 지시 2026-05-27 ──
    let _aiUsageCorp = 'hq';        // 'hq'(본사) | 'vn'(베트남법인) — 본사/베트남 책갈피 (대표 지시 2026-06-05)
    let _aiUsageLastData = null;    // 마지막 응답 캐시 — 탭 전환 시 재조회 없이 다시 렌더
    function _syncAiUsageSection() {
      const sec = document.getElementById('aiUsageSection');
      if (!sec) return;
      if (!window.__IS_MAINTENANCE__) { sec.hidden = true; return; }   // 🔧유지보수(대표님·운영자)에게만 표시 — 직원→유지보수 재이동 (대표 지시 2026-06-06)
      sec.hidden = false;
      _refreshAiUsageUI();
    }
    async function _refreshAiUsageUI() {
      const periodSel = document.getElementById('aiUsagePeriod');
      const deptSel = document.getElementById('aiUsageDept');
      const summary = document.getElementById('aiUsageSummary');
      const tbody = document.getElementById('aiUsageTbody');
      if (!summary || !tbody) return;
      const period = periodSel ? periodSel.value : 'this_month';
      const dept = deptSel ? deptSel.value : 'all';
      summary.innerHTML = '<div style="font-size:calc(11px + var(--fs-add-ui));color:var(--text-soft);">불러오는 중…</div>';
      tbody.innerHTML = '<tr><td colspan="5" style="padding:12px;text-align:center;color:var(--text-soft);">불러오는 중…</td></tr>';
      try {
        const url = `${BASE}/api/admin/translate_usage?period=${encodeURIComponent(period)}&dept=${encodeURIComponent(dept)}`;
        const d = await fetch(url).then(r => {
          if (r.status === 403) throw new Error('관리자 전용');
          return r.json();
        });
        // 부서 드롭다운 채우기 (초기 1회 또는 새 부서 발견 시)
        if (deptSel && Array.isArray(d.departments)) {
          const current = deptSel.value;
          const existing = Array.from(deptSel.options).map(o => o.value);
          const next = ['all', ...d.departments];
          if (JSON.stringify(existing) !== JSON.stringify(next)) {
            deptSel.innerHTML = '<option value="all">전체</option>' +
              d.departments.map(dpt => `<option value="${escapeHtml(dpt)}">${escapeHtml(dpt)}</option>`).join('');
            if (existing.includes(current)) deptSel.value = current;
          }
        }
        // 합계 박스
        const monthlyPct = d.monthly_limit_usd > 0
          ? Math.min(100, (d.monthly_cost_usd / d.monthly_limit_usd) * 100)
          : 0;
        const pctColor = monthlyPct > 80 ? '#dc2626' : monthlyPct > 50 ? '#d97706' : '#10b981';
        summary.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap;">
            <div>
              <div style="font-size:calc(12px + var(--fs-add-ui));color:var(--text-soft);">${escapeHtml(d.period_label)} 합계</div>
              <div style="font-size:calc(20px + var(--fs-add-ui));font-weight:800;color:#1f2937;">$${d.total_cost_usd.toFixed(4)}</div>
              <div style="font-size:calc(11px + var(--fs-add-ui));color:var(--text-soft);">호출 ${d.total_calls.toLocaleString()}회 / 토큰 ${(d.total_in_tokens + d.total_out_tokens).toLocaleString()}</div>
            </div>
            <div style="text-align:right;">
              <div style="font-size:calc(11px + var(--fs-add-ui));color:var(--text-soft);">이번 달 한도</div>
              <div style="font-size:calc(13px + var(--fs-add-ui));font-weight:700;color:${pctColor};">$${d.monthly_cost_usd.toFixed(4)} / $${d.monthly_limit_usd.toFixed(2)}</div>
              <div style="font-size:10px;color:var(--text-soft);">${monthlyPct.toFixed(1)}% · 공급자: ${escapeHtml(d.provider)}</div>
            </div>
          </div>
          <div style="margin-top:6px;height:6px;background:#E5E7EB;border-radius:3px;overflow:hidden;">
            <div style="width:${monthlyPct}%;height:100%;background:${pctColor};transition:width .2s;"></div>
          </div>
        `;
        // 표 — 본사/베트남법인 책갈피로 분리 렌더 (대표 지시 2026-06-05)
        _aiUsageLastData = d;
        _renderAiUsageRows();
      } catch (e) {
        summary.innerHTML = `<div style="font-size:calc(12px + var(--fs-add-ui));color:#dc2626;">불러오기 실패: ${escapeHtml(String(e.message || e))}</div>`;
        tbody.innerHTML = '';
      }
    }
    // 본사/베트남법인 탭별 행 렌더 — 캐시(_aiUsageLastData) 사용, 재조회 없음 (대표 지시 2026-06-05)
    function _renderAiUsageRows() {
      const tbody = document.getElementById('aiUsageTbody');
      if (!tbody) return;
      const all = (_aiUsageLastData && Array.isArray(_aiUsageLastData.users)) ? _aiUsageLastData.users : [];
      const hq = all.filter(u => !u.is_vn);
      const vn = all.filter(u => u.is_vn);
      const cHq = document.querySelector('[data-corp-count="hq"]');
      const cVn = document.querySelector('[data-corp-count="vn"]');
      if (cHq) cHq.textContent = '(' + hq.length + ')';
      if (cVn) cVn.textContent = '(' + vn.length + ')';
      document.querySelectorAll('.ai-usage-corp-tab').forEach(b => {
        const on = (b.dataset.corp === _aiUsageCorp);
        b.style.background = on ? 'var(--accent)' : 'var(--surface)';
        b.style.color = on ? '#fff' : 'var(--text)';
        b.style.borderColor = on ? 'var(--accent)' : 'var(--border)';
      });
      const list = (_aiUsageCorp === 'vn') ? vn : hq;
      if (!list.length) {
        tbody.innerHTML = '<tr><td colspan="5" style="padding:18px;text-align:center;color:var(--text-soft);">해당 법인 사용 내역 없음</td></tr>';
        return;
      }
      let sCalls = 0, sTok = 0, sCost = 0;
      const body = list.map(u => {
        const dept = u.department ? (typeof deptDisplayLabel === 'function' ? deptDisplayLabel(u.department) : u.department) : '';
        const meta = [u.title, dept].filter(Boolean).join(' · ');
        sCalls += (u.calls || 0); sTok += ((u.in_tokens || 0) + (u.out_tokens || 0)); sCost += (u.cost_usd || 0);
        const _nm = (u.is_vn && u.display_name_vn) ? `${u.display_name_vn} (${u.display_name})` : u.display_name;
        return `<tr style="border-bottom:1px solid var(--border);">
            <td style="padding:5px 8px;"><b>${escapeHtml(_nm)}</b></td>
            <td style="padding:5px 8px;color:var(--text-soft);font-size:10.5px;">${escapeHtml(meta)}</td>
            <td style="padding:5px 8px;text-align:right;">${u.calls.toLocaleString()}</td>
            <td style="padding:5px 8px;text-align:right;color:var(--text-soft);font-size:10.5px;">${(u.in_tokens + u.out_tokens).toLocaleString()}</td>
            <td style="padding:5px 8px;text-align:right;font-weight:700;color:#A5282C;">$${u.cost_usd.toFixed(4)}</td>
          </tr>`;
      }).join('');
      const sub = `<tr style="border-top:2px solid var(--border);background:var(--bg);">
            <td style="padding:6px 8px;font-weight:800;" colspan="2">${_aiUsageCorp === 'vn' ? '🇻🇳 베트남법인' : '🇰🇷 본사'} 소계 · ${list.length}명</td>
            <td style="padding:6px 8px;text-align:right;font-weight:800;">${sCalls.toLocaleString()}</td>
            <td style="padding:6px 8px;text-align:right;color:var(--text-soft);font-weight:700;">${sTok.toLocaleString()}</td>
            <td style="padding:6px 8px;text-align:right;font-weight:800;color:#A5282C;">$${sCost.toFixed(4)}</td>
          </tr>`;
      tbody.innerHTML = body + sub;
    }
    const _aiUsageRefreshBtn = document.getElementById('aiUsageRefreshBtn');
    if (_aiUsageRefreshBtn) _aiUsageRefreshBtn.addEventListener('click', _refreshAiUsageUI);
    document.querySelectorAll('.ai-usage-corp-tab').forEach(b => {
      b.addEventListener('click', () => { _aiUsageCorp = b.dataset.corp; _renderAiUsageRows(); });
    });
    const _aiUsagePeriod = document.getElementById('aiUsagePeriod');
    if (_aiUsagePeriod) _aiUsagePeriod.addEventListener('change', _refreshAiUsageUI);
    const _aiUsageDept = document.getElementById('aiUsageDept');
    if (_aiUsageDept) _aiUsageDept.addEventListener('change', _refreshAiUsageUI);

    // ── 🐞 버그 신고 (전 직원 신고 + 유지보수관리자 관리) — 대표 지시 2026-06-03 ──
    function _bugCollectContext() {
      const ua = navigator.userAgent || "";
      const has = (s) => ua.indexOf(s) >= 0;
      const device = (window.matchMedia && window.matchMedia("(pointer:coarse)").matches) ? "모바일" : "PC";
      let browser = "기타";
      if (has("Edg/")) browser = "Edge";
      else if (has("SamsungBrowser")) browser = "Samsung";
      else if (has("Chrome/")) browser = "Chrome";
      else if (has("Firefox/")) browser = "Firefox";
      else if (has("Version/") && has("Safari")) browser = "Safari";
      let os = "기타";
      if (has("Windows")) os = "Windows";
      else if (has("Android")) os = "Android";
      else if (has("iPhone") || has("iPad") || has("iPod")) os = "iOS";
      else if (has("Mac OS X")) os = "Mac";
      else if (has("Linux")) os = "Linux";
      return {
        screen: (activeRoom ? "대화방" : "메인"),
        room: (activeRoom ? (activeRoom.name || ("room#" + activeRoom.id)) : ""),
        device: device, browser: browser, os: os,
        app_version: (window.__ASSET_VER__ || ""),
        ui_lang: (window._meUiLang || document.documentElement.lang || ""),
        screen_size: (window.innerWidth + "x" + window.innerHeight),
        url: String(location.pathname + location.search).slice(0, 200),
      };
    }
    const _bugSubmitBtn = document.getElementById('bugSubmitBtn');
    if (_bugSubmitBtn) _bugSubmitBtn.addEventListener('click', async function () {
      const tEl = document.getElementById('bugTitle');
      const bEl = document.getElementById('bugBody');
      const shotEl = document.getElementById('bugShot');
      const resEl = document.getElementById('bugResult');
      const title = ((tEl && tEl.value) || "").trim();
      const body = ((bEl && bEl.value) || "").trim();
      if (!title && !body) { alert("내용을 입력해 주세요. / Vui lòng nhập nội dung."); return; }
      _bugSubmitBtn.disabled = true;
      const _orig = _bugSubmitBtn.textContent;
      _bugSubmitBtn.textContent = "보내는 중…";
      try {
        const r = await fetch(`${BASE}/api/bug_reports`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: title, body: body, context: _bugCollectContext() }),
        });
        const d = await r.json().catch(() => ({}));
        if (!r.ok || d.error) throw new Error(d.error || ("오류 " + r.status));
        // 스크린샷 — 신고 글이 올라간 방에 기존 업로드로 첨부 (best-effort, 실패해도 신고는 접수됨)
        const file = shotEl && shotEl.files && shotEl.files[0];
        if (file && d.room_id && typeof api !== "undefined" && api.upload) {
          try { await api.upload(d.room_id, file, null, null); } catch (e) {}
        }
        if (tEl) tEl.value = "";
        if (bEl) bEl.value = "";
        if (shotEl) shotEl.value = "";
        if (resEl) {
          resEl.hidden = false;
          resEl.textContent = "✅ 신고가 접수되었습니다. 감사합니다! '🐞 버그 신고' 채널에서 진행 상황을 볼 수 있어요. / Đã gửi báo lỗi. Cảm ơn!";
        }
      } catch (e) {
        alert("신고 전송 실패 / Gửi thất bại: " + (e.message || e));
      } finally {
        _bugSubmitBtn.disabled = false;
        _bugSubmitBtn.textContent = _orig;
      }
    });

    // 🐞 유지보수관리자(김정락) 전용 — 버그 신고 관리
    let _bugFilter = "";
    const _BUG_ST = {
      "new":      { label: "접수",     color: "#2563eb" },
      "triaged":  { label: "확인중",   color: "#d97706" },
      "fixed":    { label: "수정완료", color: "#7c3aed" },
      "deployed": { label: "배포완료", color: "#10b981" },
      "wontfix":  { label: "보류",     color: "#6b7280" },
    };
    const _BUG_ORDER = ["new", "triaged", "fixed", "deployed", "wontfix"];
    function _syncBugAdminSection() {
      const sec = document.getElementById('bugAdminSection');
      if (!sec) return;
      if (!window.__IS_MAINTENANCE__) { sec.hidden = true; return; }
      sec.hidden = false;
      _refreshBugAdmin();
    }
    async function _refreshBugAdmin() {
      const list = document.getElementById('bugAdminList');
      if (!list) return;
      list.innerHTML = '<div style="padding:14px;text-align:center;color:var(--text-soft);">불러오는 중…</div>';
      try {
        const url = `${BASE}/api/admin/bug_reports${_bugFilter ? ("?status=" + encodeURIComponent(_bugFilter)) : ""}`;
        const d = await fetch(url).then(r => { if (r.status === 403) throw new Error("유지보수관리자 전용"); return r.json(); });
        const reps = d.reports || [];
        if (!reps.length) {
          list.innerHTML = '<div style="padding:18px;text-align:center;color:var(--text-soft);">해당 신고 없음</div>';
          return;
        }
        list.innerHTML = reps.map(b => {
          let ctx = {};
          try { ctx = JSON.parse(b.context_json || "{}"); } catch (e) {}
          const st = _BUG_ST[b.status] || { label: b.status, color: "#6b7280" };
          const metaArr = [ctx.device, ctx.browser, ctx.os, ctx.app_version ? ("v" + ctx.app_version) : "", ctx.screen_size].filter(Boolean);
          const when = String(b.created_at || "").replace("T", " ").slice(0, 16);
          const opts = _BUG_ORDER.map(s => `<option value="${s}"${s === b.status ? " selected" : ""}>${_BUG_ST[s].label}</option>`).join("");
          return `<div class="bug-card">
            <div class="bug-card-top">
              <span class="bug-badge" style="background:${st.color};">${escapeHtml(st.label)}</span>
              <b class="bug-card-title">${escapeHtml(b.title || "(제목 없음)")}</b>
            </div>
            ${b.body ? ('<div class="bug-card-body">' + escapeHtml(b.body) + '</div>') : ""}
            <div class="bug-card-meta">${escapeHtml(b.reporter_name || "?")} · ${escapeHtml(when)}${metaArr.length ? " · " + escapeHtml(metaArr.join(" · ")) : ""}</div>
            <div class="bug-card-act">
              <span style="color:var(--text-soft);font-size:11px;">상태</span>
              <select class="bug-status-sel" data-bid="${b.id}">${opts}</select>
            </div>
          </div>`;
        }).join("");
        list.querySelectorAll('.bug-status-sel').forEach(sel => {
          sel.addEventListener('change', async function () {
            const bid = this.getAttribute('data-bid');
            try {
              const r = await fetch(`${BASE}/api/admin/bug_reports/${bid}/status`, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status: this.value }),
              });
              if (!r.ok) throw new Error("실패");
              _refreshBugAdmin();
            } catch (e) { alert(window.KNK_t("alert.statusChangeFail","상태 변경 실패")); }
          });
        });
      } catch (e) {
        list.innerHTML = `<div style="padding:14px;text-align:center;color:#dc2626;">불러오기 실패: ${escapeHtml(String(e.message || e))}</div>`;
      }
    }
    document.querySelectorAll('#bugAdminFilter .bug-fl').forEach(btn => {
      btn.addEventListener('click', function () {
        _bugFilter = this.getAttribute('data-bugfilter') || "";
        document.querySelectorAll('#bugAdminFilter .bug-fl').forEach(b => b.classList.toggle('active', b === this));
        _refreshBugAdmin();
      });
    });
    const _bugAdminRefresh = document.getElementById('bugAdminRefresh');
    if (_bugAdminRefresh) _bugAdminRefresh.addEventListener('click', _refreshBugAdmin);

    // ── 📊 사용 현황 (유지보수관리자 전용) — 대표 지시 2026-06-03 ──
    function _syncUsageSection() {
      const sec = document.getElementById('usageSection');
      if (!sec) return;
      if (!window.__IS_MAINTENANCE__) { sec.hidden = true; return; }
      sec.hidden = false;
      _refreshUsage();
    }

    // ── 📋 사용동의 현황 (관리자 전용) — 대표 지시 2026-06-05 ──
    let _consentMembers = [];
    let _consentCorp = 'hq';   // 본사/베트남법인 책갈피 (대표 지시 2026-06-05)
    function _renderConsentRows() {
      const tbody = document.getElementById('consentTbody');
      if (!tbody) return;
      const hq = _consentMembers.filter(m => !m.is_vn);
      const vn = _consentMembers.filter(m => m.is_vn);
      const cHq = document.querySelector('[data-ccorp-count="hq"]');
      const cVn = document.querySelector('[data-ccorp-count="vn"]');
      if (cHq) cHq.textContent = '(' + hq.length + ')';
      if (cVn) cVn.textContent = '(' + vn.length + ')';
      document.querySelectorAll('.consent-corp-tab').forEach(b => {
        const on = (b.dataset.corp === _consentCorp);
        b.style.background = on ? 'var(--accent)' : 'var(--surface)';
        b.style.color = on ? '#fff' : 'var(--text)';
        b.style.borderColor = on ? 'var(--accent)' : 'var(--border)';
      });
      const list = (_consentCorp === 'vn') ? vn : hq;
      if (!list.length) {
        tbody.innerHTML = '<tr><td colspan="4" style="padding:14px;text-align:center;color:var(--text-soft);">해당 법인 대상 직원이 없습니다.</td></tr>';
        return;
      }
      tbody.innerHTML = list.map(m => {
        const nm = (m.is_vn && m.display_name_vn)
          ? (escapeHtml(m.display_name_vn) + ' (' + escapeHtml(m.display_name || '') + ')')
          : escapeHtml(m.display_name || '');
        const dept = (typeof _deptShort === 'function') ? _deptShort(m.department) : (m.department || '');
        const ag = m.agreed
          ? '<span style="color:#10b981;font-weight:700;">✅</span>'
          : '<span style="color:#DC2626;font-weight:700;">❌ 미동의</span>';
        const at = (m.agreed && m.agreed_at) ? escapeHtml(String(m.agreed_at).slice(0, 16).replace('T', ' ')) : '';
        const rowBg = m.agreed ? '' : 'background:rgba(220,38,38,0.06);';
        return '<tr style="' + rowBg + '">' +
          '<td style="padding:5px 8px;border-bottom:1px solid var(--border);">' + nm + '</td>' +
          '<td style="padding:5px 8px;border-bottom:1px solid var(--border);color:var(--text-soft);">' + escapeHtml(dept) + '</td>' +
          '<td style="padding:5px 8px;border-bottom:1px solid var(--border);text-align:center;white-space:nowrap;">' + ag + '</td>' +
          '<td style="padding:5px 8px;border-bottom:1px solid var(--border);color:var(--text-soft);white-space:nowrap;">' + at + '</td>' +
        '</tr>';
      }).join('');
    }
    function _syncConsentSection() {
      const sec = document.getElementById('consentSection');
      if (!sec) return;
      // 관리자(ceo) 전체에게 표시 — 동의 현황은 인사 관리 기능 (대표 지시 2026-06-05). 백엔드도 _is_admin_user(ceo+owner).
      if (window._meRole !== "ceo") { sec.hidden = true; return; }
      sec.hidden = false;
      _refreshConsentStatus();
    }
    async function _refreshConsentStatus() {
      const summary = document.getElementById('consentSummary');
      const tbody = document.getElementById('consentTbody');
      if (!summary || !tbody) return;
      summary.innerHTML = '<span style="color:var(--text-soft);">불러오는 중…</span>';
      tbody.innerHTML = '<tr><td colspan="4" style="padding:12px;text-align:center;color:var(--text-soft);">불러오는 중…</td></tr>';
      try {
        const d = await fetch(`${BASE}/api/admin/consent_status`).then(r => {
          if (r.status === 403) throw new Error('관리자 전용');
          return r.json();
        });
        const hq = d.hq || {}, vn = d.vn || {};
        summary.innerHTML =
          '<div style="display:flex;gap:14px;flex-wrap:wrap;align-items:center;">' +
            '<div><b style="font-size:calc(15px + var(--fs-add-ui));">전체 ' + (d.agreed || 0) + ' / ' + (d.total || 0) + '</b> 동의' +
              (d.pending > 0 ? ' <span style="color:#DC2626;font-weight:700;">(미동의 ' + d.pending + '명)</span>' : ' <span style="color:#10b981;">(전원 완료)</span>') + '</div>' +
            '<div style="color:var(--text-soft);">🇰🇷 본사 ' + (hq.agreed || 0) + '/' + (hq.total || 0) + (hq.pending > 0 ? ' <span style="color:#DC2626;">(미 ' + hq.pending + ')</span>' : '') + '</div>' +
            '<div style="color:var(--text-soft);">🇻🇳 베트남 ' + (vn.agreed || 0) + '/' + (vn.total || 0) + (vn.pending > 0 ? ' <span style="color:#DC2626;">(미 ' + vn.pending + ')</span>' : '') + '</div>' +
          '</div>';
        _consentMembers = d.members || [];
        if (!_consentMembers.length) {
          tbody.innerHTML = '<tr><td colspan="4" style="padding:12px;text-align:center;color:var(--text-soft);">대상 직원이 없습니다.</td></tr>';
          const _cHq0 = document.querySelector('[data-ccorp-count="hq"]'); if (_cHq0) _cHq0.textContent = '(0)';
          const _cVn0 = document.querySelector('[data-ccorp-count="vn"]'); if (_cVn0) _cVn0.textContent = '(0)';
          return;
        }
        _renderConsentRows();   // 활성 법인 책갈피만 렌더 (대표 지시 2026-06-05)
      } catch (e) {
        summary.innerHTML = '<span style="color:#DC2626;">불러오기 실패: ' + escapeHtml(e.message || String(e)) + '</span>';
        tbody.innerHTML = '<tr><td colspan="4" style="padding:12px;text-align:center;color:var(--text-soft);">—</td></tr>';
      }
    }
    {
      const _cRefresh = document.getElementById('consentRefreshBtn');
      if (_cRefresh) _cRefresh.addEventListener('click', _refreshConsentStatus);
      const _cExport = document.getElementById('consentExportBtn');
      if (_cExport) _cExport.addEventListener('click', () => {
        const a = document.createElement('a');
        a.href = `${BASE}/api/admin/consent_status/export.xlsx`;
        a.click();
      });
      // 본사/베트남법인 책갈피 전환 (대표 지시 2026-06-05)
      document.querySelectorAll('.consent-corp-tab').forEach(b => {
        b.addEventListener('click', () => { _consentCorp = b.dataset.corp; _renderConsentRows(); });
      });
    }
    // ── 🌐 방 이름 자동 번역 (유지보수관리자 전용) — 대표 지시 2026-06-05 ──
    function _syncRoomTransSection() {
      const sec = document.getElementById('roomTransSection');
      if (!sec) return;
      if (!window.__IS_MAINTENANCE__) { sec.hidden = true; return; }
      sec.hidden = false;
    }
    {
      const _rtBtn = document.getElementById('roomTransRunBtn');
      const _rtStatus = document.getElementById('roomTransStatus');
      let _rtRunning = false;
      const _rtSet = (h) => { if (_rtStatus) _rtStatus.innerHTML = h; };
      if (_rtBtn) _rtBtn.addEventListener('click', async () => {
        if (_rtRunning) return;
        _rtRunning = true; _rtBtn.disabled = true;
        let afterId = 0, totalDone = 0, total = 0, guard = 0;
        _rtSet('번역 시작…');
        try {
          while (guard < 5000) {
            guard++;
            const d = await fetch(`${BASE}/api/admin/retranslate_rooms`, {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ after_id: afterId, limit: 4 })
            }).then(r => { if (r.status === 403) throw new Error('관리자 전용'); return r.json(); });
            if (d.error) throw new Error(d.error);
            afterId = d.last_id; total = d.total || total;
            totalDone += (d.processed || 0);
            _rtSet('번역 중… <b>' + totalDone + ' / ' + total + '</b> 방 (남은 ' + (d.remaining || 0) + ')');
            if (!d.processed || (d.remaining || 0) <= 0) break;
          }
          _rtSet('✅ 완료 — 총 <b>' + totalDone + '</b>개 방 번역됨. 화면을 새로고침하면 각자 언어로 보입니다.');
        } catch (e) {
          _rtSet('<span style="color:#DC2626;">실패: ' + escapeHtml(e.message || String(e)) + '</span>');
        } finally {
          _rtRunning = false; _rtBtn.disabled = false;
        }
      });
    }

    function _usageBar(pct, color) {
      const p = Math.max(0, Math.min(100, pct || 0));
      return '<div class="u-bar"><div class="u-bar-fill" style="width:' + p + '%;background:' + (color || '#A5282C') + ';"></div></div>';
    }
    function _deptShort(dept) {
      if (!dept) return '(미지정)';
      if (typeof deptDisplayLabel === 'function') { try { return deptDisplayLabel(dept); } catch (e) {} }
      let s = String(dept);
      const slash = s.lastIndexOf('/');
      if (slash >= 0) s = s.slice(slash + 1);
      return s.trim() || dept;
    }
    async function _refreshUsage() {
      const body = document.getElementById('usageBody');
      const periodSel = document.getElementById('usagePeriod');
      if (!body) return;
      const period = periodSel ? periodSel.value : 'this_month';
      body.innerHTML = '<div style="padding:14px;text-align:center;color:var(--text-soft);">불러오는 중…</div>';
      try {
        const d = await fetch(`${BASE}/api/admin/usage_overview?period=${encodeURIComponent(period)}`).then(r => {
          if (r.status === 403) throw new Error('유지보수관리자 전용');
          return r.json();
        });
        const a = d.adoption || {};
        const feats = d.features || [];
        const maxFeat = Math.max(1, ...feats.map(f => f.count || 0));
        const hqPct = a.hq_total ? (a.hq_active * 100 / a.hq_total) : 0;
        const vnPct = a.vn_total ? (a.vn_active * 100 / a.vn_total) : 0;
        const adoptCard =
          '<div class="u-cards">' +
            '<div class="u-card u-card-hero">' +
              '<div class="u-card-lbl">채택률 (' + escapeHtml(d.period_label) + ' 사용)</div>' +
              '<div class="u-card-big">' + (a.active_users || 0) + '<span class="u-card-unit"> / ' + (a.total_users || 0) + '명</span></div>' +
              '<div class="u-card-sub">' + (a.active_pct || 0) + '% 가 이 기간에 메신저로 업무</div>' +
              _usageBar(a.active_pct, '#10b981') +
            '</div>' +
            '<div class="u-card"><div class="u-card-lbl">오늘 (DAU)</div><div class="u-card-mid">' + (a.dau || 0) + '<span class="u-card-unit">명</span></div></div>' +
            '<div class="u-card"><div class="u-card-lbl">최근 7일 (WAU)</div><div class="u-card-mid">' + (a.wau || 0) + '<span class="u-card-unit">명</span></div></div>' +
            '<div class="u-card"><div class="u-card-lbl">최근 30일 (MAU)</div><div class="u-card-mid">' + (a.mau || 0) + '<span class="u-card-unit">명</span></div></div>' +
          '</div>' +
          '<div class="u-cards" style="margin-top:6px;">' +
            '<div class="u-card"><div class="u-card-lbl">🇰🇷 본사 활성</div><div class="u-card-mid">' + (a.hq_active || 0) + '<span class="u-card-unit"> / ' + (a.hq_total || 0) + '</span></div>' + _usageBar(hqPct, '#2563eb') + '</div>' +
            '<div class="u-card"><div class="u-card-lbl">🇻🇳 베트남 활성</div><div class="u-card-mid">' + (a.vn_active || 0) + '<span class="u-card-unit"> / ' + (a.vn_total || 0) + '</span></div>' + _usageBar(vnPct, '#d97706') + '</div>' +
          '</div>';
        const featRows = feats.map(f =>
          '<div class="u-feat"><div class="u-feat-lbl">' + (f.emoji || '') + ' ' + escapeHtml(f.label) + '</div>' +
          '<div class="u-feat-bar">' + _usageBar((f.count || 0) * 100 / maxFeat, '#A5282C') + '</div>' +
          '<div class="u-feat-cnt">' + (f.count || 0).toLocaleString() + '</div></div>'
        ).join('');
        const featBlock = '<div class="u-h">📊 기능별 사용 (' + escapeHtml(d.period_label) + ')</div>' + (featRows || '<div class="u-empty">사용 내역 없음</div>');
        const depts = d.departments || [];
        const deptRows = depts.map(x => {
          const pct = x.total ? Math.round(x.active * 100 / x.total) : 0;
          const col = pct >= 60 ? '#10b981' : (pct >= 30 ? '#d97706' : '#dc2626');
          return '<div class="u-dept"><div class="u-dept-lbl" title="' + escapeHtml(x.department) + '">' + escapeHtml(_deptShort(x.department)) + '</div>' +
            '<div class="u-dept-bar">' + _usageBar(pct, col) + '</div>' +
            '<div class="u-dept-cnt">' + x.active + '/' + x.total + ' <span style="color:var(--text-soft);">(' + pct + '%)</span></div></div>';
        }).join('');
        const deptBlock = '<div class="u-h" style="margin-top:12px;">🏢 부서별 활성률</div>' + (deptRows || '<div class="u-empty">부서 정보 없음</div>');
        const per = d.per_user || [];
        // 본사/베트남 책갈피로 분리 (대표 지시 2026-06-05) — 부서코드 02_VN/ 기준
        const _puIsVn = (u) => String((typeof deptSortKey === 'function' ? deptSortKey(u.department || '') : (u.department || ''))).startsWith('02_VN/');
        const _perHq = per.filter(u => !_puIsVn(u));
        const _perVn = per.filter(u => _puIsVn(u));
        const _puRowsOf = (arr) => arr.map((u, i) => {
          // 베트남 직원: '베트남어 (한국식발음)' 병기 (대표 지시 2026-06-05) — AI사용량·동의현황 표와 동일
          const _nm = (u.is_vn && u.display_name_vn) ? (u.display_name_vn + ' (' + u.display_name + ')') : u.display_name;
          return '<tr style="border-bottom:1px solid var(--border);">' +
          '<td style="padding:4px 8px;color:var(--text-soft);">' + (i + 1) + '</td>' +
          '<td style="padding:4px 8px;"><b>' + escapeHtml(_nm) + '</b><div style="font-size:10px;color:var(--text-soft);">' + escapeHtml([u.title, _deptShort(u.department)].filter(Boolean).join(' · ')) + '</div></td>' +
          '<td style="padding:4px 8px;text-align:right;">' + (u.msgs || 0).toLocaleString() + '</td>' +
          '<td style="padding:4px 8px;text-align:right;color:var(--text-soft);">' + (u.files || 0).toLocaleString() + '</td>' +
          '<td style="padding:4px 8px;text-align:right;font-weight:700;">' + (u.total || 0).toLocaleString() + '</td>' +
          '<td style="padding:4px 8px;text-align:right;color:var(--text-soft);font-size:10px;">' + escapeHtml(u.last_at || '') + '</td></tr>';
        }).join('');
        const _puTable = (arr) =>
          '<div style="max-height:300px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;margin-top:6px;">' +
          '<table style="width:100%;border-collapse:collapse;font-size:calc(11px + var(--fs-add-ui));">' +
          '<thead style="position:sticky;top:0;background:var(--bg);"><tr>' +
          '<th style="padding:5px 8px;text-align:left;">#</th><th style="padding:5px 8px;text-align:left;">이름</th>' +
          '<th style="padding:5px 8px;text-align:right;">메시지</th><th style="padding:5px 8px;text-align:right;">파일</th>' +
          '<th style="padding:5px 8px;text-align:right;">합계</th><th style="padding:5px 8px;text-align:right;">마지막</th>' +
          '</tr></thead><tbody>' + (_puRowsOf(arr) || '<tr><td colspan="6" style="padding:12px;text-align:center;color:var(--text-soft);">없음</td></tr>') + '</tbody></table></div>';
        const _puTabBtn = (key, label, n, active) =>
          '<button type="button" class="upu-tab" data-upu="' + key + '" style="flex:1;padding:6px 8px;font-size:calc(12px + var(--fs-add-ui));border:1px solid ' + (active ? 'var(--accent)' : 'var(--border)') + ';border-radius:6px;cursor:pointer;font-weight:700;background:' + (active ? 'var(--accent)' : 'var(--surface)') + ';color:' + (active ? '#fff' : 'var(--text)') + ';">' + label + ' (' + n + ')</button>';
        const puBlock = '<details class="u-details"><summary>👤 개인별 상세 (' + per.length + '명 · 유지보수관리자만)</summary>' +
          '<div class="upu-tabs" style="display:flex;gap:6px;margin-top:6px;">' +
          _puTabBtn('hq', '🇰🇷 본사', _perHq.length, true) + _puTabBtn('vn', '🇻🇳 베트남', _perVn.length, false) +
          '</div>' +
          '<div class="upu-pane" data-upu-pane="hq">' + _puTable(_perHq) + '</div>' +
          '<div class="upu-pane" data-upu-pane="vn" style="display:none;">' + _puTable(_perVn) + '</div>' +
          '</details>';
        body.innerHTML = adoptCard + featBlock + deptBlock + puBlock;
        // 개인별 상세 — 본사/베트남 책갈피 전환 (대표 지시 2026-06-05)
        body.querySelectorAll('.upu-tab').forEach(tab => {
          tab.addEventListener('click', () => {
            const k = tab.dataset.upu;
            body.querySelectorAll('.upu-tab').forEach(b => {
              const on = (b.dataset.upu === k);
              b.style.background = on ? 'var(--accent)' : 'var(--surface)';
              b.style.color = on ? '#fff' : 'var(--text)';
              b.style.borderColor = on ? 'var(--accent)' : 'var(--border)';
            });
            body.querySelectorAll('.upu-pane').forEach(p => { p.style.display = (p.dataset.upuPane === k) ? '' : 'none'; });
          });
        });
      } catch (e) {
        body.innerHTML = '<div style="padding:14px;text-align:center;color:#dc2626;">불러오기 실패: ' + escapeHtml(String(e.message || e)) + '</div>';
      }
    }
    const _usageRefreshBtn = document.getElementById('usageRefreshBtn');
    if (_usageRefreshBtn) _usageRefreshBtn.addEventListener('click', _refreshUsage);
    const _usagePeriodSel = document.getElementById('usagePeriod');
    if (_usagePeriodSel) _usagePeriodSel.addEventListener('change', _refreshUsage);

    // ── 👤 운영 담당자 지정 (대표님=유지보수 owner 만) — 대표 지시 2026-06-03 ──
    let _opsAdminCache = [];
    let _opsCorp = 'hq';   // 본사/베트남법인 책갈피 (대표 지시 2026-06-05)
    function _syncOpsAdminSection() {
      const sec = document.getElementById('opsAdminSection');
      if (!sec) return;
      if (!window.__IS_MAINT_OWNER__) { sec.hidden = true; return; }
      sec.hidden = false;
      _refreshOpsAdmins();
    }
    async function _refreshOpsAdmins() {
      const list = document.getElementById('opsAdminList');
      if (!list) return;
      list.innerHTML = '<div style="padding:14px;text-align:center;color:var(--text-soft);">불러오는 중…</div>';
      try {
        const d = await fetch(`${BASE}/api/admin/ops_admins`).then(r => { if (r.status === 403) throw new Error('대표님 전용'); return r.json(); });
        _opsAdminCache = d.users || [];
        _renderOpsAdmins();
      } catch (e) {
        list.innerHTML = '<div style="padding:14px;text-align:center;color:#dc2626;">불러오기 실패: ' + escapeHtml(String(e.message || e)) + '</div>';
      }
    }
    function _renderOpsAdmins() {
      const list = document.getElementById('opsAdminList');
      const searchEl = document.getElementById('opsAdminSearch');
      if (!list) return;
      // 본사/베트남 책갈피 카운트·활성표시 (대표 지시 2026-06-05)
      const _opsIsVn = (u) => String((typeof deptSortKey === 'function' ? deptSortKey(u.department || '') : (u.department || ''))).startsWith('02_VN/');
      const _hqAll = _opsAdminCache.filter(u => !_opsIsVn(u));
      const _vnAll = _opsAdminCache.filter(u => _opsIsVn(u));
      const _cHq = document.querySelector('[data-ocorp-count="hq"]');
      const _cVn = document.querySelector('[data-ocorp-count="vn"]');
      if (_cHq) _cHq.textContent = '(' + _hqAll.length + ')';
      if (_cVn) _cVn.textContent = '(' + _vnAll.length + ')';
      document.querySelectorAll('.ops-corp-tab').forEach(b => {
        const on = (b.dataset.corp === _opsCorp);
        b.style.background = on ? 'var(--accent)' : 'var(--surface)';
        b.style.color = on ? '#fff' : 'var(--text)';
        b.style.borderColor = on ? 'var(--accent)' : 'var(--border)';
      });
      const q = ((searchEl && searchEl.value) || '').trim().toLowerCase();
      let users = (_opsCorp === 'vn') ? _vnAll : _hqAll;
      if (q) users = users.filter(u => ((u.display_name || '') + ' ' + (u.department || '') + ' ' + (u.title || '')).toLowerCase().indexOf(q) >= 0);
      if (!users.length) { list.innerHTML = '<div style="padding:14px;text-align:center;color:var(--text-soft);">' + (q ? '검색 결과 없음' : '해당 법인 직원이 없습니다.') + '</div>'; return; }
      list.innerHTML = users.map(u => {
        const meta = [u.title, _deptShort(u.department)].filter(Boolean).join(' · ');
        // 베트남 직원: '베트남어 (한국식발음)' 병기 (대표 지시 2026-06-05)
        const _nm = (u.is_vn && u.display_name_vn) ? (u.display_name_vn + ' (' + u.display_name + ')') : u.display_name;
        if (u.is_owner) {
          return '<div class="ops-row"><div class="ops-info"><b>' + escapeHtml(_nm) + '</b> <span class="ops-owner">대표님</span><div class="ops-meta">' + escapeHtml(meta) + '</div></div><span style="font-size:11px;color:var(--text-soft);flex-shrink:0;">항상 활성</span></div>';
        }
        const on = u.ops_allowed === 1;
        return '<div class="ops-row"><div class="ops-info"><b>' + escapeHtml(_nm) + '</b>' + (on ? ' <span class="ops-on">운영</span>' : '') + '<div class="ops-meta">' + escapeHtml(meta) + '</div></div>' +
          '<button type="button" class="ops-toggle' + (on ? ' on' : '') + '" data-uid="' + u.user_id + '" data-on="' + (on ? '1' : '0') + '">' + (on ? '해제' : '운영 부여') + '</button></div>';
      }).join('');
      list.querySelectorAll('.ops-toggle').forEach(btn => {
        btn.addEventListener('click', async function () {
          const uid = this.getAttribute('data-uid');
          const cur = this.getAttribute('data-on') === '1';
          const next = cur ? 0 : 1;
          if (next === 1 && !confirm(window.KNK_t("confirm.grantOpsRole","이 직원에게 운영 권한을 부여합니다.\n대표님이 보는 유지보수 화면(사용 현황·버그 관리·시스템 설정)을 똑같이 보게 됩니다. 진행할까요?"))) return;
          this.disabled = true;
          try {
            const r = await fetch(`${BASE}/api/admin/ops_admins/${uid}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ allowed: next }) });
            const dd = await r.json().catch(() => ({}));
            if (!r.ok || dd.error) throw new Error(dd.error || '실패');
            const tu = _opsAdminCache.find(x => String(x.user_id) === String(uid));
            if (tu) tu.ops_allowed = next;
            _renderOpsAdmins();
          } catch (e) { alert(window.KNK_t("alert.changeFail","변경 실패") + ": " + (e.message || e)); this.disabled = false; }
        });
      });
    }
    const _opsAdminSearchEl = document.getElementById('opsAdminSearch');
    if (_opsAdminSearchEl) _opsAdminSearchEl.addEventListener('input', _renderOpsAdmins);
    // 본사/베트남법인 책갈피 전환 (대표 지시 2026-06-05)
    document.querySelectorAll('.ops-corp-tab').forEach(b => {
      b.addEventListener('click', () => { _opsCorp = b.dataset.corp; _renderOpsAdmins(); });
    });

    // ── 🔧 시스템 설정 토글 상태 로딩 (유지보수 전용) — 권한→유지보수 이동 (대표 지시 2026-06-03) ──
    //   토글 4종(번역ON/OFF·상태표시·AI모델·WORKS)이 🔧유지보수로 옮겨오며, 상태 로딩을
    //   ceo 전용 권한표(_refreshPermUI)와 분리해 운영자도 정상 표시되게 함.
    function _syncSysConfigSection() {
      const sec = document.getElementById('sysConfigSection');
      if (!sec) return;
      if (!window.__IS_MAINTENANCE__) { sec.hidden = true; return; }
      sec.hidden = false;
      _loadSysConfig();
    }
    async function _loadSysConfig() {
      try {
        const d = await fetch(`${BASE}/api/admin/system_config`).then(r => r.ok ? r.json() : {});
        const tr = document.getElementById('aiTranslateToggle');
        if (tr) tr.checked = !!d.translate_enabled;
        const pd = document.getElementById('presenceDetailToggle');
        if (pd) pd.checked = !!d.presence_detail;
        const mi = document.getElementById('aiModelInput');
        if (mi) {
          mi.value = d.ai_model || '';
          const locked = !!d.ai_model_locked;
          mi.disabled = locked;
          const sb = document.getElementById('aiModelSaveBtn');
          if (sb) sb.disabled = locked;
          const res = document.getElementById('aiModelResult');
          if (res) { res.textContent = locked ? '서버 환경변수로 고정됨 (화면에서 변경 불가)' : ''; res.style.color = 'var(--text-soft)'; }
        }
        const wh = document.getElementById('worksHistToggle');
        if (wh) {
          wh.checked = !!d.works_history_sync;
          const urlSet = !!d.works_history_url_set;
          const whs = document.getElementById('worksHistStatus');
          if (whs) {
            whs.textContent = urlSet ? (wh.checked ? '✅ 전송 동작 중 (WORKS 주소 설정됨)' : '⏸ 꺼짐') : '⚠ WORKS 수신 주소 미설정 — 01세션 연동 후 동작 (지금은 켜도 전송 안 함)';
            whs.style.color = (urlSet && wh.checked) ? '#10B981' : 'var(--text-soft)';
          }
        }
      } catch (e) {}
    }
    // ── 🔐 권한 통합 표 (관리자 전용) — 채널·WORKS·AI 요약 한 곳에서 (대표 지시 2026-05-31 재편) ──
    //   3개 엔드포인트(channel_permissions / ai_permissions / users)를 id 로 병합해 한 줄에 3칸으로 표시.
    //   토글: 채널 POST /api/admin/channel_permissions/<id> · AI POST /api/admin/ai_permissions/<id> · WORKS PATCH /api/users/<id>.
    let _permAllUsers = [];  // 병합된 전체 직원 캐시 (검색용)
    let _permCorp = "hq";    // 법인 책갈피: 'hq' 본사 | 'vn' 베트남법인 (대표 지시 2026-05-31)
    // 본사/VN 판정 — 사용자 탭과 동일 기준(부서 정렬키가 02_VN/ 으로 시작하면 베트남)
    const _permIsVN = (u) => (typeof deptSortKey === "function" ? deptSortKey(u.department || "") : "").indexOf("02_VN/") === 0;
    const _permGroup = () => _permAllUsers.filter(u => _permCorp === "vn" ? _permIsVN(u) : !_permIsVN(u));
    function _updatePermCount() {
      const countEl = document.getElementById("permCount");
      if (!countEl) return;
      const g = _permGroup();
      const tot = g.length;
      const chan = g.filter(u => u.by_title === 1 || u.channel_create_allowed === 1).length;
      const works = g.filter(u => u.works_access === 1 || u.works_access === true).length;
      const ai = g.filter(u => u.ai_summary_allowed === 1).length;
      countEl.textContent = `채널 ${chan} · WORKS ${works} · AI ${ai} / 전체 ${tot}`;
    }
    function _renderPermList(filter) {
      const wrap = document.getElementById("permList");
      if (!wrap) return;
      const f = (filter || "").trim().toLowerCase();
      const users = _permGroup().filter(u => {
        if (!f) return true;
        const hay = `${u.display_name || ""} ${u.display_name_vn || ""} ${u.display_name_en || ""} ${u.title || ""} ${u.department || ""} ${u.username || ""}`.toLowerCase();
        return hay.includes(f);
      });
      const ceoMark = (u) => u.role === "ceo" ? `<span style="font-size:10px;color:var(--accent);font-weight:700;margin-left:4px;">관리자</span>` : "";
      const chanCell = (u) => {
        if (u.by_title === 1) return `<span class="perm-cell perm-cell-lock" title="직급으로 항상 허용">🔒</span>`;
        return `<label class="perm-cell"><input type="checkbox" class="perm-cb-chan" data-uid="${u.id}" ${u.channel_create_allowed === 1 ? "checked" : ""}></label>`;
      };
      const worksCell = (u) => `<label class="perm-cell"><input type="checkbox" class="perm-cb-works" data-uid="${u.id}" ${(u.works_access === 1 || u.works_access === true) ? "checked" : ""}></label>`;
      const aiCell = (u) => `<label class="perm-cell"><input type="checkbox" class="perm-cb-ai" data-uid="${u.id}" ${u.ai_summary_allowed === 1 ? "checked" : ""}></label>`;
      wrap.innerHTML = users.length
        ? users.map(u => {
            const dept = u.department ? (typeof deptDisplayLabel === "function" ? deptDisplayLabel(u.department) : u.department) : "";
            const meta = [u.title, dept].filter(Boolean).join(" · ");
            // 이름 표기 = 메인 화면과 동일한 _dispName (한국어 모드: 베트남 직원 = '베트남어 (한국식)') (대표 지시 2026-05-31)
            const nm = (typeof _dispName === "function" ? _dispName(u) : "") || u.display_name || u.username;
            return `<div class="perm-row" data-uid="${u.id}">
              <span class="perm-who"><span class="perm-name">${escapeHtml(nm)}${ceoMark(u)}</span><span class="perm-meta">${escapeHtml(meta)}</span></span>
              ${chanCell(u)}${worksCell(u)}${aiCell(u)}
            </div>`;
          }).join("")
        : `<div class="dialog-hint" style="padding:14px;text-align:center;font-size:calc(12px + var(--fs-add-ui));">${f ? "검색 결과 없음" : (_permCorp === "vn" ? "베트남법인 직원이 없습니다" : "본사 직원이 없습니다")}</div>`;
      _updatePermCount();
      // 토글 핸들러 — 각 권한별 엔드포인트로
      const onChan = async (e) => {
        const cb = e.currentTarget, uid = parseInt(cb.dataset.uid, 10), allowed = cb.checked ? 1 : 0;
        try {
          const r = await fetch(`${BASE}/api/admin/channel_permissions/${uid}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ allowed }) }).then(x => x.json());
          if (r && r.ok) { const u = _permAllUsers.find(x => x.id === uid); if (u) u.channel_create_allowed = allowed; _updatePermCount(); }
          else { cb.checked = !cb.checked; alert((r && r.error) || "저장 실패"); }
        } catch (_) { cb.checked = !cb.checked; alert(window.KNK_t("alert.saveFail","저장 실패")); }
      };
      const onWorks = async (e) => {
        const cb = e.currentTarget, uid = parseInt(cb.dataset.uid, 10), val = cb.checked ? 1 : 0;
        try {
          const r = await fetch(`${BASE}/api/users/${uid}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ works_access: val }) }).then(x => x.json());
          if (r && (r.ok || r.user)) {
            const u = _permAllUsers.find(x => x.id === uid); if (u) u.works_access = val;
            const cu = Array.isArray(_usersCache) ? _usersCache.find(x => x.id === uid) : null; if (cu) cu.works_access = val;
            _updatePermCount();
          } else { cb.checked = !cb.checked; alert((r && r.error) || "저장 실패"); }
        } catch (_) { cb.checked = !cb.checked; alert(window.KNK_t("alert.saveFail","저장 실패")); }
      };
      const onAi = async (e) => {
        const cb = e.currentTarget, uid = parseInt(cb.dataset.uid, 10), allowed = cb.checked ? 1 : 0;
        try {
          const r = await fetch(`${BASE}/api/admin/ai_permissions/${uid}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ allowed }) }).then(x => x.json());
          if (r && r.ok) {
            const u = _permAllUsers.find(x => x.id === uid); if (u) u.ai_summary_allowed = allowed;
            const cu = Array.isArray(_usersCache) ? _usersCache.find(x => x.id === uid) : null; if (cu) cu.ai_summary_allowed = allowed;
            _updatePermCount();
            try { if (typeof renderUsers === "function") renderUsers(); } catch (_) {}
          } else { cb.checked = !cb.checked; alert((r && r.error) || "저장 실패"); }
        } catch (_) { cb.checked = !cb.checked; alert(window.KNK_t("alert.saveFail","저장 실패")); }
      };
      wrap.querySelectorAll(".perm-cb-chan").forEach(cb => cb.addEventListener("change", onChan));
      wrap.querySelectorAll(".perm-cb-works").forEach(cb => cb.addEventListener("change", onWorks));
      wrap.querySelectorAll(".perm-cb-ai").forEach(cb => cb.addEventListener("change", onAi));
    }
    async function _refreshPermUI() {
      const wrap = document.getElementById("permList");
      if (!wrap) return;
      try {
        const [chanData, aiData, usersArr] = await Promise.all([
          fetch(`${BASE}/api/admin/channel_permissions`).then(r => r.ok ? r.json() : { users: [] }).catch(() => ({ users: [] })),
          fetch(`${BASE}/api/admin/ai_permissions`).then(r => r.ok ? r.json() : { users: [] }).catch(() => ({ users: [] })),
          fetch(`${BASE}/api/users`).then(r => r.ok ? r.json() : []).catch(() => []),
        ]);
        const trToggle = document.getElementById("aiTranslateToggle");
        if (trToggle) trToggle.checked = !!(aiData && aiData.translate_enabled);
        // 상태표시 상세 토글 상태 반영 (대표 지시 2026-06-01)
        const pdToggle = document.getElementById("presenceDetailToggle");
        if (pdToggle) pdToggle.checked = !!(aiData && aiData.presence_detail);
        // AI 모델 현재값 반영 + 환경변수 잠금 처리 (대표 지시 2026-06-01)
        const _aiMi = document.getElementById("aiModelInput");
        if (_aiMi) {
          _aiMi.value = (aiData && aiData.ai_model) ? aiData.ai_model : "";
          const _locked = !!(aiData && aiData.ai_model_locked);
          _aiMi.disabled = _locked;
          const _aiSb = document.getElementById("aiModelSaveBtn");
          if (_aiSb) _aiSb.disabled = _locked;
          const _aiRes = document.getElementById("aiModelResult");
          if (_aiRes) {
            if (_locked) { _aiRes.textContent = "서버 환경변수로 고정됨 (화면에서 변경 불가)"; _aiRes.style.color = "var(--text-soft)"; }
            else { _aiRes.textContent = ""; }
          }
        }
        // WORKS 이력 자동전송 토글 상태 (대표 지시 2026-06-01)
        const _whT = document.getElementById("worksHistToggle");
        if (_whT) {
          _whT.checked = !!(aiData && aiData.works_history_sync);
          const _urlSet = !!(aiData && aiData.works_history_url_set);
          const _whS = document.getElementById("worksHistStatus");
          if (_whS) {
            _whS.textContent = _urlSet
              ? (_whT.checked ? "✅ 전송 동작 중 (WORKS 주소 설정됨)" : "⏸ 꺼짐")
              : "⚠ WORKS 수신 주소 미설정 — 01세션 연동 후 동작 (지금은 켜도 전송 안 함)";
            _whS.style.color = (_urlSet && _whT.checked) ? "#10B981" : "var(--text-soft)";
          }
        }
        const aiMap = {}; ((aiData && aiData.users) || []).forEach(u => { aiMap[u.id] = u; });
        const worksMap = {}; (Array.isArray(usersArr) ? usersArr : []).forEach(u => { worksMap[u.id] = u; });
        let base = (chanData && chanData.users) || [];
        if (!base.length) {
          // 폴백: 채널 엔드포인트가 비면 /api/users(비게스트) 로
          base = (Array.isArray(usersArr) ? usersArr : []).filter(u => !(u.is_guest === 1 || u.is_guest === true) && u.username !== "_deleted_user");
        }
        _permAllUsers = base.map(u => {
          const a = aiMap[u.id], w = worksMap[u.id];
          return Object.assign({}, u, {
            ai_summary_allowed: a ? (a.ai_summary_allowed === 1 ? 1 : 0) : (u.ai_summary_allowed === 1 ? 1 : 0),
            works_access: w ? ((w.works_access === 1 || w.works_access === true) ? 1 : 0) : ((u.works_access === 1 || u.works_access === true) ? 1 : 0),
            // 이름 3종(한국식·베트남어·영문)은 /api/users 응답에서 보강 → _dispName 병기용 (대표 지시 2026-05-31)
            display_name: (w && w.display_name) ? w.display_name : u.display_name,
            display_name_vn: (w && w.display_name_vn != null) ? w.display_name_vn : u.display_name_vn,
            display_name_en: (w && w.display_name_en != null) ? w.display_name_en : u.display_name_en,
          });
        });
        const s = document.getElementById("permSearch");
        _renderPermList(s ? s.value : "");
      } catch (e) {
        wrap.innerHTML = `<div class="dialog-hint" style="padding:14px;color:var(--accent);text-align:center;font-size:calc(12px + var(--fs-add-ui));">로드 실패: ${escapeHtml(String(e))}</div>`;
      }
    }
    function _syncPermSection() {
      // 권한 서브탭은 관리자(ceo) 전용 (관리자 책갈피 자체가 ceo 전용이라 이중 안전망)
      if (window._meRole !== "ceo") return;
      _refreshPermUI();
    }
    window._syncPermSection = _syncPermSection;  // 위 init 에서 호출
    // 통합 권한 표 검색
    const _permSearch = document.getElementById("permSearch");
    if (_permSearch) {
      _permSearch.addEventListener("input", () => { _renderPermList(_permSearch.value); });
    }
    // 🇰🇷/🇻🇳 법인 책갈피 — 본사 / 베트남법인 전환 (대표 지시 2026-05-31)
    const _permCorpTabs = document.getElementById("permCorpTabs");
    if (_permCorpTabs) {
      _permCorpTabs.querySelectorAll(".perm-corp-tab").forEach(btn => {
        btn.addEventListener("click", () => {
          _permCorp = (btn.dataset.corp === "vn") ? "vn" : "hq";
          _permCorpTabs.querySelectorAll(".perm-corp-tab").forEach(b => b.classList.toggle("active", b === btn));
          _renderPermList(_permSearch ? _permSearch.value : "");
        });
      });
    }
    // 번역 토글 이벤트
    const _aiTrToggle = document.getElementById("aiTranslateToggle");
    if (_aiTrToggle) {
      _aiTrToggle.addEventListener("change", async () => {
        const en = _aiTrToggle.checked ? 1 : 0;
        try {
          const r = await fetch(`${BASE}/api/admin/ai_translate_toggle`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled: en }),
          }).then(x => x.json());
          if (!(r && r.ok)) {
            _aiTrToggle.checked = !_aiTrToggle.checked;
            alert((r && r.error) || "저장 실패");
          }
        } catch (e) {
          _aiTrToggle.checked = !_aiTrToggle.checked;
          alert(window.KNK_t("alert.saveFail","저장 실패"));
        }
      });
    }
    // 상태표시 상세(기기·회사망) 토글 — 대표 지시 2026-06-01
    const _pdToggle = document.getElementById("presenceDetailToggle");
    if (_pdToggle) {
      _pdToggle.addEventListener("change", async () => {
        const en = _pdToggle.checked ? 1 : 0;
        try {
          const r = await fetch(`${BASE}/api/admin/presence_detail_toggle`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled: en }),
          }).then(x => x.json());
          if (r && r.ok) {
            // 본인 화면 즉시 반영 (다른 클라이언트는 서버 broadcast 가 처리)
            window._presenceDetail = (en === 1);
            try { if (typeof renderUserList === "function") renderUserList(); } catch(e2) {}
            try { if (typeof renderRoomList === "function") renderRoomList(); } catch(e2) {}
            try { _refreshMsgAvatars(); } catch(e2) {}
            try { _refreshPickerAvatars(); } catch(e2) {}
            try { const _me = _userStatusMap[meId]; if (_me) _renderMyStatusBadge(_me); } catch(e2) {}
          } else {
            _pdToggle.checked = !_pdToggle.checked;
            alert((r && r.error) || "저장 실패");
          }
        } catch (e) {
          _pdToggle.checked = !_pdToggle.checked;
          alert(window.KNK_t("alert.saveFail","저장 실패"));
        }
      });
    }
    // 🤖 AI 모델 — 연결 테스트 + 저장 (대표 지시 2026-06-01, 가이드 §3)
    const _aiModelInput = document.getElementById("aiModelInput");
    const _aiModelTestBtn = document.getElementById("aiModelTestBtn");
    const _aiModelSaveBtn = document.getElementById("aiModelSaveBtn");
    const _aiModelResult = document.getElementById("aiModelResult");
    function _setAiModelResult(txt, color) {
      if (_aiModelResult) { _aiModelResult.textContent = txt; _aiModelResult.style.color = color || "var(--text)"; }
    }
    if (_aiModelTestBtn) {
      _aiModelTestBtn.addEventListener("click", async () => {
        const model = (_aiModelInput && _aiModelInput.value.trim()) || "";
        _setAiModelResult("⏳ 연결 테스트 중...", "var(--text-soft)");
        _aiModelTestBtn.disabled = true;
        try {
          const r = await fetch(`${BASE}/api/admin/ai_model/test`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ model }),
          }).then(x => x.json());
          if (r && r.ok) _setAiModelResult(`✅ 정상 · 모델 ${r.model} · 응답 "${r.answer || ""}"`, "#10B981");
          else _setAiModelResult(`❌ 실패 · ${(r && r.error) || "알 수 없는 오류"}`, "#EF4444");
        } catch (e) {
          _setAiModelResult(`❌ 실패 · ${String(e)}`, "#EF4444");
        } finally {
          _aiModelTestBtn.disabled = false;
        }
      });
    }
    if (_aiModelSaveBtn) {
      _aiModelSaveBtn.addEventListener("click", async () => {
        const model = (_aiModelInput && _aiModelInput.value.trim()) || "";
        if (!model) { _setAiModelResult("모델 이름을 입력하세요.", "#EF4444"); return; }
        _aiModelSaveBtn.disabled = true;
        try {
          const r = await fetch(`${BASE}/api/admin/ai_model`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ model }),
          }).then(x => x.json());
          if (r && r.ok) _setAiModelResult(`💾 저장됨 · 현재 모델 ${r.model} — 꼭 '연결 테스트'로 확인하세요`, "#10B981");
          else _setAiModelResult(`저장 실패 · ${(r && r.error) || ""}`, "#EF4444");
        } catch (e) {
          _setAiModelResult(`저장 실패 · ${String(e)}`, "#EF4444");
        } finally {
          _aiModelSaveBtn.disabled = false;
        }
      });
    }
    // 📤 WORKS 이력 자동전송 토글 (대표 지시 2026-06-01)
    const _worksHistToggle = document.getElementById("worksHistToggle");
    if (_worksHistToggle) {
      _worksHistToggle.addEventListener("change", async () => {
        const en = _worksHistToggle.checked ? 1 : 0;
        const _whS = document.getElementById("worksHistStatus");
        try {
          const r = await fetch(`${BASE}/api/admin/works_history_toggle`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled: en }),
          }).then(x => x.json());
          if (r && r.ok) {
            if (_whS) {
              if (!r.url_set) { _whS.textContent = "⚠ WORKS 수신 주소 미설정 — 01세션 연동 후 동작 (지금은 켜도 전송 안 함)"; _whS.style.color = "var(--text-soft)"; }
              else if (r.effective) { _whS.textContent = "✅ 전송 동작 중"; _whS.style.color = "#10B981"; }
              else { _whS.textContent = "⏸ 꺼짐"; _whS.style.color = "var(--text-soft)"; }
            }
          } else {
            _worksHistToggle.checked = !_worksHistToggle.checked;
            alert((r && r.error) || "저장 실패");
          }
        } catch (e) {
          _worksHistToggle.checked = !_worksHistToggle.checked;
          alert(window.KNK_t("alert.saveFail","저장 실패"));
        }
      });
    }
    const _aiUsageExportBtn = document.getElementById('aiUsageExportBtn');
    if (_aiUsageExportBtn) _aiUsageExportBtn.addEventListener('click', () => {
      const period = _aiUsagePeriod ? _aiUsagePeriod.value : 'this_month';
      const dept = _aiUsageDept ? _aiUsageDept.value : 'all';
      const url = `${BASE}/api/admin/translate_usage/export?period=${encodeURIComponent(period)}&dept=${encodeURIComponent(dept)}`;
      window.open(url, '_blank');
    });
    // 📨 푸시 테스트 버튼 — 서버가 자기 자신에게 push 발송
    const _pushTestBtn = document.getElementById('nsPushTestBtn');
    const _pushResult = document.getElementById('nsPushResult');
    if (_pushTestBtn) {
      _pushTestBtn.addEventListener('click', async () => {
        _pushTestBtn.disabled = true;
        if (_pushResult) { _pushResult.textContent = '📨 발송 중...'; _pushResult.style.color = ''; }
        try {
          const r = await fetch(BASE + "/api/push/test", { method: "POST" });
          const data = await r.json();
          if (_pushResult) {
            const total = data.total_subscriptions || 0;
            if (data.sent > 0) {
              _pushResult.innerHTML = `✅ 서버가 ${data.sent}/${total} 구독지로 푸시 발송 완료. <strong>잠시 후 OS 알림 도착해야 정상</strong>.`;
              _pushResult.style.color = '#10B981';
            } else if (total === 0) {
              _pushResult.innerHTML = `❌ 푸시 발송 실패 — 등록된 구독 0개. "🔄 푸시 재구독" 먼저 누르세요.`;
              _pushResult.style.color = '#A5282C';
            } else {
              // 구독은 있는데 전부 실패한 경우 — 에러 원인을 textarea 에 표시 + 자동 클립보드 복사
              const errLines = (data.errors || []).map(e => `#${e.id || '?'}: ${e.error || ''}`).join('\n');
              const full = `KNK 푸시 진단 — 등록 구독 ${total}개 전부 발송 실패\n발송 성공: ${data.sent}\n시각: ${new Date().toISOString()}\n\n--- 실패 원인 ---\n${errLines}`;
              _pushResult.innerHTML = `
                <div style="color:#A5282C;margin-bottom:6px;"><strong>❌ ${total}개 구독 전부 발송 실패</strong></div>
                <textarea readonly id="nsPushErrBox"
                  style="width:100%;height:140px;font-family:monospace;font-size:10px;line-height:1.4;
                         padding:6px 8px;border:1px solid #FCA5A5;border-radius:6px;background:#FEF2F2;color:#1F2937;
                         user-select:text;-webkit-user-select:text;resize:vertical;"
                  onclick="this.select()"></textarea>
                <div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;">
                  <button type="button" id="nsCopyErrBtn" class="ns-preview-btn">📋 클립보드 복사</button>
                  <span id="nsCopyStatus" style="font-size:calc(11px + var(--fs-add-ui));color:var(--text-soft);align-self:center;"></span>
                </div>
              `;
              const $errBox = document.getElementById('nsPushErrBox');
              if ($errBox) $errBox.value = full;
              const $copyBtn = document.getElementById('nsCopyErrBtn');
              const $copyStatus = document.getElementById('nsCopyStatus');
              const doCopy = async () => {
                try {
                  await navigator.clipboard.writeText(full);
                  if ($copyStatus) { $copyStatus.textContent = '✅ 복사됨!'; $copyStatus.style.color = '#10B981'; }
                } catch (e) {
                  // Fallback — execCommand
                  try {
                    if ($errBox) {
                      $errBox.focus(); $errBox.select();
                      const ok = document.execCommand('copy');
                      if ($copyStatus) {
                        $copyStatus.textContent = ok ? '✅ 복사됨!' : '⚠️ textarea 텍스트 위 길게 눌러 복사하세요';
                        $copyStatus.style.color = ok ? '#10B981' : '#A5282C';
                      }
                    }
                  } catch (e2) {
                    if ($copyStatus) {
                      $copyStatus.textContent = '⚠️ 자동 복사 실패 — textarea 텍스트 길게 눌러 직접 복사';
                      $copyStatus.style.color = '#A5282C';
                    }
                  }
                }
              };
              if ($copyBtn) $copyBtn.addEventListener('click', doCopy);
              // 자동 1회 복사 시도 (HTTPS + 사용자 제스처 직후라 보통 OK)
              await doCopy();
            }
          }
        } catch (e) {
          if (_pushResult) {
            _pushResult.textContent = '❌ API 호출 실패: ' + e.message;
            _pushResult.style.color = '#A5282C';
          }
        } finally {
          _pushTestBtn.disabled = false;
        }
      });
    }
    // 💬 실제 수신 시뮬레이션 — 다른 사람이 보낸 것처럼 (똑똑한 억제 로직 적용)
    const _pushSimBtn = document.getElementById('nsPushSimBtn');
    if (_pushSimBtn) {
      _pushSimBtn.addEventListener('click', async () => {
        _pushSimBtn.disabled = true;
        if (_pushResult) { _pushResult.textContent = '💬 시뮬레이션 발송 중...'; _pushResult.style.color = ''; }
        try {
          const r = await fetch(BASE + "/api/push/test_simulate", { method: "POST" });
          const data = await r.json();
          if (_pushResult) {
            if (data.skipped && data.pc_active) {
              _pushResult.innerHTML = `🖥️ <strong>PC 활성 감지 → 모바일 푸시 스킵 (똑똑한 억제 정상)</strong><br>
                <span style="font-size:calc(11px + var(--fs-add-ui));color:var(--text-soft);">${data.message}</span>`;
              _pushResult.style.color = '#F59E0B';
            } else if (data.sent > 0) {
              _pushResult.innerHTML = `✅ <strong>시뮬레이션 푸시 발송 성공 (${data.sent}개)</strong><br>
                <span style="font-size:calc(11px + var(--fs-add-ui));color:var(--text-soft);">잠시 후 휴대폰(백그라운드/화면 꺼짐)에 알림이 와야 정상입니다.</span>`;
              _pushResult.style.color = '#10B981';
            } else {
              _pushResult.innerHTML = `⚠️ 발송 0개 — 등록 구독 ${data.total_subscriptions || 0}개. 재구독 필요할 수 있음.`;
              _pushResult.style.color = '#A5282C';
            }
          }
        } catch (e) {
          if (_pushResult) { _pushResult.textContent = '❌ 시뮬레이션 실패: ' + e.message; _pushResult.style.color = '#A5282C'; }
        } finally {
          _pushSimBtn.disabled = false;
        }
      });
    }
    // 🔄 푸시 재구독 버튼 — 기존 구독 취소 후 새로 등록
    const _pushResubBtn = document.getElementById('nsPushResubBtn');
    if (_pushResubBtn) {
      _pushResubBtn.addEventListener('click', async () => {
        _pushResubBtn.disabled = true;
        if (_pushResult) { _pushResult.textContent = '🔄 재구독 중...'; _pushResult.style.color = ''; }
        const result = await setupWebPush({ forceResubscribe: true });
        if (_pushResult) {
          if (result.ok) {
            const cntInfo = typeof result.serverCount === 'number'
              ? ` 서버 DB 구독 수: <strong>${result.serverCount}</strong>` : '';
            if (result.serverCount === 0) {
              _pushResult.innerHTML = `⚠️ 재구독 응답은 받았지만 서버 DB 에 저장 0개. INSERT 실패 의심.${cntInfo}`;
              _pushResult.style.color = '#A5282C';
            } else {
              _pushResult.innerHTML = `✅ 푸시 재구독 성공!${cntInfo} 이제 📨 테스트 버튼 누르세요.`;
              _pushResult.style.color = '#10B981';
            }
          } else {
            _pushResult.innerHTML = `❌ 재구독 실패: ${result.reason}`;
            _pushResult.style.color = '#A5282C';
          }
        }
        refreshPushDiagnostic();
        _pushResubBtn.disabled = false;
      });
    }
    // 체크박스·셀렉트 → settings 즉시 저장
    const wireToggle = (id, key) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.addEventListener('change', async () => {
        notifySettings.set(key, el.checked);
        // 시스템 알림 켰을 때 권한 없으면 요청
        if (key === 'systemNotification' && el.checked) {
          await notify.ensurePermission();
        }
      });
    };
    wireToggle('nsSound', 'soundEnabled');
    wireToggle('nsCurrentRoomSound', 'currentRoomSound');
    wireToggle('nsSystem', 'systemNotification');
    // nsTitleBlink·nsInlineToast·nsSidebarBlink 제거됨 (2026-05-26) — 실효성 없음
    wireToggle('nsHidePreview', 'hidePreview');   // 🔒 알림 내용 숨기기 — 시스템 알림 'KNK message' 로만 (대표 지시 2026-05-26)
    // 추가로 서버에도 동기화 — 잠금화면 푸시 페이로드를 서버가 가려서 보내기 위함
    const _nsHideEl = document.getElementById('nsHidePreview');
    if (_nsHideEl) {
      _nsHideEl.addEventListener('change', () => {
        fetch(BASE + '/api/me/push_hide_preview', {
          method: 'PUT', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ hide: !!_nsHideEl.checked }),
        }).catch(() => {});
      });
    }
    // 음량 슬라이더
    const _vol = document.getElementById('nsVolume');
    const _volPct = document.getElementById('nsVolumePct');
    if (_vol) {
      _vol.addEventListener('input', () => {
        notifySettings.set('volume', parseInt(_vol.value, 10) / 100);
        if (_volPct) _volPct.textContent = _vol.value + '%';
      });
    }
    // 사운드 종류
    const _st = document.getElementById('nsSoundType');
    if (_st) {
      _st.addEventListener('change', () => {
        notifySettings.set('soundType', _st.value);
      });
    }
    // 미리듣기 — playSound 가 내부적으로 Web Audio + HTMLAudio fallback 둘 다 처리.
    // 진단 결과를 다이얼로그 위쪽 큰 박스 + alert 로 표시 (어떤 모바일에서도 보이게).
    const _preview = document.getElementById('nsSoundPreview');
    if (_preview) {
      _preview.addEventListener('click', async () => {
        // 클릭 시점에 select 값을 강제로 settings 에 다시 저장 (change 이벤트 누락 보호)
        const _stEl = document.getElementById('nsSoundType');
        if (_stEl && _stEl.value) notifySettings.set('soundType', _stEl.value);
        // 재생 시도
        await notify.preview();
        const ctx = notify.getAudioState ? notify.getAudioState() : null;
        const vol = Math.round((notifySettings.get('volume') || 0) * 100);
        const selVal = _stEl ? (_stEl.value || '?') : '?';
        const stgVal = notifySettings.get('soundType') || '?';
        const match = selVal === stgVal ? '일치' : '불일치';
        // 진단 박스 — ns-section (사운드 섹션 전체) 의 마지막에 별도 행으로 추가
        const $section = _preview.closest('.ns-section') || _preview.parentElement;
        let marker = document.getElementById('nsSoundDebug');
        if (!marker) {
          marker = document.createElement('div');
          marker.id = 'nsSoundDebug';
          marker.style.cssText = 'display:block;margin-top:10px;padding:10px 12px;background:#FEF2F2;border:2px solid #A5282C;border-radius:8px;font-size:calc(13px + var(--fs-add-ui));line-height:1.6;font-family:monospace;color:#1F2937;width:100%;clear:both;';
          $section.appendChild(marker);
        }
        const lines = [
          `<strong style="color:#A5282C;">🔊 ${stgVal} · ${vol}%</strong>`,
          `<span style="color:var(--text-soft);font-size:calc(11px + var(--fs-add-ui));">Web Audio: ${ctx ? ctx.state : '없음'} · select/settings ${match}</span>`,
        ];
        marker.innerHTML = lines.join('<br>');
        marker.style.cssText = 'display:block;margin-top:8px;padding:6px 10px;background:#FEF2F2;border:1px solid #FCA5A5;border-radius:6px;font-size:calc(12px + var(--fs-add-ui));line-height:1.5;color:#1F2937;width:100%;';
        // 3초 후 자동 사라짐
        clearTimeout(marker._fadeTimer);
        marker.style.opacity = '1';
        marker._fadeTimer = setTimeout(() => {
          marker.style.transition = 'opacity 0.5s';
          marker.style.opacity = '0';
        }, 3000);
      });
    }
  }

  setupDropzone();

  // ====== 🔒 화면 잠금 (자리 비움 자동 잠금) — 이 기기에만 적용 ======
  //  설정은 localStorage: timeoutMin 0=미적용 / cred 있으면 지문·얼굴 등록됨.
  //  로그인 세션은 유지하고 화면만 가림. 해제 = 비밀번호(서버 확인) 또는 지문·얼굴(WebAuthn, 기기 보안).
  const LK_KEY = { timeout: "knkmsg.lock.timeoutMin", cred: "knkmsg.lock.credId" };
  let _lkLocked = false;
  let _lkLast = Date.now();

  function lkTimeoutMin() { return parseInt(localStorage.getItem(LK_KEY.timeout) || "0", 10) || 0; }
  function lkEnabled() { return lkTimeoutMin() > 0; }
  function lkHasBio() { return !!localStorage.getItem(LK_KEY.cred); }

  function _lkB64ToBuf(b64) {
    const bin = atob(String(b64).replace(/-/g, "+").replace(/_/g, "/"));
    const arr = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
    return arr.buffer;
  }
  function _lkBufToB64(buf) {
    const bytes = new Uint8Array(buf);
    let s = "";
    for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
    return btoa(s);
  }
  async function _lkBioAvailable() {
    try {
      if (!window.PublicKeyCredential || !window.isSecureContext) return false;
      if (!PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable) return false;
      return await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
    } catch (e) { return false; }
  }

  function _lkMark() { _lkLast = Date.now(); }
  function _lkCheckIdle() {
    if (_lkLocked || !lkEnabled()) return;
    if (Date.now() - _lkLast >= lkTimeoutMin() * 60000) lockScreen();
  }

  function lockScreen() {
    if (_lkLocked) return;
    const ov = document.getElementById("lockOverlay");
    if (!ov) return;
    _lkLocked = true;
    try { sessionStorage.setItem("knkmsg.lock.on", "1"); } catch (e) {}
    const err = document.getElementById("lockErr");
    if (err) { err.hidden = true; err.textContent = ""; }
    const pw = document.getElementById("lockPwInput");
    if (pw) {
      pw.value = "";
      // 잠글 때마다 가림(●) 상태 + 👁 아이콘으로 초기화 (이전에 '보기'로 열어뒀어도)
      if (pw.dataset.knkFallback === "1") pw.type = "password"; else pw.classList.add("knk-masked");
      const _tg = document.querySelector('.pw-toggle[data-pw-toggle-for="lockPwInput"]');
      if (_tg) { _tg.textContent = "👁"; _tg.classList.remove("shown"); }
    }
    const bioBtn = document.getElementById("lockBioBtn");
    if (bioBtn) bioBtn.hidden = !lkHasBio();
    ov.hidden = false;
    document.body.classList.add("lk-locked");
    setTimeout(() => { try { if (pw) pw.focus(); } catch (e) {} }, 80);
  }

  function _lkDoUnlock() {
    _lkLocked = false;
    try { sessionStorage.removeItem("knkmsg.lock.on"); } catch (e) {}
    const ov = document.getElementById("lockOverlay");
    if (ov) ov.hidden = true;
    document.body.classList.remove("lk-locked");
    _lkMark();
  }

  // 반환: { ok, reason, status } — reason: ""(성공)·"empty"·"wrong"·"server"·"network"
  //  서버/네트워크 오류를 '비번 틀림'으로 오인하지 않도록 원인을 구분한다. (대표 지시 2026-06-02)
  async function _lkTryPassword(pw) {
    if (!pw) return { ok: false, reason: "empty" };
    try {
      const r = await fetch(BASE + "/api/verify_password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ password: pw }),
      });
      if (!r.ok) return { ok: false, reason: "server", status: r.status };
      const d = await r.json().catch(() => null);
      return (d && d.ok) ? { ok: true, reason: "" } : { ok: false, reason: "wrong" };
    } catch (e) { return { ok: false, reason: "network" }; }
  }

  async function _lkTryBio() {
    const idB64 = localStorage.getItem(LK_KEY.cred);
    if (!idB64) return false;
    try {
      const challenge = crypto.getRandomValues(new Uint8Array(32));
      await navigator.credentials.get({
        publicKey: {
          challenge,
          allowCredentials: [{ type: "public-key", id: _lkB64ToBuf(idB64) }],
          userVerification: "required",
          timeout: 60000,
        },
      });
      return true;   // 인증 성공(예외 없이 반환) = 기기 보안 통과
    } catch (e) { return false; }
  }

  async function _lkRegisterBio() {
    const challenge = crypto.getRandomValues(new Uint8Array(32));
    const userId = crypto.getRandomValues(new Uint8Array(16));
    const uname = (window.MY_USERNAME || "knk-user");
    const cred = await navigator.credentials.create({
      publicKey: {
        challenge,
        rp: { name: "KNK 이음" },
        user: { id: userId, name: uname, displayName: uname },
        pubKeyCredParams: [{ type: "public-key", alg: -7 }, { type: "public-key", alg: -257 }],
        authenticatorSelection: { authenticatorAttachment: "platform", userVerification: "required" },
        timeout: 60000,
        attestation: "none",
      },
    });
    if (!cred || !cred.rawId) throw new Error("등록 실패");
    localStorage.setItem(LK_KEY.cred, _lkBufToB64(cred.rawId));
  }

  async function lkSyncUI() {
    const sel = document.getElementById("lkTimeout");
    if (sel) sel.value = String(lkTimeoutMin());
    const status = document.getElementById("lkBioStatus");
    const toggle = document.getElementById("lkBioToggle");
    const row = document.getElementById("lkBioRow");
    const avail = await _lkBioAvailable();
    if (row) row.style.opacity = avail ? "1" : "0.5";
    if (toggle) {
      toggle.disabled = !avail;
      toggle.textContent = lkHasBio() ? "해제" : "등록";
    }
    if (status) {
      if (!avail) status.textContent = "이 기기·브라우저는 지문·얼굴 인식을 지원하지 않습니다. 비밀번호로 잠금 해제됩니다.";
      else if (lkHasBio()) status.textContent = "지문·얼굴 등록됨 ✓ — 잠금 해제 시 사용할 수 있습니다.";
      else status.textContent = "등록하면 잠금 해제 때 지문·얼굴을 사용할 수 있습니다.";
    }
  }

  function lkInit() {
    const ov = document.getElementById("lockOverlay");
    if (!ov) return;
    // 활동 감지 → 마지막 활동 시각 갱신 (잠겨있을 땐 무시)
    ["pointerdown", "keydown", "mousemove", "touchstart", "scroll", "click", "wheel"].forEach(ev => {
      document.addEventListener(ev, () => { if (!_lkLocked) _lkMark(); }, { passive: true, capture: true });
    });
    // 주기 점검(보일 때) + 백그라운드 복귀·창 포커스 시 즉시 점검
    setInterval(_lkCheckIdle, 15000);
    document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") _lkCheckIdle(); });
    window.addEventListener("focus", _lkCheckIdle);
    // 새로고침 등으로 잠금 상태였으면 복원
    try { if (lkEnabled() && sessionStorage.getItem("knkmsg.lock.on") === "1") lockScreen(); } catch (e) {}

    // ---- 잠금 화면 조작 ----
    const pwForm = document.getElementById("lockPwForm");
    const pwInput = document.getElementById("lockPwInput");
    const errBox = document.getElementById("lockErr");
    const bioBtn = document.getElementById("lockBioBtn");
    const showErr = (msg) => { if (errBox) { errBox.textContent = msg; errBox.hidden = false; } };
    if (pwForm) pwForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const res = await _lkTryPassword(pwInput ? pwInput.value : "");
      if (res.ok) { _lkDoUnlock(); return; }
      // 오류 원인 구분 안내 — 서버·네트워크 오류를 '비번 틀림'으로 오인하지 않게
      if (res.reason === "empty") showErr("비밀번호를 입력하세요.");
      else if (res.reason === "server") showErr("서버 오류로 확인하지 못했습니다 (코드 " + (res.status || "?") + "). 잠시 후 다시 시도하세요.");
      else if (res.reason === "network") showErr("네트워크 오류로 확인하지 못했습니다. 연결을 확인하고 다시 시도하세요.");
      else { showErr("비밀번호가 올바르지 않습니다. (👁 로 입력 내용을 확인하세요)"); if (pwInput) { pwInput.value = ""; pwInput.focus(); } }
    });
    if (bioBtn) bioBtn.addEventListener("click", async () => {
      const ok = await _lkTryBio();
      if (ok) _lkDoUnlock();
      else showErr("지문·얼굴 인식에 실패했습니다. 비밀번호로 시도하세요.");
    });
    const logoutBtn = document.getElementById("lockLogoutBtn");
    if (logoutBtn) logoutBtn.addEventListener("click", () => { location.href = BASE + "/logout"; });

    // ---- 설정 조작 ----
    const sel = document.getElementById("lkTimeout");
    if (sel) sel.addEventListener("change", () => {
      localStorage.setItem(LK_KEY.timeout, String(parseInt(sel.value, 10) || 0));
      _lkMark();
    });
    const toggle = document.getElementById("lkBioToggle");
    if (toggle) toggle.addEventListener("click", async () => {
      if (lkHasBio()) { localStorage.removeItem(LK_KEY.cred); lkSyncUI(); return; }
      toggle.disabled = true;
      try {
        await _lkRegisterBio();
        alert(window.KNK_t("alert.bioRegDone","지문·얼굴 등록 완료. 이제 잠금 해제 때 사용할 수 있습니다."));
      } catch (e) {
        alert(window.KNK_t("alert.bioRegFail","지문·얼굴 등록에 실패했거나 취소되었습니다.\n(기기 보안 — Windows Hello·Touch ID·지문이 먼저 설정돼 있어야 합니다)"));
      }
      toggle.disabled = false;
      lkSyncUI();
    });
    const testBtn = document.getElementById("lkTestBtn");
    if (testBtn) testBtn.addEventListener("click", () => {
      if (!lkEnabled()) { alert(window.KNK_t("alert.pickLockTime","먼저 '자동 잠금' 시간을 선택하세요 (미적용이면 잠기지 않습니다).")); return; }
      lockScreen();
    });

    lkSyncUI();
  }

  lkInit();

  // ---------- @mention autocomplete ----------
  function setupMentionAutocomplete() {
    let popup = null;
    let activeIdx = 0;
    let matches = [];

    function close() {
      if (popup) { popup.remove(); popup = null; }
      matches = []; activeIdx = 0;
    }

    function pickCurrent() {
      if (!popup || !matches.length) return;
      const u = matches[activeIdx];
      const name = u.display_name || u.username;   // 이름으로 멘션 (이메일 X) — 대표 지시 2026-05-22
      const v = els.msgInput.value;
      const cursor = els.msgInput.selectionStart;
      const before = v.slice(0, cursor);
      const m = before.match(/(^|\s)@([\w가-힣]*)$/);   // @ 는 맨 앞/공백 뒤일 때만 (이메일 차단) — 대표 지시 2026-06-02
      if (!m) return;
      const atPos = before.length - m[2].length - 1;    // @ 위치(앞 경계 문자는 보존)
      const after = v.slice(cursor);
      els.msgInput.value = v.slice(0, atPos) + "@" + name + " " + after;
      const pos = atPos + 1 + name.length + 1;
      els.msgInput.setSelectionRange(pos, pos);
      close();
    }

    function show(list) {
      close();
      if (!list.length) return;
      matches = list;   // 방 참여 인원 '전체' 표시 — 8명 제한 제거(스크롤·방향키로 모두 접근). (대표 지시 2026-06-02)
      activeIdx = 0;
      popup = document.createElement("div");
      popup.className = "mention-popup";
      popup.innerHTML = matches.map((u, i) => {
        // 멘션 팝업도 '이름 직급 부서' (deptShortLabel: 본사 숫자없음·VN..·총괄숨김) — 대표 지시 2026-05-22
        const title = u.title || "";
        const dept = u.department ? ((typeof deptShortLabel === "function") ? deptShortLabel(u.department) : u.department) : "";
        const meta = [title, dept].filter(Boolean).join(" ");
        return `
        <div class="mention-row ${i === 0 ? 'active' : ''}" data-idx="${i}">
          <div class="avatar" style="width:22px;height:22px;font-size:calc(11px + var(--fs-add-ui));background:${u.avatar_color}">${_avatarBody(u)}</div>
          <span><b>${escapeHtml(u.display_name)}</b>${meta ? ` <small style="color:#6b7280">${escapeHtml(meta)}</small>` : ""}</span>
        </div>`;
      }).join("");
      const rect = els.msgInput.getBoundingClientRect();
      popup.style.left = rect.left + "px";
      popup.style.bottom = (window.innerHeight - rect.top + 4) + "px";
      popup.style.position = "fixed";
      document.body.appendChild(popup);
      popup.querySelectorAll(".mention-row").forEach(row => {
        row.addEventListener("mousedown", (e) => { e.preventDefault(); activeIdx = parseInt(row.dataset.idx, 10); pickCurrent(); });
      });
    }

    els.msgInput.addEventListener("input", async () => {
      const v = els.msgInput.value;
      const before = v.slice(0, els.msgInput.selectionStart);
      const m = before.match(/(^|\s)@([\w가-힣]*)$/);   // @ 는 맨 앞/공백 뒤일 때만 (이메일 차단) — 대표 지시 2026-06-02
      if (!m) { close(); return; }
      const q = m[2].toLowerCase();
      await ensureUsers();
      // 멘션 후보 = 이 방 멤버 전체(직원+게스트). (대표 지시 2026-05-30)
      //   직원 디렉터리(users)는 게스트를 제외하므로, 그것만 쓰면 직원이 게스트를 멘션할 수 없었다.
      //   → roomReadStatus.members(게스트 포함)를 출처로 삼고 디렉터리(users) 정보로 보강한다.
      //   멤버 목록이 비어있는 비정상 상황에선 옛 동작(디렉터리 전체) 유지 (안전망).
      let base;
      if (roomReadStatus && Array.isArray(roomReadStatus.members) && roomReadStatus.members.length) {
        base = roomReadStatus.members.map(mb => {
          const dir = users.find(u => u.id === mb.user_id);
          // 디렉터리에 있으면 보강(직원), 없으면(게스트) read_status 정보만으로 구성
          return dir ? Object.assign({}, mb, dir) : Object.assign({ id: mb.user_id }, mb);
        });
      } else {
        base = users;
      }
      // _deleted_user 플레이스홀더 + 비활성 사용자는 멘션 대상에서 제외 (대표 지시 2026-05-20)
      const list = base.filter(u =>
        u.id !== meId && u.username !== "_deleted_user" && u.active !== 0
      ).filter(u =>
        !q || (u.username || "").toLowerCase().includes(q) || (u.display_name || "").toLowerCase().includes(q)
      );
      list.sort((a, b) => (a.display_name || a.username || "").localeCompare(b.display_name || b.username || "", "ko"));   // 찾기 쉽게 이름순 정렬 (대표 지시 2026-06-02)
      show(list);
    });
    els.msgInput.addEventListener("keydown", (e) => {
      if (!popup) return;
      // 방향키 이동 시 선택 항목을 보이는 영역으로 스크롤 — 보이는 범위 밖도 따라가게 (대표 지시 2026-06-02)
      const _hl = () => {
        const rows = popup.querySelectorAll(".mention-row");
        rows.forEach((r, i) => r.classList.toggle("active", i === activeIdx));
        const a = rows[activeIdx];
        if (a) { try { a.scrollIntoView({ block: "nearest" }); } catch (_) {} }
      };
      if (e.key === "ArrowDown") { e.preventDefault(); activeIdx = (activeIdx + 1) % matches.length; _hl(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); activeIdx = (activeIdx - 1 + matches.length) % matches.length; _hl(); }
      else if (e.key === "Enter" || e.key === "Tab") { e.preventDefault(); pickCurrent(); }
      else if (e.key === "Escape") { close(); }
    });
    els.msgInput.addEventListener("blur", () => setTimeout(close, 150));
  }

  // ---------- Web Push ----------
  function urlBase64ToUint8Array(base64) {
    const padding = "=".repeat((4 - base64.length % 4) % 4);
    const base64Std = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
    const raw = atob(base64Std);
    const arr = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
    return arr;
  }

  // iOS(아이폰·아이패드) 감지 — iPadOS 13+ 는 MacIntel 로 위장하므로 touch 로 보정
  function _isIOS() {
    const ua = navigator.userAgent || "";
    return /iPad|iPhone|iPod/.test(ua) ||
      (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  }
  // PWA standalone(홈 화면 추가 앱) 모드 여부 — iOS 는 navigator.standalone
  function _isStandalone() {
    return (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) ||
      window.navigator.standalone === true;
  }
  // 카카오톡 등 '인앱 브라우저(웹뷰)' 감지 — PWA 설치·푸시가 막혀 있어 별도 안내가 필요. (대표 지시 2026-05-30)
  //  웨일·크롬·삼성인터넷·엣지 등 '진짜 브라우저' 는 제외(설치 배너가 정상 동작).
  function _isInAppBrowser() {
    const ua = navigator.userAgent || "";
    if (/Whale|SamsungBrowser|Edg|FxiOS|CriOS/i.test(ua)) return false;     // 진짜 브라우저
    if (/KAKAOTALK/i.test(ua)) return true;                                  // 카카오톡 (안드로이드·아이폰 공통)
    if (/\bwv\b/i.test(ua)) return true;                                     // Android System WebView (대부분의 인앱 브라우저)
    if (/(NAVER|Line\/|FBAN|FBAV|FB_IAB|Instagram|DaumApps|; ?Band)/i.test(ua)) return true;
    return false;
  }
  // 현재 UI 언어(한/베/영)로 문구 선택 — 베트남 직원·중국폰 등 다양성 대응. (대표 지시 2026-05-30)
  function _pickLang(ko, vi, en) {
    const l = window.KNK_LANG || "ko";
    return l === "vi" ? vi : (l === "en" ? en : ko);
  }
  window._isIOS = _isIOS;
  window._isStandalone = _isStandalone;
  window._isInAppBrowser = _isInAppBrowser;

  // setupWebPush — 결과 객체 반환해서 진단 가능. {ok, reason, details}
  async function setupWebPush(opts) {
    opts = opts || {};
    // 🍎 iOS 특수 — Safari 탭에서는 Web Push 불가. 홈 화면 추가 PWA 에서만 동작 (iOS 16.4+).
    if (_isIOS() && !_isStandalone()) {
      return {
        ok: false,
        ios_need_install: true,
        reason: "📲 아이폰은 '홈 화면에 추가'한 앱에서만 알림이 옵니다.\n" +
                "Safari 하단 공유(⬆️) → '홈 화면에 추가' → 추가된 KNK 아이콘으로 실행 → 다시 알림 설정하세요.",
      };
    }
    if (!("serviceWorker" in navigator)) {
      return { ok: false, reason: "이 브라우저는 Service Worker 미지원" };
    }
    if (!("PushManager" in window)) {
      const iosHint = _isIOS() ? " — 아이폰은 iOS 16.4 이상 + 홈 화면 추가 필요" : "";
      return { ok: false, reason: "이 브라우저는 Push API 미지원 (iOS Safari 16.4 미만, 일부 모바일 브라우저)" + iosHint };
    }
    try {
      const reg = await navigator.serviceWorker.ready;
      const cfg = await fetch(BASE + "/api/push/vapid_public").then(r => r.ok ? r.json() : null);
      if (!cfg) return { ok: false, reason: "서버 VAPID 키 조회 실패" };
      if (!cfg.public_key || !cfg.enabled) {
        return { ok: false, reason: "서버에 VAPID 키 미설정 (관리자 generate_vapid.py 실행 필요)" };
      }
      let sub = await reg.pushManager.getSubscription();
      if (opts.forceResubscribe && sub) {
        try { await sub.unsubscribe(); } catch (e) {}
        sub = null;
      }
      if (!sub) {
        if (Notification.permission !== "granted") {
          const p = await Notification.requestPermission();
          if (p !== "granted") return { ok: false, reason: "알림 권한 거부됨 (휴대폰 설정에서 허용 필요)" };
        }
        sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(cfg.public_key),
        });
      }
      const resp = await fetch(BASE + "/api/push/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subscription: sub.toJSON() }),
      });
      if (!resp.ok) {
        let bodyTxt = "";
        try { bodyTxt = " (" + (await resp.text()).slice(0, 200) + ")"; } catch (_) {}
        return { ok: false, reason: `서버 등록 실패: HTTP ${resp.status}${bodyTxt}` };
      }
      const body = await resp.json().catch(() => ({}));
      return {
        ok: true,
        endpoint: sub.endpoint.slice(0, 60) + "...",
        serverCount: body.subscription_count,
      };
    } catch (e) {
      console.log("Web Push 설정 실패:", e);
      return { ok: false, reason: "예외: " + (e && e.message ? e.message : String(e)) };
    }
  }
  // 외부 접근용 (다이얼로그 진단 버튼)
  window.knkSetupWebPush = setupWebPush;

  // ===== 좌/우 분리선 드래그 — 오른쪽으로만 +110px (대화방 제목 잘릴 때 펼쳐 확인). 대표 지시 2026-05-22·2026-05-26 =====
  function setupSidebarResizer() {
    const resizer = document.getElementById("sidebarResizer");
    const appEl = document.getElementById("app");
    if (!resizer || !appEl) return;
    const BASE_W = 360, MAX_EXTRA = 110;   // 360 ~ 470px (오른쪽으로만, +110px)
    const LS_KEY = "knkmsg.sidebarExtra";
    const setWidth = (extra) => {
      const e = Math.max(0, Math.min(MAX_EXTRA, Math.round(extra)));
      appEl.style.setProperty("--sidebar-width", (BASE_W + e) + "px");
      return e;
    };
    const curExtra = () => {
      const v = appEl.style.getPropertyValue("--sidebar-width")
                || getComputedStyle(appEl).getPropertyValue("--sidebar-width");
      const px2 = parseInt(v, 10) || BASE_W;
      return Math.max(0, Math.min(MAX_EXTRA, px2 - BASE_W));
    };
    // 저장값 복원
    try {
      const saved = parseInt(localStorage.getItem(LS_KEY) || "0", 10);
      if (saved > 0) setWidth(saved);
    } catch (e) {}
    let dragging = false, startX = 0, startExtra = 0;
    const clientX = (ev) => (ev.touches && ev.touches[0]) ? ev.touches[0].clientX : ev.clientX;
    const onDown = (ev) => {
      dragging = true; startX = clientX(ev); startExtra = curExtra();
      resizer.classList.add("dragging");
      document.body.style.userSelect = "none"; document.body.style.cursor = "col-resize";
      ev.preventDefault();
    };
    const onMove = (ev) => {
      if (!dragging) return;
      setWidth(startExtra + (clientX(ev) - startX));   // 오른쪽 드래그 = +extra, 왼쪽 = 줄지만 0(360px)에서 멈춤
      ev.preventDefault();
    };
    const onUp = () => {
      if (!dragging) return;
      dragging = false;
      resizer.classList.remove("dragging");
      document.body.style.userSelect = ""; document.body.style.cursor = "";
      try { localStorage.setItem(LS_KEY, String(curExtra())); } catch (e) {}
    };
    resizer.addEventListener("mousedown", onDown);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    resizer.addEventListener("touchstart", onDown, { passive: false });
    window.addEventListener("touchmove", onMove, { passive: false });
    window.addEventListener("touchend", onUp);
    // 더블클릭 → 원래 폭(360px)으로 복귀
    resizer.addEventListener("dblclick", () => {
      setWidth(0);
      try { localStorage.setItem(LS_KEY, "0"); } catch (e) {}
    });
  }

  // ========================================================================
  // 사내 메신저 이용·보안 동의서 게이트 (대표 지시 2026-06-03)
  //   · 첫 로그인 + 마지막 동의로부터 약 100일마다 / 게스트(고객사) 제외
  //   · 동의해야 사용 가능(전체 차단), '동의 안 함'=로그아웃, 끝까지 읽어야 버튼 활성
  // ========================================================================
  async function _checkConsentGate() {
    if (window._meIsGuest) return;                 // 게스트 제외
    if (SOLO_MODE) return;                          // 분리창에선 중복 표시 안 함
    let data;
    try {
      const lang = window.KNK_LANG || "ko";
      data = await fetch(`${BASE}/api/me/consent?lang=${encodeURIComponent(lang)}`).then(r => r.json());
    } catch (_) { return; }                         // API 실패 시 게이트 건너뜀(전사 락아웃 방지)
    if (!data || !data.needed) return;
    return new Promise((resolve) => { _showConsentModal(data, resolve); });
  }

  function _showConsentModal(data, onAgree) {
    const gate = document.getElementById("consentGate");
    if (!gate) { onAgree(); return; }
    const titleEl = document.getElementById("consentTitle");
    const bodyEl = document.getElementById("consentBody");
    const hintEl = document.getElementById("consentScrollHint");
    const agreeBtn = document.getElementById("consentAgreeBtn");
    const declineBtn = document.getElementById("consentDeclineBtn");
    titleEl.textContent = data.title || "";
    bodyEl.innerHTML = data.html || "";             // 서버 고정 문서(사용자 입력 아님)
    agreeBtn.textContent = data.agree_label || "동의합니다";
    declineBtn.textContent = data.decline_label || "동의 안 함";
    hintEl.textContent = data.scroll_hint || "";
    agreeBtn.disabled = true;
    hintEl.style.visibility = "";
    gate.hidden = false;
    const _enableIfRead = () => {                    // 끝까지 읽어야 동의 버튼 활성 (대표 지시)
      if ((bodyEl.scrollTop + bodyEl.clientHeight) >= (bodyEl.scrollHeight - 24)) {
        agreeBtn.disabled = false;
        hintEl.style.visibility = "hidden";
      }
    };
    bodyEl.addEventListener("scroll", _enableIfRead);
    setTimeout(() => {                               // 문서가 짧아 스크롤이 없으면 바로 활성
      if (bodyEl.scrollHeight <= bodyEl.clientHeight + 4) { agreeBtn.disabled = false; hintEl.style.visibility = "hidden"; }
    }, 80);
    agreeBtn.onclick = async () => {                 // 동의 → 기록 후 닫기 → 부팅 계속
      agreeBtn.disabled = true;
      try {
        await fetch(`${BASE}/api/me/consent`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ version: data.version }),
        });
      } catch (_) {}
      gate.hidden = true;
      try { onAgree(); } catch (_) {}
    };
    declineBtn.onclick = () => {                     // 동의 안 함 → 안내 후 로그아웃
      alert(data.declined_msg || "동의해야 메신저를 사용할 수 있습니다.");
      window.location.href = BASE + "/logout_local?r=consent_declined";
    };
  }

  // ---------- boot ----------
  (async () => {
    try { await _checkConsentGate(); } catch (e) {}   // 동의서 게이트(동의 전 차단) — 대표 지시 2026-06-03
    // 이미 접속 중이던 사용자도 '지금 바로' — 앱 화면이 다시 보일 때마다 게이트 재확인 (대표 지시 2026-06-05)
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState !== "visible") return;
      const _g = document.getElementById("consentGate");
      if (_g && !_g.hidden) return;   // 이미 떠 있으면 중복 방지
      try { _checkConsentGate(); } catch (e) {}
    });
    connectSocket();
    await ensureUsers();    // 멘션 렌더 위해 미리 로드
    await refreshRooms();
    setupMentionAutocomplete();
    refreshMentionBadge();  // 로그인 시 안 읽은 멘션 개수 배지 (대표 지시 2026-05-22)
    refreshMyTasksBadge();  // 로그인 시 받은 미완료 요청 개수 배지 (대표 지시 2026-05-23)
    setupSidebarResizer();  // 분리선 드래그(오른쪽 +50px) 활성화 (대표 지시 2026-05-22)
    setInterval(refreshRooms, 30000);

    // /chat?room=N — 대시보드에서 카드 클릭으로 진입 시 해당 방 자동 열기
    // /chat?solo=1&room=N — 더블클릭으로 띄운 단독창 (사이드바 없음, URL 유지)
    const params = new URLSearchParams(window.location.search);
    const wantRoom = parseInt(params.get("room") || "", 10);
    if (wantRoom) {
      const room = rooms.find(r => r.id === wantRoom);
      if (room) {
        // solo 모드: URL 유지(북마크/새로고침 대응), 즉시 열기
        // 일반 모드: URL 정리 후 약간 지연 열기
        if (SOLO_MODE) {
          // 단독창은 타이틀에 방 이름 노출 — 작업표시줄에서 구분
          document.title = (room.name || "대화") + " — KNK 이음";
          openRoom(room);
        } else {
          history.replaceState(null, "", BASE + "/chat");
          setTimeout(() => openRoom(room), 300);
        }
      }
    }

    // 첫 진입 시 다이제스트 자동 노출 (오늘/지연 있으면)
    // solo 모드(분리창)에서는 다이제스트 띄우지 않음 — 그 방만 보러 띄운 창
    // 게스트(고객사)는 다이제스트 사용 불가 — 자동 노출 안 함 (대표 지시 2026-05-30)
    if (!SOLO_MODE && !window._meIsGuest && !sessionStorage.getItem("digest_seen_today") && !wantRoom && !_digestDismissedToday()) {
      sessionStorage.setItem("digest_seen_today", "1");
      setTimeout(() => openDigest(true), 800);
    }
    // 로그아웃 시 이 기기 푸시 구독 해제 → '진짜 오프라인'(알림 끊김). (2026-05-20)
    try { _wireLogoutPushCleanup(); } catch (e) {}

    // 💻 PC/안드로이드 '앱으로 설치' 유도 — 독립 창 + 시작메뉴 + (창 닫아도) 알림. (2026-05-20)
    //  beforeinstallprompt 를 잡아뒀다가 배너 버튼 탭에서 prompt() 호출 (브라우저 정책상 제스처 필요).
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      window._deferredInstallPrompt = e;
      try { if (!_isStandalone() && !SOLO_MODE) _showInstallAppHint(); } catch (_) {}
    });
    window.addEventListener('appinstalled', () => {
      window._deferredInstallPrompt = null;
      try { const b = document.getElementById('installAppHint'); if (b) b.remove(); } catch (_) {}
    });

    // 알림 권한 + Web Push 자동 구독 (3초 후, 사용자 흐름 방해 X)
    //  · 안드로이드/PC: 자동 구독 OK.
    //  · 🍎 iOS: 권한 요청은 '사용자 탭(제스처)' 안에서만 허용 → 자동 호출은 실패.
    //    그래서 홈화면 PWA 인데 권한이 아직이면 '탭해서 알림 켜기' 배너로 유도.
    setTimeout(async () => {
      // 카카오톡 등 인앱 브라우저 — 설치·푸시 불가 → 못 켜는 알림 권유 대신 '브라우저로 열어 설치' 안내만. (대표 지시 2026-05-30)
      if (_isInAppBrowser() && !_isStandalone()) {
        try { _showInAppBrowserInstallGuide(); } catch (e) {}
        return;
      }
      try { await setupWebPush(); } catch (e) {}
      // 📢 회사 '알림 필수' 정책 — 알림 꺼져 있으면 상단 상시 배너 + 첫 1회 강한 모달 (대표 지시 2026-05-24)
      try { _notifPolicyEnforce(); } catch (e) {}
    }, 1800);   // 설치/안내 더 빨리 노출 (직전 3500 → 1800, 대표 지시 2026-05-31)
  })();

  // 로그아웃 시 이 기기 푸시 구독 해제. (2026-05-20 비대칭 로그아웃)
  //  · 휴대폰 로그아웃 = 서버가 모든 기기 완전 로그아웃 처리.
  //  · PC 로그아웃     = 이 PC 의 구독만 제거 (아래 sendBeacon + 서버 세션 endpoint 백업) → 휴대폰 영향 없음.
  function _wireLogoutPushCleanup() {
    document.querySelectorAll('a.logout, a[href$="/logout"]').forEach(a => {
      if (a.dataset._logoutWired === '1') return;
      a.dataset._logoutWired = '1';
      a.addEventListener('click', async (e) => {
        e.preventDefault();
        const href = a.href;
        try {
          if ('serviceWorker' in navigator && 'PushManager' in window) {
            const reg = await navigator.serviceWorker.ready;
            const sub = await reg.pushManager.getSubscription();
            if (sub) {
              const endpoint = sub.endpoint;
              // 1) 이 브라우저 구독 해제 (이후 서버 정리 실패해도 더는 알림 안 옴)
              try { await sub.unsubscribe(); } catch (e) {}
              // 2) 이 기기 구독행 삭제 요청 — 페이지가 닫혀도 전송 보장되는 sendBeacon 우선
              try {
                let beaconed = false;
                if (navigator.sendBeacon) {
                  const blob = new Blob([JSON.stringify({ endpoint })], { type: 'application/json' });
                  beaconed = navigator.sendBeacon(BASE + '/api/push/unsubscribe', blob);
                }
                if (!beaconed) {
                  await fetch(BASE + '/api/push/unsubscribe', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ endpoint }), keepalive: true,
                  });
                }
              } catch (e) {}
            }
          }
          if ('clearAppBadge' in navigator) { try { navigator.clearAppBadge(); } catch (e) {} }
        } catch (e) { /* noop */ }
        // 서버 /logout → 휴대폰이면 모든 기기 완전 로그아웃, PC면 이 PC 만 정리
        window.location.href = href;
      });
    });
  }

  // iOS Safari 탭 사용자에게 '홈 화면에 추가' 안내 배너 (1회). (2026-05-20)
  function _showIOSInstallHint() {
    if (document.getElementById("iosInstallHint")) return;
    const bar = document.createElement("div");
    bar.id = "iosInstallHint";
    bar.style.cssText = "position:fixed;left:8px;right:8px;bottom:8px;z-index:99999;" +
      "background:#1F2937;color:#fff;border-radius:12px;padding:14px 16px;" +
      "box-shadow:0 6px 24px rgba(0,0,0,0.3);font-size:calc(13px + var(--fs-add-ui));line-height:1.5;";
    bar.innerHTML =
      '<div style="display:flex;align-items:flex-start;gap:10px;">' +
        '<div style="font-size:calc(22px + var(--fs-add-ui));">📲</div>' +
        '<div style="flex:1;min-width:0;">' +
          '<div style="font-weight:700;margin-bottom:4px;">아이폰 알림 받으려면 홈 화면에 추가하세요</div>' +
          '<div style="color:#D1D5DB;font-size:calc(12px + var(--fs-add-ui));">Safari 하단 <b>공유 버튼(⬆)</b> → <b>"홈 화면에 추가"</b> → ' +
          '추가된 <b>KNK 아이콘</b>으로 실행하면 알림이 옵니다. (Safari 탭에서는 알림 불가)</div>' +
        '</div>' +
        '<button type="button" id="iosHintClose" style="background:transparent;border:0;color:var(--text-soft);' +
          'font-size:calc(20px + var(--fs-add-ui));cursor:pointer;padding:0 2px;line-height:1;">✕</button>' +
      '</div>';
    document.body.appendChild(bar);
    const close = () => { try { bar.remove(); } catch (e) {} };
    const btn = document.getElementById("iosHintClose");
    if (btn) btn.addEventListener("click", close);
    // 15초 후 자동 닫힘
    setTimeout(close, 15000);
  }

  // 🍎 iOS 홈화면 PWA 인데 알림 권한이 아직이면 '탭해서 알림 켜기' 배너. (2026-05-20)
  //  iOS 는 Notification.requestPermission() 을 사용자 제스처(탭) 안에서만 허용 →
  //  자동 구독이 안 되므로, 이 배너의 '알림 켜기' 탭에서 setupWebPush 를 호출해야 권한 팝업이 뜬다.
  function _showIOSEnablePushHint() {
    if (document.getElementById("iosEnablePush")) return;
    const bar = document.createElement("div");
    bar.id = "iosEnablePush";
    bar.style.cssText = "position:fixed;left:8px;right:8px;bottom:8px;z-index:99999;" +
      "background:#1F2937;color:#fff;border-radius:12px;padding:12px 14px;" +
      "box-shadow:0 6px 24px rgba(0,0,0,0.3);font-size:calc(13px + var(--fs-add-ui));line-height:1.4;";
    bar.innerHTML =
      '<div style="display:flex;align-items:center;gap:10px;">' +
        '<div style="font-size:calc(22px + var(--fs-add-ui));">🔔</div>' +
        '<div style="flex:1;min-width:0;">' +
          '<div style="font-weight:700;margin-bottom:2px;">알림을 켜시겠어요?</div>' +
          '<div style="color:#D1D5DB;font-size:calc(12px + var(--fs-add-ui));">아이폰은 한 번 탭해야 알림이 켜집니다.</div>' +
        '</div>' +
        '<button type="button" id="iosEnablePushBtn" style="background:#A5282C;border:0;color:#fff;' +
          'font-weight:700;font-size:calc(13px + var(--fs-add-ui));padding:8px 14px;border-radius:8px;cursor:pointer;white-space:nowrap;">알림 켜기</button>' +
        '<button type="button" id="iosEnablePushClose" style="background:transparent;border:0;color:var(--text-soft);' +
          'font-size:calc(20px + var(--fs-add-ui));cursor:pointer;padding:0 2px;line-height:1;">✕</button>' +
      '</div>';
    document.body.appendChild(bar);
    const close = () => { try { bar.remove(); } catch (e) {} };
    const closeBtn = document.getElementById("iosEnablePushClose");
    if (closeBtn) closeBtn.addEventListener("click", close);
    const enableBtn = document.getElementById("iosEnablePushBtn");
    if (enableBtn) enableBtn.addEventListener("click", async () => {
      enableBtn.disabled = true;
      enableBtn.textContent = window.KNK_t("btn.turningOn","켜는 중...");
      const r = await setupWebPush();   // ← 사용자 탭(제스처) 안 → iOS 권한 팝업 정상
      if (r && r.ok) {
        close();
        try { alert(window.KNK_t("alert.notifOn","✅ 알림이 켜졌습니다.")); } catch (_) {}
      } else {
        enableBtn.disabled = false;
        enableBtn.textContent = window.KNK_t("notif.enableBtn","알림 켜기");
        try {
          alert(window.KNK_t("alert.notifFail","알림을 켜지 못했습니다.") + "\n" + ((r && r.reason) || "") +
                window.KNK_t("alert.notifFailIosHint","\n\n거부하셨다면 아이폰 '설정 > 알림 > KNK' 에서 허용해주세요."));
        } catch (_) {}
      }
    });
  }

  // ===== 📢 회사 '알림 필수' 정책 — 알림 OFF 면 상시 배너 + 첫 1회 강한 모달 (대표 지시 2026-05-24) =====
  async function _notifIsOn() {
    try {
      if (typeof Notification === "undefined" || Notification.permission !== "granted") return false;
      if (!("serviceWorker" in navigator) || !("PushManager" in window)) return false;
      const reg = await navigator.serviceWorker.ready;
      return !!(await reg.pushManager.getSubscription());
    } catch (e) { return false; }
  }
  function _hideNotifPolicy() {
    ["notifPolicyBanner", "notifPolicyModal"].forEach(id => {
      const el = document.getElementById(id); if (el) el.remove();
    });
    document.body.classList.remove("has-notif-banner");
  }
  async function _notifTurnOn(btn) {
    const old = btn ? btn.textContent : "";
    if (btn) { btn.disabled = true; btn.textContent = window.KNK_t("btn.turningOn","켜는 중..."); }
    let r = null;
    try { r = await setupWebPush(); } catch (e) {}
    if (r && r.ok) {
      _hideNotifPolicy();
      try { refreshAllUserStatuses(); } catch (e) {}
      try { alert(window.KNK_t("alert.notifOn","✅ 알림이 켜졌습니다.")); } catch (e) {}
      return true;
    }
    if (btn) { btn.disabled = false; btn.textContent = old || window.KNK_t("notif.enableBtn","알림 켜기"); }
    const msg = (r && r.ios_need_install)
      ? (r.reason || "")
      : window.KNK_t("alert.notifFail","알림을 켜지 못했습니다.") + "\n" + ((r && r.reason) || "") +
        window.KNK_t("alert.notifFailHint","\n\n거부하셨다면 브라우저/휴대폰 '설정 > 알림 > KNK' 에서 허용해주세요.");
    try { alert(msg); } catch (e) {}
    return false;
  }
  function _showNotifPolicyBanner() {
    if (document.getElementById("notifPolicyBanner")) return;
    const bar = document.createElement("div");
    bar.id = "notifPolicyBanner";
    bar.innerHTML =
      '<span>🔔 <b>알림 필수</b> — 꺼져 있어요</span>' +
      '<button type="button" id="notifPolicyBannerBtn">켜기</button>';
    document.body.appendChild(bar);
    const btn = document.getElementById("notifPolicyBannerBtn");
    if (btn) btn.addEventListener("click", () => _notifTurnOn(btn));
  }
  function _showNotifPolicyModal() {
    if (document.getElementById("notifPolicyModal")) return;
    const ov = document.createElement("div");
    ov.id = "notifPolicyModal";
    ov.innerHTML =
      '<div class="np-card">' +
        '<div style="font-size:calc(40px + var(--fs-add-ui));margin-bottom:6px;">🔔</div>' +
        '<div class="np-title">회사 정책: 알림 필수</div>' +
        '<div class="np-desc">업무 메시지를 놓치지 않도록 <b>알림을 반드시 켜 주세요.</b><br>버튼을 누르고 "허용"을 선택하면 됩니다.<br><span style="color:var(--text-soft);font-size:calc(12px + var(--fs-add-ui));">(아이폰은 홈 화면에 앱 설치 후 허용)</span></div>' +
        '<button type="button" id="notifPolicyModalBtn" class="np-go">🔔 알림 켜기</button>' +
        '<button type="button" id="notifPolicyModalLater" class="np-later">나중에 (상단 배너에서 다시 켜기)</button>' +
      '</div>';
    document.body.appendChild(ov);
    const btn = document.getElementById("notifPolicyModalBtn");
    if (btn) btn.addEventListener("click", async () => {
      const ok = await _notifTurnOn(btn);
      if (ok) { const m = document.getElementById("notifPolicyModal"); if (m) m.remove(); }
    });
    const later = document.getElementById("notifPolicyModalLater");
    if (later) later.addEventListener("click", () => { const m = document.getElementById("notifPolicyModal"); if (m) m.remove(); });
  }
  async function _notifPolicyEnforce() {
    if (SOLO_MODE) return;
    // 인앱 브라우저(카톡 등)는 푸시 자체가 불가 → 권유 안 함. 게스트(외부 고객)는 회사 '알림 필수' 정책 대상 아님. (대표 지시 2026-05-30)
    if (_isInAppBrowser() || window._meIsGuest) { _hideNotifPolicy(); return; }
    if (await _notifIsOn()) { _hideNotifPolicy(); return; }
    _showNotifPolicyBanner();
    try {
      if (!localStorage.getItem("knkmsg.notifPolicyModalShown")) {
        localStorage.setItem("knkmsg.notifPolicyModalShown", "1");
        _showNotifPolicyModal();
      }
    } catch (e) {}
  }

  // 💻 'KNK 앱으로 설치' 배너 (PC/안드로이드) — beforeinstallprompt 잡힌 뒤 표시. (2026-05-20)
  //  설치하면 독립 창 + 시작메뉴 등록 + 창 닫아도 백그라운드 알림(윈도우 토스트).
  function _showInstallAppHint() {
    if (document.getElementById("installAppHint")) return;
    try { if (localStorage.getItem("knkmsg.installHintDismissed") === "1") return; } catch (_) {}
    const isDesktop = !(window.matchMedia && window.matchMedia("(pointer: coarse)").matches);
    const titleTxt = isDesktop ? "KNK를 PC 앱으로 설치할까요?" : "KNK를 앱으로 설치할까요?";
    const descTxt = isDesktop
      ? "독립 창 + 시작 메뉴 등록. 설치 후 창을 닫아도 우측 하단 알림이 옵니다."
      : "홈 화면에 추가되어 알림을 받습니다.";
    const bar = document.createElement("div");
    bar.id = "installAppHint";
    bar.style.cssText = "position:fixed;left:8px;right:8px;bottom:8px;z-index:99999;max-width:520px;margin:0 auto;" +
      "background:#1F2937;color:#fff;border-radius:12px;padding:12px 14px;" +
      "box-shadow:0 6px 24px rgba(0,0,0,0.3);font-size:calc(13px + var(--fs-add-ui));line-height:1.4;";
    bar.innerHTML =
      '<div style="display:flex;align-items:center;gap:10px;">' +
        '<div style="font-size:calc(22px + var(--fs-add-ui));">💻</div>' +
        '<div style="flex:1;min-width:0;">' +
          '<div style="font-weight:700;margin-bottom:2px;">' + titleTxt + '</div>' +
          '<div style="color:#D1D5DB;font-size:calc(12px + var(--fs-add-ui));">' + descTxt + '</div>' +
        '</div>' +
        '<button type="button" id="installAppBtn" style="background:#A5282C;border:0;color:#fff;' +
          'font-weight:700;font-size:calc(13px + var(--fs-add-ui));padding:8px 14px;border-radius:8px;cursor:pointer;white-space:nowrap;">설치</button>' +
        '<button type="button" id="installAppClose" style="background:transparent;border:0;color:var(--text-soft);' +
          'font-size:calc(20px + var(--fs-add-ui));cursor:pointer;padding:0 2px;line-height:1;">✕</button>' +
      '</div>';
    document.body.appendChild(bar);
    const close = () => { try { bar.remove(); } catch (e) {} };
    const closeBtn = document.getElementById("installAppClose");
    if (closeBtn) closeBtn.addEventListener("click", () => {
      try { localStorage.setItem("knkmsg.installHintDismissed", "1"); } catch (_) {}
      close();
    });
    const installBtn = document.getElementById("installAppBtn");
    if (installBtn) installBtn.addEventListener("click", async () => {
      const dp = window._deferredInstallPrompt;
      if (!dp) { close(); return; }
      installBtn.disabled = true;
      try {
        dp.prompt();
        await dp.userChoice;            // {outcome: 'accepted'|'dismissed'}
      } catch (_) {}
      window._deferredInstallPrompt = null;
      close();
    });
  }

  // 📲 카카오톡 등 인앱 브라우저 전용 — 설치·푸시가 막혀 있어 '기본 브라우저로 열어 설치' 안내. (대표 지시 2026-05-30)
  //  OS(아이폰/안드로이드) + 언어(한/베/영)별로 브라우저 이름·방법을 다르게 안내.
  //  ⚠ 휴대폰 브랜드로 안 나눔 — 베트남 직원 중국폰 등 다양 → OS 기준이 정확.
  function _showInAppBrowserInstallGuide() {
    if (document.getElementById("inappInstallGuide")) return;
    try { if (sessionStorage.getItem("knkmsg.inappGuideDismissed") === "1") return; } catch (_) {}
    const isIOSdev = _isIOS();
    const isAndroid = !isIOSdev;   // iOS 외엔 모두 안드로이드식 안내(갤럭시·샤오미·오포 등 중국폰 포함)
    const title = _pickLang(
      "📲 앱으로 설치하면 알림까지 받아요",
      "📲 Cài làm ứng dụng để nhận cả thông báo",
      "📲 Install as an app to also get notifications");
    const desc = isIOSdev
      ? _pickLang(
          "아이폰: 카톡 화면 <b>아래 나침반(Safari) 아이콘</b>을 누르면 사파리로 열려요.<br>(또는 <b>‘링크 복사’</b> 후 사파리 주소창에 붙여넣기)",
          "iPhone: nhấn <b>biểu tượng la bàn (Safari) ở dưới</b> để mở bằng Safari.<br>(hoặc <b>‘Sao chép link’</b> rồi dán vào Safari)",
          "iPhone: tap the <b>compass (Safari) icon at the bottom</b> to open in Safari.<br>(or <b>‘Copy link’</b> and paste into Safari)")
      : _pickLang(
          "<b>크롬·삼성인터넷·엣지</b> 같은 브라우저로 열면 설치돼요.<br>아래 <b>‘브라우저로 열기’</b>를 누르세요. (안 되면 카톡 메뉴 → <b>‘다른 브라우저로 열기’</b>)",
          "Mở bằng <b>Chrome, Samsung Internet, Edge</b>.<br>Nhấn <b>‘Mở trình duyệt’</b>. (Nếu không: menu KakaoTalk → <b>‘Mở bằng trình duyệt khác’</b>)",
          "Open in <b>Chrome, Samsung Internet, Edge</b>.<br>Tap <b>‘Open in browser’</b>. (If not: KakaoTalk menu → <b>‘Open in another browser’</b>)");
    const openBtnTxt = isIOSdev
      ? _pickLang("링크<br>복사", "Sao chép<br>link", "Copy<br>link")
      : _pickLang("브라우저로<br>열기", "Mở<br>trình duyệt", "Open in<br>browser");
    const bar = document.createElement("div");
    bar.id = "inappInstallGuide";
    bar.style.cssText = "position:fixed;left:8px;right:8px;bottom:8px;z-index:99999;max-width:520px;margin:0 auto;" +
      "background:#1F2937;color:#fff;border-radius:12px;padding:13px 15px;" +
      "box-shadow:0 6px 24px rgba(0,0,0,0.35);font-size:calc(13px + var(--fs-add-ui));line-height:1.55;";
    bar.innerHTML =
      '<div style="display:flex;align-items:flex-start;gap:10px;">' +
        '<div style="flex:1;min-width:0;">' +
          '<div style="font-weight:700;margin-bottom:4px;">' + title + '</div>' +
          '<div style="color:#D1D5DB;font-size:calc(12px + var(--fs-add-ui));">' + desc + '</div>' +
        '</div>' +
        '<button type="button" id="inappOpenExt" style="background:#A5282C;border:0;color:#fff;font-weight:700;font-size:calc(11.5px + var(--fs-add-ui));padding:7px 9px;border-radius:8px;cursor:pointer;white-space:nowrap;line-height:1.25;text-align:center;">' + openBtnTxt + '</button>' +
        '<button type="button" id="inappGuideClose" style="background:transparent;border:0;color:#9ca3af;font-size:calc(20px + var(--fs-add-ui));cursor:pointer;padding:0 2px;line-height:1;">✕</button>' +
      '</div>';
    document.body.appendChild(bar);
    const close = () => { try { bar.remove(); } catch (e) {} };
    const cb = document.getElementById("inappGuideClose");
    if (cb) cb.addEventListener("click", () => { try { sessionStorage.setItem("knkmsg.inappGuideDismissed", "1"); } catch (_) {} close(); });
    const ob = document.getElementById("inappOpenExt");
    if (ob) ob.addEventListener("click", () => {
      // ★ 직원(비게스트)은 직원 로그인(?staff=1)으로 열기 — 외부 브라우저엔 직원 세션이 없고,
      //   그 브라우저에 게스트 토큰 쿠키(knk_gt)가 남아 있으면 /login 이 고객사 페이지로 보내는 문제 방지.
      //   게스트는 현재 URL(?g=토큰 포함) 그대로 → 자기 방으로 자동 재인증. (대표 지시 2026-05-31)
      const _target = window._meIsGuest
        ? location.href
        : (location.origin + BASE + "/login?staff=1");
      if (isIOSdev) {
        // 아이폰: Safari 강제 열기 불가(OS 제한) → 링크 복사 → 사파리 주소창에 붙여넣게.
        const _mark = () => { try { ob.innerHTML = _pickLang("복사됨", "Đã chép", "Copied"); } catch (e) {} };
        try {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(_target).then(_mark).catch(() => { _giCopyFallback(_target); _mark(); });
          } else { _giCopyFallback(_target); _mark(); }
        } catch (_) {}
        return;
      }
      // 안드로이드: 크롬 인텐트로 외부 브라우저 열기 시도(best-effort). 실패(크롬 미설치 등) 시 위 안내대로 메뉴 사용.
      try {
        const path = _target.replace(/^https?:\/\//, "");
        window.location.href = "intent://" + path + "#Intent;scheme=https;package=com.android.chrome;end";
      } catch (_) {}
    });
    function _giCopyFallback(text) {
      try {
        const ta = document.createElement("textarea");
        ta.value = text; ta.style.cssText = "position:fixed;left:-9999px;top:0;";
        document.body.appendChild(ta); ta.focus(); ta.select();
        document.execCommand("copy"); document.body.removeChild(ta);
      } catch (e) {}
    }
  }
})();

/* ===== KNK 공용 달력(date picker) — HAIST WORKS 수주 달력 표준 복제 (대표 지시 2026-05-31) =====
 *  기본 <input type="date"> 의 브라우저 달력을 우리 달력으로 교체.
 *  대상: class="knk-date" 입력 (납기·마감일·다운로드 기간 등).
 *  기능: 월 격자 · 주말색(일 빨강/토 파랑) · 한국 K·베트남 V 공휴일 배지(대체=점선)
 *        · 오늘 금색 ring · 선택 빨강 채움 · 이전/다음 달 · 오늘/지우기 · min·max 존중.
 *  값:   input.value 에 YYYY-MM-DD 기록 + input/change 이벤트 → 기존 로직 그대로 호환.
 *  공휴일: /static/holidays_kr_vn.json (holidays 라이브러리로 사전 생성). 없으면 배지 생략.
 *  주의: 모달 닫기 핸들러가 [data-close] 클릭에 stopPropagation 하므로 이 핸들러는 캡처 단계로 등록.
 */
(function () {
  "use strict";
  const BASE = window.__BASE__ || "";
  const HOL = { kr: {}, vn: {}, loaded: false };

  function loadHolidays() {
    if (HOL.loaded) return;
    HOL.loaded = true;
    try {
      fetch(BASE + "/static/holidays_kr_vn.json")
        .then(function (r) { return r.json(); })
        .then(function (j) {
          HOL.kr = (j && j.kr) ? j.kr : {};
          HOL.vn = (j && j.vn) ? j.vn : {};
          if (state.open) { render(); position(); }
        })
        .catch(function () {});
    } catch (e) {}
  }

  function curLang() {
    let l = (document.documentElement.getAttribute("lang") || "ko").slice(0, 2);
    if (l !== "ko" && l !== "vi" && l !== "en" && l !== "zh") l = "ko";
    return l;
  }
  const DOW = {
    ko: ["일", "월", "화", "수", "목", "금", "토"],
    vi: ["CN", "T2", "T3", "T4", "T5", "T6", "T7"],
    en: ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"],
    zh: ["日", "一", "二", "三", "四", "五", "六"],
  };
  const LBL = {
    ko: { today: "오늘", clear: "지우기" },
    vi: { today: "Hôm nay", clear: "Xóa" },
    en: { today: "Today", clear: "Clear" },
    zh: { today: "今天", clear: "清除" },
  };

  function pad2(n) { return (n < 10 ? "0" : "") + n; }
  function toIso(y, m, d) { return y + "-" + pad2(m) + "-" + pad2(d); }
  function parseIso(s) {
    const mt = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || "");
    return mt ? { y: +mt[1], m: +mt[2], d: +mt[3] } : null;
  }
  function todayParts() {
    const t = new Date();
    return { y: t.getFullYear(), m: t.getMonth() + 1, d: t.getDate() };
  }
  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }

  let pop = null;
  const state = { open: false, input: null, viewY: 0, viewM: 0, min: "", max: "" };

  function ensurePop() {
    if (pop) return pop;
    pop = document.createElement("div");
    pop.className = "knk-dp";
    pop.style.display = "none";
    document.body.appendChild(pop);
    return pop;
  }

  function render() {
    if (!state.open) return;
    ensurePop();
    const y = state.viewY, m = state.viewM;
    const L = curLang();
    const dows = DOW[L] || DOW.ko;
    const lbl = LBL[L] || LBL.ko;
    const tp = todayParts();
    const todayIso = toIso(tp.y, tp.m, tp.d);
    const sp = parseIso(state.input ? state.input.value : "");
    const selIso = sp ? toIso(sp.y, sp.m, sp.d) : "";

    const startDow = new Date(y, m - 1, 1).getDay();
    const daysInMonth = new Date(y, m, 0).getDate();
    const prevDays = new Date(y, m - 1, 0).getDate();
    const cells = [];
    for (let i = startDow - 1; i >= 0; i--) cells.push({ d: prevDays - i, cur: false });
    for (let d = 1; d <= daysInMonth; d++) cells.push({ d: d, cur: true });
    while (cells.length % 7 !== 0) cells.push({ d: 0, cur: false });

    let h = `<div class="knk-dp-head">`
          + `<button type="button" class="knk-dp-nav" data-nav="-1" aria-label="이전 달">‹</button>`
          + `<span class="knk-dp-title">${y}년 ${pad2(m)}월</span>`
          + `<button type="button" class="knk-dp-nav" data-nav="1" aria-label="다음 달">›</button>`
          + `</div><div class="knk-dp-grid">`;
    for (let w = 0; w < 7; w++) {
      const c = w === 0 ? " sun" : (w === 6 ? " sat" : "");
      h += `<div class="knk-dp-dow${c}">${dows[w]}</div>`;
    }
    for (let i = 0; i < cells.length; i++) {
      const cell = cells[i];
      const col = i % 7;
      if (!cell.cur) { h += `<div class="knk-dp-day out"></div>`; continue; }
      const iso = toIso(y, m, cell.d);
      const hk = HOL.kr[iso], hv = HOL.vn[iso];
      const isHol = !!(hk || hv);
      let dis = false;
      if (state.min && iso < state.min) dis = true;
      if (state.max && iso > state.max) dis = true;
      let cls = "knk-dp-day";
      if (col === 0 || isHol) cls += " sun";
      else if (col === 6) cls += " sat";
      if (iso === todayIso) cls += " today";
      if (iso === selIso) cls += " sel";
      if (dis) cls += " disabled";
      let tip = iso;
      if (hk) tip += " · KR " + hk;
      if (hv) tip += " · VN " + hv;
      let badge = "";
      if (isHol) {
        badge = `<span class="knk-dp-badge">`;
        if (hk) badge += `<span class="b kr${hk.indexOf("대체") >= 0 ? " alt" : ""}">K</span>`;
        if (hv) badge += `<span class="b vn${hv.toLowerCase().indexOf("bù") >= 0 ? " alt" : ""}">V</span>`;
        badge += `</span>`;
      }
      h += `<div class="${cls}" data-d="${cell.d}" title="${esc(tip)}">${badge}<span class="n">${cell.d}</span></div>`;
    }
    h += `</div><div class="knk-dp-foot">`
       + `<button type="button" class="knk-dp-clear" data-act="clear">${lbl.clear}</button>`
       + `<button type="button" class="knk-dp-today" data-act="today">${lbl.today}</button>`
       + `</div>`;
    pop.innerHTML = h;
  }

  function pick(iso) {
    if (state.min && iso < state.min) return;
    if (state.max && iso > state.max) return;
    setValue(state.input, iso);
    close();
  }
  function setValue(input, iso) {
    if (!input) return;
    input.value = iso;
    try {
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    } catch (e) {}
  }

  function position() {
    if (!pop || !state.input) return;
    const r = state.input.getBoundingClientRect();
    pop.style.display = "block";
    const pw = pop.offsetWidth, ph = pop.offsetHeight;
    let x = r.left;
    let y = r.bottom + 4;
    if (x + pw > window.innerWidth - 8) x = window.innerWidth - pw - 8;
    if (x < 8) x = 8;
    if (y + ph > window.innerHeight - 8) {
      const up = r.top - ph - 4;
      y = up > 8 ? up : (window.innerHeight - ph - 8);
    }
    if (y < 8) y = 8;
    pop.style.left = x + "px";
    pop.style.top = y + "px";
  }

  function openFor(input) {
    ensurePop();
    loadHolidays();
    state.open = true;
    state.input = input;
    state.min = input.getAttribute("min") || "";
    state.max = input.getAttribute("max") || "";
    const sp = parseIso(input.value);
    const tp = todayParts();
    state.viewY = sp ? sp.y : tp.y;
    state.viewM = sp ? sp.m : tp.m;
    render();
    position();
  }
  function close() {
    state.open = false;
    state.input = null;
    if (pop) pop.style.display = "none";
  }

  // 클릭 위임 — 캡처 단계(모달 [data-close] stopPropagation 보다 먼저/확실히 실행)
  document.addEventListener("click", function (e) {
    const t = e.target;
    if (!t || !t.closest) return;
    if (t.closest(".knk-dp")) {
      const nav = t.closest("[data-nav]");
      if (nav) {
        state.viewM += parseInt(nav.getAttribute("data-nav"), 10);
        if (state.viewM < 1) { state.viewM = 12; state.viewY--; }
        else if (state.viewM > 12) { state.viewM = 1; state.viewY++; }
        render(); position();
        return;
      }
      const act = t.closest("[data-act]");
      if (act) {
        const a = act.getAttribute("data-act");
        if (a === "today") { const tt = todayParts(); pick(toIso(tt.y, tt.m, tt.d)); }
        else if (a === "clear") { setValue(state.input, ""); close(); }
        return;
      }
      const day = t.closest(".knk-dp-day[data-d]");
      if (day && !day.classList.contains("disabled")) {
        pick(toIso(state.viewY, state.viewM, parseInt(day.getAttribute("data-d"), 10)));
      }
      return;
    }
    const inp = t.closest(".knk-date");
    if (inp) {
      e.preventDefault();
      if (state.open && state.input === inp) { close(); return; }
      openFor(inp);
      return;
    }
    if (state.open) close();
  }, true);

  // ESC — 캡처 + stopPropagation 으로 모달보다 먼저 잡아 달력만 닫음
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && state.open) { close(); e.stopPropagation(); }
  }, true);
  window.addEventListener("resize", function () { if (state.open) position(); });
  window.addEventListener("scroll", function () { if (state.open) position(); }, true);

  window.KNKDatePicker = {
    open: openFor, close: close,
    reload: function () { HOL.loaded = false; loadHolidays(); },
  };
})();
