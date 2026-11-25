# -*- coding: utf-8 -*-
"""z1191z132 (대표 11-24 「같은 유형 미리 막기」) 시험 — 취소 수주(CANCELLED)·취소 호기(「취소」)를 빼는지,
   그리고 취소가 없는 보통 경우는 예전과 같은지 둘 다 본다.
  §1 프로젝트 상세(TestClient): 납기 MAX·발주일 MIN 맞추기 · 수주액 상자 호기 목록(N) · 통화 혼합 경고
  §1b 빠른 수정 화면 열기: 납기·발주일 맞추기
  §2 제작요청서 납기 = 고른 수주들의 가장 늦은 납기(없으면 프로젝트 납기)
  §3 매출 홈 「진행 프로젝트」 _z40_open_projects
  §4 매출 3종 _sales_3way(① 수주매출 · ② 진행매출 · ③ 최종매출) + 매출 보고서 _z17_lines 같은 기준
  §6 _so_qty_lines_z89 / _so_qty_note_z89
  §7 project_workflow.compute_project_display_status / _bulk (메모리 sqlite)
  §8 글자 확인(직접 부르기 어려운 곳)
"""
import contextlib
import io
import os
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z132-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

R = []


def check(label, cond, got=None):
    R.append(bool(cond))
    print(("✅ " if cond else "❌ ") + label + ("" if cond else "  → " + str(got)[:300]))


def setup_db():
    tmp = tempfile.mkdtemp(prefix="knk_z1191z132_")
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
                  "can_view_logistics, can_use_logistics) VALUES ('가상영업', 'admin', 'Z132', 'Z132', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
        u = dict(c.execute("SELECT * FROM users WHERE employee_no='Z132'").fetchone())
        c.execute("INSERT INTO customers (name) VALUES ('(주)가상시험')")
        cust = c.execute("SELECT id FROM customers WHERE name='(주)가상시험'").fetchone()[0]
    return {"user": u, "cust": cust}


def mk_project(c, cust, code, due, odate, sos):
    """sos = [(수주번호, 수주상태, 통화, 발주일, 납기, [(호기상태, 금액)])] → (pid, [oid], {oid: [iid]})"""
    c.execute("INSERT INTO projects (name, mgmt_code, customer_id, customer_name, project_type, status, biz_div, currency, "
              "due_date, order_date, shipment_form) VALUES ('시험장비', ?, ?, '(주)가상시험', 'NEW_EQUIP', 'IN_PROGRESS', 'T', 'KRW', ?, ?, 'ASSEMBLY')",
              (code, cust, due, odate))
    pid = c.execute("SELECT id FROM projects WHERE mgmt_code=?", (code,)).fetchone()[0]
    oids, iids = [], {}
    for no, st, ccy, od, dd, units in sos:
        tot = sum(a for _s, a in units)
        c.execute("INSERT INTO orders (project_id, order_no, customer_id, currency, status, so_type, unit_qty, total_amount, unit_label, "
                  "order_date, due_date) VALUES (?, ?, ?, ?, ?, 'EQUIPMENT', ?, ?, '장비', ?, ?)",
                  (pid, no, cust, ccy, st, len(units), tot, od, dd))
        oid = c.execute("SELECT id FROM orders WHERE order_no=?", (no,)).fetchone()[0]
        oids.append(oid)
        iids[oid] = []
        for i, (us, amt) in enumerate(units, 1):
            c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label, currency, unit_status, due_date) "
                      "VALUES (?, 1, ?, ?, ?, ?, ?, ?)", (oid, amt, amt, "%d호기" % i, ccy, us, dd))
            iids[oid].append(c.execute("SELECT MAX(id) FROM order_items").fetchone()[0])
    return pid, oids, iids


def main():
    S = setup_db()
    cust = S["cust"]
    with D.db_session() as c:
        # A: 취소 있음 — 살아 있는 KRW 수주(호기 2 진행중 + 1 취소) · 취소된 USD 수주(납기 더 늦고 발주일 더 이름)
        pa, oa, ia = mk_project(c, cust, "001T2699", "2027-03-01", "2026-10-01", [
            ("T-269901-1", "CONFIRMED", "KRW", "2026-11-01", "2026-12-10", [("진행중", 100), ("진행중", 100), ("취소", 100)]),
            ("T-269901-2", "CANCELLED", "USD", "2026-10-01", "2027-03-01", [("진행중", 500)]),
        ])
        # B: 취소 없음 — KRW 수주 호기 2 + USD 수주 호기 1 (예전과 같아야 함)
        pb, ob, ib = mk_project(c, cust, "002T2699", "2000-01-01", "2000-01-01", [
            ("T-269902-1", "CONFIRMED", "KRW", "2026-11-01", "2026-12-10", [("진행중", 100), ("진행중", 100)]),
            ("T-269902-2", "CONFIRMED", "USD", "2026-10-01", "2027-03-01", [("진행중", 500)]),
        ])
        # C: 빠른 수정 화면용(A 와 같은 모양)
        pc, oc, ic = mk_project(c, cust, "003T2699", "2027-03-01", "2026-10-01", [
            ("T-269903-1", "CONFIRMED", "KRW", "2026-11-01", "2026-12-10", [("진행중", 100)]),
            ("T-269903-2", "CANCELLED", "KRW", "2026-10-01", "2027-03-01", [("진행중", 500)]),
        ])
        # D: quick-edit 취소 없음
        pd_, od_, id_ = mk_project(c, cust, "004T2699", "2000-01-01", "2000-01-01", [
            ("T-269904-1", "CONFIRMED", "KRW", "2026-11-01", "2026-12-10", [("진행중", 100)]),
            ("T-269904-2", "CONFIRMED", "KRW", "2026-10-01", "2027-03-01", [("진행중", 500)]),
        ])

    import app.main as M                                    # noqa: E402
    from fastapi.testclient import TestClient              # noqa: E402
    M.get_user = lambda request: S["user"]
    cap = {}
    _orig_ctx = M.ctx

    def _ctx(request, name, **kw):
        if name == "project_detail.html":
            cap.clear()
            cap.update(kw)
        return _orig_ctx(request, name, **kw)
    M.ctx = _ctx
    cl = TestClient(M.app)

    def pget(pid, col):
        with D.db_session() as c:
            return c.execute("SELECT %s FROM projects WHERE id=?" % col, (pid,)).fetchone()[0]

    print("§1 프로젝트 상세")
    r = cl.get("/project/%d" % pa)
    check("A 상세 열림(200)", r.status_code == 200, r.status_code)
    # z1191z153 (대표 11-25 원칙 ③): 화면 열기만으로 저장 안 함 → 알림 목록(heal153)에 뜨고, 「맞추기」(POST)를 눌러야 저장
    check("A 열기만으로는 납기 그대로(저장 안 함) · ⚠ 알림에 납기", pget(pa, "due_date") != "2026-12-10" and any("납기" in h for h in (cap.get("heal153") or [])), (pget(pa, "due_date"), cap.get("heal153")))
    cl.post("/project/%d/heal" % pa)
    check("A 취소 있음: 납기 = 살아 있는 수주 납기 2026-12-10(취소 수주 2027-03-01 아님)", pget(pa, "due_date") == "2026-12-10", pget(pa, "due_date"))
    check("A 취소 있음: 발주일 = 2026-11-01(취소 수주 2026-10-01 아님)", pget(pa, "order_date") == "2026-11-01", pget(pa, "order_date"))
    _au = cap.get("all_units_sorted") or []
    check("A 수주액 상자 호기 = 2(취소 수주 호기·「취소」 호기 뺌 · 예전 4)", len(_au) == 2, [(u.get("so_no"), u.get("unit_status")) for u in _au])
    check("A 통화 혼합 아님(취소된 USD 수주 뺌) · 경고 없음",
          len(cap.get("currency_mix") or []) == 1 and not cap.get("currency_warning"), (cap.get("currency_mix"), cap.get("currency_warning")))
    r = cl.get("/project/%d" % pb)
    check("B 상세 열림(200)", r.status_code == 200, r.status_code)
    _cap_b = dict(cap)
    cl.post("/project/%d/heal" % pb)
    cap.clear(); cap.update(_cap_b)
    check("B 취소 없음: 납기 = MAX 2027-03-01 (예전과 같음)", pget(pb, "due_date") == "2027-03-01", pget(pb, "due_date"))
    check("B 취소 없음: 발주일 = MIN 2026-10-01 (예전과 같음)", pget(pb, "order_date") == "2026-10-01", pget(pb, "order_date"))
    check("B 취소 없음: 호기 3 · 통화 혼합 2 · 경고 있음 (예전과 같음)",
          len(cap.get("all_units_sorted") or []) == 3 and len(cap.get("currency_mix") or []) == 2 and bool(cap.get("currency_warning")),
          (len(cap.get("all_units_sorted") or []), cap.get("currency_mix")))

    print("§1b 빠른 수정 화면 열기")
    cl.get("/projects/%d/quick-edit" % pc)
    check("C 정보 수정 화면 열기만으로는 저장 안 함(z1191z153)", pget(pc, "due_date") != "2026-12-10", pget(pc, "due_date"))
    cl.post("/project/%d/heal" % pc)
    check("C 취소 있음: 납기 2026-12-10 · 발주일 2026-11-01", (pget(pc, "due_date"), pget(pc, "order_date")) == ("2026-12-10", "2026-11-01"),
          (pget(pc, "due_date"), pget(pc, "order_date")))
    cl.get("/projects/%d/quick-edit" % pd_)
    cl.post("/project/%d/heal" % pd_)
    check("D 취소 없음: 납기 MAX 2027-03-01 · 발주일 MIN 2026-10-01 (예전과 같음)",
          (pget(pd_, "due_date"), pget(pd_, "order_date")) == ("2027-03-01", "2026-10-01"), (pget(pd_, "due_date"), pget(pd_, "order_date")))

    print("§2 제작요청서 납기")
    with D.db_session() as c:
        c.execute("UPDATE projects SET due_date='2027-03-01' WHERE id=?", (pb,))
        rd = M._z132_req_due
        check("고른 수주 하나(납기 2026-12-10) → 2026-12-10", rd(c, [ob[0]], "2027-03-01") == "2026-12-10", rd(c, [ob[0]], "2027-03-01"))
        check("고른 수주 둘 → 가장 늦은 2027-03-01", rd(c, ob, "2000-01-01") == "2027-03-01")
        check("고른 수주 없음 → 프로젝트 납기(예전과 같음)", rd(c, [], "2027-03-01") == "2027-03-01")
        check("고른 수주가 취소 수주뿐 → 프로젝트 납기", rd(c, [oa[1]], "2026-12-31") == "2026-12-31", rd(c, [oa[1]], "2026-12-31"))
        c.execute("UPDATE orders SET due_date='' WHERE id=?", (od_[0],))
        check("고른 수주 납기 빈칸 → 프로젝트 납기", rd(c, [od_[0]], "2027-03-01") == "2027-03-01")
        p = dict(c.execute("SELECT * FROM projects WHERE id=?", (pb,)).fetchone())
        v = M._z48_view_ctx(c, p, {"id": 999999, "order_ids": str(ob[0]), "created_at": "2026-11-24 10:00"})
        check("요청서 화면: 일정 = 고른 수주 납기 2026-12-10 · D-n 도 그 날 기준",
              v.get("due") == "2026-12-10" and v.get("dday") == M._z48_dday("2026-12-10"), (v.get("due"), v.get("dday")))
        v0 = M._z48_view_ctx(c, p, None)
        check("새로 쓸 때(요청서 없음) = 프로젝트 납기(예전과 같음)", v0.get("due") == "2027-03-01" and v0.get("dday") == M._z48_dday("2027-03-01"))
        it = M._z49_item(c, p, str(ob[0]), "2026-11-24 10:00")
        check("묶음 줄: 일정 = 고른 수주 납기", it["due"] == "2026-12-10" and it["dday"] == M._z48_dday("2026-12-10"), (it["due"], it["dday"]))
        it0 = M._z49_item(c, p, "", "")
        check("묶음 줄 고른 수주 없음 = 프로젝트 납기(예전과 같음)", it0["due"] == "2027-03-01")

    print("§3 매출 홈 「진행 프로젝트」")
    with D.db_session() as c:
        # A 의 「취소」 호기 납기를 가장 이르게 → 빼지 않으면 납기가 앞당겨진다
        c.execute("UPDATE order_items SET due_date='2026-01-05' WHERE id=?", (ia[oa[0]][2],))
        op = {d["code"]: d for d in M._z40_open_projects(c)["projects"]}
    a3 = op.get("001T2699") or {}
    check("A: 출하 전 품목 2(「취소」 호기 뺌 · 예전 3)", a3.get("n_open") == 2, a3.get("n_open"))
    check("A: 가장 이른 납기는 「취소」 호기 날짜(2026-01-05)가 아님", a3.get("due") == "2026-12-10", a3.get("due"))
    b3 = op.get("002T2699") or {}
    check("B 취소 없음: 출하 전 품목 3 · 수주번호 2 (예전과 같음)", b3.get("n_open") == 3 and len(b3.get("so_list") or []) == 2, (b3.get("n_open"), b3.get("so_list")))
    with D.db_session() as c:
        # A 의 살아 있는 호기 둘을 출하 → 남은 건 「취소」 호기뿐 → 진행 프로젝트에서 빠짐
        c.execute("UPDATE order_items SET unit_status='출하' WHERE id IN (?,?)", tuple(ia[oa[0]][:2]))
        op2 = {d["code"]: d for d in M._z40_open_projects(c)["projects"]}
        c.execute("UPDATE order_items SET unit_status='진행중' WHERE id IN (?,?)", tuple(ia[oa[0]][:2]))
    check("A: 남은 게 「취소」 호기뿐이면 진행 프로젝트에서 빠짐", "001T2699" not in op2)

    print("§4 매출 3종 · 매출 보고서")
    with D.db_session() as c:
        # 금액 확인 쉽게 — 프로젝트 B 의 USD 수주를 KRW 로(환율 없이 비교)
        c.execute("UPDATE orders SET currency='KRW' WHERE id=?", (ob[1],))
        c.execute("UPDATE order_items SET currency='KRW' WHERE order_id=?", (ob[1],))
        c.execute("UPDATE orders SET currency='KRW' WHERE id=?", (oa[1],))
        c.execute("UPDATE order_items SET currency='KRW' WHERE order_id=?", (oa[1],))
        # 다른 프로젝트(C·D)는 매출에서 빼 두고(폐기) A·B 만 본다
        c.execute("UPDATE projects SET is_archived=1 WHERE id IN (?,?)", (pc, pd_))
        # 출하 한 줄씩(진행매출 확인용): A 1호기 · B 1호기
        c.execute("UPDATE order_items SET unit_status='출하', status_date='2026-11-20' WHERE id IN (?,?)", (ia[oa[0]][0], ib[ob[0]][0]))
        rates = M._fx_load_rates(c)
        oi_map = {ia[oa[0]][0]: {"t1d": "2026-11-21", "t1a": 100},     # A 살아 있는 호기 발행
                  ia[oa[0]][2]: {"t1d": "2026-11-21", "t1a": 100},     # A 「취소」 호기 발행칸(빼야 함)
                  ib[ob[0]][0]: {"t1d": "2026-11-21", "t1a": 100}}     # B 발행
        k = M._sales_3way(c, rates, oi_map, "year", "2026", "1", "1")["kpi"]
        # A 만 / B 만 따로 — 폐기로 하나씩 가린다
        c.execute("UPDATE projects SET is_archived=1 WHERE id=?", (pb,))
        ka = M._sales_3way(c, rates, oi_map, "year", "2026", "1", "1")["kpi"]
        la = {b: sum(x["krw"] for x in M._z17_lines(c, rates, oi_map, b)[0] if x.get("kind") == "project") for b in ("order", "ship", "tax")}
        c.execute("UPDATE projects SET is_archived=0 WHERE id=?", (pb,))
        c.execute("UPDATE projects SET is_archived=1 WHERE id=?", (pa,))
        kb = M._sales_3way(c, rates, oi_map, "year", "2026", "1", "1")["kpi"]
        lb = {b: sum(x["krw"] for x in M._z17_lines(c, rates, oi_map, b)[0] if x.get("kind") == "project") for b in ("order", "ship", "tax")}
        c.execute("UPDATE projects SET is_archived=0 WHERE id=?", (pa,))
    check("A ① 수주매출 = 200(「취소」 호기 100·취소 수주 500 뺌 · 예전 300)", round(ka["order"]) == 200, ka["order"])
    check("A ② 진행매출 = 100(출하 1줄 · 바뀌지 않음)", round(ka["prog"]) == 100, ka["prog"])
    check("A ③ 최종매출 = 100(「취소」 호기 발행칸 뺌 · 예전 200)", round(ka["final"]) == 100, ka["final"])
    check("B 취소 없음: ① 700 · ② 100 · ③ 100 (예전과 같음)",
          (round(kb["order"]), round(kb["prog"]), round(kb["final"])) == (700, 100, 100), (kb["order"], kb["prog"], kb["final"]))
    check("A+B 합 = 각각의 합", round(k["order"]) == 900 and round(k["final"]) == 200, (k["order"], k["final"]))
    check("매출 보고서(_z17_lines)도 같은 기준 — A 수주 200 · 출하 100 · 발행 100", (round(la["order"]), round(la["ship"]), round(la["tax"])) == (200, 100, 100), la)
    check("매출 보고서 B 취소 없음 — 700 · 100 · 100 (예전과 같음)", (round(lb["order"]), round(lb["ship"]), round(lb["tax"])) == (700, 100, 100), lb)

    print("§6 수량 줄 합")
    so = {"board_qty": 2, "units": [{"qty": 2, "unit_status": "진행중"}, {"qty": 3, "unit_status": "취소"}]}
    check("「취소」 줄 수량 뺌: 2(예전 5)", M._so_qty_lines_z89(so) == 2, M._so_qty_lines_z89(so))
    check("줄 합 = 등록 수량이면 「(품목 줄 합 N)」 안 띄움(예전엔 「(품목 줄 합 5)」)", M._so_qty_note_z89(so) == "", M._so_qty_note_z89(so))
    so2 = {"board_qty": 2, "units": [{"qty": 5, "unit_status": "진행중"}]}
    check("취소 없음: 줄 합 5 · 「(품목 줄 합 5)」 (예전과 같음)", M._so_qty_lines_z89(so2) == 5 and M._so_qty_note_z89(so2) == "(품목 줄 합 5)")
    so3 = {"units": [{"qty": 1}, {"qty": 2, "unit_status": None}]}
    check("상태 없는 줄은 그대로 셈(3)", M._so_qty_lines_z89(so3) == 3)

    print("§7 프로젝트 종합 상태(메모리 sqlite)")
    from app import project_workflow as W
    m = sqlite3.connect(":memory:")
    m.row_factory = sqlite3.Row
    m.execute("CREATE TABLE orders(id INTEGER PRIMARY KEY, project_id INT, status TEXT)")
    m.execute("CREATE TABLE order_items(id INTEGER PRIMARY KEY, order_id INT, unit_status TEXT)")
    for oid, pid, st, us in ((10, 1, "CONFIRMED", ["출하", "진행중"]), (11, 1, "CANCELLED", ["진행중", "진행중"]),
                             (20, 2, "CANCELLED", ["진행중"]),
                             (30, 3, "CONFIRMED", ["출하", "진행중"]), (31, 3, "SHIPPED", ["출하", None]),
                             (40, 4, "SHIPPED", ["출하", "출하"])):
        m.execute("INSERT INTO orders VALUES(?,?,?)", (oid, pid, st))
        for u in us:
            m.execute("INSERT INTO order_items(order_id, unit_status) VALUES(?,?)", (oid, u))

    def old_counts(pid):   # 예전 단건 함수 그대로의 셈
        return {r["st"]: r["n"] for r in m.execute(
            "SELECT COALESCE(oi.unit_status,'진행중') AS st, COUNT(*) AS n FROM order_items oi JOIN orders o ON o.id=oi.order_id "
            "WHERE o.project_id=? GROUP BY COALESCE(oi.unit_status,'진행중')", (pid,))}
    s1 = W.compute_project_display_status(m, 1, "제안")
    check("1: 취소 수주 호기 뺌 → 「진행중 (1/2 완료)」(예전 1/4)", s1["label"] == "진행중 (1/2 완료)" and s1["total"] == 2, (s1["label"], s1["total"]))
    s2 = W.compute_project_display_status(m, 2, "제안")
    check("2: 수주가 모두 취소 → 「취소」", s2["label"] == "취소" and s2["tone"] == "danger", s2["label"])
    s3 = W.compute_project_display_status(m, 3, "제안")
    o3 = W.project_status_from_counts(old_counts(3), "제안")
    check("3 취소 없음: 예전 셈과 같은 결과", s3 == o3 and s3["label"] == "진행중 (2/4 완료)", (s3["label"], o3["label"]))
    s4 = W.compute_project_display_status(m, 4, "제안")
    check("4 취소 없음 모두 출하: 「출하」 (예전과 같음)", s4 == W.project_status_from_counts(old_counts(4), "제안") and s4["label"] == "출하")
    bk = W.compute_project_display_status_bulk(m)
    check("벌크 = 단건(1·2·3·4 모두 같은 라벨·숫자)",
          all(W.project_status_from_counts(bk.get(p), "제안") == W.compute_project_display_status(m, p, "제안") for p in (1, 2, 3, 4)),
          {p: bk.get(p) for p in (1, 2, 3, 4)})
    check("벌크 취소 없음(3·4) = 예전 셈 그대로", bk.get(3) == old_counts(3) and bk.get(4) == old_counts(4), (bk.get(3), old_counts(3)))
    bk2 = W.compute_project_display_status_bulk(m, [1, 3])
    check("벌크 일부만 → 그 프로젝트만", set(bk2) == {1, 3})

    print("§8 글자 확인")
    src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
    check("빠른 수정 화면 납기·발주일 맞추기에 취소 수주 제외",
          'dues = [o.get("due_date") for o in sos if o.get("due_date")\n                        and str(o.get("status") or "").upper() != "CANCELLED"]' in src
          and 'ords = [o.get("order_date") for o in sos if o.get("order_date")\n                        and str(o.get("status") or "").upper() != "CANCELLED"]' in src)
    check("제작요청 알림 본문 납기 = 고른 수주 납기(_z132_req_due · 저장되는 order_ids)",
          "due = _z132_req_due(_c132, _z48_ids(_z48_oid_csv), p.get(\"due_date\")) or \"—\"" in src
          and '_d49 = _m.get("due132") or' in src)
    T = open(os.path.join(ROOT, "app", "templates", "prod_request_edit.html"), encoding="utf-8").read()
    check("제작요청서 화면 일정 칸 두 곳 = z48.due 먼저", T.count("(z48.due or p.due_date or '')[:10] or '—'") == 2)
    check("고친 곳마다 z1191z132 표시", src.count("z1191z132") >= 12, src.count("z1191z132"))

    print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
    return 0 if all(R) else 1


if __name__ == "__main__":
    sys.exit(main())
