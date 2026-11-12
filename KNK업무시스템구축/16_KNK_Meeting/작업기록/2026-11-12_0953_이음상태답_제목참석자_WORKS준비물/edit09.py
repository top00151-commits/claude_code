# -*- coding: utf-8 -*-
"""z1209 — 이음 회의 상태 답(/api/meeting/msg/status)에 제목·참석자 세 칸(세션 10 요청 · 이음 v935 짝).
사용: py edit09.py <앱 폴더>   · 줄 끝 원본 그대로"""
import io
import os
import sys

p = os.path.join(sys.argv[1], "app", "main.py")
s = io.open(p, "r", encoding="utf-8", newline="").read()
_L = '                  "can_delete": bool(viewer) and _can_delete_meeting(viewer, m)}'
NL = "\r\n" if (_L + "\r\n") in s else "\n"   # 섞인 줄 끝 파일(일부 줄만 CRLF) — 넣는 자리의 줄 끝을 따른다
if "z1209" in s:
    print("STOP: 이미 들어가 있음"); sys.exit(2)
A = '                  "can_delete": bool(viewer) and _can_delete_meeting(viewer, m)}' + NL
assert s.count(A) == 1, "자리"
ADD = '''            # 🔁 z1209 (대표 지시 2026-11-11 · 세션 10 요청 · 이음 v935 짝): 이음웍스 회의록에서 고친 제목·참석자를
            #   이음 회의·카드가 따라가게 — 이음이 1분마다 묻는 이 답에 싣는다(이음웍스는 이음을 되부르지 않는다 · z1123).
            #   서버끼리만 받는 답(공유키)이라 볼 수 있는지(can_view)와 무관하게 싣는다 — 이음은 화면에 그대로 주지 않는다.
            #   att_emps = 계정이 연결된 참석자의 사번 · att_ext = 계정 없는 참석자 이름(고객사 분 등) ·
            #   계정은 연결됐는데 사번이 빈 사람은 어느 쪽에도 넣지 않는다(이음이 사번으로만 사람을 찾는다).
            _ar = [dict(r) for r in c.execute(
                "SELECT a.user_id, a.name, u.employee_no FROM meeting_attendees a "
                "LEFT JOIN users u ON u.id=a.user_id WHERE a.meeting_id=? ORDER BY a.id", (m["id"],))]
            it["title"] = str(m.get("title") or "")
            it["att_emps"] = [str(r["employee_no"]).strip() for r in _ar
                              if r.get("user_id") and str(r.get("employee_no") or "").strip()]
            it["att_ext"] = [str(r.get("name") or "").strip() for r in _ar
                             if not r.get("user_id") and str(r.get("name") or "").strip()]
'''
s = s.replace(A, A + ADD.replace("\n", NL), 1)
tmp = p + ".tmp09"
io.open(tmp, "w", encoding="utf-8", newline="").write(s)
os.replace(tmp, p)
print("OK z1209 →", p)
