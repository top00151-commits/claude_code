# -*- coding: utf-8 -*-
"""z1179 검사기 — 🗓 회의 카드 모아보기 탭을 이음 v854~v856 과 맞춤 + 「⏳ 정리 중」 단계를 실제와 맞춤.

대표 2026-10-13: 「"회의록" 표현은 회의록이 작성됐을 때만」 · 「녹음없음은 삭제해」(이음 v854) ·
                 「아이콘이 눌렸을때만 동작」(이음 v856) · 확인 「📋 회의록 등록으로」 「회의록 없음 — 뺀다」

재는 것 (앱 두 벌 — 운영 그대로(z1178) / 고친 것 · 이음만 가짜 · 단계·권한은 **진짜 서버**)
  ① 🔴 서버 단계 — 운영: 30분째 멈춘 회의·AI 정리 중·AI 실패가 모두 「정리 대기(recorded)」 = 「⏳ 정리 중」으로 보였다
       새것: 멈춤→failed · AI 정리 중→processing · AI 실패→failed · 값은 늘 다섯 가지 안(이음과의 약속)
  ② 모아보기 응답에 can_edit — 나 true · 보기만 하는 사람 false · 회의록 없는 회의엔 안 준다
  ③ 화면(나 = 고칠 수 있음): 진행 중·끝남 → 「🔴 회의 진행 중 · 이름」·「⏹ 회의 끝남 · 이름」 + [📁 녹음 올리기][✏️ 작성하기] ·
       정리 중 → 단추 없음 · 실패 → [🔄 다시 정리] · 정리 끝 → 윗줄 「📋 회의록 등록」(노랑) · 「진행한 회의」 묶음 ·
       회의록 없음 → 아무 글도 없음 · 🔴 「회의록」이라는 말은 **정리 끝난 카드에만** · 옛 글 0 ·
       🔴 카드 빈 곳을 눌러도 안 열린다(이음 v856) · 단추를 누르면 열린다
  ④ 🔴 반대 시험 — 운영 화면엔 「녹음 없음」·「회의록 열기」·「회의록 정리 중」·빈 곳 누르기가 있다
  ⑤ 보기만 하는 사람: 정리 전 단추 없음 · 정리 끝은 「📋 회의록 보기」
  ⑥ 베트남어 — 이음 v854 와 같은 글
  ⑦ 📱 375 폭 · 콘솔 오류 0 · 사진

쓰는 법: py cards_v854_ui.py [app_base·app_new 가 있는 폴더]
판정: **종료코드**(0=통과) + 요약 줄.
"""
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1] if len(sys.argv) > 1 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
RUN = os.path.join(HERE, "run_cards_app.py")
PB, PN = 8903, 8904
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
OK = FAIL = 0
OLD_WORDS = ["녹음 없음", "녹음 안 됨", "회의록 열기", "회의록 정리 중", "회의록에서 다시 시도", "회의록 없음"]


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
    lp = os.path.join(APPDIR, "srvc_%d.log" % port)
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


def cards_api(port, uid):
    rq = urllib.request.Request("http://127.0.0.1:%d/api/meetings/msg-cards" % port, headers={"Cookie": "tuser=%d" % uid})
    with urllib.request.urlopen(rq, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


#  카드 하나를 통째로 읽는다(제목으로 찾는다)
CARD = """(t) => {
  const a = [...document.querySelectorAll('article.mc-card')].find(x => (x.querySelector('.mc-ttl')||{}).textContent === t);
  if (!a) return null;
  const pill = a.querySelector('.mc-pill'), st = a.querySelector('.mc-state'), mm = a.querySelector('.mc-min');
  let n = a.previousElementSibling;
  while (n && !(n.classList && n.classList.contains('mc-sec'))) n = n.previousElementSibling;
  const cs = getComputedStyle(pill);
  return { cls: a.className, pill: pill ? pill.textContent : '', pillBg: cs.backgroundColor, pillFg: cs.color,
           line: st ? st.textContent : '', dim: !!a.querySelector('.mc-state.dim'),
           btns: [...a.querySelectorAll('.mc-min a.mc-btn')].map(b => [b.textContent, b.getAttribute('href'), b.getAttribute('target') || '']),
           minText: (mm ? mm.textContent : '') + ' ' + (pill ? pill.textContent : ''),
           group: n ? (n.childNodes[0].textContent || '').trim() : '', cursor: getComputedStyle(a).cursor };
}"""


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
    T = {"S1": "S1 시작만·지금 회의 중", "S1b": "S1b 시작만·끝남", "S2": "S2 녹음 막 들어옴", "S3": "S3 녹음 있는데 멈춤",
         "S4": "S4 받아쓰기 도는 중", "S5": "S5 AI 정리 도는 중", "S6": "S6 AI 정리 실패", "S7": "S7 정리 끝",
         "S9": "S9 기록 없이 끝난 회의"}

    print("\n── ① 🔴 서버 단계(이음이 받는 값과 같은 함수) ──")
    B, N = sb["stages"], sn["stages"]
    print("   운영:", B)
    print("   새것:", N)
    chk("🔴 반대 시험 — 운영은 30분째 멈춘 회의(S3)를 「정리 대기」로 (%s)" % B["S3"], B["S3"] == "recorded")
    chk("🔴 반대 시험 — 운영은 AI 정리가 도는 회의(S5)를 모른다 (%s)" % B["S5"], B["S5"] == "recorded")
    chk("🔴 반대 시험 — 운영은 AI 정리가 실패한 회의(S6)를 모른다 (%s)" % B["S6"], B["S6"] == "recorded")
    chk("새것: 멈춤(S3) → failed (멈춤 기준 %s분)" % sn.get("stall_min"), N["S3"] == "failed" and sn.get("stall_min") == 10)
    chk("새것: AI 정리 중(S5) → processing", N["S5"] == "processing")
    chk("새것: AI 정리 실패(S6) → failed", N["S6"] == "failed")
    chk("그대로: 막 들어온 녹음(S2) → recorded · 받아쓰기 중(S4) → processing · 정리 끝(S7) → done · 시작만(S1·S1b) → started",
        (N["S2"], N["S4"], N["S7"], N["S1"], N["S1b"]) == ("recorded", "processing", "done", "started", "started"), N)
    chk("🔵 값은 늘 다섯 가지 안(이음과의 약속 그대로)",
        set(N.values()) <= {"started", "recorded", "processing", "failed", "done"}, N)

    print("\n── ② 모아보기 응답 — can_edit ──")
    jm, jv, jb = cards_api(PN, sn["me"]), cards_api(PN, sn["viewer"]), cards_api(PB, sb["me"])
    by = lambda j: {it["title"]: it["minutes"] for it in j["items"]}
    mm, mv, mb = by(jm), by(jv), by(jb)
    chk("나(작성자) — 회의록 있는 8건 모두 can_edit true",
        all(mm[T[k]].get("can_edit") is True for k in T if k != "S9"), {k: mm[T[k]].get("can_edit") for k in T})
    chk("보기만 하는 사람 — 볼 수는 있고(can_view) 고칠 수는 없다(can_edit false)",
        all(mv[T[k]].get("can_view") is True and mv[T[k]].get("can_edit") is False for k in T if k != "S9"))
    chk("회의록 없는 회의 — 볼 수도 고칠 수도 없다(칸을 안 준다)", mm[T["S9"]] == {"stage": "none", "can_view": False})
    chk("운영 응답엔 can_edit 칸이 없다(반대 시험)", all("can_edit" not in mb[T[k]] for k in T))
    chk("응답의 단계 = 서버 함수 값", all(mm[T[k]]["stage"] == N[k] for k in T if k != "S9"))

    with sync_playwright() as p:
        br = p.chromium.launch()

        def page_for(port, uid, w=1280, h=1600):
            ctx = br.new_context(viewport={"width": w, "height": h})
            ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": "http://127.0.0.1:%d" % port}])
            pg = ctx.new_page()
            pg.add_init_script("try{localStorage.setItem('knk_works_install_hint_never','1');}catch(e){}")
            errs = []
            pg.on("console", lambda m: errs.append("console: " + m.text[:160]) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:160]))
            pg.goto("http://127.0.0.1:%d/meetings?tab=cards" % port, wait_until="domcontentloaded")
            pg.wait_for_function("() => document.querySelectorAll('article.mc-card').length >= 9", timeout=20000)
            return ctx, pg, errs

        print("\n── ③ 화면 — 나(고칠 수 있다) ──")
        ctx, pg, errs = page_for(PN, sn["me"])
        who = mm[T["S1"]]["started_by"]
        c = {k: pg.evaluate(CARD, T[k]) for k in T}
        url = lambda k: "/meetings/%d" % sn["ids"][k]
        chk("S1 진행 중 → 「🔴 회의 진행 중 · %s」(녹음 안 됨 없음)" % who, c["S1"]["line"] == "🔴 회의 진행 중 · " + who, c["S1"])
        chk("S1 → [📁 녹음 올리기][✏️ 작성하기] · 회의록 화면으로 · 같은 창",
            c["S1"]["btns"] == [["📁 녹음 올리기", url("S1"), ""], ["✏️ 작성하기", url("S1"), ""]], c["S1"]["btns"])
        chk("S1b 끝남 → 윗줄 ✅ 회의 종료 · 「⏹ 회의 끝남 · %s」(녹음 없음 없음) · 흐린 글" % who,
            "회의 종료" in c["S1b"]["pill"] and c["S1b"]["line"] == "⏹ 회의 끝남 · " + who and c["S1b"]["dim"], c["S1b"])
        chk("S1b → [📁 녹음 올리기][✏️ 작성하기]", [b[0] for b in c["S1b"]["btns"]] == ["📁 녹음 올리기", "✏️ 작성하기"], c["S1b"]["btns"])
        for k in ("S2", "S4", "S5"):
            chk("%s → 「⏳ 정리 중」 · 단추 없음" % k, c[k]["line"] == "⏳ 정리 중" and c[k]["btns"] == [], c[k])
        for k in ("S3", "S6"):
            chk("%s → 「⚠ 정리 실패」 + [🔄 다시 정리]" % k,
                c[k]["line"] == "⚠ 정리 실패" and c[k]["btns"] == [["🔄 다시 정리", url(k), ""]], c[k])
        chk("S7 정리 끝 → 윗줄 「📋 회의록 등록」", c["S7"]["pill"] == "📋 회의록 등록", c["S7"]["pill"])
        chk("   연한 노랑 (%s / %s)" % (c["S7"]["pillBg"], c["S7"]["pillFg"]),
            c["S7"]["pillBg"] == "rgb(254, 243, 199)" and c["S7"]["pillFg"] == "rgb(146, 64, 14)")
        chk("   「✅ 진행한 회의」 묶음 (%s)" % c["S7"]["group"][:12], c["S7"]["group"].startswith("✅ 진행한 회의"))
        chk("   [📋 회의록 보기] 새 창 그대로", c["S7"]["btns"][:1] == [["📋 회의록 보기", "/meetings/%d/doc" % sn["ids"]["S7"], "_blank"]],
            c["S7"]["btns"])
        chk("S9 회의록이 아예 없는 끝난 회의 → 아래 줄·단추 **없음**(「회의록 없음」 안 씀)",
            c["S9"]["line"] == "" and c["S9"]["btns"] == [] and "회의록" not in c["S9"]["minText"], c["S9"])
        bad = [k for k in T if k != "S7" and "회의록" in c[k]["minText"]]
        chk("🔴 「회의록」이라는 말은 **정리 끝난 카드에만** (그 밖 %d장에 0)" % (len(T) - 1), not bad, bad)
        tab = pg.inner_text("#mcWrap") if pg.locator("#mcWrap").count() else pg.inner_text("main")
        left = [w for w in OLD_WORDS if w in tab]
        chk("옛 글 0 — %s" % " · ".join(OLD_WORDS), not left, left)
        chk("🔴 카드 빈 곳 누르기 없음 — 손가락 모양 아님 · tap 표시 없음",
            all("tap" not in c[k]["cls"].split() for k in T) and c["S1"]["cursor"] != "pointer", c["S1"]["cursor"])
        pg.locator("article.mc-card", has=pg.locator(".mc-ttl", has_text=T["S1"])).locator(".mc-sub").first.click()
        pg.wait_for_timeout(1200)
        chk("빈 곳을 눌러도 화면이 그대로 (%s)" % pg.url.split("127.0.0.1:%d" % PN)[-1], pg.url.endswith("/meetings?tab=cards"))
        pg.screenshot(path=os.path.join(SHOTS, "c1_모아보기_새.png"), full_page=True)
        pg.locator("article.mc-card", has=pg.locator(".mc-ttl", has_text=T["S1"])).locator("a.mc-btn", has_text="✏️ 작성하기").click()
        pg.wait_for_function("(u) => location.pathname === u", arg=url("S1"), timeout=20000)
        chk("[✏️ 작성하기]를 누르면 그 회의록 화면으로", True)
        chk("내 화면 콘솔 오류 0", not errs, errs[:3])
        ctx.close()

        print("\n── ④ 🔴 반대 시험 — 운영 화면 ──")
        ctx, pg, eb = page_for(PB, sb["me"])
        tb = pg.inner_text("#mcWrap") if pg.locator("#mcWrap").count() else pg.inner_text("main")
        chk("운영엔 「녹음 없음」·「녹음 안 됨」·「회의록 열기」·「회의록 정리 중」이 있다",
            all(w in tb for w in ("녹음 없음", "녹음 안 됨", "회의록 열기", "회의록 정리 중")), [w for w in OLD_WORDS if w in tb])
        b7 = pg.evaluate(CARD, T["S7"])
        chk("운영의 정리 끝 윗줄은 「✅ 회의 종료」 (%s)" % b7["pill"], "회의 종료" in b7["pill"])
        chk("운영엔 카드 빈 곳 누르기(tap)가 있다", pg.locator("article.mc-card.tap").count() > 0)
        pg.screenshot(path=os.path.join(SHOTS, "c0_모아보기_운영.png"), full_page=True)
        ctx.close()

        print("\n── ⑤ 보기만 하는 사람 ──")
        ctx, pg, ev = page_for(PN, sn["viewer"])
        v = {k: pg.evaluate(CARD, T[k]) for k in ("S1", "S1b", "S3", "S6", "S7")}
        chk("정리 전 카드엔 단추 없음(S1·S1b·S3·S6)", all(v[k]["btns"] == [] for k in ("S1", "S1b", "S3", "S6")),
            {k: v[k]["btns"] for k in v})
        chk("실패 글은 보인다 · 🔄 은 없다", v["S3"]["line"] == "⚠ 정리 실패")
        chk("정리 끝은 [📋 회의록 보기]", [b[0] for b in v["S7"]["btns"]][:1] == ["📋 회의록 보기"], v["S7"]["btns"])
        ctx.close()

        print("\n── ⑥ 베트남어 ──")
        ctx, pg, e3 = page_for(PN, sn["vnu"])
        q = {k: pg.evaluate(CARD, T[k]) for k in ("S1", "S2", "S3", "S7")}
        chk("📋 Đã đăng biên bản (%s)" % q["S7"]["pill"], q["S7"]["pill"] == "📋 Đã đăng biên bản")
        chk("[📁 Tải ghi âm lên][✏️ Soạn thảo] (%s)" % [b[0] for b in q["S1"]["btns"]],
            [b[0] for b in q["S1"]["btns"]] == ["📁 Tải ghi âm lên", "✏️ Soạn thảo"])
        chk("⚠ Tóm tắt thất bại + [🔄 Tóm tắt lại]", q["S3"]["line"] == "⚠ Tóm tắt thất bại"
            and [b[0] for b in q["S3"]["btns"]] == ["🔄 Tóm tắt lại"], q["S3"])
        chk("⏳ Đang tóm tắt", q["S2"]["line"] == "⏳ Đang tóm tắt", q["S2"]["line"])
        ctx.close()

        print("\n── ⑦ 📱 휴대폰 폭 ──")
        ctx, pg, e4 = page_for(PN, sn["me"], w=375, h=812)
        ow = pg.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]")
        chk("375 폭에서 옆으로 안 밀린다 (%d · %d)" % tuple(ow), ow[0] <= ow[1] + 1)
        pg.locator("article.mc-card", has=pg.locator(".mc-ttl", has_text=T["S7"])).scroll_into_view_if_needed()
        pg.screenshot(path=os.path.join(SHOTS, "c2_휴대폰.png"))
        ctx.close()
        chk("보기만·베트남어·휴대폰 화면 콘솔 오류 0", not (ev + e3 + e4), (ev + e3 + e4)[:3])
        br.close()
finally:
    kill(pb, pn)

print("\n사진: %s" % SHOTS)
print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
