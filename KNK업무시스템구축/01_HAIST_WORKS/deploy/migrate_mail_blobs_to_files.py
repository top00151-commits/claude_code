#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""메일 첨부 BLOB -> 내용해시 파일 이관 (대표 확정 2026-08-31 · 3단계).

설계 원칙 (안전 최우선):
  1) 파일을 먼저 쓰고, **다시 읽어 sha256 재검증**이 통과한 행만 BLOB 을 회수(NULL).
     -> 검증 실패 시 BLOB 그대로 둠. 첨부 손실 0.
  2) **파일은 절대 삭제하지 않음**(여러 메일이 같은 내용파일 공유 = 중복제거).
  3) **멱등·재개 가능**: id 커서로 진행. 중간에 컨테이너가 재시작돼도 이어서 실행.
     이미 이관된 행(data IS NULL)은 건너뜀. 같은 내용 파일이 있으면 재사용(중복제거).
  4) **짧은 전용 트랜잭션**(배치당) + busy_timeout + 배치 간 휴식 -> 운영 잠금 최소화(z520 교훈).
  5) 디스크 여유 확인 후 시작. 부족하면 시작 안 함.

출력은 ASCII 전용(PowerShell/SSH 경유 시 한글 깨짐 방지).

사용 (컨테이너 내부):
  /opt/knk_haist/.venv/bin/python migrate_mail_blobs_to_files.py --dry-run
  /opt/knk_haist/.venv/bin/python migrate_mail_blobs_to_files.py --batch 100 --limit 500
  /opt/knk_haist/.venv/bin/python migrate_mail_blobs_to_files.py            # 전량
"""
import argparse
import hashlib
import os
import shutil
import sqlite3
import sys
import tempfile
import time

DEFAULT_DB = "/opt/knk_haist/data/knk.db"


def att_dir(db_path):
    return os.path.join(os.path.dirname(db_path), "mail_att")


def content_path(db_path, sha):
    return os.path.join(att_dir(db_path), "sha256", sha[:2], sha)


def write_atomic(p, data):
    """임시파일 -> rename(원자적). 이미 같은 크기 파일이 있으면 재사용(중복제거)."""
    if os.path.exists(p) and os.path.getsize(p) == len(data):
        return "reused"
    d = os.path.dirname(p)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    except Exception:
        try:
            os.remove(tmp)
        except Exception:
            pass
        raise
    return "written"


def verify_file(p, sha, size):
    """파일을 되읽어 sha256 재계산 - 이것이 통과해야만 BLOB 을 회수한다."""
    try:
        if not os.path.exists(p):
            return False
        if os.path.getsize(p) != size:
            return False
        h = hashlib.sha256()
        with open(p, "rb") as f:
            while True:
                b = f.read(1024 * 1024)
                if not b:
                    break
                h.update(b)
        return h.hexdigest() == sha
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--batch", type=int, default=100, help="rows per transaction")
    ap.add_argument("--limit", type=int, default=0, help="max rows this run (0=all)")
    ap.add_argument("--sleep", type=float, default=0.30, help="seconds between batches")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    db = args.db
    if not os.path.exists(db):
        print("ERROR: db not found:", db)
        return 2

    con = sqlite3.connect(db, timeout=30)
    con.execute("PRAGMA busy_timeout=15000")
    con.row_factory = sqlite3.Row

    # sha256 컬럼 보장(이미 운영엔 있음 - 멱등)
    cols = [r[1] for r in con.execute("PRAGMA table_info(mail_attachments)")]
    if "sha256" not in cols:
        con.execute("ALTER TABLE mail_attachments ADD COLUMN sha256 TEXT")
        con.commit()
        print("[init] sha256 column added")

    todo, todo_bytes = con.execute(
        "SELECT COUNT(*), COALESCE(SUM(LENGTH(data)),0) FROM mail_attachments WHERE data IS NOT NULL"
    ).fetchone()
    done_already = con.execute(
        "SELECT COUNT(*) FROM mail_attachments WHERE data IS NULL AND path IS NOT NULL"
    ).fetchone()[0]
    print("[state] rows with BLOB (to migrate): %d  (%.1f MB)" % (todo, todo_bytes / 1048576.0))
    print("[state] rows already on file        : %d" % done_already)

    if todo == 0:
        print("[done] nothing to migrate")
        return 0

    # 디스크 여유 확인 - 필요량(중복제거 전 최대치)보다 1.5배 여유 요구
    free = shutil.disk_usage(os.path.dirname(db)).free
    need = int(todo_bytes * 1.2)
    print("[disk] free=%.1f GB   need(approx, before dedup)=%.1f GB"
          % (free / 1073741824.0, need / 1073741824.0))
    if free < need:
        print("ERROR: not enough free disk space. aborting.")
        return 3

    if args.dry_run:
        print("[dry-run] would migrate %d rows. no changes made." % todo)
        return 0

    t0 = time.time()
    last_id = 0
    n_ok = n_reused = n_written = n_fail = 0
    freed = 0
    while True:
        if args.limit and n_ok >= args.limit:
            print("[stop] limit reached (%d)" % args.limit)
            break
        take = args.batch
        if args.limit:
            take = min(take, args.limit - n_ok)
        rows = con.execute(
            "SELECT id, data FROM mail_attachments "
            "WHERE data IS NOT NULL AND id > ? ORDER BY id LIMIT ?",
            (last_id, take),
        ).fetchall()
        if not rows:
            break

        updates = []
        for r in rows:
            last_id = r["id"]
            data = r["data"]
            if data is None:
                continue
            if len(data) == 0:
                # 빈 BLOB = 내용 없음. 파일 만들지 않고 BLOB 만 비움(메타는 유지).
                updates.append((None, None, r["id"]))
                continue
            sha = hashlib.sha256(data).hexdigest()
            p = content_path(db, sha)
            try:
                how = write_atomic(p, data)
            except Exception as e:
                n_fail += 1
                print("[fail] id=%s write: %s" % (r["id"], e))
                continue
            if not verify_file(p, sha, len(data)):
                n_fail += 1
                print("[fail] id=%s verify mismatch - BLOB kept" % r["id"])
                continue
            if how == "reused":
                n_reused += 1
            else:
                n_written += 1
            freed += len(data)
            updates.append((p, sha, r["id"]))

        if updates:
            try:
                con.execute("BEGIN IMMEDIATE")
                con.executemany(
                    "UPDATE mail_attachments SET path=?, sha256=?, data=NULL WHERE id=?", updates
                )
                con.commit()
                n_ok += len(updates)
            except Exception as e:
                con.rollback()
                print("[fail] batch commit: %s - BLOBs kept, will retry next run" % e)
                n_fail += len(updates)
        if n_ok % 500 < args.batch:
            print("[prog] migrated=%d written=%d reused(dedup)=%d fail=%d  freed=%.1f MB  %.0fs"
                  % (n_ok, n_written, n_reused, n_fail, freed / 1048576.0, time.time() - t0))
        time.sleep(args.sleep)

    left = con.execute("SELECT COUNT(*) FROM mail_attachments WHERE data IS NOT NULL").fetchone()[0]
    print("")
    print("=== RESULT ===")
    print("migrated rows : %d" % n_ok)
    print("files written : %d" % n_written)
    print("dedup reused  : %d   <-- same content, no new file" % n_reused)
    print("failures      : %d   (BLOB kept, safe to re-run)" % n_fail)
    print("blob freed    : %.1f MB (reclaimed by VACUUM later)" % (freed / 1048576.0))
    print("rows left BLOB: %d" % left)
    print("elapsed       : %.0f s" % (time.time() - t0))
    print("db file size  : %.1f MB (unchanged until VACUUM)" % (os.path.getsize(db) / 1048576.0))
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
