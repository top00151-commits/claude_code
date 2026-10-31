# -*- coding: utf-8 -*-
"""z1201 검사 — 음성 메모 「✏ 고치기」 칸 넓힘(이용식 법인장 신고 · 대표 전달 2026-10-31 「고치기 화면이 너무 작아서 수정하는데 어려움」)
운영 그대로(app_base)와 새것(app_new)을 나란히 띄워 잰다.

재는 것
  ① 바뀐 파일 = voice_note_form.html 하나 · 바뀐 줄이 정해진 셋뿐
  ② 바탕(운영 그대로): 신고 화면 폭(1665)에서 칸이 좁다 — 검사기가 그 병을 잡는지(어긴 코드로 시험)
  ③ 새것: 폭 360·390·412·720·904·1280·1665·1920 마다 칸 폭 = 정리 칸 안쪽 폭 · 가로 넘침 없음 · 저장·취소 단추가 칸 아래
  ④ 높이: 짧은 글 = rows=10 · 중간 글 = 글 전부 보임(칸 안 스크롤 없음) · 긴 글 = 창 높이 70% · 눕힌 폰처럼 낮은 창도 rows=10 아래로 안 내려감
  ⑤ 모양: 받아쓴 원문 칸과 같은 글꼴·여백·테두리 · 모서리로 늘릴 수 있음(resize vertical) · 줄바꿈 그대로
  ⑥ 동작: 원래 글(마크다운 표시 그대로)이 열림 · 저장 → DB·화면 · 취소 → DB 그대로 · 다시 열면 높이 다시 맞춤 · 다시 정리 뒤 값 이어짐
  ⑦ 안 고친 곳 그대로: 고치기 안 누른 화면 HTML 차이 = 정해진 줄뿐 · 정리 칸 높이 같음 · 회의록 고치기 칸은 원래부터 꽉 참
  ⑧ 화면 오류 0
  ⑨ 대표께 보여 드릴 사진(shots/): 고치기 전 1665 · 고친 뒤 1665(긴 글·짧은 글)·폰 390·폴드 720

쓰는 법: py -3.12 q201_check.py <app_base·app_new 가 있는 폴더>   판정: 종료코드(0=통과) + 요약 줄.  🔒 시험 글은 모두 지어낸 것.
"""
import difflib
import hashlib
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1] if len(sys.argv) > 1 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
RUN = os.path.join(HERE, "run_q201_app.py")
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
PORTS = {"app_base": 8979, "app_new": 8980}
N = OK = 0
FAILS = []


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
    lp = os.path.join(APPDIR, "srv01_%d.log" % port)
    pr = subprocess.Popen([P313, RUN, os.path.join(APPDIR, app), str(port)],
                          stdout=io.open(lp, "w", encoding="utf-8"), stderr=subprocess.STDOUT, cwd=APPDIR)
    for _ in range(90):
        time.sleep(1)
        try:
            txt = io.open(lp, encoding="utf-8", errors="replace").read()
        except OSError:
            txt = ""
        for ln in txt.splitlines():
            if ln.startswith("READY"):
                return pr, json.loads(ln.split(" ", 2)[2])
        if pr.poll() is not None:
            break
    print("⛔ %s 서버가 안 떴다 — %s" % (app, lp))
    print(io.open(lp, encoding="utf-8", errors="replace").read()[-1500:])
    sys.exit(2)


def rd(app, rel):
    return io.open(os.path.join(APPDIR, app, "app", rel), encoding="utf-8").read()


def walk(app):
    root = os.path.join(APPDIR, app, "app")
    out = {}
    for d, _dirs, files in os.walk(root):
        if "__pycache__" in d:
            continue
        for f in files:
            if f.endswith((".pyc", ".bak_z1201")):
                continue
            full = os.path.join(d, f)
            out[os.path.relpath(full, root).replace("\\", "/")] = hashlib.md5(io.open(full, "rb").read()).hexdigest()
    return out


def diff(a, b):
    return [d for d in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0) if d[:1] in "+-" and not d.startswith(("+++", "---"))]


def db(app):
    return sqlite3.connect(os.path.join(APPDIR, app, "data", "knk.db"), timeout=15)


def add_note(app, owner, title, summary):
    c = db(app)
    nid = c.execute("INSERT INTO voice_notes(owner_id, title, body, summary, audio_path, created_at, updated_at) VALUES(?,?,?,?,?,?,?)",
                    (owner, title, "지어낸 받아쓴 원문입니다.", summary, "", "2026-10-30 09:30:00", "2026-10-30 09:30:00")).lastrowid
    c.commit()
    c.close()
    return nid


def get_summary(app, nid):
    c = db(app)
    r = c.execute("SELECT summary FROM voice_notes WHERE id=?", (nid,)).fetchone()
    c.close()
    return r[0]


def html(app, uid, path):
    q = urllib.request.Request("http://127.0.0.1:%d%s" % (PORTS[app], path), headers={"Cookie": "tuser=%d" % uid})
    with urllib.request.urlopen(q, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


LONG = "## 핵심\n" + "\n".join("- **지어낸 논의 %d** — 지어낸 설명이 조금 길게 이어지는 줄입니다. 담당 · 기한 미정" % i for i in range(1, 61))
MID = "## 핵심\n" + "\n".join("- **지어낸 논의 %d** — 담당 · 2026-11-%02d" % (i, i) for i in range(1, 16))
SHORT = "## 핵심\n지어낸 정리입니다.\n\n## 할 일\n- **지어낸 일** — 담당 · 2026-10-30"

print("== ① 파일 ==")
WB, WN = walk("app_base"), walk("app_new")
changed = sorted(k for k in set(WB) | set(WN) if WB.get(k) != WN.get(k))
chk("바뀐 파일 = voice_note_form.html 하나", changed == ["templates/voice_note_form.html"], str(changed))
dv = diff(rd("app_base", "templates/voice_note_form.html"), rd("app_new", "templates/voice_note_form.html"))
rem = [x[1:].strip() for x in dv if x.startswith("-")]
chk("뺀 줄 = 정해진 둘(칸 여는 div · 고치기 누를 때 줄)", rem == ['<div id="vnSumEditWrap" hidden>', "_sw.hidden = false; _sb.hidden = true;"], str(rem))
add = [x[1:].strip() for x in dv if x.startswith("+")]
chk("더한 줄 = 10줄(설명 2 · class 1 · 높이 함수 6 · 고치기 줄 1)", len(add) == 10 and any('class="vn-fld"' in x for x in add) and any("vnSumFit();" in x for x in add), "더한 %d" % len(add))

PRS, SEED, IDS = {}, {}, {}
print("== 서버 두 벌 ==")
for app in ("app_base", "app_new"):
    PRS[app], SEED[app] = start(app)
    me = SEED[app]["me"]
    IDS[app] = {"V1": SEED[app]["ids"]["V1"], "V4": SEED[app]["ids"]["V4"], "M1": SEED[app]["ids"]["M1"],
                "long": add_note(app, me, "긴 정리(지어낸 글)", LONG), "mid": add_note(app, me, "중간 정리(지어낸 글)", MID),
                "short": add_note(app, me, "짧은 정리(지어낸 글)", SHORT)}
    print("  %s 포트 %d · %s" % (app, PORTS[app], IDS[app]))

from playwright.sync_api import sync_playwright   # noqa: E402

JS = """
() => {
  const t = document.querySelector('#vnSumEdit2'), sec = document.querySelector('#vnSumSec');
  const r = t.getBoundingClientRect(), sr = sec.getBoundingClientRect();
  const scs = getComputedStyle(sec), cs = getComputedStyle(t);
  const inner = sr.width - parseFloat(scs.paddingLeft) - parseFloat(scs.paddingRight) - parseFloat(scs.borderLeftWidth) - parseFloat(scs.borderRightWidth);
  const sv = document.querySelector('#vnSumSave').getBoundingClientRect(), cc = document.querySelector('#vnSumCancel').getBoundingClientRect();
  return {w: r.width, h: r.height, inner, leftGap: r.left - sr.left, rightGap: sr.right - r.right, font: cs.fontSize, lh: cs.lineHeight, pad: cs.paddingLeft,
          radius: cs.borderTopLeftRadius, border: cs.borderTopWidth, resize: cs.resize, family: cs.fontFamily, ws: cs.whiteSpace, sh: t.scrollHeight, ch: t.clientHeight,
          innerH: window.innerHeight, over: document.documentElement.scrollWidth > window.innerWidth, scrollW: document.documentElement.scrollWidth,
          taBottom: r.bottom, saveTop: sv.top, cancelTop: cc.top, saveH: sv.height, boxHidden: document.querySelector('#vnSumBox').hidden,
          wrapHidden: document.querySelector('#vnSumEditWrap').hidden, value: t.value};
}
"""

ERRS = []


def page(br, app, uid, w, h):
    base = "http://127.0.0.1:%d" % PORTS[app]
    ctx = br.new_context(viewport={"width": w, "height": h}, device_scale_factor=(2 if w < 800 else 1), is_mobile=(w < 800), has_touch=(w < 800))
    ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": base}])
    pg = ctx.new_page()
    pg.add_init_script("""document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style');
      s.textContent = '#worksInstallHint{display:none !important}'; document.head.appendChild(s); });""")   # 휴대폰은 설치 안내 창이 누르기를 가로챔
    pg.on("pageerror", lambda e: ERRS.append("%s %d pageerror %s" % (app, w, str(e)[:160])))
    pg.on("console", lambda m: ERRS.append("%s %d console %s" % (app, w, m.text[:160])) if (m.type == "error" and "Failed to load resource" not in m.text) else None)
    return ctx, pg, base


def open_edit(br, app, uid, nid, w, h=900, shot=None):
    ctx, pg, base = page(br, app, uid, w, h)
    pg.goto(base + "/voice-notes/%d" % nid, wait_until="networkidle")
    pg.wait_for_timeout(250)
    pg.locator("#vnSumEdit").click()
    pg.wait_for_timeout(150)
    m = pg.evaluate(JS)
    if shot:
        pg.locator("#vnSumSec").scroll_into_view_if_needed()
        pg.wait_for_timeout(100)
        pg.screenshot(path=os.path.join(SHOTS, shot))
    ctx.close()
    return m


try:
    with sync_playwright() as p:
        br = p.chromium.launch()
        me_b, me_n = SEED["app_base"]["me"], SEED["app_new"]["me"]
        idb, idn = IDS["app_base"], IDS["app_new"]

        print("== ② 바탕(운영 그대로) — 검사기가 신고 내용을 잡는가 ==")
        mb = open_edit(br, "app_base", me_b, idb["long"], 1665, shot="before_1665.png")
        chk("바탕 1665: 칸이 좁다(폭 300px 아래 · 안쪽 폭의 25% 아래) — 신고 재현", mb["w"] < 300 and mb["w"] / mb["inner"] < 0.25, "칸 폭 %.0f / 안쪽 폭 %.0f · 높이 %.0f" % (mb["w"], mb["inner"], mb["h"]))
        mb390 = open_edit(br, "app_base", me_b, idb["long"], 390)
        print("    바탕 390: 칸 폭 %.0f / 안쪽 폭 %.0f · 글자 %s" % (mb390["w"], mb390["inner"], mb390["font"]))

        print("== ③ 새것 — 폭마다 칸이 꽉 찬다 ==")
        for w in (360, 390, 412, 720, 904, 1280, 1665, 1920):
            m = open_edit(br, "app_new", me_n, idn["long"], w)
            chk("폭 %d: 칸 폭 = 안쪽 폭 · 좌우 대칭 · 가로 넘침 없음 · 저장·취소 칸 아래" % w,
                abs(m["w"] - m["inner"]) <= 1 and abs(m["leftGap"] - m["rightGap"]) <= 1 and not m["over"]
                and m["saveTop"] >= m["taBottom"] and m["cancelTop"] >= m["taBottom"] and m["saveH"] <= 44 and not m["wrapHidden"] and m["boxHidden"],
                "칸 %.0f / 안쪽 %.0f · 높이 %.0f · 넘침 %s" % (m["w"], m["inner"], m["h"], m["over"]))

        print("== ④ 높이 — 글 양에 맞춘다 ==")
        ms = open_edit(br, "app_new", me_n, idn["short"], 1665)
        chk("짧은 글: rows=10 높이(약 276px)", 250 <= ms["h"] <= 300, "%.0f" % ms["h"])
        mm = open_edit(br, "app_new", me_n, idn["mid"], 1665)
        chk("중간 글(16줄): 글 전부 보임 — 칸 안 스크롤 없음 · 창 70% 안", mm["sh"] <= mm["ch"] + 1 and mm["h"] <= mm["innerH"] * 0.7 + 1 and mm["h"] > ms["h"], "높이 %.0f · 안쪽 글 높이 %d / 보이는 %d" % (mm["h"], mm["sh"], mm["ch"]))
        ml = open_edit(br, "app_new", me_n, idn["long"], 1665)
        chk("긴 글(61줄): 창 높이 70% · 칸 안에서 내림", abs(ml["h"] - round(ml["innerH"] * 0.7)) <= 1 and ml["sh"] > ml["ch"], "높이 %.0f / 창 %d · 글 높이 %d" % (ml["h"], ml["innerH"], ml["sh"]))
        chk("바탕보다 칸 넓이가 크게 늘었다(폭 5배 이상 · 높이 그 이상)", ml["w"] >= mb["w"] * 5 and ml["h"] >= mb["h"], "폭 %.0f→%.0f · 높이 %.0f→%.0f" % (mb["w"], ml["w"], mb["h"], ml["h"]))
        ml2 = open_edit(br, "app_new", me_n, idn["long"], 800, h=360)
        chk("낮은 창(가로 폰 800×360): rows=10 아래로 안 내려감", ml2["h"] >= 250, "높이 %.0f / 창 %d" % (ml2["h"], ml2["innerH"]))
        ml3 = open_edit(br, "app_new", me_n, idn["long"], 390, h=800)
        chk("폰 390×800 긴 글: 칸 높이 = 창 70% · 저장 단추까지 스크롤로 닿음", abs(ml3["h"] - 560) <= 1, "높이 %.0f" % ml3["h"])

        print("== ⑤ 모양 — 받아쓴 원문 칸과 같다 ==")
        ctx, pg, base = page(br, "app_new", me_n, 1280, 900)
        pg.goto(base + "/voice-notes/%d" % idn["V1"], wait_until="networkidle")
        pg.wait_for_timeout(250)
        pg.locator("#vnSumEdit").click()
        pg.evaluate("document.querySelector('#vnBodyWrap').open = true")
        pg.wait_for_timeout(120)
        st = pg.evaluate("""() => { const f = (s) => { const c = getComputedStyle(document.querySelector(s)), r = document.querySelector(s).getBoundingClientRect();
            return {font: c.fontSize, lh: c.lineHeight, pad: c.paddingLeft, radius: c.borderTopLeftRadius, border: c.borderTopWidth, resize: c.resize, family: c.fontFamily, ws: c.whiteSpace, w: Math.round(r.width)}; };
            return {a: f('#vnSumEdit2'), b: f('#vnBody')}; }""")
        same = {k: (st["a"][k] == st["b"][k]) for k in ("font", "lh", "pad", "radius", "border", "resize", "family", "ws")}
        chk("글꼴·줄간격·여백·테두리·늘리기·줄바꿈이 원문 칸과 같다", all(same.values()), str(st["a"]))
        chk("모서리로 늘릴 수 있다(resize vertical) · 글자 14px", st["a"]["resize"] == "vertical" and st["a"]["font"] == "14px")
        ctx.close()

        print("== ⑥ 동작 ==")
        ctx, pg, base = page(br, "app_new", me_n, 1665, 900)
        nid = idn["long"]
        pg.goto(base + "/voice-notes/%d" % nid, wait_until="networkidle")
        pg.wait_for_timeout(250)
        pg.locator("#vnSumEdit").click()
        chk("열면 원래 글(마크다운 표시·줄바꿈 그대로)", pg.input_value("#vnSumEdit2") == LONG)
        pg.fill("#vnSumEdit2", "버릴 글입니다")
        pg.locator("#vnSumCancel").click()
        pg.wait_for_timeout(120)
        chk("취소 → DB 그대로 · 정리 화면으로", get_summary("app_new", nid) == LONG and pg.locator("#vnSumBox").is_visible() and not pg.locator("#vnSumEditWrap").is_visible())
        pg.locator("#vnSumEdit").click()
        chk("취소 뒤 다시 열면 원래 글", pg.input_value("#vnSumEdit2") == LONG)
        NEWTXT = "## 핵심\n고친 **지어낸 글**입니다.\n\n- 둘째 줄"
        pg.fill("#vnSumEdit2", "  " + NEWTXT + "  \n")
        pg.locator("#vnSumSave").click()
        pg.wait_for_function("document.querySelector('#vnSumEditWrap').hidden === true", timeout=8000)
        pg.wait_for_timeout(150)
        chk("저장 → DB = 고친 글(앞뒤 빈칸 정리)", get_summary("app_new", nid) == NEWTXT, repr(get_summary("app_new", nid))[:80])
        box = pg.locator("#vnSumBox").inner_text()
        chk("저장 뒤 화면 = 그려진 정리(** 표시 없음) · 안내 「저장했습니다」", "고친" in box and "**" not in box and "저장했습니다" in pg.locator("#vnSt").inner_text(), box[:60].replace("\n", " / "))
        pg.locator("#vnSumEdit").click()
        pg.wait_for_timeout(120)
        m2 = pg.evaluate(JS)
        chk("긴 글을 짧게 고친 뒤 다시 열면 높이 다시 맞춤(rows=10) · 고친 글 그대로", 250 <= m2["h"] <= 300 and m2["value"] == NEWTXT, "높이 %.0f" % m2["h"])
        pg.reload(wait_until="networkidle")
        pg.wait_for_timeout(250)
        pg.locator("#vnSumEdit").click()
        chk("새로고침 뒤에도 고친 글", pg.input_value("#vnSumEdit2") == NEWTXT)
        ctx.close()
        mem = json.loads(io.open(os.path.join(HERE, "seed_%d.json" % PORTS["app_new"]), encoding="utf-8").read())["mem"]
        ctx, pg, base = page(br, "app_new", mem, 1280, 900)
        pg.goto(base + "/voice-notes/%d" % idn["V4"], wait_until="networkidle")
        pg.wait_for_timeout(250)
        pg.locator("#vnSumEdit").click()
        pg.wait_for_timeout(120)
        m4 = pg.evaluate(JS)
        chk("직원이 제 메모를 열어도 같은 칸", abs(m4["w"] - m4["inner"]) <= 1 and m4["h"] >= 250, "칸 %.0f / %.0f" % (m4["w"], m4["inner"]))
        ctx.close()

        print("== ⑦ 안 고친 곳 그대로 ==")
        norm = lambda t: re.sub(r"\?v=[\w.-]+", "?v=X", t)
        hb, hn = norm(html("app_base", me_b, "/voice-notes/%d" % idb["short"])), norm(html("app_new", me_n, "/voice-notes/%d" % idn["short"]))
        d = diff(hb, hn)
        rem_h = [x[1:].strip() for x in d if x.startswith("-")]
        add_h = [x[1:].strip() for x in d if x.startswith("+")]
        chk("고치기 안 누른 화면 HTML 차이 = 정해진 줄뿐(칸 여는 div · 고치기 줄 · 함수 6 · 설명이 남긴 빈 줄 1)", rem_h == ['<div id="vnSumEditWrap" hidden>', "_sw.hidden = false; _sb.hidden = true;"] and len(add_h) == 9 and add_h.count("") == 1,
            "뺀 %d · 더한 %d %s" % (len(rem_h), len(add_h), [x[:50] for x in add_h] if len(add_h) != 9 else ""))

        def sec_h(app, uid, nid_):
            ctx_, pg_, base_ = page(br, app, uid, 1280, 900)
            pg_.goto(base_ + "/voice-notes/%d" % nid_, wait_until="networkidle")
            pg_.wait_for_timeout(250)
            v = pg_.evaluate("() => { const a = (s) => Array.from(document.querySelectorAll(s)).map(e => Math.round(e.getBoundingClientRect().height)); return {sec: a('.vn-sec'), acts: a('.vn-acts .btn')}; }")
            ctx_.close()
            return v
        sb, sn = sec_h("app_base", me_b, idb["short"]), sec_h("app_new", me_n, idn["short"])
        chk("정리 보는 화면 높이·단추 높이 바탕과 같다", sb == sn, "%s" % sn["sec"])
        ctx, pg, base = page(br, "app_new", me_n, 1665, 900)
        pg.goto(base + "/meetings/%d" % idn["M1"], wait_until="networkidle")
        pg.wait_for_timeout(300)
        pg.locator("#btnSumEdit").click()
        pg.wait_for_timeout(120)
        mt = pg.evaluate("() => { const t = document.querySelector('#sumEdit').getBoundingClientRect(), p = document.querySelector('#sumEditWrap').getBoundingClientRect(); return {w: t.width, pw: p.width, h: t.height}; }")
        chk("회의록 고치기 칸은 원래부터 꽉 참(같은 병 없음)", abs(mt["w"] - mt["pw"]) <= 1 and mt["w"] > 800, "칸 %.0f / %.0f · 높이 %.0f" % (mt["w"], mt["pw"], mt["h"]))
        ctx.close()

        print("== ⑧ 화면 오류 ==")
        chk("화면 오류 0(새것)", not [e for e in ERRS if e.startswith("app_new")], str(ERRS[:3]))

        print("== ⑨ 사진 ==")
        c = db("app_new")
        c.execute("UPDATE voice_notes SET summary=? WHERE id=?", (LONG, idn["long"]))
        c.commit()
        c.close()
        open_edit(br, "app_new", me_n, idn["long"], 1665, shot="after_1665_long.png")
        open_edit(br, "app_new", me_n, idn["short"], 1665, shot="after_1665_short.png")
        open_edit(br, "app_new", me_n, idn["long"], 720, h=1000, shot="after_720.png")
        open_edit(br, "app_new", me_n, idn["long"], 390, h=800, shot="after_390.png")
        open_edit(br, "app_base", me_b, idb["long"], 390, h=800, shot="before_390.png")
        chk("사진 5+1장", all(os.path.exists(os.path.join(SHOTS, f)) for f in ("before_1665.png", "after_1665_long.png", "after_1665_short.png", "after_720.png", "after_390.png", "before_390.png")))
        br.close()
finally:
    for app, pr in PRS.items():
        try:
            pr.terminate()
        except Exception:
            pass

print("q201 %d/%d" % (OK, N), "· 실패:" if FAILS else "", FAILS if FAILS else "")
print("결과: 통과 %d · 실패 %d" % (OK, N - OK))   # 회귀 판정기(res)가 읽는 요약 줄 형식
sys.exit(0 if OK == N else 1)
