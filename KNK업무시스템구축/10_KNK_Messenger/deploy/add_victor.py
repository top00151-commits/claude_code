"""KNK 메신저 테스트용 '빅터' 계정을 추가하고 모든 방에 멤버로 가입시킴.

목적: 메신저 검증 단계에서 빅터(AI 비서)가 각 방에 들어가
      안 읽음 뱃지·실시간 동기화 등을 테스트할 수 있게 환경 구성.

서버에서 실행:
    cd /opt/knk_messenger && .venv/bin/python3 deploy/add_victor.py

멱등 — 여러 번 실행해도 안전:
  - 빅터가 이미 있으면 그대로 사용
  - 방에 이미 멤버면 건너뜀
"""
import os
import sqlite3
import sys
from datetime import datetime, timezone

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(APP_DIR, "data", "messenger.db")

try:
    from werkzeug.security import generate_password_hash
except ImportError:
    sys.path.insert(0, os.path.join(APP_DIR, ".venv", "lib", "python3.8", "site-packages"))
    from werkzeug.security import generate_password_hash

USERNAME = "victor"
DISPLAY_NAME = "빅터"
PASSWORD = "victor8161"
ROLE = "staff"
AVATAR_COLOR = "#A5282C"  # KNK 레드

db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row

# 1) victor 사용자 존재 확인 / 등록
row = db.execute("SELECT id, display_name FROM users WHERE username=?", (USERNAME,)).fetchone()
now = datetime.now(timezone.utc).isoformat()

if row:
    victor_id = row["id"]
    print(f"[INFO] '{USERNAME}' 이미 존재: id={victor_id}, name={row['display_name']}")
else:
    cur = db.execute(
        "INSERT INTO users (username, password_hash, display_name, role, avatar_color, created_at, active) "
        "VALUES (?, ?, ?, ?, ?, ?, 1)",
        (USERNAME, generate_password_hash(PASSWORD), DISPLAY_NAME, ROLE, AVATAR_COLOR, now),
    )
    victor_id = cur.lastrowid
    db.commit()
    print(f"[OK]   '{USERNAME}' 등록: id={victor_id}, name={DISPLAY_NAME}, role={ROLE}")

# 2) 모든 방에 victor 를 멤버로 추가 (이미 멤버면 건너뜀)
rooms = db.execute("SELECT id, name, type FROM rooms ORDER BY id").fetchall()
added = 0
skipped = 0
for r in rooms:
    exists = db.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?", (r["id"], victor_id)
    ).fetchone()
    if exists:
        print(f"[SKIP] room {r['id']:>3} '{r['name']}' ({r['type']}) — 이미 멤버")
        skipped += 1
    else:
        # role 컬럼 (방장/부방장/멤버) 존재 여부 확인 후 적절히 INSERT
        cols = [c[1] for c in db.execute("PRAGMA table_info(room_members)").fetchall()]
        if "role" in cols:
            db.execute(
                "INSERT INTO room_members (room_id, user_id, joined_at, role) VALUES (?,?,?,?)",
                (r["id"], victor_id, now, "member"),
            )
        else:
            db.execute(
                "INSERT INTO room_members (room_id, user_id, joined_at) VALUES (?,?,?)",
                (r["id"], victor_id, now),
            )
        print(f"[OK]   room {r['id']:>3} '{r['name']}' ({r['type']}) — victor 추가")
        added += 1

db.commit()

print()
print(f"=== 완료 ===")
print(f"  방 총 {len(rooms)} 개 — 신규 추가 {added}, 건너뜀 {skipped}")
print(f"  victor 로그인 정보: username={USERNAME} / password={PASSWORD}")
print(f"  HTTP 주소: https://haist.knknara.co.kr/msg/login")
