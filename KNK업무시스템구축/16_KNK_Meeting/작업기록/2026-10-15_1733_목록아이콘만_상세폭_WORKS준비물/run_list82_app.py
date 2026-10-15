# -*- coding: utf-8 -*-
"""z1182 시험용 WORKS 서버 — 회의록 목록(아이콘만 눌림 · 보기 전용 「🔍 회의상세(보기)」) · 회의록 상세 폭.
사용: py run_list82_app.py <앱폴더(절대경로)> <포트>

세우는 것
  · 사람 셋 — 나(김한국 · 기술영업팀 · 회의록 작성자 = 고칠 수 있다) · 보기만(박성수 · 다른 팀) · 베트남어(Nguyen · 다른 팀 · lang=vi)
  · 회의 둘 — M1 「삼성 2호기 납기 협의」(전사 공개 · 원문 길게) · M2 「주간 회의」(전사 공개 · 정리 있음)
    → 나는 둘 다 고칠 수 있고, 박성수·Nguyen 은 **보기만**(공개 범위로 보임 · 참석자 아님)
⛔ AI 를 부르지 않는다 · 진짜 로그인 대신 쿠키 tuser=<사람 id>.
"""
import io
import json
import os
import shutil
import sys
import threading
import time
from datetime import datetime

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
from starlette.responses import PlainTextResponse as _PTR_no_sw   # noqa: E402

for _r in [r for r in M.app.router.routes if getattr(r, 'path', '') == '/sw.js']:
    M.app.router.routes.remove(_r)


@M.app.get('/sw.js')
async def _sw_noop_for_test():
    return _PTR_no_sw('/* 시험용 빈 서비스워커 — 아무 일도 하지 않는다 */',
                      media_type='application/javascript')


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

TODAY = datetime.now().strftime("%Y-%m-%d")
with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code", "lang"):
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s TEXT" % col)
    ta = c.execute("INSERT INTO teams(name, code, display_order) VALUES('기술영업팀','TCA',1)").lastrowid
    tb = c.execute("INSERT INTO teams(name, code, display_order) VALUES('라이프밸류팀','TCB',2)").lastrowid
    me = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='과장', role='member', name='김한국', lang='ko', employee_no='901' "
              "WHERE id=?", (ta, me))

    def person(login, name, team, lang, emp):
        return c.execute(
            "INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang, employee_no) "
            "VALUES(?,?,'프로','member',?,1,'x-no-login-z1182',?,?)", (login, name, team, lang, emp)).lastrowid
    viewer = person("zl82vw", "박성수", tb, "ko", "902")
    vnu = person("zl82vn", "Nguyen Van A", tb, "vi", "903")

    def mtg(title, body, summary=""):
        return c.execute(
            "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, attendees_text, body, summary, status) "
            "VALUES(?,?,?,?,'all','김한국',?,?,'draft')", (title, TODAY, me, ta, body, summary)).lastrowid
    S = {}
    S["M1"] = mtg("삼성 2호기 납기 협의", ("1. 미팅안건: 보드 TEST 결과 및 추후 일정 협의\n\n"
                                          + "보드 개발은 완료됐고 기존 보드와 호환되도록 검증했습니다. " * 40).strip())
    S["M2"] = mtg("주간 회의", "원문", "결론\n- 납기 11-20 확정\n목적\n- 일정 협의\n회의 내용\n- 출하 일정 공유")

seed = {"me": me, "viewer": viewer, "vnu": vnu, "port": PORT, "ids": S}
io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(json.dumps(seed, ensure_ascii=False))
print("READY", PORT, json.dumps(seed, ensure_ascii=False), flush=True)
th.join()
