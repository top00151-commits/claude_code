# ============================================================
# HAIST WORKS - Synology NAS Docker (Ubuntu 20.04 base)
# v5H226z75 (2026-05-11) — 메신저 배포 패턴 재사용
# ============================================================
# Build:
#   docker build -t knk-haist:latest .
#
# Run (개별):
#   docker run -d --name knk-haist \
#     -p 8081:8081 \
#     -v /volume1/docker/knk-haist/data:/app/data \
#     -v /volume1/docker/knk-haist/uploads:/app/uploads \
#     -v /volume1/docker/knk-haist/backups:/app/backups \
#     --env-file /volume1/docker/knk-haist/.env \
#     --restart unless-stopped \
#     knk-haist:latest
#
# 권장: Container Manager Project 기능 (docker-compose 형태)
# ============================================================

FROM ubuntu:20.04

# 빌드 환경 (한국 시간대 / UTF-8 / 비대화)
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Seoul \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONUTF8=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 시스템 패키지: Python 3.8 (Ubuntu 20.04 기본) + 빌드 의존성 + OCR/PDF
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv python3-dev \
        sqlite3 libsqlite3-dev \
        build-essential \
        libffi-dev libssl-dev \
        zlib1g-dev libjpeg-dev libpng-dev \
        ca-certificates tzdata curl \
        tesseract-ocr tesseract-ocr-kor \
        poppler-utils \
    && ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime \
    && echo "Asia/Seoul" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# pip 최신화
RUN python3 -m pip install --upgrade pip wheel setuptools

# 작업 디렉토리
WORKDIR /app

# 의존성 먼저 (Docker 캐시 활용)
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# 앱 코드
COPY run.py ./
COPY app ./app
COPY static ./static
COPY scripts ./scripts

# 영속 데이터 디렉토리 (볼륨 마운트 포인트)
RUN mkdir -p /app/data /app/uploads /app/backups

# 비루트 사용자 (Synology 권장)
RUN groupadd -g 1000 knkhaist && \
    useradd -u 1000 -g 1000 -m -s /bin/bash knkhaist && \
    chown -R knkhaist:knkhaist /app

USER knkhaist

# 헬스체크 (Synology 컨테이너 모니터링)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8081/login >/dev/null || exit 1

# 8081 노출 (DSM Reverse Proxy 또는 호스트 nginx 가 외부 443 → 내부 8081)
EXPOSE 8081

# 운영 실행 — run.py 의 KNK_MODE=prod 분기 사용 (uvicorn workers 2)
# .env 의 KNK_MODE=prod / KNK_HOST=0.0.0.0 / KNK_WORKERS=2 환경변수로 제어
ENV KNK_HOST=0.0.0.0 \
    KNK_PORT=8081

CMD ["python3", "run.py"]
