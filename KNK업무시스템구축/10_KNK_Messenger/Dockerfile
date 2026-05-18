# ============================================================
# KNK Messenger - Synology NAS Docker (Ubuntu 20.04 base)
# ============================================================
# Build:
#   docker build -t knk-messenger:latest .
#
# Run (개별):
#   docker run -d --name knk-messenger \
#     -p 5050:5050 \
#     -v /volume1/docker/knk-messenger/data:/app/data \
#     -v /volume1/docker/knk-messenger/backups:/app/backups \
#     --env-file /volume1/docker/knk-messenger/.env \
#     --restart unless-stopped \
#     knk-messenger:latest
#
# 권장: docker-compose.yml 사용 (Synology Container Manager Project 기능)
# ============================================================

FROM ubuntu:20.04

# 빌드 시 한국어 입력 / 시간대 / 무대화 설정
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Seoul \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 시스템 패키지: Python 3.8 (Ubuntu 20.04 기본) + 빌드 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv python3-dev \
        sqlite3 libsqlite3-dev \
        build-essential \
        libffi-dev libssl-dev \
        zlib1g-dev libjpeg-dev libpng-dev \
        ca-certificates \
        tzdata \
        curl \
    && ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime \
    && echo "Asia/Seoul" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# pip 최신화
RUN python3 -m pip install --upgrade pip wheel setuptools

# 작업 디렉토리
WORKDIR /app

# 의존성 먼저 (캐시 활용)
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# 앱 코드
COPY app.py wsgi.py ./
COPY templates ./templates
COPY static ./static
COPY generate_icons.py generate_vapid.py seed_from_xlsx.py backup.py ./
# (참고자료 같은 큰 폴더는 .dockerignore에서 제외)

# 영속 데이터 디렉토리 (볼륨 마운트 포인트)
RUN mkdir -p /app/data/uploads /app/backups

# 비루트 사용자 (Synology 권장)
RUN groupadd -g 1000 knkmsg && \
    useradd -u 1000 -g 1000 -m -s /bin/bash knkmsg && \
    chown -R knkmsg:knkmsg /app

USER knkmsg

# 헬스체크 (Synology 가 컨테이너 상태 모니터링)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:5050/healthz >/dev/null || exit 1

# 5050 노출 (DSM Reverse Proxy 가 외부 443 → 내부 5050 매핑)
EXPOSE 5050

# 운영: gunicorn + eventlet 워커 (Socket.IO WebSocket 지원)
# 개발 토글: KNK_MSG_ENV=development 면 stdout 디버그 로그 + 자동 리로드 (이미 app.py 처리)
CMD ["gunicorn", "-k", "eventlet", "-w", "1", \
     "--bind", "0.0.0.0:5050", \
     "--timeout", "600", \
     "--graceful-timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "wsgi:app"]
