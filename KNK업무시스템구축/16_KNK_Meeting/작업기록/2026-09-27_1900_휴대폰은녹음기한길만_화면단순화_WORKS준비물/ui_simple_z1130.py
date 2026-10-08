# -*- coding: utf-8 -*-
"""z1130 화면 시험 — 휴대폰은 녹음기 한 길만(안내 2줄 + 올리기) · 나머지는 「다른 방법」 접기
  + 🔴 「녹음 시작」 먹통 버그(휴대폰 녹음기를 고른 뒤 눌러도 아무 일 없던 것) 재발 방지
사용: py -3.12 ui_simple_z1130.py [포트=8936]
"""
# 🔴 z1143(대표 지시 2026-10-07): 사람이 눌러 시작하는 이 화면 녹음은 막혔다.
#   이 묶음이 재는 것은 「녹음이 도는 동안」의 동작이고, 그 길은 이음 「▶ 회의 시작」
#   자동 녹음으로 그대로 산다 → 아래에서 그 길과 **똑같은 표시**를 켜고 시작한다.
#   (막혔는지 자체는 ui_block_z1143.py 가 따로 잰다)
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8936
BASE = "http://127.0.0.1:%d" % PORT
HERE = os.path.dirname(os.path.abspath(__file__))

UA_SAMSUNG = ("Mozilla/5.0 (Linux; Android 14; SM-S928N) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/153.0.0.0 Mobile Safari/537.36")
UA_IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
          "CriOS/153.0.0.0 Mobile/15E148 Safari/604.1")
UA_PC = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
         "Chrome/153.0.0.0 Safari/537.36")

OK, NG, ERRS = [], [], []


def ok(name, cond, extra=""):
    (OK if cond else NG).append(name)
    print(("  ✅ " if cond else "  ❌ ") + name + (("  — " + str(extra)[:180]) if extra != "" else ""), flush=True)


def ctx(br, ua, phone=True):
    # 🔴 z1144(2026-10-08): 앱 설치 안내 팝업(#worksInstallHint)을 끔다.
    #   휴대폰 UA 에서 불러온 뒤 약 1.2초 뒤에 떠 화면을 덮는다(세션당 1회).
    #   이 묶음은 불러오고 곧바로 누르므로 경주에 기대고 있었다 — 팝업은
    #   정상 기능이고 여기서 재는 대상이 아니다 → 꺼 두고 본디만 재다.
    _c = br.new_context(user_agent=ua,
                          viewport={"width": 390, "height": 844} if phone else {"width": 1440, "height": 900},
                          is_mobile=phone, has_touch=phone, permissions=["microphone"], base_url=BASE)
    _c.add_init_script("try{localStorage.setItem('knk_works_install_hint_never','1')}catch(e){}")
    return _c


def open_page(c, path, reqs=None):
    p = c.new_page()
    p.on("pageerror", lambda e: ERRS.append(str(e)))
    if reqs is not None:
        p.on("request", lambda r: reqs.append(r.method + " " + r.url.replace(BASE, "")))
    p.goto(BASE + path, wait_until="domcontentloaded")
    p.wait_for_timeout(900)
    return p


def in_other(p, elid):
    return p.evaluate("(id) => { const s=document.getElementById('recOtherSlot'), e=document.getElementById(id);"
                      " return !!s && !!e && s.contains(e); }", elid)


def main():
    seed = json.load(open(os.path.join(HERE, "seed_phrec.json"), encoding="utf-8"))
    mids = seed.get("mids") or [1]
    MID = mids[0]                 # 녹음 시험용
    MID2 = mids[2] if len(mids) > 2 else mids[-1]   # 이음 착지 시험용(녹음이 없는 회의)
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True, args=[
            "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])

        # ══════════ ① 안드로이드 새 회의록 화면 — 한 길만 ══════════
        print("\n■ ① 안드로이드 — 새 회의록 화면", flush=True)
        c = ctx(br, UA_SAMSUNG)
        p = open_page(c, "/meetings/new")
        g = p.locator("#recPhoneGuide")
        ok("안내 카드가 보인다", g.is_visible())
        gt = (g.inner_text() or "").replace("\n", " ")
        ok("제목 = 🎤 이 회의 녹음", "이 회의 녹음" in gt, gt[:40])
        ok("① 홈 화면에서 「음성 녹음」", "홈 화면" in gt and "음성 녹음" in gt, gt[:110])
        ok("① 안 끊긴다고 적는다", "안 끊깁니다" in gt, gt[:130])
        ok("② 공유 → KNK WORKS", "공유 → KNK WORKS" in gt, gt[-110:])
        ok("안내는 두 줄뿐(③·※ 없음)", "③" not in gt and "크롬은 웹에서" not in gt, gt[-60:])
        ok("「📁 녹음 파일 올리기」가 접히지 않고 보인다",
           p.locator("label.rec-file").first.is_visible())
        o = p.locator("#recOther")
        ok("「다른 방법」 접기가 보인다", o.is_visible())
        ok("접힌 채로 시작한다", not p.evaluate("() => document.getElementById('recOther').open"))
        ok("이 화면 녹음 단추는 접기 안에", in_other(p, "recBtn"))
        ok("짧은 녹음(capture)도 접기 안에", in_other(p, "recPhoneRecWrap"))
        body = p.locator("body").inner_text()
        ok("🔴 「30초 안에 누르지 않으면」 안내가 없다", "30초 안에 누르지" not in body)
        ok("🔴 옛 「녹음기 앱 열기」 자취 없음", "녹음기 앱 열기" not in body)
        c.close()

        # ══════════ ② 다른 방법 → 「녹음하며 회의」가 실제로 돈다 ══════════
        print("\n■ ② 「다른 방법」 → 이 화면 녹음", flush=True)
        reqs = []
        c = ctx(br, UA_SAMSUNG)
        p = open_page(c, "/meetings/%d" % MID, reqs)
        p.evaluate("() => { const d=document.getElementById('redoTools'); if(d) d.open=true; }")
        p.wait_for_timeout(300)
        p.evaluate("() => { const d=document.getElementById('recOther'); if(d) d.open=true; }")
        p.wait_for_timeout(300)
        n0 = len(reqs)
        p.evaluate("()=>{var b=document.getElementById('recBtn'); if(b) b.dataset.autorec='1';}")  # z1143
        p.locator("#recBtn").click()
        p.wait_for_timeout(2500)
        started = [r for r in reqs[n0:] if "rec-start" in r]
        ok("녹음이 실제로 시작된다(서버에 rec-start)", bool(started), started[:1])
        ok("단추가 「녹음 종료」로 바뀐다", "녹음 종료" in (p.locator("#recBtn").inner_text() or ""),
           (p.locator("#recBtn").inner_text() or "")[:30])
        ok("녹음 띠가 보인다", p.locator("#recBanner").is_visible())
        p.evaluate("()=>{var b=document.getElementById('recBtn'); if(b) b.dataset.autorec='1';}")  # z1143
        p.locator("#recBtn").click()          # 끝내기
        p.wait_for_timeout(1500)
        c.close()

        # ══════════ ③ 🔴 짧은 녹음을 고른 뒤에도 「녹음 시작」이 산다(버그 재발 방지) ══════════
        print("\n■ ③ 🔴 휴대폰 녹음기를 고른 뒤 「녹음 시작」", flush=True)
        reqs = []
        c = ctx(br, UA_SAMSUNG)
        p = open_page(c, "/meetings/%d" % MID, reqs)
        p.evaluate("() => { const d=document.getElementById('redoTools'); if(d) d.open=true; }")
        p.evaluate("() => { const d=document.getElementById('recOther'); if(d) d.open=true; }")
        p.wait_for_timeout(300)
        with p.expect_file_chooser() as fc:                    # 짧은 녹음(capture)을 실제로 고른다
            p.locator("#recPhoneRecWrap").click()
        _ = fc.value
        p.wait_for_timeout(600)
        ok("짧은 녹음(녹음기) 고르기가 열렸다", True)
        n0 = len(reqs)
        p.evaluate("()=>{var b=document.getElementById('recBtn'); if(b) b.dataset.autorec='1';}")  # z1143
        p.locator("#recBtn").click()
        p.wait_for_timeout(2500)
        started = [r for r in reqs[n0:] if "rec-start" in r]
        ok("🔴 그래도 「녹음 시작」이 돈다(옛 버그 없음)", bool(started), started[:1])
        ok("단추가 「녹음 종료」로 바뀐다", "녹음 종료" in (p.locator("#recBtn").inner_text() or ""),
           (p.locator("#recBtn").inner_text() or "")[:30])
        p.evaluate("()=>{var b=document.getElementById('recBtn'); if(b) b.dataset.autorec='1';}")  # z1143
        p.locator("#recBtn").click()
        p.wait_for_timeout(1200)
        c.close()

        # ══════════ ④ 이음 「▶ 회의 시작」(?autorec=1) — 자동 시작 없음 ══════════
        print("\n■ ④ 이음 회의 시작으로 들어왔을 때", flush=True)
        reqs = []
        c = ctx(br, UA_SAMSUNG)
        p = open_page(c, "/meetings/%d?autorec=1" % MID2, reqs)
        p.wait_for_timeout(3000)
        ok("안내 카드가 보인다", p.locator("#recPhoneGuide").is_visible())
        ok("옛 고르기 상자는 안 뜬다", not p.locator("#recPhoneLead").is_visible())
        st = (p.locator("#recStatus").inner_text() or "")
        ok("상태줄이 홈 화면 녹음기를 안내한다", "홈 화면" in st and "음성 녹음" in st, st[:110])
        ok("이 화면 녹음이 저절로 켜지지 않는다", not p.evaluate("() => !!(window._mr && window._mr.state==='recording')"))
        ok("서버에도 rec-start 가 안 갔다", not [r for r in reqs if "rec-start" in r])
        c.close()

        # ══════════ ⑤ 아이폰·PC 는 그대로 ══════════
        print("\n■ ⑤ 아이폰·PC", flush=True)
        for ua, nm, phone in ((UA_IOS, "아이폰", True), (UA_PC, "PC", False)):
            c = ctx(br, ua, phone)
            p = open_page(c, "/meetings/new")
            ok("%s: 안내 카드 숨김" % nm, not p.locator("#recPhoneGuide").is_visible())
            ok("%s: 「다른 방법」 접기 숨김" % nm, not p.locator("#recOther").is_visible())
            ok("%s: 「🎤 녹음하며 회의」가 그대로 보인다" % nm, p.locator("#recBtn").is_visible())
            ok("%s: 녹음 단추가 접기 안으로 안 갔다" % nm, not in_other(p, "recBtn"))
            c.close()

        print("\n" + "=" * 72)
        ok("화면 오류 없음", not ERRS, ERRS[:2])
        print("합계: 통과 %d · 실패 %d" % (len(OK), len(NG)), flush=True)
        for n in NG:
            print("  - 실패:", n, flush=True)
        br.close()
    return 1 if NG else 0


if __name__ == "__main__":
    sys.exit(main())
