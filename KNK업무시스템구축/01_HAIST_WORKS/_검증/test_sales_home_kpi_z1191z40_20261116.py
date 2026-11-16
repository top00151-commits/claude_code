# -*- coding: utf-8 -*-
"""z1191z40 시험 (대표 2026-11-16 「ⓘ 설명이랑 건수·진행프로젝트 기준 모두 진행해 · 진행프로젝트는 클릭하면 어떤 항목이 진행되고 있는지」)
  ① 매출 홈 카드 건수 = 수주번호 수 + 소모품 발주 수(호기·부품 줄 수가 아님) — 세 지표 모두 · 매출 보고서 「건수」(z33)와 같은 값
  ② 진행 프로젝트 = 작업일정표에 출하 전 품목이 남은 프로젝트(프로젝트 상태 칸이 아니라) · 보류·취소 수주·폐기 프로젝트 뺌 · 가까운 납기 순
  ③ ⓘ 설명 기간(연간·분기·월 · 윤년) · 화면: ⓘ 4개 · 목록 창 · 건수 글
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z40-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z40_")
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


ITEMS = {}
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상관리자', 'admin', 'T940', 'T940', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T940'").fetchone())
    CU = ins(c, "customers", {"name": "엘지전자", "alias": "엘지전자"})

    def proj(code, status, archived=0):
        return ins(c, "projects", {"code": code, "mgmt_code": code, "name": "시험 " + code, "model_name": "MDL-" + code[-4:],
                                   "biz_div": code[3], "customer_id": CU, "customer_name": "엘지전자", "status": status,
                                   "currency": "KRW", "order_date": "2026-05-05", "due_date": "2026-06-30", "is_archived": archived})

    def order(pid, no, status="CONFIRMED"):
        return ins(c, "orders", {"order_no": no, "project_id": pid, "customer_id": CU, "order_date": "2026-05-05",
                                 "due_date": "2026-06-15", "status": status, "currency": "KRW"})

    def item(oid, key, us, due="2026-05-30", amt=1000000, label="1호기"):
        ITEMS[key] = ins(c, "order_items", {"order_id": oid, "qty": 1, "unit_price": amt, "amount": amt, "unit_status": us,
                                            "status_date": "2026-05-15" if us == "출하" else None, "due_date": due,
                                            "order_date": "2026-05-05", "currency": "KRW", "unit_label": label})

    # P1: 상태 칸은 「출하」인데 덜 나감(출하 전 1) — 수주 T-1(품목 3 · 부품 줄 포함) · T-2(다 나감)
    P1 = proj("001T2605", "출하")
    o = order(P1, "T-1"); item(o, "a1", "출하"); item(o, "a2", "출하", label="부품A"); item(o, "a3", "진행중", due="2026-05-30")
    o = order(P1, "T-2"); item(o, "b1", "출하"); item(o, "b2", "출하", label="2호기")
    # P2: 상태 칸은 「수주확정」인데 다 나감 → 진행 아님
    P2 = proj("002M2605", "수주확정"); o = order(P2, "M-1"); item(o, "m1", "출하")
    # P3: 「진행중」이지만 보류 품목만 → 진행 아님(보류)
    P3 = proj("003T2605", "진행중"); o = order(P3, "T-3"); item(o, "h1", "보류")
    # P4: 취소 수주의 진행중 품목 → 뺌
    P4 = proj("004T2605", "진행중"); o = order(P4, "T-4", "CANCELLED"); item(o, "x1", "진행중")
    # P5: 폐기 프로젝트 → 뺌
    P5 = proj("005T2605", "진행중", archived=1); o = order(P5, "T-5"); item(o, "z1", "진행중")
    # P6: 상태 빈칸 품목(새로 넣은 것) = 출하 전 · 납기가 더 가까움
    P6 = proj("006T2605", "출하"); o = order(P6, "T-6"); item(o, "n1", None, due="2026-05-20")
    # 소모품 2건(수주·출하·계산서 모두 5월)
    for no in ("C-1", "C-2"):
        ins(c, "consumable_orders", {"co_no": no, "mgmt_code": "00%sC2605" % no[-1], "customer_name": "엘지전자", "customer_id": CU, "currency": "KRW",
                                     "total_amount": 500000, "status": "SHIPPED", "biz_div": "T", "order_date": "2026-05-02", "due_date": "2026-05-10",
                                     "status_date": "2026-05-10", "tax_invoice_date": "2026-05-20", "tax_invoice_amt1": 500000})

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


# 세금계산서: T-1 의 두 품목(1호기 · 부품A) 각각 1차 발행 + M-1 1차 — 같은 수주의 두 줄은 1건
OI = {ITEMS["a1"]: {"t1d": "2026-05-20", "t1a": 1000000}, ITEMS["a2"]: {"t1d": "2026-05-21", "t1a": 1000000},
      ITEMS["m1"]: {"t1d": "2026-05-22", "t1a": 1000000}}

with D.db_session() as c:
    rates = M._fx_load_rates(c)
    S = q(M._sales_3way, c, rates, OI, "month", "2026", "2", "5")
    K = S["kpi"]
    R = {b: q(M._sales_report_z17, c, rates, OI, b, "month", "2026", "2", "5") for b in ("order", "ship", "tax")}
    OP = M._z40_open_projects(c)

print("§1 카드 건수 = 수주번호 수 + 소모품 발주 수")
check((K["order_so"], K["order_co"]) == (5, 2), "수주매출: 수주 5건(T-1·T-2·M-1·T-3·T-6 · 취소 T-4·폐기 T-5 뺌) · 소모품 2건", (K.get("order_so"), K.get("order_co")))
check(K["order_cnt"] == 10, "(예전 숫자 = 줄 수 10(품목 8 + 소모품 2) — 이게 「4939건」 같은 숫자였음)", K["order_cnt"])
check((K["prog_so"], K["prog_co"]) == (3, 2), "진행매출: 출하 품목이 있는 수주 3건(T-1·T-2·M-1) · 소모품 2건", (K.get("prog_so"), K.get("prog_co")))
check((K["final_so"], K["final_co"]) == (2, 2), "최종매출: 계산서 발행 수주 2건(T-1 두 줄 = 1건 · M-1) · 소모품 2건", (K.get("final_so"), K.get("final_co")))
for b, (so, co) in (("order", ("order_so", "order_co")), ("ship", ("prog_so", "prog_co")), ("tax", ("final_so", "final_co"))):
    check(R[b]["so_n"] == K[so] + K[co], "매출 보고서 「건수」(%s 기준)와 같은 값" % b, (R[b]["so_n"], K[so], K[co]))

print("§2 진행 프로젝트 = 출하 전 품목이 남은 프로젝트")
codes = [d["code"] for d in OP["projects"]]
check(codes == ["006T2605", "001T2605"], "P1(상태 「출하」인데 덜 나감) · P6(빈칸 품목) — 가까운 납기 순 · P2(다 나감)·P3(보류만)·P4(취소)·P5(폐기) 뺌", codes)
check(OP["n"] == 2 and OP["units"] == 2, "개수 2 · 출하 전 품목 2", (OP["n"], OP["units"]))
p1 = next((d for d in OP["projects"] if d["code"] == "001T2605"), {})
check((p1.get("n_open"), p1.get("n_all"), p1.get("so_list"), p1.get("due")) == (1, 5, ["T-1"], "2026-05-30"),
      "P1: 출하 전 1 / 전체 5 · 출하 전 품목의 수주번호만(T-1) · 가까운 납기 = 출하 전 품목 납기", p1)
check(p1.get("biz_label", "").startswith("🔬"), "사업부 표시 = 등록 화면 아이콘", p1.get("biz_label"))
with D.db_session() as c:
    old = c.execute("SELECT COUNT(*) FROM projects WHERE status='진행중'").fetchone()[0]
check(old == 3, "(예전 기준 = 상태 칸 「진행중」 3 — 보류·취소·폐기까지 셌음)", old)

print("§3 ⓘ 설명 기간")
check(S["period_range"] == "2026-05-01 ~ 2026-05-31", "월간 5월", S["period_range"])
check(M._z40_period_range("year", "2026", "1", "1") == "2026-01-01 ~ 2026-12-31", "연간")
check(M._z40_period_range("quarter", "2026", "4", "1") == "2026-10-01 ~ 2026-12-31", "4분기")
check(M._z40_period_range("month", "2028", "1", "2") == "2028-02-01 ~ 2028-02-29", "윤년 2월")

print("§4 화면")
r = q(cl.get, "/sales?mode=month&year=2026&m=5")
h = r.text
check(r.status_code == 200, "매출 홈 열림", r.status_code)
check(len(re.findall(r'class="z40-i" data-z40="(order|prog|final|open)"', h)) == 4, "ⓘ 단추 4개(수주·진행·최종·진행 프로젝트)")
check(all(('id="z40t-%s"' % k) in h for k in ("order", "prog", "final", "open")) and h.count("2026-05-01 ~ 2026-05-31") >= 3,
      "설명 글 4개 · 고른 기간이 들어감")
_ct = [re.sub(r"\s+", " ", x).strip() for x in re.findall(r'<span class="z40-cnt">(.*?)</span>', h, re.S)]
check(_ct[:4] == ["수주 5건 · 소모품 2건", "수주 3건 · 소모품 2건", "소모품 2건", "출하 전 품목 2개"], "카드 건수 글(세 지표 · 화면은 DB 계산서만 봄 → 호기 계산서 없음 = 소모품만 · 0인 쪽은 안 씀)", _ct)
check(not re.search(r"발주일 기준 · \d+건", h), "예전 「발주일 기준 · N건」(줄 수) 없음")
check('id="z40OpenCard"' in h and re.search(r'<div class="kpi-num">2<span class="z40-more">', h), "진행 프로젝트 카드 숫자 = 2(누르는 카드)")
check('id="z40Modal"' in h and "진행 중인 프로젝트 2개 · 출하 전 품목 2개" in h, "목록 창 제목")
mb = h[h.find('id="z40Modal"'):]
mb = mb[:mb.find('</table>')]
check(mb.find("006T2605") < mb.find("001T2605") and ('href="/project/%d"' % P6) in mb and ('href="/project/%d"' % P1) in mb,
      "목록: 가까운 납기 순 · 관리번호 누르면 그 프로젝트")
check("002M2605" not in mb and "003T2605" not in mb and "004T2605" not in mb and "005T2605" not in mb, "목록에 진행 아닌 프로젝트 없음")
check("z40-late" in mb, "납기 지난 품목은 빨갛게 ⚠(시험 날짜 2026-05 < 오늘)")

print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
