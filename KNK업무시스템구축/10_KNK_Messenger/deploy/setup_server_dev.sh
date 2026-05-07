#!/usr/bin/env bash
# ============================================================
# KNK Messenger - 클라우드 dev 모드 셋업 (개발하면서 검증)
# ============================================================
# setup_server.sh 와의 차이:
#   - KNK_MSG_ENV=development (개발 모드 = 즉시 반영, 친절한 에러)
#   - CORS=*                  (어느 origin이든 허용 - 테스트 편함)
#   - HSTS/secure 쿠키 OFF    (HTTPS 미적용 상태에서도 동작)
#   - 그 외 (gunicorn/eventlet/nginx/systemd/cron)는 동일
#
# 어느 정도 안정되면 deploy/promote_to_production.sh 한 번 실행으로
# 운영 모드 전환.
# ============================================================
# 사용법:
#   sudo bash setup_server_dev.sh msg.knk.co.kr admin@knk.kr
# ============================================================
set -e

DOMAIN="${1:?사용법: setup_server_dev.sh <도메인> <이메일>}"
EMAIL="${2:?관리자 이메일을 두 번째 인자로 주세요.}"
APP_DIR="/opt/knk_messenger"
APP_USER="ubuntu"

echo ""
echo "==================================================="
echo "  KNK Messenger DEV-ON-CLOUD 셋업"
echo "  도메인: $DOMAIN"
echo "  모드:   development (즉시 반영, 인터넷 검증용)"
echo "==================================================="
echo ""

if [ "$EUID" -ne 0 ]; then
  echo "[오류] sudo 로 실행하세요."
  exit 1
fi

if [ ! -d "$APP_DIR" ]; then
  echo "[오류] $APP_DIR 가 없습니다. 먼저 코드를 $APP_DIR 에 올리세요."
  exit 1
fi

# 1. 패키지
echo "[1/7] 패키지 설치..."
apt update -y
apt install -y python3 python3-venv python3-pip \
               nginx certbot python3-certbot-nginx \
               ufw fail2ban sqlite3 git curl

# 2. venv
echo "[2/7] Python venv..."
cd "$APP_DIR"
[ -d ".venv" ] || python3 -m venv .venv
.venv/bin/pip install --upgrade pip wheel
.venv/bin/pip install -r requirements.txt

mkdir -p "$APP_DIR/data/uploads" "$APP_DIR/backups"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# 3. .env (DEV 모드)
ENV_FILE="$APP_DIR/.env.production"
if [ ! -f "$ENV_FILE" ]; then
  echo "[3/7] .env 생성 (development mode)..."
  SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  cat > "$ENV_FILE" <<EOF
# DEV-ON-CLOUD MODE - 인터넷에 띄우고 개발 중
# 어느 정도 안정되면 promote_to_production.sh 실행
KNK_MSG_ENV=development
KNK_MSG_PORT=5050
KNK_MSG_SECRET=$SECRET
KNK_MSG_RETENTION_MONTHS=12
KNK_MSG_ASYNC=eventlet
KNK_MSG_CORS=*
KNK_MSG_CONTACT=mailto:$EMAIL
KNK_MSG_PROXIES=1
EOF
  chmod 600 "$ENV_FILE"
  chown "$APP_USER:$APP_USER" "$ENV_FILE"
fi

# 4. systemd
echo "[4/7] systemd 등록..."
cp "$APP_DIR/deploy/knk-messenger.service" /etc/systemd/system/knk-messenger.service
systemctl daemon-reload
systemctl enable knk-messenger
systemctl restart knk-messenger
sleep 2

# 5. nginx
echo "[5/7] nginx..."
NGINX_CONF="/etc/nginx/sites-available/knk-messenger"
sed "s|__DOMAIN__|$DOMAIN|g" "$APP_DIR/deploy/nginx.conf" > "$NGINX_CONF"
ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/knk-messenger
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

# 6. SSL (꼭 필요 - PWA·푸시·서비스워커가 HTTPS만 동작)
echo "[6/7] SSL (Let's Encrypt)..."
certbot --nginx --non-interactive --agree-tos -m "$EMAIL" -d "$DOMAIN" --redirect || {
  echo "[경고] SSL 발급 실패 - DNS A 레코드 확인 후 수동 실행:"
  echo "        sudo certbot --nginx -d $DOMAIN"
}

# 7. 방화벽 + cron
echo "[7/7] 방화벽 + cron..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable
systemctl enable --now fail2ban

CRON_FILE="/etc/cron.d/knk-messenger-backup"
cat > "$CRON_FILE" <<EOF
0 3 * * * $APP_USER bash $APP_DIR/deploy/backup.sh >> $APP_DIR/backups/backup.log 2>&1
EOF
chmod 644 "$CRON_FILE"

echo ""
echo "==================================================="
echo "  DEV-ON-CLOUD 셋업 완료"
echo "==================================================="
echo "  접속:        https://$DOMAIN"
echo "  현재 모드:   DEVELOPMENT (개발 진행 중)"
echo "  코드 갱신:   (Windows에서) deploy\\sync_to_cloud.ps1"
echo "  로그:        sudo journalctl -u knk-messenger -f"
echo ""
echo "  안정되면 운영 모드로:"
echo "    sudo bash $APP_DIR/deploy/promote_to_production.sh"
echo "==================================================="
