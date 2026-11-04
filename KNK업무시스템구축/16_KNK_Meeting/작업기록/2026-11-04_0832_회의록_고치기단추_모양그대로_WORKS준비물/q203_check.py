# -*- coding: utf-8 -*-
"""z1203 검사 — 회의록 「✏ 고치기」 = 보이는 모양 그대로 고치기 모드(글 상자로 안 바꿈)
대표 2026-11-04 「고치기를 눌렀을 때도 사진 1 형태가 유지되는 상태에서 고칠 수 있게」
사용: py -3.12 q203_check.py <포트> <앱폴더>     (run_q203_app.py 로 띄운 새 서버 · 서버당 한 번)
🔒 시험 글은 모두 지어낸 것."""
import io
import json
import os
import sqlite3
import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
PORT = int(sys.argv[1])
APP = sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
SEED = json.load(io.open(os.path.join(HERE, "seed_%d.json" % PORT), encoding="utf-8"))
ME, MEM = SEED["me"], SEED["mem"]
M1, M2 = SEED["ids"]["M1"], SEED["ids"]["M2"]
BASE = "http://127.0.0.1:%d" % PORT
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
NP = [0, 0]


def _isoff(t):
    """z1205: 시작 단추 글 = 「✏ 고치기」(z1204 까지) 또는 「✏ 수정하기」(z1205~)"""
    return "고치기" in t or "수정하기" in t


def chk(name, cond, extra=""):
    NP[0 if cond else 1] += 1
    print(("  ✅ " if cond else "  ❌ ") + name + ("" if cond else "  ← " + str(extra)[:300]))


def summ(mid):
    c = sqlite3.connect(os.path.join(APP, "data", "knk.db"))
    r = c.execute("SELECT summary FROM meetings WHERE id=?", (mid,)).fetchone()[0] or ""
    c.close()
    return r


GEO = """() => { const b = document.getElementById('mtgSummary'); const r = b.getBoundingClientRect();
  return { vis: !b.hidden && r.height > 0, h: Math.round(r.height), top: Math.round(r.top), y: Math.round(window.scrollY),
           tops: Array.from(b.children).map(x => Math.round(x.getBoundingClientRect().top - r.top)) }; }"""


def page(b, uid, mid, w=1280, h=900, mobile=False):
    ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=mobile, has_touch=mobile)
    ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": BASE}])
    pg = ctx.new_page()
    pg.on("dialog", lambda d: d.accept())
    pg.goto(BASE + "/meetings/%d" % mid, wait_until="domcontentloaded")
    pg.wait_for_selector("#mtgSummary", timeout=15000)
    pg.wait_for_timeout(600)
    pg.evaluate("() => { const d = document.getElementById('worksInstallHint'); if (d) d.remove(); }")
    return ctx, pg


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        print("== 「✏ 고치기」 = 모양 그대로 ==")
        ctx, pg = page(b, ME, M1)
        pg.evaluate("() => document.getElementById('btnSumEdit').scrollIntoView({block: 'start'})")
        pg.evaluate("() => window.scrollBy(0, -80)")
        pg.wait_for_timeout(200)
        g0 = pg.evaluate(GEO)
        pg.screenshot(path=os.path.join(SHOTS, "before.png"))
        pg.click("#btnSumEdit")
        pg.wait_for_timeout(300)
        g1 = pg.evaluate(GEO)
        pg.screenshot(path=os.path.join(SHOTS, "mode_on.png"))
        chk("글 상자 안 나옴", not pg.is_visible("#sumEditWrap"))
        chk("정리 모양 그대로 보임", g1["vis"])
        chk("줄 자리·칸 높이 그대로", g1["tops"] == g0["tops"] and abs(g1["h"] - g0["h"]) <= 1, (g0["h"], g1["h"]))
        chk("화면이 안 움직임(스크롤·정리 칸 위치 그대로)", g1["y"] == g0["y"] and g1["top"] == g0["top"], (g0["y"], g1["y"], g0["top"], g1["top"]))
        chk("안내 띠 보임 · 단추 「그만두기」", pg.is_visible("#kleModeBar") and any(x in pg.inner_text("#btnSumEdit") for x in ("그만두기", "수정 완료")))   # z1204: 「✔ 수정 완료」
        chk("고칠 줄에 점선(빈 줄 빼고)", pg.evaluate("""() => Array.from(document.querySelectorAll('#mtgSummary [data-kle-on]'))
            .every(e => getComputedStyle(e).outlineStyle === 'dashed')"""))
        # 모드 안에서 한 줄 고치기 → 모드 유지
        sel = '#mtgSummary > [data-kle="6"]'
        pg.click(sel)
        pg.evaluate("""(s) => { const el = document.querySelector(s); const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
            while (tw.nextNode()) { const i = tw.currentNode.nodeValue.indexOf('감'); if (i >= 0) { const r = document.createRange();
            r.setStart(tw.currentNode, i); r.setEnd(tw.currentNode, i + 1); const g = getSelection(); g.removeAllRanges(); g.addRange(r); return; } } }""", sel)
        pg.keyboard.type("강")
        chk("고치는 줄은 실선(점선 아님)", pg.evaluate("(s) => getComputedStyle(document.querySelector(s)).outlineStyle", sel) == "solid")
        pg.keyboard.press("Enter")
        pg.wait_for_selector(".kle-toast", timeout=8000)
        pg.wait_for_timeout(300)
        chk("모드에서 고친 줄 저장", "- 강 팀장이 업체에" in summ(M1))
        chk("저장 뒤에도 모드 유지", pg.is_visible("#kleModeBar") and pg.evaluate("() => document.getElementById('mtgSummary').hasAttribute('data-kle-mode')"))
        # 그만두기
        pg.click("#btnSumEdit")
        pg.wait_for_timeout(200)
        chk("그만두기 = 모드 끝 · 안내 띠 숨김 · 단추 「고치기」", (not pg.is_visible("#kleModeBar")) and _isoff(pg.inner_text("#btnSumEdit"))
            and not pg.evaluate("() => document.getElementById('mtgSummary').hasAttribute('data-kle-mode')"))
        chk("모드 끝나면 점선 없음", pg.evaluate("""() => Array.from(document.querySelectorAll('#mtgSummary [data-kle-on]'))
            .every(e => getComputedStyle(e).outlineStyle !== 'dashed')"""))
        # 글 전체로 고치기(줄 넣기·빼기) = 예전 글 상자
        pg.click("#btnSumEdit")
        pg.click("#btnSumRaw")
        pg.wait_for_timeout(300)
        chk("「글 전체로 고치기」 = 글 상자 · 원래 글(## ·**)", pg.is_visible("#sumEdit") and pg.input_value("#sumEdit").startswith("## 핵심")
            and not pg.is_visible("#kleModeBar"))
        pg.click("#btnSumCancel")
        pg.wait_for_timeout(300)
        chk("글 상자 취소 = 정리 모양으로 · 단추 「고치기」", pg.is_visible("#mtgSummary") and _isoff(pg.inner_text("#btnSumEdit"))
            and not pg.is_visible("#kleModeBar"))
        pg.click("#btnSumEdit")
        pg.click("#btnSumRaw")
        pg.fill("#sumEdit", summ(M1) + "\n- 글 상자로 넣은 줄")
        pg.click("#btnSumSave")
        pg.wait_for_timeout(1200)
        chk("글 상자 저장(줄 넣기) 그대로 됨", summ(M1).endswith("- 글 상자로 넣은 줄") and pg.is_visible("#mtgSummary"))
        chk("새 줄도 그 자리 고치기 대상", pg.evaluate("() => document.querySelectorAll('#mtgSummary [data-kle-on]').length") >= 11)
        # 글 상자 열린 채 「그만두기」(단추) = 닫힘
        pg.click("#btnSumEdit")
        pg.click("#btnSumRaw")
        pg.click("#btnSumEdit")
        pg.wait_for_timeout(200)
        chk("글 상자에서 단추 = 닫힘", (not pg.is_visible("#sumEditWrap")) and pg.is_visible("#mtgSummary"))
        ctx.close()

        print("== 정리 없는 회의 · 보기만 · 휴대폰 ==")
        ctx, pg = page(b, ME, M2)
        if pg.locator("#btnSumEdit").count() and pg.is_visible("#btnSumEdit"):
            pg.click("#btnSumEdit")
            pg.wait_for_timeout(200)
            chk("정리 없는 회의 = 줄 고치기 못 하니 예전 글 상자", pg.is_visible("#sumEdit") and not pg.is_visible("#kleModeBar"))
        else:
            chk("정리 없는 회의 = 고치기 단추 자체 없음(그대로)", True)
        ctx.close()
        ctx, pg = page(b, MEM, M1)
        chk("보기만 = 고치기 단추·안내 띠 없음", pg.locator("#btnSumEdit").count() == 0 and pg.locator("#kleModeBar").count() == 0)
        ctx.close()
        ctx, pg = page(b, ME, M1, 390, 844, True)
        g0 = pg.evaluate(GEO)
        pg.tap("#btnSumEdit")
        pg.wait_for_timeout(300)
        g1 = pg.evaluate(GEO)
        chk("휴대폰도 모양 그대로(줄 자리·높이)", g1["vis"] and g1["tops"] == g0["tops"] and not pg.is_visible("#sumEditWrap"))
        chk("휴대폰 정리 칸 위치 차이 ≤ 한 줄(안내 글 길이 차이)", abs((g1["top"] + g1["y"]) - (g0["top"] + g0["y"])) <= 18, (g0["top"] + g0["y"], g1["top"] + g1["y"]))
        pg.screenshot(path=os.path.join(SHOTS, "phone_mode_on.png"))
        ctx.close()
        b.close()
    print("결과: 통과 %d · 실패 %d" % (NP[0], NP[1]))
    sys.exit(1 if NP[1] else 0)


main()
