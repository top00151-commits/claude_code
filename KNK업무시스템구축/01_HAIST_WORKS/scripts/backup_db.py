#!/usr/bin/env python3
"""
HAIST WORKS — knk.db 자동 백업 스크립트
=========================================

사용법:
    python scripts/backup_db.py                # 기본: data/backups/ 에 날짜별 저장, 30일 보관
    python scripts/backup_db.py --keep 90      # 90일 보관
    python scripts/backup_db.py --dest D:/bak  # 외장 경로에 저장

권장 운영:
  Windows 작업 스케줄러 (매일 02:00):
    cmd /c python "C:\\...\\01_HAIST_WORKS\\scripts\\backup_db.py" --keep 60
  Linux cron:
    0 2 * * * cd /opt/haist_works && python scripts/backup_db.py --keep 60
"""
import argparse
import os
import shutil
import sys
import time
from datetime import datetime, timedelta, date

# Windows 콘솔 UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "data", "knk.db")


def do_backup(dest_dir: str, keep_days: int) -> str:
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] DB not found: {DB_PATH}")
        sys.exit(1)

    os.makedirs(dest_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(dest_dir, f"knk_{ts}.db")

    # sqlite3 backup API 사용 (lock-safe). 실패 시 copy로 폴백.
    try:
        import sqlite3
        src = sqlite3.connect(DB_PATH)
        dst = sqlite3.connect(out_path)
        with dst:
            src.backup(dst)
        dst.close()
        src.close()
    except Exception as e:
        print(f"[WARN] sqlite backup API 실패, copy 폴백: {e}")
        shutil.copy2(DB_PATH, out_path)

    size_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f"✓ 백업 완료: {out_path} ({size_mb:.2f} MB)")

    # 보관 기간 초과 파일 삭제
    if keep_days > 0:
        cutoff = time.time() - (keep_days * 86400)
        removed = 0
        for fn in os.listdir(dest_dir):
            if not fn.startswith("knk_") or not fn.endswith(".db"):
                continue
            fp = os.path.join(dest_dir, fn)
            if os.path.getmtime(fp) < cutoff:
                os.remove(fp)
                removed += 1
        if removed:
            print(f"  (보관기간 초과 {removed}개 삭제)")
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", type=int, default=30, help="보관 일수 (0=무기한)")
    ap.add_argument("--dest", type=str, default=None, help="백업 대상 디렉토리")
    args = ap.parse_args()

    dest = args.dest or os.path.join(BASE, "data", "backups")
    do_backup(dest, args.keep)
