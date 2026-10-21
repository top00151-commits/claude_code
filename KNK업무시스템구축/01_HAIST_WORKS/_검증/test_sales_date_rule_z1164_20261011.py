#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""z1164 시험 — 매출 홈 날짜·통화를 일정표와 같은 규칙으로(호기 → 수주 → 프로젝트 · 빈 글자('') = 빈칸)
+ 그 달 기준환율이 없어 다른 달로 계산하면 「⚠ 기준환율 미입력 달」 표시
(대표 2026-10-11 「매출·영업 자료 맞춰보기」 → 「일정표와 같은 규칙으로 고치기」 · 「대표님 입력 + 미입력 표시 넣기」).

  §1 진짜 _sales_3way + 진짜 _board_tax_oi_map — 임시 DB(빈 글자·공백 날짜 · 호기 발주일만 · 프로젝트 USD·수주 원화 ·
     프로젝트 원화·수주 USD · 호기 통화가 수주보다 먼저 · 수주 납기가 다른 해 · 취소·폐기 제외 · 소모품 납기 빈 글자 · 환율 대체)
  §2 매출 홈 화면(/sales) — 3지표 숫자 · 「기준환율 미입력 달」 표시 · 환율을 넣으면 표시가 사라짐
  §3 소모품 매출 진단(/admin/consumable-sales-audit) — 매출 홈 ①과 같은 규칙
  §4 원문 — 세 식 · 매출 홈·진단·SO 감사 덤프가 쓰는지 · 옛 함수·관리번호 백필 허용 표시
  §5 배포 전 검사기 + 되돌림

⛔ 운영 DB 를 열지 않는다(임시 DB 만). fastapi 가 깔린 파이썬이 필요하다.
실행:  python _검증/test_sales_date_rule_z1164_20261011.py
"""
import contextlib
import io
import os
import re
import shutil
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "deploy"))
os.environ["KNK_SSO_SERVICE_KEY"] = "z1164-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1164_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                     ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                     ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))

FAIL, CNT = [], 0


def check(name, ok, detail=""):
    global CNT
    CNT += 1
    print(("  ✅" if ok else "  ❌") + " %02d %s" % (CNT, name) + ("" if ok else "   ← %s" % (detail,)))
    if not ok:
        FAIL.append(name)


def proj(c, mc, cust, ccy, od, dd, arch=0):
    return c.execute("INSERT INTO projects(name, mgmt_code, customer_name, currency, order_date, due_date, is_archived) "
                     "VALUES(?,?,?,?,?,?,?)", (mc, mc, cust, ccy, od, dd, arch)).lastrowid


def so(c, pid, no, st, ccy, od, dd):
    return c.execute("INSERT INTO orders(project_id, order_no, status, currency, order_date, due_date) VALUES(?,?,?,?,?,?)",
                     (pid, no, st, ccy, od, dd)).lastrowid


def unit(c, oid, amt, ccy, od, dd, st, t1d=None, t1a=None):
    return c.execute("INSERT INTO order_items(order_id, qty, unit_price, amount, currency, order_date, due_date, unit_status, "
                     "tax_invoice_date, tax_invoice_amt1) VALUES(?,?,?,?,?,?,?,?,?,?)",
                     (oid, 1, amt, amt, ccy, od, dd, st, t1d, t1a)).lastrowid


with D.db_session() as c:
    for ymd, rate in (("2026-08-01", 1500.0), ("2025-12-01", 1400.0)):
        c.execute("INSERT INTO exchange_rates(rate_date, from_currency, to_currency, rate, source) VALUES(?,?,?,?,'월기준')",
                  (ymd, "USD", "KRW", rate))
    # 가: 수주 발주일 빈 글자 → 프로젝트 발주일(2026-01) · 호기 납기 공백 → 수주 납기(2026-02)
    p1 = proj(c, "001T2601", "가상가", "KRW", "2026-01-26", "2026-05-08")
    unit(c, so(c, p1, "T-260107-2", "SHIPPED", "KRW", "", "2026-02-04"), 100, None, None, "  ", "출하")
    # 취소 수주(빠져야 함)
    unit(c, so(c, p1, "T-260130-9", "CANCELLED", "KRW", "2026-01-30", "2026-02-10"), 99999, None, None, "2026-02-10", "출하")
    # 나: 수주·프로젝트 발주일 빈 글자 · 호기 발주일만(일정표에서 넣은 값) → 2026-03
    p2 = proj(c, "002M2602", "가상나", "KRW", "", "2026-07-27")
    unit(c, so(c, p2, "M-260305-9", "CONFIRMED", "KRW", "", ""), 1000, None, "2026-03-05", None, "진행중")
    # 다: 프로젝트 USD · 수주 원화 · 호기 통화 비어 있음 → 원화 172만
    p3 = proj(c, "005M2511", "가상다", "USD", "2025-11-27", "2026-08-19")
    unit(c, so(c, p3, "M-260819-2", "SHIPPED", "KRW", "2026-08-19", "2026-08-19"), 1720000, None, None, "2026-08-19", "출하",
         "2026-08-20", 1720000)
    # 라: 프로젝트 원화 · 수주 USD · 9월(그 달 환율 없음 → 8월 1500)
    p4 = proj(c, "004T2605", "가상라", "KRW", "2026-09-01", "2026-09-10")
    unit(c, so(c, p4, "T-260901-1", "SHIPPED", "USD", "2026-09-01", "2026-09-10"), 10, None, None, "2026-09-10", "출하",
         "2026-09-15", 10)
    # 폐기 프로젝트(빠져야 함)
    p5 = proj(c, "009T2612", "가상폐기", "KRW", "2026-03-01", "2026-03-30", arch=1)
    unit(c, so(c, p5, "T-260301-1", "SHIPPED", "KRW", "2026-03-01", "2026-03-30"), 88888, None, None, "2026-03-30", "출하")
    # 사: 호기 납기 없음 → 수주 납기(2025-12) · 프로젝트 납기(2026-01)보다 먼저 → 2025년
    p6 = proj(c, "010T2601", "가상사", "KRW", "2025-12-01", "2026-01-15")
    unit(c, so(c, p6, "T-251201-1", "SHIPPED", "KRW", "2025-12-01", "2025-12-20"), 500000, None, None, None, "출하")
    # 아: 수주 원화인데 호기 통화 USD → 호기가 먼저 · 2026-02(그 달 환율 없음 → 앞 달 2025-12 1400)
    p7 = proj(c, "011T2602", "가상아", "KRW", "2026-02-02", "2026-03-03")
    unit(c, so(c, p7, "T-260202-1", "CONFIRMED", "KRW", "2026-02-02", "2026-03-03"), 20, "USD", None, None, "진행중")
    # 소모품: 납기 빈 글자 → 발주일
    c.execute("INSERT INTO consumable_orders(co_no, customer_name, total_amount, currency, order_date, due_date, status, "
              "tax_invoice_date, tax_invoice_amt1) VALUES('C-260401-1','가상마',500,'KRW','2026-04-01','','SHIPPED','2026-04-30',500)")

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

print("§1 진짜 _sales_3way (임시 DB)")
oi_map, _pi = M._board_tax_oi_map()
with D.db_session() as c:
    rates = M._fx_load_rates(c)
    r26 = M._sales_3way(c, rates, oi_map, "year", "2026", "1", "1")
    r25 = M._sales_3way(c, rates, oi_map, "year", "2025", "1", "1")
k = r26["kpi"]
check("2026 수주매출 = 100 + 1,000 + 1,720,000 + 15,000 + 28,000 + 500 = 1,764,600",
      round(k["order"]) == 1764600, k["order"])
check("2026 수주매출 6건(취소·폐기 빠짐 · 빈 글자 수주도 셈)", k["order_cnt"] == 6, k["order_cnt"])
check("2026 진행매출 = 100 + 1,720,000 + 15,000 + 500 = 1,735,600", round(k["prog"]) == 1735600, k["prog"])
check("2026 진행매출 4건", k["prog_cnt"] == 4, k["prog_cnt"])
check("2026 최종매출 = 1,720,000(원화 그대로) + 15,000 + 500 = 1,735,500", round(k["final"]) == 1735500, k["final"])
check("2025 수주·진행 = 수주 납기(2025-12)를 따른 50만", (round(r25["kpi"]["order"]), round(r25["kpi"]["prog"])) == (500000, 500000),
      (r25["kpi"]["order"], r25["kpi"]["prog"]))
check("원화 172만 수주가 172만 달러로 셈해지지 않음(최종매출 25억대 아님)", k["final"] < 10_000_000, k["final"])
check("환율 대체 = [USD 2026-02 → 2025-12, USD 2026-09 → 2026-08]",
      r26.get("fx_fallback") == [{"ccy": "USD", "applied": "2025-12", "months": ["2026-02"]},
                                 {"ccy": "USD", "applied": "2026-08", "months": ["2026-09"]}], r26.get("fx_fallback"))
check("환율 자체가 없는 통화는 그대로 missing_fx(이번 자료엔 없음)", r26.get("missing_fx") == [], r26.get("missing_fx"))
by = {b["biz"]: b for b in r26["biz_rows"]}
check("사업부: 검사기 T(100+15,000+28,000) · 자동화 M(1,000+1,720,000) · 소모품 C(500)",
      (round(by["T"]["order"]), round(by["M"]["order"]), round(by["C"]["order"])) == (43100, 1721000, 500),
      {b: round(by[b]["order"]) for b in ("T", "M", "C")})

print("§2 매출 홈 화면(/sales)")
with D.db_session() as c:
    # z1191g(2026-10-21 대표): 관리자는 역할만으로 매출·자재가 열리지 않는다 → 이 시험의 가상 관리자는 센터 4칸을 켠 관리자로
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상관리자', 'admin', 'T901', 'T901', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T901'").fetchone())
M.get_user = lambda request: ADMIN
cl = TestClient(M.app, follow_redirects=False)
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.get("/sales?year=2026")
h = r.text
check("화면 200", r.status_code == 200, r.status_code)
check("3지표 숫자가 화면에(1,764,600 · 1,735,600 · 1,735,500)",
      all(x in h for x in ("1,764,600", "1,735,600", "1,735,500")), [x for x in ("1,764,600", "1,735,600", "1,735,500") if x not in h])
check("「⚠ 기준환율 미입력 달」 표시", "⚠ 기준환율 미입력 달:" in h)
check("USD 2026-09(2026-08 환율로 계산 중)", "USD 2026-09(2026-08 환율로 계산 중)" in h)
check("USD 2026-02(2025-12 환율로 계산 중)", "USD 2026-02(2025-12 환율로 계산 중)" in h)
with D.db_session() as c:
    for ymd, rate in (("2026-09-01", 1600.0), ("2026-02-01", 1450.0)):
        c.execute("INSERT INTO exchange_rates(rate_date, from_currency, to_currency, rate, source) VALUES(?,?,?,?,'월기준')",
                  (ymd, "USD", "KRW", rate))
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.get("/sales?year=2026")
h = r.text
check("그 달 환율을 넣으면 표시가 사라짐", r.status_code == 200 and "기준환율 미입력 달" not in h, r.status_code)
check("넣은 환율로 다시 셈(수주 100+1,000+1,720,000+16,000+29,000+500 = 1,766,600)", "1,766,600" in h)

print("§3 소모품 매출 진단(/admin/consumable-sales-audit)")
with D.db_session() as c:
    p8 = proj(c, "012C2606", "가상자", "KRW", "", "")
    unit(c, so(c, p8, "C-260606-1", "CONFIRMED", "USD", "", ""), 7, None, "2026-06-06", None, "진행중")
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.get("/admin/consumable-sales-audit?year=2026")
h = r.text
check("진단 화면 200", r.status_code == 200, r.status_code)
check("수주·프로젝트 발주일이 빈 글자여도 호기 발주일로 2026 에 잡힘(012C2606)", "012C2606" in h)
check("통화는 수주 통화(USD)", re.search(r"012C2606.{0,400}USD", h, re.S) is not None)

print("§4 원문")
srcM = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
srcD = io.open(os.path.join(ROOT, "app", "database.py"), encoding="utf-8").read()
check("SALES_DD_ORDER = 호기 → 수주 → 프로젝트 · 빈 글자 = 빈칸",
      M.SALES_DD_ORDER == "COALESCE(NULLIF(TRIM(oi.order_date),''),NULLIF(TRIM(o.order_date),''),NULLIF(TRIM(p.order_date),''))")
check("SALES_DD_SHIP = 호기 납기 → 수주 → 프로젝트 납기 → 프로젝트 발주일",
      M.SALES_DD_SHIP == "COALESCE(NULLIF(TRIM(oi.due_date),''),NULLIF(TRIM(o.due_date),''),"
                         "NULLIF(TRIM(p.due_date),''),NULLIF(TRIM(p.order_date),''))")
check("SALES_CCY_ITEM = 호기 → 수주 → 프로젝트",
      M.SALES_CCY_ITEM == "COALESCE(NULLIF(TRIM(oi.currency),''),NULLIF(TRIM(o.currency),''),NULLIF(TRIM(p.currency),''))")
for old in ("COALESCE(o.order_date,p.order_date)", "COALESCE(oi.due_date,p.due_date,p.order_date)",
            "COALESCE(oi.currency,p.currency)", "COALESCE(due_date,order_date)",
            "COALESCE(o.order_date,p.order_date,'')", "COALESCE(o.currency, p.currency, 'KRW')"):
    check("옛 식 없음: %s" % old, old not in srcM)
check("부르는 곳 없는 옛 함수(_sales_delivered) 3줄에 허용 표시", srcM.count("z1164-허용: 부르는 곳 없는 옛 함수") == 3)
check("관리번호 백필(database.py)에 허용 표시", "z1164-허용: 관리번호 백필용 날짜" in srcD)
tpl = io.open(os.path.join(ROOT, "app", "templates", "sales_home.html"), encoding="utf-8").read()
check("매출 홈 화면이 fx_fallback 을 보여 줌", "s3.fx_fallback" in tpl)

print("§5 배포 전 검사기 + 되돌림")
import check_standards as CS                               # noqa: E402
with contextlib.redirect_stdout(io.StringIO()):
    now_bad = CS.check_date_fallback([])
check("지금 코드: 위반 0", now_bad == [], now_bad[:3])
_root = CS.ROOT
MUT = [
    ("app/main.py", '            + SALES_DD_ORDER + " AS dd "', '            "COALESCE(o.order_date,p.order_date) AS dd "', "①",
     "수주매출 날짜를 옛 식으로"),
    ("app/main.py", "SALES_DD_SHIP = (\"COALESCE(NULLIF(TRIM(oi.due_date),''),NULLIF(TRIM(o.due_date),''),\"",
     "SALES_DD_SHIP = (\"COALESCE(NULLIF(TRIM(o.due_date),''),NULLIF(TRIM(oi.due_date),''),\"", "②", "납기 순서를 수주 먼저로"),
    ("app/main.py", "SALES_CCY_ITEM = (\"COALESCE(NULLIF(TRIM(oi.currency),''),NULLIF(TRIM(o.currency),''),\"",
     "SALES_CCY_ITEM = (\"COALESCE(NULLIF(TRIM(oi.currency),''),\"", "②", "통화에서 수주를 뺌"),
    ("app/main.py", "                fx_fb.setdefault((_fc, _fym), set()).add(dd[:7])\n", "                pass\n", "③",
     "환율 대체 기록을 뺌"),
    ("app/main.py", 'p.order_date) AS dd "   # z1164-허용: 부르는 곳 없는 옛 함수(매출 홈은 _sales_3way)',
     'p.order_date) AS dd "', "①", "옛 함수의 허용 표시를 지움"),
    ("app/main.py", '                + SALES_CCY_ITEM + " AS ccy, "', '                "COALESCE(oi.currency,p.currency) AS ccy, "', "①",
     "소모품 진단 통화를 옛 식으로"),
    ("app/templates/sales_home.html", "{% if s3.fx_fallback %}", "{% if false %}", "④", "매출 홈의 환율 대체 표시를 뺌"),
]
for rel, old, new, mark, what in MUT:
    tmp = tempfile.mkdtemp(prefix="mut_z1164_")
    try:
        os.makedirs(os.path.join(tmp, "app", "templates"))
        for f in os.listdir(os.path.join(ROOT, "app")):
            if f.endswith(".py"):
                shutil.copyfile(os.path.join(ROOT, "app", f), os.path.join(tmp, "app", f))
        shutil.copyfile(os.path.join(ROOT, "app", "templates", "sales_home.html"),
                        os.path.join(tmp, "app", "templates", "sales_home.html"))
        p = os.path.join(tmp, rel)
        s = io.open(p, encoding="utf-8", newline="").read()
        nl = "\r\n" if "\r\n" in s else "\n"
        s2 = s.replace("\r\n", "\n")
        assert s2.count(old) == 1, (rel, old[:50], s2.count(old))
        s2 = s2.replace(old, new)
        io.open(p, "w", encoding="utf-8", newline="").write(s2.replace("\n", nl))
        CS.ROOT = tmp
        with contextlib.redirect_stdout(io.StringIO()):
            got = CS.check_date_fallback([])
    finally:
        CS.ROOT = _root
        shutil.rmtree(tmp, ignore_errors=True)
    check("되돌림 「%s」 → %s 로 잡힘" % (what, mark), any(m_.startswith(mark) for _f, _l, m_ in got), [x[2][:60] for x in got][:3])

print("")
print("결과: %d개 중 실패 %d" % (CNT, len(FAIL)))
for f in FAIL:
    print("   ❌", f)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if FAIL else 0)
