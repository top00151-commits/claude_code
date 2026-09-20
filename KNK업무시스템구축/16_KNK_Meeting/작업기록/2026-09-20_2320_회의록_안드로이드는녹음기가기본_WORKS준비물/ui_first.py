# -*- coding: utf-8 -*-
"""z1118 화면 시험 — 이음 「▶ 회의 시작」 착지에서 안드로이드는 **녹음기가 기본**

· 안드로이드: 이 화면 녹음을 켜지 않고, 큰 단추 한 번으로 녹음기가 열린다
· 30초 안에 아무것도 안 누르면 예전처럼 이 화면 녹음을 켠다(안전망)
· 아이폰·PC 는 지금 그대로(이 화면 녹음 자동 시작)
사용: py -3.12 ui_first.py <seed_phrec.json 폴더>
"""
import io
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

SEED_DIR = sys.argv[1]
seed = json.load(io.open(os.path.join(SEED_DIR, "seed_phrec.json"), encoding="utf-8"))
PORT, MIDS = seed["port"], seed["mids"]
BASE = "http://localhost:%d" % PORT
HERE = os.path.dirname(os.path.abspath(__file__))
WAV = os.path.join(HERE, "_시험용_녹음기파일.wav")

UA_AND = ("Mozilla/5.0 (Linux; Android 14; SM-S928N) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/153.0.0.0 Mobile Safari/537.36")
UA_IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
          "CriOS/153.0.0.0 Mobile/15E148 Safari/604.1")
UA_PC = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
         "Chrome/153.0.0.0 Safari/537.36")
HIDE = ("document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style');"
        "s.textContent = '#worksInstallHint{display:none !important}'; document.head.appendChild(s); });")

OK, NG = [], []


def ok(name, cond, extra=""):
    (OK if cond else NG).append(name)
    print(("PASS " if cond else "FAIL ") + name + ((" · " + str(extra)[:180]) if extra != "" else ""), flush=True)


def make_wav(path):
    rate, n = 8000, 16000
    data = b"".join(struct.pack("<h", 0) for _ in range(n))
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16))
        f.write(b"data" + struct.pack("<I", len(data)) + data)


def ctx(br, ua, phone):
    c = br.new_context(service_workers="block", permissions=["microphone"], user_agent=ua,
                       viewport={"width": 390, "height": 844} if phone else {"width": 1280, "height": 900},
                       is_mobile=phone, has_touch=phone)
    c.add_init_script(HIDE)
    return c


def rec_on(p):
    return p.evaluate("() => { const b=document.getElementById('recBanner'); return !!b && !b.hidden; }")


def api(p, path):
    return p.evaluate("""async (x) => { const r = await fetch(x); return await r.json(); }""", path)


def main():
    make_wav(WAV)
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True,
                                args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])

        # ══════════ ① 안드로이드 — 녹음기가 기본, 웹 녹음은 안 켠다 ══════════
        print("\n■ ① 안드로이드 착지 — 녹음기가 기본", flush=True)
        M1 = MIDS[0]
        c = ctx(br, UA_AND, True)
        p = c.new_page()
        p.goto("%s/meetings/%d?autorec=1" % (BASE, M1), wait_until="domcontentloaded")
        p.wait_for_timeout(4000)

        lead = p.locator("#recPhoneLead")
        ok("착지 안내 상자가 보인다", lead.is_visible())
        ok("제목 = 「아직 녹음이 시작되지 않았습니다」",
           "아직 녹음이 시작되지 않았습니다" in (p.locator("#recPhoneLeadTtl").inner_text() or ""),
           p.locator("#recPhoneLeadTtl").inner_text())
        ok("단추 = 「📱 녹음기로 회의 녹음 시작」",
           "녹음기로 회의 녹음 시작" in (p.locator("#recPhoneBtnLbl").inner_text() or ""),
           p.locator("#recPhoneBtnLbl").inner_text())
        ok("까닭 = 다른 앱·화면 꺼짐에도 안 끊김",
           "끊기지 않습니다" in (p.locator("#recPhoneLeadWhy").inner_text() or ""))
        ok("30초 뒤 이 화면 녹음이 시작된다고 알린다",
           "30초" in (p.locator("#recPhoneLeadFoot").inner_text() or ""),
           p.locator("#recPhoneLeadFoot").inner_text())

        ok("🔴 이 화면 녹음은 켜지지 않았다", not rec_on(p))
        st = api(p, "/api/meeting/%d/rec-status" % M1)
        ok("🔴 서버도 「녹음 중」이 아니다", (st.get("rec") or {}).get("state") != "recording", st.get("rec"))
        ok("상태줄이 눌러 달라고 안내한다",
           "녹음기로 회의 녹음 시작" in (p.locator("#recStatus").inner_text() or ""),
           (p.locator("#recStatus").inner_text() or "")[:80])

        with p.expect_file_chooser() as fc:
            p.locator("#recPhoneRecWrap").click()
        ok("누르면 녹음기가 열린다", fc.value is not None)
        p.wait_for_timeout(1500)
        ok("눌렀으니 표시가 남는다",
           bool(p.evaluate("() => localStorage.getItem('knk_mtg_phonerec')")))

        p.locator("#recFileCap").set_input_files(WAV)
        for _ in range(80):
            b = p.evaluate("() => (document.getElementById('mtgBody')||{}).value || ''")
            if "가짜 변환" in b:
                break
            p.wait_for_timeout(500)
        body = p.evaluate("() => (document.getElementById('mtgBody')||{}).value || ''")
        ok("녹음기 파일이 오면 자동으로 글자·정리까지", "가짜 변환" in body, body[:40])
        ok("이 화면 녹음은 끝까지 안 켜졌다(조각 없음)", body.count("가짜 변환") == 1,
           "가짜 변환 %d회" % body.count("가짜 변환"))
        c.close()

        # ══════════ ② 30초 안 누르면 이 화면 녹음(안전망) ══════════
        print("\n■ ② 30초 동안 안 누르면 — 예전처럼 이 화면 녹음", flush=True)
        M2 = MIDS[1]
        c = ctx(br, UA_AND, True)
        p = c.new_page()
        p.goto("%s/meetings/%d?autorec=1" % (BASE, M2), wait_until="domcontentloaded")
        p.wait_for_timeout(3000)
        ok("아직은 안 켜져 있다", not rec_on(p))
        p.wait_for_timeout(31000)
        ok("30초 뒤 이 화면 녹음이 켜진다", rec_on(p))
        ok("상자가 「녹음기로 바꾸기」 안내로 바뀐다",
           "휴대폰 녹음기로 녹음하시겠어요" in (p.locator("#recPhoneLeadTtl").inner_text() or ""),
           p.locator("#recPhoneLeadTtl").inner_text())
        ok("단추 글자도 「📱 휴대폰 녹음기로 녹음」으로",
           (p.locator("#recPhoneBtnLbl").inner_text() or "").strip() == "📱 휴대폰 녹음기로 녹음",
           p.locator("#recPhoneBtnLbl").inner_text())
        st = api(p, "/api/meeting/%d/rec-status" % M2)
        ok("서버도 「녹음 중」으로 안다", (st.get("rec") or {}).get("state") == "recording", st.get("rec"))
        ok("왜 켰는지 상자에 남는다(상태줄은 곧 덮인다)",
           "30초 동안 고르지 않아" in (p.locator("#recPhoneLeadFoot").inner_text() or ""),
           (p.locator("#recPhoneLeadFoot").inner_text() or "")[:90])
        ok("지금이라도 녹음기로 바꿀 수 있다고 알린다",
           "그대로 이어집니다" in (p.locator("#recPhoneLeadFoot").inner_text() or ""))
        c.close()

        # ══════════ ③ 아이폰 — 지금 그대로 ══════════
        print("\n■ ③ 아이폰 — 지금 그대로 이 화면 녹음", flush=True)
        M3 = MIDS[2]
        c = ctx(br, UA_IOS, True)
        p = c.new_page()
        p.goto("%s/meetings/%d?autorec=1" % (BASE, M3), wait_until="domcontentloaded")
        p.wait_for_timeout(4000)
        ok("아이폰: 이 화면 녹음이 바로 켜진다(기다리지 않는다)", rec_on(p))
        ok("아이폰: 착지 상자 없음", not p.locator("#recPhoneLead").is_visible())
        ok("아이폰: 녹음기 단추 없음", not p.locator("#recPhoneRecWrap").is_visible())
        nt = p.locator("#recPlatNote").inner_text() if p.locator("#recPlatNote").is_visible() else ""
        ok("아이폰: 「넘어가면 그동안은 녹음되지 않습니다」 안내 그대로", "녹음되지 않습니다" in nt, nt[:60])
        c.close()

        # ══════════ ④ PC — 지금 그대로 ══════════
        print("\n■ ④ PC — 지금 그대로", flush=True)
        M4 = MIDS[3]
        c = ctx(br, UA_PC, False)
        p = c.new_page()
        p.goto("%s/meetings/%d?autorec=1" % (BASE, M4), wait_until="domcontentloaded")
        p.wait_for_timeout(4000)
        ok("PC: 이 화면 녹음이 바로 켜진다", rec_on(p))
        ok("PC: 착지 상자 없음", not p.locator("#recPhoneLead").is_visible())
        c.close()

        br.close()

    print("\n" + "=" * 60)
    print("합계: 통과 %d · 실패 %d" % (len(OK), len(NG)))
    for n in NG:
        print("  ❌ " + n)
    try:
        os.remove(WAV)
    except OSError:
        pass
    sys.exit(1 if NG else 0)


main()
