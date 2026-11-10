# -*- coding: utf-8 -*-
"""z1191z13 시험 — 대표 「내가 변경한 적 없는데 내 이름이야」(2026-11-10) → 「1,2번 진행해」 중 2번
  작업일정표 「전체에서 찾기」(cust=, 전 기간) 가
  ① 기타사항(호기 비고·프로젝트 기타사항·소모품 기타사항) ② 화면에 안 보이는 비고(상품 부품 비고·소모품 품목 비고·
     3개 넘어 「외N」으로 잘린 비고) ③ 화면 글자 칸(고객사2·담당자·납품위치·영업담당자 …) 으로도 찾고
  ④ 검색칸 안내 문구 · 이 화면 거르기(JS)가 숨은 비고(data-find)도 보고 · 엑셀 저장 찾기도 같음 · 없는 글자는 0건
  임시 DB · TestClient · 운영 아님
"""
import contextlib
import io
import os
import re
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z13-test-only-not-a-real-key"
import app.database as D  # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z13_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상관리자', 'admin', 'T908', 'T908', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T908'").fetchone())
    conn.execute("INSERT INTO customers (name) VALUES ('가상고객')")
import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

M.get_user = lambda request: ADMIN
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0


def check(cond, msg):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", msg)
    else:
        FAIL += 1; print("  ❌", msg)




def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


# 지난 달(2025-03) 자료 — 이번 달 화면엔 없고 「전체에서 찾기」(cust=)로만 찾힌다
BASE = {"quick": "1", "customer_name": "가상고객", "biz_div": "M", "project_type": "NEW_EQUIP", "po_type": "신규", "status": "진행중",
        "confirm_now": "1", "order_date": "2025-03-04", "due_date": "2025-03-20", "currency": "KRW", "equip_name": "가상장비", "unit_qty": "1"}


def post_new(**kw):
    f = dict(BASE); f.update(kw)
    return q(cl.post, "/projects/new", data=f)


def proj(name):
    with D.db_session() as c:
        return dict(c.execute("SELECT * FROM projects WHERE name=? ORDER BY id DESC", (name,)).fetchone())


def hist(pid, field):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT * FROM project_history WHERE project_id=? AND field=? ORDER BY id", (pid, field))]


print("[1] 등록은 사람 이름 그대로(사람이 한 일)")
post_new(name="Z13가", model="MZ13", shipment_form="ASSEMBLY", unit_qty="1", unit_price="1000000", order_amount="1000000", **{"unit_amount[]": ["1000000"]})
P1 = proj("Z13가")
h = hist(P1["id"], "프로젝트")
check(h and h[0]["changed_by"] == ADMIN["id"], "신규 등록 이력 변경자 = 등록한 사람(%s)" % (h and h[0]["changed_by"]))

print("[2] 상세 화면 수주액 자가치유 → 변경자 시스템 · 메모에 화면 연 사람")
with D.db_session() as c:
    c.execute("UPDATE projects SET order_amount=? WHERE id=?", (777, P1["id"]))
r = q(cl.get, "/project/%d" % P1["id"])
check(r.status_code == 200, "상세 200 (%s)" % r.status_code)
h = hist(P1["id"], "수주액(자가치유)")
check(len(h) == 1, "자가치유 이력 1줄 (%d)" % len(h))
check(h and h[-1]["changed_by"] is None, "자가치유 변경자 = None(시스템)")
check(h and h[-1]["note"] == "v5H130 SO 합계 기준 자동 정정 · 화면 연 사람: 가상관리자", "메모 = 자동 정정 + 화면 연 사람 (%r)" % (h and h[-1]["note"]))
check(proj("Z13가")["order_amount"] == 1000000, "수주액은 그대로 맞춰짐(1,000,000)")
hl = D.get_project_history(P1["id"])
row = [x for x in hl if x["field"] == "수주액(자가치유)"]
check(row and row[0]["changed_by_name"] == "시스템", "이력 화면 변경자 = 「시스템」")
r2 = q(cl.get, "/project/%d" % P1["id"])
check(len(hist(P1["id"], "수주액(자가치유)")) == 1, "다시 열어도 같으면 이력 안 늘어남")

print("[3] 상세 화면 누락 SO 자동 발행 → 변경자 시스템")
with D.db_session() as c:
    cid = c.execute("SELECT id FROM customers WHERE name='가상고객'").fetchone()[0]
    c.execute("INSERT INTO projects (code, name, customer_id, customer_name, status, mgmt_code, biz_div, project_type, order_amount, unit_qty, unit_price, order_date, due_date, currency) "
              "VALUES ('Z13N','Z13나',?, '가상고객','진행중','998M2503','M','NEW_EQUIP',2000000,2,1000000,'2025-03-04','2025-03-20','KRW')", (cid,))
    P2 = c.execute("SELECT id FROM projects WHERE name='Z13나'").fetchone()[0]
r = q(cl.get, "/project/%d" % P2)
check(r.status_code == 200, "상세 200 (%s)" % r.status_code)
with D.db_session() as c:
    nso = c.execute("SELECT COUNT(*) FROM orders WHERE project_id=?", (P2,)).fetchone()[0]
check(nso == 1, "누락 SO 자동 발행됨 (%d)" % nso)
h = hist(P2, "수주발행(자동)")
check(len(h) == 1 and h[0]["changed_by"] is None, "자동 발행 이력 변경자 = None(시스템)")
check(h and h[0]["note"].endswith(" · 화면 연 사람: 가상관리자"), "자동 발행 메모 끝 = 화면 연 사람 (%r)" % (h and h[0]["note"]))

print("[4] 이름 없는 사용자 → 메모에 꼬리 안 붙음")
check(M._heal_by_z13({"id": 1}) == "" and M._heal_by_z13(None) == "" and M._heal_by_z13({"name": " 홍길동 "}) == " · 화면 연 사람: 홍길동", "_heal_by_z13 꼬리")

print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
