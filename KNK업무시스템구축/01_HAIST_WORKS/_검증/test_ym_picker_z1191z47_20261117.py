# -*- coding: utf-8 -*-
"""z1191z47 시험 (대표 2026-11-17 「작업일정표 월 선택이 너무 어려워 · 2026년 11월을 누르면 연·월이 보여서 바로 이동」)
  ① 월 보기: 「📅 2026년 5월 ▾」 단추 + 연·월 판(◀ 연도 ▶ · 1~12월 · 이번 달로) · 고른 달·이번 달 표시값
  ② 판 스크립트가 문법 오류 없이 돈다(node) · 이동 주소 = 이전 달 링크(사업부·소모품 칸·찾기어)에서 ym 만
  ③ 기간 보기에는 판 없음(기간 표시 그대로) · 화살표·오늘 링크 그대로
  임시 DB · TestClient · 운영 아님
"""
import contextlib, io, os, re, sys, tempfile, subprocess, shutil
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z47-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z47_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상관리자', 'admin', 'T945', 'T945', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T945'").fetchone())

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from datetime import date  # noqa: E402
M.get_user = lambda request: ADMIN
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0


def check(cond, msg, got=None):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", msg)
    else:
        FAIL += 1; print("  ❌", msg, "" if got is None else ("  ← %r" % (got,)))


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


print("§1 월 보기: 단추 + 연·월 판")
html = q(cl.get, "/sales/schedule?ym=2026-05&biz=C&cbiz=T").text
check('id="ymPickBtn"' in html and "📅 2026년 5월" in html and 'onclick="schedYmPick(event)"' in html, "「📅 2026년 5월 ▾」 = 누르는 단추")
m = re.search(r'<div class="ym-pop" id="ymPop" hidden data-y="(\d+)" data-m="(\d+)" data-ty="(\d+)" data-tm="(\d+)"', html)
t = date.today()
check(m and m.groups() == ("2026", "5", str(t.year), str(t.month)), "판 기본값: 보고 있는 달 2026-5 · 이번 달 %d-%d" % (t.year, t.month), m and m.groups())
check(len(re.findall(r'class="ym-mb" data-m="\d+"', html)) == 12 and "1월</button>" in html and "12월</button>" in html, "1월~12월 단추 12개")
check(html.count('class="ym-yb"') == 2 and "이번 달로" in html, "◀ 연도 ▶ · 「이번 달로」")
check('title="이전 달">←</a>' in html and 'title="다음 달">→</a>' in html, "← → 화살표는 그대로")
prev = re.search(r'<a href="(\?ym=2026-04[^"]*)" title="이전 달">', html)
check(prev and "biz=C" in prev.group(1) and "cbiz=T" in prev.group(1), "이동 주소의 바탕 = 이전 달 링크(사업부·소모품 칸 유지 · 찾기어는 화면이 링크에 맞춰 둠)", prev and prev.group(1))

print("§2 판 스크립트(node 로 문법·동작)")
sc = re.search(r"<script>\s*/\* z1191z47:.*?</script>", html, re.S)
check(sc is not None, "판 스크립트 있음")
node = shutil.which("node")
if sc and node:
    js = sc.group(0)[len("<script>"):-len("</script>")]
    harness = r"""
var hrefs=[]; var listeners={};
function cls(){ var s=new Set(); return {toggle:function(c,on){ if(on) s.add(c); else s.delete(c); }, add:function(c){s.add(c)}, has:function(c){return s.has(c)}}; }
var mbs=[]; for(var i=1;i<=12;i++){ mbs.push({dataset:{m:String(i)}, classList:cls(), closest:function(sel){ return sel=='.ym-mb'?this:null; }}); }
var pop={hidden:true, dataset:{y:'2026', m:'5', ty:'2026', tm:'11'}, style:{}, querySelectorAll:function(){ return mbs; },
  contains:function(x){ return mbs.indexOf(x)>=0 || x===yb || x===td; }, getBoundingClientRect:function(){ return {right:300}; }};
var yb={dataset:{yd:'1'}, closest:function(sel){ return sel=='.ym-yb'?this:null; }};
var td={closest:function(sel){ return sel=='.ym-today'?this:null; }};
var ylab={textContent:''}, btn={setAttribute:function(){}}, veil={classList:cls()}, vtxt={textContent:''};
var prevA={href:'https://x.test/sales/schedule?ym=2026-04&biz=C&cust=KNK'};
var document={getElementById:function(id){ return {ymPop:pop, ymPopY:ylab, ymPickBtn:btn, schedNavVeil:veil, schedNavVeilTxt:vtxt}[id]||null; },
  querySelector:function(){ return prevA; }, addEventListener:function(t,f){ listeners[t]=f; }};
var window={innerWidth:1600}; var location={href:'https://x.test/sales/schedule?ym=2026-05', set _h(v){}};
""" + js + r"""
window.schedYmPick({stopPropagation:function(){}});
var out={open:!pop.hidden, ylab:ylab.textContent, sel:mbs.filter(function(b){return b.classList.has('is-sel')}).map(function(b){return b.dataset.m})};
listeners.click({target:yb});
out.y2=ylab.textContent; out.sel2=mbs.filter(function(b){return b.classList.has('is-sel')}).length;
listeners.click({target:mbs[2]});
out.go=location.href; out.closed=pop.hidden; out.veil=vtxt.textContent;
pop.hidden=true; window.schedYmPick(null); listeners.click({target:td}); out.today=location.href;
pop.hidden=true; window.schedYmPick(null); listeners.keydown({key:'Escape'}); out.esc=pop.hidden;
console.log(JSON.stringify(out));
"""
    p = os.path.join(TMP, "h.js"); open(p, "w", encoding="utf-8").write(harness)
    r = subprocess.run([node, p], capture_output=True, text=True, encoding="utf-8")
    try:
        import json
        o = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        o = {"err": (r.stderr or r.stdout)[-600:]}
    check(o.get("open") and o.get("ylab") == "2026년" and o.get("sel") == ["5"], "누르면 판 열림 · 2026년 · 5월 표시", o)
    check(o.get("y2") == "2027년" and o.get("sel2") == 0, "▶ 누르면 2027년(고른 달 표시는 그 해에만)", o)
    check(o.get("go") == "/sales/schedule?ym=2027-03&biz=C&cust=KNK" and o.get("closed") and o.get("veil") == "2027년 3월 불러오는 중…",
          "3월 누르면 → ym=2027-03 · 사업부·찾기어 그대로 · 판 닫힘 · 「불러오는 중」", o)
    check(o.get("today") == "/sales/schedule?ym=2026-11&biz=C&cust=KNK", "「이번 달로」 → 이번 달", o)
    check(o.get("esc") is True, "Esc 로 닫힘", o)
else:
    check(False, "node 없음 — 스크립트 동작 시험 못 함")

print("§3 기간 보기 · 찾기(전 기간)에는 판 없음")
html = q(cl.get, "/sales/schedule?pf=2026-01-01&pt=2026-03-31").text
check('id="ymPickBtn"' not in html and "📅 기간 2026-01-01 ~ 2026-03-31" in html and "↩ 월 보기" in html, "기간 보기 = 지금처럼 기간 표시 + 월 보기로")
html = q(cl.get, "/sales/schedule?cust=KNK").text
check('id="ymPickBtn"' not in html and "↩ 월 보기" in html, "「전체에서 찾기」(전 기간 목록) = 지금처럼 · 월 보기로 돌아간 뒤 판 사용")

print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
