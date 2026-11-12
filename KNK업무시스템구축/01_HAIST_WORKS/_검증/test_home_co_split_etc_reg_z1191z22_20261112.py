# -*- coding: utf-8 -*-
"""z1191z22 시험 (이새롬 프로 요청 · 대표 「진행해」 2026-11-12)
  ① 매출 홈 사업부별 매출: 소모품 → 소모품(검사기) · 소모품(자동화) (매출 보고서와 같은 규칙) · 세 지표 · 합계 그대로 · 소모품(기타)는 있을 때만
  ② 신규 등록 「기타」 탭(사업부 E): 등록됨(관리번호 NNN E YYMM · 수주번호 E-) · 예전엔 「사업부를 선택하세요」로 막혀 검사기 화면으로 넘어감
  ③ 등록 화면에서 고른 형태 → 그 수주 so_form(작업일정표 「형태」·보고서 구분) · 추가 품목 수주는 건드리지 않음
  ④ 추가 발주(기존 관리번호)도 고른 형태 → 새 수주 so_form (M-260909-1 셋업비 사례)
  ⑤ 입력이 빠져 되돌아갈 때 보던 탭(biz_div)을 지킴
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z22-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z22_")
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
              "VALUES ('가상관리자', 'admin', 'T924', 'T924', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T924'").fetchone())
    CU = ins(c, "customers", {"name": "엘지전자", "alias": "엘지전자"})
    c.execute("INSERT OR REPLACE INTO exchange_rates (from_currency, to_currency, rate, rate_date, source) VALUES ('USD','KRW',1400,'2026-05-01','월기준')")
    # 소모품: 검사기 2건(KRW) · 자동화 1건(USD) · 사업부 빈칸 1건 — 수주·출하·계산서 모두 5월
    for no, bd, ccy, amt in (("C-1", "T", "KRW", 500000), ("C-2", "T", "KRW", 300000), ("C-3", "M", "USD", 100), ("C-4", "", "KRW", 70000)):
        ins(c, "consumable_orders", {"co_no": no, "mgmt_code": "00%sC2605" % no[-1], "customer_name": "엘지전자", "customer_id": CU, "currency": ccy,
                                     "total_amount": amt, "status": "SHIPPED", "biz_div": bd, "order_date": "2026-05-02", "due_date": "2026-05-10",
                                     "status_date": "2026-05-10", "tax_invoice_date": "2026-05-20", "tax_invoice_amt1": amt})

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


def s3(m="5"):
    oi_map, _ = q(M._board_tax_oi_map)
    with D.db_session() as c:
        rates = M._fx_load_rates(c)
        return M._sales_3way(c, rates, oi_map, "month", "2026", "2", m)


print("§1 매출 홈 소모품 나누기")
S = s3()
B = {b["biz"]: b for b in S["biz_rows"]}
check([b["biz"] for b in S["biz_rows"]] == ["T", "M", "L", "E", "CT", "CM", "CE"], "줄 순서: 검사기·자동화·라이프밸류·기타·소모품(검사기)·소모품(자동화)·소모품(기타)", list(B))
check("C" not in B and B["CT"]["label"].endswith("소모품(검사기)") and B["CM"]["label"].endswith("소모품(자동화)"), "「소모품」 한 줄 대신 소모품(검사기)·소모품(자동화)")
for k in ("order", "prog", "final"):
    check(abs(B["CT"][k] - 800000) < 1 and abs(B["CM"][k] - 140000) < 1 and abs(B["CE"][k] - 70000) < 1,
          "%s: 검사기 800,000 · 자동화 140,000(USD 100) · 사업부 빈칸 70,000 = 소모품(기타)" % k, (B["CT"][k], B["CM"][k], B["CE"][k]))
    check(abs(sum(b[k] for b in S["biz_rows"]) - S["kpi"][k]) < 1, "%s: 사업부 줄 합 = 합계" % k)
with D.db_session() as c:
    c.execute("UPDATE consumable_orders SET biz_div='M' WHERE co_no='C-4'")
S2 = s3()
check("CE" not in [b["biz"] for b in S2["biz_rows"]], "사업부 빈칸 소모품이 없으면 소모품(기타) 줄을 감춤", [b["biz"] for b in S2["biz_rows"]])
with D.db_session() as c:
    rates = M._fx_load_rates(c)
    oi_map, _ = q(M._board_tax_oi_map)
    R = M._sales_report_z17(c, rates, oi_map, "tax", "month", "2026", "2", "5")
RB = {b["key"]: b["total"] for b in R["biz_rows"]}
B2 = {b["biz"]: b for b in S2["biz_rows"]}
check(abs(RB.get("CT", 0) - B2["CT"]["final"]) < 1 and abs(RB.get("CM", 0) - B2["CM"]["final"]) < 1, "매출 홈 최종매출 = 매출 보고서(세금계산서) 소모품(검사기)·소모품(자동화)", (RB, B2["CT"]["final"], B2["CM"]["final"]))
h = q(cl.get, "/sales?mode=month&year=2026&m=5")
check(h.status_code == 200 and "소모품(검사기)" in h.text and "소모품(자동화)" in h.text, "매출 홈 화면 200 · 두 줄 보임", h.status_code)

print("§2 신규 등록 「기타」(사진과 같은 값)")
BASE = {"quick": "1", "biz_div": "E", "project_type": "OTHER", "customer_name": "엘지전자", "po_type": "신규", "shipment_form": "ETC", "is_export": "0",
        "name": "기타", "model": "P9 NY F-RING 101 디스펜서 RPM", "equip_name": "P9 NY F-RING 101 디스펜서 RPM", "unit_qty": "1", "currency": "KRW",
        "unit_price": "9900000", "order_amount": "9900000", "order_date": "2026-11-12", "due_date": "2026-11-30", "status": "진행중", "confirm_now": "1",
        "unit_label[]": "", "unit_amount[]": "9900000", "unit_due[]": "2026-11-30", "unit_ship[]": "", "unit_currency[]": "KRW"}
r = q(cl.post, "/projects/new", data=BASE)
loc = r.headers.get("location", "")
check(r.status_code == 303 and loc.startswith("/project/"), "등록됨 → 프로젝트 상세로(예전엔 /projects/quick?error=biz_div_required)", loc)
with D.db_session() as c:
    P = c.execute("SELECT id, mgmt_code, biz_div, project_type, shipment_form FROM projects ORDER BY id DESC LIMIT 1").fetchone()
    O = c.execute("SELECT id, order_no, so_form, total_amount FROM orders WHERE project_id=?", (P[0],)).fetchall()
    I = c.execute("SELECT unit_label, amount FROM order_items WHERE order_id=?", (O[0][0],)).fetchall() if O else []
check(re.match(r"^\d{3}E\d{4}$", P[1] or "") and P[2] == "E" and P[3] == "OTHER", "관리번호 NNN E YYMM · 사업부 E · 유형 기타", tuple(P))
check(len(O) == 1 and O[0][1].startswith("E-") and O[0][2] == "ETC" and abs(O[0][3] - 9900000) < 1, "수주번호 E-… · 형태(so_form) = 기타 · 9,900,000", O)
check(I and abs(sum(a for _, a in I) - 9900000) < 1, "품목 줄 금액 9,900,000(매출에 잡힘)", I)
S3 = s3("11")
B3 = {b["biz"]: b for b in S3["biz_rows"]}
check(abs(B3["E"]["order"] - 9900000) < 1, "매출 홈 2026-11 수주매출 「기타」 줄 = 9,900,000", B3["E"]["order"])
bd = q(cl.get, "/sales/schedule?ym=2026-11").text
row = re.search(r'<tr[^>]*data-soid="%d"[^>]*>(.*?)</tr>' % O[0][0], bd, re.S)
ft = re.search(r'data-edit="form_type">([^<]*)<', row.group(1)) if row else None
check(ft and ft.group(1).strip() == "기타", "작업일정표 형태 칸 = 「기타」(예전엔 기본 규칙 「제품」)", ft and ft.group(1))

print("§3 검사기 탭 · 형태 완제품/기타도 저장")
for sf, want, lbl in (("ASSEMBLY", "ASSEMBLY", "완제품"), ("ETC", "ETC", "기타")):
    f = dict(BASE, biz_div="T", project_type="NEW_EQUIP", shipment_form=sf, name="검사기-" + sf)
    r = q(cl.post, "/projects/new", data=f)
    with D.db_session() as c:
        pid = c.execute("SELECT id FROM projects WHERE name=?", ("검사기-" + sf,)).fetchone()[0]
        fs = [x[0] for x in c.execute("SELECT so_form FROM orders WHERE project_id=?", (pid,))]
    check(r.status_code == 303 and fs == [want], "검사기 · 형태 %s → so_form %s" % (lbl, want), (r.headers.get("location"), fs))

print("§4 추가 발주 · 형태 기타 → 새 수주 so_form")
with D.db_session() as c:
    mg = c.execute("SELECT mgmt_code FROM projects WHERE name='검사기-ASSEMBLY'").fetchone()[0]
f = dict(BASE, biz_div="T", project_type="NEW_EQUIP", shipment_form="ETC", po_type="기타", name="셋업비", mgmt_code=mg, model="셋업비", equip_name="셋업비")
r = q(cl.post, "/projects/new", data=f)
with D.db_session() as c:
    pid = c.execute("SELECT id FROM projects WHERE mgmt_code=?", (mg,)).fetchone()[0]
    fs = [tuple(x) for x in c.execute("SELECT order_no, so_form FROM orders WHERE project_id=? ORDER BY id", (pid,))]
check(r.status_code == 303 and len(fs) == 2 and fs[0][1] == "ASSEMBLY" and fs[1][1] == "ETC", "추가 발주: 첫 수주 완제품 그대로 · 새 수주 형태 기타", (r.headers.get("location"), fs))

print("§5 입력이 빠지면 보던 탭으로")
for bdv in ("E", "M"):
    r = q(cl.post, "/projects/new", data=dict(BASE, biz_div=bdv, customer_name=""))
    loc = r.headers.get("location", "")
    check(r.status_code == 303 and "error=customer_required" in loc and ("biz_div=%s" % bdv) in loc, "고객사 빈칸(%s 탭) → 같은 탭으로 되돌아감" % bdv, loc)
    g = q(cl.get, loc)
    check(g.status_code == 200 and ('id="qBizDiv" value="%s"' % bdv) in g.text, "되돌아간 화면 = %s 탭" % bdv, g.status_code)
r = q(cl.post, "/projects/new", data=dict(BASE, biz_div="X"))
check("error=biz_div_required" in r.headers.get("location", "") and "biz_div=X" not in r.headers.get("location", ""), "엉뚱한 사업부(X)는 지금처럼 막음", r.headers.get("location"))

print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
