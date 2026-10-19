# -*- coding: utf-8 -*-
"""z1191d 시험 — 상세 맨 위 「거래 구분」: 호기 거래구분이 섞이면 「내수·수출 섞임 (수출 2대 · 내수 1대)」
   (대표 2026-10-19 「내수,수출 섞임(수출2건,내수1대)으로 보이게 해주세요!!」 · 이새롬 프로 011T2607)
  §1 서버(임시 DB · TestClient · 실제 등록 흐름): 011T2607 꼴(신규 수출 + 추가 수출 + 추가 내수) → 섞임·대수 ·
     내수 수주 취소 → 섞임 아님 · 섞이지 않은 프로젝트는 예전 그대로 · 표시 이름(hf_export_disp) 한 번
  §2 바뀐 곳 원문
"""
import contextlib
import io
import os
import re
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191d-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191d_")
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
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version) "
                 "VALUES ('가상관리자', 'admin', 'T901', 'T901', 'sso_only_no_local_password', 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T901'").fetchone())
    ccols = {r[1] for r in conn.execute("PRAGMA table_info(customers)")}
    for col in ("alias", "country"):
        if col not in ccols:
            conn.execute("ALTER TABLE customers ADD COLUMN %s TEXT" % col)
    CUST = {}
    for key, name, alias, country in (("VINA", "가상 VINA", "가상 VINA", "Vietnam"), ("DT", "(주) 가상드림", "가상드림(동탄)", "")):
        conn.execute("INSERT INTO customers (name, alias, country) VALUES (?,?,?)", (name, alias, country))
        CUST[key] = conn.execute("SELECT id FROM customers WHERE alias=?", (alias,)).fetchone()[0]

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M.get_user = lambda request: ADMIN
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0
ALIAS = {"VINA": "가상 VINA", "DT": "가상드림(동탄)"}


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


BASE = {"quick": "1", "biz_div": "T", "project_type": "NEW_EQUIP", "status": "진행중", "confirm_now": "1",
        "order_date": "2026-10-02", "due_date": "2026-10-20", "equip_name": "기능검사기", "model": "PBA",
        "unit_qty": "1", "shipment_form": "ASSEMBLY", "currency": "KRW"}


def post(**kw):
    f = dict(BASE)
    f.update(kw)
    with contextlib.redirect_stdout(io.StringIO()):
        r = cl.post("/projects/new", data=f)
    return r.status_code, r.headers.get("location", "")


def proj(name):
    with D.db_session() as c:
        r = c.execute("SELECT * FROM projects WHERE name=? ORDER BY id DESC", (name,)).fetchone()
        return dict(r) if r else None


def orders_of(pid):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT * FROM orders WHERE project_id=? ORDER BY id", (pid,))]


def header(pid):
    with contextlib.redirect_stdout(io.StringIO()):
        r = cl.get("/project/%d" % pid)
    m = re.search(r"<dt>거래 구분</dt><dd>(.*?)</dd>", r.text, re.S)
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip() if m else None
    return r.status_code, txt, r.text.count('id="hf_export_disp"')


print("=" * 78)
print("§1 서버")
print("=" * 78)
st, loc = post(name="z1191d-A", po_type="신규", customer_name=ALIAS["VINA"], customer_id=str(CUST["VINA"]), is_export="1",
               unit_price="1000", order_amount="1000", **{"unit_amount[]": ["1000"]})
A = proj("z1191d-A")
fu = dict(name="z1191d-A", mgmt_code=A["mgmt_code"], unit_price="2000", order_amount="2000", **{"unit_amount[]": ["2000"]})
st2, _ = post(po_type="추가", customer_name=ALIAS["VINA"], customer_id=str(CUST["VINA"]), is_export="1", **fu)
st3, _ = post(po_type="개조", customer_name=ALIAS["DT"], customer_id=str(CUST["DT"]), is_export="0", **fu)
os_ = orders_of(A["id"])
check("준비: 011T2607 꼴 — 신규 수출 · 추가 수출 · 추가 내수(개조) 세 수주", st == 303 and st2 == 303 and st3 == 303 and len(os_) == 3,
      (st, st2, st3, len(os_)))
sc, txt, n_id = header(A["id"])
check("1 맨 위 거래 구분 = 「내수·수출 섞임 (수출 2대 · 내수 1대)」", sc == 200 and txt == "내수·수출 섞임 (수출 2대 · 내수 1대)", (sc, txt))
check("   표시 이름(hf_export_disp)은 한 번만", n_id == 1, n_id)
with D.db_session() as c:
    c.execute("UPDATE orders SET status='CANCELLED' WHERE id=?", (os_[2]["id"],))
sc, txt, n_id = header(A["id"])
check("2 내수 수주를 취소하면 → 섞임 아님 · 「수출」", sc == 200 and txt == "수출" and n_id == 1, (sc, txt, n_id))
with D.db_session() as c:
    c.execute("UPDATE orders SET status='CONFIRMED' WHERE id=?", (os_[2]["id"],))
    c.execute("UPDATE order_items SET unit_status='취소' WHERE order_id=?", (os_[2]["id"],))
sc, txt, _n = header(A["id"])
check("   내수 호기를 취소하면 → 섞임 아님", txt == "수출", txt)
st, loc = post(name="z1191d-B", po_type="신규", customer_name=ALIAS["DT"], customer_id=str(CUST["DT"]), is_export="0",
               unit_price="1000", order_amount="1000", **{"unit_amount[]": ["1000"]})
B = proj("z1191d-B")
sc, txt, n_id = header(B["id"])
check("3 섞이지 않은 내수 프로젝트 → 예전 그대로 「내수」", sc == 200 and txt == "내수" and n_id == 1, (sc, txt, n_id))

print()
print("=" * 78)
print("§2 바뀐 곳 원문")
print("=" * 78)
pd = open(os.path.join(ROOT, "app", "templates", "project_detail.html"), encoding="utf-8").read()
check("상세 화면: 섞임 셈(namespace · do 확장 없이) · 섞임 표시 · 예전 두 표시 그대로",
      "{% set _ix1191 = namespace(eu=0, du=0, es=0, ds=0) %}" in pd and ">내수·수출 섞임</span>" in pd and "{% do " not in pd
      and pd.count('id="hf_export_disp"') == 3)
line = [l for l in pd.splitlines() if "z1191d" in l]
check("   z1191d 줄은 HTML 쪽(스크립트 아님) — Jinja 주석으로만 표시", bool(line) and all("{#" in l for l in line), line[:1])

print()
print("결과: %d개 중 실패 %d" % (OK + FAIL, FAIL))
sys.exit(1 if FAIL else 0)
