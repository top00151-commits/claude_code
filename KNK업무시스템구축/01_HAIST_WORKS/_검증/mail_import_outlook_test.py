# -*- coding: utf-8 -*-
"""아웃룩 옛 메일 가져오기 시험 — 가짜 메일·임시 DB(운영 무접촉 · 실제 메일 없음).
대표 11-25 「기간 5·3·2·1년 · 첨부도 같은 기간 · 폴더: 아웃룩 폴더 / 자동 분류 / 직접(전 직원) · 내 것만 같은 이름 폴더만」
사용: py -3.13 _검증/mail_import_outlook_test.py"""
import base64
import datetime as dt
import io
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_mimp_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_folders as mf
    from app import mail_import_outlook as mio
finally:
    sys.stdout = _so
from starlette.testclient import TestClient  # noqa: E402

P = F = 0


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:500])


OWN, STF, OTH = 9500, 9501, 9502
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id='kjr'")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9500,'kjr','가짜대표','ceo',1,'x')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9501,'t9501','가짜직원','member',1,'x')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9502,'t9502','남직원','member',1,'x')")
    c.execute("INSERT INTO teams(id, code, name, display_order) VALUES(991,'01','시험기술영업팀',1)")

_U = {"id": STF, "role": "member"}
m.get_user = lambda req: dict(_U, name="가짜", team_id=None, team_name="")
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
_ndisk = {"ok": True}
_real_disk = mio.disk_state
mio.disk_state = lambda path=None: {"free": 50 * 1024 ** 3 if _ndisk["ok"] else 1024 ** 3, "total": 100 * 1024 ** 3, "ok": _ndisk["ok"]}

NOW = dt.datetime.now()


def ts(days):
    return (NOW - dt.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def mail(mid, days=10, path="\\\\a@fake.example\\받은 편지함", atts=None, subj="가짜 제목 비밀", frm="sender@fake.example", **kw):
    d = {"message_id": mid, "received_at": ts(days), "sent_at": ts(days), "from_email": frm, "from_name": "가짜 보낸이",
         "to": "me@knknara.co.kr", "cc": "", "subject": subj, "html": "<p>가짜 본문</p>", "text": "가짜 본문",
         "folder_path": path, "attachments": atts or [], "att_dropped": 0}
    d.update(kw)
    return d


def post(code, d):
    return k.post("/api/mail/import-outlook/mail", json={"code": code, "mail": d})


def mk(years=2, mode="outlook"):
    j = k.post("/mail/import-outlook/token", data={"years": str(years), "mode": mode}).json()
    return j


def row(mid_hash_id):
    with _db.db_session() as c:
        r = c.execute("SELECT * FROM mail_messages WHERE id=?", (mid_hash_id,)).fetchone()
        return dict(r) if r else None


def last_mail(uid):
    with _db.db_session() as c:
        r = c.execute("SELECT * FROM mail_messages WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)).fetchone()
        return dict(r) if r else None


print("== 1. 화면 · 폴더 방식(직원 3가지 · 대표 = 같은 이름 폴더만) ==")
h = k.get("/mail/import-outlook").text
check("직원 화면 200 · 기간 5·3·2·1년", all(('value="%d"' % y) in h for y in (5, 3, 2, 1)), h[:200])
check("직원 화면 = 폴더 방식 3가지(아웃룩 폴더 그대로 · 자동 분류 · 직접 정리) · 「같은 이름 폴더만」 없음",
      all(('value="%s"' % x) in h for x in ("outlook", "auto", "manual")) and 'value="match"' not in h and "같은 이름 폴더만" not in h)
check("닫기·돌아가기(← 설정·정리) · 결과 문구 규정(✅ 완료 · 👉 남은 일 · ⏳ 진행 중)",
      "/mail/tools" in h and "설정·정리" in h and all(x in h for x in ("완료 — 이 작업은 끝났습니다", "남은 일", "진행 중")))
check("설정·정리 화면에 「📥 아웃룩 옛 메일 가져오기」(직원 누구나)", 'href="/mail/import-outlook"' in k.get("/mail/tools").text)
_U.update(id=OWN, role="ceo")
ho = k.get("/mail/import-outlook").text
check("대표 화면 = 폴더 고르기 없음 · 「같은 이름 폴더」로 정해져 나옴",
      'name="miMode" value="outlook"' not in ho and 'value="auto"' not in ho and "miOwnerMode" in ho and "같은 이름" in ho)
j = mk(2, "outlook")
check("대표가 다른 방식을 보내도 = 같은 이름 폴더만(match)으로 고정", j.get("ok") and j["st"]["mode"] == "match", j)
_U.update(id=STF, role="member")
j = mk(2, "match")
check("직원이 「같은 이름」 방식을 보내면 거절", not j.get("ok"), j)
check("기간이 5·3·2·1 밖이면 거절", not mk(4, "outlook").get("ok"))

print("== 2. 번호(1회용 · 해시만 · 기한) ==")
j = mk(2, "outlook")
code = j.get("code", "")
check("번호 만들기 → 번호·명령 한 줄(이 번호로 명령 파일 받아 바로 실행)",
      j.get("ok") and len(code) >= 10 and code in j["command"] and "/api/mail/import-outlook/script?code=" in j["command"], j)
with _db.db_session() as c:
    trow = dict(c.execute("SELECT * FROM mail_import_tokens WHERE user_id=? ORDER BY id DESC LIMIT 1", (STF,)).fetchone())
check("서버엔 번호 해시만(평문 없음)", code not in str(trow) and len(trow["token_hash"]) == 64, trow)
ck = k.post("/api/mail/import-outlook/check", json={"code": code}).json()
check("check = 기간·방식·공간(숫자만)", ck.get("ok") and ck["years"] == 2 and ck["mode"] == "outlook" and ck["disk_ok"] is True, ck)
check("틀린 번호 = 403", k.post("/api/mail/import-outlook/check", json={"code": "nope-nope-nope"}).status_code == 403)
check("명령 파일: 번호 있으면 받음 · 없으면 403", k.get("/api/mail/import-outlook/script?code=" + code).status_code == 200
      and TestClient(m.app, raise_server_exceptions=False).get("/api/mail/import-outlook/script") .status_code in (200, 403))

print("== 3. 메일 한 통 ==")
r = post(code, mail("<imp1@fake.example>", days=40, atts=[{"name": "가짜.txt", "mime": "text/plain", "b64": base64.b64encode(b"hello").decode(), "content_id": "", "inline": False}]))
jr = r.json()
m1 = last_mail(STF)
check("저장 → saved · 받은 시각 = 아웃룩 받은 시각 · 읽음", jr.get("result") == "saved" and m1 and m1["received_at"][:19] == ts(40)[:19] and m1["is_read"] == 1, (jr, m1 and m1["received_at"]))
check("응답 = 숫자·결과 글자만(제목·주소 없음)", "비밀" not in r.text and "sender@" not in r.text and "fake.example" not in r.text, r.text[:300])
with _db.db_session() as c:
    na = c.execute("SELECT COUNT(*) FROM mail_attachments WHERE mail_id=?", (m1["id"],)).fetchone()[0]
check("첨부 저장", na == 1, na)
r2 = post(code, mail("<imp1@fake.example>", days=40)).json()
with _db.db_session() as c:
    dupc = c.execute("SELECT COALESCE(dup_count,1) FROM mail_messages WHERE id=?", (m1["id"],)).fetchone()[0]
check("같은 메일 다시 = 건너뜀(두 번 안 들어감 · 중복 수도 안 늘림)", r2.get("result") == "skip" and dupc == 1 and last_mail(STF)["id"] == m1["id"], (r2, dupc))
r3 = post(code, mail("<old@fake.example>", days=3 * 365)).json()
check("기간(2년) 밖 = outside(넣지 않음)", r3.get("result") == "outside" and last_mail(STF)["id"] == m1["id"], r3)
big = base64.b64encode(b"x" * (31 * 1024 * 1024)).decode()
r4 = post(code, mail("<big@fake.example>", days=5, atts=[{"name": "큰.bin", "mime": "", "b64": big, "content_id": "", "inline": False}]))
mb = last_mail(STF)
with _db.db_session() as c:
    nb = c.execute("SELECT COUNT(*) FROM mail_attachments WHERE mail_id=?", (mb["id"],)).fetchone()[0]
check("한 통 첨부 30MB 넘음 → 첨부 빼고 본문만 + 「아웃룩에 있습니다」 표시", r4.json().get("result") == "saved" and nb == 0 and "아웃룩에 있습니다" in (mb["body_html"] or ""), (r4.text[:200], nb))
check("요청 하나 45MB 넘으면 413(명령이 첨부 빼고 다시 보냄)",
      k.post("/api/mail/import-outlook/mail", content=b"{" + b" " * (46 * 1024 * 1024) + b"}", headers={"content-type": "application/json"}).status_code == 413)

print("== 4. 알림·자동 응답 안 나감 ==")
cnt = k.get("/api/mail/counts?lite=1").json()
check("새 메일 알림 대상(latest)에 가져온 메일 없음(읽음으로 들어옴)", not cnt.get("latest") or cnt["latest"]["id"] not in (m1["id"], mb["id"]), cnt.get("latest"))
with _db.db_session() as c:
    try:
        nar = c.execute("SELECT COUNT(*) FROM mail_autoreply_log").fetchone()[0]
    except Exception:
        nar = 0
check("자동 응답 기록 없음", nar == 0, nar)

print("== 5. 폴더 방식 ==")
post(code, mail("<p1@fake.example>", path="\\\\a@fake.example\\받은 편지함\\1고객사\\시노펙스"))
p1 = last_mail(STF)
post(code, mail("<p2@fake.example>", path="\\\\a@fake.example\\받은 편지함\\1고객사\\시노펙스"))
p2 = last_mail(STF)
with _db.db_session() as c:
    fl = mf.folders(c, STF)
names = [(f["name"], bool(f["parent_id"])) for f in fl]
check("① 아웃룩 폴더 그대로 = 「1고객사 › 시노펙스」를 만들어 고정 · 두 번째는 같은 폴더(새로 안 만듦)",
      ("1고객사", False) in names and ("시노펙스", True) in names and len([n for n in names if n[0] == "시노펙스"]) == 1
      and p1["fd_pin"] and p1["fd_pin"] == p2["fd_pin"], (names, p1["fd_pin"], p2["fd_pin"]))
post(code, mail("<p3@fake.example>", path="\\\\a@fake.example\\받은 편지함"))
check("① 받은 편지함 바로 아래 메일 = 고정 안 함(자동 분류)", last_mail(STF)["fd_pin"] == "", last_mail(STF)["fd_pin"])
ja = mk(1, "auto"); post(ja["code"], mail("<p4@fake.example>", days=3, path="\\\\a@fake.example\\받은 편지함\\X"))
check("② 자동 분류 = 고정 안 함", last_mail(STF)["fd_pin"] == "")
check("새 번호를 만들면 앞 번호는 끝남", post(code, mail("<p5@fake.example>")).status_code == 403)
jm = mk(1, "manual"); post(jm["code"], mail("<p6@fake.example>", days=3, path="\\\\a@fake.example\\받은 편지함\\X"))
check("③ 직접 정리 = 「분류안됨(gen)」에 고정", last_mail(STF)["fd_pin"] == "gen")

# 대표 = 같은 이름 폴더만
_U.update(id=OWN, role="ceo")
with _db.db_session() as c:
    mf.seed(c, OWN)   # 대표 아웃룩식 폴더(1.고객사 › 시노펙스 …) · 6.케이엔케이(부서)
    g = mf.add_folder(c, OWN, "공통", None, "")
    mf.add_folder(c, OWN, "공통", g, "")
jo = mk(5, "outlook")
oc = jo["code"]
post(oc, mail("<o1@fake.example>", path="\\\\a@fake.example\\받은 편지함\\1고객사\\시노펙스"))
o1 = last_mail(OWN)
with _db.db_session() as c:
    sino = [f for f in mf.folders(c, OWN) if f["name"] == "시노펙스"]
check("대표: 아웃룩 「1고객사\\시노펙스」 = 이음웍스 「1.고객사 › 시노펙스」(이름 하나만 맞음)", len(sino) == 1 and o1["fd_pin"] == "f%d" % sino[0]["id"], (o1["fd_pin"], sino))
post(oc, mail("<o2@fake.example>", path="\\\\a@fake.example\\받은 편지함\\6.케이엔케이\\01_시험기술영업팀"))
check("대표: 부서 폴더 이름이 같으면 부서 폴더(t<id>)", last_mail(OWN)["fd_pin"] == "t991", last_mail(OWN)["fd_pin"])
post(oc, mail("<o3@fake.example>", path="\\\\a@fake.example\\받은 편지함\\공통"))
check("대표: 같은 이름이 둘 이상 = 손대지 않고 「분류안됨」", last_mail(OWN)["fd_pin"] == "gen")
post(oc, mail("<o4@fake.example>", path="\\\\a@fake.example\\받은 편지함\\없는폴더이름"))
with _db.db_session() as c:
    _nf = any(f["name"] == "없는폴더이름" for f in mf.folders(c, OWN))
check("대표: 같은 이름 없음 = 「분류안됨」 · 새 폴더 안 만듦", last_mail(OWN)["fd_pin"] == "gen" and not _nf)
check("남의 번호로 넣어도 그 번호 주인 메일함에만(대표 번호 → 대표 · 직원 메일함 그대로)", last_mail(OWN)["user_id"] == OWN and not any(x for x in [last_mail(OTH)] if x))

print("== 6. 공간 부족 · 멈추기 · 끝 · 기한 ==")
_ndisk["ok"] = False
rd = post(oc, mail("<d1@fake.example>"))
check("서버 남은 공간 모자람 = 받지 않음(disk)", rd.status_code == 507 and rd.json().get("result") == "disk", rd.text[:200])
check("공간 모자라면 번호도 안 만듦", not mk(1, "outlook").get("ok"))
_ndisk["ok"] = True
st = k.post("/api/mail/import-outlook/done", json={"code": oc}).json()
check("끝 알림 → 상태 done", st.get("ok") and st.get("state") == "done", st)
check("끝난 번호로는 더 못 보냄", post(oc, mail("<d2@fake.example>")).status_code == 403)
js = k.get("/mail/import-outlook/status").json()
check("진행 상황 = 숫자(가져옴·건너뜀·실패·첨부MB)", js.get("ok") and js.get("saved") >= 4 and "state" in js, js)
jn = mk(1, "x")
with _db.db_session() as c:
    c.execute("UPDATE mail_import_tokens SET created_at=?, last_at='' WHERE id=(SELECT MAX(id) FROM mail_import_tokens)", (ts(2),))
check("24시간 지난 번호 = 거절", k.post("/api/mail/import-outlook/check", json={"code": jn["code"]}).status_code == 403)
jn2 = mk(1, "x")
k.post("/mail/import-outlook/stop")
check("멈추기 → 번호 끝", k.post("/api/mail/import-outlook/check", json={"code": jn2["code"]}).status_code == 403)

print("== 7. 명령 파일 · 문법 ==")
ps = open(os.path.join(ROOT, "deploy", "outlook_import.ps1"), "rb").read()
check("명령 파일 = UTF-8 BOM · CRLF · && 없음 · 아웃룩 읽기만(지우기·옮기기·보내기 없음)",
      ps.startswith(b"\xef\xbb\xbf") and b"\r\n" in ps and b"&&" not in ps
      and not re.search(rb"\.(Delete|Move|Send|Save)\(\)", ps), "")
try:
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('%s',[ref]$null,[ref]$e);if($e){'ERR'}else{'OK'}"
                          % os.path.join(ROOT, "deploy", "outlook_import.ps1").replace("'", "''")],
                         capture_output=True, timeout=60).stdout.decode("utf-8", "replace")
    check("PowerShell 문법 검사", "OK" in out, out)
    cmdline = j["command"] if j.get("command") else ""
    out2 = subprocess.run(["powershell", "-NoProfile", "-Command",
                           "$e=$null;[void][System.Management.Automation.Language.Parser]::ParseInput(@'\n%s\n'@,[ref]$null,[ref]$e);if($e){'ERR'}else{'OK'}" % cmdline],
                          capture_output=True, timeout=60).stdout.decode("utf-8", "replace")
    check("화면의 한 줄 명령도 PowerShell 문법 OK", "OK" in out2, out2)
except (FileNotFoundError, PermissionError, OSError):
    print("  (PowerShell 을 이 시험 안에서 못 부름 — 문법 검사는 따로 돌림)")

print("결과: %d 통과 · %d 실패" % (P, F))
sys.exit(1 if F else 0)
