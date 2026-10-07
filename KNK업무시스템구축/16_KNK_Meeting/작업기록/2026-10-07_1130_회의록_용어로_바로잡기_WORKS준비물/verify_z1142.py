# -*- coding: utf-8 -*-
"""z1142 서버 시험 — 회의록 「정리」에 우리 회사 말을 함께 보내는가
  A. 설정이 비었으면 기본 목록(MLCC …)을 보낸다
  B. 관리자가 적으면 그 목록만 보낸다(기본 목록은 안 보냄)
  C. "-" 한 글자면 아예 안 보낸다(끄기)
  D. 차례 — [이번 회의 정보](제목)가 먼저, [우리 회사 말]이 뒤 (실측으로 효과 본 배치)
  E. 「제목과 어긋나면 목록을 따른다」 규칙이 들어간다
  F. 🔴 원문(body)은 한 글자도 바꾸지 않고 그대로 보낸다
  G. 예전 그대로 — context 없이도 동작, 빈 원문은 AI 안 부름
🔴 진짜 AI 를 부르지 않는다(ai_chat 을 가로채 무엇을 보냈는지만 본다)."""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("KNK_SECRET_KEY", "verify-only-key")
sys.path.insert(0, os.path.join(os.getcwd(), "app_pkg_parent"))

OK = FAIL = 0
FAILS = []


def chk(cond, name, extra=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [PASS] %s%s" % (name, (" · " + extra) if extra else ""))
    else:
        FAIL += 1
        FAILS.append(name)
        print("  [FAIL] %s %s" % (name, extra))


# ── 가짜 환경 ─────────────────────────────────────────────
SENT = {}
SETTING = {"meeting_terms": ""}

import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "out", "ai_client.py")
if len(sys.argv) > 1:
    SRC = sys.argv[1]
print("시험 대상: %s" % SRC)

spec = importlib.util.spec_from_file_location("ai_client_under_test", SRC)
ai = importlib.util.module_from_spec(spec)
sys.modules["ai_client_under_test"] = ai
spec.loader.exec_module(ai)

ai._setting = lambda key: SETTING.get(key, "")        # DB 대신 가짜 설정


def fake_chat(user, system="", **kw):
    SENT["system"] = system
    SENT["user"] = user
    SENT["kw"] = kw
    return (True, '{"title":"t","summary":"s","decisions":[],"actions":[]}')


ai.ai_chat = fake_chat

BODY = "오늘 MSCC 출하 검사기 얘기를 했고 카트리스트를 전달했습니다. 표면장 측정도 논의."
CTX = "회의 제목: 삼성 MSCC 출하 검사기\n날짜: 2026-10-06\n참석자: 김정락"

# ── A. 설정 비었을 때 = 기본 목록 ──────────────────────────
print("\n[A] 설정이 비었으면 기본 목록을 보낸다")
SETTING["meeting_terms"] = ""
ok, r = ai.ai_extract_meeting(BODY, context=CTX)
sys_txt = SENT.get("system", "")
chk(ok, "정리 호출 성공")
chk("[우리 회사 말" in sys_txt, "「우리 회사 말」 묶음이 들어간다")
chk("MLCC" in sys_txt, "기본 목록의 MLCC 가 들어간다")
chk("파트리스트" in sys_txt and "표면저항" in sys_txt, "파트리스트·표면저항도 들어간다")

# ── B. 관리자가 적은 목록만 ────────────────────────────────
print("\n[B] 관리자가 적으면 그 목록만 보낸다")
SETTING["meeting_terms"] = "하이스트(HAIST), 케이엔케이"
ai.ai_extract_meeting(BODY, context=CTX)
sys_txt = SENT.get("system", "")
chk("하이스트(HAIST)" in sys_txt, "적은 말이 들어간다")
chk("MLCC" not in sys_txt, "기본 목록은 안 들어간다(덮어쓴다)")

# ── C. 끄기 ───────────────────────────────────────────────
print("\n[C] \"-\" 한 글자면 끈다")
SETTING["meeting_terms"] = "-"
ai.ai_extract_meeting(BODY, context=CTX)
sys_txt = SENT.get("system", "")
chk("[우리 회사 말" not in sys_txt, "묶음 자체가 안 들어간다")
chk("MLCC" not in sys_txt, "기본 목록도 안 들어간다")
chk("[이번 회의 정보]" in sys_txt, "회의 정보(제목)는 예전처럼 그대로 들어간다")

# ── D·E. 차례와 우선 규칙 ─────────────────────────────────
print("\n[D·E] 차례(제목 먼저 → 용어 뒤)와 우선 규칙")
SETTING["meeting_terms"] = ""
ai.ai_extract_meeting(BODY, context=CTX)
sys_txt = SENT.get("system", "")
i_ctx, i_terms = sys_txt.find("[이번 회의 정보]"), sys_txt.find("[우리 회사 말")
chk(i_ctx != -1 and i_terms != -1 and i_ctx < i_terms, "제목이 먼저, 용어가 뒤",
    "제목 %d < 용어 %d" % (i_ctx, i_terms))
chk("이 목록 쪽을 따른다" in sys_txt, "제목과 어긋나면 목록을 따르라는 규칙이 있다")
chk("원문에 없는 말은 절대 넣지 않는다" in sys_txt, "없는 말 넣지 말라는 규칙이 있다")

# ── F. 원문은 그대로 ──────────────────────────────────────
print("\n[F] 원문은 한 글자도 안 바꾼다")
chk(SENT.get("user") == BODY.strip(), "보낸 원문이 받은 원문과 같다")
chk("MSCC" in SENT.get("user", ""), "원문의 MSCC 는 그대로 남는다(정리에서만 바로잡는다)")

# ── G. 예전 그대로 ────────────────────────────────────────
print("\n[G] 예전 그대로")
SENT.clear()
ok, r = ai.ai_extract_meeting("")
chk(ok and r.get("summary") == "" and not SENT, "빈 원문이면 AI 를 안 부른다")
SETTING["meeting_terms"] = ""
ok, r = ai.ai_extract_meeting(BODY)        # context 없이
chk(ok, "회의 정보 없이도 동작한다")
chk("[이번 회의 정보]" not in SENT.get("system", ""), "회의 정보가 없으면 그 묶음은 안 붙는다")
chk("MLCC" in SENT.get("system", ""), "회의 정보가 없어도 용어는 들어간다")

print("\n%s  통과 %d · 실패 %d" % ("=" * 46, OK, FAIL))
if FAILS:
    print("실패 항목: " + ", ".join(FAILS))
sys.exit(1 if FAIL else 0)
