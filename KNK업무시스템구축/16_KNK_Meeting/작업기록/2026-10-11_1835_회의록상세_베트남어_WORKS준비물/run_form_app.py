# -*- coding: utf-8 -*-
"""z1159 시험용 WORKS 서버 — 회의록 상세·새 회의록 화면을 두 언어로 띄워 보려고.
사용: py run_form_app.py <앱폴더(절대경로)> <포트>

세우는 사람 둘
  · 김정락 대표이사 총괄 · lang='ko'  → 한국어 화면
  · Nguyễn 과장 검사기T · lang='vi'  → 베트남어 화면 (회의록 주인·고칠 수 있는 사람)
회의 하나: 녹음 없음·정리 없음 → 「📁 녹음 파일 올리기」 큰 칸과 안내가 다 보이는 상태
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

    def team(nm, code, order):
        r = c.execute("SELECT id FROM teams WHERE name=?", (nm,)).fetchone()
        if r:
            return r[0]
        return c.execute("INSERT INTO teams(name, code, display_order) VALUES(?,?,?)",
                         (nm, code, order)).lastrowid

    t_head = team("총괄", "TF0", 0)
    t_insp = team("검사기T", "TF1", 1)

    # 🔴 두 사람은 **말만 다르고 권한·소속은 똑같아야** 한다.
    #    안 그러면 「권한 때문에 안 나온 칸」을 「번역이 빠졌다」로 잘못 읽는다(2026-10-11 실제로 겪음).
    ko = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='대표이사', role='ceo', name='김정락', lang='ko' "
              "WHERE id=?", (t_head, ko))
    vi = c.execute(
        "INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang) "
        "VALUES('z59vi','Nguyen Van A','대표이사','ceo',?,1,'x-no-login-z1159','vi')",
        (t_head,)).lastrowid
    pid = c.execute("INSERT INTO projects(name, mgmt_code, status) "
                    "VALUES('드림텍VINA MES','006T2607','진행중')").lastrowid
    mid = c.execute(
        "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, "
        "                     attendees_text, body, status, project_id) "
        "VALUES('드림텍VINA MES 관련','2026-10-11',?,?,'all','Nguyen Van A','x','draft',?)",
        (ko, t_head, pid)).lastrowid
    for uid_, nm_ in ((ko, "김정락"), (vi, "Nguyen Van A")):
        c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,?)",
                  (mid, uid_, nm_))
    _ = t_insp

io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(
    json.dumps({"ko": ko, "vi": vi, "mid": mid, "port": PORT, "app": APP}, ensure_ascii=False))
print("READY", PORT, "mid", mid, "ko", ko, "vi", vi, flush=True)
th.join()
