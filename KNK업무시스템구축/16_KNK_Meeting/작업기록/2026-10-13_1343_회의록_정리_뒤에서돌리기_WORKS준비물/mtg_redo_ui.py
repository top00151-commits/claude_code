# -*- coding: utf-8 -*-
"""z1170 → **z1175** 검사기 — 🗓 회의록 「🔄 다시 정리」를 진짜 브라우저로 눌러 끝까지 본다.

z1170: 정리를 **뒤에서 돌린다**(앞단 60초에 안 끊기게).
z1175 (대표 2026-10-13 「회의록에는 다시 정리하기 기능이 없는데」
       → 「다시 정리 위치를 **위쪽에도 하나 더** 추가하자.. "고치기" **왼쪽 옆**에」):
  단추는 **있었지만** 접힌 「🔧 다시 하기 · 녹음 추가」 칸 안이라 아무도 못 찾았다.
  → 「📌 정리」 머리줄에 **하나 더** 놓는다(접힌 칸 것은 그대로).
  🔴 진행·결과 글도 같이 옮긴다 — `recSt()` 가 쓰던 두 자리는 ①접힌 칸 안 ②맨 위 올리기 칸인데
     ②는 녹음이 들어오면 감춰진다(`recUpHide`). **다시 정리할 때가 바로 그때**라 안 보였다.

재는 것 (가짜 AI 를 **느리게** 해 둔다 — 기본 6초)
  ① 🔴 반대 시험 — 운영 그대로엔 위 단추(`#btnExtractTop`)가 **없다**
  ② 위 단추가 **「✏ 고치기」 왼쪽**에 있다 (x 좌표로 잰다) · **안 펴도 바로 보인다**
  ③ 🔵 **위 단추로** 눌러 끝까지 — 빨간 실패 글 없음 · 요약이 새것으로 · 결정·할 일 그려짐
  ④ 🔵 **진행·결과 글이 위(`#sumSt2`)에 보인다** (아래 접힌 칸을 펴지 않고도)
  ⑤ 접힌 칸의 **옛 단추도 여전히** 된다 (양쪽이 같은 함수)
  ⑥ 🔴 사람이 손으로 적은 결정·할 일은 **그대로** · 콘솔 오류 0
  ⑦ 🔴 **못 고치는 사람에겐 위 단추가 안 보인다**

쓰는 법: py mtg_redo_ui.py <포트_base> <포트_new> [app_base·app_new 가 있는 폴더]
판정: **종료코드**(0=통과).
"""
import io
import os
import re
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
PB = int(sys.argv[1]) if len(sys.argv) > 1 else 8993
PN = int(sys.argv[2]) if len(sys.argv) > 2 else 8994
APPDIR = sys.argv[3] if len(sys.argv) > 3 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
RUN = os.path.join(HERE, "run_mtg3_app.py")
SLOW = 6.0
OK = FAIL = 0


def chk(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (name, detail))


def boot(app, port):
    lp = os.path.join(APPDIR, "srv_%d.log" % port)
    log = io.open(lp, "w", encoding="utf-8")
    pr = subprocess.Popen([P313, RUN, os.path.join(APPDIR, app), str(port), str(SLOW)],
                          stdout=log, stderr=subprocess.STDOUT, cwd=APPDIR)
    for _ in range(600):
        time.sleep(0.2)
        try:
            s = io.open(lp, encoding="utf-8").read()
        except Exception:
            s = ""
        if "READY" in s:
            m = re.search(r"READY \d+ me (\d+) other (\d+) mine (\d+) empty (\d+) notmine (\d+)", s)
            return pr, {"me": int(m.group(1)), "other": int(m.group(2)), "mine": int(m.group(3)),
                        "notmine": int(m.group(5))}
        if pr.poll() is not None:
            print(s[-2500:])
            raise SystemExit("!! %s(%d) 가 떴다 죽었다" % (app, port))
    raise SystemExit("!! %s(%d) 가 안 떴다" % (app, port))


#  recSt() 가 쓰는 칸들 — 위(z1175) · 접힌 칸 안
TOPST = "() => { var e = document.getElementById('sumSt2'); return e ? (e.textContent||'') : '(없음)'; }"
RECST = "() => { var e = document.getElementById('recStatus'); return e ? (e.textContent||'') : ''; }"


def page_for(br, port, uid):
    ctx = br.new_context(viewport={"width": 1280, "height": 1000})
    ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": "http://127.0.0.1:%d" % port}])
    pg = ctx.new_page()
    pg.add_init_script("try{localStorage.setItem('knk_works_install_hint_never','1');}catch(e){}")
    return ctx, pg


print("두 벌 띄우는 중… (가짜 AI %.0f초)" % SLOW)
pb, ib = boot("app_base", PB)
pn, inn = boot("app_new", PN)

try:
    with sync_playwright() as p:
        br = p.chromium.launch()

        # ── ① 🔴 반대 시험 ─────────────────────────────────────
        print("\n── ① 🔴 반대 시험: 운영 그대로엔 **위 단추가 없다** ──")
        cb, gb = page_for(br, PB, ib["me"])
        gb.goto("http://127.0.0.1:%d/meetings/%d" % (PB, ib["mine"]), wait_until="domcontentloaded")
        gb.wait_for_selector("#btnSumEdit", timeout=20000)
        chk("운영: 위 단추 0개", gb.locator("#btnExtractTop").count() == 0)
        chk("운영: 위 상태칸도 없다", gb.locator("#sumSt2").count() == 0)
        chk("운영: 접힌 칸 안의 단추는 있다(숨어 있을 뿐)",
            gb.locator("#btnExtract").count() == 1)
        cb.close()

        # ── ②③④⑥ 내 화면 — 위 단추로 끝까지 ───────────────────
        print("\n── ②③④ 내 화면: **「✏ 고치기」 왼쪽**에 있고, 안 펴도 눌러 끝까지 간다 ──")
        cn, gn = page_for(br, PN, inn["me"])
        errs = []
        gn.on("console", lambda m: errs.append(m.text[:140]) if m.type == "error" else None)
        gn.goto("http://127.0.0.1:%d/meetings/%d" % (PN, inn["mine"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#btnExtractTop", timeout=20000)
        chk("위 단추가 **안 펴도 보인다**", gn.locator("#btnExtractTop").is_visible())
        chk("접힌 「다시 하기」 칸은 **그대로 닫혀 있다**",
            gn.evaluate("() => { var d=document.getElementById('redoTools'); return d ? !d.open : null; }") is True)
        bt = gn.locator("#btnExtractTop").bounding_box()
        be = gn.locator("#btnSumEdit").bounding_box()
        bc = gn.locator("#btnCopySum").bounding_box()
        chk("🔵 **「✏ 고치기」 왼쪽**에 있다 (다시정리 x=%.0f < 고치기 x=%.0f)" % (bt["x"], be["x"]),
            bt["x"] < be["x"])
        chk("차례가 [다시 정리][고치기][복사] 다 (복사 x=%.0f)" % bc["x"], be["x"] < bc["x"])
        chk("같은 줄에 있다", abs(bt["y"] - be["y"]) < 6, "%.0f vs %.0f" % (bt["y"], be["y"]))
        chk("글자가 「다시 정리」다", "다시 정리" in (gn.inner_text("#btnExtractTop") or ""),
            gn.inner_text("#btnExtractTop"))
        before = (gn.inner_text("#mtgSummary") or "").strip()
        chk("누르기 전 요약은 옛것", "옛 정리" in before, before[:50])

        gn.click("#btnExtractTop")
        saw = False
        for _ in range(20):
            gn.wait_for_timeout(300)
            if "정리하는 중" in gn.evaluate(TOPST):
                saw = True
                break
        chk("🔵 **위 칸에** 「정리하는 중…」이 보인다", saw, gn.evaluate(TOPST)[:60])
        done, waited = False, 0.0
        for _ in range(120):
            gn.wait_for_timeout(500)
            waited += 0.5
            m = gn.evaluate(TOPST)
            if "완료" in m:
                done = True
                break
            if "실패" in m or "오래" in m:
                break
        msg = gn.evaluate(TOPST)
        chk("🔴 **빨간 실패 글이 안 뜬다**", "실패" not in msg, msg[:80])
        chk("🔵 **위 칸에** 「다시 정리 완료 ✓」 (%.1f초 뒤)" % waited, done, msg[:80])
        chk("접힌 칸 안에도 같은 글이 들어가 있다", "완료" in gn.evaluate(RECST),
            gn.evaluate(RECST)[:60])
        after = (gn.inner_text("#mtgSummary") or "").strip()
        chk("요약이 **새것으로 바뀐다**", "가짜 정리" in after, after[:60])
        chk("옛 요약은 사라졌다", "옛 정리" not in after, after[:60])
        whole = gn.inner_text("body")
        chk("AI 결정·할 일이 보인다", "가짜 결정" in whole and "가짜 할 일" in whole)
        chk("🔴 사람이 적은 결정·할 일이 **그대로** 보인다",
            "사람이 적은 결정" in whole and "사람이 적은 할 일" in whole)

        # ── ⑤ 접힌 칸의 옛 단추도 여전히 ───────────────────────
        print("\n── ⑤ 접힌 칸의 **옛 단추도 여전히** 된다 ──")
        gn.evaluate("() => { var d=document.getElementById('redoTools'); if(d) d.open=true; }")
        gn.wait_for_selector("#btnExtract", state="visible", timeout=20000)
        chk("옛 단추를 누를 수 있다", gn.locator("#btnExtract").is_enabled())
        gn.click("#btnExtract")
        done2, w2 = False, 0.0
        for _ in range(120):
            gn.wait_for_timeout(500)
            w2 += 0.5
            if "완료" in gn.evaluate(TOPST):
                done2 = True
                break
            if "실패" in gn.evaluate(TOPST):
                break
        chk("옛 단추로도 끝까지 간다 (%.1f초)" % w2, done2, gn.evaluate(TOPST)[:60])
        chk("콘솔 오류 0", not errs, errs[:2])
        cn.close()

        # ── ⑦ 못 고치는 사람 ───────────────────────────────────
        print("\n── ⑦ 🔴 못 고치는 사람에겐 **위 단추가 안 보인다** ──")
        co, go = page_for(br, PN, inn["other"])
        go.goto("http://127.0.0.1:%d/meetings/%d" % (PN, inn["mine"]), wait_until="domcontentloaded")
        go.wait_for_selector("#mtgSummary", timeout=20000)
        chk("위 단추 0개", go.locator("#btnExtractTop").count() == 0)
        chk("「✏ 고치기」도 0개(지금과 같다)", go.locator("#btnSumEdit").count() == 0)
        chk("🔵 「📋 복사」는 그대로 있다", go.locator("#btnCopySum").count() == 1)
        co.close()
        br.close()
finally:
    for pr in (pb, pn):
        try:
            pr.terminate()
        except Exception:
            pass

print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
