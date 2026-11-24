# -*- coding: utf-8 -*-
"""z1191z122 (대표 11-24 「1번 진행」 · 운영 32건: 작업일정표 = 출하 · 수주 카드 = 수주)
   수주마다 호기 상태에 수주 상태 맞추기 — project_workflow.sync_so_status_from_units / cascade_unit_status_to_project(order_ids)
   + 엑셀(전체 교체·부품 추가·상품 등록·값만 고치기) 뒤에도 맞춤 · 상세 「⚠ 호기는 모두 출하」 · 전체 교체 완료 창 「확인할 줄」 (글자 검사)"""
import os, sqlite3, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app import project_workflow as W
R = []
def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:200]))
def mk():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE projects(id INTEGER PRIMARY KEY, status TEXT, stage TEXT)")
    c.execute("CREATE TABLE orders(id INTEGER PRIMARY KEY, project_id INT, status TEXT, updated_at TEXT)")
    c.execute("CREATE TABLE order_items(id INTEGER PRIMARY KEY, order_id INT, unit_status TEXT)")
    c.execute("CREATE TABLE order_status_history(id INTEGER PRIMARY KEY, order_id INT, from_status TEXT, to_status TEXT, changed_by INT, note TEXT)")
    c.execute("INSERT INTO projects VALUES(1,'진행중','진행중')")
    # 수주 10: 호기 모두 출하·CONFIRMED / 11: 섞임 / 12: 모두 진행중·SHIPPED / 13: 모두 출하·PAID / 14: 모두 출하·CONFIRMED(다른 수주)
    for oid, st, us in ((10, "CONFIRMED", ["출하", "출하"]), (11, "CONFIRMED", ["출하", "진행중"]), (12, "SHIPPED", ["진행중"]),
                        (13, "PAID", ["출하"]), (14, "CONFIRMED", ["출하"])):
        c.execute("INSERT INTO orders VALUES(?,?,?,NULL)", (oid, 1, st))
        for u in us:
            c.execute("INSERT INTO order_items(order_id, unit_status) VALUES(?,?)", (oid, u))
    return c
def st(c, oid): return c.execute("SELECT status FROM orders WHERE id=?", (oid,)).fetchone()[0]
c = mk(); n = W.sync_so_status_from_units(c, 1, None)
check("관리번호 전체: 바뀐 수주 3개(10·12·14)", n == 3, n)
check("10 호기 모두 출하 → SHIPPED", st(c, 10) == "SHIPPED", st(c, 10))
check("11 섞임 → 그대로 CONFIRMED", st(c, 11) == "CONFIRMED", st(c, 11))
check("12 출하였는데 호기 모두 진행중 → IN_PRODUCTION", st(c, 12) == "IN_PRODUCTION", st(c, 12))
check("13 입금 완료(PAID) → 그대로", st(c, 13) == "PAID", st(c, 13))
check("이력에 「호기 상태에 맞춤 … z1191z122」", c.execute("SELECT COUNT(*) FROM order_status_history WHERE note LIKE '%z1191z122%'").fetchone()[0] == 3)
c = mk(); n = W.sync_so_status_from_units(c, 1, None, order_ids=[10])
check("order_ids=[10] → 10만 바뀜 · 14(다른 수주)는 그대로", st(c, 10) == "SHIPPED" and st(c, 14) == "CONFIRMED" and n == 1, (st(c, 10), st(c, 14), n))
c = mk(); W.cascade_unit_status_to_project(c, 1, None, order_ids=[10])
check("cascade(order_ids=[10]) — 관리번호 호기가 섞여 있으면 14 는 그대로", st(c, 10) == "SHIPPED" and st(c, 14) == "CONFIRMED", (st(c, 10), st(c, 14)))
# 글자 검사 — 부르는 곳
M = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check("상품 엑셀(전체 교체·부품 추가) 뒤 맞춤", '_pwf.sync_so_status_from_units(c, pid, u.get("id"), order_ids=[oid])' in M)
check("상품 등록 뒤 맞춤", '_pwf.sync_so_status_from_units(c, int(new_pid), u.get("id"), order_ids=[oid])' in M)
check("값만 고치기 뒤 맞춤", M.count("_pwf.sync_so_status_from_units(") >= 3)
check("작업일정표 상태 변경 = 상태 바꾼 수주만", "order_ids=[r[0] for r in c.execute(f\"SELECT DISTINCT order_id FROM order_items WHERE id IN ({_ph2})\", _apply)" in M)
check("전체 교체 응답에 확인할 줄(checks)", '"checks": locals().get("_checks122") or []' in M)
T = open(os.path.join(ROOT, "app", "templates", "project_detail.html"), encoding="utf-8").read()
check("상세 수주 카드 「⚠ 호기는 모두 출하」 알림", "so-st-diff122" in T and "⚠ 호기는 모두 출하" in T)
check("전체 교체 완료 창에 「확인할 줄」", "_ckm122" in T and "확인할 줄 ' + _ck122.length" in T)
print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
