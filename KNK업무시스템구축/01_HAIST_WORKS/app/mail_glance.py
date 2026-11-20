# -*- coding: utf-8 -*-
"""메일 2단계(대표 11-20 「다음 진행해」) — 메일 숫자·기록 + 정보 받아 오기(읽기만).

  ⑥ 받은편지함 위 「메일 하루 숫자」 — 오늘 예약 숫자(`count_sched_today`) · 나머지 숫자는 이미 있는 함수 그대로
  ⑦ 큰 파일(대용량 링크) 받아 간 시각 — 표 `mail_large_dl`(링크 번호·시각만 · 받아 간 사람의 주소·IP 는 적지 않음)
  🏖 휴가 → 부재중 자동 응답 「제안」 · 받는 사람 휴가 표시 — 이음 직원 명부(GET /api/sso/directory)를 **서버에서만** 부르고 5분 캐시
  🏢 거래처 메일 옆 진행 상황 — 웍스 고객사·프로젝트를 **읽기만**(고치지 않음)

계획서: 작업기록/2026-11-19_2306_메일_다음기능_최종정리_세션경계확인.md 5장 「2단계」
⛔ 이음 대화방·메시지는 읽지도 쓰지도 않는다(명부만 · 김정락–안지연 1:1 방과 무관).
⛔ 공유키 값은 화면·기록·응답 어디에도 내보내지 않는다.
⛔ 메일 본문은 어디로도 보내지 않는다(이 모듈은 본문을 다루지 않음 · 대용량 링크 번호만 찾는다).
"""
import re
import threading
import time
from datetime import datetime, timedelta, timezone

import httpx

from . import sso_client as _sso   # 이음 주소·공유키 — 다른 세션(01) 파일이라 읽기만(import)

# ═══════════════════════ 이음 직원 명부(휴가) ═══════════════════════
DIR_TTL = 300          # 잘 받아 온 명부는 5분 동안 다시 안 부름
DIR_FAIL_TTL = 60      # 실패하면 1분 동안 다시 안 부름(느린 이음을 두드리지 않게)
DIR_STALE_MAX = 900    # 실패했을 때 15분 안에 받아 둔 명부는 그대로 씀
DIR_TIMEOUT = 4.0
VAC_STATUS = "vacation"

_DIR = {"data": None, "ok_at": 0.0, "fail_at": 0.0, "busy": False, "calls": 0}
_DIR_LOCK = threading.Lock()


def dir_reset():
    """시험·시연용 — 캐시 비우기."""
    with _DIR_LOCK:
        _DIR.update(data=None, ok_at=0.0, fail_at=0.0, busy=False, calls=0)


def dir_calls() -> int:
    return int(_DIR.get("calls") or 0)


def _norm_emp(e) -> str:
    return str(e or "").strip().upper()


def _fetch_directory():
    """이음 명부 → 휴가 중인 사람만 남긴 작은 표. 실패 = None. (전화·연락처 등 다른 칸은 버린다)"""
    key = _sso.get_service_key()
    if not key:
        return None
    url = "%s/api/sso/directory" % (_sso.MESSENGER_INTERNAL_BASE or "").rstrip("/")
    try:
        r = httpx.get(url, headers={"X-SSO-Service-Key": key}, timeout=DIR_TIMEOUT)
    except Exception as e:
        print("[MAIL-VAC] 이음 명부 연결 실패: %s" % type(e).__name__, flush=True)
        return None
    if r.status_code != 200:
        print("[MAIL-VAC] 이음 명부 응답 %s" % r.status_code, flush=True)
        return None
    try:
        users = (r.json() or {}).get("users") or []
    except Exception:
        print("[MAIL-VAC] 이음 명부 읽기 실패(JSON 아님)", flush=True)
        return None
    by_emp, by_email = {}, {}
    for u in users:
        if not isinstance(u, dict):
            continue
        if u.get("active") is False or (u.get("status") or "") != VAC_STATUS:
            continue
        rec = {"emp": _norm_emp(u.get("employee_no")), "name": (u.get("name_kr") or "").strip(),
               "position": (u.get("position") or "").strip(), "dept": (u.get("dept") or "").strip(),
               "until": (u.get("status_until") or "") or ""}
        if rec["emp"]:
            by_emp[rec["emp"]] = rec
        em = (u.get("email") or "").strip().lower()
        if em and "@" in em:
            by_email[em] = rec
    return {"emp": by_emp, "email": by_email, "total": len(users)}


def directory(now=None):
    """휴가 표(캐시). 서버 일꾼 스레드에서 부를 것(run_in_threadpool) — DB 를 쥔 채 부르지 말 것.
    다른 요청이 이미 부르는 중이면 기다리지 않고 지금 가진 것(없으면 None)을 돌려준다."""
    now = time.time() if now is None else now
    with _DIR_LOCK:
        d, ok_at, fail_at = _DIR["data"], _DIR["ok_at"], _DIR["fail_at"]
        if d is not None and now - ok_at < DIR_TTL:
            return d
        stale = d if (d is not None and now - ok_at < DIR_STALE_MAX) else None
        if now - fail_at < DIR_FAIL_TTL or _DIR["busy"]:
            return stale
        _DIR["busy"] = True
        _DIR["calls"] += 1
    got = None
    try:
        got = _fetch_directory()
    except Exception as e:
        print("[MAIL-VAC] 이음 명부 오류: %s" % type(e).__name__, flush=True)
        got = None
    with _DIR_LOCK:
        _DIR["busy"] = False
        if got is not None:
            _DIR["data"], _DIR["ok_at"] = got, time.time()
            return got
        _DIR["fail_at"] = time.time()
        return stale


def until_local(iso, off: int) -> str:
    """이음 휴가 끝(ISO · 보통 UTC) → 보는 사람 소속 날짜 'YYYY-MM-DD'. 자정 딱 끝이면 그 전날까지로 본다. 모르면 ''."""
    s = str(iso or "").strip()
    if not s:
        return ""
    try:
        s2 = s.replace("Z", "+00:00").replace(" ", "T", 1)
        if re.match(r"^\d{4}-\d{2}-\d{2}$", s2):
            return s2
        dt = datetime.fromisoformat(s2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        loc = dt.astimezone(timezone.utc).replace(tzinfo=None) + timedelta(hours=int(off))
        if loc.hour == 0 and loc.minute == 0 and loc.second == 0:
            loc -= timedelta(seconds=1)
        return loc.date().isoformat()
    except Exception:
        return ""


def md_label(d: str) -> str:
    """'2026-11-24' → '11/24'."""
    try:
        return "%d/%d" % (int(d[5:7]), int(d[8:10]))
    except Exception:
        return ""


def my_vacation(dirdata, emp_no, emails, off: int):
    """내가 이음에 휴가로 돼 있으면 {'until': 'YYYY-MM-DD' 또는 '', 'label': '~11/24'} · 아니면 None."""
    if not dirdata:
        return None
    rec = None
    e = _norm_emp(emp_no)
    if e:
        rec = (dirdata.get("emp") or {}).get(e)
    if rec is None:
        for em in (emails or []):
            rec = (dirdata.get("email") or {}).get((em or "").strip().lower())
            if rec:
                break
    if not rec:
        return None
    u = until_local(rec.get("until"), off)
    return {"until": u, "label": ("~" + md_label(u)) if u else ""}


def vac_for_addrs(dirdata, addrs, emp_of_addr, off: int) -> dict:
    """주소 목록 → 휴가 중인 사람만 {주소: {'emp', 'name', 'until', 'label'}}.
    emp_of_addr = 웍스 직원 주소 → 사번(명부 주소와 다르게 적힌 사람도 찾게)."""
    out = {}
    if not dirdata:
        return out
    for a in addrs or []:
        a = (a or "").strip().lower()
        if not a or "@" not in a or a in out:
            continue
        rec = (dirdata.get("email") or {}).get(a)
        if rec is None:
            e = _norm_emp((emp_of_addr or {}).get(a))
            if e:
                rec = (dirdata.get("emp") or {}).get(e)
        if not rec:
            continue
        u = until_local(rec.get("until"), off)
        out[a] = {"emp": rec.get("emp") or "", "name": rec.get("name") or "", "position": rec.get("position") or "",
                  "dept": rec.get("dept") or "", "until": u, "label": ("~" + md_label(u)) if u else ""}
    return out


# ═══════════════════════ ⑥ 오늘 예약 숫자 ═══════════════════════
def count_sched_today(c, user_id, end_srv: str) -> dict:
    """오늘(보는 사람 소속 날짜) 안에 보낼 예약(시각이 이미 됐는데 아직 안 나간 것 포함) · 못 보낸 예약.
    end_srv = 그 사람 내일 0시를 서버 시각 글자로."""
    from . import mail_store as _ms
    _ms._ensure_security_cols(c)
    r = c.execute(
        "SELECT SUM(CASE WHEN sched_state IN ('wait','sending') AND sched_at<? THEN 1 ELSE 0 END) AS t, "
        "SUM(CASE WHEN sched_state='fail' THEN 1 ELSE 0 END) AS f "
        "FROM mail_messages WHERE user_id=? AND direction='sched' AND is_deleted=0 AND COALESCE(sched_at,'')<>''",
        (end_srv, user_id)).fetchone()
    return {"today": int((r["t"] if r else 0) or 0), "fail": int((r["f"] if r else 0) or 0)}


# ═══════════════════════ ⑦ 큰 파일 받아 간 시각 ═══════════════════════
_DL_RE = re.compile(r"/dl/([A-Za-z0-9_\-]{16,64})")
DL_RECENT = 5


def ensure_dl(c):
    from . import mail_store as _ms
    _ms.ensure_large_dl(c)


def large_tokens_in(*texts) -> list:
    seen, out = set(), []
    for t in texts:
        for tk in _DL_RE.findall(t or ""):
            if tk not in seen:
                seen.add(tk)
                out.append(tk)
    return out[:20]


def large_info_for_mail(c, user_id, m, label_fn) -> list:
    """이 메일 본문에 있는 대용량 링크 중 **내가 올린 파일만** → [{name, size_h, n, first, last, recent[], expired, exp}].
    label_fn(서버 시각 글자) → 보는 사람 소속 「11/20 14:03」."""
    from . import mail_store as _ms
    toks = large_tokens_in(m.get("body_text") or "", m.get("body_html") or "")
    if not toks:
        return []
    ensure_dl(c)
    out = []
    for tk in toks:
        r = c.execute("SELECT token, filename, size, download_count, expires_at, uploaded_by, "
                      "(expires_at IS NOT NULL AND datetime('now','localtime') > expires_at) AS ex "
                      "FROM mail_large_files WHERE token=?", (tk,)).fetchone()
        if not r or r["uploaded_by"] != user_id:
            continue
        lg = c.execute("SELECT COUNT(*) AS n, MIN(at) AS a1, MAX(at) AS a2 FROM mail_large_dl WHERE token=?", (tk,)).fetchone()
        recent = [label_fn(x["at"]) for x in c.execute(
            "SELECT at FROM mail_large_dl WHERE token=? ORDER BY id DESC LIMIT ?", (tk, DL_RECENT)).fetchall()]
        n = max(int(r["download_count"] or 0), int(lg["n"] or 0))
        out.append({"name": r["filename"] or "file", "size_h": _ms.human_size(r["size"]), "n": n,
                    "logged": int(lg["n"] or 0), "first": label_fn(lg["a1"]) if lg["a1"] else "",
                    "last": label_fn(lg["a2"]) if lg["a2"] else "", "recent": recent,
                    "expired": bool(r["ex"]), "exp": label_fn(r["expires_at"]) if r["expires_at"] else ""})
    return out


# ═══════════════════════ 🏢 거래처 진행 상황(웍스 읽기만) ═══════════════════════
CUST_PJ_MAX = 5
CUST_ORDER_MAX = 3
_DONE_ST = ("완료", "종료", "취소")


def customer_of(c, email):
    """보낸 사람 → 거래처 번호. 받은 메일 「거래처 폴더」(mail_store.customer_folder_counts)와 **같은 규칙**:
    ① 연락처 이메일 정확 일치 ② 없으면 같은 회사 주소(@ 뒤)가 한 거래처만 가리킬 때. 둘 이상이면 None(추측 안 함)."""
    from . import mail_store as _ms
    e = (email or "").strip().lower()
    if not e or "@" not in e:
        return None
    try:
        cids = sorted({r["cid"] for r in c.execute(
            "SELECT customer_id AS cid FROM shared_contacts WHERE email IS NOT NULL AND customer_id IS NOT NULL "
            "AND lower(email)=?", (e,)).fetchall()})
        if len(cids) > 1:
            return None
        if not cids:
            d = e.rsplit("@", 1)[-1]
            r = c.execute("SELECT cid FROM (" + _ms._CUST_DOMAIN_MAP_SQL + ") WHERE dom=?", (d,)).fetchone()
            cids = [r["cid"]] if r else []
        if len(cids) != 1:
            return None
        ok = c.execute("SELECT id FROM customers WHERE id=?", (cids[0],)).fetchone()
        return cids[0] if ok else None
    except Exception:
        return None


def customer_progress(c, cid, with_money: bool, money_fn=None):
    """그 고객사의 진행 중 프로젝트(최근 5) · 최근 수주(3). with_money=False 면 금액 칸을 아예 만들지 않는다."""
    cu = c.execute("SELECT id, name FROM customers WHERE id=?", (cid,)).fetchone()
    if not cu:
        return None
    cols = {r[1] for r in c.execute("PRAGMA table_info(projects)").fetchall()}

    def _col(n, alt="''"):
        return n if n in cols else alt + " AS " + n

    sel = ", ".join(["id", "name", _col("mgmt_code"), _col("status"), _col("stage"), _col("due_date"),
                     _col("order_date"), _col("order_amount", "0"), _col("currency", "'KRW'")])
    arc = " AND COALESCE(is_archived,0)=0" if "is_archived" in cols else ""
    ph = ",".join("?" * len(_DONE_ST))
    live = [dict(r) for r in c.execute(
        "SELECT " + sel + " FROM projects WHERE customer_id=? AND COALESCE(status,'') NOT IN (" + ph + ")" + arc +
        " ORDER BY id DESC LIMIT ?", (cid,) + _DONE_ST + (CUST_PJ_MAX + 1,)).fetchall()]
    n_live = c.execute("SELECT COUNT(*) FROM projects WHERE customer_id=? AND COALESCE(status,'') NOT IN (" + ph + ")" + arc,
                       (cid,) + _DONE_ST).fetchone()[0]
    orders = []
    if "order_date" in cols:
        orders = [dict(r) for r in c.execute(
            "SELECT " + sel + " FROM projects WHERE customer_id=? AND COALESCE(order_date,'')<>'' AND COALESCE(status,'')<>'취소'" + arc +
            " ORDER BY order_date DESC, id DESC LIMIT ?", (cid, CUST_ORDER_MAX)).fetchall()]

    def _clean(p):
        x = {"id": p["id"], "name": p.get("name") or "", "code": p.get("mgmt_code") or "", "status": p.get("status") or "",
             "stage": p.get("stage") or "", "due": (p.get("due_date") or "")[:10], "order_date": (p.get("order_date") or "")[:10]}
        if with_money and money_fn and p.get("order_amount"):
            try:
                x["amount"] = money_fn(p.get("order_amount"), p.get("currency") or "KRW")
            except Exception:
                pass
        return x

    return {"id": cu["id"], "name": cu["name"] or "", "live": [_clean(p) for p in live[:CUST_PJ_MAX]],
            "live_n": int(n_live or 0), "orders": [_clean(p) for p in orders], "money": bool(with_money)}
