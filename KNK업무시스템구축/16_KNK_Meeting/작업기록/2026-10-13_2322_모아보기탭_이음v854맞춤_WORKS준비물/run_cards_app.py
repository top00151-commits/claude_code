# -*- coding: utf-8 -*-
"""z1179 시험용 WORKS 서버 — 🗓 회의 카드 모아보기 탭(이음 v854~v856 과 맞춤)을 **진짜 서버 판단**으로 잰다.
사용: py run_cards_app.py <앱폴더(절대경로)> <포트>

🔵 이음만 가짜다 — `sso_client.fetch_msg_meetings`(이음에 회의 목록을 묻는 한 함수)를 바꿔 끼운다.
   단계(정리 중·멈춤·AI 실패)와 「고칠 수 있는 사람」은 **진짜 서버**가 계산한다.

세우는 것
  · 사람 셋 — 나(김한국 · 회의록 작성자 = 고칠 수 있다) · 보기만(박성수 · 다른 팀 · 공개라 볼 수만) · 베트남어(Nguyen · 나와 같은 팀 · lang=vi)
  · 이음 회의 9건(msg 101~109)과 그 회의록(108 은 회의록 없음):
      S1 시작만·지금 회의 중   S1b 시작만·끝남          S2 녹음 막 들어옴(정리 대기)
      S3 🔴 녹음 있는데 30분째 아무것도 안 돎(멈춤)    S4 받아쓰기 도는 중   S5 AI 정리 도는 중
      S6 🔴 AI 정리 실패        S7 정리 끝(📋 회의록 등록)   S9 회의록이 아예 없는 끝난 회의
⛔ AI 를 부르지 않는다 · 진짜 로그인 대신 쿠키 tuser=<사람 id>.
"""
import io
import json
import os
import shutil
import sys
import threading
import time
from datetime import datetime, timedelta

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
from app import sso_client             # noqa: E402
from app.database import db_session    # noqa: E402

# 🧹 시험에서는 **아무 일도 안 하는** 서비스워커(운영 /sw.js 는 화면을 다시 읽혀 시험이 터진다 · z1174)
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

#  이음 회의 시각 = 한국 시각 「YYYY-MM-DDTHH:MM」 · 지금 기준으로 놓는다
NOW = datetime.now()
def at(minutes_from_now):
    return (NOW + timedelta(minutes=minutes_from_now)).strftime("%Y-%m-%dT%H:%M")

EUM = {   # msg id → (제목, 시작(지금부터 분), 길이(분))
    101: ("S1 시작만·지금 회의 중", -10, 60),
    102: ("S1b 시작만·끝남", -180, 60),
    103: ("S2 녹음 막 들어옴", -120, 60),
    104: ("S3 녹음 있는데 멈춤", -150, 60),
    105: ("S4 받아쓰기 도는 중", -100, 60),
    106: ("S5 AI 정리 도는 중", -90, 60),
    107: ("S6 AI 정리 실패", -80, 60),
    #  🔴 제목에 「회의록 없음」을 넣지 말 것 — 검사기가 탭 글 전체에서 그 낱말을 찾는다(첫 판에 제목이 걸렸다)
    108: ("S9 기록 없이 끝난 회의", -200, 60),
    109: ("S7 정리 끝", -240, 60),
}


def fake_fetch(emp, d_from, d_to, timeout=8.0):
    items = []
    for mid, (title, start, dur) in EUM.items():
        items.append({"id": mid, "title": title, "start_at": at(start), "tz_offset": 9, "tz_label": "",
                      "duration_min": dur, "location": "", "visibility": "all",
                      "organizer": {"name": "김한국"}, "attendees": [], "externals": [],
                      "me": {"is_organizer": False, "is_attendee": True, "response": "attending"}})
    return {"ok": True, "items": items, "truncated": False}


sso_client.fetch_msg_meetings = fake_fetch

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
    ta = c.execute("INSERT INTO teams(name, code, display_order) VALUES('기술영업팀','TCA',1)").lastrowid
    tb = c.execute("INSERT INTO teams(name, code, display_order) VALUES('라이프밸류팀','TCB',2)").lastrowid
    me = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='과장', role='member', name='김한국', lang='ko', employee_no='901' "
              "WHERE id=?", (ta, me))
    viewer = c.execute(
        "INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang, employee_no) "
        "VALUES('zc79vw','박성수','프로','member',?,1,'x-no-login-z1179','ko','902')", (tb,)).lastrowid
    vnu = c.execute(
        "INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang, employee_no) "
        "VALUES('zc79vn','Nguyen Van A','member','member',?,1,'x-no-login-z1179','vi','903')", (ta,)).lastrowid

    def mtg(msg_id, body="", summary="", audio=""):
        return c.execute(
            "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, attendees_text, body, summary, "
            "                     audio_path, status, msg_meeting_id) VALUES(?,?,?,?,'all','김한국',?,?,?,'draft',?)",
            (EUM[msg_id][0], NOW.strftime("%Y-%m-%d"), me, ta, body, summary, audio, msg_id)).lastrowid

    S = {}
    S["S1"] = mtg(101)
    S["S1b"] = mtg(102)
    S["S2"] = mtg(103, audio="meeting_audio/fake_s2.m4a")
    S["S3"] = mtg(104, audio="meeting_audio/fake_s3.m4a")
    #  🔴 멈춤 = 마지막으로 고친 지 30분(_MTG_STALL_MIN 10분보다 오래)
    c.execute("UPDATE meetings SET updated_at=datetime('now','localtime','-30 minutes') WHERE id=?", (S["S3"],))
    S["S4"] = mtg(105, audio="meeting_audio/fake_s4.m4a")
    S["S5"] = mtg(106, body="🎙 [음성 변환]\n받아쓴 글", audio="meeting_audio/fake_s5.m4a")
    S["S6"] = mtg(107, body="🎙 [음성 변환]\n받아쓴 글", audio="meeting_audio/fake_s6.m4a")
    #  z1185: 「정리 끝」= 정리 + 회의록 작성됨 — 원문이 메모뿐이면 이제 done 이 아니다 → 받아쓴 글(S5·S6 과 같은 꼴)
    S["S7"] = mtg(109, body="🎙 [음성 변환]\n받아쓴 글", summary="요점\n- 정리 끝")
    #  108 = 회의록 없음(WORKS 에 없다)
    #  베트남어 직원은 S1·S3·S6 의 **참석자** — 참석자는 고칠 수 있다(z1133) → 베트남어 단추 글을 본다
    for k in ("S1", "S3", "S6"):
        c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,?)", (S[k], vnu, "Nguyen Van A"))

#  🔵 작업 상태 — 받아쓰기(S4) · AI 정리(S5 도는 중 · S6 실패)
with M._STT_LOCK:
    M._STT_JOBS[S["S4"]] = {"state": "running", "error": ""}
with M._MTG_SUM_LOCK:
    M._MTG_SUM_JOBS[S["S5"]] = {"state": "running", "error": "", "result": {}}
    M._MTG_SUM_JOBS[S["S6"]] = {"state": "error", "error": "가짜 실패", "result": {}}

#  서버가 계산한 단계 — 이음이 받는 값(msg/status)과 같은 함수
with db_session() as c:
    stages = {k: M._meeting_msg_stage(dict(c.execute("SELECT * FROM meetings WHERE id=?", (v,)).fetchone()))
              for k, v in S.items()}

seed = {"me": me, "viewer": viewer, "vnu": vnu, "port": PORT, "ids": S, "stages": stages,
        "stall_min": getattr(M, "_MTG_STALL_MIN", None)}
io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(json.dumps(seed, ensure_ascii=False))
print("READY", PORT, json.dumps(seed, ensure_ascii=False), flush=True)
th.join()
