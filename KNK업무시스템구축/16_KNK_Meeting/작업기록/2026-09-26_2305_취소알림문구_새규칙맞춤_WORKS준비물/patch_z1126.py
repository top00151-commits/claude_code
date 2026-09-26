# -*- coding: utf-8 -*-
"""z1126 — 취소 알림 새 규칙에 맞춘 글 두 줄 (대표 결정 2026-09-26 「다른 참석자 있으면 알림」)
  새 규칙(이음 쪽 세션 10): **나 말고 참석자가 있으면** 언제나 「🗑 회의가 취소되었습니다」(시작 전·후 구분 없음) · 혼자 만든 회의는 조용히
  ① 삭제 뒤 알림에서 「시작 전 회의라」를 뺀다(그 조건이 없어짐)
  ② 첫 확인 창(이음 회의도 함께 지울 때)에 「나 말고 참석자가 있으면 취소 알림이 갑니다」 한 줄
사용: py patch_z1126.py <앱 사본 폴더>
기준: 운영 z1125(meeting_form 69062939)"""
import hashlib
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = sys.argv[1]
REL = "app/templates/meeting_form.html"
p = os.path.join(ROOT, REL)
raw = open(p, "rb").read()
h = hashlib.sha256(raw).hexdigest()[:8]
assert h == "69062939", f"{REL} 기준이 다름: {h}"
s = raw.decode("utf-8")
assert "\r\n" not in s


def rep(s, old, new, name):
    n = s.count(old)
    assert n == 1, f"{name}: 기준 글 {n}곳(기대 1)"
    return s.replace(old, new)


# ① 삭제 뒤 알림 — 「시작 전 회의라」 뺌 (옛 규칙을 말하던 주석도 함께)
s = rep(s,
        "      else if (mg.notified>0){   // z1123 (대표 결정 2026-09-22): 시작 전 회의 — 이음이 참석자에게 취소 알림을 보냈다\n"
        "        alert('회의록과 이음 회의를 지웠습니다.\\n\\n🔔 시작 전 회의라 참석자 '+mg.notified+'명에게 「회의가 취소되었습니다」 알림이 갔습니다.');\n",
        "      else if (mg.notified>0){   // z1126 (대표 결정 2026-09-26): 나 말고 참석자가 있는 회의 — 이음이 취소 알림을 보냈다(시작 전·후 구분 없음)\n"
        "        alert('회의록과 이음 회의를 지웠습니다.\\n\\n🔔 참석자 '+mg.notified+'명에게 「회의가 취소되었습니다」 알림이 갔습니다.');\n",
        "삭제 뒤 알림")

# ② 첫 확인 창 — 취소 알림 미리 알림(대표 결정 2026-09-26)
s = rep(s,
        "    if(md==='yes') q1+='\\n\\n🗓 이음 회의도 함께 지워집니다 — 참석자 달력·회의 알림 카드·회의 카드 모아보기에서 사라집니다.';\n",
        "    if(md==='yes') q1+='\\n\\n🗓 이음 회의도 함께 지워집니다 — 참석자 달력·회의 알림 카드·회의 카드 모아보기에서 사라집니다.'\n"
        "      +'\\n(나 말고 참석자가 있으면 「회의가 취소되었습니다」 알림이 갑니다)';   // z1126 대표 결정 2026-09-26\n",
        "첫 확인 창 취소 알림 줄")

assert "시작 전 회의라" not in s
tmp = p + ".tmp_z1126"
with io.open(tmp, "w", encoding="utf-8", newline="") as f:
    f.write(s)
os.replace(tmp, p)
print("  [OK]", REL, "→", hashlib.sha256(s.encode("utf-8")).hexdigest()[:8])
