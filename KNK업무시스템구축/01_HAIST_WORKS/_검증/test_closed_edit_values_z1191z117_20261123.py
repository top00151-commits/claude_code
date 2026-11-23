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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z117-test-only-not-a-real-key"
import app.database as D                                   # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z117_"); _REAL = D.DB_PATH; D.DB_PATH = os.path.join(TMP, "t.db"); assert D.DB_PATH != _REAL
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

print("§1 입금 완료 수주 줄 고치기")
r = q(cl.post, "/sales/orders/items/%d/edit" % IDS[1], data={"sell_krw": "4200000", "unit_price": str(round(4200000 / 1456.51, 4))})
check("확인 표시 없이 → 409 · 「입금 완료된 수주」 안내 · 저장 안 됨", r.status_code == 409 and "입금 완료" in r.json().get("message", "") and one("SELECT sell_krw FROM order_items WHERE id=?", (IDS[1],))["sell_krw"] == 7000000, (r.status_code, r.text[:200]))
r = q(cl.post, "/sales/orders/items/%d/edit" % IDS[1], data={"sell_krw": "4200000", "unit_price": str(round(4200000 / 1456.51, 4))}, headers=H)
it = one("SELECT * FROM order_items WHERE id=?", (IDS[1],)); o = one("SELECT * FROM orders WHERE id=?", (OID,))
check("확인 표시 있으면 저장 · 상태 PAID 그대로", r.status_code == 200 and r.json().get("ok") and o["status"] == "PAID", (r.status_code, r.text[:200]))
print("§2 상품(외화) 줄 맞춤")
check("판매가 4,200,000 → 단가 2,883.61 = 인보이스 · 금액 2,883.61", it["sell_krw"] == 4200000 and abs(it["unit_price"] - 2883.61) < 1e-9 and abs(it["invoice_unit_price_usd"] - 2883.61) < 1e-9 and abs(it["amount"] - 2883.61) < 1e-9, it)
check("세금계산서 칸 그대로", it["tax_invoice_date"] == "2026-02-06" and abs(it["tax_invoice_amt1"] - 2883.61) < 1e-9, it)
h = one("SELECT note FROM order_status_history WHERE order_id=? ORDER BY id DESC LIMIT 1", (OID,))
check("이력: 「정정(확인함)」 · 판매가 7,000,000 → 4,200,000 · 거짓 「→ —」 없음", h and "정정(확인함)" in h["note"] and "판매가(원) 7,000,000 → 4,200,000" in h["note"] and "→ —" not in h["note"], h)
r = q(cl.post, "/sales/orders/items/%d/edit" % IDS[2], data={"qty": "5"}, headers=H)
it = one("SELECT * FROM order_items WHERE id=?", (IDS[2],))
check("수량만 4 → 5: 금액 = 5 × 인보이스 34.05 = 170.25", abs(it["amount"] - 170.25) < 1e-9 and abs(it["unit_price"] - 34.05) < 1e-9, it)
r = q(cl.post, "/sales/orders/items/%d/edit" % IDS[0], data={"invoice_unit_price_usd": "0.47"}, headers=H)
it = one("SELECT * FROM order_items WHERE id=?", (IDS[0],))
check("인보이스만 0.47: 단가 0.47 · 금액 28 × 0.47 = 13.16", abs(it["unit_price"] - 0.47) < 1e-9 and abs(it["amount"] - 13.16) < 1e-9 and abs(it["invoice_amount_usd"] - 13.16) < 1e-9, it)
print("§3 작업일정표 수량 따라감")
r = q(cl.post, "/sales/orders/items/%d/edit" % IID2, data={"qty": "5", "unit_price": "171000", "amount": "855000"})
o2 = one("SELECT * FROM orders WHERE id=?", (OID2,)); it2 = one("SELECT * FROM order_items WHERE id=?", (IID2,))
check("줄 수량 6 → 5 · 단가 171,000 · 금액 855,000 · board_qty 6 → 5", r.json().get("ok") and o2["board_qty"] == 5 and it2["unit_price"] == 171000 and it2["amount"] == 855000, (r.text[:200], o2["board_qty"], it2))
with D.db_session() as c:
    c.execute("UPDATE orders SET board_qty=9 WHERE id=?", (OID2,))
q(cl.post, "/sales/orders/items/%d/edit" % IID2, data={"qty": "4"})
check("처음부터 다르게 적은 표시 수량(9)은 그대로", one("SELECT board_qty FROM orders WHERE id=?", (OID2,))["board_qty"] == 9)
hd2 = q(cl.get, "/project/%d" % PID2).text
check("수주 카드: 「(품목 줄 합 4)」 옆 「↻ 4(으)로 맞추기」 단추", "(품목 줄 합 4)" in hd2 and "knkBoardSync117(%d" % OID2 in hd2 and "↻ 4(으)로 맞추기" in hd2)
r = q(cl.post, "/sales/orders/%d/board-qty-sync" % OID2)
check("맞추기 → board_qty 9 → 4(품목 줄 합)", r.json().get("ok") and one("SELECT board_qty FROM orders WHERE id=?", (OID2,))["board_qty"] == 4, r.text[:200])

print("§4 엑셀 값만 고치기")
tb = q(cl.get, "/projects/import-product-template?so_id=%d" % OID).content
import openpyxl                                            # noqa: E402
def edited(fn):
    wb = openpyxl.load_workbook(io.BytesIO(tb)); ws = wb.worksheets[0]
    hr = next(r for r in range(1, 40) if any("자재품명" in str(ws.cell(r, c).value or "") for c in range(1, 20)))
    hdr = {str(ws.cell(hr, c).value or ""): c for c in range(1, ws.max_column + 1)}
    col = lambda k: next(c for h, c in hdr.items() if k in h)
    fn(ws, hr, col); b = io.BytesIO(); wb.save(b); return b.getvalue()
before = {i: one("SELECT * FROM order_items WHERE id=?", (i,)) for i in IDS}
x1 = edited(lambda ws, hr, col: ws.cell(hr + 3, col("비고")).__setattr__("value", "확인 완료"))
r = q(cl.post, "/sales/orders/%d/overwrite-product" % OID, files={"xlsx": ("a.xlsx", x1)}, data={"mode": "update", "dry": "1"})
j = r.json()
check("미리 보기(dry): 1줄(SENSOR 비고) · 저장 안 됨", j.get("ok") and j.get("dry") and j.get("n_changed") == 1 and j["diffs"][0]["name"] == "SENSOR" and one("SELECT line_note FROM order_items WHERE id=?", (IDS[2],))["line_note"] in (None, ""), j)
r = q(cl.post, "/sales/orders/%d/overwrite-product" % OID, files={"xlsx": ("a.xlsx", x1)}, data={"mode": "update"})
check("입금 완료 수주 · 확인 표시 없이 저장 → 거절(need_closed_ok)", r.json().get("need_closed_ok") and not r.json().get("ok"), r.text[:200])
r = q(cl.post, "/sales/orders/%d/overwrite-product" % OID, files={"xlsx": ("a.xlsx", x1)}, data={"mode": "update"}, headers=H)
after = {i: one("SELECT * FROM order_items WHERE id=?", (i,)) for i in IDS}
ids_now = [x[0] for x in [tuple(v.values()) for v in [one("SELECT id FROM order_items WHERE id=?", (i,)) for i in IDS]]]
check("저장: SENSOR 비고만 · 줄 번호 그대로 · 세금계산서 그대로", r.json().get("ok") and after[IDS[2]]["line_note"] == "확인 완료" and ids_now == IDS
      and all(after[i]["tax_invoice_amt1"] == before[i]["tax_invoice_amt1"] and after[i]["tax_invoice_date"] == before[i]["tax_invoice_date"] for i in IDS)
      and all(after[i]["unit_price"] == before[i]["unit_price"] and after[i]["amount"] == before[i]["amount"] for i in IDS), (r.text[:200]))
x2 = edited(lambda ws, hr, col: ws.cell(hr + 4, col("자재품명")).__setattr__("value", "새 부품"))
r = q(cl.post, "/sales/orders/%d/overwrite-product" % OID, files={"xlsx": ("a.xlsx", x2)}, data={"mode": "update", "dry": "1"}, headers=H)
check("줄을 더한 파일 → 「줄 수가 다릅니다」", not r.json().get("ok") and "줄 수가 다릅니다" in r.json().get("message", ""), r.text[:200])
x3 = edited(lambda ws, hr, col: ws.cell(hr + 1, col("자재품명")).__setattr__("value", "다른이름"))
r = q(cl.post, "/sales/orders/%d/overwrite-product" % OID, files={"xlsx": ("a.xlsx", x3)}, data={"mode": "update", "dry": "1"}, headers=H)
check("품명을 바꾼 파일 → 「품명 순서가 … 1번째 줄」", not r.json().get("ok") and "1번째 줄" in r.json().get("message", ""), r.text[:200])
x4 = edited(lambda ws, hr, col: None)
r = q(cl.post, "/sales/orders/%d/overwrite-product" % OID, files={"xlsx": ("a.xlsx", x4)}, data={"mode": "update", "dry": "1"}, headers=H)
check("받은 양식 그대로 올림 → 바뀌는 줄 0(반올림 차이를 바뀜으로 안 봄)", r.json().get("ok") and r.json().get("n_changed") == 0, r.json())

print("§5 확인할 줄 점검")
ck = M._parts_checks_z117([
    {"unit_label": "PC", "qty": 1, "unit_price": 4806.0089, "amount": 2883.61, "invoice_unit_price_usd": 2883.61, "sell_krw": 7000000, "cost_krw": 3500000, "margin_pct": 20, "fx_rate": 1456.51},
    {"unit_label": "A", "qty": 27, "unit_price": 31.4312, "amount": 848.61, "invoice_unit_price_usd": 31.43, "sell_krw": 48003, "fx_rate": 1527.3},
    {"unit_label": "B", "qty": 1, "unit_price": 4800, "amount": 4800, "cost_krw": 2400, "margin_pct": 50, "sell_krw": 4800},
    {"unit_label": "S", "spec": "X", "qty": 1, "unit_price": 10, "amount": 10}, {"unit_label": "S", "spec": "X", "qty": 1, "unit_price": 100, "amount": 100},
    {"unit_label": "T", "spec": "Y", "qty": 1, "unit_price": 10, "amount": 10}, {"unit_label": "T", "spec": "Y", "qty": 1, "unit_price": 13.3, "amount": 13.3},
], fx_line=lambda r: r.get("fx_rate") is not None)
check("판매가÷환율≠인보이스 · 매입가×마진≠판매가(204번 같은 실수)를 잡음", 0 in ck and any("÷ 환율" in m for m in ck[0]) and any("마진" in m for m in ck[0]), ck.get(0))
check("반올림(4자리 단가 · 2자리 인보이스)은 안 잡음", 1 not in ck, ck.get(1))
check("판매가 기준 마진율(50% = 2배)은 맞는 것으로 봄", 2 not in ck, ck.get(2))
check("같은 품목 10배 차이는 잡고 1.33배(마진 차이)는 안 잡음", 3 in ck and 4 in ck and 5 not in ck and 6 not in ck, ck)

print("§6 단가 미정 · 화면 조각")
r = q(cl.post, "/sales/orders/%d/price-tbd" % OID2, data={"on": "1"})
check("단가 미정 켜기 → price_tbd=1", r.json().get("ok") and one("SELECT price_tbd FROM orders WHERE id=?", (OID2,))["price_tbd"] == 1, r.text[:200])
hq = q(cl.get, "/projects/quick?biz_div=M").text
check("등록 화면: ☐ 단가 미정(qPriceTbd) · 체크하면 빈 단가 = 0 으로 보냄", 'id="qPriceTbd"' in hq and "qTbdOn117" in hq)
sb = io.open(os.path.join(ROOT, "app", "templates", "schedule_board.html"), encoding="utf-8").read()
check("작업일정표: r.is_tbd → [미정] 칸(단가·금액 둘 다) · 세금계산서 비우기 확인", sb.count("{% elif r.is_tbd %}") == 2 and "비우기 취소함" in sb)
hd = q(cl.get, "/project/%d" % PID).text
check("상세: 「프로젝트 정보 수정」 = /quick-edit · 입금 완료 카드 data-closed117 · 값만 고치기 단추 · 확인할 줄 띠",
      "/projects/%d/quick-edit" % PID in hd and 'data-closed117="PAID"' in hd and "값만 고치기(엑셀)" in hd, None)
print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
