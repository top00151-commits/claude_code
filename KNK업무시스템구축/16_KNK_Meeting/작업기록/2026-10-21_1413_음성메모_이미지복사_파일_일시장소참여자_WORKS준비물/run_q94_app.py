# -*- coding: utf-8 -*-
"""z1194 시험용 WORKS 서버 — 음성 메모 🖼 이미지 · 📝 파일(.md) · 일시·장소·참여자.
대표 2026-10-21 「음성메모 정리된걸 … 이미지로 복사해서 붙여 넣을수있게」 · 「정리할때 대화참여자,장소,시간도 기록할수있으면」
사용: py run_q94_app.py <앱폴더(절대경로)> <포트>

AI 는 부르지 않는다(가짜도 안 씀 · 키 비움) · 진짜 로그인 대신 쿠키 tuser · 이음 주소는 닫힌 포트 · 🔒 시험 글은 모두 지어낸 것.
메모(김한국 901 것)
  N1 긴 정리 + 일시·장소·참여자(새것만 · 운영엔 칸 없음)   N2 짧은 정리(세 칸 비움)   N3 정리 전
  N4 꺾쇠 글(제목·정리·세 칸에 <b>·<img onerror>) — 그림·파일·복사가 글자로만 다루나
  N5 녹음 올리기 시험(세 칸 비움)   N6 녹음 올리기 시험(일시를 사람이 먼저 적음)
  NV 베트남법인 직원(Nguyen Van A 903) 메모 — 녹음 올리기 일시가 +7 로   NO 남(박다른 905)의 메모
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
os.environ["KNK_SSO_SERVICE_KEY"] = "q94-test-key"      # 시험용 값(운영 키 아님)
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

for _r in [r for r in M.app.router.routes if getattr(r, 'path', '') == '/sw.js']:
    M.app.router.routes.remove(_r)


@M.app.get('/sw.js')
async def _sw_noop_for_test():
    return _PTR('/* 시험용 빈 서비스워커 */', media_type='application/javascript')


CALLS = []
ai_client.ai_available = lambda: False


def _no_ai(*a, **k):
    CALLS.append(1)
    return (False, "시험 서버 — AI 안 부름")


ai_client.ai_chat = _no_ai


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

#  ── 지어낸 정리 글 ──
SEC = []
for i in range(1, 9):
    SEC.append("## 시험 주제 %d\n" % i
               + "\n".join("- 지어낸 문장 %d-%d — 출하 일정은 **11월 %d일**로 정리했고 포장은 그 전날까지 마친다는 내용이다." % (i, j, 10 + j)
                           for j in range(1, 6)))
LONG = ("## 핵심\n지어낸 긴 메모입니다. 거래처 방문 결과와 남은 확인 사항을 정리했다(시험 글).\n\n"
        + "\n\n".join(SEC)
        + "\n\n## 할 일\n- **견적서 보내기** — 김한국 · 2026-10-24\n- [확인 필요] 셋업 시작일 — 고객사 확인")
SHORT = "## 핵심\n지어낸 짧은 정리입니다.\n\n## 할 일\n- **자료 보내기** — 김한국 · 2026-10-22"
XSS = "## 핵심\n꺾쇠 <b>굵게</b> <img src=x onerror=alert(1)> 글자로만 보여야 한다.\n\n- [결정] 시험 <script>alert(2)</script>"

with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code", "lang"):
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s TEXT" % col)
    tcols = {r[1] for r in c.execute("PRAGMA table_info(teams)")}
    if "entity" not in tcols:
        c.execute("ALTER TABLE teams ADD COLUMN entity TEXT")
    ta = c.execute("INSERT INTO teams(name, code, display_order, entity) VALUES('기술영업팀','TCA',1,'KOR')").lastrowid
    tv = c.execute("INSERT INTO teams(name, code, display_order, entity) VALUES('베트남관리팀','TCV',2,'VN')").lastrowid
    me = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='과장', role='member', name='김한국', lang='ko', employee_no='901' WHERE id=?", (ta, me))
    other = c.execute("INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang, employee_no) "
                      "VALUES('zq94x','박다른','프로','member',?,1,'x-no-login-z1194','ko','905')", (ta,)).lastrowid
    vnu = c.execute("INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang, employee_no) "
                    "VALUES('zq94vn','Nguyen Van A','프로','member',?,1,'x-no-login-z1194','vi','903')", (tv,)).lastrowid
    vcols = {r[1] for r in c.execute("PRAGMA table_info(voice_notes)")}
    META = "meta_when" in vcols

    def note(owner, title, summary, when="", place="", people="", created="2026-10-21 12:38:26"):
        nid = c.execute("INSERT INTO voice_notes(owner_id, title, body, summary, audio_path, created_at, updated_at) "
                        "VALUES(?,?,?,?,?,?,?)", (owner, title, "(시험 원문)" if summary else "", summary, "", created, created)).lastrowid
        if META and (when or place or people):
            c.execute("UPDATE voice_notes SET meta_when=?, meta_place=?, meta_people=? WHERE id=?", (when, place, people, nid))
        return nid
    S = {}
    S["N1"] = note(me, "거래처 방문 정리(지어낸 글)", LONG, "2026-10-21 (화) 11:00 ~ 12:00 (60분)", "고객사 2층 회의실", "김한국 과장, 박다른 프로, 고객사 담당자")
    S["N2"] = note(me, "짧은 메모(지어낸 글)", SHORT, created="2026-10-21 15:00:00")
    S["N3"] = note(me, "정리 전 메모", "")
    S["N4"] = note(me, "꺾쇠 <b>제목</b>", XSS, "<b>일시</b>", "<img src=x onerror=alert(3)>", "A & B \"따옴\" 'x'")
    S["N5"] = note(me, "녹음 올리기 시험", "")
    S["N6"] = note(me, "녹음 올리기 시험(일시 먼저)", "", "사람이 적은 일시")
    S["NV"] = note(vnu, "VN 메모", "")
    S["NO"] = note(other, "남의 메모", SHORT)

seed = {"me": me, "other": other, "vnu": vnu, "port": PORT, "ids": S, "long": LONG, "short": SHORT, "xss": XSS, "has_meta": META}
io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(json.dumps(seed, ensure_ascii=False))
print("READY", PORT, json.dumps({"me": me, "ids": S, "has_meta": META}, ensure_ascii=False), flush=True)
th.join()
