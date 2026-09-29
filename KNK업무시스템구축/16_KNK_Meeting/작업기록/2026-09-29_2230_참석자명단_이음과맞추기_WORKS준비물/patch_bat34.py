# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 이음에서 참석자를 바꾸면 WORKS 명단도 따라감 (z1134)
사용: py patch_bat34.py <원본 bat(직전 z1133)> <결과 bat> <회귀 결과>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-29 v5H226z1133[" in s, "직전 기록(z1133 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

REG = "__REG__"
NEW = ("REM   LAST UPDATE: 2026-09-29 v5H226z1134[회의록 — 이음에서 **참석자를 바꾸면** WORKS 회의록 명단도 따라간다(대표 지시 2026-09-29). "
       "①전까지는 명단이 이음 「▶ 회의 시작」을 누른 시점 값으로 굳어 있었다(회의록을 처음 만들 때만 채움) → "
       "z1133 부터 그 명단이 곧 권한이라 새 참석자가 아무것도 못 했다 "
       "②새 도우미 `_msg_sync_attendees` — 사번은 정확히 1명일 때만 연결 · 계정 없는 사람은 이름만 · "
       "뺄 사람만 빼고 새로 온 사람만 넣는다(멱등) · 참석자 칸 글도 이음 명단 순서로 다시 적음 "
       "③새 입구 `POST /api/meeting/msg/attendees`(서버 전용 공유키) — 이음이 참석자를 바꿔 저장한 뒤 한 번 부른다 · "
       "회의록이 없으면 아무것도 만들지 않고 result=none · 🔴이음을 되부르지 않음 · "
       "🔴참석자 칸이 아예 없는 본문은 400 으로 거절(실수로 전원 삭제 방지) "
       "④「▶ 회의 시작」이 다시 불려도 같은 도우미로 맞춘다(안전망) "
       "⑤🔴대표 결정 = 빠진 사람은 그 뒤로 못 고침(올린 것은 남음) · **녹음 중인 사람은 빼지 않음**(끝난 뒤 빠짐) · "
       "작성자·이음 등록 담당은 명단과 무관하게 그대로. "
       "검증=서버 48(운영 코드로는 25 실패) · 회귀 " + REG + " · 표준 검사기. main.py]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-29 v5H226z1134[" in chk
assert chk.count(nl + "REM   - 2026-09-29 v5H226z1133[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
