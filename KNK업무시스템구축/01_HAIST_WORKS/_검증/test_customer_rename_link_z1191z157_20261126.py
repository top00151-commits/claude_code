# -*- coding: utf-8 -*-
"""z1191z157 (대표 11-26 「고객사 이름만 바뀔 때도 기존 등록한 것과 연결」):
   ① 공용 해석 — 지금 이름 → 시스템명 → 옛 이름(이력) · 딱 한 곳만 · 두 곳 겹침·지점 여러 곳·사용안함 = 연결 안 함
   ② 매출 보고서 VINA = 고객 번호(이름을 「KNK VINA CO LTD」로 바꿔도 · 한 번 더 바꿔도) · 금액 그대로
   ③ 소모품 목록·상세 = 지금 이름으로 보임(DB 글자는 그대로) · 소모품 엑셀 짝짓기(옛 이름·시스템명·겹침)
   ④ 고객사 이름 변경 화면 — 미리보기(읽기 전용) · 확인 없는 저장 = 아무것도 안 바뀜 · 확인 저장 = 같은 번호 자료 이름 함께 + 줄마다 이력
      · 시스템명 글자(드림텍(아산) 식)는 그대로 · 세금계산서는 그대로
   ⑤ 고객사 엑셀 일괄 등록에 옛 이름 = 새로 안 만듦 · 화면 열기만으로 DB 그대로
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z157-test-only-not-a-real-key"
import app.database as D  # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z157_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
    D.migrate_customers_name_unique()   # 운영처럼 같은 정식명 여러 지점 허용(z619)
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상실무', 'admin', 'T157', 'T157', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T157'").fetchone())

    def cust(name, alias="", sbn="", active=1):
        conn.execute("INSERT INTO customers (name, alias, sub_biz_no, is_active) VALUES (?,?,?,?)", (name, alias, sbn, active))
        return conn.execute("SELECT MAX(id) FROM customers").fetchone()[0]
    VINA = cust("KNK VINA", "")
    SEV = cust("가상 SAMSUNG VIETNAM", "SEV")
    DH = cust("(주) 가상드림", "가상드림(본사)")
    DA = cust("(주) 가상드림", "가상드림(아산)", "0005")
    X1 = cust("가상 하나", "")
    X2 = cust("가상 둘", "")
    OFF = cust("가상 옛회사(사용안함)", "")
    # 이력 — 옛 이름(VINA 는 아래 ④에서 화면으로 바꿈)
    for cid, ov, nv in ((SEV, "가상 SAMSUNG VN", "가상 SAMSUNG VIETNAM"),
                        (DH, "(주)가상드림", "(주) 가상드림"),
                        (X1, "가상 겹친이름", "가상 하나"), (X2, "가상 겹친이름", "가상 둘"),
                        (OFF, "가상 옛회사", "가상 옛회사(사용안함)")):
        conn.execute("INSERT INTO customer_history(customer_id, changed_by, field, old_value, new_value, note) VALUES(?,?,?,?,?,?)",
                     (cid, None, "고객사명", ov, nv, "시험"))
import app.main as M  # noqa: E402
import app.consumables as CO  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

M.get_user = lambda request: ADMIN
cl = TestClient(M.app, follow_redirects=False)
R = []


def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:400]))


# ── ① 공용 해석
with D.db_session() as c:
    r = lambda n: D.resolve_customer_by_name(c, n)
    check("① 지금 이름 = 연결", r("가상 SAMSUNG VIETNAM")["id"] == SEV)
    check("   시스템명 = 연결", r("SEV")["id"] == SEV and r("SEV")["how"] == "alias")
    o = r("가상 SAMSUNG VN")
    check("   옛 이름 = 같은 고객 번호 + 지금 이름 알려 줌", o["id"] == SEV and o["how"] == "old" and o["cur_name"] == "가상 SAMSUNG VIETNAM", o)
    check("   옛 이름이 두 고객사에 겹침 = 연결 안 함(ambiguous)", r("가상 겹친이름")["id"] is None and r("가상 겹친이름")["reason"] == "ambiguous")
    check("   옛 이름이지만 지점 여러 곳(같은 정식명) = 연결 안 함(unsafe)", r("(주)가상드림")["id"] is None and r("(주)가상드림")["reason"] == "unsafe")
    check("   옛 이름이지만 「사용안함」 고객사 = 연결 안 함", r("가상 옛회사")["id"] is None)
    check("   같은 정식명 지점 여러 곳 = 연결 안 함", r("(주) 가상드림")["id"] is None and r("(주) 가상드림")["reason"] == "ambiguous")
    check("   없는 이름 = 연결 안 함", r("가상 없는회사")["id"] is None and r("가상 없는회사")["reason"] == "unmatched")
    check("   resolve_customer_id 도 옛 이름 연결(이유 old_name)", D.resolve_customer_id(c, "가상 SAMSUNG VN") == (SEV, "old_name"))
    check("   resolve_customer_id 겹침 = 미연결 · 기존 연결 있으면 유지", D.resolve_customer_id(c, "가상 겹친이름") == (None, "ambiguous")
          and D.resolve_customer_id(c, "가상 겹친이름", prefer_id=X2) == (X2, "kept"))

# ── 자료 만들기: VINA 프로젝트·수주·소모품, 드림텍(아산) 시스템명 글자 프로젝트, 세금계산서
with D.db_session() as c:
    ocols = {r[1] for r in c.execute("PRAGMA table_info(orders)")}
    c.execute("INSERT INTO projects (mgmt_code, name, customer_id, customer_name, currency, is_export, project_type) "
              "VALUES ('901T2611', '가상 VINA 장비', ?, 'KNK VINA', 'USD', 1, 'NEW_EQUIP')", (VINA,))
    PV = c.execute("SELECT id FROM projects WHERE mgmt_code='901T2611'").fetchone()[0]
    c.execute("INSERT INTO projects (mgmt_code, name, customer_id, customer_name, currency, is_export, project_type) "
              "VALUES ('902T2611', '가상 아산 장비', ?, '가상드림(아산)', 'KRW', 0, 'NEW_EQUIP')", (DA,))
    PA = c.execute("SELECT id FROM projects WHERE mgmt_code='902T2611'").fetchone()[0]
    c.execute("INSERT INTO orders (project_id, order_no, customer_id, currency, total_amount, order_date, status) "
              "VALUES (?,?,?,?,?,?,?)", (PV, "T-261101-1", VINA, "USD", 1000.0, "2026-11-01", "CONFIRMED"))
    OV = c.execute("SELECT id FROM orders WHERE order_no='T-261101-1'").fetchone()[0]
    c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, currency, unit_label, order_date) VALUES (?,?,?,?,?,?,?)",
              (OV, 1, 1000.0, 1000.0, "USD", "1호기", "2026-11-01"))
    c.execute("INSERT INTO consumable_orders (co_no, mgmt_code, customer_id, customer_name, currency, total_amount, status, order_date, biz_div) "
              "VALUES ('C-261102-1', '901C2611', ?, 'KNK VINA', 'KRW', 500000, 'CONFIRMED', '2026-11-02', 'T')", (VINA,))
    COV = c.execute("SELECT id FROM consumable_orders WHERE co_no='C-261102-1'").fetchone()[0]
    c.execute("INSERT INTO consumable_orders (co_no, mgmt_code, customer_id, customer_name, currency, total_amount, status, order_date, biz_div) "
              "VALUES ('C-261103-1', '902C2611', ?, '가상 SAMSUNG VN', 'KRW', 300000, 'CONFIRMED', '2026-11-03', 'T')", (SEV,))
    COS = c.execute("SELECT id FROM consumable_orders WHERE co_no='C-261103-1'").fetchone()[0]
    tcols = {r[1] for r in c.execute("PRAGMA table_info(tax_invoices)")}
    c.execute("INSERT INTO tax_invoices (ti_no, issue_date, customer_name, customer_id, total_amount, currency, status) VALUES "
              "('TI-2611-0001','2026-11-05','KNK VINA',?,500000,'KRW','발행')", (VINA,))


def report_vina():
    with D.db_session() as c:
        rates = M._fx_load_rates(c)
        with contextlib.redirect_stdout(io.StringIO()):
            lines = M._z17_lines(c, rates, {}, "order")[0]
    v = [x for x in lines if x["is_vina"]]
    return len(v), round(sum(float(x["amt"]) for x in v), 2), sorted({x["cust"] for x in v})


def fp():
    with D.db_session() as c:
        out = []
        for t in ("projects", "consumable_orders", "orders", "tax_invoices", "customers", "customer_history", "project_history", "consumable_history"):
            out.append((t, [tuple(r) for r in c.execute("SELECT * FROM %s ORDER BY id" % t)]))
        return out


V0 = report_vina()
check("② 바꾸기 전 VINA = 프로젝트 1줄 + 소모품 1줄", V0[0] == 2, V0)

# ── ③ 소모품 목록·상세·엑셀 짝짓기(옛 이름 자료)
lst = {x["id"]: x for x in CO.co_list(limit=50)}
check("③ 소모품 목록 — 옛 이름(가상 SAMSUNG VN) 저장 줄이 지금 이름으로 보임 · DB 글자는 _saved 에",
      lst[COS]["customer_name"] == "가상 SAMSUNG VIETNAM" and lst[COS].get("customer_name_saved") == "가상 SAMSUNG VN", lst.get(COS))
check("   소모품 상세도 지금 이름", CO.co_get(COS)["customer_name"] == "가상 SAMSUNG VIETNAM")
m1 = CO.match_customer_by_name("가상 SAMSUNG VN")
m2 = CO.match_customer_by_name("SEV")
check("   엑셀 짝짓기 — 옛 이름 → 같은 고객 번호 · 지금 이름", m1 and m1["id"] == SEV and m1["name"] == "가상 SAMSUNG VIETNAM", m1)
check("   엑셀 짝짓기 — 시스템명 → 그 고객", m2 and m2["id"] == SEV, m2)
check("   엑셀 짝짓기 — 옛 이름 두 곳 겹침 = 연결 안 함", CO.match_customer_by_name("가상 겹친이름") is None)
check("   엑셀 짝짓기 — 같은 정식명 지점 여러 곳 = 연결 안 함(예전엔 첫 지점)", CO.match_customer_by_name("(주) 가상드림") is None)
with D.db_session() as c:
    cid_tax = D.resolve_customer_by_name(c, "가상 SAMSUNG VN")["id"]
check("   세금계산서 고객 연결(공용 해석) — 옛 이름도 같은 번호", cid_tax == SEV)

# ── ④ 고객사 이름 변경 화면
BEFORE_VIEW = fp()
codes = {}
for path in ("/customers/%d/edit" % VINA, "/customer/%d" % VINA, "/api/customers/%d/rename-preview?new_name=KNK%%20VINA%%20CO%%20LTD" % VINA,
             "/consumables", "/consumables/%d" % COV, "/projects", "/project/%d" % PV, "/sales/report", "/sales"):
    with contextlib.redirect_stdout(io.StringIO()):
        rr = cl.get(path)
    codes[path] = rr.status_code
check("④ 화면·미리보기 열기 → 오류 없음(500 아님)", all(v < 500 for v in codes.values()), codes)
check("   화면·미리보기 열기만으로 DB 그대로", fp() == BEFORE_VIEW)
pv = cl.get("/api/customers/%d/rename-preview" % VINA, params={"new_name": "KNK VINA CO LTD"}).json()
items = {x["table"]: x for x in pv.get("items", [])}
check("   미리보기 = 프로젝트 1건·소모품 1건 함께 바꿈 · 세금계산서는 서류라 그대로(바꿈 0)",
      pv.get("ok") and items.get("projects", {}).get("change") == 1 and items.get("consumable_orders", {}).get("change") == 1
      and any(d["table"] == "tax_invoices" for d in pv.get("documents", [])), pv)
form_src = open(os.path.join(ROOT, "app", "templates", "customer_form.html"), encoding="utf-8").read()
check("   수정 화면에 단계 줄(1 새 이름 적기 → 2 바뀔 곳 확인 → 3 이름 다시 고치기 → 4 저장 끝) · ✕ 닫기 · 취소 · 다시 고치기",
      all(k in form_src for k in ("'새 이름 적기'", "'바뀔 곳 확인'", "'(고칠 때만) 이름 다시 고치기'", "'저장 끝'", "✕ 닫기", "z157Re", "z157No")))

base_form = {"name": "KNK VINA CO LTD", "alias": "", "is_active": "1", "is_overseas": "1", "country": "VN"}
snap = fp()
with contextlib.redirect_stdout(io.StringIO()):
    r0 = cl.post("/customers/%d/edit" % VINA, data=base_form)
check("   확인 표시 없이 저장 → 돌려보냄 · 아무것도 안 바뀜", r0.status_code == 303 and "rename_confirm_needed=1" in r0.headers.get("location", "") and fp() == snap,
      (r0.status_code, r0.headers.get("location")))
with contextlib.redirect_stdout(io.StringIO()):
    r1 = cl.post("/customers/%d/edit" % VINA, data=dict(base_form, rename_confirm="1", alias="KNK VINA"))
loc = r1.headers.get("location", "")
check("   확인 저장 → 고객사 상세로(저장 끝 단계 숫자)", r1.status_code == 303 and loc.startswith("/customer/%d?z157=" % VINA), loc)
with contextlib.redirect_stdout(io.StringIO()):
    dpage = cl.get(loc).text
check("   상세 맨 위 「✓ 4 저장 끝」 + ✅ 하나 · ✕ 닫기", "✓ 4 저장 끝" in dpage and "✅ 고객사 이름을" in dpage and "✕ 닫기" in dpage and "👉" not in dpage.split("z157Done")[1][:1500])
with D.db_session() as c:
    pn = c.execute("SELECT customer_name, customer_id FROM projects WHERE id=?", (PV,)).fetchone()
    cn = c.execute("SELECT customer_name, customer_id FROM consumable_orders WHERE id=?", (COV,)).fetchone()
    pa = c.execute("SELECT customer_name FROM projects WHERE id=?", (PA,)).fetchone()[0]
    tn = c.execute("SELECT customer_name FROM tax_invoices WHERE ti_no='TI-2611-0001'").fetchone()[0]
    ph = c.execute("SELECT COUNT(*) FROM project_history WHERE project_id=? AND field='고객사명' AND new_value='KNK VINA CO LTD'", (PV,)).fetchone()[0]
    ch = c.execute("SELECT COUNT(*) FROM consumable_history WHERE co_id=? AND field='customer_name' AND new_value='KNK VINA CO LTD'", (COV,)).fetchone()[0]
    hh = c.execute("SELECT COUNT(*) FROM customer_history WHERE customer_id=? AND field='고객사명' AND old_value='KNK VINA' AND new_value='KNK VINA CO LTD'", (VINA,)).fetchone()[0]
check("   같은 번호 프로젝트·소모품 저장 이름 = 새 이름 · 번호 그대로", tuple(pn) == ("KNK VINA CO LTD", VINA) and tuple(cn) == ("KNK VINA CO LTD", VINA), (tuple(pn), tuple(cn)))
check("   다른 고객사 시스템명 글자(가상드림(아산))·세금계산서 = 그대로", pa == "가상드림(아산)" and tn == "KNK VINA", (pa, tn))
check("   바뀐 줄마다 이력(프로젝트 1 · 소모품 1) + 고객사 이력 1", ph == 1 and ch == 1 and hh == 1, (ph, ch, hh))
V1 = report_vina()
check("② 이름 바꾼 뒤 VINA 줄 수·금액 같음 · 보고서 이름 = 새 이름", V1[:2] == V0[:2] and V1[2] == ["KNK VINA CO LTD"], (V0, V1))
# 한 번 더 바꿔도(번호 기준)
with contextlib.redirect_stdout(io.StringIO()):
    cl.post("/customers/%d/edit" % VINA, data=dict(base_form, name="가상 베트남 법인", alias="", rename_confirm="1"))
V2 = report_vina()
check("   이름을 VINA 글자가 없는 이름으로 또 바꿔도 VINA 판정 그대로(옛 이름 이력 = 번호)", V2[:2] == V0[:2], (V0, V2))
with D.db_session() as c:
    o2 = D.resolve_customer_by_name(c, "KNK VINA CO LTD")
    o1 = D.resolve_customer_by_name(c, "KNK VINA")
check("   두 번 바꾼 뒤 옛 이름 둘 다(「KNK VINA」·「KNK VINA CO LTD」) 같은 번호로 연결", o1["id"] == VINA and o2["id"] == VINA, (o1, o2))

# ── ④-2 시스템명 = 옛 이름(운영 KNK VINA 64건 같은 경우): 이름 바꾸기 전에 만든 줄만 함께 · 그 뒤 줄(사람이 시스템명으로 적음)은 그대로
with D.db_session() as c:
    c.execute("INSERT INTO customers (name, alias) VALUES ('가상 법인 CO LTD', '가상 법인')")
    AL = c.execute("SELECT MAX(id) FROM customers").fetchone()[0]
    c.execute("INSERT INTO customer_history(customer_id, changed_by, field, old_value, new_value, note, changed_at) VALUES(?,?,?,?,?,?,?)",
              (AL, None, "고객사명", "가상 법인", "가상 법인 CO LTD", "시험", "2026-11-20 11:39:37"))
    for no, ca in (("C-261110-9", "2026-11-10 10:00:00"), ("C-261121-9", "2026-11-21 10:00:00")):
        c.execute("INSERT INTO consumable_orders (co_no, customer_id, customer_name, currency, total_amount, status, order_date, created_at) "
                  "VALUES (?,?,'가상 법인','KRW',1000,'CONFIRMED','2026-11-10',?)", (no, AL, ca))
pv2 = cl.get("/api/customers/%d/rename-preview" % AL, params={"new_name": "가상 법인 COMPANY LIMITED"}).json()
it2 = {x["table"]: x for x in pv2.get("items", [])}
check("④-2 미리보기 — 시스템명과 같은 옛 이름 줄: 이름 변경 전 1건만 함께 · 뒤 1건 그대로", it2.get("consumable_orders", {}).get("change") == 1
      and it2["consumable_orders"]["keep"] == 1, pv2)
with contextlib.redirect_stdout(io.StringIO()):
    cl.post("/customers/%d/edit" % AL, data={"name": "가상 법인 COMPANY LIMITED", "alias": "가상 법인", "is_active": "1", "is_overseas": "1",
                                             "country": "VN", "rename_confirm": "1"})
with D.db_session() as c:
    got = dict(c.execute("SELECT co_no, customer_name FROM consumable_orders WHERE customer_id=?", (AL,)).fetchall())
check("   확인 저장 뒤 — 전 줄 = 새 이름 · 뒤 줄 = 시스템명 그대로", got == {"C-261110-9": "가상 법인 COMPANY LIMITED", "C-261121-9": "가상 법인"}, got)

# ── ⑤ 고객사 엑셀 일괄 등록 — 옛 이름은 새로 안 만듦(확정 쪽 막기)
with D.db_session() as c:
    n0 = c.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
ADMIN["team_id"] = 1   # 고객사 일괄 등록 = 기술영업팀(z1191z102)
with contextlib.redirect_stdout(io.StringIO()):
    rc = cl.post("/customers/import-confirm", json={"rows": [{"row_no": 1, "name": "가상 SAMSUNG VN", "is_active": 1}]})
with D.db_session() as c:
    n1 = c.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
check("⑤ 고객사 일괄 등록에 옛 이름 → 새 고객사 안 만듦(실패 줄로 알림)", n1 == n0 and rc.status_code < 500 and "옛 이름" in rc.text, (rc.status_code, rc.text[:300]))

# ── ⑥ z1191z157b (대표 「항상 기본은 ID번호로 연결 · 1차 고객사만」): 저장 글자를 일부러 옛 이름으로 둔 자료 → 모든 대상 화면이 번호의 지금 이름
import re as _re6
import zipfile as _zf
import html as _html6
with D.db_session() as c:
    c.execute("INSERT INTO customers (name, alias, is_overseas, country) VALUES ('가상 지금회사 CO LTD', '', 1, 'VN')")
    ZC = c.execute("SELECT MAX(id) FROM customers").fetchone()[0]
    c.execute("INSERT INTO customer_history(customer_id, changed_by, field, old_value, new_value, note) VALUES(?,?,?,?,?,?)",
              (ZC, None, "고객사명", "가상 옛회사명", "가상 지금회사 CO LTD", "시험"))
    c.execute("INSERT INTO projects (mgmt_code, name, customer_id, customer_name, secondary_customer, currency, is_export, project_type, stage, status, biz_div, order_date) "
              "VALUES ('903T2611', '가상 옛이름 장비', ?, '가상 옛회사명', '가상 2차옛글자', 'USD', 1, 'NEW_EQUIP', '진행', '진행중', 'T', '2026-11-20')", (ZC,))
    PZ = c.execute("SELECT id FROM projects WHERE mgmt_code='903T2611'").fetchone()[0]
    c.execute("INSERT INTO orders (project_id, order_no, customer_id, currency, total_amount, order_date, status, end_customer) "
              "VALUES (?,?,?,?,?,?,?,?)", (PZ, "T-261120-1", ZC, "USD", 700.0, "2026-11-20", "CONFIRMED", "가상 2차옛글자"))
    OZ = c.execute("SELECT id FROM orders WHERE order_no='T-261120-1'").fetchone()[0]
    c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, currency, unit_label, order_date) VALUES (?,?,?,?,?,?,?)",
              (OZ, 1, 700.0, 700.0, "USD", "1호기", "2026-11-20"))
    c.execute("INSERT INTO consumable_orders (co_no, mgmt_code, customer_id, customer_name, currency, total_amount, status, order_date, biz_div) "
              "VALUES ('C-261120-7', '903C2611', ?, '가상 옛회사명', 'KRW', 1000, 'CONFIRMED', '2026-11-20', 'T')", (ZC,))
    COZ = c.execute("SELECT id FROM consumable_orders WHERE co_no='C-261120-7'").fetchone()[0]
SNAP6 = fp()
pages6 = ["/projects", "/project/%d" % PZ, "/projects/%d/edit" % PZ, "/projects/%d/quick-edit" % PZ, "/sales/orders", "/sales/orders/%d" % OZ,
          "/sales/schedule", "/dept/schedule", "/sales", "/sales/report?basis=order&mode=year&year=2026", "/sales/quotations", "/progress", "/export/prep", "/export/ship/%d" % PZ,
          "/consumables", "/consumables/%d" % COZ, "/projects/export.xlsx", "/sales/quotations/export.xlsx", "/sales/report.xlsx", "/sales/schedule/export.xlsx"]
bad6, now6, codes6 = {}, {}, {}
for path in pages6:
    with contextlib.redirect_stdout(io.StringIO()):
        rr = cl.get(path)
    codes6[path] = rr.status_code
    body = rr.content
    if body[:2] == b"PK":
        z = _zf.ZipFile(io.BytesIO(body))
        t = _html6.unescape(" ".join(z.read(n).decode("utf-8", "replace") for n in z.namelist() if n.endswith(".xml")))   # 엑셀 속 한글은 &#…; 로 적힘
    else:
        t = body.decode("utf-8", "replace")
    olds = [m for m in _re6.finditer("가상 옛회사명", t) if "line-through" not in t[max(0, m.start() - 200):m.start()]]
    if olds:
        bad6[path] = len(olds)
    now6[path] = t.count("가상 지금회사 CO LTD")
check("⑥ 대상 화면 %d곳 열림(500 아님)" % len(pages6), all(v < 500 for v in codes6.values()), codes6)
check("   저장 글자가 옛 이름이어도 대상 화면·엑셀에 옛 이름 안 보임(이력 줄 제외)", not bad6, bad6)
must = ["/projects", "/project/%d" % PZ, "/projects/%d/edit" % PZ, "/sales/schedule", "/dept/schedule", "/sales/quotations", "/export/prep",
        "/export/ship/%d" % PZ, "/consumables", "/projects/export.xlsx", "/sales/report?basis=order&mode=year&year=2026"]
check("   번호의 지금 이름이 보임(목록·상세·정보 수정·일정표·전사일정표·견적·수출·소모품·엑셀·보고서)", all(now6.get(x, 0) > 0 for x in must),
      {x: now6.get(x) for x in must})
check("   2차 고객 글자는 그대로(번호로 안 바꿈)", "가상 2차옛글자" in cl.get("/project/%d" % PZ).text)
check("   화면 %d곳 열기만으로 DB 그대로" % len(pages6), fp() == SNAP6)
with D.db_session() as c:
    st = c.execute("SELECT customer_name FROM projects WHERE id=?", (PZ,)).fetchone()[0]
check("   DB 저장 글자는 그대로(옛 이름 · 읽기만)", st == "가상 옛회사명", st)
row = {"customer_id": ZC, "customer_name": "가상 옛회사명", "ti_no": "TI-1"}
with D.db_session() as c:
    D.fix_customer_names_in(c, [row])
check("   발행 서류 줄(ti_no)은 그때 이름 그대로", row["customer_name"] == "가상 옛회사명")

print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
