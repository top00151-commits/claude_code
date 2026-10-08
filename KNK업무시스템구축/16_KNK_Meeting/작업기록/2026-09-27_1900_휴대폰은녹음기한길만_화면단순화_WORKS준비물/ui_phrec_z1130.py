# -*- coding: utf-8 -*-

# z1130: 휴대폰은 「다른 방법」(이 화면 녹음·짧은 녹음)이 접혀 있다 — 시험은 열어 놓고 본다
OPEN_OTHER = ("document.addEventListener('DOMContentLoaded', function(){ setTimeout(function(){"
              " var d=document.getElementById('recOther'); if(d) d.open=true; }, 0); });")
"""z1115+z1127 화면 시험 — 「📱 휴대폰 녹음기로 녹음」(안드로이드) · 아이폰 안내 · 목록 표시줄

실제 크롬(가짜 마이크)으로 안드로이드/아이폰/PC 세 가지 기기를 흉내 내 확인한다.
사용: py -3.12 ui_phrec.py [포트=8936]
"""
import json
import os
import struct
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8936
BASE = "http://127.0.0.1:%d" % PORT
HERE = os.path.dirname(os.path.abspath(__file__))
WAV = os.path.join(HERE, "_시험용_녹음.wav")

UA_AND = ("Mozilla/5.0 (Linux; Android 14; SM-S928N) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/153.0.0.0 Mobile Safari/537.36")
UA_IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
          "CriOS/153.0.0.0 Mobile/15E148 Safari/604.1")
UA_PC = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
         "Chrome/153.0.0.0 Safari/537.36")

OK, NG = [], []


def chk(name, cond, extra=""):
    (OK if cond else NG).append(name)
    print(("  ✅ " if cond else "  ❌ ") + name + (("  — " + str(extra)) if extra else ""), flush=True)


def make_wav(path, secs=1):
    rate = 8000
    n = rate * secs
    data = b"".join(struct.pack("<h", 0) for _ in range(n))
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16))
        f.write(b"data" + struct.pack("<I", len(data)) + data)


def ctx(br, ua, phone):
    c = br.new_context(
        user_agent=ua,
        viewport={"width": 390, "height": 844} if phone else {"width": 1440, "height": 900},
        is_mobile=phone, has_touch=phone,
        permissions=["microphone"], base_url=BASE)
    c.add_init_script(OPEN_OTHER)
    # 🔴 z1144(2026-10-08): 앱 설치 안내 팝업(#worksInstallHint)을 끔다.
    #   그 팝업은 휴대폰 UA 에서 불러온 뒤 약 1.2초 뒤에 떠 화면을 덮는다(세션당 1회).
    #   이 묶음은 `load` 뒤 700ms 에 누르므로 **0.5초 차 경주**에 기대고 있었다 —
    #   페이지가 조금만 무거워지면(메뉴 한 줄) 경주가 뒤집혀 엉똑한 고장처럼 보였다.
    #   팝업 자체는 정상 기능이고 이 묶음이 재는 대상이 아니다 → 꺼 두고 본디만 재다.
    c.add_init_script("try{localStorage.setItem('knk_works_install_hint_never','1')}catch(e){}")
    return c


def main():
    make_wav(WAV)
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True, args=[
            "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream", "--autoplay-policy=no-user-gesture-required"])

        # ══════════════ ① 안드로이드 — 새 회의 화면 ══════════════
        print("\n① 안드로이드 · 새 회의 화면", flush=True)
        c = ctx(br, UA_AND, True)
        p = c.new_page()
        p.goto(BASE + "/meetings/new", wait_until="load")
        p.wait_for_timeout(700)

        wrap = p.locator("#recPhoneRecWrap")
        chk("안드로이드: 「📱 녹음기로 바로 녹음」 단추가 보인다(z1127)", wrap.is_visible())
        chk("z1130 첫 선택 = 안내 카드가 보인다", p.locator("#recPhoneGuide").is_visible())
        chk("z1129 옛 「녹음기 앱 열기」 단추는 없다", p.locator("#recOpenApp").count() == 0)
        chk("단추 글자(z1127)", "녹음기로 바로 녹음" in (wrap.inner_text() or ""), wrap.inner_text().replace("\n", " ")[:40])
        chk("z1127 사실대로 — 다른 앱으로 가면 저장되고 끝남", "저장되고 끝납니다" in (wrap.inner_text() or ""))

        order = p.evaluate("""() => {
            const w=document.getElementById('recPhoneRecWrap'), b=document.getElementById('recBtn');
            if(!w||!b) return 'missing';
            return (w.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) ? 'phone-first' : 'rec-first';
        }""")
        chk("녹음기 단추가 「🎙 녹음하며 회의」보다 위", order == "phone-first", order)

        cap = p.evaluate("""() => {
            const i=document.getElementById('recFileCap');
            return i ? {cap:i.hasAttribute('capture'), acc:i.getAttribute('accept'), t:i.type} : null;
        }""")
        chk("숨은 입력에 capture 속성", bool(cap and cap["cap"]), cap)
        chk("accept=audio/*", bool(cap and cap["acc"] == "audio/*"), cap and cap["acc"])

        chk("「🎙 녹음하며 회의」는 두 번째 선택(alt 색)",
            p.evaluate("() => document.getElementById('recBtn').classList.contains('alt')"))

        note = p.locator("#recPlatNote")
        nt = note.inner_text() if note.count() and note.is_visible() else ""
        chk("안드로이드 안내 상자가 보인다", note.is_visible())
        chk("안내에 「안드로이드」", "안드로이드" in nt)
        chk("안내에 홈 화면에서 여는 길(z1129)", "홈 화면" in nt and "음성 녹음" in nt)
        chk("안내에 「이 화면을 켜 둘 때만」", "켜 둘 때만" in nt)

        # 기존 「📁 녹음 파일 올리기」는 그대로(capture 없음)
        chk("기존 「📁 녹음 파일 올리기」는 capture 없음(파일 고르기 그대로)",
            p.evaluate("() => { const i=document.getElementById('recFile'); return !!i && !i.hasAttribute('capture'); }"))

        # 단추를 누르면 → 파일 고르기 창이 열리고(=녹음기 연결) 회의가 먼저 만들어진다
        p.evaluate("() => { window.__posts=[]; }")
        p.on("request", lambda r: p.evaluate("(u)=>window.__posts.push(u)", r.url)
             if r.method == "POST" and r.url.endswith("/api/meeting") else None)
        with p.expect_file_chooser() as fc_info:
            wrap.click()
        fc = fc_info.value
        chk("누르면 녹음기(파일 고르기)가 열린다", fc is not None)
        p.wait_for_timeout(1200)

        st = (p.locator("#recStatus").inner_text() or "")
        chk("상태줄 안내 「휴대폰 녹음기가 열립니다」", "휴대폰 녹음기가 열립니다" in st, st[:60])

        mark = p.evaluate("() => { try{ return JSON.parse(localStorage.getItem('knk_mtg_phonerec')||'null'); }catch(_){ return 'ERR'; } }")
        chk("회의가 먼저 저장되고 표시가 남는다", bool(mark and mark.get("id")), mark)
        mid = (mark or {}).get("id")

        # 녹음기가 돌려준 파일 → 평소 올리기와 같은 길
        p.locator("#recFileCap").set_input_files(WAV)
        for _ in range(60):
            if "정리" in (p.locator("#recStatus").inner_text() or "") or p.url.rstrip("/").endswith(str(mid)):
                break
            p.wait_for_timeout(500)
        p.wait_for_timeout(2500)
        gone = p.evaluate("() => localStorage.getItem('knk_mtg_phonerec')")
        chk("파일이 올라가면 표시가 스스로 지워진다", gone is None, gone)
        body = p.evaluate("() => (document.getElementById('mtgBody')||{}).value || ''")
        chk("음성→글자 결과가 회의 내용에 들어온다", "가짜 변환" in body, body[:40])
        c.close()

        # ══════════════ ② 아이폰 — 단추 없음 · 안내만 ══════════════
        print("\n② 아이폰 · 새 회의 화면", flush=True)
        c = ctx(br, UA_IOS, True)
        p = c.new_page()
        p.goto(BASE + "/meetings/new", wait_until="load")
        p.wait_for_timeout(700)
        chk("아이폰: 녹음기 단추는 보이지 않는다", not p.locator("#recPhoneRecWrap").is_visible())
        chk("아이폰: 「🎙 녹음하며 회의」는 큰 빨강 그대로",
            p.evaluate("() => { const b=document.getElementById('recBtn'); return b.classList.contains('start-big') && !b.classList.contains('alt'); }"))
        note = p.locator("#recPlatNote")
        nt = note.inner_text() if note.is_visible() else ""
        chk("아이폰 안내 상자가 보인다", note.is_visible())
        chk("안내에 「아이폰·아이패드」", "아이폰" in nt)
        chk("안내에 「넘어가면 그동안은 녹음되지 않습니다」", "녹음되지 않습니다" in nt, nt[:70])
        chk("안내에 「이 화면을 켠 채로」", "켠 채로" in nt)
        # z1138(대표 지시 2026-10-05): 단추 이름을 「📁 녹음 파일 올리기」 하나로 통일했다(안내문과 달라 더 찾기 어려웠다)
        chk("안내에 대안(음성 메모 → 올리기)", "음성 메모" in nt and "녹음 파일 올리기" in nt)
        chk("아이폰 안내는 파란 상자(ios)",
            p.evaluate("() => document.getElementById('recPlatNote').classList.contains('ios')"))
        c.close()

        # ══════════════ ③ PC — 아무것도 늘지 않는다 ══════════════
        print("\n③ PC · 새 회의 화면", flush=True)
        c = ctx(br, UA_PC, False)
        p = c.new_page()
        p.goto(BASE + "/meetings/new", wait_until="load")
        p.wait_for_timeout(700)
        chk("PC: 녹음기 단추 없음", not p.locator("#recPhoneRecWrap").is_visible())
        chk("PC: 기기별 안내 상자 없음", not p.locator("#recPlatNote").is_visible())
        chk("PC: 「🎙 녹음하며 회의」 그대로",
            p.evaluate("() => { const b=document.getElementById('recBtn'); return b.classList.contains('start-big') && !b.classList.contains('alt'); }"))
        # 🔴 z1143(대표 지시 2026-10-07): PC 에서도 사람이 눌러 시작하는 이 화면 녹음은 막는다.
        #   예전엔 여기서 「PC 는 여전히 녹음이 시작된다」를 봤다(안드로이드 전용 변경이 PC 를
        #   건드리지 않았는지 보는 회귀). 이제 의도가 바뀌어 **막히는 것이 정상**이다.
        p.locator("#recBtn").click()
        p.wait_for_timeout(2000)
        chk("PC: 눌러도 녹음이 시작되지 않는다(z1143)",
            p.evaluate("() => { const b=document.getElementById('recBanner'); return !b || b.hidden; }"))
        chk("PC: 휴대폰 녹음기를 쓰라는 안내가 뜬다(z1143)",
            p.evaluate("() => { const n=document.getElementById('recBlockNote');"
                       " return !!n && !n.hidden && (n.innerText||'').indexOf('녹음기') >= 0; }"))
        c.close()

        # ══════════════ ④ 상세 화면(안드로이드) ══════════════
        print("\n④ 안드로이드 · 회의록 상세 「🔧 다시 하기」", flush=True)
        c = ctx(br, UA_AND, True)
        p = c.new_page()
        p.goto(BASE + "/meetings/2", wait_until="load")
        p.wait_for_timeout(700)
        p.evaluate("() => { const d=document.getElementById('redoTools'); if(d) d.open=true; }")
        p.wait_for_timeout(300)
        chk("상세: 「📱 휴대폰 녹음기로 녹음」 단추가 보인다", p.locator("#recPhoneRecWrap").is_visible())
        chk("상세: 기기별 안내 상자가 보인다", p.locator("#recPlatNote").is_visible())
        chk("상세: capture 입력이 있다",
            p.evaluate("() => { const i=document.getElementById('recFileCap'); return !!i && i.hasAttribute('capture'); }"))
        with p.expect_file_chooser() as fc_info:
            p.locator("#recPhoneRecWrap").click()
        chk("상세: 누르면 녹음기가 열린다", fc_info.value is not None)
        p.wait_for_timeout(800)
        mk = p.evaluate("() => { try{ return JSON.parse(localStorage.getItem('knk_mtg_phonerec')||'null'); }catch(_){ return 'ERR'; } }")
        chk("상세: 표시에 이 회의 번호가 남는다", bool(mk and mk.get("id") == 2), mk)
        c.close()

        # ══════════════ ⑤ 목록 표시줄 ══════════════
        print("\n⑤ 회의록 목록 · 「📱 녹음기로 녹음하던 회의」 표시줄", flush=True)
        c = ctx(br, UA_AND, True)
        p = c.new_page()
        p.goto(BASE + "/meetings", wait_until="load")
        p.wait_for_timeout(500)
        chk("표시가 없으면 표시줄은 숨어 있다", not p.locator("#mtgPhRecBar").is_visible())

        p.evaluate("""() => localStorage.setItem('knk_mtg_phonerec',
            JSON.stringify({id:3,title:'주간 영업회의',at:Date.now()-25*60*1000}))""")
        p.reload(wait_until="load")
        p.wait_for_timeout(500)
        chk("표시가 있으면 표시줄이 보인다", p.locator("#mtgPhRecBar").is_visible())
        chk("회의 제목이 보인다", "주간 영업회의" in (p.locator("#mtgPhRecLink").inner_text() or ""))
        chk("그 회의로 연결된다", (p.locator("#mtgPhRecLink").get_attribute("href") or "").endswith("/meetings/3"))
        chk("경과 시간이 보인다(25분 전)", "25분 전" in (p.locator("#mtgPhRecWhen").inner_text() or ""),
            p.locator("#mtgPhRecWhen").inner_text())
        chk("올릴 곳 안내", "음성 파일 올리기" in (p.locator("#mtgPhRecBar").inner_text() or ""))

        p.locator("#mtgPhRecDrop").click()
        p.wait_for_timeout(300)
        chk("「표시 지우기」로 사라진다", not p.locator("#mtgPhRecBar").is_visible())
        chk("표시도 함께 비워진다", p.evaluate("() => localStorage.getItem('knk_mtg_phonerec')") is None)

        p.evaluate("""() => localStorage.setItem('knk_mtg_phonerec',
            JSON.stringify({id:3,title:'어제 회의',at:Date.now()-13*3600*1000}))""")
        p.reload(wait_until="load")
        p.wait_for_timeout(500)
        chk("12시간 넘은 표시는 무시된다", not p.locator("#mtgPhRecBar").is_visible())
        chk("12시간 넘은 표시는 스스로 지워진다",
            p.evaluate("() => localStorage.getItem('knk_mtg_phonerec')") is None)
        c.close()

        br.close()

    print("\n" + "=" * 60)
    print("통과 %d / 실패 %d" % (len(OK), len(NG)))
    if NG:
        for n in NG:
            print("  ❌ " + n)
    try:
        os.remove(WAV)
    except OSError:
        pass
    sys.exit(1 if NG else 0)


main()
