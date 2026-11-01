# -*- coding: utf-8 -*-
"""z1200 음성 메모 베트남어(B안) 검사 — 운영 그대로(app_base)와 새것(app_new)을 나란히.
  ① 안 건드린 것: ai_client.py · 한국어 지시문 · 바뀐 파일 목록
  ② 한국어 사용자: 화면(사전 줄 뺀) 글자 그대로 · 정리 = 한국어 지시문
  ③ 베트남어 사용자: 목록·상세 화면에 메뉴 말고 한글 없음 · 사전 빠짐 0
  ④ 정리: 베트남어 지시문 · 저장 · 제목(빈 칸만) · 받아쓴 원문 그대로 · 표시 색 · 실패 안내
  ⑤ 고치기·복사·이미지·파일·서버 오류 말 · 자동 일시
쓰는 법: py -3.12 q200_check.py <app_base·app_new 가 있는 폴더>   🔒 시험 글은 모두 지어낸 것 · 실제 AI 안 부름."""
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

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1] if len(sys.argv) > 1 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
RUN = os.path.join(HERE, "run_q200_app.py")
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
PORTS = {"app_base": 8981, "app_new": 8982}
N = OK = 0
FAILS = []
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
    lp = os.path.join(APPDIR, "srv00_%d.log" % port)
    pr = subprocess.Popen([P313, RUN, os.path.join(APPDIR, app), str(port)], stdout=io.open(lp, "w", encoding="utf-8"),
                          stderr=subprocess.STDOUT, cwd=APPDIR)
    for _ in range(90):
        time.sleep(1)
        txt = io.open(lp, encoding="utf-8", errors="replace").read()
        for ln in txt.splitlines():
            if ln.startswith("READY"):
                return pr, json.loads(ln.split(" ", 2)[2])
        if pr.poll() is not None:
            break
    print("⛔ %s 서버가 안 떴다" % app)
    print(io.open(lp, encoding="utf-8", errors="replace").read()[-1500:])
    sys.exit(2)


def rd(app, rel):
    return io.open(os.path.join(APPDIR, app, "app", rel), encoding="utf-8").read()


def walk(app):
    root = os.path.join(APPDIR, app, "app")
    out = {}
    for d, _x, files in os.walk(root):
        if "__pycache__" in d:
            continue
        for f in files:
            if not f.endswith((".pyc", ".bak_z1200")):
                full = os.path.join(d, f)
                out[os.path.relpath(full, root).replace("\\", "/")] = hashlib.md5(io.open(full, "rb").read()).hexdigest()
    return out


def http(port, path, uid, data=None, method=None):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), data=(json.dumps(data).encode() if data is not None else None), method=method)
    req.add_header("Cookie", "tuser=%s" % uid)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
        except (ConnectionError, urllib.error.URLError):
            if attempt == 2:
                raise
            time.sleep(1)   # 윈도 시험 PC 연결 끊김(10053) 한 번은 다시


def db(app):
    return sqlite3.connect(os.path.join(APPDIR, app, "data", "knk.db"), timeout=15)


def wait_sum(port, nid, uid):
    for _ in range(40):
        st, b = http(port, "/api/voice-note/%d/extract-status" % nid, uid)
        if st == 200 and json.loads(b).get("state") in ("done", "error", "idle"):
            return json.loads(b)
        time.sleep(0.25)
    return {}


print("== ① 안 건드린 것 ==")
WB, WN = walk("app_base"), walk("app_new")
changed = sorted(k for k in set(WB) | set(WN) if WB.get(k) != WN.get(k))
chk("바뀐 파일 = main · 새 모듈 · 화면 2 · 표시 그리기", changed == ["main.py", "templates/_v5_partials/knk_md_lite.html", "templates/voice_note_form.html", "templates/voice_notes.html", "voice_note_vi.py"], str(changed))
chk("🔴 ai_client.py(실증된 지시문) 글자 하나 안 바뀜", WB["ai_client.py"] == WN["ai_client.py"])
chk("회의록 화면 안 바뀜", WB["templates/meeting_form.html"] == WN["templates/meeting_form.html"])

srv = {}
try:
    for app in PORTS:
        srv[app] = start(app)
    PB, PN = PORTS["app_base"], PORTS["app_new"]
    SB = json.load(io.open(os.path.join(HERE, "seed_%d.json" % PB), encoding="utf-8"))
    SN = json.load(io.open(os.path.join(HERE, "seed_%d.json" % PN), encoding="utf-8"))
    IB, IN = SB["ids"], SN["ids"]
    VI, MEM = SN["vi1"], SN["mem"]

    print("== ② 한국어 사용자 ==")
    norm = lambda t: re.sub(r'var LOADED = "t\d+"', 'var LOADED="tX"', re.sub(r"\?v=[\w.-]+", "?v=X", t))
    for nm, pathb, pathn in (("목록", "/voice-notes", "/voice-notes"), ("상세", "/voice-notes/%d" % IB["V4"], "/voice-notes/%d" % IN["V4"]), ("새 메모", "/voice-notes/new", "/voice-notes/new")):
        _, hb = http(PB, pathb, SB["mem"])
        _, hn = http(PN, pathn, MEM)
        d = [x for x in __import__("difflib").unified_diff(norm(hb).splitlines(), norm(hn).splitlines(), lineterm="", n=0) if x[:1] in "+-" and not x.startswith(("+++", "---"))]
        rest = [x for x in d if x[1:].strip() and "var _VND = {}" not in x and "function _vnL(s)" not in x and "_vnL(" not in x and x[0] != "-"]
        #  뺀 줄 = 스크립트 안 글자열을 감싼 줄뿐 → 감싼 것을 벗기면 원래 줄과 같아야
        unwrap = lambda t: re.sub(r"_vnL\(('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\")\)", r"\1", t)
        hn2 = "\n".join(x for x in unwrap(norm(hn)).splitlines() if "var _VND = {}" not in x and "function _vnL(s)" not in x)
        d2 = [x for x in __import__("difflib").unified_diff(norm(hb).splitlines(), hn2.splitlines(), lineterm="", n=0) if x[:1] in "+-" and not x.startswith(("+++", "---")) and x[1:].strip() and "var TAGS = {" not in x and "var TAG_RE = " not in x]   # 표시 색(베트남어 네 가지 더함)만 허용
        chk("한국어 %s 화면 = 그대로(사전 줄·감싸기 빼면 차이 0)" % nm, not d2 and "var _VND = {}" in hn, str(d2[:3]))
    http(PN, "/api/voice-note/%d/extract" % IN["KO1"], MEM, {})
    wait_sum(PN, IN["KO1"], MEM)
    _, b = http(PN, "/__test/sys", MEM)
    sy = json.loads(b)["last"]
    chk("한국어 직원 = 한국어 지시문", "summary: 한국어" in sy and "베트남어로** 정리" not in sy)
    c = db("app_new")
    r = c.execute("SELECT title, summary FROM voice_notes WHERE id=?", (IN["KO1"],)).fetchone()
    chk("한국어 직원 정리 저장 = 한국어", r[0] == "2호기 점검" and "## 핵심" in r[1], str(r[0]))
    c.close()

    print("== ④ 정리(베트남어 직원) ==")
    c = db("app_new")
    body0 = c.execute("SELECT body FROM voice_notes WHERE id=?", (IN["VI1"],)).fetchone()[0]
    c.close()
    st, b = http(PN, "/api/voice-note/%d/extract" % IN["VI1"], VI, {})
    chk("정리 시작", st == 200, b[:80])
    wait_sum(PN, IN["VI1"], VI)
    _, b = http(PN, "/__test/sys", VI)
    sy = json.loads(b)["last"]
    chk("베트남어 직원 = 베트남어 지시문", "베트남어로** 정리" in sy and "## Trọng tâm" in sy and "[Quyết định]" in sy)
    chk("지시문에 회사 말·호기 규칙 · 메모 날짜", "máy số 2" in sy and "메모 날짜" in sy and "[회사 배경]" in sy)
    c = db("app_new")
    r = c.execute("SELECT title, summary, body FROM voice_notes WHERE id=?", (IN["VI1"],)).fetchone()
    chk("정리·제목 = 베트남어로 저장", r[0] == "Kiểm tra máy số 2" and "## Trọng tâm" in r[1] and "[Quyết định]" in r[1], r[0])
    chk("🔴 받아쓴 원문은 그대로", r[2] == body0)
    c.close()
    http(PN, "/api/voice-note/%d/extract" % IN["VI2"], VI, {})
    wait_sum(PN, IN["VI2"], VI)
    c = db("app_new")
    chk("🔴 사람이 지은 제목은 안 덮음", c.execute("SELECT title FROM voice_notes WHERE id=?", (IN["VI2"],)).fetchone()[0] == "Tiêu đề người đặt")
    c.close()
    http(PN, "/api/voice-note/%d/extract" % IN["VI4"], VI, {})
    wait_sum(PN, IN["VI4"], VI)
    c = db("app_new")
    sv = c.execute("SELECT summary FROM voice_notes WHERE id=?", (IN["VI4"],)).fetchone()[0]
    c.close()
    chk("맨 위 제목 빠진 답 = ## Trọng tâm 붙임 · 굵은 표시 벗김", sv.startswith("## Trọng tâm\n") and "- [Quyết định] Làm" in sv, sv[:60])
    http(PN, "/__test/note_fail/1", VI, {}, "POST")
    c = db("app_new")
    c.execute("UPDATE voice_notes SET summary='' WHERE id=?", (IN["VI2"],))
    c.commit()
    c.close()
    http(PN, "/api/voice-note/%d/extract" % IN["VI2"], VI, {})
    j = wait_sum(PN, IN["VI2"], VI)
    chk("정리 실패 = 베트남어 안내 · 실패면 정리 안 씀", j.get("state") == "error" and "Không xử lý được" in (j.get("error") or ""), str(j.get("error")))
    http(PN, "/__test/note_fail/0", VI, {}, "POST")

    print("== ⑤ 서버 말 ==")
    st, b = http(PN, "/api/voice-note/%d/extract" % IN["VI3"], VI, {})
    chk("베트남어 직원 오류 말", st == 400 and "Chưa có nội dung" in json.loads(b)["error"], b[:90])
    st, b = http(PN, "/api/voice-note/%d/extract" % IN["VI3"], MEM, {})
    chk("남의 메모 = 여전히 막힘", st == 404)
    st, b = http(PN, "/api/voice-note/%d/extract" % IN["KO1"], VI, {})
    chk("한국어 직원 메모도 베트남어 직원에게 막힘(말만 베트남어)", st == 404 and "Ghi chú không tồn tại" in json.loads(b)["error"])
    c = db("app_new")
    c.execute("UPDATE voice_notes SET body='', summary='' WHERE id=?", (IN["KO1"],))
    c.commit()
    c.close()
    st, b = http(PN, "/api/voice-note/%d/extract" % IN["KO1"], MEM, {})
    chk("한국어 직원 오류 말 = 한국어 그대로", st == 400 and "정리할 내용이 없습니다" in json.loads(b)["error"])

    sys.path.insert(0, os.path.join(APPDIR, "app_new"))
    print("== ③ 베트남어 화면 ==")
    HANGUL = re.compile(r"[가-힣]")
    with sync_playwright() as p:
        b = p.chromium.launch()
        for vw, tag in ((1440, "pc"), (390, "phone")):
            ctx = b.new_context(viewport={"width": vw, "height": 900}, accept_downloads=True)
            ctx.add_cookies([{"name": "tuser", "value": str(VI), "url": "http://127.0.0.1:%d" % PN}])
            ctx.add_init_script(NOHINT)
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:120]))
            base = "http://127.0.0.1:%d" % PN
            for nm, path in (("list", "/voice-notes"), ("new", "/voice-notes/new"), ("note", "/voice-notes/%d" % IN["VI1"])):
                pg.goto(base + path, wait_until="domcontentloaded")
                pg.wait_for_timeout(1300)
                main = pg.locator(".main").first if pg.locator(".main").count() else pg.locator("body")
                txt = main.inner_text()
                bad = [x for x in txt.splitlines() if HANGUL.search(x)]
                attrs = pg.evaluate("""() => [...document.querySelectorAll('.main [placeholder], .main [title], .main [aria-label], .main option')].flatMap(e => [e.placeholder, e.title, e.getAttribute('aria-label'), e.tagName==='OPTION'?e.textContent:'']).filter(x => x && /[가-힣]/.test(x))""")
                allow = [x for x in bad if "김직원" in x or "지어낸" in x]
                pg.screenshot(path=os.path.join(SHOTS, "vi_%s_%s.png" % (nm, tag)), full_page=True)
                chk("%s %s: 화면 글자에 한글 없음(데이터 빼고)" % (tag, nm), len(bad) == len(allow) and not attrs, str([x[:50] for x in bad if x not in allow][:4]) + str(attrs[:3]))
                w = pg.evaluate("[document.documentElement.scrollWidth, innerWidth]")
                chk("%s %s: 가로로 넘치지 않음" % (tag, nm), w[0] <= w[1] + 1, str(w))
            #  상세: 표시 색 · 고치기 · 복사 머리
            pg.goto(base + "/voice-notes/%d" % IN["VI1"], wait_until="domcontentloaded")
            pg.wait_for_selector("#vnSumBox .tg", timeout=8000)
            tags = pg.evaluate("[...document.querySelectorAll('#vnSumBox .tg')].map(e => [e.textContent, e.className])")
            chk("%s: [Quyết định]·[Đề xuất]·[Chưa quyết]·[Cần xác nhận] 색 표시" % tag, [x[1].split()[-1] for x in tags] == ["tg-dec", "tg-pro", "tg-und", "tg-chk"], str(tags))
            hd = pg.locator("#vnSumBox").inner_text()
            chk("%s: 정리 머리 = ■ Trọng tâm" % tag, "Trọng tâm" in hd and "Việc cần làm" in hd)
            pg.click("#vnSumEdit")
            ed = pg.input_value("#vnSumEdit2")
            chk("%s: ✏ Sửa = 베트남어 원래 글" % tag, ed.startswith("## Trọng tâm"))
            pg.click("#vnSumCancel")
            if tag == "pc":
                chk("단추 글자", pg.locator("#vnSumEdit").inner_text().strip() == "✏ Sửa" and "Tổng hợp lại" in pg.locator("#vnRedo").inner_text())
                pg.evaluate("window.__c=[];navigator.clipboard.writeText=function(t){window.__c.push(t);return Promise.resolve();}")
                pg.click("#vnCopy") if pg.locator("#vnCopy").count() else None
                pg.wait_for_timeout(300)
                st_t = pg.locator("#vnSt").inner_text() if pg.locator("#vnSt").count() else ""
                chk("복사 안내 = 베트남어", not HANGUL.search(st_t), st_t[:70])
                pg.click("#vnImg")
                pg.wait_for_selector(".vn-capbox", timeout=20000)
                pg.wait_for_timeout(500)
                cap = pg.locator(".vn-capbox").inner_text()
                chk("🖼 이미지 창 글자 = 베트남어", not HANGUL.search(cap) and "Sao chép ảnh" in cap, cap[:80])
                pg.screenshot(path=os.path.join(SHOTS, "vi_image_pc.png"))
                pg.click(".cap-close")
                with pg.expect_download() as dl:
                    pg.click("#vnMd")
                f = dl.value
                chk("📝 파일 이름 = 베트남어", f.suggested_filename.startswith("GhiChuGiongNoi_") , f.suggested_filename)
                path_md = f.path()
                md = io.open(path_md, encoding="utf-8").read()
                chk("📝 파일 머리 = Người lập · 한국어 라벨 없음", "일시:" not in md and "**작성**" not in md, md[:80])
                pg.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
                dialogs = []
                pg.click("#vnDel")
                pg.wait_for_timeout(200)
                chk("삭제 확인 창 = 베트남어", dialogs and not HANGUL.search(dialogs[0]), str(dialogs)[:90])
            chk("%s: 화면 오류 없음" % tag, not errs, str(errs[:2]))
            ctx.close()
        #  사전 빠짐 — 베트남어 화면 사전이 한국어 화면엔 안 간다
        _, h = http(PN, "/voice-notes/%d" % IN["VI1"], VI)
        chk("베트남어 화면에 사전 있음", "Tổng hợp lại" in h and "var _VND = {\"" in h)
        b.close()

    print("== ⑥ 자동 일시 ==")
    code = ("import sys;sys.path.insert(0,%r);import re,types;"
            "s=open(%r,encoding='utf-8').read();a=s.index('def vnt');g={'re':re};exec(s[s.index('def when_vi'):],g);"
            "print(g['when_vi']('2026-10-21 (수) 12:04 ~ 12:38 (34분)','vi'));print(g['when_vi']('2026-10-21 (수) 12:38 녹음','vi'));print(g['when_vi']('2026-10-21 (수) 12:38 녹음','ko'))"
            % (os.path.join(APPDIR, "app_new"), os.path.join(APPDIR, "app_new", "app", "voice_note_vi.py")))
    o = subprocess.run([P313, "-X", "utf8", "-c", code], capture_output=True, text=True, encoding="utf-8").stdout.splitlines()
    chk("일시 글 = (T4) · phút · ghi âm · 한국어는 그대로", o == ["2026-10-21 (T4) 12:04 ~ 12:38 (34 phút)", "2026-10-21 (T4) 12:38 ghi âm", "2026-10-21 (수) 12:38 녹음"], str(o))
finally:
    for app, (pr, _s) in srv.items():
        pr.terminate()
print("q200 %d/%d %s" % (OK, N, ("· 실패: " + str(FAILS)) if FAILS else ""))
print("결과: 통과 %d · 실패 %d" % (OK, N - OK))
sys.exit(1 if FAILS else 0)
