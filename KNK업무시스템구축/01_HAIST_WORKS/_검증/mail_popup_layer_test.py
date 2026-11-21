# -*- coding: utf-8 -*-
"""메일 펼침 메뉴 가림·잘림 (대표 2026-11-22 「보기 메뉴가 즐겨찾기에 가려져서 나와 · 다른 항목도 전체적으로 확인해서 수정」) — 운영 무접촉 · 임시 DB.

원인
  ① 목록 칸·명령 막대는 너비 규칙(container) 때문에 겹침 층이 칸 단위로 묶임 → 안의 🗔 보기·🏷 종류 메뉴가 왼쪽 칸 머리(즐겨찾기 상자 · 5층) 아래로
  ② 읽기 칸의 ⋯ 더 보기·🚩 기한·알림·✅ 확인 답장 상자는 칸 안 자리(absolute) → 칸 가장자리에서 잘리고 옆 목록 칸에 가려짐
고친 것(이 시험이 지킴)
  ① 메뉴가 열려 있는 동안만 그 칸을 왼쪽 칸보다 위로(:has)
  ② 열 때 화면 기준 자리(fixed · 아래 자리 없으면 위로 · 오른쪽 없으면 왼쪽으로) · 칸을 굴리면 닫음
  (실제 가림 검사 = 시연 서버에서 메뉴마다 25점 찍어 맨 위 요소 확인 — 보기 4가지·폭 4가지 · 작업기록 참고)
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
    _TMP = tempfile.mkdtemp(prefix="knk_mpl_")
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
              "VALUES(9890,'in','a@x-demo.example','가짜','me" + D + "','가짜 메일','확인 후 회신 부탁드립니다.',0,0,datetime('now','localtime'))")
    MID = c.execute("SELECT last_insert_rowid()").fetchone()[0]
ME = {"id": 9890, "role": "member", "name": "시험신입", "rank": "사원", "login_id": "t_me", "email": "me" + D, "lang": "ko"}
m.get_user = lambda req: ME
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})

h = k.get("/mail/inbox?app=1").text
v = k.get("/mail/%d?app=1" % MID).text
p = k.get("/mail/%d?pane=1" % MID)
pv = p.text if p.status_code == 200 else v

print("① 목록 칸·명령 막대 메뉴 — 열려 있는 동안 왼쪽 칸보다 위로")
check("목록 칸은 너비 규칙(container)을 씀(겹침 층이 묶이는 까닭)", re.search(r"\.mbx-listcol\{container:", h) is not None)
check("🗔 보기(details)·🏷 종류(.open) 열리면 목록 칸·명령 막대 z-index 35(왼쪽 칸 머리 5보다 위)",
      ".mbx-split>.mbx-listcol:has(details[open]),.mbx-split>.mbx-listcol:has(.mbx-kinddd.open)," in h
      and ".mbx-split>.mbx-lhead:has(details[open]),.mbx-split>.mbx-lhead:has(.mbx-kinddd.open){z-index:35}" in h)
mm = re.search(r"\.mbx-side-top\{[^}]*z-index:(\d+)", h)
check("왼쪽 칸 머리(즐겨찾기 상자) z-index < 35", mm and int(mm.group(1)) < 35, mm and mm.group(1))

print("② 읽기 칸 펼침 상자 — 화면 기준 자리")
check("상자 모양: 열면 fixed · 높은 층 · 화면 높이 넘으면 굴림",
      ".mv-more-box.mv-pop{position:fixed;right:auto;z-index:9400;max-height:calc(100vh - 16px);overflow:auto}" in v)
check("열 때 자리 잡기(아래 자리 없으면 위로 · 오른쪽 없으면 왼쪽) · 닫으면 원래대로",
      "if(y+h > innerHeight-8){ var up=r.top-4-h;" in v and "b.classList.remove('mv-pop')" in v and "d.addEventListener('toggle', function(){ place(d); })" in v)
check("칸을 굴리면 열린 상자 닫음(상자 안 굴림은 그대로)", "document.addEventListener('scroll', shut, true)" in v and "b.contains(ev.target)) return;" in v)
check("읽기 칸 조각(pane)에도 같은 자리 잡기", "d.addEventListener('toggle', function(){ place(d); })" in pv, p.status_code)
vs = io.open("app/templates/_v5_partials/mail_view_styles.html", encoding="utf-8").read()
check("모양 조각엔 스크립트 없음(머리에 들어가도 안전)", "<script" not in vs)
node = shutil.which("node")
if node:
    bad = 0
    for s in re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", v, re.S):
        if not s.strip():
            continue
        fd, pth = tempfile.mkstemp(suffix=".js")
        os.write(fd, s.encode("utf-8"))
        os.close(fd)
        r = subprocess.run([node, "--check", pth], capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL)
        if r.returncode:
            bad += 1
            print(r.stderr[:300])
        os.remove(pth)
    check("메일 보기 화면 스크립트 문법(node)", bad == 0, bad)

print("\n결과: %d 통과 · %d 실패" % (P, F))
sys.exit(1 if F else 0)
