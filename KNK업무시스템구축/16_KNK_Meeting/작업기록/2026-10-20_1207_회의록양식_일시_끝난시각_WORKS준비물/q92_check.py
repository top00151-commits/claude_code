# -*- coding: utf-8 -*-
"""z1192 검사기 — 회의록 양식 「일시」에 끝난 시각: 「2026-10-19 (월) 14:00 ~ 14:50 (50분)」.
대표 2026-10-20 「넣기 (권장)」 — 이음 회의 알림 카드는 「14:00 ~ 14:50 (50분)」인데 양식은 시작 시각만 있었다.

재는 것 (앱 두 벌 = 운영 그대로(app_base) · 새것(app_new) · 진짜 서버 · 진짜 브라우저 · AI 안 부름)
  ① main.py 차이 = 한 자리(더한 줄 11 · 뺀 줄 0) · 다른 파일 그대로 · 전역 timedelta 안 씀
  ② 11가지 경우 「일시」 칸 — 새것: 같은 날 끝난 시각이 있고 시작보다 뒤면 「시작 ~ 끝 (N분)」 · 그 밖은 지금처럼 ·
     🔴 반대: 운영은 끝난 시각이 있어도 시작 시각만
  ③ 끝난 시각이 안 붙는 회의의 양식 HTML = 운영과 글자 그대로 · 붙는 회의는 「일시」 칸만 다름
  ④ 「🖼 이미지 저장·복사」 날짜 · 문서번호 그대로
  ⑤ 브라우저로 열어 콘솔 오류 0 · 사진
쓰는 법: py q92_check.py <app_base·app_new 가 있는 폴더>   판정: 종료코드(0=통과) + 요약 줄.
"""
import difflib
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
PB, PN = 8937, 8938
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
KNOWN = "Transition was skipped"
CELL = re.compile(r'<th class="k"><i class="s2">일시</i></th><td class="v">(.*?)</td>', re.S)
OK = FAIL = 0


def chk(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (name, str(detail)[:600]))


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
    pr = subprocess.Popen([P313, os.path.join(HERE, "run_q92_app.py"), os.path.join(APPDIR, app), str(port)],
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


def page_for(br, port, uid):
    ctx = br.new_context(viewport={"width": 1100, "height": 1000})
    ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": "http://127.0.0.1:%d" % port}])
    pg = ctx.new_page()
    pg.add_init_script("try{localStorage.setItem('knk_works_install_hint_never','1');}catch(e){}")
    errs = []
    pg.on("console", lambda m: errs.append("console: " + m.text[:160]) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:160]))
    return pg, errs


def html(pg, port, mid):
    r = pg.request.get(U(port, "/meetings/%d/doc" % mid))
    return r.status, r.text()


print("\n── ① 바뀐 자리 ──")
mb = io.open(os.path.join(APPDIR, "app_base", "app", "main.py"), encoding="utf-8").read().splitlines()
mn = io.open(os.path.join(APPDIR, "app_new", "app", "main.py"), encoding="utf-8").read().splitlines()
dl = [d for d in difflib.unified_diff(mb, mn, lineterm="", n=0) if d[:1] in "+-" and not d.startswith(("+++", "---"))]
plus = [d for d in dl if d.startswith("+")]
chk("main.py 차이 = 더한 줄 11 · 뺀 줄 0", len(plus) == 11 and not [d for d in dl if d.startswith("-")], dl)
chk("더한 줄 = ended_at 읽기 · 같은 날 검사 · 분 계산 · 「시작 ~ 끝 (N분)」",
    any('m.get("ended_at")' in d for d in plus) and any("_en.startswith(_md)" in d for d in plus)
    and any('f"{_st[11:16]} ~ {_en[11:16]} ({_mins}분)"' in d for d in plus) and any("if _mins > 0:" in d for d in plus), plus)
chk("전역 timedelta 를 새로 쓰지 않았다(쓴 줄 수 그대로)",
    sum(ln.count("timedelta") for ln in mb) == sum(ln.count("timedelta") for ln in mn) and not any("timedelta" in d for d in plus))
for rel in ("app/ai_client.py", "app/i18n.py", "app/templates/meeting_doc.html", "app/templates/meeting_form.html",
            "app/templates/voice_note_form.html", "app/templates/meetings.html"):
    a = io.open(os.path.join(APPDIR, "app_base", rel), "rb").read()
    b = io.open(os.path.join(APPDIR, "app_new", rel), "rb").read()
    chk("%s 그대로" % rel, a == b)

WANT_NEW = {"T1": "2026-10-19 (월) 14:00 ~ 14:50 (50분)", "T2": "2026-10-19 (월) 14:00", "T3": "2026-10-19 (월)",
            "T4": "2026-10-19 (월) 14:00", "T5": "2026-10-19 (월) 14:00", "T6": "2026-10-19 (월) 14:00", "T7": "2026-10-19 (월)",
            "T8": "2026-10-19 (월) 14:00", "T9": "2026-10-19 (월) 09:05 ~ 17:40 (515분)", "T10": "",
            "T11": "2026-10-19 (월) 14:00 ~ 15:30 (90분)"}
WANT_BASE = dict(WANT_NEW, T1="2026-10-19 (월) 14:00", T9="2026-10-19 (월) 09:05", T11="2026-10-19 (월) 14:00")
RANGE = ("T1", "T9", "T11")
pb = pn = None
try:
    pb, sb = boot("app_base", PB)
    pn, sn = boot("app_new", PN)
    IB, IN = sb["ids"], sn["ids"]
    print("\n운영 그대로 %d · 새것 %d · 회의 %s" % (PB, PN, IN))
    with sync_playwright() as p:
        br = p.chromium.launch()
        gb, eb = page_for(br, PB, sb["me"])
        gn, en = page_for(br, PN, sn["me"])

        print("\n── ② 「일시」 칸 11가지 ──")
        HB, HN = {}, {}
        for k in WANT_NEW:
            sb_, hb = html(gb, PB, IB[k])
            sn_, hn = html(gn, PN, IN[k])
            HB[k], HN[k] = hb, hn
            cb, cn = CELL.search(hb), CELL.search(hn)
            cb, cn = (cb.group(1).strip() if cb else None), (cn.group(1).strip() if cn else None)
            chk("%s 새것 「%s」" % (k, WANT_NEW[k] or "(빈 칸)"), sn_ == 200 and cn == WANT_NEW[k], (sn_, cn))
            chk("%s 운영 「%s」%s" % (k, WANT_BASE[k] or "(빈 칸)", " 🔴 반대" if k in RANGE else ""), sb_ == 200 and cb == WANT_BASE[k], (sb_, cb))

        print("\n── ③ 양식 HTML 대조 ──")
        same = [k for k in WANT_NEW if k not in RANGE]
        chk("끝난 시각이 안 붙는 회의 %d건의 양식 = 운영과 글자 그대로" % len(same), all(HB[k] == HN[k] for k in same),
            [k for k in same if HB[k] != HN[k]])
        for k in RANGE:
            nb, nn = CELL.sub("<td>X</td>", HB[k]), CELL.sub("<td>X</td>", HN[k])
            chk("%s 「일시」 칸 빼면 운영과 글자 그대로" % k, nb == nn,
                [d for d in difflib.unified_diff(nb.splitlines(), nn.splitlines(), lineterm="", n=0)][:6])

        print("\n── ④ 날짜·문서번호 그대로 ──")
        dd = re.search(r'id="btnImg"[^>]*data-date="([^"]*)"', HN["T1"])
        chk("🖼 이미지 저장·복사 날짜 = 회의 날짜", dd and dd.group(1) == "2026-10-19", dd.group(1) if dd else None)
        chk("문서번호 MIN-20261019-%04d 그대로" % IN["T1"], ("MIN-20261019-%04d" % IN["T1"]) in HN["T1"])

        print("\n── ⑤ 브라우저 ──")
        gn.goto(U(PN, "/meetings/%d/doc" % IN["T1"]), wait_until="domcontentloaded")
        gn.wait_for_selector("table.form", timeout=20000)
        txt = gn.inner_text("table.form")
        chk("화면에 「14:00 ~ 14:50 (50분)」", "14:00 ~ 14:50 (50분)" in txt, txt[:200])
        gn.screenshot(path=os.path.join(SHOTS, "q92_doc_T1.png"), full_page=False)
        gb.goto(U(PB, "/meetings/%d/doc" % IB["T1"]), wait_until="domcontentloaded")
        gb.wait_for_selector("table.form", timeout=20000)
        gb.screenshot(path=os.path.join(SHOTS, "q92_doc_T1_before.png"), full_page=False)
        gn.goto(U(PN, "/meetings/%d/doc" % IN["T9"]), wait_until="domcontentloaded")
        gn.wait_for_selector("table.form", timeout=20000)
        chk("긴 회의 「09:05 ~ 17:40 (515분)」", "09:05 ~ 17:40 (515분)" in gn.inner_text("table.form"))
        chk("새것 콘솔 오류 0", not [e for e in en if KNOWN not in e], en[:3])
        chk("운영 콘솔 오류 0", not [e for e in eb if KNOWN not in e], eb[:3])
        br.close()
finally:
    kill(pb, pn)

print("\n사진: %s" % SHOTS)
print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
