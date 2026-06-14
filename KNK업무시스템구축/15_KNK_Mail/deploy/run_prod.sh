#!/bin/sh
# KNK Eum MAIL 운영 기동 스크립트 (NAS).
# - deploy/.env 가 있으면 환경변수로 로드
# - uvicorn 으로 app.main:app 을 127.0.0.1:포트 에 기동 (리버스프록시가 외부 노출)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
APPROOT="$(cd "$HERE/.." && pwd)"     # 15_KNK_Mail
[ -f "$HERE/.env" ] && . "$HERE/.env"
cd "$APPROOT"
exec python3 -m uvicorn app.main:app \
  --host "${KNK_MAIL_HOST:-127.0.0.1}" \
  --port "${KNK_MAIL_PORT:-8201}"
