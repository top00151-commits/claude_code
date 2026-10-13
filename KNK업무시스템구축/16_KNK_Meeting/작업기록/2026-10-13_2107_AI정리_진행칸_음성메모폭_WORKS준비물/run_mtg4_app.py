# -*- coding: utf-8 -*-
"""z1177 시험용 WORKS 서버 — 🗓 회의록 「정리하는 중」 진행 칸을 느린 가짜 AI 로 재 본다.
(z1170 run_mtg3_app.py 를 바탕으로 — 바뀐 것: **실패하는 회의** · **두 번째 회의** 를 더 세운다)
사용: py run_mtg4_app.py <앱폴더(절대경로)> <포트> [정리에 걸리는 초(기본 5)]

세우는 것
  · 사람 둘 — 나(회의 작성자 · 고칠 수 있다) · 남 (못 고친다 → 403 이 나야 한다)
  · 회의 — ① 내용 있는 내 회의 ② 내용이 **빈** 내 회의(400) ③ 남의 회의(403)
           ④ 🔴 **AI 가 실패하는** 내 회의(원문에 FAILME) ⑤ 다시 열기·창 닫기 시험용 내 회의

🔴 **느린 가짜 AI** — 진짜 AI 를 부르지 않고(키도 비운다), 정해진 초만큼 자고 결과를 돌려준다.
   원문에 FAILME 가 있으면 같은 초만큼 자고 **실패**를 돌려준다(빨간 진행 칸을 보려고).
"""
import io
import json
import os
import shutil
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
APP = sys.argv[1]
PORT = int(sys.argv[2])
SLOW = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0
os.chdir(APP)
sys.path.insert(0, APP)
os.environ.setdefault("KNK_SECRET_KEY", "verify-only-key")
os.environ["KNK_MESSENGER_SSO_INTERNAL_BASE"] = "http://127.0.0.1:9"
for _k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "KNK_OPENAI_API_KEY"):
    os.environ[_k] = ""
sys.stdout.reconfigure(encoding="utf-8")
shutil.rmtree(os.path.join(APP, "data"), ignore_errors=True)
shutil.rmtree(os.path.join(APP, "meeting_audio"), ignore_errors=True)

import uvicorn                         # noqa: E402
from app import main as M              # noqa: E402
from app.database import db_session    # noqa: E402
from app import ai_client              # noqa: E402

# 🧹 시험에서는 **아무 일도 안 하는** 서비스워커를 내준다.
#    운영 /sw.js 의 activate 는 c.navigate(c.url) 로 **열린 화면을 전부 다시 읽힌다** →
#    시험은 매번 새 브라우저라 그게 깔리면서 화면이 0.8초 뒤 다시 읽히고,
#    Playwright 가 'Execution context was destroyed' 로 터진다(이틀에 네 번 겪음).
#    🔵 404 로 두면 콘솔에 오류 한 줄이 남아 「콘솔 오류 0」 검사가 깨진다 → 빈 스크립트로.
#    ⛔ 운영 /sw.js 는 건드리지 않는다. 이 줄은 **시험 서버에만** 있다.
from starlette.responses import PlainTextResponse as _PTR_no_sw   # noqa: E402
_no_sw_in_test = [r for r in M.app.router.routes if getattr(r, 'path', '') == '/sw.js']
for _r in _no_sw_in_test:
    M.app.router.routes.remove(_r)


@M.app.get('/sw.js')
async def _sw_noop_for_test():
    return _PTR_no_sw('/* 시험용 빈 서비스워커 — 아무 일도 하지 않는다 */',
                      media_type='application/javascript')

ai_client.ai_available = lambda: True
ai_client.transcribe_available = lambda: True


CALLN = [0]


def slow_meeting(body, context=""):
    """느린 가짜 — SLOW 초 자고 결정·할 일·요약을 돌려준다(틀은 진짜와 같다)."""
    time.sleep(SLOW)
    n = len(body or "")
    if "FAILME" in (body or ""):
        return (False, {"error": "가짜 실패 — AI 가 답하지 않았습니다"})
    #  몇 번째 정리인지 글에 남긴다 — 「창을 닫아도 끝까지 됐다」를 **새 글로** 가려내려고
    CALLN[0] += 1
    return (True, {
        "decisions": [{"who": "김한국", "what": "가짜 결정 (원문 %d자)" % n, "due": "2026-10-20"}],
        "actions": [{"assignee": "김한국", "task": "가짜 할 일", "due": "2026-10-21"}],
        "summary": "요점\n- 가짜 정리 (원문 %d자) · %d번째" % (n, CALLN[0]),
        "title": "가짜 제목",
    })


ai_client.ai_extract_meeting = slow_meeting


def fake_get_user(req):
    uid = req.cookies.get("tuser")
    with db_session() as c:
        if uid:
            r = c.execute("SELECT * FROM users WHERE id=?", (int(uid),)).fetchone()
        else:
            r = c.execute("SELECT * FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()
        return dict(r) if r else None


M.get_user = fake_get_user
srv = uvicorn.Server(uvicorn.Config(M.app, host="127.0.0.1", port=PORT,
                                    log_level="warning", lifespan="on"))
th = threading.Thread(target=srv.run, daemon=True)
th.start()
for _ in range(300):
    if srv.started:
        break
    time.sleep(0.1)

with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code", "lang"):
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s TEXT" % col)
    r = c.execute("SELECT id FROM teams WHERE name=?", ("총괄",)).fetchone()
    tid = r[0] if r else c.execute(
        "INSERT INTO teams(name, code, display_order) VALUES('총괄','TF0',0)").lastrowid

    me = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    #  🔴 role 은 member — admin/ceo 로 두면 「권한 없음(403)」을 못 만든다
    c.execute("UPDATE users SET team_id=?, rank='과장', role='member', name='김한국', lang='ko' "
              "WHERE id=?", (tid, me))
    other = c.execute(
        "INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang) "
        "VALUES('z70ot','남의사람','부장','member',?,1,'x-no-login-z1170','ko')", (tid,)).lastrowid

    #  ① 내용이 있는 내 회의 (정리할 거리가 있다)
    mine = c.execute(
        "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, "
        "                     attendees_text, body, summary, status) "
        "VALUES('10월 설비 회의','2026-10-13',?,?,'all','김한국',?,'요점\n- 옛 정리','draft')",
        (me, tid, "오늘 3호기 베어링에서 소리가 납니다. " * 40)).lastrowid
    #  ② 내용이 빈 내 회의 (400)
    empty = c.execute(
        "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, body, status) "
        "VALUES('빈 회의','2026-10-13',?,?,'all','','draft')", (me, tid)).lastrowid
    #  ③ 남의 회의 — 참석자도 아니다 (403)
    notmine = c.execute(
        "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, "
        "                     attendees_text, body, status) "
        "VALUES('남의 회의','2026-10-13',?,?,'all','남의사람','남의 내용','draft')",
        (other, tid)).lastrowid
    c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,?)",
              (notmine, other, "남의사람"))
    #  사람이 손으로 적은 결정·할 일 — 🔴 AI 정리가 이것을 지우면 안 된다
    c.execute("INSERT INTO meeting_decisions(meeting_id, who, what, due, source) "
              "VALUES(?,'김한국','사람이 적은 결정','2026-10-15','manual')", (mine,))
    c.execute("INSERT INTO meeting_actions(meeting_id, assignee_name, task, due_date, source) "
              "VALUES(?,'김한국','사람이 적은 할 일','2026-10-16','manual')", (mine,))
    #  ④ 🔴 AI 가 실패하는 내 회의 — 빨간 진행 칸 · 옛 정리가 그대로 남는가
    failm = c.execute(
        "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, "
        "                     attendees_text, body, summary, status) "
        "VALUES('실패하는 회의','2026-10-13',?,?,'all','김한국',?,'요점\n- 실패 전 옛 정리','draft')",
        (me, tid, "FAILME 이 회의는 가짜 AI 가 실패를 돌려준다. " * 10)).lastrowid
    #  ⑤ 다시 열기 · 창 닫기 시험용 내 회의 (①과 섞이지 않게 따로)
    mine2 = c.execute(
        "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, "
        "                     attendees_text, body, summary, status) "
        "VALUES('다시 열기 회의','2026-10-13',?,?,'all','김한국',?,'요점\n- 다시 열기 전 옛 정리','draft')",
        (me, tid, "다시 열어도 진행이 보여야 합니다. " * 30)).lastrowid

io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(
    json.dumps({"me": me, "other": other, "mine": mine, "empty": empty,
                "notmine": notmine, "failm": failm, "mine2": mine2,
                "slow": SLOW, "port": PORT}, ensure_ascii=False))
print("READY", PORT, "me", me, "other", other, "mine", mine, "empty", empty,
      "notmine", notmine, "failm", failm, "mine2", mine2, "slow", SLOW, flush=True)
th.join()
