# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 참석자도 녹음·회의록 작성 (z1133)
사용: py patch_bat32.py <원본 bat(직전 z1131)> <결과 bat> <회귀 결과>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-27 v5H226z1131[" in s, "직전 기록(z1131 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

REG = "__REG__"
NEW = ("REM   LAST UPDATE: 2026-09-29 v5H226z1133[회의록 — **회의 참석자도** 녹음·녹음파일 올리기·회의록 작성·회의 종료(대표 지시 2026-09-28). "
       "①전까지는 작성자·이음 등록 담당·관리자/대표만 손댈 수 있었고 참석자는 보기만 됐다 "
       "②`_can_edit_meeting` 에 그 회의 참석자(meeting_attendees.user_id) 추가 · `_can_end_meeting` 도 같게 · "
       "🗑 삭제는 그대로(작성자·관리자/대표 — 대표 결정) "
       "③한 번에 열리는 것 = 녹음 시작/조각/끝내기 · 📁 올리기 · 공유로 붙이기 · 음성→글자 · 🔄 다시 정리 · 본문/제목 저장 · "
       "결정사항·할 일 추가/삭제 · 프로젝트/기회 연결 · ⏹ 회의 종료 "
       "④참석자 명단은 이음 「▶ 회의 시작」이 **사번으로** 연결해 저장(운영 46줄 중 43줄 연결) · 외부 참석자는 계정이 없어 해당 없음 "
       "⑤🔴권한 함수가 DB 를 보므로 열린 커서를 받게 하고(15곳 전달), 안 넘기면 짧게 새로 열어 본다(조용히 권한이 사라지지 않게 · WAL). "
       "검증=서버 30(운영 코드로는 10 실패 뒤 중단) · 화면 12(운영 코드로는 5 실패) · 회귀 " + REG + " · 표준 검사기. main.py]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-29 v5H226z1133[" in chk
assert chk.count(nl + "REM   - 2026-09-27 v5H226z1131[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
