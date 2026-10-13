# -*- coding: utf-8 -*-
"""z1169 검사기 ② — 🔄 **다시 정리**를 진짜 브라우저로 눌러 끝까지 본다.

대표 신고 2026-10-13 「다시 정리 눌렀는데… **정리하지 못했습니다**」
  → 서버는 성공했는데 화면만 실패였다. 고친 뒤에는 **화면도 끝까지 따라가야** 한다.

재는 것 (가짜 AI 를 **느리게** 해 둔다 — 기본 6초)
  ① 누르면 **빨간 실패 글이 뜨지 않는다** (대표가 본 그 글이 다시 나오면 실패)
  ② 기다리는 동안 **「정리하는 중…」**이 보인다
  ③ 끝나면 **「정리가 끝났습니다 ✓」** + 정리 글이 **새것으로 바뀐다**
  ④ 📋 복사 단추가 **켜져 있다**(z1168)
  ⑤ 🔴 **반대 시험** — 옛 코드에서도 끝까지 되긴 한다(여기선 앞단이 없어 안 끊긴다).
     즉 이 시험이 지키는 것은 **「새 방식으로 바꿔도 화면이 여전히 끝까지 간다」**이다.
  ⑥ 콘솔 오류 0

쓰는 법: py vn_redo_ui.py <포트_base> <포트_new> [app_base·app_new 가 있는 폴더]
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
PB = int(sys.argv[1]) if len(sys.argv) > 1 else 8987
PN = int(sys.argv[2]) if len(sys.argv) > 2 else 8988
APPDIR = sys.argv[3] if len(sys.argv) > 3 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
RUN = os.path.join(HERE, "run_vn3_app.py")
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
            m = re.search(r"READY \d+ me (\d+) mine (\d+)", s)
            return pr, {"me": int(m.group(1)), "mine": int(m.group(2))}
        if pr.poll() is not None:
            print(s[-2500:])
            raise SystemExit("!! %s(%d) 가 떴다 죽었다" % (app, port))
    raise SystemExit("!! %s(%d) 가 안 떴다" % (app, port))


print("두 벌 띄우는 중… (가짜 AI %.0f초)" % SLOW)
pb, ib = boot("app_base", PB)
pn, inn = boot("app_new", PN)

try:
    with sync_playwright() as p:
        br = p.chromium.launch()
        for lab, port, info in (("운영 그대로", PB, ib), ("내 변경", PN, inn)):
            print("\n── 【%s】 🔄 다시 정리를 눌러 본다 ──" % lab)
            ctx = br.new_context(viewport={"width": 1280, "height": 900})
            ctx.add_cookies([{"name": "tuser", "value": str(info["me"]),
                              "url": "http://127.0.0.1:%d" % port}])
            errs = []
            pg = ctx.new_page()
            pg.on("console", lambda m: errs.append(m.text[:120]) if m.type == "error" else None)
            pg.add_init_script(
                "try{localStorage.setItem('knk_works_install_hint_never','1');}catch(e){}")
            pg.goto("http://127.0.0.1:%d/voice-notes/%d" % (port, info["mine"]),
                    wait_until="domcontentloaded")
            pg.wait_for_selector("#vnRedo", timeout=15000)
            before = (pg.inner_text("#vnSumBox") or "").strip()
            chk("%s · 누르기 전 정리는 옛것" % lab, "옛 정리" in before, before[:40])

            pg.click("#vnRedo")
            #  ② 기다리는 동안 「정리하는 중…」
            saw_wait = False
            for _ in range(20):
                pg.wait_for_timeout(300)
                if "정리하는 중" in (pg.inner_text("#vnSt") or ""):
                    saw_wait = True
                    break
            chk("%s · 기다리는 동안 「정리하는 중…」이 보인다" % lab, saw_wait,
                pg.inner_text("#vnSt"))

            #  ③ 끝날 때까지 (가짜 AI %.0f초 + 물어보는 사이) 최대 40초
            done, waited = False, 0.0
            for _ in range(80):
                pg.wait_for_timeout(500)
                waited += 0.5
                if "끝났습니다" in (pg.inner_text("#vnSt") or ""):
                    done = True
                    break
                if "못했습니다" in (pg.inner_text("#vnSt") or ""):
                    break
            msg = pg.inner_text("#vnSt") or ""
            chk("%s · 🔴 **빨간 실패 글이 안 뜬다**" % lab, "못했습니다" not in msg, msg[:70])
            chk("%s · 「정리가 끝났습니다 ✓」 (%.1f초 뒤)" % (lab, waited), done, msg[:70])
            after = (pg.inner_text("#vnSumBox") or "").strip()
            chk("%s · 정리 글이 **새것으로 바뀐다**" % lab, "가짜 정리" in after, after[:60])
            chk("%s · 옛 정리는 사라졌다" % lab, "옛 정리" not in after, after[:60])
            chk("%s · 📋 복사 단추가 켜져 있다" % lab, pg.locator("#vnCopy").is_enabled())
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
