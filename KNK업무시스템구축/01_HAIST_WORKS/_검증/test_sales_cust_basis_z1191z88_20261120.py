# -*- coding: utf-8 -*-
"""z1191z88 시험 — 매출 고객사 기준 통일: 청구처(수주 1차 발주처 · 없으면 프로젝트 고객) = 매출 보고서와 같게
  대표 2026-11-20 「사진보면 드림텍 매출이 서로 다른데 원인 파악해봐.. 매출 관련 사항은 정확한 검산이 되어야해.」 → 「1번으로 진행해」
  §1 검산: 수주·진행(출하)·최종(세금계산서) 세 기준 모두 — 매출 홈 고객사별 금액 = 매출 보고서 고객사별 금액(고객사마다 원 단위)
  §2 TOP5 청구처(기본) · 「↳ 이 중 최종 고객」 · 최종 고객 기준 TOP5 · 두 기준 합계 같음
  §3 깊이 보기 ?by=end · §4 화면 글
  임시 DB · 가짜 회사 · 운영 아님
"""
import contextlib, io, os, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z88-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z88_")
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


DREAM = "(주) 가상드림"
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales) "
              "VALUES ('가상관리자', 'admin', 'T881', 'T881', 'sso_only_no_local_password', 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T881'").fetchone())
    CU = {}
    # 운영처럼 띄어쓰기만 다른 같은 회사(가상드림 아산·동탄)
    for k, n, a in (("D1", DREAM, "가상드림(아산)"), ("D2", "(주)가상드림", "가상드림(동탄)"), ("VINA", "KNK VINA", "KNK VINA"), ("HS", "한국가상(주)", "한국가상")):
        CU[k] = ins(c, "customers", {"name": n, "alias": a})
    c.execute("INSERT OR REPLACE INTO exchange_rates (from_currency, to_currency, rate, rate_date, source) VALUES ('USD','KRW',1400,'2026-05-01','월기준')")

    def proj(code, cust, ccy="KRW"):
        nm = {"D1": DREAM, "D2": "(주)가상드림", "VINA": "KNK VINA", "HS": "한국가상(주)"}[cust]
        return ins(c, "projects", {"code": code, "name": "P-" + code, "mgmt_code": code, "customer_id": CU[cust], "customer_name": nm,
                                   "currency": ccy, "status": "출하", "stage": "출하", "biz_div": code[3], "project_type": "NEW_EQUIP",
                                   "shipment_form": "ASSEMBLY", "order_date": "2026-05-01", "due_date": "2026-05-20", "is_archived": 0})

    def so(pid, no, cust, ccy="KRW"):
        return ins(c, "orders", {"project_id": pid, "order_no": no, "customer_id": CU[cust] if cust else None, "so_type": "EQUIPMENT",
                                 "currency": ccy, "status": "SHIPPED", "order_date": "2026-05-10", "due_date": "2026-05-15", "total_amount": 0})

    def unit(oid, lbl, amt, ccy=None, tax=None):
        r = {"order_id": oid, "unit_label": lbl, "qty": 1, "amount": amt, "unit_status": "출하", "status_date": "2026-05-12"}
        if ccy:
            r["currency"] = ccy
        if tax:
            r.update(tax_invoice_date="2026-05-20", tax_invoice_amt1=tax)
        return ins(c, "order_items", r)

    # ① 최종 고객 가상드림(아산) · 청구처 KNK VINA (USD 1,000 → 1,400,000원) — 이번 대표 사례 모양
    o1 = so(proj("001T2605", "D1", "USD"), "T-1", "VINA", "USD")
    unit(o1, "1호기", 1000, "USD", tax=1000)
    # ② 최종 고객 = 청구처 = 가상드림(동탄) 5,000,000
    o2 = so(proj("002T2605", "D2"), "T-2", "D2")
    unit(o2, "1호기", 5000000, tax=5000000)
    # ③ 수주에 고객사 없음 → 프로젝트 고객(한국가상) 3,000,000
    o3 = so(proj("003M2605", "HS"), "M-3", None)
    unit(o3, "1호기", 3000000, tax=3000000)
    # ④ 반대: 최종 고객 KNK VINA · 청구처 한국가상 700,000
    o4 = so(proj("004M2605", "VINA"), "M-4", "HS")
    unit(o4, "1호기", 700000, tax=700000)
    # ⑤ 소모품 — 한국가상 200,000(소모품은 청구처 = 최종 고객)
    ins(c, "consumable_orders", {"co_no": "C1", "mgmt_code": "005C2605", "customer_id": CU["HS"], "customer_name": "한국가상(주)", "currency": "KRW",
                                 "total_amount": 200000, "status": "SHIPPED", "biz_div": "T", "order_date": "2026-05-02", "due_date": "2026-05-10",
                                 "status_date": "2026-05-11", "tax_invoice_date": "2026-05-31", "tax_invoice_amt1": 200000})

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


oi_map, _ = q(M._board_tax_oi_map)
with D.db_session() as c:
    rates = M._fx_load_rates(c)
    lines = []
    S3 = M._sales_3way(c, rates, oi_map, "year", "2026", "2", "5", detail=lines)
    REP = {b: M._sales_report_z17(c, rates, oi_map, b, "year", "2026", "2", "5") for b in ("order", "ship", "tax")}

print("§1 검산 — 매출 홈 고객사별 = 매출 보고서 고객사별(세 기준 모두 · 고객사마다)")
for met, basis, nm in (("order", "order", "수주"), ("prog", "ship", "진행(출하)"), ("final", "tax", "최종(세금계산서)")):
    home = {}
    for x in lines:
        if x[0] == met:
            home[x[2]] = home.get(x[2], 0.0) + x[3]
    rep = {a["name"]: a["total"] for a in REP[basis]["cust_rows"]}
    bad = {k: (home.get(k, 0), rep.get(k, 0)) for k in set(home) | set(rep) if abs(home.get(k, 0) - rep.get(k, 0)) >= 1}
    check(not bad and abs(sum(home.values()) - REP[basis]["total"]) < 1, "%s: 고객사 %d곳 금액 모두 같음 · 합계 %s" % (nm, len(rep), format(int(REP[basis]["total"]), ",")), bad)
want = {"KNK VINA": 1400000, DREAM: 5000000, "한국가상(주)": 3000000 + 700000 + 200000}
got = {c_["customer_name"]: c_["final"] for c_ in S3["top_customers"]}
check(all(abs(got.get(k, 0) - v) < 1 for k, v in want.items()), "최종매출 청구처: KNK VINA 1,400,000 · 가상드림 5,000,000 · 한국가상 3,900,000", got)

print("§2 TOP5 — 「↳ 이 중 최종 고객」 · 최종 고객 기준")
T = {c_["customer_name"]: c_ for c_ in S3["top_customers"]}
check([(v["customer_name"], round(v["final"])) for v in T["KNK VINA"]["vias"]] == [(DREAM, 1400000)], "KNK VINA 줄 아래: 이 중 최종 고객 가상드림 1,400,000", T["KNK VINA"]["vias"])
check([(v["customer_name"], round(v["final"])) for v in T["한국가상(주)"]["vias"]] == [("KNK VINA", 700000)], "한국가상 줄 아래: 이 중 최종 고객 KNK VINA 700,000(반대 방향도)")
check(T[DREAM]["vias"] == [], "청구처 = 최종 고객이면 「이 중」 줄 없음")
E = {c_["customer_name"]: c_ for c_ in S3["top_customers_end"]}
check(abs(E[DREAM]["final"] - 6400000) < 1 and [(v["customer_name"], round(v["final"])) for v in E[DREAM]["vias"]] == [("KNK VINA", 1400000)],
      "최종 고객 기준: 가상드림 6,400,000 = 직접 5,000,000 + KNK VINA 청구 1,400,000", (E[DREAM]["final"], E[DREAM]["vias"]))
check(sorted(k["customer_name"] for k in E[DREAM]["children"]) == ["가상드림(동탄)", "가상드림(아산)"], "최종 고객 기준에서도 종사업장 펼치기(아산·동탄)")
for met in ("order", "prog", "final"):
    sb = sum(c_[met] for c_ in S3["top_customers"])
    se = sum(c_[met] for c_ in S3["top_customers_end"])
    check(abs(sb - se) < 1 and abs(sb - S3["kpi"][met]) < 1, "%s 합계: 청구처 = 최종 고객 = 카드 합계 (%s)" % (met, format(int(sb), ",")), (sb, se, S3["kpi"][met]))

print("§3 깊이 보기 — 기본 청구처 · ?by=end 최종 고객")
u = "/sales/drill?cust=%s&mode=year&year=2026" % DREAM
r1, r2 = cl.get(u), cl.get(u + "&by=end")
check(r1.status_code == 200 and "5,000,000" in r1.text and "6,400,000" not in r1.text, "청구처 기준 가상드림 = 5,000,000")
check(r2.status_code == 200 and "6,400,000" in r2.text and 'name="by" value="end"' in r2.text, "최종 고객 기준 가상드림 = 6,400,000 · 기간 바꿔도 기준 유지")
check(">최종 고객</a>" in r1.text and ">청구처</a>" in r1.text, "깊이 보기에 「고객사 기준: 청구처 / 최종 고객」")

print("§4 화면 글")
h = cl.get("/sales").text
check("청구처 기준" in h and "최종 고객 기준" in h and 'id="z88End"' in h and "매출 보고서와 같은 기준" in h, "매출 홈 TOP5: 기준 전환 · 안내")
check("↳ 이 중 최종 고객" in h and "↳ 이 중 청구처" in h, "줄 아래 「↳ 이 중 …」 두 기준 모두")
rp = cl.get("/sales/report?basis=tax&mode=year&year=2026").text
check("매출 홈 TOP5 와 같은 기준" in rp, "매출 보고서 고객사별 머리 = 「매출 홈 TOP5 와 같은 기준」")

print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
