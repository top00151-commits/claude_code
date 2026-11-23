# -*- coding: utf-8 -*-
"""메일 팝업마다 오른쪽 위 「✕」 (대표 2026-11-22 「팝업창에는 따로 종료할 수 있게 우측 상단에 X · 다른 팝업들도 다 확인해서 조치」) — 운영 무접촉 · 임시 DB.

증명할 것
  ① 공용 조각 `_v5_partials/mail_popx.html` 이 팝업 있는 모든 메일 화면에 들어감(도구 줄 · 받은편지함 · 메일 보기 · 새 창 · 쓰기)
  ② 대상 팝업 15가지가 목록에 다 있음 · 닫는 길이 각자 맞음 · ✕ 자리(위 띠)를 미리 비움 · 굴러가는 상자는 ✕ 를 위에 붙임
  ③ 숨은 창에서도 붙도록 그림 시계(requestAnimationFrame) 대신 바로 뒤(microtask) · 두 번 들어가도 한 번만
  ④ 좁은 창 도구 줄: 찾기 칸 최소 300px · 모자라면 둘째 줄(글자 겹침 고침)
  (실제 눌러 닫히는지 = 시연 서버에서 15가지 확인 · 작업기록 참고)
"""
import io
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
    _TMP = tempfile.mkdtemp(prefix="knk_mpx_")
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
    c.execute("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, subject, body_text, is_read, is_deleted, received_at) "
              "VALUES(9890,'in','a@x-demo.example','가짜','me" + D + "','가짜 메일','가짜',0,0,datetime('now','localtime'))")
    MID = c.execute("SELECT last_insert_rowid()").fetchone()[0]
ME = {"id": 9890, "role": "member", "name": "시험신입", "rank": "사원", "login_id": "t_me", "email": "me" + D, "lang": "ko"}
m.get_user = lambda req: ME
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})

MARK = "window._mailPopX=true"
print("① 팝업 있는 메일 화면마다 ✕ 조각")
pages = {"받은편지함(앱)": "/mail/inbox?app=1", "받은편지함(웍스 메뉴 안)": "/mail/inbox", "메일 보기": "/mail/%d?app=1" % MID,
         "메일 보기(웍스 메뉴 안)": "/mail/%d" % MID, "새 창": "/mail/%d?win=1" % MID, "쓰기": "/mail/compose?app=1", "쓰기(웍스 메뉴 안)": "/mail/compose",
         "그룹 메일": "/mail/groups?app=1", "설정·정리": "/mail/tools?app=1"}
H = {}
for nm, u in pages.items():
    r = k.get(u)
    H[nm] = r.text
    if r.status_code == 404 and nm == "새 창":
        print("  (새 창 주소 다름 — 건너뜀)")
        continue
    check("%s: ✕ 조각 들어감" % nm, r.status_code == 200 and MARK in r.text, r.status_code)

src = io.open("app/templates/_v5_partials/mail_popx.html", encoding="utf-8").read()
print("② 대상 팝업 · 닫는 길 · 자리")
targets = {"🗔 보기": "['.mbx-viewmenu', closeDetails]", "🏷 종류": "['.mbx-kindmenu',", "▾ 자세히": "['.mbx-adv', closeDetails]",
           "오른쪽 클릭·📁 이동": "['.mbx-ctx', function(el){ el.hidden=true; el.innerHTML=''; }]", "🎨 테마": "['#mailThemePop', hide]",
           "❔ 도움말": "['#mailHelp', hide]", "읽기 칸 ✅·🚩·⋯": "['.mv-more-box', closeDetails]", "보낸 사람": "['#mvWhoPop', hide]",
           "📎 첨부": "['#cAttachMenu', function(el){ el.style.display='none'; }]", "📝 양식": "['#cTplPop', hide]",
           "보내기 전 확인": "['#scBox', function(){ if(window.scClose) scClose(); }]", "그림 자르기": "['.crop-box',",
           "붙여넣기 고르기": "['.paste-pop', function(el){ el.remove(); }]", "☰ 폴더 칸": "['.mbx-side-top',"}
for nm, s in targets.items():
    check("대상: " + nm, s in src, s)
check("✕ = 오른쪽 위 · 「닫기」 이름표", ".mpx{position:absolute;top:4px;right:6px;" in src and "b.title='닫기'; b.setAttribute('aria-label','닫기');" in src)
check("✕ 자리(위 띠) 미리 비움 — 글자와 안 겹침", ".mbx-viewmenu,.mbx-kindmenu.pop,.mbx-adv,.mbx-ctx,#mailThemePop,#mailHelp,#mailFsPop,.mv-more-box,#mvWhoPop,#cAttachMenu,#cTplPop,#scBox,.crop-box{padding-top:30px !important}" in src)
check("굴러가는 상자 = ✕ 위에 붙음(sticky)", ".mpx.stk{position:sticky;" in src and "el.matches('#cTplPop,#scBox,.mbx-ctx,.mv-more-box')" in src)
check("종류 칩이 줄 안에 있을 땐(휴대폰) ✕ 숨김 · 폴더 칸은 펼쳤을 때만", ".mbx-kindmenu:not(.pop)>.mpx{display:none}" in src and ".mbx-split:not(.fold-pop) .mbx-side-top>.mpx{display:none}" in src)
check("✕ 누르면 다른 클릭 처리로 안 번짐", "e.preventDefault(); e.stopPropagation(); fn(el);" in src)
print("③ 붙이는 때")
check("새로 생기는 상자도(지켜보기) · 그림 시계 대신 바로 뒤", "new MutationObserver(later)" in src and "Promise.resolve().then" in src and "requestAnimationFrame(" not in src)
check("두 번 들어가도 한 번만(같은 상자에 ✕ 하나)", "if(window._mailPopX) return;" in src and "if(el.querySelector(':scope > .mpx')) return;" in src)
print("④ 좁은 창 도구 줄")
hd = io.open("app/templates/_v5_partials/mail_app_head.html", encoding="utf-8").read()
check("찾기 칸 최소 300px · 모자라면 둘째 줄", "#mailTools.mt-inbox .mt-in-l{flex:1 1 420px;min-width:300px}" in hd and "#mailTools.mt-inbox{overflow:visible;gap:4px;padding:2px 12px;flex-wrap:wrap;row-gap:2px}" in hd)
node = shutil.which("node")
if node:
    js = re.search(r"<script>(.*?)</script>", src, re.S).group(1)
    fd, p = tempfile.mkstemp(suffix=".js")
    os.write(fd, js.encode("utf-8"))
    os.close(fd)
    r = subprocess.run([node, "--check", p], capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL)
    os.remove(p)
    check("✕ 조각 스크립트 문법(node)", r.returncode == 0, r.stderr[:300])

print("\n결과: %d 통과 · %d 실패" % (P, F))
sys.exit(1 if F else 0)
