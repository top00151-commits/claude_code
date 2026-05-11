#!/bin/bash
# ============================================================
# HAIST WORKS - SQLite + 업로드 백업
# v5H226z75 (2026-05-11)
# ============================================================
# 권장: Synology HyperBackup 으로 /volume1/docker/knk-haist 전체 백업
# 본 스크립트는 HyperBackup 없이 cron 으로 사용할 때 보조용.
# ============================================================
set -e

NAS_BASE="/volume1/docker/knk-haist"
BACKUP_DIR="${NAS_BASE}/backups"
DATA_DIR="${NAS_BASE}/data"
UPLOADS_DIR="${NAS_BASE}/uploads"
KEEP_DAYS=30

TS=$(date '+%Y%m%d_%H%M%S')
mkdir -p "${BACKUP_DIR}"

echo "[$(date '+%F %T')] 백업 시작 → ${BACKUP_DIR}/knk-haist_${TS}.tar.gz"

# SQLite 안전 백업 (.backup 사용 — VACUUM INTO 보다 안전)
for db in "${DATA_DIR}"/*.db; do
    [ -e "$db" ] || continue
    fname=$(basename "$db" .db)
    sqlite3 "$db" ".backup '${BACKUP_DIR}/${fname}_${TS}.db'"
    echo "  - DB: ${fname} -> ${fname}_${TS}.db"
done

# 업로드 + DB 함께 tar
tar czf "${BACKUP_DIR}/knk-haist_${TS}.tar.gz" \
    -C "${NAS_BASE}" data uploads 2>/dev/null

echo "[$(date '+%F %T')] 완료"

# 오래된 백업 정리
find "${BACKUP_DIR}" -name "knk-haist_*.tar.gz" -mtime +${KEEP_DAYS} -delete
find "${BACKUP_DIR}" -name "*_2026*.db"          -mtime +${KEEP_DAYS} -delete

echo "[$(date '+%F %T')] ${KEEP_DAYS}일 초과 백업 정리 완료"
