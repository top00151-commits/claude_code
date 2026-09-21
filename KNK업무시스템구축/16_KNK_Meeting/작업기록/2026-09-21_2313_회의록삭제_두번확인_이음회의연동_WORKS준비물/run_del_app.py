# -*- coding: utf-8 -*-
"""z1122 화면 시험용 WORKS 서버 (기본 127.0.0.1:8940) — 가짜 이음(삭제 입구·모아보기 목록).
사용: py run_del_app.py <앱폴더(절대경로)> [포트=8940]
🔴 AI 키를 비우고 음성→글자·AI 정리는 가짜 · 이음은 sso_client.httpx 를 바꿔 끼운 가짜(운영에 닿지 않음).
사람은 쿠키 tuser=<사용자 id>. 이음 삭제 요청 기록 = GET /__test/calls"""
import io
import json
import os
import shutil
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
APP = sys.argv[1]
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8940
os.chdir(APP)
sys.path.insert(0, APP)
os.environ.setdefault("KNK_SECRET_KEY", "verify-only-key")
os.environ["KNK_MESSENGER_SSO_INTERNAL_BASE"] = "http://127.0.0.1:9"
for _k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "KNK_OPENAI_API_KEY"):
    os.environ[_k] = ""
sys.stdout.reconfigure(encoding="utf-8")
shutil.rmtree(os.path.join(APP, "data"), ignore_errors=True)
shutil.rmtree(os.path.join(APP, "meeting_audio"), ignore_errors=True)

import uvicorn                       # noqa: E402
from app import main as M            # noqa: E402
from app import sso_client as SC     # noqa: E402
from app.database import db_session   # noqa: E402
from app import ai_client            # noqa: E402

ai_client.transcribe_available = lambda: True
ai_client.ai_transcribe = lambda path, lang="": (True, "[가짜 변환] 시험")
ai_client.ai_available = lambda: True
ai_client.ai_extract_meeting = lambda body, context="": (True, {"summary": "핵심: 가짜", "decisions": [], "actions": [], "title": ""})

KEY = "test-service-key-z1122-ui"
SC.get_service_key = lambda: KEY
CALLS, DELETED, CARDS = [], set(), []
PLAN = {9401: "ok", 9402: "not_allowed", 9403: "html404", 9404: "conn", 9405: "ok", 9406: "ok"}


class _R:
    def __init__(self, status, data=None):
        self.status_code, self._d = status, data

    def json(self):
        if self._d is None:
            raise ValueError("not json")
        return self._d


class _FakeHttpx:
    def post(self, url, headers=None, json=None, timeout=None):
        if url.endswith("/api/works/meetings/delete"):
            j = dict(json or {})
            CALLS.append({"msg_meeting_id": j.get("msg_meeting_id"), "employee_no": j.get("employee_no"),
                          "works_meeting_id": j.get("works_meeting_id"),
                          "key_ok": (headers or {}).get("X-SSO-Service-Key") == KEY})
            k = PLAN.get(int(j.get("msg_meeting_id") or 0), "ok")
            if k == "conn":
                raise ConnectionError("이음 꺼짐(시험)")
            if k == "ok":
                DELETED.add(int(j["msg_meeting_id"]))
                return _R(200, {"ok": True})
            if k == "not_allowed":
                return _R(403, {"ok": False, "error": "not_allowed"})
            if k == "html404":
                return _R(404, None)
            return _R(500, {"ok": False})
        if url.endswith("/api/works/meetings"):
            return _R(200, {"ok": True, "items": [x for x in CARDS if x["id"] not in DELETED], "truncated": False})
        raise AssertionError("unexpected " + url)


SC.httpx = _FakeHttpx()


def fake_get_user(req):
    uid = req.cookies.get("tuser")
    with db_session() as c:
        r = (c.execute("SELECT * FROM users WHERE id=?", (int(uid),)).fetchone() if uid else
             c.execute("SELECT * FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone())
        return dict(r) if r else None


M.get_user = fake_get_user


@M.app.get("/__test/calls")
def _calls():
    return {"calls": CALLS, "deleted": sorted(DELETED)}


srv = uvicorn.Server(uvicorn.Config(M.app, host="127.0.0.1", port=PORT, log_level="warning", lifespan="on"))
th = threading.Thread(target=srv.run, daemon=True)
th.start()
for _ in range(300):
    if srv.started:
        break
    time.sleep(0.1)

KST = timezone(timedelta(hours=9))
Y = (datetime.now(KST) - timedelta(days=1)).strftime("%Y-%m-%d")
with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code"):
        if col not in have:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
    row = c.execute("SELECT id FROM teams WHERE name='총괄'").fetchone()
    tid = row[0] if row else c.execute("INSERT INTO teams(name, code) VALUES('총괄','TV1')").lastrowid
    ceo = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='대표이사', role='ceo', name='김정락', employee_no='T0001' WHERE id=?", (tid, ceo))

    def mk(name, login, emp, rank):
        return c.execute("INSERT INTO users(name, login_id, password, team_id, rank, role, is_active, employee_no) "
                         "VALUES(?,?,?,?,?,'member',1,?)", (name, login, "x", tid, rank, emp)).lastrowid
    owner = mk("안지연", "T0086", "T0086", "프로")
    org = mk("이한중", "T0002", "T0002", "매니저")
    other = mk("박주창", "T0003", "T0003", "프로")
    c.execute("DELETE FROM meetings")

    def mtg(key, own, msg=None, organizer=None, summary="", rec=None):
        mid = c.execute(
            "INSERT INTO meetings(title, meeting_date, mode, team_id, owner_id, location, tags, attendees_text, body, "
            "summary, audio_path, visibility, status, msg_meeting_id, msg_organizer_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"[시험] {key}", Y, "A", tid, own, "", "", "김정락, 안지연", "", summary, "", "all", "draft", msg, organizer)).lastrowid
        if rec:
            c.execute("UPDATE meetings SET rec_state='recording', rec_json=? WHERE id=?",
                      (json.dumps({"part": "", "session": "1", "seq": 3, "bytes": 3000, "secs": 30, "by": rec, "by_name": "",
                                   "started_at": "", "last_at": "", "pending": []}), mid))
        return mid

    ids = {
        "D1": mtg("D1 WORKS 에서만", owner),
        "D2": mtg("D2 이음 지움(대표)", owner, 9401, org),
        "D3": mtg("D3 이음 거절", owner, 9402, org),
        "D4": mtg("D4 이음 입구 없음", owner, 9403, owner),
        "D5": mtg("D5 이음 꺼짐", owner, 9404, owner),
        "D6": mtg("D6 권한", owner, 9405, org),
        "D7": mtg("D7 모아보기 바로 빠짐", owner, 9406, org),
        "R1": mtg("R1 녹음 중·본인", owner, 9501, org, rec=owner),
        "R2": mtg("R2 정리 끝+녹음 중·본인", owner, 9502, org, summary="핵심: 끝", rec=owner),
        "R3": mtg("R3 정리 끝", owner, 9503, org, summary="핵심: 끝"),
        "R5": mtg("R5 대표가 녹음 중", owner, 9505, org, rec=ceo),
    }


def card(i, title):
    return {"id": i, "title": title, "start_at": Y + "T10:00", "tz_offset": 9, "tz_label": "한국", "duration_min": 60,
            "location": "1층 소회의실", "visibility": "all", "organizer": {"name": "등록"},
            "attendees": [{"name": "김정락", "response": "attending", "is_organizer": False}], "externals": [],
            "me": {"is_organizer": False, "is_attendee": True, "response": "attending"}}


CARDS[:] = [card(9401, "C-D2"), card(9406, "C-D7"), card(9501, "C-R1 녹음 중·본인"), card(9502, "C-R2 정리 끝+녹음 중·본인"),
            card(9503, "C-R3 정리 끝"), card(9504, "C-R4 회의록 없음"), card(9505, "C-R5 대표가 녹음 중")]

io.open(os.path.join(HERE, "seed_del.json"), "w", encoding="utf-8").write(json.dumps(
    {"ids": ids, "ceo": ceo, "owner": owner, "org": org, "other": other, "port": PORT}, ensure_ascii=False))
print("READY", PORT, ids, flush=True)
th.join()
