# -*- coding: utf-8 -*-
"""z1168 검사기 ① — 🎤 음성 메모 **정리가 길이에 따라 늘어나는가**를 옛 코드와 맞대어 잰다.

왜 만들었나 (대표 신고 2026-10-13 「끝까지 정리가 안된것 같은데… 녹음 파일이 길어서 그런건가?」)
  운영 실측 — 받아쓴 원문 10,327 → 19,684 → 27,950자(**2.7배**)인데
  정리는 760 → 970 → 936자(**1.2배**). **길이가 안 따라 늘었다.**
  (녹음은 23.1분·49.0분·63.9분 · 분당 448·402·437자로 **받아쓰기는 끝까지 됐다**)
  까닭 둘 = ① " + "답 길이 한도가 1500 으로 고정 ② 지시문이 「짧고 쓸모 있게」뿐.

재는 것
  ① 「나온 이름·회사·날짜」 묶음이 **사라졌나** (대표 「없어도 됨」) · 나머지 지시문은 **그대로인가**
  ② 답 길이 한도가 **원문 길이에 따라** 늘어나나 · 🔴 **옛값(1500)보다 작아지는 일은 없나**
  ③ 그 값이 **진짜 AI 호출에 실리나** (가짜 AI 로 가로채 받아 적는다)
  ④ 🔴 답이 **중간에서 끊기면** 한 번 더, 한도를 끝까지 올려 **다시 부르나** (전에는 그냥 실패였다)
  ⑤ 멀쩡한 답이면 **다시 부르지 않는다**(돈·시간 낭비 금지)
  ⑥ 🔵 **짧은 메모는 옛 코드와 글자 그대로 같은 요청** — 이번 변경이 짧은 메모를 건드리지 않았다는 증거

⛔ 바깥으로 아무것도 보내지 않는다 — AI 자리에 받아 적는 가짜를 끼운다.
쓰는 법: py note_len_check.py [base·new 가 있는 폴더]
판정: **종료코드**(0=통과).
"""
import importlib.util
import json
import os
import random
import re
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


old = load("base/ai_client.py", "aic_old_z1168")
new = load("new/ai_client.py", "aic_new_z1168")

#  「우리 회사 말」은 양쪽을 똑같이 맞춘다 — 그게 달라지면 무엇 때문에 달라졌는지 못 가린다
for _m in (old, new):
    _m.meeting_terms = lambda: ""


# ── 받아 적는 가짜 AI ────────────────────────────────────────────
GOOD = json.dumps({"title": "시험", "summary": "요점\n- 하나\n할 일\n- 둘"}, ensure_ascii=False)
CUT = GOOD[:len(GOOD) - 12]          # 🔴 중간에서 끊긴 답 — 닫는 괄호가 없다


class Rec:
    """ai_chat 자리에 끼워 **무엇을 어떤 한도로 불렀는지** 받아 적는다."""

    def __init__(self, replies):
        self.calls = []
        self.replies = list(replies)

    def __call__(self, user_text, system="", **kw):
        self.calls.append({"max_tokens": kw.get("max_tokens"),
                           "temperature": kw.get("temperature"),
                           "len_user": len(user_text), "system": system})
        r = self.replies.pop(0) if self.replies else GOOD
        return (True, r)


def run(mod, body, replies=(GOOD,)):
    rec = Rec(replies)
    mod.ai_chat = rec
    ok, data = mod.ai_extract_note(body)
    return ok, data, rec.calls


assert json.loads(GOOD), "성한 답이 JSON 이 아니다"
try:
    json.loads(CUT)
    raise SystemExit("!! 끊긴 답이 그대로 JSON 으로 읽힌다 — 시험이 성립하지 않는다")
except ValueError:
    pass


# ── ① 지시문 ────────────────────────────────────────────────────
print("\n── ① 「나온 이름·회사·날짜」가 사라졌나 (나머지는 그대로인가) ──")
PO, PN = old._NOTE_EXTRACT_SYSTEM, new._NOTE_EXTRACT_SYSTEM
chk("🔴 반대 시험 — 옛 지시문엔 「나온 이름·회사·날짜」가 **있다**", "나온 이름·회사·날짜" in PO)
chk("새 지시문엔 **없다**", "나온 이름·회사·날짜" not in PN)
chk("대신 「따로 모은 목록은 만들지 않는다」로 못박았다",
    "이름·회사·날짜만 따로 모은 목록은 만들지 않는다" in PN)
for keep in ["요점", "할 일", "안건·결정사항·참석자별 발언 귀속은 만들지 않는다",
             "절대 추측·창작 금지", '{"title":"","summary":""}', "공백 포함 20자 이내"]:
    chk("옛 지시문의 「%s」는 그대로 있다" % keep[:28], keep in PO and keep in PN)
for add in ["처음부터", "끝부분까지 빠짐없이", "원문이 길면 정리도 그만큼 길어야 한다",
            "1,000자마다"]:
    chk("새로 넣은 「%s」가 있다" % add, add in PN and add not in PO)

#  🔵 지시문에서 **줄 단위로** 사라진 것이 「이름·회사·날짜」 두 줄뿐인가
gone = [l for l in PO.splitlines() if l not in PN.splitlines()]
chk("🔵 지시문에서 사라진 줄은 셋뿐(이름·회사·날짜 두 줄 + 「짧고」 한 줄)",
    len(gone) == 3, "사라진 줄 %d개: %s" % (len(gone), gone))

# ── ② 답 길이 한도 ───────────────────────────────────────────────
print("\n── ② 답 길이 한도가 원문 길이를 따라 늘어나나 ──")
TABLE = [(0, 1500), (100, 1500), (5000, 1500), (10327, 1652),
         (19684, 3149), (27950, 4472), (50000, 8000), (1000000, 8000)]
for n, want in TABLE:
    got = new._note_budget(n)
    chk("원문 %7d자 → 한도 %5d" % (n, want), got == want, "→ %s" % got)
chk("🔴 옛값(1500)보다 작아지는 길이가 **하나도 없다**",
    all(new._note_budget(n) >= 1500 for n in
        ([0, 1, 9, 9374] + [random.Random(1168).randrange(0, 300000) for _ in range(3000)])))
chk("🔴 상한 8000 을 넘는 길이가 **하나도 없다**",
    all(new._note_budget(n) <= 8000 for n in
        ([0, 10 ** 9] + [random.Random(99).randrange(0, 5000000) for _ in range(3000)])))
chk("길수록 커진다(줄어드는 구간 없음)",
    all(new._note_budget(a) <= new._note_budget(b)
        for a, b in zip(range(0, 60000, 97), range(97, 60097, 97))))

# ── ③ 그 값이 진짜 호출에 실리나 ──────────────────────────────────
print("\n── ③ 가짜 AI 로 가로채 — 실제 호출에 실리는 한도 ──")
for n, want in [(500, 1500), (10327, 1652), (27950, 4472), (60000, 8000)]:
    body = "가" * n
    ok_o, _, co = run(old, body)
    ok_n, _, cn = run(new, body)
    chk("원문 %6d자 · 옛 코드는 늘 1500" % n, co[0]["max_tokens"] == 1500, co[0]["max_tokens"])
    chk("원문 %6d자 · 새 코드는 %5d" % (n, want), cn[0]["max_tokens"] == want, cn[0]["max_tokens"])
    chk("원문 %6d자 · 원문은 **안 잘려서** 간다" % n, cn[0]["len_user"] == n, cn[0]["len_user"])

# ── ④ 끊긴 답이면 다시 부르나 ────────────────────────────────────
print("\n── ④ 🔴 답이 중간에서 끊기면 — 한도를 올려 다시 부르나 ──")
ok_o, d_o, c_o = run(old, "가" * 27950, replies=[CUT, GOOD])
chk("🔴 반대 시험 — 옛 코드는 **한 번만** 부르고", len(c_o) == 1, len(c_o))
chk("🔴 반대 시험 — 옛 코드는 그대로 **실패**한다", ok_o is False, d_o.get("error", "")[:40])
ok_n, d_n, c_n = run(new, "가" * 27950, replies=[CUT, GOOD])
chk("새 코드는 **두 번** 부른다", len(c_n) == 2, len(c_n))
chk("두 번째는 한도를 끝까지(8000) 올린다", len(c_n) > 1 and c_n[1]["max_tokens"] == 8000,
    c_n[1]["max_tokens"] if len(c_n) > 1 else "-")
chk("그래서 **성공**한다", ok_n is True, d_n.get("error", ""))
chk("정리 글이 들어 있다", bool(d_n.get("summary")), d_n)

print("\n── ⑤ 멀쩡한 답이면 다시 부르지 않는다 ──")
ok_n, _, c_n = run(new, "가" * 27950, replies=[GOOD, GOOD])
chk("한 번만 부른다", len(c_n) == 1, len(c_n))
#  이미 상한인 길이에서 끊기면 — 더 올릴 곳이 없으니 다시 부르지 않는다
ok_n, d_n, c_n = run(new, "가" * 60000, replies=[CUT, GOOD])
chk("이미 상한(8000)인데 끊기면 **다시 안 부른다**(올릴 곳이 없다)", len(c_n) == 1, len(c_n))
chk("그때는 솔직히 실패를 알린다", ok_n is False, d_n.get("error", "")[:40])

# ── ⑥ 짧은 메모는 옛 코드와 같은 요청 ────────────────────────────
print("\n── ⑥ 🔵 짧은 메모는 옛 코드와 **글자 그대로 같은 요청** ──")
#  0자는 여기 넣지 않는다 — 빈 원문은 양쪽 다 AI 를 **안 부르므로** 바로 아래에서 따로 잰다
for n in (1, 300, 3000, 5000):
    body = "나" * n
    _, _, co = run(old, body)
    _, _, cn = run(new, body)
    chk("원문 %5d자 · 한도가 같다(1500)" % n,
        co and cn and co[0]["max_tokens"] == cn[0]["max_tokens"] == 1500,
        "%s vs %s" % (co[0]["max_tokens"] if co else "-", cn[0]["max_tokens"] if cn else "-"))
    chk("원문 %5d자 · 보내는 원문·온도가 같다" % n,
        co and cn and co[0]["len_user"] == cn[0]["len_user"]
        and co[0]["temperature"] == cn[0]["temperature"])
#  빈 원문은 양쪽 다 AI 를 아예 안 부른다
_, _, co = run(old, "   ")
_, _, cn = run(new, "   ")
chk("빈 원문이면 양쪽 다 AI 를 **안 부른다**", co == [] and cn == [], "%s %s" % (len(co), len(cn)))

#  🔵 지시문 밖(회의록용)은 건드리지 않았다
print("\n── ⑦ 🔵 회의록 쪽 지시문·한도는 **안 건드렸다** ──")
chk("회의록 지시문이 그대로다", old._MEETING_EXTRACT_SYSTEM == new._MEETING_EXTRACT_SYSTEM)
so = re.search(r"max_tokens=(\d+)", "".join(
    open(os.path.join(W, "base/ai_client.py"), encoding="utf-8").readlines()[505:515]))
sn = re.search(r"max_tokens=(\d+)", "".join(
    open(os.path.join(W, "new/ai_client.py"), encoding="utf-8").readlines()[505:515]))
chk("회의록 정리 한도(2000)가 그대로다", so and sn and so.group(1) == sn.group(1) == "2000",
    "%s vs %s" % (so and so.group(1), sn and sn.group(1)))

print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
