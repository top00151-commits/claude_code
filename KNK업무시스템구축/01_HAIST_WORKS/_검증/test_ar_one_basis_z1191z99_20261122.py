# -*- coding: utf-8 -*-
"""z1191z99 시험 — 수금 알림 · 매출 분석 · 대표 대시 「미수금 잔액」 = 💰 입금 확인과 같은 계산 (대표 11-22 「1번 수금 알림·매출 분석도 진행해」)
  §1 공용 합계(_ar_totals_z99) = 입금 확인 줄 합  §2 매출 분석 칸·통화별 표  §3 대표 대시 칸  §4 수금 알림(계산서 한 장 · 7일 전·1일 지남만 · 입금 확인으로)
(아래는 z98 시험 바탕)
z1191z98 시험 — 매출·영업 메뉴 14 → 10 (대표 11-22 「5-6 합치는 작업 완료 후 1번도 바로 진행해」 · 한 가지 일은 한 곳에서만)
  §1 메뉴 10줄 순서 · 권한(매출 등록 없는 분은 💰 입금 안 보임)
  §2 한 메뉴 안의 탭 화면 → 그 메뉴에 불
  §3 💰 입금 탭 줄(입금 확인 · 미수 현황 · 입금 대사) · 채권 노화 → 미수 현황으로
  §4 📊 미수 현황 숫자 = 💰 입금 확인과 같은 계산(부가세 포함 · 계산서 기준) · 지난 날수 구간
  §5 🧾 마감 = 계산서 발행 대기만 위에 · 수금 입력 칸 없음 · 입금 숫자 대신 💰 입금 링크
  §6 🎯 수주 전 탭(영업 기회 · 견적서) · 새로 만들기 단추 없음 · 🆕 등록에 🎯 · 📋 카드
  §7 📋 프로젝트 탭 줄에 📑 수주 목록 · 수주 목록 화면에도 같은 탭 줄
  §8 📖 처음이면 안내 글
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z99-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z99_")
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
    ins = ("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, "
           "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
           "VALUES (?, ?, ?, ?, 'sso_only_no_local_password', 1, 1, 1, 1, ?, 0, 0)")
    conn.execute(ins, ("가상영업", "member", "Z981", "Z981", 1))
    conn.execute(ins, ("가상보기", "member", "Z982", "Z982", 0))
    conn.execute(ins, ("가상대표", "ceo", "Z983", "Z983", 1))
    SALES = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z981'").fetchone())
    VIEWER = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z982'").fetchone())
    CEO = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z983'").fetchone())
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


def main_part(h):
    i = h.find('<main')
    return h[i:] if i >= 0 else h


def menu(h):
    """매출·영업 묶음의 메뉴 주소 목록(공통 묶음 앞까지)."""
    a = h.find('<aside class="sidebar"')
    b = h.find('<div style="margin: 14px 14px; border-top', a)
    return re.findall(r'<a class="sb-item[^"]*" href="([^"]+)"', h[a:b])


def active(h):
    m = re.search(r'<a class="sb-item active" href="([^"]+)"', h)
    return m.group(1) if m else None


BASE = {"quick": "1", "biz_div": "T", "project_type": "NEW_EQUIP", "po_type": "신규", "status": "진행중",
        "confirm_now": "1", "order_date": "2026-07-01", "due_date": "2026-08-01", "currency": "KRW",
        "equip_name": "가상장비", "unit_qty": "1", "model": "가상모델", "prod_mode": "none",
        "unit_price": "1000000", "order_amount": "1000000"}


def reg(name, cust, status="SHIPPED"):
    f = dict(BASE, project_name=name, customer_name=cust, sales="가상영업")
    r = q(cl.post, "/projects/new", data=f, follow_redirects=False)
    assert r.status_code == 303, r.status_code
    with D.db_session() as c:
        pid = c.execute("SELECT id FROM projects WHERE name=?", (name,)).fetchone()[0]
        oid = c.execute("SELECT id FROM orders WHERE project_id=?", (pid,)).fetchone()[0]
        c.execute("UPDATE orders SET customer_id=?, status=?, total_amount=1000000 WHERE id=?",
                  (CA if cust == "가상고객A" else CB, status, oid))
        if not c.execute("SELECT 1 FROM order_items WHERE order_id=?", (oid,)).fetchone():
            c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount) VALUES (?, 1, 1000000, 1000000)", (oid,))
        c.execute("UPDATE order_items SET unit_status='출하' WHERE order_id=?", (oid,))
    return oid


def tax(oid, d, amt):
    with D.db_session() as c:
        iid = c.execute("SELECT id FROM order_items WHERE order_id=? ORDER BY id LIMIT 1", (oid,)).fetchone()[0]
        c.execute("UPDATE order_items SET tax_invoice_date=?, tax_invoice_amt1=? WHERE id=?", (d, amt, iid))


T = date.today()
O1 = reg("한기준1", "가상고객A")   # 30일 조건 · 발행 80일 전 → 50일 지남 · 300,000 받음 → 800,000
O2 = reg("한기준2", "가상고객A")   # 발행 10일 전 → 예정일 전
O3 = reg("한기준3", "가상고객B")   # 기본 60일 · 발행 200일 전 → 140일 지남
O5 = reg("한기준5", "가상고객A")   # 발행 23일 전 + 30일 → 예정일 7일 전
O6 = reg("한기준6", "가상고객A")   # 발행 31일 전 + 30일 → 1일 지남
for o, dd in ((O1, 80), (O2, 10), (O3, 200), (O5, 23), (O6, 31)):
    tax(o, (T - timedelta(days=dd)).isoformat(), 1000000)
with D.db_session() as c:
    c.execute("INSERT INTO receipts_payment (order_id, received_at, amount, method, currency) VALUES (?, ?, 300000, '이체', 'KRW')", (O1, T.isoformat()))

print("§1 공용 합계")
rows = M._rc_rows_z94(SALES)["rows"]
tot = M._ar_totals_z99(SALES)
check("받을 돈 = 입금 확인 줄 합 = 800,000 + 1,100,000×4 = 5,200,000 · 지난 돈 = 800,000 + 1,100,000 + 1,100,000 = 3,000,000 · 5장",
      tot.get("KRW") == {"rem": 5200000, "over": 3000000, "n": 5} and sum(x["rem"] for x in rows) == 5200000, tot)

print("§2 매출 분석")
h = q(cl.get, "/sales/dashboard").text
m = main_part(h)
check("「받을 돈(미수)」 칸 5,200,000원 · 예정일 지남 3,000,000원 · 누르면 📊 미수 현황",
      "받을 돈(미수)" in m and "5,200,000" in m and "예정일 지남 3,000,000원" in m and 'href="/sales/outstanding"' in m)
check("통화별 받을 돈 표: KRW · 5장 · ₩5,200,000 · ₩3,000,000 · 옛 「INVOICED+SHIPPED+PAID 수주 − 수금」 없음",
      "통화별 받을 돈" in m and "5장" in m and "₩5,200,000" in m and "₩3,000,000" in m and "INVOICED+SHIPPED+PAID" not in m)
check("옛 「다른 기준」 띠 없음", "ar-after-z94" not in m and "ar-baseline-z92" not in m)

print("§3 대표 대시")
S["user"] = CEO
hd = q(cl.get, "/dashboard").text
check("「미수금 잔액」 = 520만원(입금 확인과 같은 계산) · 설명 「세금계산서 기준 · 부가세 포함」",
      "미수금 잔액" in hd and "520만원" in hd and "세금계산서 기준 · 부가세 포함" in hd and "발행 INVOICE − 수금" not in hd)
S["user"] = SALES

print("§4 수금 알림")
with D.db_session() as c:
    c.execute("DELETE FROM notifications")
r = M.check_receivable_alerts()
with D.db_session() as c:
    ns = [dict(x) for x in c.execute("SELECT user_id, kind, title, body, link FROM notifications ORDER BY id")]
titles = [n["title"] for n in ns]
check("알림 대상 = 계산서 5장 중 2장(7일 전 · 1일 지남) · 다른 날은 안 보냄",
      r["items"] == 5 and len({t for t in titles}) == 2 and all(("한기준5" not in t) for t in titles), (r, titles))
check("7일 전 알림: 「💰 입금 예정일 7일 전 — 가상고객A · …」 · 1일 지남 알림", any(t.startswith("💰 입금 예정일 7일 전 — 가상고객A") for t in titles)
      and any(t.startswith("💰 입금 예정일 1일 지남 — 가상고객A") for t in titles), titles)
b7 = next((n for n in ns if "7일 전" in n["title"]), {})
check("알림 글: 발행일 · 받을 돈 ₩1,100,000(부가세 포함) · 예정일 · 결제 조건 · 링크 = 💰 입금 확인",
      "받을 돈(부가세 포함): ₩1,100,000" in (b7.get("body") or "") and (T + timedelta(days=7)).isoformat() in (b7.get("body") or "")
      and "세금계산서 발행 후 30일" in (b7.get("body") or "") and b7.get("link") == "/sales/receipts-check", b7)
check("받는 사람 = 수주 등록한 분(가상영업)", ns and all(n["user_id"] == SALES["id"] for n in ns), [n["user_id"] for n in ns])
r2 = M.check_receivable_alerts()
check("한 시간 안에 다시 돌려도 같은 알림 안 겹침", r2["sent"] == 0, r2)

print("\n결과: OK %d · FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
