# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 휴대폰 녹음기 「공유 → WORKS」 자동 정리 (z1117)
사용: py patch_bat17.py <원본 bat(직전 z1116)> <결과 bat>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-20 v5H226z1116[" in s, "직전 기록(z1116 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

NEW = ("REM   LAST UPDATE: 2026-09-20 v5H226z1117[회의 녹음 — 휴대폰 녹음기 「공유 → KNK Eum WORKS」 = 회의록에 붙이고 자동 정리"
       "(대표 지시 2026-09-20: 「녹음기로 녹음한 것은 종료 누르면 자동으로 요약되는 걸로 만들어야 해」 → 대표 선택 「녹음기에서 공유 → WORKS 로 바로」). "
       "평소 길(z1115)은 이미 자동이다 — 녹음기가 파일을 회의록 화면으로 직접 돌려주고 올리기·변환·정리가 저절로 이어진다. "
       "남은 구멍 = 회의가 길어 크롬이 그 화면을 버리면 돌려줄 곳이 없다 → 두 번째 길을 둔다. "
       "①manifest 에 share_target(action=/share/audio · POST · multipart/form-data · files[audio]=audio/*) → 녹음기의 「공유」 목록에 WORKS 가 뜬다 "
       "⚠설치된 앱(WebAPK)에만 뜨고, manifest 가 바뀌면 크롬이 앱을 다시 만들 때까지(보통 하루) 걸린다 — 급하면 앱을 지우고 다시 설치 "
       "②POST /share/audio = 받아서 meeting_audio/_share/ 에 잠깐 보관(표 `s_<사번>_<시각>_<8자리>` · 하루 지나면 자동 청소) → 새 화면 share_audio.html "
       "③그 화면이 localStorage 표시(z1115 knk_mtg_phonerec · 24시간)를 보고 **묻지 않고** 그 회의록에 붙인 뒤 /meetings/{id}?auto=1 로 보낸다(= 자동 정리) · "
       "표시가 없으면 「＋ 새 회의록으로 정리」 또는 최근 회의(내가 고칠 수 있는 것 12개) 고르기 "
       "④POST /api/meeting/{id}/attach-share · POST /api/meeting/share-new — 파일을 그 회의 폴더로 옮기고 `_rec_add_pending` 에 넣어 "
       "끊긴 조각과 **순서대로** 변환돼 본문에 이어 붙는다(z1113 기능 그대로 · 정리 로직 변경 없음) "
       "⑤🔴표는 올린 사람 사번을 품는다 — 남의 표로는 자기 회의록에도 못 붙인다(404) · 경로 문자 걸러냄 · 같은 표 두 번 금지 · 로그인 없으면 401 + 「녹음은 휴대폰에 그대로」 안내 · "
       "음성 확장자만(_MEETING_AUDIO_EXT) · 300MB 한도 같음 · 빈/손상 파일 거절. "
       "검증=서버 48(manifest 6 · 받기 6 · 거르기 5 · 붙이고 정리 10 · 새 회의록 5 · 권한·표 11 · 청소 2 · 기존 길 회귀 4) · "
       "화면 16(표시 있으면 바로 · 없으면 고르기 · 새 회의록 · 이어 붙이기 · 음성 아님 · ?auto=1 은 화면이 곧 지움) · "
       "회귀 녹음 서버 55 · 이음 상태 14 · 모아보기 80 · 로그인 20 · 300MB 37 · 착지 27 · 녹음 화면 27 · 휴대폰 녹음기 44 · 뒤로 가기 35 · 표준 검사기(301파일 · 인라인 194). "
       "main.py·share_audio.html]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-20 v5H226z1117[" in chk
assert chk.count(nl + "REM   - 2026-09-20 v5H226z1116[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
