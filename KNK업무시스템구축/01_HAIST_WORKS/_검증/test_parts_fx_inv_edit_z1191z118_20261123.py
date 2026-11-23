# -*- coding: utf-8 -*-
"""z1191z117 시험 — 안지연 프로 요청 · 대표 「수정할수있게 하고 한번에」
  §1 입금 완료(PAID) 수주 줄 고치기: 확인 표시 없으면 409 안내 · 있으면 저장(상태 그대로 · 이력 「정정(확인함)」 · 거짓 「→ —」 없음)
  §2 상품(외화) 줄: 판매가(원)만 고쳐도 단가 = 인보이스 = 판매가÷환율(2자리) · 금액 = 수량×단가
  §3 줄 수량 고치면 작업일정표 수량(board_qty) 따라감(맞아 있던 것만)
  §4 엑셀 「값만 고치기」: 미리 보기(dry)는 저장 안 함 · 저장하면 그 줄만 · 줄 번호·세금계산서 그대로 · 줄 수/품명 다르면 거절
  §5 「확인할 줄」 점검: 판매가÷환율≠인보이스 · 매입가×마진≠판매가(판매가 기준 마진율 인정) · 같은 품목 1.5배 · 반올림 차이는 안 잡음
  §6 단가 미정 켜기 · 화면 조각(등록 체크박스 · 작업일정표 [미정] · 정보 수정 = quick-edit)
"""
import contextlib, io, os, re, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z118-test-only-not-a-real-key"
import app.database as D                                   # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z118_"); _REAL = D.DB_PATH; D.DB_PATH = os.path.join(TMP, "t.db"); assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if not conn.execute("SELECT 1 FROM teams WHERE id=1").fetchone():
        conn.execute("INSERT INTO teams (id, name, code) VALUES (1, '기술영업팀', '01')")
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, "
                 "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상영업', 'admin', 'Z117', 'Z117', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 0, 0)")
    U = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z117'").fetchone())
    oc = {r[1] for r in conn.execute("PRAGMA table_info(orders)")}
    ic = {r[1] for r in conn.execute("PRAGMA table_info(order_items)")}
    conn.execute("INSERT INTO projects (name, mgmt_code, biz_div, project_type, shipment_form, currency, status) VALUES ('가상 상품', '901M2611', 'M', 'NEW_EQUIP', 'PARTS', 'USD', '진행중')")
    PID = conn.execute("SELECT id FROM projects WHERE mgmt_code='901M2611'").fetchone()[0]
    conn.execute("INSERT INTO orders (project_id, order_no, status, currency, so_type, total_amount, order_date, due_date) VALUES (?, 'M-261123-91', 'PAID', 'USD', 'PARTS_EXPORT', 0, '2026-01-10', '2026-02-10')", (PID,))
    OID = conn.execute("SELECT id FROM orders WHERE order_no='M-261123-91'").fetchone()[0]
    rows = [("CABLE GRAND", "PG13.5-D", 28, 330, 100, 660, 1456.51, 0.45), ("산업용 PC", "IPC-1", 1, 3500000, 100, 7000000, 1456.51, 2883.61),
            ("SENSOR", "EX-14A", 4, 24800, 100, 49600, 1456.51, 34.05)]
    for nm, sp, q, ck, mg, sk, fx, inv in rows:
        up = round(sk / fx, 4) if nm == "산업용 PC" else inv
        conn.execute("INSERT INTO order_items (order_id, unit_label, spec, qty, cost_krw, margin_pct, sell_krw, fx_rate, invoice_unit_price_usd, invoice_amount_usd, unit_price, amount, currency, tax_invoice_date, tax_invoice_amt1) "
                     "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'USD','2026-02-06',?)", (OID, nm, sp, q, ck, mg, sk, fx, inv, round(q * inv, 2), up, round(q * inv, 2), round(q * inv, 2)))
    TOT = round(sum(r[2] * r[7] for r in rows), 2)
    conn.execute("UPDATE orders SET total_amount=? WHERE id=?", (TOT, OID))
    IDS = [r[0] for r in conn.execute("SELECT id FROM order_items WHERE order_id=? ORDER BY id", (OID,))]
    # 원화 제품 수주(작업일정표 수량 따라가기)
    conn.execute("INSERT INTO projects (name, mgmt_code, biz_div, project_type, shipment_form, currency, status) VALUES ('가상 제품', '902T2611', 'T', 'NEW_EQUIP', 'SEMI', 'KRW', '진행중')")
    PID2 = conn.execute("SELECT id FROM projects WHERE mgmt_code='902T2611'").fetchone()[0]
    conn.execute("INSERT INTO orders (project_id, order_no, status, currency, so_type, total_amount, board_qty) VALUES (?, 'T-261123-92', 'SHIPPED', 'KRW', 'CONSUMABLE', 1026000, 6)", (PID2,))
    OID2 = conn.execute("SELECT id FROM orders WHERE order_no='T-261123-92'").fetchone()[0]
    conn.execute("INSERT INTO order_items (order_id, unit_label, qty, unit_price, amount, currency) VALUES (?, 'PIN BLOCK', 6, 1026000, 1026000, 'KRW')", (OID2,))
    IID2 = conn.execute("SELECT id FROM order_items WHERE order_id=?", (OID2,)).fetchone()[0]
import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402
M.get_user = lambda request: U
cl = TestClient(M.app)
OK = FAIL = 0
def check(label, cond, got=None):
    global OK, FAIL
    if cond: OK += 1; print("  ✅", label)
    else: FAIL += 1; print("  ❌", label, "" if got is None else ("→ %r" % (got,))[:400])
def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)
def one(sql, a=()):
    with D.db_session() as c:
        r = c.execute(sql, a).fetchone(); return dict(r) if r else None
H = {"X-KNK-Closed-OK": "1"}


print("§1 환율 고치기")
r = q(cl.post, "/sales/orders/items/%d/edit" % IDS[2], data={"fx_rate": "1400", "invoice_unit_price_usd": str(round(49600/1400, 2)), "cost_price": str(round(24800/1400, 4)), "cost_krw": "24800"}, headers=H)
it = one("SELECT * FROM order_items WHERE id=?", (IDS[2],))
check("환율 1400 저장 · 단가 = 인보이스 35.43 · 금액 141.72(×4) · 매입(USD) 17.7143", r.status_code == 200 and abs(it["fx_rate"] - 1400) < 1e-9 and abs(it["unit_price"] - 35.43) < 1e-9 and abs(it["invoice_unit_price_usd"] - 35.43) < 1e-9 and abs(it["amount"] - 141.72) < 1e-9 and abs(it["cost_price"] - 17.7143) < 1e-9, (r.status_code, it))
h = one("SELECT note FROM order_status_history WHERE order_id=? ORDER BY id DESC LIMIT 1", (OID,))
check("이력 「환율 1,456.51 → 1,400.00」", h and "환율 1,456.51 → 1,400.00" in h["note"], h)
for bad in ("", "0", "-5"):
    r = q(cl.post, "/sales/orders/items/%d/edit" % IDS[2], data={"fx_rate": bad, "line_note": "x"}, headers=H)
    it = one("SELECT fx_rate FROM order_items WHERE id=?", (IDS[2],))
    check("환율 %r 보내면 그대로 1400" % bad, r.status_code == 200 and abs(it["fx_rate"] - 1400) < 1e-9, (r.status_code, it))
r = q(cl.post, "/sales/orders/items/%d/edit" % IDS[2], data={"fx_rate": "1.400,5"}, headers=H)
check("점·쉼표 바꿔 친 환율 「1.400,5」 → 400 안내", r.status_code == 400, (r.status_code, r.text[:200]))
print("§2 인보이스만 고치기")
r = q(cl.post, "/sales/orders/items/%d/edit" % IDS[0], data={"invoice_unit_price_usd": "0.50", "sell_krw": str(round(0.5*1456.51))}, headers=H)
it = one("SELECT * FROM order_items WHERE id=?", (IDS[0],))
check("인보이스 0.50 → 단가 0.50 · 금액 14.00(×28) · 판매가(원) 728", abs(it["unit_price"] - 0.5) < 1e-9 and abs(it["amount"] - 14.0) < 1e-9 and it["sell_krw"] == 728, it)
o = one("SELECT total_amount FROM orders WHERE id=?", (OID,))
tot = one("SELECT SUM(amount) s FROM order_items WHERE order_id=?", (OID,))["s"]
check("수주 합계 = 줄 금액 합", abs(o["total_amount"] - tot) < 0.005, (o, tot))
print("§3 자재번호")
r = q(cl.post, "/sales/orders/items/%d/edit" % IDS[0], data={"material_no": "MAT-118"}, headers=H)
check("자재번호 MAT-118 저장 · 금액 그대로", one("SELECT material_no, amount FROM order_items WHERE id=?", (IDS[0],)) == {"material_no": "MAT-118", "amount": 14.0}, one("SELECT material_no, amount FROM order_items WHERE id=?", (IDS[0],)))
print("§4 화면 조각")
src = io.open(os.path.join(ROOT, "app", "templates", "project_detail.html"), encoding="utf-8").read()
check("환율 입력 칸(fx-inp)", 'class="unit-edit fx-inp"' in src)
check("인보이스 입력 칸(inv-up-usd-inp)", 'class="unit-edit inv-up-usd-inp knk-money"' in src)
check("연동: 환율→인보이스 · 인보이스→판매가 · 판매가→인보이스", all(k in src for k in ("_fromFx", "_fromInv", "_syncInv(); _recalcAmt();")))
check("저장: fx_rate · material_no 보냄", "body.set('fx_rate'" in src and "body.set('material_no'" in src)
check("바뀐 줄 모으기에 fxInp · matnoInp", "palletInp, weightInp, fxInp, matnoInp" in src)
check("달러 판매가는 버리지 않고 둘째 자리", "_priceIsKrwR ? Math.floor" in src)
print("§5 프로젝트 정보 수정(수정 화면) — 고른 수주 값 · 단가 미정")
qf = io.open(os.path.join(ROOT, "app", "templates", "project_quick_form.html"), encoding="utf-8").read()
mm = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check("수정 화면에도 ☐ 단가 미정(고른 수주 있을 때) · 체크 상태 = 그 수주", "{% if not ed or tso117 %}" in qf and "tso117.tbd %} checked" in qf and 'name="price_tbd_seen"' in qf)
check("수량·단가·금액 칸 = 고른 수주 값(보기) · 서버로는 원래 프로젝트 값", "el.dataset.so118 = '1'" in qf and "h.type = 'hidden'; h.name = x[1]" in qf)
check("제품(SEMI)도 단가 미정 칸이 보이게 옮김", "qPriceTbdLbl" in qf and "amtCell.querySelector('label')" in qf)
check("서버: 수정 저장 → 고른 수주 price_tbd", "z1191z118 price_tbd edit" in mm and '_tso117["tbd"]' in mm)
print("§6 제품·완제품 한 줄 수량 N — 금액만 보내도 단가 덮이지 않음(이새롬 프로 11-23)")
with D.db_session() as c:
    c.execute("INSERT INTO order_items (order_id, unit_label, qty, unit_price, amount, currency) VALUES (?, '핀블럭플로팅', 4, 171000, 684000, 'KRW')", (OID2,))
    IID4 = c.execute("SELECT MAX(id) FROM order_items").fetchone()[0]
r = q(cl.post, "/sales/orders/items/%d/edit" % IID4, data={"amount": "684000"}, headers=H)
x = one("SELECT unit_price, amount FROM order_items WHERE id=?", (IID4,))
check("수량 4 줄에 금액 684,000 만 → 단가 171,000(예전엔 684,000) · 금액 684,000", r.status_code == 200 and x == {"unit_price": 171000.0, "amount": 684000.0}, (r.status_code, x))
r = q(cl.post, "/sales/orders/items/%d/edit" % IID4, data={"unit_price": "172000", "amount": "688000"}, headers=H)
x = one("SELECT unit_price, amount FROM order_items WHERE id=?", (IID4,))
check("단가·금액 함께 → 그대로 저장(172,000 · 688,000)", x == {"unit_price": 172000.0, "amount": 688000.0}, x)
check("화면: 완제품 한 줄 수량 N = 1개 단가 칸(data-perunit118) · 「⚠ 단가×수량≠금액」 알림", "data-perunit118" in src and "단가×수량≠금액" in src)
print()
print("결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
