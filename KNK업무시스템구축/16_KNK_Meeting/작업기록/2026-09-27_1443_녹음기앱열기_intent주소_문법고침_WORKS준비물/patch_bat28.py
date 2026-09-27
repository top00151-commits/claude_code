# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 녹음기 앱 열기 주소 문법 고침 (z1128)
사용: py patch_bat28.py <원본 bat(직전 z1127)> <결과 bat> <회귀 결과>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-27 v5H226z1127[" in s, "직전 기록(z1127 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

REG = "__REG__"
NEW = ("REM   LAST UPDATE: 2026-09-27 v5H226z1128[회의록 — 「📱 녹음기 앱 열기」 주소를 문법대로 고침(데이터 부분 없는 intent:) + 못 열릴 수 있음을 사실대로. "
       "①🔴 z1127 주소 intent://#Intent;… 는 안드로이드가 남은 「//」를 그대로 요청의 데이터로 넣어(Intent.parseUri) "
       "MAIN·LAUNCHER 걸개(data 칸 없음)에 안 걸린다(IntentFilter.matchData: 걸개에 data 없으면 요청에도 없어야 맞음) → 어느 기종에서도 안 열리고 곧바로 fallback. "
       "→ intent:#Intent;action=…(호스트·경로는 크롬 문법에서 선택) "
       "②크롬 문서 「BROWSABLE 을 적어 둔 화면만 이 방법으로 열 수 있다」 → 녹음기가 그 표시를 안 가졌으면 그래도 안 열린다(대표 휴대폰에서만 판정) "
       "③그래서 화면 글도 사실대로: 단추 부제 「녹음기 앱에서 녹음하면 다른 앱을 봐도 안 끊겨요」 · 누른 뒤/상자/기기별 안내에 "
       "「크롬이 막아 안 열리는 기종도 있습니다 — 홈 화면에서 「음성 녹음」을 직접 열어 주세요(효과는 같습니다)」. "
       "라이브 실측(09-27): 운영에서 80분(147MB·1:19:49) 휴대폰 녹음 → 조각 4개(각 4.8MB) → 본문 23,099자(18:29:27~18:33:24) 성공 · ffmpeg 있음 · 한 파일 상한 300MB. "
       "검증=화면 시험 35(고치기 전 파일로는 6 실패) · 회귀 " + REG + " · 표준 검사기(인라인 194). meeting_form.html]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-27 v5H226z1128[" in chk
assert chk.count(nl + "REM   - 2026-09-27 v5H226z1127[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
