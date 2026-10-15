# -*- coding: utf-8 -*-
"""z1182 검사기 — 회의록 목록: 아이콘을 눌렀을 때만 넘어간다 · 보기 전용 「🔍 회의상세(보기)」 · 회의록 상세: 화면 폭에 맞춤.
대표 2026-10-15 (사진 두 장)
  「회의목록에 "회의상세(수정), 회의록" 이 두 아이콘을 클릭했을때 다음으로 넘어가야하는데..
   지금은 제목있는 여백을 아무대나 눌러도 희의상세(수정) 눌렀을때 화면으로 넘어가...」
  「사진2는 모니터 크기에 맞게 여백이 자동으로 조정되게 해줘.. 지금 보면 오른쪽 여백이 너무 많아...」
  → 대표 확인: 보기 전용 = 「🔍 회의상세(보기)」로 켬

재는 것 (앱 두 벌 = 운영 그대로(app_base) · 새것(app_new) · 진짜 서버 · 진짜 브라우저)
  L① 🔴 반대 시험 — 운영: 제목·빈 곳을 누르면 상세로 넘어간다 · 줄이 뜬다 · 보기만 하는 사람은 ✏ 꺼짐뿐
  L② 새것: 제목·본문 빈 곳을 눌러도 **목록 그대로** · 손가락 모양 아님 · 줄이 안 뜬다
  L③ ✏ 회의상세(수정) → 상세 · 📄 회의록 → 양식 (아이콘은 그대로 넘어간다)
  L④ 🔍 검색은 그대로(data-mid 로 줄을 찾는다 · 찾은 줄 아래 한 줄)
  L⑤ 보기만 하는 사람: 「🔍 회의상세(보기)」 켜짐 · 누르면 **읽기 전용** 상세(입력 잠김 · 다시 정리·고치기 없음) · 꺼진 ✏ 없음 · 베트남어 글
  D① 🔴 반대 시험 — 운영 상세: 1920·2560 폭에서 내용 오른쪽이 머리줄보다 수백 px 모자란다(1200px 상한)
  D② 새것 상세: 내용 오른쪽 = 머리줄 오른쪽(꽉 참) · 정리 칸도 · 📱 375 옆으로 안 밀림
  콘솔 오류 0 · 📸 shots/
쓰는 법: py list82_ui.py <app_base·app_new 가 있는 폴더>
판정: **종료코드**(0=통과) + 요약 줄.
"""
import io
import json
import os
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1] if len(sys.argv) > 1 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
PB, PN = 8915, 8916
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
OK = FAIL = 0


def chk(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (name, detail))


def freeport(port):
    ps = ("Get-NetTCPConnection -State Listen -LocalPort %d -ErrorAction SilentlyContinue | "
          "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }") % port
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
    for _ in range(50):
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "@(Get-NetTCPConnection -State Listen -LocalPort %d -ErrorAction SilentlyContinue).Count" % port],
                           capture_output=True, text=True)
        if (r.stdout or "").strip() in ("0", ""):
            return True
        time.sleep(0.2)
    raise SystemExit("!! 포트 %d 를 비우지 못했다" % port)


def boot(app, port):
    freeport(port)
    sp = os.path.join(HERE, "seed_%d.json" % port)
    if os.path.exists(sp):
        os.remove(sp)
    lp = os.path.join(APPDIR, "srv_%d.log" % port)
    pr = subprocess.Popen([P313, os.path.join(HERE, "run_list82_app.py"), os.path.join(APPDIR, app), str(port)],
                          stdout=io.open(lp, "w", encoding="utf-8"), stderr=subprocess.STDOUT, cwd=APPDIR)
    for _ in range(600):
        time.sleep(0.2)
        s = io.open(lp, encoding="utf-8").read() if os.path.exists(lp) else ""
        if "READY" in s and os.path.exists(sp):
            return pr, json.loads(io.open(sp, encoding="utf-8").read())
        if pr.poll() is not None:
            print(s[-2500:])
            raise SystemExit("!! %s(%d) 가 떴다 죽었다" % (app, port))
    raise SystemExit("!! %s(%d) 가 안 떴다" % (app, port))


def kill(*prs):
    for pr in prs:
        try:
            pr.terminate()
        except Exception:
            pass


U = lambda port, path: "http://127.0.0.1:%d%s" % (port, path)
#  🔵 운영에서도 나는 콘솔 오류 — 「📄 회의록」(따로 떨어진 양식 문서)으로 통째 이동할 때 공용 스타일(static/css/v5_main.css)의
#     「@view-transition { navigation: auto; }」 때문에 브라우저가 전환을 건너뛰며 남긴다(화면엔 안 보임 · 이번 변경 밖 · 기록에 남김).
#     L① 에서 운영도 같은 오류가 나는 것을 확인하고, 마지막 「콘솔 오류 0」은 이것만 빼고 본다.
KNOWN = "Transition was skipped"


def page_for(br, port, uid, w=1600, h=1000):
    ctx = br.new_context(viewport={"width": w, "height": h})
    ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": "http://127.0.0.1:%d" % port}])
    pg = ctx.new_page()
    pg.add_init_script("try{localStorage.setItem('knk_works_install_hint_never','1');}catch(e){}")
    pg.on("dialog", lambda d: d.accept())
    errs = []
    pg.on("console", lambda m: errs.append("console: " + m.text[:160]) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:160]))
    return ctx, pg, errs


def path_of(pg):
    return pg.evaluate("() => location.pathname")


def go_list(pg, port):
    pg.goto(U(port, "/meetings"), wait_until="domcontentloaded")
    pg.wait_for_selector(".mtg-row", timeout=20000)


def row(pg, title):
    return pg.locator(".mtg-row", has_text=title).first


WIDTH = """() => { var w = document.querySelector('.mf-wrap'), h = document.querySelector('.page-head'),
  s = document.getElementById('secSummary');
  var r = w.getBoundingClientRect(), hr = h.getBoundingClientRect(), sr = s ? s.getBoundingClientRect() : null;
  return { wrap: Math.round(r.right), head: Math.round(hr.right), sum: sr ? Math.round(sr.right) : -1,
           wrapw: Math.round(r.width), iw: window.innerWidth, sw: document.documentElement.scrollWidth }; }"""

pb = pn = None
try:
    pb, sb = boot("app_base", PB)
    pn, sn = boot("app_new", PN)
    print("서버 둘 READY — 운영 그대로 %d · 새것 %d" % (PB, PN))
    with sync_playwright() as p:
        br = p.chromium.launch()

        print("\n── L① 🔴 반대 시험(운영 그대로) ──")
        cb, gb, eb = page_for(br, PB, sb["me"])
        go_list(gb, PB)
        row(gb, "주간 회의").locator(".mtg-ttl").click()
        gb.wait_for_timeout(1200)
        chk("운영: 제목을 누르면 상세로 넘어간다(%s)" % path_of(gb), path_of(gb) == "/meetings/%d" % sb["ids"]["M2"], path_of(gb))
        go_list(gb, PB)
        cbox = row(gb, "주간 회의").locator(".mtg-card").bounding_box()
        row(gb, "주간 회의").locator(".mtg-card").click(position={"x": cbox["width"] - 12, "y": cbox["height"] - 6})
        gb.wait_for_timeout(1200)
        chk("운영: 본문 빈 곳을 눌러도 넘어간다(%s)" % path_of(gb), path_of(gb) == "/meetings/%d" % sb["ids"]["M2"], path_of(gb))
        go_list(gb, PB)
        row(gb, "주간 회의").hover(); gb.wait_for_timeout(400)
        tb = gb.evaluate("() => getComputedStyle(document.querySelector('.mtg-row')).transform")
        chk("운영: 마우스를 올리면 줄이 뜬다(transform %s)" % tb, tb not in ("none", ""), tb)
        row(gb, "주간 회의").locator('a.mtg-act[href="/meetings/%d/doc"]' % sb["ids"]["M2"]).click()
        gb.wait_for_timeout(2500)
        chk("(참고) 운영에서도 「📄 회의록」을 누르면 콘솔에 「%s」 — 공용 화면 전환 설정 · 이번 변경 밖" % KNOWN,
            any(KNOWN in e for e in eb), eb[:3])
        cvb, gvb, evb = page_for(br, PB, sb["viewer"])
        go_list(gvb, PB)
        chk("운영: 보기만 하는 사람은 ✏ 꺼짐 · 보기 아이콘 없음",
            gvb.locator(".mtg-act.off").count() >= 2 and gvb.locator("a.mtg-act.view").count() == 0)
        cvb.close()

        print("\n── L② 새것: 줄은 안 눌린다 ──")
        cn, gn, en = page_for(br, PN, sn["me"])
        go_list(gn, PN)
        tag = gn.evaluate("() => { var c = document.querySelector('.mtg-card'); return { tag: c.tagName, mid: c.getAttribute('data-mid'), href: c.getAttribute('href') }; }")
        chk("줄 본문은 링크가 아니다(%s · data-mid %s)" % (tag["tag"], tag["mid"]), tag["tag"] == "DIV" and tag["mid"] and not tag["href"], tag)
        row(gn, "주간 회의").locator(".mtg-ttl").click()
        gn.wait_for_timeout(1200)
        chk("🔴 제목을 눌러도 **목록 그대로**(%s)" % path_of(gn), path_of(gn) == "/meetings", path_of(gn))
        nbox = row(gn, "주간 회의").locator(".mtg-card").bounding_box()
        row(gn, "주간 회의").locator(".mtg-card").click(position={"x": nbox["width"] - 12, "y": nbox["height"] - 6})
        gn.wait_for_timeout(1200)
        chk("🔴 본문 빈 곳을 눌러도 **목록 그대로**(%s)" % path_of(gn), path_of(gn) == "/meetings", path_of(gn))
        row(gn, "주간 회의").locator(".mtg-meta").click()
        gn.wait_for_timeout(1000)
        chk("🔴 날짜·작성자 줄을 눌러도 **목록 그대로**", path_of(gn) == "/meetings", path_of(gn))
        cur = gn.evaluate("() => getComputedStyle(document.querySelector('.mtg-card')).cursor")
        chk("본문에 손가락 모양이 안 뜬다(cursor %s)" % cur, cur in ("default", "auto"), cur)
        row(gn, "주간 회의").hover(); gn.wait_for_timeout(400)
        tn = gn.evaluate("() => getComputedStyle(document.querySelector('.mtg-row')).transform")
        chk("마우스를 올려도 줄이 안 뜬다(transform %s)" % tn, tn in ("none", ""), tn)

        print("\n── L③ 아이콘은 그대로 넘어간다 ──")
        r2 = row(gn, "주간 회의")
        r2.locator('a.mtg-act[href="/meetings/%d"]' % sn["ids"]["M2"]).click()
        gn.wait_for_function("(p) => location.pathname === p", arg="/meetings/%d" % sn["ids"]["M2"], timeout=15000)
        gn.wait_for_timeout(900)    # 화면 전환이 끝날 때까지(사람 속도) — 바로 옮기면 공용 spa_nav 가 「Transition was skipped」
        chk("✏ 회의상세(수정) → 상세 화면", path_of(gn) == "/meetings/%d" % sn["ids"]["M2"])
        chk("  (고칠 수 있는 사람이라 입력 칸이 열려 있다)", gn.evaluate("() => !document.getElementById('mtgTitle').disabled"))
        go_list(gn, PN)
        row(gn, "주간 회의").locator('a.mtg-act[href="/meetings/%d/doc"]' % sn["ids"]["M2"]).click()
        gn.wait_for_function("(p) => location.pathname === p", arg="/meetings/%d/doc" % sn["ids"]["M2"], timeout=15000)
        gn.wait_for_timeout(900)
        chk("📄 회의록 → 회의록 양식", path_of(gn) == "/meetings/%d/doc" % sn["ids"]["M2"])
        go_list(gn, PN)
        chk("고칠 수 있는 사람에겐 ✏ 회의상세(수정) · 보기 아이콘 없음",
            gn.locator("a.mtg-act.view").count() == 0 and gn.locator('a.mtg-act[href="/meetings/%d"]' % sn["ids"]["M1"]).count() == 1)

        print("\n── L④ 🔍 검색 그대로 ──")
        gn.click("#mqInput")
        gn.fill("#mqInput", "주간")
        gn.wait_for_function("() => /검색 결과 \\d+건/.test(document.getElementById('mqCnt').textContent)", timeout=10000)
        vis = gn.evaluate("() => Array.from(document.querySelectorAll('.mtg-row')).filter(function(r){ return !r.hidden; }).map(function(r){ return +r.querySelector('.mtg-card').getAttribute('data-mid'); })")
        chk("「주간」 → 주간 회의 한 줄(data-mid 로 찾음)", vis == [sn["ids"]["M2"]], vis)
        chk("찾은 줄 본문 아래 「어디서 찾았나」 한 줄", gn.locator(".mtg-row:not([hidden]) .mtg-card .mq-hit").count() == 1)
        gn.screenshot(path=os.path.join(SHOTS, "l4_list_search_new.png"), full_page=False)
        gn.fill("#mqInput", "")
        gn.wait_for_timeout(400)

        print("\n── L⑤ 보기만 하는 사람 ──")
        cv, gv, ev = page_for(br, PN, sn["viewer"])
        go_list(gv, PN)
        views = gv.evaluate("() => Array.from(document.querySelectorAll('a.mtg-act.view')).map(function(a){ return { href: a.getAttribute('href'), t: a.textContent.trim(), title: a.title }; })")
        chk("「🔍 회의상세(보기)」 두 줄 다 켜짐 %s" % [v["t"] for v in views],
            len(views) == 2 and all(v["t"] == "🔍회의상세(보기)" for v in views), views)
        chk("말풍선 「회의상세 보기 — 이 회의록은 보기만 됩니다…」", views and views[0]["title"].startswith("회의상세 보기 — 이 회의록은 보기만 됩니다"), views[:1])
        chk("꺼진 ✏ 는 없다(.mtg-act.off 0)", gv.locator(".mtg-act.off").count() == 0)
        gv.screenshot(path=os.path.join(SHOTS, "l5_list_viewer_new.png"), full_page=False)
        row(gv, "삼성 2호기 납기 협의").locator(".mtg-ttl").click()
        gv.wait_for_timeout(1000)
        chk("보기만 하는 사람도 줄을 눌러선 안 넘어간다", path_of(gv) == "/meetings", path_of(gv))
        row(gv, "삼성 2호기 납기 협의").locator("a.mtg-act.view").click()
        gv.wait_for_function("(p) => location.pathname === p", arg="/meetings/%d" % sn["ids"]["M1"], timeout=15000)
        gv.wait_for_timeout(900)
        ro = gv.evaluate("""() => ({ title: document.getElementById('mtgTitle').disabled, body: document.getElementById('mtgBody').disabled,
                                     redo: !!document.getElementById('btnExtractTop'), edit: !!document.getElementById('btnSumEdit') })""")
        chk("🔍 → **읽기 전용** 상세(제목·원문 잠김 · 다시 정리·고치기 없음) %s" % ro,
            ro["title"] and ro["body"] and not ro["redo"] and not ro["edit"], ro)
        cv.close()
        cvn, gvn, evn = page_for(br, PN, sn["vnu"])
        go_list(gvn, PN)
        vt = gvn.evaluate("() => { var a = document.querySelector('a.mtg-act.view'); return a ? a.textContent.trim() : ''; }")
        chk("베트남어 「%s」" % vt, vt == "🔍Chi tiết (xem)", vt)
        chk("보기 전용 화면들 콘솔 오류 0", not ev and not evn, (ev + evn)[:3])
        cvn.close()

        print("\n── D 회의록 상세 폭 ──")
        for w, h in ((1920, 1000), (2560, 1200)):
            for port, sd, tag2 in ((PB, sb, "운영"), (PN, sn, "새것")):
                c2, g2, e2 = page_for(br, port, sd["me"], w, h)
                g2.goto(U(port, "/meetings/%d" % sd["ids"]["M1"]), wait_until="domcontentloaded")
                g2.wait_for_selector(".mf-wrap", timeout=20000)
                g2.wait_for_timeout(500)
                m = g2.evaluate(WIDTH)
                gap = m["head"] - m["wrap"]
                if tag2 == "운영":
                    chk("🔴 반대 시험(%d폭): 운영 내용 오른쪽이 머리줄보다 %dpx 모자란다(폭 %d)" % (w, gap, m["wrapw"]), gap >= 200, m)
                else:
                    chk("%d폭: 새것 내용 오른쪽 = 머리줄 오른쪽(차이 %dpx · 폭 %d)" % (w, gap, m["wrapw"]), abs(gap) <= 2, m)
                    chk("%d폭: 정리 칸도 꽉 찬다(머리줄과 차이 %dpx)" % (w, m["head"] - m["sum"]), abs(m["head"] - m["sum"]) <= 2, m)
                    chk("%d폭: 옆으로 안 밀린다(scroll %d ≤ %d)" % (w, m["sw"], m["iw"]), m["sw"] <= m["iw"], m)
                    if w == 1920:
                        g2.screenshot(path=os.path.join(SHOTS, "d_detail_1920_new.png"), full_page=False)
                    chk("%d폭 새것 콘솔 오류 0" % w, not e2, e2[:3])
                if tag2 == "운영" and w == 1920:
                    g2.screenshot(path=os.path.join(SHOTS, "d_detail_1920_base.png"), full_page=False)
                c2.close()
        cm, gm, em = page_for(br, PN, sn["me"], 375, 812)
        gm.goto(U(PN, "/meetings/%d" % sn["ids"]["M1"]), wait_until="domcontentloaded")
        gm.wait_for_selector(".mf-wrap", timeout=20000)
        gm.wait_for_timeout(500)
        mm = gm.evaluate(WIDTH)
        chk("📱 375: 상세 화면 옆으로 안 밀린다(scroll %d ≤ %d)" % (mm["sw"], mm["iw"]), mm["sw"] <= mm["iw"], mm)
        go_list(gm, PN)
        hs = gm.evaluate("() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth })")
        chk("📱 375: 목록도 옆으로 안 밀린다 %s" % hs, hs["sw"] <= hs["iw"], hs)
        chk("📱 콘솔 오류 0", not em, em[:3])
        cm.close()
        other = [e for e in en if KNOWN not in e]
        chk("새것 목록·상세 콘솔 오류 0 (운영에서도 나는 「%s」 %d건은 빼고)" % (KNOWN, len(en) - len(other)), not other, other[:3])
        print("   (참고) 운영 화면 콘솔 오류: %s" % (eb[:3] or "없음"))
        br.close()
finally:
    kill(pb, pn)

print("\n사진: %s" % SHOTS)
print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
