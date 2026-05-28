# 🚀 HAIST WORKS — Synology NAS 설치 가이드

> **목표**: `https://haist.knknara.co.kr/` 에 HAIST WORKS 가동
> **방식**: 메신저와 같은 NAS · 같은 도메인 · **별도 컨테이너** (메신저 무영향)
> **소요**: 약 30~40분
> **작성**: 2026-05-28 / 빅터
> **메신저 영향**: **0** (모든 작업은 분리된 컨테이너·포트·경로)

---

## 📋 사전 준비 (체크리스트)

- [ ] NAS SSH 접속 가능 (`o.knknara.co.kr:31201`, root)
- [ ] 메신저가 현재 정상 작동 중 (`https://haist.knknara.co.kr/msg/` 접속 OK)
- [ ] DSM Container Manager (Docker) 패키지 설치돼 있음
- [ ] 여유 디스크 ≥ 10GB
- [ ] **임의 32자 SECRET_KEY** 1개 미리 준비 (아래 명령으로 생성)

### SECRET_KEY 생성 (대표 PC에서 한 번)
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```
→ 출력된 64자 16진수 문자열 메모장에 잠시 보관. **카톡·메일·git 절대 금지**.

---

## 1단계 — GitHub Private Repo 생성 (대표, 5분)

> 메신저(`knk-messenger`) 와 동일 패턴.

1. 브라우저 → `https://github.com/top00151-commits` 로그인
2. **New** → Repository name: `knk-works` → **Private** 체크 → Create
3. 생성된 repo 의 URL 메모: `git@github.com:top00151-commits/knk-works.git`

### 로컬에서 push 준비 (빅터가 도와줄 부분 — 또는 대표 직접)
```powershell
cd "C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\01_HAIST_WORKS"
git init
git remote add origin git@github.com:top00151-commits/knk-works.git
git add .
git commit -m "초기 커밋 — HAIST WORKS NAS 배포용"
git branch -M main
git push -u origin main
```

> ⚠️ SSH 키가 GitHub 에 등록돼 있어야 함. 메신저 push 가능하면 같은 키 그대로 사용 가능.

---

## 2단계 — NAS SSH 접속 (대표, 2분)

```bash
ssh -p 31201 root@o.knknara.co.kr
```

비밀번호 입력 → 프롬프트 (`root@DSM:~#`) 나오면 OK.

---

## 3단계 — 디렉터리 + 코드 배치 (5분)

```bash
# 작업 디렉터리 생성 (메신저: /opt/knk_messenger / HAIST WORKS: /opt/knk_haist)
mkdir -p /volume1/docker/knk-haist/data
mkdir -p /volume1/docker/knk-haist/uploads
mkdir -p /volume1/docker/knk-haist/backups
mkdir -p /volume1/docker/knk-haist/static

# 코드 받기 (GitHub 에서 clone)
cd /opt
git clone git@github.com:top00151-commits/knk-works.git knk_haist
cd knk_haist
```

> SSH 키 인증이 안되면: `git clone https://github.com/top00151-commits/knk-works.git knk_haist` + 토큰.

---

## 4단계 — .env 환경 설정 (3분)

```bash
# 템플릿 복사
cp /opt/knk_haist/deploy/.env.example /volume1/docker/knk-haist/.env

# 편집 (vi 또는 nano)
nano /volume1/docker/knk-haist/.env
```

다음 값을 채우세요:
```
KNK_SECRET_KEY=<위에서 미리 생성한 64자 16진수>
```

저장 → 종료 (`Ctrl+O` → `Enter` → `Ctrl+X` in nano).

권한 보호:
```bash
chmod 600 /volume1/docker/knk-haist/.env
```

---

## 5단계 — Docker 이미지 빌드 + 컨테이너 실행 (10분)

```bash
cd /opt/knk_haist

# 이미지 빌드 (첫 빌드는 5~8분, Tesseract OCR 설치 포함)
docker build -t knk-haist:latest .

# 기존 컨테이너 정리 (있을 경우)
docker stop knk-haist 2>/dev/null || true
docker rm knk-haist 2>/dev/null || true

# 컨테이너 실행
docker run -d --name knk-haist \
  -p 8081:8081 \
  -v /volume1/docker/knk-haist/data:/app/data \
  -v /volume1/docker/knk-haist/uploads:/app/uploads \
  -v /volume1/docker/knk-haist/backups:/app/backups \
  --env-file /volume1/docker/knk-haist/.env \
  --restart unless-stopped \
  knk-haist:latest

# 컨테이너 가동 확인
docker ps | grep knk-haist
# STATUS 가 'Up X seconds' 이어야 함

# 컨테이너 내부 헬스체크 (NAS 안에서)
curl -fsS http://127.0.0.1:8081/login | head -3
# HTML <!DOCTYPE html> ... 가 나오면 OK
```

문제 발생 시:
```bash
docker logs --tail 100 knk-haist
```

---

## 6단계 — DSM Reverse Proxy 설정 (가장 중요 · 10분)

**DSM 웹 UI 에서:**

1. **Control Panel** → **Login Portal** → **Advanced** → **Reverse Proxy**
2. **Create** 클릭
3. 다음 입력:

| 필드 | 값 |
|---|---|
| **Description** | KNK HAIST WORKS |
| **Source Protocol** | HTTPS |
| **Source Hostname** | `haist.knknara.co.kr` |
| **Source Port** | `443` |
| **Destination Protocol** | HTTP |
| **Destination Hostname** | `localhost` |
| **Destination Port** | `8081` |

4. **Custom Header** 탭 →  WebSocket 자동 헤더 추가:
   - Click **Create → WebSocket**
   - (HAIST WORKS 는 WebSocket 미사용이지만 켜두면 무해)

5. **Advanced Settings** 탭 →
   - **HSTS**: 활성화
   - **HTTP/2**: 활성화

6. **Save** 클릭

### ⚠️ 메신저 `/msg/` 와의 공존 확인

DSM Reverse Proxy 는 **나중에 만든 규칙이 우선** 적용될 수 있어서, 메신저 규칙(`/msg/`)도 점검:

1. Reverse Proxy 목록에서 메신저 규칙 확인
2. 메신저 규칙이 **path-specific** (`/msg/...`) 이면 OK — HAIST WORKS 의 `/` 와 자동 공존
3. 메신저 규칙이 **catch-all** (`/` 포함) 이면 → HAIST WORKS 규칙을 메신저 위로 올려 우선순위 조정
   - 또는 메신저 규칙의 path 를 `/msg/*` 로 명시적 제한

---

## 7단계 — 검증 (5분)

### 브라우저에서:

1. `https://haist.knknara.co.kr/` 접속 → **HAIST WORKS 로그인 화면** 표시되면 OK ✅
2. `https://haist.knknara.co.kr/msg/` 접속 → **메신저 정상 작동** 확인 ✅
3. 두 시스템이 동시에 잘 도는지 확인

### NAS SSH 에서:
```bash
# HAIST WORKS 컨테이너 상태
docker ps | grep knk-haist
# 'Up X minutes (healthy)' 이어야 함 (헬스체크 통과)

# 메신저 영향 확인
docker ps | grep knk-messenger
# 'Up' 그대로

# 로그 확인 (HAIST WORKS)
docker logs --tail 50 knk-haist
# Uvicorn running on http://0.0.0.0:8081 보이면 OK
```

---

## 8단계 — 백업 cron 등록 (3분)

NAS SSH 에서:
```bash
# 백업 스크립트 권한
chmod +x /opt/knk_haist/deploy/backup.sh

# DSM 작업 스케줄러 또는 cron
crontab -e
```

추가:
```
# HAIST WORKS — 매일 새벽 3시 SQLite 백업 (메신저와 같은 시간대지만 별도 파일)
0 3 * * * /opt/knk_haist/deploy/backup.sh >> /volume1/docker/knk-haist/backups/cron.log 2>&1
```

저장 → 종료.

---

## 9단계 — 데이터 이전 (선택, 기존 데이터 있을 때만)

### 옵션 A — 새 빈 DB 로 시작 ⭐ 권장
- 별도 작업 없음. 첫 실행 시 DB 자동 생성, 시드 사용자 등록됨.
- 직원 합류하면서 실 데이터 입력.

### 옵션 B — 현 PC 데이터 그대로 이전
대표 PC PowerShell:
```powershell
$KEY = "C:\Users\top00\.ssh\<your_nas_key>"   # 메신저 sync 때 쓰는 동일 키
scp -P 31201 -i $KEY "C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\01_HAIST_WORKS\data\knk.db" `
    root@o.knknara.co.kr:/volume1/docker/knk-haist/data/knk.db
```

NAS 에서:
```bash
chown -R 1000:1000 /volume1/docker/knk-haist/data
docker restart knk-haist
```

---

## 10단계 — 로컬 → NAS 자동 sync 설정 (선택, 추후 코드 수정 시 편리)

대표 PC PowerShell:
```powershell
cd "C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\01_HAIST_WORKS"
.\deploy\sync_to_synology.ps1
```
→ 코드 변경 시 1줄 sync (메신저 패턴 동일).

> 처음 한 번은 환경변수 설정 필요:
> ```powershell
> [Environment]::SetEnvironmentVariable("KNK_HAIST_NAS_HOST", "o.knknara.co.kr", "User")
> [Environment]::SetEnvironmentVariable("KNK_HAIST_NAS_PORT", "31201", "User")
> [Environment]::SetEnvironmentVariable("KNK_HAIST_NAS_KEY", "C:\Users\top00\.ssh\<your_key>", "User")
> ```

---

## 🚨 장애 대응

### HAIST WORKS 응답 없음
```bash
# 1) 컨테이너 상태 확인
docker ps -a | grep knk-haist

# 2) 재시작
docker restart knk-haist

# 3) 로그 확인
docker logs --tail 200 knk-haist
```

### 메신저까지 깨졌을 경우 (긴급 롤백)
```bash
# 1) HAIST WORKS 컨테이너 중지 (메신저는 영향 없어야 정상)
docker stop knk-haist

# 2) DSM Reverse Proxy 의 HAIST WORKS 규칙 비활성화
#    (DSM UI 에서 토글로 끄기)

# 3) 메신저 정상 동작 확인
curl -fsS https://haist.knknara.co.kr/msg/healthz
```

→ HAIST WORKS 만 끄면 메신저는 그대로 살아있어야 함 (분리 설계).

### HAIST WORKS 헬스체크
- 외부: `https://haist.knknara.co.kr/login` (200 응답 + 로그인 화면)
- 내부: `curl http://127.0.0.1:8081/login` (NAS SSH 안에서)

---

## 📞 빅터 (개발) 에게 보고할 것

다음 중 하나라도 발생하면 알려주세요:
- 메신저 정상인데 HAIST WORKS 만 502/503 → 컨테이너 로그 마지막 50줄
- 메신저까지 함께 깨짐 → DSM Reverse Proxy 설정 + nginx 상태
- 빌드 실패 → `docker build` 마지막 에러 메시지
- `/login` 접속은 되는데 화면이 깨짐 → 브라우저 콘솔 에러

---

## ✅ 완료 후 다음 단계

1. **며칠 단독 사용** — 대표 단독으로 실 업무에 써보며 안정 확인
2. **운영 모드 점검** — `.env` 의 `KNK_MODE=prod` 가 적용됐는지 (`docker logs knk-haist` 에서 "운영" 표시 확인)
3. **영업팀 5명 합류** — URL + ID/임시비번 안내 (메신저 패턴)
4. **전사 합류** — 부서별 단계적 합류
5. **VN 법인 합류** — 한·베 이중 안내 (메신저와 동시 OK)
6. **AI 활성** — Anthropic/OpenAI 결제 풀리면 `.env` 에 API_KEY 1줄 추가 + 컨테이너 재시작

---

*작성: 빅터(Claude) · 2026-05-28*
*문의·이슈 보고: 대표(김정락) 통해 빅터에게 전달*
