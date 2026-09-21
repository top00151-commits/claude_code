# -*- coding: utf-8 -*-
"""미리보기 — 실제 WORKS 앱(고친 사본 · 8921) + 가짜 이음 회의 입구(8922).
로그인 = 쿠키 tuser=<users.id> (시험 전용). 이음 입구는 공유키가 맞을 때만 응답(실제 계약 모양)."""
import io, json, os, sys, threading, time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.environ.get("KNK_APP_DIR") or os.path.join(HERE, "apptest")   # z1119: 고친 사본을 밖에서 지정
os.chdir(APP)
sys.path.insert(0, APP)
os.environ.setdefault("KNK_SECRET_KEY", "verify-only-key")
# 🔴 2026-09-17: 이 PC 에는 OPENAI_API_KEY 가 있어 시험 녹음(가짜 마이크 삐 소리)이 실제 OpenAI 로 가고 있었다
#    (시험 DB 에 「🎙 [음성 변환] You」) → 시험 서버는 AI 키를 비우고, 필요한 AI 는 아래에서 가짜로 바꾼다
for _k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "KNK_OPENAI_API_KEY"):
    os.environ[_k] = ""
os.environ["KNK_SSO_SERVICE_KEY"] = "preview-shared-key"
os.environ["KNK_MESSENGER_SSO_INTERNAL_BASE"] = "http://127.0.0.1:8922"
sys.stdout.reconfigure(encoding="utf-8")

import shutil
shutil.rmtree(os.path.join(APP, "data"), ignore_errors=True)

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
from app import main as M
from app.database import db_session

KST = timezone(timedelta(hours=9))
now = datetime.now(KST)
today = now.date()


def at(day_off, hh, mm):
    d = today + timedelta(days=day_off)
    return f"{d.isoformat()}T{hh:02d}:{mm:02d}"


def A(name, resp=None, org=False):   # 응답 없음 = None (이음 계약 · 세션 10 회신)
    return {"name": name, "response": resp, "is_organizer": org}


# 9/16 회의 4건 = 대표 사진1 그대로 · 나머지 = 모양을 보여주려는 [예시]
live_start = now - timedelta(minutes=25)
MSG = [
    {"id": 101, "title": "먹자", "start_at": "2026-09-16T12:05", "tz_offset": 9, "tz_label": "한국",
     "duration_min": 30, "location": "김정락", "visibility": "private",
     "organizer": {"name": "김정락 대표이사"},
     "attendees": [A("김정락", "attending", True), A("안지연", "attending")], "externals": [],
     "me": {"is_organizer": True, "is_attendee": True, "response": "attending"}},
    {"id": 102, "title": "삼성전기_Clip Attach_진행상황 및 일정 관련 미팅", "start_at": "2026-09-16T00:00",
     "tz_offset": 9, "tz_label": "한국", "duration_min": 60, "location": "2층 소회의실", "visibility": "all",
     "organizer": {"name": "배승진 프로"},
     "attendees": [A(n) for n in ("권혁인", "김형렬", "다이", "득피", "박지만")] + [A("배승진", "attending", True), A("허동준")],
     "externals": [], "me": {"is_organizer": False, "is_attendee": False, "response": None}},
    {"id": 103, "title": "삼성전기_FPGA 관련 설비 TEST 결과 관련 미팅", "start_at": "2026-09-16T15:00",
     "tz_offset": 9, "tz_label": "한국", "duration_min": 60, "location": "2층 회의실2", "visibility": "all",
     "organizer": {"name": "배승진 프로"},
     "attendees": [A("김동후"), A("배승진", "attending", True), A("이해림")], "externals": [],
     "me": {"is_organizer": False, "is_attendee": False, "response": None}},
    {"id": 104, "title": "Soft PLC 연구과제 논의", "start_at": "2026-09-16T15:00", "tz_offset": 9,
     "tz_label": "한국", "duration_min": 60, "location": "1층 소회의실", "visibility": "all",
     "organizer": {"name": "이한중 매니저(팀장)"},
     "attendees": [A("이정우"), A("이한중", "attending", True), A("현종필")], "externals": [],
     "me": {"is_organizer": False, "is_attendee": False, "response": None}},
    {"id": 201, "title": "[예시] 생산 일정 점검", "start_at": live_start.strftime("%Y-%m-%dT%H:%M"),
     "tz_offset": 9, "tz_label": "한국", "duration_min": 90, "location": "3층 대회의실", "visibility": "hq",
     "organizer": {"name": "김정락 대표이사"},
     "attendees": [A("김정락", "attending", True), A("안지연", "attending"), A("예시직원", "change")],
     "externals": [], "me": {"is_organizer": True, "is_attendee": True, "response": "attending"}},
    {"id": 202, "title": "[예시] 품질 이슈 회의", "start_at": "2026-09-15T10:00", "tz_offset": 9,
     "tz_label": "한국", "duration_min": 40, "location": "2층 회의실2", "visibility": "all",
     "organizer": {"name": "예시직원 프로"},
     "attendees": [A("김정락", "attending"), A("예시직원", "attending", True)], "externals": ["고객사 담당 2명"],
     "me": {"is_organizer": False, "is_attendee": True, "response": "attending"}},
    {"id": 203, "title": "[예시] 베트남 법인 주간 회의", "start_at": "2026-09-14T08:30", "tz_offset": 7,
     "tz_label": "베트남", "duration_min": 60, "location": "온라인", "visibility": "all",
     "organizer": {"name": "예시직원 매니저"},
     "attendees": [A("예시직원", "attending", True), A("김정락")], "externals": [],
     "me": {"is_organizer": False, "is_attendee": True, "response": None}},
    {"id": 301, "title": "[예시] 주간 영업 회의", "start_at": at(1, 10, 0), "tz_offset": 9, "tz_label": "한국",
     "duration_min": 60, "location": "1층 소회의실", "visibility": "hq",
     "organizer": {"name": "예시직원 프로"},
     "attendees": [A("김정락", "attending"), A("예시직원", "attending", True), A("안지연", "declined")],
     "externals": [], "me": {"is_organizer": False, "is_attendee": True, "response": "attending"}},
    {"id": 302, "title": "[예시] 협력사 금형 미팅", "start_at": at(5, 14, 0), "tz_offset": 9, "tz_label": "한국",
     "duration_min": 120, "location": "3층 대회의실", "visibility": "all",
     "organizer": {"name": "김정락 대표이사"},
     "attendees": [A("김정락", "attending", True), A("안지연"), A("예시직원", "attending")],
     "externals": ["협력사 대표", "협력사 설계 담당"],
     "me": {"is_organizer": True, "is_attendee": True, "response": "attending"}},
    {"id": 303, "title": "[예시] 설비 셋업 (밤샘)", "start_at": at(8, 22, 0), "tz_offset": 9, "tz_label": "한국",
     "duration_min": 600, "location": "생산동", "visibility": "all",
     "organizer": {"name": "예시직원 프로"},
     "attendees": [A("예시직원", "attending", True), A("김정락")], "externals": [],
     "me": {"is_organizer": False, "is_attendee": True, "response": None}},
]

SEED = {}
FAKE = FastAPI()
SEEN = []
CTL = {"mode": "ok", "delay": 0.0, "extra": [], "base": True, "limit": 0}


@FAKE.post("/api/works/meetings")
async def fake_meetings(req: Request):
    import asyncio
    if req.headers.get("X-SSO-Service-Key") != "preview-shared-key":
        return JSONResponse({"ok": False, "error": "forbidden"}, 403)
    d = await req.json()
    SEEN.append(d)
    if CTL["delay"]:
        await asyncio.sleep(CTL["delay"])
    if CTL["mode"] == "403":
        return JSONResponse({"error": "forbidden"}, 403)
    if CTL["mode"] == "viewer":
        return JSONResponse({"ok": False, "error": "viewer_not_found"}, 404)
    f, t = d.get("from") or "", d.get("to") or ""
    pool = (MSG if CTL["base"] else []) + CTL["extra"]
    items = sorted([m for m in pool if f <= m["start_at"][:10] <= t], key=lambda m: m["start_at"], reverse=True)
    lim = int(CTL.get("limit") or 300)          # 이음 계약: 300건 넘으면 시작이 늦은 쪽만 · truncated
    return JSONResponse({"ok": True, "items": items[:lim], "truncated": len(items) > lim})


@FAKE.post("/__ctl")
async def fake_ctl(req: Request):
    d = await req.json()
    CTL.update(d)
    if d.get("clear_seen"):
        SEEN.clear()
    return {"ok": True, "ctl": CTL}


@FAKE.get("/__seen")
async def fake_seen():
    return {"seen": SEEN}


def fake_get_user(req):
    # 미리보기 전용: 쿠키가 없으면 대표 계정으로 본다 — 로그인 확인이 운영 이음 로그인으로 넘기지 않게(09-16 교훈)
    uid = req.cookies.get("tuser")
    with db_session() as c:
        if not uid:
            r = c.execute("SELECT * FROM users WHERE name='김정락' ORDER BY id LIMIT 1").fetchone()
        else:
            r = c.execute("SELECT * FROM users WHERE id=?", (int(uid),)).fetchone()
        return dict(r) if r else None


M.get_user = fake_get_user


@M.app.post("/__test/cards_reset")
async def _t_cards_reset():
    M._MSG_CARDS_CACHE.clear()
    M._MSG_CARDS_DOWN["until"] = 0.0
    return {"ok": True}


def serve(app, port):
    cfg = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="on")
    srv = uvicorn.Server(cfg)
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(300):
        if srv.started:
            break
        time.sleep(0.1)
    return th


serve(FAKE, 8922)
th = serve(M.app, 8921)

with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code"):
        if col not in have:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
    r = c.execute("SELECT id FROM teams WHERE name='총괄'").fetchone()
    tid = r[0] if r else c.execute("INSERT INTO teams(name, code) VALUES('총괄','TV1')").lastrowid
    ceo = c.execute("SELECT id FROM users WHERE name='김정락'").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='대표이사', role='ceo', is_active=1, employee_no='KNK0001' WHERE id=?",
              (tid, ceo))
    other = c.execute("SELECT id FROM users WHERE id<>? AND role NOT IN ('admin','ceo','executive') "
                      "AND is_active=1 LIMIT 1", (ceo,)).fetchone()[0]
    c.execute("UPDATE users SET employee_no='KNK0002' WHERE id=?", (other,))
    c.execute("DELETE FROM meetings")

    def mk(title, date, msg_id, summary="", audio="", owner=None, vis="private", status="draft"):
        return c.execute(
            "INSERT INTO meetings(title, meeting_date, mode, team_id, owner_id, location, tags, attendees_text, "
            "body, summary, audio_path, visibility, status, msg_meeting_id, msg_started_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now','localtime'))",
            (title, date, "A", tid, owner or ceo, "", "", "김정락", "원문", summary, audio, vis, status, msg_id)).lastrowid

    m1 = mk("먹자", "2026-09-16", 101, summary="핵심: 점심 메뉴 정리")
    for t in ("메뉴 정하기", "예약하기"):
        c.execute("INSERT INTO meeting_actions(meeting_id, assignee_name, task) VALUES(?,?,?)", (m1, "안지연", t))
    m2 = mk("[예시] 생산 일정 점검", today.isoformat(), 201)
    m3 = mk("[예시] 품질 이슈 회의", "2026-09-15", 202, audio="meeting_audio/x.webm", owner=other, vis="all")
    m4 = mk("[예시] 베트남 법인 주간 회의", "2026-09-14", 203, vis="all")
    M._STT_JOBS[m4] = {"state": "error", "error": "예시 오류"}
    # 일반(이음과 무관한) 회의록 몇 개 — 회의록 탭 개수 확인용
    for i, t in enumerate(("검증", "회의록 개선 마지막 회의", "회의록 프로그램 개선안")):
        c.execute("INSERT INTO meetings(title, meeting_date, mode, team_id, owner_id, visibility, status) "
                  "VALUES(?,?,?,?,?,?,?)", (t, "2026-09-16", "A", tid, ceo, "private", "draft"))

info = {"ceo": ceo, "other": other}
SEED.update(info)
io.open(os.path.join(HERE, "seed.json"), "w", encoding="utf-8").write(json.dumps(info))
print("READY", info, flush=True)
th.join()
