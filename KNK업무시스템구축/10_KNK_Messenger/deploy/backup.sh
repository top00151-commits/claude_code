#!/usr/bin/env bash
# ============================================================
# KNK Messenger - 일일 백업 (cron으로 매일 03:00 실행)
# ============================================================
# 백업 대상:
#   - data/messenger.db (SQLite)
#   - data/uploads/    (사용자 업로드 파일)
#   - .env.production  (환경변수, 1주일에 1번)
# 보관 정책:
#   - DB: 30일
#   - uploads: 7일 (용량 부담)
#
# (선택) S3 업로드: 환경변수 KNK_BACKUP_S3 가 설정돼 있으면 sync.
# ============================================================
set -e

APP_DIR="/opt/knk_messenger"
DEST="$APP_DIR/backups"
DATE=$(date +%Y%m%d_%H%M)
mkdir -p "$DEST"

# DB 핫 백업 (sqlite3 .backup 명령은 동시 쓰기 안전)
sqlite3 "$APP_DIR/data/messenger.db" ".backup $DEST/messenger_$DATE.db"
echo "[$(date)] DB backup: messenger_$DATE.db ($(du -h "$DEST/messenger_$DATE.db" | cut -f1))"

# uploads 백업 (zip)
if [ -d "$APP_DIR/data/uploads" ]; then
  cd "$APP_DIR/data" && zip -qr "$DEST/uploads_$DATE.zip" uploads
  echo "[$(date)] Uploads backup: uploads_$DATE.zip ($(du -h "$DEST/uploads_$DATE.zip" | cut -f1))"
fi

# 정리: DB 30일, uploads 7일
find "$DEST" -name "messenger_*.db"  -mtime +30 -delete
find "$DEST" -name "uploads_*.zip"   -mtime +7  -delete

# (선택) S3 업로드
if [ -n "${KNK_BACKUP_S3:-}" ]; then
  if command -v aws >/dev/null 2>&1; then
    aws s3 sync "$DEST" "$KNK_BACKUP_S3" --exclude "backup.log" --exclude "cleanup.log"
    echo "[$(date)] S3 sync done: $KNK_BACKUP_S3"
  else
    echo "[$(date)] [경고] aws-cli 미설치, S3 업로드 건너뜀"
  fi
fi

# 디스크 사용량 보고 (60GB 중 80% 넘으면 경고)
USE=$(df "$APP_DIR" | awk 'NR==2 {gsub("%",""); print $5}')
if [ "$USE" -gt 80 ]; then
  echo "[$(date)] [경고] 디스크 사용률 ${USE}% — 백업 보관 기간 단축 검토"
fi
