# -*- coding: utf-8 -*-
"""z1199 검사 — 회의록 베트남어 번역 보기(A안 · 베트남어 참석자 있으면 정리 직후 · 정리·결정·할 일·제목 + 양식·한눈에 보기).
   운영 그대로(app_base)와 새것(app_new) 두 서버 · 진짜 브라우저 · 번역은 가짜(지어낸 표 trfix_q99.json · 없는 글은 줄마다 「VI·」).

재는 것
  ① 파일: 바뀐 것 8(main·i18n·화면 4·새 모듈·새 마이그레이션) · 마이그레이션 표 2 · 다시 돌려도 더하는 것 0
  ② 한국어 사용자: 상세·목록·양식·한눈에 보기 = 운영 그대로와 같은 HTML(스크립트·스타일 뺀) · 양식·그림 화면의 말 사전(DL·VL)이 옛 글자 그대로
  ③ 언제 번역하나: 정리 고치기 → 뒤에서 번역(조각 = 제목·정리·결정·할 일·그림) · 고친 조각만 다시 · 결정 더하기 = 그 결정만 ·
     할 일 지우기 = 그 번역도 치움 · 베트남어 참석자 없는 회의록 = 번역 안 부름 · 옛 회의록 = 베트남어 직원이 열 때
  ④ 품질·비용 지킴: 숫자 어긋난 번역 = 저장 안 함(실패 표시) · 다시 열어도 다시 안 부름 · 연결 실패 뒤 10분은 열기로 안 부름
  ⑤ 화면(베트남어 사용자): 상세 A안(안내 줄 · 베트남어 정리·결정·할 일 · 제목 번역 · 원문 보기·되돌리기 · 복사는 베트남어) ·
     번역 중 → 끝나면 저절로 바뀜 · 목록 제목 번역 · 양식(베트남어 칸 이름 · 번역 내용 · [Quyết định] · 원문 보기) · 한눈에 보기(번역 · 원문)
  ⑥ 권한: 볼 수 없는 회의록의 번역 API 403 · 로그에 회의 글 없음 · 콘솔 오류 0
  ⑦ 사진: shots/
쓰는 법: py -3.12 q99_check.py <app_base·app_new 가 있는 폴더>   판정: 종료코드(0=통과) + 「결과: 통과 N · 실패 M」."""
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
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1] if len(sys.argv) > 1 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
RUN = os.path.join(HERE, "run_q99_app.py")
TRFIX = os.path.join(HERE, "trfix_q99.json")
FIX = json.load(io.open(TRFIX, encoding="utf-8"))
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
PORTS = {"app_base": 8977, "app_new": 8978}
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
    lp = os.path.join(APPDIR, "srv99_%d.log" % port)
    env = dict(os.environ, Q99_TRFIX=TRFIX)
    pr = subprocess.Popen([P313, RUN, os.path.join(APPDIR, app), str(port)], stdout=io.open(lp, "w", encoding="utf-8"),
                          stderr=subprocess.STDOUT, cwd=APPDIR, env=env)
    for _ in range(90):
        time.sleep(1)
        txt = io.open(lp, encoding="utf-8", errors="replace").read() if os.path.exists(lp) else ""
        for ln in txt.splitlines():
            if ln.startswith("READY"):
                return pr, json.loads(ln.split(" ", 2)[2]), lp
        if pr.poll() is not None:
            break
    print("⛔ %s 서버가 안 떴다" % app)
    print(io.open(lp, encoding="utf-8", errors="replace").read()[-1500:])
    sys.exit(2)


def dbp(app):
    return os.path.join(APPDIR, app, "data", "knk.db")


def db(app):
    c = sqlite3.connect(dbp(app), timeout=10)
    c.row_factory = sqlite3.Row
    return c


def req(app, method, path, uid, body=None):
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (PORTS[app], path), method=method,
                               data=(json.dumps(body).encode("utf-8") if body is not None else None))
    r.add_header("Cookie", "tuser=%s" % uid)
    if body is not None:
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def calls():
    return json.loads(req("app_new", "GET", "/__test/calls", 1)[1]).get("tr", [])


def flag(name, val):
    req("app_new", "POST", "/__test/flag/%s/%s" % (name, val), 1)


def rows(app, mid):
    c = db(app)
    out = {r["part"]: dict(r) for r in c.execute("SELECT part, src_sig, text, fail FROM content_tr WHERE kind='mtg' AND ref_id=?", (mid,))}
    c.close()
    return out


def wait_rows(mid, cond, secs=20):
    t0 = time.time()
    while time.time() - t0 < secs:
        r = rows("app_new", mid)
        if cond(r):
            return r
        time.sleep(0.4)
    return rows("app_new", mid)


def wait_idle(secs=20):
    """번역 일꾼이 끝날 때까지(부름 수가 3번 연속 그대로)"""
    last, same, t0 = -1, 0, time.time()
    while time.time() - t0 < secs:
        n = len(calls())
        same = same + 1 if n == last else 0
        last = n
        if same >= 4:
            return
        time.sleep(0.5)


def walk(app):
    root = os.path.join(APPDIR, app, "app")
    out = {}
    for d, _ds, fs in os.walk(root):
        if "__pycache__" in d:
            continue
        for f in fs:
            if f.endswith((".pyc", ".bak_z1199")):
                continue
            full = os.path.join(d, f)
            out[os.path.relpath(full, root).replace("\\", "/")] = hashlib.md5(io.open(full, "rb").read()).hexdigest()
    return out


def strip_html(h):
    h = re.sub(r"<script\b.*?</script>", "", h, flags=re.S)
    h = re.sub(r"<style\b.*?</style>", "", h, flags=re.S)
    h = re.sub(r"\d{2}:\d{2}:\d{2}", "T", h)
    h = re.sub(r"\?v=t\d+", "?v=t", h)   # 정적 파일 주소에 붙는 서버 기동 시각
    return re.sub(r"\s+", " ", h).strip()


print("== ① 파일 ==")
WB, WN = walk("app_base"), walk("app_new")
changed = sorted(k for k in set(WB) | set(WN) if WB.get(k) != WN.get(k))
chk("바뀐 파일 8", changed == ["content_tr.py", "i18n.py", "main.py", "migrations/m_z1199_content_tr.py", "templates/meeting_doc.html",
                             "templates/meeting_form.html", "templates/meeting_viz.html", "templates/meetings.html"], str(changed))

print("== 서버 두 벌 ==")
PRS, SEED, LOG = {}, {}, {}
for app in ("app_base", "app_new"):
    PRS[app], SEED[app], LOG[app] = start(app)
ME = SEED["app_new"]["me"]
M1, M2, M3 = SEED["app_new"]["ids"]["M1"], SEED["app_new"]["ids"]["M2"], SEED["app_new"]["ids"]["M3"]
cn = db("app_new")
chk("새 DB 에 번역 표 2", {"content_tr", "content_tr_log"} <= {r[0] for r in cn.execute("SELECT name FROM sqlite_master WHERE type='table'")})
cn.close()
spec = importlib.util.spec_from_file_location("m99", os.path.join(APPDIR, "app_new", "app", "migrations", "m_z1199_content_tr.py"))
m99 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m99)
chk("다시 돌려도 더하는 것 0", m99.migrate(dbp("app_new")) == {"added": []})

#  두 DB 같은 준비: 베트남어 직원(같은 팀 첫 직원) · M1 = 지어낸 회의(정리·결정·할 일·그림 · 베트남어 참석자) · M4 = 옛 회의(번역 없음)
KO = [k for k in FIX if k.startswith("## 핵심\n베트남 공장")][0]
VIZ = {"kind": "internal", "headline": "2호기 반입은 다음 주 화요일 9시로 확정 · 시운전 3일", "headline_q": "",
       "numbers": [{"v": "3톤", "label": "현지 지게차", "q": ""}, {"v": "2명", "label": "추가 시운전 인원", "q": ""}],
       "flow": {"zones": [], "loop": {"label": "", "from": "", "to": ""}},
       "decided": [{"t": "[결정] 반입은 다음 주 화요일 오전 9시", "q": ""}], "open": [{"t": "[확인 필요] 공장 전원 용량(380V · 60A)", "q": ""}],
       "todo": [{"t": "3톤 지게차 1대 추가 임차", "who": "김직원", "due": "2026-10-31", "q": ""}],
       "timeline": [{"when": "다음 주 화", "t": "설비 반입", "sure": True, "q": ""}, {"when": "반입 다음 날", "t": "시운전 시작(3일)", "sure": False, "q": ""}],
       "parts": []}
IDS = {}
for app in ("app_base", "app_new"):
    c = db(app)
    team = c.execute("SELECT team_id FROM meetings WHERE id=?", (M1,)).fetchone()[0]
    vi = c.execute("SELECT id FROM users WHERE role='member' AND team_id=? AND is_active=1 ORDER BY id", (team,)).fetchone()[0]
    c.execute("UPDATE users SET lang='vi' WHERE id=?", (vi,))
    vcols = {r[1] for r in c.execute("PRAGMA table_info(meetings)")}
    c.execute("UPDATE meetings SET title=?, summary=?, visibility='team' WHERE id=?", ("2호기 설비 반입·시운전 일정 회의", "임시 정리", M1))
    if "viz_json" in vcols:
        c.execute("UPDATE meetings SET viz_json=?, viz_at=datetime('now','localtime') WHERE id=?", (json.dumps(VIZ, ensure_ascii=False), M1))
    c.execute("DELETE FROM meeting_decisions WHERE meeting_id=?", (M1,))
    c.execute("DELETE FROM meeting_actions WHERE meeting_id=?", (M1,))
    for w in ("반입은 다음 주 화요일 오전 9시로 한다", "현지 시운전 인원 2명을 더 배치한다"):
        c.execute("INSERT INTO meeting_decisions(meeting_id, who, what, due, source) VALUES(?,?,?,?,'ai')", (M1, "", w, ""))
    for t in ("3톤 지게차 1대 추가 임차", "공장 전원 용량(380V · 60A) 확인 후 회신", "반입 일정 확정 내용을 협력사에 공유"):
        c.execute("INSERT INTO meeting_actions(meeting_id, assignee_name, task, due_date, source) VALUES(?,?,?,?,'ai')", (M1, "", t, ""))
    nm = c.execute("SELECT name FROM users WHERE id=?", (vi,)).fetchone()[0]
    c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,?)", (M1, vi, nm))
    c.execute("UPDATE meetings SET summary=?, visibility='team', team_id=? WHERE id=?", ("## 핵심\n베트남어 참석자 없는 회의.", team, M3))
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    m4 = c.execute("INSERT INTO meetings(title, meeting_date, owner_id, team_id, location, body, summary, visibility, status, created_at, updated_at) "
                   "VALUES(?,?,?,?,?,?,?,?,?,?,?)", ("옛 회의 정리 시험", now[:10], ME, team, "", "지어낸 옛 회의 원문", "## 핵심\n지난달 회의 정리입니다.",
                                                    "team", "done", now, now)).lastrowid
    c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,?)", (m4, vi, nm))
    m5 = c.execute("INSERT INTO meetings(title, meeting_date, owner_id, team_id, location, body, summary, visibility, status, created_at, updated_at) "
                   "VALUES(?,?,?,?,?,?,?,?,?,?,?)", ("대표 비공개 시험", now[:10], ME, team, "", "", "## 핵심\n비공개.", "private", "done", now, now)).lastrowid
    c.commit()
    c.close()
    IDS[app] = {"vi": vi, "M4": m4, "M5": m5}
VI, M4 = IDS["app_new"]["vi"], IDS["app_new"]["M4"]
print("  베트남어 직원 %d · M1 %d · M3 %d · M4 %d" % (VI, M1, M3, M4))

print("== ③ 언제 번역하나 ==")
chk("준비만 했을 땐 번역 0(DB 로 바꾼 것은 고리 없음)", rows("app_new", M1) == {} and calls() == [])
st, b = req("app_new", "POST", "/api/meeting/%d/summary" % M1, ME, {"summary": KO})
r = wait_rows(M1, lambda r: len(r) >= 8)
chk("정리 고침 200 → 뒤에서 번역: 제목·정리·결정 2·할 일 3·그림 = 8조각 모두 저장", st == 200 and len(r) == 8 and all(x["text"] and not x["fail"] for x in r.values()),
    "%s %s" % (st, sorted(r)))
wait_idle()
c1 = calls()
chk("번역 부름 1번(조각 7 + 그림 글 칸 한 묶음)", len(c1) == 1 and c1[0]["n"] >= 8, str([x["n"] for x in c1]))
chk("정리 번역 = 지어낸 표 그대로", r.get("summary", {}).get("text") == FIX[KO])
vz = json.loads(r.get("viz", {}).get("text") or "{}")
chk("그림 번역: 머리글·숫자 칸 옮김 · 이름·기한·원문 근거·종류는 그대로",
    vz.get("headline") == FIX[VIZ["headline"]] and vz["numbers"][0]["v"] == "3 tấn" and vz["todo"][0]["who"] == "김직원"
    and vz["todo"][0]["due"] == "2026-10-31" and vz.get("kind") == "internal", (vz.get("headline") or "")[:40])
st, b = req("app_new", "POST", "/api/meeting/%d/summary" % M1, ME, {"summary": KO + "\n- 추가 메모 1건"})
wait_rows(M1, lambda r: r.get("summary", {}).get("text", "").endswith("VI·추가 메모 1건"))
wait_idle()
c2 = calls()
chk("정리만 다시 고침 → 정리 조각만 다시 번역", len(c2) == 2 and c2[-1]["keys"] == ["summary"], str(c2[-1]["keys"] if c2 else ""))
st, b = req("app_new", "POST", "/api/meeting/%d/decision" % M1, ME, {"what": "출하 전 점검표 공유", "who": "", "due": ""})
did = json.loads(b).get("id") if st == 200 else 0
wait_rows(M1, lambda r: ("dec:%d" % did) in r)
wait_idle()
c3 = calls()
chk("결정 더하기 → 그 결정만 번역", st == 200 and c3[-1]["keys"] == ["dec:%d" % did], str(c3[-1]["keys"]))
cx = db("app_new")
aid = cx.execute("SELECT id FROM meeting_actions WHERE meeting_id=? ORDER BY id DESC LIMIT 1", (M1,)).fetchone()[0]
cx.close()
st, b = req("app_new", "DELETE", "/api/meeting/%d/action/%d" % (M1, aid), ME)
time.sleep(1.0)
chk("할 일 지우기 → 그 번역도 치움 · 새 부름 없음", st == 200 and ("act:%d" % aid) not in rows("app_new", M1) and len(calls()) == len(c3), str(st))
n0 = len(calls())
st, b = req("app_new", "POST", "/api/meeting/%d/summary" % M3, ME, {"summary": "## 핵심\n베트남어 참석자 없는 회의 — 고침."})
time.sleep(2.0)
chk("베트남어 참석자 없는 회의록 = 번역 안 부름", st == 200 and rows("app_new", M3) == {} and len(calls()) == n0)

print("== ④ 품질·비용 지킴 ==")
flag("tr_bad", 1)
st, b = req("app_new", "POST", "/api/meeting/%d/summary" % M1, ME, {"summary": KO + "\n- 고친 메모 2건"})
r = wait_rows(M1, lambda r: (r.get("summary") or {}).get("fail"))
wait_idle()
chk("숫자 어긋난 번역 = 저장 안 함(실패 표시 · 글 비움) · 다시 묻기 1번", (r.get("summary") or {}).get("fail", "").startswith("nums") and not (r.get("summary") or {}).get("text")
    and calls()[-1]["retry"] is True, str((r.get("summary") or {}).get("fail")))
flag("tr_bad", 0)
n1 = len(calls())
for _ in range(2):
    req("app_new", "GET", "/meetings/%d" % M1, VI)
time.sleep(1.5)
chk("실패한 조각은 베트남어 직원이 다시 열어도 다시 안 부름(비용 고리 없음)", len(calls()) == n1, "%d → %d" % (n1, len(calls())))
st, b = req("app_new", "GET", "/api/meeting/%d/tr" % M1, VI)
j = json.loads(b).get("tr") or {}
chk("번역 API: 실패한 정리 = 빈 글 · failed 1 · 결정은 그대로", st == 200 and j.get("summary") == "" and j.get("failed") == 1 and len(j.get("decisions") or {}) == 3, str({k: j.get(k) for k in ("state", "failed")}))
flag("tr_fail", 1)
st, b = req("app_new", "POST", "/api/meeting/%d/summary" % M1, ME, {"summary": KO + "\n- 연결 실패 시험"})
time.sleep(2.5)
wait_idle()
cx = db("app_new")
er = cx.execute("SELECT error FROM content_tr_log WHERE ref_id=? ORDER BY id DESC LIMIT 1", (M1,)).fetchone()
cx.close()
chk("연결 실패 = 기록(오류 이름만) · 저장 없음", er is not None and er[0] == "TrError", str(er[0] if er else None))
n2 = len(calls())
req("app_new", "GET", "/meetings/%d" % M1, VI)
time.sleep(1.5)
chk("연결 실패 뒤 10분은 열기로 다시 안 부름", len(calls()) == n2, "%d → %d" % (n2, len(calls())))
flag("tr_fail", 0)
st, b = req("app_new", "POST", "/api/meeting/%d/summary" % M1, ME, {"summary": KO})
wait_rows(M1, lambda r: (r.get("summary") or {}).get("text") == FIX[KO])
wait_idle()

print("== ③-2 옛 회의록 = 베트남어 직원이 열 때 ==")
chk("옛 회의록(M4)은 아직 번역 없음", rows("app_new", M4) == {})
st, h = req("app_new", "GET", "/meetings/%d" % M4, VI)
r4 = wait_rows(M4, lambda r: len(r) >= 2)
chk("베트남어 직원이 열면 번역 시작 → 제목·정리 저장", st == 200 and (r4.get("summary") or {}).get("text") == FIX["## 핵심\n지난달 회의 정리입니다."], str(sorted(r4)))
wait_idle()
st, b = req("app_new", "GET", "/api/meeting/%d/tr" % M4, VI)
chk("번역 API: done · 제목 번역", st == 200 and (json.loads(b).get("tr") or {}).get("state") == "done" and (json.loads(b)["tr"]["title"] == FIX["옛 회의 정리 시험"]))
n3 = len(calls())
req("app_new", "GET", "/meetings/%d" % M1, ME)
req("app_new", "GET", "/meetings/%d/doc" % M1, ME)
time.sleep(1)
chk("한국어 사용자가 열면 번역을 부르지 않음", len(calls()) == n3)

print("== ⑥ 권한·기록 ==")
st, b = req("app_new", "GET", "/api/meeting/%d/tr" % IDS["app_new"]["M5"], VI)
chk("볼 수 없는 회의록(남의 비공개)의 번역 API 403", st == 403, str(st))
st, b = req("app_new", "GET", "/api/meeting/%d/tr" % M1, ME)
chk("한국어 사용자에게 번역 API = tr null", st == 200 and json.loads(b).get("tr") is None)
logt = io.open(LOG["app_new"], encoding="utf-8", errors="replace").read()
trl = [ln for ln in logt.splitlines() if "[TR-Z1199]" in ln]
chk("로그에 회의 글 없음(지게차·반입·시운전·Xe nâng 0)", trl and not any(w in ln for ln in trl for w in ("지게차", "반입", "시운전", "Xe nâng", "Trọng tâm")), "로그 %d줄" % len(trl))

print("== ② 한국어 사용자 화면 = 운영 그대로 ==")
#  비교 전에 운영 그대로(app_base) DB 를 새것과 같은 회의 내용으로 맞춘다(새것에만 API 로 고친 것이 있다)
cs, cb = db("app_new"), db("app_base")
for mid in (M1, M3, M4):
    mr = cs.execute("SELECT title, summary FROM meetings WHERE id=?", (mid,)).fetchone()
    cb.execute("UPDATE meetings SET title=?, summary=? WHERE id=?", (mr["title"], mr["summary"], mid))
    for tb, cols in (("meeting_decisions", "id, meeting_id, who, what, due, source"), ("meeting_actions", "id, meeting_id, assignee_name, task, due_date, source")):
        cb.execute("DELETE FROM %s WHERE meeting_id=?" % tb, (mid,))
        for r in cs.execute("SELECT %s FROM %s WHERE meeting_id=? ORDER BY id" % (cols, tb), (mid,)):
            cb.execute("INSERT INTO %s(%s) VALUES(%s)" % (tb, cols, ",".join("?" * len(r))), tuple(r))
cb.commit()
cb.close()
cs.close()
for path, name in (("/meetings/%d" % M1, "상세"), ("/meetings", "목록"), ("/meetings/%d/doc" % M1, "양식"), ("/meetings/%d/viz" % M1, "한눈에 보기")):
    sb, hb = req("app_base", "GET", path, SEED["app_base"]["me"])
    sn, hn = req("app_new", "GET", path, ME)
    a, z = strip_html(hb), strip_html(hn)
    if a != z:
        i = next((k for k in range(min(len(a), len(z))) if a[k] != z[k]), min(len(a), len(z)))
        extra = "다른 곳: …%s… / …%s…" % (a[max(0, i - 40):i + 60], z[max(0, i - 40):i + 60])
    else:
        extra = ""
    chk("한국어 사용자 %s HTML 같음(스크립트·스타일 뺌)" % name, sb == sn == 200 and a == z, extra[:300])
sb, hb = req("app_base", "GET", "/meetings/%d/doc" % M1, SEED["app_base"]["me"])
sn, hn = req("app_new", "GET", "/meetings/%d/doc" % M1, ME)
dl = json.loads(re.search(r"var DL = (\{.*?\});", hn).group(1))
chk("양식 말 사전(DL) = 옛 글자 그대로(한국어)", all((v in hb) for v in dl.values() if v.strip()), str([k for k, v in dl.items() if v.strip() and v not in hb]))
sb, hb = req("app_base", "GET", "/meetings/%d/viz" % M1, SEED["app_base"]["me"])
sn, hn = req("app_new", "GET", "/meetings/%d/viz" % M1, ME)
vl = json.loads(re.search(r"var VL = (\{.*?\});", hn).group(1))
miss = [k for k, v in vl.items() if isinstance(v, str) and k not in ("min",) and v.strip() and v not in hb.replace("\\u", "")]
chk("한눈에 보기 말 사전(VL) = 옛 글자 그대로(한국어 · 요일·분 빼고)", not miss and vl.get("tags") is None, str(miss))

print("== ⑤ 화면(베트남어 사용자) ==")
from playwright.sync_api import sync_playwright   # noqa: E402

HIDE = "#worksInstallHint{display:none!important}"
with sync_playwright() as p:
    br = p.chromium.launch()
    base = "http://127.0.0.1:%d" % PORTS["app_new"]

    def page(uid, path, w=390):
        ctx = br.new_context(viewport={"width": w, "height": 900}, device_scale_factor=2, is_mobile=(w < 800), has_touch=(w < 800))
        ctx.add_cookies([{"name": "tuser", "value": str(uid), "url": base}])
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + path, wait_until="networkidle")
        pg.add_style_tag(content=HIDE)
        pg.wait_for_timeout(400)
        return ctx, pg, errs

    def shot(pg, sel, name):
        pg.evaluate("() => document.querySelectorAll('body *').forEach(el => { const cs = getComputedStyle(el); "
                    "if ((cs.position === 'fixed' || cs.position === 'sticky') && el.getBoundingClientRect().top < 140 && el.offsetHeight < 220) el.style.visibility = 'hidden'; })")
        loc = pg.locator(sel).first
        loc.scroll_into_view_if_needed()
        pg.wait_for_timeout(200)
        loc.screenshot(path=os.path.join(SHOTS, name))

    ctx, pg, errs = page(VI, "/meetings/%d" % M1)
    sm = pg.locator("#mtgSummary").inner_text()
    chk("상세: 안내 줄(Bản dịch tự động) · 베트남어 정리 · 콘솔 오류 0", "Bản dịch tự động" in sm and "Trọng tâm" in sm and "[Quyết định]" in sm and not errs, str(errs[:2]))
    dec1 = pg.locator("#decList .ri-main b").first.inner_text()
    chk("상세: 결정 베트남어 · 제목 번역 줄", dec1.startswith("Đưa thiết bị vào lúc 9 giờ") and pg.locator("#viTitleHint").inner_text().endswith(FIX["2호기 설비 반입·시운전 일정 회의"]), dec1[:40])
    shot(pg, "#secSummary", "vi_A_정리.png")
    shot(pg, "#secDecisions", "vi_A_결정.png")
    pg.evaluate("() => { window.__copied = ''; navigator.clipboard.writeText = function(t){ window.__copied = t; return Promise.resolve(); }; }")
    pg.locator("#btnCopySum").click()
    pg.wait_for_timeout(400)
    cp = pg.evaluate("() => window.__copied")
    chk("복사 = 보이는 말(베트남어 제목·정리)", "Trọng tâm" in cp and FIX["2호기 설비 반입·시운전 일정 회의"] in cp and "핵심" not in cp, cp[:60])
    pg.locator("[data-vs='ko']").first.click()
    pg.wait_for_timeout(300)
    sm2 = pg.locator("#mtgSummary").inner_text()
    chk("원문 보기 → 한국어 정리 · 결정 한국어 · 제목 번역 숨김", "핵심" in sm2 and "Bản gốc tiếng Hàn" in sm2 and pg.locator("#decList .ri-main b").first.inner_text().startswith("반입은")
        and pg.locator("#viTitleHint").is_hidden())
    shot(pg, "#secSummary", "vi_A_원문.png")
    pg.locator("[data-vs='vi']").first.click()
    pg.wait_for_timeout(300)
    chk("다시 베트남어로", "Trọng tâm" in pg.locator("#mtgSummary").inner_text())
    ctx.close()
    #  번역 중 → 끝나면 저절로
    flag("tr_slow", 5)
    req("app_new", "POST", "/api/meeting/%d/summary" % M1, ME, {"summary": KO + "\n- 늦은 번역 시험"})
    ctx, pg, errs = page(VI, "/meetings/%d" % M1)
    s0 = pg.locator("#mtgSummary").inner_text()
    ok_run = "Đang dịch" in s0
    t0 = time.time()
    done = False
    while time.time() - t0 < 25:
        if "VI·늦은 번역 시험" in pg.locator("#mtgSummary").inner_text():
            done = True
            break
        pg.wait_for_timeout(700)
    chk("번역 중 = 「Đang dịch」 → 끝나면 새로 고치지 않아도 베트남어로", ok_run and done and not errs, "running=%s done=%s %.0f초" % (ok_run, done, time.time() - t0))
    ctx.close()
    flag("tr_slow", 0)
    wait_idle()
    req("app_new", "POST", "/api/meeting/%d/summary" % M1, ME, {"summary": KO})
    wait_rows(M1, lambda r: (r.get("summary") or {}).get("text") == FIX[KO])
    wait_idle()
    #  목록
    ctx, pg, errs = page(VI, "/meetings")
    tv = pg.locator(".mtg-ttl-vi").all_inner_texts()
    chk("목록: 베트남어 직원 = 제목 번역 줄(번역된 회의록만)", any(FIX["2호기 설비 반입·시운전 일정 회의"] in t for t in tv) and not errs, str(len(tv)))
    shot(pg, ".mtg-row", "vi_목록.png")
    ctx.close()
    ctx, pg, errs = page(ME, "/meetings")
    chk("목록: 한국어 사용자 = 제목 번역 없음", pg.locator(".mtg-ttl-vi").count() == 0)
    ctx.close()
    #  양식
    ctx, pg, errs = page(VI, "/meetings/%d/doc" % M1, w=900)
    tx = pg.locator("body").inner_text()
    chk("양식: 베트남어 칸 이름 · 번역 정리 · [Quyết định] · 결정 번역 · 원문 보기 단추", "Tên cuộc họp" in tx and "Trọng tâm" in tx and "[Quyết định]" in tx
        and "Đưa thiết bị vào lúc 9 giờ sáng thứ Ba tuần sau" in tx and "Xem bản gốc tiếng Hàn" in tx and "회의명" not in tx and not errs, str(errs[:2]))
    pg.screenshot(path=os.path.join(SHOTS, "vi_양식.png"), full_page=True)
    pg.locator("a[href$='/doc?orig=1']").first.click()
    pg.wait_for_load_state("networkidle")
    tx2 = pg.locator("body").inner_text()
    chk("양식 원문 보기 = 한국어 칸 이름·정리 · 「Xem tiếng Việt」로 돌아가기", "회의명" in tx2 and "핵심" in tx2 and "Xem tiếng Việt" in tx2)
    ctx.close()
    #  한눈에 보기
    ctx, pg, errs = page(VI, "/meetings/%d/viz" % M1)
    tv = pg.locator("body").inner_text()
    chk("한눈에 보기: 베트남어 머리글·칸 이름(Đã quyết định) · [Quyết định] · 원문 보기 단추",
        FIX[VIZ["headline"]] in tv and "Đã quyết định" in tv and "[Quyết định]" in tv and "Xem bản gốc tiếng Hàn" in tv
        and FIX["2호기 설비 반입·시운전 일정 회의"] in tv and not errs, str(errs[:2]))
    pg.screenshot(path=os.path.join(SHOTS, "vi_한눈에보기.png"), full_page=True)
    ctx.close()
    ctx, pg, errs = page(VI, "/meetings/%d/viz?orig=1" % M1)
    chk("한눈에 보기 원문 = 한국어 머리글", VIZ["headline"] in pg.locator("body").inner_text() and not errs)
    ctx.close()
    br.close()

for pr in PRS.values():
    try:
        pr.terminate()
    except Exception:
        pass
print("q99 %d/%d" % (OK, N), "· 실패:" if FAILS else "", FAILS if FAILS else "")
print("결과: 통과 %d · 실패 %d" % (OK, N - OK))
sys.exit(0 if OK == N else 1)
