# -*- coding: utf-8 -*-
"""z1193 검사기 — 회의록 「📊 한눈에 보기」(도식화 · 추가 화면).
대표 2026-10-20 「회의 내용을 이미지화 또는 도식화해서 더 쉽게 이해할수있는 페이지를 추가」 · 「글로된 회의록 정리는 그대로 … 추가로」 ·
시안 v2(설비 배치도처럼 · 그림 위주 · 휴대폰 세로 · 종류별) → 「만들기 시작」

재는 것 (앱 두 벌 = 운영 그대로(app_base) · 새것(app_new) · 진짜 서버 · 진짜 브라우저 · AI 는 맨 끝 ai_chat 하나만 가짜)
  ━ 서버 안 띄움 ━
  ① 🔴 글 정리는 그대로 — 정리·음성 메모 지시문 글자 그대로 · ai_extract_meeting/ai_extract_note 코드 그대로 · 그리기 규칙 파일 그대로
  ② 바뀐 자리: 새 파일 2(마이그레이션 · 화면) · main.py 는 더한 줄만 · 양식 1줄 · 상세 6줄 · 화면 글 3줄
  ③ 그림 자료 다듬기(_viz_norm): 종류·수 제한·엉뚱한 type·기한 꼴 · 근거 표시(_viz_mark_src)
  ━ 진짜 서버 ━
  ④ 켜짐·꺼짐 = 📄 양식과 같다 — V2(정리 없음)·V3(헛말) 은 만들기 200+no_minutes · 화면 안내 · 상세 단추 흐림
  ⑤ V1 만들기: 시작만 알리고(started) 화면이 묻는다 → done · DB 에 viz_json·kind·지문 · 기록 [VIZ] 숫자만(회의 글 없음)
  ⑥ V1 화면: 종류 표시 · 숫자 3 · 구역 3(검사 구역 색) · 단계 수·엉뚱한 type→step · 정한 것 12(잘림)+더 보기 · 확인 필요 2 · 할 일 3(기한 꼴 틀린 것 지움) ·
     일정 3(확인 표시 1) · 부품 1 · 되돌아가는 흐름 · 근거 창(원문 찾음 · 정리 글에서 찾음 · 못 찾음) · 머리줄 「14:00 ~ 14:50 (50분)」
  ⑦ V4 정리가 바뀐 그림 → 「다시 그리기」 안내 → 다시 그리면 안내 사라짐 · 지문 새로
  ⑧ 권한: V5 남의 대외비 → 화면 303 · 상태 403 · 만들기 403 / V6 공개 회의 보는 사람 → 화면 200 · 만들기 단추 없음 · 만들기 403
  ⑨ V7 AI 오류 → 상태 error · viz_json 그대로 비어 있음
  ⑩ 상세·양식 단추: V1 켜짐(주소 /viz) · 베트남어 직원 글 「📊 Xem tổng quan」 · 양식 toolbar 「📊 한눈에 보기」 · 🔴 반대: 운영엔 /viz 404 · 단추 없음
  ⑪ V8 정리를 돌리면 AI 가 받는 지시문·원문이 운영과 글자 그대로(정리 흐름 무접촉)
  ⑫ 휴대폰 세로(390) 사진 · PC 사진 · 콘솔 오류 0
쓰는 법: py q93_check.py <app_base·app_new 가 있는 폴더>   판정: 종료코드(0=통과) + 요약 줄.  🔒 시험 글은 모두 지어낸 것.
"""
import ast
import difflib
import hashlib
import importlib.util
import io
import json
import os
import re
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
PB, PN = 8943, 8944
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
KNOWN = "Transition was skipped"
OK = FAIL = 0


def chk(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (name, str(detail)[:700]))


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
    pr = subprocess.Popen([P313, os.path.join(HERE, "run_q93_app.py"), os.path.join(APPDIR, app), str(port)],
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
    p = os.path.join(APPDIR, app, "data", "knk.db").replace("\\", "/")
    c = sqlite3.connect("file:%s?mode=ro" % p, uri=True, timeout=10)
    c.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in c.execute(sql, args)]
    finally:
        c.close()


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


def page_for(br, port, uid, w=1100, h=1000, mobile=False):
    ctx = br.new_context(viewport={"width": w, "height": h}, is_mobile=mobile, device_scale_factor=(2 if mobile else 1))
    ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": "http://127.0.0.1:%d" % port}])
    pg = ctx.new_page()
    pg.add_init_script("try{localStorage.setItem('knk_works_install_hint_never','1');}catch(e){}")
    D = {"msgs": []}

    def on_dialog(d):
        D["msgs"].append(d.message)
        d.accept()
    pg.on("dialog", on_dialog)
    errs = []
    pg.on("console", lambda m: errs.append("console: " + m.text[:160]) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:160]))
    return pg, errs, D


def get(pg, port, path):
    r = pg.request.get(U(port, path), max_redirects=0)
    try:
        return r.status, r.text(), r.headers
    except Exception:
        return r.status, "", r.headers


def post(pg, port, path, body=None):
    r = pg.request.post(U(port, path), data=json.dumps(body or {}), headers={"Content-Type": "application/json"})
    try:
        return r.status, r.json()
    except Exception:
        return r.status, {}


def load_mod(app, name):
    p = os.path.join(APPDIR, app, "app", "ai_client.py")
    spec = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def fn_src(path, name):
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return ast.dump(n)
    return None


print("\n── ① 🔴 글 정리는 그대로 ──")
AB, AN = load_mod("app_base", "q93_aic_b"), load_mod("app_new", "q93_aic_n")
chk("회의록 정리 지시문 그대로", AN._MEETING_EXTRACT_SYSTEM == AB._MEETING_EXTRACT_SYSTEM)
chk("음성 메모 정리 지시문 그대로", AN._NOTE_EXTRACT_SYSTEM == AB._NOTE_EXTRACT_SYSTEM)
chk("회사 맥락 그대로", AN._KNK_MEETING_CONTEXT == AB._KNK_MEETING_CONTEXT)
pb_, pn_ = os.path.join(APPDIR, "app_base", "app", "ai_client.py"), os.path.join(APPDIR, "app_new", "app", "ai_client.py")
for f in ("ai_extract_meeting", "ai_extract_note", "_mark_vietnamese", "ai_transcribe", "ai_transcribe_window"):
    chk("%s 코드 그대로" % f, fn_src(pb_, f) == fn_src(pn_, f))
chk("그림 자료 지시문에 「그림 자료」·JSON 틀·근거 규칙", "그림 자료" in AN._VIZ_EXTRACT_SYSTEM and '"kind":"equip|sales|internal"' in AN._VIZ_EXTRACT_SYSTEM
    and "q(근거)" in AN._VIZ_EXTRACT_SYSTEM and "글을 새로 쓰지 않는다" in AN._VIZ_EXTRACT_SYSTEM)
chk("그림 자료 지시문은 정리 지시문과 다른 글(정리 지시문엔 「그림 자료」 없음)", "그림 자료" not in AN._MEETING_EXTRACT_SYSTEM and "그림 자료" not in AN._NOTE_EXTRACT_SYSTEM)
mdh = lambda app, rel: hashlib.md5(io.open(os.path.join(APPDIR, app, "app", rel), "rb").read()).hexdigest()
for rel in ("templates/_v5_partials/knk_md_lite.html", "templates/meetings.html", "templates/voice_note_form.html"):
    chk("%s 그대로" % rel, mdh("app_base", rel) == mdh("app_new", rel))

print("\n── ② 바뀐 자리 ──")
chk("새 파일 2 — 마이그레이션 · 화면", os.path.exists(os.path.join(APPDIR, "app_new", "app", "migrations", "m_z1193_meeting_viz.py"))
    and os.path.exists(os.path.join(APPDIR, "app_new", "app", "templates", "meeting_viz.html"))
    and not os.path.exists(os.path.join(APPDIR, "app_base", "app", "templates", "meeting_viz.html")))
mb = io.open(os.path.join(APPDIR, "app_base", "app", "main.py"), encoding="utf-8").read().splitlines()
mn = io.open(os.path.join(APPDIR, "app_new", "app", "main.py"), encoding="utf-8").read().splitlines()
dl = [d for d in difflib.unified_diff(mb, mn, lineterm="", n=0) if d[:1] in "+-" and not d.startswith(("+++", "---"))]
chk("main.py = 더한 줄만(뺀 줄 0) · 두 자리(기동 마이그레이션 · 양식 뒤 📊 묶음)", not [d for d in dl if d.startswith("-")]
    and sum(1 for d in dl if "MEETING-VIZ-MIG-Z1193" in d) >= 1 and any("def meeting_viz_page" in d for d in dl)
    and any('@app.post("/api/meeting/{mid:int}/viz")' in d for d in dl) and any("def _viz_worker" in d for d in dl), len(dl))
chk("전역 timedelta 새로 안 씀", not any("timedelta" in d for d in dl))


def ndiff(rel):
    a = io.open(os.path.join(APPDIR, "app_base", "app", rel), encoding="utf-8").read().splitlines()
    b = io.open(os.path.join(APPDIR, "app_new", "app", rel), encoding="utf-8").read().splitlines()
    d = [x for x in difflib.unified_diff(a, b, lineterm="", n=0) if x[:1] in "+-" and not x.startswith(("+++", "---"))]
    return sum(1 for x in d if x[0] == "+"), sum(1 for x in d if x[0] == "-")
chk("양식(meeting_doc.html) = 「📊 한눈에 보기」 1줄만", ndiff("templates/meeting_doc.html") == (1, 0), ndiff("templates/meeting_doc.html"))
fdiff = ndiff("templates/meeting_form.html")
fn_new = io.open(os.path.join(APPDIR, "app_new", "app", "templates", "meeting_form.html"), encoding="utf-8").read()
chk("상세(meeting_form.html) = 더한 줄만(뺀 줄 0) · 단추·vizSync·정리 생길 때 켜짐·누름 안내", fdiff[1] == 0 and 10 <= fdiff[0] <= 16
    and 'id="btnVizView"' in fn_new and fn_new.count("vizSync();") == 2 and "function vizSync()" in fn_new and "MF.viz_off" in fn_new, fdiff)
chk("화면 글(i18n.py) = mf_viz · mf_viz_off · mf_viz_off_t (7줄 · 뺀 줄 0)", ndiff("i18n.py") == (7, 0), ndiff("i18n.py"))

print("\n── ③ 그림 자료 다듬기 · 근거 표시 ──")
raw = {"kind": "EQUIP", "headline": "x" * 200, "numbers": [{"v": "1", "label": "a", "q": ""}] * 9, "decided": [{"t": "d%d" % i, "q": ""} for i in range(20)],
       "todo": [{"t": "t", "who": "", "due": "25일", "q": ""}, {"t": "t2", "who": "", "due": "2026-10-24", "q": ""}, {"t": "", "q": ""}],
       "flow": {"zones": [{"name": "z", "steps": [{"label": "s", "type": "weird"}]}]}, "timeline": [{"t": "x", "sure": False}], "parts": "not-a-list"}
n = AN._viz_norm(raw)
chk("대문자 종류 → internal(모르는 값은 내부 회의) · 머리글 90자", n["kind"] == "internal" and len(n["headline"]) == 90)
chk("숫자 6개 · 정한 것 12개로 잘림 · 빈 할 일 버림 · 기한 꼴 아니면 지움", len(n["numbers"]) == 6 and len(n["decided"]) == 12 and len(n["todo"]) == 2
    and n["todo"][0]["due"] == "" and n["todo"][1]["due"] == "2026-10-24", n["todo"])
chk("설비 아니면 흐름 비움 · parts 가 목록 아니면 빈 목록 · timeline sure 보존", n["flow"]["zones"] == [] and n["parts"] == [] and n["timeline"][0]["sure"] is False)
n2 = AN._viz_norm(dict(raw, kind="equip"))
chk("설비면 흐름 살림 · 엉뚱한 type → step", len(n2["flow"]["zones"]) == 1 and n2["flow"]["zones"][0]["steps"][0]["type"] == "step")
#  근거 표시는 main.py 에서 — 함수만 꺼내 본다
src = io.open(os.path.join(APPDIR, "app_new", "app", "main.py"), encoding="utf-8").read()
tree = ast.parse(src)
ns = {}
exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name in ("_viz_mark_src", "_viz_sig")]
                        + [x for x in tree.body if isinstance(x, ast.Import) and any(a.asname == "_hl93" for a in x.names)], type_ignores=[]), "m", "exec"), ns)
v = {"numbers": [{"q": "출하는 11월 20일로"}, {"q": "출하는  11월\n20일로"}, {"q": "없는 구절"}, {"q": ""}], "decided": [{"q": "정리에만 있음"}],
     "open": [], "todo": [], "timeline": [], "parts": [], "flow": {"zones": [{"steps": [{"q": "포장은 그 전날"}]}]}}
f, t = ns["_viz_mark_src"](v, "출하는 11월 20일로 하고 포장은 그 전날까지", "정리에만 있음")
chk("근거: 원문 2(빈칸·줄바꿈 무시) · 정리 1 · 못 찾음 1 · 빈 q 는 안 셈 → 4/5",
    (f, t) == (4, 5) and [x["src"] for x in v["numbers"]] == ["body", "body", "", ""] and v["decided"][0]["src"] == "summary"
    and v["flow"]["zones"][0]["steps"][0]["src"] == "body", (f, t, v))
chk("정리 지문 12자 · 앞뒤 빈칸 무시", len(ns["_viz_sig"]("## 핵심")) == 12 and ns["_viz_sig"]("  ## 핵심 \n") == ns["_viz_sig"]("## 핵심"))

pb = pn = None
try:
    pb, sb = boot("app_base", PB)
    pn, sn = boot("app_new", PN)
    IB, IN = sb["ids"], sn["ids"]
    print("\n운영 그대로 %d · 새것 %d · 회의 %s" % (PB, PN, IN))
    chk("새 칸 4개가 기동 때 생겼다(운영엔 없음)", sn["has_viz_cols"] is True and sb["has_viz_cols"] is False)
    with sync_playwright() as p:
        br = p.chromium.launch()
        gb, eb, DB_ = page_for(br, PB, sb["me"])
        gn, en, DN = page_for(br, PN, sn["me"])

        print("\n── ④ 켜짐·꺼짐 = 📄 양식과 같다 ──")
        for k, why in (("V2", "정리 없음"), ("V3", "받아쓴 글 헛말")):
            s_, d_ = post(gn, PN, "/api/meeting/%d/viz" % IN[k])
            chk("%s(%s) 만들기 → 200 · no_minutes · 안내" % (k, why), s_ == 200 and d_.get("ok") is False and d_.get("no_minutes") is True
                and "아직 회의록 정리가 없습니다" in (d_.get("error") or ""), (s_, d_))
            st_, h_, _ = get(gn, PN, "/meetings/%d/viz" % IN[k])
            chk("%s 화면: 「아직 회의록이 작성되지 않았습니다」 · 그림 없음" % k, st_ == 200 and "아직 회의록이 작성되지 않았습니다" in h_ and 'id="viz" hidden' in h_)
        gn.goto(U(PN, "/meetings/%d" % IN["V2"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#btnVizView", state="attached", timeout=20000)
        chk("V2 상세: 📄 양식은 켜짐(받아쓴 글 있음) · 「📊 한눈에 보기」는 흐림(정리 없음) · 안내 글",
            "mf-doc-off" not in (gn.get_attribute("#btnDocView", "class") or "") and "mf-doc-off" in (gn.get_attribute("#btnVizView", "class") or "")
            and gn.get_attribute("#btnVizView", "aria-disabled") == "true" and gn.get_attribute("#btnVizView", "title") == "아직 회의록 정리가 없습니다 — 정리가 끝나면 열립니다",
            (gn.get_attribute("#btnDocView", "class"), gn.get_attribute("#btnVizView", "class"), gn.get_attribute("#btnVizView", "title")))
        n_al = len(DN["msgs"])
        gn.click("#btnVizView", force=True)
        chk("흐린 📊 를 누르면 안내 대화(새 창 안 열림)", len(DN["msgs"]) == n_al + 1 and "아직 회의록 정리가 없습니다" in DN["msgs"][-1], DN["msgs"][-1:])

        print("\n── ⑤ V1 만들기 ──")
        s5, d5 = post(gn, PN, "/api/meeting/%d/viz" % IN["V1"])
        chk("시작만 알린다(started)", s5 == 200 and d5.get("started") is True, (s5, d5))
        s5b, d5b = post(gn, PN, "/api/meeting/%d/viz" % IN["V1"])
        chk("도는 중 다시 누르면 already", d5b.get("already") is True or d5b.get("started") is True, d5b)
        done = wait_until(lambda: (json.loads(gn.request.get(U(PN, "/api/meeting/%d/viz-status" % IN["V1"])).text()) or {}).get("state") == "done", 30)
        stj = json.loads(gn.request.get(U(PN, "/api/meeting/%d/viz-status" % IN["V1"])).text())
        chk("상태 done · viz 가 실려 온다", bool(done) and isinstance(stj.get("viz"), dict) and stj["viz"].get("kind") == "equip", stj.get("state"))
        row = db("app_new", "SELECT viz_json, viz_at, viz_kind, viz_sum_sig, summary FROM meetings WHERE id=?", (IN["V1"],))[0]
        vz = json.loads(row["viz_json"])
        chk("DB: viz_json 저장 · kind equip · 만든 시각 · 지문 = 지금 정리 지문", vz.get("kind") == "equip" and row["viz_kind"] == "equip" and row["viz_at"][:4] == "2026"
            and row["viz_sum_sig"] == ns["_viz_sig"](row["summary"]), row["viz_sum_sig"])
        chk("다듬어짐: 정한 것 12 · 엉뚱한 type → step · 기한 「25일」 지움 · 근거 src 표시",
            len(vz["decided"]) == 12 and vz["flow"]["zones"][1]["steps"][2]["type"] == "step" and vz["todo"][1]["due"] == ""
            and vz["numbers"][0]["src"] == "body" and vz["open"][1]["src"] == "summary" and vz["todo"][2]["src"] == "", vz["todo"])
        lg = io.open(os.path.join(APPDIR, "srv_%d.log" % PN), encoding="utf-8").read()
        vl = [ln for ln in lg.splitlines() if "[VIZ]" in ln]
        chk("기록 「[VIZ] 회의 N: equip · 숫자 3 · 구역 3 · …」 숫자만 · 회의 글 없음",
            vl and ("equip · 숫자 3 · 구역 3 · 정한 것 12 · 확인 필요 2 · 할 일 3 · 일정 3 · 부품 1" in vl[-1]) and "출하" not in vl[-1] and "11월" not in vl[-1], vl[-1:] )
        chk("그림 AI 호출은 1번 · 정리 AI 는 안 돌았다(정리 글 그대로)", sum(1 for c in json.loads(gn.request.get(U(PN, "/__test/chat")).text())["calls"] if "그림 자료" in c["system"]) == 1
            and row["summary"] == sn["sum"])
        cl = [c for c in json.loads(gn.request.get(U(PN, "/__test/chat")).text())["calls"] if "그림 자료" in c["system"]][0]
        chk("그림 AI 에 간 글 = [이번 회의 정보]·[정리(안건)]·[결정사항]·[할 일]·[원문] 차례", all(k in cl["user"] for k in ("[이번 회의 정보]", "[정리(안건)]", "[결정사항]", "[할 일]", "[원문]"))
            and cl["user"].index("[정리(안건)]") < cl["user"].index("[원문]") and sn["talk"] in cl["user"] and sn["sum"] in cl["user"])

        print("\n── ⑥ V1 화면 ──")
        gn.goto(U(PN, "/meetings/%d/viz" % IN["V1"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#viz .zone", timeout=20000)
        chk("종류 표시 「🏭 설비 회의」 · 머리줄 「14:00 ~ 14:50 (50분)」", gn.inner_text("#kindTag") == "🏭 설비 회의" and "14:00 ~ 14:50 (50분)" in gn.inner_text("#subLine"), gn.inner_text("#subLine"))
        cnt = gn.evaluate("() => ({num: document.querySelectorAll('.num').length, zone: document.querySelectorAll('.zone').length, inspz: document.querySelectorAll('.zone.insp').length,"
                          " step: document.querySelectorAll('.step').length, stepw: document.querySelectorAll('.step.t-step').length, insps: document.querySelectorAll('.step.t-insp').length, judges: document.querySelectorAll('.step.t-judge').length, dec: document.querySelectorAll('.col.dec li').length,"
                          " dech: document.querySelectorAll('.col.dec li.morehide').length, more: document.querySelectorAll('.col.dec [data-more]').length, opn: document.querySelectorAll('.col.opn li').length,"
                          " act: document.querySelectorAll('.col.act li').length, tl: document.querySelectorAll('.tl li').length, tlq: document.querySelectorAll('.tl li.q').length,"
                          " parts: document.querySelectorAll('tr.pr').length, loop: (document.querySelector('.loop')||{}).textContent || '', warn: document.querySelectorAll('.step .w').length,"
                          " due: (document.querySelector('.col.act .due')||{}).textContent || ''})")
        chk("숫자 3 · 구역 3(검사 구역 색 1) · 단계 6(step 꼴 2 · 검사 1 · 판정 1) · 경고 1", cnt["num"] == 3 and cnt["zone"] == 3 and cnt["inspz"] == 1 and cnt["step"] == 6 and cnt["stepw"] == 2 and cnt["insps"] == 1 and cnt["judges"] == 1 and cnt["warn"] == 1, cnt)
        chk("정한 것 12(8은 접힘 · 「+8 더 보기」) · 확인 필요 2 · 할 일 3(기한 10-24)", cnt["dec"] == 12 and cnt["dech"] == 8 and cnt["more"] == 1 and cnt["opn"] == 2 and cnt["act"] == 3 and cnt["due"] == "10-24", cnt)
        chk("일정 3(확인 표시 1) · 부품 1 · 되돌아가는 흐름 글", cnt["tl"] == 3 and cnt["tlq"] == 1 and cnt["parts"] == 1 and "빈 트레이 회수" in cnt["loop"] and "출하 → 투입" in cnt["loop"], cnt)
        gn.click(".col.dec [data-more]")
        chk("더 보기 → 12개 다 펼침", gn.evaluate("() => document.querySelectorAll('.col.dec li.morehide').length") == 0)
        gn.click(".num")
        gn.wait_for_selector("#sheet", state="visible", timeout=5000)
        chk("근거 창(원문): 구절이 노랗게 · 앞뒤 글", gn.inner_text("#shT") == "근거 (원문)" and gn.evaluate("() => document.querySelector('#shQ mark').textContent") == "출하는 11월 20일로 하고"
            and "포장은" in gn.inner_text("#shQ"), gn.inner_text("#shQ")[:120])
        gn.click(".col.opn li:nth-child(2)")
        chk("근거 창(정리 글): 정리에만 있는 구절", gn.inner_text("#shT") == "근거 (정리 글)" and "셋업 시작일" in gn.inner_text("#shQ"), gn.inner_text("#shQ")[:120])
        gn.click(".col.act li:nth-child(3)")
        chk("근거 못 찾음 안내", "찾지 못했습니다" in gn.inner_text("#shQ"), gn.inner_text("#shQ")[:120])
        gn.click("#shX")
        gn.screenshot(path=os.path.join(SHOTS, "q93_viz_V1_pc.png"), full_page=True)
        gm, em, DM = page_for(br, PN, sn["me"], w=390, h=844, mobile=True)
        gm.goto(U(PN, "/meetings/%d/viz" % IN["V1"]), wait_until="domcontentloaded")
        gm.wait_for_selector("#viz .zone", timeout=20000)
        wide = gm.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1")
        chk("휴대폰 세로(390): 가로로 넘치지 않음", wide is False)
        gm.screenshot(path=os.path.join(SHOTS, "q93_viz_V1_phone.png"), full_page=True)

        print("\n── ⑦ 정리가 바뀐 그림(V4) ──")
        gn.goto(U(PN, "/meetings/%d/viz" % IN["V4"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#viz .core", timeout=20000)
        chk("「다시 그리기」 안내 · 옛 그림은 그려진다", gn.locator(".notice").count() == 1 and "그 뒤 글 정리가 바뀌었습니다" in gn.inner_text(".notice")
            and gn.inner_text("#btnBuild").strip() == "🔄 다시 그리기" and "옛 그림" in gn.inner_text("#viz .core"), gn.inner_text("#viz .core"))
        n7 = len(DN["msgs"])
        gn.click("#btnBuild")
        got7 = wait_until(lambda: "출하 일정과 셋업 순서" in (gn.inner_text("#viz") if gn.locator("#viz .core").count() else ""), 30)
        chk("다시 그리면 새 그림 · 확인 대화 1번 · 안내 사라짐", bool(got7) and len(DN["msgs"]) == n7 + 1 and "다시 만듭니다" in DN["msgs"][-1] and gn.locator(".notice").count() == 0, DN["msgs"][-2:])
        r7 = db("app_new", "SELECT viz_sum_sig, summary FROM meetings WHERE id=?", (IN["V4"],))[0]
        chk("DB 지문 새로", r7["viz_sum_sig"] == ns["_viz_sig"](r7["summary"]))

        print("\n── ⑧ 권한 ──")
        go, eo, DO = page_for(br, PN, sn["other"])
        st8, _, hd8 = get(go, PN, "/meetings/%d/viz" % IN["V5"])
        chk("V5 남의 대외비: 화면 303 → /meetings", st8 == 303 and (hd8.get("location") or "").endswith("/meetings"), (st8, hd8.get("location")))
        chk("V5 상태 403 · 만들기 403", get(go, PN, "/api/meeting/%d/viz-status" % IN["V5"])[0] == 403 and post(go, PN, "/api/meeting/%d/viz" % IN["V5"])[0] == 403)
        st6, h6, _ = get(go, PN, "/meetings/%d/viz" % IN["V6"])
        chk("V6 공개 회의 보는 사람: 화면 200 · 만들기 단추 없음 · 「작성자·참석자가 … 누르면」", st6 == 200 and 'id="btnBuild"' not in h6 and "작성자·참석자가" in h6)
        chk("V6 보는 사람 만들기 403 · 상태 200", post(go, PN, "/api/meeting/%d/viz" % IN["V6"])[0] == 403 and get(go, PN, "/api/meeting/%d/viz-status" % IN["V6"])[0] == 200)
        g0, _e0, _d0 = page_for(br, PN, 0)   # tuser=0 = 없는 사람 = 로그인 안 됨
        st0 = g0.request.get(U(PN, "/meetings/%d/viz" % IN["V1"]), max_redirects=0)
        chk("로그인 없이 → 로그인으로(303 · /login)", st0.status in (302, 303, 307) and "/login" in (st0.headers.get("location") or ""), (st0.status, st0.headers.get("location")))

        print("\n── ⑨ AI 오류(V7) ──")
        post(gn, PN, "/api/meeting/%d/viz" % IN["V7"])
        er = wait_until(lambda: (json.loads(gn.request.get(U(PN, "/api/meeting/%d/viz-status" % IN["V7"])).text()) or {}).get("state") == "error", 30)
        stj7 = json.loads(gn.request.get(U(PN, "/api/meeting/%d/viz-status" % IN["V7"])).text())
        chk("상태 error · 오류 글 그대로 · viz_json 비어 있음", bool(er) and "시험용 실패" in stj7.get("error", "")
            and db("app_new", "SELECT viz_json FROM meetings WHERE id=?", (IN["V7"],))[0]["viz_json"] == "", stj7)

        print("\n── ⑩ 상세·양식 단추 · 🔴 반대 ──")
        gn.goto(U(PN, "/meetings/%d" % IN["V1"]), wait_until="domcontentloaded")
        gn.wait_for_selector("#btnVizView", state="attached", timeout=20000)
        chk("V1 상세: 「📊 한눈에 보기」 켜짐 · 주소 /viz · 글", "mf-doc-off" not in (gn.get_attribute("#btnVizView", "class") or "")
            and gn.get_attribute("#btnVizView", "href") == "/meetings/%d/viz" % IN["V1"] and gn.inner_text("#btnVizView").strip() == "📊 한눈에 보기")
        gv, ev, DV = page_for(br, PN, sn["vnu"])
        gv.goto(U(PN, "/meetings/%d" % IN["V6"]), wait_until="domcontentloaded")
        gv.wait_for_selector("#btnVizView", state="attached", timeout=20000)
        chk("베트남어 직원 상세: 「📊 Xem tổng quan」", gv.inner_text("#btnVizView").strip() == "📊 Xem tổng quan", gv.inner_text("#btnVizView"))
        std, hd, _ = get(gn, PN, "/meetings/%d/doc" % IN["V1"])
        chk("양식 toolbar 「📊 한눈에 보기」 → /viz", std == 200 and ('href="/meetings/%d/viz">📊 한눈에 보기' % IN["V1"]) in hd)
        stb, hb, _ = get(gb, PB, "/meetings/%d/viz" % IB["V1"])
        chk("🔴 반대: 운영은 /viz 가 404", stb == 404, stb)
        gb.goto(U(PB, "/meetings/%d" % IB["V1"]), wait_until="domcontentloaded")
        gb.wait_for_selector("#btnDocView", state="attached", timeout=20000)
        chk("🔴 반대: 운영 상세엔 📊 단추 없음 · 양식에도 없음", gb.locator("#btnVizView").count() == 0 and "📊 한눈에 보기" not in get(gb, PB, "/meetings/%d/doc" % IB["V1"])[1])

        print("\n── ⑪ 정리 흐름 무접촉(V8) ──")
        X = {}
        for nm, pg_, port, ids, app in (("n", gn, PN, IN, "app_new"), ("b", gb, PB, IB, "app_base")):
            n0 = len(json.loads(pg_.request.get(U(port, "/__test/chat")).text())["calls"])
            post(pg_, port, "/api/meeting/%d/extract" % ids["V8"])
            wait_until(lambda: (db(app, "SELECT summary FROM meetings WHERE id=?", (ids["V8"],))[0]["summary"] or "").strip(), 30)
            X[nm] = json.loads(pg_.request.get(U(port, "/__test/chat")).text())["calls"][n0:]
        chk("정리 AI 가 받는 지시문·원문·답 길이 = 운영과 글자 그대로", len(X["n"]) == 1 and X["n"] == X["b"], (X["n"][:1], X["b"][:1]))

        print("\n── ⑫ 콘솔 ──")
        chk("새것 화면 콘솔 오류 0", not [e for e in en + em + eo + ev if KNOWN not in e], [e for e in en + em + eo + ev if KNOWN not in e][:3])
        chk("운영 화면 콘솔 오류 0", not [e for e in eb if KNOWN not in e], eb[:3])
        br.close()
finally:
    kill(pb, pn)

print("\n사진: %s" % SHOTS)
print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
