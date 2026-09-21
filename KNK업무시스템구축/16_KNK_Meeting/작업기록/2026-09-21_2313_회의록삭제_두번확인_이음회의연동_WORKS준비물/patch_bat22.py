# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 회의록 삭제 두 번 확인·이음 회의 함께 지우기 준비 + 이음 v817 맞춤 (z1122)
사용: py patch_bat22.py <원본 bat(직전 z1121)> <결과 bat>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-21 v5H226z1121[" in s, "직전 기록(z1121 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

REG = "__REG__"   # 회귀 결과(배포 직전 채움)
NEW = ("REM   LAST UPDATE: 2026-09-21 v5H226z1122[회의록 — 🗑 삭제 두 번 확인 · 작성자·관리자만 · 이음 회의도 함께 지우기(이음 등록자·관리자일 때) + 이음 v817 맞춤"
       "(대표 지시 09-21 23시 사진 3장: 상세에서 삭제할 때 꼭 확인 한 번 더 · 삭제는 작성자 또는 관리자만 · 삭제된 회의는 모아보기·이음 회의 알림에서도 사라지게 · "
       "대표 결정: 이음 회의까지 함께 · 이음 알림 카드는 방에서 숨김 · 이음 회의까지는 이음 등록자·관리자만 · 이음 쪽은 세션 10). "
       "①확인 두 번(첫 창 = 제목·날짜·지워지는 것·이음 회의가 함께 지워지는지 · 둘째 창 = 「⚠ 정말 삭제할까요? 되돌릴 수 없습니다」) · 실패는 화면 가운데 알림(전엔 아래 저장 줄) "
       "②권한 = 원래대로 작성자·관리자(admin/ceo)만 · 등록 담당은 고치기만(서버 403 · 단추 없음 · 시험으로 재확인) "
       "③이음에서 온 회의면 이음에 POST /api/works/meetings/delete(사번) → 지움/이미 없음=둘 다 · 거절(not_allowed)·사번 모름·입구 없음(글자 404 = 세션 10 배포 전)=회의록만+까닭 알림 · "
       "🔴 연결 실패·키 거부·오류=아무것도 안 지움(503 · 한쪽만 지워지지 않게) · 지운 뒤 모아보기 30초 저장본 비움 · 상세에 msg_del(none·yes·no)로 확인 글 미리 알림 "
       "④이음 v817(23:12) 맞춤 — 아이폰 안내 「이음 회의 카드의 「🎙 이어서 녹음」(또는 카드 빈 곳)」 · 모아보기: 녹음하던 본인 「🎙 이어서 녹음」(빨강) · 카드 빈 곳 = 그 카드 단추 · "
       "msg-cards 에 rec_mine · 주소를 msg/status 와 같게(정리 끝이어도 녹음 중이면 녹음 화면). "
       "검증=서버 33 · 화면 46(두 번 확인·대표 이음까지·거절·입구 없음·못 닿음·권한·모아보기 단추·카드 누르기·지운 회의 바로 빠짐·아이폰 안내 · 고치기 전 파일로는 실패) · "
       "회귀 " + REG + " · 표준 검사기(인라인 194). 🔴시험 도구 결함 발견·수리: netstat 줄 순서 탓에 옛 시험 서버를 못 멈춰 옛 코드를 시험하던 것 → Get-NetTCPConnection 으로 멈추고 비었는지 확인 뒤 다시 전부. "
       "main.py·sso_client.py·meeting_form.html·meetings.html]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-21 v5H226z1122[" in chk
assert chk.count(nl + "REM   - 2026-09-21 v5H226z1121[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
