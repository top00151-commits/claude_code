# -*- coding: utf-8 -*-
"""z1180 검사기 — 🔍 「🗓 회의 카드 모아보기」 탭·「🎤 음성 메모」 검색 + 두 화면 「AI」→「빅터AI」.
대표 지시 2026-10-14
  「회의록 검색 기능을 "회의카드모아보기", "음성메모" 이 부분에도 적용을 해.. 이 두가지도 검색할수있게..」
  「회의록 및 음성메모 정리할때 AI가 정리중입니다.. 이 표현 말고 AI를 "빅터AI"로 변경해줘..」
  → 권장안 확정(AskUserQuestion): 검색 = 카드 글 + 그 회의록 내용 · 옛 기간 저절로 / 빅터AI = 두 화면 전부(관리자 「AI 설정」「AI 키」만 그대로)

재는 것 (앱 두 벌 = 운영 그대로(app_base) · 새것(app_new) · 진짜 서버 · 이음 목록과 AI 만 가짜 · 진짜 브라우저)
  🗓 모아보기 탭
   A① 🔴 반대 시험 — 운영엔 검색 칸 **없음**
   A② 칸은 **읽기 전용으로 시작**(크롬 자동 채움 막기) · 누르면 풀림 · 안내 글
   A③ 처음엔 60일 전부터만 — 200일·600일 전 카드는 **아직 없다**
   A④ 「설비」 → 제목에서 찾은 3장(옛 200일 전 카드는 **저절로 불러와** 찾는다) · 노란 표시 · 묶음(예정·진행한 회의) 그대로
       · 🔴 옛 기간 불러오기는 **끝난다**(한 건도 없는 440일이 나오면 멈춤 · 이음에 더 묻지 않는다) · 「더 보기」 감춤
   A⑤ 참석자「최민수」 · 외부「박부장」 · 장소「3층」 → 그 카드 하나 · 그 줄이 노랗게
   A⑥ 회의록 내용「현대모비스」 → 그 카드 하나 + 「📋 회의록 · 정리」 + 찾은 곳 한 줄(노랑)
   A⑦ 🔴 두 곳에 걸친 AND 「IPO 최민수」(IPO=회의록 원문 · 최민수=참석자) → 그 카드 하나 · 「IPO」만 있는 다른 카드는 빠진다
   A⑧ 🔴 남의 비공개 회의록 — 「비밀단어」 0건 · 「IPO」에도 그 카드는 안 나온다
   A⑨ 600일 전 카드도 찾는다 · 없는 낱말 → 「찾는 회의가 없습니다」 · ✕ 지우면 전부(옛 카드 포함) · 요약 줄 돌아옴
   A⑩ 주소에 ?q= 가 남고, 다시 열면 그대로 찾는다 · Esc 로 지움
   A⑪ 베트남어 직원 — 칸 안내·건수·「📋 Biên bản」 · 📱 375 폭 옆으로 안 밀림 · 콘솔 오류 0
  🎤 음성 메모
   B① 🔴 반대 시험 — 운영엔 검색 칸 없음
   B② 읽기 전용 시작 · 「현대모비스」 → 내 메모 하나(남의 메모 X) · 「정리」「원문」 칸 · 찾은 곳 노랑
   B③ 원문 5만 2천 자 끝의 「희귀낱말」도 찾는다 · 제목 없는 메모는 「제목 없는 메모」 그대로
   B④ 제목「설비」 노랑 · 🔴 「%」「_」는 글자 그대로(모든 메모가 걸리지 않는다) · AND · 없음 안내 · ✕ · ?q= 다시 열기
   B⑤ 🔴 서버도 **내 것만** — 남이 찾으면 남의 것만 · 📱 375 · 콘솔 0
  🤖 빅터AI
   C① 🔴 반대 시험 — 운영 진행 칸 「AI가 회의 내용을 다시 정리하는 중…」 · 단추 「저장하고 AI 정리」
   C② 회의록 진행 칸 「빅터AI가 회의 내용을 다시 정리하는 중…」 · 단추 「💾 저장하고 빅터AI 정리」 · 결정·할 일 꼬리표 「빅터AI」
   C③ 화면(숨은 칸·말풍선 포함)에 남은 「AI」 0 — 관리자 「AI 설정」「AI 키」 안내만 예외 · 빈 칸 안내 · 회의록 양식
   C④ 음성 메모 진행 칸 「빅터AI가 녹음 내용을 다시 정리하는 중…」 · 제목 안내
   C⑤ 서버 글 — AI 꺼짐 · 까닭 없는 실패 · 터짐 → 「빅터AI …」 (메일의 같은 글은 세션 15 구역이라 그대로)
   C⑥ 베트남어 화면 「Victor AI」
  📸 대표께 보여 드릴 사진 — shots/
쓰는 법: py search80_ui.py <app_base·app_new 가 있는 폴더>
판정: **종료코드**(0=통과) + 요약 줄.
"""
import io
import json
import os
import re
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1] if len(sys.argv) > 1 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
PB, PN = 8911, 8912
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
OK = FAIL = 0


def chk(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (name, detail))


def freeport(port):
    """🔴 포트 주인을 멈추고 **비었는지 확인**한다(옛 서버가 옛 코드를 시험한 적 있다 · 09-21)."""
    ps = ("Get-NetTCPConnection -State Listen -LocalPort %d -ErrorAction SilentlyContinue | "
          "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }") % port
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
    for _ in range(50):
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "@(Get-NetTCPConnection -State Listen -LocalPort %d -ErrorAction SilentlyContinue).Count" % port],
                           capture_output=True, text=True)
        if (r.stdout or "").strip() in ("0", ""):
            return True
        time.sleep(0.2)
    raise SystemExit("!! 포트 %d 를 비우지 못했다" % port)


def boot(app, port):
    freeport(port)
    sp = os.path.join(HERE, "seed_%d.json" % port)
    if os.path.exists(sp):
        os.remove(sp)
    lp = os.path.join(APPDIR, "srv_%d.log" % port)
    pr = subprocess.Popen([P313, os.path.join(HERE, "run_search80_app.py"), os.path.join(APPDIR, app), str(port)],
                          stdout=io.open(lp, "w", encoding="utf-8"), stderr=subprocess.STDOUT, cwd=APPDIR)
    for _ in range(600):
        time.sleep(0.2)
        s = io.open(lp, encoding="utf-8").read() if os.path.exists(lp) else ""
        if "READY" in s and os.path.exists(sp):
            return pr, json.loads(io.open(sp, encoding="utf-8").read())
        if pr.poll() is not None:
            print(s[-2500:])
            raise SystemExit("!! %s(%d) 가 떴다 죽었다" % (app, port))
    raise SystemExit("!! %s(%d) 가 안 떴다" % (app, port))


def kill(*prs):
    for pr in prs:
        try:
            pr.terminate()
        except Exception:
            pass


def page_for(br, port, uid, w=1280, h=1000):
    ctx = br.new_context(viewport={"width": w, "height": h})
    ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": "http://127.0.0.1:%d" % port}])
    pg = ctx.new_page()
    pg.add_init_script("try{localStorage.setItem('knk_works_install_hint_never','1');}catch(e){}")
    pg.on("dialog", lambda d: d.accept())
    errs = []
    pg.on("console", lambda m: errs.append("console: " + m.text[:160]) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:160]))
    return ctx, pg, errs


U = lambda port, path: "http://127.0.0.1:%d%s" % (port, path)

CARDS = """() => Array.from(document.querySelectorAll('#mcBody .mc-card')).map(function(c){
  var p = c.previousElementSibling; while (p && !(p.classList && p.classList.contains('mc-sec'))) p = p.previousElementSibling;
  return { t: (c.querySelector('.mc-ttl') || {}).textContent || '',
           marks: Array.from(c.querySelectorAll('.mc-ttl mark, .mc-sub mark')).map(function(m){ return m.textContent; }),
           subs: Array.from(c.querySelectorAll('.mc-sub')).map(function(s){ return s.innerHTML; }).join(' | '),
           chips: Array.from(c.querySelectorAll('.mq-hit .mq-f')).map(function(m){ return m.textContent; }),
           snip: (c.querySelector('.mq-hit .mq-snip') || {}).innerHTML || '',
           sec: p ? p.textContent : '' }; })"""
VNS = """() => Array.from(document.querySelectorAll('.vn-card[data-vid]')).filter(function(a){
  return !a.hidden && getComputedStyle(a).display !== 'none'; }).map(function(a){
  return { id: +a.getAttribute('data-vid'), t: a.querySelector('.vn-ttl').textContent,
           tmarks: Array.from(a.querySelectorAll('.vn-ttl mark')).map(function(m){ return m.textContent; }),
           chips: Array.from(a.querySelectorAll('.mq-hit .mq-f')).map(function(m){ return m.textContent; }),
           snip: (a.querySelector('.mq-snip') || {}).innerHTML || '' }; })"""
#  진행 칸 하나를 읽는다(z1177 검사기와 같은 칸)
PANEL = """(id) => { var h = document.getElementById(id); if (!h) return null; var cs = getComputedStyle(h),
  t = h.querySelector('.kab-t'), s = h.querySelector('.kab-s');
  return { shown: !h.hidden && cs.display !== 'none', cls: h.className, title: t ? t.textContent : '', sub: s ? s.textContent : '' }; }"""
#  화면에 보이는 글(본문) 중 「빅터AI」·관리자 설정 안내를 뺀 「AI」
VIS_AI = """() => { var t = (document.querySelector('main') || document.body).innerText || '';
  ['빅터AI', 'Victor AI', 'AI 설정', 'AI 키', 'OpenAI', 'Cài đặt AI', 'khóa AI'].forEach(function(a){ t = t.split(a).join(''); });
  return t.match(/.{0,18}(?<![A-Za-z])AI(?![A-Za-z]).{0,18}/g) || []; }"""
NOHSCROLL = "() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth })"


def src_ai(html):
    """서버 화면 원본(숨은 칸·말풍선 title 까지) — **본문(main)만** · 스크립트·스타일·주석을 빼고 남은 「AI」.
    (왼쪽 메뉴·윗줄은 이번 일 범위 밖이라 보지 않는다)"""
    m = re.search(r"<main[\s\S]*?</main>", html)
    s = m.group(0) if m else ""
    s = re.sub(r"<script[\s\S]*?</script>", "", s)
    s = re.sub(r"<style[\s\S]*?</style>", "", s)
    s = re.sub(r"<!--[\s\S]*?-->", "", s)
    for a in ("빅터AI", "Victor AI", "AI 설정", "AI 키", "OpenAI", "Cài đặt AI", "khóa AI"):
        s = s.replace(a, "")
    return re.findall(r".{0,24}(?<![A-Za-z_])AI(?![A-Za-z_]).{0,24}", s)


def wait_panel(pg, pid, cond, sec):
    t0 = time.time()
    while time.time() - t0 < sec:
        p = pg.evaluate(PANEL, pid)
        if p and cond(p):
            return p
        pg.wait_for_timeout(150)
    return pg.evaluate(PANEL, pid)


def cq(pg, q, timeout=15000):
    """모아보기 검색 — 지우고 넣는다(옛 건수 글을 새 결과로 착각하지 않게) · 결과(옛 기간 불러오기 포함)가 멈출 때까지."""
    pg.fill("#mcqInput", "")
    pg.wait_for_function("() => document.getElementById('mcqCnt').textContent === ''", timeout=5000)
    pg.fill("#mcqInput", q)
    pg.wait_for_function("""() => { var t = document.getElementById('mcqCnt').textContent;
        return /(검색 결과|Kết quả)/.test(t) && t.indexOf('…') < 0 && document.getElementById('mcMore').hidden; }""",
                         timeout=timeout)
    pg.wait_for_timeout(300)
    return pg.evaluate(CARDS), pg.inner_text("#mcqCnt")


def vq(pg, q, timeout=10000):
    pg.fill("#vqInput", "")
    pg.wait_for_function("() => document.getElementById('vqCnt').textContent === ''", timeout=5000)
    pg.fill("#vqInput", q)
    pg.wait_for_function("() => /검색 결과 \\d+건|검색하지 못했/.test(document.getElementById('vqCnt').textContent)",
                         timeout=timeout)
    return pg.evaluate(VNS), pg.inner_text("#vqCnt")


def titles(cards):
    return sorted(c["t"] for c in cards)


def calls(pg, port):
    return pg.request.get(U(port, "/__test/eum_calls")).json()["calls"]


pb = pn = None
try:
    pb, sb = boot("app_base", PB)
    pn, sn = boot("app_new", PN)
    print("서버 둘 READY — 운영 그대로 %d · 새것 %d" % (PB, PN))
    with sync_playwright() as p:
        br = p.chromium.launch()

        # ═════════════ 🗓 모아보기 탭 ═════════════
        print("\n── A① 🔴 반대 시험(운영 그대로) ──")
        cb, gb, eb = page_for(br, PB, sb["me"])
        gb.goto(U(PB, "/meetings?tab=cards"), wait_until="domcontentloaded")
        gb.wait_for_selector("#mcBody .mc-card", timeout=20000)
        chk("운영: 모아보기 탭에 검색 칸 **없음**", gb.locator("#mcqInput").count() == 0)
        gb.goto(U(PB, "/voice-notes"), wait_until="domcontentloaded")
        gb.wait_for_selector(".vn-card", timeout=20000)
        chk("운영: 음성 메모 목록에 검색 칸 **없음**", gb.locator("#vqInput").count() == 0)

        print("\n── A② 칸 · A③ 처음 불러온 기간 ──")
        cn, gn, en = page_for(br, PN, sn["me"])
        gn.goto(U(PN, "/meetings?tab=cards"), wait_until="domcontentloaded")
        gn.wait_for_selector("#mcBody .mc-card", timeout=20000)
        a2 = gn.evaluate("""() => { var i = document.getElementById('mcqInput');
            return { ro: i.readOnly, ph: i.placeholder, title: i.title, ac: i.getAttribute('autocomplete'),
                     inWrap: !!i.closest('#mcWrap'), aboveBody: !!(i.compareDocumentPosition(document.getElementById('mcBody')) & 4) }; }""")
        chk("검색 칸이 **카드 위**에 있다(탭 안)", a2["inWrap"] and a2["aboveBody"], a2)
        chk("🔴 **읽기 전용으로 시작**(크롬이 로그인 ID 를 못 채운다)", a2["ro"] is True, a2)
        chk("칸 안내 「%s」" % a2["ph"], a2["ph"] == "제목·참석자·회의록 내용·고객사로 찾기", a2["ph"])
        chk("말풍선 = 띄어 쓰면 모두 들어간 것만", "모두 들어간" in a2["title"], a2["title"])
        t0 = titles(gn.evaluate(CARDS))
        chk("처음엔 60일 안 4장만(200·600일 전 카드는 아직 없다)",
            t0 == sorted(["삼성 설비 미팅", "주간 회의", "경영 회의", "예정 설비 점검"]), t0)
        chk("검색 전엔 요약 줄(전체 n건) 그대로", gn.locator("#mcBody .mc-sum").count() == 1)
        chk("검색 전엔 「더 보기」 보인다", gn.evaluate("() => !document.getElementById('mcMore').hidden"))
        n_calls0 = len(calls(gn, PN))
        gn.click("#mcqInput")
        chk("누르면 풀린다", gn.evaluate("() => document.getElementById('mcqInput').readOnly") is False)

        print("\n── A④ 「설비」 + 옛 기간 저절로 ──")
        c4, cnt4 = cq(gn, "설비", timeout=25000)
        chk("찾은 카드 = 삼성 설비 미팅 · 예정 설비 점검 · **200일 전** 옛날 설비 회의 (%s)" % cnt4,
            titles(c4) == sorted(["삼성 설비 미팅", "예정 설비 점검", "옛날 설비 회의 고대유물"]), titles(c4))
        chk("건수 「검색 결과 3건」", cnt4.strip() == "검색 결과 3건", cnt4)
        chk("제목의 「설비」가 노랗다", all("설비" in c["marks"] for c in c4), [c["marks"] for c in c4])
        sec = {c["t"]: c["sec"] for c in c4}
        chk("묶음 그대로 — 다가올 회의는 「진행할 회의」 · 지난 것은 「진행한 회의」",
            "진행할" in sec.get("예정 설비 점검", "") and "진행한" in sec.get("삼성 설비 미팅", "")
            and "진행한" in sec.get("옛날 설비 회의 고대유물", ""), sec)
        chk("찾는 동안엔 전체 요약 줄 대신 건수", gn.locator("#mcBody .mc-sum").count() == 0)
        cl = calls(gn, PN)[n_calls0:]
        chk("🔵 옛 기간을 이음에 **%d번** 더 물었다(440일씩 · 600일 전까지 닿고 빈 기간에서 멈춤)" % len(cl),
            len(cl) == 3, cl)
        spans = [(r["from"], r["to"]) for r in cl]
        ok_span = all((time.mktime(time.strptime(b, "%Y-%m-%d")) - time.mktime(time.strptime(a, "%Y-%m-%d"))) / 86400 <= 450
                      for a, b in spans)
        chk("한 번에 묻는 기간은 서버 상한(450일) 안", ok_span, spans)
        gn.wait_for_timeout(3000)
        chk("🔴 3초 더 기다려도 이음에 **더 묻지 않는다**(끝없이 돌지 않는다)", len(calls(gn, PN)) == n_calls0 + 3,
            len(calls(gn, PN)) - n_calls0)
        chk("옛 기간을 끝까지 불러왔으니 「더 보기」 감춤", gn.evaluate("() => document.getElementById('mcMore').hidden"))
        gn.screenshot(path=os.path.join(SHOTS, "a4_cards_search_old.png"), full_page=True)

        print("\n── A⑤ 참석자 · 외부 · 장소 ──")
        for q, where in (("최민수", "참석자"), ("박부장", "외부 참석자"), ("3층", "장소")):
            cc, ct = cq(gn, q)
            chk("「%s」(%s) → 삼성 설비 미팅 하나" % (q, where), titles(cc) == ["삼성 설비 미팅"], (titles(cc), ct))
            chk("  그 줄에 노란 「%s」" % q, any(q in m for c in cc for m in c["marks"]), [c["marks"] for c in cc])

        print("\n── A⑥ 회의록 내용 「현대모비스」 ──")
        c6, ct6 = cq(gn, "현대모비스")
        chk("「현대모비스」 → 주간 회의 하나(카드 글엔 없고 **회의록 정리**에 있다)", titles(c6) == ["주간 회의"], titles(c6))
        h6 = c6[0] if c6 else {}
        chk("「📋 회의록」 + 「정리」 칸 이름", h6.get("chips", [])[:1] == ["📋 회의록"] and "정리" in h6.get("chips", []), h6.get("chips"))
        chk("찾은 곳 한 줄에 노란 「현대모비스」", "<mark>현대모비스</mark>" in h6.get("snip", ""), h6.get("snip"))
        gn.screenshot(path=os.path.join(SHOTS, "a6_cards_search_minutes.png"), full_page=True)

        print("\n── A⑦ 두 곳에 걸친 AND · A⑧ 남의 비공개 ──")
        c7, ct7 = cq(gn, "IPO 최민수")
        chk("🔴 「IPO 최민수」 → 삼성 설비 미팅 하나(IPO=회의록 원문 · 최민수=참석자)", titles(c7) == ["삼성 설비 미팅"], titles(c7))
        chk("  「📋 회의록 · 원문」 줄이 붙는다", c7 and "원문" in c7[0]["chips"], c7[0]["chips"] if c7 else None)
        c8, ct8 = cq(gn, "IPO")
        chk("「IPO」 → 내가 볼 수 있는 회의록 둘만(삼성 설비 미팅 · 주간 회의)", titles(c8) == sorted(["삼성 설비 미팅", "주간 회의"]), titles(c8))
        chk("🔴 남의 **비공개** 회의록(경영 회의)은 「IPO」에 안 나온다", "경영 회의" not in titles(c8), titles(c8))
        c9, ct9 = cq(gn, "비밀단어")
        chk("🔴 「비밀단어」(남의 비공개 회의록에만) → 0건", c9 == [] and ct9.strip() == "검색 결과 0건", (titles(c9), ct9))
        chk("  「찾는 회의가 없습니다」", "찾는 회의가 없습니다" in gn.inner_text("#mcBody"), gn.inner_text("#mcBody")[:80])

        print("\n── A⑨ 600일 전 · ✕ ──")
        c10, _ = cq(gn, "아주옛날")
        chk("**600일 전** 카드도 찾는다", titles(c10) == ["아주옛날 회의"], titles(c10))
        c11, _ = cq(gn, "고대유물")
        chk("200일 전 카드 「고대유물」", titles(c11) == ["옛날 설비 회의 고대유물"], titles(c11))
        gn.click("#mcqClear")
        gn.wait_for_function("() => document.getElementById('mcqCnt').textContent === ''", timeout=5000)
        gn.wait_for_timeout(300)
        call = gn.evaluate(CARDS)
        chk("✕ 지우면 전부(불러온 옛 카드 포함 6장)", len(call) == 6, titles(call))
        chk("✕ 뒤 노란 표시 0 · 회의록 줄 0", not any(c["marks"] or c["chips"] for c in call))
        chk("✕ 뒤 요약 줄 돌아옴", gn.locator("#mcBody .mc-sum").count() == 1)
        chk("✕ 칸 감춤", gn.evaluate("() => document.getElementById('mcqClear').hidden"))

        print("\n── A⑩ 주소 · 다시 열기 · Esc ──")
        cq(gn, "현대모비스")
        url = gn.url
        chk("주소에 tab=cards 와 q 가 남는다", "tab=cards" in url and "q=" in url, url)
        gn.goto(url, wait_until="domcontentloaded")
        gn.wait_for_function("""() => /검색 결과 \\d+건/.test(document.getElementById('mcqCnt').textContent)
                                && document.getElementById('mcqCnt').textContent.indexOf('…') < 0
                                && document.getElementById('mcMore').hidden""", timeout=25000)
        gn.wait_for_timeout(300)
        r10 = gn.evaluate(CARDS)
        chk("다시 열면 칸에 그 낱말 · 결과 그대로(주간 회의)", gn.input_value("#mcqInput") == "현대모비스" and titles(r10) == ["주간 회의"],
            (gn.input_value("#mcqInput"), titles(r10)))
        gn.click("#mcqInput")
        gn.keyboard.press("Escape")
        gn.wait_for_function("() => document.getElementById('mcqCnt').textContent === ''", timeout=5000)
        chk("Esc 로 지움 → 주소의 q 도 빠진다", "q=" not in gn.url and gn.input_value("#mcqInput") == "", gn.url)
        chk("🗓 모아보기 화면 콘솔 오류 0", not en, en[:3])

        print("\n── A⑪ 베트남어 · 📱 ──")
        cv, gv, ev = page_for(br, PN, sn["vnu"])
        gv.goto(U(PN, "/meetings?tab=cards"), wait_until="domcontentloaded")
        gv.wait_for_selector("#mcBody .mc-card", timeout=20000)
        phv = gv.evaluate("() => document.getElementById('mcqInput').placeholder")
        chk("베트남어 칸 안내 「%s」" % phv, phv == "Tìm theo tiêu đề, người tham dự, nội dung biên bản, khách hàng", phv)
        gv.click("#mcqInput")
        cvv, ctv = cq(gv, "현대모비스")
        chk("베트남어 건수 「%s」" % ctv.strip(), ctv.strip() == "Kết quả: 1 cuộc họp", ctv)
        chk("베트남어 회의록 줄 「📋 Biên bản · Tóm tắt」", cvv and cvv[0]["chips"][:1] == ["📋 Biên bản"] and "Tóm tắt" in cvv[0]["chips"],
            cvv[0]["chips"] if cvv else None)
        chk("베트남어 화면 콘솔 오류 0", not ev, ev[:3])
        cv.close()
        cm, gm, em = page_for(br, PN, sn["me"], 375, 812)
        gm.goto(U(PN, "/meetings?tab=cards&q=" + "설비"), wait_until="domcontentloaded")
        gm.wait_for_function("""() => /검색 결과 \\d+건/.test(document.getElementById('mcqCnt').textContent)
                                && document.getElementById('mcqCnt').textContent.indexOf('…') < 0
                                && document.getElementById('mcMore').hidden""", timeout=25000)
        hs = gm.evaluate(NOHSCROLL)
        box = gm.evaluate("() => { var r = document.querySelector('#mcWrap .mq-box').getBoundingClientRect(); return { l: r.left, r: r.right }; }")
        chk("📱 375 폭: 옆으로 안 밀림(%s) · 칸이 화면 안(%s)" % (hs, box), hs["sw"] <= hs["iw"] and box["l"] >= 0 and box["r"] <= 375, (hs, box))
        gm.screenshot(path=os.path.join(SHOTS, "a11_cards_search_phone.png"), full_page=True)
        chk("📱 콘솔 오류 0", not em, em[:3])
        cm.close()

        # ═════════════ 🎤 음성 메모 ═════════════
        print("\n── B② 「현대모비스」 ──")
        gn.goto(U(PN, "/voice-notes"), wait_until="domcontentloaded")
        gn.wait_for_selector("#vqInput", timeout=20000)
        b2 = gn.evaluate("() => { var i = document.getElementById('vqInput'); return { ro: i.readOnly, ph: i.placeholder }; }")
        chk("🔴 읽기 전용으로 시작", b2["ro"] is True, b2)
        chk("칸 안내 「%s」" % b2["ph"], b2["ph"] == "제목·정리·원문으로 찾기", b2)
        all0 = gn.evaluate(VNS)
        chk("목록 = 내 메모 넷(남의 것 없음)", sorted(v["id"] for v in all0) == sorted([sn["notes"][k] for k in ("N1", "N2", "N3", "N4")]),
            [v["t"] for v in all0])
        gn.click("#vqInput")
        v1, vc1 = vq(gn, "현대모비스")
        chk("「현대모비스」 → 거래처 통화 하나 (%s)" % vc1.strip(), [v["id"] for v in v1] == [sn["notes"]["N1"]], [v["t"] for v in v1])
        chk("  어디서 = 「정리」「원문」", v1 and v1[0]["chips"] == ["정리", "원문"], v1[0]["chips"] if v1 else None)
        chk("  찾은 곳 한 줄 노랑", v1 and "<mark>현대모비스</mark>" in v1[0]["snip"], v1[0]["snip"] if v1 else None)
        gn.screenshot(path=os.path.join(SHOTS, "b2_voice_search.png"), full_page=True)

        print("\n── B③ 5만 2천 자 원문 ──")
        v3, _ = vq(gn, "희귀낱말")
        chk("원문 **5만 2천 자 끝**의 「희귀낱말」 → 그 메모", [v["id"] for v in v3] == [sn["notes"]["N2"]], [v["t"] for v in v3])
        chk("  어디서 = 「원문」 · 찾은 곳 노랑", v3 and v3[0]["chips"] == ["원문"] and "<mark>희귀낱말</mark>" in v3[0]["snip"],
            v3[0] if v3 else None)
        chk("  제목 없는 메모는 「제목 없는 메모」 그대로", v3 and v3[0]["t"] == "제목 없는 메모", v3[0]["t"] if v3 else None)

        print("\n── B④ 제목 · %·_ · AND · 없음 · ✕ · 다시 열기 ──")
        v4, _ = vq(gn, "설비")
        chk("「설비」 → 설비 점검 메모 · 제목 노랑", [v["id"] for v in v4] == [sn["notes"]["N3"]] and v4[0]["tmarks"] == ["설비"],
            v4)
        for q in ("30%", "%", "_"):
            vv, _ = vq(gn, q)
            chk("🔴 「%s」는 글자 그대로 → 설비 점검 메모 하나(모든 메모가 걸리지 않는다)" % q,
                [v["id"] for v in vv] == [sn["notes"]["N3"]], [v["t"] for v in vv])
        v5, _ = vq(gn, "현대모비스 납기")
        chk("「현대모비스 납기」(AND) → 거래처 통화", [v["id"] for v in v5] == [sn["notes"]["N1"]], [v["t"] for v in v5])
        v6, vc6 = vq(gn, "현대모비스 설비")
        chk("「현대모비스 설비」 → 0건 · 「찾는 메모가 없습니다」", v6 == [] and vc6.strip() == "검색 결과 0건"
            and gn.evaluate("() => !document.getElementById('vqNone').hidden"), (v6, vc6))
        gn.click("#vqClear")
        gn.wait_for_function("() => document.getElementById('vqCnt').textContent === ''", timeout=5000)
        v7 = gn.evaluate(VNS)
        chk("✕ 지우면 넷 다 · 「제목 없는 메모」 글 그대로 · 노랑 0",
            len(v7) == 4 and any(v["t"] == "제목 없는 메모" for v in v7) and not any(v["tmarks"] or v["chips"] for v in v7), v7)
        chk("✕ 뒤 「없습니다」 안내 숨김", gn.evaluate("() => document.getElementById('vqNone').hidden"))
        gn.goto(U(PN, "/voice-notes?q=설비"), wait_until="domcontentloaded")
        gn.wait_for_function("() => /검색 결과 \\d+건/.test(document.getElementById('vqCnt').textContent)", timeout=10000)
        v8 = gn.evaluate(VNS)
        chk("?q=설비 로 다시 열면 그대로 찾는다", [v["id"] for v in v8] == [sn["notes"]["N3"]] and gn.input_value("#vqInput") == "설비",
            [v["t"] for v in v8])
        chk("🎤 목록 콘솔 오류 0", not en, en[:3])

        print("\n── B⑤ 서버도 내 것만 · 📱 ──")
        co, go, eo = page_for(br, PN, sn["other"])
        r_me = gn.request.get(U(PN, "/api/voice-notes/search?q=" + "현대모비스")).json()
        r_ot = go.request.get(U(PN, "/api/voice-notes/search?q=" + "현대모비스")).json()
        chk("🔴 서버 답: 나 → 내 메모만(%s)" % [i["id"] for i in r_me["items"]], [i["id"] for i in r_me["items"]] == [sn["notes"]["N1"]], r_me)
        chk("🔴 서버 답: 남 → 남의 메모만(%s)" % [i["id"] for i in r_ot["items"]], [i["id"] for i in r_ot["items"]] == [sn["notes"]["O1"]], r_ot)
        r_empty = gn.request.get(U(PN, "/api/voice-notes/search?q=" + "%20%20")).json()
        chk("빈 낱말 → 0건(목록 전부를 돌려주지 않는다)", r_empty.get("ok") and r_empty.get("items") == [], r_empty)
        co.close()
        cm2, gm2, em2 = page_for(br, PN, sn["me"], 375, 812)
        gm2.goto(U(PN, "/voice-notes?q=현대모비스"), wait_until="domcontentloaded")
        gm2.wait_for_function("() => /검색 결과 \\d+건/.test(document.getElementById('vqCnt').textContent)", timeout=10000)
        hs2 = gm2.evaluate(NOHSCROLL)
        chk("📱 375 폭: 옆으로 안 밀림 %s" % hs2, hs2["sw"] <= hs2["iw"], hs2)
        gm2.screenshot(path=os.path.join(SHOTS, "b5_voice_search_phone.png"), full_page=True)
        chk("📱 콘솔 오류 0", not em2, em2[:3])
        cm2.close()

        # ═════════════ 🤖 빅터AI ═════════════
        print("\n── C① 🔴 반대 시험(운영 그대로) ──")
        #  「💾 저장하고 … 정리」 단추는 **새 회의록**에서 「✏️ 작성하기」를 눌러야 나온다(있는 회의는 「💾 저장」)
        gb.goto(U(PB, "/meetings/new"), wait_until="domcontentloaded")
        gb.wait_for_selector("#btnWriteMode", timeout=20000)
        gb.click("#btnWriteMode")
        gb.wait_for_selector("#writeWrap:not([hidden])", timeout=5000)
        chk("운영: 단추 「💾 저장하고 AI 정리」", "💾 저장하고 AI 정리" in gb.inner_text("main"))
        gb.goto(U(PB, "/meetings/%d" % sb["ids"]["M5"]), wait_until="domcontentloaded")
        gb.wait_for_selector("#btnExtractTop", timeout=20000)
        gb.click("#btnExtractTop")
        pbp = wait_panel(gb, "aiBusy", lambda q: q["shown"], 4)
        chk("운영: 진행 칸 「%s」" % (pbp or {}).get("title"), pbp and pbp["title"] == "AI가 회의 내용을 다시 정리하는 중…", pbp)
        wait_panel(gb, "aiBusy", lambda q: "ok" in q["cls"].split() or "err" in q["cls"].split(), 20)

        print("\n── C② 회의록 진행 칸 · 단추 · 꼬리표 ──")
        gn.goto(U(PN, "/meetings/new"), wait_until="domcontentloaded")
        gn.wait_for_selector("#btnWriteMode", timeout=20000)
        gn.click("#btnWriteMode")
        gn.wait_for_selector("#writeWrap:not([hidden])", timeout=5000)
        chk("새 회의록 「✏️ 작성하기」 → 단추 「💾 저장하고 빅터AI 정리」", "💾 저장하고 빅터AI 정리" in gn.inner_text("main"))
        ph = gn.evaluate("() => document.getElementById('mtgBody').placeholder")
        chk("원문 칸 안내 「…「저장하고 빅터AI 정리」를 누르면…」", "「저장하고 빅터AI 정리」를 누르면" in ph, ph)
        va0 = gn.evaluate(VIS_AI)
        chk("🔴 새 회의록 화면에 보이는 「AI」 0 %s" % va0, not va0, va0)
        gn.goto(U(PN, "/meetings/%d" % sn["ids"]["M5"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#btnExtractTop", timeout=20000)
        tags = gn.evaluate("() => Array.from(document.querySelectorAll('.ri-ai')).map(function(e){ return e.textContent; })")
        chk("결정·할 일 옆 꼬리표 = 「빅터AI」 (%s)" % tags, tags and all(t == "빅터AI" for t in tags) and len(tags) >= 2, tags)
        gn.click("#btnExtractTop")
        pnp = wait_panel(gn, "aiBusy", lambda q: q["shown"], 4)
        chk("🔵 진행 칸 「%s」" % (pnp or {}).get("title"), pnp and pnp["title"] == "빅터AI가 회의 내용을 다시 정리하는 중…", pnp)
        gn.screenshot(path=os.path.join(SHOTS, "c2_meeting_victor_busy.png"), full_page=False)
        pdn = wait_panel(gn, "aiBusy", lambda q: "ok" in q["cls"].split() or "err" in q["cls"].split(), 20)
        chk("끝나면 초록 ✅ (%s)" % (pdn or {}).get("title"), pdn and "ok" in pdn["cls"].split(), pdn)
        gn.wait_for_timeout(500)
        tags2 = gn.evaluate("() => Array.from(document.querySelectorAll('.ri-ai')).map(function(e){ return e.textContent; })")
        chk("정리 뒤 새 결정·할 일 꼬리표도 「빅터AI」 (%s)" % tags2, tags2 and all(t == "빅터AI" for t in tags2), tags2)
        va = gn.evaluate(VIS_AI)
        chk("🔴 회의록 화면에 보이는 「AI」 0 (관리자 설정 안내 빼고) %s" % va, not va, va)

        print("\n── C③ 숨은 칸·말풍선까지 · 빈 칸 안내 · 회의록 양식 ──")
        for key in ("M5", "M6"):
            html = gn.request.get(U(PN, "/meetings/%d" % sn["ids"][key])).text()
            left = src_ai(html)
            chk("🔴 회의록 화면 원본(%s · 접힌 칸·말풍선 포함)에 남은 「AI」 0 %s" % (key, left[:3]), not left, left[:5])
        gn.goto(U(PN, "/meetings/%d" % sn["ids"]["M6"]), wait_until="domcontentloaded")
        gn.wait_for_timeout(800)
        m6 = gn.inner_text("main")
        chk("빈 결정 칸 「결정사항이 없습니다. 「💾 저장하고 빅터AI 정리」를 누르거나…」",
            "결정사항이 없습니다. 「💾 저장하고 빅터AI 정리」를 누르거나" in m6, m6[:0])
        chk("빈 할 일 칸 「할 일이 없습니다. 「💾 저장하고 빅터AI 정리」를 누르거나…」",
            "할 일이 없습니다. 「💾 저장하고 빅터AI 정리」를 누르거나" in m6)
        chk("제목 안내 「빅터AI가 내용을 보고 지어드려요」",
            "빅터AI가 내용을 보고" in gn.request.get(U(PN, "/meetings/new")).text())
        doc = gn.request.get(U(PN, "/meetings/%d/doc" % sn["ids"]["M6"])).text()
        chk("회의록 양식(정리 전) 「(회의록 화면에서 「💾 저장하고 빅터AI 정리」)」", "「💾 저장하고 빅터AI 정리」" in doc and "AI로 정리" not in doc)
        lst = gn.request.get(U(PN, "/meetings")).text()
        chk("🔴 회의록 목록 원본에 남은 「AI」 0 %s" % src_ai(lst)[:3], not src_ai(lst), src_ai(lst)[:5])
        crd = gn.request.get(U(PN, "/meetings?tab=cards")).text()
        chk("🔴 모아보기 탭 원본에 남은 「AI」 0 %s" % src_ai(crd)[:3], not src_ai(crd), src_ai(crd)[:5])

        print("\n── C④ 음성 메모 ──")
        gn.goto(U(PN, "/voice-notes/%d" % sn["notes"]["N1"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#vnRedo", timeout=20000)
        chk("음성 메모 제목 안내 「빅터AI가 내용을 보고」", "빅터AI가 내용을 보고" in gn.inner_text("main"))
        gn.click("#vnRedo")
        pv = wait_panel(gn, "vnAiBusy", lambda q: q["shown"], 4)
        chk("🔵 음성 메모 진행 칸 「%s」" % (pv or {}).get("title"), pv and pv["title"] == "빅터AI가 녹음 내용을 다시 정리하는 중…", pv)
        gn.screenshot(path=os.path.join(SHOTS, "c4_voice_victor_busy.png"), full_page=False)
        pvd = wait_panel(gn, "vnAiBusy", lambda q: "ok" in q["cls"].split() or "err" in q["cls"].split(), 20)
        chk("끝나면 초록 ✅", pvd and "ok" in pvd["cls"].split(), pvd)
        va2 = gn.evaluate(VIS_AI)
        chk("🔴 음성 메모 화면에 보이는 「AI」 0 %s" % va2, not va2, va2)
        for path in ("/voice-notes/%d" % sn["notes"]["N1"], "/voice-notes/new", "/voice-notes"):
            left = src_ai(gn.request.get(U(PN, path)).text())
            chk("🔴 %s 원본에 남은 「AI」 0 %s" % (path, left[:3]), not left, left[:5])

        print("\n── C⑤ 서버 글 ──")
        def post(pg, port, path):
            return pg.request.post(U(port, path), data="{}", headers={"Content-Type": "application/json"}).json()

        def wait_job(pg, port, mid):
            for _ in range(60):
                s = pg.request.get(U(port, "/api/meeting/%d/extract-status" % mid)).json()
                if s.get("state") in ("done", "error"):
                    return s
                time.sleep(0.25)
            return s
        res = {}
        for port, pg, sd, tag in ((PB, gb, sb, "운영"), (PN, gn, sn, "새것")):
            pg.request.get(U(port, "/__test/ai?on=0"))
            r1 = post(pg, port, "/api/meeting/%d/extract" % sd["ids"]["M5"])
            r2 = post(pg, port, "/api/voice-note/%d/extract" % sd["notes"]["N1"])
            pg.request.get(U(port, "/__test/ai?on=1"))
            post(pg, port, "/api/meeting/%d/extract" % sd["ids"]["M7"])
            post(pg, port, "/api/meeting/%d/extract" % sd["ids"]["M8"])
            s7, s8 = wait_job(pg, port, sd["ids"]["M7"]), wait_job(pg, port, sd["ids"]["M8"])
            res[tag] = (r1.get("error", ""), r2.get("error", ""), s7.get("error", ""), s8.get("error", ""))
            print("   %s: %s" % (tag, res[tag]))
        chk("🔴 반대 시험 — 운영은 「AI가 비활성…」「AI 추출 실패」「AI 정리에 실패했습니다」",
            res["운영"][0].startswith("AI가 비활성") and res["운영"][1].startswith("AI가 비활성")
            and res["운영"][2] == "AI 추출 실패" and res["운영"][3].startswith("AI 정리에 실패했습니다"), res["운영"])
        chk("AI 꺼짐(회의록) → 「빅터AI가 비활성 상태입니다(키 미설정). …」", res["새것"][0].startswith("빅터AI가 비활성 상태입니다(키 미설정)."), res["새것"][0])
        chk("AI 꺼짐(음성 메모) → 「빅터AI가 비활성 상태입니다(키 미설정).」", res["새것"][1] == "빅터AI가 비활성 상태입니다(키 미설정).", res["새것"][1])
        chk("까닭 없는 실패 → 「빅터AI 정리 실패」", res["새것"][2] == "빅터AI 정리 실패", res["새것"][2])
        chk("터짐 → 「빅터AI 정리에 실패했습니다: 가짜 폭발」", res["새것"][3] == "빅터AI 정리에 실패했습니다: 가짜 폭발", res["새것"][3])

        print("\n── C⑥ 베트남어 ──")
        cv2, gv2, ev2 = page_for(br, PN, sn["vnu"])
        gv2.goto(U(PN, "/meetings/new"), wait_until="domcontentloaded")
        gv2.wait_for_selector("#btnWriteMode", timeout=20000)
        gv2.click("#btnWriteMode")
        gv2.wait_for_selector("#writeWrap:not([hidden])", timeout=5000)
        chk("베트남어 단추 「💾 Lưu và Victor AI tổng hợp」", "💾 Lưu và Victor AI tổng hợp" in gv2.inner_text("main"))
        gv2.goto(U(PN, "/meetings/%d" % sn["ids"]["M5"]), wait_until="domcontentloaded")
        gv2.wait_for_selector("#btnExtractTop", timeout=20000)
        vtags = gv2.evaluate("() => Array.from(document.querySelectorAll('.ri-ai')).map(function(e){ return e.textContent; })")
        chk("베트남어 꼬리표 「Victor AI」 (%s)" % vtags, vtags and all(t == "Victor AI" for t in vtags), vtags)
        vva = gv2.evaluate(VIS_AI)
        chk("🔴 베트남어 화면에 보이는 「AI」 0 %s" % vva, not vva, vva)
        gv2.click("#btnExtractTop")
        pvv = wait_panel(gv2, "aiBusy", lambda q: q["shown"], 4)
        chk("베트남어 진행 칸 「%s」" % (pvv or {}).get("title"), pvv and pvv["title"] == "Victor AI đang tổng hợp lại nội dung cuộc họp…", pvv)
        wait_panel(gv2, "aiBusy", lambda q: "ok" in q["cls"].split() or "err" in q["cls"].split(), 20)
        chk("베트남어 화면 콘솔 오류 0", not ev2, ev2[:3])
        cv2.close()
        chk("새것 화면 콘솔 오류 0(전체)", not en, en[:3])
        br.close()
finally:
    kill(pb, pn)

print("\n사진: %s" % SHOTS)
print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
