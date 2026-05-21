# Synology NAS Docker 배포 가이드

> **2026-05-11 실배포 경험 반영** — 실제 환경: Synology NAS Container Manager 의 Ubuntu 20.04 단일 컨테이너에 SSH 직접 접속 운영. systemctl 없음(host network 모드), Synology Web Station이 호스트 :80 점유 중. 아래 "방법 B" 가 실제 채택된 경로.

---

## 두 가지 배포 방식 비교

| 방식 | 적합 환경 | 관리 도구 | 우리 채택 |
|---|---|---|---|
| **방법 A: Container Manager Project (docker-compose)** | 깔끔한 격리, 컨테이너 자동 재시작 | DSM Container Manager UI | 향후 권장 |
| **방법 B: 단일 Ubuntu 컨테이너 + SSH 운영** | NAS 컨테이너에 SSH 접근, supervisord 운영 | SSH + supervisorctl | ✅ 2026-05-11 채택 |

방법 A 는 아래 본문, 방법 B 는 "방법 B 부록" 참고.

---

KNK Messenger 를 Synology NAS의 Container Manager(=Docker)로 운영. **권장 시나리오** — 24/7 가동, UPS 자체 지원, Let's Encrypt SSL 자동, HyperBackup 통합.

> 이 가이드 한 페이지만 따라하면 끝납니다. 5단계, 약 30분 소요.

---

## 사전 조건

- Synology DSM 7.0+ (Container Manager 또는 Docker 패키지 설치 가능)
- DSM 관리자 계정
- 사내 회선 공인 IP (정적 권장)
- 가비아 도메인 권한 (`knknara.co.kr` DNS 수정)
- 회사 라우터 관리자 권한 (포트포워딩 설정용)

---

## 1단계 — Synology 패키지 설치 (DSM, 5분)

1. **DSM 패키지 센터** 열기
2. **Container Manager** 검색 → 설치 (DSM 7.2+; 구 DSM은 "Docker" 패키지)
3. 설치 후 좌측 메뉴 **Container Manager** 아이콘 확인

> ⚠️ Synology 모델별 지원 여부 확인: https://www.synology.com/dsm/packages/ContainerManager

---

## 2단계 — 코드 업로드 (File Station, 5분)

### 2-1. NAS 폴더 만들기
DSM **File Station** 에서:
- `/volume1/docker/knk-messenger/` 폴더 생성
- 하위에 `data/`, `backups/` 자동 생성됨 (컨테이너 첫 실행 시)

### 2-2. 코드 복사
**옵션 A — Windows에서 SMB 마운트 후 복사** (가장 쉬움)
1. 파일 탐색기에서 `\\<NAS-IP>\docker\knk-messenger` 접속
2. 로컬의 `10_KNK_Messenger\` 안 모든 파일 (단, `data/`, `backups/`, `.venv/` 제외) 드래그·복사

**옵션 B — SSH로 scp**
```powershell
ssh admin@<NAS-IP> "mkdir -p /volume1/docker/knk-messenger"
scp -r 10_KNK_Messenger/* admin@<NAS-IP>:/volume1/docker/knk-messenger/
```

### 2-3. 필수 파일 확인
`/volume1/docker/knk-messenger/` 안에 다음이 있어야:
- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt`
- `app.py`, `wsgi.py`
- `templates/`, `static/`
- `.env.synology.example`

### 2-4. .env 만들기 (꼭 직접 만들어야 함)
DSM File Station 에서 `.env.synology.example` 복사 → `.env` 로 이름변경 → 텍스트 편집기로 열기

`KNK_MSG_SECRET` 생성 (DSM 터미널 또는 Windows PowerShell):
```powershell
# Windows PowerShell
-join ((1..64) | %{ '{0:x}' -f (Get-Random -Max 16) })
```
또는
```bash
# NAS SSH (admin 사용자)
openssl rand -hex 32
```

생성된 64자 hex 문자열을 `.env` 의 `KNK_MSG_SECRET=` 뒤에 붙이고 저장.

> ⚠️ `.env` 는 절대 git/외부에 올리지 마세요.

---

## 3단계 — 컨테이너 빌드 + 실행 (Container Manager, 5분)

### 3-1. 프로젝트 생성
1. **Container Manager** → 좌측 **프로젝트** → **생성**
2. 입력:
   - 프로젝트 이름: `knk-messenger`
   - 경로: `/docker/knk-messenger` (file station 폴더 선택)
   - 소스: `docker-compose.yml 사용`
   - 자동으로 동일 폴더의 compose 파일 인식
3. **다음** → 웹 포털 설정은 스킵 (Reverse Proxy 별도 사용)
4. **완료** → "지금 빌드하고 시작" 체크

빌드 진행상황이 로그 창에 보임. 처음 빌드는 ~3-5분 (이미지 다운로드 + pip install).

### 3-2. 동작 확인
1. Container Manager → **컨테이너** 탭에서 `knk-messenger` 가 **실행 중** 표시
2. 컨테이너 클릭 → **로그** 탭:
   - `KNK Messenger - server start` 같은 줄 보이면 OK
   - `eventlet` 또는 `gunicorn worker started` 메시지 정상

### 3-3. NAS 내부에서 접속 테스트
브라우저에서:
```
http://<NAS-IP>:5050
```
→ KNK 메신저 로그인 화면이 보이면 컨테이너 OK.

---

## 4단계 — 가비아 DNS + 라우터 포트포워딩 (대표/IT, 5분)

### 4-1. NAS 공인 IP 확인
NAS SSH (또는 컴퓨터에서) :
```bash
curl https://api.ipify.org
```
출력 예: `211.234.xxx.xxx`

### 4-2. 가비아 DNS A 레코드
가비아 → DNS 관리 → `knknara.co.kr`:
- Type: `A`
- Host: `msg`
- Value: `211.234.xxx.xxx` (위 공인 IP)
- TTL: 600

### 4-3. 회사 라우터 포트포워딩
라우터 관리자 페이지 → 포트포워딩:
| 외부 포트 | 프로토콜 | 내부 IP | 내부 포트 |
|---|---|---|---|
| 80  | TCP | <NAS LAN IP> | 80  |
| 443 | TCP | <NAS LAN IP> | 443 |

> **NAS의 80/443은 DSM이 사용 중**. DSM Reverse Proxy 가 80/443에서 받아서 컨테이너 5050 으로 프록시함. 라우터 포워딩은 NAS 의 80/443 으로.

### 4-4. DNS 전파 확인
1~10분 후 PowerShell:
```powershell
nslookup msg.knknara.co.kr 8.8.8.8
```
→ 위 공인 IP 가 보이면 OK.

---

## 5단계 — Synology Reverse Proxy + Let's Encrypt SSL (DSM, 10분)

### 5-1. Reverse Proxy 규칙 추가
DSM **제어판** → **로그인 포털** → **고급** → **역방향 프록시** → **만들기**

| 설정 | 값 |
|---|---|
| 설명 | KNK Messenger |
| 소스 프로토콜 | `HTTPS` |
| 소스 호스트 이름 | `msg.knknara.co.kr` |
| 소스 포트 | `443` |
| 대상 프로토콜 | `HTTP` |
| 대상 호스트 이름 | `localhost` |
| 대상 포트 | `5050` |

**[사용자 정의 헤더] 탭** → **만들기** → **WebSocket** 템플릿 적용 (Socket.IO 동작에 필수):
- `Upgrade` ← `$http_upgrade`
- `Connection` ← `$connection_upgrade`

**⚠️ 대용량 업로드 (DWG·동영상) 위해 추가 설정 필수**:
DSM Reverse Proxy 는 기본 100MB 한도. `client_max_body_size` 600MB 로 변경:
1. SSH 접속 후
   ```bash
   sudo nano /usr/syno/share/nginx/server.mustache
   ```
   또는 `/etc/nginx/conf.d/` 안 사용자 conf 파일에 추가:
   ```
   client_max_body_size 600M;
   client_body_timeout 600s;
   proxy_read_timeout 600s;
   proxy_send_timeout 600s;
   ```
2. `sudo synoservicectl --restart nginx` 또는 DSM 재기동
3. (대안) 직접 DSM nginx 가 막히면 라우터에서 외부 443 → NAS 의 다른 포트(예: 5443)로 매핑 + 컨테이너 직접 노출

(또는 수동 추가):
| 헤더 이름 | 값 |
|---|---|
| `Upgrade` | `$http_upgrade` |
| `Connection` | `Upgrade` |
| `X-Real-IP` | `$remote_addr` |
| `X-Forwarded-For` | `$proxy_add_x_forwarded_for` |
| `X-Forwarded-Proto` | `https` |

**저장** → 적용까지 ~5초.

### 5-2. Let's Encrypt 인증서 발급
DSM **제어판** → **보안** → **인증서** → **추가** → **새 인증서 추가**:
1. **Let's Encrypt 에서 인증서 가져오기** 선택
2. 도메인 이름: `msg.knknara.co.kr`
3. 이메일: `admin@knknara.co.kr`
4. **다음** → 발급까지 ~30초

> 💡 발급 실패 시: 4-3 라우터 포트포워딩이 NAS LAN IP의 **80번 포트**까지 도달하는지 확인. Let's Encrypt 가 80 으로 검증.

### 5-3. 인증서 매핑
인증서 목록에서 새 인증서 선택 → **설정** → 다음 서비스에 적용:
- `msg.knknara.co.kr` (역방향 프록시 항목)

### 5-4. 외부 접속 테스트
**휴대폰을 LTE/5G로** 바꾸고 (회사 와이파이 끊기):
- https://msg.knknara.co.kr 접속
- 자물쇠 아이콘 ✓ + KNK 로그인 화면 → **성공**

---

## 6단계 — 자동 백업 (HyperBackup, 5분, 선택)

DSM **HyperBackup**:
1. 백업 작업 만들기 → **데이터 백업 작업**
2. 백업 대상 선택:
   - **로컬 폴더 & USB** (외장 디스크)
   - 또는 **Synology C2** / 원격 NAS / 클라우드(S3/B2)
3. 백업 대상 폴더: `/docker/knk-messenger/data` 와 `/docker/knk-messenger/backups`
4. 스케줄: 매일 03:00
5. 보관: 30일

**또는** 컨테이너 내부 backup.sh 가 만든 `/backups/` 만 NAS 다른 폴더로 정기 동기화.

---

## 운영 명령어 (NAS SSH 또는 Container Manager UI)

### Container Manager UI
- 재시작: 컨테이너 선택 → 작업 → 다시 시작
- 로그: 컨테이너 선택 → 로그 탭
- 콘솔: 컨테이너 선택 → 터미널 탭 (디버깅용)
- 중지: 컨테이너 선택 → 작업 → 중지

### SSH (admin 계정)
```bash
cd /volume1/docker/knk-messenger

# 재시작
sudo docker compose restart

# 로그 실시간
sudo docker compose logs -f knk-messenger

# 중지·시작
sudo docker compose down
sudo docker compose up -d

# 코드 업데이트 후 재빌드
sudo docker compose up -d --build

# 백업 즉시 (컨테이너 안에서)
sudo docker exec knk-messenger python /app/backup.py

# DB 직접 접근 (디버깅)
sudo sqlite3 /volume1/docker/knk-messenger/data/messenger.db
```

---

## 코드 업데이트 워크플로우 (개발 사이클)

빅터가 로컬에서 코드 수정 후:

### 옵션 A — Windows에서 SMB 동기화 (수동, 가장 쉬움)
1. 파일 탐색기에서 `\\<NAS-IP>\docker\knk-messenger` 열기
2. 변경된 파일만 복사
3. NAS SSH 또는 Container Manager 에서 컨테이너 재시작

### 옵션 B — sync 스크립트 (자동)
대표 PC PowerShell:
```powershell
# 1번만 환경변수 설정
[Environment]::SetEnvironmentVariable("KNK_NAS_HOST", "<NAS LAN IP>", "User")
[Environment]::SetEnvironmentVariable("KNK_NAS_USER", "admin", "User")
[Environment]::SetEnvironmentVariable("KNK_NAS_PATH", "/volume1/docker/knk-messenger", "User")

# 동기화 (변경 시마다)
.\deploy\sync_to_synology.ps1
```
→ 변경 파일 SMB로 복사 + SSH 로 `docker compose restart` + 헬스체크.

> 옵션 B 의 sync 스크립트는 별도 파일 (`deploy/sync_to_synology.ps1`).

---

## 운영 모드 전환 (며칠 안정 후)

`.env` 의 `KNK_MSG_ENV=development` → `production` 으로 변경 후:
```bash
sudo docker compose restart
```

이걸로:
- HSTS · secure 쿠키 · CSP 보안 헤더 활성
- CORS 가 `*` → 실제 도메인 제한 (이미 .env 에 도메인 있음)
- 정적 파일 캐시 1일

---

## 비상시 대응

| 증상 | 명령 |
|---|---|
| https://msg.knknara.co.kr 안 열림 | DSM → Container Manager → 컨테이너 상태 확인 |
| 502 Bad Gateway | DSM Reverse Proxy 설정 확인 (5-1) |
| WebSocket 연결 실패 | Reverse Proxy WebSocket 헤더 확인 (5-1 후반) |
| SSL 만료 | DSM 보안 → 인증서 → 갱신 (자동이지만 강제 가능) |
| 컨테이너 죽음 | Container Manager 로그 확인 → SSH 로 `docker compose logs` |
| DB 손상 | `/volume1/docker/knk-messenger/data/messenger.db` HyperBackup 에서 복원 |
| 디스크 full | DSM 저장소 관리자 → 사용량 확인. 백업 보관 기간 단축 |

---

## 비용 (월)

| 항목 | 비용 |
|---|---|
| Synology NAS (이미 보유) | ₩0 |
| 가비아 서브도메인 `msg` | ₩0 |
| Let's Encrypt SSL | ₩0 |
| (선택) 사내 회선 정적 IP | ₩10,000~30,000 |
| **합계** | **₩0 ~ ₩30,000/월** |

상용 메신저(유료) 140명 약 ₩406,000/월 대비 **13~∞배 절감**.

---

## 빅터 전권 가능 항목 (Synology Docker 환경)

| 작업 | 방법 |
|---|---|
| 코드 업데이트 | `.\deploy\sync_to_synology.ps1` |
| 컨테이너 재시작 | 사용자 PC에서 `ssh admin@NAS sudo docker compose -f /volume1/docker/knk-messenger/docker-compose.yml restart` |
| 로그 확인 | DSM Container Manager UI 또는 SSH |
| dev → 운영 모드 전환 | `.env` 의 `KNK_MSG_ENV` 수정 + 재시작 |
| 사용자 비번 리셋 | `docker exec` 로 컨테이너 진입 + Python 스크립트 |

대표 결재 필요: 도메인 변경, NAS 사양 업그레이드, 데이터 거주지 이전.

---

# 방법 B 부록 — Synology Container Ubuntu 20.04 단일 SSH 운영 (2026-05-11 실배포)

## 환경
- Synology Container Manager 의 Ubuntu 20.04 이미지를 **호스트 네트워크 모드**로 실행
- 컨테이너 내부에 직접 SSH 접속 가능 (PID 1 = bash, **systemd 없음**)
- Synology DSM Web Station 의 nginx 가 호스트 `:80` 점유 중 → 우리 nginx 는 `:8080` 사용

## 접속 정보 (예시 — 실 운영 값으로 교체)
- SSH 외부: `ssh root@o.knknara.co.kr -p 31201`
- SSH LAN: `ssh root@192.168.12.5 -p 31201`
- 라우터: 외부 3310 → 컨테이너:80 / 외부 31201 → 컨테이너:22

## 1단계 — 코드 업로드
대표 PC PowerShell:
```powershell
cd "C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\10_KNK_Messenger"
# 데이터·캐시 제외하고 tar
tar --exclude=data --exclude=backups --exclude=.venv --exclude=__pycache__ -czf knk_sync.tar.gz *

# scp (sshd가 로그인 시 stderr 메시지 찍으면 scp 실패함. base64 stream 우회 가능)
scp -P 31201 knk_sync.tar.gz root@o.knknara.co.kr:/tmp/
```

서버에서:
```bash
ssh root@o.knknara.co.kr -p 31201
mkdir -p /opt/knk_messenger && cd /opt/knk_messenger
tar -xzf /tmp/knk_sync.tar.gz && rm /tmp/knk_sync.tar.gz
chmod +x deploy/*.sh
```

## 2단계 — 1줄 셋업 스크립트
```bash
cd /opt/knk_messenger
bash deploy/setup_synology_container.sh
```

이 한 줄이 처리:
- apt 패키지 설치 (python3·nginx·supervisor·sqlite3·build-essential·libjpeg-dev·libpng-dev 등)
- Python venv + requirements 설치 (anthropic 포함)
- `.env` 자동 생성 (SECRET·ADMIN_TOKEN 자동 hex)
- supervisord 등록 + 시작 (gunicorn + nginx 두 프로그램)
- 헬스 체크

## 3단계 — 포트 충돌 해결 (호스트 :80 점유 시)
스크립트가 nginx spawn error 출력하면:
```bash
# 우리 nginx 를 8080 으로 변경
sed -i 's/listen 80 default_server;/listen 8080 default_server;/g; s/listen \[::\]:80 default_server;/listen [::]:8080 default_server;/g' /etc/nginx/sites-available/knk-messenger
nginx -t && supervisorctl restart knk-nginx
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8080/login
```

200/302 이면 OK.

## 4단계 — 외부 접속 라우팅 (3가지 옵션)

호스트 :80 이 Synology Web Station 차지 중이므로:

### 옵션 (a) 라우터 매핑 변경 ⭐ 권장
DSM 외부 액세스/QuickConnect 또는 Synology Router 관리:
- 기존: 외부 3310 → 컨테이너:80 (NAS Web Station 응답)
- 변경: **외부 3310 → 컨테이너:8080** (우리 메신저)

### 옵션 (b) Synology Web Station Reverse Proxy
DSM 제어판 → 로그인 포털 → 고급 → 역방향 프록시 → 만들기:
- 소스: HTTPS / `msg.knknara.co.kr` / 443
- 대상: HTTP / localhost / 8080
- WebSocket 헤더 추가 (Upgrade / Connection)
- Let's Encrypt 인증서 발급

이 방법이 HTTPS 까지 한 번에 해결되어 PWA·Web Push 정식 가능.

### 옵션 (c) gunicorn 직접 노출
nginx 빼고 gunicorn :5050 만:
- 라우터 외부 3310 → 컨테이너:5050
- 단점: 정적 파일 캐싱 X, 향후 HTTPS 추가 시 nginx 재구축 필요

## 5단계 — supervisord 자동 시작 (재부팅 대비)
컨테이너 PID 1 이 supervisord 가 아니라서 NAS/컨테이너 재시작 시 자동 시작 X. 두 가지 대응:

**(A) 컨테이너 entrypoint 변경** (DSM Container Manager UI):
```
/usr/bin/supervisord -c /etc/supervisor/supervisord.conf -n
```

**(B) /root/.bash_profile 에 자동 시작 추가** (SSH 로그인 트리거):
```bash
echo 'pgrep supervisord > /dev/null || /usr/bin/supervisord -c /etc/supervisor/supervisord.conf' >> /root/.bash_profile
```

## 운영 명령어
```bash
# 상태
supervisorctl status
# 재시작
supervisorctl restart knk-messenger
# 로그 (gunicorn)
tail -f /opt/knk_messenger/logs/gunicorn.log
# 로그 (nginx)
tail -f /var/log/nginx/access.log /var/log/nginx/error.log
# 코드 업데이트
cd /opt/knk_messenger && tar -xzf /tmp/knk_sync.tar.gz && supervisorctl restart knk-messenger
# .env 수정 후 재시작 (ANTHROPIC_API_KEY 등록 시)
vi .env && supervisorctl restart knk-messenger
```
