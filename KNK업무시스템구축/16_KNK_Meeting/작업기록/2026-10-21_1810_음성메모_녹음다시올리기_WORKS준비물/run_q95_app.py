# -*- coding: utf-8 -*-
"""z1195 시험용 WORKS 서버 — 음성 메모 「📁 녹음 다시 올리기」.
대표 2026-10-21 「음성메모 녹음파일을 한번 잘 못 올리면 수정할 방법이 없어... 파일 다시 올리기 기능이 필요해」 → 「이대로 만들기」
사용: py run_q95_app.py <앱폴더(절대경로)> <포트>

가짜 = 받아쓰기 맨 끝 `main._stt_one`(녹음 파일 크기로 지은 글 · 크기가 SLOW 면 6초 걸림) · 정리 `ai_client.ai_extract_note`(원문 앞부분으로 지은 정리) ·
진짜 로그인 대신 쿠키 tuser · 이음 주소는 닫힌 포트 · AI 키 비움 · 🔒 시험 글은 모두 지어낸 것.
메모(김한국 901 것 · 모두 받아쓴 원문·정리·녹음 파일 있음 — R3 만 빈 메모)
  R1 자동 일시(meta_when = meta_when_auto) · 브라우저로 다시 올리기     R2 사람이 고친 일시(meta_when ≠ meta_when_auto)
  R3 빈 메모(처음 올리기 길 · 덧붙이기 그대로인지)                       R4 사람이 고친 정리(다시 정리 전에 묻는다)
  R5 자동 일시 + 파일 시각 없이 다시 올리기(일시 비움)                    R6 받아쓰기 도는 중엔 다시 올리기 막기
  R7 다시 올리기 확인 창에서 「취소」                                      RO 남(박다른 905)의 메모
"""
import io
import json
import os
import shutil
import subprocess
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
os.environ["KNK_SSO_SERVICE_KEY"] = "q95-test-key"      # 시험용 값(운영 키 아님)
for _k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "KNK_OPENAI_API_KEY"):
    os.environ[_k] = ""
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
for _d in ("data", "meeting_audio", "voice_notes"):
    shutil.rmtree(os.path.join(APP, _d), ignore_errors=True)

import uvicorn                         # noqa: E402
from app import main as M              # noqa: E402
from app import ai_client              # noqa: E402
from app.database import db_session    # noqa: E402
from starlette.responses import PlainTextResponse as _PTR   # noqa: E402
from starlette.responses import JSONResponse as _JR         # noqa: E402

for _r in [r for r in M.app.router.routes if getattr(r, 'path', '') == '/sw.js']:
    M.app.router.routes.remove(_r)


@M.app.get('/sw.js')
async def _sw_noop_for_test():
    return _PTR('/* 시험용 빈 서비스워커 */', media_type='application/javascript')


SLOW_BYTES = {"n": -1}
STT_CALLS = []
SUM_CALLS = []


def fake_stt(mid, disk, lang, hint, progress=None):
    n = os.path.getsize(disk)
    STT_CALLS.append({"bytes": n, "lang": lang})
    if n == SLOW_BYTES["n"]:
        time.sleep(6)
    time.sleep(0.3)
    return ("새 녹음 받아쓴 글 — %d바이트 · 말 %s" % (n, lang or "자동"), "", "")


def fake_note(body, context=""):
    SUM_CALLS.append(len(body or ""))
    time.sleep(0.3)
    return (True, {"title": "지어낸 제목", "summary": "## 핵심\n정리: " + (body or "")[:40]})


M._stt_one = fake_stt
ai_client.ai_available = lambda: True
ai_client.transcribe_available = lambda: True
ai_client.ai_extract_note = fake_note
ai_client.ai_chat = lambda *a, **k: (False, "시험 서버 — AI 안 부름")


@M.app.get('/__test/calls')
async def _test_calls():
    return _JR({"stt": STT_CALLS, "sum": SUM_CALLS})


@M.app.post('/__test/slow/{n:int}')
async def _test_slow(n: int):
    SLOW_BYTES["n"] = n
    return _JR({"ok": True})


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


def wav(path, secs):
    subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "sine=frequency=330:sample_rate=8000:duration=%s" % secs, "-ac", "1", path], check=True)


AUTO_OLD = "2026-10-20 (화) 09:00 ~ 09:30 (30분)"
OLD_SUM = "## 핵심\n옛 정리(잘못 올린 녹음으로 만든 지어낸 정리)"
with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code", "lang"):
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s TEXT" % col)
    tcols = {r[1] for r in c.execute("PRAGMA table_info(teams)")}
    if "entity" not in tcols:
        c.execute("ALTER TABLE teams ADD COLUMN entity TEXT")
    ta = c.execute("INSERT INTO teams(name, code, display_order, entity) VALUES('기술영업팀','TCA',1,'KOR')").lastrowid
    me = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='과장', role='member', name='김한국', lang='ko', employee_no='901' WHERE id=?", (ta, me))
    other = c.execute("INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang, employee_no) "
                      "VALUES('zq95x','박다른','프로','member',?,1,'x-no-login-z1195','ko','905')", (ta,)).lastrowid
    vcols = {r[1] for r in c.execute("PRAGMA table_info(voice_notes)")}
    HAS_AUTO = "meta_when_auto" in vcols

    def note(owner, title, body, summary, when="", auto="", edited=""):
        nid = c.execute("INSERT INTO voice_notes(owner_id, title, body, summary, audio_path, created_at, updated_at) "
                        "VALUES(?,?,?,?,?,?,?)", (owner, title, body, summary, "", "2026-10-21 12:38:26", "2026-10-21 12:38:26")).lastrowid
        if body:
            d = os.path.join(M._VN_DIR, "note_%d" % nid)
            os.makedirs(d, exist_ok=True)
            p = os.path.join(d, "rec_1000.wav")
            wav(p, 3)
            c.execute("UPDATE voice_notes SET audio_path=? WHERE id=?", (p.replace("\\", "/"), nid))
        if when and "meta_when" in vcols:
            c.execute("UPDATE voice_notes SET meta_when=? WHERE id=?", (when, nid))
        if auto and HAS_AUTO:
            c.execute("UPDATE voice_notes SET meta_when_auto=? WHERE id=?", (auto, nid))
        if edited:
            c.execute("UPDATE voice_notes SET summary_edited_at=? WHERE id=?", (edited, nid))
        return nid
    OLD_BODY = "옛 원문 — 잘못 올린 녹음을 받아쓴 지어낸 글입니다."
    S = {}
    S["R1"] = note(me, "다시 올리기 시험 1(지어낸 글)", OLD_BODY, OLD_SUM, AUTO_OLD, AUTO_OLD)
    S["R2"] = note(me, "사람이 고친 일시", OLD_BODY, OLD_SUM, "사람이 적은 일시", AUTO_OLD)
    S["R3"] = note(me, "빈 메모", "", "")
    S["R4"] = note(me, "사람이 고친 정리", OLD_BODY, "## 핵심\n사람이 고친 정리(지어낸 글)", AUTO_OLD, AUTO_OLD, "2026-10-21 13:00:00")
    S["R5"] = note(me, "파일 시각 없이", OLD_BODY, OLD_SUM, AUTO_OLD, AUTO_OLD)
    S["R6"] = note(me, "받아쓰기 도는 중", OLD_BODY, OLD_SUM)
    S["R7"] = note(me, "확인 창 취소", OLD_BODY, OLD_SUM, AUTO_OLD, AUTO_OLD)
    S["RO"] = note(other, "남의 메모", OLD_BODY, OLD_SUM)

seed = {"me": me, "other": other, "port": PORT, "ids": S, "auto_old": AUTO_OLD, "old_sum": OLD_SUM, "old_body": OLD_BODY,
        "has_auto": HAS_AUTO, "vn_dir": os.path.abspath(M._VN_DIR)}
io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(json.dumps(seed, ensure_ascii=False))
print("READY", PORT, json.dumps({"me": me, "ids": S, "has_auto": HAS_AUTO}, ensure_ascii=False), flush=True)
th.join()
