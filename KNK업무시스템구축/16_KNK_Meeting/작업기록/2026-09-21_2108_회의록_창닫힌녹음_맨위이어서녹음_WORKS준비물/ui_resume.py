# -*- coding: utf-8 -*-
"""z1120 화면 시험 — 창을 닫아(✕) 멈춘 녹음: 「🔴 녹음 중이던 회의 · 🎙 이어서 녹음」이 화면 맨 위에 있는가

실제 크롬(가짜 마이크)으로 아이폰·안드로이드·PC 화면을 흉내 낸다. 서버 = run_resume_app.py (가짜 음성→글자 = 파일 이름).
  ① 아이폰 · 본인 녹음(운영 회의 41 과 같은 상황) — 카드 「📋 회의록 열기」로 온 화면 = /meetings/{id}
     상자가 첫 화면(스크롤 없이)에 보이고 「🎙 이어서 녹음」이 첫 단추 · 한 번 누르면 묻지 않고 녹음 · 녹음 띠도 첫 화면
     · 끝내면 끊긴 조각 → 이어서 녹음 순서로 본문에 붙고 정리까지
  ② 아이폰 · 대표가 남의 녹음을 봄 — 누르면 한 번 묻는다(취소=아무 일 없음 · 확인=이어서 녹음)
  ③ 대표가 남의 녹음 「끝내고 정리」 — 묻기(취소/확인)
  ④ 안드로이드 · 이어서 녹음 → 녹음 + 「📱 휴대폰 녹음기로 녹음하시겠어요?」 상자 → 녹음기로 넘기면 세 조각이 순서대로
  ⑤ 안드로이드 · 상자를 두고 녹음기 바로 → 열려 있던 내 녹음을 먼저 닫아 녹음기 파일과 함께 정리
  ⑥ 안드로이드 · 남의 녹음이 열린 회의에서 녹음기 → 남의 녹음은 닫지 않는다
  ⑦ PC — 상자가 본문 맨 위 · 누르면 녹음 칸으로 스크롤
  ⑧ 본인 「끝내고 정리」 — 묻지 않고 정리
  ⑨ 자동 녹음 착지(?autorec=1) + 열린 녹음 — 녹음이 켜지면 상자를 치운다(두 번째 녹음기 방지)
  ⑩ 녹음 없는 회의 — 상자 없음 · 칸 순서 그대로
  ⑪ 마이크 막힘 — 이어서 녹음이 실패하면 상자를 되살린다
  ⑫ 아이폰 안내 한 줄(실수로 닫았으면 카드 「📋 회의록 열기」)
사용: py -3.12 ui_resume.py <seed_resume.json 폴더> [base]   (base = 고치기 전 파일로 돌릴 때 — 실패해야 정상)
"""
import io
import json
import os
import re
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

SEED_DIR = sys.argv[1]
BASE_MODE = len(sys.argv) > 2 and sys.argv[2] == "base"
seed = json.load(io.open(os.path.join(SEED_DIR, "seed_resume.json"), encoding="utf-8"))
PORT, MIDS, CEO, STAFF = seed["port"], seed["mids"], seed["ceo"], seed["staff"]
BASE = "http://localhost:%d" % PORT
HERE = os.path.dirname(os.path.abspath(__file__))
WAV = os.path.join(HERE, "_시험용_녹음기파일.wav")

UA_AND = ("Mozilla/5.0 (Linux; Android 14; SM-S928N) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/153.0.0.0 Mobile Safari/537.36")
UA_IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
          "Version/18.2 Mobile/15E148 Safari/604.1")
UA_PC = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
         "Chrome/153.0.0.0 Safari/537.36")
HIDE = ("document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style');"
        "s.textContent = '#worksInstallHint{display:none !important}'; document.head.appendChild(s); });")
VH = 844   # 아이폰 화면 높이(390×844)

OK, NG = [], []


def ok(name, cond, extra=""):
    (OK if cond else NG).append(name)
    print(("PASS " if cond else "FAIL ") + name + ((" · " + str(extra)[:200]) if extra != "" else ""), flush=True)


def make_wav(path):
    rate, n = 8000, 16000
    data = b"".join(struct.pack("<h", 0) for _ in range(n))
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16))
        f.write(b"data" + struct.pack("<I", len(data)) + data)


def ctx(br, ua, phone, uid, mic=True):
    c = br.new_context(service_workers="block", permissions=(["microphone"] if mic else []), user_agent=ua,
                       viewport={"width": 390, "height": VH} if phone else {"width": 1280, "height": 900},
                       is_mobile=phone, has_touch=phone)
    c.add_cookies([{"name": "tuser", "value": str(uid), "url": BASE}])
    c.add_init_script(HIDE)
    return c


def rec_on(p):
    return p.evaluate("() => { const b=document.getElementById('recBanner'); return !!b && !b.hidden; }")


def api(p, path):
    return p.evaluate("""async (x) => { const r = await fetch(x); return await r.json(); }""", path)


def rec(p, mid):
    return (api(p, "/api/meeting/%d/rec-status" % mid).get("rec") or {})


def box(p):
    """상자 위치 — 문서 맨 위에서 몇 px · 화면에 보이나 · 단추 순서 · 본문 칸 중 몇 번째(휴대폰은 보이는 순서)."""
    return p.evaluate("""() => {
        const b = document.getElementById('recResume');
        if (!b) return {exists:false};
        const r = b.getBoundingClientRect(), cs = getComputedStyle(b);
        const btns = [...b.querySelectorAll('button')].map(x => x.textContent.trim());
        const wrap = document.querySelector('.mf-wrap');
        const kids = [...wrap.children].filter(x => getComputedStyle(x).display !== 'none' && x.offsetHeight > 0);
        kids.sort((a, c) => a.getBoundingClientRect().top - c.getBoundingClientRect().top);
        const first = kids[0] ? (kids[0].id || kids[0].className) : '';
        return {exists:true, shown: cs.display !== 'none' && b.offsetHeight > 0, top: Math.round(r.top + scrollY),
                bottom: Math.round(r.bottom + scrollY), btns, first, order: cs.order};
    }""")


def body_text(p):
    return p.evaluate("() => (document.getElementById('mtgBody')||{}).value || ''")


def names(bt):
    """본문에 붙은 가짜 글자(= 변환한 파일 이름) 순서. 점 뒤 띄어쓰기(z1092 무음 접기 · 대표 「하지 말고」)는 지운다."""
    return [x.replace(". ", ".") for x in re.findall(r"\[가짜 변환\] (rec_\d+\.\s?\w+)", bt)]


def old_id(mid):
    return "rec_%d." % (1789970000000 + mid * 1000)


def wait_body(p, needle, n=1, tries=90):
    for _ in range(tries):
        if body_text(p).count(needle) >= n:
            return True
        p.wait_for_timeout(500)
    return False


def main():
    make_wav(WAV)
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True,
                                args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])
        errs = []

        # ══════════ ① 아이폰 · 본인 녹음 — 운영 회의 41 과 같은 상황 ══════════
        print("\n■ ① 아이폰 · 본인 녹음 (카드 「📋 회의록 열기」 → /meetings/{id})", flush=True)
        A = MIDS["A"]
        c = ctx(br, UA_IOS, True, STAFF)
        p = c.new_page(); p.on("pageerror", lambda e: errs.append("①" + str(e)))
        dlg = []
        p.on("dialog", lambda d: (dlg.append(d.message), d.dismiss()))
        p.goto("%s/meetings/%d" % (BASE, A), wait_until="domcontentloaded")
        p.wait_for_timeout(1500)
        bx = box(p)
        print("   상자:", bx, flush=True)
        ok("상자가 있다", bx.get("exists") and bx.get("shown"), bx)
        ok("🔴 상자가 첫 화면에(스크롤 없이) 다 보인다", bx.get("bottom", 99999) <= VH, "top=%s bottom=%s" % (bx.get("top"), bx.get("bottom")))
        ok("🔴 본문 칸 중 맨 위", bx.get("first") == "recResume", bx.get("first"))
        ok("「🎙 이어서 녹음」이 첫 단추", (bx.get("btns") or [""])[0] == "🎙 이어서 녹음", bx.get("btns"))
        ok("「⏹ 녹음 끝내고 정리」도 있다", "⏹ 녹음 끝내고 정리" in (bx.get("btns") or []), bx.get("btns"))
        h = p.evaluate("() => { const b=document.getElementById('recResumeBtn').getBoundingClientRect(); return Math.round(b.height); }")
        ok("단추 높이 44px 이상(누르기 쉬움)", h >= 44, h)
        s0 = rec(p, A)
        ok("시험 전 서버 = 녹음 중(끊긴 조각 70초)", s0.get("state") == "recording" and s0.get("secs") == 70 and s0.get("mine"), s0)

        p.locator("#recResumeBtn").click()
        p.wait_for_timeout(2500)
        ok("🔴 본인 녹음 = 묻지 않고 바로", not dlg, dlg)
        ok("누르면 이 화면 녹음이 켜진다", rec_on(p))
        ok("상자는 치워진다", not box(p).get("shown"))
        s1 = rec(p, A)
        ok("서버 = 새 녹음(끊긴 조각은 보관 1개)", s1.get("state") == "recording" and s1.get("pending") == 1 and s1.get("secs") == 0, s1)
        bn = p.evaluate("() => { const r=document.getElementById('recBanner').getBoundingClientRect(); return {top:Math.round(r.top), bottom:Math.round(r.bottom)}; }")
        ok("🔴 녹음 띠(🔴 본 회의 녹음 중)가 첫 화면에 보인다", 0 <= bn["top"] and bn["bottom"] <= VH, bn)
        sb = p.evaluate("() => { const r=document.getElementById('recBtn').getBoundingClientRect(); return {top:Math.round(r.top), bottom:Math.round(r.bottom), t:document.getElementById('recBtn').textContent}; }")
        ok("「⏹ 녹음 종료」 단추도 첫 화면에", 0 <= sb["top"] and sb["bottom"] <= VH and "녹음 종료" in sb["t"], sb)
        p.wait_for_timeout(11500)   # 10초 조각 하나 이상
        s2 = rec(p, A)
        ok("조각이 서버에 쌓인다", (s2.get("secs") or 0) >= 9, s2)
        p.locator("#recBtn").click()   # ⏹ 녹음 종료 → 자동 정리
        ok("끝내면 자동으로 글자 두 개(끊긴 조각 + 이어서 녹음)", wait_body(p, "[가짜 변환]", 2), body_text(p)[:160])
        nm = names(body_text(p))
        ok("🔴 순서 = 끊긴 조각 먼저 → 이어서 녹음", len(nm) == 2 and nm[0].startswith(old_id(A))
           and nm[1].endswith(".webm") and not nm[1].startswith(old_id(A)), nm)
        s3 = rec(p, A)
        ok("끝난 뒤 서버 = 녹음 아님 · 남은 조각 0", s3.get("state") != "recording" and s3.get("pending") == 0, s3)
        for _ in range(30):
            if "시험용 가짜 정리" in (p.locator("#mtgSummary").inner_text() or ""):
                break
            p.wait_for_timeout(500)
        ok("AI 정리까지", "시험용 가짜 정리" in (p.locator("#mtgSummary").inner_text() or ""))
        c.close()

        # ══════════ ② 아이폰 · 대표가 남의 녹음 — 묻기 ══════════
        print("\n■ ② 대표가 남(안지연)의 녹음 화면 — 「🎙 이어서 녹음」은 한 번 묻는다", flush=True)
        B = MIDS["B"]
        c = ctx(br, UA_IOS, True, CEO)
        p = c.new_page(); p.on("pageerror", lambda e: errs.append("②" + str(e)))
        answers, msgs = ["dismiss", "accept"], []

        def on_dlg(d):
            msgs.append(d.message)
            (d.accept() if (answers.pop(0) if answers else "dismiss") == "accept" else d.dismiss())
        p.on("dialog", on_dlg)
        p.goto("%s/meetings/%d" % (BASE, B), wait_until="domcontentloaded")
        p.wait_for_timeout(1500)
        bx = box(p)
        ok("대표에게도 상자가 맨 위에(고칠 수 있는 사람)", bx.get("shown") and bx.get("first") == "recResume", bx)
        ses0 = rec(p, B)
        ok("서버 = 남의 녹음(mine=false)", ses0.get("state") == "recording" and ses0.get("mine") is False, ses0)
        p.locator("#recResumeBtn").click()
        p.wait_for_timeout(1200)
        ok("🔴 묻는다", len(msgs) == 1 and "다른 사람이 시작한 녹음" in msgs[0], msgs)
        ok("묻는 글 = 그쪽 녹음이 멈춘다고 알림", bool(msgs) and "그쪽 녹음은 멈추고" in msgs[0], msgs[:1])
        ok("취소 → 녹음 안 켜짐", not rec_on(p))
        ok("취소 → 상자 그대로", box(p).get("shown"))
        s = rec(p, B)
        ok("취소 → 서버 그대로(남의 녹음 · 40초)", s.get("state") == "recording" and s.get("secs") == 40 and s.get("pending") == 0, s)
        p.locator("#recResumeBtn").click()
        p.wait_for_timeout(2500)
        ok("두 번째 확인 → 녹음 켜짐", len(msgs) == 2 and rec_on(p), msgs)
        s = rec(p, B)
        ok("확인 → 서버 새 녹음(남의 조각은 보관)", s.get("state") == "recording" and s.get("pending") == 1 and s.get("mine") is True, s)
        p.locator("#recBtn").click()
        ok("끝내면 두 조각 글자", wait_body(p, "[가짜 변환]", 2), body_text(p)[:120])
        c.close()

        # ══════════ ③ 대표가 남의 녹음 「끝내고 정리」 — 묻기 ══════════
        print("\n■ ③ 대표가 남의 녹음 「⏹ 녹음 끝내고 정리」 — 한 번 묻는다", flush=True)
        K = MIDS["K"]
        c = ctx(br, UA_IOS, True, CEO)
        p = c.new_page(); p.on("pageerror", lambda e: errs.append("③" + str(e)))
        answers, msgs = ["dismiss", "accept"], []
        p.on("dialog", on_dlg)
        p.goto("%s/meetings/%d" % (BASE, K), wait_until="domcontentloaded")
        p.wait_for_timeout(1500)
        p.locator("#recFinishBtn").click()
        p.wait_for_timeout(1200)
        ok("묻는다(끝내기)", len(msgs) == 1 and "정리를 시작" in msgs[0], msgs)
        s = rec(p, K)
        ok("취소 → 서버 그대로 녹음 중", s.get("state") == "recording", s)
        p.locator("#recFinishBtn").click()
        ok("확인 → 끝내고 자동 정리(글자 1개)", wait_body(p, "[가짜 변환]", 1), body_text(p)[:100])
        s = rec(p, K)
        ok("확인 → 서버 녹음 끝", s.get("state") != "recording", s)
        ok("상자 치워짐", not box(p).get("shown"))
        c.close()

        # ══════════ ④ 안드로이드 · 이어서 녹음 → 녹음기로 넘기기 ══════════
        print("\n■ ④ 안드로이드 · 「🎙 이어서 녹음」 → 녹음기로 넘기기", flush=True)
        C = MIDS["C"]
        c = ctx(br, UA_AND, True, CEO)
        p = c.new_page(); p.on("pageerror", lambda e: errs.append("④" + str(e)))
        dlg = []
        p.on("dialog", lambda d: (dlg.append(d.message), d.dismiss()))
        p.goto("%s/meetings/%d" % (BASE, C), wait_until="domcontentloaded")
        p.wait_for_timeout(1500)
        bx = box(p)
        ok("안드로이드도 상자가 첫 화면 맨 위", bx.get("first") == "recResume" and bx.get("bottom", 99999) <= VH, bx)
        p.locator("#recResumeBtn").click()
        p.wait_for_timeout(2500)
        ok("본인 녹음 = 묻지 않음", not dlg, dlg)
        ok("녹음 켜짐", rec_on(p))
        ok("「📱 이 회의, 휴대폰 녹음기로 녹음하시겠어요?」 상자", p.locator("#recPhoneLead").is_visible()
           and "녹음기로 녹음하시겠어요" in p.locator("#recPhoneLeadTtl").inner_text(), p.locator("#recPhoneLeadTtl").inner_text())
        ok("녹음기 단추가 그 상자 안에", p.evaluate("() => !!document.querySelector('#recPhoneLeadSlot #recPhoneRecWrap')"))
        ld = p.evaluate("() => { const r=document.getElementById('recPhoneLead').getBoundingClientRect(); return {top:Math.round(r.top), bottom:Math.round(r.bottom)}; }")
        ok("🔴 그 상자가 첫 화면에(녹음 띠가 붙은 뒤에도)", 0 <= ld["top"] and ld["bottom"] <= VH, ld)
        bw = p.evaluate("() => { const r=document.getElementById('recPhoneRecWrap').getBoundingClientRect(); return {top:Math.round(r.top), bottom:Math.round(r.bottom)}; }")
        ok("녹음기 단추가 첫 화면에", 0 <= bw["top"] and bw["bottom"] <= VH, bw)
        p.wait_for_timeout(11000)
        with p.expect_file_chooser() as fc:
            p.locator("#recPhoneRecWrap").click()
        ok("녹음기가 열린다", fc.value is not None)
        p.wait_for_timeout(2500)
        s = rec(p, C)
        ok("넘기면 이 화면 녹음은 멈춘다", not rec_on(p))
        ok("서버 = 녹음 끝 · 조각 2개 보관(끊긴 것 + 이어서 녹음)", s.get("state") != "recording" and s.get("pending") == 2, s)
        p.locator("#recFileCap").set_input_files(WAV)
        ok("녹음기 파일이 오면 세 조각이 글자로", wait_body(p, "[가짜 변환]", 3), body_text(p)[:200])
        nm = names(body_text(p))
        ok("🔴 순서 = 끊긴 조각 → 이어서 녹음 → 녹음기 파일", len(nm) == 3 and nm[0].startswith(old_id(C))
           and nm[1].endswith(".webm") and not nm[1].startswith(old_id(C)) and nm[2].endswith(".wav"), nm)
        c.close()

        # ══════════ ⑤ 안드로이드 · 상자를 두고 녹음기 바로 → 내 녹음 먼저 닫기 ══════════
        print("\n■ ⑤ 안드로이드 · 상자를 두고 「📱 휴대폰 녹음기로 녹음」 바로 (내 녹음)", flush=True)
        G = MIDS["G"]
        c = ctx(br, UA_AND, True, CEO)
        p = c.new_page(); p.on("pageerror", lambda e: errs.append("⑤" + str(e)))
        p.goto("%s/meetings/%d" % (BASE, G), wait_until="domcontentloaded")
        p.wait_for_timeout(1500)
        p.evaluate("() => { document.getElementById('redoTools').open = true; }")
        p.wait_for_timeout(300)
        with p.expect_file_chooser() as fc:
            p.locator("#recPhoneRecWrap").click()
        ok("녹음기가 열린다", fc.value is not None)
        p.wait_for_timeout(2000)
        s = rec(p, G)
        ok("🔴 열려 있던 내 녹음을 먼저 닫았다(끊긴 조각 보관 1개)", s.get("state") != "recording" and s.get("pending") == 1, s)
        ok("상자 치워짐", not box(p).get("shown"))
        p.locator("#recFileCap").set_input_files(WAV)
        ok("🔴 끊긴 조각 + 녹음기 파일 둘 다 글자로", wait_body(p, "[가짜 변환]", 2), body_text(p)[:200])
        nm = names(body_text(p))
        ok("🔴 순서 = 끊긴 조각 → 녹음기 파일", len(nm) == 2 and nm[0].startswith(old_id(G)) and nm[1].endswith(".wav"), nm)
        s = rec(p, G)
        ok("정리 뒤 서버 = 녹음 아님 · 남은 조각 0", s.get("state") != "recording" and s.get("pending") == 0, s)
        c.close()

        # ══════════ ⑥ 안드로이드 · 남의 녹음이 열린 회의에서 녹음기 → 남의 녹음은 안 닫는다 ══════════
        print("\n■ ⑥ 안드로이드 · 남의 녹음이 열린 회의에서 녹음기 — 남의 녹음은 그대로", flush=True)
        G2 = MIDS["G2"]
        c = ctx(br, UA_AND, True, CEO)
        p = c.new_page(); p.on("pageerror", lambda e: errs.append("⑥" + str(e)))
        p.goto("%s/meetings/%d" % (BASE, G2), wait_until="domcontentloaded")
        p.wait_for_timeout(1500)
        p.evaluate("() => { document.getElementById('redoTools').open = true; }")
        with p.expect_file_chooser() as fc:
            p.locator("#recPhoneRecWrap").click()
        p.wait_for_timeout(1500)
        s = rec(p, G2)
        ok("남의 녹음은 닫지 않는다(그대로 녹음 중)", s.get("state") == "recording" and s.get("secs") == 20, s)
        c.close()

        # ══════════ ⑦ PC ══════════
        print("\n■ ⑦ PC — 상자가 본문 맨 위 · 누르면 녹음 칸으로", flush=True)
        E = MIDS["E"]
        c = ctx(br, UA_PC, False, CEO)
        p = c.new_page(); p.on("pageerror", lambda e: errs.append("⑦" + str(e)))
        p.goto("%s/meetings/%d" % (BASE, E), wait_until="domcontentloaded")
        p.wait_for_timeout(1500)
        bx = box(p)
        ok("PC 도 상자가 본문 맨 위", bx.get("first") == "recResume", bx)
        ok("PC 첫 화면에 보인다", bx.get("bottom", 99999) <= 900, bx)
        ok("DOM 에서도 자동 정리 카드·기본 정보보다 앞",
           p.evaluate("() => { const w=[...document.querySelector('.mf-wrap').children]; return w.indexOf(document.getElementById('recResume')) === 0; }"))
        p.locator("#recResumeBtn").click()
        p.wait_for_timeout(2500)
        ok("PC 녹음 켜짐", rec_on(p))
        bn = p.evaluate("() => { const r=document.getElementById('recBanner').getBoundingClientRect(); return {top:Math.round(r.top), bottom:Math.round(r.bottom)}; }")
        ok("PC 녹음 띠가 화면 안(그 칸으로 스크롤)", 0 <= bn["top"] and bn["bottom"] <= 900, bn)
        ok("PC 에선 녹음기 상자 없음", not p.locator("#recPhoneLead").is_visible())
        p.locator("#recBtn").click()
        ok("PC 끝내면 두 조각 글자", wait_body(p, "[가짜 변환]", 2), body_text(p)[:120])
        c.close()

        # ══════════ ⑧ 본인 「끝내고 정리」 ══════════
        print("\n■ ⑧ 본인 「⏹ 녹음 끝내고 정리」 — 묻지 않고", flush=True)
        F = MIDS["F"]
        c = ctx(br, UA_IOS, True, CEO)
        p = c.new_page(); p.on("pageerror", lambda e: errs.append("⑧" + str(e)))
        dlg = []
        p.on("dialog", lambda d: (dlg.append(d.message), d.dismiss()))
        p.goto("%s/meetings/%d" % (BASE, F), wait_until="domcontentloaded")
        p.wait_for_timeout(1500)
        p.locator("#recFinishBtn").click()
        ok("끝내고 자동 정리(글자 1개)", wait_body(p, "[가짜 변환]", 1), body_text(p)[:100])
        ok("본인 = 묻지 않음", not dlg, dlg)
        ok("상자 치워짐", not box(p).get("shown"))
        c.close()

        # ══════════ ⑨ 자동 녹음 착지 + 열린 녹음 ══════════
        print("\n■ ⑨ 이음 「▶ 회의 시작」 착지(?autorec=1) + 열린 녹음 — 녹음이 켜지면 상자 치움", flush=True)
        H = MIDS["H"]
        c = ctx(br, UA_IOS, True, CEO)
        p = c.new_page(); p.on("pageerror", lambda e: errs.append("⑨" + str(e)))
        p.goto("%s/meetings/%d?autorec=1" % (BASE, H), wait_until="domcontentloaded")
        p.wait_for_timeout(4000)
        ok("아이폰 착지 = 자동 녹음 켜짐(지금 그대로)", rec_on(p))
        ok("🔴 녹음이 켜졌으니 상자는 치워짐(두 번째 녹음기 방지)", not box(p).get("shown"), box(p))
        s = rec(p, H)
        ok("서버 = 새 녹음 · 끊긴 조각 보관", s.get("state") == "recording" and s.get("pending") == 1, s)
        c.close()

        # ══════════ ⑩ 녹음 없는 회의 ══════════
        print("\n■ ⑩ 녹음 없는 회의 — 상자 없음 · 칸 순서 그대로", flush=True)
        N = MIDS["N"]
        c = ctx(br, UA_IOS, True, CEO)
        p = c.new_page(); p.on("pageerror", lambda e: errs.append("⑩" + str(e)))
        p.goto("%s/meetings/%d" % (BASE, N), wait_until="domcontentloaded")
        p.wait_for_timeout(1200)
        ok("상자 없음", not box(p).get("exists"))
        fst = p.evaluate("""() => { const w=document.querySelector('.mf-wrap');
            const k=[...w.children].filter(x=>getComputedStyle(x).display!=='none'&&x.offsetHeight>0);
            k.sort((a,c)=>a.getBoundingClientRect().top-c.getBoundingClientRect().top); return k[0] ? (k[0].id||k[0].className) : ''; }""")
        ok("휴대폰 첫 칸 = 회의록 정리(지금 그대로)", fst == "secSummary", fst)
        c.close()

        # ══════════ ⑪ 마이크 막힘 ══════════
        print("\n■ ⑪ 마이크를 못 열면 상자를 되살린다", flush=True)
        D = MIDS["D"]
        br2 = pw.chromium.launch(channel="chrome", headless=True)   # 가짜 마이크 없음
        c = br2.new_context(service_workers="block", user_agent=UA_IOS, viewport={"width": 390, "height": VH},
                            is_mobile=True, has_touch=True)
        c.add_cookies([{"name": "tuser", "value": str(CEO), "url": BASE}])
        c.add_init_script(HIDE)
        c.add_init_script("navigator.mediaDevices.getUserMedia = () => Promise.reject(Object.assign(new Error('Permission denied'), {name:'NotAllowedError'}));")
        p = c.new_page(); p.on("pageerror", lambda e: errs.append("⑪" + str(e)))
        p.goto("%s/meetings/%d" % (BASE, D), wait_until="domcontentloaded")
        p.wait_for_timeout(1200)
        p.locator("#recResumeBtn").click()
        p.wait_for_timeout(2000)
        ok("녹음 안 켜짐(마이크 막힘)", not rec_on(p))
        ok("🔴 상자가 되살아난다(끝내기·다시 누르기)", box(p).get("shown"), box(p))
        s = rec(p, D)
        ok("서버 그대로 녹음 중(15초)", s.get("state") == "recording" and s.get("secs") == 15, s)
        c.close(); br2.close()

        # ══════════ ⑫ 아이폰 안내 ══════════
        print("\n■ ⑫ 아이폰 안내 — 실수로 닫았으면 카드 「📋 회의록 열기」", flush=True)
        c = ctx(br, UA_IOS, True, CEO)
        p = c.new_page(); p.on("pageerror", lambda e: errs.append("⑫" + str(e)))
        p.goto("%s/meetings/%d" % (BASE, N), wait_until="domcontentloaded")
        p.wait_for_timeout(1000)
        t = p.evaluate("() => (document.getElementById('recPlatNote')||{}).textContent || ''")
        ok("아이폰 안내에 「실수로 이 창을 닫았으면」", "실수로 이 창을 닫았으면" in t and "📋 회의록 열기" in t and "🎙 이어서 녹음" in t, t[-120:])
        ok("기존 안내(다른 앱으로 넘어가면 녹음 안 됨)는 그대로", "그동안은 녹음되지 않습니다" in t)
        c.close()
        c = ctx(br, UA_AND, True, CEO)
        p = c.new_page()
        p.goto("%s/meetings/%d" % (BASE, N), wait_until="domcontentloaded")
        p.wait_for_timeout(1000)
        t = p.evaluate("() => (document.getElementById('recPlatNote')||{}).textContent || ''")
        ok("안드로이드 안내는 그대로(녹음기 안내)", "휴대폰 녹음기로 녹음" in t and "실수로 이 창을" not in t, t[:80])
        c.close()

        ok("화면 스크립트 오류 없음", not errs, errs[:3])
        br.close()

    print("\n" + "=" * 64)
    print("합계: 통과 %d · 실패 %d%s" % (len(OK), len(NG), "  (고치기 전 파일)" if BASE_MODE else ""))
    for n in NG:
        print("  ❌ " + n)
    sys.exit(1 if NG else 0)


main()
