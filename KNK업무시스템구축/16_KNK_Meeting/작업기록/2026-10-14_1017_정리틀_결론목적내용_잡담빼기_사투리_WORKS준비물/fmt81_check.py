# -*- coding: utf-8 -*-
"""z1181 검사기 — 회의록·음성메모 정리 틀 「결론 → 목적 → (회의) 내용」 · 잡담 빼기 · 숫자·이름 살리기 · 사투리는 표준어로.
대표 2026-10-14 「회의록 및 음성메모 정리할때... 일반적인 생활대화, 잡담은 빼고 정리를 했으면 좋겠어..
  조금더 구체적으로 정리는 항상 결론 우선 그다음 목적, 회의내용 순으로...」
  「사투리 교정은 여러사람이 다양하게 하는거라 누구 기준으로 하기는 어려운데...」 → 권장안 「빅터AI가 표준어로」

재는 것 (앱 두 벌 = 운영 그대로(app_base) · 새것(app_new) · 진짜 서버 · AI 는 맨 끝 한 함수만 가짜 · 진짜 브라우저)
  ① 🔴 반대 시험 — 운영이 AI 에 보내는 회의록 지시문엔 「핵심: <회의 결론 한 줄>」 · 잡담·표준어 규칙 없음
  ② 새것이 **실제로 보내는** 회의록 지시문 — 결론 → 목적 → 회의 내용 순서 · 잡담 빼기 · 숫자·이름 · 표준어 ·
     결론 없으면 있는 그대로 · 길이 규칙 · 회사 배경·우리 회사 말·이번 회의 정보도 그대로 붙는다
  ③ 정리 결과가 저장되고 결정·할 일도 그대로 들어온다
  ④ 📄 회의록 양식 — 새 머리말 셋이 「■」 굵은 머리말 · 맨 위가 「결론」 · 안건은 예전처럼 · 운영 양식은 그냥 글
  ⑤ 🔴 옛 틀(「핵심:」) 회의록 양식은 **예전 그대로**
  ⑥ 🎤 음성 메모 — 보내는 지시문 결론 → 목적 → 내용 → 할 일 · 잡담·표준어 · 혼자 말한 것 규칙 그대로 · 목록 미리보기가 「결론」부터
  ⑦ 회의록 화면 정리 칸 · 콘솔 오류 0
  📸 대표께 보여 드릴 사진 — shots/
쓰는 법: py fmt81_check.py <app_base·app_new 가 있는 폴더>
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
PB, PN = 8913, 8914
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
    pr = subprocess.Popen([P313, os.path.join(HERE, "run_fmt81_app.py"), os.path.join(APPDIR, app), str(port)],
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


def page_for(br, port, uid, w=1280, h=1000):
    ctx = br.new_context(viewport={"width": w, "height": h})
    ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": "http://127.0.0.1:%d" % port}])
    pg = ctx.new_page()
    pg.add_init_script("try{localStorage.setItem('knk_works_install_hint_never','1');}catch(e){}")
    pg.on("dialog", lambda d: d.accept())
    errs = []
    pg.on("console", lambda m: errs.append("console: " + m.text[:160]) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:160]))
    return ctx, pg, errs


def post(pg, port, path):
    return pg.request.post(U(port, path), data="{}", headers={"Content-Type": "application/json"}).json()


def wait_job(pg, port, path):
    s = {}
    for _ in range(80):
        s = pg.request.get(U(port, path)).json()
        if s.get("state") in ("done", "error"):
            return s
        time.sleep(0.25)
    return s


def order_ok(text, heads):
    idx = [text.find(h) for h in heads]
    return all(i >= 0 for i in idx) and idx == sorted(idx), idx


DOC = """() => Array.from(document.querySelectorAll('.body .ln')).map(function(e){
  return { k: e.className.replace('ln', '').trim(), t: e.textContent.trim(),
           fw: +getComputedStyle(e).fontWeight, pre: getComputedStyle(e, '::before').content }; })"""

pb = pn = None
try:
    pb, sb = boot("app_base", PB)
    pn, sn = boot("app_new", PN)
    print("서버 둘 READY — 운영 그대로 %d · 새것 %d" % (PB, PN))
    with sync_playwright() as p:
        br = p.chromium.launch()
        cb, gb, eb = page_for(br, PB, sb["me"])
        cn, gn, en = page_for(br, PN, sn["me"])

        print("\n── ① ② 회의록 — AI 에 실제로 보내는 지시문 ──")
        sysm = {}
        for port, pg, sd, tag in ((PB, gb, sb, "운영"), (PN, gn, sn, "새것")):
            r = post(pg, port, "/api/meeting/%d/extract" % sd["ids"]["M1"])
            s = wait_job(pg, port, "/api/meeting/%d/extract-status" % sd["ids"]["M1"])
            calls = pg.request.get(U(port, "/__test/ai_calls")).json()["calls"]
            mc = [c for c in calls if "혼자 말한 녹음" not in c["system"]]
            sysm[tag] = (mc[-1]["system"] if mc else "", s, r)
            print("   %s: 시작 %s · 끝 %s · AI 호출 %d번" % (tag, r.get("started") or r, s.get("state"), len(mc)))
        so, ss = sysm["운영"][0], sysm["새것"][0]
        chk("🔴 반대 시험: 운영 지시문엔 「핵심: <회의 결론 한 줄>」", "핵심: <회의 결론 한 줄>" in so)
        chk("🔴 반대 시험: 운영 지시문엔 잡담·표준어 규칙 없음", "잡담" not in so and "표준어" not in so)
        ok, idx = order_ok(ss, ["\n    결론\n", "\n    목적\n", "\n    회의 내용\n", "\n    [안건명]"])
        chk("새 지시문 순서 = 결론 → 목적 → 회의 내용 → [안건명] %s" % idx, ok, idx)
        chk("새 지시문에 옛 「핵심:」 줄 없음", "핵심: <회의 결론 한 줄>" not in ss)
        for s_ in ("업무와 상관없는 생활 대화·잡담은 정리에 넣지 않는다", "원문 그대로 살려 **구체적으로**", "표준어 글말",
                   "정해진 결론 없음", "목적도 원문에서 드러난 것만", "처음부터 끝까지", "1,000자마다"):
            chk("새 지시문에 「%s」" % s_, s_ in ss)
        for s_ in ("[회사 배경]", "[이번 회의 정보]", "회의 제목: 삼성 2호기 납기 협의", "[우리 회사 말"):
            chk("회의 정보·회사 배경·우리 회사 말은 그대로 붙는다 — 「%s」" % s_, s_ in ss and s_ in so)
        chk("결정사항·할 일 규칙 줄은 운영과 글자 그대로", ss[ss.find("- decisions:"):ss.find("[회사 배경]")]
            == so[so.find("- decisions:"):so.find("[회사 배경]")])

        print("\n── ③ 저장 ──")
        st = sysm["새것"][1]
        res = st.get("result") or st
        chk("정리 끝(done) · 저장된 정리 = 새 틀", st.get("state") == "done" and (res.get("summary") or "") == sn["mtg_sum"],
            (st.get("state"), (res.get("summary") or "")[:40]))
        chk("결정 1 · 할 일 1 도 들어왔다", len(res.get("decisions") or []) >= 1 and len(res.get("actions") or []) >= 1,
            (len(res.get("decisions") or []), len(res.get("actions") or [])))

        print("\n── ④ 📄 회의록 양식 ──")
        gn.goto(U(PN, "/meetings/%d/doc" % sn["ids"]["M1"]), wait_until="domcontentloaded")
        dn = gn.evaluate(DOC)
        heads = [d["t"] for d in dn if d["k"] == "s"]
        chk("새 머리말 셋 = 결론 · 목적 · 회의 내용 (%s)" % heads, heads == ["결론", "목적", "회의 내용"], heads)
        chk("맨 위 줄이 「결론」", dn and dn[0]["t"] == "결론" and dn[0]["k"] == "s", dn[:1])
        chk("머리말은 굵고(%s) 앞에 「■」(%s)" % ([d["fw"] for d in dn if d["k"] == "s"], [d["pre"] for d in dn if d["k"] == "s"][:1]),
            all(d["fw"] >= 700 and "■" in d["pre"] for d in dn if d["k"] == "s"))
        chk("안건 줄은 예전처럼 [안건명] 머리말", [d["t"] for d in dn if d["k"] == "h"] == ["[납기]", "[사양]"],
            [d["t"] for d in dn if d["k"] == "h"])
        chk("본문 줄(- …)은 머리말로 안 잡힌다", all(d["k"] in ("p", "e") for d in dn if d["t"].startswith("-")))
        gn.screenshot(path=os.path.join(SHOTS, "f4_doc_new.png"), full_page=True)
        gb.goto(U(PB, "/meetings/%d/doc" % sb["ids"]["M2"]), wait_until="domcontentloaded")
        db = gb.evaluate(DOC)
        chk("🔴 반대 시험: 운영 양식은 새 머리말을 **그냥 글**로 그린다", not any(d["k"] == "s" for d in db) and any(d["t"] == "결론" for d in db),
            [(d["k"], d["t"]) for d in db[:3]])
        gb.screenshot(path=os.path.join(SHOTS, "f4_doc_base.png"), full_page=True)

        print("\n── ⑤ 옛 틀 회의록 ──")
        gn.goto(U(PN, "/meetings/%d/doc" % sn["ids"]["MO"]), wait_until="domcontentloaded")
        do = gn.evaluate(DOC)
        chk("🔴 옛 「핵심:」 회의록은 예전 그대로(핵심 줄 굵게 · 새 머리말 0)",
            [d["k"] for d in do][:1] == ["k"] and not any(d["k"] == "s" for d in do) and any(d["k"] == "h" for d in do),
            [(d["k"], d["t"]) for d in do])

        print("\n── ⑥ 🎤 음성 메모 ──")
        sysv = {}
        for port, pg, sd, tag in ((PB, gb, sb, "운영"), (PN, gn, sn, "새것")):
            post(pg, port, "/api/voice-note/%d/extract" % sd["notes"]["N1"])
            wait_job(pg, port, "/api/voice-note/%d/extract-status" % sd["notes"]["N1"])
            calls = pg.request.get(U(port, "/__test/ai_calls")).json()["calls"]
            vc = [c for c in calls if "혼자 말한 녹음" in c["system"]]
            note = pg.request.get(U(port, "/api/voice-note/%d" % sd["notes"]["N1"])).json().get("note") or {}
            sysv[tag] = (vc[-1]["system"] if vc else "", note.get("summary") or "")
        vo, vn = sysv["운영"][0], sysv["새것"][0]
        chk("🔴 반대 시험: 운영 메모 지시문은 「요점·할 일」 틀 · 잡담 규칙 없음", "\n    요점\n" in vo and "잡담" not in vo)
        ok, idx = order_ok(vn, ["\n    결론\n", "\n    목적\n", "\n    내용\n", "\n    할 일\n"])
        chk("새 메모 지시문 순서 = 결론 → 목적 → 내용 → 할 일 %s" % idx, ok, idx)
        for s_ in ("업무와 상관없는 생활 대화·잡담은 정리에 넣지 않는다", "표준어 글말", "원문 그대로 살려",
                   "안건·결정사항·참석자별 발언 귀속은 만들지 않는다", "이름·회사·날짜만 따로 모은 목록은 만들지 않는다",
                   "[회사 배경]", "[우리 회사 말"):
            chk("새 메모 지시문에 「%s」" % s_, s_ in vn)
        chk("메모 정리 저장 = 새 틀", sysv["새것"][1] == sn["note_sum"], sysv["새것"][1][:40])
        gn.goto(U(PN, "/voice-notes"), wait_until="domcontentloaded")
        pre = gn.evaluate("() => { var a = document.querySelector('.vn-card .vn-pre'); return a ? a.textContent.trim() : ''; }")
        chk("음성 메모 목록 미리보기가 「결론」부터 (%s…)" % pre[:16], pre.startswith("결론"), pre[:30])
        gn.goto(U(PN, "/voice-notes/%d" % sn["notes"]["N1"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#vnSumBox", timeout=15000)
        vbox = gn.inner_text("#vnSumBox")
        chk("음성 메모 화면 정리 칸이 「결론」부터", vbox.strip().startswith("결론"), vbox[:30])
        gn.screenshot(path=os.path.join(SHOTS, "f6_voice_new.png"), full_page=True)

        print("\n── ⑦ 회의록 화면 ──")
        gn.goto(U(PN, "/meetings/%d" % sn["ids"]["M1"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#mtgSummary", timeout=15000)
        sbox = gn.inner_text("#mtgSummary")
        chk("회의록 화면 정리 칸이 「결론」부터 · 세 머리말 차례", sbox.strip().startswith("결론")
            and order_ok(sbox, ["결론", "목적", "회의 내용"])[0], sbox[:40])
        gn.screenshot(path=os.path.join(SHOTS, "f7_meeting_new.png"), full_page=False)
        chk("새것 화면 콘솔 오류 0", not en, en[:3])
        chk("운영 화면 콘솔 오류 0", not eb, eb[:3])
        br.close()
finally:
    kill(pb, pn)

print("\n사진: %s" % SHOTS)
print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
