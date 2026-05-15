# 📊 HAIST WORKS — 통합 상태 보드 (LIVE)

> **목적:** 대표님이 1초 만에 전 팀 진행 상황 파악
> **갱신:** 빅터(01) 만 수정 — 대표 명시 지시 시점에만
> **마지막 갱신:** 2026-05-16 v5H226z104 (**워크플로우 레고 빌더 — 마법사 8문항 + 45노드 + KR↔VN IC 양방향 페어 자동매칭** · 대표 결재 (c) 1+2차 통합 모드)

---

## 🚦 빅터 통합 호출 방법

| 명령 | 작동 |
|---|---|
| **"빅터, 전체 연결성 검증"** | 3팀 산출물 일괄 통합 |
| **"빅터, 팀N 통합"** | 단일 팀만 (빠름) |
| **"빅터, 라이브 검증"** | 65 페이지 자동 검증 사이클 |
| **"빅터, 표준 위반 검사"** | 코드 검수만 (변경 없음) |
| **"빅터, BAT/STATUS 갱신"** | 보고 자료만 |
| **"빅터, 롤백 태그"** | 현 시점 보존 |

---

## 🟢 통합 완료 (2026-05-10 ~ 11)

### 3차 통합 사이클 — z72 / **91 페이지** (방금)

| 팀 | 페이지 | 진행률 | 핵심 |
|---|---|---|---|
| **01A 통합플랫폼** | **22 / 22** | **100% 🟢** | (z71 그대로 + 일부 추가 갱신) |
| **01B 매출영업** | **27 / 30+** | **~90% 🟢** | (z71 그대로 + sales_home·project_detail 추가) |
| **01C 자재구매** | **42 / ~50** | **~85% 🟢** | **+26p 신규** (part·wo·qc·qms·rates·stock 전 확장) |
| **합계** | **91 페이지** | **~70%** | v5H226z71 → z72 |

추가 변경:
- `app/main.py` parts_new/edit 폼 **신규 13 필드** (자재모듈 표준 v2)
- `app/database.py` 자재 컬럼 확장 (+138/-11 lines)
- 라우트 추가 0건 (form field 확장만)

### 2차 통합 사이클 — z71 / 65 페이지 (보존)

| 팀 | 페이지 |
|---|---|
| 01A | 22 / 22 (100%) |
| 01B | 27 / 30+ (~90%, 그룹 H 8p 완벽 / v1 19p 부분) |
| 01C | 16 / 30+ (~50%) |
| 합계 | 65p / commit 41880b7 |

### 커밋 / 태그 / BAT

| 항목 | 값 |
|---|---|
| z72 통합 commit | (방금) |
| z71 통합 commit | `41880b7` (77 files) |
| 롤백 직전 z72 | `rollback-20260511-pre-integration-z72` |
| 롤백 직전 z71 | `rollback-20260510-pre-integration-z71` |
| 롤백 직후 z71 | `rollback-20260510-z71-integrated` |
| **메인 BAT** | KNK_시작.bat / START.bat 모두 z72 통합 ✅ (3곳 동기화) |
| debug_overlay | z72 |

---

## 🔍 자동 검증 결과 (2026-05-11)

### ✅ 통과 (5 카테고리)

| # | 항목 | 결과 |
|---|---|---|
| 1 | 정적 자산 (image·CSS·JS) | **11/11 OK** |
| 2 | HTML 구조 | **64/65 PASS** (daily.html option 자동닫힘은 무해) |
| 3 | Jinja 문법 | **135/135 PASS** |
| 4 | 라우트 응답 | **500 에러 0건** |
| 5 | 데이터 연결성 | **코드 레벨 안전** |

### 🔴 결함 (3건)

**#1 — 01B v1 차수 페이지 토큰 미완성** (시각 일관성)

| 페이지 | v5 잔존 | 빨강 | 등급 |
|---|---|---|---|
| project_detail.html | **62** | 27 | 🔴 즉시 보완 |
| project_form.html | 42 | 13 | 🔴 |
| sales_home.html | 17 | 3 | 🟡 |
| customer_form.html | 12 | **18** | 🟡 (빨강 ≤5% 초과) |

→ 룰 위반 X (v4 단계 분할 정책). 02 차수 보완 필요.

**#2 — project_detail.html 겹침 위험**
- position fixed 4 / sticky 7 / `<style>` 4 / `<script>` 9 / **z-index 9999**
- 시각 겹침 가능성 높음. 대표 라이브 확인 권장

**#3 — 반응형 1100px 미적용**
- 01A 22p: 0/22 ❌ / 01C 16p: 0/16 ❌ (01B만 26/27 적용)

---

## 🔵 다음 차수 우선순위

| 우선 | 대상 | 작업 | 사유 |
|---|---|---|---|
| **1** | 01B | v2 차수 — project_detail · project_form · sales_home · customer_form 토큰 마이그 완성 (~10p) | 결함 #1 |
| 2 | 01A | v3 차수 — 1100px 반응형 + 부록 B specs | 결함 #3 |
| 3 | 01C | 잔여 14p (part_detail / wo_form / qms 4 / rates 5) | 진도 |
| 4 | 빅터 | 마이그레이션 SQL 적용 검토 (`v5H226z56_자재모듈표준v1.sql`) | 결재 대기 |
| 5 | 빅터 | admin*.html / login.html / error.html (~10p) | 빅터 책임 |

---

## 🎯 대표 라이브 검증 추천 (5p · 15분)

| URL | 목적 |
|---|---|
| `/home?debug=1` | 01A 완벽 샘플 |
| `/sales/orders?debug=1` | 01B 그룹 H 완벽 샘플 |
| `/projects/[id]?debug=1` | ⚠️ **위험 페이지** (겹침 확인) |
| `/po?debug=1` | 01C partial 모드 검증 |
| `/stock/balances?debug=1` | 01C 데이터 페이지 |

서버 8081에서 가동 중. Ctrl+Shift+D 토글 / 우측 하단 "🔍 영역 보기" 진입 가능.

---

## 🔴 재작업 지시 / 🚨 충돌

| 시점 | 내용 |
|---|---|
| (없음) | 충돌·재작업 0건 |

---

## 📌 빅터 작업 메모

### z97 (2026-05-11) — 카탈로그 카드 → 부품 상세 링크
**대표 요청**: "부품을 클릭하면 해당 부품 정보 화면이 떠야 부품을 확인할 수 있어"

**구현:**
- 카탈로그 카드의 부품번호·부품명·스펙·메타·가격·재고 영역을 `<a href="/parts/{id}">` 로 감쌈
- 기존 `/parts/{pid:int}` 라우트 + `part_detail.html` 활용 (이미 존재)
- 카드 hover 시 보더 강조 + 부품번호 밑줄
- 즐겨찾기 버튼·수량 입력·담기 버튼은 stopPropagation 으로 클릭 영역 분리

**클릭 영역 분리:**
- 카드 주 영역 (부품번호 / 부품명 / 스펙 / 메타 / 가격) → 부품 상세 이동
- ★ 즐겨찾기 → 토글만 (페이지 이동 X)
- 수량 입력·🛒 담기 → 장바구니 추가만 (페이지 이동 X)

**1 commit 묶음:** catalog.html + BAT z96→z97 (3곳×2) + debug_overlay + STATUS + 롤백 태그

### z96 (2026-05-11) — 카탈로그 한영 동의어 검색
**대표 요청**: "한글과 영어 발음이 비슷한 것도 검색되게 못해?"

**구현:**
- `app/synonyms_parts.py` 신설 — 산업 부품 한영 동의어 사전 ~120 그룹
- `catalog_page()` 검색 로직: `expand_query(q)` 로 입력어를 동의어 그룹 전체로 확장
- 5 컬럼(part_no/name/spec/category/maker) × N 동의어 OR 매칭

**동의어 사전 커버:**
- 공압: 솔밸브↔solenoid valve / sy / sv / vfr, 실린더↔cylinder / cm2 / cdm2 / cj2, 피팅↔fitting / kq2
- 전기: 커넥터↔connector / d-sub, 센서↔sensor, 릴레이↔relay, 엔코더↔encoder
- 기계: 베어링↔bearing, 모터↔motor, 기어↔gear, 볼스크류↔ball screw / bs
- 측정·계측: 게이지↔gauge, 카메라↔camera, 스캐너↔scanner
- KNK 자주 쓰는: 트레이↔tray, 셔틀↔shuttle, 컨베이어↔conveyor / cv, 프로파일↔profile

**실 데이터 검증 (현 219 자재 기준):**
- "솔밸브" → 38건 매칭 (SOLENOID VALVE 그룹)
- "커넥터" → 3건 (D-SUB 등)
- "센서" → 41건

**기능:**
- 한글 → 영어 (`솔밸브` → solenoid·sy 등)
- 영어 → 한글 (`solenoid` → 솔밸브·솔레노이드 등)
- 부분 매칭 (`솔` 만 입력해도 솔밸브 그룹 매칭)
- 공백 무시 (`솔 밸브` = `솔밸브`)
- 대소문자 무시

**성능:** 상위 25 키워드로 제한 (과도한 OR 절 방지)

**1 commit 묶음:** synonyms_parts.py + main.py 검색 로직 + BAT z95→z96 (3곳×2) + debug_overlay + STATUS + 롤백 태그

### z95 (2026-05-11) — 카탈로그 3종 결함 핫픽스

**대표 보고:**
1. 화면이 아래로 쏠림 (사이드바·main 분리 안 됨)
2. 장바구니 클릭 시 OperationalError: no such column: is_active
3. 검색 "솔밸브" 한글 매칭 안 됨

**원인:**
1. `<body>` 다음 `<div class="app">` 그리드 래퍼 누락 → chrome의 sidebar·main grid 적용 안 됨
2. `projects` 테이블에 `is_active` 컬럼 없음 (PRAGMA 확인 결과 status / mgmt_code 등만 존재)
3. 검색 WHERE 절이 part_no / part_name / spec 만 검색 → category·maker 미포함

**z95 핫픽스:**
1. 5 페이지 모두 `<div class="app">` 래퍼 + `{% set active_tab = "logi" %}` 추가
   - catalog.html / catalog_cart.html / materials_requests.html / materials_request_detail.html / materials_new_review.html
2. `/catalog/cart` projects SELECT: `is_active` 제거 → `mgmt_code || name` 표시로 정정
3. 검색 WHERE: category·maker 추가 (한글 카테고리명·메이커명 매칭)

**검증:** Jinja 5/5 PASS / main.py 컴파일 OK / 라우트 4개 모두 303

**참고:** z77 SMC 더미 데이터는 다른 세션이 정리하고 다른 자재(전장 부품·AIR SYSTEM 등 219건)로 교체된 상태. "솔밸브" 검색은 정확 일치 안 되며 "SOLENOID VALVE" 영문 또는 "SY3120" 부품번호로 검색해야 결과 나옴.

### z94 (2026-05-11) — 자재 카탈로그 + 통합 요청서 + 신규 검토 대시보드 ⭐
**대표 통찰**: "BOM 등록 시 등록 자재 확인 + 신규는 따로 표기 → 전 부서 공통"

**핵심 변화 (업무 흐름 자동화):**
- Before: 설계/영업/AS/생산/관리 부서가 각자 채널로 자재 요청 → 구매팀 수작업 매칭 → 오류·지연
- After: 모든 부서가 `/catalog` 출입 → 등록 자재 검색 + 신규 검토 자재 명시적 분리 → 구매팀 통합 대시보드

**구현 (1차 — D 명세 + A 구현 통합):**
- DB 3 테이블 (`material_requests`, `material_request_items`, `catalog_favorites`)
- main.py 라우트 14개 신설
- 페이지 5개 (catalog · cart · requests · request_detail · new_review)
- 5종 요청 유형: 📐 BOM · 💼 견적 · 🔧 AS · 🏭 생산 · 📦 일반

**주요 기능:**
- `/catalog` — 검색 + 카테고리 트리 + 메이커 필터 + 즐겨찾기 + 페이징
- `/catalog/cart` — 등록 자재 + 🆕 신규 검토 자재 분리, 요청 유형 선택, 프로젝트 연결
- `/materials/requests` — 부서별·상태별 필터, KPI 6종
- `/materials/requests/{id}` — 라인별 상태 (등록/신규/검토 상태)
- `/materials/new-review` ⭐ — 구매팀 통합 대시보드 (3가지 액션: 등록·견적·거절)

**시드 데이터:**
- 5개 요청서 (요청 유형별 1건씩) + 16 라인 (신규 검토 4건 포함)

**검증:**
- Jinja 5/5 PASS
- 라우트 4개 모두 303 정상
- main.py 컴파일 OK
- DB 트랜잭션 무결성 (request → items 동시 저장)

**시안1 톤:** qv 토큰 일관 사용, data-dn 라벨 부착, 1100px 반응형 검토 가능

**1 commit 묶음 (룰 적용):**
- main.py + 5 신규 템플릿 + DB 마이그레이션 + BAT z93→z94 (3곳×2) + debug_overlay + STATUS + 롤백 태그
- 롤백 태그: rollback-20260511-pre-z94-catalog
- DB 백업: data/backups/knk_pre_z94_20260515_231928.db

**다음 차수 (대표 결재 대기):**
- z95: 외부 BOM 엑셀 업로드 + 자동 매칭 (헤더 자동 인식 + 편집거리 유사 매칭)
- z96: 견적 요청 워크플로우 (양식 PDF + 수신 등록)
- z97: BOM → PO 자동 생성 + 공급사별 그룹핑

### z93 (2026-05-11) — 드래그 후 클릭 오발사 정정
**대표 보고:** "드래그 후 이동이 정확하지 않고 디버그모드가 켜져"

**원인:**
- z92 의 click blocker (mouseup 시점에서 등록) 가 일부 환경에서 click 이벤트보다 늦게 등록됨
- `<a href="?debug=1">` 의 navigation 이 그대로 발사

**z93 보강 (4단계 차단):**
1. **mousedown** preventDefault 제거 — 단순 클릭 자연 통과 보장
2. **dragstart** 차단 — 브라우저 기본 link drag&drop 끄기
3. **시간 기반 click 차단**: `lastDragEndAt` + 350ms / `lastDraggedEl` 시점에서 capture phase 등록 (mouseup 등록 X)
4. **stopImmediatePropagation** 추가 — 다른 click 핸들러까지 차단
5. **auxclick** 도 같은 시간창에서 차단 (가운데 클릭/우클릭 navigation 우회 방지)
6. `touchAction: none` / `draggable=false` 속성 추가

검증: Jinja PASS / 라우트 303 정상

### z92 (2026-05-11) — 플로팅 아이콘 드래그 이동
- 대표 요청: 이전페이지 / 영역보기 아이콘 위치 사용자 이동 가능
- `debug_overlay.html` 에 드래그 JS 추가 (~80 lines)
- 대상: `#knkBackBtn` (이전 페이지) / `.knk-debug-toggle` (영역 보기) / `.knk-debug-panel` (디버그 패널)
- 기능:
  - 드래그 = 위치 이동 (mousedown/move/up, 4px threshold)
  - 드래그 후 클릭 한 번 차단 (오발사 방지)
  - 더블클릭 = 위치 초기화
  - localStorage 저장 (페이지 새로고침·라우트 변경 후 복원)
  - viewport 경계 clamp (화면 밖 못 나감)
  - 창 크기 변경 시 자동 재clamp
- 라이브 검증: Jinja PASS / 라우트 303 정상
- 1 commit 묶음: debug_overlay + BAT z91→z92 (3곳×2) + STATUS + 롤백 태그
- 메모리 룰 적용: 오늘 날짜 (2026-05-11) 통일 / 다른 세션의 z78~z91 미래 날짜 라벨 정정

### z77 (2026-05-11) — 실무 테스트 가상 데이터 시드

**대표 지시 (내일 실무 테스트 시작 준비):**
- 영업 제외 (이미 70 수주 / 57 프로젝트 / 129 고객)
- 자재구매: SMC 공압 자재 200 + 발주 100
- 통합플랫폼: 20건

**시드 결과:**
| 영역 | 시드 전 → 후 |
|---|---|
| parts (자재) | 14 → **214** (+200 SMC 공압: 솔밸브 30·실린더 40·피팅 35·레귤레이터 15·필터 12·루브 8·FRL 12·호스 15·사이렌서 8·압력스위치 8·센서 12·회전 5) |
| suppliers (공급사) | 6 → 9 (+SMC Korea·한국공압시스템·동양공압상사) |
| purchase_orders (발주) | 0 → **100** (최근 180일 분산, 상태 5종 가중분포) |
| po_items (발주라인) | 0 → 198 (평균 ~2 라인/발주) |
| tickets | 0 → 7 (IT지원·시설·디자인·문서·구매·회의) |
| changes | 0 → 5 (일정·정책·시스템 변경공지) |
| issues | 0 → 5 (AS·품질·설비 이슈) |
| board_posts | 13 → 16 (+3 공지) |
| **합계** | **+320건** |

**안전망:**
- 시드 전 백업: `data/backups/knk_pre_z77_seed_20260511_232418.db`
- 롤백 태그: `rollback-20260511-pre-z77-seed`
- 롤백 SQL: `data/_z77_dummy_rollback.sql` (테스트 후 더미만 일괄 삭제 가능)
- 모든 더미 식별: `note LIKE '%[Z77-DUMMY]%'`

**검증:**
- 14 라우트 모두 303 정상 (500 0건)
- 서버 reload 정상 동작
- random.seed(42) 재현 가능

**정책 환기:**
- SMC 실명 사용 정책 검토 — ERP 거래처/자재 마스터 입력은 실 운영 (외부 노출 X)
- 외부 공개 시 익명화 검토 (메모리 룰 외부 상표권 정책)

### z76 (2026-05-11) — 단일 Ubuntu 컨테이너 배포 패키지 (실 환경 반영)
**대표 NAS 환경 확정 후 z75 패키지 보완:**
- 환경: Synology Container Manager 의 단일 Ubuntu 20.04 (host network 모드, systemctl 없음)
- 메신저가 이미 supervisord + nginx :8080 으로 가동 중 — 같은 컨테이너에 공존
- SSH: 외부 `o.knknara.co.kr:31201` / 내부 `192.168.12.5:31201` (root)
- 외부 HTTP: `o.knknara.co.kr:3310` → 컨테이너:80 (Web Station)
- 빅터 SSH 자동 접속은 보안상 차단 → 패키지만 제공 + 대표가 SSH 실행

**z76 신규 파일 5개:**
- `deploy/setup_ubuntu_container.sh` — 컨테이너 내부 자동 셋업 (apt + venv + .env auto-gen + supervisord 등록 + nginx :8090)
- `deploy/supervisord-knk-haist.conf` — systemctl 대체 (uvicorn 8081 워커 2)
- `deploy/nginx-knk-haist-server.conf` — :8090 server block (uvicorn 프록시 + /static 캐싱)
- `deploy/upload_to_nas.ps1` — Windows tar+scp+원격 압축해제 자동
- `Synology_배포가이드.md` 방법 B 부록 추가 (실 운영 절차)

**z75 산출물 (별도 컨테이너 방식):**
- Dockerfile / setup_synology_container.sh / nginx-synology.conf / sync_to_synology.ps1 — 참고용 유지 (Synology 가 별도 컨테이너 채택 시 가능)

**외부 접속 옵션:**
- (α) 새 외부 포트 3320 → 컨테이너:8090  ← ⭐ 권장 (라우터 1줄)
- (β) haist.knknara.co.kr 하위 도메인 (DNS + nginx server_name 분기 + Let's Encrypt)

**보안 자동 처리:**
- KNK_SECRET_KEY hex 64자 자동 생성 (setup.sh)
- .env 권한 600 / .gitignore 차단
- KNK_MODE=prod 강제

### z75 (2026-05-11) — Synology NAS Docker 배포 패키지 (별도 컨테이너 방식, 참고용)
- 회사 NAS (메신저 가동 중과 동일) 에 HAIST WORKS 추가 배포 준비
- Ubuntu 20.04 base / Python 3 + uvicorn / 비루트 사용자 / 헬스체크
- 8개 파일 생성:
  - `Dockerfile` (Ubuntu 20.04 + Python + Tesseract + Poppler)
  - `.dockerignore` (이미지 크기 최소화)
  - `.env.synology.example` (KNK_SECRET_KEY/MODE/PORT 템플릿)
  - `.gitignore` (.env 등 비밀 보호)
  - `Synology_배포가이드.md` (14단계 상세 가이드)
  - `deploy/nginx-synology.conf` (haist.knk.co.kr 리버스 프록시)
  - `deploy/setup_synology_container.sh` (자동 셋업)
  - `deploy/sync_to_synology.ps1` (Windows → NAS 동기화)
  - `deploy/backup.sh` (DB + 업로드 자동 백업)
- 메신저와 동일 NAS, 포트 분리 (메신저 5050 / HAIST 8081)
- DSM Reverse Proxy 로 haist.knk.co.kr → :8081 매핑

### 외부 공개 전 보안 필수
- KNK_SECRET_KEY 32+자 임의값 (개발 기본값 절대 금지)
- KNK_MODE=prod 설정
- HTTPS 강제 + HyperBackup 자동 백업

### z74 (2026-05-11) — 빅터 대형 마이그 (잔여 결함 1차 해결)
- 12 페이지 v5 토큰 → qv 토큰 일괄 마이그레이션
- 잔존 248건 → 0건 (project_detail 68, project_form 43, sales_home 19, customer_form 12, consumables 11, consumable_detail 8, customer_detail 6, projects 6, consumable_form_upload 6, part_form 10, part_detail 7, part_prices 2)
- customer_form 시각 강조 빨강 1건 정리 (contacts-tbl 테이블 헤더 → 잉크 톤). 의미적 빨강(필수·삭제·에러 JS) 20건 보존
- qv 토큰 +503건 추가
- Jinja 135/135 PASS / 라이브 응답 303 정상
- 1 commit 묶음 룰 적용 (BAT 3곳×2 + debug_overlay + STATUS + 롤백 태그)

### 잔여 (다음 차수)
- 01A 22p + 01C 42p **1100px 반응형** — 페이지 레이아웃 변경 위험성 있어 v3 차수 별도 발주 권장
- 의미적 빨강 검토는 시안1 부록 specs 단계

### z73 (2026-05-11) — 빅터 핫픽스: logistics_home 회귀 정정
- 라이브 검증 발견 결함 #1 즉시 처리
- v5 토큰 15건 → qv 토큰 22건 마이그레이션
- 회귀 원인 commit a6c970f (z108 자재구매 monospace 통일) 작업 중 v5 잔존
- 1 commit 묶음 룰 적용 (BAT 3곳×2 + debug_overlay + STATUS + 롤백 태그)
- 라이브 응답 303 정상

### z72 (2026-05-11) — 3차 통합 사이클 + BAT 룰 강화

**통합:**
- 01C 자재구매 +26p (잔여 14p 명목 → 실제 26p)
- 자재모듈 표준 v2 — main.py parts_new/edit 13 신규 필드 + database.py 컬럼 확장
- 01A·01B 일부 페이지 추가 갱신

**룰 강화 (대표 명시):**
- "통합" 지시 시 BAT 필수 갱신 — 메모리 §5 신설
- BAT LAST UPDATE 날짜 = 오늘 날짜 — 메모리 §2-1 신설
- 3곳(LAST UPDATE / title / echo) 동일 날짜·동일 버전 동기화

**1 commit 묶음 (룰 적용):**
- 변경 템플릿/코드 + BAT(3곳×2) + debug_overlay + STATUS + 롤백 태그 2개

### z71 (2026-05-10~11) — 2차 통합 사이클 + 전면 자동 검증

**통합 단계 (5/10):**
- 3팀 65p 검수 → 메인 적용 → BAT z59→z71 → 롤백 태그 2개 → commit 41880b7
- 모두 옵션 A 자동 충족 (메인 직접 작업)

**자동 검증 단계 (5/11):**
- 정량 grep + Jinja 컴파일 + HTML 파싱 + 라우트 ping + CSS 분석
- 통과 5/5, 결함 3건 (모두 v2/v3 차수에서 보완 가능, 롤백 불요)
- BAT echo 날짜 정정 (commit 5e3eff6)

**빅터 한계:**
- 인증 우회 권한 거부 → 로그인 후 실제 시각 렌더링은 대표 직접 확인
- 권한별 분기 / empty-state / 반응형 깨짐 = 라이브만 가능

### z59 (2026-05-10 ADDENDUM v4) — 4충돌 정정
- BAT 권한 / v5H226z 라벨 / 워크트리 동기화 / (e) 단계 분할 명확화

### z57 (1차 사이클) — 01A 답변 / 01B 착수 / 01C po_list

---

## 🎯 페이지별 진행률

### 01A 통합플랫폼 — 22/22 = 100% 🟢
home·daily·weekly·now·team·cockpit · notifications·calendar·search · tickets×3·changes×3·issues×3·board×4·profile

### 01B 매출영업 — 27/30+ ≈ 90% 🟢 (그룹 H 8p 완벽 / v1 19p 부분)
**완벽 (그룹 H):** export_home·order_detail·order_form·ci·pl·bl_customs·fta_list·fta_form
**부분 (v1):** project_detail·projects·project_form · sales_orders·sales_home·sales_order_detail · customer_detail·customer_form·customers_list · sales_quotations·quote_detail·quote_form · sales_shipments_receipts·outstanding·aging·dashboard·forecast·production
**잔여 3p:** 소모품 외

### 01C 자재구매 — 42/~50 ≈ 85% 🟢 (z72에서 +26p)
**완료 (z71):** po_list·po_detail·po_form·po_receive · logistics_home · parts·suppliers · stock×7 · wo_list·qc_report_list
**z72 추가 (26p):** part_detail·part_form·part_prices·supplier_form · wo_form·wo_print · qc_report_form·qc_report_print · qms×4 (capa·dashboard·pareto·recurrence) · rates×5 (rates·alerts·cost_sim·dashboard·history) · stock×7 (adjust·adjustment·audit·audits·fifo·issue·issues·qc) · fx_rates
**잔여:** consumables 세부 화면 등 ~8p

⚠️ z72 신규 14p 토큰 검수: part_detail (old 7), part_form (old 10), part_prices (old 2) — v5 잔존. partial 의존이지만 인라인 잔존 있음. 02 차수 권장.

### 빅터(01) 책임 — 공통/관리자
- [x] chrome.html / styles.html / design_quiet_v3.html / debug_overlay.html (z71)
- [x] STATUS.md 운영 체계 / 발주서 + ADDENDUM v3·v4
- [x] 1차·2차 통합 사이클 / 자동 검증 시스템
- [ ] admin*.html (관리자/권한) / login.html / error.html

---

## 📈 누적 통계

| 지표 | 값 |
|---|---|
| 총 페이지 | 130+ |
| **시안1 적용 완료** | **65** (완벽 30 + 부분 35) |
| 미적용 | ~65 |
| **전체 진행률** | **~50%** |
| 1차 통합 사이클 (z57) | ✅ |
| 2차 통합 사이클 (z71) | ✅ |
| 자동 검증 사이클 (z71) | ✅ |
| 발견 결함 | 3건 (모두 비-블로커) |

---

## 🔔 대표 결재 / 통보 사항

### 대기 중
1. **마이그레이션 SQL 적용 결재** — `01C_HAIST_WORKS_자재구매/migrations/v5H226z56_자재모듈표준v1.sql`
2. **자재 라우트 확장 결재** — `database.py:po_list()` SELECT 확장 (사업부·품명·L/T)
3. **다음 차수 발주** — 우선순위 1 (01B v2) ~ 5 (빅터 admin)

### 완료
- 1차 통합 사이클 (z57)
- 2차 통합 사이클 (z71)
- 자동 검증 사이클 (z71)
- BAT 동기화 (z71)

---

**관련 문서:**
- `_ORDERS/` — 발주서
- `_STANDARDS/` — 전 팀 표준
- `01[A/B/C]/PROGRESS.md` — 각 팀 진행 추적
- `01[A/B/C]/output/HANDOFF_*` — 빅터 통합 입력
- `01[A/B/C]/output/REPLY_FROM_01_*` — 빅터 응답
