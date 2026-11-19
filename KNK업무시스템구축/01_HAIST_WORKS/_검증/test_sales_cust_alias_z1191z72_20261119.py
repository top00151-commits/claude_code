# -*- coding: utf-8 -*-
"""z1191z72 시험 (대표 2026-11-19 「매출영업센터에 고객사명 표현이 시스템명, 고객사명이 혼용 … 기준을 시스템명으로」)
  매출 홈·고객사별 매출 = 고객사 번호 → 시스템명으로 묶음(같은 정식명 지점도 나뉨) · 납품·수금 · 프로젝트 목록 소모품 줄
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z72-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z72_")
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


L = []
with D.db_session() as c:
    rates = M._fx_load_rates(c)
    S = q(M._sales_3way, c, rates, OI, "year", "2026", "1", "1", detail=L)
    DA = M._z45_drill(c, L, "", "")
    DS = M._z45_drill(c, L, "", "삼성전기")
    DD = M._z45_drill(c, L, "", "드림텍(아산)")
names = sorted({x[2] for x in L})
trip = lambda d: (round(d["order"]), round(d["prog"]), round(d["final"]))
R = {r["cust"]: r for r in DA["rows"]}

# §1·§2(매출 집계 고객사 이름)는 z1191z73 에서 「등록명 + 종사업장 펼치기」로 바뀜 → test_sales_cust_group_z1191z73_20261119.py
print("§3 납품·수금")
hs = q(cl.get, "/sales/shipments-receipts").text
cells = re.findall(r'<span class="sr-v" title="([^"]*)">([^<]*)</span>', hs)
cu_cells = [x for x in cells if x[1] in ("삼성전기", "삼성전기(주)", "드림텍(본사)", "드림텍(아산)", "드림텍(동탄)", "(주) 드림텍", "가상무별칭(주)")]
check(sorted({x[1] for x in cu_cells}) == ["드림텍(아산)", "삼성전기"], "고객사 칸 = 시스템명(이 화면에 나오는 두 수주)", sorted({x[1] for x in cu_cells}))
check(("정식: 삼성전기(주)", "삼성전기") in cells and ("정식: (주)드림텍", "드림텍(아산)") in cells, "마우스를 올리면 「정식: 삼성전기(주)」", cu_cells[:4])
check('data-cust="삼성전기"' in hs, "고객사 정렬·찾기 값도 시스템명")

print("§4 프로젝트 목록 소모품 줄")
hp = q(cl.get, "/projects").text
tds = re.findall(r'<td title="정식: ([^"]*)">([^<]*)</td>', hp)
check(("삼성전기(주)", "삼성전기") in tds and tds.count(("삼성전기(주)", "삼성전기")) == 2, "소모품 줄(정식명으로 적힘)도 프로젝트 줄처럼 「삼성전기」", [x for x in tds if "삼성" in x[0]])
check(not any(x[1] in ("삼성전기(주)", "(주) 드림텍") for x in tds), "고객사 칸에 정식명 없음", tds)

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
