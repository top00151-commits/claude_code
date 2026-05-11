#!/bin/bash
# ============================================================
# HAIST WORKS — Synology Container (Ubuntu 20.04) 내부 셋업
# v5H226z76 (2026-05-11)
# ============================================================
# 환경: 메신저(knk_messenger)가 이미 가동 중인 단일 Ubuntu 컨테이너.
#       systemctl 없음. supervisord + nginx 가 메신저용으로 가동 중.
#       호스트 :80 = Synology Web Station. 메신저 nginx = :8080.
#
# HAIST 추가:
#       uvicorn :8081 (앱)
#       nginx server block :8090 (앱 프록시 + 정적 캐싱)
#       supervisord 에 knk-haist 등록
#
# 실행 방법:
#   1. 컨테이너에 SSH 접속
#         ssh root@o.knknara.co.kr -p 31201
#   2. 코드 업로드 후 (1단계 가이드 참고) 본 스크립트 실행:
#         cd /opt/knk_haist
#         bash deploy/setup_ubuntu_container.sh
# ============================================================
set -e

APP_DIR="/opt/knk_haist"
VENV="${APP_DIR}/.venv"
ENV_FILE="${APP_DIR}/.env"
LOGS="${APP_DIR}/logs"
DATA="${APP_DIR}/data"
UPLOADS="${APP_DIR}/uploads"
BACKUPS="${APP_DIR}/backups"

SUPER_CONF="/etc/supervisor/conf.d/knk-haist.conf"
NGINX_AVAIL="/etc/nginx/sites-available/knk-haist"
NGINX_ENABLED="/etc/nginx/sites-enabled/knk-haist"

INTERNAL_HEALTH="http://127.0.0.1:8081/login"

echo "================================================"
echo "  HAIST WORKS — Ubuntu 컨테이너 셋업"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================"

# 1. 디렉토리 + 권한
echo "[1/9] 디렉토리 생성"
mkdir -p "${APP_DIR}" "${LOGS}" "${DATA}" "${UPLOADS}" "${BACKUPS}"

# 2. 시스템 패키지 (필요한 것만 — 메신저가 이미 설치한 것 재사용)
echo "[2/9] 시스템 패키지 확인/설치"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv python3-dev \
    sqlite3 libsqlite3-dev \
    build-essential libffi-dev libssl-dev \
    zlib1g-dev libjpeg-dev libpng-dev \
    ca-certificates tzdata curl \
    tesseract-ocr tesseract-ocr-kor \
    poppler-utils \
    supervisor nginx
ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime
echo "Asia/Seoul" > /etc/timezone

# 3. Python venv
echo "[3/9] Python venv + requirements"
if [ ! -d "${VENV}" ]; then
    python3 -m venv "${VENV}"
fi
"${VENV}/bin/pip" install --upgrade pip wheel setuptools
"${VENV}/bin/pip" install -r "${APP_DIR}/requirements.txt"

# 4. .env 자동 생성 (SECRET_KEY 임의 hex 32바이트)
echo "[4/9] .env 확인/생성"
if [ ! -f "${ENV_FILE}" ]; then
    SECRET_KEY=$("${VENV}/bin/python" -c "import secrets; print(secrets.token_hex(32))")
    cat > "${ENV_FILE}" <<EOF
# 자동 생성됨 ($(date '+%Y-%m-%d %H:%M:%S'))
KNK_SECRET_KEY=${SECRET_KEY}
KNK_MODE=prod
KNK_HOST=0.0.0.0
KNK_PORT=8081
KNK_WORKERS=2
TZ=Asia/Seoul
EOF
    chmod 600 "${ENV_FILE}"
    echo "    → ${ENV_FILE} 신규 생성 (SECRET_KEY 자동 hex 64자)"
else
    echo "    → ${ENV_FILE} 이미 존재 — 그대로 유지"
fi

# 5. supervisord 등록
echo "[5/9] supervisord conf 등록"
cp "${APP_DIR}/deploy/supervisord-knk-haist.conf" "${SUPER_CONF}"
# .env 값을 environment 에 주입 (KNK_SECRET_KEY 등)
# supervisord environment 는 source 못 함 → 별도 wrapper or 그대로 export
# 가장 단순: command 를 wrapper 로 변경
cat > "${APP_DIR}/run-prod.sh" <<'WRAP'
#!/bin/bash
cd /opt/knk_haist
set -a
[ -f .env ] && . ./.env
set +a
exec .venv/bin/python run.py
WRAP
chmod +x "${APP_DIR}/run-prod.sh"
# supervisord conf 의 command 를 wrapper 로 교체
sed -i "s|command=/opt/knk_haist/.venv/bin/python /opt/knk_haist/run.py|command=/opt/knk_haist/run-prod.sh|" "${SUPER_CONF}"

# supervisord 실행 중인지 확인 + reload
if ! pgrep -x supervisord > /dev/null; then
    echo "    [!] supervisord 미가동 — 시작"
    /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
    sleep 2
fi
supervisorctl reread
supervisorctl update
supervisorctl start knk-haist || true

# 6. nginx server block 등록
echo "[6/9] nginx server block 등록 (:8090)"
cp "${APP_DIR}/deploy/nginx-knk-haist-server.conf" "${NGINX_AVAIL}"
ln -sf "${NGINX_AVAIL}" "${NGINX_ENABLED}"
nginx -t

# nginx reload — supervisord 가 knk-nginx 로 관리 중이면 supervisorctl 사용
if supervisorctl status 2>/dev/null | grep -q "knk-nginx"; then
    supervisorctl restart knk-nginx
else
    # nginx 직접 실행 모드
    nginx -s reload 2>/dev/null || nginx
fi

# 7. 헬스체크 (최대 30초)
echo "[7/9] 헬스체크 (최대 30초)"
HEALTH_OK=0
for i in $(seq 1 15); do
    sleep 2
    code=$(curl -s -o /dev/null -w "%{http_code}" "${INTERNAL_HEALTH}" 2>/dev/null || echo "000")
    if [ "$code" = "200" ] || [ "$code" = "303" ] || [ "$code" = "302" ]; then
        echo "    OK — HTTP ${code} ($((i*2))s)"
        HEALTH_OK=1
        break
    fi
done
if [ "$HEALTH_OK" = "0" ]; then
    echo "    [!] 30초 안에 응답 없음. 로그 확인:"
    tail -30 "${LOGS}/uvicorn-error.log" 2>/dev/null || echo "    (uvicorn-error.log 없음)"
fi

# 8. nginx :8090 응답 확인
echo "[8/9] nginx :8090 응답 확인"
NX_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8090/login" 2>/dev/null || echo "000")
echo "    nginx :8090 → HTTP ${NX_CODE}"

# 9. 요약
echo "[9/9] 완료 요약"
echo "    APP DIR    : ${APP_DIR}"
echo "    DB         : ${DATA}/"
echo "    LOGS       : ${LOGS}/"
echo "    ENV        : ${ENV_FILE}  (KNK_SECRET_KEY 자동 생성됨)"
echo "    UVICORN    : 127.0.0.1:8081"
echo "    NGINX      : 127.0.0.1:8090 (HAIST 전용)"
echo ""
echo "운영 명령:"
echo "    supervisorctl status"
echo "    supervisorctl restart knk-haist"
echo "    tail -f ${LOGS}/uvicorn.log"
echo "    curl -I http://127.0.0.1:8081/login"
echo "    curl -I http://127.0.0.1:8090/login"
echo ""
echo "외부 접속 (대표 라우터 작업 필요):"
echo "    옵션 α — 외부 3320 → 컨테이너:8090 매핑 추가"
echo "    옵션 β — haist.knknara.co.kr DNS 추가 + nginx server_name 교체"
echo "================================================"
