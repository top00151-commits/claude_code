# -*- coding: utf-8 -*-
"""z1166 시험용 WORKS 서버 — 회의록 **목록**을 두 언어로 띄워 본다.
사용: py run_list_app.py <앱폴더(절대경로)> <포트>

세우는 사람 둘 — 🔴 **말만 다르고 권한·소속은 똑같이** (z1159 교훈:
  권한이 다르면 「권한 때문에 안 나온 것」을 「번역이 빠졌다」로 잘못 읽는다)
  · 한국어 사용자 lang='ko' · 베트남어 사용자 lang='vi' · 둘 다 role='member', 같은 팀

회의 둘 — 둘 다 전체 공개라 두 사람 모두 **목록에 보인다**
  · 회의 A = 두 사람이 **참석자** → 고칠 수 있다(✏ 켜짐)
  · 회의 B = 남의 회의 · 참석자 아님 → 못 고친다(✏ 흐림)

🔴 AI 키는 비운다 — 진짜 AI 를 부르지 않는다.
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

import uvicorn                         # noqa: E402
from app import main as M              # noqa: E402
from app.database import db_session    # noqa: E402
from app import ai_client              # noqa: E402

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

    # 🔴 두 사람은 **말만 다르고 권한·소속은 똑같다**
    ko = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='과장', role='member', name='김한국', lang='ko' "
              "WHERE id=?", (tid, ko))
    vi = c.execute(
        "INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang) "
        "VALUES('z66vi','Nguyen Van B','과장','member',?,1,'x-no-login-z1166','vi')",
        (tid,)).lastrowid
    # 남 — 회의 B 의 주인(두 사람 다 못 고치게)
    other = c.execute(
        "INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang) "
        "VALUES('z66ot','남의사람','부장','member',?,1,'x-no-login-z1166','ko')",
        (tid,)).lastrowid

    # 회의 A — 두 사람이 참석자 → 고칠 수 있다
    mid_ok = c.execute(
        "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, "
        "                     attendees_text, body, status) "
        "VALUES('고칠 수 있는 회의','2026-10-12',?,?,'all','김한국,Nguyen Van B','내용','draft')",
        (other, tid)).lastrowid
    for uid_, nm_ in ((ko, "김한국"), (vi, "Nguyen Van B")):
        c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,?)",
                  (mid_ok, uid_, nm_))
    # 회의 B — 남의 회의 · 참석자 아님 → 못 고친다
    mid_no = c.execute(
        "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, "
        "                     attendees_text, body, status) "
        "VALUES('못 고치는 회의','2026-10-11',?,?,'all','남의사람','내용','done')",
        (other, tid)).lastrowid
    c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,?)",
              (mid_no, other, "남의사람"))
    # 배지가 보이게 결정·할 일 한 건씩
    for _m in (mid_ok, mid_no):
        c.execute("INSERT INTO meeting_decisions(meeting_id, what) VALUES(?, '결정 하나')", (_m,))
        c.execute("INSERT INTO meeting_actions(meeting_id, task) VALUES(?, '할 일 하나')", (_m,))

io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(
    json.dumps({"ko": ko, "vi": vi, "other": other, "mid_ok": mid_ok, "mid_no": mid_no,
                "port": PORT, "app": APP}, ensure_ascii=False))
print("READY", PORT, "ko", ko, "vi", vi, "ok", mid_ok, "no", mid_no, flush=True)
th.join()
