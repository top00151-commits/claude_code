#!/usr/bin/env bash
# ============================================================
# KNK Messenger - Ubuntu 22.04 서버 1회 셋업 스크립트
# ============================================================
# 사용법:
#   sudo bash setup_server.sh msg.knk.co.kr admin@knk.kr
#
# 인자:
#   $1 = 도메인 (예: msg.knk.co.kr)
#   $2 = 관리자 이메일 (Let's Encrypt 알림용)
#
# 동작:
#   1) 시스템 패키지 설치 (python3, nginx, certbot, ufw, fail2ban)
#   2) /opt/knk_messenger 에 코드 위치 가정 (사전에 git clone 또는 scp)
#   3) Python venv + requirements 설치
#   4) systemd 서비스 등록
#   5) nginx 사이트 설정
#   6) Let's Encrypt SSL 발급
#   7) 방화벽 활성화
#   8) cron 백업 등록
# ============================================================
set -e

DOMAIN="${1:?사용법: setup_server.sh <도메인> <이메일>}"
EMAIL="${2:?관리자 이메일을 두 번째 인자로 주세요.}"
APP_DIR="/opt/knk_messenger"
APP_USER="ubuntu"

echo ""
echo "==================================================="
echo "  KNK Messenger 서버 셋업 시작"
echo "  도메인: $DOMAIN"
echo "  이메일: $EMAIL"
echo "  설치경로: $APP_DIR"
echo "==================================================="
echo ""

if [ "$EUID" -ne 0 ]; then
  echo "[오류] sudo 로 실행하세요."
  exit 1
fi

if [ ! -d "$APP_DIR" ]; then
  echo "[오류] $APP_DIR 가 없습니다. 먼저 코드를 $APP_DIR 에 올리세요."
  echo "       예: scp -r 10_KNK_Messenger/ ubuntu@SERVER:/opt/knk_messenger/"
  exit 1
fi

# ---------- 1. 시스템 패키지 ----------
echo "[1/8] 시스템 패키지 설치..."
apt update -y
apt install -y python3 python3-venv python3-pip \
               nginx certbot python3-certbot-nginx \
               ufw fail2ban sqlite3 git curl

# ---------- 2. Python venv ----------
echo "[2/8] Python venv 구성..."
cd "$APP_DIR"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --upgrade pip wheel
.venv/bin/pip install -r requirements.txt

# ---------- 3. 디렉토리 권한 ----------
echo "[3/8] 디렉토리 권한 설정..."
mkdir -p "$APP_DIR/data/uploads" "$APP_DIR/backups"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# ---------- 4. .env 생성 (없으면) ----------
ENV_FILE="$APP_DIR/.env.production"
if [ ! -f "$ENV_FILE" ]; then
  echo "[4/8] .env.production 생성..."
  SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  cat > "$ENV_FILE" <<EOF
KNK_MSG_ENV=production
KNK_MSG_PORT=5050
KNK_MSG_SECRET=$SECRET
KNK_MSG_RETENTION_MONTHS=12
KNK_MSG_ASYNC=eventlet
KNK_MSG_CORS=https://$DOMAIN
KNK_MSG_CONTACT=mailto:$EMAIL
KNK_MSG_PROXIES=1
EOF
  chmod 600 "$ENV_FILE"
  chown "$APP_USER:$APP_USER" "$ENV_FILE"
else
  echo "[4/8] .env.production 이미 존재 - 건드리지 않음."
fi

# ---------- 5. systemd 서비스 ----------
echo "[5/8] systemd 서비스 등록..."
cp "$APP_DIR/deploy/knk-messenger.service" /etc/systemd/system/knk-messenger.service
systemctl daemon-reload
systemctl enable knk-messenger
systemctl restart knk-messenger
sleep 2
systemctl --no-pager --full status knk-messenger | head -n 15 || true

# ---------- 6. Nginx ----------
echo "[6/8] Nginx 사이트 설정..."
NGINX_CONF="/etc/nginx/sites-available/knk-messenger"
sed "s|__DOMAIN__|$DOMAIN|g" "$APP_DIR/deploy/nginx.conf" > "$NGINX_CONF"
ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/knk-messenger
# 기본 사이트 비활성화
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

# ---------- 7. SSL (Let's Encrypt) ----------
echo "[7/8] Let's Encrypt SSL 발급..."
certbot --nginx --non-interactive --agree-tos -m "$EMAIL" -d "$DOMAIN" --redirect || {
  echo "[경고] SSL 발급 실패. DNS A 레코드가 이 서버 IP를 가리키는지 확인 후 수동 실행:"
  echo "       sudo certbot --nginx -d $DOMAIN"
}

# ---------- 8. 방화벽 ----------
echo "[8/8] UFW 방화벽 + fail2ban..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable
systemctl enable --now fail2ban

# ---------- 백업 cron ----------
CRON_FILE="/etc/cron.d/knk-messenger-backup"
cat > "$CRON_FILE" <<EOF
# KNK Messenger 자동 백업 (매일 03:00)
0 3 * * * $APP_USER bash $APP_DIR/deploy/backup.sh >> $APP_DIR/backups/backup.log 2>&1
# 매월 1일 04:00 메시지 보존정책 실행
0 4 1 * * $APP_USER curl -fsS http://127.0.0.1:5050/api/admin/cleanup -X POST >> $APP_DIR/backups/cleanup.log 2>&1 || true
EOF
chmod 644 "$CRON_FILE"

echo ""
echo "==================================================="
echo "  셋업 완료!"
echo "==================================================="
echo "  접속 URL:    https://$DOMAIN"
echo "  서비스:      sudo systemctl status knk-messenger"
echo "  로그 실시간: sudo journalctl -u knk-messenger -f"
echo "  코드 갱신:   bash $APP_DIR/deploy/update.sh"
echo "  수동 백업:   bash $APP_DIR/deploy/backup.sh"
echo "==================================================="
