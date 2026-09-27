# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 휴대폰 녹음 화면 단순화 (z1130)
사용: py patch_bat30.py <원본 bat(직전 z1127)> <결과 bat> <회귀 결과>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-27 v5H226z1129[" in s, "직전 기록(z1129 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

REG = "__REG__"
NEW = ("REM   LAST UPDATE: 2026-09-27 v5H226z1130[회의록 — 휴대폰 녹음 화면 단순화(휴대폰은 녹음기 한 길만) + 「녹음 시작」 먹통 고침. "
       "①🔴 버그: 「휴대폰 녹음기로 녹음할게요」가 _phrecChosen 을 켜 둔 채 두어 recStart 가 조용히 되돌아갔다"
       "(대표 신고 · 화면 시험으로 재현 · 서버 요청 0건) → 사람이 「녹음 시작」을 직접 누르면 표시를 푼다 "
       "②대표 결정 「휴대폰은 녹음기 한 길만」 → 안내 2줄(홈 화면 「음성 녹음」 → 공유 → KNK WORKS) + 「📁 올리기」만 남기고 "
       "이 화면 녹음·짧은 녹음·기기별 안내는 「다른 방법」 접기 안으로(녹음 시작·멈춘 녹음 상자 뜨면 자동 펼침) "
       "③이음 「▶ 회의 시작」 30초 자동 시작 삭제(화면을 떠나 있으면 빈 녹음) ④옛 고르기 상자는 안드로이드에서 안 씀 · 아이폰·PC 무변경. "
       "검증=새 화면 33(고치기 전 파일로는 4) · 회귀 " + REG + " · 표준 검사기(인라인 194). meeting_form.html]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-27 v5H226z1130[" in chk
assert chk.count(nl + "REM   - 2026-09-27 v5H226z1129[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
