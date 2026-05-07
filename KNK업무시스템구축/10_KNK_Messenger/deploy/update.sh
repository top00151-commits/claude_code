#!/usr/bin/env bash
# ============================================================
# KNK Messenger - 코드 갱신 스크립트
# ============================================================
# 운영 서버에서 코드를 업데이트할 때:
#   bash /opt/knk_messenger/deploy/update.sh
#
# 동작:
#   1) 현재 DB·업로드 백업 (안전망)
#   2) git pull (또는 사용자가 scp로 갈아끼운 후 의존성만 갱신)
#   3) requirements 변경 시 pip install
#   4) systemd 재시작
#   5) 헬스 체크
# ============================================================
set -e
APP_DIR="/opt/knk_messenger"
cd "$APP_DIR"

echo "[update] 1/5 즉시 백업 (안전망)..."
bash "$APP_DIR/deploy/backup.sh" || true

echo "[update] 2/5 코드 갱신..."
if [ -d ".git" ]; then
  git pull --rebase --autostash
else
  echo "       (git 저장소 아님 - scp/rsync로 코드를 직접 올린 상태로 가정)"
fi

echo "[update] 3/5 의존성 동기화..."
.venv/bin/pip install -r requirements.txt

echo "[update] 4/5 서비스 재시작..."
sudo systemctl restart knk-messenger
sleep 3

echo "[update] 5/5 헬스 체크..."
HTTP=$(curl -fs -o /dev/null -w "%{http_code}" http://127.0.0.1:5050/login || echo "000")
if [ "$HTTP" = "200" ] || [ "$HTTP" = "302" ]; then
  echo "[OK] HTTP $HTTP"
else
  echo "[FAIL] HTTP $HTTP - check: sudo journalctl -u knk-messenger -n 50"
  exit 2
fi
