# -*- coding: utf-8 -*-
"""z1191z17 시험 — 매출 보고서(대표 「1,2,3 진행해」 2026-11-10 · 이새롬·안지연 프로 답)
  ① 세금계산서 기준(기본) · 출하 · 수주 — 보고서 합계 = 매출 홈(_sales_3way) 합계(월·연)
  ② 사업부(소모품(검사기)·소모품(자동화) 따로) · 사업부 안 구분 · 고객사(수주 1차) · KNK VINA 2차(DRT 통합 · SEVT 따로 · 여러 개는 묶음)
     · 프로젝트 · 합계 맞춤 ✅
  ③ 출하 = 상태 발생일(출하 표시 날) 먼저 → 없으면 납기 (매출 홈도 같이)
  ④ 엑셀 5시트 · 상세 줄 = 화면 줄 · 매출 홈에 「📊 매출 보고서」 · 매출 금액 권한 없으면 못 봄
  임시 DB · TestClient · 운영 아님
"""
import contextlib, io, os, re, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z17-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z17_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()


def ins(c, table, row):
    cols = {r[1] for r in c.execute("PRAGMA table_info(%s)" % table)}
    ks = [k for k in row if k in cols]
    c.execute("INSERT INTO %s (%s) VALUES (%s)" % (table, ",".join('"%s"' % k for k in ks), ",".join("?" * len(ks))), [row[k] for k in ks])
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상관리자', 'admin', 'T917', 'T917', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T917'").fetchone())
    CU = {}
    for k, n, a in (("HS", "한국성전(주)", "한국성전"), ("VINA", "KNK VINA", "KNK VINA"), ("DT", "(주) 가상드림", "가상드림(동탄)")):
        CU[k] = ins(c, "customers", {"name": n, "alias": a})
    c.execute("INSERT OR REPLACE INTO exchange_rates (from_currency, to_currency, rate, rate_date, source) VALUES ('USD','KRW',1400,'2026-05-01','월기준')")
    c.execute("INSERT OR REPLACE INTO exchange_rates (from_currency, to_currency, rate, rate_date, source) VALUES ('USD','KRW',1450,'2026-06-01','월기준')")

    def proj(code, cust, ccy="KRW", sf="ASSEMBLY", sec=""):
        return ins(c, "projects", {"code": code, "name": "P-" + code, "mgmt_code": code, "customer_id": CU[cust], "customer_name": {"HS": "한국성전(주)", "VINA": "KNK VINA", "DT": "(주) 가상드림"}[cust],
                                   "currency": ccy, "status": "출하", "stage": "출하", "biz_div": code[3], "project_type": "NEW_EQUIP", "shipment_form": sf,
                                   "order_date": "2026-04-01", "due_date": "2026-05-20", "secondary_customer": sec, "is_archived": 0})

    def so(pid, no, cust, so_type="EQUIPMENT", ccy="KRW", end=None, **kw):
        r = {"project_id": pid, "order_no": no, "customer_id": CU[cust], "so_type": so_type, "currency": ccy, "status": "SHIPPED",
             "order_date": "2026-04-10", "due_date": "2026-05-15", "end_customer": end, "total_amount": 0}
        r.update(kw)
        return ins(c, "orders", r)

    def unit(oid, lbl, amt, **kw):
        r = {"order_id": oid, "unit_label": lbl, "qty": 1, "amount": amt, "unit_status": "출하"}
        r.update(kw)
        return ins(c, "order_items", r)

    # 검사기 · 한국성전 — 호기 계산서(5월) 2대 + 수주 계산서(호기 칸 비움 → 수주÷호기) 2대 + 6월 계산서 1대
    p1 = proj("001T2605", "HS")
    o1 = so(p1, "T-260501-1", "HS")
    unit(o1, "1호기", 2210000, tax_invoice_date="2026-05-29", tax_invoice_amt1=2210000)
    unit(o1, "2호기", 2410000, tax_invoice_date="2026-05-29", tax_invoice_amt1=2410000)
    o2 = so(p1, "T-260502-1", "HS", tax_invoice_date="2026-05-27", tax_invoice_amt1=9000000)
    unit(o2, "3호기", 4500000); unit(o2, "4호기", 4500000)
    unit(o1, "5호기", 1000000, tax_invoice_date="2026-06-10", tax_invoice_amt1=1000000, status_date="2026-06-09", due_date="2026-05-20")
    # 출하 표시 날(상태 발생일) 5월 · 납기 6월 → 출하 기준 5월
    unit(o1, "6호기", 700000, status_date="2026-05-30", due_date="2026-06-20")
    # 자동화 · KNK VINA — 상품(USD) 2차 DRT2 · 장비(USD) 2차 DREAMTECH VINA · 장비 2차 SEVT · 2차 없음
    p2 = proj("002M2605", "VINA", ccy="USD", sf="PARTS")
    o3 = so(p2, "M-260503-1", "VINA", so_type="PARTS_EXPORT", ccy="USD", end="DRT2", unit_qty=2)
    unit(o3, "BOLT", 100, currency="USD", tax_invoice_date="2026-05-20", tax_invoice_amt1=100)
    unit(o3, "NUT", 50, currency="USD", tax_invoice_date="2026-05-20", tax_invoice_amt1=50)
    p3 = proj("003T2605", "DT")
    o4 = so(p3, "T-260504-1", "VINA", ccy="USD", end="DREAMTECH VINA")
    unit(o4, "1호기", 1000, currency="USD", tax_invoice_date="2026-05-21", tax_invoice_amt1=1000)
    o5 = so(p3, "T-260504-2", "VINA", ccy="USD", end="SEVT")
    unit(o5, "2호기", 2000, currency="USD", tax_invoice_date="2026-05-22", tax_invoice_amt1=2000)
    o6 = so(p3, "T-260504-3", "VINA", ccy="USD")
    unit(o6, "3호기", 300, currency="USD", tax_invoice_date="2026-05-23", tax_invoice_amt1=300)
    # 소모품 화면 — 검사기 · 자동화(KNK VINA · 2차 여러 개)
    ins(c, "consumable_orders", {"co_no": "C1", "mgmt_code": "001C2605", "customer_name": "한국성전(주)", "currency": "KRW", "total_amount": 500000,
                                 "status": "SHIPPED", "biz_div": "T", "order_date": "2026-05-02", "due_date": "2026-05-10",
                                 "tax_invoice_date": "2026-05-31", "tax_invoice_amt1": 500000})
    ins(c, "consumable_orders", {"co_no": "C2", "mgmt_code": "002C2605", "customer_name": "KNK VINA", "currency": "USD", "total_amount": 400,
                                 "status": "SHIPPED", "biz_div": "M", "order_date": "2026-05-03", "due_date": "2026-05-12", "secondary_customer": "DSV,DRT1",
                                 "tax_invoice_date": "2026-05-31", "tax_invoice_amt1": 400})

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
M.get_user = lambda request: ADMIN
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0


def check(cond, msg, got=None):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", msg)
    else:
        FAIL += 1; print("  ❌", msg, "" if got is None else ("  ← %r" % (got,)))


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def rep(basis, mode="month", m="5", y="2026"):
    oi_map, _ = q(M._board_tax_oi_map)
    with D.db_session() as c:
        rates = M._fx_load_rates(c)
        return M._sales_report_z17(c, rates, oi_map, basis, mode, y, "2", m), M._sales_3way(c, rates, oi_map, mode, y, "2", m)


print("§1 세금계산서 기준 2026년 5월")
R, S3 = rep("tax")
want = 2210000 + 2410000 + 9000000 + (100 + 50 + 1000 + 2000 + 300) * 1400 + 500000 + 400 * 1400
check(abs(R["total"] - want) < 1, "합계 = 손계산 %s" % format(want, ","), R["total"])
check(abs(R["total"] - S3["kpi"]["final"]) < 1, "보고서 합계 = 매출 홈 최종매출", (R["total"], S3["kpi"]["final"]))
check(R["checks_ok"], "합계 맞춤(사업부·구분·고객사·프로젝트)", R["checks"])
B = {b["key"]: b for b in R["biz_rows"]}
check(abs(B["T"]["total"] - (13620000 + 3300 * 1400)) < 1 and abs(B["M"]["total"] - 150 * 1400) < 1, "사업부: 검사기 · 자동화", (B["T"]["total"], B["M"]["total"]))
check(abs(B["CT"]["total"] - 500000) < 1 and abs(B["CM"]["total"] - 560000) < 1 and B["CT"]["label"].endswith("소모품(검사기)") and B["CM"]["label"].endswith("소모품(자동화)"),
      "소모품(검사기) 500,000 · 소모품(자동화) 560,000 따로")
check(abs(B["M"]["cats"]["상품"] - 210000) < 1 and abs(B["T"]["cats"]["장비"] - B["T"]["total"]) < 1, "사업부 안 구분: 자동화 상품 · 검사기 장비")
hs = [a for a in R["cust_rows"] if a["name"] == "한국성전"]
check(hs and abs(hs[0]["total"] - (13620000 + 500000)) < 1 and hs[0]["cnt"] == 5, "고객사: 한국성전 = 호기 4 + 소모품 1 (수주÷호기 나눔 포함)", hs)
V = {a["name"]: a["total"] for a in R["vina_rows"]}
check(abs(V.get("DRT", 0) - (150 + 1000) * 1400) < 1, "KNK VINA 2차: DRT2 · DREAMTECH VINA → DRT 로 묶음", V)
check(abs(V.get("SEVT", 0) - 2800000) < 1 and abs(V.get("(2차 미입력)", 0) - 420000) < 1 and abs(V.get("DSV,DRT", 0) - 560000) < 1,
      "SEVT 따로 · 2차 미입력 · 여러 개(DSV,DRT1 → DSV,DRT 묶음)", V)
check(abs(R["vina_total"] - sum(V.values())) < 1, "KNK VINA 합계 = 2차 합")
P = {a["code"]: a["total"] for a in R["proj_rows"]}
check(abs(P.get("001T2605", 0) - 13620000) < 1, "프로젝트별 001T2605 = 13,620,000(6월 계산서 제외)", P.get("001T2605"))

print("§2 세 기준 · 기간 — 보고서 = 매출 홈")
for basis, key in (("tax", "final"), ("ship", "prog"), ("order", "order")):
    for mode, m in (("month", "5"), ("month", "6"), ("year", "5")):
        r_, s_ = rep(basis, mode, m)
        check(abs(r_["total"] - s_["kpi"][key]) < 1, "%s · %s %s월 = 매출 홈 %s" % (basis, mode, m, key), (r_["total"], s_["kpi"][key]))
r5, _ = rep("ship", "month", "5")
check(any(x["label"] == "6호기" for x in r5["lines"]) and not any(x["label"] == "5호기" for x in r5["lines"]),
      "출하 기준: 상태 발생일 5월(납기 6월) → 5월 · 상태 발생일 6월 → 5월 아님")
check("NULLIF(TRIM(oi.status_date),'')" in M.SALES_DD_SHIP, "매출 홈 출하 규칙도 상태 발생일 먼저(SALES_DD_SHIP)")

print("§3 화면 · 엑셀 · 권한")
h = q(cl.get, "/sales/report?basis=tax&mode=month&year=2026&m=5")
check(h.status_code == 200 and "📊 매출 보고서" in h.text and "✅ 합계 맞춤" in h.text and "소모품(검사기)" in h.text and "(여러 고객 · 다시 등록 대기)" in h.text,
      "화면 200 · 합계 맞춤 · 소모품(검사기) · 여러 고객 표시", h.status_code)
check(format(int(round(want)), ",") in h.text, "화면 합계 숫자")
x = q(cl.get, "/sales/report.xlsx?basis=tax&mode=month&year=2026&m=5")
ok_x = False
try:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(x.content), read_only=True)
    names = [w.title for w in wb.worksheets]
    det = list(wb["상세"].iter_rows(values_only=True))
    hdr_i = [i for i, r_ in enumerate(det) if r_ and "날짜" in r_][0]
    nlines = len([r_ for r_ in det[hdr_i + 1:] if r_ and r_[0]])
    ok_x = names[:5] == ["사업부", "고객사", "KNK VINA 2차", "프로젝트", "상세"] and nlines == R["cnt"]
except Exception as _e:
    names = repr(_e)
check(ok_x, "엑셀 5시트 · 상세 줄 수 = 화면 줄 수(%d)" % R["cnt"], names)
hh = q(cl.get, "/sales").text
check('href="/sales/report"' in hh, "매출 홈에 「📊 매출 보고서」 단추")
with D.db_session() as c:
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales) "
              "VALUES ('가상일반', 'member', 'T918', 'T918', 'sso_only_no_local_password', 1, 1, 0, 0)")
    MEM = dict(c.execute("SELECT * FROM users WHERE employee_no='T918'").fetchone())
M.get_user = lambda request: MEM
rn = q(cl.get, "/sales/report")
rx = q(cl.get, "/sales/report.xlsx")
check(rn.status_code == 303 and rx.status_code == 303, "매출 권한 없으면 화면·엑셀 못 봄(303)", (rn.status_code, rx.status_code))

print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
