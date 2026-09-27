# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 「⏹ 회의 종료」 단추 + 공유 안내 (z1131)
사용: py patch_bat31.py <원본 bat(직전 z1130)> <결과 bat> <회귀 결과>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-27 v5H226z1130[" in s, "직전 기록(z1130 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

REG = "__REG__"
NEW = ("REM   LAST UPDATE: 2026-09-27 v5H226z1131[회의록 — 「⏹ 회의 종료」 단추(예정 끝 시각 전에 끝났을 때) + 녹음 공유 안내를 사실대로. "
       "①대표 질문 「회의 종료는 어디서 선택하지? 종료시간 이전에 끝났을 때는?」 — 지금까지는 누를 곳이 없었다"
       "(규칙: 녹음이 붙거나 정리되면 즉시 종료 · 녹음 없으면 예정 끝 시각 · 녹음 중이면 끝 뒤 12시간) "
       "②meetings.ended_at(마이그 m_z1131_meeting_end · idempotent) + POST /api/meeting/{id}/end(undo 포함) "
       "③상세 머리줄에 「⏹ 회의 종료」/「✅ 종료됨 · 시:분」/「↩ 종료 되돌리기」 — 이음 회의에만 · 작성자(총괄)·관리자/대표·이음 등록자 "
       "④이음·모아보기에 넘기는 칸에 ended·ended_at → 모아보기 카드는 시간 규칙보다 먼저 본다(이음 카드는 세션 10 요청) "
       "⑤🔴.btn 의 display 가 hidden 을 덮어 !important 로 숨김(rec-phone 과 같은 함정) "
       "⑥공유 안내: 대표 폰 공유 목록에 WORKS 가 없었다(이음만 설치) → 「📁 녹음 파일 올리기」 먼저 · 공유는 「앱을 깔아 두면(크롬 ⋮ → 앱 설치)」. "
       "검증=서버 23 · 화면 22(운영 파일로는 ended_at 칸이 없어 안 돎) · 회귀 " + REG + " · 표준 검사기(인라인 194). "
       "main.py · meeting_form.html · meetings.html · migrations/m_z1131_meeting_end.py]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-27 v5H226z1131[" in chk
assert chk.count(nl + "REM   - 2026-09-27 v5H226z1130[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
