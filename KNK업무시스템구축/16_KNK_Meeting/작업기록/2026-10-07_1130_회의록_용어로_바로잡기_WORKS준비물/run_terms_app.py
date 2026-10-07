# -*- coding: utf-8 -*-
"""z1142 「회의록에서 바로잡을 우리 회사 말」 시험용 WORKS 서버 (기본 127.0.0.1:8938 · 이음 불필요).
사용: py run_terms_app.py <앱폴더(절대경로)> [포트=8938]
🔴 AI 키를 비우고 진짜 AI 를 부르지 않는다 — ai_chat 을 가로채 「무엇을 보냈는지」만 파일에 적는다.
   (ai_extract_meeting 은 진짜를 쓴다 — 그게 이번에 고친 자리다)"""
import io
import json
import os
import shutil
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WHICH = sys.argv[1] if len(sys.argv) > 1 else "app_new"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8938
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

import uvicorn                        # noqa: E402
from app import main as M             # noqa: E402
from app.database import db_session    # noqa: E402
from app import ai_client             # noqa: E402

SENT_PATH = os.path.join(HERE, "sent_prompt.txt")


def fake_chat(user, system="", **kw):
    """진짜 AI 대신 — 보낸 지시문을 파일에 적고 형식만 맞는 답을 돌려준다."""
    io.open(SENT_PATH, "w", encoding="utf-8").write(system + "\n\n@@@원문@@@\n" + (user or ""))
    return (True, json.dumps({"title": "", "summary": "핵심: 시험용", "decisions": [], "actions": []},
                             ensure_ascii=False))


ai_client.ai_chat = fake_chat
ai_client.ai_available = lambda: True
ai_client.transcribe_available = lambda: True
ai_client.ai_transcribe = lambda path, lang="": (True, "[가짜 변환] 시험용 회의 내용입니다")


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

BODY = ("오늘 삼성 MSCC 출하 검사기 건으로 모였습니다. 카트리스트는 구매팀에 전달했고, "
        "표면장 측정은 다음 주에 다시 봅니다.")
with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code"):
        if col not in have:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
    row = c.execute("SELECT id FROM teams WHERE name='총괄'").fetchone()
    tid = row[0] if row else c.execute("INSERT INTO teams(name, code) VALUES('총괄','TV1')").lastrowid
    ceo = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='대표이사', role='ceo', name='김정락' WHERE id=?", (tid, ceo))
    # 일반 직원 한 명 — 관리자 화면에 못 들어가는지 확인용
    emp = c.execute(
        "INSERT INTO users(login_id, name, role, team_id, is_active, password) "
        "VALUES('z42emp','박성수','member',?,1,'x-no-login-z1142')",   # 시험 DB 전용 자리값(로그인 안 씀)
        (tid,)).lastrowid
    c.execute("DELETE FROM meetings")
    mid = c.execute(
        "INSERT INTO meetings(title, meeting_date, mode, team_id, owner_id, location, tags, attendees_text, body, "
        "summary, audio_path, visibility, status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("삼성 MSCC 출하 검사기", "2026-10-06", "A", tid, ceo, "", "", "김정락", BODY, "", "", "all", "draft")
    ).lastrowid

io.open(os.path.join(HERE, "seed_terms.json"), "w", encoding="utf-8").write(json.dumps(
    {"mid": mid, "ceo": ceo, "emp": emp, "port": PORT, "app": WHICH, "sent": SENT_PATH}, ensure_ascii=False))
print("READY", WHICH, PORT, mid, flush=True)
th.join()
