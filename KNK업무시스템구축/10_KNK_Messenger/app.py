"""KNK Messenger — 사내 업무 전용 메신저 (1단계 MVP)

독립 프로젝트. 어느 정도 완성 후 HAIST WORKS와 SSO/사용자 API로 연결 예정.
"""
import os
import re
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
    render_template, jsonify, abort, g, send_from_directory,
)
from flask_socketio import SocketIO, emit, join_room as sio_join, leave_room as sio_leave
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "data", "messenger.db")
UPLOAD_DIR = os.path.join(APP_DIR, "data", "uploads")
PORT = int(os.environ.get("KNK_MSG_PORT", "5050"))
MAX_UPLOAD_MB = 25
MESSAGE_RETENTION_MONTHS = int(os.environ.get("KNK_MSG_RETENTION_MONTHS", "12"))
VAPID_PRIV_PATH = os.path.join(APP_DIR, "data", "vapid_private.pem")
VAPID_CONTACT = os.environ.get("KNK_MSG_CONTACT", "mailto:admin@knk.kr")


def vapid_private_key():
    if os.path.exists(VAPID_PRIV_PATH):
        with open(VAPID_PRIV_PATH, "r", encoding="utf-8") as f:
            return f.read()
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


def send_push_to_user(user_id, title, body, url=None, tag=None):
    """특정 사용자의 모든 push 구독에 알림 전송. 410/404는 만료로 간주하고 삭제."""
    if not PYWEBPUSH_OK:
        return 0
    priv = vapid_private_key()
    if not priv:
        return 0
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        subs = db.execute(
            "SELECT id, endpoint, p256dh, auth FROM push_subscriptions WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        sent = 0
        for s in subs:
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
                )
                sent += 1
            except WebPushException as e:
                code = getattr(e.response, "status_code", None) if e.response is not None else None
                if code in (404, 410):
                    db.execute("DELETE FROM push_subscriptions WHERE id = ?", (s["id"],))
                    db.commit()
            except Exception:
                pass
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
        send_push_to_user(m["user_id"], title, body, url=url, tag=tag)
ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "heic"}
ALLOWED_FILE_EXT = ALLOWED_IMAGE_EXT | {
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "hwp", "hwpx",
    "txt", "csv", "zip", "7z", "rar", "dwg", "dxf", "step", "stp", "stl",
    "mp4", "mov", "avi", "mkv", "mp3", "wav",
}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("KNK_MSG_SECRET", "knk-dev-secret-CHANGE-ME")
app.config["JSON_AS_ASCII"] = False
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # 정적 자원 캐시 비활성 (개발/베타 단계)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading", max_http_buffer_size=MAX_UPLOAD_MB * 1024 * 1024)


@app.after_request
def no_cache_html_js(resp):
    """모든 응답에 캐시 방지 헤더 — 브라우저가 항상 최신 코드 받도록."""
    if resp.mimetype in ("text/html", "application/javascript", "text/css", "application/json"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
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
    ]:
        if col not in existing_msg_cols:
            cur.execute(ddl)

    existing_item_cols = {row["name"] for row in cur.execute("PRAGMA table_info(items)").fetchall()}
    if "keep_forever" not in existing_item_cols:
        cur.execute("ALTER TABLE items ADD COLUMN keep_forever INTEGER DEFAULT 0")
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
            cur.execute(
                "INSERT INTO room_members (room_id, user_id, joined_at) VALUES (?,?,?)",
                (room_id, uid, now),
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
                cur.execute(
                    "INSERT INTO room_members (room_id, user_id, joined_at) VALUES (?,?,?)",
                    (rid, uid, now),
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
    return redirect(url_for("chat") if current_user() else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        p = request.form.get("password") or ""
        row = get_db().execute("SELECT * FROM users WHERE username = ?", (u,)).fetchone()
        if row and check_password_hash(row["password_hash"], p):
            session.clear()
            session["user_id"] = row["id"]
            return redirect(url_for("chat"))
        return render_template("login.html", error="아이디 또는 비밀번호가 올바르지 않습니다.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/chat")
@login_required
def chat():
    return render_template("chat.html", me=current_user())


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", me=current_user())


# ---------- API ----------
@app.route("/sw.js")
def serve_sw():
    """Service Worker는 루트에서 서빙해야 전체 scope('/') 인정됨."""
    return send_from_directory(os.path.join(APP_DIR, "static"), "sw.js", mimetype="application/javascript")


@app.route("/manifest.json")
def serve_manifest():
    return send_from_directory(os.path.join(APP_DIR, "static"), "manifest.json", mimetype="application/manifest+json")


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
        SELECT r.id, r.name, r.type, r.created_at,
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
         ORDER BY (last_at IS NULL), last_at DESC, r.id DESC
    """, (me["id"], me["id"])).fetchall()

    out = []
    for r in rows:
        d = dict(r)
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
    cur = db.execute(
        "INSERT INTO rooms (name, type, created_by, created_at) VALUES (?,?,?,?)",
        (name, "item", me["id"], now),
    )
    rid = cur.lastrowid
    db.execute("""
        INSERT INTO items (room_id, code, name, customer, status, due_date, description,
                           created_by, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (rid, code, name, customer, status, due_date, description, me["id"], now, now))
    for uid in user_ids:
        db.execute(
            "INSERT INTO room_members (room_id, user_id, joined_at) VALUES (?,?,?)",
            (rid, uid, now),
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
    rows = db.execute("""
        SELECT m.id, m.content, m.kind, m.created_at,
               m.file_path, m.file_name, m.file_size, m.file_mime,
               u.id AS user_id, u.display_name, u.avatar_color
          FROM messages m
          JOIN users u ON u.id = m.user_id
         WHERE m.room_id = ?
         ORDER BY m.id ASC
    """, (room_id,)).fetchall()
    out = [dict(r) for r in rows]
    # 반응 batch 로드
    if out:
        ids = tuple(r["id"] for r in out)
        placeholders = ",".join("?" for _ in ids)
        rxs = db.execute(f"""
            SELECT mr.message_id, mr.emoji, mr.user_id, u.display_name
              FROM message_reactions mr JOIN users u ON u.id = mr.user_id
             WHERE mr.message_id IN ({placeholders})
        """, ids).fetchall()
        rxmap = {}
        for r in rxs:
            rxmap.setdefault(r["message_id"], []).append({"emoji": r["emoji"], "user_id": r["user_id"], "display_name": r["display_name"]})
        for m in out:
            m["reactions"] = rxmap.get(m["id"], [])
    return jsonify(out)


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
            kwargs={"url": f"/chat?room={room_id}", "tag": f"req_{qid}"},
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
        return jsonify({"error": "subscription 형식 오류"}), 400
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
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
    return jsonify({"ok": True})


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
    me = current_user()
    sent = send_push_to_user(me["id"], "🔔 KNK 메신저 테스트", "푸시 알림이 정상 작동합니다.", url="/chat", tag="test")
    return jsonify({"sent": sent})


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


@app.route("/api/search")
@login_required
def api_search():
    me = current_user()
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify([])
    fts_q = fts_query_safe(q)
    if not fts_q:
        return jsonify([])
    db = get_db()
    msg_rows = db.execute("""
        SELECT m.id, m.content, m.kind, m.created_at, m.room_id, m.file_path, m.file_name,
               u.display_name, u.avatar_color,
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
         ORDER BY m.id DESC
         LIMIT 30
    """, (me["id"], fts_q)).fetchall()

    # 아이템 메타 검색 (LIKE) — name, customer, code, description
    tokens = re.findall(r"[\w가-힣]+", q)
    item_results = []
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
        "INSERT INTO rooms (name, type, created_by, created_at) VALUES (?,?,?,?)",
        (name, type_, me["id"], now),
    )
    rid = cur.lastrowid
    for uid in user_ids:
        db.execute(
            "INSERT INTO room_members (room_id, user_id, joined_at) VALUES (?,?,?)",
            (rid, uid, now),
        )
    db.commit()
    return jsonify({"id": rid, "existing": False})


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
    return jsonify({"ok": True})


# ---------- SocketIO ----------
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

    with app.app_context():
        db = get_db()
        if not db.execute(
            "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?",
            (room_id, uid),
        ).fetchone():
            return
        now = datetime.now(timezone.utc).isoformat()
        cur = db.execute(
            "INSERT INTO messages (room_id, user_id, content, kind, created_at) VALUES (?,?,?,?,?)",
            (room_id, uid, content, "text", now),
        )
        mid = cur.lastrowid
        db.commit()
        u = db.execute(
            "SELECT display_name, avatar_color FROM users WHERE id=?", (uid,)
        ).fetchone()

    socketio.emit("new_message", {
        "id": mid,
        "room_id": room_id,
        "user_id": uid,
        "display_name": u["display_name"],
        "avatar_color": u["avatar_color"],
        "content": content,
        "kind": "text",
        "created_at": now,
    }, to=f"room_{room_id}")

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
            kwargs={"url": f"/chat?room={room_id}", "tag": f"room_{room_id}"},
            daemon=True,
        ).start()


if __name__ == "__main__":
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    init_db()
    print(f" * KNK Messenger running on http://0.0.0.0:{PORT}")
    socketio.run(app, host="0.0.0.0", port=PORT, debug=False, allow_unsafe_werkzeug=True)
