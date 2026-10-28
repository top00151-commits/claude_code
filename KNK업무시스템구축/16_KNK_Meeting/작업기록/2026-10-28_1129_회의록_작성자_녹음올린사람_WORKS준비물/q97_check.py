# -*- coding: utf-8 -*-
"""z1197 검사 — 회의록 「작성자」(기본 = 녹음 파일 올린 사람 · 바꾸기) · 바탕(app_base)과 새것(app_new) 나란히 · 진짜 서버 · 진짜 브라우저.

재는 것
  ① 파일: 바뀐 것 = main.py · i18n.py · meeting_form.html · 새 마이그레이션 넷뿐 · 권한 네 함수(_can_view/_edit/_delete/_end_meeting) 글자 그대로
  ② 마이그레이션: 새 서버 DB 에 칸 5개 · 다시 돌려도 더하는 것 0(idempotent) · 바탕 DB 엔 없음
  ③ 흐름(지어낸 회의록 M4 · 만든 사람 = 팀원 A · 참석자 = 팀원 B):
     녹음 전: 작성자 = 만든 사람 A · A 는 ✏ 단추 있음(올린 사람 기록 없으니 지금 작성자) · B 는 단추 없음(작성자 글은 보임)
     B 가 녹음 올림 → audio_by=B · 작성자 = B(기본값) · B 단추 있음 · A 단추 없음(대표 말: 바꾸는 건 녹음 올린 사람) · A 의 바꾸기 요청 403 · B 가 임원 C 로 바꿈 200(손으로 정함)
     B 가 다시 올려도 작성자 C 그대로(손으로 정한 건 안 덮음) · 후보 목록 B 200(manual) · A 403 · 관리자 바꾸기 200 · 기본값으로(0) → 작성자 = B
     양식 「부서/작성자」 = 작성자(C 의 부서·이름) · 목록 ✍ = 작성자 · 찾기 = 작성자 이름으로 M4 · 삭제 권한 그대로(A 있음 · C 없음) · 바탕엔 작성자 API 없음(404)
  ④ 화면: 콘솔 오류 0 · ✏ 누르면 고르기 열림 · 후보 눌러 바꾸면 글자 바뀜·알림 · 폭 390 넘침 없음 · 베트남어 사용자에겐 「Người lập」
  ⑤ 사진: 작성자 줄 390·904 (shots/)
쓰는 법: py -3.12 q97_check.py <app_base·app_new 가 있는 폴더>   판정: 종료코드(0=통과) + 요약 줄.  🔒 시험 글은 모두 지어낸 것."""
import hashlib
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # 🔴 회귀는 출력을 파일로 보낸다(cp949) — ✅ 글자에서 죽지 않게(z1198 회귀 교훈)
HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1] if len(sys.argv) > 1 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
Z96PREP = r"C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\16_KNK_Meeting\작업기록\2026-10-27_1802_통역대조_WORKS준비물"
RUN = os.path.join(HERE, "run_q97_app.py")
if not os.path.exists(RUN):
    RUN = os.path.join(Z96PREP, "run_q96_app.py")
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
PORTS = {"app_base": 8969, "app_new": 8970}
N = OK = 0
FAILS = []


def chk(name, cond, extra=""):
    global N, OK
    N += 1
    if cond:
        OK += 1
        print("  ✅", name, extra)
    else:
        FAILS.append(name)
        print("  ❌", name, extra)


def start(app):
    port = PORTS[app]
    lp = os.path.join(APPDIR, "srv97_%d.log" % port)
    pr = subprocess.Popen([P313, RUN, os.path.join(APPDIR, app), str(port)],
                          stdout=io.open(lp, "w", encoding="utf-8"), stderr=subprocess.STDOUT, cwd=APPDIR)
    for _ in range(90):
        time.sleep(1)
        try:
            txt = io.open(lp, encoding="utf-8", errors="replace").read()
        except OSError:
            txt = ""
        for ln in txt.splitlines():
            if ln.startswith("READY"):
                return pr, json.loads(ln.split(" ", 2)[2])
        if pr.poll() is not None:
            break
    print("⛔ %s 서버가 안 떴다 — %s" % (app, lp))
    print(io.open(lp, encoding="utf-8", errors="replace").read()[-1500:])
    sys.exit(2)


def dbp(app):
    return os.path.join(APPDIR, app, "data", "knk.db")


def q1(app, sql, args=()):
    c = sqlite3.connect(dbp(app))
    c.row_factory = sqlite3.Row
    r = c.execute(sql, args).fetchone()
    c.close()
    return dict(r) if r else None


def qx(app, sql, args=()):
    c = sqlite3.connect(dbp(app))
    c.execute(sql, args)
    c.commit()
    c.close()


def req(app, method, path, uid, body=None, raw=None, ctype=None):
    url = "http://127.0.0.1:%d%s" % (PORTS[app], path)
    data = raw if raw is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Cookie", "tuser=%s" % uid)
    if data is not None:
        r.add_header("Content-Type", ctype or "application/json")
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def upload(app, mid, uid, path):
    b = "----q97" + uuid.uuid4().hex
    body = (("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"rec.wav\"\r\nContent-Type: audio/wav\r\n\r\n" % b).encode("utf-8")
            + io.open(path, "rb").read() + ("\r\n--%s--\r\n" % b).encode("utf-8"))
    return req(app, "POST", "/api/meeting/%d/audio" % mid, uid, raw=body, ctype="multipart/form-data; boundary=%s" % b)


def rd(app, rel):
    return io.open(os.path.join(APPDIR, app, "app", rel), encoding="utf-8").read()


def walk(app):
    root = os.path.join(APPDIR, app, "app")
    out = {}
    for d, _dirs, files in os.walk(root):
        if "__pycache__" in d:
            continue
        for f in files:
            if f.endswith((".pyc", ".bak_z1197")):
                continue
            full = os.path.join(d, f)
            out[os.path.relpath(full, root).replace("\\", "/")] = hashlib.md5(io.open(full, "rb").read()).hexdigest()
    return out


def func_text(src, name):
    m = re.search(r"\ndef %s\(.*?(?=\n(?:def |@app\.|_[A-Z_]+ *=|# z1197))" % re.escape(name), src, re.S)
    return m.group(0) if m else None


print("== ① 파일 ==")
WB, WN = walk("app_base"), walk("app_new")
changed = sorted(k for k in set(WB) | set(WN) if WB.get(k) != WN.get(k))
chk("바뀐 파일 = main · i18n · 회의록 화면 · 새 마이그레이션", changed == ["i18n.py", "main.py", "migrations/m_z1197_meeting_author.py", "templates/meeting_form.html"], str(changed))
MB, MN = rd("app_base", "main.py"), rd("app_new", "main.py")
for fn in ("_can_view_meeting", "_can_edit_meeting", "_can_delete_meeting", "_can_end_meeting"):
    a, b = func_text(MB, fn), func_text(MN, fn)
    chk("권한 함수 그대로: %s" % fn, a is not None and a == b, "" if a == b else "다름")
chk("새 것: 작성자 API 2 · 올리기 세 길에 _mtg_audio_uploaded 3 · 양식 2 · 목록 COALESCE",
    MN.count('/author-candidates"') == 1 and MN.count('"/api/meeting/{mid:int}/author"') == 1 and MN.count("_mtg_audio_uploaded(c, mid,") == 3
    and MN.count("(_mtg_author_id(m),)).fetchone()") == 1 and MN.count("user_disp_by_id(c, _mtg_author_id(m), ") == 1 and "COALESCE(au.name, usr.name) AS owner_name" in MN)

print("== 서버 두 벌 ==")
PRS, SEED = {}, {}
for app in ("app_base", "app_new"):
    PRS[app], SEED[app] = start(app)
    print("  %s 포트 %d" % (app, PORTS[app]))
ME = SEED["app_new"]["me"]
import importlib.util   # noqa: E402

print("== ② 마이그레이션 ==")
cols = {r[1] for r in sqlite3.connect(dbp("app_new")).execute("PRAGMA table_info(meetings)")}
chk("새 DB 에 작성자 칸 5", {"author_id", "author_set_by", "author_set_at", "audio_by", "audio_by_at"} <= cols)
spec = importlib.util.spec_from_file_location("m97", os.path.join(APPDIR, "app_new", "app", "migrations", "m_z1197_meeting_author.py"))
m97 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m97)
chk("다시 돌려도 더하는 칸 0(idempotent)", m97.migrate(dbp("app_new")) == {"added": []})
colsb = {r[1] for r in sqlite3.connect(dbp("app_base")).execute("PRAGMA table_info(meetings)")}
chk("바탕 DB 엔 작성자 칸 없음", "author_id" not in colsb)


def seed_m4(app):
    """지어낸 회의록 M4 — 만든 사람 A(팀원) · 참석자 B(같은 팀 팀원) · 임원 C(다른 팀) · 관리자 D"""
    c = sqlite3.connect(dbp(app))
    c.row_factory = sqlite3.Row
    team = c.execute("SELECT team_id FROM users WHERE id=?", (ME,)).fetchone()["team_id"]
    mem = [r["id"] for r in c.execute("SELECT id FROM users WHERE role='member' AND team_id=? AND is_active=1 ORDER BY id LIMIT 2", (team,))]
    exe = c.execute("SELECT id FROM users WHERE role='executive' AND team_id<>? AND is_active=1 ORDER BY id", (team,)).fetchone()["id"]
    adm = c.execute("SELECT id FROM users WHERE role='admin' AND is_active=1 ORDER BY id").fetchone()["id"]
    a, b = mem[0], mem[1]
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    cur = c.execute("INSERT INTO meetings(title, meeting_date, owner_id, team_id, location, body, summary, visibility, status, created_at, updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?)", ("작성자 시험(지어낸 글)", now[:10], a, team, "", "지어낸 회의 내용", "", "team", "draft", now, now))
    mid = cur.lastrowid
    nm = c.execute("SELECT name FROM users WHERE id=?", (b,)).fetchone()["name"]
    c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,?)", (mid, b, nm))
    c.commit()
    c.close()
    return mid, a, b, exe, adm


def name_of(app, uid):
    return q1(app, "SELECT name FROM users WHERE id=?", (uid,))["name"]


def team_name_of(app, uid):
    r = q1(app, "SELECT t.name AS tn FROM users u LEFT JOIN teams t ON u.team_id=t.id WHERE u.id=?", (uid,))
    return (r or {}).get("tn") or ""


def mrow(mid):
    return q1("app_new", "SELECT * FROM meetings WHERE id=?", (mid,))


def page(app, path, uid):
    return req(app, "GET", path, uid)[1]


#  녹음 파일(지어낸 소리 3초)
FX = os.path.join(APPDIR, "q97_fx.wav")
if not os.path.exists(FX):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-ar", "16000", "-ac", "1", FX], check=True)

print("== ③ 흐름(새것) ==")
M4, A, Bu, C, D = seed_m4("app_new")
print("  M4=%d A=%d B=%d C=%d D=%d" % (M4, A, Bu, C, D))
h = page("app_new", "/meetings/%d" % M4, A)
chk("녹음 전: 작성자 = 만든 사람 A · A 는 ✏ 단추 있음", ('id="authorDisp"' in h) and (name_of("app_new", A) in h.split('id="authorDisp"')[1][:200]) and 'id="btnAuthor"' in h)
h = page("app_new", "/meetings/%d" % M4, Bu)
chk("녹음 전: 참석자 B 는 작성자 글은 보이고 ✏ 단추 없음", 'id="authorDisp"' in h and 'id="btnAuthor"' not in h)
st, body = upload("app_new", M4, Bu, FX)
r = mrow(M4)
chk("B 가 녹음 올림 → 200 · audio_by=B · 작성자=B(기본값) · 손으로 정함 없음", st == 200 and r["audio_by"] == Bu and r["author_id"] == Bu and not r["author_set_by"], "%s %s" % (st, body[:80]))
h = page("app_new", "/meetings/%d" % M4, Bu)
chk("올린 B 의 화면: 작성자 = B · ✏ 단추 있음", name_of("app_new", Bu) in h.split('id="authorDisp"')[1][:200] and 'id="btnAuthor"' in h)
h = page("app_new", "/meetings/%d" % M4, A)
chk("만든 A 의 화면: ✏ 단추 없음(바꾸는 건 녹음 올린 사람 — 대표 말 그대로)", 'id="btnAuthor"' not in h and 'id="authorDisp"' in h)
st, body = req("app_new", "POST", "/api/meeting/%d/author" % M4, A, {"user_id": C})
chk("A 의 바꾸기 요청 403", st == 403, "%s %s" % (st, body[:80]))
st, body = req("app_new", "POST", "/api/meeting/%d/author" % M4, Bu, {"user_id": C})
j = json.loads(body) if st == 200 else {}
r = mrow(M4)
chk("B 가 임원 C 로 바꿈 → 200 · 작성자=C · 손으로 정함=B · 응답 글 = C 이름", st == 200 and r["author_id"] == C and r["author_set_by"] == Bu and name_of("app_new", C) in (j.get("author_disp") or "") and j.get("manual") is True, body[:120])
chk("권한 칸(owner_id)은 그대로 A", r["owner_id"] == A)
st, body = upload("app_new", M4, Bu, FX)
r = mrow(M4)
chk("B 가 다시 올려도 작성자 C 그대로(손으로 정한 건 안 덮음) · audio_by 는 B", st == 200 and r["author_id"] == C and r["audio_by"] == Bu)
st, body = req("app_new", "GET", "/api/meeting/%d/author-candidates?q=" % M4, Bu)
j = json.loads(body) if st == 200 else {}
chk("후보 목록(B) 200 · manual · 후보 ≤8 · 이름 직책 부서 모양", st == 200 and j.get("ok") and j.get("manual") is True and 0 < len(j.get("users") or []) <= 8 and all(x.get("disp") for x in j["users"]), body[:100])
st, body = req("app_new", "GET", "/api/meeting/%d/author-candidates?q=" % M4, A)
chk("후보 목록(A) 403", st == 403)
st, body = req("app_new", "POST", "/api/meeting/%d/author" % M4, D, {"user_id": A})
r = mrow(M4)
chk("관리자 D 가 A 로 바꿈 200", st == 200 and r["author_id"] == A and r["author_set_by"] == D)
st, body = req("app_new", "POST", "/api/meeting/%d/author" % M4, D, {"user_id": 0})
r = mrow(M4)
chk("기본값으로(0) → 작성자 = 녹음 올린 B · 손으로 정함 없음", st == 200 and r["author_id"] == Bu and not r["author_set_by"])
st, body = req("app_new", "POST", "/api/meeting/%d/author" % M4, Bu, {"user_id": 999999})
chk("없는 직원 404", st == 404)
st, body = req("app_new", "POST", "/api/meeting/%d/author" % M4, Bu, {"user_id": C})
r = mrow(M4)
chk("다시 C 로(양식·목록 확인용)", st == 200 and r["author_id"] == C)
d = page("app_new", "/meetings/%d/doc" % M4, A)
cn, ct = name_of("app_new", C), team_name_of("app_new", C)
m_ = re.search(r"부서/작성자</i></th><td class=\"v\">(.*?)</td>", d, re.S)
line = (m_.group(1) if m_ else "").strip()
chk("양식 「부서/작성자」 = C 의 부서 / 이름", bool(m_) and cn in line and (ct in line if ct else True), line[:80])
lst = page("app_new", "/meetings", A)
chk("목록 ✍ = 작성자 C", ("✍ " + cn) in lst)
st, body = req("app_new", "GET", "/api/meetings/search?q=" + urllib.request.quote(cn), A)
chk("찾기: 작성자 이름으로 M4", st == 200 and ('"id": %d' % M4 in body or '"id":%d' % M4 in body), body[:80])
h = page("app_new", "/meetings/%d" % M4, A)
chk("삭제 단추: 만든 A 있음", 'id="btnDelete"' in h)
h = page("app_new", "/meetings/%d" % M4, C)
chk("삭제 단추: 작성자 C(임원·만든 사람 아님) 없음 — 권한은 그대로", 'id="btnDelete"' not in h and 'id="authorDisp"' in h)
st, body = req("app_base", "POST", "/api/meeting/%d/author" % SEED["app_base"]["ids"]["M1"], SEED["app_base"]["me"], {"user_id": 1})
chk("바탕엔 작성자 API 없음(404/405)", st in (404, 405), str(st))

print("== ④ 화면(브라우저) ==")
from playwright.sync_api import sync_playwright   # noqa: E402

qx("app_new", "UPDATE users SET lang='vi' WHERE id=?", (A,))
with sync_playwright() as p:
    br = p.chromium.launch()
    base = "http://127.0.0.1:%d" % PORTS["app_new"]
    for w, who, shot in ((390, Bu, "author_390.png"), (904, Bu, "author_904.png")):
        ctx = br.new_context(viewport={"width": w, "height": 900}, device_scale_factor=2, is_mobile=(w < 800), has_touch=(w < 800))
        ctx.add_cookies([{"name": "tuser", "value": str(who), "url": base}])
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("%s/meetings/%d" % (base, M4), wait_until="networkidle")
        pg.add_style_tag(content="#worksInstallHint{display:none!important}")
        pg.wait_for_timeout(300)
        over = pg.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
        chk("폭 %d: 콘솔 오류 0 · 가로 넘침 없음" % w, not errs and not over, str(errs[:2]))
        pg.locator("#fldAuthor").scroll_into_view_if_needed()
        pg.locator("#btnAuthor").click()
        pg.wait_for_timeout(700)
        vis = pg.evaluate("() => { const p = document.getElementById('authorPick'); return p && !p.hidden && p.offsetParent !== null; }")
        n_opt = pg.locator(".mf-author-opt").count()
        chk("폭 %d: ✏ 누르면 고르기 열림 · 후보 있음" % w, vis and n_opt >= 2, "후보 %d" % n_opt)
        pg.locator("#fldAuthor").screenshot(path=os.path.join(SHOTS, shot))
        if w == 904:
            before = pg.locator("#authorDisp").inner_text()
            pg.locator("#authorQ").fill(name_of("app_new", D)[:1])
            pg.wait_for_timeout(600)
            target = pg.locator(".mf-author-opt[data-id='%d']" % D)
            chk("이름으로 찾기 → 관리자 D 후보 보임", target.count() == 1)
            target.first.click()
            pg.wait_for_timeout(800)
            after = pg.locator("#authorDisp").inner_text()
            stt = pg.locator("#saveStatus").inner_text()
            chk("후보 눌러 바꾸면 글자 바뀜 · 알림 「작성자를 바꿨습니다」", after != before and name_of("app_new", D) in after and "작성자" in stt, "%s → %s · %s" % (before[:20], after[:20], stt))
            chk("DB 도 D · 손으로 정함 = B", mrow(M4)["author_id"] == D and mrow(M4)["author_set_by"] == Bu)
        ctx.close()
    ctx = br.new_context(viewport={"width": 904, "height": 900})
    ctx.add_cookies([{"name": "tuser", "value": str(A), "url": base}])
    pg = ctx.new_page()
    pg.goto("%s/meetings/%d" % (base, M4), wait_until="networkidle")
    chk("베트남어 사용자(A): 「Người lập」 라벨", "Người lập" in pg.content())
    ctx.close()
    br.close()

for pr in PRS.values():
    try:
        pr.terminate()
    except Exception:
        pass
print("q97 %d/%d" % (OK, N), "· 실패:" if FAILS else "", FAILS if FAILS else "")
print("결과: 통과 %d · 실패 %d" % (OK, N - OK))   # 회귀 판정기(res)가 읽는 요약 줄 형식(z1196 q96 과 같게)
sys.exit(0 if OK == N else 1)
