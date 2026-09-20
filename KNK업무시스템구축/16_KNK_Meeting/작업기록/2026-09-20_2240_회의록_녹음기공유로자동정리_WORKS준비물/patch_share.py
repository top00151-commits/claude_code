# -*- coding: utf-8 -*-
"""z1117 — 휴대폰 녹음기 「공유 → KNK Eum WORKS」 → 회의록에 붙이고 자동 정리 (대표 지시 2026-09-20)

대표 지시: 「녹음기로 녹음한 것은 종료 누르면 자동으로 요약이 되는 걸로 만들어야 해.」 → 대표 선택 「녹음기에서 공유 → WORKS 로 바로」.

평소 길(z1115): 녹음기가 파일을 회의록 화면으로 **직접 돌려준다** → 이미 자동.
남은 구멍: 회의가 길어 크롬이 그 화면을 버리면 돌려줄 곳이 없다.
→ 설치된 WORKS 앱을 **공유 대상(Web Share Target)** 으로 등록해, 녹음기의 「공유」에서 바로 보낼 수 있게 한다.
  넘기던 회의가 이 브라우저에 표시돼 있으면 묻지 않고 붙이고, 없으면 한 번 골라 붙인다. 붙이면 자동 정리.

사용: py patch_share.py <원본 폴더> <결과 폴더>
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
os.makedirs(DST, exist_ok=True)


def load(name):
    s = io.open(os.path.join(SRC, name), encoding="utf-8", newline="").read()
    assert "\r\n" not in s, name + ": CRLF 원본 — git show 결과(LF)를 쓸 것"
    return s


def save(name, s):
    with io.open(os.path.join(DST, name), "w", encoding="utf-8", newline="") as f:
        f.write(s)


def sub1(s, old, new, tag):
    n = s.count(old)
    assert n == 1, "%s: 앵커 %d개(1개여야 함)" % (tag, n)
    return s.replace(old, new)


m0 = load("main.py")
m = m0

# ── ① manifest — 공유 대상 등록
m = sub1(
    m,
    '        "start_url": "/app",\n        "scope": "/",\n',
    '        "start_url": "/app",\n        "scope": "/",\n'
    '        # z1117 (대표 지시 2026-09-20): 휴대폰 녹음기 등의 「공유」 목록에 WORKS 를 띄운다.\n'
    '        #   회의가 길어 크롬이 녹음 화면을 버려도, 녹음기에서 공유 한 번으로 회의록에 붙고 자동 정리된다.\n'
    '        #   ⚠ 설치된 앱(WebAPK)에만 뜬다 — manifest 가 바뀌면 크롬이 앱을 다시 만들 때까지(보통 하루) 걸린다.\n'
    '        "share_target": {\n'
    '            "action": "/share/audio",\n'
    '            "method": "POST",\n'
    '            "enctype": "multipart/form-data",\n'
    '            "params": {"files": [{"name": "audio", "accept": ["audio/*"]}]},\n'
    '        },\n',
    "manifest 공유 대상",
)

# ── ② 받기·붙이기 — 음성 올리기 라우트 바로 뒤에
SHARE_PY = r'''

# ── 📤 휴대폰 녹음기 「공유」 → 회의록 (z1117 · 대표 지시 2026-09-20) ──────────────
#   대표 지시: 「녹음기로 녹음한 것이 자동으로 요약되게.」
#   평소엔 녹음기가 파일을 회의록 화면으로 직접 돌려준다(z1115 · input capture) → 그대로 자동.
#   회의가 길어 크롬이 그 화면을 버리면 돌려줄 곳이 없어진다 → 「공유」로 들어오는 두 번째 길.
#   받은 파일은 잠깐 `meeting_audio/_share/` 에 두었다가, 어느 회의록인지 정해지면 그 회의 폴더로 옮긴다.
_SHARE_DIR = os.path.join("meeting_audio", "_share")
_SHARE_OK = set("abcdefghijklmnopqrstuvwxyz0123456789_")


def _share_sweep(hours: int = 24):
    """붙이지 않고 버려진 공유 파일 치우기(하루 지난 것)."""
    import time as _t
    try:
        cut = _t.time() - hours * 3600
        for fn in os.listdir(_SHARE_DIR):
            p = os.path.join(_SHARE_DIR, fn)
            try:
                if os.path.isfile(p) and os.path.getmtime(p) < cut:
                    os.remove(p)
            except OSError:
                pass
    except OSError:
        pass


def _share_find(token: str, uid: int) -> str:
    """받은 파일 찾기 — 표는 올린 사람 번호를 품고 있어 남의 것은 집히지 않는다."""
    token = (token or "").strip()
    if not token or len(token) > 64 or not set(token) <= _SHARE_OK:
        return ""
    if not token.startswith("s_%d_" % int(uid)):
        return ""
    try:
        for fn in os.listdir(_SHARE_DIR):
            if fn.rsplit(".", 1)[0] == token:
                return os.path.join(_SHARE_DIR, fn).replace("\\", "/")
    except OSError:
        pass
    return ""


def _share_attach(mid: int, path: str) -> int:
    """받은 파일을 그 회의 폴더로 옮기고 '아직 글자로 안 바꾼 녹음'에 넣는다. 크기(바이트) 반환."""
    import time as _time
    import shutil as _sh
    ext = os.path.splitext(path)[1].lower() or ".m4a"
    audio_dir = os.path.join("meeting_audio", "meeting_%d" % mid)
    os.makedirs(audio_dir, exist_ok=True)
    rel = os.path.join(audio_dir, "rec_%d%s" % (int(_time.time()), ext)).replace("\\", "/")
    _sh.move(path, rel)
    n = os.path.getsize(rel)
    with db_session() as c:
        c.execute("UPDATE meetings SET audio_path=?, mode='B', updated_at=datetime('now','localtime') WHERE id=?",
                  (rel, mid))
    _rec_add_pending(mid, rel)   # z1113: 끊긴 조각과 차례로 변환돼 본문에 이어 붙는다
    return n


_SHARE_LOGIN_HTML = """<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>로그인 필요 · KNK HAIST WORKS</title>
<style>body{font-family:-apple-system,BlinkMacSystemFont,'Malgun Gothic',sans-serif;margin:0;padding:32px 22px;
color:#1f2328;line-height:1.8}h1{font-size:19px;margin:0 0 12px}a{display:inline-block;margin-top:18px;
background:#A5282C;color:#fff;text-decoration:none;padding:14px 20px;border-radius:12px;font-weight:800}</style>
</head><body><h1>🔒 로그인이 풀려 있습니다</h1>
<p>아래 단추로 WORKS 를 연 뒤 로그인하고, <b>녹음기에서 한 번 더 공유</b>해 주세요.<br>
<b>녹음 파일은 휴대폰에 그대로 있습니다.</b></p>
<a href="/app">WORKS 열기</a></body></html>"""


@app.post("/share/audio", response_class=HTMLResponse)
async def share_audio_receive(req: Request):
    """휴대폰 녹음기 등에서 「공유 → KNK Eum WORKS」로 보낸 음성 받기(설치된 앱의 공유 대상)."""
    u = get_user(req)
    if not u:
        return HTMLResponse(_SHARE_LOGIN_HTML, status_code=401)
    form = await req.form()
    f = form.get("audio")
    if f is None or not hasattr(f, "filename"):
        f = None
        for _v in form.values():                       # 이름이 다른 기기도 있다 — 파일이면 받는다
            if hasattr(_v, "filename") and getattr(_v, "filename", ""):
                f = _v
                break
    if f is None or not getattr(f, "filename", ""):
        return ctx(req, "share_audio.html", user=u, share=None, meetings=[], ok_ids=[], err="nofile", errmsg="")
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in _MEETING_AUDIO_EXT:
        return ctx(req, "share_audio.html", user=u, share=None, meetings=[], ok_ids=[],
                   err="ext", errmsg="지원하지 않는 음성 형식(%s)입니다." % (ext or "알 수 없음"))
    _lim = _MEETING_AUDIO_MAX_MB * 1024 * 1024
    _sz = getattr(f, "size", None)
    if _sz is not None and _sz > _lim:
        return ctx(req, "share_audio.html", user=u, share=None, meetings=[], ok_ids=[],
                   err="toobig", errmsg=_meeting_audio_too_big(_sz))
    import time as _time
    import binascii as _bl
    from starlette.concurrency import run_in_threadpool
    os.makedirs(_SHARE_DIR, exist_ok=True)
    _share_sweep()
    token = "s_%d_%d_%s" % (u["id"], int(_time.time()), _bl.hexlify(os.urandom(4)).decode())
    path = os.path.join(_SHARE_DIR, token + ext)
    n = await run_in_threadpool(_meeting_audio_save, f.file, path, _lim)
    if n > _lim:
        try:
            os.remove(path)
        except OSError:
            pass
        return ctx(req, "share_audio.html", user=u, share=None, meetings=[], ok_ids=[],
                   err="toobig", errmsg=_meeting_audio_too_big(n, exact=False))
    if n < 100:
        try:
            os.remove(path)
        except OSError:
            pass
        return ctx(req, "share_audio.html", user=u, share=None, meetings=[], ok_ids=[],
                   err="nofile", errmsg="")
    # 붙일 수 있는 최근 회의(내가 고칠 수 있는 것만) — 표시가 없을 때 고르게
    with db_session() as c:
        rows = c.execute("""SELECT * FROM meetings
                            ORDER BY meeting_date DESC, id DESC LIMIT 60""").fetchall()
        mine = [dict(r) for r in rows if _can_edit_meeting(u, dict(r))][:12]
    print(f"[SHARE-AUDIO] uid={u['id']} {f.filename} {n // 1024}KB → {token}", flush=True)
    return ctx(req, "share_audio.html", user=u,
               share={"token": token, "name": f.filename[:80], "mb": round(n / 1048576, 1)},
               meetings=[{"id": x["id"], "title": x["title"], "meeting_date": x["meeting_date"]} for x in mine],
               ok_ids=[x["id"] for x in mine], err="", errmsg="")


@app.post("/api/meeting/{mid:int}/attach-share")
async def api_meeting_attach_share(req: Request, mid: int):
    """공유로 받은 음성을 이 회의록에 붙인다(그 뒤 화면이 자동 정리를 잇는다)."""
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False, "error": "로그인 필요"}, 401)
    d = await req.json()
    with db_session() as c:
        r = c.execute("SELECT * FROM meetings WHERE id=?", (mid,)).fetchone()
        if not r:
            return JSONResponse({"ok": False, "error": "없는 회의록입니다."}, 404)
        if not _can_edit_meeting(u, dict(r)):
            return JSONResponse({"ok": False, "error": "권한이 없습니다."}, 403)
    path = _share_find(d.get("token") or "", u["id"])
    if not path or not os.path.exists(path):
        return JSONResponse({"ok": False, "error": "받은 녹음을 찾지 못했습니다 — 녹음기에서 다시 공유해 주세요."}, 404)
    from starlette.concurrency import run_in_threadpool
    n = await run_in_threadpool(_share_attach, mid, path)
    print(f"[SHARE-AUDIO] uid={u['id']} → 회의 {mid} 붙임 {n // 1024}KB", flush=True)
    return JSONResponse({"ok": True, "id": mid, "size_kb": n // 1024})


@app.post("/api/meeting/share-new")
async def api_meeting_share_new(req: Request):
    """공유로 받은 음성으로 새 회의록을 만들고 붙인다(제목은 AI 정리 때 자동으로 지어진다)."""
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False, "error": "로그인 필요"}, 401)
    d = await req.json()
    path = _share_find(d.get("token") or "", u["id"])
    if not path or not os.path.exists(path):
        return JSONResponse({"ok": False, "error": "받은 녹음을 찾지 못했습니다 — 녹음기에서 다시 공유해 주세요."}, 404)
    from starlette.concurrency import run_in_threadpool
    today = date.today().isoformat()
    with db_session() as c:
        cur = c.execute(
            """INSERT INTO meetings(title, meeting_date, mode, team_id, owner_id,
                                    location, tags, attendees_text, body, visibility, status)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            ("제목 없는 회의 " + today, today, "B", u.get("team_id"), u["id"], "", "", "", "", "team", "draft"),
        )
        mid = cur.lastrowid
    n = await run_in_threadpool(_share_attach, mid, path)
    print(f"[SHARE-AUDIO] uid={u['id']} → 새 회의 {mid} 만들고 붙임 {n // 1024}KB", flush=True)
    return JSONResponse({"ok": True, "id": mid, "size_kb": n // 1024})

'''
m = sub1(
    m,
    "\n\n# ── 🔴 녹음 중 서버 저장 (z1113 · 대표 지시 2026-09-18) ",
    SHARE_PY + "\n# ── 🔴 녹음 중 서버 저장 (z1113 · 대표 지시 2026-09-18) ",
    "공유 받기 라우트",
)

save("main.py", m)

# 새 화면은 그대로 복사
tpl = load("share_audio.html")
save("share_audio.html", tpl)

print("[OK] main.py %d → %d 글자" % (len(m0), len(m)))
for k, got, want in [("share_target", m.count('"share_target"'), 1),
                     ("/share/audio 라우트", m.count('@app.post("/share/audio"'), 1),
                     ("attach-share", m.count("attach-share"), 1),
                     ("share-new", m.count('"/api/meeting/share-new"'), 1),
                     ("_share_attach", m.count("_share_attach"), 3),
                     ("_share_find", m.count("_share_find"), 3)]:
    print("   %-20s %d  %s" % (k, got, "OK" if got == want else "⚠ %d 예상" % want))
    assert got == want, k
print("[OK] share_audio.html %d 글자" % len(tpl))
