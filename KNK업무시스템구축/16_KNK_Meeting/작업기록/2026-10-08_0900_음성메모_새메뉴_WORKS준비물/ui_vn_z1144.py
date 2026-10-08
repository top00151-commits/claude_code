# -*- coding: utf-8 -*-
"""z1144 화면 시험 — 🎙 음성 메모
사용: py -3.12 ui_vn_z1144.py [포트=8939]
  ① 왼쪽 메뉴에 있다 · 목록이 열린다 · 🔴 남의 메모는 안 보인다
  ② 새 메모 — 녹음 올리기 → 글자 → 정리까지 자동
  ③ 정리 틀이 회의용과 다르다(안건·결정사항 없음) · 「우리 회사 말」은 함께 간다
  ④ 정리 글·원문 고치기 저장 · 「🔄 다시 정리」
  ⑤ 🔴 남의 메모는 화면·API 둘 다 막힌다
  ⑥ 삭제하면 목록에서 사라지고 녹음 파일도 지워진다
🔴 진짜 AI 안 부름(서버가 가로챈다)."""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8939
BASE = f"http://127.0.0.1:{PORT}"
SEED = json.load(io.open(os.path.join(HERE, "seed_vn.json"), encoding="utf-8"))
APP = SEED["app"]

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


def sent():
    try:
        return io.open(SEED["sent"], encoding="utf-8").read()
    except Exception:
        return ""


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        c = b.new_context(viewport={"width": 1280, "height": 900})
        c.add_cookies([{"name": "tuser", "value": str(SEED["ceo"]), "url": BASE}])
        pg = c.new_page()

        # ── ① 메뉴·목록 ────────────────────────────────────
        print("\n[①] 메뉴와 목록")
        pg.goto(f"{BASE}/home", wait_until="domcontentloaded")
        pg.wait_for_selector("a.sb-item[href='/voice-notes']", timeout=15000)   # count() 는 기다리지 않는다
        _mn = pg.locator("a.sb-item[href='/voice-notes']").count()
        chk(_mn == 1, "왼쪽 메뉴에 「🎙 음성 메모」가 하나 있다", "%d개" % _mn)
        chk("🎙 음성 메모" in pg.inner_text("a.sb-item[href='/voice-notes']"), "이름이 사람 말로 되어 있다")
        pg.goto(f"{BASE}/voice-notes", wait_until="domcontentloaded")
        body = pg.inner_text("body")
        chk("음성 메모" in body, "목록 화면이 열린다")
        chk("아직 메모가 없습니다" in body, "처음엔 비어 있다")
        chk("남의 메모" not in body, "🔴 남의 메모는 목록에 안 보인다")
        chk("나만 봅니다" in body, "내 것만 보인다는 안내가 있다")

        # ── ② 새 메모 — 올리기 → 글자 → 정리 ────────────────
        print("\n[②] 새 메모 — 올리면 글자·정리까지 자동")
        wav = os.path.join(HERE, "z1144_test.wav")
        with open(wav, "wb") as f:
            f.write(b"RIFF" + (b"\0" * 4096))
        pg.goto(f"{BASE}/voice-notes/new", wait_until="domcontentloaded")
        pg.wait_for_selector("#vnFile", state="attached", timeout=15000)
        chk(pg.locator("#vnFile").count() == 1, "「📁 녹음 파일 올리기」 칸이 있다")
        chk("휴대폰 기본 녹음기" in pg.inner_text("body"), "휴대폰 녹음기로 하라는 안내가 있다")
        _acc = pg.get_attribute("#vnFile", "accept") or ""
        chk(".m4a" in _acc and ".caf" in _acc, "아이폰 대비 확장자가 함께 적혀 있다", _acc[:34] + "…")
        pg.locator("#vnFile").set_input_files(wav)
        try:
            pg.wait_for_function(
                "()=>{const e=document.getElementById('vnSumBox');"
                " return e && (e.textContent||'').indexOf('요점')>=0;}", timeout=60000)
            done = True
        except Exception:
            done = False
        chk(done, "올리면 글자→정리까지 자동으로 된다", pg.inner_text("#vnSumBox")[:30])
        chk("/voice-notes/" in pg.url and pg.url.rstrip("/").split("/")[-1].isdigit(),
            "주소가 이 메모 주소로 바뀐다", pg.url)
        NID = int(pg.url.rstrip("/").split("/")[-1])
        chk("새 음성 메모" not in pg.inner_text(".page-title"),
            "만들어진 뒤엔 머리글이 「새 음성 메모」가 아니다", pg.inner_text(".page-title"))
        chk((pg.input_value("#vnTitle") or "").strip() != "", "제목을 AI 가 지어 준다",
            pg.input_value("#vnTitle"))
        chk(SEED["fake_text"][:12] in (pg.input_value("#vnBody") or ""), "받아쓴 원문이 들어 있다")

        # ── ③ 정리 틀 ──────────────────────────────────────
        print("\n[③] 정리 틀이 회의용과 다른가")
        s = sent()
        chk("요점" in s and "할 일" in s, "요점·할 일을 뽑으라고 보냈다")
        # 🔴 「안건·결정사항」은 「만들지 않는다」는 금지 문장에 들어 있다 — 낱말로 재면 안 된다.
        #   회의용 틀이 왔는지는 그쪽에만 있는 표식으로 본다.
        chk('"decisions"' not in s and "참석자 이름이 원문에 나오면" not in s,
            "🔴 회의용 틀(결정사항 칸·참석자 귀속 지시)은 안 보냈다")
        chk("만들지 않는다" in s, "안건·결정사항을 만들지 말라고 일러 둔다")
        chk("MLCC" in s, "「우리 회사 말」 바로잡기가 함께 간다")
        chk(SEED["fake_text"][:12] in s.split("@@@원문@@@")[-1], "원문을 그대로 보냈다")

        # ── ④ 고치기 ───────────────────────────────────────
        print("\n[④] 고치기")
        pg.click("#vnSumEdit")
        pg.fill("#vnSumEdit2", "요점\n- 사람이 고친 정리")
        pg.click("#vnSumSave")
        pg.wait_for_timeout(1200)
        chk("사람이 고친 정리" in pg.inner_text("#vnSumBox"), "정리 글을 고쳐 저장할 수 있다")
        pg.goto(f"{BASE}/voice-notes/{NID}", wait_until="domcontentloaded")
        chk("사람이 고친 정리" in pg.inner_text("#vnSumBox"), "다시 열어도 고친 정리가 남아 있다")
        pg.evaluate("()=>{const d=document.getElementById('vnBodyWrap'); if(d) d.open=true;}")
        pg.fill("#vnBody", "사람이 고친 원문입니다. MSCC 단가.")
        pg.click("#vnBodySave")
        pg.wait_for_timeout(1200)
        chk("저장" in pg.inner_text("#vnBodySt"), "원문도 고쳐 저장할 수 있다", pg.inner_text("#vnBodySt")[:24])
        pg.click("#vnRedo")
        pg.wait_for_timeout(2500)
        chk("사람이 고친 원문" in sent().split("@@@원문@@@")[-1], "「🔄 다시 정리」는 고친 원문으로 돌린다")

        # ── ⑤ 🔴 남의 메모 ─────────────────────────────────
        print("\n[⑤] 🔴 남의 메모는 막힌다")
        pg.goto(f"{BASE}/voice-notes/{SEED['other_nid']}", wait_until="domcontentloaded")
        chk(pg.url.rstrip("/").endswith("/voice-notes"), "화면으로 열면 목록으로 되돌린다", pg.url)
        r = pg.request.get(f"{BASE}/api/voice-note/{SEED['other_nid']}")
        chk(r.status == 404, "API 로도 못 읽는다", str(r.status))
        r2 = pg.request.post(f"{BASE}/api/voice-note/{SEED['other_nid']}/save",
                             data=json.dumps({"summary": "남의 것 고치기"}),
                             headers={"Content-Type": "application/json"})
        chk(r2.status == 404, "API 로도 못 고친다", str(r2.status))
        r3 = pg.request.delete(f"{BASE}/api/voice-note/{SEED['other_nid']}")
        chk(r3.status == 404, "API 로도 못 지운다", str(r3.status))

        # ── ⑥ 목록·삭제 ────────────────────────────────────
        print("\n[⑥] 목록에 뜨고, 지우면 녹음도 함께 지워진다")
        pg.goto(f"{BASE}/voice-notes", wait_until="domcontentloaded")
        chk(pg.locator(f"a.vn-card[href='/voice-notes/{NID}']").count() == 1, "내 메모가 목록에 있다")
        chk("남의 메모" not in pg.inner_text("body"), "🔴 남의 메모는 여전히 안 보인다")
        _dir = os.path.join(APP, "voice_notes", f"note_{NID}")
        chk(os.path.isdir(_dir), "녹음 파일 폴더가 생겼다", _dir[-24:])
        pg.goto(f"{BASE}/voice-notes/{NID}", wait_until="domcontentloaded")
        pg.on("dialog", lambda d: d.accept())
        pg.click("#vnDel")
        pg.wait_for_url(f"{BASE}/voice-notes", timeout=15000)
        chk("아직 메모가 없습니다" in pg.inner_text("body"), "지우면 목록에서 사라진다")
        chk(not os.path.isdir(_dir), "녹음 파일 폴더도 함께 지워진다")
        try:
            os.remove(wav)
        except Exception:
            pass

        b.close()

    print(f"\n{'=' * 46}  통과 {OK} · 실패 {FAIL}")
    if FAILS:
        print("실패 항목: " + ", ".join(FAILS))
    return 1 if FAIL else 0


sys.exit(main())
