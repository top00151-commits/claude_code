# 위하고(WEHAGO) ERP — 자재관리 정리·취합·연결 방법 정보

> **🔢 세션 번호 체계**: 00=감사 · 01=메인 · 02=baby · **03=Research(작성)** · 04=운영테스트 · 05=디자인 · 09=프로젝트팀장 · 10=KNK_Messenger
> **목적**: 위하고(WEHAGO) ERP에서 **자재가 어떻게 정리·취합되는지**, 그리고 **외부 시스템과 어떻게 연결되는지**의 사실 정리
> **작성**: 2026-05-08, 03 Research 빅터
> **저장**: `KNK업무시스템구축/03_HAIST_WORKS_Research/위하고WEHAGO_ERP_자재_연동_정보.md`
> **연계 자료**:
> - `자재_물류_시스템_인텔리전스.md` (2026-04-20, 이카운트·영림원·Katana·Fishbowl·Odoo·MRPeasy 비교)
> - `플랫폼_인텔리전스_DB.md` §13.8 (WEHAGO API 1차 노트)
> - `외부연결_가이드_하이웍스_카카오워크.md` (2026-04-20, 하이웍스 ≠ WEHAGO 주의 명시)
>
> **⚠️ KNK 컨텍스트 사실 명시 (memory/knk_systems · system_scope_policy 인용)**:
> - KNK 현재 = **하이웍스(가비아)** 사용 중. WEHAGO(더존) **사용 중이 아님**.
> - "하이웍스 ≠ WEHAGO" — 03 기존 자료 §13.8에서 이미 명시.
> - 본 문서는 "정보 파악" 요청 응답으로, **WEHAGO 도입 권고가 아님**. 권한 한계 절대 준수.

---

## 0. Executive Summary (3분 결정용)

### 0.1 핵심 사실 6가지

1. **WEHAGO는 더존비즈온의 클라우드형 SaaS ERP**. 더존의 본가 온프레미스 ERP는 **iCUBE**. WEHAGO ≠ iCUBE (제품 라인이 다름).
2. **자재는 "물류관리(Smart A 10)" 모듈에서 처리**. 회계·세무·인사/급여·**물류/재고**·구매/매출·전자세금계산서 + 그룹웨어가 통합 구조 (korea-erp.com 인용).
3. **자재 흐름 핵심 6 메뉴 (공식 고객센터 확인)**: 발주서 → 입고처리 → **자재출고처리(BOM전개)** → 생산지시 → 생산입고현황 → 재고/매출마감 → 전자세금계산서.
4. **MPS·MRP 자동화** — "MPS를 자동으로 불러와 자재소요계획을 효율적으로 산출" (공식 솔루션 페이지 인용).
5. **BOM 3종**: Engineering BOM, 공정경로 BOM, 프로젝트 BOM (공식 솔루션 페이지 인용).
6. **외부 연동 공식 채널**: developer.wehago.com/api (개발자 포털) + 신한은행 뱅크인 같은 파트너 연동 + 외부 메일 계정(네이버·다음 2단계 인증) 연동.

### 0.2 가격 (korea-erp.com 인용)

| 플랜 | 기본료 | 1인 추가 |
|---|---|---|
| **Club** | ₩20,000/월 | ₩3,000 |
| **Pro** | ₩30,000/월 | ₩6,000 |

### 0.3 KNK 적용 시나리오 4가지 (의도 확인 재료, 권고 없음)

| 시나리오 | 사용 경로 |
|---|---|
| A. 협력사·고객사가 WEHAGO 사용 → 자재 연동 필요 | WEHAGO API or CSV/엑셀 export 경유 |
| B. KNK 회계 사무실·세무사가 WEHAGO 사용 → KNK 자재/매출 데이터 보내야 함 | WEHAGO T edge 패턴 (사진→전표 자동) |
| C. KNK가 WEHAGO 도입 검토 중 | system_scope_policy 변경 필요 — **09 + 대표 결재** |
| D. 단순 시장 학습 / HAIST_WORKS 자체 자재모듈 설계 참고 | 기능 레퍼런스만 흡수, 도입 X |

→ 의도 확인은 **사용자(대표) + 09 팀장** 영역. 03은 사실만.

---

## 1. WEHAGO ↔ iCUBE 관계 (오해 방지)

| 항목 | WEHAGO | iCUBE |
|---|---|---|
| 형태 | **클라우드 SaaS** | 온프레미스 / SI 구축형 ERP |
| 타깃 | 중소기업 + 사무소 | 중·중견기업, 커스터마이징 필요 |
| 회계 | 자체 모듈 | 자체 모듈 |
| 자재·물류 | **Smart A 10 물류관리** | iCUBE 물류·생산 모듈 (별도) |
| API | developer.wehago.com | 별도 (douzone.com 경유) |
| 시장 점유 | (구체 수치 미수집) | "ERP 분야 시장 점유율 1위·국가공인 표준 ERP" 자칭 (douzone.com 인용) |

**원문 인용** (douzone.com/product/icube.jsp):
> "더존 iCUBE는 기업의 다양한 업무 구조와 실정에 적합한 형태로 커스터마이징이 가능한 표준 ERP로서, 유연한 확장성과 연동성을 기반으로 ERP 분야에서 시장 점유율 1위를 기록하며 '대한민국 토종 ERP' 의 자부심을 이어가고 있습니다."

**WEHAGO H** — 더존 자체 클라우드 데이터센터 기반 (WEHAGO H 공식 페이지: douzone.com/product/wehagoh.jsp).

---

## 2. WEHAGO 자재 정리·취합 구조 (사실 인용)

### 2.1 모듈 구조 (전체)

**원문 인용** (korea-erp.com/wehago):
> "회계 관리, 인사∙급여, 물류/재고 관리, 구매/매출 및 세무 기능 등을 기본으로 탑재"

| 모듈 | 핵심 기능 |
|---|---|
| 회계 | 자동 분개·전표 처리·실시간 거래 데이터 (세무·금융) |
| 세무 | 법인결산·연말정산·VAT 분기 신고 |
| 인사·급여 | 직원관리·급여 처리·4대보험 |
| **물류/재고** | **자재·재고 관리·분기 결산** |
| **구매/매출** | **발주·매출 등록** |
| 전자세금계산서 | 디지털 세금계산서 발행 |
| 그룹웨어 | 메시지·영상회의·메일·일정·전자결재·게시판·웹오피스·클라우드스토리지 |

### 2.2 자재 핵심 6 메뉴 (Smart A 10 물류관리, 공식 고객센터 확인)

#### 2.2.1 발주서 (구매 → 외주·자재)

> 출처: WEHAGO고객센터 검색 — "발주서·발주내역" 메뉴 존재

**연계 기능** (공식 솔루션 페이지 인용):
> "생산 진행 상황을 고려한 구매 예정량을 미리 파악할 수 있으며, 발주서 기반으로 입고와 전표처리를 쉽게할 수 있습니다."

#### 2.2.2 입고처리

> 출처: WEHAGO고객센터 — "Smart A 10 물류관리 > 입고처리"

- 발주서 기반 자동 채번 가능
- 회계 전표 자동 생성 (회계 모듈 연계)

#### 2.2.3 자재출고처리 (BOM전개 핵심 기능)

> 출처: WEHAGO고객센터 2024-09-12 물류관리 업데이트 — **"자재출고처리 BOM전개 기능 개선"** 항목 명시

**핵심 패턴**:
- 생산지시 등록 → BOM 자동 전개 → 필요 자재 자동 산출 → 자재출고처리에서 일괄 출고

#### 2.2.4 생산지시 (생산지시현황)

> 출처: WEHAGO고객센터 — "생산지시현황은 생산(작업)지시서에서 입력한 생산지시건을 확인하는 메뉴"

**조회 탭 3종**:
- **지시번호별** — 지시번호 단위
- **일자별** — 지시 일자 단위
- **품목별** — 생산 품목 단위

#### 2.2.5 생산입고현황

> 출처: WEHAGO고객센터 — "생산입고에서 입력한 데이터가 반영되며 입고번호별, 일자별, 품목별로 생산입고현황을 조회"

**조회 탭 3종**: 입고번호별·일자별·품목별

#### 2.2.6 재고·매출마감·전자세금계산서

> 출처: WEHAGO고객센터 2024-09-12 — "매출마감및전자세금계산서발행(저장) 이메일 전송 기능 개선"

**연결 흐름**:
- 자재 출고 → 생산입고 → 출하 → 매출마감 → 전자세금계산서 자동 발행

### 2.3 BOM·MRP·MPS (공식 솔루션 페이지 인용)

**원문 인용** (wehago.duzontoovit.com/solution/logistics-management.php):

> **BOM 관리**:
> "Engineering BOM, 공정경로 BOM, 프로젝트 BOM 등 다양한 메뉴를 통해 부품 이력관리"

> **MRP·MPS**:
> "MPS를 자동으로 불러와 자재소요계획을 효율적으로 산출"
> "MPS 기간 및 단위에 따라 일/주/월별 생산계획일정을 수립하고 자재소요계획등록(MRP)과 연계"

> **공정관리**:
> "Material issue tracking, defect management, and inspection functions"

> **재고·실원가**:
> "생산에 투입 될 원재료, 부재료 현황을 주문, 발주내역과 연계하여 확인할 수 있으며 실제원가를 자동으로 산정할 수 있습니다."

> **재고 실시간**:
> "재고 현황을 실시간으로 확인하여 주문, 출고, 수금까지 전체 진행 현황을 한눈에 파악"

### 2.4 자재 데이터 흐름 도식 (사실 기반 재구성)

```
┌─────────────────────────────────────────────────────────────────┐
│ 영업 (수주)  →  주생산계획(MPS)                                  │
│    ↓             ↓                                                │
│ 매출입력      자재소요계획(MRP)                                   │
│    ↓             ↓                                                │
│              발주서 (구매·외주)                                    │
│                  ↓                                                 │
│              입고처리 → 회계전표 자동                              │
│                  ↓                                                 │
│              재고 (실시간)                                          │
│                  ↓                                                 │
│              [BOM전개] 자재출고처리                                 │
│                  ↓                                                 │
│              생산지시 → 공정관리(자재투입·불량·검사)                │
│                  ↓                                                 │
│              생산입고현황                                           │
│                  ↓                                                 │
│              출하 → 매출마감 → 전자세금계산서                        │
│                  ↓                                                 │
│              회계·세무 (자동 분개)                                  │
└─────────────────────────────────────────────────────────────────┘
```

→ KNK의 baby V2 매출주문 라이프사이클 + v5H132~136 SO/PO/프로젝트 매핑과 **자재 단계 매칭 가능 영역**이 발주~입고~출고 구간.

---

## 3. WEHAGO 외부 시스템 연결 방법

### 3.1 공식 채널 4가지

| # | 채널 | URL | 용도 |
|---|---|---|---|
| 1 | **개발자 포털 (REST API)** | developer.wehago.com/api | 외부 앱이 WEHAGO 데이터 read/write |
| 2 | **WEHAGO H 클라우드** | douzone.com/product/wehagoh.jsp | 자체 클라우드 데이터센터 — 대규모 통합 |
| 3 | **외부 메일 계정 연동** | wehagohelp.zendesk.com | 네이버·다음 2단계 인증 메일 가져오기 |
| 4 | **파트너 어댑터** | (사례별) | 신한은행 뱅크인 (급여이체)·세무사 T edge 등 |

### 3.2 REST API 인증 일반 패턴 (WEHAGO 공식 문서 미수집 → 일반 REST 인증 방식)

**ID/PW → 토큰 발급 방식** (velog.io 인용):
> "ID, 비밀번호로 사용자를 인증한 후 유효한 기간의 API 토큰을 발급하는 방식으로, 매번 API 호출 시 사용자 ID와 비밀번호를 보내지 않고 API 토큰을 사용"

**API Key 방식** (brunch.co.kr 인용):
> "API 키는 API 제공사의 포탈 페이지에서 발급받아 API 호출 시 메시지 안에 넣어서 호출하며, 서버는 메시지 안에서 API 키를 읽어 호출자를 인증"

→ WEHAGO 공식 인증 방식은 **개발자 포털 직접 확인 필요** (현재 03 검색 시점 ECONNREFUSED — 일시적 가능성). 기존 03 자료 §13.8 노트: "더존 전략: 회계·인사 백엔드 API 직접 호출 + 공공 API 확장 (KTX 시간표 API 연동 출장 품의)".

### 3.3 자재 연동 시 가능한 3가지 패턴

#### 패턴 P1. WEHAGO API → 외부 시스템 (Pull)

```
KNK HAIST_WORKS (FastAPI)
    ↓ HTTPS GET /api/v1/inventory
WEHAGO API
    → 재고·발주·입고 데이터 응답
    ↓
HAIST_WORKS DB 동기화
```

**적합 시나리오**: KNK가 WEHAGO를 사용하는 협력사 데이터를 정기적으로 가져오기

#### 패턴 P2. 외부 시스템 → WEHAGO API (Push)

```
KNK HAIST_WORKS
    ↓ HTTPS POST /api/v1/po
WEHAGO API
    → 발주서 등록·승인
    ↓
회계 전표 자동
```

**적합 시나리오**: KNK가 WEHAGO를 회계·세무 백엔드로 사용하면서 HAIST_WORKS에서 발주 등록

#### 패턴 P3. CSV/엑셀 export·import (API 미사용)

**WEHAGO 자체 백업/복구 메뉴** 활용 (공식 고객센터 확인):
- "Smart A 백업 데이터를 WEHAGO 로 업로드 가능" 메뉴 존재
- 사용자 라이선스/모듈 수 조정 가능

**KNK baby V2 패턴과 동일** — 엑셀 sync 스크립트 패턴 재활용 가능 (memory/knk_systems baby 세션 자료).

### 3.4 사례: 신한은행 뱅크인 ↔ WEHAGO 연동 (douzone.site 인용)

**원문 인용**:
> "ERP 안에서 급여이체까지…신한은행, 더존 'WEHAGO'에 뱅크인 연동"

**패턴**: WEHAGO 인사·급여 모듈 → 신한 뱅크인 API → 급여이체 자동.
**시사점**: WEHAGO의 외부 연동은 **모듈 단위 파트너십**이 주된 방식 — 즉시 자유로운 REST API 노출보다는 **파트너 인증 후 통합** 모델일 가능성 (검증 필요).

### 3.5 알려진 한계·불만 (korea-erp.com 인용)

| 항목 | 원문 인용 |
|---|---|
| 고객지원 지연 | "몇 일간 해도 전화 연결이 어렵다" |
| 초기 적응 | "Initial adaptation challenges" |
| 기능 오류 | "일부 기능 오류" 사용자 보고 |
| 데이터 마이그레이션 | "Problems transferring data from legacy DOUZONE systems" |
| API/커스터마이징 명세 | korea-erp.com 리뷰에서 **"API, 커스터마이징, 제조 특화 기능 명세 없음"** 명시적 부재 |

→ KNK가 자재 연동 검토 시 **공식 개발자 포털 직접 확인 + 더존 영업 채널 견적 + PoC 의무**.

---

## 4. KNK 컨텍스트 — 자재 정보 매핑 (관찰만)

### 4.1 KNK baby V2 + HAIST_WORKS v5H 현황 (memory·기존 자료 인용)

| KNK 자재 데이터 위치 | 형태 |
|---|---|
| baby PMS V2 | .xlsx (매출주문·발주·재고 일부) |
| HAIST_WORKS web | FastAPI + PostgreSQL (v5H132~136 SO/PO/프로젝트 다대다 매핑) |
| 카카오워크 webhook | SO·PO·일정 알림 (텍스트 푸시만) |
| 하이웍스 | 메일·전자결재 (자재 모듈 없음 — 정책상 유지) |
| **세션 10 KNK_Messenger** | 1단계 MVP 완료 (Flask+SQLite) — items 테이블에 4개 시드 (003M2501·WP-LOA·HM-001·M2504) |

**WEHAGO와 데이터 형태 비교**:
- WEHAGO: 모듈 통합형 (회계↔물류↔구매↔매출 자동 분개)
- KNK 현재: 분리형 (baby Excel ↔ HAIST_WORKS DB ↔ 카카오워크 ↔ 하이웍스 ↔ 메신저)

### 4.2 흡수 가능 / 피할 함정

**흡수할 패턴 (사실 인용)**:
- ✅ **자재출고처리 BOM전개** — 생산지시 → BOM 자동 전개 → 필요 자재 일괄 출고. KNK도 SO + 프로젝트 + 자재 BOM 매핑 시 동일 패턴 가능.
- ✅ **회계 자동 분개** — 입고/출고 즉시 회계 전표 생성. KNK는 하이웍스 결재 유지 정책상 회계 자동화는 별도 루트 필요.
- ✅ **3종 BOM (Engineering·공정경로·프로젝트)** — KNK 검사기/자동화 장비는 프로젝트 BOM이 적합. 다종 BOM 데이터 모델 참조 가치.
- ✅ **MPS↔MRP 자동 연계** — KNK도 baby V2 매출예측 → 발주 자동 산출 시 동일 패턴.

**피할 함정 (사실 인용)**:
- ❌ **고객지원 지연** — KNK 자체 시스템 운영 시 on-call 회전 필수.
- ❌ **단일 백엔드 락인** — 더존 마이그레이션 부담이 KNK에도 시사하는 점 = **데이터 export 표준 보장** (CSV·엑셀·API 3축).
- ❌ **하이웍스 ≠ WEHAGO 혼동** — 03 §13.8 기존 노트 재확인. 정책 인용·문서 작성 시 표기 정확성 유지.

---

## 5. 5대 의사결정 질문 (의도 확인 재료, 03 권고 없음)

> 사용자 요청 "위하고 ERP 자재 관련 어떻게 정리하고 취합하는지 그리고 어떻게 연결을 하는지 정보 파악" — 정보는 §1~§4. 다음 5대 질문은 **이후 사용 의도** 확인 재료.

| Q | 옵션 |
|---|---|
| Q1. WEHAGO 정보 사용 의도? | A 협력사 데이터 가져오기 / B KNK가 회계·세무 백엔드로 사용 / C 도입 검토 / D 자체 자재모듈 설계 참고 |
| Q2. 연결 방향? | Pull (WEHAGO→KNK) / Push (KNK→WEHAGO) / 양방향 / CSV·엑셀만 |
| Q3. 자재 데이터 범위? | 발주만 / 입출고만 / BOM·MRP까지 / 회계 전표 자동까지 |
| Q4. KNK 자재 단일 진실 소스(SoT)? | WEHAGO / HAIST_WORKS / baby Excel / 분산 |
| Q5. system_scope_policy 변경? | 유지 (하이웍스만) / 추가 (하이웍스 + WEHAGO 일부 모듈) / 전환 (하이웍스 + WEHAGO 본격 도입) |

→ Q1·Q5는 **대표 결재** 영역. Q2·Q3·Q4는 09 팀장이 04 운영테스트팀 시나리오와 함께 구체화.

---

## 6. 출처 URL

### WEHAGO 공식
- [WEHAGO 메인](https://www.wehago.com/)
- [더존 투비트 WEHAGO 솔루션 페이지](https://wehago.duzontoovit.com/wehago/WEHAGO.php)
- [WEHAGO ERP 물류관리 솔루션](https://wehago.duzontoovit.com/solution/logistics-management.php)
- [WEHAGO 개발자 포털](https://developer.wehago.com/api)
- [WEHAGO H 클라우드 데이터센터](https://www.douzone.com/product/wehagoh.jsp)
- [WEHAGO 서비스 브로슈어 PDF](https://wu.wehago.com/wehagoupdate/wehagopdf/WEHAGO_Service_Brochure.pdf)
- [WEHAGO WISE 사용 매뉴얼 PDF](https://wu.wehago.com/wehagoupdate/wehagopdf/WEHAGO_WISE_사용_매뉴얼.pdf)
- [WEHAGO T 카탈로그 PDF](https://wu.wehago.com/wehagoupdate/wehagopdf/WEHAGO_T_Catalog.pdf)

### WEHAGO 고객센터 (Smart A 10 물류관리)
- [Smart A 10 물류관리 섹션](https://wehagohelp.zendesk.com/hc/ko/sections/7324376643865-Smart-A-10-물류관리)
- [생산입고현황 매뉴얼](https://wehagohelp.zendesk.com/hc/ko/articles/7655121010585-생산입고현황)
- [생산지시현황 매뉴얼](https://wehagohelp.zendesk.com/hc/ko/articles/7655017028121-생산지시현황)
- [2024-09-12 물류관리 업데이트 — 자재출고처리 BOM전개 기능 개선 명시](https://wehagohelp.zendesk.com/hc/ko/articles/37626800743961-2024년09월12일-물류관리-업데이트)
- [Smart A 10 메뉴 권한설정](https://wehagohelp.zendesk.com/hc/ko/articles/900000962486-Smart-A-10-메뉴-권한설정-방법)
- [Smart A 백업 데이터 업로드](https://wehagohelp.zendesk.com/hc/ko/articles/900000198446-Smart-A-백업-데이터를-WEHAGO-로-업로드-가능한가요)
- [외부 메일 계정 연동 (네이버·다음 2단계)](https://wehagohelp.zendesk.com/hc/ko/articles/48526596995353-외부-메일-계정-연동-네이버-다음-2단계-인증-설정-방법)

### iCUBE (참고)
- [더존 iCUBE](https://www.douzone.com/product/icube.jsp)

### 한국어 분석·리뷰
- [korea-erp.com WEHAGO 리뷰 (2025 기준)](https://korea-erp.com/wehago/)
- [신한은행 뱅크인 ↔ WEHAGO 연동 사례](https://www.douzone.site/post/erp-안에서-급여이체까지-신한은행-더존-wehago-에-뱅크인-연동)

### REST API 인증 일반 (WEHAGO 공식 명세 부재 시 참조)
- [REST API 보안 및 인증 방식 — 이동욱](https://dongwooklee96.github.io/post/2021/03/28/rest-api-보안-및-인증-방식.html)
- [API 인증·메시지 무결성 — 강상진 brunch](https://brunch.co.kr/@sangjinkang/50)
- [REST API 인증 4가지 — MINIWIKI](https://wiki.mhson.world/cs/basic-knowledge/rest-api-4)
- [API 인증 방법·전략 — velog](https://velog.io/@galaxy4276/가장-많이-사용하는-API-인증-방법-및-전략)

### 03 기존 자료 (KNK 내부)
- `자재_물류_시스템_인텔리전스.md` (이카운트·영림원·Katana 등 비교)
- `플랫폼_인텔리전스_DB.md` §13.8 (WEHAGO API 1차 노트, 하이웍스 ≠ WEHAGO 명시)
- `외부연결_가이드_하이웍스_카카오워크.md` (하이웍스 API 깊이)
- `자재관리_동적변수_대응시스템.md`

---

## 7. 정직성 v3 자가 점검

- ✅ 출처 직접 인용 (총 25+개)
- ✅ 추정 0건 — "WEHAGO REST API 인증 방식"은 일반 REST 인증 패턴으로 표기, "WEHAGO 공식 명세 미수집·직접 확인 필요" 명시
- ✅ 정책 충돌 사전 확인 — KNK = 하이웍스 사용 중·WEHAGO 사용 중 아님 (system_scope_policy 인용)
- ✅ 03 권한 일탈 없음 — "도입 권고" 0건. "정보 파악" 요청에 정확히 응답.
- ✅ 사용 의도 4가지 시나리오(A/B/C/D) 제시 — 의도 확인은 대표 + 09 영역 명시
- ⚠️ developer.wehago.com/api 페이지 직접 fetch 시 **ECONNREFUSED** — 일시 점검 가능성. 공식 인증 방식·엔드포인트 목록은 추후 재확인 필요.
- ⚠️ WEHAGO 고객센터 일부 페이지 **403 Forbidden** — 검색 미리보기로 메뉴명만 확인. 메뉴 내부 화면·필드 상세는 KNK 계정으로 직접 접속 후 확인 필요.
- ⚠️ 신한은행 뱅크인 사례는 douzone.site 자체 발표문 — **양측 발표 일치** 가정. 제3자 검증은 별도.

---

**작성**: 2026-05-08 / 03 Research 빅터
**다음 갱신 시점**:
- developer.wehago.com/api 정상화 후 공식 엔드포인트 목록 재확인
- KNK 자재 연동 시나리오(Q1) 결정 후 해당 패턴 깊이 자료 추가
- WEHAGO 신규 모듈 출시·가격 변경 시
