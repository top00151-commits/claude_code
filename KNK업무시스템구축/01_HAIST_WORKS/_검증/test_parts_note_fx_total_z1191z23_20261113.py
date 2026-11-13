# -*- coding: utf-8 -*-
"""z1191z23 시험 — 이새롬 프로 요청(대표 「진행해」 2026-11-13)
  ① 작업일정표 상품 수주 줄 「기타사항」: 「[상품 일괄등록]」이 지워지지 않음
     원인 = 표시는 프로젝트 메모(logi_note) · 저장은 그 수주 부품 비고 전부 덮어쓰기(표시 ≠ 저장 · 부품 비고 날아갈 위험)
     고침 = 상품 수주 기타사항은 수주 메모(orders.unit_note) — NULL(안 적음) = 지금처럼 프로젝트 메모 · '' = 지움 · 부품 비고 그대로
            · 이력에 무엇을 고쳤는지 · 상품 일괄등록이 「[상품 일괄등록]」을 적지 않음
  ③ 매출 보고서 「합계(원)」 옆 「합계(외화)」(고객사별 · KNK VINA 2차 · 프로젝트별 + 합계 줄)
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z23-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z23_")
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
              "VALUES ('가상관리자', 'admin', 'T923', 'T923', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T923'").fetchone())
    CU = ins(c, "customers", {"name": "가상엔지니어링", "alias": "가상엔지"})
    # 007M2511 같은 모양: 상품 일괄등록 프로젝트(메모 「[상품 일괄등록]」) · 상품 수주 1건 · 부품 비고 따로
    P = ins(c, "projects", {"code": "907M2511", "name": "BIM LINE", "mgmt_code": "907M2511", "customer_id": CU, "customer_name": "가상엔지니어링",
                            "currency": "USD", "status": "진행중", "biz_div": "M", "project_type": "NEW_EQUIP", "shipment_form": "PARTS",
                            "logi_note": "[상품 일괄등록]", "order_date": "2026-09-01", "due_date": "2026-09-25", "is_archived": 0})
    A = ins(c, "orders", {"project_id": P, "order_no": "M-260901-7", "customer_id": CU, "so_type": "PARTS_EXPORT", "currency": "USD",
                          "status": "CONFIRMED", "order_date": "2026-09-01", "due_date": "2026-09-20", "total_amount": 300, "unit_qty": 1})
    I1 = ins(c, "order_items", {"order_id": A, "unit_label": "CYLINDER", "qty": 1, "amount": 100, "line_note": "부품비고-가", "unit_status": "진행중"})
    I2 = ins(c, "order_items", {"order_id": A, "unit_label": "O-RING", "qty": 2, "amount": 200, "line_note": "부품비고-나", "unit_status": "진행중"})
    # 비교: 장비 수주(호기 비고 = 기타사항 · 지금처럼)
    P2 = ins(c, "projects", {"code": "908M2511", "name": "장비", "mgmt_code": "908M2511", "customer_id": CU, "customer_name": "가상엔지니어링",
                             "currency": "KRW", "status": "진행중", "biz_div": "M", "project_type": "NEW_EQUIP", "shipment_form": "ASSEMBLY",
                             "order_date": "2026-09-02", "due_date": "2026-09-22", "is_archived": 0})
    B = ins(c, "orders", {"project_id": P2, "order_no": "M-260902-7", "customer_id": CU, "so_type": "EQUIPMENT", "currency": "KRW",
                          "status": "CONFIRMED", "order_date": "2026-09-02", "due_date": "2026-09-22", "total_amount": 1000})
    J1 = ins(c, "order_items", {"order_id": B, "unit_label": "1호기", "qty": 1, "amount": 1000, "unit_status": "진행중"})

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


def board_notes():
    h = q(cl.get, "/sales/schedule?ym=2026-09").text
    out = {}
    for m in re.finditer(r'<tr[^>]*data-soid="(\d+)"[^>]*>(.*?)</tr>', h, re.S):
        td = re.search(r'data-edit="note"[^>]*>([^<]*)</td>', m.group(2))
        if td:
            out[int(m.group(1))] = td.group(1).strip()
    return out


def quick(oid, **form):
    return q(cl.post, "/sales/orders/%d/quick-edit" % oid, data=form)


def db1(sql, *a):
    with D.db_session() as c:
        return c.execute(sql, a).fetchone()


print("§1 고치기 전 모양(신고와 같음)")
N0 = board_notes()
check(N0.get(A) == "[상품 일괄등록]", "상품 수주 줄 기타사항 = 「[상품 일괄등록]」(프로젝트 메모 · 수주 메모 안 적음)", N0)

print("§2 지우기 — 수주 메모에 '' · 부품 비고 그대로 · 화면 빈칸")
r = quick(A, line_note="")
check(r.status_code == 200 and r.json().get("ok"), "저장 응답 ok", r.text[:200])
check(db1("SELECT unit_note FROM orders WHERE id=?", A)[0] == "", "수주 메모 = ''(지움)", db1("SELECT unit_note FROM orders WHERE id=?", A))
check(db1("SELECT line_note FROM order_items WHERE id=?", I1)[0] == "부품비고-가" and db1("SELECT line_note FROM order_items WHERE id=?", I2)[0] == "부품비고-나",
      "부품 비고 2줄 그대로(덮어쓰지 않음)")
N1 = board_notes()
check(N1.get(A) in ("＋", ""), "다시 그린 작업일정표 = 빈칸(＋) — 「[상품 일괄등록]」 안 돌아옴", N1.get(A))
check(db1("SELECT logi_note FROM projects WHERE id=?", P)[0] == "[상품 일괄등록]", "프로젝트 메모는 건드리지 않음(데이터 정리는 따로)")
h = db1("SELECT note FROM order_status_history WHERE order_id=? ORDER BY id DESC LIMIT 1", A)[0]
check("기타사항→(지움)" in h and "수주 메모" in h, "이력에 「기타사항→(지움) (수주 메모)」(예전엔 「인라인 수정: 」 빈 글)", h)

print("§3 적기 — 그 글이 보임")
quick(A, line_note="11/20 선적 예정")
check(db1("SELECT unit_note FROM orders WHERE id=?", A)[0] == "11/20 선적 예정", "수주 메모 = 적은 글")
check(board_notes().get(A) == "11/20 선적 예정", "작업일정표 기타사항 = 적은 글")
check(db1("SELECT line_note FROM order_items WHERE id=?", I1)[0] == "부품비고-가", "부품 비고 여전히 그대로")

print("§4 수주 메모 NULL 이면 지금처럼 프로젝트 메모(다른 상품 프로젝트 메모 「4대」 같은 것 그대로 보임)")
with D.db_session() as c:
    c.execute("UPDATE orders SET unit_note=NULL WHERE id=?", (A,))
    c.execute("UPDATE projects SET logi_note='4대' WHERE id=?", (P,))
check(board_notes().get(A) == "4대", "unit_note NULL → 프로젝트 메모 「4대」")

print("§5 장비 수주 줄은 지금처럼(호기 비고에 저장)")
quick(B, line_note="장비 메모")
check(db1("SELECT line_note FROM order_items WHERE id=?", J1)[0] == "장비 메모" and db1("SELECT unit_note FROM orders WHERE id=?", B)[0] is None,
      "장비 수주: 호기 비고 = 적은 글 · 수주 메모 안 씀")
check(board_notes().get(B) == "장비 메모", "작업일정표 장비 줄 기타사항 = 적은 글")
quick(B, model_name="NEW-MODEL")
h2 = db1("SELECT note FROM order_status_history WHERE order_id=? ORDER BY id DESC LIMIT 1", B)[0]
check("모델명→NEW-MODEL" in h2, "모델명 고치면 이력에 「모델명→NEW-MODEL」", h2)

print("§6 상품 일괄등록이 「[상품 일괄등록]」을 비고에 적지 않음")
src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check('"note": "[상품 일괄등록]"' not in src and '"note": "",   # z1191z23' in src, "등록 코드에 표시 글 없음")

print("§7 합계(외화) — 글 모양")
check(M._z23_fx_txt({"USD": 24180.5}) == "USD 24,180.50", "USD 24,180.50", M._z23_fx_txt({"USD": 24180.5}))
check(M._z23_fx_txt({"VND": 1234567.4, "USD": 10}) == "VND 1,234,567 · USD 10.00", "여러 통화 = 큰 금액 먼저 · VND 소수 없음", M._z23_fx_txt({"VND": 1234567.4, "USD": 10}))
check(M._z23_fx_txt({}) == "" and M._z23_fx_txt(None) == "", "외화 없으면 빈 글")

print("§8 매출 보고서 표 — 고객사별 · KNK VINA 2차 · 프로젝트별 · 합계 줄")
LINES = [
    {"date": "2026-09-10", "krw": 1400000.0, "amt": 1000.0, "ccy": "USD", "biz": "M", "cat": "상품", "cust": "KNK VINA", "cust2": "SEV", "is_vina": True,
     "code": "001M2509", "kind": "project", "pname": "가", "pid": 1, "so": "M-1", "label": "", "model": "", "nth": ""},
    {"date": "2026-09-11", "krw": 700000.0, "amt": 500.0, "ccy": "USD", "biz": "M", "cat": "상품", "cust": "KNK VINA", "cust2": "SEVT", "is_vina": True,
     "code": "001M2509", "kind": "project", "pname": "가", "pid": 1, "so": "M-1", "label": "", "model": "", "nth": ""},
    {"date": "2026-09-12", "krw": 5000000.0, "amt": 5000000.0, "ccy": "KRW", "biz": "T", "cat": "장비", "cust": "드림텍", "cust2": "", "is_vina": False,
     "code": "002T2509", "kind": "project", "pname": "나", "pid": 2, "so": "T-1", "label": "", "model": "", "nth": ""},
    {"date": "2026-09-13", "krw": 110000.0, "amt": 2000000.0, "ccy": "VND", "biz": "T", "cat": "장비", "cust": "드림텍", "cust2": "", "is_vina": False,
     "code": "002T2509", "kind": "project", "pname": "나", "pid": 2, "so": "T-2", "label": "", "model": "", "nth": ""},
]
_orig = M._z17_lines
M._z17_lines = lambda c, rates, oi_map, basis: ([dict(x) for x in LINES], set(), {})
with D.db_session() as c:
    R = M._sales_report_z17(c, {}, {}, "tax", "month", "2026", "3", "9")
cu = {a["name"]: a["fx_txt"] for a in R["cust_rows"]}
check(cu == {"KNK VINA": "USD 1,500.00", "드림텍": "VND 2,000,000"}, "고객사별 합계(외화): KNK VINA USD 1,500.00 · 드림텍 VND 2,000,000(원화 줄은 빼고)", cu)
vi = {a["name"]: a["fx_txt"] for a in R["vina_rows"]}
check(vi == {"SEV": "USD 1,000.00", "SEVT": "USD 500.00"} and R["fx_vina_txt"] == "USD 1,500.00", "KNK VINA 2차별 · 합계 줄", (vi, R["fx_vina_txt"]))
pr = {a["code"]: a["fx_txt"] for a in R["proj_rows"]}
check(pr == {"001M2509": "USD 1,500.00", "002T2509": "VND 2,000,000"} and R["fx_total_txt"] == "VND 2,000,000 · USD 1,500.00",
      "프로젝트별 · 전체 합계 줄(통화 섞임)", (pr, R["fx_total_txt"]))
check(abs(R["total"] - 7210000) < 1 and R["checks_ok"], "합계(원)·맞춤은 그대로", (R["total"], R["checks"]))
h = q(cl.get, "/sales/report?basis=tax&mode=month&year=2026&m=9").text
M._z17_lines = _orig
check(h.count("합계(외화)") >= 3, "화면 머리줄 「합계(외화)」 3곳(고객사별·KNK VINA·프로젝트별)", h.count("합계(외화)"))
check("USD 1,500.00" in h and "VND 2,000,000" in h and "VND 2,000,000 · USD 1,500.00" in h, "화면에 외화 합계 글")

print()
print("결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
