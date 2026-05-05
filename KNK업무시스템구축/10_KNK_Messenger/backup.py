"""KNK Messenger 백업 — Python 기반 (Windows 한글 경로 안전).

매일 새벽 3시 작업스케줄러가 호출.
- DB sqlite backup (online, 락 없이)
- uploads 폴더 zip 압축
- 14일 이상 된 백업 자동 삭제
"""
import os
import sys
import sqlite3
import shutil
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

APP_DIR = Path(__file__).resolve().parent
DB = APP_DIR / "data" / "messenger.db"
UPLOADS = APP_DIR / "data" / "uploads"
BACKUP_DIR = APP_DIR / "backups"
RETENTION_DAYS = 14


def main():
    BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")

    # 1. DB 백업
    out_db = BACKUP_DIR / f"messenger_{stamp}.db"
    if not DB.exists():
        print(f"[경고] DB 파일 없음: {DB}")
        return 1
    src = sqlite3.connect(str(DB))
    dst = sqlite3.connect(str(out_db))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    print(f"[OK] DB 백업: {out_db.name} ({out_db.stat().st_size:,} B)")

    # 2. uploads 폴더 zip 압축
    if UPLOADS.exists() and any(UPLOADS.rglob("*")):
        out_zip = BACKUP_DIR / f"uploads_{stamp}.zip"
        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in UPLOADS.rglob("*"):
                if p.is_file():
                    zf.write(p, p.relative_to(UPLOADS.parent))
        print(f"[OK] 첨부 백업: {out_zip.name} ({out_zip.stat().st_size:,} B)")

    # 3. 오래된 백업 정리
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    deleted = 0
    for p in BACKUP_DIR.iterdir():
        if p.suffix in (".db", ".zip"):
            mtime = datetime.fromtimestamp(p.stat().st_mtime)
            if mtime < cutoff:
                p.unlink()
                deleted += 1
    if deleted:
        print(f"[OK] {RETENTION_DAYS}일 초과 백업 {deleted}개 삭제")

    print(f"[완료] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
