# -*- coding: utf-8 -*-
"""z1142 화면 시험 — 관리자 → AI 설정에서 「우리 회사 말」을 적고 저장하면
   회의록 「정리」가 그 말을 함께 들고 가는가.
사용: py -3.12 ui_terms_z1142.py [포트=8938]
🔴 진짜 AI 안 부름(서버가 ai_chat 을 가로채 보낸 지시문을 파일에 적는다)."""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8938
BASE = f"http://127.0.0.1:{PORT}"
SEED = json.load(io.open(os.path.join(HERE, "seed_terms.json"), encoding="utf-8"))
SENT = SEED["sent"]

OK = FAIL = 0
FAILS = []


def chk(cond, name, extra=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  [PASS] {name}" + (f" · {extra}" if extra else ""))
    else:
        FAIL += 1
        FAILS.append(name)
        print(f"  [FAIL] {name} {extra}")


def sent_text():
    try:
        return io.open(SENT, encoding="utf-8").read()
    except Exception:
        return ""


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        c = b.new_context(viewport={"width": 1280, "height": 900})
        c.add_cookies([{"name": "tuser", "value": str(SEED["ceo"]), "url": BASE}])
        pg = c.new_page()

        # ── 1. 화면에 칸이 보이나 ────────────────────────────
        print("\n[1] 관리자 → AI 설정 화면")
        pg.goto(f"{BASE}/admin/ai-settings", wait_until="domcontentloaded")
        pg.wait_for_selector("textarea[name='meeting_terms']", timeout=15000)
        ta = pg.locator("textarea[name='meeting_terms']")
        _n = ta.count()
        chk(_n == 1, "「우리 회사 말」 적는 칸이 하나 있다", "%d개" % _n)
        chk(ta.is_visible(), "칸이 보인다")
        body = pg.inner_text("body")
        chk("회의록에서 바로잡을" in body, "이름표가 사람 말로 되어 있다")
        chk("받아쓴 원문은 바꾸지 않습니다" in body, "원문은 안 바꾼다는 안내가 있다")
        chk("MLCC" in body, "기본 목록(MLCC)이 화면에 보인다")
        chk("제목도 함께 바로잡아" in body, "제목도 고치라는 안내가 있다")
        chk(ta.input_value().strip() == "", "처음엔 비어 있다(기본 목록을 쓴다는 뜻)")

        # ── 2. 적고 저장 ────────────────────────────────────
        print("\n[2] 적고 저장하면 남아 있나")
        ta.fill("MLCC(MSCC로 잘못 들림), 하이스트, 케이엔케이")
        pg.click("button.ai-btn.primary")
        pg.wait_for_load_state("domcontentloaded")
        chk("/admin/ai-settings" in pg.url, "저장 뒤 같은 화면으로 돌아온다", pg.url.split("/")[-1])
        pg.goto(f"{BASE}/admin/ai-settings", wait_until="domcontentloaded")
        v = pg.locator("textarea[name='meeting_terms']").input_value()
        chk("하이스트" in v, "다시 열어도 적은 말이 남아 있다", v[:40])

        # ── 3. 정리할 때 그 말을 들고 가나 ───────────────────
        print("\n[3] 회의록 정리가 그 말을 들고 가는가")
        if os.path.exists(SENT):
            os.remove(SENT)
        r = pg.request.post(f"{BASE}/api/meeting/{SEED['mid']}/extract")
        chk(r.status == 200, "정리 요청 성공", str(r.status))
        s = sent_text()
        chk("[우리 회사 말" in s, "AI 에게 「우리 회사 말」 묶음을 보냈다")
        chk("하이스트" in s, "관리자가 적은 말이 들어 있다")
        chk("MLCC(MSCC로 잘못 들림)" in s, "헷갈리는 말 표기도 그대로 간다")
        i_t, i_w = s.find("[이번 회의 정보]"), s.find("[우리 회사 말")
        chk(i_t != -1 and i_t < i_w, "회의 제목이 먼저, 용어가 뒤")
        chk("MSCC" in s.split("@@@원문@@@")[-1], "🔴 받아쓴 원문은 그대로다(MSCC 남아 있음)")

        # ── 4. 끄기 ─────────────────────────────────────────
        print("\n[4] - 한 글자로 끄기")
        pg.goto(f"{BASE}/admin/ai-settings", wait_until="domcontentloaded")
        pg.locator("textarea[name='meeting_terms']").fill("-")
        pg.click("button.ai-btn.primary")
        pg.wait_for_load_state("domcontentloaded")
        os.remove(SENT) if os.path.exists(SENT) else None
        pg.request.post(f"{BASE}/api/meeting/{SEED['mid']}/extract")
        s = sent_text()
        chk("[우리 회사 말" not in s, "끄면 아예 안 보낸다")
        chk("[이번 회의 정보]" in s, "회의 제목은 예전처럼 그대로 보낸다")

        # ── 5. 비우면 기본 목록 ──────────────────────────────
        print("\n[5] 비우면 기본 목록으로 돌아온다")
        pg.goto(f"{BASE}/admin/ai-settings", wait_until="domcontentloaded")
        pg.locator("textarea[name='meeting_terms']").fill("")
        pg.click("button.ai-btn.primary")
        pg.wait_for_load_state("domcontentloaded")
        os.remove(SENT) if os.path.exists(SENT) else None
        pg.request.post(f"{BASE}/api/meeting/{SEED['mid']}/extract")
        s = sent_text()
        chk("파트리스트" in s and "표면저항" in s, "기본 목록이 다시 들어간다")

        # ── 6. 일반 직원은 못 들어간다 ───────────────────────
        print("\n[6] 일반 직원은 이 화면에 못 들어간다")
        c2 = b.new_context(viewport={"width": 1280, "height": 900})
        c2.add_cookies([{"name": "tuser", "value": str(SEED["emp"]), "url": BASE}])
        pg2 = c2.new_page()
        pg2.goto(f"{BASE}/admin/ai-settings", wait_until="domcontentloaded")
        chk(pg2.locator("textarea[name='meeting_terms']").count() == 0,
            "직원 눈에는 칸이 안 보인다", pg2.url)

        # ── 7. 화면이 안 망가졌나 ────────────────────────────
        print("\n[7] 화면이 안 밀렸나")
        pg.goto(f"{BASE}/admin/ai-settings", wait_until="domcontentloaded")
        over = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        chk(over <= 0, "가로 스크롤이 안 생긴다", f"{over}px")
        chk(pg.locator("button.ai-btn.primary").count() == 1, "저장 단추는 그대로 하나")
        chk(pg.locator("input[name='openai_api_key']").count() == 1, "기존 키 입력칸도 그대로")
        pg.screenshot(path=os.path.join(HERE, "screen_ai_settings.png"), full_page=True)

        b.close()

    print(f"\n{'=' * 46}  통과 {OK} · 실패 {FAIL}")
    if FAILS:
        print("실패 항목: " + ", ".join(FAILS))
    return 1 if FAIL else 0


sys.exit(main())
