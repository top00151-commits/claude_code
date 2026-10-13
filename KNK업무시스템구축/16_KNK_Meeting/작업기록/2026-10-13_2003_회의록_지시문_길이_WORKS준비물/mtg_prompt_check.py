# -*- coding: utf-8 -*-
"""z1176 검사기 — 🗓 회의록 **지시문**에 길이 규칙을 넣은 것을 옛 코드와 맞대어 잰다.

왜 (대표 2026-10-13, 「다시 정리」 눌러 보신 뒤)
  z1174 로 **한도**는 풀었는데 회의록 정리는 그대로 짧았다.
  **실측** — 회의 70: 원문 8,323자 · 한도 **4,945** 인데 정리는 **947자(19%)**.
  = 한도가 아니라 **지시문에 길이 이야기가 한 마디도 없어서**였다.
  🔵 음성 메모는 z1168 에서 ①한도 ②지시문을 **같이** 고쳐 효과를 봤다(970 → 6,759자).
     회의록엔 ①만 옮기고 ②를 빠뜨렸다 → **반만 고친 것**이었다.

재는 것 (⛔ AI 를 부르지 않는다 — 지시문 글자만 본다)
  ① 🔴 **반대 시험** — 옛 지시문엔 그 두 줄이 **없다**
  ② 새 지시문에 두 줄이 **있다**
  ③ 🔵 **사라진 줄 0** — 늘어난 줄은 **그 둘뿐**
  ④ 🔵 **틀과 규칙은 그대로** — 핵심 한 줄 · [안건명] · 논의 요점 · (강조)/(우려)/(이견)/(합의)
       · decisions/actions · 「확정된」 · 「절대 추측·창작 금지」 · JSON 모양
  ⑤ 🔵 **음성 메모 쪽은 하나도 안 건드렸다**(지시문도 한도도)
  ⑥ 🔵 **한도 셈도 안 건드렸다** — 이번 건은 지시문만 바꾼다
  ⑦ 🔵 음성 메모와 회의록이 **같은 두 줄**을 쓴다(규칙이 두 벌이 되지 않게)

쓰는 법: py mtg_prompt_check.py [base·new 가 있는 폴더]
판정: **종료코드**(0=통과).
"""
import importlib.util
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


old = load("base/ai_client.py", "aic_old_z1176")
new = load("new/ai_client.py", "aic_new_z1176")
PO, PN = old._MEETING_EXTRACT_SYSTEM, new._MEETING_EXTRACT_SYSTEM

#  넣기로 한 두 줄의 알맹이
ADD = ["처음부터 끝까지", "끝부분까지 빠짐없이", "뒤로 갈수록 짧아지거나",
       "원문이 길면 정리도 그만큼 길어야 한다", "1,000자마다", "논의 요점"]

print("\n── ① 🔴 반대 시험: 옛 지시문엔 길이 이야기가 **없다** ──")
for s in ADD:
    if s == "논의 요점":        # 이 말은 옛 지시문에도 원래 있다(형식 설명)
        continue
    chk("옛 지시문에 「%s」가 **없다**" % s, s not in PO)
chk("🔴 옛 지시문엔 길이·분량 규칙이 한 줄도 없다",
    not any(k in PO for k in ("길면", "빠짐없이", "자마다", "줄 이상")))

print("\n── ② 새 지시문에 두 줄이 있다 ──")
for s in ADD:
    chk("새 지시문에 「%s」가 있다" % s, s in PN)
chk("「한 줄 이상」을 못박았다", "한 줄 이상" in PN)

print("\n── ③ 🔵 사라진 줄 0 · 늘어난 줄은 **그 둘뿐** ──")
ol, nl = PO.splitlines(), PN.splitlines()
gone = [x for x in ol if x not in nl]
came = [x for x in nl if x not in ol]
chk("사라진 줄 **0**", not gone, "사라짐: %s" % [g[:50] for g in gone])
chk("늘어난 줄 **2**", len(came) == 2, "%d개: %s" % (len(came), [c[:45] for c in came]))
chk("늘어난 줄이 둘 다 길이 규칙이다",
    all(("길면" in c) or ("빠짐없이" in c) for c in came), [c[:45] for c in came])
chk("줄 수가 13 → 15", (len(ol), len(nl)) == (13, 15), (len(ol), len(nl)))

print("\n── ④ 🔵 틀과 규칙은 **그대로** ──")
KEEP = ["핵심: <회의 결론 한 줄>", "[안건명]", "<논의 요점>",
        "(강조)/(우려)/(이견)/(합의)", "참석자 이름이 원문에 나오면",
        "- decisions:", "- actions:", "확정된", "절대 추측·창작 금지",
        "공백 포함 20자 이내", '{"title":"","summary":"",',
        '"decisions":[{"who":"","what":"","due":""}]',
        '"actions":[{"assignee":"","task":"","due":""}]',
        "마크다운 코드펜스·설명·인사말 금지"]
for k in KEEP:
    chk("「%s」 그대로" % k[:38], (k in PO) and (k in PN))

print("\n── ⑤ 🔵 음성 메모 쪽은 **하나도 안 건드렸다** ──")
chk("음성메모 지시문이 글자 그대로 같다", old._NOTE_EXTRACT_SYSTEM == new._NOTE_EXTRACT_SYSTEM)
chk("음성메모 한도 셈이 같다",
    all(old._note_budget(n) == new._note_budget(n) for n in range(0, 80000, 97)))

print("\n── ⑥ 🔵 한도 셈도 **안 건드렸다**(이번 건은 지시문만) ──")
chk("회의록 한도 셈이 같다",
    all(old._mtg_budget(n) == new._mtg_budget(n) for n in range(0, 80000, 97)))
for n, want in ((8323, 4945), (23811, 11914), (1700, 2000)):
    chk("회의록 원문 %6d자 → %5d (그대로)" % (n, want), new._mtg_budget(n) == want,
        new._mtg_budget(n))
chk("기다림(300초)·안전장치(4000)도 그대로",
    old.EXTRACT_TIMEOUT_SEC == new.EXTRACT_TIMEOUT_SEC == 300
    and old._SAFE_TOK == new._SAFE_TOK == 4000)

print("\n── ⑦ 🔵 음성 메모와 회의록이 **같은 두 줄**을 쓴다 ──")
for s in ("처음부터 끝까지", "끝부분까지 빠짐없이", "원문이 길면 정리도 그만큼 길어야 한다",
          "1,000자마다", "한 줄 이상"):
    chk("둘 다 「%s」를 쓴다" % s, s in new._NOTE_EXTRACT_SYSTEM and s in PN)

print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
