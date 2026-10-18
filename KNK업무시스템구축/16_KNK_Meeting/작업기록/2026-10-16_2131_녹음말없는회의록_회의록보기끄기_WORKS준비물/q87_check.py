# -*- coding: utf-8 -*-
"""z1187 검사기 — 녹음은 있으나 알아들을 말이 거의 없는 회의록도 「작성 안 됨」.
대표 2026-10-16 「이전에 회의록들은 확인을 안한건가?? 이전 회의록 등록안한건 아직 그대로 인데...」 → 「진행 (권장)」 · 「통과하면 바로 (권장)」
기준: 받아쓴 글에서 알아들을 수 있는 말(한글·라틴·숫자 글자 · 받아쓰기 헛말·같은 문장 되풀이·외국 글자 빼고)이 200자 이상일 때만 「녹음 원문 있음」.
운영 실측(10-16): 엉터리 5건 0·0·10·15·70자 ↔ 진짜 회의 가장 짧은 것 426자.

재는 것 (앱 두 벌 = 운영 그대로(app_base · z1185) · 새것(app_new) · 진짜 서버 · AI 는 맨 끝 한 함수만 가짜 · 진짜 브라우저)
  ⓪ 판정 도우미 값 — 헛말 0 · 시험 한마디 10 · 「감사합니다」 되풀이 · 기준 아래·위 · 회의 말 · 베트남어
  ① 이음 카드 단계(msg/status) — 헛말·외국 글자·시험·되풀이·메모+한 문장 = started(「정리 실패」·「정리 대기」 아님) ·
     회의 말 충분·사람이 고침·베트남어 = done · 🔴 반대 시험: 운영은 그것들을 done(정리 전이면 recorded)
  ② 목록 「📄 회의록」 꺼짐/켜짐 · 🔴 반대 시험: 운영은 켜짐
  ③ 정리 입구 — 헛말이면 AI 를 안 부르고 200 + no_minutes(reason = stt_short · 「녹음에서 알아들을 수 있는 말이 거의 없습니다」) ·
     메모만은 z1185 안내 그대로(reason = memo) · 회의 말 충분은 정리된다 · 🔴 반대 시험: 운영은 헛말로도 AI 를 부른다
  ④ 상세 「🔄 다시 정리」 → 정리 칸 밑 주황 안내(한국어 · 베트남어)
  ⑤ 녹음 올리기 — 잡음 녹음 → 받아쓰기 ✅ → ⚠ 안내(AI 안 부름 · 📄 꺼진 그대로 · 이음 started) → 회의 녹음을 다시 올림 → 정리 → done ·
     처음부터 회의 녹음이면 done · 🔴 반대 시험: 운영은 잡음 녹음도 정리해 done
  ⑥ 판정 한 곳 · 회의록 양식 화면 그대로
  ⑦ 콘솔 오류 0
쓰는 법: py q87_check.py <app_base·app_new 가 있는 폴더>
판정: **종료코드**(0=통과) + 요약 줄.
"""
import ast
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
PB, PN = 8927, 8928
KEY = "q87-test-key"   # 시험 서버의 시험용 공유키(run_q87_app.py) — 운영 키 아님
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
KNOWN = "Transition was skipped"   # 운영에도 있는 공용 화면 전환 경고(z1182 확인) — 이번 변경 밖
STT_KO = "녹음에서 알아들을 수 있는 말이 거의 없습니다 — 녹음이 제대로 됐는지 확인해 다시 올리거나 「회의 내용」 칸에 적어 주세요."
STT_VI = "Bản ghi âm gần như không có lời nói nghe được — hãy kiểm tra bản ghi rồi tải lên lại, hoặc ghi vào ô 「Nội dung cuộc họp」."
MEMO_KO = "아직 회의 내용이 없습니다"
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
    pr = subprocess.Popen([P313, os.path.join(HERE, "run_q87_app.py"), os.path.join(APPDIR, app), str(port)],
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
        if d.type == "beforeunload":
            d.accept()
            return
        D["msgs"].append(d.message)
        d.accept()
    pg.on("dialog", on_dialog)
    errs = []
    pg.on("console", lambda m: errs.append("console: " + m.text[:160]) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:160]))
    return ctx, pg, errs, D


def post(pg, port, path, body=None):
    r = pg.request.post(U(port, path), data=json.dumps(body or {}), headers={"Content-Type": "application/json"})
    try:
        return r.status, r.json()
    except Exception:
        return r.status, {}


def mstatus(pg, port, ids, emp="901"):
    r = pg.request.post(U(port, "/api/meeting/msg/status"),
                        data=json.dumps({"employee_no": emp, "msg_meeting_ids": ids}),
                        headers={"Content-Type": "application/json", "X-SSO-Service-Key": KEY})
    return r.status, (r.json() if r.status == 200 else {})


def stage(pg, port, msg_id):
    return ((mstatus(pg, port, [msg_id])[1].get("items") or {}).get(str(msg_id)) or {})


def calls(pg, port):
    return pg.request.get(U(port, "/__test/ai_calls")).json()["cnt"]["m"]


LIST_JS = """() => Array.from(document.querySelectorAll('.mtg-row')).map(function(r){
  var c = r.querySelector('.mtg-card'), a = r.querySelector('a.mtg-act[href$="/doc"]'), off = r.querySelector('.mtg-act.off');
  return { id: c ? +(c.getAttribute('data-mid') || 0) : 0, link: a ? a.getAttribute('href') : '', off: off ? off.getAttribute('title') : null }; })"""
DOCBTN_JS = """() => { var b = document.getElementById('btnDocView'); return b ? { cls: b.className } : null; }"""


def helpers(app):
    """그 앱의 main.py 에서 판정 도우미만 꺼낸다(앱은 띄우지 않는다)."""
    src = io.open(os.path.join(APPDIR, app, "app", "main.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in ("_mtg_split_stt", "_stt_meaningful_len"))
            or (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in ("_STT_HALLU_RE", "_STT_READ_RE", "_MTG_STT_MIN_CHARS")
                                                  for t in n.targets))
            or (isinstance(n, ast.Import) and any(a.asname == "_re87" for a in n.names))]
    ns = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), "main.py", "exec"), ns)
    return ns


pb = pn = None
wav = os.path.join(APPDIR, "q87_noise.wav")
wav2 = os.path.join(APPDIR, "q87_talk.wav")
try:
    pb, sb = boot("app_base", PB)
    pn, sn = boot("app_new", PN)
    IB, IN = sb["ids"], sn["ids"]
    MSG = {"G1": 801, "G2": 802, "G3": 803, "G4": 804, "G5": 805, "G6": 806, "G7": 807, "G8": 808, "G9": 809, "G10": 810,
           "U1": 811, "U2": 812, "M1": 813, "V1": 814}
    print("운영 그대로 %d · 새것 %d · 회의 %s" % (PB, PN, json.dumps(IN, ensure_ascii=False)))

    # ═══════════ ⓪ 판정 도우미 값 ═══════════
    print("\n── ⓪ 알아들을 말 세기(새 main.py 의 도우미 그대로) ──")
    H = helpers("app_new")
    L = H["_stt_meaningful_len"]
    MIN = H["_MTG_STT_MIN_CHARS"]
    chk("기준 = 200자", MIN == 200, MIN)
    v = {k: L("🎤 [음성 변환]\n" + sn[k]) for k in ("foreign", "jp", "test1", "thanks", "chat", "below", "above", "talk", "vi_talk")}
    print("    " + " · ".join("%s %d" % kv for kv in v.items()))
    chk("외국 글자·일본어 헛말 = 0자", v["foreign"] == 0 and v["jp"] == 0, v)
    chk("녹음 시험 한마디 10자 · 잡담+「시청해 주셔서 감사합니다」 50자 안", v["test1"] == 10 and v["chat"] < 50, v)
    chk("「감사합니다」 120번 되풀이 = 한 번만 센다(5자)", v["thanks"] == 5, v["thanks"])
    chk("기준 바로 아래 < 200 ≤ 기준 바로 위", v["below"] < MIN <= v["above"], (v["below"], v["above"]))
    chk("회의 말(한국어·베트남어) 200자 넘음", v["talk"] >= MIN and v["vi_talk"] >= MIN, (v["talk"], v["vi_talk"]))
    chk("🔴 반대: 운영 그대로엔 이 도우미가 없다(받아쓴 글이 있기만 하면 봤다)", "_stt_meaningful_len" not in helpers("app_base"))

    with sync_playwright() as p:
        br = p.chromium.launch()
        cb, gb, eb, DB_ = page_for(br, PB, sb["me"])
        cn, gn, en, DN = page_for(br, PN, sn["me"])

        # ═══════════ ① 이음 카드 단계 ═══════════
        print("\n── ① 이음 카드 단계(msg/status) ──")
        ids = list(MSG.values())
        _, jn = mstatus(gn, PN, ids)
        _, jb = mstatus(gb, PB, ids)
        N = {k: (jn.get("items") or {}).get(str(v), {}) for k, v in MSG.items()}
        B = {k: (jb.get("items") or {}).get(str(v), {}) for k, v in MSG.items()}
        want = {"G1": "started", "G2": "started", "G3": "started", "G4": "started", "G5": "started", "G6": "done",
                "G7": "started", "G8": "done", "G9": "done", "G10": "done", "U1": "started", "U2": "started",
                "M1": "started", "V1": "started"}
        for k, w in want.items():
            chk("%s → %s (%s)" % (k, w, N[k].get("stage")), N[k].get("stage") == w, N[k])
        chk("헛말 회의는 「📋 회의록 보기」 대신 회의록 화면 주소(녹음 올리기·작성하기)",
            all(N[k].get("url") == "/meetings/%d" % IN[k] for k in ("G1", "G2", "G3", "G4", "G5", "G7")),
            [N[k].get("url") for k in ("G1", "G5")])
        chk("정리 전 헛말(V1)은 「정리 대기」·「정리 실패」가 아니다(다시 올리거나 적게)", N["V1"].get("stage") == "started", N["V1"])
        chk("🔴 반대 시험: 운영은 헛말·외국 글자·시험·되풀이·메모+한 문장을 done 으로 보낸다",
            all(B[k].get("stage") == "done" for k in ("G1", "G2", "G3", "G4", "G5", "G7")),
            {k: B[k].get("stage") for k in ("G1", "G2", "G3", "G4", "G5", "G7")})
        chk("🔴 반대 시험: 운영은 정리 전 헛말(V1)을 「정리 대기」(recorded)", B["V1"].get("stage") == "recorded", B["V1"])
        chk("운영과 같은 것: 회의 말 충분·사람이 고침·베트남어 = done",
            all(B[k].get("stage") == "done" for k in ("G6", "G8", "G9", "G10")))

        # ═══════════ ② 목록 📄 ═══════════
        print("\n── ② 목록 「📄 회의록」 ──")
        gn.goto(U(PN, "/meetings"), wait_until="domcontentloaded")
        gn.wait_for_selector(".mtg-row", timeout=20000)
        Ln = {r["id"]: r for r in gn.evaluate(LIST_JS)}
        for k in ("G1", "G2", "G3", "G4", "G5", "G7", "H1", "V1"):
            chk("%s 📄 꺼짐" % k, not Ln.get(IN[k], {}).get("link") and Ln.get(IN[k], {}).get("off"), Ln.get(IN[k]))
        for k in ("G6", "G8", "G9", "G10", "H2"):
            chk("%s 📄 켜짐" % k, Ln.get(IN[k], {}).get("link") == "/meetings/%d/doc" % IN[k], Ln.get(IN[k]))
        gn.screenshot(path=os.path.join(SHOTS, "q87_list_new.png"), full_page=False)
        gb.goto(U(PB, "/meetings"), wait_until="domcontentloaded")
        gb.wait_for_selector(".mtg-row", timeout=20000)
        Lb = {r["id"]: r for r in gb.evaluate(LIST_JS)}
        chk("🔴 반대 시험: 운영은 헛말 회의(G1~G5·G7·H1)의 📄 가 켜져 있다",
            all(Lb.get(IB[k], {}).get("link") for k in ("G1", "G2", "G3", "G4", "G5", "G7", "H1")))

        # ═══════════ ③ 정리 입구 ═══════════
        print("\n── ③ 빅터AI 정리 입구 ──")
        c0 = calls(gn, PN)
        st1, d1 = post(gn, PN, "/api/meeting/%d/extract" % IN["G1"])
        sth, dh = post(gn, PN, "/api/meeting/%d/extract" % IN["H1"])
        stm, dm = post(gn, PN, "/api/meeting/%d/extract" % IN["M1"])
        time.sleep(1.2)
        chk("헛말(G1) → 200 · no_minutes · reason stt_short · 안내 글",
            st1 == 200 and d1.get("no_minutes") is True and d1.get("reason") == "stt_short"
            and "알아들을 수 있는 말이 거의 없습니다" in (d1.get("error") or ""), (st1, d1))
        chk("이음웍스 직접 회의 헛말만(H1)도 stt_short", sth == 200 and dh.get("reason") == "stt_short", (sth, dh))
        chk("메모만(M1)은 z1185 안내 그대로(reason memo)", stm == 200 and dm.get("reason") == "memo"
            and MEMO_KO in (dm.get("error") or ""), (stm, dm))
        chk("🔴 AI 를 **안 불렀다**(%d → %d)" % (c0, calls(gn, PN)), calls(gn, PN) == c0)
        chk("엉터리 정리 그대로(지난번 대표 결정대로 지우지 않음)", mrow("app_new", IN["G1"])["summary"] == sn["junk"])
        st8, d8 = post(gn, PN, "/api/meeting/%d/extract" % IN["G8"])
        ok8 = wait_until(lambda: "가짜 정리" in (mrow("app_new", IN["G8"])["summary"] or ""), 30)
        chk("기준 바로 위(G8)는 그대로 정리된다", st8 == 200 and d8.get("started") and bool(ok8) and calls(gn, PN) == c0 + 1, (st8, d8))
        cb0 = calls(gb, PB)
        stb, dbb = post(gb, PB, "/api/meeting/%d/extract" % IB["G1"])
        gotb = wait_until(lambda: calls(gb, PB) > cb0, 15)
        chk("🔴 반대 시험: 운영은 헛말(G1)로도 AI 를 불러 정리한다", stb == 200 and dbb.get("started") and bool(gotb), (stb, dbb))

        # ═══════════ ④ 상세 「🔄 다시 정리」 안내 ═══════════
        print("\n── ④ 상세 화면 「🔄 다시 정리」 → 안내 ──")
        gn.goto(U(PN, "/meetings/%d" % IN["G3"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#btnExtractTop", timeout=20000)
        c4 = calls(gn, PN)
        e4 = len(en)
        gn.click("#btnExtractTop")
        got4 = wait_until(lambda: "알아들을 수 있는 말이 거의 없습니다" in gn.inner_text("#sumSt2"), 15)
        col = gn.evaluate("() => getComputedStyle(document.getElementById('sumSt2')).color")
        chk("한국어 안내 글 그대로 · 주황", bool(got4) and gn.inner_text("#sumSt2").strip() == STT_KO and col == "rgb(180, 83, 9)",
            (gn.inner_text("#sumSt2"), col))
        chk("AI 안 부름 · 콘솔 빨간 오류 없음", calls(gn, PN) == c4 and not [e for e in en[e4:] if KNOWN not in e], en[e4:])
        chk("「📄 회의록 양식」 흐림", "mf-doc-off" in (gn.evaluate(DOCBTN_JS) or {}).get("cls", ""))
        gn.screenshot(path=os.path.join(SHOTS, "q87_detail_G3_guide.png"), full_page=False)
        cv, gv, ev, DV = page_for(br, PN, sn["vnu"])
        gv.goto(U(PN, "/meetings/%d" % IN["V1"]), wait_until="domcontentloaded")
        gv.wait_for_selector("#btnExtractTop", timeout=20000)
        gv.wait_for_timeout(500)
        pv = gv.evaluate("() => { var g = document.getElementById('pipeGo'); return g ? !g.hidden : null; }")
        chk("베트남어 직원(V1 작성자): 헛말뿐이면 「▶ 자동 정리 시작」 제안 없음", pv is False, pv)
        gv.click("#btnExtractTop")
        gotv = wait_until(lambda: "Bản ghi âm gần như không có lời nói" in gv.inner_text("#sumSt2"), 15)
        chk("베트남어 안내 글 그대로", bool(gotv) and gv.inner_text("#sumSt2").strip() == STT_VI, gv.inner_text("#sumSt2"))
        gv.screenshot(path=os.path.join(SHOTS, "q87_detail_V1_vi.png"), full_page=False)

        # ═══════════ ⑤ 녹음 올리기 ═══════════
        print("\n── ⑤ 녹음 올리기 — 잡음 → 안내 → 다시 올리기 → 정리 ──")
        for f in (wav, wav2):
            with open(f, "wb") as fh:
                fh.write(b"RIFF" + (b"\0" * 4096))
        gn.request.get(U(PN, "/__test/stt?mode=noise"))
        c5 = calls(gn, PN)
        gn.goto(U(PN, "/meetings/%d" % IN["U1"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#redoTools #recFile", state="attached", timeout=20000)
        gn.locator("#redoTools #recFile").set_input_files(wav)
        got5 = wait_until(lambda: "알아들을 수 있는 말이 거의 없습니다" in gn.inner_text("#pipeSteps"), 60)
        steps5 = gn.inner_text("#pipeSteps") if gn.locator("#pipeSteps").count() else ""
        r5 = mrow("app_new", IN["U1"])
        chk("받아쓰기는 끝나 원문에 들어간다(헛말)", "[음성 변환]" in (r5["body"] or "") and "[가짜 변환]" in (r5["body"] or ""))
        chk("진행 칸 = ✅ 받아쓰기 → ⚠ 안내(❌ 아님)", bool(got5) and "✅" in steps5 and "⚠" in steps5 and "❌" not in steps5, steps5)
        chk("AI 안 부름 · 정리 없음", calls(gn, PN) == c5 and not (r5["summary"] or "").strip(), (calls(gn, PN), c5))
        chk("「📄 회의록 양식」은 꺼진 그대로", "mf-doc-off" in (gn.evaluate(DOCBTN_JS) or {}).get("cls", ""))
        chk("이음 단계 = started(「정리 대기」·「정리 실패」 아님)", stage(gn, PN, MSG["U1"]).get("stage") == "started",
            stage(gn, PN, MSG["U1"]))
        gn.screenshot(path=os.path.join(SHOTS, "q87_upload_noise.png"), full_page=False)
        gn.request.get(U(PN, "/__test/stt?mode=talk"))
        gn.goto(U(PN, "/meetings/%d" % IN["U1"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#redoTools #recFile", state="attached", timeout=20000)
        gn.locator("#redoTools #recFile").set_input_files(wav2)
        done5 = wait_until(lambda: "모두 끝났습니다" in gn.inner_text("#pipeSteps"), 60)
        r5b = mrow("app_new", IN["U1"])
        chk("회의 녹음을 다시 올리면 → 정리된다(AI 1번)", bool(done5) and "가짜 정리" in (r5b["summary"] or "")
            and calls(gn, PN) == c5 + 1, gn.inner_text("#pipeSteps"))
        chk("「📄 회의록 양식」이 그 자리에서 켜짐 · 이음 단계 done",
            "mf-doc-off" not in (gn.evaluate(DOCBTN_JS) or {}).get("cls", "x")
            and stage(gn, PN, MSG["U1"]).get("stage") == "done", stage(gn, PN, MSG["U1"]))
        gn.screenshot(path=os.path.join(SHOTS, "q87_upload_again.png"), full_page=False)
        c6 = calls(gn, PN)
        gn.goto(U(PN, "/meetings/%d" % IN["U2"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#redoTools #recFile", state="attached", timeout=20000)
        gn.locator("#redoTools #recFile").set_input_files(wav2)
        done6 = wait_until(lambda: "모두 끝났습니다" in gn.inner_text("#pipeSteps"), 60)
        chk("처음부터 회의 녹음(U2) → 정리 · done", bool(done6) and calls(gn, PN) == c6 + 1
            and stage(gn, PN, MSG["U2"]).get("stage") == "done", gn.inner_text("#pipeSteps"))
        gb.request.get(U(PB, "/__test/stt?mode=noise"))
        cb5 = calls(gb, PB)
        gb.goto(U(PB, "/meetings/%d" % IB["U1"]), wait_until="domcontentloaded")
        gb.wait_for_selector("#redoTools #recFile", state="attached", timeout=20000)
        gb.locator("#redoTools #recFile").set_input_files(wav)
        doneb = wait_until(lambda: "가짜 정리" in (mrow("app_base", IB["U1"])["summary"] or ""), 60)
        chk("🔴 반대 시험: 운영은 잡음 녹음도 정리해 「정리 끝」", bool(doneb) and calls(gb, PB) == cb5 + 1
            and stage(gb, PB, MSG["U1"]).get("stage") == "done", stage(gb, PB, MSG["U1"]))

        # ═══════════ ⑥ 판정 한 곳 · 그대로인 것 ═══════════
        print("\n── ⑥ 판정 한 곳 · 그대로인 것 ──")
        srcn = io.open(os.path.join(APPDIR, "app_new", "app", "main.py"), encoding="utf-8").read()
        chk("기준 값·세는 함수 = 한 곳", srcn.count("_MTG_STT_MIN_CHARS = 200") == 1 and srcn.count("def _stt_meaningful_len(") == 1)
        chk("이음 단계: 받아쓰기 끝 + 알아들을 말 없음 = started 줄",
            srcn.count('if "[음성 변환]" in (m.get("body") or "") and not _meeting_body_written(m):') == 1)
        chk("정리 입구: reason 칸", srcn.count('"no_minutes": True, "reason": _why') == 1)
        md = lambda app, rel: hashlib.md5(io.open(os.path.join(APPDIR, app, "app", rel), "rb").read()).hexdigest()
        chk("📄 회사 공식 회의록 양식 화면 그대로", md("app_base", "templates/meeting_doc.html") == md("app_new", "templates/meeting_doc.html"))

        # ═══════════ ⑦ 콘솔 ═══════════
        print("\n── ⑦ 콘솔 ──")
        other = [e for e in en + ev if KNOWN not in e]
        chk("새것 화면 콘솔 오류 0", not other, other[:3])
        otherb = [e for e in eb if KNOWN not in e]
        chk("운영 화면 콘솔 오류 0", not otherb, otherb[:3])
        br.close()
finally:
    kill(pb, pn)
    for f in (wav, wav2):
        try:
            os.remove(f)
        except Exception:
            pass

print("\n사진: %s" % SHOTS)
print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
