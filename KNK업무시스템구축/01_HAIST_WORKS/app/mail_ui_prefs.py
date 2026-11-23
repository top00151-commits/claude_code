# -*- coding: utf-8 -*-
"""메일 화면 설정을 서버에도 기억 (11-23 대표 「조정한 글자 사이즈는 꼭 기억 — 업데이트·새로고침해도 초기값으로 돌리지 말고 가장 최근 설정값으로」)

- 지금 담는 것: 글자 크기(칸별 · 읽기 칸 보기 자리별) — 브라우저 저장(localStorage)과 같은 열쇠 이름
- 브라우저 저장이 지워져도(캐시 비우기·앱 다시 설치·다른 컴퓨터) 서버 값으로 되살림
- 「가장 최근」 = 바꾼 시각(t · ms)이 더 늦은 쪽이 이김(이 컴퓨터 ↔ 서버)
- 사람마다 한 줄(user_id) · 정해진 열쇠·값(−3~4)만 받음 — 다른 값은 버림
"""
import json

FS_KEYS = ("knkmail.fs", "knkmail.fs.side", "knkmail.fs.list",
           "knkmail.fs.read.right", "knkmail.fs.read.bottom", "knkmail.fs.read.list", "knkmail.fs.read.page")
_OK = set()


def ensure(c):
    try:
        k = c.execute("PRAGMA database_list").fetchone()[2] or ""
    except Exception:
        k = ""
    if k and k in _OK:
        return
    c.execute("CREATE TABLE IF NOT EXISTS mail_ui_prefs(user_id INTEGER PRIMARY KEY, prefs TEXT NOT NULL DEFAULT '{}', "
              "updated_at TEXT DEFAULT (datetime('now','localtime')))")
    if k:
        _OK.add(k)


def clean_fs(d):
    """받은 값 거르기 — 정해진 열쇠 · 정수 −3~4 · 바꾼 시각 t(ms) 만."""
    out = {}
    if not isinstance(d, dict):
        return out
    for k in FS_KEYS:
        v = d.get(k)
        if v is None or v == "":
            continue
        try:
            n = int(str(v).strip())
        except Exception:
            continue
        if -3 <= n <= 4:
            out[k] = n
    try:
        t = int(d.get("t") or 0)
    except Exception:
        t = 0
    out["t"] = max(0, t)
    return out


def get_fs(c, user_id):
    """서버에 기억한 글자 크기 — 없으면 None."""
    if not user_id:
        return None
    ensure(c)
    r = c.execute("SELECT prefs FROM mail_ui_prefs WHERE user_id=?", (int(user_id),)).fetchone()
    if not r:
        return None
    try:
        fs = (json.loads(r[0] or "{}") or {}).get("fs")
    except Exception:
        return None
    return clean_fs(fs) if isinstance(fs, dict) else None


def save_fs(c, user_id, d):
    """글자 크기 저장 — 서버 값보다 오래된(t 가 작은) 값은 덮어쓰지 않음(다른 컴퓨터에서 방금 바꾼 값 지키기).
    돌려줌: (저장했나, 지금 서버 값)."""
    ensure(c)
    new = clean_fs(d)
    cur = get_fs(c, user_id)
    if cur and int(cur.get("t") or 0) > int(new.get("t") or 0):
        return False, cur
    r = c.execute("SELECT prefs FROM mail_ui_prefs WHERE user_id=?", (int(user_id),)).fetchone()
    try:
        allp = json.loads(r[0]) if r and r[0] else {}
    except Exception:
        allp = {}
    if not isinstance(allp, dict):
        allp = {}
    allp["fs"] = new
    c.execute("INSERT INTO mail_ui_prefs(user_id, prefs, updated_at) VALUES(?,?,datetime('now','localtime')) "
              "ON CONFLICT(user_id) DO UPDATE SET prefs=excluded.prefs, updated_at=excluded.updated_at",
              (int(user_id), json.dumps(allp, ensure_ascii=False)))
    return True, new
