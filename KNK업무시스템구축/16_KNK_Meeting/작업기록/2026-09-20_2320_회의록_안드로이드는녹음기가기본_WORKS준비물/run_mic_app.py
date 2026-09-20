# -*- coding: utf-8 -*-
"""녹음 자동 시작·마이크 안내 시험용 WORKS 서버 (127.0.0.1:8932 · 이음 불필요).
세션 10 재현 도구(run_works_probe.py)를 바탕으로 — 어떤 앱 사본을 띄울지는 옆 파일 which_app.txt(app_base / app_new).
쿠키 tuser=<users.id> 가 있으면 그 사람, 없으면 대표 계정(로그인 확인이 운영 이음으로 넘기지 않게)."""
import io
import json
import os
import shutil
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WHICH = io.open(os.path.join(HERE, "which_app.txt"), encoding="utf-8").read().strip() or "app_base"
APP = WHICH if os.path.isabs(WHICH) else os.path.join(HERE, WHICH)
os.chdir(APP)
sys.path.insert(0, APP)
os.environ.setdefault("KNK_SECRET_KEY", "verify-only-key")
# 🔴 2026-09-17: 이 PC 에는 OPENAI_API_KEY 가 있어 시험 녹음(가짜 마이크 삐 소리)이 실제 OpenAI 로 가고 있었다
#    (시험 DB 에 「🎙 [음성 변환] You」) → 시험 서버는 AI 키를 비우고, 필요한 AI 는 아래에서 가짜로 바꾼다
for _k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "KNK_OPENAI_API_KEY"):
    os.environ[_k] = ""
sys.stdout.reconfigure(encoding="utf-8")
shutil.rmtree(os.path.join(APP, "data"), ignore_errors=True)

import uvicorn   # noqa: E402
from app import main as M   # noqa: E402
from app.database import db_session   # noqa: E402

# 🔴 AI 는 모두 가짜(네트워크 없음) — 음성→글자·AI 정리 흐름은 그대로 돌게
from app import ai_client   # noqa: E402
ai_client.transcribe_available = lambda: True
ai_client.ai_transcribe = lambda path, lang="": (True, "시험용 음성 변환 글입니다.")
ai_client.ai_available = lambda: True
ai_client.ai_extract_meeting = lambda body, context="": (True, {"summary": "핵심: 시험용 가짜 정리", "decisions": [], "actions": [], "title": ""})

PORT = 8932


def fake_get_user(req):
    uid = req.cookies.get("tuser")
    with db_session() as c:
        if uid:
            r = c.execute("SELECT * FROM users WHERE id=?", (int(uid),)).fetchone()
        else:
            r = c.execute("SELECT * FROM users WHERE name='김정락' ORDER BY id LIMIT 1").fetchone()
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
    row = c.execute("SELECT id FROM teams WHERE name='총괄'").fetchone()
    tid = row[0] if row else c.execute("INSERT INTO teams(name, code) VALUES('총괄','TV1')").lastrowid
    ceo = c.execute("SELECT id FROM users WHERE name='김정락'").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='대표이사', role='ceo', is_active=1 WHERE id=?", (tid, ceo))
    viewer = c.execute("SELECT id FROM users WHERE id<>? AND role NOT IN ('admin','ceo','executive') "
                       "AND is_active=1 LIMIT 1", (ceo,)).fetchone()[0]
    c.execute("DELETE FROM meetings")
    mids = []
    for i in range(12):
        mids.append(c.execute(
            "INSERT INTO meetings(title, meeting_date, mode, team_id, owner_id, location, tags, attendees_text, body, "
            "summary, audio_path, visibility, status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("[시험] 자동 녹음 %d" % (i + 1), "2026-09-17", "A", tid, ceo, "", "", "김정락", "", "", "", "all",
             "draft")).lastrowid)
    has_audio = c.execute(
        "INSERT INTO meetings(title, meeting_date, mode, team_id, owner_id, location, tags, attendees_text, body, "
        "summary, audio_path, visibility, status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("[시험] 녹음 있음", "2026-09-17", "A", tid, ceo, "", "", "김정락", "", "", "meeting_audio/x.webm", "all",
         "draft")).lastrowid

# 이음 역할 「여는 쪽」 — 누른 순간 빈 창을 먼저 열고, 잠시 뒤 그 창에 WORKS 주소를 넣는다(이음 _minlinkStart 와 같은 순서)
opener = """<!doctype html><meta charset="utf-8"><title>여는 쪽</title>
<button id="go" style="font-size:24px;padding:20px">▶ 회의 시작</button>
<script>
document.getElementById('go').addEventListener('click', async () => {
  const pre = window.open('', 'knk_meetings');
  await new Promise(r => setTimeout(r, 400));
  pre.location.href = new URLSearchParams(location.search).get('to');
});
</script>"""
io.open(os.path.join(APP, "static", "_probe_opener.html"), "w", encoding="utf-8").write(opener)
io.open(os.path.join(HERE, "seed_mic.json"), "w", encoding="utf-8").write(json.dumps(
    {"mids": mids, "has_audio": has_audio, "ceo": ceo, "viewer": viewer, "port": PORT, "app": WHICH}))
print("READY", WHICH, mids, flush=True)
th.join()
