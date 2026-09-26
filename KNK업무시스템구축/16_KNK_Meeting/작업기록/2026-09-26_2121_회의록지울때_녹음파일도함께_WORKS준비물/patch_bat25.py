# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 회의록을 지우면 녹음 파일도 함께 (z1125)
사용: py patch_bat25.py <원본 bat(직전 z1124)> <결과 bat> <회귀 결과>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-22 v5H226z1124[" in s, "직전 기록(z1124 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

REG = "__REG__"
NEW = ("REM   LAST UPDATE: 2026-09-26 v5H226z1125[회의록 — 🗑 삭제하면 그 회의의 녹음 파일도 서버에서 함께 지움"
       "(대표 결정 09-26 「지울때 함께 지워」 · 전에는 DB 줄만 지우고 meeting_audio/meeting_<번호>/ 가 서버에 남았다 — 화면에선 안 보이지만 파일은 남음). "
       "①새 도우미 _meeting_audio_purge — 그 회의 폴더 하나만(폴더 이름·자리 다시 확인 · meeting_audio 밖이나 _share(회의 정해지기 전 파일)는 안 건드림) · "
       "지우다 실패해도 회의록 삭제는 유지(기록만) · 디스크가 느릴 수 있어 스레드에서 "
       "②WORKS 🗑 삭제와 이음 🗓 삭제 입구(msg/delete) 둘 다에서 호출 — 🔴이음과 무관한 회의 길에는 run_in_threadpool 이름이 없어 부르는 자리마다 불러옴 · "
       "이음 입구는 실제로 지웠을 때(result=deleted)만 "
       "③확인 창 글에 「녹음 파일도 서버에서 지워집니다」 한 마디. "
       "검증=서버 19(이음 무관 회의·이음 회의·폴더 없음·권한 없음·못 닿음·kept·none·지우기 실패·이상한 번호·_share 보존·확인 창 글 · 고치기 전 파일로는 실패) · "
       "회귀 " + REG + " · 표준 검사기(인라인 194). main.py·meeting_form.html]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-26 v5H226z1125[" in chk
assert chk.count(nl + "REM   - 2026-09-22 v5H226z1124[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
