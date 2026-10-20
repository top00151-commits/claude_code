# -*- coding: utf-8 -*-
"""z1188 검사기 — 한국어·베트남어 섞인 녹음 「한국어+베트남어 섞임」(30초 조각) + 정리 「v_」 표시.
대표 2026-10-19 「회의록 및 음성메모 녹음본을 베트남어가 같이 있는 음성을 올려도 베트남어 까지 같이 확인하고 정리 할수있어?
  베트남어에서 추출해서 정리한 내용은 별도 표기를 했으면 하는데.. 예를들어 문장앞에 "v_" 이런식으로」 → 「A+B 만들기 (권장)」

재는 것 (앱 두 벌 = 운영 그대로(app_base) · 새것(app_new))
  ━ 서버 안 띄움 (두 벌의 ai_client 를 직접 불러 받아 적는 가짜 OpenAI·AI 를 끼운다) ━
  ① 🔴 「자동 감지」·한국어·베트남어 받아쓰기 요청은 운영과 **글자 하나까지 같다**(힌트 켬·끔 · 낱말 추가 · 예비 모델)
  ② 섞인 녹음 조각 요청 = 3차 시험 방식 그대로(지시 = 운영 자동 감지 지시에서 「알아듣기 어려우면 빼라」만 뺌 · 앞 조각 글 끝 200자 ·
     다시 받아쓰기 = 짧은 지시 · 낱말 없이) · 낱말 거부 → 같은 모델로 · 오류 → 예비 모델(앞 글만) · 키·파일 없음
  ③ 베트남어 문장 고르기 — 한국어만이면 원문 **그대로(같은 글)** · 「3.5」 안 자름 · 한국어 문장 속 지명 아님 · NFD 글자
  ④ 🔴 한국어만 있는 회의·메모 → AI 에 가는 지시문·원문·답 길이가 운영과 **글자 그대로** · 답 손보기도 안 함
  ⑤ 베트남어가 있으면 → 지시문 = 운영 지시문 + 「v_」 규칙 · 원문 = 표시한 글 · 새어 나온 표시·자리 틀린 「v_」 손보기 · 기록엔 숫자만
  ⑥ 운영 지시문(회의록·음성 메모·받아쓰기)·낱말 목록 그대로 · main.py 바뀐 자리
  ━ 진짜 서버(받아쓰기·정리 AI 맨 끝만 가짜 · 30초 나누기는 진짜 ffmpeg) + 진짜 브라우저 ━
  ⑦ 헛말 판정 도우미
  ⑧ 화면 — 「회의에서 쓰는 말」·「쓰는 말」에 「한국어+베트남어 섞임」(한국어·베트남어 화면) · 안내 글 · 주소 sttlang=mix ·
     🔴 반대 시험: 운영엔 없다
  ⑨ 회의록 녹음 올리기(섞임) → 30초 조각 5개(자투리 0.4초는 안 보냄) · 빈칸 → 다시 → 살림 · 힌트 낱말 헛말 → 다시 → 또 헛말 → 버림 ·
     앞 조각 글 이어 주기 · 진행 글 · 조각 폴더 지움 → 정리 → 「v_」 손본 정리·결정·할 일 → 화면·회의록 양식 · 기록
  ⑩ 「자동 감지」 녹음 올리기 = 운영과 같은 요청 한 번(조각 없음) · API 로 mix / 모르는 말 / 대문자 · 🔴 반대: 운영은 mix 를 모른다(통째)
  ⑪ 조각 하나 실패 → 통째 실패(원문 그대로 · 몇 번째 조각 · 몇 분부터) · ffmpeg 없음 → 안내
  ⑫ 음성 메모(섞임) → 30초 조각(끝 5초 조각은 보냄) → 정리 「v_」
  ⑬ 서버로 정리 — 한국어만(회의록·메모) 지시문·원문 운영과 같다 · 섞인 원문은 규칙·표시만 더해짐
  ⑭ 콘솔 오류 0
쓰는 법: py q88_check.py <app_base·app_new 가 있는 폴더>
판정: **종료코드**(0=통과) + 요약 줄.
🔒 시험 글은 모두 지어낸 것.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import sqlite3
import subprocess
import sys
import time
import types
import unicodedata
import urllib.parse
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1] if len(sys.argv) > 1 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
PB, PN = 8929, 8930
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
KNOWN = "Transition was skipped"   # 운영에도 있는 공용 화면 전환 경고(z1182 확인) — 이번 변경 밖
OMIT = "If a part is unclear, omit it rather than guessing."
RETRY_EXP3 = ("The speakers may be using Korean, Vietnamese, or both. Transcribe verbatim in the language "
              "actually spoken. Do not translate.")          # 3차 시험(stt_exp3.py)에 쓴 글 그대로
PREV = " Previous part of this recording (context only — do not repeat it): "
MIX_KO = "한국어+베트남어 섞임"
MIX_VI = "Tiếng Hàn + Tiếng Việt (lẫn lộn)"
NOTE_KO = ("골라 주면 받아쓰기가 더 정확해집니다. 한국어와 베트남어가 섞인 회의는 「한국어+베트남어 섞임」을 고르세요"
           "(30초씩 나눠 받아써 시간이 더 걸립니다).")
NOTE_VI = ("Chọn đúng thì việc ghi lại sẽ chính xác hơn. Cuộc họp dùng lẫn tiếng Hàn và tiếng Việt thì hãy chọn "
           "「Tiếng Hàn + Tiếng Việt (lẫn lộn)」 (chia từng đoạn 30 giây nên lâu hơn).")
FFMPEG_ERR = "서버에 음성 나누는 도구(ffmpeg)가 없어 「한국어+베트남어 섞임」으로 받아쓰지 못했습니다 — 관리자에게 알려 주세요."
#  받아쓰기가 힌트 낱말 목록을 그대로 내놓은 헛말(시연 10-19 · 18분 메모 · 빗금·마침표·쉼표가 섞임) — 회사 낱말 목록이지 회의 글이 아니다
KW_SLASH = ("케이엔케이 / 하이스트. 사출, 금형, 지그, 포고핀, 프로브핀, 비전검사, 검사장비, 출하 검사기, 자동화, 공차, 치수, 품번, "
            "발주, 견적, 납기, 검수, 협력사, 고객사, 베트남법인, 설비, 가동, 불량, 양산, 샘플, 도면, 센서, 컨베이어, 에어호스, 유닛, "
            "조립체, 단가, 세금계산서, 동글, 정전기, 표면저항, ép phun nhựa, khuôn mẫu, bản vẽ, ngày giao hàng, máy kiểm tra, "
            "kích thước, nghiệm thu, báo giá, nhà cung cấp, dây khí, cụm, MLCC, FPCB, 파트리스트, 러버, PVC")
OK = FAIL = 0


def chk(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (name, str(detail)[:900]))


def freeport(port):
    ps = ("Get-NetTCPConnection -State Listen -LocalPort %d -ErrorAction SilentlyContinue | "
          "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }") % port
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
    for _ in range(50):
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "@(Get-NetTCPConnection -State Listen -LocalPort %d -ErrorAction SilentlyContinue).Count" % port],
                           capture_output=True, text=True)
        if (r.stdout or "").strip() in ("0", ""):
            return True
        time.sleep(0.2)
    raise SystemExit("!! 포트 %d 를 비우지 못했다" % port)


def boot(app, port):
    freeport(port)
    sp = os.path.join(HERE, "seed_%d.json" % port)
    if os.path.exists(sp):
        os.remove(sp)
    lp = os.path.join(APPDIR, "srv_%d.log" % port)
    pr = subprocess.Popen([P313, os.path.join(HERE, "run_q88_app.py"), os.path.join(APPDIR, app), str(port)],
                          stdout=io.open(lp, "w", encoding="utf-8"), stderr=subprocess.STDOUT, cwd=APPDIR)
    for _ in range(600):
        time.sleep(0.2)
        s = io.open(lp, encoding="utf-8").read() if os.path.exists(lp) else ""
        if "READY" in s and os.path.exists(sp):
            return pr, json.loads(io.open(sp, encoding="utf-8").read())
        if pr.poll() is not None:
            print(s[-2500:])
            raise SystemExit("!! %s(%d) 가 떴다 죽었다" % (app, port))
    raise SystemExit("!! %s(%d) 가 안 떴다" % (app, port))


def kill(*prs):
    for pr in prs:
        try:
            pr.terminate()
        except Exception:
            pass


U = lambda port, path: "http://127.0.0.1:%d%s" % (port, path)


def db(app, sql, args=()):
    """서버가 쓰는 DB 를 **읽기만** 한다."""
    p = os.path.join(APPDIR, app, "data", "knk.db").replace("\\", "/")
    c = sqlite3.connect("file:%s?mode=ro" % p, uri=True, timeout=10)
    c.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in c.execute(sql, args)]
    finally:
        c.close()


def mrow(app, mid):
    return db(app, "SELECT * FROM meetings WHERE id=?", (mid,))[0]


def wait_until(fn, timeout=30.0, step=0.25):
    t0 = time.time()
    v = None
    while time.time() - t0 < timeout:
        try:
            v = fn()
        except Exception:
            v = None
        if v:
            return v
        time.sleep(step)
    return v


def page_for(br, port, uid, w=1280, h=1000):
    ctx = br.new_context(viewport={"width": w, "height": h})
    ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": "http://127.0.0.1:%d" % port}])
    pg = ctx.new_page()
    pg.add_init_script("try{localStorage.setItem('knk_works_install_hint_never','1');}catch(e){}")
    D = {"msgs": []}

    def on_dialog(d):
        if d.type == "beforeunload":
            d.accept()
            return
        D["msgs"].append(d.message)
        d.accept()
    pg.on("dialog", on_dialog)
    errs = []
    pg.on("console", lambda m: errs.append("console: " + m.text[:160]) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:160]))
    return ctx, pg, errs, D


def jget(pg, port, path):
    r = pg.request.get(U(port, path))
    try:
        return r.json()
    except Exception:
        return {}


def post(pg, port, path, body=None):
    r = pg.request.post(U(port, path), data=json.dumps(body or {}), headers={"Content-Type": "application/json"})
    try:
        return r.status, r.json()
    except Exception:
        return r.status, {}


def ffmake(path, secs):
    subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "sine=frequency=440:sample_rate=16000:duration=%s" % secs, "-ac", "1", path], check=True)


# ═══════════════════════ 서버 안 띄움 — 두 벌의 ai_client 를 직접 ═══════════════════════
def load(app, name):
    p = os.path.join(APPDIR, app, "app", "ai_client.py")
    spec = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


class Rec:
    """받아 적는 가짜 OpenAI — fail(kw) 가 예외를 돌려주면 그 호출은 실패한다."""

    def __init__(self, fail=None, text=" 받아쓴 글 "):
        self.calls, self.fail, self.text = [], fail, text

    def mod(self):
        rec = self

        class Tr:
            def create(self, **kw):
                kw2 = dict(kw)
                kw2.pop("file", None)
                rec.calls.append(json.loads(json.dumps(kw2, ensure_ascii=False)))
                e = rec.fail(kw2) if rec.fail else None
                if e:
                    raise e
                return types.SimpleNamespace(text=rec.text)

        class Cl:
            def __init__(self, **_):
                self.audio = types.SimpleNamespace(transcriptions=Tr())
        return types.SimpleNamespace(OpenAI=Cl)


def use(mod, rec, hint=True, key="sk-test-q88-not-a-real-key"):
    mod.openai = rec.mod()
    mod._OPENAI_OK = True
    mod._key_for = (lambda provider: key)
    mod.STT_HINT_ON = hint
    mod.STT_MODEL = "gpt-transcribe"
    mod.STT_FALLBACK_MODEL = "whisper-1"


AUDIO = os.path.join(APPDIR, "q88_fake.m4a")
io.open(AUDIO, "wb").write(b"\0" * 16)
AB = load("app_base", "q88_aic_base")
AN = load("app_new", "q88_aic_new")

print("\n── ① 🔴 「자동 감지」·한국어·베트남어 받아쓰기 요청 = 운영 그대로 ──")
for hint in (True, False):
    for lang in ("", "ko", "vi", "en"):
        rb, rn = Rec(), Rec()
        use(AB, rb, hint)
        use(AN, rn, hint)
        ob = AB.ai_transcribe(AUDIO, lang)
        on = AN.ai_transcribe(AUDIO, lang)
        chk("힌트 %s · 언어 %-4s 요청 글자 그대로" % ("켬" if hint else "끔", lang or "자동"),
            ob == on and rb.calls == rn.calls and len(rn.calls) == 1, (rb.calls, rn.calls))
rb, rn = Rec(), Rec()
use(AB, rb)
use(AN, rn)
chk("낱말 더 얹기(사람 전용) 요청 그대로",
    AB.ai_transcribe(AUDIO, "ko", "", ["추가낱말"]) == AN.ai_transcribe(AUDIO, "ko", "", ["추가낱말"]) and rb.calls == rn.calls)
_gptfail = lambda kw: RuntimeError("server boom") if kw.get("model", "").startswith("gpt") else None
rb, rn = Rec(_gptfail), Rec(_gptfail)
use(AB, rb)
use(AN, rn)
chk("기본 모델 실패 → 예비 모델 흐름 그대로", AB.ai_transcribe(AUDIO, "") == AN.ai_transcribe(AUDIO, "")
    and rb.calls == rn.calls and [c["model"] for c in rn.calls] == ["gpt-transcribe", "whisper-1"], rn.calls)

print("\n── ② 섞인 녹음 30초 조각 요청 = 3차 시험 방식 그대로 ──")
chk("🔴 반대: 운영엔 조각 받아쓰기 함수가 없다", not hasattr(AB, "ai_transcribe_window"))
chk("조각 길이 30초", getattr(AN, "STT_MIX_WIN_SEC", None) == 30)
P0 = AB._stt_prompt("", "", new_model=True).replace(OMIT, "").strip()     # 운영 지시문에서 그 한 문장만 뺀 것(3차 시험과 같은 계산)
KW80 = AB._stt_keywords("")[:80]
chk("지시 = 운영 자동 감지 지시 − 「알아듣기 어려우면 빼라」 한 문장",
    AN._stt_mix_prompt("") == P0 and OMIT not in P0 and OMIT in AB._stt_prompt("", "", new_model=True)
    and "Transcribe verbatim in the language actually spoken" in P0 and "translate" in P0, P0)
chk("다시 받아쓰기 지시 = 3차 시험 글 그대로", AN._STT_MIX_RETRY_PROMPT == RETRY_EXP3)
rn = Rec()
use(AN, rn)
o0 = AN.ai_transcribe_window(AUDIO, "")
chk("첫 조각: 모델·json·지시·낱말 80 · 언어 안 정함 · 앞 글 없음 · 글 다듬음",
    o0 == (True, "받아쓴 글") and rn.calls == [{"model": "gpt-transcribe", "response_format": "json", "prompt": P0,
                                              "extra_body": {"keywords": KW80}}], rn.calls)
prev = "가나다라마바사 " * 30 + "Xin chào anh, hôm nay mình kiểm tra máy nhé."
rn = Rec()
use(AN, rn)
AN.ai_transcribe_window(AUDIO, prev)
chk("다음 조각: 지시 끝에 앞 조각 글 끝 200자", rn.calls and rn.calls[0]["prompt"] == P0 + PREV + prev[-200:]
    and len(prev) > 200, (rn.calls[0]["prompt"][-260:] if rn.calls else None))
rn = Rec()
use(AN, rn)
AN.ai_transcribe_window(AUDIO, prev, retry=True)
chk("다시 받아쓰기: 짧은 지시만 · 낱말·앞 글 없음", rn.calls == [{"model": "gpt-transcribe", "response_format": "json",
                                                  "prompt": RETRY_EXP3}], rn.calls)
rn = Rec()
use(AN, rn, hint=False)
AN.ai_transcribe_window(AUDIO, "")
chk("힌트 끔(KNK_WORKS_STT_HINT=0): 지시는 주고 낱말은 안 줌", rn.calls == [{"model": "gpt-transcribe",
                                                                  "response_format": "json", "prompt": P0}], rn.calls)
rn = Rec(lambda kw: TypeError("Unknown parameter: 'keywords'") if "extra_body" in kw else None)
use(AN, rn)
o = AN.ai_transcribe_window(AUDIO, "")
chk("낱말 거부 → 같은 모델로 낱말 없이 한 번 더(예비로 안 떨어짐)",
    o[0] and [c["model"] for c in rn.calls] == ["gpt-transcribe", "gpt-transcribe"] and "extra_body" not in rn.calls[1]
    and rn.calls[1]["prompt"] == P0, rn.calls)
rn = Rec(_gptfail)
use(AN, rn)
o = AN.ai_transcribe_window(AUDIO, prev)
chk("기본 모델 오류 → 예비 모델(지시문 없이 앞 글 끝 200자만)",
    o[0] and rn.calls[1:] == [{"model": "whisper-1", "prompt": prev[-200:]}], rn.calls)
rn = Rec(_gptfail)
use(AN, rn)
AN.ai_transcribe_window(AUDIO, "")
chk("예비 모델 · 앞 글 없음 → 아무것도 안 줌", rn.calls[1:] == [{"model": "whisper-1"}], rn.calls)
rn = Rec(_gptfail)
use(AN, rn)
AN.ai_transcribe_window(AUDIO, prev, retry=True)
chk("예비 모델 · 다시 받아쓰기 → 앞 글도 안 줌", rn.calls[1:] == [{"model": "whisper-1"}], rn.calls)
rn = Rec(lambda kw: RuntimeError("boom-all"))
use(AN, rn)
o = AN.ai_transcribe_window(AUDIO, "")
chk("둘 다 오류 → 실패 · 마지막 오류 그대로", o[0] is False and o[1].startswith("음성→글자 오류(openai): whisper-1: boom-all"), o)
rn = Rec()
use(AN, rn, key="")
o = AN.ai_transcribe_window(AUDIO, "")
chk("키 없음 → 안내 · 안 부름", o[0] is False and "OpenAI 키가 필요합니다" in o[1] and not rn.calls, o)
rn = Rec()
use(AN, rn)
o = AN.ai_transcribe_window(AUDIO + ".none", "")
chk("파일 없음 → 안내 · 안 부름", o == (False, "음성 파일을 찾을 수 없습니다.") and not rn.calls, o)

print("\n── ③ 베트남어 문장 고르기 ──")
MK = AN._VI_MARK
chk("표시 글자 = 「〔베트남어〕」", MK == "〔베트남어〕")
TALK_KO = ("오늘은 삼성 A라인 2호기 출하 일정을 정리했습니다. 출하는 11월 20일로 하고 3.5미터 컨베이어를 씁니다.\n"
           "## 핵심\n- [결정] 셋업은 25일!\n🎤 [음성 변환]\n박닌 Đông Anh 공장에서 확인했습니다. Dạ.")
for t in (TALK_KO, "", "   ", "회의 메모만 있습니다", "Bắc Ninh 법인"):
    out = AN._mark_vietnamese(t)
    chk("한국어만(%s…) → 같은 글 그대로 · 0" % (t[:14].replace("\n", " ") or "빈 글"), out[1] == 0 and out[0] is t, out)
T = ("고객사 방문 메모\n\n🎤 [음성 변환]\nAnh ơi, hôm nay kiểm tra máy số hai nhé. Giá là 3.5 triệu đồng. 네, 알겠습니다. Vâng ạ.\n"
     "박닌 Đông Anh 공장에서 확인했습니다.\nDạ.\nAnh Kim nói là 견적 gửi trước thứ sáu nhé.")
WANT = ("고객사 방문 메모\n\n🎤 [음성 변환]\n" + MK + "Anh ơi, hôm nay kiểm tra máy số hai nhé. " + MK
        + "Giá là 3.5 triệu đồng. 네, 알겠습니다. " + MK + "Vâng ạ.\n박닌 Đông Anh 공장에서 확인했습니다.\nDạ.\n" + MK
        + "Anh Kim nói là 견적 gửi trước thứ sáu nhé.")
out = AN._mark_vietnamese(T)
chk("섞인 글: 베트남어 문장 4개만 표시(한국어 문장·지명 하나·「Dạ.」 한 마디는 아님 · 한국어 낱말 섞인 베트남어 문장은 표시)",
    out == (WANT, 4), out)
chk("「3.5」 숫자 안에서 안 자른다", "Giá là 3.5 triệu đồng." in out[0] and "3." + MK not in out[0])
chk("표시 빼면 원문과 글자 그대로", out[0].replace(MK, "") == T)
#  받아쓴 글은 운영 헛말 정리(_stt_strip_hallucination)를 거치며 「3.5」가 「3. 5」로 벌어져 들어온다(⑨에서 실측)
o = AN._mark_vietnamese("Giá vận chuyển là 3. 5 triệu đồng một chuyến. 네, 알겠습니다.")
chk("「3. 5」(벌어진 숫자)도 한 문장으로 — 숫자 가운데에 표시가 끼지 않는다",
    o == (MK + "Giá vận chuyển là 3. 5 triệu đồng một chuyến. 네, 알겠습니다.", 1), o)
o = AN._mark_vietnamese("Hôm nay có 3. Ngày mai sẽ có 5 cái máy mới.")
chk("숫자로 끝난 문장 뒤 글자로 시작하는 문장은 따로", o == (MK + "Hôm nay có 3. " + MK + "Ngày mai sẽ có 5 cái máy mới.", 2), o)
nfd = unicodedata.normalize("NFD", "Vâng ạ, cảm ơn anh nhiều.")
o = AN._mark_vietnamese(nfd)
chk("NFD(글자 쪼갠 꼴) 베트남어도 고른다 · 글은 그대로", o == (MK + nfd, 1), o)

print("\n── ④ 🔴 한국어만 → AI 에 가는 것이 운영과 글자 그대로 ──")
CAP = {}


def cap(tag, resp):
    def f(user_text, system="", **kw):
        CAP.setdefault(tag, []).append({"user": user_text, "system": system, "max_tokens": kw.get("max_tokens"),
                                        "temperature": kw.get("temperature"), "timeout": kw.get("timeout_sec")})
        return (True, resp)
    return f


PLAIN = json.dumps({"title": "출하 일정", "summary": "## 핵심\n출하일을 정했다.\n\n## 납기\n- v_ 이상한 줄 〔베트남어〕 그대로",
                    "decisions": [{"who": "", "what": "v_[결정] 이상", "due": ""}],
                    "actions": [{"assignee": "김한국", "task": "출하 준비", "due": "2026-11-19"}]}, ensure_ascii=False)
SEEDT = "고객사 방문 — 검사기 컨셉 협의 (이음 회의 메모)"
KBODY = SEEDT + "\n\n🎤 [음성 변환]\n" + TALK_KO
CTX = "회의 제목: 시험 회의\n날짜: 2026-10-19 (월)\n참석자: 김한국, 최민수"
for fn, ctx_ in (("ai_extract_meeting", CTX), ("ai_extract_note", "메모 날짜: 2026-10-19 (월)")):
    CAP.clear()
    AB.ai_chat, AN.ai_chat = cap("b", PLAIN), cap("n", PLAIN)
    rb_ = getattr(AB, fn)(KBODY, context=ctx_)
    so = io.StringIO()
    with contextlib.redirect_stdout(so):
        rn_ = getattr(AN, fn)(KBODY, context=ctx_)
    chk("%s: 지시문·원문·답 길이·온도·기다림 글자 그대로" % fn, CAP.get("b") == CAP.get("n") and len(CAP["n"]) == 1,
        (CAP.get("b"), CAP.get("n")))
    chk("%s: 답도 운영과 같다(손보기 안 함 — 이상한 「v_ 」·표시도 그대로)" % fn, rb_ == rn_ and "〔베트남어〕" in rn_[1]["summary"], rn_)
    chk("%s: 기록 안 남김" % fn, "[VI-MARK]" not in so.getvalue(), so.getvalue())

print("\n── ⑤ 베트남어가 있으면 → 「v_」 규칙 · 표시한 원문 · 답 손보기 ──")
VI_W = ("Anh ơi, hôm nay mình kiểm tra máy số hai trước khi giao hàng nhé. Giá vận chuyển là 3.5 triệu đồng một chuyến. "
        "Bên khách hàng muốn nhận hàng vào thứ sáu tuần sau, nên phải đóng gói xong trước thứ năm.")
MBODY = SEEDT + "\n\n🎤 [음성 변환]\n" + VI_W + "\n네, 알겠습니다. 출하 전에 2호기 검사를 한 번 더 하겠습니다."
LEAK = json.dumps({"title": "출하", "summary": ("## 핵심\n출하 일정을 정했다.\n\n## 납기\n- 〔베트남어〕2호기 출하는 다음 주 금요일로 한다\n"
                                              "- v_[결정] 포장은 목요일까지 마친다\n- v_ 운송비는 3.5백만 동 [확인 필요]\n"
                                              "- [결정] 셋업은 25일부터 시작한다\n- v_[내부 방침] 운송비는 구매팀이 본다"),
                   "decisions": [{"who": "", "what": "v_(내부 방침) 포장은 목요일까지 마친다", "due": ""},
                                 {"who": "", "what": "셋업은 25일부터 시작한다", "due": ""}],
                   "actions": [{"assignee": "", "task": "〔베트남어〕 2호기 검사 결과를 고객사에 공유한다", "due": ""},
                               {"assignee": "", "task": "운송비를 거래처와 다시 확인한다", "due": ""}]}, ensure_ascii=False)
WANT_SUM = ("## 핵심\n출하 일정을 정했다.\n\n## 납기\n- v_2호기 출하는 다음 주 금요일로 한다\n- [결정] v_포장은 목요일까지 마친다\n"
            "- v_운송비는 3.5백만 동 [확인 필요]\n- [결정] 셋업은 25일부터 시작한다\n- [내부 방침] v_운송비는 구매팀이 본다")
marked, nmark = AN._mark_vietnamese(MBODY)
chk("이 원문의 베트남어 문장 = 3", nmark == 3, nmark)
for fn, ctx_, what in (("ai_extract_meeting", CTX, "회의록"), ("ai_extract_note", "메모 날짜: 2026-10-19 (월)", "음성 메모")):
    CAP.clear()
    AB.ai_chat, AN.ai_chat = cap("b", LEAK), cap("n", LEAK)
    rb_ = getattr(AB, fn)(MBODY, context=ctx_)
    so = io.StringIO()
    with contextlib.redirect_stdout(so):
        rn_ = getattr(AN, fn)(MBODY, context=ctx_)
    b0, n0 = CAP["b"][0], CAP["n"][0]
    chk("%s: 지시문 = 운영 지시문 + 빈 줄 + 「v_」 규칙(그 밖은 그대로)" % fn, n0["system"] == b0["system"] + "\n\n" + AN._VI_RULE, n0["system"][-300:])
    chk("%s: 원문 = 표시한 글(운영은 원문 그대로)" % fn, n0["user"] == marked and b0["user"] == MBODY.strip())
    bud = AN._mtg_budget(len(marked)) if fn == "ai_extract_meeting" else AN._note_budget(len(marked))
    chk("%s: 답 길이 = 표시한 글 길이로 셈" % fn, n0["max_tokens"] == bud, (n0["max_tokens"], bud))
    chk("%s: 정리 손보기 — 새어 나온 표시 → v_ · 「v_ 」 → v_ · [결정]/[내부 방침] 앞 → 뒤" % fn,
        rn_[0] and rn_[1]["summary"] == WANT_SUM, rn_[1].get("summary"))
    chk("%s: 🔴 반대: 운영은 손보지 않는다" % fn, "〔베트남어〕" in rb_[1]["summary"])
    if fn == "ai_extract_meeting":
        chk("결정: 「v_(내부 방침) …」 → 「(내부 방침) v_…」 · 한국어 결정 그대로",
            [d["what"] for d in rn_[1]["decisions"]] == ["(내부 방침) v_포장은 목요일까지 마친다", "셋업은 25일부터 시작한다"],
            rn_[1]["decisions"])
        chk("할 일: 새어 나온 표시 → v_(띄어쓰기 없이) · 한국어 할 일 그대로",
            [a["task"] for a in rn_[1]["actions"]] == ["v_2호기 검사 결과를 고객사에 공유한다", "운송비를 거래처와 다시 확인한다"],
            rn_[1]["actions"])
        want_log = "[VI-MARK] 회의록: 베트남어 문장 3개 표시 → 정리에 v_ 6곳"
    else:
        chk("음성 메모 답 모양 그대로(summary·title 둘만)", sorted(rn_[1]) == ["summary", "title"], sorted(rn_[1]))
        want_log = "[VI-MARK] 음성 메모: 베트남어 문장 3개 표시 → 정리에 v_ 4곳"
    chk("%s: 제목은 손대지 않음" % fn, rn_[1]["title"] == "출하")
    chk("%s: 기록 = 숫자만(「%s」 · 글은 안 찍는다)" % (fn, want_log), so.getvalue().strip() == want_log
        and "Anh" not in so.getvalue() and "포장" not in so.getvalue(), so.getvalue())

print("\n── ⑥ 운영 지시문·낱말 그대로 · 규칙 글 · main.py 바뀐 자리 ──")
chk("회의록 정리 지시문 그대로", AN._MEETING_EXTRACT_SYSTEM == AB._MEETING_EXTRACT_SYSTEM)
chk("음성 메모 정리 지시문 그대로", AN._NOTE_EXTRACT_SYSTEM == AB._NOTE_EXTRACT_SYSTEM)
chk("회사 맥락 그대로", AN._KNK_MEETING_CONTEXT == AB._KNK_MEETING_CONTEXT)
chk("받아쓰기 지시(언어·말투 모두) 그대로", all(AN._stt_prompt(l, d, nm) == AB._stt_prompt(l, d, nm)
                                         for l in ("", "ko", "vi", "en") for d in ("", "gyeongsang", "vi_north")
                                         for nm in (True, False)))
chk("힌트 낱말 그대로", all(AN._stt_keywords(l) == AB._stt_keywords(l) for l in ("", "ko", "vi", "en")))
R_ = AN._VI_RULE
for frag in ("「v_」", "「〔베트남어〕」로 시작하는 문장은 베트남어로 말한 것", "한국어로 정리", "띄어쓰기 없이",
             "「## 핵심」 문단과 title 에는 붙이지 않는다", "[결정]", "「(내부 방침)」", "한국어로 말한 내용에는 붙이지 않는다",
             "표시 자체는 정리에 옮기지 않는다"):
    chk("규칙 글에 「%s」" % frag, frag in R_)
chk("규칙 글에 지어낸 회의 내용 보기 없음(모양만)", "<내용>" in R_ and "박닌" not in R_ and "출하" not in R_)
srcn = io.open(os.path.join(APPDIR, "app_new", "app", "main.py"), encoding="utf-8").read()
srcb = io.open(os.path.join(APPDIR, "app_base", "app", "main.py"), encoding="utf-8").read()
chk("받는 말 검사 두 곳(회의록·음성 메모)에 mix", srcn.count('in ("ko", "vi", "en", "mix") else ""') == 2
    and srcb.count('in ("ko", "vi", "en") else ""') == 2)
chk("🔴 반대: 운영 main.py 엔 mix 가 없다", '"mix"' not in srcb)
chk("섞임 길은 한 곳 · 그 밖은 운영 그대로(elif)", srcn.count('if lang == "mix":') == 1
    and srcn.count("elif os.path.getsize(disk) <= _STT_MAX_BYTES:") == 1)
chk("통째 받아쓰기 부르는 곳 수 그대로(2)", srcn.count("ai_client.ai_transcribe(") == srcb.count("ai_client.ai_transcribe(") == 2)
chk("30분 구간 나누기 그대로(조각 길이만 받게)", 'str(seg_sec or _STT_SEG_SEC)' in srcn
    and "def _stt_split(disk: str, workdir: str, seg_sec: int = 0):" in srcn)
chk("헛말 정리(_stt_strip_hallucination) 그대로", srcn.count("def _stt_strip_hallucination(") == 1
    and srcn.split("def _stt_strip_hallucination(")[1].split("\ndef ")[0] == srcb.split("def _stt_strip_hallucination(")[1].split("\ndef ")[0])


def helpers(app):
    """그 앱의 main.py 에서 헛말 정리 함수만 꺼낸다(앱은 띄우지 않는다) — 받아쓴 글이 원문에 들어가는 모양을 계산하려고."""
    import ast
    tree = ast.parse(io.open(os.path.join(APPDIR, app, "app", "main.py"), encoding="utf-8").read())
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name == "_stt_strip_hallucination")
            or (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in ("_STT_REPEAT_MIN", "_STT_REPEAT_MAXLEN")
                                                  for t in n.targets))]
    ns = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), "main.py", "exec"), ns)
    return ns


STRIP = helpers("app_new")["_stt_strip_hallucination"]
mdh = lambda app, rel: hashlib.md5(io.open(os.path.join(APPDIR, app, "app", rel), "rb").read()).hexdigest()
for rel in ("templates/meeting_doc.html", "templates/_v5_partials/knk_md_lite.html"):
    chk("%s 그대로(「v_」는 보통 글자 — 그리는 규칙 안 바꿈)" % rel, mdh("app_base", rel) == mdh("app_new", rel))
os.remove(AUDIO)

# ═══════════════════════ 진짜 서버 + 진짜 브라우저 ═══════════════════════
WAV120 = os.path.join(HERE, "q88_120s.wav")     # run_q88_app.py 가 A1~A3 녹음으로 복사한다
WAV95 = os.path.join(APPDIR, "q88_95s.wav")
WAVX = [WAV120, WAV95]
ffmake(WAV120, "120.4")
ffmake(WAV95, "95")
PART = lambda i: "part_%03d.mp3" % i
STLANG_JS = """() => Array.from(document.querySelectorAll('select.sttLangPick')).map(function(s){
  return { id: s.id, v: s.value, opts: Array.from(s.options).map(function(o){ return [o.value, o.textContent.trim()]; }),
           note: (s.parentNode.querySelector('.mf-hint') || {}).textContent }; })"""
VNLANG_JS = """() => { var s = document.getElementById('vnLang'); return s ? Array.from(s.options).map(function(o){
  return [o.value, o.textContent.trim()]; }) : null; }"""
pb = pn = None


def pick_mix(pg, v="mix"):
    try:
        pg.select_option("#sttLang", v, timeout=3000)
    except Exception:
        pg.evaluate("(v) => document.querySelectorAll('select.sttLangPick').forEach(function(s){ s.value = v; })", v)
    return pg.evaluate("() => Array.from(document.querySelectorAll('select.sttLangPick')).map(function(s){ return s.value; })")


def watch_stt(pg, port, mid, timeout=60):
    """받아쓰기가 끝날 때까지 상태를 자주 물어 진행 글을 모은다."""
    seen, t0, st = [], time.time(), {}
    while time.time() - t0 < timeout:
        st = jget(pg, port, "/api/meeting/%d/stt-status" % mid)
        p = st.get("progress") or ""
        if p and p not in seen:
            seen.append(p)
        if st.get("state") in ("done", "error"):
            break
        time.sleep(0.12)
    return st, seen


try:
    pb, sb = boot("app_base", PB)
    pn, sn = boot("app_new", PN)
    IB, IN = sb["ids"], sn["ids"]
    NB, NN = sb["notes"], sn["notes"]
    print("\n운영 그대로 %d · 새것 %d · 회의 %s · 메모 %s" % (PB, PN, json.dumps(IN, ensure_ascii=False), NN))
    chk("새것 서버엔 조각 받아쓰기 · 운영엔 없음", sn["has_window"] is True and sb["has_window"] is False)
    VI_RULE = AN._VI_RULE
    #  원문에 들어가는 모양 = 조각 글을 줄로 이은 뒤 운영 헛말 정리를 거친 것(문장마다 끊어 띄어쓰기로 다시 잇는다 — 운영 그대로)
    EXP_TXT = STRIP(sn["vi_w"] + "\n" + sn["ko_w1"] + "\n" + sn["ko_w2"])[0]
    print("    (원문에 들어갈 모양 — 운영 헛말 정리 뒤: 「%s…」)" % EXP_TXT[:70])

    with sync_playwright() as p:
        br = p.chromium.launch()
        cb, gb, eb, DB_ = page_for(br, PB, sb["me"])
        cn, gn, en, DN = page_for(br, PN, sn["me"])

        # ═══════════ ⑦ 헛말 판정 도우미 ═══════════
        print("\n── ⑦ 헛말 판정(30초 조각) ──")
        J = lambda t: jget(gn, PN, "/__test/junk?t=" + urllib.parse.quote(t)).get("junk")
        for t, want, why in ((sn["kw_junk"], True, "힌트 낱말 그대로"), (sn["hallu_w"], True, "「시청해 주셔서 감사합니다」뿐"),
                             ("I I I I I I I I I I", True, "같은 말 되풀이"), ("ご視聴ありがとうございました", True, "외국 글자만"),
                             ("시청해 주셔서 감사합니다. 네.", True, "헛말 + 한 글자"), ("", False, "빈칸(다시 받아쓰기는 따로)"),
                             (sn["ko_w1"], False, "한국어 말"), (sn["vi_w"], False, "베트남어 말"),
                             ("시청해 주셔서 감사합니다. 그럼 출하는 20일로 하겠습니다.", False, "헛말 + 진짜 말"),
                             ("검사, 금형", False, "낱말 둘이지만 진짜 말일 수도 — 「검사」는 힌트에 없음"),
                             ("케이엔케이. 하이스트. 사출. 금형. 지그. 포고핀. 프로브핀. 비전검사.", True,
                              "힌트 낱말 마침표 나열(3차 시험 4분52초 메모에서 실제로 나옴)"),
                             (KW_SLASH, True, "힌트 낱말 빗금·마침표·쉼표 섞어 나열(시연 18분 메모에서 실제로 나옴)"),
                             ("사출 금형 지그 다 확인했어요", False, "힌트 낱말 셋 + 진짜 말"),
                             ("사출 금형 납기 문제로 다음 주에 다시 회의하기로 했습니다", False, "힌트 낱말 든 진짜 문장"),
                             ("금형비, 사출.", False, "힌트 낱말 둘뿐(셋 미만 — 남김)")):
            chk("%s → %s" % (why, "버림" if want else "남김"), J(t) is want, (t, J(t)))
        chk("🔴 반대: 운영엔 이 도우미가 없다", jget(gb, PB, "/__test/junk?t=x").get("have") is False)

        # ═══════════ ⑧ 화면 ═══════════
        print("\n── ⑧ 화면 — 「한국어+베트남어 섞임」 선택지 ──")
        gn.goto(U(PN, "/meetings/%d" % IN["U1"]), wait_until="domcontentloaded")
        gn.wait_for_selector("select.sttLangPick", state="attached", timeout=20000)
        Sn = gn.evaluate(STLANG_JS)
        chk("회의록: 고르는 칸 두 자리(큰 올리기 · 접힌 다시 하기)", [s["id"] for s in Sn] == ["sttLang", "sttLangRedo"], Sn)
        chk("선택지 = 자동 감지 · 한국어 · 베트남어 · 한국어+베트남어 섞임(두 자리 같음)",
            all(s["opts"] == [["", "자동 감지 (기본)"], ["ko", "한국어"], ["vi", "베트남어"], ["mix", MIX_KO]] for s in Sn), Sn)
        chk("기본은 그대로 자동 감지", all(s["v"] == "" for s in Sn))
        chk("안내 글(한국어) 바뀜", all((s["note"] or "").strip() == NOTE_KO for s in Sn), [s["note"] for s in Sn])
        try:
            gn.locator("#sttLang").scroll_into_view_if_needed(timeout=3000)
        except Exception:
            pass
        gn.screenshot(path=os.path.join(SHOTS, "q88_form_options_ko.png"), full_page=False)
        gb.goto(U(PB, "/meetings/%d" % IB["U1"]), wait_until="domcontentloaded")
        gb.wait_for_selector("select.sttLangPick", state="attached", timeout=20000)
        Sb = gb.evaluate(STLANG_JS)
        chk("🔴 반대: 운영 선택지엔 섞임이 없다", all([o[0] for o in s["opts"]] == ["", "ko", "vi"] for s in Sb), Sb)
        cv, gv, ev, DV = page_for(br, PN, sn["vnu"])
        gv.goto(U(PN, "/meetings/%d" % IN["W1"]), wait_until="domcontentloaded")
        gv.wait_for_selector("select.sttLangPick", state="attached", timeout=20000)
        Sv = gv.evaluate(STLANG_JS)
        chk("베트남어 화면: 「%s」" % MIX_VI, all(s["opts"][-1] == ["mix", MIX_VI] and len(s["opts"]) == 4 for s in Sv), Sv)
        chk("베트남어 화면: 안내 글 바뀜", all((s["note"] or "").strip() == NOTE_VI for s in Sv), [s["note"] for s in Sv])
        gv.screenshot(path=os.path.join(SHOTS, "q88_form_options_vi.png"), full_page=False)
        gn.goto(U(PN, "/meetings/%d?sttlang=mix" % IN["U1"]), wait_until="domcontentloaded")
        gn.wait_for_selector("select.sttLangPick", state="attached", timeout=20000)
        chk("주소 sttlang=mix → 두 자리 모두 섞임으로", [s["v"] for s in gn.evaluate(STLANG_JS)] == ["mix", "mix"])
        gn.goto(U(PN, "/meetings/%d?sttlang=zz" % IN["U1"]), wait_until="domcontentloaded")
        gn.wait_for_selector("select.sttLangPick", state="attached", timeout=20000)
        chk("주소 sttlang=zz(모르는 말) → 그대로 자동", [s["v"] for s in gn.evaluate(STLANG_JS)] == ["", ""])
        gb.goto(U(PB, "/meetings/%d?sttlang=mix" % IB["U1"]), wait_until="domcontentloaded")
        gb.wait_for_selector("select.sttLangPick", state="attached", timeout=20000)
        chk("🔴 반대: 운영은 sttlang=mix 를 안 받는다", [s["v"] for s in gb.evaluate(STLANG_JS)] == ["", ""])
        gn.goto(U(PN, "/voice-notes/new"), wait_until="domcontentloaded")
        gn.wait_for_selector("#vnLang", timeout=20000)
        chk("음성 메모 「쓰는 말」 = 자동 · 한국어 · 베트남어 · 섞임", gn.evaluate(VNLANG_JS) == [
            ["", "자동 감지 (기본)"], ["ko", "한국어"], ["vi", "베트남어"], ["mix", MIX_KO]], gn.evaluate(VNLANG_JS))
        gb.goto(U(PB, "/voice-notes/new"), wait_until="domcontentloaded")
        gb.wait_for_selector("#vnLang", timeout=20000)
        chk("🔴 반대: 운영 음성 메모엔 섞임이 없다", [o[0] for o in gb.evaluate(VNLANG_JS)] == ["", "ko", "vi"])

        # ═══════════ ⑨ 회의록 녹음 올리기(섞임) ═══════════
        print("\n── ⑨ 회의록 녹음 올리기 — 「한국어+베트남어 섞임」 ──")
        jget(gn, PN, "/__test/tr?reset=1")
        nc0 = len(jget(gn, PN, "/__test/chat")["calls"])
        gn.goto(U(PN, "/meetings/%d" % IN["U1"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#redoTools #recFile", state="attached", timeout=20000)
        chk("섞임을 고름(보이는 큰 올리기 자리)", pick_mix(gn)[:1] == ["mix"])
        gn.locator("#redoTools #recFile").set_input_files(WAV120)
        st9, seen9 = watch_stt(gn, PN, IN["U1"], 90)
        done9 = wait_until(lambda: "모두 끝났습니다" in gn.inner_text("#pipeSteps"), 90)
        r9 = mrow("app_new", IN["U1"])
        tr9 = jget(gn, PN, "/__test/tr")["tr"]
        files9 = [t["file"] for t in tr9]
        chk("받아쓰기 끝 · 정리까지 「모두 끝났습니다」", st9.get("state") == "done" and bool(done9), (st9, gn.inner_text("#pipeSteps")))
        chk("원문 = 메모 + 🎤 [음성 변환] + 베트남어 · 한국어(살린 조각) · 한국어 — 헛말 조각은 빠짐",
            r9["body"] == sn["seed"] + "\n\n🎤 [음성 변환]\n" + EXP_TXT, r9["body"])
        chk("보낸 조각 = 0 · 1(빈칸) · 1(다시) · 2(헛말) · 2(다시) · 3 — 자투리 4(0.4초)는 안 보냄",
            files9 == [PART(0), PART(1), PART(1), PART(2), PART(2), PART(3)], files9)
        chk("조각 크기 = 30초 × 64kbps(약 240KB)", all(200000 < t["size"] < 260000 for t in tr9), [t["size"] for t in tr9])
        k9 = [t["kw"] for t in tr9]
        chk("1번째: 앞 글 없음 · 낱말 80", k9 and k9[0] == {"model": "gpt-transcribe", "response_format": "json", "prompt": P0,
                                                    "extra_body": {"keywords": KW80}}, k9[:1])
        chk("2번째: 앞 조각(베트남어) 글을 이어 준다", len(k9) > 1 and k9[1]["prompt"] == P0 + PREV + sn["vi_w"][-200:])
        chk("빈칸 → 다시: 짧은 지시 · 낱말 없음", len(k9) > 2 and k9[2] == {"model": "gpt-transcribe", "response_format": "json",
                                                           "prompt": RETRY_EXP3}, k9[2:3])
        chk("3번째: 앞 글 = 다시 받아 살린 한국어", len(k9) > 3 and k9[3]["prompt"] == P0 + PREV + sn["ko_w1"][-200:])
        chk("헛말 → 다시(짧은 지시) → 또 헛말 → 버림", len(k9) > 4 and k9[4]["prompt"] == RETRY_EXP3
            and tr9[3]["text"] == sn["kw_junk"] and tr9[4]["text"] == sn["hallu_w"])
        chk("4번째: 버린 조각은 앞 글이 되지 않는다(살린 한국어 그대로)", len(k9) > 5 and k9[5]["prompt"] == P0 + PREV + sn["ko_w1"][-200:])
        chk("모두 기본 모델 · 언어는 안 정함", all(k["model"] == "gpt-transcribe" and "languages" not in (k.get("extra_body") or {})
                                         for k in k9))
        sub = [s for s in seen9 if "30초 조각" in s]
        chk("진행 글 「30초 조각 5개 중 N번째」(자투리는 진행에도 안 나옴)",
            sub and all(s.startswith("30초 조각 5개 중 ") for s in sub) and "30초 조각 5개 중 5번째" not in seen9, seen9)
        chk("조각 담았던 임시 폴더를 지웠다", jget(gn, PN, "/__test/mixdirs")["left"] == [], jget(gn, PN, "/__test/mixdirs"))
        ch9 = jget(gn, PN, "/__test/chat")["calls"][nc0:]
        chk("정리 AI 한 번 · 원문에 베트남어 표시 3곳 · 지시문 끝 = 「v_」 규칙", len(ch9) == 1 and ch9[0]["user"].count("〔베트남어〕") == 3
            and ch9[0]["system"].endswith("\n\n" + VI_RULE), [(c["user"][:80], c["system"][-80:]) for c in ch9])
        r9 = mrow("app_new", IN["U1"])
        L9 = (r9["summary"] or "").split("\n")
        chk("저장된 정리: v_ 손봄(표시 → v_ · 「v_ 」 → v_ · [결정] 뒤로) · 한국어 줄 그대로",
            "- v_2호기 출하는 다음 주 금요일로 한다" in L9 and "- [결정] v_포장은 목요일까지 마친다" in L9
            and "- v_운송비는 3.5백만 동으로 들었다 [확인 필요]" in L9 and "- [결정] 셋업은 25일부터 시작한다" in L9
            and "〔베트남어〕" not in r9["summary"], r9["summary"])
        d9 = [x["what"] for x in db("app_new", "SELECT what FROM meeting_decisions WHERE meeting_id=? AND source='ai' ORDER BY id",
                                    (IN["U1"],))]
        a9 = [x["task"] for x in db("app_new", "SELECT task FROM meeting_actions WHERE meeting_id=? AND source='ai' ORDER BY id",
                                    (IN["U1"],))]
        chk("저장된 결정: 「(내부 방침) v_…」", d9 == ["(내부 방침) v_포장은 목요일까지 마친다", "셋업은 25일부터 시작한다"], d9)
        chk("저장된 할 일: 「v_…」", a9 == ["v_2호기 검사 결과를 고객사에 공유한다", "운송비를 거래처와 다시 확인한다"], a9)
        gn.goto(U(PN, "/meetings/%d" % IN["U1"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#mtgSummary.mdl", timeout=20000)
        h9 = gn.inner_html("#mtgSummary")
        chk("화면 정리: 「[결정]」 색 글씨 뒤에 v_ · 밑줄은 기울임이 아니다",
            '<span class="tg tg-dec">[결정]</span> v_포장은' in h9 and "v_2호기 출하는" in h9 and "<em>" not in h9, h9[:600])
        gn.locator("#mtgSummary").scroll_into_view_if_needed()
        gn.screenshot(path=os.path.join(SHOTS, "q88_meeting_summary_v.png"), full_page=False)
        gn.goto(U(PN, "/meetings/%d/doc" % IN["U1"]), wait_until="domcontentloaded")
        hd = gn.content()
        chk("회의록 양식: 정리 줄 · 결정에 v_ 그대로", "v_2호기 출하는 다음 주 금요일로 한다" in hd
            and '<span class="tg tg-dec">[결정]</span> v_포장은' in hd and "(내부 방침) v_포장은" in hd)
        gn.screenshot(path=os.path.join(SHOTS, "q88_meeting_doc_v.png"), full_page=True)
        lg = io.open(os.path.join(APPDIR, "srv_%d.log" % PN), encoding="utf-8").read()
        chk("서버 기록: 「[VI-MARK] 회의록: 베트남어 문장 3개 표시 → 정리에 v_ 5곳」 · 회의 글은 안 찍힘",
            "[VI-MARK] 회의록: 베트남어 문장 3개 표시 → 정리에 v_ 5곳" in lg and "Anh ơi" not in lg and "포장은" not in lg,
            [ln for ln in lg.splitlines() if "VI-MARK" in ln])

        # ═══════════ ⑩ 자동 감지 · API ═══════════
        print("\n── ⑩ 「자동 감지」 녹음 올리기 = 운영과 같은 요청 · API ──")
        K10 = {}
        for nm, pg_, port, ids, app in (("new", gn, PN, IN, "app_new"), ("base", gb, PB, IB, "app_base")):
            jget(pg_, port, "/__test/tr?reset=1")
            pg_.goto(U(port, "/meetings/%d" % ids["U2"]), wait_until="domcontentloaded")
            pg_.wait_for_selector("#redoTools #recFile", state="attached", timeout=20000)
            pg_.locator("#redoTools #recFile").set_input_files(WAV120)
            wait_until(lambda: "모두 끝났습니다" in pg_.inner_text("#pipeSteps"), 90)
            K10[nm] = (jget(pg_, port, "/__test/tr")["tr"], mrow(app, ids["U2"])["body"])
        t_n, t_b = K10["new"][0], K10["base"][0]
        chk("자동 감지: 통째 한 번(조각 없음)", len(t_n) == 1 and not t_n[0]["file"].startswith("part_"), [t["file"] for t in t_n])
        chk("🔴 자동 감지 요청 = 운영과 글자 그대로", len(t_b) == 1 and t_n[0]["kw"] == t_b[0]["kw"], (t_n, t_b))
        chk("원문도 운영과 같다", K10["new"][1] == K10["base"][1] == sn["seed"] + "\n\n🎤 [음성 변환]\n" + sn["talk"])
        A10 = {}
        for key, lang in (("A1", "mix"), ("A2", "zz"), ("A3", "MIX")):
            jget(gn, PN, "/__test/tr?reset=1")
            s_, d_ = post(gn, PN, "/api/meeting/%d/transcribe" % IN[key], {"lang": lang})
            st_, _ = watch_stt(gn, PN, IN[key], 60)
            A10[key] = (s_, d_, st_.get("state"), [t["file"] for t in jget(gn, PN, "/__test/tr")["tr"]])
        chk("API lang=mix → 30초 조각", A10["A1"][2] == "done" and A10["A1"][3][:1] == [PART(0)] and len(A10["A1"][3]) == 6, A10["A1"])
        chk("API lang=zz(모르는 말) → 자동 감지(통째)", A10["A2"][2] == "done" and len(A10["A2"][3]) == 1
            and not A10["A2"][3][0].startswith("part_"), A10["A2"])
        chk("API lang=MIX(대문자) → 자동 감지(정확히 mix 만)", A10["A3"][2] == "done" and len(A10["A3"][3]) == 1, A10["A3"])
        chk("API 섞임 원문 = 화면으로 올린 것과 같다", mrow("app_new", IN["A1"])["body"] == sn["seed"] + "\n\n🎤 [음성 변환]\n" + EXP_TXT)
        jget(gb, PB, "/__test/tr?reset=1")
        post(gb, PB, "/api/meeting/%d/transcribe" % IB["A1"], {"lang": "mix"})
        stb, _ = watch_stt(gb, PB, IB["A1"], 60)
        tb10 = jget(gb, PB, "/__test/tr")["tr"]
        chk("🔴 반대: 운영은 mix 를 모르고 자동 감지로 통째 한 번", stb.get("state") == "done" and len(tb10) == 1
            and not tb10[0]["file"].startswith("part_") and "languages" not in (tb10[0]["kw"].get("extra_body") or {}), tb10)

        # ═══════════ ⑪ 실패 ═══════════
        print("\n── ⑪ 조각 하나 실패 → 통째 실패 · ffmpeg 없음 ──")
        jget(gn, PN, "/__test/mix?sc=fail3")
        jget(gn, PN, "/__test/tr?reset=1")
        gn.goto(U(PN, "/meetings/%d" % IN["U3"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#redoTools #recFile", state="attached", timeout=20000)
        pick_mix(gn)
        gn.locator("#redoTools #recFile").set_input_files(WAV120)
        st11, _ = watch_stt(gn, PN, IN["U3"], 60)
        want11 = "30초 조각 5개 중 3번째(약 1분부터)를 글자로 바꾸지 못했습니다 — 음성→글자 오류(openai): whisper-1: boom-q88"
        chk("상태 = 오류 · 몇 번째 조각 · 몇 분부터 · 원래 오류", st11.get("state") == "error" and st11.get("error") == want11, st11)
        got11 = wait_until(lambda: "30초 조각 5개 중 3번째(약 1분부터)" in gn.inner_text("#pipeSteps"), 30)
        chk("화면 진행 칸에 그 안내", bool(got11), gn.inner_text("#pipeSteps"))
        chk("원문 그대로(반쪽 받아쓰기를 붙이지 않음)", mrow("app_new", IN["U3"])["body"] == sn["seed"])
        tr11 = jget(gn, PN, "/__test/tr")["tr"]
        chk("실패한 조각은 예비 모델로도 한 번(앞 글만) · 그 뒤 조각은 안 보냄",
            [t["file"] for t in tr11] == [PART(0), PART(1), PART(1), PART(2), PART(2)]
            and tr11[-1]["kw"] == {"model": "whisper-1", "prompt": sn["ko_w1"][-200:]}, [(t["file"], t["kw"].get("model")) for t in tr11])
        chk("조각 폴더 지움(실패해도)", jget(gn, PN, "/__test/mixdirs")["left"] == [])
        gn.screenshot(path=os.path.join(SHOTS, "q88_fail_piece.png"), full_page=False)
        jget(gn, PN, "/__test/mix?sc=script")
        off = jget(gn, PN, "/__test/noff?on=1")
        chk("(시험 준비) 서버가 ffmpeg 를 못 찾게 함", off.get("ffmpeg") == "", off)
        jget(gn, PN, "/__test/tr?reset=1")
        gn.goto(U(PN, "/meetings/%d" % IN["U4"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#redoTools #recFile", state="attached", timeout=20000)
        pick_mix(gn)
        gn.locator("#redoTools #recFile").set_input_files(WAV120)
        st11b, _ = watch_stt(gn, PN, IN["U4"], 60)
        chk("ffmpeg 없음 → 「섞임」 안내(25MB 이야기 아님) · 안 보냄", st11b.get("state") == "error"
            and st11b.get("error") == FFMPEG_ERR and not jget(gn, PN, "/__test/tr")["tr"], st11b)
        on = jget(gn, PN, "/__test/noff?on=0")
        chk("(시험 정리) ffmpeg 되돌림", bool(on.get("ffmpeg")), on)

        # ═══════════ ⑫ 음성 메모(섞임) ═══════════
        print("\n── ⑫ 음성 메모 녹음 올리기 — 「한국어+베트남어 섞임」 ──")
        jget(gn, PN, "/__test/tr?reset=1")
        nc12 = len(jget(gn, PN, "/__test/chat")["calls"])
        last0 = (db("app_new", "SELECT MAX(id) AS m FROM voice_notes")[0]["m"] or 0)
        gn.goto(U(PN, "/voice-notes/new"), wait_until="domcontentloaded")
        gn.wait_for_selector("#vnLang", timeout=20000)
        gn.select_option("#vnLang", "mix")
        gn.locator("#vnFile").set_input_files(WAV95)
        n12 = wait_until(lambda: [r for r in db("app_new", "SELECT * FROM voice_notes WHERE id>? ORDER BY id DESC", (last0,))
                                  if "v_" in (r["summary"] or "")], 90)
        r12 = n12[0] if n12 else {}
        tr12 = jget(gn, PN, "/__test/tr")["tr"]
        chk("새 메모 · 원문 = 베트남어 · 한국어 · 한국어(헛말 빠짐)", bool(n12) and r12.get("body") == EXP_TXT, r12.get("body"))
        chk("95초 = 30초 조각 넷 — 끝 5초 조각은 보낸다(1초 넘음)",
            [t["file"] for t in tr12] == [PART(0), PART(1), PART(1), PART(2), PART(2), PART(3)]
            and 30000 < tr12[-1]["size"] < 60000, [(t["file"], t["size"]) for t in tr12])
        ch12 = jget(gn, PN, "/__test/chat")["calls"][nc12:]
        chk("메모 정리: 원문 표시 3곳 · 「v_」 규칙", len(ch12) == 1 and ch12[0]["user"].count("〔베트남어〕") == 3
            and ch12[0]["system"].endswith("\n\n" + VI_RULE))
        L12 = (r12.get("summary") or "").split("\n")
        chk("메모 정리 손봄", "- v_2호기 출하는 다음 주 금요일로 한다" in L12 and "- [결정] v_포장은 목요일까지 마친다" in L12
            and "〔베트남어〕" not in (r12.get("summary") or ""), r12.get("summary"))
        gn.goto(U(PN, "/voice-notes/%d" % r12.get("id", 0)), wait_until="domcontentloaded")
        gn.wait_for_selector("#vnSumBox.mdl", timeout=20000)
        h12 = gn.inner_html("#vnSumBox")
        chk("메모 화면: 「[결정]」 색 글씨 뒤에 v_", '<span class="tg tg-dec">[결정]</span> v_포장은' in h12 and "<em>" not in h12, h12[:500])
        gn.screenshot(path=os.path.join(SHOTS, "q88_voice_note_v.png"), full_page=False)

        # ═══════════ ⑬ 서버로 정리 — 한국어만은 운영과 같다 ═══════════
        print("\n── ⑬ 「🔄 다시 정리」(서버) — 한국어만은 운영과 같은 지시문·원문 ──")

        def run_extract(pg_, port, path, app, sql, rid):
            n0 = len(jget(pg_, port, "/__test/chat")["calls"])
            s_, d_ = post(pg_, port, path)
            wait_until(lambda: (db(app, sql, (rid,))[0]["summary"] or "").strip(), 30)
            wait_until(lambda: len(jget(pg_, port, "/__test/chat")["calls"]) > n0, 10)
            return s_, d_, jget(pg_, port, "/__test/chat")["calls"][n0:]
        X = {}
        for nm, pg_, port, ids, ns, app in (("n", gn, PN, IN, NN, "app_new"), ("b", gb, PB, IB, NB, "app_base")):
            X[nm + "K1"] = run_extract(pg_, port, "/api/meeting/%d/extract" % ids["K1"], app,
                                       "SELECT summary FROM meetings WHERE id=?", ids["K1"])
            X[nm + "V1"] = run_extract(pg_, port, "/api/meeting/%d/extract" % ids["V1"], app,
                                       "SELECT summary FROM meetings WHERE id=?", ids["V1"])
            X[nm + "N1"] = run_extract(pg_, port, "/api/voice-note/%d/extract" % ns["N1"], app,
                                       "SELECT summary FROM voice_notes WHERE id=?", ns["N1"])
            X[nm + "N2"] = run_extract(pg_, port, "/api/voice-note/%d/extract" % ns["N2"], app,
                                       "SELECT summary FROM voice_notes WHERE id=?", ns["N2"])
        for k, what in (("K1", "회의록"), ("N1", "음성 메모")):
            cn_, cb_ = X["n" + k][2], X["b" + k][2]
            chk("🔴 한국어만 %s: 지시문·원문·답 길이 운영과 글자 그대로" % what, len(cn_) == 1 and cn_ == cb_,
                ([(c["system"][-120:], c["user"][:60]) for c in cn_], [(c["system"][-120:], c["user"][:60]) for c in cb_]))
        for k, what, nv in (("V1", "회의록", 3), ("N2", "음성 메모", 3)):
            cn_, cb_ = X["n" + k][2], X["b" + k][2]
            ok_ = len(cn_) == 1 and len(cb_) == 1
            chk("섞인 %s: 지시문 = 운영 + 「v_」 규칙 · 원문 = 운영 원문에 표시만 %d곳" % (what, nv),
                ok_ and cn_[0]["system"] == cb_[0]["system"] + "\n\n" + VI_RULE
                and cn_[0]["user"].replace("〔베트남어〕", "") == cb_[0]["user"] and cn_[0]["user"].count("〔베트남어〕") == nv,
                (cn_[:1], cb_[:1]))

        # ═══════════ ⑭ 콘솔 ═══════════
        print("\n── ⑭ 콘솔 ──")
        other = [e for e in en + ev if KNOWN not in e]
        chk("새것 화면 콘솔 오류 0", not other, other[:3])
        otherb = [e for e in eb if KNOWN not in e]
        chk("운영 화면 콘솔 오류 0", not otherb, otherb[:3])
        br.close()
finally:
    kill(pb, pn)
    for f in WAVX:
        try:
            os.remove(f)
        except Exception:
            pass

print("\n사진: %s" % SHOTS)
print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
