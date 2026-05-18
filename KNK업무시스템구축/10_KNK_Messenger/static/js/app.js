// KNK Messenger — client (Phase A+B+C+D)
(() => {
  const app = document.getElementById("app");
  const meId = parseInt(app.dataset.meId, 10);
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
  let activeFilter = "all";
  let activeTab = "item";
  let activeGalleryTab = "image";
  let activeReqTab = "open";
  let pendingReqMessage = null;     // 요청 등록 시 원본 메시지

  // ---------- helpers ----------
  const escapeHtml = (s) =>
    String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  const fmtTime = (iso) => {
    const d = new Date(iso);
    if (isNaN(d)) return "";
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    const opts = sameDay
      ? { hour: "2-digit", minute: "2-digit" }
      : { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" };
    return d.toLocaleString("ko-KR", opts);
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
    getSelfRoom: () => fetch(`${BASE}/api/me/self_room`).then(r => r.json()),
    setMemberRole: (rid, uid, role) => fetch(`${BASE}/api/rooms/${rid}/members/${uid}/role`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ role }) }).then(r => r.json()),
    transferHost: (rid, toUid) => fetch(`${BASE}/api/rooms/${rid}/transfer-host`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ to_user_id: toUid }) }).then(r => r.json()),
    inviteToRoom: (rid, uids) => fetch(`${BASE}/api/rooms/${rid}/invite`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ user_ids: uids }) }).then(r => r.json()),
    kickMember: (rid, uid) => fetch(`${BASE}/api/rooms/${rid}/members/${uid}/kick`, { method: "POST" }).then(r => r.json()),
    markRead: (rid) => fetch(`${BASE}/api/rooms/${rid}/read`, { method: "POST" }),
    upload: (rid, file, onProgress) => {
      // XHR 사용 — 진행률 이벤트 받으려면 fetch 대신 XHR (Stream API 미흡)
      return new Promise((resolve, reject) => {
        const fd = new FormData();
        fd.append("room_id", rid);
        fd.append("file", file);
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
    if (activeFilter === "my-tasks") {
      els.roomList.hidden = true;
      els.searchResults.hidden = true;
      els.myTasks.hidden = false;
      renderMyTasks();
      return;
    }
    els.myTasks.hidden = true;
    els.roomList.hidden = false;
    if (!list.length) {
      els.roomList.innerHTML = `<li class="empty-state" style="padding:32px;font-size:13px;">${rooms.length ? "이 필터에 해당하는 항목이 없습니다." : "대화가 없습니다.<br>＋ 버튼으로 새 아이템을 시작하세요."}</li>`;
      return;
    }
    els.roomList.innerHTML = list.map(r => {
      const isSelf = r.type === "self";
      const name = isSelf ? "📝 나에게 보내기" : (r.name || "(이름없음)");
      const color = isSelf ? "#f59e0b" : (r.avatar_color || (r.type === "item" ? "#7c3aed" : "#3b82f6"));
      const last = r.last_message ? escapeHtml(String(r.last_message).slice(0, 40)) : "<em style='color:#9ca3af'>대화 없음</em>";
      const time = r.last_at ? fmtTime(r.last_at) : "";
      const unread = r.unread > 0 ? `<span class="unread-badge">${r.unread > 99 ? "99+" : r.unread}</span>` : "";
      const active = activeRoom && activeRoom.id === r.id ? "active" : "";

      let chips = "";
      if (r.type === "item") {
        if (r.item_customer) chips += `<span class="customer-chip">${escapeHtml(r.item_customer)}</span>`;
        if (r.item_code) chips += `<span class="code-chip">${escapeHtml(r.item_code)}</span>`;
        if (r.item_status) chips += `<span class="status-pill status-${r.item_status}">${STATUS_LABEL[r.item_status] || r.item_status}</span>`;
      } else if (isSelf) {
        chips += `<span class="customer-chip" style="background:#fef3c7;color:#92400e">메모</span>`;
      }
      // 자동삭제 설정된 방은 ⏱ 아이콘 (WhatsApp 식)
      const retentionIcon = (r.retention_days && r.retention_days > 0)
        ? `<span class="room-retention-icon" title="자동삭제 ${r.retention_days===1?'24시간':r.retention_days+'일'} 후">⏱</span>`
        : "";

      const mutedIcon = notifySettings.isRoomMuted(r.id) ? `<span class="room-muted-icon" title="이 방 알림 음소거 중">🔕</span>` : "";
      const rowClass = [active, r.type === "item" ? "item-row" : "", isSelf ? "self-row" : ""].filter(Boolean).join(" ");
      return `
        <li data-room-id="${r.id}" class="${rowClass}">
          <div class="avatar" style="background:${color}">${escapeHtml(initial(name))}</div>
          <div class="room-info">
            <div class="room-name-line">
              ${chips}
              <div class="room-name">${escapeHtml(name)}${retentionIcon}${mutedIcon}</div>
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
        openRoom(rooms.find(r => r.id === rid));
      });
      // 더블클릭 → 그 방만 새 창(팝업)으로 분리 — 카카오톡PC 와 같은 멀티윈도우
      // 같은 방을 두 번 더블클릭하면 같은 창(name) 재사용해서 새 창 안 생김.
      li.addEventListener("dblclick", (e) => {
        e.preventDefault();
        // 솔로창 안에서는 동작 불필요 (사이드바 자체가 없지만 안전)
        if (SOLO_MODE) return;
        const rid = parseInt(li.dataset.roomId, 10);
        const url = BASE + `/chat?solo=1&room=${rid}`;
        const winName = `knk_room_${rid}`;
        // 카카오톡 분리창 비슷한 좁고 긴 비율 — 사용자가 모서리 드래그로 자유롭게 리사이즈 가능
        const features = "width=306,height=544,resizable=yes,scrollbars=yes,menubar=no,toolbar=no,location=no,status=no";
        const w = window.open(url, winName, features);
        if (w) {
          try { w.focus(); } catch(_) {}
        }
        // 더블클릭으로 텍스트 선택되는 것 방지
        try { window.getSelection().removeAllRanges(); } catch(_) {}
      });
    });
  }

  // ---------- render messages ----------
  function renderMessages(msgs) {
    if (!msgs.length) {
      els.messages.innerHTML = `<div class="empty-state">아직 메시지가 없습니다.<br>첫 메시지를 보내보세요.</div>`;
      return;
    }
    els.messages.innerHTML = msgs.map(msgHtml).join("");
    wireMessageActions();
    scrollToBottom({ force: true });  // 방 처음 열 때 / 메시지 전체 재로드 시 무조건 최하단
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
    if (m.kind === "image" && m.file_path) {
      cls += " image";
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

    // 읽음/안읽음 — 내 메시지에만 표시
    let readBadge = "";
    if (mine && roomReadStatus.members && roomReadStatus.members.length > 1) {
      const others = roomReadStatus.members.filter(mb => mb.user_id !== meId);
      const unreadBy = others.filter(mb => (mb.last_read_message_id || 0) < m.id);
      if (unreadBy.length > 0) {
        const unreadNames = unreadBy.map(mb => mb.display_name).join(", ");
        readBadge = `<span class="read-badge unread" title="${escapeHtml('안 읽음: ' + unreadNames)}">${unreadBy.length}</span>`;
      } else {
        readBadge = `<span class="read-badge all-read" title="모두 읽음">읽음</span>`;
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

    // 스레드 — 답글 카운트 배지 (Slack 식)
    let threadHtml = "";
    if (m.thread_reply_count && m.thread_reply_count > 0) {
      const cnt = m.thread_reply_count;
      const lastAt = m.thread_last_at ? fmtTime(m.thread_last_at) : "";
      threadHtml = `<button type="button" class="thread-reply-badge" data-act="open_thread" title="스레드 열기">
        💬 답글 ${cnt}${lastAt ? ` · 마지막 ${lastAt}` : ""}
      </button>`;
    }

    return `
      <li class="${cls}" data-msg-id="${m.id}" data-parent-msg-id="${m.parent_message_id || ""}">
        <div class="avatar" style="background:${m.avatar_color || "#3b82f6"}">${escapeHtml(initial(m.display_name))}</div>
        <div class="body">
          ${mine ? "" : `<div class="author">${escapeHtml(m.display_name)}</div>`}
          ${forwardCard}
          ${quoteCard}
          ${bubble}
          ${trHtml}
          ${rxHtml ? `<div class="reactions">${rxHtml}</div>` : ""}
          ${ackHtml}
          ${threadHtml}
          <div class="time">${readBadge}${fmtTime(m.created_at)}</div>
        </div>
        <div class="msg-action-bar">
          <button type="button" class="msg-action-btn" data-act="rx" data-emoji="👍" title="좋아요">👍</button>
          <button type="button" class="msg-action-btn" data-act="rx" data-emoji="✅" title="확인">✅</button>
          <button type="button" class="msg-action-btn" data-act="rx" data-emoji="❤" title="응원">❤</button>
          ${trBtn}
          <button type="button" class="${starBtnCls}" data-act="star" title="중요 결정으로 별표">${m.starred_by_me ? "★" : "☆"}</button>
          <button type="button" class="msg-action-btn" data-act="request" title="이 메시지를 요청으로 등록">📌 요청</button>
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

  // forceScroll=true: 본인 메시지 전송 직후 등 무조건 최하단으로.
  // 기본: 사용자가 위쪽 보고 있으면 위치 유지, 맨 아래 근처면 자동 스크롤.
  function appendMessage(m, forceScroll) {
    if (!els.messages.querySelector(".msg")) {
      els.messages.innerHTML = "";
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

  // 모바일에서 메시지 탭 시 액션바 토글 (카톡식). 데스크탑은 hover 로 자동.
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

  // ───────── 메시지 컨텍스트 메뉴 (카카오톡 PC 스타일) ─────────
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

    // DOM 생성
    const menu = document.createElement("div");
    menu.className = "msg-context-menu";
    menu.innerHTML = items.map(it => {
      if (it.divider) return `<div class="mcm-divider"></div>`;
      if (it.section) return `<div class="mcm-section-label">${escapeHtml(it.label)}</div>`;
      return `<button type="button" class="mcm-item" data-act="${it.act}" ${it.data ? `data-emoji="${escapeHtml(it.data)}"` : ""}>
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
  // 스레드(Threaded Reply) — Slack 식 사이드 패널
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
          <button type="submit" class="thread-send-btn" title="전송">➤</button>
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
    const parentHtml = `
      <div class="thread-parent">
        <div class="thread-msg-row">
          <div class="avatar" style="background:${p.avatar_color || '#3b82f6'}">${escapeHtml(initial(p.display_name))}</div>
          <div class="thread-msg-body">
            <div class="thread-msg-author">${escapeHtml(p.display_name)} <span class="thread-msg-time">${fmtTime(p.created_at)}</span></div>
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
          <div class="thread-msg-author">${escapeHtml(r.display_name)} <span class="thread-msg-time">${fmtTime(r.created_at)}</span></div>
          <div class="thread-msg-content">${escapeHtml(r.content || '').replace(/\n/g,'<br>')}</div>
        </div>
      </div>
    `).join("");
    body.innerHTML = parentHtml + repliesHtml;
    body.scrollTop = body.scrollHeight;
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
          <p class="dialog-hint">원본의 작성자·시각·방 정보가 그대로 보존됩니다 (Telegram 식).</p>
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
      const typeLabel = r.type === "item" ? "아이템" : r.type === "direct" ? "1:1" : r.type === "channel" ? "채널" : "그룹";
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


    // ─── 카카오톡식 우클릭/long-press 컨텍스트 메뉴 ───
    els.messages.querySelectorAll(".msg").forEach(li => {
      if (li._ctxWired) return;
      li._ctxWired = true;
      // 데스크톱: 우클릭
      li.addEventListener("contextmenu", (e) => {
        // 링크·이미지·input·textarea 위에서는 브라우저 기본 메뉴 우선 (복사 등)
        if (e.target.closest("a, input, textarea, .it-close, button.rx-chip")) return;
        e.preventDefault();
        showMessageContextMenu(li, e.clientX, e.clientY);
      });
      // 모바일: long-press (500ms)
      let touchTimer = null;
      let touchStartXY = null;
      li.addEventListener("touchstart", (e) => {
        if (e.target.closest("a, button, input, textarea")) return;
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
        const img = a.querySelector("img");
        els.lightboxImg.src = img.src;
        els.lightboxMeta.textContent = img.alt || "";
        els.lightbox.showModal();
      });
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

  async function renderItemMeta(room) {
    const isItem = room.type === "item";
    if (!isItem) {
      els.itemMeta.hidden = true;
      els.itemMeta.innerHTML = "";
      els.itemEditBtn.hidden = true;
    } else {
      const parts = [];
      if (room.item_customer) parts.push(`<span class="customer-chip">${escapeHtml(room.item_customer)}</span>`);
      if (room.item_code) parts.push(`<span class="code-chip">${escapeHtml(room.item_code)}</span>`);
      if (room.item_status) parts.push(`<span class="status-pill status-${room.item_status}">${STATUS_LABEL[room.item_status] || room.item_status}</span>`);
      if (room.item_due) parts.push(`<span class="meta-due">납기 ${fmtDate(room.item_due)}</span>`);
      els.itemMeta.innerHTML = parts.join("");
      els.itemMeta.hidden = parts.length === 0;
      els.itemEditBtn.hidden = false;
    }
    els.galleryBtn.hidden = false;
    els.requestsBtn.hidden = false;
    if (els.exportBtn) els.exportBtn.hidden = false;
    if (els.leaveRoomBtn) els.leaveRoomBtn.hidden = false;
    if (els.starredBtn) els.starredBtn.hidden = false;
    if (els.aiSummaryBtn) els.aiSummaryBtn.hidden = false;
    if (els.aiRewriteBtn) els.aiRewriteBtn.disabled = false;
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
    // 요약 카운트 옆에 미니 표시
    try {
      const s = await api.summary(room.id);
      const items = [];
      if (s.image_count) items.push(`<span class="sm-item">📷 ${s.image_count}</span>`);
      if (s.file_count) items.push(`<span class="sm-item">📎 ${s.file_count}</span>`);
      if (s.open_requests) items.push(`<span class="sm-item attn">📌 ${s.open_requests} 열림</span>`);
      if (s.active_requests) items.push(`<span class="sm-item">⚙ ${s.active_requests} 진행중</span>`);
      if (s.members) items.push(`<span class="sm-item">👥 ${s.members}</span>`);
      if (items.length) {
        els.itemMeta.innerHTML += `<div class="summary-mini" style="width:100%">${items.join("")}</div>`;
        els.itemMeta.hidden = false;
      }
    } catch (e) { /* ignore */ }
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
    // ※ emit("leave") 안 함 — 카카오톡식 동작: 한 번 join 한 방은 영원히 join.
    // 다른 방으로 전환해도 그 방의 새 메시지 알림(소리·토스트·사이드바 깜빡임)을 받기 위함.
    // 서버 connect 핸들러가 모든 방 자동 join 하므로 명시적 emit("join") 도 보험 차원만.
    activeRoom = room;
    app.classList.add("viewing-chat");
    els.chatTitle.textContent = room.name || "(이름없음)";
    renderItemMeta(room);
    els.msgInput.disabled = false;
    els.sendBtn.disabled = false;
    els.attachBtn.disabled = false;
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
    renderMessages(msgs);
    await api.markRead(room.id);
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

  async function refreshRooms() {
    rooms = await api.rooms();
    if (!els.searchResults.hidden) return;
    renderRoomList();
    if (activeRoom) {
      const updated = rooms.find(r => r.id === activeRoom.id);
      if (updated) {
        activeRoom = updated;
        renderItemMeta(updated);
        els.chatTitle.textContent = updated.name || "(이름없음)";
      }
    }
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
      socket.emit("send", payload);
      els.msgInput.value = "";
      autoGrowMsgInput();              // 높이 초기화
      cancelQuoteReply();               // 인용 미리보기 영역 제거
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
        alert(`전송 실패: ${data.error || r.status}\n${data.hint || ""}`);
        // 실패 시 원문 복원
        els.msgInput.value = text;
        autoGrowMsgInput();
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

  // ---------- file upload (with progress) ----------
  async function uploadFiles(files) {
    if (!activeRoom || !files || !files.length) return;

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
        const res = await api.upload(activeRoom.id, f, (pct, loaded, total) => {
          $fill.style.width = pct + "%";
          $pct.textContent = `${pct}%  (${fmtMB(loaded)}/${fmtMB(total)} MB)`;
        });
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
    return `
      <label>
        <input type="checkbox" value="${u.id}">
        <div class="avatar" style="width:28px;height:28px;font-size:12px;background:${u.avatar_color}">${escapeHtml(initial(u.display_name))}</div>
        <span>${escapeHtml(u.display_name)} <small style="color:#9ca3af">@${escapeHtml(u.username)}</small></span>
      </label>`;
  }

  async function ensureUsers() {
    if (!users.length) users = await api.users();
    return users;
  }

  async function openNewRoom() {
    await ensureUsers();
    const others = users.filter(u => u.id !== meId);
    const html = others.map(userPickerHtml).join("");
    els.userPicker.innerHTML = html;
    els.itemUserPicker.innerHTML = html;
    els.roomName.value = "";
    els.itemCustomer.value = "";
    els.itemCode.value = "";
    els.itemName.value = "";
    els.itemStatus.value = "active";
    els.itemDue.value = "";
    setTab("item");
    els.newRoomDialog.showModal();
  }

  async function createRoom(e) {
    e.preventDefault();
    if (activeTab === "item") {
      const name = els.itemName.value.trim();
      if (!name) { alert("아이템 이름은 필수입니다."); return; }
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
    } else {
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
    const isSub = my_role === 'sub_host';
    const canInvite = isHost || isSub;
    const dlg = document.getElementById('roomSettingsDialog');
    const typeLabel = document.getElementById('rsRoomTypeLabel');
    typeLabel.textContent = room.type === 'item' ? '아이템 방' : (room.type === 'direct' ? '1:1 대화' : '그룹 대화');

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
    } else if (isHost) {
      nameHtml += `
        <div class="rs-form">
          <input id="rsRoomNameInput" type="text" maxlength="100" value="${escapeHtml(room.name || '')}" placeholder="방 이름">
          <label class="rs-checkbox">
            <input id="rsNameLockCheck" type="checkbox" ${room.name_locked ? 'checked' : ''}>
            <span>이름 고정 (멤버 별명 금지)</span>
          </label>
          <button type="button" id="rsRenameBtn" class="primary-btn">이름 저장</button>
        </div>
        <div class="rs-hint">방장 권한으로 모든 멤버에게 보이는 이름을 변경합니다.</div>
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
    nameArea.innerHTML = nameHtml;

    // 멤버 목록
    document.getElementById('rsMemberCount').textContent = members.length;
    const memberList = document.getElementById('rsMemberList');
    memberList.innerHTML = members.map(m => {
      const isMe = m.id === meId;
      let actions = '';
      if (!isMe) {
        if (isHost) {
          // 방장: 부방장 토글, 일반 멤버로, 방장 위임, 추방
          if (m.role === 'sub_host') {
            actions += `<button class="rs-act-btn" data-act="demote" data-uid="${m.id}">⭐→👤 일반 멤버로</button>`;
          } else if (m.role === 'member') {
            actions += `<button class="rs-act-btn" data-act="promote" data-uid="${m.id}">👤→⭐ 부방장 지정</button>`;
          }
          actions += `<button class="rs-act-btn rs-danger" data-act="transfer" data-uid="${m.id}">👑 방장 위임</button>`;
          actions += `<button class="rs-act-btn rs-danger" data-act="kick" data-uid="${m.id}">🚪 추방</button>`;
        } else if (isSub && m.role === 'member') {
          actions += `<button class="rs-act-btn rs-danger" data-act="kick" data-uid="${m.id}">🚪 추방</button>`;
        }
      }
      return `
        <div class="rs-member">
          <div class="rs-member-info">
            <span class="avatar" style="background:${m.avatar_color};width:32px;height:32px;font-size:14px">${escapeHtml(m.display_name[0])}</span>
            <div>
              <div class="rs-member-name">${escapeHtml(m.display_name)}${isMe ? ' <span class="rs-me">(나)</span>' : ''}</div>
              <div class="rs-member-role">${_badgeForRole(m.role)}</div>
            </div>
          </div>
          ${actions ? `<div class="rs-member-actions">${actions}</div>` : ''}
        </div>
      `;
    }).join('');

    // 초대 버튼 — self 방은 1인방이라 초대 자체 불가
    document.getElementById('rsInviteArea').style.display = (canInvite && room.type !== 'self') ? 'block' : 'none';

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
        { v: 0,  label: '영구 보존', desc: '글로벌 정책만 적용 (기본 ' + (window.KNK_RETENTION_MONTHS || 12) + '개월)' },
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
          if (!confirm(`[${member.display_name}] 님을 방에서 추방할까요?`)) return;
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
    const candidates = allUsers.filter(u => !existingIds.has(u.id) && u.id !== meId && u.active !== 0);
    const picker = document.getElementById('invitePicker');
    if (!candidates.length) {
      picker.innerHTML = '<div class="rs-hint">초대 가능한 사용자가 없습니다 (모두 이미 멤버).</div>';
    } else {
      picker.innerHTML = candidates.map(u => `
        <label class="user-pick">
          <input type="checkbox" value="${u.id}">
          <span class="avatar" style="background:${u.avatar_color}">${escapeHtml(u.display_name[0])}</span>
          <span class="upn">${escapeHtml(u.display_name)}</span>
        </label>
      `).join('');
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
      els.galleryContent.querySelectorAll(".gallery-tile").forEach(t => {
        t.addEventListener("click", () => {
          els.lightboxImg.src = t.dataset.src;
          els.lightboxMeta.textContent = t.dataset.name;
          els.lightbox.showModal();
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
    if (d.stale_items.length) html += sec(`💤 7일 이상 조용한 아이템`, d.stale_items.map(it => ({ id: 0, title: it.name, due_date: null, room_id: it.room_id, room_name: it.name, customer: it.customer, code: it.code })));
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
      els.requestsList.innerHTML = `<div class="empty-state" style="padding:32px;color:var(--text-soft);">${activeReqTab === "open" ? "열린 요청이 없습니다. 카톡과 다르게 — 묻혀서 잃어버리는 요청은 이제 없습니다." : "해당 상태의 요청이 없습니다."}</div>`;
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
      users.map(u => `<option value="${u.id}">${escapeHtml(u.display_name)}</option>`).join("");
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
    if (!q) {
      els.searchResults.hidden = true;
      els.roomList.hidden = false;
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
              <span style="font-weight:700;font-size:11px;color:#7c3aed">📁 아이템</span>
              ${chips.join("")}
              ${status}
            </div>
            <div class="search-result-content"><strong>${highlight(m.room_name || "", q)}</strong>${m.item_desc ? ` — ${highlight(String(m.item_desc).slice(0,100), q)}` : ""}</div>
          </div>`;
      }
      const content = m.kind === "image" ? `🖼 ${escapeHtml(m.file_name || "사진")}` :
                      m.kind === "file" ? `📎 ${escapeHtml(m.file_name || "파일")}` :
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
    els.chatPane.addEventListener("drop", (e) => {
      e.preventDefault();
      dragCounter = 0;
      overlay.style.display = "none";
      if (!activeRoom) return;
      const files = e.dataTransfer.files;
      if (files && files.length) uploadFiles(files);
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

    // ─── Presence (Telegram-style: PC 활성 시 모바일 푸시 자동 억제) ───
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
    socket.on('connect', () => { _presenceLastActive = null; sendPresence(); });
    if (socket.connected) sendPresence();
    // 가시성 변경
    document.addEventListener('visibilitychange', sendPresence);
    window.addEventListener('focus', sendPresence);
    window.addEventListener('blur', sendPresence);
    // pageshow (bfcache 복원 시 active 재인식)
    window.addEventListener('pageshow', sendPresence);

    socket.on("new_message", (m) => {
      if (activeRoom && m.room_id === activeRoom.id) {
        // 내가 보낸 메시지면 무조건 최하단 (내 발화 보러 가는 게 자연스러움).
        // 남이 보낸 메시지면 nearBottom 가드 — 위쪽 보고 있으면 위치 유지.
        const isMine = m.user_id === meId;
        appendMessage(m, isMine);
        api.markRead(activeRoom.id);
      }
      refreshRooms();
      // ===== 알림 분기 (notify.trigger 내부에서 설정·음소거 추가 분기) =====
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
      // 내 메시지의 read-badge만 다시 그리기
      els.messages.querySelectorAll(".msg.mine").forEach(li => {
        const mid = parseInt(li.dataset.msgId, 10);
        const badge = li.querySelector(".read-badge");
        const others = roomReadStatus.members.filter(mb => mb.user_id !== meId);
        const unreadBy = others.filter(mb => (mb.last_read_message_id || 0) < mid);
        if (badge) {
          if (unreadBy.length === 0) {
            badge.className = "read-badge all-read";
            badge.textContent = "읽음";
            badge.title = "모두 읽음";
          } else {
            badge.className = "read-badge unread";
            badge.textContent = unreadBy.length;
            badge.title = "안 읽음: " + unreadBy.map(x => x.display_name).join(", ");
          }
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

    // ----- 화면 내 토스트 — 카카오톡PC 스타일 (우하단 슬라이드업, 누적) -----
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
                   msg.kind === 'file' ? '📎 파일' : msg.content;

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

  // 카톡 방식: composer-area 는 position:fixed; bottom:0; 으로 layout viewport 하단 고정
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
      const layoutBottom = innerH;
      const visualBottom = vvOffsetTop + vvH;
      const gap = Math.max(0, Math.round(layoutBottom - visualBottom));
      area.style.transform = gap > 0 ? `translateY(-${gap}px)` : 'translateY(0)';
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

  els.newRoomDialog.querySelectorAll(".tab").forEach(t => {
    t.addEventListener("click", () => setTab(t.dataset.tab));
  });

  els.filterBar.querySelectorAll(".chip").forEach(c => {
    c.addEventListener("click", () => {
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
  els.fileInput.addEventListener("change", () => {
    if (els.fileInput.files.length) uploadFiles(els.fileInput.files);
    els.fileInput.value = "";
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
      const map = { requests: "requestsBtn", starred: "starredBtn", gallery: "galleryBtn", export: "exportBtn", edit: "itemEditBtn", leave: "leaveRoomBtn", ai_summary: "aiSummaryBtn" };
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
  // 🧠 AI 요약 + ✨ 작성 도움 (Slack AI / Teams Copilot 식)
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
      popup.innerHTML = matches.map((u, i) => `
        <div class="mention-row ${i === 0 ? 'active' : ''}" data-idx="${i}">
          <div class="avatar" style="width:24px;height:24px;font-size:11px;background:${u.avatar_color}">${escapeHtml(initial(u.display_name))}</div>
          <span><b>${escapeHtml(u.display_name)}</b> <small style="color:#9ca3af">@${escapeHtml(u.username)}</small></span>
        </div>`).join("");
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
      const list = users.filter(u => u.id !== meId).filter(u =>
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

  // setupWebPush — 결과 객체 반환해서 진단 가능. {ok, reason, details}
  async function setupWebPush(opts) {
    opts = opts || {};
    if (!("serviceWorker" in navigator)) {
      return { ok: false, reason: "이 브라우저는 Service Worker 미지원" };
    }
    if (!("PushManager" in window)) {
      return { ok: false, reason: "이 브라우저는 Push API 미지원 (iOS Safari 16.4 미만, 일부 모바일 브라우저)" };
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
    // 알림 권한 + Web Push 자동 구독 (3초 후, 사용자 흐름 방해 X)
    setTimeout(() => setupWebPush(), 3500);
  })();
})();
