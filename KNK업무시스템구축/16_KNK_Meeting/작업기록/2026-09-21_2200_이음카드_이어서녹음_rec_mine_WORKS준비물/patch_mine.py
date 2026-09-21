# -*- coding: utf-8 -*-
"""z1121 — 이음 회의 카드용 msg/status 에 `rec_mine`(보는 사람이 그 녹음을 시작했나) 한 칸

대표 지시(2026-09-21 22시 「만들어줘」): 창을 ✕ 로 닫아 멈춘 녹음 — 이음 카드 단추를 녹음하던 사람에겐
「🎙 이어서 녹음」으로(세션 10 요청). 이음은 '보는 사람이 녹음하던 사람인가'를 모른다 → WORKS 가 알려 준다.
  · rec_mine = 녹음이 열려 있고(recording) 그 녹음을 시작한 사람(rec_json.by) = 보는 사람(employee_no → WORKS 사용자)
  · 그 밖엔 false · 보는 사람을 못 찾으면 false · 다른 칸·주소는 그대로(추가만 — 옛 이음은 모르는 칸이라 무시)
  · WORKS 회의 화면은 녹음하던 본인이면 맨 위 「🎙 이어서 녹음」을 묻지 않고 한 번에(z1120 REC.mine 과 같은 판단)
사용: py patch_mine.py <원본 main.py(운영 cc246a09)> <결과 main.py>
"""
import hashlib
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
s0 = io.open(SRC, encoding="utf-8", newline="").read()
assert "\r\n" not in s0, "CRLF 원본 — git show 결과(LF)를 쓸 것"
print("원본 sha256:", hashlib.sha256(s0.encode("utf-8")).hexdigest()[:16])

OLD = (
    '            _rv = _rec_view(m)       # z1114: 녹음 중인가 · 서버에 저장된 초(창이 닫혀 끊긴 녹음도)\n'
    '            it = {"stage": _meeting_msg_stage(m), "can_view": can_view,\n'
    '                  "started_by": _msg_owner_disp(c, m.get("owner_id")),\n'
    '                  "started_at": m.get("msg_started_at") or "",\n'
    '                  "recording": _rv["state"] == "recording",\n'
    '                  "rec_secs": _rv["secs"] if _rv["state"] == "recording" else 0}\n'
)
NEW = (
    '            _rv = _rec_view(m, viewer)   # z1114: 녹음 중인가 · 서버에 저장된 초(창이 닫혀 끊긴 녹음도)\n'
    '            it = {"stage": _meeting_msg_stage(m), "can_view": can_view,\n'
    '                  "started_by": _msg_owner_disp(c, m.get("owner_id")),\n'
    '                  "started_at": m.get("msg_started_at") or "",\n'
    '                  "recording": _rv["state"] == "recording",\n'
    '                  "rec_secs": _rv["secs"] if _rv["state"] == "recording" else 0,\n'
    '                  # z1121: 보는 사람이 그 녹음을 시작했나 — 창을 닫아 멈춘 녹음이면 이음 카드 단추를 그 사람에게만\n'
    '                  #   「🎙 이어서 녹음」으로(대표 지시 2026-09-21 · 세션 10). WORKS 회의 화면의 REC.mine(z1120)과 같은 판단.\n'
    '                  "rec_mine": _rv["state"] == "recording" and bool(_rv["mine"])}\n'
)
assert s0.count(OLD) == 1, "앵커 %d개" % s0.count(OLD)
s = s0.replace(OLD, NEW)
with io.open(DST, "w", encoding="utf-8", newline="") as f:
    f.write(s)
print("[OK] main.py %d → %d 글자" % (len(s0), len(s)))
print("결과 sha256:", hashlib.sha256(s.encode("utf-8")).hexdigest()[:16])
assert s.count('"rec_mine": _rv["state"] == "recording" and bool(_rv["mine"])') == 1
assert s.count("_rv = _rec_view(m, viewer)") == 1
