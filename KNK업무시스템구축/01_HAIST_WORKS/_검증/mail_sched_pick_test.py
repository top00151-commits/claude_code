# -*- coding: utf-8 -*-
"""메일 예약 — 웍스 달력 · 확인 뒤 표시 · 보내기로 예약 (대표 2026-11-19). 운영 무접촉 · 임시 DB · 가짜 자료.

대표 말씀: 「달력 시간이 내가 웍스에 정해놓은 달력 기준이 있어 그걸 사용해주고 날짜 시간 선택 후 확인 버튼을 눌러서
예약 날짜 팝업창을 닫게 해주고 … 예약 발송 날짜(요일) 시간을 표시해줘.. 그럼 그걸 최종확인하고 보내기 부르면 예약발송완료하게.」

증명할 것
  ① 날짜 = 웍스 표준 달력(KnkCal — knk_datepicker.html) · 메일 앱 화면(왼쪽 메뉴 없음)에도 들어감 · 브라우저 기본 날짜·시각 칸 없음
  ② 빠른 단추는 「고르기만」(바로 예약 안 함) · 「✓ 확인」 → 창 닫고 도구 줄에 「⏱ 11월 23일(월) 오후 2:30 예약」 · 바꾸기 · ✕ 예약 빼기
  ③ 예약을 골라 두면 「📤 보내기」 → 「⏱ 예약 보내기」 · 누르면 최종 확인 → 서버 예약(지금 바로 보내기 길 아님)
  ④ 시각 = 보는 사람 소속(본사 +9 · 베트남 +7) · 서버도 같은 시각을 받아 예약(직접 고른 'YYYY-MM-DDTHH:MM')
"""
import io
import os
import sys
import tempfile
from datetime import timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_mschp_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
finally:
    sys.stdout = _so
from starlette.testclient import TestClient  # noqa: E402

P = F = 0


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:300])


cp = open(os.path.join(ROOT, "app", "templates", "mail_compose.html"), encoding="utf-8").read()

print("== ① 웍스 달력 ==")
check("쓰기 화면이 웍스 표준 달력(knk_datepicker.html)을 넣음", '{% include "_v5_partials/knk_datepicker.html" %}' in cp)
check("날짜 칸 = knk-cal(웍스 달력) · KnkCal.attach", 'class="knk-cal" id="scDate"' in cp and "KnkCal.attach(f.d)" in cp)
check("브라우저 기본 날짜·시각 칸(datetime-local) 없음", "datetime-local" not in cp)
check("시각 = 오전/오후 시 + 5분 단위", "(h<12?'오전 ':'오후 ')+((h%12)||12)+'시</option>'" in cp and "for(var m=0;m<60;m+=5)" in cp)

print("== ② 고르기 → 확인 → 표시 ==")
check("빠른 단추는 고르기만(cmpSchedQuick · 바로 예약하는 cmpSchedGo 를 부르지 않음)",
      "cmpSchedQuick(\\'tom8\\',this)" in cp and "onclick=\"cmpSchedGo(\\'tom8\\')\"" not in cp)
check("「✓ 확인」 → 창 닫고 표시(scClose · scShow)", 'id="scOk" onclick="cmpSchedOk()"' in cp and "KnkCal.hide(); scClose(); scShow();" in cp)
check("도구 줄 예약 표시 = 날짜(요일) 시각 · 바꾸기 · ✕ 예약 빼기",
      'id="cSchedTag"' in cp and 'id="cSchedTxt"' in cp and 'onclick="cmpSchedule()">바꾸기' in cp and "✕ 예약 빼기" in cp
      and "(+p[1])+'월 '+(+p[2])+'일('+DOW[d.getUTCDay()]+') '" in cp)
check("2분 뒤 ~ 90일 밖이면 확인 잠금 + 까닭", "b.disabled=!ok" in cp and "⚠ 2분 뒤 ~ 90일 안에서 골라 주세요" in cp)

print("== ③ 보내기 = 예약 보내기 ==")
check("예약을 골라 두면 보내기 → 예약 길(cmpSchedSend)", "if(SCHED) return cmpSchedSend();" in cp)
check("단추 글자 「⏱ 예약 보내기」 ↔ 빼면 「📤 보내기」", "b.textContent='⏱ 예약 보내기'" in cp and "b.textContent='📤 보내기'" in cp)
check("최종 확인 창(같은 검사) → 서버 예약(at = YYYY-MM-DDTHH:MM)", "cmpSchedGo(\\''+SCHED.at+'\\')" in cp and "at:f.d.value+'T'+scP2(+f.h.value)+':'+scP2(+f.m.value)" in cp
      and "var r0=checks();" in cp[cp.index("function cmpSchedSend"):cp.index("window.cmpSchedGo")]
      and "cmpPre(r0, function(r){" in cp[cp.index("function cmpSchedSend"):cp.index("window.cmpSchedGo")])   # 11-21 가 묶음: 같은 검사 + 서버 확인
check("보낼 때 시각이 이미 가까워지면 다시 고르라고 알림", "이 너무 가깝거나 지났습니다" in cp)

print("== ④ 시각 = 소속 기준 · 서버 ==")
OWN = 9501
with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9501,'schp','시험직원','member',1,'x')")
m.get_user = lambda req: {"id": OWN, "role": "member", "name": "시험직원", "team_id": None, "team_name": ""}
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
hc = k.get("/mail/compose").text
check("쓰기 화면 열림 · 소속 시각 차이(본사 9) 넣어 줌", "SCHED_OFF=9;" in hc, hc[:200])
check("쓰기 화면에 웍스 달력 스크립트(window.KnkCal)", "window.KnkCal = { attach: attach" in hc)
_real_ent = m._meeting_user_entity
m._meeting_user_entity = lambda c, u: "VN"
check("베트남 직원이면 7", "SCHED_OFF=7;" in k.get("/mail/compose").text)
m._meeting_user_entity = _real_ent
now9 = m._mail_now_local(9)
pick = (now9 + timedelta(days=3)).replace(hour=14, minute=30, second=0, microsecond=0)
srv = m._mail_sched_from(pick.strftime("%Y-%m-%dT%H:%M"), 9)
check("직접 고른 시각(현지 3일 뒤 14:30) → 서버 시각으로 바꿔 예약", bool(srv) and srv.startswith(m._mail_local_to_server(pick, 9)[:16]), srv)
check("1분 뒤는 거절(2분 뒤부터)", m._mail_sched_from((now9 + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M"), 9) == "")
check("91일 뒤는 거절", m._mail_sched_from((now9 + timedelta(days=91)).strftime("%Y-%m-%dT%H:%M"), 9) == "")

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
