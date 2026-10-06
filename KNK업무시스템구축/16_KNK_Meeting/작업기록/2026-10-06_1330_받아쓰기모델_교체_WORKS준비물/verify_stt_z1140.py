# -*- coding: utf-8 -*-
"""z1140 서버 시험 — 받아쓰기 모델 교체 (대표 지시 2026-10-06)
  A. 기본값 — 새 모델(gpt-transcribe) 로 보낸다 · 폴백은 whisper-1
  B. 신형/구형 호출법이 다르다 — 신형 response_format=json·languages(복수) / 구형 language(단수)
  C. 🔴 지시문(prompt)·힌트(keywords)는 **아무 때도 안 보낸다**(구형은 결과에 튀어나오고, 이득을 증명 못 했다)
  D. 새 모델이 터지면 옛 모델로 **자동으로 한 번 더** · 둘 다 터지면 사람말 오류
  E. 환경변수로 되돌릴 수 있다(KNK_WORKS_STT_MODEL=whisper-1)
  F. 예전 그대로 — 키 없음·파일 없음·SDK 없음
🔴 진짜 AI 를 부르지 않는다(호출을 가로채 무엇을 보냈는지만 본다)."""
import os
import sys
import types

sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("KNK_SECRET_KEY", "verify-only-key")
sys.path.insert(0, os.getcwd())

OK = FAIL = 0
FAILS = []


def chk(cond, name, extra=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  [PASS] {name}" + (f" · {extra}" if extra != "" else ""))
    else:
        FAIL += 1
        FAILS.append(name)
        print(f"  [FAIL] {name} {extra}")


SENT = []        # 보낸 내용 기록
FAIL_ON = set()  # 이 모델이면 터뜨린다


class _Resp:
    def __init__(self, text):
        self.text = text


class _Tr:
    def create(self, **kw):
        SENT.append(dict(kw))
        m = kw.get("model")
        if m in FAIL_ON:
            raise RuntimeError("일부러 낸 오류(%s)" % m)
        return _Resp("받아쓴 글 (%s)" % m)


class _Audio:
    transcriptions = _Tr()


class _Client:
    def __init__(self, **kw):
        self.audio = _Audio()


def load(env=None):
    """ai_client 를 환경변수와 함께 새로 불러온다(모듈 맨 위에서 모델을 읽으므로)."""
    for k in ("KNK_WORKS_STT_MODEL", "KNK_WORKS_STT_FALLBACK"):
        os.environ.pop(k, None)
    for k, v in (env or {}).items():
        os.environ[k] = v
    import importlib
    for mod in [m for m in list(sys.modules) if m.endswith("ai_client")]:
        del sys.modules[mod]
    import app as _pkg
    if hasattr(_pkg, "ai_client"):      # 꾸러미에 남은 옛 모듈을 떼야 새로 읽는다
        delattr(_pkg, "ai_client")
    AC = importlib.import_module("app.ai_client")
    AC.openai = types.SimpleNamespace(OpenAI=_Client)
    AC._OPENAI_OK = True
    AC._key_for = lambda p: "test-key" if p == "openai" else ""
    return AC


AUDIO = os.path.abspath("z1140_test.m4a")
with open(AUDIO, "wb") as f:
    f.write(b"\0" * 1024)

# ═══ A. 기본값 ═══════════════════════════════════════════════════════════════
print("\n■ A. 기본값 = 새 모델", flush=True)
AC = load()
chk(AC.STT_MODEL == "gpt-transcribe", "A1 기본 모델 = gpt-transcribe", AC.STT_MODEL)
chk(AC.STT_FALLBACK_MODEL == "whisper-1", "A2 실패하면 whisper-1", AC.STT_FALLBACK_MODEL)
SENT.clear()
ok, txt = AC.ai_transcribe(AUDIO)
chk(ok and "gpt-transcribe" in txt, "A3 받아쓰기 성공", txt)
chk(len(SENT) == 1 and SENT[0]["model"] == "gpt-transcribe", "A4 새 모델로 한 번만 보냈다",
    [s["model"] for s in SENT])

# ═══ B. 신형/구형 호출법 ═════════════════════════════════════════════════════
print("\n■ B. 신형·구형 호출법이 다르다", flush=True)
SENT.clear()
AC.ai_transcribe(AUDIO, "ko")
s = SENT[0]
chk(s.get("response_format") == "json", "B1 신형은 response_format=json", s.get("response_format"))
chk(s.get("extra_body") == {"languages": ["ko"]}, "B2 신형 언어는 languages(복수)", s.get("extra_body"))
chk("language" not in s, "B3 신형에 단수 language 를 보내지 않는다")
SENT.clear()
AC.ai_transcribe(AUDIO)          # 언어 없이(기본)
chk("extra_body" not in SENT[0], "B4 언어를 안 주면 언어 칸도 안 보낸다(베트남 회의 보호)", SENT[0].keys())
AC2 = load({"KNK_WORKS_STT_MODEL": "whisper-1"})
SENT.clear()
AC2.ai_transcribe(AUDIO, "vi")
s = SENT[0]
chk(s.get("language") == "vi", "B5 구형은 단수 language", s.get("language"))
chk("response_format" not in s and "extra_body" not in s, "B6 구형에 신형 칸을 보내지 않는다", s.keys())

# ═══ C. 지시문·힌트 안 보냄 ══════════════════════════════════════════════════
print("\n■ C. 🔴 지시문·힌트는 아무 때도 안 보낸다", flush=True)
AC = load()
SENT.clear()
AC.ai_transcribe(AUDIO, "ko")
AC2 = load({"KNK_WORKS_STT_MODEL": "whisper-1"})
AC2.ai_transcribe(AUDIO, "ko")
chk(all("prompt" not in s for s in SENT), "C1 prompt 를 한 번도 안 보냈다")
chk(all("keywords" not in str(s.get("extra_body") or {}) for s in SENT), "C2 keywords 도 안 보냈다")

# ═══ D. 새 모델이 터지면 옛 모델로 ═══════════════════════════════════════════
print("\n■ D. 새 모델이 터지면 옛 모델로 자동으로 한 번 더", flush=True)
AC = load()
SENT.clear()
FAIL_ON.clear()
FAIL_ON.add("gpt-transcribe")
ok, txt = AC.ai_transcribe(AUDIO)
chk(ok and "whisper-1" in txt, "D1 옛 모델로 받아써서 성공", txt)
chk([s["model"] for s in SENT] == ["gpt-transcribe", "whisper-1"], "D2 새 모델 먼저, 그다음 옛 모델",
    [s["model"] for s in SENT])
SENT.clear()
FAIL_ON.add("whisper-1")
ok, txt = AC.ai_transcribe(AUDIO)
chk((not ok) and "음성→글자 오류" in txt, "D3 둘 다 터지면 사람말 오류", txt[:60])
chk(len(SENT) == 2, "D4 두 번만 시도한다(무한 재시도 없음)", len(SENT))
FAIL_ON.clear()

# ═══ E. 되돌리기 ═════════════════════════════════════════════════════════════
print("\n■ E. 환경변수 한 줄로 되돌릴 수 있다", flush=True)
AC = load({"KNK_WORKS_STT_MODEL": "whisper-1"})
SENT.clear()
AC.ai_transcribe(AUDIO)
chk([s["model"] for s in SENT] == ["whisper-1"], "E1 KNK_WORKS_STT_MODEL=whisper-1 이면 옛 모델만",
    [s["model"] for s in SENT])
AC = load({"KNK_WORKS_STT_MODEL": "gpt-4o-transcribe"})
SENT.clear()
AC.ai_transcribe(AUDIO, "ko")
chk(SENT[0]["model"] == "gpt-4o-transcribe" and SENT[0].get("response_format") == "json",
    "E2 다른 신형 모델로도 바꿀 수 있다", SENT[0]["model"])

# ═══ F. 예전 그대로 ══════════════════════════════════════════════════════════
print("\n■ F. 예전 그대로", flush=True)
AC = load()
AC._key_for = lambda p: ""
ok, txt = AC.ai_transcribe(AUDIO)
chk((not ok) and "OpenAI 키" in txt, "F1 키 없으면 그대로 안내", txt[:40])
AC = load()
ok, txt = AC.ai_transcribe("없는파일.m4a")
chk((not ok) and "찾을 수 없습니다" in txt, "F2 파일 없으면 그대로 안내", txt[:40])
AC = load()
AC._OPENAI_OK = False
ok, txt = AC.ai_transcribe(AUDIO)
chk((not ok) and "SDK 미설치" in txt, "F3 SDK 없으면 그대로 안내", txt[:40])
chk(hasattr(load(), "transcribe_available"), "F4 쓰기 전 확인 함수는 그대로")

try:
    os.remove(AUDIO)
except Exception:
    pass
print("\n" + "=" * 68)
print(f"합계: 통과 {OK} · 실패 {FAIL}")
for f in FAILS:
    print("  - 실패:", f)
sys.exit(1 if FAIL else 0)
