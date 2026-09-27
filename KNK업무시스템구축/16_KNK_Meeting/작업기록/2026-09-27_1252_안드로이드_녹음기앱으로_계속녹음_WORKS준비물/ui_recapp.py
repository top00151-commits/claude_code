# -*- coding: utf-8 -*-
"""z1127 화면 시험 — 「📱 녹음기 앱 열기」(안드로이드) · 못 열었을 때 안내 · 옛 거짓 문구 제거
  대표 실사(2026-09-26): `capture` 로 연 녹음기는 다른 앱으로 넘어가면 녹음을 끝내고 저장한다(사진 「최대 05:16」).
  → 녹음기 **앱 자체**를 여는 단추를 첫 선택으로. 끝난 파일은 「공유 → KNK WORKS」·「📁 음성 파일 올리기」.
실제 크롬으로 안드로이드(삼성·삼성 아님)·아이폰·PC 를 흉내 낸다. 사용: py -3.12 ui_recapp.py [포트=8936]
"""
import json
import os
import sys
import urllib.parse

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
    return br.new_context(user_agent=ua, viewport={"width": 390, "height": 844} if phone else {"width": 1440, "height": 900},
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
        app = p.locator("#recOpenApp")
        ok("「📱 녹음기 앱 열기」 단추가 보인다", app.is_visible(), app.count())
        txt = (app.inner_text() or "").replace("\n", " ")
        ok("단추 글자 = 녹음기 앱 열기", "녹음기 앱 열기" in txt, txt[:50])
        ok("부제 = 다른 앱을 봐도 계속 녹음", "계속 녹음" in txt, txt[:60])
        wrap = p.locator("#recPhoneRecWrap")
        wtxt = (wrap.inner_text() or "").replace("\n", " ")
        ok("옛 단추는 「짧은 회의용」으로 남는다", wrap.is_visible() and "녹음기로 바로 녹음" in wtxt, wtxt[:60])
        ok("옛 단추가 사실대로 적는다(다른 앱으로 가면 저장되고 끝남)", "저장되고 끝납니다" in wtxt, wtxt[:80])
        body = p.locator("body").inner_text()
        ok("🔴 거짓 문구 「다른 앱을 봐도 끊기지 않아요」 없음", "끊기지 않아요" not in body)
        order = p.evaluate("""() => {
            const a=document.getElementById('recOpenApp'), w=document.getElementById('recPhoneRecWrap'), b=document.getElementById('recBtn');
            if(!a||!w||!b) return 'missing';
            const f=(x,y)=> (x.compareDocumentPosition(y) & Node.DOCUMENT_POSITION_FOLLOWING) ? 1 : 0;
            return f(a,w) && f(w,b) ? 'app-first' : 'wrong';
        }""")
        ok("차례 = 녹음기 앱 열기 → 바로 녹음 → 이 화면 녹음", order == "app-first", order)

        # ══════════ ② 녹음기 앱을 여는 주소(intent) ══════════
        print("\n■ ② 녹음기 앱을 여는 주소", flush=True)
        url = p.evaluate("() => (window.__knkRecAppUrl ? window.__knkRecAppUrl() : '')")
        ok("intent 주소를 만든다", url.startswith("intent://#Intent;"), url[:80])
        ok("앱을 그냥 여는 방식(LAUNCHER) — 불려 나온 모드가 아니다",
           "action=android.intent.action.MAIN" in url and "category=android.intent.category.LAUNCHER" in url, url[:140])
        ok("삼성폰 → 삼성 녹음기 앱", "package=com.sec.android.app.voicenote;" in url, url[:160])
        ok("못 열면 이 화면으로 돌아오게(fallback)", "S.browser_fallback_url=" in url and url.endswith(";end"), url[-90:])
        fb = urllib.parse.unquote(url.split("S.browser_fallback_url=")[1].split(";end")[0])
        ok("돌아오는 주소에 recapp=manual 표시", "recapp=manual" in fb and fb.startswith(BASE), fb)
        ok("녹음기로 바로 녹음(capture) 입력은 그대로 하나",
           p.evaluate("() => document.querySelectorAll('#recFileCap[capture]').length") == 1)
        c.close()

        # ══════════ ③ 삼성이 아닌 안드로이드 ══════════
        print("\n■ ③ 삼성이 아닌 안드로이드(Pixel)", flush=True)
        c = ctx(br, UA_PIXEL)
        p = open_page(c, "/meetings/new")
        url2 = p.evaluate("() => (window.__knkRecAppUrl ? window.__knkRecAppUrl() : '')")
        ok("픽셀 → 구글 녹음기 앱", "package=com.google.android.apps.recorder;" in url2, url2[:160])
        ok("단추는 똑같이 보인다", p.locator("#recOpenApp").is_visible())
        c.close()

        # ══════════ ④ 자동으로 못 열었을 때(?recapp=manual) ══════════
        print("\n■ ④ 녹음기 앱을 자동으로 못 열었을 때", flush=True)
        c = ctx(br, UA_SAMSUNG)
        p = open_page(c, "/meetings/%d?recapp=manual" % MID)
        lead = p.locator("#recPhoneLead")
        ok("안내 상자가 뜬다", lead.is_visible(), lead.count())
        lt = (p.locator("#recPhoneLeadTtl").inner_text() or "")
        lw = (p.locator("#recPhoneLeadWhy").inner_text() or "")
        ok("제목 = 자동으로 열지 못했습니다", "자동으로 열지 못했습니다" in lt, lt[:60])
        ok("홈 화면에서 「음성 녹음」을 직접 열라고 안내", "음성 녹음" in lw and "직접" in lw, lw[:90])
        ok("끝난 뒤 길 = 공유 → KNK WORKS", "공유 → KNK WORKS" in lw, lw[-90:])
        ok("상자 안에 녹음기 앱 열기 단추가 있다",
           p.evaluate("() => { const s=document.getElementById('recPhoneLeadSlot'), a=document.getElementById('recOpenApp');"
                      " return !!s && !!a && s.contains(a); }"))
        c.close()

        # 새 회의록 화면은 상자가 없다 → 상태줄로 같은 말을 한다
        c = ctx(br, UA_SAMSUNG)
        p = open_page(c, "/meetings/new?recapp=manual")
        st = (p.locator("#recStatus").inner_text() or "")
        ok("새 회의록 화면: 상태줄로 안내", "자동으로 열지 못했습니다" in st and "음성 녹음" in st, st[:110])
        ok("새 회의록 화면 안내에도 공유 길", "공유 → KNK WORKS" in st, st[-80:])
        c.close()

        # ══════════ ⑤ 아이폰·PC 는 새 단추가 없다 ══════════
        print("\n■ ⑤ 아이폰·PC", flush=True)
        for ua, nm, ph in ((UA_IOS, "아이폰", True), (UA_PC, "PC", False)):
            c = ctx(br, ua, ph)
            p = open_page(c, "/meetings/new")
            ok("%s: 「녹음기 앱 열기」 단추 없음" % nm, not p.locator("#recOpenApp").is_visible())
            ok("%s: 옛 녹음기 단추도 없음" % nm, not p.locator("#recPhoneRecWrap").is_visible())
            c.close()

        # ══════════ ⑥ 기기별 안내(안드로이드) ══════════
        print("\n■ ⑥ 기기별 안내", flush=True)
        c = ctx(br, UA_SAMSUNG)
        p = open_page(c, "/meetings/new")
        nt = p.locator("#recPlatNote").inner_text() if p.locator("#recPlatNote").count() else ""
        ok("안내가 「녹음기 앱 열기」를 권한다", "녹음기 앱 열기" in nt, nt[:80])
        ok("안내가 공유 길을 알려 준다", "공유 → KNK WORKS" in nt, nt[:120])
        ok("안내가 옛 길의 한계를 적는다(저장되고 끝남·길이 상한)",
           "저장되고 끝나고" in nt and ("5분" in nt or "05:16" in nt), nt[-140:])
        ok("이 화면 녹음 설명은 그대로", "켜 둘 때만" in nt)
        ok("화면 오류 없음", not ERRS, ERRS[:3])
        c.close()
        br.close()

    print("\n" + "=" * 72)
    print("합계: 통과 %d · 실패 %d" % (len(OK), len(NG)))
    for x in NG:
        print("  - 실패:", x)
    sys.exit(1 if NG else 0)


if __name__ == "__main__":
    main()
