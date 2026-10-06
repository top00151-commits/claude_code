# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 받아쓰기 모델 교체 (z1140)
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
NEW = ("REM   LAST UPDATE: 2026-10-06 v5H226z1140[회의록 — **받아쓰기 모델을 이음과 같은 것으로 교체**"
       "(대표 지시 2026-10-06 「녹음 파일을 너무 잘못 분석한 것 같다 · 교정 사전으로 될 일이 아니다」). "
       "①같은 녹음 5분을 다섯 번 받아써 비교(회의 53) → 🔴**지금 모델(whisper-1)은 회의 앞 20초를 통째로 빠뜨렸다** · "
       "코그넥스→「코고넥스」·동글→「동굴」·OKNG→「OK 엔지」·2D→「3D」·기술적으로→「교수적으로」 "
       "②`gpt-transcribe` 는 그 낱말을 거의 다 맞히고 **더 빠름**(15초→8~10초)·값도 더 쌈 · 이음은 2026-07-31부터 쓰는 중 "
       "③`ai_client.ai_transcribe` 한 함수만 교체 — 모델=`KNK_WORKS_STT_MODEL`(기본 gpt-transcribe) · "
       "실패하면 `KNK_WORKS_STT_FALLBACK`(기본 whisper-1)로 **자동 한 번 더** · "
       "신형은 `response_format=json`+`extra_body.languages`(복수) / 구형은 `language`(단수) "
       "④🔴**넣지 않은 것**: 한국어 지정(효과 없고 **베트남 직원 52명** 회의를 망칠 위험) · 힌트 낱말(이득 없음) · "
       "소리 품질 96kbps(효과 증명 못 함) — 셋 다 재 보고 뺐다 "
       "⑤🔧되돌리기 = 환경변수 `KNK_WORKS_STT_MODEL=whisper-1` 한 줄. "
       "검증=서버 22(옛 코드로는 바로 중단) · 실제 녹음으로 끝까지 성공(10초·2,011자) · " + REG + " · 표준 검사기. "
       "ai_client.py]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-10-06 v5H226z1140[" in chk
assert chk.count(nl + "REM   - " + prev) == 1, "직전 기록이 한 줄 아래로 밀리지 않았다"
print("[OK] BAT 갱신", len(raw), "→", len(data))
