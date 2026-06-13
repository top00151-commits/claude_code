# -*- coding: utf-8 -*-
"""
KNK Mail 파이프라인 검증 (받기/보내기) — 2026-06-13 대표 지시
====================================================================
운영(NAS)에서 실제로 도는 그 코드(app.mail_store / app.mail_send)를
로컬 임시 SQLite 로 그대로 호출해 '여러 상황'을 자동 통과시켜 검증.
- 실제 인터넷 메일을 보내거나 받지 않음(스팸·운영DB 오염 0).
- 보내기는 smtplib.SMTP_SSL 을 가짜로 갈아끼워(monkeypatch) 메일 조립만 검증.
- AI 분류는 운영에서 검증됨(로컬 키는 stale 가능) → run_ai=False 로 구조만 결정적 검증,
  카테고리 질의는 수동 UPDATE 로 모사.
"""
import os, sys, sqlite3, tempfile, traceback

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
APP_PARENT = os.path.abspath(os.path.join(HERE, "..", "..", "01_HAIST_WORKS"))
sys.path.insert(0, APP_PARENT)

# 암호화 키: 실제 data/.mail_key 를 만들지 않도록 테스트용 키를 env 로 주입
from cryptography.fernet import Fernet
os.environ["KNK_MAIL_KEY"] = Fernet.generate_key().decode()

from app import database as DB           # SCHEMA 재사용
from app import mail_store as MS
from app import mail_send as SEND

PASS, FAIL = 0, 0
def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}" + (f"  ({extra})" if extra else ""))
    else:
        FAIL += 1
        print(f"  [FAIL] {name}" + (f"  ({extra})" if extra else ""))

def section(t):
    print("\n" + "=" * 64 + f"\n{t}\n" + "=" * 64)

# ── 임시 DB 구성 ──────────────────────────────────────────────────────
con = sqlite3.connect(":memory:")
con.row_factory = sqlite3.Row
con.execute("PRAGMA foreign_keys = ON")
con.executescript(DB.SCHEMA)

# 운영 현실 모사: '김정락' 동명 계정 2개(시드 kjr + 대표 실로그인), 베트남 직원 1명
con.execute("INSERT INTO users(id,name,login_id,password,role,is_active,lang) "
            "VALUES(1,'김정락','kjr','x','ceo',1,'ko')")          # 시드(낮은 id)
con.execute("INSERT INTO users(id,name,login_id,password,role,is_active,lang) "
            "VALUES(7,'김정락','ceo_kim','x','ceo',1,'ko')")       # 대표 실 로그인(높은 id)
con.execute("INSERT INTO users(id,name,login_id,password,role,is_active,lang) "
            "VALUES(3,'Nguyen Van A','vn01','x','member',1,'vi')")  # 베트남
con.commit()

# ════════════════════════════════════════════════════════════════════
section("받기(RECEIVING) — 원문(MIME) 파싱 + 저장")
# ════════════════════════════════════════════════════════════════════

# 시나리오 1: 한국어 일반 plain
# (실제 메일은 비ASCII 헤더를 RFC2047 로 인코딩해 보냄 — 그 형태로 검증)
from email.header import Header as _Hdr
_fn1 = _Hdr("홍길동", "utf-8").encode()
_sj1 = _Hdr("안녕하세요 문의드립니다", "utf-8").encode()
raw1 = (f"From: {_fn1} <hong@dreamtech.co.kr>\r\n"
        "To: test@knk-mailtest.com\r\n"
        f"Subject: {_sj1}\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n\r\n"
        "안녕하세요, 제품 카탈로그 한 부 요청드립니다. 감사합니다.")
p1 = MS.parse_raw_email(raw1)
check("S1 파싱: from_email", p1.get("from_email") == "hong@dreamtech.co.kr", p1.get("from_email"))
check("S1 파싱: from_name", p1.get("from_name") == "홍길동", p1.get("from_name"))
check("S1 파싱: to_email", p1.get("to_email") == "test@knk-mailtest.com", p1.get("to_email"))
check("S1 파싱: subject(한글)", p1.get("subject") == "안녕하세요 문의드립니다", p1.get("subject"))
check("S1 파싱: 본문 보존", "카탈로그" in (p1.get("text") or ""))
mid1, own1 = MS.store_inbound(con, to_email=p1["to_email"], from_email=p1["from_email"],
                              from_name=p1["from_name"], subject=p1["subject"],
                              text=p1["text"], html=p1["html"], cc=p1["cc"],
                              size=len(raw1), run_ai=False)
check("S1 저장: mail_id 발급", bool(mid1), f"id={mid1}")
check("S1 저장: 수신자=대표(동명 중 낮은 id=1)", own1 == 1, f"owner={own1}")

# 시나리오 2: 견적 요청 HTML
raw2 = ("From: sales@abc-corp.com\r\nTo: test@knk-mailtest.com\r\n"
        "Subject: 견적 요청 - 검사장비\r\nContent-Type: text/html; charset=utf-8\r\n\r\n"
        "<html><body><p>KNK-INS-300 <b>견적</b>을 요청합니다.</p>"
        "<script>alert(1)</script></body></html>")
p2 = MS.parse_raw_email(raw2)
check("S2 HTML→text 추출", "견적" in (p2.get("text") or ""), repr((p2.get("text") or "")[:40]))
check("S2 script 제거(XSS 원문정리)", "alert(1)" not in (p2.get("text") or ""))
check("S2 html 원문 보관", "<b>" in (p2.get("html") or ""))
mid2, _ = MS.store_inbound(con, to_email=p2["to_email"], from_email=p2["from_email"],
                           subject=p2["subject"], text=p2["text"], html=p2["html"],
                           cc=p2["cc"], run_ai=False)

# 시나리오 3: 발주 + 참조(Cc)
raw3 = ("From: order@buyer.co.kr\r\nTo: test@knk-mailtest.com\r\n"
        "Cc: manager@buyer.co.kr, account@buyer.co.kr\r\n"
        "Subject: 발주의 건\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n"
        "자동화 설비 1식 발주합니다.")
p3 = MS.parse_raw_email(raw3)
check("S3 Cc 파싱", "manager@buyer.co.kr" in (p3.get("cc") or ""), p3.get("cc"))
mid3, _ = MS.store_inbound(con, to_email=p3["to_email"], from_email=p3["from_email"],
                           subject=p3["subject"], text=p3["text"], cc=p3["cc"], run_ai=False)
row3 = MS.get_mail(con, mid3, 1)
check("S3 저장 Cc 보존", row3 and "account@buyer.co.kr" in (row3.get("cc") or ""))

# 시나리오 4: 세금계산서 multipart + 첨부(PDF) — 파일명은 RFC2047 인코딩(실제 메일 형태)
_fn4 = _Hdr("세금계산서_2026.pdf", "utf-8").encode()
_sj4 = _Hdr("세금계산서 송부", "utf-8").encode()
raw4 = (
    "From: tax@vendor.co.kr\r\nTo: test@knk-mailtest.com\r\n"
    f"Subject: {_sj4}\r\n"
    "MIME-Version: 1.0\r\n"
    "Content-Type: multipart/mixed; boundary=BB\r\n\r\n"
    "--BB\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n"
    "세금계산서 첨부합니다.\r\n"
    f"--BB\r\nContent-Type: application/pdf; name=\"{_fn4}\"\r\n"
    f"Content-Disposition: attachment; filename=\"{_fn4}\"\r\n\r\n"
    "%PDF-1.4 fake\r\n--BB--\r\n")
p4 = MS.parse_raw_email(raw4)
_a4 = p4.get("attachments") or []
check("S4 첨부 파일명 인식", len(_a4) == 1 and _a4[0].get("filename") == "세금계산서_2026.pdf",
      str([a.get("filename") for a in _a4]))
check("S4 본문에 첨부 표기", "[첨부 1개:" in (p4.get("text") or ""), repr((p4.get("text") or "")[-40:]))
check("S4 본문 텍스트 보존", "세금계산서 첨부" in (p4.get("text") or ""))

# 시나리오 5: 베트남어 → 베트남 직원(alias 매핑)
con.execute("INSERT INTO mail_aliases(address,user_id) VALUES('vn@knk-mailtest.com',3)")
con.commit()
raw5 = ("From: kh@khachhang-vn.com\r\nTo: vn@knk-mailtest.com\r\n"
        "Subject: Yêu cầu báo giá\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n"
        "Kính gửi KNK, chúng tôi muốn nhận báo giá.")
p5 = MS.parse_raw_email(raw5)
mid5, own5 = MS.store_inbound(con, to_email=p5["to_email"], from_email=p5["from_email"],
                              subject=p5["subject"], text=p5["text"], run_ai=False)
check("S5 alias 매핑→베트남 직원(id=3)", own5 == 3, f"owner={own5}")
check("S5 베트남어 본문 보존", "báo giá" in (p5.get("text") or ""))

# 시나리오 6: multipart/alternative (text + html) → text 우선
raw6 = ("From: a@b.com\r\nTo: test@knk-mailtest.com\r\nSubject: alt\r\n"
        "MIME-Version: 1.0\r\nContent-Type: multipart/alternative; boundary=XX\r\n\r\n"
        "--XX\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nPLAIN_BODY_HERE\r\n"
        "--XX\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<p>HTML_BODY</p>\r\n--XX--\r\n")
p6 = MS.parse_raw_email(raw6)
check("S6 멀티파트 text 우선", (p6.get("text") or "").strip().startswith("PLAIN_BODY_HERE"),
      repr((p6.get("text") or "")[:30]))

# 시나리오 7: MIME 인코딩 제목(=?UTF-8?B?…?=)
import base64
enc = base64.b64encode("한글제목 테스트".encode("utf-8")).decode()
raw7 = (f"From: x@y.com\r\nTo: test@knk-mailtest.com\r\nSubject: =?UTF-8?B?{enc}?=\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n\r\nbody")
p7 = MS.parse_raw_email(raw7)
check("S7 인코딩 제목 디코드", p7.get("subject") == "한글제목 테스트", p7.get("subject"))

# 시나리오 8: 깨진/헤더 누락 메일(견고성) — 조용히 버리지 않고 기본 수신자로 저장
raw8 = "random text with no headers at all\r\nstill no headers"
p8 = MS.parse_raw_email(raw8)
check("S8 깨진 메일도 dict 반환(예외 X)", isinstance(p8, dict))
mid8, own8 = MS.store_inbound(con, to_email=p8.get("to_email", ""), from_email=p8.get("from_email", ""),
                              subject=p8.get("subject", ""), text=p8.get("text", ""), run_ai=False)
check("S8 to 비어도 기본 수신자로 저장(미손실)", bool(mid8) and own8 == 1, f"id={mid8} owner={own8}")
r8 = MS.get_mail(con, mid8, 1)
check("S8 제목 폴백 '(제목 없음)'", r8 and r8.get("subject") == "(제목 없음)", r8 and r8.get("subject"))

# 시나리오 9: 수신자 매핑 우선순위 — mail_default_user_id(대표 실로그인 id=7)
con.execute("INSERT INTO app_settings(key,value) VALUES('mail_default_user_id','7')")
con.commit()
mid9, own9 = MS.store_inbound(con, to_email="unknown@knk-mailtest.com", from_email="z@z.com",
                              subject="미지정 주소", text="hi", run_ai=False)
check("S9 기본수신자 지정 시 그 계정(id=7)으로", own9 == 7, f"owner={own9}")
# alias 가 default 보다 우선인지 재확인
mid9b, own9b = MS.store_inbound(con, to_email="vn@knk-mailtest.com", from_email="z@z.com",
                                subject="alias 우선", text="hi", run_ai=False)
check("S9 alias > 기본수신자 우선순위", own9b == 3, f"owner={own9b}")

# ════════════════════════════════════════════════════════════════════
section("조회/상태 — 받은편지함·미읽음·분류·읽음·별표·삭제·소유권")
# ════════════════════════════════════════════════════════════════════
# 분류 질의 검증용으로 카테고리 수동 세팅(AI 자체는 운영 검증)
con.execute("UPDATE mail_messages SET category='견적' WHERE id=?", (mid2,))
con.execute("UPDATE mail_messages SET category='발주' WHERE id=?", (mid3,))
con.commit()

inbox = MS.list_inbox(con, 1)
check("받은편지함 목록(대표 id=1)", len(inbox) >= 4, f"count={len(inbox)}")
unread = MS.count_unread(con, 1)
check("미읽음 카운트 = 전체(아직 안읽음)", unread == len(inbox), f"unread={unread}")

cc = MS.category_counts(con, 1)
check("분류별 카운트에 견적 포함", cc.get("견적", 0) == 1, str(cc))
filtered = MS.list_inbox(con, 1, category="발주")
check("분류 필터(발주)만 반환", all(True for _ in filtered) and len(filtered) == 1, f"count={len(filtered)}")

MS.mark_read(con, mid1, 1)
check("읽음 처리 후 미읽음 감소", MS.count_unread(con, 1) == unread - 1)

st = MS.toggle_star(con, mid1, 1)
check("별표 토글 ON", st == 1)
st2 = MS.toggle_star(con, mid1, 1)
check("별표 토글 OFF", st2 == 0)

# 소유권 강제: 대표(1) 메일을 베트남(3)이 조회 → None
check("소유권 차단: 남의 메일 조회 불가", MS.get_mail(con, mid1, 3) is None)

# 소프트 삭제 후 목록/카운트에서 제외
before = len(MS.list_inbox(con, 1))
MS.soft_delete(con, mid1, 1)
check("삭제 후 목록에서 제외", len(MS.list_inbox(con, 1)) == before - 1)
check("삭제 메일은 조회도 불가", MS.get_mail(con, mid1, 1) is None)

# ════════════════════════════════════════════════════════════════════
section("보내기(SENDING) — 암호화·설정·메일 조립(실발송 X, SMTP 가짜)")
# ════════════════════════════════════════════════════════════════════
# 1) 암호화 라운드트립(A안 키)
secret = "cf_api_token_xxx_secret_value"
enc_pw = SEND.encrypt(secret)
check("Fernet 암호화/복호화 일치", SEND.decrypt(enc_pw) == secret)
check("암호문은 평문과 다름(평문 저장 X)", enc_pw and enc_pw != secret)

# 2) 보내기 설정 저장/조회
SEND.save_send_config(con, "smtp.mx.cloudflare.net", "465", "api_token", secret)
con.commit()
cfg = SEND.get_send_config(con)
check("보내기 설정 저장·복호화", cfg and cfg["host"] == "smtp.mx.cloudflare.net"
      and cfg["user"] == "api_token" and cfg["password"] == secret, str({k: cfg[k] for k in ("host", "port", "user")}) if cfg else "None")
check("시스템 발송 준비됨", SEND.system_send_ready(con) is True)

# 3) SMTP 를 가짜로 갈아끼워 '조립된 메일'만 검증 (실제 발송 안 함)
captured = {}
class FakeSMTP:
    def __init__(self, host, port, **kw): captured["host"] = host; captured["port"] = port
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def login(self, user, pw): captured["login_user"] = user; captured["login_pass"] = pw
    def send_message(self, msg): captured["msg"] = msg
SEND.smtplib.SMTP_SSL = FakeSMTP

ok, msg = SEND.send_system(con, from_email="test@knk-mailtest.com",
                           to_email="customer@example.com", subject="견적 회신",
                           body="견적서 보내드립니다.", from_name="KNK 영업",
                           cc="cc@example.com",
                           attachments=[("quote.pdf", b"%PDF fake", "application/pdf")])
check("send_system 성공 반환", ok is True, msg)
m = captured.get("msg")
check("SMTP 로그인 계정 = api_token", captured.get("login_user") == "api_token", captured.get("login_user"))
check("로그인 비번 = 복호화된 토큰", captured.get("login_pass") == secret)
check("접속 호스트/포트", captured.get("host") == "smtp.mx.cloudflare.net" and captured.get("port") == 465,
      f"{captured.get('host')}:{captured.get('port')}")
check("From = 보내는 직원 주소", m and m["From"] and "test@knk-mailtest.com" in m["From"], m["From"] if m else "")
check("To = 수신자", m and m["To"] == "customer@example.com")
check("Cc 반영", m and m["Cc"] == "cc@example.com")
check("Subject 반영", m and m["Subject"] == "견적 회신")
# 첨부 확인
fnames = [pp.get_filename() for pp in (m.walk() if m else []) if pp.get_filename()]
check("첨부 파일 포함", "quote.pdf" in fnames, str(fnames))

# 4) 잘못된 주소 거부
bad_ok, bad_msg = SEND.send_system(con, from_email="test@knk-mailtest.com",
                                   to_email="not-an-email", subject="x", body="x")
check("잘못된 수신자 주소 거부", bad_ok is False, bad_msg)

# 5) 보낸편지함 기록 + 조회
oid = MS.store_outbound(con, user_id=7, from_email="test@knk-mailtest.com",
                        to_email="customer@example.com", subject="견적 회신",
                        body="본문", from_name="KNK 영업")
con.commit()
sent = MS.list_sent(con, 7)
check("보낸편지함에 1건 기록", MS.count_sent(con, 7) == 1 and len(sent) == 1, f"count={MS.count_sent(con,7)}")
check("보낸편지함 direction=out 분리(받은함엔 안 섞임)",
      all(r["id"] != oid for r in MS.list_inbox(con, 7)))

# ════════════════════════════════════════════════════════════════════
section("버그 후보 확증 — default_owner 의 username 컬럼")
# ════════════════════════════════════════════════════════════════════
try:
    con.execute("SELECT id FROM users WHERE username='kjr'")
    print("  [??] username 컬럼이 존재함 — 버그 아님")
except sqlite3.OperationalError as e:
    check("default_owner 1순위 쿼리(username='kjr')는 항상 실패함", "no such column" in str(e).lower(), str(e))
    print("       → try/except 로 가려져 2순위(name='김정락')로 폴백.")
    print("       → 동명 계정 다수면 낮은 id 로 감(z383 원인). login_id='kjr' 로 고쳐야 의도대로 동작.")

# 폴백 동작 자체는 정상(미손실)인지 확인: mail_default_user_id 제거 후
con.execute("DELETE FROM app_settings WHERE key='mail_default_user_id'")
con.commit()
_, own_fb = MS.store_inbound(con, to_email="zzz@knk-mailtest.com", from_email="a@a.com",
                             subject="fallback", text="x", run_ai=False)
check("기본수신자 미지정 시에도 메일 미손실(폴백 저장)", own_fb in (1, 7), f"owner={own_fb}")

print("\n" + "=" * 64)
print(f"결과: PASS={PASS}  FAIL={FAIL}")
print("=" * 64)
sys.exit(1 if FAIL else 0)
