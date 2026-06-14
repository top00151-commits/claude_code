# -*- coding: utf-8 -*-
"""KNK Eum MAIL — 독립 DB 계층 (별도 mail.db).

WORKS DB와 완전 분리. 메일 8종 테이블 + app_settings + users(직원명부 미러).
users 미러는 메신저에서 동기화(sync). mail_messages.user_id 는 이 미러를 참조.
로직 모듈(mail_store/send/fetch)은 연결(cursor)을 인자로 받으므로 그대로 재사용.
"""
from __future__ import annotations
import sqlite3
from contextlib import contextmanager

from . import config

# ─── 스키마 ───────────────────────────────────────────────────────
SCHEMA = """
PRAGMA journal_mode = WAL;

-- 설정 (mail_send/fetch 설정값 등) — WORKS get_setting/set_setting 호환(app_settings)
CREATE TABLE IF NOT EXISTS app_settings (
    key         TEXT PRIMARY KEY,
    value       TEXT,
    description TEXT,
    updated_at  TEXT DEFAULT (datetime('now','localtime')),
    updated_by  INTEGER
);

-- 직원명부 미러 (메신저 동기화) — 메일 소유자/권한 판단의 기준
-- upsert_user_from_payload(sso_client) 가 쓰는 컬럼을 모두 보유
CREATE TABLE IF NOT EXISTS users (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_no      TEXT,                 -- 사번 (메신저 마스터)
    login_id         TEXT,                 -- = 사번
    password         TEXT,                 -- SSO 전용(자체로그인 미사용 sentinel)
    name             TEXT,
    name_en          TEXT,
    name_vi          TEXT,
    email            TEXT,
    phone            TEXT,
    dept_code        TEXT,
    team_id          INTEGER,
    rank             TEXT,
    role             TEXT DEFAULT 'member',-- member/admin/ceo
    entity           TEXT,                 -- KOR/VN
    is_active        INTEGER DEFAULT 1,
    password_version INTEGER DEFAULT 1,
    lang             TEXT DEFAULT 'ko',
    created_at       TEXT DEFAULT (datetime('now','localtime'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_empno ON users(employee_no);

-- ─── 메일 본문/첨부 ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mail_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
    direction   TEXT DEFAULT 'in',          -- in/out/draft
    from_email  TEXT,
    from_name   TEXT,
    to_email    TEXT,
    cc          TEXT,
    bcc         TEXT,
    subject     TEXT,
    body_text   TEXT,
    body_html   TEXT,
    category    TEXT DEFAULT '일반',
    lang        TEXT,
    summary     TEXT,
    is_read     INTEGER DEFAULT 0,
    is_starred  INTEGER DEFAULT 0,
    is_deleted  INTEGER DEFAULT 0,
    raw_size    INTEGER DEFAULT 0,
    received_at TEXT DEFAULT (datetime('now','localtime')),
    read_at     TEXT,
    deleted_at  TEXT,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_mailmsg_user ON mail_messages(user_id, is_deleted, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_mailmsg_cat  ON mail_messages(user_id, category);

CREATE TABLE IF NOT EXISTS mail_attachments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mail_id     INTEGER REFERENCES mail_messages(id) ON DELETE CASCADE,
    filename    TEXT,
    mime        TEXT,
    size        INTEGER DEFAULT 0,
    path        TEXT,
    content_id  TEXT,
    is_inline   INTEGER DEFAULT 0,
    data        BLOB,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_mailatt_mail ON mail_attachments(mail_id);

-- 수신 주소 → 사용자 매핑
CREATE TABLE IF NOT EXISTS mail_aliases (
    address     TEXT PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);

-- 대용량 첨부 (토큰 다운로드)
CREATE TABLE IF NOT EXISTS mail_large_files (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    token          TEXT UNIQUE NOT NULL,
    filename       TEXT,
    mime           TEXT,
    size           INTEGER DEFAULT 0,
    path           TEXT,
    uploaded_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    download_count INTEGER DEFAULT 0,
    expires_at     TEXT,
    created_at     TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_mlf_token ON mail_large_files(token);

-- 서명
CREATE TABLE IF NOT EXISTS mail_signatures (
    user_id    INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    body       TEXT,
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 가져오기(POP3/IMAP) 계정 + 중복방지
CREATE TABLE IF NOT EXISTS mail_fetch_accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_user_id   INTEGER UNIQUE,
    label           TEXT,
    protocol        TEXT DEFAULT 'pop3',
    host            TEXT,
    port            INTEGER DEFAULT 995,
    use_ssl         INTEGER DEFAULT 1,
    username        TEXT,
    password_enc    TEXT,
    last_uid        INTEGER DEFAULT 0,
    enabled         INTEGER DEFAULT 1,
    last_run        TEXT,
    last_status     TEXT,
    last_count      INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS mail_fetch_seen (
    account_id  INTEGER,
    uidl        TEXT,
    fetched_at  TEXT DEFAULT (datetime('now','localtime')),
    PRIMARY KEY (account_id, uidl)
);

-- 자동분류 규칙
CREATE TABLE IF NOT EXISTS mail_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    match_type TEXT NOT NULL,
    pattern TEXT NOT NULL,
    category TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
"""


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_session():
    conn = get_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """DB 파일·폴더 생성 + 스키마 보장 (idempotent)."""
    config.ensure_dirs()
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def table_names() -> list[str]:
    with db_session() as c:
        return [r["name"] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]


# ─── 설정 (WORKS database.get_setting/set_setting 호환) ───────────
def get_setting(key: str, default: str = "") -> str:
    try:
        with db_session() as c:
            row = c.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
            if row and row["value"] is not None:
                return row["value"]
    except sqlite3.OperationalError:
        pass
    return default


def set_setting(key: str, value: str, user_id: int = None, description: str = None):
    with db_session() as c:
        existing = c.execute("SELECT key FROM app_settings WHERE key=?", (key,)).fetchone()
        if existing:
            if description is not None:
                c.execute("UPDATE app_settings SET value=?, description=?, "
                          "updated_at=datetime('now','localtime'), updated_by=? WHERE key=?",
                          (value, description, user_id, key))
            else:
                c.execute("UPDATE app_settings SET value=?, "
                          "updated_at=datetime('now','localtime'), updated_by=? WHERE key=?",
                          (value, user_id, key))
        else:
            c.execute("INSERT INTO app_settings(key, value, description, updated_by) VALUES(?,?,?,?)",
                      (key, value, description or "", user_id))
