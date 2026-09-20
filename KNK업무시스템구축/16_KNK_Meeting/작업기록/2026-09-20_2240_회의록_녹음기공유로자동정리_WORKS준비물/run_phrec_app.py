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

ai_client.transcribe_available = lambda: True
ai_client.ai_transcribe = lambda path, lang="": (True, "[가짜 변환] 시험용 회의 내용입니다")
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
