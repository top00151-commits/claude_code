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
import secrets
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
MAX_UPLOAD_MB = int(os.environ.get("KNK_MSG_MAX_UPLOAD_MB", "1000"))   # 요청당 전체 1GB (대표 지시 2026-05-19. nginx client_max_body_size 함께 조정 필요)
MESSAGE_RETENTION_MONTHS = int(os.environ.get("KNK_MSG_RETENTION_MONTHS", "12"))
VAPID_PRIV_PATH = os.path.join(APP_DIR, "data", "vapid_private.pem")
VAPID_CONTACT = os.environ.get("KNK_MSG_CONTACT", "mailto:admin@knknara.co.kr")

# ---------- 운영(인터넷) 배포용 환경변수 ----------
# 운영 모드: KNK_MSG_ENV=production 으로 켜면 보안 헤더·HTTPS 강제·CORS 제한 활성
ENV = os.environ.get("KNK_MSG_ENV", "development").lower()
IS_PRODUCTION = ENV == "production"

# === 최고관리자(소유자) — 대표 지시 2026-05-21 ===
# 이 username 계정은 부팅 시 자동으로 관리자(ceo)·활성 보장되고,
# 강등·비활성·삭제가 차단(보호)되며, 화면에 '👑 최고관리자' 로 표시된다.
# 코드/환경변수로 지정되므로 운영 DB 를 직접 안 만져도 배포(재시작)만으로 적용.
OWNER_USERNAME = os.environ.get("KNK_MSG_OWNER_USERNAME", "top0015@knknara.co.kr").strip().lower()

def _is_owner(username):
    """이 계정이 최고관리자(소유자)인지."""
    return bool(username) and str(username).strip().lower() == OWNER_USERNAME


def _is_team_lead(user):
    """직급(title)에 '팀장' 포함 = 팀장. (대표 지시 2026-05-21 — 채널 생성·관리 권한)"""
    try:
        return bool(user) and ("팀장" in (user["title"] or ""))
    except Exception:
        return False


def _norm_dept(dept):
    """부서 정규화 — 끝의 (괄호) 제거. 동일 부서 인식용.
    예) '04 설계팀(자동화)'·'04 설계팀(검사기)' → '04 설계팀' (대표 지시 2026-05-21)."""
    return re.sub(r'\s*\([^)]*\)\s*$', '', (dept or '').strip())
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


# ---------- Presence (PC 활성 시 모바일 푸시 억제) ----------
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

# PC presence 가 이 시간(초) 이상 갱신 안 되면 "실제로 보고 있지 않음"(절전·자리비움)으로 간주.
# 클라이언트가 30초마다 heartbeat 를 보내므로, 60초 = heartbeat 2회 누락 시 비활성 판정.
# (대표 지시 2026-05-20: PC 켜둬도 자리 비우면 모바일 알림 와야 함)
_PC_ACTIVE_STALE_SEC = 60

def _user_has_active_pc(uid):
    """해당 사용자의 PC 연결 중 '실제로 활성'(포커스 + 최근 heartbeat) 게 있으면 True.
    이 때만 모바일 푸시를 발송하지 않음 — PC 활성 감지 + 자리비움 보정.
    PC active 라도 마지막 presence 갱신이 _PC_ACTIVE_STALE_SEC 이상 오래됐으면
    절전·잠금·자리비움으로 보고 False 반환 → 모바일 푸시 정상 발송."""
    if not uid:
        return False
    now = _pres_time.time()
    with _user_conn_lock:
        conns = _user_connections.get(uid, {})
        for sid, info in conns.items():
            if info.get("device") == "pc" and info.get("active"):
                ts = info.get("ts", 0)
                if now - ts <= _PC_ACTIVE_STALE_SEC:
                    return True   # PC 가 진짜 활성 (최근 heartbeat 있음)
    return False


def _user_is_online(uid):
    """uid 의 활성 SocketIO 연결이 하나라도 있으면 True (= 로그인 상태).
    아무 연결도 없으면 False (= 미접속·오프라인).
    상태 점등용 — 사용자가 별도 상태 설정을 하지 않아도 본 함수가 False 면 'offline' 강제."""
    if not uid:
        return False
    with _user_conn_lock:
        return bool(_user_connections.get(uid))


def _user_has_pc_connection(uid):
    """uid 의 현재 소켓 연결 중 'pc' 기기가 하나라도 있으면 True.
    상태 자동표시용 — PC 접속 있으면 '가능', 휴대폰만이면 '휴대폰'.
    (절전·자리비움 stale 체크는 안 함 — 그건 푸시 억제용 _user_has_active_pc 의 역할)."""
    if not uid:
        return False
    with _user_conn_lock:
        for info in _user_connections.get(uid, {}).values():
            if info.get("device") == "pc":
                return True
    return False


def send_push_to_user(user_id, title, body, url=None, tag=None, collect_errors=False, clear=False):
    """특정 사용자의 모든 push 구독에 알림 전송. 410/404는 만료로 간주하고 삭제.
    collect_errors=True 이면 (sent_count, [{id, endpoint, error}], total_subs) 튜플 반환.
    clear=True 이면 알림을 띄우는 대신 '읽음' 신호(type=clear)를 보내 sw.js 가 해당 방(tag)
    알림을 닫고 배지만 갱신하게 한다 — 다른 기기(백그라운드 휴대폰)의 알림 자동 삭제용."""
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
        # 앱 아이콘 배지용 — 이 사용자의 전체 안 읽은 메시지 총합 (방 목록 unread 와 동일 계산)
        badge_count = 0
        try:
            brow = db.execute("""
                SELECT COALESCE(SUM(cnt), 0) AS total FROM (
                    SELECT (SELECT COUNT(*) FROM messages m
                              WHERE m.room_id = rm.room_id
                                AND m.id > rm.last_read_message_id
                                AND m.user_id != ?
                                AND (m.whisper_to_user_id IS NULL OR m.whisper_to_user_id = ?)
                           ) AS cnt
                      FROM room_members rm
                     WHERE rm.user_id = ?
                )
            """, (user_id, user_id, user_id)).fetchone()
            badge_count = (brow["total"] or 0) if brow else 0
        except Exception:
            badge_count = 0
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
                    data=json.dumps(
                        {"type": "clear", "tag": tag, "badge": badge_count}
                        if clear else
                        {"title": title, "body": body, "url": url or "/chat", "tag": tag, "badge": badge_count}
                    ),
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
        # 해당 사용자가 PC에서 활성(포커스) 상태이면 푸시 스킵.
        # 이중 알림(PC 화면 + 휴대폰 진동) 피로 해소가 1차 목적.
        if _user_has_active_pc(m["user_id"]):
            print(f"[push] skip uid={m['user_id']} — PC active")
            continue
        send_push_to_user(m["user_id"], title, body, url=url, tag=tag)
# ============================================================
# 🛡️ 파일 업로드 보안 정책 (대표 지시 2026-05-19 강화)
#   1) 화이트리스트 — 허용된 확장자만 통과
#   2) 블랙리스트 — 위험 실행 파일 명시 차단 (defense-in-depth)
#   3) Magic Number 검증 — 확장자 위조 차단 (예: report.pdf 인데 PE 헤더)
#   4) 더블 확장자 차단 — 예: "report.pdf.exe"
#   5) 단일 파일 크기 — 별도 제한 (PER_FILE_MAX_MB)
# ============================================================
DANGEROUS_EXT = {
    # Windows 실행
    "exe", "scr", "com", "bat", "cmd", "pif", "msi", "msu", "msp", "cpl",
    "vb", "vbs", "vbe", "js", "jse", "wsf", "wsh", "ps1", "ps2", "psc1", "psc2",
    "lnk", "url", "inf", "reg",
    # 매크로 가능 Office
    "docm", "xlsm", "pptm", "dotm", "xltm", "potm",
    # Linux/Mac 실행
    "sh", "bash", "zsh", "csh", "ksh", "fish",
    "app", "dmg", "pkg", "deb", "rpm",
    # 기타 위험
    "jar", "class", "war", "ear",   # Java
    "py", "pl", "rb", "php",         # 스크립트
    "apk", "ipa",                    # 모바일
    "html", "htm", "xhtml", "shtml", # HTML (XSS 위험 — 다운로드 후 브라우저로 열면 JS 실행)
    "svg",                           # SVG (script 임베드 가능)
    "iso", "img",                    # 디스크 이미지
}
# 실행 파일 magic number — 확장자 위조에도 검출
EXECUTABLE_MAGIC = [
    b"MZ",          # Windows PE (exe, dll, scr ...)
    b"\x7fELF",     # Linux ELF
    b"\xca\xfe\xba\xbe",  # Mach-O fat binary
    b"\xcf\xfa\xed\xfe",  # Mach-O 64bit
    b"\xfe\xed\xfa\xce",  # Mach-O 32bit
    b"\xfe\xed\xfa\xcf",  # Mach-O 64bit BE
    b"PK\x03\x04",        # zip (jar/apk 도 zip — 확장자로 추가 판단)
    b"#!",                # Shebang (스크립트)
]
PER_FILE_MAX_MB = int(os.environ.get("KNK_MSG_PER_FILE_MAX_MB", "500"))   # 단일 파일 500MB (대표 지시 2026-05-19)

# ============================================================
# 🛡️ Rate Limiter (In-Memory, 분 단위 슬라이딩 윈도)
#   uid + 액션 별로 분당 호출 횟수 제한. 스팸·DoS 차단.
#   단일 worker 환경 가정. 다중 worker 확장 시 Redis 로 교체.
# ============================================================
import collections as _rl_collections
_rate_buckets = _rl_collections.defaultdict(list)  # (uid, action) -> [timestamps]
_rate_lock = _pres_threading.Lock()

def _check_rate_limit(uid, action, max_per_minute=60):
    """uid 의 액션 분당 횟수 검사. 통과 시 True, 초과 시 False.
    호출 시점을 기록 → 60초 이전 기록은 자동 정리."""
    if not uid:
        return True
    now = _pres_time.time()
    cutoff = now - 60.0
    key = (uid, action)
    with _rate_lock:
        bucket = _rate_buckets[key]
        # 60초 이전 기록 제거
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)
        if len(bucket) >= max_per_minute:
            return False
        bucket.append(now)
    return True

def _is_dangerous_filename(filename):
    """파일명 자체에 위험 패턴이 있는지 확인.
    - 더블 확장자 (report.pdf.exe)
    - 위험 확장자 (exe, bat, ...)
    - 숨김 파일 (.htaccess)"""
    if not filename:
        return True, "파일명이 비어 있습니다"
    fn = filename.lower().strip()
    # 더블 확장자 — 위험 확장자가 마지막이 아닌 중간에 있으면 의심
    parts = fn.split(".")
    if len(parts) >= 3:
        # 마지막에서 두 번째 부분이 위험 확장자면 → 위장 의심
        for p in parts[1:-1]:
            if p in DANGEROUS_EXT:
                return True, f"이중 확장자 의심 (.{p}.~)"
    last_ext = parts[-1] if len(parts) > 1 else ""
    if last_ext in DANGEROUS_EXT:
        return True, f"실행 파일 확장자 차단 (.{last_ext})"
    return False, ""

def _check_executable_magic(file_storage):
    """파일 첫 16바이트 읽어 magic number 검사 — 실행 파일이면 차단.
    호출 후 stream pointer 를 처음으로 되돌려 놓음."""
    try:
        header = file_storage.stream.read(16)
        file_storage.stream.seek(0)
    except Exception:
        return False, ""
    for sig in EXECUTABLE_MAGIC:
        if header.startswith(sig):
            # PK (zip) 은 docx/xlsx 등도 zip 이므로 별도 처리. 여기는 확장자가 이미 화이트리스트 통과한 후라
            # zip 매직이라도 OK. 다만 명시적으로 zip 확장자 아니면서 PK 면 위험.
            if sig == b"PK\x03\x04":
                continue
            # 셔뱅 #! — 텍스트 파일에도 있을 수 있으나 .txt 화이트리스트 안에서 보면 위험 X
            if sig == b"#!":
                continue
            return True, f"실행 파일 헤더 검출 (magic: {sig.hex()})"
    return False, ""


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
    # SocketIO 버퍼는 단일 메시지 한도 — HTTP 업로드는 별도 (Flask MAX_CONTENT_LENGTH 가 1GB).
    # 1GB 버퍼는 OOM 위험 (단일 worker, 4-8GB RAM) → 512MB 로 제한 (2026-05-20).
    max_http_buffer_size=512 * 1024 * 1024,
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


@app.errorhandler(500)
def handle_500(err):
    """500 에러 자동 로깅 + 관리자 socketio 알림 (대표 지시 2026-05-19)."""
    import traceback as _tb
    tb_str = _tb.format_exc()
    try:
        # 파일 로그 — 운영 시점 디버깅 가능하도록 영속화
        log_path = os.path.join(APP_DIR, "data", "error.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n\n=== [{datetime.now(timezone.utc).isoformat()}] {request.method} {request.path} ===\n")
            try:
                uid = session.get("user_id")
                f.write(f"user_id={uid}, ip={request.remote_addr}, ua={request.user_agent.string[:200]}\n")
            except Exception:
                pass
            f.write(tb_str)
    except Exception:
        pass
    # 관리자(ceo) 들에게 실시간 알림 (socketio) — 최초 100자만
    try:
        short = tb_str.split("\n")[-2] if len(tb_str.split("\n")) >= 2 else str(err)
        socketio.emit("admin_error_alert", {
            "path": request.path,
            "method": request.method,
            "error": short[:200],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass
    return jsonify({"error": "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요."}), 500


@app.errorhandler(413)
def handle_413(err):
    """파일이 너무 큼 (Flask MAX_CONTENT_LENGTH 초과)."""
    return jsonify({"error": f"파일이 너무 큽니다 (최대 {MAX_UPLOAD_MB}MB)"}), 413


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
        db = g._db = sqlite3.connect(DB_PATH, timeout=20.0)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        # 동시성 향상 — WAL 모드: 읽기·쓰기 동시 가능, 쓰기 락 범위 축소 (2026-05-20)
        # 75명 동시 사용 시 DB 락 병목 해소.
        db.execute("PRAGMA journal_mode=WAL")
        # 안전성-성능 trade-off: NORMAL — 전원 차단 시 마지막 트랜잭션 손실 가능하나 OS 크래시엔 안전
        db.execute("PRAGMA synchronous=NORMAL")
        # 락 대기 — 동시 INSERT 충돌 시 최대 20초 재시도 (기본 5초 → 20초)
        db.execute("PRAGMA busy_timeout=20000")
        # 캐시 — 페이지 캐시 64MB (기본 2MB → 64MB)
        db.execute("PRAGMA cache_size=-65536")
        # WAL 자동 체크포인트 — 1000 페이지 (기본). 너무 늦추면 .wal 파일 커짐.
    return db


@app.teardown_appcontext
def close_db(_exc):
    db = getattr(g, "_db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # WAL 모드 한 번만 적용 (DB 파일 메타에 영구 저장됨) — 2026-05-20
    try:
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA busy_timeout=20000")
    except Exception as _e:
        print(f"[init_db] PRAGMA 적용 실패 (무시): {_e}", flush=True)
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

    -- 프로젝트(=프로젝트/품목): 일반 메신저의 '방'을 자동 정리 가능한 단위로 승격
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY,
        room_id INTEGER UNIQUE NOT NULL,
        code TEXT,                          -- 관리번호 e.g. 003M2501
        name TEXT NOT NULL,                 -- 프로젝트명
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

    -- 메시지 전달확인 (acknowledgment) — '읽음'을 넘어선 명시적 확인
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

    -- 사용자 상태 (자리비움·회의중·외근·방해금지·온라인·오프라인)
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

    -- 프로젝트(프로젝트 방) 이력 스냅샷 — HAIST WORKS 연동 대비.
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

    -- AI 요약 캐시
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

    -- 동시 로그인 제한 (휴대폰 1대 + PC 1대) — (user_id, device_type) 당 활성 세션 1개만.
    -- 같은 종류 기기에서 새로 로그인하면 token 이 덮어써져 옛 기기 세션이 무효화됨.
    CREATE TABLE IF NOT EXISTS active_sessions (
        user_id INTEGER NOT NULL,
        device_type TEXT NOT NULL,   -- 'pc' | 'mobile'
        token TEXT NOT NULL,
        user_agent TEXT,
        ip TEXT,
        created_at TEXT NOT NULL,
        PRIMARY KEY (user_id, device_type),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    conn.commit()

    # ---- 컬럼 마이그레이션 ----
    existing_msg_cols = {row["name"] for row in cur.execute("PRAGMA table_info(messages)").fetchall()}
    for col, ddl in [
        ("file_path", "ALTER TABLE messages ADD COLUMN file_path TEXT"),
        ("file_name", "ALTER TABLE messages ADD COLUMN file_name TEXT"),
        ("file_size", "ALTER TABLE messages ADD COLUMN file_size INTEGER"),
        ("file_mime", "ALTER TABLE messages ADD COLUMN file_mime TEXT"),
        # 스레드 — parent_message_id 가 채워지면 스레드 답글.
        # NULL=일반 메시지 (메인 채널에 표시). NOT NULL=답글 (스레드 패널에만 표시).
        ("parent_message_id", "ALTER TABLE messages ADD COLUMN parent_message_id INTEGER"),
        # 인용 답장(Quote Reply) — 본 채널에 답글 + 원본 미니 카드 표시 (스레드와 별개)
        ("quoted_message_id", "ALTER TABLE messages ADD COLUMN quoted_message_id INTEGER"),
        # 전달(Forward) 출처 — 메타데이터 보존
        # 원본 메시지 ID. 원본이 삭제돼도 아래 forwarded_* 캐시로 복원 가능
        ("forwarded_from_message_id", "ALTER TABLE messages ADD COLUMN forwarded_from_message_id INTEGER"),
        ("forwarded_from_user_id", "ALTER TABLE messages ADD COLUMN forwarded_from_user_id INTEGER"),
        # 원본 작성자명·방명·시각 캐시 (원본 삭제 후에도 표시되도록)
        ("forwarded_from_name", "ALTER TABLE messages ADD COLUMN forwarded_from_name TEXT"),
        ("forwarded_from_room_name", "ALTER TABLE messages ADD COLUMN forwarded_from_room_name TEXT"),
        ("forwarded_from_created_at", "ALTER TABLE messages ADD COLUMN forwarded_from_created_at TEXT"),
        # 귓속말 — 특정 한 사용자에게만 보이는 메시지 (sender + recipient 만). NULL=공개.
        ("whisper_to_user_id", "ALTER TABLE messages ADD COLUMN whisper_to_user_id INTEGER"),
        # 앨범 묶음 — 사진 N장을 1개 그리드 메시지로 묶을 때 부여하는 UUID. NULL=단독.
        ("album_id", "ALTER TABLE messages ADD COLUMN album_id TEXT"),
        # 편집 이력 — 마지막 수정 시각 (NULL=한 번도 편집 안 함) (대표 지시 2026-05-19)
        ("edited_at", "ALTER TABLE messages ADD COLUMN edited_at TEXT"),
    ]:
        if col not in existing_msg_cols:
            cur.execute(ddl)
    # 스레드 답글 조회 인덱스
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_parent ON messages(parent_message_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_quoted ON messages(quoted_message_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_whisper ON messages(room_id, whisper_to_user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_album ON messages(album_id)")

    existing_item_cols = {row["name"] for row in cur.execute("PRAGMA table_info(items)").fetchall()}
    if "keep_forever" not in existing_item_cols:
        cur.execute("ALTER TABLE items ADD COLUMN keep_forever INTEGER DEFAULT 0")

    # 사용자 활성/비활성 (퇴사자 차단)
    existing_user_cols = {row["name"] for row in cur.execute("PRAGMA table_info(users)").fetchall()}
    if "active" not in existing_user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1")
    # 직급·부서 — 사이드바 "사용자" 탭에서 표시
    if "title" not in existing_user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN title TEXT")
    if "department" not in existing_user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN department TEXT")
    # 회사 이메일·전화번호 — 사내 디렉터리
    if "email" not in existing_user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN email TEXT")
    if "phone" not in existing_user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    # 첫 로그인 시 비밀번호 변경 강제 (신규 등록자는 1, 기존 사용자는 0)
    if "must_change_password" not in existing_user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0")
    # 사번 — 회사 내부 직원 식별 번호 (대표 지시 2026-05-19)
    if "employee_no" not in existing_user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN employee_no TEXT")
    # 아바타 사진 URL — 본인 사진 업로드용. NULL 이면 이름 첫 글자 + 배경색 표시 (대표 지시 2026-05-19)
    if "avatar_url" not in existing_user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")

    # 사용자 상태 — 'dnd' (방해금지) 옵션 제거됨 → 기존 dnd 사용자는 online(회사)로 환원
    try:
        cur.execute("UPDATE user_statuses SET status='online' WHERE status='dnd'")
    except Exception:
        pass

    # 옛 부서명 '경영지원' (시드값) → KNK 표준 '관리팀' (대표 지시 2026-05-19).
    # 단, 직급이 '대표이사'인 사람은 부서 소속 없음 → 대상 제외.
    try:
        cur.execute(
            "UPDATE users SET department='관리팀' "
            "WHERE department='경영지원' AND (title IS NULL OR title != '대표이사')"
        )
    except Exception:
        pass

    # 마이그레이션 버전 추적 테이블 — 1회성 데이터 변환이 매 재시작마다 반복되지 않도록 (대표 지시 2026-05-19)
    try:
        cur.execute("CREATE TABLE IF NOT EXISTS app_migrations (name TEXT PRIMARY KEY, applied_at TEXT)")
    except Exception:
        pass

    def _migration_applied(name):
        try:
            return cur.execute("SELECT 1 FROM app_migrations WHERE name=?", (name,)).fetchone() is not None
        except Exception:
            return False

    def _mark_migration(name):
        try:
            cur.execute("INSERT OR REPLACE INTO app_migrations (name, applied_at) VALUES (?, ?)",
                        (name, datetime.now(timezone.utc).isoformat()))
        except Exception:
            pass

    # 대표이사 직급 → '총괄' (00) 부서 1회성 배정.
    # 이후 UI 에서 부서 수동 변경 시 덮어쓰지 않음 (마이그레이션 버전 마커).
    if not _migration_applied("v2_ceo_to_chonggwal"):
        try:
            cur.execute("UPDATE users SET department='총괄' WHERE title='대표이사' AND (department IS NULL OR department != '총괄')")
            _mark_migration("v2_ceo_to_chonggwal")
        except Exception:
            pass

    # 베트남법인 부서값 재포맷 — 1회성. 'VN기술팀' → 'VN12-01 기술팀' 등.
    # (이력 보존용 — 이후 v5_vn_format_swap 에서 다시 '12-VN01 기술팀' 형식으로 swap)
    if not _migration_applied("v2_vn_remap"):
        try:
            _vn_remap = {
                "VN기술팀":       "VN12-01 기술팀",
                "VN조립팀":       "VN12-02 조립팀",
                "VN전장팀":       "VN12-03 전장팀",
                "VN설계팀":       "VN12-04 설계팀",
                "VN소프트웨어팀": "VN12-05 소프트웨어팀",
                "VN가공팀":       "VN12-06 가공팀",
                "VN품질팀":       "VN12-07 품질팀",
                "VN구매팀":       "VN12-08 구매팀",
                "VN관리팀":       "VN12-09 관리팀",
            }
            for old_val, new_val in _vn_remap.items():
                cur.execute("UPDATE users SET department=? WHERE department=?", (new_val, old_val))
            _mark_migration("v2_vn_remap")
        except Exception:
            pass

    # 베트남법인 부서값 포맷 변경 (대표 지시 2026-05-20)
    #   'VN12-NN 부서명' → '12-VNNN 부서명'
    #   예: 'VN12-09 관리팀' → '12-VN09 관리팀'
    #   한국법인 코드 12 가 앞으로 나오고 VN 이 베트남 부서번호 앞에 붙음.
    if not _migration_applied("v5_vn_format_swap"):
        try:
            _vn_swap = {
                "VN12-01 기술팀":       "12-VN01 기술팀",
                "VN12-02 조립팀":       "12-VN02 조립팀",
                "VN12-03 전장팀":       "12-VN03 전장팀",
                "VN12-04 설계팀":       "12-VN04 설계팀",
                "VN12-05 소프트웨어팀": "12-VN05 소프트웨어팀",
                "VN12-06 가공팀":       "12-VN06 가공팀",
                "VN12-07 품질팀":       "12-VN07 품질팀",
                "VN12-08 구매팀":       "12-VN08 구매팀",
                "VN12-09 관리팀":       "12-VN09 관리팀",
            }
            _vs_changed = 0
            for old_val, new_val in _vn_swap.items():
                r = cur.execute("UPDATE users SET department=? WHERE department=?", (new_val, old_val))
                _vs_changed += (r.rowcount or 0)
            _mark_migration("v5_vn_format_swap")
            print(f"[migration] v5_vn_format_swap 1회 실행 — {_vs_changed}명 UPDATE", flush=True)
        except Exception as _e:
            print(f"[migration] v5_vn_format_swap 실패: {_e}", flush=True)

    # ── KNK 직원 명단 Excel 기준 부서값 일괄 정정 (대표 지시 2026-05-19) ──
    # 1회성 마이그레이션. 이후 UI 변경은 보존됨.
    # 강제 재실행: 버전 이름 ('v4_excel_dept_remap') 을 새 번호로 바꾸면 다시 1회 실행됨.
    # 모호 케이스: 김동현→설계팀(자동화), 김범수→설계팀(검사기), 윤경호→설계팀(자동화)
    # chkcsd(최홍광 전무)→총괄, dhkimman/top0015(대표이사)→총괄
    if not _migration_applied("v4_excel_dept_remap"):
        EXCEL_DEPT_REMAP = {
            "anjiyeon@knknara.co.kr": "기술영업팀",
            "b8004@knknara.co.kr": "검사기팀",
            "bumsu.kim@knknara.co.kr": "설계팀(검사기)",
            "buy1@knknara.co.kr": "구매팀",
            "buy2@knknara.co.kr": "구매팀",
            "buy3@knknara.co.kr": "구매팀",
            "buy4@knknara.co.kr": "구매팀",
            "buy5@knknara.co.kr": "구매팀",
            "changho.choi@knknara.co.kr": "소프트웨어팀",
            "cheongmyung.lee@knknara.co.kr": "가공팀",
            "chkcsd@knknara.co.kr": "총괄",  # 최홍광 전무 — 00 총괄 (대표 지시 2026-05-19 갱신)
            "chunghee.lee@knknara.co.kr": "소프트웨어팀",
            "chungil71@knknara.co.kr": "제조기술1팀",
            "daeseong.kang@knknara.co.kr": "제조기술2팀",
            "dhkimman@knknara.co.kr": "총괄",
            "donghyun.kim@knknara.co.kr": "설계팀(자동화)",
            "dongwook.kim@knknara.co.kr": "소프트웨어팀",
            "giwoon.kim@knknara.co.kr": "소프트웨어팀",
            "hanbin@knknara.co.kr": "검사기팀",
            "hanjung.lee@knknara.co.kr": "소프트웨어팀",
            "hojae.an@knknara.co.kr": "설계팀(검사기)",
            "hyun.lee@knknara.co.kr": "기술영업팀",
            "hyungjin.jeong@knknara.co.kr": "품질팀",
            "hyungryul.kim@knknara.co.kr": "전장설계팀",
            "hyunkyu.choi@knknara.co.kr": "설계팀(자동화)",
            "jaekyeom.na@knknara.co.kr": "라이프밸류팀",
            "jaeun.han@knknara.co.kr": "설계팀(자동화)",
            "jihoon.kim@knknara.co.kr": "검사기팀",
            "jihyeon.park@knknara.co.kr": "제조기술2팀",
            "jinho.joo@knknara.co.kr": "소프트웨어팀",
            "jinho.keum@knknara.co.kr": "제조기술1팀",
            "jks7434@knknara.co.kr": "검사기팀",
            "jongpil.hyeon@knknara.co.kr": "소프트웨어팀",
            "joochang.park@knknara.co.kr": "소프트웨어팀",
            "jun0130@knknara.co.kr": "설계팀(검사기)",
            "jungseok.hwang@knknara.co.kr": "소프트웨어팀",
            "jungwoo.lee@knknara.co.kr": "소프트웨어팀",
            "junyeob.shin@knknara.co.kr": "관리팀",
            "junyoung.ma@knknara.co.kr": "제조기술1팀",
            "khy9631@knknara.co.kr": "검사기팀",
            "kiseon.kim@knknara.co.kr": "라이프밸류팀",
            "kjr7749@knknara.co.kr": "품질팀",
            "knk1@knknara.co.kr": "관리팀",
            "knk2@knknara.co.kr": "관리팀",
            "knk3@knknara.co.kr": "관리팀",
            "knk4@knknara.co.kr": "관리팀",
            "kunghwan.oh@knknara.co.kr": "기술영업팀",
            "kwanghun.yoon@knknara.co.kr": "검사기팀",
            "kwangyoung.shin@knknara.co.kr": "설계팀(자동화)",
            "lhl2425@knknara.co.kr": "기술영업팀",
            "mingyu.jeong@knknara.co.kr": "설계팀(자동화)",
            "ngoclan.le@knknara.co.kr": "구매팀",
            "sales1@knknara.co.kr": "기술영업팀",
            "sangchon.lee@knknara.co.kr": "설계팀(자동화)",
            "sb8664@knknara.co.kr": "가공팀",
            "sejin.kim@knknara.co.kr": "가공팀",
            "seojoon.lee@knknara.co.kr": "검사기팀",
            "seungjin.bae@knknara.co.kr": "기술영업팀",
            "soft@knknara.co.kr": "개발혁신팀",
            "suhyeon.kim@knknara.co.kr": "개발혁신팀",
            "sungjin.jung@knknara.co.kr": "구매팀",
            "sungjin.lee@knknara.co.kr": "검사기팀",
            "sungki.bang@knknara.co.kr": "제조기술2팀",
            "sungsu.park@knknara.co.kr": "라이프밸류팀",
            "taehum.yeon@knknara.co.kr": "제조기술2팀",
            "taehyoung.kim@knknara.co.kr": "검사기팀",
            "taekhun.leem@knknara.co.kr": "제조기술2팀",
            "taewoo.lee@knknara.co.kr": "제조기술1팀",
            "top0015@knknara.co.kr": "총괄",
            "wangxia1019@knknara.co.kr": "제조기술2팀",
            "yoon5468@knknara.co.kr": "가공팀",
            "yoon5959@knknara.co.kr": "설계팀(자동화)",
            "younghoon.na@knknara.co.kr": "제조기술2팀",
            "youngjun.lee2@knknara.co.kr": "소프트웨어팀",
            "yslee@knknara.co.kr": "12-VN09 관리팀",
        }
        try:
            _ed_changed = 0
            for _email, _dept in EXCEL_DEPT_REMAP.items():
                if _dept is None:
                    _r = cur.execute(
                        "UPDATE users SET department=NULL WHERE LOWER(username)=? AND department IS NOT NULL",
                        (_email.lower(),)
                    )
                else:
                    # 대표이사 제외 가드 제거 — 총괄 배정이 대표이사에게 적용되어야 함
                    _r = cur.execute(
                        "UPDATE users SET department=? "
                        "WHERE LOWER(username)=? "
                        "  AND COALESCE(department,'') != ?",
                        (_dept, _email.lower(), _dept)
                    )
                if _r.rowcount > 0:
                    _ed_changed += 1
            _mark_migration("v4_excel_dept_remap")
            print(f"[migration] v4_excel_dept_remap 1회 실행 — {_ed_changed}명 UPDATE", flush=True)
        except Exception as _e:
            print(f"[migration] Excel 부서 정정 실패: {_e}", flush=True)
    # 첫 사용자(대표) 자동 기본값 — 빈 값일 때만
    # 대표이사(시드 id=1)는 직급만 부여. 부서는 비워둠 — 대표이사는 조직 위에 있어 부서 소속 X (대표 지시 2026-05-19).
    cur.execute("UPDATE users SET title='대표이사' WHERE id=1 AND (title IS NULL OR title='')")

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

    # 채널 소속 범위 (대표 지시 2026-05-20) — NULL(일반/사용자채널) | 'all'(KNK WORLD 전직원)
    # | 'hq'(본사) | 'vn'(베트남). 자동 생성·멤버 자동 동기화·나가기 금지 대상.
    if "channel_scope" not in existing_room_cols:
        cur.execute("ALTER TABLE rooms ADD COLUMN channel_scope TEXT")

    # 방/채널 아바타 이미지 URL — 관리자가 채널 아이콘에 사진 설정 (대표 지시 2026-05-20)
    if "avatar_url" not in existing_room_cols:
        cur.execute("ALTER TABLE rooms ADD COLUMN avatar_url TEXT")

    # created_by → host 자동 백필 — 1회성. 매번 부팅 시 실행되면
    # 사용자가 UI 에서 호스트를 강등한 경우 매번 복귀되는 버그 발생.
    if not _migration_applied("v2_room_host_backfill"):
        try:
            cur.execute("""
                UPDATE room_members
                   SET role = 'host'
                 WHERE role != 'host'
                   AND (room_id, user_id) IN (
                       SELECT id, created_by FROM rooms
                        WHERE created_by IS NOT NULL
                   )
            """)
            _mark_migration("v2_room_host_backfill")
        except Exception:
            pass

    # self 방 이름 '📝 메모' 통일 — 1회성 (옛 '📝 나에게 보내기' 갱신).
    # 매번 실행되면 사용자가 self 방 이름 바꿔도 매번 리셋되는 버그.
    if not _migration_applied("v2_self_room_rename"):
        try:
            cur.execute("UPDATE rooms SET name='📝 메모' WHERE type='self' AND name != '📝 메모'")
            _mark_migration("v2_self_room_rename")
        except Exception:
            pass

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
    # 마지막 읽은 시각 — 읽음 명단의 '언제 읽었는지' 표시용 (대표 지시 2026-05-19)
    if "last_read_at" not in existing_rm_cols:
        cur.execute("ALTER TABLE room_members ADD COLUMN last_read_at TEXT")
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

    # 시드 프로젝트 — 대표가 보여준 기존 대화방 4개 미러 (items 테이블 비어있으면 1회 주입)
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

    # 자동 채널(KNK WORLD/본사/베트남) 생성 + 전 직원 멤버십 동기화 + '전체공지' 삭제 (대표 지시 2026-05-20)
    try:
        _resync_auto_channels(conn)
    except Exception as e:
        print(f"[init_db] 자동채널 동기화 실패(무시): {e}", flush=True)

    # 최고관리자(소유자) 자동 보장 — OWNER_USERNAME 계정이 있으면 ceo·활성 강제 (대표 지시 2026-05-21)
    try:
        conn.execute("UPDATE users SET role='ceo' WHERE LOWER(username)=? AND role!='ceo'", (OWNER_USERNAME,))
        conn.execute("UPDATE users SET active=1 WHERE LOWER(username)=? AND COALESCE(active,1)!=1", (OWNER_USERNAME,))
        conn.commit()
    except Exception as e:
        print(f"[init_db] 최고관리자 보장 실패(무시): {e}", flush=True)

    conn.close()


# ===== 자동 채널 (KNK WORLD / 본사 / 베트남) — 대표 지시 2026-05-20 =====
# 부서값 '12-VN…' = 베트남, 그 외(또는 미지정) = 본사.
# 3개 채널은 자동 생성·멤버 자동 동기화·나가기 금지(channel_scope 로 식별).
AUTO_CHANNELS = [
    ("all", "🌏 KNK WORLD"),   # 아시아 지구 (대표 지시 2026-05-21)
    ("hq",  "🇰🇷 본사채널"),   # 본사 앞 이모지 태극기로 (대표 지시 2026-05-21)
    ("vn",  "🇻🇳 베트남채널"),
]


def _user_is_vietnam(department):
    """부서값이 '12-VN' 으로 시작하면 베트남법인 소속."""
    return bool(department) and str(department).strip().startswith("12-VN")


def _desired_scopes_for(department, active, is_owner=False):
    """이 사용자가 속해야 할 자동채널 scope 집합.
    최고관리자(소유자)는 본사·베트남 구분 없이 모든 채널 소속 (대표 지시 2026-05-21, 규칙 2)."""
    if not active:
        return set()
    if is_owner:
        return {"all", "hq", "vn"}
    return {"all", ("vn" if _user_is_vietnam(department) else "hq")}


def _auto_channel_ids(db):
    """scope -> room_id 매핑 (없으면 생성). + 레거시 '전체공지' 채널 제거."""
    now = datetime.now(timezone.utc).isoformat()
    # 레거시 '전체공지' 삭제 (대표 지시: 전체공지 삭제) — 메시지·멤버도 명시적 정리(FK 미적용 대비)
    try:
        for o in db.execute(
            "SELECT id FROM rooms WHERE type='channel' AND name='전체공지' AND channel_scope IS NULL"
        ).fetchall():
            rid = o["id"]
            db.execute("DELETE FROM messages WHERE room_id=?", (rid,))
            db.execute("DELETE FROM room_members WHERE room_id=?", (rid,))
            db.execute("DELETE FROM rooms WHERE id=?", (rid,))
    except Exception as e:
        print(f"[auto_channel] 전체공지 삭제 실패(무시): {e}")
    ids = {}
    for scope, cname in AUTO_CHANNELS:
        row = db.execute("SELECT id, name FROM rooms WHERE channel_scope=?", (scope,)).fetchone()
        if row:
            ids[scope] = row["id"]
            # 기존 채널 이름이 바뀐 경우(예: 본사 🏢→🇰🇷) 자동 동기화 (대표 지시 2026-05-21)
            if row["name"] != cname:
                db.execute("UPDATE rooms SET name=? WHERE id=?", (cname, row["id"]))
        else:
            cur = db.execute(
                "INSERT INTO rooms (name, type, created_by, created_at, name_locked, channel_scope) "
                "VALUES (?,?,?,?,?,?)",
                (cname, "channel", 1, now, 1, scope),
            )
            ids[scope] = cur.lastrowid
    return ids


def _sync_user_auto_channels(db, uid):
    """한 사용자의 자동채널 멤버십을 소속에 맞춰 추가/제거 (직원 등록·정보수정 후 호출)."""
    try:
        u = db.execute(
            "SELECT id, username, department, COALESCE(active,1) AS active FROM users WHERE id=?", (uid,)
        ).fetchone()
        if not u:
            return
        ids = _auto_channel_ids(db)
        want = _desired_scopes_for(u["department"], u["active"], _is_owner(u["username"]))
        now = datetime.now(timezone.utc).isoformat()
        for scope, rid in ids.items():
            if scope in want:
                db.execute(
                    "INSERT OR IGNORE INTO room_members (room_id, user_id, joined_at, role) VALUES (?,?,?,?)",
                    (rid, uid, now, "member"),
                )
            else:
                db.execute("DELETE FROM room_members WHERE room_id=? AND user_id=?", (rid, uid))
        db.commit()
    except Exception as e:
        print(f"[auto_channel] sync_user({uid}) 실패: {e}")


def _resync_auto_channels(db):
    """전 직원 자동채널 멤버십 일괄 동기화 (+ 채널 생성·전체공지 삭제). 부팅·일괄등록 시 호출."""
    ids = _auto_channel_ids(db)
    now = datetime.now(timezone.utc).isoformat()
    users = db.execute("SELECT id, username, department, COALESCE(active,1) AS active FROM users").fetchall()
    want = {rid: set() for rid in ids.values()}
    for u in users:
        for scope in _desired_scopes_for(u["department"], u["active"], _is_owner(u["username"])):
            want[ids[scope]].add(u["id"])
    for scope, rid in ids.items():
        have = set(r["user_id"] for r in db.execute(
            "SELECT user_id FROM room_members WHERE room_id=?", (rid,)
        ).fetchall())
        for uid in (want[rid] - have):
            db.execute(
                "INSERT OR IGNORE INTO room_members (room_id, user_id, joined_at, role) VALUES (?,?,?,?)",
                (rid, uid, now, "member"),
            )
        for uid in (have - want[rid]):
            db.execute("DELETE FROM room_members WHERE room_id=? AND user_id=?", (rid, uid))
    db.commit()


# ---------- Auth ----------
# ===== 동시 로그인 제한 (휴대폰 1대 + PC 1대) =====
_MOBILE_UA_RE = re.compile(r"Android|iPhone|iPad|iPod|IEMobile|Windows Phone|BlackBerry|Mobile|Mobi|Tablet", re.I)


def _device_type_from_ua(ua):
    """User-Agent 로 기기 종류 판별 — 휴대폰/태블릿은 'mobile', 그 외(PC)는 'pc'."""
    return "mobile" if (ua and _MOBILE_UA_RE.search(ua)) else "pc"


def _upsert_active_session(uid, dtype, token, ua):
    """(user_id, device_type) 활성 세션 등록/교체 — 같은 종류 옛 토큰을 덮어써 옛 기기를 무효화."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute("""
        INSERT INTO active_sessions (user_id, device_type, token, user_agent, ip, created_at)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(user_id, device_type) DO UPDATE SET
            token=excluded.token, user_agent=excluded.user_agent,
            ip=excluded.ip, created_at=excluded.created_at
    """, (uid, dtype, token, (ua or "")[:200], (request.remote_addr if request else None), now))
    db.commit()


def _session_token_valid(uid):
    """현재 세션이 (user, device_type) 활성 세션과 일치하는지.
    · 토큰 없는 기존 로그인(배포 전)은 자동 인정(grandfather) — 대량 강제 로그아웃 방지.
    · 같은 종류 기기에서 새로 로그인하면 토큰이 안 맞아 False (= 밀려남)."""
    try:
        tok = session.get("sess_token")
        dtype = session.get("device_type")
        ua = request.headers.get("User-Agent", "") if request else ""
        if not tok:
            # 배포 전 로그인 — 토큰 발급 + 등록(adopt)
            dtype = _device_type_from_ua(ua)
            tok = secrets.token_urlsafe(24)
            session["sess_token"] = tok
            session["device_type"] = dtype
            _upsert_active_session(uid, dtype, tok, ua)
            return True
        row = get_db().execute(
            "SELECT token FROM active_sessions WHERE user_id=? AND device_type=?",
            (uid, dtype or "pc"),
        ).fetchone()
        if row is None:
            # 활성행 없음 = 이 세션은 종료됨 (휴대폰 완전 로그아웃으로 삭제됐거나 다른 기기가 차지 후 로그아웃).
            # → 무효 처리해 다음 요청에서 로그인 화면으로. (토큰 없는 '기존 로그인'은 위 grandfather 에서 이미 처리)
            return False
        return row["token"] == tok
    except Exception as e:
        # 검증 중 오류가 나도 로그인은 막지 않음 (안전 측 default)
        print(f"[session] token 검증 오류: {e}")
        return True


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    user = get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    if not user:
        return None
    # 동시 로그인 제한 — 다른 같은종류 기기에서 로그인했으면 이 세션은 무효
    if not _session_token_valid(uid):
        return None
    return user


def login_required(view):
    @wraps(view)
    def wrapped(*a, **k):
        if not current_user():
            # user_id 는 있는데 current_user 가 None → 다른 기기 로그인으로 밀려남 (kicked)
            kicked = bool(session.get("user_id"))
            session.clear()
            if kicked:
                return redirect(url_for("login") + "?kicked=1")
            return redirect(url_for("login"))
        return view(*a, **k)
    return wrapped


def _force_logout_same_device_type(uid, dtype):
    """같은 종류 기기로 새 로그인 시, 기존 같은 종류 소켓에 즉시 force_logout 전송.
    밀려난 기기가 실시간으로 로그인 화면으로 빠지게 함 (HTTP 검증과 별개의 즉시 반영)."""
    try:
        sids = []
        with _user_conn_lock:
            for sid, info in _user_connections.get(uid, {}).items():
                if info.get("device") == dtype:
                    sids.append(sid)
        for sid in sids:
            try:
                socketio.emit("force_logout", {"reason": "다른 기기 로그인"}, to=sid)
            except Exception:
                pass
    except Exception as e:
        print(f"[session] force_logout emit 실패: {e}")


def _force_logout_all(uid):
    """이 사용자의 '모든' 소켓에 force_logout 전송 — 휴대폰 로그아웃 시 PC 등 전부 함께 로그아웃."""
    try:
        sids = []
        with _user_conn_lock:
            sids = list(_user_connections.get(uid, {}).keys())
        for sid in sids:
            try:
                socketio.emit("force_logout", {"reason": "휴대폰에서 로그아웃"}, to=sid)
            except Exception:
                pass
    except Exception as e:
        print(f"[session] force_logout_all emit 실패: {e}")


def _presence_offline_status(uid):
    """소켓이 모두 끊겼을 때 남에게 보여줄 상태 —
    푸시 구독이 남아있으면 'mobile'(📱 휴대폰), 없으면 'offline'(완전 오프라인)."""
    try:
        has_push = get_db().execute(
            "SELECT 1 FROM push_subscriptions WHERE user_id=? LIMIT 1", (uid,)
        ).fetchone()
        return "mobile" if has_push else "offline"
    except Exception:
        return "offline"


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
            # 동시 로그인 제한 — 기기 종류(폰/PC)별 토큰 발급 + 등록.
            # 같은 종류로 이미 로그인된 다른 기기는 이 토큰이 덮어써 자동 무효화(밀려남).
            try:
                ua = request.headers.get("User-Agent", "")
                dtype = _device_type_from_ua(ua)
                tok = secrets.token_urlsafe(24)
                session["sess_token"] = tok
                session["device_type"] = dtype
                _upsert_active_session(row["id"], dtype, tok, ua)
                # 같은 종류 기기로 이미 접속 중이던 기기는 즉시 force_logout (실시간 밀어내기)
                _force_logout_same_device_type(row["id"], dtype)
            except Exception as e:
                print(f"[login] active_session 등록 실패: {e}")
            return redirect(url_for("chat") + f"?v={STATIC_VERSION}&t={int(_time.time())}")
        return render_template("login.html", error="아이디 또는 비밀번호가 올바르지 않습니다.")
    # GET — 강제 로그아웃(밀려남/휴대폰 완전로그아웃) 안내
    kicked_msg = None
    if request.args.get("kicked"):
        r = request.args.get("r") or ""
        if "휴대폰" in r:
            kicked_msg = "휴대폰에서 로그아웃하여 이 PC도 함께 로그아웃되었습니다."
        else:
            kicked_msg = "다른 기기에서 로그인되어 이 기기는 로그아웃되었습니다. (동시 사용은 휴대폰 1대 + PC 1대까지)"
    return render_template("login.html", notice=kicked_msg)


@app.route("/logout")
def logout():
    # 비대칭 로그아웃 (대표 지시 2026-05-20):
    #  · 휴대폰 로그아웃 = '완전 로그아웃' — 폰+PC 전부 로그아웃 + 모든 푸시 삭제 → 완전 오프라인.
    #  · PC 로그아웃     = '이 PC 만'   — PC 세션·PC 푸시만 정리. 휴대폰은 세션·알림 그대로.
    uid = session.get("user_id")
    dtype = session.get("device_type") or "pc"
    tok = session.get("sess_token")
    ep = session.get("push_endpoint")
    if uid:
        try:
            db = get_db()
            if dtype == "mobile":
                # 휴대폰 = 모든 기기 완전 로그아웃
                db.execute("DELETE FROM push_subscriptions WHERE user_id=?", (uid,))
                db.execute("DELETE FROM active_sessions WHERE user_id=?", (uid,))
                db.commit()
                _force_logout_all(uid)               # PC 등 다른 기기 즉시 로그아웃
                try:
                    _last_status_bcast[uid] = "offline"   # disconnect 중복 emit 방지
                    socketio.emit("user_status_changed", {
                        "user_id": uid, "status": "offline",
                        "custom_text": None, "emoji": None,
                        "label": STATUS_LABEL_KO.get("offline", "오프라인"),
                    })
                except Exception:
                    pass
            else:
                # PC = 이 기기만 — 휴대폰에 영향 없음
                #  · 이 PC 의 푸시 구독만 삭제 (세션에 기록된 endpoint, 없으면 클라이언트 sendBeacon 이 처리)
                if ep:
                    db.execute("DELETE FROM push_subscriptions WHERE user_id=? AND endpoint=?", (uid, ep))
                if tok:
                    db.execute("DELETE FROM active_sessions WHERE user_id=? AND token=?", (uid, tok))
                db.commit()
                # 상태 broadcast 는 소켓 disconnect 핸들러가 '휴대폰/오프라인' 정확히 계산해 처리
        except Exception as e:
            print(f"[logout] cleanup 실패: {e}")
    session.clear()
    return redirect(url_for("login"))


@app.route("/logout_local")
def logout_local():
    """'이 기기만' 로그아웃 — 다른 기기 로그인으로 밀려난 기기 전용.
    푸시 구독은 건드리지 않음(계정의 다른 기기 알림을 끄면 안 되므로). 세션만 정리."""
    uid = session.get("user_id")
    tok = session.get("sess_token")
    if uid and tok:
        try:
            db = get_db()
            # 내 토큰의 활성세션 행만 제거 — 이미 새 기기가 덮어썼으면 불일치로 아무것도 안 지워짐(안전)
            db.execute("DELETE FROM active_sessions WHERE user_id=? AND token=?", (uid, tok))
            db.commit()
        except Exception:
            pass
    session.clear()
    return redirect(url_for("login", kicked=1, r=(request.args.get("r") or "")))


@app.route("/chat")
@login_required
def chat():
    # 첫 접속 시 '나에게 보내기' 1인방 자동 보장 — 학습비용 0 으로 즉시 사용 가능.
    try:
        _ensure_self_room(session["user_id"])
    except Exception as e:
        print(f"[chat] self_room 보장 실패: {e}")
    _me = current_user()
    return render_template("chat.html", me=_me, me_is_owner=_is_owner(_me["username"]), me_is_team_lead=_is_team_lead(_me))


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
        "description": "KNK 사내 업무 전용 메신저 — 프로젝트별 자동 정리·요청 추적·전사 검색",
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
        "is_owner": _is_owner(u["username"]),
        "is_team_lead": _is_team_lead(u),
    })


@app.route("/api/users")
@login_required
def api_users():
    """전체 사용자 목록 — 사이드바 '👥 사용자' 탭, 멤버 초대, 멘션 자동완성 등에서 공통 사용.
    직급(title)·부서(department) 포함. 비활성(퇴사) 사용자는 active=0 으로 필터링 가능."""
    me = current_user()
    me_is_ceo = (me["role"] == "ceo") if me else False
    rows = get_db().execute(
        "SELECT id, username, display_name, role, avatar_color, avatar_url, title, department, email, phone, employee_no, active "
        "FROM users "
        "WHERE username != '_deleted_user' "   # 시스템 플레이스홀더는 디렉터리 응답에서 제외 (대표 지시 2026-05-20)
        "ORDER BY "
        " CASE WHEN department IS NULL OR department='' THEN 1 ELSE 0 END, "
        " department ASC, "
        " CASE role WHEN 'ceo' THEN 0 ELSE 1 END, "
        " display_name ASC"
    ).fetchall()
    # 보안: role(권한) 은 본인 자신 또는 관리자만 볼 수 있게.
    # 다른 일반 사용자에게는 role 필드를 응답에서 제거 (F12 네트워크 탭으로도 못 보게).
    out = []
    for r in rows:
        d = dict(r)
        d["is_owner"] = _is_owner(d.get("username"))   # 최고관리자(소유자) 여부
        if not me_is_ceo and d["id"] != (me["id"] if me else None):
            d.pop("role", None)
            d.pop("is_owner", None)
        out.append(d)
    return jsonify(out)


@app.route("/api/users/<int:user_id>", methods=["PATCH"])
@login_required
def api_user_patch(user_id):
    """사용자 정보 수정 — 본인은 직급·부서 본인 것 수정 가능, 대표(ceo)는 모든 사람 수정 가능.
    body: {title?, department?, display_name?, avatar_color?}"""
    me = current_user()
    if me["id"] != user_id and me["role"] != "ceo":
        return jsonify({"error": "본인 또는 관리자만 수정 가능"}), 403
    data = request.get_json(silent=True) or {}
    fields = {}
    if "title" in data:
        v = (data.get("title") or "").strip()[:40]
        fields["title"] = v or None
    if "department" in data:
        v = (data.get("department") or "").strip()[:40]
        fields["department"] = v or None
    if "email" in data:
        v = (data.get("email") or "").strip()[:100]
        # 비어있어도 OK (지우기). 값 있으면 최소 @ 포함 검증
        if v and "@" not in v:
            return jsonify({"error": "이메일 형식이 올바르지 않습니다 (@ 누락)"}), 400
        fields["email"] = v or None
    if "phone" in data:
        v = (data.get("phone") or "").strip()[:30]
        fields["phone"] = v or None
    if "employee_no" in data:
        v = (data.get("employee_no") or "").strip()[:30]
        fields["employee_no"] = v or None
    # display_name·avatar_color·role·active 는 관리자만 수정 가능
    if me["role"] == "ceo":
        # 최고관리자(소유자) 보호 — 강등·비활성 차단 (대표 지시 2026-05-21)
        _tgt = get_db().execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()
        _target_is_owner = _tgt and _is_owner(_tgt["username"])
        if "display_name" in data:
            v = (data.get("display_name") or "").strip()[:40]
            if v:
                fields["display_name"] = v
        if "avatar_color" in data:
            v = (data.get("avatar_color") or "").strip()
            if v and len(v) <= 16:
                fields["avatar_color"] = v
        if "active" in data:
            if _target_is_owner and not data.get("active"):
                return jsonify({"error": "최고관리자 계정은 비활성화할 수 없습니다."}), 400
            fields["active"] = 1 if data.get("active") else 0
        if "role" in data:
            # 관리자 선정·해지는 최고관리자(소유자)만 가능 (대표 지시 2026-05-21, 규칙 1)
            if not _is_owner(me["username"]):
                return jsonify({"error": "관리자 선정·해지는 최고관리자만 할 수 있습니다."}), 403
            new_role = (data.get("role") or "").strip().lower()
            if new_role not in ("ceo", "staff"):
                return jsonify({"error": "role 은 'ceo' 또는 'staff' 만 가능"}), 400
            if _target_is_owner and new_role != "ceo":
                return jsonify({"error": "최고관리자 계정은 강등할 수 없습니다."}), 400
            # 안전장치: 마지막 관리자가 자기 자신을 강등하려는 경우 차단
            if user_id == me["id"] and new_role == "staff":
                db_pre = get_db()
                ceo_count = db_pre.execute("SELECT COUNT(*) AS n FROM users WHERE role='ceo' AND active=1").fetchone()["n"]
                if ceo_count <= 1:
                    return jsonify({"error": "마지막 관리자는 본인을 강등할 수 없습니다. 다른 사람을 먼저 관리자로 임명한 뒤 강등하세요."}), 400
            fields["role"] = new_role
    if not fields:
        return jsonify({"error": "변경할 필드가 없습니다"}), 400
    db = get_db()
    cols = ", ".join(f"{k} = ?" for k in fields.keys())
    args = list(fields.values()) + [user_id]
    db.execute(f"UPDATE users SET {cols} WHERE id = ?", args)
    db.commit()
    # 부서·활성 변경 시 자동채널(KNK WORLD/본사/베트남) 멤버십 재동기화 (대표 지시 2026-05-20)
    if ("department" in fields) or ("active" in fields):
        try: _sync_user_auto_channels(db, user_id)
        except Exception as e: print(f"[auto_channel] patch sync 실패: {e}")
    row = db.execute(
        "SELECT id, username, display_name, role, avatar_color, avatar_url, title, department, email, phone, employee_no, active FROM users WHERE id=?",
        (user_id,),
    ).fetchone()
    # 실시간 알림 — 다른 클라이언트도 사용자 정보 즉시 갱신
    socketio.emit("user_info_changed", dict(row))
    return jsonify({"ok": True, "user": dict(row)})


# ============================================================
# 📷 아바타 사진 업로드 (대표 지시 2026-05-19)
#   본인 또는 관리자만 업로드 가능. jpg/png/webp/gif, 5MB 이하.
#   저장: data/uploads/avatars/<user_id>.<ext>  (한 사용자 1장)
#   URL: BASE_PATH + /uploads/avatars/<user_id>.<ext>?v=<ts>  (캐시 무력화용 timestamp)
# ============================================================
AVATAR_DIR = os.path.join(UPLOAD_DIR, "avatars")
os.makedirs(AVATAR_DIR, exist_ok=True)
AVATAR_ALLOWED_EXT = {"jpg", "jpeg", "png", "webp", "gif"}
AVATAR_MAX_BYTES = 5 * 1024 * 1024  # 5MB
# 방/채널 아바타 이미지 (관리자가 채널 아이콘에 사진 설정) — data/uploads/room_avatars/<room_id>.<ext>
ROOM_AVATAR_DIR = os.path.join(UPLOAD_DIR, "room_avatars")
os.makedirs(ROOM_AVATAR_DIR, exist_ok=True)

@app.route("/api/users/<int:user_id>/avatar", methods=["POST"])
@login_required
def api_user_avatar_upload(user_id):
    """아바타 사진 업로드 — multipart/form-data 의 'file' 필드.
    권한: 본인 또는 관리자(ceo).
    반환: {ok: True, avatar_url: '...?v=12345'}"""
    me = current_user()
    if me["id"] != user_id and me["role"] != "ceo":
        return jsonify({"error": "본인 또는 관리자만 업로드 가능"}), 403
    if "file" not in request.files:
        return jsonify({"error": "file 필드에 이미지 첨부 필요"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "파일명 누락"}), 400
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in AVATAR_ALLOWED_EXT:
        return jsonify({"error": f"지원 형식: {', '.join(AVATAR_ALLOWED_EXT)}"}), 400
    # 크기 체크 — content_length 신뢰 안 되면 stream 으로 측정
    data = f.read()
    if len(data) > AVATAR_MAX_BYTES:
        return jsonify({"error": f"파일이 너무 큽니다 ({len(data)//1024}KB > {AVATAR_MAX_BYTES//1024//1024}MB)"}), 400
    if len(data) < 100:
        return jsonify({"error": "파일이 너무 작거나 손상되었습니다"}), 400
    # 기존 파일 (다른 확장자) 삭제
    for old_ext in AVATAR_ALLOWED_EXT:
        old_path = os.path.join(AVATAR_DIR, f"{user_id}.{old_ext}")
        if os.path.exists(old_path):
            try: os.remove(old_path)
            except Exception: pass
    # 저장
    save_path = os.path.join(AVATAR_DIR, f"{user_id}.{ext}")
    with open(save_path, "wb") as out:
        out.write(data)
    # DB 갱신 (캐시 무력화용 timestamp 쿼리)
    import time as _t
    ts = int(_t.time())
    rel_url = f"{BASE_PATH}/uploads/avatars/{user_id}.{ext}?v={ts}"
    db = get_db()
    db.execute("UPDATE users SET avatar_url=? WHERE id=?", (rel_url, user_id))
    db.commit()
    # 실시간 broadcast
    row = db.execute(
        "SELECT id, username, display_name, role, avatar_color, avatar_url, title, department, email, phone, employee_no, active FROM users WHERE id=?",
        (user_id,),
    ).fetchone()
    socketio.emit("user_info_changed", dict(row))
    return jsonify({"ok": True, "avatar_url": rel_url})


@app.route("/api/users/<int:user_id>/avatar", methods=["DELETE"])
@login_required
def api_user_avatar_delete(user_id):
    """아바타 사진 제거 — 본인 또는 관리자."""
    me = current_user()
    if me["id"] != user_id and me["role"] != "ceo":
        return jsonify({"error": "본인 또는 관리자만 삭제 가능"}), 403
    for ext in AVATAR_ALLOWED_EXT:
        p = os.path.join(AVATAR_DIR, f"{user_id}.{ext}")
        if os.path.exists(p):
            try: os.remove(p)
            except Exception: pass
    db = get_db()
    db.execute("UPDATE users SET avatar_url=NULL WHERE id=?", (user_id,))
    db.commit()
    row = db.execute(
        "SELECT id, username, display_name, role, avatar_color, avatar_url, title, department, email, phone, employee_no, active FROM users WHERE id=?",
        (user_id,),
    ).fetchone()
    socketio.emit("user_info_changed", dict(row))
    return jsonify({"ok": True})


@app.route("/uploads/avatars/<path:filename>")
def serve_avatar(filename):
    """업로드된 아바타 이미지 서빙."""
    return send_from_directory(AVATAR_DIR, filename)


@app.route("/uploads/room_avatars/<path:filename>")
def serve_room_avatar(filename):
    """업로드된 방/채널 아바타 이미지 서빙."""
    return send_from_directory(ROOM_AVATAR_DIR, filename)


@app.route("/api/rooms/<int:room_id>/avatar", methods=["POST"])
@login_required
def api_room_avatar_upload(room_id):
    """채널/방 아바타 이미지 업로드 — 관리자(ceo) 전용. (대표 지시 2026-05-20)"""
    me = current_user()
    if me["role"] != "ceo":
        return jsonify({"error": "관리자만 채널 아이콘을 설정할 수 있습니다."}), 403
    db = get_db()
    room = db.execute("SELECT id FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not room:
        return jsonify({"error": "방이 없습니다."}), 404
    if "file" not in request.files:
        return jsonify({"error": "file 필드에 이미지 첨부 필요"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "파일명 누락"}), 400
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in AVATAR_ALLOWED_EXT:
        return jsonify({"error": f"지원 형식: {', '.join(AVATAR_ALLOWED_EXT)}"}), 400
    data = f.read()
    if len(data) > AVATAR_MAX_BYTES:
        return jsonify({"error": f"파일이 너무 큽니다 ({len(data)//1024}KB > {AVATAR_MAX_BYTES//1024//1024}MB)"}), 400
    if len(data) < 100:
        return jsonify({"error": "파일이 너무 작거나 손상되었습니다"}), 400
    for old_ext in AVATAR_ALLOWED_EXT:
        op = os.path.join(ROOM_AVATAR_DIR, f"{room_id}.{old_ext}")
        if os.path.exists(op):
            try: os.remove(op)
            except Exception: pass
    with open(os.path.join(ROOM_AVATAR_DIR, f"{room_id}.{ext}"), "wb") as out:
        out.write(data)
    import time as _t
    rel_url = f"{BASE_PATH}/uploads/room_avatars/{room_id}.{ext}?v={int(_t.time())}"
    db.execute("UPDATE rooms SET avatar_url=? WHERE id=?", (rel_url, room_id))
    db.commit()
    try:
        _emit_room_event(room_id, "room_avatar_changed", {"room_id": room_id, "avatar_url": rel_url})
    except Exception:
        pass
    return jsonify({"ok": True, "avatar_url": rel_url})


@app.route("/api/rooms/<int:room_id>/avatar", methods=["DELETE"])
@login_required
def api_room_avatar_delete(room_id):
    """채널/방 아바타 이미지 제거 — 관리자(ceo) 전용."""
    me = current_user()
    if me["role"] != "ceo":
        return jsonify({"error": "관리자만 가능"}), 403
    for ext in AVATAR_ALLOWED_EXT:
        p = os.path.join(ROOM_AVATAR_DIR, f"{room_id}.{ext}")
        if os.path.exists(p):
            try: os.remove(p)
            except Exception: pass
    db = get_db()
    db.execute("UPDATE rooms SET avatar_url=NULL WHERE id=?", (room_id,))
    db.commit()
    try:
        _emit_room_event(room_id, "room_avatar_changed", {"room_id": room_id, "avatar_url": None})
    except Exception:
        pass
    return jsonify({"ok": True})


@app.route("/api/rooms/direct/<int:other_user_id>", methods=["POST"])
@login_required
def api_rooms_direct_open(other_user_id):
    """1:1 채팅방 열기 — 이미 있으면 그 방, 없으면 새로 생성.
    사이드바 '👥 사용자' 탭에서 사람 클릭 시 호출됨."""
    me = current_user()
    if other_user_id == me["id"]:
        return jsonify({"error": "본인과는 1:1 채팅 불가 — 📝 메모 사용"}), 400
    db = get_db()
    other = db.execute("SELECT id, active FROM users WHERE id=?", (other_user_id,)).fetchone()
    if not other:
        return jsonify({"error": "사용자 없음"}), 404
    if not other["active"]:
        return jsonify({"error": "비활성 사용자"}), 400
    # 기존 1:1 방 찾기 (양쪽이 모두 멤버이며 다른 멤버가 없는 direct 방)
    existing = db.execute("""
        SELECT r.id FROM rooms r
          JOIN room_members rm1 ON rm1.room_id=r.id AND rm1.user_id=?
          JOIN room_members rm2 ON rm2.room_id=r.id AND rm2.user_id=?
         WHERE r.type='direct'
         LIMIT 1
    """, (me["id"], other_user_id)).fetchone()
    if existing:
        return jsonify({"room_id": existing["id"], "existing": True})
    # 신규 생성
    now = datetime.now(timezone.utc).isoformat()
    cur = db.execute(
        "INSERT INTO rooms (name, type, created_by, created_at, name_locked) VALUES (?,?,?,?,1)",
        ("", "direct", me["id"], now),
    )
    rid = cur.lastrowid
    for uid in (me["id"], other_user_id):
        role = "host" if uid == me["id"] else "member"
        db.execute(
            "INSERT INTO room_members (room_id, user_id, joined_at, role) VALUES (?,?,?,?)",
            (rid, uid, now, role),
        )
    db.commit()
    return jsonify({"room_id": rid, "existing": False})


@app.route("/api/rooms")
@login_required
def api_rooms():
    me = current_user()
    db = get_db()
    # 귓속말 필터 — 본인이 송신자/수신자가 아닌 귓속말은 last_message·unread 에서 모두 제외.
    # 다른 사람 사이드바·푸시·미열람 카운트에 안 보이게 (귓속말은 진짜 둘만 보이게).
    rows = db.execute("""
        SELECT r.id, r.name, r.type, r.created_at, r.name_locked, r.created_by,
               r.retention_days, r.invite_policy, r.channel_scope, r.avatar_url,
               rm.role AS my_role,
               rm.pinned, rm.order_value,
               (SELECT alias FROM room_aliases WHERE room_id=r.id AND user_id=?) AS my_alias,
               it.code AS item_code, it.customer AS item_customer,
               it.status AS item_status, it.due_date AS item_due,
               (SELECT content FROM messages
                  WHERE room_id = r.id
                    AND (whisper_to_user_id IS NULL OR whisper_to_user_id = ? OR user_id = ?)
                    AND (r.type != 'self' OR COALESCE(kind,'text') NOT IN ('system','deleted'))
                  ORDER BY id DESC LIMIT 1) AS last_message,
               (SELECT created_at FROM messages
                  WHERE room_id = r.id
                    AND (whisper_to_user_id IS NULL OR whisper_to_user_id = ? OR user_id = ?)
                    AND (r.type != 'self' OR COALESCE(kind,'text') NOT IN ('system','deleted'))
                  ORDER BY id DESC LIMIT 1) AS last_at,
               (SELECT COUNT(*) FROM messages m
                  WHERE m.room_id = r.id
                    AND m.id > rm.last_read_message_id
                    AND m.user_id != ?
                    AND (m.whisper_to_user_id IS NULL OR m.whisper_to_user_id = ?)
               ) AS unread
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
    """, (
        me["id"],                       # my_alias
        me["id"], me["id"],             # last_message whisper filter (whisper_to_user_id=me OR user_id=me)
        me["id"], me["id"],             # last_at whisper filter
        me["id"], me["id"],             # unread: user_id != me AND (whisper IS NULL OR whisper=me)
        me["id"],                       # rm.user_id = me
    )).fetchall()

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
            # 그룹/프로젝트 방: name_locked=0 이고 내 별명 있으면 별명 우선
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
        return jsonify({"error": "프로젝트 이름은 필수입니다."}), 400
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
    # 프로젝트 방은 이름 고정 (방장만 변경 가능)
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
        (rid, me["id"], f"프로젝트 [{name}] 생성됨", "system", now),
    )
    db.commit()
    return jsonify({"room_id": rid, "name": name})


@app.route("/api/items/lookup", methods=["GET"])
@login_required
def api_items_lookup():
    """관리번호(관리번호) 자동완성 — 기존 등록된 프로젝트에서 동일·유사 코드 조회.

    Query string:
        code  : 검색 문자열 (전방·중간 부분 일치)
        limit : 최대 반환 건수 (기본 10, 상한 30)

    응답:
        [{code, customer, name, status, due_date, room_id, created_at, source: 'local'}]
        - code 별로 가장 최근(created_at MAX) 1건만 반환 (DISTINCT)
        - 정렬: 정확 일치 > 전방 일치 > 부분 일치, 동률은 최신 우선

    향후: HAIST WORKS 시스템 연동 시 'source' 필드 분기 사용 가능
        (예: source='haist_works' / 'local')
    """
    q = (request.args.get("code") or "").strip()
    try:
        limit = int(request.args.get("limit", 10))
    except (ValueError, TypeError):
        limit = 10
    limit = max(1, min(limit, 30))
    if not q or len(q) < 1:
        return jsonify([])
    db = get_db()
    # SQLite — case-insensitive LIKE (ASCII). 한글은 대소문자 영향 없음.
    like = f"%{q}%"
    # 같은 code 가 여러 번 등록됐을 때 최신 1건만 반환 (서브쿼리 GROUP BY).
    rows = db.execute("""
        SELECT it.id, it.room_id, it.code, it.customer, it.name,
               it.status, it.due_date, it.created_at
          FROM items it
         INNER JOIN (
             SELECT code, MAX(created_at) AS max_ts
               FROM items
              WHERE code IS NOT NULL AND code != '' AND code LIKE ?
              GROUP BY code
         ) latest
            ON it.code = latest.code AND it.created_at = latest.max_ts
         ORDER BY
             CASE WHEN LOWER(it.code) = LOWER(?) THEN 0
                  WHEN LOWER(it.code) LIKE LOWER(?) THEN 1
                  ELSE 2
             END,
             it.created_at DESC
         LIMIT ?
    """, (like, q, f"{q}%", limit)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["source"] = "local"   # 향후 HAIST WORKS 연동 시 'haist_works' 등으로 분기
        out.append(d)
    return jsonify(out)


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
    # 메인 타임라인은 스레드 부모(parent_message_id IS NULL)만 표시.
    # 답글은 /api/messages/<id>/thread 로 별도 조회.
    # 귓속말 필터: whisper_to_user_id 가 NULL(공개) 이거나 송신자/수신자가 본인일 때만.
    rows = db.execute("""
        SELECT m.id, m.content, m.kind, m.created_at,
               m.file_path, m.file_name, m.file_size, m.file_mime,
               m.parent_message_id AS thread_parent_id,
               m.quoted_message_id,
               m.forwarded_from_message_id, m.forwarded_from_user_id,
               m.forwarded_from_name, m.forwarded_from_room_name, m.forwarded_from_created_at,
               m.whisper_to_user_id,
               m.album_id,
               u.id AS user_id, u.display_name, u.avatar_color
          FROM messages m
          JOIN users u ON u.id = m.user_id
         WHERE m.room_id = ?
           AND m.parent_message_id IS NULL
           AND (m.whisper_to_user_id IS NULL
                OR m.whisper_to_user_id = ?
                OR m.user_id = ?)
         ORDER BY m.id ASC
    """, (room_id, me["id"], me["id"])).fetchall()
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

        # 귓속말 수신자 표시명 batch 로드
        whisper_ids = [r["whisper_to_user_id"] for r in out if r.get("whisper_to_user_id")]
        whisper_name_map = {}
        if whisper_ids:
            wph = ",".join("?" for _ in whisper_ids)
            wnrows = db.execute(
                f"SELECT id, display_name FROM users WHERE id IN ({wph})",
                whisper_ids,
            ).fetchall()
            whisper_name_map = {r["id"]: r["display_name"] for r in wnrows}
        for r in out:
            wid = r.get("whisper_to_user_id")
            if wid:
                r["whisper_to_name"] = whisper_name_map.get(wid)

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
    """전달(Forward) — 출처 보존.
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
        # 텍스트 메시지의 경우 본문은 원본 텍스트를 그대로 옮김.
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
    """스레드 답글 목록 + 부모 메시지. 사이드 패널 데이터.
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
    """전달확인 — '내가 봤고 처리하겠다' 명시. 단순 '읽음' 보다 강한 의지 표시.

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
@app.route("/api/messages/<int:message_id>/read_status", methods=["GET"])
@login_required
def api_message_read_status(message_id):
    """메시지를 읽은 사람·안 읽은 사람 명단 (대표 지시 2026-05-19).

    동작:
        - 방 멤버 전체 조회
        - 각 멤버의 last_read_message_id 와 비교
        - last_read >= message_id → 읽음
        - 그 미만 → 안 읽음
        - 발신자 본인은 명단에서 제외 (본인은 항상 본 거니까)

    응답:
        {
          message_id,
          read: [{user_id, display_name, avatar_color, avatar_url, last_read_at}],
          unread: [{user_id, display_name, avatar_color, avatar_url}],
          read_count, unread_count, total_members
        }
    """
    me = current_user()
    db = get_db()
    msg = db.execute(
        "SELECT id, room_id, user_id, created_at FROM messages WHERE id=?", (message_id,)
    ).fetchone()
    if not msg:
        return jsonify({"error": "메시지를 찾을 수 없습니다"}), 404
    # 방 멤버인지 확인
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
        (msg["room_id"], me["id"])
    ).fetchone():
        return jsonify({"error": "이 방 멤버만 조회 가능"}), 403
    # 방 멤버 전원 조회 (발신자 제외)
    rows = db.execute("""
        SELECT u.id, u.display_name, u.avatar_color, u.avatar_url,
               rm.last_read_message_id, rm.last_read_at
          FROM room_members rm
          JOIN users u ON u.id = rm.user_id
         WHERE rm.room_id = ? AND u.id != ? AND u.active = 1
         ORDER BY u.display_name
    """, (msg["room_id"], msg["user_id"])).fetchall()
    read = []
    unread = []
    for r in rows:
        d = {
            "user_id": r["id"],
            "display_name": r["display_name"],
            "avatar_color": r["avatar_color"],
            "avatar_url": r["avatar_url"],
        }
        last_read = r["last_read_message_id"] or 0
        if last_read >= message_id:
            d["last_read_at"] = r["last_read_at"]
            read.append(d)
        else:
            unread.append(d)
    return jsonify({
        "message_id": message_id,
        "sender_user_id": msg["user_id"],
        "read": read,
        "unread": unread,
        "read_count": len(read),
        "unread_count": len(unread),
        "total_members": len(read) + len(unread),
    })


@app.route("/api/messages/<int:message_id>", methods=["PATCH"])
@login_required
def api_message_edit(message_id):
    """메시지 편집 — 본인 텍스트 메시지만 (대표 지시 2026-05-19).

    body: {content: '새 내용'}
    제약:
        - 본인 메시지만 (관리자도 X — 보안)
        - 텍스트 메시지만 (kind='text' 또는 NULL)
        - 삭제된 메시지(kind='deleted')는 편집 불가
        - 시스템 메시지(kind='system')는 편집 불가
        - content 길이 1~4000자
    동작:
        - content 업데이트 + edited_at = 현재 시각
        - 검색 인덱스(FTS) 자동 동기화 (trigger)
        - socketio 'message_edited' broadcast → 다른 사용자 화면 즉시 갱신
    """
    me = current_user()
    db = get_db()
    msg = db.execute(
        "SELECT id, room_id, user_id, kind FROM messages WHERE id = ?",
        (message_id,)
    ).fetchone()
    if not msg:
        return jsonify({"error": "메시지를 찾을 수 없습니다"}), 404
    # 권한 — 본인만
    if msg["user_id"] != me["id"]:
        return jsonify({"error": "본인 메시지만 편집 가능"}), 403
    # 종류 제약
    if msg["kind"] == "deleted":
        return jsonify({"error": "삭제된 메시지는 편집 불가"}), 400
    if msg["kind"] in ("image", "file", "system", "sticker"):
        return jsonify({"error": "사진·파일·스티커·시스템 메시지는 편집 불가"}), 400
    data = request.get_json(silent=True) or {}
    new_content = (data.get("content") or "").strip()
    if not new_content:
        return jsonify({"error": "내용이 비어 있습니다"}), 400
    if len(new_content) > 4000:
        new_content = new_content[:4000]
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "UPDATE messages SET content = ?, edited_at = ? WHERE id = ?",
        (new_content, now, message_id)
    )
    db.commit()
    # broadcast
    try:
        socketio.emit("message_edited", {
            "message_id": message_id,
            "room_id": msg["room_id"],
            "content": new_content,
            "edited_at": now,
        }, to=f"room_{msg['room_id']}")
    except Exception as e:
        print(f"[message edit] socketio emit 실패: {e}", flush=True)
    return jsonify({"ok": True, "message_id": message_id, "content": new_content, "edited_at": now})


@app.route("/api/messages/<int:message_id>", methods=["DELETE"])
@login_required
def api_message_delete(message_id):
    """메시지 삭제 (대표 지시 2026-05-19).

    권한:
        - 본인 메시지: 언제든 삭제 가능
        - 관리자(ceo): 누구 메시지든 삭제 가능 (보안·법무 대응)
        - 그 외: 403

    동작 (soft delete):
        - content → '🗑️ 삭제된 메시지'
        - kind → 'deleted'
        - 첨부 파일이 있으면 디스크에서도 제거
        - 인용·답글·전달 메타데이터 NULL 화 (혼란 방지)
        - socketio 'message_deleted' broadcast → 모든 방 멤버 화면 즉시 갱신

    record 자체는 보존 (이력 추적·읽음 카운트·인덱스 일관성)."""
    me = current_user()
    db = get_db()
    msg = db.execute(
        "SELECT id, room_id, user_id, kind, file_path FROM messages WHERE id = ?",
        (message_id,)
    ).fetchone()
    if not msg:
        return jsonify({"error": "메시지를 찾을 수 없습니다"}), 404
    # 권한 체크 — 본인 또는 ceo
    if msg["user_id"] != me["id"] and me["role"] != "ceo":
        return jsonify({"error": "본인이 보낸 메시지만 삭제할 수 있습니다"}), 403
    # 이미 삭제된 메시지면 no-op
    if msg["kind"] == "deleted":
        return jsonify({"ok": True, "message": "이미 삭제됨"})
    # 첨부 파일 디스크에서 제거
    if msg["file_path"]:
        try:
            full_path = os.path.join(UPLOAD_DIR, msg["file_path"])
            if os.path.exists(full_path):
                os.remove(full_path)
        except Exception as e:
            print(f"[message delete] 파일 제거 실패: {e}", flush=True)
    # soft delete — content/kind 만 교체, record 보존
    now = datetime.now(timezone.utc).isoformat()
    db.execute("""
        UPDATE messages SET
            content = '🗑️ 삭제된 메시지',
            kind = 'deleted',
            file_path = NULL, file_name = NULL, file_size = NULL, file_mime = NULL,
            quoted_message_id = NULL,
            forwarded_from_message_id = NULL, forwarded_from_user_id = NULL,
            forwarded_from_name = NULL, forwarded_from_room_name = NULL, forwarded_from_created_at = NULL,
            album_id = NULL
        WHERE id = ?
    """, (message_id,))
    db.commit()
    # 실시간 broadcast — 모든 방 멤버에게 알림
    try:
        socketio.emit("message_deleted", {
            "message_id": message_id,
            "room_id": msg["room_id"],
            "deleted_by": me["id"],
            "deleted_at": now,
        }, to=f"room_{msg['room_id']}")
    except Exception as e:
        print(f"[message delete] socketio emit 실패: {e}", flush=True)
    return jsonify({"ok": True, "message_id": message_id})


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
# AI 보조 — 채널 일간 요약 / 긴 스레드 요약 / 작성 톤 조정.
# 한국어 1순위 — 한국어 특화로 차별화.
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
    """프로젝트(프로젝트 방) 이력용 요약 — HAIST WORKS 프로젝트 이력 포맷.
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
        if item_meta.get("name"): bits.append(f"프로젝트명 {item_meta['name']}")
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

        # 프로젝트 메타
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
    """모든 프로젝트 방에 대해 자동 이력 생성 (하루 1회 호출)."""
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
    """작성 톤 조정 (AI 작성 도움)."""
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
    """작성 톤 조정 (AI 작성 도움).
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
    # 프로젝트 방만 — 일반 방은 이력 비활성
    rtype = db.execute("SELECT type FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not rtype or rtype["type"] != "item":
        return jsonify({"error": "이력은 프로젝트 방에서만 생성 가능합니다"}), 400
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
      - 보내는 사람이 양국어 동시에 만들어 발송 (일반 메신저 번역의 한계 극복: 받은 사람만 번역되는 문제 X)
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

    # 🛡️ 보안 검사 1: 위험 확장자 + 이중 확장자 차단
    dangerous, why = _is_dangerous_filename(original)
    if dangerous:
        return jsonify({"error": f"보안 정책에 따라 차단됨: {why}"}), 400

    # 🛡️ 보안 검사 2: 화이트리스트 통과
    if ext and ext not in ALLOWED_FILE_EXT:
        return jsonify({"error": f"허용되지 않는 확장자(.{ext})"}), 400

    # 🛡️ 보안 검사 3: 실행 파일 magic number — 확장자 위조 차단
    is_exec, why = _check_executable_magic(f)
    if is_exec:
        return jsonify({"error": f"실행 파일은 업로드할 수 없습니다 — {why}"}), 400

    # 🛡️ 보안 검사 4: 단일 파일 크기 — Content-Length 사전 검사
    content_len = request.content_length or 0
    if content_len > PER_FILE_MAX_MB * 1024 * 1024:
        return jsonify({"error": f"파일이 너무 큽니다 (단일 {PER_FILE_MAX_MB}MB 초과)"}), 413

    # 🛡️ 보안 검사 5: 사용자별 분당 업로드 횟수 제한 (Rate Limit)
    # 사진 일괄 업로드 (30장) + 약간의 여유 = 60개/분 (대표 지시 2026-05-19)
    if not _check_rate_limit(me["id"], "upload", max_per_minute=60):
        return jsonify({"error": "업로드 속도 제한 — 잠시 후 다시 시도하세요 (1분에 60개)"}), 429

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

    # 앨범 묶음 ID (선택) — 클라이언트가 같은 album_id 로 N번 업로드 호출 → 그리드 1개 메시지로 렌더.
    # 사진(kind='image') 일 때만 의미가 있어 file 타입은 강제로 무시.
    album_id = (request.form.get("album_id") or "").strip() or None
    if album_id and kind != "image":
        album_id = None

    cur = db.execute("""
        INSERT INTO messages (room_id, user_id, content, kind, file_path, file_name, file_size, file_mime, album_id, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (room_id, me["id"], original, kind, rel_path, original, size, mime, album_id, now))
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
        "album_id": album_id,
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


@app.route("/api/albums/<album_id>/zip")
@login_required
def api_album_zip(album_id):
    """앨범(같은 album_id 의 image 메시지들)을 ZIP 으로 묶어 다운로드.
    권한: 해당 방의 멤버여야 한다.
    """
    import zipfile
    import io
    from flask import send_file as _send_file

    if not album_id or len(album_id) > 80:
        abort(400)
    me = current_user()
    db = get_db()
    rows = db.execute("""
        SELECT m.file_path, m.file_name, m.room_id, m.created_at
          FROM messages m
         WHERE m.album_id = ?
           AND m.kind = 'image'
           AND m.file_path IS NOT NULL
         ORDER BY m.id ASC
    """, (album_id,)).fetchall()
    if not rows:
        abort(404)
    room_id = rows[0]["room_id"]
    if not db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?", (room_id, me["id"])
    ).fetchone():
        abort(403)

    buf = io.BytesIO()
    used = set()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in rows:
            src = os.path.join(UPLOAD_DIR, r["file_path"])
            if not os.path.exists(src):
                continue
            name = r["file_name"] or os.path.basename(r["file_path"])
            # 동명 충돌 방지 — 사진명_1.jpg, _2.jpg 식
            arc = name
            n = 1
            while arc in used:
                stem, ext = os.path.splitext(name)
                arc = f"{stem}_{n}{ext}"
                n += 1
            used.add(arc)
            zf.write(src, arcname=arc)
    if not used:
        abort(404)
    buf.seek(0)

    short = (album_id or "album")[:8]
    zip_name = f"album_{short}.zip"
    return _send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=zip_name,
    )


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
    """방 요약 — 프로젝트 카드 헤더 / 다이제스트용 카운트"""
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
    """전체 프로젝트 대시보드 — 카운트·최근활동 한눈"""
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

    일반 메신저에서 묻혀서 못 보고 지나가는 일을 막기 위한 핵심 기능.
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
    """프로젝트 이력 Excel 내보내기 — 4시트(개요/메시지/요청/첨부).

    일반 메신저로 못 했던 기능: 프로젝트 단위로 모든 이력을 한 파일로.
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
    ws1["A1"] = "KNK 메신저 — 프로젝트 이력 보고서"
    ws1["A1"].font = Font(bold=True, size=14)
    ws1.merge_cells("A1:B1")
    rows1 = [
        ["내보내기 일시", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M (UTC)")],
        ["내보낸 사람", me["display_name"]],
        ["", ""],
        ["방 이름", room["name"] if room else ""],
        ["타입", {"item": "프로젝트", "channel": "채널", "group": "그룹채팅", "direct": "1:1"}.get(room["type"] if room else "", "")],
    ]
    if item:
        rows1.extend([
            ["고객사", item["customer"] or ""],
            ["관리번호", item["code"] or ""],
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
    """프로젝트 타임라인 — 날짜별로 사진·파일·요청·결정 그룹.

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
    # 이 기기(세션)의 push endpoint 기록 — PC 로그아웃 시 '이 PC 의 푸시만' 정확히 삭제하기 위함.
    try:
        session["push_endpoint"] = endpoint
    except Exception:
        pass
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


@app.route("/api/push/unsubscribe_all", methods=["POST"])
@login_required
def api_push_unsubscribe_all():
    """내 계정의 모든 기기 푸시 구독 삭제 — '완전 오프라인' 확실한 탈출구.
    로그아웃 정리가 실패해 '휴대폰' 상태로 끼어있을 때 즉시 정리용."""
    me = current_user()
    db = get_db()
    n = db.execute(
        "SELECT COUNT(*) FROM push_subscriptions WHERE user_id=?", (me["id"],)
    ).fetchone()[0]
    db.execute("DELETE FROM push_subscriptions WHERE user_id=?", (me["id"],))
    db.commit()
    return jsonify({"ok": True, "deleted": n})


@app.route("/api/push/test", methods=["POST"])
@login_required
def api_push_test():
    """테스트 푸시 발송 + 실패 시 상세 에러 반환 (진단용).
    본인→본인 직접 발송 (억제 로직 우회) — 푸시 인프라 자체 동작 확인용."""
    me = current_user()
    sent, errors, total = send_push_to_user(
        me["id"],
        "🔔 KNK 메신저 테스트",
        "푸시 알림이 정상 작동합니다.",
        url="/chat", tag="test",
        collect_errors=True,
    )
    return jsonify({"sent": sent, "total_subscriptions": total, "errors": errors})


@app.route("/api/push/test_simulate", methods=["POST"])
@login_required
def api_push_test_simulate():
    """실제 메시지 수신 시나리오 시뮬레이션 — 똑똑한 억제 로직(_user_has_active_pc) 적용.
    '다른 사람이 보낸 메시지' 처럼 동작:
      · PC 가 실제 활성(focus+최근 heartbeat) → 모바일 푸시 스킵 (정상 동작 확인)
      · PC 비활성/자리비움/끔 → 모바일 푸시 발송 (백그라운드 알림 확인)
    """
    me = current_user()
    pc_active = _user_has_active_pc(me["id"])
    if pc_active:
        return jsonify({
            "pc_active": True,
            "skipped": True,
            "message": "PC가 활성 상태라 모바일 푸시를 스킵했습니다 (똑똑한 억제 정상 동작). "
                       "휴대폰만 두고 PC를 끄거나 1분 이상 자리를 비운 뒤 다시 시도하세요.",
        })
    sent, errors, total = send_push_to_user(
        me["id"],
        "💬 테스트발송 — 새 메시지",
        "실제 수신 시나리오 시뮬레이션입니다. 이 알림이 보이면 백그라운드 푸시 정상!",
        url="/chat", tag="test_sim",
        collect_errors=True,
    )
    return jsonify({"pc_active": False, "skipped": False, "sent": sent, "total_subscriptions": total, "errors": errors})


@app.route("/api/admin/cleanup", methods=["POST"])
@login_required
def api_admin_cleanup():
    """메시지 자동삭제 — N개월 이전 메시지(첨부 포함) 제거. 단 keep_forever=1 프로젝트·system 메시지 보존.

    수동 실행 또는 외부 스케줄러(Windows 작업스케줄러·cron)에서 호출.
    """
    me = current_user()
    if me["role"] != "ceo":
        abort(403)
    db = get_db()
    cutoff = (datetime.now(timezone.utc).date().replace(day=1)).isoformat()
    # cutoff = "오늘 - N개월" 의 첫날
    months = MESSAGE_RETENTION_MONTHS
    # 1단계: 전역 보존 정책 (N개월). keep_forever=1 프로젝트은 제외.
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


# ============================================================
# 🧪 부하 테스트 전용 API (대표 지시 2026-05-20)
#   격리된 테스트 계정·방·메시지 일괄 생성/삭제. admin 전용.
#   계정 username 패턴: loadtest_001@knktest.local ~ loadtest_NNN@knktest.local
#   방 이름 prefix: [LOADTEST]
#   confirm_token 필수 (URL 또는 body): "I_UNDERSTAND_LOAD_TEST"
# ============================================================
LOAD_TEST_USERNAME_PREFIX = "loadtest_"
LOAD_TEST_USERNAME_DOMAIN = "@knktest.local"
LOAD_TEST_ROOM_NAME_PREFIX = "[LOADTEST]"
LOAD_TEST_CONFIRM_TOKEN = "I_UNDERSTAND_LOAD_TEST"


@app.route("/api/admin/load_test/setup", methods=["POST"])
@login_required
def api_load_test_setup():
    """N개 격리 테스트 계정 + 1개 격리 방 자동 생성.
    body: {count: 75, confirm_token: 'I_UNDERSTAND_LOAD_TEST'}
    응답: {users: [{username, password, id}, ...], room_id, room_name}"""
    me = current_user()
    if me["role"] != "ceo":
        abort(403)
    data = request.get_json(silent=True) or {}
    if data.get("confirm_token") != LOAD_TEST_CONFIRM_TOKEN:
        return jsonify({"error": f"confirm_token 필수: '{LOAD_TEST_CONFIRM_TOKEN}'"}), 400
    count = int(data.get("count", 75))
    if count < 1 or count > 200:
        return jsonify({"error": "count 는 1~200 사이"}), 400
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    created_users = []
    for i in range(1, count + 1):
        username = f"{LOAD_TEST_USERNAME_PREFIX}{i:03d}{LOAD_TEST_USERNAME_DOMAIN}"
        password = f"{LOAD_TEST_USERNAME_PREFIX}{i:03d}_pwd"
        display_name = f"부하테스트{i:03d}"
        # 이미 존재하면 그 id 사용
        existing = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if existing:
            uid = existing["id"]
            # 비밀번호 갱신 (이전 테스트 잔존 대비)
            db.execute("UPDATE users SET password_hash=?, must_change_password=0, active=1 WHERE id=?",
                       (generate_password_hash(password), uid))
        else:
            cur = db.execute(
                "INSERT INTO users (username, password_hash, display_name, role, avatar_color, created_at, "
                " email, title, department, must_change_password, active) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (username, generate_password_hash(password), display_name, "staff", "#9CA3AF",
                 now, username, "부하테스트", "테스트", 0, 1)
            )
            uid = cur.lastrowid
        created_users.append({"id": uid, "username": username, "password": password})
    # 격리 방 생성 (이미 존재하면 재활용)
    room_name = f"{LOAD_TEST_ROOM_NAME_PREFIX} 부하 테스트 방"
    existing_room = db.execute("SELECT id FROM rooms WHERE name=?", (room_name,)).fetchone()
    if existing_room:
        room_id = existing_room["id"]
        # 기존 멤버 다 비우고 재구성
        db.execute("DELETE FROM room_members WHERE room_id=?", (room_id,))
    else:
        cur = db.execute(
            "INSERT INTO rooms (name, type, created_by, created_at, invite_policy) "
            "VALUES (?, 'group', ?, ?, 'all')",
            (room_name, me["id"], now)
        )
        room_id = cur.lastrowid
    # admin + 75개 테스트 계정 모두 멤버로
    db.execute("INSERT INTO room_members (room_id, user_id, role, joined_at) VALUES (?, ?, 'host', ?)",
               (room_id, me["id"], now))
    for u in created_users:
        db.execute("INSERT INTO room_members (room_id, user_id, role, joined_at) VALUES (?, ?, 'member', ?)",
                   (room_id, u["id"], now))
    db.commit()
    return jsonify({
        "users": created_users,
        "room_id": room_id,
        "room_name": room_name,
        "count": len(created_users),
    })


@app.route("/api/admin/load_test/cleanup", methods=["POST"])
@login_required
def api_load_test_cleanup():
    """loadtest_* 계정 + [LOADTEST] 방 + 관련 메시지·파일 일괄 삭제.
    body: {confirm_token: 'I_UNDERSTAND_LOAD_TEST'}"""
    me = current_user()
    if me["role"] != "ceo":
        abort(403)
    data = request.get_json(silent=True) or {}
    if data.get("confirm_token") != LOAD_TEST_CONFIRM_TOKEN:
        return jsonify({"error": f"confirm_token 필수: '{LOAD_TEST_CONFIRM_TOKEN}'"}), 400
    db = get_db()
    # 1) [LOADTEST] 방의 모든 메시지·파일 삭제
    rooms = db.execute("SELECT id FROM rooms WHERE name LIKE ?", (f"{LOAD_TEST_ROOM_NAME_PREFIX}%",)).fetchall()
    deleted_files = 0
    deleted_msgs = 0
    deleted_rooms = 0
    for r in rooms:
        rid = r["id"]
        # 파일 디스크 삭제
        files = db.execute("SELECT file_path FROM messages WHERE room_id=? AND file_path IS NOT NULL", (rid,)).fetchall()
        for f in files:
            try:
                fpath = os.path.join(UPLOAD_DIR, f["file_path"])
                if os.path.exists(fpath):
                    os.remove(fpath)
                    deleted_files += 1
            except Exception:
                pass
        # 방 디렉토리 자체 삭제 시도
        try:
            room_dir = os.path.join(UPLOAD_DIR, str(rid))
            if os.path.isdir(room_dir):
                import shutil as _sh
                _sh.rmtree(room_dir, ignore_errors=True)
        except Exception:
            pass
        # 메시지 + 멤버 + 방 삭제 (FK CASCADE 의존)
        c = db.execute("DELETE FROM messages WHERE room_id=?", (rid,))
        deleted_msgs += c.rowcount or 0
        db.execute("DELETE FROM room_members WHERE room_id=?", (rid,))
        db.execute("DELETE FROM requests WHERE room_id=?", (rid,))
        db.execute("DELETE FROM rooms WHERE id=?", (rid,))
        deleted_rooms += 1
    # 2) loadtest_* 계정 삭제 — 다른 곳에 있는 멤버십·메시지도 정리
    test_users = db.execute(
        "SELECT id FROM users WHERE username LIKE ?",
        (f"{LOAD_TEST_USERNAME_PREFIX}%{LOAD_TEST_USERNAME_DOMAIN}",)
    ).fetchall()
    deleted_users = 0
    for u in test_users:
        uid = u["id"]
        db.execute("DELETE FROM room_members WHERE user_id=?", (uid,))
        db.execute("DELETE FROM messages WHERE user_id=?", (uid,))
        db.execute("DELETE FROM users WHERE id=?", (uid,))
        deleted_users += 1
    db.commit()
    return jsonify({
        "deleted_users": deleted_users,
        "deleted_rooms": deleted_rooms,
        "deleted_messages": deleted_msgs,
        "deleted_files": deleted_files,
    })


@app.route("/api/admin/load_test/status")
@login_required
def api_load_test_status():
    me = current_user()
    if me["role"] != "ceo":
        abort(403)
    db = get_db()
    test_users = db.execute(
        "SELECT COUNT(*) AS n FROM users WHERE username LIKE ?",
        (f"{LOAD_TEST_USERNAME_PREFIX}%{LOAD_TEST_USERNAME_DOMAIN}",)
    ).fetchone()
    test_rooms = db.execute("SELECT id, name FROM rooms WHERE name LIKE ?",
                            (f"{LOAD_TEST_ROOM_NAME_PREFIX}%",)).fetchall()
    test_msgs = 0
    for r in test_rooms:
        c = db.execute("SELECT COUNT(*) AS n FROM messages WHERE room_id=?", (r["id"],)).fetchone()
        test_msgs += c["n"]
    return jsonify({
        "test_users_count": test_users["n"],
        "test_rooms": [{"id": r["id"], "name": r["name"]} for r in test_rooms],
        "test_messages_count": test_msgs,
    })


@app.route("/api/admin/backup_now", methods=["POST"])
@login_required
def api_admin_backup_now():
    """수동 백업 즉시 실행 — deploy/backup.sh 호출. admin 전용."""
    me = current_user()
    if me["role"] != "ceo":
        abort(403)
    try:
        import subprocess as _sp
        backup_script = os.path.join(APP_DIR, "deploy", "backup.sh")
        if not os.path.exists(backup_script):
            return jsonify({"error": f"backup.sh not found at {backup_script}"}), 500
        result = _sp.run(["bash", backup_script], capture_output=True, text=True, timeout=600)
        return jsonify({
            "exit_code": result.returncode,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-2000:],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users", methods=["POST"])
@login_required
def api_users_create():
    """관리자만 — 직원 등록.
    표준 정책: username = 회사 이메일, 초기 password = 전화번호 (숫자만), must_change_password=1.
    body: {display_name, email, phone, title?, department?, role?, avatar_color?}
    + 호환: 옛 방식의 {username, password, display_name} 도 허용."""
    me = current_user()
    if me["role"] != "ceo":
        abort(403)
    data = request.get_json(silent=True) or {}
    display_name = (data.get("display_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    title = (data.get("title") or "").strip()[:40] or None
    department = (data.get("department") or "").strip()[:40] or None
    employee_no = (data.get("employee_no") or "").strip()[:30] or None
    role = data.get("role") or "staff"
    avatar_color = data.get("avatar_color") or "#3b82f6"
    # 호환: username·password 직접 지정 가능 (특수 케이스)
    explicit_username = (data.get("username") or "").strip().lower()
    explicit_password = data.get("password")

    if not display_name:
        return jsonify({"error": "이름(display_name) 필수"}), 400

    # 표준 모드: 이메일·전화 기반
    if not explicit_username:
        if not email or "@" not in email:
            return jsonify({"error": "회사 이메일(@ 포함) 필수"}), 400
        if not phone:
            return jsonify({"error": "휴대폰 번호 필수 (초기 비밀번호로 사용)"}), 400
        username = email
        # 비밀번호는 전화번호의 숫자만 (대시·공백 제거)
        digits = "".join(ch for ch in phone if ch.isdigit())
        if len(digits) < 9:
            return jsonify({"error": "전화번호 자릿수 부족 (숫자 9자리 이상)"}), 400
        password = digits
        must_change = 1
    else:
        username = explicit_username
        password = explicit_password or "knk1234"
        must_change = 1 if data.get("must_change_password", True) else 0

    db = get_db()
    if db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
        return jsonify({"error": f"이미 존재하는 ID: {username}"}), 400
    now = datetime.now(timezone.utc).isoformat()
    cur = db.execute(
        "INSERT INTO users (username, password_hash, display_name, role, avatar_color, "
        " created_at, email, phone, title, department, employee_no, must_change_password) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (username, generate_password_hash(password), display_name, role, avatar_color,
         now, email or None, phone or None, title, department, employee_no, must_change),
    )
    db.commit()
    # 신규 직원 → 자동채널(KNK WORLD + 본사/베트남) 자동 가입 (대표 지시 2026-05-20)
    try: _sync_user_auto_channels(db, cur.lastrowid)
    except Exception as e: print(f"[auto_channel] create sync 실패: {e}")
    # broadcast — 사용자 목록 즉시 갱신
    new_row = db.execute(
        "SELECT id, username, display_name, role, avatar_color, title, department, email, phone, employee_no, active "
        "FROM users WHERE id=?", (cur.lastrowid,)
    ).fetchone()
    socketio.emit("user_info_changed", dict(new_row))
    return jsonify({
        "id": cur.lastrowid,
        "username": username,
        "display_name": display_name,
        "initial_password_hint": "전화번호 숫자만 (대시·공백 제외)" if must_change == 1 else None,
    })


def _ensure_deleted_placeholder_user(db):
    """삭제된 사용자의 메시지·요청을 이전받을 플레이스홀더 사용자.
    username='_deleted_user', active=0 (로그인 불가). 1회만 생성."""
    row = db.execute("SELECT id FROM users WHERE username = '_deleted_user'").fetchone()
    if row:
        return row["id"]
    now = datetime.now(timezone.utc).isoformat()
    cur = db.execute(
        "INSERT INTO users (username, password_hash, display_name, role, avatar_color, "
        " created_at, active) VALUES (?,?,?,?,?,?,?)",
        ("_deleted_user", "", "(삭제된 사용자)", "staff", "#9CA3AF", now, 0),
    )
    return cur.lastrowid


@app.route("/api/users/<int:user_id>", methods=["DELETE"])
@login_required
def api_user_delete(user_id):
    """사용자 완전 삭제 (퇴사 등). 관리자(ceo) 만 가능.
    동작:
      1. 메시지·요청·방생성 기록을 '(삭제된 사용자)' 플레이스홀더로 이전 (이력 보존)
      2. 사용자 행 DELETE → CASCADE 로 room_members·push_subscriptions·reactions 자동 정리
    안전장치:
      - 본인 삭제 불가
      - 마지막 관리자 삭제 불가
      - 초기 대표 계정(id=1) 삭제 불가 (비활성화는 가능)"""
    me = current_user()
    if me["role"] != "ceo":
        return jsonify({"error": "관리자만 삭제 가능"}), 403
    if user_id == me["id"]:
        return jsonify({"error": "본인은 삭제할 수 없습니다. 다른 관리자에게 요청하세요."}), 400
    db = get_db()
    row = db.execute("SELECT id, display_name, role FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        return jsonify({"error": "사용자 없음"}), 404
    # id=1 = 초기 대표 계정 — 절대 삭제 금지 (시드 보호)
    if user_id == 1:
        return jsonify({"error": "초기 대표 계정(id=1)은 삭제할 수 없습니다. 비활성화만 가능합니다."}), 400
    # 최고관리자(소유자) — 삭제 금지 (대표 지시 2026-05-21)
    _own = db.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()
    if _own and _is_owner(_own["username"]):
        return jsonify({"error": "최고관리자 계정은 삭제할 수 없습니다."}), 400
    # 플레이스홀더 사용자에게 본인을 삭제하려는 경우 — 차단
    if row["display_name"] == "(삭제된 사용자)":
        return jsonify({"error": "시스템 사용자는 삭제할 수 없습니다."}), 400
    # 마지막 관리자 삭제 차단
    if row["role"] == "ceo":
        ceo_count = db.execute("SELECT COUNT(*) AS n FROM users WHERE role='ceo' AND active=1").fetchone()["n"]
        if ceo_count <= 1:
            return jsonify({"error": "마지막 관리자는 삭제할 수 없습니다. 다른 관리자를 먼저 임명하세요."}), 400
    deleted_name = row["display_name"]
    # 플레이스홀더 사용자 확보
    placeholder_id = _ensure_deleted_placeholder_user(db)
    # 메시지·요청·방생성 등 NOT NULL FK 가 있는 것들 → 플레이스홀더로 이전
    db.execute("UPDATE messages SET user_id = ? WHERE user_id = ?", (placeholder_id, user_id))
    db.execute("UPDATE messages SET forwarded_from_user_id = ? WHERE forwarded_from_user_id = ?", (placeholder_id, user_id))
    db.execute("UPDATE rooms SET created_by = ? WHERE created_by = ?", (placeholder_id, user_id))
    try:
        db.execute("UPDATE requests SET requested_by = ? WHERE requested_by = ?", (placeholder_id, user_id))
        db.execute("UPDATE requests SET assigned_to = NULL WHERE assigned_to = ?", (user_id,))
    except Exception:
        pass
    try:
        db.execute("UPDATE items SET created_by = ? WHERE created_by = ?", (placeholder_id, user_id))
    except Exception:
        pass
    # 사용자 삭제 — CASCADE 로 room_members/push_subscriptions/reactions/acks/stars 등 자동 정리
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    # 실시간 broadcast — 사용자 목록 즉시 갱신
    socketio.emit("user_deleted", {"user_id": user_id, "display_name": deleted_name})
    return jsonify({"ok": True, "deleted_user_id": user_id, "display_name": deleted_name})


@app.route("/api/users/<int:user_id>/reset_password", methods=["POST"])
@login_required
def api_user_reset_password(user_id):
    """관리자가 사용자 비밀번호를 전화번호(숫자만)로 초기화 (대표 지시 2026-05-21, 규칙 5).
    초기화 후 must_change_password=1 → 사용자 첫 로그인 시 새 비밀번호 설정 강제."""
    me = current_user()
    if me["role"] != "ceo":
        return jsonify({"error": "관리자만 비밀번호를 초기화할 수 있습니다."}), 403
    db = get_db()
    row = db.execute("SELECT id, username, display_name, phone FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        return jsonify({"error": "사용자 없음"}), 404
    # 최고관리자 비밀번호는 탈취 방지 — 본인(최고관리자)만 변경 가능
    if _is_owner(row["username"]) and not _is_owner(me["username"]):
        return jsonify({"error": "최고관리자 비밀번호는 본인만 변경할 수 있습니다."}), 403
    digits = "".join(ch for ch in (row["phone"] or "") if ch.isdigit())
    if not digits:
        return jsonify({"error": "이 사용자의 전화번호가 없어 초기화할 수 없습니다. 먼저 전화번호를 등록하세요."}), 400
    db.execute("UPDATE users SET password_hash=?, must_change_password=1 WHERE id=?",
               (generate_password_hash(digits), user_id))
    db.commit()
    return jsonify({"ok": True, "temp_password": digits, "display_name": row["display_name"]})


@app.route("/api/me/password", methods=["PUT"])
@login_required
def api_me_password():
    """본인 비밀번호 변경. body: {current_password, new_password}
    must_change_password=1 인 첫 로그인 사용자도 이 엔드포인트로 변경."""
    me = current_user()
    data = request.get_json(silent=True) or {}
    cur_pw = data.get("current_password") or ""
    new_pw = data.get("new_password") or ""
    if not new_pw or len(new_pw) < 6:
        return jsonify({"error": "새 비밀번호는 6자 이상"}), 400
    if new_pw == cur_pw:
        return jsonify({"error": "현재 비밀번호와 동일 — 변경 의미 없음"}), 400
    db = get_db()
    row = db.execute("SELECT password_hash FROM users WHERE id=?", (me["id"],)).fetchone()
    if not row or not check_password_hash(row["password_hash"], cur_pw):
        return jsonify({"error": "현재 비밀번호가 올바르지 않습니다"}), 400
    db.execute(
        "UPDATE users SET password_hash=?, must_change_password=0 WHERE id=?",
        (generate_password_hash(new_pw), me["id"]),
    )
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/me/must_change_password", methods=["GET"])
@login_required
def api_me_must_change():
    """현재 사용자가 비밀번호 변경 강제 상태인지 조회 (UI 다이얼로그 트리거용)."""
    me = current_user()
    db = get_db()
    row = db.execute("SELECT must_change_password FROM users WHERE id=?", (me["id"],)).fetchone()
    return jsonify({"must_change": bool(row and row["must_change_password"])})


@app.route("/api/users/bulk/template")
@login_required
def api_users_bulk_template():
    """직원 일괄 등록용 엑셀 양식 다운로드. 관리자만."""
    me = current_user()
    if me["role"] != "ceo":
        abort(403)
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from openpyxl.worksheet.datavalidation import DataValidation
    except ImportError:
        return jsonify({"error": "openpyxl 미설치"}), 500
    import io

    wb = Workbook()
    # ─── 시트 1: 입력 ───
    ws = wb.active
    ws.title = "직원등록"
    headers = ["이름 *", "회사 이메일 * (=로그인 ID)", "휴대폰 * (=초기 비밀번호)", "사번", "직급", "부서", "권한"]
    ws.append(headers)
    # 헤더 스타일
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="A5282C", end_color="A5282C", fill_type="solid")
    border_thin = Border(
        left=Side(style='thin', color='D1D5DB'),
        right=Side(style='thin', color='D1D5DB'),
        top=Side(style='thin', color='D1D5DB'),
        bottom=Side(style='thin', color='D1D5DB'),
    )
    for col_idx, _ in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border_thin
    ws.row_dimensions[1].height = 30
    # 컬럼 너비 (이름, 이메일, 휴대폰, 사번, 직급, 부서, 권한)
    widths = [14, 32, 18, 12, 14, 14, 12]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + i)].width = w
    # 예시 행 3개
    examples = [
        ["홍길동", "hong@knknara.co.kr", "010-1234-5678", "K2401", "사원", "영업", "일반"],
        ["이순신", "lee@knknara.co.kr", "010-2345-6789", "K2402", "과장", "기술", "일반"],
        ["김영업", "kim.sales@knknara.co.kr", "010-3456-7890", "K2403", "부장", "기술영업", "관리자"],
    ]
    for row in examples:
        ws.append(row)
    # 예시 행 색상 강조 (회색 — "예시" 표시)
    example_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    for r in range(2, 5):
        for c in range(1, 8):
            cell = ws.cell(row=r, column=c)
            cell.fill = example_fill
            cell.font = Font(italic=True, color="9CA3AF")
            cell.border = border_thin
    # 빈 행 추가 (사용자가 직접 입력) — 100행
    for _ in range(100):
        ws.append(["", "", "", "", "", "", ""])
    for r in range(5, 105):
        for c in range(1, 8):
            ws.cell(row=r, column=c).border = border_thin

    # 권한 컬럼 (G열) 드롭다운: 관리자 / 일반
    dv_role = DataValidation(type="list", formula1='"관리자,일반"', allow_blank=True)
    dv_role.error = "권한은 '관리자' 또는 '일반' 만 가능합니다"
    dv_role.errorTitle = "잘못된 권한"
    ws.add_data_validation(dv_role)
    dv_role.add(f"G2:G105")
    # 부서 컬럼 (F열) 드롭다운 — 본사 14 + 베트남법인 9 (대표 지시 2026-05-20 갱신)
    # 본사: 'NN 부서명' / 베트남: '12-VNNN 부서명' (베트남은 DB에도 코드 포함하여 통째로 저장)
    # 일괄 등록 파싱이 prefix 자동 인식 → 본사는 부서명 그대로, 베트남은 '12-VNNN 부서명' 그대로 DB 저장.
    dv_dept = DataValidation(
        type="list",
        formula1='"00 총괄,01 기술영업팀,02 검사기팀,03 품질팀,04 설계팀(자동화),04 설계팀(검사기),05 소프트웨어팀,06 전장설계팀,07 제조기술1팀,08 제조기술2팀,09 가공팀,10 구매팀,11 관리팀,13 개발혁신팀,14 라이프밸류팀,12-VN01 기술팀,12-VN02 조립팀,12-VN03 전장팀,12-VN04 설계팀,12-VN05 소프트웨어팀,12-VN06 가공팀,12-VN07 품질팀,12-VN08 구매팀,12-VN09 관리팀"',
        allow_blank=True,
    )
    ws.add_data_validation(dv_dept)
    dv_dept.add(f"F2:F105")

    # ─── 시트 2: 안내 ───
    ws2 = wb.create_sheet("안내")
    notes = [
        ["KNK 메신저 — 직원 일괄 등록 안내", ""],
        ["", ""],
        ["1. 필수 필드 (별표 * 표시)", ""],
        ["", "이름 / 회사 이메일 / 휴대폰 — 3개는 반드시 입력"],
        ["", "직급·부서·권한 은 비워둬도 됨 (나중에 본인이 직접 수정 가능)"],
        ["", ""],
        ["2. 로그인 ID 와 초기 비밀번호", ""],
        ["", "회사 이메일 = 로그인 ID (그대로)"],
        ["", "휴대폰 번호 (숫자만 사용) = 초기 비밀번호"],
        ["", "예: 010-1234-5678 → 비밀번호 '01012345678'"],
        ["", ""],
        ["3. 첫 로그인 동작", ""],
        ["", "직원이 처음 로그인하면 비밀번호 변경 다이얼로그가 강제로 노출됨"],
        ["", "본인만 아는 비밀번호로 변경한 후에야 메신저 사용 가능"],
        ["", ""],
        ["4. 권한 옵션", ""],
        ["", "'관리자' — 직원 등록·다른 사람 정보 수정·계정 비활성화·삭제 가능"],
        ["", "'일반' (또는 빈칸) — 본인 정보만 수정. 평소 사용자"],
        ["", ""],
        ["5. 이메일 중복 검사", ""],
        ["", "이미 등록된 이메일은 자동 스킵됨 (결과 화면에 표시)"],
        ["", ""],
        ["6. 양식 작성 팁", ""],
        ["", "예시 3줄은 자동 무시됩니다 (회색·기울임 표시 행)"],
        ["", "그 아래 빈 행부터 직접 입력하세요"],
        ["", "100명 이상 등록 필요 시 여러 번 나눠 업로드"],
        ["", ""],
        ["7. 부서 코드 매핑표 (참고용)", ""],
        ["[임원]", ""],
        ["", "00 총괄  (대표이사 전용)"],
        ["[본사 — 한국]", ""],
        ["", "01 기술영업팀         07 제조기술1팀"],
        ["", "02 검사기팀           08 제조기술2팀"],
        ["", "03 품질팀             09 가공팀"],
        ["", "04 설계팀(자동화)     10 구매팀"],
        ["", "04 설계팀(검사기)     11 관리팀"],
        ["", "05 소프트웨어팀       13 개발혁신팀"],
        ["", "06 전장설계팀         14 라이프밸류팀"],
        ["", "※ 12번은 베트남법인 prefix 전용 — 본사엔 12 없음"],
        ["[베트남법인 — 12번 산하]", ""],
        ["", "12-VN01 기술팀         12-VN06 가공팀"],
        ["", "12-VN02 조립팀         12-VN07 품질팀"],
        ["", "12-VN03 전장팀         12-VN08 구매팀"],
        ["", "12-VN04 설계팀         12-VN09 관리팀"],
        ["", "12-VN05 소프트웨어팀"],
    ]
    for r, (a, b) in enumerate(notes, start=1):
        ws2.cell(row=r, column=1, value=a)
        ws2.cell(row=r, column=2, value=b)
    ws2.column_dimensions['A'].width = 28
    ws2.column_dimensions['B'].width = 80
    # 1행 제목 굵게
    ws2.cell(row=1, column=1).font = Font(bold=True, size=14, color="A5282C")

    # 다운로드
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    from flask import send_file
    return send_file(
        buf,
        as_attachment=True,
        download_name="KNK_직원등록_양식.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/api/users/bulk", methods=["POST"])
@login_required
def api_users_bulk():
    """엑셀 일괄 등록. 관리자만. multipart/form-data 의 'file' 필드에 .xlsx.
    결과: {created: [...], skipped: [{row, name, reason}], errors: [{row, name, error}]}"""
    me = current_user()
    if me["role"] != "ceo":
        return jsonify({"error": "관리자만 일괄 등록 가능"}), 403
    if "file" not in request.files:
        return jsonify({"error": "file 필드에 엑셀 첨부 필요"}), 400
    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith((".xlsx", ".xlsm")):
        return jsonify({"error": "엑셀 파일(.xlsx) 만 업로드 가능"}), 400
    try:
        from openpyxl import load_workbook
    except ImportError:
        return jsonify({"error": "openpyxl 미설치"}), 500
    try:
        wb = load_workbook(f, read_only=True, data_only=True)
        ws = wb.active
    except Exception as e:
        return jsonify({"error": f"엑셀 파일 열기 실패: {e}"}), 400

    EXAMPLE_EMAILS = {"hong@knknara.co.kr", "lee@knknara.co.kr", "kim.sales@knknara.co.kr"}
    EXAMPLE_NAMES = {"홍길동", "이순신", "김영업"}

    created = []
    skipped = []
    errors = []
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    # 헤더 한 줄 스킵 (row=1). row=2 부터 데이터.
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or all(c is None or (isinstance(c, str) and not c.strip()) for c in row):
            continue  # 빈 행 스킵
        # 7컬럼: 이름·이메일·전화·사번·직급·부서·권한
        name = (str(row[0]) if row[0] is not None else "").strip()
        email = (str(row[1]) if row[1] is not None else "").strip().lower()
        phone = (str(row[2]) if row[2] is not None else "").strip()
        employee_no = (str(row[3]) if len(row) > 3 and row[3] is not None else "").strip()
        title = (str(row[4]) if len(row) > 4 and row[4] is not None else "").strip()
        department = (str(row[5]) if len(row) > 5 and row[5] is not None else "").strip()
        # 부서 코드 정규화 (대표 지시 2026-05-20 갱신)
        #  · '01 기술영업팀'    → '기술영업팀'           (본사 — code prefix 제거)
        #  · '12-VN01 기술팀'  → '12-VN01 기술팀'      (베트남법인 — DB에도 코드 포함하여 통째로 저장)
        #  · 'VN12-01 기술팀'  → '12-VN01 기술팀'      (legacy 포맷 자동 변환)
        import re as _re_dept
        m_vn_new = _re_dept.match(r"^\s*12-VN(\d{2})\s+(.+)$", department)
        m_vn_legacy = _re_dept.match(r"^\s*VN12-(\d{2})\s+(.+)$", department) if not m_vn_new else None
        m_kr = _re_dept.match(r"^\s*(\d{2})\s+(.+)$", department) if (not m_vn_new and not m_vn_legacy) else None
        if m_vn_new:
            department = f"12-VN{m_vn_new.group(1)} {m_vn_new.group(2).strip()}"
        elif m_vn_legacy:
            department = f"12-VN{m_vn_legacy.group(1)} {m_vn_legacy.group(2).strip()}"
        elif m_kr:
            department = m_kr.group(2).strip()
        role_raw = (str(row[6]) if len(row) > 6 and row[6] is not None else "").strip()
        # 예시 행 자동 스킵
        if email in EXAMPLE_EMAILS or name in EXAMPLE_NAMES:
            skipped.append({"row": row_idx, "name": name, "reason": "예시 행 (자동 스킵)"})
            continue
        # 권한 변환
        role = "ceo" if role_raw == "관리자" else "staff"
        # 검증
        if not name:
            errors.append({"row": row_idx, "name": "(이름 없음)", "error": "이름 누락"})
            continue
        if not email or "@" not in email:
            errors.append({"row": row_idx, "name": name, "error": "이메일 형식 오류 (@ 누락)"})
            continue
        if not phone:
            errors.append({"row": row_idx, "name": name, "error": "휴대폰 번호 누락"})
            continue
        digits = "".join(ch for ch in phone if ch.isdigit())
        if len(digits) < 9:
            errors.append({"row": row_idx, "name": name, "error": f"전화번호 자릿수 부족 ({digits})"})
            continue
        # 중복 검사
        if db.execute("SELECT 1 FROM users WHERE username=?", (email,)).fetchone():
            skipped.append({"row": row_idx, "name": name, "reason": f"이미 등록됨 ({email})"})
            continue
        # 등록
        try:
            db.execute(
                "INSERT INTO users (username, password_hash, display_name, role, avatar_color, "
                " created_at, email, phone, title, department, employee_no, must_change_password) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    email,
                    generate_password_hash(digits),
                    name, role, "#3b82f6",
                    now, email, phone,
                    title or None, department or None, employee_no or None, 1,
                ),
            )
            created.append({"row": row_idx, "name": name, "email": email, "phone_initial_pw": digits})
        except Exception as e:
            errors.append({"row": row_idx, "name": name, "error": f"DB 오류: {e}"})
    db.commit()
    # 일괄 등록 후 자동채널(KNK WORLD/본사/베트남) 멤버십 전체 재동기화 (대표 지시 2026-05-20)
    if created:
        try: _resync_auto_channels(db)
        except Exception as e: print(f"[auto_channel] bulk resync 실패: {e}")
    # broadcast — 새로 등록된 사용자 목록 갱신
    if created:
        rows = db.execute(
            "SELECT id, username, display_name, role, avatar_color, title, department, email, phone, employee_no, active "
            "FROM users WHERE username IN ({})".format(",".join("?" for _ in created)),
            [c["email"] for c in created],
        ).fetchall()
        for r in rows:
            socketio.emit("user_info_changed", dict(r))
    return jsonify({
        "created_count": len(created),
        "skipped_count": len(skipped),
        "error_count": len(errors),
        "created": created,
        "skipped": skipped,
        "errors": errors,
    })


def _parse_search_filters(q):
    """고급 검색 필터 파싱.
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
    """전문 검색 + 고급 필터.
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

    # 프로젝트 메타 검색 (LIKE) — plain_q 기준. 필터링 모드(예: from:만)면 스킵.
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

    # 프로젝트 결과 먼저, 그 다음 메시지 결과
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
    # 채널 생성 — 관리자(ceo) 또는 팀장 (대표 지시 2026-05-21)
    if type_ == "channel":
        _tl = _is_team_lead(me)
        if me["role"] != "ceo" and not _tl:
            return jsonify({"error": "채널은 관리자 또는 팀장만 만들 수 있습니다."}), 403
        # 팀장(비ceo)은 같은 부서원만 채널에 넣을 수 있음
        if me["role"] != "ceo" and _tl:
            _db0 = get_db()
            my_nd = _norm_dept(me["department"])
            for uid in user_ids:
                if uid == me["id"]:
                    continue
                ur = _db0.execute("SELECT department FROM users WHERE id=?", (uid,)).fetchone()
                if not ur or _norm_dept(ur["department"]) != my_nd:
                    return jsonify({"error": "팀장은 같은 부서원만 채널에 초대할 수 있습니다."}), 403
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

    room = db.execute("SELECT type, name, channel_scope FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not room:
        return jsonify({"error": "방이 없습니다."}), 404
    # 자동 채널(KNK WORLD/본사/베트남)은 전사·소속 채널이라 나갈 수 없음 (대표 지시 2026-05-20)
    if room["channel_scope"]:
        return jsonify({"error": "전사·소속 채널은 나갈 수 없습니다."}), 400

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
    if not r:
        return None
    role = r["role"]
    # 채널에서는 등록된 관리자(ceo)·최고관리자 모두가 방장 기능 수행 가능 (대표 지시 2026-05-21)
    # → 멤버이기만 하면 ceo 는 effective 'host' 로 취급 (rename·멤버관리·초대정책·삭제 등).
    if role != 'host':
        room = db.execute("SELECT type FROM rooms WHERE id=?", (room_id,)).fetchone()
        if room and room["type"] == 'channel':
            u = db.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
            if u and u["role"] == 'ceo':
                return 'host'
    return role


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


@app.route("/api/rooms/<int:room_id>", methods=["DELETE"])
@login_required
def api_room_delete(room_id):
    """채널(대화방) 삭제 (대표 지시 2026-05-21).
    관리자(ceo)는 모든 채널, 팀장은 본인이 만든 채널만. 자동 채널은 삭제 불가."""
    me = current_user()
    db = get_db()
    room = db.execute("SELECT id, type, channel_scope, name, created_by FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not room:
        return jsonify({"error": "방을 찾을 수 없습니다."}), 404
    if room["channel_scope"]:
        return jsonify({"error": "자동 채널(KNK WORLD/본사/베트남)은 삭제할 수 없습니다."}), 400
    if room["type"] != "channel":
        return jsonify({"error": "채널만 삭제할 수 있습니다."}), 400
    # 권한: 관리자(ceo) 또는 본인이 만든 채널의 팀장
    if me["role"] != "ceo":
        if not (_is_team_lead(me) and room["created_by"] == me["id"]):
            return jsonify({"error": "채널은 관리자 또는 채널을 만든 팀장만 삭제할 수 있습니다."}), 403
    name = room["name"]
    _emit_room_event(room_id, "room_deleted", {"room_id": room_id, "name": name})
    # 의존 데이터 명시 정리 (FK CASCADE 미적용 대비) — 전체공지 삭제와 동일 패턴
    db.execute("DELETE FROM messages WHERE room_id=?", (room_id,))
    db.execute("DELETE FROM room_members WHERE room_id=?", (room_id,))
    db.execute("DELETE FROM rooms WHERE id=?", (room_id,))
    db.commit()
    return jsonify({"ok": True, "deleted": name})


@app.route("/api/rooms/<int:room_id>/members", methods=["GET"])
@login_required
def api_room_members(room_id):
    """방 멤버 목록 + 각 역할 + 내 별명 + name_locked."""
    me = current_user()
    db = get_db()
    if not _my_room_role(db, room_id, me["id"]):
        abort(403)
    room = db.execute(
        "SELECT id, name, type, created_by, name_locked, retention_days, invite_policy, avatar_url FROM rooms WHERE id=?",
        (room_id,),
    ).fetchone()
    if not room:
        abort(404)
    alias = db.execute("SELECT alias FROM room_aliases WHERE room_id=? AND user_id=?",
                       (room_id, me["id"])).fetchone()
    return jsonify({
        "room": {
            "id": room["id"], "name": room["name"], "type": room["type"],
            "created_by": room["created_by"], "name_locked": bool(room["name_locked"]),
            "retention_days": room["retention_days"],
            "invite_policy": room["invite_policy"] or "all",
            # 방 설정 화면의 '아이콘 사진 변경/제거' 버튼 표시에 필요 (대표 지시 2026-05-20)
            "avatar_url": room["avatar_url"],
        },
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
    """방 이름 변경 — 방장 또는 관리자(ceo). body: {name, name_locked?}"""
    me = current_user()
    db = get_db()
    role = _my_room_role(db, room_id, me["id"])
    if role != 'host' and me["role"] != 'ceo':
        return jsonify({"error": "방장 또는 관리자만 가능"}), 403
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


# ---------- 사용자 상태 + 캘린더 동기화 ----------
# 대표 지시 2026-05-19: '온라인'→'회사' 라벨 변경, 방해금지 제거,
# 해외출장·국내출장·휴가 신규 추가.
# (status 키 'online' 은 코드 호환 위해 유지하고 라벨만 변경)
VALID_STATUSES = ("online", "away", "busy", "meeting", "external", "overseas", "domestic", "vacation", "offline")
STATUS_LABEL_KO = {
    "online":   "💻 컴퓨터",
    "mobile":   "📱 휴대폰",
    "away":     "🌙 자리비움",
    "busy":     "🔴 바쁨",
    "meeting":  "🤝 회의 중",
    "external": "🚗 외근",
    "overseas": "✈️ 해외출장",
    "domestic": "🚆 국내출장",
    "vacation": "🌴 휴가",
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


def _computed_user_status(uid):
    """uid 의 '표시용' 상태 dict — 자동표시 규칙 적용 (다른 사람에게 보이는 값).
      · 접속 중 + 기본('online') → PC 연결 있으면 'online'(가능), 휴대폰만이면 'mobile'(📱 휴대폰)
      · 접속 중 + 특수상태(회의중·외근 등) → 그대로 (사용자 선택)
      · 미접속 → 푸시 있으면 'mobile', 없으면 'offline'
    호출 측에서 app context 보장 필요 (get_db 사용)."""
    base = _get_user_status(uid)
    status = base["status"]
    if _user_is_online(uid):
        if status == "online":
            status = "online" if _user_has_pc_connection(uid) else "mobile"
        # else: 특수상태 그대로
    else:
        try:
            has_push = get_db().execute(
                "SELECT 1 FROM push_subscriptions WHERE user_id=? LIMIT 1", (uid,)
            ).fetchone()
        except Exception:
            has_push = None
        status = "mobile" if has_push else "offline"
        base["custom_text"] = None
        base["emoji"] = None
        base["until_at"] = None
    base["status"] = status
    base["label"] = STATUS_LABEL_KO.get(status, status)
    return base


# 직전에 broadcast 한 표시상태 캐시 — 동일 상태 중복 emit 방지 (uid -> status). eventlet 단일스레드 가정.
_last_status_bcast = {}

def _broadcast_status_if_changed(uid):
    """uid 의 표시 상태를 계산해, 직전 broadcast 와 다를 때만 user_status_changed emit.
    호출 측에서 app context 보장 필요."""
    try:
        s = _computed_user_status(uid)
        if _last_status_bcast.get(uid) == s["status"]:
            return
        _last_status_bcast[uid] = s["status"]
        socketio.emit("user_status_changed", {
            "user_id": uid, "status": s["status"],
            "custom_text": s.get("custom_text"), "emoji": s.get("emoji"),
            "label": s["label"],
        })
    except Exception as e:
        print(f"[status] broadcast 실패: {e}")


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
    cur = _get_user_status(me["id"])  # 본인에게 돌려줄 값 = 본인이 고른 상태
    # 다른 사람에게는 자동표시 규칙(가능/휴대폰) 적용한 값으로 broadcast
    disp = _computed_user_status(me["id"])
    _last_status_bcast[me["id"]] = disp["status"]
    socketio.emit("user_status_changed", {
        "user_id": me["id"], "status": disp["status"],
        "custom_text": disp.get("custom_text"), "emoji": disp.get("emoji"),
        "label": disp["label"],
    })
    return jsonify({"ok": True, "current": cur})


@app.route("/api/users/statuses", methods=["GET"])
@login_required
def api_users_statuses():
    """전체 사용자 현재 상태 일괄 조회 — 사이드바·메시지 아바타 색점용."""
    db = get_db()
    me = current_user()
    my_uid = me["id"] if me else None
    rows = db.execute("""
        SELECT u.id AS user_id, u.display_name,
               COALESCE(us.status, 'online') AS status,
               us.custom_text, us.emoji, us.until_at
          FROM users u
          LEFT JOIN user_statuses us ON us.user_id = u.id
         WHERE u.active = 1
    """).fetchall()
    # 푸시 구독이 있는 사용자 집합 — 앱이 닫혀도(연결 끊겨도) 알림 받을 수 있음 = '📱 휴대폰'
    # (대표 지시 2026-05-20: 오프라인 vs 휴대폰 구분. 오프라인=로그아웃·알림X, 휴대폰=알림O)
    try:
        push_uids = set(r["user_id"] for r in db.execute(
            "SELECT DISTINCT user_id FROM push_subscriptions"
        ).fetchall())
    except Exception:
        push_uids = set()
    out = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for r in rows:
        d = dict(r)
        # ★ 본인은 항상 online 으로 간주 (API 호출 자체가 활성 세션 증거)
        #   SocketIO connect 전 API 호출 race condition 회피 (대표 지시 2026-05-19).
        is_self = (my_uid is not None and d["user_id"] == my_uid)
        uid = d["user_id"]
        online = _user_is_online(uid)
        # 만료된 until_at 은 기본(online)으로 강등 (DB 미반영, 표시상만)
        if d.get("until_at") and d["until_at"] < now_iso:
            d["status"] = "online"
            d["until_at"] = None
        set_status = d["status"]  # 사용자가 설정한 상태 (없으면 'online')
        # ★ 상태 자동표시 규칙 (대표 지시 2026-05-20):
        #   · 접속 중 + 기본('online') → PC 연결 있으면 '가능', 휴대폰만이면 '📱 휴대폰'
        #   · 접속 중 + 특수상태(회의중·외근 등) → 그대로 (사용자 선택)
        #   · 미접속 → 푸시 있으면 '휴대폰', 없으면 '오프라인'
        if online or is_self:
            if set_status == "online":
                # 본인인데 아직 소켓 미연결(로드 직후 race)이면 PC 판정 불가 → '가능' 기본
                d["status"] = "online" if (_user_has_pc_connection(uid) or (is_self and not online)) else "mobile"
            else:
                d["status"] = set_status
        else:
            d["status"] = "mobile" if uid in push_uids else "offline"
            d["custom_text"] = None
            d["emoji"] = None
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


# ============================================================
# 🛡️ 자동 백업 워커 (대표 지시 2026-05-19)
#   매일 새벽 3시 (KST) deploy/backup.sh 실행. cron 별도 설정 불필요.
#   threading.Thread daemon — eventlet 환경에서도 안전 (subprocess 사용).
# ============================================================
_backup_thread_started = False

def _start_backup_worker():
    global _backup_thread_started
    if _backup_thread_started:
        return
    _backup_thread_started = True
    import threading as _th, subprocess as _sp, time as _t
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td
    def _loop():
        # KST = UTC+9
        kst = _tz(_td(hours=9))
        while True:
            try:
                now_kst = _dt.now(kst)
                # 다음 새벽 3시 (KST) 계산
                target = now_kst.replace(hour=3, minute=0, second=0, microsecond=0)
                if now_kst >= target:
                    target = target + _td(days=1)
                wait_seconds = (target - now_kst).total_seconds()
                # 한 번에 너무 오래 자지 않도록 — 6시간씩 끊어서 sleep
                while wait_seconds > 0:
                    chunk = min(wait_seconds, 6 * 3600)
                    _t.sleep(chunk)
                    wait_seconds -= chunk
                # 백업 실행
                backup_script = os.path.join(APP_DIR, "deploy", "backup.sh")
                if os.path.exists(backup_script):
                    try:
                        # 백업 로그는 data/backup.log 에 누적
                        log_path = os.path.join(APP_DIR, "data", "backup.log")
                        with open(log_path, "a", encoding="utf-8") as logf:
                            _sp.run(
                                ["bash", backup_script],
                                stdout=logf, stderr=_sp.STDOUT,
                                timeout=1800,  # 30분 타임아웃
                            )
                        print(f"[backup worker] 백업 완료 ({_dt.now(kst).isoformat()})", flush=True)
                    except _sp.TimeoutExpired:
                        print("[backup worker] 백업 타임아웃 (30분 초과)", flush=True)
                    except Exception as e:
                        print(f"[backup worker] 백업 실행 에러: {e}", flush=True)
                else:
                    print(f"[backup worker] 백업 스크립트 없음: {backup_script}", flush=True)
            except Exception as e:
                print(f"[backup worker] loop error: {e}", flush=True)
                _t.sleep(3600)  # 에러 시 1시간 후 재시도
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
    '나와의 채팅' 모델.
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
    room_row = db.execute("SELECT invite_policy, type, created_by FROM rooms WHERE id=?", (room_id,)).fetchone()
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
    # 팀장(비ceo)은 본인이 만든 채널에 같은 부서원만 초대 가능 (대표 지시 2026-05-21)
    if me["role"] != "ceo" and _is_team_lead(me) and room_row["type"] == "channel":
        if room_row["created_by"] != me["id"]:
            return jsonify({"error": "팀장은 본인이 만든 채널에만 초대할 수 있습니다."}), 403
        my_nd = _norm_dept(me["department"])
        for uid in user_ids:
            ur = db.execute("SELECT department FROM users WHERE id=?", (uid,)).fetchone()
            if not ur or _norm_dept(ur["department"]) != my_nd:
                return jsonify({"error": "팀장은 같은 부서원만 채널에 초대할 수 있습니다."}), 403
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
    """멤버 내보내기. host 는 모든 멤버. sub_host 는 일반 member 만."""
    me = current_user()
    db = get_db()
    my_role = _my_room_role(db, room_id, me["id"])
    if my_role not in ('host', 'sub_host'):
        return jsonify({"error": "방장·부방장만 내보낼 수 있습니다"}), 403
    if user_id == me["id"]:
        return jsonify({"error": "본인은 /leave 로 나가기"}), 400
    target = db.execute("SELECT u.display_name, rm.role FROM room_members rm "
                        "JOIN users u ON u.id=rm.user_id "
                        "WHERE rm.room_id=? AND rm.user_id=?",
                        (room_id, user_id)).fetchone()
    if not target:
        return jsonify({"error": "멤버가 아님"}), 404
    if my_role == 'sub_host' and target["role"] in ('host', 'sub_host'):
        return jsonify({"error": "부방장은 방장·부방장을 내보낼 수 없습니다"}), 403
    db.execute("DELETE FROM room_members WHERE room_id=? AND user_id=?", (room_id, user_id))
    db.commit()
    now = datetime.now(timezone.utc).isoformat()
    sys_text = f"[{target['display_name']}] 님이 방에서 나갔습니다 (by {me['display_name']})"
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
    # 읽기 전 — 이 방에 내가 안 읽은(남이 보낸) 메시지가 있었는지 확인.
    #  있었다면 읽음 처리 후, 다른 기기(특히 백그라운드 휴대폰)의 이 방 알림을 clear 푸시로 닫는다.
    #  (안 읽은 게 없었으면 알림도 없으니 불필요한 푸시를 보내지 않음 — 푸시 남용/배터리 방지)
    prevrow = db.execute(
        "SELECT last_read_message_id FROM room_members WHERE room_id=? AND user_id=?",
        (room_id, me["id"]),
    ).fetchone()
    prev_read = (prevrow["last_read_message_id"] or 0) if prevrow else 0
    had_unread = db.execute(
        "SELECT 1 FROM messages WHERE room_id=? AND id>? AND user_id!=? "
        "AND (whisper_to_user_id IS NULL OR whisper_to_user_id=?) LIMIT 1",
        (room_id, prev_read, me["id"], me["id"]),
    ).fetchone() is not None
    last = db.execute("SELECT MAX(id) AS m FROM messages WHERE room_id=?", (room_id,)).fetchone()
    if last and last["m"]:
        now_iso = datetime.now(timezone.utc).isoformat()
        db.execute(
            "UPDATE room_members SET last_read_message_id=?, last_read_at=? WHERE room_id=? AND user_id=?",
            (last["m"], now_iso, room_id, me["id"]),
        )
        db.commit()
        # 같은 방의 다른 클라이언트에 읽음 알림 → 그쪽 UI에서 "안 읽음 N" 숫자 갱신
        socketio.emit("read_status", {
            "room_id": room_id,
            "user_id": me["id"],
            "last_read": last["m"],
            "last_read_at": now_iso,
        }, to=f"room_{room_id}")
    # 다른 기기의 이 방 OS 알림 자동 닫기 — 백그라운드 휴대폰은 소켓이 끊겨 푸시로만 닿으므로
    # clear 푸시를 보내 sw.js 가 tag=room_<id> 알림을 닫고 배지를 갱신하게 한다. (대표 지시 2026-05-20)
    #  ?clear=0 (활성 방 메시지 자동 읽음 등 같은 기기에서 이미 닫는 경우)이면 생략 — 푸시 낭비 방지.
    suppress_clear = (request.args.get("clear") == "0")
    if had_unread and PYWEBPUSH_OK and not suppress_clear:
        try:
            socketio.start_background_task(
                send_push_to_user, me["id"], "", "",
                url=None, tag=f"room_{room_id}", clear=True,
            )
        except Exception:
            pass
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
        SELECT rm.user_id, rm.last_read_message_id, rm.last_read_at,
               u.display_name, u.avatar_color, u.avatar_url, u.title, u.department
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
    일반 메신저식 동작 — 활성 방이 아니어도 모든 방의 new_message broadcast 를 받아
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
    # 온라인 진입 broadcast 는 곧이어 오는 on_presence(기기 종류 확정 후)에서 처리 →
    # PC 면 '가능', 휴대폰만이면 '휴대폰' 으로 정확히 표시 (connect 시점엔 기기 미상이라 깜빡임 방지).
    try:
        _presence_register(uid, request.sid, device="unknown", active=True)
    except Exception as e:
        print(f"[presence] register 실패: {e}")


@socketio.on("disconnect")
def on_disconnect():
    """SocketIO 연결 해제 시 presence 에서 제거.
    마지막 연결이 끊겼으면 다른 사용자에게 offline 알림."""
    uid = session.get("user_id")
    if not uid:
        return
    try:
        _presence_unregister(uid, request.sid)
        # 연결 해제 후 표시 상태 재계산 broadcast:
        #  · PC 끊기고 휴대폰 남음 → '가능'→'휴대폰' 으로 전환
        #  · 마지막 연결까지 끊김 → 푸시 있으면 '휴대폰', 없으면 '오프라인'
        with app.app_context():
            _broadcast_status_if_changed(uid)
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
        # 기기 종류(pc/mobile) 확정 → 표시 상태(가능/휴대폰) 변동 시 broadcast
        with app.app_context():
            _broadcast_status_if_changed(uid)
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


# ============================================================
# 스티커 — static/stickers/manifest.json 의 허용 파일 + 라벨
# ============================================================
STICKER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "stickers")
_STICKER_LABELS = None
def _sticker_labels():
    """{파일명: 라벨} dict. manifest.json 1회 로드 후 캐시."""
    global _STICKER_LABELS
    if _STICKER_LABELS is None:
        labels = {}
        try:
            with open(os.path.join(STICKER_DIR, "manifest.json"), encoding="utf-8") as fp:
                for item in json.load(fp):
                    f = item.get("file")
                    if f:
                        labels[f] = item.get("label", "")
        except Exception:
            labels = {}
        _STICKER_LABELS = labels
    return _STICKER_LABELS


@socketio.on("send")
def on_send(data):
    uid = session.get("user_id")
    if not uid or not isinstance(data, dict):
        return
    # 🛡️ Rate Limit — 분당 60개 메시지 (1초당 1개 평균. 스팸 차단)
    if not _check_rate_limit(uid, "send_message", max_per_minute=60):
        try:
            socketio.emit("rate_limited", {"action": "send_message", "message": "메시지 전송 속도 제한 — 1분에 60개"}, to=request.sid)
        except Exception:
            pass
        return
    room_id = data.get("room_id")
    content = (data.get("content") or "").strip()
    # 스티커 전송 — sticker=파일명. static/stickers 의 허용된 파일만 처리. content 는 라벨로 대체.
    sticker_file = (data.get("sticker") or "").strip()
    is_sticker = False
    if sticker_file:
        _labels = _sticker_labels()
        if sticker_file in _labels:
            is_sticker = True
            content = _labels.get(sticker_file) or "스티커"
        else:
            return  # 허용되지 않은 스티커 파일명 — 무시
    if not room_id:
        return
    if not is_sticker and not content:
        return
    if len(content) > 4000:
        content = content[:4000]
    # 인용 답장 — quoted_message_id (선택). 본 채널에 답글 + 원본 미니 카드.
    quoted_id = data.get("quoted_message_id")
    try:
        quoted_id = int(quoted_id) if quoted_id else None
    except (ValueError, TypeError):
        quoted_id = None
    # 귓속말 — whisper_to_user_id (선택). 송신자·수신자만 보이는 메시지.
    whisper_to = data.get("whisper_to_user_id")
    try:
        whisper_to = int(whisper_to) if whisper_to else None
    except (ValueError, TypeError):
        whisper_to = None
    if whisper_to == uid:
        whisper_to = None   # 자기 자신에게 귓속말은 의미 없음

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
        # 귓속말 대상이 같은 방 멤버인지 확인
        whisper_to_name = None
        if whisper_to:
            wrow = db.execute(
                "SELECT u.display_name FROM users u "
                " JOIN room_members rm ON rm.user_id=u.id "
                " WHERE u.id=? AND rm.room_id=?",
                (whisper_to, room_id),
            ).fetchone()
            if not wrow:
                whisper_to = None  # 같은 방이 아니면 귓속말 불가
            else:
                whisper_to_name = wrow["display_name"]
        now = datetime.now(timezone.utc).isoformat()
        kind = "sticker" if is_sticker else "text"
        cur = db.execute(
            "INSERT INTO messages (room_id, user_id, content, kind, created_at, quoted_message_id, whisper_to_user_id, file_name) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (room_id, uid, content, kind, now, quoted_id, whisper_to, sticker_file if is_sticker else None),
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
        "kind": kind,
        "created_at": now,
    }
    if is_sticker:
        payload["file_name"] = sticker_file
    if quoted_id:
        payload["quoted_message_id"] = quoted_id
        payload["quoted"] = quoted_meta
    if whisper_to:
        payload["whisper_to_user_id"] = whisper_to
        payload["whisper_to_name"] = whisper_to_name
    # 귓속말은 방 전체 broadcast 안 함 — 송신자·수신자 SID 에만 개별 emit
    if whisper_to:
        target_sids = set()
        with _user_conn_lock:
            for u_to_check in (uid, whisper_to):
                for sid, info in (_user_connections.get(u_to_check, {})).items():
                    target_sids.add(sid)
        for sid in target_sids:
            try:
                socketio.emit("new_message", payload, to=sid)
            except Exception as _e:
                pass
    else:
        socketio.emit("new_message", payload, to=f"room_{room_id}")

    # Web Push — 백그라운드 알림 (송신자 제외 모든 방 멤버)
    # 귓속말이면 푸시도 수신자 1명에게만 (송신자·다른 멤버 제외).
    if PYWEBPUSH_OK and whisper_to:
        # 귓속말 푸시
        with app.app_context():
            db3 = get_db()
            r3 = db3.execute("SELECT name FROM rooms WHERE id=?", (room_id,)).fetchone()
            room_name = r3["name"] if r3 else "채팅"
        if not _user_has_active_pc(whisper_to):
            import threading as _t
            _t.Thread(
                target=send_push_to_user,
                args=(whisper_to, f"🤫 {u['display_name']} 귓속말 ({room_name})", content[:120]),
                kwargs={"url": f"{BASE_PATH}/chat?room={room_id}", "tag": f"whisper_{room_id}_{uid}"},
                daemon=True,
            ).start()
        return  # 일반 푸시 흐름 스킵
    if PYWEBPUSH_OK:
        # 방 이름 조회 + 메시지에 멘션 있는지 검사
        with app.app_context():
            db2 = get_db()
            r = db2.execute("SELECT name, type FROM rooms WHERE id=?", (room_id,)).fetchone()
            room_name = r["name"] if r else "채팅"
        title = f"💬 {u['display_name']} ({room_name})"
        body = content[:120]
        # 비동기 스레드로 발송 (pywebpush는 HTTP 호출이라 블로킹)
        # tag 를 '방 단위'(room_N)로 — 같은 방 알림은 1개 카드로 합쳐짐. 새 메시지는
        # renotify 로 그 카드를 갱신·재알림. 알림창이 메시지 수만큼 쌓이는 문제 해결. (2026-05-20)
        # 앱 아이콘 배지 숫자는 sw.js 의 setAppBadge(payload.badge=안읽음 총합) 가 담당 → tag 와 무관.
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
    _start_backup_worker()  # 매일 새벽 3시(KST) 자동 백업 (대표 지시 2026-05-19)
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
