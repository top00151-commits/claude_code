# -*- coding: utf-8 -*-
"""z1177 검사기 — 「AI가 … 정리하는 중」 **진행 칸**(회의록·음성 메모) + 🎤 음성 메모 **오른쪽 여백**.

대표 지시 2026-10-13 (사진 두 장)
  1. 「"AI가 회의 내용을 다시 정리하는 중…" 이부분이 **확실하게 표현**이 됐으면 좋겠어 ..
      이부분은 **음성메모 부분도 동일하게** 처리해줘」
  2. 「음성메모 **오른쪽 여백 삭제**해줘.. 필요없는 부분인데」

무엇이 잘못돼 있었나
  1. 정리하는 동안 보이는 것이 **12px 회색 글 한 줄**뿐 — 움직임도, 몇 초째인지도 없다.
     그 밑에는 옛 정리가 그대로 보여 **멈춘 것처럼** 보였다.
  2. 음성 메모 화면에만 `max-width: 900px` — 넓은 화면에서 오른쪽이 통째로 비었다(목록 화면은 꽉 찬다).

재는 것 (앱 두 벌 · 가짜 AI 를 **느리게** 6초 · 진짜 브라우저)
  🗓 회의록
   M① 🔴 반대 시험 — 운영 그대로: 진행 칸 **없음** · 상태 글은 12px · 회색(그 수치를 적어 둔다)
   M② 누르면 1초 안에 **파란 진행 칸** — 굵은 글 14px 이상 · 도는 표시(애니메이션) · 흐르는 막대
   M③ ⏱ 시계가 **간다**(2초 뒤 2초 이상 늘어남) · 안내에 「창을 닫아도」 · 「실패」「오래」 낱말 없음
   M④ 그동안 옛 정리는 **흐리게** · 같은 글이 두 번 보이지 않게 위 상태 줄은 **잠깐 숨김**
       🔵 그래도 그 줄의 글은 그대로 들어 있다(z1175 시험이 그 글을 읽는다)
   M⑤ 끝나면 **초록 ✅ + 걸린 시간** · 정리가 새것으로 · 흐림 풀림 · 단추 다시 눌림
   M⑥ 10초 뒤 칸이 접히고 위 상태 줄에 「완료」가 **남는다**
   M⑦ 🔴 실패하면 **빨강 ⚠** + 까닭 · 옛 정리 **그대로** · 흐림 풀림 · 단추 다시 눌림
   M⑧ 🔴 **정리 도중에 다시 열면**(새로고침) 진행 칸이 **다시 뜨고** 시계가 **실제로 지난 시간**부터 간다
   M⑨ 🔴 **창을 닫아도 끝까지 된다** — 누르고 바로 창을 닫았다가 다시 열면 정리가 **새것** (안내 글의 약속)
   M⑩ 서버 상태 답: 도는 동안 `elapsed`(정수) · 시작 시각(t0)은 **밖으로 안 나간다**
   M⑪ 🔴 못 고치는 사람 화면엔 칸이 **없다** · 콘솔 오류 0 · 베트남어 안내 있음 · 「위」 뺀 완료 글
   M⑫ 🔴 정리 도중에 **링크로 다른 회의로 넘어가면**(WORKS 는 본문만 갈아끼운다) 넘어간 화면을 **안 건드린다**
       · 서버 일은 끝까지 간다(앞 회의 정리가 새것) — 회의록은 z1106 장치가 이미 막고 있음을 확인
  🎤 음성 메모
   V① 🔴 반대 시험 — 운영 그대로: 오른쪽 빈 곳이 **300px 넘게** · 진행 칸 없음
   V② 새것: 오른쪽 빈 곳이 **목록 화면과 같다**(꽉 참) — 1600·1280 두 폭에서
   V③ 누르면 **같은 진행 칸**(회의록과 바탕색·글 크기 같음) · 「🔄 다시 정리」 잠김 · 옛 정리 흐리게
   V④ 위 칸 글(vnSt)은 **그대로** 「정리하는 중…」
   V⑤ 끝나면 초록 ✅ · 「정리가 끝났습니다 ✓」 · 정리 새것 · 📋 복사 켜짐 · 단추 풀림
   V⑥ 🔴 실패하면 빨강 ⚠ · 옛 정리 그대로
   V⑦ 🔴 정리 도중에 다시 열면 칸이 다시 뜨고 시계가 이어진다 · 단추 잠김
   V⑧ 🔴 창을 닫아도 끝까지 된다
   V⑨ 서버 상태 답: `elapsed` · t0 안 나감
   V⑩ 📱 휴대폰 폭(375): 옆으로 밀리지 않는다 · 칸이 화면 안
   V⑪ z1167 회귀 — 시안 문서 흔적 0 · 콘솔 오류 0
   V⑫ 🔴 정리 도중에 링크로 다른 메모로 넘어가면 —
       **반대 시험**: 운영 그대로는 넘어간 메모 화면에 **앞 메모의 정리·원문을 써 넣는다**(원문 저장을 누르면 엉뚱한 메모에 저장)
       새것: 넘어간 메모는 **그대로** · 진행 칸 안 뜸 · 단추 눌림 · 서버 일은 끝까지(앞 메모에 새 정리 저장)
       🗓 회의록은 z1106 에 같은 까닭으로 막았는데 🎤 음성 메모(z1144)는 빠뜨렸었다
  📸 대표께 보여 드릴 사진 — shots/ 에 저장

쓰는 법: py ai_busy_ui.py [app_base·app_new 가 있는 폴더]
판정: **종료코드**(0=통과) + 요약 줄.
"""
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1] if len(sys.argv) > 1 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
SLOW = 6.0
PM_B, PM_N, PV_B, PV_N = 8995, 8996, 8997, 8998
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
    """🔴 포트 주인을 멈추고 **비었는지 확인**한다(옛 서버가 옛 코드를 시험한 적 있다 · 09-21)."""
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


def boot(run, app, port):
    freeport(port)
    sp = os.path.join(HERE, "seed_%d.json" % port)
    if os.path.exists(sp):
        os.remove(sp)
    lp = os.path.join(APPDIR, "srv_%d.log" % port)
    pr = subprocess.Popen([P313, os.path.join(HERE, run), os.path.join(APPDIR, app), str(port), str(SLOW)],
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


def page_for(br, port, uid, w=1280, h=1000):
    ctx = br.new_context(viewport={"width": w, "height": h})
    ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": "http://127.0.0.1:%d" % port}])
    pg = ctx.new_page()
    pg.add_init_script("try{localStorage.setItem('knk_works_install_hint_never','1');}catch(e){}")
    errs = []
    pg.on("console", lambda m: errs.append("console: " + m.text[:160]) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:160]))
    return ctx, pg, errs


def secs_of(txt):
    m = re.search(r"(\d+):(\d\d)", txt or "")
    return int(m.group(1)) * 60 + int(m.group(2)) if m else -1


#  진행 칸 하나를 통째로 읽는다
PANEL = """(id) => { var h = document.getElementById(id); if (!h) return null;
  var cs = getComputedStyle(h), t = h.querySelector('.kab-t'), s = h.querySelector('.kab-s'),
      ic = h.querySelector('.kab-ic'), bar = h.querySelector('.kab-bar > i'), ck = h.querySelector('.kab-clk');
  var r = h.getBoundingClientRect();
  return { shown: !h.hidden && cs.display !== 'none', cls: h.className, bg: cs.backgroundColor,
           title: t ? t.textContent : '', sub: s ? s.textContent : '', clock: ck ? ck.textContent : '',
           tfs: t ? parseFloat(getComputedStyle(t).fontSize) : 0, tfw: t ? +getComputedStyle(t).fontWeight : 0,
           tcol: t ? getComputedStyle(t).color : '',
           spin: ic ? getComputedStyle(ic).animationName : '', slide: bar ? getComputedStyle(bar).animationName : '',
           role: h.getAttribute('role'), live: h.getAttribute('aria-live'),
           left: r.left, right: r.right, width: r.width }; }"""
OPAC = "(id) => { var e = document.getElementById(id); return e ? +getComputedStyle(e).opacity : -1; }"
#  main 안 내용의 오른쪽 끝 ↔ **화면** 오른쪽 끝 (= 오른쪽 빈 곳)
#  🔴 운영의 900px 상한은 main **자체**에 걸려 있다 → main 의 오른쪽이 아니라 화면 오른쪽에서 잰다
GAP = """() => { var m = document.querySelector('main.main') || document.querySelector('main');
  var right = 0;
  Array.prototype.forEach.call(m.children, function(c){
    if (getComputedStyle(c).display === 'none') return;
    var r = c.getBoundingClientRect(); if (r.width > 0 && r.right > right) right = r.right; });
  return { gap: Math.round(window.innerWidth - right), main: Math.round(m.getBoundingClientRect().width),
           right: Math.round(right) }; }"""


def wait_panel(pg, pid, cond, sec):
    t0 = time.time()
    while time.time() - t0 < sec:
        p = pg.evaluate(PANEL, pid)
        if p and cond(p):
            return p, time.time() - t0
        pg.wait_for_timeout(150)
    return pg.evaluate(PANEL, pid), time.time() - t0


#  WORKS 의 링크 이동(spa_nav — 본문만 갈아끼운다)을 그대로 일으킨다. 진짜 링크를 만들어 누른다.
#  🔴 「전체 이동」으로 빠지면 이 시험은 헛것을 잰다 → 표식(window.__spaMark)이 남아 있는지로 가린다.
def spa_go(pg, path, ready_js):
    pg.evaluate("""(p) => { window.__spaMark = 1; var a = document.createElement('a'); a.href = p;
        a.textContent = 'go'; (document.querySelector('main') || document.body).appendChild(a); a.click(); }""", path)
    pg.wait_for_function(ready_js, timeout=20000)
    return pg.evaluate("() => window.__spaMark === 1")


def kill(*prs):
    for pr in prs:
        try:
            pr.terminate()
        except Exception:
            pass


# ── 번역 글 (서버 안 띄움) ─────────────────────────────────────
print("── 번역 글 ──")
_sp = importlib.util.spec_from_file_location("i18n_z1177", os.path.join(APPDIR, "app_new", "app", "i18n.py"))
_i = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(_i)
_sp0 = importlib.util.spec_from_file_location("i18n_z1177b", os.path.join(APPDIR, "app_base", "app", "i18n.py"))
_i0 = importlib.util.module_from_spec(_sp0)
_sp0.loader.exec_module(_i0)
H = _i.T.get("mf_ai_hint") or {}
chk("새 글 mf_ai_hint 한국어", "창을 닫아도" in H.get("ko", ""), H)
chk("새 글 mf_ai_hint 베트남어(한글 0)", bool(H.get("vi")) and not re.search("[가-힣]", H.get("vi", "")), H.get("vi"))
chk("안내에 「실패」「오래」 낱말이 없다(옛 시험이 그 낱말로 판정한다)",
    not any(w in H.get("ko", "") for w in ("실패", "오래")))
RD = _i.T["mf_re_done"]
chk("완료 글에서 「위」를 뺐다(정리 글 **위**에도 뜬다)", "위 " not in RD["ko"] and "ở trên" not in RD["vi"], RD)
chk("완료 글에 「완료」는 그대로(옛 시험이 그 낱말을 본다)", "완료" in RD["ko"], RD["ko"])
#  🔴 z1178 회귀에서 고침: 처음엔 「글 수 +1」로 **숫자를 못박았다** → 뒤 변경(z1178 검색 +17)을 얹은 코드로
#     돌리면 969 → 987 이 되어 **제품은 멀쩡한데 깨졌다**. 뜻(z1177 의 새 글이 있다 · 사라진 글 0)만 본다.
chk("새로 생긴 번역 글에 mf_ai_hint 가 있다 (%d → %d)" % (len(_i0.T), len(_i.T)),
    "mf_ai_hint" in (set(_i.T) - set(_i0.T)))
gone_keys = set(_i0.T) - set(_i.T)
chk("사라진 번역 글 0", not gone_keys, gone_keys)
STEP_AI = _i.T["mf_step_ai"]["ko"]

MSHOT = {}
pmb = pmn = pvb = pvn = None
try:
    with sync_playwright() as p:
        br = p.chromium.launch()

        # ═════════════════════ 🗓 회의록 ═════════════════════
        print("\n두 벌 띄우는 중… (🗓 회의록 · 가짜 AI %.0f초)" % SLOW)
        pmb, sb = boot("run_mtg4_app.py", "app_base", PM_B)
        pmn, sn = boot("run_mtg4_app.py", "app_new", PM_N)

        print("\n── M① 🔴 반대 시험: 운영 그대로 ──")
        cb, gb, eb = page_for(br, PM_B, sb["me"])
        gb.goto("http://127.0.0.1:%d/meetings/%d" % (PM_B, sb["mine"]), wait_until="domcontentloaded")
        gb.wait_for_selector("#btnExtractTop", timeout=20000)
        chk("운영: 진행 칸 **없음**", gb.locator("#aiBusy").count() == 0 and gb.locator(".kab").count() == 0)
        gb.click("#btnExtractTop")
        gb.wait_for_timeout(1500)
        st = gb.evaluate("""() => { var e = document.getElementById('sumSt2'), cs = getComputedStyle(e);
          return { t: e.textContent, fs: parseFloat(cs.fontSize), fw: +cs.fontWeight, col: cs.color }; }""")
        chk("운영: 그동안 보이는 건 글 한 줄 「%s」" % st["t"][:30], "정리하는 중" in st["t"], st)
        chk("운영: 그 글은 **12px** (지금 %.1fpx) · 굵기 %d · 색 %s" % (st["fs"], st["fw"], st["col"]),
            st["fs"] <= 12.5, st)
        chk("운영: 옛 정리는 **흐려지지 않는다**(멈춘 것처럼 보인 까닭)", gb.evaluate(OPAC, "mtgSummary") == 1)
        gb.locator("#secSummary").screenshot(path=os.path.join(SHOTS, "1_회의록_운영_정리중.png"))
        cb.close()

        print("\n── M②③④ 새것: 누르면 파란 진행 칸 ──")
        cn, gn, en = page_for(br, PM_N, sn["me"])
        gn.goto("http://127.0.0.1:%d/meetings/%d" % (PM_N, sn["mine"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#btnExtractTop", timeout=20000)
        p0 = gn.evaluate(PANEL, "aiBusy")
        chk("칸은 있고, 누르기 전엔 **안 보인다**", p0 is not None and not p0["shown"], p0)
        gn.click("#btnExtractTop")
        p1, w1 = wait_panel(gn, "aiBusy", lambda q: q["shown"], 3)
        chk("🔵 누르고 **%.1f초** 만에 진행 칸이 뜬다" % w1, p1["shown"] and w1 < 1.0, p1)
        chk("제목 = 「%s」" % p1["title"], p1["title"] == "빅터AI가 회의 내용을 다시 정리하는 중…", p1["title"])
        chk("🔵 글이 **크고 굵다** (%.1fpx · %d — 전엔 12px)" % (p1["tfs"], p1["tfw"]),
            p1["tfs"] >= 14 and p1["tfw"] >= 700, p1)
        chk("파란 바탕 (%s)" % p1["bg"], p1["bg"] == "rgb(239, 246, 255)", p1["bg"])
        chk("🔵 **도는 표시**가 돈다 (animation=%s)" % p1["spin"], p1["spin"] == "kabspin", p1["spin"])
        chk("🔵 **흐르는 막대**가 흐른다 (animation=%s)" % p1["slide"], p1["slide"] == "kabslide", p1["slide"])
        chk("화면 읽기 프로그램용 표시(role=status · aria-live)", p1["role"] == "status" and p1["live"] == "polite", p1)
        chk("안내 「%s」" % p1["sub"][:60], "창을 닫아도" in p1["sub"], p1["sub"])
        chk("안내에 「실패」「오래」 없음", not any(w in p1["sub"] for w in ("실패", "오래")), p1["sub"])
        a = secs_of(p1["clock"])
        gn.wait_for_timeout(2300)
        p2 = gn.evaluate(PANEL, "aiBusy")
        b = secs_of(p2["clock"])
        chk("🔵 ⏱ 시계가 **간다** (%s → %s)" % (p1["clock"].strip(), p2["clock"].strip()), a >= 0 and b - a >= 2, (a, b))
        chk("🔵 옛 정리는 **흐리게** (불투명도 %.2f)" % gn.evaluate(OPAC, "mtgSummary"),
            gn.evaluate(OPAC, "mtgSummary") < 0.5)
        hid = gn.evaluate("() => getComputedStyle(document.getElementById('sumSt2')).display")
        chk("같은 글이 두 번 안 보이게 위 상태 줄은 잠깐 숨김 (display=%s)" % hid, hid == "none")
        chk("🔵 그래도 그 줄에 글은 들어 있다(z1175 시험이 읽는다)",
            "정리하는 중" in gn.evaluate("() => document.getElementById('sumSt2').textContent"))
        chk("누르는 동안 두 단추 모두 잠김",
            gn.locator("#btnExtractTop").is_disabled() and gn.evaluate(
                "() => document.getElementById('btnExtract').disabled") is True)
        js = gn.request.get("http://127.0.0.1:%d/api/meeting/%d/extract-status" % (PM_N, sn["mine"])).json()
        chk("M⑩ 서버 상태 답에 `elapsed`(정수 %r)" % js.get("elapsed"),
            js.get("state") == "running" and isinstance(js.get("elapsed"), int) and js["elapsed"] >= 2, js)
        chk("M⑩ 시작 시각(t0)은 밖으로 안 나간다", "t0" not in js, list(js))
        gn.locator("#secSummary").screenshot(path=os.path.join(SHOTS, "2_회의록_새_정리중.png"))

        print("\n── M⑤⑥ 끝나면 초록 · 10초 뒤 접힘 ──")
        p3, w3 = wait_panel(gn, "aiBusy", lambda q: "ok" in q["cls"].split() or "err" in q["cls"].split(), 30)
        chk("🔵 **초록 ✅** (%.1f초 더 기다림)" % w3, "ok" in p3["cls"].split(), p3["cls"])
        chk("완료 글 「%s」" % p3["title"], "완료" in p3["title"] and "위 " not in p3["title"], p3["title"])
        chk("🔵 걸린 시간 ⏱ %s (가짜 AI %.0f초)" % (p3["clock"].strip(), SLOW), secs_of(p3["clock"]) >= SLOW - 1, p3)
        chk("초록 바탕 (%s)" % p3["bg"], p3["bg"] == "rgb(240, 253, 244)", p3["bg"])
        chk("도는 표시는 멈췄다", p3["spin"] in ("none", ""), p3["spin"])
        chk("흐림 풀림", gn.evaluate(OPAC, "mtgSummary") == 1)
        s_after = gn.inner_text("#mtgSummary")
        chk("정리가 **새것** 「%s」" % s_after.strip()[:30], "가짜 정리" in s_after and "옛 정리" not in s_after, s_after[:60])
        chk("단추 다시 눌림", gn.locator("#btnExtractTop").is_enabled())
        whole = gn.inner_text("body")
        chk("🔴 사람이 적은 결정·할 일 **그대로**", "사람이 적은 결정" in whole and "사람이 적은 할 일" in whole)
        gn.locator("#secSummary").screenshot(path=os.path.join(SHOTS, "3_회의록_새_완료.png"))
        p4, w4 = wait_panel(gn, "aiBusy", lambda q: not q["shown"], 13)
        chk("10초 뒤 칸이 접힌다 (%.1f초)" % w4, not p4["shown"], p4)
        vis = gn.evaluate("() => { var e = document.getElementById('sumSt2'); "
                          "return [getComputedStyle(e).display, e.textContent]; }")
        chk("🔵 접힌 뒤 위 상태 줄에 「완료」가 **남는다** (%s)" % vis[1][:24], vis[0] != "none" and "완료" in vis[1], vis)

        print("\n── M⑦ 🔴 실패하면 빨강 ──")
        gn.goto("http://127.0.0.1:%d/meetings/%d" % (PM_N, sn["failm"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#btnExtractTop", timeout=20000)
        gn.click("#btnExtractTop")
        wait_panel(gn, "aiBusy", lambda q: q["shown"], 3)
        p5, w5 = wait_panel(gn, "aiBusy", lambda q: "err" in q["cls"].split() or "ok" in q["cls"].split(), 30)
        chk("🔴 **빨강 ⚠** (%.1f초)" % w5, "err" in p5["cls"].split(), p5["cls"])
        chk("까닭이 보인다 「%s」" % p5["title"][:30], "가짜 실패" in p5["title"], p5["title"])
        chk("빨간 바탕 (%s)" % p5["bg"], p5["bg"] == "rgb(254, 242, 242)", p5["bg"])
        chk("🔴 옛 정리 **그대로**", "실패 전 옛 정리" in gn.inner_text("#mtgSummary"))
        chk("흐림 풀림", gn.evaluate(OPAC, "mtgSummary") == 1)
        chk("단추 다시 눌림", gn.locator("#btnExtractTop").is_enabled())
        gn.locator("#secSummary").screenshot(path=os.path.join(SHOTS, "4_회의록_새_실패.png"))
        mtg_err = list(en)
        cn.close()

        print("\n── M⑧ 🔴 정리 도중에 **다시 열면** ──")
        cr, gr, er = page_for(br, PM_N, sn["me"])
        url2 = "http://127.0.0.1:%d/meetings/%d" % (PM_N, sn["mine2"])
        gr.goto(url2, wait_until="domcontentloaded")
        gr.wait_for_selector("#btnExtractTop", timeout=20000)
        gr.click("#btnExtractTop")
        wait_panel(gr, "aiBusy", lambda q: q["shown"], 3)
        gr.wait_for_timeout(2500)
        gr.reload(wait_until="domcontentloaded")
        gr.wait_for_selector("#mtgSummary", timeout=20000)
        p6, w6 = wait_panel(gr, "aiBusy", lambda q: q["shown"], 5)
        chk("🔵 다시 연 화면에도 진행 칸이 **다시 뜬다** (%.1f초)" % w6, p6["shown"], p6)
        chk("🔵 시계가 0 부터가 아니라 **실제로 지난 시간**부터 (%s)" % p6["clock"].strip(), secs_of(p6["clock"]) >= 2, p6)
        chk("제목은 「다시」 없는 글 「%s」" % p6["title"], p6["title"] == STEP_AI + "…", p6["title"])
        chk("다시 연 화면에서도 단추 잠김", gr.locator("#btnExtractTop").is_disabled())
        p7, w7 = wait_panel(gr, "aiBusy", lambda q: "ok" in q["cls"].split() or "err" in q["cls"].split(), 30)
        chk("끝까지 따라가 **초록 ✅**", "ok" in p7["cls"].split(), p7["cls"])
        s_r = gr.inner_text("#mtgSummary")
        chk("정리가 새것", "가짜 정리" in s_r, s_r[:50])

        print("\n── M⑨ 🔴 **창을 닫아도** 끝까지 된다 ──")
        before = gr.inner_text("#mtgSummary").strip()
        cr.close()
        cx, gx, ex = page_for(br, PM_N, sn["me"])
        gx.goto(url2, wait_until="domcontentloaded")
        gx.wait_for_selector("#btnExtractTop", timeout=20000)
        gx.click("#btnExtractTop")
        wait_panel(gx, "aiBusy", lambda q: q["shown"], 3)
        gx.wait_for_timeout(1000)
        cx.close()                                   # ← 누르고 바로 창을 닫는다
        time.sleep(SLOW + 3)
        cy, gy, ey = page_for(br, PM_N, sn["me"])
        gy.goto(url2, wait_until="domcontentloaded")
        gy.wait_for_selector("#mtgSummary", timeout=20000)
        after = gy.inner_text("#mtgSummary").strip()
        chk("🔵 다시 열면 정리가 **새것** (「%s」 → 「%s」)" % (before[-6:], after[-6:]),
            after != before and "가짜 정리" in after, (before, after))
        chk("다시 연 화면엔 진행 칸이 **없다**(이미 끝났으니)", not gy.evaluate(PANEL, "aiBusy")["shown"])
        cy.close()

        print("\n── M⑪ 못 고치는 사람 · 콘솔 ──")
        co, go, eo = page_for(br, PM_N, sn["other"])
        go.goto("http://127.0.0.1:%d/meetings/%d" % (PM_N, sn["mine"]), wait_until="domcontentloaded")
        go.wait_for_selector("#mtgSummary", timeout=20000)
        go.wait_for_timeout(800)
        chk("🔴 못 고치는 사람 화면엔 진행 칸이 **없다**", go.locator("#aiBusy").count() == 0)
        chk("그 화면도 콘솔 오류 0", not eo, eo[:2])
        co.close()
        chk("🗓 회의록 화면 콘솔 오류 0", not (mtg_err + er + ex + ey), (mtg_err + er + ex + ey)[:3])
        MSHOT["bg"], MSHOT["tfs"] = p1["bg"], p1["tfs"]

        print("\n── M⑫ 🔴 정리 도중에 **링크로 다른 회의로 넘어가면** — 넘어간 화면을 건드리지 않는다 ──")
        cs, gs, es = page_for(br, PM_N, sn["me"])
        gs.goto("http://127.0.0.1:%d/meetings/%d" % (PM_N, sn["mine"]), wait_until="domcontentloaded")
        gs.wait_for_selector("#btnExtractTop", timeout=20000)
        n0 = gs.request.get("http://127.0.0.1:%d/api/meeting/%d/extract-status" % (PM_N, sn["mine"])).json()
        gs.click("#btnExtractTop")
        wait_panel(gs, "aiBusy", lambda q: q["shown"], 3)
        spa = spa_go(gs, "/meetings/%d" % sn["failm"],
                     "() => { var t = document.getElementById('mtgTitle'); return t && t.value === '실패하는 회의'; }")
        chk("링크 이동이 **본문만 갈아끼우기**였다(전체 이동이면 이 시험은 헛것)", spa is True, spa)
        time.sleep(SLOW + 3)
        sx = gs.inner_text("#mtgSummary")
        chk("🔴 넘어간 회의의 정리는 **그대로** 「%s」" % sx.strip()[-12:], "실패 전 옛 정리" in sx and "가짜 정리" not in sx, sx[:60])
        chk("🔴 넘어간 회의에 앞 회의의 결정·할 일이 **안 들어왔다**", "가짜 결정" not in gs.inner_text("body"))
        px = gs.evaluate(PANEL, "aiBusy")
        chk("넘어간 회의 화면엔 진행 칸이 **안 떠 있다**", px is not None and not px["shown"], px)
        n1 = gs.request.get("http://127.0.0.1:%d/api/meeting/%d/extract-status" % (PM_N, sn["mine"])).json()
        #  🔴 같은 회의를 앞에서 이미 정리했다 → 「done」만으로는 이번 일이 돌았는지 모른다 → **글이 바뀌었나**로
        chk("🔵 서버 일은 끝까지 갔다 — 앞 회의 정리가 **새것**(「%s」 → 「%s」)"
            % ((n0.get("summary") or "")[-5:], (n1.get("summary") or "")[-5:]),
            n1.get("state") == "done" and (n1.get("summary") or "") != (n0.get("summary") or "")
            and "가짜 정리" in (n1.get("summary") or ""), (n0, n1))
        chk("그 화면 콘솔 오류 0", not es, es[:2])
        cs.close()
        kill(pmb, pmn)

        # ═════════════════════ 🎤 음성 메모 ═════════════════════
        print("\n두 벌 띄우는 중… (🎤 음성 메모 · 가짜 AI %.0f초)" % SLOW)
        pvb, vb = boot("run_vn4_app.py", "app_base", PV_B)
        pvn, vn = boot("run_vn4_app.py", "app_new", PV_N)

        print("\n── V①② 오른쪽 여백 ──")
        for w in (1600, 1280):
            c1, g1, _ = page_for(br, PV_B, vb["me"], w=w)
            g1.goto("http://127.0.0.1:%d/voice-notes/%d" % (PV_B, vb["mine"]), wait_until="domcontentloaded")
            g1.wait_for_selector("#vnSumBox", timeout=20000)
            gb_ = g1.evaluate(GAP)
            if w == 1600:
                chk("🔴 운영: 진행 칸 없음", g1.locator("#vnAiBusy").count() == 0)
                g1.screenshot(path=os.path.join(SHOTS, "5_음성메모_운영_%d.png" % w))
            c1.close()
            c2, g2, _ = page_for(br, PV_N, vn["me"], w=w)
            g2.goto("http://127.0.0.1:%d/voice-notes" % PV_N, wait_until="domcontentloaded")
            g2.wait_for_timeout(600)
            gl = g2.evaluate(GAP)
            g2.goto("http://127.0.0.1:%d/voice-notes/%d" % (PV_N, vn["mine"]), wait_until="domcontentloaded")
            g2.wait_for_selector("#vnSumBox", timeout=20000)
            gn_ = g2.evaluate(GAP)
            print("   [%d폭] 운영 빈 곳 %dpx · 새것 %dpx · 목록 화면 %dpx (main 폭 %d)"
                  % (w, gb_["gap"], gn_["gap"], gl["gap"], gn_["main"]))
            if w == 1600:
                chk("🔴 반대 시험 — 운영은 오른쪽이 **%dpx** 빈다" % gb_["gap"], gb_["gap"] >= 300, gb_)
            else:
                chk("🔴 반대 시험 — 운영은 1280 폭에서도 **%dpx** 빈다" % gb_["gap"], gb_["gap"] >= 100, gb_)
            chk("🔵 새것은 목록 화면과 같다 (%d vs %dpx)" % (gn_["gap"], gl["gap"]),
                abs(gn_["gap"] - gl["gap"]) <= 4 and gn_["gap"] < 80, (gn_, gl))
            c2.close()

        print("\n── V③④⑤ 누르면 같은 진행 칸 ──")
        cv, gv, ev = page_for(br, PV_N, vn["me"], w=1600)
        gv.goto("http://127.0.0.1:%d/voice-notes/%d" % (PV_N, vn["mine"]), wait_until="domcontentloaded")
        gv.wait_for_selector("#vnRedo", timeout=20000)
        q0 = gv.evaluate(PANEL, "vnAiBusy")
        chk("칸은 있고 누르기 전엔 안 보인다", q0 is not None and not q0["shown"], q0)
        gv.click("#vnRedo")
        q1, x1 = wait_panel(gv, "vnAiBusy", lambda q: q["shown"], 3)
        chk("🔵 누르고 %.1f초 만에 뜬다" % x1, q1["shown"] and x1 < 1.0, q1)
        chk("제목 「%s」" % q1["title"], q1["title"] == "빅터AI가 녹음 내용을 다시 정리하는 중…", q1["title"])
        chk("🔵 회의록과 **같은 모양** (바탕 %s · 글 %.1fpx)" % (q1["bg"], q1["tfs"]),
            q1["bg"] == MSHOT["bg"] and q1["tfs"] == MSHOT["tfs"], (q1, MSHOT))
        chk("도는 표시 · 흐르는 막대", q1["spin"] == "kabspin" and q1["slide"] == "kabslide", q1)
        chk("안내 「%s」" % q1["sub"][:50], "창을 닫아도" in q1["sub"] and "녹음" in q1["sub"], q1["sub"])
        chk("🔵 「🔄 다시 정리」 잠김", gv.locator("#vnRedo").is_disabled())
        chk("V④ 위 칸 글은 그대로 「%s」" % gv.inner_text("#vnSt")[:20], "정리하는 중" in gv.inner_text("#vnSt"))
        a = secs_of(q1["clock"])
        gv.wait_for_timeout(2300)
        q2 = gv.evaluate(PANEL, "vnAiBusy")
        chk("⏱ 시계가 간다 (%s → %s)" % (q1["clock"].strip(), q2["clock"].strip()), secs_of(q2["clock"]) - a >= 2)
        #  🔵 흐림은 0.25초에 걸쳐 바뀐다 — 칸이 뜬 바로 그 순간에 재면 아직 1.00 이다(첫 판에서 그렇게 헛실패)
        #     → 회의록과 같이 **시계를 본 뒤**에 잰다
        chk("옛 정리 흐리게 (%.2f · kab-dim)" % gv.evaluate(OPAC, "vnSumBox"),
            gv.evaluate(OPAC, "vnSumBox") < 0.5
            and "kab-dim" in gv.evaluate("() => document.getElementById('vnSumBox').className"))
        jv = gv.request.get("http://127.0.0.1:%d/api/voice-note/%d/extract-status" % (PV_N, vn["mine"])).json()
        chk("V⑨ 서버 상태 답에 `elapsed`(%r) · t0 안 나감" % jv.get("elapsed"),
            jv.get("state") == "running" and isinstance(jv.get("elapsed"), int) and "t0" not in jv, jv)
        gv.screenshot(path=os.path.join(SHOTS, "6_음성메모_새_1600_정리중.png"))
        q3, x3 = wait_panel(gv, "vnAiBusy", lambda q: "ok" in q["cls"].split() or "err" in q["cls"].split(), 30)
        chk("🔵 초록 ✅", "ok" in q3["cls"].split(), q3["cls"])
        chk("완료 글 「%s」 · 걸린 시간 %s" % (q3["title"], q3["clock"].strip()),
            q3["title"] == "정리가 끝났습니다 ✓" and secs_of(q3["clock"]) >= SLOW - 1, q3)
        chk("위 칸 글 「%s」" % gv.inner_text("#vnSt"), "끝났습니다" in gv.inner_text("#vnSt"))
        sv_ = gv.inner_text("#vnSumBox")
        chk("정리 새것", "가짜 정리" in sv_ and "옛 정리" not in sv_, sv_[:50])
        chk("흐림 풀림 · 단추 풀림", gv.evaluate(OPAC, "vnSumBox") == 1 and gv.locator("#vnRedo").is_enabled())
        chk("📋 복사 켜짐(z1168)", gv.locator("#vnCopy").is_enabled())
        gv.locator("#vnSumSec").screenshot(path=os.path.join(SHOTS, "7_음성메모_새_완료.png"))

        print("\n── V⑥ 🔴 실패하면 빨강 ──")
        gv.goto("http://127.0.0.1:%d/voice-notes/%d" % (PV_N, vn["failn"]), wait_until="domcontentloaded")
        gv.wait_for_selector("#vnRedo", timeout=20000)
        gv.click("#vnRedo")
        wait_panel(gv, "vnAiBusy", lambda q: q["shown"], 3)
        q4, x4 = wait_panel(gv, "vnAiBusy", lambda q: "err" in q["cls"].split() or "ok" in q["cls"].split(), 30)
        chk("🔴 빨강 ⚠ 「%s」" % q4["title"][:30], "err" in q4["cls"].split() and "가짜 실패" in q4["title"], q4)
        chk("옛 정리 그대로", "실패 전 옛 정리" in gv.inner_text("#vnSumBox"))
        chk("위 칸 글에도 까닭", "가짜 실패" in gv.inner_text("#vnSt"), gv.inner_text("#vnSt"))
        chk("흐림 풀림 · 단추 풀림", gv.evaluate(OPAC, "vnSumBox") == 1 and gv.locator("#vnRedo").is_enabled())
        vn_err = list(ev)
        cv.close()

        print("\n── V⑦ 🔴 정리 도중에 다시 열면 ──")
        cr, gr, er2 = page_for(br, PV_N, vn["me"])
        u2 = "http://127.0.0.1:%d/voice-notes/%d" % (PV_N, vn["mine2"])
        gr.goto(u2, wait_until="domcontentloaded")
        gr.wait_for_selector("#vnRedo", timeout=20000)
        gr.click("#vnRedo")
        wait_panel(gr, "vnAiBusy", lambda q: q["shown"], 3)
        gr.wait_for_timeout(2500)
        gr.reload(wait_until="domcontentloaded")
        gr.wait_for_selector("#vnSumBox", timeout=20000)
        q5, x5 = wait_panel(gr, "vnAiBusy", lambda q: q["shown"], 5)
        chk("🔵 다시 연 화면에도 진행 칸 (%.1f초)" % x5, q5["shown"], q5)
        chk("🔵 시계가 실제로 지난 시간부터 (%s)" % q5["clock"].strip(), secs_of(q5["clock"]) >= 2, q5)
        chk("「🔄 다시 정리」 잠김", gr.locator("#vnRedo").is_disabled())
        q6, _ = wait_panel(gr, "vnAiBusy", lambda q: "ok" in q["cls"].split() or "err" in q["cls"].split(), 30)
        chk("끝까지 따라가 초록 ✅", "ok" in q6["cls"].split(), q6["cls"])
        before = gr.inner_text("#vnSumBox").strip()
        cr.close()

        print("\n── V⑧ 🔴 창을 닫아도 끝까지 ──")
        cx, gx, ex2 = page_for(br, PV_N, vn["me"])
        gx.goto(u2, wait_until="domcontentloaded")
        gx.wait_for_selector("#vnRedo", timeout=20000)
        gx.click("#vnRedo")
        wait_panel(gx, "vnAiBusy", lambda q: q["shown"], 3)
        gx.wait_for_timeout(1000)
        cx.close()
        time.sleep(SLOW + 3)
        cy, gy, ey2 = page_for(br, PV_N, vn["me"])
        gy.goto(u2, wait_until="domcontentloaded")
        gy.wait_for_selector("#vnSumBox", timeout=20000)
        after = gy.inner_text("#vnSumBox").strip()
        nth = lambda s: (re.search(r"(\d+)번째", s) or re.search("", "")).group(0) or "?"
        chk("🔵 다시 열면 정리가 새것 (「%s」 → 「%s」)" % (nth(before), nth(after)),
            after != before and "가짜 정리" in after, (before[-30:], after[-30:]))
        cy.close()

        print("\n── V⑩ 📱 휴대폰 폭 ──")
        cp, gp, ep = page_for(br, PV_N, vn["me"], w=375, h=812)
        gp.goto("http://127.0.0.1:%d/voice-notes/%d" % (PV_N, vn["mine"]), wait_until="domcontentloaded")
        gp.wait_for_selector("#vnRedo", timeout=20000)
        gp.click("#vnRedo")
        q7, _ = wait_panel(gp, "vnAiBusy", lambda q: q["shown"], 3)
        ow = gp.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]")
        chk("옆으로 밀리지 않는다 (문서 폭 %d · 화면 %d)" % tuple(ow), ow[0] <= ow[1] + 1, ow)
        chk("칸이 화면 안 (오른쪽 끝 %.0f)" % q7["right"], q7["right"] <= ow[1] and q7["left"] >= 0, q7)
        gp.evaluate("() => document.getElementById('vnSumSec').scrollIntoView()")
        gp.wait_for_timeout(300)
        gp.screenshot(path=os.path.join(SHOTS, "8_휴대폰_음성메모_정리중.png"))
        wait_panel(gp, "vnAiBusy", lambda q: "ok" in q["cls"].split() or "err" in q["cls"].split(), 30)
        cp.close()

        print("\n── V⑫ 🔴 정리 도중에 **링크로 다른 메모로 넘어가면** ──")
        VSPA = "() => { var t = document.getElementById('vnTitle'); return t && t.value === '실패하는 메모'; }"
        #  🔴 반대 시험 — 운영 그대로는 **앞 메모 정리를 넘어간 메모 화면에 써 넣는다**(그것을 재 두어야 시험이 헛돌지 않는다)
        cb2, gb2, _ = page_for(br, PV_B, vb["me"])
        gb2.goto("http://127.0.0.1:%d/voice-notes/%d" % (PV_B, vb["mine"]), wait_until="domcontentloaded")
        gb2.wait_for_selector("#vnRedo", timeout=20000)
        gb2.click("#vnRedo")
        gb2.wait_for_timeout(500)
        spa0 = spa_go(gb2, "/voice-notes/%d" % vb["failn"], VSPA)
        time.sleep(SLOW + 4)
        bsum, bbody = gb2.inner_text("#vnSumBox"), gb2.input_value("#vnBody")
        chk("링크 이동이 본문만 갈아끼우기였다(운영)", spa0 is True, spa0)
        chk("🔴 반대 시험 — 운영은 넘어간 메모 화면에 **앞 메모 정리를 써 넣는다** 「%s」" % bsum.strip()[:20],
            "가짜 정리" in bsum, bsum[:60])
        chk("🔴 반대 시험 — 운영은 넘어간 메모의 **원문 칸까지** 앞 메모 것으로 바꾼다",
            "FAILME" not in bbody, bbody[:40])
        cb2.close()
        cs2, gs2, es2 = page_for(br, PV_N, vn["me"])
        gs2.goto("http://127.0.0.1:%d/voice-notes/%d" % (PV_N, vn["mine"]), wait_until="domcontentloaded")
        gs2.wait_for_selector("#vnRedo", timeout=20000)
        sum0 = ((gs2.request.get("http://127.0.0.1:%d/api/voice-note/%d" % (PV_N, vn["mine"])).json()
                 .get("note") or {}).get("summary") or "")
        gs2.click("#vnRedo")
        wait_panel(gs2, "vnAiBusy", lambda q: q["shown"], 3)
        spa1 = spa_go(gs2, "/voice-notes/%d" % vn["failn"], VSPA)
        time.sleep(SLOW + 4)
        nsum, nbody = gs2.inner_text("#vnSumBox"), gs2.input_value("#vnBody")
        chk("링크 이동이 본문만 갈아끼우기였다(새것)", spa1 is True, spa1)
        chk("🔵 넘어간 메모의 정리는 **그대로** 「%s」" % nsum.strip()[-10:], "실패 전 옛 정리" in nsum and "가짜 정리" not in nsum, nsum[:60])
        chk("🔵 넘어간 메모의 원문 칸도 **그대로**", "FAILME" in nbody, nbody[:40])
        chk("🔵 넘어간 메모 위 칸에 「끝났습니다」가 **안 뜬다**", "끝났습니다" not in gs2.inner_text("#vnSt"), gs2.inner_text("#vnSt"))
        qx = gs2.evaluate(PANEL, "vnAiBusy")
        chk("넘어간 메모 화면엔 진행 칸이 안 떠 있다", qx is not None and not qx["shown"], qx)
        chk("「🔄 다시 정리」는 눌린다(앞 메모가 잠근 채로 남지 않는다)", gs2.locator("#vnRedo").is_enabled())
        nn = gs2.request.get("http://127.0.0.1:%d/api/voice-note/%d" % (PV_N, vn["mine"])).json()
        sum1 = (nn.get("note") or {}).get("summary") or ""
        #  🔴 같은 메모를 앞에서 이미 정리했다 → 「가짜 정리」가 있다는 것만으로는 모른다 → **글이 바뀌었나**로
        chk("🔵 서버 일은 끝까지 갔다 — 앞 메모에 **새 정리가 저장됐다**(「%s」 → 「%s」)"
            % ((re.search(r"\d+번째", sum0) or re.search("", "")).group(0),
               (re.search(r"\d+번째", sum1) or re.search("", "")).group(0)),
            sum1 != sum0 and "가짜 정리" in sum1, (sum0[-40:], sum1[-40:]))
        chk("그 화면 콘솔 오류 0", not es2, es2[:2])
        cs2.close()

        print("\n── V⑪ 회귀 · 콘솔 ──")
        html = br.new_context()
        html.add_cookies([{"name": "tuser", "value": str(vn["me"]), "url": "http://127.0.0.1:%d" % PV_N}])
        body = html.request.get("http://127.0.0.1:%d/voice-notes/%d" % (PV_N, vn["mine"])).text()
        html.close()
        chk("z1167 시안 문서 흔적 0", "toast-stage" not in body and "토스트·알림 5종" not in body)
        chk("문서 한 장(<!DOCTYPE 1개)", body.count("<!DOCTYPE") == 1, body.count("<!DOCTYPE"))
        allv = vn_err + er2 + ex2 + ey2 + ep
        chk("🎤 음성 메모 화면 콘솔 오류 0", not allv, allv[:3])
        br.close()
finally:
    kill(pmb, pmn, pvb, pvn)

print("\n사진: %s" % SHOTS)
print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
