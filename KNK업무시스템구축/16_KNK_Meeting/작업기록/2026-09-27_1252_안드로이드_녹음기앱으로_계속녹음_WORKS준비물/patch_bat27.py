# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 안드로이드 「📱 녹음기 앱 열기」 (z1127)
사용: py patch_bat27.py <원본 bat(직전 z1126)> <결과 bat> <회귀 결과>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-26 v5H226z1126[" in s, "직전 기록(z1126 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

REG = "__REG__"
NEW = ("REM   LAST UPDATE: 2026-09-27 v5H226z1127[회의록 — 안드로이드 녹음: 「📱 녹음기 앱 열기」를 첫 선택으로(다른 앱을 봐도 계속 녹음)"
       "(대표 실사 09-26: capture 로 연 녹음기는 **불려 나온 모드**라 다른 앱으로 넘어가면 녹음을 끝내고 저장하고 길이 상한도 있다 — 대표 사진 「최대 05:16」. "
       "그래서 옛 부제 「다른 앱을 봐도 끊기지 않아요」는 거짓이었다). "
       "①새 단추 = 녹음기 **앱 자체**를 여는 intent(LAUNCHER · 삼성=com.sec.android.app.voicenote · 그 밖=com.google.android.apps.recorder) → 알림줄에 남아 계속 녹음 "
       "②끝난 파일 = 녹음기 「공유 → KNK WORKS」(설치 앱) 또는 「📁 음성 파일 올리기」 "
       "③옛 단추는 「📱 녹음기로 바로 녹음(짧은 회의)」로 작게 · 사실대로(다른 앱으로 가면 저장되고 끝남) "
       "④못 열면 S.browser_fallback_url 로 ?recapp=manual 돌아와 손으로 여는 길 안내(상세=상자·새 회의록=상태줄) "
       "⑤기기별 안내·착지 안내·상자 글 전부 사실대로. "
       "검증=새 화면 시험 31(단추·차례·intent 주소·삼성/구글·못 열었을 때·아이폰PC 숨김·안내문 · 고치기 전 파일로는 단추가 없어 실패) · "
       "휴대폰 3종 새 문구 사본(45·26·25) · 창 닫힌 녹음 74 · 회귀 " + REG + " · 표준 검사기(인라인 194). meeting_form.html]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-27 v5H226z1127[" in chk
assert chk.count(nl + "REM   - 2026-09-26 v5H226z1126[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
