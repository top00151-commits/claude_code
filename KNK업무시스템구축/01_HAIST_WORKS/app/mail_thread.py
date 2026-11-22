# -*- coding: utf-8 -*-
"""같은 대화 한눈에 (대표 2026-11-22 밤 「메일 규칙을 쉽게 — 너가 사용자라면」 3)

회신·전달은 보낸 사람 기준 자리(우리 직원 = 부서 폴더 · 거래처 = 그 회사 폴더)에 그대로 두고,
메일을 열면 「💬 같은 대화 N통 · 폴더별 통수」를 한 줄로 · 누르면 그 대화의 메일을 시간 순서로 펼친다(옮기지 않음).

같은 대화 = 제목이 같은 메일(앞의 RE:·FW:·회신:·전달: 등은 뺌 · 대소문자·띄어쓰기 무시) · 그 메일 앞뒤 120일 안 · 내 메일만(받은·보낸).
제목이 너무 짧거나 흔하면(「견적 요청」 같은 것으로 서로 다른 대화가 많이 섞이면) 보낸 곳이 같은 메일만 남긴다.
"""
import re
from datetime import datetime, timedelta

WINDOW_DAYS = 120
MAX_ITEMS = 40
GENERIC_N = 25          # 이보다 많이 걸리면 흔한 제목 → 보낸 곳이 같은 것만


def _dom(e):
    e = (e or "").strip().lower()
    return e.rsplit("@", 1)[-1] if "@" in e else ""


def _dt(s):
    try:
        return datetime.strptime((s or "")[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def thread_of(c, uid, m, res=None) -> dict:
    """메일 한 통의 같은 대화 → {"n", "by": [(폴더, 통수)], "rows": [{id, at, who, sj, folder, cur, out}]} · 저 혼자면 None."""
    from .mail_store import _normalize_subject
    key = _normalize_subject(m.get("subject") or "")
    if key == "(제목 없음)" or len(re.sub(r"\s+", "", key)) < 4:
        return None
    at = _dt(m.get("received_at") or m.get("created_at"))
    lo = (at - timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%d %H:%M:%S") if at else "0000"
    hi = (at + timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%d %H:%M:%S") if at else "9999"
    core = key[:60]
    rows = []
    for r in c.execute("SELECT id, direction, lower(COALESCE(from_email,'')) AS e, COALESCE(from_name,'') AS nm, "
                       "COALESCE(to_email,'') AS t, COALESCE(subject,'') AS sj, COALESCE(received_at, created_at, '') AS at, "
                       "COALESCE(fd_key,'') AS k, COALESCE(fd_pin,'') AS pin FROM mail_messages "
                       "WHERE user_id=? AND is_deleted=0 AND COALESCE(is_blocked,0)=0 AND direction IN ('in','out') "
                       "AND COALESCE(received_at, created_at, '') BETWEEN ? AND ? AND instr(lower(subject), ?) > 0 "
                       "ORDER BY COALESCE(received_at, created_at) LIMIT 400", (int(uid), lo, hi, core)).fetchall():
        if _normalize_subject(r["sj"]) == key:
            rows.append(dict(r))
    if len(rows) > GENERIC_N:   # 흔한 제목 — 이 메일의 상대 회사(보낸 곳 · 내가 보낸 메일이면 받는 곳)와 같은 것만
        md = _dom(m.get("from_email")) if m.get("direction") != "out" else _dom((m.get("to_email") or "").split(",")[0])
        if md:
            rows = [r for r in rows if r["id"] == m.get("id") or _dom(r["e"]) == md
                    or (r["direction"] == "out" and md in (r["t"] or "").lower())]
    if len(rows) <= 1:
        return None
    labels = (res or {}).get("labels") or {}
    valid = (res or {}).get("valid") or ()
    by, items = {}, []
    for r in rows:
        if r["direction"] == "out":
            fl = "보낸 메일"
            who = "→ " + ((r["t"] or "").split(",")[0].strip() or "?")
        else:
            k = r["pin"] if (r["pin"] and r["pin"] in valid) else (r["k"] or "gen")
            fl = labels.get(k, "일반" if k == "gen" else "받은 메일")
            who = r["nm"] or r["e"] or "(보낸 사람 모름)"
        by[fl] = by.get(fl, 0) + 1
        items.append({"id": r["id"], "at": (r["at"] or "")[5:16], "who": who[:40], "sj": (r["sj"] or "")[:90],
                      "folder": fl, "cur": r["id"] == m.get("id"), "out": r["direction"] == "out"})
    if len(items) > MAX_ITEMS:   # 이 메일 둘레만
        ci = next((i for i, x in enumerate(items) if x["cur"]), 0)
        s0 = max(0, min(ci - MAX_ITEMS // 2, len(items) - MAX_ITEMS))
        items = items[s0:s0 + MAX_ITEMS]
    return {"n": len(rows), "by": sorted(by.items(), key=lambda x: -x[1]), "rows": items}
