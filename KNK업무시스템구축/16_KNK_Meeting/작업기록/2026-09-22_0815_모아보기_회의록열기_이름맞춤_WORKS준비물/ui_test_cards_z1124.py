# -*- coding: utf-8 -*-
"""🗓 회의 카드 모아보기 — 실제 WORKS 서버(8921) + 가짜 이음 입구(8922) + 시험용 크롬.
로컬 주소만 연다(운영 주소 없음)."""
import io, json, os, sys, threading, time
from datetime import datetime, timedelta, timezone
import httpx
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
HERE = 'C:/Users/top00/JR/Claude 코드/KNK업무시스템구축/16_KNK_Meeting/작업기록\\2026-09-21_1830_회의카드모아보기_끝났는데회의중_WORKS준비물'   # z1124 사본: 원래 시험 폴더의 seed.json·shots 를 그대로 쓴다
BASE = "http://127.0.0.1:8921"
FAKE = "http://127.0.0.1:8922"
seed = json.load(io.open(os.path.join(HERE, "seed.json"), encoding="utf-8"))
OUT = os.path.join(HERE, "shots")
res, errs = [], []


def ok(name, cond, extra=""):
    res.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (" · " + str(extra) if extra != "" else ""), flush=True)


def ctl(**kw):
    httpx.post(FAKE + "/__ctl", json=kw, timeout=5)


def seen():
    return httpx.get(FAKE + "/__seen", timeout=5).json()["seen"]


def reset_works():
    httpx.post(BASE + "/__test/cards_reset", timeout=5)


KST = timezone(timedelta(hours=9))
HIDE_HINT = """document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style');
  s.textContent = '#worksInstallHint{display:none}'; document.head.appendChild(s); });"""


def new_page(b, **kw):
    c = b.new_context(**kw)
    c.add_cookies([{"name": "tuser", "value": str(seed["ceo"]), "url": BASE}])
    c.add_init_script(HIDE_HINT)
    pg = c.new_page()
    tag = kw.get("viewport", {}).get("width")
    pg.on("console", lambda m: errs.append((tag, m.text)) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append((tag, "pageerror " + str(e))))
    reqs = []
    pg.on("request", lambda r: reqs.append(r.url) if "/api/meetings/msg-cards" in r.url else None)
    return c, pg, reqs


def settle(pg):
    pg.wait_for_load_state("networkidle")
    time.sleep(1.5)


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)

    # ── 1. 이음이 느려도 WORKS 는 멈추지 않는다 (일꾼 1개 보호) ──
    ctl(mode="ok", delay=4.0, extra=[], base=True, clear_seen=True)
    reset_works()
    box = {}

    def slow():
        t0 = time.time()
        r = httpx.get(BASE + "/api/meetings/msg-cards?from=2026-08-01&to=2026-08-02",
                      cookies={"tuser": str(seed["ceo"])}, timeout=20)
        box["slow"] = (time.time() - t0, r.status_code)

    th = threading.Thread(target=slow)
    th.start()
    time.sleep(0.8)
    t0 = time.time()
    r = httpx.get(BASE + "/api/version", timeout=10)
    fast = time.time() - t0
    th.join()
    # 이 PC 는 요청마다 약 0.5초가 더 걸린다 — 막혔다면 3초 이상 걸린다
    ok("1-1 이음 4초 기다리는 동안 다른 요청 바로 응답(막히지 않음)", r.status_code == 200 and fast < 2.0, round(fast, 3))
    ok("1-2 느린 요청도 끝남", box.get("slow", (0, 0))[1] == 200 and box["slow"][0] >= 3.5, box.get("slow"))
    # 8초 넘으면 연결 실패 안내 · 15초 쉼
    ctl(delay=15.0, clear_seen=True)
    reset_works()
    t0 = time.time()
    d = httpx.get(BASE + "/api/meetings/msg-cards?from=2026-08-03&to=2026-08-04",
                  cookies={"tuser": str(seed["ceo"])}, timeout=30).json()
    took = time.time() - t0
    ok("1-3 이음 15초 → 8초에 끊고 안내", d.get("ok") is False and "연결하지 못했습니다" in d.get("error", "") and took < 12,
       (round(took, 2), d))
    d2 = httpx.get(BASE + "/api/meetings/msg-cards?from=2026-08-05&to=2026-08-06",
                   cookies={"tuser": str(seed["ceo"])}, timeout=30).json()
    ok("1-4 끊긴 직후엔 이음을 다시 부르지 않음", d2.get("ok") is False and len(seen()) == 1, len(seen()))
    time.sleep(1.5)
    ctl(delay=0.0, clear_seen=True)
    reset_works()

    # ── 2. PC 화면: 탭 전환·묶음·버튼·이스케이프 ──
    now = datetime.now(KST)
    soon = (now + timedelta(minutes=3)).replace(second=0, microsecond=0)   # 시험 브라우저 시계는 이 30초 전으로 맞춘다
    evil = {"id": 901, "title": "<img src=x onerror=\"window.__xss=1\">악성 제목", "start_at": (now - timedelta(days=2)).strftime("%Y-%m-%dT10:00"),
            "tz_offset": 9, "tz_label": "한국<b>", "duration_min": 30, "location": "<script>window.__xss=2</script>",
            "visibility": "all", "organizer": {"name": "<i>담당</i>"},
            "attendees": [{"name": "<u>참석</u>", "response": "attending", "is_organizer": False}],
            "externals": ["<b>외부</b>"], "me": {"is_organizer": True, "is_attendee": True, "response": "attending"}}
    upcoming = {"id": 902, "title": "[시험] 곧 시작", "start_at": soon.strftime("%Y-%m-%dT%H:%M"), "tz_offset": 9,
                "tz_label": "한국", "duration_min": 30, "location": "대회의실", "visibility": "all",
                "organizer": {"name": "김정락 대표이사"}, "attendees": [], "externals": [],
                "me": {"is_organizer": False, "is_attendee": False, "response": ""}}
    old = {"id": 903, "title": "[시험] 70일 전 회의", "start_at": (now - timedelta(days=70)).strftime("%Y-%m-%dT09:00"),
           "tz_offset": 9, "tz_label": "한국", "duration_min": 60, "location": "", "visibility": "all",
           "organizer": {"name": ""}, "attendees": [], "externals": [],
           "me": {"is_organizer": False, "is_attendee": False, "response": ""}}
    ctl(extra=[evil, upcoming, old], base=True, clear_seen=True, mode="ok")

    c, pg, reqs = new_page(b, viewport={"width": 1280, "height": 900})
    pg.clock.install(time=soon.astimezone(timezone.utc) - timedelta(seconds=30))
    pg.goto(BASE + "/meetings")
    settle(pg)
    ok("2-1 기본 = 회의록 탭 · 카드 요청 없음", pg.locator(".mt-tab.on").inner_text().startswith("📝") and not reqs, reqs)
    pg.locator(".mt-tab", has_text="회의 카드 모아보기").click()
    pg.wait_for_selector(".mc-card")
    time.sleep(0.8)
    ok("2-2 탭 전환 = 주소 ?tab=cards", pg.url == BASE + "/meetings?tab=cards", pg.url)
    n = pg.locator(".mc-card").count()
    ok("2-3 카드 12장 (사진 4 + 예시 6 + 시험 2)", n == 12, n)
    ok("2-4 스크립트 오류 없음·악성 글자 실행 안 됨", pg.evaluate("window.__xss === undefined"))
    evil_card = pg.locator(".mc-card", has_text="악성 제목")
    ok("2-5 악성 제목은 글자로만", '<img src=x onerror="window.__xss=1">악성 제목' in evil_card.inner_text(),
       evil_card.locator(".mc-ttl").inner_text())
    ok("2-6 태그 글자도 글자로", all(s in evil_card.inner_text() for s in ("<script>window.__xss=2</script>", "<i>담당</i>", "<u>참석</u>", "<b>외부</b>", "(한국<b>)")))
    ok("2-7 악성 카드 안에 진짜 태그 없음", evil_card.locator("img, script, i, u, b:not(.mc-sub > b)").count() == 0,
       evil_card.locator("img, script, i, u").count())
    up = pg.locator(".mc-card", has_text="곧 시작")
    ok("2-8 곧 시작 = 🗓 예정 · 진행할 회의 묶음", "예정" in up.locator(".mc-pill").inner_text())
    ok("2-9 70일 전 회의는 처음엔 안 보임", pg.locator(".mc-card", has_text="70일 전").count() == 0)
    link = pg.locator(".mc-card", has_text="먹자").locator("a.mc-go")
    ok("2-10 회의록 보기 = 새 창 · 화면 전환 장치 제외",
       link.get_attribute("target") == "_blank" and link.get_attribute("data-no-swap") is not None and link.get_attribute("rel") == "noopener")
    with c.expect_page() as pop_info:
        link.click()
    pop = pop_info.value
    pop.wait_for_load_state()
    ok("2-11 새 창 = 회의록 양식", pop.url.endswith("/doc") and "회의록" in pop.title(), (pop.url, pop.title()))
    pop.close()
    ok("2-12 원래 창은 카드 탭 그대로", pg.url.endswith("?tab=cards") and pg.locator(".mc-card").count() == 12)

    # 시간이 흐르면 윗줄이 바뀐다 (30초마다 · 바뀐 카드만 다시 그림)
    n_req = len(reqs)
    pg.clock.fast_forward(60 * 1000)
    time.sleep(0.5)
    ok("2-13 시작 시각이 지나면 🔴 회의 중 묶음으로", "회의 중" in pg.locator(".mc-card", has_text="곧 시작").locator(".mc-pill").inner_text(),
       pg.locator(".mc-card", has_text="곧 시작").locator(".mc-pill").inner_text())
    ok("2-14 그 사이 서버 재요청 없음(2분 전)", len(reqs) == n_req, (n_req, len(reqs)))
    pg.clock.fast_forward(65 * 1000)
    time.sleep(1.5)
    ok("2-15 2분 넘으면 회의록 단계 새로 받기", len(reqs) == n_req + 1, (n_req, len(reqs)))

    # 더 보기 (60일씩)
    before = len(seen())
    pg.locator("#mcMore").click()
    pg.wait_for_selector(".mc-card:has-text('70일 전')", timeout=10000)
    last = seen()[-1]
    first_from = pg.evaluate("document.querySelector('.mc-sec small') ? document.querySelector('.mc-sec small').textContent : ''")
    exp_to = (now.date() - timedelta(days=61)).isoformat()
    exp_from = (now.date() - timedelta(days=120)).isoformat()
    ok("2-16 더 보기 = 바로 앞 60일을 물음", last.get("from") == exp_from and last.get("to") == exp_to, last)
    ok("2-17 70일 전 회의가 진행한 회의에 붙음 · 기간 글자 바뀜", pg.locator(".mc-card", has_text="70일 전").count() == 1
       and first_from.startswith(exp_from.replace("-", ".")), first_from)
    ok("2-18 합계 13건", "모두 13건" in pg.locator(".mc-sum").inner_text(), pg.locator(".mc-sum").inner_text())
    # 새로 고침 뒤에도 더 불러온 옛 회의는 남는다
    reset_works()
    pg.locator("#mcReload").click()
    time.sleep(1.5)
    ok("2-19 새로 고침 뒤에도 더 불러온 회의 유지", pg.locator(".mc-card", has_text="70일 전").count() == 1
       and pg.locator(".mc-card").count() == 13, pg.locator(".mc-card").count())

    # z1124: 단추 이름 「📋 회의록 열기」(이음 v807 과 같게 · 대표 지시 2026-09-22) — 옛 이름은 없어야
    _q = pg.locator(".mc-card", has_text="품질 이슈")
    ok("2-19b 진행 중 카드 단추 = 「📋 회의록 열기」 · 옛 「📝 회의록 화면」 없음", _q.locator("a.mc-btn", has_text="📋 회의록 열기").count() == 1
       and pg.locator("a.mc-btn", has_text="회의록 화면").count() == 0, _q.locator("a.mc-btn").all_inner_texts())
    # 회의록 열기 링크 → 화면 전환 장치로 상세
    pg.locator(".mc-card", has_text="품질 이슈").locator("a.mc-btn", has_text="회의록 열기").click()
    pg.wait_for_selector(".mf-wrap", timeout=10000)
    ok("2-20 회의록 화면으로 이동(본문만 바뀜)", "/meetings/" in pg.url and "?tab" not in pg.url, pg.url)
    n_req = len(reqs)
    pg.clock.fast_forward(5 * 60 * 1000)
    time.sleep(1.0)
    ok("2-21 떠난 뒤엔 모아보기 새로 받기가 멈춤", len(reqs) == n_req, (n_req, len(reqs)))
    pg.go_back()
    pg.wait_for_selector(".mc-card", timeout=10000)
    ok("2-22 뒤로 가기 = 카드 탭 다시", pg.url.endswith("?tab=cards"))
    c.close()

    # ── 3. 오류 안내 · 다시 시도 ──
    ctl(mode="403", clear_seen=True)
    reset_works()
    c, pg, reqs = new_page(b, viewport={"width": 1280, "height": 900})
    pg.goto(BASE + "/meetings?tab=cards")
    settle(pg)
    pg.wait_for_selector("[data-mc-retry]", timeout=10000)
    ok("3-1 이음 거부 → 안내 + 다시 시도 버튼", "거부" in pg.locator("#mcBody").inner_text(), pg.locator("#mcBody").inner_text())
    ok("3-2 더 보기 버튼 숨김", pg.locator("#mcMore").is_hidden(),
       pg.evaluate("getComputedStyle(document.getElementById('mcMore')).display"))
    ctl(mode="viewer")
    pg.locator("[data-mc-retry]").click()
    pg.wait_for_function("document.getElementById('mcBody').textContent.indexOf('사번') >= 0", timeout=10000)
    ok("3-3 다시 시도 → 직원 못 찾음 안내", "사번" in pg.locator("#mcBody").inner_text())
    ctl(mode="ok")
    pg.locator("[data-mc-retry]").click()
    pg.wait_for_selector(".mc-card", timeout=10000)
    ok("3-4 이음이 돌아오면 다시 시도로 카드", pg.locator(".mc-card").count() == 12, pg.locator(".mc-card").count())
    # 카드가 있는데 새로 고침이 실패하면 → 알림만, 카드 유지
    ctl(mode="403")
    reset_works()
    msgs = []
    pg.once("dialog", lambda dlg: (msgs.append(dlg.message), dlg.accept()))
    pg.locator("#mcReload").click()
    for _ in range(100):
        if msgs:
            break
        pg.wait_for_timeout(100)
    time.sleep(0.3)
    ok("3-5 새로 고침 실패 → 알림 · 카드 그대로", msgs and "거부" in msgs[0] and pg.locator(".mc-card").count() == 12, msgs)
    ctl(mode="ok")
    c.close()

    # 불러오는 동안에도 더 보기 버튼은 안 보인다
    ctl(delay=3.0)
    reset_works()
    c, pg, reqs = new_page(b, viewport={"width": 1280, "height": 900})
    pg.goto(BASE + "/meetings?tab=cards", wait_until="domcontentloaded")
    time.sleep(0.5)
    ok("3-6 불러오는 중 안내 · 더 보기 숨김", "불러오는 중" in pg.locator("#mcBody").inner_text() and pg.locator("#mcMore").is_hidden())
    pg.wait_for_selector(".mc-card", timeout=15000)
    ok("3-7 다 불러오면 더 보기 보임", pg.locator("#mcMore").is_visible())
    c.close()
    ctl(delay=0.0)

    # ── 3b. 이음이 잘라 보낼 때(truncated · 시작이 이른 회의부터 빠짐) — 더 보기로 빠짐없이 ──
    ctl(mode="ok", base=True, extra=[], limit=5, clear_seen=True)
    reset_works()
    c, pg, reqs = new_page(b, viewport={"width": 1280, "height": 900})
    pg.goto(BASE + "/meetings?tab=cards")
    settle(pg)
    pg.wait_for_selector(".mc-card", timeout=10000)
    ok("3b-1 잘린 첫 화면 = 5장 + 이어보기 안내", pg.locator(".mc-card").count() == 5 and "이어서" in pg.locator("#mcMoreNote").inner_text(),
       (pg.locator(".mc-card").count(), pg.locator("#mcMoreNote").inner_text()))
    first_seen = seen()[-1]
    oldest_first = min(pg.evaluate("Array.from(document.querySelectorAll('.mc-card .mc-sub b')).map(e => e.textContent.slice(0, 10))"))
    counts = [5]
    for _ in range(6):
        if pg.locator("#mcMore").is_hidden():
            break
        before_n = pg.locator(".mc-card").count()
        note_before = pg.locator("#mcMoreNote").inner_text()
        pg.locator("#mcMore").click()
        for _w in range(100):
            if pg.locator("#mcMore").is_enabled() and pg.locator("#mcMore").inner_text().startswith("▼"):
                break
            pg.wait_for_timeout(100)
        counts.append(pg.locator(".mc-card").count())
        if "이어서" not in pg.locator("#mcMoreNote").inner_text() and counts[-1] == counts[-2]:
            break
    asks = [(x.get("from"), x.get("to")) for x in seen()]
    ok("3b-2 더 보기를 이어 누르면 빠짐없이 10장", counts[-1] == 10, (counts, asks))
    ids = pg.evaluate("Array.from(document.querySelectorAll('.mc-card .mc-ttl')).map(e => e.textContent)")
    ok("3b-3 같은 회의가 두 번 나오지 않음", len(ids) == len(set(ids)), ids)
    more_asks = [a for a in asks if a[1] != first_seen["to"]]   # 첫 기간 요청(시험 크롬이 한 번 더 읽음)은 뺀다
    ok("3b-4 이어 묻기 = 잘린 날짜(받은 것 중 가장 이른 날)를 포함해서",
       more_asks and more_asks[0][1] == oldest_first and more_asks[0][0] < first_seen["from"], (oldest_first, more_asks[:3]))
    # 다 불러온 뒤 새로 고침 — 첫 기간은 다시 잘려 와도 더 불러 둔 회의는 남는다
    reset_works()
    label_before = pg.evaluate("document.querySelector('.mc-sec small') ? document.querySelector('.mc-sec small').textContent : ''")
    pg.locator("#mcReload").click()
    for _w in range(100):
        if pg.locator("#mcReload").is_enabled():
            break
        pg.wait_for_timeout(100)
    time.sleep(0.5)
    label_after = pg.evaluate("document.querySelector('.mc-sec small') ? document.querySelector('.mc-sec small').textContent : ''")
    ok("3b-5 새로 고침 뒤에도 10장 · 기간 글자 그대로", pg.locator(".mc-card").count() == 10 and label_before == label_after,
       (pg.locator(".mc-card").count(), label_before, label_after))
    c.close()
    ctl(limit=0)
    reset_works()

    # ── 4. 빈 목록 ──
    ctl(base=False, extra=[], clear_seen=True)
    reset_works()
    c, pg, reqs = new_page(b, viewport={"width": 1280, "height": 900})
    pg.goto(BASE + "/meetings?tab=cards")
    settle(pg)
    pg.wait_for_selector(".mc-sum", timeout=10000)
    t = pg.locator("#mcBody").inner_text()
    ok("4-1 회의 0건 → 안내 두 줄", "예정된 회의가 없습니다" in t and "이 기간에 지난 회의가 없습니다" in t and "지금 회의 중" not in t, t[:120])
    c.close()
    ctl(base=True, extra=[])
    reset_works()

    # ── 5. 휴대폰 ──
    c, pg, reqs = new_page(b, viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    pg.goto(BASE + "/meetings?tab=cards")
    pg.wait_for_selector(".mc-card", timeout=10000)
    settle(pg)
    mx = pg.evaluate("Math.max(...Array.from(document.querySelectorAll('.mt-tabs, #mcWrap, #mcWrap *')).map(e => e.getBoundingClientRect().right))")
    ok("5-1 휴대폰 본문 가로 넘침 없음", mx <= 390.5, mx)
    tabs = pg.evaluate("Array.from(document.querySelectorAll('.mt-tab')).map(e => Math.round(e.getBoundingClientRect().width))")
    ok("5-2 휴대폰 탭 두 개 반씩", len(tabs) == 2 and abs(tabs[0] - tabs[1]) <= 2, tabs)
    pg.locator(".mt-tab", has_text="회의록").first.tap()
    pg.wait_for_selector(".kpi-card", timeout=10000)
    ok("5-3 휴대폰 탭 누르기 → 회의록 목록", pg.url.endswith("/meetings"))
    c.close()
    b.close()

print("errors:", json.dumps(errs, ensure_ascii=False)[:1500])
ok("9-1 콘솔 오류 없음", not errs, errs[:3])
print("결과: %d/%d 통과" % (sum(1 for _, v in res if v), len(res)))
