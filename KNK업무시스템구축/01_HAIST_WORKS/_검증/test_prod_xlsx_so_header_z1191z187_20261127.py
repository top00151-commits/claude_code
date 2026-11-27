# -*- coding: utf-8 -*-
"""z1191z187 (대표 11-27 「3번 진행해」) — 상품 양식(수주 엑셀)
   §1 채워진 양식 내려받기 머리 = 그 수주 값(1차 고객·2차·PO유형·모델·발주일·거래구분) — 관리번호 처음 등록 값 아님
   §2 받은 그대로 다시 올리기 = 바뀌는 칸 없음 → 확인 없이 저장 · 수주 2개+ = 관리번호 처음 등록 값(고객·통화) 그대로
   §3 엑셀 머리에서 거래구분을 바꾸면 = 먼저 「확인 필요」(아무것도 안 바뀜) → 확인(hdr_ok=1) 뒤 저장 · 이력"""
import contextlib, io, os, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z187-test-only-not-a-real-key"   # 시험용 가짜 값
import app.database as D   # noqa: E402
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_z187_"), "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
OK = FAIL = 0


def check(cond, msg, got=None):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", msg)
    else:
        FAIL += 1; print("  ❌", msg, " ←", got)


def ins(c, t, d):
    cols = {r[1] for r in c.execute("PRAGMA table_info(%s)" % t)}
    ks = [k for k in d if k in cols]
    c.execute("INSERT INTO %s (%s) VALUES (%s)" % (t, ",".join('"%s"' % k for k in ks), ",".join("?" * len(ks))), [d[k] for k in ks])
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("biz_divs", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    TEAM = ins(c, "teams", {"name": "기술영업팀", "code": "01", "entity": "KOR", "display_order": 1})
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, can_view_sales, can_use_sales, "
              "can_view_logistics, can_use_logistics) VALUES ('가상대표', 'ceo', 'Z187', 'Z187', 'sso_only_no_local_password', 1, 1, ?, 1, 1, 1, 1)", (TEAM,))
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='Z187'").fetchone())
    c.execute("INSERT OR IGNORE INTO field_access_policy (category, team_id) VALUES ('sales_amount', ?)", (TEAM,))
    CK = ins(c, "customers", {"name": "국내전자(주)"})
    CA = ins(c, "customers", {"name": "ALPHA VIETNAM CO LTD"})
    P = ins(c, "projects", {"code": "908M2611", "mgmt_code": "908M2611", "name": "가상 상품", "customer_id": CK, "customer_name": "국내전자(주)",
                            "po_type": "신규", "is_export": 0, "currency": "KRW", "order_date": "2026-01-01", "status": "진행중", "biz_div": "M",
                            "project_type": "PARTS", "shipment_form": "PARTS", "is_archived": 0, "model_name": "처음모델"})
    O1 = ins(c, "orders", {"project_id": P, "order_no": "M-260101-1", "customer_id": CK, "currency": "KRW", "total_amount": 1000, "status": "CONFIRMED",
                           "po_type": "신규", "order_date": "2026-01-01", "so_type": "PARTS_EXPORT"})
    ins(c, "order_items", {"order_id": O1, "qty": 1, "unit_price": 1000, "amount": 1000, "unit_label": "국내부품", "is_export": 0, "currency": "KRW", "unit_status": "진행중"})
    O2 = ins(c, "orders", {"project_id": P, "order_no": "M-261101-1", "customer_id": CA, "currency": "USD", "total_amount": 200, "status": "CONFIRMED",
                           "po_type": "추가", "order_date": "2026-11-01", "due_date": "2026-12-01", "so_type": "PARTS_EXPORT", "end_customer": "SEV",
                           "model_name": "둘째모델"})
    ins(c, "order_items", {"order_id": O2, "qty": 2, "unit_price": 100, "amount": 200, "unit_label": "수출부품", "is_export": 1, "currency": "USD",
                           "unit_status": "진행중", "invoice_unit_price_usd": 100})

import app.main as M   # noqa: E402
from fastapi.testclient import TestClient   # noqa: E402
M.get_user = lambda request: ADMIN
with contextlib.redirect_stdout(io.StringIO()):
    try:
        M.startup()
    except Exception as _e:
        print("startup:", _e)
cl = TestClient(M.app)
import openpyxl   # noqa: E402

print("§1 채워진 양식 머리 = 그 수주 값")
r = cl.get("/projects/import-product-template?so_id=%d" % O2)
raw = r.content
wb = openpyxl.load_workbook(io.BytesIO(raw))
ws = wb.worksheets[0]
cells = {}
for row in ws.iter_rows():
    for cc in row:
        if isinstance(cc.value, str) and cc.value.strip():
            cells[(cc.row, cc.column)] = cc.value.strip()
vals = set(cells.values())


def near(label):
    for (rr, cc), v in cells.items():
        if v == label:
            return cells.get((rr, cc + 1))   # 머리 칸 = 라벨 오른쪽 값
    return None


check(r.status_code == 200 and "ALPHA VIETNAM CO LTD" in vals and "국내전자(주)" not in vals, "1차 고객 = 수주 고객(ALPHA) · 처음 등록 고객(국내전자) 아님", [v for v in vals if "CO" in v or "전자" in v][:5])
check("SEV" in vals and "추가" in vals and "둘째모델" in vals and "처음모델" not in vals, "2차 SEV · PO유형 추가 · 모델 = 수주 값", sorted(v for v in vals if len(v) < 12)[:30])
check(near("거래구분") == "수출", "거래구분 = 수주 품목(수출)", near("거래구분"))
print("§2 받은 그대로 다시 올리기 = 확인 없이 · 관리번호 처음 값 그대로")
up = cl.post("/sales/orders/%d/overwrite-product" % O2, files={"xlsx": ("상품양식.xlsx", raw, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
             data={"mode": "replace"})
j = up.json()
with D.db_session() as c:
    pr = dict(c.execute("SELECT customer_id, customer_name, currency, is_export, model_name FROM projects WHERE id=?", (P,)).fetchone())
    o2 = dict(c.execute("SELECT currency, po_type FROM orders WHERE id=?", (O2,)).fetchone())
check(j.get("ok") and not j.get("need_hdr_ok"), "바뀌는 칸 없음 = 바로 저장", up.text[:200])
check(pr["customer_id"] == CK and pr["currency"] == "KRW" and int(pr["is_export"] or 0) == 0 and pr["model_name"] == "처음모델",
      "수주 2개 = 관리번호 처음 등록 값(고객·통화·거래구분·모델) 그대로", pr)
check(o2["currency"] == "USD" and o2["po_type"] == "추가", "수주 통화·PO유형 그대로", o2)
print("§3 거래구분을 바꾸면 먼저 확인")
for (rr, cc), v in list(cells.items()):
    if v == "거래구분":
        tgt = ws.cell(rr, cc + 1)
        tgt.value = "내수"
        break
b2 = io.BytesIO(); wb.save(b2)
up = cl.post("/sales/orders/%d/overwrite-product" % O2, files={"xlsx": ("상품양식.xlsx", b2.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
             data={"mode": "replace"})
j = up.json()
with D.db_session() as c:
    o2c = c.execute("SELECT currency FROM orders WHERE id=?", (O2,)).fetchone()[0]
check(j.get("need_hdr_ok") and {x["f"] for x in j.get("hdr_changes") or []} >= {"거래구분", "통화"} and o2c == "USD",
      "거래구분 수출→내수(통화 USD→KRW 함께) = 먼저 확인 필요 · 아직 안 바뀜", (up.text[:200], o2c))
up = cl.post("/sales/orders/%d/overwrite-product" % O2, files={"xlsx": ("상품양식.xlsx", b2.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
             data={"mode": "replace", "hdr_ok": "1"})
with D.db_session() as c:
    o2c = c.execute("SELECT currency FROM orders WHERE id=?", (O2,)).fetchone()[0]
    h = c.execute("SELECT field, old_value, new_value FROM project_history WHERE project_id=? AND note LIKE 'z1191z187%'", (P,)).fetchall()
check(up.json().get("ok") and o2c == "KRW" and any("거래구분" in x[0] for x in h), "확인하면 저장 · 이력(수주 거래구분 전→후)", (up.text[:120], o2c, h))
t = open(os.path.join(ROOT, "app", "templates", "project_detail.html"), encoding="utf-8").read()
check("j.need_hdr_ok" in t and "fd.append('hdr_ok', '1')" in t, "화면: 확인 창 → 확인하면 다시 보냄")
print()
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
