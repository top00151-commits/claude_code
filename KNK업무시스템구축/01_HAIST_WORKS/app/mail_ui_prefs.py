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


# ── 11-23 대표 「🏷 종류(견적·발주·세금계산서)를 내가 지정해서 보고 싶어 · 고치는 메뉴를 팝업에서 바로」 ──
#   prefs["kinds"] = 순서대로 [{id, b(기본 이름) | n(내 이름)·w(찾을 낱말)·i(그림), on(보이기)}]
#   기본 셋(견적·발주·세금계산서) = AI 분류 + 제목 낱말(mail_store.KIND_WORDS) · 숨기기·순서만
#   내 종류 = 제목·보낸 사람(이름·주소)에 낱말 중 하나라도 들어간 받은 메일
BUILTIN_KINDS = (("견적", "💲"), ("발주", "🛒"), ("세금계산서", "🧾"))
# 그림 = 메일 화면 선 아이콘(mail_design_v2 MAP)에 있는 것만 — 새 디자인에서 모양이 섞이지 않게
KIND_ICONS = ("🏷", "🛠", "🚚", "📦", "📋", "📝", "📅", "⭐", "📌", "💬", "🏢", "👤", "📊", "💡", "⚠", "🔔", "📎", "✅")
KIND_SUGGEST = (
    ("제작요청", "🛠", ("제작 요청", "제작요청", "제작 진행", "제작진행")),
    ("구매", "📦", ("구매", "구입", "purchase")),
    ("가공", "🛠", ("가공", "machining")),
    ("납품·출하", "🚚", ("납품", "출하", "delivery")),
    ("성적서", "📋", ("성적서", "검사성적", "inspection report")),
    ("샘플", "📌", ("샘플", "견본", "sample")),
    ("도면", "📝", ("도면", "drawing")),
)
MAX_CUSTOM = 15


def default_kinds():
    return [{"id": "b:" + n, "b": n, "i": ic, "on": 1} for n, ic in BUILTIN_KINDS]


def _words(v):
    if isinstance(v, str):
        v = v.replace("\n", ",").replace("·", ",").split(",")
    if not isinstance(v, (list, tuple)):
        return []
    out, seen = [], set()
    for w in v:
        w = str(w or "").strip().replace("%", "").replace("_", " ").strip()[:40]
        if w and w.lower() not in seen:
            seen.add(w.lower())
            out.append(w)
    return out[:20]


def clean_kinds(lst):
    """받은 목록 거르기 — 기본 셋은 숨기기·순서만 · 내 종류는 이름(20자)·낱말(20개)·그림(정해진 것) · 빠진 기본은 끝에 「숨김」으로."""
    import re as _re
    bmap = dict(BUILTIN_KINDS)
    out, seen, used = [], set(), set()
    if not isinstance(lst, (list, tuple)):
        lst = []
    for x in list(lst)[:40]:
        if isinstance(x, dict):
            kid = str(x.get("id") or "")
            if _re.fullmatch(r"u\d{1,6}", kid):
                used.add(int(kid[1:]))
    nxt = (max(used) + 1) if used else 1
    ncus = 0
    for x in list(lst)[:40]:
        if not isinstance(x, dict):
            continue
        on = 1 if x.get("on") in (1, True, "1", "true", "on") else 0
        b = x.get("b")
        if b in bmap:
            if "b:" + b in seen:
                continue
            seen.add("b:" + b)
            out.append({"id": "b:" + b, "b": b, "i": bmap[b], "on": on})
            continue
        name = str(x.get("n") or "").strip()[:20]
        words = _words(x.get("w"))
        if not name or not words or ncus >= MAX_CUSTOM:
            continue
        kid = str(x.get("id") or "")
        if not _re.fullmatch(r"u\d{1,6}", kid) or kid in seen:
            kid = "u%d" % nxt
            nxt += 1
        seen.add(kid)
        ic = str(x.get("i") or "")
        if ic not in KIND_ICONS:
            ic = "🏷"
        out.append({"id": kid, "n": name, "w": words, "i": ic, "on": on})
        ncus += 1
    for n, ic in BUILTIN_KINDS:
        if "b:" + n not in seen:
            out.append({"id": "b:" + n, "b": n, "i": ic, "on": 0})
    return out


def _load(c, user_id):
    ensure(c)
    r = c.execute("SELECT prefs FROM mail_ui_prefs WHERE user_id=?", (int(user_id),)).fetchone()
    try:
        d = json.loads(r[0]) if r and r[0] else {}
    except Exception:
        d = {}
    return d if isinstance(d, dict) else {}


def get_kinds(c, user_id):
    """내 종류 목록(순서대로 · 숨긴 것 포함). 고른 적 없으면 기본 셋."""
    if not user_id:
        return default_kinds()
    k = _load(c, user_id).get("kinds")
    return clean_kinds(k) if isinstance(k, list) and k else default_kinds()


def save_kinds(c, user_id, lst):
    d = _load(c, user_id)
    d["kinds"] = clean_kinds(lst)
    c.execute("INSERT INTO mail_ui_prefs(user_id, prefs, updated_at) VALUES(?,?,datetime('now','localtime')) "
              "ON CONFLICT(user_id) DO UPDATE SET prefs=excluded.prefs, updated_at=excluded.updated_at",
              (int(user_id), json.dumps(d, ensure_ascii=False)))
    return d["kinds"]


# ── 11-23 대표 「"광고·알림" 은 어떻게 지정? 내가 할 수 있는 거야?」 ──
#   자동 판단(mail_cleanup.judge: 제목 (광고) · 수신거부 안내 · 답장 안 받는 자동 주소 · 주소록·보낸 적 있으면 빼기) 위에
#   내가 보낸 사람(주소)마다 덮어씀 — prefs["ad"] = {"on": [주소], "off": [주소]} · 사람마다
AD_MAX = 1000


def _addr(a):
    a = str(a or "").strip().lower()
    return a if ("@" in a and len(a) <= 200 and " " not in a) else ""


def _since(v):
    """'YYYY-MM-DD' 또는 'YYYY-MM-DD HH:MM:SS' 만 · 그 밖 = ''."""
    import re as _re
    v = str(v or "").strip()
    if _re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return v + " 00:00:00"
    return v if _re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", v) else ""


def get_ad_marks(c, user_id):
    """(광고·알림으로 표시한 주소, 광고·알림 아님으로 표시한 주소). 날짜부터 표시한 주소도 「표시」에 듦."""
    on, off, since = get_ad_marks3(c, user_id)
    return on | set(since), off


def get_ad_marks3(c, user_id):
    """(지난 메일도 모두 광고·알림, 아님, {주소: 그때 받은 메일부터 광고·알림})."""
    if not user_id:
        return set(), set(), {}
    d = _load(c, user_id).get("ad") or {}
    if not isinstance(d, dict):
        return set(), set(), {}
    off = {x for x in (_addr(a) for a in (d.get("off") or [])) if x}
    on = {x for x in (_addr(a) for a in (d.get("on") or [])) if x} - off
    sm = d.get("since") if isinstance(d.get("since"), dict) else {}
    since = {}
    for k, v in sm.items():
        a, s = _addr(k), _since(v)
        if a and s and a not in off and a not in on:
            since[a] = s
    return on, off, since


def set_ad_mark(c, user_id, addr, mode, since=""):
    """mode: 'on' = 광고·알림으로(since 가 있으면 그때 받은 메일부터 · 없으면 지난 메일도 모두) · 'off' = 아님 · '' = 자동 판단으로.
    반환 지금 표시('on'|'off'|'') · 주소가 이상하면 None."""
    a = _addr(addr)
    if not a:
        return None
    d = _load(c, user_id)
    m = d.get("ad") if isinstance(d.get("ad"), dict) else {}
    on = [x for x in (m.get("on") or []) if _addr(x) and _addr(x) != a]
    off = [x for x in (m.get("off") or []) if _addr(x) and _addr(x) != a]
    sm = {k: v for k, v in (m.get("since") or {}).items() if _addr(k) and _addr(k) != a} if isinstance(m.get("since"), dict) else {}
    s = _since(since)
    if mode == "on" and s:
        sm[a] = s
    elif mode == "on":
        on.append(a)
    elif mode == "off":
        off.append(a)
    if len(sm) > AD_MAX:
        sm = dict(list(sm.items())[-AD_MAX:])
    d["ad"] = {"on": on[-AD_MAX:], "off": off[-AD_MAX:], "since": sm}
    c.execute("INSERT INTO mail_ui_prefs(user_id, prefs, updated_at) VALUES(?,?,datetime('now','localtime')) "
              "ON CONFLICT(user_id) DO UPDATE SET prefs=excluded.prefs, updated_at=excluded.updated_at",
              (int(user_id), json.dumps(d, ensure_ascii=False)))
    return mode if mode in ("on", "off") else ""


# ── 11-23 대표 「전체·안 읽음·첨부 … 줄에서 선택해 놓은 게 분류하면서 옮기다 보면 자꾸 풀려 — 내가 풀 때까지 선택돼 있게」 ──
#   거르기 줄 상태를 내 계정에 기억 — 받은편지함 주소에 직접 적힌 값이 먼저 · 없으면 이 값으로 채움
CHIP_DEFAULT = {"unread": 0, "att": 0, "noad": 0, "thread": 1, "cat": "", "kd": ""}


def clean_chips(d):
    import re as _re
    d = d if isinstance(d, dict) else {}
    out = dict(CHIP_DEFAULT)
    for k in ("unread", "att", "noad", "thread"):
        try:
            out[k] = 1 if int(d.get(k, CHIP_DEFAULT[k]) or 0) else 0
        except Exception:
            pass
    cat = str(d.get("cat") or "")
    out["cat"] = cat if cat in dict(BUILTIN_KINDS) else ""
    kd = str(d.get("kd") or "")
    out["kd"] = kd if _re.fullmatch(r"u\d{1,6}", kd) else ""
    if out["kd"]:
        out["cat"] = ""
    return out


def get_chips(c, user_id):
    """기억한 거르기 줄 상태 — 한 번도 안 바꿨으면 None."""
    if not user_id:
        return None
    v = _load(c, user_id).get("chips")
    return clean_chips(v) if isinstance(v, dict) else None


def save_chips(c, user_id, d):
    new = clean_chips(d)
    cur = _load(c, user_id)
    if cur.get("chips") == new:
        return new
    cur["chips"] = new
    c.execute("INSERT INTO mail_ui_prefs(user_id, prefs, updated_at) VALUES(?,?,datetime('now','localtime')) "
              "ON CONFLICT(user_id) DO UPDATE SET prefs=excluded.prefs, updated_at=excluded.updated_at",
              (int(user_id), json.dumps(cur, ensure_ascii=False)))
    return new
