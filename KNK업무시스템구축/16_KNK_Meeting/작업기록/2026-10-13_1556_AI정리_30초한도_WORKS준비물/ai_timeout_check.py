# -*- coding: utf-8 -*-
"""z1172 검사기 — AI 를 부를 때 **몇 초까지 기다리는가**를 옛 코드와 맞대어 잰다.

대표 신고 2026-10-13 「**AI 호출 오류(openai): Request timed out.**」
  까닭 = `ai_client.py` 의 공용 `TIMEOUT_SEC = 30`. 짧은 답(번역 등)엔 맞지만,
  z1168 로 **정리 답이 길어지자** 30초를 넘기기 시작했다(재시도 2번이라 90초쯤 버티다 터진다).
  ⛔ 공용값을 올리면 **남의 기능까지 전부** 바뀐다 → **정리 호출에만** 300초를 준다.

🔵 **가장 센 검사** = 「**정리만 300초로 바뀌고, 나머지는 30초 그대로인가**」.
   그리고 「정리를 부른 **뒤에도** 남의 호출이 30초인가」(공용 클라이언트를 안 건드렸다는 증거).

재는 것
  ① 🔴 반대 시험 — 옛 코드는 **정리도 30초**였다
  ② 🎤 음성 메모 정리 · 🗓 회의록 정리 = **300초**
  ③ 🔵 **남의 호출은 30초 그대로** — 그냥 `ai_chat` · 짧은 요약 · 번역 등
  ④ 🔵 **공용 클라이언트가 안 바뀐다** — 300초 호출 **뒤에** 부른 남의 호출도 30초
  ⑤ 끊긴 답 다시 부를 때도 300초
  ⑥ 그 밖에 보내는 것(원문·max_tokens·온도)은 **옛 코드와 글자 그대로 같다**

⛔ 바깥으로 아무것도 보내지 않는다 — 진짜 SDK 로 클라이언트만 만들고, 보내는 자리는 가짜로 막는다.
쓰는 법: py ai_timeout_check.py [base·new 가 있는 폴더]
판정: **종료코드**(0=통과).
"""
import importlib.util
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

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


def load(fname, modname):
    p = os.path.join(W, fname)
    spec = importlib.util.spec_from_file_location(modname, p)
    m = importlib.util.module_from_spec(spec)
    sys.modules[modname] = m
    spec.loader.exec_module(m)
    return m


GOOD = json.dumps({"title": "시험", "summary": "요점\n- 하나"}, ensure_ascii=False)
MEET = json.dumps({"title": "시험", "summary": "요점", "decisions": [], "actions": []},
                  ensure_ascii=False)


def arm(m, reply=GOOD):
    """진짜 OpenAI 클라이언트를 만들되 **보내는 자리만** 가짜로 막고, 그때의 timeout 을 받아 적는다."""
    rec = []
    os.environ["OPENAI_API_KEY"] = "sk-test-not-a-real-key"
    m.meeting_terms = lambda: ""
    m.get_provider = lambda: "openai"
    m._sdk_ok = lambda p: True
    m._key_for = lambda p: "sk-test-not-a-real-key"
    m._OPENAI_OK = True
    m._client = None                      # 캐시 비우기
    m._client_signature = None

    def fake_create(client, mdl, messages, max_tokens, temperature):
        rec.append({"timeout": getattr(client, "timeout", None),
                    "max_tokens": max_tokens, "temperature": temperature,
                    "user_len": len(messages[-1]["content"])})

        class _Msg:
            content = reply

        class _Ch:
            message = _Msg()

        class _R:
            choices = [_Ch()]
        return _R()

    m._openai_create = fake_create
    return rec


old = load("base/ai_client.py", "aic_old_z1172")
new = load("new/ai_client.py", "aic_new_z1172")
BODY = "가" * 20000

print("\n── ① 🔴 반대 시험: 옛 코드는 **정리도 30초**였다 ──")
r = arm(old)
old.ai_extract_note(BODY)
chk("옛 코드 · 음성 메모 정리 = 30초", r and r[0]["timeout"] == 30, r[:1])
r = arm(old)
old.ai_extract_meeting(BODY)
chk("옛 코드 · 회의록 정리 = 30초", r and r[0]["timeout"] == 30, r[:1])
chk("옛 코드엔 EXTRACT_TIMEOUT_SEC 이 **없다**", not hasattr(old, "EXTRACT_TIMEOUT_SEC"))
chk("옛 ai_chat 엔 timeout_sec 칸이 **없다**",
    "timeout_sec" not in old.ai_chat.__code__.co_varnames)

print("\n── ② 🔵 새 코드: 정리만 300초 ──")
chk("EXTRACT_TIMEOUT_SEC = 300", getattr(new, "EXTRACT_TIMEOUT_SEC", None) == 300,
    getattr(new, "EXTRACT_TIMEOUT_SEC", None))
chk("공용 TIMEOUT_SEC 은 **안 건드렸다**(30)", new.TIMEOUT_SEC == 30 == old.TIMEOUT_SEC,
    new.TIMEOUT_SEC)
rn = arm(new)
new.ai_extract_note(BODY)
chk("🎤 음성 메모 정리 = **300초**", rn and rn[0]["timeout"] == 300, rn[:1])
rm_ = arm(new)
new.ai_extract_meeting(BODY)
chk("🗓 회의록 정리 = **300초**", rm_ and rm_[0]["timeout"] == 300, rm_[:1])

print("\n── ③ 🔵 남의 호출은 **30초 그대로** ──")
for lab, fn in (("그냥 ai_chat", lambda m: m.ai_chat("안녕")),
                ("기본값 그대로 부르기", lambda m: m.ai_chat("안녕", system="시험"))):
    ro, rnn = arm(old), None
    fn(old)
    rnn = arm(new)
    fn(new)
    chk("%s · 옛 %s초 · 새 %s초 (같다)" % (lab, ro[0]["timeout"], rnn[0]["timeout"]),
        ro[0]["timeout"] == rnn[0]["timeout"] == 30)
#  이 파일 안의 **다른 기능**들도 그대로인지 — timeout_sec 을 안 주는 ai_chat 호출 전부
import re  # noqa: E402
src = open(os.path.join(W, "new/ai_client.py"), encoding="utf-8").read()
calls = re.findall(r"ai_chat\((?:[^()]|\([^()]*\))*\)", src)
calls = [c for c in calls if not c.startswith("ai_chat(\n")]
with_to = [c for c in calls if "timeout_sec" in c]
chk("새 코드에서 timeout_sec 을 주는 곳은 **정리뿐**(3곳: 음성메모 2 · 회의록 1)",
    len(with_to) == 2, "한 줄짜리 %d곳 · 전체 %d곳" % (len(with_to), len(calls)))

print("\n── ④ 🔵 공용 클라이언트가 **안 바뀐다**(가장 센 검사) ──")
rn2 = arm(new)
new.ai_extract_note(BODY)          # 300초짜리 호출 먼저
new.ai_chat("안녕")                 # 그 **뒤에** 남의 호출
chk("정리(300초) 뒤에 부른 남의 호출이 **다시 30초**",
    len(rn2) >= 2 and rn2[0]["timeout"] == 300 and rn2[1]["timeout"] == 30,
    [x["timeout"] for x in rn2])
chk("캐시된 공용 클라이언트 자체가 30초다",
    getattr(new._get_client("openai"), "timeout", None) == 30,
    getattr(new._get_client("openai"), "timeout", None))

print("\n── ⑤ 끊긴 답 다시 부를 때도 300초 ──")
CUT = GOOD[:len(GOOD) - 12]
rn3 = arm(new, reply=CUT)
new.ai_extract_note(BODY)
chk("두 번 부른다", len(rn3) == 2, len(rn3))
chk("두 번째도 **300초**", len(rn3) > 1 and rn3[1]["timeout"] == 300,
    [x["timeout"] for x in rn3])

print("\n── ⑥ 🔵 보내는 것은 옛 코드와 **글자 그대로 같다** ──")
for lab, call in (("음성 메모 정리", lambda m: m.ai_extract_note(BODY)),
                  ("회의록 정리", lambda m: m.ai_extract_meeting(BODY))):
    ro = arm(old, reply=(GOOD if "음성" in lab else MEET))
    call(old)
    rnn = arm(new, reply=(GOOD if "음성" in lab else MEET))
    call(new)
    for k in ("max_tokens", "temperature", "user_len"):
        chk("%s · %s 가 같다 (%s)" % (lab, k, ro[0][k]), ro[0][k] == rnn[0][k],
            "%s vs %s" % (ro[0][k], rnn[0][k]))

print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
