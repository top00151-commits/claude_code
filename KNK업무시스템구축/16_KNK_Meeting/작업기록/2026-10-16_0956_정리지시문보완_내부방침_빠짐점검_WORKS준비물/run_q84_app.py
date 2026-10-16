# -*- coding: utf-8 -*-
"""z1184 시험용 WORKS 서버 — z1183 의 run_q83_app.py 를 그대로 옮겨 왔다(가짜는 맨 끝 ai_chat 하나 · 받은 지시문을 적어 둔다).
  z1184 = 정리 지시문 보완 5가지 + [이번 회의 정보] 요일 + 음성 메모 [메모 정보] — q84_check.py 가 실제로 보내는 지시문을 본다.
(아래는 z1183 머리말)
z1183 시험용 WORKS 서버 — 회의록·음성메모 정리 품질 기준(대표 2026-10-15) · 마크다운 정리 · 고친 정리 확인 + 이전 정리 보관.
사용: py run_q84_app.py <앱폴더(절대경로)> <포트>

🔵 AI 는 **맨 끝 한 함수(`ai_client.ai_chat`)만** 가짜다 — 정리 함수(`ai_extract_meeting`·`ai_extract_note`)는 **진짜**가 돈다.
   그래서 서버가 AI 에 **실제로 보내는 지시문**을 붙잡아 볼 수 있다(`/__test/ai_calls`).
   가짜 답은 새 기준 모양(## 핵심 → ## 주제 · 목록 · **굵게** · [결정]/[미결]/[제안])이고, **부를 때마다 번호가 바뀐다**
   (「가짜 정리 1」 → 「가짜 정리 2」) — 다시 정리·이전 정리 맞바꾸기를 글자로 가려 보려고.
   🔴 이 답은 「AI 가 기준대로 잘 정리하나」를 증명하지 않는다 — 그건 올린 뒤 실제 회의 「🔄 다시 정리」로 본다(z1176 과 같은 방식).
   음성→글자도 가짜(「[가짜 변환] …」) — 녹음을 올리면 자동 정리까지 가는 길을 시험하려고.

세우는 것
  사람: 나(김한국 · ko · 작성자) · 박성수(보기만 · ko) · Nguyen Van A(vi · 자기 회의 작성자)
  회의: MQ 「삼성 2호기 납기 협의」 = 옛 z1181 틀 정리(S0) + AI 결정·할 일 + 사람이 넣은 결정·할 일 + 일일카드로 보낸 할 일
        MN 새 마크다운 정리가 이미 있는 회의 · MO 옛 「핵심:」 정리 · M81 z1181 「결론·목적·회의 내용」 정리
        ME 녹음 없음 · 정리 있음 · (새것만) 「사람이 고친 표시」 — 녹음을 올리면 자동 정리가 먼저 묻나
        MV Nguyen 의 회의 · (새것만) 이전 정리 있음 · 고친 표시
  음성 메모: NQ 옛 틀 정리(S0) · NN 새 마크다운 정리
⛔ 진짜 AI 를 부르지 않는다(키 비움) · 진짜 로그인 대신 쿠키 tuser=<사람 id>.
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
for _d in ("data", "meeting_audio", "voice_notes"):
    shutil.rmtree(os.path.join(APP, _d), ignore_errors=True)

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


#  새 기준 모양의 가짜 답 — %d 자리에 부른 번호가 들어간다
MTG_SUM = ("## 핵심\n삼성 A라인 2호기 출하일을 **2026-11-20**으로 정했다(가짜 정리 %d). "
           "셋업 시작일은 고객사 확인이 남았다.\n\n"
           "## 납기·셋업\n- [결정] 출하 **11월 20일**\n- [미결] 셋업 시작일 — 고객사 확인 필요\n  - 25일 시작 제안(김한국)\n\n"
           "## 사양\n1. 카메라 2대 추가 요청 — 납기 영향 (우려)\n2. [제안] 조명 교체")
NOTE_SUM = ("## 핵심\n현대모비스 납기를 **11월 둘째 주**로 정했다(가짜 메모 %d).\n\n"
            "## 통화 내용\n- 담당자와 통화 · 납기 확인\n\n## 할 일\n- **출하 일정표 갱신** — 김한국 · 11-10까지")
CALLS = []
CNT = {"m": 0, "n": 0}


def fake_chat(user_text, system="", **kw):
    """맨 끝 한 함수만 가짜 — 받은 지시문을 적어 두고 새 기준 모양의 답을 돌려준다(부를 때마다 번호가 바뀐다)."""
    CALLS.append({"system": system, "len": len(user_text or ""), "max_tokens": kw.get("max_tokens")})
    time.sleep(0.4)
    if "혼자 말한 녹음" in system:
        CNT["n"] += 1
        return (True, json.dumps({"title": "", "summary": NOTE_SUM % CNT["n"]}, ensure_ascii=False))
    CNT["m"] += 1
    k = CNT["m"]
    return (True, json.dumps({"title": "", "summary": MTG_SUM % k,
                              "decisions": [{"who": "김한국", "what": "2호기 출하일 11-20 확정 (가짜 결정 %d)" % k,
                                             "due": "2026-11-20"}],
                              "actions": [{"assignee": "김한국",
                                           "task": "카메라 2대 추가 시 납기 영향을 확인해 영업팀에 공유 (가짜 할 일 %d)" % k,
                                           "due": ""}]}, ensure_ascii=False))


ai_client.ai_available = lambda: True
ai_client.ai_chat = fake_chat
ai_client.transcribe_available = lambda: True
ai_client.ai_transcribe = lambda path, lang="": (True, "[가짜 변환] 셋업 일정을 다시 이야기했습니다")


@M.app.get('/__test/ai_calls')
async def _test_ai_calls():
    return _JR({"calls": CALLS, "cnt": CNT})


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
S0 = ("결론\n- 2호기 납기 11-20 확정\n목적\n- 2호기 납기·셋업 일정 협의\n회의 내용\n[납기]\n- 11월 20일 출하 (합의)")
NOTE_S0 = "결론\n- 현대모비스 납기 확인\n목적\n- 고객 통화 기록\n내용\n- 담당자와 통화"
MN_SUM = ("## 핵심\n2호기 출하일을 **11월 20일**로 정했고, 셋업 시작일은 고객사 확인이 남았다.\n\n"
          "## 납기\n- [결정] 출하 **11월 20일**\n  - 포장은 전날까지\n- [확인 필요] 셋업 25일 vs 27일 — 발언이 엇갈림\n\n"
          "## 사양\n1. 카메라 2대 추가 — (내부 방침) 고객 공유 전 원가 확인\n2. [제안] 조명 교체")
with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code", "lang"):
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s TEXT" % col)
    NEWCOLS = {r[1] for r in c.execute("PRAGMA table_info(meetings)")} >= {"summary_prev", "summary_edited_at"}
    ta = c.execute("INSERT INTO teams(name, code, display_order) VALUES('기술영업팀','TCA',1)").lastrowid
    tb = c.execute("INSERT INTO teams(name, code, display_order) VALUES('라이프밸류팀','TCB',2)").lastrowid
    me = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='과장', role='member', name='김한국', lang='ko', employee_no='901' "
              "WHERE id=?", (ta, me))

    def person(login, name, team, lang, emp):
        return c.execute(
            "INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang, employee_no) "
            "VALUES(?,?,'프로','member',?,1,'x-no-login-z1183',?,?)", (login, name, team, lang, emp)).lastrowid
    viewer = person("zq83vw", "박성수", tb, "ko", "902")
    vnu = person("zq83vn", "Nguyen Van A", tb, "vi", "903")

    def mtg(title, body, summary="", owner=None, team=None):
        return c.execute(
            "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, attendees_text, body, summary, status) "
            "VALUES(?,?,?,?,'all','김한국, 최민수',?,?,'draft')",
            (title, TODAY, owner or me, team or ta, body, summary)).lastrowid
    S = {}
    S["MQ"] = mtg("삼성 2호기 납기 협의",
                  "안녕하세요 다들 점심은 드셨어요? 자 그럼 본론으로 — 삼성 A라인 2호기 납기는 11월 20일로 갑시다. "
                  "셋업은 25일부터 하자는 제안이 있었는데 고객사 확인이 필요합니다. 카메라 2대 추가 요청이 왔는데 "
                  "김한국 과장이 납기 영향을 확인해 주세요. 주말에 등산 가실 분?", S0)
    #  MQ 의 결정·할 일 — AI 가 만든 것(그때의 정리와 함께 보관 대상) · 사람이 넣은 것 · 일일카드로 보낸 것(그대로 남아야 한다)
    c.execute("INSERT INTO meeting_decisions(meeting_id, who, what, due, source) VALUES(?,?,?,?,'ai')",
              (S["MQ"], "김한국", "처음 AI 결정 (S0)", "2026-11-20"))
    c.execute("INSERT INTO meeting_actions(meeting_id, assignee_name, assignee_user_id, task, due_date, source) "
              "VALUES(?,?,?,?,?,'ai')", (S["MQ"], "김한국", me, "처음 AI 할 일 (S0)", ""))
    c.execute("INSERT INTO meeting_decisions(meeting_id, who, what, due, source) VALUES(?,?,?,?,'manual')",
              (S["MQ"], "최민수", "사람이 적은 결정", ""))
    c.execute("INSERT INTO meeting_actions(meeting_id, assignee_name, assignee_user_id, task, due_date, source) "
              "VALUES(?,?,?,?,?,'manual')", (S["MQ"], "최민수", None, "사람이 적은 할 일", ""))
    tk = c.execute("INSERT INTO tasks(user_id, work_date, title, category, status, notes) VALUES(?,?,?,?,?,?)",
                   (me, TODAY, "일일카드로 보낸 할 일", "고객대응", "진행중", "")).lastrowid
    c.execute("INSERT INTO meeting_actions(meeting_id, assignee_name, assignee_user_id, task, due_date, source, "
              "linked_task_id) VALUES(?,?,?,?,?,'ai',?)", (S["MQ"], "김한국", me, "일일카드로 보낸 AI 할 일", "", tk))
    S["MN"] = mtg("새 기준 정리 회의", "원문", MN_SUM)
    S["MO"] = mtg("옛 틀 회의", "원문", "핵심: 11월 납기 확정\n\n[납기]\n- 11월 20일 출하 (합의)")
    S["M81"] = mtg("z1181 틀 회의", "원문", "결론\n- 납기 11-20 확정\n목적\n- 일정 협의\n회의 내용\n[납기]\n- 11월 20일 출하 (합의)")
    S["ME"] = mtg("녹음 전 고친 정리 회의", "회의 전에 손으로 적은 메모입니다.", "## 핵심\n사람이 손으로 고친 정리입니다.")
    S["MV"] = mtg("Cuộc họp tiến độ", "Nội dung cuộc họp", "## 핵심\nBản tổng hợp hiện tại.", owner=vnu, team=tb)
    if NEWCOLS:   # 새것에만 칸이 있다 — 운영 그대로에는 이 표시가 없다(그래서 묻지 않는다)
        c.execute("UPDATE meetings SET summary_edited_at='2026-10-15 17:40' WHERE id=?", (S["ME"],))
        c.execute("UPDATE meetings SET summary_prev='## 핵심\nBản trước.', summary_prev_at='2026-10-15 09:00', "
                  "summary_edited_at='2026-10-15 10:00' WHERE id=?", (S["MV"],))
    N = {}
    N["NQ"] = c.execute("INSERT INTO voice_notes(owner_id, title, body, summary) VALUES(?,?,?,?)",
                        (me, "거래처 통화", "현대모비스 담당자랑 통화했습니다. 납기는 11월 둘째 주로 정했고요. "
                                            "아 그리고 어제 야구 봤어요? 출하 일정표는 다음 달 10일까지 고쳐 놓을게요.",
                         NOTE_S0)).lastrowid
    N["NN"] = c.execute("INSERT INTO voice_notes(owner_id, title, body, summary) VALUES(?,?,?,?)",
                        (me, "현장 메모", "원문", NOTE_SUM % 0)).lastrowid

seed = {"me": me, "viewer": viewer, "vnu": vnu, "port": PORT, "ids": S, "notes": N, "newcols": NEWCOLS,
        "s0": S0, "note_s0": NOTE_S0, "mn_sum": MN_SUM, "mtg_sum": MTG_SUM, "note_sum": NOTE_SUM}
io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(json.dumps(seed, ensure_ascii=False))
print("READY", PORT, json.dumps({"me": me, "ids": S, "notes": N, "newcols": NEWCOLS}, ensure_ascii=False), flush=True)
th.join()
