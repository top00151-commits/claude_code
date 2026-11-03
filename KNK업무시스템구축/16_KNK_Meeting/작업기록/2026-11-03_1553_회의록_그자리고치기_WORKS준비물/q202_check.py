# -*- coding: utf-8 -*-
"""z1202 검사 — 회의록 정리 글·회의록 양식 그 자리에서 고치기 + 고친 낱말을 회의 원문에도(같은 글자 전부)
사용: py -3.12 q202_check.py <포트> <앱폴더>     (run_q202_app.py 로 띄운 새 서버 · 이 검사는 자료를 바꾼다 → 서버당 한 번)
🔒 시험 글은 모두 지어낸 것."""
import io
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
PORT = int(sys.argv[1])
APP = sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
SEED = json.load(io.open(os.path.join(HERE, "seed_%d.json" % PORT), encoding="utf-8"))
ME, MEM, ATT, KANG = SEED["me"], SEED["mem"], SEED["att"], SEED["kang"]
IDS = SEED["ids"]
M1, M2 = IDS["M1"], IDS["M2"]
BASE = "http://127.0.0.1:%d" % PORT
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
NP = [0, 0]


def chk(name, cond, extra=""):
    NP[0 if cond else 1] += 1
    print(("  ✅ " if cond else "  ❌ ") + name + ("" if cond else "  ← " + str(extra)[:300]))


def db():
    return sqlite3.connect(os.path.join(APP, "data", "knk.db"))


def mrow(mid):
    c = db()
    r = c.execute("SELECT summary, body, updated_at FROM meetings WHERE id=?", (mid,)).fetchone()
    c.close()
    return {"summary": r[0] or "", "body": r[1] or "", "ts": r[2]}


def http(path, uid, data=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(data).encode("utf-8") if data is not None else None,
                                 headers={"Content-Type": "application/json", "Cookie": "tuser=%d" % uid},
                                 method="POST" if data is not None else "GET")
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read().decode("utf-8") or "{}")
            except Exception:
                return e.code, {}
        except (ConnectionError, urllib.error.URLError):
            if attempt == 2:
                raise
            time.sleep(1)


#  고치는 칸 안의 글자 고르기 — word 의 n 번째 · end=True 면 그 뒤에 커서만
SEL_JS = """([sel, word, nth, end]) => {
  const el = document.querySelector(sel); if (!el) return 'no-el';
  const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT); const nodes = []; let all = '';
  while (tw.nextNode()) { nodes.push([tw.currentNode, all.length]); all += tw.currentNode.nodeValue; }
  let at = -1, from = 0; for (let i = 0; i <= nth; i++) { at = all.indexOf(word, from); if (at < 0) return 'no-word'; from = at + 1; }
  const pos = (k) => { for (let i = nodes.length - 1; i >= 0; i--) if (nodes[i][1] <= k) return [nodes[i][0], k - nodes[i][1]]; return [nodes[0][0], 0]; };
  const r = document.createRange(); const a = pos(at), b = pos(at + word.length);
  if (end) { r.setStart(b[0], b[1]); r.collapse(true); } else { r.setStart(a[0], a[1]); r.setEnd(b[0], b[1]); }
  const s = getSelection(); s.removeAllRanges(); s.addRange(r); return 'ok';
}"""


def toast(page, timeout=8000):
    page.wait_for_selector(".kle-toast", timeout=timeout)
    return page.inner_text(".kle-toast")


def notoast(page):
    page.evaluate("document.querySelectorAll('.kle-toast').forEach(t => t.remove())")


def ctx_for(b, uid, w=1280, h=1000, mobile=False):
    ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=mobile, has_touch=mobile)
    ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": BASE}])
    return ctx


def open_form(ctx, mid=M1):
    pg = ctx.new_page()
    pg.on("dialog", lambda d: d.accept())
    pg.goto(BASE + "/meetings/%d" % mid, wait_until="domcontentloaded")
    pg.wait_for_selector("#mtgSummary", timeout=15000)
    pg.wait_for_timeout(600)
    return pg


def line_sel(i):
    return '#mtgSummary > [data-kle="%d"]' % i


def edit_replace(pg, sel, word, new, nth=0, end=False):
    notoast(pg)
    pg.click(sel)
    pg.wait_for_timeout(150)
    r = pg.evaluate(SEL_JS, [sel, word, nth, end])
    if r != "ok":
        return r
    if new:
        pg.keyboard.type(new)
    else:
        pg.keyboard.press("Delete")
    pg.keyboard.press("Enter")
    return "ok"


def main():
    lines0 = SEED["summary"].split("\n")
    with sync_playwright() as p:
        b = p.chromium.launch()
        # ── 1. 정리 화면 — 보이는 모양 그대로 ──
        print("== 정리 화면(회의록) ==")
        ctx = ctx_for(b, ME)
        pg = open_form(ctx)
        chk("안내 줄 보임(고칠 수 있는 사람 · 정리 있음)", pg.is_visible("#kleHint"))
        n_all = pg.eval_on_selector_all("#mtgSummary > [data-kle]", "e => e.length")
        n_on = pg.eval_on_selector_all("#mtgSummary > [data-kle-on]", "e => e.length")
        chk("줄 = 원래 글 줄 수(%d)" % len(lines0), n_all == len(lines0), n_all)
        chk("빈 줄 빼고 모두 누를 수 있음", n_on == len([x for x in lines0 if x.strip()]), n_on)
        pg.screenshot(path=os.path.join(SHOTS, "form_before.png"), full_page=False)
        geo = """() => { const b = document.getElementById('mtgSummary'); const r = b.getBoundingClientRect();
                 return { h: r.height, tops: Array.from(b.children).map(x => Math.round(x.getBoundingClientRect().top - r.top)),
                          htmls: Array.from(b.children).map(x => x.innerHTML) }; }"""
        g0 = pg.evaluate(geo)
        pg.click(line_sel(6))
        y0 = pg.evaluate("() => window.scrollY")
        pg.wait_for_timeout(300)
        g1 = pg.evaluate(geo)
        chk("고치기 시작해도 화면이 안 움직임", pg.evaluate("() => window.scrollY") == y0)
        ed = pg.evaluate("() => { const e = document.querySelector('%s'); return [e.isContentEditable, e.classList.contains('kle-edit'), document.activeElement === e]; }" % line_sel(6))
        chk("누른 줄만 고치는 칸(같은 자리 · 포커스)", ed == [True, True, True], ed)
        chk("정리 칸 높이 그대로(형태 안 깨짐)", abs(g0["h"] - g1["h"]) <= 2, (g0["h"], g1["h"]))
        chk("모든 줄 자리 그대로", all(abs(a - c) <= 1 for a, c in zip(g0["tops"], g1["tops"])), (g0["tops"][:8], g1["tops"][:8]))
        chk("다른 줄 그림 그대로", all(g0["htmls"][i] == g1["htmls"][i] for i in range(len(g0["htmls"])) if i != 6))
        chk("원래 줄 「## · - · **」 표시가 화면에 안 나옴", "**" not in pg.inner_text(line_sel(8)) and "##" not in pg.inner_text("#mtgSummary"))
        pg.evaluate(SEL_JS, [line_sel(6), "감", 0, False])
        pg.keyboard.type("강")
        pg.screenshot(path=os.path.join(SHOTS, "form_editing.png"), full_page=False)
        pg.keyboard.press("Enter")
        t = toast(pg)
        pg.screenshot(path=os.path.join(SHOTS, "form_saved_toast.png"), full_page=False)
        r = mrow(M1)
        L = r["summary"].split("\n")
        chk("고친 줄 저장(- 강 팀장이 …)", L[6] == "- 강 팀장이 업체에 입고 일정을 다시 확인하기로 했다.", L[6])
        chk("다른 줄 한 글자도 안 바뀜", all(L[i] == lines0[i] for i in range(len(lines0)) if i != 6))
        chk("원문 「감 팀장」 3곳 모두 「강 팀장」", r["body"].count("감 팀장") == 0 and r["body"].count("강 팀장") == 3, r["body"])
        chk("원문 「감자」는 그대로(열쇠 = 앞뒤 3글자)", "감자 이야기" in r["body"])
        chk("알림 = 원문 3곳 · 되돌리기 단추", "3" in t and pg.is_visible(".kle-toast button"), t)
        tv = pg.eval_on_selector("#mtgBody", "e => e.value")
        chk("화면 원문 칸도 새 원문", tv == r["body"])
        chk("「● 저장 안 됨」 안 뜸", not pg.is_visible("#dirtyFlag"))
        g2 = pg.evaluate(geo)
        chk("저장 뒤에도 자리 그대로", all(abs(a - c) <= 1 for a, c in zip(g0["tops"], g2["tops"])))
        # 되돌리기
        pg.click(".kle-toast button")
        t2 = toast(pg)
        r2 = mrow(M1)
        chk("↩ 원문 되돌리기 = 원문만 원래대로", r2["body"] == SEED["body"] and "강 팀장이" in r2["summary"], t2)
        chk("되돌린 원문이 화면 칸에도", pg.eval_on_selector("#mtgBody", "e => e.value") == SEED["body"])
        # 굵은 글씨 안 고침 → ** 그대로 · 원문에 없으면 알림
        edit_replace(pg, line_sel(7), "분리", "구분")
        t3 = toast(pg)
        L = mrow(M1)["summary"].split("\n")
        chk("굵은 글씨 안 고침 = 표시(**·[결정]) 그대로", L[7] == "- [결정] 자재 시트에 **입고 예정일과 실제 입고일을 구분**해 기록한다.", L[7])
        chk("원문에 없는 낱말 = 정리만 고쳤다고 알림", "분리해" in t3, t3)
        chk("[결정] 색 표시 그대로", pg.eval_on_selector(line_sel(7) + " .tg-dec", "e => e.textContent") == "[결정]")
        # 굵은 표시 경계를 넘는 고침 → 글은 맞게 · 굵은 표시만 빠짐
        edit_replace(pg, line_sel(7), "구분해", "나눠")
        toast(pg)
        L = mrow(M1)["summary"].split("\n")
        chk("굵은 경계 넘는 고침 = 보이는 글 그대로 저장", L[7] == "- [결정] 자재 시트에 입고 예정일과 실제 입고일을 나눠 기록한다.", L[7])
        # 숫자
        edit_replace(pg, line_sel(1), "26", "28")
        t4 = toast(pg)
        r4 = mrow(M1)
        chk("숫자 고침 = 그 줄", "현재 28대분은 6대 출하" in r4["summary"], r4["summary"][:120])
        chk("원문 26대분 → 28대분 · 126대분·6대는 그대로", "28대분은 6대 먼저" in r4["body"] and "126대분" in r4["body"], r4["body"])
        # 넣기만(팀장 → 팀장님) — 원문 안 건드림
        b5 = mrow(M1)["body"]
        edit_replace(pg, line_sel(11), "팀장", "님", end=True)
        t5 = toast(pg)
        r5 = mrow(M1)
        chk("넣기만 = 정리만 저장", "- 다음 회의는 팀장님 참석으로 진행한다." in r5["summary"] and r5["body"] == b5, t5)
        # Esc = 취소
        s6 = mrow(M1)["summary"]
        pg.click(line_sel(4))
        pg.keyboard.type("XYZ")
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(500)
        chk("Esc = 안 바뀜(화면·저장)", mrow(M1)["summary"] == s6 and "XYZ" not in pg.inner_text("#mtgSummary"))
        # 다른 곳 누르면 저장
        notoast(pg)
        pg.click(line_sel(4))
        pg.evaluate(SEL_JS, [line_sel(4), "가장 큰", 0, False])
        pg.keyboard.type("제일 큰")
        pg.click("#secSummary .mf-sec-title")
        toast(pg)
        chk("다른 곳 누르면 저장", "제일 큰 원인" in mrow(M1)["summary"])
        # 원문 칸에 저장 안 된 고침이 있으면 원문은 그대로
        pg.fill("#mtgBody", SEED["body"] + " 손으로 더 쓴 글")
        pg.dispatch_event("#mtgBody", "input")
        b7 = mrow(M1)["body"]
        edit_replace(pg, line_sel(6), "강 팀장", "곽 팀장")
        t7 = toast(pg)
        r7 = mrow(M1)
        chk("원문 칸 고치는 중 = 정리만 저장 · 원문 그대로", "곽 팀장이" in r7["summary"] and r7["body"] == b7, t7)
        chk("손으로 쓴 원문 칸 글 그대로", pg.eval_on_selector("#mtgBody", "e => e.value").endswith("손으로 더 쓴 글"))
        # 줄을 비우면 그 줄이 빠진다
        n8 = len(mrow(M1)["summary"].split("\n"))
        notoast(pg)
        pg.click(line_sel(11))
        pg.keyboard.press("Control+A")
        pg.keyboard.press("Delete")
        pg.keyboard.press("Enter")
        toast(pg)
        s8 = mrow(M1)["summary"]
        chk("줄을 비우면 그 줄이 빠짐", len(s8.split("\n")) == n8 - 1 and "다음 회의는" not in s8, s8[-80:])
        ctx.close()

        # ── 2. 다른 사람이 먼저 고쳤으면(409) ──
        print("== 겹친 고침 ==")
        ctx = ctx_for(b, ME)
        pg = open_form(ctx)
        cur = mrow(M1)
        st, _ = http("/api/meeting/%d/summary" % M1, ATT, {"summary": cur["summary"] + "\n- 참석자가 덧붙임", "base_ts": cur["ts"]})
        chk("참석자는 정리 고치기 가능(API 200)", st == 200, st)
        time.sleep(1.1)
        edit_replace(pg, line_sel(3), "자재", "부품")
        t9 = toast(pg)
        chk("먼저 바뀐 것을 덮지 않음(409 알림 · 원래 줄로)", "참석자가 덧붙임" in mrow(M1)["summary"] and "부품 지연과" not in mrow(M1)["summary"]
            and "부품" not in pg.inner_text(line_sel(3)), t9)
        ctx.close()

        # ── 3. 보기만 하는 사람 · 정리 없는 회의 ──
        print("== 권한 · 정리 없음 ==")
        ctx = ctx_for(b, MEM)
        pg = open_form(ctx)
        chk("보기만 = 안내 줄 없음 · 누를 줄 없음", (not pg.is_visible("#kleHint")) and pg.eval_on_selector_all("[data-kle-on]", "e => e.length") == 0)
        pg.goto(BASE + "/meetings/%d/doc" % M1, wait_until="domcontentloaded")
        chk("보기만 = 양식에도 고치기 없음", pg.eval_on_selector_all("[data-klec], [data-kle-on]", "e => e.length") == 0 and "KNKLineEdit" not in pg.content())
        ctx.close()
        cur = mrow(M1)
        st1, _ = http("/api/meeting/%d/summary" % M1, MEM, {"summary": "x", "base_ts": cur["ts"]})
        st2, _ = http("/api/meeting/%d/decision/%d/edit" % (M1, IDS["D1"]), MEM, {"what": "x"})
        st3, _ = http("/api/meeting/%d/action/%d/edit" % (M1, IDS["A1"]), MEM, {"task": "x"})
        st4, _ = http("/api/meeting/%d/body-fix-undo" % M1, MEM, {"fix_id": 1})
        chk("보기만 = 서버도 막음(403 넷)", (st1, st2, st3, st4) == (403, 403, 403, 403), (st1, st2, st3, st4))
        ctx = ctx_for(b, ME)
        pg = open_form(ctx, M2)
        chk("정리 없는 회의 = 안내 줄 없음", not pg.is_visible("#kleHint"))
        ctx.close()
        ctx = ctx_for(b, ATT)
        pg = ctx.new_page()
        pg.goto(BASE + "/meetings/%d/doc" % M1, wait_until="domcontentloaded")
        chk("참석자 = 양식에서 고치기 가능", pg.eval_on_selector_all("[data-klec]", "e => e.length") == 9)
        ctx.close()

        # ── 4. 회의록 양식 ──
        print("== 회의록 양식 ==")
        c = db()
        c.execute("UPDATE meetings SET body=? WHERE id=?", (SEED["body"], M1))
        c.commit()
        c.close()
        ctx = ctx_for(b, ME)
        pg = ctx.new_page()
        pg.goto(BASE + "/meetings/%d/doc" % M1, wait_until="domcontentloaded")
        pg.wait_for_timeout(500)
        sm = mrow(M1)["summary"].split("\n")
        nl = pg.eval_on_selector_all(".sheet .body > .ln[data-kle]", "e => e.length")
        chk("양식 정리 줄 = 원래 글 줄 수", nl == len(sm), (nl, len(sm)))
        chk("양식 안내 줄", "글을 누르면 그 자리에서" in pg.inner_text("body"))
        dgeo = "() => ({ h: document.querySelector('.sheet').getBoundingClientRect().height, tops: Array.from(document.querySelectorAll('.sheet .body > *')).map(x => Math.round(x.getBoundingClientRect().top - document.querySelector('.sheet').getBoundingClientRect().top)) })"
        k = sm.index("- 이번 일정 지연의 제일 큰 원인은 지급품 입고 지연이었다.")
        sel = '.sheet .body > .ln[data-kle="%d"]' % k
        d0 = pg.evaluate(dgeo)
        pg.click(sel)
        pg.wait_for_timeout(200)
        d1 = pg.evaluate(dgeo)
        chk("양식도 형태 그대로(높이·자리)", abs(d0["h"] - d1["h"]) <= 2 and all(abs(a - c) <= 1 for a, c in zip(d0["tops"], d1["tops"])), (d0["h"], d1["h"]))
        pg.evaluate(SEL_JS, [sel, "지급품", 0, False])
        pg.keyboard.type("사급품")
        pg.screenshot(path=os.path.join(SHOTS, "doc_editing.png"), full_page=False)
        pg.keyboard.press("Enter")
        t10 = toast(pg)
        r10 = mrow(M1)
        chk("양식 정리 줄 저장", "제일 큰 원인은 사급품 입고" in r10["summary"], t10)
        chk("양식에서도 원문 고침(지급품 → 사급품)", "사급품이 늦었다" in r10["body"] and "1" in t10, r10["body"])
        # 결정 칸
        sel = '[data-klec="dec:%d:what"]' % IDS["D1"]
        edit_replace(pg, sel, "감", "강")
        t11 = toast(pg)
        c = db()
        w = c.execute("SELECT what, who FROM meeting_decisions WHERE id=?", (IDS["D1"],)).fetchone()
        c.close()
        r11 = mrow(M1)
        chk("결정 칸 저장", w[0] == "강 팀장이 입고 일정표를 매주 공유한다", w)
        chk("결정 칸 고침도 원문에(3곳)", r11["body"].count("강 팀장") == 3 and "3" in t11, t11)
        chk("결정 칸 화면", pg.inner_text(sel) == "강 팀장이 입고 일정표를 매주 공유한다")
        # 기한 빈칸(—) → 날짜
        sel = '[data-klec="dec:%d:due"]' % IDS["D1"]
        notoast(pg)
        pg.click(sel)
        pg.wait_for_timeout(150)
        chk("빈칸은 「—」 없이 비어서 시작", pg.inner_text(sel).strip() == "", pg.inner_text(sel))
        pg.keyboard.type("2026-11-25")
        pg.keyboard.press("Enter")
        toast(pg)
        c = db()
        due = c.execute("SELECT due FROM meeting_decisions WHERE id=?", (IDS["D1"],)).fetchone()[0]
        c.close()
        chk("기한 저장 · 화면", due == "2026-11-25" and pg.inner_text(sel) == "2026-11-25", due)
        # 할 일 담당 → 사람 연결 · 원문은 안 건드림
        b12 = mrow(M1)["body"]
        sel = '[data-klec="act:%d:assignee"]' % IDS["A1"]
        edit_replace(pg, sel, "감팀장", "강팀장")
        toast(pg)
        c = db()
        a = c.execute("SELECT assignee_name, assignee_user_id FROM meeting_actions WHERE id=?", (IDS["A1"],)).fetchone()
        c.close()
        chk("할 일 담당 저장 + 사람 연결", a[0] == "강팀장" and a[1] == KANG, a)
        chk("담당 칸은 원문을 안 건드림", mrow(M1)["body"] == b12)
        # 내용은 비울 수 없다
        sel = '[data-klec="act:%d:task"]' % IDS["A1"]
        notoast(pg)
        pg.click(sel)
        pg.keyboard.press("Control+A")
        pg.keyboard.press("Delete")
        pg.keyboard.press("Enter")
        t13 = toast(pg)
        c = db()
        tk = c.execute("SELECT task FROM meeting_actions WHERE id=?", (IDS["A1"],)).fetchone()[0]
        c.close()
        chk("할 일 내용 비우기 = 막음 · 원래 글로", tk == "업체 입고 일정 다시 확인" and pg.inner_text(sel) == tk, t13)
        # 인쇄 때 안내·알림 안 보임
        pg.emulate_media(media="print")
        hid = pg.evaluate("() => Array.from(document.querySelectorAll('.toolbar')).every(t => getComputedStyle(t).display === 'none')")
        chk("인쇄 = 안내 줄 숨김", hid)
        pg.emulate_media(media="screen")
        ctx.close()

        # ── 5. 휴대폰 ──
        print("== 휴대폰 ==")
        ctx = ctx_for(b, ME, 390, 844, True)
        pg = open_form(ctx)
        pg.evaluate("() => { const d = document.getElementById('worksInstallHint'); if (d) d.remove(); }")   # 앱 설치 안내(시험과 무관)
        g0 = pg.evaluate(geo)
        pg.tap(line_sel(5))
        pg.wait_for_timeout(250)
        g1 = pg.evaluate(geo)
        chk("휴대폰도 누른 줄만 고치는 칸 · 자리 그대로", pg.evaluate("() => document.querySelector('%s').isContentEditable" % line_sel(5))
            and all(abs(a - c) <= 1 for a, c in zip(g0["tops"], g1["tops"])))
        pg.screenshot(path=os.path.join(SHOTS, "phone_editing.png"), full_page=False)
        pg.keyboard.press("Escape")
        ctx.close()
        b.close()

    # ── 6. 서버 막기 · 되돌리기 겹침 ──
    print("== 서버 ==")
    cur = mrow(M1)
    st, d = http("/api/meeting/%d/summary" % M1, ME, {"summary": cur["summary"] + "\n- 하나", "base_ts": cur["ts"], "fix": {"old": "강 팀", "new": "감 팀"}})
    chk("열쇠 공백 뺀 2글자 = 원문 안 건드림", st == 200 and d.get("body_fix") is None and mrow(M1)["body"] == cur["body"], d)
    cur = mrow(M1)
    st, d = http("/api/meeting/%d/summary" % M1, ME, {"summary": cur["summary"] + "\n- 둘", "base_ts": cur["ts"], "fix": {"old": "강 팀장", "new": "감 팀장"}})
    fid = (d.get("body_fix") or {}).get("id")
    chk("API 원문 고침 3곳", st == 200 and (d.get("body_fix") or {}).get("n") == 3 and d.get("body") == mrow(M1)["body"], d.get("body_fix"))
    cur = mrow(M1)
    st, d = http("/api/meeting/%d/summary" % M1, ME, {"summary": cur["summary"] + "\n- 셋", "base_ts": cur["ts"], "fix": {"old": "사급품이", "new": "지급품이"}})
    st, d = http("/api/meeting/%d/body-fix-undo" % M1, ME, {"fix_id": fid})
    chk("그 뒤로 원문이 또 바뀌면 되돌리지 않음(409)", st == 409 and "감 팀장" in mrow(M1)["body"], (st, d))
    st, d = http("/api/meeting/%d/body-fix-undo" % M1, ME, {"fix_id": 99999})
    chk("없는 고침 되돌리기 = 400", st == 400, st)
    st, d = http("/api/meeting/%d/decision/%d/edit" % (M1, IDS["D2"]), ME, {"what": "  "})
    chk("결정 내용 빈칸 = 400", st == 400, st)
    print("결과: 통과 %d · 실패 %d" % (NP[0], NP[1]))
    sys.exit(1 if NP[1] else 0)


main()
