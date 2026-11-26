# -*- coding: utf-8 -*-
"""z1191z156 시험 — 견적서·고객 발주서 = 수주번호(orders.id)에만 붙인다 (대표 11-25 정하고 11-26 「진행하자」)
  §1 상세 「＋ 견적서 엑셀 올리기」: 수주 1개 = 그 수주 · 2개 이상 안 고르면 저장 안 함·알림 · 고르면 그 수주에만 · 다른 관리번호 수주 막음 · 수주 없음 막음
  §2 견적 관리(올리기→자리 후보→붙이기): 후보·찾기에 관리번호 자리 없음 · 수주번호 없이 붙이기 막음
  §3 등록 화면 [등록] = 이번에 만든 수주 · 추가 발주 = 새 수주(앞 수주 아님) · 수정 화면 [저장] = 고른 수주(안 고르면 붙이지 않음)
  §4 고객 발주서(상세·견적 관리): 같은 규칙
  §5 관리번호에만 붙는 줄(order_id NULL)이 새로 생기지 않음 · 등록 전 임시 파일은 그대로
  §6 옛 order_id 없는 견적서·발주서 = 저절로 안 붙음 · 판정에 안 씀 · 「⚠ 수주 칸 확인 필요」에 나옴 · 열기만으로 저장 안 함 · 사람이 고르면 붙음·이력
  §7 화면(상세·견적 관리·수정 화면·확인 필요) · 「대표 견적」 말 없음 · 화면 스크립트 문법(node)
  임시 DB · TestClient · 운영 아님"""
import contextlib
import io
import os
import re
import subprocess
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z156-test-only-not-a-real-key"   # 시험용 가짜 값
import app.database as D  # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z156_")
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
    tcols = {r[1] for r in conn.execute("PRAGMA table_info(teams)")}
    if not conn.execute("SELECT 1 FROM teams WHERE id=1").fetchone():
        if "code" in tcols:
            conn.execute("INSERT INTO teams (id, code, name) VALUES (1, '01', '기술영업팀')")
        else:
            conn.execute("INSERT INTO teams (id, name) VALUES (1, '기술영업팀')")
    else:
        conn.execute("UPDATE teams SET name='기술영업팀' WHERE id=1")
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, can_view_sales, can_use_sales, "
                 "can_view_logistics, can_use_logistics) VALUES ('가상영업', 'admin', 'Z156', 'Z156', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z156'").fetchone())
    conn.execute("INSERT OR IGNORE INTO field_access_policy (category, team_id) VALUES ('sales_amount', 1)")
    conn.execute("INSERT INTO customers (name) VALUES ('가상고객갑')")
    CU = conn.execute("SELECT id FROM customers WHERE name='가상고객갑'").fetchone()[0]
    from datetime import date as _d
    T0 = _d.today().isoformat()

    def proj(code, name):
        conn.execute("INSERT INTO projects (mgmt_code, name, customer_id, customer_name, currency, order_amount, order_date, due_date, stage, sales_name) "
                     "VALUES (?, ?, ?, '가상고객갑', 'KRW', 0, ?, ?, '수주확정', '가상영업')", (code, name, CU, T0, T0))
        return conn.execute("SELECT id FROM projects WHERE mgmt_code=?", (code,)).fetchone()[0]

    def so(pid, no, amt, label, st="CONFIRMED"):
        conn.execute("INSERT INTO orders (project_id, order_no, customer_id, currency, total_amount, order_date, due_date, status) "
                     "VALUES (?, ?, ?, 'KRW', ?, ?, ?, ?)", (pid, no, CU, amt, T0, T0, st))
        oid = conn.execute("SELECT id FROM orders WHERE order_no=?", (no,)).fetchone()[0]
        conn.execute("INSERT INTO order_items (order_id, amount, unit_price, unit_label) VALUES (?, ?, ?, ?)", (oid, amt, amt, label))
        return oid

    P1 = proj("961M2611", "수주 하나")
    O11 = so(P1, "Z-261126-1", 1000000, "1호기")
    P2 = proj("962M2611", "수주 둘")
    O21 = so(P2, "Z-261126-2", 2000000, "1호기")
    O22 = so(P2, "Z-261126-3", 3000000, "2호기")
    OX = so(P2, "Z-261126-9", 9, "취소", st="CANCELLED")
    P0 = proj("963M2611", "수주 없음")
    PL = proj("964M2611", "옛 자료(수주 넷)")
    OL = [so(PL, "Z-2611L-%d" % i, 1000000 * i, "%d호기" % i) for i in (1, 2, 3, 4)]

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

M.get_user = lambda request: ADMIN
FAKE = {"fields": {}}
M._qr61.read_quote = lambda raw, name, pw="": {"ok": True, "fields": dict(FAKE["fields"]), "warnings": []}
cl = TestClient(M.app, follow_redirects=False)
XL = b"PK\x03\x04" + b"0" * 64
PDF = b"%PDF-1.4 test"
R = []


def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:400]))


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def rows(sql, *a):
    with D.db_session() as c:
        return [tuple(r) for r in c.execute(sql, a).fetchall()]


def qfiles(pid):
    return rows("SELECT order_id, orig_name FROM project_quote_files WHERE project_id=? ORDER BY id", pid)


def pfiles(pid):
    return rows("SELECT order_id, orig_name FROM project_po_files WHERE project_id=? ORDER BY id", pid)


def attach(pid, name, oid=None, fields=None):
    FAKE["fields"] = fields or {"amount": 1000000, "currency": "KRW"}
    data = {"order_id": str(oid)} if oid else {}
    return q(cl.post, "/api/project-quote/attach/%d" % pid, data=data, files={"file": (name, XL, "application/vnd.ms-excel")}).json()


def nfiles_on_disk():
    n = 0
    for base in (M._z61_dir(), M._z143_dir()):
        for _r, _d2, fs in os.walk(base):
            n += len(fs)
    return n


# 옛 자료(운영 003M2509 같은 1건): 관리번호에만 붙은 견적서·발주서 · 등록 전 임시 파일(project_id 없음)
with D.db_session() as c:
    M._z61_table(c)
    M._po143.table(c)
    c.execute("INSERT INTO project_quote_files(tok, project_id, order_id, orig_name, stored, by_id, by_name, created_at, attached_at, read_json) "
              "VALUES('legacyq', ?, NULL, '옛_관리번호견적.xlsx', '202609/legacyq.xlsx', ?, '가상영업', '2026-09-01 10:00', '2026-09-01 10:00', ?)",
              (PL, ADMIN["id"], '{"fields": {"amount": 1000000, "currency": "KRW"}}'))
    LQ = c.execute("SELECT id FROM project_quote_files WHERE tok='legacyq'").fetchone()[0]
    c.execute("INSERT INTO project_po_files(tok, project_id, order_id, orig_name, stored, kind, by_id, by_name, created_at) "
              "VALUES('legacyp', ?, NULL, '옛_관리번호발주서.pdf', '202609/legacyp.pdf', 'pdf', ?, '가상영업', '2026-09-01 10:00')", (PL, ADMIN["id"]))
    LP = c.execute("SELECT id FROM project_po_files WHERE tok='legacyp'").fetchone()[0]
    from datetime import datetime as _dt
    _now = _dt.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO project_quote_files(tok, project_id, order_id, orig_name, stored, by_id, created_at) "
              "VALUES('tmpq', NULL, NULL, '등록전_임시.xlsx', '202611/tmpq.xlsx', ?, ?)", (ADMIN["id"], _now))
    c.execute("INSERT INTO project_po_files(tok, project_id, order_id, orig_name, stored, kind, by_id, created_at) "
              "VALUES('tmpp', NULL, NULL, '등록전_임시.pdf', '202611/tmpp.pdf', 'pdf', ?, ?)", (ADMIN["id"], _now))

print("§1 상세 「＋ 견적서 엑셀 올리기」")
j = attach(P1, "견적_하나.xlsx")
check("수주 1개 · 안 골라도 = 그 수주에 붙음", j.get("ok") and j.get("order_id") == O11 and j.get("slot") == "Z-261126-1" and qfiles(P1) == [(O11, "견적_하나.xlsx")], (j, qfiles(P1)))
n0 = nfiles_on_disk()
j = attach(P2, "견적_둘_안고름.xlsx")
check("수주 2개 · 안 고르면 저장 안 함 · 「👉 수주번호를 골라 주세요」", (not j.get("ok")) and j.get("need_so") and "👉 수주번호를 골라 주세요" in (j.get("message") or "")
      and qfiles(P2) == [] and nfiles_on_disk() == n0, (j, qfiles(P2)))
check("멈춤 답에 고를 수주 2개(취소 수주 뺌)", [o["id"] for o in j.get("sos") or []] == [O21, O22], j.get("sos"))
j = attach(P2, "견적_둘_2호기.xlsx", O22, {"amount": 2500000, "currency": "KRW"})
check("고르면 그 수주에만(2호기) · 1호기 수주엔 없음", j.get("ok") and qfiles(P2) == [(O22, "견적_둘_2호기.xlsx")], qfiles(P2))
check("올린 순간 이 수주 금액 다름 알림(via own)", j.get("diff_sos") == ["Z-261126-3"], j)
check("변경 이력에 어느 수주인지", rows("SELECT COUNT(*) FROM project_history WHERE project_id=? AND note LIKE '%수주 Z-261126-3%'", P2)[0][0] >= 1)
j = attach(P2, "견적_남의수주.xlsx", O11)
check("다른 관리번호의 수주번호 = 막음(저장 안 함)", (not j.get("ok")) and j.get("need_so") and len(qfiles(P2)) == 1, (j, qfiles(P2)))
j = attach(P2, "견적_취소수주.xlsx", OX)
check("취소된 수주 = 막음", (not j.get("ok")) and len(qfiles(P2)) == 1, j)
j = attach(P0, "견적_수주없음.xlsx")
check("수주 없는 관리번호 = 막음 · 「수주를 먼저 등록」", (not j.get("ok")) and j.get("no_so") and "수주를 먼저" in (j.get("message") or "") and qfiles(P0) == [], j)
j = attach(P2, "견적_둘_2호기_새판.xlsx", O22, {"amount": 3000000, "currency": "KRW"})
check("같은 수주에 다시 올리면 그 수주 견적만 바뀜(예전 것 지움)", j.get("ok") and j.get("replaced") == 1 and qfiles(P2) == [(O22, "견적_둘_2호기_새판.xlsx")] and not j.get("diff_sos"), (j, qfiles(P2)))

print("§2 견적 관리 — 올리기 → 수주번호 고르기 → 붙이기")
FAKE["fields"] = {"amount": 2000000, "currency": "KRW"}
rd = q(cl.post, "/api/project-quote/read", files={"file": ("962M2611_견적.xlsx", XL, "application/vnd.ms-excel")}).json()
cd = q(cl.get, "/api/quotes-z105/cands?tok=" + rd["tok"]).json()
check("관리번호만 적힌 파일 → 후보 = 그 관리번호의 수주번호들만(관리번호 자리 없음) · 금액이 같아도 미리 안 고름(빈칸 · 「금액 같음」 표시만)",
      sorted(x["oid"] for x in cd.get("cands") or []) == [O21, O22] and cd.get("pick") is None
      and [x["same"] for x in cd["cands"] if x["oid"] == O21] == [True], cd)
check("수주 1개 관리번호 파일 → 그 수주 하나 · 미리 고름",
      (lambda c2: [x["oid"] for x in c2.get("cands") or []] == [O11] and c2.get("pick") == 0)(
          q(cl.get, "/api/quotes-z105/cands?tok=" + q(cl.post, "/api/project-quote/read", files={"file": ("961M2611.xlsx", XL, "application/vnd.ms-excel")}).json()["tok"]).json()))
sr = q(cl.get, "/api/quotes-z105/search?q=962M2611").json()
it = sr.get("items") or []
check("찾기: 관리번호 줄 = 머리 글(head · 고를 수 없음) · 나머지는 모두 수주번호",
      it and it[0].get("head") and it[0].get("oid") is None and all(x.get("oid") for x in it[1:]) and "대표" not in it[0]["label"], it)
pl = q(cl.post, "/api/project-quote/place", data={"tok": rd["tok"], "pid": P2}).json()
check("수주번호 없이 붙이기 → 저장 안 함 · 「👉 수주번호를 골라 주세요」", (not pl.get("ok")) and pl.get("need_so")
      and rows("SELECT project_id FROM project_quote_files WHERE tok=?", rd["tok"]) == [(None,)], pl)
pl = q(cl.post, "/api/project-quote/place", data={"tok": rd["tok"], "pid": P2, "order_id": O21}).json()
check("수주번호 고르고 붙이기 → 그 수주에만", pl.get("ok") and pl.get("slot") == "Z-261126-2" and (O21, "962M2611_견적.xlsx") in qfiles(P2), (pl, qfiles(P2)))

print("§3 등록 화면 [등록] · 추가 발주 · 수정 화면 [저장]")
BASE = {"quick": "1", "biz_div": "M", "project_type": "NEW_EQUIP", "status": "진행중", "confirm_now": "1",
        "order_date": T0, "due_date": T0, "currency": "KRW", "equip_name": "가상장비", "unit_qty": "1",
        "shipment_form": "ASSEMBLY", "unit_price": "1000000", "order_amount": "1000000", "unit_amount[]": ["1000000"]}
FAKE["fields"] = {"amount": 1000000, "currency": "KRW"}
t1 = q(cl.post, "/api/project-quote/read", files={"file": ("등록_견적.xlsx", XL, "application/vnd.ms-excel")}).json()["tok"]
q(cl.post, "/projects/new", data=dict(BASE, name="Z156등록", model="MZ156", customer_name="가상고객갑", po_type="신규", quote_tok=t1))
PN = rows("SELECT id, mgmt_code FROM projects WHERE name='Z156등록'")
check("새 등록 됨", len(PN) == 1, PN)
PN, CODE = PN[0]
SO1 = rows("SELECT id FROM orders WHERE project_id=? ORDER BY id", PN)
check("새 등록 견적서 = 이번에 만든 수주번호에 붙음", len(SO1) == 1 and qfiles(PN) == [(SO1[0][0], "등록_견적.xlsx")], (SO1, qfiles(PN)))
t2 = q(cl.post, "/api/project-quote/read", files={"file": ("추가발주_견적.xlsx", XL, "application/vnd.ms-excel")}).json()["tok"]
q(cl.post, "/projects/new", data=dict(BASE, name="Z156등록", model="MZ156", customer_name="가상고객갑", po_type="추가", mgmt_code=CODE, quote_tok=t2))
SO2 = rows("SELECT id FROM orders WHERE project_id=? ORDER BY id", PN)
check("추가 발주(같은 관리번호에 새 수주) 견적서 = 새 수주에 붙음(앞 수주 아님)",
      len(SO2) == 2 and (SO2[1][0], "추가발주_견적.xlsx") in qfiles(PN) and (SO2[0][0], "등록_견적.xlsx") in qfiles(PN), (SO2, qfiles(PN)))
t3 = q(cl.post, "/api/project-quote/read", files={"file": ("수정_견적.xlsx", XL, "application/vnd.ms-excel")}).json()["tok"]
check("수정 [저장] · 수주 2개 · 안 고름 → 붙이지 않음(\"need_so\") · 파일은 그대로 남김", q(M._z61_attach, P2, t3, ADMIN) == "need_so"
      and rows("SELECT project_id FROM project_quote_files WHERE tok=?", t3) == [(None,)])
check("수정 [저장] · 고른 수주(1호기)에 붙음", q(M._z61_attach, P2, t3, ADMIN, order_id=str(O21)) is True
      and rows("SELECT order_id FROM project_quote_files WHERE tok=?", t3) == [(O21,)])
t4 = q(cl.post, "/api/project-quote/read", files={"file": ("수정_하나.xlsx", XL, "application/vnd.ms-excel")}).json()["tok"]
check("수정 [저장] · 수주 1개 · 안 골라도 그 수주", q(M._z61_attach, P1, t4, ADMIN) is True and rows("SELECT order_id FROM project_quote_files WHERE tok=?", t4) == [(O11,)])
src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check("수정 화면 경로: quote_order_id 넘김 · 못 붙였으면 상세에서 「👉」 알림", 'order_id=form.get("quote_order_id")' in src and '?z156=need_so' in src)

print("§4 고객 발주서")
up = lambda data, name="발주서.pdf": q(cl.post, "/api/customer-po/upload", data=data, files={"file": (name, PDF, "application/pdf")}).json()
j = up({"pid": P1})
check("상세: 수주 1개 · 안 골라도 그 수주", j.get("ok") and j.get("placed") and pfiles(P1) == [(O11, "발주서.pdf")], (j, pfiles(P1)))
n0 = nfiles_on_disk()
j = up({"pid": P2})
check("상세: 수주 2개 · 안 고르면 저장 안 함 · 알림", (not j.get("ok")) and j.get("need_so") and pfiles(P2) == [] and nfiles_on_disk() == n0, (j, pfiles(P2)))
j = up({"pid": P2, "order_id": O22})
check("상세: 고르면 그 수주에만", j.get("ok") and pfiles(P2) == [(O22, "발주서.pdf")], pfiles(P2))
j = up({"pid": P0})
check("상세: 수주 없는 관리번호 = 막음", (not j.get("ok")) and j.get("no_so") and pfiles(P0) == [], j)
j = up({}, "962M2611_PO.pdf")
check("견적 관리: 관리번호만 적힌 파일 → 후보 = 수주번호들만 · 미리 안 고름",
      j.get("ok") and not j.get("placed") and [x["oid"] for x in j.get("cands") or []] == [O21, O22] and j.get("pick") is None, j)
pp = q(cl.post, "/api/customer-po/place", data={"tok": j["tok"], "pid": P2}).json()
check("견적 관리: 수주번호 없이 붙이기 → 저장 안 함", (not pp.get("ok")) and pp.get("need_so")
      and rows("SELECT project_id FROM project_po_files WHERE tok=?", j["tok"]) == [(None,)], pp)
pp = q(cl.post, "/api/customer-po/place", data={"tok": j["tok"], "pid": P2, "order_id": O21}).json()
check("견적 관리: 고르면 그 수주에만", pp.get("ok") and (O21, "962M2611_PO.pdf") in pfiles(P2), (pp, pfiles(P2)))
sr = q(cl.get, "/api/customer-po/search?q=962M2611").json().get("items") or []
check("발주서 찾기: 관리번호 줄 = 머리 글 · 나머지는 수주번호", sr and sr[0].get("head") and all(x.get("oid") for x in sr[1:]), sr)
with D.db_session() as c:
    cs, pk, _w = M._z143_cands(c, "961M2611 발주.pdf")
check("발주서 자리 후보: 수주 1개 관리번호 = 그 수주 하나 · 미리 고름", [x["oid"] for x in cs] == [O11] and pk == 0, cs)

print("§5 관리번호에만 붙는 줄이 새로 생기지 않음")
check("견적서: order_id 없는 붙은 줄 = 옛 1건뿐", rows("SELECT id FROM project_quote_files WHERE project_id IS NOT NULL AND order_id IS NULL") == [(LQ,)])
check("발주서: order_id 없는 붙은 줄 = 옛 1건뿐", rows("SELECT id FROM project_po_files WHERE project_id IS NOT NULL AND order_id IS NULL") == [(LP,)])
check("등록 전 임시 파일(project_id 없음)은 그대로", rows("SELECT COUNT(*) FROM project_quote_files WHERE tok='tmpq' AND project_id IS NULL")[0][0] == 1
      and rows("SELECT COUNT(*) FROM project_po_files WHERE tok='tmpp' AND project_id IS NULL")[0][0] == 1)
blk = src[src.index("# ═══ z1191z156"):]
check("코드: 견적서를 붙이는 곳에 order_id=NULL·IS NULL 자리 고르기가 남지 않음",
      "order_id=NULL" not in src and "_z105_slot_rows(c, int(pid), None)" not in src and "_proj_slot" not in src)

print("§6 옛 order_id 없는 견적서·발주서")
with D.db_session() as c:
    st = M._z141_project(c, PL)
check("판정에 안 씀: 수주 넷 모두 「없음」(관리번호 견적서를 따라가지 않음 · via proj 없음)",
      all(st[o]["st"] == "none" and st[o]["via"] != "proj" for o in OL), st)
d150 = M._z150_one(PL)
check("모아 보기: 옛 견적서는 pq 로 보이기만 · 견적 없는 수주 4", d150["pq"] and d150["pq"]["id"] == LQ and d150["miss_q"] == 4, d150 and d150["miss_q"])


def fp():
    return (rows("SELECT COUNT(*) FROM project_history")[0][0], rows("SELECT group_concat(COALESCE(order_id,'∅')) FROM project_quote_files")[0][0],
            rows("SELECT group_concat(COALESCE(order_id,'∅')) FROM project_po_files")[0][0])


f0 = fp()
h = q(cl.get, "/projects/so-check").text
check("확인 필요 화면: 옛 견적서·발주서 둘 다 나옴 · 수주번호 고르기 칸", "옛_관리번호견적.xlsx" in h and "옛_관리번호발주서.pdf" in h
      and "z156-fsel" in h and "— 수주번호 고르기 —" in h and "등록전_임시" not in h, h[:200])
check("확인 필요 화면: 단계 줄(전체 순서·지금 할 일) · ✕ 닫기", "z156FileStep" in h and "👉 지금 하실 일" in h and "닫기" in h)
check("확인 필요 화면을 열기만 해서는 아무것도 저장 안 함", fp() == f0, (fp(), f0))
with D.db_session() as c:
    check("확인 필요 수 = 수주 칸 + 파일 2건", M._z154_check_count(c) == len(M._z154_check_rows(c)) + 2)
r = q(cl.post, "/api/so-check-file/quote/%d" % LQ, data={}).json()
check("안 고르고 누르면 저장 안 함(수주 넷)", (not r.get("ok")) and r.get("need_so") and fp() == f0, r)
r = q(cl.post, "/api/so-check-file/quote/%d" % LQ, data={"order_id": O11}).json()
check("다른 관리번호 수주 = 막음", not r.get("ok") and fp() == f0, r)
with D.db_session() as c:   # 3호기에는 이미 견적서가 있다
    c.execute("INSERT INTO project_quote_files(tok, project_id, order_id, orig_name, stored, by_id, created_at, attached_at) "
              "VALUES('l3', ?, ?, '3호기_견적.xlsx', '202611/l3.xlsx', ?, '2026-11-20 10:00', '2026-11-20 10:00')", (PL, OL[2], ADMIN["id"]))
f0 = fp()
rr = q(cl.post, "/api/so-check-file/quote/%d" % LQ, data={"order_id": OL[2]})
r = rr.json()
check("그 수주에 이미 견적서가 있으면 멈춤(저절로 지우지 않음) · 「👉」", rr.status_code == 409 and not r.get("ok") and "👉" in (r.get("message") or "") and fp() == f0, r)
r = q(cl.post, "/api/so-check-file/quote/%d" % LQ, data={"order_id": OL[1]}).json()
check("사람이 고른 수주(2호기)에 붙음", r.get("ok") and r.get("shown") == "Z-2611L-2" and rows("SELECT order_id FROM project_quote_files WHERE id=?", LQ) == [(OL[1],)], r)
check("이력: 누가·어느 파일·어느 수주", rows("SELECT COUNT(*) FROM project_history WHERE project_id=? AND field='견적서 파일 수주번호' AND new_value='Z-2611L-2' "
                                   "AND note LIKE '%옛_관리번호견적.xlsx%' AND changed_by=?", PL, ADMIN["id"])[0][0] == 1)
r = q(cl.post, "/api/so-check-file/quote/%d" % LQ, data={"order_id": OL[0]})
check("두 번 누르면 409(이미 정해짐)", r.status_code == 409)
with D.db_session() as c:
    st = M._z141_project(c, PL)
check("붙인 뒤 = 2호기 「이 수주 견적」으로 판정", st[OL[1]]["via"] == "own" and st[OL[1]]["f"]["id"] == LQ, st[OL[1]])
r = q(cl.post, "/api/so-check-file/po/%d" % LP, data={"order_id": OL[3]}).json()
check("옛 발주서 → 고른 수주(4호기)에 붙음 · 이력", r.get("ok") and rows("SELECT order_id FROM project_po_files WHERE id=?", LP) == [(OL[3],)]
      and rows("SELECT COUNT(*) FROM project_history WHERE project_id=? AND field='고객 발주서 수주번호'", PL)[0][0] == 1, r)
h = q(cl.get, "/projects/so-check").text
check("다 고르면 확인 필요 화면에서 빠짐", "옛_관리번호견적.xlsx" not in h and "옛_관리번호발주서.pdf" not in h)

print("§7 화면")
h2 = q(cl.get, "/project/%d" % P2).text
check("상세(수주 2개): 견적서 칸 = 수주번호 고르기(빈칸으로 시작) · 단계 줄", 'class="z156-so-sel"' in h2 and "— 수주번호 고르기 —" in h2 and "z156QStep" in h2
      and "👉 지금 하실 일" in h2, "")
check("상세: 고객 발주서 칸도 수주번호 고르기", "z156PStep%d" % P2 in h2 and h2.count('class="z156-so-sel"') >= 2)
check("상세: 견적서 줄마다 수주번호", "Z-261126-3" in h2 and ">견적서</dt>" in h2)
h1 = q(cl.get, "/project/%d" % P1).text
check("상세(수주 1개): 그 수주가 미리 골라져 있음", re.search(r'<option value="%d" selected>Z-261126-1' % O11, h1) is not None)
h0 = q(cl.get, "/project/%d" % P0).text
check("상세(수주 없음): 「아직 수주번호가 없어」 · 올리기 단추 없음", "아직 수주번호가 없어 견적서를 올릴 수 없습니다" in h0 and "z62-up-btn" not in h0)
hn = q(cl.get, "/project/%d?z156=need_so" % P2).text
check("상세: 수정 화면에서 못 붙였을 때 「👉 남은 일」", "수주번호를 고르지 않아 붙이지 않았습니다" in hn)
hq = q(cl.get, "/sales/quotations?period=all").text
check("견적 관리 열림 · 관리번호 줄은 올리는 자리 아님(수주번호 줄만 qm-slot)", 'class="pj qm-slot"' not in hq and 'class="so qm-slot"' in hq)
he = q(cl.get, "/projects/%d/quick-edit" % P2)
check("수정 화면(간편) 열림 · 수주번호 고르기 칸 · 안 고르면 [저장] 멈춤 스크립트", he.status_code == 200 and 'name="quote_order_id"' in he.text and "stopImmediatePropagation" in he.text, he.status_code)
T = lambda *p: open(os.path.join(ROOT, "app", "templates", *p), encoding="utf-8").read()
bad_words = [(n, w) for n in (("sales_quotations.html",), ("project_detail.html",), ("_v5_partials", "quote_fill.html"), ("_v5_partials", "docs_chips.html"),
                               ("_v5_partials", "docs_board_z150.html"), ("quote_view.html",), ("guide.html",), ("sales_order_detail.html",))
             for w in ("대표 견적", "관리번호 대표 견적", "관리번호 견적서</", "모든 수주가 이 견적서를 따라") if w in re.sub(r"\{#.*?#\}|/\*.*?\*/", "", T(*n), flags=re.S)]
check("화면 글에 「대표 견적」·「관리번호 대표」·「모든 수주가 따라감」 없음", not bad_words, bad_words)
check("서버 답 글에도 「관리번호 대표 견적」 없음", "관리번호 대표 견적\"" not in src and "\" · 관리번호 대표 견적 · \"" not in src)

node = None
for cand in ("node", r"C:\Program Files\nodejs\node.exe"):
    try:
        subprocess.run([cand, "--version"], capture_output=True, check=True); node = cand; break
    except Exception:
        pass
if node:
    bad = []
    for rel in (("sales_quotations.html",), ("project_detail.html",), ("so_check_z154.html",), ("sales_order_detail.html",),
                ("_v5_partials", "po_rows.html"), ("_v5_partials", "po_script.html"), ("_v5_partials", "quote_fill.html"),
                ("_v5_partials", "quote_rows.html"), ("_v5_partials", "step_z156.html"), ("_v5_partials", "docs_board_z150.html")):
        s = T(*rel)
        for k, m in enumerate(re.finditer(r"<script(?![^>]*src)[^>]*>(.*?)</script>", s, re.S)):
            b = re.sub(r"\{%.*?%\}", "", m.group(1), flags=re.S); b = re.sub(r"\{\{.*?\}\}", "0", b, flags=re.S); b = re.sub(r"\{#.*?#\}", "", b, flags=re.S)
            fd, fpth = tempfile.mkstemp(suffix=".js"); os.write(fd, b.encode("utf-8")); os.close(fd)
            r = subprocess.run([node, "--check", fpth], capture_output=True, text=True, encoding="utf-8")
            os.remove(fpth)
            if r.returncode:
                bad.append("/".join(rel) + "#%d " % k + r.stderr.strip().split("\n")[0][-160:])
    # 실제로 그려진 화면의 스크립트도(틀 글자 바꾸기 없이)
    for nm, html in (("상세", h2), ("견적 관리", hq), ("수정", he.text), ("확인 필요", q(cl.get, "/projects/so-check").text)):
        for k, m in enumerate(re.finditer(r"<script(?![^>]*src)(?![^>]*type=\"application/(?:ld\+)?json\")[^>]*>(.*?)</script>", html, re.S)):
            fd, fpth = tempfile.mkstemp(suffix=".js"); os.write(fd, m.group(1).encode("utf-8")); os.close(fd)
            r = subprocess.run([node, "--check", fpth], capture_output=True, text=True, encoding="utf-8")
            os.remove(fpth)
            if r.returncode:
                bad.append("그려진 " + nm + "#%d " % k + r.stderr.strip().split("\n")[0][-160:])
    check("바꾼 화면 스크립트 문법 모두 통과(node · 틀 + 그려진 화면)", not bad, bad)
else:
    print("… node 가 없어 스크립트 문법 검사는 건너뜀")

print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
