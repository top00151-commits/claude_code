# -*- coding: utf-8 -*-
"""WORKS knk.db → kmail mail.db 메일 데이터 이전 (cutover 2-4, 대표 지시 2026-06-22).

- WORKS 원본(knk.db)은 **읽기 전용**(절대 안 건드림). kmail mail.db 에만 INSERT.
- user_id 매핑 = login_id(사번) 기준 1:1. 메일 소유자만 kmail users 에 생성(현재 대표 1명).
- 기본 dry-run(분석만). --apply 로 실제 복사. 멱등 아님 → apply 는 '빈 kmail mail.db'에 1회만.
- 검증환경(로컬 복사본)서 먼저 돌려보고, 결과 확인 후 같은 스크립트로 실제 mail.db 생성.

사용:
  python migrate_mail_to_kmail.py --works knk.db --kmail mail.db            # dry-run(분석)
  python migrate_mail_to_kmail.py --works knk.db --kmail mail.db --apply    # 실제 복사
"""
import sqlite3
import argparse
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 공통 컬럼(양쪽 동일). WORKS 추가 컬럼(dedup_hash·dup_count·is_blocked·risk_level·risk_note)은 제외(무시).
MSG_COLS = ["user_id", "direction", "from_email", "from_name", "to_email", "cc", "bcc",
            "subject", "body_text", "body_html", "category", "lang", "summary",
            "is_read", "is_starred", "is_deleted", "raw_size", "received_at", "read_at",
            "deleted_at", "created_at"]
ATT_COLS = ["mail_id", "filename", "mime", "size", "path", "content_id", "is_inline", "data", "created_at"]

# kmail(15_KNK_Mail/app/db.py) 메일 관련 스키마 — --ensure-schema 로 빈 mail.db 생성 시 사용.
# (실제 적용 때는 kmail의 진짜 mail.db 를 쓰지만, 컨테이너 안 리허설용으로 동일 스키마를 만든다.)
KMAIL_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT, employee_no TEXT, login_id TEXT, password TEXT,
    name TEXT, name_en TEXT, name_vi TEXT, email TEXT, phone TEXT, dept_code TEXT,
    team_id INTEGER, rank TEXT, role TEXT DEFAULT 'member', entity TEXT, is_active INTEGER DEFAULT 1,
    password_version INTEGER DEFAULT 1, lang TEXT DEFAULT 'ko', created_at TEXT DEFAULT (datetime('now','localtime')));
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_empno ON users(employee_no);
CREATE TABLE IF NOT EXISTS mail_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, direction TEXT DEFAULT 'in',
    from_email TEXT, from_name TEXT, to_email TEXT, cc TEXT, bcc TEXT, subject TEXT,
    body_text TEXT, body_html TEXT, category TEXT DEFAULT '일반', lang TEXT, summary TEXT,
    is_read INTEGER DEFAULT 0, is_starred INTEGER DEFAULT 0, is_deleted INTEGER DEFAULT 0,
    raw_size INTEGER DEFAULT 0, received_at TEXT DEFAULT (datetime('now','localtime')),
    read_at TEXT, deleted_at TEXT, created_at TEXT DEFAULT (datetime('now','localtime')));
CREATE INDEX IF NOT EXISTS idx_mailmsg_user ON mail_messages(user_id, is_deleted, received_at DESC);
CREATE TABLE IF NOT EXISTS mail_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT, mail_id INTEGER, filename TEXT, mime TEXT,
    size INTEGER DEFAULT 0, path TEXT, content_id TEXT, is_inline INTEGER DEFAULT 0, data BLOB,
    created_at TEXT DEFAULT (datetime('now','localtime')));
CREATE INDEX IF NOT EXISTS idx_mailatt_mail ON mail_attachments(mail_id);
CREATE TABLE IF NOT EXISTS mail_aliases (address TEXT PRIMARY KEY, user_id INTEGER, created_at TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS mail_signatures (user_id INTEGER PRIMARY KEY, body TEXT, updated_at TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS mail_rules (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, match_type TEXT, pattern TEXT, category TEXT, enabled INTEGER DEFAULT 1, created_at TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS mail_fetch_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, owner_user_id INTEGER UNIQUE, label TEXT, protocol TEXT DEFAULT 'pop3',
    host TEXT, port INTEGER DEFAULT 995, use_ssl INTEGER DEFAULT 1, username TEXT, password_enc TEXT,
    last_uid INTEGER DEFAULT 0, enabled INTEGER DEFAULT 1, last_run TEXT, last_status TEXT, last_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now','localtime')));
"""


def colnames(con, table):
    return {r[1] for r in con.execute("PRAGMA table_info(%s)" % table).fetchall()}


def copy_filtered(src_row, cols, remap):
    return [remap.get(c, lambda v: v)(src_row[c]) if c in remap else src_row[c] for c in cols]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", required=True, help="WORKS knk.db (읽기 전용)")
    ap.add_argument("--kmail", required=True, help="kmail mail.db (INSERT 대상)")
    ap.add_argument("--apply", action="store_true", help="실제 복사(미지정=dry-run 분석만)")
    ap.add_argument("--ensure-schema", action="store_true", help="kmail mail.db 에 메일 스키마 없으면 생성(빈 DB 새로 만들 때)")
    args = ap.parse_args()

    mode = "APPLY(실제 복사)" if args.apply else "DRY-RUN(분석만)"
    print("===== 메일 이전 %s =====" % mode)
    print("WORKS(읽기): %s" % args.works)
    print("kmail(쓰기): %s" % args.kmail)

    w = sqlite3.connect(args.works)
    w.row_factory = sqlite3.Row
    k = sqlite3.connect(args.kmail)
    k.row_factory = sqlite3.Row

    if args.ensure_schema:
        k.executescript(KMAIL_SCHEMA)
        k.commit()
        print("[스키마] kmail 메일 스키마 보장(없으면 생성)")

    # 안전: kmail 이 비어있는지 확인(중복 적재 방지)
    kn = k.execute("SELECT COUNT(*) FROM mail_messages").fetchone()[0]
    if kn > 0 and args.apply:
        print("[중단] kmail mail_messages 가 이미 %d건 — 빈 DB에만 적용하세요(중복 방지)." % kn)
        return 2
    print("[사전] kmail 기존 메일: %d건" % kn)

    # 1) 메일 소유자 → kmail user 매핑(login_id 기준)
    owners = w.execute(
        "SELECT DISTINCT m.user_id uid, u.login_id lid, u.email em, u.name nm, "
        "u.role rl, u.rank rk, u.lang lg FROM mail_messages m "
        "LEFT JOIN users u ON u.id=m.user_id").fetchall()
    print("\n[1] 메일 소유자 %d명" % len(owners))
    idmap = {}
    kcols = colnames(k, "users")
    for o in owners:
        lid = (o["lid"] or "").strip()
        if not lid:
            print("  ⚠ uid=%s login_id 없음 → 미매핑(메일 보류)" % o["uid"])
            continue
        kr = k.execute("SELECT id FROM users WHERE login_id=? OR employee_no=?", (lid, lid)).fetchone()
        if kr:
            idmap[o["uid"]] = kr["id"]
            print("  ✓ 매핑 works:%s → kmail:%s (login_id=%s, %s)" % (o["uid"], kr["id"], lid, o["nm"]))
        elif args.apply:
            # kmail users 에 생성(employee_no=login_id=사번, password=SSO sentinel)
            fields = {"employee_no": lid, "login_id": lid, "password": "!sso",
                      "name": o["nm"], "email": o["em"], "role": o["rl"] or "member",
                      "rank": o["rk"], "lang": o["lg"] or "ko", "is_active": 1}
            use = {kk: vv for kk, vv in fields.items() if kk in kcols}
            cur = k.execute("INSERT INTO users(%s) VALUES(%s)" % (",".join(use), ",".join("?" * len(use))),
                            list(use.values()))
            idmap[o["uid"]] = cur.lastrowid
            print("  + kmail 사용자 생성: login_id=%s name=%s → kmail:%s" % (lid, o["nm"], cur.lastrowid))
        else:
            print("  · kmail 사용자 없음 login_id=%s name=%s → (apply 시 생성)" % (lid, o["nm"]))

    # 2) 메일 복사
    msgs = w.execute("SELECT * FROM mail_messages ORDER BY id").fetchall()
    mailmap = {}
    todo = sum(1 for m in msgs if m["user_id"] in idmap or not args.apply)
    print("\n[2] 메일 %d건 (복사 대상: 매핑된 소유자 것만)" % len(msgs))
    copied = skipped = 0
    for m in msgs:
        if m["user_id"] not in idmap:
            if args.apply:
                skipped += 1
                continue
        if args.apply:
            vals = [idmap[m["user_id"]] if c == "user_id" else m[c] for c in MSG_COLS]
            cur = k.execute("INSERT INTO mail_messages(%s) VALUES(%s)" % (
                ",".join(MSG_COLS), ",".join("?" * len(MSG_COLS))), vals)
            mailmap[m["id"]] = cur.lastrowid
        copied += 1
    print("  복사:%d  보류(미매핑):%d" % (copied, skipped))

    # 3) 첨부 복사(mail_id 재매핑)
    atts = w.execute("SELECT * FROM mail_attachments ORDER BY id").fetchall()
    acopied = 0
    for a in atts:
        if args.apply:
            if a["mail_id"] not in mailmap:
                continue
            vals = [mailmap[a["mail_id"]] if c == "mail_id" else a[c] for c in ATT_COLS]
            k.execute("INSERT INTO mail_attachments(%s) VALUES(%s)" % (
                ",".join(ATT_COLS), ",".join("?" * len(ATT_COLS))), vals)
        acopied += 1
    print("[3] 첨부 %d건 %s" % (len(atts), "복사" if args.apply else "(dry-run)"))

    # 4) 부가 테이블(user_id 재매핑) — aliases·signatures·rules·fetch_accounts
    def copy_table(table, idcol):
        if table not in {r[0] for r in w.execute("SELECT name FROM sqlite_master WHERE type='table'")}:
            return
        rows = w.execute("SELECT * FROM %s" % table).fetchall()
        cols = [c for c in colnames(w, table) if c in colnames(k, table) and c != "id"]
        n = 0
        for r in rows:
            uidv = r[idcol] if idcol in r.keys() else None
            if uidv is not None and uidv not in idmap:
                continue  # 미매핑 소유자 건 보류
            if args.apply:
                vals = [idmap.get(r[c], r[c]) if c == idcol else r[c] for c in cols]
                try:
                    k.execute("INSERT INTO %s(%s) VALUES(%s)" % (table, ",".join(cols), ",".join("?" * len(cols))), vals)
                except sqlite3.IntegrityError:
                    pass  # PK 중복(예: signatures user_id PK) 무시
            n += 1
        print("[4] %s %d건 %s" % (table, n, "복사" if args.apply else "(dry-run)"))

    copy_table("mail_aliases", "user_id")
    copy_table("mail_signatures", "user_id")
    copy_table("mail_rules", "user_id")
    copy_table("mail_fetch_accounts", "owner_user_id")

    if args.apply:
        k.commit()
        print("\n[검증]")
        print("  kmail mail_messages:", k.execute("SELECT COUNT(*) FROM mail_messages").fetchone()[0])
        print("  kmail mail_attachments:", k.execute("SELECT COUNT(*) FROM mail_attachments").fetchone()[0])
        print("  kmail users:", k.execute("SELECT COUNT(*) FROM users").fetchone()[0])
        try:
            mb = (k.execute("SELECT COALESCE(SUM(LENGTH(data)),0) FROM mail_attachments").fetchone()[0] or 0) / 1048576.0
            print("  kmail 첨부 용량:", round(mb, 1), "MB")
        except Exception:
            pass
        print("  → WORKS 원본은 그대로(읽기만 함).")
    else:
        print("\n[DRY-RUN 끝] 위 매핑·건수가 맞으면 --apply 로 실제 복사하세요.")

    w.close()
    k.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
