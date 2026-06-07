# 🚀 HAIST WORKS — 메신저 컨테이너 내부 설치 가이드

> **버전**: v5H226z108n20 (2026-05-28)
> **목표**: `https://haist.knknara.co.kr/works/` 에서 HAIST WORKS 접속 가능
> **방식**: 메신저와 **같은 컨테이너** 안에 추가 설치 (별도 Docker 컨테이너 X)
> **소요**: 약 10분
> **메신저 영향**: 0 (별도 supervisor program / nginx location / 디렉터리)

---

## 📋 설계 (왜 이렇게 하나)

| 항목 | 위치 |
|---|---|
| 컨테이너 | 메신저와 **동일** (1개만) |
| 코드 | `/opt/knk_haist/` (메신저는 `/opt/knk_messenger/`) |
| 데이터·업로드 | `/opt/knk_haist/{data,uploads,backups,logs}/` |
| Python venv | `/opt/knk_haist/.venv/` (메신저와 분리) |
| supervisor program | `knk-works` (메신저는 `knk-messenger`) |
| 내부 포트 | 8081 (uvicorn) — 메신저는 5050 |
| nginx 라우팅 | `location /works/` → 127.0.0.1:8081 |
| 외부 URL | `https://haist.knknara.co.kr/works/` |

**메신저 비건드림 보장:**
- 별도 supervisor program → 메신저 program 영향 0
- 별도 nginx location → 메신저 `/msg/` 영향 0
- 별도 디렉터리 → 파일 충돌 0
- nginx 설정 변경 시 자동 백업 + `nginx -t` 검증 + 실패 시 자동 롤백

---

## ⚡ 1-줄 설치 (전체 흐름)

### Step 1: NAS host SSH 접속

본인 PC PowerShell:
```powershell
ssh -p 31201 root@o.knknara.co.kr
```

### Step 2: 메신저 컨테이너 진입

```bash
# 메신저 컨테이너 이름 확인 (보통 knk-messenger 또는 knkhaist)
docker ps --format '{{.Names}}'

# 컨테이너 안으로 진입
docker exec -it <컨테이너이름> bash
```

### Step 3: 코드 받기 (컨테이너 안)

```bash
cd /opt
# 이미 받아두셨으면 pull 만:
[ -d knk_haist ] && cd knk_haist && git pull && cd .. || git clone https://github.com/top00151-commits/knk-haist-works.git knk_haist

cd /opt/knk_haist
ls -la deploy/
# install_in_messenger_container.sh 보이면 OK
```

> 컨테이너 안에 git 이 없으면: `apt-get update && apt-get install -y git`

### Step 4: ⭐ 설치 스크립트 1줄 실행

```bash
cd /opt/knk_haist && bash deploy/install_in_messenger_container.sh
```

→ 약 5~8분 (의존성 설치 시간 포함). 다음 작업 자동:
1. 환경 점검
2. Python venv + requirements 설치
3. 데이터 디렉터리 생성
4. .env + SECRET_KEY 자동 생성
5. supervisor program 등록
6. nginx `/works/` location 추가 (메신저 설정 백업 후)
7. nginx -t 검증 + reload
8. supervisorctl start knk-works
9. 헬스체크 (내부 8081 + 외부 /works/login + 메신저 /msg/ 영향)

### Step 5: 브라우저 검증

1. `https://haist.knknara.co.kr/works/` → **HAIST WORKS 로그인 화면** ✅
2. `https://haist.knknara.co.kr/msg/` → **메신저 정상** (변화 없음) ✅

---

## 🔍 핵심 기술 — `/works/` subpath 처리

### 문제
HAIST WORKS 템플릿에 `<a href="/login">` 같은 **절대경로 875+ 개**.
`/works/` subpath 로 배포하면 브라우저가 `/login` 으로 가서 404.

### 해결 — nginx `sub_filter` 자동 재작성
응답 HTML·JS·CSS 안의 절대경로를 nginx 가 자동으로 `/works/` prefix 추가.

```nginx
sub_filter 'href="/' 'href="/works/';
sub_filter 'src="/'  'src="/works/';
sub_filter 'action="/' 'action="/works/';
sub_filter 'fetch("/'  'fetch("/works/';
sub_filter 'url("/'    'url("/works/';
proxy_redirect / /works/;
proxy_redirect ~^/(.*)$ /works/$1;
```

→ HAIST WORKS 코드 **0 변경**. nginx 가 변환 처리. (`deploy/nginx_works_location.conf` 참조)

### 장점·단점
| 장점 | 단점 |
|---|---|
| 코드 수정 0 | gzip 비활성화 (소폭 성능 하락) |
| 즉시 배포 | 일부 JS 동적 URL (`${var}/api`) 못 잡을 수 있음 |
| 롤백 1초 | API JSON 응답 절대경로 안 변환 (드문 케이스) |

→ 운영하면서 깨지는 곳 발견 시 코드 수정 (`KNK_BASE_PATH` 환경변수 도입) 으로 점진 개선.

---

## 🔧 관리 명령 (컨테이너 안)

```bash
# 상태
supervisorctl status knk-works

# 재시작 (코드 갱신 후)
cd /opt/knk_haist && git pull && supervisorctl restart knk-works

# 로그
tail -f /opt/knk_haist/logs/uvicorn.log
tail -f /opt/knk_haist/logs/uvicorn-error.log

# 의존성 재설치 (requirements.txt 변경 후)
cd /opt/knk_haist
source .venv/bin/activate
pip install -r requirements.txt
deactivate
supervisorctl restart knk-works
```

### nginx 재로드 (설정 변경 후)
```bash
nginx -t && nginx -s reload
```

---

## 🚨 장애 대응 / 롤백

### HAIST WORKS 가 502/응답없음

```bash
# 1) 로그 확인
tail -50 /opt/knk_haist/logs/uvicorn-error.log

# 2) 재시작
supervisorctl restart knk-works

# 3) 그래도 안 되면 — HAIST WORKS 만 중단 (메신저는 그대로)
supervisorctl stop knk-works
```

### 메신저까지 영향 (긴급)

극히 드물어야 함 (분리 설계). 만약 발생:

```bash
# 1) HAIST WORKS 중단
supervisorctl stop knk-works

# 2) nginx 설정을 백업본으로 복원 (TIMESTAMP 는 설치 시각)
ls /etc/nginx/conf.d/*.bak.*
cp /etc/nginx/conf.d/knk-messenger.conf.bak.<TIMESTAMP> \
   /etc/nginx/conf.d/knk-messenger.conf
nginx -t && nginx -s reload

# 3) 메신저 확인
curl -fsS https://haist.knknara.co.kr/msg/healthz
```

→ 5분 이내 완전 롤백 가능.

### 완전 제거 (HAIST WORKS 만)

```bash
# 1) supervisor program 중단·제거
supervisorctl stop knk-works
rm /etc/supervisor/conf.d/knk-works.conf
supervisorctl reread && supervisorctl update

# 2) nginx 설정 복원
cp /etc/nginx/conf.d/*.bak.<TIMESTAMP> /etc/nginx/conf.d/<원본>
nginx -t && nginx -s reload

# 3) (선택) 코드·데이터 제거 — 진짜 완전 제거할 때만
rm -rf /opt/knk_haist
```

---

## ✅ 설치 후 보고할 5가지

설치 스크립트 끝에 자동 출력되는 내용으로 다음 보고:

- [ ] `supervisorctl status knk-works` → `RUNNING`
- [ ] `https://haist.knknara.co.kr/works/` → 로그인 화면
- [ ] `https://haist.knknara.co.kr/msg/` → 메신저 정상
- [ ] 내부 헬스체크 (http://127.0.0.1:8081/login) HTTP 200
- [ ] nginx 백업 파일 위치 (롤백용)

---

## 📞 문의

- 설치 중 막힘 → 빅터(개발) 에게 에러 메시지 전달
- 보안 (SECRET_KEY 등) 노출 의심 → 즉시 재발급 (스크립트 재실행 안 됨, 수동)

---

*작성: 빅터(Claude) · 2026-05-28*
