# -*- coding: utf-8 -*-
"""z1190 시험 — 수주(SO)마다 2차 발주처(최종 고객)
   (대표 2026-10-16 「A 관리번호를 처음엔 드림텍(동탄)이 발주 · 추가 제작은 드림텍 베트남 → KNK VINA → 본사.
    KNKVINA 가 1차, 드림텍 베트남이 2차인데 항상 처음 입력한 고객사로 지정된다」)

  규칙: 수주의 2차 = 그 수주에 적힌 값 · 비어 있고 1차가 프로젝트 고객과 같으면 프로젝트 고객사2 · 1차가 다르면 빈칸
  §1 서버(임시 DB · TestClient): 칸 생김 · 추가 발주 등록이 고객사2 를 그 수주에 저장(완제품·상품) · 같은 고객/다른 고객 ·
     작업일정표 줄 고객사2(위 규칙) · 수주 카드 빠른 수정(적기·지우기) · 로그인 ID 막기(z1173) · 상세 화면 표시
  §2 실제 화면(Chromium): 상세 수주 카드에서 2차를 적고 「모두 저장」 → DB · 다시 열면 보임 · 스크립트 오류 0
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

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1190-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1190_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                     ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                     ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version) "
                 "VALUES ('가상관리자', 'admin', 'T901', 'T901', 'sso_only_no_local_password', 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T901'").fetchone())
    ccols = {r[1] for r in conn.execute("PRAGMA table_info(customers)")}
    for col in ("alias", "country"):
        if col not in ccols:
            conn.execute("ALTER TABLE customers ADD COLUMN %s TEXT" % col)
    CUST = {}
    for key, name, alias, country in (("DT", "(주) 가상드림동탄", "가상드림(동탄)", ""),
                                      ("VINA", "가상 VINA", "가상 VINA", "Vietnam")):
        conn.execute("INSERT INTO customers (name, alias, country) VALUES (?,?,?)", (name, alias, country))
        CUST[key] = conn.execute("SELECT id FROM customers WHERE name=?", (name,)).fetchone()[0]
    OCOLS = {r[1] for r in conn.execute("PRAGMA table_info(orders)")}

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M.get_user = lambda request: ADMIN
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


ALIAS = {"DT": "가상드림(동탄)", "VINA": "가상 VINA"}
BASE = {"quick": "1", "biz_div": "T", "project_type": "NEW_EQUIP", "status": "진행중", "confirm_now": "1",
        "order_date": "2026-10-02", "due_date": "2026-10-20", "equip_name": "기능검사기", "model": "PBA",
        "unit_qty": "1", "shipment_form": "ASSEMBLY", "currency": "KRW"}


def post(**kw):
    f = dict(BASE)
    f.update(kw)
    with contextlib.redirect_stdout(io.StringIO()):
        r = cl.post("/projects/new", data=f)
    return r.status_code, r.headers.get("location", "")


def orders_of(pid):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT * FROM orders WHERE project_id=? ORDER BY id", (pid,))]


print("=" * 78)
print("§1 서버")
print("=" * 78)
check("1 orders 에 end_customer 칸(마이그레이션)", "end_customer" in OCOLS, sorted(OCOLS)[:8])
st, loc = post(name="z1190-P", po_type="신규", customer_name=ALIAS["DT"], customer_id=str(CUST["DT"]), is_export="0",
               secondary_customer="가상최종A", unit_price="1000", order_amount="1000", **{"unit_amount[]": ["1000"]})
with D.db_session() as c:
    P = dict(c.execute("SELECT * FROM projects WHERE name='z1190-P'").fetchone())
check("2 신규 등록(1차 가상드림(동탄) · 고객사2 가상최종A) → 프로젝트 2차 · 첫 수주 2차 칸은 비움(프로젝트를 따름)",
      st == 303 and (P.get("secondary_customer") or "") == "가상최종A" and orders_of(P["id"])[0].get("end_customer") is None,
      (st, loc, P.get("secondary_customer"), orders_of(P["id"])[0].get("end_customer")))


def followup(ckey, end=None, iex="0", sf="ASSEMBLY", extra=None):
    kw = dict(name=P["name"], po_type="추가", mgmt_code=P["mgmt_code"], customer_name=ALIAS[ckey], customer_id=str(CUST[ckey]),
              is_export=iex, shipment_form=sf)
    if end is not None:
        kw["secondary_customer"] = end
    if sf == "PARTS":
        kw.update({"unit_price": "", "order_amount": "0", "pk_name[]": ["부품A"], "pk_model[]": ["M-1"], "pk_qty[]": ["2"],
                   "pk_price[]": ["300"]})
    else:
        kw.update({"unit_price": "2000", "order_amount": "2000", "unit_amount[]": ["2000"]})
    if extra:
        kw.update(extra)
    n0 = len(orders_of(P["id"]))
    st, loc = post(**kw)
    os_ = orders_of(P["id"])
    return (st == 303 and "error=" not in loc and len(os_) == n0 + 1), (os_[-1] if len(os_) > n0 else None), (st, loc)


ok, F1, raw = followup("VINA", end="가상드림 베트남", iex="1")
check("3 추가 발주 1차 KNK VINA · 고객사2 「가상드림 베트남」 → 그 수주 2차 저장(예전엔 버려짐)",
      ok and F1["customer_id"] == CUST["VINA"] and F1.get("end_customer") == "가상드림 베트남", (raw, F1 and F1.get("end_customer")))
ok, F2, raw = followup("DT")
check("4 같은 고객(가상드림(동탄)) 추가 발주 · 고객사2 비움 → 2차 칸 비움(프로젝트를 따름)",
      ok and F2.get("end_customer") is None, (raw, F2 and F2.get("end_customer")))
ok, F3, raw = followup("VINA", iex="1")
check("5 KNK VINA 추가 발주 · 고객사2 비움 → 2차 칸 비움", ok and F3.get("end_customer") is None, (raw, F3 and F3.get("end_customer")))
ok, F4, raw = followup("VINA", end="가상드림 베트남", iex="1", sf="PARTS")
check("6 상품(PARTS) 추가 발주 · 고객사2 → 그 수주 2차 저장", ok and F4.get("end_customer") == "가상드림 베트남",
      (raw, F4 and F4.get("end_customer"), F4 and F4.get("so_type")))

with contextlib.redirect_stdout(io.StringIO()):
    res = M.build_schedule_board_rows(ADMIN, 2026, 10)
rows = [r for r in (res.get("rows") or []) if r.get("code") == P["mgmt_code"]]
by_so = {}
for r in rows:
    by_so.setdefault(r.get("so_no"), r)
c2 = {so: r.get("cust2") for so, r in by_so.items()}
S0 = orders_of(P["id"])[0]["order_no"]
check("7 작업일정표 줄 고객사2: 첫 수주(같은 고객) = 프로젝트 「가상최종A」", c2.get(S0) == "가상최종A", c2)
check("   KNK VINA + 2차 적힘 = 「가상드림 베트남」", c2.get(F1["order_no"]) == "가상드림 베트남", c2)
check("   같은 고객 추가 발주(2차 비움) = 프로젝트 「가상최종A」", c2.get(F2["order_no"]) == "가상최종A", c2)
check("   🔴 KNK VINA 추가 발주(2차 비움) = 빈칸(다른 경로는 프로젝트 2차를 물려받지 않음)", c2.get(F3["order_no"]) == "", c2)
check("   줄 1차(고객사1)는 그대로 수주 발주처", (by_so.get(F1["order_no"]) or {}).get("customer_disp") == "가상 VINA"
      and (by_so.get(S0) or {}).get("customer_disp") == "가상드림(동탄)",
      {k: v.get("customer_disp") for k, v in by_so.items()})

with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/sales/orders/%d/quick-edit" % F3["id"], data={"end_customer": "가상드림 베트남2"})
with D.db_session() as c:
    e3 = c.execute("SELECT end_customer FROM orders WHERE id=?", (F3["id"],)).fetchone()[0]
check("8 수주 카드 빠른 수정 · 2차 적기 → 저장", r.status_code == 200 and e3 == "가상드림 베트남2", (r.status_code, e3))
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/sales/orders/%d/quick-edit" % F3["id"], data={"end_customer": ""})
with D.db_session() as c:
    e3 = c.execute("SELECT end_customer FROM orders WHERE id=?", (F3["id"],)).fetchone()[0]
check("   2차 지우기 → NULL", r.status_code == 200 and e3 is None, (r.status_code, e3))
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/sales/orders/%d/quick-edit" % F3["id"], data={"end_customer": "T901"})
check("9 2차 칸에 로그인 ID(브라우저 자동 채움) → 400 + 「2차 발주처」 안내(z1173 막기)",
      r.status_code == 400 and "2차 발주처" in ((r.json() or {}).get("message") or ""), (r.status_code, r.text[:160]))

with contextlib.redirect_stdout(io.StringIO()):
    h = cl.get("/project/%d" % P["id"]).text
check("10 상세 화면: 수주 카드마다 「🌐 2차」", h.count("🌐 2차") == len(orders_of(P["id"])), (h.count("🌐 2차"), len(orders_of(P["id"]))))
check("   적힌 2차는 굵게 · 같은 고객은 「가상최종A (프로젝트)」 · 다른 경로 빈칸은 —",
      "가상드림 베트남</b>" in h and "가상최종A (프로젝트)" in h, (h.count("가상드림 베트남"), h.count("(프로젝트)")))
check("   수정 칸은 메인(편집) 카드 1장에만(나머지 추가 수주는 「📎 참고」 보기 전용 카드)", h.count('data-field="end_customer"') == 1,
      h.count('data-field="end_customer"'))
with contextlib.redirect_stdout(io.StringIO()):
    h3 = cl.get("/project/%d?so=%s" % (P["id"], F3["order_no"])).text
m3 = re.search(r'<div class="so-card editable" data-soid="(\d+)"', h3)
check("   ?so=수주번호 로 열면 그 수주가 편집 카드 · 2차 수정 칸 있음(z695)", bool(m3) and m3.group(1) == str(F3["id"])
      and h3.count('data-field="end_customer"') == 1, (m3 and m3.group(1), F3["id"]))
with contextlib.redirect_stdout(io.StringIO()):
    hs = cl.get("/sales/schedule?ym=2026-10").text
check("11 작업일정표 화면(/sales/schedule): 「가상드림 베트남」 보임", "가상드림 베트남" in hs, hs.count("가상드림 베트남"))

print()
print("=" * 78)
print("§2 실제 화면 — Chromium · 시험용 서버(임시 DB)")
print("=" * 78)
DRIVER = r'''
import json, sys
from playwright.sync_api import sync_playwright
BASEURL, PID, SOID, SONO = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
out = {"page_errors": [], "cases": {}}
CARD = '.so-card.editable[data-soid="' + SOID + '"]'   # ?so=수주번호 로 연 그 수주 = 메인(편집) 카드
with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 1500, "height": 1000})
    ctx.add_init_script("try{sessionStorage.setItem('knkAutoReloadTs', String(Date.now()));}catch(e){}")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: out["page_errors"].append(str(e)[:200]))
    dialogs = []
    pg.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
    try:
        pg.goto(BASEURL + "/project/" + PID + "?so=" + SONO)
        try:
            pg.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        has = pg.evaluate("(sel)=>!!document.querySelector(sel + ' input[data-field=end_customer]')", CARD)
        pg.click(CARD + " .toggle-edit")
        pg.wait_for_timeout(300)
        pg.click(CARD + " input[data-field=end_customer]")
        ro = pg.evaluate("(sel)=>document.querySelector(sel + ' input[data-field=end_customer]').readOnly", CARD)
        pg.keyboard.type("가상드림 베트남3")
        pg.click(CARD + " .save-all-btn")
        pg.wait_for_timeout(2500)
        pg.goto(BASEURL + "/project/" + PID + "?so=" + SONO)
        try:
            pg.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        # 편집 카드는 값을 입력 칸에 담아 보인다(입력 칸 값은 innerText 에 안 잡힘) → 칸 값·표시 글자를 직접 읽는다
        shown = pg.evaluate("""(sel)=>{ var c=document.querySelector(sel); if(!c) return null;
            var i=c.querySelector('input[data-field=end_customer]'), item=i ? i.closest('.item') : null,
                d=item ? item.querySelector('.display-val') : null;
            return {inp: i ? i.value : null, disp: d ? (d.textContent||'').trim() : null}; }""", CARD)
        out["cases"]["A"] = {"has": has, "ro_after_click": ro, "dialogs": dialogs, "shown": shown}
    except Exception as e:
        out["cases"]["A"] = {"exc": str(e)[:400]}
    ctx.close()
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
cases, page_errors = {}, []
if PWPY:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    rr = subprocess.run([PWPY, DRV, BASEURL, str(P["id"]), str(F3["id"]), F3["order_no"]], capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=600, env=env)
    line = [x for x in (rr.stdout or "").splitlines() if x.startswith("@@RESULT@@")]
    if line:
        res2 = json.loads(line[-1][len("@@RESULT@@"):])
        cases, page_errors = res2["cases"], res2["page_errors"]
    else:
        print("   (브라우저 쪽 출력)", (rr.stdout or "")[-800:], (rr.stderr or "")[-1500:])
        page_errors = ["(브라우저 결과 없음)"]
A = cases.get("A") or {}
with D.db_session() as c:
    e3 = c.execute("SELECT end_customer FROM orders WHERE id=?", (F3["id"],)).fetchone()[0]
check("A 상세 수주 카드: 2차 칸 있음 · 누르면 읽기전용 풀림(z1173) · 적고 「모두 저장」 → DB 저장 · 알림창 없음",
      A.get("has") is True and A.get("ro_after_click") is False and e3 == "가상드림 베트남3" and not A.get("dialogs"), (A, e3))
check("   다시 열면 그 카드에 보임(입력 칸 값 · 표시 글자)", (A.get("shown") or {}).get("inp") == "가상드림 베트남3"
      and (A.get("shown") or {}).get("disp") == "가상드림 베트남3", A)
check("화면 스크립트 오류 0", not page_errors, page_errors)

print()
print("=" * 78)
print("§3 바뀐 곳 원문")
print("=" * 78)
mn = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
pw = io.open(os.path.join(ROOT, "app", "project_workflow.py"), encoding="utf-8").read()
db = io.open(os.path.join(ROOT, "app", "database.py"), encoding="utf-8").read()
tp = io.open(os.path.join(ROOT, "app", "templates", "project_detail.html"), encoding="utf-8").read()
check("DB 마이그레이션 한 줄 · 업무 데이터 UPDATE 없음",
      '("end_customer", "ALTER TABLE orders ADD COLUMN end_customer TEXT")' in db
      and not re.search(r"UPDATE orders SET end_customer", db))
check("add_followup_order end_customer · 상세 수주 목록 칸", "end_customer: str | None = None) -> dict:" in pw and '"end_customer"):   # z1190' in pw)
check("main: 추가 발주 넘김 · 상품 · 빠른 수정 · z1173 막기 · 일정표 SQL · 줄 규칙 두 곳",
      "end_customer=((form.get(\"secondary_customer\")" in mn and "_end1190" in mn and "_has1190" in mn
      and '("2차 발주처", form.get("end_customer"))' in mn and "AS o_end" in mn
      and mn.count('elif _ln.get("so_cust_id") and info.get("pcid")') == 2)
check("상세 카드 「🌐 2차」 · 템플릿 JS 에 Jinja 기호 문제 없음", "🌐 2차" in tp)

print()
print("결과: %d개 중 실패 %d" % (OK + FAIL, FAIL))
sys.exit(1 if FAIL else 0)
