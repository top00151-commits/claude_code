# -*- coding: utf-8 -*-
"""z1191z100 시험 — 수금 알림 켜기: 평일 09:00 · 받는 사람 설정(기본 안지연 프로 = 사번 67) (대표 11-22)
  §1 받는 사람 기본값  §2 묶음 알림 1건(웍스 + 이음)  §3 평일·공휴일 시각  §4 하루 한 번  §5 화면 줄·바꾸기 권한·저장"""
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z100-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z100_")
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
    conn.execute(ins, ("가상안지연", "admin", "67", "Z984", 1))
    SALES = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z981'").fetchone())
    VIEWER = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z982'").fetchone())
    CEO = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z983'").fetchone())
    AN = dict(conn.execute("SELECT * FROM users WHERE employee_no='67'").fetchone())
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


import app.sso_client as SSO
SENT = []
SSO.notify_via_messenger = lambda emps, title, body, link="", timeout=10.0, card=None: (SENT.append((list(emps), title, link)) or {"ok": True, "sent": len(emps)})
T = date.today()
O1 = reg("알림1", "가상고객A")   # 30일 조건 · 발행 80일 전 → 50일 지남(300,000 받음 → 800,000)
O3 = reg("알림3", "가상고객B")   # 기본 60일 · 발행 200일 전 → 140일 지남
O5 = reg("알림5", "가상고객A")   # 발행 23일 전 + 30일 → 7일 전
O6 = reg("알림6", "가상고객A")   # 발행 31일 전 + 30일 → 1일 지남
for o, dd in ((O1, 80), (O3, 200), (O5, 23), (O6, 31)):
    tax(o, (T - timedelta(days=dd)).isoformat(), 1000000)
with D.db_session() as c:
    c.execute("INSERT INTO receipts_payment (order_id, received_at, amount, method, currency) VALUES (?, ?, 300000, '이체', 'KRW')", (O1, T.isoformat()))

print("§1 받는 사람 기본값")
with D.db_session() as c:
    check("설정 없으면 = 안지연 프로(사번 67) 한 분", M._ar_alert_recipient_ids_z100(c) == [AN["id"]], M._ar_alert_recipient_ids_z100(c))

print("§2 묶음 알림")
with D.db_session() as c:
    c.execute("DELETE FROM notifications")
r = M.check_receivable_alerts()
with D.db_session() as c:
    ns = [dict(x) for x in c.execute("SELECT user_id, title, body, link FROM notifications ORDER BY id")]
check("알림 1건(계산서마다 따로가 아니라 묶음) · 안지연 프로만", len(ns) == 1 and ns[0]["user_id"] == AN["id"] and r["sent"] == 1 and r["new"] == 2, (r, ns))
n0 = ns[0] if ns else {}
check("제목 「💰 수금 확인 MM-DD — 새로 챙길 계산서 2장」", n0.get("title") == "💰 수금 확인 %s — 새로 챙길 계산서 2장" % T.strftime("%m-%d"), n0.get("title"))
b = n0.get("body") or ""
check("본문: 1일 지남 1장 · 7일 전 1장 · 전체 지난 돈 ₩3,000,000(2곳) · 입금 확인 안내 · 링크",
      "🔴 예정일 1일 지남(새로 지남) 1장" in b and "🟠 예정일 7일 전 1장" in b and "전체 예정일 지난 돈: ₩3,000,000 (2곳)" in b
      and "입금 확인됨" in b and n0.get("link") == "/sales/receipts-check", b)
check("이음 「WORKS 알림」으로도 = 사번 67 · 링크 전체 주소", SENT and SENT[0][0] == ["67"] and SENT[0][2].endswith("/sales/receipts-check"), SENT)
r2 = M.check_receivable_alerts()
check("한 시간 안에 다시 돌려도 웍스·이음 둘 다 안 겹침", r2["sent"] == 0 and len(SENT) == 1, (r2, len(SENT)))

print("§3 평일 09:00 · 공휴일")
from datetime import datetime as DT
f = M._ar_alert_seconds_until_next_z100
check("금 10:00 → 월 09:00", f(DT(2026, 11, 27, 10, 0)) == (DT(2026, 11, 30, 9, 0) - DT(2026, 11, 27, 10, 0)).total_seconds())
check("토 08:00 → 월 09:00", f(DT(2026, 11, 28, 8, 0)) == (DT(2026, 11, 30, 9, 0) - DT(2026, 11, 28, 8, 0)).total_seconds())
check("평일 08:00 → 그날 09:00(1시간)", f(DT(2026, 11, 24, 8, 0)) == 3600)
check("공휴일(12-25 성탄절 금) 08:00 → 12-28 월 09:00", "2026-12-25" in M.HOLIDAYS_KR and f(DT(2026, 12, 25, 8, 0)) == (DT(2026, 12, 28, 9, 0) - DT(2026, 12, 25, 8, 0)).total_seconds())
dn = M._ar_alert_due_now_z100
check("보낼 때: 평일 09:30 예 · 08:59 아니오 · 18:00 아니오 · 토요일 아니오 · 공휴일 아니오",
      dn(DT(2026, 11, 24, 9, 30)) and not dn(DT(2026, 11, 24, 8, 59)) and not dn(DT(2026, 11, 24, 18, 0))
      and not dn(DT(2026, 11, 28, 10, 0)) and not dn(DT(2026, 12, 25, 10, 0)))

from datetime import date as DD
check("맡을 날 수: 화 1 · 월 3(금·토·일) · 성탄절(금) 다음 월 12-28 = 4(금 휴일·토·일·월)",
      M._ar_alert_span_z100(DD(2026, 11, 24)) == 1 and M._ar_alert_span_z100(DD(2026, 11, 23)) == 3
      and M._ar_alert_span_z100(DD(2026, 12, 28)) == 4)
fake = [{"dday": d, "cname": "가", "order_no": "SO%d" % d, "rem_fmt": "₩1", "due": "x", "ccy": "KRW", "rem": 1, "cid": 1}
        for d in (-4, -3, -2, -1, 0, 4, 5, 6, 7, 8, -29, -30, -32, -33)]
n1, t1, b1, _ = M._ar_alert_digest_z100(fake, 1)
n3, t3, b3, _ = M._ar_alert_digest_z100(fake, 3)
check("하루 치(span 1): -1 · 7 · -30 만 = 3장", n1 == 3, (n1, b1))
check("월요일(span 3): -3~-1 · 5~7 · -32~-30(-31 없음) = 8장 · 「주말·휴일 포함 3일 치」",
      n3 == 8 and "주말·휴일 포함 3일 치" in b3 and "SO-4" not in b3 and "SO4 " not in b3 and "SO8" not in b3 and "SO-33" not in b3, (n3, b3))

print("§4 하루 한 번")
check("같은 날 두 번 잡으면 두 번째는 못 잡음 · 다음 날은 잡음",
      M._ar_alert_claim_z100("2026-11-24") and not M._ar_alert_claim_z100("2026-11-24") and M._ar_alert_claim_z100("2026-11-25"))

print("§5 화면 · 바꾸기")
h = main_part(q(cl.get, "/sales/receipts-check").text)
check("영업 담당(일반): 🔔 수금 알림 줄 · 받는 사람 = 가상안지연 · 바꾸기 단추 없음",
      'id="rcAlertBar"' in h and "가상안지연" in h[h.find('id="rcAlertBar"'):h.find('id="rcAlertBar"') + 900] and "rcAlertOpen()" not in h)
S["user"] = CEO
hc = main_part(q(cl.get, "/sales/receipts-check").text)
check("대표: 「⚙ 받는 사람 바꾸기」 · 고를 사람 목록(안지연 체크됨) · 이음 3명 제한 안내",
      "⚙ 받는 사람 바꾸기" in hc and ('value="%d" checked' % AN["id"]) in hc and "김정락 · 안지연 · 이새롬" in hc)
r = q(cl.post, "/sales/ar-alert/recipients", json={"user_ids": [AN["id"], SALES["id"]]})
check("대표가 저장(안지연 + 가상영업)", r.status_code == 200 and r.json().get("ok") and r.json().get("ids") == [AN["id"], SALES["id"]], r.text[:200])
r = q(cl.post, "/sales/ar-alert/recipients", json={"user_ids": [999999]})
check("없는 계정이면 저장 안 함(400)", r.status_code == 400, r.status_code)
S["user"] = SALES
r = q(cl.post, "/sales/ar-alert/recipients", json={"user_ids": [SALES["id"]]})
check("일반 영업 담당은 못 바꿈(403)", r.status_code == 403, r.status_code)
S["user"] = AN
r = q(cl.post, "/sales/ar-alert/recipients", json={"user_ids": [AN["id"]]})
check("안지연 프로(관리자 · 매출 등록)는 바꿀 수 있음", r.status_code == 200 and r.json().get("ids") == [AN["id"]], r.text[:200])
with D.db_session() as c:
    a = c.execute("SELECT COUNT(*) FROM doc_audit_log WHERE doc_type='ar_alert_recipients'").fetchone()[0]
check("바꾼 기록 남음(2건)", a == 2, a)
S["user"] = CEO
q(cl.post, "/sales/ar-alert/recipients", json={"user_ids": []})
with D.db_session() as c:
    c.execute("DELETE FROM notifications")
r = M.check_receivable_alerts()
check("받는 사람을 모두 빼면 알림 안 감", r["recipients"] == 0 and r["sent"] == 0, r)
S["user"] = SALES

print("\n결과: OK %d · FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
