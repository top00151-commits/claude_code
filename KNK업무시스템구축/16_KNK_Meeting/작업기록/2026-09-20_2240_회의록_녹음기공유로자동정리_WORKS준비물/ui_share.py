# -*- coding: utf-8 -*-
"""z1117 화면 시험 — 「공유 → WORKS」로 들어온 녹음 받기 화면

실제 크롬으로, 크롬이 공유 대상에 보내는 것과 같은 모양(POST multipart/form-data)을 보낸다.
  · 넘기던 회의 표시가 있으면 묻지 않고 붙이고 그 회의록으로 간다
  · 표시가 없으면 골라서 붙인다(새 회의록 / 최근 회의)
사용: py -3.12 ui_share.py [포트=8936]
"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8936
BASE = "http://localhost:%d" % PORT
UA_AND = ("Mozilla/5.0 (Linux; Android 14; SM-S928N) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/153.0.0.0 Mobile Safari/537.36")
HIDE = ("document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style');"
        "s.textContent = '#worksInstallHint{display:none !important}'; document.head.appendChild(s); });")

# 크롬이 공유 대상에 보내는 것과 같은 모양: enctype=multipart/form-data 로 POST 이동
SHARE_JS = """(name) => {
  const f = new File([new Uint8Array(4000)], name, {type: 'audio/mp4'});
  const dt = new DataTransfer(); dt.items.add(f);
  const form = document.createElement('form');
  form.method = 'POST'; form.action = '/share/audio'; form.enctype = 'multipart/form-data';
  const i = document.createElement('input'); i.type = 'file'; i.name = 'audio'; i.files = dt.files;
  form.appendChild(i); document.body.appendChild(form); form.submit();
}"""

OK, NG = [], []


def ok(name, cond, extra=""):
    (OK if cond else NG).append(name)
    print(("PASS " if cond else "FAIL ") + name + ((" · " + str(extra)[:180]) if extra != "" else ""), flush=True)


def main():
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True)
        c = br.new_context(service_workers="block", user_agent=UA_AND,
                           viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        c.add_init_script(HIDE)
        p = c.new_page()
        NAV = []
        p.on('framenavigated', lambda fr: NAV.append(fr.url) if fr == p.main_frame else None)

        # 붙일 회의 번호를 하나 얻는다
        p.goto(BASE + "/meetings", wait_until="domcontentloaded")
        mid = p.evaluate("""() => { const a=document.querySelector('a.mtg-card[href^="/meetings/"]');
                                    return a ? parseInt(a.getAttribute('href').split('/').pop(),10) : 0; }""")
        ok("붙일 회의를 찾았다", bool(mid), mid)

        # ── ① 넘기던 회의 표시가 있으면 묻지 않고 붙인다 ──
        print("\n■ ① 표시가 있으면 묻지 않고 그 회의록으로", flush=True)
        p.evaluate("""(id) => localStorage.setItem('knk_mtg_phonerec',
            JSON.stringify({id:id, title:'주간 영업회의', at:Date.now()-10*60*1000}))""", mid)
        p.evaluate(SHARE_JS, "회의녹음 001.m4a")
        p.wait_for_url("**/meetings/%d**" % mid, timeout=20000)
        ok("바로 그 회의록으로 옮겨진다", p.url.split("?")[0].endswith("/meetings/%d" % mid), p.url)
        ok("자동 정리로 들어갔다(?auto=1 · 화면이 곧 지운다)",
           any(u.split("?")[0].endswith("/meetings/%d" % mid) and "auto=1" in u for u in NAV), NAV[-2:])
        ok("표시가 지워졌다", p.evaluate("() => localStorage.getItem('knk_mtg_phonerec')") is None)
        for _ in range(60):
            b = p.evaluate("() => (document.getElementById('mtgBody')||{}).value || ''")
            if "가짜 변환" in b or "내용>" in b:
                break
            p.wait_for_timeout(500)
        body = p.evaluate("() => (document.getElementById('mtgBody')||{}).value || ''")
        ok("자동으로 글자·정리까지 이어진다", ("가짜 변환" in body or "내용>" in body), body[:50])

        # ── ② 표시가 없으면 고른다 ──
        print("\n■ ② 표시가 없으면 어디에 붙일지 고른다", flush=True)
        p.goto(BASE + "/meetings", wait_until="domcontentloaded")
        p.evaluate("() => localStorage.removeItem('knk_mtg_phonerec')")
        p.evaluate(SHARE_JS, "회의녹음 002.m4a")
        p.wait_for_url("**/share/audio", timeout=20000)
        p.wait_for_timeout(800)
        ok("받은 파일 이름이 보인다", "회의녹음 002.m4a" in (p.locator("main").inner_text() or ""))
        ok("고르는 칸이 보인다", p.locator("#shPickWrap").is_visible())
        ok("「＋ 새 회의록으로 정리」가 있다", p.locator("#shNew").is_visible())
        ok("최근 회의도 고를 수 있다", p.locator("[data-mid]").count() >= 1, p.locator("[data-mid]").count())

        # ── ③ 「＋ 새 회의록으로 정리」 ──
        print("\n■ ③ 새 회의록으로 정리", flush=True)
        p.locator("#shNew").click()
        p.wait_for_url("**/meetings/**", timeout=20000)
        ok("새 회의록으로 옮겨진다", "/meetings/" in p.url and p.url.split("?")[0].split("/")[-1].isdigit(), p.url)
        ok("새 회의록도 자동 정리로 들어갔다(?auto=1)", any("auto=1" in u for u in NAV[-3:]), NAV[-2:])
        for _ in range(60):
            b = p.evaluate("() => (document.getElementById('mtgBody')||{}).value || ''")
            if "가짜 변환" in b or "내용>" in b:
                break
            p.wait_for_timeout(500)
        body = p.evaluate("() => (document.getElementById('mtgBody')||{}).value || ''")
        ok("새 회의록도 자동으로 정리된다", ("가짜 변환" in body or "내용>" in body), body[:50])

        # ── ④ 최근 회의에 이어 붙이기 ──
        print("\n■ ④ 최근 회의에 이어 붙이기", flush=True)
        p.goto(BASE + "/meetings", wait_until="domcontentloaded")
        p.evaluate("() => localStorage.removeItem('knk_mtg_phonerec')")
        p.evaluate(SHARE_JS, "회의녹음 003.m4a")
        p.wait_for_url("**/share/audio", timeout=20000)
        p.wait_for_timeout(800)
        b0 = p.locator("[data-mid]").first
        tgt = b0.get_attribute("data-mid")
        NAV.clear()
        b0.click()
        p.wait_for_url("**/meetings/%s**" % tgt, timeout=20000)
        ok("고른 회의록으로 옮겨진다", p.url.split("?")[0].endswith("/meetings/%s" % tgt), (tgt, p.url))
        ok("고른 회의록도 자동 정리로 들어갔다(?auto=1)",
           any(u.split("?")[0].endswith("/meetings/%s" % tgt) and "auto=1" in u for u in NAV), NAV[-2:])

        # ── ⑤ 음성이 아니면 ──
        print("\n■ ⑤ 음성이 아닌 것이 오면", flush=True)
        p.goto(BASE + "/meetings", wait_until="domcontentloaded")
        p.evaluate("""() => {
          const f = new File([new Uint8Array(500)], '메모.txt', {type:'text/plain'});
          const dt = new DataTransfer(); dt.items.add(f);
          const form = document.createElement('form');
          form.method='POST'; form.action='/share/audio'; form.enctype='multipart/form-data';
          const i=document.createElement('input'); i.type='file'; i.name='audio'; i.files=dt.files;
          form.appendChild(i); document.body.appendChild(form); form.submit(); }""")
        p.wait_for_url("**/share/audio", timeout=20000)
        p.wait_for_timeout(500)
        ok("음성 파일만 받는다고 알린다", "지원하지 않는 음성 형식" in (p.locator("main").inner_text() or ""))

        errs = []
        p.on("pageerror", lambda e: errs.append(str(e)))
        p.wait_for_timeout(300)
        ok("화면 스크립트 오류 없음", not errs, errs[:2])

        c.close()
        br.close()

    print("\n" + "=" * 60)
    print("합계: 통과 %d · 실패 %d" % (len(OK), len(NG)))
    for n in NG:
        print("  ❌ " + n)
    sys.exit(1 if NG else 0)


main()
