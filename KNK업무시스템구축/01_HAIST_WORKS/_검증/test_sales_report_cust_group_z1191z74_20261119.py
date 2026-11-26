# -*- coding: utf-8 -*-
"""z1191z74 시험 (대표 2026-11-19 「매출보고서쪽도 동일하게 맞춰.」 = z1191z73)
  매출보고서(화면·엑셀) 고객사 = 등록명 · 한 회사 여러 종사업장(드림텍)은 합산 + 펼치기(화면 ▸ · 엑셀 + 그룹) · 줄 단위는 사업장
  임시 DB · TestClient · 운영 아님
"""
import contextlib, io, os, re, sys, tempfile
from urllib.parse import quote
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z74-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z74_")
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


IT = {}
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상관리자', 'admin', 'T972', 'T972', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T972'").fetchone())
    SE = ins(c, "customers", {"name": "삼성전기(주)", "alias": "삼성전기"})
    D1 = ins(c, "customers", {"name": "(주) 드림텍", "alias": "드림텍(본사)"})
    D2 = ins(c, "customers", {"name": "(주)드림텍", "alias": "드림텍(아산)"})   # 운영도 띄어쓰기만 다른 같은 정식명 셋
    D3 = ins(c, "customers", {"name": "(주) 드림텍 ", "alias": "드림텍(동탄)"})
    NA = ins(c, "customers", {"name": "가상무별칭(주)", "alias": ""})

    def proj(code, cid, cname):
        return ins(c, "projects", {"code": code, "mgmt_code": code, "name": "PBA", "model_name": "MD-" + code, "equip_name": "검사기",
                                   "biz_div": code[3], "customer_id": cid, "customer_name": cname, "status": "진행중",
                                   "currency": "KRW", "order_date": "2026-05-05", "due_date": "2026-06-30", "is_archived": 0})

    def order(pid, cid, no):
        return ins(c, "orders", {"order_no": no, "project_id": pid, "customer_id": cid, "order_date": "2026-05-05",
                                 "due_date": "2026-06-15", "status": "CONFIRMED", "currency": "KRW"})

    def item(oid, key, amt):
        IT[key] = ins(c, "order_items", {"order_id": oid, "qty": 1, "unit_price": amt, "amount": amt, "unit_status": "출하",
                                         "status_date": "2026-05-15", "due_date": "2026-06-10", "order_date": "2026-05-05", "currency": "KRW", "unit_label": key})

    # 저장된 글자가 섞여 있다(운영처럼): 정식명으로 적힌 건 · 시스템명으로 적힌 건
    item(order(proj("001T2605", SE, "삼성전기(주)"), SE, "T-260505-1"), "s1", 1000000)
    item(order(proj("002T2605", SE, "삼성전기"), SE, "T-260505-2"), "s2", 2000000)
    item(order(proj("003T2605", D1, "(주) 드림텍"), D1, "T-260505-3"), "d1", 300000)
    item(order(proj("004T2605", D2, "(주) 드림텍"), D2, "T-260505-4"), "d2", 400000)
    item(order(proj("005T2605", D3, "드림텍(동탄)"), D3, "T-260505-5"), "d3", 500000)
    item(order(proj("006T2605", NA, "가상무별칭(주)"), NA, "T-260505-6"), "n1", 600000)
    item(order(proj("007T2605", None, "번호없는고객"), None, "T-260505-7"), "x1", 700000)
    CO = ins(c, "consumable_orders", {"co_no": "C-1", "mgmt_code": "001C2605", "customer_name": "삼성전기(주)", "customer_id": SE, "currency": "KRW",
                                      "total_amount": 400000, "status": "SHIPPED", "biz_div": "T", "order_date": "2026-05-02", "due_date": "2026-05-10",
                                      "status_date": "2026-05-10", "tax_invoice_date": "2026-05-20", "tax_invoice_amt1": 400000,
                                      "model_name": "소모품", "equip_name": "핀 2종", "project_name": "SENSOR"})

OI = {IT["s1"]: {"t1d": "2026-05-20", "t1a": 1000000}, IT["d2"]: {"t1d": "2026-05-25", "t1a": 400000}}

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
M.get_user = lambda request: ADMIN
M._board_tax_oi_map = lambda: (OI, {})
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


import openpyxl  # noqa: E402
M.can_view_field = lambda u, f, *a, **k: True
with D.db_session() as c:
    rates = M._fx_load_rates(c)
    R = q(M._sales_report_z17, c, rates, OI, "ship", "year", "2026", "1", "1")
C = {a["name"]: a for a in R["cust_rows"]}

print("§1 보고서 고객사 = 등록명")
# z1191z161 (대표 11-26): 수주에 1차 고객사가 비면 관리번호에 적힌 글자(번호없는고객)로 대신하지 않고 「⚠ 고객 미정(확인 필요)」
check(sorted(C) == sorted(["삼성전기(주)", "(주) 드림텍", "가상무별칭(주)", "⚠ 고객 미정(확인 필요)"]), "고객사별 = 등록명(수주 고객사가 비면 「⚠ 고객 미정」)", sorted(C))
check(round(C["삼성전기(주)"]["total"]) == 3400000 and C["삼성전기(주)"]["children"] == [], "삼성전기(주) = 등록명·시스템명으로 적힌 건 + 소모품 한 줄(340만) · 펼치기 없음", C["삼성전기(주)"])
g = C["(주) 드림텍"]
check(round(g["total"]) == 1200000 and g["so_n"] == 3, "(주) 드림텍 = 세 사업장 합산 120만 · 수주 3건", (g["total"], g["so_n"]))
check([(k["name"], round(k["total"]), k["so_n"]) for k in g["children"]] == [("드림텍(동탄)", 500000, 1), ("드림텍(아산)", 400000, 1), ("드림텍(본사)", 300000, 1)],
      "펼치면 드림텍(동탄) 50만 · (아산) 40만 · (본사) 30만", [(k["name"], k["total"]) for k in g["children"]])
check(R["checks_ok"] and abs(sum(a["total"] for a in R["cust_rows"]) - R["total"]) < 1, "고객사 합 = 총합(펼친 줄은 합에 안 들어감)")
P = {a["code"]: a["cust"] for a in R["proj_rows"]}
check(P["004T2605"] == "드림텍(아산)" and P["003T2605"] == "드림텍(본사)" and P["001T2605"] == "삼성전기(주)", "프로젝트별(줄 단위): 드림텍은 사업장(시스템명) · 나머지는 등록명", P)
Lx = {x["so"]: (x["cust"], x.get("cust_br")) for x in R["lines"]}
check(Lx["T-260505-5"] == ("(주) 드림텍", "드림텍(동탄)") and Lx["T-260505-1"] == ("삼성전기(주)", None), "줄: 등록명 + 사업장", Lx)

print("§2 보고서 화면")
h = q(cl.get, "/sales/report?basis=ship&mode=year&year=2026").text
check("<td>삼성전기(주)</td>" in h and "<td>(주) 드림텍<button" in h, "고객사별: 등록명")
check(h.count('class="z73-tg"') == 1 and "</span>3곳</button>" in h, "드림텍 줄에만 「▸ 3곳」")
kids = re.findall(r'<tr class="z73-ch z73p-r\d+" hidden>.*?└</span> ([^<]+)</td>', h)
check(kids == ["드림텍(동탄)", "드림텍(아산)", "드림텍(본사)"], "펼칠 줄 3개(처음 숨김)", kids)
check("<td>드림텍(아산)</td>" in h, "상세 줄: 드림텍은 사업장 이름")

print("§3 보고서 엑셀")
r_ = q(cl.get, "/sales/report.xlsx?basis=ship&mode=year&year=2026")
check(r_.status_code == 200, "엑셀 받기 200", r_.status_code)
wb = openpyxl.load_workbook(io.BytesIO(r_.content))
ws = wb["고객사"]
rows = [(r, ws.cell(r, 2).value, ws.cell(r, 3).value, ws.row_dimensions[r].outlineLevel, ws.row_dimensions[r].hidden) for r in range(1, ws.max_row + 1)]
gi = [k for k, x in enumerate(rows) if x[1] == "(주) 드림텍  (+ 3곳)"]
check(len(gi) == 1, "「고객사」 시트: 「(주) 드림텍  (+ 3곳)」 한 줄", [x[1] for x in rows])
sub = rows[gi[0] + 1:gi[0] + 4] if gi else []
check([(x[1], x[2], x[3], x[4]) for x in sub] == [("   └ 드림텍(동탄)", 500000, 1, True), ("   └ 드림텍(아산)", 400000, 1, True), ("   └ 드림텍(본사)", 300000, 1, True)],
      "그 밑 사업장 3줄 = 엑셀 그룹(접혀 있음 · + 로 펼침)", [(x[1], x[2], x[3], x[4]) for x in sub])
check(ws.sheet_properties.outlinePr.summaryBelow is False, "+ 단추가 등록명 줄 옆(위)에")
check(any(ws.cell(r, 2).value == "삼성전기(주)" for r in range(1, ws.max_row + 1)), "삼성전기(주) = 등록명")
s1 = wb.worksheets[0]
txt = " ".join(str(c.value) for row in s1.iter_rows() for c in row if c.value)
check("(주) 드림텍 = 종사업장 드림텍(동탄)/드림텍(아산)/드림텍(본사) 합산" in txt and "드림텍(아산)" not in txt.replace("드림텍(동탄)/드림텍(아산)/드림텍(본사)", ""), "1장(보고): 등록명 합산 + 「고객사 시트에서 + 」 안내 한 줄")
det = None
for w in wb.worksheets:
    hdr = [w.cell(6, k).value for k in range(1, 16)]
    if "2차 고객사" in hdr and "호기" in hdr:
        det = (w, hdr.index("고객사") + 1)
vals = [det[0].cell(r, det[1]).value for r in range(7, det[0].max_row + 1)] if det else []
check(det and "드림텍(동탄)" in vals and "삼성전기(주)" in vals and "(주) 드림텍" not in vals, "상세 시트: 줄마다 드림텍은 사업장 · 나머지는 등록명", sorted(set(v for v in vals if v)))

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
