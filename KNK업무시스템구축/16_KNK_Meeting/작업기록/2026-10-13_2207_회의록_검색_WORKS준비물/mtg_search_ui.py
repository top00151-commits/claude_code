# -*- coding: utf-8 -*-
"""z1178 검사기 — 🔍 회의록 검색.

대표 지시 2026-10-13: 「회의록 검색 기능을 넣었으면 좋겠어.. 검색에는 제목,내용,참여자,고객사등 내용으로 검색할수있게.」
대표 확인: 이해 보고(7가지) → 「진행해」

재는 것 (앱 두 벌 — 운영 그대로(z1177) / 고친 것)
  ① 🔴 반대 시험 — 운영엔 검색 칸 **없음** · 검색 주소는 404
  ② 🔴 목록은 **그대로** — 나·남·대표 셋 다 운영과 **같은 회의가 같은 차례로**(목록 질의를 함수로 떼어냈다)
  ③ 칸마다 찾는다 — 제목·원문(3만 자 뒤)·정리·참석자(적은 글·명단)·작성자·결정·할 일·장소 · 찾은 칸 이름 · 앞뒤 한 줄
  ④ 🔴 **공개 범위** — 남의 비공개·다른 팀 회의의 「삼성전기」는 나에겐 **안 나온다** · 남·대표에겐 그들 목록대로
       · 검색 결과는 늘 **그 사람 목록의 부분집합**
  ⑤ 낱말 여러 개 = 모두 들어간 회의만 · 대소문자 상관없음(LG/lg) · 🔴 % 와 _ 는 글자 그대로
  ⑥ 로그인 안 한 사람은 401
  ⑦ 브라우저 — 칸이 맨 위 · 🔴 누르기 전엔 읽기 전용(크롬 자동 채우기 막기 · z1173) · 치면 걸러짐 · 건수 ·
       제목 노랗게 · 찾은 곳 한 줄 · 숫자 칸 숨김 · ✕ 로 원래대로 · 없으면 「찾는 회의가 없습니다」 · Esc
  ⑧ 주소에 검색어 — 새로고침·「뒤로」(WORKS 본문 갈아끼우기)에도 그대로
  ⑨ 베트남어 화면 · 📱 375 폭 · 콘솔 오류 0 · 사진

쓰는 법: py mtg_search_ui.py [app_base·app_new 가 있는 폴더]
판정: **종료코드**(0=통과) + 요약 줄.
"""
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1] if len(sys.argv) > 1 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
RUN = os.path.join(HERE, "run_mtgq_app.py")
PB, PN = 8901, 8902
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
            return
        time.sleep(0.2)
    raise SystemExit("!! 포트 %d 를 비우지 못했다" % port)


def boot(app, port):
    freeport(port)
    sp = os.path.join(HERE, "seed_%d.json" % port)
    if os.path.exists(sp):
        os.remove(sp)
    lp = os.path.join(APPDIR, "srvq_%d.log" % port)
    pr = subprocess.Popen([P313, RUN, os.path.join(APPDIR, app), str(port)],
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


def get(port, path, uid):
    rq = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), headers={"Cookie": "tuser=%d" % uid})
    try:
        with urllib.request.urlopen(rq, timeout=30) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def list_ids(port, uid):
    code, html = get(port, "/meetings", uid)
    return code, [int(x) for x in re.findall(r'<a class="mtg-card" href="/meetings/(\d+)"', html)]


def search(port, uid, q):
    t0 = time.time()
    code, body = get(port, "/api/meetings/search?q=" + urllib.parse.quote(q), uid)
    dt = time.time() - t0
    try:
        j = json.loads(body)
    except Exception:
        j = {}
    return code, j, dt


def kill(*prs):
    for pr in prs:
        try:
            pr.terminate()
        except Exception:
            pass


pb = pn = None
try:
    print("두 벌 띄우는 중…")
    pb, sb = boot("app_base", PB)
    pn, sn = boot("app_new", PN)
    S = sn
    name = {S[k]: k for k in S if k.startswith("M")}

    print("\n── ① 🔴 반대 시험: 운영 그대로 ──")
    code, html = get(PB, "/meetings", sb["me"])
    chk("운영 목록 200", code == 200, code)
    chk("운영엔 검색 칸 **없음**", 'id="mqInput"' not in html)
    code, _ = get(PB, "/api/meetings/search?q=%EC%82%BC%EC%84%B1", sb["me"])
    chk("운영엔 검색 주소가 **없다** (%d)" % code, code == 404, code)

    print("\n── ② 🔴 목록은 그대로 — 운영과 같은 회의가 같은 차례로 ──")
    for who in ("me", "other", "boss", "vnu"):
        cb, ib = list_ids(PB, sb[who])
        cn, inn = list_ids(PN, sn[who])
        chk("%-5s 목록 %d건 · 운영과 **같다**(차례까지)" % (who, len(inn)),
            cb == cn == 200 and [name.get(x) for x in inn] == [{sb[k]: k for k in sb if k.startswith("M")}.get(x) for x in ib]
            and len(inn) > 0, (ib, inn))
    _, my_list = list_ids(PN, sn["me"])
    chk("내 목록엔 남의 비공개(M9)·다른 팀(M14)이 **원래 없다**", S["M9"] not in my_list and S["M14"] not in my_list)

    print("\n── ③ 칸마다 찾는다 ──")
    CASES = [  # (낱말, 기대 회의, 그 회의에서 찾은 칸, 앞뒤 한 줄에 들어갈 글)
        ("삼성전기", ["M1"], "title", None),
        ("LG이노텍", ["M2", "M13"], None, None),
        ("드림텍", ["M3"], "summary", "드림텍"),
        ("한화솔루션", ["M4"], "att", "한화솔루션"),
        ("SKC", ["M5"], "dec", "SKC"),
        ("포스코", ["M6"], "act", "포스코"),
        ("판교", ["M7"], "loc", "판교"),
        ("박성수", ["M8"], "owner", None),
        ("김대표", ["M12"], "att", "김대표"),
    ]
    times = []
    for q, want, field, snip in CASES:
        code, j, dt = search(PN, sn["me"], q)
        times.append(dt)
        got = sorted(name.get(it["id"], "?") for it in j.get("items", []))
        chk("「%s」 → %s" % (q, ", ".join(got) or "없음"), code == 200 and got == sorted(want), (code, got, want))
        if field:
            it = [x for x in j.get("items", []) if x["id"] == S[want[0]]]
            chk("   찾은 칸에 「%s」" % field, bool(it) and field in it[0]["hits"], it)
            if snip:
                chk("   앞뒤 한 줄에 「%s」" % snip, bool(it) and snip.lower() in (it[0]["snip"] or "").lower(),
                    it and it[0]["snip"])
    code, j, _ = search(PN, sn["me"], "LG이노텍")
    m2 = [x for x in j.get("items", []) if x["id"] == S["M2"]]
    chk("🔵 원문 **3만 자 뒤**에 있어도 찾고, 그 자리 앞뒤를 보여 준다 「%s」" % (m2 and m2[0]["snip"][:40]),
        bool(m2) and "body" in m2[0]["hits"] and "LG이노텍" in m2[0]["snip"] and len(m2[0]["snip"]) < 140, m2)
    m13 = [x for x in j.get("items", []) if x["id"] == S["M13"]]
    chk("제목에서만 찾은 회의는 「제목」 · 한 줄 없음(제목이 이미 보인다)",
        bool(m13) and m13[0]["hits"] == ["title"] and m13[0]["snip"] == "", m13)
    chk("빠르다 — 가장 느린 검색 %.0fms (3만 자 원문 포함)" % (max(times) * 1000), max(times) < 1.0, times)

    print("\n── ④ 🔴 공개 범위 ──")
    for who, want in (("me", ["M1"]), ("other", ["M14", "M9"]), ("boss", ["M1", "M14", "M9"])):
        code, j, _ = search(PN, sn[who], "삼성전기")
        got = sorted(name.get(it["id"], "?") for it in j.get("items", []))
        chk("%-5s 「삼성전기」 → %s" % (who, ", ".join(got)), got == sorted(want), (got, want))
    for who in ("me", "other", "boss", "vnu"):
        _, lst = list_ids(PN, sn[who])
        sub = True
        for q in ("삼성전기", "회의", "김한국", "기술영업팀", "%", "_", "LG이노텍"):
            _, j, _ = search(PN, sn[who], q)
            if not {it["id"] for it in j.get("items", [])} <= set(lst):
                sub = False
        chk("%-5s 검색 결과는 늘 **내 목록의 부분집합**(낱말 7개)" % who, sub)
    code, j, _ = search(PN, sn["me"], "기술영업팀")
    A_TEAM = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M10", "M11", "M12", "M13"]
    chk("팀 이름으로 — A팀 회의 11건 전부(%d건)" % len(j.get("items", [])),
        sorted(name.get(it["id"], "?") for it in j.get("items", [])) == sorted(A_TEAM),
        [name.get(it["id"]) for it in j.get("items", [])])

    print("\n── ⑤ 낱말 여러 개 · 대소문자 · % _ ──")
    for q, want in (("삼성 출하", ["M1"]), ("삼성 드림텍", []), ("lg이노텍", ["M2", "M13"]), ("skc", ["M5"]),
                    ("100%", ["M10"]), ("%", ["M10"]), ("_", ["M1", "M11"]), ("A_B", ["M11"]),
                    ("  삼성전기   출하검사기  ", ["M1"])):
        code, j, _ = search(PN, sn["me"], q)
        got = sorted(name.get(it["id"], "?") for it in j.get("items", []))
        chk("「%s」 → %s" % (q.strip(), ", ".join(got) or "없음"), code == 200 and got == sorted(want), (got, want))
    code, j, _ = search(PN, sn["me"], "")
    chk("빈 검색어 → 빈 결과(화면이 전체를 보여 준다)", code == 200 and j.get("items") == [], j)
    code, j, _ = search(PN, sn["me"], " ".join("낱말%d" % i for i in range(20)))
    chk("낱말이 많아도 8개까지만 본다", code == 200 and len(j.get("terms", [])) == 8, j.get("terms"))

    print("\n── ⑥ 로그인 안 한 사람 ──")
    code, _ = get(PN, "/api/meetings/search?q=%EC%82%BC%EC%84%B1", 999999)
    chk("없는 사람으로 물으면 401 (%d)" % code, code == 401, code)

    with sync_playwright() as p:
        br = p.chromium.launch()

        def page_for(uid, w=1280, h=900, mobile=False):
            ctx = br.new_context(viewport={"width": w, "height": h}, is_mobile=mobile, has_touch=mobile)
            ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": "http://127.0.0.1:%d" % PN}])
            pg = ctx.new_page()
            pg.add_init_script("try{localStorage.setItem('knk_works_install_hint_never','1');}catch(e){}")
            errs = []
            pg.on("console", lambda m: errs.append("console: " + m.text[:160]) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:160]))
            return ctx, pg, errs

        VIS = "() => Array.prototype.filter.call(document.querySelectorAll('.mtg-row'), function(r){ return !r.hidden; }).map(function(r){ var a=r.querySelector('a.mtg-card'); return +(/\\/meetings\\/(\\d+)/.exec(a.getAttribute('href'))[1]); })"

        def wait_cnt(pg, want_sub, sec=6):
            t0 = time.time()
            while time.time() - t0 < sec:
                t = pg.inner_text("#mqCnt")
                if want_sub in t:
                    return t
                pg.wait_for_timeout(100)
            return pg.inner_text("#mqCnt")

        print("\n── ⑦ 브라우저 — 내 화면 ──")
        ctx, pg, errs = page_for(sn["me"])
        pg.goto("http://127.0.0.1:%d/meetings" % PN, wait_until="domcontentloaded")
        pg.wait_for_selector("#mqInput", timeout=20000)
        bi, bb = pg.locator("#mqInput").bounding_box(), pg.locator(".bento").bounding_box()
        chk("검색 칸이 보인다 · 숫자 칸보다 **위**", pg.locator("#mqInput").is_visible() and bi["y"] < bb["y"], (bi, bb))
        chk("안내 글 「%s」" % pg.get_attribute("#mqInput", "placeholder"),
            pg.get_attribute("#mqInput", "placeholder") == "제목·내용·참석자·고객사로 찾기")
        chk("🔴 누르기 전엔 **읽기 전용**(크롬이 로그인 ID 를 못 채운다)", pg.evaluate("() => document.getElementById('mqInput').readOnly") is True)
        chk("시작할 땐 전체 %d건이 보인다" % len(pg.evaluate(VIS)), len(pg.evaluate(VIS)) == len(my_list))
        pg.click("#mqInput")
        chk("누르면 바로 쓸 수 있다", pg.evaluate("() => document.getElementById('mqInput').readOnly") is False)
        pg.type("#mqInput", "삼성 출하", delay=30)
        t = wait_cnt(pg, "1건")
        vis = pg.evaluate(VIS)
        chk("「삼성 출하」 → 「%s」 · 남은 줄 %s" % (t, [name.get(x) for x in vis]), "검색 결과 1건" in t and vis == [S["M1"]], (t, vis))
        chk("제목이 노랗게(mark)", pg.locator(".mtg-row:not([hidden]) .mtg-ttl mark").count() >= 1)
        chk("찾은 칸 이름 「제목」", "제목" in pg.inner_text(".mtg-row:not([hidden]) .mq-hit"))
        chk("찾는 동안 전체 숫자 칸은 숨긴다", pg.evaluate("() => document.querySelector('.main .bento').hidden") is True)
        chk("주소에 검색어 「%s」" % urllib.parse.unquote(pg.url.split("?", 1)[-1]), "q=" in pg.url)
        pg.fill("#mqInput", "LG이노텍")
        t = wait_cnt(pg, "2건")
        vis = pg.evaluate(VIS)
        chk("「LG이노텍」 → 「%s」" % t, sorted(vis) == sorted([S["M2"], S["M13"]]), vis)
        row2 = pg.locator(".mtg-row:not([hidden])").filter(has=pg.locator('a[href="/meetings/%d"]' % S["M2"]))
        h2 = row2.locator(".mq-hit").inner_text()
        chk("원문에서 찾은 줄: 「원문」 + 앞뒤 한 줄 「%s」" % h2[:40], "원문" in h2 and "LG이노텍" in h2)
        chk("앞뒤 한 줄 안의 낱말도 노랗게", row2.locator(".mq-snip mark").count() >= 1)
        pg.locator("#secSummary, .mq-bar").first.screenshot(path=os.path.join(SHOTS, "q0_bar.png"))
        pg.screenshot(path=os.path.join(SHOTS, "q1_LG이노텍.png"))
        pg.fill("#mqInput", "삼성 드림텍")
        t = wait_cnt(pg, "0건")
        chk("없으면 「찾는 회의가 없습니다」 (%s)" % t, pg.locator("#mqNone").is_visible() and pg.evaluate(VIS) == [])
        pg.click("#mqClear")
        pg.wait_for_timeout(300)
        chk("✕ 누르면 원래대로 — 전체 %d건 · 숫자 칸 · 건수 지움" % len(pg.evaluate(VIS)),
            len(pg.evaluate(VIS)) == len(my_list) and pg.locator(".bento").is_visible()
            and pg.inner_text("#mqCnt").strip() == "" and pg.locator(".mq-hit").count() == 0)
        chk("✕ 뒤 주소에서 검색어가 빠진다", "q=" not in pg.url, pg.url)
        chk("제목의 노란 칠도 지워진다", pg.locator(".mtg-ttl mark").count() == 0)
        pg.fill("#mqInput", "판교")
        wait_cnt(pg, "1건")
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(300)
        chk("Esc 로도 지운다", pg.input_value("#mqInput") == "" and len(pg.evaluate(VIS)) == len(my_list))

        print("\n── ⑧ 주소에 검색어 — 새로고침 · 「뒤로」 ──")
        pg.goto("http://127.0.0.1:%d/meetings?q=%s" % (PN, urllib.parse.quote("드림텍")), wait_until="domcontentloaded")
        pg.wait_for_selector("#mqInput", timeout=20000)
        t = wait_cnt(pg, "1건")
        chk("주소로 열면 칸이 채워지고 바로 찾는다 「%s」" % t,
            pg.input_value("#mqInput") == "드림텍" and pg.evaluate(VIS) == [S["M3"]])
        chk("「정리」에서 찾았다", "정리" in pg.inner_text(".mtg-row:not([hidden]) .mq-hit"))
        pg.evaluate("() => { window.__spaMark = 1; }")
        pg.click('.mtg-row:not([hidden]) a.mtg-card')
        pg.wait_for_function("() => location.pathname === '/meetings/%d'" % S["M3"], timeout=20000)
        pg.wait_for_timeout(800)
        pg.go_back()
        pg.wait_for_function("() => location.pathname === '/meetings' && !!document.getElementById('mqInput')", timeout=20000)
        t = wait_cnt(pg, "1건")
        chk("회의를 열었다가 「뒤로」 → 검색 그대로 「%s」 (본문만 갈아끼우기: %s)"
            % (t, pg.evaluate("() => window.__spaMark === 1")),
            pg.input_value("#mqInput") == "드림텍" and pg.evaluate(VIS) == [S["M3"]])
        chk("🗓 회의록 화면 콘솔 오류 0", not errs, errs[:3])
        ctx.close()

        print("\n── ⑨ 남의 화면 · 베트남어 · 휴대폰 ──")
        ctx, pg, e2 = page_for(sn["other"])
        pg.goto("http://127.0.0.1:%d/meetings" % PN, wait_until="domcontentloaded")
        pg.wait_for_selector("#mqInput", timeout=20000)
        pg.click("#mqInput")
        pg.type("#mqInput", "삼성전기", delay=20)
        wait_cnt(pg, "2건")
        chk("남(B팀) 화면 「삼성전기」 → 자기 회의 둘(M9·M14)", sorted(pg.evaluate(VIS)) == sorted([S["M9"], S["M14"]]),
            [name.get(x) for x in pg.evaluate(VIS)])
        ctx.close()
        ctx, pg, e3 = page_for(sn["vnu"])
        pg.goto("http://127.0.0.1:%d/meetings" % PN, wait_until="domcontentloaded")
        pg.wait_for_selector("#mqInput", timeout=20000)
        ph = pg.get_attribute("#mqInput", "placeholder")
        chk("베트남어 안내 「%s」" % ph, ph.startswith("Tìm theo") and not re.search("[가-힣]", ph))
        pg.click("#mqInput")
        pg.type("#mqInput", "드림텍", delay=20)
        t = wait_cnt(pg, "Kết quả")
        hit = pg.inner_text(".mtg-row:not([hidden]) .mq-hit") if pg.evaluate(VIS) else ""
        chk("베트남어 건수 「%s」 · 칸 이름 「%s」" % (t, hit[:20]), "Kết quả: 1" in t and "Tóm tắt" in hit)
        ctx.close()
        ctx, pg, e4 = page_for(sn["me"], w=375, h=812, mobile=True)
        pg.goto("http://127.0.0.1:%d/meetings" % PN, wait_until="domcontentloaded")
        pg.wait_for_selector("#mqInput", timeout=20000)
        pg.tap("#mqInput")
        pg.type("#mqInput", "LG이노텍", delay=20)
        wait_cnt(pg, "2건")
        ow = pg.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]")
        bx = pg.locator("#mqInput").bounding_box()
        chk("📱 375 폭: 옆으로 안 밀린다 (%d · %d) · 칸이 화면 안" % tuple(ow),
            ow[0] <= ow[1] + 1 and bx["x"] >= 0 and bx["x"] + bx["width"] <= ow[1])
        chk("📱 손가락으로 눌러도 쓸 수 있다(읽기 전용 풀림) · 2건", pg.input_value("#mqInput") == "LG이노텍"
            and len(pg.evaluate(VIS)) == 2)
        pg.screenshot(path=os.path.join(SHOTS, "q2_휴대폰.png"))
        ctx.close()
        chk("남·베트남어·휴대폰 화면 콘솔 오류 0", not (e2 + e3 + e4), (e2 + e3 + e4)[:3])
        br.close()
finally:
    kill(pb, pn)

print("\n사진: %s" % SHOTS)
print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
