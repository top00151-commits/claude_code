# -*- coding: utf-8 -*-
"""z1168 → **z1174** 검사기 — 🎤 음성 메모 · 🗓 회의록 **정리 길이 한도**를 옛 코드와 맞대어 잰다.

왜 (대표 신고 2026-10-13 「끝까지 정리가 안된것 같은데」 · 「회의록도 정리되는 글자수가 정해져있지?」)
  **운영 실측** — 한국어는 **글자 하나 ≈ 토큰 하나**다.
    · 🎤 메모 4: 원문  9,321자 → 한도 1,500 → 정리 1,413자 = **한도의 94%**(눌림)
    · 🎤 메모 3: 원문 27,950자 → 한도 4,472 → 정리 4,032자 = **한도의 90%**(눌림)
    · 🎤 메모 2: 원문 19,684자 → 한도 3,149 → 정리 **6,759자** = **들어갈 수 없는 크기**
                 → 첫 호출이 잘려 「끊기면 상한으로 한 번 더」가 구해 줬다(= 매번 두 번 부름)
    · 🗓 회의 56: 원문 23,811자 → **2000 고정** → 정리 1,174자(**4%**) · 가장 긴 회의록 정리 1,278자
  → z1174: 음성메모 0.16→**0.45**(상한 8,000→**12,000**) · 회의록 **2000 고정 → 원문 비례**
    (결정·할 일이 같은 답에 들어가므로 그 몫 1,200 을 얹는다)

재는 것
  ① 한도 셈이 표대로인가 (음성메모·회의록) · 🔴 **옛값보다 작아지는 길이가 하나도 없나**
  ② 🔵 **짧은 것은 옛 코드와 글자 그대로 같은 요청** (음성메모 3,333자 이하 · 회의록 1,700자 이하)
  ③ 그 값이 **진짜 호출에 실리나** (가짜 AI 로 가로채)
  ④ 🔴 답이 **끊기면** 상한으로 한 번 더 (음성메모·회의록 둘 다)
  ⑤ 🔴 **안전장치** — 모델이 그만큼 못 내보내면 **작은 값(4,000)으로 한 번 더** (z1174)
  ⑥ 🔵 그 밖에 보내는 것(원문·온도)은 **옛 코드와 같다** · 빈 원문이면 AI 를 안 부른다

⛔ 바깥으로 아무것도 보내지 않는다 — AI 자리에 받아 적는 가짜를 끼운다.
쓰는 법: py note_len_check.py [base·new 가 있는 폴더]   (base = 지금 운영 · new = 내 변경)
판정: **종료코드**(0=통과).
"""
import importlib.util
import json
import os
import random
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


old = load("base/ai_client.py", "aic_old_z1174")
new = load("new/ai_client.py", "aic_new_z1174")
for _m in (old, new):
    _m.meeting_terms = lambda: ""      # 양쪽을 똑같이 맞춘다

NOTE_GOOD = json.dumps({"title": "시험", "summary": "요점\n- 하나"}, ensure_ascii=False)
MTG_GOOD = json.dumps({"title": "시험", "summary": "요점", "decisions": [], "actions": []},
                      ensure_ascii=False)
CUT = NOTE_GOOD[:len(NOTE_GOOD) - 12]          # 🔴 중간에서 끊긴 답(닫는 괄호가 없다)
TOOBIG = "AI 호출 오류(openai): max_tokens is too large: 12000"   # 모델이 거부하는 오류


class Rec:
    """ai_chat 자리에 끼워 **무엇을 어떤 한도로 불렀는지** 받아 적는다.
    replies 각 칸이 (성공여부, 글) 이면 그대로, 글만이면 성공으로 본다."""

    def __init__(self, replies):
        self.calls = []
        self.replies = list(replies)

    def __call__(self, user_text, system="", **kw):
        self.calls.append({"max_tokens": kw.get("max_tokens"),
                           "temperature": kw.get("temperature"),
                           "timeout": kw.get("timeout_sec"),
                           "len_user": len(user_text)})
        r = self.replies.pop(0) if self.replies else NOTE_GOOD
        return r if isinstance(r, tuple) else (True, r)


def run_note(mod, body, replies=(NOTE_GOOD,)):
    rec = Rec(replies)
    mod.ai_chat = rec
    ok, data = mod.ai_extract_note(body)
    return ok, data, rec.calls


def run_mtg(mod, body, replies=(MTG_GOOD,)):
    rec = Rec(replies)
    mod.ai_chat = rec
    ok, data = mod.ai_extract_meeting(body)
    return ok, data, rec.calls


def old_note(n):
    return max(1500, min(8000, int(n * 0.16)))      # 지금 운영(z1168)


assert json.loads(NOTE_GOOD) and json.loads(MTG_GOOD)
try:
    json.loads(CUT)
    raise SystemExit("!! 끊긴 답이 그대로 읽힌다 — 시험이 성립하지 않는다")
except ValueError:
    pass

# ── ① 한도 셈 ───────────────────────────────────────────────────
print("\n── ① 한도 셈이 표대로인가 ──")
NT = [(0, 1500), (100, 1500), (3333, 1500), (5000, 2250), (9321, 4194),
      (19684, 8857), (23811, 10714), (27950, 12000), (1000000, 12000)]
for n, want in NT:
    chk("🎤 음성메모 · 원문 %7d자 → %5d" % (n, want), new._note_budget(n) == want,
        "→ %s" % new._note_budget(n))
MT = [(0, 2000), (1700, 2000), (5000, 3450), (8421, 4989), (9321, 5394),
      (19684, 10057), (23811, 11914), (27950, 12000), (1000000, 12000)]
for n, want in MT:
    chk("🗓 회의록 · 원문 %7d자 → %5d" % (n, want), new._mtg_budget(n) == want,
        "→ %s" % new._mtg_budget(n))
RND = [random.Random(1173).randrange(0, 400000) for _ in range(3000)]
chk("🔴 음성메모가 옛 하한(1500) 밑으로 가는 길이가 **하나도 없다**",
    all(new._note_budget(n) >= 1500 for n in [0, 1, 9] + RND))
chk("🔴 회의록이 옛값(2000) 밑으로 가는 길이가 **하나도 없다**",
    all(new._mtg_budget(n) >= 2000 for n in [0, 1, 9, 1700] + RND))
chk("🔴 상한 12000 을 넘는 길이가 **하나도 없다**(둘 다)",
    all(new._note_budget(n) <= 12000 and new._mtg_budget(n) <= 12000
        for n in [0, 10 ** 9] + RND))
chk("길수록 커진다 — 줄어드는 구간 없음(둘 다)",
    all(new._note_budget(a) <= new._note_budget(b) and new._mtg_budget(a) <= new._mtg_budget(b)
        for a, b in zip(range(0, 80000, 97), range(97, 80097, 97))))
chk("🔵 회의록 한도가 음성메모보다 **늘 크거나 같다**(결정·할 일 몫)",
    all(new._mtg_budget(n) >= new._note_budget(n) for n in range(0, 80000, 131)))
chk("🔴 반대 시험 — 옛 코드엔 `_mtg_budget` 이 **없다**(회의록은 2000 고정이었다)",
    not hasattr(old, "_mtg_budget"))
chk("🔴 반대 시험 — 옛 음성메모 상한은 8000 이었다", old._NOTE_TOK_MAX == 8000)

# ── ② 짧은 것은 옛 코드와 같은 요청 ──────────────────────────────
print("\n── ② 🔵 짧은 것은 옛 코드와 **글자 그대로 같은 요청** ──")
for n in (1, 300, 3000, 3333):
    _, _, co = run_note(old, "나" * n)
    _, _, cn = run_note(new, "나" * n)
    chk("🎤 원문 %5d자 · 한도 같다(%s)" % (n, co[0]["max_tokens"]),
        co[0]["max_tokens"] == cn[0]["max_tokens"] == 1500,
        "%s vs %s" % (co[0]["max_tokens"], cn[0]["max_tokens"]))
    chk("🎤 원문 %5d자 · 원문·온도도 같다" % n,
        co[0]["len_user"] == cn[0]["len_user"] and co[0]["temperature"] == cn[0]["temperature"])
for n in (1, 500, 1700):
    _, _, co = run_mtg(old, "다" * n, replies=[MTG_GOOD])
    _, _, cn = run_mtg(new, "다" * n, replies=[MTG_GOOD])
    chk("🗓 원문 %5d자 · 한도 같다(2000)" % n,
        co[0]["max_tokens"] == cn[0]["max_tokens"] == 2000,
        "%s vs %s" % (co[0]["max_tokens"], cn[0]["max_tokens"]))
_, _, co = run_note(old, "   ")
_, _, cn = run_note(new, "   ")
chk("빈 원문이면 양쪽 다 AI 를 **안 부른다**", co == [] and cn == [], "%d %d" % (len(co), len(cn)))

# ── ③ 그 값이 진짜 호출에 실리나 ─────────────────────────────────
print("\n── ③ 가짜 AI 로 가로채 — 실제 호출에 실리는 한도 ──")
for n in (500, 9321, 19684, 60000):
    _, _, co = run_note(old, "가" * n)
    _, _, cn = run_note(new, "가" * n)
    chk("🎤 원문 %6d자 · 옛 %5d → 새 %5d" % (n, co[0]["max_tokens"], cn[0]["max_tokens"]),
        co[0]["max_tokens"] == old_note(n) and cn[0]["max_tokens"] == new._note_budget(n))
    chk("🎤 원문 %6d자 · 원문은 **안 잘려서** 간다" % n, cn[0]["len_user"] == n)
for n in (5000, 23811, 60000):
    _, _, co = run_mtg(old, "가" * n, replies=[MTG_GOOD])
    _, _, cn = run_mtg(new, "가" * n, replies=[MTG_GOOD])
    chk("🗓 원문 %6d자 · 옛 **2000 고정** → 새 %5d" % (n, cn[0]["max_tokens"]),
        co[0]["max_tokens"] == 2000 and cn[0]["max_tokens"] == new._mtg_budget(n))
chk("🔵 기다림(300초)은 그대로다", run_note(new, "가" * 9321)[2][0]["timeout"] == 300)

# ── ④ 끊긴 답이면 상한으로 한 번 더 ──────────────────────────────
print("\n── ④ 🔴 답이 **끊기면** 상한으로 한 번 더 ──")
ok_n, d_n, c_n = run_note(new, "가" * 19684, replies=[CUT, NOTE_GOOD])
chk("🎤 두 번 부른다", len(c_n) == 2, len(c_n))
chk("🎤 두 번째는 상한 12000", len(c_n) > 1 and c_n[1]["max_tokens"] == 12000,
    [x["max_tokens"] for x in c_n])
chk("🎤 그래서 성공한다", ok_n is True and bool(d_n.get("summary")), d_n.get("error"))
ok_m, d_m, c_m = run_mtg(new, "가" * 19684, replies=[CUT, MTG_GOOD])
chk("🗓 두 번 부른다", len(c_m) == 2, len(c_m))
chk("🗓 두 번째는 상한 12000", len(c_m) > 1 and c_m[1]["max_tokens"] == 12000,
    [x["max_tokens"] for x in c_m])
chk("🗓 그래서 성공한다", ok_m is True, d_m.get("error"))
chk("🔴 반대 시험 — 옛 코드는 회의록이 끊기면 **그대로 실패**한다",
    run_mtg(old, "가" * 19684, replies=[CUT, MTG_GOOD])[0] is False)
#  이미 상한이면 더 올릴 곳이 없다
_, _, c_x = run_note(new, "가" * 60000, replies=[CUT, NOTE_GOOD])
chk("🎤 이미 상한이면 **다시 안 부른다**", len(c_x) == 1, len(c_x))
#  멀쩡하면 한 번만
chk("🎤 멀쩡한 답이면 한 번만", len(run_note(new, "가" * 19684)[2]) == 1)
chk("🗓 멀쩡한 답이면 한 번만", len(run_mtg(new, "가" * 19684, replies=[MTG_GOOD])[2]) == 1)

# ── ⑤ 안전장치 — 모델이 그만큼 못 내보내면 ──────────────────────
print("\n── ⑤ 🔴 안전장치: 모델이 그만큼 못 내보내면 **작은 값으로 한 번 더** ──")
chk("`_tok_limit_error` 가 그 오류를 알아본다", new._tok_limit_error(TOOBIG))
for bad in ("AI 호출 오류(openai): Invalid API key", "AI 비활성 (공급사·키 미설정)",
            "AI 호출 오류(openai): The model `gpt-9` does not exist"):
    chk("🔵 그 밖의 오류는 **안 건드린다** — %s" % bad[:34], not new._tok_limit_error(bad))
ok_s, d_s, c_s = run_note(new, "가" * 19684, replies=[(False, TOOBIG), NOTE_GOOD])
chk("🎤 두 번 부른다", len(c_s) == 2, len(c_s))
chk("🎤 두 번째는 **4000**", len(c_s) > 1 and c_s[1]["max_tokens"] == 4000,
    [x["max_tokens"] for x in c_s])
chk("🎤 그래서 성공한다", ok_s is True, d_s.get("error"))
ok_s2, d_s2, c_s2 = run_mtg(new, "가" * 19684, replies=[(False, TOOBIG), MTG_GOOD])
chk("🗓 두 번 부르고 두 번째는 4000",
    len(c_s2) == 2 and c_s2[1]["max_tokens"] == 4000, [x["max_tokens"] for x in c_s2])
chk("🗓 그래서 성공한다", ok_s2 is True, d_s2.get("error"))
ok_k, d_k, c_k = run_note(new, "가" * 19684,
                          replies=[(False, "AI 호출 오류(openai): Invalid API key")])
chk("🔵 키 오류면 **다시 안 부르고** 그대로 알린다", len(c_k) == 1 and ok_k is False,
    (len(c_k), ok_k))
chk("🔴 반대 시험 — 옛 코드엔 안전장치가 **없다**", not hasattr(old, "_tok_limit_error"))

print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
