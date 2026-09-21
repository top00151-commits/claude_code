# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — WORKS 「🗓 회의 카드 모아보기」 끝났는데 「지금 회의 중」 고침 (z1119)
사용: py patch_bat19.py <원본 bat(직전 z1118)> <결과 bat>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-20 v5H226z1118[" in s, "직전 기록(z1118 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

NEW = ("REM   LAST UPDATE: 2026-09-21 v5H226z1119[회의록 — 「🗓 회의 카드 모아보기」 탭: 끝났는데 「🔴 지금 회의 중」 고침"
       "(대표 신고 09-21: 이음 회의 카드 「라이프밸류…[코엔] 미팅」 11:00~12:00 이 15:51 에도 「회의 중」 → 이음 v815 로 고침(17:43) · "
       "세션 10 확인: WORKS 모아보기 탭(z1108)도 같은 판정을 복사해 써서 같은 문제). "
       "원인=WORKS 단계 started 가 **녹음 중**과 **「▶ 회의 시작」만 누르고 녹음 없음**을 둘 다 담는데(_meeting_msg_stage), "
       "탭 headState 가 started 면 끝나고 12시간 「회의 중」(뜻은 '녹음 중일 때만') · minutesHtml 은 시간 무관 「🔴 회의 진행 중 · 이름 녹음」 · "
       "탭 자료 /api/meetings/msg-cards 에 recording 칸이 없어 둘을 가를 수도 없었다(운영 같은 상태 4건 #40·#33·#31·#28). "
       "①msg-cards 의 minutes 에 recording·rec_secs(이음이 쓰는 msg/status 와 같은 값 · _rec_view) "
       "②윗줄 — recording===false 면 끝 시각에 종료 · 끝 뒤 12시간 「회의 중」은 녹음 중일 때만 · 시작 전·회의 시간 안에 누른 회의는 그대로 · 칸 없는 옛 응답은 예전대로 "
       "③아래 줄 — 녹음 중 「🔴 녹음 중 · 이름 · N분 저장됨」(1분 미만은 분 없음) · 녹음 없음·끝 전 「🔴 회의 진행 중 · 이름 · 녹음 안 됨」 · "
       "녹음 없음·끝 뒤 「⏹ 회의 끝남 · 이름 · 녹음 없음」(흐린 글 · 이음 v815 대표 결정 문구) · 아래 줄이 윗줄 판정(hs)을 따라가 30초 다시 그리기 때 두 줄이 함께 바뀜. "
       "검증=서버 17(자료에 recording·rec_secs · 이음 msg/status 와 5회의 모두 같은 값) · 화면 23(9경우 윗줄·아래 줄·묶음 · 시계 고정해 끝 시각 넘기면 두 줄 함께·묶음 이동) · "
       "회귀 모아보기 80·원래 화면 43 · 이음 상태 14 · 녹음 서버 55 · 공유 받기 48 · 휴대폰 녹음기 44 · 표준 검사기(인라인 194). main.py·meetings.html]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-21 v5H226z1119[" in chk
assert chk.count(nl + "REM   - 2026-09-20 v5H226z1118[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
