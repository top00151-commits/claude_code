# -*- coding: utf-8 -*-
"""z1180 시험용 WORKS 서버 — 🔍 모아보기 탭·음성 메모 검색 + 「빅터AI」 글.
사용: py run_search80_app.py <앱폴더(절대경로)> <포트>

🔵 이음만 가짜다 — `sso_client.fetch_msg_meetings`(이음에 회의 목록을 묻는 한 함수)를 바꿔 끼운다.
   🔴 가짜도 **진짜처럼 날짜로 거른다**(시작일이 from~to 안인 것만) — 「처음엔 60일 전부터 · 옛 기간은 더 불러와야」를
      그대로 재려고. 물은 기간은 `/__test/eum_calls` 로 본다(옛 기간 불러오기가 끝없이 돌지 않는지).
   공개 범위·회의록 검색은 **진짜 서버**가 한다.
🔵 AI 도 가짜다(부르지 않는다) — 느린 가짜(2초)로 「빅터AI가 … 정리하는 중…」 진행 칸을 본다.
   `/__test/ai?on=0` 이면 「AI 꺼짐」(서버 안내 글 시험) · `?on=1` 이면 다시 켬.

세우는 것
  · 사람 넷 — 나(김한국 · 기술영업팀) · 보기만(박성수 · 다른 팀) · 베트남어(Nguyen · 나와 같은 팀 · lang=vi) · 남(이영희 · 다른 팀)
  · 이음 회의 6건(msg 201~206):
      C1 「삼성 설비 미팅」 2일 전 · 장소 본사 3층 · 참석 김한국·최민수 · 외부 「삼성 박부장」 · 회의록(공개) 원문에 「IPO」
      C2 「주간 회의」 5일 전 · 참석 김한국·박성수 · 회의록(공개) 정리에 「현대모비스」·「IPO」 (정리 끝)
      C3 「경영 회의」 7일 전 · 참석 이영희 · 회의록 **비공개(이영희 것)** — 정리에 「비밀단어」·「IPO」 → 나는 못 본다
      C4 「옛날 설비 회의 고대유물」 **200일 전**(처음 60일 밖)      C5 「아주옛날 회의」 **600일 전**(첫 440일 묶음 밖)
      C6 「예정 설비 점검」 3일 뒤
  · 음성 메모 — 내 것 넷(N1 현대모비스 · N2 원문 5만 2천 자 끝에 「희귀낱말」 · N3 설비·「30%」·「50_60」 · N4 녹음 없음) · 남의 것 하나(O1 현대모비스)
  · 「빅터AI」 화면용 내 회의 M5(원문만 · 정리 전 · AI 가 만든 결정·할 일 꼬리표) · M6(정리 전 · 결정·할 일 없음 → 빈 칸 안내)
⛔ 진짜 AI 를 부르지 않는다 · 진짜 로그인 대신 쿠키 tuser=<사람 id>.
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
from app import ai_client              # noqa: E402
from app.database import db_session    # noqa: E402

# 🧹 시험에서는 **아무 일도 안 하는** 서비스워커(운영 /sw.js 는 화면을 다시 읽혀 시험이 터진다 · z1174)
from starlette.responses import PlainTextResponse as _PTR_no_sw   # noqa: E402
from starlette.responses import JSONResponse as _JR               # noqa: E402
for _r in [r for r in M.app.router.routes if getattr(r, 'path', '') == '/sw.js']:
    M.app.router.routes.remove(_r)


@M.app.get('/sw.js')
async def _sw_noop_for_test():
    return _PTR_no_sw('/* 시험용 빈 서비스워커 — 아무 일도 하지 않는다 */',
                      media_type='application/javascript')


# ── 가짜 AI (2초 · 틀은 진짜와 같다) ──
AI_ON = [True]
SLOW = 2.0
ai_client.ai_available = lambda: AI_ON[0]
ai_client.transcribe_available = lambda: True


def slow_meeting(body, context=""):
    time.sleep(SLOW)
    #  서버 실패 글 시험 — 「까닭 없는 실패」(error 칸 없음) · 「터짐」(예외)
    if "NOERRKEY" in (body or ""):
        return (False, {})
    if "EXPLODE" in (body or ""):
        raise RuntimeError("가짜 폭발")
    return (True, {
        "decisions": [{"who": "김한국", "what": "가짜 결정", "due": "2026-10-20"}],
        "actions": [{"assignee": "김한국", "task": "가짜 할 일", "due": "2026-10-21"}],
        "summary": "요점\n- 가짜 정리 (원문 %d자)" % len(body or ""),
        "title": "",
    })


def slow_note(body):
    time.sleep(SLOW)
    return (True, {"summary": "요점\n- 가짜 정리 (원문 %d자)\n할 일\n- 없음" % len(body or ""), "title": ""})


ai_client.ai_extract_meeting = slow_meeting
ai_client.ai_extract_note = slow_note


@M.app.get('/__test/ai')
async def _test_ai(on: int = 1):
    AI_ON[0] = bool(on)
    return _JR({"ok": True, "ai": AI_ON[0]})


def fake_get_user(req):
    uid = req.cookies.get("tuser")
    with db_session() as c:
        if uid:
            r = c.execute("SELECT * FROM users WHERE id=?", (int(uid),)).fetchone()
        else:
            r = c.execute("SELECT * FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()
        return dict(r) if r else None


M.get_user = fake_get_user

# ── 가짜 이음 (날짜로 거른다) ──
NOW = datetime.now()


def at(days=0, minutes=0):
    return (NOW + timedelta(days=days, minutes=minutes)).strftime("%Y-%m-%dT%H:%M")


EUM = {   # msg id → 카드
    201: dict(title="삼성 설비 미팅", start_at=at(-2), location="본사 3층 회의실", organizer="김한국",
              attendees=["김한국", "최민수"], externals=["삼성 박부장"]),
    202: dict(title="주간 회의", start_at=at(-5), location="", organizer="김한국",
              attendees=["김한국", "박성수"], externals=[]),
    203: dict(title="경영 회의", start_at=at(-7), location="", organizer="이영희",
              attendees=["이영희"], externals=[]),
    204: dict(title="옛날 설비 회의 고대유물", start_at=at(-200), location="", organizer="김한국",
              attendees=["김한국"], externals=[]),
    205: dict(title="아주옛날 회의", start_at=at(-600), location="", organizer="김한국",
              attendees=["김한국"], externals=[]),
    206: dict(title="예정 설비 점검", start_at=at(3), location="", organizer="김한국",
              attendees=["김한국"], externals=[]),
}
CALLS = []


def fake_fetch(emp, d_from, d_to, timeout=8.0):
    CALLS.append({"from": d_from, "to": d_to})
    items = []
    for mid, e in EUM.items():
        day = e["start_at"][:10]
        if not (d_from <= day <= d_to):
            continue
        items.append({"id": mid, "title": e["title"], "start_at": e["start_at"], "tz_offset": 9, "tz_label": "",
                      "duration_min": 60, "location": e["location"], "visibility": "all",
                      "organizer": {"name": e["organizer"]},
                      "attendees": [{"name": n, "response": "attending"} for n in e["attendees"]],
                      "externals": list(e["externals"]),
                      "me": {"is_organizer": False, "is_attendee": True, "response": "attending"}})
    return {"ok": True, "items": items, "truncated": False}


sso_client.fetch_msg_meetings = fake_fetch


@M.app.get('/__test/eum_calls')
async def _test_eum_calls():
    return _JR({"calls": CALLS})


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

    def person(login, name, team, lang, emp):
        return c.execute(
            "INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang, employee_no) "
            "VALUES(?,?,'프로','member',?,1,'x-no-login-z1180',?,?)", (login, name, team, lang, emp)).lastrowid
    viewer = person("zs80vw", "박성수", tb, "ko", "902")
    vnu = person("zs80vn", "Nguyen Van A", ta, "vi", "903")
    other = person("zs80ot", "이영희", tb, "ko", "904")

    def mtg(title, owner, team, vis, body="", summary="", msg_id=None, days=0, att="김한국"):
        return c.execute(
            "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, attendees_text, body, summary, "
            "                     status, msg_meeting_id) VALUES(?,?,?,?,?,?,?,?,'draft',?)",
            (title, (NOW + timedelta(days=days)).strftime("%Y-%m-%d"), owner, team, vis, att, body, summary,
             msg_id)).lastrowid

    S = {}
    S["M1"] = mtg("삼성 설비 미팅", me, ta, "all", body="라인 증설 이야기. IPO 일정은 내년 상반기로 본다.",
                  summary="", msg_id=201, days=-2, att="김한국, 최민수")
    S["M2"] = mtg("주간 회의", me, ta, "all", body="원문",
                  summary="요점\n- 현대모비스 납기 확인\n- IPO 자료 준비", msg_id=202, days=-5, att="김한국, 박성수")
    S["M3"] = mtg("경영 회의", other, tb, "private", body="원문", summary="요점\n- 비밀단어 IPO 논의",
                  msg_id=203, days=-7, att="이영희")
    #  「빅터AI」 화면용 — 정리 전 내 회의(원문만) + AI 가 만든 결정·할 일(꼬리표 「빅터AI」)
    S["M5"] = mtg("다시 정리 시험 회의", me, ta, "team", body="회의 원문입니다. 다시 정리 시험.", summary="", days=-1)
    c.execute("INSERT INTO meeting_decisions(meeting_id, who, what, due) VALUES(?,?,?,?)", (S["M5"], "김한국", "가짜 결정 줄", ""))
    c.execute("INSERT INTO meeting_actions(meeting_id, assignee_name, task, due_date) VALUES(?,?,?,?)",
              (S["M5"], "김한국", "가짜 할 일 줄", ""))
    #  결정·할 일 없는 정리 전 회의 → 빈 칸 안내(「💾 저장하고 빅터AI 정리」를 누르거나…)
    S["M6"] = mtg("빈 회의", me, ta, "team", body="", summary="", days=-1)
    #  서버 실패 글 시험용(가짜 AI 가 원문 낱말을 보고 실패한다)
    S["M7"] = mtg("까닭 없는 실패 회의", me, ta, "team", body="NOERRKEY 원문", summary="", days=-1)
    S["M8"] = mtg("터지는 회의", me, ta, "team", body="EXPLODE 원문", summary="", days=-1)
    #  베트남어 직원은 M5 의 참석자 — 참석자는 고칠 수 있다(z1133) → 베트남어 글을 본다
    c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,?)", (S["M5"], vnu, "Nguyen Van A"))
    c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,?)", (S["M1"], me, "김한국"))

    def note(owner, title, summary, body, audio=""):
        return c.execute("INSERT INTO voice_notes(owner_id, title, summary, body, audio_path) VALUES(?,?,?,?,?)",
                         (owner, title, summary, body, audio)).lastrowid
    N = {}
    N["N1"] = note(me, "거래처 통화", "요점\n- 현대모비스 납기 확인", "현대모비스 담당자와 통화했다. 납기 확인.")
    N["N2"] = note(me, "", "", "가" * 52000 + " 희귀낱말 " + "나" * 300)
    N["N3"] = note(me, "설비 점검 메모", "요점\n- 할인율 30% 확인", "설비 점검 50_60 구간 이야기")
    N["N4"] = note(me, "녹음 없는 메모", "", "")
    N["O1"] = note(other, "남의 메모 현대모비스", "현대모비스", "현대모비스 남의 원문")

seed = {"me": me, "viewer": viewer, "vnu": vnu, "other": other, "port": PORT, "ids": S, "notes": N,
        "today": NOW.strftime("%Y-%m-%d")}
io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(json.dumps(seed, ensure_ascii=False))
print("READY", PORT, json.dumps(seed, ensure_ascii=False), flush=True)
th.join()
