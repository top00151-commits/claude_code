# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 회의록 마이크 아이콘 (z1146)
사용: py patch_bat46.py <원본 bat> <결과 bat> <검증 결과>
🔴 셸 heredoc 으로 돌리지 말 것 — 글 속 백틱을 셸이 명령으로 실행해 내용이 사라진다(2026-10-08 실제)."""
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "REM   LAST UPDATE:" in s, "LAST UPDATE 줄 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
prev = s[s.index("REM   LAST UPDATE: ") + len("REM   LAST UPDATE: "):].split(nl)[0]
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl), "| 직전:", prev[:40])

REG = "__REG__"
NEW = ("REM   LAST UPDATE: 2026-10-08 v5H226z1146[🎤 **회의록 마이크 아이콘도 또렷하게**"
       "(대표 지시 2026-10-08 「회의록도 같이 변경해줘」 · z1145 음성 메모에 이어). "
       "앱 파일 475개를 훑어 🎙(U+1F399) **48곳 · 파일 6개**를 🎤(U+1F3A4)로 바꿨다 — "
       "meeting_form.html 34 · main.py 6 · meetings.html 3 · ai_client.py 2 · m_z1144 2 · "
       "**share_audio.html 1**(처음에 놓쳤던 곳 — 전체를 훑어 찾았다). "
       "🔴**그냥 바꿨으면 깨졌을 자리 둘**: "
       "① meeting_form.html 1201 줄이 **단추 글자가 🎙 로 시작하는지 비교**한다"
       "(indexOf 로 0번째) → 라벨만 바꾸면 단추 이름이 덮어써진다 · 같이 바꿔 짝을 맞췄다 "
       "② 「🎙 [음성 변환]」은 **회의록 본문에 저장되는 글자**다 — 찾아 쓰는 코드 2곳(main 5919 · form 834)이 "
       "**이모지를 빼고 「[음성 변환]」만** 찾는 것을 확인하고 바꿨다"
       "(지난 회의록에 이미 적힌 표시는 그대로 둔다 — 기록은 고치지 않는다). "
       "시험의 🎙 은 전부 **검사 이름표**였고 판정은 이모지 없이 한다 → 이름표 9곳만 맞춤 · "
       "옛 작업기록 파일은 무접촉(그때 모습을 적어 둔 것). "
       "🔵두 글자 모두 UTF-8 4바이트 = **파일 크기 동일**. "
       "검증=" + REG + " · 표준 검사기 · JS 문법. "
       "meeting_form.html · meetings.html · share_audio.html · main.py · ai_client.py · m_z1144_voice_note.py]" + nl)

if len(sys.argv) > 3:
    NEW = NEW.replace(REG, sys.argv[3])
assert REG not in NEW, "검증 결과를 셋째 인자로 넣을 것"
lines = s.split(nl)
for i, ln in enumerate(lines):
    if ln.startswith("REM   LAST UPDATE:"):
        lines[i] = NEW.rstrip("\r\n") + nl + "REM   - " + ln[len("REM   LAST UPDATE: "):]
        break
else:
    raise SystemExit("LAST UPDATE 줄 없음")
out = nl.join(lines)
data = out.encode("utf-8")
with open(DST, "wb") as f:
    f.write(data)
chk = open(DST, "rb").read().decode("utf-8")
assert chk.startswith("﻿") == s.startswith("﻿")
assert chk.count("REM   LAST UPDATE:") == 1 and "v5H226z1146[" in chk
assert chk.count(nl + "REM   - " + prev) == 1, "직전 기록이 한 줄 아래로 밀리지 않았다"
# 🔴 백틱 사고 재발 방지 — 들어가야 할 말이 실제로 들어갔는지 본다
for must in ("indexOf 로 0번째", "[음성 변환]", "share_audio.html 1"):
    assert must in chk, "글이 빠졌다: " + must
print("[OK] BAT 갱신", len(raw), "→", len(data), "· 들어갈 말 3가지 확인")
