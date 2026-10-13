# -*- coding: utf-8 -*-
"""z1162 시험용 WORKS 서버 — 바깥 틀(왼쪽 메뉴)을 네 사람으로 띄워 보려고.
사용: py run_shell_app.py <앱폴더(절대경로)> <포트>

세우는 사람 넷 — 🔴 **말만 다르고 권한·소속은 짝끼리 똑같아야** 한다
  · ko_ceo  김정락   대표이사 총괄  role=ceo     lang=ko
  · vi_ceo  Nguyen A 대표이사 총괄  role=ceo     lang=vi
  · ko_lead 한도윤   팀장  검사기T  role=member  lang=ko  position='팀장'
  · vi_lead Tran B   팀장  검사기T  role=member  lang=vi  position='팀장'
🔴 팀장 두 사람은 **권한 판정이 안 깨졌는지** 보려고 있다 —
   chrome.html 의 `_is_leader` 가 '팀장' 글자를 직책에서 찾는다. 번역하면 메뉴가 사라진다.
🔴 AI 키는 비운다.
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

import uvicorn                         # noqa: E402
from app import main as M              # noqa: E402
from app.database import db_session    # noqa: E402

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
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code", "lang",
                "position", "dept"):
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s TEXT" % col)

    def team(nm, code, order):
        r = c.execute("SELECT id FROM teams WHERE name=?", (nm,)).fetchone()
        return r[0] if r else c.execute(
            "INSERT INTO teams(name, code, display_order) VALUES(?,?,?)", (nm, code, order)).lastrowid

    t_head = team("총괄", "TS0", 0)
    t_insp = team("검사기T", "TS1", 1)

    ko_ceo = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='대표이사', role='ceo', name='김정락', lang='ko',"
              " position='대표이사', dept='총괄' WHERE id=?", (t_head, ko_ceo))

    def emp(login, nm, rank, role, tid, lang, pos, dept):
        return c.execute(
            "INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang,"
            "                  position, dept) VALUES(?,?,?,?,?,1,'x-no-login-z1162',?,?,?)",
            (login, nm, rank, role, tid, lang, pos, dept)).lastrowid

    vi_ceo = emp("z62vc", "Nguyen Van A", "대표이사", "ceo", t_head, "vi", "대표이사", "총괄")
    ko_lead = emp("z62kl", "한도윤", "팀장", "member", t_insp, "ko", "팀장", "검사기T")
    vi_lead = emp("z62vl", "Tran Van B", "팀장", "member", t_insp, "vi", "팀장", "검사기T")

io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(json.dumps(
    {"ko_ceo": ko_ceo, "vi_ceo": vi_ceo, "ko_lead": ko_lead, "vi_lead": vi_lead,
     "port": PORT, "app": APP}, ensure_ascii=False))
print("READY", PORT, "ko_ceo", ko_ceo, "vi_ceo", vi_ceo, "ko_lead", ko_lead, "vi_lead", vi_lead,
      flush=True)
th.join()
