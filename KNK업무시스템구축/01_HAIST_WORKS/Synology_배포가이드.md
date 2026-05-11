# HAIST WORKS — Synology NAS Docker 배포 가이드

> **v5H226z76 (2026-05-11)** — 메신저(10_KNK_Messenger)가 2026-05-11 실배포한 동일 NAS·동일 패턴 재사용.
> 실제 환경 = **단일 Ubuntu 20.04 컨테이너 + supervisord** (메신저와 공존). 별도 컨테이너 X.
>
> **즉시 사용: → 본 문서 가장 아래 "🚀 방법 B 부록 — 실 배포 절차 (Auto)"** 섹션 참고.
>
> 본문은 별도 컨테이너 방식 (참고용, 미사용)

---

## 0. 전제 조건 (이미 완료된 항목)

메신저 배포로 인해 다음은 **이미 갖춰져 있음** ✅:
- Synology DSM 7.0+ + Container Manager
- 회사 라우터 80/443 포트포워딩 → NAS
- 가비아 DNS 관리 권한
- Let's Encrypt 인증 체인

HAIST WORKS 추가 시 새로 할 것 — **DNS 1줄 + nginx 1블록**.

---

## 1. 가비아 DNS A 레코드 추가 (3분)

가비아 콘솔 → DNS 관리 → 해당 도메인:

| 호스트 | 타입 | 값 | TTL |
|---|---|---|---|
| `haist` | A | (NAS 공인 IP — 메신저와 동일) | 600 |

→ 30분 후 `nslookup haist.knk.co.kr` 으로 확인.

---

## 2. NAS 폴더 준비 (5분)

NAS SSH 접속:

```bash
ssh admin@192.168.1.10  # (NAS 내부 IP)

# 폴더 생성
sudo mkdir -p /volume1/docker/knk-haist/{data,uploads,backups,src}
sudo chown -R 1000:1000 /volume1/docker/knk-haist
```

---

## 3. 코드 업로드 (5분)

### 옵션 A — Windows PC에서 PowerShell

```powershell
cd "C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\01_HAIST_WORKS"
./deploy/sync_to_synology.ps1 -NasIP 192.168.1.10
```

### 옵션 B — File Station 수동
1. File Station 열기
2. `/volume1/docker/knk-haist/src` 로 이동
3. 다음만 업로드 (큰 폴더 제외):
   - `app/`, `static/`, `scripts/`, `deploy/`
   - `run.py`, `requirements.txt`
   - `Dockerfile`, `.dockerignore`

---

## 4. `.env` 만들기 (필수, 3분)

NAS SSH 에서:

```bash
cd /volume1/docker/knk-haist
cp src/.env.synology.example .env

# SECRET_KEY 생성
docker run --rm python:3.11-slim python -c "import secrets; print(secrets.token_hex(32))"

# 위 출력값을 .env 의 KNK_SECRET_KEY 에 붙여넣기
nano .env
```

`.env` 최종 모습:
```
KNK_SECRET_KEY=8a3f...64자리...c9e1
KNK_MODE=prod
KNK_HOST=0.0.0.0
KNK_PORT=8081
KNK_WORKERS=2
TZ=Asia/Seoul
```

⚠️ **절대 `.env`를 GitHub에 커밋 금지** (`.gitignore` 이미 등록됨).

---

## 5. 컨테이너 빌드 + 실행 (10분)

### 옵션 A — 자동 스크립트
```bash
cd /volume1/docker/knk-haist/src
bash deploy/setup_synology_container.sh
```

### 옵션 B — Container Manager GUI
1. Container Manager → 프로젝트 → 만들기
2. 경로: `/volume1/docker/knk-haist/src`
3. 소스: 기존 Dockerfile 선택
4. 빌드 + 실행

### 옵션 C — 수동 docker run
```bash
cd /volume1/docker/knk-haist/src
docker build -t knk-haist:latest .

docker run -d --name knk-haist \
    -p 8081:8081 \
    -v /volume1/docker/knk-haist/data:/app/data \
    -v /volume1/docker/knk-haist/uploads:/app/uploads \
    -v /volume1/docker/knk-haist/backups:/app/backups \
    --env-file /volume1/docker/knk-haist/.env \
    --restart unless-stopped \
    knk-haist:latest
```

---

## 6. 내부 동작 확인 (1분)

```bash
# 컨테이너 상태
docker ps | grep knk-haist

# 로그
docker logs -f knk-haist

# 내부 HTTP 응답
curl -I http://127.0.0.1:8081/login
# 기대: HTTP/1.1 200 OK

# 메신저와 충돌 확인 — 포트 5050 / 8081 분리됨
netstat -tlnp | grep -E '5050|8081'
```

---

## 7. DSM Reverse Proxy 설정 (5분)

DSM 웹콘솔 → **Control Panel → Login Portal → Advanced → Reverse Proxy → Create**

| 항목 | 값 |
|---|---|
| **Description** | KNK HAIST WORKS |
| **Source Protocol** | HTTPS |
| **Source Hostname** | haist.knk.co.kr |
| **Source Port** | 443 |
| **Destination Protocol** | HTTP |
| **Destination Hostname** | localhost |
| **Destination Port** | 8081 |

**Custom Header** 탭:
| Header | Value |
|---|---|
| Upgrade | $http_upgrade |
| Connection | $connection_upgrade |
| X-Real-IP | $remote_addr |
| X-Forwarded-For | $proxy_add_x_forwarded_for |
| X-Forwarded-Proto | $scheme |

저장.

---

## 8. SSL 인증서 (Let's Encrypt) — 자동

DSM → **Control Panel → Security → Certificate → Add → Add a new certificate**

- Domain name: `haist.knk.co.kr`
- Email: 대표 이메일
- Subject Alternative Name: 비워둠

→ Synology 가 자동으로 발급 + 90일마다 갱신.

생성된 인증서를 Reverse Proxy 의 haist.knk.co.kr 항목에 할당.

---

## 9. 외부 동작 확인

```
브라우저 → https://haist.knk.co.kr/login
```

- ✅ 자물쇠 아이콘 (HTTPS 정상)
- ✅ 로그인 화면 표시
- ✅ 평소 계정으로 로그인 → /home

---

## 10. 백업 자동화 (선택)

### 권장 — HyperBackup (이미 메신저 백업 설정 있을 가능성)
- DSM → HyperBackup → Backup task 추가
- 대상: `/volume1/docker/knk-haist/` 전체
- 일 1회, 30일 보존

### 보조 — cron + backup.sh
```bash
crontab -e
# 매일 02:00 백업
0 2 * * * /volume1/docker/knk-haist/src/deploy/backup.sh >> /volume1/docker/knk-haist/backups/cron.log 2>&1
```

---

## 11. 업데이트 (코드 수정 후)

```powershell
# Windows PC 에서
cd "C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\01_HAIST_WORKS"
./deploy/sync_to_synology.ps1 -Rebuild
```

또는 NAS에서:
```bash
cd /volume1/docker/knk-haist/src
git pull  # 또는 새 파일 받음
bash deploy/setup_synology_container.sh
```

---

## 12. 트러블슈팅

| 증상 | 원인 | 조치 |
|---|---|---|
| 컨테이너 즉시 종료 | `.env` 누락 / KNK_SECRET_KEY 기본값 | `docker logs knk-haist` 확인 |
| HTTPS 자물쇠 깨짐 | SSL 인증서 미할당 | DSM Certificate 에서 reassign |
| 로그인 후 빈 화면 | DB 권한 / 볼륨 마운트 오류 | `ls -la /volume1/docker/knk-haist/data` |
| 한글 깨짐 | 컨테이너 timezone | Dockerfile 에서 `Asia/Seoul` 고정됨 |
| 메신저와 포트 충돌 | 8081 다른 컨테이너 사용 | `docker ps -a` 확인, 포트 변경 |
| 외부에서 안 보임 | 방화벽 / DNS 미전파 | `nslookup haist.knk.co.kr` |

---

## 13. 보안 체크리스트 (외부 공개 전 필수)

- [ ] `.env` 의 KNK_SECRET_KEY 가 32+자 임의값 (개발 기본값 절대 금지)
- [ ] `.env` 의 KNK_MODE=prod
- [ ] 사용자 비밀번호 일제 재설정 권장
- [ ] HTTPS 강제 (HTTP 접근 시 자동 리다이렉트)
- [ ] HyperBackup 일 1회 자동 백업
- [ ] DSM 사용자 권한 분리 (haist 컨테이너 전용 uid 1000)
- [ ] DB 평문 SQLite — 민감 데이터 확인 후 암호화 검토
- [ ] 로그인 brute-force 방어 (rate limit 미들웨어 추가 권장)

---

## 14. 운영 명령 모음

```bash
# 상태
docker ps | grep knk-haist

# 로그 실시간
docker logs -f knk-haist

# 재시작
docker restart knk-haist

# 중단
docker stop knk-haist

# 컨테이너 안 셸 (디버깅)
docker exec -it knk-haist bash

# 이미지 재빌드 (코드 변경 시)
cd /volume1/docker/knk-haist/src
bash deploy/setup_synology_container.sh

# DB 직접 확인
docker exec -it knk-haist sqlite3 /app/data/knk.db
```

---

**관련 문서:**
- `Dockerfile` — 컨테이너 이미지 정의
- `.env.synology.example` — 환경변수 템플릿
- `deploy/nginx-synology.conf` — DSM Reverse Proxy 안 쓸 때 nginx conf
- `deploy/setup_synology_container.sh` — 자동 셋업 스크립트
- `deploy/sync_to_synology.ps1` — Windows → NAS 동기화
- `deploy/backup.sh` — DB·업로드 백업
- `10_KNK_Messenger/Synology_배포가이드.md` — 메신저 가이드 (같은 NAS, 같은 패턴)

---

# 🚀 방법 B 부록 — 실 배포 절차 (Auto, 2026-05-11 채택)

> **이 섹션이 실제 사용되는 절차입니다.**
> 본문(별도 컨테이너 방식)은 참고용으로만 유지.

## 환경

| 항목 | 값 |
|---|---|
| 컨테이너 | Synology Container Manager의 단일 Ubuntu 20.04 (host network 모드) |
| systemctl | ❌ 없음. **supervisord** 사용 |
| 메신저 | `/opt/knk_messenger/` + supervisord knk-messenger + nginx :8080 가동 중 |
| HAIST 추가 | `/opt/knk_haist/` + supervisord knk-haist + nginx :8090 |
| SSH (외부) | `ssh root@o.knknara.co.kr -p 31201` (PW: knk123!) |
| SSH (LAN) | `ssh root@192.168.12.5 -p 31201` |
| 외부 HTTP | o.knknara.co.kr:3310 → 컨테이너:80 (Web Station) |

## 1단계 — 코드 업로드 (Windows PC)

PowerShell 에서:
```powershell
cd "C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\01_HAIST_WORKS"
./deploy/upload_to_nas.ps1
# 비밀번호 입력 요청 2회: knk123!
```

→ tar 자동 생성 + scp 업로드 + 원격 압축 해제까지 자동.

## 2단계 — 컨테이너 안에서 셋업 (NAS SSH)

```bash
ssh root@o.knknara.co.kr -p 31201   # PW: knk123!

cd /opt/knk_haist
bash deploy/setup_ubuntu_container.sh
```

이 한 줄이 자동 처리:
- apt 패키지 추가 (python3 venv, build-essential, tesseract-ocr-kor, poppler-utils, supervisor, nginx)
- Python venv + requirements.txt 설치
- `.env` 자동 생성 (KNK_SECRET_KEY 임의 hex 64자, KNK_MODE=prod)
- supervisord 에 `knk-haist` 프로그램 등록 + 시작
- nginx 에 server block (`:8090`) 추가 + reload
- 헬스체크 (uvicorn :8081 + nginx :8090)

## 3단계 — 동작 확인 (SSH 안)

```bash
# 컨테이너 안 상태
supervisorctl status | grep knk-haist
# → knk-haist  RUNNING  pid xxxxx

# uvicorn 직접
curl -I http://127.0.0.1:8081/login   # HTTP 200 또는 303 OK

# nginx 프록시
curl -I http://127.0.0.1:8090/login   # HTTP 200 또는 303 OK

# 로그
tail -f /opt/knk_haist/logs/uvicorn.log
tail -f /opt/knk_haist/logs/uvicorn-error.log
```

## 4단계 — 외부 접속 라우팅 (대표/IT)

### 옵션 (α) 새 외부 포트 — ⭐ 권장 (가장 빠름)

회사 라우터 관리자 페이지:

| 외부 포트 | 프로토콜 | 내부 IP | 내부 포트 |
|---|---|---|---|
| 3320 | TCP | 192.168.12.5 (NAS) | 8090 (HAIST nginx) |

→ 외부 접속: **`http://o.knknara.co.kr:3320/login`**

### 옵션 (β) 하위 도메인 — 정식 (DNS 작업 필요)

1. 가비아 DNS A 레코드 추가: `haist.knknara.co.kr` → NAS 공인 IP
2. `/opt/knk_haist/deploy/nginx-knk-haist-server.conf` 의 `server_name _;` → `server_name haist.knknara.co.kr;` 로 교체
3. `supervisorctl restart knk-nginx` (또는 `nginx -s reload`)
4. DSM Reverse Proxy 안 쓰면 라우터 3310 → 컨테이너:8090 변경 + nginx server_name 분기로 메신저·HAIST 동시 처리
5. Let's Encrypt 발급 (DSM Certificate)
6. 외부 접속: **`https://haist.knknara.co.kr/`**

## 5단계 — 보안 사후 점검

```bash
# .env 권한 확인 (600)
ls -la /opt/knk_haist/.env

# SECRET_KEY 가 hex 64자 인지
grep KNK_SECRET_KEY /opt/knk_haist/.env

# prod 모드인지
grep KNK_MODE /opt/knk_haist/.env

# .env 가 git 추적 제외인지 (호스트 PC에서 확인)
```

⚠️ **대표 추가 작업 권장:**
- 사용자 비밀번호 일제 재설정 (외부 공개 직전)
- HyperBackup 으로 `/opt/knk_haist/data/` 자동 백업 추가
- 로그인 brute-force 방어 (rate limit 미들웨어 추가 검토)

## 6단계 — 운영 명령 모음

```bash
# 상태
supervisorctl status

# 재시작
supervisorctl restart knk-haist

# 중단
supervisorctl stop knk-haist

# 코드 업데이트 (Windows PC 에서 push 후 NAS 에서)
cd /opt/knk_haist
tar -xzf /tmp/knk_haist_sync.tar.gz   # upload_to_nas.ps1 이 자동 처리
supervisorctl restart knk-haist

# 로그
tail -100 /opt/knk_haist/logs/uvicorn.log
tail -100 /opt/knk_haist/logs/uvicorn-error.log

# DB 직접
sqlite3 /opt/knk_haist/data/knk.db

# nginx reload (server_name 등 변경 시)
nginx -t && supervisorctl restart knk-nginx
```

## 7단계 — supervisord 자동 시작 (재부팅 대비)

메신저 셋업 시 이미 처리된 경우 추가 작업 없음. 미처리면:

**(A) 컨테이너 entrypoint** (DSM Container Manager UI):
```
/usr/bin/supervisord -c /etc/supervisor/supervisord.conf -n
```

**(B) /root/.bash_profile**:
```bash
echo 'pgrep supervisord > /dev/null || /usr/bin/supervisord -c /etc/supervisor/supervisord.conf' >> /root/.bash_profile
```

## 8단계 — 트러블슈팅

| 증상 | 조치 |
|---|---|
| `supervisorctl: knk-haist 없음` | `supervisorctl reread && supervisorctl update` |
| uvicorn 즉시 종료 | `tail /opt/knk_haist/logs/uvicorn-error.log` — 보통 .env 누락 또는 venv 미설치 |
| `:8081` 응답 X | `supervisorctl status` 로 RUNNING 확인 / 포트 점유: `ss -tlnp \| grep 8081` |
| `:8090` 응답 X | `nginx -t` 로 conf 검증 / `supervisorctl restart knk-nginx` |
| 한글 깨짐 | `.env` 의 `TZ=Asia/Seoul` 확인 / supervisord environment LANG 확인 |
| `.env` SECRET_KEY 비어있음 | `rm .env && bash deploy/setup_ubuntu_container.sh` 재실행 |
| 8090 충돌 | nginx conf 의 `listen 8090` → 다른 포트로 변경 + 라우터도 같이 변경 |

---

**관련 파일 (deploy/):**
- `setup_ubuntu_container.sh` — 자동 셋업 (한 줄 실행)
- `supervisord-knk-haist.conf` — supervisord 프로그램 정의
- `nginx-knk-haist-server.conf` — nginx server block (:8090)
- `upload_to_nas.ps1` — Windows → NAS 업로드 자동화
- `backup.sh` — DB·업로드 백업 (cron 또는 HyperBackup 보조)
