# -*- coding: utf-8 -*-
"""z1191z102 시험 — 고객사 등록 = 기술영업팀 + 대표만 (대표 11-22 「고객사 등록도 기술영업팀만」 → 「기술영업팀 + 대표만」)
  §1 관리팀(매출 등록 권한 있음 · 기술영업팀 아님) = 새 고객사 못 만듦(화면·저장·엑셀·관리 도구) · 고치기는 그대로
  §2 기술영업팀 · 대표 = 됨  §3 매출 등록 권한 없는 분 = 🆕 등록 안 보임·홈으로(z101 되돌림)"""
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z102-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z102_")
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
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, can_view_sales, can_use_sales) "
                 "VALUES ('가상관리팀', 'admin', 'Z987', 'Z987', 'x', 1, 1, NULL, 1, 1)")
    SALES = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z981'").fetchone())
    VIEWER = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z982'").fetchone())
    CEO = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z983'").fetchone())
    AN = dict(conn.execute("SELECT * FROM users WHERE employee_no='67'").fetchone())
    OUT = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z985'").fetchone())
    EXE = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z986'").fetchone())
    ADM = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z987'").fetchone())
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



def cards_of(h): return [c.split("?")[0] for c in re.findall(r'<a class="pc-card[^"]*" href="([^"]+)"', h)]
def ncust(name):
    with D.db_session() as c:
        return c.execute("SELECT COUNT(*) FROM customers WHERE name=?", (name,)).fetchone()[0]
NEW = {"name": "새고객관리팀", "biz_no": "123-45-61111", "ceo_name": "홍길동", "address": "서울", "is_active": "1"}

print("§1 관리팀(매출 등록 권한 · 기술영업팀 아님)")
S["user"] = ADM
r = q(cl.get, "/customers/new", follow_redirects=False)
check("고객사 등록 화면 → 고객사 목록으로(안내)", r.status_code == 303 and "reg_customer_denied" in r.headers.get("location", ""), (r.status_code, r.headers.get("location")))
r = q(cl.post, "/customers/new", data=NEW, follow_redirects=False)
check("저장도 막힘 · 안 만들어짐", r.status_code == 303 and ncust("새고객관리팀") == 0, (r.status_code, ncust("새고객관리팀")))
h = q(cl.get, "/projects/new").text
check("🆕 등록 첫 화면: 🤝 고객사 카드 없음 · 「기술영업팀에서 합니다」", "/customers/new" not in cards_of(h) and "기술영업팀에서 합니다" in h, cards_of(h))
for path in ("/customers/import-xlsx", "/customers/import-verify"):
    r = q(cl.post, path, files={"xlsx": ("a.xlsx", b"x", "application/octet-stream")})
    check("엑셀 일괄 %s → 403" % path.split("/")[-1], r.status_code == 403, r.status_code)
r = q(cl.post, "/customers/import-confirm", json={"rows": []})
check("엑셀 일괄 확정 → 403", r.status_code == 403, r.status_code)
r = q(cl.post, "/api/admin/customer", json={"name": "관리도구고객"})
check("옛 관리 도구로 새 고객사 → 403 · 안 만들어짐", r.status_code == 403 and ncust("관리도구고객") == 0, r.status_code)
with D.db_session() as c:
    cid = c.execute("SELECT id FROM customers WHERE name='가상고객A'").fetchone()[0]
r = q(cl.post, "/api/admin/customer", json={"id": cid, "name": "가상고객A", "tier": "일반", "note": "고치기"})
check("고치기는 그대로 됨", r.status_code == 200, r.status_code)
r = q(cl.post, "/api/admin/import-mgmt", files={"file": ("a.xlsx", b"x", "application/octet-stream")})
check("관리번호 대장 가져오기(고객사 자동 생성) → 403", r.status_code == 403, r.status_code)
hl = q(cl.get, "/customers").text
check("고객사 목록: 엑셀 일괄 업로드 단추 없음 · 「새 고객사 등록은 기술영업팀에서」", "📤 엑셀 일괄 업로드</button>" not in hl and "새 고객사 등록은 기술영업팀에서 합니다" in hl)
hl2 = q(cl.get, "/customers?err=reg_customer_denied").text
check("막혔을 때 안내 글", "기술영업팀(또는 대표)</b>만 할 수 있습니다" in hl2)
ha = io.open(os.path.join(ROOT, "app", "templates", "admin.html"), encoding="utf-8").read()
check("관리 화면 「＋ 고객사 추가」 단추 없음(안내 글)", 'href="/customers/new">＋ 고객사 추가' not in ha and "새 고객사 등록은 기술영업팀" in ha)

print("§2 기술영업팀 · 대표")
for who, U in (("기술영업팀", SALES), ("대표", CEO)):
    S["user"] = U
    nm = "새고객" + who
    r = q(cl.get, "/customers/new")
    r2 = q(cl.post, "/customers/new", data=dict(NEW, name=nm, biz_no="123-45-6%04d" % len(who)), follow_redirects=False)
    check("%s: 등록 화면 200 · 저장 → 만들어짐" % who, r.status_code == 200 and r2.status_code in (302, 303) and ncust(nm) == 1, (r.status_code, r2.status_code, ncust(nm)))
    h = q(cl.get, "/projects/new").text
    check("%s: 🆕 등록에 🤝 고객사 카드" % who, "/customers/new" in cards_of(h))
    hl = q(cl.get, "/customers").text
    check("%s: 고객사 목록 엑셀 일괄 업로드 단추 · 「🆕 등록 → 🤝 고객사」 안내" % who, "📤 엑셀 일괄 업로드</button>" in hl and "🆕 등록 → 🤝 고객사" in hl)

print("§3 매출 등록 권한 없는 분")
S["user"] = OUT
r = q(cl.get, "/projects/new", follow_redirects=False)
check("🆕 등록 → 홈으로(z101 「고객사 카드만」 되돌림)", r.status_code == 303 and r.headers.get("location", "").startswith("/home"), (r.status_code, r.headers.get("location")))
S["user"] = VIEWER
hm = q(cl.get, "/sales").text
check("매출 보기만(등록 권한 없음): 메뉴에 🆕 등록 · 🧾 마감 안 보임", "/projects/new" not in menu(hm) and "/sales/shipments-receipts" not in menu(hm), menu(hm))
S["user"] = SALES

print("\n결과: OK %d · FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
