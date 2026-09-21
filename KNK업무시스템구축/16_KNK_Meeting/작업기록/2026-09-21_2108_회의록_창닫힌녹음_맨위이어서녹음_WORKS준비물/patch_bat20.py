# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 창을 닫아(✕) 멈춘 녹음: 「🎙 이어서 녹음」 상자를 화면 맨 위로 (z1120)
사용: py patch_bat20.py <원본 bat(직전 z1119)> <결과 bat>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-21 v5H226z1119[" in s, "직전 기록(z1119 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

NEW = ("REM   LAST UPDATE: 2026-09-21 v5H226z1120[회의록 — 창을 닫아(✕) 멈춘 녹음: 「🔴 녹음 중이던 회의 · 🎙 이어서 녹음」 상자를 화면 맨 위로"
       "(대표 신고 09-21 사진=이음 회의 카드: 아이폰 웹 녹음 중 녹음 창을 ✕ 로 닫으면 다시 녹음하러 찾아 들어가기가 너무 복잡 → 카드를 누르면 「이어서 녹음」이 있는 화면으로 바로). "
       "운영 실측=회의 41(안지연 프로 아이폰): ▶ 회의 시작 → 70초(조각 8) → ✕ → 카드 「📋 회의록 열기」 → /meetings/41 → 목록으로 헤맴 → 다시 들어와 28초. "
       "원인=카드는 이미 그 화면으로 보냄 · 상자(z1113)가 휴대폰 칸 순서 규칙에 없어 order:50 = 맨 아래(아이폰 화면 844px 에서 1,822px 아래 · 「끝내고 정리」가 첫 단추). "
       "①상자를 화면 맨 위(자동 정리 카드 위 · 휴대폰 order:0) ②「🎙 이어서 녹음」 첫 단추·「⏹ 녹음 끝내고 정리」 둘째·높이 44px "
       "③이어서 녹음 → 녹음 칸(띠·일시정지·종료)도 맨 위(휴대폰 .recfront · PC 스크롤 · 녹음 띠가 붙으며 크롬이 화면을 157px 밀어 올리는 것 되잡음) · 안드로이드는 z1116 「📱 휴대폰 녹음기로 녹음하시겠어요?」 상자 함께 · 마이크를 못 열면 상자 되살림 "
       "④남이 시작한 녹음이면 한 번 묻기(대표·관리자·등록 담당이 카드를 열어 보다가 누르면 그 사람 화면 녹음이 멈추므로 · 본인 녹음은 묻지 않고 한 번에) "
       "⑤이 화면에서 녹음이 시작되면(녹음 추가·자동 녹음) 상자 치움(두 번째 녹음기 방지) "
       "⑥(안드로이드) 상자를 두고 녹음기를 바로 누르면 열려 있던 내 녹음을 먼저 닫음 — 전엔 끊긴 조각이 정리에서 빠지고 서버가 계속 「녹음 중」(고치기 전 파일로 재현) "
       "⑦아이폰 안내 한 줄: 실수로 창을 닫았으면 이음 카드 「📋 회의록 열기」 → 맨 위 「🎙 이어서 녹음」. 서버·이음 변경 없음. "
       "검증=화면 74(아이폰 본인·대표 남의 녹음 묻기·끝내기 묻기·안드로이드 넘기기 세 조각 순서·녹음기 바로·남의 녹음 안 닫음·PC·본인 끝내기·자동 녹음 착지·녹음 없음·마이크 막힘·안내 · 고치기 전 파일로는 실패) · "
       "회귀 녹음 화면 27·휴대폰 폭 31·뒤로 가기 35·휴대폰 녹음기 44·넘기기 26·녹음기 기본 25·공유 화면 16·마이크 안내 16·나갈 때 알림 62·녹음 서버 55·공유 받기 48·이음 상태 14 · 표준 검사기(인라인 194). meeting_form.html]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-21 v5H226z1120[" in chk
assert chk.count(nl + "REM   - 2026-09-21 v5H226z1119[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
