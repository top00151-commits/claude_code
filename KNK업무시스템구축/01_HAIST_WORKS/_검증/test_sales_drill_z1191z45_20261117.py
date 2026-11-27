# -*- coding: utf-8 -*-
"""z1191z45 시험 (대표 2026-11-17 「TOP5 고객사 이름을 누르면 고객사 등록 화면이 아니라 그 고객사의 수주·진행·최종 매출이
  어떤 항목으로 이루어졌는지 · 사업부별 매출도 사업부를 누르면 그 사업부의 고객사별 수주·진행·최종」)
  ① 사업부 → 고객사별(진행매출 순) · 합계 = 매출 홈 사업부 줄
  ② 고객사 → 수주(소모품 발주)별 · 합계 = 매출 홈 TOP5 그 고객사 줄 · 사업부별 소계 · 기간 밖 수주의 진행매출만 있는 줄
     · 발주일 = 수주매출이 쓰는 날짜(수주 발주일 칸이 비면 호기 발주일 — 운영에 있음)
  ③ 매출 홈 링크(사업부 · TOP5 고객사 · 고객사 전체 보기) · 권한
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z45-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z45_")
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
              "VALUES ('가상관리자', 'admin', 'T945', 'T945', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T945'").fetchone())
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('물류만', 'user', 'T946', 'T946', 'sso_only_no_local_password', 1, 1, 0, 0, 1, 1)")
    NOSALES = dict(c.execute("SELECT * FROM users WHERE employee_no='T946'").fetchone())
    LG = ins(c, "customers", {"name": "엘지전자", "alias": "엘지전자"})
    DT = ins(c, "customers", {"name": "드림텍(아산)", "alias": "드림텍(아산)"})

    def proj(code, cid, cname, model, equip, od="2026-05-05"):
        return ins(c, "projects", {"code": code, "mgmt_code": code, "name": "PBA", "model_name": model, "equip_name": equip,
                                   "biz_div": code[3], "customer_id": cid, "customer_name": cname, "status": "진행중",
                                   "currency": "KRW", "order_date": od, "due_date": "2026-06-30", "is_archived": 0})

    def order(pid, cid, no, od, status="CONFIRMED"):
        return ins(c, "orders", {"order_no": no, "project_id": pid, "customer_id": cid, "order_date": od,
                                 "due_date": "2026-06-15", "status": status, "currency": "KRW"})

    def item(oid, key, us, amt, od, ship=None):
        IT[key] = ins(c, "order_items", {"order_id": oid, "qty": 1, "unit_price": amt, "amount": amt, "unit_status": us,
                                         "status_date": ship, "due_date": "2026-06-10", "order_date": od, "currency": "KRW", "unit_label": key})

    P1 = proj("001T2605", LG, "엘지전자", "LM-V600", "OS 검사기")
    o = order(P1, LG, "T-1", "2026-05-05"); item(o, "a1", "출하", 1000000, "2026-05-05", "2026-05-15"); item(o, "a2", "진행중", 2000000, "2026-05-05")
    o = order(P1, LG, "T-4", "2025-12-01"); item(o, "a4", "출하", 700000, "2025-12-01", "2026-05-10")     # 작년 수주 · 올해 출하
    o = order(P1, LG, "T-9", "2026-05-06", "CANCELLED"); item(o, "a9", "출하", 9999, "2026-05-06", "2026-05-16")   # 취소 → 뺌
    P2 = proj("002M2605", LG, "엘지전자", "HCM", "STOCKER", od="")
    o = order(P2, LG, "M-1", ""); item(o, "m1", "출하", 3000000, "2026-04-01", "2026-06-01")   # 운영처럼 수주 발주일 칸이 빔 → 호기 발주일
    P3 = proj("003T2605", DT, "드림텍(아산)", "WATCH9", "PPG 검사기")
    o = order(P3, DT, "T-3", "2026-03-03"); item(o, "d1", "출하", 500000, "2026-03-03", "2026-03-20")
    CO = ins(c, "consumable_orders", {"co_no": "C-1", "mgmt_code": "001C2605", "customer_name": "엘지전자", "customer_id": LG, "currency": "KRW",
                                      "total_amount": 400000, "status": "SHIPPED", "biz_div": "T", "order_date": "2026-05-02", "due_date": "2026-05-10",
                                      "status_date": "2026-05-10", "tax_invoice_date": "2026-05-20", "tax_invoice_amt1": 400000,
                                      "model_name": "소모품", "equip_name": "핀 2종", "project_name": "SENSOR"})

OI = {IT["a1"]: {"t1d": "2026-05-20", "t1a": 1000000}, IT["d1"]: {"t1d": "2026-03-25", "t1a": 500000}}

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
CUR = {"u": ADMIN}
M.get_user = lambda request: CUR["u"]
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
    DB = M._z45_drill(c, L, "T", "")
    DA = M._z45_drill(c, L, "", "")
    DC = M._z45_drill(c, L, "", "엘지전자")
    DCT = M._z45_drill(c, L, "T", "엘지전자")
BIZ = {b["biz"]: b for b in S["biz_rows"]}
TOP = {t["customer_name"]: t for t in S["top_customers"]}
trip = lambda d: (round(d["order"]), round(d["prog"]), round(d["final"]))

print("§0 매출 홈 숫자는 그대로")
check(S["kpi"] == S0["kpi"] and S["biz_rows"] == S0["biz_rows"] and S["top_customers"] == S0["top_customers"], "깊이 보기 줄을 모아도 매출 홈 합계·사업부·TOP5 같음")

print("§1 사업부 → 고객사별")
check([r["cust"] for r in DB["rows"]] == ["엘지전자", "드림텍(아산)"], "검사기: 고객사 2곳 · 진행매출 순", [r["cust"] for r in DB["rows"]])
check(trip(DB["rows"][0]) == (3000000, 1700000, 1000000) and DB["rows"][0]["n"] == 2,
      "엘지전자(검사기): 수주 300만(T-1) · 진행 170만(T-1 100만 + 작년 수주 T-4 70만) · 최종 100만 · 수주 2건(취소 T-9 뺌)", (trip(DB["rows"][0]), DB["rows"][0]["n"]))
check(trip(DB["tot"]) == trip(BIZ["T"]), "합계 = 매출 홈 「사업부별 매출」 검사기 줄", (trip(DB["tot"]), trip(BIZ["T"])))
check(trip(DA["tot"]) == (round(S["kpi"]["order"]), round(S["kpi"]["prog"]), round(S["kpi"]["final"])), "사업부 전체 = 매출 홈 합계")
for nm in TOP:
    r = next(x for x in DA["rows"] if x["cust"] == nm)
    check(trip(r) == trip(TOP[nm]), "고객사 전체 보기의 %s = TOP5 줄" % nm, (trip(r), trip(TOP[nm])))

print("§2 고객사 → 수주별")
check(trip(DC["tot"]) == trip(TOP["엘지전자"]) == (6400000, 5100000, 1400000), "엘지전자 합계 = TOP5 엘지전자 줄(수주 640만 · 진행 510만 · 최종 140만)", trip(DC["tot"]))
check([r["so"] for r in DC["rows"]] == ["M-1", "T-1", "T-4", "C-1"], "한 줄 = 수주번호 하나(소모품은 발주번호) · 진행매출 순 · 취소 T-9 없음", [r["so"] for r in DC["rows"]])
R = {r["so"]: r for r in DC["rows"]}
check(trip(R["T-4"]) == (0, 700000, 0) and R["T-4"]["od"] == "2025-12-01", "작년 수주 T-4 = 올해 진행매출만(수주매출 0) · 발주일 2025-12-01", R["T-4"])
check(R["M-1"]["od"] == "2026-04-01", "수주 발주일 칸이 비면 수주매출과 같은 날짜(호기 발주일)", R["M-1"]["od"])
check((R["T-1"]["code"], R["T-1"]["id"], R["T-1"]["model"], R["T-1"]["equip"], R["T-1"]["label"]) == ("001T2605", P1, "LM-V600", "OS 검사기", M.SALES3_BIZ_LABEL["T"]),
      "수주 줄: 관리번호 · 프로젝트 · 모델명 · 설비명 · 사업부", R["T-1"])
check((R["C-1"]["kind"], R["C-1"]["id"], R["C-1"]["equip"], R["C-1"]["biz"], R["C-1"]["od"]) == ("C", CO, "핀 2종", "CT", "2026-05-02"), "소모품 줄: 소모품 화면 · 소모품(검사기) · 발주일", R["C-1"])
check([s["biz"] for s in DC["biz_sub"]] == ["T", "M", "CT"] and trip(DC["biz_sub"][1]) == (3000000, 3000000, 0), "사업부별 소계(검사기 · 자동화 · 소모품(검사기))", [(s["biz"], trip(s)) for s in DC["biz_sub"]])
check([r["so"] for r in DCT["rows"]] == ["T-1", "T-4"] and trip(DCT["tot"]) == trip(DB["rows"][0]), "엘지전자 + 검사기만 = 사업부 화면의 엘지전자 줄", [r["so"] for r in DCT["rows"]])

print("§3 화면")
P = "mode=year&year=2026&q=1&m=1"
h = q(cl.get, "/sales?" + P).text
# z1191z179 (대표 11-27): 소모품이 있으면 사업부 줄 = 사업부 + 그 소모품(TA) · 없으면 예전처럼 T
check(('href="/sales/drill?biz=T&amp;mode=year&amp;year=2026' in h) or ('href="/sales/drill?biz=TA&amp;mode=year&amp;year=2026' in h), "매출 홈 「사업부별 매출」 사업부 → 깊이 보기")
check("📦 소모품</a>" in h and 'href="/sales/drill?biz=CT&amp;' in h and 'href="/sales/drill?biz=TA&amp;' in h, "z1191z179: 검사기 줄 = 소모품 포함 · 아래 「└ 📦 소모품」 줄(소모품만 깊이 보기)")
_hta = q(cl.get, "/sales/drill?biz=TA&" + P)
check(_hta.status_code == 200 and "검사기(소모품 포함)" in _hta.text, "z1191z179: 깊이 보기 TA = 검사기 + 소모품(검사기)")
check(('href="/sales/drill?cust=%s&amp;mode=year' % quote("엘지전자")) in h, "매출 홈 TOP5 고객사 → 그 고객사 매출 내역")
check('/customers?q=' not in h, "TOP5 고객사 이름이 더는 고객사 등록 화면으로 안 감")
check('고객사 전체 보기' in h, "TOP5 옆 「고객사 전체 보기」")
r = q(cl.get, "/sales/drill?biz=T&" + P)
hb = r.text
check(r.status_code == 200 and "고객사별 매출" in hb, "사업부 깊이 보기 열림", r.status_code)
check(re.findall(r'<a class="cu" href="/sales/drill\?cust=[^"]+"[^>]*>([^<]+) ›</a>', hb) == ["엘지전자", "드림텍(아산)"], "고객사 줄 · 누르면 그 고객사(검사기)")
check("3,500,000" in hb and "2,200,000" in hb and "1,500,000" in hb, "합계 줄(수주 350만 · 진행 220만 · 최종 150만)")
r = q(cl.get, "/sales/drill?cust=%s&%s" % (quote("엘지전자"), P))
hc = r.text
check(r.status_code == 200 and "엘지전자" in hc and "매출 내역" in hc, "고객사 깊이 보기 열림", r.status_code)
check(('href="/project/%d?so=T-1"' % P1) in hc and ('href="/consumables/%d"' % CO) in hc, "수주번호 → 그 수주의 프로젝트 · 소모품 → 소모품 화면")
check(re.findall(r'<a class="dr-so"[^>]*>([^<]+)</a>', hc) == ["M-1", "T-1", "T-4", "C-1"], "수주 줄 순서(진행매출 순)")
check("6,400,000" in hc and "5,100,000" in hc and "1,400,000" in hc, "합계 = TOP5 엘지전자")
check("사업부별" in hc and "📦" in hc, "사업부별 소계 표")
check('data-knk-fill' in hc and 'data-knk-back' in hc, "표 높이 자동 · 매출 홈으로 돌아가기")
he = q(cl.get, "/sales/drill?cust=%s&mode=year&year=2024" % quote("엘지전자")).text
check("이 기간에 매출이 없습니다" in he, "매출 없는 기간 안내")
CUR["u"] = NOSALES
r2 = q(cl.get, "/sales/drill?biz=T")
check(r2.status_code == 303 and "no_perm=sales" in r2.headers.get("location", ""), "매출 권한 없으면 못 들어옴(안내로)", (r2.status_code, r2.headers.get("location")))
CUR["u"] = ADMIN

print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
