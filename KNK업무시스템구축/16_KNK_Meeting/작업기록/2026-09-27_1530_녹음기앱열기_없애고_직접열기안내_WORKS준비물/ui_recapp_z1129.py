# -*- coding: utf-8 -*-
"""z1129 화면 시험 — 「녹음기 앱 열기」 단추를 없애고 「홈 화면에서 직접 열기」 3단계 안내로
  까닭: 대표가 4번 눌렀고 4번 다 크롬이 거부(운영 로그 ?recapp=manual 4회) · 크롬은 BROWSABLE 을 적어 둔 앱만 연다.
  덤: 옛 단추는 누를 때마다 빈 회의록을 만들었다(46·47·49) → 새 회의록 화면에서는 아무것도 안 만든다.
실제 크롬으로 안드로이드(삼성·픽셀)·아이폰·PC 를 흉내 낸다. 사용: py -3.12 ui_recapp_z1129.py [포트=8936]
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8936
BASE = "http://127.0.0.1:%d" % PORT
HERE = os.path.dirname(os.path.abspath(__file__))

UA_SAMSUNG = ("Mozilla/5.0 (Linux; Android 14; SM-S928N) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/153.0.0.0 Mobile Safari/537.36")
UA_PIXEL = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/153.0.0.0 Mobile Safari/537.36")
UA_IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
          "CriOS/153.0.0.0 Mobile/15E148 Safari/604.1")
UA_PC = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
         "Chrome/153.0.0.0 Safari/537.36")

OK, NG, ERRS = [], [], []


def ok(name, cond, extra=""):
    (OK if cond else NG).append(name)
    print(("  ✅ " if cond else "  ❌ ") + name + (("  — " + str(extra)[:180]) if extra != "" else ""), flush=True)


def ctx(br, ua, phone=True):
    return br.new_context(user_agent=ua,
                          viewport={"width": 390, "height": 844} if phone else {"width": 1440, "height": 900},
                          is_mobile=phone, has_touch=phone, permissions=["microphone"], base_url=BASE)


def open_page(c, path):
    p = c.new_page()
    p.on("pageerror", lambda e: ERRS.append(str(e)))
    p.goto(BASE + path, wait_until="domcontentloaded")
    p.wait_for_timeout(900)
    return p


def main():
    seed = json.load(open(os.path.join(HERE, "seed_phrec.json"), encoding="utf-8"))
    MID = (seed.get("mids") or [1])[0]
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True, args=[
            "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])

        # ══════════ ① 안드로이드(삼성) 새 회의록 화면 ══════════
        print("\n■ ① 안드로이드(삼성) — 새 회의록 화면", flush=True)
        c = ctx(br, UA_SAMSUNG)
        p = open_page(c, "/meetings/new")
        ok("🔴 옛 「녹음기 앱 열기」 단추가 없다", p.locator("#recOpenApp").count() == 0)
        ok("🔴 앱 여는 주소를 만들지 않는다",
           p.evaluate("() => (typeof window.__knkRecAppUrl)") == "undefined")
        body = p.locator("body").inner_text()
        ok("🔴 화면에 「녹음기 앱 열기」 글자가 없다", "녹음기 앱 열기" not in body)
        g = p.locator("#recPhoneGuide")
        ok("3단계 안내 카드가 보인다", g.is_visible(), g.count())
        gt = (g.inner_text() or "").replace("\n", " ")
        ok("제목 = 휴대폰 녹음기로 녹음(안 끊김)", "휴대폰 녹음기로 녹음" in gt and "안 끊깁니다" in gt, gt[:70])
        ok("① 홈 화면에서 「음성 녹음」", "홈 화면" in gt and "음성 녹음" in gt, gt[:120])
        ok("② 공유 → KNK WORKS", "공유" in gt and "KNK WORKS" in gt, gt[120:230])
        ok("③ ＋ 새 회의록으로 정리", "새 회의록으로 정리" in gt, gt[200:320])
        ok("왜 직접 여는지 까닭도 적는다", "열 수 없어" in gt or "열 수 없습니다" in gt, gt[-90:])
        wrap = p.locator("#recPhoneRecWrap")
        wtxt = (wrap.inner_text() or "").replace("\n", " ")
        ok("「바로 녹음(짧은 회의)」은 그대로 있다", wrap.is_visible() and "녹음기로 바로 녹음" in wtxt, wtxt[:60])
        ok("그 길의 한계도 그대로 적는다", "저장되고 끝납니다" in wtxt, wtxt[:90])
        ok("이 화면 녹음 단추도 그대로", p.locator("#recBtn").is_visible())
        ok("녹음기로 바로 녹음(capture) 입력은 하나",
           p.evaluate("() => document.querySelectorAll('#recFileCap[capture]').length") == 1)
        order = p.evaluate("""() => {
            const g=document.getElementById('recPhoneGuide'), w=document.getElementById('recPhoneRecWrap'),
                  b=document.getElementById('recBtn');
            if(!g||!w||!b) return 'missing';
            const f=(x,y)=> (x.compareDocumentPosition(y) & Node.DOCUMENT_POSITION_FOLLOWING) ? 1 : 0;
            return f(g,w) && f(w,b) ? 'guide-first' : 'wrong';
        }""")
        ok("차례 = 안내 → 바로 녹음 → 이 화면 녹음", order == "guide-first", order)
        note = (p.locator("#recPlatNote").inner_text() or "") if p.locator("#recPlatNote").count() else ""
        ok("기기별 안내도 홈 화면에서 열라고 적는다",
           ("홈 화면" in note and "음성 녹음" in note) if note else True, note[:120])
        c.close()

        # ══════════ ② 삼성이 아닌 안드로이드 ══════════
        print("\n■ ② 삼성이 아닌 안드로이드(Pixel)", flush=True)
        c = ctx(br, UA_PIXEL)
        p = open_page(c, "/meetings/new")
        ok("안내 카드는 똑같이 보인다", p.locator("#recPhoneGuide").is_visible())
        ok("옛 단추 없음", p.locator("#recOpenApp").count() == 0)
        c.close()

        # ══════════ ③ 아이폰·PC 는 안 보인다 ══════════
        print("\n■ ③ 아이폰·PC", flush=True)
        for ua, nm, phone in ((UA_IOS, "아이폰", True), (UA_PC, "PC", False)):
            c = ctx(br, ua, phone)
            p = open_page(c, "/meetings/new")
            ok("%s: 안내 카드 숨김" % nm, not p.locator("#recPhoneGuide").is_visible())
            ok("%s: 「바로 녹음」도 숨김" % nm, not p.locator("#recPhoneRecWrap").is_visible())
            ok("%s: 이 화면 녹음은 보인다" % nm, p.locator("#recBtn").is_visible())
            c.close()

        # ══════════ ④ 상세 화면 — 안내 카드 + 「휴대폰 녹음기로 녹음할게요」 ══════════
        print("\n■ ④ 상세 화면(안드로이드)", flush=True)
        c = ctx(br, UA_SAMSUNG)
        p = open_page(c, "/meetings/%d" % MID)
        p.evaluate("() => { const d=document.getElementById('redoTools'); if(d) d.open=true; }")
        p.wait_for_timeout(300)
        ok("상세 화면에도 안내 카드가 있다", p.locator("#recPhoneGuide").is_visible())
        mine = p.locator("#recPhoneMine")
        ok("「📱 휴대폰 녹음기로 녹음할게요」 단추가 보인다", mine.is_visible(), mine.count())
        ok("단추 글자", "휴대폰 녹음기로 녹음할게요" in (mine.inner_text() or ""), (mine.inner_text() or "")[:40])
        url_before = p.url
        mine.click()
        p.wait_for_timeout(800)
        ok("눌러도 화면이 딴 데로 가지 않는다(앱 열기 시도 없음)", p.url == url_before, p.url[-40:])
        st = (p.locator("#recStatus").inner_text() or "")
        ok("누르면 홈 화면에서 여는 길을 안내한다", "홈 화면" in st and "음성 녹음" in st, st[:110])
        ok("끝난 뒤 붙이는 길도 안내한다", "공유" in st and "KNK WORKS" in st, st[-80:])
        ok("안내 카드가 그대로 보인다", p.locator("#recPhoneGuide").is_visible())
        c.close()

        # ══════════ ⑤ 옛 주소(?recapp=manual)로 들어와도 같은 안내 ══════════
        print("\n■ ⑤ 옛 주소 호환(?recapp=manual)", flush=True)
        c = ctx(br, UA_SAMSUNG)
        p = open_page(c, "/meetings/new?recapp=manual")
        st = (p.locator("#recStatus").inner_text() or "")
        ok("상태줄이 홈 화면에서 열라고 안내", "홈 화면" in st and "음성 녹음" in st, st[:110])
        ok("자동으로 못 열었다는 옛 말은 없다", "자동으로 열지 못했습니다" not in st, st[:80])
        c.close()

        print("\n" + "=" * 72)
        ok("화면 오류 없음", not ERRS, ERRS[:2])
        print("합계: 통과 %d · 실패 %d" % (len(OK), len(NG)), flush=True)
        for n in NG:
            print("  - 실패:", n, flush=True)
        br.close()
    return 1 if NG else 0


if __name__ == "__main__":
    sys.exit(main())
