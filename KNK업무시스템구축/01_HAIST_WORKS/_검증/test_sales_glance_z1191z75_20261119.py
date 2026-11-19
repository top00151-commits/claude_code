# -*- coding: utf-8 -*-
"""z1191z75 시험 (대표 2026-11-19 「이 페이지를 한번에 쉽게 알아볼수있게 책갈피 형태로 페이지를 한장더 만들었으면 좋겠어 …
  지금 페이지는 그냥 두고 하나더 페이지를 만들어서 그래프나 다른 방식으로 … 누구나 쉽게 이해하고 알아볼수있게」)
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z75-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z75_")
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



print("§1 금액 줄여 보이기(억·만)")
W_ = M._z75_won
check([W_(36804119183), W_(4900000), W_(83380000), W_(0), W_(None), W_(5000), W_(123456789012)] == ["368.0억", "490만", "8,338만", "0", "0", "5,000원", "1,234.6억"],
      "368.0억 · 490만 · 8,338만 · 0 · 5,000원 · 1,234.6억", [W_(36804119183), W_(4900000), W_(83380000), W_(5000), W_(123456789012)])

print("§2 숫자 = 매출 홈과 같은 계산(원 단위까지)")
h1 = q(cl.get, "/sales?mode=year&year=2026").text
h2 = q(cl.get, "/sales/glance?mode=year&year=2026").text
n1 = re.findall(r'<div class="kpi-num"[^>]*>([\d,]+)<', h1)[:3]
n2 = dict(re.findall(r'class="z75-k" data-v="(\w+)"[^>]*\n\s*title="[^"]* ([\d,]+)원"', h2))
check(n1 and [n2.get("order"), n2.get("prog"), n2.get("final")] == n1, "카드 3장 원 단위 = 숫자 화면 카드", (n1, n2))
check("590만" in h2 and "진행매출" in h2, "진행매출 590만(억·만으로 줄여 보임)")

print("§3 책갈피 — 두 화면 오가기 · 기간 따라감")
check('href="/sales/glance?mode=year&amp;year=2026&amp;q=' in h1 and "📈 한눈에 보기" in h1 and 'class="z75-tab on" aria-current="page">🔢 숫자로 보기' in h1,
      "숫자 화면: 「🔢 숫자로 보기」 켜짐 + 「📈 한눈에 보기」 책갈피(같은 기간)")
check('class="z75-tab on" aria-current="page">📈 한눈에 보기' in h2 and 'href="/sales?mode=year&amp;year=2026' in h2, "한눈에 화면: 「📈 한눈에 보기」 켜짐 + 숫자 화면으로 돌아가는 책갈피")
check("kpi-num" in h1 and "사업부별 매출" in h1 and "TOP 5 고객사" in h1, "숫자 화면 내용은 그대로")

print("§4 그래프 자료")
with D.db_session() as c:
    rates = M._fx_load_rates(c)
    L, Y = [], {}
    S = q(M._sales_3way, c, rates, OI, "year", "2026", "1", "1", detail=L, ym=Y)
    S0 = q(M._sales_3way, c, rates, OI, "year", "2026", "1", "1")
check(S["kpi"] == S0["kpi"] and S["top_customers"] == S0["top_customers"], "월별 합계(ym)를 받아도 매출 홈 숫자는 그대로")
import datetime as _dt
G = {g["key"]: g for g in M._z75_glance(S, L, Y, "year", "2026", "1", "1", _dt.date(2026, 11, 19))}
gp = G["prog"]
check([round(x["v"]) for x in gp["months"]] == [0, 0, 0, 0, 5900000, 0, 0, 0, 0, 0, 0, 0] and gp["months"][4]["h"] == 100 and gp["best"]["m"] == 5,
      "월별: 진행매출 5월 590만(가장 큰 달 = 막대 100%)", [round(x["v"]) for x in gp["months"]])
check(gp["months"][11]["future"] and not gp["months"][10]["future"], "오늘(11-19) 뒤 12월은 「아직」으로 흐리게")
check(abs(sum(x["v"] for x in gp["months"]) - S["kpi"]["prog"]) < 1, "월별 합 = 진행매출 합")
cu = {x["name"]: x for x in gp["cust"]}
check(round(cu["삼성전기(주)"]["v"]) == 3400000 and cu["삼성전기(주)"]["kids"] == [], "고객사: 삼성전기(주) 340만(등록명 합산)", cu.get("삼성전기(주)"))
check(round(cu["(주) 드림텍"]["v"]) == 1200000 and [(k["name"], k["txt"]) for k in cu["(주) 드림텍"]["kids"]] == [("드림텍(동탄)", "50만"), ("드림텍(아산)", "40만"), ("드림텍(본사)", "30만")],
      "드림텍 = 막대 하나 120만 · 아래 작은 글 동탄 50만 · 아산 40만 · 본사 30만", cu.get("(주) 드림텍"))
check(gp["cust"][0]["name"] == "삼성전기(주)" and gp["cust"][0]["w"] == 100 and abs(sum(x["pct"] for x in gp["cust"]) + gp["rest_pct"] - 100) < 0.01,
      "큰 순 · 1위 막대 100% · 비율 합 100%")
check(gp["biz"] and abs(sum(b["pct"] for b in gp["biz"]) - 100) < 0.01 and all(b["v"] > 0 for b in gp["biz"]), "사업부: 0 은 빼고 비율 합 100%", gp["biz"])
check("고객사 1위 삼성전기(주)" in gp["summary"] and "사업부 1위" in gp["summary"], "한 줄 요약", gp["summary"])
gf = G["final"]
check(round(gf["total"]) == round(S["kpi"]["final"]) and [round(x["v"]) for x in gf["months"]][4] == round(S["kpi"]["final"]), "최종매출도 같은 규칙(5월 발행분)", [round(x["v"]) for x in gf["months"]])

print("§5 화면 — 기준 고르기 · 기간 바꾸기")
check(h2.count('class="z75-v"') == 3 and h2.count(" hidden>") >= 2 and 'data-v="prog" aria-pressed="true"' not in h2, "그래프 묶음 3개(처음엔 하나만 보임)")
check('data-v="prog" style="--kc:#15803d;" aria-pressed="true"' in h2, "처음 기준 = 진행매출")
h3 = q(cl.get, "/sales/glance?mode=quarter&year=2026&q=2&v=final").text
check('data-v="final" style="--kc:#b45309;" aria-pressed="true"' in h3 and "2026년 2분기" in h3, "주소의 v=final · 분기 그대로 열림")
check("고른 기간은 진하게" in h3 and h3.count('z75-mcol off') == 27, "분기: 월별은 1~12월 · 고른 3달 밖 9달은 흐리게(기준 3묶음 × 9)", h3.count('z75-mcol off'))
check(q(cl.get, "/sales/glance?mode=month&year=2026&m=5&v=zzz").status_code == 200, "이상한 v 도 진행매출로 열림")
check(q(cl.get, "/sales/glance?year=2019").status_code == 200, "자료 없는 해도 열림")
check("'&v='+encodeURIComponent(cur)" in h2 and "history.replaceState" in h2, "기간을 바꿔도 보던 기준 유지 · 카드 고르면 주소에 남김")

print("§6 권한 — 매출 못 보는 사람은 못 들어감")
M.get_user = lambda request: dict(ADMIN, role="member", can_view_sales=0, can_use_sales=0)
r_ = q(cl.get, "/sales/glance")
check(r_.status_code in (302, 303) and "no_perm=sales" in r_.headers.get("location", ""), "매출 권한 없으면 /home?no_perm=sales", (r_.status_code, r_.headers.get("location")))
M.get_user = lambda request: ADMIN

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
