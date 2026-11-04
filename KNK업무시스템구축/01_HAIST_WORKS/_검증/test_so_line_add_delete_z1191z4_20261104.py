# -*- coding: utf-8 -*-
"""z1191z4 시험 — 수주 내역 줄 추가·삭제 (이새롬 프로 요청 2026-11-04 「수주내역에 호기,단가,금액 등 1줄추가, 1줄삭제 가능하게」)
   대표 결정: ① 「＋ 호기 추가」 잠금 상태에서도 보임 → 누르면 수정 모드 자동 + 추가 칸 열림
             ② 「✏️ 수정」 상태에서만 장비 호기 줄 삭제(×) — 확인창 「○○ · 금액 ○○ 을 삭제합니다」
  §1 서버(임시 DB · TestClient): 상세 화면에 ×·「삭제」 헤더·추가 단추 · 줄 삭제 → 합계·대수·이력 다시 계산 ·
     「호기·일련번호 관리」에 등록된 줄은 막음(줄 그대로) · 줄 추가 · 청구된 수주는 그대로 막힘
  §2 화면 규칙(CSS · JS 원문): 잠금 때 추가 단추 숨김 규칙 없음 · 수정 때 × 칸 보임 · 확인창 문구 · 저장 안 한 변경 먼저
"""
import contextlib
import io
import os
import re
import sqlite3
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z4-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


def setup_db():
    """임시 DB: 장비 프로젝트 1 · 수주 1(줄 3: 세금계산서 적힌 줄 · 보통 줄 · 호기·일련번호에 등록된 줄) · 청구된 수주 1"""
    tmp = tempfile.mkdtemp(prefix="knk_z1191z4_")
    real = D.DB_PATH
    D.DB_PATH = os.path.join(tmp, "t.db")
    assert D.DB_PATH != real
    with contextlib.redirect_stdout(io.StringIO()):
        D.init_db()
    from app.migrations import m_z1053_project_unit as MU
    with contextlib.redirect_stdout(io.StringIO()):
        MU.migrate(D.DB_PATH)
    with D.db_session() as c:
        have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
        for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                         ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                         ("must_change_pw", "INTEGER DEFAULT 0")]:
            if col not in have:
                c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
        c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, "
                  "can_view_logistics, can_use_logistics) VALUES ('가상영업', 'admin', 'Z934', 'Z934', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
        u = dict(c.execute("SELECT * FROM users WHERE employee_no='Z934'").fetchone())
        c.execute("INSERT INTO customers (name) VALUES ('(주)가상성전')")
        cust = c.execute("SELECT id FROM customers WHERE name='(주)가상성전'").fetchone()[0]
        c.execute("INSERT INTO projects (name, mgmt_code, customer_id, customer_name, project_type, status, biz_div, currency) "
                  "VALUES ('PBA', '099T2699', ?, '(주)가상성전', 'NEW_EQUIP', 'IN_PROGRESS', 'T', 'KRW')", (cust,))
        pid = c.execute("SELECT id FROM projects WHERE mgmt_code='099T2699'").fetchone()[0]
        c.execute("INSERT INTO orders (project_id, order_no, customer_id, currency, status, so_type, unit_qty, total_amount, unit_label, order_date, due_date) "
                  "VALUES (?, 'T-269999-1', ?, 'KRW', 'CONFIRMED', 'EQUIPMENT', 3, 440000, 'TOP PIN BLOCK · BOT PIN BLOCK · PIN C', '2026-10-27', '2026-11-06')",
                  (pid, cust))
        oid = c.execute("SELECT id FROM orders WHERE order_no='T-269999-1'").fetchone()[0]
        ids = []
        for lbl, amt, td, ta in (("TOP PIN BLOCK", 180000, "2026-10-30", 170000), ("BOT PIN BLOCK", 160000, None, None),
                                 ("PIN C", 100000, None, None)):
            c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label, currency, unit_status, tax_invoice_date, tax_invoice_amt1) "
                      "VALUES (?, 1, ?, ?, ?, 'KRW', '진행중', ?, ?)", (oid, amt, amt, lbl, td, ta))
            ids.append(c.execute("SELECT max(id) FROM order_items").fetchone()[0])
        c.execute("INSERT INTO project_units (project_id, working_name, entity, seed_order_item_id, seed_order_no, seed_unit_label) "
                  "VALUES (?, 'PIN C', 'KOR', ?, 'T-269999-1', 'PIN C')", (pid, ids[2]))
        # 청구(INVOICED)된 수주는 다른 프로젝트에 — 같은 프로젝트면 그 카드가 먼저 그려질 수 있다
        c.execute("INSERT INTO projects (name, mgmt_code, customer_id, customer_name, project_type, status, biz_div, currency) "
                  "VALUES ('SENSOR', '098T2699', ?, '(주)가상성전', 'NEW_EQUIP', 'IN_PROGRESS', 'T', 'KRW')", (cust,))
        pid2 = c.execute("SELECT id FROM projects WHERE mgmt_code='098T2699'").fetchone()[0]
        c.execute("INSERT INTO orders (project_id, order_no, customer_id, currency, status, so_type, unit_qty, total_amount) "
                  "VALUES (?, 'T-269999-2', ?, 'KRW', 'INVOICED', 'EQUIPMENT', 1, 50000)", (pid2, cust))
        oid2 = c.execute("SELECT id FROM orders WHERE order_no='T-269999-2'").fetchone()[0]
        c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label, currency) VALUES (?, 1, 50000, 50000, '1호기', 'KRW')", (oid2,))
        inv_item = c.execute("SELECT max(id) FROM order_items").fetchone()[0]
    return {"user": u, "pid": pid, "oid": oid, "ids": ids, "inv_item": inv_item}


def main():
    S = setup_db()
    import app.main as M                                    # noqa: E402
    from fastapi.testclient import TestClient              # noqa: E402
    M.get_user = lambda request: S["user"]
    cl = TestClient(M.app)
    pid, oid, ids = S["pid"], S["oid"], S["ids"]

    print("§1 서버 — 임시 DB · TestClient")
    r = cl.get("/project/%d" % pid)
    h = r.text
    check("상세 화면 200", r.status_code == 200, r.status_code)
    card = h[h.find('data-soid="%d"' % oid):]
    # z1191z4c: 이 수주는 'N호기' 줄이 없어 배지가 「제품」 → 단추 이름이 「＋ 품목 추가」(같은 add-unit 단추)
    check("수주 카드에 추가 단추(잠금 상태에서도 그려짐 · 제품 수주라 「＋ 품목 추가」)", 'class="btn-mini primary add-unit">＋ 품목 추가<' in card)
    check("× 칸 헤더 = 「삭제」(예전 「수정」 아님)", '<th class="center edit-only" style="width:80px;">삭제</th>' in card
          and '<th class="center edit-only" style="width:80px;">수정</th>' not in h)
    check("줄마다 삭제(×) 단추 3개", card.count('class="row-del"') >= 3, card.count('class="row-del"'))
    check("z1191z4b: 카드 위 단추 = 「🗑 수주 삭제」(예전 「🗑 삭제」 없음)", ">🗑 수주 삭제</button>" in card and ">🗑 삭제</button>" not in h)

    r = cl.post("/sales/orders/items/%d/delete" % ids[1])
    j = r.json()
    with D.db_session() as c:
        o = dict(c.execute("SELECT total_amount, unit_qty, unit_label FROM orders WHERE id=?", (oid,)).fetchone())
        left = [x[0] for x in c.execute("SELECT unit_label FROM order_items WHERE order_id=? ORDER BY id", (oid,))]
        hist = [x[0] for x in c.execute("SELECT note FROM order_status_history WHERE order_id=? ORDER BY id", (oid,))]
        pamt = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    check("보통 줄(BOT PIN BLOCK) 삭제 → ok", r.status_code == 200 and j.get("ok"), j)
    check("남은 줄 = TOP PIN BLOCK · PIN C", left == ["TOP PIN BLOCK", "PIN C"], left)
    check("수주 합계 440,000 → 280,000 · 대수 3 → 2 · 라벨 다시 묶음",
          o["total_amount"] == 280000 and o["unit_qty"] == 2 and o["unit_label"] == "TOP PIN BLOCK · PIN C", o)
    check("변경 이력에 「호기 라인 삭제 [BOT PIN BLOCK] · 단가 160,000 제거」",
          any("BOT PIN BLOCK" in (n or "") and "160,000" in (n or "") and "440,000 → 280,000" in (n or "") for n in hist), hist)
    pk = pamt.keys()
    _amt_col = next((k for k in ("order_amount", "amount_krw") if k in pk), None)
    check("프로젝트 수주액도 다시 계산(280,000)", _amt_col is not None and float(pamt[_amt_col] or 0) == 280000,
          (_amt_col, pamt[_amt_col] if _amt_col else None))

    r = cl.post("/sales/orders/items/%d/delete" % ids[2])
    j = r.json()
    with D.db_session() as c:
        still = c.execute("SELECT count(*) FROM order_items WHERE id=?", (ids[2],)).fetchone()[0]
        o2 = c.execute("SELECT total_amount FROM orders WHERE id=?", (oid,)).fetchone()[0]
    check("「호기·일련번호 관리」에 등록된 줄 삭제 → 400 · 안내(취소로)", r.status_code == 400 and "호기·일련번호" in (j.get("message") or "")
          and "취소" in (j.get("message") or ""), (r.status_code, j))
    check("막힌 줄은 그대로 · 합계 그대로", still == 1 and o2 == 280000, (still, o2))

    r = cl.post("/sales/orders/%d/add-unit" % oid, data={"label": "추가 PIN", "amount": "50,000", "qty": "1", "currency": "KRW", "note": ""})
    j = r.json()
    with D.db_session() as c:
        o3 = dict(c.execute("SELECT total_amount, unit_qty FROM orders WHERE id=?", (oid,)).fetchone())
        lbls = [x[0] for x in c.execute("SELECT unit_label FROM order_items WHERE order_id=? ORDER BY id", (oid,))]
    check("줄 추가(추가 PIN · 50,000) → 합계 330,000 · 대수 3", j.get("ok") and o3["total_amount"] == 330000 and o3["unit_qty"] == 3
          and lbls[-1] == "추가 PIN", (j, o3, lbls))

    r = cl.post("/sales/orders/items/%d/delete" % S["inv_item"])
    check("청구(INVOICED)된 수주 줄은 예전처럼 삭제 막힘", r.status_code == 400, (r.status_code, r.text[:120]))

    # 표가 없는 옛 DB 에서도 삭제가 깨지지 않음(project_units 없음)
    with D.db_session() as c:
        c.execute("ALTER TABLE project_units RENAME TO project_units_z4_off")
    try:
        with D.db_session() as c:
            tid = c.execute("SELECT id FROM order_items WHERE order_id=? AND unit_label='추가 PIN'", (oid,)).fetchone()[0]
        r = cl.post("/sales/orders/items/%d/delete" % tid)
        check("호기 표가 없는 DB 에서도 삭제 정상", r.status_code == 200 and r.json().get("ok"), (r.status_code, r.text[:120]))
    finally:
        with D.db_session() as c:
            c.execute("ALTER TABLE project_units_z4_off RENAME TO project_units")

    print("§2 화면 규칙 — CSS · JS 원문")
    css = open(os.path.join(ROOT, "static", "css", "project_detail.css"), encoding="utf-8").read()
    html = open(os.path.join(ROOT, "app", "templates", "project_detail.html"), encoding="utf-8").read()
    check("잠금 때 「＋ 호기 추가」 숨김 규칙 없음", not re.search(r"\.so-card\.editable:not\(\.unlocked\)\s*\.add-unit(?![-\w])", css))
    check("잠금 때 × 는 계속 숨김", ".so-card.editable:not(.unlocked) .row-del { display: none !important; }" in css)
    check("수정 때 장비·항목 표도 × 칸 보임", ".so-card.editable.unlocked .so-units td.edit-only { display: table-cell !important; }" in css)
    check("💾 줄 저장 단추는 계속 숨김", ".so-card .row-save," in css and ".so-card .so-meta-save { display: none !important; }" in css)
    check("추가 단추: 잠금이면 수정 모드 켜고 추가 칸 열기", "if (!card.classList.contains('unlocked') && toggleBtn) {" in html
          and "toggleBtn.click();" in html and "addCard.classList.add('open');" in html)
    check("확인창 문구 「○○」 · 금액 ○○ 을 삭제합니다 + 함께 지워지는 기록 안내",
          "' 을 삭제합니다.'" in html and "이 줄에 적힌 아래 기록도 함께 지워집니다" in html and "마지막 줄입니다" in html)
    check("저장 안 한 다른 줄 변경이 있으면 먼저 저장하게(삭제·추가 둘 다)", html.count("먼저 위 「💾 저장」을 누른 뒤") == 2)
    check("z1191z4b: 수주 삭제 확인창 첫 줄 「수주번호 ○○ 전체를 삭제합니다」 + 한 줄은 × 안내",
          "' 전체를 삭제합니다.\\n\\n'" in html and "한 줄만 지우려면 취소 → ✏️ 수정 → 줄 오른쪽 ×" in html)
    print("결과: 통과 %d / 실패 %d" % (OK, FAIL))
    return FAIL


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
