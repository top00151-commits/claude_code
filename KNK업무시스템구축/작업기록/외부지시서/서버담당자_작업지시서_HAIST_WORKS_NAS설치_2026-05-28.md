# 🔧 서버 담당자 작업 지시서 — HAIST WORKS NAS 설치

> **요청자**: 김정락 대표이사 / ㈜케이엔케이
> **요청일**: 2026-05-28
> **수신**: KNK 서버(NAS) 담당자
> **건명**: 사내 NAS (메신저 운영 중) 에 **HAIST WORKS** 웹 시스템 추가 설치 + DSM Reverse Proxy 설정
> **소요 예상**: 30~40분
> **메신저 운영 영향**: **0** (별도 컨테이너 · 별도 포트 · 별도 디렉터리)
> **긴급도**: 보통 (1주 이내)

---

## 1. 개요

**HAIST WORKS** — KNK 사내 업무 통합 플랫폼 (FastAPI + SQLite + Jinja2 / 자체 개발) 을
현재 메신저가 운영 중인 **같은 NAS, 같은 도메인 (`haist.knknara.co.kr`)** 에 추가 설치.

**완료 후 접속 주소:**

| 시스템 | 주소 |
|---|---|
| **HAIST WORKS** (이번 신규) | `https://haist.knknara.co.kr/` |
| 메신저 (기존, 그대로) | `https://haist.knknara.co.kr/msg/` |

---

## 2. 이미 완료된 사항 (담당자 작업 불필요)

| 항목 | 상태 |
|---|---|
| GitHub Private 리포지토리 생성 | ✅ 완료 — `https://github.com/top00151-commits/knk-haist-works` |
| 코드 push (333 파일, 약 30MB) | ✅ 완료 (DB·credentials·uploads 는 제외돼 있음) |
| Dockerfile · deploy/ 자산 (nginx·supervisor·backup 등) | ✅ 완료 (repo 안 `deploy/` 폴더) |
| 설치 가이드 (이 문서의 상세판) | ✅ `deploy/HAIST_WORKS_NAS_설치가이드.md` |
| `.env.example` 템플릿 | ✅ `deploy/.env.example` |

---

## 3. 담당자 작업 (체크리스트)

| 단계 | 작업 | 소요 |
|---|---|---|
| [ ] **① 사전 점검** | NAS 디스크 여유 / 포트 8081 사용 가능 / Container Manager 설치 확인 | 2분 |
| [ ] **② SECRET_KEY 생성** | 64자 임의 hex (보안 — 파일·메일 X) | 1분 |
| [ ] **③ 디렉터리 + git clone** | `/volume1/docker/knk-haist/` + `/opt/knk_haist/` | 5분 |
| [ ] **④ .env 작성** | SECRET_KEY + 모드 설정 | 3분 |
| [ ] **⑤ Docker 이미지 빌드** | `docker build -t knk-haist:latest .` | 5~8분 |
| [ ] **⑥ 컨테이너 실행** | port 8081, --restart unless-stopped | 1분 |
| [ ] **⑦ 내부 헬스체크** | `curl http://127.0.0.1:8081/login` | 1분 |
| [ ] **⑧ DSM Reverse Proxy** | `/` → 컨테이너 8081 (가장 중요) | 5분 |
| [ ] **⑨ 외부 접속 검증** | `https://haist.knknara.co.kr/` | 2분 |
| [ ] **⑩ 메신저 영향 확인** | `https://haist.knknara.co.kr/msg/` 정상 | 1분 |
| [ ] **⑪ 백업 cron 등록** | 매일 03시 SQLite 백업 | 3분 |

---

## 4. 단계별 상세 명령어 (NAS SSH 안에서 복붙)

### ① SSH 접속

본인 PC PowerShell/터미널:
```
ssh -p 31201 root@o.knknara.co.kr
```

> 비밀번호 입력 시 화면에 안 보이는 게 정상 (Linux SSH 표준).

### ② SECRET_KEY 생성

NAS SSH 안에서:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

→ 출력된 64자 hex 문자열을 **메모장에 1회용 보관** (NAS .env 에만 들어갈 값).
**카톡·메일·git 절대 X.**

### ③ 디렉터리 + git clone

```bash
# 데이터 볼륨 (영속 저장)
mkdir -p /volume1/docker/knk-haist/data
mkdir -p /volume1/docker/knk-haist/uploads
mkdir -p /volume1/docker/knk-haist/backups

# 코드 받기 (private repo)
cd /opt
git clone https://github.com/top00151-commits/knk-haist-works.git knk_haist
cd knk_haist
ls -la
# Dockerfile, app/, deploy/, requirements.txt 등 보이면 OK
```

> private repo 라 username + Personal Access Token (PAT) 요구할 수 있음.
> PAT 발급은 김정락 대표에게 요청 (또는 메신저 배포 때 쓰던 토큰 재활용).

### ④ .env 작성

```bash
cp /opt/knk_haist/deploy/.env.example /volume1/docker/knk-haist/.env
nano /volume1/docker/knk-haist/.env
```

다음만 채우기 (다른 줄은 그대로):
```
KNK_SECRET_KEY=<②에서 생성한 64자 hex>
```

저장: `Ctrl+O` → `Enter` → `Ctrl+X`

권한 보호:
```bash
chmod 600 /volume1/docker/knk-haist/.env
ls -la /volume1/docker/knk-haist/.env
# -rw------- 1 root root ... 표시되면 OK
```

### ⑤ Docker 이미지 빌드

```bash
cd /opt/knk_haist
docker build -t knk-haist:latest .
```

> 5~8분 소요 (Ubuntu 20.04 + Python + Tesseract OCR + 의존성).
> 끝에 `Successfully tagged knk-haist:latest` 보이면 성공.

### ⑥ 컨테이너 실행

```bash
# 기존 컨테이너 있으면 정리 (재실행 대비)
docker stop knk-haist 2>/dev/null
docker rm   knk-haist 2>/dev/null

# 실행
docker run -d --name knk-haist \
  -p 8081:8081 \
  -v /volume1/docker/knk-haist/data:/app/data \
  -v /volume1/docker/knk-haist/uploads:/app/uploads \
  -v /volume1/docker/knk-haist/backups:/app/backups \
  --env-file /volume1/docker/knk-haist/.env \
  --restart unless-stopped \
  knk-haist:latest

# 상태 확인
docker ps | grep knk-haist
# STATUS 컬럼이 'Up X seconds' 이면 OK
```

### ⑦ 내부 헬스체크

```bash
# 10초 대기 후 응답 확인
sleep 10
curl -fsS http://127.0.0.1:8081/login | head -3
# HTML <!DOCTYPE html>... 가 보이면 OK ✅

# 로그도 확인
docker logs --tail 30 knk-haist
# 'Uvicorn running on http://0.0.0.0:8081' 보이면 정상
```

> 실패 시 → 아래 §6 장애 대응

### ⑧ DSM Reverse Proxy 설정 ⭐ 가장 중요 ⭐

**DSM 웹 UI (`https://o.knknara.co.kr:5001`) 에서:**

1. **제어판 → 로그인 포털 → 고급 → 역방향 프록시** (Control Panel → Login Portal → Advanced → Reverse Proxy)
2. **생성** 클릭
3. 입력:

| 필드 | 값 |
|---|---|
| **설명** | KNK HAIST WORKS |
| **소스 프로토콜** | HTTPS |
| **소스 호스트 이름** | `haist.knknara.co.kr` |
| **소스 포트** | `443` |
| **HSTS 활성화** | ✅ |
| **HTTP/2 활성화** | ✅ |
| **대상 프로토콜** | HTTP |
| **대상 호스트 이름** | `localhost` |
| **대상 포트** | `8081` |

4. **저장** 클릭

### ⚠️ 메신저 `/msg/` 와의 공존 — 매우 중요

DSM Reverse Proxy 는 **나중 추가된 규칙이 우선** 적용될 수 있으므로:

1. 역방향 프록시 목록에서 **메신저 규칙** 확인 (`haist.knknara.co.kr/msg/...`)
2. 메신저 규칙이 **path-based** (`/msg/`) 로 명시돼 있으면 → HAIST WORKS 의 `/` 와 자동 공존 ✅
3. 메신저 규칙이 **catch-all** (path 미지정 → 전체) 이면 → 다음 중 한 가지로 조정:
   - (a) HAIST WORKS 규칙을 **메신저보다 위 (우선순위 상위)** 로 올림
   - (b) 메신저 규칙을 path `/msg/` 명시로 변경
4. 변경 후 **DSM 자체가 nginx reload** 함 (수동 reload 불필요)

### ⑨ 외부 접속 검증

브라우저에서:

1. **`https://haist.knknara.co.kr/`** → **HAIST WORKS 로그인 화면** 표시되면 OK ✅
2. **`https://haist.knknara.co.kr/msg/`** → **메신저 정상 작동** 확인 (변화 없어야 함) ✅
3. 두 시스템 동시에 잘 도는지 5분 정도 사용해보기

### ⑩ 메신저 영향 재확인

NAS SSH 에서:
```bash
docker ps
# knk-messenger : Up X days  ← 영향 없어야 정상
# knk-haist     : Up X minutes ← 신규
```

```bash
# 메신저 헬스
curl -fsS https://haist.knknara.co.kr/msg/healthz
# {"ok": true, ...} 또는 동등한 응답
```

### ⑪ 백업 cron 등록

```bash
# 백업 스크립트 권한
chmod +x /opt/knk_haist/deploy/backup.sh

# crontab 편집
crontab -e
```

추가 (메신저 백업은 그대로 두고, 줄만 추가):
```
# HAIST WORKS — 매일 03:30 SQLite 백업 (메신저 03:00 과 30분 간격)
30 3 * * * /opt/knk_haist/deploy/backup.sh >> /volume1/docker/knk-haist/backups/cron.log 2>&1
```

저장 → 종료.

---

## 5. 완료 후 보고 (대표에게)

작업 완료 후 다음 5가지 확인 후 보고 부탁드립니다:

- [ ] `docker ps` 에서 `knk-haist` STATUS 가 `Up X minutes (healthy)`
- [ ] `https://haist.knknara.co.kr/` 브라우저 접속 → 로그인 화면 OK
- [ ] `https://haist.knknara.co.kr/msg/` → 메신저 정상 (영향 0)
- [ ] DSM 역방향 프록시 목록에 HAIST WORKS 규칙 추가됨
- [ ] cron 에 HAIST WORKS 백업 줄 추가됨

---

## 6. 장애 대응 / 롤백

### HAIST WORKS 가 502/503/응답없음

```bash
# 1) 컨테이너 상태
docker ps -a | grep knk-haist

# 2) 로그 확인 (장애 원인 파악)
docker logs --tail 100 knk-haist

# 3) 재시작
docker restart knk-haist

# 4) 다시 안 되면 — 메신저는 그대로 두고 HAIST WORKS 만 중단
docker stop knk-haist
# (DSM 역방향 프록시의 HAIST WORKS 규칙도 비활성화 가능)
```

### 메신저까지 영향 받았을 경우 (긴급)

이는 **거의 발생하지 않아야** 합니다 (분리 설계). 만약 발생 시:

```bash
# 1) HAIST WORKS 컨테이너 즉시 중단
docker stop knk-haist

# 2) DSM 역방향 프록시에서 HAIST WORKS 규칙 비활성화 또는 삭제
#    (DSM UI 에서 토글)

# 3) 메신저 컨테이너 상태 확인
docker ps | grep knk-messenger
# 살아있어야 정상. 죽었으면 → supervisorctl restart knk-messenger (메신저 컨테이너 내부)

# 4) 메신저 외부 접속 확인
curl -fsS https://haist.knknara.co.kr/msg/healthz
```

→ 보통 5분 이내 완전 롤백 가능.

---

## 7. 환경변수 (.env) 참고

운영 모드 핵심 키:

```env
KNK_MODE=prod              # 운영 모드 (필수)
KNK_HOST=0.0.0.0           # 컨테이너 내부 바인딩
KNK_PORT=8081              # 내부 포트
KNK_WORKERS=2              # uvicorn worker 수
KNK_SECRET_KEY=<64자 hex>  # 보안 키 (절대 외부 노출 X)

# 선택 (현재 비워둠 — 추후 추가)
KNK_AI_PROVIDER=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
HIWORKS_MESSENGER_TOKEN=
```

전체 옵션은 `deploy/.env.example` 참조.

---

## 8. 보안 규칙 (꼭 지킬 것)

1. ❌ **비밀번호·SECRET_KEY·API 키를 카톡·메일·git·메모 평문에 저장 금지**
2. ❌ **`.env` 파일을 git 에 commit 금지** (`.gitignore` 에 이미 포함됨)
3. ❌ **컨테이너 외부에 SECRET_KEY 출력·logging 금지**
4. ✅ **SECRET_KEY 는 작업 후 메모장 즉시 닫기**
5. ✅ **권한**: `.env` 는 `chmod 600`, root 만 읽기
6. ✅ **백업 파일**도 NAS 외부 (메일·USB 등) 유출 금지 — DB 안에 고객·자재 정보 있음
7. ✅ **DSM admin / SSH root 비밀번호**가 메신저와 같다면 그대로 사용 OK (별도 발급 불필요)

---

## 9. 자산 위치 요약

| 위치 | 내용 |
|---|---|
| **GitHub Repo** | `https://github.com/top00151-commits/knk-haist-works` (private) |
| **NAS 코드** | `/opt/knk_haist/` |
| **NAS 데이터** | `/volume1/docker/knk-haist/data/` (SQLite DB) |
| **NAS 업로드** | `/volume1/docker/knk-haist/uploads/` (사용자 첨부) |
| **NAS 백업** | `/volume1/docker/knk-haist/backups/` |
| **NAS .env** | `/volume1/docker/knk-haist/.env` (chmod 600) |
| **Docker 이미지** | `knk-haist:latest` |
| **컨테이너 이름** | `knk-haist` |
| **내부 포트** | 8081 |
| **외부 URL** | `https://haist.knknara.co.kr/` |
| **상세 가이드** | `repo 안 deploy/HAIST_WORKS_NAS_설치가이드.md` |

---

## 10. 문의·보고

| 항목 | 연락처 |
|---|---|
| 작업 중 막힘 / 명령 에러 | 김정락 대표 → 빅터(개발) 에게 전달 |
| 메신저 영향 의심 / 긴급 롤백 | 김정락 대표 직접 |
| 외부 URL 접속 검증 | 대표 직접 확인 |
| 완료 보고 | 대표 (위 §5 5가지 체크리스트) |

---

## 11. 빌드 결과 회신 양식 (담당자 → 대표)

작업 완료 후 다음 양식으로 회신 부탁드립니다:

```
1. docker ps knk-haist 상태:   [ Up X minutes (healthy) / 기타 ]
2. https://haist.knknara.co.kr/ 접속 결과:   [ 로그인 화면 OK / 에러: ___ ]
3. https://haist.knknara.co.kr/msg/ 메신저 영향:   [ 정상 / 변화 있음: ___ ]
4. DSM 역방향 프록시 규칙 추가:   [ 완료 / 보류 (사유): ___ ]
5. 백업 cron 등록:   [ 완료 / 보류 ]
6. 발견된 이슈 / 추가 결정 필요사항: ___
7. SECRET_KEY 보관 방식: [ NAS .env 만 / 추가 백업 위치(어디): ___ ]
```

---

*작성: 빅터(Claude) / 2026-05-28*
*문의 응답: 김정락 대표 통해 빅터에게 전달*
*상세 가이드 참고: `01_HAIST_WORKS/deploy/HAIST_WORKS_NAS_설치가이드.md`*
