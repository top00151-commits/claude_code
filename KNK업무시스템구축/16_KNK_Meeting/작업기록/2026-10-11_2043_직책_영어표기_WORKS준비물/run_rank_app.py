# -*- coding: utf-8 -*-
"""z1163 시험용 WORKS 서버 — 직책을 두 언어로 띄워 보려고.
사용: py run_rank_app.py <앱폴더(절대경로)> <포트>

세우는 사람 — 🔴 **말만 다르고 직책·권한은 짝끼리 똑같이**
  · ko_ceo  김정락    대표이사    role=ceo    lang=ko
  · vi_ceo  Nguyen A  대표이사    role=ceo    lang=vi
  · ko_lead 한도윤    과장(팀장)  role=ceo    lang=ko   ← 관리 화면도 봐야 하니 ceo
  · vi_lead Tran B    과장(팀장)  role=ceo    lang=vi
  그리고 명단에 나올 사람들: 사원·프로·매니저·상무이사·법인장·반장 (운영에 있는 직책들)
🔴 AI 키는 비운다.
"""
import io
import json
import os
import shutil
import sys
import threading
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
APP = sys.argv[1]
PORT = int(sys.argv[2])
os.chdir(APP)
sys.path.insert(0, APP)
os.environ.setdefault("KNK_SECRET_KEY", "verify-only-key")
os.environ["KNK_MESSENGER_SSO_INTERNAL_BASE"] = "http://127.0.0.1:9"
for _k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "KNK_OPENAI_API_KEY"):
    os.environ[_k] = ""
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
    for col in ("name_vi", "name_en", "employee_no", "entity", "lang"):
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s TEXT" % col)

    def team(nm, code, order):
        r = c.execute("SELECT id FROM teams WHERE name=?", (nm,)).fetchone()
        return r[0] if r else c.execute(
            "INSERT INTO teams(name, code, display_order) VALUES(?,?,?)",
            (nm, code, order)).lastrowid

    t_head = team("총괄", "TR0", 0)
    t_insp = team("검사기T", "TR1", 1)

    ko_ceo = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='대표이사', role='ceo', name='김정락', lang='ko' "
              "WHERE id=?", (t_head, ko_ceo))

    def emp(login, nm, rank, tid, lang, role="member"):
        return c.execute(
            "INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang) "
            "VALUES(?,?,?,?,?,1,'x-no-login-z1163',?)",
            (login, nm, rank, role, tid, lang)).lastrowid

    vi_ceo = emp("z63vc", "Nguyen Van A", "대표이사", t_head, "vi", "ceo")
    ko_lead = emp("z63kl", "한도윤", "과장(팀장)", t_insp, "ko", "ceo")
    vi_lead = emp("z63vl", "Tran Van B", "과장(팀장)", t_insp, "vi", "ceo")
    # 명단에 나올 사람들 — 운영에 있는 직책을 골고루
    for i, (nm, rk) in enumerate([("오세진", "사원"), ("문가온", "프로"), ("배하늘", "매니저"),
                                  ("최하람", "상무이사"), ("Le Van C", "법인장"),
                                  ("Pham D", "반장"), ("유지호", "매니저(팀장)"),
                                  ("Vu E", "차장(팀장)"), ("신가빈", "부장")]):
        emp("z63m%d" % i, nm, rk, t_insp, "ko")

io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(json.dumps(
    {"ko_ceo": ko_ceo, "vi_ceo": vi_ceo, "ko_lead": ko_lead, "vi_lead": vi_lead,
     "port": PORT, "app": APP}, ensure_ascii=False))
print("READY", PORT, "ko_ceo", ko_ceo, "vi_ceo", vi_ceo, flush=True)
th.join()
