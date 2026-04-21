# HAIST WORKS 배포 가이드

> **대상**: KNK 사내 배포 담당자 (김정락 대표 / IT 담당)
> **작성**: 2026-04-20 · 빅터(Victor)
> **상태**: MVP 배포 준비

---

## 🎯 배포 전 체크리스트

### 1. 데이터 준비
- [ ] `scripts/backup_db.py` 실행하여 현재 DB 백업
- [ ] `scripts/migrate_baby_v2.py --dry-run` 으로 baby 데이터 마이그레이션 리허설
- [ ] baby PMS 실 파일의 컬럼 구조 확인 (COLUMN_MAP_TEMPLATE 조정)
- [ ] 마이그레이션 실행 → `/admin` 에서 프로젝트 건수 확인
- [ ] 초기 비밀번호 배포 (`/admin` → 재생성 버튼 → Excel 다운로드)

### 2. 하이웍스 API 토큰 (선택, 알림 활성화)
- [ ] 하이웍스 오피스 로그인 (관리자)
- [ ] 오피스 관리 → 환경 설정 → **API 관리**
- [ ] **메신저 알림 API** 토큰 발급 → `/admin/settings`
- [ ] 인사관리 / 전자결재 토큰 (선택)

### 3. 서버 환경
- [ ] Python 3.10+ 설치 확인
- [ ] 필요 패키지: `pip install -r requirements.txt`
  - fastapi, uvicorn, jinja2, openpyxl, python-multipart, itsdangerous
- [ ] 포트 8081 방화벽 개방 (또는 Nginx 리버스 프록시)
- [ ] DB 파일 (`data/knk.db`) 쓰기 권한

---

## 🖥 배포 옵션

### 옵션 A. 사내 서버 (권장, KNK 데이터 외부 유출 없음)

**사전 조건**:
- Windows 또는 Linux 서버 1대 (최소 2코어 / 4GB RAM)
- 사내망에서 접근 가능한 IP

**Windows 서버 실행**:
```bat
cd C:\path\to\01_HAIST_WORKS
python run.py
```

**Linux (systemd 서비스)**:
```ini
# /etc/systemd/system/haist.service
[Unit]
Description=HAIST WORKS
After=network.target

[Service]
Type=simple
User=haist
WorkingDirectory=/opt/haist_works
ExecStart=/usr/bin/python3 run.py
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable haist
sudo systemctl start haist
```

**Nginx 리버스 프록시 (HTTPS)**:
```nginx
server {
    listen 443 ssl http2;
    server_name haist.knk.co.kr;
    ssl_certificate     /etc/ssl/haist.crt;
    ssl_certificate_key /etc/ssl/haist.key;

    client_max_body_size 50M;  # Excel 업로드

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 옵션 B. 클라우드 (소규모, 외부 접근)
- AWS Lightsail / Naver Cloud / 오라클 무료 티어
- 보안그룹 443만 개방
- Let's Encrypt 인증서 자동 갱신

### 옵션 C. NAS (시놀로지 등)
- Container Station 또는 Docker
- Dockerfile 필요 (별도 요청 시 작성)

---

## 🔒 보안 체크리스트

- [ ] `main.py`의 `SessionMiddleware(secret_key=...)` 값을 운영용으로 교체
  (현재 `"knk-haist-2026-phase1"` → 랜덤 32자)
- [ ] admin 계정 비밀번호 변경 (기본 `admin/admin1234`)
- [ ] HTTPS 적용 (Nginx + Let's Encrypt)
- [ ] DB 파일 OS 권한 제한 (chmod 600)
- [ ] 백업 실행 확인 (cron 또는 Windows 작업 스케줄러)
- [ ] 로그 로테이션 설정

---

## 📅 백업 전략

**매일 02:00 자동 백업** (60일 보관):
```bat
# Windows 작업 스케줄러
python C:\path\to\01_HAIST_WORKS\scripts\backup_db.py --keep 60
```
```bash
# Linux cron
0 2 * * * cd /opt/haist_works && python scripts/backup_db.py --keep 60
```

**외장 저장소 추가 복사** (주 1회):
```bash
0 3 * * 0 rsync -a data/backups/ user@nas:/backup/haist/
```

---

## 🚀 파일럿 → 전사 확대 단계

### Phase P1 — 10명 파일럿 (1주)
- 참여 부서: 기술영업 / 구매 / 품질
- 목표: 변경 Inform / 티켓 / 진행률 실사용 검증
- 피드백 창구: 전사 게시판 "HAIST WORKS 피드백"

### Phase P2 — 30명 확대 (2주차)
- 전 부서 팀장 + 주요 담당자
- 목표: 물류 입출고 / 이슈 DB 실사용

### Phase P3 — 전사 60명 (3주차)
- 하이웍스 API 토큰 활성 (알림 발송 시작)
- 실사용 수치 모니터링

---

## 🆘 문제 발생 시

### 서버 안 켜짐
```bash
python run.py   # 포어그라운드로 실행해 에러 확인
# 주요 원인: 포트 충돌, DB 권한, 패키지 누락
```

### DB 잠김 / 손상
```bash
# 1. 서비스 정지
sudo systemctl stop haist
# 2. 최신 백업 복원
cp data/backups/knk_YYYYMMDD_HHMMSS.db data/knk.db
# 3. 재기동
sudo systemctl start haist
```

### 사용자 비밀번호 분실
- admin 로그인 → `/admin` → 재생성 버튼 → 해당 사용자만 수동 교체

---

## 📞 연락처

- 시스템 오너: 김정락 대표
- GitHub: `top00151-commits/claude_code`
- 문서 인덱스: `01_HAIST_WORKS/_README.md` (있으면)
- Victor 도움말: 사이트 우상단 🤖 "빅터에게 물어보기" 클릭

---

## 📌 운영 중 빈번한 작업

| 작업 | 경로 |
|------|------|
| 비밀번호 초기화 | `/admin` → 재생성 |
| 프로젝트 일괄 등록 | `/admin` → 관리코드 엑셀 업로드 |
| 하이웍스 토큰 교체 | `/admin/settings` |
| 부서원 추가 | `/admin` → 사용자 탭 |
| 백업 다운로드 | `data/backups/` 에서 파일 복사 |
| 로그 확인 | `tail -f nohup.out` 또는 systemd `journalctl -u haist` |
