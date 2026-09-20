# -*- coding: utf-8 -*-
"""녹음 중 뒤로 가기 = 「회의를 끝낼까요?」 · 다른 앱 경고 · 다른 곳에서 끝냄 — 실제 크롬 화면 시험 (z1114)
가짜 마이크(크롬 --use-fake-device-for-media-stream). 사용: py -3.12 ui_back.py <seed_rec.json 폴더>"""
import io
import json
import os
import sys
from urllib.parse import quote
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
SEED_DIR = sys.argv[1]
seed = json.load(io.open(os.path.join(SEED_DIR, "seed_rec.json"), encoding="utf-8"))
BASE = "http://localhost:%d" % seed["port"]
M0, M1, M2, M3 = seed["mids"][:4]
HIDE = ("document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style');"
        "s.textContent = '#worksInstallHint{display:none !important}'; document.head.appendChild(s); });")
PHONE_UA = ("Mozilla/5.0 (Linux; Android 14; SM-S921N) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/153.0.0.0 Mobile Safari/537.36")
res, errs, bad_resp = [], [], []


def ok(name, cond, extra=""):
    res.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (" · " + str(extra)[:200] if extra != "" else ""), flush=True)



IOS_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
          "CriOS/153.0.0.0 Mobile/15E148 Safari/604.1")

def new_ctx(b, phone, ua=None):
    kw = (dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
               user_agent=ua or PHONE_UA) if phone else dict(viewport={"width": 1280, "height": 900}))
    ctx = b.new_context(service_workers="block", permissions=["microphone"], **kw)
    ctx.add_init_script(HIDE)
    ctx.on("page", lambda pg: (pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None),
                               pg.on("pageerror", lambda e: errs.append("pageerror " + str(e))),
                               pg.on("response", lambda r: bad_resp.append((r.status, r.url.replace(BASE, "")))
                                     if r.status >= 400 else None)))
    return ctx


def back(pg, wait=700):
    try:
        pg.go_back(timeout=1800)
    except Exception:
        pass
    try:
        pg.wait_for_timeout(wait)
    except Exception:
        pass                                # 창이 닫힌 경우(이음이 연 창) — 그게 기대한 결과일 수 있다


def recording(pg):
    return pg.evaluate("() => { const b = document.getElementById('recBtn'); return !!(b && b.dataset.on === '1'); }")


def dialog_shown(pg):
    return pg.evaluate("() => { const d = document.getElementById('recBackAsk'); return !!(d && !d.hidden); }")


def guard(pg):
    return pg.evaluate("() => ({len: history.length, guard: !!(history.state && history.state.knkRecGuard)})")


def hide_for(pg, ms):
    pg.evaluate("() => { Object.defineProperty(document, 'visibilityState', {configurable:true, get:() => 'hidden'});"
                " document.dispatchEvent(new Event('visibilitychange')); }")
    pg.wait_for_timeout(ms)
    pg.evaluate("() => { Object.defineProperty(document, 'visibilityState', {configurable:true, get:() => 'visible'});"
                " document.dispatchEvent(new Event('visibilitychange')); }")
    pg.wait_for_timeout(300)


def start_rec(pg):
    pg.wait_for_selector("#redoTools")
    pg.evaluate("() => { const d = document.getElementById('redoTools'); if (d) d.open = true; }")
    pg.click("#recBtn")
    pg.wait_for_timeout(2500)


def wait_body(pg, ms=15000):
    try:
        pg.wait_for_function("() => { const t = document.getElementById('mtgBody'); return t && t.value.indexOf('[가짜 변환]') >= 0; }",
                             timeout=ms)
        return True
    except Exception:
        return False


with sync_playwright() as p:
    B = p.chromium.launch(channel="chrome", headless=True, args=["--use-fake-device-for-media-stream"])

    # ── A. PC · 목록 → 회의(화면 전환) · 녹음 → 뒤로 가기 ─────────────────────────
    print("\n■ A. PC — 목록에서 들어온 회의 · 녹음 중 뒤로 가기")
    ctx = new_ctx(B, phone=False)
    pg = ctx.new_page()
    pg.goto(BASE + "/meetings", wait_until="domcontentloaded")
    pg.wait_for_timeout(400)
    pg.click(f'a.mtg-card[href="/meetings/{M0}"]')
    pg.wait_for_url(f"**/meetings/{M0}")
    pg.wait_for_timeout(500)
    start_rec(pg)
    ok("A 녹음 시작", recording(pg))
    g = guard(pg)
    ok("A 녹음 시작 = 되돌아갈 칸 생김", g["guard"], g)
    ok("A PC 에는 휴대폰 안내 줄 없음", pg.evaluate("() => { const e = document.getElementById('recPhoneHint'); return !e || e.hidden; }"))
    back(pg)
    ok("A 뒤로 가기 → 「회의를 끝낼까요?」 창", dialog_shown(pg))
    ok("A 뒤로 가기 → 화면·주소 그대로", pg.url.endswith(f"/meetings/{M0}") and pg.query_selector("#mtgTags") is not None, pg.url)
    ok("A 뒤로 가기 → 녹음은 계속", recording(pg))
    txt = pg.inner_text("#recBackAsk") if dialog_shown(pg) else ""
    ok("A 창 글: 회의를 끝낼까요 · 끝내고 정리 · 계속 녹음", "회의를 끝낼까요" in txt and "끝내고 정리" in txt and "계속 녹음" in txt, txt[:80])
    pg.click("#rbaKeep")
    pg.wait_for_timeout(300)
    ok("A 「계속 녹음」 → 창 닫히고 녹음 계속", not dialog_shown(pg) and recording(pg))
    back(pg)
    ok("A 다시 뒤로 가기 → 또 묻는다", dialog_shown(pg) and recording(pg))
    pg.click("#rbaEnd")
    pg.wait_for_timeout(800)
    ok("A 「회의 끝내고 정리」 → 녹음 멈춤", not recording(pg))
    ok("A 끝낸 뒤 음성→글자·정리까지", wait_body(pg))
    back(pg, 1200)
    ok("A 끝난 뒤 뒤로 가기 한 번 = 목록으로(되돌아갈 칸은 건너뜀)",
       pg.url.rstrip("/").endswith("/meetings") and pg.query_selector("#mtgTags") is None, pg.url)
    # 고친 글이 저장 전이면 예전 확인창이 먼저(건너뛰기보다 앞) — 이미 글이 있는 회의는 정리 끝 신호가 없어 새 회의로 시험
    newid = pg.evaluate("""async () => { const r = await fetch('/api/meeting', {method:'POST',
        headers:{'Content-Type':'application/json'}, body: JSON.stringify({title:'[시험] 저장 전 뒤로 가기', meeting_date:'2026-09-18', visibility:'all'})});
        return (await r.json()).id; }""")
    pg.goto(BASE + f"/meetings/{newid}", wait_until="domcontentloaded")
    pg.wait_for_timeout(400)
    start_rec(pg)
    with pg.expect_response(lambda r: r.url.endswith(f"/api/meeting/{newid}/extract"), timeout=20000):
        pg.click("#recBtn")                 # ⏹ 종료 → 음성→글자 → AI 정리(extract)까지 기다린다
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(1500)
    pg.wait_for_selector("#mtgTags")
    pg.fill("#mtgTags", "저장 전 시험")
    seen = []
    plan = ["dismiss"]

    def on_dlg(d):
        seen.append((d.type, d.message[:40]))
        (d.dismiss() if (plan and plan.pop(0) == "dismiss") else d.accept())
    pg.on("dialog", on_dlg)
    back(pg)
    ok("A 저장 전 글 + 뒤로 가기 → 예전 확인창이 뜬다", any(t == "confirm" for t, _ in seen), seen)
    ok("A 확인창 취소 → 그대로 머묾", pg.url.endswith(f"/meetings/{newid}") and pg.input_value("#mtgTags") == "저장 전 시험", pg.url)
    plan[:] = ["accept"]
    back(pg, 1200)
    ok("A 확인 → 나감(되돌아갈 칸까지 한 번에 건너뜀)", not pg.url.endswith(f"/meetings/{newid}"), pg.url)
    # 되돌아갈 칸 없이 들어온 경우(goto)는 첫 칸이라 닫을 수 없는 창 → 나가기로 하면 원래대로 이동
    ctx.close()

    # ── B. 휴대폰 · 이음처럼 새 창으로 연 회의 ─────────────────────────────────────
    print("\n■ B. 휴대폰 — 이음이 연 창 · 뒤로 가기 · 다른 앱 경고 · 끝나면 창 닫힘")
    ctx = new_ctx(B, phone=True)
    op = ctx.new_page()
    op.goto(BASE + "/static/_probe_opener.html?to=" + quote(f"/meetings/{M1}"), wait_until="domcontentloaded")
    with ctx.expect_page() as pi:
        op.click("#go")
    pp = pi.value
    pp.wait_for_url(f"**/meetings/{M1}", timeout=15000)
    pp.wait_for_timeout(600)
    start_rec(pp)
    ok("B 녹음 시작", recording(pp))
    ok("B 되돌아갈 칸 생김", guard(pp)["guard"], guard(pp))
    hint = pp.evaluate("() => { const e = document.getElementById('recPhoneHint'); return e && !e.hidden ? e.textContent : ''; }")
    ok("B 휴대폰 안내 줄: 이 화면을 켜 두세요 · 다른 앱이면 녹음 안 됨", "켠 채로" in hint and "다른 앱" in hint, hint)
    hide_for(pp, 4200)
    st = pp.inner_text("#recStatus")
    ok("B 다른 앱 4초 뒤 돌아옴 → 정확한 경고", "휴대폰이 마이크를 막아" in st and "초 동안" in st, st[:90])
    back(pp)
    ok("B 뒤로 가기 → 창이 닫히지 않고 「회의를 끝낼까요?」", (not pp.is_closed()) and dialog_shown(pp))
    ok("B 창 버튼 크기(누르기 쉬움) · 화면 안",
       pp.evaluate("() => { const b = document.getElementById('rbaEnd').getBoundingClientRect(); "
                   "return b.height >= 44 && b.right <= document.documentElement.clientWidth; }"))
    pp.click("#rbaEnd")
    pp.wait_for_timeout(800)
    ok("B 끝내고 정리 → 녹음 멈춤", not recording(pp))
    ok("B 음성→글자·정리까지", wait_body(pp))
    back(pp, 1500)
    ok("B 끝난 뒤 뒤로 가기 = 창 닫힘(이음으로 돌아감)", pp.is_closed())
    ctx.close()

    # ── C. 회의 알림 자동 녹음(?autorec=1) — 아직 한 번도 안 누른 화면 ───────────────
    print("\n■ C. 자동 녹음 — 누르기 전엔 칸 없음 · 처음 누르면 생김")
    # z1118: 안드로이드는 녹음기가 기본이라 '누른 적 없이 자동 녹음'이 더는 없다 → 그 상황이 남는 아이폰으로 본다
    ctx = new_ctx(B, phone=True, ua=IOS_UA)
    op = ctx.new_page()
    op.goto(BASE + "/static/_probe_opener.html?to=" + quote(f"/meetings/{M2}?autorec=1"), wait_until="domcontentloaded")
    with ctx.expect_page() as pi:
        op.click("#go")
    pp = pi.value
    pp.wait_for_url(f"**/meetings/{M2}**", timeout=15000)
    pp.wait_for_timeout(3500)
    ok("C 자동 녹음 시작됨", recording(pp))
    g = guard(pp)
    ok("C 누르기 전 — 되돌아갈 칸을 아직 만들지 않음(크롬 규칙)", not g["guard"], g)
    pp.click("#recBanner")                  # 아무 데나 한 번 누름
    pp.wait_for_timeout(400)
    g = guard(pp)
    ok("C 처음 누른 순간 — 되돌아갈 칸 생김", g["guard"], g)
    back(pp)
    ok("C 그 뒤 뒤로 가기 → 「회의를 끝낼까요?」", (not pp.is_closed()) and dialog_shown(pp))
    pp.click("#rbaEnd")
    pp.wait_for_timeout(800)
    ok("C 끝내고 정리 → 녹음 멈춤", not recording(pp))
    wait_body(pp)
    ctx.close()

    # ── D. 다른 곳에서 이 녹음을 마침(목록·PC) → 이 화면 녹음 멈춤 · 두 번 안 올림 ────
    print("\n■ D. 다른 곳에서 새로 시작/마침 → 이 화면은 멈추고 올리지 않음")
    ctx = new_ctx(B, phone=False)
    pg = ctx.new_page()
    ups = []
    pg.on("request", lambda r: ups.append(r.url.replace(BASE, "")) if (r.method == "POST" and r.url.endswith("/audio")) else None)
    pg.goto(BASE + f"/meetings/{M3}", wait_until="domcontentloaded")
    pg.wait_for_timeout(400)
    start_rec(pg)
    ok("D 녹음 시작", recording(pg))
    pg.evaluate("""async (id) => { await fetch('/api/meeting/'+id+'/rec-start', {method:'POST',
                   headers:{'Content-Type':'application/json'}, body: JSON.stringify({ext:'.webm'})}); }""", M3)
    hide_for(pg, 1200)                      # 조각을 하나 내보내게 → 서버가 stale 로 거절
    pg.wait_for_timeout(1500)
    ok("D 이 화면 녹음 멈춤", not recording(pg))
    st = pg.inner_text("#recStatus")
    ok("D 사람말 안내", "다른 곳에서 이 녹음을" in st, st[:80])
    pg.wait_for_timeout(1500)
    ok("D 녹음 전체를 다시 올리지 않음(겹침 없음)", not ups, ups)
    pg.evaluate("async (id) => { await fetch('/api/meeting/'+id+'/rec-finish', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'}); }", M3)
    ctx.close()
    B.close()

print("실패 응답(주소):", bad_resp)
exp = [(st, u) for st, u in bad_resp if st == 409 and "/rec-chunk" in u]          # D 에서 일부러 만든 거절
unexp = [(st, u) for st, u in bad_resp if (st, u) not in exp]
ok("예상 밖 실패 응답 없음", not unexp, unexp)
bad = [e for e in errs if "favicon" not in e and "sw.js" not in e and "Failed to load resource" not in e]
ok("화면 스크립트 오류 없음", not bad, bad[:3])
print("\n" + "=" * 68)
print("합계: 통과 %d · 실패 %d" % (sum(1 for _, c in res if c), sum(1 for _, c in res if not c)))
for n, c in res:
    if not c:
        print("  - 실패:", n)
print("=" * 68)
sys.exit(1 if any(not c for _, c in res) else 0)
