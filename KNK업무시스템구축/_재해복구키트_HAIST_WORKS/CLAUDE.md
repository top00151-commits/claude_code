# CLAUDE.md — HAIST WORKS (이 파일은 Claude Code가 자동으로 읽습니다)

> **새 클로드에게:** 이 폴더는 ㈜케이엔케이(KNK) **사내 통합 업무 시스템 HAIST WORKS** 의 비상복구 키트입니다.
> 이 문서 하나로 "이 프로젝트가 무엇이고, 어떻게 고치고, 어떻게 배포하고, 망가졌을 때 어떻게 되살리는지"를
> 즉시 파악할 수 있도록 만들었습니다. **먼저 이 문서를 끝까지 읽으세요.**
> 더 깊은 맥락은 `재현가이드_NAS배포.md` (자산 인벤토리 + 8단계 재현) 와 `프로젝트_히스토리.md` 에 있습니다.

---

## 0. 한눈에 (가장 중요한 것만)

| 항목 | 값 |
|---|---|
| 무엇 | 사내 업무 통합 시스템 (매출영업·자재구매·통합플랫폼·워크플로우·자재모듈·환율 등) |
| 기술 | Python **FastAPI** + **SQLite** + **Jinja2** + **uvicorn** (Python 3.11.9) |
| 공개 주소 | **https://works.knknara.co.kr/** |
| 운영 서버 | 사내 **Synology NAS** Docker 컨테이너 `KNKHAIST` (메신저와 같은 컨테이너) |
| 코드 백업 | GitHub `git@github.com:top00151-commits/knk-haist-works.git` (branch `main`, Private) |
| 최고관리자 | 사번 `5` / `top0015@knknara.co.kr` (대표님) |
| 핵심 파일 | `app/main.py` (라우트) · `app/database.py` (스키마·CRUD) · `app/templates/` (Jinja2) |
| 페이지 수 | 약 100 페이지 (시안1 Quiet Tone v3 적용 완료) |
| 운영 시작 | 2026-05-29 (NAS 배포 완료, HTTPS 활성화 대기 중) |

---

## 1. 배포 방법 (코드 고친 뒤 반영하는 법)

표준 순서는 **수정 → 커밋 → GitHub push → NAS pull → supervisor restart** 입니다.

```bash
# 1) 로컬에서 코드 수정 + commit + push
git add <고친파일>
git commit -m "설명"
git push origin main

# 2) NAS 컨테이너 SSH 접속
ssh -p 31201 root@o.knknara.co.kr

# 3) 컨테이너 안에서
cd /opt/knk_haist
git pull
supervisorctl restart knk-works
tail -20 /opt/knk_haist/logs/uvicorn-error.log   # 에러 확인
```

**의존성 변경 시 추가**:
```bash
source .venv/bin/activate
pip install -r requirements.txt
deactivate
supervisorctl restart knk-works
```

---

## 2. 절대 지켜야 할 안전 규칙 (위반 금지)

1. **비밀값을 화면에 출력(echo/print)하지 말 것** — `.env`의 `KNK_SECRET_KEY`, API 키 등. 존재 여부만 확인하고 값은 절대 표시 금지.
2. **프로덕션 SSH 직접 접속(`root@o.knknara.co.kr -p 31201`)으로 읽기/쓰기는 사용자 명시 승인 후에만**.
3. **`KNK_WORKERS` 를 2 이상으로 절대 변경 금지** — SQLite 동시 init 시 database is locked 에러.
4. **nginx 백업을 `sites-enabled/` 또는 `conf.d/` 안에 만들지 말 것** — nginx 가 추가 설정으로 읽어 duplicate server 에러. `/root/nginx-backups/` 사용.
5. **컨테이너 안 nginx 의 `/works/` location 은 무용지물** — DSM Reverse Proxy 가 직접 uvicorn 으로 보내서 nginx 안 거침. 손대지 말 것.
6. **DSM 설정 변경**(Reverse Proxy · DNS · SSL · 라우팅)은 전산담당자(최보현 상무) 영역. **빅터 직접 시도 금지**.
7. **메신저 코드 직접 수정 금지** — 메신저는 별도 세션 영역. 사번 SSO 등 협업은 `_TO_메신저세션/` 발주서로만.
8. **`git add -A` 금지** (메모리 룰 — 비밀파일 실수 commit 방지). 개별 파일 명시.
9. **사용자 대신 `gh auth login` / 계정 생성 / 비밀번호 입력 금지.**
10. **지시 받으면 즉시 착수 금지 → 먼저 이해한 내용을 정리해 보고하고, 확인받은 뒤 진행** (대표 직접 지시, 절대준수).
11. 파일 생성·수정은 `KNK업무시스템구축/` 폴더 내부에서만.

---

## 3. 운영 구조 & 장애 주의

### 3.1 컨테이너 구조 (KNKHAIST · Ubuntu 20.04)

```
KNKHAIST 컨테이너 (메신저와 공유)
├── 메신저 (Flask gunicorn, port 5050) ← 시스템 Python 3.8
├── HAIST WORKS (FastAPI uvicorn, port 8081) ← Python 3.11.9 (pyenv)
└── 서로 영향 0 (별도 supervisor program · 별도 venv · 별도 디렉터리)
```

| 폴더 | 컨테이너 안 | NAS host (영구 볼륨) |
|---|---|---|
| 메신저 | `/opt/knk_messenger/` | `docker/Haist/opt/knk_messenger/` |
| HAIST WORKS | `/opt/knk_haist/` | `docker/Haist/opt/knk_haist/` |
| SSH 키·pyenv | `/root/` | `docker/Haist/root/` |

→ **컨테이너 삭제·재생성해도 `/opt`와 `/root` 안 내용은 NAS 디스크에 살아있음**. 같은 볼륨 매핑으로 재생성하면 즉시 복원.

### 3.2 외부 진입 경로

```
인터넷
   ↓
라우터 (80/443 포워딩)
   ↓
NAS DSM nginx (Reverse Proxy)
   ├── haist.knknara.co.kr → :5050 (메신저)
   └── works.knknara.co.kr → :8081 (HAIST WORKS)
```

⚠️ DSM Reverse Proxy 는 **호스트명 단위만** 라우팅. path 기반 라우팅 미지원 (확인됨).

### 3.3 운영 명령

```bash
# 상태 확인
supervisorctl status knk-works                # RUNNING 이어야

# 재시작 (코드 수정 후)
cd /opt/knk_haist && git pull && supervisorctl restart knk-works

# 로그
tail -f /opt/knk_haist/logs/uvicorn.log
tail -f /opt/knk_haist/logs/uvicorn-error.log

# 헬스체크
curl -sS http://127.0.0.1:8081/login            # HTTP 200 정상
```

---

## 4. 망가졌을 때 되살리기 (재해 복구)

**`재현가이드_NAS배포.md` 의 8단계** 참고. 요약:

1. 새 PC에 **Claude Code + Git** 설치
2. 코드 받기: `git clone git@github.com:top00151-commits/knk-haist-works.git`
3. **이 폴더(`_재해복구키트_HAIST_WORKS/`)** 의 `재현가이드_NAS배포.md` 정독
4. 시나리오별 복구:
   - **코드 손상**: `git clone` 다시 + `install_in_messenger_container.sh` 재실행
   - **컨테이너 삭제**: 새 컨테이너 + 같은 볼륨 매핑 → 즉시 복원
   - **NAS 교체**: Hyper Backup 복원 + DSM Reverse Proxy 재등록
   - **GitHub 분실**: NAS 안 `/opt/knk_haist/` 가 사실상 백업본
5. 비밀번호는 회사 금고의 **비상복구_열쇠보관표.md** 에서 확인

---

## 5. 사람 친화 한글 용어 (UI 문구 작성 시)

화면·메뉴는 쉬운 한글로. 영문 약어·기술용어를 그대로 노출하지 말 것.

- 워크플로우 → **일 순서**
- 노드 → **일**
- 마법사 → **만들기**
- IC (Inter-Company) → **사내거래** / **법인 간 매매**
- KR → 한국 / VN → 베트남 / PO → 발주(주문) / SW → 소프트웨어

---

## 6. 외부 브랜드 익명화 (절대준수)

상용 제품·외부 ERP 실명을 **코드·UI·문서 어디에도 직접 거론 금지** (법적 리스크 차단).

| 원래 실명 | 치환 명칭 |
|---|---|
| 위하고 / 더존 / WEHAGO | 외부 ERP |
| 하이웍스 / Hiworks | 외부 그룹웨어 |
| 카카오톡 / 카톡 | 사내 메신저 |
| SAP / Oracle / SystemEver | 참고 ERP |
| 삼성전자/전기 | 고객사A / 고객사B |
| 갤럭시 S27 | 제품1 / P001 |

→ 자세한 매핑: `KNK업무시스템구축/_STANDARDS/외부브랜드_익명화_매핑.md`

---

## 7. 다음 작업 (트리거 대기)

- [ ] HTTPS 활성화 (전산담당자 DSM Reverse Proxy `HAIST_WORKS.HTTPS` 항목 추가)
- [ ] 메신저 세션이 사번 SSO 작업 착수 (발주서: `KNK업무시스템구축/_TO_메신저세션/2026-05-29_사번SSO.md`)
- [ ] HAIST WORKS Phase 2: SSO 클라이언트 구현 (메신저 측 완료 후 3일)
- [ ] z56·z58 마이그레이션 SQL NAS 적용 (`01_HAIST_WORKS/migrations/`)
- [ ] 부품 수출 마진 시스템 정식 발주 (`_TO_빅터/발주_부품수출마진시스템_2026-05-29.md` 결재 4건 대기)

---

## 8. 메모리 룰 인덱스 (~/.claude/.../memory/)

이 세션 시작 시 자동 로드되는 메모리:
- `MEMORY.md` (인덱스)
- `session_team1_platform.md` (이 세션 = HAIST WORKS 빅터(01) 통합 운영)
- `feedback_explain_first.md` (지시 받으면 이해 정리 보고 후 진행)
- `human_friendly_terms.md` (사람 친화 용어 규칙)
- `trademark_anonymization_rules.md` (외부 제품 익명화)

---

**작성: 빅터(Claude) · 2026-05-29**
**기준 시점: NAS 배포 완료 (works.knknara.co.kr HTTP 동작)**
