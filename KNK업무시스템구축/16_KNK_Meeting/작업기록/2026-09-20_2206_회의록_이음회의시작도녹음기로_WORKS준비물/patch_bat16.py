# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 이음 「▶ 회의 시작」 착지에서도 휴대폰 녹음기로 (z1116)
사용: py patch_bat16.py <원본 bat(직전 z1115)> <결과 bat>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-20 v5H226z1115[" in s, "직전 기록(z1115 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

NEW = ("REM   LAST UPDATE: 2026-09-20 v5H226z1116[회의 녹음 — 이음 회의 카드 「▶ 회의 시작」 착지에서도 휴대폰 녹음기로"
       "(대표 지시 2026-09-20: 「이음 카드에서도 회의 시작을 누르면 녹음기로 녹음될 수 있도록 해줘」). "
       "그 길 = WORKS /meetings/{id}?autorec=1 착지 → '이 화면 녹음'이 자동 시작(안전망으로 그대로 둠 · 안 누르면 아예 녹음이 없을 위험). "
       "①안드로이드 착지 화면 「🔧 다시 하기」 맨 위에 빨간 테두리 안내 상자 — 「📱 이 회의, 휴대폰 녹음기로 녹음하시겠어요?」 "
       "+ 까닭(다른 앱으로 넘어가면 그동안 소리가 안 들어옴 · 실측 95초) + 「📱 휴대폰 녹음기로 녹음」 큰 단추(z1115 단추를 이 상자로 옮김 — 입력은 하나뿐) "
       "②🔴z1115 결함 수리: 이 화면 녹음이 도는 중에 녹음기 단추를 누르면 **두 녹음이 겹쳤다** → 넘길 때 recStop 으로 깨끗이 마치고, "
       "rec-finish 로 지금까지 조각을 서버 '아직 글자로 안 바꾼 녹음'에 남기되 **정리는 하지 않는다**(_recHandoff) → "
       "녹음기 파일이 올라오면 그때 한 번만 정리해 _stt_worker 가 두 조각을 순서대로 이어 붙인다(서버 변경 없음) "
       "③늦게 열린 마이크로 이 화면 녹음이 되살아나지 않게(_phrecChosen — getUserMedia 가 늦게 풀려도 시작 안 함) "
       "④녹음기에서 파일 없이 돌아오면 4초 뒤 한 번 안내(지금까지 녹음은 서버에 있고 「🔄 다시 정리」로 이어 감) "
       "⑤🔴기존 결함: recPump 가 조각을 보낼 때마다 recBanner(true) 로 띠를 다시 켜서, 녹음이 끝난 뒤에도 「🔴 녹음 중」이 남았다"
       "(평소엔 바로 이어지는 자동 정리가 가려 안 보였다) → 녹음 중일 때만 다시 켠다. "
       "아이폰·PC 는 착지 상자 없음(아이폰은 녹음기를 못 엶 · z1115 안내 그대로 · PC 는 창을 내려도 마이크 유지). "
       "🔴브라우저는 '누른 것' 없이 녹음기를 못 연다 → 자동으로는 못 열고 한 번 누르게 한다. 이음 쪽 변경 없음. "
       "검증=화면 27(착지 상자·단추 위치·입력 1개·안전망 자동 녹음·넘기면 띠 꺼짐·서버 녹음 중 아님·정리 안 함·pending 1·파일 오면 정리 1회·두 조각 모두 글자·빈손 복귀 안내·PC/아이폰 그대로) · "
       "회귀 휴대폰 녹음기 44 · 뒤로 가기 35 · 녹음 화면 27 · 녹음 서버 55 · 300MB 37 · 마이크 안내 16 · 휴대폰 폭 31 · 표준 검사기(인라인 193). "
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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-20 v5H226z1116[" in chk
assert chk.count(nl + "REM   - 2026-09-20 v5H226z1115[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
