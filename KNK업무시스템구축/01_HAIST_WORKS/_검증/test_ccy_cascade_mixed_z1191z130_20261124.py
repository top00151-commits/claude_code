# -*- coding: utf-8 -*-
"""z1191z130 (대표 11-24 「1. 진행」): 프로젝트 정보 수정 통화 변경 → 수주 통화 퍼뜨리기
   ① 수주 통화가 섞인 관리번호 = 수주 통화 하나도 안 바꿈 ② 모두 같을 때만 옛 통화 수주를 새 통화로
   ③ 계산서 발행(INVOICED)·입금 완료(PAID)·취소(CANCELLED)·입금 기록 있는 수주는 그대로 ④ 품목 줄 = 자기 수주 통화"""
import os, sqlite3, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app import project_workflow as W
R = []
def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:200]))
SCHEMA = """
CREATE TABLE projects(id INTEGER PRIMARY KEY, currency TEXT);
CREATE TABLE orders(id INTEGER PRIMARY KEY, project_id INT, currency TEXT, status TEXT, due_date TEXT, order_date TEXT);
CREATE TABLE order_items(id INTEGER PRIMARY KEY, order_id INT, currency TEXT, due_date TEXT, order_date TEXT);
CREATE TABLE receipts_payment(id INTEGER PRIMARY KEY, order_id INT);
CREATE TABLE project_history(id INTEGER PRIMARY KEY, project_id INT, changed_by INT, field TEXT, old_value TEXT, new_value TEXT, note TEXT, changed_at TEXT);
"""
def mk(sos):
    c = sqlite3.connect(":memory:"); c.executescript(SCHEMA)
    c.execute("INSERT INTO projects VALUES(1,'USD')")
    for oid, ccy, st in sos:
        c.execute("INSERT INTO orders(id, project_id, currency, status) VALUES(?,?,?,?)", (oid, 1, ccy, st))
        for _ in range(2):
            c.execute("INSERT INTO order_items(order_id, currency) VALUES(?,?)", (oid, ccy))
    return c
def oc(c, oid): return c.execute("SELECT currency FROM orders WHERE id=?", (oid,)).fetchone()[0]
def ic(c, oid): return sorted({r[0] for r in c.execute("SELECT COALESCE(currency,'') FROM order_items WHERE order_id=?", (oid,))})
# ① 섞임(USD 2 + KRW 1) → USD→KRW 로 바꿔도 수주 통화 그대로
c = mk([(1, "USD", "CONFIRMED"), (2, "USD", "SHIPPED"), (3, "KRW", "CONFIRMED")])
s = W.cascade_project_meta_to_so(c, 1, {"currency": "USD"}, {"currency": "KRW"}, None)
check("① 통화 섞인 관리번호: 달러 수주 1·2 그대로 USD", oc(c, 1) == "USD" and oc(c, 2) == "USD" and ic(c, 1) == ["USD"], (oc(c, 1), oc(c, 2), ic(c, 1)))
check("① 원화 수주 3 그대로 KRW", oc(c, 3) == "KRW", oc(c, 3))
check("① 이력 요약에 「섞여 있어 그대로」", any("섞여 있어" in x for x in (s or [])), s)
# ② 모두 USD → KRW: 진행 수주는 바뀜 · 계산서·입금 완료·취소·입금 기록은 그대로
c = mk([(1, "USD", "CONFIRMED"), (2, "USD", "INVOICED"), (3, "USD", "PAID"), (4, "USD", "CANCELLED"), (5, "USD", "SHIPPED")])
c.execute("INSERT INTO receipts_payment(order_id) VALUES(5)")
W.cascade_project_meta_to_so(c, 1, {"currency": "USD"}, {"currency": "KRW"}, None)
check("② 한 통화 관리번호: 진행 수주 1 → KRW · 품목도 KRW", oc(c, 1) == "KRW" and ic(c, 1) == ["KRW"], (oc(c, 1), ic(c, 1)))
check("② 계산서 발행 수주 2 그대로 USD", oc(c, 2) == "USD" and ic(c, 2) == ["USD"], (oc(c, 2), ic(c, 2)))
check("② 입금 완료 3 · 취소 4 그대로 USD", oc(c, 3) == "USD" and oc(c, 4) == "USD", (oc(c, 3), oc(c, 4)))
check("② 입금 기록 있는 수주 5 그대로 USD", oc(c, 5) == "USD" and ic(c, 5) == ["USD"], (oc(c, 5), ic(c, 5)))
bad = c.execute("SELECT COUNT(*) FROM order_items oi JOIN orders o ON o.id=oi.order_id WHERE oi.currency<>o.currency").fetchone()[0]
check("④ 수주 통화 ≠ 품목 통화 줄 0", bad == 0, bad)
# ③ 섞임 판단에서 취소 수주는 빼고 본다(취소 KRW + 진행 USD = 한 통화)
c = mk([(1, "USD", "CONFIRMED"), (2, "KRW", "CANCELLED")])
W.cascade_project_meta_to_so(c, 1, {"currency": "USD"}, {"currency": "KRW"}, None)
check("③ 취소 수주는 섞임에서 뺌: 진행 수주 1 → KRW · 취소 수주 2 그대로", oc(c, 1) == "KRW" and oc(c, 2) == "KRW", (oc(c, 1), oc(c, 2)))
print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
