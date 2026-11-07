# -*- coding: utf-8 -*-
"""z1191z11 시험 — 데이터 꼬임 점검의 남은 중간 위험(대표 「남은 중간 위험도 점검 결과대로 진행해」 2026-11-07)
  E 소속 확인: 호기 일괄 상태 · 세금계산서 줄 쓰기 · 묶음 발행 — 다른 관리번호 호기·수주면 409 · 아무것도 안 씀 · 제 것은 통과
  F·G 원문: 상세 수주 머리 바뀐 칸만 · 처리기 한 번만(세금계산서 팝업 · 떠날 때 경고 · 일일업무 붙여넣기) · 사업자등록증 인식 · 정보 수정 고객 채우기 · 소모품 통화 확인
  임시 DB · TestClient · 운영 아님
"""
import contextlib
import io
import os
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z11-test-only-not-a-real-key"
import app.database as D  # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z11_")
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
                 "VALUES ('가상관리자', 'admin', 'T911', 'T911', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T911'").fetchone())
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


BASE = {"quick": "1", "customer_name": "가상고객", "biz_div": "T", "project_type": "NEW_EQUIP", "po_type": "신규", "status": "진행중",
        "confirm_now": "1", "order_date": "2026-11-04", "due_date": "2026-11-20", "currency": "KRW", "equip_name": "가상장비", "unit_qty": "1"}


def post_new(**kw):
    f = dict(BASE); f.update(kw)
    return q(cl.post, "/projects/new", data=f)


def proj(name):
    with D.db_session() as c:
        return dict(c.execute("SELECT * FROM projects WHERE name=? ORDER BY id DESC", (name,)).fetchone())


def orders_of(pid):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT * FROM orders WHERE project_id=? ORDER BY id", (pid,))]


def items_of(oid):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT * FROM order_items WHERE order_id=? ORDER BY id", (oid,))]


post_new(name="A-설비", model="MA", shipment_form="ASSEMBLY", unit_qty="2", unit_price="100", order_amount="200", **{"unit_amount[]": ["100", "100"]})
post_new(name="B-설비", model="MB", shipment_form="ASSEMBLY", unit_qty="1", unit_price="300", order_amount="300", **{"unit_amount[]": ["300"]})
PA, PB = proj("A-설비"), proj("B-설비")
OA, OB = orders_of(PA["id"])[0], orders_of(PB["id"])[0]
IA = [x["id"] for x in items_of(OA["id"])]; IB = [x["id"] for x in items_of(OB["id"])]

print("§1 호기 일괄 상태 — 다른 관리번호 수주")
r = q(cl.post, "/projects/%d/units/bulk-status" % PA["id"], data={"status": "출하", "order_id": str(OB["id"])})
check(r.status_code == 409 and all((x["unit_status"] or "진행중") != "출하" for x in items_of(OB["id"])), "A 주소로 B 수주 → 409 · B 호기 그대로")
r = q(cl.post, "/projects/%d/units/bulk-status" % PA["id"], data={"status": "보류", "order_id": str(OA["id"])})
check(r.status_code == 200 and all(x["unit_status"] == "보류" for x in items_of(OA["id"])), "제 수주는 통과")

print("§2 세금계산서 줄 쓰기(row-tax) — 다른 관리번호 호기")
r = q(cl.post, "/sales/schedule/row-tax", json={"ref_id": PA["id"], "field": "tax_invoice_date", "value": "2026-11-07", "uids": ",".join(map(str, IA + IB))})
check(r.status_code == 409 and all(x["tax_invoice_date"] in (None, "") for x in items_of(OB["id"]) + items_of(OA["id"])), "A 줄에 B 호기 섞임 → 409 · 아무 호기도 안 바뀜")
r = q(cl.post, "/sales/schedule/row-tax", json={"ref_id": PA["id"], "field": "tax_invoice_amt1", "value": "200", "uids": ",".join(map(str, IA))})
check(r.status_code == 200 and abs(sum(float(x["tax_invoice_amt1"] or 0) for x in items_of(OA["id"])) - 200) < 1e-9, "제 호기는 통과(합계 200)")

print("§3 묶음 발행 — 줄의 호기가 다른 관리번호")
line_bad = {"kind": "project", "ref_id": PA["id"], "uids": [str(i) for i in IB], "amount": 300, "customer": "가상고객", "currency": "KRW", "code": PA["mgmt_code"]}
r = q(cl.post, "/sales/schedule/tax-invoice/issue", json={"lines": [line_bad], "issue_date": "2026-11-07", "tier": 2})
with D.db_session() as c:
    nti = c.execute("SELECT COUNT(*) FROM tax_invoices").fetchone()[0]
check(r.status_code == 409 and nti == 0 and all(x["tax_invoice_date2"] in (None, "") for x in items_of(OB["id"])), "A 줄에 B 호기 → 409 · 장부·호기 모두 안 씀 — %s" % r.text[:90])
line_ok = {"kind": "project", "ref_id": PB["id"], "uids": [str(i) for i in IB], "amount": 300, "customer": "가상고객", "currency": "KRW", "code": PB["mgmt_code"]}
r = q(cl.post, "/sales/schedule/tax-invoice/issue", json={"lines": [line_ok], "issue_date": "2026-11-07", "tier": 2})
check(r.status_code == 200 and r.json().get("ok") and items_of(OB["id"])[0]["tax_invoice_date2"] == "2026-11-07", "제 호기는 발행 통과 — %s" % r.text[:90])

print("§4 원문(F·G)")
R = lambda *p: io.open(os.path.join(ROOT, "app", "templates", *p), encoding="utf-8").read()
pd, dl, cf, pf, cd = R("project_detail.html"), R("daily.html"), R("customer_form.html"), R("project_form.html"), R("consumable_detail.html")
check(pd.count("if ((inp.value || '') !== (inp.dataset.orig || '')) body.set(inp.dataset.field") == 2, "상세 수주 머리 저장 2곳: 바뀐 칸만")
check("window.__knkTiClickFn = function(e){" in pd and "if(!window.__knkTiClickBound)" in pd and "document.addEventListener('click',function(e){\n    var cell" not in pd, "세금계산서 팝업 click 처리기 한 번만")
check("window._knkCardDirtyFns = [];" in pd and "if (!window.__knkPdLeaveBound)" in pd and "if (!document.contains(card)) return false;" in pd, "떠날 때 경고: 화면마다 새 목록 · 처리기 한 번 · 떠난 카드 제외")
check("if (!window.__knkDailyPasteBound)" in dl and "window.__knkDailyPasteFn = (function(e){" in dl, "일일업무 붙여넣기 처리기 한 번만")
check("if (!document.contains(fileEl)) return;" in cf and "_bizScope.querySelector(`[name=\"${name}\"]`)" in cf, "사업자등록증 인식: 화면 있을 때만 · 그 폼 안에서만")
check("var _ieAlive=function()" in pf and "if(!_ieAlive() || !document.contains(ci)) return;" in pf, "정보 수정 고객 채우기: 그 프로젝트 화면일 때만")
check("if(!document.getElementById('coPage')) return;" in cd, "소모품 통화 확인창: 소모품 화면에서만")
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
