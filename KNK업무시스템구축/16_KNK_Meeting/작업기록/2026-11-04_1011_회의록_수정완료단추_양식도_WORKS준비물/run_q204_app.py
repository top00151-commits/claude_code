# -*- coding: utf-8 -*-
"""z1204 시험용 WORKS 서버 — z1202 시험 서버 그대로(「✏ 고치기」 → 「✔ 수정 완료」 · 회의록 양식도 시험용)
대표 2026-11-03 「고치기를 누르면 이 형태가 깨지기 때문에 내가 본 화면이 어디 있는지 찾기가 너무 어려워」
               「여기서 수정한 단어 … 회의 내용 원본에도 틀린 내용이 자동으로 수정이 될 수 있게」
사용: py run_q202_app.py <앱폴더(절대경로)> <포트>
AI 키 비움 · 진짜 로그인 대신 쿠키 tuser · 이음 주소는 닫힌 포트 · 🔒 시험 글은 모두 지어낸 것.
사람: 대표(ceo · 작성자) · 직원(member · 같은 팀 · 참석자 아님 = 보기만) · 참석 직원(member · 참석자 = 고치기 가능)
회의 M1 정리·결정·할 일 있음 · M2 정리 없음
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
os.environ["KNK_SSO_SERVICE_KEY"] = "q202-test-key"      # 시험용 값(운영 키 아님)
for _k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "KNK_OPENAI_API_KEY"):
    os.environ[_k] = ""
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
for _d in ("data", "meeting_audio", "voice_notes"):
    shutil.rmtree(os.path.join(APP, _d), ignore_errors=True)

import uvicorn                         # noqa: E402
from app import main as M              # noqa: E402
from app.database import db_session    # noqa: E402
from starlette.responses import PlainTextResponse as _PTR   # noqa: E402

for _r in [r for r in M.app.router.routes if getattr(r, 'path', '') == '/sw.js']:
    M.app.router.routes.remove(_r)


@M.app.get('/sw.js')
async def _sw_noop_for_test():
    return _PTR('/* 시험용 빈 서비스워커 */', media_type='application/javascript')


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

#  지어낸 정리 — 소제목 · 목록 · 들여쓴 목록 · 굵게 · [결정] · 번호 · 빈 줄이 다 있다
SUMM = "\n".join([
    "## 핵심",
    "포장 설비의 부품 입고 지연과 출하 차수 변경으로 일정이 흔들린 원인을 점검했다. 현재 26대분은 6대 출하 후 10대분 검사 예정이다.",
    "",
    "## 자재 지연과 일정 변동",
    "- 이번 일정 지연의 가장 큰 원인은 지급품 입고 지연이었다.",
    "  - 장납기 부품은 **확정 입고 일정**이 공유되지 않았다.",
    "- 감 팀장이 업체에 입고 일정을 다시 확인하기로 했다.",
    "- [결정] 자재 시트에 **입고 예정일과 실제 입고일을 분리**해 기록한다.",
    "1. 매주 목요일 오전 10시에 자재 회의를 연다.",
    "",
    "## 기타",
    "- 다음 회의는 팀장 참석으로 진행한다.",
])
BODY = ("지어낸 받아쓴 원문입니다. 감 팀장이 업체에 확인한다고 했습니다. 26대분은 6대 먼저 나가고 126대분은 내년입니다. "
        "감 팀장님 말로는 지급품이 늦었다고 합니다. 감자 이야기는 아닙니다. 다시 감 팀장에게 묻기로 했습니다.")
with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code", "lang"):
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s TEXT" % col)
    tcols = {r[1] for r in c.execute("PRAGMA table_info(teams)")}
    if "entity" not in tcols:
        c.execute("ALTER TABLE teams ADD COLUMN entity TEXT")
    ta = c.execute("INSERT INTO teams(name, code, display_order, entity) VALUES('총괄','00',0,'KOR')").lastrowid
    me = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='대표이사', role='ceo', name='김대표', lang='ko', employee_no='1' WHERE id=?", (ta, me))

    def person(login, name, rank, role, no):
        return c.execute("INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang, employee_no) "
                         "VALUES(?,?,?,?,?,1,'x-no-login-z1202',?, ?)", (login, name, rank, role, ta, "ko", no)).lastrowid
    mem = person("zq202m", "김직원", "프로", "member", "904")       # 같은 팀 · 참석자 아님 = 보기만
    att = person("zq202a", "박참석", "프로", "member", "905")       # 참석자 = 고칠 수 있다
    kang = person("zq202k", "강팀장", "팀장", "member", "906")      # 할 일 담당 이름 연결 시험

    def meeting(title, summ, body):
        mid = c.execute("INSERT INTO meetings(title, meeting_date, owner_id, team_id, location, body, summary, visibility, status, "
                        "attendees_text, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                        (title, "2026-11-03", me, ta, "지어낸 회의실", body, summ, "team", "done", "박참석",
                         "2026-11-03 10:00:00", "2026-11-03 10:00:00")).lastrowid
        M._meeting_link_attendees(c, mid, "박참석")
        return mid
    V = {"M1": meeting("자재 입고 점검 회의(지어낸 글)", SUMM, BODY), "M2": meeting("정리 없는 회의", "", "원문만 있다")}
    V["D1"] = c.execute("INSERT INTO meeting_decisions(meeting_id, who, what, due, source) VALUES(?,?,?,?,'ai')",
                        (V["M1"], "감 팀장", "감 팀장이 입고 일정표를 매주 공유한다", "")).lastrowid
    V["D2"] = c.execute("INSERT INTO meeting_decisions(meeting_id, who, what, due, source) VALUES(?,?,?,?,'ai')",
                        (V["M1"], "", "자재 시트에 지급품 구분을 적는다", "2026-11-20")).lastrowid
    V["A1"] = c.execute("INSERT INTO meeting_actions(meeting_id, assignee_name, task, due_date, source) VALUES(?,?,?,?,'ai')",
                        (V["M1"], "감팀장", "업체 입고 일정 다시 확인", "")).lastrowid
seed = {"me": me, "mem": mem, "att": att, "kang": kang, "port": PORT, "ids": V, "body": BODY, "summary": SUMM}
io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(json.dumps(seed, ensure_ascii=False))
print("READY", PORT, json.dumps({"me": me, "ids": V}, ensure_ascii=False), flush=True)
th.join()
