# -*- coding: utf-8 -*-
"""z1196 검사기 — 🗣 통역 대조(음성 메모 · 회의록 · 대표·임원만).
대표 2026-10-27 「통역이 제대로 통역을 했을까?」 → 엑셀 → 화면 시안 → 「음성 메모 + 회의록 둘 다 · 대표·임원만 · 사람이 단추 눌러야 · 이대로 만들어 회귀 통과하면 올리기」

재는 것 (앱 두 벌 = 운영 그대로(app_base) · 새것(app_new) · 진짜 서버 · 진짜 브라우저 · 대조 계산은 두 자리(화자 구분 받아쓰기 · 빅터AI 대조)만 가짜)
  ━ 서버 안 띄움 ━
  ① 그 밖의 파일 글자 그대로(정리 지시문 ai_client 포함) · 바뀐 파일 넷 + 새 파일 셋뿐 · ② 바뀐 자리(main.py 뺀 줄 = 녹음 응답 두 줄뿐 · 전역 datetime 안 더함 · 화면·i18n 은 더하기만)
  ③ 마이그레이션 두 번(14 → 0 · 표 없으면 0) · ④ 계산 모듈 단위(발화 묶기 · 통역 짐작 · 항목 번호·분류 · 지시문 글 · 10분 조각)
  ━ 진짜 서버 ━
  ⑤ 단추: 대표·임원에게만(메모 vnInterp · 회의록 btnInterpView) · 관리자·직원 없음 · 🔴 반대: 운영엔 없음
  ⑥ 화면 권한: 대표 200 · 직원·관리자 → 그 기록으로 · 비로그인 → 로그인 · 남의 메모 → 그 메모로 · 운영은 404
  ⑦ 만들기 끝까지(V1 30초): 시작만 알림 → 돌다 → 끝 · DB 대조표(항목 5 · ①~⑤ 1씩) · 받아쓴 글·정리 그대로 · 쓴 토큰 기록 · 기록 줄엔 숫자만 · 화면 카드 5 · ▶ 자리 이동(Range)
  ⑧ 다시 대조 → 이전 표 보관 · ↩ 이전 대조 맞바꾸기(두 번이면 제자리) · 이전 없으면 거절
  ⑨ 긴 녹음(V2 650초) = 2조각 · 둘째 조각에 「아는 화자」 넘김 · 4분 창 3개 → 항목 15
  ⑩ 실패하면 error + 까닭 · 표는 그대로 · ⑪ 서버가 다시 켜져 끊긴 것은 「끊김」으로 · 다시 만들 수 있음 · ⑫ 녹음 없으면 못 만듦(메모·회의록)
  ⑬ API 권한(직원·관리자 403 · 비로그인 401 · 남의 메모 403) · ⑭ 회의록판(M1 끝까지 · 양식·한눈에 보기 고리 · 임원 200 · 직원 → 회의록으로 · 남의 비공개 회의도 대표는 봄)
  ⑮ 녹음 Range: 206 조각 = 파일 조각 · 없으면 200+Accept-Ranges · 범위 밖 416 · 🔴 반대: 운영은 200 통째
  ⑯ AI 없으면 400 · ⑰ 휴대폰 390 가로 넘침 0 · 콘솔 오류 0 · 직원 메모 화면도 멀쩡(전역 판정 함수)
쓰는 법: py -3.12 q96_check.py <app_base·app_new 가 있는 폴더>   판정: 종료코드(0=통과) + 요약 줄.  🔒 시험 글은 모두 지어낸 것.
"""
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
import tempfile
import time
import urllib.error
import urllib.request
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1] if len(sys.argv) > 1 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
PB, PN = 8963, 8964
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
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
    pr = subprocess.Popen([P313, os.path.join(HERE, "run_q96_app.py"), os.path.join(APPDIR, app), str(port)],
                          stdout=io.open(lp, "w", encoding="utf-8"), stderr=subprocess.STDOUT, cwd=APPDIR)
    for _ in range(900):
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


def srvlog(port):
    p = os.path.join(APPDIR, "srv_%d.log" % port)
    return io.open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else ""


U = lambda port, path: "http://127.0.0.1:%d%s" % (port, path)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def http(port, path, uid=None, method="GET", body=None, headers=None):
    """(상태, 헤더 dict, 바디 bytes) — 되돌림(3xx)은 따라가지 않는다."""
    h = dict(headers or {})
    if uid is not None:
        h["Cookie"] = "tuser=%s" % uid
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(U(port, path), data=data, method=method, headers=h)
    try:
        with _opener.open(req, timeout=30) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()


def js(port, path, uid=None, method="GET", body=None):
    st, _h, b = http(port, path, uid, method, body)
    try:
        return st, json.loads(b.decode("utf-8"))
    except Exception:
        return st, {"_raw": b[:200].decode("utf-8", "replace")}


def db(app, sql, args=()):
    p = os.path.join(APPDIR, app, "data", "knk.db").replace("\\", "/")
    c = sqlite3.connect("file:%s?mode=ro" % p, uri=True, timeout=10)
    c.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in c.execute(sql, args)]
    finally:
        c.close()


def md5(app, rel):
    return hashlib.md5(io.open(os.path.join(APPDIR, app, "app", rel), "rb").read()).hexdigest()


def rd(app, rel):
    return io.open(os.path.join(APPDIR, app, "app", rel), encoding="utf-8").read()


def diff(a, b):
    return [d for d in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0)
            if d[:1] in "+-" and not d.startswith(("+++", "---"))]


def wait_until(fn, timeout=60.0, step=0.4):
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


def walk(app):
    out = {}
    root = os.path.join(APPDIR, app, "app")
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in ("__pycache__",)]
        for f in files:
            if f.endswith((".pyc", ".bak_z1196")):
                continue
            p = os.path.join(d, f)
            out[os.path.relpath(p, root).replace("\\", "/")] = hashlib.md5(io.open(p, "rb").read()).hexdigest()
    return out


# ═══════════════════════ 서버 안 띄움 ═══════════════════════
print("── ① 그 밖의 파일 글자 그대로 · 바뀐 파일 넷 + 새 파일 셋뿐 ──")
for rel in ("ai_client.py", "database.py", "templates/meeting_viz.html", "templates/meeting_doc.html", "templates/voice_notes.html",
            "templates/meetings.html", "templates/_v5_partials/knk_md_lite.html", "templates/_v5_partials/styles.html",
            "migrations/m_z1193_meeting_viz.py", "migrations/m_z1194_voice_note_meta.py", "migrations/m_z1195_voice_note_when_auto.py"):
    chk("그대로: %s" % rel, md5("app_base", rel) == md5("app_new", rel))
WB, WN = walk("app_base"), walk("app_new")
changed = sorted(k for k in WB if k in WN and WB[k] != WN[k])
added = sorted(k for k in WN if k not in WB)
removed = sorted(k for k in WB if k not in WN)
chk("바뀐 파일 = main.py · i18n.py · 메모 화면 · 회의록 화면", changed == ["i18n.py", "main.py", "templates/meeting_form.html", "templates/voice_note_form.html"], changed)
chk("새 파일 = interp_check.py · 화면 · 마이그레이션", added == ["interp_check.py", "migrations/m_z1196_interp_check.py", "templates/interp_check.html"], added)
chk("없어진 파일 0", removed == [], removed)

print("── ② 바뀐 자리 ──")
dm = diff(rd("app_base", "main.py"), rd("app_new", "main.py"))
rem = [x[1:] for x in dm if x.startswith("-")]
add = [x[1:] for x in dm if x.startswith("+")]
AUD = '    return FileResponse(disk, media_type=_MEETING_AUDIO_MIME.get(ext, "application/octet-stream"))'
chk("main.py 뺀 줄 = 녹음 응답 두 줄뿐", rem == [AUD, AUD], rem[:4])
chk("main.py 더한 줄에 판정 함수·전역·Range·마이그레이션·경로 8개",
    sum(1 for x in add if "def _interp_can_use" in x) == 1 and sum(1 for x in add if 'tpl.env.globals["interp_can_use"]' in x) == 1
    and sum(1 for x in add if "return _audio_file_response(req, disk" in x) == 2 and sum(1 for x in add if "m_z1196_interp_check import migrate" in x) == 1
    and sum(1 for x in add if x.startswith("@app.")) == 8, len(add))
chk("main.py 에 전역 datetime/timedelta 안 더함", not any(re.match(r"^(from datetime import|import datetime)", x) for x in add))
chk("main.py 기록 print 에 회의 글 변수 없음(숫자만)", all(("rec[" not in x and "data[\"turns\"]" not in x) for x in add if "print(" in x))
for rel, must in (("templates/voice_note_form.html", ['id="vnInterp"', "interp_can_use(user)"]),
                  ("templates/meeting_form.html", ['id="btnInterpView"', "i.mf_interp"]),
                  ("i18n.py", ['"mf_interp"', '"mf_interp_t"', '"vi": "🗣'])):
    d = diff(rd("app_base", rel), rd("app_new", rel))
    chk("%s: 더하기만 · 핵심 글 있음" % rel.split("/")[-1], not [x for x in d if x.startswith("-")] and all(any(m in x for x in d) for m in must),
        [x for x in d if x.startswith("-")][:3])

print("── ③ 마이그레이션 두 번 ──")
spec = importlib.util.spec_from_file_location("m96", os.path.join(APPDIR, "app_new", "app", "migrations", "m_z1196_interp_check.py"))
m96 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m96)
with tempfile.TemporaryDirectory() as td:
    p = os.path.join(td, "t.db")
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE voice_notes(id INTEGER PRIMARY KEY, title TEXT)")
    c.execute("CREATE TABLE meetings(id INTEGER PRIMARY KEY, title TEXT)")
    c.execute("INSERT INTO voice_notes(title) VALUES('x')")
    c.commit()
    c.close()
    r1 = m96.migrate(p)
    r2 = m96.migrate(p)
    c = sqlite3.connect(p)
    cols = {r[1] for r in c.execute("PRAGMA table_info(voice_notes)")}
    row0 = c.execute("SELECT interp_json, interp_state FROM voice_notes").fetchone()
    c.close()
    chk("새 칸 7 × 2 = 14 → 두 번째 0", len(r1["added"]) == 14 and r2["added"] == [], (r1, r2))
    chk("칸 이름 7 · 기존 줄은 빈 글", {"interp_json", "interp_at", "interp_prev", "interp_prev_at", "interp_state", "interp_error", "interp_usage"} <= cols and row0 == ("", ""))
    p2 = os.path.join(td, "e.db")
    sqlite3.connect(p2).close()
    chk("표 없는 DB 는 0", m96.migrate(p2)["added"] == [])

print("── ④ 계산 모듈 단위 ──")
sys.path.insert(0, os.path.join(APPDIR, "app_new"))
os.environ.setdefault("KNK_SECRET_KEY", "verify-only-key")
for _k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
    os.environ[_k] = ""
import app.interp_check as IC   # noqa: E402
chk("10분 조각 · 겹침 3초 · 창 4분 · 묶음 20/90", IC.CHUNK_SEC == 600 and IC.OVERLAP_SEC == 3 and IC.WIN == 240 and IC.GAP == 20 and IC.MAXLEN == 90)
chk("지시문 글 — 대조·묶음(실증판 핵심 문장)", "원말로 쓰지 말고" in IC.SYSTEM_CMP and "「분:초」" in IC.SYSTEM_CMP and "들었어야" in IC.SYSTEM_BLK and "옮겨지지 않은 말 묶음" in IC.SYSTEM_BLK)
chk("to_sec · mmss · lang_of", IC.to_sec("3:39") == 219 and IC.to_sec(12.5) == 12.5 and IC.to_sec("x", 7) == 7 and IC.mmss(596.4) == "9:56"
    and IC.lang_of("안녕") == "ko" and IC.lang_of("Câu trả lời") == "vi" and IC.lang_of("안녕 Câu") == "ko+vi")
segs = [{"start": 0, "end": 1, "speaker": "A", "text": "하나"}, {"start": 1.5, "end": 2, "speaker": "A", "text": "둘"}, {"start": 3.5, "end": 4, "speaker": "A", "text": "셋"},
        {"start": 4.2, "end": 6, "speaker": "D", "text": "Lời dịch"}, {"start": 6.1, "end": 7, "speaker": "D", "text": "한국어 옮김"}, {"start": 7.5, "end": 9, "speaker": "B", "text": "Câu trả lời"}]
turns = IC.build_turns(segs)
chk("발화 묶기: 같은 화자 1초 안은 합치고 넘으면 나눔(D 두 조각도 합쳐 4)", [t["text"] for t in turns][:2] == ["하나 둘", "셋"] and len(turns) == 4 and turns[2]["lang"] == "ko+vi", [t["text"] for t in turns])
by, interp = IC.roles(turns)
chk("통역 짐작 = 두 언어 다 쓰는 D · 역할 글", interp == "D" and by["D"]["역할"] == "통역(추정)" and by["B"]["역할"].startswith("베트남") and by["A"]["역할"].startswith("한국"))
rows = [{"_sec": 7.5, "_isec": None, "방향": "VI→KO", "판정": "뜻 바뀜", "심각도": 2, "원말_화자": "B", "원말": "x", "통역한_말": "y", "AI_독립번역": "z", "성격": "답변·설명", "까닭": "w"},
        {"_sec": 0.0, "_isec": None, "방향": "KO→VI", "판정": "같음", "심각도": 0, "원말_화자": "A", "원말": "x", "통역한_말": "y", "AI_독립번역": "z", "성격": "질문", "까닭": ""}]
blocks = [{"dir": "VI→KO", "start": 20.0, "end": 30.0, "rows": [rows[0], rows[0]], "화자": "B", "원말": "o", "번역": "p", "sev": 2, "요지": "g", "대상": "t", "들었어야": "예", "까닭": "r"}]
data = IC.assemble(turns, by, interp, rows, blocks, 40.0, 1, start_clock="09:00:00")
chk("항목 = 시간순 번호 · 분류 ①⑤② · 셈", [(i["id"], i["cat"]) for i in data["items"]] == [(1, 5), (2, 1), (3, 2)] and data["counts"] == {"1": [1, 1], "2": [1, 1], "3": [0, 0], "4": [0, 0], "5": [1, 0]}
    and data["start_clock"] == "09:00:00" and data["n_turns"] == 4 and data["speakers"][0]["id"] == interp, ([(i["id"], i["cat"]) for i in data["items"]], data["counts"], data["n_turns"]))
_ta = IC.ai_client.transcribe_available
IC.ai_client.transcribe_available = lambda: False
chk("available(): 받아쓰기 키 없으면 못 만듦", IC.available() is False)
IC.ai_client.transcribe_available = _ta

# ═══════════════════════ 진짜 서버 ═══════════════════════
print("── 서버 두 벌 띄우기(운영 그대로 %d · 새것 %d) ──" % (PB, PN))
prB, sB = boot("app_base", PB)
prN, sN = boot("app_new", PN)
ME, EXE, ADM, MEM = sN["me"], sN["exe"], sN["adm"], sN["mem"]
I = sN["ids"]
IB = sB["ids"]
chk("새것엔 새 칸 · 운영엔 없음", sN["has_cols"] and not sB["has_cols"])
LOG0 = len(srvlog(PN))
try:
    print("── ⑤ 단추는 대표·임원에게만 ──")
    OWN = {ME: I["V1"], EXE: I["V7"], ADM: I["V8"], MEM: I["V4"]}      # 메모는 제 것만 열린다 → 사람마다 제 메모로
    for uid, who, exp in ((ME, "대표", True), (EXE, "임원", True), (ADM, "관리자", False), (MEM, "직원", False)):
        st, _h, b = http(PN, "/voice-notes/%d" % OWN[uid], uid)
        chk("메모 화면 %s: 단추 %s" % (who, "있음" if exp else "없음"), st == 200 and (('id="vnInterp"' in b.decode("utf-8")) == exp), st)
        st, _h, b = http(PN, "/meetings/%d" % I["M1"], uid)
        chk("회의록 화면 %s: 단추 %s" % (who, "있음" if exp else "없음"), st == 200 and (('id="btnInterpView"' in b.decode("utf-8")) == exp), st)
    st, _h, b = http(PB, "/voice-notes/%d" % IB["V1"], sB["me"])
    chk("🔴 반대 — 운영 메모 화면엔 단추 없음", st == 200 and 'id="vnInterp"' not in b.decode("utf-8"))
    st, _h, b = http(PB, "/meetings/%d" % IB["M1"], sB["me"])
    chk("🔴 반대 — 운영 회의록 화면엔 단추 없음", st == 200 and 'id="btnInterpView"' not in b.decode("utf-8"))

    print("── ⑥ 화면 권한 ──")
    st, _h, b = http(PN, "/voice-notes/%d/interp" % I["V1"], ME)
    chk("대표: 메모 통역 대조 200 · 만들기 단추 · 예상치 칸", st == 200 and "🗣 통역 대조 만들기" in b.decode("utf-8") and 'id="est"' in b.decode("utf-8"), st)
    for uid, who in ((MEM, "직원"), (ADM, "관리자")):
        st, h, _b = http(PN, "/voice-notes/%d/interp" % I["V1"], uid)
        chk("%s: 메모 통역 대조 → 그 메모로(303)" % who, st == 303 and h.get("location", "").endswith("/voice-notes/%d" % I["V1"]), (st, h.get("location")))
    st, h, _b = http(PN, "/voice-notes/%d/interp" % I["V1"], 0)
    chk("비로그인 → 로그인으로", st == 303 and "/login" in h.get("location", ""), (st, h.get("location")))
    st, h, _b = http(PN, "/voice-notes/%d/interp" % I["V4"], ME)
    chk("대표라도 남의 메모 → 그 메모로(메모 규칙 = 주인만)", st == 303 and h.get("location", "").endswith("/voice-notes/%d" % I["V4"]), (st, h.get("location")))
    st, _h, b = http(PN, "/meetings/%d/interp" % I["M2"], ME)
    chk("대표: 직원의 비공개 회의록도 200(회의록 규칙 = 역할)", st == 200 and "🗣" in b.decode("utf-8"), st)
    st, h, _b = http(PN, "/meetings/%d/interp" % I["M1"], MEM)
    chk("직원: 회의록 통역 대조 → 회의록으로(303)", st == 303 and h.get("location", "").endswith("/meetings/%d" % I["M1"]), (st, h.get("location")))
    st, _h, _b = http(PB, "/voice-notes/%d/interp" % IB["V1"], sB["me"])
    st2, _h, _b = http(PB, "/meetings/%d/interp" % IB["M1"], sB["me"])
    chk("🔴 반대 — 운영엔 화면 없음(404 둘)", st == 404 and st2 == 404, (st, st2))

    print("── ⑦ 만들기 끝까지(V1) ──")
    js(PN, "/__test/reset", method="POST")
    r0 = db("app_new", "SELECT body, summary FROM voice_notes WHERE id=?", (I["V1"],))[0]
    st, j = js(PN, "/api/voice-note/%d/interp" % I["V1"], ME, "POST", {})
    chk("시작 = ok·started", st == 200 and j.get("ok") and j.get("started"), j)
    st, j2 = js(PN, "/api/voice-note/%d/interp" % I["V1"], ME, "POST", {})
    chk("또 누르면 already", j2.get("already") is True or j2.get("started") is True, j2)
    st, s1 = js(PN, "/api/voice-note/%d/interp-status" % I["V1"], ME)
    chk("상태 = running 또는 done(글 있음)", s1.get("state") in ("running", "done"), s1)
    done = wait_until(lambda: js(PN, "/api/voice-note/%d/interp-status" % I["V1"], ME)[1].get("state") == "done", 90)
    chk("끝남(done)", bool(done), js(PN, "/api/voice-note/%d/interp-status" % I["V1"], ME)[1])
    r = db("app_new", "SELECT * FROM voice_notes WHERE id=?", (I["V1"],))[0]
    d1 = json.loads(r["interp_json"] or "{}")
    chk("DB 대조표: 항목 5 · ①~⑤ 1씩(빨강 ①1 ②1) · 조각 1 · 통역 D", len(d1.get("items") or []) == 5 and d1.get("counts") == {"1": [1, 1], "2": [1, 1], "3": [1, 0], "4": [1, 0], "5": [1, 0]}
        and d1.get("chunks") == 1 and d1.get("interp") == "D", d1.get("counts"))
    chk("만든 시각 · state done · 이전 없음 · 시작 시각 15:06:00(자동 일시에서)", bool(r["interp_at"]) and r["interp_state"] == "done" and r["interp_prev"] == "" and d1.get("start_clock") == "15:06:00",
        (r["interp_at"], r["interp_state"], d1.get("start_clock")))
    chk("받아쓴 글·정리 그대로", r["body"] == r0["body"] and r["summary"] == r0["summary"])
    us = json.loads(r["interp_usage"] or "{}")
    chk("쓴 토큰 기록(받아쓰기 1 · 대조 2)", len(us.get("stt") or []) == 1 and len(us.get("cmp") or []) == 2, us)
    st, calls = js(PN, "/__test/calls")
    chk("가짜 부름: 받아쓰기 1(30초 · 아는 화자 없음) · 대조 1 + 묶음 1", len(calls["diar"]) == 1 and calls["diar"][0]["names"] == [] and 28 <= calls["diar"][0]["sec"] <= 31
        and [c["kind"] for c in calls["chat"]] == ["cmp", "blk"], calls)
    lg = srvlog(PN)[LOG0:]
    chk("기록 줄: 시작·조각·저장(숫자만) · 지어낸 글 안 찍힘", ("[INTERP-Z1196] vn %d: 시작" % I["V1"]) in lg and ("[INTERP-Z1196] vn %d: 저장 · 항목 5" % I["V1"]) in lg
        and "받아쓰기 조각 1/1" in lg and "지어낸 한국어 말" not in lg and "Câu trả lời" not in lg)
    chk("임시 폴더 지움", not os.path.exists(os.path.join(APPDIR, "app_new", "data", "interp_tmp")) or os.listdir(os.path.join(APPDIR, "app_new", "data", "interp_tmp")) == [])

    print("── ⑧ 다시 대조 → 이전 표 · ↩ 맞바꾸기 ──")
    js(PN, "/__test/flag/variant/2", method="POST")
    old_json, old_at = r["interp_json"], r["interp_at"]
    time.sleep(1.1)
    st, j = js(PN, "/api/voice-note/%d/interp" % I["V1"], ME, "POST", {})
    done = wait_until(lambda: js(PN, "/api/voice-note/%d/interp-status" % I["V1"], ME)[1].get("state") == "done" and
                      db("app_new", "SELECT interp_prev FROM voice_notes WHERE id=?", (I["V1"],))[0]["interp_prev"] != "", 90)
    r = db("app_new", "SELECT * FROM voice_notes WHERE id=?", (I["V1"],))[0]
    chk("다시 대조: 이전 표 = 첫 표 · 새 표는 다름", bool(done) and r["interp_prev"] == old_json and r["interp_prev_at"] == old_at and r["interp_json"] != old_json, (r["interp_prev_at"], old_at))
    new_json, new_at = r["interp_json"], r["interp_at"]
    st, _h, b = http(PN, "/voice-notes/%d/interp" % I["V1"], ME)
    chk("화면에 「↩ 이전 대조」 단추", 'id="btnPrev"' in b.decode("utf-8") and "🔄 다시 대조" in b.decode("utf-8"))
    st, j = js(PN, "/api/voice-note/%d/interp-restore" % I["V1"], ME, "POST", {})
    r = db("app_new", "SELECT * FROM voice_notes WHERE id=?", (I["V1"],))[0]
    chk("↩ 맞바꾸기: 지금 = 첫 표 · 이전 = 새 표", j.get("ok") and r["interp_json"] == old_json and r["interp_at"] == old_at and r["interp_prev"] == new_json and r["interp_prev_at"] == new_at, j)
    js(PN, "/api/voice-note/%d/interp-restore" % I["V1"], ME, "POST", {})
    r = db("app_new", "SELECT * FROM voice_notes WHERE id=?", (I["V1"],))[0]
    chk("두 번이면 제자리", r["interp_json"] == new_json and r["interp_prev"] == old_json)
    st, j = js(PN, "/api/voice-note/%d/interp-restore" % I["V2"], ME, "POST", {})
    chk("이전 없으면 거절", j.get("ok") is False and "이전 대조표가 없습니다" in j.get("error", ""), j)
    js(PN, "/__test/flag/variant/1", method="POST")

    print("── ⑨ 긴 녹음(V2 650초) = 2조각 ──")
    js(PN, "/__test/reset", method="POST")
    st, j = js(PN, "/api/voice-note/%d/interp" % I["V2"], ME, "POST", {})
    done = wait_until(lambda: js(PN, "/api/voice-note/%d/interp-status" % I["V2"], ME)[1].get("state") == "done", 150)
    r = db("app_new", "SELECT * FROM voice_notes WHERE id=?", (I["V2"],))[0]
    d2 = json.loads(r["interp_json"] or "{}")
    st, calls = js(PN, "/__test/calls")
    chk("받아쓰기 2번 · 둘째에 아는 화자(A) 넘김", bool(done) and len(calls["diar"]) == 2 and calls["diar"][0]["names"] == [] and calls["diar"][1]["names"] == ["A"] and calls["diar"][1]["refs"] == 1, calls["diar"])
    chk("조각 2 · 창 3 → 항목 15 · ①3(빨강3) ②3(2) ③3(1) ④3 ⑤3", d2.get("chunks") == 2 and len(d2.get("items") or []) == 15
        and d2.get("counts") == {"1": [3, 3], "2": [3, 2], "3": [3, 1], "4": [3, 0], "5": [3, 0]} and [c["kind"] for c in calls["chat"]] == ["cmp", "cmp", "cmp", "blk"],
        (d2.get("chunks"), d2.get("counts"), [c["kind"] for c in calls["chat"]]))
    chk("발화 100개 넘고 화자 3 · 길이 650", d2.get("n_turns", 0) > 100 and len(d2.get("speakers") or []) == 3 and 645 <= d2.get("dur", 0) <= 655, (d2.get("n_turns"), d2.get("dur")))

    print("── ⑩ 실패 · ⑪ 끊김 · ⑫ 녹음 없음 ──")
    js(PN, "/__test/flag/fail_diar/1", method="POST")
    before = db("app_new", "SELECT interp_json FROM voice_notes WHERE id=?", (I["V5"],))[0]["interp_json"]
    st, j = js(PN, "/api/voice-note/%d/interp" % I["V5"], ME, "POST", {})
    err = wait_until(lambda: (lambda s: s if s.get("state") == "error" else None)(js(PN, "/api/voice-note/%d/interp-status" % I["V5"], ME)[1]), 60)
    r = db("app_new", "SELECT * FROM voice_notes WHERE id=?", (I["V5"],))[0]
    chk("실패: state error + 까닭(종류+글) · DB 도 error · 표는 그대로", bool(err) and "RuntimeError" in err.get("error", "") and r["interp_state"] == "error" and r["interp_error"] and r["interp_json"] == before, err)
    st, _h, b = http(PN, "/voice-notes/%d/interp" % I["V5"], ME)
    chk("화면에 ⚠ 만들지 못했습니다 + 표는 그대로 보임", 'id="jobErr"' in b.decode("utf-8") and "🔄 다시 대조" in b.decode("utf-8"))
    chk("기록 [INTERP-Z1196 ERR]", ("[INTERP-Z1196 ERR] vn %d" % I["V5"]) in srvlog(PN))
    js(PN, "/__test/flag/fail_diar/0", method="POST")
    st, s6 = js(PN, "/api/voice-note/%d/interp-status" % I["V6"], ME)
    chk("끊김(DB running · 작업 없음) = error 「끊겼습니다」", s6.get("state") == "error" and "끊겼습니다" in s6.get("error", ""), s6)
    st, _h, b = http(PN, "/voice-notes/%d/interp" % I["V6"], ME)
    chk("끊김 화면: ⚠ 안내 + 만들기 단추 살아 있음", "끊겼습니다" in b.decode("utf-8") and "🗣 통역 대조 만들기" in b.decode("utf-8") and "disabled" not in b.decode("utf-8").split('id="btnBuild"')[0][-60:])
    st, j = js(PN, "/api/voice-note/%d/interp" % I["V6"], ME, "POST", {})
    done = wait_until(lambda: js(PN, "/api/voice-note/%d/interp-status" % I["V6"], ME)[1].get("state") == "done", 60)
    chk("끊긴 것도 다시 만들면 done", j.get("started") and bool(done), j)
    st, j = js(PN, "/api/voice-note/%d/interp" % I["V3"], ME, "POST", {})
    st2, _h, b = http(PN, "/voice-notes/%d/interp" % I["V3"], ME)
    chk("녹음 없는 메모: 못 만듦(no_audio) · 화면 안내", j.get("ok") is False and j.get("no_audio") and "녹음이 없어" in b.decode("utf-8"), j)
    st, j = js(PN, "/api/meeting/%d/interp" % I["M3"], ME, "POST", {})
    chk("녹음 없는 회의록도 못 만듦", j.get("ok") is False and j.get("no_audio"), j)

    print("── ⑬ API 권한 ──")
    st, j = js(PN, "/api/voice-note/%d/interp" % I["V4"], MEM, "POST", {})
    chk("직원(제 메모) 만들기 403 · 대표·임원만", st == 403 and "대표·임원" in j.get("error", ""), (st, j))
    st, j = js(PN, "/api/voice-note/%d/interp" % I["V1"], ADM, "POST", {})
    chk("관리자 403", st == 403, (st, j))
    st, j = js(PN, "/api/voice-note/%d/interp" % I["V1"], 0, "POST", {})
    chk("비로그인 401", st == 401, (st, j))
    st, j = js(PN, "/api/voice-note/%d/interp-status" % I["V1"], MEM)
    st2, j2 = js(PN, "/api/voice-note/%d/interp-restore" % I["V1"], MEM, "POST", {})
    chk("직원 상태·되돌리기 403", st == 403 and st2 == 403, (st, st2))
    st, j = js(PN, "/api/voice-note/%d/interp" % I["V4"], ME, "POST", {})
    chk("대표라도 남의 메모 403(내 메모만)", st == 403 and "내 메모" in j.get("error", ""), (st, j))

    print("── ⑭ 회의록판(M1) ──")
    js(PN, "/__test/reset", method="POST")
    st, j = js(PN, "/api/meeting/%d/interp" % I["M1"], ME, "POST", {})
    done = wait_until(lambda: js(PN, "/api/meeting/%d/interp-status" % I["M1"], ME)[1].get("state") == "done", 90)
    rm = db("app_new", "SELECT * FROM meetings WHERE id=?", (I["M1"],))[0]
    dm1 = json.loads(rm["interp_json"] or "{}")
    chk("회의록 만들기 끝 · 항목 5 · 시작 시각 09:00:00(msg_started_at)", bool(done) and len(dm1.get("items") or []) == 5 and dm1.get("start_clock") == "09:00:00" and rm["interp_state"] == "done", dm1.get("start_clock"))
    st, _h, b = http(PN, "/meetings/%d/interp" % I["M1"], ME)
    h = b.decode("utf-8")
    chk("회의록판 화면: 양식·한눈에 보기 고리 · 회의록으로", ("/meetings/%d/doc" % I["M1"]) in h and ("/meetings/%d/viz" % I["M1"]) in h and "회의록으로" in h)
    st, _h, _b = http(PN, "/meetings/%d/interp" % I["M1"], EXE)
    chk("임원 200", st == 200, st)
    chk("기록: mtg 저장 줄", ("[INTERP-Z1196] mtg %d: 저장 · 항목 5" % I["M1"]) in srvlog(PN))

    print("── ⑮ 녹음 Range ──")
    for kind, path, rel in (("메모", "/api/voice-note/%d/audio" % I["V1"], db("app_new", "SELECT audio_path FROM voice_notes WHERE id=?", (I["V1"],))[0]["audio_path"]),
                            ("회의록", "/api/meeting/%d/audio" % I["M1"], db("app_new", "SELECT audio_path FROM meetings WHERE id=?", (I["M1"],))[0]["audio_path"])):
        raw = io.open(rel, "rb").read()
        st, h, b = http(PN, path, ME)
        chk("%s 녹음 Range 없음 → 200 전체 + Accept-Ranges" % kind, st == 200 and len(b) == len(raw) and h.get("accept-ranges") == "bytes", (st, len(b), len(raw), h.get("accept-ranges")))
        st, h, b = http(PN, path, ME, headers={"Range": "bytes=100-199"})
        chk("%s Range 100-199 → 206 · 조각 = 파일 조각" % kind, st == 206 and b == raw[100:200] and h.get("content-range") == "bytes 100-199/%d" % len(raw) and h.get("content-length") == "100", (st, h.get("content-range")))
        st, h, b = http(PN, path, ME, headers={"Range": "bytes=%d-" % (len(raw) - 50)})
        chk("%s Range 끝 50 → 206" % kind, st == 206 and b == raw[-50:], (st, len(b)))
        st, h, b = http(PN, path, ME, headers={"Range": "bytes=-30"})
        chk("%s Range 뒤에서 30 → 206" % kind, st == 206 and b == raw[-30:], st)
        st, h, b = http(PN, path, ME, headers={"Range": "bytes=%d-%d" % (len(raw) + 10, len(raw) + 20)})
        chk("%s 범위 밖 → 416" % kind, st == 416 and h.get("content-range") == "bytes */%d" % len(raw), (st, h.get("content-range")))
    st, h, b = http(PN, "/api/voice-note/%d/audio" % I["V1"], MEM, headers={"Range": "bytes=0-9"})
    chk("남의 메모 녹음은 Range 라도 403(권한 그대로)", st == 403, st)
    st, h, b = http(PN, "/api/meeting/%d/audio" % I["M2"], sN["mem2"], headers={"Range": "bytes=0-9"})
    chk("못 보는 비공개 회의 녹음은 Range 라도 거절(권한 그대로)", st in (401, 403, 404), st)
    st, h, b = http(PN, "/api/meeting/%d/audio" % I["M1"], MEM, headers={"Range": "bytes=0-9"})
    chk("볼 수 있는 회의(팀 공개) 녹음은 직원도 206(권한 그대로)", st == 206 and len(b) == 10, st)
    rawb = io.open(db("app_base", "SELECT audio_path FROM voice_notes WHERE id=?", (IB["V1"],))[0]["audio_path"], "rb").read()
    st, h, b = http(PB, "/api/voice-note/%d/audio" % IB["V1"], sB["me"], headers={"Range": "bytes=100-199"})
    chk("🔴 반대 — 운영은 Range 를 몰라 200 통째", st == 200 and len(b) == len(rawb), (st, len(b)))

    print("── ⑯ AI 없음 ──")
    js(PN, "/__test/flag/ai/0", method="POST")
    st, j = js(PN, "/api/voice-note/%d/interp" % I["V2"], ME, "POST", {})
    chk("AI(받아쓰기 키·ffmpeg) 없으면 400 + 까닭", st == 400 and "키" in j.get("error", ""), (st, j))
    js(PN, "/__test/flag/ai/1", method="POST")

    print("── ⑰ 진짜 브라우저(PC · 휴대폰) ──")
    CONSOLE = []
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        ctx = br.new_context(viewport={"width": 1366, "height": 900}, locale="ko-KR")
        ctx.add_cookies([{"name": "tuser", "value": str(ME), "url": U(PN, "")}])
        pg = ctx.new_page()
        pg.on("console", lambda m: CONSOLE.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: CONSOLE.append("pageerror: " + str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.goto(U(PN, "/voice-notes/%d/interp" % I["V1"]), wait_until="networkidle")
        pg.wait_for_selector("#list .it")
        pg.wait_for_timeout(500)
        nums = pg.evaluate("Array.from(document.querySelectorAll('#nums .num b')).map(function(b){ return b.firstChild.textContent; })")
        chk("화면: 카드 5 · 숫자 1·1·1·1·1 · 먼저 들어 볼 자리 2(①1 ②1) · 머리 ①②", pg.locator("#list .it").count() == 5 and nums == ["1", "1", "1", "1", "1"]
            and pg.locator("#top li[data-go]").count() == 2 and pg.locator("#top li.gh").count() == 2, nums)
        sub = pg.evaluate("document.getElementById('subLine').textContent")
        chk("머리줄: 일시 · 장소 · 녹음 0:30 · 화자 3 · 통역 D · 만든 때", "15:06" in sub and "지어낸 회의실" in sub and "0:30" in sub and "3명" in sub and "화자 D" in sub and "대조 만든 때" in sub, sub)
        try:
            pg.wait_for_function("document.getElementById('au').readyState >= 1", timeout=15000)
        except Exception:
            pass
        far = pg.evaluate("(function(){ var b = Array.from(document.querySelectorAll('#list .pl')).map(function(x){ return +x.getAttribute('data-seek'); }); return Math.max.apply(null, b); })()")
        pg.click("#list .pl[data-seek='%g']" % far)
        pg.wait_for_timeout(1200)
        cur = pg.evaluate("document.getElementById('au').currentTime")
        skend = pg.evaluate("(function(a){ return a.seekable.length ? a.seekable.end(0) : 0; })(document.getElementById('au'))")
        chk("▶ 뒤쪽 자리로 정말 이동(Range) · 옮길 수 있는 끝 ≈ 30초", abs(cur - far) < 2.5 and skend > 25, "플레이어 %.1f vs %.1f · 끝 %.0f" % (cur, far, skend))
        chk("「부터 듣는 중」 + 시각(15:06:xx)", "부터 듣는 중" in pg.evaluate("document.getElementById('now').textContent") and "15:06:" in pg.evaluate("document.getElementById('now').textContent"))
        pg.click("#nums .num[data-cat='2']")
        pg.wait_for_timeout(200)
        chk("② 필터 → 1줄", pg.evaluate("document.querySelectorAll('#list .it:not(.hid)').length") == 1)
        pg.screenshot(path=os.path.join(SHOTS, "q96_pc_memo.png"))
        #  다시 대조 — 확인 창 → 시작 → 돌다 → 끝나면 새로 열림(만든 때 바뀜)
        at0 = db("app_new", "SELECT interp_at FROM voice_notes WHERE id=?", (I["V1"],))[0]["interp_at"]
        js(PN, "/__test/flag/slow/3", method="POST")
        time.sleep(1.1)
        pg.click("#btnBuild")
        pg.wait_for_timeout(1500)
        chk("다시 대조: 돌고 있음 표시 + 단추 잠김", pg.evaluate("!document.getElementById('busy').hidden && document.getElementById('btnBuild').disabled"))
        ok_reload = wait_until(lambda: db("app_new", "SELECT interp_at FROM voice_notes WHERE id=?", (I["V1"],))[0]["interp_at"] != at0, 60)
        pg.wait_for_timeout(4500)
        chk("끝나면 화면 새로 열림(busy 숨김 · ↩ 이전 대조 있음)", bool(ok_reload) and pg.evaluate("document.getElementById('busy').hidden") and pg.locator("#btnPrev").count() == 1)
        js(PN, "/__test/flag/slow/0", method="POST")
        #  회의록판 머리줄
        pg.goto(U(PN, "/meetings/%d/interp" % I["M1"]), wait_until="networkidle")
        pg.wait_for_selector("#list .it")
        sub2 = pg.evaluate("document.getElementById('subLine').textContent")
        chk("회의록 머리줄 = 2026-10-27 (화) · 장소 · 시각 09:00", sub2.startswith("2026-10-27 (화)") and "지어낸 회의실" in sub2, sub2)
        pg.screenshot(path=os.path.join(SHOTS, "q96_pc_meeting.png"))
        #  직원 메모 화면도 멀쩡(전역 판정 함수)
        ctx2 = br.new_context(viewport={"width": 1366, "height": 900})
        ctx2.add_cookies([{"name": "tuser", "value": str(MEM), "url": U(PN, "")}])
        p2 = ctx2.new_page()
        p2.on("pageerror", lambda e: CONSOLE.append("pageerror(직원): " + str(e)))
        p2.goto(U(PN, "/voice-notes/%d" % I["V4"]), wait_until="networkidle")
        chk("직원 메모 화면 멀쩡(제목 칸 있음 · 단추 없음)", p2.locator("#vnTitle").count() == 1 and p2.locator("#vnInterp").count() == 0)
        ctx2.close()
        m = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True, locale="ko-KR")
        m.add_cookies([{"name": "tuser", "value": str(ME), "url": U(PN, "")}])
        mp = m.new_page()
        mp.on("pageerror", lambda e: CONSOLE.append("pageerror(폰): " + str(e)))
        mp.goto(U(PN, "/voice-notes/%d/interp" % I["V2"]), wait_until="networkidle")
        mp.wait_for_selector("#list .it")
        mp.wait_for_timeout(400)
        chk("휴대폰 390: 가로 넘침 0 · 카드 15", mp.evaluate("document.documentElement.scrollWidth") <= 390 and mp.locator("#list .it").count() == 15)
        mp.screenshot(path=os.path.join(SHOTS, "q96_mobile.png"))
        mp.goto(U(PN, "/voice-notes/%d/interp" % I["V3"]), wait_until="networkidle")
        mp.screenshot(path=os.path.join(SHOTS, "q96_mobile_empty.png"))
        m.close()
        br.close()
    chk("콘솔 오류 0", not [x for x in CONSOLE if "favicon" not in x], CONSOLE[:3])
finally:
    kill(prB, prN)
    freeport(PB)
    freeport(PN)
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(0 if FAIL == 0 else 1)
