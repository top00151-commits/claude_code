# -*- coding: utf-8 -*-
"""z1191 · z1191b · z1191c 시험 — 고객사1·2 와 부서 기록을 수주번호 기준으로
   (대표 2026-10-19 「등록할 때부터 발주업체를 관리번호가 아니라 수주번호별로 — 고객사1·고객사2 모두」 · 「부서 기록도 수주번호별로」 · 「진행해」)

  §1 서버(임시 DB · TestClient)
     z1191  신규 등록 첫 수주 2차 · 관리번호 검색 「지난 발주처」 · 정보수정 → 첫 수주(옛 값이 같을 때만) ·
            작업일정표 한 칸(고객사·고객사2·거래구분) = 그 줄의 수주(첫 수주면 대표값도) · 일괄(+PO유형) · 수주 카드 → 대표값
     z1191b 전사일정표 = 수주번호마다 줄(그 수주 발주처) · 부서 기록 = 그 수주(order_id) · 옛 기록 = 첫 수주 줄 · 모아보기 수주번호
     z1191c 상세 맨 위 고객사 「외 n곳」
  §2 실제 화면(Chromium) — 추가 발주 「지난 발주처」 단추(같은 상호 다른 종사업장도 번호로 정확히) · 작업일정표 고객사 칸 ·
     전사일정표 날짜 칸 기록 · 스크립트 오류 0
  §3 바뀐 곳 원문
"""
import contextlib
import io
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
from html.parser import HTMLParser

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
    D.migrate_customers_name_unique()   # 운영은 서버 시작 때 돈다(z619) — 같은 상호 다른 종사업장을 넣으려면 필요
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                     ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                     ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    # z1191g(2026-10-21 대표): 관리자는 역할만으로 매출·자재가 열리지 않는다 → 이 시험의 가상 관리자는 센터 4칸을 켠 관리자로
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상관리자', 'admin', 'T901', 'T901', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T901'").fetchone())
    ccols = {r[1] for r in conn.execute("PRAGMA table_info(customers)")}
    for col in ("alias", "country"):
        if col not in ccols:
            conn.execute("ALTER TABLE customers ADD COLUMN %s TEXT" % col)
    CUST = {}
    # 같은 정식 상호 두 종사업장(DT1·DT2) — 단추는 번호로 정확히 골라야 한다
    for key, name, alias, country in (("VINA", "가상 VINA", "가상 VINA", "Vietnam"),
                                      ("DT1", "(주) 가상드림", "가상드림(동탄)", ""),
                                      ("DT2", "(주) 가상드림", "가상드림(아산)", ""),
                                      ("OTH", "가상기타(주)", "가상기타", "")):
        conn.execute("INSERT INTO customers (name, alias, country) VALUES (?,?,?)", (name, alias, country))
        CUST[key] = conn.execute("SELECT id FROM customers WHERE alias=?", (alias,)).fetchone()[0]
    DSLC = {r[1] for r in conn.execute("PRAGMA table_info(dept_schedule_log)")}

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M.get_user = lambda request: ADMIN
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0
ALIAS = {"VINA": "가상 VINA", "DT1": "가상드림(동탄)", "DT2": "가상드림(아산)", "OTH": "가상기타"}


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


BASE = {"quick": "1", "biz_div": "T", "project_type": "NEW_EQUIP", "status": "진행중", "confirm_now": "1",
        "order_date": "2026-10-02", "due_date": "2026-10-20", "equip_name": "기능검사기", "model": "PBA",
        "unit_qty": "1", "shipment_form": "ASSEMBLY", "currency": "KRW"}


def post(**kw):
    f = dict(BASE)
    f.update(kw)
    with contextlib.redirect_stdout(io.StringIO()):
        r = cl.post("/projects/new", data=f)
    return r.status_code, r.headers.get("location", "")


def proj(pid):
    with D.db_session() as c:
        return dict(c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone())


def proj_by_name(nm):
    with D.db_session() as c:
        r = c.execute("SELECT * FROM projects WHERE name=? ORDER BY id DESC", (nm,)).fetchone()
        return dict(r) if r else None


def orders_of(pid):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT * FROM orders WHERE project_id=? ORDER BY id", (pid,))]


def order(oid):
    with D.db_session() as c:
        return dict(c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone())


def items_of(oid):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT * FROM order_items WHERE order_id=? ORDER BY id", (oid,))]


def new_project(name, ckey, end="", iex="1"):
    kw = dict(name=name, po_type="신규", customer_name=ALIAS[ckey], customer_id=str(CUST[ckey]), is_export=iex,
              unit_price="1000", order_amount="1000", **{"unit_amount[]": ["1000"]})
    if end:
        kw["secondary_customer"] = end
    st, loc = post(**kw)
    return st, loc, proj_by_name(name)


def followup(p, ckey, end=None, iex="0"):
    kw = dict(name=p["name"], po_type="추가", mgmt_code=p["mgmt_code"], customer_name=ALIAS[ckey], customer_id=str(CUST[ckey]),
              is_export=iex, unit_price="2000", order_amount="2000", **{"unit_amount[]": ["2000"]})
    if end is not None:
        kw["secondary_customer"] = end
    before = len(orders_of(p["id"]))
    st, loc = post(**kw)
    new = orders_of(p["id"])[before:]
    return (st == 303 and "error=" not in loc and len(new) == 1), (new[0] if new else None), (st, loc)


def cell(pid, field, value, so_oid="", customer_id="", uids=""):
    with contextlib.redirect_stdout(io.StringIO()):
        r = cl.post("/sales/schedule/cell", json={"kind": "project", "ref_id": pid, "field": field, "value": value,
                                                   "so_oid": str(so_oid), "customer_id": str(customer_id), "uids": uids})
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {}


class FormGrab(HTMLParser):
    """action 이 want 로 끝나는 <form> 안의 칸을 브라우저가 보내는 대로 모은다(z1190c 시험과 같은 것)."""

    def __init__(self, want):
        super().__init__(convert_charrefs=True)
        self.want, self.inform, self.fields, self._sel, self._ta = want, False, [], None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form":
            self.inform = (a.get("action") or "").endswith(self.want)
            return
        if not self.inform or "disabled" in a:
            return
        if tag == "input":
            n, t = a.get("name"), (a.get("type") or "text").lower()
            if not n or t in ("submit", "button", "file", "image", "reset"):
                return
            if t in ("checkbox", "radio") and "checked" not in a:
                return
            self.fields.append((n, a.get("value") if a.get("value") is not None else ("on" if t in ("checkbox", "radio") else "")))
        elif tag == "select":
            self._sel = [a.get("name"), None, None]
        elif tag == "option" and self._sel is not None:
            v = a.get("value") or ""
            if self._sel[2] is None:
                self._sel[2] = v
            if "selected" in a:
                self._sel[1] = v
        elif tag == "textarea":
            self._ta = [a.get("name"), ""]

    def handle_endtag(self, tag):
        if tag == "form":
            self.inform = False
        elif tag == "select" and self._sel is not None:
            if self._sel[0]:
                self.fields.append((self._sel[0], self._sel[1] if self._sel[1] is not None else (self._sel[2] or "")))
            self._sel = None
        elif tag == "textarea" and self._ta is not None:
            if self._ta[0]:
                self.fields.append((self._ta[0], self._ta[1]))
            self._ta = None

    def handle_data(self, data):
        if self._ta is not None:
            self._ta[1] += data


def edit_roundtrip(pid, override):
    r = cl.get("/projects/%d/edit" % pid)
    g = FormGrab("/projects/%d/edit" % pid)
    g.feed(r.text)
    f = {}
    for k, v in g.fields:
        f.setdefault(k, []).append(v)
    f["unlock_verified"] = ["1"]
    p0 = proj(pid)   # 고객사 칸은 「고객 고르기」 스크립트가 숨은 칸을 만들어 채운다
    f.setdefault("customer_name", [p0.get("customer_name") or ""])
    f.setdefault("customer_id", [str(p0.get("customer_id") or "")])
    for k, v in override.items():
        f[k] = [v]
    with contextlib.redirect_stdout(io.StringIO()):
        rr = cl.post("/projects/%d/edit" % pid, data={k: (v if len(v) > 1 else v[0]) for k, v in f.items()})
    return rr.status_code, rr.headers.get("location", "")


print("=" * 78)
print("§1 서버")
print("=" * 78)
st, loc, P = new_project("z1191-P", "VINA", end="가상최종A")
S0 = orders_of(P["id"])[0] if P else {}
check("1 신규 등록(1차 가상 VINA · 고객사2 가상최종A) → 첫 수주 1차 = 프로젝트 고객 · **2차도 첫 수주 칸에**",
      st == 303 and S0.get("customer_id") == CUST["VINA"] and S0.get("end_customer") == "가상최종A",
      (st, loc, S0.get("customer_id"), S0.get("end_customer")))
st2, loc2, Q = new_project("z1191-Q", "OTH", end="")
Q0 = orders_of(Q["id"])[0] if Q else {}
check("   고객사2 비우고 신규 → 첫 수주 2차 비움(NULL)", st2 == 303 and Q0.get("end_customer") is None, Q0.get("end_customer"))
ok1, F1, raw1 = followup(P, "DT1", end="")
ok2, F2, raw2 = followup(P, "VINA", end="가상최종B", iex="1")
check("   추가 발주 둘(가상드림(동탄) · 가상 VINA+2차) 준비", ok1 and ok2, (raw1, raw2))

with contextlib.redirect_stdout(io.StringIO()):
    r = cl.get("/api/projects/search", params={"q": P["mgmt_code"]})
row = [x for x in (r.json().get("rows") or []) if x.get("id") == P["id"]]
row = row[0] if row else {}
sc = row.get("so_custs") or []
check("2 관리번호 검색 「지난 발주처」: 최근 것부터 · 중복 없이 · 건수 — 가상 VINA(2) · 가상드림(동탄)(1)",
      [(x.get("id"), x.get("name"), x.get("n")) for x in sc] == [(CUST["VINA"], "가상 VINA", 2), (CUST["DT1"], "가상드림(동탄)", 1)], sc)
check("   「지난 2차」: 수주 2차(최근부터) + 프로젝트 고객사2(중복 없이)", row.get("so_ends") == ["가상최종B", "가상최종A"], row.get("so_ends"))
try:
    with D.db_session() as c:
        c.execute("INSERT INTO projects (name, mgmt_code, customer_id, customer_name, biz_div, status) VALUES (?,?,?,?,?,?)",
                  ("z1191-NOSO", "099T2610", CUST["DT2"], "(주) 가상드림", "T", "수주예정"))
except Exception as _e:
    print("   (수주 없는 관리번호 준비 실패:", _e, ")")
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.get("/api/projects/search", params={"q": "099T2610"})
rn = [x for x in (r.json().get("rows") or []) if x.get("mgmt_code") == "099T2610"]
check("   수주 없는 관리번호 → 프로젝트 고객 하나(건수 0)",
      bool(rn) and [(x["id"], x["n"]) for x in rn[0].get("so_custs") or []] == [(CUST["DT2"], 0)], rn and rn[0].get("so_custs"))

# 정보수정 → 첫 수주
st, loc = edit_roundtrip(P["id"], {"customer_id": str(CUST["OTH"]), "customer_name": "가상기타(주)", "secondary_customer": "가상최종C"})
s0, f1, f2 = order(S0["id"]), order(F1["id"]), order(F2["id"])
check("3 정보수정(고객사1 → 가상기타 · 고객사2 → 가상최종C) → 첫 수주도 같이(옛 대표값과 같았으므로)",
      st == 303 and "error" not in loc and s0["customer_id"] == CUST["OTH"] and s0.get("end_customer") == "가상최종C",
      (st, loc, s0["customer_id"], s0.get("end_customer")))
check("   추가 수주는 그대로(가상드림(동탄) · 가상 VINA/가상최종B)",
      f1["customer_id"] == CUST["DT1"] and f2["customer_id"] == CUST["VINA"] and f2.get("end_customer") == "가상최종B",
      (f1["customer_id"], f2["customer_id"], f2.get("end_customer")))
with D.db_session() as c:   # 첫 수주를 일부러 다른 고객으로 둔 프로젝트(운영 7건 같은 경우)
    c.execute("UPDATE orders SET customer_id=? WHERE id=?", (CUST["DT2"], Q0["id"]))
st, loc = edit_roundtrip(Q["id"], {"customer_id": str(CUST["VINA"]), "customer_name": "가상 VINA"})
check("   첫 수주가 대표값과 달랐으면(일부러) 정보수정이 덮지 않음",
      st == 303 and order(Q0["id"])["customer_id"] == CUST["DT2"] and proj(Q["id"])["customer_id"] == CUST["VINA"],
      (st, order(Q0["id"])["customer_id"], proj(Q["id"])["customer_id"]))

# 작업일정표 한 칸 — 고객사(1차)
stc, j = cell(P["id"], "cust", "가상 VINA", so_oid=F1["id"], customer_id=CUST["VINA"])
check("4 작업일정표 고객사 칸(추가 수주 줄) → **그 수주**만 · 프로젝트 고객 그대로",
      stc == 200 and j.get("ok") and j.get("scope") == "so" and order(F1["id"])["customer_id"] == CUST["VINA"]
      and proj(P["id"])["customer_id"] == CUST["OTH"], (stc, j, order(F1["id"])["customer_id"], proj(P["id"])["customer_id"]))
stc, j = cell(P["id"], "cust", "가상드림(아산)", so_oid=S0["id"], customer_id=CUST["DT2"])
check("   첫 수주 줄 → 그 수주 + 프로젝트 대표값도(옛 값이 같았으므로)",
      stc == 200 and j.get("ok") and order(S0["id"])["customer_id"] == CUST["DT2"] and proj(P["id"])["customer_id"] == CUST["DT2"],
      (stc, j, order(S0["id"])["customer_id"], proj(P["id"])["customer_id"]))
stc, j = cell(P["id"], "cust", "없는회사", so_oid=F1["id"])
check("   등록 안 된 이름 → 400 · 안내 · 그대로", stc == 400 and "찾을 수 없" in (j.get("error") or "")
      and order(F1["id"])["customer_id"] == CUST["VINA"], (stc, j))
stc, j = cell(P["id"], "cust", "(주) 가상드림", so_oid=F1["id"])
check("   같은 정식 상호 두 곳(번호 없이) → 400 「2곳」", stc == 400 and "2곳" in (j.get("error") or ""), (stc, j))
stc, j = cell(Q["id"], "cust", "가상기타", customer_id=CUST["OTH"])
check("   수주 번호 없는 줄은 예전대로 프로젝트", stc == 200 and j.get("ok") and proj(Q["id"])["customer_id"] == CUST["OTH"]
      and not j.get("scope"), (stc, j, proj(Q["id"])["customer_id"]))

# 고객사2
stc, j = cell(P["id"], "cust2", "가상최종D", so_oid=F1["id"])
check("5 고객사2 칸(추가 수주 줄) → 그 수주 2차 · 프로젝트 2차 그대로",
      stc == 200 and order(F1["id"]).get("end_customer") == "가상최종D" and proj(P["id"]).get("secondary_customer") == "가상최종C",
      (stc, j, order(F1["id"]).get("end_customer"), proj(P["id"]).get("secondary_customer")))
stc, j = cell(P["id"], "cust2", "가상최종E", so_oid=S0["id"])
pp = proj(P["id"])
check("   첫 수주 줄 → 프로젝트 2차도 · 2단 표시",
      stc == 200 and order(S0["id"]).get("end_customer") == "가상최종E" and pp.get("secondary_customer") == "가상최종E"
      and pp.get("two_tier_order") == 1, (stc, j, order(S0["id"]).get("end_customer"), pp.get("secondary_customer")))
stc, j = cell(P["id"], "cust2", "", so_oid=S0["id"])
pp = proj(P["id"])
check("   첫 수주 줄에서 지우면 → 그 수주·대표값 모두 비움 · 2단 끔(최종 매출 0)",
      stc == 200 and order(S0["id"]).get("end_customer") is None and not pp.get("secondary_customer") and pp.get("two_tier_order") == 0,
      (order(S0["id"]).get("end_customer"), pp.get("secondary_customer"), pp.get("two_tier_order")))

# 거래구분
iex_p = proj(P["id"]).get("is_export")
stc, j = cell(P["id"], "trade", "내수", so_oid=F2["id"])
check("6 거래구분 칸(수주 줄 · 호기 지정 없음) → 그 수주 호기 전부 · 프로젝트 값 그대로",
      stc == 200 and all(i.get("is_export") == 0 for i in items_of(F2["id"])) and proj(P["id"]).get("is_export") == iex_p,
      (stc, j, [i.get("is_export") for i in items_of(F2["id"])], proj(P["id"]).get("is_export")))
with D.db_session() as c:
    c.execute("INSERT INTO order_items (order_id, unit_label, qty, unit_price, amount, is_export) VALUES (?,?,?,?,?,?)",
              (F2["id"], "9호기", 1, 0, 0, 0))
its = items_of(F2["id"])
stc, j = cell(P["id"], "trade", "수출", so_oid=F2["id"], uids=str(its[-1]["id"]))
its = items_of(F2["id"])
check("   호기를 집으면 그 호기만", stc == 200 and its[-1].get("is_export") == 1 and its[0].get("is_export") == 0,
      [i.get("is_export") for i in its])
with D.db_session() as c:
    c.execute("UPDATE orders SET status='INVOICED' WHERE id=?", (F2["id"],))
stc, j = cell(P["id"], "trade", "내수", so_oid=F2["id"])
stc2, j2 = cell(P["id"], "cust", "가상드림(동탄)", so_oid=F2["id"], customer_id=CUST["DT1"])
stc3, j3 = cell(P["id"], "cust2", "가상최종F", so_oid=F2["id"])
check("   계산서 발행 끝난 수주: 거래구분·발주처는 막음(400) · 2차는 됨",
      stc == 400 and stc2 == 400 and stc3 == 200 and order(F2["id"])["customer_id"] == CUST["VINA"], (stc, j, stc2, j2, stc3))
with D.db_session() as c:
    c.execute("UPDATE orders SET status='CONFIRMED' WHERE id=?", (F2["id"],))
    c.execute("DELETE FROM order_items WHERE order_id=? AND unit_label='9호기'", (F2["id"],))   # 시험용 호기 — 전사일정표 줄 수에 안 섞이게

# 일괄
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/sales/schedule/bulk-cell", json={"field": "po_type", "value": "수리", "targets": [
        {"kind": "project", "ref_id": P["id"], "so_oid": str(F1["id"])},
        {"kind": "project", "ref_id": P["id"], "so_oid": str(S0["id"])}]})
jb = r.json()
check("7 일괄 PO유형(수주 줄 둘) → 그 두 수주 · 성공 열쇠에 수주",
      jb.get("ok_count") == 2 and order(F1["id"]).get("po_type") == "수리" and order(S0["id"]).get("po_type") == "수리"
      and "project:%d:%d" % (P["id"], F1["id"]) in (jb.get("ok_keys") or []), jb)
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/sales/schedule/bulk-cell", json={"field": "cust2", "value": "가상최종G", "targets": [
        {"kind": "project", "ref_id": P["id"], "so_oid": str(F2["id"])}]})
check("   일괄 고객사2(추가 수주 줄) → 그 수주만", r.json().get("ok_count") == 1 and order(F2["id"]).get("end_customer") == "가상최종G"
      and not proj(P["id"]).get("secondary_customer"), r.json())

# 수주 카드 빠른 수정 → 대표값
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/sales/orders/%d/quick-edit" % S0["id"], data={"order_customer": "가상 VINA"})
check("8 수주 카드(첫 수주) 발주처 → 가상 VINA · 프로젝트 대표값도",
      r.status_code == 200 and order(S0["id"])["customer_id"] == CUST["VINA"] and proj(P["id"])["customer_id"] == CUST["VINA"],
      (r.status_code, order(S0["id"])["customer_id"], proj(P["id"])["customer_id"]))
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/sales/orders/%d/quick-edit" % F1["id"], data={"order_customer": "가상드림(동탄)"})
check("   추가 수주 카드 → 그 수주만(대표값 그대로)",
      r.status_code == 200 and order(F1["id"])["customer_id"] == CUST["DT1"] and proj(P["id"])["customer_id"] == CUST["VINA"],
      (r.status_code, order(F1["id"])["customer_id"], proj(P["id"])["customer_id"]))
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/sales/orders/%d/quick-edit" % S0["id"], data={"end_customer": "가상최종H"})
check("   수주 카드(첫 수주) 2차 → 대표값 2차도", r.status_code == 200 and proj(P["id"]).get("secondary_customer") == "가상최종H",
      proj(P["id"]).get("secondary_customer"))

print()
print("-- z1191b 전사일정표 --")
check("9 부서 기록 표에 수주 칸(order_id)", "order_id" in DSLC, sorted(DSLC))


def dept_html():
    with contextlib.redirect_stdout(io.StringIO()):
        r = cl.get("/dept/schedule", params={"ym": "2026-10"})
    return r.status_code, r.text


def rows_of(h, pid):
    out = []
    for m in re.finditer(r'<tr data-kind="project" data-ref="%d"[^>]*>(.*?)</tr>' % pid, h, re.S):
        tag = m.group(0)[:m.group(0).index(">") + 1]
        oid = re.search(r'data-oid="(\d*)"', tag)
        lk = re.search(r'data-lk="([^"]*)"', tag)
        out.append({"oid": oid.group(1) if oid else None, "lk": lk.group(1) if lk else None, "html": m.group(1)})
    return out


stc, h = dept_html()
rs = rows_of(h, P["id"])
by_oid = {r["oid"]: r for r in rs}
check("10 전사일정표: 관리번호 하나에 **수주마다 한 줄**(3수주 → 3줄) · 줄마다 수주 번호·기록 열쇠",
      stc == 200 and len(rs) == 3 and set(by_oid) == {str(S0["id"]), str(F1["id"]), str(F2["id"])}
      and by_oid.get(str(F1["id"]), {}).get("lk") == "project:%d:%d" % (P["id"], F1["id"]), (stc, [(r["oid"], r["lk"]) for r in rs]))
check("   줄마다 그 수주의 발주처 — 가상드림(동탄) 줄 · 가상 VINA 줄 · 수주번호",
      "가상드림(동탄)" in by_oid.get(str(F1["id"]), {}).get("html", "") and F1["order_no"] in by_oid.get(str(F1["id"]), {}).get("html", "")
      and "가상 VINA" in by_oid.get(str(F2["id"]), {}).get("html", ""), [re.sub(r"\s+", " ", r["html"])[:300] for r in rs][:2])
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/dept/schedule/cell/add", json={"kind": "project", "ref_id": P["id"], "date": "2026-10-05", "dept": "설계팀",
                                                  "log_type": "진행", "content": "z1191b 동탄 수주 기록", "order_id": str(F1["id"])})
with D.db_session() as c:
    lg = c.execute("SELECT order_id FROM dept_schedule_log WHERE content='z1191b 동탄 수주 기록'").fetchone()
check("11 부서 기록 쓰기(그 줄의 수주) → order_id 저장", r.status_code == 200 and r.json().get("ok") and lg and lg[0] == F1["id"],
      (r.status_code, r.text[:200], lg and lg[0]))
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/dept/schedule/cell/add", json={"kind": "project", "ref_id": P["id"], "date": "2026-10-05", "dept": "설계팀",
                                                  "log_type": "진행", "content": "남의 수주", "order_id": str(Q0["id"])})
check("   다른 관리번호의 수주 → 400", r.status_code == 400, (r.status_code, r.text[:160]))
with D.db_session() as c:   # 옛 기록(수주 없음) — 운영 1건 같은 것
    c.execute("INSERT INTO dept_schedule_log(ref_kind, ref_id, log_date, dept, log_type, content) VALUES (?,?,?,?,?,?)",
              ("project", P["id"], "2026-10-06", "설계팀", "진행", "z1191b 옛 기록"))
stc, h = dept_html()
mlog = re.search(r"var LOGS=(\{.*?\}), MYTEAM=", h, re.S)
LOGS = json.loads(mlog.group(1)) if mlog else {}
k_f1, k_s0 = "project:%d:%d" % (P["id"], F1["id"]), "project:%d:%d" % (P["id"], S0["id"])
txt = lambda k: json.dumps(LOGS.get(k) or {}, ensure_ascii=False)   # noqa: E731
check("   그 기록은 동탄 수주 줄 열쇠에만 · 옛 기록은 첫 수주 줄 열쇠에",
      "z1191b 동탄 수주 기록" in txt(k_f1) and "z1191b 동탄 수주 기록" not in txt(k_s0) and "z1191b 옛 기록" in txt(k_s0)
      and "z1191b 옛 기록" not in txt(k_f1), sorted(LOGS.keys()))
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.get("/dept/schedule/timeline", params={"kind": "project", "ref_id": P["id"]})
its_tl = r.json().get("items") or []
check("   모아보기(📜): 기록마다 수주번호(옛 기록은 빈칸)",
      any(x.get("content") == "z1191b 동탄 수주 기록" and x.get("so") == F1["order_no"] for x in its_tl)
      and any(x.get("content") == "z1191b 옛 기록" and x.get("so") == "" for x in its_tl), its_tl)

print()
print("-- z1191c 상세 맨 위 --")
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.get("/project/%d" % P["id"])
m = re.search(r'<dt>고객사</dt><dd[^>]*>(.*?)</dd>', r.text, re.S)
dd = re.sub(r"<[^>]+>", " ", m.group(1)) if m else ""
check("12 상세 맨 위 고객사 = 대표(가상 VINA) + 「외 1곳 (가상드림(동탄))」",
      r.status_code == 200 and "가상 VINA" in dd and "외 1곳" in dd and "가상드림(동탄)" in dd, re.sub(r"\s+", " ", dd)[:200])
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.get("/project/%d" % Q["id"])
m = re.search(r'<dt>고객사</dt><dd[^>]*>(.*?)</dd>', r.text, re.S)
dq = re.sub(r"<[^>]+>", " ", m.group(1)) if m else ""
check("   다른 발주처가 있으면만(Q: 첫 수주가 다른 고객 → 외 1곳) — 표시 규칙 확인", "외 1곳" in dq, re.sub(r"\s+", " ", dq)[:200])

print()
print("=" * 78)
print("§2 실제 화면 — Chromium · 시험용 서버(임시 DB)")
print("=" * 78)
DRIVER = r'''
import json, sys
from playwright.sync_api import sync_playwright
BASEURL, MG, F1, VINA, DT1, DT2, PID = sys.argv[1:8]
out = {"page_errors": [], "cases": {}}
CP = "input[data-cust-picker][data-cust-name=customer_name]"

def wait_idle(pg):
    try:
        pg.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass

def pick_mgmt(pg, code):
    for _t in range(3):
        pg.fill("#qMgmtInput", "")
        pg.type("#qMgmtInput", code, delay=30)
        pg.wait_for_timeout(700)
        hit = pg.evaluate("""(code)=>{ var ds=[].slice.call(document.querySelectorAll('#qMgmtList > div'));
            var d=ds.filter(function(x){ var b=x.querySelector('b'); return b && b.textContent.trim()===code; })[0];
            if(!d) return false; d.dispatchEvent(new MouseEvent('mousedown', {bubbles:true, cancelable:true})); return true; }""", code)
        if hit:
            break
    pg.wait_for_timeout(900)
    return hit

def st(pg):
    return pg.evaluate("""()=>{ var c=document.querySelector('#quickForm input[name=customer_id]'), p=document.querySelector('input[data-cust-picker][data-cust-name=customer_name]'),
        s=document.querySelector('#quickForm input[name=secondary_customer]'), x=document.getElementById('qIsExport'),
        c1=document.getElementById('qCust1Chips'), c2=document.getElementById('qCust2Chips');
        function chips(b){ return b ? [].map.call(b.querySelectorAll('.qf-chip'), function(e){ return e.textContent; }) : null; }
        return {cid: c ? c.value : null, pick: p ? p.value : null, sec: s ? s.value : null, iex: x ? x.value : null,
                c1: chips(c1), c1h: c1 ? c1.hidden : null, c2: chips(c2), c2h: c2 ? c2.hidden : null}; }""")

def a_chips(pg):
    pg.goto(BASEURL + "/projects/quick?biz_div=T"); wait_idle(pg)
    pg.select_option("#qPoType", "추가"); pg.wait_for_timeout(300)
    hit = pick_mgmt(pg, MG)
    s1 = st(pg)
    pg.evaluate("""(t)=>{ var b=[].filter.call(document.querySelectorAll('#qCust1Chips .qf-chip'), function(e){ return e.textContent===t; })[0]; if(b) b.click(); }""", "가상드림(동탄)")
    pg.wait_for_timeout(900)
    s2 = st(pg)
    pg.evaluate("""()=>{ var b=document.querySelector('#qCust2Chips .qf-chip'); if(b) b.click(); }""")
    pg.wait_for_timeout(300)
    s3 = st(pg)
    pg.evaluate("""(n)=>{ var s=document.getElementById('qNameSel'), i=document.getElementById('qNameInp');
                         if(s && s.offsetParent!==null){ s.value='__free__'; if(typeof qNamePick==='function') qNamePick('__free__'); }
                         if(i){ i.style.display=''; i.value=n; } }""", "z1191-P")
    pg.fill("input[name=model]", "PBA")
    pg.fill("input[name=equip_name]", "기능검사기")
    pg.evaluate("""()=>{ var c=document.getElementById('qProdNotify'); if(c && c.checked) c.click(); }""")
    for sel, v in (("#qOrderDate", "2026-10-03"), ("#qDueDate", "2026-10-21")):
        if pg.query_selector(sel):
            pg.fill(sel, v)
    if pg.query_selector("#qUnitPrice"):
        pg.fill("#qUnitPrice", "3000")
    posts = []
    pg.on("request", lambda rq: posts.append(rq.url) if (rq.method == "POST" and "/projects/new" in rq.url) else None)
    pg.click("button.qf-save"); pg.wait_for_timeout(1500)
    try:
        pg.wait_for_load_state("domcontentloaded", timeout=8000)
    except Exception:
        pass
    return {"hit": hit, "after_mgmt": s1, "after_chip": s2, "after_chip2": s3, "posts": len(posts), "url": pg.url}

def b_board(pg):
    pg.goto(BASEURL + "/sales/schedule?ym=2026-10"); wait_idle(pg); pg.wait_for_timeout(800)
    sel = 'tr[data-soid="' + F1 + '"] td[data-edit="cust"]'
    has = bool(pg.query_selector(sel))
    if not has:
        return {"has": False}
    pg.click(sel); pg.wait_for_timeout(300)
    pg.fill("td[data-edit=cust] input.cell-input", "가상 VINA"); pg.wait_for_timeout(900)
    picked = pg.evaluate("""(id)=>{ var it=document.querySelector('.knkcust-dd .knkcust-it[data-id="'+id+'"]'); if(!it) return false;
        it.dispatchEvent(new MouseEvent('mousedown', {bubbles:true, cancelable:true})); return true; }""", VINA)
    pg.wait_for_timeout(1500)
    txt = pg.evaluate("(s)=>{ var td=document.querySelector(s); return td ? td.textContent.trim() : null; }", sel)
    return {"has": True, "picked": picked, "cell": txt}

def c_dept(pg):
    pg.goto(BASEURL + "/dept/schedule?ym=2026-10"); wait_idle(pg); pg.wait_for_timeout(600)
    sel = 'tr[data-oid="' + F1 + '"] td.day[data-day="7"]'
    if not pg.query_selector(sel):
        return {"has": False}
    pg.click(sel); pg.wait_for_timeout(400)
    title = pg.evaluate("()=>{ var t=document.getElementById('dsxTitle'); return t ? t.textContent : null; }")
    pg.fill("#dsxContent", "z1191b 화면 기록")
    pg.click("#dsxSave"); pg.wait_for_timeout(1800)
    try:
        pg.wait_for_load_state("domcontentloaded", timeout=8000)
    except Exception:
        pass
    pg.wait_for_timeout(600)
    marks = pg.evaluate("""(f1)=>{ var out={}; [].forEach.call(document.querySelectorAll('tr[data-ref]'), function(tr){
        var td=tr.querySelector('td.day[data-day="7"]'); if(tr.dataset.oid) out[tr.dataset.oid]=td ? !!td.querySelector('.mk') : null; }); return out; }""", F1)
    return {"has": True, "title": title, "marks": marks}

with sync_playwright() as p:
    br = p.chromium.launch()
    def run(key, fn):
        ctx = br.new_context(viewport={"width": 1500, "height": 1000})
        ctx.add_init_script("try{sessionStorage.setItem('knkAutoReloadTs', String(Date.now()));}catch(e){}")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: out["page_errors"].append(key + ": " + str(e)[:200]))
        pg.on("dialog", lambda d: d.accept())
        try:
            out["cases"][key] = fn(pg)
        except Exception as e:
            out["cases"][key] = {"exc": str(e)[:400]}
        finally:
            ctx.close()
    for k, fn in (("A", a_chips), ("B", b_board), ("C", c_dept)):
        run(k, fn)
    br.close()
print("@@RESULT@@" + json.dumps(out, ensure_ascii=False))
'''


def find_pw_python():
    cands = [sys.executable, os.environ.get("KNK_PW_PY", ""),
             os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python312\python.exe"), "python"]
    for c in cands:
        if not c:
            continue
        try:
            if subprocess.run([c, "-c", "import playwright.sync_api"], capture_output=True, timeout=60).returncode == 0:
                return c
        except Exception:
            pass
    return None


import uvicorn                                              # noqa: E402

_sk = socket.socket()
_sk.bind(("127.0.0.1", 0))
PORT = _sk.getsockname()[1]
_sk.close()
srv = uvicorn.Server(uvicorn.Config(M.app, host="127.0.0.1", port=PORT, lifespan="off", log_level="warning"))
threading.Thread(target=srv.run, daemon=True).start()
for _ in range(150):
    if srv.started:
        break
    time.sleep(0.1)
BASEURL = "http://127.0.0.1:%d" % PORT
check("시험용 서버 뜸(127.0.0.1 · 빈 포트 · 시작 작업 끔)", srv.started, PORT)
PWPY = find_pw_python()
check("Playwright 있는 파이썬 찾음", bool(PWPY), PWPY)
DRV = os.path.join(TMP, "pw_driver.py")
io.open(DRV, "w", encoding="utf-8").write(DRIVER)
n_before = len(orders_of(P["id"]))
cases, page_errors = {}, []
if PWPY:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    rr = subprocess.run([PWPY, DRV, BASEURL, P["mgmt_code"], str(F1["id"]), str(CUST["VINA"]), str(CUST["DT1"]), str(CUST["DT2"]),
                         str(P["id"])], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900, env=env)
    line = [x for x in (rr.stdout or "").splitlines() if x.startswith("@@RESULT@@")]
    if line:
        res = json.loads(line[-1][len("@@RESULT@@"):])
        cases, page_errors = res["cases"], res["page_errors"]
    else:
        print("   (브라우저 쪽 출력)", (rr.stdout or "")[-800:], (rr.stderr or "")[-1500:])
        page_errors = ["(브라우저 결과 없음)"]
A = cases.get("A") or {}
a1, a2, a3 = A.get("after_mgmt") or {}, A.get("after_chip") or {}, A.get("after_chip2") or {}
check("A 추가 발주 · 관리번호만 고르면 고객사 **비어 있음**(몰래 안 채움) · 「지난 발주처」 단추 보임",
      A.get("hit") and not a1.get("cid") and not (a1.get("pick") or "").strip() and a1.get("c1h") is False
      and "가상드림(동탄)" in (a1.get("c1") or []) and "가상 VINA" in (a1.get("c1") or []), a1)
check("   단추 「가상드림(동탄)」 → 그 종사업장 번호로 정확히(같은 상호 「가상드림(아산)」 아님)",
      a2.get("cid") == str(CUST["DT1"]) and a2.get("pick") == "가상드림(동탄)", a2)
check("   「지난 2차」 단추 → 고객사2 칸에 들어감", a3.get("c2h") is False and bool(a3.get("sec")) and a3.get("sec") == (a3.get("c2") or [""])[0], a3)
newA = orders_of(P["id"])[n_before:]
check("   「＋ 등록」 → 새 수주 1차 = 가상드림(동탄) · 2차 = 고른 값",
      A.get("posts") == 1 and len(newA) == 1 and newA[0]["customer_id"] == CUST["DT1"] and newA[0].get("end_customer") == a3.get("sec"),
      (A.get("posts"), A.get("url"), [(o["order_no"], o["customer_id"], o.get("end_customer")) for o in newA]))
B = cases.get("B") or {}
check("B 작업일정표 · 동탄 수주 줄 고객사 칸에서 가상 VINA 고름 → 그 수주만 바뀜 · 프로젝트 그대로",
      B.get("has") and B.get("picked") and order(F1["id"])["customer_id"] == CUST["VINA"] and proj(P["id"])["customer_id"] == CUST["VINA"]
      and (B.get("cell") or "").startswith("가상 VINA"), (B, order(F1["id"])["customer_id"]))
C = cases.get("C") or {}
with D.db_session() as c:
    lgc = c.execute("SELECT order_id FROM dept_schedule_log WHERE content='z1191b 화면 기록'").fetchone()
check("C 전사일정표 · 그 수주 줄 날짜 칸 → 기록 창 제목에 수주번호 · 저장 → 그 수주(order_id)",
      C.get("has") and F1["order_no"] in (C.get("title") or "") and lgc and lgc[0] == F1["id"], (C.get("title"), lgc and lgc[0]))
check("   표시(●)는 그 수주 줄에만", (C.get("marks") or {}).get(str(F1["id"])) is True and (C.get("marks") or {}).get(str(S0["id"])) is False,
      C.get("marks"))
check("화면 스크립트 오류 0", not page_errors, page_errors)

print()
print("=" * 78)
print("§3 바뀐 곳 원문")
print("=" * 78)
T = os.path.join(ROOT, "app", "templates")
mn = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
pw = open(os.path.join(ROOT, "app", "project_workflow.py"), encoding="utf-8").read()
db = open(os.path.join(ROOT, "app", "database.py"), encoding="utf-8").read()
qf = open(os.path.join(T, "project_quick_form.html"), encoding="utf-8").read()
cp = open(os.path.join(T, "_v5_partials", "customer_picker.html"), encoding="utf-8").read()
sb = open(os.path.join(T, "schedule_board.html"), encoding="utf-8").read()
ds = open(os.path.join(T, "dept_schedule.html"), encoding="utf-8").read()
pd = open(os.path.join(T, "project_detail.html"), encoding="utf-8").read()
check("서버: 수주 칸 저장 함수 한 곳 · 한 칸/일괄 모두 거기로 · 대표값 맞추기 둘",
      mn.count("def _z1191_so_cell(") == 1 and mn.count("_z1191_so_cell(field, value, _so_oid") == 1
      and mn.count("_z1191_so_cell(field, value, _soid1191") == 1 and "def _z1191_sync_project_from_so(" in mn
      and "def _z1191_cascade_first_so(" in mn)
check("등록: 첫 수주 2차(confirm_order·confirm_order_multi) · z621 미리 채우기 없앰 · 단추",
      pw.count("_z1191_end_first(c, proj, order_id)   # z1191") == 1 and pw.count("_z1191_end_first(c, proj, oid)   # z1191") == 1 and "custP.value=rw.customer_name" not in qf and "qFuChips(rw);" in qf
      and 'id="qCust1Chips"' in qf and 'id="qCust2Chips"' in qf and ".qf-chips[hidden]{display:none;}" in qf)
check("고객 고르기: 번호로 고르기(setById) 내보냄", "setById:setById" in cp and "inp.__custSetById=" in cp)
check("작업일정표: 고객사 칸·일괄이 수주 번호를 보냄", "customer_id:(opt?opt.id:''),so_oid:tr.dataset.soid||''" in sb
      and "so_oid:(tr.dataset.soid||''), uids:(tr.dataset.uids||'')" in sb)
check("전사일정표: 수주별 줄 · 기록 열쇠 · 기록에 수주 · DB 칸 한 줄(업무 데이터 UPDATE 없음)",
      "_board_split_lines_map(unfold_sos=True, pids=_pids)" in mn and "_board_split_lines_map(unfold_sos=False" not in mn
      and 'data-lk="{{ key }}"' in ds and "order_id:(cur.oid||'')" in ds
      and '"ALTER TABLE dept_schedule_log ADD COLUMN order_id INTEGER"' in db and "UPDATE dept_schedule_log SET order_id" not in db)
check("상세 맨 위: 외 n곳(do 확장 없이)", "{% set _oth1191 = " in pd and "{% do " not in pd)
for nm, src in (("project_quick_form.html", qf), ("schedule_board.html", sb), ("dept_schedule.html", ds), ("customer_picker.html", cp)):
    bad = [l for l in src.splitlines() if ("z1191" in l) and "{#" not in l and ("{{" in l or "{%" in l)
           and 'data-lk="{{ key }}"' not in l]
    check("%s: z1191 스크립트 줄에 Jinja 기호 없음" % nm, not bad, bad[:2])

print()
print("결과: %d개 중 실패 %d" % (OK + FAIL, FAIL))
sys.exit(1 if FAIL else 0)
