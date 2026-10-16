# -*- coding: utf-8 -*-
"""z1185 검사기 — 「회의록 작성됨」일 때만 「📋 회의록 보기」·「📄 회의록」 켜기.
대표 2026-10-16 (세션 10 전달 · 사진): 「회의록이 녹음 원문 또는 수기 작성이 되지 않았을때는 회의록보기 아이콘은
비활성화가 되어야함.. 회의록보기 아이콘은 회의록이 작성되었을때만 활성화하는게 맞음.」
대표 선택: 진행 (권장) · 기존 3건 그대로 두기 (권장) · 통과하면 바로 (권장)

재는 것 (앱 두 벌 = 운영 그대로(app_base · z1184) · 새것(app_new) · 진짜 서버 · AI 는 맨 끝 한 함수만 가짜 · 진짜 브라우저)
  ⓪ 칸 하나(body_edited_at)만 더하고 **기존 데이터는 안 바꾼다**(엉터리 정리 그대로 · 고친 표시 빈 값)
  ① 이음 카드 단계(이음이 부르는 msg/status 그대로) — 메모만 + 정리 = started(📋 회의록 보기 꺼짐 · 「회의록 등록」 알림 없음) ·
     받아쓴 글 + 정리 = done · 사람이 고친 정리 = done · 「↩ 이전 정리」 맞바꾼 정리 = started · 🔴 반대 시험: 운영은 done
  ② 이음웍스 회의록 목록 「📄 회의록」 — 작성 전 = 꺼짐(양식 링크 없음 · 까닭은 말풍선 · 누르면 까닭만 알림 — 휴대폰엔 말풍선이 없다) ·
     📱 375 폭 · 🔴 반대 시험: 운영은 다 켜짐 · 베트남어 말풍선·알림
  ③ 「▶ 자동 정리 시작」 제안 — 메모만이면 안 띄운다(🔴 반대 시험: 운영은 띄운다) · 이음웍스에서 손으로 쓴 회의는 그대로 띄운다
  ④ 빅터AI 정리 입구 — 메모만이면 **AI 를 안 부르고** 200 + 안내(no_minutes) · 원문 빔 = 예전 그대로 400 · 🔴 반대 시험: 운영은 부른다
  ⑤ 상세 「📄 회의록 양식」 — 작성 전 흐림 · 누르면 까닭만(새 창 안 엶) · 작성된 회의는 새 창 · 🔄 다시 정리 = 주황 안내(빨간 오류 아님) ·
     「회의 내용」을 적고 💾 저장 → **그 자리에서** 켜짐 → 정리 → 이음 단계 done
  ⑥ 원문 저장 판정 — 줄바꿈·띄어쓰기만 다르면 「사람이 씀」 아님 · 글을 더하면 씀 · 새 회의록(원문 있음)도 씀
  ⑦ 「↩ 이전 정리」 맞바꾸기는 「작성」이 아니다 · 그 뒤 사람이 고치면 작성
  ⑧ 메모만인 이음 회의에 녹음 올리기 → 받아쓰기 → 「📄 회의록 양식」 그 자리에서 켜짐 → 자동 정리 → done
  ⑨ 끝난 뒤 목록 — 방금 작성된 회의들의 📄 가 켜짐
  ⑩ 코드 한 곳 — 판정 함수 하나를 세 입구(이음 시작·이음 상태·모아보기 카드)가 같이 쓴다 · 회의록 양식 화면은 안 바뀜
  ⑪ 콘솔 오류 0
쓰는 법: py q85_check.py <app_base·app_new 가 있는 폴더>
판정: **종료코드**(0=통과) + 요약 줄.
"""
import hashlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1] if len(sys.argv) > 1 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
PB, PN = 8925, 8926
KEY = "q85-test-key"   # 시험 서버의 시험용 공유키(run_q85_app.py) — 운영 키 아님
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
KNOWN = "Transition was skipped"   # 운영에도 있는 공용 화면 전환 경고(z1182 확인) — 이번 변경 밖
MT_OFF_KO = "아직 회의록이 작성되지 않았습니다 — 녹음을 올리거나 회의 내용을 적으면 열립니다"
MT_OFF_VI = "Biên bản chưa được soạn — tải bản ghi âm lên hoặc ghi nội dung cuộc họp thì sẽ mở được"
DOC_OFF_KO = "아직 회의록이 작성되지 않았습니다 — 녹음을 올리거나 「회의 내용」 칸에 적어 저장하면 열립니다."
DOC_OFF_VI = "Biên bản chưa được soạn — hãy tải bản ghi âm lên hoặc ghi vào ô 「Nội dung cuộc họp」 rồi lưu thì sẽ mở được."
NOMIN_KO = "아직 회의 내용이 없습니다 — 녹음을 올리거나 「회의 내용」 칸에 먼저 적어 주세요(이음 회의 메모만으로는 정리하지 않습니다)."
OK = FAIL = 0


def chk(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (name, detail))


def freeport(port):
    ps = ("Get-NetTCPConnection -State Listen -LocalPort %d -ErrorAction SilentlyContinue | "
          "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }") % port
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
    for _ in range(50):
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "@(Get-NetTCPConnection -State Listen -LocalPort %d -ErrorAction SilentlyContinue).Count" % port],
                           capture_output=True, text=True)
        if (r.stdout or "").strip() in ("0", ""):
            return True
        time.sleep(0.2)
    raise SystemExit("!! 포트 %d 를 비우지 못했다" % port)


def boot(app, port):
    freeport(port)
    sp = os.path.join(HERE, "seed_%d.json" % port)
    if os.path.exists(sp):
        os.remove(sp)
    lp = os.path.join(APPDIR, "srv_%d.log" % port)
    pr = subprocess.Popen([P313, os.path.join(HERE, "run_q85_app.py"), os.path.join(APPDIR, app), str(port)],
                          stdout=io.open(lp, "w", encoding="utf-8"), stderr=subprocess.STDOUT, cwd=APPDIR)
    for _ in range(600):
        time.sleep(0.2)
        s = io.open(lp, encoding="utf-8").read() if os.path.exists(lp) else ""
        if "READY" in s and os.path.exists(sp):
            return pr, json.loads(io.open(sp, encoding="utf-8").read())
        if pr.poll() is not None:
            print(s[-2500:])
            raise SystemExit("!! %s(%d) 가 떴다 죽었다" % (app, port))
    raise SystemExit("!! %s(%d) 가 안 떴다" % (app, port))


def kill(*prs):
    for pr in prs:
        try:
            pr.terminate()
        except Exception:
            pass


U = lambda port, path: "http://127.0.0.1:%d%s" % (port, path)


def db(app, sql, args=()):
    """서버가 쓰는 DB 를 **읽기만** 한다."""
    p = os.path.join(APPDIR, app, "data", "knk.db").replace("\\", "/")
    c = sqlite3.connect("file:%s?mode=ro" % p, uri=True, timeout=10)
    c.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in c.execute(sql, args)]
    finally:
        c.close()


def mrow(app, mid):
    return db(app, "SELECT * FROM meetings WHERE id=?", (mid,))[0]


def wait_until(fn, timeout=30.0, step=0.25):
    t0 = time.time()
    v = None
    while time.time() - t0 < timeout:
        try:
            v = fn()
        except Exception:
            v = None
        if v:
            return v
        time.sleep(step)
    return v


def page_for(br, port, uid, w=1280, h=1000):
    ctx = br.new_context(viewport={"width": w, "height": h})
    ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": "http://127.0.0.1:%d" % port}])
    pg = ctx.new_page()
    pg.add_init_script("try{localStorage.setItem('knk_works_install_hint_never','1');}catch(e){}")
    D = {"msgs": []}

    def on_dialog(d):
        if d.type == "beforeunload":   # 화면을 옮길 때의 「나가시겠습니까」는 시험 대상이 아니다 — 늘 나간다
            d.accept()
            return
        D["msgs"].append(d.message)
        d.accept()
    pg.on("dialog", on_dialog)
    errs = []
    pg.on("console", lambda m: errs.append("console: " + m.text[:160]) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:160]))
    return ctx, pg, errs, D


def post(pg, port, path, body=None, method="POST"):
    f = pg.request.put if method == "PUT" else pg.request.post
    r = f(U(port, path), data=json.dumps(body or {}), headers={"Content-Type": "application/json"})
    try:
        return r.status, r.json()
    except Exception:
        return r.status, {}


def mstatus(pg, port, ids, emp="901"):
    """이음이 부르는 그대로 — 서버 간 공유키(시험용) + 사번."""
    r = pg.request.post(U(port, "/api/meeting/msg/status"),
                        data=json.dumps({"employee_no": emp, "msg_meeting_ids": ids}),
                        headers={"Content-Type": "application/json", "X-SSO-Service-Key": KEY})
    return r.status, (r.json() if r.status == 200 else {})


def calls(pg, port):
    return pg.request.get(U(port, "/__test/ai_calls")).json()["cnt"]["m"]


LIST_JS = """() => Array.from(document.querySelectorAll('.mtg-row')).map(function(r){
  var c = r.querySelector('.mtg-card'), a = r.querySelector('a.mtg-act[href$="/doc"]'), off = r.querySelector('.mtg-act.off');
  return { id: c ? +(c.getAttribute('data-mid') || 0) : 0, link: a ? a.getAttribute('href') : '',
           off: off ? off.getAttribute('title') : null, tag: off ? off.tagName : '', aria: off ? off.getAttribute('aria-disabled') : null,
           op: off ? getComputedStyle(off).opacity : '', cur: off ? getComputedStyle(off).cursor : '',
           txt: off ? off.textContent.trim() : '' }; })"""
DOCBTN_JS = """() => { var b = document.getElementById('btnDocView'); if (!b) return null;
  return { cls: b.className, aria: b.getAttribute('aria-disabled'), title: b.getAttribute('title'),
           op: +getComputedStyle(b).opacity, cur: getComputedStyle(b).cursor, href: b.getAttribute('href'), txt: b.textContent.trim() }; }"""
PIPE_JS = """() => { var c = document.getElementById('pipeCard'), g = document.getElementById('pipeGo');
  return { card: c ? !c.hidden : null, go: g ? !g.hidden : null, steps: (document.getElementById('pipeSteps') || {}).innerText || '' }; }"""


def by_id(rows):
    return {r["id"]: r for r in rows}


pb = pn = None
wav = os.path.join(APPDIR, "q85_fake.wav")
try:
    pb, sb = boot("app_base", PB)
    pn, sn = boot("app_new", PN)
    IB, IN = sb["ids"], sn["ids"]
    MSG = {"E1": 701, "E2": 702, "E3": 703, "E4": 704, "E5": 705, "E6": 706, "E7": 707, "E8": 708, "E9": 709}
    print("운영 그대로 %d · 새것 %d · 회의 %s" % (PB, PN, json.dumps(IN, ensure_ascii=False)))
    with sync_playwright() as p:
        br = p.chromium.launch()
        cb, gb, eb, DB_ = page_for(br, PB, sb["me"])
        cn, gn, en, DN = page_for(br, PN, sn["me"])

        # ═══════════ ⓪ 칸 · 기존 데이터 ═══════════
        print("\n── ⓪ 칸 하나만 더하고 기존 데이터는 안 바꾼다 ──")
        chk("새것: meetings.body_edited_at 칸이 생겼다", sn["has_body_edited"] is True)
        chk("🔴 반대 시험: 운영 그대로엔 그 칸이 없다", sb["has_body_edited"] is False)
        allrows = db("app_new", "SELECT id, body_edited_at, summary FROM meetings")
        chk("기존 회의록은 모두 「고친 적 없음」(빈 값)으로 시작 — 데이터를 채우지 않는다(%d건)" % len(allrows),
            all((r["body_edited_at"] or "") == "" for r in allrows), [r for r in allrows if r["body_edited_at"]][:2])
        chk("기동이 엉터리 정리를 지우지 않는다(대표 「그대로 두기」)", mrow("app_new", IN["E1"])["summary"] == sn["junk"])

        # ═══════════ ① 이음 카드 단계 ═══════════
        print("\n── ① 이음 카드 단계(msg/status — 이음이 부르는 그대로) ──")
        ids = list(MSG.values())
        stn, jn = mstatus(gn, PN, ids)
        stb, jb = mstatus(gb, PB, ids)
        chk("두 서버 다 200(시험용 공유키)", (stn, stb) == (200, 200), (stn, stb))
        N = {k: (jn.get("items") or {}).get(str(v), {}) for k, v in MSG.items()}
        B = {k: (jb.get("items") or {}).get(str(v), {}) for k, v in MSG.items()}
        want = {"E1": "started", "E2": "started", "E3": "done", "E4": "done", "E5": "started",
                "E6": "started", "E7": "started", "E8": "started", "E9": "started"}
        for k, w in want.items():
            chk("%s → %s (%s)" % (k, w, N[k].get("stage")), N[k].get("stage") == w, N[k])
        chk("🔴 핵심: 메모만 + 엉터리 정리(E1) = 「정리 끝」 아님 → 이음 「📋 회의록 보기」 꺼짐 · 「회의록 등록」 알림 없음",
            N["E1"].get("stage") != "done")
        chk("E1 주소 = 회의록 화면(녹음 올리기·작성하기) · 양식 아님", N["E1"].get("url") == "/meetings/%d" % IN["E1"], N["E1"].get("url"))
        chk("E3 받아쓴 글 = 양식으로 바로", N["E3"].get("url") == "/meetings/%d/doc" % IN["E3"], N["E3"].get("url"))
        chk("E4 사람이 고친 정리 = 양식으로 바로", N["E4"].get("url") == "/meetings/%d/doc" % IN["E4"], N["E4"].get("url"))
        chk("단계 값은 다섯 가지 안에서만(이음과의 약속)",
            {x.get("stage") for x in N.values()} <= {"started", "recorded", "processing", "failed", "done"})
        chk("🔴 반대 시험: 운영은 E1(메모만 + 엉터리 정리)을 done 으로 보낸다", B["E1"].get("stage") == "done", B["E1"])
        chk("🔴 반대 시험: 운영은 E1 주소가 양식", B["E1"].get("url") == "/meetings/%d/doc" % IB["E1"], B["E1"].get("url"))
        chk("🔴 반대 시험: 운영은 E5(맞바꾼 정리)도 done", B["E5"].get("stage") == "done", B["E5"])
        chk("운영과 같은 것: E3·E4 done · E2·E6 started",
            [B[k].get("stage") for k in ("E3", "E4", "E2", "E6")] == ["done", "done", "started", "started"],
            [B[k].get("stage") for k in ("E3", "E4", "E2", "E6")])

        # ═══════════ ② 목록 📄 회의록 ═══════════
        print("\n── ② 이음웍스 회의록 목록 「📄 회의록」 ──")
        gn.goto(U(PN, "/meetings"), wait_until="domcontentloaded")
        gn.wait_for_selector(".mtg-row", timeout=20000)
        Ln = by_id(gn.evaluate(LIST_JS))
        on_k = ["E3", "E4", "N1", "N3"]
        off_k = ["E1", "E2", "E5", "E6", "E7", "E8", "E9", "N2"]
        for k in on_k:
            r = Ln.get(IN[k], {})
            chk("%s 📄 켜짐(양식 링크)" % k, r.get("link") == "/meetings/%d/doc" % IN[k] and r.get("off") is None, r)
        for k in off_k:
            r = Ln.get(IN[k], {})
            chk("%s 📄 꺼짐(링크 없음 · 까닭 말풍선)" % k, not r.get("link") and r.get("off") == MT_OFF_KO, r)
        r1 = Ln.get(IN["E1"], {})
        chk("꺼진 📄 = 누를 수 없는 칸(span · aria-disabled) · 흐림 · 금지 커서 · 「📄 회의록」 글자 그대로",
            r1.get("tag") == "SPAN" and r1.get("aria") == "true" and abs(float(r1.get("op") or 1) - 0.42) < 0.02
            and r1.get("cur") == "not-allowed" and r1.get("txt") == "📄회의록", r1)
        gn.screenshot(path=os.path.join(SHOTS, "q85_list_new.png"), full_page=False)
        #  휴대폰엔 말풍선이 없다 → 꺼진 📄 를 누르면 까닭만 알린다(aria-disabled 라 Playwright 는 force — 사람 손은 그냥 눌린다)
        u0 = gn.url
        DN["msgs"] = []
        gn.locator('.mtg-row:has(.mtg-card[data-mid="%d"]) .mtg-act.off' % IN["E1"]).click(force=True)
        gn.wait_for_timeout(900)
        chk("꺼진 📄 를 누르면 까닭만 알린다(알림 1번 · 글 = 말풍선) · 화면은 그대로", DN["msgs"] == [MT_OFF_KO] and gn.url == u0,
            (DN["msgs"], gn.url))
        pm = cn.pages[:]
        gm = cn.new_page()
        gm.set_viewport_size({"width": 375, "height": 800})
        gm.goto(U(PN, "/meetings"), wait_until="domcontentloaded")
        gm.wait_for_selector(".mtg-row", timeout=20000)
        mob = gm.evaluate("""(id) => { var r = document.querySelector('.mtg-card[data-mid="' + id + '"]').closest('.mtg-row');
            var o = r.querySelector('.mtg-act.off'), t = o.querySelector('.mtg-act-t');
            return { tdisp: getComputedStyle(t).display, op: getComputedStyle(o).opacity,
                     overflow: document.documentElement.scrollWidth > window.innerWidth }; }""", IN["E1"])
        chk("📱 375 폭: 꺼진 📄 는 그림만(글자 숨김 — 다른 아이콘과 같은 규칙) · 흐림 · 옆으로 안 밀림",
            mob["tdisp"] == "none" and abs(float(mob["op"]) - 0.42) < 0.02 and not mob["overflow"], mob)
        gm.screenshot(path=os.path.join(SHOTS, "q85_list_new_375.png"), full_page=False)
        gm.close()
        gb.goto(U(PB, "/meetings"), wait_until="domcontentloaded")
        gb.wait_for_selector(".mtg-row", timeout=20000)
        Lb = by_id(gb.evaluate(LIST_JS))
        chk("🔴 반대 시험: 운영은 모든 줄의 📄 가 켜져 있다(메모만인 E1·빈 원문 N2 도)",
            all(Lb.get(IB[k], {}).get("link") for k in on_k + off_k) and not any(Lb.get(IB[k], {}).get("off") for k in off_k))
        gb.screenshot(path=os.path.join(SHOTS, "q85_list_base.png"), full_page=False)
        cv, gv, ev, DV = page_for(br, PN, sn["vnu"])
        gv.goto(U(PN, "/meetings"), wait_until="domcontentloaded")
        gv.wait_for_selector(".mtg-row", timeout=20000)
        Lv = by_id(gv.evaluate(LIST_JS))
        chk("베트남어 직원: 꺼진 📄 말풍선 = 베트남어", Lv.get(IN["E1"], {}).get("off") == MT_OFF_VI, Lv.get(IN["E1"]))
        chk("베트남어 직원: 작성된 회의(E3)는 켜짐", Lv.get(IN["E3"], {}).get("link") == "/meetings/%d/doc" % IN["E3"])
        DV["msgs"] = []
        gv.locator('.mtg-row:has(.mtg-card[data-mid="%d"]) .mtg-act.off' % IN["E1"]).click(force=True)
        gv.wait_for_timeout(900)
        chk("베트남어 직원: 꺼진 📄 를 누르면 알림도 베트남어", DV["msgs"] == [MT_OFF_VI], DV["msgs"])

        # ═══════════ ③ 「▶ 자동 정리 시작」 제안 ═══════════
        print("\n── ③ 「▶ 자동 정리 시작」 제안 ──")
        gn.goto(U(PN, "/meetings/%d" % IN["E2"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#btnExtractTop", timeout=20000)
        gn.wait_for_timeout(600)
        pe2 = gn.evaluate(PIPE_JS)
        chk("메모만(E2) → 제안 안 띄움(진행 칸 감춤 · ▶ 단추 감춤)", pe2["card"] is False and pe2["go"] is False, pe2)
        gb.goto(U(PB, "/meetings/%d" % IB["E2"]), wait_until="domcontentloaded")
        gb.wait_for_selector("#btnExtractTop", timeout=20000)
        gb.wait_for_timeout(600)
        pb2 = gb.evaluate(PIPE_JS)
        chk("🔴 반대 시험: 운영은 메모만(E2)에도 「▶ 자동 정리 시작」을 띄운다(→ 회의 내용 없는 정리)", pb2["go"] is True, pb2)
        gn.goto(U(PN, "/meetings/%d" % IN["N1"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#btnExtractTop", timeout=20000)
        gn.wait_for_timeout(600)
        pn1 = gn.evaluate(PIPE_JS)
        chk("이음웍스에서 손으로 쓴 회의(N1)는 그대로 제안", pn1["go"] is True, pn1)

        # ═══════════ ④ 빅터AI 정리 입구 ═══════════
        print("\n── ④ 빅터AI 정리 입구 ──")
        c0 = calls(gn, PN)
        st, d = post(gn, PN, "/api/meeting/%d/extract" % IN["E1"])
        time.sleep(1.2)
        chk("메모만(E1) → 200 · ok:false · no_minutes(정상 흐름 — 콘솔 빨간 오류 없음)",
            st == 200 and d.get("ok") is False and d.get("no_minutes") is True, (st, d))
        chk("서버 안내 글 = 「녹음을 올리거나 「회의 내용」 칸에 먼저 적어 주세요」",
            "아직 회의 내용이 없습니다" in (d.get("error") or "") and "회의 내용" in (d.get("error") or ""), d.get("error"))
        chk("🔴 AI 를 **안 불렀다**(%d → %d)" % (c0, calls(gn, PN)), calls(gn, PN) == c0)
        chk("엉터리 정리 그대로(대표 「그대로 두기」)", mrow("app_new", IN["E1"])["summary"] == sn["junk"])
        st6, d6 = post(gn, PN, "/api/meeting/%d/extract" % IN["E6"])
        st6b, d6b = post(gb, PB, "/api/meeting/%d/extract" % IB["E6"])
        chk("원문 빔(E6) = 예전 그대로 400 「비어 있습니다」(운영과 같음)",
            st6 == 400 and "비어 있습니다" in (d6.get("error") or "") and st6b == 400, (st6, d6, st6b))
        cb0 = calls(gb, PB)
        stb1, db1 = post(gb, PB, "/api/meeting/%d/extract" % IB["E1"])
        gotb = wait_until(lambda: calls(gb, PB) > cb0, 15)
        chk("🔴 반대 시험: 운영은 메모만(E1)으로도 AI 를 불러 정리한다", stb1 == 200 and db1.get("started") and bool(gotb), (stb1, db1))
        c1 = calls(gn, PN)
        stn1, dn1 = post(gn, PN, "/api/meeting/%d/extract" % IN["N1"])
        okn1 = wait_until(lambda: "가짜 정리" in (mrow("app_new", IN["N1"])["summary"] or ""), 30)
        chk("이음웍스에서 손으로 쓴 회의(N1)는 그대로 정리된다", stn1 == 200 and dn1.get("started") and bool(okn1)
            and calls(gn, PN) == c1 + 1, (stn1, dn1))

        # ═══════════ ⑤ 상세 「📄 회의록 양식」 · 안내 · 저장하면 그 자리에서 켜짐 ═══════════
        print("\n── ⑤ 상세 화면 「📄 회의록 양식」 ──")
        gn.goto(U(PN, "/meetings/%d" % IN["E1"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#btnDocView", timeout=20000)
        b1 = gn.evaluate(DOCBTN_JS)
        chk("E1: 흐림(mf-doc-off · 흐린 정도 0.45 · 금지 커서) · aria-disabled · 말풍선 = 까닭",
            "mf-doc-off" in b1["cls"] and b1["aria"] == "true" and abs(b1["op"] - 0.45) < 0.02 and b1["cur"] == "not-allowed"
            and b1["title"] == MT_OFF_KO, b1)
        chk("E1: 단추 글자·주소는 그대로(「📄 회의록 양식」)", b1["txt"] == "📄 회의록 양식" and b1["href"] == "/meetings/%d/doc" % IN["E1"], b1)
        n_pages = len(cn.pages)
        DN["msgs"] = []
        #  aria-disabled 는 Playwright 가 「안 눌림」으로 보고 기다린다 — 사람 손은 눌린다 → force(진짜 마우스 누름 그대로)
        gn.click("#btnDocView", force=True)
        gn.wait_for_timeout(1200)
        chk("E1: 누르면 까닭만 알린다(알림 창 1번 · 글 그대로)", DN["msgs"] == [DOC_OFF_KO], DN["msgs"])
        chk("E1: 새 창을 열지 않는다", len(cn.pages) == n_pages, len(cn.pages))
        gn.screenshot(path=os.path.join(SHOTS, "q85_detail_E1_off.png"), full_page=False)
        gb.goto(U(PB, "/meetings/%d" % IB["E1"]), wait_until="domcontentloaded")
        gb.wait_for_selector('a[href="/meetings/%d/doc"]' % IB["E1"], timeout=20000)
        bcls = gb.get_attribute('a[href="/meetings/%d/doc"]' % IB["E1"], "class") or ""
        chk("🔴 반대 시험: 운영은 메모만(E1)도 「📄 회의록 양식」이 켜져 있다", "mf-doc-off" not in bcls, bcls)
        gn.goto(U(PN, "/meetings/%d" % IN["E3"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#btnDocView", timeout=20000)
        b3 = gn.evaluate(DOCBTN_JS)
        chk("E3(받아쓴 글): 켜짐 · 말풍선 없음", "mf-doc-off" not in b3["cls"] and b3["aria"] is None and b3["title"] is None, b3)
        with cn.expect_page(timeout=15000) as pi:
            gn.click("#btnDocView")
        np_ = pi.value
        np_.wait_for_load_state("domcontentloaded")
        chk("E3: 누르면 새 창에 회의록 양식", np_.url.endswith("/meetings/%d/doc" % IN["E3"]), np_.url)
        np_.close()

        print("\n── ⑤-2 메모만(E2): 🔄 다시 정리 → 안내 · 「회의 내용」 적고 💾 저장 → 그 자리에서 켜짐 ──")
        gn.goto(U(PN, "/meetings/%d" % IN["E2"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#btnExtractTop", timeout=20000)
        b2 = gn.evaluate(DOCBTN_JS)
        chk("E2: 처음엔 흐림", "mf-doc-off" in b2["cls"], b2)
        c2 = calls(gn, PN)
        e_before = len(en)
        gn.click("#btnExtractTop")
        got2 = wait_until(lambda: "아직 회의 내용이 없습니다" in gn.inner_text("#sumSt2"), 15)
        col = gn.evaluate("() => getComputedStyle(document.getElementById('sumSt2')).color")
        chk("🔄 다시 정리 → 정리 칸 밑에 안내(글 그대로)", bool(got2) and gn.inner_text("#sumSt2").strip() == NOMIN_KO,
            gn.inner_text("#sumSt2"))
        chk("안내 = 주황(실패 빨강 아님)", col == "rgb(180, 83, 9)", col)
        chk("AI 안 부름 · 진행 칸 닫힘 · 단추 다시 눌림",
            calls(gn, PN) == c2 and gn.evaluate("() => { var a = document.getElementById('aiBusy'); return !a || a.hidden; }")
            and gn.evaluate("() => !document.getElementById('btnExtractTop').disabled"))
        chk("콘솔 빨간 오류 없음(안내는 200)", len([e for e in en[e_before:] if KNOWN not in e]) == 0, en[e_before:])
        gn.screenshot(path=os.path.join(SHOTS, "q85_detail_E2_guide.png"), full_page=False)
        body0 = gn.input_value("#mtgBody")
        gn.fill("#mtgBody", body0 + "\n실제 회의 내용: 출하일을 11월 20일로 정했습니다. 셋업은 25일부터.")
        gn.click("#btnSave")
        lit = wait_until(lambda: "mf-doc-off" not in gn.evaluate(DOCBTN_JS)["cls"], 15)
        b2b = gn.evaluate(DOCBTN_JS)
        chk("💾 저장 → **그 자리에서**(새로 고침 없이) 「📄 회의록 양식」이 켜진다",
            bool(lit) and b2b["aria"] is None and b2b["title"] is None, b2b)
        chk("서버: 사람이 원문을 쓴 시각이 적혔다", bool((mrow("app_new", IN["E2"])["body_edited_at"] or "").strip()))
        gn.click("#btnExtractTop")
        ok2 = wait_until(lambda: "가짜 정리" in (mrow("app_new", IN["E2"])["summary"] or ""), 30)
        chk("그 뒤 🔄 다시 정리 → 빅터AI 정리가 된다", bool(ok2) and calls(gn, PN) == c2 + 1)
        _, j2 = mstatus(gn, PN, [MSG["E2"]])
        chk("→ 이음 단계 done(📋 회의록 보기 · 「회의록 등록」 알림)", (j2.get("items") or {}).get(str(MSG["E2"]), {}).get("stage") == "done", j2)
        gn.screenshot(path=os.path.join(SHOTS, "q85_detail_E2_written.png"), full_page=False)

        # ═══════════ ⑥ 원문 저장 판정 ═══════════
        print("\n── ⑥ 원문 저장 = 사람이 썼나 ──")
        e8 = mrow("app_new", IN["E8"])
        st8, d8 = post(gn, PN, "/api/meeting/%d" % IN["E8"], {"title": e8["title"], "body": "첫 줄\n둘째 줄"}, "PUT")
        chk("줄바꿈만 다름(CRLF → LF) → 「사람이 씀」 아님 · 꺼진 그대로",
            st8 == 200 and d8.get("has_minutes") is False and d8.get("body_written") is False
            and (mrow("app_new", IN["E8"])["body_edited_at"] or "") == "", (st8, d8))
        st8b, d8b = post(gn, PN, "/api/meeting/%d" % IN["E8"], {"title": "E8 제목만 바꿈", "body": "  첫 줄 \n\n 둘째 줄  "}, "PUT")
        chk("띄어쓰기·빈 줄만 다름 + 제목만 바꿈 → 아님", st8b == 200 and d8b.get("has_minutes") is False
            and (mrow("app_new", IN["E8"])["body_edited_at"] or "") == "", (st8b, d8b))
        st8c, d8c = post(gn, PN, "/api/meeting/%d" % IN["E8"], {"title": "E8 제목만 바꿈", "body": "첫 줄\n둘째 줄\n셋째 줄(사람이 더 씀)"}, "PUT")
        chk("글을 더함 → 「사람이 씀」 · 켜짐", st8c == 200 and d8c.get("has_minutes") is True and d8c.get("body_written") is True
            and bool((mrow("app_new", IN["E8"])["body_edited_at"] or "").strip()), (st8c, d8c))
        stc, dc = post(gn, PN, "/api/meeting", {"title": "새 회의 손으로", "body": "손으로 쓴 새 회의 내용"})
        chk("이음웍스 새 회의록(원문 있음) → 쓴 시각 적힘", stc == 200 and dc.get("ok")
            and bool((mrow("app_new", dc.get("id"))["body_edited_at"] or "").strip()), (stc, dc))
        stc2, dc2 = post(gn, PN, "/api/meeting", {"title": "새 회의 빈", "body": ""})
        chk("이음웍스 새 회의록(원문 없음) → 빈 값", stc2 == 200 and dc2.get("ok")
            and (mrow("app_new", dc2.get("id"))["body_edited_at"] or "") == "", (stc2, dc2))
        stb8, db8 = post(gb, PB, "/api/meeting/%d" % IB["E8"], {"title": "E8", "body": "첫 줄\n둘째 줄"}, "PUT")
        chk("운영 그대로의 저장 응답은 예전 모양(판정 칸 없음 — 새 칸만 덧붙였다)",
            stb8 == 200 and db8.get("ok") and "has_minutes" not in db8, db8)

        # ═══════════ ⑦ 「↩ 이전 정리」 맞바꾸기 ═══════════
        print("\n── ⑦ 「↩ 이전 정리」 맞바꾸기는 「작성」이 아니다 ──")
        st9, d9 = post(gn, PN, "/api/meeting/%d/summary-restore" % IN["E9"])
        r9 = mrow("app_new", IN["E9"])
        chk("맞바꿈 → 고친 시각 = 보관 시각(같은 값으로 함께 적힘 — 판정이 기대는 것)",
            st9 == 200 and d9.get("ok") and r9["summary_edited_at"] and r9["summary_edited_at"] == r9["summary_prev_at"], (st9, r9.get("summary_edited_at"), r9.get("summary_prev_at")))
        chk("맞바꾼 정리 = 「작성」 아님(응답 · 이음 단계 started)", d9.get("has_minutes") is False
            and (mstatus(gn, PN, [MSG["E9"]])[1].get("items") or {}).get(str(MSG["E9"]), {}).get("stage") == "started", d9)
        time.sleep(1.3)   # 사람 손은 1초보다 느리다 — 같은 초면 맞바꿈과 구별이 안 된다(설명서에 적음)
        st9b, d9b = post(gn, PN, "/api/meeting/%d/summary" % IN["E9"], {"summary": "## 핵심\n사람이 다시 적은 회의 정리"})
        chk("그 뒤 사람이 ✏ 고치기로 정리를 적음 → 「작성」 · 이음 단계 done", st9b == 200 and d9b.get("has_minutes") is True
            and (mstatus(gn, PN, [MSG["E9"]])[1].get("items") or {}).get(str(MSG["E9"]), {}).get("stage") == "done", d9b)

        # ═══════════ ⑧ 녹음 올리기 ═══════════
        print("\n── ⑧ 메모만인 이음 회의(E7)에 녹음 올리기 ──")
        with open(wav, "wb") as f:
            f.write(b"RIFF" + (b"\0" * 4096))
        gn.goto(U(PN, "/meetings/%d" % IN["E7"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#redoTools #recFile", state="attached", timeout=20000)
        chk("E7: 올리기 전엔 흐림", "mf-doc-off" in gn.evaluate(DOCBTN_JS)["cls"])
        c7 = calls(gn, PN)
        gn.locator("#redoTools #recFile").set_input_files(wav)
        done7 = wait_until(lambda: "모두 끝났습니다" in gn.inner_text("#pipeSteps"), 60)
        steps7 = gn.inner_text("#pipeSteps") if gn.locator("#pipeSteps").count() else ""
        r7 = mrow("app_new", IN["E7"])
        chk("받아쓴 글이 원문에 들어간다", "[음성 변환]" in (r7["body"] or "") and "[가짜 변환]" in (r7["body"] or ""), (r7["body"] or "")[-60:])
        chk("자동 정리까지 끝 · ❌ 없음 · 「내용 없음」 안내 없음", bool(done7) and "❌" not in steps7 and NOMIN_KO not in steps7, steps7)
        chk("빅터AI 정리가 됐다(AI 1번)", "가짜 정리" in (r7["summary"] or "") and calls(gn, PN) == c7 + 1)
        chk("「📄 회의록 양식」이 **그 자리에서** 켜졌다", "mf-doc-off" not in gn.evaluate(DOCBTN_JS)["cls"])
        _, j7 = mstatus(gn, PN, [MSG["E7"]])
        chk("→ 이음 단계 done", (j7.get("items") or {}).get(str(MSG["E7"]), {}).get("stage") == "done", j7)
        gn.screenshot(path=os.path.join(SHOTS, "q85_detail_E7_upload.png"), full_page=False)

        # ═══════════ ⑨ 끝난 뒤 목록 ═══════════
        print("\n── ⑨ 끝난 뒤 목록 — 방금 작성된 회의의 📄 가 켜짐 ──")
        gn.goto(U(PN, "/meetings"), wait_until="domcontentloaded")
        gn.wait_for_selector(".mtg-row", timeout=20000)
        L2 = by_id(gn.evaluate(LIST_JS))
        for k in ("E2", "E7", "E8", "E9"):
            chk("%s 📄 이제 켜짐" % k, L2.get(IN[k], {}).get("link") == "/meetings/%d/doc" % IN[k], L2.get(IN[k]))
        for k in ("E1", "E5", "E6", "N2"):
            chk("%s 📄 그대로 꺼짐" % k, L2.get(IN[k], {}).get("off") == MT_OFF_KO, L2.get(IN[k]))

        # ═══════════ 베트남어 상세 ═══════════
        print("\n── 베트남어 직원 상세 화면 ──")
        gv.goto(U(PN, "/meetings/%d" % IN["E1"]), wait_until="domcontentloaded")
        gv.wait_for_selector("#btnDocView", timeout=20000)
        bv = gv.evaluate(DOCBTN_JS)
        chk("말풍선 = 베트남어", bv["title"] == MT_OFF_VI and "mf-doc-off" in bv["cls"], bv)
        DV["msgs"] = []
        gv.click("#btnDocView", force=True)
        gv.wait_for_timeout(1000)
        chk("누르면 알림도 베트남어", DV["msgs"] == [DOC_OFF_VI], DV["msgs"])
        gv.screenshot(path=os.path.join(SHOTS, "q85_detail_E1_vi.png"), full_page=False)

        # ═══════════ ⑩ 코드 한 곳 ═══════════
        print("\n── ⑩ 판정 한 곳 · 그대로인 것 ──")
        srcn = io.open(os.path.join(APPDIR, "app_new", "app", "main.py"), encoding="utf-8").read()
        srcb = io.open(os.path.join(APPDIR, "app_base", "app", "main.py"), encoding="utf-8").read()
        chk("판정 함수 = 하나씩(원문 내용 · 회의록 작성됨)",
            srcn.count("def _meeting_body_written(") == 1 and srcn.count("def _meeting_has_minutes(") == 1)
        _st = '"stage": _meeting_msg_stage(m)'
        chk("이음 단계를 쓰는 세 곳(회의 시작·상태·모아보기 카드)이 같은 단계 함수 — 운영과 같은 수",
            srcn.count(_st) == srcb.count(_st) == 3, (srcn.count(_st), srcb.count(_st)))
        chk("단계 함수의 done 줄이 판정 함수를 본다",
            'if (m.get("summary") or "").strip() and _meeting_has_minutes(m):\n        return "done"' in srcn)
        md = lambda app, rel: hashlib.md5(io.open(os.path.join(APPDIR, app, "app", rel), "rb").read()).hexdigest()
        chk("📄 회사 공식 회의록 양식 화면은 안 바뀜(파일 그대로)", md("app_base", "templates/meeting_doc.html") == md("app_new", "templates/meeting_doc.html"))
        for frag in ('"제목 없는 회의 " + today, today, "B"',   # 녹음기 공유로 새 회의(share_new)
                     'str(d.get("note") or "").strip()[:4000]'):  # 이음 「▶ 회의 시작」 새 회의록 = 메모 씨앗
            chk("그대로: %s" % frag[:40], srcb.count(frag) == srcn.count(frag) == 1)

        # ═══════════ ⑪ 콘솔 ═══════════
        print("\n── ⑪ 콘솔 ──")
        other = [e for e in en + ev if KNOWN not in e]
        chk("새것 화면 콘솔 오류 0", not other, other[:3])
        otherb = [e for e in eb if KNOWN not in e]
        chk("운영 화면 콘솔 오류 0", not otherb, otherb[:3])
        br.close()
finally:
    kill(pb, pn)
    try:
        os.remove(wav)
    except Exception:
        pass

print("\n사진: %s" % SHOTS)
print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
