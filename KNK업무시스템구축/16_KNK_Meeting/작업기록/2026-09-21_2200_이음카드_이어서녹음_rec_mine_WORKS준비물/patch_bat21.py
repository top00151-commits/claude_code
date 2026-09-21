# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 이음 회의 카드용 msg/status 에 rec_mine 한 칸 (z1121)
사용: py patch_bat21.py <원본 bat(직전 z1120)> <결과 bat>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-21 v5H226z1120[" in s, "직전 기록(z1120 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

NEW = ("REM   LAST UPDATE: 2026-09-21 v5H226z1121[회의록 — 이음 회의 카드용 msg/status 에 rec_mine(보는 사람이 그 녹음을 시작했나) 한 칸"
       "(대표 지시 09-21 22시 「만들어줘」: 창을 ✕ 로 닫아 멈춘 녹음 — 이음 카드 단추를 녹음하던 사람에겐 「🎙 이어서 녹음」으로 · 세션 10 요청). "
       "이음은 보는 사람이 녹음하던 사람인지 모른다 → WORKS 가 알려 줌: rec_mine = 녹음이 열려 있고(recording) 그 녹음을 시작한 사람(rec_json.by) = 보는 사람(employee_no) · "
       "그 밖·보는 사람 못 찾음 = false · 정리가 끝난(done) 회의에 더 녹음하다 닫아도 본인은 true · 다른 칸·주소 그대로(추가만 — 옛 이음은 무시) · "
       "WORKS 회의 화면 REC.mine(z1120 · 본인이면 묻지 않고 한 번에)과 같은 판단(_rec_view(m, viewer)). "
       "검증=서버 14(본인 true·대표 false·녹음한 사람 바뀌면 따라감·끝나면 false·done+녹음 중·모르는 사번·회의록 없음·키 · 고치기 전 파일로는 실패) · "
       "회귀 이음 상태 14·모아보기 17·녹음 서버 55·공유 받기 48 · 표준 검사기(인라인 194). main.py]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-21 v5H226z1121[" in chk
assert chk.count(nl + "REM   - 2026-09-21 v5H226z1120[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
