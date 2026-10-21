# -*- coding: utf-8 -*-
"""z1194 검사기 — 음성 메모 🖼 이미지 · 📝 파일(.md) · 일시·장소·참여자.
대표 2026-10-21 「음성메모 정리된걸 복사해서 대화방에 붙여 넣기 하면 … 텍스트 형태로 올라가는데.. 마크다운 방식에 파일 또는 음성메모 양식을
만들어 이미지로 복사해서 붙여 넣을수있게」 · 「그리고 정리할때 대화참여자,장소,시간도 기록할수있으면 좋겠어」
→ 시안 → 대표 선택 「둘 다 두기」 · 「사람이 적기 + 일시는 녹음 파일로 자동」 · 「만들어서 회귀 통과하면 올리기」

재는 것 (앱 두 벌 = 운영 그대로(app_base) · 새것(app_new) · 진짜 서버 · 진짜 브라우저 · AI 안 부름)
  ━ 서버 안 띄움 ━
  ① 🔴 정리는 그대로 — ai_client.py(정리 지시문)·그리기 규칙·목록 화면·회의록 화면 파일 글자 그대로
  ② 바뀐 자리 — main.py 는 정해 둔 네 줄만 바뀌고 나머지는 더한 줄 · 화면 파일은 두 줄만 바뀜 · 전역 timedelta 안 씀
  ③ 세 칸 다듬기(_vn_meta_from) · ④ 녹음 파일 → 일시 글(_vn_when_from_file: 본사 +9 · 베트남 +7 · 길이 · 자정 넘김 · 지어내지 않기)
  ⑤ 마이그레이션 두 번 = 두 번째는 더하는 것 없음
  ━ 진짜 서버 ━
  ⑥ 화면: 세 칸 · 🖼 이미지 · 📝 파일 단추(정리 전 흐림) · 🔴 반대: 운영엔 없음
  ⑦ 📋 복사: 세 칸 안 적은 메모 = 운영과 글자 그대로 · 적은 메모 = 머리 아래 세 줄만 더함
  ⑧ 🖼 이미지: 그리는 글(카드) — 제목·세 칸·정리(소제목 수)·작성 · 긴 메모만 📝 권함 · 클립보드에 그림(image/png) · 빈 그림 아님
  ⑨ 꺾쇠 글은 글자로만(그림·화면) · 📝 파일 내용(머리 · 세 칸 · 작성 · 정리 글자 그대로)
  ⑩ 세 칸 저장(입력칸을 벗어날 때 · 빈칸 정리 · 길이 한도 · 지우기) · API(만들 때·고칠 때·읽을 때) · 🔴 반대: 운영은 세 칸만 보내면 400
  ⑪ 녹음 올리기: 비어 있으면 파일 시각·길이로 채움(본사 +9 · 베트남 +7) · 이미 있으면 안 바꿈 · 파일 시각 없으면 안 채움
  ⑫ 권한(남의 메모 · 비로그인) · ⑬ 휴대폰 390 · ⑭ 목록 화면 카드 모양 그대로(바로 열기 · 메모에서 넘어가기) · ⑮ 콘솔 오류 0
쓰는 법: py q94_check.py <app_base·app_new 가 있는 폴더>   판정: 종료코드(0=통과) + 요약 줄.  🔒 시험 글은 모두 지어낸 것.
"""
import ast
import base64
import difflib
import hashlib
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1] if len(sys.argv) > 1 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
PB, PN = 8945, 8946
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
    pr = subprocess.Popen([P313, os.path.join(HERE, "run_q94_app.py"), os.path.join(APPDIR, app), str(port)],
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


def rd(app, rel):
    return io.open(os.path.join(APPDIR, app, "app", rel), encoding="utf-8").read()


def md5(app, rel):
    return hashlib.md5(io.open(os.path.join(APPDIR, app, "app", rel), "rb").read()).hexdigest()


def diff(a, b):
    return [d for d in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0)
            if d[:1] in "+-" and not d.startswith(("+++", "---"))]


def ffmake(path, secs):
    subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "sine=frequency=440:sample_rate=16000:duration=%s" % secs, "-ac", "1", path], check=True)


# ═══════════════════════ 서버 안 띄움 ═══════════════════════
print("── ① 정리는 그대로 — 그 밖의 파일 글자 그대로 ──")
for rel in ("ai_client.py", "i18n.py", "templates/_v5_partials/knk_md_lite.html", "templates/voice_notes.html",
            "templates/meeting_doc.html", "templates/meeting_form.html", "templates/meeting_viz.html",
            "templates/_v5_partials/styles.html", "templates/_v5_partials/knk_ai_busy.html"):
    chk("그대로: %s" % rel, md5("app_base", rel) == md5("app_new", rel))
chk("새 파일: 마이그레이션 m_z1194", os.path.exists(os.path.join(APPDIR, "app_new", "app", "migrations", "m_z1194_voice_note_meta.py"))
    and not os.path.exists(os.path.join(APPDIR, "app_base", "app", "migrations", "m_z1194_voice_note_meta.py")))

print("\n── ② 바뀐 자리 ──")
mb, mn = rd("app_base", "main.py"), rd("app_new", "main.py")
dm = diff(mb, mn)
rem = sorted(d[1:] for d in dm if d.startswith("-"))
EXP_REM = sorted([
    "async def api_voice_note_audio_upload(req: Request, nid: int, file: UploadFile = File(...)):",
    '    out = {k: n.get(k) for k in ("id", "title", "body", "summary", "audio_path", "created_at", "updated_at")}',
    '    return JSONResponse({"ok": True, "size_kb": _n // 1024})',
    '    return ctx(req, "voice_note_form.html", user=u, note=n)',
])
chk("main.py 바뀐 줄 = 정해 둔 네 줄(올리기 머리 · 읽기 칸 · 올리기 답 · 화면 넘김)", rem == EXP_REM, rem)
add = [d[1:] for d in dm if d.startswith("+")]
chk("main.py 더한 줄 수(보고용) %d" % len(add), 60 <= len(add) <= 120, len(add))
chk("전역 timedelta 안 씀 — 함수 안에서만 가져온다", all(("timedelta" not in a) or ("timedelta as _tdz" in a) for a in add)
    and not any(re.search(r"(?<![\w.])timedelta\(", a) for a in add))
chk("기동 마이그레이션 · 도우미 둘 · 화면 넘김 · 녹음 올리기", mn.count("[VOICE-META-MIG-Z1194]") == 1 and mn.count("def _vn_meta_from(") == 1
    and mn.count("def _vn_when_from_file(") == 1 and 'note=n, who_disp=who)' in mn and 'rec_end_ms: str = Form("")' in mn)
fb, fn = rd("app_base", "templates/voice_note_form.html"), rd("app_new", "templates/voice_note_form.html")
df = diff(fb, fn)
remf = [d[1:] for d in df if d.startswith("-")]
chk("화면 파일 바뀐 줄 = 두 줄(📋 복사 글 끝 · 새 메모 만들기)", sorted(remf) == sorted([
    "    return head + '\\n\\n' + s;",
    "        body: JSON.stringify({ title: ($('vnTitle').value||'').trim() }) });"]), remf)
chk("🔴 이름 겹침 없음 — 목록 화면의 .vn-card · .vn-meta 를 새로 정의하지 않는다",
    not re.search(r"^\s*\.vn-card\b|^\s*\.vn-meta\b", "\n".join(d[1:] for d in df if d.startswith("+")), re.M))

print("\n── ③ 세 칸 다듬기(_vn_meta_from) ──")


def grab(src, names, extra_ns=None):
    tree = ast.parse(src)
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in names)
            or (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in names for t in n.targets))]
    ns = dict(extra_ns or {})
    exec(compile(ast.Module(body=keep, type_ignores=[]), "main.py", "exec"), ns)
    return ns


NS = grab(mn, {"_VN_META_MAX", "_vn_meta_from", "_ko_wd"}, {"datetime": datetime})
mf = NS["_vn_meta_from"]
chk("적은 것만(만들 때)", mf({"meta_when": " a  b ", "meta_place": "", "meta_people": None, "x": 1}) == {"meta_when": "a b"})
chk("보낸 칸이면 빈 글도(고칠 때 · 지우기)", mf({"meta_place": "  "}, keep_empty=True) == {"meta_place": ""})
chk("줄바꿈·탭 → 한 칸", mf({"meta_people": "가\n\t나   다"}) == {"meta_people": "가 나 다"})
chk("길이 한도 100·100·300", [len(v) for v in mf({"meta_when": "x" * 500, "meta_place": "y" * 500, "meta_people": "z" * 500}).values()] == [100, 100, 300])
chk("dict 아니면 빈 결과", mf(None) == {} and mf("abc") == {})

print("\n── ④ 녹음 파일 → 일시 글(_vn_when_from_file) ──")


class _C:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


ENT = {"ent": "KOR"}
NS2 = grab(mn, {"_vn_when_from_file", "_ko_wd"},
           {"datetime": datetime, "db_session": lambda: _C(), "_meeting_user_entity": lambda c, u: (u or {}).get("ent", "KOR")})
vw = NS2["_vn_when_from_file"]
tmpd = tempfile.mkdtemp(prefix="q94_")
W125, W30, W150 = os.path.join(tmpd, "w125.wav"), os.path.join(tmpd, "w30.wav"), os.path.join(tmpd, "w150.wav")
ffmake(W125, "125")
ffmake(W30, "30")
ffmake(W150, "150")


def kfmt(ts, hrs):
    return datetime.fromtimestamp(ts, timezone(timedelta(hours=hrs)))


def wd(d):
    return "월화수목금토일"[d.weekday()]


now = time.time()
end = int(now - 3600)
e9, s9 = kfmt(end, 9), kfmt(end - 120, 9)   # 125초 → 2분(반올림) · 시작 = 끝 − 2분
exp9 = "%s (%s) %s ~ %s (2분)" % (s9.strftime("%Y-%m-%d"), wd(s9), s9.strftime("%H:%M"), e9.strftime("%H:%M"))
got9 = vw(W125, str(end * 1000), {"ent": "KOR"})
chk("본사(+9) · 125초 → 「… ~ … (2분)」", got9 == exp9, (got9, exp9))
e7, s7 = kfmt(end, 7), kfmt(end - 120, 7)
exp7 = "%s (%s) %s ~ %s (2분)" % (s7.strftime("%Y-%m-%d"), wd(s7), s7.strftime("%H:%M"), e7.strftime("%H:%M"))
got7 = vw(W125, str(end * 1000), {"ent": "VN"})
chk("베트남(+7) → 두 시간 앞", got7 == exp7, (got7, exp7))
g150 = vw(W150, str(end * 1000), {"ent": "KOR"})
s150 = kfmt(end - 180, 9)
chk("분은 반올림(150초 → 3분 · 시작 = 끝 − 3분)", g150 == "%s (%s) %s ~ %s (3분)" % (s150.strftime("%Y-%m-%d"), wd(s150), s150.strftime("%H:%M"), e9.strftime("%H:%M")), g150)
got30 = vw(W30, str(end * 1000), {"ent": "KOR"})
chk("1분 안 되는 녹음 → 끝 시각만 「HH:MM 녹음」", got30 == "%s (%s) %s 녹음" % (e9.strftime("%Y-%m-%d"), wd(e9), e9.strftime("%H:%M")), got30)
_path = os.environ.get("PATH", "")
os.environ["PATH"] = os.pathsep.join(p for p in _path.split(os.pathsep) if "ffmpeg" not in p.lower())
gotnp = vw(W125, str(end * 1000), {"ent": "KOR"})
os.environ["PATH"] = _path
chk("ffprobe 가 없으면 끝 시각만(지어내지 않음)", gotnp.endswith(" 녹음") and "~" not in gotnp, gotnp)
chk("파일 시각 없음·이상한 글 → 안 채움", vw(W125, "", {}) == "" and vw(W125, "abc", {}) == "" and vw(W125, "0", {}) == "")
chk("앞날(지금 + 1시간) → 안 채움", vw(W125, str(int((now + 3600) * 1000)), {}) == "")
chk("31일 전 → 안 채움", vw(W125, str(int((now - 31 * 86400) * 1000)), {}) == "")
kst = timezone(timedelta(hours=9))
mid = datetime.now(kst).replace(hour=0, minute=1, second=0, microsecond=0)
if mid.timestamp() > now:
    mid -= timedelta(days=1)
gotmid = vw(W125, str(int(mid.timestamp() * 1000)), {"ent": "KOR"})
pd = mid - timedelta(seconds=125)
chk("자정 넘김 → 시작 날짜로 「23:59 ~ 00:01 (2분)」", gotmid == "%s (%s) 23:59 ~ 00:01 (2분)" % (pd.strftime("%Y-%m-%d"), wd(pd)), gotmid)

print("\n── ⑤ 마이그레이션 두 번 ──")
import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location("m94", os.path.join(APPDIR, "app_new", "app", "migrations", "m_z1194_voice_note_meta.py"))
m94 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m94)
tdb = os.path.join(tmpd, "m.db")
cc = sqlite3.connect(tdb)
cc.execute("CREATE TABLE voice_notes(id INTEGER PRIMARY KEY, title TEXT NOT NULL DEFAULT '')")
cc.execute("INSERT INTO voice_notes(title) VALUES('x')")
cc.commit()
cc.close()
r1, r2 = m94.migrate(tdb), m94.migrate(tdb)
cc = sqlite3.connect(tdb)
row = cc.execute("SELECT meta_when, meta_place, meta_people FROM voice_notes").fetchone()
cc.close()
chk("첫 번째 = 세 칸 더함 · 두 번째 = 없음 · 옛 줄은 빈 글", r1["added"] == ["voice_notes.meta_when", "voice_notes.meta_place", "voice_notes.meta_people"]
    and r2["added"] == [] and row == ("", "", ""), (r1, r2, row))
tdb2 = os.path.join(tmpd, "m2.db")
sqlite3.connect(tdb2).close()
chk("표가 없으면 건너뜀", m94.migrate(tdb2).get("skip") == "voice_notes 없음")

# ═══════════════════════ 진짜 서버 + 진짜 브라우저 ═══════════════════════
prb, SB = boot("app_base", PB)
prn, SN = boot("app_new", PN)
ME, VNU = SN["me"], SN["vnu"]
I = SN["ids"]
chk("두 벌 같은 메모 번호", SB["ids"] == SN["ids"], (SB["ids"], SN["ids"]))
chk("새것만 세 칸 있음(운영 = 칸 없음)", SN["has_meta"] and not SB["has_meta"])
lp = io.open(os.path.join(APPDIR, "srv_%d.log" % PN), encoding="utf-8").read()
chk("기동 기록 [VOICE-META-MIG-Z1194] 세 칸", "[VOICE-META-MIG-Z1194] {'added': ['voice_notes.meta_when', 'voice_notes.meta_place', 'voice_notes.meta_people']}" in lp)

H2C_WRAP = """() => new Promise((res, rej) => {
  const go = () => { const real = window.html2canvas; window.__cards = [];
    window.html2canvas = function(el, opt){ window.__cards.push({ html: el.outerHTML, w: opt.width, h: opt.height, scale: opt.scale }); return real(el, opt); };
    res(true); };
  if (window.html2canvas) return go();
  const s = document.createElement('script'); s.src = '/static/vendor/html2canvas/html2canvas.min.js';
  s.onload = go; s.onerror = () => rej('no h2c'); document.head.appendChild(s); })"""
GET_IMG = """async () => { const u = document.querySelector('.vn-capprev img').src;
  const b = await (await fetch(u)).blob(); const ab = new Uint8Array(await b.arrayBuffer());
  let s = ''; for (let i = 0; i < ab.length; i += 32768) s += String.fromCharCode.apply(null, ab.subarray(i, i + 32768));
  return btoa(s); }"""
errs = {"b": [], "n": []}
dialogs = []
try:
    with sync_playwright() as pw:
        br = pw.chromium.launch()

        def mk(port, uid, w=1366, h=900, mobile=False):
            kw = dict(viewport={"width": w, "height": h}, locale="ko-KR", permissions=["clipboard-read", "clipboard-write"],
                      accept_downloads=True)
            if mobile:
                kw.update(device_scale_factor=2, is_mobile=True, has_touch=True)
            cx = br.new_context(**kw)
            cx.add_cookies([{"name": "tuser", "value": str(uid), "url": U(port, "/")}])
            pg = cx.new_page()
            k = "n" if port == PN else "b"
            pg.on("console", lambda m: errs[k].append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errs[k].append("pageerror: %s" % e))
            pg.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
            return cx, pg

        cxb, gb = mk(PB, ME)
        cxn, gn = mk(PN, ME)

        def clip(pg):
            return pg.evaluate("navigator.clipboard.readText()").replace("\r\n", "\n")

        # ═══════════ ⑥ 화면 ═══════════
        print("\n── ⑥ 화면: 세 칸 · 단추 ──")
        gn.goto(U(PN, "/voice-notes/%d" % I["N1"]), wait_until="networkidle")
        gb.goto(U(PB, "/voice-notes/%d" % I["N1"]), wait_until="networkidle")
        v = gn.evaluate("['vnWhen','vnPlace','vnPeople'].map(i => document.getElementById(i).value)")
        chk("N1 세 칸 값", v == ["2026-10-21 (화) 11:00 ~ 12:00 (60분)", "고객사 2층 회의실", "김한국 과장, 박다른 프로, 고객사 담당자"], v)
        chk("🖼 이미지 · 📝 파일 단추 켜짐", gn.evaluate("!document.getElementById('vnImg').disabled && !document.getElementById('vnMd').disabled"))
        chk("🔴 반대: 운영 화면엔 세 칸·두 단추 없음", gb.evaluate("!document.getElementById('vnWhen') && !document.getElementById('vnImg') && !document.getElementById('vnMd')"))
        gn.screenshot(path=os.path.join(SHOTS, "q94_N1_pc.png"))
        gn.goto(U(PN, "/voice-notes/%d" % I["N3"]), wait_until="networkidle")
        chk("정리 전(N3) → 🖼 · 📝 흐림(📋 복사와 같다)", gn.evaluate("document.getElementById('vnImg').disabled && document.getElementById('vnMd').disabled && document.getElementById('vnCopy').disabled"))

        # ═══════════ ⑦ 📋 복사 ═══════════
        print("\n── ⑦ 📋 복사 ──")
        gn.goto(U(PN, "/voice-notes/%d" % I["N2"]), wait_until="networkidle")
        gb.goto(U(PB, "/voice-notes/%d" % I["N2"]), wait_until="networkidle")
        gn.click("#vnCopy")
        gn.wait_for_timeout(300)
        tn2 = clip(gn)
        gb.click("#vnCopy")
        gb.wait_for_timeout(300)
        tb2 = clip(gb)
        chk("세 칸 안 적은 메모(N2) = 운영과 글자 그대로", tn2 == tb2 and len(tn2) > 20, (tn2[:80], tb2[:80]))
        gn.goto(U(PN, "/voice-notes/%d" % I["N1"]), wait_until="networkidle")
        gb.goto(U(PB, "/voice-notes/%d" % I["N1"]), wait_until="networkidle")
        gn.click("#vnCopy")
        gn.wait_for_timeout(300)
        tn1 = clip(gn).split("\n")
        gb.click("#vnCopy")
        gb.wait_for_timeout(300)
        tb1 = clip(gb).split("\n")
        chk("적은 메모(N1) = 머리 아래 세 줄만 더함", tn1[1:4] == ["일시: 2026-10-21 (화) 11:00 ~ 12:00 (60분)", "장소: 고객사 2층 회의실",
                                                         "참여자: 김한국 과장, 박다른 프로, 고객사 담당자"]
            and tn1[:1] + tn1[4:] == tb1, (tn1[:5], tb1[:3]))

        # ═══════════ ⑧ 🖼 이미지 ═══════════
        print("\n── ⑧ 🖼 이미지 ──")
        gn.evaluate(H2C_WRAP)
        gn.click("#vnImg")
        gn.wait_for_selector(".vn-capov .vn-capprev img", timeout=60000)
        gn.wait_for_function("document.querySelector('.vn-capprev img').complete && document.querySelector('.vn-capprev img').naturalWidth > 0")
        cards = gn.evaluate("window.__cards")
        chk("그림은 한 번 그림(html2canvas 1회)", len(cards) == 1, len(cards))
        ch = cards[0]["html"] if cards else ""
        chk("카드 폭 480 · 배율 2 이상", cards and cards[0]["w"] == 480 and cards[0]["scale"] >= 2, cards and {k: cards[0][k] for k in ("w", "h", "scale")})
        chk("카드 = 로고 · 「음성 메모」 · 제목", 'class="vc-logo"' in ch and ">음성 메모<" in ch and "거래처 방문 정리(지어낸 글)" in ch)
        rows = re.findall(r'<span class="vc-k">([^<]*)</span><span class="vc-v">([^<]*)</span>', ch)
        chk("카드 세 칸(일시·장소·참여자 · 적은 그대로)", rows == [("일시", "2026-10-21 (화) 11:00 ~ 12:00 (60분)"), ("장소", "고객사 2층 회의실"),
                                                     ("참여자", "김한국 과장, 박다른 프로, 고객사 담당자")], rows)
        chk("카드 정리 = 화면과 같은 규칙(소제목 10 = 핵심 + 주제 8 + 할 일)", ch.count('class="md-s"') == 10, ch.count('class="md-s"'))
        who = db("app_new", "SELECT u.name, u.rank, t.name tn FROM users u LEFT JOIN teams t ON u.team_id=t.id WHERE u.id=?", (ME,))[0]
        chk("카드 아래 「작성 이름 직책 부서」", ("작성 %s %s %s" % (who["name"], who["rank"], who["tn"])) in ch, re.findall(r'class="vc-foot">(.*?)</div>', ch))
        sz = gn.evaluate("document.querySelector('.vn-capsz').textContent")
        chk("그림 크기 = 960 × (480 × 배율) · 세로 김", sz.startswith("960×") and int(sz.split("×")[1].split(" ")[0]) > 960 * 2.2, sz)
        chk("긴 메모 → 📝 파일 권하는 줄", gn.locator(".vn-capov .vn-captall").count() == 1)
        png = base64.b64decode(gn.evaluate(GET_IMG))
        try:
            from PIL import Image
            im = Image.open(io.BytesIO(png)).convert("RGB")
            ex = im.getextrema()
            red = sum(1 for x in range(0, im.size[0], 4) for y in range(0, min(400, im.size[1]), 4)
                      if abs(im.getpixel((x, y))[0] - 0xa5) < 30 and im.getpixel((x, y))[1] < 80)
            chk("빈 그림 아님 · 위쪽에 회사 빨간 줄", ex[0][0] < 100 and red > 20, (ex, red))
        except ImportError:
            chk("빈 그림 아님(PIL 없음 — 크기만)", len(png) > 20000, len(png))
        gn.screenshot(path=os.path.join(SHOTS, "q94_preview_pc.png"))
        io.open(os.path.join(SHOTS, "q94_card_N1.png"), "wb").write(png)
        gn.click(".vn-capov .cap-copy")
        gn.wait_for_timeout(700)
        ty = gn.evaluate("navigator.clipboard.read().then(items => items.map(i => i.types.join(',')).join('|'))")
        chk("📋 이미지 복사 → 클립보드에 그림만(image/png · 글 없음)", ty == "image/png", ty)
        chk("복사 알림", "복사했습니다" in gn.evaluate("document.querySelector('.vn-capmsg').textContent"))
        with gn.expect_download() as dl0:
            gn.click(".vn-capov .cap-save")
        chk("💾 이미지 저장 → png 내려받기", dl0.value.suggested_filename == "음성메모_거래처 방문 정리(지어낸 글)_2026-10-21.png", dl0.value.suggested_filename)
        gn.click(".vn-capov .cap-close")
        chk("닫기 → 창 없어짐", gn.locator(".vn-capov").count() == 0)
        gn.click("#vnImg")
        gn.wait_for_selector(".vn-capov .vn-capprev img", timeout=60000)
        chk("같은 글이면 그림을 다시 그리지 않음", len(gn.evaluate("window.__cards")) == 1)
        gn.click(".vn-capov .cap-close")
        gn.fill("#vnPlace", "고객사 3층 회의실")
        gn.click("#vnTitle")
        gn.wait_for_timeout(400)
        gn.click("#vnImg")
        gn.wait_for_selector(".vn-capov .vn-capprev img", timeout=60000)
        c2 = gn.evaluate("window.__cards")
        chk("칸을 고치면 새로 그림(고친 장소가 그림에)", len(c2) == 2 and "고객사 3층 회의실" in c2[1]["html"], len(c2))
        gn.click(".vn-capov .cap-close")

        gn.goto(U(PN, "/voice-notes/%d" % I["N2"]), wait_until="networkidle")
        gn.evaluate(H2C_WRAP)
        gn.click("#vnImg")
        gn.wait_for_selector(".vn-capov .vn-capprev img", timeout=60000)
        c3 = gn.evaluate("window.__cards")
        chk("짧은 메모(N2) = 세 칸 상자 없음 · 📝 권하는 줄 없음", c3 and 'class="vc-meta"' not in c3[0]["html"] and gn.locator(".vn-capov .vn-captall").count() == 0)
        gn.click(".vn-capov .cap-close")

        # ═══════════ ⑨ 꺾쇠 글 · 📝 파일 ═══════════
        print("\n── ⑨ 꺾쇠 글은 글자로만 · 📝 파일 ──")
        gn.goto(U(PN, "/voice-notes/%d" % I["N4"]), wait_until="networkidle")
        gn.evaluate(H2C_WRAP)
        gn.click("#vnImg")
        gn.wait_for_selector(".vn-capov .vn-capprev img", timeout=60000)
        c4 = gn.evaluate("window.__cards")[0]["html"]
        chk("그림 카드: 제목·세 칸·정리의 꺾쇠 = 글자(&lt;) · 진짜 태그 없음",
            "꺾쇠 &lt;b&gt;제목&lt;/b&gt;" in c4 and "&lt;img src=x onerror=alert(3)&gt;" in c4 and c4.count("<img") == 1
            and "<script" not in c4 and "&lt;script&gt;" in c4, re.findall(r"<img[^>]*>", c4))
        chk("화면도 대화상자(alert) 안 뜸", not dialogs, dialogs)
        gn.click(".vn-capov .cap-close")
        with gn.expect_download() as dl4:
            gn.click("#vnMd")
        md4 = io.open(dl4.value.path(), encoding="utf-8").read()
        chk("📝 파일 이름의 꺾쇠·빗금 지움", "<" not in dl4.value.suggested_filename and dl4.value.suggested_filename.endswith("_2026-10-21.md"), dl4.value.suggested_filename)
        chk("📝 파일은 글 그대로(이음이 막고 그린다)", md4.startswith("# 꺾쇠 <b>제목</b>\n"))

        gn.goto(U(PN, "/voice-notes/%d" % I["N1"]), wait_until="networkidle")
        gn.fill("#vnPlace", "고객사 2층 회의실")
        gn.click("#vnTitle")
        gn.wait_for_timeout(400)
        with gn.expect_download() as dl1:
            gn.click("#vnMd")
        md1 = io.open(dl1.value.path(), encoding="utf-8").read()
        s1 = db("app_new", "SELECT summary FROM voice_notes WHERE id=?", (I["N1"],))[0]["summary"]
        whod = "%s %s %s" % (who["name"], who["rank"], who["tn"])
        exp1 = ("# 거래처 방문 정리(지어낸 글)\n\n- **일시**: 2026-10-21 (화) 11:00 ~ 12:00 (60분)\n- **장소**: 고객사 2층 회의실\n"
                "- **참여자**: 김한국 과장, 박다른 프로, 고객사 담당자\n- **작성**: %s\n\n%s\n" % (whod, s1.strip()))
        chk("📝 N1 파일 = 제목 · 세 칸 · 작성 · 정리 글자 그대로", md1 == exp1, md1[:200])
        chk("📝 이름 = 음성메모_제목_날짜.md", dl1.value.suggested_filename == "음성메모_거래처 방문 정리(지어낸 글)_2026-10-21.md", dl1.value.suggested_filename)
        chk("📝 알림", "마크다운 파일을 저장했습니다" in gn.inner_text("#vnSt"))
        gn.goto(U(PN, "/voice-notes/%d" % I["N2"]), wait_until="networkidle")
        with gn.expect_download() as dl2:
            gn.click("#vnMd")
        md2 = io.open(dl2.value.path(), encoding="utf-8").read()
        s2 = db("app_new", "SELECT summary FROM voice_notes WHERE id=?", (I["N2"],))[0]["summary"]
        chk("📝 N2(세 칸 비움) = 제목 · 작성 · 정리", md2 == "# 짧은 메모(지어낸 글)\n\n- **작성**: %s\n\n%s\n" % (whod, s2.strip()), md2[:120])

        # ═══════════ ⑩ 세 칸 저장 · API ═══════════
        print("\n── ⑩ 세 칸 저장 · API ──")
        gn.fill("#vnPlace", "  고객사    공장  ")
        gn.click("#vnTitle")
        gn.wait_for_timeout(500)
        gn.fill("#vnPeople", "가" * 400)
        gn.click("#vnTitle")
        gn.wait_for_timeout(500)
        r2 = db("app_new", "SELECT meta_place, meta_people, meta_when FROM voice_notes WHERE id=?", (I["N2"],))[0]
        chk("벗어날 때 저장 · 빈칸 정리 · 참여자 300자까지(입력칸도 300)", r2["meta_place"] == "고객사 공장" and len(r2["meta_people"]) == 300, (r2["meta_place"], len(r2["meta_people"])))
        gn.fill("#vnPlace", "")
        gn.click("#vnTitle")
        gn.wait_for_timeout(500)
        chk("지우면 빈 글로 저장", db("app_new", "SELECT meta_place FROM voice_notes WHERE id=?", (I["N2"],))[0]["meta_place"] == "")
        gn.reload(wait_until="networkidle")
        chk("다시 열어도 그대로", gn.evaluate("document.getElementById('vnPlace').value") == "" and len(gn.evaluate("document.getElementById('vnPeople').value")) == 300)

        def api(pg, port, path, body=None, method="POST"):
            r = pg.request.fetch(U(port, path), method=method, data=json.dumps(body) if body is not None else None,
                                 headers={"Content-Type": "application/json"})
            try:
                return r.status, r.json()
            except Exception:
                return r.status, {}
        st, j = api(gn, PN, "/api/voice-note", {"title": "API 메모", "meta_place": " 공장 ", "meta_people": "", "meta_when": "어제"})
        rr = db("app_new", "SELECT meta_when, meta_place, meta_people FROM voice_notes WHERE id=?", (j.get("id"),))
        chk("만들 때 세 칸 함께(적은 것만)", st == 200 and rr and rr[0] == {"meta_when": "어제", "meta_place": "공장", "meta_people": ""}, (st, rr))
        st, j = api(gn, PN, "/api/voice-note/%d/save" % I["N2"], {"meta_when": "오늘 \n 오후"})
        chk("고칠 때 세 칸만 보내도 됨(200)", st == 200 and db("app_new", "SELECT meta_when FROM voice_notes WHERE id=?", (I["N2"],))[0]["meta_when"] == "오늘 오후", (st, j))
        st, j = api(gb, PB, "/api/voice-note/%d/save" % I["N2"], {"meta_when": "오늘"})
        chk("🔴 반대: 운영은 세 칸만 보내면 400(모르는 칸)", st == 400, (st, j))
        st, j = api(gn, PN, "/api/voice-note/%d" % I["N1"], method="GET")
        chk("읽기에 세 칸", st == 200 and j["note"].get("meta_place") == "고객사 2층 회의실" and "meta_when" in j["note"] and "meta_people" in j["note"], j.get("note", {}).keys())
        st, j = api(gb, PB, "/api/voice-note/%d" % I["N1"], method="GET")
        chk("🔴 반대: 운영 읽기엔 세 칸 없음", st == 200 and "meta_when" not in j["note"])

        # ═══════════ ⑪ 녹음 올리기 → 일시 ═══════════
        print("\n── ⑪ 녹음 올리기 → 일시 ──")

        def up(pg, port, nid, wav, ms=None):
            mp = {"file": {"name": "rec.wav", "mimeType": "audio/wav", "buffer": io.open(wav, "rb").read()}}
            if ms is not None:
                mp["rec_end_ms"] = str(ms)
            r = pg.request.post(U(port, "/api/voice-note/%d/audio" % nid), multipart=mp)
            try:
                return r.status, r.json()
            except Exception:
                return r.status, {}
        endms = int((time.time() - 1800) * 1000)
        e9, s9 = kfmt(endms / 1000.0, 9), kfmt(endms / 1000.0 - 120, 9)
        exp9 = "%s (%s) %s ~ %s (2분)" % (s9.strftime("%Y-%m-%d"), wd(s9), s9.strftime("%H:%M"), e9.strftime("%H:%M"))
        st, j = up(gn, PN, I["N5"], W125, endms)
        chk("비어 있으면 파일 시각·길이로 채움(본사 +9 · 답에도)", st == 200 and j.get("meta_when") == exp9
            and db("app_new", "SELECT meta_when FROM voice_notes WHERE id=?", (I["N5"],))[0]["meta_when"] == exp9, (st, j, exp9))
        st, j = up(gn, PN, I["N5"], W30, endms - 7200 * 1000)
        chk("다시 올려도 이미 있는 일시는 안 바꿈", st == 200 and j.get("meta_when") == exp9, j)
        st, j = up(gn, PN, I["N6"], W125, endms)
        chk("사람이 먼저 적은 일시는 안 바꿈", st == 200 and j.get("meta_when") == "사람이 적은 일시", j)
        st, j0 = api(gn, PN, "/api/voice-note", {"title": "파일 시각 없음"})
        st, j = up(gn, PN, j0["id"], W125, None)
        chk("파일 시각을 안 보내면 안 채움", st == 200 and j.get("meta_when") == "", j)
        cxv, gv = mk(PN, VNU)
        e7, s7 = kfmt(endms / 1000.0, 7), kfmt(endms / 1000.0 - 120, 7)
        exp7 = "%s (%s) %s ~ %s (2분)" % (s7.strftime("%Y-%m-%d"), wd(s7), s7.strftime("%H:%M"), e7.strftime("%H:%M"))
        st, j = up(gv, PN, I["NV"], W125, endms)
        chk("베트남법인 직원 → +7 로", st == 200 and j.get("meta_when") == exp7, (j, exp7))
        st, j = up(gb, PB, I["N5"], W125, endms)
        chk("🔴 반대: 운영 올리기 답엔 일시 없음(파일 시각을 몰라 그냥 받는다)", st == 200 and "meta_when" not in j, j)
        gn.goto(U(PN, "/voice-notes/%d" % I["N5"]), wait_until="networkidle")
        chk("화면에도 채운 일시", gn.evaluate("document.getElementById('vnWhen').value") == exp9)

        # ═══════════ ⑫ 권한 ═══════════
        print("\n── ⑫ 권한 ──")
        rp = gn.request.get(U(PN, "/voice-notes/%d" % I["NO"]), max_redirects=0)
        chk("남의 메모 화면 → 목록으로(303)", rp.status == 303 and rp.headers.get("location", "").endswith("/voice-notes"), (rp.status, rp.headers.get("location")))
        st, j = api(gn, PN, "/api/voice-note/%d/save" % I["NO"], {"meta_place": "x"})
        chk("남의 메모 세 칸 고치기 → 404", st == 404, (st, j))
        st, j = up(gn, PN, I["NO"], W30, endms)
        chk("남의 메모 녹음 올리기 → 404", st == 404, (st, j))
        cx0 = br.new_context()
        cx0.add_cookies([{"name": "tuser", "value": "0", "url": U(PN, "/")}])
        p0 = cx0.new_page()
        r0 = p0.request.post(U(PN, "/api/voice-note/%d/save" % I["N2"]), data=json.dumps({"meta_place": "x"}), headers={"Content-Type": "application/json"})
        chk("비로그인 → 401", r0.status == 401, r0.status)
        cx0.close()
        chk("남의 메모·비로그인 시도 뒤에도 내 값 그대로", db("app_new", "SELECT meta_place FROM voice_notes WHERE id=?", (I["NO"],))[0]["meta_place"] == "")

        # ═══════════ ⑬ 휴대폰 ═══════════
        print("\n── ⑬ 휴대폰 390 ──")
        cxm, gm = mk(PN, ME, 390, 844, mobile=True)
        gm.goto(U(PN, "/voice-notes/%d" % I["N1"]), wait_until="networkidle")
        gm.wait_for_timeout(800)
        gm.evaluate("() => { const b = Array.from(document.querySelectorAll('button')).find(x => x.textContent.trim() === '닫기' && x.offsetParent); if (b) b.click(); }")
        box = gm.evaluate("['vnWhen','vnPlace','vnPeople'].map(i => { const r = document.getElementById(i).getBoundingClientRect(); return [Math.round(r.left), Math.round(r.width), Math.round(r.top)]; })")
        chk("세 칸이 한 줄씩 쌓임(왼쪽·폭 같음 · 위아래)", len({b[0] for b in box}) == 1 and len({b[1] for b in box}) == 1 and box[0][2] < box[1][2] < box[2][2], box)
        chk("가로 넘침 없음", gm.evaluate("document.documentElement.scrollWidth") <= 392, gm.evaluate("document.documentElement.scrollWidth"))
        chk("단추 넷 다 보임", gm.evaluate("['vnCopy','vnImg','vnMd','vnDel'].every(i => { const e = document.getElementById(i); return e && e.offsetParent && e.getBoundingClientRect().right <= 392; })"))
        gm.screenshot(path=os.path.join(SHOTS, "q94_N1_phone.png"))
        cxm.close()

        # ═══════════ ⑭ 목록 화면 그대로 ═══════════
        print("\n── ⑭ 목록 화면 카드 모양 그대로 ──")
        STY = "() => { const c = document.querySelector('a.vn-card'); const m = c && c.querySelector('.vn-meta'); if (!c) return null; const s = getComputedStyle(c), t = m ? getComputedStyle(m) : {};" \
              " return [document.querySelectorAll('a.vn-card').length, s.display, s.paddingTop, s.borderTopWidth, s.backgroundColor, Math.round(c.getBoundingClientRect().width), t.display, t.fontSize]; }"
        gb.goto(U(PB, "/voice-notes"), wait_until="networkidle")
        gn.goto(U(PN, "/voice-notes"), wait_until="networkidle")
        sb, sn = gb.evaluate(STY), gn.evaluate(STY)
        chk("바로 연 목록: 카드 수·모양 = 운영(카드 수는 API 로 만든 2장만 더)", sn and sb and sn[1:] == sb[1:] and sn[0] == sb[0] + 2, (sb, sn))
        gn.goto(U(PN, "/voice-notes/%d" % I["N1"]), wait_until="networkidle")
        gn.click(".page-meta a[href='/voice-notes']")
        gn.wait_for_selector("a.vn-card", timeout=20000)
        gn.wait_for_timeout(500)
        chk("메모 화면에서 넘어간 목록도 같은 모양(그림 카드 이름이 안 샘)", gn.evaluate(STY)[1:] == sn[1:], (gn.evaluate(STY), sn))

        # ═══════════ ⑮ 콘솔 ═══════════
        print("\n── ⑮ 콘솔 ──")
        on = [e for e in errs["n"] if KNOWN not in e]
        ob = [e for e in errs["b"] if KNOWN not in e]
        chk("새것 콘솔 오류 0", not on, on[:3])
        chk("운영 콘솔 오류 0", not ob, ob[:3])
        br.close()
finally:
    kill(prb, prn)
    freeport(PB)
    freeport(PN)

print("\n=============================================")
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
