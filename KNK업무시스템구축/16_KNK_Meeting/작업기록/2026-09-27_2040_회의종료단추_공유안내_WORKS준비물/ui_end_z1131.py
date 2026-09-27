# -*- coding: utf-8 -*-
"""z1131 화면 시험 — 「⏹ 회의 종료」 단추(예정 끝 시각 전에 끝났을 때) + 공유 안내 글
  ① 이음 회의와 연결된 회의록: 단추 보임 · 종료 표시 숨김
  ② 누르면(확인) → 「✅ 종료됨 · 시:분」 · 단추는 「↩ 종료 되돌리기」로 · 서버(DB)에도 끝낸 시각
  ③ 되돌리면 원래대로(서버도 비워짐)
  ④ 이음과 무관한 회의·새 회의록 화면에는 단추 없음 · 권한 없는 사람에게도 없음
  ⑤ 안내 글이 「📁 녹음 파일 올리기」를 먼저 말하고, 공유는 「앱을 깔았으면」으로 적는다
사용: py -3.12 ui_end_z1131.py [포트=8936]
"""
import json
import os
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8936
BASE = "http://127.0.0.1:%d" % PORT
HERE = os.path.dirname(os.path.abspath(__file__))
UA_SAMSUNG = ("Mozilla/5.0 (Linux; Android 14; SM-S928N) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/153.0.0.0 Mobile Safari/537.36")

OK, NG, ERRS = [], [], []


def ok(name, cond, extra=""):
    (OK if cond else NG).append(name)
    print(("  ✅ " if cond else "  ❌ ") + name + (("  — " + str(extra)[:170]) if extra != "" else ""), flush=True)


def main():
    # 🔴 seed_phrec.json 은 **서버를 띄운 쪽**이 쓴 것을 봐야 한다(둘째 인자로 그 폴더를 받는다).
    #   내 폴더의 사본은 다른 사본(app_base 등)을 가리킬 수 있어 엉뚱한 DB 를 건드린다(2026-09-27 회귀에서 겪음).
    seed_dir = sys.argv[2] if len(sys.argv) > 2 else HERE
    seed = json.load(open(os.path.join(seed_dir, "seed_phrec.json"), encoding="utf-8"))
    mids, ceo, app_dir = seed["mids"], seed["ceo"], seed["app"]
    M_MSG, M_PLAIN = mids[0], mids[1]
    db_path = os.path.join(app_dir, "data", "knk.db")

    def sql(q, args=()):
        con = sqlite3.connect(db_path)
        cur = con.execute(q, args)
        rows = cur.fetchall()
        con.commit()
        con.close()
        return rows

    # 이음 회의와 연결 · 종료 표시는 지운 상태로 시작 · 권한 없는 직원 하나
    sql("UPDATE meetings SET msg_meeting_id=?, msg_organizer_id=?, ended_at='' WHERE id=?", (9901, ceo, M_MSG))
    sql("UPDATE meetings SET msg_meeting_id=NULL, ended_at='' WHERE id=?", (M_PLAIN,))
    try:
        sql("INSERT INTO users(name, login_id, password, role, is_active) VALUES('시험직원','t_end_x','x','member',1)")
    except Exception:
        pass
    other = sql("SELECT id FROM users WHERE login_id='t_end_x'")[0][0]

    def ended_at():
        r = sql("SELECT ended_at FROM meetings WHERE id=?", (M_MSG,))
        return (r[0][0] or "") if r else ""

    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True, args=[
            "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])
        c = br.new_context(user_agent=UA_SAMSUNG, viewport={"width": 390, "height": 844},
                           is_mobile=True, has_touch=True, permissions=["microphone"], base_url=BASE)
        p = c.new_page()
        p.on("pageerror", lambda e: ERRS.append(str(e)))
        p.on("dialog", lambda d: d.accept())

        # ══════════ ① 단추가 보인다 ══════════
        print("\n■ ① 이음 회의와 연결된 회의록", flush=True)
        p.goto("%s/meetings/%d" % (BASE, M_MSG), wait_until="domcontentloaded")
        p.wait_for_timeout(900)
        b = p.locator("#btnEndMeeting")
        ok("「⏹ 회의 종료」 단추가 보인다", b.is_visible(), b.count())
        ok("단추 글자", "회의 종료" in (b.inner_text() or ""), (b.inner_text() or "")[:20])
        ok("아직 종료 표시는 없다", not p.locator("#mtgEndedTag").is_visible())
        ok("되돌리기 단추도 숨어 있다", not p.locator("#btnUnendMeeting").is_visible())

        # ══════════ ② 누르면 종료 ══════════
        print("\n■ ② 눌러서 종료", flush=True)
        b.click()
        p.wait_for_timeout(1500)
        tag = p.locator("#mtgEndedTag")
        ok("「✅ 종료됨」 표시가 나온다", tag.is_visible(), (tag.inner_text() or "")[:30])
        ok("끝낸 시각이 시:분으로 붙는다", ":" in (tag.inner_text() or ""), (tag.inner_text() or "")[:30])
        ok("종료 단추는 숨는다", not p.locator("#btnEndMeeting").is_visible())
        ok("「↩ 종료 되돌리기」가 나온다", p.locator("#btnUnendMeeting").is_visible())
        ok("서버에도 끝낸 시각이 적힌다", len(ended_at()) >= 16, ended_at())

        # ══════════ ③ 되돌리기 ══════════
        print("\n■ ③ 되돌리기", flush=True)
        p.locator("#btnUnendMeeting").click()
        p.wait_for_timeout(1500)
        ok("종료 표시가 사라진다", not p.locator("#mtgEndedTag").is_visible())
        ok("종료 단추가 다시 나온다", p.locator("#btnEndMeeting").is_visible())
        ok("서버도 비워진다", ended_at() == "", ended_at())

        # 새로 고쳐도 같은 상태(서버가 그린 화면)
        p.reload(wait_until="domcontentloaded")
        p.wait_for_timeout(800)
        ok("새로 고쳐도 종료 단추가 보인다", p.locator("#btnEndMeeting").is_visible())
        p.locator("#btnEndMeeting").click()
        p.wait_for_timeout(1500)
        p.reload(wait_until="domcontentloaded")
        p.wait_for_timeout(800)
        ok("종료한 뒤 새로 고치면 종료 표시가 그대로", p.locator("#mtgEndedTag").is_visible(),
           (p.locator("#mtgEndedTag").inner_text() or "")[:30])
        ok("그때는 종료 단추가 없다", not p.locator("#btnEndMeeting").is_visible())
        sql("UPDATE meetings SET ended_at='' WHERE id=?", (M_MSG,))

        # ══════════ ④ 단추가 없어야 하는 곳 ══════════
        print("\n■ ④ 단추가 없어야 하는 곳", flush=True)
        p.goto("%s/meetings/%d" % (BASE, M_PLAIN), wait_until="domcontentloaded")
        p.wait_for_timeout(700)
        ok("이음과 무관한 회의: 단추 없음", p.locator("#btnEndMeeting").count() == 0)
        p.goto("%s/meetings/new" % BASE, wait_until="domcontentloaded")
        p.wait_for_timeout(700)
        ok("새 회의록 화면: 단추 없음", p.locator("#btnEndMeeting").count() == 0)
        c.close()

        c2 = br.new_context(user_agent=UA_SAMSUNG, viewport={"width": 390, "height": 844},
                            is_mobile=True, has_touch=True, base_url=BASE)
        c2.add_cookies([{"name": "tuser", "value": str(other), "url": BASE}])
        p2 = c2.new_page()
        p2.goto("%s/meetings/%d" % (BASE, M_MSG), wait_until="domcontentloaded")
        p2.wait_for_timeout(700)
        ok("권한 없는 직원: 단추 없음", p2.locator("#btnEndMeeting").count() == 0)
        c2.close()

        # ══════════ ⑤ 공유 안내 글 ══════════
        print("\n■ ⑤ 녹음 안내 글(공유는 앱을 깔았을 때)", flush=True)
        c3 = br.new_context(user_agent=UA_SAMSUNG, viewport={"width": 390, "height": 844},
                            is_mobile=True, has_touch=True, permissions=["microphone"], base_url=BASE)
        p3 = c3.new_page()
        p3.goto("%s/meetings/new" % BASE, wait_until="domcontentloaded")
        p3.wait_for_timeout(900)
        g = (p3.locator("#recPhoneGuide").inner_text() or "").replace("\n", " ")
        ok("② 가 「📁 녹음 파일 올리기」를 먼저 말한다", "녹음 파일 올리기" in g, g[:150])
        ok("공유는 「앱을 깔아 두면」으로 적는다", "앱을 깔아" in g and "공유 → KNK WORKS" in g, g[-140:])
        ok("앱 설치 방법도 한 줄 적는다", "앱 설치" in g, g[-90:])
        c3.close()

        print("\n" + "=" * 70)
        ok("화면 오류 없음", not ERRS, ERRS[:2])
        print("합계: 통과 %d · 실패 %d" % (len(OK), len(NG)), flush=True)
        for n in NG:
            print("  - 실패:", n, flush=True)
        br.close()
    return 1 if NG else 0


if __name__ == "__main__":
    sys.exit(main())
