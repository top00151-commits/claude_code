# -*- coding: utf-8 -*-
"""👉 맡기기 — 메일 한 통을 이음(사내 메신저) **요청**으로 넘긴다(대표 2026-11-20 「맡기기는 (가)로, 원문은 복사로 진행해」).

  · 담당자·기한·독촉·결과 확인은 **이음 요청**이 맡는다 — 메일 쪽은 넘기기 + 상태 띠만.
  · 메일 원문은 **복사**해서 넘긴다(맡은 직원에게 메일함을 열어 주지 않음).
  · 이음 입구 계약서: 10_KNK_Messenger/작업기록/2026-11-20_0203_Eum_v988_메일맡기기_계약서.md
      ① POST {이음}/api/requests/from-mail          (요청 만들기)
      ② POST {이음}/api/requests/from-mail/status   (ref 로 상태 읽기 · 한 번에 100개까지)
  · 부르는 곳 = **웍스 서버에서만**. 공유키(X-SSO-Service-Key) 값은 화면·로그·응답 어디에도 내보내지 않는다.

⛔ 철칙: 김정락(대표)–안지연(사번 67) 이음 1:1 방은 어떤 경우에도 대상이 아니다.
   이 기능은 이음이 만드는 「📧 메일 업무」 그룹 방만 쓰며(이음 계약 2-4: 1:1 방·내 메모는 절대 쓰지 않음),
   메일 쪽은 이음 대화방·메시지를 **읽지 않는다** — 받는 것은 요청 번호·ref·주소·상태·담당자 이름뿐.
⛔ 메일 본문은 이음 말고 다른 AI·번역·외부 서비스로 보내지 않는다.
"""
import json
import re
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

import httpx

from . import sso_client as _sso   # 이음 주소·공유키 — 다른 세션(01) 파일이라 읽기만(import)

# ── 🧪 시험 동안 맡기는 사람(대표 2026-11-20 「3번 막아」) — 김정락(5)·안지연(67)·이새롬(306) ──
#    대표 「풀어」 때 **이 한 줄만** 바꾸면 단추·서버 둘 다 풀린다(None = 전 직원).  이음도 같은 명단으로 막는다(계약 5-10).
TEST_GROUP = ("5", "67", "306")

MAX_ASSIGNEES = 20
MAX_INSTR = 200
MAX_FILES = 10
MAX_TOTAL = 50 * 1024 * 1024          # 첨부 합계 50MB(이음 한도 · 몸통 52MB 넘으면 이음이 끊을 수 있음)
BODY_MAX = 20000                       # 본문 글자 2만 자(이음과 같은 규칙으로 미리 자름)
BODY_CUT_MARK = "…(이하 생략)"
CREATE_TIMEOUT = 90.0                  # 첨부 50MB 를 내부망으로 올리는 시간까지
STATUS_TIMEOUT = 6.0
STATUS_CACHE_SEC = 60                  # 상태는 1분에 한 번 이하로만 묻는다(계약 5-2)
RESULT_KINDS = ("reply", "file", "check")
RESULT_LABEL = {"reply": "답변", "file": "파일", "check": "처리 확인"}

# 상태 값 → 띠에 붙는 표시(계약 3-3)
STATE_MARK = {"working": "", "review": "📬 확인 대기", "done": "✓ 처리 끝", "closed": "종료",
              "declined": "⛔ 거절", "cancelled": "취소", "gone": ""}

# 이음 오류(계약 2-6) → 사람말
ERR_KO = {
    "forbidden": "이음이 연결 키를 받지 않았습니다(관리자 확인 필요).",
    "bad_payload": "보낸 내용을 이음이 읽지 못했습니다(전산 확인 필요).",
    "requester_invalid": "내 계정(사번)이 이음에서 켜진 직원이 아닙니다 — 전산 담당자에게 확인해 주세요.",
    "not_in_test_group": "🧪 시험 기간이라 맡기기는 김정락·안지연·이새롬만 쓸 수 있습니다.",
    "assignees_required": "담당자를 한 명 이상 골라 주세요.",
    "too_many_assignees": "담당자는 %d명까지 고를 수 있습니다." % MAX_ASSIGNEES,
    "assignee_invalid": "손님·잠긴 계정에는 맡길 수 없습니다",
    "instruction_too_long": "한 줄 지시는 %d자까지입니다." % MAX_INSTR,
    "bad_due": "기한 날짜가 올바르지 않습니다 — 달력에서 다시 골라 주세요.",
    "mail_required": "메일 내용을 넘기지 못했습니다(전산 확인 필요).",
    "too_many_files": "첨부가 너무 많아 이음이 받지 않았습니다(%d개까지) — 「첨부 함께 보내기」를 끄고 맡겨 주세요." % MAX_FILES,
    "files_too_large": "첨부가 너무 커서 이음이 받지 않았습니다(합계 50MB까지) — 「첨부 함께 보내기」를 끄고 맡겨 주세요.",
    "bad_file": "첨부 파일을 이음이 읽지 못했습니다 — 「첨부 함께 보내기」를 끄고 맡겨 보세요.",
    "rate_limited": "짧은 시간에 너무 많이 맡겼습니다. 1분쯤 뒤에 다시 눌러 주세요.",
    "bad_refs": "상태를 묻는 열쇠 꼴이 틀렸습니다(전산 확인 필요).",
}

_OK = set()


def _dbkey(c):
    try:
        return c.execute("PRAGMA database_list").fetchone()[2] or ("mem:%x" % id(c))
    except Exception:
        return "?"


def ensure(c):
    """맡김 기록 표(만들기만 · 기존 자료는 건드리지 않음)."""
    k = _dbkey(c)
    if k in _OK:
        return
    c.execute("""CREATE TABLE IF NOT EXISTS mail_delegations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mail_id INTEGER NOT NULL,
        owner_id INTEGER NOT NULL,              -- 맡긴 사람(웍스 users.id)
        ref TEXT NOT NULL,                      -- 이음 열쇠(32자) — 상태는 이것으로만 묻는다
        request_no INTEGER,
        win_url TEXT DEFAULT '', url TEXT DEFAULT '', room_name TEXT DEFAULT '',
        assignees TEXT DEFAULT '[]',            -- [{"employee_no":"…","name":"…"}] (이름은 상태 응답으로 새로 고침)
        due TEXT DEFAULT '', instruction TEXT DEFAULT '', result_kind TEXT DEFAULT 'reply',
        state TEXT DEFAULT 'working', label TEXT DEFAULT '', state_at TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now','localtime')))""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_maildlg_mail ON mail_delegations(owner_id, mail_id)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_maildlg_ref ON mail_delegations(ref)")
    _OK.add(k)


# ═══════════════════════ 누가 쓰나 ═══════════════════════
def emp_no(u) -> str:
    """로그인한 사람의 사번(users.employee_no). 사번이 없는 계정은 '' → 맡길 수 없음."""
    try:
        return str((u or {}).get("employee_no") or "").strip()
    except Exception:
        return ""


def allowed(u) -> bool:
    """「👉 맡기기」 단추·서버 입구를 쓸 수 있는 사람 — 🧪 시험 명단(TEST_GROUP) 한 곳에서만 정한다."""
    e = emp_no(u)
    if not e:
        return False
    return True if TEST_GROUP is None else (e in TEST_GROUP)


def _is_system(e) -> bool:
    e = str(e or "").strip().lower()
    return (not e) or e.startswith("zz") or e.startswith("_")


def _has_empno(c) -> bool:
    try:
        return any(r[1] == "employee_no" for r in c.execute("PRAGMA table_info(users)").fetchall())
    except Exception:
        return False


def staff_search(c, q="", limit=30):
    """담당자 고르기 — 웍스 직원 명단 읽기만(켜진 계정 · 사번 있음 · 봇 아님). 이름·부서·직책·사번·메일로 찾기."""
    if not _has_empno(c):
        return []
    q = (q or "").strip().lower()
    rows = c.execute(
        "SELECT u.id, u.name, COALESCE(u.rank,'') AS rank, COALESCE(u.email,'') AS email, TRIM(u.employee_no) AS employee_no, "
        "COALESCE(t.name,'') AS team_name, COALESCE(t.display_order, 999) AS tord "
        "FROM users u LEFT JOIN teams t ON t.id=u.team_id "
        "WHERE u.is_active=1 AND u.employee_no IS NOT NULL AND TRIM(u.employee_no)<>'' "
        "ORDER BY tord, t.name, u.name").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        if _is_system(d["employee_no"]):
            continue
        if q:
            hay = " ".join([d["name"] or "", d["rank"], d["team_name"], d["email"], d["employee_no"]]).lower()
            if not all(w in hay for w in q.split()):
                continue
        out.append(d)
        if len(out) >= limit:
            break
    return out


def staff_by_empno(c, emps, active_only=True):
    """사번 → {name, rank, team_name} (기본 = 켜진 계정만 · active_only=False 면 꺼진 사람 이름도 — 오류 안내용)."""
    out = {}
    emps = [str(e).strip() for e in (emps or []) if str(e).strip()][:100]
    if not emps or not _has_empno(c):
        return out
    q = ",".join("?" * len(emps))
    for r in c.execute(
            "SELECT u.id, u.name, COALESCE(u.rank,'') AS rank, TRIM(u.employee_no) AS employee_no, COALESCE(t.name,'') AS team_name "
            "FROM users u LEFT JOIN teams t ON t.id=u.team_id WHERE " + ("u.is_active=1 AND " if active_only else "") +
            "TRIM(u.employee_no) IN (%s) ORDER BY u.is_active" % q, emps).fetchall():
        out[r["employee_no"]] = dict(r)
    return out


# ═══════════════════════ 메일 → 넘길 글 ═══════════════════════
def html_to_text(html: str) -> str:
    """HTML → 글자(줄바꿈은 살림). 스크립트·스타일은 버림. 본문 속 명령·링크는 그냥 글자(데이터)일 뿐."""
    if not html:
        return ""
    import html as _h
    t = re.sub(r"(?is)<(script|style|head|title)[^>]*>.*?</\1>", " ", html)
    t = re.sub(r"(?is)<!--.*?-->", " ", t)
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</(p|div|tr|li|h[1-6]|blockquote|table|pre)\s*>", "\n", t)
    t = re.sub(r"(?i)<li[^>]*>", "· ", t)
    t = re.sub(r"(?i)</t[dh]\s*>", "\t", t)
    t = re.sub(r"(?s)<[^>]+>", "", t)
    t = _h.unescape(t).replace("\xa0", " ")
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r" ?\n ?", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def body_for(m) -> (str, bool):
    """넘길 본문 글자 → (글자, 잘렸나). 글자 본문(body_text) 먼저, 없으면 HTML 을 글자로. 2만 자 넘으면 자르고 「…(이하 생략)」."""
    t = (m.get("body_text") or "").strip()
    # 글자 본문이 없거나, HTML 만 온 메일이라 저장 때 한 줄로 뭉개진 글자면(mail_store._html_to_text) → HTML 을 줄바꿈 살려 다시 글자로
    if m.get("body_html") and (not t or "\n" not in t):
        t = html_to_text(m.get("body_html") or "") or t
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    if len(t) > BODY_MAX:
        return t[:BODY_MAX - len(BODY_CUT_MARK)].rstrip() + BODY_CUT_MARK, True
    return t, False


def received_iso(s) -> str:
    """메일 받은 시각(서버 DB 의 datetime('now','localtime') 글자) → 시간대를 붙인 ISO(계약 2-2)."""
    s = (s or "").strip()
    if not s:
        return ""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s[:19], fmt).astimezone().isoformat(timespec="seconds")
        except Exception:
            continue
    return s


def _addrs(s):
    try:
        from .mail_send import split_addr_list
        return [x.strip() for x in split_addr_list(s or "") if x.strip()]
    except Exception:
        return [x.strip() for x in re.split(r"[,;]", s or "") if x.strip()]


def file_atts(c, mail_id):
    """그 메일의 첨부(본문 그림 빼고) — 이름·크기만."""
    return [dict(r) for r in c.execute(
        "SELECT id, filename, COALESCE(size,0) AS size FROM mail_attachments WHERE mail_id=? AND COALESCE(is_inline,0)=0 ORDER BY id",
        (mail_id,)).fetchall()]


def att_limits(atts) -> dict:
    n = len(atts)
    total = sum(int(a.get("size") or 0) for a in atts)
    over = n > MAX_FILES or total > MAX_TOTAL
    why = ""
    if n > MAX_FILES:
        why = "첨부가 %d개라 한 번에 넘길 수 없습니다(%d개까지)" % (n, MAX_FILES)
    elif total > MAX_TOTAL:
        why = "첨부 합계가 %s라 한 번에 넘길 수 없습니다(50MB까지)" % mb(total)
    return {"n": n, "total": total, "total_txt": mb(total), "over": over, "why": why}


def mb(n) -> str:
    n = int(n or 0)
    if n >= 1024 * 1024:
        return "%.1fMB" % (n / 1024.0 / 1024.0)
    return "%dKB" % max(1, (n + 1023) // 1024) if n else "0KB"


_IDEM_RE = re.compile(r"^[A-Za-z0-9_.:-]{8,64}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def norm_assignees(raw):
    """'5, VN201 1102' 또는 목록 → 사번 목록(겹치면 한 번 · 순서 유지)."""
    if isinstance(raw, (list, tuple)):
        parts = [str(x) for x in raw]
    else:
        parts = re.split(r"[\s,;]+", str(raw or ""))
    out, seen = [], set()
    for p in parts:
        p = p.strip()
        if not p:
            continue
        key = p.upper()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def check_form(*, assignees, due, instruction, result_kind, today_local):
    """화면에서 막은 것을 서버에서도 한 번 더(사람말). → (ok, message)"""
    if not assignees:
        return False, ERR_KO["assignees_required"]
    if len(assignees) > MAX_ASSIGNEES:
        return False, ERR_KO["too_many_assignees"]
    if len(instruction or "") > MAX_INSTR:
        return False, ERR_KO["instruction_too_long"]
    if due:
        if not _DATE_RE.match(due):
            return False, ERR_KO["bad_due"]
        try:
            datetime.strptime(due, "%Y-%m-%d")
        except Exception:
            return False, ERR_KO["bad_due"]
        if today_local and due < today_local:
            return False, "기한이 이미 지난 날짜입니다 — 오늘이나 그 뒤로 골라 주세요."
    if result_kind not in RESULT_KINDS:
        return False, "받을 결과를 골라 주세요."
    return True, ""


def build_payload(*, requester, assignees, due, instruction, result_kind, idem_key, m):
    body, cut = body_for(m)
    instr = re.sub(r"\s+", " ", instruction or "").strip()[:MAX_INSTR]
    p = {
        "requester_employee_no": str(requester),
        "assignee_employee_nos": [str(a) for a in assignees],
        "instruction": instr,
        "result_kind": result_kind if result_kind in RESULT_KINDS else "reply",
        "idem_key": idem_key,
        "mail": {
            "subject": (m.get("subject") or "")[:300],
            "from_name": (m.get("from_name") or "")[:100],
            "from_addr": (m.get("from_email") or "")[:254],
            "received_at": received_iso(m.get("received_at")),
            "to": _addrs(m.get("to_all") or m.get("to_email") or ""),
            "cc": _addrs(m.get("cc") or ""),
            "body": body,
        },
    }
    if due:
        p["due"] = due
    return p, cut


def new_idem() -> str:
    return "mdlg-" + secrets.token_hex(12)


# ═══════════════════════ 이음 부르기(서버 → 서버) ═══════════════════════
def _base():
    return (getattr(_sso, "MESSENGER_INTERNAL_BASE", "") or "").rstrip("/")


def _err(code, message, **kw):
    d = {"ok": False, "code": code, "message": message}
    d.update(kw)
    return d


def _human_error(status, d):
    code = str((d or {}).get("error") or "")
    if status == 404 and not code:
        return _err("not_ready", "이음에 아직 맡기기 입구가 없습니다(이음 업데이트 전) — 잠시 뒤 다시 해 주세요.")
    if code in ERR_KO:
        extra = {}
        if code == "assignee_invalid":
            extra["bad"] = [str(x) for x in ((d or {}).get("bad") or [])][:MAX_ASSIGNEES]
        return _err(code, ERR_KO[code], **extra)
    if status == 403:
        return _err("forbidden", ERR_KO["forbidden"])
    if status == 429:
        return _err("rate_limited", ERR_KO["rate_limited"])
    msg = str((d or {}).get("message") or "").strip()[:200]
    return _err(code or "http_%d" % status, msg or ("이음 응답 오류(%d) — 잠시 뒤 다시 해 주세요." % status))


def call_create(payload, files=None, timeout=None):
    """요청 만들기. files = [(원래 이름, bytes, mime)] — 있으면 multipart(payload 글자 + files 여러 개), 없으면 JSON.
    반환: 이음 200 응답(ok True) 또는 {ok:False, code, message[, bad]}. 공유키 값은 어디에도 싣지 않는다."""
    timeout = CREATE_TIMEOUT if timeout is None else timeout
    key = _sso.get_service_key()
    if not key:
        return _err("no_key", "이음 연결 키가 설정되지 않았습니다(관리자 확인 필요).")
    base = _base()
    if not base:
        return _err("no_base", "이음 주소가 설정되지 않았습니다(관리자 확인 필요).")
    url = base + "/api/requests/from-mail"
    hdr = {"X-SSO-Service-Key": key}
    try:
        if files:
            mp = [("files", (fn or "attachment", data, mime or "application/octet-stream")) for fn, data, mime in files]
            r = httpx.post(url, headers=hdr, data={"payload": json.dumps(payload, ensure_ascii=False)}, files=mp, timeout=timeout)
        else:
            r = httpx.post(url, headers=hdr, json=payload, timeout=timeout)
    except httpx.TimeoutException:
        print("[MAIL-DLG] 이음 응답 시간 넘김(요청 만들기)", flush=True)
        return _err("timeout", "이음이 제때 답하지 않았습니다. 「맡기기」를 한 번 더 눌러 주세요(같은 요청이 두 번 생기지 않습니다).")
    except Exception as e:
        print("[MAIL-DLG] 이음 연결 실패: %s" % type(e).__name__, flush=True)
        return _err("conn", "이음에 연결하지 못했습니다. 잠시 뒤 「맡기기」를 다시 눌러 주세요(같은 요청이 두 번 생기지 않습니다).")
    try:
        d = r.json()
    except Exception:
        d = {}
    if not isinstance(d, dict):
        d = {}
    if r.status_code != 200 or not d.get("ok"):
        print("[MAIL-DLG] 이음 거절: %s %s" % (r.status_code, str(d.get("error") or "")[:40]), flush=True)
        return _human_error(r.status_code, d)
    ref = str(d.get("ref") or "")
    if not re.match(r"^[0-9a-f]{32}$", ref):
        return _err("bad_reply", "이음 응답에 요청 열쇠가 없습니다(이음 확인 필요).")
    return d


_CACHE = {}            # ref → (시각, item)
_CACHE_LOCK = threading.Lock()


def call_status(refs, timeout=None, max_age=None, now=None):
    """ref 로 상태 읽기 — 1분 안에 물은 것은 다시 묻지 않음 · 100개씩 모아 묻기.
    반환: ({ref: item}, 오류 사람말 또는 '')."""
    now = time.time() if now is None else now
    timeout = STATUS_TIMEOUT if timeout is None else timeout
    max_age = STATUS_CACHE_SEC if max_age is None else max_age
    refs = [r for r in dict.fromkeys(str(x) for x in (refs or [])) if re.match(r"^[0-9a-f]{32}$", r)]
    out, need = {}, []
    with _CACHE_LOCK:
        for r in refs:
            hit = _CACHE.get(r)
            if hit and now - hit[0] < max_age:
                out[r] = hit[1]
            else:
                need.append(r)
    if not need:
        return out, ""
    key = _sso.get_service_key()
    if not key:
        return out, "이음 연결 키가 설정되지 않았습니다(관리자 확인 필요)."
    url = _base() + "/api/requests/from-mail/status"
    err = ""
    for i in range(0, len(need), 100):
        part = need[i:i + 100]
        try:
            r = httpx.post(url, headers={"X-SSO-Service-Key": key}, json={"refs": part}, timeout=timeout)
        except Exception as e:
            print("[MAIL-DLG] 상태 읽기 연결 실패: %s" % type(e).__name__, flush=True)
            err = "이음에 연결하지 못해 지금 상태를 못 읽었습니다."
            break
        try:
            d = r.json()
        except Exception:
            d = {}
        if r.status_code != 200 or not isinstance(d, dict) or not d.get("ok"):
            h = _human_error(r.status_code, d if isinstance(d, dict) else {})
            err = "지금 상태를 못 읽었습니다 — " + h["message"]
            break
        with _CACHE_LOCK:
            for it in (d.get("items") or []):
                if isinstance(it, dict) and it.get("ref") in part:
                    out[it["ref"]] = it
                    _CACHE[it["ref"]] = (now, it)
    return out, err


def cache_clear():
    with _CACHE_LOCK:
        _CACHE.clear()


# ═══════════════════════ 저장·읽기 ═══════════════════════
def save(c, *, mail_id, owner_id, resp, assignees, instruction, result_kind):
    """이음이 만든 요청을 기록(같은 ref 는 한 번만 — 다시 보내 받은 existing 응답이면 그대로 둠)."""
    ensure(c)
    ref = resp["ref"]
    if c.execute("SELECT id FROM mail_delegations WHERE ref=?", (ref,)).fetchone():
        return False
    c.execute("INSERT INTO mail_delegations(mail_id, owner_id, ref, request_no, win_url, url, room_name, assignees, due, "
              "instruction, result_kind, state, label) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (mail_id, owner_id, ref, int(resp.get("request_no") or 0) or None, str(resp.get("win_url") or "")[:500],
               str(resp.get("url") or "")[:500], str(resp.get("room_name") or "")[:200],
               json.dumps(assignees, ensure_ascii=False), str(resp.get("due") or "")[:20], (instruction or "")[:MAX_INSTR],
               result_kind, "working", "진행 중"))
    return True


def rows_for_mail(c, owner_id, mail_id):
    ensure(c)
    return [dict(r) for r in c.execute(
        "SELECT * FROM mail_delegations WHERE owner_id=? AND mail_id=? AND state<>'gone' ORDER BY id", (owner_id, mail_id)).fetchall()]


def count_for_mail(c, owner_id, mail_id) -> int:
    try:
        ensure(c)
        return c.execute("SELECT COUNT(*) FROM mail_delegations WHERE owner_id=? AND mail_id=? AND state<>'gone'",
                         (owner_id, mail_id)).fetchone()[0]
    except Exception:
        return 0


def apply_status(c, rows, items):
    """이음 상태를 기록에 반영(gone = 지움 표시 · 이름은 이음 표시 이름으로)."""
    for d in rows:
        it = items.get(d["ref"])
        if not it:
            continue
        if not it.get("found"):
            d["missing"] = True
            continue
        st = str(it.get("state") or "working")
        d["state"], d["label"] = st, str(it.get("label") or "")
        d["state_at"] = str(it.get("ended_at") or it.get("delivered_at") or it.get("updated_at") or "")
        d["archived"] = bool(it.get("archived"))
        if it.get("due"):
            d["due"] = str(it.get("due"))[:20]
        names = [{"employee_no": str(a.get("employee_no") or ""), "name": str(a.get("name") or ""),
                  "status": str(a.get("status") or "")} for a in (it.get("assignees") or []) if isinstance(a, dict)]
        if names:
            d["assignees"] = json.dumps(names, ensure_ascii=False)
        c.execute("UPDATE mail_delegations SET state=?, label=?, state_at=?, due=?, assignees=? WHERE id=?",
                  (d["state"], d["label"], d["state_at"], d.get("due") or "", d["assignees"], d["id"]))
    return [d for d in rows if d.get("state") != "gone"]


def local_label(iso_utc, off) -> str:
    """UTC ISO → 맡긴 사람 소속 시각 「11/21 12:10」."""
    s = (iso_utc or "").strip()
    if not s:
        return ""
    try:
        t = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        t = t.astimezone(timezone.utc).replace(tzinfo=None) + timedelta(hours=off)
        return t.strftime("%m/%d %H:%M")
    except Exception:
        return ""


def due_label(due) -> str:
    s = (due or "").strip()
    if not s:
        return ""
    try:
        d = datetime.strptime(s[:10], "%Y-%m-%d")
        lab = "%02d/%02d(%s)" % (d.month, d.day, "월화수목금토일"[d.weekday()])
        return lab + ((" " + s[11:16]) if len(s) >= 16 else "")
    except Exception:
        return s[:16]


def view_item(d, off) -> dict:
    """띠 한 줄에 필요한 것만(공유키·이음 내부 값 없음)."""
    try:
        names = [a.get("name") or a.get("employee_no") or "" for a in json.loads(d.get("assignees") or "[]")]
    except Exception:
        names = []
    st = d.get("state") or "working"
    return {"id": d["id"], "request_no": d.get("request_no"), "names": [n for n in names if n],
            "state": st, "mark": STATE_MARK.get(st, d.get("label") or ""), "label": d.get("label") or "",
            "when": local_label(d.get("state_at"), off) if st in ("review", "done", "closed", "cancelled") else "",
            "due": due_label(d.get("due")), "win_url": d.get("win_url") or "", "url": d.get("url") or "",
            "room_name": d.get("room_name") or "", "missing": bool(d.get("missing")),
            "result": RESULT_LABEL.get(d.get("result_kind") or "reply", "답변"),
            "instruction": d.get("instruction") or ""}
