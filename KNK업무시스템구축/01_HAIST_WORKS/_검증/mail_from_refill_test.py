# -*- coding: utf-8 -*-
"""보낸 사람 주소 못 읽은 메일 다시 채우기 (대표 2026-11-22 「보낸 사람 없는 메일 5통 다시 읽어서 채워 줘」) — 운영 무접촉 · 임시 DB · 가짜 메일함(POP3·IMAP 흉내).

증명할 것
  ① 셈만(dry): 찾은 통수만 · 저장 자료는 그대로 · 돌려주는 값에 주소·이름 없음
  ② 채우기: 원본 머리(Message-ID 해시가 같은 것)의 보낸 사람을 새 방식으로 읽어 이름·주소만 채움 · 바꾸기 전 값은 되돌림 표에
     · 다른 메일(보낸 사람 있는 것·남의 메일·원본 없는 것)은 안 건드림
  ③ ↺ 되돌리기 = 빈 값으로 되돌림 · IMAP 도 같은 결과 · 원본은 읽기만(IMAP readonly · BODY.PEEK)
"""
import base64
import io
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
os.environ["KNK_RUN_MAIL_FETCH"] = "0"

_so = sys.stdout
sys.stdout = io.StringIO()
try:
    from cryptography.fernet import Fernet
    os.environ.setdefault("KNK_MAIL_KEY", Fernet.generate_key().decode())
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_mfr_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as MS
    from app import mail_fetch as MF
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
        print("  [FAIL]", name, "<-", str(extra)[:400])


def b64(s):
    return "=?UTF-8?B?" + base64.b64encode(s.encode()).decode() + "?="


D = "@knknara.co.kr"
UID, OTHER = 9890, 9891
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x', email=NULL")
    c.execute("INSERT INTO users(id, login_id, name, rank, role, is_active, password, email) VALUES(9890,'t_me','시험신입','사원','member',1,'x','me" + D + "')")
    c.execute("INSERT INTO users(id, login_id, name, rank, role, is_active, password, email) VALUES(9891,'t_oth','시험남','사원','member',1,'x','oth" + D + "')")
    MF._ensure_table(c)
    MF.save_account(c, UID, protocol="pop3", host="pop.fake-demo", port=995, use_ssl=True, username="me", password_enc=m._mail.encrypt("fake-pw"), label="시험")

    def put(uid, frm, nm, mid, subj):
        i, _ = MS.store_inbound(c, to_email="me" + D, from_email=frm, from_name=nm, subject=subj, text="가짜",
                                owner_id=uid, run_ai=False, message_id=mid)
        return i
    A = put(UID, "", "", "a-1@demo", "주간보고 A")            # 원본: 이름에 쉼표
    B = put(UID, "", "", "b-2@demo", "주간보고 B")            # 원본: 이름에 @
    C = put(UID, "", "", "c-3@demo", "원본 없는 메일")         # 메일함에 원본 없음
    OK = put(UID, "keep-demo@example.com", "그대로", "d-4@demo", "보낸 사람 있는 메일")
    OTH = put(OTHER, "", "", "a-1@demo-oth", "남의 메일")

HDR = {"a-1@demo": "From: %s <vn-demo@example.com>\r\nMessage-ID: <a-1@demo>\r\n" % b64("홍길동, KNK VINA"),
       "b-2@demo": "From: %s <hq-demo@example.com>\r\nMessage-ID: <b-2@demo>\r\n" % b64("김@본사"),
       "d-4@demo": "From: 다른값 <changed-demo@example.com>\r\nMessage-ID: <d-4@demo>\r\n",
       "z-9@demo": "From: 아무개 <z-demo@example.com>\r\nMessage-ID: <z-9@demo>\r\n"}
ORDER = ["z-9@demo", "d-4@demo", "b-2@demo", "a-1@demo"]
CALLS = {"top": 0, "imap_fetch": [], "imap_readonly": None}


class FakePOP:
    def uidl(self):
        return b"+OK", [("%d uid%d" % (i + 1, i + 1)).encode() for i in range(len(ORDER))], 0

    def top(self, n, k):
        CALLS["top"] += 1
        return b"+OK", HDR[ORDER[n - 1]].encode().split(b"\r\n"), 0

    def quit(self):
        pass


class FakeIMAP:
    def select(self, box, readonly=False):
        CALLS["imap_readonly"] = readonly
        return "OK", [b"4"]

    def uid(self, cmd, *a):
        if cmd == "search":
            return "OK", [b" ".join(str(i + 1).encode() for i in range(len(ORDER)))]
        CALLS["imap_fetch"].append(a[1])
        out = []
        for u in a[0].split(","):
            out.append((("%s (UID %s BODY[HEADER.FIELDS (MESSAGE-ID FROM REPLY-TO)] {1}" % (u, u)).encode(), HDR[ORDER[int(u) - 1]].encode()))
            out.append(b")")
        return "OK", out

    def logout(self):
        pass


MF._pop3_connect = lambda *a, **k: FakePOP()
MF._imap_connect = lambda *a, **k: FakeIMAP()
ME = {"id": UID, "role": "member", "name": "시험신입", "rank": "사원", "login_id": "t_me", "email": "me" + D, "lang": "ko"}
m.get_user = lambda req: ME
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})


def wait():
    for _ in range(100):
        j = k.get("/mail/from-refill").json()
        if j.get("state") in ("done", "error"):
            return j
        time.sleep(0.05)
    return j


def row(i):
    with _db.db_session() as c:
        r = c.execute("SELECT from_email, from_name FROM mail_messages WHERE id=?", (i,)).fetchone()
        return (r["from_email"] or "", r["from_name"] or "")


print("① 셈만")
j0 = k.post("/mail/from-refill", data={"dry": "1"}).json()
j = wait()
check("셈만: 대상 3 · 찾음 2(원본 없는 1통) · 저장 자료 그대로", j0.get("ok") and j.get("state") == "done" and j.get("targets") == 3 and j.get("found") == 2
      and j.get("updated") == 0 and row(A) == ("", "") and row(B) == ("", ""), j)
check("돌려주는 값에 주소·이름 없음", "example.com" not in str(j) and "홍길동" not in str(j), j)

print("② 채우기")
k.post("/mail/from-refill", data={})
j = wait()
check("채움 2통", j.get("state") == "done" and j.get("updated") == 2, j)
check("A: 이름에 쉼표가 있던 메일 → 이름·주소", row(A) == ("vn-demo@example.com", "홍길동, KNK VINA"), row(A))
check("B: 이름에 @ 가 있던 메일 → 이름·주소", row(B) == ("hq-demo@example.com", "김@본사"), row(B))
check("원본 없는 메일·보낸 사람 있던 메일·남의 메일은 그대로", row(C) == ("", "") and row(OK) == ("keep-demo@example.com", "그대로") and row(OTH) == ("", ""), (row(C), row(OK), row(OTH)))
with _db.db_session() as c:
    bk = c.execute("SELECT COUNT(*) FROM mail_from_refill_bak WHERE user_id=? AND old_from_email=''", (UID,)).fetchone()[0]
check("바꾸기 전 값 = 되돌림 표에 2줄", bk == 2, bk)
check("원본 머리만 읽음(POP3 TOP · 찾으면 멈춤)", CALLS["top"] > 0)

print("③ 되돌리기 · IMAP")
j = k.post("/mail/from-refill", data={"undo": "1"}).json()
check("↺ 되돌리기 = 2통 빈 값으로", j.get("undone") == 2 and row(A) == ("", "") and row(B) == ("", ""), (j, row(A)))
_orig = m._mailfetch_creds
m._mailfetch_creds = lambda c, u, form=None: ("imap",) + tuple(_orig(c, u, form)[1:])
k.post("/mail/from-refill", data={})
j = wait()
check("IMAP 도 같은 결과(2통)", j.get("updated") == 2 and row(A) == ("vn-demo@example.com", "홍길동, KNK VINA"), (j, row(A)))
check("IMAP 원본은 읽기만(readonly · BODY.PEEK)", CALLS["imap_readonly"] is True and all("BODY.PEEK" in x for x in CALLS["imap_fetch"]), CALLS)
m._mailfetch_creds = _orig
k.post("/mail/from-refill", data={"undo": "1"})

print("④ 11-24 3차 — 숫자 점검 · 제목+시각 짝(Message-ID 없이 저장된 대상)")
# 대상 새로: c형(Message-ID 없이 저장 → 판정값 = 보낸이+제목+본문) 세 가지
#   E = 제목 하나·시각 맞는 원본 하나 → 채움 · G1·G2 = 같은 제목·같은 시각 둘 → 원본 하나와 둘 다 맞음 → 안 채움
#   H = 같은 제목·시각 원본이 둘 → 안 채움 · I = 제목 같지만 시각 2시간 차이 → 안 채움
T0 = "Tue, 4 Aug 2026 10:00:00 +0900"
T0s = MS._sent_at(T0)
with _db.db_session() as c:
    def put2(subj, sent, frm=""):
        i, _ = MS.store_inbound(c, to_email="me" + D, from_email=frm, from_name="", subject=subj, text="가짜 " + subj + str(time.time()),
                                owner_id=UID, run_ai=False, message_id="", sent_at=sent)
        c.execute("UPDATE mail_messages SET received_at=? WHERE id=?", ("2026-11-24 21:00:00", i))
        return i
    E = put2("가짜 견적 회신 E", T0s)
    G1 = put2("가짜 같은제목 G", T0s)
    G2 = put2("가짜 같은제목 G", T0s)
    H = put2("가짜 두원본 H", T0s)
    I = put2("가짜 시각다름 I", MS._sent_at("Tue, 4 Aug 2026 12:00:00 +0900"))


def hdr2(subj, frm, date, mid):
    return "From: %s\r\nSubject: %s\r\nDate: %s\r\nMessage-ID: <%s>\r\n" % (frm, b64(subj), date, mid)


HDR.update({"e@src": hdr2("가짜 견적 회신 E", "%s <e-demo@example.com>" % b64("가짜이"), "Tue, 4 Aug 2026 10:03:00 +0900", "e@src"),
            "g@src": hdr2("가짜 같은제목 G", "g-demo@example.com", "Tue, 4 Aug 2026 10:01:00 +0900", "g@src"),
            "h1@src": hdr2("가짜 두원본 H", "h1-demo@example.com", "Tue, 4 Aug 2026 10:02:00 +0900", "h1@src"),
            "h2@src": hdr2("가짜 두원본 H", "h2-demo@example.com", "Tue, 4 Aug 2026 09:58:00 +0900", "h2@src"),
            "i@src": hdr2("가짜 시각다름 I", "i-demo@example.com", "Tue, 4 Aug 2026 10:00:00 +0900", "i@src")})
ORDER[:] = ["e@src", "g@src", "h1@src", "h2@src", "i@src"] + ORDER
k.post("/mail/from-refill", data={"dry": "1"})
j = wait()
dg = j.get("diag") or {}
check("셈만: 원본 숫자(STAT 없음 = -1 · UIDL 9 · 가장 옛/새 달)", j.get("src_uidl") == 9 and j.get("src_oldest") == "2026-08" and j.get("src_newest") == "2026-08", j)
check("셈만: 제목+시각 짝 1통(E만) · Message-ID 짝 2통(A·B)", j.get("found_subj") == 1 and j.get("found_mid") == 2 and j.get("found") == 3, j)
check("숫자 점검: 대상 8 = mid형 3 · c형 5 · 달별 · 원래 날짜 있는 수 5 · 전체 받은 메일",
      dg.get("targets") == 8 and dg.get("hash_kind") == {"mid": 3, "c": 5, "none": 0} and dg.get("sent_at_known") == 5
      and sum((dg.get("targets_by_month") or {}).values()) == 8 and dg.get("all_in", 0) >= 9, dg)
check("숫자 점검·진행 상황에 주소·제목·이름 글자 없음",
      not any(x in str(j) for x in ("example.com", "가짜 견적", "같은제목", "두원본", "홍길동", "가짜이")), str(j)[:300])
with _db.db_session() as c:
    bk_before = c.execute("SELECT COUNT(*) FROM mail_from_refill_bak").fetchone()[0]
k.post("/mail/from-refill", data={})
j = wait()
check("채우기: 3통(A·B = Message-ID · E = 제목+시각)", j.get("updated") == 3, j)
check("E: 제목+시각 하나만 맞음 → 이름·주소", row(E) == ("e-demo@example.com", "가짜이"), row(E))
check("G1·G2: 같은 제목·시각 대상 둘 → 안 채움", row(G1) == ("", "") and row(G2) == ("", ""), (row(G1), row(G2)))
check("H: 맞는 원본 둘 → 안 채움 · I: 시각 2시간 차이 → 안 채움", row(H) == ("", "") and row(I) == ("", ""), (row(H), row(I)))
j = k.post("/mail/from-refill", data={"undo": "1"}).json()
check("↺ 되돌리기 = 3통 빈 값으로(E 포함)", j.get("undone") == 3 and row(E) == ("", ""), (j, row(E)))

print("⑤ 전 직원 숫자 점검(관리자)")
check("직원은 전 직원 점검 못 함", k.get("/mail/from-diag-all").status_code == 403)
ME["role"] = "ceo"
j = k.get("/mail/from-diag-all").json()
ME["role"] = "member"
_u = {r["user_id"]: r for r in j.get("users", [])}
check("전 직원 점검: 사람별 빈 주소(나 8 · 남 1) · 최근 7일 · 머리글 남긴 수 · 숫자만",
      j.get("ok") and _u.get(UID, {}).get("empty") == 8 and _u.get(UID, {}).get("empty_7d") == 8 and _u.get(OTHER, {}).get("empty") == 1
      and "empty_hdr" in _u.get(UID, {}) and "example.com" not in str(j) and "가짜" not in str(j), j)

print("\n결과: %d 통과 · %d 실패" % (P, F))
sys.exit(1 if F else 0)
