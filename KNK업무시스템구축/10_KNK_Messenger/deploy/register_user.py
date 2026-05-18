#!/usr/bin/env python3
"""KNK 메신저 사용자 등록/수정 헬퍼 (CLI).

사용 예:
    # 새 사용자 등록
    python3 register_user.py add --username kim --password knk1234 --name "김정락" --role ceo

    # 비밀번호 초기화
    python3 register_user.py reset --username kim --password newpass1234

    # 비활성화 (로그인 차단)
    python3 register_user.py disable --username kim

    # 활성화
    python3 register_user.py enable --username kim

    # 목록
    python3 register_user.py list

    # 역할 변경
    python3 register_user.py role --username kim --role manager

서버에서 직접 실행 (SSH 후 /opt/knk_messenger/deploy/register_user.py).
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone

# Path resolution — 서버에 배포되면 /opt/knk_messenger 기준
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(APP_DIR, "data", "messenger.db")

try:
    from werkzeug.security import generate_password_hash
except ImportError:
    # venv 활성화 안 됐을 때 fallback
    sys.path.insert(0, os.path.join(APP_DIR, "venv", "lib", "python3.8", "site-packages"))
    from werkzeug.security import generate_password_hash

VALID_ROLES = {"ceo", "manager", "staff"}
DEFAULT_COLORS = [
    "#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6",
    "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1",
]


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def ensure_active_column(db):
    """active 컬럼 없으면 추가 (마이그레이션). 기존 사용자는 모두 active=1."""
    cols = [r[1] for r in db.execute("PRAGMA table_info(users)").fetchall()]
    if "active" not in cols:
        db.execute("ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1")
        db.commit()
        print("[migration] users.active 컬럼 추가됨")


def cmd_add(args):
    db = get_db()
    ensure_active_column(db)
    if db.execute("SELECT 1 FROM users WHERE username=?", (args.username,)).fetchone():
        print(f"[FAIL] 이미 존재: {args.username}")
        return 1
    if args.role not in VALID_ROLES:
        print(f"[FAIL] role 은 {VALID_ROLES} 중 하나")
        return 1
    color = args.color or DEFAULT_COLORS[hash(args.username) % len(DEFAULT_COLORS)]
    now = datetime.now(timezone.utc).isoformat()
    cur = db.execute(
        "INSERT INTO users (username, password_hash, display_name, role, avatar_color, created_at, active) "
        "VALUES (?,?,?,?,?,?,1)",
        (args.username, generate_password_hash(args.password), args.name, args.role, color, now),
    )
    db.commit()
    print(f"[OK] 등록됨: id={cur.lastrowid} username={args.username} name={args.name} role={args.role}")
    return 0


def cmd_reset(args):
    db = get_db()
    row = db.execute("SELECT id FROM users WHERE username=?", (args.username,)).fetchone()
    if not row:
        print(f"[FAIL] 없음: {args.username}")
        return 1
    db.execute("UPDATE users SET password_hash=? WHERE username=?",
               (generate_password_hash(args.password), args.username))
    db.commit()
    print(f"[OK] 비번 초기화: {args.username}")
    return 0


def cmd_disable(args):
    db = get_db()
    ensure_active_column(db)
    r = db.execute("UPDATE users SET active=0 WHERE username=?", (args.username,))
    db.commit()
    print(f"[OK] 비활성화 ({r.rowcount} 영향): {args.username}" if r.rowcount else f"[FAIL] 없음")
    return 0 if r.rowcount else 1


def cmd_enable(args):
    db = get_db()
    ensure_active_column(db)
    r = db.execute("UPDATE users SET active=1 WHERE username=?", (args.username,))
    db.commit()
    print(f"[OK] 활성화: {args.username}" if r.rowcount else f"[FAIL] 없음")
    return 0 if r.rowcount else 1


def cmd_role(args):
    if args.role not in VALID_ROLES:
        print(f"[FAIL] role 은 {VALID_ROLES}")
        return 1
    db = get_db()
    r = db.execute("UPDATE users SET role=? WHERE username=?", (args.role, args.username))
    db.commit()
    print(f"[OK] role 변경: {args.username} → {args.role}" if r.rowcount else f"[FAIL] 없음")
    return 0 if r.rowcount else 1


def cmd_list(args):
    db = get_db()
    ensure_active_column(db)
    rows = db.execute(
        "SELECT id, username, display_name, role, active, created_at FROM users ORDER BY id"
    ).fetchall()
    print(f"{'ID':>4} {'USERNAME':<14} {'NAME':<16} {'ROLE':<8} {'ACTIVE':<7} CREATED")
    print("-" * 70)
    for r in rows:
        print(f"{r['id']:>4} {r['username']:<14} {r['display_name']:<16} {r['role']:<8} "
              f"{'YES' if r['active'] else 'NO':<7} {r['created_at'][:10]}")
    print(f"\n총 {len(rows)} 명 (활성 {sum(1 for r in rows if r['active'])}, 비활성 {sum(1 for r in rows if not r['active'])})")
    return 0


def main():
    p = argparse.ArgumentParser(description="KNK 메신저 사용자 관리")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="사용자 등록")
    a.add_argument("--username", required=True)
    a.add_argument("--password", required=True)
    a.add_argument("--name", required=True, help="표시 이름")
    a.add_argument("--role", default="staff", choices=list(VALID_ROLES))
    a.add_argument("--color", default=None, help="아바타 색 (HEX, 예: #3b82f6)")

    r = sub.add_parser("reset", help="비밀번호 초기화")
    r.add_argument("--username", required=True)
    r.add_argument("--password", required=True)

    d = sub.add_parser("disable", help="비활성화")
    d.add_argument("--username", required=True)

    e = sub.add_parser("enable", help="활성화")
    e.add_argument("--username", required=True)

    ro = sub.add_parser("role", help="역할 변경")
    ro.add_argument("--username", required=True)
    ro.add_argument("--role", required=True, choices=list(VALID_ROLES))

    sub.add_parser("list", help="목록")

    args = p.parse_args()
    handler = {
        "add": cmd_add, "reset": cmd_reset, "disable": cmd_disable,
        "enable": cmd_enable, "role": cmd_role, "list": cmd_list,
    }[args.cmd]
    sys.exit(handler(args))


if __name__ == "__main__":
    main()
