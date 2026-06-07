#!/bin/sh
# ─────────────────────────────────────────────────────────────────────────
# RS256 키 쌍 생성 — 메신저 SSO (Identity Provider). 컨테이너 안에서 1회 실행.
#   발주: _TO_메신저세션/2026-05-29_사번SSO.md §3.4.1
#   private = 메신저만 보관(서명) / public = 모든 Service Provider 공유(검증)
#   ★ 멱등: 이미 키가 있으면 절대 덮어쓰지 않음 (재생성 = 발급된 모든 토큰 무효화)
# ─────────────────────────────────────────────────────────────────────────
set -e
KEYS_DIR="${KNK_MSG_KEYS_DIR:-/opt/knk_messenger/keys}"
PRIV="$KEYS_DIR/jwt_rs256_private.pem"
PUB="$KEYS_DIR/jwt_rs256_public.pem"

mkdir -p "$KEYS_DIR"

if [ -f "$PRIV" ] && [ -f "$PUB" ]; then
  echo "[gen_sso_keys] 이미 존재 — 덮어쓰지 않음: $KEYS_DIR"
  ls -l "$KEYS_DIR"
  exit 0
fi

echo "[gen_sso_keys] RS256 2048bit 키 쌍 생성 중..."
openssl genrsa -out "$PRIV" 2048
openssl rsa -in "$PRIV" -pubout -out "$PUB"
chmod 600 "$PRIV"
chmod 644 "$PUB"

echo "[gen_sso_keys] 생성 완료:"
ls -l "$KEYS_DIR"
echo ""
echo "[gen_sso_keys] public key (Service Provider 에 공유):"
cat "$PUB"
