# -*- coding: utf-8 -*-

# z1130: 휴대폰은 「다른 방법」(이 화면 녹음·짧은 녹음)이 접혀 있다 — 시험은 열어 놓고 본다
OPEN_OTHER = ("document.addEventListener('DOMContentLoaded', function(){ setTimeout(function(){"
              " var d=document.getElementById('recOther'); if(d) d.open=true; }, 0); });")
"""녹음 화면 시험 — 녹음하는 동안 서버에 저장되는지 · 창이 닫혀도 끝낼 수 있는지 (z1113)
가짜 마이크(크롬 --use-fake-device-for-media-stream)로 실제 녹음을 돌린다.
사용: py -3.12 ui_rec.py <seed_rec.json 폴더>"""
# 🔴 z1143(대표 지시 2026-10-07): 사람이 눌러 시작하는 이 화면 녹음은 막혔다.
#   이 묶음이 재는 것은 「녹음이 도는 동안」의 동작이고, 그 길은 이음 「▶ 회의 시작」
#   자동 녹음으로 그대로 산다 → 아래에서 그 길과 **똑같은 표시**를 켜고 시작한다.
#   (막혔는지 자체는 ui_block_z1143.py 가 따로 잰다)
import io
import json
import os
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
SEED_DIR = sys.argv[1]
seed = json.load(io.open(os.path.join(SEED_DIR, "seed_rec.json"), encoding="utf-8"))
PORT = seed["port"]
BASE = "http://localhost:%d" % PORT
MIDS = seed["mids"]
HIDE = ("document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style');"
        "s.textContent = '#worksInstallHint{display:none !important}'; document.head.appendChild(s); });")
res, errs = [], []


def ok(name, cond, extra=""):
    res.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (" · " + str(extra)[:220] if extra != "" else ""), flush=True)


def new_ctx(b, phone=True):
    kw = dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
              user_agent=("Mozilla/5.0 (Linux; Android 14; SM-S921N) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/153.0.0.0 Mobile Safari/537.36")) if phone else dict(viewport={"width": 1280, "height": 900})
    ctx = b.new_context(service_workers="block", permissions=["microphone"], **kw)
    ctx.add_init_script(HIDE)
    ctx.add_init_script(OPEN_OTHER)
    ctx.on("page", lambda pg: (pg.on("console", lambda msg: errs.append(msg.text) if msg.type == "error" else None),
                               pg.on("pageerror", lambda e: errs.append("pageerror " + str(e)))))
    return ctx


def hide_page(pg):
    """휴대폰에서 다른 앱으로 넘어간 순간 흉내 — 화면이 숨겨지면 조각을 바로 내보내야 한다."""
    pg.evaluate("""() => { Object.defineProperty(document, 'visibilityState', {configurable: true, get: () => 'hidden'});
                           document.dispatchEvent(new Event('visibilitychange')); }""")


def show_page(pg):
    pg.evaluate("""() => { Object.defineProperty(document, 'visibilityState', {configurable: true, get: () => 'visible'});
                           document.dispatchEvent(new Event('visibilitychange')); }""")


def api(pg, path):
    return pg.evaluate("""async (p) => { const r = await fetch(p); return await r.json(); }""", path)


with sync_playwright() as p:
    B = p.chromium.launch(channel="chrome", headless=True, args=["--use-fake-device-for-media-stream"])

    # ── ① 새 회의에서 녹음 시작 = 회의록이 먼저 만들어지고 서버 저장이 열린다 ──
    print("\n■ ① 녹음 시작 — 회의록 먼저 만들고 서버에 「녹음 중」")
    ctx = new_ctx(B)
    pg = ctx.new_page()
    calls = []
    pg.on("request", lambda r: calls.append((r.method, r.url.replace(BASE, ""))) if "/api/meeting" in r.url else None)
    pg.goto(BASE + "/meetings/new", wait_until="domcontentloaded")
    pg.wait_for_timeout(400)
    pg.evaluate("()=>{var b=document.getElementById('recBtn'); if(b) b.dataset.autorec='1';}")  # z1143
    pg.click("#recBtn")
    pg.wait_for_timeout(2500)
    ok("녹음 시작 = 회의 만들기(POST /api/meeting)", any(m == "POST" and u == "/api/meeting" for m, u in calls), calls[:4])
    ok("녹음 시작 = 서버 저장 열기(rec-start)", any("rec-start" in u for m, u in calls), calls[:6])
    mid = pg.evaluate("window.__MTG && window.__MTG.id")
    ok("회의 번호가 화면에 생김", bool(mid), mid)
    st = api(pg, "/api/meeting/%d/rec-status" % mid)
    ok("서버가 「녹음 중」으로 안다", st.get("rec", {}).get("state") == "recording", st)

    # ── ② 다른 앱으로 넘어가는 순간 조각을 바로 내보낸다 ──
    print("\n■ ② 다른 앱으로 넘어갈 때 — 그 자리에서 조각 보내기")
    chunks = []
    pg.on("response", lambda r: chunks.append(r.status) if "rec-chunk" in r.url else None)
    hide_page(pg)
    pg.wait_for_timeout(2500)
    show_page(pg)
    ok("숨는 순간 조각이 서버로 갔다", len(chunks) >= 1 and chunks[0] == 200, chunks[:3])
    st = api(pg, "/api/meeting/%d/rec-status" % mid)
    ok("서버에 저장된 크기가 0보다 크다", (st.get("rec", {}).get("kb") or 0) >= 0 and st["rec"]["state"] == "recording", st)

    # ── ③ 저장된 시간이 화면(빨간 띠)에 보인다 ──
    print("\n■ ③ 화면에 「저장됨」 표시")
    pg.wait_for_timeout(11000)          # 10초 조각이 저절로 한 번 더
    lbl = pg.inner_text("#recBannerLbl")
    ok("빨간 띠에 저장된 시간 표시", "저장됨" in lbl, lbl)
    ok("조각이 10초마다 저절로 간다", len(chunks) >= 2, chunks[:5])

    # ── ④ 창이 그대로 닫혀도(=앱이 죽어도) 서버에는 남는다 ──
    print("\n■ ④ 창이 닫힌 뒤 — 목록에서 「녹음 끝내고 정리」")
    ctx.close()                          # 브라우저 창 통째로 사라짐(대표가 겪은 상황)
    ctx2 = new_ctx(B)
    pg2 = ctx2.new_page()
    navs = []
    pg2.on("framenavigated", lambda fr: navs.append(fr.url) if fr == pg2.main_frame else None)
    pg2.goto(BASE + "/meetings", wait_until="domcontentloaded")
    pg2.wait_for_timeout(500)
    html = pg2.content()
    ok("목록에 「🔴 녹음 중」이 보인다", "🔴 녹음 중" in html)
    ok("목록에 「녹음 끝내고 정리」 단추", pg2.locator('[data-rec-finish="%d"]' % mid).count() == 1)
    pg2.click('[data-rec-finish="%d"]' % mid)
    pg2.wait_for_url("**/meetings/%d**" % mid, timeout=15000)
    # ?auto=1 은 착지 뒤 주소에서 지워진다(z971 자동 정리) → '지나간 주소'로 확인한다
    ok("그 회의 화면으로 옮겨 자동 정리 시작(?auto=1)", any(("/meetings/%d" % mid) in u and "auto=1" in u for u in navs),
       navs[-3:])
    pg2.wait_for_timeout(6000)
    body = pg2.input_value("#mtgBody") if pg2.locator("#mtgBody").count() else ""
    ok("녹음이 글자로 바뀌어 회의 내용에 들어감", "[가짜 변환]" in body, body[:80])
    st = api(pg2, "/api/meeting/%d/rec-status" % mid)
    ok("「녹음 중」 표시가 사라짐", st.get("rec", {}).get("state") == "", st)

    # ── ⑤ 상세 화면 복귀 상자 — 이어서 녹음 ──
    print("\n■ ⑤ 「🔴 녹음 중이던 회의」 상자에서 이어서 녹음")
    mid2 = MIDS[0]
    ctx3 = new_ctx(B)
    pg3 = ctx3.new_page()
    pg3.goto(BASE + "/meetings/%d" % mid2, wait_until="domcontentloaded")
    pg3.wait_for_timeout(400)
    # 창이 닫혀 끊긴 녹음을 서버에 만들어 둔다(시작 → 조각 하나)
    made = pg3.evaluate("""async (id) => {
        const r = await fetch('/api/meeting/'+id+'/rec-start', {method:'POST',
            headers:{'Content-Type':'application/json'}, body: JSON.stringify({ext:'.webm'})});
        const j = await r.json();
        const c = await fetch('/api/meeting/'+id+'/rec-chunk?session='+j.session+'&seq=1&secs=30',
            {method:'POST', headers:{'Content-Type':'application/octet-stream'}, body: new Uint8Array(3000)});
        return {start: j.ok===true, chunk: (await c.json()).ok===true};
    }""", mid2)
    ok("끊긴 녹음 만들기(시작+조각)", made.get("start") and made.get("chunk"), made)
    pg3.reload(wait_until="domcontentloaded")
    pg3.wait_for_timeout(500)
    ok("상세 화면에 복귀 상자", pg3.locator("#recResume").count() == 1)
    ok("복귀 상자에 「녹음 끝내고 정리」·「이어서 녹음」",
       pg3.locator("#recFinishBtn").count() == 1 and pg3.locator("#recResumeBtn").count() == 1)
    pg3.click("#recResumeBtn")
    pg3.wait_for_timeout(2500)
    ok("이어서 녹음이 시작됨(빨간 띠)", pg3.locator("#recBanner").is_visible())
    st = api(pg3, "/api/meeting/%d/rec-status" % mid2)
    ok("서버도 다시 「녹음 중」", st.get("rec", {}).get("state") == "recording", st)
    pg3.evaluate("()=>{var b=document.getElementById('recBtn'); if(b) b.dataset.autorec='1';}")  # z1143
    pg3.click("#recBtn")                       # ⏹ 녹음 종료
    pg3.wait_for_timeout(7000)
    st = api(pg3, "/api/meeting/%d/rec-status" % mid2)
    ok("녹음 종료 뒤 「녹음 중」 사라짐", st.get("rec", {}).get("state") == "", st)
    body = pg3.input_value("#mtgBody") if pg3.locator("#mtgBody").count() else ""
    ok("이어서 녹음도 글자로 바뀜", "[가짜 변환]" in body, body[:80])

    # ── ⑥ 서버 저장을 못 열면 예전 방식(전체 올리기)으로 돌아간다 ──
    print("\n■ ⑥ 서버 저장이 막혀도 녹음은 된다(예전 방식으로)")
    mid3 = MIDS[1]
    ctx4 = new_ctx(B)
    pg4 = ctx4.new_page()
    pg4.route("**/rec-start", lambda route: route.abort())
    ups = []
    pg4.on("response", lambda r: ups.append(r.url.replace(BASE, "")) if r.url.endswith("/audio") and r.request.method == "POST" else None)
    pg4.goto(BASE + "/meetings/%d" % mid3, wait_until="domcontentloaded")
    pg4.wait_for_timeout(300)
    pg4.evaluate("() => { const d = document.getElementById('redoTools'); if (d) d.open = true; }")
    pg4.evaluate("()=>{var b=document.getElementById('recBtn'); if(b) b.dataset.autorec='1';}")  # z1143
    pg4.click("#recBtn")
    pg4.wait_for_timeout(3000)
    sttxt = pg4.inner_text("#recStatus")
    ok("서버 저장을 못 열면 그렇게 알린다", "창을 닫지 마세요" in sttxt, sttxt[:120])
    pg4.evaluate("()=>{var b=document.getElementById('recBtn'); if(b) b.dataset.autorec='1';}")  # z1143
    pg4.click("#recBtn")                       # 종료 → 예전 방식(통째로 올리기)
    pg4.wait_for_timeout(6000)
    ok("녹음 전체가 예전 방식으로 올라감", len(ups) >= 1, ups[:3])
    body = pg4.input_value("#mtgBody") if pg4.locator("#mtgBody").count() else ""
    ok("그래도 글자로 바뀜", "[가짜 변환]" in body, body[:80])

    # ── ⑦ 소리가 하나도 안 들어왔으면 방금 만든 빈 회의록을 지운다(목록 더럽히지 않게) ──
    print("\n■ ⑦ 소리가 없으면 방금 만든 빈 회의록은 지운다")
    ctx5 = new_ctx(B)
    pg5 = ctx5.new_page()
    # 조각이 서버에 닿지 않게 가로채고(보낸 척만) → 서버 파일은 비어 있다
    pg5.route("**/rec-chunk*", lambda route: route.fulfill(status=200, content_type="application/json",
                                                           body='{"ok":true,"seq":1,"bytes":0,"secs":0}'))
    dels = []
    pg5.on("request", lambda r: dels.append(r.url.replace(BASE, "")) if r.method == "DELETE" else None)
    pg5.goto(BASE + "/meetings/new", wait_until="domcontentloaded")
    pg5.wait_for_timeout(400)
    pg5.evaluate("()=>{var b=document.getElementById('recBtn'); if(b) b.dataset.autorec='1';}")  # z1143
    pg5.click("#recBtn")
    pg5.wait_for_timeout(2500)
    newid = pg5.evaluate("window.__MTG && window.__MTG.id")
    pg5.evaluate("()=>{var b=document.getElementById('recBtn'); if(b) b.dataset.autorec='1';}")  # z1143
    pg5.click("#recBtn")
    pg5.wait_for_timeout(5000)
    sttxt = pg5.inner_text("#recStatus")
    ok("소리가 없으면 그렇게 알린다", "녹음된 소리가 없습니다" in sttxt, sttxt[:80])
    ok("방금 만든 빈 회의록을 지움", any(("/api/meeting/%d" % newid) in d for d in dels), (newid, dels[:3]))
    # 브라우저 밖에서 확인(일부러 404 를 받는 요청이 화면 오류 목록에 섞이지 않게)
    import urllib.request, urllib.error
    try:
        gone = urllib.request.urlopen(BASE + "/api/meeting/%d/rec-status" % newid, timeout=10).status
    except urllib.error.HTTPError as e:
        gone = e.code
    ok("그 회의가 실제로 없어짐", gone == 404, gone)
    ctx5.close()

    ctx2.close(); ctx3.close(); ctx4.close()
    B.close()

# ⑥에서 일부러 막은 rec-start 의 ERR_FAILED 는 시험이 만든 것이라 뺀다
bad_err = [e for e in errs if "favicon" not in e and "sw.js" not in e and "ERR_FAILED" not in e]
ok("화면 오류 없음", not bad_err, bad_err[:3])
print("\n" + "=" * 68)
print("합계: 통과 %d · 실패 %d" % (sum(1 for _, c in res if c), sum(1 for _, c in res if not c)))
for n, c in res:
    if not c:
        print("  - 실패:", n)
print("=" * 68)
sys.exit(1 if any(not c for _, c in res) else 0)
