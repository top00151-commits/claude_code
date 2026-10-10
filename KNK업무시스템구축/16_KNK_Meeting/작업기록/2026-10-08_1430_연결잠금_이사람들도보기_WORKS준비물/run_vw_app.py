# -*- coding: utf-8 -*-
"""z1147·z1148 시험용 WORKS 서버 (기본 127.0.0.1:8941 · 이음 불필요).
사용: py run_vw_app.py <앱폴더(절대경로)> [포트=8941]

세우는 사람들 (🔴 핵심: 「팀 공개인데 참석도 안 한 사람」이 있어야 대표님 상황이 재현된다)
  · 김정락  대표이사 총괄   role=ceo    → 원래 다 본다(대조군)
  · 한도윤    과장   검사기T  role=member → 회의록 주인
  · 오세진  대리   검사기T  role=member → 참석자
  · 문가온  대리   생산팀   role=member → 🔴 참석 안 함 · 다른 팀 → 지금은 볼 길이 없다
회의: 「드림텍VINA MES 관련」 · 팀 공개(team=검사기T) · 프로젝트 하나 연결해 둠(z1147 칩이 남는지)
🔴 AI 키는 비운다 — 진짜 AI 를 부르지 않는다."""
import io
import json
import os
import shutil
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WHICH = sys.argv[1] if len(sys.argv) > 1 else "app_new"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8941
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

    def team(nm, code, order):
        r = c.execute("SELECT id FROM teams WHERE name=?", (nm,)).fetchone()
        if r:
            c.execute("UPDATE teams SET display_order=? WHERE id=?", (order, r[0]))
            return r[0]
        return c.execute("INSERT INTO teams(name, code, display_order) VALUES(?,?,?)",
                         (nm, code, order)).lastrowid

    t_head = team("총괄", "TV0", 0)
    t_insp = team("검사기T", "TV1", 1)
    t_prod = team("생산팀", "TV2", 2)

    ceo = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='대표이사', role='ceo', name='김정락' WHERE id=?",
              (t_head, ceo))

    def emp(login, nm, rank, tid):
        return c.execute(
            "INSERT INTO users(login_id, name, rank, role, team_id, is_active, password) "
            "VALUES(?,?,?,'member',?,1,'x-no-login-z1148')", (login, nm, rank, tid)).lastrowid

    owner = emp("z48own", "한도윤", "과장", t_insp)       # 회의록 주인
    att = emp("z48att", "오세진", "대리", t_insp)       # 참석자
    out = emp("z48out", "문가온", "대리", t_prod)       # 🔴 참석 안 함·다른 팀
    out2 = emp("z48ou2", "배하늘", "사원", t_prod)      # 또 한 사람(여러 명 고르기 시험)

    pid = c.execute("INSERT INTO projects(name, mgmt_code, status) "
                    "VALUES('드림텍VINA MES','006T2607','진행중')").lastrowid
    mid = c.execute(
        "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, "
        "                     attendees_text, body, status, project_id) "
        "VALUES('드림텍VINA MES 관련','2026-10-08',?,?,'team','한도윤, 오세진','녹음 한번 해보고 있어. 아.','draft',?)",
        (owner, t_insp, pid)).lastrowid
    for uid_, nm_ in ((owner, "한도윤"), (att, "오세진")):
        c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,?)",
                  (mid, uid_, nm_))

io.open(os.path.join(HERE, "seed_vw.json"), "w", encoding="utf-8").write(json.dumps(
    {"ceo": ceo, "owner": owner, "att": att, "out": out, "out2": out2,
     "mid": mid, "pid": pid, "port": PORT, "app": WHICH}, ensure_ascii=False))
print("READY", WHICH, PORT, "mid", mid, "out", out, flush=True)
th.join()
