# -*- coding: utf-8 -*-
"""z1207 검사 — 회의록 양식 화면 「🔗 링크 복사」 (대표 2026-11-09)
운영 그대로(app_base)와 새것(app_new)을 나란히 띄워 본다.
  ① 파일: 바뀐 파일 = meeting_doc.html · i18n.py 둘 · 서버(main.py) 안 건드림
  ② 단추: 한국어 「🔗 링크 복사」 · 베트남어 「🔗 Sao chép liên kết」 · 보기만 하는 직원에게도 · 인쇄엔 안 나옴
  ③ 복사: 클립보드에 /meetings/<번호>/doc(꼬리 ?orig=1 뺌) · 클립보드 막히면 옛 복사 · 그것도 막히면 주소 칸
  ④ 🔒 링크로 열기: 로그인 안 됨 → 로그인(이음)으로 · 내용 0 · 로그인 주소에 「돌아올 곳」 = 그 회의록
       · 다른 팀 직원(팀 공개) → 회의록 목록으로 · 비공개 회의 → 참석 안 한 같은 팀 직원도 못 봄 · 참석자는 봄
       · 링크에 열쇠·토큰 없음(주소 = 번호뿐)
  ⑤ 단추 말고 화면 HTML 차이 = 정해진 것뿐 · 단추 줄 한 줄(PC) · 휴대폰 가로 넘침 없음 · 오류 0 · 사진(shots/)
쓰는 법: py -3.12 q207_check.py <app_base·app_new 가 있는 폴더>   🔒 시험 글은 모두 지어낸 것.
"""
import difflib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1]
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
RUN = os.path.join(HERE, "run_q207_app.py")
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
PORTS = {"app_base": 8994, "app_new": 8995}
N = OK = 0
FAILS = []
ERRS = []
NOHINT = "addEventListener('DOMContentLoaded',function(){var s=document.createElement('style');s.textContent='#worksInstallHint{display:none!important}';document.head.appendChild(s);});"


def chk(name, cond, extra=""):
    global N, OK
    N += 1
    if cond:
        OK += 1
        print("  ✅", name, extra)
    else:
        FAILS.append(name)
        print("  ❌", name, extra)


def start(app):
    port = PORTS[app]
    lp = os.path.join(APPDIR, "srv07_%d.log" % port)
    pr = subprocess.Popen([P313, RUN, os.path.join(APPDIR, app), str(port)], stdout=io.open(lp, "w", encoding="utf-8"),
                          stderr=subprocess.STDOUT, cwd=APPDIR)
    for _ in range(120):
        time.sleep(1)
        txt = io.open(lp, encoding="utf-8", errors="replace").read()
        if any(ln.startswith("READY") for ln in txt.splitlines()):
            return pr
        if pr.poll() is not None:
            break
    print("⛔ %s 서버가 안 떴다 — %s" % (app, lp))
    print(io.open(lp, encoding="utf-8", errors="replace").read()[-1500:])
    sys.exit(2)


def walk(app):
    root = os.path.join(APPDIR, app, "app")
    out = {}
    for d, _x, files in os.walk(root):
        if "__pycache__" in d:
            continue
        for f in files:
            if not f.endswith(".pyc"):
                full = os.path.join(d, f)
                out[os.path.relpath(full, root).replace("\\", "/")] = hashlib.md5(io.open(full, "rb").read()).hexdigest()
    return out


def diff(a, b):
    return [d for d in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0) if d[:1] in "+-" and not d.startswith(("+++", "---"))]


class NoRedir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


OPENER = urllib.request.build_opener(NoRedir)


def get(port, path, uid=None):
    """돌려 보내기를 따라가지 않고 그대로 받는다 → (상태, 가는 곳, 본문)"""
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path))
    if uid is not None:
        req.add_header("Cookie", "tuser=%s" % uid)
    try:
        with OPENER.open(req, timeout=30) as r:
            return r.status, r.headers.get("Location", ""), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location", ""), e.read().decode("utf-8", "replace")


def norm(h):
    h = re.sub(r"\?v=[0-9A-Za-z_.-]+", "?v=X", h)
    h = re.sub(r'var LOADED = "[^"]*"', 'var LOADED = "X"', h)
    h = re.sub(r'"_ts": ?"[^"]*"|data-ts="[^"]*"', "TS", h)
    h = re.sub(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?", "T", h)   # 서버를 띄운 시각(시험 자료 만든 때)
    return h


print("== ① 파일 ==")
WB, WN = walk("app_base"), walk("app_new")
changed = sorted(k for k in set(WB) | set(WN) if WB.get(k) != WN.get(k))
chk("바뀐 파일 = 회의록 양식 화면 · 글자 사전 둘", changed == ["i18n.py", "templates/meeting_doc.html"], str(changed))
chk("서버(main.py) 안 건드림", "main.py" not in changed)
d1 = diff(io.open(os.path.join(APPDIR, "app_base", "app", "i18n.py"), encoding="utf-8").read(),
          io.open(os.path.join(APPDIR, "app_new", "app", "i18n.py"), encoding="utf-8").read())
chk("사전 = 더하기만 6줄(빼는 줄 0)", len(d1) == 6 and all(x.startswith("+") for x in d1), str(len(d1)))
d2 = diff(io.open(os.path.join(APPDIR, "app_base", "app", "templates", "meeting_doc.html"), encoding="utf-8").read(),
          io.open(os.path.join(APPDIR, "app_new", "app", "templates", "meeting_doc.html"), encoding="utf-8").read())
chk("양식 화면 = 더하기만(빼는 줄 0)", d2 and all(x.startswith("+") for x in d2), "더한 %d" % len(d2))

PRS = {}
try:
    for app in ("app_base", "app_new"):
        PRS[app] = start(app)
    PB, PN = PORTS["app_base"], PORTS["app_new"]
    SB = json.load(io.open(os.path.join(HERE, "seed_%d.json" % PB), encoding="utf-8"))
    S = json.load(io.open(os.path.join(HERE, "seed_%d.json" % PN), encoding="utf-8"))
    IB, I = SB["ids"], S["ids"]

    print("== ⑤ 화면 HTML(서버) — 단추 말고 같은가 ==")
    for who, key in (("대표(고칠 수 있음)", "me"), ("같은 팀 직원(보기만)", "mem"), ("베트남어 직원", "vi")):
        _, _, hb = get(PB, "/meetings/%d/doc" % IB["M1"], SB[key])
        _, _, hn = get(PN, "/meetings/%d/doc" % I["M1"], S[key])
        dd = diff(norm(hb), norm(hn))
        rem = [x for x in dd if x.startswith("-")]
        btn = [x for x in dd if 'id="btnLink"' in x]
        chk("%s: 빼는 줄 0 · 단추 1줄 더함" % who, rem == [] and len(btn) == 1, str(rem[:2]))
        lab = "🔗 Sao chép liên kết" if key == "vi" else "🔗 링크 복사"
        chk("%s: 단추 글 「%s」" % (who, lab), ('>%s</button>' % lab) in hn)
    _, _, mb = get(PB, "/meetings/%d" % IB["M1"], SB["me"])
    _, _, mn = get(PN, "/meetings/%d" % I["M1"], S["me"])
    chk("회의록 상세 화면 = 같은 HTML", diff(norm(mb), norm(mn)) == [], str(diff(norm(mb), norm(mn))[:2]))

    _tb = io.open(os.path.join(APPDIR, "app_new", "app", "i18n.py"), encoding="utf-8").read()
    chk("사전 이름이 겹치지 않음(옛 md_link 「연결」 그대로 · 새 이름 한 번씩)",
        _tb.count('"md_link": {"ko": "연결"') == 1 and all(_tb.count('"%s":' % k) == 1 for k in ("md_copylink", "md_copylink_ok", "md_copylink_manual")))
    print("== ④ 🔒 링크로 열기 ==")
    link_path = "/meetings/%d/doc" % I["M1"]
    st, loc, body = get(PN, link_path, None)
    chk("로그인 안 됨 → 로그인으로 돌려 보냄(303)", st in (302, 303, 307) and loc.startswith("/login?next="), "%s %s" % (st, loc))
    chk("로그인 안 됨 → 회의 내용 0", "자재 입고" not in body and "감 팀장" not in body and len(body) < 400, "본문 %d자" % len(body))
    chk("「돌아올 곳」 = 그 회의록 양식", urllib.parse.unquote(loc.split("next=", 1)[-1]) == link_path, loc)
    st2, loc2, _ = get(PN, loc, None)
    chk("/login → 이음 로그인 주소로(돌아올 곳 들고)", st2 in (302, 303, 307) and "sso" in loc2.lower() and urllib.parse.quote(urllib.parse.quote(link_path, safe=""), safe="") in loc2,
        loc2[:160])
    st3, loc3, b3 = get(PN, link_path, S["other"])
    chk("다른 팀 직원(팀 공개 회의) → 목록으로 · 내용 0", st3 in (302, 303) and loc3 == "/meetings" and "자재 입고" not in b3, "%s %s" % (st3, loc3))
    st4, _, b4 = get(PN, link_path, S["mem"])
    chk("같은 팀 직원 → 열림", st4 == 200 and "자재 입고" in b4)
    p3 = "/meetings/%d/doc" % I["M3"]
    st5, loc5, b5 = get(PN, p3, S["mem"])
    chk("비공개 회의 → 참석 안 한 같은 팀 직원 못 봄", st5 in (302, 303) and loc5 == "/meetings" and "KX7Q" not in b5, "%s %s" % (st5, loc5))
    st6, _, b6 = get(PN, p3, S["att"])
    chk("비공개 회의 → 참석자는 열림", st6 == 200 and "KX7Q" in b6)
    st7, loc7, b7 = get(PN, p3, None)
    chk("비공개 회의 · 로그인 안 됨 → 로그인으로 · 내용 0", st7 in (302, 303) and loc7.startswith("/login?next=") and "KX7Q" not in b7)
    for pth in ("/meetings/%d" % I["M1"], "/meetings/%d/viz" % I["M1"], "/meetings", "/home"):
        s8, l8, _ = get(PN, pth, None)
        chk("로그인 안 됨 → 다른 화면도 못 봄 %s" % pth, s8 in (302, 303, 307) and "/login" in l8, "%s %s" % (s8, l8[:60]))

    from playwright.sync_api import sync_playwright   # noqa: E402

    print("== ②③ 눌러 보기 ==")
    with sync_playwright() as p:
        br = p.chromium.launch()

        def page(port, uid, w, h, clip=True):
            base = "http://127.0.0.1:%d" % port
            ctx = br.new_context(viewport={"width": w, "height": h}, device_scale_factor=(2 if w < 800 else 1), is_mobile=(w < 800), has_touch=(w < 800))
            if clip:
                ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=base)
            ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": base}])
            pg = ctx.new_page()
            pg.add_init_script(NOHINT)
            pg.on("pageerror", lambda e: ERRS.append("pageerror %s" % str(e)[:160]))
            pg.on("console", lambda m: ERRS.append("console %s" % m.text[:160]) if (m.type == "error" and "Failed to load resource" not in m.text) else None)
            return ctx, pg, base

        want = "http://127.0.0.1:%d/meetings/%d/doc" % (PN, I["M1"])
        # PC — 클립보드
        ctx, pg, base = page(PN, S["me"], 1665, 900)
        pg.goto(base + "/meetings/%d/doc" % I["M1"], wait_until="networkidle")
        tb = pg.evaluate("""() => { const t = document.querySelector('.toolbar'); const bs = [...t.querySelectorAll('.btn')];
            const tops = new Set(bs.map(b => Math.round(b.getBoundingClientRect().top))); return {n: bs.length, rows: tops.size,
            order: bs.map(b => b.id || b.textContent.trim().slice(0, 6))}; }""")
        chk("PC: 단추 줄 한 줄 · 순서(… 수정하기 · 링크 복사 · 이미지 · 인쇄)", tb["rows"] == 1 and tb["order"][-3:] == ["btnLink", "btnImg", tb["order"][-1]] and "btnKle" in tb["order"], str(tb))
        pg.screenshot(path=os.path.join(SHOTS, "pc_toolbar.png"), clip={"x": 0, "y": 0, "width": 1665, "height": 160})
        pg.click("#btnLink")
        pg.wait_for_timeout(300)
        clip = pg.evaluate("navigator.clipboard.readText()")
        chk("PC: 클립보드 = 회의록 양식 주소", clip == want, clip)
        t = pg.locator(".lnk-toast")
        chk("PC: 「링크를 복사했습니다」 띠", t.is_visible() and "링크를 복사했습니다" in t.inner_text())
        pg.screenshot(path=os.path.join(SHOTS, "pc_copied.png"))
        pg.wait_for_timeout(4800)
        chk("PC: 띠는 잠시 뒤 저절로 닫힘", pg.locator(".lnk-toast").count() == 0)
        # 수정하기 켠 채로도
        pg.click("#btnKle")
        pg.wait_for_timeout(150)
        pg.evaluate("navigator.clipboard.writeText('')")
        pg.click("#btnLink")
        pg.wait_for_timeout(300)
        chk("PC: 「수정하기」 켠 채로 눌러도 복사", pg.evaluate("navigator.clipboard.readText()") == want)
        pg.emulate_media(media="print")
        chk("인쇄: 링크 단추·띠 안 나옴", not pg.locator("#btnLink").is_visible() and not pg.locator(".lnk-toast").is_visible())
        pg.emulate_media(media="screen")
        ctx.close()
        # 번역·원문 꼬리(?orig=1)가 붙은 주소에서도 깨끗한 주소
        ctx, pg, base = page(PN, S["me"], 1665, 900)
        pg.goto(base + "/meetings/%d/doc?orig=1" % I["M1"], wait_until="networkidle")
        pg.click("#btnLink")
        pg.wait_for_timeout(300)
        chk("꼬리(?orig=1) 붙은 화면에서도 주소는 번호까지만", pg.evaluate("navigator.clipboard.readText()") == want)
        ctx.close()
        # 클립보드 막힘 → 옛 복사
        ctx, pg, base = page(PN, S["mem"], 1665, 900, clip=False)
        pg.add_init_script("Object.defineProperty(navigator, 'clipboard', {get(){ return {writeText(){ return Promise.reject(new Error('막힘')); }}; }});"
                           "window.__copied=null; const _ec=document.execCommand.bind(document); document.execCommand=function(c){ if(c==='copy'){ const a=document.activeElement; window.__copied=(a&&a.value)||''; return true;} return _ec.apply(null, arguments); };")
        pg.goto(base + "/meetings/%d/doc" % I["M1"], wait_until="networkidle")
        chk("보기만 하는 직원에게도 단추", pg.locator("#btnLink").is_visible() and pg.locator("#btnKle").count() == 0)
        pg.click("#btnLink")
        pg.wait_for_timeout(300)
        chk("클립보드 막힘 → 옛 복사로 같은 주소", pg.evaluate("window.__copied") == want, str(pg.evaluate("window.__copied")))
        chk("클립보드 막힘 → 그래도 「복사했습니다」", "링크를 복사했습니다" in pg.locator(".lnk-toast").inner_text())
        ctx.close()
        # 둘 다 막힘 → 주소 칸(휴대폰)
        ctx, pg, base = page(PN, S["mem"], 390, 844, clip=False)
        pg.add_init_script("Object.defineProperty(navigator, 'clipboard', {get(){ return undefined; }}); document.execCommand=function(){ return false; };")
        pg.goto(base + "/meetings/%d/doc" % I["M1"], wait_until="networkidle")
        ov = pg.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        pg.screenshot(path=os.path.join(SHOTS, "phone_toolbar.png"), clip={"x": 0, "y": 0, "width": 390, "height": 260})
        pg.click("#btnLink")
        pg.wait_for_timeout(300)
        inp = pg.locator("#lnkUrl")
        chk("둘 다 막힘 → 주소 칸이 뜨고 그 주소가 골라져 있음", inp.is_visible() and inp.input_value() == want and pg.evaluate("document.activeElement && document.activeElement.id") == "lnkUrl")
        chk("둘 다 막힘 → 「자동 복사가 막혔습니다」", "자동 복사가 막혔습니다" in pg.locator(".lnk-toast").inner_text())
        bx = pg.locator(".lnk-toast").bounding_box()
        chk("휴대폰: 띠가 화면 안 · 가로 넘침 없음", bx and bx["x"] >= 0 and bx["x"] + bx["width"] <= 390 and not ov, str(bx))
        pg.screenshot(path=os.path.join(SHOTS, "phone_manual.png"))
        pg.locator(".lnk-toast button").click()
        chk("「닫기」로 닫힘", pg.locator(".lnk-toast").count() == 0)
        ctx.close()
        # 베트남어
        ctx, pg, base = page(PN, S["vi"], 390, 844)
        pg.goto(base + "/meetings/%d/doc" % I["M1"], wait_until="networkidle")
        pg.click("#btnLink")
        pg.wait_for_timeout(300)
        chk("베트남어: 같은 주소 · 베트남어 알림", pg.evaluate("navigator.clipboard.readText()") == want and "Đã sao chép liên kết" in pg.locator(".lnk-toast").inner_text())
        pg.screenshot(path=os.path.join(SHOTS, "phone_vi_copied.png"))
        ctx.close()
        # 복사한 주소를 다른 사람이 열면(로그인 = 쿠키 있음)
        ctx, pg, base = page(PN, S["other"], 1665, 900)
        pg.goto(want, wait_until="networkidle")
        chk("다른 팀 직원이 링크를 열면 → 회의록 목록 · 내용 안 보임", pg.url.endswith("/meetings") and "자재 입고 점검 회의" not in pg.content(), pg.url)
        ctx.close()
        br.close()

    print("== 오류 ==")
    chk("화면 오류 0", ERRS == [], str(ERRS[:3]))
finally:
    for pr in PRS.values():
        try:
            pr.kill()
        except Exception:
            pass

if FAILS:
    print("실패한 것:", FAILS)
print("\n결과: 통과 %d · 실패 %d" % (OK, len(FAILS)))
sys.exit(0 if not FAILS else 1)
