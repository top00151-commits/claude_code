# ════════════════════════════════════════════════════════════════════════
#  🎙 음성 메모 (z1144 · 대표 지시 2026-10-08)
#  「이 녹음파일 올려서 정리하는 걸 지금은 회의록 들어가서 새 회의록을 눌러야만 하는데…
#    회의록 말고 **일반적인 의견 내용을 녹음한 걸 정리해주는 것도** 필요해」
#  쓰임새(대표): 떠오른 생각·지시사항 / 전화 통화·고객 방문 / 현장·설비 메모 / 말로 하는 보고
#  🔴 **내 것만 보인다**(대표 결정) — 관리자도 남의 메모는 못 본다.
#  🔴 meetings 표와 섞지 않는다 — 거긴 이음과 얽혀 있어(회의 카드·참석자 동기화·삭제 연동)
#     한 군데만 조건을 빠뜨려도 개인 메모가 이음 회의 카드로 새어 나간다.
#  🔴 녹음 처리 알맹이(_stt_one: 25MB 넘으면 쪼개기)는 회의록과 **한 벌**을 같이 쓴다.
#  🔴 개인 메모라 활동 기록(log_activity)에 남기지 않는다.
# ════════════════════════════════════════════════════════════════════════
_VN_DIR = "voice_notes"
_VN_JOBS: dict = {}
_VN_LOCK = _stt_thr.Lock()


def _vn_row(c, nid: int):
    r = c.execute("SELECT * FROM voice_notes WHERE id=?", (nid,)).fetchone()
    return dict(r) if r else None


def _vn_mine(u, n) -> bool:
    """🔴 내 것만 — 대표 결정 2026-10-08. 보기·고치기·지우기 모두 이 판정 하나를 쓴다."""
    try:
        return bool(n) and bool(u) and int(n.get("owner_id") or 0) == int(u["id"])
    except Exception:
        return False


def _vn_progress(nid: int, txt: str):
    with _VN_LOCK:
        j = _VN_JOBS.get(nid)
        if j is not None and j.get("state") == "running":
            j["progress"] = txt


def _vn_worker(nid: int, disk: str):
    """음성 → 글자 → 메모 원문에 덧붙이기(백그라운드). 사람이 고쳐 둔 원문은 지우지 않는다."""
    text, err, warn = "", "", ""
    try:
        text, err, warn = _stt_one(0, disk, "", "", progress=lambda t: _vn_progress(nid, t))
        if text:
            with db_session() as c:
                row = c.execute("SELECT body FROM voice_notes WHERE id=?", (nid,)).fetchone()
                prev = ((row["body"] if row else "") or "").strip()
                body = ((prev + "\n\n") if prev else "") + text.strip()
                c.execute("UPDATE voice_notes SET body=?, updated_at=datetime('now','localtime') WHERE id=?",
                          (body, nid))
    except Exception as _e:
        err = err or f"받아쓴 글을 저장하지 못했습니다: {_e}"
    with _VN_LOCK:
        _VN_JOBS[nid] = {"state": ("error" if err else "done"), "error": err, "warn": warn, "progress": ""}


@app.get("/voice-notes", response_class=HTMLResponse)
async def voice_notes_page(req: Request):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login?next=/voice-notes", 303)
    with db_session() as c:
        rows = c.execute("SELECT * FROM voice_notes WHERE owner_id=? ORDER BY id DESC LIMIT 300",
                         (u["id"],)).fetchall()
    return ctx(req, "voice_notes.html", user=u, notes=[dict(r) for r in rows])


@app.get("/voice-notes/new", response_class=HTMLResponse)
async def voice_note_new_page(req: Request):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login?next=/voice-notes/new", 303)
    return ctx(req, "voice_note_form.html", user=u, note=None)


@app.get("/voice-notes/{nid:int}", response_class=HTMLResponse)
async def voice_note_detail_page(req: Request, nid: int):
    u = get_user(req)
    if not u:
        return RedirectResponse(f"/login?next=/voice-notes/{nid}", 303)
    with db_session() as c:
        n = _vn_row(c, nid)
    if not n or not _vn_mine(u, n):
        return RedirectResponse("/voice-notes", 303)
    return ctx(req, "voice_note_form.html", user=u, note=n)


@app.post("/api/voice-note")
async def api_voice_note_create(req: Request):
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    try:
        d = await req.json()
    except Exception:
        d = {}
    title = str(d.get("title") or "").strip()[:200]
    with db_session() as c:
        nid = c.execute("INSERT INTO voice_notes(owner_id, title) VALUES(?, ?)",
                        (u["id"], title)).lastrowid
    return JSONResponse({"ok": True, "id": nid})


@app.get("/api/voice-note/{nid:int}")
async def api_voice_note_get(req: Request, nid: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    with db_session() as c:
        n = _vn_row(c, nid)
    if not _vn_mine(u, n):
        return JSONResponse({"ok": False, "error": "없거나 볼 수 없는 메모입니다."}, 404)
    return JSONResponse({"ok": True, "note": {k: n.get(k) for k in
                                              ("id", "title", "body", "summary", "audio_path",
                                               "created_at", "updated_at")}})


@app.post("/api/voice-note/{nid:int}/audio")
async def api_voice_note_audio_upload(req: Request, nid: int, file: UploadFile = File(...)):
    """휴대폰 녹음 올리기 → voice_notes/note_{id}/ 에 저장. 받는 형식·한도는 회의록과 같다."""
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    with db_session() as c:
        n = _vn_row(c, nid)
    if not _vn_mine(u, n):
        return JSONResponse({"ok": False, "error": "없거나 볼 수 없는 메모입니다."}, 404)
    orig = file.filename or "rec.m4a"
    ext = os.path.splitext(orig)[1].lower() or ".m4a"
    if ext not in _MEETING_AUDIO_EXT:
        return JSONResponse({"ok": False, "error": f"지원하지 않는 음성 형식({ext})."}, 400)
    _lim = _MEETING_AUDIO_MAX_MB * 1024 * 1024
    _sz = getattr(file, "size", None)
    if _sz is not None and _sz > _lim:
        return JSONResponse({"ok": False, "error": _meeting_audio_too_big(_sz)}, 400)
    if _sz is not None and _sz < 100:
        return JSONResponse({"ok": False, "error": "빈/손상 음성 파일입니다."}, 400)
    import time as _time
    from starlette.concurrency import run_in_threadpool
    audio_dir = os.path.join(_VN_DIR, f"note_{nid}")
    os.makedirs(audio_dir, exist_ok=True)
    ts = int(_time.time())
    disk_path = os.path.join(audio_dir, f"rec_{ts}{ext}")
    _n = await run_in_threadpool(_meeting_audio_save, file.file, disk_path, _lim)
    if _n > _lim:
        return JSONResponse({"ok": False, "error": _meeting_audio_too_big(_n, exact=False)}, 400)
    if _n < 100:
        return JSONResponse({"ok": False, "error": "빈/손상 음성 파일입니다."}, 400)
    rel = disk_path.replace("\\", "/")
    with db_session() as c:
        c.execute("UPDATE voice_notes SET audio_path=?, updated_at=datetime('now','localtime') WHERE id=?",
                  (rel, nid))
    return JSONResponse({"ok": True, "size_kb": _n // 1024})


@app.get("/api/voice-note/{nid:int}/audio")
async def api_voice_note_audio_get(req: Request, nid: int):
    """녹음 다시 듣기 — 내 메모만(정적 노출 금지)."""
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    with db_session() as c:
        n = _vn_row(c, nid)
    if not _vn_mine(u, n):
        return JSONResponse({"error": "권한 없음"}, 403)
    disk = (n.get("audio_path") or "").strip()
    if not disk or not os.path.exists(disk):
        return JSONResponse({"error": "녹음 없음"}, 404)
    ext = os.path.splitext(disk)[1].lower()
    return FileResponse(disk, media_type=_MEETING_AUDIO_MIME.get(ext, "application/octet-stream"))


@app.post("/api/voice-note/{nid:int}/transcribe")
async def api_voice_note_transcribe(req: Request, nid: int):
    """음성 → 글자 (백그라운드 시작). 상태는 /stt-status 로 본다."""
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    from . import ai_client
    if not ai_client.transcribe_available():
        return JSONResponse({"ok": False, "error": "음성→글자는 OpenAI 키가 필요합니다(현재 미설정/무효). "
                                                   "관리자 → AI 설정에서 등록하면 즉시 동작합니다."}, 400)
    with db_session() as c:
        n = _vn_row(c, nid)
    if not _vn_mine(u, n):
        return JSONResponse({"ok": False, "error": "없거나 볼 수 없는 메모입니다."}, 404)
    disk = (n.get("audio_path") or "").strip()
    if not disk or not os.path.exists(disk):
        return JSONResponse({"ok": False, "error": "녹음 파일이 없습니다. 먼저 올려 주세요."}, 400)
    with _VN_LOCK:
        if (_VN_JOBS.get(nid) or {}).get("state") == "running":
            return JSONResponse({"ok": True, "already": True})
        _VN_JOBS[nid] = {"state": "running", "progress": "", "error": "", "warn": ""}
    _stt_thr.Thread(target=_vn_worker, args=(nid, disk), daemon=True).start()
    return JSONResponse({"ok": True, "started": True})


@app.get("/api/voice-note/{nid:int}/stt-status")
async def api_voice_note_stt_status(req: Request, nid: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    with db_session() as c:
        n = _vn_row(c, nid)
    if not _vn_mine(u, n):
        return JSONResponse({"ok": False, "error": "없거나 볼 수 없는 메모입니다."}, 404)
    with _VN_LOCK:
        j = dict(_VN_JOBS.get(nid) or {"state": "idle"})
    j["ok"] = True
    return JSONResponse(j)


@app.post("/api/voice-note/{nid:int}/extract")
async def api_voice_note_extract(req: Request, nid: int):
    """받아쓴 원문 → 요점·할 일 정리. 🔴 원문(body)은 바꾸지 않는다."""
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    from . import ai_client
    if not ai_client.ai_available():
        return JSONResponse({"ok": False, "error": "AI가 비활성 상태입니다(키 미설정)."}, 400)
    with db_session() as c:
        n = _vn_row(c, nid)
    if not _vn_mine(u, n):
        return JSONResponse({"ok": False, "error": "없거나 볼 수 없는 메모입니다."}, 404)
    body = (n.get("body") or "").strip()
    if not body:
        return JSONResponse({"ok": False, "error": "정리할 내용이 없습니다. 녹음을 먼저 올리세요."}, 400)
    ok, r = ai_client.ai_extract_note(body)
    if not ok:
        return JSONResponse({"ok": False, "error": r.get("error", "정리 실패")}, 502)
    summary = (r.get("summary") or "").strip()[:20000]
    title = (n.get("title") or "").strip()
    new_title = title or (r.get("title") or "").strip()[:200]   # 사람이 지은 제목은 건드리지 않는다
    with db_session() as c:
        c.execute("UPDATE voice_notes SET summary=?, title=?, updated_at=datetime('now','localtime') "
                  "WHERE id=?", (summary, new_title, nid))
    return JSONResponse({"ok": True, "summary": summary, "title": new_title})


@app.post("/api/voice-note/{nid:int}/save")
async def api_voice_note_save(req: Request, nid: int):
    """제목·원문·정리 글 고치기 — 보낸 칸만 바꾼다."""
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    try:
        d = await req.json()
    except Exception:
        d = {}
    with db_session() as c:
        n = _vn_row(c, nid)
    if not _vn_mine(u, n):
        return JSONResponse({"ok": False, "error": "없거나 볼 수 없는 메모입니다."}, 404)
    sets, args = [], []
    if d.get("title") is not None:
        sets.append("title=?")
        args.append(str(d.get("title")).strip()[:200])
    if d.get("body") is not None:
        sets.append("body=?")
        args.append(str(d.get("body")).replace("\r\n", "\n").strip()[:200000])
    if d.get("summary") is not None:
        sets.append("summary=?")
        args.append(str(d.get("summary")).replace("\r\n", "\n").strip()[:20000])
    if not sets:
        return JSONResponse({"ok": False, "error": "바꿀 내용이 없습니다."}, 400)
    args.append(nid)
    with db_session() as c:
        c.execute("UPDATE voice_notes SET " + ", ".join(sets)
                  + ", updated_at=datetime('now','localtime') WHERE id=?", tuple(args))
        ts = _row_ts(c, "voice_notes", nid)
    return JSONResponse({"ok": True, "updated_at": ts})


@app.delete("/api/voice-note/{nid:int}")
async def api_voice_note_delete(req: Request, nid: int):
    """메모 지우기 — 올린 녹음 파일도 함께. 🔴 내 것만."""
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    with db_session() as c:
        n = _vn_row(c, nid)
    if not _vn_mine(u, n):
        return JSONResponse({"ok": False, "error": "없거나 볼 수 없는 메모입니다."}, 404)
    import shutil as _sh
    try:
        _dir = os.path.join(_VN_DIR, f"note_{nid}")
        if os.path.isdir(_dir):
            _sh.rmtree(_dir, ignore_errors=True)
    except Exception as _e:
        print(f"[VOICE-NOTE] 녹음 폴더 삭제 실패(무시): {_e}")
    with db_session() as c:
        c.execute("DELETE FROM voice_notes WHERE id=?", (nid,))
    with _VN_LOCK:
        _VN_JOBS.pop(nid, None)
    return JSONResponse({"ok": True})


