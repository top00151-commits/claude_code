# -*- coding: utf-8 -*-
"""z1192 시험용 WORKS 서버 — 회의록 양식 「일시」에 끝난 시각(「14:00 ~ 14:50 (50분)」).
대표 2026-10-20 「넣기 (권장)」(이음 회의 알림 카드엔 「14:00 ~ 14:50 (50분)」이 있는데 양식엔 시작 시각만 있었다)
사용: py run_q92_app.py <앱폴더(절대경로)> <포트>
가짜 = 진짜 로그인 대신 쿠키 tuser · 이음 주소는 닫힌 포트 · AI 키 비움(이 시험은 AI 를 안 부른다).
회의 11건(회의 날짜는 모두 2026-10-19 (월) 고정 — 시작·끝 시각 조합마다 하나) · 🔒 시험 글은 지어낸 것.
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
os.environ["KNK_SSO_SERVICE_KEY"] = "q92-test-key"      # 시험용 값(운영 키 아님)
for _k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "KNK_OPENAI_API_KEY"):
    os.environ[_k] = ""
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
for _d in ("data", "meeting_audio", "voice_notes"):
    shutil.rmtree(os.path.join(APP, _d), ignore_errors=True)

import uvicorn                         # noqa: E402
from app import main as M              # noqa: E402
from app.database import db_session    # noqa: E402
from starlette.responses import PlainTextResponse as _PTR_no_sw   # noqa: E402

for _r in [r for r in M.app.router.routes if getattr(r, 'path', '') == '/sw.js']:
    M.app.router.routes.remove(_r)


@M.app.get('/sw.js')
async def _sw_noop_for_test():
    return _PTR_no_sw('/* 시험용 빈 서비스워커 — 아무 일도 하지 않는다 */', media_type='application/javascript')


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

D = "2026-10-19"
SUM = "## 핵심\n검사기 컨셉과 견적 조건을 들었다(지어낸 시험 글).\n\n## 일정\n- [결정] 견적은 **금요일**까지 낸다"
#  (이름, 회의 날짜, 시작(msg_started_at), 끝(ended_at))
CASES = [
    ("T1 시작·끝 같은 날", D, "2026-10-19 14:00:27", "2026-10-19 14:50:28"),
    ("T2 시작만", D, "2026-10-19 14:00:27", ""),
    ("T3 둘 다 없음", D, "", ""),
    ("T4 끝이 다음 날", D, "2026-10-19 14:00:27", "2026-10-20 01:10:00"),
    ("T5 끝이 시작보다 앞", D, "2026-10-19 14:00:27", "2026-10-19 13:50:00"),
    ("T6 같은 분에 끝남", D, "2026-10-19 14:00:27", "2026-10-19 14:00:50"),
    ("T7 시작이 다른 날", D, "2026-10-18 14:00:27", "2026-10-18 15:00:00"),
    ("T8 끝 시각이 이상한 글", D, "2026-10-19 14:00:27", "abc"),
    ("T9 긴 회의", D, "2026-10-19 09:05:10", "2026-10-19 17:40:59"),
    ("T10 회의 날짜 없음", "", "2026-10-19 14:00:27", "2026-10-19 14:50:28"),
    ("T11 끝 시각 초 없음", D, "2026-10-19 14:00:27", "2026-10-19 15:30"),
]
with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code", "lang"):
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s TEXT" % col)
    ta = c.execute("INSERT INTO teams(name, code, display_order) VALUES('기술영업팀','TCA',1)").lastrowid
    me = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='프로', role='member', name='김한국', lang='ko', employee_no='901' WHERE id=?", (ta, me))
    ids = {}
    for name, md, st, en in CASES:
        key = name.split()[0]
        ids[key] = c.execute(
            "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, attendees_text, body, summary, status, location, "
            "msg_started_at, ended_at) VALUES(?,?,?,?,'all','김한국, 최민수','지어낸 회의 메모',?,'draft','2층 회의실1',?,?)",
            (name, md, me, ta, SUM, st or None, en or None)).lastrowid
seed = {"me": me, "port": PORT, "ids": ids, "cases": CASES}
io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(json.dumps(seed, ensure_ascii=False))
print("READY", PORT, json.dumps(ids, ensure_ascii=False), flush=True)
th.join()
