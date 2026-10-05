# -*- coding: utf-8 -*-
"""z1138 화면 시험 — 「📁 녹음 파일 올리기」가 회의록 맨 위에 **스크롤 없이** 보인다 (대표 지시 2026-10-05)
  A. 녹음 없는 회의(폰) — 큰 단추가 첫 화면 안에 보임 · 「🔧 다시 하기」를 펼치지 않아도 · 이름은 하나
  B. 그 단추로 실제로 올라간다 — 올린 뒤 큰 칸은 사라지고 알림 글은 맨 위에도 보인다
  C. 이미 녹음이 있는 회의 → 큰 칸 없음(대표 결정: 녹음이 없을 때만)
  D. 녹음 중이던 회의 → 큰 칸 없음(그 자리는 「🔴 녹음 중이던 회의」 상자)
  E. PC 폭에서도 위쪽에 보인다
  F. 「🔧 다시 하기」 안의 올리기 단추도 그대로(두 길 다 된다)
사용: py -3.12 ui_recup_z1138.py [포트=8936] [씨앗폴더]
🔴 씨앗(seed_phrec.json)은 **서버를 띄운 쪽**이 쓴 것을 본다(둘째 인자) — 다른 사본 DB 를 건드리지 않게."""
import json
import os
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8936
BASE = "http://127.0.0.1:%d" % PORT
HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Linux; Android 14; SM-S928N) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/153.0.0.0 Mobile Safari/537.36")

OK, NG, ERRS = [], [], []


def ok(name, cond, extra=""):
    (OK if cond else NG).append(name)
    print(("  ✅ " if cond else "  ❌ ") + name + (("  — " + str(extra)[:170]) if extra != "" else ""), flush=True)


def main():
    seed_dir = sys.argv[2] if len(sys.argv) > 2 else HERE
    seed = json.load(open(os.path.join(seed_dir, "seed_phrec.json"), encoding="utf-8"))
    mids, ceo, app_dir = seed["mids"], seed["ceo"], seed["app"]
    M_EMPTY, M_HAS, M_REC = mids[0], mids[1], mids[2]
    db_path = os.path.join(app_dir, "data", "knk.db")
    wav = os.path.join(seed_dir, "z1138_test.wav")
    with open(wav, "wb") as f:
        f.write(b"RIFF" + (b"\0" * 4096))

    def sql(q, args=()):
        con = sqlite3.connect(db_path)
        cur = con.execute(q, args)
        rows = cur.fetchall()
        con.commit()
        con.close()
        return rows

    # 녹음 없는 회의 / 이미 녹음이 있는 회의 / 녹음 중이던 회의 — 셋을 만들어 둔다
    sql("UPDATE meetings SET audio_path='', rec_state='', body='', summary='' WHERE id=?", (M_EMPTY,))
    sql("UPDATE meetings SET audio_path='meeting_audio/x.m4a', rec_state='' WHERE id=?", (M_HAS,))
    sql("UPDATE meetings SET audio_path='', rec_state='recording', "
        "rec_json='{\"secs\": 95, \"bytes\": 20480, \"by_name\": \"김정락\"}' WHERE id=?", (M_REC,))

    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True, args=[
            "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])

        def open_mtg(mid, phone=True):
            vp = {"width": 390, "height": 844} if phone else {"width": 1280, "height": 900}
            c = br.new_context(user_agent=(UA if phone else None), viewport=vp,
                               is_mobile=phone, has_touch=phone, permissions=["microphone"], base_url=BASE)
            c.add_cookies([{"name": "tuser", "value": str(ceo), "url": BASE}])
            p = c.new_page()
            p.on("pageerror", lambda e: ERRS.append(str(e)))
            p.goto("%s/meetings/%d" % (BASE, mid), wait_until="domcontentloaded")
            p.wait_for_timeout(800)
            return c, p

        def in_first_screen(p, sel):
            """스크롤하지 않은 첫 화면 안에 들어와 있나 — 이게 「바로 보인다」의 뜻"""
            return p.evaluate("""(s)=>{const e=document.querySelector(s); if(!e) return null;
                const r=e.getBoundingClientRect();
                return {top:Math.round(r.top), bottom:Math.round(r.bottom), h:Math.round(r.height),
                        vh:window.innerHeight, scroll:Math.round(window.scrollY),
                        inside:(r.top>=0 && r.top < window.innerHeight)};}""", sel)

        # ══════════ A. 녹음 없는 회의 (휴대폰) ══════════
        print("\n■ A. 녹음이 없는 회의 — 휴대폰 (390×844)", flush=True)
        c, p = open_mtg(M_EMPTY)
        ok("A1 「📁 녹음 파일 올리기」 칸이 보인다", p.locator("#recUpTop").is_visible())
        box = in_first_screen(p, "#recUpTop")
        ok("A2 🔴 스크롤하지 않은 첫 화면 안에 있다", bool(box and box["inside"]) and box["scroll"] == 0, box)
        ok("A3 「🔧 다시 하기」를 펼치지 않아도 보인다",
           p.evaluate("()=>{const d=document.getElementById('redoTools');return !!d && !d.open;}"))
        lbl = p.locator("#recUpBtn").inner_text()
        ok("A4 단추 글 = 「📁 녹음 파일 올리기」", "📁 녹음 파일 올리기" in lbl, lbl.replace("\n", " ")[:60])
        hh = p.evaluate("()=>Math.round(document.getElementById('recUpBtn').getBoundingClientRect().height)")
        ok("A5 누르기 쉬운 크기(44px 이상)", hh >= 44, "%dpx" % hh)
        ok("A6 안내에 「홈 화면 「음성 녹음」」이 있다", "음성 녹음" in p.locator("#recUpTop").inner_text())
        body_txt = p.evaluate("()=>document.body.innerText")
        ok("A7 이름이 하나 — 「음성 파일 올리기」 표기 없음", "음성 파일 올리기" not in body_txt)
        pos = p.evaluate("""()=>{const g=s=>{const e=document.querySelector(s);
            return e?Math.round(e.getBoundingClientRect().top):null;};
            return {up:g('#recUpTop'), top:g('.mf-top'), redo:g('#redoTools')};}""")
        ok("A8 기본정보·다시하기보다 위에 있다", pos["up"] < pos["top"] and pos["up"] < pos["redo"], pos)
        ok("A9 파일 고르기 입력이 붙어 있다", p.locator("#recFileTop").count() == 1)

        # ══════════ B. 그 단추로 실제로 올라간다 ══════════
        print("\n■ B. 맨 위 단추로 올리기 (가짜 변환·정리까지)", flush=True)
        p.locator("#recFileTop").set_input_files(wav)
        try:
            p.wait_for_function(
                "()=>{const t=document.getElementById('mtgBody');return t && t.value.indexOf('[가짜 변환]')>=0;}",
                timeout=30000)
            up = True
        except Exception:
            up = False
        ok("B1 올리면 음성→글자·정리까지 자동으로 된다", up,
           p.evaluate("()=>document.getElementById('mtgBody').value.slice(0,40)"))
        ok("B2 올린 뒤 큰 칸은 사라진다(녹음이 생겼으니)", not p.locator("#recUpTop").is_visible())
        saved = sql("SELECT COALESCE(audio_path,'') FROM meetings WHERE id=?", (M_EMPTY,))[0][0]
        ok("B3 서버에 녹음 파일이 남았다", saved != "", saved[-28:])
        c.close()

        # ══════════ C. 이미 녹음이 있는 회의 ══════════
        print("\n■ C. 이미 녹음이 있는 회의 — 큰 칸 없음(대표 결정)", flush=True)
        c, p = open_mtg(M_HAS)
        ok("C1 큰 올리기 칸이 그려지지 않는다", p.locator("#recUpTop").count() == 0)
        p.evaluate("()=>{const d=document.getElementById('redoTools');if(d)d.open=true;}")
        p.wait_for_timeout(300)
        ok("C2 「🔧 다시 하기」 안에서는 그대로 올릴 수 있다", p.locator("label.rec-file").first.is_visible())
        c.close()

        # ══════════ D. 녹음 중이던 회의 ══════════
        print("\n■ D. 녹음 중이던 회의 — 그 자리는 「🔴 녹음 중이던 회의」", flush=True)
        c, p = open_mtg(M_REC)
        ok("D1 큰 올리기 칸이 그려지지 않는다", p.locator("#recUpTop").count() == 0)
        ok("D2 「🔴 녹음 중이던 회의」 상자가 보인다", p.locator("#recResume").is_visible())
        c.close()

        # ══════════ E. PC 폭 ══════════
        print("\n■ E. PC 폭 (1280×900)", flush=True)
        sql("UPDATE meetings SET audio_path='', rec_state='', body='', summary='' WHERE id=?", (mids[3],))
        c, p = open_mtg(mids[3], phone=False)
        ok("E1 큰 올리기 칸이 보인다", p.locator("#recUpTop").is_visible())
        box = in_first_screen(p, "#recUpTop")
        ok("E2 스크롤하지 않은 첫 화면 안에 있다", bool(box and box["inside"]) and box["scroll"] == 0, box)
        ok("E3 기본정보보다 위에 있다",
           p.evaluate("""()=>{const a=document.getElementById('recUpTop').getBoundingClientRect().top,
             b=document.querySelector('.mf-top').getBoundingClientRect().top; return a<b;}"""))

        # ══════════ F. 알림 글이 맨 위에도 보인다 ══════════
        print("\n■ F. 알림 글이 맨 위 칸에도 보인다", flush=True)
        bad = os.path.join(seed_dir, "z1138_bad.txt")
        with open(bad, "wb") as _f:
            _f.write(b"not audio")
        p.locator("#recFileTop").set_input_files(bad)
        try:
            p.wait_for_function("()=>{const t=document.getElementById('recUpSt');"
                                "return t && t.textContent.trim().length>0 "
                                "&& t.textContent.indexOf('저장 중')<0;}", timeout=20000)
        except Exception:
            pass
        st = p.locator("#recUpSt").inner_text()
        ok("F1 소리 파일이 아니면 까닭이 맨 위 칸에 보인다", st.strip() != "", st[:70])
        ok("F2 그때 큰 칸은 그대로 남아 다시 고를 수 있다", p.locator("#recUpTop").is_visible())
        c.close()

        # ══════════ G. 정리가 끝난 회의록(녹음 없음) — 결과를 가리지 않는다 ══════════
        print("\n■ G. 정리가 이미 있는 회의록(녹음 없음) — 큰 칸 없음(결과 먼저)", flush=True)
        sql("UPDATE meetings SET audio_path='', rec_state='', rec_json='', summary=? WHERE id=?",
            ("핵심: 손으로 적은 회의록", M_REC))
        c, p = open_mtg(M_REC)
        ok("G1 정리가 있으면 큰 칸을 띄우지 않는다", p.locator("#recUpTop").count() == 0)
        fst = p.evaluate("""()=>{const w=document.querySelector('.mf-wrap');
            const k=[...w.children].filter(x=>getComputedStyle(x).display!=='none'&&x.offsetHeight>0);
            k.sort((a,b)=>a.getBoundingClientRect().top-b.getBoundingClientRect().top);
            return k[0]?(k[0].id||k[0].className):'';}""")
        ok("G2 첫 칸은 회의록 정리 그대로(결과 먼저)", fst == "secSummary", fst)
        p.evaluate("()=>{const d=document.getElementById('redoTools');if(d)d.open=true;}")
        p.wait_for_timeout(300)
        ok("G3 「🔧 다시 하기」로는 그때도 올릴 수 있다", p.locator("label.rec-file").first.is_visible())
        c.close()

        print("\n" + "=" * 70)
        ok("화면 오류 없음", not ERRS, ERRS[:2])
        print("합계: 통과 %d · 실패 %d" % (len(OK), len(NG)), flush=True)
        for n in NG:
            print("  - 실패:", n, flush=True)
        br.close()
    return 1 if NG else 0


if __name__ == "__main__":
    sys.exit(main())
