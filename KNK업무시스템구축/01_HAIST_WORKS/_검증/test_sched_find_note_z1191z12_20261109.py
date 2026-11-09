# -*- coding: utf-8 -*-
"""z1191z12 시험 — 이새롬 프로 요청 「기타사항이나 비고에 적혀 있는 내용도 검색 기능에」(대표 「1,2,3,4 진행해」 2026-11-09)
  작업일정표 「전체에서 찾기」(cust=, 전 기간) 가
  ① 기타사항(호기 비고·프로젝트 기타사항·소모품 기타사항) ② 화면에 안 보이는 비고(상품 부품 비고·소모품 품목 비고·
     3개 넘어 「외N」으로 잘린 비고) ③ 화면 글자 칸(고객사2·담당자·납품위치·영업담당자 …) 으로도 찾고
  ④ 검색칸 안내 문구 · 이 화면 거르기(JS)가 숨은 비고(data-find)도 보고 · 엑셀 저장 찾기도 같음 · 없는 글자는 0건
  임시 DB · TestClient · 운영 아님
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z12-test-only-not-a-real-key"
import app.database as D  # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z12_")
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
                 "VALUES ('가상관리자', 'admin', 'T908', 'T908', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T908'").fetchone())
    conn.execute("INSERT INTO customers (name) VALUES ('가상고객')")
import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

M.get_user = lambda request: ADMIN
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0


def check(cond, msg):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", msg)
    else:
        FAIL += 1; print("  ❌", msg)




def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


# 지난 달(2025-03) 자료 — 이번 달 화면엔 없고 「전체에서 찾기」(cust=)로만 찾힌다
BASE = {"quick": "1", "customer_name": "가상고객", "biz_div": "M", "project_type": "NEW_EQUIP", "po_type": "신규", "status": "진행중",
        "confirm_now": "1", "order_date": "2025-03-04", "due_date": "2025-03-20", "currency": "KRW", "equip_name": "가상장비", "unit_qty": "1"}


def post_new(**kw):
    f = dict(BASE); f.update(kw)
    return q(cl.post, "/projects/new", data=f)


def proj(name):
    with D.db_session() as c:
        return dict(c.execute("SELECT * FROM projects WHERE name=? ORDER BY id DESC", (name,)).fetchone())


def so_items(pid):
    with D.db_session() as c:
        oid = c.execute("SELECT id FROM orders WHERE project_id=? ORDER BY id LIMIT 1", (pid,)).fetchone()[0]
        return oid, [r[0] for r in c.execute("SELECT id FROM order_items WHERE order_id=? ORDER BY id", (oid,))]


def row_html(h, code):
    return "\n".join(m for m in re.findall(r"<tr[^>]*>.*?</tr>", h, re.S) if (">%s<" % code) in m)


def find(word):
    return q(cl.get, "/sales/schedule?cust=%s" % word).text


print("§0 자료 만들기")
post_new(name="찾기-호기비고", model="MZ1", shipment_form="ASSEMBLY", unit_qty="2", unit_price="100", order_amount="200", **{"unit_amount[]": ["100", "100"]})
P1 = proj("찾기-호기비고"); _o1, I1 = so_items(P1["id"])
post_new(name="찾기-잘린비고", model="MZ2", shipment_form="ASSEMBLY", unit_qty="4", unit_price="100", order_amount="400", **{"unit_amount[]": ["100"] * 4})
P2 = proj("찾기-잘린비고"); _o2, I2 = so_items(P2["id"])
post_new(name="찾기-프로젝트기타", model="MZ3", shipment_form="ASSEMBLY", unit_qty="1", unit_price="100", order_amount="100", **{"unit_amount[]": ["100"]})
P3 = proj("찾기-프로젝트기타")
post_new(name="찾기-상품부품", model="MZ4", shipment_form="ASSEMBLY", unit_qty="1", unit_price="100", order_amount="100", **{"unit_amount[]": ["100"]})
P4 = proj("찾기-상품부품"); O4, I4 = so_items(P4["id"])
with D.db_session() as c:
    for _i, _n in zip(I1, ("PO#4506062127", "PO#4506093575")):
        c.execute("UPDATE order_items SET line_note=? WHERE id=?", (_n, _i))
    for _i, _n in zip(I2, ("NA-1", "NA-2", "NA-3", "NA-4")):
        c.execute("UPDATE order_items SET line_note=? WHERE id=?", (_n, _i))
    c.execute("UPDATE projects SET logi_note='LOGI메모77' WHERE id=?", (P3["id"],))
    c.execute("UPDATE order_items SET line_note=NULL WHERE order_id=(SELECT id FROM orders WHERE project_id=?)", (P3["id"],))
    c.execute("UPDATE orders SET so_type='PARTS_EXPORT' WHERE id=?", (O4,))
    for _i in I4:
        c.execute("UPDATE order_items SET line_note='PARTNOTE77' WHERE id=?", (_i,))
    c.execute("INSERT INTO consumable_orders (co_no, customer_name, order_date, due_date, currency, total_amount, status, mgmt_code, biz_div, equip_name, "
              "note, secondary_customer, cc_name, ship_to, sales_name) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              ("C-250305-91", "가상고객", "2025-03-05", "2025-03-25", "KRW", 1000, "CONFIRMED", "991C2503", "T", "소모품 1종",
               "CONSHEAD88", "Z12최종고객", "Z12담당자", "Z12납품위치", "Z12영업"))
    _cid = c.execute("SELECT id FROM consumable_orders WHERE co_no='C-250305-91'").fetchone()[0]
    c.execute("INSERT INTO consumable_order_items (co_id, line_no, part_name, qty, unit, unit_price, amount, note) VALUES (?,?,?,?,?,?,?,?)",
              (_cid, 1, "POGO PIN", 1, "EA", 1000, 1000, "CONSNOTE55"))
    c.execute("INSERT INTO consumable_order_items (co_id, line_no, part_name, qty, unit, unit_price, amount, note) VALUES (?,?,?,?,?,?,?,?)",
              (_cid, 2, "SPRING", 1, "EA", 0, 0, "None"))
check(len(I1) == 2 and len(I2) == 4 and len(I4) >= 1, "호기 2·4·부품 줄 만들어짐 — %d·%d·%d" % (len(I1), len(I2), len(I4)))
hm = q(cl.get, "/sales/schedule?ym=2026-11").text
check(not row_html(hm, P1["mgmt_code"]) and not row_html(hm, "991C2503"), "이번 달(2026-11) 화면엔 2025-03 자료 없음 — 전 기간 찾기로만 찾힘")

print("§1 기타사항(보이는 비고) — 「전체에서 찾기」")
h = find("4506062127")
r1 = row_html(h, P1["mgmt_code"])
check(r1 and "PO#4506062127" in r1, "호기 비고 PO#4506062127 → 그 줄 찾힘(기타사항 칸에 보임)")
check(row_html(find("4506093575"), P1["mgmt_code"]), "같은 줄 둘째 호기 비고 PO#4506093575 도 찾힘")
check(row_html(find("logi메모77"), P3["mgmt_code"]), "프로젝트 기타사항(LOGI메모77) — 대소문자 무시로 찾힘")
check(row_html(find("CONSHEAD88"), "991C2503"), "소모품 기타사항(CONSHEAD88) 찾힘")

print("§2 화면에 안 보이는 비고")
h = find("NA-4")
r2 = row_html(h, P2["mgmt_code"])
check(r2 and "외1" in r2 and ">NA-1 · NA-2 · NA-3 외1<" in r2, "호기 비고 4개 → 기타사항 칸은 「NA-1 · NA-2 · NA-3 외1」(그대로)")
check(r2 and 'data-find="NA-1 NA-2 NA-3 NA-4"' in r2, "잘린 넷째 비고 NA-4 로도 찾힘 · 줄에 data-find(이 화면 거르기용)")
h = find("PARTNOTE77")
r4 = row_html(h, P4["mgmt_code"])
check(r4 and "PARTNOTE77" in r4 and ">PARTNOTE77<" not in r4, "상품(부품) 수주 부품 비고 PARTNOTE77 찾힘 · 기타사항 칸엔 안 보임(표시 규칙 그대로)")
h = find("CONSNOTE55")
r5 = row_html(h, "991C2503")
check(r5 and "CONSNOTE55" in r5, "소모품 품목 비고 CONSNOTE55 찾힘 · data-find 에 실림")
check(r5 and "None" not in r5.split("data-find=")[1].split('"')[1], "소모품 품목 비고의 「None」 글자는 찾기 자료에 안 들어감")
check(not row_html(find("None"), "991C2503"), "「None」으로 찾으면 그 소모품 안 나옴")

print("§3 화면 글자 칸")
for w, lab in (("Z12최종고객", "고객사2"), ("Z12담당자", "고객 담당자"), ("Z12납품위치", "납품위치"), ("Z12영업", "영업담당자")):
    check(row_html(find(w), "991C2503"), "%s(%s) 로 찾힘" % (lab, w))
check(row_html(find("2025-03-25"), "991C2503"), "납품일(2025-03-25) 로 찾힘")

print("§4 없는 글자 · 엑셀 · 화면 원문")
h0 = find("zzz없는글자z12")
check(not re.findall(r"<tr[^>]*data-ref=", h0), "없는 글자 → 0줄")
import openpyxl  # noqa: E402
r = q(cl.get, "/sales/schedule/export.xlsx?ym=2025-03&cust=PARTNOTE77")
ws = openpyxl.load_workbook(io.BytesIO(r.content)).active
hdr = [c.value for c in ws[1]]; ic = hdr.index("관리번호")
codes = {str(rw[ic]) for rw in ws.iter_rows(min_row=2, values_only=True) if rw[ic]}
check(codes == {P4["mgmt_code"]}, "엑셀 저장(그 달)도 같은 찾기 — 부품 비고 PARTNOTE77 만 — %s" % sorted(codes))
b = io.open(os.path.join(ROOT, "app", "templates", "schedule_board.html"), encoding="utf-8").read()
check("고객사·기타사항(비고) — Enter=전체 기간에서 찾기" in b, "검색칸 안내 문구에 「기타사항(비고)」")
check("hay+=(tr.getAttribute('data-find')||'');" in b, "이 화면 거르기(글자 칠 때)도 data-find 를 본다")
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
