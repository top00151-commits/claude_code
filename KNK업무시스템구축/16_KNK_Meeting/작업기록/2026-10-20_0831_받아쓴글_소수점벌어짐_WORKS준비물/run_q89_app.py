# -*- coding: utf-8 -*-
"""z1189 시험용 WORKS 서버 — 받아쓴 글의 소수점이 벌어지지 않나(「1.2%」가 「1. 2%」로 안 바뀌나).
대표 2026-10-19 「다음 건으로 고치기 검토 (권장)」(z1188 시연 중 발견 · 운영 받아쓴 글 94곳)
사용: py run_q89_app.py <앱폴더(절대경로)> <포트>

가짜는 맨 끝 둘만 — 받아쓰기(OpenAI 자리 · 진짜 ai_transcribe·ai_transcribe_window·헛말 정리·30초 나누기(진짜 ffmpeg)가 돈다) ·
정리 AI(ai_chat — 받은 원문을 적어 둔다 = 정리 AI 가 보는 글).
  통째 받아쓰기(자동 감지) = 숫자 많은 한국어 회의 말 · 30초 조각(섞임) = part_000 베트남어(3.5) · part_001 한국어(1.2%) · 그 밖 빈칸
🔒 시험 글은 모두 지어낸 것. ⛔ 진짜 AI·이음을 부르지 않는다.
"""
import io
import json
import os
import re
import shutil
import sys
import threading
import time
import types
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
APP = sys.argv[1]
PORT = int(sys.argv[2])
os.chdir(APP)
sys.path.insert(0, APP)
os.environ.setdefault("KNK_SECRET_KEY", "verify-only-key")
os.environ["KNK_MESSENGER_SSO_INTERNAL_BASE"] = "http://127.0.0.1:9"
os.environ["KNK_SSO_SERVICE_KEY"] = "q89-test-key"      # 시험용 값(운영 키 아님)
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
    return _PTR_no_sw('/* 시험용 빈 서비스워커 — 아무 일도 하지 않는다 */',
                      media_type='application/javascript')


#  ── 지어낸 시험 글(숫자 많은 회의) ──
DEC_TALK = ("오늘은 2호기 검사 결과를 정리했습니다. 불량률은 1.2%로 지난달 0.8%보다 올랐습니다. "
            "공차는 0.05mm 안으로 맞춰야 하고 두께는 2.5mm로 바꾸기로 했습니다. "
            "출하는 10.23일로 하고 셋업은 4.5일 걸린다고 봤습니다. 단가는 3.75달러로 다시 협의하겠습니다. "
            "검사 프로그램 버전 2.0 을 현장에 올려 한 번 더 돌려 보겠습니다. "
            "구매팀은 거래처에 견적을 다시 요청하고 결과를 이번 주 금요일까지 공유하기로 했습니다. "
            "카메라 두 대를 추가해 달라는 요청은 납기에 영향이 있는지 기술팀이 이번 주 안에 확인하겠습니다. "
            "조명 교체 제안은 원가를 먼저 계산해 보고 다음 회의에서 다시 이야기하기로 했습니다. "
            "다음 회의는 다음 주 화요일 오전 열 시입니다.")
VI_DEC = ("Giá vận chuyển là 3.5 triệu đồng một chuyến. Máy số hai cần chỉnh khe hở 0.2 mm trước khi giao hàng. "
          "Bên khách hàng muốn nhận hàng vào thứ sáu tuần sau. "
          "Nhóm kỹ thuật sẽ kiểm tra lại tỉ lệ lỗi 1.2% và báo cáo vào sáng mai.")
KO_DEC = ("네, 알겠습니다. 그럼 불량률 1.2%는 다시 확인하고 운송비 3.5백만 동은 구매팀이 거래처와 협의하겠습니다. "
          "검사 결과는 내일 오전까지 고객사에 공유하겠습니다. "
          "셋업 일정은 고객사 담당자와 다시 맞춰 보고 결과를 이번 주 안에 알려 드리겠습니다.")
SEED = "고객사 방문 — 검사기 컨셉 협의 (이음 회의 메모)"
PLAIN_SUM = "## 핵심\n검사 결과를 정리했다(가짜 정리 %d).\n\n## 품질\n- 불량률 확인"
TR = []


def _answer(name, kw):
    m = re.match(r"part_(\d+)\.mp3$", name or "")
    if not m:
        return DEC_TALK
    i = int(m.group(1))
    return {0: VI_DEC, 1: KO_DEC}.get(i, "")


class _FakeTr:
    def create(self, file=None, **kw):
        name = os.path.basename(getattr(file, "name", "") or "")
        TR.append({"file": name, "kw": json.loads(json.dumps(kw, ensure_ascii=False, default=str))})
        time.sleep(0.2)
        return types.SimpleNamespace(text=_answer(name, kw))


class _FakeClient:
    def __init__(self, **_):
        self.audio = types.SimpleNamespace(transcriptions=_FakeTr())


ai_client.openai = types.SimpleNamespace(OpenAI=_FakeClient)
ai_client._OPENAI_OK = True
ai_client._key_for = lambda provider: "sk-test-q89-not-a-real-key"   # 가짜 — 바깥으로 안 나간다(openai 자리도 가짜)
ai_client.transcribe_available = lambda: True
CALLS = []
CNT = {"m": 0}


def fake_chat(user_text, system="", **kw):
    CALLS.append({"user": user_text or "", "max_tokens": kw.get("max_tokens")})
    time.sleep(0.2)
    CNT["m"] += 1
    return (True, json.dumps({"title": "", "summary": PLAIN_SUM % CNT["m"], "decisions": [], "actions": []},
                             ensure_ascii=False))


ai_client.ai_available = lambda: True
ai_client.ai_chat = fake_chat


@M.app.get('/__test/tr')
async def _test_tr(reset: int = 0):
    out = list(TR)
    if reset:
        TR.clear()
    return _JR({"tr": out})


@M.app.get('/__test/chat')
async def _test_chat():
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
    ta = c.execute("INSERT INTO teams(name, code, display_order) VALUES('기술영업팀','TCA',1)").lastrowid
    me = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='과장', role='member', name='김한국', lang='ko', employee_no='901' "
              "WHERE id=?", (ta, me))

    def mtg(title, msg_id):
        return c.execute(
            "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, attendees_text, body, summary, "
            "                     status, msg_meeting_id, audio_path) VALUES(?,?,?,?,'all','김한국, 최민수',?,'','draft',?,'')",
            (title, TODAY, me, ta, SEED, msg_id)).lastrowid
    S = {"D1": mtg("D1 자동 감지 녹음(숫자 많음)", 841), "D2": mtg("D2 섞인 녹음(숫자)", 842)}

seed = {"me": me, "port": PORT, "ids": S, "seed": SEED, "dec_talk": DEC_TALK, "vi_dec": VI_DEC, "ko_dec": KO_DEC,
        "has_window": hasattr(ai_client, "ai_transcribe_window")}
io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(json.dumps(seed, ensure_ascii=False))
print("READY", PORT, json.dumps({"me": me, "ids": S}, ensure_ascii=False), flush=True)
th.join()
