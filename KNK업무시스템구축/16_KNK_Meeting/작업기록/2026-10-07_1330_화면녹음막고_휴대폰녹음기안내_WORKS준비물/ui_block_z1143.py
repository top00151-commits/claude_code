# -*- coding: utf-8 -*-
"""z1143 화면 시험 — 이 화면 녹음을 막고 「휴대폰 녹음기를 쓰세요」로 안내하는가
사용: py -3.12 ui_block_z1143.py [포트=8936]
  ① 새 회의록 「🎙 녹음하며 회의」 — 눌러도 녹음 안 됨 · 안내가 뜸 · **마이크를 아예 안 부름**
  ② 회의록 상세 「🎙 녹음 추가」 — 같음
  ③ 🔴 이음 「▶ 회의 시작」(?autorec=1) 로 열린 창은 **막지 않는다**
  ④ 녹음 중일 때 「⏹ 종료」는 그대로 (막는 안내가 뜨면 안 된다)
  ⑤ 「📁 녹음 파일 올리기」는 그대로 보인다(이제 이 길이 본길)
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8936
REG = sys.argv[2] if len(sys.argv) > 2 else HERE
BASE = f"http://127.0.0.1:{PORT}"
SEED = json.load(io.open(os.path.join(REG, "seed_phrec.json"), encoding="utf-8"))
MID = SEED["mids"][0]

OK = FAIL = 0
FAILS = []


def chk(cond, name, extra=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  [PASS] {name}" + (f" · {extra}" if extra else ""))
    else:
        FAIL += 1
        FAILS.append(name)
        print(f"  [FAIL] {name} {extra}")


# 마이크를 불렀는지 감시 — 클릭 전에 심는다
SPY = """window.__micAsked = 0;
try{
  var _g = navigator.mediaDevices && navigator.mediaDevices.getUserMedia;
  if(_g){ navigator.mediaDevices.getUserMedia = function(){ window.__micAsked++; return _g.apply(this, arguments); }; }
}catch(e){}"""


def state(pg):
    return pg.evaluate("""() => {
      var b = document.getElementById('recBtn');
      var n = document.getElementById('recBlockNote');
      var ban = document.getElementById('recBanner');
      return {
        btn: b ? (b.textContent||'').trim() : null,
        on: b ? !!b.dataset.on : null,
        autorec: b ? !!b.dataset.autorec : null,
        note: (n && !n.hidden) ? (n.innerText||'') : '',
        banner: ban ? !ban.hidden : null,
        mic: window.__micAsked || 0
      };
    }""")


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])
        c = b.new_context(viewport={"width": 390, "height": 844})
        c.grant_permissions(["microphone"], origin=BASE)   # 허용해 둬도 녹음이 안 돼야 한다
        c.add_cookies([{"name": "tuser", "value": str(SEED["ceo"]), "url": BASE}])
        c.add_init_script(SPY)
        pg = c.new_page()

        # ── ① 새 회의록 ────────────────────────────────────
        print("\n[①] 새 회의록 「🎙 녹음하며 회의」")
        pg.goto(f"{BASE}/meetings/new", wait_until="domcontentloaded")
        pg.wait_for_selector("#recBtn", timeout=15000)
        s0 = state(pg)
        chk(s0["btn"] is not None, "단추가 있다", s0["btn"])
        chk("휴대폰 녹음기로 녹음해 주세요" in pg.inner_text("#recBtn"),
            "보조글이 「휴대폰 녹음기로 녹음해 주세요」로 바뀌었다")
        chk(s0["note"] == "", "처음엔 안내 상자가 없다")
        pg.click("#recBtn")
        pg.wait_for_timeout(1200)
        s1 = state(pg)
        chk(s1["mic"] == 0, "🔴 마이크를 아예 안 불렀다", f"호출 {s1['mic']}회")
        chk(not s1["on"], "녹음이 시작되지 않았다(단추가 종료로 안 바뀜)", s1["btn"])
        chk(not s1["banner"], "「🔴 본 회의 녹음 중」 띠가 안 뜬다")
        chk(s1["note"] != "", "안내 상자가 뜬다")
        n = s1["note"]
        chk("휴대폰" in n and "녹음기" in n, "휴대폰 녹음기를 쓰라고 한다")
        chk("음성 녹음" in n and "음성 메모" in n, "안드로이드·아이폰 녹음기 이름을 알려 준다")
        chk("녹음 파일 올리기" in n, "다음에 할 일(📁 올리기)을 알려 준다")
        chk("가까이" in n, "가까이서 담으라는 말이 있다")
        pg.click("#recBtn")
        pg.wait_for_timeout(800)
        s2 = state(pg)
        chk(s2["mic"] == 0 and not s2["on"], "두 번 눌러도 녹음 안 됨")
        chk(pg.locator("#recFile").count() == 1, "⑤ 「📁 녹음 파일 올리기」는 그대로 있다")
        over = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        chk(over <= 0, "가로 스크롤이 안 생긴다", f"{over}px")
        pg.screenshot(path=os.path.join(HERE, "screen_new_blocked.png"), full_page=True)

        # ── ② 회의록 상세 「🎙 녹음 추가」 ──────────────────
        print("\n[②] 회의록 상세 「🎙 녹음 추가」")
        pg2 = c.new_page()
        pg2.goto(f"{BASE}/meetings/{MID}", wait_until="domcontentloaded")
        pg2.wait_for_selector("#recBtn", state="attached", timeout=15000)
        pg2.evaluate("() => { var d=document.getElementById('redoTools'); if(d) d.open=true; }")
        pg2.wait_for_selector("#recBtn", timeout=15000)   # 「🔧 다시 하기」를 펴야 보인다
        pg2.wait_for_timeout(300)
        d0 = state(pg2)
        chk(not d0["autorec"], "보통으로 연 상세 화면에는 자동녹음 표시가 없다")
        pg2.click("#recBtn")
        pg2.wait_for_timeout(1200)
        d1 = state(pg2)
        chk(d1["mic"] == 0, "🔴 마이크를 아예 안 불렀다", f"호출 {d1['mic']}회")
        chk(not d1["on"], "녹음이 시작되지 않았다", d1["btn"])
        chk(d1["note"] != "" and "휴대폰" in d1["note"], "같은 안내가 뜬다")

        # ── ③ 🔴 이음 「▶ 회의 시작」은 막지 않는다 ─────────
        print("\n[③] 🔴 이음 「▶ 회의 시작」(?autorec=1) 은 그대로")
        pg3 = c.new_page()
        pg3.goto(f"{BASE}/meetings/{MID}?autorec=1", wait_until="domcontentloaded")
        pg3.wait_for_selector("#recBtn", state="attached", timeout=15000)
        pg3.wait_for_timeout(2500)
        a0 = state(pg3)
        chk(a0["autorec"], "단추에 자동녹음 표시가 남는다(막지 않는 길)")
        chk(a0["note"] == "", "자동으로 열린 창에는 막는 안내가 안 뜬다")
        chk(a0["mic"] > 0 or a0["on"] or a0["banner"],
            "이 길에서는 녹음이 그대로 시작된다", f"mic {a0['mic']} · on {a0['on']} · 띠 {a0['banner']}")

        # ── ④ 녹음 중 「⏹ 종료」는 그대로 ──────────────────
        print("\n[④] 녹음 중 「⏹ 종료」는 막지 않는다")
        pg4 = c.new_page()
        pg4.goto(f"{BASE}/meetings/new", wait_until="domcontentloaded")
        pg4.wait_for_selector("#recBtn", timeout=15000)
        pg4.evaluate("() => { document.getElementById('recBtn').dataset.on='1'; }")
        pg4.click("#recBtn")
        pg4.wait_for_timeout(600)
        e1 = state(pg4)
        chk(e1["note"] == "", "녹음 중에 누르면 막는 안내가 안 뜬다(종료로 간다)")

        # ── ⑥ 🔴 그럼 새 회의록은 어떻게 만드나 — 「📁 녹음 파일 올리기」가 그 길이다 ──
        print("\n[⑥] 🔴 새 회의록에서 올리기로 회의가 만들어지는가")
        wav = os.path.join(HERE, "z1143_test.wav")
        with open(wav, "wb") as f:
            f.write(b"RIFF" + (b"\0" * 4096))
        pg5 = c.new_page()
        calls = []
        pg5.on("request", lambda r: calls.append((r.method, r.url.split("127.0.0.1:%d" % PORT)[-1])))
        pg5.goto(f"{BASE}/meetings/new", wait_until="domcontentloaded")
        pg5.wait_for_selector("#recFile", state="attached", timeout=15000)
        pg5.locator("#recFile").set_input_files(wav)
        try:
            pg5.wait_for_function(
                "()=>{const t=document.getElementById('mtgBody');return t && t.value.indexOf('[가짜 변환]')>=0;}",
                timeout=40000)
            done = True
        except Exception:
            done = False
        chk(any(m == "POST" and u == "/api/meeting" for m, u in calls),
            "올리면 회의가 만들어진다(POST /api/meeting)", str([u for m, u in calls if m == "POST"][:3]))
        chk(done, "올리면 음성→글자·AI 정리까지 자동으로 된다",
            pg5.evaluate("()=>{const t=document.getElementById('mtgBody');return t?t.value.slice(0,30):'';}"))
        try:
            os.remove(wav)
        except Exception:
            pass

        b.close()

    print(f"\n{'=' * 46}  통과 {OK} · 실패 {FAIL}")
    if FAILS:
        print("실패 항목: " + ", ".join(FAILS))
    return 1 if FAIL else 0


sys.exit(main())
