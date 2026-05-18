#!/usr/bin/env bash
# ============================================================
# KNK Messenger - Synology NAS Docker Ubuntu 20.04 1줄 셋업
# ============================================================
# 환경: Synology Container Manager 의 Ubuntu 20.04 이미지 (systemd 없음)
# 라우터: 외부 o.knknara.co.kr:3310 -> 컨테이너 :80
#         외부 o.knknara.co.kr:31201 -> 컨테이너 :22 (SSH)
#
# 사용:
#   1) 코드를 /opt/knk_messenger 에 업로드 후
#   2) ssh root@o.knknara.co.kr -p 31201
#   3) bash /opt/knk_messenger/deploy/setup_synology_container.sh
#
# 처리:
#   - apt 업데이트 + python3·nginx·supervisor·sqlite3 등 설치
#   - Python venv + requirements 설치
#   - .env 자동 생성 (KNK_MSG_SECRET·ADMIN_TOKEN 자동 hex)
#   - supervisord 등록 (gunicorn + nginx)
#   - nginx 사이트 활성화
#   - 시작 + 헬스체크
# ============================================================
set -e

APP_DIR="/opt/knk_messenger"
LOG_DIR="$APP_DIR/logs"

echo
echo "==================================================="
echo "  KNK Messenger - Synology Container 셋업"
echo "==================================================="
echo

if [ ! -d "$APP_DIR" ]; then
  echo "[오류] $APP_DIR 없음. 먼저 코드를 업로드하세요."
  exit 1
fi

# === 1. 시스템 패키지 ===
echo "[1/7] 시스템 패키지 설치..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip python3-dev \
    sqlite3 libsqlite3-dev \
    build-essential libffi-dev libssl-dev \
    zlib1g-dev libjpeg-dev libpng-dev \
    nginx supervisor \
    curl ca-certificates tzdata locales
# 한국 시간대
ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime
echo "Asia/Seoul" > /etc/timezone
# UTF-8 locale
locale-gen ko_KR.UTF-8 || true
locale-gen en_US.UTF-8 || true

mkdir -p "$LOG_DIR" "$APP_DIR/data/uploads" "$APP_DIR/backups"

# === 2. Python venv ===
echo "[2/7] Python venv + 의존성..."
cd "$APP_DIR"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --upgrade pip wheel
.venv/bin/pip install -r requirements.txt

# === 3. .env 자동 생성 (없을 때만) ===
ENV_FILE="$APP_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "[3/7] .env 자동 생성..."
  SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  ADMIN_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  cat > "$ENV_FILE" <<EOF
# KNK Messenger 환경변수 (자동 생성)
KNK_MSG_ENV=development
KNK_MSG_PORT=5050
KNK_MSG_SECRET=$SECRET
KNK_MSG_ADMIN_TOKEN=$ADMIN_TOKEN
KNK_MSG_RETENTION_MONTHS=12
KNK_MSG_ASYNC=eventlet
KNK_MSG_CORS=*
KNK_MSG_CONTACT=mailto:admin@knknara.co.kr
KNK_MSG_PROXIES=1
KNK_MSG_MAX_UPLOAD_MB=500
KNK_MSG_LOGIN_FAIL_LIMIT=5
KNK_MSG_LOGIN_LOCK_SECONDS=300
KNK_MSG_RATE_PER_SEC=5
KNK_MSG_RATE_BURST=10
# AI 번역 (선택): ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_API_KEY=
KNK_MSG_TRANSLATE_MODEL=claude-haiku-4-5
KNK_MSG_TRANSLATE_USD_LIMIT=20
EOF
  chmod 600 "$ENV_FILE"
else
  echo "[3/7] .env 이미 존재 - 건드리지 않음"
fi

# === 4. supervisord 설정 ===
echo "[4/7] supervisord 등록..."
cp "$APP_DIR/deploy/supervisord.conf" /etc/supervisor/conf.d/knk-messenger.conf

# gunicorn 이 .env 를 읽도록 EnvironmentFile 대체 — supervisord 의 environment 에
# 직접 모두 넣을 수도 있지만 .env 를 wsgi.py 가 자동 로드하도록 처리하는 게 깔끔.
# 우선은 gunicorn 시작 명령을 .env 자동 로드 래퍼로 변경.
cat > "$APP_DIR/run_gunicorn.sh" <<'WRAP'
#!/usr/bin/env bash
# .env 의 KEY=VALUE 를 export 후 gunicorn 실행 (eventlet 워커)
set -a
[ -f "/opt/knk_messenger/.env" ] && . /opt/knk_messenger/.env
set +a
cd /opt/knk_messenger
exec /opt/knk_messenger/.venv/bin/gunicorn \
     -k eventlet -w 1 \
     --bind 127.0.0.1:5050 \
     --timeout 600 --graceful-timeout 60 \
     --access-logfile - --error-logfile - \
     wsgi:app
WRAP
chmod +x "$APP_DIR/run_gunicorn.sh"

# supervisord conf 의 command 를 래퍼로 교체
sed -i 's|^command=.*gunicorn .*|command=/opt/knk_messenger/run_gunicorn.sh|' /etc/supervisor/conf.d/knk-messenger.conf

# === 5. nginx 사이트 ===
echo "[5/7] nginx 사이트 활성화..."
cp "$APP_DIR/deploy/nginx-synology.conf" /etc/nginx/sites-available/knk-messenger
# 기본 사이트 비활성화 (default_server 충돌 방지)
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/knk-messenger /etc/nginx/sites-enabled/knk-messenger
nginx -t

# === 6. supervisord 시작 / 갱신 ===
echo "[6/7] supervisord 시작..."
# Synology Docker Ubuntu 컨테이너는 PID 1 이 보통 sshd. supervisord 가 따로 실행돼야 함.
# 컨테이너 재시작 시에도 자동 시작되도록 supervisord 데몬을 백그라운드로 실행.
if ! pgrep -f "supervisord" > /dev/null 2>&1; then
  /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
  sleep 2
fi
supervisorctl reread || true
supervisorctl update || true
supervisorctl restart knk-messenger || true
supervisorctl restart knk-nginx || true
sleep 4

# === 7. 헬스체크 ===
echo "[7/7] 헬스체크..."
HTTP=$(curl -fs -o /dev/null -w "%{http_code}" http://127.0.0.1:5050/healthz || echo "000")
NGINX_HTTP=$(curl -fs -o /dev/null -w "%{http_code}" http://127.0.0.1/healthz || echo "000")
echo "   gunicorn(5050): HTTP $HTTP"
echo "   nginx(80):      HTTP $NGINX_HTTP"

if [ "$HTTP" = "200" ] || [ "$HTTP" = "302" ]; then
  if [ "$NGINX_HTTP" = "200" ] || [ "$NGINX_HTTP" = "302" ]; then
    echo
    echo "==================================================="
    echo "  셋업 완료!"
    echo "==================================================="
    echo "  외부 접속:    http://o.knknara.co.kr:3310/"
    echo "  내부 헬스:    http://127.0.0.1/login (HTTP $NGINX_HTTP)"
    echo "  로그 (gunicorn): tail -f $LOG_DIR/gunicorn.log"
    echo "  로그 (nginx):    tail -f /var/log/nginx/access.log"
    echo "  재시작:       supervisorctl restart knk-messenger"
    echo "  상태:         supervisorctl status"
    echo "==================================================="
  else
    echo "[경고] gunicorn 동작 OK, nginx 비정상. nginx -t 확인 필요"
    exit 2
  fi
else
  echo "[오류] gunicorn 비정상. 로그 확인:"
  tail -n 50 "$LOG_DIR/gunicorn.err.log" || true
  exit 2
fi
