# -*- coding: utf-8 -*-
"""z1149 — 이 화면 녹음은 **새로 시작할 수 없다** (대표 지시 2026-10-08)
사용: py -3.12 ui_norec_z1149.py [포트=8936]

왜 이 묶음이 생겼나
  대표 지시 「회의 시작을 눌렀을때 녹음되는걸 막아」로 녹음을 켜는 길이 모두 닫혔다.
    ①녹음 단추(z1143) ②이음 자동 녹음(z1149) ③「이어서 녹음」은 이미 열린 녹음 자리가 있어야 보인다
  → 새 녹음 자리를 열 길이 없다. 그래서 **녹음을 켠 뒤**를 보던 옛 묶음
    (ui_rec_z1130 · ui_back_z1130)은 확인할 길이 사라졌다(대표 결정 「이제 안 된다로 바꾸기」).
  이 묶음이 그 자리를 대신해 **새 사실**을 지킨다. 옛 파일은 기록으로 그대로 둔다.

  🔴 「먹통 금지」는 그대로다 — 눌렀을 때 아무 일도 안 일어나면 안 되고,
     반드시 **까닭과 갈 길**(휴대폰 녹음기 · 📁 녹음 파일 올리기)을 보여 줘야 한다.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8936
BASE = "http://127.0.0.1:%d" % PORT
# 🔵 씨앗은 **서버를 띄운 폴더**에 생긴다 — 묶음에선 reg/, 혼자 돌릴 땐 이 파일 옆.
#    둘 다 찾아보고 없으면 어디를 봤는지 알려 준다(조용히 죽지 않게).
_CAND = [os.path.join(HERE, "seed_phrec.json"),
         os.path.join(HERE, "reg", "seed_phrec.json"),
         os.path.join(os.getcwd(), "seed_phrec.json")]
if len(sys.argv) > 2:
    _CAND.insert(0, os.path.join(sys.argv[2], "seed_phrec.json"))
_SP = next((x for x in _CAND if os.path.exists(x)), None)
if not _SP:
    print("씨앗(seed_phrec.json)을 못 찾았습니다. 찾아본 곳:")
    for x in _CAND:
        print("   " + x)
    sys.exit(2)
SEED = json.load(io.open(_SP, encoding="utf-8"))
MIDS = SEED["mids"]
UA_AND = ("Mozilla/5.0 (Linux; Android 14; SM-S918N) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/127.0.0.0 Mobile Safari/537.36")
UA_IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
          "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")

OK, NG = [], []


def ok(name, cond, extra=""):
    (OK if cond else NG).append(name)
    print(("PASS " if cond else "FAIL ") + name + (" · " + str(extra)[:140] if extra != "" else ""),
          flush=True)


def note_of(p):
    return p.evaluate("() => { const n=document.getElementById('recBlockNote');"
                      " return n && !n.hidden ? (n.textContent||'') : ''; }")


def rec_on(p):
    return p.evaluate("() => { const b=document.getElementById('recBanner'); return !!b && !b.hidden; }")


def unfold(p):
    # 🔵 휴대폰에서는 이 화면 녹음 단추가 「다른 방법」(recOther) 안에 **한 겹 더** 접혀 있다(z1130)
    p.evaluate("() => { const d=document.getElementById('redoTools'); if(d) d.open=true; }")
    p.wait_for_timeout(200)
    p.evaluate("() => { const d=document.getElementById('recOther'); if(d) d.open=true; }")
    p.wait_for_timeout(250)


def always_note(p):
    return p.evaluate("() => { const a=document.getElementById('recAddNote');"
                      " return a && !a.hidden ? (a.textContent||'') : ''; }")


def main():
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True,
                                args=["--use-fake-device-for-media-stream"])

        # ══ ① 새 회의록 — 눌러도 녹음도 회의록도 안 생긴다 ══
        print("\n■ ① 새 회의록에서 눌렀을 때", flush=True)
        reqs = []
        # 🔵 안드로이드 새 회의록에서는 이 단추가 **원래 숨어 있다**(z1130 휴대폰은 녹음기 한 길)
        #    → 눌러 보는 시험은 단추가 보이는 PC 로 한다.
        c = br.new_context(viewport={"width": 1280, "height": 860},
                           permissions=["microphone"], service_workers="block")
        p = c.new_page()
        p.on("request", lambda r: reqs.append((r.method, r.url.replace(BASE, "")))
             if "/api/meeting" in r.url else None)
        p.goto(BASE + "/meetings/new", wait_until="domcontentloaded")
        p.wait_for_selector("#recBtn", state="attached", timeout=15000)
        p.wait_for_timeout(400)
        unfold(p)
        # 🔴 z1153 (대표 지시 2026-10-08 「이 부분도 비활성화로」): 단추가 잠겨 있다
        ok("z1153 — 「녹음하며 회의」가 잠겨 있다", p.locator("#recBtn").is_disabled())
        ok("녹음이 안 켜진다", not rec_on(p))
        ok("서버에 녹음을 열지 않는다(rec-start 없음)",
           not any("rec-start" in u for _m, u in reqs), [u for _m, u in reqs][:4])
        # 🔴 예전엔 녹음을 켜면 회의록이 **먼저 만들어졌다**(z1113) — 이제 그 길도 없다
        ok("🔴 빈 회의록이 만들어지지 않는다(목록이 더러워지지 않는다)",
           not any(m == "POST" and u == "/api/meeting" for m, u in reqs), reqs[:4])
        _sub = p.evaluate("() => { const e=document.querySelector('#recBtn .start-sub');"
                          " return e ? (e.textContent||'') : ''; }")
        ok("🔴 먹통이 아니다 — 단추 밑에 「휴대폰 녹음기로」라고 적혀 있다", "휴대폰 녹음기" in _sub, _sub[:60])
        c.close()

        # ══ ② 회의록 상세 — 같다 ══
        print("\n■ ② 회의록 상세에서 눌렀을 때", flush=True)
        c = br.new_context(viewport={"width": 390, "height": 840}, user_agent=UA_AND,
                           permissions=["microphone"], service_workers="block")
        p = c.new_page()
        p.goto("%s/meetings/%d" % (BASE, MIDS[0]), wait_until="domcontentloaded")
        p.wait_for_selector("#recBtn", state="attached", timeout=15000)
        unfold(p)
        ok("z1153 — 상세 「녹음 추가」도 잠겨 있다", p.locator("#recBtn").is_disabled())
        ok("상세에서도 녹음이 안 켜진다", not rec_on(p))
        _a = always_note(p)
        ok("z1153 — 까닭과 갈 길이 늘 보인다", ("휴대폰" in _a) and ("녹음 파일 올리기" in _a), _a[:70])
        c.close()

        # ══ ③ 이음 착지 — 녹음은 안 켜지되 **안내는 보여야 한다** ══
        #   🔴 처음 만들 때 이 안내까지 같이 꺼 버린 적이 있다(회귀가 잡음) → 여기서 못박는다.
        print("\n■ ③ 이음 「▶ 회의 시작」 착지 — 녹음 없음 + 안내 있음", flush=True)
        for qs, nm in (("?fromeum=1", "새 표시(fromeum)"), ("?autorec=1", "옛 주소(autorec)")):
            c = br.new_context(viewport={"width": 390, "height": 840}, user_agent=UA_AND,
                               permissions=["microphone"], service_workers="block")
            p = c.new_page()
            p.goto("%s/meetings/%d%s" % (BASE, MIDS[1], qs), wait_until="domcontentloaded")
            p.wait_for_timeout(3000)
            ok("%s: 자동 녹음이 안 켜진다" % nm, not rec_on(p))
            ok("%s: 🔴 「다시 하기」가 펴져 안내가 보인다" % nm,
               p.evaluate("() => { const d=document.getElementById('redoTools'); return !!d && d.open; }"))
            ok("%s: 🔴 「📁 녹음 파일 올리기」가 바로 보인다(갈 길)" % nm,
               p.evaluate("() => { const e=document.getElementById('recUpBtn');"
                          " return !!e && !!(e.offsetWidth||e.offsetHeight||e.getClientRects().length); }"))
            c.close()

        # ══ ④ 아이폰·PC 도 같다 ══
        print("\n■ ④ 아이폰·PC 착지", flush=True)
        for ua, nm, w in ((UA_IOS, "아이폰", 390), (None, "PC", 1280)):
            kw = {"viewport": {"width": w, "height": 860}, "permissions": ["microphone"],
                  "service_workers": "block"}
            if ua:
                kw["user_agent"] = ua
            c = br.new_context(**kw)
            p = c.new_page()
            p.goto("%s/meetings/%d?fromeum=1" % (BASE, MIDS[2]), wait_until="domcontentloaded")
            p.wait_for_timeout(3000)
            ok("%s: 자동 녹음이 안 켜진다" % nm, not rec_on(p))
            st = (p.locator("#recStatus").inner_text() or "")
            ok("%s: 상태줄이 휴대폰 녹음기를 알려 준다" % nm,
               ("휴대폰" in st) or ("녹음 파일 올리기" in st), st[:80])
            # 🔴 자바스크립트에는 대문자 U 이스케이프가 없다 —
            #   파이썬 버릇으로 그렇게 쓰면 화면에 'U0001F3A4' 가 글자로 나온다(실제로 겪음).
            _bad = "U0001F"
            ok("%s: 🔴 이모지가 깨져 글자로 보이지 않는다" % nm,
               (_bad not in st) and (_bad not in p.inner_text("body")), st[:60])
            c.close()

        # ══ ⑤ 🔵 「이어서 녹음」 단추는 녹음 자리가 있을 때만 — 지금은 안 뜬다 ══
        print("\n■ ⑤ 🔵 「🎤 이어서 녹음」은 열린 녹음 자리가 있어야 뜬다", flush=True)
        c = br.new_context(viewport={"width": 1280, "height": 860}, service_workers="block")
        p = c.new_page()
        p.goto("%s/meetings/%d" % (BASE, MIDS[3]), wait_until="domcontentloaded")
        p.wait_for_timeout(700)
        ok("녹음 자리가 없으면 「이어서 녹음」이 없다", p.locator("#recResumeBtn").count() == 0,
           p.locator("#recResumeBtn").count())
        made = p.evaluate("""async (id) => {
            const r = await fetch('/api/meeting/'+id+'/rec-start', {method:'POST',
                headers:{'Content-Type':'application/json'}, body: JSON.stringify({ext:'.webm'})});
            return (await r.json()).ok === true; }""", MIDS[3])
        ok("시험용으로 녹음 자리를 연다(서버 창구는 살아 있다)", made)
        p.reload(wait_until="domcontentloaded")
        p.wait_for_timeout(900)
        ok("🔵 자리가 있으면 「이어서 녹음」이 뜬다(끝내러 들어갈 길은 남아 있다)",
           p.locator("#recResumeBtn").count() == 1)
        c.close()
        br.close()

    print("\n" + "=" * 60)
    print("합계: 통과 %d · 실패 %d" % (len(OK), len(NG)))
    for n in NG:
        print("  ❌ " + n)
    sys.exit(1 if NG else 0)


main()
