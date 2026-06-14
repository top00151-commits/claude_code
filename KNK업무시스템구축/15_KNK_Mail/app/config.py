# -*- coding: utf-8 -*-
"""KNK Eum MAIL — 독립 앱 설정 (단일 관리 지점).

WORKS와 완전 분리: 별도 DB(mail.db)·별도 첨부 저장소·별도 세션.
모든 경로/환경값은 여기서만 정의한다.
"""
from __future__ import annotations
import os

# ── 경로 ──────────────────────────────────────────────
APP_DIR = os.path.dirname(os.path.abspath(__file__))          # 15_KNK_Mail/app
PROJECT_DIR = os.path.dirname(APP_DIR)                          # 15_KNK_Mail
DATA_DIR = os.environ.get("KNK_MAIL_DATA", os.path.join(PROJECT_DIR, "data"))
TEMPLATES_DIR = os.path.join(APP_DIR, "templates")
STATIC_DIR = os.path.join(APP_DIR, "static")
UPLOADS_DIR = os.path.join(DATA_DIR, "mail_uploads")           # 일반 첨부
LARGE_DIR = os.path.join(DATA_DIR, "mail_large")               # 대용량 첨부(토큰 다운로드)

# ── 별도 DB (WORKS와 무관) ────────────────────────────
DB_PATH = os.environ.get("KNK_MAIL_DB", os.path.join(DATA_DIR, "mail.db"))

# ── 세션 ──────────────────────────────────────────────
# max_age 없음 = 세션 쿠키(브라우저 닫으면 만료) — WORKS/메신저 인증 표준과 동일
SESSION_SECRET = os.environ.get("KNK_MAIL_SESSION_SECRET", "knk-mail-dev-secret-change-me")
SESSION_COOKIE = "knk_mail_session"

# ── 메신저 SSO (메일 전용 audience) ───────────────────
#   메신저가 메일을 새 소비자(SP)로 등록해야 함: audience='knk-mail',
#   redirect_uri allowlist = https://mail.knknara.co.kr/sso/land
SSO_AUDIENCE = os.environ.get("KNK_MAIL_SSO_AUDIENCE", "knk-mail")

# 이 앱의 외부 공개 주소 (SSO redirect_uri 빌드용). 운영 = https://mail.knknara.co.kr
PUBLIC_BASE = os.environ.get("KNK_MAIL_PUBLIC_BASE", "http://127.0.0.1:8201").rstrip("/")

# 개발용 로컬 로그인 우회 (운영 절대 금지) — 기본 off. KNK_MAIL_DEV_LOGIN=1 일 때만.
DEV_LOGIN = os.environ.get("KNK_MAIL_DEV_LOGIN", "0") == "1"

# 세션 쿠키 Secure(운영=1). 미들웨어가 사용.
HTTPS_ONLY = os.environ.get("KNK_MAIL_HTTPS_ONLY", "0") == "1"

# ── fail-closed: 운영(HTTPS_ONLY=1)에서 세션키가 비었거나 git 기본값이면 기동 거부 ──
#   .env 미로드 등으로 SESSION_SECRET 이 공개 기본값으로 떨어지면 누구나 세션 위조 가능 →
#   조용히 뜨지 말고 즉시 실패(인증 우회 방지).
if HTTPS_ONLY and (not SESSION_SECRET or SESSION_SECRET == "knk-mail-dev-secret-change-me"):
    raise RuntimeError(
        "KNK_MAIL_SESSION_SECRET 가 운영에서 미설정/기본값입니다. "
        "강력한 무작위 값으로 설정하세요(.env 로드 확인). 공개 기본키로는 기동 거부.")
if HTTPS_ONLY and PUBLIC_BASE.startswith("http://127.0.0.1"):
    raise RuntimeError(
        "KNK_MAIL_PUBLIC_BASE 가 운영에서 localhost 입니다(.env 미로드 의심). "
        "https://mail.knknara.co.kr 로 설정하세요.")

# ── 표시 ──────────────────────────────────────────────
APP_NAME = "KNK Eum MAIL"
THEME_COLOR = "#A5282C"


def ensure_dirs():
    """데이터/첨부 폴더 보장 (없으면 생성)."""
    for d in (DATA_DIR, UPLOADS_DIR, LARGE_DIR):
        os.makedirs(d, exist_ok=True)
