# -*- coding: utf-8 -*-
"""메일함 칸 분리줄 끌기 (대표 2026-11-22 「분리줄이 마우스 클릭한 상태로 이동시키고 클릭을 안 했는데도 계속 잡혀 있어서 막 움직여요」) — 운영 무접촉 · 임시 DB.

까닭
  읽기 칸 메일 본문은 페이지 안의 작은 창(iframe). 분리줄을 끌다가 그 위나 창 밖에서 손을 떼면
  「뗐다」(mouseup)가 메일함 화면에 오지 않아 끌기가 끝나지 않음 → 손을 뗀 뒤에도 분리줄이 마우스를 따라감.
고친 것(이 시험이 지킴)
  ① 끄는 동안 iframe 이 마우스를 못 가져가게(pointer-events:none) · 끝나면 원래 값으로
  ② 움직일 때 왼쪽 단추가 안 눌려 있으면 바로 끝 · 창이 포커스를 잃거나 화면이 가려져도 끝
  ③ 옆 분리줄(폭)·아래 보기 분리줄(높이) 둘 다 같은 공용 함수(mbxDragGuard) · 메일 쓰기 그림 자르기 틀도 단추 확인
  (실제 마우스 끌기 = 시연 서버에서 확인 · 작업기록 참고)
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
os.environ["KNK_RUN_MAIL_FETCH"] = "0"

_so = sys.stdout
sys.stdout = io.StringIO()
try:
    from cryptography.fernet import Fernet
    os.environ.setdefault("KNK_MAIL_KEY", Fernet.generate_key().decode())
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_msd_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
finally:
    sys.stdout = _so
from starlette.testclient import TestClient  # noqa: E402

P = F = 0


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:400])


D = "@knknara.co.kr"
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x', email=NULL")
    c.execute("INSERT INTO users(id, login_id, name, rank, role, is_active, password, email) VALUES(9890,'t_me','시험신입','사원','member',1,'x','me" + D + "')")
ME = {"id": 9890, "role": "member", "name": "시험신입", "rank": "사원", "login_id": "t_me", "email": "me" + D, "lang": "ko"}
m.get_user = lambda req: ME
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
h = k.get("/mail/inbox?app=1").text

print("① 받은편지함 화면 — 공용 끌기 함수")
check("공용 끌기 함수 mbxDragGuard 있음", "window.mbxDragGuard=function(cursor, onMove, onEnd){" in h)
i0 = h.find("function attachDrag(")
i1 = h.find("attachDrag('[data-g=\"1\"]'")
body = h[i0:i1]
check("옆 분리줄(폭)·아래 보기 분리줄(높이) 둘 다 공용 함수로", body.count("mbxDragGuard(") == 2 and "mbxDragGuard('col-resize'" in body and "mbxDragGuard('row-resize'" in body, body.count("mbxDragGuard("))
check("분리줄 끌기에 예전 방식(문서에 직접 mousemove·mouseup 걸기) 남지 않음",
      "document.addEventListener('mousemove',move)" not in body and "document.addEventListener('mouseup',up)" not in body)
check("두 분리줄 연결 그대로(폭 150~520 · 260~920)", "attachDrag('[data-g=\"1\"]','--mbx-c1','knkmail.c1',150,520);" in h and "attachDrag('[data-g=\"2\"]','--mbx-c2','knkmail.c2',260,920);" in h)

print("② 공용 함수 동작(node · 가짜 화면)")
g0 = h.find("window.mbxDragGuard=function")
g1 = h.find("  // 거터 드래그", g0)
src = h[g0:g1]
node = shutil.which("node")
if not node:
    check("node 있음(동작 시험)", False, "node 없음")
else:
    js = r"""
function ET(){ return {ls:{}, addEventListener:function(t,f){ (this.ls[t]=this.ls[t]||[]).push(f); },
  removeEventListener:function(t,f){ this.ls[t]=(this.ls[t]||[]).filter(function(x){ return x!==f; }); },
  fire:function(t,e){ (this.ls[t]||[]).slice().forEach(function(f){ f(e||{}); }); }, n:function(t){ return (this.ls[t]||[]).length; } }; }
function mk(){
  var document=ET(); document.body={style:{}};
  var fr={style:{pointerEvents:'auto'}, a:{}, setAttribute:function(k,v){ this.a[k]=v; }, getAttribute:function(k){ return k in this.a ? this.a[k] : null; }, removeAttribute:function(k){ delete this.a[k]; }};
  var fr2={style:{pointerEvents:''}, a:{}, setAttribute:fr.setAttribute, getAttribute:fr.getAttribute, removeAttribute:fr.removeAttribute};
  document.querySelectorAll=function(){ return [fr, fr2]; };
  var window=ET();
  return {document:document, window:window, fr:fr, fr2:fr2};
}
var out={};
function run(name, steps){
  var E=mk(), document=E.document, window=E.window, moves=[], ended=0;
  eval(SRC);
  window.mbxDragGuard('col-resize', function(ev){ moves.push(ev.clientX); }, function(){ ended++; });
  var r={peDuring:E.fr.style.pointerEvents, pe2During:E.fr2.style.pointerEvents, cursorDuring:document.body.style.cursor};
  steps(document, window);
  r.moves=moves; r.ended=ended; r.peAfter=E.fr.style.pointerEvents; r.pe2After=E.fr2.style.pointerEvents; r.cursorAfter=document.body.style.cursor;
  r.left=document.n('mousemove')+document.n('mouseup')+window.n('blur')+document.n('visibilitychange'); r.attrLeft=('data-mbx-pe' in E.fr.a);
  out[name]=r;
}
run('normal', function(d,w){ d.fire('mousemove',{buttons:1,clientX:10}); d.fire('mouseup',{buttons:0}); d.fire('mousemove',{buttons:1,clientX:99}); });
run('released_elsewhere', function(d,w){ d.fire('mousemove',{buttons:1,clientX:10}); d.fire('mousemove',{buttons:0,clientX:20}); d.fire('mousemove',{buttons:1,clientX:99}); });
run('blur', function(d,w){ d.fire('mousemove',{buttons:1,clientX:10}); w.fire('blur'); d.fire('mousemove',{buttons:1,clientX:99}); d.fire('mouseup',{}); });
run('hidden', function(d,w){ d.fire('visibilitychange'); d.fire('mousemove',{buttons:1,clientX:99}); });
run('no_buttons_prop', function(d,w){ d.fire('mousemove',{clientX:10}); d.fire('mouseup',{}); });
console.log(JSON.stringify(out));
"""
    fd, pth = tempfile.mkstemp(suffix=".js")
    os.write(fd, ("var SRC=" + json.dumps(src) + ";\n" + js).encode("utf-8"))
    os.close(fd)
    r = subprocess.run([node, pth], capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL)
    os.remove(pth)
    try:
        o = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        o = {}
        print(r.stdout[-400:], r.stderr[-600:])
    n = o.get("normal", {})
    check("끄는 동안: 본문 창(iframe) 마우스 막음 · 커서 = 좌우 화살표", n.get("peDuring") == "none" and n.get("pe2During") == "none" and n.get("cursorDuring") == "col-resize", n)
    check("보통 끌기: 움직임 따라감 → 손 떼면 끝 · 그 뒤 움직임 안 따라감", n.get("moves") == [10] and n.get("ended") == 1, n)
    check("끝나면 본문 창 원래 값으로(auto · 빈 값) · 커서 원래대로 · 표지 남지 않음", n.get("peAfter") == "auto" and n.get("pe2After") == "" and n.get("cursorAfter") == "" and n.get("attrLeft") is False, n)
    check("끝나면 걸어 둔 감시 모두 풂(계속 잡힘 없음)", n.get("left") == 0, n)
    e = o.get("released_elsewhere", {})
    check("🔴 본문 창·창 밖에서 손을 뗀 경우(뗐다 신호 없음): 다음 움직임에서 단추 안 눌림 → 바로 끝 · 더 안 따라감", e.get("moves") == [10] and e.get("ended") == 1 and e.get("left") == 0, e)
    b = o.get("blur", {})
    check("창이 포커스를 잃으면 끝(한 번만)", b.get("moves") == [10] and b.get("ended") == 1 and b.get("left") == 0, b)
    hd = o.get("hidden", {})
    check("화면이 가려지면 끝", hd.get("moves") == [] and hd.get("ended") == 1, hd)
    nb = o.get("no_buttons_prop", {})
    check("단추 정보가 없는 옛 브라우저: 예전처럼 따라가다 떼면 끝", nb.get("moves") == [10] and nb.get("ended") == 1, nb)

print("③ 메일 쓰기 그림 자르기 틀")
cp = io.open("app/templates/mail_compose.html", encoding="utf-8").read()
check("자르기 틀 끌기도 단추 안 눌리면 멈춤", "function onMove(ev){ if(!mode)return; if(typeof ev.buttons==='number' && !(ev.buttons & 1)){ mode=null; return; }" in cp)

print("④ 문법")
if node:
    bad = 0
    for s_ in re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", h, re.S):
        if not s_.strip():
            continue
        fd, pth = tempfile.mkstemp(suffix=".js")
        os.write(fd, s_.encode("utf-8"))
        os.close(fd)
        r = subprocess.run([node, "--check", pth], capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL)
        if r.returncode:
            bad += 1
            print(r.stderr[:300])
        os.remove(pth)
    check("받은편지함 스크립트 문법(node)", bad == 0, bad)

print("\n결과: %d 통과 · %d 실패" % (P, F))
sys.exit(1 if F else 0)
