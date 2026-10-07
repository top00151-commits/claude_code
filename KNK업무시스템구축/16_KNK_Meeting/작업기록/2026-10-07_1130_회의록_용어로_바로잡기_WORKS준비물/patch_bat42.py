# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 회의록 「정리」가 우리 회사 말로 바로잡기 (z1142)
사용: py patch_bat42.py <원본 bat> <결과 bat> <검증 결과>"""
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
NEW = ("REM   LAST UPDATE: 2026-10-07 v5H226z1142[회의록 — **받아쓴 글의 잘못 들린 우리 회사 말을 「정리」에서 바로잡기**"
       "(대표 지시 2026-10-07 「MSCC가 아니고 MLCC 야... 해봐」). "
       "①왜 — 대회의실 녹음 진단에서 **소리가 작으면 AI가 메운다**를 증명(같은 회의 안 앞 9분 -40dB·뒤 5분 -25dB → "
       "같은 소리를 두 방식으로 받아쓴 글의 일치율 73.2% vs 95.4%). 못 들은 말은 못 살리지만 **아는 낱말**은 맥락으로 바로잡을 수 있다 "
       "②만든 것 = 관리자 → AI 설정에 「회의록에서 바로잡을 우리 회사 말」 칸(`app_settings.meeting_terms` · 빈 값=기본 목록 · `-`=끄기) → "
       "`ai_extract_meeting` 이 **회의 정보 뒤에** 그 목록을 붙여 보냄 "
       "③실측(같은 원문 3,648자·5회) = 표면장→**표면저항**·카트리스트→**파트리스트** 5/5 바로잡힘 · "
       "목록에만 있고 회의에 없던 말(코그넥스·YOLO·텔레센트릭) **0회**(억지로 안 넣음) · "
       "제목까지 바로잡으면 **MSCC 0 · MLCC 4** "
       "④🔴회의 **제목**에 틀린 말이 있으면 그 말만은 흔들린다 → 제목도 고쳐야 확실 "
       "⑤🔴**받아쓴 원문(body)은 한 글자도 안 바꾼다** — 정리 글에서만 바로잡는다 · "
       "`_MEETING_EXTRACT_SYSTEM` 본문 무접촉(실증된 프롬프트 불변). "
       "검증=서버 18(옛 코드 8 실패) · 화면 22 두 번(옛 코드는 칸이 없어 멈춤) · " + REG + " · 표준 검사기 · "
       "개념 추적기 6개 층. ai_client.py · main.py · admin_ai_settings.html]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-10-07 v5H226z1142[" in chk
assert chk.count(nl + "REM   - " + prev) == 1, "직전 기록이 한 줄 아래로 밀리지 않았다"
print("[OK] BAT 갱신", len(raw), "→", len(data))
