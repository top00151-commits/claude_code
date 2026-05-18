"""KNK Messenger — 사내 업무 전용 메신저 (1단계 MVP)

독립 프로젝트. 어느 정도 완성 후 HAIST WORKS와 SSO/사용자 API로 연결 예정.
"""
import os
import re
import sys
import uuid
import json
import base64
import mimetypes
import sqlite3
from datetime import datetime, timezone
from functools import wraps

try:
    from pywebpush import webpush, WebPushException
    PYWEBPUSH_OK = True
except ImportError:
    PYWEBPUSH_OK = False

from flask import (
    Flask, request, session, redirect, url_for,
    render_template, jsonify, abort, g, send_from_directory, make_response,
)
from flask_socketio import SocketIO, emit, join_room as sio_join, leave_room as sio_leave
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "data", "messenger.db")
UPLOAD_DIR = os.path.join(APP_DIR, "data", "uploads")
PORT = int(os.environ.get("KNK_MSG_PORT", "5050"))
# 업로드 한도 — DWG 도면·동영상 대비 500MB 기본. 환경변수로 조정 가능.
# Synology Reverse Proxy / nginx 의 client_max_body_size 도 동시에 키워야 함.
MAX_UPLOAD_MB = int(os.environ.get("KNK_MSG_MAX_UPLOAD_MB", "500"))
MESSAGE_RETENTION_MONTHS = int(os.environ.get("KNK_MSG_RETENTION_MONTHS", "12"))
VAPID_PRIV_PATH = os.path.join(APP_DIR, "data", "vapid_private.pem")
VAPID_CONTACT = os.environ.get("KNK_MSG_CONTACT", "mailto:admin@knknara.co.kr")

# ---------- 운영(인터넷) 배포용 환경변수 ----------
# 운영 모드: KNK_MSG_ENV=production 으로 켜면 보안 헤더·HTTPS 강제·CORS 제한 활성
ENV = os.environ.get("KNK_MSG_ENV", "development").lower()
IS_PRODUCTION = ENV == "production"
# Socket.IO async_mode: 개발=threading(Windows OK), 운영=eventlet(gunicorn worker)
ASYNC_MODE = os.environ.get("KNK_MSG_ASYNC", "threading")
# CORS allowed origins: 콤마 구분. 예) "https://o.knknara.co.kr"
_cors_env = os.environ.get("KNK_MSG_CORS", "*")
CORS_ALLOWED = [o.strip() for o in _cors_env.split(",")] if _cors_env != "*" else "*"
# 하위 경로 배포: KNK_MSG_BASE_PATH=/msg 로 설정하면 앱이 /msg 하위에서 서비스됨.
# 역방향 프록시는 도메인 전체를 그대로 전달하므로 수정 불필요.
# 미설정(빈값) 시 기존처럼 루트(/)에서 동작 — 로컬 개발 하위 호환.
BASE_PATH = os.environ.get("KNK_MSG_BASE_PATH", "").strip().rstrip("/")
# 정적 파일 캐시 (운영은 1일, 개발은 0)
STATIC_CACHE_AGE = int(os.environ.get("KNK_MSG_STATIC_CACHE", "86400" if IS_PRODUCTION else "0"))
# 신뢰할 프록시 수 (nginx 등 리버스 프록시 뒤에서 X-Forwarded-* 신뢰)
TRUSTED_PROXIES = int(os.environ.get("KNK_MSG_PROXIES", "1" if IS_PRODUCTION else "0"))

# --- AI 번역 (Claude Haiku) ---
# ANTHROPIC_API_KEY 가 설정돼 있어야 활성. 없으면 endpoint 가 친절한 안내 응답.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
TRANSLATE_MODEL = os.environ.get("KNK_MSG_TRANSLATE_MODEL", "claude-haiku-4-5")
# 월 비용 한도 (USD). 초과 시 신규 번역 차단 (캐시는 계속 동작).
TRANSLATE_MONTHLY_USD_LIMIT = float(os.environ.get("KNK_MSG_TRANSLATE_USD_LIMIT", "20.0"))
# 데모 모드 — API 키 없이 UI 흐름 테스트용. KNK_MSG_TRANSLATE_MOCK=1 이면 가짜 번역 반환.
_mock_env = os.environ.get("KNK_MSG_TRANSLATE_MOCK", "").strip()
if _mock_env == "0":
    TRANSLATE_MOCK = False  # 명시적 OFF
elif _mock_env == "1":
    TRANSLATE_MOCK = True   # 명시적 ON
else:
    # 자동 분기: 개발 환경에서 API 키 없으면 데모 모드로 자동 활성 (편의)
    # 운영 환경(KNK_MSG_ENV=production)에서는 자동 활성 X — 실수로 데모 번역이 운영에 나가는 것 방지
    TRANSLATE_MOCK = (not ANTHROPIC_API_KEY) and (not IS_PRODUCTION)
# 지원 언어 (UI 옵션 + 시스템 프롬프트 분기)
TRANSLATE_LANGS = {
    "ko": "한국어",
    "vi": "Tiếng Việt (베트남어)",
    "en": "English",
}


def vapid_private_key():
    """VAPID 개인키 파일 경로 반환 — pywebpush.webpush(vapid_private_key=PATH) 에 그대로 사용.
    이전 코드는 PEM 문자열 자체를 반환했는데, 일부 pywebpush 버전이 이를
    raw 32 bytes base64 로 잘못 해석해 ASN.1 파싱 에러 발생. 파일 경로로 넘기면
    pywebpush 가 내부 from_file 로 PEM 정상 로드."""
    if os.path.exists(VAPID_PRIV_PATH):
        return VAPID_PRIV_PATH
    return None


def vapid_public_key_b64u():
    """VAPID 개인키에서 공개키를 raw 65바이트 → base64url 인코딩으로 추출."""
    if not os.path.exists(VAPID_PRIV_PATH):
        return None
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization
        with open(VAPID_PRIV_PATH, "rb") as f:
            priv = serialization.load_pem_private_key(f.read(), password=None)
        pub = priv.public_key().public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )
        return base64.urlsafe_b64encode(pub).rstrip(b"=").decode()
    except Exception:
        return None


# ---------- Presence (Telegram-style: PC 활성 시 모바일 푸시 억제) ----------
# 메모리 내 SID 매핑: uid -> { sid: {"device": "pc"|"mobile"|"unknown", "active": bool, "ts": float} }
# 단일 worker (eventlet) 환경 가정. 멀티 워커 확장 시 Redis 등으로 교체 필요.
import threading as _pres_threading
import time as _pres_time
_user_connections = {}
_user_conn_lock = _pres_threading.Lock()

def _presence_register(uid, sid, device="unknown", active=True):
    """SocketIO 연결 등록·갱신."""
    if not uid or not sid:
        return
    if device not in ("pc", "mobile", "unknown"):
        device = "unknown"
    with _user_conn_lock:
        _user_connections.setdefault(uid, {})[sid] = {
            "device": device,
            "active": bool(active),
            "ts": _pres_time.time(),
        }

def _presence_unregister(uid, sid):
    """SocketIO 연결 해제."""
    if not uid or not sid:
        return
    with _user_conn_lock:
        conns = _user_connections.get(uid)
        if not conns:
            return
        conns.pop(sid, None)
        if not conns:
            _user_connections.pop(uid, None)

def _user_has_active_pc(uid):
    """해당 사용자의 PC 연결 중 active(포커스 있음) 게 있으면 True.
    이 때는 모바일 푸시를 발송하지 않음 — Telegram 동작."""
    if not uid:
        return False
    with _user_conn_lock:
        conns = _user_connections.get(uid, {})
        for sid, info in conns.items():
            if info.get("device") == "pc" and info.get("active"):
                return True
    return False


def send_push_to_user(user_id, title, body, url=None, tag=None, collect_errors=False):
    """특정 사용자의 모든 push 구독에 알림 전송. 410/404는 만료로 간주하고 삭제.
    collect_errors=True 이면 (sent_count, [{id, endpoint, error}], total_subs) 튜플 반환."""
    errors = []
    if not PYWEBPUSH_OK:
        if collect_errors:
            return 0, [{"error": "PYWEBPUSH_OK=False (pywebpush 모듈 import 실패)"}], 0
        return 0
    priv = vapid_private_key()
    if not priv:
        if collect_errors:
            return 0, [{"error": "VAPID 개인키 파일(data/vapid_private.pem) 없음"}], 0
        return 0
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        subs = db.execute(
            "SELECT id, endpoint, p256dh, auth FROM push_subscriptions WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        total = len(subs)
        sent = 0
        for s in subs:
            ep_prefix = s["endpoint"][:60] + "..." if s["endpoint"] else "?"
            try:
                webpush(
                    subscription_info={
                        "endpoint": s["endpoint"],
                        "keys": {"p256dh": s["p256dh"], "auth": s["auth"]},
                    },
                    data=json.dumps({"title": title, "body": body, "url": url or "/chat", "tag": tag}),
                    vapid_private_key=priv,
                    vapid_claims={"sub": VAPID_CONTACT},
                    ttl=43200,  # 12시간
                    # Urgency: high — Android Doze 모드/Battery Saver 우회.
                    # 화면 꺼진 상태에서도 즉시 푸시 도달 (지연 차단).
                    # Topic (방 ID): 같은 방의 미열람 알림이 누적되면 OS 가 합쳐서 1개 표시.
                    headers={
                        "Urgency": "high",
                        **({"Topic": tag} if tag else {}),
                    },
                )
                sent += 1
            except WebPushException as e:
                code = getattr(e.response, "status_code", None) if e.response is not None else None
                body_resp = ""
                try:
                    if e.response is not None:
                        body_resp = e.response.text[:200]
                except Exception:
                    pass
                err_msg = f"WebPushException code={code} body={body_resp} msg={str(e)[:200]}"
                print(f"[push] FAIL sub_id={s['id']} {ep_prefix} → {err_msg}")
                errors.append({"id": s["id"], "endpoint": ep_prefix, "error": err_msg})
                if code in (404, 410):
                    db.execute("DELETE FROM push_subscriptions WHERE id = ?", (s["id"],))
                    db.commit()
            except Exception as e:
                err_msg = f"{type(e).__name__}: {str(e)[:300]}"
                print(f"[push] EXCEPTION sub_id={s['id']} {ep_prefix} → {err_msg}")
                errors.append({"id": s["id"], "endpoint": ep_prefix, "error": err_msg})
        if collect_errors:
            return sent, errors, total
        return sent
    finally:
        db.close()


def push_message_to_room_members(room_id, sender_user_id, title, body, url=None, tag=None):
    """방의 sender 외 모든 멤버에게 push (백그라운드 알림)."""
    if not PYWEBPUSH_OK:
        return
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        members = db.execute(
            "SELECT user_id FROM room_members WHERE room_id = ? AND user_id != ?",
            (room_id, sender_user_id),
        ).fetchall()
    finally:
        db.close()
    for m in members:
        # Telegram-style: 해당 사용자가 PC에서 활성(포커스) 상태이면 푸시 스킵.
        # 이중 알림(PC 화면 + 휴대폰 진동) 피로 해소가 1차 목적.
        if _user_has_active_pc(m["user_id"]):
            print(f"[push] skip uid={m['user_id']} — PC active (Telegram-style)")
            continue
        send_push_to_user(m["user_id"], title, body, url=url, tag=tag)
ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "heic"}
ALLOWED_FILE_EXT = ALLOWED_IMAGE_EXT | {
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "hwp", "hwpx",
    "txt", "csv", "zip", "7z", "rar", "dwg", "dxf", "step", "stp", "stl",
    "mp4", "mov", "avi", "mkv", "mp3", "wav",
}

def _load_or_generate_secret():
    """SECRET_KEY 자동 생성·영속화. 환경변수 우선, 없으면 data/secret.key 사용·생성."""
    env_key = os.environ.get("KNK_MSG_SECRET")
    if env_key and len(env_key) >= 16:
        return env_key
    sec_path = os.path.join(APP_DIR, "data", "secret.key")
    os.makedirs(os.path.dirname(sec_path), exist_ok=True)
    if os.path.exists(sec_path):
        with open(sec_path, "r", encoding="utf-8") as f:
            v = f.read().strip()
            if len(v) >= 16:
                return v
    import secrets as _secrets
    new_key = _secrets.token_hex(32)
    with open(sec_path, "w", encoding="utf-8") as f:
        f.write(new_key)
    print(f" * SECRET_KEY 신규 생성·저장: {sec_path}")
    return new_key


app = Flask(__name__)
app.config["SECRET_KEY"] = _load_or_generate_secret()
app.config["JSON_AS_ASCII"] = False
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = STATIC_CACHE_AGE
app.config["TEMPLATES_AUTO_RELOAD"] = not IS_PRODUCTION  # 개발만 자동 리로드
app.jinja_env.auto_reload = not IS_PRODUCTION

# 정적 자산 캐시 버스팅 — 서버 시작 시각을 버전으로 사용. 코드 수정 후 재시작 시 자동으로 새 버전.
import time as _time
STATIC_VERSION = str(int(_time.time()))

@app.context_processor
def _inject_asset_version():
    return {
        "asset_version": STATIC_VERSION,
        "base_path": BASE_PATH,
        "retention_months": MESSAGE_RETENTION_MONTHS,
    }

# 세션 자동 로그인 유지 — 명시적 로그아웃 전까지 90일 (모바일 사용성)
# session.permanent=True 와 함께 동작. 환경변수로 조정 가능.
from datetime import timedelta as _timedelta
SESSION_DAYS = int(os.environ.get("KNK_MSG_SESSION_DAYS", "90"))
app.config["PERMANENT_SESSION_LIFETIME"] = _timedelta(days=SESSION_DAYS)
app.config["SESSION_REFRESH_EACH_REQUEST"] = True  # 매 요청마다 만료 시간 갱신 (활성 사용자는 영구 유지)

# 운영 환경: 세션 쿠키 보안 강화 + HTTPS 강제
if IS_PRODUCTION:
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PREFERRED_URL_SCHEME"] = "https"
    # nginx 등 리버스 프록시 뒤에서 X-Forwarded-Proto/Host 신뢰
    if TRUSTED_PROXIES > 0:
        try:
            from werkzeug.middleware.proxy_fix import ProxyFix
            app.wsgi_app = ProxyFix(
                app.wsgi_app,
                x_for=TRUSTED_PROXIES, x_proto=TRUSTED_PROXIES,
                x_host=TRUSTED_PROXIES, x_prefix=TRUSTED_PROXIES,
            )
        except Exception:
            pass

socketio = SocketIO(
    app,
    cors_allowed_origins=CORS_ALLOWED,
    async_mode=ASYNC_MODE,
    max_http_buffer_size=MAX_UPLOAD_MB * 1024 * 1024,
)


# /msg 같은 하위 경로 배포 지원 — PATH_INFO 에서 BASE_PATH 를 떼어 SCRIPT_NAME 으로 옮긴다.
# 결과: url_for() 가 자동으로 접두어를 붙이고, Socket.IO 미들웨어도 정상 동작.
# SocketIO(app) 이후에 감싸야 PrefixMiddleware 가 최외곽이 되어 /msg/socket.io 도 처리됨.
if BASE_PATH:
    class _PrefixMiddleware:
        def __init__(self, wsgi_app, prefix):
            self.wsgi_app = wsgi_app
            self.prefix = prefix

        def __call__(self, environ, start_response):
            path = environ.get("PATH_INFO", "")
            # 헬스체크는 접두어와 무관하게 항상 통과 (docker/healthcheck·배포 스크립트용)
            if path == "/healthz":
                return self.wsgi_app(environ, start_response)
            if path == self.prefix or path.startswith(self.prefix + "/"):
                environ["SCRIPT_NAME"] = environ.get("SCRIPT_NAME", "") + self.prefix
                environ["PATH_INFO"] = path[len(self.prefix):] or "/"
                return self.wsgi_app(environ, start_response)
            # BASE_PATH 외 경로(루트 포함)는 404 — 메신저는 /msg 하위에서만 서비스
            start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
            return ["Not Found".encode("utf-8")]

    app.wsgi_app = _PrefixMiddleware(app.wsgi_app, BASE_PATH)


@app.after_request
def no_cache_html_js(resp):
    """동적 응답(HTML/JS/CSS/JSON)에 캐시 방지 헤더. 운영에서도 코드 수정 즉시 반영을 위해 유지.
    + 운영 환경에서는 보안 헤더 추가."""
    if resp.mimetype in ("text/html", "application/javascript", "text/css", "application/json"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    if IS_PRODUCTION:
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return resp


# ---------- DB ----------
def get_db():
    db = getattr(g, "_db", None)
    if db is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        db = g._db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db


@app.teardown_appcontext
def close_db(_exc):
    db = getattr(g, "_db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        display_name TEXT NOT NULL,
        role TEXT DEFAULT 'staff',
        avatar_color TEXT DEFAULT '#3b82f6',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY,
        name TEXT,
        type TEXT NOT NULL,        -- direct | group | channel
        created_by INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY (created_by) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS room_members (
        room_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        joined_at TEXT NOT NULL,
        last_read_message_id INTEGER DEFAULT 0,
        PRIMARY KEY (room_id, user_id),
        FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY,
        room_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        kind TEXT DEFAULT 'text',  -- text | image | file | system
        created_at TEXT NOT NULL,
        FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    CREATE INDEX IF NOT EXISTS idx_messages_room_created ON messages(room_id, created_at);

    -- 아이템(=프로젝트/품목): 카톡의 '방'을 자동 정리 가능한 단위로 승격
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY,
        room_id INTEGER UNIQUE NOT NULL,
        code TEXT,                          -- 모델/품번 e.g. 003M2501
        name TEXT NOT NULL,                 -- 아이템명
        customer TEXT,                      -- 고객사 e.g. 삼성전자
        status TEXT DEFAULT 'active',       -- active | hold | done | cancelled
        due_date TEXT,                      -- 납기 (ISO date)
        description TEXT,
        created_by INTEGER,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
        FOREIGN KEY (created_by) REFERENCES users(id)
    );
    CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
    CREATE INDEX IF NOT EXISTS idx_items_customer ON items(customer);

    -- 요청(티켓): 메시지 → 추적 가능한 작업으로 승격
    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY,
        room_id INTEGER NOT NULL,
        message_id INTEGER,
        title TEXT NOT NULL,
        description TEXT,
        requested_by INTEGER NOT NULL,
        assigned_to INTEGER,
        due_date TEXT,
        status TEXT DEFAULT 'open',     -- open | in_progress | done | cancelled
        priority TEXT DEFAULT 'normal',  -- low | normal | high
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        closed_at TEXT,
        FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE SET NULL,
        FOREIGN KEY (requested_by) REFERENCES users(id),
        FOREIGN KEY (assigned_to) REFERENCES users(id)
    );
    CREATE INDEX IF NOT EXISTS idx_requests_room_status ON requests(room_id, status);
    CREATE INDEX IF NOT EXISTS idx_requests_assigned_status ON requests(assigned_to, status);
    CREATE INDEX IF NOT EXISTS idx_requests_due ON requests(due_date);

    -- 메시지 반응 (👍 ✅ ❤ 등) — "네 알겠습니다" 노이즈 감소용
    CREATE TABLE IF NOT EXISTS message_reactions (
        id INTEGER PRIMARY KEY,
        message_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        emoji TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE (message_id, user_id, emoji),
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_reactions_msg ON message_reactions(message_id);

    -- 메시지 전달확인 (acknowledgment) — 카톡 '읽음'을 넘어선 명시적 확인
    -- "내가 봤고 처리하겠습니다" 의지 표시
    CREATE TABLE IF NOT EXISTS message_acks (
        id INTEGER PRIMARY KEY,
        message_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        ack_type TEXT DEFAULT 'ok',     -- ok | doing | done | reject
        comment TEXT,                    -- 선택: "오늘 5시까지 처리하겠음" 같은 메모
        created_at TEXT NOT NULL,
        UNIQUE (message_id, user_id, ack_type),
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_acks_msg ON message_acks(message_id);
    CREATE INDEX IF NOT EXISTS idx_acks_user ON message_acks(user_id);

    -- 메시지 별표 (중요 결정 마킹) — 사용자별
    CREATE TABLE IF NOT EXISTS message_stars (
        message_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        starred_at TEXT NOT NULL,
        PRIMARY KEY (message_id, user_id),
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_stars_user ON message_stars(user_id);

    -- 첨부 파일 버전 체인 (같은 도면 v1/v2/v3)
    -- parent_message_id 가 가장 최초 버전. version_no 1=v1, 2=v2 ...
    CREATE TABLE IF NOT EXISTS attachment_versions (
        message_id INTEGER PRIMARY KEY,         -- 이 attachment 메시지
        parent_message_id INTEGER NOT NULL,     -- 첫 버전의 message_id (자기 자신이면 자기)
        version_no INTEGER NOT NULL DEFAULT 1,
        room_id INTEGER NOT NULL,
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
        FOREIGN KEY (parent_message_id) REFERENCES messages(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_attver_parent ON attachment_versions(parent_message_id);
    CREATE INDEX IF NOT EXISTS idx_attver_room ON attachment_versions(room_id);

    -- 메시지 번역 캐시 — 같은 메시지를 두 번 번역하지 않음 (Claude API 비용 절약)
    CREATE TABLE IF NOT EXISTS message_translations (
        id INTEGER PRIMARY KEY,
        message_id INTEGER NOT NULL,
        target_lang TEXT NOT NULL,         -- 'ko' | 'vi' | 'en'
        source_lang TEXT,                  -- 자동 감지 결과
        translated_text TEXT NOT NULL,
        model TEXT,                        -- 'claude-haiku-4-5' 등
        input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        cost_usd REAL DEFAULT 0,
        created_at TEXT NOT NULL,
        UNIQUE (message_id, target_lang),
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_translations_msg ON message_translations(message_id);
    CREATE INDEX IF NOT EXISTS idx_translations_created ON message_translations(created_at);

    -- 사용자 상태 (Slack/Teams 식: 자리비움·회의중·외근·방해금지·온라인·오프라인)
    -- user_id PRIMARY KEY = 사용자 1명당 1개 행 (UPSERT 패턴).
    CREATE TABLE IF NOT EXISTS user_statuses (
        user_id INTEGER PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'online',  -- online | away | busy | meeting | external | dnd | offline
        custom_text TEXT,                        -- 사용자 정의 ("HAIST WORKS 운영 중")
        emoji TEXT,                              -- 상태 이모지 (선택)
        until_at TEXT,                           -- 이 시각까지 유지 (NULL=수동 변경까지 영구)
        auto_set INTEGER NOT NULL DEFAULT 0,     -- 1=캘린더 자동 설정, 0=수동
        updated_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_user_statuses_until ON user_statuses(until_at);

    -- 사용자 캘린더 일정 (간단 — 외부 iCal/Google Calendar 연동은 후속)
    -- 시작 시각에 자동 "회의 중" 전환, 종료 시각에 "온라인" 복귀.
    CREATE TABLE IF NOT EXISTS user_calendar_events (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        start_at TEXT NOT NULL,    -- ISO datetime
        end_at TEXT NOT NULL,
        kind TEXT DEFAULT 'meeting',  -- meeting | external | busy
        applied INTEGER NOT NULL DEFAULT 0,  -- 0=대기, 1=시작 적용됨, 2=종료 적용됨
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_cal_user_start ON user_calendar_events(user_id, start_at);
    CREATE INDEX IF NOT EXISTS idx_cal_applied ON user_calendar_events(applied, start_at, end_at);

    -- 프로젝트(아이템 방) 이력 스냅샷 — HAIST WORKS 연동 대비.
    -- 하루 1회 자동 + 수동 즉시 갱신. 각 스냅샷은 마지막 스냅샷 이후 새 메시지를 요약.
    CREATE TABLE IF NOT EXISTS project_history (
        id INTEGER PRIMARY KEY,
        room_id INTEGER NOT NULL,
        period_start TEXT,                  -- 이 스냅샷이 다룬 메시지 첫 시각
        period_end TEXT NOT NULL,           -- 마지막 시각
        first_message_id INTEGER,           -- 다룬 범위 (다음 자동 생성의 기준)
        last_message_id INTEGER NOT NULL,
        summary_text TEXT NOT NULL,         -- AI 요약 본문 (한국어)
        message_count INTEGER NOT NULL DEFAULT 0,
        attachment_count INTEGER NOT NULL DEFAULT 0,
        attachments_json TEXT,              -- [{name,size,mime,url,sender,sent_at}, ...]
        model TEXT,
        input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        cost_usd REAL DEFAULT 0,
        created_by INTEGER,                 -- NULL=자동, user_id=수동
        created_at TEXT NOT NULL,
        synced_to_hw INTEGER NOT NULL DEFAULT 0,  -- HAIST WORKS 전송 여부 (이후 사용)
        synced_at TEXT,
        FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_ph_room_created ON project_history(room_id, created_at);
    CREATE INDEX IF NOT EXISTS idx_ph_synced ON project_history(synced_to_hw, room_id);

    -- AI 요약 캐시 (Slack AI / Teams Copilot 식)
    -- scope_type 으로 무엇을 요약했는지 구분: 'channel_recent'(방의 최근 N개) | 'thread'(스레드)
    -- scope_key 는 그 식별자: 'room:{id}:last:{N}' 또는 'thread:{parent_msg_id}'
    -- last_message_id 는 캐시 무효화 기준 — 새 메시지가 들어왔으면 다시 생성
    CREATE TABLE IF NOT EXISTS ai_summaries (
        id INTEGER PRIMARY KEY,
        scope_type TEXT NOT NULL,
        scope_key TEXT NOT NULL,
        room_id INTEGER,
        last_message_id INTEGER NOT NULL,
        summary_text TEXT NOT NULL,
        model TEXT,
        input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        cost_usd REAL DEFAULT 0,
        created_by INTEGER,
        created_at TEXT NOT NULL,
        UNIQUE (scope_type, scope_key, last_message_id),
        FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_aisum_scope ON ai_summaries(scope_type, scope_key);
    CREATE INDEX IF NOT EXISTS idx_aisum_created ON ai_summaries(created_at);

    -- Web Push 구독 (한 사용자가 여러 디바이스 가능)
    CREATE TABLE IF NOT EXISTS push_subscriptions (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        endpoint TEXT UNIQUE NOT NULL,
        p256dh TEXT NOT NULL,
        auth TEXT NOT NULL,
        user_agent TEXT,
        created_at TEXT NOT NULL,
        last_used TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_push_user ON push_subscriptions(user_id);
    """)
    conn.commit()

    # ---- 컬럼 마이그레이션 ----
    existing_msg_cols = {row["name"] for row in cur.execute("PRAGMA table_info(messages)").fetchall()}
    for col, ddl in [
        ("file_path", "ALTER TABLE messages ADD COLUMN file_path TEXT"),
        ("file_name", "ALTER TABLE messages ADD COLUMN file_name TEXT"),
        ("file_size", "ALTER TABLE messages ADD COLUMN file_size INTEGER"),
        ("file_mime", "ALTER TABLE messages ADD COLUMN file_mime TEXT"),
        # Slack 식 스레드 — parent_message_id 가 채워지면 스레드 답글.
        # NULL=일반 메시지 (메인 채널에 표시). NOT NULL=답글 (스레드 패널에만 표시).
        ("parent_message_id", "ALTER TABLE messages ADD COLUMN parent_message_id INTEGER"),
        # 인용 답장(Quote Reply) — 본 채널에 답글 + 원본 미니 카드 표시 (스레드와 별개)
        ("quoted_message_id", "ALTER TABLE messages ADD COLUMN quoted_message_id INTEGER"),
        # 전달(Forward) 출처 — Telegram 식 메타데이터 보존
        # 원본 메시지 ID. 원본이 삭제돼도 아래 forwarded_* 캐시로 복원 가능
        ("forwarded_from_message_id", "ALTER TABLE messages ADD COLUMN forwarded_from_message_id INTEGER"),
        ("forwarded_from_user_id", "ALTER TABLE messages ADD COLUMN forwarded_from_user_id INTEGER"),
        # 원본 작성자명·방명·시각 캐시 (원본 삭제 후에도 표시되도록)
        ("forwarded_from_name", "ALTER TABLE messages ADD COLUMN forwarded_from_name TEXT"),
        ("forwarded_from_room_name", "ALTER TABLE messages ADD COLUMN forwarded_from_room_name TEXT"),
        ("forwarded_from_created_at", "ALTER TABLE messages ADD COLUMN forwarded_from_created_at TEXT"),
    ]:
        if col not in existing_msg_cols:
            cur.execute(ddl)
    # 스레드 답글 조회 인덱스
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_parent ON messages(parent_message_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_quoted ON messages(quoted_message_id)")

    existing_item_cols = {row["name"] for row in cur.execute("PRAGMA table_info(items)").fetchall()}
    if "keep_forever" not in existing_item_cols:
        cur.execute("ALTER TABLE items ADD COLUMN keep_forever INTEGER DEFAULT 0")

    # 사용자 활성/비활성 (퇴사자 차단)
    existing_user_cols = {row["name"] for row in cur.execute("PRAGMA table_info(users)").fetchall()}
    if "active" not in existing_user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1")

    # 방 이름 고정 플래그 (방장만 이름 변경 가능 vs 멤버 각자 별명 가능)
    existing_room_cols = {row["name"] for row in cur.execute("PRAGMA table_info(rooms)").fetchall()}
    if "name_locked" not in existing_room_cols:
        cur.execute("ALTER TABLE rooms ADD COLUMN name_locked INTEGER NOT NULL DEFAULT 0")

    # 방별 메시지 자동 삭제 일수 (WhatsApp 식: 1=24시간, 7=1주, 30=30일, 90=90일)
    # NULL=영구(글로벌 MESSAGE_RETENTION_MONTHS 만 적용). 방장이 설정 가능.
    if "retention_days" not in existing_room_cols:
        cur.execute("ALTER TABLE rooms ADD COLUMN retention_days INTEGER")

    # 초대 권한 정책 — 'all'(기본: 모든 멤버) | 'host_only'(방장·부방장만)
    if "invite_policy" not in existing_room_cols:
        cur.execute("ALTER TABLE rooms ADD COLUMN invite_policy TEXT NOT NULL DEFAULT 'all'")

    # 매 부팅마다 created_by → host 자동 백필 (idempotent)
    # 신규 방의 host 가 누락된 경우(seed/외부 INSERT) 자동 교정.
    cur.execute("""
        UPDATE room_members
           SET role = 'host'
         WHERE role != 'host'
           AND (room_id, user_id) IN (
               SELECT id, created_by FROM rooms
                WHERE created_by IS NOT NULL
           )
    """)

    # self 방 이름을 '📝 메모' 로 통일 (옛 '📝 나에게 보내기' 자동 갱신)
    cur.execute("UPDATE rooms SET name='📝 메모' WHERE type='self' AND name != '📝 메모'")

    # 방 멤버 역할 (host=방장, sub_host=부방장, member=일반)
    existing_rm_cols = {row["name"] for row in cur.execute("PRAGMA table_info(room_members)").fetchall()}
    if "role" not in existing_rm_cols:
        cur.execute("ALTER TABLE room_members ADD COLUMN role TEXT NOT NULL DEFAULT 'member'")
        # 기존 방의 created_by 사용자를 host 로 백필
        cur.execute("""
            UPDATE room_members SET role='host'
             WHERE (room_id, user_id) IN (
                SELECT id, created_by FROM rooms WHERE created_by IS NOT NULL
             )
        """)

    # 사용자별 방 정렬 — order_value(REAL, 사이 삽입 용이) + pinned(0/1)
    # NULL=자동 정렬, INTEGER/REAL=수동. pinned=1 인 방은 항상 상단 그룹.
    if "order_value" not in existing_rm_cols:
        cur.execute("ALTER TABLE room_members ADD COLUMN order_value REAL")
    if "pinned" not in existing_rm_cols:
        cur.execute("ALTER TABLE room_members ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rm_user_order ON room_members(user_id, pinned, order_value)")

    # 방 별명 (멤버 각자 자기 화면에서만 보이는 이름)
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS room_aliases (
        user_id INTEGER NOT NULL,
        room_id INTEGER NOT NULL,
        alias TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (user_id, room_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
    );
    """)
    conn.commit()

    # ---- FTS5 가상 테이블 (전문 검색) ----
    cur.executescript("""
    CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
        content, content='messages', content_rowid='id', tokenize='unicode61'
    );
    CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
        INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
    END;
    CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
        INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
    END;
    CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
        INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
        INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
    END;
    """)
    # 기존 데이터 FTS 인덱스 1회 채우기
    cur.execute("SELECT COUNT(*) AS n FROM messages_fts")
    if cur.fetchone()["n"] == 0:
        cur.execute("INSERT INTO messages_fts(rowid, content) SELECT id, content FROM messages")
    conn.commit()

    now = datetime.now(timezone.utc).isoformat()

    cur.execute("SELECT COUNT(*) AS n FROM users")
    if cur.fetchone()["n"] == 0:
        seed = [
            ("kjr",  "knk1234", "김정락 대표", "ceo",   "#ef4444"),
            ("hong", "knk1234", "홍길동",      "staff", "#3b82f6"),
            ("lee",  "knk1234", "이순신",      "staff", "#10b981"),
        ]
        for username, pw, display, role, color in seed:
            cur.execute(
                "INSERT INTO users (username, password_hash, display_name, role, avatar_color, created_at) VALUES (?,?,?,?,?,?)",
                (username, generate_password_hash(pw), display, role, color, now),
            )
        cur.execute(
            "INSERT INTO rooms (name, type, created_by, created_at) VALUES (?,?,?,?)",
            ("전체공지", "channel", 1, now),
        )
        room_id = cur.lastrowid
        for uid in (1, 2, 3):
            mrole = 'host' if uid == 1 else 'member'
            cur.execute(
                "INSERT INTO room_members (room_id, user_id, joined_at, role) VALUES (?,?,?,?)",
                (room_id, uid, now, mrole),
            )
        cur.execute(
            "INSERT INTO messages (room_id, user_id, content, kind, created_at) VALUES (?,?,?,?,?)",
            (room_id, 1, "환영합니다 — KNK 메신저 시작합니다.", "system", now),
        )
        conn.commit()

    # 시드 아이템 — 대표가 보여준 카톡방 4개 미러 (items 테이블 비어있으면 1회 주입)
    cur.execute("SELECT COUNT(*) AS n FROM items")
    if cur.fetchone()["n"] == 0:
        items_seed = [
            ("003M2501", "Watch Molding 자동화",   "삼성전자",     "active"),
            ("WP-LOA",   "WING PLATE PRESS LOA",  "삼성전자",     "active"),
            ("HM-001",   "KNK·하나머티리얼",        "하나머티리얼",  "done"),
            ("M2504",    "메탈치수 검사기",         "삼성전자",     "active"),
        ]
        for code, name, customer, status in items_seed:
            cur.execute(
                "INSERT INTO rooms (name, type, created_by, created_at) VALUES (?,?,?,?)",
                (name, "item", 1, now),
            )
            rid = cur.lastrowid
            cur.execute("""
                INSERT INTO items (room_id, code, name, customer, status, created_by, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (rid, code, name, customer, status, 1, now, now))
            for uid in (1, 2, 3):
                mrole = 'host' if uid == 1 else 'member'
                cur.execute(
                    "INSERT INTO room_members (room_id, user_id, joined_at, role) VALUES (?,?,?,?)",
                    (rid, uid, now, mrole),
                )
        conn.commit()

    conn.close()


# ---------- Auth ----------
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()


def login_required(view):
    @wraps(view)
    def wrapped(*a, **k):
        if not current_user():
            return redirect(url_for("login"))
        return view(*a, **k)
    return wrapped


# ---------- Pages ----------
@app.route("/")
def index():
    # 모바일 브라우저 HTML 캐시 완전 우회:
    # 302 redirect 응답 자체도 캐시될 수 있으므로 작은 HTML + JS location.replace 로 매번 unique URL 발생
    # 이렇게 하면 옛 / 응답이 캐시에 박혀 있어도, 그 응답을 받기만 하면 JS 가 새 URL 로 강제 이동
    if current_user():
        body = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>KNK</title></head>
<body><script>
location.replace('{BASE_PATH}/chat?v={STATIC_VERSION}&t=' + Date.now() + '&r=' + Math.random());
</script>
<noscript><meta http-equiv="refresh" content="0;url={BASE_PATH}/chat?v={STATIC_VERSION}"></noscript>
</body></html>"""
        resp = make_response(body)
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, private"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        p = request.form.get("password") or ""
        row = get_db().execute("SELECT * FROM users WHERE username = ?", (u,)).fetchone()
        if row and check_password_hash(row["password_hash"], p):
            session.clear()
            session["user_id"] = row["id"]
            # 자동 로그인 유지 — PERMANENT_SESSION_LIFETIME 만큼(기본 90일) 쿠키 유지.
            # 명시적 /logout 호출 전까지 브라우저 닫고 켜도 로그인 상태.
            session.permanent = True
            return redirect(url_for("chat") + f"?v={STATIC_VERSION}&t={int(_time.time())}")
        return render_template("login.html", error="아이디 또는 비밀번호가 올바르지 않습니다.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/chat")
@login_required
def chat():
    # 첫 접속 시 '나에게 보내기' 1인방 자동 보장 — 학습비용 0 으로 즉시 사용 가능.
    try:
        _ensure_self_room(session["user_id"])
    except Exception as e:
        print(f"[chat] self_room 보장 실패: {e}")
    return render_template("chat.html", me=current_user())


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", me=current_user())


# ---------- API ----------
@app.route("/healthz")
def healthz():
    """헬스체크 — BASE_PATH 와 무관하게 항상 루트(/healthz)에서 응답."""
    return "ok", 200


@app.route("/sw.js")
def serve_sw():
    """Service Worker — BASE_PATH 하위 경로 배포 시 /msg/sw.js 로 서빙되며 scope 는 /msg/.
    sw.js 내부에서 base 경로는 등록 시 ?base= 쿼리로 전달받는다."""
    return send_from_directory(os.path.join(APP_DIR, "static"), "sw.js", mimetype="application/javascript")


@app.route("/manifest.json")
def serve_manifest():
    """PWA manifest — BASE_PATH 를 반영해 동적 생성 (start_url·scope·아이콘 경로)."""
    bp = BASE_PATH
    data = {
        "name": "KNK 메신저",
        "short_name": "KNK",
        "description": "KNK 사내 업무 전용 메신저 — 아이템별 자동 정리·요청 추적·전사 검색",
        "start_url": f"{bp}/chat",
        "scope": f"{bp}/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#ffffff",
        "theme_color": "#A5282C",
        "lang": "ko",
        "icons": [
            {"src": f"{bp}/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": f"{bp}/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
            {"src": f"{bp}/static/icons/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
        ],
        "categories": ["business", "productivity"],
    }
    resp = make_response(jsonify(data))
    resp.headers["Content-Type"] = "application/manifest+json; charset=utf-8"
    return resp


@app.route("/api/me")
@login_required
def api_me():
    u = current_user()
    return jsonify({
        "id": u["id"], "username": u["username"],
        "display_name": u["display_name"], "role": u["role"],
        "avatar_color": u["avatar_color"],
    })


@app.route("/api/users")
@login_required
def api_users():
    rows = get_db().execute(
        "SELECT id, username, display_name, role, avatar_color FROM users ORDER BY display_name"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/rooms")
@login_required
def api_rooms():
    me = current_user()
    db = get_db()
    rows = db.execute("""
        SELECT r.id, r.name, r.type, r.created_at, r.name_locked, r.created_by,
               r.retention_days, r.invite_policy,
               rm.role AS my_role,
               rm.pinned, rm.order_value,
               (SELECT alias FROM room_aliases WHERE room_id=r.id AND user_id=?) AS my_alias,
               it.code AS item_code, it.customer AS item_customer,
               it.status AS item_status, it.due_date AS item_due,
               (SELECT content FROM messages WHERE room_id = r.id ORDER BY id DESC LIMIT 1) AS last_message,
               (SELECT created_at FROM messages WHERE room_id = r.id ORDER BY id DESC LIMIT 1) AS last_at,
               (SELECT COUNT(*) FROM messages m
                  WHERE m.room_id = r.id
                    AND m.id > rm.last_read_message_id
                    AND m.user_id != ?) AS unread
          FROM rooms r
          JOIN room_members rm ON rm.room_id = r.id
          LEFT JOIN items it ON it.room_id = r.id
         WHERE rm.user_id = ?
         ORDER BY
            CASE r.type WHEN 'self' THEN 0 ELSE 1 END,
            CASE WHEN rm.pinned = 1 THEN 0 ELSE 1 END,
            CASE WHEN rm.order_value IS NOT NULL THEN 0 ELSE 1 END,
            rm.order_value ASC,
            (last_at IS NULL), last_at DESC, r.id DESC
    """, (me["id"], me["id"], me["id"])).fetchall()

    out = []
    for r in rows:
        d = dict(r)
        # 1:1 방은 항상 상대방 이름으로 표시
        if r["type"] == "direct":
            other = db.execute("""
                SELECT u.display_name, u.avatar_color
                  FROM room_members rm
                  JOIN users u ON u.id = rm.user_id
                 WHERE rm.room_id = ? AND rm.user_id != ?
                 LIMIT 1
            """, (r["id"], me["id"])).fetchone()
            if other:
                d["name"] = other["display_name"]
                d["avatar_color"] = other["avatar_color"]
        else:
            # 그룹/아이템 방: name_locked=0 이고 내 별명 있으면 별명 우선
            if not r["name_locked"] and r["my_alias"]:
                d["display_name_override"] = r["my_alias"]
                d["original_name"] = r["name"]
                d["name"] = r["my_alias"]
        out.append(d)
    return jsonify(out)


@app.route("/api/items", methods=["POST"])
@login_required
def api_items_create():
    me = current_user()
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "아이템 이름은 필수입니다."}), 400
    code = (data.get("code") or "").strip() or None
    customer = (data.get("customer") or "").strip() or None
    status = data.get("status") or "active"
    if status not in ("active", "hold", "done", "cancelled"):
        status = "active"
    due_date = data.get("due_date") or None
    description = (data.get("description") or "").strip() or None
    user_ids = list({int(x) for x in (data.get("user_ids") or [])})
    if me["id"] not in user_ids:
        user_ids.append(me["id"])

    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    # 아이템 방은 이름 고정 (방장만 변경 가능)
    cur = db.execute(
        "INSERT INTO rooms (name, type, created_by, created_at, name_locked) VALUES (?,?,?,?,1)",
        (name, "item", me["id"], now),
    )
    rid = cur.lastrowid
    db.execute("""
        INSERT INTO items (room_id, code, name, customer, status, due_date, description,
                           created_by, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (rid, code, name, customer, status, due_date, description, me["id"], now, now))
    for uid in user_ids:
        role = 'host' if uid == me["id"] else 'member'
        db.execute(
            "INSERT INTO room_members (room_id, user_id, joined_at, role) VALUES (?,?,?,?)",
            (rid, uid, now, role),
        )
    db.execute(
        "INSERT INTO messages (room_id, user_id, content, kind, created_at) VALUES (?,?,?,?,?)",
        (rid, me["id"], f"아이템 [{name}] 생성됨", "system", now),
    )
    db.commit()
    return jsonify({"room_id": rid, "name": name})


@app.route("/api/items/<int:room_id>", methods=["GET"])
@login_required
def api_item_get(room_id):
    me = current_user()
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
        (room_id, me["id"]),
    ).fetchone():
        abort(403)
    row = db.execute("""
        SELECT it.*, r.name AS room_name
          FROM items it JOIN rooms r ON r.id = it.room_id
         WHERE it.room_id = ?
    """, (room_id,)).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


@app.route("/api/items/<int:room_id>", methods=["PATCH"])
@login_required
def api_item_update(room_id):
    me = current_user()
    data = request.get_json(silent=True) or {}
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
        (room_id, me["id"]),
    ).fetchone():
        abort(403)
    fields, args = [], []
    for f in ("code", "customer", "status", "due_date", "description", "name", "keep_forever"):
        if f in data:
            v = data[f]
            if f == "keep_forever":
                v = 1 if v else 0
            elif f == "name":
                v = (v or "").strip() or None
            else:
                v = v or None
            fields.append(f"{f} = ?")
            args.append(v)
    if not fields:
        return jsonify({"ok": True})
    now = datetime.now(timezone.utc).isoformat()
    args.append(now)
    args.append(room_id)
    db.execute(
        f"UPDATE items SET {', '.join(fields)}, updated_at = ? WHERE room_id = ?",
        args,
    )
    if "name" in data:
        db.execute("UPDATE rooms SET name = ? WHERE id = ?", (data["name"], room_id))
    if "status" in data:
        label = {"active": "진행중", "hold": "보류", "done": "완료", "cancelled": "취소"}.get(data["status"], data["status"])
        db.execute(
            "INSERT INTO messages (room_id, user_id, content, kind, created_at) VALUES (?,?,?,?,?)",
            (room_id, me["id"], f"상태 변경 → {label}", "system", now),
        )
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/rooms/<int:room_id>/messages")
@login_required
def api_room_messages(room_id):
    me = current_user()
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
        (room_id, me["id"]),
    ).fetchone():
        abort(403)
    # 메인 타임라인은 스레드 부모(parent_message_id IS NULL)만 표시 — Slack 동작.
    # 답글은 /api/messages/<id>/thread 로 별도 조회.
    rows = db.execute("""
        SELECT m.id, m.content, m.kind, m.created_at,
               m.file_path, m.file_name, m.file_size, m.file_mime,
               m.parent_message_id AS thread_parent_id,
               m.quoted_message_id,
               m.forwarded_from_message_id, m.forwarded_from_user_id,
               m.forwarded_from_name, m.forwarded_from_room_name, m.forwarded_from_created_at,
               u.id AS user_id, u.display_name, u.avatar_color
          FROM messages m
          JOIN users u ON u.id = m.user_id
         WHERE m.room_id = ?
           AND m.parent_message_id IS NULL
         ORDER BY m.id ASC
    """, (room_id,)).fetchall()
    out = [dict(r) for r in rows]
    if out:
        ids = tuple(r["id"] for r in out)
        placeholders = ",".join("?" for _ in ids)

        # 반응 batch 로드
        rxs = db.execute(f"""
            SELECT mr.message_id, mr.emoji, mr.user_id, u.display_name
              FROM message_reactions mr JOIN users u ON u.id = mr.user_id
             WHERE mr.message_id IN ({placeholders})
        """, ids).fetchall()
        rxmap = {}
        for r in rxs:
            rxmap.setdefault(r["message_id"], []).append({"emoji": r["emoji"], "user_id": r["user_id"], "display_name": r["display_name"]})

        # ack batch 로드
        acks = db.execute(f"""
            SELECT a.message_id, a.user_id, a.ack_type, a.comment, u.display_name
              FROM message_acks a JOIN users u ON u.id = a.user_id
             WHERE a.message_id IN ({placeholders})
        """, ids).fetchall()
        ackmap = {}
        for a in acks:
            ackmap.setdefault(a["message_id"], []).append({
                "user_id": a["user_id"], "ack_type": a["ack_type"],
                "comment": a["comment"], "display_name": a["display_name"],
            })

        # 본인 별표 batch 로드
        my_stars = db.execute(
            f"SELECT message_id FROM message_stars WHERE user_id = ? AND message_id IN ({placeholders})",
            (me["id"],) + ids,
        ).fetchall()
        starred_ids = {s["message_id"] for s in my_stars}

        # 첨부 버전 정보 batch 로드
        avs = db.execute(f"""
            SELECT message_id, version_no, parent_message_id
              FROM attachment_versions
             WHERE message_id IN ({placeholders})
        """, ids).fetchall()
        avmap = {a["message_id"]: dict(a) for a in avs}

        # 같은 parent 의 최신 버전 찾기 (latest 표시용)
        if avmap:
            parent_ids = tuple({a["parent_message_id"] for a in avmap.values()})
            ph2 = ",".join("?" for _ in parent_ids)
            latest_rows = db.execute(f"""
                SELECT parent_message_id, MAX(version_no) AS max_v
                  FROM attachment_versions
                 WHERE parent_message_id IN ({ph2})
                 GROUP BY parent_message_id
            """, parent_ids).fetchall()
            latest_map = {r["parent_message_id"]: r["max_v"] for r in latest_rows}
        else:
            latest_map = {}

        # 캐시된 번역 batch 로드 — 클라이언트가 이미 번역된 메시지는 자동 표시
        translations = db.execute(f"""
            SELECT message_id, target_lang, translated_text
              FROM message_translations
             WHERE message_id IN ({placeholders})
        """, ids).fetchall()
        trmap = {}
        for t in translations:
            trmap.setdefault(t["message_id"], {})[t["target_lang"]] = t["translated_text"]

        # 스레드 답글 카운트 — 각 부모 메시지의 reply_count + 마지막 답글 시각
        thread_rows = db.execute(f"""
            SELECT parent_message_id AS pid,
                   COUNT(*) AS cnt,
                   MAX(created_at) AS last_at,
                   COUNT(DISTINCT user_id) AS participants
              FROM messages
             WHERE parent_message_id IN ({placeholders})
             GROUP BY parent_message_id
        """, ids).fetchall()
        thread_map = {t["pid"]: dict(t) for t in thread_rows}

        # 인용 답장 — quoted_message_id 가 가리키는 원본 메시지 batch 로드 (미니 카드용)
        quoted_ids = [r["quoted_message_id"] for r in out if r.get("quoted_message_id")]
        quoted_map = {}
        if quoted_ids:
            qph = ",".join("?" for _ in quoted_ids)
            qrows = db.execute(f"""
                SELECT m.id, m.content, m.kind, m.created_at, m.file_name,
                       u.display_name, u.avatar_color
                  FROM messages m JOIN users u ON u.id = m.user_id
                 WHERE m.id IN ({qph})
            """, quoted_ids).fetchall()
            quoted_map = {q["id"]: dict(q) for q in qrows}

        for m in out:
            m["reactions"] = rxmap.get(m["id"], [])
            m["acks"] = ackmap.get(m["id"], [])
            m["starred_by_me"] = m["id"] in starred_ids
            m["translations"] = trmap.get(m["id"], {})
            # 스레드 — 답글 정보
            t = thread_map.get(m["id"])
            if t:
                m["thread_reply_count"] = t["cnt"]
                m["thread_last_at"] = t["last_at"]
                m["thread_participants"] = t["participants"]
            else:
                m["thread_reply_count"] = 0
            # 인용 답장 — 원본 메시지 미니 카드용 메타
            if m.get("quoted_message_id"):
                qm = quoted_map.get(m["quoted_message_id"])
                if qm:
                    m["quoted"] = qm
                else:
                    # 원본 삭제된 경우 — 마커만
                    m["quoted"] = {"deleted": True}
            av = avmap.get(m["id"])
            if av:
                m["version_no"] = av["version_no"]
                # 첨부 버전 부모 — 스레드 부모와 다른 개념이라 별도 필드명 사용
                m["attachment_parent_id"] = av["parent_message_id"]
                # 하위호환 — 기존 frontend 가 data-parent-msg-id 로 읽음 (첨부 버전용)
                m["parent_message_id"] = av["parent_message_id"]
                m["is_latest_version"] = (av["version_no"] == latest_map.get(av["parent_message_id"], av["version_no"]))
    return jsonify(out)


@app.route("/api/messages/<int:message_id>/forward", methods=["POST"])
@login_required
def api_message_forward(message_id):
    """전달(Forward) — Telegram 식 출처 보존.
    body: {to_room_ids: [int, ...], add_comment?: str (선택)}
    원본 메시지 1건을 N개 대상 방에 복사. 각 새 메시지에는 forwarded_from_* 메타가 박힘.
    원본이 첨부파일이면 같은 파일 정보도 복사 (실제 파일은 공유)."""
    me = current_user()
    db = get_db()
    src = db.execute("""
        SELECT m.id, m.room_id, m.user_id, m.content, m.kind, m.created_at,
               m.file_path, m.file_name, m.file_size, m.file_mime,
               u.display_name AS author_name,
               r.name AS room_name
          FROM messages m
          JOIN users u ON u.id = m.user_id
          JOIN rooms r ON r.id = m.room_id
         WHERE m.id = ?
    """, (message_id,)).fetchone()
    if not src:
        return jsonify({"error": "원본 메시지 없음"}), 404
    # 출처 방 멤버 권한 (원본 볼 권한 있어야 전달 가능)
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
        (src["room_id"], me["id"]),
    ).fetchone():
        return jsonify({"error": "원본 방 멤버 아님"}), 403
    data = request.get_json(silent=True) or {}
    to_rooms = data.get("to_room_ids") or []
    add_comment = (data.get("add_comment") or "").strip()
    if not isinstance(to_rooms, list) or not to_rooms:
        return jsonify({"error": "to_room_ids 필요"}), 400
    try:
        to_rooms = [int(x) for x in to_rooms]
    except (ValueError, TypeError):
        return jsonify({"error": "to_room_ids 형식 오류"}), 400
    if len(to_rooms) > 20:
        return jsonify({"error": "한 번에 최대 20개 방"}), 400

    # 사전 검증: 모든 대상 방의 멤버여야 함
    bad = []
    for rid in to_rooms:
        if not db.execute(
            "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
            (rid, me["id"]),
        ).fetchone():
            bad.append(rid)
    if bad:
        return jsonify({"error": f"방 멤버 아님: {bad}"}), 403

    me_row = db.execute("SELECT display_name, avatar_color FROM users WHERE id=?", (me["id"],)).fetchone()
    now = datetime.now(timezone.utc).isoformat()
    new_ids = []
    for rid in to_rooms:
        # 코멘트 + (있으면) 원본 텍스트. 첨부파일은 파일 정보 복사.
        # 텍스트 메시지의 경우 본문은 원본 텍스트를 그대로 옮김 (Telegram 식).
        new_content = src["content"] if (src["kind"] in ("text", "image", "file") and src["content"]) else ""
        if add_comment:
            # 사용자 코멘트가 있으면 본문 앞에 코멘트, 새 줄 후 원본 (둘 다 표시)
            new_content = add_comment + ("\n\n" + new_content if new_content else "")
        cur = db.execute("""
            INSERT INTO messages
                (room_id, user_id, content, kind, created_at,
                 file_path, file_name, file_size, file_mime,
                 forwarded_from_message_id, forwarded_from_user_id,
                 forwarded_from_name, forwarded_from_room_name, forwarded_from_created_at)
            VALUES (?,?,?,?,?, ?,?,?,?, ?,?,?,?,?)
        """, (
            rid, me["id"], new_content, src["kind"] or "text", now,
            src["file_path"], src["file_name"], src["file_size"], src["file_mime"],
            src["id"], src["user_id"],
            src["author_name"], src["room_name"], src["created_at"],
        ))
        mid = cur.lastrowid
        new_ids.append({"room_id": rid, "message_id": mid})
        # 실시간 broadcast
        payload = {
            "id": mid,
            "room_id": rid,
            "user_id": me["id"],
            "display_name": me_row["display_name"],
            "avatar_color": me_row["avatar_color"],
            "content": new_content,
            "kind": src["kind"] or "text",
            "created_at": now,
            "file_path": src["file_path"],
            "file_name": src["file_name"],
            "file_size": src["file_size"],
            "file_mime": src["file_mime"],
            "forwarded_from_message_id": src["id"],
            "forwarded_from_user_id": src["user_id"],
            "forwarded_from_name": src["author_name"],
            "forwarded_from_room_name": src["room_name"],
            "forwarded_from_created_at": src["created_at"],
        }
        socketio.emit("new_message", payload, to=f"room_{rid}")
    db.commit()

    # 푸시 발송 — 각 방의 송신자 외 멤버
    if PYWEBPUSH_OK:
        body_preview = (add_comment or src["content"] or src["file_name"] or "")[:120]
        for rid in to_rooms:
            row = db.execute("SELECT name FROM rooms WHERE id=?", (rid,)).fetchone()
            room_name = row["name"] if row else "채팅"
            title = f"↗ {me_row['display_name']} 전달 ({room_name})"
            import threading as _t
            _t.Thread(
                target=push_message_to_room_members,
                args=(rid, me["id"], title, body_preview),
                kwargs={"url": f"{BASE_PATH}/chat?room={rid}", "tag": f"room_{rid}"},
                daemon=True,
            ).start()
    return jsonify({"ok": True, "forwarded_to": new_ids, "count": len(new_ids)})


@app.route("/api/messages/<int:message_id>/thread", methods=["GET"])
@login_required
def api_message_thread(message_id):
    """스레드 답글 목록 + 부모 메시지. Slack 식 사이드 패널 데이터.
    응답: { parent: {...}, replies: [...] }"""
    me = current_user()
    db = get_db()
    parent = db.execute("""
        SELECT m.id, m.room_id, m.content, m.kind, m.created_at,
               m.file_path, m.file_name, m.file_size, m.file_mime,
               u.id AS user_id, u.display_name, u.avatar_color
          FROM messages m
          JOIN users u ON u.id = m.user_id
         WHERE m.id = ?
    """, (message_id,)).fetchone()
    if not parent:
        return jsonify({"error": "not found"}), 404
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
        (parent["room_id"], me["id"]),
    ).fetchone():
        abort(403)
    replies = db.execute("""
        SELECT m.id, m.content, m.kind, m.created_at,
               m.file_path, m.file_name, m.file_size, m.file_mime,
               u.id AS user_id, u.display_name, u.avatar_color
          FROM messages m
          JOIN users u ON u.id = m.user_id
         WHERE m.parent_message_id = ?
         ORDER BY m.id ASC
    """, (message_id,)).fetchall()
    return jsonify({
        "parent": dict(parent),
        "replies": [dict(r) for r in replies],
    })


@app.route("/api/messages/<int:message_id>/reply", methods=["POST"])
@login_required
def api_message_reply(message_id):
    """스레드 답글 작성 (텍스트 전용).
    body: {content: str}
    답글은 parent_message_id 가 채워진 messages 레코드. 메인 채널 타임라인엔 안 보이고
    스레드 패널에서만 보임. Web Push 는 부모 작성자 + 기존 답글 작성자들에게."""
    me = current_user()
    db = get_db()
    parent = db.execute("SELECT id, room_id, user_id FROM messages WHERE id=?", (message_id,)).fetchone()
    if not parent:
        return jsonify({"error": "not found"}), 404
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
        (parent["room_id"], me["id"]),
    ).fetchone():
        abort(403)
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content required"}), 400
    if len(content) > 4000:
        content = content[:4000]
    # 부모의 부모가 있으면 (대부분 None 이어야 함) 그것을 사용 → 답글의 답글이 아니라 같은 스레드.
    real_parent_id = message_id
    pp = db.execute("SELECT parent_message_id FROM messages WHERE id=?", (message_id,)).fetchone()
    if pp and pp["parent_message_id"]:
        real_parent_id = pp["parent_message_id"]
    now = datetime.now(timezone.utc).isoformat()
    cur = db.execute(
        "INSERT INTO messages (room_id, user_id, content, kind, created_at, parent_message_id) VALUES (?,?,?,?,?,?)",
        (parent["room_id"], me["id"], content, "text", now, real_parent_id),
    )
    mid = cur.lastrowid
    db.commit()
    u = db.execute("SELECT display_name, avatar_color FROM users WHERE id=?", (me["id"],)).fetchone()
    payload = {
        "id": mid,
        "room_id": parent["room_id"],
        "user_id": me["id"],
        "display_name": u["display_name"],
        "avatar_color": u["avatar_color"],
        "content": content,
        "kind": "text",
        "created_at": now,
        "parent_message_id": real_parent_id,    # 호환용
        "thread_parent_id": real_parent_id,     # 새 키
    }
    # 스레드 패널 실시간 갱신용 이벤트 + 메인 타임라인 reply_count 갱신용
    socketio.emit("thread_reply", payload, to=f"room_{parent['room_id']}")
    socketio.emit("thread_count_changed", {
        "room_id": parent["room_id"],
        "parent_id": real_parent_id,
    }, to=f"room_{parent['room_id']}")
    # 푸시 — 부모 작성자 + 기존 답글 작성자들 (송신자 제외)
    if PYWEBPUSH_OK:
        recipients = set()
        if parent["user_id"] != me["id"]:
            recipients.add(parent["user_id"])
        prev_repliers = db.execute(
            "SELECT DISTINCT user_id FROM messages WHERE parent_message_id=? AND user_id != ?",
            (real_parent_id, me["id"]),
        ).fetchall()
        for r in prev_repliers:
            recipients.add(r["user_id"])
        if recipients:
            room_row = db.execute("SELECT name FROM rooms WHERE id=?", (parent["room_id"],)).fetchone()
            room_name = room_row["name"] if room_row else "채팅"
            title = f"💬 {u['display_name']} (스레드·{room_name})"
            body = content[:120]
            import threading as _t
            def _push_all():
                for rid in recipients:
                    if _user_has_active_pc(rid):
                        continue
                    send_push_to_user(
                        rid, title, body,
                        url=f"{BASE_PATH}/chat?room={parent['room_id']}&thread={real_parent_id}",
                        tag=f"thread_{real_parent_id}",
                    )
            _t.Thread(target=_push_all, daemon=True).start()
    return jsonify({"ok": True, "id": mid, "parent_id": real_parent_id})


@app.route("/api/messages/<int:message_id>/react", methods=["POST"])
@login_required
def api_message_react(message_id):
    me = current_user()
    data = request.get_json(silent=True) or {}
    emoji = (data.get("emoji") or "").strip()
    if not emoji or len(emoji) > 16:
        return jsonify({"error": "emoji 필수"}), 400
    db = get_db()
    msg = db.execute("SELECT room_id FROM messages WHERE id=?", (message_id,)).fetchone()
    if not msg:
        return jsonify({"error": "not found"}), 404
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
        (msg["room_id"], me["id"]),
    ).fetchone():
        abort(403)
    # 토글 — 이미 있으면 삭제, 없으면 추가
    existing = db.execute(
        "SELECT id FROM message_reactions WHERE message_id=? AND user_id=? AND emoji=?",
        (message_id, me["id"], emoji),
    ).fetchone()
    now = datetime.now(timezone.utc).isoformat()
    if existing:
        db.execute("DELETE FROM message_reactions WHERE id=?", (existing["id"],))
        action = "removed"
    else:
        db.execute(
            "INSERT INTO message_reactions (message_id, user_id, emoji, created_at) VALUES (?,?,?,?)",
            (message_id, me["id"], emoji, now),
        )
        action = "added"
    db.commit()
    socketio.emit("reaction_updated", {
        "message_id": message_id,
        "room_id": msg["room_id"],
        "user_id": me["id"],
        "display_name": me["display_name"],
        "emoji": emoji,
        "action": action,
    }, to=f"room_{msg['room_id']}")
    return jsonify({"action": action})


# ---------- 메시지 전달확인 (acknowledgment) ----------
ACK_TYPES = ("ok", "doing", "done", "reject")


@app.route("/api/messages/<int:message_id>/ack", methods=["POST"])
@login_required
def api_message_ack(message_id):
    """전달확인 — '내가 봤고 처리하겠다' 명시. 카톡 '읽음' 보다 강한 의지 표시.

    body: { "ack_type": "ok" | "doing" | "done" | "reject", "comment": "..." (선택) }
    토글 동작 — 같은 ack_type 다시 호출하면 해제.
    """
    me = current_user()
    db = get_db()
    msg = db.execute(
        "SELECT m.id, m.room_id, m.user_id, m.content, m.kind FROM messages m WHERE m.id = ?",
        (message_id,),
    ).fetchone()
    if not msg:
        abort(404)
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
        (msg["room_id"], me["id"]),
    ).fetchone():
        abort(403)

    data = request.get_json(silent=True) or {}
    ack_type = data.get("ack_type", "ok")
    if ack_type not in ACK_TYPES:
        return jsonify({"error": "ack_type 은 ok/doing/done/reject"}), 400
    comment = (data.get("comment") or "").strip() or None

    existing = db.execute(
        "SELECT id FROM message_acks WHERE message_id=? AND user_id=? AND ack_type=?",
        (message_id, me["id"], ack_type),
    ).fetchone()

    now = datetime.now(timezone.utc).isoformat()
    if existing:
        # 토글: 해제
        db.execute("DELETE FROM message_acks WHERE id = ?", (existing["id"],))
        action = "removed"
    else:
        db.execute(
            "INSERT INTO message_acks (message_id, user_id, ack_type, comment, created_at) VALUES (?,?,?,?,?)",
            (message_id, me["id"], ack_type, comment, now),
        )
        action = "added"
    db.commit()

    socketio.emit("ack_updated", {
        "message_id": message_id,
        "user_id": me["id"],
        "display_name": me["display_name"],
        "ack_type": ack_type,
        "action": action,
        "comment": comment,
    }, to=f"room_{msg['room_id']}")
    return jsonify({"action": action, "ack_type": ack_type})


@app.route("/api/messages/<int:message_id>/acks")
@login_required
def api_message_acks_list(message_id):
    """메시지의 ack 누적 + 미확인자 목록."""
    me = current_user()
    db = get_db()
    msg = db.execute("SELECT room_id, user_id FROM messages WHERE id = ?", (message_id,)).fetchone()
    if not msg:
        abort(404)
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?", (msg["room_id"], me["id"])
    ).fetchone():
        abort(403)

    acks = db.execute("""
        SELECT a.user_id, a.ack_type, a.comment, a.created_at,
               u.display_name, u.avatar_color
          FROM message_acks a
          JOIN users u ON u.id = a.user_id
         WHERE a.message_id = ?
         ORDER BY a.created_at
    """, (message_id,)).fetchall()

    # 방 멤버 중 ack 안 한 사람 — 메시지 작성자는 제외 (본인이 본인 글 ack 할 필요 없음)
    members = db.execute("""
        SELECT u.id, u.display_name, u.avatar_color
          FROM room_members rm JOIN users u ON u.id = rm.user_id
         WHERE rm.room_id = ?
    """, (msg["room_id"],)).fetchall()
    acked_ids = {a["user_id"] for a in acks}
    pending = [
        dict(m) for m in members
        if m["id"] not in acked_ids and m["id"] != msg["user_id"]
    ]
    return jsonify({
        "acks": [dict(a) for a in acks],
        "pending": pending,
    })


# ---------- 메시지 별표 (중요 결정 마킹) ----------
@app.route("/api/messages/<int:message_id>/star", methods=["POST"])
@login_required
def api_message_star(message_id):
    """메시지 별표 토글 — 중요 결정·합의·이정표 마킹. 사용자별."""
    me = current_user()
    db = get_db()
    msg = db.execute("SELECT room_id FROM messages WHERE id = ?", (message_id,)).fetchone()
    if not msg:
        abort(404)
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?", (msg["room_id"], me["id"])
    ).fetchone():
        abort(403)
    existing = db.execute(
        "SELECT 1 FROM message_stars WHERE message_id=? AND user_id=?",
        (message_id, me["id"]),
    ).fetchone()
    if existing:
        db.execute("DELETE FROM message_stars WHERE message_id=? AND user_id=?", (message_id, me["id"]))
        action = "removed"
    else:
        db.execute(
            "INSERT INTO message_stars (message_id, user_id, starred_at) VALUES (?,?,?)",
            (message_id, me["id"], datetime.now(timezone.utc).isoformat()),
        )
        action = "added"
    db.commit()
    return jsonify({"action": action})


@app.route("/api/rooms/<int:room_id>/starred")
@login_required
def api_room_starred(room_id):
    """방 안에서 본인이 별표한 메시지 모음 — 인수인계·결정 정리용."""
    me = current_user()
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?", (room_id, me["id"])
    ).fetchone():
        abort(403)
    rows = db.execute("""
        SELECT m.id, m.content, m.kind, m.created_at, m.file_name, m.file_path,
               u.display_name, u.avatar_color
          FROM message_stars s
          JOIN messages m ON m.id = s.message_id
          JOIN users u ON u.id = m.user_id
         WHERE m.room_id = ? AND s.user_id = ?
         ORDER BY s.starred_at DESC
    """, (room_id, me["id"])).fetchall()
    return jsonify([dict(r) for r in rows])


# ---------- AI 요약·재작성 (Claude Haiku) ----------
# Slack AI / Teams Copilot 식 — 채널 일간 요약 / 긴 스레드 요약 / 작성 톤 조정.
# 한국어 1순위. Slack AI 가 한국어 미지원이라 즉시 차별화 가능.
AI_SUMMARY_MODEL = os.environ.get("KNK_MSG_AI_SUMMARY_MODEL", "claude-haiku-4-5")


def _claude_summarize_messages(messages_payload, mode="channel"):
    """메시지 리스트를 요약. mode='channel' (방의 최근 N개) 또는 'thread' (스레드).
    messages_payload: [{display_name, content, created_at, kind}, ...]
    반환: ({summary_text, in_tokens, out_tokens, cost_usd}, None) 또는 (None, err)."""
    try:
        import anthropic
    except ImportError:
        return None, "anthropic SDK 미설치"
    if not ANTHROPIC_API_KEY:
        return None, "ANTHROPIC_API_KEY 환경변수 미설정"
    if not messages_payload:
        return None, "요약할 메시지가 없습니다"

    # 메시지를 자연어 transcript 로 변환 (LLM 가독성)
    lines = []
    for m in messages_payload:
        if m.get("kind") == "system":
            continue
        ts = m.get("created_at", "")
        try:
            from datetime import datetime as _dt
            dt = _dt.fromisoformat(ts.replace("Z", "+00:00")) if ts else None
            ts_short = dt.strftime("%m-%d %H:%M") if dt else ""
        except Exception:
            ts_short = ts[:16]
        name = m.get("display_name", "?")
        content = (m.get("content") or "").strip()
        if not content:
            content = f"[{m.get('kind','파일')}]"
        lines.append(f"[{ts_short}] {name}: {content}")
    transcript = "\n".join(lines)
    if not transcript:
        return None, "요약할 본문이 비어있음"

    mode_label = "스레드 토론" if mode == "thread" else "채팅방 대화"
    system_prompt = f"""You are a Korean business communication assistant for KNK Corporation (industrial machinery / inspection equipment).

Your job: Summarize the following Korean {mode_label} for a busy executive (대표/임원).

Output format (Korean):
**핵심 요약** (1~2 문장)
**주요 결정사항** (불릿)
**미결사항·후속조치** (불릿, 담당자 명시)
**관련 인물** (이름 나열)

Rules:
- Maximum 350 한글 글자. 짧고 명확하게.
- 기술 용어·품번(예: 003M2501, WP-LOA)·고객사명은 원문 그대로.
- 추측 금지. 본문에 없으면 "없음".
- 정중한 평어체 (보고서 톤). "~함", "~확인 필요" 같은 어조.
"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        msg = client.messages.create(
            model=AI_SUMMARY_MODEL,
            max_tokens=1024,
            system=[
                {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}},
            ],
            messages=[
                {"role": "user", "content": f"다음 {mode_label}을 요약해 주세요:\n\n{transcript}"},
            ],
        )
        summary = "".join(b.text for b in msg.content if hasattr(b, "text")).strip()
        in_t = msg.usage.input_tokens
        out_t = msg.usage.output_tokens
        cost = (in_t / 1_000_000.0) * 1.0 + (out_t / 1_000_000.0) * 5.0
        return {
            "summary_text": summary,
            "in_tokens": in_t,
            "out_tokens": out_t,
            "cost_usd": cost,
            "model": AI_SUMMARY_MODEL,
        }, None
    except Exception as e:
        return None, f"Claude API 오류: {e}"


def _claude_summarize_for_history(messages_payload, item_meta=None):
    """프로젝트(아이템 방) 이력용 요약 — HAIST WORKS 프로젝트 이력 포맷.
    messages_payload 는 _claude_summarize_messages 와 같은 dict 리스트.
    item_meta 는 {code, name, customer, status} (있으면 컨텍스트로 전달).
    반환 형식: 기존 함수와 동일 ({summary_text, in_tokens, out_tokens, cost_usd, model}, None)."""
    try:
        import anthropic
    except ImportError:
        return None, "anthropic SDK 미설치"
    if not ANTHROPIC_API_KEY:
        return None, "ANTHROPIC_API_KEY 환경변수 미설정"
    if not messages_payload:
        return None, "요약할 메시지가 없습니다"

    # transcript 빌드
    lines = []
    for m in messages_payload:
        if m.get("kind") == "system":
            continue
        ts = m.get("created_at", "")
        try:
            from datetime import datetime as _dt
            dt = _dt.fromisoformat(ts.replace("Z", "+00:00")) if ts else None
            ts_short = dt.strftime("%m-%d %H:%M") if dt else ""
        except Exception:
            ts_short = ts[:16]
        name = m.get("display_name", "?")
        content = (m.get("content") or "").strip()
        kind = m.get("kind", "text")
        file_name = m.get("file_name")
        if kind == "image" and file_name:
            content = f"[사진: {file_name}] " + content
        elif kind == "file" and file_name:
            content = f"[파일: {file_name}] " + content
        if not content:
            content = f"[{kind}]"
        lines.append(f"[{ts_short}] {name}: {content}")
    transcript = "\n".join(lines)
    if not transcript:
        return None, "요약할 본문이 비어있음"

    item_ctx = ""
    if item_meta:
        bits = []
        if item_meta.get("code"): bits.append(f"품번 {item_meta['code']}")
        if item_meta.get("name"): bits.append(f"아이템명 {item_meta['name']}")
        if item_meta.get("customer"): bits.append(f"고객사 {item_meta['customer']}")
        if item_meta.get("status"): bits.append(f"상태 {item_meta['status']}")
        if bits:
            item_ctx = "\n[프로젝트 컨텍스트] " + " · ".join(bits) + "\n"

    system_prompt = f"""You are a Korean business communication assistant for KNK Corporation (industrial machinery / inspection equipment).

Your job: Summarize the following Korean project conversation as PROJECT HISTORY for HAIST WORKS (ERP system).
This summary will be saved as the official project log.

Output structure (Korean, in this exact order):

**기간 요약** (1~2 문장 — 이번 기간에 무엇이 진행되었는지 핵심)

**주요 결정사항**
- (담당자) 결정 내용 (날짜)
- ...

**진척 상황**
- 이번 기간 완료된 작업
- 진행 중인 작업

**미결 사항 / 후속조치**
- (담당자) 해야 할 것 (기한)
- ...

**관련 인물**
- 이름 나열 (쉼표 구분)

**언급된 외부 거래처·품번**
- 거래처명, 품번 등 (있으면)

Rules:
- 최대 600 한글 글자.
- 기술 용어·품번(예: 003M2501, WP-LOA)·고객사명은 원문 그대로.
- 추측 금지. 본문에 없으면 "없음".
- 정중한 평어체 (보고서 톤). "~함", "~확인 필요", "~예정".
- 시간은 가능하면 명시 (예: 5월 17일 14:00).
{item_ctx}"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        msg = client.messages.create(
            model=AI_SUMMARY_MODEL,
            max_tokens=2048,
            system=[
                {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}},
            ],
            messages=[
                {"role": "user", "content": f"다음 프로젝트 대화를 이력 보고서로 요약해 주세요:\n\n{transcript}"},
            ],
        )
        summary = "".join(b.text for b in msg.content if hasattr(b, "text")).strip()
        in_t = msg.usage.input_tokens
        out_t = msg.usage.output_tokens
        cost = (in_t / 1_000_000.0) * 1.0 + (out_t / 1_000_000.0) * 5.0
        return {
            "summary_text": summary,
            "in_tokens": in_t,
            "out_tokens": out_t,
            "cost_usd": cost,
            "model": AI_SUMMARY_MODEL,
        }, None
    except Exception as e:
        return None, f"Claude API 오류: {e}"


def _generate_project_history(room_id, created_by_uid=None):
    """방의 마지막 history 이후 새 메시지를 AI 요약 + 첨부 정리해서 1개 스냅샷 생성.
    created_by_uid 가 None 이면 자동(워커), 값이 있으면 수동(사용자).
    반환: (history_dict, None) 또는 (None, err_str). 새 메시지 0개면 (None, 'no_new')."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        # 마지막 스냅샷 last_message_id
        last_snap = db.execute(
            "SELECT last_message_id FROM project_history WHERE room_id=? ORDER BY id DESC LIMIT 1",
            (room_id,),
        ).fetchone()
        last_mid_cursor = last_snap["last_message_id"] if last_snap else 0

        # 그 이후 새 메시지 (시스템 제외, 스레드 답글 제외 — 메인 타임라인만)
        rows = db.execute("""
            SELECT m.id, m.content, m.kind, m.created_at,
                   m.file_path, m.file_name, m.file_size, m.file_mime,
                   u.display_name
              FROM messages m JOIN users u ON u.id = m.user_id
             WHERE m.room_id = ? AND m.id > ?
               AND m.kind != 'system'
               AND m.parent_message_id IS NULL
             ORDER BY m.id ASC
        """, (room_id, last_mid_cursor)).fetchall()

        if not rows:
            return None, "no_new"
        if len(rows) < 2 and created_by_uid is None:
            # 자동 워커: 메시지 1개만으론 의미있는 요약 어려움. 다음 사이클에 시도.
            return None, "too_few"

        # 아이템 메타
        item_meta = None
        item_row = db.execute("""
            SELECT it.code, it.name, it.customer, it.status
              FROM items it WHERE it.room_id=?
        """, (room_id,)).fetchone()
        if item_row:
            item_meta = dict(item_row)

        # AI 요약
        result, err = _claude_summarize_for_history([dict(r) for r in rows], item_meta=item_meta)
        if err:
            return None, err

        # 첨부 정리
        attachments = []
        for r in rows:
            if r["file_path"]:
                attachments.append({
                    "message_id": r["id"],
                    "name": r["file_name"] or r["file_path"],
                    "size": r["file_size"],
                    "mime": r["file_mime"],
                    "url": f"{BASE_PATH}/uploads/{r['file_path']}",
                    "sender": r["display_name"],
                    "sent_at": r["created_at"],
                })

        now = datetime.now(timezone.utc).isoformat()
        first_mid = rows[0]["id"]
        last_mid = rows[-1]["id"]
        period_start = rows[0]["created_at"]
        period_end = rows[-1]["created_at"]

        cur = db.execute("""
            INSERT INTO project_history
                (room_id, period_start, period_end, first_message_id, last_message_id,
                 summary_text, message_count, attachment_count, attachments_json,
                 model, input_tokens, output_tokens, cost_usd,
                 created_by, created_at)
            VALUES (?,?,?,?,?, ?,?,?,?, ?,?,?,?, ?,?)
        """, (
            room_id, period_start, period_end, first_mid, last_mid,
            result["summary_text"], len(rows), len(attachments),
            json.dumps(attachments, ensure_ascii=False),
            result["model"], result["in_tokens"], result["out_tokens"], result["cost_usd"],
            created_by_uid, now,
        ))
        hid = cur.lastrowid
        db.commit()
        return {
            "id": hid,
            "room_id": room_id,
            "period_start": period_start,
            "period_end": period_end,
            "first_message_id": first_mid,
            "last_message_id": last_mid,
            "summary_text": result["summary_text"],
            "message_count": len(rows),
            "attachment_count": len(attachments),
            "attachments": attachments,
            "model": result["model"],
            "cost_usd": result["cost_usd"],
            "created_by": created_by_uid,
            "created_at": now,
        }, None
    finally:
        db.close()


def _auto_generate_project_histories():
    """모든 아이템 방에 대해 자동 이력 생성 (하루 1회 호출)."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        rooms = db.execute("""
            SELECT id, name FROM rooms WHERE type='item'
        """).fetchall()
    finally:
        db.close()
    generated = 0
    for r in rooms:
        try:
            hist, err = _generate_project_history(r["id"], created_by_uid=None)
            if hist:
                generated += 1
                print(f"[project_history] auto-generated for room {r['id']} ({r['name']})")
            elif err and err not in ("no_new", "too_few"):
                print(f"[project_history] room {r['id']} failed: {err}")
        except Exception as e:
            print(f"[project_history] room {r['id']} exception: {e}")
    print(f"[project_history] auto run complete — generated {generated} snapshots")
    return generated


# 자동 이력 워커 — 하루 1회 (24시간 = 86400 초)
_phist_thread_started = False
def _start_project_history_worker():
    global _phist_thread_started
    if _phist_thread_started:
        return
    _phist_thread_started = True
    def _loop():
        import time as _t
        # 서버 시작 직후 30분 대기 (안정화 후 첫 실행)
        _t.sleep(30 * 60)
        while True:
            try:
                _auto_generate_project_histories()
            except Exception as e:
                print(f"[project_history worker] error: {e}")
            _t.sleep(24 * 60 * 60)   # 24시간
    import threading as _th
    _th.Thread(target=_loop, daemon=True).start()


REWRITE_TONES = {
    "formal":       "정중한 공식 비즈니스 한국어 (존댓말, ~합니다체)",
    "short":        "동일한 의미를 유지하면서 가능한 한 짧게 (1~2 문장)",
    "professional": "기술·업무 보고서 톤. 간결하고 명확하게",
    "casual":       "동료 간 가벼운 말투 (~네요, ~할게요)",
    "polite":       "외부 거래처에 보내는 정중한 한국어",
}


def _claude_rewrite(text, tone="formal"):
    """작성 톤 조정 (Slack AI Compose 식)."""
    try:
        import anthropic
    except ImportError:
        return None, "anthropic SDK 미설치"
    if not ANTHROPIC_API_KEY:
        return None, "ANTHROPIC_API_KEY 환경변수 미설정"
    text = (text or "").strip()
    if not text:
        return None, "재작성할 텍스트가 비어있음"
    tone_desc = REWRITE_TONES.get(tone, REWRITE_TONES["formal"])
    system_prompt = f"""You are a Korean business writing assistant for KNK Corporation.

Rewrite the user's draft message in the following tone:
{tone_desc}

Rules:
- 원문 의미·정보는 100% 보존.
- 기술 용어·품번(003M2501, WP-LOA 등)·고객사명·@멘션·이모지는 그대로.
- 한국어로만 출력. 설명·메모 없이 다듬은 메시지 본문만 출력.
- 1줄 입력은 1줄 출력. 여러 줄은 줄바꿈 유지.
"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        msg = client.messages.create(
            model=AI_SUMMARY_MODEL,
            max_tokens=1024,
            system=[
                {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}},
            ],
            messages=[
                {"role": "user", "content": text},
            ],
        )
        rewritten = "".join(b.text for b in msg.content if hasattr(b, "text")).strip()
        in_t = msg.usage.input_tokens
        out_t = msg.usage.output_tokens
        cost = (in_t / 1_000_000.0) * 1.0 + (out_t / 1_000_000.0) * 5.0
        return {
            "text": rewritten,
            "in_tokens": in_t,
            "out_tokens": out_t,
            "cost_usd": cost,
            "model": AI_SUMMARY_MODEL,
        }, None
    except Exception as e:
        return None, f"Claude API 오류: {e}"


# ---------- AI 번역 (Claude Haiku) ----------
# KNK 업계(사출·금형·메탈·도면) 용어 사전. 번역 일관성 + 정확도 향상.
KNK_GLOSSARY = """
[KNK 업무 용어 — 번역 시 일관성 유지]
- 사출 = injection molding (vi: ép phun nhựa)
- 금형 = mold (vi: khuôn mẫu)
- 메탈 = metal (vi: kim loại)
- 도면 = drawing / blueprint (vi: bản vẽ)
- 납기 = delivery date / due date (vi: ngày giao hàng)
- 검사기 = inspection machine / inspector (vi: máy kiểm tra)
- 치수 = dimension (vi: kích thước)
- LOA = Letter of Agreement
- 검수 = inspection / acceptance (vi: nghiệm thu)
- 품번 = part number (vi: mã sản phẩm)
- 발주 = purchase order (vi: đặt hàng)
- 견적 = quotation (vi: báo giá)
- 협력사 = supplier / partner (vi: nhà cung cấp)
- 고객사 = customer (vi: khách hàng)
- 케이엔케이 / KNK = ㈜케이엔케이
- 하이스트 / HAIST = HAIST Innovation
- 베트남법인 = Vietnam branch (vi: chi nhánh Việt Nam)
"""


def _claude_translate(text, target_lang_code):
    """Claude Haiku 호출. 성공 시 (translated_text, source_lang, in_tokens, out_tokens, cost_usd)."""
    target_name = TRANSLATE_LANGS.get(target_lang_code)
    if not target_name:
        return None, f"지원 안 되는 언어: {target_lang_code}"

    # === 데모 모드: API 키 없이 UI 흐름 테스트 (무료) ===
    if TRANSLATE_MOCK:
        # 간단한 KNK 핵심 용어 미니 사전 — 실제 번역처럼 보이는 데모용 변환
        mini_dict = {
            "vi": {
                "안녕하세요": "Xin chào",
                "감사합니다": "Cảm ơn",
                "도면": "bản vẽ",
                "사출": "ép phun nhựa",
                "금형": "khuôn mẫu",
                "납기": "ngày giao hàng",
                "오늘": "hôm nay",
                "내일": "ngày mai",
                "부탁드립니다": "vui lòng",
                "확인": "xác nhận",
                "메탈": "kim loại",
                "검사기": "máy kiểm tra",
                "치수": "kích thước",
                "수정": "sửa đổi",
            },
            "en": {
                "안녕하세요": "Hello",
                "감사합니다": "Thank you",
                "도면": "drawing",
                "사출": "injection molding",
                "금형": "mold",
                "납기": "due date",
                "오늘": "today",
                "내일": "tomorrow",
                "부탁드립니다": "please",
                "확인": "confirm",
                "메탈": "metal",
                "검사기": "inspection machine",
                "치수": "dimension",
                "수정": "modify",
            },
            "ko": {
                "Xin chào": "안녕하세요",
                "Cảm ơn": "감사합니다",
                "Hello": "안녕하세요",
                "Thank you": "감사합니다",
            },
        }
        translated = text
        for k, v in mini_dict.get(target_lang_code, {}).items():
            translated = translated.replace(k, v)
        # 실제 번역과 구분되도록 명시
        translated = f"[데모 {target_lang_code.upper()}] {translated}"
        return (translated, None, 0, 0, 0.0), None

    # === 실제 Claude API 호출 ===
    try:
        import anthropic
    except ImportError:
        return None, "anthropic SDK 미설치 (requirements.txt 의 anthropic 설치 필요)"

    if not ANTHROPIC_API_KEY:
        return None, "ANTHROPIC_API_KEY 환경변수 미설정"

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    system_prompt = f"""You are a professional Korean-Vietnamese-English business translator for KNK Corporation, a Korean industrial machinery and inspection equipment company with a Vietnam branch.

{KNK_GLOSSARY}

Rules:
1. Translate ONLY into {target_name}. Do NOT add explanations or notes.
2. Preserve technical part numbers (e.g. 003M2501, WP-LOA), brand names, file paths, URLs, @mentions.
3. Use formal business tone (한국어: 존댓말, 베트남어: anh/chị + ạ, English: professional).
4. If the source is already in {target_name}, return the source as-is (do not translate to itself).
5. Keep emoji and formatting (newlines, bullets) as-is.
6. Output ONLY the translated text, nothing else.
"""

    try:
        msg = client.messages.create(
            model=TRANSLATE_MODEL,
            max_tokens=1024,
            system=[
                {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}},
            ],
            messages=[
                {"role": "user", "content": f"Translate the following to {target_name}:\n\n{text}"},
            ],
        )
        translated = "".join(b.text for b in msg.content if hasattr(b, "text")).strip()
        in_t = msg.usage.input_tokens
        out_t = msg.usage.output_tokens
        # Haiku 4.5 가격: $1/MTok input, $5/MTok output (대략)
        cost = (in_t / 1_000_000.0) * 1.0 + (out_t / 1_000_000.0) * 5.0
        return (translated, None, in_t, out_t, cost), None
    except Exception as e:
        return None, f"Claude API 오류: {e}"


def _translate_monthly_cost():
    """이번 달 누적 번역 비용 (USD)."""
    db = get_db()
    row = db.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) AS total FROM message_translations WHERE date(created_at) >= date('now', 'start of month')"
    ).fetchone()
    return float(row["total"] or 0)


@app.route("/api/rooms/<int:room_id>/summarize", methods=["POST"])
@login_required
def api_room_summarize(room_id):
    """방의 최근 N개 메시지(또는 since 이후) AI 요약.
    body: {limit?: int=80, since?: 'YYYY-MM-DD', force?: bool}
    캐시 동작: 마지막 메시지 ID 기준 캐싱. 같은 ID 면 재생성 안 함 (비용 절감)."""
    me = current_user()
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
        (room_id, me["id"]),
    ).fetchone():
        abort(403)
    data = request.get_json(silent=True) or {}
    limit = int(data.get("limit") or 80)
    if limit < 5: limit = 5
    if limit > 300: limit = 300
    since = data.get("since")  # 'YYYY-MM-DD'
    force = bool(data.get("force"))

    # 메시지 수집 — 스레드 부모만 (메인 타임라인 기준). 시스템 메시지 제외.
    if since:
        rows = db.execute("""
            SELECT m.id, m.content, m.kind, m.created_at,
                   u.display_name
              FROM messages m
              JOIN users u ON u.id = m.user_id
             WHERE m.room_id = ? AND m.parent_message_id IS NULL
               AND m.kind != 'system'
               AND date(m.created_at) >= date(?)
             ORDER BY m.id ASC
        """, (room_id, since)).fetchall()
        scope_key = f"room:{room_id}:since:{since}"
    else:
        rows = db.execute("""
            SELECT m.id, m.content, m.kind, m.created_at,
                   u.display_name
              FROM messages m
              JOIN users u ON u.id = m.user_id
             WHERE m.room_id = ? AND m.parent_message_id IS NULL
               AND m.kind != 'system'
             ORDER BY m.id DESC
             LIMIT ?
        """, (room_id, limit)).fetchall()
        rows = list(reversed(rows))   # 시간 순으로
        scope_key = f"room:{room_id}:last:{limit}"

    if not rows:
        return jsonify({"summary": "요약할 메시지가 없습니다.", "cached": False, "message_count": 0})

    last_msg_id = rows[-1]["id"]
    # 캐시 조회
    if not force:
        cached = db.execute("""
            SELECT summary_text, created_at, model, input_tokens, output_tokens
              FROM ai_summaries
             WHERE scope_type='channel' AND scope_key=? AND last_message_id=?
             ORDER BY id DESC LIMIT 1
        """, (scope_key, last_msg_id)).fetchone()
        if cached:
            return jsonify({
                "summary": cached["summary_text"],
                "cached": True,
                "cached_at": cached["created_at"],
                "model": cached["model"],
                "message_count": len(rows),
            })

    # Claude 호출
    payload = [dict(r) for r in rows]
    result, err = _claude_summarize_messages(payload, mode="channel")
    if err:
        return jsonify({"error": err}), 500
    # 캐시 저장
    now = datetime.now(timezone.utc).isoformat()
    db.execute("""
        INSERT INTO ai_summaries
            (scope_type, scope_key, room_id, last_message_id, summary_text,
             model, input_tokens, output_tokens, cost_usd, created_by, created_at)
        VALUES ('channel', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (scope_key, room_id, last_msg_id, result["summary_text"],
          result["model"], result["in_tokens"], result["out_tokens"],
          result["cost_usd"], me["id"], now))
    db.commit()
    return jsonify({
        "summary": result["summary_text"],
        "cached": False,
        "model": result["model"],
        "input_tokens": result["in_tokens"],
        "output_tokens": result["out_tokens"],
        "cost_usd": result["cost_usd"],
        "message_count": len(rows),
    })


@app.route("/api/messages/<int:message_id>/summarize_thread", methods=["POST"])
@login_required
def api_thread_summarize(message_id):
    """스레드(부모 + 답글 전체) AI 요약. 캐시는 마지막 답글 ID 기준."""
    me = current_user()
    db = get_db()
    parent = db.execute("""
        SELECT m.id, m.room_id, m.content, m.kind, m.created_at,
               u.display_name
          FROM messages m JOIN users u ON u.id = m.user_id
         WHERE m.id = ?
    """, (message_id,)).fetchone()
    if not parent:
        return jsonify({"error": "not found"}), 404
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
        (parent["room_id"], me["id"]),
    ).fetchone():
        abort(403)
    replies = db.execute("""
        SELECT m.id, m.content, m.kind, m.created_at,
               u.display_name
          FROM messages m JOIN users u ON u.id = m.user_id
         WHERE m.parent_message_id = ?
         ORDER BY m.id ASC
    """, (message_id,)).fetchall()
    all_rows = [dict(parent)] + [dict(r) for r in replies]
    if len(all_rows) < 3:
        return jsonify({"summary": "요약할 만큼 답글이 충분하지 않습니다 (3개 이상 필요).", "cached": False})
    data = request.get_json(silent=True) or {}
    force = bool(data.get("force"))
    last_id = replies[-1]["id"] if replies else parent["id"]
    scope_key = f"thread:{message_id}"
    if not force:
        cached = db.execute("""
            SELECT summary_text, created_at, model
              FROM ai_summaries
             WHERE scope_type='thread' AND scope_key=? AND last_message_id=?
             ORDER BY id DESC LIMIT 1
        """, (scope_key, last_id)).fetchone()
        if cached:
            return jsonify({
                "summary": cached["summary_text"],
                "cached": True,
                "cached_at": cached["created_at"],
                "model": cached["model"],
                "message_count": len(all_rows),
            })
    result, err = _claude_summarize_messages(all_rows, mode="thread")
    if err:
        return jsonify({"error": err}), 500
    now = datetime.now(timezone.utc).isoformat()
    db.execute("""
        INSERT INTO ai_summaries
            (scope_type, scope_key, room_id, last_message_id, summary_text,
             model, input_tokens, output_tokens, cost_usd, created_by, created_at)
        VALUES ('thread', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (scope_key, parent["room_id"], last_id, result["summary_text"],
          result["model"], result["in_tokens"], result["out_tokens"],
          result["cost_usd"], me["id"], now))
    db.commit()
    return jsonify({
        "summary": result["summary_text"],
        "cached": False,
        "model": result["model"],
        "message_count": len(all_rows),
        "input_tokens": result["in_tokens"],
        "output_tokens": result["out_tokens"],
        "cost_usd": result["cost_usd"],
    })


@app.route("/api/ai/rewrite", methods=["POST"])
@login_required
def api_ai_rewrite():
    """작성 톤 조정 (Slack AI Compose 식).
    body: {text: str, tone: 'formal'|'short'|'professional'|'casual'|'polite'}"""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    tone = data.get("tone") or "formal"
    if tone not in REWRITE_TONES:
        return jsonify({"error": f"tone 은 {list(REWRITE_TONES.keys())} 중 하나"}), 400
    if not text:
        return jsonify({"error": "text 필수"}), 400
    if len(text) > 4000:
        return jsonify({"error": "text 4000 자 제한"}), 400
    result, err = _claude_rewrite(text, tone=tone)
    if err:
        return jsonify({"error": err}), 500
    return jsonify({
        "text": result["text"],
        "model": result["model"],
        "input_tokens": result["in_tokens"],
        "output_tokens": result["out_tokens"],
        "cost_usd": result["cost_usd"],
    })


@app.route("/api/rooms/<int:room_id>/history", methods=["GET"])
@login_required
def api_room_history_list(room_id):
    """프로젝트 이력 목록 — 시간 역순. 방 멤버 누구나 조회."""
    me = current_user()
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
        (room_id, me["id"]),
    ).fetchone():
        abort(403)
    rows = db.execute("""
        SELECT id, period_start, period_end, first_message_id, last_message_id,
               summary_text, message_count, attachment_count, attachments_json,
               model, cost_usd, created_by, created_at, synced_to_hw, synced_at
          FROM project_history
         WHERE room_id = ?
         ORDER BY id DESC
         LIMIT 200
    """, (room_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["attachments"] = json.loads(d.pop("attachments_json") or "[]")
        except Exception:
            d["attachments"] = []
        # created_by display_name 채우기
        if d.get("created_by"):
            u = db.execute("SELECT display_name FROM users WHERE id=?", (d["created_by"],)).fetchone()
            d["created_by_name"] = u["display_name"] if u else None
            d["created_mode"] = "manual"
        else:
            d["created_by_name"] = None
            d["created_mode"] = "auto"
        out.append(d)
    return jsonify(out)


@app.route("/api/rooms/<int:room_id>/history/generate", methods=["POST"])
@login_required
def api_room_history_generate(room_id):
    """수동 즉시 이력 생성. 방 멤버 누구나 가능 (이력 자체는 비용 발생 — 추후 권한 제한 검토)."""
    me = current_user()
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
        (room_id, me["id"]),
    ).fetchone():
        abort(403)
    # 아이템 방만 — 일반 방은 이력 비활성
    rtype = db.execute("SELECT type FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not rtype or rtype["type"] != "item":
        return jsonify({"error": "이력은 아이템 방에서만 생성 가능합니다"}), 400
    hist, err = _generate_project_history(room_id, created_by_uid=me["id"])
    if err == "no_new":
        return jsonify({"error": "마지막 이력 이후 새 메시지가 없습니다", "no_new": True}), 200
    if err == "too_few":
        return jsonify({"error": "새 메시지가 적어 의미 있는 요약이 어렵습니다 (수동은 1개부터 가능)", "too_few": True}), 200
    if err:
        return jsonify({"error": err}), 500
    return jsonify({"ok": True, "history": hist})


@app.route("/api/rooms/<int:room_id>/history/<int:history_id>", methods=["GET"])
@login_required
def api_room_history_get(room_id, history_id):
    """단일 이력 상세."""
    me = current_user()
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
        (room_id, me["id"]),
    ).fetchone():
        abort(403)
    r = db.execute("""
        SELECT * FROM project_history WHERE id=? AND room_id=?
    """, (history_id, room_id)).fetchone()
    if not r:
        return jsonify({"error": "not found"}), 404
    d = dict(r)
    try:
        d["attachments"] = json.loads(d.pop("attachments_json") or "[]")
    except Exception:
        d["attachments"] = []
    return jsonify(d)


@app.route("/api/messages/<int:message_id>/translate", methods=["POST"])
@login_required
def api_message_translate(message_id):
    """메시지 번역 — 캐시 우선, 없으면 Claude Haiku 호출.

    body: { "target_lang": "ko" | "vi" | "en" }
    """
    me = current_user()
    db = get_db()
    msg = db.execute(
        "SELECT id, room_id, content, kind FROM messages WHERE id = ?", (message_id,)
    ).fetchone()
    if not msg:
        abort(404)
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?", (msg["room_id"], me["id"])
    ).fetchone():
        abort(403)

    if msg["kind"] not in ("text", None) or not (msg["content"] or "").strip():
        return jsonify({"error": "번역 가능한 텍스트 메시지가 아닙니다."}), 400

    data = request.get_json(silent=True) or {}
    target_lang = data.get("target_lang", "vi")
    if target_lang not in TRANSLATE_LANGS:
        return jsonify({"error": f"지원 언어: {', '.join(TRANSLATE_LANGS.keys())}"}), 400

    # 1) 캐시 조회
    cached = db.execute(
        "SELECT translated_text, source_lang, model, created_at FROM message_translations WHERE message_id=? AND target_lang=?",
        (message_id, target_lang),
    ).fetchone()
    if cached:
        return jsonify({
            "message_id": message_id,
            "target_lang": target_lang,
            "translated_text": cached["translated_text"],
            "source_lang": cached["source_lang"],
            "model": cached["model"],
            "from_cache": True,
        })

    # 2) API 키 또는 데모 모드 확인
    if not ANTHROPIC_API_KEY and not TRANSLATE_MOCK:
        return jsonify({
            "error": "번역 서비스가 설정되지 않았습니다.",
            "hint": "1) 데모 모드: KNK_MSG_TRANSLATE_MOCK=1 환경변수 + 서버 재시작\n2) 실제 번역: ANTHROPIC_API_KEY 환경변수 + 서버 재시작",
        }), 503

    # 3) 월 비용 한도 가드
    monthly = _translate_monthly_cost()
    if monthly >= TRANSLATE_MONTHLY_USD_LIMIT:
        return jsonify({
            "error": f"이번 달 번역 비용 한도(${TRANSLATE_MONTHLY_USD_LIMIT}) 초과",
            "monthly_cost_usd": monthly,
            "hint": "캐시된 번역은 계속 사용 가능. 한도를 늘리려면 KNK_MSG_TRANSLATE_USD_LIMIT 환경변수 조정.",
        }), 429

    # 4) Claude 호출
    result, err = _claude_translate(msg["content"], target_lang)
    if err:
        return jsonify({"error": err}), 500

    translated, source_lang, in_t, out_t, cost = result

    # 5) 캐시 저장
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        """INSERT INTO message_translations
           (message_id, target_lang, source_lang, translated_text, model,
            input_tokens, output_tokens, cost_usd, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (message_id, target_lang, source_lang, translated, TRANSLATE_MODEL,
         in_t, out_t, cost, now),
    )
    db.commit()

    return jsonify({
        "message_id": message_id,
        "target_lang": target_lang,
        "translated_text": translated,
        "source_lang": source_lang,
        "model": TRANSLATE_MODEL,
        "from_cache": False,
        "cost_usd": round(cost, 6),
        "monthly_cost_usd": round(monthly + cost, 4),
    })


@app.route("/api/translate/status")
@login_required
def api_translate_status():
    """번역 기능 상태 — UI 가 메뉴 표시 여부 결정용."""
    return jsonify({
        "enabled": bool(ANTHROPIC_API_KEY) or TRANSLATE_MOCK,
        "mock_mode": TRANSLATE_MOCK,
        "model": "DEMO (mock)" if TRANSLATE_MOCK else TRANSLATE_MODEL,
        "languages": TRANSLATE_LANGS,
        "monthly_cost_usd": round(_translate_monthly_cost(), 4),
        "monthly_limit_usd": TRANSLATE_MONTHLY_USD_LIMIT,
    })


@app.route("/api/messages/send", methods=["POST"])
@login_required
def api_messages_send():
    """전송 시점 번역 지원 메시지 송신.

    body:
      room_id (int)        — 방 ID
      content (str)        — 원문
      translate_to (list[str], 선택) — 함께 첨부할 번역 언어들. 예: ["vi"], ["vi","en"]

    동작:
      1. 멤버십 확인
      2. translate_to 있으면 Claude 호출해서 번역 (캐시 가능 — 메시지 저장 후 message_translations 에 기록)
      3. 메시지 저장 (원문은 그대로)
      4. 번역들을 message_translations 에 저장 (메시지 로드 시 자동 inline 표시됨)
      5. socket new_message 로 broadcast (translations dict 포함 → 양국어 즉시 표시)

    이게 Socket 'send' 이벤트와 다른 점:
      - 번역 비용·시간 때문에 sync REST 로 분리
      - 보내는 사람이 양국어 동시에 만들어 발송 (카톡 번역의 한계 극복: 받은 사람만 번역되는 문제 X)
    """
    me = current_user()
    data = request.get_json(silent=True) or {}
    room_id = data.get("room_id")
    content = (data.get("content") or "").strip()
    translate_to = data.get("translate_to") or []

    if not isinstance(translate_to, list):
        translate_to = [translate_to] if translate_to else []
    translate_to = [t for t in translate_to if t in TRANSLATE_LANGS]

    if not room_id or not content:
        return jsonify({"error": "room_id 와 content 필수"}), 400
    try:
        room_id = int(room_id)
    except (TypeError, ValueError):
        return jsonify({"error": "room_id 가 숫자가 아닙니다"}), 400
    if len(content) > 4000:
        content = content[:4000]

    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
        (room_id, me["id"]),
    ).fetchone():
        abort(403)

    # 1) 번역 수행 (있으면)
    translations = {}  # lang -> translated_text
    translation_meta = {}  # lang -> (in_t, out_t, cost_usd, source_lang)

    if translate_to:
        if not ANTHROPIC_API_KEY and not TRANSLATE_MOCK:
            return jsonify({
                "error": "번역 서비스가 설정되지 않았습니다.",
                "hint": "1) 데모 모드: 메신저START.bat 실행 전 환경변수 KNK_MSG_TRANSLATE_MOCK=1 설정\n2) 실제 번역: ANTHROPIC_API_KEY 환경변수 설정 후 서버 재시작",
            }), 503

        # 월 비용 가드
        monthly = _translate_monthly_cost()
        if monthly >= TRANSLATE_MONTHLY_USD_LIMIT:
            return jsonify({
                "error": f"이번 달 번역 비용 한도(${TRANSLATE_MONTHLY_USD_LIMIT}) 초과",
                "hint": "한도를 늘리려면 KNK_MSG_TRANSLATE_USD_LIMIT 환경변수 조정",
            }), 429

        for lang in translate_to:
            result, err = _claude_translate(content, lang)
            if err:
                return jsonify({"error": f"{lang} 번역 실패: {err}"}), 500
            translated, source_lang, in_t, out_t, cost = result
            translations[lang] = translated
            translation_meta[lang] = (in_t, out_t, cost, source_lang)

    # 2) 메시지 저장
    now = datetime.now(timezone.utc).isoformat()
    cur = db.execute(
        "INSERT INTO messages (room_id, user_id, content, kind, created_at) VALUES (?,?,?,?,?)",
        (room_id, me["id"], content, "text", now),
    )
    mid = cur.lastrowid

    # 3) 번역 캐시 저장
    for lang, text in translations.items():
        in_t, out_t, cost, source_lang = translation_meta[lang]
        db.execute(
            """INSERT INTO message_translations
               (message_id, target_lang, source_lang, translated_text, model,
                input_tokens, output_tokens, cost_usd, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (mid, lang, source_lang, text, TRANSLATE_MODEL,
             in_t, out_t, cost, now),
        )
    db.commit()

    # 4) 사용자 정보 + broadcast
    u = db.execute(
        "SELECT display_name, avatar_color FROM users WHERE id=?", (me["id"],)
    ).fetchone()
    payload = {
        "id": mid,
        "room_id": room_id,
        "user_id": me["id"],
        "display_name": u["display_name"],
        "avatar_color": u["avatar_color"],
        "content": content,
        "kind": "text",
        "created_at": now,
        "translations": translations,  # {lang: text} - 클라이언트가 즉시 inline 렌더
    }
    socketio.emit("new_message", payload, to=f"room_{room_id}")

    # Web Push — 백그라운드 알림 (휴대폰 PWA 가 닫혀있어도 OS 알림 도착).
    # socket 'send' 이벤트는 이미 push 호출함. REST 라우트도 동일하게 처리.
    if PYWEBPUSH_OK:
        try:
            r = db.execute("SELECT name FROM rooms WHERE id=?", (room_id,)).fetchone()
            room_name = r["name"] if r and r["name"] else "채팅"
        except Exception:
            room_name = "채팅"
        push_title = f"💬 {u['display_name']} ({room_name})"
        push_body = content[:120]
        import threading
        threading.Thread(
            target=push_message_to_room_members,
            args=(room_id, me["id"], push_title, push_body),
            kwargs={"url": f"{BASE_PATH}/chat?room={room_id}", "tag": f"room_{room_id}"},
            daemon=True,
        ).start()

    return jsonify(payload)


# ---------- 파일 버전 체인 ----------
@app.route("/api/files/<int:message_id>/versions")
@login_required
def api_file_versions(message_id):
    """이 첨부 메시지가 속한 파일 버전 체인 전체."""
    me = current_user()
    db = get_db()
    msg = db.execute("SELECT room_id FROM messages WHERE id = ?", (message_id,)).fetchone()
    if not msg:
        abort(404)
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?", (msg["room_id"], me["id"])
    ).fetchone():
        abort(403)
    av = db.execute(
        "SELECT parent_message_id FROM attachment_versions WHERE message_id = ?", (message_id,)
    ).fetchone()
    if not av:
        return jsonify([])
    rows = db.execute("""
        SELECT av.message_id, av.version_no, av.parent_message_id,
               m.file_name, m.file_path, m.file_size, m.file_mime,
               m.user_id, m.created_at,
               u.display_name, u.avatar_color
          FROM attachment_versions av
          JOIN messages m ON m.id = av.message_id
          JOIN users u ON u.id = m.user_id
         WHERE av.parent_message_id = ?
         ORDER BY av.version_no DESC
    """, (av["parent_message_id"],)).fetchall()
    return jsonify([dict(r) for r in rows])


# ---------- 파일 업로드 / 다운로드 ----------
def ext_of(filename):
    return (filename.rsplit(".", 1)[-1] or "").lower() if "." in filename else ""


def is_image_ext(ext):
    return ext in ALLOWED_IMAGE_EXT


@app.route("/api/upload", methods=["POST"])
@login_required
def api_upload():
    me = current_user()
    room_id = request.form.get("room_id")
    if not room_id:
        return jsonify({"error": "room_id가 필요합니다."}), 400
    try:
        room_id = int(room_id)
    except (TypeError, ValueError):
        return jsonify({"error": "room_id가 숫자가 아닙니다."}), 400

    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?", (room_id, me["id"])
    ).fetchone():
        abort(403)

    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "파일이 없습니다."}), 400

    original = f.filename
    ext = ext_of(original)
    if ext and ext not in ALLOWED_FILE_EXT:
        return jsonify({"error": f"허용되지 않는 확장자(.{ext})"}), 400

    safe_base = secure_filename(original) or "file"
    if not ext_of(safe_base):
        safe_base = f"{safe_base}.{ext}" if ext else safe_base
    unique = f"{uuid.uuid4().hex[:12]}_{safe_base}"
    room_dir = os.path.join(UPLOAD_DIR, str(room_id))
    os.makedirs(room_dir, exist_ok=True)
    fpath = os.path.join(room_dir, unique)
    f.save(fpath)
    size = os.path.getsize(fpath)
    mime = f.mimetype or mimetypes.guess_type(unique)[0] or "application/octet-stream"

    kind = "image" if is_image_ext(ext) else "file"
    rel_path = f"{room_id}/{unique}"
    now = datetime.now(timezone.utc).isoformat()

    cur = db.execute("""
        INSERT INTO messages (room_id, user_id, content, kind, file_path, file_name, file_size, file_mime, created_at)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (room_id, me["id"], original, kind, rel_path, original, size, mime, now))
    mid = cur.lastrowid

    # 동일 방·동일 원본 파일명으로 이전 업로드 있으면 버전 체인 연결
    prev = db.execute("""
        SELECT av.parent_message_id, av.version_no
          FROM messages m
          JOIN attachment_versions av ON av.message_id = m.id
         WHERE m.room_id = ? AND m.file_name = ? AND m.id != ?
         ORDER BY av.version_no DESC LIMIT 1
    """, (room_id, original, mid)).fetchone()

    if prev:
        parent_id = prev["parent_message_id"]
        version_no = (prev["version_no"] or 1) + 1
    else:
        # 첫 버전 — 자기 자신이 부모
        # 같은 파일명의 가장 오래된 메시지를 부모로 (그동안 attachment_versions 없던 케이스)
        oldest = db.execute(
            "SELECT id FROM messages WHERE room_id=? AND file_name=? AND kind IN ('image','file') ORDER BY id ASC LIMIT 1",
            (room_id, original),
        ).fetchone()
        parent_id = oldest["id"] if oldest else mid
        # 부모도 attachment_versions 가 없으면 v1 으로 backfill
        if oldest and oldest["id"] != mid:
            existing_parent_av = db.execute(
                "SELECT 1 FROM attachment_versions WHERE message_id=?", (oldest["id"],)
            ).fetchone()
            if not existing_parent_av:
                db.execute(
                    "INSERT INTO attachment_versions (message_id, parent_message_id, version_no, room_id) VALUES (?,?,?,?)",
                    (oldest["id"], oldest["id"], 1, room_id),
                )
            # 그 사이 다른 버전 카운트 — 최대 version_no 기반
            max_v = db.execute(
                "SELECT MAX(version_no) AS m FROM attachment_versions WHERE parent_message_id = ?",
                (parent_id,),
            ).fetchone()
            version_no = (max_v["m"] or 1) + 1
        else:
            version_no = 1

    db.execute(
        "INSERT INTO attachment_versions (message_id, parent_message_id, version_no, room_id) VALUES (?,?,?,?)",
        (mid, parent_id, version_no, room_id),
    )
    db.commit()

    u = db.execute("SELECT display_name, avatar_color FROM users WHERE id=?", (me["id"],)).fetchone()
    payload = {
        "id": mid,
        "room_id": room_id,
        "user_id": me["id"],
        "display_name": u["display_name"],
        "avatar_color": u["avatar_color"],
        "content": original,
        "kind": kind,
        "file_path": rel_path,
        "file_name": original,
        "file_size": size,
        "file_mime": mime,
        "created_at": now,
        "version_no": version_no,
        "parent_message_id": parent_id,
    }
    socketio.emit("new_message", payload, to=f"room_{room_id}")
    return jsonify(payload)


@app.route("/uploads/<int:room_id>/<path:filename>")
@login_required
def serve_upload(room_id, filename):
    me = current_user()
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?", (room_id, me["id"])
    ).fetchone():
        abort(403)
    return send_from_directory(os.path.join(UPLOAD_DIR, str(room_id)), filename)


@app.route("/api/rooms/<int:room_id>/attachments")
@login_required
def api_room_attachments(room_id):
    me = current_user()
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?", (room_id, me["id"])
    ).fetchone():
        abort(403)
    kind = request.args.get("kind", "all")  # all | image | file
    sql = """
        SELECT m.id, m.kind, m.file_path, m.file_name, m.file_size, m.file_mime, m.created_at,
               u.id AS user_id, u.display_name, u.avatar_color
          FROM messages m JOIN users u ON u.id = m.user_id
         WHERE m.room_id = ? AND m.file_path IS NOT NULL
    """
    params = [room_id]
    if kind == "image":
        sql += " AND m.kind = 'image'"
    elif kind == "file":
        sql += " AND m.kind = 'file'"
    sql += " ORDER BY m.id DESC"
    rows = db.execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])


# ---------- 요청(티켓) ----------
@app.route("/api/rooms/<int:room_id>/requests")
@login_required
def api_requests_list(room_id):
    me = current_user()
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?", (room_id, me["id"])
    ).fetchone():
        abort(403)
    status = request.args.get("status")
    sql = """
        SELECT q.*, ub.display_name AS requested_by_name, ub.avatar_color AS requested_by_color,
               ua.display_name AS assigned_to_name, ua.avatar_color AS assigned_to_color,
               m.content AS source_message
          FROM requests q
          JOIN users ub ON ub.id = q.requested_by
          LEFT JOIN users ua ON ua.id = q.assigned_to
          LEFT JOIN messages m ON m.id = q.message_id
         WHERE q.room_id = ?
    """
    params = [room_id]
    if status:
        sql += " AND q.status = ?"
        params.append(status)
    sql += " ORDER BY (q.status='open') DESC, (q.due_date IS NULL), q.due_date ASC, q.id DESC"
    rows = db.execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/requests", methods=["POST"])
@login_required
def api_request_create():
    me = current_user()
    data = request.get_json(silent=True) or {}
    room_id = data.get("room_id")
    title = (data.get("title") or "").strip()
    if not room_id or not title:
        return jsonify({"error": "방과 제목은 필수입니다."}), 400
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?", (room_id, me["id"])
    ).fetchone():
        abort(403)
    now = datetime.now(timezone.utc).isoformat()
    cur = db.execute("""
        INSERT INTO requests (room_id, message_id, title, description, requested_by, assigned_to,
                              due_date, status, priority, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        room_id,
        data.get("message_id"),
        title,
        (data.get("description") or "").strip() or None,
        me["id"],
        data.get("assigned_to"),
        data.get("due_date") or None,
        "open",
        data.get("priority") or "normal",
        now, now,
    ))
    qid = cur.lastrowid

    # 시스템 메시지로 알림
    assignee_name = ""
    if data.get("assigned_to"):
        a = db.execute("SELECT display_name FROM users WHERE id=?", (data.get("assigned_to"),)).fetchone()
        if a:
            assignee_name = f" → {a['display_name']}"
    due_part = f" (납기 {data.get('due_date')})" if data.get("due_date") else ""
    sys_msg = f"📌 요청 등록{assignee_name}{due_part}: {title}"
    cur = db.execute(
        "INSERT INTO messages (room_id, user_id, content, kind, created_at) VALUES (?,?,?,?,?)",
        (room_id, me["id"], sys_msg, "system", now),
    )
    sys_mid = cur.lastrowid
    db.commit()

    # 채팅방에 시스템 메시지 emit
    socketio.emit("new_message", {
        "id": sys_mid, "room_id": room_id, "user_id": me["id"],
        "display_name": me["display_name"], "avatar_color": me["avatar_color"],
        "content": sys_msg, "kind": "system", "created_at": now,
    }, to=f"room_{room_id}")
    socketio.emit("requests_updated", {"room_id": room_id}, to=f"room_{room_id}")

    # Web Push: 담당자 직접 통지
    if PYWEBPUSH_OK and data.get("assigned_to") and int(data["assigned_to"]) != me["id"]:
        import threading
        room = db.execute("SELECT name FROM rooms WHERE id=?", (room_id,)).fetchone()
        room_name = room["name"] if room else ""
        push_title = f"📌 새 요청 — {me['display_name']}"
        push_body = f"[{room_name}] {title}" + (f" (납기 {data.get('due_date')})" if data.get("due_date") else "")
        threading.Thread(
            target=send_push_to_user,
            args=(int(data["assigned_to"]), push_title, push_body),
            kwargs={"url": f"{BASE_PATH}/chat?room={room_id}", "tag": f"req_{qid}"},
            daemon=True,
        ).start()

    return jsonify({"id": qid})


@app.route("/api/requests/<int:req_id>", methods=["PATCH"])
@login_required
def api_request_update(req_id):
    me = current_user()
    data = request.get_json(silent=True) or {}
    db = get_db()
    row = db.execute("SELECT * FROM requests WHERE id=?", (req_id,)).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
        (row["room_id"], me["id"])
    ).fetchone():
        abort(403)

    fields, args = [], []
    for f in ("title", "description", "assigned_to", "due_date", "status", "priority"):
        if f in data:
            v = data[f]
            if isinstance(v, str):
                v = v.strip() or None
            fields.append(f"{f} = ?")
            args.append(v)
    if not fields:
        return jsonify({"ok": True})
    now = datetime.now(timezone.utc).isoformat()
    args.append(now)
    if data.get("status") in ("done", "cancelled"):
        fields.append("closed_at = ?")
        args.append(now)
    args.append(req_id)
    db.execute(f"UPDATE requests SET {', '.join(fields)}, updated_at = ? WHERE id = ?", args)

    # 상태 변경 시 시스템 메시지
    if "status" in data:
        labels = {"open": "열림", "in_progress": "진행중", "done": "완료", "cancelled": "취소"}
        sys_msg = f"📌 요청 [{row['title']}] → {labels.get(data['status'], data['status'])}"
        cur = db.execute(
            "INSERT INTO messages (room_id, user_id, content, kind, created_at) VALUES (?,?,?,?,?)",
            (row["room_id"], me["id"], sys_msg, "system", now),
        )
        sys_mid = cur.lastrowid
        db.commit()
        socketio.emit("new_message", {
            "id": sys_mid, "room_id": row["room_id"], "user_id": me["id"],
            "display_name": me["display_name"], "avatar_color": me["avatar_color"],
            "content": sys_msg, "kind": "system", "created_at": now,
        }, to=f"room_{row['room_id']}")
    else:
        db.commit()

    socketio.emit("requests_updated", {"room_id": row["room_id"]}, to=f"room_{row['room_id']}")
    return jsonify({"ok": True})


@app.route("/api/my/requests")
@login_required
def api_my_requests():
    me = current_user()
    db = get_db()
    rows = db.execute("""
        SELECT q.*, r.name AS room_name, it.customer AS item_customer, it.code AS item_code,
               ub.display_name AS requested_by_name, ub.avatar_color AS requested_by_color
          FROM requests q
          JOIN rooms r ON r.id = q.room_id
          LEFT JOIN items it ON it.room_id = q.room_id
          JOIN users ub ON ub.id = q.requested_by
         WHERE q.assigned_to = ? AND q.status IN ('open','in_progress')
         ORDER BY (q.due_date IS NULL), q.due_date ASC, q.id DESC
    """, (me["id"],)).fetchall()
    return jsonify([dict(r) for r in rows])


# ---------- 검색 ----------
def fts_query_safe(q):
    # FTS5 query: 단어 단위로 분리 후 prefix 매칭. 특수문자 제거.
    tokens = re.findall(r"[\w가-힣]+", q)
    if not tokens:
        return None
    return " ".join(t + "*" for t in tokens)


@app.route("/api/rooms/<int:room_id>/summary")
@login_required
def api_room_summary(room_id):
    """방 요약 — 아이템 카드 헤더 / 다이제스트용 카운트"""
    me = current_user()
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?", (room_id, me["id"])
    ).fetchone():
        abort(403)
    counts = db.execute("""
        SELECT
            (SELECT COUNT(*) FROM messages WHERE room_id=? AND kind='text') AS text_count,
            (SELECT COUNT(*) FROM messages WHERE room_id=? AND kind='image') AS image_count,
            (SELECT COUNT(*) FROM messages WHERE room_id=? AND kind='file') AS file_count,
            (SELECT COUNT(*) FROM requests WHERE room_id=? AND status='open') AS open_requests,
            (SELECT COUNT(*) FROM requests WHERE room_id=? AND status='in_progress') AS active_requests,
            (SELECT COUNT(*) FROM requests WHERE room_id=? AND status='done') AS done_requests,
            (SELECT MAX(created_at) FROM messages WHERE room_id=?) AS last_activity,
            (SELECT COUNT(*) FROM room_members WHERE room_id=?) AS members
    """, (room_id, room_id, room_id, room_id, room_id, room_id, room_id, room_id)).fetchone()
    return jsonify(dict(counts))


@app.route("/api/items/dashboard")
@login_required
def api_items_dashboard():
    """전체 아이템 대시보드 — 카운트·최근활동 한눈"""
    me = current_user()
    db = get_db()
    rows = db.execute("""
        SELECT r.id AS room_id, r.name, it.code, it.customer, it.status, it.due_date,
               (SELECT COUNT(*) FROM messages WHERE room_id=r.id AND kind='image') AS image_count,
               (SELECT COUNT(*) FROM messages WHERE room_id=r.id AND kind='file') AS file_count,
               (SELECT COUNT(*) FROM requests WHERE room_id=r.id AND status='open') AS open_requests,
               (SELECT COUNT(*) FROM requests WHERE room_id=r.id AND status='in_progress') AS active_requests,
               (SELECT MAX(created_at) FROM messages WHERE room_id=r.id) AS last_activity
          FROM rooms r
          JOIN items it ON it.room_id = r.id
          JOIN room_members rm ON rm.room_id = r.id AND rm.user_id = ?
         ORDER BY (it.status = 'active') DESC, last_activity DESC NULLS LAST
    """, (me["id"],)).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/digest")
@login_required
def api_digest():
    """오늘 / 이번주 — 로그인 직후 보여주는 자동 다이제스트.

    카톡에서 묻혀서 못 보고 지나가는 일을 막기 위한 핵심 기능.
    """
    me = current_user()
    db = get_db()
    today_iso = datetime.now(timezone.utc).date().isoformat()

    overdue = db.execute("""
        SELECT q.id, q.title, q.due_date, r.name AS room_name, r.id AS room_id,
               it.customer, it.code
          FROM requests q
          JOIN rooms r ON r.id = q.room_id
          LEFT JOIN items it ON it.room_id = q.room_id
         WHERE q.assigned_to = ? AND q.status IN ('open','in_progress')
           AND q.due_date IS NOT NULL AND q.due_date < ?
         ORDER BY q.due_date ASC
    """, (me["id"], today_iso)).fetchall()

    today_due = db.execute("""
        SELECT q.id, q.title, q.due_date, r.name AS room_name, r.id AS room_id,
               it.customer, it.code
          FROM requests q
          JOIN rooms r ON r.id = q.room_id
          LEFT JOIN items it ON it.room_id = q.room_id
         WHERE q.assigned_to = ? AND q.status IN ('open','in_progress')
           AND q.due_date = ?
    """, (me["id"], today_iso)).fetchall()

    upcoming = db.execute("""
        SELECT q.id, q.title, q.due_date, r.name AS room_name, r.id AS room_id,
               it.customer, it.code
          FROM requests q
          JOIN rooms r ON r.id = q.room_id
          LEFT JOIN items it ON it.room_id = q.room_id
         WHERE q.assigned_to = ? AND q.status IN ('open','in_progress')
           AND q.due_date IS NOT NULL AND q.due_date > ?
           AND date(q.due_date) <= date(?, '+7 days')
         ORDER BY q.due_date ASC
    """, (me["id"], today_iso, today_iso)).fetchall()

    no_due = db.execute("""
        SELECT COUNT(*) AS n FROM requests
         WHERE assigned_to = ? AND status IN ('open','in_progress') AND due_date IS NULL
    """, (me["id"],)).fetchone()["n"]

    requested_open = db.execute("""
        SELECT q.id, q.title, q.due_date, q.status,
               r.name AS room_name, r.id AS room_id,
               ua.display_name AS assigned_to_name,
               it.customer, it.code
          FROM requests q
          JOIN rooms r ON r.id = q.room_id
          LEFT JOIN items it ON it.room_id = q.room_id
          LEFT JOIN users ua ON ua.id = q.assigned_to
         WHERE q.requested_by = ? AND q.status IN ('open','in_progress')
         ORDER BY (q.due_date IS NULL), q.due_date ASC
    """, (me["id"],)).fetchall()

    stale_items = db.execute("""
        SELECT r.id AS room_id, r.name, it.customer, it.code, it.status,
               (SELECT MAX(created_at) FROM messages WHERE room_id=r.id) AS last_activity
          FROM rooms r
          JOIN items it ON it.room_id = r.id
          JOIN room_members rm ON rm.room_id = r.id AND rm.user_id = ?
         WHERE it.status = 'active'
           AND (SELECT MAX(created_at) FROM messages WHERE room_id=r.id) IS NOT NULL
           AND date((SELECT MAX(created_at) FROM messages WHERE room_id=r.id)) < date(?, '-7 days')
         ORDER BY last_activity ASC
         LIMIT 10
    """, (me["id"], today_iso)).fetchall()

    return jsonify({
        "overdue": [dict(r) for r in overdue],
        "today_due": [dict(r) for r in today_due],
        "upcoming": [dict(r) for r in upcoming],
        "no_due_count": no_due,
        "requested_open": [dict(r) for r in requested_open],
        "stale_items": [dict(r) for r in stale_items],
    })


@app.route("/api/rooms/<int:room_id>/export.xlsx")
@login_required
def api_room_export_xlsx(room_id):
    """아이템 이력 Excel 내보내기 — 4시트(개요/메시지/요청/첨부).

    카톡으로 절대 못 했던 기능: 아이템 단위로 모든 이력을 한 파일로.
    감사·법무 보고·인수인계용.
    """
    me = current_user()
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?", (room_id, me["id"])
    ).fetchone():
        abort(403)

    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from io import BytesIO
    from flask import send_file

    room = db.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
    item = db.execute("SELECT * FROM items WHERE room_id=?", (room_id,)).fetchone()
    msgs = db.execute("""
        SELECT m.*, u.display_name FROM messages m JOIN users u ON u.id=m.user_id
         WHERE m.room_id=? ORDER BY m.id ASC
    """, (room_id,)).fetchall()
    reqs = db.execute("""
        SELECT q.*, ub.display_name AS requested_by_name, ua.display_name AS assigned_to_name
          FROM requests q
          JOIN users ub ON ub.id=q.requested_by
          LEFT JOIN users ua ON ua.id=q.assigned_to
         WHERE q.room_id=? ORDER BY q.id ASC
    """, (room_id,)).fetchall()
    attachments = db.execute("""
        SELECT m.id, m.kind, m.file_name, m.file_size, m.created_at, u.display_name
          FROM messages m JOIN users u ON u.id=m.user_id
         WHERE m.room_id=? AND m.file_path IS NOT NULL
         ORDER BY m.id ASC
    """, (room_id,)).fetchall()
    members = db.execute("""
        SELECT u.username, u.display_name, u.role, rm.joined_at
          FROM room_members rm JOIN users u ON u.id=rm.user_id
         WHERE rm.room_id=? ORDER BY rm.joined_at ASC
    """, (room_id,)).fetchall()

    wb = Workbook()
    KIND_LABEL = {"text": "메시지", "image": "사진", "file": "파일", "system": "시스템"}
    REQ_STATUS = {"open": "열림", "in_progress": "진행중", "done": "완료", "cancelled": "취소"}
    ITEM_STATUS = {"active": "진행중", "hold": "보류", "done": "완료", "cancelled": "취소"}

    bold = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="2563EB")
    border = Border(*[Side(style='thin', color='E5E7EB')] * 4)
    wrap = Alignment(wrap_text=True, vertical="top")

    def setup_header(ws, headers, widths=None):
        for i, h in enumerate(headers, 1):
            c = ws.cell(row=1, column=i, value=h)
            c.font = bold; c.fill = header_fill; c.alignment = Alignment(horizontal="center")
        if widths:
            for i, w in enumerate(widths, 1):
                ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "A2"

    # Sheet 1: 개요
    ws1 = wb.active
    ws1.title = "개요"
    ws1["A1"] = "KNK 메신저 — 아이템 이력 보고서"
    ws1["A1"].font = Font(bold=True, size=14)
    ws1.merge_cells("A1:B1")
    rows1 = [
        ["내보내기 일시", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M (UTC)")],
        ["내보낸 사람", me["display_name"]],
        ["", ""],
        ["방 이름", room["name"] if room else ""],
        ["타입", {"item": "아이템", "channel": "채널", "group": "그룹채팅", "direct": "1:1"}.get(room["type"] if room else "", "")],
    ]
    if item:
        rows1.extend([
            ["고객사", item["customer"] or ""],
            ["모델/품번", item["code"] or ""],
            ["상태", ITEM_STATUS.get(item["status"], item["status"] or "")],
            ["납기", item["due_date"] or ""],
            ["영구보존", "예" if item["keep_forever"] else "아니오"],
            ["설명", item["description"] or ""],
        ])
    rows1.extend([
        ["", ""],
        ["통계", ""],
        ["  · 메시지 수", sum(1 for m in msgs if m["kind"] == "text")],
        ["  · 사진", sum(1 for m in msgs if m["kind"] == "image")],
        ["  · 파일", sum(1 for m in msgs if m["kind"] == "file")],
        ["  · 시스템 메시지", sum(1 for m in msgs if m["kind"] == "system")],
        ["  · 요청 (전체)", len(reqs)],
        ["  · 요청 (열림+진행중)", sum(1 for r in reqs if r["status"] in ("open", "in_progress"))],
        ["  · 멤버 수", len(members)],
    ])
    for i, (k, v) in enumerate(rows1, 3):
        ws1.cell(row=i, column=1, value=k).font = Font(bold=True)
        ws1.cell(row=i, column=2, value=v)
    ws1.column_dimensions["A"].width = 18
    ws1.column_dimensions["B"].width = 60

    # Sheet 2: 메시지 타임라인
    ws2 = wb.create_sheet("메시지")
    setup_header(ws2, ["#", "일시", "보낸이", "구분", "내용", "파일명", "크기(B)"], [6, 20, 15, 8, 70, 30, 12])
    for i, m in enumerate(msgs, 2):
        ws2.cell(row=i, column=1, value=m["id"])
        ws2.cell(row=i, column=2, value=m["created_at"])
        ws2.cell(row=i, column=3, value=m["display_name"])
        ws2.cell(row=i, column=4, value=KIND_LABEL.get(m["kind"], m["kind"]))
        cell = ws2.cell(row=i, column=5, value=m["content"])
        cell.alignment = wrap
        ws2.cell(row=i, column=6, value=m["file_name"] or "")
        ws2.cell(row=i, column=7, value=m["file_size"] or "")
    ws2.auto_filter.ref = ws2.dimensions

    # Sheet 3: 요청
    ws3 = wb.create_sheet("요청")
    setup_header(ws3, ["#", "상태", "우선순위", "제목", "상세", "요청자", "담당자", "납기", "등록일", "마감일"], [6, 10, 10, 35, 50, 12, 12, 12, 18, 18])
    for i, r in enumerate(reqs, 2):
        ws3.cell(row=i, column=1, value=r["id"])
        ws3.cell(row=i, column=2, value=REQ_STATUS.get(r["status"], r["status"]))
        ws3.cell(row=i, column=3, value=r["priority"])
        ws3.cell(row=i, column=4, value=r["title"]).alignment = wrap
        ws3.cell(row=i, column=5, value=r["description"] or "").alignment = wrap
        ws3.cell(row=i, column=6, value=r["requested_by_name"])
        ws3.cell(row=i, column=7, value=r["assigned_to_name"] or "")
        ws3.cell(row=i, column=8, value=r["due_date"] or "")
        ws3.cell(row=i, column=9, value=r["created_at"])
        ws3.cell(row=i, column=10, value=r["closed_at"] or "")
    if reqs:
        ws3.auto_filter.ref = ws3.dimensions

    # Sheet 4: 첨부
    ws4 = wb.create_sheet("첨부")
    setup_header(ws4, ["#", "구분", "파일명", "크기(B)", "올린이", "일시"], [6, 8, 50, 12, 15, 20])
    for i, a in enumerate(attachments, 2):
        ws4.cell(row=i, column=1, value=a["id"])
        ws4.cell(row=i, column=2, value=KIND_LABEL.get(a["kind"], a["kind"]))
        ws4.cell(row=i, column=3, value=a["file_name"] or "")
        ws4.cell(row=i, column=4, value=a["file_size"] or "")
        ws4.cell(row=i, column=5, value=a["display_name"])
        ws4.cell(row=i, column=6, value=a["created_at"])
    if attachments:
        ws4.auto_filter.ref = ws4.dimensions

    # Sheet 5: 멤버
    ws5 = wb.create_sheet("멤버")
    setup_header(ws5, ["아이디", "이름", "역할", "참여일"], [12, 18, 10, 20])
    for i, m in enumerate(members, 2):
        ws5.cell(row=i, column=1, value=m["username"])
        ws5.cell(row=i, column=2, value=m["display_name"])
        ws5.cell(row=i, column=3, value=m["role"])
        ws5.cell(row=i, column=4, value=m["joined_at"])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    safe_name = re.sub(r'[\\/:"*?<>|]+', "_", room["name"] or f"room{room_id}")
    fname = f"KNK메신저_{safe_name}_{today}.xlsx"
    return send_file(
        buf,
        as_attachment=True,
        download_name=fname,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/api/rooms/<int:room_id>/timeline")
@login_required
def api_room_timeline(room_id):
    """아이템 타임라인 — 날짜별로 사진·파일·요청·결정 그룹.

    신규 담당자가 인수받을 때 처음부터 끝까지 한 페이지로 보기 위한 용도.
    """
    me = current_user()
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?", (room_id, me["id"])
    ).fetchone():
        abort(403)
    msgs = db.execute("""
        SELECT m.id, m.kind, m.content, m.file_path, m.file_name, m.file_size, m.created_at,
               u.display_name, u.avatar_color
          FROM messages m JOIN users u ON u.id = m.user_id
         WHERE m.room_id = ?
         ORDER BY m.id ASC
    """, (room_id,)).fetchall()
    reqs = db.execute("""
        SELECT q.*, ub.display_name AS requested_by_name, ua.display_name AS assigned_to_name
          FROM requests q
          JOIN users ub ON ub.id = q.requested_by
          LEFT JOIN users ua ON ua.id = q.assigned_to
         WHERE q.room_id = ?
         ORDER BY q.id ASC
    """, (room_id,)).fetchall()
    return jsonify({
        "messages": [dict(r) for r in msgs],
        "requests": [dict(r) for r in reqs],
    })


@app.route("/api/push/vapid_public")
@login_required
def api_push_vapid_public():
    pk = vapid_public_key_b64u()
    if not pk:
        return jsonify({"error": "VAPID 키 없음 — generate_vapid.py 실행 필요"}), 503
    return jsonify({"public_key": pk, "enabled": PYWEBPUSH_OK})


@app.route("/api/push/subscribe", methods=["POST"])
@login_required
def api_push_subscribe():
    me = current_user()
    data = request.get_json(silent=True) or {}
    sub = data.get("subscription") or {}
    endpoint = sub.get("endpoint")
    keys = sub.get("keys") or {}
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")
    if not (endpoint and p256dh and auth):
        return jsonify({"error": "subscription 형식 오류",
                        "got": {"endpoint": bool(endpoint), "p256dh": bool(p256dh), "auth": bool(auth)}}), 400
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    try:
        db.execute("""
            INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth, user_agent, created_at, last_used)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(endpoint) DO UPDATE SET
                user_id = excluded.user_id,
                p256dh = excluded.p256dh,
                auth = excluded.auth,
                last_used = excluded.last_used
        """, (me["id"], endpoint, p256dh, auth, request.headers.get("User-Agent", "")[:200], now, now))
        db.commit()
    except Exception as e:
        print(f"[push/subscribe] INSERT 실패 user={me['id']}: {e}")
        return jsonify({"error": f"DB INSERT 실패: {e}"}), 500
    # 저장 확인 — INSERT 직후 다시 조회해서 row 수 반환
    count = db.execute(
        "SELECT COUNT(*) FROM push_subscriptions WHERE user_id=?", (me["id"],)
    ).fetchone()[0]
    print(f"[push/subscribe] OK user={me['id']} count={count} ua={request.headers.get('User-Agent','')[:80]}")
    return jsonify({"ok": True, "subscription_count": count})


@app.route("/api/push/diag")
@login_required
def api_push_diag():
    """현재 사용자의 push 구독 상태 진단 — 다이얼로그에 표시."""
    me = current_user()
    db = get_db()
    rows = db.execute(
        """SELECT id, substr(endpoint, 1, 60) AS ep_prefix, user_agent,
                  datetime(created_at) AS created, datetime(last_used) AS last_used
             FROM push_subscriptions WHERE user_id=? ORDER BY id""",
        (me["id"],),
    ).fetchall()
    return jsonify({
        "user_id": me["id"],
        "display_name": me["display_name"],
        "pywebpush_ok": PYWEBPUSH_OK,
        "vapid_key_present": bool(vapid_public_key_b64u()),
        "subscription_count": len(rows),
        "subscriptions": [{
            "id": r["id"],
            "endpoint": r["ep_prefix"] + "...",
            "user_agent": (r["user_agent"] or "")[:80],
            "created": r["created"],
            "last_used": r["last_used"],
        } for r in rows],
    })


@app.route("/api/push/unsubscribe", methods=["POST"])
@login_required
def api_push_unsubscribe():
    me = current_user()
    data = request.get_json(silent=True) or {}
    endpoint = data.get("endpoint")
    if not endpoint:
        return jsonify({"error": "endpoint 필요"}), 400
    db = get_db()
    db.execute("DELETE FROM push_subscriptions WHERE user_id=? AND endpoint=?", (me["id"], endpoint))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/push/test", methods=["POST"])
@login_required
def api_push_test():
    """테스트 푸시 발송 + 실패 시 상세 에러 반환 (진단용)."""
    me = current_user()
    sent, errors, total = send_push_to_user(
        me["id"],
        "🔔 KNK 메신저 테스트",
        "푸시 알림이 정상 작동합니다.",
        url="/chat", tag="test",
        collect_errors=True,
    )
    return jsonify({"sent": sent, "total_subscriptions": total, "errors": errors})


@app.route("/api/admin/cleanup", methods=["POST"])
@login_required
def api_admin_cleanup():
    """메시지 자동삭제 — N개월 이전 메시지(첨부 포함) 제거. 단 keep_forever=1 아이템·system 메시지 보존.

    수동 실행 또는 외부 스케줄러(Windows 작업스케줄러·cron)에서 호출.
    """
    me = current_user()
    if me["role"] != "ceo":
        abort(403)
    db = get_db()
    cutoff = (datetime.now(timezone.utc).date().replace(day=1)).isoformat()
    # cutoff = "오늘 - N개월" 의 첫날
    months = MESSAGE_RETENTION_MONTHS
    # 1단계: 전역 보존 정책 (N개월). keep_forever=1 아이템은 제외.
    # SQLite date() 산술
    rows = db.execute("""
        SELECT m.id, m.file_path
          FROM messages m
          JOIN rooms r ON r.id = m.room_id
          LEFT JOIN items it ON it.room_id = m.room_id
         WHERE m.kind != 'system'
           AND date(m.created_at) < date('now', ?)
           AND COALESCE(it.keep_forever, 0) = 0
    """, (f"-{months} months",)).fetchall()
    # 2단계: 방별 retention_days 가 설정되면 그 일수 이전 메시지도 추가 삭제.
    # WhatsApp 식 자동 삭제 — 방장이 보안·정리 목적으로 설정.
    per_room_rows = db.execute("""
        SELECT m.id, m.file_path
          FROM messages m
          JOIN rooms r ON r.id = m.room_id
         WHERE r.retention_days IS NOT NULL
           AND r.retention_days > 0
           AND m.kind != 'system'
           AND julianday('now') - julianday(m.created_at) > r.retention_days
    """).fetchall()
    # 중복 제거 (전역에서 이미 삭제될 ID 는 2단계에서 빼기)
    seen_ids = {r["id"] for r in rows}
    for pr in per_room_rows:
        if pr["id"] not in seen_ids:
            rows.append(pr)
            seen_ids.add(pr["id"])
    deleted = 0
    deleted_files = 0
    for r in rows:
        if r["file_path"]:
            try:
                fp = os.path.join(UPLOAD_DIR, r["file_path"])
                if os.path.exists(fp):
                    os.remove(fp)
                    deleted_files += 1
            except OSError:
                pass
        db.execute("DELETE FROM messages WHERE id = ?", (r["id"],))
        deleted += 1
    db.commit()
    return jsonify({"deleted_messages": deleted, "deleted_files": deleted_files, "retention_months": months})


@app.route("/api/admin/cleanup/preview")
@login_required
def api_admin_cleanup_preview():
    """삭제 미리보기 — 실제 삭제는 안 하고 카운트만 반환."""
    me = current_user()
    if me["role"] != "ceo":
        abort(403)
    db = get_db()
    months = MESSAGE_RETENTION_MONTHS
    row = db.execute("""
        SELECT COUNT(*) AS n,
               SUM(CASE WHEN m.file_path IS NOT NULL THEN 1 ELSE 0 END) AS files
          FROM messages m
          JOIN rooms r ON r.id = m.room_id
          LEFT JOIN items it ON it.room_id = m.room_id
         WHERE m.kind != 'system'
           AND date(m.created_at) < date('now', ?)
           AND COALESCE(it.keep_forever, 0) = 0
    """, (f"-{months} months",)).fetchone()
    return jsonify({
        "would_delete_messages": row["n"] or 0,
        "would_delete_files": row["files"] or 0,
        "retention_months": months,
        "ceo_only": True,
    })


@app.route("/api/users", methods=["POST"])
@login_required
def api_users_create():
    """대표만 — 사용자 추가. 기술영업팀 베타 멤버 등록용."""
    me = current_user()
    if me["role"] != "ceo":
        abort(403)
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or "knk1234"
    display_name = (data.get("display_name") or "").strip()
    role = data.get("role") or "staff"
    avatar_color = data.get("avatar_color") or "#3b82f6"
    if not username or not display_name:
        return jsonify({"error": "username과 display_name 필수"}), 400
    db = get_db()
    if db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
        return jsonify({"error": "이미 존재하는 username"}), 400
    now = datetime.now(timezone.utc).isoformat()
    cur = db.execute(
        "INSERT INTO users (username, password_hash, display_name, role, avatar_color, created_at) VALUES (?,?,?,?,?,?)",
        (username, generate_password_hash(password), display_name, role, avatar_color, now),
    )
    db.commit()
    return jsonify({"id": cur.lastrowid, "username": username, "display_name": display_name})


def _parse_search_filters(q):
    """Slack/Discord 식 검색 필터 파싱.
       지원 키: from:이름, in:방이름, has:file|image|link, before:YYYY-MM-DD, after:YYYY-MM-DD
       이름·방에는 # 또는 @ 접두 가능 (예: in:#영업, from:@김정락).
       반환: (plain_text, filters)"""
    filters = {
        'from':  [],    # 발신자 이름·아이디 (OR)
        'in':    [],    # 방 이름 (OR)
        'has':   [],    # file, image, link 중 (AND)
        'before': None, # YYYY-MM-DD
        'after':  None, # YYYY-MM-DD
    }
    parts = []
    # 인용("") 안의 다중 토큰도 한 단어로 묶음 → 일단 단순 split.
    for tok in (q or "").split():
        m = re.match(r'^(from|in|has|before|after):(.+)$', tok, re.IGNORECASE)
        if not m:
            parts.append(tok)
            continue
        key = m.group(1).lower()
        val = m.group(2).strip().lstrip('#@').strip()
        if not val:
            continue
        if key in ('from', 'in'):
            filters[key].append(val)
        elif key == 'has':
            v = val.lower()
            if v in ('file', 'image', 'link', 'photo', 'pic'):
                # photo/pic 도 image 동의어
                if v in ('photo', 'pic'):
                    v = 'image'
                if v not in filters['has']:
                    filters['has'].append(v)
        elif key in ('before', 'after'):
            # YYYY-MM-DD 형식 검증
            if re.match(r'^\d{4}-\d{2}-\d{2}$', val):
                filters[key] = val
    return ' '.join(parts).strip(), filters


@app.route("/api/search")
@login_required
def api_search():
    """전문 검색 + Slack/Discord 식 고급 필터.
       사용 예: "발주 from:김정락 has:file before:2026-05-01 in:#영업\""""
    me = current_user()
    raw_q = (request.args.get("q") or "").strip()
    if not raw_q:
        return jsonify([])
    plain_q, filters = _parse_search_filters(raw_q)
    db = get_db()

    # ----- 동적 WHERE 구성 -----
    where_clauses = []
    args = [me["id"]]   # 첫 인자는 room_members.user_id (방 멤버 권한)

    # from: — 발신자 (display_name 또는 username LIKE) — OR
    if filters['from']:
        sub_or = []
        for name in filters['from']:
            sub_or.append("(u.display_name LIKE ? OR u.username LIKE ?)")
            args.extend([f"%{name}%", f"%{name}%"])
        where_clauses.append("(" + " OR ".join(sub_or) + ")")

    # in: — 방 이름 OR (별명·실제 이름 둘 다 매칭)
    if filters['in']:
        sub_or = []
        for rn in filters['in']:
            sub_or.append("r.name LIKE ?")
            args.append(f"%{rn}%")
        where_clauses.append("(" + " OR ".join(sub_or) + ")")

    # has: — file/image/link AND (다중이면 모두 충족)
    for h in filters['has']:
        if h == 'file':
            where_clauses.append("m.file_path IS NOT NULL")
        elif h == 'image':
            where_clauses.append("(m.kind='image' OR (m.file_mime IS NOT NULL AND m.file_mime LIKE 'image/%'))")
        elif h == 'link':
            where_clauses.append("(m.content LIKE '%http://%' OR m.content LIKE '%https://%')")

    # before/after: — date 비교
    if filters['before']:
        where_clauses.append("date(m.created_at) < date(?)")
        args.append(filters['before'])
    if filters['after']:
        where_clauses.append("date(m.created_at) > date(?)")
        args.append(filters['after'])

    # FTS 또는 LIKE 본문 검색 (plain_q 가 있을 때만)
    use_fts = False
    fts_q = None
    if plain_q:
        fts_q = fts_query_safe(plain_q)
        if fts_q:
            use_fts = True

    if use_fts:
        # FTS MATCH 경로 — content 검색
        sql = f"""
            SELECT m.id, m.content, m.kind, m.created_at, m.room_id, m.file_path, m.file_name, m.file_mime,
                   u.display_name, u.avatar_color, u.username,
                   r.name AS room_name, r.type AS room_type,
                   it.customer AS item_customer, it.code AS item_code,
                   'message' AS result_type
              FROM messages_fts fts
              JOIN messages m ON m.id = fts.rowid
              JOIN users u ON u.id = m.user_id
              JOIN rooms r ON r.id = m.room_id
              JOIN room_members rm ON rm.room_id = r.id AND rm.user_id = ?
              LEFT JOIN items it ON it.room_id = r.id
             WHERE messages_fts MATCH ?
               {('AND ' + ' AND '.join(where_clauses)) if where_clauses else ''}
             ORDER BY m.id DESC
             LIMIT 50
        """
        # args 순서: me["id"], fts_q, [filter args ...]
        full_args = [me["id"], fts_q] + args[1:]
        msg_rows = db.execute(sql, full_args).fetchall()
    elif where_clauses:
        # 필터만 있고 본문 검색 없음 — 직접 messages 스캔 (FTS 없이)
        sql = f"""
            SELECT m.id, m.content, m.kind, m.created_at, m.room_id, m.file_path, m.file_name, m.file_mime,
                   u.display_name, u.avatar_color, u.username,
                   r.name AS room_name, r.type AS room_type,
                   it.customer AS item_customer, it.code AS item_code,
                   'message' AS result_type
              FROM messages m
              JOIN users u ON u.id = m.user_id
              JOIN rooms r ON r.id = m.room_id
              JOIN room_members rm ON rm.room_id = r.id AND rm.user_id = ?
              LEFT JOIN items it ON it.room_id = r.id
             WHERE {' AND '.join(where_clauses)}
             ORDER BY m.id DESC
             LIMIT 50
        """
        msg_rows = db.execute(sql, args).fetchall()
    else:
        # 검색어가 전부 stop-word 등으로 fts_query_safe 가 비어졌고 필터도 없음 → 빈 결과
        msg_rows = []

    # 아이템 메타 검색 (LIKE) — plain_q 기준. 필터링 모드(예: from:만)면 스킵.
    item_results = []
    if plain_q:
        tokens = re.findall(r"[\w가-힣]+", plain_q)
        if tokens:
            like_clauses = []
            like_args = [me["id"]]
            for t in tokens:
                like_clauses.append("(it.name LIKE ? OR it.customer LIKE ? OR it.code LIKE ? OR it.description LIKE ?)")
                for _ in range(4):
                    like_args.append(f"%{t}%")
            item_rows = db.execute(f"""
                SELECT r.id AS room_id, r.name AS room_name, r.type AS room_type,
                       it.customer AS item_customer, it.code AS item_code,
                       it.status AS item_status, it.description AS item_desc,
                       'item' AS result_type
                  FROM items it
                  JOIN rooms r ON r.id = it.room_id
                  JOIN room_members rm ON rm.room_id = r.id AND rm.user_id = ?
                 WHERE {' AND '.join(like_clauses)}
                 ORDER BY r.id DESC
                 LIMIT 20
            """, like_args).fetchall()
            item_results = [dict(r) for r in item_rows]

    # 아이템 결과 먼저, 그 다음 메시지 결과
    return jsonify(item_results + [dict(r) for r in msg_rows])


@app.route("/api/rooms", methods=["POST"])
@login_required
def api_rooms_create():
    me = current_user()
    data = request.get_json(silent=True) or {}
    user_ids = list({int(x) for x in (data.get("user_ids") or [])})
    if me["id"] not in user_ids:
        user_ids.append(me["id"])
    if len(user_ids) < 2:
        return jsonify({"error": "최소 2명 이상이어야 합니다."}), 400
    type_ = data.get("type") or ("direct" if len(user_ids) == 2 else "group")
    name = (data.get("name") or "").strip() or None
    # 이름 고정 — 방장이 지정한 이름을 다른 멤버가 변경/별명 불가
    name_locked = 1 if data.get("name_locked") else 0
    # direct 방은 항상 name_locked=0 (이름 없음, 각자 상대방 이름으로 표시)
    if type_ == "direct":
        name_locked = 0
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    if type_ == "direct" and len(user_ids) == 2:
        other = [u for u in user_ids if u != me["id"]][0]
        existing = db.execute("""
            SELECT r.id FROM rooms r
              JOIN room_members rm1 ON rm1.room_id=r.id AND rm1.user_id=?
              JOIN room_members rm2 ON rm2.room_id=r.id AND rm2.user_id=?
             WHERE r.type='direct'
             LIMIT 1
        """, (me["id"], other)).fetchone()
        if existing:
            return jsonify({"id": existing["id"], "existing": True})

    cur = db.execute(
        "INSERT INTO rooms (name, type, created_by, created_at, name_locked) VALUES (?,?,?,?,?)",
        (name, type_, me["id"], now, name_locked),
    )
    rid = cur.lastrowid
    # 생성자는 host, 나머지는 member
    for uid in user_ids:
        role = 'host' if uid == me["id"] else 'member'
        db.execute(
            "INSERT INTO room_members (room_id, user_id, joined_at, role) VALUES (?,?,?,?)",
            (rid, uid, now, role),
        )
    db.commit()
    return jsonify({"id": rid, "existing": False, "name_locked": name_locked})


@app.route("/api/rooms/<int:room_id>/membership", methods=["DELETE"])
@login_required
def api_leave_room(room_id):
    """방 나가기 — 본인을 room_members에서 제거 + 시스템 메시지로 다른 멤버에 알림."""
    me = current_user()
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?", (room_id, me["id"])
    ).fetchone():
        return jsonify({"error": "이 방의 멤버가 아닙니다."}), 404

    room = db.execute("SELECT type, name FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not room:
        return jsonify({"error": "방이 없습니다."}), 404

    now = datetime.now(timezone.utc).isoformat()
    sys_text = f"[{me['display_name']}] 님이 나갔습니다."
    cur = db.execute(
        "INSERT INTO messages (room_id, user_id, content, kind, created_at) VALUES (?,?,?,?,?)",
        (room_id, me["id"], sys_text, "system", now),
    )
    sys_mid = cur.lastrowid
    db.execute(
        "DELETE FROM room_members WHERE room_id=? AND user_id=?", (room_id, me["id"])
    )
    db.commit()

    # 남은 멤버에게 시스템 메시지 emit
    socketio.emit("new_message", {
        "id": sys_mid, "room_id": room_id, "user_id": me["id"],
        "display_name": me["display_name"], "avatar_color": me["avatar_color"],
        "content": sys_text, "kind": "system", "created_at": now,
    }, to=f"room_{room_id}")

    return jsonify({"ok": True, "room_type": room["type"], "room_name": room["name"]})


# ============================================================
# 방 권한 관리: host(방장)·sub_host(부방장)·member(일반)
# ============================================================
def _my_room_role(db, room_id, user_id):
    r = db.execute("SELECT role FROM room_members WHERE room_id=? AND user_id=?",
                   (room_id, user_id)).fetchone()
    return r["role"] if r else None


def _room_members_full(db, room_id):
    """방 멤버 + 역할 + 표시정보 일괄. UI 멤버 패널용."""
    return [dict(r) for r in db.execute("""
        SELECT u.id, u.username, u.display_name, u.avatar_color,
               rm.role, rm.joined_at
          FROM room_members rm JOIN users u ON u.id = rm.user_id
         WHERE rm.room_id = ?
         ORDER BY CASE rm.role WHEN 'host' THEN 0 WHEN 'sub_host' THEN 1 ELSE 2 END, u.display_name
    """, (room_id,)).fetchall()]


def _emit_room_event(room_id, event, payload):
    """방 멤버 전체에 이벤트 브로드캐스트."""
    socketio.emit(event, payload, to=f"room_{room_id}")


@app.route("/api/rooms/<int:room_id>/members", methods=["GET"])
@login_required
def api_room_members(room_id):
    """방 멤버 목록 + 각 역할 + 내 별명 + name_locked."""
    me = current_user()
    db = get_db()
    if not _my_room_role(db, room_id, me["id"]):
        abort(403)
    room = db.execute("SELECT id, name, type, created_by, name_locked FROM rooms WHERE id=?",
                      (room_id,)).fetchone()
    if not room:
        abort(404)
    alias = db.execute("SELECT alias FROM room_aliases WHERE room_id=? AND user_id=?",
                       (room_id, me["id"])).fetchone()
    return jsonify({
        "room": {"id": room["id"], "name": room["name"], "type": room["type"],
                 "created_by": room["created_by"], "name_locked": bool(room["name_locked"])},
        "members": _room_members_full(db, room_id),
        "my_alias": alias["alias"] if alias else None,
        "my_role": _my_room_role(db, room_id, me["id"]),
    })


@app.route("/api/rooms/<int:room_id>/alias", methods=["POST", "DELETE"])
@login_required
def api_room_alias(room_id):
    """내 화면에서만 보이는 방 별명. name_locked=1 이면 거부."""
    me = current_user()
    db = get_db()
    room = db.execute("SELECT name_locked, type FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not room:
        abort(404)
    if not _my_room_role(db, room_id, me["id"]):
        abort(403)
    if room["type"] == "direct":
        return jsonify({"error": "1:1 방은 별명 설정 불가"}), 400
    if room["name_locked"]:
        return jsonify({"error": "이 방은 이름 고정. 방장만 변경 가능"}), 400
    now = datetime.now(timezone.utc).isoformat()
    if request.method == "DELETE":
        db.execute("DELETE FROM room_aliases WHERE room_id=? AND user_id=?", (room_id, me["id"]))
        db.commit()
        return jsonify({"ok": True, "alias": None})
    data = request.get_json(silent=True) or {}
    alias = (data.get("alias") or "").strip()
    if not alias:
        db.execute("DELETE FROM room_aliases WHERE room_id=? AND user_id=?", (room_id, me["id"]))
        db.commit()
        return jsonify({"ok": True, "alias": None})
    if len(alias) > 50:
        return jsonify({"error": "별명은 50자 이내"}), 400
    db.execute("""
        INSERT INTO room_aliases (user_id, room_id, alias, updated_at) VALUES (?,?,?,?)
        ON CONFLICT(user_id, room_id) DO UPDATE SET alias=excluded.alias, updated_at=excluded.updated_at
    """, (me["id"], room_id, alias, now))
    db.commit()
    return jsonify({"ok": True, "alias": alias})


@app.route("/api/rooms/<int:room_id>/name", methods=["PATCH"])
@login_required
def api_room_rename(room_id):
    """방 이름 변경 — 방장만. body: {name, name_locked?}"""
    me = current_user()
    db = get_db()
    role = _my_room_role(db, room_id, me["id"])
    if role != 'host':
        return jsonify({"error": "방장만 가능"}), 403
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "이름은 비어있을 수 없음"}), 400
    if len(name) > 100:
        return jsonify({"error": "이름은 100자 이내"}), 400
    name_locked = 1 if data.get("name_locked") else 0
    db.execute("UPDATE rooms SET name=?, name_locked=? WHERE id=?", (name, name_locked, room_id))
    # name_locked=1 이면 기존 alias 모두 삭제 (방장이 강제)
    if name_locked:
        db.execute("DELETE FROM room_aliases WHERE room_id=?", (room_id,))
    db.commit()
    now = datetime.now(timezone.utc).isoformat()
    sys_text = f"방 이름이 [{name}] 으로 변경됨"
    cur = db.execute(
        "INSERT INTO messages (room_id, user_id, content, kind, created_at) VALUES (?,?,?,?,?)",
        (room_id, me["id"], sys_text, "system", now),
    )
    db.commit()
    _emit_room_event(room_id, "room_renamed", {
        "room_id": room_id, "name": name, "name_locked": bool(name_locked),
        "by": me["display_name"],
    })
    _emit_room_event(room_id, "new_message", {
        "id": cur.lastrowid, "room_id": room_id, "user_id": me["id"],
        "display_name": me["display_name"], "avatar_color": me["avatar_color"],
        "content": sys_text, "kind": "system", "created_at": now,
    })
    return jsonify({"ok": True, "name": name, "name_locked": bool(name_locked)})


@app.route("/api/rooms/<int:room_id>/retention", methods=["GET", "PUT"])
@login_required
def api_room_retention(room_id):
    """방별 메시지 자동 삭제 일수 설정 (WhatsApp 식).
    GET: 현재 설정 반환. PUT: body {retention_days: int|null}.
    null=영구 보존(글로벌 정책만 적용), 1=24시간, 7=1주, 30=30일, 90=90일.
    방장만 변경 가능 — 멤버는 GET 만."""
    me = current_user()
    db = get_db()
    # 멤버 확인
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
        (room_id, me["id"]),
    ).fetchone():
        return jsonify({"error": "방 멤버 아님"}), 403
    if request.method == "GET":
        row = db.execute("SELECT retention_days FROM rooms WHERE id=?", (room_id,)).fetchone()
        return jsonify({"retention_days": row["retention_days"] if row else None})
    # PUT
    if _my_room_role(db, room_id, me["id"]) != 'host':
        return jsonify({"error": "방장만 변경 가능"}), 403
    data = request.get_json(silent=True) or {}
    raw = data.get("retention_days")
    if raw is None:
        rd = None
    else:
        try:
            rd = int(raw)
            if rd not in (1, 7, 30, 90):
                return jsonify({"error": "retention_days 는 1/7/30/90 또는 null"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "retention_days 형식 오류"}), 400
    db.execute("UPDATE rooms SET retention_days=? WHERE id=?", (rd, room_id))
    db.commit()
    # 시스템 메시지로 변경 사실 기록
    now = datetime.now(timezone.utc).isoformat()
    label = "영구 보존" if rd is None else (
        "24시간 후" if rd == 1 else f"{rd}일 후"
    )
    sys_text = f"메시지 자동 삭제 정책: {label}"
    cur = db.execute(
        "INSERT INTO messages (room_id, user_id, content, kind, created_at) VALUES (?,?,?,?,?)",
        (room_id, me["id"], sys_text, "system", now),
    )
    db.commit()
    _emit_room_event(room_id, "new_message", {
        "id": cur.lastrowid, "room_id": room_id, "user_id": me["id"],
        "display_name": me["display_name"], "avatar_color": me["avatar_color"],
        "content": sys_text, "kind": "system", "created_at": now,
    })
    _emit_room_event(room_id, "room_retention_changed", {
        "room_id": room_id, "retention_days": rd,
    })
    return jsonify({"ok": True, "retention_days": rd})


# ---------- 사용자 상태 (Slack/Teams 식) + 캘린더 동기화 ----------
VALID_STATUSES = ("online", "away", "busy", "meeting", "external", "dnd", "offline")
STATUS_LABEL_KO = {
    "online":   "🟢 온라인",
    "away":     "🌙 자리비움",
    "busy":     "🔴 바쁨",
    "meeting":  "🤝 회의 중",
    "external": "🚗 외근",
    "dnd":      "🚫 방해금지",
    "offline":  "⚫ 오프라인",
}


def _get_user_status(uid):
    """사용자의 현재 상태 dict 반환. 없으면 online 디폴트."""
    db = get_db()
    row = db.execute("SELECT * FROM user_statuses WHERE user_id=?", (uid,)).fetchone()
    if not row:
        return {
            "user_id": uid, "status": "online", "custom_text": None,
            "emoji": None, "until_at": None, "auto_set": 0,
            "label": STATUS_LABEL_KO["online"],
        }
    d = dict(row)
    # until_at 지났으면 online 으로 간주 (영구 적용은 별도 cron 에서)
    if d.get("until_at"):
        try:
            from datetime import datetime as _dt
            ua = _dt.fromisoformat(d["until_at"].replace("Z", "+00:00"))
            if ua < datetime.now(timezone.utc):
                d["status"] = "online"
                d["until_at"] = None
        except Exception:
            pass
    d["label"] = STATUS_LABEL_KO.get(d["status"], d["status"])
    return d


@app.route("/api/me/status", methods=["GET", "PUT"])
@login_required
def api_me_status():
    """내 상태 조회 / 변경.
    GET: 현재 상태 + 모든 가능한 상태 enum.
    PUT body: {status, custom_text?, emoji?, until_at?}"""
    me = current_user()
    if request.method == "GET":
        return jsonify({
            "current": _get_user_status(me["id"]),
            "options": [{"value": k, "label": v} for k, v in STATUS_LABEL_KO.items()],
        })
    db = get_db()
    data = request.get_json(silent=True) or {}
    status = data.get("status") or "online"
    if status not in VALID_STATUSES:
        return jsonify({"error": f"status 는 {VALID_STATUSES} 중 하나"}), 400
    custom_text = (data.get("custom_text") or "").strip()[:80] or None
    emoji = (data.get("emoji") or "").strip()[:8] or None
    until_at = data.get("until_at") or None
    now = datetime.now(timezone.utc).isoformat()
    db.execute("""
        INSERT INTO user_statuses (user_id, status, custom_text, emoji, until_at, auto_set, updated_at)
        VALUES (?,?,?,?,?,0,?)
        ON CONFLICT(user_id) DO UPDATE SET
            status=excluded.status, custom_text=excluded.custom_text,
            emoji=excluded.emoji, until_at=excluded.until_at,
            auto_set=0, updated_at=excluded.updated_at
    """, (me["id"], status, custom_text, emoji, until_at, now))
    db.commit()
    cur = _get_user_status(me["id"])
    socketio.emit("user_status_changed", {
        "user_id": me["id"], "status": cur["status"],
        "custom_text": cur.get("custom_text"), "emoji": cur.get("emoji"),
        "label": cur["label"],
    })
    return jsonify({"ok": True, "current": cur})


@app.route("/api/users/statuses", methods=["GET"])
@login_required
def api_users_statuses():
    """전체 사용자 현재 상태 일괄 조회 — 사이드바·메시지 아바타 색점용."""
    db = get_db()
    rows = db.execute("""
        SELECT u.id AS user_id, u.display_name,
               COALESCE(us.status, 'online') AS status,
               us.custom_text, us.emoji, us.until_at
          FROM users u
          LEFT JOIN user_statuses us ON us.user_id = u.id
         WHERE u.active = 1
    """).fetchall()
    out = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for r in rows:
        d = dict(r)
        # 만료된 until_at 은 online 으로 강등 (DB 미반영, 표시상만)
        if d.get("until_at") and d["until_at"] < now_iso:
            d["status"] = "online"
            d["until_at"] = None
        d["label"] = STATUS_LABEL_KO.get(d["status"], d["status"])
        out.append(d)
    return jsonify(out)


@app.route("/api/me/calendar", methods=["GET", "POST"])
@login_required
def api_me_calendar():
    """내 캘린더 일정 — GET: 목록 / POST: 추가.
    POST body: {title, start_at, end_at, kind?}"""
    me = current_user()
    db = get_db()
    if request.method == "GET":
        # 향후 7일치만 (UI 부하 차단)
        rows = db.execute("""
            SELECT id, title, start_at, end_at, kind, applied
              FROM user_calendar_events
             WHERE user_id=? AND date(end_at) >= date('now', '-1 day')
             ORDER BY start_at ASC
             LIMIT 100
        """, (me["id"],)).fetchall()
        return jsonify([dict(r) for r in rows])
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    start_at = (data.get("start_at") or "").strip()
    end_at = (data.get("end_at") or "").strip()
    kind = data.get("kind") or "meeting"
    if kind not in ("meeting", "external", "busy"):
        kind = "meeting"
    if not title or not start_at or not end_at:
        return jsonify({"error": "title/start_at/end_at 필수"}), 400
    now = datetime.now(timezone.utc).isoformat()
    cur = db.execute("""
        INSERT INTO user_calendar_events (user_id, title, start_at, end_at, kind, applied, created_at)
        VALUES (?,?,?,?,?,0,?)
    """, (me["id"], title, start_at, end_at, kind, now))
    db.commit()
    return jsonify({"ok": True, "id": cur.lastrowid})


@app.route("/api/me/calendar/<int:event_id>", methods=["DELETE"])
@login_required
def api_me_calendar_delete(event_id):
    me = current_user()
    db = get_db()
    db.execute("DELETE FROM user_calendar_events WHERE id=? AND user_id=?", (event_id, me["id"]))
    db.commit()
    return jsonify({"ok": True})


def _apply_calendar_status_transitions():
    """캘린더 일정 시작·종료에 따라 사용자 상태 자동 전환.
    /api/me/status PUT 으로 수동 변경되면 auto_set=0 으로 갱신돼 자동전환 차단.
    cron 또는 요청 hook 에서 주기 호출."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        # 시작됐고 아직 적용 안 된 일정 → 회의 중 자동 설정
        starting = db.execute("""
            SELECT id, user_id, title, end_at, kind
              FROM user_calendar_events
             WHERE applied = 0 AND start_at <= ? AND end_at > ?
        """, (now_iso, now_iso)).fetchall()
        for ev in starting:
            # 현재 사용자 상태 — 수동 설정이면 건드리지 않음
            us = db.execute("SELECT status, auto_set FROM user_statuses WHERE user_id=?", (ev["user_id"],)).fetchone()
            if us and us["auto_set"] == 0 and us["status"] in ("dnd", "external"):
                # 수동으로 더 강한 상태 설정돼 있으면 그것을 존중
                pass
            else:
                new_status = "meeting" if ev["kind"] == "meeting" else (
                    "external" if ev["kind"] == "external" else "busy"
                )
                db.execute("""
                    INSERT INTO user_statuses (user_id, status, custom_text, until_at, auto_set, updated_at)
                    VALUES (?,?,?,?,1,?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        status=excluded.status, custom_text=excluded.custom_text,
                        until_at=excluded.until_at, auto_set=1, updated_at=excluded.updated_at
                """, (ev["user_id"], new_status, ev["title"], ev["end_at"], now_iso))
            db.execute("UPDATE user_calendar_events SET applied=1 WHERE id=?", (ev["id"],))
        # 종료된 일정 (applied=1) → online 복귀 (auto_set=1 인 경우만)
        ending = db.execute("""
            SELECT id, user_id FROM user_calendar_events
             WHERE applied = 1 AND end_at <= ?
        """, (now_iso,)).fetchall()
        for ev in ending:
            us = db.execute("SELECT status, auto_set FROM user_statuses WHERE user_id=?", (ev["user_id"],)).fetchone()
            if us and us["auto_set"] == 1:
                db.execute("""
                    UPDATE user_statuses
                       SET status='online', custom_text=NULL, until_at=NULL, auto_set=0, updated_at=?
                     WHERE user_id=?
                """, (now_iso, ev["user_id"]))
            db.execute("UPDATE user_calendar_events SET applied=2 WHERE id=?", (ev["id"],))
        db.commit()
    finally:
        db.close()


# 캘린더 자동 전환을 60초마다 백그라운드에서 실행
_cal_thread_started = False
def _start_calendar_worker():
    global _cal_thread_started
    if _cal_thread_started:
        return
    _cal_thread_started = True
    def _loop():
        import time as _t
        while True:
            try:
                _apply_calendar_status_transitions()
            except Exception as e:
                print(f"[calendar worker] error: {e}")
            _t.sleep(60)
    import threading as _th
    _th.Thread(target=_loop, daemon=True).start()


@app.route("/api/rooms/<int:room_id>/invite_policy", methods=["PUT"])
@login_required
def api_room_invite_policy(room_id):
    """방의 초대 권한 정책 변경 — 방장만.
    body: {invite_policy: 'all' | 'host_only'}
    'all' = 모든 멤버 초대 가능 (기본). 'host_only' = 방장·부방장만 초대 가능."""
    me = current_user()
    db = get_db()
    role = _my_room_role(db, room_id, me["id"])
    if role != 'host':
        return jsonify({"error": "방장만 변경 가능"}), 403
    data = request.get_json(silent=True) or {}
    policy = data.get("invite_policy")
    if policy not in ("all", "host_only"):
        return jsonify({"error": "invite_policy 는 'all' 또는 'host_only'"}), 400
    db.execute("UPDATE rooms SET invite_policy=? WHERE id=?", (policy, room_id))
    db.commit()
    now = datetime.now(timezone.utc).isoformat()
    label = "모든 멤버 가능" if policy == "all" else "방장·부방장만 가능"
    sys_text = f"초대 권한: {label}"
    cur = db.execute(
        "INSERT INTO messages (room_id, user_id, content, kind, created_at) VALUES (?,?,?,?,?)",
        (room_id, me["id"], sys_text, "system", now),
    )
    db.commit()
    _emit_room_event(room_id, "room_invite_policy_changed", {
        "room_id": room_id, "invite_policy": policy,
    })
    _emit_room_event(room_id, "new_message", {
        "id": cur.lastrowid, "room_id": room_id, "user_id": me["id"],
        "display_name": me["display_name"], "avatar_color": me["avatar_color"],
        "content": sys_text, "kind": "system", "created_at": now,
    })
    return jsonify({"ok": True, "invite_policy": policy})


@app.route("/api/rooms/<int:room_id>/order", methods=["PUT"])
@login_required
def api_room_order(room_id):
    """사용자별 방 순서 조정.
    body: {action: 'pin' | 'unpin' | 'top' | 'bottom' | 'up' | 'down' | 'reset'}
    pin/unpin: rm.pinned 토글. top/bottom/up/down: order_value 조정. reset: 둘 다 NULL.
    각 사용자별 독립적으로 동작 (server 저장)."""
    me = current_user()
    db = get_db()
    rm = db.execute(
        "SELECT pinned, order_value FROM room_members WHERE room_id=? AND user_id=?",
        (room_id, me["id"]),
    ).fetchone()
    if not rm:
        return jsonify({"error": "방 멤버 아님"}), 403
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    if action not in ("pin", "unpin", "top", "bottom", "up", "down", "reset"):
        return jsonify({"error": "action 은 pin/unpin/top/bottom/up/down/reset"}), 400

    # 본인이 속한 모든 방의 정렬 정보 (self 제외, pinned/non-pinned 그룹별)
    # pin 그룹 안에서 order_value 정렬, 일반 그룹 안에서 order_value 정렬
    is_pinned = bool(rm["pinned"])
    my_ov = rm["order_value"]

    def _peers_in_group(pinned_flag):
        """같은 그룹(pin/일반) 의 다른 방들 — order_value 가 설정된 것만."""
        return db.execute("""
            SELECT room_id, order_value FROM room_members
             WHERE user_id=? AND pinned=?
               AND room_id != ?
               AND order_value IS NOT NULL
             ORDER BY order_value ASC
        """, (me["id"], pinned_flag, room_id)).fetchall()

    def _all_in_group_sorted(pinned_flag):
        """그룹 안 모든 방 + 자동정렬 기준(last_at) 까지 합쳐 위→아래 순으로."""
        # api_rooms 와 동일한 정렬 로직: order_value 있는 것 먼저, 없는 것은 last_at desc
        return db.execute("""
            SELECT rm.room_id, rm.order_value,
                   (SELECT created_at FROM messages
                     WHERE room_id = rm.room_id ORDER BY id DESC LIMIT 1) AS last_at
              FROM room_members rm
              JOIN rooms r ON r.id = rm.room_id
             WHERE rm.user_id=? AND rm.pinned=? AND r.type != 'self'
             ORDER BY
                CASE WHEN rm.order_value IS NOT NULL THEN 0 ELSE 1 END,
                rm.order_value ASC,
                (last_at IS NULL), last_at DESC, rm.room_id DESC
        """, (me["id"], pinned_flag)).fetchall()

    now = datetime.now(timezone.utc).isoformat()

    if action == "reset":
        db.execute(
            "UPDATE room_members SET pinned=0, order_value=NULL WHERE room_id=? AND user_id=?",
            (room_id, me["id"]),
        )
    elif action == "pin":
        # 핀 그룹 최상단으로 (가장 작은 order_value 보다 더 작게)
        peers = _peers_in_group(1)
        new_ov = (peers[0]["order_value"] - 1.0) if peers else 0.0
        db.execute(
            "UPDATE room_members SET pinned=1, order_value=? WHERE room_id=? AND user_id=?",
            (new_ov, room_id, me["id"]),
        )
    elif action == "unpin":
        db.execute(
            "UPDATE room_members SET pinned=0 WHERE room_id=? AND user_id=?",
            (room_id, me["id"]),
        )
    elif action == "top":
        peers = _peers_in_group(1 if is_pinned else 0)
        new_ov = (peers[0]["order_value"] - 1.0) if peers else 0.0
        db.execute(
            "UPDATE room_members SET order_value=? WHERE room_id=? AND user_id=?",
            (new_ov, room_id, me["id"]),
        )
    elif action == "bottom":
        # 같은 그룹의 모든 방(자동정렬 포함) 중 가장 큰 order_value 보다 1 크게
        # order_value NULL 인 방들도 고려: 그것들은 last_at 기준 자동정렬이라
        # bottom 으로 보내려면 가장 큰 order_value + 1 보다 더 큰 값으로 설정
        peers = _peers_in_group(1 if is_pinned else 0)
        max_ov = peers[-1]["order_value"] if peers else 0.0
        # 자동정렬 방까지 아래로 보내려면 매우 큰 값 — 그러나 자동정렬은 항상 order_value 있는 것 다음에 표시되므로
        # max_ov + 1 이면 그룹의 명시 정렬된 방들 중 맨 아래. 자동정렬 방들은 더 아래에 표시됨.
        # → 사용자 의도(맨 아래)는 자동정렬 위치 너머. 따라서 9999 같이 매우 큰 값 사용.
        new_ov = 9999.0 + (max_ov or 0)
        db.execute(
            "UPDATE room_members SET order_value=? WHERE room_id=? AND user_id=?",
            (new_ov, room_id, me["id"]),
        )
    elif action in ("up", "down"):
        ordered = _all_in_group_sorted(1 if is_pinned else 0)
        # 현재 인덱스
        idx = next((i for i, x in enumerate(ordered) if x["room_id"] == room_id), -1)
        if idx < 0:
            return jsonify({"error": "정렬 위치 찾기 실패"}), 500
        if action == "up" and idx == 0:
            return jsonify({"ok": True, "no_change": True, "reason": "이미 최상단"})
        if action == "down" and idx == len(ordered) - 1:
            return jsonify({"ok": True, "no_change": True, "reason": "이미 최하단"})
        # 인접한 두 방 사이로 삽입 (REAL 사이값 = 평균)
        if action == "up":
            above = ordered[idx - 1]
            above_ov = above["order_value"]
            if idx >= 2:
                above_above = ordered[idx - 2]
                aa_ov = above_above["order_value"]
                if aa_ov is not None and above_ov is not None:
                    new_ov = (aa_ov + above_ov) / 2
                else:
                    new_ov = (above_ov if above_ov is not None else 0.0) - 1.0
            else:
                new_ov = (above_ov if above_ov is not None else 0.0) - 1.0
        else:  # down
            below = ordered[idx + 1]
            below_ov = below["order_value"]
            if idx + 2 < len(ordered):
                below_below = ordered[idx + 2]
                bb_ov = below_below["order_value"]
                if bb_ov is not None and below_ov is not None:
                    new_ov = (below_ov + bb_ov) / 2
                else:
                    new_ov = (below_ov if below_ov is not None else 0.0) + 1.0
            else:
                new_ov = (below_ov if below_ov is not None else 0.0) + 1.0
        db.execute(
            "UPDATE room_members SET order_value=? WHERE room_id=? AND user_id=?",
            (new_ov, room_id, me["id"]),
        )
    db.commit()
    return jsonify({"ok": True, "action": action})


def _ensure_self_room(uid):
    """사용자의 '나에게 보내기' 1인방 보장. 없으면 생성.
    Telegram Saved Messages / KakaoTalk 나와의 채팅 모델.
    type='self' 이며 room_members 엔트리 1개(본인)만 가짐."""
    db = get_db()
    row = db.execute("""
        SELECT r.id FROM rooms r
         JOIN room_members rm ON rm.room_id = r.id
         WHERE r.type='self' AND rm.user_id=?
         LIMIT 1
    """, (uid,)).fetchone()
    if row:
        return row["id"]
    now = datetime.now(timezone.utc).isoformat()
    cur = db.execute(
        "INSERT INTO rooms (name, type, created_by, created_at, name_locked) VALUES (?,?,?,?,?)",
        ("📝 메모", "self", uid, now, 1),  # name_locked=1 → 별명 비활성
    )
    rid = cur.lastrowid
    db.execute(
        "INSERT INTO room_members (room_id, user_id, joined_at, role) VALUES (?,?,?,?)",
        (rid, uid, now, "host"),
    )
    db.execute(
        "INSERT INTO messages (room_id, user_id, content, kind, created_at) VALUES (?,?,?,?,?)",
        (rid, uid, "📝 메모·임시 파일·즉시 기록용 1인방입니다. 다른 사람은 볼 수 없습니다.", "system", now),
    )
    db.commit()
    return rid


@app.route("/api/me/self_room", methods=["GET"])
@login_required
def api_me_self_room():
    """'나에게 보내기' 1인방 ID 반환. 없으면 자동 생성."""
    me = current_user()
    rid = _ensure_self_room(me["id"])
    return jsonify({"room_id": rid})


@app.route("/api/rooms/<int:room_id>/members/<int:user_id>/role", methods=["POST"])
@login_required
def api_room_set_role(room_id, user_id):
    """멤버 역할 변경 — 방장만. body: {role: 'sub_host'|'member'} (host 는 transfer 로만)"""
    me = current_user()
    db = get_db()
    if _my_room_role(db, room_id, me["id"]) != 'host':
        return jsonify({"error": "방장만 가능"}), 403
    if user_id == me["id"]:
        return jsonify({"error": "본인은 transfer-host 로 변경"}), 400
    data = request.get_json(silent=True) or {}
    new_role = data.get("role")
    if new_role not in ('sub_host', 'member'):
        return jsonify({"error": "role 은 sub_host 또는 member"}), 400
    target = db.execute("SELECT role FROM room_members WHERE room_id=? AND user_id=?",
                        (room_id, user_id)).fetchone()
    if not target:
        return jsonify({"error": "멤버가 아님"}), 404
    db.execute("UPDATE room_members SET role=? WHERE room_id=? AND user_id=?",
               (new_role, room_id, user_id))
    db.commit()
    target_user = db.execute("SELECT display_name FROM users WHERE id=?", (user_id,)).fetchone()
    label = '부방장' if new_role == 'sub_host' else '일반 멤버'
    now = datetime.now(timezone.utc).isoformat()
    sys_text = f"[{target_user['display_name']}] 님이 {label} 으로 지정됨"
    cur = db.execute(
        "INSERT INTO messages (room_id, user_id, content, kind, created_at) VALUES (?,?,?,?,?)",
        (room_id, me["id"], sys_text, "system", now),
    )
    db.commit()
    _emit_room_event(room_id, "member_role_changed", {
        "room_id": room_id, "user_id": user_id, "role": new_role,
    })
    _emit_room_event(room_id, "new_message", {
        "id": cur.lastrowid, "room_id": room_id, "user_id": me["id"],
        "display_name": me["display_name"], "avatar_color": me["avatar_color"],
        "content": sys_text, "kind": "system", "created_at": now,
    })
    return jsonify({"ok": True})


@app.route("/api/rooms/<int:room_id>/transfer-host", methods=["POST"])
@login_required
def api_room_transfer_host(room_id):
    """방장 위임 — 현재 방장만. body: {to_user_id}"""
    me = current_user()
    db = get_db()
    if _my_room_role(db, room_id, me["id"]) != 'host':
        return jsonify({"error": "방장만 가능"}), 403
    data = request.get_json(silent=True) or {}
    to_uid = int(data.get("to_user_id") or 0)
    if not to_uid or to_uid == me["id"]:
        return jsonify({"error": "대상이 자기자신일 수 없음"}), 400
    target = db.execute("SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
                        (room_id, to_uid)).fetchone()
    if not target:
        return jsonify({"error": "대상이 방 멤버가 아님"}), 404
    db.execute("UPDATE room_members SET role='member' WHERE room_id=? AND user_id=?",
               (room_id, me["id"]))
    db.execute("UPDATE room_members SET role='host' WHERE room_id=? AND user_id=?",
               (room_id, to_uid))
    db.execute("UPDATE rooms SET created_by=? WHERE id=?", (to_uid, room_id))
    db.commit()
    to_user = db.execute("SELECT display_name FROM users WHERE id=?", (to_uid,)).fetchone()
    now = datetime.now(timezone.utc).isoformat()
    sys_text = f"방장이 [{me['display_name']}] → [{to_user['display_name']}] 로 변경됨"
    cur = db.execute(
        "INSERT INTO messages (room_id, user_id, content, kind, created_at) VALUES (?,?,?,?,?)",
        (room_id, me["id"], sys_text, "system", now),
    )
    db.commit()
    _emit_room_event(room_id, "host_transferred", {
        "room_id": room_id, "new_host_id": to_uid, "old_host_id": me["id"],
    })
    _emit_room_event(room_id, "new_message", {
        "id": cur.lastrowid, "room_id": room_id, "user_id": me["id"],
        "display_name": me["display_name"], "avatar_color": me["avatar_color"],
        "content": sys_text, "kind": "system", "created_at": now,
    })
    return jsonify({"ok": True})


@app.route("/api/rooms/<int:room_id>/invite", methods=["POST"])
@login_required
def api_room_invite(room_id):
    """방 멤버 초대 — invite_policy 에 따라 권한 분기.
    'all'(기본): 모든 방 멤버가 초대 가능. 'host_only': 방장·부방장만.
    body: {user_ids: [int]}"""
    me = current_user()
    db = get_db()
    # 본인이 멤버인지 확인
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
        (room_id, me["id"]),
    ).fetchone():
        return jsonify({"error": "방 멤버 아님"}), 403
    # 방의 초대 정책 조회
    room_row = db.execute("SELECT invite_policy, type FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not room_row:
        return jsonify({"error": "방을 찾을 수 없음"}), 404
    # 1:1·self 방은 멤버 추가 불가
    if room_row["type"] in ("direct", "self"):
        return jsonify({"error": "1:1 또는 1인방은 멤버를 추가할 수 없습니다"}), 400
    invite_policy = room_row["invite_policy"] or "all"
    my_role = _my_room_role(db, room_id, me["id"])
    if invite_policy == "host_only" and my_role not in ('host', 'sub_host'):
        return jsonify({"error": "이 방은 방장·부방장만 초대할 수 있습니다"}), 403
    data = request.get_json(silent=True) or {}
    user_ids = list({int(x) for x in (data.get("user_ids") or [])})
    if not user_ids:
        return jsonify({"error": "초대할 사용자 ID 필요"}), 400
    now = datetime.now(timezone.utc).isoformat()
    added = []
    for uid in user_ids:
        # 이미 멤버면 skip
        if db.execute("SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
                      (room_id, uid)).fetchone():
            continue
        u = db.execute("SELECT id, display_name, active FROM users WHERE id=?",
                       (uid,)).fetchone()
        if not u or not u["active"]:
            continue
        db.execute("INSERT INTO room_members (room_id, user_id, joined_at, role) VALUES (?,?,?,'member')",
                   (room_id, uid, now))
        added.append(u["display_name"])
    if not added:
        return jsonify({"error": "추가된 사용자 없음 (이미 멤버이거나 비활성)"}), 400
    db.commit()
    sys_text = f"[{', '.join(added)}] 님이 초대됨 (by {me['display_name']})"
    cur = db.execute(
        "INSERT INTO messages (room_id, user_id, content, kind, created_at) VALUES (?,?,?,?,?)",
        (room_id, me["id"], sys_text, "system", now),
    )
    db.commit()
    _emit_room_event(room_id, "members_added", {"room_id": room_id, "added": added})
    _emit_room_event(room_id, "new_message", {
        "id": cur.lastrowid, "room_id": room_id, "user_id": me["id"],
        "display_name": me["display_name"], "avatar_color": me["avatar_color"],
        "content": sys_text, "kind": "system", "created_at": now,
    })
    return jsonify({"ok": True, "added": added})


@app.route("/api/rooms/<int:room_id>/members/<int:user_id>/kick", methods=["POST"])
@login_required
def api_room_kick(room_id, user_id):
    """멤버 추방. host 는 모든 멤버. sub_host 는 일반 member 만."""
    me = current_user()
    db = get_db()
    my_role = _my_room_role(db, room_id, me["id"])
    if my_role not in ('host', 'sub_host'):
        return jsonify({"error": "방장·부방장만 추방 가능"}), 403
    if user_id == me["id"]:
        return jsonify({"error": "본인은 /leave 로 나가기"}), 400
    target = db.execute("SELECT u.display_name, rm.role FROM room_members rm "
                        "JOIN users u ON u.id=rm.user_id "
                        "WHERE rm.room_id=? AND rm.user_id=?",
                        (room_id, user_id)).fetchone()
    if not target:
        return jsonify({"error": "멤버가 아님"}), 404
    if my_role == 'sub_host' and target["role"] in ('host', 'sub_host'):
        return jsonify({"error": "부방장은 방장·부방장 추방 불가"}), 403
    db.execute("DELETE FROM room_members WHERE room_id=? AND user_id=?", (room_id, user_id))
    db.commit()
    now = datetime.now(timezone.utc).isoformat()
    sys_text = f"[{target['display_name']}] 님이 추방됨 (by {me['display_name']})"
    cur = db.execute(
        "INSERT INTO messages (room_id, user_id, content, kind, created_at) VALUES (?,?,?,?,?)",
        (room_id, me["id"], sys_text, "system", now),
    )
    db.commit()
    _emit_room_event(room_id, "member_kicked", {"room_id": room_id, "user_id": user_id})
    _emit_room_event(room_id, "new_message", {
        "id": cur.lastrowid, "room_id": room_id, "user_id": me["id"],
        "display_name": me["display_name"], "avatar_color": me["avatar_color"],
        "content": sys_text, "kind": "system", "created_at": now,
    })
    return jsonify({"ok": True})


@app.route("/api/rooms/<int:room_id>/read", methods=["POST"])
@login_required
def api_mark_read(room_id):
    me = current_user()
    db = get_db()
    last = db.execute("SELECT MAX(id) AS m FROM messages WHERE room_id=?", (room_id,)).fetchone()
    if last and last["m"]:
        db.execute(
            "UPDATE room_members SET last_read_message_id=? WHERE room_id=? AND user_id=?",
            (last["m"], room_id, me["id"]),
        )
        db.commit()
        # 같은 방의 다른 클라이언트에 읽음 알림 → 그쪽 UI에서 "안 읽음 N" 숫자 갱신
        socketio.emit("read_status", {
            "room_id": room_id,
            "user_id": me["id"],
            "last_read": last["m"],
        }, to=f"room_{room_id}")
    return jsonify({"ok": True, "last_read": last["m"] if last else 0})


@app.route("/api/rooms/<int:room_id>/read_status")
@login_required
def api_read_status(room_id):
    """방 멤버별 마지막으로 읽은 메시지 ID 반환 (읽음/안읽음 표시용)."""
    me = current_user()
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?", (room_id, me["id"])
    ).fetchone():
        abort(403)
    rows = db.execute("""
        SELECT rm.user_id, rm.last_read_message_id, u.display_name, u.avatar_color
          FROM room_members rm JOIN users u ON u.id = rm.user_id
         WHERE rm.room_id = ?
    """, (room_id,)).fetchall()
    return jsonify({
        "members": [dict(r) for r in rows],
        "total": len(rows),
    })


# ---------- SocketIO ----------
@socketio.on("connect")
def on_connect():
    """클라이언트 SocketIO 연결 시점에 사용자가 속한 모든 방에 자동 join.
    카카오톡식 동작 — 활성 방이 아니어도 모든 방의 new_message broadcast 를 받아
    소리·토스트·사이드바 깜빡임 등 알림이 동작.
    + Presence 등록 — 클라이언트가 곧이어 "presence" 이벤트로 device/active 갱신."""
    uid = session.get("user_id")
    if not uid:
        return
    try:
        with app.app_context():
            db = get_db()
            rows = db.execute(
                "SELECT room_id FROM room_members WHERE user_id=?", (uid,)
            ).fetchall()
            for r in rows:
                sio_join(f"room_{r['room_id']}")
    except Exception as e:
        print(f"[socket connect] auto-join 실패: {e}")
    # Presence — 일단 device 미상·active=True 로 등록.
    # 클라이언트가 connect 직후 emit("presence", {device, active}) 보내며 갱신.
    try:
        _presence_register(uid, request.sid, device="unknown", active=True)
    except Exception as e:
        print(f"[presence] register 실패: {e}")


@socketio.on("disconnect")
def on_disconnect():
    """SocketIO 연결 해제 시 presence 에서 제거."""
    uid = session.get("user_id")
    if not uid:
        return
    try:
        _presence_unregister(uid, request.sid)
    except Exception as e:
        print(f"[presence] unregister 실패: {e}")


@socketio.on("presence")
def on_presence(data):
    """클라이언트의 device_type + active 상태 보고.
    페이지 visibility 변경, focus/blur 마다 호출됨.
    이 정보로 _user_has_active_pc(uid) 가 푸시 스킵 여부를 판단."""
    uid = session.get("user_id")
    if not uid or not isinstance(data, dict):
        return
    device = data.get("device")
    if device not in ("pc", "mobile"):
        device = "unknown"
    active = bool(data.get("active", True))
    try:
        _presence_register(uid, request.sid, device=device, active=active)
    except Exception as e:
        print(f"[presence] update 실패: {e}")


@socketio.on("join")
def on_join(data):
    rid = data.get("room_id") if isinstance(data, dict) else None
    if rid:
        sio_join(f"room_{rid}")


@socketio.on("leave")
def on_leave(data):
    rid = data.get("room_id") if isinstance(data, dict) else None
    if rid:
        sio_leave(f"room_{rid}")


@socketio.on("send")
def on_send(data):
    uid = session.get("user_id")
    if not uid or not isinstance(data, dict):
        return
    room_id = data.get("room_id")
    content = (data.get("content") or "").strip()
    if not room_id or not content:
        return
    if len(content) > 4000:
        content = content[:4000]
    # 인용 답장 — quoted_message_id (선택). 본 채널에 답글 + 원본 미니 카드.
    quoted_id = data.get("quoted_message_id")
    try:
        quoted_id = int(quoted_id) if quoted_id else None
    except (ValueError, TypeError):
        quoted_id = None

    with app.app_context():
        db = get_db()
        if not db.execute(
            "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
            (room_id, uid),
        ).fetchone():
            return
        # quoted_id 가 있으면 같은 방의 메시지인지 검증 (다른 방 메시지를 인용은 안 됨 — 전달 기능 사용)
        if quoted_id:
            qrow = db.execute(
                "SELECT room_id FROM messages WHERE id=?", (quoted_id,)
            ).fetchone()
            if not qrow or qrow["room_id"] != room_id:
                quoted_id = None
        now = datetime.now(timezone.utc).isoformat()
        cur = db.execute(
            "INSERT INTO messages (room_id, user_id, content, kind, created_at, quoted_message_id) VALUES (?,?,?,?,?,?)",
            (room_id, uid, content, "text", now, quoted_id),
        )
        mid = cur.lastrowid
        db.commit()
        u = db.execute(
            "SELECT display_name, avatar_color FROM users WHERE id=?", (uid,)
        ).fetchone()
        # quoted 메타데이터 — 클라이언트가 즉시 카드로 렌더할 수 있도록 함께 보냄
        quoted_meta = None
        if quoted_id:
            q = db.execute("""
                SELECT m.id, m.content, m.kind, m.created_at, m.file_name,
                       u.display_name, u.avatar_color
                  FROM messages m JOIN users u ON u.id = m.user_id
                 WHERE m.id = ?
            """, (quoted_id,)).fetchone()
            if q:
                quoted_meta = dict(q)

    payload = {
        "id": mid,
        "room_id": room_id,
        "user_id": uid,
        "display_name": u["display_name"],
        "avatar_color": u["avatar_color"],
        "content": content,
        "kind": "text",
        "created_at": now,
    }
    if quoted_id:
        payload["quoted_message_id"] = quoted_id
        payload["quoted"] = quoted_meta
    socketio.emit("new_message", payload, to=f"room_{room_id}")

    # Web Push — 백그라운드 알림 (송신자 제외 모든 방 멤버)
    if PYWEBPUSH_OK:
        # 방 이름 조회 + 메시지에 멘션 있는지 검사
        with app.app_context():
            db2 = get_db()
            r = db2.execute("SELECT name, type FROM rooms WHERE id=?", (room_id,)).fetchone()
            room_name = r["name"] if r else "채팅"
        title = f"💬 {u['display_name']} ({room_name})"
        body = content[:120]
        # 비동기 스레드로 발송 (pywebpush는 HTTP 호출이라 블로킹)
        import threading
        threading.Thread(
            target=push_message_to_room_members,
            args=(room_id, uid, title, body),
            kwargs={"url": f"{BASE_PATH}/chat?room={room_id}", "tag": f"room_{room_id}"},
            daemon=True,
        ).start()


def _local_ips():
    """이 PC의 LAN/VPN IP들을 모두 반환."""
    ips = set()
    try:
        import socket as _sock
        host = _sock.gethostname()
        for info in _sock.getaddrinfo(host, None):
            ip = info[4][0]
            if ip and ":" not in ip and not ip.startswith("127."):
                ips.add(ip)
    except Exception:
        pass
    return sorted(ips)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    init_db()
    _start_calendar_worker()  # 캘린더 자동 상태 전환 백그라운드 워커
    _start_project_history_worker()  # 프로젝트 이력 하루 1회 자동 생성
    print()
    print(" ============================================")
    print("  KNK Messenger - server start")
    print(" ============================================")
    print(f"   PC (this server):  http://localhost:{PORT}")
    for ip in _local_ips():
        print(f"   employee URL:      http://{ip}:{PORT}")
    print(f"   port:              {PORT}  (open in firewall)")
    print(f"   upload dir:        {UPLOAD_DIR}")
    print(f"   DB:                {DB_PATH}")
    print(f"   retention:         {MESSAGE_RETENTION_MONTHS} months")
    print(f"   env:               {ENV}  async_mode={ASYNC_MODE}")
    if ANTHROPIC_API_KEY:
        print(f"   AI translation:    REAL (Claude {TRANSLATE_MODEL}, ${TRANSLATE_MONTHLY_USD_LIMIT}/month limit)")
    elif TRANSLATE_MOCK:
        print(f"   AI translation:    DEMO MODE (auto-enabled, no API key)")
        print(f"                      -> 가짜 번역 + KNK 핵심 용어만 진짜 변환")
        print(f"                      -> 진짜 번역 원하시면: 번역키설정.bat 실행")
    else:
        print(f"   AI translation:    DISABLED")
    print(" ============================================")
    print()
    socketio.run(app, host="0.0.0.0", port=PORT, debug=False, allow_unsafe_werkzeug=True)
