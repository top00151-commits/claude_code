# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 🎙 음성 메모 (z1144)
사용: py patch_bat44.py <원본 bat> <결과 bat> <검증 결과>"""
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
NEW = ("REM   LAST UPDATE: 2026-10-08 v5H226z1144[🎙 **음성 메모 — 회의가 아닌 녹음도 정리**"
       "(대표 지시 2026-10-08 「회의록 말고 일반적인 의견 내용을 녹음한 걸 정리해주는 것도 필요해」). "
       "①왼쪽 메뉴 `🎙 음성 메모`(M-00-26) → `+ 새 메모` → **📁 녹음 파일 올리기 한 번**이면 "
       "음성→글자→정리(요점·할 일)까지 자동 · 제목도 AI 가 지어 준다 "
       "②대표 결정 = 쓰임새 네 가지 모두(떠오른 생각·전화 통화·현장 메모·말로 하는 보고) · **전 직원** · **내 것만 보임** "
       "③🔴**회의록(meetings) 표와 섞지 않았다** — 거긴 이음과 얽혀 있어(회의 카드·참석자 동기화·삭제 연동) "
       "조건 한 군데만 빠져도 개인 메모가 이음 카드로 샌다 → 새 표 `voice_notes`(마이그 m_z1144) "
       "④🔴**녹음 알맹이는 회의록과 한 벌** — `_stt_one` 에 `progress=` 만 더해 같이 쓴다(두 벌이면 한쪽만 고치는 사고) · "
       "「우리 회사 말」 바로잡기(z1142)도 같은 한 벌 "
       "⑤🔴**정리 틀은 새로** — 회의용(안건·결정사항·참석자 귀속)을 혼자 말한 녹음에 씌우면 없는 결정을 지어낸다 → "
       "`ai_extract_note()` 는 요점·할 일·나온 이름만 "
       "⑥개인 메모라 활동 기록에 안 남기고, 지우면 녹음 파일도 함께 지운다. "
       "검증=화면 32(운영 코드로는 표가 없어 못 돎 · 남의 메모는 화면·API 모두 404) · " + REG + " · 표준 검사기 · JS 문법. "
       "🔴시험 교훈: 휴대폰 UA 묶음은 1.2초짜리 **앱 설치 안내 팝업**과 경주한다 → 꺼 두고 본디만 잰다(3묶음 고침). "
       "voice_notes.html · voice_note_form.html · m_z1144_voice_note.py · ai_client.py · main.py · chrome.html]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-10-08 v5H226z1144[" in chk
assert chk.count(nl + "REM   - " + prev) == 1, "직전 기록이 한 줄 아래로 밀리지 않았다"
print("[OK] BAT 갱신", len(raw), "→", len(data))
