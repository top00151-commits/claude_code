# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 녹음기 앱 열기 단추 삭제·직접 열기 안내 (z1129)
사용: py patch_bat29.py <원본 bat(직전 z1127)> <결과 bat> <회귀 결과>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-27 v5H226z1128[" in s, "직전 기록(z1128 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

REG = "__REG__"
NEW = ("REM   LAST UPDATE: 2026-09-27 v5H226z1129[회의록 — 안드로이드 녹음: 「📱 녹음기 앱 열기」 단추를 없애고 「홈 화면에서 직접 열기」 3단계 안내로. "
       "①🔴 대표 실물 4번 모두 크롬이 앱 열기를 거부(운영 로그 ?recapp=manual 4회) — 크롬 문서 「BROWSABLE 을 적어 둔 화면만 이 방법으로 열 수 있다」 "
       "→ 삼성 「음성 녹음」은 웹에서 못 연다(z1127·z1128 방향이 틀렸다) "
       "②옛 단추는 누를 때 회의록을 먼저 만들어 실패할 때마다 빈 회의록이 남았다(46·47·49 — 대표 허락 아래 정리) "
       "③새 회의록 화면 = 3단계 안내 카드(홈 화면 「음성 녹음」 → 공유 → KNK WORKS → ＋ 새 회의록으로 정리) "
       "④상세 화면 = 「📱 휴대폰 녹음기로 녹음할게요」(이 회의 표시 + 30초 자동 시작 취소 · 화면 이동 없음) "
       "⑤이음 「▶ 회의 시작」 고르기·기기별 안내·상자 글 전부 새 길에 맞춤 · intent 코드/주소 전부 삭제. "
       "검증=새 화면 33(고치기 전 파일로는 실패) · 회귀 " + REG + " · 표준 검사기(인라인 194). meeting_form.html]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-27 v5H226z1129[" in chk
assert chk.count(nl + "REM   - 2026-09-27 v5H226z1128[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
