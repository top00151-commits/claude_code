# -*- coding: utf-8 -*-
"""z1149·z1150 시험
사용: py -3.12 ui_end_z1150.py [포트=8948]

z1149 ① 이음 「▶ 회의 시작」(?autorec=1) 으로 열어도 **녹음이 안 켜진다**
      ② 서버가 주소에 ?autorec=1 을 **아예 안 보낸다**
      ③ 🔵 「🎤 이어서 녹음」은 그대로 산다(이미 돌던 녹음을 이어가는 길)
z1150 ④ 이음이 부르는 「⏹ 회의 종료」 창구 — 공유키·권한·되돌리기·녹음 중
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8948
BASE = "http://127.0.0.1:%d" % PORT
S = json.load(io.open(os.path.join(HERE, "seed_end.json"), encoding="utf-8"))
HDR = {"X-SSO-Service-Key": S["key"], "Content-Type": "application/json"}

OK = FAIL = 0
FAILS = []


def chk(cond, name, extra=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [PASS] " + name + (" · " + str(extra)[:150] if extra != "" else ""))
    else:
        FAIL += 1
        FAILS.append(name)
        print("  [FAIL] " + name + " " + str(extra)[:200])


def state(pg):
    return pg.evaluate("""() => {
      const b = document.getElementById('recBtn');
      const n = document.getElementById('recBlockNote');
      return { autorec: b ? !!b.dataset.autorec : null,
               on: b ? !!b.dataset.on : null,
               label: b ? (b.textContent||'').trim().slice(0,30) : '',
               note: n && !n.hidden ? (n.textContent||'').trim() : '',
               banner: !!document.getElementById('mtgRecBar') };
    }""")


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        c = b.new_context(viewport={"width": 420, "height": 900},
                          permissions=[])   # 마이크 허락 안 줌 — 부르면 티가 난다
        c.add_cookies([{"name": "tuser", "value": str(S["owner"]), "url": BASE}])
        rq = c.request

        # ══ ① ?autorec=1 로 열어도 녹음이 안 켜진다 ══
        print("\n[①] z1149 — 이음 「▶ 회의 시작」으로 열어도 녹음이 안 켜진다")
        pg = c.new_page()
        mic = []
        pg.on("console", lambda m: mic.append(m.text) if "getUserMedia" in (m.text or "") else None)
        pg.goto("%s/meetings/%d?autorec=1" % (BASE, S["mid_ok"]), wait_until="domcontentloaded")
        pg.wait_for_selector("#recBtn", state="attached", timeout=15000)
        pg.wait_for_timeout(2600)   # 자동 시작이 있었다면 이 사이에 돈다
        a = state(pg)
        chk(not a["autorec"], "단추에 자동녹음 표시가 **안 남는다**(예외가 닫혔다)", a)
        chk(not a["on"], "녹음이 안 켜졌다")
        chk(not a["banner"], "「🔴 녹음 중」 띠가 없다")

        # 🔵 이음에서 들어온 사람이 길을 잃지 않는지 — 「📁 녹음 파일 올리기」가 **접지 않아도** 보인다
        upv = pg.evaluate("() => { const e=document.getElementById('recUpBtn');"
                          " return !!e && !!(e.offsetWidth||e.offsetHeight||e.getClientRects().length); }")
        chk(upv, "🔵 이음에서 와도 「📁 녹음 파일 올리기」가 바로 보인다(갈 길이 있다)")

        # 눌러도 막히고 안내가 뜬다 — 단추는 「🔧 다시 하기」 안에 접혀 있다(원래 그렇다)
        # 🔴 z1153 (대표 지시 2026-10-08): 단추가 **잠겨** 있다 → 누를 수 없다
        pg.evaluate("() => { const d=document.getElementById('redoTools'); if(d) d.open=true; }")
        pg.wait_for_timeout(200)
        chk(pg.locator("#recBtn").is_disabled(), "z1153 — 단추가 회색으로 잠겨 있다")
        _a = pg.evaluate("() => { const a=document.getElementById('recAddNote');"
                         " return a && !a.hidden ? (a.textContent||'') : ''; }")
        chk("휴대폰" in _a and "녹음 파일 올리기" in _a, "까닭과 갈 길이 늘 보인다", _a[:60])

        # ══ ② 서버가 autorec 을 안 보낸다 ══
        print("\n[②] z1149 — 서버가 주소에 ?autorec=1 을 안 붙인다")
        r = rq.post("%s/api/meeting/msg/start" % BASE, headers=HDR, data=json.dumps({
            "msg_meeting_id": S["msg_ok"], "title": "드림텍VINA MES 관련",
            "start_at": "2026-10-08T10:00", "visibility": "all",
            "starter_employee_no": "E901"}))
        j = r.json()
        chk(r.status == 200 and j.get("ok"), "이음 「▶ 회의 시작」 창구는 그대로 돈다", r.status)
        chk("autorec" not in (j.get("url") or ""), "🔴 돌려주는 주소에 autorec 이 없다", j.get("url"))

        # ══ ③ 「이어서 녹음」은 그대로 ══
        print("\n[③] 🔵 「🎤 이어서 녹음」은 막지 않는다(이미 돌던 녹음을 이어간다)")
        pg2 = c.new_page()
        pg2.goto("%s/meetings/%d" % (BASE, S["mid_rec"]), wait_until="domcontentloaded")
        pg2.wait_for_timeout(900)
        chk(pg2.locator("#recResumeBtn").count() == 1, "녹음 중이던 회의엔 「이어서 녹음」 단추가 있다")
        chk(pg2.evaluate("() => { const b=document.getElementById('recResumeBtn');"
                         " return !!b && !b.disabled; }"), "그 단추는 잠겨 있지 않다")

        # ══ ④ 종료 창구 ══
        print("\n[④] z1150 — 이음이 부르는 「⏹ 회의 종료」 창구")

        def call(body, key=True):
            h = dict(HDR) if key else {"Content-Type": "application/json"}
            rr = rq.post("%s/api/meeting/msg/end" % BASE, headers=h, data=json.dumps(body))
            try:
                return rr.status, rr.json()
            except Exception:
                return rr.status, {}

        st, j = call({"msg_meeting_id": S["msg_ok"], "employee_no": "E901"}, key=False)
        chk(st == 403 and j.get("error") == "forbidden", "🔴 공유키 없으면 막는다", "%s %s" % (st, j))

        st, j = call({"msg_meeting_id": 99999, "employee_no": "E901"})
        chk(j.get("error") == "not_found", "없는 회의 → not_found", j)

        st, j = call({"msg_meeting_id": S["msg_ok"], "employee_no": "E999"})
        chk(j.get("error") == "no_user", "모르는 사번 → no_user", j)

        st, j = call({"msg_meeting_id": S["msg_ok"], "employee_no": "E904"})
        chk(j.get("error") == "not_allowed", "🔴 권한 없는 사람(남) → not_allowed", j)

        st, j = call({"msg_meeting_id": S["msg_rec"], "employee_no": "E901"})
        chk(j.get("error") == "recording", "🔴 녹음 중이면 끝내지 않는다 → recording", j)

        st, j = call({"msg_meeting_id": S["msg_ok"], "employee_no": "E902"})
        chk(j.get("ok") and j.get("ended") and j.get("ended_at"),
            "🔵 참석자가 끝낼 수 있다(사람이 누르는 길과 같은 기준)", j)
        ended_at = j.get("ended_at")

        st, j = call({"msg_meeting_id": S["msg_ok"], "employee_no": "E903"})
        chk(j.get("ok") and j.get("already"), "이미 끝난 회의를 또 부르면 already", j)

        # 🔴 z1152 (대표 지시 2026-10-08 「되돌리기 만들지마」): 창구에서 그 갈래를 지웠다.
        #   보내도 되돌아가지 않아야 한다 — 끝난 상태 그대로.
        st, j = call({"msg_meeting_id": S["msg_ok"], "employee_no": "E901", "undo": True})
        chk(j.get("ok") and j.get("ended") is True,
            "z1152 — undo 를 보내도 되돌아가지 않는다(갈래가 없다)", j)

        st, j = call({"msg_meeting_id": S["msg_ok"], "employee_no": "E903"})
        chk(j.get("ok") and j.get("ended"), "이음 등록 담당도 끝낼 수 있다", j)

        # 끝낸 것이 WORKS 화면에도 보이나
        #   🔵 「🗓 회의 카드 모아보기」 탭은 이음에서 카드를 받아 오는데 시험 서버엔 이음이 없다 →
        #      여기서는 **회의록 상세**로 본다(같은 ended_at 을 본다).
        pg3 = c.new_page()
        pg3.goto("%s/meetings/%d" % (BASE, S["mid_ok"]), wait_until="domcontentloaded")
        pg3.wait_for_selector("#mtgEndedTag", state="attached", timeout=15000)
        tag = pg3.evaluate("() => { const e=document.getElementById('mtgEndedTag');"
                           " return e && !e.hidden ? e.textContent.trim() : ''; }")
        chk("종료됨" in tag, "회의록 상세가 「✅ 종료됨」으로 바뀐다(이음 카드도 같은 값을 본다)", tag)
        hid = pg3.evaluate("() => { const e=document.getElementById('btnEndMeeting');"
                           " return e ? !!e.hidden : null; }")
        chk(hid is True, "끝난 회의엔 「⏹ 회의 종료」 단추가 안 보인다", hid)
        chk(ended_at and len(ended_at) >= 16, "끝낸 시각이 돌아온다", ended_at)

        b.close()

    print("\n" + "=" * 56)
    print("  통과 %d · 실패 %d" % (OK, FAIL))
    for f in FAILS:
        print("   ✗ " + f)
    print("=" * 56)
    return 1 if FAIL else 0


sys.exit(main())
