# -*- coding: utf-8 -*-
"""z1191z73 시험 (대표 2026-11-19 「매출집계에서 고객사 명은 고객사명 등록명으로 … 종사업장번호가 여러개 있는 고객사는 시스템명으로 … 각각 매출이 얼마인지」
  + 「드림텍 경우 고객사 등록명으로 합산으로 보여주는데 펼치기 누르면 시스템명으로 구분해서 얼마인지 각각」)
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z73-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z73_")
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
    S0 = q(M._sales_3way, c, rates, OI, "year", "2026", "1", "1")
    DA = M._z45_drill(c, L, "", "")
    DS = M._z45_drill(c, L, "", "삼성전기(주)")
    DG = M._z45_drill(c, L, "", "(주) 드림텍")
    DD = M._z45_drill(c, L, "", "드림텍(아산)")
trip = lambda d: (round(d["order"]), round(d["prog"]), round(d["final"]))
R = {r["cust"]: r for r in DA["rows"]}

print("§1 매출 집계 고객사 = 등록명")
# z1191z161 (대표 11-26): 수주에 1차 고객사가 비면 관리번호에 적힌 글자(번호없는고객)로 대신하지 않고 「⚠ 고객 미정(확인 필요)」
check(sorted(R) == sorted(["삼성전기(주)", "(주) 드림텍", "가상무별칭(주)", "⚠ 고객 미정(확인 필요)"]), "고객사 = 등록명(수주 고객사가 비면 「⚠ 고객 미정」)", sorted(R))
check(trip(R["삼성전기(주)"]) == (3400000, 3400000, 1400000), "삼성전기(주) = 등록명·시스템명으로 적힌 건 + 소모품 한 줄로(수주 340만 · 진행 340만 · 최종 140만)", trip(R["삼성전기(주)"]))
check(R["삼성전기(주)"]["children"] == [] and R["가상무별칭(주)"]["children"] == [], "종사업장이 하나뿐인 고객사는 펼치기 없음")
check(trip(DA["tot"]) == (round(S["kpi"]["order"]), round(S["kpi"]["prog"]), round(S["kpi"]["final"])) == (5900000, 5900000, 1800000), "합계는 그대로(전체 = 매출 홈 카드)", trip(DA["tot"]))
check(S["kpi"] == S0["kpi"] and S["top_customers"] == S0["top_customers"], "깊이 보기 줄을 모아도 매출 홈 숫자 같음")

print("§2 한 회사 여러 종사업장 — 등록명 한 줄 합산 · 펼치면 시스템명별")
g = R["(주) 드림텍"]
check(trip(g) == (1200000, 1200000, 400000) and g["n"] == 3, "등록명이 같은 드림텍 3곳(띄어쓰기만 다른 것 포함) = 「(주) 드림텍」 한 줄 합산(수주 120만 · 최종 40만 · 수주 3건)", (trip(g), g["n"]))
check([(k["cust"], round(k["order"]), round(k["final"]), k["n"]) for k in g["children"]] == [("드림텍(동탄)", 500000, 0, 1), ("드림텍(아산)", 400000, 400000, 1), ("드림텍(본사)", 300000, 0, 1)],
      "펼치면 드림텍(동탄) 50만 · (아산) 40만(최종 40만) · (본사) 30만 — 진행매출 순", [(k["cust"], trip(k), k["n"]) for k in g["children"]])
check(sum(k["order"] for k in g["children"]) == g["order"] and sum(k["final"] for k in g["children"]) == g["final"], "펼친 줄 합 = 등록명 줄")
TOP = {t["customer_name"]: t for t in S["top_customers"]}
check(list(TOP)[0] == "삼성전기(주)" and [k["customer_name"] for k in TOP["(주) 드림텍"]["children"]] == ["드림텍(동탄)", "드림텍(아산)", "드림텍(본사)"] and TOP["삼성전기(주)"]["children"] == [],
      "매출 홈 TOP5: 등록명 · 드림텍만 펼칠 줄 3개", {k: [x["customer_name"] for x in v["children"]] for k, v in TOP.items()})

print("§3 고객사 눌러 들어가기(수주별)")
check(sorted(r["so"] for r in DS["rows"]) == ["C-1", "T-260505-1", "T-260505-2"], "삼성전기(주) → 수주 3줄", [r["so"] for r in DS["rows"]])
check(sorted(r["so"] for r in DG["rows"]) == ["T-260505-3", "T-260505-4", "T-260505-5"] and trip(DG["tot"]) == trip(g), "(주) 드림텍 → 세 사업장 수주 모두 · 합계 = 표 줄", [r["so"] for r in DG["rows"]])
check([r["so"] for r in DD["rows"]] == ["T-260505-4"], "펼친 줄 드림텍(아산) → 아산 수주만", [r["so"] for r in DD["rows"]])

print("§4 화면")
h = q(cl.get, "/sales/drill?mode=year&year=2026").text
check(">삼성전기(주) ›<" in h and ">(주) 드림텍 ›<" in h, "고객사별 매출: 등록명 줄", None)
check('class="z73-tg" data-z73="d2" aria-expanded="false"' in h and "</span>3곳</button>" in h and h.count('class="z73-tg"') == 1, "드림텍 줄에만 「▸ 3곳」 펼치기 단추")
kids = re.findall(r'<tr class="z73-ch z73p-(d\d+)" hidden>.*?cust=([^&"]+)', h, re.S)
check([k[0] for k in kids] == ["d2"] * 3 and len(kids) == 3, "펼칠 줄 3개(처음엔 숨김 · 드림텍 줄에 딸림)", kids)
check("cust=%EB%93%9C%EB%A6%BC%ED%85%8D%28%EC%95%84%EC%82%B0%29" in h, "펼친 줄 「드림텍(아산) ›」을 누르면 아산만 보기")
check("tb.querySelectorAll('.z73p-'+g" in h, "머리글 정렬해도 펼친 줄은 제 회사 밑에")   # z1191z161: 2차 줄(.z161p-)도 함께 옮김
hh = q(cl.get, "/sales?mode=year&year=2026").text
check('data-z73="t' in hh and 'class="z73p-t' in hh and "삼성전기(주)" in hh, "매출 홈 TOP5: 등록명 · 드림텍 펼치기 단추와 숨은 줄")
hd = q(cl.get, "/sales/drill?mode=year&year=2026&cust=" + __import__("urllib.parse").parse.quote("(주) 드림텍")).text
check("T-260505-3" in hd and "T-260505-4" in hd and "T-260505-5" in hd, "「(주) 드림텍 ›」 화면 = 세 사업장 수주")

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
