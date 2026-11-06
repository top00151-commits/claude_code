# -*- coding: utf-8 -*-
"""z1191z10 시험 — 데이터 꼬임 원인 1·2·3·4·5 (대표 「1·2·3·4·5 진행해」 2026-11-06)
  1 정보 수정 저장: 화면에 없는 칸(영업담당·PM·고객PO·2단계 발주) 유지 · 비고 유지 · 수주확정 상태 유지 · 수주 있으면 초기협의로 안 바뀜 · 단가 그대로
  2 일괄 출하: 고른 줄(호기·수주)만
  3 일일업무·홈 날짜 = window.SEL_DATE (원문)
  4 호기·부품 줄 저장: 안 보낸 칸 그대로(금액·단가·비고·납기·통화)
  5 소모품 자재 연결: 남의 품목 409
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z10-test-only-not-a-real-key"
import app.database as D  # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z10_")
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
                 "VALUES ('가상관리자', 'admin', 'T910', 'T910', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T910'").fetchone())
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
        "confirm_now": "1", "order_date": "2026-11-04", "due_date": "2026-11-20", "currency": "USD", "fx_rate": "1400", "equip_name": "가상장비", "unit_qty": "1"}


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


def form_from_edit_page(h):
    """정보 수정 화면이 실제로 보내는 값(브라우저처럼) — name 있는 input·select·textarea 의 기본 값"""
    f = {}
    for mm in re.finditer(r'<input[^>]*>', h):
        tag = mm.group(0)
        nm = re.search(r'name="([^"]+)"', tag)
        if not nm:
            continue
        if re.search(r'type="(checkbox|radio|file|submit|button)"', tag) and "checked" not in tag:
            continue
        val = re.search(r'value="([^"]*)"', tag)
        f[nm.group(1)] = (val.group(1) if val else "").replace("&amp;", "&")
    for mm in re.finditer(r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>', h, re.S):
        opts = re.findall(r'<option value="([^"]*)"([^>]*)>', mm.group(2))
        sel = [v for v, a in opts if "selected" in a]
        f[mm.group(1)] = sel[0] if sel else (opts[0][0] if opts else "")
    for mm in re.finditer(r'<textarea[^>]*name="([^"]+)"[^>]*>(.*?)</textarea>', h, re.S):
        f[mm.group(1)] = mm.group(2)
    return f


print("§1 정보 수정 저장 — 수주확정 · 수주 있음")
post_new(name="정보수정-설비", model="MX", shipment_form="ASSEMBLY", unit_qty="2", unit_price="12345.67", order_amount="24691.34",
         **{"unit_amount[]": ["12345.67", "12345.67"]})
P = proj("정보수정-설비")
with D.db_session() as c:
    c.execute("UPDATE projects SET status='수주확정', sales_name='이현', pm_name='김PM', customer_po='PO-777', two_tier_order='1', logi_note='1호기/R0.1', unit_price=12345.67 WHERE id=?", (P["id"],))
h = q(cl.get, "/projects/%d/edit" % P["id"]).text
check('<option value="수주확정" selected>' in h, "상태 목록에 지금 상태 「수주확정」이 골라진 채로")
check(">1호기/R0.1</textarea>" in h, "비고 칸에 지금 비고(logi_note)")
f = form_from_edit_page(h)
check(f.get("status") == "수주확정" and "sales" not in f and "customer_po" not in f, "화면이 보내는 값: 상태=수주확정 · 영업담당·고객PO 칸 없음")
f["unlock_verified"] = "1"; f["customer_name"] = "가상고객"   # 고객사 칸은 화면 스크립트(고르기 창)가 채움
r = q(cl.post, "/projects/%d/edit" % P["id"], data=f)
P2 = proj("정보수정-설비")
check(r.status_code in (200, 303) and "error=" not in (r.headers.get("location") or ""), "저장 통과 — %s" % (r.headers.get("location") or "")[:50])
check(P2["sales_name"] == "이현" and P2["pm_name"] == "김PM" and P2["customer_po"] == "PO-777" and str(P2["two_tier_order"]) == "1", "영업담당·PM·고객PO·2단계 발주 그대로 — %s/%s/%s/%s" % (P2["sales_name"], P2["pm_name"], P2["customer_po"], P2["two_tier_order"]))
check(P2["logi_note"] == "1호기/R0.1", "비고 그대로 — %r" % P2["logi_note"])
check(P2["status"] == "수주확정", "상태 수주확정 그대로 — %s" % P2["status"])
check(abs(float(P2["unit_price"] or 0) - 12345.67) < 1e-6, "단가 12,345.67 그대로(화면 정수 12,346 저장 안 함) — %s" % P2["unit_price"])
f2 = dict(f); f2["status"] = "초기협의"
q(cl.post, "/projects/%d/edit" % P["id"], data=f2)
check(proj("정보수정-설비")["status"] == "수주확정", "수주 있는 프로젝트를 초기협의로 되돌리는 저장은 막힘")
f3 = dict(f); f3["status"] = "출하"; f3["note"] = ""
q(cl.post, "/projects/%d/edit" % P["id"], data=f3)
P3 = proj("정보수정-설비")
check(P3["status"] == "출하" and (P3["logi_note"] or "") == "", "다른 상태로 바꾸기·비고를 일부러 비우기는 그대로 반영")

print("§1b 수주 없는 프로젝트 — 초기협의 가능 · 단가 바꾸면 반영")
with D.db_session() as c:
    c.execute("INSERT INTO projects (name, customer_name, biz_div, project_type, status, unit_qty, unit_price, order_amount, currency, sales_name) "
              "VALUES ('제안-건','가상고객','T','NEW_EQUIP','견적발행',1,1000.5,1000.5,'USD','오경환')")
PN = proj("제안-건")
fN = form_from_edit_page(q(cl.get, "/projects/%d/edit" % PN["id"]).text); fN["unlock_verified"] = "1"; fN["status"] = "초기협의"; fN["customer_name"] = "가상고객"
q(cl.post, "/projects/%d/edit" % PN["id"], data=fN)
PN2 = proj("제안-건")
check(PN2["status"] == "초기협의" and PN2["sales_name"] == "오경환" and abs(float(PN2["unit_price"]) - 1000.5) < 1e-9, "수주 없음: 초기협의 저장 · 영업담당 유지 · 단가 1000.5(표시 1,001) 그대로 — %s %s %s" % (PN2["status"], PN2["sales_name"], PN2["unit_price"]))
fN["unit_price"] = "2000"
q(cl.post, "/projects/%d/edit" % PN["id"], data=fN)
check(abs(float(proj("제안-건")["unit_price"]) - 2000) < 1e-9, "실제로 바꾼 단가(2,000)는 반영")

print("§2 일괄 출하 — 고른 줄만")
post_new(name="출하-설비", model="M1", shipment_form="ASSEMBLY", unit_qty="2", unit_price="100", order_amount="200", currency="KRW", **{"unit_amount[]": ["100", "100"]})
PS = proj("출하-설비")
post_new(name="출하-설비", po_type="추가", mgmt_code=PS["mgmt_code"], model="M1", shipment_form="ASSEMBLY", unit_qty="2", unit_price="100", order_amount="200", currency="KRW", **{"unit_amount[]": ["100", "100"]})
O1, O2 = orders_of(PS["id"])[:2]
I2 = [x["id"] for x in items_of(O2["id"])]
r = q(cl.post, "/sales/schedule/bulk-ship", json={"items": [{"kind": "project", "ref_id": PS["id"], "uids": I2, "so_oid": O2["id"]}]})
st1 = [x["unit_status"] or "진행중" for x in items_of(O1["id"])]; st2 = [x["unit_status"] for x in items_of(O2["id"])]
check(r.json().get("ok") and all(s == "출하" for s in st2) and all(s != "출하" for s in st1), "추가 수주 줄만 골라 출하 → 그 수주 호기만 출하 · 1차 수주 그대로 — %s / %s" % (st1, st2))
r = q(cl.post, "/sales/schedule/bulk-ship", json={"items": [{"kind": "project", "ref_id": PS["id"], "uids": [], "so_oid": O1["id"]}]})
check(all(x["unit_status"] == "출하" for x in items_of(O1["id"])), "수주 번호만 보내면 그 수주 호기만")
post_new(name="출하-단일", model="M2", shipment_form="ASSEMBLY", unit_qty="1", unit_price="100", order_amount="100", currency="KRW", **{"unit_amount[]": ["100"]})
PU = proj("출하-단일")
q(cl.post, "/sales/schedule/bulk-ship", json={"items": [{"kind": "project", "ref_id": PU["id"]}]})
check(all(x["unit_status"] == "출하" for o in orders_of(PU["id"]) for x in items_of(o["id"])), "옛 방식(번호 없이)은 예전처럼 관리번호 전체")
post_new(name="출하-남의", model="M3", shipment_form="ASSEMBLY", unit_qty="1", unit_price="100", order_amount="100", currency="KRW", **{"unit_amount[]": ["100"]})
PX = proj("출하-남의"); IX = items_of(orders_of(PX["id"])[0]["id"])[0]["id"]
q(cl.post, "/sales/schedule/bulk-ship", json={"items": [{"kind": "project", "ref_id": PU["id"], "uids": [IX]}]})
check((items_of(orders_of(PX["id"])[0]["id"])[0]["unit_status"] or "진행중") != "출하", "다른 관리번호 호기 번호를 보내도 안 바뀜(관리번호 소속만)")

print("§3 일일업무·홈 날짜(원문)")
dly = io.open(os.path.join(ROOT, "app", "templates", "daily.html"), encoding="utf-8").read()
hom = io.open(os.path.join(ROOT, "app", "templates", "home.html"), encoding="utf-8").read()
bare = lambda s: [l for l in s.splitlines() if re.search(r'(?<![\w.])SEL_DATE\b', l) and not l.strip().startswith("//") and "window.SEL_DATE" not in l]
check(not bare(dly) and dly.count("window.SEL_DATE") >= 5, "일일업무: 날짜는 모두 window.SEL_DATE")
check(not bare(hom) and "const SEL_DATE" not in hom, "홈: const SEL_DATE 없음 · 날짜는 window.SEL_DATE")

print("§4 호기·부품 줄 저장 — 안 보낸 칸 그대로")
post_new(name="호기-설비", model="M4", shipment_form="ASSEMBLY", unit_qty="1", unit_price="1500.25", order_amount="1500.25", **{"unit_amount[]": ["1500.25"]})
PH = proj("호기-설비"); OH = orders_of(PH["id"])[0]; IH = items_of(OH["id"])[0]
with D.db_session() as c:
    c.execute("UPDATE order_items SET line_note='처음 비고', due_date='2026-12-31', currency='EUR' WHERE id=?", (IH["id"],))
r = q(cl.post, "/sales/orders/items/%d/edit" % IH["id"], data={"note": "비고만 고침"})
I1 = items_of(OH["id"])[0]
check(r.status_code == 200 and I1["line_note"] == "비고만 고침", "비고만 보내면 비고 저장 — %s" % r.text[:80])
check(abs(float(I1["amount"]) - 1500.25) < 1e-9 and abs(float(I1["unit_price"]) - 1500.25) < 1e-9, "금액·단가 그대로(예전엔 금액 0 또는 표시값) — %s / %s" % (I1["amount"], I1["unit_price"]))
check(I1["due_date"] == "2026-12-31" and I1["currency"] == "EUR", "호기 납기·통화 덮어쓰기 그대로 — %s %s" % (I1["due_date"], I1["currency"]))
r = q(cl.post, "/sales/orders/items/%d/edit" % IH["id"], data={"amount": "1700"})
I2b = items_of(OH["id"])[0]
check(abs(float(I2b["amount"]) - 1700) < 1e-9 and abs(float(I2b["unit_price"]) - 1700) < 1e-9 and I2b["line_note"] == "비고만 고침", "금액만 보내면 금액·단가(호기 규칙) 저장 · 비고 그대로")
with D.db_session() as c:
    c.execute("UPDATE order_items SET unit_price=755.5625, amount=6044.5, qty=8 WHERE id=?", (IH["id"],))
q(cl.post, "/sales/orders/items/%d/edit" % IH["id"], data={"note": "부품 비고"})
I3 = items_of(OH["id"])[0]
check(abs(float(I3["unit_price"]) - 755.5625) < 1e-9 and abs(float(I3["amount"]) - 6044.5) < 1e-9, "부품식(단가≠금액) 줄도 비고만 고치면 단가 755.5625·금액 그대로")
pdh = io.open(os.path.join(ROOT, "app", "templates", "project_detail.html"), encoding="utf-8").read()
check("if (_dzN(r.amtInp)) body.set('amount'" in pdh and "if (_dz(r.noteInp)) body.set('note'" in pdh and "if (_dz(r.costInp)) {" in pdh, "화면: 줄 안에서 바뀐 칸만 보냄(원문)")

print("§5 소모품 자재 연결 — 남의 품목 409")
with D.db_session() as c:
    for no in ("C-A", "C-B"):
        c.execute("INSERT INTO consumable_orders (co_no, customer_name, currency, total_amount, status, mgmt_code) VALUES (?,?,?,?,?,?)", (no, "가상고객", "USD", 0, "CONFIRMED", no))
    ca = c.execute("SELECT id FROM consumable_orders WHERE co_no='C-A'").fetchone()[0]
    cb = c.execute("SELECT id FROM consumable_orders WHERE co_no='C-B'").fetchone()[0]
    c.execute("INSERT INTO consumable_order_items (co_id, line_no, part_name, qty, unit_price, amount) VALUES (?,?,?,?,?,?)", (cb, 1, "B품목", 1, 1, 1))
    ib = c.execute("SELECT id FROM consumable_order_items WHERE co_id=?", (cb,)).fetchone()[0]
r = q(cl.post, "/consumables/%d/items/%d/match-part" % (ca, ib), data={"part_id": "1"})
with D.db_session() as c:
    pid_b = c.execute("SELECT part_id FROM consumable_order_items WHERE id=?", (ib,)).fetchone()[0]
check(r.status_code == 409 and pid_b is None, "A 주소로 B 품목 자재 연결 → 409 · 안 바뀜")
r = q(cl.post, "/consumables/%d/items/%d/match-part" % (cb, ib), data={"part_id": ""})
check(r.status_code == 200, "자기 품목은 통과")
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
