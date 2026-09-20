# -*- coding: utf-8 -*-
"""z1116 화면 시험 — 이음 「▶ 회의 시작」(?autorec=1) 착지에서 휴대폰 녹음기로 넘기기

가짜 마이크(크롬)로 실제 녹음을 돌린 뒤, 녹음기 단추를 눌렀을 때
  · 이 화면 녹음이 깨끗이 멈추는지(겹침 없음)
  · 그 순간에 '정리'가 시작되지 않는지(두 번 정리 방지)
  · 녹음기 파일이 들어온 뒤 한 번만 정리하며 두 조각이 순서대로 붙는지
를 본다. 사용: py -3.12 ui_lead.py <seed_phrec.json 폴더>
"""
import io
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

SEED_DIR = sys.argv[1]
seed = json.load(io.open(os.path.join(SEED_DIR, "seed_phrec.json"), encoding="utf-8"))
PORT = seed["port"]
MIDS = seed["mids"]
BASE = "http://localhost:%d" % PORT
HERE = os.path.dirname(os.path.abspath(__file__))
WAV = os.path.join(HERE, "_시험용_녹음기파일.wav")

UA_AND = ("Mozilla/5.0 (Linux; Android 14; SM-S928N) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/153.0.0.0 Mobile Safari/537.36")
UA_IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
          "CriOS/153.0.0.0 Mobile/15E148 Safari/604.1")
UA_PC = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
         "Chrome/153.0.0.0 Safari/537.36")
HIDE = ("document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style');"
        "s.textContent = '#worksInstallHint{display:none !important}'; document.head.appendChild(s); });")

OK, NG = [], []


def ok(name, cond, extra=""):
    (OK if cond else NG).append(name)
    print(("PASS " if cond else "FAIL ") + name + ((" · " + str(extra)[:200]) if extra != "" else ""), flush=True)


def make_wav(path, secs=2):
    rate, n = 8000, 8000 * 2
    data = b"".join(struct.pack("<h", 0) for _ in range(n))
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16))
        f.write(b"data" + struct.pack("<I", len(data)) + data)


def ctx(br, ua, phone):
    c = br.new_context(service_workers="block", permissions=["microphone"], user_agent=ua,
                       viewport={"width": 390, "height": 844} if phone else {"width": 1280, "height": 900},
                       is_mobile=phone, has_touch=phone)
    c.add_init_script(HIDE)
    return c


def api(pg, path):
    return pg.evaluate("""async (p) => { const r = await fetch(p); return await r.json(); }""", path)


def main():
    make_wav(WAV)
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True,
                                args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])

        # ══════════ ① 안드로이드 · 이음 「▶ 회의 시작」 착지 ══════════
        print("\n■ ① 안드로이드 — 이음 「▶ 회의 시작」(?autorec=1) 착지", flush=True)
        M1 = MIDS[0]
        c = ctx(br, UA_AND, True)
        p = c.new_page()
        calls = []
        p.on("request", lambda r: calls.append(r.url.replace(BASE, "")) if "/api/meeting" in r.url else None)
        p.goto("%s/meetings/%d?autorec=1" % (BASE, M1), wait_until="domcontentloaded")
        p.wait_for_timeout(3500)

        lead = p.locator("#recPhoneLead")
        ok("착지 안내 상자가 보인다", lead.is_visible())
        lt = lead.inner_text() if lead.is_visible() else ""
        ok("상자가 「아직 녹음이 시작되지 않았습니다」로 뜬다(z1118 — 안드로이드는 녹음기가 기본)",
           "아직 녹음이 시작되지 않았습니다" in lt, lt[:60])
        ok("녹음기 단추가 상자 안에 있다",
           p.evaluate("() => { const s=document.getElementById('recPhoneLeadSlot'), w=document.getElementById('recPhoneRecWrap');"
                      " return !!s && !!w && s.contains(w); }"))
        ok("녹음기 입력은 하나뿐(중복 없음)",
           p.evaluate("() => document.querySelectorAll('#recFileCap').length") == 1)
        ok("z1118 — 이 화면 녹음은 저절로 켜지지 않는다",
           not p.evaluate("() => { const b=document.getElementById('recBanner'); return !!b && !b.hidden; }"))
        # 넘기기(z1116)를 보려면 이 화면 녹음이 돌고 있어야 한다 → 직접 켠다
        p.locator("#recBtn").click()
        p.wait_for_timeout(3000)
        ok("「🎙 녹음 시작」으로 이 화면 녹음이 켜진다",
           p.evaluate("() => { const b=document.getElementById('recBanner'); return !!b && !b.hidden; }"))
        st = api(p, "/api/meeting/%d/rec-status" % M1)
        ok("서버도 「녹음 중」으로 안다", (st.get("rec") or {}).get("state") == "recording", st.get("rec"))

        # 조각이 서버로 가도록 잠시 녹음
        p.wait_for_timeout(12000)

        # ── 녹음기로 넘기기 ──
        print("\n■ ② 녹음기로 넘기기 — 이 화면 녹음은 멈추고, 정리는 아직 안 한다", flush=True)
        calls.clear()
        with p.expect_file_chooser() as fc:
            p.locator("#recPhoneRecWrap").click()
        ok("누르면 녹음기(파일 고르기)가 열린다", fc.value is not None)
        p.wait_for_timeout(6000)

        ok("이 화면 녹음이 멈춘다(겹침 없음)",
           p.evaluate("() => { const b=document.getElementById('recBanner'); return !b || b.hidden; }"))
        stt = (p.locator("#recStatus").inner_text() or "")
        ok("상태줄 = 넘기는 중 안내", "녹음기로 넘깁니다" in stt or "서버에 저장됐습니다" in stt, stt[:90])
        st = api(p, "/api/meeting/%d/rec-status" % M1)
        ok("서버도 「녹음 중」이 아니다", (st.get("rec") or {}).get("state") != "recording", st.get("rec"))
        ok("rec-finish 로 마무리했다", any("rec-finish" in u for u in calls), [u for u in calls][-4:])
        ok("🔴 아직 정리(transcribe)를 시작하지 않았다", not any("transcribe" in u for u in calls),
           [u for u in calls if "transcribe" in u])
        pend = (st.get("rec") or {}).get("pending")
        ok("지금까지 녹음이 '아직 글자로 안 바꾼 녹음'에 남아 있다", (pend or 0) >= 1, st.get("rec"))

        # ── 녹음기가 돌려준 파일 ──
        print("\n■ ③ 녹음기 파일이 돌아오면 — 한 번만 정리하고 두 조각을 순서대로", flush=True)
        calls.clear()
        p.locator("#recFileCap").set_input_files(WAV)
        for _ in range(80):
            b = p.evaluate("() => (document.getElementById('mtgBody')||{}).value || ''")
            if b.count("가짜 변환") >= 2:
                break
            p.wait_for_timeout(500)
        p.wait_for_timeout(2000)
        body = p.evaluate("() => (document.getElementById('mtgBody')||{}).value || ''")
        ok("정리가 한 번 시작됐다", len([u for u in calls if "transcribe" in u]) == 1,
           [u for u in calls if "transcribe" in u])
        ok("두 조각(화면 녹음 + 녹음기 파일)이 모두 글자로 들어왔다", body.count("가짜 변환") >= 2,
           "가짜 변환 %d회" % body.count("가짜 변환"))
        ok("목록 표시도 지워졌다", p.evaluate("() => localStorage.getItem('knk_mtg_phonerec')") is None)
        c.close()

        # ══════════ ④ 안드로이드 · 녹음기에서 빈손으로 돌아옴 ══════════
        print("\n■ ④ 녹음기에서 파일 없이 돌아왔을 때 — 어디 있는지 알려 준다", flush=True)
        M2 = MIDS[1]
        c = ctx(br, UA_AND, True)
        p = c.new_page()
        p.goto("%s/meetings/%d?autorec=1" % (BASE, M2), wait_until="domcontentloaded")
        p.wait_for_timeout(3500)
        with p.expect_file_chooser() as fc:
            p.locator("#recPhoneRecWrap").click()
        _ = fc.value
        p.wait_for_timeout(1500)
        p.evaluate("""() => { Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>'hidden'});
                              document.dispatchEvent(new Event('visibilitychange')); }""")
        p.wait_for_timeout(800)
        p.evaluate("""() => { Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>'visible'});
                              document.dispatchEvent(new Event('visibilitychange')); }""")
        p.wait_for_timeout(6000)
        stt = (p.locator("#recStatus").inner_text() or "")
        ok("빈손 복귀 안내가 뜬다", "받은 파일이 없습니다" in stt, stt[:110])
        ok("안내가 올릴 방법을 알려 준다", "음성 파일 올리기" in stt and "다시 정리" in stt)
        c.close()

        # ══════════ ⑤ PC · 예전 그대로 ══════════
        print("\n■ ⑤ PC — 착지 상자 없음 · 자동 녹음 그대로", flush=True)
        M3 = MIDS[2]
        c = ctx(br, UA_PC, False)
        p = c.new_page()
        p.goto("%s/meetings/%d?autorec=1" % (BASE, M3), wait_until="domcontentloaded")
        p.wait_for_timeout(3500)
        ok("PC: 착지 상자 없음", not p.locator("#recPhoneLead").is_visible())
        ok("PC: 녹음기 단추 없음", not p.locator("#recPhoneRecWrap").is_visible())
        ok("PC: 자동 녹음은 그대로 시작된다",
           p.evaluate("() => { const b=document.getElementById('recBanner'); return !!b && !b.hidden; }"))
        c.close()

        # ══════════ ⑥ 아이폰 · 상자 없음 · 자동 녹음 + 안내 ══════════
        print("\n■ ⑥ 아이폰 — 착지 상자 없음(녹음기 못 엶) · 자동 녹음 + 안내", flush=True)
        M4 = MIDS[3]
        c = ctx(br, UA_IOS, True)
        p = c.new_page()
        p.goto("%s/meetings/%d?autorec=1" % (BASE, M4), wait_until="domcontentloaded")
        p.wait_for_timeout(3500)
        ok("아이폰: 착지 상자 없음", not p.locator("#recPhoneLead").is_visible())
        ok("아이폰: 녹음기 단추 없음", not p.locator("#recPhoneRecWrap").is_visible())
        ok("아이폰: 자동 녹음은 그대로 시작된다",
           p.evaluate("() => { const b=document.getElementById('recBanner'); return !!b && !b.hidden; }"))
        nt = p.locator("#recPlatNote").inner_text() if p.locator("#recPlatNote").is_visible() else ""
        ok("아이폰: 「넘어가면 그동안은 녹음되지 않습니다」 안내 그대로", "녹음되지 않습니다" in nt, nt[:70])
        c.close()

        br.close()

    print("\n" + "=" * 62)
    print("합계: 통과 %d · 실패 %d" % (len(OK), len(NG)))
    for n in NG:
        print("  ❌ " + n)
    try:
        os.remove(WAV)
    except OSError:
        pass
    sys.exit(1 if NG else 0)


main()
