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
check("가운데 = 칸별 고르기 창 · 양옆 = 모든 칸 한 단계씩", 'onclick="mailFsPanel(event)"' in tools and 'onclick="mailFsStep(-1)"' in tools and 'onclick="mailFsStep(1)"' in tools)
check("칸별 창(11-23): 폴더·목록·읽기 칸 줄 · 「모두 보통」 · ✕ 목록에 등록", 'id="mailFsPop"' in h and 'id="mailFsRows"' in h and "mailFsSet(0)" in h
      and "['#mailFsPop'," in h and "window.mailFsRows=" in h)
check("몇 % 인지는 좁은 화면에서도 보임(글자 「글자」만 숨김)", '<span class="t">글자</span><b class="fs-pct" id="mtFsPct">' in tools)
check("받은편지함·메일 보기는 본문 안에도 크기 조각(화면 전환 때도 돎)",
      h.rfind("window.mailFsSet=") > h.find('<main class="main"') > 0 and H["메일 보기"].rfind("window.mailFsSet=") > H["메일 보기"].find('<main class="main"') > 0)

print("② 단계 — node 로 실제 실행")
fs = io.open("app/templates/_v5_partials/mail_fs.html", encoding="utf-8").read()
js = re.search(r"<script>(.*?)</script>", fs, re.S).group(1)
check("화면에 서버 기억 값이 실려 옴(MAIL_FS_SRV)", "window.MAIL_FS_SRV={{ _fsp|tojson }};" in js)
js = js.replace("{{ _fsp|tojson }}", "SRV_INIT")
node = shutil.which("node")
if node:
    harness = r"""
var store = {}; var cls = {}; var attr = {}; var prop = {}; var VIEW = 'right'; var HAS_SPLIT = true;
var localStorage = {getItem:function(k){ return Object.prototype.hasOwnProperty.call(store,k) ? store[k] : null; },
  setItem:function(k,v){ store[k]=String(v); }, removeItem:function(k){ delete store[k]; }};
var split = {getAttribute:function(a){ return a==='data-view' ? VIEW : null; }};
var document = {readyState:'complete', querySelector:function(q){ return (q==='.mbx-split' && HAS_SPLIT) ? split : null; },
  addEventListener:function(){}, documentElement:{classList:{toggle:function(c,on){ cls[c]=!!on; }},
  setAttribute:function(a,v){ attr[a]=v; }, removeAttribute:function(a){ delete attr[a]; },
  style:{setProperty:function(p,v){ prop[p]=v; }, removeProperty:function(p){ delete prop[p]; }}}};
var window = globalThis; var SRV_INIT = null; var posts = [];
function fetch(u, o){ posts.push({u:u, b:JSON.parse(o.body), keep:!!o.keepalive}); return Promise.resolve({json:function(){ return {ok:true, saved:true}; }}); }
function run(){ window._mfsObs=false; window._mfsSynced=false; %s }
function pc(k){ return mailFsPct(mailFsPane(k)); }
function snap(){ return {L:mailFsLevel(), pct:mailFsPct(mailFsLevel()), side:pc('side'), list:pc('list'), read:pc('read'),
  big:!!cls['mfb-read'], bigl:!!cls['mfb-list'], z:prop['--mfz-read']||'', zl:prop['--mfz-list']||'', zs:prop['--mfz-side']||'',
  mfz:attr['data-mfz']||'', fs:store['knkmail.fs'], old:store['knkmail.big']}; }
var out = {};
run(); out.fresh = snap();
store = {'knkmail.big':'1'}; cls={}; attr={}; prop={}; run(); out.legacy = snap();
var ups = []; for (var i=0;i<5;i++){ mailFsStep(1); ups.push(snap()); } out.ups = ups;
var dns = []; for (var i=0;i<9;i++){ mailFsStep(-1); dns.push(snap()); } out.dns = dns;
mailFsSet(0); out.reset = snap();
mailFsSet(99); out.clamp = snap();
store['knkmail.fs']='abc'; mailFsApply(); out.junk = snap();
// 11-23 칸별 · 읽기 칸은 보기 자리마다
store = {}; cls={}; attr={}; prop={}; VIEW='right'; run();
mailFsPaneStep('read', 2); out.p1 = snap();                       // 오른쪽 읽기 칸만 120
mailFsPaneStep('list', -1); out.p2 = snap();                      // 목록만 93
VIEW='bottom'; mailFsApply(); out.p3 = snap();                    // 아래 = 기본(100)
mailFsPaneStep('read', -2); out.p4 = snap();                      // 아래 읽기 칸 87
VIEW='right'; mailFsApply(); out.p5 = snap();                     // 오른쪽으로 돌아오면 120 그대로
HAS_SPLIT=false; mailFsApply(); out.p6 = snap(); HAS_SPLIT=true;  // 따로 연 메일 = page(기본 100)
mailFsStep(1); out.p7 = snap();                                   // 모두 한 단계: 오른쪽 130·목록 100·폴더 110
VIEW='bottom'; mailFsApply(); out.p8 = snap();                    // 아래 87→93
VIEW='weird'; mailFsApply(); out.p9 = snap();                     // 모르는 보기 = 오른쪽
mailFsSet(0); VIEW='bottom'; mailFsApply(); out.p10 = snap(); out.keys = Object.keys(store).filter(function(k){ return k!=='knkmail.fs.t'; }).sort();
// 11-23 「꼭 기억 · 새로고침·업데이트해도 가장 최근 값」
store = {}; posts = []; VIEW='right'; SRV_INIT=null; run(); out.k0 = posts.length;                  // 아무것도 없음 = 안 보냄
mailFsPaneStep('read', 2); out.k1 = {n:posts.length, last:posts[posts.length-1], t:store['knkmail.fs.t']};   // 바꾸면 바로 계정에 저장
store = {}; posts = []; SRV_INIT = {'knkmail.fs.read.right':2, 'knkmail.fs.list':-1, t:5000}; run(); out.k2 = snap(); out.k2n = posts.length;   // 브라우저 저장이 지워짐 → 서버 값
store = {'knkmail.fs.read.right':'4', 'knkmail.fs.t':'9000'}; posts = []; SRV_INIT = {'knkmail.fs.read.right':2, t:5000}; run(); out.k3 = snap(); out.k3n = posts.length;   // 이 컴퓨터가 더 최근 → 그 값 · 계정에 올림
store = {'knkmail.fs.read.right':'4', 'knkmail.fs.t':'1000'}; posts = []; SRV_INIT = {'knkmail.fs.read.right':2, t:5000}; run(); out.k4 = snap(); out.k4n = posts.length;   // 다른 컴퓨터가 더 최근 → 서버 값
store = {'knkmail.fs':'2'}; posts = []; SRV_INIT = null; run(); out.k5 = {n:posts.length, b:posts[0] && posts[0].b, read:pc('read')};   // 예전에 맞춘 값(시각 없음) → 계정에 올림
store = {}; posts = []; SRV_INIT = null; run(); mailFsStep(1); mailFsSet(0); out.k6 = posts.length;   // 양옆 ±·모두 보통도 저장
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
        check("예전 「글자 크게」 켠 기기 = 110%(큰 글씨 규칙 그대로)", o["legacy"]["pct"] == 110 and o["legacy"]["big"] and o["legacy"]["bigl"] and not o["legacy"]["z"], o["legacy"])
        check("＋ : 120 → 130 → 145 → 145(끝에서 멈춤)", [x["pct"] for x in o["ups"]] == [120, 130, 145, 145, 145], [x["pct"] for x in o["ups"]])
        check("110% 넘으면 큰 글씨 규칙 + 배율(1.1·1.2·1.33) · 세 칸 함께", [x["z"] for x in o["ups"][:3]] == ["1.1", "1.2", "1.33"]
              and [x["zl"] for x in o["ups"][:3]] == ["1.1", "1.2", "1.33"] and [x["zs"] for x in o["ups"][:3]] == ["1.1", "1.2", "1.33"] and all(x["big"] for x in o["ups"]), o["ups"][:3])
        check("저장 = knkmail.fs · 옛 knkmail.big 은 지움", o["ups"][0]["fs"] == "2" and o["ups"][0].get("old") is None, o["ups"][0])
        check("− : 130·120·110·100·93·87·80·80·80(끝에서 멈춤)", [x["pct"] for x in o["dns"]] == [130, 120, 110, 100, 93, 87, 80, 80, 80], [x["pct"] for x in o["dns"]])
        check("100% 아래 = 큰 글씨 규칙 꺼짐 · 배율 0.93·0.87·0.8", [x["z"] for x in o["dns"][4:7]] == ["0.93", "0.87", "0.8"] and not any(x["big"] for x in o["dns"][4:]), o["dns"][4:7])
        check("가운데(모두 보통) = 100% · 배율 지움", o["reset"]["pct"] == 100 and not o["reset"]["z"] and not o["reset"]["mfz"], o["reset"])
        check("이상한 값 = 145% 로 막음 · 글자 저장값 = 100%", o["clamp"]["pct"] == 145 and o["junk"]["pct"] == 100, (o["clamp"], o["junk"]))
        print("  ── 11-23 칸별 · 읽기 칸 보기 자리마다")
        q = lambda k: (o[k]["side"], o[k]["list"], o[k]["read"])
        check("읽기 칸만 ＋2 → 폴더 100·목록 100·읽기 120 · 읽기 칸에만 배율", q("p1") == (100, 100, 120) and o["p1"]["z"] == "1.1" and not o["p1"]["zl"] and not o["p1"]["zs"], o["p1"])
        check("목록만 −1 → 93 (읽기 칸 120 그대로)", q("p2") == (100, 93, 120) and o["p2"]["zl"] == "0.93", o["p2"])
        check("보기를 「아래」로 → 읽기 칸 = 그 자리 값(처음은 기본 100) · 목록 93 그대로", q("p3") == (100, 93, 100), o["p3"])
        check("아래 읽기 칸 −2 → 87", q("p4") == (100, 93, 87), o["p4"])
        check("다시 「오른쪽」 → 읽기 칸 120 되살아남", q("p5") == (100, 93, 120), o["p5"])
        check("따로 연 메일 화면(page) = 그 자리 값(기본 100)", o["p6"]["read"] == 100, o["p6"])
        check("양옆 ＋(모든 칸) → 폴더 110·목록 100·오른쪽 읽기 130(차이 유지)", q("p7") == (110, 100, 130), o["p7"])
        check("…아래 읽기 칸도 함께 87→93", o["p8"]["read"] == 93, o["p8"])
        check("모르는 보기 값 = 오른쪽 값으로", o["p9"]["read"] == 130, o["p9"])
        check("모두 보통 → 모든 칸·모든 자리 100 · 칸별 저장값 지움", q("p10") == (100, 100, 100) and o["keys"] == ["knkmail.fs"], (o["p10"], o["keys"]))
        print("  ── 11-23 꼭 기억(내 계정 · 가장 최근 값)")
        check("처음(아무 값 없음) = 계정에 안 보냄", o["k0"] == 0, o["k0"])
        k1 = o["k1"]
        check("바꾸면 바로 계정에 저장(keepalive · 바꾼 시각 함께)", k1["n"] == 1 and k1["last"]["u"] == "/api/mail/ui-prefs" and k1["last"]["keep"]
              and k1["last"]["b"]["fs"].get("knkmail.fs.read.right") == "2" and int(k1["t"]) > 1000000000000, k1)
        check("브라우저 저장이 지워져도(새로고침·업데이트·캐시 비움) 계정 값으로 되살림", q("k2") == (100, 93, 120) and o["k2n"] == 0, (o["k2"], o["k2n"]))
        check("이 컴퓨터 값이 더 최근 → 그 값(145%) 쓰고 계정에 올림", o["k3"]["read"] == 145 and o["k3n"] == 1, (o["k3"], o["k3n"]))
        check("다른 컴퓨터에서 더 최근에 바꿈 → 계정 값(120%)", o["k4"]["read"] == 120 and o["k4n"] == 0, (o["k4"], o["k4n"]))
        check("예전에 맞춘 값(시각 없음)도 계정에 올림 · 화면은 그대로 120%", o["k5"]["n"] == 1 and o["k5"]["b"]["fs"].get("knkmail.fs") == "2" and o["k5"]["read"] == 120, o["k5"])
        check("양옆 ±·모두 보통도 저장", o["k6"] == 2, o["k6"])
else:
    print("  (node 없음 — 단계 실행 시험 건너뜀)")

print("③ 배율 범위 · 설정 화면")
vs = io.open("app/templates/_v5_partials/mail_view_styles.html", encoding="utf-8").read()
check("배율은 칸 안쪽만 · 칸마다 따로(폴더·목록·읽기 칸=단독 메일 포함)",
      "html[data-mfz] .mbx-side > *{zoom:var(--mfz-side,1)}" in vs and "html[data-mfz] .mbx-list > *{zoom:var(--mfz-list,1)}" in vs
      and "html[data-mfz] #readPane > *, html[data-mfz] .mv-zoom > *{zoom:var(--mfz-read,1)}" in vs)
ib = io.open("app/templates/mail_inbox.html", encoding="utf-8").read()
check("큰 글씨 규칙도 칸별(mfb-list·mfb-side·mfb-read) · 예전 전체 규칙 안 남음",
      "html.mfb-list .mbx-subj" in ib and "html.mfb-side .mbx-fold" in ib and "html.mfb-read .mv-body" in vs and "html.mbx-big ." not in ib + vs)
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

print("④ 내 계정에 기억(서버) — 가짜 사람만")
r = k.post("/api/mail/ui-prefs", json={"fs": {"knkmail.fs.read.right": "3", "knkmail.fs.list": -1, "t": 7000}})
check("저장", r.status_code == 200 and r.json().get("saved") is True, r.text[:200])
r = k.post("/api/mail/ui-prefs", json={"fs": {"knkmail.fs.read.right": "0", "t": 6000}})
check("더 오래된 값은 덮어쓰지 않고 지금 계정 값을 돌려줌", r.json().get("saved") is False and r.json()["fs"].get("knkmail.fs.read.right") == 3, r.text[:200])
r = k.post("/api/mail/ui-prefs", json={"fs": {"knkmail.fs.read.right": "99", "evil": "<script>", "knkmail.fs.side": "x", "knkmail.fs": 1, "t": 8000}})
j = r.json()["fs"]
check("정해진 열쇠·−3~4 만 받음(이상한 값·열쇠 버림)", j == {"knkmail.fs": 1, "t": 8000}, j)
r = k.post("/api/mail/ui-prefs", json={"fs": {"knkmail.fs.read.bottom": 2, "t": 9000}})
h2 = k.get("/mail/inbox?app=1").text
check("다시 열면 화면에 계정 값이 실려 옴", 'window.MAIL_FS_SRV={"knkmail.fs.read.bottom": 2, "t": 9000};' in h2, re.findall(r"window.MAIL_FS_SRV=[^;]*;", h2)[:1])
h3 = k.get("/mail/%d?app=1" % MID).text
check("따로 연 메일 화면에도", 'window.MAIL_FS_SRV={"knkmail.fs.read.bottom": 2, "t": 9000};' in h3)
_me = dict(ME)
m.get_user = lambda req: None
r = k.post("/api/mail/ui-prefs", json={"fs": {"knkmail.fs": 1, "t": 1}})
check("로그인 안 하면 저장 안 됨", r.status_code == 401, r.status_code)
m.get_user = lambda req: _me

print("\n결과: %d 통과 · %d 실패" % (P, F))
sys.exit(1 if F else 0)
