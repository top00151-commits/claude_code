// KNK Messenger — client (Phase A+B+C+D)
(() => {
  const app = document.getElementById("app");
  const meId = parseInt(app.dataset.meId, 10);
  // 내 역할 — 서버가 페이지에 심어줌 (관리자 'ceo' / 일반 'staff'). 부팅 즉시 설정해
  // 관리자 전용 UI(🆔 직원등록 등)를 users 목록 로드 전에도 정확히 토글. (대표 지시 2026-05-20)
  window._meRole = (app.dataset.meRole || "staff");
  // 최고관리자(소유자) 여부 — 서버가 페이지에 심어줌 (대표 지시 2026-05-21)
  window._meIsOwner = (app.dataset.meOwner === "1");
  // 팀장 여부 — 채널 생성·관리 권한 (대표 지시 2026-05-21)
  window._meIsTeamLead = (app.dataset.meTeamlead === "1");
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

  const $ = (id) => document.getElementById(id);
  const els = {
    roomList: $("roomList"),
    chatTitle: $("chatTitle"),
    itemMeta: $("itemMeta"),
    itemEditBtn: $("itemEditBtn"),
    requestsBtn: $("requestsBtn"),
    requestsBadge: $("requestsBadge"),
    galleryBtn: $("galleryBtn"),
    exportBtn: $("exportBtn"),
    leaveRoomBtn: $("leaveRoomBtn"),
    leaveRoomDialog: $("leaveRoomDialog"),
    leaveMyName: $("leaveMyName"),
    leaveWithExportBtn: $("leaveWithExportBtn"),
    leaveJustBtn: $("leaveJustBtn"),
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
    aiSummaryRegenBtn: $("aiSummaryRegenBtn"),
    aiSummaryCopyBtn: $("aiSummaryCopyBtn"),
    aiRewriteBtn: $("aiRewriteBtn"),
    aiRewriteMenu: $("aiRewriteMenu"),
    // 사이드바 탭 + 사용자 목록
    sidebarTabs: $("sidebarTabs"),
    userListToolbar: $("userListToolbar"),
    newUserBtn: $("newUserBtn"),
    newUserDialog: $("newUserDialog"),
    nuDisplayName: $("nuDisplayName"),
    nuEmail: $("nuEmail"),
    nuPhone: $("nuPhone"),
    nuTitle: $("nuTitle"),
    nuDept: $("nuDept"),
    nuRoleCeo: $("nuRoleCeo"),
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
    statusSaveBtn: $("statusSaveBtn"),
    calTitle: $("calTitle"),
    calStart: $("calStart"),
    calEnd: $("calEnd"),
    calKind: $("calKind"),
    calAddBtn: $("calAddBtn"),
    calEventList: $("calEventList"),
  };

  const STATUS_LABEL = { active: "진행중", hold: "보류", done: "완료", cancelled: "취소" };
  const REQ_STATUS_LABEL = { open: "열림", in_progress: "진행중", done: "완료", cancelled: "취소" };

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
  let activeRoom = null;
  let rooms = [];
  let users = [];
  let roomReadStatus = { members: [], total: 0 };  // 현재 방의 읽음 상태
  let _lastMsgDateStr = null;  // 마지막으로 렌더된 메시지의 날짜(toDateString) — 날짜 바뀐 첫 메시지 판별용
  let activeFilter = "all";
  let activeTab = "item";
  let activeGalleryTab = "image";
  let activeReqTab = "open";
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

  const initial = (name) => (name && name.length ? name[0] : "?");

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
      if (!newContent) { alert("내용이 비어 있습니다."); return; }
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
        alert("편집 실패: " + (err.message || err));
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
      alert("확인 현황 조회 실패: " + (err.message || err));
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
    // 이미지·파일 첨부 영역 제거
    li.querySelectorAll(".image-wrap, .file-wrap, .album-grid, .forward-card, .quote-card, .whisper-header").forEach(el => el.remove());
    // 액션 버튼들 숨김 (반응·요청·번역 등 의미 없어짐)
    const actionBar = li.querySelector(".msg-action-bar");
    if (actionBar) actionBar.style.display = "none";
    const reactBar = li.querySelector(".react-bar");
    if (reactBar) reactBar.style.display = "none";
  }

  // 아바타 inner — avatar_url 있으면 <img>, 없으면 이름 첫 글자 (대표 지시 2026-05-19)
  function _avatarBody(u) {
    if (u && u.avatar_url) {
      return `<img class="avatar-img" src="${escapeHtml(u.avatar_url)}" alt="" loading="lazy" onerror="this.style.display='none';this.parentElement.classList.add('avatar-img-failed');">`;
    }
    return escapeHtml(initial((u && u.display_name) || "?"));
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

  // 아바타 업로드 trigger — file input 동적 생성 + Canvas 리사이즈 + 업로드
  async function _triggerAvatarUpload(userId) {
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
          // 1) Canvas 리사이즈·압축 (500KB 이하면 그대로 사용, 그 이상이면 리사이즈)
          let blob;
          try {
            blob = await _resizeImageForAvatar(f, 512, 0.85);
            // 만약 결과가 여전히 크면 quality 0.7 로 재시도
            if (blob.size > 1024 * 1024) {
              blob = await _resizeImageForAvatar(f, 512, 0.7);
            }
          } catch (err) {
            // Canvas 변환 실패 시 원본 그대로 시도 (서버에서 검증)
            console.warn("[avatar] resize 실패, 원본 사용:", err);
            blob = f;
            if (blob.size > 5 * 1024 * 1024) {
              alert("이미지가 5MB 초과 + 자동 변환 실패. 다른 이미지로 시도하세요.");
              resolve(); return;
            }
          }
          // 2) 업로드 (.jpg 확장자로)
          const fd = new FormData();
          fd.append("file", blob, "avatar.jpg");
          const res = await fetch(`${BASE}/api/users/${userId}/avatar`, { method: "POST", body: fd })
            .then(r => r.json());
          if (res.error) { alert(res.error); resolve(); return; }
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
          // ★ 본인 사진이면 헤더 좌상단 아바타도 즉시 갱신 (대표 지시 2026-05-19)
          if (userId === meId) {
            try { _updateHeaderAvatar(res.avatar_url); } catch(e) {}
          }
          // ucm 닫고 다시 표시 (새 사진 반영)
          try { closeUserContextMenu(); } catch(e) {}
          resolve();
        } catch (err) {
          alert("업로드 실패: " + (err && err.message ? err.message : err));
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
      alert("사진 제거 실패: " + (err && err.message ? err.message : err));
    }
  }

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
      // 헤더 '🆔 직원 등록' 버튼 권한 토글 — 관리자(ceo)만 노출.
      // window._meRole(서버가 부팅 시 심어줌) 기준 → users 목록 로드 타이밍과 무관하게 정확.
      try {
        const newUserBtnEl = document.getElementById("newUserBtn");
        if (newUserBtnEl) newUserBtnEl.hidden = (window._meRole !== "ceo");
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
    messages: (rid) => fetch(`${BASE}/api/rooms/${rid}/messages`).then(r => r.json()),
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
    upload: (rid, file, onProgress, albumId) => {
      // XHR 사용 — 진행률 이벤트 받으려면 fetch 대신 XHR (Stream API 미흡)
      return new Promise((resolve, reject) => {
        const fd = new FormData();
        fd.append("room_id", rid);
        fd.append("file", file);
        if (albumId) fd.append("album_id", albumId);
        const xhr = new XMLHttpRequest();
        xhr.open("POST", BASE + "/api/upload");
        if (onProgress && xhr.upload) {
          xhr.upload.addEventListener("progress", (e) => {
            if (e.lengthComputable) {
              onProgress(Math.round((e.loaded / e.total) * 100), e.loaded, e.total);
            }
          });
        }
        xhr.onload = () => {
          try {
            const data = JSON.parse(xhr.responseText);
            if (xhr.status >= 200 && xhr.status < 300) resolve(data);
            else reject(data);
          } catch (err) { reject({ error: `HTTP ${xhr.status}` }); }
        };
        xhr.onerror = () => reject({ error: "네트워크 오류" });
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
    return rooms.filter(r => r.type === activeFilter);
  }

  function renderRoomList() {
    const list = filteredRooms();
    // 사이드바 탭이 '사용자' 이면 방 목록 표시 안 함 (refresh·socket 이벤트 시에도 유지)
    // 아래 모든 분기에서 들어가도 hidden 유지하려면 여기서 조기 반환은 안 됨 — DOM 은 그려두되 .hidden 만 true.
    const onUsersTab = (typeof _sidebarTab !== "undefined" && _sidebarTab === "users");
    if (activeFilter === "my-tasks") {
      els.roomList.hidden = true;
      els.searchResults.hidden = true;
      els.myTasks.hidden = onUsersTab ? true : false;
      if (!onUsersTab) renderMyTasks();
      return;
    }
    els.myTasks.hidden = true;
    els.roomList.hidden = onUsersTab ? true : false;
    if (!list.length) {
      els.roomList.innerHTML = `<li class="empty-state" style="padding:32px;font-size:13px;">${rooms.length ? "이 필터에 해당하는 항목이 없습니다." : "대화가 없습니다.<br>＋ 버튼으로 새 프로젝트을 시작하세요."}</li>`;
      return;
    }
    els.roomList.innerHTML = list.map(r => {
      const isSelf = r.type === "self";
      // 1:1 방 — '이름 직급님-부서' 형식 (대표 지시 2026-05-19)
      let name = isSelf ? "📝 내 메모장" : (r.name || "(이름없음)");
      if (r.type === "direct" && Array.isArray(users) && users.length) {
        try {
          const cached = users.find(u => u.display_name === r.name) || {};
          if (cached.display_name) {
            let nm = cached.display_name;
            if (cached.title) nm += ` ${cached.title}님`;
            else nm += "님";
            if (cached.department) {
              const dept = (typeof deptShortLabel === "function") ? deptShortLabel(cached.department) : cached.department;
              name = `${nm}-${dept}`;
            } else {
              name = nm;
            }
          }
        } catch(e) {}
      }
      // 방 종류별 원형 색상 (대표 지시 2026-05-20):
      //  메모장=주황(기존) / 프로젝트=녹색 / 채널=KNK색 / 그룹=보라(추천) / 1:1=기존(상대색 또는 파랑)
      const color =
        isSelf                 ? "#f59e0b" :
        r.type === "item"      ? "#16A34A" :   // 프로젝트 = 녹색
        r.type === "channel"   ? "#A5282C" :   // 채널 = 케이엔케이 색
        r.type === "group"     ? "#7C3AED" :   // 그룹 = 보라 (빅터 추천)
                                 (r.avatar_color || "#3b82f6");  // 1:1(direct) = 기존
      // self(내 메모장)은 미리보기 줄을 항상 빈칸 — 메모 내용이 있어도 방 목록엔 표시 안 함 (대표 지시 2026-05-20)
      const last = isSelf ? "" : (r.last_message ? escapeHtml(String(r.last_message).slice(0, 40)) : "<em style='color:#9ca3af'>대화 없음</em>");
      const time = r.last_at ? fmtTime(r.last_at) : "";
      const unread = r.unread > 0 ? `<span class="unread-badge">${r.unread > 99 ? "99+" : r.unread}</span>` : "";
      const active = activeRoom && activeRoom.id === r.id ? "active" : "";

      let chips = "";
      if (r.type === "item") {
        if (r.item_customer) chips += `<span class="customer-chip">${escapeHtml(r.item_customer)}</span>`;
        if (r.item_code) chips += `<span class="code-chip">${escapeHtml(r.item_code)}</span>`;
        if (r.item_status) chips += `<span class="status-pill status-${r.item_status}">${STATUS_LABEL[r.item_status] || r.item_status}</span>`;
      }
      // self 방은 이름 자체가 "📝 메모" 라 별도 칩 불필요
      // 자동삭제 설정된 방은 ⏱ 아이콘 (WhatsApp 식)
      const retentionIcon = (r.retention_days && r.retention_days > 0)
        ? `<span class="room-retention-icon" title="자동삭제 ${r.retention_days===1?'24시간':r.retention_days+'일'} 후">⏱</span>`
        : "";

      const mutedIcon = notifySettings.isRoomMuted(r.id) ? `<span class="room-muted-icon" title="이 방 알림 음소거 중">🔕</span>` : "";
      // 핀 고정 표시
      const pinnedIcon = r.pinned ? `<span class="room-pinned-icon" title="여기 고정됨">📌</span>` : "";
      // 원형아이콘 — 자동채널은 실제 국기·지구 이모지 (Noto 폰트로 이미지 렌더, 대표 지시 2026-05-21)
      let avatarText = initial(name);
      let avatarFlag = false;
      if (isSelf) avatarText = "✏️";                                       // 📝 내 메모장 = 연필
      else if (r.channel_scope === "all") { avatarText = "🌏"; avatarFlag = true; }  // KNK WORLD = 아시아 지구
      else if (r.channel_scope === "hq")  { avatarText = "🇰🇷"; avatarFlag = true; }  // 본사 = 태극기
      else if (r.channel_scope === "vn")  { avatarText = "🇻🇳"; avatarFlag = true; }  // 베트남 = 베트남국기
      // 방/채널 아바타 — 관리자가 올린 이미지(avatar_url) 있으면 사진, 없으면 글자/이모지
      const avatarInner = r.avatar_url
        ? `<img class="avatar-img" src="${escapeHtml(r.avatar_url)}" alt="" loading="lazy" onerror="this.style.display='none';this.parentElement.classList.add('avatar-img-failed');">`
        : escapeHtml(avatarText);
      const rowClass = [active, r.type === "item" ? "item-row" : "", isSelf ? "self-row" : "", r.pinned ? "pinned-row" : ""].filter(Boolean).join(" ");
      return `
        <li data-room-id="${r.id}" class="${rowClass}">
          <div class="avatar${avatarFlag ? ' room-flag-avatar' : ''}" style="background:${color}">${avatarInner}</div>
          <div class="room-info">
            <div class="room-name-line">
              ${chips}
              <div class="room-name">${pinnedIcon}${escapeHtml(name)}${retentionIcon}${mutedIcon}</div>
            </div>
            <div class="room-last">${last}</div>
          </div>
          <div class="room-meta">
            <div class="room-time">${time}</div>
            ${unread}
          </div>
        </li>`;
    }).join("");
    els.roomList.querySelectorAll("li[data-room-id]").forEach(li => {
      li.addEventListener("click", () => {
        const rid = parseInt(li.dataset.roomId, 10);
        // 이미 열려 보고 있는 방을 다시 클릭하면 재렌더 안 함 → 깜빡임 방지 (대표 지시 2026-05-20)
        if (activeRoom && activeRoom.id === rid && app.classList.contains("viewing-chat")) return;
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
        const features = "width=306,height=544,resizable=yes,scrollbars=yes,menubar=no,toolbar=no,location=no,status=no";
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
      // 모바일 롱프레스 — 0.5초
      let _rlPressTimer = null, _rlTouchXY = { x: 0, y: 0 };
      li.addEventListener("touchstart", (e) => {
        const t = e.touches[0];
        _rlTouchXY = { x: t.clientX, y: t.clientY };
        _rlPressTimer = setTimeout(() => {
          _rlPressTimer = null;
          const rid = parseInt(li.dataset.roomId, 10);
          showRoomContextMenu(rid, _rlTouchXY.x, _rlTouchXY.y);
        }, 500);
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
        const features = "width=306,height=544,resizable=yes,scrollbars=yes,menubar=no,toolbar=no,location=no,status=no";
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
      alert(`동작 실패: ${err && err.message ? err.message : err}`);
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

  function renderMessages(msgs) {
    // 메모장(self) — 혼자 보는 방: 삭제 자리표시 + 시스템 메시지(방 이름 변경 등) 숨김 (대표 지시 2026-05-20)
    if (activeRoom && activeRoom.type === "self") {
      msgs = (msgs || []).filter(m => m.kind !== "deleted" && m.kind !== "system");
    }
    if (!msgs.length) {
      els.messages.innerHTML = `<div class="empty-state">아직 메시지가 없습니다.<br>첫 메시지를 보내보세요.</div>`;
      _lastMsgDateStr = null;
      return;
    }
    const grouped = groupAlbums(msgs);
    _markShowDates(grouped);
    els.messages.innerHTML = grouped.map(msgHtml).join("");
    wireMessageActions();
    _forceMessagesToBottom();  // 방 처음 열 때 / 메시지 전체 재로드 시 무조건 최하단 (컴포저 높이 반영)
  }

  function renderTextWithMentions(text) {
    const escaped = escapeHtml(text);
    return escaped.replace(/@([\w가-힣]{1,30})/g, (full, name) => {
      const u = users.find(x => x.username === name || x.display_name === name);
      const isMe = u && u.id === meId;
      return `<span class="mention${isMe ? ' me' : ''}">@${escapeHtml(name)}</span>`;
    });
  }

  function msgHtml(m) {
    if (m.kind === "system") {
      return `<li class="msg system" data-msg-id="${m.id}"><div class="body"><div class="bubble">${escapeHtml(m.content)}</div></div></li>`;
    }
    const mine = m.user_id === meId;
    let cls = mine ? "msg mine" : "msg";
    if (m.starred_by_me) cls += " starred";

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
          <a class="file-link" href="${BASE}/uploads/${escapeHtml(m.file_path)}" download="${escapeHtml(m.file_name || "")}">받기</a>
        </div>`;
    } else if (m.kind === "sticker" && m.file_name) {
      cls += " sticker";
      bubble = `<div class="bubble sticker-bubble"><img class="sticker-img" src="${BASE}/static/stickers/${encodeURIComponent(m.file_name)}" alt="${escapeHtml(m.content || "스티커")}" title="${escapeHtml(m.content || "")}" loading="lazy"></div>`;
    } else {
      bubble = `<div class="bubble">${renderTextWithMentions(m.content || "")}</div>`;
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

    // 읽음/안읽음 — 내 메시지에만 표시.
    // 귓속말이면 수신자 1명만 카운트 (다른 멤버는 메시지를 보지도 못 함).
    let readBadge = "";
    if (mine && roomReadStatus.members && roomReadStatus.members.length > 1) {
      let others;
      if (m.whisper_to_user_id) {
        others = roomReadStatus.members.filter(mb => mb.user_id === m.whisper_to_user_id);
      } else {
        others = roomReadStatus.members.filter(mb => mb.user_id !== meId);
      }
      const unreadBy = others.filter(mb => (mb.last_read_message_id || 0) < m.id);
      if (others.length === 0) {
        // 귓속말인데 수신자 정보 미상 — 표시 안 함
      } else if (unreadBy.length > 0) {
        const unreadNames = unreadBy.map(mb => mb.display_name).join(", ");
        // 클릭 가능 (대표 지시 2026-05-19) — 누가 읽고 안 읽었는지 명단 다이얼로그
        readBadge = `<span class="read-badge unread clickable" data-read-status-mid="${m.id}" title="${escapeHtml('클릭: 읽음/안읽음 명단 보기 (안 읽음: ' + unreadNames + ')')}">${unreadBy.length}</span>`;
      } else {
        readBadge = `<span class="read-badge all-read clickable" data-read-status-mid="${m.id}" title="클릭: 누가 언제 읽었는지 보기">읽음</span>`;
      }
    }

    const starBtnCls = m.starred_by_me ? "star-btn starred" : "star-btn";

    // 번역 표시 — 캐시된 번역이 있고 텍스트 메시지면 보여줌
    let trHtml = "";
    const trs = m.translations || {};
    const trKeys = Object.keys(trs);
    if (trKeys.length > 0 && (m.kind === "text" || !m.kind)) {
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
      <li class="${cls}" data-msg-id="${m.id}" data-parent-msg-id="${m.parent_message_id || ""}" data-uid="${m.user_id || ""}" data-whisper-to="${m.whisper_to_user_id || ""}" data-album-id="${m.album_id || ""}">
        <div class="avatar" style="background:${m.avatar_color || "#3b82f6"}">${_avatarBody(m)}</div>
        <div class="body">
          ${mine ? "" : (() => {
            // 메시지 작성자 — hover title 에 직급·부서 표시 (대표 지시 2026-05-19)
            const _cached = (Array.isArray(users) ? users.find(x => x.id === m.user_id) : null) || {};
            const _t = _cached.title || m.title || "";
            const _d = _cached.department || m.department || "";
            const _meta = [];
            if (_t) _meta.push(_t);
            if (_d) _meta.push(typeof deptDisplayLabel === "function" ? deptDisplayLabel(_d) : _d);
            const _tip = _meta.length ? `${m.display_name} (${_meta.join(" · ")})\n우클릭으로 사용자 메뉴` : "우클릭으로 사용자 메뉴";
            return `<div class="author" data-uid="${m.user_id || ""}" title="${escapeHtml(_tip)}">${escapeHtml(m.display_name)}</div>`;
          })()}
          ${whisperHeader}
          ${forwardCard}
          ${quoteCard}
          <div class="bubble-row">${bubble}<div class="time">${m.edited_at ? `<span class="edited-badge" title="원본: ${fmtTime(m.created_at)} · 편집: ${fmtTime(m.edited_at)}">✏ 편집됨 ${fmtTime(m.edited_at)}</span>` : ""}${readBadge}${m._showDate === undefined ? fmtTime(m.created_at) : fmtMsgTime(m.created_at, !!m._showDate)}</div></div>
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
        els.messages.innerHTML = grouped.map(msgHtml).join("");
        wireMessageActions();
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
    els.messages.insertAdjacentHTML("beforeend", msgHtml(m));
    wireMessageActions();
    scrollToBottom({ force: forceScroll === true });
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
      tmp.innerHTML = msgHtml(target);
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
            <div style="font-size:11px;color:var(--text-soft);">${escapeHtml(v.display_name)} · ${fmtDate(v.created_at)} · ${fmtSize(v.file_size)}</div>
          </div>
          <a href="${BASE}/uploads/${escapeHtml(v.file_path)}" download="${escapeHtml(v.file_name)}" class="file-link">받기</a>
        </div>
      `).join("");
    }
    els.versionsDialog.showModal();
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
          body = `<a href="${BASE}/uploads/${escapeHtml(s.file_path)}" download="${escapeHtml(s.file_name || "")}">[파일] ${escapeHtml(s.file_name || "")}</a>`;
        } else {
          body = escapeHtml(s.content || "");
        }
        return `
          <div class="starred-row" style="padding:10px;border-bottom:1px solid var(--border);">
            <div style="font-size:11px;color:var(--text-soft);margin-bottom:4px;">★ ${escapeHtml(s.display_name)} · ${fmtDate(s.created_at)}</div>
            <div style="font-size:13px;line-height:1.5;">${body}</div>
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

  async function openTranslateMenu(anchorBtn, messageId) {
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
    const rect = anchorBtn.getBoundingClientRect();
    popup.style.position = "fixed";
    popup.style.left = Math.min(rect.left, window.innerWidth - 200) + "px";
    popup.style.top  = (rect.bottom + 4) + "px";

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
            alert(`번역 실패: ${r.error}\n\n${r.hint || ""}`);
          } else {
            await refreshSingleMessage(messageId);
          }
        } catch (err) {
          alert("번역 요청 실패: " + err);
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

    // 메뉴 항목 정의
    const items = [
      { label: "반응", section: true },
      { icon: "👍", label: "좋아요",  act: "rx", data: "👍" },
      { icon: "✅", label: "확인",    act: "rx", data: "✅" },
      { icon: "❤",  label: "응원",   act: "rx", data: "❤" },
      { divider: true },
    ];
    if (isText) {
      items.push({ icon: "🌐", label: "번역",        act: "translate" });
      items.push({ icon: "📋", label: "텍스트 복사",  act: "copy" });
    }
    items.push({ icon: "💬", label: "스레드에서 답글", act: "thread_reply" });
    items.push({ icon: "↪", label: "인용 답장", act: "quote_reply" });
    items.push({ icon: "↗", label: "다른 방으로 전달", act: "forward" });
    items.push({ icon: isStarred ? "★" : "☆", label: isStarred ? "별표 해제" : "★ 중요 결정 별표", act: "star" });
    items.push({ icon: "📌", label: "📌 요청으로 등록", act: "request" });
    // 본인 텍스트 메시지 → 편집 (대표 지시 2026-05-19) — 사진·파일은 X, 삭제된 메시지도 X
    const isDeleted = li.classList.contains("msg-deleted");
    if (isMine && isText && !isDeleted) {
      items.push({ divider: true });
      items.push({ icon: "✏️", label: "편집", act: "edit" });
    }
    // 본인 메시지 OR 관리자 → 삭제 (대표 지시 2026-05-19)
    if ((isMine || window._meRole === "ceo") && !isDeleted) {
      if (!isMine || !isText) items.push({ divider: true });   // 편집 항목 없을 때만 divider 추가
      items.push({ icon: "🗑️", label: "삭제", act: "delete", danger: true });
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
          if (!confirm("이 메시지를 삭제하시겠습니까?\n삭제한 메시지는 복구할 수 없으며, 다른 사용자 화면에도 '삭제된 메시지' 로 표시됩니다.")) return;
          try {
            const r = await fetch(`${BASE}/api/messages/${mid}`, { method: "DELETE" }).then(x => x.json());
            if (r.error) { alert(r.error); return; }
            // socketio 'message_deleted' broadcast 가 화면 갱신 처리. fallback 으로 본 화면도 즉시 갱신.
            _markMessageAsDeleted(parseInt(mid, 10));
          } catch (err) {
            alert("삭제 실패: " + (err.message || err));
          }
        } else if (act === "translate") {
          // 기존 hidden 번역 버튼 트리거 또는 직접 호출
          const trBtn = li.querySelector("[data-act='translate']");
          if (trBtn) {
            await openTranslateMenu(trBtn, mid);
          }
        } else if (act === "copy") {
          const txt = li.querySelector(".bubble")?.textContent?.trim() || "";
          try { await navigator.clipboard.writeText(txt); } catch (_) {}
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
        <form id="threadComposer" class="thread-composer">
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
        if (!text || !_activeThreadParentId) return;
        const res = await fetch(`${BASE}/api/messages/${_activeThreadParentId}/reply`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: text }),
        }).then(r => r.json()).catch(() => ({ error: "네트워크 오류" }));
        if (res.error) { alert(res.error); return; }
        ta.value = "";
        // 새 답글은 socket 의 thread_reply 이벤트로 자동 반영. 안전망으로 재로드.
        await renderThreadPanel(_activeThreadParentId);
      });
      // Enter 발송 / Shift+Enter 줄바꿈
      const ta = document.getElementById("threadInput");
      ta.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
          e.preventDefault();
          document.getElementById("threadComposer").requestSubmit();
        }
      });
    }
    panel.classList.add("open");
    // 🧠 AI 요약 버튼 헤더에 추가 (없으면 1회만)
    if (typeof window._addThreadSummarizeBtn === "function") {
      window._addThreadSummarizeBtn(parentId);
    }
    // 이전 스레드 요약 박스 제거 (새 부모로 열렸을 때)
    const oldBox = document.getElementById("threadAiSumBox");
    if (oldBox) oldBox.remove();
    await renderThreadPanel(parentId);
    setTimeout(() => document.getElementById("threadInput")?.focus(), 50);
  }

  function closeThreadPanel() {
    _activeThreadParentId = null;
    const panel = document.getElementById("threadPanel");
    if (panel) panel.classList.remove("open");
  }

  async function renderThreadPanel(parentId) {
    const body = document.getElementById("threadBody");
    if (!body) return;
    body.innerHTML = `<div class="thread-loading">불러오는 중…</div>`;
    let data;
    try {
      data = await fetch(`${BASE}/api/messages/${parentId}/thread`).then(r => r.json());
    } catch (e) {
      body.innerHTML = `<div class="thread-error">스레드 로드 실패</div>`;
      return;
    }
    if (data.error) {
      body.innerHTML = `<div class="thread-error">${escapeHtml(data.error)}</div>`;
      return;
    }
    const p = data.parent;
    const replies = data.replies || [];
    // 스레드 작성자 메타 — 직급·부서 작은 회색 (대표 지시 2026-05-19)
    const _threadAuthorMeta = (u) => {
      const cached = (Array.isArray(users) ? users.find(x => x.id === u.user_id) : null) || {};
      const _t = cached.title || u.title || "";
      const _d = cached.department || u.department || "";
      const parts = [];
      if (_t) parts.push(escapeHtml(_t));
      if (_d) parts.push(escapeHtml(typeof deptDisplayLabel === "function" ? deptDisplayLabel(_d) : _d));
      return parts.length ? `<span class="thread-author-meta"> · ${parts.join(" · ")}</span>` : "";
    };
    const parentHtml = `
      <div class="thread-parent">
        <div class="thread-msg-row">
          <div class="avatar" style="background:${p.avatar_color || '#3b82f6'}">${escapeHtml(initial(p.display_name))}</div>
          <div class="thread-msg-body">
            <div class="thread-msg-author">${escapeHtml(p.display_name)}${_threadAuthorMeta(p)} <span class="thread-msg-time">${fmtTime(p.created_at)}</span></div>
            <div class="thread-msg-content">${escapeHtml(p.content || '').replace(/\n/g,'<br>')}</div>
          </div>
        </div>
      </div>
      <div class="thread-divider">답글 ${replies.length}개</div>
    `;
    const repliesHtml = replies.map(r => `
      <div class="thread-msg-row">
        <div class="avatar" style="background:${r.avatar_color || '#3b82f6'}">${escapeHtml(initial(r.display_name))}</div>
        <div class="thread-msg-body">
          <div class="thread-msg-author">${escapeHtml(r.display_name)}${_threadAuthorMeta(r)} <span class="thread-msg-time">${fmtTime(r.created_at)}</span></div>
          <div class="thread-msg-content">${escapeHtml(r.content || '').replace(/\n/g,'<br>')}</div>
        </div>
      </div>
    `).join("");
    body.innerHTML = parentHtml + repliesHtml;
    body.scrollTop = body.scrollHeight;
  }

  // ============================================================
  // 🤫 귓속말 (Whisper) — 대화방 안에서 1명에게만 보이는 메시지
  // ============================================================
  let _pendingWhisperUid = null;

  function startWhisperMode(uid, name) {
    if (!activeRoom) {
      alert("먼저 대화방을 선택하세요.");
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

  async function openForwardDialog(mid) {
    _forwardSourceMid = mid;
    _forwardSelected = new Set();
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
          <input type="text" id="forwardSearchInput" placeholder="🔍 방 이름 검색" style="width:100%;padding:8px 10px;border:1px solid var(--border);border-radius:6px;margin-bottom:10px;font-size:13px;">
          <div id="forwardRoomList" style="max-height:300px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;padding:6px;"></div>
          <div style="margin-top:10px;">
            <label style="font-size:12px;color:var(--text-soft);display:block;margin-bottom:4px;">코멘트 (선택 — 전달과 함께 보낼 메모)</label>
            <textarea id="forwardComment" rows="2" maxlength="300" placeholder="예: 확인 부탁드립니다" style="width:100%;padding:8px;border:1px solid var(--border);border-radius:6px;font-size:13px;resize:vertical;"></textarea>
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
    }
    _renderForwardRooms();
    try { dlg.showModal(); } catch (_) {}
  }

  function _renderForwardRooms() {
    const list = document.getElementById("forwardRoomList");
    const q = (document.getElementById("forwardSearchInput")?.value || "").trim().toLowerCase();
    // rooms 전역 사용
    const candidates = (rooms || []).filter(r => {
      if (r.type === "self") return false;  // 자기 1인방은 본인 메모용이라 전달 부적합 (옵션)
      if (!q) return true;
      return (r.name || "").toLowerCase().includes(q);
    });
    if (!candidates.length) {
      list.innerHTML = `<div style="padding:20px;text-align:center;color:var(--text-soft);font-size:13px;">방이 없습니다.</div>`;
      return;
    }
    list.innerHTML = candidates.map(r => {
      const checked = _forwardSelected.has(r.id) ? "checked" : "";
      const typeLabel = r.type === "item" ? "프로젝트" : r.type === "direct" ? "1:1" : r.type === "channel" ? "채널" : "그룹";
      return `
        <label class="forward-room-row" style="display:flex;align-items:center;gap:8px;padding:8px;border-radius:6px;cursor:pointer;">
          <input type="checkbox" data-rid="${r.id}" ${checked}>
          <div class="avatar" style="width:28px;height:28px;font-size:13px;background:${r.avatar_color || '#3b82f6'}">${escapeHtml(initial(r.name || "?"))}</div>
          <div style="flex:1;min-width:0;">
            <div style="font-weight:600;font-size:13px;color:#1F2937;">${escapeHtml(r.name || "(이름없음)")}</div>
            <div style="font-size:11px;color:var(--text-soft);">${typeLabel}${r.item_customer ? " · " + escapeHtml(r.item_customer) : ""}</div>
          </div>
        </label>
      `;
    }).join("");
    list.querySelectorAll("input[type=checkbox]").forEach(cb => {
      cb.addEventListener("change", (e) => {
        const rid = parseInt(cb.dataset.rid, 10);
        if (cb.checked) _forwardSelected.add(rid);
        else _forwardSelected.delete(rid);
        document.getElementById("forwardCount").textContent = _forwardSelected.size;
      });
    });
    document.getElementById("forwardCount").textContent = _forwardSelected.size;
  }

  async function _confirmForward() {
    if (!_forwardSourceMid || _forwardSelected.size === 0) {
      alert("전달할 방을 1개 이상 선택하세요.");
      return;
    }
    const comment = (document.getElementById("forwardComment")?.value || "").trim();
    const btn = document.getElementById("forwardConfirmBtn");
    const prevText = btn.textContent;
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
      alert(`✅ ${res.count}개 방으로 전달 완료`);
    } catch (e) {
      alert("❌ 네트워크 오류");
    } finally {
      btn.disabled = false;
      btn.textContent = prevText;
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
      // 모바일 롱프레스 (0.5초) — 시각 피드백·햅틱·iOS callout 차단
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
        }, 500);
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
          alert("원본 메시지가 현재 보이는 범위에 없습니다. 위로 스크롤해 주세요.");
        }
      });
    });
    // 모바일에서 메시지 버블 탭하면 액션바 토글
    wireMessageTapToggle();


    // ─── 우클릭/long-press 컨텍스트 메뉴 ───
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
      // 모바일: long-press (500ms)
      let touchTimer = null;
      let touchStartXY = null;
      li.addEventListener("touchstart", (e) => {
        // .author 는 자체 long-press 로 사용자 메뉴 (귓속말·정보 등)
        if (e.target.closest("a, button, input, textarea, .author")) return;
        const t = e.touches[0];
        touchStartXY = { x: t.clientX, y: t.clientY };
        li.classList.add("long-pressing");
        touchTimer = setTimeout(() => {
          touchTimer = null;
          li.classList.remove("long-pressing");
          // 햅틱 — Android vibrate. iOS 는 vibrate 미지원이라 long-press 시각 효과(scale)로만 피드백.
          if (navigator.vibrate) try { navigator.vibrate(40); } catch (_) {}
          showMessageContextMenu(li, touchStartXY.x, touchStartXY.y);
        }, 500);
      }, { passive: true });
      const cancelLongPress = () => {
        if (touchTimer) { clearTimeout(touchTimer); touchTimer = null; }
        li.classList.remove("long-pressing");
      };
      li.addEventListener("touchend", cancelLongPress, { passive: true });
      li.addEventListener("touchcancel", cancelLongPress, { passive: true });
      li.addEventListener("touchmove", (e) => {
        if (!touchStartXY || !touchTimer) return;
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
          openLightbox(items, startIdx, albumId);
        } else {
          // 단일 사진
          const img = a.querySelector("img");
          openLightbox([{ src: img.src, name: img.alt || "" }], 0, null);
        }
      });
    });
  }

  // ---------- 라이트박스 상태 + 조작 ----------
  const _lb = { items: [], index: 0, albumId: null };

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
  }

  function renderLightboxItem() {
    const item = _lb.items[_lb.index];
    if (!item) return;
    els.lightboxImg.src = item.src;
    els.lightboxImg.alt = item.name || "";
    els.lightboxMeta.textContent = item.name || "";
    const counter = document.getElementById("lbCounter");
    if (counter) counter.textContent = `${_lb.index + 1} / ${_lb.items.length}`;
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
    a.href = item.src;
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
  }

  async function renderItemMeta(room) {
    const isItem = room.type === "item";
    // 헤더 메타 '기본부'(프로젝트 칩) 계산. ⚠ 깜빡임 방지(대표 지시 2026-05-20, preview 실측):
    //   itemMeta 를 미리 비우거나 숨기지 않는다 — 요약까지 모은 뒤 '한 번에' 교체(중간 빈 상태 X → 헤더가 줄었다 커지지 않음).
    let basePart = "";
    if (isItem) {
      const parts = [];
      if (room.item_customer) parts.push(`<span class="customer-chip">${escapeHtml(room.item_customer)}</span>`);
      if (room.item_code) parts.push(`<span class="code-chip">${escapeHtml(room.item_code)}</span>`);
      if (room.item_status) parts.push(`<span class="status-pill status-${room.item_status}">${STATUS_LABEL[room.item_status] || room.item_status}</span>`);
      if (room.item_due) parts.push(`<span class="meta-due">납기 ${fmtDate(room.item_due)}</span>`);
      basePart = parts.join("");
      els.itemEditBtn.hidden = false;
    } else {
      els.itemEditBtn.hidden = true;
    }
    els.galleryBtn.hidden = false;
    els.requestsBtn.hidden = false;
    if (els.exportBtn) els.exportBtn.hidden = false;
    // 자동 채널(전사/소속)은 나가기 금지 → 나가기 버튼 숨김 (대표 지시 2026-05-20)
    if (els.leaveRoomBtn) els.leaveRoomBtn.hidden = !!room.channel_scope;
    if (els.starredBtn) els.starredBtn.hidden = false;
    if (els.aiSummaryBtn) els.aiSummaryBtn.hidden = false;
    if (els.aiRewriteBtn) els.aiRewriteBtn.disabled = false;
    // 📚 프로젝트 이력 — 프로젝트 방에서만
    if (els.projectHistoryBtn) els.projectHistoryBtn.hidden = (room.type !== "item");
    const rsBtn = document.getElementById('roomSettingsBtn');
    if (rsBtn) rsBtn.hidden = (room.type === 'direct');  // 1:1 방은 설정 X
    if (els.headMoreBtn) els.headMoreBtn.hidden = false;  // 모바일 ⋮ 더보기
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
      if (s.image_count) items.push(`<span class="sm-item">📷 ${s.image_count}</span>`);
      if (s.file_count) items.push(`<span class="sm-item">📎 ${s.file_count}</span>`);
      if (s.open_requests) items.push(`<span class="sm-item attn">📌 ${s.open_requests} 열림</span>`);
      if (s.active_requests) items.push(`<span class="sm-item">⚙ ${s.active_requests} 진행중</span>`);
      if (s.members) items.push(`<span class="sm-item">👥 ${s.members}</span>`);
      if (items.length) summaryHtml = `<div class="summary-mini" style="width:100%">${items.join("")}</div>`;
    } catch (e) { /* ignore */ }
    // 그새 다른 방으로 바뀌었으면 새 방 헤더를 덮어쓰지 않음 (빠른 전환 경쟁 방지)
    if (!activeRoom || activeRoom.id !== room.id) return;
    const full = basePart + summaryHtml;
    els.itemMeta.innerHTML = full;
    els.itemMeta.hidden = (full === "");
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
  async function openRoom(room) {
    if (!room) return;
    // ※ emit("leave") 안 함 — 한 번 join 한 방은 계속 join 유지.
    // 다른 방으로 전환해도 그 방의 새 메시지 알림(소리·토스트·사이드바 깜빡임)을 받기 위함.
    // 서버 connect 핸들러가 모든 방 자동 join 하므로 명시적 emit("join") 도 보험 차원만.
    activeRoom = room;
    app.classList.add("viewing-chat");
    // 1:1 방 제목 — '이름 직급님-부서' 형식 (대표 지시 2026-05-19)
    await ensureUsers();
    _setChatTitleFor(room);
    // 헤더 메타는 비동기로 갱신(중간에 비우지 않아 헤더 안 흔들림). 메시지 렌더를 막지 않음 → 빠른 전환.
    renderItemMeta(room);
    els.msgInput.disabled = false;
    els.sendBtn.disabled = false;
    els.attachBtn.disabled = false;
    if (els.emojiBtn) els.emojiBtn.disabled = false;
    if (els.stickerBtn) els.stickerBtn.disabled = false;
    // 모바일에서 키보드 자동 띄움 방지 — 사용자가 입력창 누를 때만 열림
    if (window.innerWidth > 720) els.msgInput.focus();
    // 브라우저 뒤로가기 = 방 목록으로 (모바일). 로그아웃 방지.
    if (window.innerWidth <= 720 && !(history.state && history.state.knkRoom)) {
      try { history.pushState({ knkRoom: room.id }, "", `?room=${room.id}`); } catch(e) {}
    }
    socket.emit("join", { room_id: room.id });
    // 메시지 + 읽음 상태 병렬 로드
    const [msgs, rs] = await Promise.all([
      api.messages(room.id),
      api.readStatus(room.id).catch(() => ({ members: [], total: 0 })),
    ]);
    roomReadStatus = rs || { members: [], total: 0 };
    // 1:1 방 제목 정확도 보강 — readStatus 의 멤버 정보 반영 (대표 지시 2026-05-19)
    _setChatTitleFor(room);
    renderMessages(msgs);
    await api.markRead(room.id);
    _clearRoomNotifications(room.id);   // 이 방을 열어 확인 → 이 기기의 이 방 알림 즉시 닫기
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

  // 활성 방 제목 갱신 — 1:1 방은 '이름 직급님-부서' 형식, 그 외는 room.name (대표 지시 2026-05-19)
  function _setChatTitleFor(room) {
    if (!room) return;
    let title = room.name || "(이름없음)";
    if (room.type === "self") title = "📝 내 메모장";
    if (room.type === "direct") {
      try {
        // readStatus 캐시(roomReadStatus) 또는 users 캐시에서 상대방 정보 추출
        let other = null;
        if (roomReadStatus && roomReadStatus.members) {
          other = roomReadStatus.members.find(u => u && u.user_id !== meId);
        }
        const cached = other ? (users.find(u => u.id === other.user_id) || {}) : (users.find(u => u.display_name === room.name) || {});
        const dispName = cached.display_name || (other && other.display_name) || room.name || "";
        const titleStr = cached.title || (other && other.title) || "";
        const department = cached.department || (other && other.department) || "";
        if (dispName) {
          let name = dispName;
          if (titleStr) name += ` ${titleStr}님`;
          else name += "님";
          if (department) {
            const dept = (typeof deptShortLabel === "function") ? deptShortLabel(department) : department;
            title = `${name}-${dept}`;
          } else {
            title = name;
          }
        }
      } catch(e) {}
    }
    els.chatTitle.textContent = title;
    els.chatTitle.title = title;
  }

  async function refreshRooms() {
    rooms = await api.rooms();
    try { _syncAppBadge(); } catch (e) {}   // 앱 아이콘 배지 = 전체 안 읽은 합 (읽으면 감소 반영)
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

  // 특정 방의 OS 푸시 알림(tag=room_<id>)을 닫음. (대표 지시 2026-05-20)
  //  같은 기기에서 그 방을 열어/보고 확인하면, 알림을 직접 누르지 않아도 자동으로 사라지게.
  //  (다른 기기 — 백그라운드 휴대폰 — 는 서버가 보내는 clear 푸시를 sw.js 가 받아서 닫음)
  function _clearRoomNotifications(roomId) {
    if (!roomId || !("serviceWorker" in navigator)) return;
    try {
      navigator.serviceWorker.getRegistration().then(reg => {
        if (!reg || !reg.getNotifications) return;
        const tag = "room_" + roomId;
        const closeMatching = (notes) => notes.forEach(n => {
          if (n.tag === tag) { try { n.close(); } catch (e) {} }
        });
        reg.getNotifications({ tag }).then(closeMatching).catch(() => {});
        reg.getNotifications().then(closeMatching).catch(() => {});  // tag 필터 부정확한 브라우저 대비
      }).catch(() => {});
    } catch (e) {}
  }

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

  function applyComposerLangUI() {
    if (!activeRoom || !els.composerLangbar) return;
    const mode = getRoomTranslateMode(activeRoom.id);
    els.composerLangbar.querySelectorAll(".cl-chip").forEach(c => {
      c.dataset.active = (c.dataset.lang === mode) ? "1" : "0";
    });
    // 컴포저 보더 색 — 시각적 안전망
    const composer = $("composer");
    composer.classList.remove("tr-vi", "tr-en", "tr-ko");
    if (mode) composer.classList.add("tr-" + mode);
    // 힌트 텍스트
    const hints = {
      "":   "",
      "vi": "전송 시 베트남어 자동 첨부",
      "en": "전송 시 영어 자동 첨부",
      "ko": "전송 시 한국어 자동 첨부",
    };
    if (els.composerLangHint) els.composerLangHint.textContent = hints[mode] || "";
    // placeholder 도 살짝 변경
    if (mode) {
      els.msgInput.placeholder = `메시지 입력... (자동 번역 ON)`;
    } else {
      els.msgInput.placeholder = "메시지 입력...";
    }
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
    const text = els.msgInput.value.trim();
    if (!text || !activeRoom) return;

    const mode = getRoomTranslateMode(activeRoom.id);

    if (!mode) {
      // 평소 동작 — 빠른 socket 송신 (인용 답장이면 quoted_message_id 포함)
      const payload = { room_id: activeRoom.id, content: text };
      if (_pendingQuoteMid) payload.quoted_message_id = _pendingQuoteMid;
      if (_pendingWhisperUid) payload.whisper_to_user_id = _pendingWhisperUid;
      socket.emit("send", payload);
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
      const r = await fetch(BASE + "/api/messages/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          room_id: activeRoom.id,
          content: text,
          translate_to: [mode],
        }),
      });
      const data = await r.json();
      if (!r.ok) {
        const errMsg = data.error || `HTTP ${r.status}`;
        // 번역 서비스 미설정 — langbar 자동 숨김 + 친절한 안내 (대표 지시 2026-05-19)
        if (errMsg.includes("번역") || errMsg.includes("ANTHROPIC") || errMsg.includes("translat")) {
          alert(`번역 기능을 사용할 수 없습니다.\n\n관리자가 번역 API 를 설정한 후 사용할 수 있습니다.\n원문은 번역 없이 전송됩니다.`);
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
          alert(`전송 실패: ${errMsg}\n${data.hint || ""}`);
          // 실패 시 원문 복원
          els.msgInput.value = text;
          autoGrowMsgInput();
        }
      }
      // 성공 시: socket new_message 가 자동으로 화면에 추가하므로 별도 처리 X
    } catch (e) {
      alert("네트워크 오류 — 메시지 전송 실패");
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
      alert(`다음 파일이 500MB 를 초과하여 업로드할 수 없습니다:\n\n${names}\n\n파일을 압축하거나 분할 후 다시 시도하세요.`);
      return;
    }
    if (files.length > COUNT_LIMIT) {
      alert(`한 번에 최대 ${COUNT_LIMIT}개 파일까지 첨부 가능합니다. (선택: ${files.length}개)\n\n나눠서 보내주세요.`);
      return;
    }
    const totalSize = files.reduce((s, f) => s + f.size, 0);
    if (totalSize > TOTAL_LIMIT) {
      alert(`첨부 파일 합계가 1GB 를 초과합니다 (현재 ${(totalSize/1024/1024).toFixed(1)}MB).\n\n나눠서 보내주세요.`);
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
          alert(`업로드 실패: ${f.name}\n${res.error}`);
        }
      } catch (e) {
        const msg = (e && e.error) || "네트워크 오류";
        alert(`업로드 실패: ${f.name}\n${msg}\n\n파일이 너무 크거나 (서버 한도 초과) 네트워크가 끊겼을 수 있습니다.`);
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
    const title = u.title || "";
    const dept = u.department || "";
    const deptLabel = dept ? (typeof deptDisplayLabel === "function" ? deptDisplayLabel(dept) : dept) : "";
    const haystack = [u.display_name, title, dept, deptLabel, u.username || ""].join(" ").toLowerCase();
    // 메타 라인 — '직급 · 부서' / 둘 다 없으면 username
    const metaParts = [];
    if (title) metaParts.push(escapeHtml(title));
    if (deptLabel) metaParts.push(escapeHtml(deptLabel));
    const metaText = metaParts.length ? metaParts.join(" · ") : escapeHtml(u.username || "");
    return `
      <label data-search="${escapeHtml(haystack)}">
        <input type="checkbox" value="${u.id}">
        <div class="avatar" style="width:26px;height:26px;font-size:11px;background:${u.avatar_color}">${escapeHtml(initial(u.display_name))}</div>
        <div class="user-picker-info">
          <div class="user-picker-name">${escapeHtml(u.display_name)}</div>
          <div class="user-picker-meta">${metaText}</div>
        </div>
      </label>`;
  }

  // 사용자 picker 검색 필터 — 입력에 따라 행 hidden 토글 + 매칭 카운트 표시
  function _wireUserPickerSearch(searchInputId, pickerId, countId) {
    const input = document.getElementById(searchInputId);
    const picker = document.getElementById(pickerId);
    const countEl = document.getElementById(countId);
    if (!input || !picker) return;
    const update = () => {
      const q = input.value.trim().toLowerCase();
      const labels = picker.querySelectorAll("label[data-search]");
      let visible = 0, total = labels.length, checked = 0;
      labels.forEach(lb => {
        const hay = lb.getAttribute("data-search") || "";
        const match = !q || hay.includes(q);
        lb.style.display = match ? "" : "none";
        if (match) visible++;
        if (lb.querySelector("input:checked")) checked++;
      });
      if (countEl) {
        countEl.textContent = checked > 0
          ? `${checked}명 선택 · ${q ? `검색 ${visible}/${total}` : `전체 ${total}명`}`
          : (q ? `${visible}/${total}명` : `${total}명`);
      }
    };
    // 입력·체크 변화 시 카운트 갱신
    input.addEventListener("input", update);
    picker.addEventListener("change", update);
    // 최초 렌더 후 1회 카운트 표시
    requestAnimationFrame(update);
  }

  async function ensureUsers() {
    if (!users.length) users = await api.users();
    try { _updateMeHeaderInfo(); } catch(e) {}
    return users;
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
    const html = others.map(userPickerHtml).join("");
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
    // 채널 탭 — 관리자(ceo) 또는 팀장만 노출 (대표 지시 2026-05-21)
    const _chTab = els.newRoomDialog.querySelector('[data-tab="channel"]');
    if (_chTab) _chTab.style.display = (window._meRole === "ceo" || window._meIsTeamLead) ? "" : "none";
    setTab("item");
    els.newRoomDialog.showModal();
    // 프로젝트 탭 열린 후 검색 입력에 포커스 (바로 타이핑 가능)
    // 모바일에서는 자동 포커스 안 함 — 키보드가 즉시 올라와 다이얼로그를 가리는 문제 회피.
    // 사용자가 의도적으로 검색창 탭하면 그때 자동 스크롤.
    if (!window.matchMedia("(max-width: 720px)").matches) {
      setTimeout(() => { try { document.getElementById("itemUserSearch")?.focus(); } catch(e){} }, 50);
    }
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
      if (!name) { alert("프로젝트 이름은 필수입니다."); return; }
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
      if (window._meRole !== "ceo" && !window._meIsTeamLead) { alert("채널은 관리자 또는 팀장만 만들 수 있습니다."); return; }
      const checked = [...document.querySelectorAll('#channelUserPicker input:checked')].map(c => parseInt(c.value, 10));
      if (!checked.length) { alert("채널에 참여할 사람을 1명 이상 선택하세요."); return; }
      const nm = (document.getElementById('channelName')?.value || "").trim();
      if (!nm) { alert("채널 이름을 입력하세요."); return; }
      const payload = { user_ids: [...checked, meId], type: "channel", name: nm };
      if (document.getElementById('channelNameLock')?.checked) payload.name_locked = true;
      const res = await api.createRoom(payload);
      if (res.error) { alert(res.error); return; }
      els.newRoomDialog.close();
      await refreshRooms();
      const room = rooms.find(r => r.id === res.id);
      if (room) openRoom(room);
    } else {
      // 1:1 / 그룹
      const checked = [...els.userPicker.querySelectorAll("input:checked")].map(c => parseInt(c.value, 10));
      if (!checked.length) { alert("상대를 1명 이상 선택하세요."); return; }
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
    if (role === 'host') return '<span class="rs-badge rs-host">👑 방장</span>';
    if (role === 'sub_host') return '<span class="rs-badge rs-sub">⭐ 부방장</span>';
    return '';
  }

  function _renderRoomSettings() {
    const data = _currentRoomSettings;
    if (!data) return;
    const { room, members, my_role, my_alias } = data;
    const isHost = my_role === 'host';
    const isCeo = (window._meRole === "ceo");   // 관리자는 모든 방 이름 변경 가능 (대표 지시 2026-05-20)
    const isSub = my_role === 'sub_host';
    const canInvite = isHost || isSub;
    const dlg = document.getElementById('roomSettingsDialog');
    const typeLabel = document.getElementById('rsRoomTypeLabel');
    typeLabel.textContent = room.type === 'item' ? '프로젝트 방' : (room.type === 'direct' ? '1:1 대화' : '그룹 대화');

    // 이름 영역 — 맨 위에 음소거 토글 행 (모든 방 공통)
    const nameArea = document.getElementById('rsNameArea');
    const isMuted = notifySettings.isRoomMuted(room.id);
    let nameHtml = `
      <div class="rs-mute-row" style="display:flex;align-items:center;gap:10px;padding:10px 12px;background:${isMuted ? '#FEF2F2' : '#F9FAFB'};border:1px solid var(--border);border-radius:8px;margin-bottom:14px;cursor:pointer;" id="rsMuteRow">
        <span style="font-size:22px;">${isMuted ? '🔕' : '🔔'}</span>
        <div style="flex:1;">
          <div style="font-weight:600;font-size:13px;">${isMuted ? '이 방 알림 음소거 중' : '이 방 알림 받기'}</div>
          <div style="font-size:11.5px;color:var(--text-soft);">${isMuted ? '소리·시스템 알림·토스트 모두 꺼짐 (배지·미읽기 카운트는 그대로)' : '소리·화면·시스템 알림 정상 동작'}</div>
        </div>
        <button type="button" class="primary-btn" id="rsMuteToggleBtn" style="background:${isMuted ? '#10b981' : 'var(--accent)'};">${isMuted ? '🔔 다시 받기' : '🔕 음소거'}</button>
      </div>
    `;
    if (room.type === 'direct') {
      nameHtml += `<div class="rs-readonly">1:1 방은 상대방 이름으로 자동 표시됩니다.</div>`;
    } else if (room.type === 'self') {
      // 내 메모장 — 이름은 고정(📝 내 메모장). 이름 입력란 미표시 (대표 지시 2026-05-20)
    } else if (isHost || isCeo) {
      nameHtml += `
        <div class="rs-form">
          <input id="rsRoomNameInput" type="text" maxlength="100" value="${escapeHtml(room.name || '')}" placeholder="방 이름">
          <label class="rs-checkbox">
            <input id="rsNameLockCheck" type="checkbox" ${room.name_locked ? 'checked' : ''}>
            <span>이름 고정 (멤버 별명 금지)</span>
          </label>
          <button type="button" id="rsRenameBtn" class="primary-btn">이름 저장</button>
        </div>
        <div class="rs-hint">${isHost ? '방장' : '관리자'} 권한으로 모든 멤버에게 보이는 이름을 변경합니다.</div>
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
    // 채널/방 아이콘 사진 — 관리자(ceo) 전용 (대표 지시 2026-05-20)
    if (isCeo && room.type !== 'direct' && room.type !== 'self') {
      const curAv = room.avatar_url
        ? `<img src="${escapeHtml(room.avatar_url)}" style="width:46px;height:46px;border-radius:50%;object-fit:cover;border:1px solid var(--border);">`
        : `<div style="width:46px;height:46px;border-radius:50%;background:#e5e7eb;display:grid;place-items:center;font-size:10px;color:#9ca3af;text-align:center;line-height:1.1;">사진<br>없음</div>`;
      nameHtml += `
        <div class="rs-form" style="display:flex;align-items:center;gap:10px;margin-top:12px;">
          <div id="rsRoomAvatarPreview">${curAv}</div>
          <input type="file" id="rsRoomAvatarFile" accept="image/*" style="display:none;">
          <button type="button" id="rsRoomAvatarBtn" class="primary-btn">아이콘 사진 ${room.avatar_url ? '변경' : '올리기'}</button>
          ${room.avatar_url ? '<button type="button" id="rsRoomAvatarDelBtn" class="secondary-btn">제거</button>' : ''}
        </div>
        <div class="rs-hint">🔒 관리자 전용 — 채널/방 아이콘에 사진을 설정합니다 (jpg·png·webp·gif, 5MB 이하).</div>
      `;
    }
    nameArea.innerHTML = nameHtml;

    // 멤버 목록
    document.getElementById('rsMemberCount').textContent = members.length;
    const memberList = document.getElementById('rsMemberList');
    memberList.innerHTML = members.map(m => {
      const isMe = m.id === meId;
      let actions = '';
      if (!isMe) {
        if (isHost) {
          // 방장: 부방장 토글, 일반 멤버로, 방장 위임, 내보내기 — 짧은 라벨 (대표 지시 2026-05-19)
          if (m.role === 'sub_host') {
            actions += `<button class="rs-act-btn" data-act="demote" data-uid="${m.id}" title="일반 멤버로 강등">⭐→👤</button>`;
          } else if (m.role === 'member') {
            actions += `<button class="rs-act-btn" data-act="promote" data-uid="${m.id}" title="부방장 지정">⭐ 부방장</button>`;
          }
          actions += `<button class="rs-act-btn rs-danger" data-act="transfer" data-uid="${m.id}" title="방장 위임">👑 위임</button>`;
          actions += `<button class="rs-act-btn rs-danger" data-act="kick" data-uid="${m.id}" title="이 멤버를 방에서 내보내기">🚪 제외</button>`;
        } else if (isSub && m.role === 'member') {
          actions += `<button class="rs-act-btn rs-danger" data-act="kick" data-uid="${m.id}" title="이 멤버를 방에서 내보내기">🚪 제외</button>`;
        }
      }
      // 직급·부서 메타 라인 (대표 지시 2026-05-19) — users 캐시에서 보강
      const cached = (Array.isArray(users) ? users.find(u => u.id === m.id) : null) || {};
      const metaTitle = cached.title || m.title || "";
      const metaDept = cached.department || m.department || "";
      const metaParts = [];
      if (metaTitle) metaParts.push(escapeHtml(metaTitle));
      if (metaDept) {
        const deptLabel = (typeof deptDisplayLabel === "function") ? deptDisplayLabel(metaDept) : metaDept;
        metaParts.push(escapeHtml(deptLabel));
      }
      const metaLine = metaParts.length ? `<div class="rs-member-meta">${metaParts.join(" · ")}</div>` : "";
      return `
        <div class="rs-member">
          <div class="rs-member-info">
            <span class="avatar" style="background:${m.avatar_color};width:28px;height:28px;font-size:12px">${escapeHtml(m.display_name[0])}</span>
            <div style="min-width:0;flex:1;">
              <div class="rs-member-name">${escapeHtml(m.display_name)}${isMe ? ' <span class="rs-me">(나)</span>' : ''}</div>
              ${metaLine}
              <div class="rs-member-role">${_badgeForRole(m.role)}</div>
            </div>
          </div>
          ${actions ? `<div class="rs-member-actions">${actions}</div>` : ''}
        </div>
      `;
    }).join('');

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
            <select id="rsRetentionSelect" style="padding:8px;border:1px solid var(--border);border-radius:6px;font-size:13px;">
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
        const labelOf = (p) => p === 'host_only' ? '👑 방장·부방장만' : '👥 모든 멤버 가능 (기본)';
        if (isHost) {
          ipArea.innerHTML = `
            <div class="rs-form" style="flex-direction:column;align-items:stretch;gap:8px;">
              <label class="rs-checkbox" style="display:flex;align-items:flex-start;gap:8px;cursor:pointer;padding:8px 10px;border:2px solid ${curPolicy === 'all' ? 'var(--accent)' : '#E5E7EB'};border-radius:6px;background:${curPolicy === 'all' ? '#FEF2F2' : '#fff'};">
                <input type="radio" name="rsIp" value="all" ${curPolicy === 'all' ? 'checked' : ''} style="margin-top:3px;">
                <span>
                  <div style="font-weight:600;font-size:13px;">👥 모든 멤버 초대 가능 <span style="font-size:11px;color:var(--text-soft);">(기본)</span></div>
                  <div style="font-size:11.5px;color:var(--text-soft);">방의 누구나 새 멤버를 초대할 수 있음</div>
                </span>
              </label>
              <label class="rs-checkbox" style="display:flex;align-items:flex-start;gap:8px;cursor:pointer;padding:8px 10px;border:2px solid ${curPolicy === 'host_only' ? 'var(--accent)' : '#E5E7EB'};border-radius:6px;background:${curPolicy === 'host_only' ? '#FEF2F2' : '#fff'};">
                <input type="radio" name="rsIp" value="host_only" ${curPolicy === 'host_only' ? 'checked' : ''} style="margin-top:3px;">
                <span>
                  <div style="font-weight:600;font-size:13px;">👑 방장·부방장만 초대 가능</div>
                  <div style="font-size:11.5px;color:var(--text-soft);">일반 멤버는 초대 불가 — 폐쇄형 방</div>
                </span>
              </label>
              <button type="button" id="rsIpSaveBtn" class="primary-btn">초대 권한 저장</button>
            </div>
            <div class="rs-hint">⚠ 내보내기 권한은 항상 방장·부방장만 가능 (이 설정과 무관).</div>
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
      if (!newName) { alert('이름을 입력하세요.'); return; }
      const locked = document.getElementById('rsNameLockCheck').checked;
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
          alert('업로드 오류: ' + (e.message || e));
          avBtn.disabled = false; avBtn.textContent = "아이콘 사진 올리기"; return;
        }
        await refreshRooms();
        await openRoomSettings(room.id);
      };
    }
    const avDel = document.getElementById('rsRoomAvatarDelBtn');
    if (avDel) avDel.onclick = async () => {
      if (!confirm('아이콘 사진을 제거할까요? (기본 색 아이콘으로 돌아감)')) return;
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
        && (isCeo || (window._meIsTeamLead && room.created_by === meId));
      chDelSec.style.display = canDeleteChannel ? "" : "none";
      chDelBtn.onclick = async () => {
        const nm = roomFull.name || room.name || '이 채널';
        if (!confirm(`⚠ 채널 "${nm}" 을(를) 영구 삭제할까요?\n모든 대화·첨부가 사라지며 되돌릴 수 없습니다.`)) return;
        const res = await fetch(`${BASE}/api/rooms/${room.id}`, { method: 'DELETE' }).then(r => r.json()).catch(e => ({ error: String(e) }));
        if (res.error) { alert("❌ " + res.error); return; }
        alert(`✅ 채널이 삭제되었습니다: ${res.deleted}`);
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
        if (act === 'promote') {
          await api.setMemberRole(room.id, uid, 'sub_host');
        } else if (act === 'demote') {
          await api.setMemberRole(room.id, uid, 'member');
        } else if (act === 'transfer') {
          if (!confirm(`[${member.display_name}] 님에게 방장을 위임합니다. 본인은 일반 멤버가 됩니다. 진행할까요?`)) return;
          await api.transferHost(room.id, uid);
        } else if (act === 'kick') {
          if (!confirm(`[${member.display_name}] 님을 방에서 내보낼까요?`)) return;
          await api.kickMember(room.id, uid);
        }
        await openRoomSettings(room.id);
      };
    });

    document.getElementById('rsInviteBtn').onclick = () => openInviteDialog(room.id, members);

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
      picker.innerHTML = candidates.map(userPickerHtml).join('');
    }
    const dlg = document.getElementById('inviteDialog');
    const confirmBtn = document.getElementById('confirmInvite');
    confirmBtn.onclick = async () => {
      const ids = [...picker.querySelectorAll('input:checked')].map(c => parseInt(c.value, 10));
      if (!ids.length) { alert('초대할 사람을 선택하세요.'); return; }
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
          <a href="${BASE}/uploads/${escapeHtml(m.file_path)}" download="${escapeHtml(m.file_name || "")}">받기</a>
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
  async function openRequests() {
    if (!activeRoom) return;
    activeReqTab = "open";
    els.requestsDialog.querySelectorAll(".gtab").forEach(t => {
      t.classList.toggle("active", t.dataset.rtab === "open");
    });
    await renderRequests();
    if (!els.requestsDialog.open) els.requestsDialog.showModal();
  }

  async function renderRequests() {
    if (!activeRoom) return;
    const data = await api.requests(activeRoom.id, activeReqTab);
    els.requestsCount.textContent = data.length;
    if (!data.length) {
      els.requestsList.innerHTML = `<div class="empty-state" style="padding:32px;color:var(--text-soft);">${activeReqTab === "open" ? "열린 요청이 없습니다. 일반 메신저와 다르게 — 묻혀서 잃어버리는 요청은 이제 없습니다." : "해당 상태의 요청이 없습니다."}</div>`;
      return;
    }
    els.requestsList.innerHTML = data.map(reqItemHtml).join("");
    els.requestsList.querySelectorAll("[data-req-act]").forEach(b => {
      b.addEventListener("click", async () => {
        const id = parseInt(b.dataset.reqId, 10);
        const act = b.dataset.reqAct;
        if (act === "start") await api.updateRequest(id, { status: "in_progress" });
        else if (act === "done") await api.updateRequest(id, { status: "done" });
        else if (act === "cancel") {
          if (!confirm("이 요청을 취소하시겠습니까?")) return;
          await api.updateRequest(id, { status: "cancelled" });
        } else if (act === "reopen") await api.updateRequest(id, { status: "open" });
        await renderRequests();
        await refreshRequestsBadge();
      });
    });
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
    const assigned = q.assigned_to_name
      ? `<span>👤 ${escapeHtml(q.assigned_to_name)}</span>`
      : `<span style="color:#d97706;font-weight:700">👤 미지정</span>`;
    const priority = q.priority === "high" ? `<span class="req-priority-high">긴급</span>` : "";
    let actions = "";
    if (q.status === "open") {
      actions = `
        <button class="req-action-btn primary" data-req-act="start" data-req-id="${q.id}">시작</button>
        <button class="req-action-btn" data-req-act="done" data-req-id="${q.id}">바로 완료</button>
        <button class="req-action-btn" data-req-act="cancel" data-req-id="${q.id}">취소</button>`;
    } else if (q.status === "in_progress") {
      actions = `
        <button class="req-action-btn primary" data-req-act="done" data-req-id="${q.id}">완료</button>
        <button class="req-action-btn" data-req-act="cancel" data-req-id="${q.id}">취소</button>`;
    } else {
      actions = `<button class="req-action-btn" data-req-act="reopen" data-req-id="${q.id}">다시 열기</button>`;
    }
    return `
      <div class="${cls}">
        <div class="req-head">
          <div class="req-title">${priority} ${escapeHtml(q.title)}</div>
          <span class="req-status req-status-${q.status}">${REQ_STATUS_LABEL[q.status] || q.status}</span>
        </div>
        ${q.description ? `<div class="req-desc">${escapeHtml(q.description)}</div>` : ""}
        <div class="req-meta">
          <span>요청 ${escapeHtml(q.requested_by_name || "")}</span>
          ${assigned}
          ${dueText}
          <span style="color:#9ca3af">· ${fmtTime(q.created_at)}</span>
        </div>
        <div class="req-actions">${actions}</div>
      </div>`;
  }

  async function openNewRequest({ messageId = null, sourceContent = "" } = {}) {
    await ensureUsers();
    pendingReqMessage = messageId;
    els.reqAssignedTo.innerHTML = `<option value="">(미지정)</option>` +
      users
        .filter(u => u.username !== "_deleted_user" && u.active !== 0)
        .map(u => {
          // 담당자 드롭다운에도 직급·부서 함께 표기 (대표 지시 2026-05-20)
          const title = u.title || "";
          const dept = u.department || "";
          const deptLabel = dept ? ((typeof deptDisplayLabel === "function") ? deptDisplayLabel(dept) : dept) : "";
          const meta = [title, deptLabel].filter(Boolean).join(" · ");
          const label = meta ? `${u.display_name} (${meta})` : u.display_name;
          return `<option value="${u.id}">${escapeHtml(label)}</option>`;
        }).join("");
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
    if (!title) { alert("제목은 필수입니다."); return; }
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

  async function runSearch(q) {
    q = q.trim();
    const onUsersTab = (typeof _sidebarTab !== "undefined" && _sidebarTab === "users");
    if (!q) {
      els.searchResults.hidden = true;
      els.roomList.hidden = onUsersTab ? true : false;
      // 사용자 탭 — 검색어 비우면 전체 목록 다시 표시
      if (onUsersTab) {
        window._userListQuery = "";
        if (typeof renderUserList === "function") renderUserList();
      }
      return;
    }
    // 사용자 탭 — globalSearch 를 사용자 목록 필터로 사용 (대표 지시 2026-05-19)
    //   이름·직급·부서·이메일 중 어디든 매칭. 메시지 API 호출 X.
    if (onUsersTab) {
      els.searchResults.hidden = true;
      els.roomList.hidden = true;
      els.myTasks.hidden = true;
      window._userListQuery = q.toLowerCase();
      if (typeof renderUserList === "function") renderUserList();
      return;
    }
    const data = await api.search(q);
    els.roomList.hidden = true;
    els.myTasks.hidden = true;
    els.searchResults.hidden = false;
    if (!data.length) {
      els.searchResults.innerHTML = `<div class="search-empty">"${escapeHtml(q)}" 결과 없음</div>`;
      return;
    }
    els.searchResults.innerHTML = data.map(m => {
      const chips = [];
      if (m.item_customer) chips.push(`<span class="customer-chip">${escapeHtml(m.item_customer)}</span>`);
      if (m.item_code) chips.push(`<span class="code-chip">${escapeHtml(m.item_code)}</span>`);
      if (m.result_type === "item") {
        const status = m.item_status ? `<span class="status-pill status-${m.item_status}">${STATUS_LABEL[m.item_status]}</span>` : "";
        return `
          <div class="search-result-item" data-room-id="${m.room_id}" style="border-left:3px solid #7c3aed;padding-left:9px">
            <div class="search-result-room">
              <span style="font-weight:700;font-size:11px;color:#7c3aed">📁 프로젝트</span>
              ${chips.join("")}
              ${status}
            </div>
            <div class="search-result-content"><strong>${highlight(m.room_name || "", q)}</strong>${m.item_desc ? ` — ${highlight(String(m.item_desc).slice(0,100), q)}` : ""}</div>
          </div>`;
      }
      const content = m.kind === "image" ? `🖼 ${escapeHtml(m.file_name || "사진")}` :
                      m.kind === "file" ? `📎 ${escapeHtml(m.file_name || "파일")}` :
                      m.kind === "sticker" ? `🐶 ${escapeHtml(m.content || "스티커")}` :
                      highlight(String(m.content || "").slice(0, 200), q);
      return `
        <div class="search-result-item" data-room-id="${m.room_id}">
          <div class="search-result-room">
            <span style="font-weight:700;font-size:11px;color:var(--text-soft)">💬 메시지</span>
            ${chips.join("")}
            <span style="font-weight:600">${escapeHtml(m.room_name || "")}</span>
            <span style="margin-left:auto">${fmtTime(m.created_at)}</span>
          </div>
          <div class="search-result-content"><strong>${escapeHtml(m.display_name)}:</strong> ${content}</div>
        </div>`;
    }).join("");
    els.searchResults.querySelectorAll(".search-result-item").forEach(li => {
      li.addEventListener("click", () => {
        const rid = parseInt(li.dataset.roomId, 10);
        const room = rooms.find(r => r.id === rid);
        if (room) {
          els.globalSearch.value = "";
          els.searchResults.hidden = true;
          els.roomList.hidden = false;
          openRoom(room);
        }
      });
    });
  }

  // ---------- my tasks ----------
  async function renderMyTasks() {
    const data = await api.myRequests();
    if (!data.length) {
      els.myTasks.innerHTML = `<div class="search-empty">현재 나에게 할당된 요청이 없습니다. 🎉</div>`;
      return;
    }
    els.myTasks.innerHTML = data.map(q => {
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
      return `
        <div class="task-row ${dueCls}" data-room-id="${q.room_id}">
          <div class="task-title">${escapeHtml(q.title)}</div>
          <div class="task-meta">
            ${chips.join("")}
            <span style="font-weight:600">${escapeHtml(q.room_name || "")}</span>
            <span class="task-due">${dueText}</span>
            <span class="req-status req-status-${q.status}" style="margin-left:auto">${REQ_STATUS_LABEL[q.status] || q.status}</span>
          </div>
        </div>`;
    }).join("");
    els.myTasks.querySelectorAll(".task-row").forEach(li => {
      li.addEventListener("click", () => {
        const rid = parseInt(li.dataset.roomId, 10);
        const room = rooms.find(r => r.id === rid);
        if (room) openRoom(room);
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
      const choice = await chooseAttachMode(files);
      if (choice.mode === "cancel") return;
      if (choice.mode === "album") {
        const albumId = (window.crypto && crypto.randomUUID)
          ? crypto.randomUUID()
          : `alb_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
        await uploadFiles(files, { albumId });
      } else {
        await uploadFiles(files);
      }
    });

    // paste image from clipboard
    document.addEventListener("paste", (e) => {
      if (!activeRoom) return;
      const items = e.clipboardData?.items || [];
      const files = [];
      for (const it of items) {
        if (it.kind === "file") {
          const f = it.getAsFile();
          if (f) files.push(f);
        }
      }
      if (files.length) uploadFiles(files);
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
    const _presenceDevice = window.matchMedia('(pointer: coarse)').matches ? 'mobile' : 'pc';
    let _presenceLastActive = null;  // 마지막 전송값 캐시 (중복 방지)
    function sendPresence() {
      try {
        if (!socket || !socket.connected) return;
        const active = !document.hidden && document.hasFocus();
        // 같은 값 중복 전송 방지 (블러·포커스 폭주 시 트래픽 감소)
        if (_presenceLastActive === active) return;
        _presenceLastActive = active;
        socket.emit('presence', { device: _presenceDevice, active });
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
    });
    if (socket.connected) sendPresence();
    // 가시성 변경
    document.addEventListener('visibilitychange', sendPresence);
    window.addEventListener('focus', sendPresence);
    window.addEventListener('blur', sendPresence);
    // pageshow (bfcache 복원 시 active 재인식)
    window.addEventListener('pageshow', sendPresence);

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

    // PC 활성 heartbeat — 30초마다 (서버 _PC_ACTIVE_STALE_SEC=60 보다 짧게). (2026-05-20)
    //  PC 가 진짜 focus 상태일 때만 presence(active=true) 재전송 → 서버 ts 갱신.
    //  자리비움·절전·잠금 시 heartbeat 멈춤 → 60초 후 서버가 '비활성' 판정 → 모바일 푸시 발송.
    //  (대표 지시: PC 켜둬도 자리 비우면 휴대폰 알림 오게)
    if (_presenceDevice === 'pc') {
      setInterval(() => {
        try {
          if (!socket || !socket.connected) return;
          if (!document.hidden && document.hasFocus()) {
            // active 상태 강제 재전송 (중복 방지 캐시 우회 — ts 갱신 목적)
            socket.emit('presence', { device: _presenceDevice, active: true });
          }
        } catch (e) { /* noop */ }
      }, 30000);
    }

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
        // 활성 방 메시지는 같은 기기에서 로컬로 알림을 닫으므로 서버 clear 푸시는 생략(낭비 방지)
        api.markRead(activeRoom.id, { noClearPush: true });
        _clearRoomNotifications(activeRoom.id);
      }
      refreshRooms();
      // ===== 알림 분기 (notify.trigger 내부에서 설정·음소거 추가 분기) =====
      // 🚫 DND 모드 → 모든 알림 차단 (배지·미읽기 카운트는 그대로 보임)
      if (window.KNK_DND_ACTIVE) return;
      // 기본: 창이 안 보이거나 다른 방에 있으면 알림.
      // 추가: 사용자가 "현재 방에서도 소리" 설정 켜면 → 같은 방 활성 상태에서도 소리만 재생.
      if (m.user_id !== meId && m.kind !== 'system') {
        const isFocused = document.hasFocus() && !document.hidden;
        const isThisRoomActive = activeRoom && m.room_id === activeRoom.id;
        const inActive = isFocused && isThisRoomActive;
        if (!inActive) {
          notify.trigger(m);
        } else if (notifySettings.get('currentRoomSound')
                   && notifySettings.get('soundEnabled')
                   && !notifySettings.isRoomMuted(m.room_id)) {
          // 현재 방 활성 상태 + currentRoomSound ON + soundEnabled ON → 소리만
          // (배지·토스트·시스템알림 없이 단순 audio cue)
          notify.preview();
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
      // 내 메시지의 read-badge만 다시 그리기 — 귓속말은 수신자 1명만 기준
      els.messages.querySelectorAll(".msg.mine").forEach(li => {
        const mid = parseInt(li.dataset.msgId, 10);
        const badge = li.querySelector(".read-badge");
        if (!badge) return;
        const whisperTo = parseInt(li.dataset.whisperTo, 10);
        let others;
        if (whisperTo) {
          others = roomReadStatus.members.filter(mb => mb.user_id === whisperTo);
        } else {
          others = roomReadStatus.members.filter(mb => mb.user_id !== meId);
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
    titleBlink: true,            // 탭 제목 깜빡임
    inlineToast: true,           // 화면 내 우상단 토스트
    sidebarBlink: true,          // 사이드바 방 항목 깜빡임
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
    const ORIGINAL_TITLE = document.title;
    let unreadCount = 0;
    let titleBlinkInterval = null;
    let blinkState = false;
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

    // ----- 페이지 제목 깜빡임 -----
    function updateTitle() {
      if (unreadCount === 0) {
        document.title = ORIGINAL_TITLE;
        if (titleBlinkInterval) { clearInterval(titleBlinkInterval); titleBlinkInterval = null; }
        return;
      }
      // 설정에서 OFF 면 제목 그대로
      if (!notifySettings.get('titleBlink')) {
        document.title = ORIGINAL_TITLE;
        if (titleBlinkInterval) { clearInterval(titleBlinkInterval); titleBlinkInterval = null; }
        return;
      }
      const newMsgTitle = `🔔 (${unreadCount}) 새 메시지 — KNK 메신저`;
      document.title = newMsgTitle;
      if (!titleBlinkInterval) {
        titleBlinkInterval = setInterval(() => {
          blinkState = !blinkState;
          document.title = blinkState
            ? `💬 ${unreadCount}개의 새 메시지`
            : newMsgTitle;
        }, 1500);
      }
    }

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

    // ----- 화면 내 토스트 — PC 메신저 스타일 (우하단 슬라이드업, 누적) -----
    function getToastContainer() {
      let c = document.querySelector('.toast-container');
      if (!c) {
        c = document.createElement('div');
        c.className = 'toast-container';
        document.body.appendChild(c);
      }
      return c;
    }
    function showInlineToast(msg, senderName, roomName) {
      const container = getToastContainer();
      const t = document.createElement('div');
      t.className = 'inline-toast';
      const body = msg.kind === 'image' ? '📷 사진'
                 : msg.kind === 'file'  ? '📎 ' + (msg.file_name || '파일')
                 : msg.kind === 'sticker' ? '🐶 ' + (msg.content || '스티커')
                 : (msg.content || '').slice(0, 100);
      t.innerHTML = `
        <button type="button" class="it-close" aria-label="닫기">✕</button>
        <div class="it-sender">${escapeHtml(senderName)} — ${escapeHtml(roomName)}</div>
        <div class="it-body">${escapeHtml(body)}</div>
      `;
      // 새 토스트는 컨테이너 맨 아래에 들어와 위로 슬라이드업
      // (column 정렬이라 appendChild 가 시각적으로 가장 아래 = 화면상 가장 아래)
      container.appendChild(t);
      // 토스트가 너무 많이 쌓이지 않게 — 최대 5개. 초과 시 가장 위(가장 오래된) 제거.
      while (container.children.length > 5) {
        container.firstElementChild.remove();
      }
      // 클릭 → 해당 방 열기
      const goRoom = (e) => {
        if (e.target.closest('.it-close')) return;
        const r = rooms.find(x => x.id === msg.room_id);
        if (r) {
          window.focus();
          openRoom(r);
        }
        t.remove();
      };
      t.addEventListener('click', goRoom);
      t.querySelector('.it-close').addEventListener('click', (e) => { e.stopPropagation(); t.remove(); });
      // 5초 후 페이드 아웃 → 제거
      setTimeout(() => t.classList.add('it-fade'), 4500);
      setTimeout(() => { try { t.remove(); } catch(e) {} }, 5000);
    }

    // ----- 사이드바 방 항목 깜빡임 — 0.7s × 6회 ≈ 4.2초 -----
    function blinkSidebarRoom(roomId) {
      const li = els.roomList && els.roomList.querySelector(`li[data-room-id="${roomId}"]`);
      if (!li) return;
      li.classList.remove('blink');     // 진행 중이면 리셋
      void li.offsetWidth;              // reflow 강제로 animation 재시작
      li.classList.add('blink');
      setTimeout(() => li.classList.remove('blink'), 4500);
    }

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
      // 같은 방 연속 메시지 5초 내 중복 알림 차단 (사이드바 깜빡임은 별도 처리)
      if (notifySettings.get('sidebarBlink')) {
        blinkSidebarRoom(msg.room_id);
      }
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

      // 화면 내 토스트
      if (notifySettings.get('inlineToast')) {
        showInlineToast(msg, senderName, roomName);
      }

      // 시스템 알림 (OS 토스트)
      if (!notifySettings.get('systemNotification')) return;
      const ok = await ensurePermission();
      if (!ok) return;
      try {
        const n = new Notification(`${senderName} — ${roomName}`, {
          body,
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
    app.classList.remove("viewing-chat");
    // ※ emit("leave") 안 함 — 모든 방 join 유지해서 알림 받음. activeRoom 만 null 처리.
    activeRoom = null;
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

  // 브라우저 뒤로가기 = 방목록으로 (로그아웃 X)
  window.addEventListener("popstate", () => {
    if (app.classList.contains("viewing-chat")) {
      leaveRoomView({ fromPopstate: true });
    }
  });

  // ===== 모바일 키보드 가림 방지 (visualViewport 정밀 처리) =====
  // iOS Safari / Android Chrome 의 키보드가 올라올 때:
  //   - visualViewport.height: 키보드 뺀 실제 가시 영역
  //   - visualViewport.offsetTop: 페이지 자체가 스크롤된 만큼
  // chat-app 의 height 를 vvh 로 잡으면 키보드 위만큼만 차지 → composer 자동으로 보임
  // ===== VirtualKeyboard API (Chrome 94+) — 키보드 영역 명시 추적 =====
  // 이걸 활성화하면 env(keyboard-inset-height) CSS 변수가 동작하고
  // visualViewport 이벤트도 더 안정적으로 발생
  if ('virtualKeyboard' in navigator) {
    try { navigator.virtualKeyboard.overlaysContent = true; } catch (e) {}
  }

  // composer-area 는 position:fixed; bottom:0; 으로 layout viewport 하단 고정
  // 키보드 올라오면 visual viewport 가 줄어들지만 layout viewport(window.innerHeight)는 유지됨 (Samsung 등)
  // → 그 차이만큼 composer-area 를 transform: translateY(-gap) 으로 위로 밀어 키보드 바로 위 배치
  const updateViewport = () => {
    const vv = window.visualViewport;
    const innerH = window.innerHeight;
    let vvH = vv ? Math.round(vv.height) : innerH;
    let vvOffsetTop = vv ? Math.round(vv.offsetTop) : 0;

    // VirtualKeyboard API 가능하면 그 값을 우선 사용 (가장 정확)
    let kbH = 0;
    if ('virtualKeyboard' in navigator && navigator.virtualKeyboard.boundingRect) {
      kbH = Math.round(navigator.virtualKeyboard.boundingRect.height || 0);
      if (kbH > 0) {
        // VirtualKeyboard 가 키보드 높이를 정확히 알려주면 그걸 우선
        vvH = innerH - kbH;
      }
    }

    document.documentElement.style.setProperty('--vvh', vvH + 'px');
    // body·chat-app 의 inline height 강제는 진짜 모바일(터치)만.
    // ★ 핵심: pointer:coarse 단독으로 판정. (max-width:720px OR 는 PC 의 좁은 PWA 창도
    //   모바일로 잘못 매칭해서 zoom 0.72 환경의 CSS calc 를 덮어쓰게 됨 → 빈 영역 발생.)
    const isMobileEnv = window.matchMedia('(pointer: coarse)').matches;
    if (isMobileEnv && document.body.classList.contains('chat-body')) {
      document.body.style.height = vvH + 'px';
      const _chatApp = document.querySelector('.chat-app');
      if (_chatApp) _chatApp.style.height = vvH + 'px';
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
      // composer 위치 보정(translateY)은 '모바일 키보드 추적' 전용.
      // 데스크탑(마우스)에선 가로 스크롤바 등으로 gap 이 생겨 컴포저가 떠오르거나 흔들릴 수 있어 적용 안 함. (대표 지시 2026-05-20)
      if (isMobileEnv) {
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
    // 메시지 영역을 가장 아래로 — 사용자가 맨 아래 근처면 force, 위쪽 보고 있으면 유지
    if (els.messages && els.messages.scrollHeight > 0) {
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
        if (els.messages) {
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
      // 사용자 탭에서 방 필터 칩(전체/프로젝트/1:1/그룹/채널/내 요청)을 누르면
      // 자동으로 '방' 탭으로 전환 (대표 지시 2026-05-20)
      if (typeof _sidebarTab !== "undefined" && _sidebarTab !== "rooms") {
        setSidebarTab("rooms");
      }
      activeFilter = c.dataset.filter;
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
  els.fileInput.addEventListener("change", async () => {
    // ★ input.files 는 live FileList — input.value="" 직후 비워짐.
    //   uploadFiles 가 async 라 await 중에 두번째 파일을 잃지 않도록
    //   먼저 정적 배열로 복사한 뒤 input.value 를 초기화한다.
    const picked = Array.from(els.fileInput.files);
    els.fileInput.value = "";
    if (!picked.length) return;
    const choice = await chooseAttachMode(picked);
    if (choice.mode === "cancel") return;
    if (choice.mode === "album") {
      const albumId = (window.crypto && crypto.randomUUID)
        ? crypto.randomUUID()
        : `alb_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
      await uploadFiles(picked, { albumId });
    } else {
      await uploadFiles(picked);
    }
  });

  if (els.exportBtn) {
    els.exportBtn.addEventListener("click", () => {
      if (!activeRoom) return;
      window.location.href = `${BASE}/api/rooms/${activeRoom.id}/export.xlsx`;
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
      alert("나가기 실패: " + e.message + "\n\n서버 재시작이 필요할 수 있습니다.");
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
      els.leaveRoomDialog.classList.add("open");
    });
  }
  if (els.leaveWithExportBtn) els.leaveWithExportBtn.addEventListener("click", () => doLeaveRoom(true));
  if (els.leaveJustBtn) els.leaveJustBtn.addEventListener("click", () => {
    if (!confirm("정말 나가시겠습니까? Excel 저장 없이 즉시 나갑니다.")) return;
    doLeaveRoom(false);
  });
  els.galleryBtn.addEventListener("click", () => openGallery("image"));
  els.closeGallery.addEventListener("click", () => els.galleryDialog.close());
  els.galleryDialog.querySelectorAll(".gtab").forEach(t => {
    t.addEventListener("click", () => openGallery(t.dataset.gtab));
  });
  els.requestsBtn.addEventListener("click", openRequests);
  if (els.starredBtn) els.starredBtn.addEventListener("click", showStarredDialog);

  // 모바일 ⋮ 더보기 메뉴 — 클릭 시 토글, 항목 클릭 시 해당 기존 버튼 트리거
  if (els.headMoreBtn && els.headMoreMenu) {
    let backdrop = null;
    const openMenu = () => {
      // hidden 안 된 버튼만 메뉴에 표시
      els.headMoreMenu.querySelectorAll("button[data-act]").forEach(b => {
        const map = { requests: "requestsBtn", starred: "starredBtn", gallery: "galleryBtn", export: "exportBtn", edit: "itemEditBtn", leave: "leaveRoomBtn" };
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
      if (b.dataset.act === 'settings') {
        openRoomSettings();
        return;
      }
      const map = { requests: "requestsBtn", starred: "starredBtn", gallery: "galleryBtn", export: "exportBtn", edit: "itemEditBtn", leave: "leaveRoomBtn", ai_summary: "aiSummaryBtn", project_history: "projectHistoryBtn" };
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
  // 모바일 스와이프 (좌우 50px 이상)
  (function() {
    const stage = els.lightbox?.querySelector(".lb-stage");
    if (!stage) return;
    let sx = 0, sy = 0, tracking = false;
    stage.addEventListener("touchstart", (e) => {
      if (e.touches.length !== 1) { tracking = false; return; }
      sx = e.touches[0].clientX; sy = e.touches[0].clientY;
      tracking = true;
    }, { passive: true });
    stage.addEventListener("touchend", (e) => {
      if (!tracking) return;
      tracking = false;
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

  // 모든 dialog/modal 우클릭 시 즉시 강제 닫기 (긴급 탈출)
  document.addEventListener("contextmenu", (e) => {
    const dlg = e.target.closest("dialog, .modal");
    if (dlg && (dlg.open || dlg.classList?.contains("open"))) {
      e.preventDefault();
      try { dlg.close(); } catch(_){}
      dlg.classList?.remove("open");
      dlg.removeAttribute("open");
      dlg.style.display = "none";
    }
  });
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

  async function openAiSummary(roomId, roomName) {
    if (!roomId) return;
    _aiSummaryActiveRoom = roomId;
    _aiSummaryActiveParams = { limit: 80, force: false };  // 기본
    if (els.aiSummaryRoomName) els.aiSummaryRoomName.textContent = `📍 ${roomName || ""}`;
    if (els.aiSummaryBody) els.aiSummaryBody.textContent = "버튼을 눌러 요약을 생성하세요.";
    if (els.aiSummaryMeta) els.aiSummaryMeta.textContent = "";
    try { els.aiSummaryDialog.showModal(); } catch (_) {}
    // 자동으로 최근 80개 1회 시도
    await runAiSummary(_aiSummaryActiveParams);
  }

  async function runAiSummary(params) {
    if (!_aiSummaryActiveRoom) return;
    if (!els.aiSummaryBody) return;
    els.aiSummaryBody.textContent = "🧠 Claude 가 요약하는 중… (수 초 소요)";
    els.aiSummaryMeta.textContent = "";
    _aiSummaryActiveParams = params;
    try {
      const res = await fetch(`${BASE}/api/rooms/${_aiSummaryActiveRoom}/summarize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      }).then(r => r.json());
      if (res.error) {
        els.aiSummaryBody.textContent = `❌ ${res.error}`;
        return;
      }
      els.aiSummaryBody.textContent = res.summary || "(빈 응답)";
      let meta = `대상 메시지: ${res.message_count}개`;
      if (res.cached) {
        meta += ` · 💾 캐시 (생성: ${res.cached_at?.slice(0,16) || ""})`;
      } else {
        if (res.model) meta += ` · 모델: ${res.model}`;
        if (res.cost_usd) meta += ` · 비용: $${res.cost_usd.toFixed(4)}`;
      }
      els.aiSummaryMeta.textContent = meta;
    } catch (e) {
      els.aiSummaryBody.textContent = `❌ 네트워크 오류: ${e.message || e}`;
    }
  }

  // 범위 선택 버튼들 (limit / since)
  document.querySelectorAll(".ai-range-btn").forEach(b => {
    b.addEventListener("click", () => {
      const limit = b.dataset.limit ? parseInt(b.dataset.limit, 10) : null;
      const since = b.dataset.since;
      const params = { force: false };
      if (limit) {
        params.limit = limit;
      } else if (since) {
        const now = new Date();
        let target;
        if (since === "today") {
          target = now;
        } else if (since === "yesterday") {
          target = new Date(now.getTime() - 86400000);
        } else if (since === "week") {
          target = new Date(now.getTime() - 7 * 86400000);
        }
        if (target) {
          params.since = target.toISOString().slice(0, 10);
        }
      }
      runAiSummary(params);
    });
  });

  if (els.aiSummaryRegenBtn) {
    els.aiSummaryRegenBtn.addEventListener("click", () => {
      if (_aiSummaryActiveParams) {
        runAiSummary({ ..._aiSummaryActiveParams, force: true });
      }
    });
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
        alert("✨ 작성 도움\n\n다듬을 텍스트를 먼저 입력하세요.");
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
          alert("❌ 네트워크 오류");
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
    html += emojis.map(e => `<button type="button" class="es-chip" data-emoji="${e}" title="${escapeHtml(word)} → ${e}">${e}</button>`).join("");
    html += stickers.map(s => `<button type="button" class="es-sticker" data-file="${escapeHtml(s.file)}" title="스티커: ${escapeHtml(s.label)}"><img src="${BASE}/static/stickers/${encodeURIComponent(s.file)}" alt="${escapeHtml(s.label)}" loading="lazy"></button>`).join("");
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

  // 추천 스티커 클릭 — 트리거 단어를 입력창에서 지우고 스티커를 메시지로 전송
  function applyStickerSuggestion(file) {
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
    sendSticker(file);
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
        applyStickerSuggestion(st.dataset.file);
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
      p.hidden = false;
    } else {
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
  if (els.stickerPicker) {
    els.stickerPicker.addEventListener("click", (e) => {
      const btn = e.target.closest(".sp-item");
      if (!btn) return;
      e.preventDefault();
      e.stopPropagation();
      sendSticker(btn.dataset.file);
    });
  }
  // 바깥 클릭으로 닫기
  document.addEventListener("click", (e) => {
    if (!els.stickerPicker || els.stickerPicker.hidden) return;
    if (els.stickerPicker.contains(e.target)) return;
    if (e.target === els.stickerBtn) return;
    toggleStickerPicker(false);
  });
  // ESC 로 닫기
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && els.stickerPicker && !els.stickerPicker.hidden) {
      toggleStickerPicker(false);
    }
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
    }
    // 탭 전환 시 검색 입력 초기화 — 사용자 탭 검색어가 방 탭으로 넘어가지 않게 (대표 지시 2026-05-19)
    if (els.globalSearch) els.globalSearch.value = "";
    window._userListQuery = "";
    // placeholder 도 탭에 맞게 변경 (대표 UX 힌트)
    if (els.globalSearch) {
      els.globalSearch.placeholder = (tab === "users")
        ? "🔍 사용자 검색 (이름·직급·부서)"
        : "🔍 검색 (from:이름 in:방 has:file before:날짜)";
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
      if (els.userList) els.userList.hidden = false;
      // 툴바는 비어있지만 향후 확장용으로 유지 (현재 hidden 가능)
      if (els.userListToolbar) els.userListToolbar.hidden = true;
      // 직원 등록 버튼은 헤더(.head-actions)로 이동 — 권한 체크는 별도 시점에서 처리
      renderUserList();
    }
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

  function renderUserList() {
    if (!els.userList) return;
    if (!_usersCache.length) {
      els.userList.innerHTML = `<div class="empty-state" style="padding:32px;font-size:13px;">사용자가 없습니다.</div>`;
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
        els.userList.innerHTML = `<div class="empty-state" style="padding:32px;font-size:13px;">검색 결과 없음 — "${escapeHtml(q)}"</div>`;
        return;
      }
    }
    // 부서별 그룹핑
    const groups = {};
    filtered.forEach(u => {
      const key = u.department || "(미지정)";
      if (!groups[key]) groups[key] = [];
      groups[key].push(u);
    });
    // 내 부서를 항상 맨 위로 (대표 지시 2026-05-20) → 그다음 부서코드 순:
    //   본사(00·01~11·13·14) → 베트남(12-VNNN, 정렬키 VN12-NN) → (미지정)
    const myDept = (_usersCache.find(u => u.id === meId) || {}).department || "(미지정)";
    const deptKeys = Object.keys(groups).sort((a, b) => {
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
    let html = "";
    deptKeys.forEach(dept => {
      const color = _deptColor(dept);
      const deptLabel = dept === "(미지정)" ? dept : deptDisplayLabel(dept);
      // 부서 내부 정렬 — 팀장(0) → 파트장(1) → 그 외(2) → 동일 순위는 display_name 가나다순
      groups[dept].sort((a, b) => {
        // 본인은 자기 부서 안에서 항상 맨 위 (대표 지시 2026-05-20)
        if (a.id === meId) return -1;
        if (b.id === meId) return 1;
        const ra = _titleRank(a.title);
        const rb = _titleRank(b.title);
        if (ra !== rb) return ra - rb;
        return String(a.display_name || "").localeCompare(String(b.display_name || ""), "ko");
      });
      html += `<div class="user-dept-head" style="border-left:3px solid ${color};">${escapeHtml(deptLabel)} <span class="user-dept-count">${groups[dept].length}</span></div>`;
      html += groups[dept].map(u => {
        const isMe = u.id === meId;
        const inactive = !u.active;
        const statusInfo = (window._userStatusMap && window._userStatusMap[u.id]) || null;
        const dotColor = statusInfo ? _getStatusColor(statusInfo.status) : "#9ca3af";
        const statusLabel = statusInfo ? (statusInfo.label || statusInfo.status) : "";
        const customText = statusInfo && statusInfo.custom_text ? ` · ${escapeHtml(statusInfo.custom_text)}` : "";
        const title = u.title ? `<span class="user-title-chip">${escapeHtml(u.title)}</span>` : "";
        // 관리자 뱃지 — '관리자가 볼 때'만 표시. 최고관리자(소유자)는 별도 표기. (대표 지시 2026-05-20·21)
        const ceoBadge = (window._meRole === "ceo")
          ? (u.is_owner ? `<span class="user-ceo-badge user-owner-badge">👑 최고관리자</span>`
                        : (u.role === "ceo" ? `<span class="user-ceo-badge">관리자</span>` : ""))
          : "";
        const inactiveLabel = inactive ? `<span class="user-inactive">비활성</span>` : "";
        return `
          <div class="user-card ${inactive ? 'user-inactive-row' : ''}" data-uid="${u.id}" ${inactive ? 'data-inactive="1"' : ''}>
            <div class="user-card-avatar" style="background:${u.avatar_color || '#3b82f6'}">${_avatarBody(u)}<span class="status-dot" style="background:${dotColor};"></span></div>
            <div class="user-card-info">
              <div class="user-card-name">${escapeHtml(u.display_name)}${isMe ? ' <span class="rs-me">(나)</span>' : ''} ${ceoBadge} ${inactiveLabel}</div>
              <div class="user-card-meta">${title}<span class="user-status-text" style="color:${dotColor};">${escapeHtml(statusLabel)}${customText}</span></div>
            </div>
            <button type="button" class="user-card-menu-btn" data-uid="${u.id}" title="정보 수정·메뉴">⋮</button>
          </div>`;
      }).join("");
    });
    els.userList.innerHTML = html;
    // 이벤트: 카드 클릭 → 1:1 채팅 / ⋮ 메뉴 클릭 → 정보 수정
    els.userList.querySelectorAll(".user-card").forEach(card => {
      card.addEventListener("click", async (e) => {
        if (e.target.closest(".user-card-menu-btn")) return;   // 메뉴 버튼은 별도
        const uid = parseInt(card.dataset.uid, 10);
        if (uid === meId) {
          // 본인 클릭 → 본인 정보 수정 다이얼로그
          openUserInfoDialog(uid);
          return;
        }
        if (card.dataset.inactive === "1") {
          alert("비활성 사용자와는 새 1:1 채팅을 시작할 수 없습니다.");
          return;
        }
        // 1:1 채팅 열기 (없으면 자동 생성)
        const res = await fetch(`${BASE}/api/rooms/direct/${uid}`, { method: "POST" }).then(r => r.json());
        if (res.error) { alert(res.error); return; }
        await refreshRooms();
        // 방 탭으로 전환하고 해당 방 열기
        setSidebarTab("rooms");
        const r = rooms.find(x => x.id === res.room_id);
        if (r) openRoom(r);
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
  }

  // ─── 사용자 카드 컨텍스트 메뉴 (우클릭/롱프레스) ───
  function closeUserContextMenu() {
    document.querySelectorAll(".user-context-menu").forEach(m => m.remove());
  }
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".user-context-menu")) closeUserContextMenu();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeUserContextMenu();
  });

  function showUserContextMenu(uid, clientX, clientY) {
    closeUserContextMenu();
    const u = _usersCache.find(x => x.id === uid);
    if (!u) return;
    const me = _usersCache.find(x => x.id === meId);
    const isCeo = me && me.role === "ceo";
    const isSelf = uid === meId;
    const statusInfo = (window._userStatusMap && window._userStatusMap[uid]) || null;
    const dotColor = statusInfo ? _getStatusColor(statusInfo.status) : "#9ca3af";
    const statusLabel = statusInfo ? (statusInfo.label || statusInfo.status) : "(미접속)";
    const customText = statusInfo && statusInfo.custom_text ? statusInfo.custom_text : "";

    const menu = document.createElement("div");
    menu.className = "msg-context-menu user-context-menu";
    menu.innerHTML = `
      <div class="ucm-card">
        <div class="ucm-avatar" style="background:${u.avatar_color || '#3b82f6'}" data-uid="${u.id}" title="${(isSelf || (window._meRole === 'ceo')) ? '클릭하여 사진 변경' : ''}">${_avatarBody(u)}<span class="ucm-status-dot" style="background:${dotColor};"></span>${(isSelf || (window._meRole === 'ceo')) ? '<span class="ucm-avatar-edit">📷</span>' : ''}</div>
        <div class="ucm-body">
          <div class="ucm-name">${escapeHtml(u.display_name || '')}${isSelf ? ' <span class="ucm-me">(나)</span>' : ''}${u.is_owner ? ' <span class="ucm-ceo">👑 최고관리자</span>' : ((u.role === 'ceo' && isSelf) ? ' <span class="ucm-ceo">👑 관리자</span>' : '')}${!u.active ? ' <span class="ucm-inactive">⚠ 비활성</span>' : ''}</div>
          <div class="ucm-row"><span class="ucm-label">사번</span><span class="ucm-value">${escapeHtml(u.employee_no || '(미설정)')}</span></div>
          <div class="ucm-row"><span class="ucm-label">직급</span><span class="ucm-value">${escapeHtml(u.title || '(미설정)')}</span></div>
          <div class="ucm-row"><span class="ucm-label">부서</span><span class="ucm-value">${escapeHtml(u.department ? deptDisplayLabel(u.department) : '(미설정)')}</span></div>
          <div class="ucm-row"><span class="ucm-label">이메일</span><span class="ucm-value">${u.email ? `<a href="mailto:${escapeHtml(u.email)}" class="ucm-link" title="이메일 보내기">${escapeHtml(u.email)}</a>` : '<span class="ucm-unset">(미설정)</span>'}</span></div>
          <div class="ucm-row"><span class="ucm-label">전화</span><span class="ucm-value">${u.phone ? `<a href="tel:${escapeHtml((u.phone||'').replace(/[^0-9+]/g,''))}" class="ucm-link" title="전화 걸기">${escapeHtml(u.phone)}</a>` : '<span class="ucm-unset">(미설정)</span>'}</span></div>
          <div class="ucm-row"><span class="ucm-label">상태</span><span class="ucm-value" style="color:${dotColor};font-weight:600;">${escapeHtml(statusLabel)}</span></div>
          ${customText ? `<div class="ucm-row"><span class="ucm-label">메모</span><span class="ucm-value">${escapeHtml(customText)}</span></div>` : ''}
          <div class="ucm-row"><span class="ucm-label">ID</span><span class="ucm-value ucm-mono">${escapeHtml(u.username || '')}</span></div>
        </div>
      </div>
      <div class="mcm-divider"></div>
      ${!isSelf && u.active ? `<button type="button" class="mcm-item" data-act="dm"><span class="mcm-icon">💬</span><span>1:1 채팅</span></button>` : ''}
      ${!isSelf && u.active && activeRoom && activeRoom.type !== 'direct' && activeRoom.type !== 'self' ? `<button type="button" class="mcm-item" data-act="whisper"><span class="mcm-icon">🤫</span><span>귓속말 — 둘만 보이는 메시지</span></button>` : ''}
      ${u.email ? `<button type="button" class="mcm-item" data-act="email"><span class="mcm-icon">📧</span><span>이메일 보내기</span></button>` : ''}
      ${u.phone ? `<button type="button" class="mcm-item" data-act="phone"><span class="mcm-icon">📞</span><span>전화 걸기</span></button>` : ''}
      ${u.phone ? `<button type="button" class="mcm-item" data-act="copy_phone"><span class="mcm-icon">📋</span><span>전화번호 복사</span></button>` : ''}
      ${isSelf || isCeo ? `<button type="button" class="mcm-item" data-act="edit"><span class="mcm-icon">✏</span><span>정보 수정</span></button>` : ''}
      ${(isSelf || isCeo) && u.avatar_url ? `<button type="button" class="mcm-item" data-act="remove_photo"><span class="mcm-icon">🗑</span><span>프로필 사진 제거 (기본 아이콘으로)</span></button>` : ''}
      ${isSelf ? `<button type="button" class="mcm-item" data-act="change_password"><span class="mcm-icon">🔐</span><span>비밀번호 변경</span></button>` : ''}
      ${!isSelf ? `<button type="button" class="mcm-item" data-act="mention"><span class="mcm-icon">@</span><span>현재 방에 @멘션 삽입</span></button>` : ''}
    `;
    document.body.appendChild(menu);
    const w = menu.offsetWidth, h = menu.offsetHeight;
    let x = clientX, y = clientY;
    if (x + w > window.innerWidth - 8) x = window.innerWidth - w - 8;
    if (y + h > window.innerHeight - 8) y = window.innerHeight - h - 8;
    if (x < 8) x = 8; if (y < 8) y = 8;
    menu.style.left = x + "px"; menu.style.top = y + "px";
    // 아바타 클릭 → 사진 업로드 (본인 또는 관리자만, ucm-avatar-edit 버튼 visible 인 경우)
    const avatarEl = menu.querySelector(".ucm-avatar");
    if (avatarEl && (isSelf || (window._meRole === "ceo"))) {
      avatarEl.style.cursor = "pointer";
      avatarEl.addEventListener("click", (ev) => {
        ev.stopPropagation();
        _triggerAvatarUpload(uid);
      });
    }
    menu.querySelectorAll(".mcm-item").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const act = btn.dataset.act;
        closeUserContextMenu();
        if (act === "dm") {
          const res = await fetch(`${BASE}/api/rooms/direct/${uid}`, { method: "POST" }).then(r => r.json());
          if (res.error) { alert(res.error); return; }
          await refreshRooms();
          setSidebarTab("rooms");
          const r = rooms.find(x => x.id === res.room_id);
          if (r) openRoom(r);
        } else if (act === "edit") {
          openUserInfoDialog(uid);
        } else if (act === "change_password") {
          openChangePasswordDialog();
        } else if (act === "remove_photo") {
          if (!confirm("프로필 사진을 제거하고 기본 아이콘으로 되돌릴까요?")) return;
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
            t.style.cssText = "position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#10B981;color:#fff;padding:10px 16px;border-radius:8px;font-size:13px;z-index:99999;box-shadow:0 4px 12px rgba(0,0,0,0.2);";
            document.body.appendChild(t);
            setTimeout(() => t.remove(), 1500);
          } catch (e) { alert("복사 실패: " + (e.message || e)); }
        } else if (act === "mention") {
          if (!activeRoom) {
            alert("먼저 대화방을 선택하세요.");
            return;
          }
          const tag = "@" + (u.username || u.display_name);
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
  }

  function _getStatusColor(status) {
    const map = {
      online: "#10B981", away: "#9CA3AF", busy: "#EF4444",
      meeting: "#F59E0B", external: "#8B5CF6", dnd: "#DC2626", offline: "#6B7280",
    };
    return map[status] || "#9ca3af";
  }

  // 사용자 정보 수정 다이얼로그
  function openUserInfoDialog(uid) {
    const u = _usersCache.find(x => x.id === uid);
    if (!u) return;
    const me = _usersCache.find(x => x.id === meId);
    const isCeo = me && me.role === "ceo";
    const isSelf = uid === meId;
    if (!isCeo && !isSelf) {
      // 다른 사람 정보 — 읽기 전용 미리보기. 권한(role) 은 노출 안 함.
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
          if (!phoneDigits) { alert("이 사용자의 전화번호가 없어 초기화할 수 없습니다. 먼저 전화번호를 입력·저장하세요."); return; }
          if (!confirm(`${u.display_name} 님의 비밀번호를 전화번호(${phoneDigits})로 초기화할까요?\n\n초기화 후 사용자는 첫 로그인 시 새 비밀번호를 설정합니다.`)) return;
          try {
            const res = await fetch(`${BASE}/api/users/${uid}/reset_password`, { method: "POST" }).then(r => r.json());
            if (res.error) { alert("❌ " + res.error); return; }
            alert(`✅ 비밀번호가 초기화되었습니다.\n임시 비밀번호(전화번호): ${res.temp_password}\n\n사용자에게 전달하세요. 첫 로그인 시 새 비밀번호를 설정하게 됩니다.`);
          } catch (e) { alert("❌ 네트워크 오류: " + (e.message || e)); }
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
            if (typed !== null) alert("이름이 일치하지 않습니다. 삭제 취소.");
            return;
          }
          delBtn.disabled = true;
          delBtn.textContent = "삭제 중…";
          try {
            const res = await fetch(`${BASE}/api/users/${uid}`, { method: "DELETE" }).then(r => r.json());
            if (res.error) { alert("❌ " + res.error); return; }
            alert(`✅ ${res.display_name} 님의 계정이 삭제되었습니다.`);
            try { els.userInfoDialog.close(); } catch (_) {}
            await refreshUserList();
          } catch (e) {
            alert("❌ 네트워크 오류: " + (e.message || e));
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
            if (!confirm("⚠ 본인의 관리자 권한을 해제하시겠습니까?\n\n해제하면 직원 등록·다른 사용자 정보 수정 등 관리 기능이 차단됩니다. 진행할까요?")) {
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
      setSidebarTab(b.dataset.tab);
    });
  }

  // ─── ➕ 직원 등록 (관리자 전용) ───
  if (els.newUserBtn && els.newUserDialog) {
    // 배선 즉시 권한대로 숨김/노출 (HTML 기본 hidden + 부팅 role 기준) — 일반 직원에겐 안 보이게
    els.newUserBtn.hidden = (window._meRole !== "ceo");
    els.newUserBtn.addEventListener("click", () => {
      // 관리자 전용 가드 — 버튼이 어떤 이유로 보이더라도 일반 직원은 진입 차단 (서버도 403)
      if (window._meRole !== "ceo") { alert("관리자 전용 기능입니다."); return; }
      // 폼 초기화
      ["nuDisplayName","nuEmail","nuPhone","nuTitle"].forEach(k => { if (els[k]) els[k].value = ""; });
      const _empNo = document.getElementById("nuEmployeeNo"); if (_empNo) _empNo.value = "";
      if (els.nuDept) els.nuDept.value = "";
      if (els.nuRoleCeo) els.nuRoleCeo.checked = false;
      if (els.nuResult) els.nuResult.textContent = "";
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
          alert("엑셀 파일을 선택하세요.");
          return;
        }
        const file = fInput.files[0];
        if (!file.name.toLowerCase().endsWith(".xlsx") && !file.name.toLowerCase().endsWith(".xlsm")) {
          alert("엑셀(.xlsx) 파일만 업로드 가능합니다.");
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
              <div style="font-weight:700;color:#065F46;font-size:14px;">
                ✅ 일괄 등록 완료 — 성공 ${res.created_count}건 · 스킵 ${res.skipped_count}건 · 오류 ${res.error_count}건
              </div>
            </div>`;
          if (res.created && res.created.length) {
            html += `<details style="margin-bottom:6px;"><summary style="cursor:pointer;font-weight:600;color:#065F46;font-size:12.5px;">✅ 신규 등록 ${res.created.length}건 (펼쳐서 확인)</summary>`;
            html += `<div style="max-height:200px;overflow-y:auto;font-size:11.5px;padding:6px;border:1px solid #D1FAE5;border-radius:6px;margin-top:4px;">`;
            res.created.forEach(c => {
              html += `<div style="padding:2px 0;"><b>${escapeHtml(c.name)}</b> · ${escapeHtml(c.email)} · 초기PW: <code>${escapeHtml(c.phone_initial_pw)}</code></div>`;
            });
            html += `</div></details>`;
          }
          if (res.skipped && res.skipped.length) {
            html += `<details style="margin-bottom:6px;"><summary style="cursor:pointer;font-weight:600;color:#92400E;font-size:12.5px;">⏭ 스킵 ${res.skipped.length}건 (이미 등록·예시 행)</summary>`;
            html += `<div style="max-height:160px;overflow-y:auto;font-size:11.5px;padding:6px;border:1px solid #FDE68A;border-radius:6px;margin-top:4px;">`;
            res.skipped.forEach(s => {
              html += `<div style="padding:2px 0;">행 ${s.row}: <b>${escapeHtml(s.name)}</b> — ${escapeHtml(s.reason)}</div>`;
            });
            html += `</div></details>`;
          }
          if (res.errors && res.errors.length) {
            html += `<details open style="margin-bottom:6px;"><summary style="cursor:pointer;font-weight:600;color:#991B1B;font-size:12.5px;">❌ 오류 ${res.errors.length}건 (수정 후 재업로드 필요)</summary>`;
            html += `<div style="max-height:160px;overflow-y:auto;font-size:11.5px;padding:6px;border:1px solid #FCA5A5;border-radius:6px;margin-top:4px;">`;
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
        const display_name = els.nuDisplayName?.value?.trim();
        const email = els.nuEmail?.value?.trim()?.toLowerCase();
        const phone = els.nuPhone?.value?.trim();
        const title = els.nuTitle?.value?.trim();
        const department = els.nuDept?.value;
        const employee_no = document.getElementById("nuEmployeeNo")?.value?.trim() || "";
        const role = els.nuRoleCeo?.checked ? "ceo" : "staff";
        if (!display_name) { alert("이름을 입력하세요."); return; }
        if (!email || !email.includes("@")) { alert("회사 이메일을 입력하세요 (@ 포함)."); return; }
        if (!phone) { alert("휴대폰 번호를 입력하세요."); return; }
        const digits = phone.replace(/\D/g, "");
        if (digits.length < 9) { alert("전화번호 자릿수가 부족합니다 (숫자 9자리 이상)."); return; }
        els.nuSaveBtn.disabled = true;
        const prevText = els.nuSaveBtn.textContent;
        els.nuSaveBtn.textContent = "등록 중…";
        try {
          const res = await fetch(`${BASE}/api/users`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ display_name, email, phone, title, department, employee_no, role }),
          }).then(r => r.json());
          if (res.error) {
            if (els.nuResult) els.nuResult.innerHTML = `<span style="color:#dc2626;">❌ ${escapeHtml(res.error)}</span>`;
            return;
          }
          if (els.nuResult) {
            els.nuResult.innerHTML = `
              <div style="background:#ECFDF5;border:1px solid #10B981;border-radius:8px;padding:10px;color:#065F46;">
                ✅ 등록 완료 — <b>${escapeHtml(display_name)}</b><br>
                <div style="margin-top:6px;font-size:11.5px;line-height:1.6;">
                  • <b>로그인 ID</b>: <code>${escapeHtml(email)}</code><br>
                  • <b>초기 비밀번호</b>: <code>${escapeHtml(digits)}</code> (휴대폰 번호 숫자)<br>
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

  // ─── 🔐 비밀번호 보기/숨기기 토글 (👁) — 전역 1회 wire ───
  document.querySelectorAll(".pw-toggle").forEach((btn) => {
    if (btn._pwWired) return;
    btn._pwWired = true;
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-pw-toggle-for");
      const inp = document.getElementById(id);
      if (!inp) return;
      const shown = inp.type === "text";
      inp.type = shown ? "password" : "text";
      btn.textContent = shown ? "👁" : "🙈";
      btn.classList.toggle("shown", !shown);
      btn.setAttribute("aria-label", shown ? "비밀번호 보기" : "비밀번호 숨기기");
    });
  });

  // ─── 🔐 비밀번호 변경 다이얼로그 (수동 호출용) ───
  function openChangePasswordDialog() {
    if (!els.changePwDialog) return;
    // 폼 초기화
    if (els.cpwCurrent) els.cpwCurrent.value = "";
    if (els.cpwNew) els.cpwNew.value = "";
    if (els.cpwNew2) els.cpwNew2.value = "";
    // 👁 토글이 text 로 바꿔뒀을 수도 — 닫고 다시 열 때 안전하게 password 로 환원
    ["cpwCurrent", "cpwNew", "cpwNew2"].forEach((id) => {
      const inp = document.getElementById(id);
      if (inp && inp.type === "text") inp.type = "password";
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
        alert("✅ 비밀번호가 변경되었습니다. 메신저를 사용하세요.");
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
          <div style="text-align:center;color:var(--text-soft);padding:36px 16px;font-size:13.5px;">
            아직 생성된 이력이 없습니다.<br>
            대화가 어느 정도 쌓이면 매일 자동으로 요약·정리되며,<br>
            <b>"✨ 지금 갱신"</b> 버튼으로 즉시 만들 수도 있습니다.
          </div>`;
        return;
      }
      els.phList.innerHTML = list.map(h => {
        const periodStart = h.period_start ? h.period_start.slice(5, 16).replace("T", " ") : "";
        const periodEnd = h.period_end ? h.period_end.slice(5, 16).replace("T", " ") : "";
        const author = h.created_mode === "auto" ? "🤖 자동" : `✋ ${h.created_by_name || "수동"}`;
        const cost = (h.cost_usd && h.cost_usd > 0) ? `<span style="color:#6B7280;">· $${h.cost_usd.toFixed(4)}</span>` : "";
        const synced = h.synced_to_hw ? `<span style="color:#10b981;font-weight:600;" title="HAIST WORKS 전송됨 ${h.synced_at||''}">📤 HW 전송됨</span>` : "";
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
              <div class="ph-card-meta">${author} · 메시지 ${h.message_count}개${h.attachment_count > 0 ? ' · 첨부 ' + h.attachment_count : ''} ${cost} ${synced}</div>
            </div>
            <div class="ph-card-body">${escapeHtml(h.summary_text || '').replace(/\n/g, '<br>')}</div>
            ${atts ? `<div class="ph-card-atts"><div class="ph-card-atts-title">첨부 ${h.attachment_count}개</div>${atts}</div>` : ''}
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
        alert("❌ 네트워크 오류");
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
    // 임원 (1) — 대표이사 전용 (코드 00 → 맨 위 정렬)
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
    if (name === "설계팀(자동화)") return "04.1";
    if (name === "설계팀(검사기)") return "04.2";
    return DEPT_CODES[name] || "99";
  }
  function deptDisplayLabel(name) {
    if (!name) return "";
    // 베트남법인 — DB 값에 이미 코드 포함 → 그대로 표시
    // 새 포맷: '12-VNNN 부서명' / legacy: 'VN12-NN 부서명' (둘 다 그대로 표시)
    if (/^12-VN\d{2}\s+/.test(name)) return name;
    if (/^VN12-\d{2}\s+/.test(name)) return name;
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
    away:     { color: "#9CA3AF", label: "🌙 자리비움",   desc: "잠시 자리에 없음" },
    busy:     { color: "#EF4444", label: "🔴 바쁨",       desc: "응답 어려움" },
    meeting:  { color: "#F59E0B", label: "🤝 회의 중",    desc: "회의·통화" },
    external: { color: "#8B5CF6", label: "🚗 외근",       desc: "사무실 외" },
    overseas: { color: "#3B82F6", label: "✈️ 해외출장",   desc: "해외 출장 중" },
    domestic: { color: "#06B6D4", label: "🚆 국내출장",   desc: "국내 출장 중" },
    vacation: { color: "#EC4899", label: "🌴 휴가",       desc: "휴가 중" },
    offline:  { color: "#6B7280", label: "⚫ 오프라인",   desc: "로그아웃 — 알림 안 옴" },
  };
  let _userStatusMap = {};   // uid -> status info
  window._userStatusMap = _userStatusMap;
  let _myCurrentStatus = "online";

  async function refreshAllUserStatuses() {
    try {
      const list = await fetch(`${BASE}/api/users/statuses`).then(r => r.json());
      list.forEach(u => { _userStatusMap[u.user_id] = u; });
      window._userStatusMap = _userStatusMap;
      // 내 상태 표시 갱신
      const me = _userStatusMap[meId];
      if (me) {
        _myCurrentStatus = me.status;
        _renderMyStatusBadge(me);
        _applyDndIfNeeded(me.status);
      }
      // 메시지 발신자 아바타 점 갱신
      els.messages?.querySelectorAll(".msg .avatar").forEach(av => {
        const li = av.closest(".msg");
        if (!li) return;
        const uid = parseInt(li.dataset.uid, 10);  // 옵션 — 없으면 skip
        // (uid 미지정이라 발신자 색점은 후속 작업으로)
      });
    } catch (e) { /* noop */ }
  }

  function _renderMyStatusBadge(s) {
    if (els.myStatusDot) {
      els.myStatusDot.className = "status-dot status-" + s.status;
      els.myStatusDot.style.background = STATUS_INFO[s.status]?.color || "#6B7280";
    }
    if (els.myStatusText) {
      const customSuffix = s.custom_text ? ` · ${s.custom_text}` : "";
      els.myStatusText.textContent = (STATUS_INFO[s.status]?.label || s.label || s.status) + customSuffix;
    }
  }

  function _applyDndIfNeeded(status) {
    // DND 시 알림 시스템 강제 차단 — notifySettings 와 별개로 작동
    window.KNK_DND_ACTIVE = (status === "dnd");
  }

  function openStatusDialog() {
    if (!els.statusDialog || !els.statusOptionsArea) return;
    // 상태 옵션 카드 렌더 — 'mobile'·'offline' 은 자동 판정 상태라 수동 선택 카드에서 제외
    // 컴팩트 1줄 카드(아이콘+라벨) — 설명은 hover 툴팁으로. 2열 그리드라 한 화면에 다 보임. (대표 지시 2026-05-21)
    els.statusOptionsArea.innerHTML = Object.entries(STATUS_INFO).filter(([k]) => k !== "mobile" && k !== "offline").map(([k, v]) => `
      <button type="button" class="status-option-card" data-status="${k}" title="${escapeHtml(v.desc)}" style="display:flex;align-items:center;gap:6px;text-align:left;padding:8px 10px;border:2px solid ${k === _myCurrentStatus ? v.color : '#E5E7EB'};background:${k === _myCurrentStatus ? '#F9FAFB' : '#fff'};border-radius:8px;cursor:pointer;min-width:0;">
        <span style="font-weight:600;font-size:calc(13px + var(--fs-add-ui));color:#1F2937;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${v.label}</span>
      </button>
    `).join("");
    // 저장 로직 헬퍼 (대표 지시 2026-05-19) — 더블클릭·저장 버튼 양쪽에서 호출
    async function _saveStatus(statusKey, opts = {}) {
      const body = {
        status: statusKey,
        custom_text: els.statusCustomText?.value?.trim() || null,
        until_at: els.statusUntilAt?.value ? (els.statusUntilAt.value + ":00.000Z") : null,
      };
      const res = await fetch(`${BASE}/api/me/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).then(r => r.json()).catch(() => ({ error: "네트워크 오류" }));
      if (res.error) { alert(res.error); return false; }
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
    let pickedStatus = _myCurrentStatus;
    els.statusOptionsArea.querySelectorAll(".status-option-card").forEach(b => {
      b.addEventListener("click", () => {
        pickedStatus = b.dataset.status;
        els.statusOptionsArea.querySelectorAll(".status-option-card").forEach(c => {
          const k = c.dataset.status;
          c.style.borderColor = (k === pickedStatus) ? STATUS_INFO[k].color : "#E5E7EB";
          c.style.background = (k === pickedStatus) ? "#F9FAFB" : "#fff";
        });
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
      // 터치 디바이스용 — title 에 안내 추가
      b.setAttribute("title", `더블클릭(또는 더블탭): 즉시 적용`);
    });
    // 현재 사용자정의 문구·until 채우기
    const cur = _userStatusMap[meId] || {};
    if (els.statusCustomText) els.statusCustomText.value = cur.custom_text || "";
    if (els.statusUntilAt) els.statusUntilAt.value = cur.until_at ? cur.until_at.slice(0, 16) : "";
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
        if (!title || !start || !end) { alert("제목·시작·종료를 모두 입력하세요."); return; }
        const startISO = start + ":00.000Z";
        const endISO = end + ":00.000Z";
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
        els.calEventList.innerHTML = `<div style="font-size:12px;color:var(--text-soft);padding:8px;text-align:center;">예약된 일정 없음</div>`;
        return;
      }
      els.calEventList.innerHTML = list.map(e => {
        const startShort = e.start_at?.slice(5, 16).replace("T", " ");
        const endShort = e.end_at?.slice(5, 16).replace("T", " ");
        const stateIcon = e.applied === 2 ? "✅" : e.applied === 1 ? "🔄" : "⏰";
        const kindIcon = e.kind === "external" ? "🚗" : e.kind === "busy" ? "🔴" : "🤝";
        return `
          <div class="cal-event-row" style="display:flex;align-items:center;gap:8px;padding:6px 8px;border-bottom:1px solid #F3F4F6;font-size:12px;">
            <span>${stateIcon}</span><span>${kindIcon}</span>
            <span style="flex:1;font-weight:600;">${escapeHtml(e.title)}</span>
            <span style="color:var(--text-soft);">${startShort} ~ ${endShort}</span>
            <button type="button" class="rs-act-btn rs-danger" data-cal-del="${e.id}" style="padding:2px 6px;">🗑</button>
          </div>
        `;
      }).join("");
      els.calEventList.querySelectorAll("[data-cal-del]").forEach(b => {
        b.addEventListener("click", async () => {
          if (!confirm("일정을 삭제할까요?")) return;
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
    n = parseInt(n, 10); if (isNaN(n) || n < 0 || n > 4) n = 0;
    document.body.classList.remove("fs-1", "fs-2", "fs-3", "fs-4");
    if (n >= 1 && n <= 4) document.body.classList.add("fs-" + n);
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
  // 상태 다이얼로그 안의 🔐 비밀번호 변경 버튼
  const _statusCpwBtn = document.getElementById("statusChangePwBtn");
  if (_statusCpwBtn) {
    _statusCpwBtn.addEventListener("click", () => {
      try { els.statusDialog.close(); } catch (_) {}
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
      };
      window._userStatusMap = _userStatusMap;
      if (e.user_id === meId) {
        _myCurrentStatus = e.status;
        _renderMyStatusBadge(_userStatusMap[meId]);
        _applyDndIfNeeded(e.status);
      }
      // 사이드바 사용자 목록 색점 즉시 갱신 (대표 지시 2026-05-19)
      try { if (typeof renderUserList === "function") renderUserList(); } catch(err) {}
    });
  }
  setTimeout(_wireStatusSocket, 500);
  // 최초 로드 + 1분 주기 갱신 (실시간 broadcast 를 놓쳤을 때 안전망). (2026-05-20: 5분→1분)
  setTimeout(refreshAllUserStatuses, 1500);
  setInterval(refreshAllUserStatuses, 60 * 1000);

  // 스레드 패널에 🧠 요약 버튼 동적 추가
  // (openThreadPanel 에서 호출됨 — 별도 함수)
  window._addThreadSummarizeBtn = function(parentId) {
    const head = document.querySelector(".thread-panel-head");
    if (!head || head.querySelector(".thread-summarize-btn")) return;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "thread-summarize-btn";
    btn.title = "🧠 스레드 AI 요약";
    btn.textContent = "🧠";
    btn.style.cssText = "background:transparent;border:0;cursor:pointer;font-size:16px;padding:4px 8px;border-radius:6px;margin-right:6px;";
    btn.addEventListener("click", async () => {
      const body = document.getElementById("threadBody");
      if (!body) return;
      // 임시 결과 영역
      let box = document.getElementById("threadAiSumBox");
      if (!box) {
        box = document.createElement("div");
        box.id = "threadAiSumBox";
        box.style.cssText = "background:#FEF3C7;border:1px solid #F59E0B;border-radius:8px;padding:10px;margin-bottom:10px;font-size:13px;line-height:1.7;white-space:pre-wrap;color:#92400E;";
        body.insertBefore(box, body.firstChild);
      }
      box.textContent = "🧠 Claude 가 스레드를 요약하는 중…";
      try {
        const res = await fetch(`${BASE}/api/messages/${parentId}/summarize_thread`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        }).then(r => r.json());
        if (res.error) { box.textContent = `❌ ${res.error}`; return; }
        box.innerHTML = `<div style="font-weight:700;margin-bottom:4px;">🧠 AI 요약 (${res.message_count}개 메시지)</div>` +
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

  // 🔄 강제 새로고침 버튼 — SW unregister + 모든 cache 삭제 + 강제 reload
  const _hardReloadBtn = document.getElementById("hardReloadBtn");
  if (_hardReloadBtn) {
    _hardReloadBtn.addEventListener("click", async () => {
      if (!confirm("🔄 강제 새로고침\n\n캐시를 모두 비우고 최신 버전을 받습니다. 진행할까요?")) return;
      try {
        // 1) Service Worker unregister
        if ("serviceWorker" in navigator) {
          const regs = await navigator.serviceWorker.getRegistrations();
          await Promise.all(regs.map(r => r.unregister()));
        }
        // 2) 모든 Cache 삭제
        if ("caches" in window) {
          const keys = await caches.keys();
          await Promise.all(keys.map(k => caches.delete(k)));
        }
      } catch (e) { console.log("cache clear 실패:", e); }
      // 3) 강제 reload (캐시 무시)
      location.reload(true);
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
    if ($('nsTitleBlink')) $('nsTitleBlink').checked = !!s.titleBlink;
    if ($('nsInlineToast')) $('nsInlineToast').checked = !!s.inlineToast;
    if ($('nsSidebarBlink')) $('nsSidebarBlink').checked = !!s.sidebarBlink;
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
          lines.push(`✅ 푸시 구독: 등록됨<br><span style="color:#9CA3AF;font-size:11px;">${sub.endpoint.slice(0, 70)}...</span>`);
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
            lines.push(`<span style="color:#9CA3AF;font-size:11px;">  · #${s.id} ${s.endpoint}<br>    ua: ${s.user_agent} (${s.created})</span>`);
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
      _notifyDlg.showModal();
      await notify.ensurePermission();
      refreshPushDiagnostic();
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
                  <span id="nsCopyStatus" style="font-size:11px;color:var(--text-soft);align-self:center;"></span>
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
                <span style="font-size:11px;color:#9CA3AF;">${data.message}</span>`;
              _pushResult.style.color = '#F59E0B';
            } else if (data.sent > 0) {
              _pushResult.innerHTML = `✅ <strong>시뮬레이션 푸시 발송 성공 (${data.sent}개)</strong><br>
                <span style="font-size:11px;color:#9CA3AF;">잠시 후 휴대폰(백그라운드/화면 꺼짐)에 알림이 와야 정상입니다.</span>`;
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
    wireToggle('nsTitleBlink', 'titleBlink');
    wireToggle('nsInlineToast', 'inlineToast');
    wireToggle('nsSidebarBlink', 'sidebarBlink');
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
          marker.style.cssText = 'display:block;margin-top:10px;padding:10px 12px;background:#FEF2F2;border:2px solid #A5282C;border-radius:8px;font-size:13px;line-height:1.6;font-family:monospace;color:#1F2937;width:100%;clear:both;';
          $section.appendChild(marker);
        }
        const lines = [
          `<strong style="color:#A5282C;">🔊 ${stgVal} · ${vol}%</strong>`,
          `<span style="color:var(--text-soft);font-size:11px;">Web Audio: ${ctx ? ctx.state : '없음'} · select/settings ${match}</span>`,
        ];
        marker.innerHTML = lines.join('<br>');
        marker.style.cssText = 'display:block;margin-top:8px;padding:6px 10px;background:#FEF2F2;border:1px solid #FCA5A5;border-radius:6px;font-size:12px;line-height:1.5;color:#1F2937;width:100%;';
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
      const v = els.msgInput.value;
      const cursor = els.msgInput.selectionStart;
      const before = v.slice(0, cursor);
      const m = before.match(/@([\w가-힣]*)$/);
      if (!m) return;
      const start = before.length - m[0].length;
      const after = v.slice(cursor);
      els.msgInput.value = v.slice(0, start) + "@" + (u.username) + " " + after;
      const pos = start + 1 + u.username.length + 1;
      els.msgInput.setSelectionRange(pos, pos);
      close();
    }

    function show(list) {
      close();
      if (!list.length) return;
      matches = list.slice(0, 8);
      activeIdx = 0;
      popup = document.createElement("div");
      popup.className = "mention-popup";
      popup.innerHTML = matches.map((u, i) => {
        // 멘션 팝업에도 직급·부서 표기 (대표 지시 2026-05-20) — 없으면 아이디로 대체
        const title = u.title || "";
        const dept = u.department || "";
        const deptLabel = dept ? ((typeof deptDisplayLabel === "function") ? deptDisplayLabel(dept) : dept) : "";
        const meta = [title, deptLabel].filter(Boolean).join(" · ") || (u.username || "");
        return `
        <div class="mention-row ${i === 0 ? 'active' : ''}" data-idx="${i}">
          <div class="avatar" style="width:24px;height:24px;font-size:11px;background:${u.avatar_color}">${escapeHtml(initial(u.display_name))}</div>
          <span><b>${escapeHtml(u.display_name)}</b> <small style="color:#9ca3af">${escapeHtml(meta)}</small></span>
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
      const m = before.match(/@([\w가-힣]*)$/);
      if (!m) { close(); return; }
      const q = m[1].toLowerCase();
      await ensureUsers();
      // _deleted_user 플레이스홀더 + 비활성 사용자는 멘션 대상에서 제외 (대표 지시 2026-05-20)
      const list = users.filter(u =>
        u.id !== meId && u.username !== "_deleted_user" && u.active !== 0
      ).filter(u =>
        !q || u.username.toLowerCase().includes(q) || u.display_name.toLowerCase().includes(q)
      );
      show(list);
    });
    els.msgInput.addEventListener("keydown", (e) => {
      if (!popup) return;
      if (e.key === "ArrowDown") { e.preventDefault(); activeIdx = (activeIdx + 1) % matches.length; popup.querySelectorAll(".mention-row").forEach((r, i) => r.classList.toggle("active", i === activeIdx)); }
      else if (e.key === "ArrowUp") { e.preventDefault(); activeIdx = (activeIdx - 1 + matches.length) % matches.length; popup.querySelectorAll(".mention-row").forEach((r, i) => r.classList.toggle("active", i === activeIdx)); }
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
  window._isIOS = _isIOS;
  window._isStandalone = _isStandalone;

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

  // ---------- boot ----------
  (async () => {
    connectSocket();
    await ensureUsers();    // 멘션 렌더 위해 미리 로드
    await refreshRooms();
    setupMentionAutocomplete();
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
          document.title = (room.name || "대화") + " — KNK 메신저";
          openRoom(room);
        } else {
          history.replaceState(null, "", BASE + "/chat");
          setTimeout(() => openRoom(room), 300);
        }
      }
    }

    // 첫 진입 시 다이제스트 자동 노출 (오늘/지연 있으면)
    // solo 모드(분리창)에서는 다이제스트 띄우지 않음 — 그 방만 보러 띄운 창
    if (!SOLO_MODE && !sessionStorage.getItem("digest_seen_today") && !wantRoom) {
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
      const r = await setupWebPush();
      const iosTab = !SOLO_MODE && r && r.ios_need_install;       // iOS Safari 탭 (설치 안 함)
      const noti = (typeof Notification !== "undefined") ? Notification.permission : "denied";
      const iosNeedTap = !SOLO_MODE && _isIOS() && _isStandalone() &&
                         (!r || !r.ok) && noti !== "granted" && noti !== "denied";
      if (iosTab) {
        // 홈 화면 추가 안내 1회 (localStorage 중복 방지)
        try {
          if (!localStorage.getItem("knkmsg.iosInstallHintShown")) {
            localStorage.setItem("knkmsg.iosInstallHintShown", "1");
            _showIOSInstallHint();
          }
        } catch (e) {}
      } else if (iosNeedTap) {
        // 홈화면 PWA 인데 알림 권한 미요청 — 탭해서 켜기 배너 (iOS 제스처 필요)
        try { _showIOSEnablePushHint(); } catch (e) {}
      }
    }, 3500);
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
      "box-shadow:0 6px 24px rgba(0,0,0,0.3);font-size:13px;line-height:1.5;";
    bar.innerHTML =
      '<div style="display:flex;align-items:flex-start;gap:10px;">' +
        '<div style="font-size:22px;">📲</div>' +
        '<div style="flex:1;min-width:0;">' +
          '<div style="font-weight:700;margin-bottom:4px;">아이폰 알림 받으려면 홈 화면에 추가하세요</div>' +
          '<div style="color:#D1D5DB;font-size:12px;">Safari 하단 <b>공유 버튼(⬆)</b> → <b>"홈 화면에 추가"</b> → ' +
          '추가된 <b>KNK 아이콘</b>으로 실행하면 알림이 옵니다. (Safari 탭에서는 알림 불가)</div>' +
        '</div>' +
        '<button type="button" id="iosHintClose" style="background:transparent;border:0;color:#9CA3AF;' +
          'font-size:20px;cursor:pointer;padding:0 2px;line-height:1;">✕</button>' +
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
      "box-shadow:0 6px 24px rgba(0,0,0,0.3);font-size:13px;line-height:1.4;";
    bar.innerHTML =
      '<div style="display:flex;align-items:center;gap:10px;">' +
        '<div style="font-size:22px;">🔔</div>' +
        '<div style="flex:1;min-width:0;">' +
          '<div style="font-weight:700;margin-bottom:2px;">알림을 켜시겠어요?</div>' +
          '<div style="color:#D1D5DB;font-size:12px;">아이폰은 한 번 탭해야 알림이 켜집니다.</div>' +
        '</div>' +
        '<button type="button" id="iosEnablePushBtn" style="background:#A5282C;border:0;color:#fff;' +
          'font-weight:700;font-size:13px;padding:8px 14px;border-radius:8px;cursor:pointer;white-space:nowrap;">알림 켜기</button>' +
        '<button type="button" id="iosEnablePushClose" style="background:transparent;border:0;color:#9CA3AF;' +
          'font-size:20px;cursor:pointer;padding:0 2px;line-height:1;">✕</button>' +
      '</div>';
    document.body.appendChild(bar);
    const close = () => { try { bar.remove(); } catch (e) {} };
    const closeBtn = document.getElementById("iosEnablePushClose");
    if (closeBtn) closeBtn.addEventListener("click", close);
    const enableBtn = document.getElementById("iosEnablePushBtn");
    if (enableBtn) enableBtn.addEventListener("click", async () => {
      enableBtn.disabled = true;
      enableBtn.textContent = "켜는 중...";
      const r = await setupWebPush();   // ← 사용자 탭(제스처) 안 → iOS 권한 팝업 정상
      if (r && r.ok) {
        close();
        try { alert("✅ 알림이 켜졌습니다."); } catch (_) {}
      } else {
        enableBtn.disabled = false;
        enableBtn.textContent = "알림 켜기";
        try {
          alert("알림을 켜지 못했습니다.\n" + ((r && r.reason) || "") +
                "\n\n거부하셨다면 아이폰 '설정 > 알림 > KNK' 에서 허용해주세요.");
        } catch (_) {}
      }
    });
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
      "box-shadow:0 6px 24px rgba(0,0,0,0.3);font-size:13px;line-height:1.4;";
    bar.innerHTML =
      '<div style="display:flex;align-items:center;gap:10px;">' +
        '<div style="font-size:22px;">💻</div>' +
        '<div style="flex:1;min-width:0;">' +
          '<div style="font-weight:700;margin-bottom:2px;">' + titleTxt + '</div>' +
          '<div style="color:#D1D5DB;font-size:12px;">' + descTxt + '</div>' +
        '</div>' +
        '<button type="button" id="installAppBtn" style="background:#A5282C;border:0;color:#fff;' +
          'font-weight:700;font-size:13px;padding:8px 14px;border-radius:8px;cursor:pointer;white-space:nowrap;">설치</button>' +
        '<button type="button" id="installAppClose" style="background:transparent;border:0;color:#9CA3AF;' +
          'font-size:20px;cursor:pointer;padding:0 2px;line-height:1;">✕</button>' +
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
})();
