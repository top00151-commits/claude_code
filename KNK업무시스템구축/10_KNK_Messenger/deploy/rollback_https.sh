#!/bin/bash
# HTTPS 전환 롤백 — 가장 최근 백업 .env 로 복구
set -e

ENV_FILE="/opt/knk_messenger/.env"
LATEST_BACKUP=$(ls -t "$ENV_FILE".before_https.* 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "[FAIL] 백업 파일 없음"
    exit 1
fi

cp -v "$LATEST_BACKUP" "$ENV_FILE"
supervisorctl restart knk-messenger
sleep 3
echo ""
echo "[OK] 롤백 완료 — KNK_MSG_ENV=$(grep ^KNK_MSG_ENV $ENV_FILE)"
curl -fs -o /dev/null -w "[HTTP 5050] %{http_code}\n" http://127.0.0.1:5050/healthz || echo "FAIL"
