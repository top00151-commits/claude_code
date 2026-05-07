#!/usr/bin/env bash
# ============================================================
# KNK Messenger - dev 모드 -> 운영 모드 전환
# ============================================================
# 사용 시점:
#   - 인터넷에서 며칠 사용해보고 안정 확인
#   - 베타 사용자 피드백 반영 끝
#   - 정식 사용 시작 직전
#
# 동작:
#   1) .env.production 의 KNK_MSG_ENV 를 production 으로
#   2) CORS 를 실제 도메인으로 제한
#   3) 백업 1번 + systemd 재시작
#   4) 변경사항 출력
# ============================================================
set -e
APP_DIR="/opt/knk_messenger"
ENV_FILE="$APP_DIR/.env.production"

if [ ! -f "$ENV_FILE" ]; then
  echo "[오류] $ENV_FILE 없음"
  exit 1
fi

echo "[1/3] 즉시 백업..."
bash "$APP_DIR/deploy/backup.sh" || true

# 현재 도메인 추출 (nginx 설정에서)
DOMAIN=$(grep -oP 'server_name \K[^;]+' /etc/nginx/sites-available/knk-messenger | head -1 | tr -d ' ')
if [ -z "$DOMAIN" ]; then
  echo "[경고] 도메인 자동 추출 실패. 환경변수 그대로 둡니다."
fi

echo "[2/3] 운영 모드로 전환..."
# 백업 1부 보관
cp "$ENV_FILE" "$ENV_FILE.dev.$(date +%Y%m%d_%H%M)"

# 변경
sed -i 's/^KNK_MSG_ENV=.*/KNK_MSG_ENV=production/' "$ENV_FILE"
if [ -n "$DOMAIN" ]; then
  sed -i "s|^KNK_MSG_CORS=.*|KNK_MSG_CORS=https://$DOMAIN|" "$ENV_FILE"
fi

echo "  현재 .env:"
grep -E '^KNK_MSG_(ENV|CORS|ASYNC|PROXIES)' "$ENV_FILE" | sed 's/^/    /'

echo "[3/3] 서비스 재시작..."
systemctl restart knk-messenger
sleep 3

# 헬스체크
HTTP=$(curl -fs -o /dev/null -w "%{http_code}" http://127.0.0.1:5050/login || echo "000")
if [ "$HTTP" = "200" ] || [ "$HTTP" = "302" ]; then
  echo ""
  echo "==================================================="
  echo "  운영 모드 전환 완료"
  echo "==================================================="
  echo "  접속:    https://${DOMAIN:-<your-domain>}"
  echo "  HTTP:    $HTTP (정상)"
  echo "  보안:    HSTS, secure cookie, CORS 제한 활성"
  echo ""
  echo "  되돌리려면:"
  echo "    sudo cp $ENV_FILE.dev.* $ENV_FILE"
  echo "    sudo systemctl restart knk-messenger"
  echo "==================================================="
else
  echo "[오류] HTTP $HTTP - 운영 모드 전환 후 비정상"
  echo "       복구: sudo cp $ENV_FILE.dev.* $ENV_FILE && sudo systemctl restart knk-messenger"
  exit 2
fi
