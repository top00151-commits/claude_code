# -*- coding: utf-8 -*-
"""z1185 시험용 WORKS 서버 — 「회의록 작성됨」일 때만 「📋 회의록 보기」·「📄 회의록」 켜기.
대표 2026-10-16 (세션 10 전달 · 사진): 「회의록이 녹음 원문 또는 수기 작성이 되지 않았을때는 회의록보기 아이콘은
비활성화가 되어야함.. 회의록보기 아이콘은 회의록이 작성되었을때만 활성화하는게 맞음.」
사용: py run_q85_app.py <앱폴더(절대경로)> <포트>

z1184 의 run_q84_app.py 와 같은 틀 — AI 는 **맨 끝 한 함수(`ai_client.ai_chat`)만** 가짜(부른 횟수를 `/__test/ai_calls` 로 본다) ·
음성→글자도 가짜(「[가짜 변환] …」) · 이음 서버 간 공유키는 **시험용 값**(이음이 부르는 `msg/status` 를 이 검사기가 대신 부른다).

세우는 것 (사람: 나 = 김한국 · ko · 사번 901 · 모든 회의의 작성자 / Nguyen Van A · vi · 보기만)
  이음 「▶ 회의 시작」으로 만든 회의록(이음 회의 id 701~709 · 원문 = 이음 회의 메모(씨앗))
    E1 메모만 · 엉터리 정리(운영 3건과 같은 꼴)      E2 메모만 · 정리 전
    E3 받아쓴 글 + 정리                              E4 메모만 · 사람이 직접 고친 정리
    E5 메모만 · 「↩ 이전 정리」로 맞바꾼 정리(고친 시각 = 보관 시각)
    E6 원문 빔                                       E7 메모만 · 녹음 올리기 시험
    E8 메모(줄바꿈 CRLF) · 줄바꿈만 다른 저장 시험   E9 메모만 · 엉터리 정리 + 이전 정리(맞바꾸기 → 사람이 고침 시험)
  이음웍스에서 직접 만든 회의록
    N1 손으로 쓴 원문 · 정리 전   N2 원문 빔   N3 손으로 쓴 원문 + 정리
⛔ 진짜 AI 를 부르지 않는다(키 비움) · 진짜 로그인 대신 쿠키 tuser=<사람 id> · 진짜 이음을 부르지 않는다(주소를 닫힌 포트로).
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
os.environ["KNK_SSO_SERVICE_KEY"] = "q85-test-key"      # 시험용 값(운영 키 아님) — msg/status 를 이 검사기가 부르려고
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


MTG_SUM = ("## 핵심\n출하일을 **2026-11-20**으로 정했다(가짜 정리 %d).\n\n"
           "## 납기\n- [결정] 출하 **11월 20일**\n- [미결] 셋업 시작일 — 고객사 확인 필요")
CALLS = []
CNT = {"m": 0, "n": 0}


def fake_chat(user_text, system="", **kw):
    """맨 끝 한 함수만 가짜 — 부른 것을 적어 두고 정리 모양의 답을 돌려준다(부를 때마다 번호가 바뀐다)."""
    CALLS.append({"len": len(user_text or ""), "head": (user_text or "")[:60]})
    time.sleep(0.4)
    CNT["m"] += 1
    k = CNT["m"]
    return (True, json.dumps({"title": "", "summary": MTG_SUM % k,
                              "decisions": [{"who": "김한국", "what": "출하일 11-20 확정 (가짜 결정 %d)" % k, "due": ""}],
                              "actions": []}, ensure_ascii=False))


ai_client.ai_available = lambda: True
ai_client.ai_chat = fake_chat
ai_client.transcribe_available = lambda: True
#  z1187: 받아쓴 글은 알아들을 말이 200자 이상이어야 「녹음 원문 있음」 → 실제 회의처럼 문장을 덧붙인다(앞머리 그대로)
ai_client.ai_transcribe = lambda path, lang="": (True, "[가짜 변환] 출하일은 11월 20일로 정했습니다. " + '오늘은 삼성 A라인 2호기 출하 일정과 셋업 순서를 함께 정리했습니다. 출하는 11월 20일로 하고 포장은 그 전날까지 마치기로 했습니다. 셋업은 25일부터 시작하는데 고객사 담당자의 확인을 먼저 받아야 합니다. 카메라 두 대를 추가해 달라는 요청은 납기에 영향이 있는지 기술팀이 이번 주 안에 확인하겠습니다. 조명 교체 제안은 원가를 먼저 계산해 보고 다음 회의에서 다시 이야기하기로 했습니다. 검사 프로그램은 지난번 오류가 난 부분을 고친 판으로 현장에서 한 번 더 돌려 보겠습니다. 부품 단가가 오른 것은 구매팀이 거래처와 다시 협의해 결과를 공유하기로 했습니다. 다음 회의는 다음 주 화요일 오전 열 시에 같은 장소에서 하겠습니다.')


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
SEED = "고객사 방문 — 검사기 컨셉 협의 (이음 회의 메모)"
JUNK = "## 핵심\n회의 내용이 제공되지 않아 안건만 적었다(엉터리 정리 1)"
JUNK2 = "## 핵심\n안건을 논의한 것처럼 다시 적었다(엉터리 정리 2)"
REAL = "## 핵심\n출하일을 11월 20일로 정했다(진짜 정리)"
HAND = "## 핵심\n사람이 직접 적은 회의 정리입니다"
with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code", "lang"):
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s TEXT" % col)
    MCOLS = {r[1] for r in c.execute("PRAGMA table_info(meetings)")}
    ta = c.execute("INSERT INTO teams(name, code, display_order) VALUES('기술영업팀','TCA',1)").lastrowid
    tb = c.execute("INSERT INTO teams(name, code, display_order) VALUES('라이프밸류팀','TCB',2)").lastrowid
    me = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='과장', role='member', name='김한국', lang='ko', employee_no='901' "
              "WHERE id=?", (ta, me))
    vnu = c.execute(
        "INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang, employee_no) "
        "VALUES('zq85vn','Nguyen Van A','프로','member',?,1,'x-no-login-z1185','vi','903')", (tb,)).lastrowid

    def mtg(title, body, summary="", msg_id=None, **extra):
        mid = c.execute(
            "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, attendees_text, body, summary, "
            "                     status, msg_meeting_id) VALUES(?,?,?,?,'all','김한국, 최민수',?,?,'draft',?)",
            (title, TODAY, me, ta, body, summary, msg_id)).lastrowid
        for k, v in extra.items():
            c.execute("UPDATE meetings SET %s=? WHERE id=?" % k, (v, mid))
        return mid
    S = {}
    S["E1"] = mtg("E1 이음 메모만 엉터리 정리", SEED, JUNK, 701)
    S["E2"] = mtg("E2 이음 메모만 정리 전", SEED, "", 702)
    S["E3"] = mtg("E3 이음 받아쓴 글", SEED + "\n\n🎤 [음성 변환]\n출하일은 11월 20일로 정했습니다. " + '오늘은 삼성 A라인 2호기 출하 일정과 셋업 순서를 함께 정리했습니다. 출하는 11월 20일로 하고 포장은 그 전날까지 마치기로 했습니다. 셋업은 25일부터 시작하는데 고객사 담당자의 확인을 먼저 받아야 합니다. 카메라 두 대를 추가해 달라는 요청은 납기에 영향이 있는지 기술팀이 이번 주 안에 확인하겠습니다. 조명 교체 제안은 원가를 먼저 계산해 보고 다음 회의에서 다시 이야기하기로 했습니다. 검사 프로그램은 지난번 오류가 난 부분을 고친 판으로 현장에서 한 번 더 돌려 보겠습니다. 부품 단가가 오른 것은 구매팀이 거래처와 다시 협의해 결과를 공유하기로 했습니다. 다음 회의는 다음 주 화요일 오전 열 시에 같은 장소에서 하겠습니다.', REAL, 703)   # z1187: 여러 문장
    S["E4"] = mtg("E4 이음 사람이 고친 정리", SEED, HAND, 704, summary_edited_at="2026-10-16 14:00:00")
    S["E5"] = mtg("E5 이음 이전 정리로 맞바꿈", SEED, JUNK2, 705, summary_prev=JUNK,
                  summary_prev_at="2026-10-16 14:55:00", summary_edited_at="2026-10-16 14:55:00")
    S["E6"] = mtg("E6 이음 원문 빔", "", "", 706)
    S["E7"] = mtg("E7 이음 메모만 녹음 올리기", SEED, "", 707)
    S["E8"] = mtg("E8 이음 메모 줄바꿈", "첫 줄\r\n둘째 줄", "", 708)
    S["E9"] = mtg("E9 이음 맞바꾸기 뒤 사람이 고침", SEED, JUNK2, 709, summary_prev=JUNK,
                  summary_prev_at="2026-10-16 14:55:00")
    S["N1"] = mtg("N1 직접 손으로 쓴 원문", "손으로 적은 회의 내용입니다. 출하일은 11월 20일.", "")
    S["N2"] = mtg("N2 직접 원문 빔", "", "")
    S["N3"] = mtg("N3 직접 원문과 정리", "손으로 적은 회의 내용", REAL)

seed = {"me": me, "vnu": vnu, "port": PORT, "ids": S, "has_body_edited": "body_edited_at" in MCOLS,
        "seed": SEED, "junk": JUNK, "junk2": JUNK2, "real": REAL, "hand": HAND}
io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(json.dumps(seed, ensure_ascii=False))
print("READY", PORT, json.dumps({"me": me, "ids": S}, ensure_ascii=False), flush=True)
th.join()
