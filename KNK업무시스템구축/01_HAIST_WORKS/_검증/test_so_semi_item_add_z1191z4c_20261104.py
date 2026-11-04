# -*- coding: utf-8 -*-
"""z1191z4c 시험 — 제품 수주는 호기 추가가 아니라 「＋ 품목 추가」 · 제품 줄은 「대」로 세지 않음
   이새롬 프로 요청(2026-11-04) 「형태를 제품으로 설정하면 호기 추가가 되지 않게 해주세요.」(015T2610 · 혼합: 완제품 1호기 + 제품 2줄)
   대표 결정 「1. 추천 2. 추천 3. 추천」
  §1 화면(임시 DB · TestClient): 혼합 프로젝트의 제품 수주 카드 = 「＋ 품목 추가」 · 제품 표(수량 칸) · 「품목 2 · 수량 2개」 ·
     총 수량 「1대 · 제품 2개」 · 수주액 상자 「× 3대」 문장 숨김
  §2 서버: 제품 수주 품목 추가 = 1줄(수량 N · 금액 = 단가×N · 규격 · 'N호기' 아님) · 배지 그대로 제품 · 수량 = 품목 수량 합 ·
     품목 삭제 → 수량 다시 합 · 이력 「품목 줄 삭제」 · 완제품 수주 호기 추가는 예전 그대로(N대 = N줄 · N호기)
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z4c-test-only-not-a-real-key"   # 시험용 가짜 값

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
    tmp = tempfile.mkdtemp(prefix="knk_z1191z4c_")
    real = D.DB_PATH
    D.DB_PATH = os.path.join(tmp, "t.db")
    assert D.DB_PATH != real
    with contextlib.redirect_stdout(io.StringIO()):
        D.init_db()
    with D.db_session() as c:
        have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
        for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                         ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                         ("must_change_pw", "INTEGER DEFAULT 0")]:
            if col not in have:
                c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
        c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, "
                  "can_view_logistics, can_use_logistics) VALUES ('가상영업', 'admin', 'Z935', 'Z935', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
        u = dict(c.execute("SELECT * FROM users WHERE employee_no='Z935'").fetchone())
        c.execute("INSERT INTO customers (name) VALUES ('(주)가상성전')")
        cust = c.execute("SELECT id FROM customers WHERE name='(주)가상성전'").fetchone()[0]
        # 015T2610 모양: 프로젝트 형태 = 완제품(ASSEMBLY) · 완제품 수주(1호기) + 제품 수주(품명 2줄 · so_form 없음)
        c.execute("INSERT INTO projects (name, mgmt_code, customer_id, customer_name, project_type, status, biz_div, currency, shipment_form) "
                  "VALUES ('PBA', '097T2699', ?, '(주)가상성전', 'NEW_EQUIP', 'IN_PROGRESS', 'T', 'KRW', 'ASSEMBLY')", (cust,))
        pid = c.execute("SELECT id FROM projects WHERE mgmt_code='097T2699'").fetchone()[0]
        c.execute("INSERT INTO orders (project_id, order_no, customer_id, currency, status, so_type, unit_qty, total_amount, unit_label, order_date) "
                  "VALUES (?, 'T-269997-1', ?, 'KRW', 'CONFIRMED', 'EQUIPMENT', 1, 1530000, '1호기', '2026-10-16')", (pid, cust))
        oa = c.execute("SELECT id FROM orders WHERE order_no='T-269997-1'").fetchone()[0]
        c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label, currency, unit_status) "
                  "VALUES (?, 1, 1530000, 1530000, '1호기', 'KRW', '진행중')", (oa,))
        c.execute("INSERT INTO orders (project_id, order_no, customer_id, currency, status, so_type, unit_qty, total_amount, unit_label, order_date) "
                  "VALUES (?, 'T-269997-2', ?, 'KRW', 'CONFIRMED', 'EQUIPMENT', 2, 340000, 'TOP PIN BLOCK · BOT PIN BLOCK', '2026-10-27')", (pid, cust))
        ob = c.execute("SELECT id FROM orders WHERE order_no='T-269997-2'").fetchone()[0]
        for lbl, amt in (("TOP PIN BLOCK", 180000), ("BOT PIN BLOCK", 160000)):
            c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label, spec, currency, unit_status) "
                      "VALUES (?, 1, ?, ?, ?, ?, 'KRW', '진행중')", (ob, amt, amt, lbl, lbl))
        c.execute("UPDATE projects SET order_amount=1870000 WHERE id=?", (pid,))
    return {"user": u, "pid": pid, "oa": oa, "ob": ob}


def main():
    S = setup_db()
    import app.main as M                                    # noqa: E402
    from fastapi.testclient import TestClient              # noqa: E402
    M.get_user = lambda request: S["user"]
    cl = TestClient(M.app)
    pid, oa, ob = S["pid"], S["oa"], S["ob"]

    print("§1 화면 — 혼합 프로젝트(완제품 + 제품)")
    # 작업일정표에서 그 수주를 눌러 들어온 것처럼(?so=) — 이새롬 프로 화면과 같다(그 수주가 편집 카드)
    h = cl.get("/project/%d?so=T-269997-2" % pid).text
    i_b, i_a = h.find('<div class="so-card editable" data-soid="%d"' % ob), h.find('<div class="so-card ref-so" data-soid="%d"' % oa)
    check("제품 수주가 편집 카드 · 완제품 수주는 참고 카드", 0 < i_b < i_a, (i_b, i_a))
    cb = h[i_b:i_a]
    check("제품 수주 카드 단추 = 「＋ 품목 추가」(「＋ 호기 추가」 없음)", ">＋ 품목 추가</button>" in cb and "＋ 호기 추가" not in cb)
    check("추가 칸 = 품명 · 규격 · 수량(개) · 단가(1개당)", 'placeholder="품명 (예: TOP PIN BLOCK)"' in cb and 'name="spec"' in cb
          and ">개 ×<" in cb and 'placeholder="단가 (1개당)"' in cb)
    check("제품 표 = 수량 칸 있음", '<th class="num" style="width:60px;">수량</th>' in cb)
    check("카드 아래 = 「품목 2 · 수량 2개」(「2대」 아님)", "품목 <b>2</b> · 수량 <b>2개</b>" in cb and "수량 <b>2대</b>" not in cb)
    check("총 수량 = 「1대 · 제품 2개」", "총 수량 1대" in h and "제품 2개" in h and "총 수량 3대" not in h)
    check("수주액 상자 「단가 … × N대」 문장 숨김", '단가 <b style="color:var(--ink);">' not in h)

    print("§2 서버 — 품목 추가 · 삭제")
    r = cl.post("/sales/orders/%d/add-unit" % ob, data={"label": "PIN GUIDE", "spec": "PG-1", "amount": "10,000", "qty": "3",
                                                         "currency": "KRW", "note": ""})
    j = r.json()
    with D.db_session() as c:
        rows = [dict(x) for x in c.execute("SELECT unit_label, qty, unit_price, amount, spec FROM order_items WHERE order_id=? ORDER BY id", (ob,))]
        o = dict(c.execute("SELECT unit_qty, total_amount FROM orders WHERE id=?", (ob,)).fetchone())
    new = rows[-1] if rows else {}
    check("품목 추가 ok", j.get("ok"), j)
    check("1줄만 생김(호기로 안 나눔) · 이름 PIN GUIDE · 수량 3 · 단가 10,000 · 금액 30,000 · 규격 PG-1",
          len(rows) == 3 and new.get("unit_label") == "PIN GUIDE" and new.get("qty") == 3 and new.get("unit_price") == 10000
          and new.get("amount") == 30000 and new.get("spec") == "PG-1", rows)
    check("수주 수량 = 품목 수량 합 5 · 합계 370,000", o["unit_qty"] == 5 and o["total_amount"] == 370000, o)
    h2 = cl.get("/project/%d?so=T-269997-2" % pid).text
    cb2 = h2[h2.find('<div class="so-card editable" data-soid="%d"' % ob):h2.find('<div class="so-card ref-so" data-soid="%d"' % oa)]
    check("추가 뒤에도 배지 「제품」 · 「품목 3 · 수량 5개」", ">제품</span>" in cb2 and "품목 <b>3</b> · 수량 <b>5개</b>" in cb2)

    r = cl.post("/sales/orders/%d/add-unit" % ob, data={"label": "", "amount": "5000", "qty": "1", "currency": "KRW"})
    with D.db_session() as c:
        lbl = c.execute("SELECT unit_label FROM order_items WHERE order_id=? ORDER BY id DESC LIMIT 1", (ob,)).fetchone()[0]
    check("품명을 비우면 「(품명 미입력)」(N호기 아님)", r.json().get("ok") and lbl == "(품명 미입력)", lbl)

    with D.db_session() as c:
        pg_id = c.execute("SELECT id FROM order_items WHERE order_id=? AND unit_label='PIN GUIDE'", (ob,)).fetchone()[0]
    r = cl.post("/sales/orders/items/%d/delete" % pg_id)
    with D.db_session() as c:
        o = dict(c.execute("SELECT unit_qty, total_amount FROM orders WHERE id=?", (ob,)).fetchone())
        hist = [x[0] for x in c.execute("SELECT note FROM order_status_history WHERE order_id=? ORDER BY id", (ob,))]
    check("품목 삭제 → 수량 = 남은 품목 수량 합 3 · 합계 345,000", r.json().get("ok") and o["unit_qty"] == 3 and o["total_amount"] == 345000, o)
    check("이력 「품목 줄 삭제 [PIN GUIDE]」", any("품목 줄 삭제 [PIN GUIDE]" in (n or "") for n in hist), hist)

    r = cl.post("/sales/orders/%d/add-unit" % oa, data={"label": "", "amount": "1,000,000", "qty": "2", "currency": "KRW"})
    with D.db_session() as c:
        la = [x[0] for x in c.execute("SELECT unit_label FROM order_items WHERE order_id=? ORDER BY id", (oa,))]
        qa = c.execute("SELECT unit_qty FROM orders WHERE id=?", (oa,)).fetchone()[0]
    ha = cl.get("/project/%d" % pid).text
    ca = ha[ha.find('<div class="so-card editable" data-soid="%d"' % oa):]
    ca = ca[:ca.find('<div class="so-card ref-so"')]
    check("완제품 수주 카드(기본 진입)는 「＋ 호기 추가」 · 「수량 3대」 그대로(위에서 2대 더함)", ">＋ 호기 추가</button>" in ca and "수량 <b>3대</b>" in ca and "＋ 품목 추가" not in ca, (re.findall(r"add-unit\">[^<]*<", ca), re.findall(r"수량 <b>[^<]*</b>|품목 <b>[^<]*</b>", ca), len(ca)))
    check("완제품 수주 호기 추가는 예전 그대로(2대 = 2줄 · N호기 · 대수 3)",
          r.json().get("ok") and len(la) == 3 and all(x.endswith("호기") for x in la) and qa == 3, (la, qa))

    print("결과: 통과 %d / 실패 %d" % (OK, FAIL))
    return FAIL


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
