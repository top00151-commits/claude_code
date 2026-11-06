# -*- coding: utf-8 -*-
"""z1191z9 시험 — 소모품 저장이 앞에 본 소모품에 값을 덮어쓰던 결함(이새롬 프로 신고 032C2607 · 대표 「1·2·3·4 진행」 2026-11-06)
  3 서버 문지기: edit-field·save-all 은 화면 번호(page_co)가 주소 번호와 같아야 저장(없음·다름 = 409 · 아무것도 안 씀) ·
    품목 경로(edit·link-project·link-by-mgmt·delete)와 save-all 품목은 그 소모품 것만 · 저장만 눌러 단가가 반올림되지 않음
  4 「None」 글자 저장 막기(머리·품목) · 화면이 빈칸을 「None」으로 그리지 않음
  1·2 원문: spa_nav 안전망(재선언 오류 → 전체 새로 열기 · 주소 기록 먼저) · 소모품 상세 = 전체 새로 열기 · 화면 번호 전송
  임시 DB · TestClient · 운영 아님
"""
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z9-test-only-not-a-real-key"
import app.database as D  # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z9_")
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
                 "VALUES ('가상관리자', 'admin', 'T909', 'T909', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T909'").fetchone())

    def _co(no, code, equip, sec, biz, items):
        conn.execute("INSERT INTO consumable_orders (co_no, customer_name, order_date, due_date, currency, total_amount, status, mgmt_code, biz_div, equip_name, secondary_customer) "
                     "VALUES (?,?,?,?,?,?,?,?,?,?,?)", (no, "가상 VINA", "2026-11-02", "2026-11-19", "USD", 0, "CONFIRMED", code, biz, equip, sec))
        cid = conn.execute("SELECT id FROM consumable_orders WHERE co_no=?", (no,)).fetchone()[0]
        for i, (nm, qty, up) in enumerate(items, 1):
            conn.execute("INSERT INTO consumable_order_items (co_id, line_no, part_name, qty, unit, unit_price, amount) VALUES (?,?,?,?,?,?,?)",
                         (cid, i, nm, qty, "EA", up, round(qty * up, 2)))
        conn.execute("UPDATE consumable_orders SET total_amount=(SELECT SUM(amount) FROM consumable_order_items WHERE co_id=?) WHERE id=?", (cid, cid))
        return cid
    A = _co("C-1", "901C2611", "DSV 소모품 4종", "DSV", "T", [("PCB", 15, 44.52)])
    B = _co("C-2", "902C2611", "DRT2 소모품 9종", "DRT2", "M", [("DSV 소모품", 8, 755.5625)])
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


def co(cid):
    with D.db_session() as c:
        return dict(c.execute("SELECT * FROM consumable_orders WHERE id=?", (cid,)).fetchone())


def items(cid):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT * FROM consumable_order_items WHERE co_id=? ORDER BY id", (cid,))]


IA, IB = items(A)[0]["id"], items(B)[0]["id"]
A0 = co(A)

print("§1 save-all — 사고 재현 요청(B 화면 값 · A 주소) 은 거부")
hdrB = {"equip_name": "DRT2 소모품 9종", "secondary_customer": "DRT2", "biz_div": "M", "tax_invoice_amt1": "804.03"}
r = q(cl.post, "/consumables/%d/save-all" % A, json={"header": hdrB, "lines": [{"iid": IB, "fields": {"part_name": "DSV 소모품"}}]})
check(r.status_code == 409 and "새로 고침" in r.json().get("error", ""), "옛 화면(번호 없음) → 409 · 「새로 고침」 안내")
r = q(cl.post, "/consumables/%d/save-all" % A, json={"header": hdrB, "lines": [{"iid": IB, "fields": {}}], "page_co": B})
check(r.status_code == 409, "화면 번호 B · 주소 A → 409")
A1 = co(A)
check(A1["equip_name"] == A0["equip_name"] and A1["secondary_customer"] == "DSV" and A1["biz_div"] == "T", "A 는 그대로(장비명·2차 고객사·사업부)")
r = q(cl.post, "/consumables/%d/save-all" % A, json={"header": {"equip_name": "DSV 소모품 4종"}, "lines": [{"iid": IB, "fields": {"part_name": "X"}}], "page_co": A})
check(r.status_code == 409 and items(B)[0]["part_name"] == "DSV 소모품", "화면 번호는 맞아도 남의 품목(B)이 섞이면 통째 거부 · B 품목 그대로")

print("§2 save-all — 정상 저장 · 단가 반올림 안 함 · None 글자 안 씀")
r = q(cl.post, "/consumables/%d/save-all" % B, json={"header": {"equip_name": "DRT2 소모품 9종", "secondary_customer": "B에서 고침", "cc_name": "None", "ship_to": "None"},
                                                   "lines": [{"iid": IB, "fields": {"part_name": "DSV 소모품", "qty": "8", "unit_price": "755.56", "note": "None", "spec": "None"}}], "page_co": B})
B1, IB1 = co(B), items(B)[0]
check(r.status_code == 200 and r.json().get("ok") and B1["secondary_customer"] == "B에서 고침", "같은 번호 → 저장됨")
check(abs(IB1["unit_price"] - 755.5625) < 1e-9 and abs(B1["total_amount"] - 6044.5) < 1e-9, "표시값 755.56 으로 저장해도 단가 755.5625 · 합계 6,044.50 그대로 — %s / %s" % (IB1["unit_price"], B1["total_amount"]))
check((B1["cc_name"] or "") == "" and (B1["ship_to"] or "") == "" and (IB1["note"] or "") == "" and (IB1["spec"] or "") == "", "「None」 글자 → 빈칸(머리·품목)")
r = q(cl.post, "/consumables/%d/save-all" % B, json={"header": {}, "lines": [{"iid": IB, "fields": {"unit_price": "760"}}], "page_co": B})
check(abs(items(B)[0]["unit_price"] - 760) < 1e-9, "실제로 바꾼 단가(760)는 저장")

print("§3 edit-field — 화면 번호 필요")
r = q(cl.post, "/consumables/%d/edit-field" % A, json={"field": "equip_name", "value": "덮어쓰기"})
check(r.status_code == 409 and co(A)["equip_name"] == "DSV 소모품 4종", "번호 없음 → 409 · 안 씀")
r = q(cl.post, "/consumables/%d/edit-field" % A, json={"field": "equip_name", "value": "덮어쓰기", "page_co": B})
check(r.status_code == 409 and co(A)["equip_name"] == "DSV 소모품 4종", "번호 다름 → 409 · 안 씀")
r = q(cl.post, "/consumables/%d/edit-field" % A, json={"field": "secondary_customer", "value": "None", "page_co": A})
check(r.status_code == 200 and (co(A)["secondary_customer"] or "") == "", "번호 같음 → 저장 · 「None」 → 빈칸")
r = q(cl.post, "/consumables/%d/edit-field" % A, json={"field": "secondary_customer", "value": "DSV", "page_co": A})
check(co(A)["secondary_customer"] == "DSV", "정상 값 저장")

print("§4 품목 경로 — 그 소모품 품목만")
r = q(cl.post, "/consumables/%d/items/%d/edit" % (A, IB), data={"part_name": "남의 품목"})
check(r.status_code == 409 and items(B)[0]["part_name"] == "DSV 소모품", "edit: A 주소로 B 품목 → 409")
r = q(cl.post, "/consumables/%d/items/%d/edit" % (A, IA), data={"note": "None"})
check(r.status_code == 200 and (items(A)[0]["note"] or "") == "", "edit: 자기 품목 → 저장 · 「None」 → 빈칸")
r = q(cl.post, "/consumables/%d/items/%d/link-project" % (A, IB), data={"project_id": "1"})
check(r.status_code == 409 and items(B)[0]["linked_project_id"] is None, "link-project: 남의 품목 → 409")
r = q(cl.post, "/consumables/%d/items/%d/link-by-mgmt" % (A, IB), json={"mgmt_code": ""})
check(r.status_code == 409, "link-by-mgmt: 남의 품목 → 409")
r = q(cl.post, "/consumables/%d/items/%d/delete" % (A, IB))
check(r.status_code == 409 and len(items(B)) == 1, "delete: A 주소로 B 품목 삭제 → 409 · B 품목 남음")

print("§5 화면(상세) — 빈칸을 「None」으로 그리지 않음 · 화면 번호")
with D.db_session() as c:
    c.execute("UPDATE consumable_orders SET cc_name=NULL, cc_phone=NULL, ship_to=NULL, sales_name=NULL, model_name=NULL WHERE id=?", (A,))
    c.execute("UPDATE consumable_order_items SET spec=NULL, note=NULL WHERE id=?", (IA,))
h = q(cl.get, "/consumables/%d" % A).text
check('value="None"' not in h, "빈칸이 value=\"None\" 으로 안 그려짐")
check('id="coPage" data-co-id="%d"' % A in h and "page_co:_coPageId()" in h, "화면 번호 표시 · 저장 때 보냄")

print("§6 원문 — spa_nav 안전망 · 소모품 상세 전체 새로 열기")
s = io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "spa_nav.html"), encoding="utf-8").read()
check("var FULL_ONLY = [/^\\/consumables\\/\\d+\\/?$/];" in s and "if (mustFull(href)) return false;" in s and "if (mustFull(url))" in s, "소모품 상세 = 클릭·뒤로 모두 전체 새로 열기")
check("REDECL.test(m)) _redecl = true" in s and "if (_redecl) { window.knkLeaveOk = true; window.location.replace(url); return; }" in s, "재선언 오류 → 그 화면 전체 새로 열기")
check(s.index("history.pushState({ knkSpa: true }") < s.index("document.startViewTransition(doSwap)"), "주소 기록이 본문 교체보다 먼저")
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
