# -*- coding: utf-8 -*-
"""메일 「보낸 곳별 정리」 · 「다시 안 받기」 (2026-11-16 대표 지시 · 세션 15)

대표 말씀: 「스팸 메일들. 나한테 불필요한 메일들을 내가 다 찾아서 일일이 지우는 것도 일이었어. …
          쉽게 할 수 있는 방법이 있었으면 좋겠어.」

하는 일
  ① 받은편지함을 **보낸 곳별로 묶어** 보여 준다 — 광고·알림으로 보이는 곳을 위에. 한 번에 골라 정리.
  ② 「다시 안 받기」 — **나에게만** 적용(회사 전체 차단목록과 별개). 그 발신의 메일은 앞으로 내 차단함으로 간다.

지키는 것
  · 지우지 않는다 — 휴지통(되돌리기 가능) 또는 차단함(되돌리기 가능)으로 옮길 뿐.
  · 별표한 메일은 한 번에 정리에서 남긴다.
  · 「다시 안 받기」는 우리 저장소 안의 규칙이다 — 메일 속 「수신거부」 링크에 접속하지 않는다
    (메일 본문의 링크는 접속 금지 규정 · 수신거부 링크는 주소가 살아 있음을 알려 주는 미끼일 수도 있다).
  · 광고·알림 판별은 규칙으로만(AI·외부 전송 없음). 주소록에 있거나 내가 답장한 적 있는 곳은 「거래 상대」로 따로 표시.
  · 켜는 길이 있으면 푸는 길도 — 「다시 안 받기」 목록에서 풀 수 있고, 풀 때 옮겨진 메일을 되돌릴 수 있다.
"""
from __future__ import annotations

import re

OUR_DOMAINS = ("knknara.co.kr",)
SCAN_LIMIT = 5000           # 묶음을 만들 때 훑는 최근 받은 메일 수(화면 속도)
MAX_ADDRS = 200             # 한 번에 정리할 수 있는 보낸 곳 수

_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# 사람이 아니라 장치가 보내는 주소(답장을 받지 않는 주소 · 소식지 · 알림)
_RE_ROBOT = re.compile(
    r"^(?:.*no[-_.]?reply.*|.*do[-_.]?not[-_.]?reply.*|.*noreply.*|newsletter.*|news|notice|notify|"
    r"notifications?|mailer(?:-daemon)?|mailing|marketing|promo(?:tion)?s?|events?|bounces?|alerts?|digest|"
    r"updates?|webzine|magazine|campaign|ad|ads|edm|dm)(?:[-_.+].*)?$", re.I)
_SQL_AD = ("(subject LIKE '%(광고)%' OR subject LIKE '%[광고]%' OR subject LIKE '%（광고）%' "
           "OR subject LIKE '%(AD)%' OR subject LIKE '%[AD]%')")
_SQL_UNSUB = ("(instr(substr(COALESCE(body_text,''), -2500), '수신거부')>0 "
              "OR instr(substr(COALESCE(body_text,''), -2500), '수신 거부')>0 "
              "OR instr(substr(COALESCE(body_text,''), -2500), '수신을 원치')>0 "
              "OR instr(substr(COALESCE(body_text,''), -2500), '수신을 원하지')>0 "
              "OR instr(substr(COALESCE(body_text,''), -2500), '구독 취소')>0 "
              "OR instr(substr(COALESCE(body_text,''), -2500), '구독취소')>0 "
              "OR instr(lower(substr(COALESCE(body_text,''), -2500)), 'unsubscribe')>0 "
              "OR instr(lower(substr(COALESCE(body_text,''), -2500)), 'opt-out')>0 "
              "OR instr(lower(substr(COALESCE(body_text,''), -2500)), 'opt out')>0)")

_OK = {"v": False}


def ensure(c) -> None:
    """내 「다시 안 받기」 목록 표 — 없으면 만든다(빈 표 · 기존 자료 무접촉)."""
    if _OK["v"]:
        return
    c.execute("""CREATE TABLE IF NOT EXISTS mail_user_blocks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        addr TEXT NOT NULL,
        note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(user_id, addr))""")
    _OK["v"] = True


def norm(addr) -> str:
    a = (addr or "").strip().lower()
    m = _RE_EMAIL.search(a)
    return m.group(0) if m else ""


def _domain(addr: str) -> str:
    return addr.rsplit("@", 1)[1] if "@" in addr else ""


def is_internal(addr: str) -> bool:
    d = _domain(norm(addr))
    return bool(d) and any(d == o or d.endswith("." + o) for o in OUR_DOMAINS)


# ─── 「다시 안 받기」(나에게만) ────────────────────────────────────────────────
def is_muted(c, user_id, from_email) -> bool:
    a = norm(from_email)
    if not a or not user_id:
        return False
    try:
        ensure(c)
        return c.execute("SELECT 1 FROM mail_user_blocks WHERE user_id=? AND addr=?", (user_id, a)).fetchone() is not None
    except Exception:
        return False


def list_mutes(c, user_id) -> list:
    ensure(c)
    rows = c.execute(
        "SELECT b.id, b.addr, b.created_at, "
        "(SELECT COUNT(*) FROM mail_messages m WHERE m.user_id=b.user_id AND m.direction='in' AND m.is_deleted=0 "
        " AND COALESCE(m.is_blocked,0)=1 AND lower(m.from_email)=b.addr) AS held "
        "FROM mail_user_blocks b WHERE b.user_id=? ORDER BY b.id DESC", (user_id,)).fetchall()
    return [dict(r) for r in rows]


def add_mute(c, user_id, addr, note: str = "") -> int:
    """이 발신을 나에게만 「다시 안 받기」 + 이미 받은 것도 내 차단함으로. 반환 = 옮긴 통수(-1 = 주소가 아님)."""
    a = norm(addr)
    if not a or not user_id:
        return -1
    ensure(c)
    c.execute("INSERT OR IGNORE INTO mail_user_blocks(user_id, addr, note) VALUES(?,?,?)", (user_id, a, (note or "")[:120]))
    cur = c.execute(
        "UPDATE mail_messages SET is_blocked=1 WHERE user_id=? AND direction='in' AND is_deleted=0 "
        "AND COALESCE(is_blocked,0)=0 AND lower(from_email)=?", (user_id, a))
    return cur.rowcount or 0


def remove_mute(c, user_id, addr, restore: bool = False) -> int:
    """「다시 안 받기」 풀기. restore=True 면 차단함에 옮겨 둔 이 발신의 메일을 받은편지함으로 되돌린다.
    (회사 전체 차단목록에 걸린 곳 · 위험 판정으로 격리된 메일은 되돌리지 않는다.) 반환 = 되돌린 통수."""
    a = norm(addr)
    if not a or not user_id:
        return 0
    ensure(c)
    c.execute("DELETE FROM mail_user_blocks WHERE user_id=? AND addr=?", (user_id, a))
    if not restore:
        return 0
    try:
        from . import mail_store as _ms
        if _ms.is_sender_blocked(c, a):
            return 0
    except Exception:
        return 0
    cur = c.execute(
        "UPDATE mail_messages SET is_blocked=0 WHERE user_id=? AND direction='in' AND is_deleted=0 "
        "AND COALESCE(is_blocked,0)=1 AND COALESCE(risk_level,0)<3 AND lower(from_email)=?", (user_id, a))
    return cur.rowcount or 0


# ─── 보낸 곳별 묶음 ───────────────────────────────────────────────────────────
def _partner_sets(c, user_id) -> tuple:
    """(주소록에 있는 주소, 내가 메일을 보낸 적 있는 주소)."""
    contacts, replied = set(), set()
    try:
        for r in c.execute("SELECT lower(email) FROM shared_contacts WHERE email IS NOT NULL AND email<>''").fetchall():
            if r[0]:
                contacts.add(r[0].strip())
    except Exception:
        pass
    try:
        for r in c.execute("SELECT to_email, cc FROM mail_messages WHERE user_id=? AND direction='out' "
                           "ORDER BY id DESC LIMIT 3000", (user_id,)).fetchall():
            for e in _RE_EMAIL.findall(((r[0] or "") + " " + (r[1] or "")).lower()):
                replied.add(e)
    except Exception:
        pass
    return contacts, replied


def judge(addr: str, n: int, ad_n: int, unsub_n: int, in_contacts: bool, replied: bool) -> tuple:
    """묶음 하나의 갈래와 까닭. 반환 (kind, reasons) — kind: 'bulk'(광고·알림으로 보임) / 'partner'(거래 상대) / 'normal'."""
    reasons = []
    if is_internal(addr):
        return "partner", ["사내"]
    if in_contacts:
        reasons.append("주소록에 있음")
    if replied:
        reasons.append("내가 메일을 보낸 적 있음")
    if reasons:
        return "partner", reasons
    local = addr.split("@")[0] if "@" in addr else addr
    if ad_n and ad_n * 2 >= n:
        reasons.append("제목에 (광고) 표기")
    if unsub_n and unsub_n * 2 >= n:
        reasons.append("수신거부 안내가 붙은 메일")
    if _RE_ROBOT.match(local):
        reasons.append("답장을 받지 않는 자동 발송 주소")
    return ("bulk" if reasons else "normal"), reasons


def sender_groups(c, user_id, scan_limit: int = SCAN_LIMIT) -> dict:
    """받은편지함(차단함·휴지통 제외)의 최근 메일을 보낸 곳별로 묶는다.
    반환 {"groups": [...], "scanned": 훑은 통수, "total": 받은편지함 전체 통수}."""
    total = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 "
                      "AND COALESCE(is_blocked,0)=0", (user_id,)).fetchone()[0]
    rows = c.execute(
        "SELECT id, lower(COALESCE(from_email,'')) AS addr, from_name, subject, is_read, is_starred, received_at, "
        "COALESCE(raw_size,0) AS sz, " + _SQL_AD + " AS ad, " + _SQL_UNSUB + " AS unsub "
        "FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0 "
        "ORDER BY id DESC LIMIT ?", (user_id, int(scan_limit))).fetchall()
    contacts, replied = _partner_sets(c, user_id)
    g = {}
    for r in rows:
        a = (r["addr"] or "").strip()
        d = g.get(a)
        if d is None:
            d = g[a] = {"addr": a, "name": (r["from_name"] or "").strip(), "n": 0, "unread": 0, "starred": 0,
                        "last_at": r["received_at"] or "", "subject": (r["subject"] or "")[:120], "bytes": 0,
                        "ad_n": 0, "unsub_n": 0}
        d["n"] += 1
        d["unread"] += 0 if r["is_read"] else 1
        d["starred"] += 1 if r["is_starred"] else 0
        d["bytes"] += int(r["sz"] or 0)
        d["ad_n"] += 1 if r["ad"] else 0
        d["unsub_n"] += 1 if r["unsub"] else 0
    out = []
    # 11-23 대표 「광고·알림은 내가 지정할 수 있어?」 — 내가 보낸 사람마다 덮어쓴 표시가 자동 판단보다 먼저
    try:
        from . import mail_ui_prefs as _mup
        _ad_on, _ad_off, _ad_since = _mup.get_ad_marks3(c, user_id)
    except Exception as e:
        print("[MAIL-CLEANUP ad-mark ERR] %s: %s" % (type(e).__name__, e))
        _ad_on, _ad_off, _ad_since = set(), set(), {}
    for a, d in g.items():
        kind, reasons = judge(a, d["n"], d["ad_n"], d["unsub_n"], a in contacts, a in replied) if a else ("normal", [])
        if a and a in _ad_off:
            kind, reasons = "normal", ["내가 「광고·알림 아님」으로 표시"]
        elif a and a in _ad_on:
            kind, reasons = "bulk", ["내가 「광고·알림」으로 표시"]
        elif a and a in _ad_since:
            kind, reasons = "bulk", ["내가 「광고·알림」으로 표시(%s 받은 메일부터)" % _ad_since[a][:10]]
        d["kind"], d["reasons"] = kind, reasons
        out.append(d)
    order = {"bulk": 0, "normal": 1, "partner": 2}
    out.sort(key=lambda x: (order[x["kind"]], -x["n"], x["addr"]))
    return {"groups": out, "scanned": len(rows), "total": total}


def _addrs(addrs) -> list:
    seen, out = set(), []
    for a in addrs or ():
        n = norm(a)
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out[:MAX_ADDRS]


def trash_senders(c, user_id, addrs) -> dict:
    """고른 보낸 곳의 받은 메일을 모두 휴지통으로(별표한 메일은 남김 · 되돌리기 가능). 반환 {"moved", "kept_starred", "senders"}."""
    moved = kept = 0
    al = _addrs(addrs)
    for a in al:
        kept += c.execute(
            "SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 "
            "AND COALESCE(is_blocked,0)=0 AND COALESCE(is_starred,0)=1 AND lower(from_email)=?", (user_id, a)).fetchone()[0]
        cur = c.execute(
            "UPDATE mail_messages SET is_deleted=1, deleted_at=datetime('now','localtime') "
            "WHERE user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0 "
            "AND COALESCE(is_starred,0)=0 AND lower(from_email)=?", (user_id, a))
        moved += cur.rowcount or 0
    return {"moved": moved, "kept_starred": kept, "senders": len(al)}


def mute_senders(c, user_id, addrs) -> dict:
    """고른 보낸 곳을 나에게만 「다시 안 받기」 + 이미 받은 것도 내 차단함으로. 사내 주소는 건너뛴다."""
    moved = done = skipped = 0
    for a in _addrs(addrs):
        if is_internal(a):
            skipped += 1
            continue
        n = add_mute(c, user_id, a, "보낸 곳별 정리")
        if n >= 0:
            done += 1
            moved += n
    return {"moved": moved, "senders": done, "skipped_internal": skipped}
