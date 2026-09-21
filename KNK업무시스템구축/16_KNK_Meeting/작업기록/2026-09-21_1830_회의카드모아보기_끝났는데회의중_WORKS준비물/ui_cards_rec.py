# -*- coding: utf-8 -*-
"""z1119 화면 시험 — WORKS 「🗓 회의 카드 모아보기」 탭: 끝났는데 「지금 회의 중」 고침 (이음 v815 와 같은 글·규칙)

실제 크롬으로 /meetings?tab=cards 를 열고, 탭이 부르는 /api/meetings/msg-cards 응답을 경우별로 만들어 넣는다.
브라우저 시계를 고정(page.clock)해 끝 시각을 넘기면 30초 다시 그리기 때 윗줄·아래 줄이 함께 바뀌는지도 본다.
사용: py -3.12 ui_cards_rec.py [포트=8936]
"""
import json
import sys
from datetime import datetime, timedelta, timezone

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8936
BASE = "http://localhost:%d" % PORT
KST = timezone(timedelta(hours=9))
T0 = datetime.now(KST).replace(hour=14, minute=0, second=30, microsecond=0)   # 브라우저 시계 = 오늘 14:00:30 KST
WHO = "김동후 대표이사 총괄"
OK, NG = [], []


def ok(name, cond, extra=""):
    (OK if cond else NG).append(name)
    print(("PASS " if cond else "FAIL ") + name + ((" · " + str(extra)[:170]) if extra != "" else ""), flush=True)


def card(i, title, start, dur, stage="started", **mn):
    m = {"stage": stage, "can_view": True, "started_by": WHO, "url": "/meetings/%d" % i}
    m.update(mn)
    return {"id": i, "title": title, "start_at": start.strftime("%Y-%m-%dT%H:%M"), "tz_offset": 9, "tz_label": "한국",
            "duration_min": dur, "location": "", "visibility": "all", "organizer": {"name": "등록담당"},
            "attendees": [], "externals": [], "me": {"is_organizer": False, "is_attendee": True, "response": "attending"},
            "minutes": m}


H = lambda h=0, m=0: T0.replace(second=0) + timedelta(hours=h, minutes=m)
ITEMS = [
    card(1, "A 시작만·끝남", H(-2), 60, recording=False, rec_secs=0),            # 12:00~13:00 · 끝남
    card(2, "B 시작만·진행 중", H(0, -10), 60, recording=False, rec_secs=0),       # 13:50~14:50
    card(3, "C 녹음 중·끝남", H(-2), 60, recording=True, rec_secs=600),           # 끝났지만 녹음 중 → 12시간 회의 중
    card(4, "D 녹음 중 30초", H(0, -10), 60, recording=True, rec_secs=30),
    card(5, "E 옛 응답(칸 없음)·끝남", H(-2), 60),                                 # recording 칸 없음 → 예전 그대로
    card(6, "F 시작 전에 누름", H(0, 10), 60, recording=False, rec_secs=0),        # 14:10~ · 누른 회의는 회의 중
    card(7, "G 녹음 중·13시간 전 끝", H(-14), 60, recording=True, rec_secs=900),  # 12시간 지남 → 종료
    card(8, "H 정리 끝", H(-3), 60, stage="done", recording=False, rec_secs=0),
    card(9, "I 곧 끝남(시작만)", H(-1, 1), 60, recording=False, rec_secs=0),       # 13:01~14:01 · 30초 뒤 끝
]


def payload():
    d = T0.date()
    return json.dumps({"ok": True, "from": (d - timedelta(days=7)).isoformat(), "to": (d + timedelta(days=14)).isoformat(),
                       "today": d.isoformat(), "items": ITEMS, "truncated": False})


def info(p, i):
    return p.evaluate("""(t) => {
        const a = [...document.querySelectorAll('article.mc-card')].find(x => (x.querySelector('.mc-ttl')||{}).textContent === t);
        if (!a) return null;
        const sec = a.closest('section, .mc-sec, div');
        let group = '';
        let n = a; while (n && n !== document.body) { const h = n.previousElementSibling;
          if (n.parentElement && n.parentElement.querySelector) {}
          n = n.parentElement; }
        return { pill: (a.querySelector('.mc-pill')||{}).textContent || '', cls: a.className,
                 line: (a.querySelector('.mc-state')||{}).textContent || '',
                 dim: !!(a.querySelector('.mc-state.dim')) };
    }""", i)


def group_of(p, title):
    """카드가 들어 있는 묶음 제목(🔴 지금 회의 중 / 🔜 진행할 회의 / ✅ 진행한 회의)."""
    return p.evaluate("""(t) => {
        const a = [...document.querySelectorAll('article.mc-card')].find(x => (x.querySelector('.mc-ttl')||{}).textContent === t);
        if (!a) return '';
        let n = a.previousElementSibling;                       // 묶음 제목 = 카드 앞쪽 가장 가까운 .mc-sec
        while (n && !(n.classList && n.classList.contains('mc-sec'))) n = n.previousElementSibling;
        return n ? (n.childNodes[0].textContent || '').trim() : '';
    }""", title)


def main():
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True)
        c = br.new_context(service_workers="block", viewport={"width": 1280, "height": 1400})
        c.add_init_script("document.addEventListener('DOMContentLoaded',()=>{const s=document.createElement('style');"
                          "s.textContent='#worksInstallHint{display:none !important}';document.head.appendChild(s);});")
        p = c.new_page()
        errs = []
        p.on("pageerror", lambda e: errs.append(str(e)))
        p.route("**/api/meetings/msg-cards*", lambda r: r.fulfill(status=200, content_type="application/json", body=payload()))
        p.clock.install(time=T0)
        p.goto(BASE + "/meetings?tab=cards", wait_until="domcontentloaded")
        p.wait_for_selector("article.mc-card", timeout=20000)
        p.wait_for_timeout(500)

        print("\n■ ① 경우별 윗줄·아래 줄", flush=True)
        a = info(p, "A 시작만·끝남")
        ok("A 시작만·끝남 → 윗줄 ✅ 회의 종료", "회의 종료" in a["pill"], a)
        ok("A → 아래 줄 「⏹ 회의 끝남 · 이름 · 녹음 없음」", a["line"] == "⏹ 회의 끝남 · %s · 녹음 없음" % WHO, a["line"])
        ok("A → 「✅ 진행한 회의」 묶음", group_of(p, "A 시작만·끝남").startswith("✅ 진행한 회의"), group_of(p, "A 시작만·끝남"))

        b = info(p, "B 시작만·진행 중")
        ok("B 시작만·진행 중 → 윗줄 🔴 회의 중", "회의 중" in b["pill"], b)
        ok("B → 아래 줄 「🔴 회의 진행 중 · 이름 · 녹음 안 됨」", b["line"] == "🔴 회의 진행 중 · %s · 녹음 안 됨" % WHO, b["line"])
        ok("B → 「🔴 지금 회의 중」 묶음", group_of(p, "B 시작만·진행 중").startswith("🔴 지금 회의 중"), group_of(p, "B 시작만·진행 중"))

        cc = info(p, "C 녹음 중·끝남")
        ok("C 녹음 중·끝남 → 윗줄 🔴 회의 중(12시간 연장 그대로)", "회의 중" in cc["pill"], cc)
        ok("C → 「🔴 녹음 중 · 이름 · 10분 저장됨」", cc["line"] == "🔴 녹음 중 · %s · 10분 저장됨" % WHO, cc["line"])

        d = info(p, "D 녹음 중 30초")
        ok("D 녹음 30초 → 「🔴 녹음 중 · 이름」(1분 미만은 분 없음)", d["line"] == "🔴 녹음 중 · %s" % WHO, d["line"])

        e = info(p, "E 옛 응답(칸 없음)·끝남")
        ok("E 옛 응답 → 윗줄 예전 그대로(🔴 회의 중)", "회의 중" in e["pill"], e)
        ok("E 옛 응답 → 아래 줄 예전 글(「… 녹음」)", e["line"] == "🔴 회의 진행 중 · %s 녹음" % WHO, e["line"])

        f = info(p, "F 시작 전에 누름")
        ok("F 시작 전에 누름 → 🔴 회의 중(누른 회의는 그대로)", "회의 중" in f["pill"], f)
        ok("F → 「진행 중 · 녹음 안 됨」", f["line"] == "🔴 회의 진행 중 · %s · 녹음 안 됨" % WHO, f["line"])

        g = info(p, "G 녹음 중·13시간 전 끝")
        ok("G 녹음 중이어도 끝나고 12시간 지남 → ✅ 회의 종료", "회의 종료" in g["pill"], g)

        h = info(p, "H 정리 끝")
        ok("H 정리 끝 → ✅ 회의 종료(그대로)", "회의 종료" in h["pill"], h)
        ok("H → 「📋 회의록 보기」 그대로", p.evaluate("""() => { const a=[...document.querySelectorAll('article.mc-card')]
            .find(x => (x.querySelector('.mc-ttl')||{}).textContent === 'H 정리 끝'); return !!(a && a.querySelector('.mc-go')); }"""))
        ok("A 는 흐린 글(끝난 것)", a["dim"], a)

        print("\n■ ② 끝 시각이 지나면 30초 다시 그리기 때 두 줄이 함께", flush=True)
        i0 = info(p, "I 곧 끝남(시작만)")
        ok("I 끝나기 전 → 🔴 회의 중 · 「진행 중 · 녹음 안 됨」",
           "회의 중" in i0["pill"] and i0["line"].endswith("· 녹음 안 됨"), i0)
        p.clock.fast_forward(95000)          # 14:02:05 — 끝(14:01:00)을 넘기고 30초 틱이 돈다
        p.wait_for_timeout(300)
        i1 = info(p, "I 곧 끝남(시작만)")
        ok("I 끝난 뒤 → 윗줄 ✅ 회의 종료", "회의 종료" in i1["pill"], i1)
        ok("I 끝난 뒤 → 아래 줄도 「⏹ 회의 끝남 · 녹음 없음」(두 줄 함께)",
           i1["line"] == "⏹ 회의 끝남 · %s · 녹음 없음" % WHO, i1["line"])
        ok("I → 「✅ 진행한 회의」 묶음으로 옮겨감", group_of(p, "I 곧 끝남(시작만)").startswith("✅ 진행한 회의"),
           group_of(p, "I 곧 끝남(시작만)"))
        b1 = info(p, "B 시작만·진행 중")
        ok("B 는 아직 회의 시간 안 → 그대로 🔴 회의 중", "회의 중" in b1["pill"], b1)

        ok("화면 스크립트 오류 없음", not errs, errs[:2])
        br.close()

    print("\n" + "=" * 60)
    print("합계: 통과 %d · 실패 %d" % (len(OK), len(NG)))
    for n in NG:
        print("  ❌ " + n)
    sys.exit(1 if NG else 0)


main()
