# -*- coding: utf-8 -*-
"""z1120 증거용 — 안드로이드: 창이 닫혀 멈춘 내 녹음이 열린 채 「📱 휴대폰 녹음기로 녹음」을 누르면
끊긴 조각이 정리에 들어가나(고치기 전 = 빠지고 서버가 계속 「녹음 중」). 사용: py -3.12 ui_gap_only.py <seed 폴더>"""
import io, json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright
W = sys.argv[1]
seed = json.load(io.open(os.path.join(W, "seed_resume.json"), encoding="utf-8"))
BASE, G, CEO = "http://localhost:%d" % seed["port"], seed["mids"]["G"], seed["ceo"]
UA = "Mozilla/5.0 (Linux; Android 14; SM-S928N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Mobile Safari/537.36"
with sync_playwright() as pw:
    br = pw.chromium.launch(channel="chrome", headless=True, args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])
    c = br.new_context(service_workers="block", permissions=["microphone"], user_agent=UA, viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    c.add_cookies([{"name": "tuser", "value": str(CEO), "url": BASE}])
    c.add_init_script("document.addEventListener('DOMContentLoaded',()=>{const s=document.createElement('style');s.textContent='#worksInstallHint{display:none !important}';document.head.appendChild(s);});")
    p = c.new_page()
    p.goto("%s/meetings/%d" % (BASE, G), wait_until="domcontentloaded"); p.wait_for_timeout(1500)
    p.evaluate("() => { document.getElementById('redoTools').open = true; }")
    with p.expect_file_chooser():
        p.locator("#recPhoneRecWrap").click()
    p.wait_for_timeout(1500)
    p.locator("#recFileCap").set_input_files(os.path.join(W, "_시험용_녹음기파일.wav"))
    for _ in range(60):
        b = p.evaluate("() => (document.getElementById('mtgBody')||{}).value || ''")
        if "[가짜 변환]" in b and (p.evaluate("() => (document.getElementById('mtgSummary')||{}).textContent||''").find("가짜 정리") >= 0):
            break
        p.wait_for_timeout(500)
    b = p.evaluate("() => (document.getElementById('mtgBody')||{}).value || ''")
    nm = [x.replace(". ", ".") for x in re.findall(r"\[가짜 변환\] (rec_\d+\.\s?\w+)", b)]
    st = p.evaluate("async (u) => (await (await fetch(u)).json()).rec", "/api/meeting/%d/rec-status" % G)
    print("본문에 붙은 녹음:", nm)
    print("서버 녹음 상태:", {k: st.get(k) for k in ("state", "secs", "pending")})
    print("끊긴 조각 포함:", any(x.startswith("rec_%d." % (1789970000000 + G * 1000)) for x in nm))
    br.close()
