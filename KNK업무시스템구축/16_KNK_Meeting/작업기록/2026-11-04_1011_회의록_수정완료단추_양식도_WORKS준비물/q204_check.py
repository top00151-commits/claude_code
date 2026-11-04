# -*- coding: utf-8 -*-
"""z1204 검사 — 「✏ 고치기」를 눌러야 고친다 · 다 고치면 「✔ 수정 완료」(고치던 줄도 저장) · 회의록 양식도 같게
대표 2026-11-04 「수정하고 다음은 어떻게해? 그만두기? "수정완료" 버튼이 있어야할것 같은데」
                「여기서도(회의록 양식) 수정할때 수정하기 누르고 완료되면 수정완료 이렇게 누르게 해야해」
사용: py -3.12 q204_check.py <포트> <앱폴더>     (run_q204_app.py 로 띄운 새 서버 · 서버당 한 번)
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
M1, M2, D2 = SEED["ids"]["M1"], SEED["ids"]["M2"], SEED["ids"]["D2"]
BASE = "http://127.0.0.1:%d" % PORT
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
NP = [0, 0]
ERRS = []


def chk(name, cond, extra=""):
    NP[0 if cond else 1] += 1
    print(("  ✅ " if cond else "  ❌ ") + name + ("" if cond else "  ← " + str(extra)[:300]))


def q(sql, *a):
    c = sqlite3.connect(os.path.join(APP, "data", "knk.db"))
    r = c.execute(sql, a).fetchone()
    c.close()
    return r[0] if r else None


def summ(mid):
    return q("SELECT summary FROM meetings WHERE id=?", mid) or ""


def page(b, uid, url, w=1280, h=900, mobile=False):
    ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=mobile, has_touch=mobile)
    ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": BASE}])
    pg = ctx.new_page()
    pg.on("dialog", lambda d: d.accept())
    pg.on("pageerror", lambda e: ERRS.append(str(e)))
    pg.goto(BASE + url, wait_until="domcontentloaded")
    pg.wait_for_timeout(700)
    pg.evaluate("() => { const d = document.getElementById('worksInstallHint'); if (d) d.remove(); }")
    return ctx, pg


def select_char(pg, sel, ch):
    pg.evaluate("""([s, ch]) => { const el = document.querySelector(s); const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
        while (tw.nextNode()) { const i = tw.currentNode.nodeValue.indexOf(ch); if (i >= 0) { const r = document.createRange();
        r.setStart(tw.currentNode, i); r.setEnd(tw.currentNode, i + 1); const g = getSelection(); g.removeAllRanges(); g.addRange(r); return; } } }""", [sel, ch])


def editing(pg, sel):
    return pg.evaluate("(s) => document.querySelector(s).isContentEditable", sel)


DOC_GEO = """() => { const s = document.querySelector('.sheet').getBoundingClientRect();
  return { top: Math.round(s.top + window.scrollY), h: Math.round(s.height) }; }"""


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        print("== 정리 화면: 「✏ 고치기」 → 「✔ 수정 완료」 ==")
        ctx, pg = page(b, ME, "/meetings/%d" % M1)
        pg.wait_for_selector("#mtgSummary")
        sel = '#mtgSummary > [data-kle="6"]'
        chk("누르기 전 안내 = 「✏ 고치기」를 누르면 …", pg.is_visible("#kleHint") and "고치기」를 누르면" in pg.inner_text("#kleHint"))
        pg.click(sel)
        pg.wait_for_timeout(200)
        chk("누르기 전엔 줄을 눌러도 안 고쳐진다", not editing(pg, sel))
        chk("누르기 전엔 점선 없음", pg.evaluate("""() => Array.from(document.querySelectorAll('#mtgSummary [data-kle-on]'))
            .every(e => getComputedStyle(e).outlineStyle !== 'dashed')"""))
        pg.click("#btnSumEdit")
        pg.wait_for_timeout(250)
        chk("「✏ 고치기」 → 단추 「✔ 수정 완료」", "수정 완료" in pg.inner_text("#btnSumEdit"), pg.inner_text("#btnSumEdit"))
        chk("안내 띠에 「다 고치면 ✔ 수정 완료」", "수정 완료" in pg.inner_text("#kleModeBar"))
        pg.click(sel)
        select_char(pg, sel, "감")
        pg.keyboard.type("강")
        pg.wait_for_timeout(150)
        pg.screenshot(path=os.path.join(SHOTS, "form_editing.png"))
        # Enter 안 누르고 바로 「✔ 수정 완료」
        pg.click("#btnSumEdit")
        pg.wait_for_timeout(1500)
        chk("Enter 안 누르고 「✔ 수정 완료」 = 고치던 줄 저장", "- 강 팀장이 업체에" in summ(M1), summ(M1)[:200])
        chk("수정 완료 = 모드 끝 · 단추 「✏ 고치기」 · 안내 띠 숨김", "고치기" in pg.inner_text("#btnSumEdit") and not pg.is_visible("#kleModeBar")
            and not pg.evaluate("() => document.getElementById('mtgSummary').hasAttribute('data-kle-mode')"))
        chk("화면에도 고친 글", "강 팀장이 업체에" in pg.inner_text("#mtgSummary"))
        pg.screenshot(path=os.path.join(SHOTS, "form_done.png"))
        # Esc 는 그 줄 취소(모드는 그대로)
        pg.click("#btnSumEdit")
        pg.click(sel)
        pg.keyboard.type("XYZ")
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(300)
        chk("Esc = 그 줄만 취소 · 모드 그대로", "XYZ" not in summ(M1) and "수정 완료" in pg.inner_text("#btnSumEdit"))
        pg.click("#btnSumEdit")
        pg.wait_for_timeout(300)
        chk("바뀐 것 없이 「✔ 수정 완료」 = 그냥 끝", "XYZ" not in summ(M1) and "고치기" in pg.inner_text("#btnSumEdit"))
        ctx.close()

        print("== 회의록 양식: 「✏ 고치기」 → 「✔ 수정 완료」 ==")
        for w, h, mob, tag in ((1280, 900, False, "pc"), (390, 844, True, "phone")):
            ctx, pg = page(b, ME, "/meetings/%d/doc" % M1, w, h, mob)
            chk("[%s] 「✏ 고치기」 단추 있음" % tag, pg.is_visible("#btnKle") and "고치기" in pg.inner_text("#btnKle"))
            g0 = pg.evaluate(DOC_GEO)
            if tag == "pc":
                pg.screenshot(path=os.path.join(SHOTS, "doc_before.png"))
            pg.click("#btnKle")
            pg.wait_for_timeout(250)
            g1 = pg.evaluate(DOC_GEO)
            chk("[%s] 누르면 단추 「✔ 수정 완료」 · 안내 바뀜" % tag, "수정 완료" in pg.inner_text("#btnKle") and "고치는 중" in pg.inner_text("#kleDocHint"))
            lim = 0 if tag == "pc" else 20
            chk("[%s] 양식 위치·높이 그대로(차이 ≤ %d)" % (tag, lim), abs(g1["top"] - g0["top"]) <= lim and g1["h"] == g0["h"], (g0, g1))
            chk("[%s] 고칠 칸마다 점선" % tag, pg.evaluate("""() => { const a = Array.from(document.querySelectorAll('.sheet .body [data-kle-on]'));
                return a.length >= 12 && a.every(e => getComputedStyle(e).outlineStyle === 'dashed'); }"""))
            if tag == "phone":
                pg.screenshot(path=os.path.join(SHOTS, "doc_phone_mode.png"))
                ctx.close()
                continue
            pg.screenshot(path=os.path.join(SHOTS, "doc_mode.png"))
            pg.click("#btnKle")
            pg.wait_for_timeout(200)
            chk("[pc] 다시 누르면 끝 · 점선 없음 · 「✏ 고치기」", "고치기" in pg.inner_text("#btnKle") and pg.evaluate("""() =>
                Array.from(document.querySelectorAll('.sheet .body [data-kle-on]')).every(e => getComputedStyle(e).outlineStyle !== 'dashed')"""))
            dsel = '.sheet .body [data-kle="6"]'
            pg.click(dsel)
            pg.wait_for_timeout(200)
            chk("[pc] 누르기 전엔 양식 글을 눌러도 안 고쳐진다", not editing(pg, dsel))
            # 정리 줄: Enter 없이 「✔ 수정 완료」
            pg.click("#btnKle")
            pg.click(dsel)
            select_char(pg, dsel, "강")
            pg.keyboard.type("감")
            pg.wait_for_timeout(150)
            pg.click("#btnKle")
            pg.wait_for_timeout(1500)
            chk("[pc] 양식 정리 줄 — Enter 없이 「✔ 수정 완료」 = 저장", "- 감 팀장이 업체에" in summ(M1), summ(M1)[:200])
            chk("[pc] 수정 완료 = 모드 끝", "고치기" in pg.inner_text("#btnKle") and not pg.evaluate("() => document.querySelector('.sheet .body').hasAttribute('data-kle-mode')"))
            # 표 칸: Enter 저장 → 모드 유지 → 수정 완료
            csel = '[data-klec="dec:%d:what"]' % D2
            pg.click("#btnKle")
            pg.click(csel)
            pg.keyboard.press("End")
            pg.keyboard.type("(확인)")
            pg.keyboard.press("Enter")
            pg.wait_for_selector(".kle-toast", timeout=8000)
            pg.wait_for_timeout(400)
            chk("[pc] 결정 표 칸 Enter 저장", q("SELECT what FROM meeting_decisions WHERE id=?", D2) == "자재 시트에 지급품 구분을 적는다(확인)",
                q("SELECT what FROM meeting_decisions WHERE id=?", D2))
            chk("[pc] Enter 뒤에도 모드 유지", "수정 완료" in pg.inner_text("#btnKle"))
            pg.click("#btnKle")
            pg.wait_for_timeout(300)
            # 이미지 저장을 모드 중에 누르면 점선이 그림에 안 들어가게 먼저 끝
            pg.click("#btnKle")
            pg.click("#btnImg")
            pg.wait_for_timeout(300)
            chk("[pc] 모드 중 「이미지 저장」 = 모드 먼저 끝(점선 없이)", not pg.evaluate("() => document.querySelector('.sheet .body').hasAttribute('data-kle-mode')"))
            pg.wait_for_timeout(2500)
            ctx.close()

        print("== 보기만 · 정리 없는 회의 ==")
        ctx, pg = page(b, MEM, "/meetings/%d/doc" % M1)
        chk("보기만 = 양식에 「✏ 고치기」 없음", pg.locator("#btnKle").count() == 0)
        ctx.close()
        ctx, pg = page(b, MEM, "/meetings/%d" % M1)
        chk("보기만 = 정리 화면 고치기 단추 없음", pg.locator("#btnSumEdit").count() == 0)
        ctx.close()
        ctx, pg = page(b, ME, "/meetings/%d" % M2)
        if pg.locator("#btnSumEdit").count() and pg.is_visible("#btnSumEdit"):
            pg.click("#btnSumEdit")
            pg.wait_for_timeout(200)
            chk("정리 없는 회의 = 예전 글 상자 그대로", pg.is_visible("#sumEdit"))
        else:
            chk("정리 없는 회의 = 고치기 단추 자체 없음(그대로)", True)
        ctx.close()
        b.close()
    chk("화면 스크립트 오류 0", not ERRS, ERRS[:3])
    print("결과: 통과 %d · 실패 %d" % (NP[0], NP[1]))
    sys.exit(1 if NP[1] else 0)


main()
