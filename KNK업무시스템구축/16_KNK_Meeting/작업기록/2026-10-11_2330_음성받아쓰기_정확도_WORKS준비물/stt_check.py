# -*- coding: utf-8 -*-
"""z1165 검사기 — 받아쓰기 요청을 **옛 코드와 새 코드에서 똑같이 받아 적어** 맞춰 본다.

🔵 이번 건의 「가장 센 검사」 = **힌트를 끄면 z1165 이전과 글자 하나까지 같은 요청**이 나간다.
   (화면이 아니라 서버가 바뀌는 건이라, 「화면이 같다」 대신 「보내는 요청이 같다」로 잰다.)

⛔ 바깥으로 아무것도 보내지 않는다 — OpenAI 자리에 받아 적는 가짜를 끼운다.
"""
import importlib.util
import io
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")

#  쓰는 법: py stt_check.py [base·new 가 있는 폴더]
#     그 폴더에 base/ (지금 운영 그대로) 와 new/ (내 변경) 가 있어야 한다.
W = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
OK = FAIL = 0


def chk(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (name, detail))


# ── 받아 적는 가짜 OpenAI ──────────────────────────────────────────
class _Rec:
    def __init__(self):
        self.calls = []

    def _mk(self):
        rec = self

        class _Tr:
            def create(self, **kw):
                kw2 = dict(kw)
                kw2.pop("file", None)          # 파일 핸들은 비교에서 뺀다
                rec.calls.append(kw2)

                class _R:
                    text = "받아쓴 글"
                return _R()

        class _Audio:
            transcriptions = _Tr()

        class _Cl:
            audio = _Audio()

        class _OpenAI:
            def __init__(self, **_):
                pass

            def __new__(cls, **_):
                return _Cl()
        return _OpenAI


def load(fname, modname):
    p = os.path.join(W, fname)
    spec = importlib.util.spec_from_file_location(modname, p)
    m = importlib.util.module_from_spec(spec)
    sys.modules[modname] = m
    spec.loader.exec_module(m)
    return m


os.environ["OPENAI_API_KEY"] = "sk-test-not-a-real-key"   # 가짜 — 바깥으로 안 나간다
AUDIO = os.path.join(tempfile.gettempdir(), "z1165_fake.m4a")
io.open(AUDIO, "wb").write(b"\0" * 16)

old = load("base/app_ai_client.py", "aic_old")
new = load("new/app_ai_client.py", "aic_new")


def send(mod, lang="", dialect="", keywords=None, hint=None):
    """그 코드가 **실제로 보내는 요청**을 받아 적어 돌려준다."""
    rec = _Rec()
    mod.openai = rec._mk()()  # noqa — 모듈 수준 openai 자리에 가짜
    mod.openai = type("O", (), {"OpenAI": rec._mk()})
    mod._OPENAI_OK = True
    if hint is not None and hasattr(mod, "STT_HINT_ON"):
        mod.STT_HINT_ON = hint
    try:
        if mod is new:
            ok, _ = mod.ai_transcribe(AUDIO, lang, dialect, keywords)
        else:
            ok, _ = mod.ai_transcribe(AUDIO, lang)
    except TypeError:
        ok, _ = mod.ai_transcribe(AUDIO, lang)
    return ok, rec.calls


print("\n── ① 가장 센 검사: 힌트를 끄면 z1165 이전과 **똑같은 요청** ──")
for lang in ["", "ko", "vi", "en"]:
    ok_o, c_o = send(old, lang)
    ok_n, c_n = send(new, lang, hint=False)
    chk("언어 %-4s 요청이 글자 그대로 같다" % (lang or "자동"),
        ok_o and ok_n and c_o == c_n, "\n       옛:%s\n       새:%s" % (c_o, c_n))

print("\n── ② 힌트를 켜면 — 설명과 낱말이 실린다 ──")
ok, c = send(new, "ko", hint=True)
k = c[0] if c else {}
chk("한국어: 설명이 실린다", "prompt" in k and "케이엔케이" in k["prompt"])
chk("한국어: 「그대로 받아쓰기」를 못박는다", "요약" in k.get("prompt", ""))
chk("한국어: 낱말이 실린다", len((k.get("extra_body") or {}).get("keywords") or []) > 10)
kws = (k.get("extra_body") or {}).get("keywords") or []
chk("한국어: 회사 말 목록의 바른 말이 들어온다(MLCC)", "MLCC" in kws)
chk("🔴 괄호 안 **잘못 들리는 보기**는 안 들어간다(MSC·MSCC·MHC)",
    not any(x in kws for x in ("MSC", "MSCC", "MHC")), kws[:40])
chk("낱말은 80개를 넘지 않는다(환각 방지)", len(kws) <= 80, len(kws))
chk("언어를 보낸다", (k.get("extra_body") or {}).get("languages") == ["ko"])

print("\n── ③ 🔴 자동 감지일 때 한국어를 편들지 않는다 ──")
ok, c = send(new, "", hint=True)
k = c[0] if c else {}
p = k.get("prompt", "")
chk("자동: 한국어 설명이 아니다", "케이엔케이" not in p, p[:60])
chk("자동: 두 말이 다 나올 수 있다고 알린다", "Korean" in p and "Vietnamese" in p)
chk("자동: 말한 언어 그대로 받아쓰라 한다", "verbatim in the language actually spoken" in p)
chk("자동: 번역 금지를 못박는다", "translate" in p)
kws = (k.get("extra_body") or {}).get("keywords") or []
chk("자동: 한국어 낱말도 있다", "금형" in kws)
chk("자동: 베트남어 낱말도 있다", any("khuôn" in x for x in kws))
chk("자동: 언어를 못박지 않는다", "languages" not in (k.get("extra_body") or {}))

print("\n── ④ 베트남어로 고르면 ──")
ok, c = send(new, "vi", hint=True)
k = c[0] if c else {}
chk("베트남: 한국어 설명이 아니다", "케이엔케이" not in k.get("prompt", ""))
chk("베트남: 언어를 보낸다", (k.get("extra_body") or {}).get("languages") == ["vi"])
kws = (k.get("extra_body") or {}).get("keywords") or []
chk("베트남: 한국어 낱말을 섞지 않는다", "금형" not in kws)

print("\n── ⑤ 🔴 구형(whisper-1)에는 지시문을 주지 않는다 ──")
#   whisper 의 prompt 는 '앞서 받아쓴 글' 취급 — 지시문을 주면 결과에 튀어나온다
new.STT_MODEL = "whisper-1"
new.STT_FALLBACK_MODEL = "whisper-1"
ok, c = send(new, "ko", hint=True)
k = c[0] if c else {}
chk("구형: 지시문 문장이 없다", "받아쓰세요" not in k.get("prompt", ""), k.get("prompt", "")[:60])
chk("구형: 낱말 나열만 준다", "," in k.get("prompt", "") and "금형" in k.get("prompt", ""))
chk("구형: 신형 항목(extra_body)을 안 쓴다", "extra_body" not in k)
chk("구형: 단수 language 를 쓴다", k.get("language") == "ko")
new.STT_MODEL = "gpt-transcribe"
new.STT_FALLBACK_MODEL = "whisper-1"

print("\n── ⑥ 🔴 힌트가 거부되면 — 같은 모델로 힌트 없이 먼저 다시 간다 ──")
#   이게 없으면 whisper-1 로 곧장 떨어져 **정확도가 거꾸로 나빠진다**


class _RecFail(_Rec):
    def _mk(self):
        rec = self

        class _Tr:
            def create(self, **kw):
                kw2 = dict(kw)
                kw2.pop("file", None)
                rec.calls.append(kw2)
                if "extra_body" in kw2 and "keywords" in (kw2["extra_body"] or {}):
                    raise TypeError("Unknown parameter: 'keywords'")

                class _R:
                    text = "받아쓴 글"
                return _R()

        class _Audio:
            transcriptions = _Tr()

        class _Cl:
            audio = _Audio()
        return type("O2", (), {"OpenAI": staticmethod(lambda **_: _Cl())})


rec = _RecFail()
new.openai = rec._mk()
new._OPENAI_OK = True
new.STT_HINT_ON = True
ok, _txt = new.ai_transcribe(AUDIO, "ko")
mods = [c.get("model") for c in rec.calls]
chk("거부돼도 성공한다", ok)
chk("같은 모델로 두 번 간다(예비로 안 떨어진다)", mods == ["gpt-transcribe", "gpt-transcribe"], mods)
chk("두 번째엔 낱말을 안 보낸다", "extra_body" not in rec.calls[1] or
    "keywords" not in (rec.calls[1].get("extra_body") or {}))
chk("두 번째엔 설명도 안 보낸다", "prompt" not in rec.calls[1])

print("\n── ⑦ 사람별 말투는 그 언어의 것일 때만 ──")
new.openai = type("O", (), {"OpenAI": staticmethod(lambda **_: None)})
chk("한국어 + 경상도 → 설명에 들어간다", "경상도" in new._stt_prompt("ko", "gyeongsang"))
chk("베트남어 + 경상도 → 무시한다", "경상도" not in new._stt_prompt("vi", "gyeongsang"))
chk("베트남어 + 북부 → 발음 힌트가 들어간다", "Bac Ninh" in new._stt_prompt("vi", "vi_north"))
chk("한국어 + 북부 → 무시한다", "Bac Ninh" not in new._stt_prompt("ko", "vi_north"))
chk("자동 + 말투 → 무시한다(어느 언어인지 모른다)",
    "경상도" not in new._stt_prompt("", "gyeongsang"))
chk("모르는 말투 → 무시한다", "None" not in new._stt_prompt("ko", "서울말"))

print("\n── ⑧ 힌트 거부 판정 ──")
for s, want in [("Unknown parameter: 'keywords'", True), ("unsupported parameter", True),
                ("Additional properties are not allowed", True),
                ("Connection timeout", False), ("Rate limit exceeded (429)", False),
                ("Audio file might be corrupted or unsupported", True)]:
    chk("판정 %-42s → %s" % (s[:42], want), new._stt_param_error(s) == want)

print("\n── ⑨ 회사 말 목록 뽑기 ──")
new._setting = lambda k: ("MLCC(적층 세라믹 콘덴서 · MSC/MSCC/MHC 로 잘못 들림), FPCB, "
                          "파트리스트(부품 목록 · 카트리스트로 잘못 들림), 표면저항(표면장으로 잘못 들림)"
                          if k == "meeting_terms" else "")
ws = new._stt_company_words()
chk("바른 말만 뽑는다", ws == ["MLCC", "FPCB", "파트리스트", "표면저항"], ws)
new._setting = lambda k: "-" if k == "meeting_terms" else ""
chk("「-」 로 끄면 회사 말이 0개", new._stt_company_words() == [])

print("\n── ⑩ 긴 녹음 조각이 25MB 안에 드나 (산수) ──")
mt = io.open(os.path.join(W, "new", "app_main.py"), encoding="utf-8").read()
import re as _re
sec = int(_re.search(r"_STT_SEG_SEC = (\d+) \* 60", mt).group(1)) * 60
kb = int(_re.search(r'KNK_WORKS_STT_KBPS"\) or "(\d+)"', mt).group(1))
mb = sec * kb / 8.0 / 1024.0
chk("한 조각 %d분 × %dkbps = %.1fMB ≤ 25MB" % (sec // 60, kb, mb), mb <= 25.0, mb)
chk("여유가 30%% 넘는다 (%.0f%%)" % ((25.0 - mb) / 25.0 * 100), (25.0 - mb) / 25.0 > 0.30)
chk("z1165 전(32kbps)보다 소리가 좋다", kb > 32, kb)
chk("경계가 줄었다(20분 → %d분)" % (sec // 60), sec > 20 * 60)
chk("ffmpeg 가 그 값을 쓴다", 'f"{_STT_SEG_KBPS}k"' in mt)
chk("진행 글이 숫자를 손으로 안 적는다", "20분씩 나누는 중" not in mt)

print("\n── ⑪ 되돌리기 한 줄이 있나 ──")
nt = io.open(os.path.join(W, "new", "app_ai_client.py"), encoding="utf-8").read()
chk("KNK_WORKS_STT_HINT 로 끌 수 있다", 'KNK_WORKS_STT_HINT' in nt)
chk("KNK_WORKS_STT_KBPS 로 되돌릴 수 있다", "KNK_WORKS_STT_KBPS" in mt)
chk("옛 되돌리기(KNK_WORKS_STT_MODEL)가 그대로 있다", "KNK_WORKS_STT_MODEL" in nt)

print("\n── ⑫ 안 건드렸나 (저장되는 것) ──")
chk("정리 프롬프트 무접촉", "_MEETING_EXTRACT_SYSTEM" in nt and
    nt.count("_MEETING_EXTRACT_SYSTEM") == io.open(
        os.path.join(W, "base", "app_ai_client.py"), encoding="utf-8").read().count("_MEETING_EXTRACT_SYSTEM"))
bt = io.open(os.path.join(W, "base", "app_main.py"), encoding="utf-8").read()
for fn in ["_stt_append_body", "_stt_strip_hallucination", "_stt_fix_3gp_brand", "_rec_drop_pending"]:
    chk("%s 무접촉" % fn, bt.count(fn) == mt.count(fn))
chk("본문에 붙이는 머리말 「🎤 [음성 변환]」 그대로", '"🎤 [음성 변환]\\n"' in mt)

print("\n── ⑬ 보이지 않는 제어 글자 0개 ──")
for n2, s in [("ai_client", nt), ("main", mt)]:
    bad = sum(s.count(chr(x)) for x in list(range(1, 9)) + [11, 12] + list(range(14, 32)))
    chk("%s 에 제어 글자 0개" % n2, bad == 0, bad)

print("\n합계 %d검사 · 실패 %d" % (OK + FAIL, FAIL))   # 「합계」 = 회귀 묶음이 읽는 말투
sys.exit(1 if FAIL else 0)
