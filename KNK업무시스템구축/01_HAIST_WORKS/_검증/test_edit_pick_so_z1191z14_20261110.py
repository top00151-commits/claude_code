# -*- coding: utf-8 -*-
"""z1191z14 시험 — 안지연 프로 요청 「프로젝트 정보 수정에서 수주번호를 눌러도 그대로 · 어느 수주 내용인지 모름」
   (대표 「1번 진행해」 2026-11-10)
  수정 화면(/projects/{pid}/edit)에 「✏ 고칠 대상: [관리번호 공통] [수주…]」 — 수주를 고르면 그 수주의 칸(발주처·2차·PO유형·
  발주일·납기·납품처·모델·장비)이 그 수주 값으로 보이고 「이 수주만 저장」(상세 수주 카드와 같은 저장 경로).
  수주 2건 이상이면 공통 화면의 발주일·납기는 고치는 칸 대신 「어느 수주 값인지」 · 서버도 날짜를 받지 않는다(다른 수주로 퍼짐 막기).
  §1 서버(임시 DB · TestClient) · §2 실제 화면(Chromium · 시험용 서버) · 운영 아님
  환경변수 Z14_SHOT_ONLY=1 → 자료만 만들고 화면만 찍음(고치기 전 코드의 화면 비교용)
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z14-test-only-not-a-real-key"   # 시험용 가짜 값
SHOT_ONLY = os.environ.get("Z14_SHOT_ONLY") == "1"
SHOT_DIR = os.environ.get("Z14_SHOT_DIR", "")

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z14_")
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
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상관리자', 'admin', 'T914', 'T914', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T914'").fetchone())
    ccols = {r[1] for r in conn.execute("PRAGMA table_info(customers)")}
    for col in ("alias", "country"):
        if col not in ccols:
            conn.execute("ALTER TABLE customers ADD COLUMN %s TEXT" % col)
    CUST = {}
    for key, name, alias, country in (("DT", "(주) 가상드림동탄", "가상드림(동탄)", ""),
                                      ("VINA", "가상 VINA", "가상 VINA", "Vietnam")):
        conn.execute("INSERT INTO customers (name, alias, country) VALUES (?,?,?)", (name, alias, country))
        CUST[key] = conn.execute("SELECT id FROM customers WHERE name=?", (name,)).fetchone()[0]

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


def items_of(oid):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT * FROM order_items WHERE order_id=? ORDER BY id", (oid,))]


def proj(name):
    with D.db_session() as c:
        return dict(c.execute("SELECT * FROM projects WHERE name=? ORDER BY id DESC", (name,)).fetchone())


def get(url):
    with contextlib.redirect_stdout(io.StringIO()):
        return cl.get(url)


# 자료: 수주 2건(첫 수주 가상드림(동탄) · 추가 수주 가상 VINA · 날짜 다름) + 수주 1건짜리 비교용
post(name="z14-P", po_type="신규", customer_name=ALIAS["DT"], customer_id=str(CUST["DT"]), is_export="0",
     secondary_customer="가상최종A", unit_price="1000", order_amount="1000", **{"unit_amount[]": ["1000"]})
P = proj("z14-P")
post(name="z14-P", po_type="추가", mgmt_code=P["mgmt_code"], customer_name=ALIAS["VINA"], customer_id=str(CUST["VINA"]),
     is_export="1", order_date="2026-10-05", due_date="2026-11-30", unit_price="2000", order_amount="2000",
     **{"unit_amount[]": ["2000"]})
SO = orders_of(P["id"])
S1, S2 = SO[0], SO[-1]
post(name="z14-ONE", po_type="신규", customer_name=ALIAS["DT"], customer_id=str(CUST["DT"]), is_export="0",
     unit_price="500", order_amount="500", **{"unit_amount[]": ["500"]})
P1 = proj("z14-ONE")

if not SHOT_ONLY:
    print("=" * 78)
    print("§1 서버")
    print("=" * 78)
    check("0 자료: 수주 2건 · 날짜 다름", len(SO) == 2 and S1["order_date"] == "2026-10-02" and S2["due_date"] == "2026-11-30",
          [(o["order_no"], o["order_date"], o["due_date"]) for o in SO])
    r = get("/projects/%d/edit" % P["id"])
    h = r.text
    check("1 수정 화면 200 · 「고칠 대상」 상자 · 공통 단추 + 수주 단추 2개", r.status_code == 200 and 'id="z14Box"' in h
          and h.count('class="z14-tab"') == 3 and ('data-so="%s"' % S1["order_no"]) in h and ('data-so="%s"' % S2["order_no"]) in h,
          (r.status_code, h.count('class="z14-tab"')))
    pn = {}
    for m in re.finditer(r'<div class="z14-panel" data-so="([^"]+)" data-soid="(\d+)".*?(?=<div class="z14-panel"|<datalist id="z14CustList")', h, re.S):
        pn[m.group(1)] = m.group(0)
    check("2 수주마다 칸 묶음(패널) 2개 · 수주 id 맞음", len(pn) == 2 and ('data-soid="%d"' % S2["id"]) in pn.get(S2["order_no"], ""), list(pn))

    def val(block, field):
        m = re.search(r'data-field="%s" data-orig="([^"]*)" value="([^"]*)"' % field, block)
        return m.group(2) if m else None
    p1, p2 = pn.get(S1["order_no"], ""), pn.get(S2["order_no"], "")
    check("3 첫 수주 칸 = 그 수주 값(발주 10-02 · 납기 = DB 그 수주 값 · 2차 가상최종A)",
          val(p1, "order_date") == "2026-10-02" and val(p1, "due_date") == str(S1["due_date"] or "")[:10] and val(p1, "end_customer") == "가상최종A",
          (val(p1, "order_date"), val(p1, "due_date"), S1["due_date"], val(p1, "end_customer")))
    check("4 추가 수주 칸 = 그 수주 값(발주 10-05 · 납기 11-30 · 발주처 「가상 VINA」)",
          val(p2, "order_date") == "2026-10-05" and val(p2, "due_date") == "2026-11-30" and val(p2, "order_customer") == "가상 VINA",
          (val(p2, "order_date"), val(p2, "due_date"), val(p2, "order_customer")))
    check("5 추가 수주(1차가 프로젝트 고객과 다름) 2차 칸 안내 = 프로젝트 2차를 물려받지 않음",
          "(비움 = 프로젝트 값 가상최종A)" not in p2 and "(비움 = 프로젝트 값" not in p2, re.findall(r'placeholder="[^"]*"', p2)[:3])
    check("6 PO유형 고르기 칸 · 저장 단추 「이 수주만 저장」", 'data-po="1"' in p2 and ("이 수주(%s)만 저장" % S2["order_no"]) in p2)
    check("7b 진행중 안내 글: 수주 2건이면 「발주일·납기는 수주마다 — 고칠 대상」", "발주일·납기는 <b>수주마다</b>" in h)
    check("7 공통 화면 발주일·납기 = 고치는 칸 없음 · 출처 수주 표시(가장 이른 발주 · 가장 늦은 납기)",
          'name="order_date"' not in h and 'name="due_date"' not in h
          and ("← 수주 %s" % S1["order_no"]) in h and ("← 수주 %s" % S2["order_no"]) in h, (h.count('name="order_date"')))
    check("8 고객사2 칸에 (대표값) 표시", re.search(r'<label>고객사2<span[^>]*>[^<]*</span>|<label>고객사2 <span class="sub" style="color:#b45309', h) is not None)
    check("9 수주 표(위 상자 · ③ 금액 두 곳): 수주번호 = 이 화면에서 고르기(z14-pick-link · 표 밖은 ?so= 로 다시 열림) · 상세 카드 ↗ 따로 · 납기 칸",
          h.count('class="z14-pick-link"') == 4 and ("/project/%d?so=" % P["id"]) in h and ">납기</th>" in h)
    h2 = get("/projects/%d/edit?so=%s" % (P["id"], S2["order_no"])).text
    check("10 ?so=수주번호 → 그 수주를 고른 채로 열림(data-sel)", ('data-sel="%s"' % S2["order_no"]) in h2)
    h3 = get("/projects/%d/edit?so=NOPE-1" % P["id"]).text
    check("11 없는 수주번호 → 공통(data-sel 빈칸)", 'data-sel=""' in h3)
    h4 = get("/projects/%d/edit?so=%s&z14ok=%s" % (P["id"], S2["order_no"], S2["order_no"])).text
    check("12 저장 뒤 돌아오면 「✅ 수주 … 저장됨」", ("✅ 수주 <b>%s</b> 저장됨" % S2["order_no"]) in h4)
    hp1 = get("/projects/%d/edit" % P1["id"]).text
    check("13 수주 1건 프로젝트 = 예전 그대로(고칠 대상 없음 · 날짜 칸 있음)",
          'id="z14Box"' not in hp1 and 'name="order_date"' in hp1 and 'name="due_date"' in hp1)

    # 서버 막기: 수주 2건 프로젝트의 공통 저장에 날짜를 실어 보내도 수주·호기 날짜는 그대로
    def edit_form(pp, **kw):
        f = {"unlock_verified": "1", "name": pp["name"], "customer_name": "(주) 가상드림동탄", "customer_id": str(CUST["DT"]),
             "biz_div": "T", "project_type": "NEW_EQUIP", "po_type": pp.get("po_type") or "신규", "status": "진행중",
             "equip_name": "기능검사기", "model": "PBA", "shipment_form": "ASSEMBLY", "currency": "KRW", "is_export": "0",
             "unit_qty": "1"}
        f.update(kw)
        with contextlib.redirect_stdout(io.StringIO()):
            return cl.post("/projects/%d/edit" % pp["id"], data=f)
    before = [(o["order_date"], o["due_date"]) for o in orders_of(P["id"])]
    ib = [(i["order_date"], i["due_date"]) for o in orders_of(P["id"]) for i in items_of(o["id"])]
    pr = proj("z14-P")
    rr = edit_form(pr, order_date="2027-01-01", due_date="2027-01-31")
    after = [(o["order_date"], o["due_date"]) for o in orders_of(P["id"])]
    ia = [(i["order_date"], i["due_date"]) for o in orders_of(P["id"]) for i in items_of(o["id"])]
    check("14 수주 2건 공통 저장에 날짜 → 저장은 되고(303 → 상세) 수주·호기 날짜는 그대로",
          rr.status_code == 303 and rr.headers.get("location") == "/project/%d" % P["id"] and before == after and ib == ia,
          (rr.status_code, rr.headers.get("location"), before, after))
    rr1 = edit_form(P1, order_date="2026-10-02", due_date="2026-12-24")
    check("15 수주 1건 프로젝트 공통 저장 날짜 → 예전처럼 받음(프로젝트 납기 2026-12-24)",
          rr1.status_code == 303 and rr1.headers.get("location") == "/project/%d" % P1["id"] and proj("z14-ONE")["due_date"] == "2026-12-24",
          (rr1.status_code, proj("z14-ONE")["due_date"]))

    # 수정 화면이 쓰는 저장 경로 = 상세 수주 카드와 같은 경로 — 이 수주만 바뀐다
    with contextlib.redirect_stdout(io.StringIO()):
        q = cl.post("/sales/orders/%d/quick-edit" % S2["id"], data={"due_date": "2026-12-15", "ship_to": "가상 공장2"})
    a1, a2 = orders_of(P["id"])
    check("16 이 수주만 저장(납기·납품처) → 그 수주만 바뀜 · 다른 수주 그대로",
          q.json().get("ok") and a2["due_date"] == "2026-12-15" and a2["ship_to"] == "가상 공장2" and a1["due_date"] == S1["due_date"],
          (q.json(), a2["due_date"], a1["due_date"]))
    with contextlib.redirect_stdout(io.StringIO()):
        q2 = cl.post("/sales/schedule/cell", json={"kind": "project", "ref_id": P["id"], "field": "po_type", "value": "수리", "so_oid": str(S2["id"])})
    a1, a2 = orders_of(P["id"])
    check("17 PO유형(so_oid) → 그 수주만", q2.json().get("ok") and a2.get("po_type") == "수리" and (a1.get("po_type") or "") != "수리",
          (q2.json(), a1.get("po_type"), a2.get("po_type")))

print()
print("=" * 78)
print("§2 실제 화면 — Chromium · 시험용 서버(임시 DB)")
print("=" * 78)
DRIVER = r'''
import json, sys
from playwright.sync_api import sync_playwright
BASEURL, PID, SO2, SHOTDIR, SHOTONLY = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] == "1"
out = {"page_errors": [], "cases": {}}
def shot(pg, name):
    if SHOTDIR:
        pg.screenshot(path=SHOTDIR + "/" + name + ".png", full_page=False)
with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 1500, "height": 1100})
    ctx.add_init_script("try{sessionStorage.setItem('knkAutoReloadTs', String(Date.now()));}catch(e){}")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: out["page_errors"].append(str(e)[:200]))
    dialogs = []
    pg.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
    def go(url):
        pg.goto(BASEURL + url)
        try:
            pg.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
    try:
        go("/projects/" + PID + "/edit")
        if SHOTONLY:
            pg.click("#pfUnlockBtn"); pg.wait_for_timeout(300)
            shot(pg, "before_1_top")
            pg.locator("#pfConfirmRows").scroll_into_view_if_needed(); pg.evaluate("window.scrollBy(0, -250)"); pg.wait_for_timeout(200)
            shot(pg, "before_2_dates")
            out["cases"]["shot"] = True
        else:
            st = pg.evaluate("""()=>({now:(document.getElementById('z14Now')||{}).innerText||'',
                 secVis: Array.from(document.querySelectorAll('.pf-section')).some(s=>s.offsetParent!==null),
                 panVis: Array.from(document.querySelectorAll('.z14-panel')).filter(s=>s.offsetParent!==null).length})""")
            out["cases"]["A"] = st
            shot(pg, "after_1_common")
            pg.click('.z14-tab[data-so="' + SO2 + '"]'); pg.wait_for_timeout(200)
            st2 = pg.evaluate("""()=>({now:(document.getElementById('z14Now')||{}).innerText||'', url: location.search,
                 secVis: Array.from(document.querySelectorAll('.pf-section')).some(s=>s.offsetParent!==null),
                 pan: Array.from(document.querySelectorAll('.z14-panel')).filter(s=>s.offsetParent!==null).map(s=>s.dataset.so),
                 due: (document.querySelector('.z14-panel[data-so="__SO__"] [data-field=due_date]')||{}).value})""".replace("__SO__", SO2))
            out["cases"]["B"] = st2
            shot(pg, "after_2_so_picked")
            # 잠금 해제 전 저장 → 알림 · 저장 안 됨
            dialogs.clear()
            pg.click('.z14-panel[data-so="' + SO2 + '"] .z14-save'); pg.wait_for_timeout(300)
            out["cases"]["C"] = {"dialogs": list(dialogs)}
            # 잠금 해제 → 납기·납품처·PO유형 고치고 이 수주만 저장
            dialogs.clear()
            pg.click("#pfUnlockBtn"); pg.wait_for_timeout(300)
            sel = '.z14-panel[data-so="' + SO2 + '"] '
            pg.evaluate("""(sel)=>{ function setv(q,v){ var el=document.querySelector(sel+q); el.value=v;
                 el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); }
                 setv('[data-field=due_date]','2027-02-14'); setv('[data-field=ship_to]','가상 공장3'); setv('[data-po]','개조'); }""", sel)
            pg.wait_for_timeout(150)
            shot(pg, "after_3_editing")
            with pg.expect_navigation(timeout=15000):
                pg.click(sel + ".z14-save")
            try:
                pg.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            st4 = pg.evaluate("""()=>({url: location.search, ok: (document.body.innerText||'').indexOf('저장됨')>=0,
                 now:(document.getElementById('z14Now')||{}).innerText||''})""")
            st4["dialogs"] = list(dialogs)
            out["cases"]["D"] = st4
            shot(pg, "after_4_saved")
            # 바꾼 뒤 다른 수주로 넘어가면 확인창
            dialogs.clear()
            pg.evaluate("""(sel)=>{ var el=document.querySelector(sel+'[data-field=ship_to]'); el.value='임시'; el.dispatchEvent(new Event('input',{bubbles:true})); }""", sel)
            pg.click('.z14-tab[data-so=""]'); pg.wait_for_timeout(200)
            st5 = pg.evaluate("""(sel)=>({ship:(document.querySelector(sel+'[data-field=ship_to]')||{}).value, secVis: Array.from(document.querySelectorAll('.pf-section')).some(s=>s.offsetParent!==null)})""", sel)
            st5["dialogs"] = list(dialogs)
            out["cases"]["E"] = st5
            pg.locator("#pfConfirmRows").scroll_into_view_if_needed(); pg.evaluate("window.scrollBy(0, -250)"); pg.wait_for_timeout(200)
            shot(pg, "after_5_common_dates")
    except Exception as e:
        out["cases"]["exc"] = str(e)[:500]
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
    rr = subprocess.run([PWPY, DRV, BASEURL, str(P["id"]), S2["order_no"], SHOT_DIR, "1" if SHOT_ONLY else "0"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, env=env)
    line = [x for x in (rr.stdout or "").splitlines() if x.startswith("@@RESULT@@")]
    if line:
        res2 = json.loads(line[-1][len("@@RESULT@@"):])
        cases, page_errors = res2["cases"], res2["page_errors"]
    else:
        print("   (브라우저 쪽 출력)", (rr.stdout or "")[-800:], (rr.stderr or "")[-1500:])
        page_errors = ["(브라우저 결과 없음)"]
if SHOT_ONLY:
    check("고치기 전 화면 찍음", cases.get("shot") is True, cases)
else:
    A, B, C, Dd, E = (cases.get(k) or {} for k in ("A", "B", "C", "D", "E"))
    check("A 처음 열면 「관리번호 공통」 · 공통 칸 보임 · 수주 칸 숨김", "공통 정보" in (A.get("now") or "") and A.get("secVis") is True
          and A.get("panVis") == 0, A)
    check("B 수주 단추 누르면 그 수주 칸만 · 공통 칸 숨김 · 「지금 고치는 것: 수주 …」 · 주소에 ?so= · 납기 = 그 수주 값",
          B.get("pan") == [S2["order_no"]] and B.get("secVis") is False and S2["order_no"] in (B.get("now") or "")
          and ("so=" + S2["order_no"]) in (B.get("url") or "") and B.get("due") == "2026-12-15", B)
    check("C 잠금 해제 전 저장 → 「잠금 해제」 알림 · 저장 안 함", any("잠금 해제" in x for x in (C.get("dialogs") or [])), C)
    a1, a2 = orders_of(P["id"])
    check("D 잠금 해제 → 고치고 「이 수주만 저장」 → 돌아와 저장됨 표시 · 그 수주 그대로 선택",
          Dd.get("ok") is True and ("so=" + S2["order_no"]) in (Dd.get("url") or "") and S2["order_no"] in (Dd.get("now") or ""), Dd)
    check("   DB: 그 수주만 납기 2027-02-14 · 납품처 가상 공장3 · PO유형 개조 / 다른 수주 그대로",
          a2["due_date"] == "2027-02-14" and a2["ship_to"] == "가상 공장3" and a2.get("po_type") == "개조"
          and a1["due_date"] == S1["due_date"] and (a1.get("ship_to") or "") == (S1.get("ship_to") or "") and (a1.get("po_type") or "") != "개조",
          (a1["due_date"], a1.get("po_type"), a2["due_date"], a2["ship_to"], a2.get("po_type")))
    check("E 고친 채 다른 대상 누르면 확인창 → 넘어가면 고친 값 되돌림 · 공통 칸 보임",
          any("저장하지 않은 변경" in x for x in (E.get("dialogs") or [])) and E.get("ship") == "가상 공장3" and E.get("secVis") is True, E)
check("화면 스크립트 오류 0", not page_errors, page_errors)
try:
    srv.should_exit = True
except Exception:
    pass
print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
