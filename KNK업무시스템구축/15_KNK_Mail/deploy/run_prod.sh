#!/bin/sh
# KNK Eum MAIL 운영 기동 스크립트 (NAS).
# - deploy/.env 가 있으면 환경변수로 로드
# - uvicorn 으로 app.main:app 을 127.0.0.1:포트 에 기동 (리버스프록시가 외부 노출)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
APPROOT="$(cd "$HERE/.." && pwd)"     # 15_KNK_Mail
# 운영 .env 는 data/.env (배포 스크립트가 거기 씀). set -a 로 export.
if [ -f "$APPROOT/data/.env" ]; then set -a; . "$APPROOT/data/.env"; set +a; fi
cd "$APPROOT"
exec python3 -m uvicorn app.main:app \
  --host "${KNK_MAIL_HOST:-127.0.0.1}" \
  --port "${KNK_MAIL_PORT:-8201}"
