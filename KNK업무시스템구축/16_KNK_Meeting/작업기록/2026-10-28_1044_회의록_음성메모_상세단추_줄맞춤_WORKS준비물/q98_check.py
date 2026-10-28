# -*- coding: utf-8 -*-
"""z1198 검사 — 회의록·음성 메모 상세 위 단추 줄(폴드 접음·펼침·보통 폰·태블릿·PC 폭) · 운영 그대로(app_base)와 새것(app_new) 나란히.

재는 것
  ① 그 밖 파일 그대로(두 화면 파일만 다름) · 바뀐 줄 = 인라인 div 한 줄 뺌 + class/CSS 더함(그 밖 뺀 줄 0)
  ② 새것: 폭 360·390·412·720·904·1280 마다 — 단추 글자 안 꺾임(모든 단추 높이 ≤ 44 · 서로 같은 높이) · white-space nowrap · 줄바꿈 허용(flex-wrap wrap)
         · 줄 수(좁은 폭 ≤3 · 720 이상 ≤2 · 1280 = 1) · 같은 줄은 위가 같고 줄 사이 간격이 같다 · 가로 넘침 없음 · 단추 글자 그대로(6개 · 종료됨 꼬리표 포함)
         · 「⏹ 종료」 단추는 끝난 회의에선 숨은 채 · 직원 눈엔 통역 대조·삭제 없이도 한 줄
  ③ 음성 메모: 단추 5개 높이 모두 같음(38) · nowrap · 줄바꿈 · 넘침 없음
  ④ 바탕(운영 그대로)에선 360 폭에서 단추가 꺾인다(높이 > 60) · 메모 단추 높이가 서로 다르다(40/37) — 검사기가 잡는지(어긴 코드로 검사기 시험)
  ⑤ 대표께 보여 드릴 사진: 새것 360·390·412·720·904 + 바탕 360 (shots/)
쓰는 법: py -3.12 q98_check.py <app_base·app_new 가 있는 폴더>   판정: 종료코드(0=통과) + 요약 줄.  🔒 시험 글은 모두 지어낸 것(run_q96_app.py 씨앗)."""
import difflib
import hashlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1] if len(sys.argv) > 1 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
Z96PREP = r"C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\16_KNK_Meeting\작업기록\2026-10-27_1802_통역대조_WORKS준비물"
RUN = os.path.join(HERE, "run_q98_app.py")
if not os.path.exists(RUN):
    RUN = os.path.join(Z96PREP, "run_q96_app.py")
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
PORTS = {"app_base": 8965, "app_new": 8966}
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
    lp = os.path.join(APPDIR, "srv98_%d.log" % port)
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


def first_user(app, role, mid):
    """READY 줄엔 대표(me)·기록 번호만 있다 — 직원 번호는 시험 DB 에서(그 회의록과 같은 팀의 첫 사람 · 팀 공개 회의록을 볼 수 있어야 하니)."""
    c = sqlite3.connect(os.path.join(APPDIR, app, "data", "knk.db"))
    r = c.execute("SELECT u.id FROM users u JOIN meetings m ON m.team_id=u.team_id WHERE u.role=? AND m.id=? ORDER BY u.id", (role, mid)).fetchone()
    c.close()
    return r[0]


def set_ended(app, mid):
    """M1 을 이음 연결 + 끝난 회의로(「✅ 종료됨 · 15:40」 꼬리표가 나오게) — 시험 DB 만."""
    p = os.path.join(APPDIR, app, "data", "knk.db")
    c = sqlite3.connect(p)
    c.execute("UPDATE meetings SET msg_meeting_id=777, ended_at='2026-10-27 15:40:00' WHERE id=?", (mid,))
    c.commit()
    c.close()


def md5(app, rel):
    return hashlib.md5(io.open(os.path.join(APPDIR, app, "app", rel), "rb").read()).hexdigest()


def rd(app, rel):
    return io.open(os.path.join(APPDIR, app, "app", rel), encoding="utf-8").read()


def walk(app):
    root = os.path.join(APPDIR, app, "app")
    out = {}
    for d, _dirs, files in os.walk(root):
        if "__pycache__" in d:
            continue
        for f in files:
            if f.endswith((".pyc", ".bak_z1198")):
                continue
            full = os.path.join(d, f)
            out[os.path.relpath(full, root).replace("\\", "/")] = hashlib.md5(io.open(full, "rb").read()).hexdigest()
    return out


def diff(a, b):
    return [d for d in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0) if d[:1] in "+-" and not d.startswith(("+++", "---"))]


print("== ① 파일 ==")
WB, WN = walk("app_base"), walk("app_new")
changed = sorted(k for k in set(WB) | set(WN) if WB.get(k) != WN.get(k))
chk("바뀐 파일 = 두 화면 파일뿐", changed == ["templates/meeting_form.html", "templates/voice_note_form.html"], str(changed))
dm = diff(rd("app_base", "templates/meeting_form.html"), rd("app_new", "templates/meeting_form.html"))
rem = [x for x in dm if x.startswith("-")]
chk("회의록 화면 뺀 줄 = 인라인 flex div 한 줄", len(rem) == 1 and 'style="display:flex;gap:10px;"' in rem[0], str(rem)[:160])
chk("회의록 화면 더한 줄에 class·nowrap·flex-wrap", any("mf-head-acts" in x and "class=" in x for x in dm) and any("white-space:nowrap" in x for x in dm) and any("flex-wrap:wrap" in x for x in dm))
dv = diff(rd("app_base", "templates/voice_note_form.html"), rd("app_new", "templates/voice_note_form.html"))
chk("메모 화면 뺀 줄 0 · 더한 줄에 .vn-acts .btn nowrap", not [x for x in dv if x.startswith("-")] and any(".vn-acts .btn" in x and "nowrap" in x for x in dv), "더함 %d" % len(dv))
chk("두 화면 파일에 z1198 표시", "z1198" in rd("app_new", "templates/meeting_form.html") and "z1198" in rd("app_new", "templates/voice_note_form.html"))

print("== 서버 두 벌 ==")
PRS = {}
SEED = {}
for app in ("app_base", "app_new"):
    PRS[app], SEED[app] = start(app)
    set_ended(app, SEED[app]["ids"]["M1"])
    print("  %s 포트 %d · ids %s" % (app, PORTS[app], SEED[app]["ids"]))

from playwright.sync_api import sync_playwright   # noqa: E402

JS = """
(sel) => {
  const box = document.querySelector(sel);
  if (!box) return {err: 'no ' + sel};
  const items = Array.from(box.querySelectorAll('.btn, .mf-ended')).filter(b => b.offsetParent !== null && !b.hidden);
  const rows = {};
  const out = items.map(b => { const r = b.getBoundingClientRect(); const cs = getComputedStyle(b);
    const top = Math.round(r.top); (rows[top] = rows[top] || []).push(Math.round(r.height));
    return {t: (b.textContent || '').trim().replace(/\\s+/g, ' '), w: Math.round(r.width), h: Math.round(r.height), top, ws: cs.whiteSpace}; });
  const bcs = getComputedStyle(box);
  const end = document.querySelector('#btnEndMeeting'); const tag = document.querySelector('#mtgEndedTag');
  return {items: out, rows: Object.keys(rows).map(Number).sort((a, b) => a - b), wrap: bcs.flexWrap, display: bcs.display,
          over: document.documentElement.scrollWidth > window.innerWidth, innerW: window.innerWidth, scrollW: document.documentElement.scrollWidth,
          endHidden: !end || end.hidden || end.offsetParent === null, tagText: tag && tag.offsetParent !== null ? tag.textContent.trim() : null};
}
"""
WIDTHS = (360, 390, 412, 720, 904, 1280)


def measure(br, app, uid, path, sel, w, shot=None):
    base = "http://127.0.0.1:%d" % PORTS[app]
    ctx = br.new_context(viewport={"width": w, "height": 820}, device_scale_factor=2, is_mobile=(w < 800), has_touch=(w < 800))
    ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": base}])
    pg = ctx.new_page()
    pg.goto(base + path, wait_until="networkidle")
    pg.wait_for_timeout(350)
    m = pg.evaluate(JS, sel)
    if shot:
        pg.locator(".page-head").screenshot(path=os.path.join(SHOTS, shot))
    ctx.close()
    return m


def rows_ok(m):
    """같은 줄은 위가 같고(이미 top 으로 묶음) · 줄 사이 간격이 서로 같다(±1) · 모든 단추 높이가 같다(±1)"""
    hs = [i["h"] for i in m["items"]]
    if not hs:
        return False, "단추 0"
    gaps = [b - a for a, b in zip(m["rows"], m["rows"][1:])]
    same_gap = all(abs(g - gaps[0]) <= 1 for g in gaps) if gaps else True
    return (max(hs) - min(hs) <= 1 and same_gap), "높이 %s · 줄 위 %s" % (sorted(set(hs)), m["rows"])


with sync_playwright() as p:
    br = p.chromium.launch()
    me = SEED["app_new"]["me"]
    mem = first_user("app_new", "member", SEED["app_new"]["ids"]["M1"])
    M1, V1 = SEED["app_new"]["ids"]["M1"], SEED["app_new"]["ids"]["V1"]
    EXPECT_TXT = {"← 목록", "📄 회의록 양식", "📊 한눈에 보기", "🗣 통역 대조", "🗑 삭제", "✅ 종료됨 · 15:40"}
    print("== ② 새것 · 회의록 상세 위 단추 줄 ==")
    for w in WIDTHS:
        m = measure(br, "app_new", me, "/meetings/%d" % M1, ".mf-head-acts", w, shot=("new_meeting_%d.png" % w if w != 1280 else None))
        if "err" in m:
            chk("폭 %d: 단추 줄 있음" % w, False, m["err"])
            continue
        hs = [i["h"] for i in m["items"]]
        ok_rows, why = rows_ok(m)
        limit = 3 if w <= 480 else (2 if w < 1280 else 1)
        chk("폭 %d: 글자 안 꺾임(높이 ≤44 · 같은 높이) · 줄 %d개(≤%d) · 간격 같음" % (w, len(m["rows"]), limit),
            max(hs) <= 44 and ok_rows and len(m["rows"]) <= limit, why)
        chk("폭 %d: nowrap · flex-wrap wrap · 가로 넘침 없음" % w,
            all(i["ws"] == "nowrap" for i in m["items"]) and m["wrap"] == "wrap" and not m["over"],
            "wrap=%s 넘침=%s(%s/%s)" % (m["wrap"], m["over"], m["scrollW"], m["innerW"]))
        if w == 360:
            chk("폭 360: 단추 글자 6개 그대로 · 종료됨 꼬리표 보임 · ⏹ 종료 단추 숨음",
                {i["t"] for i in m["items"]} == EXPECT_TXT and m["endHidden"] and (m["tagText"] or "").startswith("✅"),
                str([i["t"] for i in m["items"]]))
            print("    360 단추:", [(i["t"], i["w"], i["h"], i["top"]) for i in m["items"]])
    m = measure(br, "app_new", mem, "/meetings/%d" % M1, ".mf-head-acts", 360)
    chk("직원 눈(360): 통역 대조·삭제 없음 · 남은 단추 한 줄 높이", "err" not in m and not any("통역" in i["t"] or "삭제" in i["t"] for i in m["items"])
        and m["items"] and max(i["h"] for i in m["items"]) <= 44, str([i["t"] for i in m.get("items", [])]))
    print("== ③ 새것 · 음성 메모 상세 위 단추 줄 ==")
    for w in (360, 390, 412, 904):
        m = measure(br, "app_new", me, "/voice-notes/%d" % V1, ".vn-acts", w, shot=("new_memo_%d.png" % w if w in (360, 904) else None))
        if "err" in m:
            chk("메모 폭 %d: 단추 줄 있음" % w, False, m["err"])
            continue
        hs = [i["h"] for i in m["items"]]
        ok_rows, why = rows_ok(m)
        chk("메모 폭 %d: 단추 %d개 같은 높이(≤44) · nowrap · 줄바꿈 · 넘침 없음" % (w, len(m["items"])),
            len(m["items"]) == 5 and max(hs) <= 44 and ok_rows and all(i["ws"] == "nowrap" for i in m["items"]) and m["wrap"] == "wrap" and not m["over"], why)
    print("== ④ 바탕(운영 그대로) — 검사기가 잡는가 ==")
    mb = measure(br, "app_base", SEED["app_base"]["me"], "/meetings/%d" % SEED["app_base"]["ids"]["M1"], ".page-head > div:nth-child(2)", 360, shot="base_meeting_360.png")
    chk("바탕 360: 단추가 꺾인다(높이 > 60) — 검사기가 잡음", "err" not in mb and max(i["h"] for i in mb["items"]) > 60, str([(i["t"], i["h"]) for i in mb.get("items", [])]))
    mv = measure(br, "app_base", SEED["app_base"]["me"], "/voice-notes/%d" % SEED["app_base"]["ids"]["V1"], ".vn-acts", 904)
    chk("바탕 메모: 단추 높이가 서로 다르다(40/37) — 검사기가 잡음", "err" not in mv and len({i["h"] for i in mv["items"]}) > 1, str(sorted({i["h"] for i in mv.get("items", [])})))
    br.close()

for app, pr in PRS.items():
    try:
        pr.terminate()
    except Exception:
        pass
print("q98 %d/%d" % (OK, N), "· 실패:" if FAILS else "", FAILS if FAILS else "")
sys.exit(0 if OK == N else 1)
