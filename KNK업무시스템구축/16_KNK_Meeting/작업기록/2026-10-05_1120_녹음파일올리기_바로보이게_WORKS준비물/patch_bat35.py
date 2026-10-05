# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 「📁 녹음 파일 올리기」를 맨 위로 (z1138)
사용: py patch_bat35.py <원본 bat> <결과 bat> <회귀 결과>"""
import io
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
NEW = ("REM   LAST UPDATE: 2026-10-05 v5H226z1138[회의록 — **「📁 녹음 파일 올리기」를 회의록 맨 위 큰 단추로**(대표 지시 2026-10-05 "
       "「휴대폰 녹음기로 녹음한 걸 올리는 메뉴가 바로 보이질 않아 찾기 어렵다」). "
       "①전까지는 올리기가 **「🔧 다시 하기 · 녹음 추가(필요할 때만)」 접힌 칸** 안에만 있었다 → 녹음을 마치고 회의록을 다시 열면 "
       "그 칸이 접힌 채 화면 아래(폰 순서 11)로 내려가 **올리는 자리로 보이지 않았다** "
       "②새 칸 `#recUpTop` — 진행 카드 바로 아래(폰 order:2 · PC 는 DOM 위쪽) · 큰 단추 108px · 안내 한 줄(홈 화면 「음성 녹음」) "
       "③🔴**녹음이 없을 때만** 크게 보인다(대표 결정) — 녹음이 들어오면(올리기 성공·이 화면 녹음 시작) 감춘다 · "
       "녹음 중이던 회의는 그 자리가 「🔴 녹음 중이던 회의」 "
       "④올리는 길은 하나만 — 새 입력칸을 기존 `onPickFile` 에 이어 붙임(처리·검사·자동 정리 그대로) "
       "⑤접힌 칸 안의 알림 글은 안 보이므로 `recSt` 가 **맨 위 칸에도** 같은 글을 쓴다(예: 「지원하지 않는 음성 형식(.txt)」) "
       "⑥🔴이름 통일 10곳 — 안내문은 「📁 녹음 파일 올리기」, 단추는 「📁 음성 파일 올리기」로 **서로 달라** 더 찾기 어려웠다 "
       "⑦🔴`.mf-section` 의 display 가 hidden 을 덮어 `#recUpTop[hidden]{display:none !important}` 필요. "
       "검증=화면 22(운영 코드로는 2개 실패 뒤 중단 — 단추가 없어 시험이 못 이어감) · 회귀 " + REG + " · 표준 검사기. meeting_form.html]" + nl)

if len(sys.argv) > 3:
    NEW = NEW.replace(REG, sys.argv[3])
assert REG not in NEW, "회귀 결과를 셋째 인자로 넣을 것"
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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-10-05 v5H226z1138[" in chk
assert chk.count(nl + "REM   - " + prev) == 1, "직전 기록이 한 줄 아래로 밀리지 않았다"
print("[OK] BAT 갱신", len(raw), "→", len(data))
