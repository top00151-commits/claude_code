# -*- coding: utf-8 -*-
"""z1190b 시험 — 상세 화면 「프로젝트 정보」 배열 (대표 「화면이 배열이 너무 안맞게 나오는데」 · 013T2606 · A안)

  상황: 위 5줄에 아주 긴 품명(R3/BOT PIN BLOCK SET(BOT,MID,FLOATING),…)이 보이는 제품 수주 → 고치기 전엔 수주액 상자가
        619px 까지 늘고 왼쪽 정보 칸이 379px(폭 1366)로 눌려 값이 6.8줄까지 꺾였다.
  확인(Chromium · 폭 1366·1600): 수주액 상자 340~460px · 정보 칸 값 3줄 이하 · 좁으면 2쌍(4칸)·넓으면 3쌍(6칸) ·
        긴 품명 「…」+ 마우스 올리면 전체(title) · 짧은 품명 프로젝트는 예전처럼 · 스크립트 오류 0 · 원문
"""
import contextlib
import io
import json
import os
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1190b-test-only-not-a-real-key"   # 시험용 가짜 값
import app.database as D  # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1190b_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    # z1191g(2026-10-21 대표): 관리자는 역할만으로 매출·자재가 열리지 않는다 → 이 시험의 가상 관리자는 센터 4칸을 켠 관리자로
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상관리자', 'admin', 'T901', 'T901', 'x', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T901'").fetchone())
    cc = {r[1] for r in c.execute("PRAGMA table_info(customers)")}
    for col in ("alias", "country"):
        if col not in cc:
            c.execute("ALTER TABLE customers ADD COLUMN %s TEXT" % col)
    c.execute("INSERT INTO customers (name, alias, country) VALUES ('(주) 가상드림', '가상드림(아산)', '')")
    ASAN = c.execute("SELECT id FROM customers WHERE alias='가상드림(아산)'").fetchone()[0]
import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

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


BASE = {"quick": "1", "biz_div": "T", "project_type": "NEW_EQUIP", "status": "진행중", "confirm_now": "1",
        "order_date": "2026-10-02", "due_date": "2026-10-20", "equip_name": "기능검사기(UK4S)", "model": "SM-S956 SUB",
        "currency": "KRW", "is_export": "0"}
LONG = "R3/BOT PIN BLOCK SET(BOT,MID,FLOATING),PIN BLOCK PCB(TOP),TOP PIN BLOCK"
NAMES = ["핀블럭세트", "핀블럭PCB", "탑핀블럭", "메인플로팅"]
PRICES = ["532000", "76000", "171000", "171000"]


def mk(name, first_items):
    with contextlib.redirect_stdout(io.StringIO()):
        cl.post("/projects/new", data=dict(BASE, name=name, po_type="신규", customer_name="가상드림(아산)", customer_id=str(ASAN),
                                           shipment_form="SEMI", unit_price="", order_amount="0", unit_qty=str(len(first_items)),
                                           **{"it_name[]": [x[0] for x in first_items], "it_spec[]": [x[0] for x in first_items],
                                              "it_qty[]": ["1"] * len(first_items), "it_price[]": [x[1] for x in first_items]}))
    with D.db_session() as c:
        p = dict(c.execute("SELECT * FROM projects WHERE name=?", (name,)).fetchone())
    with contextlib.redirect_stdout(io.StringIO()):
        cl.post("/projects/new", data=dict(BASE, name=name, po_type="추가", mgmt_code=p["mgmt_code"], customer_name="가상드림(아산)",
                                           customer_id=str(ASAN), shipment_form="SEMI", unit_price="", order_amount="0", unit_qty="4",
                                           **{"it_name[]": NAMES, "it_spec[]": NAMES, "it_qty[]": ["1"] * 4, "it_price[]": PRICES}))
    return p


PL = mk("z1190b-LONG", [(LONG, "779000")])      # 긴 품명이 위 5줄 안(5번째)
PS = mk("z1190b-SHORT", [("핀블럭", "100000")])  # 짧은 품명만 — 예전 모양 그대로여야
check("준비: 긴 품명 프로젝트 · 짧은 품명 프로젝트", bool(PL and PS))

DRIVER = r'''
import json, sys
from playwright.sync_api import sync_playwright
BASEURL, PIDS = sys.argv[1], sys.argv[2].split(",")
out = {"page_errors": [], "m": {}}
JS = """()=>{
  var L=document.querySelector('.proj-info-left'), A=document.querySelector('.def-amt'), G=document.querySelector('.proj-info-left dl.def');
  var dds=[].slice.call(document.querySelectorAll('.proj-info-left dl.def dd'));
  var lines=dds.map(function(d){ var lh=parseFloat(getComputedStyle(d).lineHeight)||18; return Math.round((d.getBoundingClientRect().height-18)/lh*10)/10; });
  var cols=G ? getComputedStyle(G).gridTemplateColumns.split(' ').filter(Boolean).length : 0;
  var lbl=[].slice.call(document.querySelectorAll('.amt-breakdown .ab-lbl')).map(function(s){
      return {t:(s.textContent||'').trim(), cut:s.scrollWidth>s.clientWidth+1, title:s.getAttribute('title')||''}; });
  return {left: L?Math.round(L.getBoundingClientRect().width):0, amt: A?Math.round(A.getBoundingClientRect().width):0,
          cols: cols, max_lines: Math.max.apply(null, lines.concat([0])), ab: lbl};
}"""
with sync_playwright() as p:
    br = p.chromium.launch()
    for pid in PIDS:
        for w in (1366, 1600):
            ctx = br.new_context(viewport={"width": w, "height": 900})
            ctx.add_init_script("try{sessionStorage.setItem('knkAutoReloadTs', String(Date.now()));}catch(e){}")
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: out["page_errors"].append(str(e)[:200]))
            pg.goto(BASEURL + "/project/" + pid)
            try:
                pg.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            pg.wait_for_timeout(500)
            out["m"][pid + "@" + str(w)] = pg.evaluate(JS)
            ctx.close()
    br.close()
print("@@RESULT@@" + json.dumps(out, ensure_ascii=False))
'''


def find_pw_python():
    for c in (sys.executable, os.environ.get("KNK_PW_PY", ""),
              os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python312\python.exe"), "python"):
        if not c:
            continue
        try:
            if subprocess.run([c, "-c", "import playwright.sync_api"], capture_output=True, timeout=60).returncode == 0:
                return c
        except Exception:
            pass
    return None


import uvicorn  # noqa: E402

_sk = socket.socket(); _sk.bind(("127.0.0.1", 0)); PORT = _sk.getsockname()[1]; _sk.close()
srv = uvicorn.Server(uvicorn.Config(M.app, host="127.0.0.1", port=PORT, lifespan="off", log_level="warning"))
threading.Thread(target=srv.run, daemon=True).start()
for _ in range(150):
    if srv.started:
        break
    time.sleep(0.1)
check("시험용 서버 뜸(127.0.0.1 · 빈 포트 · 시작 작업 끔)", srv.started, PORT)
PWPY = find_pw_python()
check("Playwright 있는 파이썬 찾음", bool(PWPY), PWPY)
DRV = os.path.join(TMP, "drv.py")
io.open(DRV, "w", encoding="utf-8").write(DRIVER)
m, errs = {}, []
if PWPY:
    rr = subprocess.run([PWPY, DRV, "http://127.0.0.1:%d" % PORT, "%d,%d" % (PL["id"], PS["id"])], capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=600, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    line = [x for x in (rr.stdout or "").splitlines() if x.startswith("@@RESULT@@")]
    if line:
        res = json.loads(line[-1][len("@@RESULT@@"):])
        m, errs = res["m"], res["page_errors"]
    else:
        print("   (브라우저 쪽 출력)", (rr.stdout or "")[-600:], (rr.stderr or "")[-1200:])
        errs = ["(브라우저 결과 없음)"]
L1, L2 = m.get("%d@1366" % PL["id"], {}), m.get("%d@1600" % PL["id"], {})
S1, S2 = m.get("%d@1366" % PS["id"], {}), m.get("%d@1600" % PS["id"], {})
longs = [x for x in (L1.get("ab") or []) if x["t"] == LONG or x["title"] == LONG]
check("A 긴 품명 · 폭 1366: 수주액 상자 340~460px(고치기 전 619)", 340 <= L1.get("amt", 0) <= 460, L1.get("amt"))
check("   왼쪽 정보 칸 500px 이상(고치기 전 379) · 2쌍(4칸) · 값 3줄 이하(고치기 전 6.8)",
      L1.get("left", 0) >= 500 and L1.get("cols") == 4 and L1.get("max_lines", 9) <= 3, (L1.get("left"), L1.get("cols"), L1.get("max_lines")))
check("   긴 품명은 「…」로 잘리고 마우스 올리면 전체(title)", bool(longs) and longs[0]["cut"] and longs[0]["title"] == LONG, longs[:1])
check("B 긴 품명 · 폭 1600: 상자 460px 이하 · 정보 3쌍(6칸) · 값 3줄 이하",
      L2.get("amt", 999) <= 460 and L2.get("cols") == 6 and L2.get("max_lines", 9) <= 3, (L2.get("amt"), L2.get("cols"), L2.get("max_lines")))
check("C 짧은 품명 · 폭 1600: 예전처럼 상자 340px · 정보 3쌍(6칸)",
      S2.get("amt") == 340 and S2.get("cols") == 6, (S2.get("amt"), S2.get("cols")))
check("   짧은 품명 · 폭 1366: 상자 340px · 값 3줄 이하(좁으면 2쌍)", S1.get("amt") == 340 and S1.get("max_lines", 9) <= 3,
      (S1.get("amt"), S1.get("cols"), S1.get("max_lines")))
check("   짧은 품명은 안 잘림 · title 은 같은 글", all((not x["cut"]) and x["title"] == x["t"] for x in (S2.get("ab") or [])), S2.get("ab"))
check("화면 스크립트 오류 0", not errs, errs)

css = io.open(os.path.join(ROOT, "static", "css", "project_detail.css"), encoding="utf-8").read()
tpl = io.open(os.path.join(ROOT, "app", "templates", "project_detail.html"), encoding="utf-8").read()
check("원문: 상자 fit-content(460px) · 정보 칸 container · 2쌍/1쌍 규칙 · 900px 이하 한 줄 다시",
      "fit-content(460px)" in css and ".proj-info-left { container-type: inline-size; }" in css
      and "@container (max-width: 760px)" in css and "@container (max-width: 470px)" in css
      and css.rfind("@media (max-width: 900px) { .proj-info-2col { grid-template-columns: 1fr; }") > css.find("fit-content(460px)"))
check("원문: 수주액 줄 품명 title(z1190b)", '<span class="ab-lbl" title="{{ _ab_txt }}">' in tpl)
print("결과: %d개 중 실패 %d" % (OK + FAIL, FAIL))
sys.exit(1 if FAIL else 0)
