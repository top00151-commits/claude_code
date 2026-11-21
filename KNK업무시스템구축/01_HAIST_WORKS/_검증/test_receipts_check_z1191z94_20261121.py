# -*- coding: utf-8 -*-
"""z1191z94 시험 — 💰 입금 확인(세금계산서 기준 받을 돈) (대표 11-21 「다음 입금 확인 화면 진행해」)
  §1 나누기: 예정일 = 발행일 + 고객사 결제 조건 · 지남 / 7일 안 / 그 뒤(z95: 안 고른 고객사 = 기본 60일 · 결제 조건 정하기 링크)
  §2 금액: 부가세 포함(국내 원화 10% · 수출 0%) · 마이너스(수정) 계산서는 받을 돈에서 뺌
  §3 [✅ 입금 확인됨]: 일부 입금 → 남은 금액 줄어듦 · 다 차면 수주 = 입금 완료(PAID) + 상태 이력 · 줄 사라짐
  §4 막기: 매출 등록 권한 없으면 화면·기록 다 막힘 · 금액 0·입금일 없음 = 거절
  §5 메뉴·띠: 「💰 입금 확인」 메뉴 · 정리 끝(ar_baseline_done=1)이면 미수 화면에 입금 확인 안내 · 👤 내 건만
"""
import contextlib
import io
import os
import re
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z94-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z94_")
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
    if not conn.execute("SELECT 1 FROM teams WHERE id=1").fetchone():
        tcols = {r[1] for r in conn.execute("PRAGMA table_info(teams)")}
        if "code" in tcols:
            conn.execute("INSERT INTO teams (id, code, name) VALUES (1, '01', '기술영업팀')")
        else:
            conn.execute("INSERT INTO teams (id, name) VALUES (1, '기술영업팀')")
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, "
                 "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상영업', 'member', 'Z941', 'Z941', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 0, 0)")
    SALES = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z941'").fetchone())
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, "
                 "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상설계', 'member', 'Z942', 'Z942', 'sso_only_no_local_password', 1, 1, 1, 1, 0, 0, 0)")
    VIEWER = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z942'").fetchone())
    conn.execute("INSERT INTO customers (name, pay_days) VALUES ('가상고객A', 30)")
    conn.execute("INSERT INTO customers (name, pay_days) VALUES ('가상고객B', 0)")
    CA = conn.execute("SELECT id FROM customers WHERE name='가상고객A'").fetchone()[0]
    CB = conn.execute("SELECT id FROM customers WHERE name='가상고객B'").fetchone()[0]
    conn.execute("INSERT OR IGNORE INTO field_access_policy (category, team_id) VALUES ('sales_amount', 1)")

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

S = {"user": SALES}
M.get_user = lambda request: S["user"]
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


BASE = {"quick": "1", "biz_div": "T", "project_type": "NEW_EQUIP", "po_type": "신규", "status": "진행중",
        "confirm_now": "1", "order_date": "2026-07-01", "due_date": "2026-08-01", "currency": "KRW",
        "equip_name": "가상장비", "unit_qty": "1", "model": "가상모델", "prod_mode": "none",
        "unit_price": "1000000", "order_amount": "1000000"}


def reg(name, cust, sales="가상영업"):
    f = dict(BASE, project_name=name, customer_name=cust, sales=sales)
    r = q(cl.post, "/projects/new", data=f, follow_redirects=False)
    assert r.status_code == 303 and r.headers.get("location", "").startswith("/project/"), r.headers.get("location")
    with D.db_session() as c:
        pid = c.execute("SELECT id FROM projects WHERE name=?", (name,)).fetchone()[0]
        oid = c.execute("SELECT id FROM orders WHERE project_id=?", (pid,)).fetchone()[0]
        c.execute("UPDATE orders SET customer_id=?, status='SHIPPED', total_amount=1000000 WHERE id=?",
                  (CA if cust == "가상고객A" else CB, oid))
    return oid


def tax(oid, n, d, amt, export=0):
    col_d = "tax_invoice_date" if n == 1 else "tax_invoice_date%d" % n
    with D.db_session() as c:
        r0 = c.execute("SELECT id FROM order_items WHERE order_id=? ORDER BY id LIMIT 1", (oid,)).fetchone()
        if not r0:   # 이 시험 등록 길에서는 호기 줄이 바로 안 생김 → 한 줄 만들어 둠(운영은 호기 줄에 계산서 날짜)
            c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount) VALUES (?, 1, 1000000, 1000000)", (oid,))
            r0 = c.execute("SELECT id FROM order_items WHERE order_id=? ORDER BY id LIMIT 1", (oid,)).fetchone()
        iid = r0[0]
        c.execute("UPDATE order_items SET %s=?, tax_invoice_amt%d=?, is_export=? WHERE id=?" % (col_d, n), (d, amt, export, iid))


T = date.today()
O1 = reg("입금시험1", "가상고객A")              # 발행 40일 전 + 30일 = 10일 지남
O2 = reg("입금시험2", "가상고객A", "다른사람")   # 발행 25일 전 + 30일 = D-5
O3 = reg("입금시험3", "가상고객B")              # 결제 조건 없음
O4 = reg("입금시험4", "가상고객A", "다른사람")   # 수출 = 부가세 0
tax(O1, 1, (T - timedelta(days=40)).isoformat(), 1000000)
tax(O2, 1, (T - timedelta(days=25)).isoformat(), 1000000)
tax(O2, 2, (T - timedelta(days=24)).isoformat(), -100000)
tax(O3, 1, (T - timedelta(days=5)).isoformat(), 1000000)
tax(O4, 1, (T - timedelta(days=50)).isoformat(), 1000000, export=1)

print("§1·§2 나누기 · 금액")
d = M._rc_rows_z94(SALES)
by = {x["oid"]: x for x in d["rows"]}
check("O1 = 예정일 지남 · 10일 지남 · 1,100,000(부가세 포함)", by.get(O1, {}).get("bucket") == "overdue" and by[O1]["dday"] == -10 and by[O1]["rem"] == 1100000, by.get(O1))
check("O2 = 7일 안(D-5) · 마이너스 계산서 뺌 = 1,100,000 − 110,000 = 990,000", by.get(O2, {}).get("bucket") == "week" and by[O2]["dday"] == 5 and by[O2]["rem"] == 990000, by.get(O2))
# z1191z95 (대표 11-21): 결제 조건 안 고른 고객사 = 기본 「세금계산서 발행 후 60일」 → 「미설정」 묶음 없음
check("O3 = 결제 조건 안 고름 → 기본 60일(발행 5일 전 → D-55 · 그 뒤) · 발행 후 5일", by.get(O3, {}).get("bucket") == "later" and by[O3]["dday"] == 55 and by[O3]["term_default"] and by[O3]["age"] == 5, by.get(O3))
check("O4 = 수출이라 부가세 0 → 1,000,000 · 20일 지남", by.get(O4, {}).get("rem") == 1000000 and by[O4]["bucket"] == "overdue", by.get(O4))
h = q(cl.get, "/sales/receipts-check").text
check("화면 200 · 고객사 묶음 · 기본 고객사(B)에 ⚙ 결제 조건 정하기 링크", "가상고객A" in h and ('href="/customers/%d/edit"' % CB) in h and "⚙ 결제 조건 정하기" in h)
check("고객사 줄 조건 글자: A = 옛 일수 30 → 「세금계산서 발행 후 30일」 · B = 「기본 · 세금계산서 발행 후 60일」", "세금계산서 발행 후 30일" in h and "기본 · 세금계산서 발행 후 60일" in h)
check("KPI: 예정일 지남 1곳 · 2장", re.search(r'🔴 예정일 지남</div>\s*<div class="v">1곳 · 2장', h) is not None)
check("관리팀 확인 요청 글 복사 단추", "📋 관리팀 확인 요청 글 복사" in h)

print("§3 [✅ 입금 확인됨]")
r = q(cl.post, "/sales/receipts-check/record", json={"order_id": O1, "received_at": T.isoformat(), "amount": "500,000", "note": "관리팀 확인"})
j = r.json()
check("일부 입금 500,000 → 저장 · 아직 출하 상태", r.status_code == 200 and j.get("ok") and j.get("status") == "SHIPPED", j)
by = {x["oid"]: x for x in M._rc_rows_z94(SALES)["rows"]}
check("남은 금액 600,000", by.get(O1, {}).get("rem") == 600000, by.get(O1))
r = q(cl.post, "/sales/receipts-check/record", json={"order_id": O1, "received_at": T.isoformat(), "amount": 600000})
j = r.json()
check("나머지 600,000 → 입금 완료(PAID)", j.get("ok") and j.get("status") == "PAID", j)
with D.db_session() as c:
    st = c.execute("SELECT status FROM orders WHERE id=?", (O1,)).fetchone()[0]
    hs = c.execute("SELECT COUNT(*) FROM order_status_history WHERE order_id=? AND to_status='PAID'", (O1,)).fetchone()[0]
    rp = c.execute("SELECT COUNT(*), SUM(amount), MAX(method), MAX(received_by) FROM receipts_payment WHERE order_id=?", (O1,)).fetchone()
check("수주 상태 PAID · 상태 이력 1줄 · 입금 2줄(방법 「입금 확인」 · 입력자 = 나)",
      st == "PAID" and hs == 1 and rp[0] == 2 and rp[1] == 1100000 and rp[2] == "입금 확인" and rp[3] == SALES["id"], (st, hs, tuple(rp)))
check("다 받은 O1 은 목록에서 사라짐", O1 not in {x["oid"] for x in M._rc_rows_z94(SALES)["rows"]})
r = q(cl.post, "/sales/receipts-check/record", json={"order_id": O2, "received_at": T.isoformat(), "amount": 990000})
check("마이너스 계산서 있는 O2: 990,000 받으면 다 참 — 계산서 합(900,000)이 수주 금액(1,000,000)에 못 미쳐 상태는 그대로",
      r.json().get("ok") and r.json().get("status") == "SHIPPED" and O2 not in {x["oid"] for x in M._rc_rows_z94(SALES)["rows"]}, r.json())

print("§4 막기")
for body, why in (({"order_id": O3, "received_at": T.isoformat(), "amount": 0}, "금액 0"),
                  ({"order_id": O3, "received_at": "", "amount": 1000}, "입금일 없음"),
                  ({"order_id": 999999, "received_at": T.isoformat(), "amount": 1000}, "없는 수주")):
    r = q(cl.post, "/sales/receipts-check/record", json=body)
    check("거절: %s" % why, r.status_code in (400, 404) and not r.json().get("ok"), (r.status_code, r.text[:80]))
S["user"] = VIEWER
r = q(cl.get, "/sales/receipts-check", follow_redirects=False)
check("매출 등록 권한 없으면 화면 → 홈(안내)", r.status_code == 303 and "no_perm=sales" in r.headers.get("location", ""), r.headers.get("location"))
r = q(cl.post, "/sales/receipts-check/record", json={"order_id": O3, "received_at": T.isoformat(), "amount": 1000})
check("매출 등록 권한 없으면 기록 403", r.status_code == 403, r.status_code)
check("메뉴에 「💰 입금 확인」 안 보임(권한 없음)", 'href="/sales/receipts-check"' not in q(cl.get, "/sales").text)
S["user"] = SALES

print("§5 메뉴 · 띠 · 내 건")
hs = q(cl.get, "/sales").text
sb = re.findall(r'<a class="sb-item[^"]*" href="([^"]+)"', hs)
check("메뉴: 납품·수금 → 💰 입금 확인 → 미수금", "/sales/receipts-check" in sb and sb.index("/sales/receipts-check") == sb.index("/sales/outstanding") - 1
      and "💰 입금 확인" in hs, sb)
ho = q(cl.get, "/sales/outstanding").text
check("정리 전: 미수금 화면 경고 띠", "아래 미수 숫자는 아직 실제 미수가 아닙니다" in ho and "ar-after-z94" not in ho)
with D.db_session() as c:
    c.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('ar_baseline_done', '1')")
ho = q(cl.get, "/sales/outstanding").text
check("정리 끝: 경고 대신 「💰 입금 확인」 안내", "ar-after-z94" in ho and 'href="/sales/receipts-check"' in ho and "아래 미수 숫자는" not in ho)
h = q(cl.get, "/sales/receipts-check").text
check("👤 내 건만 단추(내 이름 건 있음)", 'id="rcMineBtn"' in h)
h1 = q(cl.get, "/sales/receipts-check?mine=1").text
check("내 건만 켜면 남의 건 고객사 묶음 지우는 코드", "if (s.getAttribute('data-mine')!=='1') s.remove();" in h1)
g = q(cl.get, "/sales/flow-guide").text
check("안내 6단계 = 입금 확인 화면으로 바로 가기", 'href="/sales/receipts-check"' in g and "입금 확인 — 예정일 된 고객사" in g)

print("\n결과: OK %d · FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
