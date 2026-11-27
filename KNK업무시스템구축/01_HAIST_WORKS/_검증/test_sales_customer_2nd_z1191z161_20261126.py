# -*- coding: utf-8 -*-
"""z1191z161 시험 — 매출 고객사 = 수주 1차 고객사 하나 · 고객사 줄 아래 「└ 2차」(수주 2차 칸)만 · 2차 없으면 줄 없음
  대표 2026-11-26 「매출영업센터 TOP5 에 KNK VINA 아래 SAMSUNG INDIA 가 있는데 이렇게 될 수가 없어 · 『이 중 청구처』 무슨 말이야」
  → 「2차가 없으면 표현하지 마 깔끔하게」 「매출 영업현황·매출보고서 등 이런 문제가 없는지 다시 점검 · 금액은 정말 중요」
  §1 TOP5: KNK VINA 아래 2차(SEV·SEVT·DRT)만 · 첫 수주 고객 SAMSUNG INDIA 가 VINA 아래 안 나옴 · 2차 빈 수주는 줄 없음 · 금액
  §2 수주에 1차 고객사가 비면 관리번호 고객으로 대신하지 않고 「⚠ 고객 미정(확인 필요)」(합계엔 그대로) — 매출 홈·보고서
  §3 화면 글(「최종 고객」「이 중 청구처」「청구처 기준」 없음) · 깊이 보기(?by=end 무시 · 2차 표)
  §4 고객사 상세 총 수주액 = 그 고객 수주 합(발주 달 환율) · 관리번호 금액·고객은 안 씀
  §5 빅터 매출 답 = 매출 홈 계산 · 권한 없으면 금액 없음
  §6 고객 등급 매출 = 수주만(두 번 세기 없음 · 환산) · §7 진행 중인 프로젝트·최근 프로젝트 고객 = 수주 고객
  임시 DB · 가짜 회사 · 운영 아님
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z161-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z161_")
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


VINA, SI, EL = "KNK VINA", "SAMSUNG INDIA (가상)", "가상전기(주)"
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales) "
              "VALUES ('가상대표', 'ceo', 'T1611', 'T1611', 'sso_only_no_local_password', 1, 1, 1, 1)")
    CEO = dict(c.execute("SELECT * FROM users WHERE employee_no='T1611'").fetchone())
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales) "
              "VALUES ('가상직원', 'member', 'T1612', 'T1612', 'sso_only_no_local_password', 1, 1, 0, 0)")
    STAFF = dict(c.execute("SELECT * FROM users WHERE employee_no='T1612'").fetchone())
    CU = {k: ins(c, "customers", {"name": n, "alias": ""}) for k, n in (("V", VINA), ("SI", SI), ("E", EL))}
    c.execute("INSERT OR REPLACE INTO exchange_rates (from_currency, to_currency, rate, rate_date, source) VALUES ('USD','KRW',1400,'2026-05-01','월기준')")
    c.execute("INSERT OR REPLACE INTO exchange_rates (from_currency, to_currency, rate, rate_date, source) VALUES ('USD','KRW',1300,'2026-06-01','월기준')")

    def proj(code, cust, ccy="KRW", amt=0):
        return ins(c, "projects", {"code": code, "name": "P-" + code, "mgmt_code": code, "customer_id": CU[cust], "customer_name": {"V": VINA, "SI": SI, "E": EL}[cust],
                                   "currency": ccy, "order_amount": amt, "status": "진행중", "stage": "수주", "biz_div": code[3], "project_type": "NEW_EQUIP",
                                   "shipment_form": "ASSEMBLY", "order_date": "2026-05-01", "due_date": "2026-05-20", "is_archived": 0})

    def so(pid, no, cust, end, ccy="KRW", total=0, status="SHIPPED", od="2026-05-10"):
        return ins(c, "orders", {"project_id": pid, "order_no": no, "customer_id": CU[cust] if cust else None, "end_customer": end, "so_type": "EQUIPMENT",
                                 "currency": ccy, "status": status, "order_date": od, "due_date": "2026-05-15", "total_amount": total})

    def unit(oid, lbl, amt, us="출하", tax=None):
        r = {"order_id": oid, "unit_label": lbl, "qty": 1, "amount": amt, "unit_status": us, "status_date": "2026-05-12"}
        if tax:
            r.update(tax_invoice_date="2026-05-20", tax_invoice_amt1=tax)
        return ins(c, "order_items", r)

    # 관리번호 P1 = 처음 등록 때 고객 SAMSUNG INDIA(첫 수주) · 관리번호 금액 USD 9,999(유혹 — 쓰면 안 됨)
    P1 = proj("001M2605", "SI", "USD", 9999)
    o1 = so(P1, "M-1", "SI", "", "USD", 1000)          # SAMSUNG INDIA 수주 · 2차 비움 → 2차 줄 없음
    unit(o1, "1호기", 1000, tax=1000)
    o2 = so(P1, "M-2", "V", "SEV", "USD", 2000)        # 같은 관리번호의 KNK VINA 수주 · 2차 SEV
    unit(o2, "1호기", 2000, tax=2000)
    unit(o2, "2호기", 0, us="제작")                     # 출하 전 품목(진행 중인 프로젝트 창)
    # 관리번호 P2 = KNK VINA
    P2 = proj("002T2605", "V")
    o3 = so(P2, "T-3", "V", None, "KRW", 400000)        # 2차 안 정함(NULL) → 2차 줄 없음
    unit(o3, "1호기", 400000, tax=400000)
    o4 = so(P2, "T-4", "V", "SEV 1대, SEVT 1대", "KRW", 1000000)   # 대수 비율로 SEV·SEVT 반씩
    unit(o4, "1호기", 1000000, tax=1000000)
    so(P2, "T-9", "V", "SEV", "KRW", 7777777, status="CANCELLED")   # 취소 수주 — 어디에도 안 들어감
    # 관리번호 P3 = 가상전기 · 수주 고객 비어 있음 → 「고객 미정」(관리번호 고객 가상전기로 대신하지 않음)
    P3 = proj("003T2605", "E")
    o5 = so(P3, "T-5", None, "", "KRW", 250000)
    unit(o5, "1호기", 250000, tax=250000)
    # 소모품 — KNK VINA · 2차 DRT
    ins(c, "consumable_orders", {"co_no": "C1", "mgmt_code": "006C2605", "customer_id": CU["V"], "customer_name": VINA, "secondary_customer": "DRT",
                                 "currency": "KRW", "total_amount": 300000, "status": "SHIPPED", "biz_div": "T", "order_date": "2026-05-02",
                                 "due_date": "2026-05-10", "status_date": "2026-05-11", "tax_invoice_date": "2026-05-31", "tax_invoice_amt1": 300000})

import app.main as M  # noqa: E402
import app.victor as V  # noqa: E402
import app.customer_tier as CT  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
M.get_user = lambda request: CEO
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


def txt(h):
    import html as _h
    return re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ", h))))


oi_map, _ = q(M._board_tax_oi_map)
with D.db_session() as c:
    rates = M._fx_load_rates(c)
    lines = []
    S3 = M._sales_3way(c, rates, oi_map, "year", "2026", "2", "5", detail=lines)
    REP = {b: q(M._sales_report_z17, c, rates, oi_map, b, "year", "2026", "2", "5") for b in ("order", "ship", "tax")}
T = {x["customer_name"]: x for x in S3["top_customers"]}

print("§1 TOP5 — KNK VINA 아래 2차만 · SAMSUNG INDIA 가 VINA 아래 안 나옴")
W_V = 2000 * 1400 + 400000 + 1000000 + 300000     # 고객사 줄 = 고치기 전 청구처 기준과 같은 금액
for met in ("order", "prog", "final"):
    check(abs(T[VINA][met] - W_V) < 1, "KNK VINA %s = %s (수주 3건 + 소모품)" % (met, format(W_V, ",")), T[VINA][met])
check(abs(T[SI]["order"] - 1400000) < 1, "SAMSUNG INDIA 수주 = 1,400,000(자기 수주 M-1 만 · 관리번호 금액 9,999달러 안 씀)", T[SI]["order"])
c2 = {x["name"]: x for x in T[VINA]["c2"]}
check(sorted(c2) == ["DRT", "SEV", "SEVT"], "KNK VINA 아래 2차 = DRT·SEV·SEVT 만", sorted(c2))
check(not any("SAMSUNG" in n for n in c2), "KNK VINA 아래에 SAMSUNG INDIA 없음")
check(abs(c2["SEV"]["order"] - (2800000 + 500000)) < 1 and c2["SEV"]["n"] == 2, "2차 SEV = M-2 2,800,000 + T-4 반 500,000 · 수주 2건", c2["SEV"])
check(abs(c2["SEVT"]["final"] - 500000) < 1 and c2["SEVT"]["n"] == 1, "2차 SEVT = T-4 반 500,000 · 수주 1건", c2["SEVT"])
check(abs(c2["DRT"]["prog"] - 300000) < 1, "2차 DRT = 소모품 300,000", c2["DRT"])
check(T[SI]["c2"] == [], "SAMSUNG INDIA = 2차 빈 수주뿐 → 2차 줄 없음(「2차 없음」 줄도 만들지 않음)", T[SI]["c2"])
check(all(sum(x[m] for x in t["c2"]) <= t[m] + 0.5 for t in S3["top_customers"] for m in ("order", "prog", "final")), "2차 줄 합 ≤ 고객사 줄(모든 고객사·지표)")
check(abs(sum(x["order"] for x in T[VINA]["c2"]) - (W_V - 400000)) < 1, "2차 합 = 고객사 줄 − 2차 안 정한 수주(T-3 400,000)")
for met in ("order", "prog", "final"):
    check(abs(sum(x[met] for x in S3["top_customers"]) - S3["kpi"][met]) < 1, "%s TOP 줄 합 = 카드 합계" % met)
check("top_customers_end" not in S3 and all("vias" not in x for x in S3["top_customers"]), "옛 「최종 고객 기준」·「이 중 …」 자료 없음")

print("§2 고객 미정 — 관리번호 고객으로 대신하지 않음")
check(M.Z161_CUST_TBD in T and abs(T[M.Z161_CUST_TBD]["order"] - 250000) < 1, "수주 고객 빈 T-5 → 「⚠ 고객 미정(확인 필요)」 250,000", list(T))
check(EL not in T, "관리번호 고객 가상전기로 대신 세지 않음")
check(S3["cust_tbd"] and abs(S3["cust_tbd"]["final"] - 250000) < 1, "cust_tbd(TOP5 밖이어도 알림) 금액", S3["cust_tbd"])
rep_c = {a["name"]: a["total"] for a in REP["tax"]["cust_rows"]}
check(abs(rep_c.get(M.Z161_CUST_TBD, 0) - 250000) < 1 and EL not in rep_c, "매출 보고서도 「고객 미정」 250,000 · 가상전기 없음", rep_c)
for met, basis in (("order", "order"), ("prog", "ship"), ("final", "tax")):
    home = {}
    for x in lines:
        if x[0] == met:
            home[x[2]] = home.get(x[2], 0.0) + x[3]
    rep = {a["name"]: a["total"] for a in REP[basis]["cust_rows"]}
    bad = {k: (home.get(k, 0), rep.get(k, 0)) for k in set(home) | set(rep) if abs(home.get(k, 0) - rep.get(k, 0)) >= 1}
    check(not bad, "%s: 매출 홈 고객사별 = 매출 보고서 고객사별" % met, bad)

print("§3 화면")
h = cl.get("/sales?mode=year&year=2026").text
t = txt(h)
for w in ("최종 고객", "이 중 청구처", "이 중 최종 고객", "청구처 기준", "2차 없음", "by=end"):
    check(w not in (h if w == "by=end" else t), "매출 홈에 「%s」 없음" % w)
check("└ 2차 SEV · 수주 2건" in t and "└ 2차 DRT · 수주 1건" in t, "매출 홈 「└ 2차 SEV · 수주 2건」·「└ 2차 DRT · 수주 1건」")
check("고객사 = 세금계산서를 받는 1차 고객사(수주번호마다 적힌 곳)" in t and "그 수주의 장비가 최종 납품·셋업되는 곳" in t, "TOP5 설명 글")
check("⚠ 고객 미정(확인 필요)" in t, "매출 홈 「⚠ 고객 미정」 알림")
check("출하일(없으면 납기) 기준" in t, "진행매출 설명 = 출하일(없으면 납기)")
i = t.find("02 ")
vina_blk = t[t.find(VINA + " ›"):t.find(SI + " ›")] if t.find(SI + " ›") > t.find(VINA + " ›") else t[t.find(VINA + " ›"):]
check("SAMSUNG" not in vina_blk.split("최근 프로젝트")[0], "화면: KNK VINA 줄 묶음 안에 SAMSUNG 글자 없음", vina_blk[:300])
d1 = cl.get("/sales/drill?cust=%s&mode=year&year=2026" % VINA)
d2 = cl.get("/sales/drill?cust=%s&mode=year&year=2026&by=end" % VINA)
td1 = txt(d1.text)
check(d1.status_code == 200 and "최종 고객" not in td1 and "청구처" not in td1, "깊이 보기: 「최종 고객」·「청구처」 단추 없음")
check(td1 == txt(d2.text), "깊이 보기: 옛 주소 ?by=end 는 무시(같은 화면)")
check("└ 2차 SEV" in td1 and "2차 (그 수주의 장비가" in td1, "깊이 보기: 2차 표")
# z1191z170 (대표 11-27 「2차 수주건수를 누르면 어떤 수주인지」): TOP5 「수주 N건」 → 그 2차 수주만 · 건수·금액 = TOP5 그 줄
import urllib.parse as _up
_m = re.search(r"└ 2차 SEV · 수주 (\d+)건 › (₩[\d,]+) (₩[\d,]+) (₩[\d,]+)", t)
check(_m is not None and ("c2=SEV" in h), "매출 홈: 「└ 2차 SEV · 수주 N건」이 누르는 연결", _m and _m.group(0))
_dc = cl.get("/sales/drill?cust=%s&c2=SEV&mode=year&year=2026" % _up.quote(VINA))
_tc = txt(_dc.text)
_f = re.search(r"합계 (₩[\d,]+) (₩[\d,]+) (₩[\d,]+)", _tc)
check(_dc.status_code == 200 and re.search(r"2차 SEV ?가 적힌 수주만", _tc) and _m and re.search(r"수주 %s ?건 ·" % _m.group(1), _tc), "2차로 거른 깊이 보기: 안내 + 수주 건수 = TOP5", _tc[:200])
check(_m and _f and _f.groups() == _m.groups()[1:], "2차로 거른 깊이 보기 합계 = TOP5 「└ 2차 SEV」 줄(수주·진행·최종)", (_m and _m.groups(), _f and _f.groups()))
check("2차 거르기 풀기" in _tc, "2차 거르기 풀기 연결")
da = txt(cl.get("/sales/drill?mode=year&year=2026").text)
check("└ 2차 SEVT" in da, "고객사 전체 보기에도 「└ 2차」 줄")

print("§4 고객사 상세 — 수주 기준")
cap = {}
_ctx0 = M.ctx


def _cap(req, tpl, **kw):
    cap[tpl] = kw
    return _ctx0(req, tpl, **kw)


M.ctx = _cap
r = cl.get("/customer/%d" % CU["SI"])
bd = cap["customer_detail.html"]["pjts_total_bd"]
check(r.status_code == 200 and abs(bd["krw"] - 1400000) < 1 and [(x["currency"], x["total"]) for x in bd["by_ccy"]] == [("USD", 1000.0)],
      "SAMSUNG INDIA 총 수주액 = USD 1,000(≈ 1,400,000) · 관리번호 금액 9,999달러·KNK VINA 수주 안 들어감", bd.get("by_ccy"))
check([s["order_no"] for s in cap["customer_detail.html"]["so_rows"]] == ["M-1"], "SAMSUNG INDIA 수주 목록 = M-1 하나(관리번호 함께)")
r = cl.get("/customer/%d" % CU["V"])
bdv = cap["customer_detail.html"]["pjts_total_bd"]
check(abs(bdv["krw"] - W_V) < 1, "KNK VINA 총 수주액 = 수주 합 %s(취소 T-9 제외 · 매출 홈 수주매출과 같음)" % format(W_V, ","), bdv["krw"])
check(sorted(s["order_no"] for s in cap["customer_detail.html"]["so_rows"]) == ["C1", "M-2", "T-3", "T-4"], "KNK VINA 수주 목록 = M-2·T-3·T-4 + 소모품 C1",
      [s["order_no"] for s in cap["customer_detail.html"]["so_rows"]])
check("M-2" in r.text and "001M2605" in r.text, "KNK VINA 상세에 다른 고객 관리번호의 자기 수주(M-2 · 001M2605)도 보임")
r = cl.get("/customer/%d" % CU["E"])
check(abs(cap["customer_detail.html"]["pjts_total_bd"]["krw"] or 0) < 1 and not cap["customer_detail.html"]["so_rows"], "가상전기(관리번호 고객만) 총 수주액 0 · 수주 없음")
M.ctx = _ctx0

print("§5 빅터 매출 답")
ans = q(V.h_sales, CEO, D.db_session)
check(M._fmt_money(S3["kpi"]["order"], "KRW") in ans["text"], "빅터 올해 수주매출 = 매출 홈 카드(%s)" % M._fmt_money(S3["kpi"]["order"], "KRW"), ans["text"][:200])
check("₩" not in q(V.h_sales, STAFF, D.db_session)["text"], "매출 권한 없는 직원 → 금액 안 보여 줌")

print("§6 고객 등급 매출(12개월)")
got = {}
_sr = CT._score_revenue
CT._score_revenue = lambda a: (got.setdefault("a", a), _sr(a))[1]
with D.db_session() as c:
    CT.compute_customer_tier(c, CU["SI"])
CT._score_revenue = _sr
check(abs(got.get("a", -1) - 1400000) < 1, "SAMSUNG INDIA 12개월 매출 = 1,400,000(수주만 · 달러 환산 · 관리번호 금액 두 번 세기 없음)", got)

print("§7 진행 중인 프로젝트 · 최근 프로젝트 — 고객 = 수주 고객")
with D.db_session() as c:
    op = M._z40_open_projects(c)
p1 = [p for p in op["projects"] if p["pid"] == P1]
check(p1 and p1[0]["cust"] == VINA, "001M2605 진행 창 고객 = 출하 전 품목이 남은 수주 고객 KNK VINA(관리번호 고객 SAMSUNG INDIA 아님)", p1)
cap2 = {}
M.ctx = lambda req, tpl, **kw: (cap2.update(kw), _ctx0(req, tpl, **kw))[1]
cl.get("/sales?mode=year&year=2026")
M.ctx = _ctx0
rc = {d["mgmt_code"]: d for d in cap2["sales_kpi"]["recent"]}
check(rc["001M2605"]["custs_z161"] == [SI, VINA], "최근 프로젝트 001M2605 고객 = 수주 고객(SAMSUNG INDIA 외 1곳)", rc["001M2605"]["custs_z161"])
check(abs(rc["002T2605"]["fx_bd_z104"]["krw"] - 1400000) < 1, "최근 프로젝트 002T2605 금액 = 살아 있는 수주 합 1,400,000(취소 7,777,777 제외)", rc["002T2605"]["fx_bd_z104"]["krw"])

print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
