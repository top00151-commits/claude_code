// KNK Messenger — client (Phase A+B+C+D)
(() => {
  const app = document.getElementById("app");
  const meId = parseInt(app.dataset.meId, 10);

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
  document.addEventListener("click", (e) => {
    const closeTrigger = e.target.closest("[data-close]");
    if (closeTrigger) {
      const modal = closeTrigger.closest(".modal");
      if (modal) { modal.close(); e.stopPropagation(); return; }
    }
    if (e.target.classList && e.target.classList.contains("modal")) {
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
    rooms: () => fetch("/api/rooms").then(r => r.json()),
    users: () => fetch("/api/users").then(r => r.json()),
    messages: (rid) => fetch(`/api/rooms/${rid}/messages`).then(r => r.json()),
    createRoom: (payload) => fetch("/api/rooms", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }).then(r => r.json()),
    createItem: (payload) => fetch("/api/items", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }).then(r => r.json()),
    getItem: (rid) => fetch(`/api/items/${rid}`).then(r => r.json()),
    updateItem: (rid, payload) => fetch(`/api/items/${rid}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }).then(r => r.json()),
    markRead: (rid) => fetch(`/api/rooms/${rid}/read`, { method: "POST" }),
    upload: (rid, file) => {
      const fd = new FormData();
      fd.append("room_id", rid);
      fd.append("file", file);
      return fetch("/api/upload", { method: "POST", body: fd }).then(r => r.json());
    },
    attachments: (rid, kind) => fetch(`/api/rooms/${rid}/attachments?kind=${kind}`).then(r => r.json()),
    requests: (rid, status) => {
      const q = status && status !== "all" ? `?status=${status}` : "";
      return fetch(`/api/rooms/${rid}/requests${q}`).then(r => r.json());
    },
    summary: (rid) => fetch(`/api/rooms/${rid}/summary`).then(r => r.json()),
    timeline: (rid) => fetch(`/api/rooms/${rid}/timeline`).then(r => r.json()),
    digest: () => fetch("/api/digest").then(r => r.json()),
    createRequest: (payload) => fetch("/api/requests", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }).then(r => r.json()),
    updateRequest: (id, payload) => fetch(`/api/requests/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }).then(r => r.json()),
    myRequests: () => fetch("/api/my/requests").then(r => r.json()),
    search: (q) => fetch(`/api/search?q=${encodeURIComponent(q)}`).then(r => r.json()),
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
      const name = r.name || "(이름없음)";
      const color = r.avatar_color || (r.type === "item" ? "#7c3aed" : "#3b82f6");
      const last = r.last_message ? escapeHtml(String(r.last_message).slice(0, 40)) : "<em style='color:#9ca3af'>대화 없음</em>";
      const time = r.last_at ? fmtTime(r.last_at) : "";
      const unread = r.unread > 0 ? `<span class="unread-badge">${r.unread > 99 ? "99+" : r.unread}</span>` : "";
      const active = activeRoom && activeRoom.id === r.id ? "active" : "";

      let chips = "";
      if (r.type === "item") {
        if (r.item_customer) chips += `<span class="customer-chip">${escapeHtml(r.item_customer)}</span>`;
        if (r.item_code) chips += `<span class="code-chip">${escapeHtml(r.item_code)}</span>`;
        if (r.item_status) chips += `<span class="status-pill status-${r.item_status}">${STATUS_LABEL[r.item_status] || r.item_status}</span>`;
      }

      return `
        <li data-room-id="${r.id}" class="${active} ${r.type === "item" ? "item-row" : ""}">
          <div class="avatar" style="background:${color}">${escapeHtml(initial(name))}</div>
          <div class="room-info">
            <div class="room-name-line">
              ${chips}
              <div class="room-name">${escapeHtml(name)}</div>
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
    scrollToBottom();
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
    let bubble = "";
    if (m.kind === "image" && m.file_path) {
      cls += " image";
      bubble = `<a class="bubble" href="/uploads/${escapeHtml(m.file_path)}" target="_blank" data-img="1"><img src="/uploads/${escapeHtml(m.file_path)}" alt="${escapeHtml(m.file_name || "")}" loading="lazy"></a>`;
    } else if (m.kind === "file" && m.file_path) {
      cls += " file";
      bubble = `
        <div class="bubble">
          <div class="file-icon">${fileIcon(m.file_name)}</div>
          <div class="file-info">
            <div class="file-name">${escapeHtml(m.file_name || "파일")}</div>
            <div class="file-size">${fmtSize(m.file_size)}</div>
          </div>
          <a class="file-link" href="/uploads/${escapeHtml(m.file_path)}" download="${escapeHtml(m.file_name || "")}">받기</a>
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
    return `
      <li class="${cls}" data-msg-id="${m.id}">
        <div class="avatar" style="background:${m.avatar_color || "#3b82f6"}">${escapeHtml(initial(m.display_name))}</div>
        <div class="body">
          ${mine ? "" : `<div class="author">${escapeHtml(m.display_name)}</div>`}
          ${bubble}
          ${rxHtml ? `<div class="reactions">${rxHtml}</div>` : ""}
          <div class="time">${fmtTime(m.created_at)}</div>
        </div>
        <div class="msg-action-bar">
          <button type="button" class="msg-action-btn" data-act="rx" data-emoji="👍" title="좋아요">👍</button>
          <button type="button" class="msg-action-btn" data-act="rx" data-emoji="✅" title="확인">✅</button>
          <button type="button" class="msg-action-btn" data-act="rx" data-emoji="❤" title="응원">❤</button>
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

  function appendMessage(m) {
    if (!els.messages.querySelector(".msg")) {
      els.messages.innerHTML = "";
    }
    els.messages.insertAdjacentHTML("beforeend", msgHtml(m));
    wireMessageActions();
    scrollToBottom();
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
        await fetch(`/api/messages/${mid}/react`, {
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
        await fetch(`/api/messages/${mid}/react`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ emoji: c.dataset.emoji }),
        });
      });
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

  function scrollToBottom() {
    requestAnimationFrame(() => {
      els.messages.scrollTop = els.messages.scrollHeight;
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
    if (activeRoom && activeRoom.id !== room.id) {
      socket.emit("leave", { room_id: activeRoom.id });
    }
    activeRoom = room;
    app.classList.add("viewing-chat");
    els.chatTitle.textContent = room.name || "(이름없음)";
    renderItemMeta(room);
    els.msgInput.disabled = false;
    els.sendBtn.disabled = false;
    els.attachBtn.disabled = false;
    els.msgInput.focus();
    socket.emit("join", { room_id: room.id });
    const msgs = await api.messages(room.id);
    renderMessages(msgs);
    await api.markRead(room.id);
    await refreshRooms();
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

  async function send() {
    const text = els.msgInput.value.trim();
    if (!text || !activeRoom) return;
    socket.emit("send", { room_id: activeRoom.id, content: text });
    els.msgInput.value = "";
    els.msgInput.focus();
  }

  // ---------- file upload ----------
  async function uploadFiles(files) {
    if (!activeRoom || !files || !files.length) return;
    for (const f of files) {
      try {
        const res = await api.upload(activeRoom.id, f);
        if (res.error) {
          alert(`업로드 실패: ${f.name} — ${res.error}`);
        }
      } catch (e) {
        alert(`업로드 실패: ${f.name}`);
      }
    }
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
        <div class="gallery-tile" data-src="/uploads/${escapeHtml(m.file_path)}" data-name="${escapeHtml(m.file_name || "")}">
          <img src="/uploads/${escapeHtml(m.file_path)}" loading="lazy" alt="${escapeHtml(m.file_name || "")}">
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
          <a href="/uploads/${escapeHtml(m.file_path)}" download="${escapeHtml(m.file_name || "")}">받기</a>
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
    socket = io({ transports: ["websocket", "polling"] });
    socket.on("new_message", (m) => {
      if (activeRoom && m.room_id === activeRoom.id) {
        appendMessage(m);
        api.markRead(activeRoom.id);
      }
      refreshRooms();
    });
    socket.on("requests_updated", (e) => {
      if (activeRoom && e.room_id === activeRoom.id) {
        refreshRequestsBadge();
        if (els.requestsDialog.open) renderRequests();
      }
    });
    socket.on("reaction_updated", async (e) => {
      if (!activeRoom || e.room_id !== activeRoom.id) return;
      // 해당 메시지만 다시 그리기 — 전체 messages 재요청 가성비
      const msgs = await api.messages(activeRoom.id);
      const target = msgs.find(m => m.id === e.message_id);
      if (!target) return;
      const li = els.messages.querySelector(`.msg[data-msg-id="${e.message_id}"]`);
      if (li) {
        const tmp = document.createElement("div");
        tmp.innerHTML = msgHtml(target);
        li.replaceWith(tmp.firstElementChild);
        wireMessageActions();
      }
    });
  }

  // ---------- wire ----------
  els.composer.addEventListener("submit", (e) => { e.preventDefault(); send(); });
  els.backBtn.addEventListener("click", () => {
    app.classList.remove("viewing-chat");
    if (activeRoom) socket.emit("leave", { room_id: activeRoom.id });
    activeRoom = null;
    els.chatTitle.textContent = "대화를 선택하세요";
    els.itemMeta.hidden = true;
    els.itemMeta.innerHTML = "";
    els.itemEditBtn.hidden = true;
    els.galleryBtn.hidden = true;
    els.requestsBtn.hidden = true;
    els.requestsBadge.hidden = true;
    if (els.exportBtn) els.exportBtn.hidden = true;
    els.msgInput.disabled = true;
    els.sendBtn.disabled = true;
    els.attachBtn.disabled = true;
    els.messages.innerHTML = "";
    refreshRooms();
  });
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

  els.attachBtn.addEventListener("click", () => els.fileInput.click());
  els.fileInput.addEventListener("change", () => {
    if (els.fileInput.files.length) uploadFiles(els.fileInput.files);
    els.fileInput.value = "";
  });

  if (els.exportBtn) {
    els.exportBtn.addEventListener("click", () => {
      if (!activeRoom) return;
      window.location.href = `/api/rooms/${activeRoom.id}/export.xlsx`;
    });
  }
  els.galleryBtn.addEventListener("click", () => openGallery("image"));
  els.closeGallery.addEventListener("click", () => els.galleryDialog.close());
  els.galleryDialog.querySelectorAll(".gtab").forEach(t => {
    t.addEventListener("click", () => openGallery(t.dataset.gtab));
  });
  els.requestsBtn.addEventListener("click", openRequests);

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

  els.digestBtn.addEventListener("click", () => openDigest(false));
  els.closeDigest.addEventListener("click", () => els.digestDialog.close());

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

  async function setupWebPush() {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) return;
    try {
      const reg = await navigator.serviceWorker.ready;
      const cfg = await fetch("/api/push/vapid_public").then(r => r.ok ? r.json() : null);
      if (!cfg || !cfg.public_key || !cfg.enabled) return;
      let sub = await reg.pushManager.getSubscription();
      if (!sub) {
        // 권한 확인
        if (Notification.permission !== "granted") {
          const p = await Notification.requestPermission();
          if (p !== "granted") return;
        }
        sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(cfg.public_key),
        });
      }
      // 서버 등록 (or 갱신)
      await fetch("/api/push/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subscription: sub.toJSON() }),
      });
    } catch (e) {
      console.log("Web Push 설정 실패:", e);
    }
  }

  // ---------- boot ----------
  (async () => {
    connectSocket();
    await ensureUsers();    // 멘션 렌더 위해 미리 로드
    await refreshRooms();
    setupMentionAutocomplete();
    setInterval(refreshRooms, 30000);

    // /chat?room=N — 대시보드에서 카드 클릭으로 진입 시 해당 방 자동 열기
    const params = new URLSearchParams(window.location.search);
    const wantRoom = parseInt(params.get("room") || "", 10);
    if (wantRoom) {
      const room = rooms.find(r => r.id === wantRoom);
      if (room) {
        history.replaceState(null, "", "/chat");
        setTimeout(() => openRoom(room), 300);
      }
    }

    // 첫 진입 시 다이제스트 자동 노출 (오늘/지연 있으면)
    if (!sessionStorage.getItem("digest_seen_today") && !wantRoom) {
      sessionStorage.setItem("digest_seen_today", "1");
      setTimeout(() => openDigest(true), 800);
    }
    // 알림 권한 + Web Push 자동 구독 (3초 후, 사용자 흐름 방해 X)
    setTimeout(() => setupWebPush(), 3500);
  })();
})();
