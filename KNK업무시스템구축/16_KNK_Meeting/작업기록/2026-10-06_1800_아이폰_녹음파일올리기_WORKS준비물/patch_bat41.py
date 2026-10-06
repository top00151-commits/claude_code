# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 아이폰 녹음 파일 올리기 (z1141)
사용: py patch_bat40.py <원본 bat> <결과 bat> <검증 결과>"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "REM   LAST UPDATE:" in s, "LAST UPDATE 줄 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
prev = s[s.index("REM   LAST UPDATE: ") + len("REM   LAST UPDATE: "):].split(nl)[0]
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl), "| 직전:", prev[:40])

REG = "__REG__"
NEW = ("REM   LAST UPDATE: 2026-10-06 v5H226z1141[회의록 — **아이폰에서 「📁 녹음 파일 올리기」가 먹통이던 것**"
       "(직원 신고 2026-10-06 박성수 프로 사번 317 · 아이폰 · `기산로 3.m4a` 15.5MB 30:10 「눌러도 반응이 없어」). "
       "①실측 — 서버에 **요청이 아예 안 들어왔다**(올리기 기록 0건) → 휴대폰 안에서 막힌 것(용량·서버 아님 · 같은 날 14:56 엔 성공) "
       "②고친 것 둘 = ⓐ고를 수 있는 파일 조건이 `audio/*` 하나뿐이라 아이폰이 좁게 봐 **녹음 파일이 안 눌림** → "
       "서버 `_MEETING_AUDIO_EXT` 와 **똑같이** 확장자 12개(.m4a .mp3 .mp4 .wav .webm .ogg .oga .aac .3gp .mpeg .mpga .caf)를 함께 적음"
       "(고를 수 있는데 서버가 퇴짜 놓는 일이 없게) ⓑ`display:none` 은 아이폰에서 **파일 고르기 창 자체가 안 열림** → "
       "`.knk-file-vh`(안 보이되 없는 것으로 만들지 않음 · 자리도 안 차지) "
       "③🔴「📱 녹음기로 바로 녹음」(recFileCap)의 accept 는 **그대로** — 확장자를 붙이면 녹음기 대신 파일 고르기가 열린다 "
       "④🔎**크롬으로는 아이폰 파일 고르기를 재현할 수 없다** → 박성수 프로 실물 확인 필요. "
       "검증=화면 16(옛 코드 4 실패) · 파일 고르기 창 열림 두 자리 · 실제 .m4a 올리기 · " + REG + " · 표준 검사기. "
       "meeting_form.html]" + nl)

if len(sys.argv) > 3:
    NEW = NEW.replace(REG, sys.argv[3])
assert REG not in NEW, "검증 결과를 셋째 인자로 넣을 것"
lines = s.split(nl)
for i, ln in enumerate(lines):
    if ln.startswith("REM   LAST UPDATE:"):
        lines[i] = NEW.rstrip("\r\n") + nl + "REM   - " + ln[len("REM   LAST UPDATE: "):]
        break
else:
    raise SystemExit("LAST UPDATE 줄 없음")
out = nl.join(lines)
data = out.encode("utf-8")
with open(DST, "wb") as f:
    f.write(data)
chk = open(DST, "rb").read().decode("utf-8")
assert chk.startswith("﻿") == s.startswith("﻿")
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-10-06 v5H226z1141[" in chk
assert chk.count(nl + "REM   - " + prev) == 1, "직전 기록이 한 줄 아래로 밀리지 않았다"
print("[OK] BAT 갱신", len(raw), "→", len(data))
