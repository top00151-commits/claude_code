# -*- coding: utf-8 -*-
"""아웃룩 옛 메일 가져오기 — 11-25 대표
「1. 기간: 5년전부터 / 3년전부터 / 2년전부터 / 1년전부터 (불러올때 사용자가 선택할수있게) 2. 첨부는 기간설정에 따라 동일하게 적용
 3. 폴더: 아웃룩폴더 구성 따를지, 이음웍스 자동분류 따를지, 아니면 사용자가 직접할지.. 이건 전직원 적용 …
 내것만 "아웃룩 폴더와 동일한 폴더만 적용해주고 아닌건 내가 따로 정리할께."」

흐름: 화면에서 기간·폴더 방식을 고르고 「가져오기 번호」를 만든다(1회용 · 해시만 저장) →
      PC 명령(deploy/outlook_import.ps1 -Code 번호)이 아웃룩 메일을 최근 것부터 한 통씩 POST →
      같은 메일(같은 Message-ID)은 건너뜀 · 받은 시각 = 아웃룩 받은 시각 · 읽음 · AI·알림·자동 응답 없음.
폴더 방식:
  outlook = 아웃룩 폴더 그대로(「받은 편지함」 아래 경로를 메일 폴더로 · 없으면 새로 만듦 · 3단계까지)
  auto    = 이음웍스 자동 분류(고정 안 함)
  manual  = 직접 정리(모두 「일반」 = 분류안됨에 고정)
  match   = **대표 계정만**(직원 화면에 없음) — 아웃룩 폴더 마지막 이름과 같은 이름의 이음웍스 폴더가 **하나만** 있으면 그 폴더 · 아니면 「일반」
서버 공간: 첨부 폴더 디스크 남은 공간이 15% 또는 5GB 밑이면 받지 않음.
"""
import base64
import datetime as _dt
import hashlib
import os
import re
import secrets
import shutil

YEARS = (5, 3, 2, 1)
STAFF_MODES = ("outlook", "auto", "manual")
OWNER_MODE = "match"
MAX_MAIL_BYTES = 30 * 1024 * 1024        # 한 통 첨부 합계가 이보다 크면 첨부 빼고 본문만
MAX_REQ_BYTES = 45 * 1024 * 1024         # 요청 하나(첨부 base64 포함) 한도
TOKEN_HOURS = 24
TOKEN_IDLE_HOURS = 6                     # 가져오는 중이면 마지막으로 받은 때부터 6시간 더(만든 뒤 최대 72시간)
TOKEN_MAX_HOURS = 72
DISK_MIN_FREE = 5 * 1024 ** 3
DISK_MIN_RATIO = 0.15
_INBOX_NAMES = {"받은편지함", "inbox", "받은메일함"}

MODE_NAME = {"outlook": "아웃룩 폴더 그대로", "auto": "이음웍스 자동 분류", "manual": "직접 정리(모두 「분류안됨」)",
             "match": "같은 이름 폴더만 · 나머지는 직접 정리"}


def _now():
    return _dt.datetime.now()


def _fmt(t):
    return t.strftime("%Y-%m-%d %H:%M:%S")


def ensure(c):
    c.execute("""CREATE TABLE IF NOT EXISTS mail_import_tokens(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token_hash TEXT NOT NULL UNIQUE,
        years INTEGER NOT NULL,
        mode TEXT NOT NULL,
        since TEXT NOT NULL,
        created_at TEXT NOT NULL,
        state TEXT DEFAULT 'ready',
        saved INTEGER DEFAULT 0, skipped INTEGER DEFAULT 0, failed INTEGER DEFAULT 0, outside INTEGER DEFAULT 0,
        att_bytes INTEGER DEFAULT 0, att_dropped INTEGER DEFAULT 0,
        last_at TEXT DEFAULT '')""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_mimp_tok_user ON mail_import_tokens(user_id, id)")
    c.execute("""CREATE TABLE IF NOT EXISTS mail_import_items(
        mail_id INTEGER PRIMARY KEY, token_id INTEGER, user_id INTEGER)""")


def _hash(code):
    return hashlib.sha256(("knk-mimp:" + (code or "").strip()).encode("utf-8")).hexdigest()


def is_owner(c, uid):
    from .mail_folders import _owner_id
    return bool(uid) and _owner_id(c) == uid


def modes_for(c, uid):
    return (OWNER_MODE,) if is_owner(c, uid) else STAFF_MODES


def create_token(c, uid, years, mode):
    """번호 만들기 — 대표 계정은 폴더 방식이 match 로 고정(다른 값을 보내도). 직원은 match 를 쓸 수 없음.
    반환 (번호 평문 — 화면에 한 번만, 행 정보). 같은 사람의 앞 번호는 끝냄."""
    ensure(c)
    try:
        years = int(years)
    except Exception:
        years = 0
    if years not in YEARS:
        raise ValueError("기간은 5·3·2·1년 중에서 골라 주세요")
    if is_owner(c, uid):
        mode = OWNER_MODE
    elif mode not in STAFF_MODES:
        raise ValueError("폴더 방식을 골라 주세요")
    code = secrets.token_urlsafe(9).replace("-", "x").replace("_", "y")
    now = _now()
    try:
        since = now.replace(year=now.year - years)
    except ValueError:   # 2월 29일
        since = now.replace(year=now.year - years, day=28)
    c.execute("UPDATE mail_import_tokens SET state='ended' WHERE user_id=? AND state IN ('ready','running')", (uid,))
    cur = c.execute("INSERT INTO mail_import_tokens(user_id, token_hash, years, mode, since, created_at) VALUES(?,?,?,?,?,?)",
                    (uid, _hash(code), years, mode, since.strftime("%Y-%m-%d") + " 00:00:00", _fmt(now)))
    return code, get_token(c, cur.lastrowid)


def get_token(c, tid):
    r = c.execute("SELECT * FROM mail_import_tokens WHERE id=?", (tid,)).fetchone()
    return dict(r) if r else None


def latest(c, uid):
    ensure(c)
    r = c.execute("SELECT * FROM mail_import_tokens WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)).fetchone()
    return dict(r) if r else None


def _alive(t, now=None):
    if not t or t.get("state") not in ("ready", "running"):
        return False
    now = now or _now()
    try:
        made = _dt.datetime.strptime(t["created_at"][:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return False
    if now <= made + _dt.timedelta(hours=TOKEN_HOURS):
        return True
    try:
        last = _dt.datetime.strptime((t.get("last_at") or "")[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return False
    return now <= last + _dt.timedelta(hours=TOKEN_IDLE_HOURS) and now <= made + _dt.timedelta(hours=TOKEN_MAX_HOURS)


def find_token(c, code):
    """번호 → 살아 있는 행(없거나 끝났거나 기한 지남 = None)."""
    ensure(c)
    if not code or len(code) > 64:
        return None
    r = c.execute("SELECT * FROM mail_import_tokens WHERE token_hash=?", (_hash(code),)).fetchone()
    t = dict(r) if r else None
    return t if _alive(t) else None


def stop(c, uid):
    ensure(c)
    return c.execute("UPDATE mail_import_tokens SET state='stopped' WHERE user_id=? AND state IN ('ready','running')",
                     (uid,)).rowcount


def disk_state(path=None):
    """{"free": 바이트, "total": 바이트, "ok": 받을 수 있나}."""
    if not path:
        from .database import DB_PATH
        path = os.path.dirname(DB_PATH)
    try:
        du = shutil.disk_usage(path)
        ok = du.free >= DISK_MIN_FREE and (du.total <= 0 or du.free / float(du.total) >= DISK_MIN_RATIO)
        return {"free": du.free, "total": du.total, "ok": bool(ok)}
    except Exception:
        return {"free": 0, "total": 0, "ok": True}


# ─── 폴더 ───────────────────────────────────────────────────────
def norm_name(s):
    """「1고객사」=「1.고객사」 · 「01_기술영업팀」=「01 기술영업팀」 — 빈칸·점·밑줄·줄표·괄호 빼고 소문자."""
    return re.sub(r"[\s._\-()\[\]·]+", "", (s or "")).lower()


def path_parts(path):
    """아웃룩 폴더 경로 → 「받은 편지함」 아래 이름들. 예) \\\\a@b\\받은 편지함\\1고객사\\시노펙스 → [1고객사, 시노펙스]."""
    ps = [p.strip() for p in re.split(r"[\\/]+", path or "") if p.strip()]
    for i, p in enumerate(ps):
        if norm_name(p) in _INBOX_NAMES:
            return ps[i + 1:]
    # 받은 편지함이 없으면 메일함 이름(주소)만 떼고 나머지
    if ps and "@" in ps[0]:
        ps = ps[1:]
    return ps


def name_map(c, uid):
    """이음웍스 폴더 이름(정규화) → 고정 키 목록. 폴더 = f<id>(직원 묶음 맨 위 제외) · 부서 폴더 = t<id>(사람이 바꾼 이름 포함)."""
    from . import mail_folders as MF
    MF.ensure(c)
    m = {}

    def add(nm, key):
        k = norm_name(nm)
        if k:
            m.setdefault(k, [])
            if key not in m[k]:
                m[k].append(key)
    fl = MF.folders(c, uid)
    staff_top = [f for f in fl if not f["parent_id"] and f["kind"] == "staff"]
    for f in fl:
        if not f["parent_id"] and f["kind"] == "staff":
            continue
        add(f["name"], "f%d" % f["id"])
    if staff_top:
        tp = MF.team_prefs(c, uid)
        for t in MF.teams(c):
            pr = tp.get("t%d" % t["id"], {})
            if pr.get("merge"):
                continue
            add(pr.get("name") or MF.folder_team_label(t), "t%d" % t["id"])
            add(MF.folder_team_label(t), "t%d" % t["id"])
    return m


def _folder_for_path(c, uid, parts):
    """outlook 방식 — 경로대로 메일 폴더를 찾거나 만든다(3단계까지 · 더 깊으면 셋째 단계에 모음). 반환 키 또는 ''."""
    from . import mail_folders as MF
    if not parts:
        return ""
    parts = parts[:3]
    parent = None
    key = ""
    for depth, nm in enumerate(parts):
        rows = c.execute("SELECT id, name, kind FROM mail_folders WHERE user_id=? AND "
                         + ("parent_id=?" if parent else "parent_id IS NULL"),
                         ((uid, parent) if parent else (uid,))).fetchall()
        hit = [r for r in rows if norm_name(r["name"]) == norm_name(nm)]
        if hit:
            fid = hit[0]["id"]
            if depth == 0 and hit[0]["kind"] == "staff":
                # 회사 부서 묶음 — 아래는 부서 폴더(t<id>)라 만들 수 없음 → 남은 이름으로 부서 폴더를 찾음(하나만)
                m = name_map(c, uid)
                for nm2 in reversed(parts[1:]):
                    ks = [k for k in m.get(norm_name(nm2), []) if k.startswith("t")]
                    if len(ks) == 1:
                        return ks[0]
                return ""
        else:
            fid = MF.add_folder(c, uid, nm, parent, "")
            if not fid:
                break
        parent, key = fid, "f%d" % fid
    return key


def folder_key(c, uid, mode, path):
    """메일 한 통의 고정 키 — '' = 고정 안 함(자동 분류)."""
    if mode == "auto":
        return ""
    if mode == "manual":
        return "gen"
    parts = path_parts(path)
    if mode == "outlook":
        return _folder_for_path(c, uid, parts)
    if mode == "match":
        if not parts:
            return "gen"
        ks = name_map(c, uid).get(norm_name(parts[-1]), [])
        return ks[0] if len(ks) == 1 else "gen"
    return ""


# ─── 메일 한 통 ─────────────────────────────────────────────────
def _parse_time(s):
    s = (s or "").strip().replace("T", " ")[:19]
    for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return _dt.datetime.strptime(s, f)
        except Exception:
            continue
    return None


def _addr(a):
    a = (a or "").strip().strip("<>").strip()
    return a.lower() if ("@" in a and len(a) <= 254 and not any(ch in a for ch in " \t\r\n,;")) else ""


def take_mail(c, t, d):
    """한 통 저장. 반환 결과 글자 하나: saved | skip | outside | fail · 그리고 첨부 바이트·뺀 첨부 수."""
    from . import mail_store as MS
    uid = t["user_id"]
    rt = _parse_time(d.get("received_at"))
    if not rt:
        return "fail", 0, 0
    since = _parse_time(t["since"])
    if since and rt < since:
        return "outside", 0, 0
    if rt > _now() + _dt.timedelta(days=1):
        return "fail", 0, 0
    mid = str(d.get("message_id") or "").strip().strip("<>").strip()[:500]
    frm = _addr(d.get("from_email"))
    subject = str(d.get("subject") or "")[:1000]
    html = str(d.get("html") or "")
    text = str(d.get("text") or "")
    body = text.strip() or MS._html_to_text(html)
    MS._ensure_dedup_cols(c)
    h = MS._dedup_hash(mid, frm, (subject or "(제목 없음)").strip(), body)
    if c.execute("SELECT 1 FROM mail_messages WHERE user_id=? AND dedup_hash=? LIMIT 1", (uid, h)).fetchone():
        return "skip", 0, 0
    atts, total, dropped = [], 0, 0
    raw_atts = d.get("attachments") or []
    for a in raw_atts:
        try:
            data = base64.b64decode(a.get("b64") or "", validate=False)
        except Exception:
            data = b""
        total += len(data)
        atts.append({"filename": str(a.get("name") or "첨부")[:200], "mime": str(a.get("mime") or "application/octet-stream")[:120],
                     "size": len(data), "content_id": str(a.get("content_id") or "").strip("<>")[:200],
                     "inline": bool(a.get("inline")), "data": data})
    try:
        dropped = int(d.get("att_dropped") or 0)
    except Exception:
        dropped = 0
    if total > MAX_MAIL_BYTES:
        dropped += len(atts)
        atts, total = [], 0
    if dropped:
        note = ('<div style="border:1px solid #f3c27a;background:#fff7e6;color:#7a4a05;border-radius:8px;padding:8px 10px;'
                'margin:0 0 10px;font-size:13px">📎 첨부 %d개는 너무 커서(한 통 30MB 넘음) 가져오지 않았습니다 — 예전 아웃룩에 있습니다.</div>' % dropped)
        html = note + (html or ("<pre>%s</pre>" % (text.replace("&", "&amp;").replace("<", "&lt;"))))
    to_all = str(d.get("to") or "")[:4000]
    to1 = _addr((to_all.split(",")[0] if to_all else "")) or ""
    sent = _parse_time(d.get("sent_at"))
    max_before = c.execute("SELECT COALESCE(MAX(id),0) FROM mail_messages").fetchone()[0] or 0
    mail_id, _own = MS.store_inbound(
        c, to_email=to1 or "import@knknara.co.kr", from_email=frm, from_name=str(d.get("from_name") or "")[:200],
        subject=subject, text=text, html=html, cc=str(d.get("cc") or "")[:4000], size=len(html) + len(text) + total,
        owner_id=uid, run_ai=False, attachments=atts or None, message_id=mid,
        raw_headers=str(d.get("transport_headers") or "")[:64 * 1024], to_all=to_all,
        sent_at=_fmt(sent) if sent else "")
    if not mail_id:
        return "fail", 0, 0
    if mail_id <= max_before:   # 이미 있던 같은 메일(store_inbound 가 기존 번호를 돌려줌) — 건드리지 않음
        return "skip", 0, 0
    c.execute("UPDATE mail_messages SET received_at=?, is_read=1 WHERE id=? AND user_id=?", (_fmt(rt), mail_id, uid))
    key = folder_key(c, uid, t["mode"], d.get("folder_path") or "")
    if key:
        c.execute("UPDATE mail_messages SET fd_pin=? WHERE id=? AND user_id=?", (key, mail_id, uid))
    c.execute("INSERT OR IGNORE INTO mail_import_items(mail_id, token_id, user_id) VALUES(?,?,?)", (mail_id, t["id"], uid))
    return "saved", total, dropped


def finish(c, t):
    """PC 명령이 끝까지 돌았음 — 번호도 함께 끝냄(다시 하려면 새 번호 · 같은 메일은 어차피 건너뜀)."""
    c.execute("UPDATE mail_import_tokens SET state='done', last_at=? WHERE id=?", (_fmt(_now()), t["id"]))


def count_result(c, t, res, att_bytes=0, dropped=0):
    col = {"saved": "saved", "skip": "skipped", "outside": "outside", "fail": "failed"}.get(res, "failed")
    c.execute("UPDATE mail_import_tokens SET %s=%s+1, att_bytes=att_bytes+?, att_dropped=att_dropped+?, "
              "state='running', last_at=? WHERE id=?" % (col, col), (int(att_bytes or 0), int(dropped or 0), _fmt(_now()), t["id"]))


def public(t, disk=None):
    """화면·명령에 돌려줄 숫자(번호·주소·제목 없음)."""
    if not t:
        return {}
    return {"years": t["years"], "mode": t["mode"], "mode_name": MODE_NAME.get(t["mode"], ""), "since": (t["since"] or "")[:10],
            "state": t["state"], "alive": _alive(t), "created_at": t["created_at"], "last_at": t.get("last_at") or "",
            "saved": t["saved"], "skipped": t["skipped"], "failed": t["failed"], "outside": t["outside"],
            "att_mb": round((t["att_bytes"] or 0) / 1048576.0, 1), "att_dropped": t["att_dropped"],
            "disk_ok": (disk or {}).get("ok", True), "free_gb": round(((disk or {}).get("free") or 0) / 1073741824.0, 1)}
