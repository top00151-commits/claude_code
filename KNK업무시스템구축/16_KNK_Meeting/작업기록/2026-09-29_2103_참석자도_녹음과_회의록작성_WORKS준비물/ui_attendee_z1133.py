# -*- coding: utf-8 -*-
"""z1133 화면 시험 — 참석자 눈에 녹음·올리기·정리·종료 단추가 보이고, 삭제는 안 보인다
  ① 참석자: 회의록이 열리고 「🎤 녹음」·「📁 녹음 파일 올리기」·「🔄 다시 정리」·「⏹ 회의 종료」 보임 · 「🗑 삭제」 없음
  ② 참석자 아닌 직원: 비공개 회의는 열리지 않는다(목록으로 튕김)
  ③ 작성자: 예전 그대로(삭제까지 보임)
사용: py -3.12 ui_attendee_z1133.py [포트=8936] [씨앗폴더]
🔴 씨앗(seed_phrec.json)은 **서버를 띄운 쪽**이 쓴 것을 본다(둘째 인자) — 다른 사본 DB 를 건드리지 않게.
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
UA = ("Mozilla/5.0 (Linux; Android 14; SM-S928N) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/153.0.0.0 Mobile Safari/537.36")

OK, NG, ERRS = [], [], []


def ok(name, cond, extra=""):
    (OK if cond else NG).append(name)
    print(("  ✅ " if cond else "  ❌ ") + name + (("  — " + str(extra)[:170]) if extra != "" else ""), flush=True)


def main():
    seed_dir = sys.argv[2] if len(sys.argv) > 2 else HERE
    seed = json.load(open(os.path.join(seed_dir, "seed_phrec.json"), encoding="utf-8"))
    mids, ceo, app_dir = seed["mids"], seed["ceo"], seed["app"]
    MID = mids[0]
    db_path = os.path.join(app_dir, "data", "knk.db")

    def sql(q, args=()):
        con = sqlite3.connect(db_path)
        cur = con.execute(q, args)
        rows = cur.fetchall()
        con.commit()
        con.close()
        return rows

    # 참석자 한 명(계정 연결) · 참석자 아닌 직원 한 명 · 비공개 이음 회의로 만들어 둔다
    for login, name in (("t_att_ui", "이한중"), ("t_out_ui", "박주창")):
        if not sql("SELECT id FROM users WHERE login_id=?", (login,)):
            sql("INSERT INTO users(name, login_id, password, role, is_active) VALUES(?,?,'x','member',1)", (name, login))
    att = sql("SELECT id FROM users WHERE login_id='t_att_ui'")[0][0]
    out = sql("SELECT id FROM users WHERE login_id='t_out_ui'")[0][0]
    sql("UPDATE meetings SET owner_id=?, msg_meeting_id=9931, msg_organizer_id=?, visibility='private', ended_at='' "
        "WHERE id=?", (ceo, ceo, MID))
    sql("DELETE FROM meeting_attendees WHERE meeting_id=?", (MID,))
    sql("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,'이한중')", (MID, att))

    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True, args=[
            "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])

        def page_as(uid):
            c = br.new_context(user_agent=UA, viewport={"width": 390, "height": 844},
                               is_mobile=True, has_touch=True, permissions=["microphone"], base_url=BASE)
            c.add_cookies([{"name": "tuser", "value": str(uid), "url": BASE}])
            p = c.new_page()
            p.on("pageerror", lambda e: ERRS.append(str(e)))
            p.goto("%s/meetings/%d" % (BASE, MID), wait_until="domcontentloaded")
            p.wait_for_timeout(900)
            return c, p

        # ══════════ ① 참석자 ══════════
        print("\n■ ① 참석자(이한중)", flush=True)
        c, p = page_as(att)
        ok("회의록 상세가 열린다", "/meetings/%d" % MID in p.url, p.url[-30:])
        p.evaluate("() => { const d=document.getElementById('redoTools'); if(d) d.open=true;"
                   " const o=document.getElementById('recOther'); if(o) o.open=true; }")
        p.wait_for_timeout(400)
        ok("「🎤 녹음」 단추가 보인다", p.locator("#recBtn").is_visible())
        ok("「📁 음성 파일 올리기」가 보인다", p.locator("label.rec-file").first.is_visible())
        ok("「🔄 다시 정리」가 보인다", p.locator("#btnExtract").is_visible())
        ok("「⏹ 회의 종료」가 보인다", p.locator("#btnEndMeeting").is_visible(), p.locator("#btnEndMeeting").count())
        ok("🗑 삭제 단추는 없다", p.locator("#btnDelete").count() == 0)
        ok("본문 칸을 고칠 수 있다(읽기 전용 아님)",
           p.evaluate("() => { const t=document.getElementById('mtgBody');"
                      " return !!t && !t.readOnly && !t.disabled; }"))
        c.close()

        # ══════════ ② 참석자가 아닌 직원 ══════════
        print("\n■ ② 참석자가 아닌 직원(박주창)", flush=True)
        c, p = page_as(out)
        ok("비공개 회의는 열리지 않는다(목록으로)", "/meetings/%d" % MID not in p.url, p.url[-30:])
        c.close()

        # ══════════ ③ 작성자 ══════════
        print("\n■ ③ 작성자(대표 계정)", flush=True)
        c, p = page_as(ceo)
        ok("회의록이 열린다", "/meetings/%d" % MID in p.url, p.url[-30:])
        ok("🗑 삭제 단추가 보인다(예전 그대로)", p.locator("#btnDelete").is_visible())
        ok("「⏹ 회의 종료」도 보인다", p.locator("#btnEndMeeting").is_visible())
        c.close()

        print("\n" + "=" * 70)
        ok("화면 오류 없음", not ERRS, ERRS[:2])
        print("합계: 통과 %d · 실패 %d" % (len(OK), len(NG)), flush=True)
        for n in NG:
            print("  - 실패:", n, flush=True)
        br.close()
    return 1 if NG else 0


if __name__ == "__main__":
    sys.exit(main())
