# -*- coding: utf-8 -*-
"""z1191z95 시험 — 고객사 결제 조건 고르기 6가지 + 기본 「세금계산서 발행 후 60일」 (대표 11-21)
  §1 규칙 함수: 현금(당일) · 15일 · 당월 말 · 익월 말(12월→1월 해 넘김) · 익익월 말 · 직접입력 N일 · 안 고름=60일 · 옛 일수만=직접입력
  §2 고객사 수정 화면: 고르기 7칸(기본+6) · 지금 값 선택 · 저장하면 종류·일수 저장 · 이력 「결제 조건」 · 직접입력 빈칸=기본
  §3 고객사 새로 등록: 고른 조건 저장
  §4 같은 규칙을 쓰는 화면: 💰 입금 확인 예정일 · 고객사 줄 조건 글자 · 기본 고객사 [⚙ 결제 조건 정하기] · 🚚 납품·수금 입금예상일 · 미수금 만기
"""
import contextlib
import io
import os
import sys
import tempfile
from datetime import date, timedelta

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z95-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z95_")
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
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, "
                 "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상대표', 'ceo', 'Z951', 'Z951', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    CEO = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z951'").fetchone())
    conn.execute("INSERT INTO customers (name, biz_no, ceo_name, address, pay_days) VALUES ('조건고객', '123-45-67890', '홍길동', '서울', 0)")
    conn.execute("INSERT INTO customers (name, biz_no, ceo_name, address, pay_days) VALUES ('옛일수고객', '123-45-67891', '홍길동', '서울', 45)")
    C1 = conn.execute("SELECT id FROM customers WHERE name='조건고객'").fetchone()[0]
    C2 = conn.execute("SELECT id FROM customers WHERE name='옛일수고객'").fetchone()[0]

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M.get_user = lambda request: CEO
cl = TestClient(M.app)
OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


print("§1 규칙 함수")
f = M._pay_due_z95
d0 = date(2026, 11, 21)
check("현금 = 발행일 당일", f(d0, "cash", 0) == d0)
check("15일 = 12-06", f(d0, "d15", 0) == date(2026, 12, 6))
check("당월 말 = 11-30", f(d0, "eom", 0) == date(2026, 11, 30))
check("익월 말 = 12-31", f(d0, "eom1", 0) == date(2026, 12, 31))
check("익익월 말 = 다음 해 01-31(해 넘김)", f(d0, "eom2", 0) == date(2027, 1, 31))
check("12월 발행 익월 말 = 다음 해 01-31 · 1월 발행 익월 말 = 02-28", f(date(2026, 12, 3), "eom1", 0) == date(2027, 1, 31) and f(date(2027, 1, 30), "eom1", 0) == date(2027, 2, 28))
check("직접입력 45일", f(d0, "days", 45) == d0 + timedelta(days=45))
check("안 고름 = 기본 60일", f(d0, "", 0) == d0 + timedelta(days=60) and f(d0, None, None) == d0 + timedelta(days=60))
check("옛 입력(종류 없이 일수만 30) = 직접입력 30일", f(d0, "", 30) == d0 + timedelta(days=30))
check("직접입력인데 일수 0 · 모르는 종류 = 기본 60일", f(d0, "days", 0) == d0 + timedelta(days=60) and f(d0, "xyz", 0) == d0 + timedelta(days=60))
lb = M._pay_term_label_z95
check("글자: 기본 · 익월 말 · 직접 45일 · 옛 30일",
      [lb("", 0), lb("eom1", 0), lb("days", 45), lb("", 30)] ==
      ["기본 · 세금계산서 발행 후 60일", "세금계산서 발행 후 익월 말", "세금계산서 발행 후 45일", "세금계산서 발행 후 30일"],
      [lb("", 0), lb("eom1", 0), lb("days", 45), lb("", 30)])

print("§2 고객사 수정")
h = q(cl.get, "/customers/%d/edit" % C1).text
opts = ["기본 · 세금계산서 발행 후 60일", "1. 현금", "2. 세금계산서 발행 후 15일", "3. 세금계산서 발행 후 당월 말",
        "4. 세금계산서 발행 후 익월 말", "5. 세금계산서 발행 후 익익월 말", "6. 직접입력"]
check("고르기 7칸(기본 + 대표님 6가지 · 번호 그대로)", all(o in h for o in opts) and 'name="pay_term"' in h, [o for o in opts if o not in h])
check("안 고른 고객사 = 「기본」이 선택됨", '<option value="" selected>기본 · 세금계산서 발행 후 60일</option>' in h)
h2 = q(cl.get, "/customers/%d/edit" % C2).text
check("옛 일수(45)만 있는 고객사 = 「6. 직접입력」 선택 · 45 보임", 'value="days" selected' in h2 and 'value="45"' in h2)
BASEF = {"name": "조건고객", "biz_no": "123-45-67890", "ceo_name": "홍길동", "address": "서울", "is_active": "1"}
r = q(cl.post, "/customers/%d/edit" % C1, data=dict(BASEF, pay_term="eom1", pay_days=""), follow_redirects=False)
with D.db_session() as c:
    row = c.execute("SELECT pay_term, pay_days FROM customers WHERE id=?", (C1,)).fetchone()
    hist = c.execute("SELECT old_value, new_value FROM customer_history WHERE customer_id=? AND field='결제 조건'", (C1,)).fetchall()
check("익월 말 저장 = (eom1, 0)", r.status_code in (302, 303) and tuple(row) == ("eom1", 0), (r.status_code, tuple(row) if row else None))
check("이력 「결제 조건: 기본 · 60일 → 익월 말」", [tuple(x) for x in hist] == [("기본 · 세금계산서 발행 후 60일", "세금계산서 발행 후 익월 말")], [tuple(x) for x in hist])
q(cl.post, "/customers/%d/edit" % C1, data=dict(BASEF, pay_term="days", pay_days="45"), follow_redirects=False)
with D.db_session() as c:
    row = c.execute("SELECT pay_term, pay_days FROM customers WHERE id=?", (C1,)).fetchone()
check("직접입력 45 저장 = (days, 45)", tuple(row) == ("days", 45), tuple(row))
q(cl.post, "/customers/%d/edit" % C1, data=dict(BASEF, pay_term="days", pay_days=""), follow_redirects=False)
with D.db_session() as c:
    row = c.execute("SELECT pay_term, pay_days FROM customers WHERE id=?", (C1,)).fetchone()
check("직접입력인데 빈칸 = 기본으로(('', 0))", tuple(row) == ("", 0), tuple(row))
q(cl.post, "/customers/%d/edit" % C1, data=dict(BASEF, pay_term="", pay_days=""), follow_redirects=False)
with D.db_session() as c:
    n = c.execute("SELECT COUNT(*) FROM customer_history WHERE customer_id=? AND field='결제 조건'", (C1,)).fetchone()[0]
check("같은 조건(기본→기본)이면 이력 안 늘어남(3줄 그대로)", n == 3, n)

print("§3 고객사 새로 등록")
r = q(cl.post, "/customers/new", data={"name": "새조건고객", "biz_no": "123-45-67899", "ceo_name": "홍길동", "address": "서울",
                                       "is_active": "1", "pay_term": "d15", "pay_days": ""}, follow_redirects=False)
with D.db_session() as c:
    row = c.execute("SELECT pay_term, pay_days FROM customers WHERE name='새조건고객'").fetchone()
check("새 고객사 15일 저장 = (d15, 0)", row is not None and tuple(row) == ("d15", 0), (r.status_code, tuple(row) if row else None))
hn = q(cl.get, "/customers/new").text
check("새 등록 화면도 고르기 7칸 · 기본 선택", '<option value="" selected>기본 · 세금계산서 발행 후 60일</option>' in hn and "5. 세금계산서 발행 후 익익월 말" in hn)

print("§4 같은 규칙을 쓰는 화면")
with D.db_session() as c:
    c.execute("UPDATE customers SET pay_term='eom', pay_days=0 WHERE id=?", (C1,))
    c.execute("INSERT INTO orders (order_no, customer_id, status, currency, total_amount, order_date) VALUES ('SO-Z95-1', ?, 'SHIPPED', 'KRW', 1000000, '2026-10-01')", (C1,))
    c.execute("INSERT INTO orders (order_no, customer_id, status, currency, total_amount, order_date) VALUES ('SO-Z95-2', ?, 'SHIPPED', 'KRW', 1000000, '2026-10-01')", (C2,))
    o1 = c.execute("SELECT id FROM orders WHERE order_no='SO-Z95-1'").fetchone()[0]
    o2 = c.execute("SELECT id FROM orders WHERE order_no='SO-Z95-2'").fetchone()[0]
    c.execute("UPDATE customers SET pay_days=0, pay_term='' WHERE id=?", (C2,))
    # 납품·수금 화면은 프로젝트에 붙은 수주의 호기 줄에서 계산서 날짜를 읽음 → 시험 수주에도 프로젝트를 붙임
    for _n, _oid in (("Z95-P1", o1), ("Z95-P2", o2)):
        c.execute("INSERT INTO projects (name, mgmt_code, status) VALUES (?, ?, '출하')", (_n, _n))
        c.execute("UPDATE orders SET project_id=(SELECT id FROM projects WHERE name=?) WHERE id=?", (_n, _oid))
    for oid in (o1, o2):
        c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_status, tax_invoice_date, tax_invoice_amt1) "
                  "VALUES (?, 1, 1000000, 1000000, '출하', '2026-10-10', 1000000)", (oid,))
d = M._rc_rows_z94(CEO)
by = {x["oid"]: x for x in d["rows"]}
check("입금 확인: 당월 말 고객 = 10-31 예정 · 조건 글자 「세금계산서 발행 후 당월 말」",
      by.get(o1, {}).get("due") == "2026-10-31" and by[o1]["term_label"] == "세금계산서 발행 후 당월 말" and not by[o1]["term_default"], by.get(o1))
check("입금 확인: 기본 고객 = 10-10 + 60일 = 12-09 · 기본 표시", by.get(o2, {}).get("due") == "2026-12-09" and by[o2]["term_default"], by.get(o2))
check("「미설정」 묶음 없음(모두 예정일 있음)", not [x for x in d["rows"] if x["bucket"] == "noterms"])
hr = q(cl.get, "/sales/receipts-check").text
check("화면: 기본 고객 옆 [⚙ 결제 조건 정하기] · 기본 적용 안내 1곳 · KPI 3칸",
      "⚙ 결제 조건 정하기" in hr and ('href="/customers/%d/edit"' % C2) in hr and "결제 조건을 아직 안 고른 고객사 <b>1곳</b>" in hr
      and hr.count('class="rc-kpi ') == 3, hr.count('class="rc-kpi '))
hs = q(cl.get, "/sales/shipments-receipts?ym=2026-10").text
check("납품·수금: 입금예상일 10-31 · 12-09(같은 규칙) · 「결제조건 미설정」 글자 없음",
      "2026-10-31" in hs and "2026-12-09" in hs and "결제조건 미설정" not in hs, ("2026-10-31" in hs, "2026-12-09" in hs, "결제조건 미설정" in hs))
with D.db_session() as c:
    items = M._outstanding_receivables(c)
bo = {x["order_id"]: x for x in items}
check("미수금 만기: 당월 말 = 10-31 · 기본 = 12-09", bo.get(o1, {}).get("due_date_calc") == "2026-10-31" and bo.get(o2, {}).get("due_date_calc") == "2026-12-09",
      (bo.get(o1, {}).get("due_date_calc"), bo.get(o2, {}).get("due_date_calc")))

print("\n결과: OK %d · FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
