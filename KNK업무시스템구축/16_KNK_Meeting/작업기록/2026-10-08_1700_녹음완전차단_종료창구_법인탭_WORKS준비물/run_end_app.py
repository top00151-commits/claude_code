# -*- coding: utf-8 -*-
"""z1149·z1150 시험용 WORKS 서버 (기본 127.0.0.1:8948).
사용: py run_end_app.py <앱폴더(절대경로)> [포트=8948]

세우는 것
  · 공유키를 아는 '이음 서버' 흉내 — sso_client.get_service_key 를 시험용 값으로 바꾼다
  · 회의 2개: ① 보통 회의(msg_meeting_id=9001) ② 🔴 녹음 중인 회의(9002)
  · 사람 4: 한도윤(주인·사번 E901) · 오세진(참석자 E902) · 나윤슬(이음 등록 담당 E903) · 문가온(남 E904)
🔴 AI 키는 비운다."""
import io
import json
import os
import shutil
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WHICH = sys.argv[1] if len(sys.argv) > 1 else "app_new"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8948
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

import uvicorn                         # noqa: E402
from app import main as M              # noqa: E402
from app.database import db_session    # noqa: E402
from app import ai_client              # noqa: E402
from app import sso_client             # noqa: E402

KEY = "z1150-test-service-key"
sso_client.get_service_key = lambda: KEY     # 이음 서버 흉내 — 운영 키는 쓰지 않는다
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
            c.execute("ALTER TABLE users ADD COLUMN %s TEXT" % col)
    row = c.execute("SELECT id FROM teams WHERE name='검사기T'").fetchone()
    tid = row[0] if row else c.execute(
        "INSERT INTO teams(name, code, display_order) VALUES('검사기T','TV1',1)").lastrowid
    row2 = c.execute("SELECT id FROM teams WHERE name='생산팀'").fetchone()
    tid2 = row2[0] if row2 else c.execute(
        "INSERT INTO teams(name, code, display_order) VALUES('생산팀','TV2',2)").lastrowid

    def emp(login, nm, rank, team, no):
        return c.execute(
            "INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, employee_no) "
            "VALUES(?,?,?,'member',?,1,'x-no-login-z1150',?)", (login, nm, rank, team, no)).lastrowid

    owner = emp("z50own", "한도윤", "과장", tid, "E901")
    att = emp("z50att", "오세진", "대리", tid, "E902")
    org = emp("z50org", "나윤슬", "사원", tid, "E903")
    out = emp("z50out", "문가온", "대리", tid2, "E904")

    def meeting(msg_id, title, rec=""):
        mid = c.execute(
            "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, attendees_text, "
            "                     body, status, msg_meeting_id, msg_organizer_id, rec_state) "
            "VALUES(?,?,?,?,'team','한도윤, 오세진','','draft',?,?,?)",
            (title, "2026-10-08", owner, tid, msg_id, org, rec)).lastrowid
        for uid_, nm_ in ((owner, "한도윤"), (att, "오세진")):
            c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,?)",
                      (mid, uid_, nm_))
        return mid

    mid_ok = meeting(9001, "드림텍VINA MES 관련")
    mid_rec = meeting(9002, "🔴 아직 녹음 중인 회의", rec="recording")

io.open(os.path.join(HERE, "seed_end.json"), "w", encoding="utf-8").write(json.dumps(
    {"owner": owner, "att": att, "org": org, "out": out, "mid_ok": mid_ok, "mid_rec": mid_rec,
     "msg_ok": 9001, "msg_rec": 9002, "key": KEY, "port": PORT, "app": WHICH}, ensure_ascii=False))
print("READY", WHICH, PORT, "mid_ok", mid_ok, "mid_rec", mid_rec, flush=True)
th.join()
