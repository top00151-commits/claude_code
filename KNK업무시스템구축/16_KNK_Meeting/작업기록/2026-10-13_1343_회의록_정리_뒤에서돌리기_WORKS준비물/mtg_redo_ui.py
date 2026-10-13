# -*- coding: utf-8 -*-
"""z1170 검사기 ② — 🗓 회의록 「🔄 다시 정리」를 진짜 브라우저로 눌러 끝까지 본다.

재는 것 (가짜 AI 를 **느리게** 해 둔다 — 기본 6초)
  ① 🔴 **빨간 실패 글이 안 뜬다**(「AI 정리 실패」가 다시 나오면 실패)
  ② 기다리는 동안 「…정리하는 중…」이 보인다
  ③ 끝나면 「다시 정리 완료 ✓」 + **요약 글이 새것으로 바뀐다**
  ④ 결정사항·할 일이 화면에 그려진다 · **사람이 적은 것도 그대로 남는다**
  ⑤ 콘솔 오류 0
  🔵 양쪽(운영 그대로·내 변경) 다 돌려 **바꿔도 화면이 여전히 끝까지 간다**를 지킨다.
     (여기엔 앞단이 없어 옛 코드도 끊기지 않는다 — 끊김 자체는 mtg_async_check 가 잰다)

🔴 단추는 접힌 「다시 하기」 칸(`#redoTools`) 안에 있다 — 먼저 펴야 누를 수 있다(z1165 교훈).

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
            m = re.search(r"READY \d+ me (\d+) other (\d+) mine (\d+)", s)
            return pr, {"me": int(m.group(1)), "mine": int(m.group(3))}
        if pr.poll() is not None:
            print(s[-2500:])
            raise SystemExit("!! %s(%d) 가 떴다 죽었다" % (app, port))
    raise SystemExit("!! %s(%d) 가 안 떴다" % (app, port))


#  recSt() 가 쓰는 그 칸을 똑같이 읽는다(이 화면엔 recStatus 가 둘 있어 첫째가 쓰인다)
RECST = "() => { var e = document.getElementById('recStatus'); return e ? (e.textContent||'') : ''; }"

print("두 벌 띄우는 중… (가짜 AI %.0f초)" % SLOW)
pb, ib = boot("app_base", PB)
pn, inn = boot("app_new", PN)

try:
    with sync_playwright() as p:
        br = p.chromium.launch()
        for lab, port, info in (("운영 그대로", PB, ib), ("내 변경", PN, inn)):
            print("\n── 【%s】 🔄 다시 정리를 눌러 본다 ──" % lab)
            ctx = br.new_context(viewport={"width": 1280, "height": 1000})
            ctx.add_cookies([{"name": "tuser", "value": str(info["me"]),
                              "url": "http://127.0.0.1:%d" % port}])
            errs = []
            pg = ctx.new_page()
            pg.on("console", lambda m: errs.append(m.text[:140]) if m.type == "error" else None)
            pg.add_init_script(
                "try{localStorage.setItem('knk_works_install_hint_never','1');}catch(e){}")
            pg.goto("http://127.0.0.1:%d/meetings/%d" % (port, info["mine"]),
                    wait_until="domcontentloaded")
            #  🔴 단추는 접힌 칸 안이라 **처음엔 안 보인다** — 먼저 칸을 펴고 나서 기다린다
            pg.wait_for_selector("#btnExtract", state="attached", timeout=20000)
            before = (pg.inner_text("#mtgSummary") or "").strip()
            chk("%s · 누르기 전 요약은 옛것" % lab, "옛 정리" in before, before[:50])

            pg.evaluate("() => { var d=document.getElementById('redoTools'); if(d) d.open=true; }")
            pg.wait_for_selector("#btnExtract", state="visible", timeout=20000)
            chk("%s · 「🔄 다시 정리」 단추를 누를 수 있다" % lab,
                pg.locator("#btnExtract").is_enabled())
            pg.click("#btnExtract")

            #  ② 기다리는 동안
            saw = False
            for _ in range(20):
                pg.wait_for_timeout(300)
                if "정리하는 중" in pg.evaluate(RECST):
                    saw = True
                    break
            chk("%s · 기다리는 동안 「정리하는 중…」이 보인다" % lab, saw, pg.evaluate(RECST)[:60])

            #  ③ 끝날 때까지 (최대 60초)
            done, waited = False, 0.0
            for _ in range(120):
                pg.wait_for_timeout(500)
                waited += 0.5
                msg = pg.evaluate(RECST)
                if "완료" in msg:
                    done = True
                    break
                if "실패" in msg or "오래" in msg:
                    break
            msg = pg.evaluate(RECST)
            chk("%s · 🔴 **빨간 실패 글이 안 뜬다**" % lab, "실패" not in msg, msg[:80])
            chk("%s · 「다시 정리 완료 ✓」 (%.1f초 뒤)" % (lab, waited), done, msg[:80])

            after = (pg.inner_text("#mtgSummary") or "").strip()
            chk("%s · 요약이 **새것으로 바뀐다**" % lab, "가짜 정리" in after, after[:60])
            chk("%s · 옛 요약은 사라졌다" % lab, "옛 정리" not in after, after[:60])

            #  ④ 결정·할 일 — AI 것과 사람이 적은 것이 **함께** 보인다
            whole = pg.inner_text("body")
            chk("%s · AI 결정이 보인다" % lab, "가짜 결정" in whole)
            chk("%s · AI 할 일이 보인다" % lab, "가짜 할 일" in whole)
            chk("%s · 🔴 사람이 적은 결정이 **그대로** 보인다" % lab, "사람이 적은 결정" in whole)
            chk("%s · 🔴 사람이 적은 할 일이 **그대로** 보인다" % lab, "사람이 적은 할 일" in whole)
            chk("%s · 콘솔 오류 0" % lab, not errs, errs[:2])
            ctx.close()
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
