# -*- coding: utf-8 -*-
"""z1122 화면 시험 — 회의록 삭제 두 번 확인 · 권한 · 이음 회의 함께 지우기 결과 알림
+ 「🗓 회의 카드 모아보기」: 녹음하던 본인 「🎙 이어서 녹음」 · 카드 빈 곳 누르기 · 지운 회의 바로 빠짐 · 아이폰 안내 글
실제 크롬 · 서버 = run_del_app.py(가짜 이음). 사용: py -3.12 ui_del.py <seed_del.json 폴더>"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

SEED = json.load(io.open(os.path.join(sys.argv[1], "seed_del.json"), encoding="utf-8"))
IDS, CEO, OWNER, ORG, OTHER = SEED["ids"], SEED["ceo"], SEED["owner"], SEED["org"], SEED["other"]
BASE = "http://localhost:%d" % SEED["port"]
UA_IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
          "Version/18.2 Mobile/15E148 Safari/604.1")
UA_PC = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36")
HIDE = ("document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style');"
        "s.textContent = '#worksInstallHint{display:none !important}'; document.head.appendChild(s); });")
OK, NG, ERRS = [], [], []


def ok(name, cond, extra=""):
    (OK if cond else NG).append(name)
    print(("PASS " if cond else "FAIL ") + name + ((" · " + str(extra)[:220]) if extra != "" else ""), flush=True)


def ctx(br, uid, phone=False):
    c = br.new_context(service_workers="block", user_agent=UA_IOS if phone else UA_PC,
                       viewport={"width": 390, "height": 844} if phone else {"width": 1280, "height": 900},
                       is_mobile=phone, has_touch=phone)
    c.add_cookies([{"name": "tuser", "value": str(uid), "url": BASE}])
    c.add_init_script(HIDE)
    return c


class Dialogs:
    """누를 답을 차례로 — 'accept'/'dismiss'. 뜬 글은 msgs 에 쌓인다(답이 떨어지면 dismiss)."""
    def __init__(self, page):
        self.plan, self.msgs = [], []
        page.on("dialog", self._on)

    def _on(self, d):
        self.msgs.append((d.type, d.message))
        (d.accept() if (self.plan.pop(0) if self.plan else "dismiss") == "accept" else d.dismiss())

    def set(self, *plan):
        self.plan, self.msgs = list(plan), []


def api(p, path, method="GET"):
    return p.evaluate("""async ([u, m]) => { const r = await fetch(u, {method: m}); let j = null; try { j = await r.json(); } catch (e) {}
                        return {status: r.status, url: r.url, json: j}; }""", [path, method])


def exists(p, mid):
    r = api(p, "/api/meeting/%d/rec-status" % mid)
    return r["status"] == 200


def open_detail(c, mid):
    p = c.new_page()
    p.on("pageerror", lambda e: ERRS.append(str(e)))
    dl = Dialogs(p)
    p.goto("%s/meetings/%d" % (BASE, mid), wait_until="domcontentloaded")
    p.wait_for_timeout(1200)
    return p, dl


def main():
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True)

        # ══════════ ① 두 번 확인(이음과 무관한 회의 · 아이폰 · 작성자) ══════════
        print("\n■ ① 두 번 확인 — 취소하면 그대로 · 둘 다 확인해야 지워짐 (아이폰 · 작성자)", flush=True)
        c = ctx(br, OWNER, phone=True)
        p, dl = open_detail(c, IDS["D1"])
        ok("작성자 화면에 🗑 삭제 단추", p.locator("#btnDelete").count() == 1)
        dl.set("dismiss")
        p.locator("#btnDelete").click(); p.wait_for_timeout(800)
        m1 = dl.msgs[0][1] if dl.msgs else ""
        ok("첫 확인 창 = 「🗑 이 회의록을 삭제할까요?」 · 제목 · 지워지는 것", len(dl.msgs) == 1 and "🗑 이 회의록을 삭제할까요?" in m1
           and "[시험] D1 WORKS 에서만" in m1 and "녹음·음성 글자·정리·결정·할 일" in m1, m1[:120])
        ok("이음과 무관한 회의 → 이음 회의 문구 없음", "이음 회의" not in m1)
        ok("첫 창 취소 → 그대로", exists(p, IDS["D1"]) and "/meetings/%d" % IDS["D1"] in p.url)
        dl.set("accept", "dismiss")
        p.locator("#btnDelete").click(); p.wait_for_timeout(800)
        m2 = dl.msgs[1][1] if len(dl.msgs) > 1 else ""
        ok("🔴 두 번째 확인 창 = 「⚠ 정말 삭제할까요? … 되돌릴 수 없습니다」", len(dl.msgs) == 2 and "⚠ 정말 삭제할까요?" in m2
           and "되돌릴 수 없습니다" in m2, m2[:100])
        ok("두 번째 창 취소 → 그대로", exists(p, IDS["D1"]))
        dl.set("accept", "accept")
        p.locator("#btnDelete").click()
        p.wait_for_url("**/meetings", timeout=15000); p.wait_for_timeout(800)
        ok("둘 다 확인 → 지우고 회의록 목록으로", p.url.rstrip("/").endswith("/meetings") and len(dl.msgs) == 2, p.url)
        ok("목록에서 사라짐", "[시험] D1 WORKS 에서만" not in p.locator("body").inner_text())
        ok("서버에서도 없음", not exists(p, IDS["D1"]))
        c.close()

        # ══════════ ② 대표 — 이음 회의까지 함께 ══════════
        print("\n■ ② 대표가 지움 — 이음 회의도 함께(가짜 이음 ok)", flush=True)
        c = ctx(br, CEO)
        p, dl = open_detail(c, IDS["D2"])
        dl.set("accept", "accept")
        p.locator("#btnDelete").click()
        p.wait_for_url("**/meetings", timeout=15000); p.wait_for_timeout(800)
        ok("첫 창에 「🗓 이음 회의도 함께 지워집니다」", "🗓 이음 회의도 함께 지워집니다" in (dl.msgs[0][1] if dl.msgs else ""), dl.msgs[:1])
        ok("두 번째 창에 「이음 회의까지」", "이음 회의까지" in (dl.msgs[1][1] if len(dl.msgs) > 1 else ""))
        ok("둘 다 지워지면 추가 알림 없음(창 2개뿐)", len(dl.msgs) == 2, [t for t, _ in dl.msgs])
        calls = api(p, "/__test/calls")["json"]
        last = (calls.get("calls") or [{}])[-1]
        ok("이음에 「지워 주세요」 — 이음 회의 번호·대표 사번·WORKS 번호·공유키", last.get("msg_meeting_id") == 9401
           and last.get("employee_no") == "T0001" and last.get("works_meeting_id") == IDS["D2"] and last.get("key_ok") is True, last)
        ok("회의록도 지워짐", not exists(p, IDS["D2"]))
        c.close()

        # ══════════ ③ 작성자(등록자 아님) — 이음이 거절 → 회의록만 ══════════
        print("\n■ ③ 작성자(등록자 아님) — 회의록만 지우고 까닭 알림", flush=True)
        c = ctx(br, OWNER)
        p, dl = open_detail(c, IDS["D3"])
        dl.set("accept", "accept", "accept")
        p.locator("#btnDelete").click()
        p.wait_for_url("**/meetings", timeout=15000); p.wait_for_timeout(800)
        ok("첫 창에 「🗓 이음 회의는 남습니다」", "🗓 이음 회의는 남습니다" in (dl.msgs[0][1] if dl.msgs else ""), dl.msgs[:1])
        ok("결과 알림 = 등록한 사람(또는 관리자)만", len(dl.msgs) == 3 and dl.msgs[2][0] == "alert"
           and "등록한 사람(또는 관리자)만" in dl.msgs[2][1], dl.msgs[2:] if len(dl.msgs) > 2 else dl.msgs)
        ok("회의록은 지워짐", not exists(p, IDS["D3"]))
        c.close()

        # ══════════ ④ 이음 입구가 아직 없음 → 회의록만 ══════════
        print("\n■ ④ 이음 삭제 입구 없음(세션 10 배포 전) — 회의록만 · 알림", flush=True)
        c = ctx(br, OWNER)
        p, dl = open_detail(c, IDS["D4"])
        dl.set("accept", "accept", "accept")
        p.locator("#btnDelete").click()
        p.wait_for_url("**/meetings", timeout=15000); p.wait_for_timeout(800)
        ok("등록자 본인 → 첫 창에 「이음 회의도 함께」", "🗓 이음 회의도 함께 지워집니다" in (dl.msgs[0][1] if dl.msgs else ""))
        ok("결과 알림 = 이음 쪽 준비 중", len(dl.msgs) == 3 and "이음 쪽 준비 중" in dl.msgs[2][1], dl.msgs[2:] if len(dl.msgs) > 2 else dl.msgs)
        ok("회의록은 지워짐", not exists(p, IDS["D4"]))
        c.close()

        # ══════════ ⑤ 이음 꺼짐 → 아무것도 안 지움 ══════════
        print("\n■ ⑤ 이음에 못 닿음 — 지우지 않고 알림 · 단추 다시 쓸 수 있음", flush=True)
        c = ctx(br, OWNER, phone=True)
        p, dl = open_detail(c, IDS["D5"])
        dl.set("accept", "accept", "accept")
        p.locator("#btnDelete").click(); p.wait_for_timeout(2500)
        ok("알림 = 「회의록을 지우지 않았습니다」", len(dl.msgs) == 3 and "회의록을 지우지 않았습니다" in dl.msgs[2][1], dl.msgs[2:] if len(dl.msgs) > 2 else dl.msgs)
        ok("🔴 회의록 그대로 · 이 화면 그대로", exists(p, IDS["D5"]) and "/meetings/%d" % IDS["D5"] in p.url, p.url)
        ok("삭제 단추 다시 누를 수 있음", p.locator("#btnDelete").is_enabled())
        c.close()

        # ══════════ ⑥ 권한 ══════════
        print("\n■ ⑥ 권한 — 등록 담당·다른 직원은 삭제 단추 없음 · 서버도 403", flush=True)
        for uid, nm in ((ORG, "등록 담당"), (OTHER, "다른 직원")):
            c = ctx(br, uid)
            p, dl = open_detail(c, IDS["D6"])
            ok(f"{nm} → 🗑 삭제 단추 없음", p.locator("#btnDelete").count() == 0 and "/meetings/%d" % IDS["D6"] in p.url, p.url)
            r = api(p, "/api/meeting/%d" % IDS["D6"], "DELETE")
            ok(f"{nm} → 직접 요청해도 403", r["status"] == 403, r)
            c.close()
        c = ctx(br, CEO)
        p, dl = open_detail(c, IDS["D6"])
        ok("회의록 그대로(위 거절 뒤)", exists(p, IDS["D6"]))
        c.close()

        # ══════════ ⑦ 모아보기 — 녹음하던 본인 「🎙 이어서 녹음」 · 카드 누르기 ══════════
        print("\n■ ⑦ 「🗓 회의 카드 모아보기」 — 본인 「🎙 이어서 녹음」 · 카드 빈 곳 누르기 (작성자=안지연)", flush=True)
        c = ctx(br, OWNER)
        p = c.new_page(); p.on("pageerror", lambda e: ERRS.append(str(e)))
        p.goto(BASE + "/meetings?tab=cards", wait_until="domcontentloaded")
        p.wait_for_selector("article.mc-card", timeout=20000); p.wait_for_timeout(600)

        def cinfo(title):
            return p.evaluate("""(t) => { const a = [...document.querySelectorAll('article.mc-card')]
                  .find(x => ((x.querySelector('.mc-ttl')||{}).textContent||'') === t);
                if (!a) return null;
                const b = a.querySelector('.mc-min a.mc-btn');
                return {tap: a.classList.contains('tap'), cursor: getComputedStyle(a).cursor,
                        btn: b ? b.textContent.trim() : '', href: b ? b.getAttribute('href') : '', target: b ? (b.getAttribute('target')||'') : '',
                        bg: b ? getComputedStyle(b).backgroundColor : ''}; }""", title)
        r1, r2, r3, r4, r5 = (cinfo("C-R1 녹음 중·본인"), cinfo("C-R2 정리 끝+녹음 중·본인"), cinfo("C-R3 정리 끝"),
                              cinfo("C-R4 회의록 없음"), cinfo("C-R5 대표가 녹음 중"))
        ok("녹음하던 본인 → 「🎙 이어서 녹음」 · 녹음 화면", r1 and r1["btn"] == "🎙 이어서 녹음" and r1["href"] == "/meetings/%d" % IDS["R1"], r1)
        ok("「🎙 이어서 녹음」은 빨강(이음 v817 과 같은 #dc2626)", r1 and r1["bg"] == "rgb(220, 38, 38)", r1 and r1["bg"])
        ok("정리 끝 + 녹음 중(본인) → 「🎙 이어서 녹음」 · 주소 = 녹음 화면(양식 아님)", r2 and r2["btn"] == "🎙 이어서 녹음"
           and r2["href"] == "/meetings/%d" % IDS["R2"], r2)
        ok("정리 끝 → 「📋 회의록 보기」(새 창 · 양식) 그대로", r3 and r3["btn"] == "📋 회의록 보기" and r3["href"].endswith("/doc") and r3["target"] == "_blank", r3)
        ok("남(대표)이 녹음 중 → 「📝 회의록 화면」 그대로", r5 and r5["btn"] == "📝 회의록 화면", r5)
        ok("회의록 단추가 있는 카드만 손가락(tap)", r1["tap"] and r1["cursor"] == "pointer" and r4 and not r4["tap"] and r4["cursor"] != "pointer", (r1["cursor"], r4))
        # 글자 고르기 — 끌어서 고르면 이동하지 않는다
        sub = p.locator("article.mc-card.tap", has_text="C-R1 녹음 중·본인").locator(".mc-sub").first
        bb = sub.bounding_box()
        p.mouse.move(bb["x"] + 4, bb["y"] + bb["height"] / 2); p.mouse.down()
        p.mouse.move(bb["x"] + bb["width"] - 6, bb["y"] + bb["height"] / 2, steps=6); p.mouse.up()
        p.wait_for_timeout(900)
        ok("글자를 끌어 고르면 이동하지 않음", "tab=cards" in p.url, p.url)
        p.evaluate("() => window.getSelection().removeAllRanges()")
        # 회의록 없는 카드 — 눌러도 그대로
        p.locator("article.mc-card", has_text="C-R4 회의록 없음").locator(".mc-ttl").click()
        p.wait_for_timeout(900)
        ok("회의록 단추 없는 카드 → 눌러도 그대로", "tab=cards" in p.url, p.url)
        # 정리 끝 카드 — 빈 곳 = 「📋 회의록 보기」와 같게 새 창
        with c.expect_page(timeout=8000) as np:
            p.locator("article.mc-card", has_text="C-R3 정리 끝").locator(".mc-sub").first.click(position={"x": 2, "y": 2})
        newp = np.value; newp.wait_for_load_state("domcontentloaded")
        ok("정리 끝 카드 빈 곳 → 새 창에 회의록 양식(단추와 같게)", newp.url.endswith("/meetings/%d/doc" % IDS["R3"]), newp.url)
        newp.close()
        ok("원래 탭은 그대로", "tab=cards" in p.url, p.url)
        # 본인 녹음 카드 — 빈 곳 = 「🎙 이어서 녹음」과 같게 같은 창 · 도착 화면 맨 위 상자
        p.locator("article.mc-card", has_text="C-R1 녹음 중·본인").locator(".mc-ttl").click()
        p.wait_for_url("**/meetings/%d" % IDS["R1"], timeout=15000); p.wait_for_timeout(1200)
        ok("🔴 녹음 카드 빈 곳 → 녹음 화면으로(단추와 같게)", p.url.endswith("/meetings/%d" % IDS["R1"]), p.url)
        ok("도착 화면 맨 위 「🔴 녹음 중이던 회의 · 🎙 이어서 녹음」(z1120)",
           p.evaluate("() => { const b = document.getElementById('recResume'); return !!b && b.offsetHeight > 0; }"))
        c.close()

        # ══════════ ⑧ 지운 회의 — 모아보기에서 바로 빠짐 ══════════
        print("\n■ ⑧ 지운 회의는 모아보기에서 바로 빠진다(30초 저장본 비움)", flush=True)
        c = ctx(br, CEO)
        p = c.new_page(); p.on("pageerror", lambda e: ERRS.append(str(e)))
        dl = Dialogs(p)
        p.goto(BASE + "/meetings?tab=cards", wait_until="domcontentloaded")
        p.wait_for_selector("article.mc-card", timeout=20000); p.wait_for_timeout(500)
        ok("지우기 전 — 모아보기에 C-D7 있음", p.locator("article.mc-card", has_text="C-D7").count() == 1)
        p.goto("%s/meetings/%d" % (BASE, IDS["D7"]), wait_until="domcontentloaded"); p.wait_for_timeout(1000)
        dl.set("accept", "accept")
        p.locator("#btnDelete").click()
        p.wait_for_url("**/meetings", timeout=15000); p.wait_for_timeout(500)
        p.goto(BASE + "/meetings?tab=cards", wait_until="domcontentloaded")
        p.wait_for_selector("article.mc-card", timeout=20000); p.wait_for_timeout(500)
        ok("🔴 지운 뒤 바로 — 모아보기에서 C-D7 사라짐", p.locator("article.mc-card", has_text="C-D7").count() == 0)
        ok("다른 카드는 그대로", p.locator("article.mc-card", has_text="C-R3 정리 끝").count() == 1)
        c.close()

        # ══════════ ⑨ 아이폰 안내 글 ══════════
        print("\n■ ⑨ 아이폰 안내 — 이음 카드 「🎙 이어서 녹음」(v817)", flush=True)
        c = ctx(br, OWNER, phone=True)
        p, dl = open_detail(c, IDS["D6"])
        t = p.evaluate("() => (document.getElementById('recPlatNote')||{}).textContent || ''")
        ok("「이음 회의 카드의 「🎙 이어서 녹음」(또는 카드 빈 곳)」", "이음 회의 카드의 「🎙 이어서 녹음」(또는 카드 빈 곳)" in t, t[-150:])
        ok("옛 글(「📋 회의록 열기」) 없음 · 기존 안내 그대로", "「📋 회의록 열기」" not in t and "그동안은 녹음되지 않습니다" in t)
        c.close()

        ok("화면 스크립트 오류 없음", not ERRS, ERRS[:3])
        br.close()

    print("\n" + "=" * 64)
    print("합계: 통과 %d · 실패 %d" % (len(OK), len(NG)))
    for n in NG:
        print("  ❌ " + n)
    sys.exit(1 if NG else 0)


main()
