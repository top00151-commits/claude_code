# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 모아보기 단추 이름 「📋 회의록 열기」 (z1124)
사용: py patch_bat24.py <원본 bat(직전 z1123)> <결과 bat> <회귀 결과>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-22 v5H226z1123[" in s, "직전 기록(z1123 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

REG = "__REG__"
NEW = ("REM   LAST UPDATE: 2026-09-22 v5H226z1124[회의록 「🗓 회의 카드 모아보기」 — 단추 이름 「📝 회의록 화면」 → 「📋 회의록 열기」"
       "(대표 지시 09-22 08시 「회의록 열기로 맞춰」 · 이음 회의 카드 v807 과 같은 이름 · 진행 중·정리 중·실패 · 녹음하던 본인이 아닌 사람). "
       "가는 곳·여는 방식은 그대로(이름만) · 카드 빈 곳 누르기 주석도 새 이름으로. "
       "검증=고치기 전 파일로 새 이름 시험 실패(모아보기 원래 화면·삭제 화면) · 회귀 " + REG + " · 표준 검사기(인라인 194). "
       "meetings.html]" + nl)

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
with io.open(DST, "w", encoding="utf-8", newline="") as f:
    f.write(out)
chk = open(DST, "rb").read().decode("utf-8")
assert chk.startswith("﻿") == s.startswith("﻿")
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-22 v5H226z1124[" in chk
assert chk.count(nl + "REM   - 2026-09-22 v5H226z1123[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
