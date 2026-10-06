# -*- coding: utf-8 -*-
"""z1139 화면 시험 — 「📋 회의록 정리」 글을 그 자리에서 고친다 (대표 지시 2026-10-05)
  A. 정리 칸에 「✏ 고치기」가 보인다 · 누르면 글칸에 지금 정리 글이 들어온다
  B. 낱말을 고쳐 저장 → 화면·서버·새로고침 모두 바뀐 글
  C. 「취소」는 아무것도 안 바꾼다
  D. 🔴 손으로 고친 뒤 「🔄 다시 정리」를 누르면 한 번 묻는다(고친 글이 사라지므로)
  E. 고칠 수 없는 사람에게는 「✏ 고치기」가 안 보인다
사용: py -3.12 ui_sumedit_z1139.py [포트=8936] [씨앗폴더]"""
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
AI_SUM = ("핵심: 주요 설비의 구매·검수를 일정에 맞춰 마무리한다.\n[구매·제작 일정]\n"
          "- 방앗간 공장은 1차 검토를 완료했고 금일 최종 검토를 준비 중")
FIXED = AI_SUM.replace("방앗간 공장", "반월 공장")


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

    if not sql("SELECT id FROM users WHERE login_id='z39_out_ui'"):
        sql("INSERT INTO users(name, login_id, password, role, is_active) VALUES('박주창','z39_out_ui','x','member',1)")
    out = sql("SELECT id FROM users WHERE login_id='z39_out_ui'")[0][0]
    sql("UPDATE meetings SET owner_id=?, visibility='all', summary=?, body=?, audio_path='', rec_state='' "
        "WHERE id=?", (ceo, AI_SUM, "회의 원문입니다 [음성 변환]", MID))
    sql("DELETE FROM meeting_attendees WHERE meeting_id=?", (MID,))

    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True)

        def page_as(uid):
            c = br.new_context(user_agent=UA, viewport={"width": 390, "height": 844},
                               is_mobile=True, has_touch=True, base_url=BASE)
            c.add_cookies([{"name": "tuser", "value": str(uid), "url": BASE}])
            p = c.new_page()
            p.on("pageerror", lambda e: ERRS.append(str(e)))
            p.goto("%s/meetings/%d" % (BASE, MID), wait_until="domcontentloaded")
            p.wait_for_timeout(900)
            return c, p

        # ══════════ A. 고치기 단추·글칸 ══════════
        print("\n■ A. 「✏ 고치기」가 보이고, 누르면 지금 글이 들어온다", flush=True)
        c, p = page_as(ceo)
        ok("A1 정리 칸에 「✏ 고치기」가 보인다", p.locator("#btnSumEdit").is_visible())
        ok("A2 처음엔 고치기 상자가 숨어 있다", not p.locator("#sumEditWrap").is_visible())
        ok("A3 정리 글이 AI 가 적은 그대로", "방앗간 공장" in p.locator("#mtgSummary").inner_text())
        p.click("#btnSumEdit")
        p.wait_for_timeout(350)
        ok("A4 누르면 고치기 글칸이 나온다", p.locator("#sumEdit").is_visible())
        ok("A5 읽기 전용 글상자는 숨는다", not p.locator("#mtgSummary").is_visible())
        ok("A6 글칸에 지금 정리 글이 들어 있다",
           p.locator("#sumEdit").input_value().strip() == AI_SUM.strip(),
           p.locator("#sumEdit").input_value()[:40])
        ok("A7 단추 글이 「✖ 그만두기」로 바뀐다", "그만두기" in p.locator("#btnSumEdit").inner_text())

        # ══════════ B. 고쳐 저장 ══════════
        print("\n■ B. 낱말을 고쳐 저장한다", flush=True)
        p.fill("#sumEdit", FIXED)
        p.click("#btnSumSave")
        try:
            p.wait_for_function("()=>{const b=document.getElementById('mtgSummary');"
                                "return b && !b.hidden && b.textContent.indexOf('반월 공장')>=0;}", timeout=15000)
            done = True
        except Exception:
            done = False
        ok("B1 화면 정리 글이 바뀐다(「방앗간」→「반월」)", done, p.locator("#mtgSummary").inner_text()[-40:])
        ok("B2 고치기 상자는 닫힌다", not p.locator("#sumEditWrap").is_visible())
        ok("B3 서버에도 저장됐다", "반월 공장" in (sql("SELECT summary FROM meetings WHERE id=?", (MID,))[0][0] or ""))
        ok("B4 AI 가 적은 다른 줄은 그대로", "핵심: 주요 설비의 구매·검수" in p.locator("#mtgSummary").inner_text())
        p.reload(wait_until="domcontentloaded")
        p.wait_for_timeout(800)
        ok("B5 새로고침해도 고친 글 그대로", "반월 공장" in p.locator("#mtgSummary").inner_text())

        # ══════════ C. 취소 ══════════
        print("\n■ C. 「취소」는 아무것도 안 바꾼다", flush=True)
        p.click("#btnSumEdit")
        p.wait_for_timeout(300)
        p.fill("#sumEdit", "엉뚱한 글로 바꿔 보기")
        p.click("#btnSumCancel")
        p.wait_for_timeout(350)
        ok("C1 상자가 닫힌다", not p.locator("#sumEditWrap").is_visible())
        ok("C2 화면 글은 그대로", "반월 공장" in p.locator("#mtgSummary").inner_text())
        ok("C3 서버 글도 그대로",
           "엉뚱한" not in (sql("SELECT summary FROM meetings WHERE id=?", (MID,))[0][0] or ""))

        # ══════════ D. 「🔄 다시 정리」 되묻기 ══════════
        print("\n■ D. 손으로 고친 뒤 「🔄 다시 정리」는 한 번 묻는다", flush=True)
        p.click("#btnSumEdit")
        p.wait_for_timeout(250)
        p.fill("#sumEdit", FIXED + "\n- 손으로 한 줄 더")
        p.click("#btnSumSave")
        p.wait_for_timeout(1500)
        asked = {"n": 0, "txt": ""}

        def on_dialog(dlg):
            asked["n"] += 1
            asked["txt"] = dlg.message
            dlg.dismiss()      # 「아니오」 — 고친 글이 남아야 한다

        p.on("dialog", on_dialog)
        p.evaluate("()=>{const d=document.getElementById('redoTools'); if(d) d.open=true;}")
        p.wait_for_timeout(300)
        p.click("#btnExtract")
        p.wait_for_timeout(1200)
        ok("D1 되묻는 창이 뜬다", asked["n"] == 1, asked["txt"][:80])
        ok("D2 창 글에 「사라집니다」가 들어 있다", "사라집니다" in asked["txt"], asked["txt"][:80])
        ok("D3 「아니오」면 고친 글이 그대로",
           "손으로 한 줄 더" in (sql("SELECT summary FROM meetings WHERE id=?", (MID,))[0][0] or ""))
        c.close()

        # ══════════ E. 고칠 수 없는 사람 ══════════
        print("\n■ E. 고칠 수 없는 사람에게는 안 보인다", flush=True)
        c, p = page_as(out)
        ok("E1 회의록은 열린다(전 직원 공개)", "/meetings/%d" % MID in p.url, p.url[-24:])
        ok("E2 「✏ 고치기」가 없다", p.locator("#btnSumEdit").count() == 0)
        ok("E3 고치기 상자도 없다", p.locator("#sumEditWrap").count() == 0)
        ok("E4 정리 글은 읽을 수 있다", "반월 공장" in p.locator("#mtgSummary").inner_text())
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
