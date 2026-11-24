# -*- coding: utf-8 -*-
"""아웃룩에서 보낸 사람 채우기 시험 — 가짜 메일·가짜 CSV·임시 DB(운영 무접촉 · 실제 메일 없음).
대표 11-25 「예전 아웃룩에 남아있는데 어떻게 전달하지?」
사용: py -3.13 _검증/mail_from_outlook_test.py"""
import io
import os
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
    _TMP = tempfile.mkdtemp(prefix="knk_mfo_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_from_outlook as mfo
    from app import mail_from_guess as mg
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


ME, OTHER = 9401, 9402
with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9401,'t9401','가짜대표','ceo',1,'x')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9402,'t9402','가짜직원','member',1,'x')")


def put(owner, mid, frm="", name="", subj="가짜 제목"):
    with _db.db_session() as c:
        i, _o = ms.store_inbound(c, to_email="t%d@knknara.co.kr" % owner, from_email=frm, from_name=name,
                                 subject=subj, text="가짜 본문 " + mid, owner_id=owner, run_ai=False, message_id=mid)
        # 예전에 읽지 못해 빈 채로 저장된 메일처럼
        c.execute("UPDATE mail_messages SET from_email=?, from_name=? WHERE id=?", (frm, name, i))
        return i


a1 = put(ME, "<aaa1@fake.example>")
a2 = put(ME, "aaa2@fake.example", frm="홍길동")         # 주소 칸에 이름만
a3 = put(ME, "aaa3@fake.example")                        # 파일에 주소 없음
a4 = put(ME, "aaa4@fake.example")                        # 파일에 없음
ok1 = put(ME, "ok1@fake.example", frm="real@fake.example", name="정상")
o1 = put(OTHER, "aaa1@fake.example")                     # 남의 메일(같은 번호)
with _db.db_session() as c:   # a1 은 예전에 「추정」으로 표시된 적이 있다고 침(빈 주소로 되돌려 놓은 상태)
    mg.ensure(c) if hasattr(mg, "ensure") else None
    try:
        c.execute("""CREATE TABLE IF NOT EXISTS mail_from_guessed(mail_id INTEGER PRIMARY KEY, addr TEXT, src TEXT, batch TEXT)""")
    except Exception:
        pass
    c.execute("INSERT OR REPLACE INTO mail_from_guessed(mail_id, addr, src, batch) VALUES(?,?,?,?)", (a1, "x@fake.example", "서명", "guess-x"))

CSV = ('﻿"message_id","from_email","from_name","received_at"\r\n'
       '"<aaa1@fake.example>","Kim.A@Partner.fake.example","김에이, 부장","2026-07-01 09:00:00"\r\n'
       '"aaa2@fake.example","b@partner.fake.example","","2026-07-02 09:00:00"\r\n'
       '"aaa3@fake.example","","이름만","2026-07-03 09:00:00"\r\n'
       '"","c@partner.fake.example","번호없음","2026-07-04 09:00:00"\r\n'
       '"zzz9@fake.example","d@partner.fake.example","다른메일","2026-07-05 09:00:00"\r\n').encode("utf-8")

print("== 1. 파일 읽기 ==")
p = mfo.parse_csv(CSV)
check("BOM·따옴표·쉼표 든 이름 읽음 · 줄 5 · 번호 있는 줄 4 · 쓸 수 있는 줄 3(주소 없는 줄 뺌)",
      p["rows"] == 5 and p["with_mid"] == 4 and len(p["items"]) == 3, p)
check("머리줄에 Message-ID 칸이 없으면 bad_header", mfo.parse_csv(b"a,b\r\n1,2\r\n")["bad_header"])

print("== 2. 입구 ==")
_U = {"role": "member"}
m.get_user = lambda req: {"id": ME if _U["role"] != "member" else OTHER, "role": _U["role"], "name": "가짜", "team_id": None, "team_name": ""}
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
files = lambda b: {"file": ("KNK_아웃룩_보낸사람.csv", b, "text/csv")}
check("직원은 막힘(화면·올리기·명령 파일)", k.post("/mail/from-outlook", files=files(CSV), data={"dry": "1"}).status_code == 403
      and k.get("/mail/from-outlook/script").status_code == 403 and k.get("/mail/from-outlook").status_code == 303)
_U["role"] = "ceo"
h = k.get("/mail/from-outlook").text
check("관리자 화면 200 · 남은 수 · 명령 한 줄 · 내려받기", "보낸 사람 채우기" in h and "outlook_from_export.ps1" in h and "ExecutionPolicy Bypass" in h)
sc = k.get("/mail/from-outlook/script")
check("명령 파일 내려받기 200", sc.status_code == 200 and b"Outlook.Application" in sc.content, sc.status_code)
check("설정·정리 관리자 줄에 링크", "/mail/from-outlook" in k.get("/mail/tools").text)

j = k.post("/mail/from-outlook", files=files(CSV), data={"dry": "1"}).json()
with _db.db_session() as c:
    still = c.execute("SELECT COUNT(*) FROM mail_messages WHERE id IN (?,?) AND COALESCE(from_email,'') NOT LIKE '%@%'", (a1, a2)).fetchone()[0]
check("셈만 = 맞음 2 · 바꾸지 않음", j.get("ok") and j.get("matched") == 2 and j.get("filled") == 0 and still == 2, j)
check("응답에 주소·이름 글자 없음", "partner.fake.example" not in str(j) and "김에이" not in str(j), j)

j = k.post("/mail/from-outlook", files=files(CSV)).json()
with _db.db_session() as c:
    g = {r["id"]: (r["from_email"], r["from_name"], r["fd_key"]) for r in c.execute(
        "SELECT id, from_email, from_name, COALESCE(fd_key,'') AS fd_key FROM mail_messages WHERE id IN (?,?,?,?,?,?)", (a1, a2, a3, a4, ok1, o1))}
    gs = c.execute("SELECT COUNT(*) FROM mail_from_guessed WHERE mail_id=?", (a1,)).fetchone()[0]
    bak = c.execute("SELECT COUNT(*) FROM mail_from_refill_bak WHERE batch LIKE 'outlook-%'").fetchone()[0]
check("채우기 = 2통 · 주소 소문자 · 쉼표 든 이름 그대로", j.get("filled") == 2 and g[a1][0] == "kim.a@partner.fake.example" and g[a1][1] == "김에이, 부장", (j, g))
check("주소 칸에 이름만 있던 메일 = 그 이름을 이름 칸으로(파일 이름이 비었을 때)", g[a2] == ("b@partner.fake.example", "홍길동", ""), g[a2])
check("파일에 주소 없는 메일·파일에 없는 메일은 그대로", "@" not in (g[a3][0] or "") and "@" not in (g[a4][0] or ""), g)
check("정상 메일·남의 메일은 안 건드림", g[ok1][0] == "real@fake.example" and "@" not in (g[o1][0] or ""), g)
check("「🔎 추정」 표시 지움 · 되돌림 표 2줄 · fd_key 비움", gs == 0 and bak == 2 and g[a1][2] == "", (gs, bak))
check("남은 대상 = 2(a3·a4)", j.get("left") == 2, j)
check("응답 = 숫자만", "partner" not in str(j) and "홍길동" not in str(j), j)

j = k.post("/mail/from-outlook", data={"undo": "1"}).json()
with _db.db_session() as c:
    g2 = {r["id"]: (r["from_email"] or "", r["from_name"] or "") for r in c.execute(
        "SELECT id, from_email, from_name FROM mail_messages WHERE id IN (?,?)", (a1, a2))}
check("되돌리기 = 2통 · 고치기 전 값 그대로", j.get("undone") == 2 and g2[a1] == ("", "") and g2[a2] == ("홍길동", ""), (j, g2))

big = b'"message_id","from_email"\r\n' + b"x" * (mfo.MAX_BYTES + 10)
check("20MB 넘으면 거절", k.post("/mail/from-outlook", files=files(big)).status_code == 400)
check("빈 파일·머리줄 틀림 = 400", k.post("/mail/from-outlook", files=files(b"")).status_code == 400
      and k.post("/mail/from-outlook", files=files(b"a,b\r\n1,2\r\n")).status_code == 400)

print("== 3. 명령 파일(.ps1) ==")
ps = open(os.path.join(ROOT, "deploy", "outlook_from_export.ps1"), "rb").read()
txt = ps.decode("utf-8-sig")
check(".ps1 = UTF-8 BOM(5.1 한글) · CRLF", ps.startswith(b"\xef\xbb\xbf") and b"\r\n" in ps and ps.count(b"\n") == ps.count(b"\r\n"))
check(".ps1 = 5.1 문법(&& 없음) · 4칸만(제목·본문 안 읽음) · 읽기만", "&&" not in txt and ".Subject" not in txt and ".Body" not in txt
      and ".Delete(" not in txt and ".Move(" not in txt and ".Save(" not in txt and "0x1035001F" in txt)

print("결과: %d 통과 · %d 실패" % (P, F))
sys.exit(1 if F else 0)
