# -*- coding: utf-8 -*-
"""
KNK Mail 아웃룩 편의기능 검증 — 임시저장·읽음표시·숨은참조(BCC)·서식(HTML) 발송
"""
import os, sys, sqlite3

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "01_HAIST_WORKS")))
from cryptography.fernet import Fernet
os.environ["KNK_MAIL_KEY"] = Fernet.generate_key().decode()

from app import database as DB
from app import mail_store as MS
from app import mail_send as SEND

PASS, FAIL = 0, 0
def check(n, c, e=""):
    global PASS, FAIL
    if c: PASS += 1; print(f"  [PASS] {n}" + (f"  ({e})" if e else ""))
    else: FAIL += 1; print(f"  [FAIL] {n}" + (f"  ({e})" if e else ""))
def section(t): print("\n" + "=" * 60 + f"\n{t}\n" + "=" * 60)

con = sqlite3.connect(":memory:")
con.row_factory = sqlite3.Row
con.execute("PRAGMA foreign_keys=ON")
con.executescript(DB.SCHEMA)
con.execute("INSERT INTO users(id,name,login_id,password,role,is_active) VALUES(1,'김정락','kjr','x','ceo',1)")
con.commit()

section("스키마 — bcc 컬럼")
cols = [r[1] for r in con.execute("PRAGMA table_info(mail_messages)").fetchall()]
check("mail_messages.bcc 컬럼 존재", "bcc" in cols, str([c for c in cols if c in ('cc','bcc')]))

section("임시저장(Drafts)")
did = MS.save_draft(con, user_id=1, to_email="a@b.com", cc="c@d.com", bcc="e@f.com",
                    subject="초안제목", body="작성 중", body_html="<b>작성 중</b>")
con.commit()
check("임시저장 생성", bool(did))
check("임시저장 개수=1", MS.count_drafts(con, 1) == 1)
d = MS.get_draft(con, did, 1)
check("조회 필드 보존", d and d["to_email"] == "a@b.com" and d["bcc"] == "e@f.com" and d["body_html"] == "<b>작성 중</b>")
did2 = MS.save_draft(con, user_id=1, draft_id=did, to_email="a2@b.com", subject="초안2", body="수정", body_html="x")
con.commit()
check("같은 id로 갱신(중복생성 X)", did2 == did and MS.count_drafts(con, 1) == 1)
check("갱신 내용 반영", MS.get_draft(con, did, 1)["to_email"] == "a2@b.com")
check("초안은 받은/보낸함에 안 섞임", len(MS.list_inbox(con, 1)) == 0 and len(MS.list_sent(con, 1)) == 0)
check("타인은 초안 조회 불가", MS.get_draft(con, did, 2) is None)
MS.delete_draft(con, did, 1)
con.commit()
check("임시저장 삭제", MS.count_drafts(con, 1) == 0 and MS.get_draft(con, did, 1) is None)

section("읽음/안읽음 수동 표시")
con.execute("INSERT INTO mail_messages(user_id,direction,from_email,subject,body_text,is_read) "
            "VALUES(1,'in','x@y.com','테스트','본문',0)")
mid = con.execute("SELECT id FROM mail_messages WHERE direction='in'").fetchone()[0]
con.commit()
MS.set_read(con, mid, 1, read=True); con.commit()
r = con.execute("SELECT is_read, read_at FROM mail_messages WHERE id=?", (mid,)).fetchone()
check("읽음 표시(is_read=1, read_at 기록)", r["is_read"] == 1 and r["read_at"])
MS.set_read(con, mid, 1, read=False); con.commit()
r = con.execute("SELECT is_read, read_at FROM mail_messages WHERE id=?", (mid,)).fetchone()
check("안읽음 표시(is_read=0, read_at NULL)", r["is_read"] == 0 and r["read_at"] is None)

section("보낸함 저장 — 숨은참조·HTML 본문")
oid = MS.store_outbound(con, user_id=1, from_email="me@x.com", to_email="t@y.com",
                        subject="제목", body="평문", cc="c@y.com", bcc="bcc@y.com",
                        body_html="<p>서식 <b>본문</b></p>")
con.commit()
row = con.execute("SELECT bcc, body_html, direction FROM mail_messages WHERE id=?", (oid,)).fetchone()
check("보낸메일 bcc 저장", row["bcc"] == "bcc@y.com")
check("보낸메일 HTML 본문 저장", row["body_html"] == "<p>서식 <b>본문</b></p>")
check("direction=out", row["direction"] == "out")

section("발송 — BCC 봉투수신자 + HTML 대체파트 (SMTP 가짜)")
SEND.save_send_config(con, "smtp.mx.cloudflare.net", "465", "api_token", "tok_secret")
con.commit()
captured = {}
class FakeSMTP:
    def __init__(self, *a, **k): pass
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def login(self, u, p): captured["login"] = (u, p)
    def send_message(self, msg): captured["msg"] = msg
SEND.smtplib.SMTP_SSL = FakeSMTP
ok, msg = SEND.send_system(con, from_email="me@knk.com", to_email="t@y.com", subject="제목",
                           body="평문 대체", from_name="김정락", cc="c@y.com",
                           bcc="bcc1@y.com, bcc2@y.com", html="<b>서식 본문</b>")
check("발송 성공", ok is True, msg)
m = captured.get("msg")
check("Bcc 헤더 설정됨", m and m["Bcc"] == "bcc1@y.com, bcc2@y.com", m["Bcc"] if m else "")
types = [p.get_content_type() for p in m.walk()] if m else []
check("HTML 대체 파트 포함", "text/html" in types, str(types))
check("평문 파트 포함(대체)", "text/plain" in types)
check("To/Cc 헤더 정상", m and m["To"] == "t@y.com" and m["Cc"] == "c@y.com")
# HTML 발송 위생: 스크립트 제거 확인
safe = MS.sanitize_html_for_view("<b>hi</b><script>bad()</script>", 0, [])
check("발신 HTML 위생처리(script 제거)", "<b>" in safe and "<script" not in safe.lower())

print("\n" + "=" * 60)
print(f"결과: PASS={PASS}  FAIL={FAIL}")
print("=" * 60)
sys.exit(1 if FAIL else 0)
