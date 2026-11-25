# -*- coding: utf-8 -*-
"""z1191z155 (대표 11-25 「사실 = 수주」 남은 세 가지):
   ① 매출 보고서 VINA 2차 — 수주 2차 칸이 NULL(안 정함)이면 관리번호 2차로 대신 세지 않고 「⚠ 2차 미정(확인 필요)」 줄로 따로 · 금액 합은 그대로
   ② 수출 CI — 통화·구매자·최종 고객 = 수주 값(모두 같을 때) · 다르면 알림(ci_warn155)
   ③ 목록·대시 모아 보기(z155_so_mix) · 제작요청서 거래구분 기본값 = 고른 수주 품목 줄 · 화면 열기만으로 저장 안 함
   임시 DB · TestClient · 운영 아님"""
import contextlib
import io
import os
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z155-test-only-not-a-real-key"
import app.database as D  # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z155_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상영업', 'admin', 'T155', 'T155', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T155'").fetchone())
    conn.execute("INSERT INTO customers (name) VALUES ('KNK VINA')")
    VINA = conn.execute("SELECT id FROM customers WHERE name='KNK VINA'").fetchone()[0]
    conn.execute("INSERT INTO customers (name) VALUES ('가상삼성')")
    SAM = conn.execute("SELECT id FROM customers WHERE name='가상삼성'").fetchone()[0]
import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

M.get_user = lambda request: ADMIN
cl = TestClient(M.app, follow_redirects=False)
R = []


def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:300]))


ocols = None
with D.db_session() as c:
    ocols = {r[1] for r in c.execute("PRAGMA table_info(orders)")}
    icols = {r[1] for r in c.execute("PRAGMA table_info(order_items)")}
    c.execute("INSERT INTO projects (mgmt_code, name, customer_id, customer_name, secondary_customer, currency, is_export, project_type) "
              "VALUES ('901M2611', '가상 관리번호', ?, 'KNK VINA', 'SEV', 'USD', 1, 'NEW_EQUIP')", (VINA,))
    PID = c.execute("SELECT id FROM projects WHERE mgmt_code='901M2611'").fetchone()[0]

    def mk_so(no, cid, end, ccy, amt, od):
        cols = ["project_id", "order_no", "customer_id", "currency", "total_amount", "order_date", "status"]
        vals = [PID, no, cid, ccy, amt, od, "CONFIRMED"]
        if "end_customer" in ocols:
            cols.append("end_customer"); vals.append(end)
        c.execute("INSERT INTO orders (%s) VALUES (%s)" % (",".join(cols), ",".join("?" * len(cols))), vals)
        oid = c.execute("SELECT id FROM orders WHERE order_no=?", (no,)).fetchone()[0]
        icol = ["order_id", "qty", "unit_price", "amount", "currency", "unit_label", "order_date"]
        ival = [oid, 1, amt, amt, ccy, "1호기", od]
        if "is_export" in icols:
            icol.append("is_export"); ival.append(1 if ccy != "KRW" else 0)
        c.execute("INSERT INTO order_items (%s) VALUES (%s)" % (",".join(icol), ",".join("?" * len(icol))), ival)
        return oid
    O1 = mk_so("M-261101-1", VINA, None, "USD", 1000.0, "2026-11-01")     # 2차 안 정함
    O2 = mk_so("M-261102-1", VINA, "SEVT", "USD", 500.0, "2026-11-02")    # 2차 SEVT
    O3 = mk_so("M-261103-1", SAM, None, "KRW", 2000000.0, "2026-11-03")   # 다른 고객 · 원화

# ① 매출 보고서 줄
with D.db_session() as c:
    rates = M._fx_load_rates(c) if hasattr(M, "_fx_load_rates") else {}
    with contextlib.redirect_stdout(io.StringIO()):
        lines = M._z17_lines(c, rates, {}, "order")[0]
        rep = M._sales_report_z17(c, rates, {}, "order", "year", 2026, 1, 11)
mine = [x for x in lines if x.get("code") == "901M2611"]
l1 = [x for x in mine if x["so"] == "M-261101-1"]
l2 = [x for x in mine if x["so"] == "M-261102-1"]
check("① 2차 안 정한 수주 = c2_tbd · 2차 칸 비움(관리번호 SEV 를 대신 쓰지 않음)", l1 and l1[0].get("c2_tbd") is True and not l1[0].get("cust2"), l1[:1])
check("   2차 정한 수주 = 그 값(SEVT) · c2_tbd 아님", l2 and l2[0].get("cust2") == "SEVT" and not l2[0].get("c2_tbd"), l2[:1])
vr = rep.get("vina_rows") if isinstance(rep, dict) else None
if vr is not None:
    names = {a["name"]: a for a in vr}
    check("   VINA 2차 표 = 「⚠ 2차 미정(확인 필요)」 줄 따로 · SEV 줄 없음", M.Z155_TBD in names and "SEV" not in names, list(names))
else:
    print("· vina_rows 는 다른 함수에서 모음 — 줄 단위만 확인")

# ② 수출 CI
with D.db_session() as c:
    p, ci, ln = M._export_ci_build(c, PID)
check("② CI(세관 문서) 글은 예전 그대로 · 수주마다 다르면 알림만(통화·구매자·최종 고객 미정)",
      ci and any("통화" in w for w in ci.get("ci_warn155", [])) and any("구매자" in w for w in ci["ci_warn155"])
      and any("최종 고객" in w for w in ci["ci_warn155"]) and ci["buyer"] == "KNK VINA" and ci["final_customer"] == "SEV",
      ci and {k: ci[k] for k in ("buyer", "final_customer", "currency", "ci_warn155")})

# ③ 모아 보기 · 화면 열기만으로 저장 안 함
mx = M._z155_so_mix().get(PID) or {}
check("③ 모아 보기 = 통화 USD·KRW · 고객 둘", set(mx.get("ccys", [])) == {"USD", "KRW"} and len(mx.get("custs", [])) == 2, mx)


def fp():
    with D.db_session() as c:
        return (c.execute("SELECT COUNT(*), COALESCE(SUM(LENGTH(COALESCE(note,''))),0) FROM project_history").fetchone(),
                [tuple(r) for r in c.execute("SELECT id, customer_id, COALESCE(end_customer,'<N>'), currency, total_amount FROM orders WHERE project_id=? ORDER BY id", (PID,))],
                tuple(c.execute("SELECT customer_id, COALESCE(secondary_customer,''), currency, COALESCE(order_amount,0) FROM projects WHERE id=?", (PID,)).fetchone()))


before = fp()
codes = {}
for path in ("/projects", "/sales/report", "/project/%d" % PID, "/progress", "/export/prep/%d" % PID, "/export/prep/%d/invoice" % PID):
    with contextlib.redirect_stdout(io.StringIO()):
        r = cl.get(path)
    codes[path] = r.status_code
after = fp()
check("   화면 6곳 열기 → 오류 없음(500 아님)", all(v < 500 for v in codes.values()), codes)
check("   화면 열기만으로 DB 그대로(이력·수주·관리번호)", before == after, (before, after))

# 제작요청서 거래구분 기본값 = 고른 수주 품목 줄
src = open(os.path.join(ROOT, "app", "templates", "prod_request_edit.html"), encoding="utf-8").read()
check("   제작요청서 거래구분 = z48.iex155(고른 수주) · 없으면 「(대표값 · 확인 필요)」", src.count("z48.iex155") >= 2 and "(대표값 · 확인 필요" in src)

print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
