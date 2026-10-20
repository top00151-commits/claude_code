# -*- coding: utf-8 -*-
"""z1189 검사기 — 받아쓴 글의 소수점이 벌어지지 않게(「1.2%」→「1. 2%」 막기).
대표 2026-10-19 「다음 건으로 고치기 검토 (권장)」 · 운영 받아쓴 글 94곳(회의록 36건 중 17건 86곳 · 음성 메모 10건 중 3건 8곳)
· 이미 저장된 곳은 그대로(대표)

재는 것 (앱 두 벌 = 기준(app_base = z1188 까지 · 오늘 밤 운영이 될 것) · 새것(app_new = z1189))
  ━ 서버 안 띄움 (두 벌의 main.py 에서 헛말 정리 함수만 꺼내 같은 글을 넣는다) ━
  ① 숫자 사이 점이 없는 글은 결과가 기준과 글자 그대로(되풀이 줄이기·끊기·잇기·셈 모두)
  ② 숫자 사이 점은 그대로(1.2% · 0.05mm · 10.23 · 3.5 · 2.0 · 1.2.3 · 20.5.) · 🔴 반대: 기준은 벌린다
  ③ 숫자로 끝난 문장 뒤 글자로 시작하는 문장은 그대로 끊는다(「총 20. 다음은」)
  ④ 바뀐 자리 = 끊는 규칙 한 줄(+ 설명 두 줄)뿐 — main.py 의 나머지는 글자 그대로
  ━ 진짜 서버 + 진짜 브라우저 (받아쓰기·정리 AI 맨 끝만 가짜 · 30초 나누기는 진짜 ffmpeg) ━
  ⑤ 회의록 녹음 올리기(자동 감지) → 원문 「1.2%」「0.05mm」「10.23」 그대로 · 정리 AI 가 보는 글도 · 🔴 반대: 기준은 「1. 2%」
  ⑥ 「한국어+베트남어 섞임」 → 조각 글의 「3.5」「0.2」「1.2%」 그대로 · 베트남어 표시 문장 수는 기준과 같다
  ⑦ 음성 메모 녹음 올리기 → 원문 그대로 · 정리 AI 가 보는 글도
  ⑧ 기준과 다른 것은 숫자 사이 점뿐(새 원문의 「숫자.숫자」를 「숫자. 숫자」로 바꾸면 기준과 글자 그대로)
  ⑨ 콘솔 오류 0
쓰는 법: py q89_check.py <app_base·app_new 가 있는 폴더>
판정: **종료코드**(0=통과) + 요약 줄.  🔒 시험 글은 모두 지어낸 것.
"""
import ast
import difflib
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1] if len(sys.argv) > 1 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
PB, PN = 8931, 8932
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
KNOWN = "Transition was skipped"   # 운영에도 있는 공용 화면 전환 경고(z1182 확인) — 이번 변경 밖
OK = FAIL = 0


def chk(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (name, str(detail)[:700]))


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
    pr = subprocess.Popen([P313, os.path.join(HERE, "run_q89_app.py"), os.path.join(APPDIR, app), str(port)],
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


def db(app, sql, args=()):
    p = os.path.join(APPDIR, app, "data", "knk.db").replace("\\", "/")
    c = sqlite3.connect("file:%s?mode=ro" % p, uri=True, timeout=10)
    c.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in c.execute(sql, args)]
    finally:
        c.close()


def wait_until(fn, timeout=30.0, step=0.25):
    t0 = time.time()
    v = None
    while time.time() - t0 < timeout:
        try:
            v = fn()
        except Exception:
            v = None
        if v:
            return v
        time.sleep(step)
    return v


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


def jget(pg, port, path):
    r = pg.request.get(U(port, path))
    try:
        return r.json()
    except Exception:
        return {}


def helpers(app):
    """그 앱의 main.py 에서 헛말 정리 함수만 꺼낸다(앱은 띄우지 않는다)."""
    tree = ast.parse(io.open(os.path.join(APPDIR, app, "app", "main.py"), encoding="utf-8").read())
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name == "_stt_strip_hallucination")
            or (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in ("_STT_REPEAT_MIN", "_STT_REPEAT_MAXLEN")
                                                  for t in n.targets))]
    ns = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), "main.py", "exec"), ns)
    return ns["_stt_strip_hallucination"]


SB, SN = helpers("app_base"), helpers("app_new")

print("\n── ① 숫자 사이 점이 없는 글 = 기준과 글자 그대로 ──")
SAME = {
    "회의 말(여러 문장)": ("오늘은 삼성 A라인 2호기 출하 일정과 셋업 순서를 함께 정리했습니다. 출하는 11월 20일로 하고 포장은 그 전날까지 "
                     "마치기로 했습니다. 셋업은 25일부터 시작하는데 고객사 담당자의 확인을 먼저 받아야 합니다."),
    "물음표·느낌표·말줄임": "정말요? 네! 그럼… 그렇게 하죠... 알겠습니다?! 좋아요.",
    "줄바꿈": "첫째 줄입니다\n둘째 줄입니다.\n\n셋째 줄",
    "헛말 되풀이(줄이기)": "감사합니다. " * 12 + "시청해 주셔서 감사합니다.",
    "짧은 말 되풀이": "네. 네. 네. 네. 네. 그럼 시작하겠습니다.",
    "베트남어": "Anh ơi, hôm nay kiểm tra máy số hai nhé. Dạ. Vâng ạ, em sẽ gửi báo giá trước thứ sáu.",
    "영어·번호 꼴": "No.1 제품입니다. Version two. OK. 1차 검수는 끝났습니다.",
    "숫자로 끝난 문장": "총 20. 다음은 셋업입니다. 수량은 3개. 그다음 안건.",
    "빈 글": "",
    "빈칸만": "   ",
    "외국 글자 헛말": "ご視聴ありがとうございました。チャンネル登録をお願いいたします。",
}
for k, t in SAME.items():
    b, n = SB(t), SN(t)
    chk("%s — 결과·줄인 곳 수 그대로" % k, b == n, (b, n))

print("\n── ② 숫자 사이 점은 그대로 · 🔴 반대: 기준은 벌린다 ──")
DIFF = [("불량률은 1.2%입니다.", "1.2%"), ("공차는 0.05mm 안입니다.", "0.05mm"), ("출하는 10.23일로 합니다.", "10.23일"),
        ("Giá là 3.5 triệu đồng.", "3.5 triệu"), ("버전 2.0 으로 올렸다.", "2.0 으로"), ("1.2.3 단계로 나눈다.", "1.2.3 단계"),
        ("값은 20.5. 끝.", "20.5. 끝"), ("2026.10.19 회의", "2026.10.19 회의")]
for t, want in DIFF:
    n, b = SN(t)[0], SB(t)[0]
    chk("「%s」 그대로(기준: 「%s」)" % (want, b), want in n and want not in b, (n, b))
chk("숫자 사이 점만 다르다(새 글의 「숫자.숫자」를 벌리면 기준과 같다)",
    all(re.sub(r"(\d)\.(?=\d)", r"\1. ", SN(t)[0]) == SB(t)[0] for t, _ in DIFF))

print("\n── ③ 숫자로 끝난 문장 뒤는 그대로 끊는다 ──")
t = "총 20.\n다음은 셋업입니다. 수량은 3. 그다음 안건."
chk("「총 20.」·「수량은 3.」 뒤 끊기 기준과 같다", SN(t) == SB(t), (SN(t), SB(t)))

print("\n── ④ 바뀐 자리 = 끊는 규칙 한 줄(+ 설명 두 줄)뿐 ──")
mb = io.open(os.path.join(APPDIR, "app_base", "app", "main.py"), encoding="utf-8").read().splitlines()
mn = io.open(os.path.join(APPDIR, "app_new", "app", "main.py"), encoding="utf-8").read().splitlines()
dl = [d for d in difflib.unified_diff(mb, mn, lineterm="", n=0) if d[:1] in "+-" and not d.startswith(("+++", "---"))]
chk("main.py 차이 = 빠진 줄 1 · 더한 줄 3", len([d for d in dl if d.startswith("-")]) == 1
    and len([d for d in dl if d.startswith("+")]) == 3, dl)
chk("빠진 줄 = 옛 끊는 규칙 · 더한 줄 = 설명 둘 + 새 규칙",
    any(d.startswith("-") and "_re_h.split(" in d for d in dl)
    and [d for d in dl if d.startswith("+") and "_re_h.split(" in d][0].count("(?!(?<=\\d\\.)\\d)") == 1
    and sum(1 for d in dl if d.startswith("+    #")) == 2, dl)
for rel in ("app/ai_client.py", "app/i18n.py", "app/templates/meeting_form.html", "app/templates/voice_note_form.html"):
    a = io.open(os.path.join(APPDIR, "app_base", rel), "rb").read()
    b = io.open(os.path.join(APPDIR, "app_new", rel), "rb").read()
    chk("%s 그대로" % rel, a == b)

# ═══════════════════════ 진짜 서버 + 진짜 브라우저 ═══════════════════════
WAV = os.path.join(APPDIR, "q89_65s.wav")
subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                "sine=frequency=440:sample_rate=16000:duration=65", "-ac", "1", WAV], check=True)
pb = pn = None


def pick(pg, v):
    try:
        pg.select_option("#sttLang", v, timeout=3000)
    except Exception:
        pg.evaluate("(v) => document.querySelectorAll('select.sttLangPick').forEach(function(s){ s.value = v; })", v)


def run_meeting(pg, port, app, mid, lang):
    n0 = len(jget(pg, port, "/__test/chat")["calls"])
    jget(pg, port, "/__test/tr?reset=1")
    pg.goto(U(port, "/meetings/%d" % mid), wait_until="domcontentloaded")
    pg.wait_for_selector("#redoTools #recFile", state="attached", timeout=20000)
    pick(pg, lang)
    pg.locator("#redoTools #recFile").set_input_files(WAV)
    done = wait_until(lambda: "모두 끝났습니다" in pg.inner_text("#pipeSteps"), 90)
    body = db(app, "SELECT body FROM meetings WHERE id=?", (mid,))[0]["body"]
    calls = jget(pg, port, "/__test/chat")["calls"][n0:]
    tr = jget(pg, port, "/__test/tr")["tr"]
    return bool(done), body, calls, tr


def run_note(pg, port, app):
    last0 = db(app, "SELECT COALESCE(MAX(id),0) AS m FROM voice_notes")[0]["m"]
    n0 = len(jget(pg, port, "/__test/chat")["calls"])
    pg.goto(U(port, "/voice-notes/new"), wait_until="domcontentloaded")
    pg.wait_for_selector("#vnLang", timeout=20000)
    pg.locator("#vnFile").set_input_files(WAV)
    r = wait_until(lambda: [x for x in db(app, "SELECT * FROM voice_notes WHERE id>? ORDER BY id DESC", (last0,))
                            if (x["summary"] or "").strip()], 90)
    calls = jget(pg, port, "/__test/chat")["calls"][n0:]
    return (r[0] if r else {}), calls


try:
    pb, sb = boot("app_base", PB)
    pn, sn = boot("app_new", PN)
    print("\n기준 %d · 새것 %d · 회의 %s" % (PB, PN, sn["ids"]))
    chk("두 벌 모두 「섞임」 받아쓰기가 있다(z1188 위)", sb["has_window"] is True and sn["has_window"] is True)
    DEC, VI, KO = sn["dec_talk"], sn["vi_dec"], sn["ko_dec"]
    with sync_playwright() as p:
        br = p.chromium.launch()
        cb, gb, eb = page_for(br, PB, sb["me"])
        cn, gn, en = page_for(br, PN, sn["me"])

        print("\n── ⑤ 회의록 녹음 올리기(자동 감지) ──")
        dn, bn, cn5, tn = run_meeting(gn, PN, "app_new", sn["ids"]["D1"], "")
        db5, bb, cb5, tb = run_meeting(gb, PB, "app_base", sb["ids"]["D1"], "")
        chk("두 벌 모두 정리까지 「모두 끝났습니다」", dn and db5, (dn, db5))
        chk("받아쓰기 = 통째 한 번(조각 없음) · 요청 기준과 같다", len(tn) == len(tb) == 1 and tn[0]["kw"] == tb[0]["kw"]
            and not tn[0]["file"].startswith("part_"), (tn, tb))
        chk("새 원문 = 메모 + 🎤 [음성 변환] + 받아쓴 글 그대로(「1.2%」「0.05mm」「10.23일」「2.0」)",
            bn == sn["seed"] + "\n\n🎤 [음성 변환]\n" + DEC and all(x in bn for x in ("1.2%", "0.05mm", "10.23일", "2.0 을")), bn)
        chk("🔴 반대: 기준 원문은 「1. 2%」「0. 05mm」「10. 23일」", all(x in bb for x in ("1. 2%", "0. 05mm", "10. 23일")), bb)
        chk("정리 AI 가 보는 글도 「1.2%」(기준은 「1. 2%」)", cn5 and "1.2%" in cn5[-1]["user"] and cb5 and "1. 2%" in cb5[-1]["user"])
        chk("⑧ 새 원문의 숫자 사이 점만 벌리면 기준과 글자 그대로", re.sub(r"(\d)\.(?=\d)", r"\1. ", bn) == bb)
        gn.goto(U(PN, "/meetings/%d" % sn["ids"]["D1"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#mtgBody", timeout=20000)
        chk("화면 「회의 내용(원문)」 칸에도 「1.2%」", "1.2%" in gn.input_value("#mtgBody"))
        gn.screenshot(path=os.path.join(SHOTS, "q89_meeting_body.png"), full_page=False)
        gb.goto(U(PB, "/meetings/%d" % sb["ids"]["D1"]), wait_until="domcontentloaded")
        gb.wait_for_selector("#mtgBody", timeout=20000)
        chk("🔴 반대: 기준 화면 「회의 내용(원문)」 칸은 「1. 2%」", "1. 2%" in gb.input_value("#mtgBody"))
        gb.screenshot(path=os.path.join(SHOTS, "q89_meeting_body_before.png"), full_page=False)

        print("\n── ⑥ 「한국어+베트남어 섞임」 ──")
        dn6, bn6, cn6, tn6 = run_meeting(gn, PN, "app_new", sn["ids"]["D2"], "mix")
        db6, bb6, cb6, tb6 = run_meeting(gb, PB, "app_base", sb["ids"]["D2"], "mix")
        chk("두 벌 모두 끝 · 조각 받아쓰기(0·1·2(빈칸→다시))", dn6 and db6 and [t["file"] for t in tn6] == [t["file"] for t in tb6]
            and [t["file"] for t in tn6][:2] == ["part_000.mp3", "part_001.mp3"], ([t["file"] for t in tn6], [t["file"] for t in tb6]))
        chk("새 원문: 「3.5 triệu」「0.2 mm」「1.2%」「3.5백만」 그대로",
            all(x in bn6 for x in ("3.5 triệu", "0.2 mm", "1.2%", "3.5백만")), bn6)
        chk("🔴 반대: 기준은 「3. 5 triệu」「0. 2 mm」「1. 2%」", all(x in bb6 for x in ("3. 5 triệu", "0. 2 mm", "1. 2%")), bb6)
        mk = lambda cs: cs[-1]["user"].count("〔베트남어〕") if cs else -1
        chk("베트남어 표시 문장 수 기준과 같다(%d · 「1. 2%%」도 한 문장)" % mk(cn6), mk(cn6) == mk(cb6) == 4, (mk(cn6), mk(cb6)))
        chk("⑧ 새 원문의 숫자 사이 점만 벌리면 기준과 글자 그대로", re.sub(r"(\d)\.(?=\d)", r"\1. ", bn6) == bb6)

        print("\n── ⑦ 음성 메모 녹음 올리기 ──")
        rn, cn7 = run_note(gn, PN, "app_new")
        rb, cb7 = run_note(gb, PB, "app_base")
        chk("새 메모 원문 = 받아쓴 글 그대로(「1.2%」)", rn.get("body") == DEC, rn.get("body"))
        chk("🔴 반대: 기준 메모는 「1. 2%」", "1. 2%" in (rb.get("body") or ""))
        chk("정리 AI 가 보는 글도 「1.2%」", cn7 and "1.2%" in cn7[-1]["user"])
        chk("⑧ 숫자 사이 점만 다르다", re.sub(r"(\d)\.(?=\d)", r"\1. ", rn.get("body") or "") == (rb.get("body") or ""))

        print("\n── ⑨ 콘솔 ──")
        chk("새것 화면 콘솔 오류 0", not [e for e in en if KNOWN not in e], en[:3])
        chk("기준 화면 콘솔 오류 0", not [e for e in eb if KNOWN not in e], eb[:3])
        br.close()
finally:
    kill(pb, pn)
    try:
        os.remove(WAV)
    except Exception:
        pass

print("\n사진: %s" % SHOTS)
print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
