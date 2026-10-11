# -*- coding: utf-8 -*-
"""z1165 — 「회의에서 쓰는 말」이 **정말 서버까지 가나**를 브라우저로 잰다.

  ① 🔴 큰 올리기 자리의 칸이 **눈에 보인다** — 처음엔 접힌 칸 안에 넣어 **안 보였다**
     (2026-10-05 대표 신고 「접힌 칸 안에만 있어 찾기 어렵다」와 같은 실수)
  ② 기본은 「자동」(빈 값) = z1165 이전과 같은 동작
  ③ 🔵 **진짜 올리는 길**로 고른 값이 받아쓰기 요청에 실려 간다 ← 이 기능의 핵심 증명
  ④ 🔴 「새 회의록」에서 고른 말이 화면이 바뀐 뒤에도 살아 있다(`?sttlang=`)
  ⑤ ⛔ 주소로 들어온 엉뚱한 값은 안 받는다
  ⑥ 베트남어 쓰는 분 화면에서도 같다 · 화면 오류 0

사용: py -3.12 stt_pick_z1165.py <포트> <씨앗폴더>
"""
import json
import os
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8972
SEED = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(__file__))
BASE = "http://127.0.0.1:%d" % PORT

OK = FAIL = 0


def ok(name, cond, extra=""):
    global OK, FAIL
    if cond:
        OK += 1
    else:
        FAIL += 1
    print(("  ✅ " if cond else "  ❌ ") + name + (("  — " + str(extra)[:160]) if extra != "" else ""),
          flush=True)


seed = json.load(open(os.path.join(SEED, "seed_%d.json" % PORT), encoding="utf-8"))
MID, KO, VI, APP = seed["mid"], seed["ko"], seed["vi"], seed["app"]
DB = os.path.join(APP, "data", "knk.db")
M4A = os.path.join(SEED, "z1165_test.m4a")
with open(M4A, "wb") as f:                     # 폰 녹음과 같은 생김새(ftyp M4A)
    f.write(b"\x00\x00\x00\x20ftypM4A " + b"\0" * 4096)


def reset_meeting():
    """큰 올리기 자리가 다시 보이게 — 녹음·정리를 비운다(시험 DB 만)."""
    con = sqlite3.connect(DB)
    con.execute("UPDATE meetings SET audio_path='', rec_state='', rec_json='', "
                "body='', summary='' WHERE id=?", (MID,))
    con.commit()
    con.close()


def goto_ready(page, url, visible=True):
    """화면으로 가서 **그 칸이 자리를 잡을 때까지** 기다린다.

    🔴 `goto(wait_until="load")` 만으로는 모자랐다 — 묶음으로 돌 때 기계가 바빠
       덜 그려진 사이에 `count()`·`input_value()` 를 읽으면 거짓경보가 난다(실제로 겪음).
       `count()`·`input_value()` 는 **기다려 주지 않는다**.
    """
    page.goto(url, wait_until="load")
    page.locator("#sttLang").wait_for(state="visible" if visible else "attached", timeout=20000)


def main():
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True)

        def page_for(uid):
            c = br.new_context(base_url=BASE)
            # 설치 안내 팝업은 재는 대상이 아니다(누르기를 가로막는다)
            c.add_init_script("try{localStorage.setItem('knk_works_install_hint_never','1')}catch(e){}")
            c.add_cookies([{"name": "tuser", "value": str(uid), "url": BASE}])
            return c, c.new_page()

        c, p = page_for(KO)

        print("\n■ ① 🔴 큰 올리기 자리의 칸이 눈에 보인다")
        reset_meeting()
        goto_ready(p, "%s/meetings/%d" % (BASE, MID))
        # 🔴 `count()` 는 기다려 주지 않는다 — 묶음으로 돌 때 기계가 바빠 덜 그려진 사이에 읽으면
        #    「2인데 2가 아니다」 같은 거짓경보가 난다(실제로 겪음). **보일 때까지 기다린 뒤 한 번만** 읽는다.
        p.locator("#sttLang").wait_for(state="visible", timeout=20000)
        n_pick = p.locator("select.sttLangPick").count()
        ok("칸이 두 자리에 있다(큰 올리기 · 다시 하기)", n_pick == 2, n_pick)
        ok("🔴 큰 올리기 자리의 칸이 **보인다**", p.locator("#sttLang").is_visible())
        n_redo = p.locator("#sttLangRedo").count()
        ok("다시 하기 쪽 칸은 접혀 있다(있지만 안 보임)",
           n_redo == 1 and not p.locator("#sttLangRedo").is_visible(), n_redo)
        ok("큰 올리기 단추보다 아래에 있다(누르기를 안 가린다)",
           p.locator("#recUpBtn").bounding_box()["y"] < p.locator("#sttLang").bounding_box()["y"])

        print("\n■ ② 기본은 「자동」(빈 값)")
        ok("기본값이 빈 값", p.input_value("#sttLang") == "", p.input_value("#sttLang"))

        print("\n■ ③ 🔵 진짜 올리는 길로 — 고른 값이 요청에 실려 간다 (핵심 증명)")
        for want in ("ko", "vi", ""):
            reset_meeting()
            c2, p2 = page_for(KO)
            got = {}

            def grab(route):
                try:
                    got["body"] = route.request.post_data
                except Exception:
                    got["body"] = None
                route.fulfill(status=200, content_type="application/json",
                              body='{"ok":false,"error":"시험: 여기서 멈춘다"}')

            p2.route("**/api/meeting/*/transcribe", grab)
            goto_ready(p2, "%s/meetings/%d" % (BASE, MID))
            if want:
                p2.select_option("#sttLang", want)
            p2.locator("#recFileTop").set_input_files(M4A)
            for _ in range(60):
                p2.wait_for_timeout(500)
                if "body" in got:
                    break
            body = got.get("body")
            sent = "요청이 안 왔다"
            if body is not None:
                try:
                    sent = json.loads(body).get("lang")
                except Exception:
                    sent = "읽기 실패: " + str(body)[:60]
            ok("고른 값 %-4s → 요청에 lang=%r" % (want or "자동", sent), sent == want, body)
            c2.close()

        print("\n■ ④ 🔴 「새 회의록」에서 고른 말이 화면이 바뀐 뒤에도 살아 있다")
        reset_meeting()
        for v in ("ko", "vi"):
            goto_ready(p, "%s/meetings/%d?auto=1&sttlang=%s" % (BASE, MID, v))
            ok("주소로 %s 를 넘기면 두 칸 다 그 값이다" % v,
               p.input_value("#sttLang") == v and p.input_value("#sttLangRedo") == v,
               [p.input_value("#sttLang"), p.input_value("#sttLangRedo")])
        ok("보내는 쪽 — 새 회의 이동 줄이 그 값을 싣는다",
           "&sttlang='+encodeURIComponent(_sl)" in p.content())

        print("\n■ ⑤ ⛔ 주소로 들어온 엉뚱한 값은 안 받는다")
        for bad in ("en", "zh", "xx", "1"):
            goto_ready(p, "%s/meetings/%d?sttlang=%s" % (BASE, MID, bad))
            v = p.input_value("#sttLang")
            ok("%-4s → 자동으로 떨어진다" % bad, v == "", v)

        print("\n■ ⑥ 베트남어 쓰는 분 화면 · 화면 오류 0")
        c3, p3 = page_for(VI)
        errs = []
        p3.on("pageerror", lambda e: errs.append(str(e)))
        goto_ready(p3, "%s/meetings/%d?auto=1&sttlang=vi" % (BASE, MID))
        p3.wait_for_timeout(1500)
        ok("베트남어 화면도 그 값으로 골라져 있다", p3.input_value("#sttLang") == "vi",
           p3.input_value("#sttLang"))
        ok("보기 이름이 베트남어다", "Tiếng Hàn" in p3.content())
        ok("자바스크립트 오류 없음", not errs, errs[:2])

        br.close()

    print("\n합계 %d검사 · 실패 %d" % (OK + FAIL, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
