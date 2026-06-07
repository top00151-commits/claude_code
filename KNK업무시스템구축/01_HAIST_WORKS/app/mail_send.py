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
import ssl
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, parseaddr

SMTP_HOST = os.environ.get("KNK_SMTP_HOST", "smtps.hiworks.com")
SMTP_PORT = int(os.environ.get("KNK_SMTP_PORT", "465"))


def _fernet():
    key = (os.environ.get("KNK_MAIL_KEY") or "").strip()
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
