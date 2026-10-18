# -*- coding: utf-8 -*-
"""z1187 시험용 WORKS 서버 — 녹음은 있으나 알아들을 말이 거의 없는 회의록도 「작성 안 됨」.
대표 2026-10-16 「이전에 회의록들은 확인을 안한건가?? 이전 회의록 등록안한건 아직 그대로 인데...」
(사진 = 09-30 회의 「음성 변환 내용이 판독되지 않아 … 확인할 수 없음」 · 이음 「📋 회의록 등록」 · 「📋 회의록 보기」)
사용: py run_q87_app.py <앱폴더(절대경로)> <포트>

z1185 의 run_q85_app.py 와 같은 틀 — AI 는 맨 끝 `ai_client.ai_chat` 하나만 가짜(부른 횟수 `/__test/ai_calls`) ·
음성→글자도 가짜 — **무엇을 돌려줄지 시험이 고른다**(`/__test/stt?mode=noise|talk` : noise = 받아쓰기 헛말 · talk = 회의 말).
🔒 시험 글은 모두 지어낸 것(운영 회의 글을 옮기지 않는다 — 저장소가 공개될 수 있다).

세우는 것 (나 = 김한국 · ko · 사번 901 · 작성자 / Nguyen Van A · vi · 사번 903 · V1 의 작성자)
  이음 회의록(이음 회의 id 801~) — 원문 = 이음 메모(씨앗) + 받아쓴 글
    G1 외국 글자 헛말 + 엉터리 정리       G2 일본어 헛말 한 줄 + 엉터리 정리     G3 녹음 시험 한마디 + 엉터리 정리
    G4 「감사합니다」 되풀이 + 엉터리 정리  G5 긴 안건 메모 + 한 문장 + 메모를 다시 쓴 정리
    G6 회의 말 충분 + 정리                 G7 기준 바로 아래(약 170자) + 정리     G8 기준 바로 위(약 235자) + 정리
    G9 헛말 + 사람이 이음웍스에서 원문을 고침(새것만 표시) + 정리                   G10 베트남어 회의 말 충분 + 정리
    U1 메모만 · 녹음 올리기(잡음 → 다시 올리기)   U2 메모만 · 녹음 올리기(회의 말)   M1 메모만(z1185 안내 그대로인지)
    V1 Nguyen 의 회의 · 헛말 · 정리 전(베트남어 안내)
  이음웍스에서 직접 만든 회의록
    H1 헛말만 + 엉터리 정리      H2 손으로 쓴 글 + 헛말 + 정리
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
os.environ["KNK_SSO_SERVICE_KEY"] = "q87-test-key"      # 시험용 값(운영 키 아님) — msg/status 를 이 검사기가 부르려고
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


#  ── 지어낸 시험 글 ──
TALK = ("오늘은 삼성 A라인 2호기 출하 일정과 셋업 순서를 함께 정리했습니다. "
        "출하는 11월 20일로 하고 포장은 그 전날까지 마치기로 했습니다. "
        "셋업은 25일부터 시작하는데 고객사 담당자의 확인을 먼저 받아야 합니다. "
        "카메라 두 대를 추가해 달라는 요청은 납기에 영향이 있는지 기술팀이 이번 주 안에 확인하겠습니다. "
        "조명 교체 제안은 원가를 먼저 계산해 보고 다음 회의에서 다시 이야기하기로 했습니다. "
        "검사 프로그램은 지난번 오류가 난 부분을 고친 판으로 현장에서 한 번 더 돌려 보겠습니다. "
        "부품 단가가 오른 것은 구매팀이 거래처와 다시 협의해 결과를 공유하기로 했습니다. "
        "다음 회의는 다음 주 화요일 오전 열 시에 같은 장소에서 하겠습니다.")
SENT = [s.strip() + "." for s in TALK.split(".") if s.strip()]
BELOW = " ".join(SENT[:5])        # 기준 바로 아래(약 170자)
ABOVE = " ".join(SENT[:7])        # 기준 바로 위(약 235자)
FOREIGN = ("క ఖగ ఘఙ చఛజ ఝఞట ఠడ ఢణత థదధ నపఫ బభమ యరల వశష సహళ క్షఱ " * 6).strip()
JP = "チャンネル登録をお願いいたします。"
TEST1 = "녹음 한번 해보고 있어. 아."
THANKS = "감사합니다. " * 120 + "시청해 주셔서 감사합니다."
CHAT = "커피 한 잔 더 할래? 창문 좀 열어 줘. 시청해 주셔서 감사합니다."
VI_TALK = ("Hôm nay chúng ta đã thống nhất lịch giao hàng của máy số hai là ngày hai mươi tháng mười một. "
           "Việc lắp đặt sẽ bắt đầu từ ngày hai mươi lăm sau khi khách hàng xác nhận. "
           "Nhóm kỹ thuật sẽ kiểm tra ảnh hưởng của việc thêm hai camera trong tuần này. "
           "Cuộc họp tiếp theo vào thứ Ba tuần sau lúc mười giờ sáng tại cùng phòng họp.")
SEED = "고객사 방문 — 검사기 컨셉 협의 (이음 회의 메모)"
MEMO_LONG = ("미팅 안건: 회사 소개와 질의응답\n\n검사 순서\n작업자가 바코드를 찍고 제품 전원을 연결 -> 제품 자세를 잡고 앞뒤 자동 회전 -> "
             "화면 색을 바꾸며 카메라로 밝기·채도·선명도 검사 -> 성능 검사 -> 불량 항목만 다시 측정 -> 전원 분리")
JUNK = "## 핵심\n음성 변환 내용이 판독되지 않아 회의 결론과 논의 요점을 확인할 수 없음(엉터리 정리)"
MEMO_SUM = "## 핵심\n회사 소개와 질의응답을 진행했고 검사 순서를 공유했다(메모를 다시 쓴 정리)"
REAL = "## 핵심\n출하일을 11월 20일로 정했다(진짜 정리)"
STT = {"mode": "talk"}


def stt_text():
    return ("[가짜 변환] " + CHAT + " " + FOREIGN) if STT["mode"] == "noise" else ("[가짜 변환] " + TALK)


MTG_SUM = ("## 핵심\n출하일을 **2026-11-20**으로 정했다(가짜 정리 %d).\n\n"
           "## 납기\n- [결정] 출하 **11월 20일**\n- [미결] 셋업 시작일 — 고객사 확인 필요")
CALLS = []
CNT = {"m": 0}


def fake_chat(user_text, system="", **kw):
    """맨 끝 한 함수만 가짜 — 부른 것을 적어 두고 정리 모양의 답을 돌려준다(부를 때마다 번호가 바뀐다)."""
    CALLS.append({"len": len(user_text or "")})
    time.sleep(0.4)
    CNT["m"] += 1
    k = CNT["m"]
    return (True, json.dumps({"title": "", "summary": MTG_SUM % k, "decisions": [], "actions": []}, ensure_ascii=False))


ai_client.ai_available = lambda: True
ai_client.ai_chat = fake_chat
ai_client.transcribe_available = lambda: True
ai_client.ai_transcribe = lambda path, lang="": (True, stt_text())


@M.app.get('/__test/ai_calls')
async def _test_ai_calls():
    return _JR({"calls": CALLS, "cnt": CNT})


@M.app.get('/__test/stt')
async def _test_stt(mode: str = "talk"):
    STT["mode"] = "noise" if mode == "noise" else "talk"
    return _JR({"mode": STT["mode"]})


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
    MCOLS = {r[1] for r in c.execute("PRAGMA table_info(meetings)")}
    ta = c.execute("INSERT INTO teams(name, code, display_order) VALUES('기술영업팀','TCA',1)").lastrowid
    tb = c.execute("INSERT INTO teams(name, code, display_order) VALUES('라이프밸류팀','TCB',2)").lastrowid
    me = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='과장', role='member', name='김한국', lang='ko', employee_no='901' "
              "WHERE id=?", (ta, me))
    vnu = c.execute(
        "INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang, employee_no) "
        "VALUES('zq87vn','Nguyen Van A','프로','member',?,1,'x-no-login-z1187','vi','903')", (tb,)).lastrowid

    def mtg(title, body, summary="", msg_id=None, owner=None, audio="", **extra):
        mid = c.execute(
            "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, attendees_text, body, summary, "
            "                     status, msg_meeting_id, audio_path) VALUES(?,?,?,?,'all','김한국, 최민수',?,?,'draft',?,?)",
            (title, TODAY, owner or me, ta, body, summary, msg_id, audio)).lastrowid
        for k, v in extra.items():
            if k in MCOLS:
                c.execute("UPDATE meetings SET %s=? WHERE id=?" % k, (v, mid))
        return mid

    def stt(t):
        return "\n\n🎤 [음성 변환]\n" + t
    S = {}
    S["G1"] = mtg("G1 외국 글자 헛말", SEED + stt(FOREIGN), JUNK, 801, audio="meeting_audio/g1.m4a")
    S["G2"] = mtg("G2 일본어 헛말", SEED + stt(JP), JUNK, 802, audio="meeting_audio/g2.m4a")
    S["G3"] = mtg("G3 녹음 시험 한마디", SEED + stt(TEST1), JUNK, 803, audio="meeting_audio/g3.m4a")
    S["G4"] = mtg("G4 감사합니다 되풀이", SEED + stt(THANKS), JUNK, 804, audio="meeting_audio/g4.m4a")
    S["G5"] = mtg("G5 안건 메모와 한 문장", MEMO_LONG + stt("올해 6월에 양산을 시작해서요."), MEMO_SUM, 805,
                  audio="meeting_audio/g5.m4a")
    S["G6"] = mtg("G6 회의 말 충분", SEED + stt(TALK), REAL, 806, audio="meeting_audio/g6.m4a")
    S["G7"] = mtg("G7 기준 바로 아래", SEED + stt(BELOW), REAL, 807, audio="meeting_audio/g7.m4a")
    S["G8"] = mtg("G8 기준 바로 위", SEED + stt(ABOVE), REAL, 808, audio="meeting_audio/g8.m4a")
    S["G9"] = mtg("G9 헛말과 사람이 고친 원문", "사람이 고친 메모" + stt(TEST1), REAL, 809, audio="meeting_audio/g9.m4a",
                  body_edited_at="2026-10-16 20:00:00")
    S["G10"] = mtg("G10 베트남어 회의 말", SEED + stt(VI_TALK), REAL, 810, audio="meeting_audio/g10.m4a")
    S["U1"] = mtg("U1 메모만 잡음 올리기", SEED, "", 811)
    S["U2"] = mtg("U2 메모만 회의 녹음 올리기", SEED, "", 812)
    S["M1"] = mtg("M1 메모만", SEED, "", 813)
    S["V1"] = mtg("V1 Cuộc họp chỉ có tạp âm", SEED + stt(TEST1), "", 814, owner=vnu, audio="meeting_audio/v1.m4a")
    S["H1"] = mtg("H1 직접 헛말만", stt(TEST1).strip(), JUNK, audio="meeting_audio/h1.m4a")
    S["H2"] = mtg("H2 직접 손글과 헛말", "손으로 적은 회의 내용입니다. 출하일은 11월 20일." + stt(TEST1), REAL,
                  audio="meeting_audio/h2.m4a")
    #  재생기가 찾는 녹음 파일 — 이름만 있고 파일이 없으면 화면이 404 를 콘솔에 찍는다(운영엔 파일이 있다) → 작은 가짜 파일을 둔다
    os.makedirs(os.path.join(APP, "meeting_audio"), exist_ok=True)
    for (_ap,) in c.execute("SELECT audio_path FROM meetings WHERE TRIM(COALESCE(audio_path,''))<>''").fetchall():
        with open(os.path.join(APP, _ap), "wb") as _fh:
            _fh.write(b"RIFF" + b"\0" * 1024)

seed = {"me": me, "vnu": vnu, "port": PORT, "ids": S, "has_body_edited": "body_edited_at" in MCOLS,
        "junk": JUNK, "memo_sum": MEMO_SUM, "real": REAL, "talk": TALK, "below": BELOW, "above": ABOVE, "vi_talk": VI_TALK,
        "foreign": FOREIGN, "jp": JP, "test1": TEST1, "thanks": THANKS, "chat": CHAT}
io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(json.dumps(seed, ensure_ascii=False))
print("READY", PORT, json.dumps({"me": me, "ids": S}, ensure_ascii=False), flush=True)
th.join()
