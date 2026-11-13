# -*- coding: utf-8 -*-
"""보내는 메일의 필수 헤더 검증 (2026-11-13 스팸 분류 사고).

사고: 대표가 WORKS 메일로 보낸 메일이 지메일에서 **스팸함**으로 들어갔다.
원인: 우리가 만든 메시지에 **Date 도 Message-ID 도 없었다.**
      · EmailMessage 는 From/To/Subject/Content-* 만 만든다
      · smtplib.send_message 는 **Resent-Date 만** 다룬다 — 일반 Date·Message-ID 를 안 넣는다
      · Date 는 RFC 5322 **필수** 헤더다 → 없으면 '규격 미달'로 스팸 신호
      (같은 도메인에서 하이웍스 웹메일로 보낸 메일은 정상 수신 → 도메인 문제 아니었음)

증명할 것
  ① 실제 발송 경로(_smtp_send)가 Date·Message-ID 를 찍는다
  ② Date 가 진짜 날짜로 읽히고 시간대(한국)를 달고 있다
  ③ Message-ID 가 보내는 도메인으로 만들어진다 — <...@knknara.co.kr>
  ④ 서식 본문(HTML)·첨부가 있어도 그대로 찍힌다
  ⑤ 옛 경로(send_mail)도 같이 찍는다
  ⑥ ⭐대조군 — 안 찍으면 이 시험이 정말로 잡아내는가 (시험이 눈뜬장님이 아님을 증명)
  ⑦ (회귀) Bcc 는 전송 메시지에서 빠지고, 봉투 수신자로만 쓰인다
"""
import os
import smtplib
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from cryptography.fernet import Fernet  # noqa: E402
os.environ.setdefault("KNK_MAIL_KEY", Fernet.generate_key().decode())

from email.message import EmailMessage          # noqa: E402
from email.utils import parsedate_to_datetime   # noqa: E402

from app import mail_send as ms                 # noqa: E402

PASS = FAIL = 0

FROM = "tester@knknara.co.kr"          # 가짜 — 실제 계정 아님
TO = "someone@example.com"
FAKE_PW = "FAKE-not-a-real-password-0000"


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS]", name)
    else:
        FAIL += 1
        print("  [FAIL]", name, extra)


class FakeSMTP:
    """진짜로 보내지 않고, 보내려던 메시지를 붙잡아 둔다."""
    seen = {}

    def __init__(self, host, port, context=None, timeout=None):
        FakeSMTP.seen = {"host": host, "port": port}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def login(self, user, pw):
        FakeSMTP.seen["login_user"] = user

    def send_message(self, msg):
        # 진짜 smtplib 와 같이 Bcc 는 봉투로 옮기고 헤더에선 지운다
        FakeSMTP.seen["bcc_envelope"] = msg.get("Bcc")
        del msg["Bcc"]
        FakeSMTP.seen["msg"] = msg


real_ssl = smtplib.SMTP_SSL
smtplib.SMTP_SSL = FakeSMTP
try:
    # ════════════ §1 실제 발송 경로가 헤더를 찍는가 ════════════
    print("\n§1 실제 발송 경로(_smtp_send) 가 Date·Message-ID 를 찍는다")
    ok, msg_txt = ms._smtp_send("smtps.hiworks.com", 465, FROM, FAKE_PW,
                                FROM, TO, "제목 시험", "본문 시험")
    check("발송 호출 성공", ok, msg_txt)
    m = FakeSMTP.seen.get("msg")
    check("메시지를 붙잡았다", m is not None)
    check("⭐Date 헤더가 있다", bool(m and m.get("Date")), m and m.get("Date"))
    check("⭐Message-ID 헤더가 있다", bool(m and m.get("Message-ID")), m and m.get("Message-ID"))

    print("\n§2 Date 가 진짜 날짜로 읽히고 시간대를 달고 있다")
    d = None
    try:
        d = parsedate_to_datetime(m.get("Date"))
        check("Date 가 날짜로 해석된다", True)
    except Exception as e:
        check("Date 가 날짜로 해석된다", False, "%s: %s" % (type(e).__name__, e))
    check("Date 에 시간대(offset)가 붙어 있다", bool(d and d.utcoffset() is not None),
          d and str(d.utcoffset()))
    check("Date 시간대가 한국(+9)이다",
          bool(d and d.utcoffset() is not None and d.utcoffset().total_seconds() == 9 * 3600),
          d and str(d.utcoffset()))

    print("\n§3 Message-ID 가 보내는 도메인으로 만들어진다")
    mid = (m.get("Message-ID") or "")
    check("<...> 모양이다", mid.startswith("<") and mid.endswith(">"), mid)
    check("보내는 도메인(knknara.co.kr)으로 끝난다", mid.rstrip(">").endswith("@knknara.co.kr"), mid)
    check("Message-ID 가 매번 달라진다",
          mid != ms.make_msgid(domain="knknara.co.kr"))

    print("\n§4 서식 본문(HTML)·첨부가 있어도 그대로 찍힌다")
    ms._smtp_send("smtps.hiworks.com", 465, FROM, FAKE_PW, FROM, TO,
                  "서식", "본문", html="<p>안녕하세요</p>",
                  attachments=[("a.txt", b"hello", "text/plain")])
    m2 = FakeSMTP.seen.get("msg")
    check("HTML+첨부에도 Date 있음", bool(m2 and m2.get("Date")))
    check("HTML+첨부에도 Message-ID 있음", bool(m2 and m2.get("Message-ID")))
    check("HTML 대체 본문이 살아 있다", m2 is not None and m2.is_multipart())

    print("\n§5 옛 경로(send_mail)도 같이 찍는다")
    ms.send_mail(FROM, FAKE_PW, TO, "제목", "본문")
    m3 = FakeSMTP.seen.get("msg")
    check("send_mail 도 Date 있음", bool(m3 and m3.get("Date")), m3 and m3.get("Date"))
    check("send_mail 도 Message-ID 있음", bool(m3 and m3.get("Message-ID")))

    print("\n§6 ⭐대조군 — 안 찍으면 이 시험이 정말 잡아내는가")
    bare = EmailMessage()
    bare["From"] = FROM
    bare["To"] = TO
    bare["Subject"] = "제목"
    bare.set_content("본문")
    check("(대조군) 헤더를 안 찍으면 Date 가 없다", bare.get("Date") is None)
    check("(대조군) 헤더를 안 찍으면 Message-ID 가 없다", bare.get("Message-ID") is None)
    # 진짜 smtplib 이 보태 주지 않는다는 것도 함께 못박는다
    import inspect
    src = inspect.getsource(smtplib.SMTP.send_message)
    check("(근거) smtplib.send_message 는 일반 Date 를 넣지 않는다",
          not any(("'Date'" in ln or '"Date"' in ln) and "Resent" not in ln
                  for ln in src.splitlines()))
    check("(근거) smtplib.send_message 는 Message-ID 를 넣지 않는다",
          "Message-ID" not in src and "make_msgid" not in src)
    ms._stamp_required_headers(bare, FROM)
    check("찍고 나면 Date 가 생긴다", bare.get("Date") is not None)
    check("찍고 나면 Message-ID 가 생긴다", bare.get("Message-ID") is not None)
    # 이미 있으면 덮어쓰지 않는다(중복 헤더 금지)
    before = bare.get("Date")
    ms._stamp_required_headers(bare, FROM)
    check("두 번 찍어도 덮어쓰거나 중복되지 않는다",
          bare.get("Date") == before and len(bare.get_all("Date") or []) == 1,
          len(bare.get_all("Date") or []))

    print("\n§7 (회귀) Bcc 는 전송 메시지에서 빠진다")
    ms._smtp_send("smtps.hiworks.com", 465, FROM, FAKE_PW, FROM, TO,
                  "제목", "본문", bcc="hidden@example.com")
    m4 = FakeSMTP.seen.get("msg")
    check("Bcc 가 봉투 수신자로 쓰였다",
          (FakeSMTP.seen.get("bcc_envelope") or "") == "hidden@example.com")
    check("Bcc 헤더는 전송 메시지에서 지워졌다", m4 is not None and m4.get("Bcc") is None)
    check("Bcc 가 있어도 Date·Message-ID 는 그대로", bool(m4 and m4.get("Date") and m4.get("Message-ID")))

    print("\n§8 (회귀) 로그인 계정과 보내는 주소가 달라도 된다")
    ms._smtp_send("smtps.hiworks.com", 465, "relay-user", FAKE_PW,
                  FROM, TO, "제목", "본문")
    check("로그인은 발송망 계정으로", FakeSMTP.seen.get("login_user") == "relay-user",
          FakeSMTP.seen.get("login_user"))
    check("보내는 주소는 From 그대로",
          (FakeSMTP.seen.get("msg") or {}).get("From", "").endswith("<%s>" % FROM)
          or (FakeSMTP.seen.get("msg") or {}).get("From") == FROM,
          (FakeSMTP.seen.get("msg") or {}).get("From"))

    print("\n§9 ⭐비밀번호가 메시지 어디에도 섞이지 않는다")
    blob = str(FakeSMTP.seen.get("msg"))
    check("전송 메시지에 비밀번호 없음", FAKE_PW not in blob)
finally:
    smtplib.SMTP_SSL = real_ssl

print("\n" + "=" * 56)
print("  통과 %d / 실패 %d" % (PASS, FAIL))
print("=" * 56)
sys.exit(1 if FAIL else 0)
