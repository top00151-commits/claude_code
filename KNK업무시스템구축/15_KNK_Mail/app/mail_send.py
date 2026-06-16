"""
v5H228 (2026-05-31 대표 지시) — 직원 본인 하이웍스 계정으로 메일 발송 (A1)

· 외부 그룹웨어(하이웍스) SMTP 발송: smtps.hiworks.com:465 (SSL)
· 직원이 본인 메일주소 + (앱)비밀번호를 1회 등록 → Fernet 으로 암호화 보관
· 발송 시 복호화하여 본인 계정으로 SMTP 로그인 → 보낸사람 = 본인

[보안]
  · 비밀번호 평문 저장 금지 — Fernet 대칭키 암호화. 키는 OS/.env 환경변수 KNK_MAIL_KEY.
  · 하이웍스 "앱 비밀번호"(별도 발급) 사용 권장 — 메인 비번 대신.
  · 각 직원은 하이웍스 [메일>환경설정>기본설정]에서 POP3/SMTP "사용" 활성화 필요.
  · KNK_MAIL_KEY 미설정 시 기능 자동 비활성(안전 폴백).

KNK_MAIL_KEY 생성(1회): python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"
  → 출력값을 .env 의 KNK_MAIL_KEY 에 등록.
"""
from __future__ import annotations

import os
import re
import ssl
import base64
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, parseaddr, make_msgid

SMTP_HOST = os.environ.get("KNK_SMTP_HOST", "smtps.hiworks.com")
SMTP_PORT = int(os.environ.get("KNK_SMTP_PORT", "465"))


def _mail_key() -> str:
    """메일 암호화 키.
    ① 환경변수 KNK_MAIL_KEY (정석·우선) → ② 없으면 데이터 폴더의 키 파일(.mail_key) 1회 자동생성.
    (A안 2026-06-13 대표 결정: 전산 env 없이 자체 생성. 운영 본격전환 땐 env 키로 교체 권장.)
    키 파일은 DB 와 같은 폴더 — git 미포함·DB덤프 미포함, 배포(git pull)에도 보존."""
    key = (os.environ.get("KNK_MAIL_KEY") or "").strip()
    if key:
        return key
    try:
        from cryptography.fernet import Fernet
        try:
            from .database import DB_PATH as _dbp
            data_dir = os.path.dirname(os.path.abspath(_dbp))
        except Exception:
            data_dir = os.path.join(os.getcwd(), "data")
        os.makedirs(data_dir, exist_ok=True)
        kpath = os.path.join(data_dir, ".mail_key")
        if os.path.exists(kpath):
            with open(kpath, "r", encoding="utf-8") as f:
                fk = f.read().strip()
            if fk:
                return fk
        fk = Fernet.generate_key().decode()
        with open(kpath, "w", encoding="utf-8") as f:
            f.write(fk)
        try:
            os.chmod(kpath, 0o600)
        except Exception:
            pass
        return fk
    except Exception:
        return ""


def _fernet():
    key = _mail_key()
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
        return Fernet(key.encode())
    except Exception:
        return None


def mail_available() -> bool:
    """암호화 키가 설정되어 메일 기능을 쓸 수 있는지."""
    return _fernet() is not None


def encrypt(plain: str) -> str:
    f = _fernet()
    if not f or not plain:
        return ""
    return f.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str:
    f = _fernet()
    if not f or not token:
        return ""
    return f.decrypt(token.encode("utf-8")).decode("utf-8")


def is_valid_email(addr: str) -> bool:
    name, mail = parseaddr(addr or "")
    return "@" in mail and "." in mail.split("@")[-1]


# ─── 자격증명 저장/조회 ──────────────────────────────────────────────
def save_creds(c, user_id: int, email: str, password: str = "") -> None:
    """본인 메일 자격증명 저장(암호화). password 가 빈 값이면 기존 비번 유지(이메일만 갱신)."""
    email = (email or "").strip()
    if password:
        enc = encrypt(password)
        c.execute(
            """INSERT INTO user_mail_creds(user_id, smtp_email, smtp_password_enc, updated_at)
               VALUES(?,?,?,datetime('now','localtime'))
               ON CONFLICT(user_id) DO UPDATE SET
                 smtp_email=excluded.smtp_email,
                 smtp_password_enc=excluded.smtp_password_enc,
                 updated_at=excluded.updated_at""",
            (user_id, email, enc),
        )
    else:
        c.execute(
            """INSERT INTO user_mail_creds(user_id, smtp_email, smtp_password_enc, updated_at)
               VALUES(?,?,'',datetime('now','localtime'))
               ON CONFLICT(user_id) DO UPDATE SET
                 smtp_email=excluded.smtp_email,
                 updated_at=excluded.updated_at""",
            (user_id, email),
        )


def get_email(c, user_id: int) -> str:
    row = c.execute("SELECT smtp_email FROM user_mail_creds WHERE user_id=?", (user_id,)).fetchone()
    return (row["smtp_email"] if row else "") or ""


def has_creds(c, user_id: int) -> bool:
    row = c.execute(
        "SELECT 1 FROM user_mail_creds WHERE user_id=? AND smtp_email<>'' AND smtp_password_enc<>''",
        (user_id,),
    ).fetchone()
    return bool(row)


def get_creds(c, user_id: int):
    row = c.execute(
        "SELECT smtp_email, smtp_password_enc FROM user_mail_creds WHERE user_id=?",
        (user_id,),
    ).fetchone()
    if not row or not row["smtp_email"] or not row["smtp_password_enc"]:
        return None
    try:
        pw = decrypt(row["smtp_password_enc"])
    except Exception:
        return None
    if not pw:
        return None
    return {"email": row["smtp_email"], "password": pw}


def delete_creds(c, user_id: int) -> None:
    c.execute("DELETE FROM user_mail_creds WHERE user_id=?", (user_id,))


# ─── 발송 ────────────────────────────────────────────────────────────
def send_mail(from_email: str, password: str, to_email: str, subject: str, body: str,
              from_name: str = "", cc: str = "", attachments=None) -> tuple[bool, str]:
    """본인 계정으로 SMTP 발송. 반환 (성공, 메시지).
    attachments: [(filename, bytes, mime), ...]"""
    if not is_valid_email(from_email):
        return (False, "보내는 메일주소가 올바르지 않습니다.")
    if not is_valid_email(to_email):
        return (False, "받는 메일주소가 올바르지 않습니다.")
    msg = EmailMessage()
    msg["From"] = formataddr((from_name or from_email, from_email))
    msg["To"] = to_email
    if cc.strip():
        msg["Cc"] = cc.strip()
    msg["Subject"] = subject or "(제목 없음)"
    msg.set_content(body or "")
    for fname, data, mime in (attachments or []):
        maintype, _, subtype = (mime or "application/octet-stream").partition("/")
        msg.add_attachment(data, maintype=maintype or "application",
                           subtype=subtype or "octet-stream", filename=fname)
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=30) as s:
            s.login(from_email, password)
            s.send_message(msg)
        return (True, "발송 완료")
    except smtplib.SMTPAuthenticationError:
        return (False, "로그인 실패 — 메일주소/비밀번호 확인. (하이웍스에서 POP3/SMTP 활성화 + 앱 비밀번호 사용)")
    except Exception as e:
        return (False, f"발송 오류: {str(e)[:120]}")


# ─── 시스템 발송 (자체 메일망 — Cloudflare/AWS SMTP) ──────────────────
# 직원 개인 계정이 아닌 '회사 발송망(SMTP)' 으로 보냄. 로그인 계정(시스템)과
# 보내는 주소(From=직원@우리도메인)가 다를 수 있어 _smtp_send 로 분리.
# 설정은 app_settings: mail_send_host / mail_send_port / mail_send_user / mail_send_pass_enc(암호화).
def _setting(c, key: str, default: str = "") -> str:
    try:
        r = c.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
        return ((r["value"] if r else default) or default)
    except Exception:
        return default


# 본문에 붙여넣은/삽입한 이미지는 <img src="data:image/...;base64,..."> 로 박혀 발송된다.
# 지메일·아웃룩 등 일부 수신측은 본문에 박힌 data: 이미지를 보안상 차단(깨져 보임).
# → 발송 직전에 실제 '인라인 첨부(Content-ID)' 로 바꿔 보내면 수신측에서 사진처럼 정상 표시.
_DATA_IMG_RE = re.compile(
    r'(?is)src\s*=\s*(["\'])(data:image/([A-Za-z0-9.+\-]+);base64,([^"\']+))\1'
)


def _inline_data_images(html: str):
    """HTML 안의 data:image base64 들을 cid: 참조로 치환하고,
    인라인 첨부 목록 [(cid_full, subtype, bytes), ...] 을 함께 반환.
    - cid_full 은 <id@host> 형태(add_related 용), HTML 엔 꺾쇠 뺀 cid:id@host 로 넣음.
    - 디코드 실패/빈 데이터는 원본 그대로 둠(데이터 손실 방지)."""
    parts = []

    def _repl(m):
        quote = m.group(1)
        subtype = (m.group(3) or "png").lower()
        if subtype == "jpg":
            subtype = "jpeg"
        b64 = re.sub(r"\s+", "", m.group(4) or "")
        try:
            raw = base64.b64decode(b64)
        except Exception:
            return m.group(0)
        if not raw:
            return m.group(0)
        cid_full = make_msgid()        # <xxxx@host>
        cid = cid_full[1:-1]           # 꺾쇠 제거 → src="cid:xxxx@host"
        parts.append((cid_full, subtype, raw))
        return f"src={quote}cid:{cid}{quote}"

    new_html = _DATA_IMG_RE.sub(_repl, html or "")
    return new_html, parts


def _smtp_send(host: str, port: int, login_user: str, login_pass: str,
               from_email: str, to_email: str, subject: str, body: str,
               from_name: str = "", cc: str = "", attachments=None,
               bcc: str = "", html: str = "") -> tuple[bool, str]:
    """임의 SMTP 서버로 발송. login 계정과 From 이 달라도 됨(시스템 발송망용).
    bcc: 숨은참조(봉투 수신자에 포함, 전송 메시지엔 Bcc 헤더 제거). html: 서식 본문(대체)."""
    if not is_valid_email(from_email):
        return (False, "보내는 메일주소가 올바르지 않습니다.")
    if not is_valid_email(to_email):
        return (False, "받는 메일주소가 올바르지 않습니다.")
    msg = EmailMessage()
    msg["From"] = formataddr((from_name or from_email, from_email))
    msg["To"] = to_email
    if (cc or "").strip():
        msg["Cc"] = cc.strip()
    if (bcc or "").strip():
        msg["Bcc"] = bcc.strip()   # send_message 가 봉투 수신자로 쓰고 헤더는 제거
    msg["Subject"] = subject or "(제목 없음)"
    msg.set_content(body or "")
    if html and html.strip():
        html_send, inline_imgs = _inline_data_images(html)
        msg.add_alternative(html_send, subtype="html")
        if inline_imgs:
            # text/html 대체 파트에 인라인 이미지 부착 →
            # multipart/alternative[text, multipart/related[html, image...]]
            html_part = msg.get_payload()[1]
            for cid_full, subtype, data in inline_imgs:
                html_part.add_related(data, "image", subtype, cid=cid_full)
    for fname, data, mime in (attachments or []):
        maintype, _, subtype = (mime or "application/octet-stream").partition("/")
        msg.add_attachment(data, maintype=maintype or "application",
                           subtype=subtype or "octet-stream", filename=fname)
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, int(port or 465), context=ctx, timeout=30) as s:
            s.login(login_user, login_pass)
            s.send_message(msg)   # To/Cc/Bcc 헤더에서 봉투 수신자 자동 추출 + Bcc 헤더 삭제
        return (True, "발송 완료")
    except smtplib.SMTPAuthenticationError:
        return (False, "발송망 로그인 실패 — 보내기 설정의 계정/비밀번호를 확인하세요.")
    except Exception as e:
        return (False, f"발송 오류: {str(e)[:120]}")


def get_send_config(c):
    """시스템 발송망 설정. 없으면 None."""
    host = _setting(c, "mail_send_host")
    user = _setting(c, "mail_send_user")
    pw_enc = _setting(c, "mail_send_pass_enc")
    if not (host and user and pw_enc):
        return None
    try:
        pw = decrypt(pw_enc)
    except Exception:
        return None
    if not pw:
        return None
    return {"host": host, "port": int(_setting(c, "mail_send_port", "465") or "465"),
            "user": user, "password": pw}


def system_send_ready(c) -> bool:
    """시스템 발송 가능 여부(암호화키 + 호스트·계정·비번 설정)."""
    return mail_available() and get_send_config(c) is not None


def save_send_config(c, host: str, port: str, user: str, password: str) -> None:
    """보내기 설정 저장. password 빈 값이면 기존 비번 유지."""
    def _set(k, v):
        c.execute("INSERT INTO app_settings(key,value) VALUES(?,?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, v))
    _set("mail_send_host", (host or "").strip())
    _set("mail_send_port", str(port or "465").strip())
    _set("mail_send_user", (user or "").strip())
    if password:
        _set("mail_send_pass_enc", encrypt(password))


def send_system(c, from_email: str, to_email: str, subject: str, body: str,
                from_name: str = "", cc: str = "", attachments=None,
                bcc: str = "", html: str = "") -> tuple[bool, str]:
    """회사 발송망(시스템 SMTP)으로 발송. from_email = 보내는 직원의 @우리도메인 주소."""
    cfg = get_send_config(c)
    if not cfg:
        return (False, "보내기 설정이 안 돼 있습니다. 관리자 '메일 보내기 설정'에서 입력하세요.")
    return _smtp_send(cfg["host"], cfg["port"], cfg["user"], cfg["password"],
                      from_email, to_email, subject, body, from_name, cc, attachments,
                      bcc=bcc, html=html)
