#!/bin/bash
# ============================================================
# HAIST WORKS - Synology NAS 초기 컨테이너 셋업
# v5H226z75 (2026-05-11)
# ============================================================
# 실행 위치: NAS SSH 콘솔에서 (Container Manager 가 자동 빌드도 가능)
# 사전 조건: Container Manager (Docker) 패키지 설치
# ============================================================
set -e

NAS_BASE="/volume1/docker/knk-haist"
IMG_TAG="knk-haist:latest"
CONTAINER="knk-haist"
HOST_PORT=8081

echo "================================================"
echo "  HAIST WORKS - Synology Docker 셋업"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================"

# 1. 디렉토리 생성
echo "[1/6] 디렉토리 생성: ${NAS_BASE}"
mkdir -p "${NAS_BASE}/data" \
         "${NAS_BASE}/uploads" \
         "${NAS_BASE}/backups" \
         "${NAS_BASE}/static"

# 2. .env 확인
if [ ! -f "${NAS_BASE}/.env" ]; then
    echo "[!] ${NAS_BASE}/.env 가 없습니다."
    echo "    .env.synology.example 를 .env 로 복사 후 KNK_SECRET_KEY 채우세요."
    if [ -f "${NAS_BASE}/.env.synology.example" ]; then
        cp "${NAS_BASE}/.env.synology.example" "${NAS_BASE}/.env"
        echo "[i] .env 템플릿 복사됨. 편집 필요: nano ${NAS_BASE}/.env"
    fi
    exit 1
fi

# 3. SECRET_KEY 검증 (개발 기본값이면 중단)
if grep -q "여기에_32자_이상" "${NAS_BASE}/.env"; then
    echo "[!] .env 의 KNK_SECRET_KEY 가 기본값입니다. 임의 32+자 값으로 교체하세요."
    echo "    생성: docker run --rm python:3.11-slim python -c \"import secrets; print(secrets.token_hex(32))\""
    exit 1
fi

# 4. 이미지 빌드 (소스가 같은 폴더에 있다고 가정)
SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "[2/6] 이미지 빌드: ${IMG_TAG} (from ${SRC_DIR})"
cd "${SRC_DIR}"
docker build -t "${IMG_TAG}" .

# 5. 기존 컨테이너 중단/제거 (재배포 대응)
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "[3/6] 기존 컨테이너 ${CONTAINER} 중단/제거"
    docker stop "${CONTAINER}" 2>/dev/null || true
    docker rm   "${CONTAINER}" 2>/dev/null || true
else
    echo "[3/6] 신규 컨테이너 (기존 없음)"
fi

# 6. 컨테이너 실행
echo "[4/6] 컨테이너 실행"
docker run -d --name "${CONTAINER}" \
    -p ${HOST_PORT}:8081 \
    -v "${NAS_BASE}/data:/app/data" \
    -v "${NAS_BASE}/uploads:/app/uploads" \
    -v "${NAS_BASE}/backups:/app/backups" \
    --env-file "${NAS_BASE}/.env" \
    --restart unless-stopped \
    "${IMG_TAG}"

# 7. 헬스체크 대기
echo "[5/6] 컨테이너 시작 대기 (최대 30초)"
for i in {1..15}; do
    sleep 2
    if curl -fsS "http://127.0.0.1:${HOST_PORT}/login" > /dev/null 2>&1; then
        echo "    OK — ${i}*2초 후 응답"
        break
    fi
done

# 8. 로그 미리보기
echo "[6/6] 최근 로그 (마지막 30줄)"
docker logs --tail 30 "${CONTAINER}"

echo "================================================"
echo "  완료"
echo "  내부 접속:  http://NAS_IP:${HOST_PORT}/login"
echo "  외부 접속:  DSM Reverse Proxy 설정 후 https://haist.knk.co.kr"
echo "  상태 확인:  docker ps | grep ${CONTAINER}"
echo "  로그 확인:  docker logs -f ${CONTAINER}"
echo "  중단:       docker stop ${CONTAINER}"
echo "================================================"
