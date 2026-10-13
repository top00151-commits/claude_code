# -*- coding: utf-8 -*-
"""z1178 시험용 WORKS 서버 — 🔍 회의록 검색을 잰다.
사용: py run_mtgq_app.py <앱폴더(절대경로)> <포트>

세우는 것
  · 팀 둘 — A 기술영업팀 · B 라이프밸류팀
  · 사람 넷 — 나(김한국 · A · member) · 남(박성수 · B · member) · 대표(김대표 · ceo) · 베트남어 직원(A · lang=vi)
  · 회의 14 — 고객사 이름이 **칸마다 하나씩** 들어간다(제목·원문 3만 자 뒤·정리·참석자·결정·할 일·장소)
      🔴 남의 **비공개** 회의(M9)와 **다른 팀** 회의(M14)에도 「삼성전기」를 넣는다 → 나에겐 안 나와야 한다
      🔴 「100%」·「A_B」 — % 와 _ 를 글자 그대로 찾는가
⛔ AI 를 부르지 않는다(키를 비운다) · 진짜 로그인 대신 쿠키 tuser=<사람 id>.
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

# 🧹 시험에서는 **아무 일도 안 하는** 서비스워커를 내준다(운영 /sw.js 는 화면을 다시 읽혀 시험이 터진다 · z1174).
#    ⛔ 운영 /sw.js 는 건드리지 않는다. 이 줄은 **시험 서버에만** 있다.
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

with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code", "lang"):
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s TEXT" % col)
    ta = c.execute("INSERT INTO teams(name, code, display_order) VALUES('기술영업팀','TQA',1)").lastrowid
    tb = c.execute("INSERT INTO teams(name, code, display_order) VALUES('라이프밸류팀','TQB',2)").lastrowid

    me = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    #  🔴 role 은 member — admin/ceo 로 두면 공개 범위 시험을 못 한다
    c.execute("UPDATE users SET team_id=?, rank='과장', role='member', name='김한국', lang='ko' WHERE id=?",
              (ta, me))
    other = c.execute(
        "INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang) "
        "VALUES('zq78ot','박성수','프로','member',?,1,'x-no-login-z1178','ko')", (tb,)).lastrowid
    boss = c.execute(
        "INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang) "
        "VALUES('zq78ceo','김대표','대표이사','ceo',?,1,'x-no-login-z1178','ko')", (ta,)).lastrowid
    vnu = c.execute(
        "INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang) "
        "VALUES('zq78vn','Nguyen Van A','member','member',?,1,'x-no-login-z1178','vi')", (ta,)).lastrowid

    def mtg(title, owner, team, vis="team", body="", summary="", att="", loc="", date="2026-10-13"):
        return c.execute(
            "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, attendees_text, "
            "                     body, summary, location, status) VALUES(?,?,?,?,?,?,?,?,?,'draft')",
            (title, date, owner, team, vis, att, body, summary, loc)).lastrowid

    S = {}
    S["M1"] = mtg("삼성전기_출하검사기 관련 컨셉 미팅", me, ta, body="출하검사기 사양을 논의했다.",
                  summary="요점\n- 컨셉 확정", date="2026-10-13")
    S["M2"] = mtg("주간 회의", me, ta,
                  body=("가나다라 " * 6000) + " LG이노텍 라인 증설 일정을 공유했다. " + ("마바사 " * 500),
                  summary="요점\n- 일정 공유", date="2026-10-12")
    S["M3"] = mtg("단가 회의", me, ta, body="단가 이야기", summary="요점\n- 드림텍 단가 협의 진행", date="2026-10-11")
    S["M4"] = mtg("외부 미팅", me, ta, body="소개", att="한화솔루션 최부장, 김한국", date="2026-10-10")
    S["M5"] = mtg("견적 회의", me, ta, body="견적", date="2026-10-09")
    c.execute("INSERT INTO meeting_decisions(meeting_id, who, what, due, source) "
              "VALUES(?,'김한국','SKC 견적 회신 금요일까지','2026-10-17','manual')", (S["M5"],))
    S["M6"] = mtg("샘플 회의", me, ta, body="샘플", date="2026-10-08")
    c.execute("INSERT INTO meeting_actions(meeting_id, assignee_name, task, due_date, source) "
              "VALUES(?,'김한국','포스코 샘플 발송','2026-10-20','manual')", (S["M6"],))
    S["M7"] = mtg("현장 방문", me, ta, body="방문", loc="판교 고객사 회의실", date="2026-10-07")
    S["M8"] = mtg("라이프밸류 주간회의", other, tb, vis="all", body="주간 보고", date="2026-10-06")
    #  🔴 남의 비공개 회의 — 나는 못 본다(참석자도 아니다) · 「삼성전기」가 들어 있다
    S["M9"] = mtg("비공개 단가 회의", other, tb, vis="private", body="삼성전기 비밀 단가 협의", date="2026-10-05")
    S["M10"] = mtg("100% 달성 회의", me, ta, body="목표 100% 달성", date="2026-10-04")
    S["M11"] = mtg("A_B 테스트", me, ta, body="실험", date="2026-10-03")
    S["M12"] = mtg("임원 보고", me, ta, body="보고", date="2026-10-02")
    c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,'')", (S["M12"], boss))
    S["M13"] = mtg("LG이노텍 협력 회의", me, ta, body="협력", date="2026-10-01")
    #  🔴 다른 팀(B) 「팀 공개」 회의 — 나는 못 본다 · 「삼성전기」가 들어 있다
    S["M14"] = mtg("라이프밸류 팀 회의", other, tb, vis="team", body="삼성전기 납품 일정", date="2026-09-30")

seed = {"me": me, "other": other, "boss": boss, "vnu": vnu, "ta": ta, "tb": tb, "port": PORT}
seed.update(S)
io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(
    json.dumps(seed, ensure_ascii=False))
print("READY", PORT, json.dumps(seed, ensure_ascii=False), flush=True)
th.join()
