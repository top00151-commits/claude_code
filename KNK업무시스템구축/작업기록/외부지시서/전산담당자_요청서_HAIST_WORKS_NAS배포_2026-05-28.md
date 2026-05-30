# 📋 전산담당자 작업 요청서 — HAIST WORKS NAS 배포

> **요청자**: 김정락 대표이사
> **요청일**: 2026-05-28
> **수신**: KNK 전산담당자
> **건명**: 사내 NAS(메신저 운영 호스트)에 **HAIST WORKS** 웹 시스템 추가 배포
> **긴급도**: 보통 (1주 이내 작업 권장)
> **영향**: 기존 KNK 메신저 운영에 **영향 없음** (추가 배포만, 메신저 환경 비건드림)

---

## 1. 무엇을 / 왜

### 무엇
**HAIST WORKS** — KNK 사내 업무 통합 플랫폼 (자체 개발) 을 메신저와 **같은 NAS · 같은 도메인**에 추가 배포.

### 왜
- 매출·영업·자재구매·일순서·티켓·게시판 등 **75명 전사 업무**를 시스템화
- 메신저 인프라(HTTPS·도메인·백업·SSH) **재사용** → 추가 비용·관리 포인트 최소
- 데이터는 **사내에만** 보관 (외부 클라우드 미사용 일관성 유지)

### 배포 후 직원 접속 주소
| 시스템 | 주소 |
|---|---|
| **HAIST WORKS** (신규) | `https://haist.knknara.co.kr/` |
| 메신저 (현재) | `https://haist.knknara.co.kr/msg/` |

---

## 2. 기술 사양 (참고)

| 항목 | 값 |
|---|---|
| 기술 스택 | Python 3.10+ / **FastAPI** + Uvicorn (ASGI) / SQLite |
| 내부 포트 | **8081** (변경 가능 — 사용 중이면 알려주세요) |
| 워커 | uvicorn 2 workers (메모리 ~400MB) |
| 디스크 사용 | 초기 ~300MB, 운영 1년 후 ~5GB 추정 (업로드 포함) |
| 동접 부하 | 75명 동접 (메신저 부하 테스트 140명 통과 — 유사 부하) |
| HTTPS | **메신저용 Let's Encrypt 인증서 그대로 재사용** (재발급 불필요) |
| 외부 의존 | 없음 (옵션: Anthropic/OpenAI API — 대표 결정 후) |
| 백업 | DB·업로드 일일 백업 (메신저와 동일 패턴) |

> ⚠️ 메신저(Flask + gunicorn eventlet)와 다른 워커 모델(FastAPI + uvicorn)이지만 충돌은 없습니다.
> 권장: **별도 Docker 컨테이너** 또는 **별도 supervisor program** 으로 격리.

---

## 3. 전산담당자께 요청드릴 사항

### 🅰 사전 확인 (회신 부탁드림)

다음 항목을 확인하시고 가능 여부 회신 부탁드립니다:

| # | 항목 | 확인 내용 | 회신 |
|---|---|---|---|
| 1 | **NAS 여유 디스크** | 최소 10GB 여유 (1년 운영용) | □ OK / □ 부족 |
| 2 | **내부 포트 8081** | 메신저(5050) 외 8081 사용 가능 여부 | □ 가능 / □ 다른 포트 권장: ___ |
| 3 | **컨테이너 방식** | (a) 별도 Docker 컨테이너 신설 / (b) 메신저 컨테이너에 program 추가 / (c) NAS 호스트 native 설치 | □ a (추천) / □ b / □ c |
| 4 | **설치 경로** | `/opt/knk_works/` 신설 권장 (메신저는 `/opt/knk_messenger/`) | □ 같은 패턴 OK / □ 다른 경로 권장: ___ |
| 5 | **GitHub 접근** | 신규 private repo `knk-works` 생성 → NAS에 deploy key 등록 가능? | □ 가능 / □ 다른 방식: ___ |
| 6 | **메신저 운영 중단 없이 가능?** | 모든 작업이 메신저 다운타임 없이 가능한지 | □ 가능 / □ 점검 시간 필요 |

### 🅱 실제 작업 (확인 후 진행)

확인 회신 받으면 **상세 설치 가이드** (단계별 명령어)를 별도 전달 드립니다.
대표적인 작업 항목 미리보기:

1. **디렉터리·권한 생성**
   ```
   /opt/knk_works/                 (메인 설치)
   /opt/knk_works/data/            (SQLite DB)
   /opt/knk_works/uploads/         (사용자 업로드)
   /opt/knk_works/backups/         (자동 백업)
   /opt/knk_works/logs/            (gunicorn·uvicorn 로그)
   ```

2. **Python 환경**
   - venv 생성 (메신저와 분리)
   - `pip install -r requirements.txt` (FastAPI·uvicorn 등)

3. **Supervisor에 program 추가**
   ```
   [program:knk-works]
   command=/opt/knk_works/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8081 --workers 2
   directory=/opt/knk_works/01_HAIST_WORKS
   user=root  (또는 메신저와 동일 계정)
   autostart=true
   autorestart=true
   stdout_logfile=/opt/knk_works/logs/uvicorn.log
   stderr_logfile=/opt/knk_works/logs/uvicorn.err.log
   environment=KNK_MODE="prod",KNK_PORT="8081",KNK_HOST="127.0.0.1",KNK_SECRET_KEY="(별도 전달)"
   ```

4. **Nginx 설정 (가장 중요)** — 메신저 `/msg/` 와 공존
   ```
   server {
     server_name haist.knknara.co.kr;
     listen 443 ssl;
     # ... 기존 SSL 설정 그대로 ...

     # 기존: 메신저 (그대로 유지)
     location /msg/ {
       proxy_pass http://127.0.0.1:5050/;
       # ... 기존 설정 그대로 ...
     }

     # 신규: HAIST WORKS (루트)
     location / {
       proxy_pass http://127.0.0.1:8081;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto https;
       proxy_read_timeout 300;
       client_max_body_size 50M;   # 자재 사진·견적 PDF 업로드용
     }
   }
   ```

5. **방화벽**
   - **외부 8081 직접 노출 차단** (nginx 프록시 경유만)
   - 메신저 정책 그대로 적용

6. **백업 cron 추가** (메신저와 동일 패턴)
   ```
   0 3 * * *  /opt/knk_works/scripts/backup.sh
   ```

7. **헬스 체크 URL**
   - 내부: `http://127.0.0.1:8081/admin/health`
   - 외부: `https://haist.knknara.co.kr/admin/health`

### 🅲 가동 후 검증

설치 완료 후 함께 확인:
- [ ] `supervisorctl status knk-works` → `RUNNING`
- [ ] `https://haist.knknara.co.kr/` 접속 → 로그인 화면 표시
- [ ] `https://haist.knknara.co.kr/msg/` 접속 → 메신저 정상 (영향 없음)
- [ ] 메신저 헬스 체크 `https://haist.knknara.co.kr/msg/healthz` 200 응답
- [ ] HAIST WORKS 헬스 체크 200 응답
- [ ] 24시간 후 백업 파일 자동 생성 확인

---

## 4. 보안·운영 정책

| 항목 | 정책 |
|---|---|
| `KNK_SECRET_KEY` 등 비밀값 | 환경변수만 사용 · 파일·git 저장 금지 (메신저와 동일) |
| 외부 API 키 | `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` 환경변수 (현재는 미설정 — 결제 후 추가) |
| SSH 키 | 메신저와 같은 키 사용 가능 (편의) 또는 신규 발급 |
| 백업 보관 | NAS 안 7일치 + 주간 1회 외부 백업 (정책 결정 필요) |
| 로그 보관 | 14일 자동 rotate |
| 사용자 비밀번호 | bcrypt 해싱 (시스템 기본 적용) |

---

## 5. 영향·위험·롤백

### 영향
- **메신저**: 영향 0 (별도 컨테이너/프로세스/포트, nginx의 `/msg/` 위치는 건드리지 않음)
- **NAS**: 메모리 +400MB, 디스크 +수GB 사용
- **네트워크**: 외부 노출은 nginx 한 점만 (현재와 동일)

### 위험
| 위험 | 발생 가능성 | 대응 |
|---|---|---|
| nginx 설정 오타로 메신저까지 다운 | 낮음 | 작업 전 nginx 설정 백업 → `nginx -t` 검증 후 `reload` |
| 새 supervisor program 충돌 | 낮음 | 메신저는 `knk-messenger`, 신규는 `knk-works` 명확 분리 |
| 디스크 풀 (업로드 폭증) | 낮음 | client_max_body_size 50M 제한 + 모니터링 |

### 롤백 (문제 발생 시)
1. `supervisorctl stop knk-works`
2. nginx 설정에서 신규 `location /` 블록 제거 후 `nginx -s reload`
3. (선택) `/opt/knk_works/` 디렉터리 제거

→ 메신저는 그대로 정상 운영, 위 작업은 5분 이내.

---

## 6. 일정 제안

| 단계 | 일자 | 담당 |
|---|---|---|
| ① **사전 확인 회신** (요청서 1~6번 답변) | 1~2일 내 | 전산담당자 |
| ② 상세 설치 가이드 작성·전달 | 회신 후 1일 | 빅터(개발) |
| ③ **NAS 설치 작업** (1회, ~30분) | 일정 협의 | 전산담당자 + 빅터 원격 지원 |
| ④ 검증 + 대표 단독 사용 (안정 확인) | 1주 | 대표 |
| ⑤ 운영 모드 전환 + 직원 합류 | 안정 확인 후 | 대표 + 빅터 |

---

## 7. 자주 묻는 질문 (FAQ)

**Q. 메신저랑 같이 죽을 위험은?**
A. 분리된 supervisor program이라 독립적입니다. HAIST WORKS가 죽어도 메신저는 살아있고, 반대도 마찬가지입니다. nginx만 살아있으면 둘 중 하나는 응답합니다.

**Q. HTTPS 인증서를 따로 받아야 하나요?**
A. 아니요. `haist.knknara.co.kr` 인증서가 메신저용으로 이미 발급돼 있고, 같은 도메인의 다른 path니까 그대로 사용 가능합니다.

**Q. 메신저 컨테이너 안 건드린다고 했는데, nginx 설정은 어디 있나요?**
A. 메신저 컨테이너 안 nginx 설정에 신규 `location /` 추가 OR NAS 호스트 nginx에 reverse proxy 추가 — 어느 구조인지에 따라 다릅니다. 컨테이너 안이면 컨테이너 nginx 설정만 수정, 호스트면 호스트 nginx 수정. 확인 후 가이드 드리겠습니다.

**Q. 우리가 만든 다른 서비스(예: 회사 홈페이지)는 어떻게 되나요?**
A. 현재 `haist.knknara.co.kr/`(루트)는 비어있거나 메신저로 리다이렉트 중일 텐데, 이 자리에 HAIST WORKS가 들어옵니다. 회사 공개 홈페이지는 별도 도메인(`knknara.co.kr` 등) 사용 권장.

**Q. 외부(베트남법인) 접속은?**
A. 인터넷이 닿는 모든 곳에서 `https://haist.knknara.co.kr/` 로 접속 가능. 메신저와 동일.

---

## 8. 문의·답변 경로

- **이 요청서 관련 질문**: 김정락 대표
- **기술 세부 사항**: 빅터(개발자) — 대표 통해 전달
- **회신 방법**: 1~6번 표 채워서 메일 또는 인쇄본 회신

---

## 9. 첨부 / 참고 자료

- 메신저 운영 현황: `10_KNK_Messenger/서버현황.md`
- 메신저 배포 가이드: `10_KNK_Messenger/CLAUDE.md`, `10_KNK_Messenger/INTERNET_DEPLOY_CHECKLIST.md`
- HAIST WORKS 코드 위치: 현재 대표 PC `C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\01_HAIST_WORKS\`
- HAIST WORKS 운영 모드 BAT: `KNK_운영시작.bat` (참고용)

---

*이 요청서는 대표(김정락)가 검토·확정 후 전산담당자에게 전달합니다. 빅터(개발)는 회신 후 상세 가이드 작성으로 대기.*
