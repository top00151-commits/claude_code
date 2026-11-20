# -*- coding: utf-8 -*-
"""z1191z86 — 수출 단가 점검 조건(사용자가 정함) · 범위 밖 줄의 허용/고치기 선택

대표 2026-11-20:
  「단가가 지난번보다 30% 넘게? 이런 부분은 조건을 사용자가 넣을수있으면 좋겠어.. 지금은 우리가 원자재를 베트남세관 눈치로
   약 12%~15%만 올리는 중이라.. 이런 변할수있는거라.. 조건을 사용자가 넣을수있게.」
  「…기존에 나간 단가와 얼마가 차이가 나는지를 찾아내면 되는 것 같아. 그거를 갖다가 범위를 정하는 거고. 만약에 그 정한 범위를
   벗어나든가 하면은 일단 알람을 울려주는 건지, 그럼 알람 울려주고 나서 사용자가 그 벗어난 것도 허용을 할 건지 말 건지를
   선택을 받고 다음을 진행하면 되는 거고.」
  ⛔구매 단가 대비 마진(12~15%) 점검은 구매 모듈이 연결된 뒤(지금은 하지 않음).

무엇:
  - 조건 = 통관 구분(수책통관 · 일반통관)마다 「지난번 수출 단가보다 오름 N% · 내림 N% 넘으면 알림」(빈칸 = 그쪽은 안 봄).
    처음 값 = 오름·내림 15%(대표 11-20 「15%로 하고」 · 그전 ① 은 ±20%) — 바꾸면 ① 자동 채움 · 선적 건 서류 점검이 **같은 조건**을 쓴다.
  - 범위 밖 줄 → 사용자가 「허용(까닭)」 또는 「고치기」를 고른다 — (인보이스 번호 · 규격 · 이번 단가)마다 한 번.
    고르기 전에는 ① 의 채운 파일 받기를 열지 않는다(고르면 바로 열림). 단가를 바꿔 다시 올리면 새로 고른다.
  - 「고치기」로 고른 단가는 다음 인보이스의 「지난번」 기준에서 뺀다(틀린 값이 기준이 되지 않게).
"""
from __future__ import annotations

KINDS = ("수책통관", "일반통관")
DEFAULT_PCT = 15.0          # 처음 값 = 대표 11-20 「15%로 하고」(그전 ① 은 ±20% · z1191p)
MAX_PCT = 1000.0
REASONS = ("가격이 바뀜(인상·인하 반영)", "사양·구성이 지난번과 다름", "수량·묶음 단위가 다름", "환율·운임 반영")


def ensure(c):
    c.execute("""CREATE TABLE IF NOT EXISTS export_price_rule (
        kind TEXT PRIMARY KEY, up_pct REAL, down_pct REAL, updated_by INTEGER, updated_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS export_price_rule_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, old_value TEXT, new_value TEXT, by_user INTEGER, at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS export_price_ack (
        invoice_no TEXT, part_key TEXT, price_key TEXT, descr TEXT, base_price REAL, base_invoice TEXT, diff REAL,
        decision TEXT, reason TEXT, by_user INTEGER, at TEXT,
        PRIMARY KEY(invoice_no, part_key, price_key))""")
    # ① 자동 채움 한 번(기록 id)마다 범위 밖이던 줄 — 받기 전에 다 골랐는지 본다
    c.execute("""CREATE TABLE IF NOT EXISTS export_price_need (
        log_id INTEGER, invoice_no TEXT, part_key TEXT, price_key TEXT, PRIMARY KEY(log_id, part_key, price_key))""")
    for k in KINDS:
        c.execute("INSERT OR IGNORE INTO export_price_rule(kind, up_pct, down_pct, updated_by, updated_at) VALUES(?,?,?,NULL,NULL)",
                  (k, DEFAULT_PCT, DEFAULT_PCT))


def pkey(price) -> str:
    """단가 → 고른 것을 묶는 열쇠(소수 넷째 자리까지)."""
    try:
        return "%.4f" % round(float(price), 4)
    except (TypeError, ValueError):
        return ""


def rules(c) -> dict:
    ensure(c)
    return {r["kind"]: {"up": r["up_pct"], "down": r["down_pct"], "by": r["updated_by"], "at": r["updated_at"] or ""}
            for r in c.execute("SELECT * FROM export_price_rule")}


def kind_of(v) -> str:
    """양식 이름·통관 구분 글자 → 수책통관 / 일반통관 / ''(모름·섞임)."""
    s = "·".join(v) if isinstance(v, (list, tuple, set)) else str(v or "")
    a, b = ("수책" in s), ("일반" in s or "소모품" in s)
    return "수책통관" if a and not b else ("일반통관" if b and not a else "")


def tol(rs: dict, kind: str):
    """(오름 %, 내림 %) — 구분을 모르면(섞임) 두 구분 중 더 좁은 값. None = 그쪽은 안 봄."""
    if kind in rs:
        return rs[kind]["up"], rs[kind]["down"]

    def tight(vals):
        vals = [x for x in vals if x is not None]
        return min(vals) if vals else None
    return tight([rs[k]["up"] for k in rs]), tight([rs[k]["down"] for k in rs])


def out_of_range(diff, up, down) -> bool:
    return (up is not None and diff > up + 1e-9) or (down is not None and diff < -down - 1e-9)


def rule_text(up, down) -> str:
    bits = []
    if up is not None:
        bits.append("오름 %g%%" % up)
    if down is not None:
        bits.append("내림 %g%%" % down)
    return (" · ".join(bits) + " 넘으면 알림") if bits else "단가는 안 봄"


def stamp(c) -> str:
    """점검 결과를 다시 만들어야 하는지 — 조건이 바뀌거나 「고치기」가 늘면 달라진다."""
    ensure(c)
    r = c.execute("SELECT COALESCE(MAX(updated_at),''), COUNT(*), COALESCE(SUM(up_pct),-1), COALESCE(SUM(down_pct),-1) FROM export_price_rule").fetchone()
    f = c.execute("SELECT COUNT(*), COALESCE(MAX(at),'') FROM export_price_ack WHERE decision='fix'").fetchone()
    return "r%s.%s.%s.%s|f%s.%s" % (r[0], r[1], r[2], r[3], f[0], f[1])


def fixed(c) -> set:
    """「고치기」로 고른 (인보이스, 규격, 단가) — 다음 인보이스의 「지난번」 기준에서 뺀다."""
    ensure(c)
    return {(r[0], r[1], r[2]) for r in c.execute("SELECT invoice_no, part_key, price_key FROM export_price_ack WHERE decision='fix'")}


def acks(c, invoice_no) -> dict:
    ensure(c)
    if not invoice_no:
        return {}
    return {(r["part_key"], r["price_key"]): dict(r) for r in
            c.execute("SELECT * FROM export_price_ack WHERE invoice_no=?", (invoice_no,))}


def overlay(rows: list, ak: dict, udisp=None, c=None) -> dict:
    """범위 밖 줄들(key · now)에 고른 것을 붙인다 → {open, allow, fix}. rows 는 그 자리에서 바뀐다."""
    n = {"open": 0, "allow": 0, "fix": 0}
    seen = set()
    for p in rows:
        a = ak.get((p.get("key"), pkey(p.get("now"))))
        p["decision"] = (a or {}).get("decision") or ""
        p["reason"] = (a or {}).get("reason") or ""
        p["at"] = ((a or {}).get("at") or "")[:16]
        p["by_name"] = (udisp(c, a["by_user"]) if (udisp and a and a.get("by_user")) else "")
        k = (p.get("key"), pkey(p.get("now")))
        if k in seen:
            continue
        seen.add(k)
        n[p["decision"] or "open"] += 1
    return n


def save_need(c, log_id, invoice_no, rows):
    """① 한 번의 범위 밖 줄을 적어 둔다(받기 전 확인용) — 같은 기록이면 바꿔 적는다."""
    ensure(c)
    c.execute("DELETE FROM export_price_need WHERE log_id=?", (log_id,))
    if not invoice_no:
        return
    for p in rows:
        c.execute("INSERT OR IGNORE INTO export_price_need(log_id, invoice_no, part_key, price_key) VALUES(?,?,?,?)",
                  (log_id, invoice_no, p["key"], pkey(p["now"])))


def open_count(c, log_id) -> tuple:
    """(아직 안 고른 줄 수, 인보이스 번호) — ① 받기 전에 본다."""
    ensure(c)
    r = c.execute("SELECT COUNT(*), MAX(n.invoice_no) FROM export_price_need n LEFT JOIN export_price_ack a "
                  "ON a.invoice_no=n.invoice_no AND a.part_key=n.part_key AND a.price_key=n.price_key "
                  "WHERE n.log_id=? AND COALESCE(a.decision,'')=''", (log_id,)).fetchone()
    return (r[0] or 0), (r[1] or "")
