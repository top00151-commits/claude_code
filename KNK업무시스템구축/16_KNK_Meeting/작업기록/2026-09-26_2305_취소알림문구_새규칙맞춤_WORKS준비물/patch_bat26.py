# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 취소 알림 글 새 규칙 맞춤 (z1126)
사용: py patch_bat26.py <원본 bat(직전 z1125)> <결과 bat> <회귀 결과>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-26 v5H226z1125[" in s, "직전 기록(z1125 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

REG = "__REG__"
NEW = ("REM   LAST UPDATE: 2026-09-26 v5H226z1126[회의록 — 회의 취소 알림 글을 새 규칙에 맞춤"
       "(대표 결정 09-26 「다른 참석자 있으면 알림」 · 이음 v821 23:19 LIVE: 시작 전·후 구분 없이 **나 말고 참석자가 있으면** 취소 알림 · 혼자 만든 회의는 조용히). "
       "발단=대표 「삭제하면 그냥 삭제돼서 기존 회의를 취소한 건지 원래 없었던 건지 헷갈린다」. "
       "①삭제 뒤 알림에서 「시작 전 회의라」를 뺌 → 「🔔 참석자 N명에게 「회의가 취소되었습니다」 알림이 갔습니다」 "
       "②첫 확인 창(이음 회의도 함께 지울 때)에 「(나 말고 참석자가 있으면 「회의가 취소되었습니다」 알림이 갑니다)」 한 줄 · 옛 규칙을 말하던 주석도 교체. "
       "검증=서버 21 · 화면 13(고치기 전 파일로는 각각 2·3개 실패) · 회귀 " + REG + " · 표준 검사기(인라인 194). meeting_form.html]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-26 v5H226z1126[" in chk
assert chk.count(nl + "REM   - 2026-09-26 v5H226z1125[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
