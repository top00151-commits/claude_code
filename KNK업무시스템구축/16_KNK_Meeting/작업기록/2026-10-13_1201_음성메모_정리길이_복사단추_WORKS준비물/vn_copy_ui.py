# -*- coding: utf-8 -*-
"""z1168 검사기 ② — 🎤 음성 메모 **📋 복사 단추**를 진짜 브라우저로 눌러 본다.

대표 지시 2026-10-13 「삭제 아이콘 왼쪽에 복사 아이콘이 있으면 좋겠어..
                      내용을 바로 정리한 형식대로 복사해서 다른데 쉽게 전달할수있게」
대표 확정: 복사되는 것 = **제목 + 날짜 + 정리 글**

재는 것 (앱 두 벌 · 운영 그대로 8983 · 내 변경 8984)
  ① 🔴 **반대 시험** — 운영 화면엔 복사 단추가 **없다**(있으면 검사기가 헛것을 보는 것)
  ② 내 화면엔 **있고**, **삭제 단추 왼쪽**에 있다 (x 좌표로 잰다 · 눈으로 말고)
  ③ 정리가 있는 메모 → 단추가 **눌린다**
  ④ 🔵 **진짜로 눌러서** 클립보드를 읽어 **제목 (날짜) + 빈 줄 + 정리 글**인지 글자로 맞춘다
  ⑤ 정리가 **없는** 메모 → 단추가 **흐리고 안 눌린다**(z1166 과 같은 방식)
  ⑥ 정리 글을 **고치면** 복사되는 내용도 **따라 바뀐다**
  ⑦ 🔵 그 밖의 화면 글은 운영과 **글자 그대로 같다**(내가 넣은 것만 빼고)
  ⑧ 500 없음

쓰는 법: py vn_copy_ui.py <포트_base> <포트_new> [app_base·app_new 가 있는 폴더]
판정: **종료코드**(0=통과).
"""
import difflib
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
PB = int(sys.argv[1]) if len(sys.argv) > 1 else 8983
PN = int(sys.argv[2]) if len(sys.argv) > 2 else 8984
APPDIR = sys.argv[3] if len(sys.argv) > 3 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
#  서버는 z1167 때 만든 것을 그대로 쓴다(메모 둘 — 정리 끝난 것 · 정리 전 것)
RUN = os.path.join(os.path.dirname(HERE),
                   "2026-10-13_1035_음성메모_시안문서_지움_WORKS준비물", "run_vn2_app.py")
OK = FAIL = 0


def chk(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (name, detail))


_VOL = [(re.compile(r"\?v=t[0-9]{6,}"), "?v=X"),
        (re.compile(r'"t[0-9]{9,}"'), '"tX"'),
        (re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}(:[0-9]{2})?"), "DATETIME")]


def nocache(s):
    s = s.replace("\r\n", "\n")
    for r, sub in _VOL:
        s = r.sub(sub, s)
    return s


def boot(app, port):
    lp = os.path.join(APPDIR, "srv_%d.log" % port)
    log = io.open(lp, "w", encoding="utf-8")
    pr = subprocess.Popen([P313, RUN, os.path.join(APPDIR, app), str(port)],
                          stdout=log, stderr=subprocess.STDOUT, cwd=APPDIR)
    for _ in range(600):
        time.sleep(0.2)
        try:
            s = io.open(lp, encoding="utf-8").read()
        except Exception:
            s = ""
        if "READY" in s:
            m = re.search(r"READY \d+ me (\d+) done (\d+) todo (\d+)", s)
            return pr, {"me": int(m.group(1)), "done": int(m.group(2)), "todo": int(m.group(3))}
        if pr.poll() is not None:
            print(s[-2500:])
            raise SystemExit("!! %s(%d) 가 떴다 죽었다" % (app, port))
    raise SystemExit("!! %s(%d) 가 안 떴다" % (app, port))


def get(port, path, uid):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path))
    req.add_header("Cookie", "tuser=%d" % uid)
    r = urllib.request.urlopen(req, timeout=60)
    return r.getcode(), nocache(r.read().decode("utf-8", "replace"))


print("두 벌 띄우는 중…")
pb, ib = boot("app_base", PB)
pn, inn = boot("app_new", PN)
print("  운영그대로 %d · 내변경 %d (정리끝 %d · 정리전 %d)" % (PB, PN, inn["done"], inn["todo"]))

#  서버가 심어 둔 값 — 기대하는 복사 내용을 **시험이 지어내지 않고** 여기서 가져온다
SEED = json.load(io.open(os.path.join(os.path.dirname(RUN), "seed_%d.json" % PN),
                         encoding="utf-8"))

#  🔵 화면에 새로 나타난 줄이 **내가 파일에 새로 넣은 줄**인지 보려고, 파일 차이를 먼저 읽어 둔다.
#     (허용 목록을 손으로 적으면 내 줄도 「낯선 줄」로 잡히고, 아무 줄이나 봐주게 되기도 한다)
def _tpl(tree):
    return io.open(os.path.join(APPDIR, tree, "app", "templates", "voice_note_form.html"),
                   encoding="utf-8").read().replace("\r\n", "\n").splitlines()


#  🔴 집합 차이(set-set)로 뽑으면 **원래도 있던 줄**(닫는 괄호 `}` 같은 것)이 빠진다.
#     그러면 내가 넣은 닫는 괄호가 「낯선 줄」로 잡힌다 → **진짜 차이(diff)** 로 뽑는다.
_FILE_ADDED = {ln[1:].strip() for ln in
               difflib.unified_diff(_tpl("app_base"), _tpl("app_new"), n=0, lineterm="")
               if ln.startswith("+") and not ln.startswith("+++") and ln[1:].strip()}
print("  화면틀 파일에서 늘어난 줄 %d개" % len(_FILE_ADDED))
assert _FILE_ADDED, "파일에 늘어난 줄이 없다 — 사본이 잘못 깔렸다"
assert "}" in _FILE_ADDED or "});" in _FILE_ADDED, "닫는 괄호가 안 잡혔다 — diff 가 헛돌았다"

try:
    # ── ⓪ 먼저: 화면 글이 운영과 같은가 ─────────────────────────
    #    🔴 **아무것도 누르기 전에** 잰다 — 뒤에서 정리 글을 고치면 그 뒤 비교는 거짓이 된다.
    print("\n── ⓪ 🔵 화면 글은 운영과 글자 그대로 같다 (손대기 전에 잰다) ──")
    for label, nid_b, nid_n in [("정리 끝난 메모", ib["done"], inn["done"]),
                                ("정리 전 메모", ib["todo"], inn["todo"])]:
        cbz, a = get(PB, "/voice-notes/%d" % nid_b, ib["me"])
        cnz, b = get(PN, "/voice-notes/%d" % nid_n, inn["me"])
        chk("%s · 운영 200" % label, cbz == 200, cbz)
        chk("%s · 내변경 200" % label, cnz == 200, cnz)
        #  🔵 복사 단추 **덩어리를 통째로 들어내고** 견준다.
        #     (그 줄들은 {% if %} 가 들어 있어 파일 줄과 화면 줄이 생김새가 다르다.
        #      단추 자체는 브라우저 검사 ②~⑥ 이 훨씬 세게 지킨다.)
        b2, cut = re.subn(r'[ \t]*<button[^>]*id="vnCopy"[\s\S]*?</button>\n?', "", b)
        chk("%s · 🔴 복사 단추 덩어리를 찾아 들어냈다(반대 시험)" % label, cut == 1, "찾은 수 %d" % cut)
        came, gone = [], []
        for ln in difflib.unified_diff(a.splitlines(), b2.splitlines(), n=0, lineterm=""):
            if ln[:3] in ("---", "+++") or ln.startswith("@@"):
                continue
            (came if ln.startswith("+") else gone).append(ln[1:])
        #  남은 들어온 줄은 전부 **내가 파일에 넣은 줄과 글자 그대로 같아야** 한다
        odd = [x for x in came if x.strip() and x.strip() not in _FILE_ADDED]
        chk("%s · 들어온 줄이 **모두 내가 파일에 넣은 줄**" % label, not odd,
            "낯선 줄 %d개: %s" % (len(odd), odd[:3]))
        chk("%s · 🔵 **사라진 줄 0**" % label, not gone, "사라짐: %s" % gone[:3])
        chk("%s · 들어온 줄이 있다(검사가 헛돌지 않는다)" % label, len(came) > 0)

    with sync_playwright() as p:
        br = p.chromium.launch()
        ctx = br.new_context(viewport={"width": 1280, "height": 900})
        ctx.grant_permissions(["clipboard-read", "clipboard-write"],
                              origin="http://127.0.0.1:%d" % PN)

        def page_for(port, uid):
            c = br.new_context(viewport={"width": 1280, "height": 900})
            c.grant_permissions(["clipboard-read", "clipboard-write"],
                                origin="http://127.0.0.1:%d" % port)
            c.add_cookies([{"name": "tuser", "value": str(uid),
                            "url": "http://127.0.0.1:%d" % port}])
            pg = c.new_page()
            pg.add_init_script("try{localStorage.setItem('knk_works_install_hint_never','1');}catch(e){}")
            return c, pg

        # ── ① 🔴 반대 시험 — 운영 화면엔 복사 단추가 없다 ──────────
        print("\n── ① 🔴 반대 시험: 운영 그대로엔 복사 단추가 **없다** ──")
        cb, gb = page_for(PB, ib["me"])
        gb.goto("http://127.0.0.1:%d/voice-notes/%d" % (PB, ib["done"]),
                wait_until="domcontentloaded")
        gb.wait_for_selector("#vnDel", timeout=15000)
        chk("운영 화면: 📋 복사 단추 0개", gb.locator("#vnCopy").count() == 0)
        chk("운영 화면: 🗑 삭제 단추는 있다", gb.locator("#vnDel").count() == 1)

        # ── ②③ 내 화면 — 있고, 삭제 왼쪽이고, 눌린다 ───────────────
        print("\n── ②③ 내 화면: 삭제 **왼쪽**에 있고 눌린다 ──")
        cn, gn = page_for(PN, inn["me"])
        gn.goto("http://127.0.0.1:%d/voice-notes/%d" % (PN, inn["done"]),
                wait_until="domcontentloaded")
        gn.wait_for_selector("#vnCopy", timeout=15000)
        chk("📋 복사 단추가 있다", gn.locator("#vnCopy").count() == 1)
        bc = gn.locator("#vnCopy").bounding_box()
        bd = gn.locator("#vnDel").bounding_box()
        chk("🔵 **삭제 단추 왼쪽**에 있다 (복사 x=%.0f < 삭제 x=%.0f)" % (bc["x"], bd["x"]),
            bc["x"] < bd["x"])
        chk("같은 줄에 있다(위아래로 안 밀렸다)", abs(bc["y"] - bd["y"]) < 6,
            "복사 y=%.0f 삭제 y=%.0f" % (bc["y"], bd["y"]))
        chk("정리가 있으니 **안 흐리다**(눌린다)", gn.locator("#vnCopy").is_enabled())

        # ── ④ 🔵 진짜로 눌러서 클립보드를 읽는다 ────────────────────
        print("\n── ④ 🔵 눌러서 클립보드를 **글자로** 맞춘다 ──")
        gn.click("#vnCopy")
        gn.wait_for_timeout(500)
        got = gn.evaluate("async () => { try { return await navigator.clipboard.readText(); }"
                          " catch(e) { return 'ERR:' + e.message; } }")
        #  🔵 Windows 클립보드는 줄바꿈을 \r\n 으로 바꿔 준다(붙여넣을 때 오히려 맞다) → 맞춰서 본다
        raw = str(got)
        had_crlf = "\r\n" in raw
        got = raw.replace("\r\n", "\n")
        title = gn.input_value("#vnTitle")
        body = gn.inner_text("#vnSumBox").strip()
        when = gn.get_attribute("#vnCopy", "data-when") or ""
        want = (title + ((" (" + when + ")") if when else "")) + "\n\n" + body
        chk("클립보드에 들어갔다(오류 아님)", not str(got).startswith("ERR:"), str(got)[:80])
        chk("ℹ 줄바꿈은 Windows 식(\\r\\n)으로 담긴다 — 붙여넣을 때 맞다", had_crlf)
        chk("🔵 **제목 (날짜) + 빈 줄 + 정리 글** 그대로", got == want,
            "\n       받음: %r\n       기대: %r" % (str(got)[:160], want[:160]))
        chk("제목이 들어 있다 (%s)" % title, title and title in str(got))
        chk("날짜가 들어 있다 (%s)" % when, when and when in str(got))
        chk("정리 글이 **줄바꿈까지 그대로** 들어 있다", body and body in str(got))
        chk("정리 글 줄 수가 같다",
            len([l for l in str(got).split("\n\n", 1)[-1].splitlines() if l.strip()])
            == len([l for l in body.splitlines() if l.strip()]))
        chk("단추 글자가 잠깐 「✓ 복사됨」으로 바뀐다",
            "복사됨" in (gn.inner_text("#vnCopy") or ""), gn.inner_text("#vnCopy"))
        chk("안내가 뜬다", "복사" in (gn.inner_text("#vnSt") or ""), gn.inner_text("#vnSt"))

        # ── ⑤ 정리가 없는 메모 — 흐리고 안 눌린다 ──────────────────
        print("\n── ⑤ 정리가 **없는** 메모: 흐리고 안 눌린다 ──")
        gn.goto("http://127.0.0.1:%d/voice-notes/%d" % (PN, inn["todo"]),
                wait_until="domcontentloaded")
        gn.wait_for_selector("#vnCopy", timeout=15000)
        chk("단추는 보인다(사라지지 않는다)", gn.locator("#vnCopy").is_visible())
        chk("🔵 **흐리다**(안 눌린다)", not gn.locator("#vnCopy").is_enabled())
        chk("까닭이 적혀 있다", "정리 전" in (gn.get_attribute("#vnCopy", "title") or ""),
            gn.get_attribute("#vnCopy", "title"))

        # ── ⑥ 정리 글을 고치면 복사 내용도 따라 바뀐다 ──────────────
        print("\n── ⑥ 정리 글을 고치면 복사 내용도 따라 바뀐다 ──")
        gn.click("#vnSumEdit")
        gn.fill("#vnSumEdit2", "요점\n- 고쳐 쓴 줄 하나\n- 고쳐 쓴 줄 둘")
        gn.click("#vnSumSave")
        gn.wait_for_timeout(900)
        chk("고치고 나면 단추가 **켜진다**", gn.locator("#vnCopy").is_enabled())
        gn.click("#vnCopy")
        gn.wait_for_timeout(500)
        got2 = gn.evaluate("async () => { try { return await navigator.clipboard.readText(); }"
                           " catch(e) { return 'ERR:' + e.message; } }")
        chk("고친 글이 복사된다", "고쳐 쓴 줄 둘" in str(got2), str(got2)[:120])
        chk("옛 글은 안 따라온다", "3호기" not in str(got2))

        cb.close()
        cn.close()
        br.close()
finally:
    for pr in (pb, pn):
        try:
            pr.terminate()
        except Exception:
            pass

print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
