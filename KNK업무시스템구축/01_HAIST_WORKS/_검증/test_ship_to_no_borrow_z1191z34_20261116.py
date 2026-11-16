# -*- coding: utf-8 -*-
"""z1191z34 시험 — 작업일정표 납품위치: 같은 관리번호 「다른 수주」 납품처를 빌려 보이지 않음 (이새롬 프로 신고 · 대표 「B로 진행해」 2026-11-16)
  신고: 002T2605 마지막 수주 T-261103-1(국내 납품) 납품위치가 「드림텍 베트남」 · 지워도 다시 보임 · 수주·호기 납품처는 빈칸
  원인: 줄·수주 납품처가 비면 같은 관리번호 다른 수주 납품처를 빌려 보임(v5H226z263 보강)
  ① 빈 수주 줄 = 빈칸(＋)  ② 자기 수주 값은 그대로  ③ 줄에 적으면 보임 · 지우면 지워짐  ④ 엑셀/행 만들기도 같음
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z34-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z34_")
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


with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상관리자', 'admin', 'T934', 'T934', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T934'").fetchone())
    CU = ins(c, "customers", {"name": "가상드림텍(동탄)", "alias": "가상드림텍"})
    P = ins(c, "projects", {"code": "002T2605", "name": "PBA", "mgmt_code": "002T2605", "customer_id": CU, "customer_name": "가상드림텍(동탄)",
                            "currency": "KRW", "status": "진행중", "stage": "진행중", "biz_div": "T", "project_type": "NEW_EQUIP",
                            "shipment_form": "ASSEMBLY", "form_type": "제품", "order_date": "2026-09-01", "due_date": "2026-09-25", "is_archived": 0})
    A = ins(c, "orders", {"project_id": P, "order_no": "T-260303-9", "customer_id": CU, "so_type": "EQUIPMENT", "currency": "KRW", "status": "SHIPPED",
                          "order_date": "2026-09-01", "due_date": "2026-09-10", "total_amount": 1000, "ship_to": "드림텍 베트남"})
    IA = ins(c, "order_items", {"order_id": A, "unit_label": "1호기", "qty": 1, "amount": 1000, "unit_status": "출하"})
    B = ins(c, "orders", {"project_id": P, "order_no": "T-261103-1", "customer_id": CU, "so_type": "EQUIPMENT", "currency": "KRW", "status": "SHIPPED",
                          "order_date": "2026-09-03", "due_date": "2026-09-13", "total_amount": 674000, "ship_to": None})
    IB = ins(c, "order_items", {"order_id": B, "unit_label": "도전봉", "qty": 1, "amount": 674000, "unit_status": "출하"})

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


def board():
    h = q(cl.get, "/sales/schedule?ym=2026-09").text
    out = {}
    for m in re.finditer(r'<tr[^>]*data-soid="(\d+)"[^>]*>(.*?)</tr>', h, re.S):
        td = re.search(r'data-edit="ship_to"[^>]*>([^<]*)</td>', m.group(2))
        if td:
            out[int(m.group(1))] = td.group(1).strip()
    rows = q(M.build_schedule_board_rows, ADMIN, 2026, 9)["rows"]
    fn = {r.get("so_no"): (r.get("ship_to") or "") for r in rows if r.get("is_unit")}
    return out, fn


def unit_ship(iid, v):
    return q(cl.post, "/sales/schedule/unit-field", json={"iid": iid, "field": "ship_to", "value": v}).json()


print("§1 빌려 보이지 않음")
S, F = board()
check(S.get(B) == "＋" and F.get("T-261103-1") == "", "납품처 빈 수주 T-261103-1 = 빈칸(＋) — 다른 수주 「드림텍 베트남」 안 빌림(화면·엑셀)", (S, F))
check(S.get(A) == "드림텍 베트남" and F.get("T-260303-9") == "드림텍 베트남", "자기 수주 납품처가 있는 줄은 그대로", (S.get(A), F.get("T-260303-9")))
print("§2 적으면 보이고 지우면 지워짐")
j = unit_ship(IB, "아산 본사")
S, F = board()
check(j.get("ok") and S.get(B) == "아산 본사" and F.get("T-261103-1") == "아산 본사", "줄에 「아산 본사」 적음 → 보임", (j, S.get(B)))
j = unit_ship(IB, "")
S, F = board()
check(j.get("ok") and S.get(B) == "＋" and F.get("T-261103-1") == "", "지우면 빈칸(＋) — 다시 「드림텍 베트남」으로 돌아오지 않음", (j, S.get(B)))
check(S.get(A) == "드림텍 베트남", "다른 수주 값은 그대로", S.get(A))

print()
print("결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
