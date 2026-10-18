# -*- coding: utf-8 -*-
"""z1115 「📱 휴대폰 녹음기로 녹음」 시험용 WORKS 서버 (기본 127.0.0.1:8936 · 이음 불필요).
사용: py run_phrec_app.py <앱폴더(절대경로 가능)> [포트=8936]
🔴 AI 키를 비우고 음성→글자·AI 정리를 모두 가짜로 바꾼다(2026-09-17 실제 whisper 호출 사고 뒤 규칙)."""
import io
import json
import os
import shutil
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WHICH = sys.argv[1] if len(sys.argv) > 1 else "app_new"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8936
APP = WHICH if os.path.isabs(WHICH) else os.path.join(HERE, WHICH)
os.chdir(APP)
sys.path.insert(0, APP)
os.environ.setdefault("KNK_SECRET_KEY", "verify-only-key")
os.environ["KNK_MESSENGER_SSO_INTERNAL_BASE"] = "http://127.0.0.1:9"
for _k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "KNK_OPENAI_API_KEY"):
    os.environ[_k] = ""
sys.stdout.reconfigure(encoding="utf-8")
shutil.rmtree(os.path.join(APP, "data"), ignore_errors=True)
shutil.rmtree(os.path.join(APP, "meeting_audio"), ignore_errors=True)

import uvicorn                       # noqa: E402
from app import main as M            # noqa: E402
from app.database import db_session   # noqa: E402
from app import ai_client            # noqa: E402

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

ai_client.transcribe_available = lambda: True
#  z1187: 받아쓴 글은 알아들을 말이 200자 이상이어야 「녹음 원문 있음」 → 실제 회의처럼 문장을 덧붙인다(앞머리 그대로)
ai_client.ai_transcribe = lambda path, lang="": (True, "[가짜 변환] 시험용 회의 내용입니다. " + '오늘은 삼성 A라인 2호기 출하 일정과 셋업 순서를 함께 정리했습니다. 출하는 11월 20일로 하고 포장은 그 전날까지 마치기로 했습니다. 셋업은 25일부터 시작하는데 고객사 담당자의 확인을 먼저 받아야 합니다. 카메라 두 대를 추가해 달라는 요청은 납기에 영향이 있는지 기술팀이 이번 주 안에 확인하겠습니다. 조명 교체 제안은 원가를 먼저 계산해 보고 다음 회의에서 다시 이야기하기로 했습니다. 검사 프로그램은 지난번 오류가 난 부분을 고친 판으로 현장에서 한 번 더 돌려 보겠습니다. 부품 단가가 오른 것은 구매팀이 거래처와 다시 협의해 결과를 공유하기로 했습니다. 다음 회의는 다음 주 화요일 오전 열 시에 같은 장소에서 하겠습니다.')
ai_client.ai_available = lambda: True
ai_client.ai_extract_meeting = lambda body, context="": (True, {"summary": "핵심: 시험용 가짜 정리",
                                                                "decisions": [], "actions": [], "title": ""})


def fake_get_user(req):
    uid = req.cookies.get("tuser")
    with db_session() as c:
        if uid:
            r = c.execute("SELECT * FROM users WHERE id=?", (int(uid),)).fetchone()
        else:
            r = c.execute("SELECT * FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()
        return dict(r) if r else None


M.get_user = fake_get_user
srv = uvicorn.Server(uvicorn.Config(M.app, host="127.0.0.1", port=PORT, log_level="warning", lifespan="on"))
th = threading.Thread(target=srv.run, daemon=True)
th.start()
for _ in range(300):
    if srv.started:
        break
    time.sleep(0.1)

with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code"):
        if col not in have:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
    row = c.execute("SELECT id FROM teams WHERE name='총괄'").fetchone()
    tid = row[0] if row else c.execute("INSERT INTO teams(name, code) VALUES('총괄','TV1')").lastrowid
    ceo = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='대표이사', role='ceo', name='김정락' WHERE id=?", (tid, ceo))
    c.execute("DELETE FROM meetings")
    mids = [c.execute(
        "INSERT INTO meetings(title, meeting_date, mode, team_id, owner_id, location, tags, attendees_text, body, "
        "summary, audio_path, visibility, status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (f"[시험] 회의 {i}", "2026-09-20", "A", tid, ceo, "", "", "김정락", "", "", "", "all", "draft")).lastrowid
        for i in range(4)]

io.open(os.path.join(HERE, "seed_phrec.json"), "w", encoding="utf-8").write(json.dumps(
    {"mids": mids, "ceo": ceo, "port": PORT, "app": WHICH}))
print("READY", WHICH, PORT, mids, flush=True)
th.join()
