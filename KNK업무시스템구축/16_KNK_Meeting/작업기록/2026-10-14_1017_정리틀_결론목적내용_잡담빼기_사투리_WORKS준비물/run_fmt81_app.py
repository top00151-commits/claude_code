# -*- coding: utf-8 -*-
"""z1181 시험용 WORKS 서버 — 정리 틀 「결론 → 목적 → (회의) 내용」 · 잡담 빼기 · 사투리는 표준어로.
사용: py run_fmt81_app.py <앱폴더(절대경로)> <포트>

🔵 AI 는 **맨 끝 한 함수(`ai_client.ai_chat`)만** 가짜다 — 회의록·음성 메모 정리 함수(`ai_extract_meeting`·
   `ai_extract_note`)는 **진짜**가 돈다. 그래서 서버가 AI 에 **실제로 보내는 지시문**을 붙잡아 볼 수 있다
   (`/__test/ai_calls`). 가짜는 새 틀 모양의 답을 돌려준다(화면·양식이 새 머리말을 어떻게 그리나 보려고).
   🔴 이 답은 「AI 가 잘 정리하나」를 증명하지 않는다 — 그건 올린 뒤 실제 회의 「🔄 다시 정리」로 본다(z1176 과 같은 방식).

세우는 것 — 나(김한국) 한 사람
  · M1 「삼성 2호기 납기 협의」 — 원문에 잡담·사투리 섞임 · 정리 전 → 「다시 정리」 시험
  · M2 새 틀로 이미 정리된 회의(AI 안 부르고 양식만 비교)
  · MO 옛 틀(「핵심:」)로 정리된 회의 — 옛 회의록이 예전 그대로 그려지나
  · N1 음성 메모(원문만)
⛔ 진짜 AI 를 부르지 않는다 · 진짜 로그인 대신 쿠키 tuser=<사람 id>.
"""
import io
import json
import os
import shutil
import sys
import threading
import time
from datetime import datetime

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
from app import ai_client              # noqa: E402
from app.database import db_session    # noqa: E402
from starlette.responses import PlainTextResponse as _PTR_no_sw   # noqa: E402
from starlette.responses import JSONResponse as _JR               # noqa: E402

for _r in [r for r in M.app.router.routes if getattr(r, 'path', '') == '/sw.js']:
    M.app.router.routes.remove(_r)


@M.app.get('/sw.js')
async def _sw_noop_for_test():
    return _PTR_no_sw('/* 시험용 빈 서비스워커 — 아무 일도 하지 않는다 */',
                      media_type='application/javascript')


MTG_SUM = ("결론\n- 삼성 A라인 검사기 2호기 납기를 2026-11-20 으로 확정\n"
           "목적\n- 2호기 납기·셋업 일정 협의\n"
           "회의 내용\n[납기]\n- 11월 20일 출하, 11월 25일 셋업 시작 (합의)\n"
           "[사양]\n- 카메라 2대 추가 요청 — 김한국 검토 (우려)")
NOTE_SUM = ("결론\n- 현대모비스 납기 11월 둘째 주로 확정\n"
            "목적\n- 고객 통화 내용 기록\n"
            "내용\n- 담당자와 통화 · 납기 확인\n"
            "할 일\n- 출하 일정표 갱신 — 김한국 · 11-10까지")
CALLS = []


def fake_chat(user_text, system="", **kw):
    """맨 끝 한 함수만 가짜 — 받은 지시문을 적어 두고 새 틀 모양의 답을 돌려준다."""
    CALLS.append({"system": system, "len": len(user_text or ""), "max_tokens": kw.get("max_tokens")})
    time.sleep(0.5)
    if "혼자 말한 녹음" in system:
        return (True, json.dumps({"title": "", "summary": NOTE_SUM}, ensure_ascii=False))
    return (True, json.dumps({"title": "", "summary": MTG_SUM,
                              "decisions": [{"who": "김한국", "what": "2호기 납기 11-20 확정", "due": "2026-11-20"}],
                              "actions": [{"assignee": "김한국", "task": "카메라 2대 추가 검토", "due": "2026-10-20"}]},
                             ensure_ascii=False))


ai_client.ai_available = lambda: True
ai_client.ai_chat = fake_chat


@M.app.get('/__test/ai_calls')
async def _test_ai_calls():
    return _JR({"calls": CALLS})


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

TODAY = datetime.now().strftime("%Y-%m-%d")
with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code", "lang"):
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s TEXT" % col)
    ta = c.execute("INSERT INTO teams(name, code, display_order) VALUES('기술영업팀','TCA',1)").lastrowid
    me = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='과장', role='member', name='김한국', lang='ko', employee_no='901' "
              "WHERE id=?", (ta, me))

    def mtg(title, body, summary=""):
        return c.execute(
            "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, attendees_text, body, summary, status) "
            "VALUES(?,?,?,?,'team','김한국, 최민수',?,?,'draft')", (title, TODAY, me, ta, body, summary)).lastrowid
    S = {}
    S["M1"] = mtg("삼성 2호기 납기 협의",
                  "안녕하세요 다들 점심은 드셨어요? 오늘 날씨 억수로 덥네예. "
                  "자 그럼 본론으로 — 삼성 A라인 2호기 납기는 11월 20일로 가입시더. 셋업은 25일부터. "
                  "카메라 2대 추가 요청이 왔는데 김한국 과장이 검토해 주이소. 주말에 등산 가실 분?")
    S["M2"] = mtg("새 틀 회의", "원문", MTG_SUM)
    S["MO"] = mtg("옛 틀 회의", "원문", "핵심: 11월 납기 확정\n\n[납기]\n- 11월 20일 출하 (합의)")
    N = {}
    N["N1"] = c.execute("INSERT INTO voice_notes(owner_id, title, body, summary) VALUES(?,?,?,?)",
                        (me, "거래처 통화", "현대모비스 담당자랑 통화했심더. 납기는 11월 둘째 주로 정했고예. "
                                            "아 그리고 어제 야구 봤어요? 출하 일정표는 다음 달 10일까지 고쳐 놓을게요.", "")).lastrowid

seed = {"me": me, "port": PORT, "ids": S, "notes": N, "mtg_sum": MTG_SUM, "note_sum": NOTE_SUM}
io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(json.dumps(seed, ensure_ascii=False))
print("READY", PORT, json.dumps({"me": me, "ids": S, "notes": N}, ensure_ascii=False), flush=True)
th.join()
