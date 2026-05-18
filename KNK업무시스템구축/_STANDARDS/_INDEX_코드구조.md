# HAIST WORKS — 코드 구조 인덱스 (Phase 1)

> **대표 결재**: 2026-04-29 (옵션 A → B 단계적 진행)
> **목적**: 코드 수정 시 어디를 봐야 하는지 즉시 찾기
> **단계**: Phase 1 (현재) — 시각적 정리만, 파일 분할 없음
> **다음 단계**: Phase 2 — `app/routes/` 폴더로 영역별 분리

---

## 0. 한 줄

총 **20,000+ 행 Python · 18,000 행 Jinja2 · 7,400 행 CSS** 의 KNK 통합 업무 플랫폼. main.py 안에 13 PART · 77 §섹션으로 구성.

---

## 1. 파일 행수 현황 (2026-04-29 기준)

### Python
| 파일 | 행 수 | 평가 | 목적 |
|---|---:|---|---|
| `app/main.py` | 10,540+ | 🔴 매우 큼 | 모든 라우트 (Phase 2에서 분할 예정) |
| `app/database.py` | 7,733 | 🔴 큼 | DB 스키마·CRUD·시드 |
| `app/victor.py` | 973 | 🟢 적정 | 빅터 AI ask 로직 |
| `app/i18n.py` | 562 | 🟢 적정 | 4개 언어 번역 |
| `app/menu_catalog.py` | 292 | 🟢 깨끗 | M-XX-YY 메뉴 식별 (Phase 1 신규) |
| `app/hiworks_client.py` | 174 | 🟢 깨끗 | 하이웍스 API (스캐폴드) |

### Templates (Top 10)
| 파일 | 행 수 |
|---|---:|
| `base.html` | 1,281 |
| `home.html` | 924 |
| `guide.html` | 686 |
| `login.html` | 467 |
| `base_sales.html` | 402 |
| `base_logi.html` | 388 |
| `admin_team_perms.html` | 372 |
| `part_detail.html` | 350 |
| `change_form.html` | 308 |
| `admin.html` | 308 |

→ 124 템플릿 파일, 총 18,874 행

### Static
| 파일 | 행 수 |
|---|---:|
| `static/style.css` | 7,399 |
| `static/style_hubs.css` | 163 (비활성화 — 주석 처리됨) |

---

## 2. main.py 구조 (13 PART · 77 §)

> **사용법**: 에디터에서 `§N.` 검색 (예: `§42.` → SALES QUOTATIONS 영역으로 점프)

### PART I. 기반 (Core) — Line 1~620
| § | 영역 | Line | 핵심 함수 |
|---|---|---:|---|
| §1 | IMPORTS | 1 | fastapi·database·i18n·menu_catalog |
| §2 | APP 초기화 | 32 | `app = FastAPI()`, middleware, mount |
| §3 | STARTUP + 일일 미작성자 알림 | 40 | `_start_daily_reminder_scheduler()` |
| §4 | Phase 1 빅터 라우팅 + 메뉴 도움말 API | 220 | `POST /victor/route`, `GET /api/menu-help` |
| §5 | HELPERS | 310 | `ctx()`, `get_user()`, `role_home()`, `require()` |
| §6 | Phase 1 메뉴 식별번호 헬퍼 | 395 | `_current_menu_for(path)` |

### PART II. 인증·진입점 — Line 624~668
| § | 영역 | Line | 라우트 |
|---|---|---:|---|
| §7 | AUTH | 624 | `/login`, `/logout`, `/me` |
| §8 | ROOT | 658 | `/` (역할별 자동 분기) |

### PART III. 일상 업무 (전 직원) — Line 669~3000
| § | 영역 | Line | 라우트 | M-코드 |
|---|---|---:|---|---|
| §9 | HOME — 직관적 단일 페이지 | 669 | `/home`, `/home/{date}` | M-00-01 |
| §10 | DAILY — 일일 업무카드 | 904 | `/daily`, `/daily/{date}` | M-00-02 |
| §11 | SUMMARY — 통합 요약 | 1137 | `/summary` | M-00-05 |
| §12 | HISTORY — 개인 히스토리 | 1851 | `/history` | M-00-04 |
| §13 | CALENDAR — 월간 뷰 | 2899 | `/calendar`, `/calendar/{month}` | M-00-08 |
| §14 | FEED — 부서간 피드 | 2974 | `/feed`, `/feed/{date}` | M-00-06 |

### PART IV. 통신·협업 — Line 1303~4858
| § | 영역 | Line | 라우트 | M-코드 |
|---|---|---:|---|---|
| §15 | COMMENTS API | 1303 | `/api/task/{tid}/comments` |  |
| §16 | TASK DETAIL API | 1337 | `/api/task/{tid}/detail` |  |
| §17 | REACTIONS API | 1365 | `/api/task/{tid}/reaction` |  |
| §18 | 번역 API | 1380 | `/api/set-lang` |  |
| §19 | 업무 위임 API | 1462 | `/api/task/{tid}/delegate` |  |
| §20 | 멘션 자동완성 API | 1490 | `/api/users/search` |  |
| §21 | SIDEBAR TREE API | 1501 | `/api/sidebar-tree` |  |
| §22 | ACTIVITIES API | 1550 | `/api/activities` |  |
| §23 | NOTIFICATIONS API | 1784 | `/api/notifications` | M-00-09 |
| §24 | CHANGES INFORM | 3926 | `/changes/*` |  |
| §25 | TICKETS | 4237 | `/tickets/*` | M-00-11 |
| §26 | ISSUES (이슈·AS DB) | 4548 | `/issues/*`, `/qms/issues/*/sla` |  |
| §27 | BOARD (게시판) | 4723 | `/board/*` | M-00-10 |

### PART V. 분석·보고 — Line 1583~2655
| § | 영역 | Line | 라우트 | M-코드 |
|---|---|---:|---|---|
| §28 | SEARCH | 1583 | `/search` |  |
| §29 | RETRO | 1674 | `/api/project/{pid}/retro` |  |
| §30 | COCKPIT | 1694 | `/cockpit`, `/_cockpit_legacy` | M-05-03 |
| §31 | BOTTLENECKS | 1770 | `/bottlenecks` |  |
| §32 | TEAM DASHBOARD | 1904 | `/team`, `/team/{date}`, `/team/permissions`, `/team/{id}/permissions` | M-00-07 / M-04-06 |
| §33 | CEO DASHBOARD | 2176 | `/dashboard`, `/ceo` | M-05-01 |
| §34 | WEEKLY | 2368 | `/weekly`, `/weekly/{wk_mon}`, `/weekly/team`, `/weekly/company`, `/weekly/compare` | M-05-02 |

### PART VI. 프로젝트 — Line 2749~9012
| § | 영역 | Line | 라우트 |
|---|---|---:|---|
| §35 | PROJECT DETAIL | 2749 | `/project/{pid}`, `/projects`, `/projects/new`, `/projects/{pid}/edit` |
| §36 | PROGRESS DASHBOARD | 4150 | `/progress`, `/progress-dashboard`, `/progress/{pid}` |
| §37 | PROGRESS GANTT/BURNDOWN | 8713 | `/progress/{pid}/gantt`, `/progress/{pid}/burndown`, `/progress/{pid}/milestones` |

### PART VII. 매출영업 (M-01) — Line 2825~8021
| § | 영역 | Line | 라우트 | M-코드 |
|---|---|---:|---|---|
| §38 | CUSTOMER LIST | 2825 | `/customers` | M-01-09 |
| §39 | CUSTOMER DETAIL | 2853 | `/customer/{cid}` |  |
| §40 | SALES S1 가드 / 라이프사이클 | 7161 | `/sales`, `/sales/production/start` | M-01-01 |
| §41 | COMPANY INFO (견적서 헤더) | 7246 | (헤더 상수) |  |
| §42 | SALES QUOTATIONS | 7273 | `/sales/quotations`, `/sales/quotations/{id}/print` | M-01-02 |
| §43 | SALES DASHBOARD / FORECAST | 7707 | `/sales/dashboard`, `/sales/forecast`, `/sales/forecast/refresh` | M-01-06·M-01-07 |
| §44 | OUTSTANDING / RECEIPTS | 7914 | `/sales/outstanding`, `/sales/aging`, `/sales/shipments-receipts` | M-01-04·M-01-05·M-01-08 |

### PART VIII. 수출입 (M-01-10/11) — Line 8122~10001
| § | 영역 | Line | 라우트 | M-코드 |
|---|---|---:|---|---|
| §45 | EXPORT P11 | 8122 | `/export`, `/export/orders/*`, `/export/ci/*`, `/export/pl/*`, `/export/bl/*`, `/export/customs/*`, `/export/dashboard` | M-01-10 |
| §46 | EXPORT PRINT | 8555 | `/export/ci/{id}/print`, `/export/pl/{id}/print`, `/export/bl/{id}/print` |  |
| §47 | FTA CERTIFICATES | 9894 | `/export/fta/*` | M-01-11 |

### PART IX. 자재구매 (M-02) — Line 4952~9893
| § | 영역 | Line | 라우트 | M-코드 |
|---|---|---:|---|---|
| §48 | LOGISTICS HUB | 4952 | `/logistics`, `/parts/*` | M-02-01·M-02-02 |
| §49 | SUPPLIERS | 5269 | `/suppliers`, `/suppliers/new`, `/suppliers/{id}/edit` | M-02-03 |
| §50 | PURCHASE ORDERS | 5368 | `/po/*` | M-02-04·M-02-05 |
| §51 | STOCK MOVEMENTS | 5539 | `/stock/movements`, `/stock/balances`, `/stock/balances/fifo/*` | M-02-07 |
| §52 | STOCK S2 가드 / 입출고 | 6870 | `/stock/issue`, `/stock/issues`, `/stock/receipts`, `/stock/qc/*` | M-02-06·M-02-08·M-02-12 |
| §53 | STOCK AUDIT | 5885 | `/stock/audits`, `/stock/audits/{id}` |  |
| §54 | STOCK AUDIT v2 (첨부·close) | 6039 | `/stock/adjustments/*` |  |
| §55 | SAFETY STOCK / REORDER | 9667 | `/stock/safety`, `/stock/reorder-recommendations`, `/stock/alerts/check` | M-02-10·M-02-11 |
| §56 | RATES | 5574 | `/rates` | M-02-13 |
| §57 | RATES STRENGTHENING | 9455 | `/rates/dashboard`, `/rates/cost-sim/{pid}`, `/rates/alerts`, `/rates/price-history/{pid}` | M-02-14 |
| §58 | PRICES BY DATE | 5621 | `/parts/{pid}/prices/*` |  |
| §59 | FX RATES | 9740 | `/fx/rates` |  |

### PART X. 품질관리 (QMS) — Line 9006~10318
| § | 영역 | Line | 라우트 |
|---|---|---:|---|
| §60 | QMS | 9006 | `/qms`, `/qms/issues/{iid}/sla` |
| §61 | QMS CAPA / PARETO | 9218 | `/qms/capa`, `/qms/pareto`, `/qms/recurrence` |
| §62 | QC INSPECTION REPORTS | 10102 | `/qc/inspection-reports/*` |

### PART XI. 생산 — Line 10319~끝
| § | 영역 | Line | 라우트 | M-코드 |
|---|---|---:|---|---|
| §63 | WORK ORDERS | 10319 | `/production/work-orders/*` | M-02-15 |

### PART XII. 관리·설정 (M-04) — Line 3097~6776
| § | 영역 | Line | 라우트 | M-코드 |
|---|---|---:|---|---|
| §64 | ADMIN | 3097 | `/admin` | M-04-01 |
| §65 | MGMT CODE IMPORT | 3194 | `/api/admin/import-mgmt` |  |
| §66 | PASSWORD REGENERATION | 3231 | `/api/admin/regenerate-passwords` |  |
| §67 | GUIDE | 3270 | `/guide` | M-00-13 |
| §68 | EXTERNAL ASSETS REVIEW | 3283 | `/admin/external-assets`, `/api/admin/external-asset-decision` |  |
| §69 | COMPANY INFO ADMIN | 3445 | `/admin/company-info` | M-04-03 |
| §70 | HIWORKS LINKS (HR) | 3519 | `/hr/hiworks` | M-03-02 |
| §71 | PROFILE | 3616 | `/profile`, `/api/profile/*` | M-03-01 |
| §72 | REMINDERS | 3799 | `/admin/reminders` |  |
| §73 | EXPORT WEEKLY CSV | 3840 | `/export/weekly` |  |
| §74 | PERMISSIONS S3 (위임 1차) | 6208 | `/admin/permissions`, `/grant`, `/revoke`, `/audit` | M-04-02 |
| §75 | PERMISSIONS S3 v3 (그룹·매트릭스) | 6458 | `/admin/permissions/groups`, `/matrix` |  |
| §76 | PERMISSIONS REPORT | 6749 | `/admin/permissions/report/*` |  |
| §77 | (관리자 헬스 등 추가 영역) | (분산) | `/admin/health`, `/admin/settings`, `/admin/hiworks-settings` | M-04-04·M-04-05 |

### PART XIII. AI 통합
| § | 영역 | Line | 라우트 |
|---|---|---:|---|
| §77 | VICTOR AI ASK | 6177 | `/api/victor/ask` |

---

## 3. 영역별 라우트 분포 (검색용)

| URL prefix | 라우트 수 | 주 영역 |
|---|---:|---|
| `/stock/*` | 33 | 자재 (PART IX) |
| `/api/*` | 31 | 통신 (PART IV) |
| `/admin/*` | 31 | 관리 (PART XII) |
| `/export/*` | 23 | 수출입 (PART VIII) |
| `/sales/*` | 21 | 매출영업 (PART VII) |
| `/qms/*` | 14 | QMS (PART X) |
| `/board/*` | 12 | 게시판 (PART IV §27) |
| `/parts/*` | 11 | 자재 (PART IX §48) |
| `/rates/*` | 9 | 환율 (PART IX §56·57) |
| `/po/*` | 9 | 발주 (PART IX §50) |
| `/weekly/*` | 8 | 보고 (PART V §34) |
| `/tickets/*` | 8 | 티켓 (PART IV §25) |
| `/progress/*` | 8 | 프로젝트 (PART VI §36) |

---

## 4. database.py 구조 (Phase 1.4 정리 예정)

| 영역 | Line 추정 |
|---|---|
| 스키마 정의 (CREATE TABLE) | 1~750 |
| seed 데이터 / 초기화 | 750~1200 |
| 사용자·인증·권한 | 1200~2000 |
| 일일 카드 / 작업 / 댓글 | 2000~2700 |
| 알림 / activities | 2700~3100 |
| 통합 검색 | 3100~3300 |
| 프로젝트 / 관리코드 | 3200~3700 |
| 안전재고 / 발주 추천 | 3700~4000 |
| 수불 / FIFO | 4000~5000 |
| 매출 / 견적 / 수주 | 5000~5500 |
| 수출입 / FTA | 5500~6500 |
| QMS / CAPA | 6500~7000 |
| 게시판 / 변경 / 티켓 | 7000~7500 |
| 작업지시서 / QC 보고서 | 7500~7733 |

→ Phase 1.4 정확한 매핑 + 표준 마커 적용 예정.

---

## 5. 자주 쓰는 작업 (Quick Reference)

### 신규 라우트 추가
1. 본 INDEX 에서 적합한 PART/§ 확인
2. `app/main.py` 해당 § 영역 끝에 `@app.get("/...")` 추가
3. 메뉴 사용자에게 노출하려면 → `app/menu_catalog.py` 에 M-XX-YY 등록

### 권한 가드 추가
- 일반: `from .database import require` → `u = require(req, ["leader","admin"])`
- 매출: `_s1_guard(req)` (PART VII §40)
- 자재: `_s2_guard(req)` (PART IX §52)
- 환율: `_rates_guard(req)` (PART IX §57)

### i18n 다국어 키 추가
- `app/i18n.py` `_TRANSLATIONS` dict 에 ko/en/vi/ja 4개 언어 추가
- 템플릿: `{{ i.새_키|default('한국어 기본값') }}`

### 새 페이지 사이드바 노출
- `base.html` (통합) / `base_sales.html` (매출) / `base_logi.html` (자재) 중 적합한 곳에 `<a class="sb-item">` 추가

---

## 6. Phase 2 계획 (대표 결재 후 진행)

본 INDEX 가 정상 작동하면 Phase 2 진행:

```
app/
├── main.py                 (~200행 — FastAPI 진입점만)
├── routes/
│   ├── __init__.py
│   ├── auth.py             (PART II)
│   ├── home.py             (PART III)
│   ├── tasks_api.py        (PART IV §15~22)
│   ├── reports.py          (PART V)
│   ├── projects.py         (PART VI)
│   ├── sales.py            (PART VII)
│   ├── export.py           (PART VIII)
│   ├── logistics.py        (PART IX)
│   ├── qms.py              (PART X)
│   ├── production.py       (PART XI)
│   ├── admin.py            (PART XII)
│   └── victor_ai.py        (PART XIII)
├── menu_catalog.py         (그대로)
├── database.py             (Phase 2.5에서 분할 예정)
├── i18n.py                 (그대로)
├── victor.py               (그대로)
└── hiworks_client.py       (그대로)
```

각 router 분할 후 04 회귀 검증 1회씩, 4사이클 분산.

---

## 7. 변경 이력

| 일자 | 변경 | 비고 |
|---|---|---|
| 2026-04-29 | Phase 1 시작 — main.py TOC 삽입, INDEX 작성 | 옵션 A 적용 |
| 2026-04-29 | Phase 1.4 — database.py TOC 헤더 표준화 | 13 PART · 25 § |
| 2026-04-29 | Phase 1.5 — 죽은 코드 점검 | 코드 내부 DEPRECATED 0건 / TODO 1건 (안전) |
| 2026-04-29 | Phase 1.5 — `_LEGACY_v1_logistics_backup/` 외부 이동 | `_ARCHIVE_2026-04-29/` 폴더 생성 / 대표 결재 옵션 가 |
| 2026-04-29 | Phase 1.6 — 폴더 정리 (옵션 2) | 옛 archive 2개 + 카카오워크 가이드 archive로 / 4-25~4-27 발주응답 83개 `_HISTORY_~2026-04-27/` 분리 / admin_settings.html 폴더명 정정 |
| 향후 | Phase 2 — routes/ 폴더 분할 | 대표 결재 후 |

---

## 8. 정리 완료 항목

### 8-1. `_LEGACY_v1_logistics_backup/` 폴더 외부 이동 ✅
- **이전 위치**: `01_HAIST_WORKS/_LEGACY_v1_logistics_backup/`
- **현재 위치**: `KNK업무시스템구축/_ARCHIVE_2026-04-29/_LEGACY_v1_logistics_backup/`
- **결재**: 대표 직접 (옵션 가) 2026-04-29
- **검증**: 활성 코드 import 0건 / SYNTAX OK 유지 / app 모듈 모두 정상
- **부속 자료**: `_ARCHIVE_2026-04-29/README.md` 생성 (보관 사유·금지 사항·복원 방법)

### 8-2. 코드 내부 정리 (점검 결과)
- `# DEPRECATED` 마커: 0건
- `# TODO` 마커: 1건 (database.py)
- → 정리 우선순위 낮음. 다음 사이클로 이연.

---

*Phase 1 (옵션 A) — 코드 깨짐 0건 / 시각적 정리 + 검색성 향상 / Phase 2 분할 사전 준비*
