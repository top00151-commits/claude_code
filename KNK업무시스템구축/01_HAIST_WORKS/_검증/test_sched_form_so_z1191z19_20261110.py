# -*- coding: utf-8 -*-
"""z1191z19 시험 — 작업일정표 「형태」 칸 = 그 줄 수주의 형태(so_form) (이새롬 프로 신고 · 대표 「1~4 진행」 2026-11-10)
  신고: 삼성전기 M-260909-1(셋업비 1식) 형태를 「기타」로 바꾸면 계속 「제품」으로 돌아감
  원인: 화면은 수주 형태(so_form_label_key)를 보이는데 칸을 고치면 프로젝트 형태가 바뀜(z1033 PO유형과 같은 병)
  ① 한 칸 저장: 수주 줄이면 그 수주 so_form · 같은 관리번호 다른 수주·프로젝트 대표값은 그대로 · 이력 · 해제 = 기본 규칙
  ② 다시 그린 작업일정표 = 고른 값(헛돌지 않음)  ③ 일괄 수정도 같은 규칙 + 줄 표시 값
  ④ 막기: 다른 관리번호 수주 · 엉뚱한 값 · 권한  ⑤ 수주 없는 줄은 지금처럼 프로젝트  ⑥ 매출 보고서 구분도 따라감
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z19-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z19_")
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
              "VALUES ('가상관리자', 'admin', 'T919', 'T919', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T919'").fetchone())
    CU = ins(c, "customers", {"name": "가상전기(주)", "alias": "가상전기"})
    # 관리번호 006M2507 같은 모양: 첫 수주 = 완제품(1호기) · 추가 수주 = 셋업비 1식(형태 비어 있음 → 기본 규칙 「제품」)
    P = ins(c, "projects", {"code": "006M2507", "name": "컴포넌트", "mgmt_code": "006M2507", "customer_id": CU, "customer_name": "가상전기(주)",
                            "currency": "KRW", "status": "진행중", "stage": "진행중", "biz_div": "M", "project_type": "NEW_EQUIP",
                            "shipment_form": "ASSEMBLY", "form_type": "완제품", "order_date": "2026-09-01", "due_date": "2026-09-25", "is_archived": 0})
    A = ins(c, "orders", {"project_id": P, "order_no": "M-260310-1", "customer_id": CU, "so_type": "EQUIPMENT", "so_form": "ASSEMBLY",
                          "currency": "KRW", "status": "CONFIRMED", "order_date": "2026-09-01", "due_date": "2026-09-20", "total_amount": 230000000})
    ins(c, "order_items", {"order_id": A, "unit_label": "1호기", "qty": 1, "amount": 230000000, "unit_status": "진행중"})
    B = ins(c, "orders", {"project_id": P, "order_no": "M-260909-1", "customer_id": CU, "so_type": "EQUIPMENT", "so_form": None, "po_type": "기타",
                          "currency": "KRW", "status": "SHIPPED", "order_date": "2026-09-09", "due_date": "2026-09-25", "total_amount": 15000000})
    ins(c, "order_items", {"order_id": B, "unit_label": "셋업비", "qty": 1, "amount": 15000000, "unit_status": "출하",
                           "tax_invoice_date": "2026-09-26", "tax_invoice_amt1": 15000000})
    # 다른 관리번호(막기 시험용)
    P2 = ins(c, "projects", {"code": "007M2509", "name": "다른것", "mgmt_code": "007M2509", "customer_id": CU, "customer_name": "가상전기(주)",
                             "currency": "KRW", "status": "진행중", "biz_div": "M", "project_type": "NEW_EQUIP", "shipment_form": "ASSEMBLY",
                             "order_date": "2026-09-02", "due_date": "2026-09-22", "is_archived": 0})
    O2 = ins(c, "orders", {"project_id": P2, "order_no": "M-260902-1", "customer_id": CU, "so_type": "EQUIPMENT", "currency": "KRW",
                           "status": "CONFIRMED", "order_date": "2026-09-02", "due_date": "2026-09-22", "total_amount": 1000})
    ins(c, "order_items", {"order_id": O2, "unit_label": "1호기", "qty": 1, "amount": 1000, "unit_status": "진행중"})
    # 수주 없는 관리번호(지금처럼 프로젝트를 고친다)
    P3 = ins(c, "projects", {"code": "008M2509", "name": "수주없음", "customer_id": CU, "customer_name": "가상전기(주)", "currency": "KRW",
                             "status": "진행중", "biz_div": "M", "project_type": "NEW_EQUIP", "shipment_form": "ASSEMBLY", "form_type": "완제품",
                             "order_date": "2026-09-03", "due_date": "2026-09-23", "is_archived": 0})

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


def so_form(oid):
    with D.db_session() as c:
        return c.execute("SELECT so_form FROM orders WHERE id=?", (oid,)).fetchone()[0]


def proj_form(pid):
    with D.db_session() as c:
        r = c.execute("SELECT form_type, shipment_form FROM projects WHERE id=?", (pid,)).fetchone()
        return (r[0], r[1])


def board_forms():
    """작업일정표(2026-09)를 그려 수주 줄마다 형태 칸 글자."""
    h = q(cl.get, "/sales/schedule?ym=2026-09").text
    out = {}
    for m in re.finditer(r'<tr[^>]*data-soid="(\d+)"[^>]*>(.*?)</tr>', h, re.S):
        td = re.search(r'data-edit="form_type">([^<]*)</td>', m.group(2))
        if td:
            out[int(m.group(1))] = td.group(1).strip()
    return out, h


def cell(value, so_oid, ref=None, field="form_type"):
    return q(cl.post, "/sales/schedule/cell", json={"kind": "project", "ref_id": ref or P, "field": field, "value": value, "so_oid": str(so_oid) if so_oid else ""})


print("§0 고치기 전 모양(신고와 같음)")
F0, H0 = board_forms()
check(F0.get(B) == "제품" and F0.get(A) == "완제품", "셋업비 수주 = 「제품」(기본 규칙) · 첫 수주 = 「완제품」", F0)
check("z1191z19" in H0 and "j.so_values" in H0, "작업일정표 화면에 z1191z19 표시 규칙(한 칸·일괄)")

print("§1 한 칸 저장 = 그 수주")
r = cell("기타", B)
j = r.json()
check(r.status_code == 200 and j.get("ok") and j.get("scope") == "so" and j.get("value") == "기타", "「기타」 저장 → 수주에 · 표시 값 「기타」", j)
check(so_form(B) == "ETC", "M-260909-1 so_form = ETC", so_form(B))
check(so_form(A) == "ASSEMBLY", "같은 관리번호 다른 수주(M-260310-1)는 그대로 ASSEMBLY", so_form(A))
check(proj_form(P) == ("완제품", "ASSEMBLY"), "프로젝트 대표 형태는 그대로(완제품)", proj_form(P))
with D.db_session() as c:
    hist = [x[0] for x in c.execute("SELECT note FROM order_status_history WHERE order_id=? ORDER BY id", (B,))]
check(any("형태 변경: 제품 → 기타" in (x or "") and "작업일정표" in (x or "") for x in hist), "변경 이력 「형태 변경: 제품 → 기타 (작업일정표)」", hist)

print("§2 다시 그린 작업일정표 = 고른 값(헛돌지 않음)")
F1, _ = board_forms()
check(F1.get(B) == "기타" and F1.get(A) == "완제품", "새로 그려도 M-260909-1 = 「기타」 · M-260310-1 = 「완제품」", F1)
pd = q(cl.get, "/project/%d?so=M-260909-1" % P)
check(pd.status_code == 200 and "기타" in pd.text, "프로젝트 상세(그 수주 기준)도 200 · 「기타」 글자", pd.status_code)

print("§3 해제 = 기본 규칙 · 다른 값")
j = cell("", B).json()
check(j.get("ok") and so_form(B) is None and j.get("value") == "제품", "(해제) → so_form 비움 · 표시 「제품」(호기 없음 기본 규칙)", (j, so_form(B)))
j = cell("상품", B).json()
check(j.get("ok") and so_form(B) == "PARTS" and j.get("value") == "상품", "「상품」 → PARTS", so_form(B))
j = cell("완제품", B).json()
check(j.get("ok") and so_form(B) == "ASSEMBLY" and board_forms()[0].get(B) == "완제품", "「완제품」 → ASSEMBLY · 화면도", so_form(B))

print("§4 막기")
r = cell("엉터리", B)
check(r.status_code == 400 and so_form(B) == "ASSEMBLY", "엉뚱한 값은 400 · 그대로", (r.status_code, so_form(B)))
r = cell("기타", O2, ref=P)   # 다른 관리번호의 수주를 이 관리번호 줄로
check(r.status_code == 400 and so_form(O2) is None, "다른 관리번호의 수주는 400 · 그대로", (r.status_code, so_form(O2)))

print("§5 일괄 수정도 같은 규칙")
rb = q(cl.post, "/sales/schedule/bulk-cell", json={"field": "form_type", "value": "기타", "targets": [
    {"kind": "project", "ref_id": P, "so_oid": str(B), "uids": ""}]})
jb = rb.json()
check(jb.get("ok_count") == 1 and so_form(B) == "ETC" and so_form(A) == "ASSEMBLY" and proj_form(P) == ("완제품", "ASSEMBLY"),
      "일괄 「기타」 → 그 수주만 ETC · 다른 수주·프로젝트 그대로", (jb, so_form(B), proj_form(P)))
check((jb.get("so_values") or {}).get("project:%d:%d" % (P, B)) == "기타", "일괄 응답에 줄 표시 값", jb.get("so_values"))
jb2 = q(cl.post, "/sales/schedule/bulk-cell", json={"field": "form_type", "value": "", "targets": [
    {"kind": "project", "ref_id": P, "so_oid": str(B), "uids": ""}]}).json()
check(so_form(B) is None and (jb2.get("so_values") or {}).get("project:%d:%d" % (P, B)) == "제품", "일괄 해제 → 기본 규칙 「제품」 표시 값", jb2.get("so_values"))
q(cl.post, "/sales/schedule/bulk-cell", json={"field": "form_type", "value": "기타", "targets": [{"kind": "project", "ref_id": P, "so_oid": str(B), "uids": ""}]})

print("§6 수주 없는 줄은 지금처럼 프로젝트")
r = cell("기타", None, ref=P3)
check(r.json().get("ok") and proj_form(P3)[0] == "기타", "수주 없는 관리번호 → 프로젝트 형태 「기타」", proj_form(P3))

print("§7 매출 보고서 구분도 따라감")
oi_map, _ = q(M._board_tax_oi_map)
with D.db_session() as c:
    rates = M._fx_load_rates(c)
    R = M._sales_report_z17(c, rates, oi_map, "tax", "month", "2026", "3", "9")
ln = [x for x in R["lines"] if x["so"] == "M-260909-1"]
check(ln and ln[0]["cat"] == "기타" and abs(ln[0]["krw"] - 15000000) < 1, "M-260909-1 1,500만 원 = 「기타」 구분", ln and (ln[0]["cat"], ln[0]["krw"]))

print("§8 권한")
with D.db_session() as c:
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales) "
              "VALUES ('가상일반', 'member', 'T920', 'T920', 'sso_only_no_local_password', 1, 1, 0, 0)")
    MEM = dict(c.execute("SELECT * FROM users WHERE employee_no='T920'").fetchone())
M.get_user = lambda request: MEM
r = cell("제품", B)
check(r.status_code == 403 and so_form(B) == "ETC", "매출 등록 권한 없으면 403 · 그대로", (r.status_code, so_form(B)))

print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
