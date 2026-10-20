# -*- coding: utf-8 -*-
"""z1188 시험용 WORKS 서버 — 한국어·베트남어 섞인 녹음 「한국어+베트남어 섞임」(30초 조각) + 정리 「v_」 표시.
대표 2026-10-19 「회의록 및 음성메모 녹음본을 베트남어가 같이 있는 음성을 올려도 베트남어 까지 같이 확인하고 정리 할수있어?
  베트남어에서 추출해서 정리한 내용은 별도 표기를 했으면 하는데.. 예를들어 문장앞에 "v_" 이런식으로」 → 「A+B 만들기 (권장)」
사용: py run_q88_app.py <앱폴더(절대경로)> <포트>

가짜는 **맨 끝 둘**만 — 그 위 코드(받아쓰기 함수 · 30초 나누기(진짜 ffmpeg) · 헛말 거르기 · 정리 함수)는 진짜가 돈다:
  ① OpenAI 받아쓰기 = `ai_client.openai` 자리의 받아 적는 가짜 — 조각 이름(part_NNN)으로 무엇을 돌려줄지 고른다
     (시나리오 `/__test/mix?sc=script|fail3` · 받은 요청 = `/__test/tr`)
       part_000 = 베트남어 · part_001 = 빈칸 → 다시 받아쓰면 한국어 · part_002 = 힌트 낱말 헛말 → 다시 해도 헛말(버림) ·
       part_003 = 한국어 · part_004 = 1초 못 되는 자투리(보내면 안 된다) · 조각 아닌 파일(자동 감지 길) = 한국어 회의 말
       fail3 = part_002 에서 두 모델 모두 오류
  ② 정리 AI = `ai_client.ai_chat` — 받은 지시문·원문을 적어 둔다(`/__test/chat`) · 원문에 「〔베트남어〕」가 있으면
     표시가 새어 나오고 자리가 틀린 답(서버가 손봐야 하는 모양)을 돌려준다
🔒 시험 글은 모두 지어낸 것(운영 회의 글을 옮기지 않는다 — 저장소가 공개될 수 있다).
⛔ 진짜 AI·이음을 부르지 않는다(키 자리 = 시험용 가짜 글 · openai 모듈 자리 = 가짜) · 진짜 로그인 대신 쿠키 tuser=<사람 id>.
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
os.environ["KNK_SSO_SERVICE_KEY"] = "q88-test-key"      # 시험용 값(운영 키 아님)
for _k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "KNK_OPENAI_API_KEY"):
    os.environ[_k] = ""
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)   # 서버 기록([VI-MARK])을 검사기가 바로 읽는다
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
VI_W = ("Anh ơi, hôm nay mình kiểm tra máy số hai trước khi giao hàng nhé. "
        "Giá vận chuyển là 3.5 triệu đồng một chuyến. "
        "Bên khách hàng muốn nhận hàng vào thứ sáu tuần sau, nên phải đóng gói xong trước thứ năm.")
KO_W1 = ("네, 알겠습니다. 그럼 출하 전에 2호기 검사를 한 번 더 하고 결과를 고객사에 공유하겠습니다. "
         "운송비는 구매팀이 거래처와 다시 확인해 주세요.")
KO_W2 = ("셋업은 25일부터 시작하고 고객사 담당자 확인을 먼저 받기로 했습니다. "
         "다음 회의는 다음 주 화요일 오전 열 시에 같은 장소에서 하겠습니다.")
KW_JUNK = "ép phun nhựa, khuôn mẫu, bản vẽ, ngày giao hàng"       # 힌트 낱말이 그대로 나온 헛말(대표 시험 18분 메모)
HALLU_W = "시청해 주셔서 감사합니다."
SEED = "고객사 방문 — 검사기 컨셉 협의 (이음 회의 메모)"
MIXED = VI_W + "\n" + KO_W1 + "\n" + KO_W2
PLAIN_SUM = ("## 핵심\n출하일을 **2026-11-20**으로 정했다(가짜 정리 %d).\n\n"
             "## 납기\n- [결정] 출하 **11월 20일**\n- [미결] 셋업 시작일 — 고객사 확인 필요")
#  표시가 새어 나오고 · 「v_ 」 띄어 쓰고 · [결정] 앞에 붙은 답 — 서버가 손봐야 하는 모양
LEAK_SUM = ("## 핵심\n출하 일정과 셋업 순서를 정했다(가짜 정리 %d).\n\n"
            "## 납기\n- 〔베트남어〕2호기 출하는 다음 주 금요일로 한다\n- v_[결정] 포장은 목요일까지 마친다\n"
            "- v_ 운송비는 3.5백만 동으로 들었다 [확인 필요]\n- [결정] 셋업은 25일부터 시작한다")
LEAK_DEC = [{"who": "", "what": "v_(내부 방침) 포장은 목요일까지 마친다", "due": ""},
            {"who": "", "what": "셋업은 25일부터 시작한다", "due": ""}]
LEAK_ACT = [{"assignee": "", "task": "〔베트남어〕 2호기 검사 결과를 고객사에 공유한다", "due": ""},
            {"assignee": "", "task": "운송비를 거래처와 다시 확인한다", "due": ""}]

#  ── ① 받아쓰기 가짜(OpenAI 자리) ──
TR = []
MIX = {"sc": "script"}
_RETRY = getattr(ai_client, "_STT_MIX_RETRY_PROMPT", None)


def _answer(name, kw):
    m = re.match(r"part_(\d+)\.mp3$", name or "")
    if not m:
        return TALK                                   # 자동 감지 길(통째) — 한국어 회의 말
    i = int(m.group(1))
    retry = _RETRY is not None and kw.get("prompt") == _RETRY
    if MIX["sc"] == "fail3" and i == 2:
        raise RuntimeError("boom-q88")
    if i == 0:
        return VI_W
    if i == 1:
        return KO_W1 if retry else ""
    if i == 2:
        return HALLU_W if retry else KW_JUNK
    if i == 3:
        return KO_W2
    return "TINY-CALLED"


class _FakeTr:
    def create(self, file=None, **kw):
        name = os.path.basename(getattr(file, "name", "") or "")
        try:
            size = os.path.getsize(file.name)
        except Exception:
            size = -1
        rec = {"file": name, "size": size, "kw": json.loads(json.dumps(kw, ensure_ascii=False, default=str)),
               "t": round(time.time(), 3)}
        TR.append(rec)
        time.sleep(0.3)
        try:
            txt = _answer(name, kw)
        except Exception as e:
            rec["raised"] = str(e)
            raise
        rec["text"] = txt
        return types.SimpleNamespace(text=txt)


class _FakeClient:
    def __init__(self, **_):
        self.audio = types.SimpleNamespace(transcriptions=_FakeTr())


ai_client.openai = types.SimpleNamespace(OpenAI=_FakeClient)
ai_client._OPENAI_OK = True
ai_client._key_for = lambda provider: "sk-test-q88-not-a-real-key"   # 가짜 — 바깥으로 안 나간다(openai 자리도 가짜)
ai_client.transcribe_available = lambda: True

#  ── ② 정리 AI 가짜(맨 끝 한 함수) ──
CALLS = []
CNT = {"m": 0}


def fake_chat(user_text, system="", **kw):
    CALLS.append({"user": user_text or "", "system": system or "", "max_tokens": kw.get("max_tokens")})
    time.sleep(0.3)
    CNT["m"] += 1
    k = CNT["m"]
    if "〔베트남어〕" in (user_text or ""):
        return (True, json.dumps({"title": "", "summary": LEAK_SUM % k, "decisions": LEAK_DEC, "actions": LEAK_ACT},
                                 ensure_ascii=False))
    return (True, json.dumps({"title": "", "summary": PLAIN_SUM % k, "decisions": [], "actions": []}, ensure_ascii=False))


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


@M.app.get('/__test/mix')
async def _test_mix(sc: str = "script"):
    MIX["sc"] = sc if sc in ("script", "fail3") else "script"
    return _JR({"sc": MIX["sc"]})


_PATH0 = os.environ.get("PATH", "")


@M.app.get('/__test/noff')
async def _test_noff(on: int = 1):
    """on=1: 서버가 ffmpeg 를 못 찾게 PATH 에서 그 폴더를 뺀다 · on=0: 되돌린다."""
    if on:
        for _ in range(8):                       # 같은 이름이 여러 폴더에 있을 수 있다 → 못 찾을 때까지 뺀다
            ff = shutil.which("ffmpeg") or ""
            if not ff:
                break
            d = os.path.normcase(os.path.dirname(ff).rstrip("\\/"))
            os.environ["PATH"] = os.pathsep.join(p for p in os.environ.get("PATH", "").split(os.pathsep)
                                                 if os.path.normcase(p.rstrip("\\/")) != d)
    else:
        os.environ["PATH"] = _PATH0
    return _JR({"ffmpeg": shutil.which("ffmpeg") or ""})


@M.app.get('/__test/junk')
async def _test_junk(t: str = ""):
    f = getattr(M, "_stt_mix_junk", None)
    return _JR({"have": f is not None, "junk": (f(t) if f else None)})


@M.app.get('/__test/mixdirs')
async def _test_mixdirs():
    """30초 조각을 담았던 임시 폴더가 남았나(받아쓰기가 끝나면 지워야 한다)."""
    left = []
    for root, dirs, _files in os.walk(APP):
        for d in dirs:
            if d.startswith("stt_mix_") or d.startswith("stt_parts_"):
                left.append(os.path.relpath(os.path.join(root, d), APP))
    return _JR({"left": left})


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
WAV120 = os.path.join(HERE, "q88_120s.wav")      # 시험이 만들어 둔다(진짜 ffmpeg · 120.4초 = 30초 조각 넷 + 0.4초 자투리)
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
        "VALUES('zq88vn','Nguyen Van A','프로','member',?,1,'x-no-login-z1188','vi','903')", (tb,)).lastrowid

    def mtg(title, body, summary="", msg_id=None, owner=None, audio=""):
        return c.execute(
            "INSERT INTO meetings(title, meeting_date, owner_id, team_id, visibility, attendees_text, body, summary, "
            "                     status, msg_meeting_id, audio_path) VALUES(?,?,?,?,'all','김한국, 최민수',?,?,'draft',?,?)",
            (title, TODAY, owner or me, ta, body, summary, msg_id, audio)).lastrowid

    def stt(t):
        return "\n\n🎤 [음성 변환]\n" + t
    S = {}
    S["U1"] = mtg("U1 섞인 녹음 올리기", SEED, "", 821)
    S["U2"] = mtg("U2 자동 감지 녹음 올리기", SEED, "", 822)
    S["U3"] = mtg("U3 섞인 녹음 조각 실패", SEED, "", 823)
    S["U4"] = mtg("U4 ffmpeg 없음", SEED, "", 824)
    S["A1"] = mtg("A1 API 로 mix", SEED, "", 825, audio="meeting_audio/a1.wav")
    S["A2"] = mtg("A2 API 로 모르는 말", SEED, "", 826, audio="meeting_audio/a2.wav")
    S["A3"] = mtg("A3 API 로 대문자 MIX", SEED, "", 827, audio="meeting_audio/a3.wav")
    S["K1"] = mtg("K1 한국어만 정리", SEED + stt(TALK), "", 828)
    S["V1"] = mtg("V1 섞인 원문 정리", SEED + stt(MIXED), "", 829)
    S["W1"] = mtg("W1 Cuộc họp của Nguyen", SEED, "", 830, owner=vnu)
    N = {}
    N["N1"] = c.execute("INSERT INTO voice_notes(owner_id, title, body) VALUES(?,?,?)",
                        (me, "N1 한국어만 메모", TALK)).lastrowid
    N["N2"] = c.execute("INSERT INTO voice_notes(owner_id, title, body) VALUES(?,?,?)",
                        (me, "N2 섞인 메모", VI_W + "\n" + KO_W1)).lastrowid
    os.makedirs(os.path.join(APP, "meeting_audio"), exist_ok=True)
    for _ap in ("a1.wav", "a2.wav", "a3.wav"):
        shutil.copyfile(WAV120, os.path.join(APP, "meeting_audio", _ap))

seed = {"me": me, "vnu": vnu, "port": PORT, "ids": S, "notes": N, "today": TODAY,
        "talk": TALK, "vi_w": VI_W, "ko_w1": KO_W1, "ko_w2": KO_W2, "kw_junk": KW_JUNK, "hallu_w": HALLU_W,
        "seed": SEED, "mixed": MIXED, "leak_sum": LEAK_SUM, "plain_sum": PLAIN_SUM,
        "has_window": hasattr(ai_client, "ai_transcribe_window")}
io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(json.dumps(seed, ensure_ascii=False))
print("READY", PORT, json.dumps({"me": me, "ids": S, "notes": N}, ensure_ascii=False), flush=True)
th.join()
