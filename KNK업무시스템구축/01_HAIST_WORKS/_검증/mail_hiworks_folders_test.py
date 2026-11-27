# -*- coding: utf-8 -*-
"""하이웍스 개인 메일함 가져오기 시험 — 가짜 IMAP(imaplib 흉내) · 임시 DB(운영·실제 하이웍스·실제 메일 무접촉).
대표 11-27 「1번으로 진행해」 · 「아웃룩 안 쓰고 하이웍스만 사용하는 직원들이 있어서 만드는 거야」
확인: 폴더 목록(기본 함 빼기 · 이름 해독) · 이미 있는 메일 옮기기 · 새 메일 저장 · 다른 폴더에 있던 메일 그대로 ·
      지운 메일 그대로 · 이어서 하기(두 번 안 들어감) · 너무 큰 메일 · 규칙 후보 · 확인한 것만 저장 · 하이웍스 읽기 전용 ·
      비밀번호 저장 안 함 · 본인 주소만 · 다른 사이트 요청 막기 · 화면 열림
사용: py -3.13 _검증/mail_hiworks_folders_test.py"""
import imaplib
import io
import os
import re
import sys
import tempfile
import time
from email.message import EmailMessage

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
    _TMP = tempfile.mkdtemp(prefix="knk_mhw_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_folders as mf
    from app import mail_hiworks_folders as mhw
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


PW = "가짜-비번-Zq81!"      # 가짜 비밀번호(DB 에 남으면 안 됨)
ME, OTHER = 9601, 9602
with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email) VALUES(?,?,?,?,?,?,?)",
              (ME, "t9601", "가짜직원", "member", 1, "x", "hong@knknara.co.kr"))
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email) VALUES(?,?,?,?,?,?,?)",
              (OTHER, "t9602", "남직원", "member", 1, "x", "kim@knknara.co.kr"))
mio.disk_state = lambda path=None: {"free": 50 * 1024 ** 3, "total": 100 * 1024 ** 3, "ok": True}


# ─── 가짜 메일 ───────────────────────────────────────────────────
def raw_mail(mid, frm, subj, body="가짜 본문"):
    e = EmailMessage()
    e["From"] = frm
    e["To"] = "hong@knknara.co.kr"
    e["Subject"] = subj
    e["Date"] = "Mon, 02 Nov 2026 09:00:00 +0900"
    if mid:
        e["Message-ID"] = "<%s>" % mid
    e.set_content(body)
    return e.as_bytes()


# 이음 메일에 이미 있는 메일
with _db.db_session() as c:
    A, _ = ms.store_inbound(c, to_email="hong@knknara.co.kr", owner_id=ME, from_email="boss@partner.example",
                            subject="이미 있는 메일 A", text="a", run_ai=False, message_id="a1@x")
    B, _ = ms.store_inbound(c, to_email="hong@knknara.co.kr", owner_id=ME, from_email="boss@partner.example",
                            subject="이미 다른 폴더 B", text="b", run_ai=False, message_id="b1@x")
    C, _ = ms.store_inbound(c, to_email="hong@knknara.co.kr", owner_id=ME, from_email="x@partner.example",
                            subject="지운 메일 C", text="c", run_ai=False, message_id="c1@x")
    OF = mf.add_folder(c, ME, "내가 만든 다른 폴더")
    c.execute("UPDATE mail_messages SET fd_pin=? WHERE id=?", ("f%d" % OF, B))
    c.execute("UPDATE mail_messages SET is_deleted=1 WHERE id=?", (C,))
    # 남의 메일함에 같은 번호의 메일 — 건드리면 안 됨
    X, _ = ms.store_inbound(c, to_email="kim@knknara.co.kr", owner_id=OTHER, from_email="boss@partner.example",
                            subject="남의 메일", text="o", run_ai=False, message_id="d1@x")

ENC = mhw.encode_mutf7
BOX = {
    "INBOX": [],
    ENC("주간업무"): [
        (101, "a1@x", "boss@partner.example", "이미 있는 메일 A", True, None),
        (102, "b1@x", "boss@partner.example", "이미 다른 폴더 B", True, None),
        (103, "c1@x", "x@partner.example", "지운 메일 C", True, None),
        (104, "d1@x", "boss@partner.example", "새 메일 D1", True, None),
        (105, "d2@x", "boss@partner.example", "새 메일 D2", False, None),
        (106, "", "boss@partner.example", "번호 없는 새 메일", True, None),
        (107, "big@x", "boss@partner.example", "너무 큰 메일", True, mhw.MAX_MSG_BYTES + 1),
    ],
    ENC("자금일보"): [(200 + i, "f%d@x" % i, "fin%d@bank-x.example" % (i % 2), "자금일보 %d" % i, True, None) for i in range(4)],
    "INBOX/" + ENC("홍길동"): [(300, "h1@x", "gil@free.example", "홍길동 메일", True, None)],
}
LIST = [
    b'(\\HasChildren) "/" "INBOX"',
    b'(\\HasNoChildren \\Sent) "/" "' + ENC("보낸메일함").encode() + b'"',
    b'(\\HasNoChildren) "/" "' + ENC("휴지통").encode() + b'"',
    b'(\\HasNoChildren) "/" "' + ENC("스팸메일함").encode() + b'"',
    b'(\\Noselect \\HasChildren) "/" "' + ENC("묶음만").encode() + b'"',
    b'(\\HasNoChildren) "/" "' + ENC("주간업무").encode() + b'"',
    (b'(\\HasNoChildren) "/" {%d}' % len(ENC("자금일보")), ENC("자금일보").encode()),   # 글자 묶음(literal)으로 온 이름
    b'(\\HasNoChildren) "/" "INBOX/' + ENC("홍길동").encode() + b'"',
]
CALLS = []


class FakeIMAP:
    def __init__(self, user, pw):
        if pw != PW or user != "hong@knknara.co.kr":
            raise imaplib.IMAP4.error("AUTHENTICATIONFAILED")
        self.sel = None
        self.readonly = []

    def list(self, *a):
        CALLS.append(("LIST",))
        return "OK", list(LIST)

    def status(self, name, what):
        CALLS.append(("STATUS", name))
        n = name.strip('"')
        return "OK", [b'"%s" (MESSAGES %d)' % (n.encode(), len(BOX.get(n, [])))]

    def select(self, name, readonly=False):
        CALLS.append(("SELECT", name, readonly))
        self.readonly.append(readonly)
        self.sel = name.strip('"')
        return "OK", [b"1"]

    def uid(self, cmd, *args):
        cmd = cmd.upper()
        CALLS.append(("UID", cmd) + tuple(str(a) for a in args))
        items = BOX.get(self.sel, [])
        if cmd == "SEARCH":
            return "OK", [" ".join(str(x[0]) for x in items).encode()]
        if cmd == "FETCH":
            want = {int(u) for u in args[0].split(",")}
            spec = args[1]
            out = []
            for (u, mid, frm, sj, seen, size) in items:
                if u not in want:
                    continue
                raw = raw_mail(mid, frm, sj)
                if "HEADER.FIELDS" in spec:
                    hdr = ("Message-ID: <%s>\r\n" % mid if mid else "") + "From: %s\r\nSubject: x\r\n\r\n" % frm
                    meta = ('%d (UID %d FLAGS (%s) INTERNALDATE "02-Nov-2026 09:00:00 +0900" RFC822.SIZE %d '
                            'BODY[HEADER.FIELDS (MESSAGE-ID FROM SUBJECT DATE)] {%d}'
                            % (u, u, "\\Seen" if seen else "", size or len(raw), len(hdr))).encode()
                    out += [(meta, hdr.encode()), b")"]
                elif spec == "(BODY.PEEK[])":
                    out += [(b"%d (UID %d BODY[] {%d}" % (u, u, len(raw)), raw), b")"]
                else:
                    CALLS.append(("BAD-FETCH", spec))
            return "OK", out
        CALLS.append(("FORBIDDEN-UID", cmd))
        return "NO", []

    def __getattr__(self, nm):   # store·expunge·copy·move·append·delete … 무엇이든 부르면 기록
        def _f(*a, **k):
            CALLS.append(("FORBIDDEN", nm))
            return "NO", []
        return _f

    def logout(self):
        CALLS.append(("LOGOUT",))


mhw.CONNECT = lambda host, port, user, pw: FakeIMAP(user, pw)

print("[1] 이름 해독")
for s in ("주간업무", "자금일보", "홍길동 & 김철수", "Q&A 2026"):
    check("되짚기 %s" % s, mhw.decode_mutf7(mhw.encode_mutf7(s)) == s, mhw.encode_mutf7(s))
check("영문 이름은 그대로", mhw.decode_mutf7("Work.2026") == "Work.2026")

print("[2] 폴더 목록 — 개인 메일함만")
M, used = mhw.connect("", 993, "hong@knknara.co.kr", PW)
fl = mhw.list_folders(M)
labels = [f["label"] for f in fl]
check("개인 메일함 셋(주간업무·자금일보·홍길동)", sorted(labels) == sorted(["주간업무", "자금일보", "홍길동"]), labels)
check("받은·보낸·휴지통·스팸·묶음만 빠짐", not any(x in labels for x in ("INBOX", "보낸메일함", "휴지통", "스팸메일함", "묶음만")), labels)
check("메일 수", {f["label"]: f["count"] for f in fl} == {"주간업무": 7, "자금일보": 4, "홍길동": 1}, fl)
check("기본 서버 주소 = imaps.hiworks.com", used == "imaps.hiworks.com", used)
try:
    mhw.connect("", 993, "hong@knknara.co.kr", "틀린비번")
    check("틀린 비밀번호 = 실패", False)
except Exception as e:
    msg = mhw.friendly_error(e)
    check("틀린 비밀번호 = 쉬운 안내(IMAP 사용 켜기)", "IMAP 사용을 켜" in msg, msg)

print("[3] 본인 주소만")
with _db.db_session() as c:
    check("본인 주소 그대로", mhw.match_own(c, ME, "Hong@KNKnara.co.kr") == "hong@knknara.co.kr")
    check("아이디만(hong)", mhw.match_own(c, ME, "hong") == "hong@knknara.co.kr")
    check("남의 주소 = 거절", mhw.match_own(c, ME, "kim@knknara.co.kr") == "")

print("[4] 가져오기(직접 · 기다림)")
CALLS.clear()
ok, rid = mhw.start(_db.db_session, ME, "hong@knknara.co.kr", PW, "imaps.hiworks.com", fl, wait=True)
with _db.db_session() as c:
    st = mhw.public(mhw.latest(c, ME))
    fid = {r["name"]: r["id"] for r in c.execute("SELECT id, name FROM mail_folders WHERE user_id=?", (ME,)).fetchall()}
    kw = "f%d" % fid.get("주간업무", 0)
    pin = {r["id"]: r["fd_pin"] for r in c.execute("SELECT id, COALESCE(fd_pin,'') AS fd_pin FROM mail_messages WHERE user_id=?", (ME,)).fetchall()}
    new = {r["subject"]: dict(r) for r in c.execute("SELECT * FROM mail_messages WHERE user_id=? AND id>?", (ME, X)).fetchall()}
    other_pin = c.execute("SELECT COALESCE(fd_pin,'') FROM mail_messages WHERE id=?", (X,)).fetchone()[0]
check("끝남", st.get("state") == "done", st)
check("같은 이름 폴더 셋이 생김", all(n in fid for n in ("주간업무", "자금일보", "홍길동")), fid)
check("이미 있던 A = 주간업무로 옮김", pin.get(A) == kw, pin.get(A))
check("다른 폴더에 둔 B = 그대로", pin.get(B) == "f%d" % OF, pin.get(B))
check("지운 C = 그대로(옮기지 않음)", pin.get(C) == "", pin.get(C))
check("새 메일 D1·D2·번호 없는 메일 저장 · 주간업무", all(new.get(s, {}).get("fd_pin") == kw for s in ("새 메일 D1", "새 메일 D2", "번호 없는 새 메일")), list(new))
check("읽음 = 하이웍스 그대로(D1 읽음 · D2 안 읽음)", new.get("새 메일 D1", {}).get("is_read") == 1 and new.get("새 메일 D2", {}).get("is_read") == 0)
check("받은 때 = 하이웍스 도착 시각(2026-11-02)", (new.get("새 메일 D1", {}).get("received_at") or "").startswith("2026-11-02"), new.get("새 메일 D1", {}).get("received_at"))
check("너무 큰 메일 = 받지 않음", "너무 큰 메일" not in new and st["big"] == 1, st)
check("숫자: 새로 8 · 옮김 1 · 그대로 1 · 지운 것 1", (st["saved"], st["moved"], st["kept"], st["other"]) == (8, 1, 1, 1), st)
check("남의 메일함 = 손대지 않음", other_pin == "")
check("새 메일 주인 = 본인만", all(v["user_id"] == ME for v in new.values()))

print("[5] 하이웍스 읽기 전용")
bad = [x for x in CALLS if x[0] in ("FORBIDDEN", "FORBIDDEN-UID", "BAD-FETCH")]
check("STORE·EXPUNGE·COPY·MOVE·APPEND·DELETE 0번", not bad, bad)
sel = [x for x in CALLS if x[0] == "SELECT"]
check("폴더는 모두 읽기 전용으로 열림", sel and all(x[2] is True for x in sel), sel)
fetches = [x for x in CALLS if x[:2] == ("UID", "FETCH")]
check("읽기는 PEEK 만(읽음 표시 안 붙음)", fetches and all("PEEK" in x[3] for x in fetches), fetches[:3])

print("[6] 이어서 하기 = 두 번 안 들어감")
with _db.db_session() as c:
    n0 = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=?", (ME,)).fetchone()[0]
ok, rid2 = mhw.start(_db.db_session, ME, "hong@knknara.co.kr", PW, "imaps.hiworks.com", fl, wait=True)
with _db.db_session() as c:
    n1 = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=?", (ME,)).fetchone()[0]
    st2 = mhw.public(mhw.latest(c, ME))
check("두 번째엔 새 메일 0 · 메일 수 그대로", n1 == n0 and st2["saved"] == 0, (n0, n1, st2))
check("두 번째엔 「이미 그 폴더」로 셈", st2["already"] == 9, st2)

print("[7] 비밀번호 저장 안 함")
db_bytes = open(_db.DB_PATH, "rb").read()
for ext in ("-wal",):
    if os.path.exists(_db.DB_PATH + ext):
        db_bytes += open(_db.DB_PATH + ext, "rb").read()
check("DB 파일에 비밀번호 글자 없음", PW.encode("utf-8") not in db_bytes)
check("뒤에서 도는 작업 남지 않음", not mhw.is_running(ME))

print("[8] 규칙 후보 · 확인한 것만 저장")
with _db.db_session() as c:
    cands = mhw.rule_candidates(c, ME)
by = {x["folder"]: x for x in cands}
check("자금일보 = 회사 주소 @bank-x.example 후보", by.get("자금일보", {}).get("kind") == "domain" and by["자금일보"]["pattern"] == "bank-x.example", cands)
check("주간업무 = boss@partner.example 계열 후보", by.get("주간업무", {}).get("pattern") in ("partner.example", "boss@partner.example"), by.get("주간업무"))
check("1통짜리 홍길동 = 후보 없음", "홍길동" not in by)
with _db.db_session() as c:
    r0 = c.execute("SELECT COUNT(*) FROM mail_move_rules WHERE user_id=?", (ME,)).fetchone()[0]
    o1 = mhw.save_rules(c, ME, [by["자금일보"]["id"]], "")
    o2 = mhw.save_rules(c, ME, ["domain|evil.example|f1"], "new")
    r1 = c.execute("SELECT COUNT(*) FROM mail_move_rules WHERE user_id=?", (ME,)).fetchone()[0]
check("언제부터 안 고르면 저장 안 함", not o1["ok"] and r1 == r0, o1)
check("후보에 없는 값 = 저장 안 함", o2["saved"] == 0 and o2["skipped"] == 1, o2)
check("규칙 후보만 보고 저장 안 하면 규칙 0", r0 == 0, r0)
with _db.db_session() as c:
    o3 = mhw.save_rules(c, ME, [by["자금일보"]["id"]], "new")
    rr = [dict(r) for r in c.execute("SELECT kind, pattern, target, since FROM mail_move_rules WHERE user_id=?", (ME,)).fetchall()]
    again = {x["folder"]: x for x in mhw.rule_candidates(c, ME)}
check("체크한 것 하나만 저장", o3["saved"] == 1 and len(rr) == 1 and rr[0]["pattern"] == "bank-x.example" and rr[0]["target"] == "f%d" % fid["자금일보"], (o3, rr))
check("지금부터만 = 시작 시각 있음", bool(rr and rr[0]["since"]), rr)
check("다시 보면 「이미 있음」", again.get("자금일보", {}).get("status") == "have", again.get("자금일보"))
check("주간업무 후보는 저장 안 됨(체크 안 함)", again.get("주간업무", {}).get("status") == "new", again.get("주간업무"))

print("[9] 화면·주소(시험 서버 흉내)")
_U = {"id": ME}
m.get_user = lambda req: dict(_U, role="member", name="가짜", team_id=None, team_name="", login_id="t%d" % _U["id"])
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
r = k.get("/mail/hiworks-folders")
check("화면 열림 200", r.status_code == 200, r.status_code)
check("화면: 단계 줄·닫기·비밀번호 저장 안 함 안내", all(s in r.text for s in ("연결·폴더 보기", "규칙 확인", "저장하지 않습니다", "hwConnect")) and ("닫기" in r.text or "mail-exit" in r.text), r.text[:300])
r = k.get("/mail/tools")
check("메일 도구에 입구", r.status_code == 200 and "/mail/hiworks-folders" in r.text, r.status_code)
r = k.post("/mail/hiworks-folders/connect", data={"hw_id": "kim@knknara.co.kr", "hw_pw": PW})
check("남의 주소로 연결 = 거절", r.status_code == 400 and "본인" in r.json().get("message", ""), r.text[:200])
r = k.post("/mail/hiworks-folders/connect", data={"hw_id": "hong@knknara.co.kr", "hw_pw": PW, "host": "evil.example.com"})
check("하이웍스 아닌 서버 주소 = 거절", r.status_code == 400, r.text[:200])
r = k.post("/mail/hiworks-folders/connect", data={"hw_id": "hong@knknara.co.kr", "hw_pw": ""})
check("비밀번호 없으면 거절", r.status_code == 400, r.text[:200])
r = k.post("/mail/hiworks-folders/connect", data={"hw_id": "hong@knknara.co.kr", "hw_pw": PW})
j = r.json()
check("연결 → 폴더 셋", r.status_code == 200 and len(j.get("folders") or []) == 3, r.text[:300])
check("응답에 비밀번호 없음", PW not in r.text)
r = k.post("/mail/hiworks-folders/connect", data={"hw_id": "hong@knknara.co.kr", "hw_pw": PW}, headers={"origin": "https://evil.example"})
check("다른 사이트에서 온 요청 = 막음(403)", r.status_code == 403, r.status_code)
raws = [f["raw"] for f in j.get("folders") or []]
import json as _json
r = k.post("/mail/hiworks-folders/start", data={"hw_id": "hong", "hw_pw": PW, "folders": _json.dumps(raws)})
check("시작(뒤에서)", r.status_code == 200 and r.json().get("ok"), r.text[:300])
t0 = time.time()
stt = {}
while time.time() - t0 < 20:
    stt = k.get("/mail/hiworks-folders/status").json().get("st") or {}
    if stt.get("state") != "running":
        break
    time.sleep(0.2)
check("뒤에서 끝남", stt.get("state") == "done", stt)
r = k.get("/mail/hiworks-folders/rules")
check("규칙 후보 주소", r.status_code == 200 and r.json().get("rules"), r.text[:200])
r = k.post("/mail/hiworks-folders/rules", data={"picked": "[]", "when": "new"})
check("체크 없이 저장 = 거절", r.status_code == 400, r.text[:200])
_U["id"] = OTHER
stx = k.get("/mail/hiworks-folders/status").json().get("st")
check("다른 직원에겐 내 진행 상황 안 보임", not stx, stx)
r = k.get("/mail/hiworks-folders")
check("다른 직원 화면도 열림(누구나)", r.status_code == 200 and "kim@knknara.co.kr" in r.text and "hong@knknara.co.kr" not in r.text)

print("\n결과: %d 통과 · %d 실패" % (P, F))
sys.exit(1 if F else 0)
