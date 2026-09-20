# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 이음 「▶ 회의 시작」 착지에서 안드로이드는 녹음기가 기본 (z1118)
사용: py patch_bat18.py <원본 bat(직전 z1117)> <결과 bat>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-20 v5H226z1117[" in s, "직전 기록(z1117 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

NEW = ("REM   LAST UPDATE: 2026-09-20 v5H226z1118[회의 녹음 — 이음 「▶ 회의 시작」 착지에서 **안드로이드는 휴대폰 녹음기가 기본**"
       "(대표 지시 2026-09-20: 「이음에서 회의 시작하기 누르면 웹으로 우선 녹음이 되는데, 이걸 기본으로 안드로이드 녹음기로 되면 다 해결될 것 같다. "
       "아이폰 iOS 는 지금 경우를 적용해야 하고」). "
       "전(z1116): 착지하면 이 화면 녹음이 먼저 켜지고 그 위에 「녹음기로 바꾸기」 안내. 이제: 안드로이드는 **이 화면 녹음을 아예 켜지 않는다**. "
       "①착지 상자가 「🔴 아직 녹음이 시작되지 않았습니다」 + 큰 단추 「📱 녹음기로 회의 녹음 시작」 — 한 번 누르면 휴대폰 녹음기가 열리고, "
       "마치면 파일이 돌아와 자동으로 글자·정리(웹 녹음 조각이 아예 없어 정리도 한 덩이) "
       "②🔴브라우저는 '사람이 누른 것' 없이 녹음기를 못 연다 → 한 번 누르는 것은 없앨 수 없다 → **30초 안에 아무것도 안 누르면** 예전처럼 이 화면 녹음을 켠다"
       "(아예 녹음이 없는 사고 방지 · 이음 회의 81 선례) · 그때 상자를 「녹음기로 바꾸기」로 바꾸고 **까닭을 상자에 남긴다**"
       "(상태줄은 녹음 시작 안내로 곧 덮이므로) · 누르면 30초 대기는 꺼진다(_phFallback) "
       "③`_phrecChosen` 이면 늦게 풀린 마이크로도 이 화면 녹음을 시작하지 않는다(autorecStartHere 이중 확인) "
       "④아이폰·PC 는 **지금 그대로**(착지 즉시 이 화면 녹음 자동 시작 · 아이폰은 z1115 안내 「다른 앱·다른 웹 화면으로 넘어가면 그동안 녹음 안 됨」). "
       "검증=화면 25(안드로이드: 상자 글·단추 글·이 화면 녹음 안 켜짐·서버도 아님·누르면 녹음기·파일 오면 자동 정리·조각 1개 / 30초 뒤 안전망·상자 전환·까닭 남김 / 아이폰·PC 그대로) · "
       "회귀 넘기기 26(ui_lead — z1118 기본에 맞춰 「🎙 녹음 시작」을 눌러 켠 뒤 넘기기 확인) · 뒤로 가기 35(블록 C 는 '누른 적 없이 자동 녹음'이 남는 아이폰으로 옮김) · "
       "휴대폰 녹음기 44 · 녹음 화면 27 · 휴대폰 폭 31 · 공유 받기 48 · 마이크 안내 16 · 표준 검사기(인라인 194). "
       "meeting_form.html]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-20 v5H226z1118[" in chk
assert chk.count(nl + "REM   - 2026-09-20 v5H226z1117[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
