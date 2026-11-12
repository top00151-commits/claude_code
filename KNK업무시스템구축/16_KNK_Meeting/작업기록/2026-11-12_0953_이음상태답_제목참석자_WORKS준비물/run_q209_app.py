# -*- coding: utf-8 -*-
"""z1209 시험용 WORKS 서버 — 이음 회의 상태 답(/api/meeting/msg/status)에 제목·참석자 세 칸.
사용: py run_q209_app.py <앱폴더(절대경로)> <포트>
🔒 시험 글·이름은 모두 지어낸 것. ⛔ 진짜 AI·진짜 이음을 부르지 않는다(키 비움 · 이음 주소는 닫힌 포트).
세우는 것(사번)
  김한국 901(작성자·기술팀) · 최민수 902(기술팀) · Nguyen Van A VN903(다른 팀) · 박무사번(계정 있음·사번 없음)
  · 남다른 905(다른 팀 · 비공개 회의를 못 보는 사람)
  M1 이음 회의 801 · 전체 공개 · 참석 「김한국, 최민수, 가상고객 홍길동 부장, 박무사번」
  M2 이음 회의 802 · 비공개(작성자+참석자만) · 참석 「최민수」
  M3 이음 회의 803 · 팀 공개 · 참석 없음
  (이음 회의 899 = 회의록 없음)
  H1 이음과 연결 안 된 회의록(이음 회의 id 없음)
"""
import os
import shutil
import sys
import threading
import time
from datetime import datetime

APP = sys.argv[1]
PORT = int(sys.argv[2])
os.chdir(APP)
sys.path.insert(0, APP)
os.environ.setdefault("KNK_SECRET_KEY", "verify-only-key")
os.environ["KNK_MESSENGER_SSO_INTERNAL_BASE"] = "http://127.0.0.1:9"
os.environ["KNK_SSO_SERVICE_KEY"] = "q209-test-key"      # 시험용 값(운영 키 아님)
for _k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "KNK_OPENAI_API_KEY"):
    os.environ[_k] = ""
sys.stdout.reconfigure(encoding="utf-8")
for _d in ("data", "meeting_audio", "voice_notes"):
    shutil.rmtree(os.path.join(APP, _d), ignore_errors=True)

import uvicorn                         # noqa: E402
from app import main as M              # noqa: E402
from app import ai_client              # noqa: E402
from app.database import db_session    # noqa: E402

ai_client.ai_available = lambda: False


def fake_get_user(req):
    uid = req.cookies.get("tuser")
    with db_session() as c:
        if uid:
            r = c.execute("SELECT * FROM users WHERE id=?", (int(uid),)).fetchone()
        else:
            return None
        return dict(r) if r else None


M.get_user = fake_get_user

srv = uvicorn.Server(uvicorn.Config(M.app, host="127.0.0.1", port=PORT, log_level="warning", lifespan="on"))
th = threading.Thread(target=srv.run, daemon=True)
th.start()
for _ in range(300):
    if srv.started:
        break
    time.sleep(0.1)

TODAY = datetime.now().strftime("%Y-%m-%d")
with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("employee_no", "lang"):
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s TEXT" % col)
    ta = c.execute("INSERT INTO teams(name, code, display_order) VALUES('기술시험팀','Q2A',1)").lastrowid
    tb = c.execute("INSERT INTO teams(name, code, display_order) VALUES('다른시험팀','Q2B',2)").lastrowid
    me = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='과장', role='member', name='김한국', employee_no='901' WHERE id=?", (ta, me))

    def user(login, name, team, emp):
        return c.execute("INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, employee_no) "
                         "VALUES(?,?,'프로','member',?,1,'x-no-login-q209',?)", (login, name, team, emp)).lastrowid
    U = {"me": me,
         "choi": user("zq209a", "최민수", ta, "902"),
         "vn": user("zq209b", "Nguyen Van A", tb, "VN903"),
         "noemp": user("zq209c", "박무사번", ta, None),
         "other": user("zq209d", "남다른", tb, "905")}

    def mtg(title, vis, att, msg_id):
        mid = c.execute(
            "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, attendees_text, body, summary, "
            "status, msg_meeting_id) VALUES(?,?,?,?,?,?,'(가짜 원문)','','draft',?)",
            (title, TODAY, me, ta, vis, att, msg_id)).lastrowid
        M._meeting_link_attendees(c, mid, att)     # 운영과 같은 함수로 명단을 만든다
        return mid
    S = {"M1": mtg("가상전기_검사설비 협의", "all", "김한국, 최민수, 가상고객 홍길동 부장, 박무사번", 801),
         "M2": mtg("비공개 시험 회의", "private", "최민수", 802),
         "M3": mtg("참석 없는 회의", "team", "", 803),
         "H1": mtg("이음과 연결 안 된 회의록", "all", "김한국", None)}

import json  # noqa: E402
with open(os.path.join(APP, "q209_ids.json"), "w", encoding="utf-8") as f:
    json.dump({"users": U, "meetings": S}, f)
print("READY", PORT, flush=True)
while True:
    time.sleep(3600)
