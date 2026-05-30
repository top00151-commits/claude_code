# HAIST WORKS — NAS 배포 재현 가이드 + 비상 복구

> **이 문서 하나로 다른 PC·다른 시점에서 NAS 에 다시 연결 가능.**
> **비밀번호·SECRET_KEY·SSH private key 본문은 절대 여기 적지 않음 — "어디 있는지" 만 기록.**
> 비밀번호는 같은 폴더의 `비상복구_열쇠보관표.md` 인쇄본(회사 금고) 참조.

> **출처**: `작업기록_2026-05-29_NAS배포_완료.md` §16~§20 추출
> **기준 시점**: 2026-05-29 NAS 배포 완료 (works.knknara.co.kr HTTP 동작)

---

## 16. 자산 인벤토리 (재연결·재현용 — 보안값 제외 모든 위치)

> **이 섹션만 있으면 다른 PC·다른 시점에서 NAS 에 다시 연결 가능.**
> **비밀번호·SECRET_KEY·SSH private key 본문은 절대 여기 적지 않음 — "어디 있는지" 만 기록.**

### 16.1 도메인 / 외부 진입점

| 항목 | 값 | 비고 |
|---|---|---|
| 메인 도메인 | `knknara.co.kr` | KNK 회사 도메인 |
| 메신저 | `https://haist.knknara.co.kr/msg/` | Flask, 기존 운영 중 |
| HAIST WORKS | `https://works.knknara.co.kr/` | FastAPI, 신규 (오늘 배포) |
| NAS DDNS | `knknara.myDS.me` | Synology 제공, 백업 진입점 |
| QuickConnect ID | `knknara.direct.quickconnect.to` | DSM 접속용 |

### 16.2 NAS 정보 (Synology)

| 항목 | 값 |
|---|---|
| NAS 서버명 | `KNKNAS1` |
| 내부 IP | `192.168.123.5` (Bond 2 정적 IP) |
| 보조 IP | `192.168.123.10` (Bond 1 정적 IP, 현재 연결 해제) |
| 게이트웨이 | `192.168.123.254` |
| DNS | `168.126.63.1` |
| 작업 그룹 | `KNK` |
| 볼륨 1 (KNKNAS1) | 34.9 TB (사용 4.5 TB, 13%) |
| 볼륨 2 (BACKUP) | 34.9 TB (사용 14.5 TB, 41%) |
| 라우터 외부 매핑 | 80, 443 → DSM nginx |
| DSM 관리 포트 | 5000 (HTTP) / 5001 (HTTPS) — **사무실 LAN 에서만** |

### 16.3 컨테이너 (Docker 4개 실행 중)

| 컨테이너 | 이미지 | 용도 | 빅터 작업 |
|---|---|---|---|
| **KNKHAIST** | `ubuntu:20.04` | 메신저 + HAIST WORKS | ✅ 작업 대상 |
| KNKGIT | `gitea/gitea:latest` | 사내 git 서버 | (활용 검토) |
| KNKDEV | `knkdev:2024410` | 개발 환경 | — |
| Portainer | `portainer/portainer-ce` | 컨테이너 GUI 관리 | — |

#### KNKHAIST 컨테이너 상세

| 항목 | 값 |
|---|---|
| OS | Ubuntu 20.04.6 LTS (Focal Fossa) |
| 아키텍처 | amd64 |
| 시스템 Python | 3.8 (메신저 사용) |
| 추가 Python | 3.11.9 (pyenv, HAIST WORKS 전용) |
| nginx | 1.18.0 (Ubuntu) |
| supervisor | 동작 중 (`/etc/supervisor/conf.d/`) |
| Hostname | `KNKHAIST` |
| 실행 명령 | `/bin/bash` (장시간 동작) |
| 가동 일수 | 9일+ (2026-05-19 ~) |
| RAM 사용 | 270 MB |
| CPU 사용 | 0.16% |

#### 볼륨 매핑 (NAS host ↔ 컨테이너 안)

| NAS host 경로 | 컨테이너 안 경로 | 권한 | 용도 |
|---|---|---|---|
| `docker/Haist/` | `/home` | rw | 일반 home |
| `docker/Haist/opt` | `/opt` | rw | **코드·DB·venv·pyenv** (영구) |
| `docker/Haist/root` | `/root` | rw | **SSH 키·bashrc·pyenv** (영구) |
| `homes/top0015` | `/haist` | rw | 사용자 home (top0015) |

→ 컨테이너 삭제·재생성해도 `/opt` 와 `/root` 안의 내용은 NAS 디스크에 살아있음. **재현 시 이 디렉터리를 그대로 마운트하면 즉시 복원**.

### 16.4 SSH 접근 정보

| 대상 | 명령 | 비밀번호 위치 | 빅터 사용 가능 |
|---|---|---|---|
| **KNKHAIST 컨테이너** | `ssh -p 31201 root@o.knknara.co.kr` | 대표님 보관 | ✅ 컨테이너 안만 |
| NAS host (DSM 22) | `ssh root@o.knknara.co.kr` (포트 22) | 미확인·차단 | ❌ |
| NAS host (admin) | `ssh admin@192.168.123.5` | 미확인·차단 | ❌ |
| 사용자 ssh (top0015) | `ssh top0015@192.168.123.5` | SSH 권한 부여 안 됨 | ❌ |

→ **현재 빅터는 KNKHAIST 컨테이너 안에서만 작업 가능**. NAS host (DSM, Reverse Proxy, 인증서, 라우팅) 변경은 전산담당자(최보현 상무) 요청 필수.

### 16.5 GitHub 저장소

| 항목 | 값 |
|---|---|
| HAIST WORKS repo | `git@github.com:top00151-commits/knk-haist-works.git` |
| 가시성 | Private |
| 브랜치 | `main` |
| 인증 방식 | SSH key (ed25519) |
| KNKHAIST 안 키 경로 | `~/.ssh/github_deploy` (private), `~/.ssh/github_deploy.pub` (public) |
| 키 권한 | private 600, public 644 |
| SSH config | `~/.ssh/config` (Host github.com → IdentityFile ~/.ssh/github_deploy) |
| GitHub 등록 | top00151-commits 계정의 Deploy Keys 또는 SSH Keys |

#### SSH config (`~/.ssh/config`) 정확한 내용
```
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_deploy
    StrictHostKeyChecking no
```

### 16.6 HAIST WORKS 디렉터리 구조 (`/opt/knk_haist/`)

```
/opt/knk_haist/
├── .venv/                          ← Python 3.11.9 가상환경
│   ├── bin/
│   │   ├── python (→ ~/.pyenv/versions/3.11.9/bin/python)
│   │   ├── uvicorn
│   │   ├── pip
│   │   └── run_knk_works.sh        ← supervisor 가 호출하는 wrapper
│   └── lib/python3.11/site-packages/
├── .env                            ← KNK_SECRET_KEY 등 (chmod 600, .gitignore)
├── app/                            ← 애플리케이션 코드
│   ├── main.py                     ← FastAPI 진입점
│   ├── database.py                 ← SQLite 스키마·CRUD
│   ├── ...
│   └── templates/                  ← Jinja2 템플릿
├── deploy/                         ← 배포 스크립트
│   ├── .env.example
│   ├── install_in_messenger_container.sh
│   ├── nginx_works_location.conf  (→ 폐기 예정)
│   └── supervisor_knk_works.conf
├── data/                           ← SQLite DB 파일 (영구)
├── uploads/                        ← 업로드 파일 (영구)
├── backups/                        ← DB 백업 (영구)
├── logs/                           ← uvicorn 로그
│   ├── uvicorn.log
│   └── uvicorn-error.log
├── requirements.txt
└── .git/                           ← GitHub 동기화용
```

### 16.7 .env 파일 형식 (`/opt/knk_haist/.env`)

> 실제 값 X. 형식만 기록. **chmod 600, root:root, .gitignore 등록됨**.

```
KNK_MODE=prod
KNK_HOST=127.0.0.1
KNK_PORT=8081
KNK_WORKERS=1                # ← SQLite 락 방지 (절대 2 이상 금지)
KNK_SECRET_KEY=<64자 hex>    # ← secrets.token_hex(32) 로 자동 생성됨
KNK_AI_PROVIDER=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
HIWORKS_MESSENGER_TOKEN=
HIWORKS_HR_TOKEN=
HIWORKS_APPROVAL_TOKEN=
KNK_DEBUG=0
KNK_BACKUP_S3=
```

**SECRET_KEY 잃어버린 경우 영향**: 기존 세션 쿠키 무효화 (사용자 전원 재로그인 필요). 데이터 손실 X.

### 16.8 supervisor 설정

#### 메신저 (`/etc/supervisor/conf.d/knk-messenger.conf` — 빅터가 손대지 않음)
- 프로그램명: `knk-messenger`
- 실행: gunicorn → `0.0.0.0:5050`
- Python: 시스템 3.8

#### HAIST WORKS (`/etc/supervisor/conf.d/knk-works.conf` — 빅터 생성)
- 프로그램명: `knk-works`
- 실행: `/opt/knk_haist/.venv/bin/run_knk_works.sh` (wrapper)
- Wrapper 내용: `.env` 로드 → uvicorn 실행 (`127.0.0.1:8081`, workers=1)
- 로그: `/opt/knk_haist/logs/uvicorn.log`, `uvicorn-error.log`
- autostart, autorestart 활성화

### 16.9 nginx 설정 (현재 — 정리 대상)

| 경로 | 용도 | 정리 후 상태 |
|---|---|---|
| `/etc/nginx/sites-enabled/knk-messenger` | 메신저 nginx + `/works/` location (빅터가 추가) | `/works/` 블록 제거 예정 |
| `/etc/nginx/sites-enabled/default` | 기본 페이지 | 그대로 |
| `/root/nginx-backups/` | 빅터가 만든 백업 디렉터리 | 비상 복구용 보관 |

**중요**: 컨테이너 안 nginx 는 외부 traffic 안 받음 (DSM 이 gunicorn/uvicorn 으로 직행). nginx 8080 listen 은 사실상 사용 X. 정리 후 메신저 conf 는 원본 상태로 복귀.

### 16.10 포트 사용 현황

| 포트 | 서비스 | 외부 노출 | 비고 |
|---|---|---|---|
| 5050 | 메신저 gunicorn | ✅ (DSM → haist.knknara.co.kr) | Flask 직접 |
| 8081 | HAIST WORKS uvicorn | ✅ (DSM → works.knknara.co.kr) | FastAPI 직접 |
| 8080 | 컨테이너 nginx | ❌ (사용 안 함) | 추후 정리 |
| 31201 | SSH (컨테이너) | ✅ | 빅터 작업용 |
| 5051 | (미사용) | ❌ | 옵션 B 대비 예약 |

### 16.11 DSM Reverse Proxy 항목 (4개)

| 설명 | 소스 | 대상 | 등록자 |
|---|---|---|---|
| `HAIST.HTTP` | `http://haist.knknara.co.kr:80` | `http://localhost:5050` | 기존 |
| `HAIST.HTTPS` | `https://haist.knknara.co.kr:443` | `http://localhost:5050` | 기존 |
| `HAIST_WORKS.HTTP` | `http://works.knknara.co.kr:80` | `http://localhost:8081` | 2026-05-29 상무님 |
| `HAIST_WORKS.HTTPS` | `https://works.knknara.co.kr:443` | `http://localhost:8081` | 대기 (인증서는 발급됨) |

### 16.12 SSL 인증서 (DSM → 제어판 → 보안 → 인증서)

| 도메인 | 인증서 이름 | 발급 | 만기 |
|---|---|---|---|
| `haist.knknara.co.kr` | (RSA/ECC) HAIST 인증서 | Let's Encrypt | 2026-08-12 |
| `works.knknara.co.kr` | (RSA/ECC) HAIST.Works 인증서 | Let's Encrypt | 2026-08-27 |
| `msg.knknara.co.kr` | (RSA/ECC) HAIST.Messenger 인증서 | Let's Encrypt | 2026-08-27 |

**자동 갱신**: Let's Encrypt는 90일마다 만료. DSM 자동 갱신 설정 확인 필요.

### 16.13 DNS 등록 (어디서 관리되는지 확인 필요)

| 도메인 | 등록 위치 | 비고 |
|---|---|---|
| `knknara.co.kr` | (전산담당자 보관) | 회사 도메인 등록기관 |
| `haist.knknara.co.kr` | A 또는 CNAME | 기존 |
| `msg.knknara.co.kr` | A 또는 CNAME | 기존 |
| `works.knknara.co.kr` | A 또는 CNAME | 2026-05-29 신규 (상무님) |
| `o.knknara.co.kr` | A | NAS 외부 진입점 |

---

## 17. 처음부터 재현 가이드 (Zero → 동작)

> **시나리오**: 컨테이너가 통째로 날아갔거나, 새 NAS 에 이관할 때.

### Step 1: NAS / 컨테이너 준비 (전산담당자)

```
1. Synology DSM → Docker → 새 컨테이너 (ubuntu:20.04)
   - 이름: KNKHAIST 또는 임의
   - 볼륨 매핑:
     · docker/Haist/opt → /opt
     · docker/Haist/root → /root
   - 환경변수: TZ=Asia/Seoul
   - 명령: /bin/bash -c "tail -f /dev/null" 또는 supervisord
   - SSH 포트 매핑: 31201 → 22

2. 컨테이너 안에서 SSH 설치
   apt-get update
   apt-get install -y openssh-server supervisor nginx git curl
   service ssh start

3. root 비밀번호 설정 (passwd) — 대표님 별도 보관

4. SSH 키 생성 + GitHub 등록
   ssh-keygen -t ed25519 -f ~/.ssh/github_deploy -N ""
   cat ~/.ssh/github_deploy.pub  # 이걸 GitHub Deploy Keys 에 등록
   chmod 600 ~/.ssh/github_deploy
   cat > ~/.ssh/config << 'EOF'
   Host github.com
       HostName github.com
       User git
       IdentityFile ~/.ssh/github_deploy
       StrictHostKeyChecking no
   EOF
   chmod 600 ~/.ssh/config
   ssh -T git@github.com  # "Hi top00151-commits!" 떠야 OK
```

### Step 2: HAIST WORKS 코드 받기

```bash
cd /opt
git clone git@github.com:top00151-commits/knk-haist-works.git knk_haist
cd knk_haist
ls deploy/  # install_in_messenger_container.sh 보이면 OK
```

### Step 3: Python 3.11 설치 (pyenv 빌드 — 10~15분)

```bash
# 빌드 의존성
apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev wget curl llvm libncursesw5-dev \
    xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

# pyenv 설치
curl -fsSL https://pyenv.run | bash

# 환경변수 (~/.bashrc 에 영구화)
cat >> ~/.bashrc << 'EOF'
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
EOF

# 현재 셸에 적용
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# Python 3.11.9 빌드
pyenv install 3.11.9
$PYENV_ROOT/versions/3.11.9/bin/python --version  # Python 3.11.9
```

### Step 4: 설치 스크립트 실행

```bash
cd /opt/knk_haist
bash deploy/install_in_messenger_container.sh
```

→ 자동 진행:
- venv 생성 (`.venv/`, Python 3.11.9 기반)
- requirements.txt 설치
- 데이터 디렉터리 (`data/`, `uploads/`, `backups/`, `logs/`)
- `.env` 생성 + `KNK_SECRET_KEY` 자동 생성
- supervisor program `knk-works` 등록·시작
- 헬스체크

### Step 5: venv 만 따로 3.11 로 생성하는 경우 (수동)

설치 스크립트가 어떤 이유로 3.8 venv 만들면 강제:

```bash
supervisorctl stop knk-works
rm -rf /opt/knk_haist/.venv
$PYENV_ROOT/versions/3.11.9/bin/python -m venv /opt/knk_haist/.venv
cd /opt/knk_haist
source .venv/bin/activate
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
deactivate
bash deploy/install_in_messenger_container.sh   # wrapper 재생성
```

### Step 6: 검증

```bash
supervisorctl status knk-works               # RUNNING
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8081/login   # 200
ss -tlnp | grep -E '5050|8081'              # 둘 다 LISTEN
```

### Step 7: DSM Reverse Proxy 등록 (전산담당자)

DSM → 제어판 → 로그인 포털 → 고급 → 역방향 프록시 → 생성

```
설명: HAIST_WORKS.HTTPS
소스: HTTPS, works.knknara.co.kr, 443, HSTS 활성화
대상: HTTP, localhost, 8081
```

HTTP(80) 항목도 같이 추가 (선택).

DNS 등록 + SSL 인증서 발급은 전산담당자 영역.

### Step 8: 외부 검증

```
브라우저: https://works.knknara.co.kr/login
→ 자물쇠 + 로그인 화면이면 완료
```

---

## 18. 비상 복구 시나리오

### 18.1 컨테이너 안 코드 손상

```bash
cd /opt
rm -rf knk_haist
git clone git@github.com:top00151-commits/knk-haist-works.git knk_haist
cd knk_haist
bash deploy/install_in_messenger_container.sh
```

`.env` (SECRET_KEY) 도 새로 생성됨 → 사용자 전원 재로그인. DB·업로드는 다른 디렉터리(`data/`, `uploads/`)라 영향 X.

### 18.2 컨테이너 자체 삭제 → 재생성

볼륨 매핑(`docker/Haist/opt` → `/opt`) 이 살아있으면:
1. 새 ubuntu:20.04 컨테이너 + 같은 볼륨 매핑
2. 컨테이너 안에서:
   ```bash
   apt-get update && apt-get install -y supervisor nginx git curl
   # /etc/supervisor/conf.d/knk-works.conf 가 /opt 에 없으면 재배포
   cd /opt/knk_haist && bash deploy/install_in_messenger_container.sh
   ```
3. `.venv` 와 `.env` 와 데이터 모두 보존됨 → 즉시 동작

### 18.3 NAS 자체 교체

1. 새 NAS 에 같은 docker 볼륨 복원 (Hyper Backup 또는 수동 복사)
2. DSM Reverse Proxy 4개 항목 재등록 (§16.11 참조)
3. DNS A 레코드 변경 (구 NAS IP → 신 NAS IP)
4. SSL 인증서 재발급 (Let's Encrypt 자동)
5. 컨테이너 재생성 + 위 18.2 절차

### 18.4 GitHub 저장소 분실

`/opt/knk_haist/` 전체가 사실상 백업본. NAS 의 그 디렉터리에서 새 GitHub 저장소로 push 하면 복구.

```bash
cd /opt/knk_haist
git remote set-url origin git@github.com:<new-org>/<new-repo>.git
git push -u origin main
```

### 18.5 SECRET_KEY 분실

`.env` 만 손상되고 `data/` DB 살아있으면:
```bash
GENKEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
sed -i "s|KNK_SECRET_KEY=.*|KNK_SECRET_KEY=$GENKEY|" /opt/knk_haist/.env
chmod 600 /opt/knk_haist/.env
supervisorctl restart knk-works
```

사용자 전원 재로그인 필요. 데이터 손실 X.

---

## 19. 비밀값·계정 위치 (값은 적지 않음 — 보안)

| 항목 | 어디 있나 | 누가 알 수 있나 |
|---|---|---|
| KNKHAIST 컨테이너 SSH 비밀번호 | 대표님 1Password / 보안 메모 | 대표님 |
| `~/.ssh/github_deploy` (private) | 컨테이너 `/root/.ssh/` (영구 볼륨) | 컨테이너 root |
| `~/.ssh/github_deploy.pub` | GitHub repo Deploy Keys 등록됨 | 공개 |
| GitHub PAT (사용 안 함) | — | — |
| `/opt/knk_haist/.env` 의 `KNK_SECRET_KEY` | NAS `docker/Haist/opt/knk_haist/.env` | 컨테이너 root |
| ANTHROPIC_API_KEY | `.env` (현재 비어있음) | (활성화 시 대표님) |
| OPENAI_API_KEY | `.env` (현재 비어있음) | (활성화 시 대표님) |
| HIWORKS 토큰 | `.env` (현재 비어있음) | (활성화 시 전산담당자) |
| NAS host root 비밀번호 | 전산담당자(최보현 상무) | 전산담당자 |
| DSM admin 비밀번호 | 전산담당자 | 전산담당자 |
| 라우터 관리 비밀번호 | 전산담당자 | 전산담당자 |

---

## 20. 다음 빅터(또는 다른 AI)에게 핸드오프 메모

> 이 문서를 처음 보는 AI / 새 세션 빅터에게:

1. **읽을 순서**: §0 → §12(최종 아키텍처) → §16(자산 인벤토리) → 필요 시 §17(재현 가이드)
2. **현재 상태 확인 명령** (컨테이너 SSH 들어가서):
   ```bash
   supervisorctl status knk-works                # RUNNING 이어야
   curl -sI http://127.0.0.1:8081/login           # 200
   ls /opt/knk_haist/.env                        # 존재해야
   $HOME/.pyenv/versions/3.11.9/bin/python --version  # 3.11.9
   git -C /opt/knk_haist remote -v               # github.com:top00151-commits/knk-haist-works.git
   ```
3. **금지 사항**:
   - `KNK_WORKERS` 를 2 이상으로 절대 변경 금지 (SQLite 락)
   - nginx 백업을 `sites-enabled/` 또는 `conf.d/` 안에 만들지 말 것
   - 컨테이너 안 nginx 의 `/works/` location 은 무용지물 — 손대지 말 것
   - DSM 설정 변경은 전산담당자(최보현 상무) 영역 — 빅터 직접 시도 금지
4. **자유 사항**:
   - `/opt/knk_haist/` 안의 모든 코드·설정 자유
   - GitHub push 자유 (단, `.env` 와 `data/` 절대 commit 금지 — `.gitignore` 확인)
   - supervisor `knk-works` 재시작·로그 확인 자유
5. **막혔을 때 연락 라인**:
   - 컨테이너 안 문제 → 빅터 직접 해결
   - 컨테이너 밖 (DSM·DNS·SSL·라우터) → 대표님 → 전산담당자(최보현 상무)

---

*작성: 빅터(Claude) · 2026-05-29*
