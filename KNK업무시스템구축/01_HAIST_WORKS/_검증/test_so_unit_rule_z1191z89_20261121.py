# -*- coding: utf-8 -*-
"""z1191z89 시험 — 수주 수량 단위 규칙 하나(작업일정표 = 프로젝트 상세) · 추가 수주 펼침표 통화 기호
   안지연 프로 요청(001E2611 · 첫 수주 단위 빈칸) + 대표 11-20 「단위, 원화등 … 전체적으로 맞는지 다시 검증해」 → 11-21 「다음 진행할것 진행해」
  §1 규칙 함수: 적어 둔 단위가 먼저 · 비면 형태별 기본 하나(완제품 대 · 제품 EA · 기타 식 · 소모품 건 · 상품 PO유형) = 작업일정표 수량 칸 규칙(_board_qty_unit)
  §2 숫자+단위 글자: 한글 단위는 붙여 쓰고(1식·2대·1대분) EA·SET 는 띄움 · 프로젝트 수주 단위가 섞이면 곱셈 문장 안 씀
  §3 화면(임시 DB · TestClient): 001E2611 모양(기타 · 첫 수주 단위 빈칸 + SET 수주) — 카드 「1식」·「2 SET」 · 「× N대」 없음 ·
     빈칸을 SET 로 고치면 오른쪽 「단가 … × 3 SET」 · 제품 수주 빈 단위 = EA
  §4 일정표 「같은 관리번호의 추가 수주」 펼침표: ₩ 고정 없음 · 수주 통화 기호
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z89-test-only-not-a-real-key"   # 시험용 가짜 값

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
    tmp = tempfile.mkdtemp(prefix="knk_z1191z89_")
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
                  "can_view_logistics, can_use_logistics) VALUES ('가상영업', 'admin', 'Z989', 'Z989', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
        u = dict(c.execute("SELECT * FROM users WHERE employee_no='Z989'").fetchone())
        c.execute("INSERT INTO customers (name) VALUES ('(주)가상아이')")
        cust = c.execute("SELECT id FROM customers WHERE name='(주)가상아이'").fetchone()[0]
        # 001E2611 모양: 형태 기타 · 첫 수주 단위 빈칸(1) + SET 수주(2)
        c.execute("INSERT INTO projects (name, mgmt_code, customer_id, customer_name, project_type, status, biz_div, currency, shipment_form) "
                  "VALUES ('지그', '097E2699', ?, '(주)가상아이', 'NEW_EQUIP', 'IN_PROGRESS', 'E', 'KRW', 'ETC')", (cust,))
        pid = c.execute("SELECT id FROM projects WHERE mgmt_code='097E2699'").fetchone()[0]
        oids = []
        for no, bu, q, amt in (("E-269989-1", None, 1, 100000), ("E-269989-2", "SET", 2, 200000)):
            c.execute("INSERT INTO orders (project_id, order_no, customer_id, currency, status, so_type, so_form, unit_qty, total_amount, unit_label, "
                      "order_date, board_unit) VALUES (?, ?, ?, 'KRW', 'CONFIRMED', 'OTHER', 'ETC', ?, ?, '지그', '2026-11-01', ?)",
                      (pid, no, cust, q, amt, bu))
            oid = c.execute("SELECT id FROM orders WHERE order_no=?", (no,)).fetchone()[0]
            oids.append(oid)
            c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label, currency, unit_status) "
                      "VALUES (?, ?, 100000, ?, '지그', 'KRW', '진행중')", (oid, q, amt))
        c.execute("UPDATE projects SET order_amount=300000 WHERE id=?", (pid,))
        # 제품 수주(단위 빈칸) 하나짜리 프로젝트
        c.execute("INSERT INTO projects (name, mgmt_code, customer_id, customer_name, project_type, status, biz_div, currency, shipment_form) "
                  "VALUES ('핀블럭', '098T2699', ?, '(주)가상아이', 'NEW_EQUIP', 'IN_PROGRESS', 'T', 'KRW', 'SEMI')", (cust,))
        pid2 = c.execute("SELECT id FROM projects WHERE mgmt_code='098T2699'").fetchone()[0]
        c.execute("INSERT INTO orders (project_id, order_no, customer_id, currency, status, so_type, unit_qty, total_amount, unit_label, order_date) "
                  "VALUES (?, 'T-269989-3', ?, 'KRW', 'CONFIRMED', 'EQUIPMENT', 3, 30000, 'PIN', '2026-11-01')", (pid2, cust))
        o3 = c.execute("SELECT id FROM orders WHERE order_no='T-269989-3'").fetchone()[0]
        c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label, spec, currency, unit_status) "
                  "VALUES (?, 3, 10000, 30000, 'PIN', 'PIN', 'KRW', '진행중')", (o3,))
        c.execute("UPDATE projects SET order_amount=30000 WHERE id=?", (pid2,))
        # 038T2604 모양: 제품 · 등록 때 「작업일정표 수량」 5 식 · 품목 2줄(3 + 3 = 6)
        c.execute("INSERT INTO projects (name, mgmt_code, customer_id, customer_name, project_type, status, biz_div, currency, shipment_form) "
                  "VALUES ('지그2', '099T2699', ?, '(주)가상아이', 'NEW_EQUIP', 'IN_PROGRESS', 'T', 'KRW', 'SEMI')", (cust,))
        pid3 = c.execute("SELECT id FROM projects WHERE mgmt_code='099T2699'").fetchone()[0]
        c.execute("INSERT INTO orders (project_id, order_no, customer_id, currency, status, so_type, unit_qty, total_amount, unit_label, order_date, "
                  "board_qty, board_unit) VALUES (?, 'T-269989-4', ?, 'KRW', 'CONFIRMED', 'EQUIPMENT', 2, 500000, 'JIG', '2026-11-01', 5, '식')", (pid3, cust))
        o4 = c.execute("SELECT id FROM orders WHERE order_no='T-269989-4'").fetchone()[0]
        for lbl in ("TOP JIG", "BOT JIG"):
            c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label, spec, currency, unit_status) "
                      "VALUES (?, 3, 41667, 250000, ?, ?, 'KRW', '진행중')", (o4, lbl, lbl))
        # 수주가 2건이어야 프로젝트 정보에 「수량(수주)」 칸이 나온다 → 앞선 수주 하나(제품 · 1줄)
        c.execute("INSERT INTO orders (project_id, order_no, customer_id, currency, status, so_type, unit_qty, total_amount, unit_label, order_date) "
                  "VALUES (?, 'T-269989-5', ?, 'KRW', 'CONFIRMED', 'EQUIPMENT', 1, 10000, 'PIN', '2026-10-01')", (pid3, cust))
        o5 = c.execute("SELECT id FROM orders WHERE order_no='T-269989-5'").fetchone()[0]
        c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label, spec, currency, unit_status) "
                  "VALUES (?, 1, 10000, 10000, 'PIN', 'PIN', 'KRW', '진행중')", (o5,))
        c.execute("UPDATE projects SET order_amount=510000 WHERE id=?", (pid3,))
    return {"user": u, "pid": pid, "oids": oids, "pid2": pid2, "pid3": pid3}


def main():
    S = setup_db()
    import app.main as M                                    # noqa: E402
    from fastapi.testclient import TestClient              # noqa: E402

    print("§1 규칙 함수 = 작업일정표 수량 칸 규칙")
    su = M._so_qty_unit_z89
    check("비면: 완제품 대 · 제품 EA · 기타 식 · 소모품 건",
          [su({"form_key": k}) for k in ("assembly", "semi", "etc", "consumable")] == ["대", "EA", "식", "건"],
          [su({"form_key": k}) for k in ("assembly", "semi", "etc", "consumable")])
    check("적어 둔 단위가 먼저(기타 SET · 제품 대)", su({"form_key": "etc", "board_unit": "SET"}) == "SET" and su({"form_key": "semi", "board_unit": "대"}) == "대")
    check("소모품 수주도 고른 단위가 먼저(식 → 식 · 비면 건) — 일정표 수주 줄과 같게",
          su({"form_key": "consumable", "board_unit": "식"}) == "식" and su({"form_key": "consumable"}) == "건")
    check("상품 = PO유형(개조 식 · 그 밖 대분)", su({"form_key": "parts", "po_type": "개조"}) == "식" and su({"form_key": "parts", "po_type": "신규"}) == "대분")
    same = all(su({"form_key": k, "board_unit": bu}) == M._board_qty_unit({"qty_form": lb, "board_unit": bu})
               for k, lb in (("assembly", "완제품"), ("semi", "제품"), ("etc", "기타"), ("consumable", "소모품"))
               for bu in (None, "SET", "EA"))
    check("형태 4가지 × 단위(빈칸·SET·EA) 모두 일정표 함수와 같은 글자", same)

    print("§2 숫자+단위 · 섞임")
    qu = M._qty_with_unit_z89
    check("1식 · 2대 · 1대분 · 3건 붙임 / 2 SET · 1 EA 띄움 · 천 단위 쉼표",
          [qu(1, "식"), qu(2, "대"), qu(1, "대분"), qu(3, "건"), qu(2, "SET"), qu(1, "EA"), qu(1200, "EA")] ==
          ["1식", "2대", "1대분", "3건", "2 SET", "1 EA", "1,200 EA"])
    one = M._so_unit_one_z89
    check("수주 단위 하나면 그 단위 · 섞이면 빈칸 · 취소 수주는 빼고 · 수주 없으면 대",
          one([{"form_key": "etc", "board_unit": "SET"}, {"form_key": "etc", "board_unit": "SET"}]) == "SET"
          and one([{"form_key": "etc"}, {"form_key": "etc", "board_unit": "SET"}]) == ""
          and one([{"form_key": "etc", "board_unit": "SET"}, {"form_key": "etc", "status": "CANCELLED"}]) == "SET"
          and one([]) == "대")

    print("§3 화면 — 001E2611 모양(기타 · 첫 수주 단위 빈칸)")
    M.get_user = lambda request: S["user"]
    cl = TestClient(M.app)
    h = cl.get("/project/%d" % S["pid"]).text
    check("단위 빈칸 수주 카드 = 「수량 1식」(전: 1대 · 일정표는 1 식)", "수량 <b>1식</b>" in h and "수량 <b>1대</b>" not in h)
    check("SET 수주 카드 = 「수량 2 SET」", "수량 <b>2 SET</b>" in h)
    check("수주 표 머리 「단가 (1식)」·「(1 SET)」(전: 둘 다 1대)", ">(1식)</span>" in h and ">(1 SET)</span>" in h and ">(1대)</span>" not in h)
    check("단위가 섞여 「단가 × N대」 곱셈 문장 없음", "대</b> = <b" not in h and "SET</b> = <b" not in h)
    with D.db_session() as c:
        c.execute("UPDATE orders SET board_unit='SET' WHERE id=?", (S["oids"][0],))
    h2 = cl.get("/project/%d" % S["pid"]).text
    check("빈칸을 SET 로 고치면 카드 「1 SET」", "수량 <b>1 SET</b>" in h2)
    check("오른쪽 곱셈 = 「× 3 SET」(수량 합 · 대 아님)", ">3 SET</b> = <b" in h2 and "대</b> = <b" not in h2)
    h3 = cl.get("/project/%d" % S["pid2"]).text
    check("제품 수주 단위 빈칸 = 「수량 3 EA」(전: 3개 · 일정표 EA)", "수량 <b>3 EA</b>" in h3 and "수량 <b>3개</b>" not in h3)

    h4 = cl.get("/project/%d?so=T-269989-4" % S["pid3"]).text
    check("등록 때 「작업일정표 수량 5 식」 → 카드 「품목 2 · 수량 5식」(전: 품목 합 6식)", "품목 <b>2</b> · 수량 <b>5식</b>" in h4 and "수량 <b>6식</b>" not in h4)
    # z1191z123(11-24 안지연·이새롬 답 ①): 품목 두 줄 이상(세트)은 일정표 수량 기준 · 품목 줄 합과 비교 안 함
    check("세트(품목 2줄)는 「(품목 줄 합 6)」 안 띄움(z123 · 일정표 수량 기준)", "(품목 줄 합 6)" not in h4)
    check("프로젝트 정보 수량(수주)도 5식", "</span></dt><dd>5식" in h4, h4[h4.find("<dt>수량 <span"):h4.find("<dt>수량 <span") + 160] if "<dt>수량 <span" in h4 else "정보 수량 칸 없음")
    check("같은 수를 일정표 함수도 씀(표시수량 먼저)", M._so_qty_z89({"board_qty": 5, "units": [{"qty": 3}, {"qty": 3}]}) == 5
          and M._so_qty_z89({"units": [{"qty": 3}, {"qty": 3}]}) == 6 and M._so_qty_z89({"unit_qty": 2}) == 2)

    print("§4 일정표 추가 수주 펼침표 — 통화 기호")
    src = open(os.path.join(ROOT, "app", "templates", "schedule_board.html"), encoding="utf-8").read()
    i = src.find("function toggleRefSos(")
    seg = src[i:src.find("\n}\n", i)]
    check("₩ 고정 없음 · 수주 통화(r.currency)로 기호", "'₩'+Number(r.amount)" not in seg and "r.currency" in seg and "_rs+Number(r.amount)" in seg)
    check("종류 칸 = 서버가 주는 so_type", "r.so_type" in seg)

    print("§5 2차(대표 「2번까지 같이 고치고」) — 수주 목록 · 총 수량 · 같은 날 창 · 제작요청서 · 수정 화면 표")
    check("단위별 합 「2대 · 3 SET」 · 상품은 글자 그대로", M._so_qty_join_z89([{"fk": "assembly", "unit": "대", "qty": 2}, {"fk": "etc", "unit": "SET", "qty": 3},
                                                              {"fk": "parts", "text": "완제품 1대분"}]) == "2대 · 3 SET · 완제품 1대분")
    check("프로젝트 상세 「총 수량 3 SET」(전: 총 수량 3대)", "총 수량 3 SET" in h2 and "총 수량 3대" not in h2)
    with D.db_session() as c:
        qm = M._so_qty_text_map_z89(c, S["oids"])
        o4 = c.execute("SELECT id FROM orders WHERE order_no='T-269989-4'").fetchone()[0]
        qm4 = M._so_qty_text_map_z89(c, [o4])
    check("수주 번호 → 수량 글자(카드와 같음): SET 1 · SET 2 · 표시수량 5식", [qm[x]["text"] for x in S["oids"]] == ["1 SET", "2 SET"] and qm4[o4]["text"] == "5식",
          ([qm[x]["text"] for x in S["oids"]], qm4))
    hl = cl.get("/sales/orders").text
    check("수주 목록 수량 칸 = 「1 SET」·「2 SET」·「5식」(전: 1대·2대·2대)", "<b>1 SET</b>" in hl and "<b>2 SET</b>" in hl and "<b>5식</b>" in hl and "</b>대</td>" not in hl)
    hc = cl.get("/sales/orders?biz=C").text
    check("수주 목록 소모품 탭에 「None대」 없음", "None</b>대" not in hc and "None대" not in hc)
    src2 = open(os.path.join(ROOT, "app", "templates", "_v5_partials", "knk_tax_sameday.html"), encoding="utf-8").read()
    check("같은 날 창 = 서버 글자(완제품 N대 · 그 밖 품목 N줄)", "x.units_text" in src2 and "x.units + '대'" not in src2)
    src3 = open(os.path.join(ROOT, "app", "templates", "prod_request_edit.html"), encoding="utf-8").read()
    check("제작요청서 품목 번호 = 호기 없으면 수주 수량 글자", "it.hogi||it.qtytxt||" in src3 and src3.count('data-qtytxt="') >= 4)
    with D.db_session() as c:
        p3 = dict(c.execute("SELECT * FROM projects WHERE id=?", (S["pid3"],)).fetchone())
        o4id = c.execute("SELECT id FROM orders WHERE order_no='T-269989-4'").fetchone()[0]
        it = M._z49_item(c, p3, "", "")
        it4 = M._z49_item(c, p3, str(o4id), "")
    check("제작요청서 품목 줄 = 가리키는 수주의 수량 글자(PIN 수주 → 「1 EA」)", it.get("qty_txt") == "1 EA" and it.get("so_nos") == ["T-269989-5"], (it.get("so_nos"), it.get("qty_txt")))
    check("JIG 수주를 가리키면 「5식」(등록 때 수 · 품목 합 6식 아님)", it4.get("qty_txt") == "5식", (it4.get("so_nos"), it4.get("qty_txt")))

    print("\n결과: 통과 %d / 실패 %d" % (OK, FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
