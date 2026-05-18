#!/bin/bash
# KNK 메신저 production 모드 전환 + 검증
# 사용: 대표님이 DSM 인증서 + Reverse Proxy 설정 완료 후 빅터가 실행
#   ssh root@haist.knknara.co.kr -p 31201 bash /opt/knk_messenger/deploy/flip_to_production.sh

set -e

ENV_FILE="/opt/knk_messenger/.env"
DOMAIN="haist.knknara.co.kr"

echo "==============================================="
echo "  KNK 메신저 HTTPS production 전환"
echo "==============================================="

# 1) 백업
BACKUP="$ENV_FILE.before_https.$(date +%Y%m%d_%H%M%S)"
cp -v "$ENV_FILE" "$BACKUP"

# 2) .env 수정
sed -i "s/^KNK_MSG_ENV=.*/KNK_MSG_ENV=production/" "$ENV_FILE"
# KNK_MSG_CORS 도 도메인으로 제한
if grep -q "^KNK_MSG_CORS=" "$ENV_FILE"; then
    sed -i "s|^KNK_MSG_CORS=.*|KNK_MSG_CORS=https://$DOMAIN|" "$ENV_FILE"
else
    echo "KNK_MSG_CORS=https://$DOMAIN" >> "$ENV_FILE"
fi
# VAPID contact 갱신
sed -i "s|^KNK_MSG_CONTACT=.*|KNK_MSG_CONTACT=mailto:admin@knknara.co.kr|" "$ENV_FILE" || true

echo ""
echo "변경된 환경변수:"
grep -E "^KNK_MSG_(ENV|CORS|CONTACT)" "$ENV_FILE"

# 3) gunicorn 재시작
echo ""
echo "메신저 재시작 중..."
supervisorctl restart knk-messenger
sleep 4

# 4) 검증
echo ""
echo "==============================================="
echo "검증"
echo "==============================================="

echo -n "[로컬 HTTP 5050]   "
curl -fs -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:5050/healthz || echo "FAIL"

echo -n "[외부 HTTPS /msg]  "
curl -fs -o /dev/null -w "HTTP %{http_code}\n" "https://$DOMAIN/msg/login" || echo "FAIL (DSM Reverse Proxy 확인 필요)"

echo -n "[HTTPS 인증서]     "
echo | openssl s_client -servername "$DOMAIN" -connect "$DOMAIN":443 2>/dev/null \
    | openssl x509 -noout -issuer -dates 2>/dev/null | head -3 || echo "FAIL"

echo ""
echo "==============================================="
echo "완료. 만약 외부 HTTPS 가 FAIL 이면:"
echo "  1) DSM 인증서 발급 확인"
echo "  2) DSM Reverse Proxy 활성 확인 (haist.knknara.co.kr:443 → localhost:5050)"
echo "  3) 라우터 외부 443 포트 개방 확인"
echo ""
echo "롤백: bash /opt/knk_messenger/deploy/rollback_https.sh"
echo "백업: $BACKUP"
echo "==============================================="
