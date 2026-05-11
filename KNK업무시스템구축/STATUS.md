# 📊 HAIST WORKS — 통합 상태 보드 (LIVE)

> **목적:** 대표님이 1초 만에 전 팀 진행 상황 파악
> **갱신:** 빅터(01) 만 수정 — 대표 명시 지시 시점에만
> **마지막 갱신:** 2026-05-11 v5H226z75 (**Synology NAS Docker 배포 패키지 — Ubuntu 20.04**)

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

### z75 (2026-05-11) — Synology NAS Docker 배포 패키지
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
