# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 정리 글 바로 고치기 (z1139)
사용: py patch_bat39.py <원본 bat> <결과 bat> <회귀 결과>"""
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
NEW = ("REM   LAST UPDATE: 2026-10-06 v5H226z1139[회의록 — **「📋 회의록 정리」 글을 사람이 바로 고친다**"
       "(대표 지시 2026-10-05 「음성 인식이 잘못되어 잘못 작성한 부분은 어떻게 수정하지?」). "
       "①전까지 정리 글은 **읽기 전용**이고 서버도 **AI 정리로만** 썼다 → 낱말 하나를 고치려 해도 원문을 고쳐 "
       "「🔄 다시 정리」로 AI 를 통째로 다시 돌려야 했고 **다른 문장 표현까지 바뀌었다** "
       "②새 입구 `POST /api/meeting/{mid}/summary` — 고친 글을 그대로 저장(🔴**AI 를 부르지 않는다**) · "
       "권한은 회의록 고치기와 같음(참석자 포함 z1133) · 먼저 저장 충돌(base_ts) 409 · 활동기록 `meeting_summary_edit` 로 누가 고쳤는지 남김 · "
       "20000자 상한 · 앞뒤 빈칸만 다듬고 줄바꿈은 보존 "
       "③화면 — 정리 칸 머리에 「✏ 고치기」(고칠 수 있는 사람에게만) · 누르면 그 자리가 글칸으로 · 「💾 정리 저장」·「취소」 · "
       "🔴`[hidden]` 을 이기는 `!important`(display 가 hidden 을 덮는다) "
       "④🔴손으로 고친 뒤 「🔄 다시 정리」를 누르면 **한 번 묻는다**(고친 글이 사라지므로 · 이 화면에서 고친 경우) "
       "⑤결정사항·할 일·회의 원문·제목·장소는 **안 건드린다**. "
       "검증=서버 27(운영 코드로는 18 실패) · 화면 23(운영 코드로는 1 실패 뒤 중단) · 회귀 " + REG + " · 표준 검사기. "
       "main.py · meeting_form.html]" + nl)

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
data = out.encode("utf-8")
with open(DST, "wb") as f:
    f.write(data)
chk = open(DST, "rb").read().decode("utf-8")
assert chk.startswith("﻿") == s.startswith("﻿")
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-10-06 v5H226z1139[" in chk
assert chk.count(nl + "REM   - " + prev) == 1, "직전 기록이 한 줄 아래로 밀리지 않았다"
print("[OK] BAT 갱신", len(raw), "→", len(data))
