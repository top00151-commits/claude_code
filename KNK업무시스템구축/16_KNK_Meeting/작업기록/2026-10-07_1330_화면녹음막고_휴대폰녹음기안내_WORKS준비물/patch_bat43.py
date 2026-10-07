# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 이 화면 녹음 막고 휴대폰 녹음기 안내 (z1143)
사용: py patch_bat43.py <원본 bat> <결과 bat> <검증 결과>"""
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
NEW = ("REM   LAST UPDATE: 2026-10-08 v5H226z1143[회의록 — **이 화면에서 직접 녹음하는 길을 막고 「휴대폰 녹음기를 쓰세요」로 안내**"
       "(대표 지시 2026-10-07 「녹음하며 회의 단추를 누르면 휴대폰 녹음기를 사용하세요라고 안내 · 여기서 녹음하는 기능은 일단 막아 놓고」). "
       "①왜 — 이 화면 녹음은 **화면을 켜 둘 때만** 소리가 들어오고(아이폰은 다른 앱으로 가면 끊김), "
       "2026-10-07 대회의실 진단에서 멀리 담긴 소리는 받아쓰기가 무너졌다(같은 회의 앞 9분 -40dB·뒤 5분 -25dB → 일치율 73.2% vs 95.4%) "
       "②막는 범위(대표 결정) = ⓐ새 회의록 「🎙 녹음하며 회의」 ⓑ상세 「🎙 녹음 추가」 **둘뿐** · PC 도 함께 "
       "③🔴**이음 「▶ 회의 시작」 자동 녹음(`?autorec=1`)·「🎙 이어서 녹음」·녹음 중 「⏹ 종료」는 그대로** — "
       "그 길들은 단추를 거치지 않고 `recStart()` 를 직접 부르므로 누름 처리만 막으면 갈린다 "
       "(autorec 은 주소를 바로 지우므로 단추에 `data-autorec` 표시를 남겨 통과시킨다) "
       "④누르면 **마이크를 아예 안 부르고** 안내 상자가 뜬다(「먹통」 금지 — 까닭과 갈 길을 보여 준다) · "
       "보조글 「누르면 바로 녹음」→「휴대폰 녹음기로 녹음해 주세요」 · 새 회의록 안내문도 휴대폰 녹음기 기준으로 "
       "⑤단추 **이름은 그대로**(이음 안내 4개 언어가 「🎙 녹음하며 회의」를 쓴다) "
       "⑥🔴**새 회의록은 이제 「📁 녹음 파일 올리기」가 만든다** — 올리면 POST /api/meeting → 글자 변환 → AI 정리까지 자동(시험으로 확인). "
       "검증=화면 24(운영 코드로는 14 실패 · 마이크 호출 0회 · autorec 은 그대로 녹음) · " + REG + " · 표준 검사기 · JS 문법. "
       "옛 시험 4개(ui_rec·ui_back·ui_simple·ui_phrec)는 **새 의도로 고쳤다**(제품을 시험에 맞추지 않음). "
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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-10-08 v5H226z1143[" in chk
assert chk.count(nl + "REM   - " + prev) == 1, "직전 기록이 한 줄 아래로 밀리지 않았다"
print("[OK] BAT 갱신", len(raw), "→", len(data))
