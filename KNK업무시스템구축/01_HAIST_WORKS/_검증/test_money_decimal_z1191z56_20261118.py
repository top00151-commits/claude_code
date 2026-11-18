# -*- coding: utf-8 -*-
"""z1191z56 시험 (대표 2026-11-18 「달러 소수점 — 우선 지금까지 저장된 값은 그대로 적용하고」 + 세 규칙 고름)
  ① 점·쉼표 바꿔 친 숫자(「13.224,61」) = 저장 안 함 · 바로잡을 값 안내 — 작업일정표 호기 칸·세금계산서(줄·호기)·프로젝트 칸 · 프로젝트 상세 호기 줄 수정·호기 추가 · 소모품 라인
  ② 새로 저장하는 금액 = 둘째 자리 엑셀식 반올림(2,806.659 → 2,806.66)
  ③ 단가 표시 = 엑셀식 반올림(41.355 → 41.36) · 저장값은 그대로
  ④ 지금까지 저장된 값은 그대로(셋째 자리 금액 줄을 읽기만 해서는 안 바뀜)
  ⑤ 화면: 공용 틀에 바로잡기 스크립트 · 한국어·베트남어 글 · 금액 꾸미개가 쉼표를 지우지 않음
  임시 DB · TestClient · 운영 아님
"""
import contextlib, io, os, re, sys, tempfile
from datetime import date, timedelta
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z56-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z56_")
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


FUT = (date.today() + timedelta(days=14)).isoformat()
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0"), ("biz_divs", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상관리자', 'admin', 'T956', 'T956', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T956'").fetchone())
    CU = ins(c, "customers", {"name": "가상해외(주)"})
    P = ins(c, "projects", {"code": "050T2611", "name": "PBA", "mgmt_code": "050T2611", "customer_id": CU, "customer_name": "가상해외(주)", "currency": "USD",
                            "status": "수주확정", "biz_div": "T", "project_type": "NEW_EQUIP", "shipment_form": "ASSEMBLY", "order_date": "2026-11-13", "due_date": FUT,
                            "is_archived": 0, "unit_qty": 3, "order_amount": 0})
    O = ins(c, "orders", {"order_no": "T-261118-1", "customer_id": CU, "order_date": "2026-11-18", "due_date": FUT, "total_amount": 0, "status": "CONFIRMED",
                          "project_id": P, "unit_label": "1호기", "unit_qty": 3, "currency": "USD", "so_type": "EQUIPMENT", "po_type": "신규"})
    I1 = ins(c, "order_items", {"order_id": O, "qty": 1, "unit_price": 1000, "amount": 1000})
    I2 = ins(c, "order_items", {"order_id": O, "qty": 1, "unit_price": 1000, "amount": 1000})
    I3 = ins(c, "order_items", {"order_id": O, "qty": 3, "unit_price": 935.553, "amount": 2806.659})   # 지금까지 저장된 셋째 자리 금액
    P2 = ins(c, "projects", {"code": "051T2611", "name": "PBA2", "mgmt_code": "051T2611", "customer_id": CU, "customer_name": "가상해외(주)", "currency": "USD",
                             "status": "수주확정", "biz_div": "T", "project_type": "NEW_EQUIP", "shipment_form": "ASSEMBLY", "order_date": "2026-11-13", "due_date": FUT,
                             "is_archived": 0, "unit_qty": 1, "order_amount": 0})
    CO = ins(c, "consumable_orders", {"co_no": "C-261118-9", "mgmt_code": "090C2611", "customer_id": CU, "customer_name": "가상해외(주)", "order_date": "2026-11-18",
                                      "status": "CONFIRMED", "currency": "USD"})
    CI = ins(c, "consumable_order_items", {"co_id": CO, "part_name": "PIN", "qty": 2, "unit_price": 31.43, "amount": 62.86})

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
M.get_user = lambda request: ADMIN
with contextlib.redirect_stdout(io.StringIO()):
    try:
        M.startup()
    except Exception as _e:
        print("startup:", _e)
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


def oi(iid, col="amount"):
    with D.db_session() as c:
        return c.execute("SELECT %s FROM order_items WHERE id=?" % col, (iid,)).fetchone()[0]


TI_A = M._TI_ACOLS[0]

print("§1 점·쉼표 판별(서버 공용)")
H = D.num_swap_hint
check(H("13.224,61") == "13,224.61" and H("$13.224,61") == "13,224.61" and H("-1.234,5") == "-1,234.5", "「13.224,61」 → 「13,224.61」로 치셨나요?")
check(H("1.234.567") == "1,234,567" and H("12,5") == "12.5" and H("1,50") == "1.50", "점 두 개 · 쉼표 뒤 1~2자리도 바로잡을 값")
check(all(H(x) is None for x in ("1,234.56", "1234.56", "1,234", "0.5", "", None, "13,224.61", "abc", "M3,5")), "바른 숫자·빈칸·글자는 그대로(막지 않음)")
check(H("1,2,3") == "" and "숫자 형식이 맞지 않습니다" in D.num_swap_msg("1,2,3"), "바로잡을 수 없는 것 = 「숫자 형식이 맞지 않습니다」")
check(D.money_r2(2806.659) == 2806.66 and D.money_r2(41.355) == 41.36 and D.money_r2(1.005) == 1.01 and D.money_r2(None) is None, "둘째 자리 엑셀식 반올림(1.005 → 1.01 · 파이썬 round 는 1.0)")

print("§2 작업일정표 호기 칸(/sales/schedule/unit-field)")
uf = lambda iid, f, v: q(cl.post, "/sales/schedule/unit-field", json={"iid": iid, "field": f, "value": v})
r = uf(I1, "unit_price", "13.224,61")
check(r.status_code == 400 and "13,224.61 로 치셨나요" in r.json().get("error", "") and oi(I1, "unit_price") == 1000, "단가 「13.224,61」 → 저장 안 함 · 「13,224.61 로 치셨나요?」", r.text[:200])
r = uf(I1, "amount", "2.806,66")
check(r.status_code == 400 and oi(I1) == 1000, "금액 「2.806,66」 → 저장 안 함", r.text[:120])
r = uf(I1, "amount", "2806.659")
check(r.status_code == 200 and oi(I1) == 2806.66, "금액 2806.659 → 2806.66 으로 저장", oi(I1))
r = uf(I2, "unit_price", "41.355")
check(r.status_code == 200 and oi(I2, "unit_price") == 41.355 and oi(I2) == 41.36, "단가는 친 값 그대로(41.355) · 금액 = 둘째 자리(41.36)", (oi(I2, "unit_price"), oi(I2)))
r = uf(I2, "qty", "3")
check(r.status_code == 200 and oi(I2) == 124.07, "수량 3 → 금액 41.355×3=124.065 → 124.07", oi(I2))
r = uf(I2, TI_A, "13.224,61")
check(r.status_code == 400 and oi(I2, TI_A) in (None, 0), "세금계산서 금액(호기) 「13.224,61」 → 저장 안 함", r.text[:120])
r = uf(I2, TI_A, "100.005")
check(r.status_code == 200 and oi(I2, TI_A) == 100.01, "세금계산서 금액(호기) 100.005 → 100.01", oi(I2, TI_A))
with D.db_session() as c:
    tot = c.execute("SELECT total_amount FROM orders WHERE id=?", (O,)).fetchone()[0]
check(abs(tot - (2806.66 + 124.07 + 2806.659)) < 1e-9, "수주 합계 = 줄 합(고친 두 줄은 둘째 자리 · 안 고친 줄은 그대로)", tot)

print("§3 지금까지 저장된 값은 그대로")
check(oi(I3) == 2806.659 and oi(I3, "unit_price") == 935.553, "안 고친 셋째 자리 금액 줄(2,806.659)은 그대로", oi(I3))
for u_ in ("/sales/schedule", "/project/%d" % P):
    q(cl.get, u_)
check(oi(I3) == 2806.659, "작업일정표·프로젝트 화면을 열어도 그대로")

print("§4 세금계산서 금액(줄 · /sales/schedule/row-tax)")
rt = lambda v: q(cl.post, "/sales/schedule/row-tax", json={"ref_id": P, "field": TI_A, "value": v, "uids": "%d,%d" % (I1, I2)})
r = rt("13.224,61")
check(r.status_code == 400 and "13,224.61" in r.json().get("error", "") and oi(I1, TI_A) in (None, 0), "줄 「13.224,61」 → 저장 안 함(11-16·17 13.22461 로 저장됐던 곳)", r.text[:160])
r = rt("13224.615")
check(r.status_code == 200 and round(oi(I1, TI_A) + oi(I2, TI_A), 2) == 13224.62, "줄 13224.615 → 합계 13224.62(둘째 자리)로 나눠 저장", (oi(I1, TI_A), oi(I2, TI_A)))
r = rt("13,224.61")
check(r.status_code == 200 and round(oi(I1, TI_A) + oi(I2, TI_A), 2) == 13224.61, "바른 「13,224.61」은 그대로 저장")

print("§5 프로젝트 상세 호기 줄 수정 · 호기 추가")
r = q(cl.post, "/sales/orders/items/%d/edit" % I1, data={"amount": "1.234,5"})
check(r.status_code == 400 and "1,234.5 로 치셨나요" in r.json().get("message", "") and oi(I1) == 2806.66, "호기 줄 금액 「1.234,5」 → 저장 안 함", r.text[:160])
r = q(cl.post, "/sales/orders/items/%d/edit" % I1, data={"amount": "1234.565"})
check(r.status_code == 200 and oi(I1) == 1234.57, "호기 줄 금액 1234.565 → 1234.57", (r.status_code, r.text[:120], oi(I1)))
r = q(cl.post, "/sales/orders/items/%d/edit" % I1, data={"unit_price": "12,5"})
check(r.status_code == 400 and oi(I1) == 1234.57, "판매단가 「12,5」 → 저장 안 함(「12.5 로 치셨나요?」)", r.text[:120])
with D.db_session() as c:
    n0 = c.execute("SELECT COUNT(*) FROM order_items WHERE order_id=?", (O,)).fetchone()[0]
r = q(cl.post, "/sales/orders/%d/add-unit" % O, data={"amount": "13.224,61", "qty": "1"})
with D.db_session() as c:
    n1 = c.execute("SELECT COUNT(*) FROM order_items WHERE order_id=?", (O,)).fetchone()[0]
check(r.status_code == 400 and n1 == n0, "호기 추가 금액 「13.224,61」 → 추가 안 함", r.text[:120])
r = q(cl.post, "/sales/orders/%d/add-unit" % O, data={"amount": "500.125", "qty": "1"})
with D.db_session() as c:
    last = c.execute("SELECT amount FROM order_items WHERE order_id=? ORDER BY id DESC LIMIT 1", (O,)).fetchone()[0]
check(r.status_code == 200 and last == 500.13, "호기 추가 금액 500.125 → 500.13", (r.status_code, r.text[:120], last))

print("§6 작업일정표 프로젝트 칸 · 소모품 라인")
ok_, msg_ = D.schedule_cell_update("project", P2, "amount", "1.234,56")
with D.db_session() as c:
    pa = c.execute("SELECT order_amount FROM projects WHERE id=?", (P2,)).fetchone()[0]
check(not ok_ and "1,234.56" in msg_ and not pa, "프로젝트 칸 금액 「1.234,56」 → 저장 안 함", (ok_, msg_))
ok_, msg_ = D.schedule_cell_update("project", P2, "amount", "1000.005")
with D.db_session() as c:
    pa = c.execute("SELECT order_amount FROM projects WHERE id=?", (P2,)).fetchone()[0]
check(ok_ and pa == 1000.01, "프로젝트 칸 금액 1000.005 → 1000.01", pa)
r = q(cl.post, "/consumables/%d/items/%d/edit" % (CO, CI), data={"unit_price": "31,43"})
with D.db_session() as c:
    cu = c.execute("SELECT unit_price, amount FROM consumable_order_items WHERE id=?", (CI,)).fetchone()
check(r.status_code == 400 and "31.43" in r.json().get("error", "") and tuple(cu) == (31.43, 62.86), "소모품 단가 「31,43」 → 저장 안 함(전엔 3143 으로 저장)", (r.text[:120], tuple(cu)))
r = q(cl.post, "/consumables/%d/items/%d/edit" % (CO, CI), data={"unit_price": "31.432"})
with D.db_session() as c:
    cu = c.execute("SELECT unit_price, amount FROM consumable_order_items WHERE id=?", (CI,)).fetchone()
check(r.status_code == 200 and tuple(cu) == (31.432, 62.86), "소모품 단가 31.432 → 금액 62.86(지금처럼 둘째 자리)", tuple(cu))

print("§7 단가 표시 = 엑셀식")
check(M._fmt_price(41.355, "USD") == "41.36" and M._fmt_price(4.2533, "USD") == "4.25" and M._fmt_price(1234.5, "KRW") == "1,235" and M._fmt_price("1,000", "KRW") == "1,000",
      "41.355 → 41.36(전엔 41.35) · 4.2533 → 4.25 · 원화 1234.5 → 1,235", [M._fmt_price(41.355, "USD"), M._fmt_price(1234.5, "KRW")])
check(M._fmt_price("", "USD") == "0.00" and M._fmt_price("x", "USD") == "x", "빈칸·글자는 지금처럼")

print("§8 화면(공용 틀 · 금액 꾸미개 · 베트남어)")
h = q(cl.get, "/consumables/%d" % CO).text
import json as _js
_m = re.search(r"ns_ask: (\"(?:[^\"\\]|\\.)*\")", h)
_ask = _js.loads(_m.group(1)) if _m else ""
check("window.__knkNumSwap" in h and "점(.)과 쉼표(,)가 바뀐 것 같습니다" in _ask and "{fix}" in _ask, "공용 틀에 바로잡기 스크립트 · 한국어 글", _ask[:60])
check(h.find("window.__knkNumSwap") < h.find("window.knkDraft"), "되살림(z53) 스크립트보다 앞")
kin = io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "knk_inputs.html"), encoding="utf-8").read()
check("z1191z56" in kin and "split('.').length > 2" in kin, "금액 꾸미개: 점 뒤 쉼표·점 두 개면 칠 때 쉼표를 지우지 않음")
import app.i18n as I  # noqa: E402
_ns = getattr(I, "T", None) or getattr(I, "TEXTS", None) or {}
_src = io.open(os.path.join(ROOT, "app", "i18n.py"), encoding="utf-8").read()
check("ch_ns_ask" in _src and "có vẻ dấu chấm" in _src and "ch_ns_bad" in _src, "베트남어 글도 있음")

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
