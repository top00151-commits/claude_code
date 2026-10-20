# -*- coding: utf-8 -*-
"""z1191e 시험 — 관리자 콘솔 「사용자」 법인 책갈피(본사 · 베트남법인 · 전체)
   (대표 2026-10-20 「이 화면에서 사용자를 본사, 베트남법인 페이지를 책갈피 형태로 선택해서 볼수있게 수정해줘」)
  §1 서버(임시 DB · TestClient): 관리자 화면에 책갈피 셋 · 법인 드롭다운은 숨김 · 사용자 줄마다 법인
  §2 실제 화면(Chromium): 처음 = 본사 · 숫자 · 누르면 그 법인만 · 부서 목록도 그 법인 · 법인 바꾸면 안 보이는 사람 체크 풀림 ·
     다시 열면 마지막 책갈피 · 책갈피를 바꿔도 부서 칸 폭·검색 칸 자리 그대로 · 스크립트 오류 0 (화면 사진: 시험 폴더 임시)
  §3 바뀐 곳 원문
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191e-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191e_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                     ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                     ("must_change_pw", "INTEGER DEFAULT 0"), ("email", "TEXT"), ("rank", "TEXT"), ("team_id", "INTEGER")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    tcols = {r[1] for r in conn.execute("PRAGMA table_info(teams)")}
    if "entity" not in tcols:
        conn.execute("ALTER TABLE teams ADD COLUMN entity TEXT")
    TEAM = {}
    for key, nm, ent in (("K1", "가상설계팀", "KOR"), ("K2", "가상영업팀", "KOR"), ("V1", "가상설계팀", "VN"), ("V2", "가상생산팀", "VN")):
        conn.execute("INSERT INTO teams (name, entity, code) VALUES (?,?,?)", (nm, ent, "Z" + key))
        TEAM[key] = conn.execute("SELECT MAX(id) FROM teams").fetchone()[0]
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version) "
                 "VALUES ('가상관리자', 'admin', 'T901', 'T901', 'sso_only_no_local_password', 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T901'").fetchone())
    PEOPLE = [("가상본사1", "T801", "K1"), ("가상본사2", "T802", "K1"), ("가상본사3", "T803", "K2"), ("가상본사4", "T804", "K2"),
              ("가상베트남1", "VN801", "V1"), ("가상베트남2", "VN802", "V2"), ("가상베트남3", "VN803", "V2")]
    for nm, sb, tk in PEOPLE:
        conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, email) "
                     "VALUES (?, 'member', ?, ?, 'x', 1, 1, ?, ?)", (nm, sb, sb, TEAM[tk], sb.lower() + "@example.invalid"))
    N_ALL = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

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


print("=" * 78)
print("§1 서버")
print("=" * 78)
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.get("/admin")
h = r.text
n_vn = h.count('data-corp="베트남법인" data-dept=')
n_kr = h.count('data-corp="본사" data-dept=')
check("1 관리자 화면 · 책갈피 셋(본사·베트남법인·전체)", r.status_code == 200 and 'class="ucf-tabs"' in h
      and h.count('class="ucf-tab"') == 2 and 'class="ucf-tab all"' in h, (r.status_code, h.count('class="ucf-tab')))
check("   법인 드롭다운은 숨김(책갈피가 값을 바꾼다)", '<select id="ucfCorp" onchange="ucfApply()" style="display:none;" aria-hidden="true">' in h)
check("   사용자 줄마다 법인 — 베트남 3 · 본사 %d(관리자 포함)" % (N_ALL - 3), n_vn == 3 and n_kr == N_ALL - 3, (n_vn, n_kr, N_ALL))

print()
print("=" * 78)
print("§2 실제 화면 — Chromium · 시험용 서버(임시 DB)")
print("=" * 78)
DRIVER = r'''
import json, sys
from playwright.sync_api import sync_playwright
BASEURL, SHOT = sys.argv[1], sys.argv[2]
out = {"page_errors": []}
def st(pg):
    return pg.evaluate("""()=>{ var tabs=[].map.call(document.querySelectorAll('.ucf-tab'), function(t){ return {corp:t.getAttribute('data-corp'), on:t.classList.contains('on'), n:(t.querySelector('.n')||{}).textContent}; });
        var vis=[].filter.call(document.querySelectorAll('#usersTbl tr.urow'), function(r){ return r.style.display!=='none'; });
        var corps={}; vis.forEach(function(r){ var c=r.getAttribute('data-corp'); corps[c]=(corps[c]||0)+1; });
        var depts=[].slice.call(document.querySelectorAll('#ucfDept option')).map(function(o){ return o.value; }).filter(Boolean);
        var ds=document.getElementById('ucfDept'), q=document.getElementById('ucfQ');
        return {tabs:tabs, vis:vis.length, corps:corps, depts:depts, cnt:(document.getElementById('ucfCnt')||{}).textContent,
                sel:(document.getElementById('ucfCorp')||{}).value,
                dw:ds?Math.round(ds.getBoundingClientRect().width*10)/10:0, qx:q?Math.round(q.getBoundingClientRect().left*10)/10:0}; }""")
with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 1400, "height": 900})
    ctx.add_init_script("try{sessionStorage.setItem('knkAutoReloadTs', String(Date.now()));}catch(e){}")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: out["page_errors"].append(str(e)[:200]))
    pg.on("dialog", lambda d: d.dismiss())
    pg.goto(BASEURL + "/admin")
    try:
        pg.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    pg.wait_for_timeout(500)
    out["first"] = st(pg)
    tw = pg.query_selector("#panel-users .table-wrap")
    if tw:
        tw.screenshot(path=SHOT + "_kr.png")
    # 본사 줄 하나 체크 → 베트남법인으로 바꾸면 체크가 풀려야(안 보이는 사람 실수 삭제 막기)
    pg.evaluate("""()=>{ var r=[].filter.call(document.querySelectorAll('#usersTbl tr.urow'), function(x){ return x.style.display!=='none' && x.querySelector('.urow-chk'); })[0];
        if(r){ var c=r.querySelector('.urow-chk'); c.checked=true; c.dispatchEvent(new Event('change',{bubbles:true})); } }""")
    out["checked_before"] = pg.evaluate("()=>document.querySelectorAll('.urow-chk:checked').length")
    pg.select_option("#ucfDept", index=1)
    pg.wait_for_timeout(200)
    out["dept_kr_pick"] = pg.evaluate("()=>document.getElementById('ucfDept').value")
    pg.click('.ucf-tab[data-corp="베트남법인"]'); pg.wait_for_timeout(300)
    out["vn"] = st(pg)
    out["checked_after"] = pg.evaluate("()=>document.querySelectorAll('.urow-chk:checked').length")
    out["dept_after_switch"] = pg.evaluate("()=>document.getElementById('ucfDept').value")
    if tw:
        tw.screenshot(path=SHOT + "_vn.png")
    pg.click('.ucf-tab.all'); pg.wait_for_timeout(300)
    out["all"] = st(pg)
    # 본사로 한 번 더 갔다가(폭이 자꾸 늘지 않는지) 「전체」로 돌아와 다시 열기
    pg.click('.ucf-tab[data-corp="본사"]'); pg.wait_for_timeout(300)
    out["kr2"] = st(pg)
    pg.click('.ucf-tab.all'); pg.wait_for_timeout(300)
    pg.reload()
    try:
        pg.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    pg.wait_for_timeout(500)
    out["reload"] = st(pg)
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
check("시험용 서버 뜸(127.0.0.1 · 빈 포트 · 시작 작업 끔)", srv.started, PORT)
PWPY = find_pw_python()
check("Playwright 있는 파이썬 찾음", bool(PWPY), PWPY)
DRV = os.path.join(TMP, "pw_driver.py")
io.open(DRV, "w", encoding="utf-8").write(DRIVER)
SHOT = os.environ.get("KNK_SHOT_PREFIX") or os.path.join(TMP, "shot")
res = {}
if PWPY:
    rr = subprocess.run([PWPY, DRV, "http://127.0.0.1:%d" % PORT, SHOT], capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=600, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    line = [x for x in (rr.stdout or "").splitlines() if x.startswith("@@RESULT@@")]
    res = json.loads(line[-1][len("@@RESULT@@"):]) if line else {"page_errors": ["(브라우저 결과 없음) " + (rr.stderr or "")[-600:]]}
F1, VN, AL, RL = res.get("first") or {}, res.get("vn") or {}, res.get("all") or {}, res.get("reload") or {}
tab = lambda s, c: next((t for t in (s.get("tabs") or []) if t.get("corp") == c), {})   # noqa: E731
n_kr_all = N_ALL - 3
check("A 처음 = 「본사」 책갈피 · 본사 사람만(%d명) · 「%d명 표시」" % (n_kr_all, n_kr_all),
      tab(F1, "본사").get("on") and F1.get("vis") == n_kr_all and set((F1.get("corps") or {}).keys()) == {"본사"}
      and F1.get("cnt") == "%d명 표시" % n_kr_all, F1)
check("   숫자: 본사 %d · 베트남법인 3 · 전체 %d" % (n_kr_all, N_ALL),
      tab(F1, "본사").get("n") == str(n_kr_all) and tab(F1, "베트남법인").get("n") == "3" and tab(F1, "").get("n") == str(N_ALL),
      F1.get("tabs"))
check("   부서 목록 = 본사 부서만", bool(F1.get("depts")) and all(not d.startswith("베트남") for d in F1.get("depts")), F1.get("depts"))
check("B 「베트남법인」 → 베트남 사람만 3명 · 부서 목록 = 베트남 부서만",
      tab(VN, "베트남법인").get("on") and VN.get("vis") == 3 and set((VN.get("corps") or {}).keys()) == {"베트남법인"}
      and bool(VN.get("depts")) and all(d.startswith("베트남") for d in VN.get("depts")), VN)
check("   법인을 바꾸면 안 보이게 된 사람의 체크가 풀림(실수 삭제 막기) · 고른 본사 부서도 풀림",
      res.get("checked_before") == 1 and res.get("checked_after") == 0 and bool(res.get("dept_kr_pick"))
      and res.get("dept_after_switch") == "", (res.get("checked_before"), res.get("checked_after"), res.get("dept_kr_pick"), res.get("dept_after_switch")))
check("C 「전체」 → 모두 %d명" % N_ALL, tab(AL, "").get("on") and AL.get("vis") == N_ALL, AL)
check("D 다시 열면 마지막 책갈피(전체) 그대로", tab(RL, "").get("on") and RL.get("vis") == N_ALL, RL)
K2 = res.get("kr2") or {}
_dw = [s.get("dw") for s in (F1, VN, AL, K2, RL)]
_qx = [s.get("qx") for s in (F1, VN, AL, K2, RL)]
check("E 책갈피를 바꿔도 부서 칸 폭·검색 칸 자리 그대로(본사·베트남·전체·본사 다시·다시 열기)",
      all(_dw) and max(_dw) - min(_dw) <= 0.5 and all(_qx) and max(_qx) - min(_qx) <= 0.5, {"부서 칸 폭": _dw, "검색 칸 자리": _qx})
check("화면 스크립트 오류 0", not res.get("page_errors"), res.get("page_errors"))

print()
print("=" * 78)
print("§3 바뀐 곳 원문")
print("=" * 78)
ad = open(os.path.join(ROOT, "app", "templates", "admin.html"), encoding="utf-8").read()
check("책갈피 동작은 기존 거르기(ucfApply)를 그대로 씀 · 기억 열쇠 · 팀 탭은 그대로",
      "window.ucfTab=function(corp)" in ad and "localStorage.setItem('knkAdminUserCorp'" in ad
      and '<select id="tcfCorp" onchange="tcfApply()">' in ad)
bad = [l for l in ad.splitlines() if "z1191e" in l and "{#" not in l and ("{{" in l or "{%" in l)]
check("z1191e 스크립트 줄에 Jinja 기호 없음", not bad, bad[:2])

print()
print("결과: %d개 중 실패 %d" % (OK + FAIL, FAIL))
sys.exit(1 if FAIL else 0)
