# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 「📱 휴대폰 녹음기로 녹음」 · 기기별 안내 (z1115)
사용: py patch_bat15.py <원본 bat(직전 z1114)> <결과 bat>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-18 v5H226z1114[" in s, "직전 기록(z1114 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

NEW = ("REM   LAST UPDATE: 2026-09-20 v5H226z1115[회의 녹음 — 「📱 휴대폰 녹음기로 녹음」(안드로이드) · 기기별 안내(대표 지시 2026-09-20: "
       "「휴대폰 기본 녹음기로 녹음하게 연결할 수 없나」 · 「어떤 사항에서도 녹음이 중지되면 안 된다」 · 「iOS 는 기존대로 녹음하되 웹 창을 바꾸면 녹음이 안 된다고 안내」). "
       "실측(운영 회의 37 「테스트2」 4분 57초 · 1초 단위 소리 크기): 00:05~01:26 말소리(-19dB) → 01:57~03:31 **95초 완전 무음(-101dB)** → 03:46~04:55 말소리(-25dB) "
       "= 대표가 말한 주제 3개 중 화면을 떠나 있던 가운데 하나만 통째로 빠짐(회의 36 도 227초 중 144초 무음). "
       "원인=안드로이드 11+ 가 화면에 안 보이는 앱의 마이크를 막음(예외=마이크용 상주 서비스를 가진 진짜 앱) → 브라우저 안의 웹 화면으로는 못 품. "
       "①새 회의·상세에 큰 단추 「📱 휴대폰 녹음기로 녹음」 — input[capture] 로 폰 기본 녹음기를 바로 열고, 끝나면 그 파일이 평소 올리기와 같은 길(300MB·긴 녹음 나눠 변환)로 들어간다 "
       "②누르는 즉시 회의를 먼저 만든다(녹음기가 떠 있는 동안 크롬이 화면을 버려도 올릴 자리가 남게 · await 하면 '누름'이 풀려 녹음기가 안 열리므로 저장은 뒤에서) "
       "③회의록 목록 맨 위 「📱 휴대폰 녹음기로 녹음하던 회의」 표시줄(localStorage 12시간 · 파일이 올라가면 스스로 사라짐) "
       "④기기별 안내 상자 — 안드로이드=녹음기 권유+화면 녹음은 켜 둘 때만 · 아이폰·아이패드=이 화면에서 녹음하되 다른 앱·다른 웹 화면으로 넘어가면 그동안 녹음 안 됨+음성 메모 대안(대표 지시) · PC 는 안 보임 "
       "⑤안드로이드에서 「🎙 녹음하며 회의」는 두 번째 선택으로 색만 바꿈(글자는 그대로 — 이음 안내 4개 언어가 이 이름을 씀). "
       "🔴 .start-big/.btn 의 display 가 hidden 속성을 덮어 아이폰·PC 에도 단추가 보였다 → .rec-phone[hidden]{display:none!important} (시험이 잡음). "
       "검증=화면 44(안드로이드 단추·순서·capture·안내 · 아이폰 단추 없음·안내 · PC 그대로 · 상세 · 목록 표시줄 12시간) · "
       "회귀 뒤로 가기 35 · 녹음 화면 27 · 녹음 서버 55 · 이음 상태 14 · 300MB 37 · 마이크 안내 16 · 휴대폰 폭 31 · 모아보기 80 · 로그인 20 · 표준 검사기(인라인 193). "
       "meeting_form.html·meetings.html]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-20 v5H226z1115[" in chk
assert chk.count(nl + "REM   - 2026-09-18 v5H226z1114[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
