# -*- coding: utf-8 -*-
"""z1195 검사기 — 음성 메모 「📁 녹음 다시 올리기」.
대표 2026-10-21 「그리고 음성메모 녹음파일을 한번 잘 못 올리면 수정할 방법이 없어... 파일 다시 올리기 기능이 필요해」 →
「이대로 만들기」(원문은 새 녹음으로 바꿈 · 정리 새로 · 지금 정리는 「↩ 이전 정리」 · 자동 일시만 새로 · 사람이 적은 일시·제목 그대로 · 먼저 올린 녹음은 서버에 남김)
· 「회귀 통과하면 올리기」

재는 것 (앱 두 벌 = 운영 그대로(app_base) · 새것(app_new) · 진짜 서버 · 진짜 브라우저 · 받아쓰기·정리는 맨 끝 함수만 가짜)
  ━ 서버 안 띄움 ━
  ① 그 밖의 파일 글자 그대로(정리 지시문 ai_client 포함) · ② 바뀐 자리(main.py 정해 둔 여덟 줄 · 화면 두 줄 · 전역 timedelta 안 씀) · ③ 마이그레이션 두 번
  ━ 진짜 서버 ━
  ④ 단추: 원문 있는 메모만 「📁 녹음 다시 올리기」 · 빈 메모는 처음 올리기 칸 · 🔴 반대: 운영엔 없음
  ⑤ 누르면 「쓰는 말」·파일 칸 · 글 「📁 바꿀 녹음 파일 고르기」 · 「취소」 → 처음대로
  ⑥ R1 브라우저로 끝까지: 확인 창 → 올리기 → 받아쓰기 → 정리 · 원문 = 새 녹음 글만(옛 글 없음) · 정리 새로 · 이전 정리 = 옛 정리 · 녹음 경로 바뀜 ·
     먼저 올린 녹음 파일 그대로 · 일시 = 새 녹음 시각(자동분) · 화면도 새 원문·일시 · 칸 닫힘 · 기록 [VN-REUPLOAD-Z1195] 글자 수만
  ⑦ R7 확인 창 「취소」 → 아무것도 안 바뀜 · ⑧ R2 사람이 고친 일시 그대로 · R5 파일 시각 없이 → 자동 일시 비움
  ⑨ R4 사람이 고친 정리 → 다시 정리 전에 묻고 · 이전 정리로 보관 · ⑩ 처음 올리기·replace 없는 받아쓰기 = 덧붙이기 그대로 · 🔴 반대: 운영은 replace 를 몰라 덧붙임
  ⑪ R6 받아쓰기 도는 중엔 다시 올리기 막음 · ⑫ 권한(남의 메모 404 · 비로그인 401) · ⑬ 휴대폰 390 · ⑭ 콘솔 오류 0
쓰는 법: py q95_check.py <app_base·app_new 가 있는 폴더>   판정: 종료코드(0=통과) + 요약 줄.  🔒 시험 글은 모두 지어낸 것.
"""
import difflib
import hashlib
import importlib.util
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1] if len(sys.argv) > 1 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
PB, PN = 8957, 8958
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
KNOWN = "Transition was skipped"
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
    pr = subprocess.Popen([P313, os.path.join(HERE, "run_q95_app.py"), os.path.join(APPDIR, app), str(port)],
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


def row(app, nid):
    return db(app, "SELECT * FROM voice_notes WHERE id=?", (nid,))[0]


def md5(app, rel):
    return hashlib.md5(io.open(os.path.join(APPDIR, app, "app", rel), "rb").read()).hexdigest()


def rd(app, rel):
    return io.open(os.path.join(APPDIR, app, "app", rel), encoding="utf-8").read()


def diff(a, b):
    return [d for d in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0)
            if d[:1] in "+-" and not d.startswith(("+++", "---"))]


def ffmake(path, secs):
    subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "sine=frequency=440:sample_rate=16000:duration=%s" % secs, "-ac", "1", path], check=True)


def kfmt(ts, hrs):
    return datetime.fromtimestamp(ts, timezone(timedelta(hours=hrs)))


def wd(d):
    return "월화수목금토일"[d.weekday()]


def wait_until(fn, timeout=40.0, step=0.3):
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


# ═══════════════════════ 서버 안 띄움 ═══════════════════════
print("── ① 그 밖의 파일 글자 그대로 ──")
for rel in ("ai_client.py", "i18n.py", "templates/_v5_partials/knk_md_lite.html", "templates/voice_notes.html",
            "templates/meeting_doc.html", "templates/meeting_form.html", "templates/meeting_viz.html",
            "templates/_v5_partials/styles.html", "templates/_v5_partials/knk_ai_busy.html",
            "migrations/m_z1194_voice_note_meta.py"):
    chk("그대로: %s" % rel, md5("app_base", rel) == md5("app_new", rel))
chk("새 파일: 마이그레이션 m_z1195", os.path.exists(os.path.join(APPDIR, "app_new", "app", "migrations", "m_z1195_voice_note_when_auto.py"))
    and not os.path.exists(os.path.join(APPDIR, "app_base", "app", "migrations", "m_z1195_voice_note_when_auto.py")))

print("\n── ② 바뀐 자리 ──")
mb, mn = rd("app_base", "main.py"), rd("app_new", "main.py")
dm = diff(mb, mn)
rem = sorted(d[1:] for d in dm if d.startswith("-"))
EXP_REM = sorted([
    'def _vn_worker(nid: int, disk: str, lang: str = ""):',
    "    lang: 'ko'/'vi'/'en' 또는 ''(자동 감지) — z1165 에서 화면이 보내 준다.\"\"\"",
    '                body = ((prev + "\\n\\n") if prev else "") + text.strip()',
    '                                      rec_end_ms: str = Form("")):',
    '        if _mw:',
    '            c.execute("UPDATE voice_notes SET meta_when=? WHERE id=? AND TRIM(COALESCE(meta_when,\'\'))=\'\'", (_mw, nid))',
    '    return JSONResponse({"ok": True, "size_kb": _n // 1024, "meta_when": ((_r["meta_when"] if _r else "") or "")})',
    '    _stt_thr.Thread(target=_vn_worker, args=(nid, disk, lang or ""), daemon=True).start()',
])
chk("main.py 바뀐 줄 = 정해 둔 여덟 줄(일꾼 머리·설명 · 원문 합치기 · 일꾼 부르기 · 올리기 머리 · 자동 일시 셋)", rem == EXP_REM, rem)
add = [d[1:] for d in dm if d.startswith("+")]
chk("main.py 더한 줄 %d(보고용)" % len(add), 20 <= len(add) <= 45, len(add))
chk("전역 timedelta 안 씀", not any("timedelta" in a for a in add))
chk("기동 마이그레이션 · 일꾼 replace · 올리기 replace", mn.count("[VOICE-WHENAUTO-MIG-Z1195]") == 1
    and 'def _vn_worker(nid: int, disk: str, lang: str = "", replace: bool = False):' in mn
    and 'replace: str = Form("")' in mn and mn.count("args=(nid, disk, lang or \"\", _rep)") == 1)
chk("🔴 반대: 운영 일꾼은 늘 덧붙인다", 'body = ((prev + "\\n\\n") if prev else "") + text.strip()' in mb and "replace" not in mb.split("def _vn_worker(")[1].split("\n@app.")[0])
fb, fn = rd("app_base", "templates/voice_note_form.html"), rd("app_new", "templates/voice_note_form.html")
remf = sorted(d[1:] for d in diff(fb, fn) if d.startswith("-"))
chk("화면 파일 바뀐 줄 = 두 줄(올리기 글을 칸으로 · 받아쓰기 요청)", remf == sorted([
    "      <label class=\"vn-up\">📁 녹음 파일 올리기",
    "        body: JSON.stringify({ lang: (($('vnLang')||{}).value) || '' }) });   // z1165"]), remf)

print("\n── ③ 마이그레이션 두 번 ──")
spec = importlib.util.spec_from_file_location("m95", os.path.join(APPDIR, "app_new", "app", "migrations", "m_z1195_voice_note_when_auto.py"))
m95 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m95)
tmpd = tempfile.mkdtemp(prefix="q95_")
tdb = os.path.join(tmpd, "m.db")
cc = sqlite3.connect(tdb)
cc.execute("CREATE TABLE voice_notes(id INTEGER PRIMARY KEY, meta_when TEXT NOT NULL DEFAULT '')")
cc.execute("INSERT INTO voice_notes(meta_when) VALUES('x')")
cc.commit()
cc.close()
r1, r2 = m95.migrate(tdb), m95.migrate(tdb)
cc = sqlite3.connect(tdb)
v = cc.execute("SELECT meta_when, meta_when_auto FROM voice_notes").fetchone()
cc.close()
chk("첫 번째 = 칸 더함 · 두 번째 = 없음 · 옛 줄은 빈 글(= 사람이 적은 일시로 본다)", r1["added"] == ["voice_notes.meta_when_auto"] and r2["added"] == [] and v == ("x", ""), (r1, r2, v))
tdb2 = os.path.join(tmpd, "m2.db")
sqlite3.connect(tdb2).close()
chk("표가 없으면 건너뜀", m95.migrate(tdb2).get("skip") == "voice_notes 없음")

# ═══════════════════════ 진짜 서버 + 진짜 브라우저 ═══════════════════════
W95 = os.path.join(tmpd, "new95.wav")
W40 = os.path.join(tmpd, "new40.wav")
WSLOW = os.path.join(tmpd, "slow.wav")
ffmake(W95, "95")
ffmake(W40, "40")
ffmake(WSLOW, "7")
END = int(time.time() - 3600)
os.utime(W95, (END, END))          # 브라우저가 보내는 파일 시각(lastModified) = 이 파일 수정 시각
prb, SB = boot("app_base", PB)
prn, SN = boot("app_new", PN)
ME, I = SN["me"], SN["ids"]
chk("두 벌 같은 메모 번호", SB["ids"] == SN["ids"])
chk("새것만 자동 일시 칸(운영 = 없음)", SN["has_auto"] and not SB["has_auto"])
chk("기동 기록 [VOICE-WHENAUTO-MIG-Z1195] 칸 하나",
    "[VOICE-WHENAUTO-MIG-Z1195] {'added': ['voice_notes.meta_when_auto']}" in io.open(os.path.join(APPDIR, "srv_%d.log" % PN), encoding="utf-8").read())
errs = {"b": [], "n": []}
DLG = []
try:
    with sync_playwright() as pw:
        br = pw.chromium.launch()

        def mk(port, uid, w=1366, h=900, mobile=False, dialog="accept"):
            kw = dict(viewport={"width": w, "height": h}, locale="ko-KR")
            if mobile:
                kw.update(device_scale_factor=2, is_mobile=True, has_touch=True)
            cx = br.new_context(**kw)
            cx.add_cookies([{"name": "tuser", "value": str(uid), "url": U(port, "/")}])
            pg = cx.new_page()
            k = "n" if port == PN else "b"
            pg.on("console", lambda m: errs[k].append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errs[k].append("pageerror: %s" % e))
            pg._dlg = {"mode": dialog}

            def _d(d):
                DLG.append((k, d.type, d.message))
                d.accept() if pg._dlg["mode"] == "accept" else d.dismiss()
            pg.on("dialog", _d)
            return cx, pg

        cxb, gb = mk(PB, ME)
        cxn, gn = mk(PN, ME)

        def api(pg, port, path, body=None, method="POST"):
            r = pg.request.fetch(U(port, path), method=method, data=json.dumps(body) if body is not None else None,
                                 headers={"Content-Type": "application/json"})
            try:
                return r.status, r.json()
            except Exception:
                return r.status, {}

        def up(pg, port, nid, wav, ms=None, replace=False):
            mp = {"file": {"name": "rec.wav", "mimeType": "audio/wav", "buffer": io.open(wav, "rb").read()}}
            if ms is not None:
                mp["rec_end_ms"] = str(ms)
            if replace:
                mp["replace"] = "1"
            r = pg.request.post(U(port, "/api/voice-note/%d/audio" % nid), multipart=mp)
            try:
                return r.status, r.json()
            except Exception:
                return r.status, {}

        def stt_done(pg, port, nid):
            return wait_until(lambda: (api(pg, port, "/api/voice-note/%d/stt-status" % nid, method="GET")[1].get("state") in ("done", "error")), 40)

        def sum_done(pg, port, nid):
            return wait_until(lambda: (api(pg, port, "/api/voice-note/%d/extract-status" % nid, method="GET")[1].get("state") in ("done", "error")), 40)

        # ═══════════ ④ 단추 ═══════════
        print("\n── ④ 단추 ──")
        gn.goto(U(PN, "/voice-notes/%d" % I["R1"]), wait_until="networkidle")
        gb.goto(U(PB, "/voice-notes/%d" % I["R1"]), wait_until="networkidle")
        vis = "(id) => { const e = document.getElementById(id); return !!(e && e.offsetParent); }"
        chk("원문 있는 메모(R1): 「📁 녹음 다시 올리기」 보임 · 처음 올리기 칸·쓰는 말 숨김",
            gn.evaluate(vis, "vnReup") and not gn.evaluate(vis, "vnUpWrap") and not gn.evaluate(vis, "vnLangWrap"))
        chk("단추 글 「📁 녹음 다시 올리기」", gn.inner_text("#vnReup").strip() == "📁 녹음 다시 올리기")
        chk("🔴 반대: 운영 화면엔 다시 올리기 없음", gb.locator("#vnReup").count() == 0)
        gn.screenshot(path=os.path.join(SHOTS, "q95_R1_before.png"))
        gn.goto(U(PN, "/voice-notes/%d" % I["R3"]), wait_until="networkidle")
        chk("빈 메모(R3): 다시 올리기 숨김 · 처음 올리기 칸 보임(글 그대로)", not gn.evaluate(vis, "vnReup") and gn.evaluate(vis, "vnUpWrap")
            and gn.inner_text("#vnUpTxt").strip() == "📁 녹음 파일 올리기")
        gn.goto(U(PN, "/voice-notes/new"), wait_until="networkidle")
        chk("새 메모 화면: 다시 올리기 없음 · 처음 올리기 칸", not gn.evaluate(vis, "vnReup") and gn.evaluate(vis, "vnUpWrap"))

        # ═══════════ ⑤ 누르기 · 취소 ═══════════
        print("\n── ⑤ 누르면 칸이 열리고 · 취소 ──")
        gn.goto(U(PN, "/voice-notes/%d" % I["R1"]), wait_until="networkidle")
        gn.click("#vnReup")
        gn.wait_for_function("document.getElementById('vnUpWrap').offsetParent !== null")
        chk("쓰는 말·파일 칸 보임 · 글 「📁 바꿀 녹음 파일 고르기」 · 취소 보임 · 다시 올리기 줄 숨김",
            gn.evaluate(vis, "vnLangWrap") and gn.inner_text("#vnUpTxt").strip() == "📁 바꿀 녹음 파일 고르기"
            and gn.evaluate(vis, "vnReupCancel") and not gn.evaluate(vis, "vnReup"))
        chk("안내 글", "바꿀 녹음 파일을 고르세요" in gn.inner_text("#vnSt"))
        gn.screenshot(path=os.path.join(SHOTS, "q95_R1_reup_open.png"))
        gn.click("#vnReupCancel")
        chk("취소 → 처음대로(칸 닫힘 · 글 되돌림 · 다시 올리기 보임)", not gn.evaluate(vis, "vnUpWrap") and not gn.evaluate(vis, "vnLangWrap")
            and gn.evaluate(vis, "vnReup") and gn.inner_text("#vnUpTxt").strip() == "📁 녹음 파일 올리기")

        # ═══════════ ⑥ R1 끝까지(브라우저) ═══════════
        print("\n── ⑥ R1 다시 올리기 끝까지 ──")
        r1b = row("app_new", I["R1"])
        old_path = r1b["audio_path"]
        gn.click("#vnReup")
        gn.select_option("#vnLang", "ko")
        n_dlg = len(DLG)
        gn.set_input_files("#vnFile", W95)
        ok_end = wait_until(lambda: "정리가 끝났습니다" in gn.inner_text("#vnSt"), 60)
        chk("확인 창이 한 번 떴다(바꿀까요)", len(DLG) == n_dlg + 1 and "바꿀까요" in DLG[-1][2] and "이전 정리" in DLG[-1][2], DLG[n_dlg:])
        chk("올리기 → 받아쓰기 → 정리 끝", ok_end, gn.inner_text("#vnSt"))
        r1 = row("app_new", I["R1"])
        sz = os.path.getsize(W95)
        chk("원문 = 새 녹음 글만(옛 원문 없음 · 덧붙이지 않음)", r1["body"] == "새 녹음 받아쓴 글 — %d바이트 · 말 ko" % sz and "옛 원문" not in r1["body"], r1["body"][:80])
        chk("정리 = 새 원문으로 · 이전 정리 = 옛 정리", r1["summary"].startswith("## 핵심\n정리: 새 녹음 받아쓴 글") and r1["summary_prev"] == SN["old_sum"], (r1["summary"][:40], r1["summary_prev"][:30]))
        chk("제목은 그대로(사람이 지은 제목 · AI 제목으로 안 바꿈)", r1["title"] == "다시 올리기 시험 1(지어낸 글)")
        chk("녹음 경로 바뀜 · 먼저 올린 녹음 파일은 서버에 그대로", r1["audio_path"] != old_path and os.path.exists(os.path.join(APPDIR, "app_new", old_path)), (old_path, r1["audio_path"]))
        e9, s9 = kfmt(END, 9), kfmt(END - 120, 9)
        exp9 = "%s (%s) %s ~ %s (2분)" % (s9.strftime("%Y-%m-%d"), wd(s9), s9.strftime("%H:%M"), e9.strftime("%H:%M"))
        chk("일시 = 새 녹음 시각(자동분이라 바꿈) · 자동 칸도 같은 글", r1["meta_when"] == exp9 and r1["meta_when_auto"] == exp9, (r1["meta_when"], exp9))
        chk("화면: 새 원문 · 새 일시 · 칸 닫힘 · 다시 올리기 보임",
            gn.input_value("#vnBody") == r1["body"] and gn.input_value("#vnWhen") == exp9 and not gn.evaluate(vis, "vnUpWrap")
            and not gn.evaluate(vis, "vnLangWrap") and gn.evaluate(vis, "vnReup"))
        chk("「↩ 이전 정리」 단추 보임", gn.evaluate(vis, "vnPrev"))
        calls = api(gn, PN, "/__test/calls", method="GET")[1]
        chk("받아쓰기에 고른 말(ko) 그대로", calls["stt"] and calls["stt"][-1]["lang"] == "ko", calls["stt"][-1:])
        lg = io.open(os.path.join(APPDIR, "srv_%d.log" % PN), encoding="utf-8").read()
        m = re.findall(r"\[VN-REUPLOAD-Z1195\] 메모 (\d+): 녹음을 바꿔 원문을 새로 · (\d+)자 → (\d+)자", lg)
        chk("기록 [VN-REUPLOAD-Z1195] = 메모 번호·글자 수만(글 내용 없음)", m and m[-1] == (str(I["R1"]), str(len(SN["old_body"])), str(len(r1["body"])))
            and "옛 원문" not in "".join(ln for ln in lg.splitlines() if "VN-REUPLOAD" in ln), m)
        gn.screenshot(path=os.path.join(SHOTS, "q95_R1_after.png"))

        # ═══════════ ⑦ 확인 창 취소 ═══════════
        print("\n── ⑦ R7 확인 창 「취소」 ──")
        cxd, gd = mk(PN, ME, dialog="dismiss")
        gd.goto(U(PN, "/voice-notes/%d" % I["R7"]), wait_until="networkidle")
        before = row("app_new", I["R7"])
        files0 = sorted(os.listdir(os.path.join(SN["vn_dir"], "note_%d" % I["R7"])))
        gd.click("#vnReup")
        gd.wait_for_function("document.getElementById('vnUpWrap').offsetParent !== null")   # 칸이 열린 뒤(사람도 그 뒤에야 고른다)
        gd.set_input_files("#vnFile", W40)
        gd.wait_for_timeout(1500)
        after = row("app_new", I["R7"])
        chk("취소하면 올리지 않음(원문·정리·녹음·일시 그대로 · 파일 수 그대로)", {k: after[k] for k in ("body", "summary", "audio_path", "meta_when")}
            == {k: before[k] for k in ("body", "summary", "audio_path", "meta_when")}
            and sorted(os.listdir(os.path.join(SN["vn_dir"], "note_%d" % I["R7"]))) == files0)
        chk("칸은 열린 채(다시 고르거나 「취소」)", gd.evaluate(vis, "vnUpWrap") and gd.evaluate(vis, "vnReupCancel"))
        cxd.close()

        # ═══════════ ⑧ 일시 — 사람이 고친 것 · 파일 시각 없음 ═══════════
        print("\n── ⑧ 일시 ──")
        st_, j = up(gn, PN, I["R2"], W95, END * 1000, replace=True)
        r2 = row("app_new", I["R2"])
        chk("사람이 고친 일시(R2)는 그대로 · 답에 replaced", st_ == 200 and j.get("replaced") is True and j.get("meta_when") == "사람이 적은 일시"
            and r2["meta_when"] == "사람이 적은 일시" and r2["meta_when_auto"] == SN["auto_old"], (j, r2["meta_when"]))
        st_, j = up(gn, PN, I["R5"], W95, None, replace=True)
        r5 = row("app_new", I["R5"])
        chk("자동 일시(R5) + 새 녹음 시각 모름 → 비움(잘못 올린 녹음 시각을 남기지 않음)", st_ == 200 and j.get("meta_when") == ""
            and r5["meta_when"] == "" and r5["meta_when_auto"] == "", (j, r5["meta_when"], r5["meta_when_auto"]))
        st_, j = api(gn, PN, "/api/voice-note/%d/transcribe" % I["R2"], {"lang": "", "replace": True})
        stt_done(gn, PN, I["R2"])
        chk("API 로 받아쓰기 replace → 원문 바꿈", row("app_new", I["R2"])["body"] == "새 녹음 받아쓴 글 — %d바이트 · 말 자동" % sz)

        # ═══════════ ⑨ 사람이 고친 정리 ═══════════
        print("\n── ⑨ R4 사람이 고친 정리 ──")
        gn.goto(U(PN, "/voice-notes/%d" % I["R4"]), wait_until="networkidle")
        n_dlg = len(DLG)
        gn.click("#vnReup")
        gn.wait_for_function("document.getElementById('vnUpWrap').offsetParent !== null")
        gn.set_input_files("#vnFile", W40)
        ok4 = wait_until(lambda: "정리가 끝났습니다" in gn.inner_text("#vnSt"), 60)
        msgs = [d[2] for d in DLG[n_dlg:]]
        chk("확인 창 둘(바꿀까요 → 사람이 고친 정리가 있습니다)", len(msgs) == 2 and "바꿀까요" in msgs[0] and "사람이 고친 정리" in msgs[1], msgs)
        r4 = row("app_new", I["R4"])
        chk("새 정리 · 이전 정리 = 사람이 고친 정리", ok4 and r4["summary"].startswith("## 핵심\n정리: 새 녹음") and r4["summary_prev"].startswith("## 핵심\n사람이 고친 정리"), (r4["summary"][:30], r4["summary_prev"][:30]))

        # ═══════════ ⑩ 덧붙이기 그대로 · 운영 대조 ═══════════
        print("\n── ⑩ 처음 올리기·replace 없는 받아쓰기 = 덧붙이기 그대로 ──")
        up(gn, PN, I["R3"], W40, END * 1000)
        api(gn, PN, "/api/voice-note/%d/transcribe" % I["R3"], {"lang": ""})
        stt_done(gn, PN, I["R3"])
        b1 = row("app_new", I["R3"])["body"]
        api(gn, PN, "/api/voice-note/%d/transcribe" % I["R3"], {"lang": ""})
        time.sleep(0.5)
        stt_done(gn, PN, I["R3"])
        b2 = row("app_new", I["R3"])["body"]
        sz40 = os.path.getsize(W40)
        t40 = "새 녹음 받아쓴 글 — %d바이트 · 말 자동" % sz40
        chk("처음 받아쓰기 = 그 글 · replace 없이 한 번 더 = 뒤에 덧붙임(예전 그대로)", b1 == t40 and b2 == t40 + "\n\n" + t40, (b1[:40], b2[:90]))
        st_, j = up(gb, PB, I["R6"], W40, END * 1000, replace=True)
        api(gb, PB, "/api/voice-note/%d/transcribe" % I["R6"], {"lang": "", "replace": True})
        stt_done(gb, PB, I["R6"])
        b6 = db("app_base", "SELECT body FROM voice_notes WHERE id=?", (I["R6"],))[0]["body"]
        chk("🔴 반대: 운영은 replace 를 몰라 옛 원문 뒤에 덧붙인다", b6.startswith(SB["old_body"]) and b6.endswith(t40) and "replaced" not in j, (b6[:60], j))

        # ═══════════ ⑪ 받아쓰기 도는 중 ═══════════
        print("\n── ⑪ R6 받아쓰기 도는 중엔 막기 ──")
        api(gn, PN, "/__test/slow/%d" % os.path.getsize(WSLOW))
        up(gn, PN, I["R6"], WSLOW, END * 1000)
        api(gn, PN, "/api/voice-note/%d/transcribe" % I["R6"], {"lang": ""})
        gn.goto(U(PN, "/voice-notes/%d" % I["R6"]), wait_until="networkidle")
        gn.click("#vnReup")
        gn.wait_for_timeout(800)
        chk("도는 중 → 「끝난 뒤에 다시」 · 칸 안 열림", "끝난 뒤에 다시" in gn.inner_text("#vnSt") and not gn.evaluate(vis, "vnUpWrap"), gn.inner_text("#vnSt"))
        stt_done(gn, PN, I["R6"])
        api(gn, PN, "/__test/slow/-1")

        # ═══════════ ⑫ 권한 ═══════════
        print("\n── ⑫ 권한 ──")
        st_, j = up(gn, PN, I["RO"], W40, END * 1000, replace=True)
        chk("남의 메모 다시 올리기 → 404", st_ == 404, (st_, j))
        st_, j = api(gn, PN, "/api/voice-note/%d/transcribe" % I["RO"], {"lang": "", "replace": True})
        chk("남의 메모 받아쓰기 replace → 404", st_ == 404, (st_, j))
        chk("남의 메모 그대로", row("app_new", I["RO"])["body"] == SN["old_body"])
        cx0 = br.new_context()
        cx0.add_cookies([{"name": "tuser", "value": "0", "url": U(PN, "/")}])
        p0 = cx0.new_page()
        r0 = p0.request.post(U(PN, "/api/voice-note/%d/transcribe" % I["R1"]), data=json.dumps({"replace": True}), headers={"Content-Type": "application/json"})
        chk("비로그인 → 401", r0.status == 401, r0.status)
        cx0.close()

        # ═══════════ ⑬ 휴대폰 ═══════════
        print("\n── ⑬ 휴대폰 390 ──")
        cxm, gm = mk(PN, ME, 390, 844, mobile=True)
        gm.goto(U(PN, "/voice-notes/%d" % I["R1"]), wait_until="networkidle")
        gm.wait_for_timeout(800)
        gm.evaluate("() => { const b = Array.from(document.querySelectorAll('button')).find(x => x.textContent.trim() === '닫기' && x.offsetParent); if (b) b.click(); }")
        chk("다시 올리기 단추 보임 · 가로 넘침 없음", gm.evaluate(vis, "vnReup") and gm.evaluate("document.documentElement.scrollWidth") <= 392)
        gm.click("#vnReup")
        gm.wait_for_timeout(400)
        chk("휴대폰에서도 칸이 열림 · 넘침 없음", gm.evaluate(vis, "vnUpWrap") and gm.evaluate("document.documentElement.scrollWidth") <= 392)
        gm.screenshot(path=os.path.join(SHOTS, "q95_phone_open.png"))
        cxm.close()

        print("\n── ⑭ 콘솔 ──")
        on = [e for e in errs["n"] if KNOWN not in e]
        ob = [e for e in errs["b"] if KNOWN not in e]
        chk("새것 콘솔 오류 0", not on, on[:3])
        chk("운영 콘솔 오류 0", not ob, ob[:3])
        br.close()
finally:
    kill(prb, prn)
    freeport(PB)
    freeport(PN)

print("\n=============================================")
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
