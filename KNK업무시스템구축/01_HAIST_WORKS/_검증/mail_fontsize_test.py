# -*- coding: utf-8 -*-
"""메일 글자 크기 −·＋ 8단계 (대표 2026-11-22 「글자 크게 양옆에 +- · 양쪽 다 3단계 추가」) — 운영 무접촉 · 임시 DB(knk_mfs_*) · 가짜 사람만.

증명할 것
  ① 도구 줄 = 「− 🔠 글자 100% ＋」(받은편지함·보낸편지함·쓰기·설정 등 도구 줄이 있는 모든 메일 화면에서 돌아감)
  ② 단계(node 로 실제 실행): 80·87·93·100·110·120·130·145% · 양 끝에서 멈춤 · 가운데 = 100% · 이 기기에 저장(knkmail.fs)
     예전 「글자 크게」를 켜 둔 기기(knkmail.big=1)는 110% 에서 시작 · 110% 이상 = 예전 큰 글씨 규칙(mbx-big) + 배율
  ③ 배율은 칸 안쪽만(목록 줄·폴더 줄·읽기 칸·단독 메일 화면) · ⚙ 설정·정리 스위치도 같은 단계 · 파이썬 3.8
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
    _TMP = tempfile.mkdtemp(prefix="knk_mfs_")
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
        print("  [FAIL]", name, "<-", str(extra)[:500])


D = "@knknara.co.kr"
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x', email=NULL")
    c.execute("INSERT INTO users(id, login_id, name, rank, role, is_active, password, email) VALUES(9890,'t_me','시험신입','사원','member',1,'x','me" + D + "')")
    c.execute("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, subject, body_text, is_read, is_deleted, received_at) "
              "VALUES(9890,'in','a@x-demo.example','가짜','me" + D + "','가짜 메일','가짜',0,0,datetime('now','localtime'))")
    MID = c.execute("SELECT last_insert_rowid()").fetchone()[0]
ME = {"id": 9890, "role": "member", "name": "시험신입", "rank": "사원", "login_id": "t_me", "email": "me" + D, "lang": "ko"}
m.get_user = lambda req: ME
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})

print("① 도구 줄 「− 🔠 글자 100% ＋」 · 모든 메일 화면")
pages = {"받은편지함": "/mail/inbox", "메일 보기": "/mail/%d" % MID, "보낸편지함": "/mail/sent", "쓰기": "/mail/compose",
         "설정·정리": "/mail/tools", "임시보관함": "/mail/drafts"}
H = {}
for nm, u in pages.items():
    r = k.get(u + ("&" if "?" in u else "?") + "app=1")
    H[nm] = r.text
    check("%s: − ＋ 단추와 크기 조각(함수 정의)이 함께" % nm, r.status_code == 200 and 'id="mtFsDn"' in r.text and 'id="mtFsUp"' in r.text
          and "window.mailFsSet=" in r.text and 'id="mtFsPct"' in r.text, r.status_code)
h = H["받은편지함"]
tools = h[h.find('id="mailTools"'):h.find('</nav>', h.find('id="mailTools"'))]
check("순서: − → 🔠 글자 → ＋ (테마와 설정·정리 사이)",
      tools.find('id="mtThemeBtn"') < tools.find('id="mtFsDn"') < tools.find('id="mtBigTop"') < tools.find('id="mtFsUp"') < tools.find('href="/mail/tools"'))
check("가운데 = 보통(100%)으로 · 양옆 = 한 단계씩", 'onclick="mailFsSet(0)"' in tools and 'onclick="mailFsStep(-1)"' in tools and 'onclick="mailFsStep(1)"' in tools)
check("몇 % 인지는 좁은 화면에서도 보임(글자 「글자」만 숨김)", '<span class="t">글자</span><b class="fs-pct" id="mtFsPct">' in tools)
check("받은편지함·메일 보기는 본문 안에도 크기 조각(화면 전환 때도 돎)",
      h.rfind("window.mailFsSet=") > h.find('<main class="main"') > 0 and H["메일 보기"].rfind("window.mailFsSet=") > H["메일 보기"].find('<main class="main"') > 0)

print("② 단계 — node 로 실제 실행")
fs = io.open("app/templates/_v5_partials/mail_fs.html", encoding="utf-8").read()
js = re.search(r"<script>(.*?)</script>", fs, re.S).group(1)
node = shutil.which("node")
if node:
    harness = r"""
var store = {}; var cls = {}; var attr = {}; var prop = {};
var localStorage = {getItem:function(k){ return Object.prototype.hasOwnProperty.call(store,k) ? store[k] : null; },
  setItem:function(k,v){ store[k]=String(v); }, removeItem:function(k){ delete store[k]; }};
var document = {documentElement:{classList:{toggle:function(c,on){ cls[c]=!!on; }},
  setAttribute:function(a,v){ attr[a]=v; }, removeAttribute:function(a){ delete attr[a]; },
  style:{setProperty:function(p,v){ prop[p]=v; }, removeProperty:function(p){ delete prop[p]; }}}};
var window = globalThis;
function run(){ %s }
function snap(){ return {L:mailFsLevel(), pct:mailFsPct(mailFsLevel()), big:!!cls['mbx-big'], z:prop['--mfz']||'', mfz:attr['data-mfz']||'', fs:store['knkmail.fs'], old:store['knkmail.big']}; }
var out = {};
run(); out.fresh = snap();
store = {'knkmail.big':'1'}; cls={}; attr={}; prop={}; run(); out.legacy = snap();
var ups = []; for (var i=0;i<5;i++){ mailFsStep(1); ups.push(snap()); } out.ups = ups;
var dns = []; for (var i=0;i<9;i++){ mailFsStep(-1); dns.push(snap()); } out.dns = dns;
mailFsSet(0); out.reset = snap();
mailFsSet(99); out.clamp = snap();
store['knkmail.fs']='abc'; mailFsApply(); out.junk = snap();
console.log(JSON.stringify(out));
""" % js
    fd, p = tempfile.mkstemp(suffix=".js")
    os.write(fd, harness.encode("utf-8"))
    os.close(fd)
    r = subprocess.run([node, p], capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL)
    os.remove(p)
    try:
        o = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        o = {}
        check("node 실행", False, r.stderr[:400])
    if o:
        check("처음 기기 = 100% · 배율 없음 · 큰 글씨 규칙 꺼짐", o["fresh"]["pct"] == 100 and not o["fresh"]["big"] and not o["fresh"]["z"], o["fresh"])
        check("예전 「글자 크게」 켠 기기 = 110%(큰 글씨 규칙 그대로)", o["legacy"]["pct"] == 110 and o["legacy"]["big"] and not o["legacy"]["z"], o["legacy"])
        check("＋ : 120 → 130 → 145 → 145(끝에서 멈춤)", [x["pct"] for x in o["ups"]] == [120, 130, 145, 145, 145], [x["pct"] for x in o["ups"]])
        check("110% 넘으면 큰 글씨 규칙 + 배율(1.1·1.2·1.33)", [x["z"] for x in o["ups"][:3]] == ["1.1", "1.2", "1.33"] and all(x["big"] for x in o["ups"]), o["ups"][:3])
        check("저장 = knkmail.fs · 옛 knkmail.big 은 지움", o["ups"][0]["fs"] == "2" and o["ups"][0].get("old") is None, o["ups"][0])
        check("− : 130·120·110·100·93·87·80·80·80(끝에서 멈춤)", [x["pct"] for x in o["dns"]] == [130, 120, 110, 100, 93, 87, 80, 80, 80], [x["pct"] for x in o["dns"]])
        check("100% 아래 = 큰 글씨 규칙 꺼짐 · 배율 0.93·0.87·0.8", [x["z"] for x in o["dns"][4:7]] == ["0.93", "0.87", "0.8"] and not any(x["big"] for x in o["dns"][4:]), o["dns"][4:7])
        check("가운데 = 100% · 배율 지움", o["reset"]["pct"] == 100 and not o["reset"]["z"] and not o["reset"]["mfz"], o["reset"])
        check("이상한 값 = 145% 로 막음 · 글자 저장값 = 100%", o["clamp"]["pct"] == 145 and o["junk"]["pct"] == 100, (o["clamp"], o["junk"]))
else:
    print("  (node 없음 — 단계 실행 시험 건너뜀)")

print("③ 배율 범위 · 설정 화면")
vs = io.open("app/templates/_v5_partials/mail_view_styles.html", encoding="utf-8").read()
check("배율은 칸 안쪽만(폴더 줄·목록 줄·읽기 칸·단독 메일)",
      "html[data-mfz] .mbx-side > *, html[data-mfz] .mbx-list > *, html[data-mfz] #readPane > *, html[data-mfz] .mv-zoom > *{zoom:var(--mfz,1)}" in vs)
check("단독 메일 화면·새 창에 감싸는 칸", 'class="mv-zoom"' in H["메일 보기"] and 'class="mv-zoom"' in io.open("app/templates/mail_view_win.html", encoding="utf-8").read())
t = H["설정·정리"]
check("⚙ 설정·정리 「글자 크게 보기」 = 같은 단계(켬 110% · 도구 줄 80%~145% 안내)", "mtBigToggle()" in t and "80%~145%" in t and "mailFsSet(mailFsLevel()>=1 ? 0 : 1)" in t)
bad = 0
if node:
    for nm in ("받은편지함", "메일 보기", "설정·정리"):
        for s in re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", H[nm], re.S):
            if not s.strip():
                continue
            fd, p = tempfile.mkstemp(suffix=".js")
            os.write(fd, s.encode("utf-8"))
            os.close(fd)
            r = subprocess.run([node, "--check", p], capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL)
            if r.returncode:
                bad += 1
                print(r.stderr[:300])
            os.remove(p)
    check("스크립트 문법(node) — 받은편지함·메일 보기·설정", bad == 0, bad)

print("\n결과: %d 통과 · %d 실패" % (P, F))
sys.exit(1 if F else 0)
