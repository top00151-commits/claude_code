# -*- coding: utf-8 -*-
"""z1167 시험용 WORKS 서버 — 🎤 음성 메모 **목록**과 **상세**를 띄워 본다.
사용: py run_vn2_app.py <앱폴더(절대경로)> <포트>

세우는 것
  · 사람 하나 — 음성 메모는 「내 것만」 보이므로 주인이 곧 보는 사람이다
  · 메모 둘 — ① 정리까지 끝난 메모(summary + body 둘 다 있음 → 「받아쓴 원문」 칸이 펼쳐질 수 있다)
              ② 아직 정리 전 메모(목록에 두 줄 이상 뜨게)

🔴 AI 키는 비운다 — 진짜 AI 를 부르지 않는다.
🔵 이 묶음이 보려는 것은 **화면에 시안 문서가 섞여 나오는가** 하나뿐이라
   권한·언어는 건드리지 않는다(섞으면 무엇 때문에 달라졌는지 못 가린다).
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
os.chdir(APP)
sys.path.insert(0, APP)
os.environ.setdefault("KNK_SECRET_KEY", "verify-only-key")
os.environ["KNK_MESSENGER_SSO_INTERNAL_BASE"] = "http://127.0.0.1:9"
for _k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "KNK_OPENAI_API_KEY"):
    os.environ[_k] = ""
sys.stdout.reconfigure(encoding="utf-8")
shutil.rmtree(os.path.join(APP, "data"), ignore_errors=True)
shutil.rmtree(os.path.join(APP, "meeting_audio"), ignore_errors=True)
shutil.rmtree(os.path.join(APP, "voice_notes"), ignore_errors=True)

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
    c.execute("UPDATE users SET team_id=?, rank='과장', role='member', name='김한국', lang='ko' "
              "WHERE id=?", (tid, me))

    # ① 정리까지 끝난 메모 — 「📌 정리」와 「🎤 받아쓴 원문」이 둘 다 차 있다
    done = c.execute(
        "INSERT INTO voice_notes(owner_id, title, body, summary) VALUES(?,?,?,?)",
        (me, "현장 설비 메모",
         "오늘 3호기 베어링에서 소리가 납니다. 다음 주에 교체 일정 잡아 주세요.",
         "요점\n- 3호기 베어링 이상음\n할 일\n- 교체 일정 잡기")).lastrowid
    # ② 아직 정리 전 메모
    todo = c.execute(
        "INSERT INTO voice_notes(owner_id, title, body, summary) VALUES(?,?,'','')",
        (me, "전화 통화 메모")).lastrowid

io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(
    json.dumps({"me": me, "done": done, "todo": todo, "port": PORT, "app": APP},
               ensure_ascii=False))
print("READY", PORT, "me", me, "done", done, "todo", todo, flush=True)
th.join()
