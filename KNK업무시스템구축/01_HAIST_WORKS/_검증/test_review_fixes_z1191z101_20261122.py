# -*- coding: utf-8 -*-
"""z1191z101 시험 — 지난밤 작업 다시 보기에서 찾은 문제 고침 (대표 11-22 「찾은 문제 다 고쳐서 올려」)
  §1 입금 기록 서버 확인(inf·배열 · 남은 돈보다 많음 · 같은 입금 두 번 → 알림 뒤 확인하면 기록)
  §2 입금 완료 판정 = 발행일 있는 계산서만  §3 수금 알림 실패 → 오늘 몫 풀고 다시  §4 권한(수동 보내기 · 받는 사람 고르기)
  §5 운영 DB 에서만 저절로 켜짐"""
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z101-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z101_")
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
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, can_view_sales, can_use_sales) "
                 "VALUES ('가상외부', 'member', 'Z985', 'Z985', 'x', 1, 1, NULL, 0, 0)")
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, can_view_sales, can_use_sales) "
                 "VALUES ('가상임원', 'executive', 'Z986', 'Z986', 'x', 1, 1, NULL, 1, 1)")
    SALES = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z981'").fetchone())
    VIEWER = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z982'").fetchone())
    CEO = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z983'").fetchone())
    AN = dict(conn.execute("SELECT * FROM users WHERE employee_no='67'").fetchone())
    OUT = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z985'").fetchone())
    EXE = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z986'").fetchone())
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
import app.sso_client as SSO
SSO.notify_via_messenger = lambda *a, **k: {"ok": True}
T = date.today()
O1 = reg("고침1", "가상고객A")
tax(O1, (T - timedelta(days=10)).isoformat(), 1000000)    # 받을 돈 1,100,000
post = lambda body: q(cl.post, "/sales/receipts-check/record", json=body)

print("§1 입금 기록 서버 확인")
r = post({"order_id": O1, "received_at": T.isoformat(), "amount": "inf"})
check("금액 inf → 400(저장 안 함)", r.status_code == 400, (r.status_code, r.text[:120]))
r = post({"order_id": O1, "received_at": T.isoformat(), "amount": "nan"})
check("금액 nan → 400", r.status_code == 400, r.status_code)
r = q(cl.post, "/sales/receipts-check/record", json=[1, 2])
check("몸통이 배열 → 500 아닌 400", r.status_code == 400, r.status_code)
r = post({"order_id": O1, "received_at": T.isoformat(), "amount": 2000000})
check("남은 돈(1,100,000)보다 많음 → 409 알림(저장 안 함)", r.status_code == 409 and r.json().get("need_confirm") and "남은 받을 돈" in r.json().get("error", ""), r.text[:200])
with D.db_session() as c:
    n0 = c.execute("SELECT COUNT(*) FROM receipts_payment WHERE order_id=?", (O1,)).fetchone()[0]
check("알림만 하고 기록은 안 됨", n0 == 0, n0)
r = post({"order_id": O1, "received_at": T.isoformat(), "amount": 500000})
check("남은 돈 안쪽이면 바로 기록", r.status_code == 200 and r.json().get("ok"), r.text[:200])
r = post({"order_id": O1, "received_at": T.isoformat(), "amount": 500000})
check("같은 날 같은 금액 다시 → 409 「이미 1건」", r.status_code == 409 and "이미 1건" in r.json().get("error", ""), r.text[:200])
r = post({"order_id": O1, "received_at": T.isoformat(), "amount": 500000, "confirm": True})
check("확인했다고 보내면 기록(막지 않음)", r.status_code == 200 and r.json().get("ok"), r.text[:200])
with D.db_session() as c:
    n2 = c.execute("SELECT COUNT(*) FROM receipts_payment WHERE order_id=?", (O1,)).fetchone()[0]
check("기록 2건", n2 == 2, n2)
h = q(cl.get, "/sales/receipts-check").text
check("화면: 서버 알림을 받으면 같은 입력으로 다시 누를 때 confirm · 「먼저 발행한 계산서부터 채웁니다」 안내",
      "need_confirm" in h and "window.__rcSrvOk" in h and "먼저 발행한 계산서부터" in h)

print("§2 입금 완료 판정")
O2 = reg("고침2", "가상고객A")
tax(O2, (T - timedelta(days=5)).isoformat(), 500000)        # 1차 500,000 (발행일 있음)
with D.db_session() as c:                                     # 2차 = 금액만(발행일 없음)
    c.execute("UPDATE order_items SET tax_invoice_amt2=500000, tax_invoice_date2=NULL WHERE order_id=?", (O2,))
r = post({"order_id": O2, "received_at": T.isoformat(), "amount": 550000})
with D.db_session() as c:
    st = c.execute("SELECT status FROM orders WHERE id=?", (O2,)).fetchone()[0]
check("1차만 받음(2차는 발행일 없음) → 입금 완료(PAID) 아님", r.status_code == 200 and st != "PAID", (r.text[:120], st))

print("§3 수금 알림 실패 → 다시")
import threading as TH
from datetime import datetime as DT
timers = []
class FakeTimer:
    def __init__(self, s, f): timers.append((s, f.__name__)); self.daemon = True
    def start(self): pass
_real_timer, _real_now, _real_chk = TH.Timer, M._kst_wall_now, M.check_receivable_alerts
TH.Timer = FakeTimer
M._kst_wall_now = lambda: DT(2026, 11, 24, 9, 30)
def _boom(*a, **k): raise RuntimeError("database is locked(시험)")
M.check_receivable_alerts = _boom
M._ar_alert_tick_z100()
with D.db_session() as c:
    last = (c.execute("SELECT value FROM app_settings WHERE key='ar_alert_last_run_z100'").fetchone() or [None])[0]
check("보내다 실패 → 오늘 몫 풀림(다시 보낼 수 있음) · 10분 뒤 다시 예약 · 다음 날 예약도",
      (last or "") == "" and ("_ar_alert_retry_z100" in [n for _, n in timers]) and any(s == 600 for s, _ in timers)
      and "_ar_alert_tick_z100" in [n for _, n in timers], (last, timers))
sent = []
M.check_receivable_alerts = lambda *a, **k: (sent.append(1) or {"recipients": 1, "sent": 1, "new": 0, "messenger": True})
M._ar_alert_retry_z100()
with D.db_session() as c:
    last = c.execute("SELECT value FROM app_settings WHERE key='ar_alert_last_run_z100'").fetchone()[0]
check("10분 뒤 다시 → 보내고 오늘 몫 잡음", sent == [1] and last == "2026-11-24", (sent, last))
M._ar_alert_retry_z100()
check("또 불려도 두 번 안 보냄", sent == [1], sent)
TH.Timer, M._kst_wall_now, M.check_receivable_alerts = _real_timer, _real_now, _real_chk

print("§4 권한")
r = q(cl.post, "/sales/alerts/check")
check("수동 「지금 보내기」: 일반 영업 담당 → 403", r.status_code == 403, r.status_code)
S["user"] = CEO
r = q(cl.post, "/sales/alerts/check")
check("대표 → 200", r.status_code == 200, r.status_code)
r = q(cl.post, "/sales/ar-alert/recipients", json={"user_ids": [OUT["id"]]})
check("받는 사람: 매출 권한 없는 다른 부서 직원 → 400(고객사 금액 알림이라)", r.status_code == 400, r.status_code)
r = q(cl.post, "/sales/ar-alert/recipients", json={"user_ids": [AN["id"], SALES["id"]]})
check("매출 권한자는 됨", r.status_code == 200 and r.json().get("ids") == [AN["id"], SALES["id"]], r.text[:200])
S["user"] = SALES

print("§5 운영 DB 에서만")
src = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check("기동: KNK_RUN_AR_ALERT 없으면 DB 경로가 /opt/knk_haist/ 일 때만 시계 켬", 'startswith("/opt/knk_haist/")' in src and '_ar_env == ""' in src)

print("§6 🆕 등록 첫 화면 · 엑셀 일괄 등록")
def cards_of(h): return [c.split("?")[0] for c in re.findall(r'<a class="pc-card[^"]*" href="([^"]+)"', h)]
S["user"] = OUT
r = q(cl.get, "/projects/new", follow_redirects=False)
# z1191z102 (대표 11-22 「고객사 등록도 기술영업팀만」): 권한 없는 분께 「고객사 카드만」 열던 것 되돌림 → 홈으로
check("매출 등록 권한 없는 분: 🆕 등록 → 홈으로(z102)", r.status_code == 303 and r.headers.get("location", "").startswith("/home"), (r.status_code, r.headers.get("location")))
r = q(cl.get, "/projects/new?type=OTHER", follow_redirects=False)
check("그분이 프로젝트 등록 폼으로 바로 가면 여전히 막힘", r.status_code == 303, r.status_code)
S["user"] = VIEWER   # 매출 보기만(등록 권한 없음)
hm = q(cl.get, "/sales").text
check("메뉴(매출 보기만 · 등록 권한 없음): 🧾 마감 · 🆕 등록 안 보임(경로와 같게 · z102)", "/sales/shipments-receipts" not in menu(hm) and "/projects/new" not in menu(hm), menu(hm))
S["user"] = SALES
h = q(cl.get, "/projects/new").text
check("기술영업 담당: 카드 8개 · 엑셀 일괄 등록 보임", len(cards_of(h)) == 8 and "📥 엑셀 일괄 등록" in h, cards_of(h))
S["user"] = EXE
h = q(cl.get, "/projects/new").text
check("수동발행 권한 없는 매출 등록 권한자(임원): 엑셀 일괄 등록 안 보임", "📥 엑셀 일괄 등록" not in h)
r = q(cl.post, "/projects/import-confirm", json={"rows": []})
check("그분이 엑셀 일괄 등록을 보내도 403", r.status_code == 403 and "수동발행 권한" in r.json().get("error", ""), r.text[:160])

print("§7 관리번호 직접 입력 = 수동발행 권한")
FORM = dict(BASE, project_name="직접번호1", customer_name="가상고객A", sales="가상영업", mgmt_code="901T2611")
r = q(cl.post, "/projects/new", data=FORM, follow_redirects=False)
check("권한 없는 분(임원)이 신규에 관리번호 직접 → 막힘(manual_mgmt_denied)", r.status_code == 303 and "manual_mgmt_denied" in r.headers.get("location", ""), r.headers.get("location"))
with D.db_session() as c:
    n9 = c.execute("SELECT COUNT(*) FROM projects WHERE mgmt_code='901T2611'").fetchone()[0]
check("그 번호로 만들어지지 않음", n9 == 0, n9)
S["user"] = SALES
r = q(cl.post, "/projects/new", data=dict(FORM, mgmt_code="902M2611", project_name="직접번호2"), follow_redirects=False)
check("기술영업 담당이라도 사업부 글자가 틀리면(T 등록에 M) → manual_mgmt_invalid", "manual_mgmt_invalid" in r.headers.get("location", ""), r.headers.get("location"))
r = q(cl.post, "/projects/new", data=dict(FORM, mgmt_code="903T2611", project_name="직접번호3"), follow_redirects=False)
with D.db_session() as c:
    n3 = c.execute("SELECT COUNT(*) FROM projects WHERE mgmt_code='903T2611'").fetchone()[0]
check("기술영업 담당 · 맞는 번호 → 그 번호로 등록", r.status_code == 303 and n3 == 1, (r.headers.get("location"), n3))
hf = q(cl.get, "/projects/new?type=OTHER&err=manual_mgmt_denied&code=901E2611").text
check("「E 기타」 폼: 권한 없음 안내 글", "관리번호 수동발행 권한" in hf)

print("§8 남은 옛 이름 · 메뉴 찾기 · 내 건만")
g = q(cl.get, "/sales/flow-guide").text
check("안내 끝 줄: 「🎯 수주 전」·「📋 프로젝트 → 📑 수주 목록」(옛 「📑 수주」 메뉴 이름 없음)", "「🎯 수주 전」" in g and "📑 수주 목록" in g and "「📑 수주」" not in g)
src_mc = io.open(os.path.join(ROOT, "app", "menu_catalog.py"), encoding="utf-8").read()
check("빅터 메뉴 찾기: 💰 입금 확인(M-01-18 · 입금·수금) · 견적서 올리기 = 견적 관리(z1191z105)",
      '"M-01-18"' in src_mc and '"/sales/receipts-check", ["입금", "수금"' in src_mc and '"/sales/quotes/new"' not in src_mc
      and '("M-01-02-N", "01", "견적서 올리기",    "/sales/quotations"' in src_mc)
hh = io.open(os.path.join(ROOT, "app", "templates", "home.html"), encoding="utf-8").read()
check("통합 홈 「새 견적 작성」 → 🆕 등록", '<a class="action-card" href="/projects/new">' in hh and 'href="/sales/quotes/new"' not in hh)
hp = q(cl.get, "/projects?q=고침&view=list").text
m = re.search(r'<a href="(/projects\?[^"]*)" id="projMineBtn"', hp)
check("「👤 내 건만」 누를 때 검색어·보기 값 그대로", bool(m) and "q=" in m.group(1) and "view=list" in m.group(1) and "mine=1" in m.group(1), m.group(1) if m else None)
q(cl.get, "/projects?mine=1")
hp2 = q(cl.get, "/projects").text
check("켜져 있으면 「· 남의 건 숨김」 표시", "남의 건 숨김" in hp2)
q(cl.get, "/projects?mine=0")

print("\n결과: OK %d · FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
