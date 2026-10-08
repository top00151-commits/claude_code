# -*- coding: utf-8 -*-
"""휴대폰 UA 로 새 회의 화면을 열고 설치 안내 팝업이 뜨는지만 본다."""
import sys, io
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright
UA = ("Mozilla/5.0 (Linux; Android 13; SM-S918N) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120.0.0.0 Mobile Safari/537.36")
BASE = "http://127.0.0.1:8936"
with sync_playwright() as p:
    b = p.chromium.launch()
    c = b.new_context(user_agent=UA, viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    pg = c.new_page()
    pg.goto(BASE + "/meetings/new", wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    vis = pg.evaluate("()=>{const o=document.getElementById('worksInstallHint');return !!o && !o.hidden;}")
    print("설치 안내 팝업 떴나:", "예" if vis else "아니오")
    b.close()
