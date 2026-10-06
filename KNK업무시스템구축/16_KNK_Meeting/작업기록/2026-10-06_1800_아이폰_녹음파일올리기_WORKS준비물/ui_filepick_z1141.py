# -*- coding: utf-8 -*-
"""z1141 화면 시험 — 아이폰에서 녹음 파일을 고를 수 있게 (직원 신고 2026-10-06 박성수 프로)
  A. 올리기 입력칸 3곳: `accept` 에 서버가 받는 확장자 12가지가 들어 있다 · `display:none` 이 아니다
  B. 눈에는 안 보이고 자리도 안 차지한다(화면이 안 밀렸다)
  C. 단추를 누르면 **파일 고르기가 열린다**(눌러도 반응 없던 증상의 반대)
  D. 실제로 .m4a 를 골라 올리면 그대로 올라간다(지금 되던 것 유지)
  E. 「📱 녹음기로 바로 녹음」은 accept 를 안 건드렸다(녹음기가 열려야 하므로)
🔎 한계: 여기는 크롬이라 **아이폰 파일 고르기 자체는 재현할 수 없다** → 박성수 프로 실물 확인 필요.
사용: py -3.12 ui_filepick_z1141.py [포트=8936] [씨앗폴더]"""
import json
import os
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8936
BASE = "http://127.0.0.1:%d" % PORT
HERE = os.path.dirname(os.path.abspath(__file__))
UA_IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 "
          "(KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1")
WANT_EXTS = [".m4a", ".mp3", ".mp4", ".wav", ".webm", ".ogg", ".oga", ".aac", ".3gp", ".mpeg", ".mpga", ".caf"]

OK, NG, ERRS = [], [], []


def ok(name, cond, extra=""):
    (OK if cond else NG).append(name)
    print(("  ✅ " if cond else "  ❌ ") + name + (("  — " + str(extra)[:170]) if extra != "" else ""), flush=True)


def main():
    seed_dir = sys.argv[2] if len(sys.argv) > 2 else HERE
    seed = json.load(open(os.path.join(seed_dir, "seed_phrec.json"), encoding="utf-8"))
    mids, ceo, app_dir = seed["mids"], seed["ceo"], seed["app"]
    MID = mids[0]
    db = os.path.join(app_dir, "data", "knk.db")
    m4a = os.path.join(seed_dir, "z1141_test.m4a")
    with open(m4a, "wb") as f:                      # 아이폰 녹음과 같은 생김새(ftyp M4A)
        f.write(b"\x00\x00\x00\x20ftypM4A " + b"\0" * 4096)

    def sql(q, a=()):
        con = sqlite3.connect(db)
        cur = con.execute(q, a)
        rows = cur.fetchall()
        con.commit()
        con.close()
        return rows

    sql("UPDATE meetings SET audio_path='', rec_state='', rec_json='', body='', summary='' WHERE id=?", (MID,))

    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True)
        c = br.new_context(user_agent=UA_IOS, viewport={"width": 390, "height": 844},
                           is_mobile=True, has_touch=True, base_url=BASE)
        c.add_cookies([{"name": "tuser", "value": str(ceo), "url": BASE}])
        p = c.new_page()
        p.on("pageerror", lambda e: ERRS.append(str(e)))
        p.goto("%s/meetings/%d" % (BASE, MID), wait_until="domcontentloaded")
        p.wait_for_timeout(900)

        # ══════════ A. 고를 수 있는 파일 조건 ══════════
        print("\n■ A. 고를 수 있는 파일 조건(accept)", flush=True)
        info = p.evaluate("""()=>[...document.querySelectorAll('input[type=file]')].map(e=>({
            id:e.id, accept:e.getAttribute('accept')||'', cap:e.hasAttribute('capture'),
            disp:getComputedStyle(e).display, cls:e.className}))""")
        ups = [x for x in info if not x["cap"]]
        caps = [x for x in info if x["cap"]]
        ok("A1 올리기 입력칸이 있다", len(ups) >= 1, [x["id"] for x in ups])
        miss = [(x["id"], e) for x in ups for e in WANT_EXTS if e not in x["accept"]]
        ok("A2 올리기 칸 accept 에 서버가 받는 확장자 12가지가 모두 있다", not miss, miss[:4])
        ok("A3 accept 에 audio/* 도 그대로 있다", all("audio/*" in x["accept"] for x in ups))
        ok("A4 🔴 올리기 칸이 display:none 이 아니다(아이폰이 창을 연다)",
           all(x["disp"] != "none" for x in ups), [(x["id"], x["disp"]) for x in ups])
        ok("A5 숨김은 전용 방식(knk-file-vh)으로", all("knk-file-vh" in x["cls"] for x in ups))

        # ══════════ B. 안 보이고 자리도 안 차지 ══════════
        print("\n■ B. 눈에는 안 보이고 화면도 안 밀린다", flush=True)
        box = p.evaluate("""()=>{const e=document.querySelector('#recFileTop');
            if(!e) return null; const r=e.getBoundingClientRect();
            return {w:Math.round(r.width), h:Math.round(r.height)};}""")
        ok("B1 입력칸 크기가 1px 이하(안 보인다)", bool(box) and box["w"] <= 2 and box["h"] <= 2, box)
        big = p.evaluate("""()=>{const b=document.getElementById('recUpBtn');
            return b ? Math.round(b.getBoundingClientRect().height) : 0;}""")
        ok("B2 큰 단추 크기는 그대로(108px 안팎)", 90 <= big <= 130, "%dpx" % big)
        ok("B3 가로 스크롤이 생기지 않았다",
           p.evaluate("()=>document.documentElement.scrollWidth <= window.innerWidth + 1"),
           p.evaluate("()=>[document.documentElement.scrollWidth, window.innerWidth]"))

        # ══════════ C. 누르면 파일 고르기가 열린다 ══════════
        print("\n■ C. 단추를 누르면 파일 고르기가 열린다", flush=True)
        try:
            with p.expect_file_chooser(timeout=8000) as fc:
                p.click("#recUpBtn")
            chooser = fc.value
            ok("C1 맨 위 「📁 녹음 파일 올리기」 → 창 열림", chooser is not None)
        except Exception as e:
            ok("C1 맨 위 「📁 녹음 파일 올리기」 → 창 열림", False, str(e)[:80])
        p.evaluate("()=>{const d=document.getElementById('redoTools'); if(d) d.open=true;}")
        p.wait_for_timeout(300)
        try:
            with p.expect_file_chooser(timeout=8000) as fc2:
                p.locator("label.rec-file").first.click()
            ok("C2 「🔧 다시 하기」 안의 올리기도 창 열림", fc2.value is not None)
        except Exception as e:
            ok("C2 「🔧 다시 하기」 안의 올리기도 창 열림", False, str(e)[:80])

        # ══════════ D. 실제로 올라간다 ══════════
        print("\n■ D. 실제로 .m4a 를 골라 올리면 올라간다", flush=True)
        p.locator("#recFileTop").set_input_files(m4a)
        try:
            p.wait_for_function(
                "()=>{const t=document.getElementById('mtgBody');return t && t.value.indexOf('[가짜 변환]')>=0;}",
                timeout=30000)
            done = True
        except Exception:
            done = False
        ok("D1 올리면 음성→글자·정리까지 자동", done,
           p.evaluate("()=>document.getElementById('mtgBody').value.slice(0,30)"))
        ok("D2 서버에 파일이 남았다", (sql("SELECT COALESCE(audio_path,'') FROM meetings WHERE id=?", (MID,))[0][0] or "") != "")

        # ══════════ E. 녹음기 단추는 그대로 ══════════
        print("\n■ E. 「📱 녹음기로 바로 녹음」은 안 건드렸다", flush=True)
        ok("E1 녹음기 칸이 있다", len(caps) >= 1, [x["id"] for x in caps])
        ok("E2 그 칸 accept 는 audio/* 그대로(확장자 안 붙임 — 녹음기가 열려야 한다)",
           all(x["accept"] == "audio/*" for x in caps), [x["accept"] for x in caps])
        ok("E3 그 칸도 display:none 은 아니다", all(x["disp"] != "none" for x in caps))

        print("\n" + "=" * 70)
        ok("화면 오류 없음", not ERRS, ERRS[:2])
        print("합계: 통과 %d · 실패 %d" % (len(OK), len(NG)), flush=True)
        for n in NG:
            print("  - 실패:", n, flush=True)
        br.close()
    try:
        os.remove(m4a)
    except Exception:
        pass
    return 1 if NG else 0


if __name__ == "__main__":
    sys.exit(main())
