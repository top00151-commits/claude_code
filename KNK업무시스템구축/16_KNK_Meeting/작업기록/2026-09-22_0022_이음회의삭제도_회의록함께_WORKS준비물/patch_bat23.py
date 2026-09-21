# -*- coding: utf-8 -*-
"""BAT LAST UPDATE 갱신 — 이음 🗓 회의에서 지워도 WORKS 회의록까지 함께 · 취소 알림 안내 (z1123)
사용: py patch_bat23.py <원본 bat(직전 z1122)> <결과 bat> <회귀 결과>"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
raw = open(SRC, "rb").read()
s = raw.decode("utf-8")
assert "LAST UPDATE: 2026-09-21 v5H226z1122[" in s, "직전 기록(z1122 LAST UPDATE) 판독 실패"
nl = "\r\n" if raw.count(b"\r\n") else "\n"
print("BOM:", s.startswith("﻿"), "| 줄바꿈:", repr(nl))

REG = "__REG__"   # 회귀 결과(배포 직전 채움)
NEW = ("REM   LAST UPDATE: 2026-09-22 v5H226z1123[회의록 — 이음 🗓 회의에서 지워도 WORKS 회의록까지 함께 · 시작 전 회의 취소 알림 안내"
       "(대표 결정 09-22 00시: 시작 전 회의를 지우면 참석자에게 취소 알림 · 이음 🗓 회의 창에서 지울 때도 카드 숨김(회의 알림 방에서 카드 메시지를 지울 때는 아님) · "
       "🗓 에서 지우면 WORKS 회의록(녹음·정리)도 함께(작성자·관리자일 때만) · 🗓 삭제도 두 번 확인 — 이음 쪽은 세션 10). "
       "①새 서버 전용 입구 POST /api/meeting/msg/delete(공유키) — 이음이 자기 회의를 지우기 전에 부름 · 회의록 작성자(▶ 회의 시작을 누른 사람)·관리자(admin/ceo)면 지움(deleted) · "
       "회의록 없음=none · 등록 담당·다른 직원=남김(kept·not_allowed) · 사번 모름=남김(kept·viewer_not_found) · 🔴 여기서 이음을 다시 부르지 않음(서로 부르며 돌지 않게) · "
       "지우면 활동 기록 · 어느 결과든 모아보기 30초 저장본 비움 "
       "②msg/status 에 can_delete(WORKS 🗑 삭제와 같은 판단) — 이음 🗓 「삭제」 첫 확인 창이 「WORKS 회의록도 함께 지워집니다 / 남습니다」를 미리 "
       "③WORKS 🗑 삭제 뒤 이음이 취소 알림을 보냈으면(notified) 「🔔 시작 전 회의라 참석자 N명에게 「회의가 취소되었습니다」 알림이 갔습니다」. "
       "검증=서버 45(공유키·잘못된 요청·none·작성자·대표·관리자·VN 사번·등록 담당·모르는 사번·퇴사·같은 사번 2명·이음 되부름 0·재시도·저장본·can_delete·notified) · "
       "화면 10(취소 알림 안내·알림 없을 때 그대로·거절/입구 없음 알림 그대로 · 고치기 전 파일로는 실패) · 회귀 " + REG + " · 표준 검사기(인라인 194). "
       "main.py·sso_client.py·meeting_form.html]" + nl)

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
assert chk.count("REM   LAST UPDATE:") == 1 and "LAST UPDATE: 2026-09-22 v5H226z1123[" in chk
assert chk.count(nl + "REM   - 2026-09-21 v5H226z1122[") == 1
print("[OK] BAT 갱신", len(raw), "→", len(chk.encode("utf-8")))
