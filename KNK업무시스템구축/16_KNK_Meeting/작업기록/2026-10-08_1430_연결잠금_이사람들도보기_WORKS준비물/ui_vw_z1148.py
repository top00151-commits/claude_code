# -*- coding: utf-8 -*-
"""z1147·z1148 화면 시험
사용: py -3.12 ui_vw_z1148.py [포트=8941]

z1147 ① 「🔗 연결」 칸이 회색으로 잠겼다 — 화면도, 주소로 직접 불러도
z1148 ② 지금은 참석 안 한 사람이 볼 길이 없다(출발점)
      ③ 「이 사람들도 보기」로 넣는다
      ④ 🔴 **두 층 다** — 상세도 열리고 회의록 **목록에도** 보인다
      ⑤ 🔴 회의록을 저장해도 명단이 안 사라진다(참석자 칸에 안 넣은 까닭)
      ⑥ 빼면 다시 안 보인다 · 권한 없는 사람은 명단을 못 고친다
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8941
BASE = "http://127.0.0.1:%d" % PORT
SEED = json.load(io.open(os.path.join(HERE, "seed_vw.json"), encoding="utf-8"))
MID = SEED["mid"]
TITLE = "드림텍VINA MES 관련"

OK = FAIL = 0
FAILS = []


def chk(cond, name, extra=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [PASS] " + name + (" · " + str(extra) if extra else ""))
    else:
        FAIL += 1
        FAILS.append(name)
        print("  [FAIL] " + name + " " + str(extra))


def as_user(ctx, uid, page=None):
    """그 사람으로 바꾼다. 🔴 **새 창**을 연다 — 같은 창을 쓰면 sessionStorage 의 페이지 탭
    (knkPtabs989)에 앞사람이 열어 둔 회의 제목이 남아 「목록에 보인다」로 잘못 읽힌다.
    서버 응답에는 없다(실측: request.get 으로는 안 나온다). 사람마다 제 브라우저를 쓰는 실제와도 같다."""
    ctx.clear_cookies()
    ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": BASE}])
    if page is not None:
        page.close()
    return ctx.new_page()


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        c = b.new_context(viewport={"width": 1280, "height": 950})

        # ══ ① z1147 「🔗 연결」 잠금 — 대표 계정(영업 권한이 있어야 칸이 뜬다) ══
        print("\n[①] z1147 — 「🔗 연결 (프로젝트·영업기회)」 잠금")
        pg = as_user(c, SEED["ceo"])
        pg.goto("%s/meetings/%d" % (BASE, MID), wait_until="domcontentloaded")
        pg.wait_for_selector("#secLink", timeout=15000)
        chk(pg.locator("#secLink").count() == 1, "「연결」 칸이 지워지지 않고 그대로 있다")
        body = pg.inner_text("body")
        chk("지금은 사용하지 않습니다" in body, "칸 머리에 「지금은 사용하지 않습니다」가 붙었다")
        chk("이 칸은 아직 사용하지 않습니다" in body, "왜 잠겼는지 안내가 있다")
        for sel, nm in (("#mtgProj", "프로젝트 고르기"), ("#mtgOpp", "영업기회 고르기"),
                        ("#btnLink", "「💾 연결 저장」"), ("#btnToOpp", "「🎯 새 영업기회 등록」")):
            if pg.locator(sel).count():
                chk(pg.locator(sel).is_disabled(), "%s 가 잠겨 있다" % nm)
            else:
                chk(False, "%s 가 화면에 없다(있어야 한다 — 삭제가 아니라 잠금)" % nm)
        chk("006T2607" in body, "🔵 이미 연결된 프로젝트 표시는 그대로 보인다(지난 기록)")

        # 주소로 직접 불러도 막히나
        rq = c.request
        r1 = rq.post("%s/api/meeting/%d/link" % (BASE, MID),
                     data={"project_id": None, "opportunity_id": None})
        chk(r1.status == 403, "🔴 주소로 직접 불러도 연결 저장이 막힌다", "HTTP %d" % r1.status)
        chk("사용하지 않습니다" in r1.text(), "막을 때 사람 말로 알려 준다", r1.text()[:60])
        r2 = rq.post("%s/api/meeting/%d/to-opportunity" % (BASE, MID), data={})
        chk(r2.status == 403, "🔴 주소로 직접 불러도 새 영업기회 등록이 막힌다", "HTTP %d" % r2.status)

        # ══ ② z1148 출발점 — 참석 안 한 다른 팀 사람은 볼 길이 없다 ══
        print("\n[②] z1148 — 지금은 볼 길이 없다(대표님이 말씀하신 상황)")
        pg = as_user(c, SEED["out"], pg)
        pg.goto("%s/meetings" % BASE, wait_until="domcontentloaded")
        chk(TITLE not in pg.inner_text("body"), "🔴 참석 안 한 사람의 회의록 목록에 안 보인다")
        pg.goto("%s/meetings/%d" % (BASE, MID), wait_until="domcontentloaded")
        chk(pg.url.rstrip("/").endswith("/meetings"), "🔴 주소로 열어도 목록으로 되돌려진다", pg.url)

        # ══ ③ 「이 사람들도 보기」로 넣기 — 회의록 주인(한도윤) ══
        print("\n[③] 「이 사람들도 보기」로 넣기")
        pg = as_user(c, SEED["owner"], pg)
        pg.goto("%s/meetings/%d" % (BASE, MID), wait_until="domcontentloaded")
        pg.wait_for_selector("#vwFld", timeout=15000)
        chk(pg.locator("#vwFld").count() == 1, "공개 범위 아래에 「이 사람들도 보기」 칸이 있다")
        chk("아직 없습니다" in pg.inner_text("#vwChips"), "처음엔 아무도 없다")
        chk(pg.locator("#secLink").count() == 0,
            "🔵 영업 권한 없는 사람에겐 「연결」 칸이 원래 안 보인다(그대로)")

        pg.click("#vwOpen")
        pg.wait_for_selector("#vwList .vw-row", timeout=15000)
        lst = pg.inner_text("#vwList")
        chk("생산팀" in lst and "검사기T" in lst, "고르는 명단이 부서별로 묶여 있다")
        rows = pg.locator("#vwList .vw-row")
        chk(rows.count() >= 4, "직원들이 나온다", "%d줄" % rows.count())
        att_row = pg.locator("#vwList .vw-row", has_text="오세진 대리 검사기T")
        chk("이미 볼 수 있음" in att_row.inner_text(), "참석자에겐 「이미 볼 수 있음」이 붙는다")
        out_row = pg.locator("#vwList .vw-row", has_text="문가온 대리 생산팀")
        chk("이미 볼 수 있음" not in out_row.inner_text(),
            "🔴 참석 안 한 다른 팀 사람에겐 그 표시가 없다(= 지금 못 본다)")
        chk("문가온 대리 생산팀" in lst, "이름이 「이름 직책 부서」로 나온다")

        pg.fill("#vwQ", "문가온")
        pg.wait_for_timeout(150)
        chk(pg.locator("#vwList .vw-row").count() == 1, "찾기로 걸러진다",
            "%d줄" % pg.locator("#vwList .vw-row").count())
        pg.locator("#vwList .vw-row input").first.check()
        chk("1명 골랐습니다" in pg.inner_text("#vwCnt"), "몇 명 골랐는지 알려 준다")
        pg.click("#vwSave")
        pg.wait_for_selector("#vwChips .vw-chip", timeout=15000)
        chk("문가온 대리 생산팀" in pg.inner_text("#vwChips"), "고른 사람이 칸에 남는다")
        chk("저장했습니다" in pg.inner_text("#vwSt"), "저장됐다고 알려 준다")

        # ══ ④ 🔴 두 층 다 — 목록과 상세 ══
        print("\n[④] 🔴 상세만이 아니라 회의록 목록에도 보여야 한다")
        pg = as_user(c, SEED["out"], pg)
        pg.goto("%s/meetings" % BASE, wait_until="domcontentloaded")
        chk(TITLE in pg.inner_text("body"), "🔴 회의록 **목록**에 보인다(열람 판정만 고치면 여기서 빠진다)")
        pg.goto("%s/meetings/%d" % (BASE, MID), wait_until="domcontentloaded")
        chk("/meetings/%d" % MID in pg.url, "상세 화면이 열린다", pg.url)
        chk(TITLE in pg.inner_text("body"), "회의 내용이 보인다")
        chk(pg.locator("#mtgTitle").is_disabled(), "🔵 보기만 된다 — 제목을 못 고친다")
        chk(pg.locator("#vwOpen").count() == 0, "🔵 고를 권한이 없으니 「＋ 직원 고르기」가 없다")
        r3 = c.request.post("%s/api/meeting/%d/viewers" % (BASE, MID),
                            data={"user_ids": [SEED["out2"]]})
        chk(r3.status == 403, "🔴 권한 없는 사람이 주소로 명단을 고치면 막힌다", "HTTP %d" % r3.status)

        # ══ ⑤ 🔴 회의록을 저장해도 안 사라진다 ══
        print("\n[⑤] 🔴 회의록을 저장해도 명단이 살아남는다(참석자 칸에 안 넣은 까닭)")
        pg = as_user(c, SEED["owner"], pg)
        r4 = c.request.put("%s/api/meeting/%d" % (BASE, MID),
                           data={"title": TITLE, "meeting_date": "2026-10-08",
                                 "visibility": "team", "location": "2층 회의실1",
                                 "tags": "", "attendees_text": "한도윤, 오세진",
                                 "body": "녹음 한번 해보고 있어. 아.", "status": "draft"})
        chk(r4.status == 200, "회의록 저장이 그대로 된다", "HTTP %d" % r4.status)
        pg = as_user(c, SEED["out"], pg)
        pg.goto("%s/meetings" % BASE, wait_until="domcontentloaded")
        chk(TITLE in pg.inner_text("body"),
            "🔴 저장 뒤에도 그대로 보인다 — 참석자 표에 넣었으면 여기서 사라졌다")

        # ══ ⑥ 빼기 ══
        print("\n[⑥] 명단에서 빼면 다시 안 보인다")
        pg = as_user(c, SEED["owner"], pg)
        pg.goto("%s/meetings/%d" % (BASE, MID), wait_until="domcontentloaded")
        pg.wait_for_selector("#vwOpen", timeout=15000)
        pg.click("#vwOpen")
        pg.wait_for_selector("#vwList .vw-row", timeout=15000)
        pg.fill("#vwQ", "문가온")
        pg.wait_for_timeout(150)
        pg.locator("#vwList .vw-row input").first.uncheck()
        pg.click("#vwSave")
        pg.wait_for_timeout(600)
        chk("아직 없습니다" in pg.inner_text("#vwChips"), "칸이 다시 비었다")
        pg = as_user(c, SEED["out"], pg)
        pg.goto("%s/meetings" % BASE, wait_until="domcontentloaded")
        chk(TITLE not in pg.inner_text("body"), "🔴 뺀 사람의 목록에서 사라진다")
        pg.goto("%s/meetings/%d" % (BASE, MID), wait_until="domcontentloaded")
        chk(pg.url.rstrip("/").endswith("/meetings"), "🔴 상세도 다시 막힌다", pg.url)

        # ══ ⑦ 새 회의록 화면 안내 ══
        print("\n[⑦] 새 회의록 화면")
        pg = as_user(c, SEED["owner"], pg)
        pg.goto("%s/meetings/new" % BASE, wait_until="domcontentloaded")
        # 새 회의록의 공개 범위는 「더 보기」 안에 접혀 있다(원래 그렇다) → 펴고 본다
        pg.wait_for_selector("#mtgMore", timeout=15000)
        pg.evaluate("document.getElementById('mtgMore').open = true")
        pg.wait_for_timeout(120)
        nb = pg.inner_text("body")
        chk("저장한 뒤" in nb and "이 사람들도 보기" in nb,
            "새 회의록엔 「저장한 뒤 고를 수 있다」고 알려 준다")
        chk("공개 범위" in nb, "공개 범위 칸은 그대로 있다")

        b.close()

    print("\n" + "=" * 56)
    print("  통과 %d · 실패 %d" % (OK, FAIL))
    if FAILS:
        for f in FAILS:
            print("   ✗ " + f)
    print("=" * 56)
    return 1 if FAIL else 0


sys.exit(main())
