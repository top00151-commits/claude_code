# -*- coding: utf-8 -*-
"""대표님께 보여 드릴 화면 넉 장. 사용: py -3.12 shot_z1148.py [포트=8941] [저장폴더]"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8941
OUTD = sys.argv[2] if len(sys.argv) > 2 else HERE
BASE = "http://127.0.0.1:%d" % PORT
S = json.load(io.open(os.path.join(HERE, "seed_vw.json"), encoding="utf-8"))
MID = S["mid"]


def shot(pg, nm, sel=None):
    p = os.path.join(OUTD, nm)
    (pg.locator(sel) if sel else pg).screenshot(path=p)
    print("  저장:", nm)


with sync_playwright() as p:
    b = p.chromium.launch()
    c = b.new_context(viewport={"width": 1180, "height": 980}, device_scale_factor=2)

    # ① 「🔗 연결」 잠긴 모습 — 대표 계정(영업 권한이 있어야 칸이 뜬다)
    c.add_cookies([{"name": "tuser", "value": str(S["ceo"]), "url": BASE}])
    pg = c.new_page()
    pg.goto("%s/meetings/%d" % (BASE, MID), wait_until="domcontentloaded")
    pg.wait_for_selector("#secLink", timeout=15000)
    pg.locator("#secLink").scroll_into_view_if_needed()
    pg.wait_for_timeout(400)
    shot(pg, "화면1_연결칸_잠김.png", "#secLink")

    # ② 「이 사람들도 보기」 — 고르는 명단을 편 모습 (회의록 주인)
    c.clear_cookies()
    c.add_cookies([{"name": "tuser", "value": str(S["owner"]), "url": BASE}])
    pg.close()
    pg = c.new_page()
    pg.goto("%s/meetings/%d" % (BASE, MID), wait_until="domcontentloaded")
    pg.wait_for_selector("#vwOpen", timeout=15000)
    pg.click("#vwOpen")
    pg.wait_for_selector("#vwList .vw-row", timeout=15000)
    pg.fill("#vwQ", "문가온")
    pg.wait_for_timeout(250)
    pg.locator("#vwList .vw-row input").first.check()
    pg.wait_for_timeout(150)
    shot(pg, "화면2_직원고르기.png", "#vwFld")

    # ③ 고르고 저장한 뒤
    pg.click("#vwSave")
    pg.wait_for_selector("#vwChips .vw-chip", timeout=15000)
    pg.wait_for_timeout(300)
    shot(pg, "화면3_고른뒤.png", "#vwFld")

    # ④ 그 사람(문가온)의 회의록 목록 — 참석 안 했는데 이제 보인다
    c.clear_cookies()
    c.add_cookies([{"name": "tuser", "value": str(S["out"]), "url": BASE}])
    pg.close()
    pg = c.new_page()
    pg.goto("%s/meetings" % BASE, wait_until="domcontentloaded")
    pg.wait_for_timeout(700)
    shot(pg, "화면4_그사람_목록에보임.png")
    b.close()
print("끝")
