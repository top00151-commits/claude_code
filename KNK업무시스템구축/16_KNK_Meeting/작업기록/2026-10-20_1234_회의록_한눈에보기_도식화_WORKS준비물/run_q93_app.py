# -*- coding: utf-8 -*-
"""z1193 시험용 WORKS 서버 — 회의록 「📊 한눈에 보기」(도식화 · 추가 화면).
대표 2026-10-20 「회의 내용을 이미지화 또는 도식화해서 더 쉽게 이해할수있는 페이지를 추가」 · 「글로된 회의록 정리는 그대로 … 추가로」
사용: py run_q93_app.py <앱폴더(절대경로)> <포트>

가짜 = 맨 끝 `ai_client.ai_chat` 하나(그림 자료 지시문이면 지어낸 그림 JSON · 정리 지시문이면 지어낸 정리 JSON · 받은 지시문·원문을 적어 둔다
`/__test/chat`) · 진짜 로그인 대신 쿠키 tuser · 이음 주소는 닫힌 포트 · 🔒 시험 글은 모두 지어낸 것.
회의(모두 지어낸 글)
  V1 정리 있음 + 받아쓴 글 충분 → 그림 만들기 길   V2 정리 없음        V3 정리 있음 + 받아쓴 글 헛말(이음 회의)
  V4 그림 있음(옛 지문) + 정리가 바뀜 → 「다시 그리기」 안내   V5 남의 회의(대외비)   V6 공개 회의(보는 사람 = 편집 못 함)
  V7 AI 오류    V8 정리 지시문 대조용(정리를 돌린다)
사람: 김한국(901 · 작성자) · 박다른(905 · 다른 팀 · 참석자 아님) · Nguyen Van A(903 · vi · V6 보는 사람)
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
os.environ["KNK_SSO_SERVICE_KEY"] = "q93-test-key"      # 시험용 값(운영 키 아님)
for _k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "KNK_OPENAI_API_KEY"):
    os.environ[_k] = ""
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
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
    return _PTR_no_sw('/* 시험용 빈 서비스워커 */', media_type='application/javascript')


#  ── 지어낸 시험 글 ──
TALK = ("오늘은 삼성 A라인 2호기 출하 일정과 셋업 순서를 함께 정리했습니다. "
        "출하는 11월 20일로 하고 포장은 그 전날까지 마치기로 했습니다. "
        "셋업은 25일부터 시작하는데 고객사 담당자의 확인을 먼저 받아야 합니다. "
        "카메라 두 대를 추가해 달라는 요청은 납기에 영향이 있는지 기술팀이 이번 주 안에 확인하겠습니다. "
        "조명 교체 제안은 원가를 먼저 계산해 보고 다음 회의에서 다시 이야기하기로 했습니다. "
        "검사 프로그램은 지난번 오류가 난 부분을 고친 판으로 현장에서 한 번 더 돌려 보겠습니다. "
        "부품 단가가 오른 것은 구매팀이 거래처와 다시 협의해 결과를 공유하기로 했습니다. "
        "다음 회의는 다음 주 화요일 오전 열 시에 같은 장소에서 하겠습니다.")
TEST1 = "녹음 한번 해보고 있어. 아."
SEED = "고객사 방문 — 검사기 컨셉 협의 (이음 회의 메모)"
SUM = ("## 핵심\n2호기 출하 일정과 셋업 순서를 정했다(지어낸 정리).\n\n## 납기·셋업\n- [결정] 출하 **11월 20일** · 포장은 전날까지\n"
       "- [미결] 셋업 시작일 — 고객사 확인 필요\n\n## 추가 요청\n- 카메라 두 대 추가 — 납기 영향 확인(기술팀)\n- (내부 방침) 조명 교체는 원가 계산 뒤 다음 회의에서")
SUM_OLD = "## 핵심\n옛 정리(그림을 만들 때의 정리).\n\n## 납기\n- [결정] 출하 11월 20일"
#  그림 자료(가짜 AI 답) — q 는 원문·정리에서 옮긴 구절(근거 찾기 시험용 · 하나는 일부러 없는 구절 · 하나는 정리에만 있는 구절)
VIZ = {
    "kind": "equip", "headline": "2호기 출하 일정과 셋업 순서를 정했다", "headline_q": "출하 일정과 셋업 순서를 함께 정리했습니다",
    "numbers": [{"v": "11월 20일", "label": "출하", "q": "출하는 11월 20일로 하고"},
                {"v": "카메라 2대", "label": "추가 요청", "q": "카메라 두 대를 추가해 달라는 요청"},
                {"v": "25일", "label": "셋업 시작", "q": "셋업은 25일부터 시작하는데"}],
    "flow": {"zones": [
        {"name": "투입", "note": "제품 투입", "steps": [{"label": "제품 투입", "sub": "작업자", "type": "in", "warn": "", "q": ""}]},
        {"name": "검사", "note": "검사 프로그램", "steps": [
            {"label": "검사 프로그램", "sub": "고친 판으로 한 번 더", "type": "insp", "warn": "오류 부분 재확인", "q": "지난번 오류가 난 부분을 고친 판으로"},
            {"label": "판정", "sub": "OK/NG", "type": "judge", "warn": "", "q": ""},
            {"label": "이상한 종류", "sub": "type 이 엉뚱함", "type": "weird", "warn": "", "q": ""}]},
        {"name": "출하", "note": "포장 → 출하", "steps": [{"label": "포장", "sub": "전날까지", "type": "step", "warn": "", "q": "포장은 그 전날까지 마치기로"},
                                                 {"label": "출하", "sub": "11월 20일", "type": "out", "warn": "", "q": "출하는 11월 20일로"}]}],
        "loop": {"label": "빈 트레이 회수", "from": "출하", "to": "투입"}},
    "decided": [{"t": "[결정] 출하는 11월 20일 · 포장은 전날까지", "q": "출하는 11월 20일로 하고 포장은 그 전날까지"},
                {"t": "(내부 방침) 조명 교체는 원가 계산 뒤 다음 회의에서", "q": "조명 교체 제안은 원가를 먼저 계산해 보고"}]
               + [{"t": "[결정] 시험용 결정 %d" % i, "q": ""} for i in range(3, 16)],      # 15개 → 12개로 잘려야 한다
    "open": [{"t": "[확인 필요] 셋업 시작일 — 고객사 확인", "q": "고객사 담당자의 확인을 먼저 받아야"},
             {"t": "[미결] 셋업 시작일(정리에만 있는 구절)", "q": "셋업 시작일 — 고객사 확인 필요"}],
    "todo": [{"t": "카메라 추가의 납기 영향 확인", "who": "기술팀", "due": "2026-10-24", "q": "기술팀이 이번 주 안에 확인하겠습니다"},
             {"t": "부품 단가 거래처 재협의", "who": "구매팀", "due": "25일", "q": "구매팀이 거래처와 다시 협의해"},
             {"t": "정리에만 있는 항목(근거 없음)", "who": "", "due": "", "q": "이 구절은 원문에 없다 zzz"}],
    "timeline": [{"when": "10-27 (화)", "t": "다음 회의 오전 열 시", "sure": True, "q": "다음 회의는 다음 주 화요일 오전 열 시"},
                 {"when": "11-20", "t": "출하", "sure": True, "q": "출하는 11월 20일"},
                 {"when": "11-25", "t": "셋업 시작", "sure": False, "q": "셋업은 25일부터"}],
    "parts": [{"what": "카메라", "spec": "2대 추가", "note": "납기 영향 확인", "q": "카메라 두 대를 추가해 달라는"}],
}
PLAIN = {"title": "", "summary": "## 핵심\n출하일을 **2026-11-20**으로 정했다(가짜 정리).", "decisions": [], "actions": []}
CALLS = []


def fake_chat(user_text, system="", **kw):
    CALLS.append({"user": user_text or "", "system": system or "", "max_tokens": kw.get("max_tokens"), "temperature": kw.get("temperature")})
    time.sleep(0.4)
    if "그림 자료" in (system or ""):
        if "회의 제목: V7" in (user_text or ""):
            return (False, "AI 호출 오류(가짜): 시험용 실패")
        return (True, json.dumps(VIZ, ensure_ascii=False))
    return (True, json.dumps(PLAIN, ensure_ascii=False))


ai_client.ai_available = lambda: True
ai_client.ai_chat = fake_chat
ai_client.transcribe_available = lambda: True


@M.app.get('/__test/chat')
async def _test_chat():
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

srv = uvicorn.Server(uvicorn.Config(M.app, host="127.0.0.1", port=PORT, log_level="warning", lifespan="on"))
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
    MCOLS = {r[1] for r in c.execute("PRAGMA table_info(meetings)")}
    ta = c.execute("INSERT INTO teams(name, code, display_order) VALUES('기술영업팀','TCA',1)").lastrowid
    tb = c.execute("INSERT INTO teams(name, code, display_order) VALUES('라이프밸류팀','TCB',2)").lastrowid
    me = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='과장', role='member', name='김한국', lang='ko', employee_no='901' WHERE id=?", (ta, me))
    other = c.execute("INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang, employee_no) "
                      "VALUES('zq93x','박다른','프로','member',?,1,'x-no-login-z1193','ko','905')", (tb,)).lastrowid
    vnu = c.execute("INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang, employee_no) "
                    "VALUES('zq93vn','Nguyen Van A','프로','member',?,1,'x-no-login-z1193','vi','903')", (tb,)).lastrowid

    def mtg(title, body, summary="", vis="all", msg_id=None, **extra):
        mid = c.execute(
            "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, attendees_text, body, summary, status, msg_meeting_id, "
            "location, msg_started_at, ended_at) VALUES(?,?,?,?,?,'김한국, 최민수',?,?,'draft',?,'2층 회의실1','%s 14:00:27','%s 14:50:28')"
            % (TODAY, TODAY), (title, TODAY, me, ta, vis, body, summary, msg_id)).lastrowid
        for k, v in extra.items():
            if k in MCOLS:
                c.execute("UPDATE meetings SET %s=? WHERE id=?" % k, (v, mid))
        return mid

    def stt(t):
        return "\n\n🎤 [음성 변환]\n" + t
    S = {}
    S["V1"] = mtg("V1 설비 회의(그림 만들기)", SEED + stt(TALK), SUM)
    S["V2"] = mtg("V2 정리 없음", SEED + stt(TALK), "")
    S["V3"] = mtg("V3 받아쓴 글 헛말", SEED + stt(TEST1), SUM, msg_id=831)
    S["V4"] = mtg("V4 그림 있음 · 정리 바뀜", SEED + stt(TALK), SUM,
                  viz_json=json.dumps(dict(VIZ, headline="옛 그림"), ensure_ascii=False), viz_at="2026-10-19 10:00:00", viz_kind="equip", viz_sum_sig="deadbeef0000")
    S["V5"] = mtg("V5 남의 대외비 회의", SEED + stt(TALK), SUM, vis="private")
    S["V6"] = mtg("V6 공개 회의(보기만)", SEED + stt(TALK), SUM)
    S["V7"] = mtg("V7 AI 오류", SEED + stt(TALK), SUM)
    S["V8"] = mtg("V8 정리 지시문 대조", SEED + stt(TALK), "")
    for k in ("V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"):
        c.execute("INSERT INTO meeting_decisions(meeting_id, who, what, due, source) VALUES(?,?,?,?,'ai')", (S[k], "", "출하는 11월 20일로 한다(지어낸 결정)", "2026-11-20"))
        c.execute("INSERT INTO meeting_actions(meeting_id, assignee_name, task, due_date, source) VALUES(?,?,?,?,'ai')", (S[k], "기술팀", "카메라 추가 납기 영향 확인(지어낸 할 일)", ""))

seed = {"me": me, "other": other, "vnu": vnu, "port": PORT, "ids": S, "talk": TALK, "sum": SUM, "viz": VIZ, "seed": SEED,
        "has_viz_cols": "viz_json" in MCOLS}
io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(json.dumps(seed, ensure_ascii=False))
print("READY", PORT, json.dumps({"me": me, "ids": S}, ensure_ascii=False), flush=True)
th.join()
