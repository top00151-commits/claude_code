# -*- coding: utf-8 -*-
"""z1191z124 (운영 11-24 11:49 006M2511): 프로젝트 통화를 바꿔도 입금 기록 있는·입금 완료 수주의 품목 통화는 그대로 ·
   품목 줄은 자기 수주 통화를 따른다 — project_workflow.cascade_project_meta_to_so"""
import os, sqlite3, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app import project_workflow as W
R = []
def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:200]))
c = sqlite3.connect(":memory:")
c.executescript("""
CREATE TABLE projects(id INTEGER PRIMARY KEY, currency TEXT);
CREATE TABLE orders(id INTEGER PRIMARY KEY, project_id INT, currency TEXT, status TEXT, due_date TEXT, order_date TEXT);
CREATE TABLE order_items(id INTEGER PRIMARY KEY, order_id INT, currency TEXT, due_date TEXT, order_date TEXT);
CREATE TABLE receipts_payment(id INTEGER PRIMARY KEY, order_id INT);
CREATE TABLE project_history(id INTEGER PRIMARY KEY, project_id INT, changed_by INT, field TEXT, old_value TEXT, new_value TEXT, note TEXT, changed_at TEXT);
INSERT INTO projects VALUES(1,'USD');
INSERT INTO orders VALUES(10,1,'USD','PAID',NULL,NULL);        -- 달러 수주 · 입금 완료(M-251127-2 같은)
INSERT INTO orders VALUES(11,1,'KRW','SHIPPED',NULL,NULL);     -- 원화 수주(M-260819-1 같은)
INSERT INTO orders VALUES(12,1,'USD','CONFIRMED',NULL,NULL);   -- 달러 수주 · 입금 기록 없음
INSERT INTO receipts_payment VALUES(1,10);
""")
for oid, cur, n in ((10, "USD", 5), (11, None, 2), (12, "USD", 3)):
    for _ in range(n):
        c.execute("INSERT INTO order_items(order_id, currency) VALUES(?,?)", (oid, cur))
W.cascade_project_meta_to_so(c, 1, {"currency": "USD"}, {"currency": "KRW"}, None)
def ic(oid): return sorted({r[0] for r in c.execute("SELECT COALESCE(currency,'') FROM order_items WHERE order_id=?", (oid,))})
def oc(oid): return c.execute("SELECT currency FROM orders WHERE id=?", (oid,)).fetchone()[0]
check("입금 완료·입금 기록 있는 달러 수주 10: 수주 USD · 품목 USD 그대로", oc(10) == "USD" and ic(10) == ["USD"], (oc(10), ic(10)))
# z1191z153·z154 (대표 11-25 「수주가 사실 · 퍼뜨리지 않음」): 수주가 여럿이면 통화를 퍼뜨리지 않는다 — 빈 품목 통화는 자기 수주 통화(KRW)를 따름
check("원화 수주 11: 수주 KRW 그대로 · 품목 통화 빈칸 그대로(자기 수주 통화를 따름)", oc(11) == "KRW" and ic(11) == [""], (oc(11), ic(11)))
# z1191z130: 수주 통화가 섞인 관리번호(10·12 USD + 11 KRW)는 프로젝트 통화를 바꿔도 수주 통화를 안 바꾼다
check("입금 기록 없는 달러 수주 12: 통화 섞인 관리번호라 수주 USD · 품목 USD 그대로(z130)", oc(12) == "USD" and ic(12) == ["USD"], (oc(12), ic(12)))
bad = c.execute("SELECT COUNT(*) FROM order_items oi JOIN orders o ON o.id=oi.order_id WHERE COALESCE(oi.currency,'')<>'' AND oi.currency<>o.currency").fetchone()[0]
check("수주 통화 ≠ 품목 통화 줄 0", bad == 0, bad)
print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
