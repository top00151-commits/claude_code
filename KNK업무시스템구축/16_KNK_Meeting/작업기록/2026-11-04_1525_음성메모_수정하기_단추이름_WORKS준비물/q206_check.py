# -*- coding: utf-8 -*-
"""z1206 검사 — 음성 메모 정리 단추 「✏ 고치기」 → 「✏ 수정하기」 (대표 2026-11-04 「음성메모도 수정하기로 변경」)
운영 그대로(app_base)와 새것(app_new)을 나란히 띄워 본다.
  ① 파일: 바뀐 파일 = voice_note_form.html · voice_note_vi.py 둘 · 바뀐 줄 = 각 1줄
  ② 한국어 직원: 단추 글 「✏ 수정하기」 · 화면에 「✏ 고치기」 없음 · 누르면 글 상자 열림 · 저장 · 취소 그대로
  ③ 베트남어 직원: 단추 글 「✏ Sửa」 그대로 · 한글 단추 글이 새지 않음
  ④ 단추 말고 화면 HTML 차이 0(한국어·베트남어) · 회의록 화면은 그대로(같은 HTML)
  ⑤ 오류 0 · 사진(shots/)
쓰는 법: py -3.12 q206_check.py <app_base·app_new 가 있는 폴더>   🔒 시험 글은 모두 지어낸 것.
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
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1]
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
RUN = os.path.join(HERE, "run_q206_app.py")
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
PORTS = {"app_base": 8992, "app_new": 8993}
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
    lp = os.path.join(APPDIR, "srv06_%d.log" % port)
    pr = subprocess.Popen([P313, RUN, os.path.join(APPDIR, app), str(port)], stdout=io.open(lp, "w", encoding="utf-8"),
                          stderr=subprocess.STDOUT, cwd=APPDIR)
    for _ in range(120):
        time.sleep(1)
        txt = io.open(lp, encoding="utf-8", errors="replace").read()
        for ln in txt.splitlines():
            if ln.startswith("READY"):
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


def rd(app, rel):
    return io.open(os.path.join(APPDIR, app, "app", rel), encoding="utf-8").read()


def diff(a, b):
    return [d for d in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0) if d[:1] in "+-" and not d.startswith(("+++", "---"))]


def http(port, path, uid):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), headers={"Cookie": "tuser=%s" % uid})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "replace")


def norm(h):
    # 매번 바뀌는 값(시각·무작위 토큰)만 지운다
    h = re.sub(r"\?v=[0-9A-Za-z_.-]+", "?v=X", h)
    h = re.sub(r'var LOADED = "[^"]*"', 'var LOADED = "X"', h)
    h = re.sub(r'id="knkVer" data-v="[^"]*"', 'id="knkVer" data-v="X"', h)   # 11-27: 서버 켠 시각 버전 표시(그 뒤 생김)
    h = re.sub(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?", "T", h)
    h = re.sub(r'(nonce|csrf[_-]?token)="[^"]*"', r'\1="X"', h)
    return h


print("== ① 파일 ==")
WB, WN = walk("app_base"), walk("app_new")
changed = sorted(k for k in set(WB) | set(WN) if WB.get(k) != WN.get(k))
chk("바뀐 파일 = 음성 메모 화면 · 베트남어 사전 둘", changed == ["templates/voice_note_form.html", "voice_note_vi.py"], str(changed))
d1 = diff(rd("app_base", "templates/voice_note_form.html"), rd("app_new", "templates/voice_note_form.html"))
chk("화면 = 1줄만(단추 글)", len(d1) == 2 and "✏ 고치기" in d1[0] and "✏ 수정하기" in d1[1] and d1[0].replace("고치기", "수정하기")[1:] == d1[1][1:], str(d1))
d2 = diff(rd("app_base", "voice_note_vi.py"), rd("app_new", "voice_note_vi.py"))
chk("사전 = 1줄만(열쇠 이름 · 베트남어 「✏ Sửa」 그대로)", len(d2) == 2 and '"✏ 고치기": "✏ Sửa",' in d2[0] and '"✏ 수정하기": "✏ Sửa",' in d2[1], str(d2))
chk("회의록·다른 화면 파일 안 건드림", not any(("meeting" in k or "i18n" in k or "knk_line_edit" in k) for k in changed))

PRS = {}
try:
    for app in ("app_base", "app_new"):
        PRS[app] = start(app)
    PB, PN = PORTS["app_base"], PORTS["app_new"]
    SB = json.load(io.open(os.path.join(HERE, "seed_%d.json" % PB), encoding="utf-8"))
    SN = json.load(io.open(os.path.join(HERE, "seed_%d.json" % PN), encoding="utf-8"))
    IB, IN = SB["ids"], SN["ids"]

    print("== ④ 화면 HTML(서버) ==")
    for who, key, nid in (("한국어(대표)", "me", "V1"), ("베트남어 직원", "vi1", "VI1")):
        _, hb = http(PB, "/voice-notes/%d" % IB[nid], SB[key])
        _, hn = http(PN, "/voice-notes/%d" % IN[nid], SN[key])
        dd = diff(norm(hb), norm(hn))
        if key == "me":
            ok = len(dd) == 2 and "✏ 고치기" in dd[0] and "✏ 수정하기" in dd[1]
            chk("%s: 차이 = 단추 1줄뿐" % who, ok, str(dd[:4]))
            chk("%s: 새 화면 글에 「✏ 고치기」 없음(코드 설명 주석 빼고)" % who, ">✏ 고치기<" not in hn and ">✏ 수정하기</button>" in hn)
        else:
            dv = [x for x in dd if "var _VND = " not in x]   # 사전(JS) 줄은 열쇠 이름만 바뀐다 — 아래에서 따로 본다
            chk("%s: 사전 줄 말고 차이 0(「✏ Sửa」 그대로)" % who, dv == [] and len(dd) == 2, str(dv[:4]))
            def vnd(h):
                ln = [x for x in h.splitlines() if "var _VND = " in x][0]
                return json.JSONDecoder().raw_decode(ln[ln.index("{"):])[0]
            jb, jn = vnd(hb), vnd(hn)
            jb2 = dict(jb)
            jb2["✏ 수정하기"] = jb2.pop("✏ 고치기", None)
            chk("%s: 사전 = 열쇠 「✏ 고치기」→「✏ 수정하기」 만(값 「✏ Sửa」)" % who, jb2 == jn and jn.get("✏ 수정하기") == "✏ Sửa", "%d→%d" % (len(jb), len(jn)))
            chk("%s: 「✏ Sửa」 있고 한글 단추 글 없음" % who, 'id="vnSumEdit" type="button">✏ Sửa</button>' in hn and ">✏ 수정하기<" not in hn and ">✏ 고치기<" not in hn)
    _, mb = http(PB, "/meetings/%d" % IB["M1"], SB["me"])
    _, mn = http(PN, "/meetings/%d" % IN["M1"], SN["me"])
    chk("회의록 화면 = 같은 HTML", diff(norm(mb), norm(mn)) == [], str(diff(norm(mb), norm(mn))[:4]))
    _, lb = http(PB, "/voice-notes", SB["me"])
    _, ln_ = http(PN, "/voice-notes", SN["me"])
    chk("음성 메모 목록 = 같은 HTML", diff(norm(lb), norm(ln_)) == [], str(diff(norm(lb), norm(ln_))[:4]))

    from playwright.sync_api import sync_playwright   # noqa: E402

    print("== ②③ 눌러 보기 ==")
    with sync_playwright() as p:
        br = p.chromium.launch()

        def page(port, uid, w, h):
            base = "http://127.0.0.1:%d" % port
            ctx = br.new_context(viewport={"width": w, "height": h}, device_scale_factor=(2 if w < 800 else 1), is_mobile=(w < 800), has_touch=(w < 800))
            ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": base}])
            pg = ctx.new_page()
            pg.add_init_script(NOHINT)
            pg.on("pageerror", lambda e: ERRS.append("pageerror %s" % str(e)[:160]))
            pg.on("console", lambda m: ERRS.append("console %s" % m.text[:160]) if (m.type == "error" and "Failed to load resource" not in m.text) else None)
            return ctx, pg, base

        for tag, w, h in (("pc", 1665, 900), ("phone", 390, 844)):
            ctx, pg, base = page(PN, SN["me"], w, h)
            pg.goto(base + "/voice-notes/%d" % IN["V1"], wait_until="networkidle")
            pg.wait_for_timeout(250)
            b = pg.locator("#vnSumEdit")
            chk("한국어 %s: 단추 글 「✏ 수정하기」" % tag, b.inner_text().strip() == "✏ 수정하기", b.inner_text())
            bb = b.bounding_box()
            chk("한국어 %s: 단추 한 줄(줄바꿈 없음)" % tag, bb and bb["height"] < 48, str(bb))
            pg.locator("#vnSumSec").scroll_into_view_if_needed()
            pg.screenshot(path=os.path.join(SHOTS, "after_%s.png" % tag))
            b.click()
            pg.wait_for_timeout(200)
            chk("한국어 %s: 누르면 글 상자 열림" % tag, pg.locator("#vnSumEditWrap").is_visible() and not pg.locator("#vnSumBox").is_visible())
            if tag == "pc":
                v0 = pg.input_value("#vnSumEdit2")
                pg.fill("#vnSumEdit2", v0 + "\n- 지어낸 덧붙임 줄")
                pg.click("#vnSumSave")
                pg.wait_for_timeout(600)
                chk("한국어 pc: 저장 → 글 상자 닫힘 · 정리 칸에 고친 글", (not pg.locator("#vnSumEditWrap").is_visible()) and "지어낸 덧붙임 줄" in pg.inner_text("#vnSumBox"))
                b.click()
                pg.wait_for_timeout(150)
                pg.click("#vnSumCancel")
                pg.wait_for_timeout(150)
                chk("한국어 pc: 취소 → 닫힘", not pg.locator("#vnSumEditWrap").is_visible())
            ctx.close()
        # 바탕 사진(비교용)
        ctx, pg, base = page(PB, SB["me"], 1665, 900)
        pg.goto(base + "/voice-notes/%d" % IB["V1"], wait_until="networkidle")
        pg.locator("#vnSumSec").scroll_into_view_if_needed()
        chk("바탕(운영 그대로)은 「✏ 고치기」", pg.locator("#vnSumEdit").inner_text().strip() == "✏ 고치기")
        pg.screenshot(path=os.path.join(SHOTS, "before_pc.png"))
        ctx.close()
        # 베트남어
        ctx, pg, base = page(PN, SN["vi1"], 390, 844)
        pg.goto(base + "/voice-notes/%d" % IN["VI1"], wait_until="networkidle")
        pg.wait_for_timeout(250)
        chk("베트남어 phone: 단추 글 「✏ Sửa」", pg.locator("#vnSumEdit").inner_text().strip() == "✏ Sửa")
        pg.locator("#vnSumEdit").click()
        pg.wait_for_timeout(200)
        chk("베트남어 phone: 누르면 글 상자 열림", pg.locator("#vnSumEditWrap").is_visible())
        pg.screenshot(path=os.path.join(SHOTS, "after_vi_phone.png"))
        ctx.close()
        br.close()

    print("== ⑤ 오류 ==")
    chk("화면 오류 0", ERRS == [], str(ERRS[:3]))
finally:
    for pr in PRS.values():
        try:
            pr.kill()
        except Exception:
            pass

if FAILS:
    print("실패한 것:", FAILS)
print("\n결과: 통과 %d · 실패 %d" % (OK, len(FAILS)))   # 회귀 요약이 읽는 모양(「결과: 숫자」)
sys.exit(0 if not FAILS else 1)
