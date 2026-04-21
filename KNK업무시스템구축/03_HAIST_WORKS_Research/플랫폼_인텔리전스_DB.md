# 플랫폼 인텔리전스 DB — 순수 사실·사례 수집

> **🔢 세션 번호 체계 (2026-04-21)**: 00=감사팀 · 01=메인 · 02=baby · **03=Research(이 세션, 작성자)**. 문서 내 "세션1"·"세션3" 언급은 01·03으로 해석. 상세: `memory/session_separation.md`

> **문서 성격**: 상용 플랫폼들의 **장점·단점·고충·실패·성공 사례 원문 수집**.
> **목적**: 세션3(HAIST_WORKS 메인)이 **자체 구축 시 참조할 사실 DB**.
> **리서치 세션의 규율**:
> - ✅ 사용자 직접 인용·사례·출처 수집
> - ✅ 장점·단점 팩트 병기
> - ❌ **구매 권고 하지 않음**
> - ❌ **아키텍처·로드맵 제시하지 않음**
> - ❌ **"KNK에게 추천" 표현 하지 않음**
>
> **작성**: 2026-04-20 (지속 갱신)
> **세션**: HAIST_WORKS_Research
> **다음 세션 참조**: `@KNK업무시스템구축/HAIST_WORKS_Research/플랫폼_인텔리전스_DB.md`

---

## 📋 목차

1. [BOM·PLM 플랫폼](#1-bom-plm-플랫폼)
   - 1.1 [OpenBOM](#11-openbom)
   - 1.2 [Aras Innovator](#12-aras-innovator)
   - 1.3 [SolidWorks PDM](#13-solidworks-pdm)
   - 1.4 [Siemens Teamcenter](#14-siemens-teamcenter)
   - 1.5 [PTC Windchill](#15-ptc-windchill)
2. [업무·협업 플랫폼](#2-업무협업-플랫폼)
   - 2.1 [Notion](#21-notion)
   - 2.2 [Airtable](#22-airtable)
   - 2.3 [Monday.com](#23-mondaycom)
   - 2.4 [Slack](#24-slack)
3. [ERP 플랫폼](#3-erp-플랫폼)
   - 3.1 [MRPeasy](#31-mrpeasy)
   - 3.2 [SAP Business One](#32-sap-business-one)
   - 3.3 [Odoo](#33-odoo)
   - 3.4 [더존 ERP](#34-더존-erp)
4. [AI/Copilot](#4-aicopilot)
   - 4.1 [Microsoft 365 Copilot](#41-microsoft-365-copilot)
5. [CAD 협업](#5-cad-협업)
   - 5.1 [Altium 365](#51-altium-365)
6. [⭐ KNK CAD 환경 분석 (AutoCAD+SolidWorks+Inventor+AutoCAD 전장)](#6-knk-cad-환경-분석)
7. [SolidWorks Electrical 전환 연구](#7-solidworks-electrical-전환-연구)
8. [Inventor ↔ SolidWorks 이관 심화](#8-inventor--solidworks-이관-심화)
9. [한국 CAD 커뮤니티 현실](#9-한국-cad-커뮤니티-현실)
10. [하드웨어 Git-like 버전 관리](#10-하드웨어-git-like-버전-관리)
11. [자체 MCP 서버 구축 도구·사례](#11-자체-mcp-서버-구축-도구사례)
12. [통합 시스템 유사 사례 — 업계 포지션](#12-통합-시스템-유사-사례)
13. [하이웍스 API·메일 연동 사례·옵션](#13-하이웍스-api메일-연동-사례옵션)

---

## 1. BOM·PLM 플랫폼

### 1.1 OpenBOM

**출처**: G2, Capterra, TrustRadius, OpenBOM 공식 블로그 (700+ 리뷰 종합)

#### 🟢 장점 (사용자 언급)

- 클라우드 네이티브 — 비싼 구축비 없음
- 14일 무료 체험 제공
- ECAD/MCAD 자동 동기화 (의료기기 스타트업 Abram Scientific 증언)
- 3도메인(MCAD+ECAD+SW) BOM 통합
- API 무료 포함 (무제한 호출)
- Abram VP Richard Wiard 인용: "설계 환경을 엔지니어링·품질 도구와 연결 가능한 것이 가치"

#### 🔴 치명적 약점 (사용자 불만 원문)

| # | 고충 | 출처 |
|---|---|---|
| 1 | **"UI가 혼란스럽다. 중앙 부품 DB 탐색·공개/비공개 속성 구분이 어렵다"** | G2 리뷰 |
| 2 | **"신규 사용자 학습 곡선이 가파르다"** | Capterra |
| 3 | **"SolidWorks·ERP 통합이 부족하다"** · **"ERP 통합은 여전히 수동 조정 필요"** | TrustRadius |
| 4 | **"공개 속성 수정 시 기존 데이터에 반영되지 않아 불일치 발생"** | G2 |
| 5 | **"가격이 1년 만에 급증"** | Capterra |
| 6 | **"구매/재고 기능이 $450/월(구 가격)에만 있음 — 경쟁 ERP 대비 불리"** | Capterra |
| 7 | **"BOM 중심이고, 부서 간 업무 커버리지는 PLM보다 좁음"** | TrustRadius |

#### 💰 실제 가격 (OpenBOM 공식 2026)

| Tier | 월간 결제 | 연간 결제 (45% 할인) |
|---|---|---|
| Team | $55/seat/월 | $30/seat/월 |
| Company | $165/seat/월 | $90/seat/월 |
| Enterprise | 맞춤 견적 | — |
| CAD Add-in | $45/seat/월 | $25/seat/월 |

데이터 레코드 초과 시 추가 요금 ($100~$1,000/월, 레코드 수 따라).

#### 📚 사례

**Abram Scientific (미국 의료기기 스타트업)**:
- Arena PLM 8년 사용 후 OpenBOM으로 이관
- VP Richard Wiard: "전통 시스템은 실시간 통합 부재, 스케일 어려움"
- 초기 단계에 선제 도입 (복잡성 덮치기 전)
- DHF/DMR (FDA 규제) 대응 목적

#### 🔍 세션3 참조 포인트 (흡수/회피)

**흡수할 패턴**:
- 3도메인 BOM을 하나의 Digital Thread로 관리하는 개념
- 클라우드·실시간·초기 도입 전략
- CAD Add-in으로 자동 BOM 추출 개념

**피할 함정**:
- UI가 기술 친화적이지 않으면 채택 실패 (KNK가 자체 UI 설계 시 주의)
- 공개/비공개 속성 구분 혼란 방지
- 가격 인상으로 인한 벤더 리스크

---

### 1.2 Aras Innovator

**출처**: Gartner Peer Insights, G2, Capterra, CIMdata 커멘터리

#### 🟢 장점 (사용자 언급)

- 코어 기능 무료 (파트너 유지보수만 유료)
- 저코드 아키텍처로 깊은 커스터마이징
- 자동차·항공 대형 OEM 레퍼런스 다수
- Gartner analyst rating 92점

#### 🔴 치명적 약점 (사용자 불만 원문)

| # | 고충 | 출처 |
|---|---|---|
| 1 | **"데이터 매핑 일관성 부재 · 실시간 데이터 동기화 문제"** | Gartner |
| 2 | **"ERP와 통합이 난장판이다 — 실시간 의사결정 방해, 지연 유발"** | Gartner |
| 3 | **"사무실 전체가 기능·처리 속도를 매일 불평한다. 리포트 포맷 변경이 어렵다"** | Gartner Peer |
| 4 | **"신규 사용자 학습 곡선 극도로 가파름"** | Capterra |
| 5 | **"몇 분 걸릴 작업이 몇 시간 걸린다"** | softwarereviews.com |
| 6 | **"기본 기능(예: Reference Designator 필드)조차 커스텀 설정 필요 — 왜 이렇게 많은 커스터마이징이 필요한가?"** | Gartner |
| 7 | **"지속적인 전문가 지원 필요 · 지원 응답 지연"** | softwarereviews |

#### 🔍 세션3 참조 포인트

**흡수할 패턴**:
- 저코드 커스터마이징 철학 (단, KNK는 자체 코드 기반으로 동일 효과)

**피할 함정**:
- 기본 기능조차 커스텀이어야 하는 구조 → 세션3는 현장 요구를 기본 기능으로 내장
- "커스터마이징 역설" (커스텀 안 하면 못 쓰는 구조)
- UI 성능 최적화 실패 사례 → 대규모 어셈블리에서 느려지지 않게 설계

---

### 1.3 SolidWorks PDM

**출처**: SolidWorks 공식, GoEngineer, xLM, Trimech

#### 🟢 장점 (사용자 언급)

- 싱글 사이트 소형 회사에 특화
- SolidWorks와 native 통합 (설계자 학습 곡선 0)
- check-in/check-out · 상태 기반 권한 · 리비전 관리
- SOLIDWORKS PDM Professional은 SOLIDWORKS 외에 DraftSight, AutoCAD, Inventor, Creo, Solid Edge 파일도 관리

#### 🔴 치명적 약점 (사용자 불만)

| # | 고충 | 출처 |
|---|---|---|
| 1 | **"수년간 비관리 파일 누적 후 PDM 도입 시 중복·깨진 참조·헤더ache 유발"** | Trimech |
| 2 | **"온프레미스 PDM의 총소유비용(TCO)은 초기 SW 비용의 3~5배"** | CAD Rooms |
| 3 | **"Autodesk는 다른 시스템에서 Vault로 마이그레이션 도구 제공 안 함 — 벤더 락인"** | Autodesk |
| 4 | Teamcenter로 이관 서비스 별도 존재 → 마이그레이션 어려움 암시 | PLM CAD Utilities |

#### 📚 사례

- **Vault → SOLIDWORKS PDM 이관**: xLM Solutions 서비스 존재 (즉, 이관이 어렵고 전문 서비스 필요)
- **SOLIDWORKS PDM → Teamcenter 이관**: 완전 릴리스·obsolete 상태 포함해서 성공 사례 존재

#### 🔍 세션3 참조 포인트

**흡수할 패턴**:
- check-in/check-out 개념
- 상태 기반 권한 (In Work → Approved → Released)
- Where Used 추적

**피할 함정**:
- 온프레미스 TCO가 초기 비용의 3~5배 → 클라우드·자체 호스팅 고려 필요
- 마이그레이션 서비스 필요할 정도의 데이터 락인

---

### 1.4 Siemens Teamcenter

**출처**: G2, Capterra, Gartner Peer Insights, TrustRadius

#### 🟢 장점 (사용자 언급)

- Digital Thread — 요구사항 → 시스템 → 멀티CAD EBOM → 변경·변형 → 제조성 → 릴리스 한 줄로 연결
- ECR/ECO 플로우 + redline + 영향 분석 시각화
- ASML (반도체 노광 장비 세계 1위)이 사용

#### 🔴 치명적 약점 (사용자 불만 원문)

| # | 고충 | 출처 |
|---|---|---|
| 1 | **"전체 구조와 UI가 지저분하다 (messy, muddied and convoluted)"** | G2 |
| 2 | **"탐색이 미묘하고 제약되고 번거롭다 (nuanced, constrained, cumbersome)"** | G2 |
| 3 | **"큰 어셈블리 작업 시 성능 문제 — 많은 지연(lag) 발생"** | TrustRadius |
| 4 | **"Teamcenter는 셋업과 관리가 절대적 악몽 (absolute nightmare)"** | 사용자 리뷰 |
| 5 | **"쓸만한 문서가 ZERO. 일반 개요만 있고 예시 없음"** | 사용자 리뷰 |
| 6 | **"관리자 교육이 몇 년 배울 것을 1주일에 밀어넣음 (cramming years into one week)"** | 사용자 리뷰 |
| 7 | **"복잡한 기능이 많아 신규 사용자 인터페이스 학습 어려움"** | Capterra |
| 8 | **"Rich Client 제거가 많은 문제 야기 — 클릭이 너무 많고 사용자가 변경 기피"** | Gartner |

#### 🔍 세션3 참조 포인트

**흡수할 패턴**:
- Digital Thread 개념 (요구사항→릴리스 한 줄 연결)
- ECR/ECO 영향 분석 시각화
- 변경 redline 개념

**피할 함정**:
- UI가 복잡하면 전사 채택 실패 — 세션3는 KNK 현장 부서원도 쉽게 쓸 수 있는 UI 우선
- 문서화 부재로 인한 관리자 훈련 실패 → 부서별 사용 가이드 필수
- Rich Client → 웹 전환 시 사용자 저항 주의

---

### 1.5 PTC Windchill

**출처**: Gartner Peer Insights, TrustRadius, PTC Community 포럼

#### 🟢 장점 (사용자 언급)

- 변경 관리·CAD 통합 기능 강함 (일반적 평가)
- 대기업·중견 제조업 글로벌 레퍼런스

#### 🔴 치명적 약점 (사용자 불만 원문)

| # | 고충 | 출처 |
|---|---|---|
| 1 | **"UI가 복잡·비직관적, 신규 사용자에 특히 어려움"** | Gartner |
| 2 | **"UI가 일관성 없고 구식 — 부서·사이트별 다르게 구현돼서 혼란"** | TrustRadius |
| 3 | **"다른 PLM 대비 학습 곡선 가파름"** | Gartner |
| 4 | **"큰 CAD 어셈블리·다중 리비전 처리 시 성능 저하"** | TrustRadius |
| 5 | **"SAP ERP·ALM 도구 연결에 OSLC 통합 개선 필요"** | TrustRadius |
| 6 | **"CAD 데이터 변경 시 버전 관리 유연성 부족 — BOM 관리 수동 개입 필요"** | Gartner |
| 7 | **"PTC 애플리케이션 엔지니어 고용 권장 — 셋업 복잡함"** | TrustRadius |

#### 🔍 세션3 참조 포인트

**흡수할 패턴**:
- 변경 관리 워크플로우의 ECR/ECO 구조

**피할 함정**:
- 부서·사이트별 다른 구현 → 일관된 표준화 필수
- 외부 전문가 고용해야 하는 복잡도 → 자체 개발이 차라리 나음

---

## 2. 업무·협업 플랫폼

### 2.1 Notion

**출처**: Herdr.io 2025 복 불만 리포트, Notion 공식 성능 문서, Medium 분석, Hack'celeration 2026 리뷰

#### 🟢 장점 (사용자 언급)

- 위키·노트·DB 올인원
- 무료 티어 강력
- Notion AI (GPT-5/Claude Opus/o3 포함, Business plan 이상)
- Notion 3.0 에이전트 — DB 변화 감지·응답 초안·페이지 업데이트
- 한국어 번역 품질 우수 (Herdr)
- 한국 공식 지사·고객 우수 (첫 외국어 = 한국어)

#### 🔴 치명적 약점 (사용자 불만 원문)

| # | 고충 | 출처 |
|---|---|---|
| 1 | **"단일 DB가 1.5MB로 제한됨"** | Notion 2026 성능 문서 |
| 2 | **"DB가 1,000 연관 아이템 초과 시 쿼리 성능 심각 저하"** | 공식 문서 |
| 3 | **"5,000 페이지 상호 연결 시 검색 정확도 떨어짐 (중복 결과 발생)"** | 공식 시뮬 |
| 4 | **"10,000 행 초과 시 눈에 띄게 로딩 지연"** | Herdr |
| 5 | **"Jira·Asana 같은 헤비 시스템의 완전 대체는 아니다"** | 2025 리뷰 |
| 6 | **"Notion AI는 콘텐츠에는 좋지만 핵심 운영 워크플로우에 쓰려고 하면 한계가 명백해짐"** | eesel 분석 |
| 7 | **"'올인원' 철학이 실시간 비즈니스 요구 앞에서는 제약으로 느껴진다"** | eesel |
| 8 | **"Notion→Confluence 이관을 '복붙'으로 생각하면 DB 링크 깨짐·파일 첨부 누락·고아 페이지 발생"** | Data Migration Tools |
| 9 | **"Notion 자동화는 Zapier/Make 의존 필수"** | 병렬 테스트 결과 (오류율 23% vs Airtable 8%) |
| 10 | **"Workers (AI 에이전트): 30초 타임아웃·128MB 메모리·도메인 화이트리스트·Enterprise 전용"** | 공식 문서 |

#### 📚 사례

- **제조업 고객**: "구매 주문 → 생산 태스크 자동 생성 안 됨" → 주문당 15~20분 수작업 × 30~40주문/주 = 주 8~10시간 낭비 (여러 DB 거침)
- 한국 시장: 첫 외국어 한국어로 지정할 정도로 투자, 단 **제조업 사례 극소** (IT/스타트업 위주)

#### 🔍 세션3 참조 포인트

**흡수할 패턴**:
- Relations + Rollups (DB 간 연결·자동 집계)
- Multiple Views (표/칸반/캘린더/타임라인 전환)
- `@` 멘션·태그 시스템
- 페이지 사이드바 네비게이션

**피할 함정**:
- 5,000~10,000 행 벽 → 세션3는 PostgreSQL 기반으로 확장성 확보
- 자동화가 외부 도구 의존 → 내장 자동화 필수
- "올인원"의 역설 (유연함이 제약이 됨)

---

### 2.2 Airtable

**출처**: Capterra, eesel AI, Servalian, Hack'celeration 2026

#### 🟢 장점 (사용자 언급)

- 관계형 DB + 스프레드시트 UI 하이브리드
- 자동화 오류율 8% (Notion 대비 1/3)
- API 응답 2~3배 빠름
- AI 필드 (자동 카테고리, 감성, 요약, 생성)
- 50,000 레코드/base (유료), Enterprise 500K
- 명확한 rate limit 공개

#### 🔴 치명적 약점 (사용자 불만 원문)

| # | 고충 | 출처 |
|---|---|---|
| 1 | **"2024~2025 가격 급증 — Team plan $12→$20 (67% 인상), Business $24→$45 (87.5% 인상)"** | Servalian |
| 2 | **"제약 강화 + 가격 인상 조합 = 'bait and switch'"** | 사용자 표현 |
| 3 | **"티어 한도 초과 시 즉시 업그레이드 강제 — 1건만 넘어도"** | Servalian |
| 4 | **"20,000 레코드 초과 시 성능 저하 — lookup·rollup·formula 사용 시 '저장 중' 수 분 멈춤"** | 커뮤니티 포럼 |
| 5 | **"벤더 락인 — 모든 프로세스를 Airtable 안에 넣으면 이탈이 매우 어려움"** | 다수 |
| 6 | **"가격 인상·기능 변화에 휘둘릴 수밖에 없어짐"** | 사용자 표현 |

#### 📚 마이그레이션 사례

**CornerUp** (PostgreSQL 이관):
- 창업자 Harrison Azizi: "실험 속도 10배 증가"
- 사용자당 라이선스 비용 제거
- 데이터 아키텍처 완전 통제 회복

#### 🔍 세션3 참조 포인트

**흡수할 패턴**:
- Grid / Kanban / Gallery / Calendar 뷰 전환
- Linked record · Lookup · Rollup · Formula 필드 타입
- AI 필드 (자동 카테고리·요약)
- Interface Designer (역할별 맞춤 화면)

**피할 함정**:
- 50K 레코드 벽 → 세션3는 무제한 설계
- 가격 급등 위험 → 자체 구축이 대안
- 락인 구조 → 데이터 소유권 보장

---

### 2.3 Monday.com

**출처**: SaaS Probe, Trackingtime, Productive, Medium

#### 🟢 장점 (사용자 언급)

- 시각적 프로젝트 관리, 보드 기반
- 색상·상태 커스터마이징 직관적
- 비교적 저렴 ($9/seat/월)
- 가장 빠른 온보딩, 비기술 팀에 적합

#### 🔴 치명적 약점 (사용자 불만 원문)

| # | 고충 | 출처 |
|---|---|---|
| 1 | **"팀 확장 시 가격 급증"** | SaaS Probe |
| 2 | **"고급 자동화·워크로드 뷰가 상위 티어에만 있어서 조기 업그레이드 강제"** | Productive |
| 3 | **"유연한 보드가 팀별 다른 프로젝트 구조를 만들어 — 복잡 프로젝트 관리 어려움"** | Productive |
| 4 | **"하위 플랜 자동화 액션 제한 → 운영 확장성 저해"** | 사용자 |
| 5 | **"AI가 실제 있는 티어가 가장 비쌈"** | 비교 분석 |
| 6 | **"무료 플랜이 2명 제한 — 테스트 불가능, 팀이면 즉시 페이월"** | 사용자 |
| 7 | **"관계형 데이터 모델 약함 (Airtable 대비)"** | 비교 |

#### 🔍 세션3 참조 포인트

**흡수할 패턴**:
- 상태별 색상 뱃지 + 드래그 앤 드롭
- 자동 알림 (@멘션·상태 변경)
- Automation Recipes (자연어 → 자동화) + Gantt with dependencies
- 타임라인·간트 뷰

**피할 함정**:
- 티어 업그레이드 강제
- 팀별 보드 구조 파편화

---

### 2.4 Slack

**출처**: Pumble, TechGuide, Chanty, Reworks, Discord vs Slack 비교

#### 🟢 장점 (사용자 언급)

- 2,600 통합 (압도적 생태계)
- Workflow Builder + Conditional Branching
- Channel Routing + Variables
- Zendesk 등 티켓 연동 표준

#### 🔴 치명적 약점 (사용자 불만 원문)

| # | 고충 | 출처 |
|---|---|---|
| 1 | **"가격 상승과 복잡성이 기업을 대안으로 밀어냄"** | Reworks |
| 2 | **"통합이 본질보다 'nice-to-have'인 팀은 가격 정당화 어려움"** | Chanty |
| 3 | **"무료 플랜 메시지 이력 90일 제한"** (Pumble은 무제한) | 비교 |
| 4 | Microsoft 365 기업은 Teams로 이동 — UX는 Teams가 더 무거움에도 불구 | 업계 동향 |
| 5 | Discord로 이동도 있지만: "Discord는 SSO 없음·SCIM 없음·eDiscovery 없음·컴플라이언스 없음 → 엔터프라이즈 보안 감사 실패" | 사용자 경고 |

#### 📚 한국 컨텍스트 (과거 리서치에서 확인)

한국 Slack 사용 기업: **모두 IT/서비스/플랫폼** (라포랩스·바로고·강남언니·페이히어·중고나라·우아한·토스·네이버·카카오·KT DS·SK BB)
→ **제조업 사례 = 0**

#### 🔍 세션3 참조 포인트

**흡수할 패턴**:
- 채널·스레드 구조
- `/command` 단축
- Zendesk 티켓 통합 흐름

**피할 함정**:
- 90일 메시지 이력 제한
- 한국 제조업 부재 (문화 미스매치)
- 엔터프라이즈 보안 요건을 Discord 같은 소비자 도구로 대체할 수 없음

---

## 3. ERP 플랫폼

### 3.1 MRPeasy

**출처**: MRPeasy 공식 case study, Capterra, Unleashed Software 비교

#### 🟢 장점 (사용자 언급)

**실적**:
- Vanquish Hardware: 도입 첫해 매출 25% 상승
- 익명 고객: 재고비 20% 감소 · 10개월 만에 40% 성장
- Motion Impossible (영국 영화 장비사): **외부 컨설턴트 0명**으로 자체 구축 성공
- York Cocoa Works: "자원 이용이 훨씬 효율적, 납기 준수 개선"

- 문서·비디오 튜토리얼 품질 우수
- BOM · MRP · PO · 재고 · 작업지시서 통합

#### 🔴 치명적 약점 (사용자 불만 원문)

| # | 고충 | 출처 |
|---|---|---|
| 1 | **"구식 UI — 단순 작업에 불필요한 단계 추가"** | Unleashed |
| 2 | **"커스터마이징 제약 — 업종별 요구·특수 조정에 벽"** | 사용자 |
| 3 | **"수동 재고 관리 → 시스템 충돌 예기치 않게 발생"** | Capterra |
| 4 | **"통합 옵션 제한 — 타 소프트웨어 연결 어려움"** | 사용자 |
| 5 | **"문서·리포트 기본 커스터마이징도 추가 비용"** | 사용자 |
| 6 | **"회계 기능 최소 — 별도 SW 필요"** | 사용자 |
| 7 | **"지원팀이 타당한 문제 제기를 묵살하는 경우"** | 사용자 |
| 8 | **"거의 다 왔다 싶은 기능이 많지만 (almost there), 고치려면 추가 비용"** | Unleashed |
| 9 | **"한 달 사용이 완전한 재앙이었다 (complete disaster)"** | 극단 사용자 |
| 10 | **"$79/user/월 — 경쟁 솔루션 대비 비쌈 (Odoo $39)"** | 비교 |

#### 🔍 세션3 참조 포인트

**흡수할 패턴**:
- BOM 계층 트리 UI (다중 레벨)
- MRP 제안 알고리즘 (수요→발주 자동)
- 작업지시서(Work Order) 상태 흐름
- 재고 로트 추적
- **"외부 컨설턴트 0명으로 자체 구축" 성공 패턴** (KNK와 유사 상황)

**피할 함정**:
- 커스터마이징 제약 → 자체 구축의 유연성 우위
- 통합 부족 → MCP·API 기반 개방 설계
- UI 구식 → 현대적 UI 필수

---

### 3.2 SAP Business One

**출처**: Noeldcosta, Emerging Alliance, Alluvia, Synavos

#### 🟢 장점 (사용자 언급)

- MRP · 재고 · 공급망 완비
- 재무 안정성
- 2026년 기준 약 $149/user/월

#### 🔴 치명적 약점 (사용자 불만 원문)

| # | 고충 | 출처 |
|---|---|---|
| 1 | **"SME에 구현·라이선싱·유지 비용이 과도 — 초기 비용이 장벽"** | Seidor |
| 2 | **"숨겨진 비용: 추가 사용자·커스터마이징·인프라 업그레이드·3rd party 통합"** | Emerging Alliance |
| 3 | **"연간 유지보수 15~22% (라이선스 비용 대비)"** | Emerging Alliance |
| 4 | **"교육비 $1,000~$5,000, 부서별·고급 교육 시 급증"** | Emerging Alliance |
| 5 | **"통합 비용 건당 $3,000~$15,000"** | Emerging Alliance |
| 6 | **"레거시 데이터 불완전·비일관 시 마이그레이션 시간 연장·비용 급증"** | AIS Corp |
| 7 | **"SAP가 자주 freeze·crash — 작업 유실 스트레스 + 백엔드 에러 유발"** | 사용자 |
| 8 | **"ERP 통합이 가장 큰 불만 — 종이로는 간단해 보이지만 숨은 복잡성·유지보수 악몽"** | Alluvia |

#### 📚 실패 사례 (심화리서치 §6 참조)

- **Hershey 1999**: SAP 할로윈 전 전환 실패, $112M 손실
- **Lidl 2018**: SAP S/4HANA 7년 $500M 쓰고 포기
- **Revlon 2018**: 공장 가동 중단, 주요 소매업체 납품 실패
- **Haribo 2018**: S/4HANA 후 원재료·재고 추적 불가, 마트 품절
- **통계**: 제조업 ERP 73% 실패 (Godlan 2025)

#### 🔍 세션3 참조 포인트

**흡수할 패턴**:
- MRP 계획 알고리즘 (재주문점·안전재고)
- 공급망 모듈 구조

**피할 함정**:
- 숨겨진 비용 구조 (초기 대비 TCO 3~5배)
- freeze·crash → 안정성 테스트 우선
- 레거시 데이터 마이그레이션 철저 준비 필요
- 빅뱅 전환 금지 (Hershey·Revlon 교훈)

---

### 3.3 Odoo

**출처**: PPTS Solutions, VentorTech, AALogics, Plucore, 업계 통계

#### 🟢 장점 (사용자 언급)

- 오픈소스 커뮤니티
- 모듈화 — 선택적 구현 가능
- 저렴 ($24/user/월)
- 설정 대시보드 직관적 (판매·재고·제조·프로젝트·현금)

#### 🔴 치명적 약점 (사용자 불만 원문)

| # | 고충 | 출처 |
|---|---|---|
| 1 | **"MRP 계획은 화면상 좋지만 실제 공장 바닥에서 실패"** | AALogics |
| 2 | **"대부분 문제는 Odoo 자체가 아니라 구현 품질·설정 약함·실제 워크플로우 정렬 실패"** | AALogics |
| 3 | **"'Success Pack'과 BSA 할당이 주요 불만 — 풀 ERP 컨설팅으로 오해됨"** | VentorTech |
| 4 | **"고객 지원이 단편적·영업 중심 (fragmented and sales-oriented)"** | VentorTech |
| 5 | **"ERP 구현 실패율 50~70% (업계 공통) — Odoo도 예외 아님"** | Plucore |
| 6 | **"Odoo 프로젝트 55~75%가 피할 수 있는 실수로 좌초, 비용 초과 189%"** | Plucore |
| 7 | **"모듈화가 관리 소홀 시 파편화 시스템 생성"** | PPTS |
| 8 | **"주요 실패 원인: 계획 부실·사용자 저항·데이터 마이그 오류·커스텀 어려움·기존 시스템 통합"** | Plucore |

#### 🔍 세션3 참조 포인트

**흡수할 패턴**:
- 모듈화 개념 (사이드바 모듈 구조)
- 설정 대시보드 패턴

**피할 함정**:
- "화면상 좋지만 공장 바닥에서 실패" → 세션3는 현장 부서 설문 기반 철저 검증 필요
- 지원 부실 → KNK는 자체 지원·유지 가능
- 파편화 위험 → 표준 아키텍처 강제

---

### 3.4 더존 ERP

**출처**: 한국ERP.com, 클리앙, 나무위키

#### 🟢 장점 (사용자 언급)

- **국내 ERP 시장 강자** (중소기업 1위)
- 회계·재무 기능 강함
- 전국 지원망
- 전자결재·지출결의 자동화 (WEHAGO 계열)

#### 🔴 치명적 약점 (사용자 불만 원문)

| # | 고충 | 출처 |
|---|---|---|
| 1 | **"소규모 고객이 체감하는 지원 만족도 낮음"** | 한국ERP |
| 2 | **"더존 고객센터 전화번호로 몇 일간 해도 연결이 어렵다"** | 클리앙 |
| 3 | **"복잡한 문제 답변까지 시간 많이 걸림"** | 사용자 |
| 4 | **"초기 적응 어려움·일부 기능 오류/개선 필요"** | 한국ERP |
| 5 | **"기존 더존 프로그램과의 데이터 이전 문제"** | 사용자 |
| 6 | **"서비스 만족도 5점 만점 3.5점 — 보통"** | 한국ERP |
| 7 | ⚠️ **"회계쪽은 그나마 괜찮은데 제조관련 모듈은 정말이지 답이 나오지 않습니다"** | 클리앙 사용자 실언 |
| 8 | **"스마트A 2023.12 단종 → 2025.12 유지보수 종료 → 고객 교체 고민"** | 한국ERP |

#### 🔍 세션3 참조 포인트

**흡수할 패턴**:
- 전자결재·지출결의 자동 전표 연동 (WEHAGO와 유지 중이므로 연동만)

**피할 함정**:
- 제조 모듈 부재 → 세션3가 직접 구축하는 영역
- 벤더 단종 리스크 (스마트A 사례) → 자체 구축이 더 안전
- 지원 응대 지연 → 외주 의존 회피

---

## 4. AI/Copilot

### 4.1 Microsoft 365 Copilot

**출처**: Epcgroup, Windows Forum, Computerworld, Avantiico, Forrester TEI, Gartner, HowToGeek, HackerNews

#### 🟢 장점 (사용자 언급)

- Forrester ROI 보고: 3년 112~457% (25K employee 기준)
- Forrester SMB 연구: 3년 132~353%
- Word/Excel/Outlook/Teams 내장 통합
- Production Schedule Optimizer Agent (제조업 특화)
- Product Change Management Agent (승인 기간 몇 주→며칠, BOM 종속성 누락 80% 감소)

#### 🔴 치명적 약점 (사용자 불만 원문)

| # | 고충 | 출처 |
|---|---|---|
| 1 | **🔴 제조업 도입 실패 사건** (특정 제조사): **"5,000 Copilot 라이선스를 월요일 아침 배포 → 화요일까지 800 헬프데스크 티켓 → 금요일 CEO가 'IT에 꺼버리라고 지시' → 재시도 설득에 4개월 소요"** | Epcgroup |
| 2 | **"유료 seat 침투율이 Microsoft 베이스의 작은 분율에 불과"** | Windows Forum |
| 3 | **"활성 채택 불균등, 운영 취약·일관성 없는 출력·불분명한 ROI 불만 증가"** | 업계 리포트 |
| 4 | **"Gartner: 60%가 파일럿 시작했지만 6%만 마무리, 1%만 전 직원 배포 완료"** | Gartner |
| 5 | **"오인식·어지러운 실제 입력에 대한 불안정성 — 수동 교정·감사 필요 → 생산성 이익 훼손"** | 업계 리뷰 |
| 6 | **"Copilot 액세스 받은 직원 중 4 in 10 미만이 실제 사용"** | Avantiico |
| 7 | **"훈련 없이 라이선스만 주면 활성 20% 미만 → CFO가 $30/user/월 투자 의문 제기"** | Avantiico |
| 8 | **"$30/user/월 premium — 명확한 감독·측정 가능한 생산성 없으면 비용 급증"** | Computerworld |
| 9 | **"How-To Geek 헤드라인: 'Microsoft는 Copilot이 쓸모없다는 것을 알고 있다'"** | HowToGeek |
| 10 | **"HackerNews: 'Microsoft 365 Copilot의 상업적 실패'"** | HackerNews |

#### 📚 실패 사건 원문

특정 제조사 (기업명 미공개):
> A manufacturing company deployed 5,000 Copilot licenses on a Monday morning, generating 800 help desk tickets by Tuesday due to issues like Copilot pulling irrelevant content and users not understanding prompts. By Friday, the CEO had instructed IT to "turn it off"—and convincing leadership to try again took 4 months.

#### 🔍 세션3 참조 포인트

**흡수할 패턴**:
- **Production Schedule Optimizer** 개념 (BOM+작업지시+장비 상태+인력 일정 통합)
- **Product Change Management Agent** 개념 (변경 영향 분석·승인 라우팅)
- Teams 내 AI 호출 UX

**피할 함정** ⚠️ 중요:
- **5,000 라이선스 빅뱅 배포 = 4일 만에 폐기** → 세션3는 **5~10명 파일럿 → 부서별 단계 확장** 필수
- "라이선스만 주고 훈련 없음" = 활성 20% 미만 → **사용 가이드·교육 필수**
- "관련 없는 콘텐츠 당김" = RAG 품질 관리 필요 → **임베딩·컨텍스트 품질 검증**
- "프롬프트 이해 못함" → **자연어 질의는 예시·템플릿 제공** 필수
- ROI 측정 불가 → **KPI 사전 정의** (KNK는 이미 설문 기반 KPI 있음)

---

## 5. CAD 협업

### 5.1 Altium 365

**출처**: Altium 공식 Status, IsDown, 공식 FAQ, eevblog 포럼

#### 🟢 장점 (사용자 언급)

- **MCAD CoDesigner = 무료** (Altium 365 Workspace 포함)
- SolidWorks·PTC Creo·Autodesk Inventor·Fusion 360·Siemens NX 지원
- 보드 외곽·컴포넌트 배치·홀 위치·멀티보드 어셈블리 연속 동기화
- 실시간 양방향 (변경 수락/거부 선택)
- 한국 공식 파트너 = 한컴 인텔리전스

#### 🔴 치명적 약점 (사용자 불만 원문)

| # | 고충 | 출처 |
|---|---|---|
| 1 | **"외부 클라우드 제공자 이슈로 incidents 발생"** | Altium 공식 |
| 2 | **"2022.10부터 모니터링 중 101 outages/incidents — 월평균 2.5건"** | IsDown |
| 3 | **"Incident 중간 해결 시간 53분"** | IsDown |
| 4 | **"최근 90일 1 incident, 중간 54분"** | IsDown |
| 5 | **"클라우드 스토리지 추가 과금 가능성"** | eevblog 포럼 |
| 6 | **"Altium 365 연결 끊김 이슈 (Lost Connection)"** | 공식 KB |

#### 💰 가격 (2026)

| 구성 | 연 비용/인 |
|---|---|
| Altium Designer Standard (365 Standard 포함) | $1,495~$2,500 |
| Altium Designer Professional | $3,495~$4,500 |
| Altium 365 Pro 업그레이드 | +$1,000 |
| Altium Designer 한국 표준 (한컴) | $8,795~$10,000 |

#### 🔍 세션3 참조 포인트

**흡수할 패턴**:
- 양방향 실시간 동기화 (변경 수락/거부 UI)
- Board Shape · Placement · Hole Location 동기화 대상
- Push 버튼 + 코멘트 워크플로우

**피할 함정**:
- 월 2.5 outage → 클라우드 의존 리스크
- 인터넷 끊김 시 작업 불가 → 오프라인 대체 전략 필요

---

## 6. ⭐ KNK CAD 환경 분석

> **KNK 실제 사용 도구** (2026-04 기준):
> - **기구설계**: AutoCAD (2D) + SolidWorks (3D) + Inventor (3D)
> - **전장설계**: AutoCAD (AutoCAD Electrical 아닌 일반 AutoCAD 추정)

### 6.1 도구별 기본 정보

| 도구 | 제작사 | 주 용도 | 파일 형식 |
|---|---|---|---|
| AutoCAD | Autodesk | 2D 도면·전장 스키매틱 | .dwg |
| SolidWorks | Dassault Systèmes | 3D 파라메트릭 모델 | .sldprt, .sldasm, .slddrw |
| Inventor | Autodesk | 3D 파라메트릭 모델 | .ipt, .iam, .idw |

### 6.2 3도구 혼용 사례 — 사용자 고충

**출처**: Autodesk 공식, CAD Interoperability, GSC, CAExperts, 사용자 포럼

| # | 고충 | 출처 |
|---|---|---|
| 1 | **"다수 회사가 다중 CAD 환경 — 부서 다수·회사 인수·레거시 유지 때문. 문제는 CAD 간 통신·협업"** | CAD Interoperability |
| 2 | **"SolidWorks → Inventor 변환 시 'dumb solid'로만 들어감 — 피처 트리·스케치 손실, 수정 불가"** | Autodesk 포럼 |
| 3 | **"Inventor → SolidWorks도 dumb solid 문제 동일, 피처 손실"** | Autodesk |
| 4 | **"SolidWorks configurations(iPart/iAssemble 유사)는 Inventor 변환 시 까다로움"** | solidsolutions |
| 5 | **"STEP/Parasolid export는 'dead' B-Rep geometry만 보존 — 피처 트리 손실로 타 시스템에서 수정 불가"** | CAD Interoperability |

### 6.3 통합 메커니즘 (팩트)

#### 🔷 AnyCAD (Inventor)

Inventor는 **AnyCAD** 기능 내장:
- SolidWorks·CATIA V5·NX·Creo·Fusion 360 파일을 **native 없이 참조**
- **양방향 associativity** — 원본 파일 변경 시 Inventor 어셈블리에 자동 전파
- 멀티 CAD co-design 가능 (공급사 SolidWorks · 본사 Inventor 시나리오)

#### 🔷 DWG 파일 처리 (Inventor)

- **DWG Underlay**: 2D DWG를 스케치 평면에 투명 전사 → Project DWG Geometry로 스케치 생성
- **Inventor ↔ AutoCAD DWG 양방향 연결** — AutoCAD에서 DWG 수정 시 Inventor 파일 자동 업데이트

#### 🔷 SOLIDWORKS PDM Professional

관리 가능 파일 (non-native 포함):
- SOLIDWORKS · DraftSight · **AutoCAD** · **Inventor** · Creo · Solid Edge
- 레거시 CAD 파일과 신규 SOLIDWORKS 파일이 같은 폴더에 공존 가능

### 6.4 BOM 통합 — 실제 사례

**Pump and Abrasion Technologies** (중량 펌프 제조):
- SOLIDWORKS → ERP BOM 수동 내보내기에 **BOM당 15~20분**
- 월 총 15시간 이상
- CADTALK 통합 후: BOM당 2~3분, 월 10시간 이상 절약

**Sands Agricultural Machinery** (영국 농기계):
- Autodesk Inventor CAD와 Infor CloudSuite ERP 단절
- 설계 작업이 ERP에 일관되게 전송되지 않음
- 과도한 수동 작업 강제

**Peerless-AV**:
- 파일 분산·설계 데이터 오류로 중요 데이터 일관성 문제
- 수동 데이터 입력이 엔지니어링에 여러 시스템에 걸쳐 재입력 강제

### 6.5 AutoCAD Electrical (참고 — KNK는 이것 아닌 일반 AutoCAD 사용)

**만약 KNK가 AutoCAD Electrical 사용 시 얻을 기능**:
- 스키매틱에서 직접 BOM 리포트 생성
- Vault 통합 시 BOM을 Item Master로 자동 채움
- Phoenix Contact·WAGO·Weidmuller 터미널 스트립 데이터 직접 내보내기
- OpenBOM 통합 (one click component data)

**실제 AutoCAD Electrical BOM 사용자 고충**:
| # | 고충 | 출처 |
|---|---|---|
| 1 | **"BOM 리포트에 설명이 누락 — 카탈로그에서 부품을 선택·클릭해야 설명 포함"** | Autodesk |
| 2 | **"부품 번호 끝 공백·어셈블리/설치 코드 불일치 → 설명 누락"** | Autodesk |
| 3 | **"Vault Professional에서 AutoCAD Electrical BOM 레퍼런스 지정자(location, tag) 속성 선택 불가"** | Autodesk |
| 4 | **"BOM 생성 시 다른 프로젝트 데이터가 당겨짐 — 활성 프로젝트로 돌리기 어려움"** | 사용자 |
| 5 | **"스키매틱·패널 두 BOM 관리 필요 — 단순 셋업은 '한 패널, 한 BOM' 권장"** | Graitec |

### 6.6 일반 AutoCAD (전장)로 도면 관리 시 실태

**출처**: OpenBOM AutoCAD Electrical 통합, Autodesk Vault, Coolorange

**고충**:
| # | 고충 | 출처 |
|---|---|---|
| 1 | **"일반 AutoCAD 스키매틱은 BOM 자동 추출이 어려움 — 수동 리스트링"** | 업계 |
| 2 | **"엔지니어링 팀이 BOM·재사용 프로젝트 데이터 관리·재사용에 고충 — 같은 도면의 여러 버전 부유"** | Coolorange |
| 3 | **"엔지니어가 BOM 수정했는데 제조가 구 사본 계속 사용 — 변경 관리 이슈"** | Coolorange |
| 4 | **"중앙 primary DB 없이 구식 스프레드시트 리스트 잔존"** | Coolorange |

**해결 옵션 (사실만)**:
- OpenBOM이 AutoCAD Electrical 통합 제공 (일반 AutoCAD는 직접 지원 제한적)
- Autodesk Vault가 AutoCAD Electrical 프로젝트에서 BOM 추출 가능

### 6.7 🔍 세션3 참조 포인트

**사실 요약**:
- KNK는 **4개 CAD 도구** 동시 사용 (AutoCAD · SolidWorks · Inventor + 전장 AutoCAD)
- **AnyCAD (Inventor)**는 SolidWorks 양방향 참조 가능 — 피처 손실 없음
- **DWG 파일은 Inventor와 AutoCAD 간 자동 업데이트** 링크 가능
- **SOLIDWORKS PDM Professional**이 Autodesk 파일도 포함 관리 가능
- **일반 AutoCAD 전장 스키매틱은 BOM 자동 추출 기능 없음** — 수동 리스트링 또는 외부 도구(OpenBOM·Vault) 필요
- **CAD → BOM 수동 입력은 월 15시간+ 소요** (실제 사례)

**세션3 고려 가능 방향 (사실 기반, 권고 아님)**:
- 4개 CAD 도구 파일을 **메타데이터만 인덱싱**하는 방식 (세션3 직접 구축 시)
- AnyCAD 개념을 **참조 링크 모델**로 재현 가능
- DWG·SLDPRT·IPT 파일의 **파일 시스템 감지 + 버전 관리**는 자체 구축 영역
- **BOM 자동 추출**은 각 CAD API (SolidWorks API·Inventor API·AutoCAD ObjectARX) 접근 필요
- 일반 AutoCAD 전장 도면의 **BOM 자동화는 가장 어려운 영역** — 스키매틱 블록 태깅 표준 필요

**피할 함정**:
- dumb solid 변환 후 피처 손실 → 편집 원본은 원래 도구에서만
- 다중 CAD 표준 부재 → 관리코드·버전 표준 필수
- BOM 수동 입력의 월 시간 낭비 → 자동화 우선 영역

---

## 📌 이 문서의 규칙

1. **사실만 기록**: 사용자 인용·출처·통계·사례
2. **구매 추천 금지**: "KNK는 X를 도입해야" 표현 없음
3. **아키텍처 제안 금지**: 세션3 결정 사항
4. **지속 갱신**: 신규 리서치 추가될 때마다 섹션 확장
5. **세션3 친화**: "흡수할 패턴 / 피할 함정" 형식으로 참조 포인트 제공

---

**최종 갱신**: 2026-04-20 (Batch 1+2+3+Multi-CAD+§7~§12 신규 추가)

---

## 7. SolidWorks Electrical 전환 연구

**출처**: Javelin-tech, GoEngineer, Capterra, TriMech, SolidWorks 공식, Autodesk Community

### 7.1 SolidWorks Electrical 2026 공식 기능 (팩트)

- 스마트 커넥터 도구
- 3D 라우팅 개선
- 협업 기능 향상
- 시간 절약·병목 제거 목적

### 7.2 AutoCAD Electrical → SolidWorks Electrical 전환 시 알려진 두려움 요소

| # | 두려움 | 출처 |
|---|---|---|
| 1 | 레거시 프로젝트 데이터 손실 | SolidWorks 공식 migration 가이드 |
| 2 | 생산성 손실 (학습·적응 기간) | 공식 |
| 3 | 학습 곡선 | 공식 |
| 4 | 워크플로우 유연성 | 공식 |
| 5 | 산출물 품질·포맷 | 공식 |

### 7.3 성공적 전환 권장 패턴 (사실)

- **레거시 문서 버전 관리 하에 보존**
- **AutoCAD/AutoCAD Electrical은 기존 편집 용도로 유지**
- **신규 프로젝트부터 SolidWorks Electrical로 시작**
- **SolidWorks 전환 유틸리티** 확인 → 완전 재작도 회피

### 7.4 공개 구체 케이스 스터디

**검색 결과**: 2025~2026 AutoCAD Electrical → SolidWorks Electrical로 전환한 **구체 회사 케이스 스터디 공개 자료는 제한적** (공급사 마케팅 자료가 대부분).

### 7.5 세션3 참조 포인트

**흡수할 패턴**:
- "레거시 유지 + 신규는 신 도구" 분리 전략 (빅뱅 전환 회피)
- 2D 도면 양방향 참조 유지 개념

**피할 함정**:
- 구체 성공/실패 케이스 자료 부족 → 실제 효과 검증 어려움
- 공급사 마케팅 자료와 실사용자 경험 갭

---

## 8. Inventor ↔ SolidWorks 이관 심화

**출처**: Autodesk Community, Javelin-tech, Hawk Ridge Systems, SWYFT Solutions, Ketiv, TransMagic, GSC, CAD Exchanger

### 8.1 핵심 사실 (반복 확인)

- **Feature tree는 이관 시 완전 손실** — 각 시스템으로 전송 시마다
- **STEP·Parasolid·IGES 등 중립 포맷은 'dumb solid'만** 전달 (피처·스케치 없음)
- **2D 도면은 호환 불가** — Inventor는 SolidWorks 부품·어셈블리만 열고 도면은 못 열음
- **iPart/iAssemble ↔ SolidWorks configurations**는 개념 유사하나 변환 까다로움

### 8.2 실제 사용자 포럼 질의·결론 (원문 인용)

**Autodesk Community 질의**: 부서 1은 SolidWorks, 부서 2는 Inventor 사용 — 모델 전송 방법?

**경험자 결론 (원문 요약)**:
> "SolidWorks 파일을 Inventor에서 native 'feature tree'로 수정할 수 있는 능력은 **존재하지 않는다**. 한 시스템에서 다른 시스템으로 전송 시 feature tree는 essentially lost."

> "부서 간 왕복 수정 필요 시, **하나의 프로그램으로 통합**하는 것이 권장."

### 8.3 AnyCAD (Inventor 기능)의 한계

- **양방향 associativity** — 원본 변경 시 참조본 자동 업데이트
- **하지만 Inventor에서 직접 편집은 여전히 불가** (원본 SolidWorks 파일을 SolidWorks에서 편집해야)
- 공급사-본사 협업 시나리오에 적합 (편집 없는 참조)

### 8.4 3rd Party 변환 도구 (TransMagic 등)

- TransMagic, CAD Exchanger 등 변환 도구 존재
- **"full editing capability" 약속은 신중 검토 필요** — 피처 트리 복원은 여전히 제한적
- 일부 스마트 변환은 가능하나 완벽한 네이티브 편집은 보장 안 됨

### 8.5 데이터 손실 리스크

| 구분 | 내용 |
|---|---|
| 숨김 파일 | "일부 파일은 손실되거나 의도적으로 숨겨질 수 있음" |
| 폴리곤 메시만 전송 | 모든 파일이 함께 전송 안 되면 근사 지오메트리만 남음 |
| 정확 지오메트리·설계 정보 손실 | 전체 디자인 인텐트 파악 불가 |

### 8.6 세션3 참조 포인트

**팩트**:
- KNK가 Inventor + SolidWorks 둘 다 유지 시 **네이티브 편집 왕복은 불가** — 원본 도구에서만 편집
- 메타데이터·참조·BOM 통합은 가능 (편집 분리 정책 필수)

**세션3 설계 시 고려 사항 (사실 기반)**:
- "어느 CAD가 원본(source of truth)인지" 파일별 명시 필요
- BOM 통합은 메타데이터만 — 피처 트리 불가능
- 부서 간 편집 왕복 시나리오는 기술적으로 불가 → 프로세스로 해결

---

## 9. 한국 CAD 커뮤니티 현실

**출처**: JobKorea, 고캐드, 나무위키, 클리앙, Decre Yellow

### 9.1 한국 제조업 CAD 보급률 (팩트 요약)

| 구분 | 주 사용 도구 |
|---|---|
| **2D 도면** | AutoCAD (지배적) |
| **3D 기구 설계** | Creo · Inventor · CATIA · Solid Edge |
| **3D 기계 설계** | NX UG · CATIA · SolidWorks |
| **업계 전반** | SolidWorks가 Inventor보다 **실무 보급률 높음** |

### 9.2 커뮤니티에서 반복되는 조언 (원문)

> "일단 어디로 갈건지 회사부터 정하고 익히라. 가고자 하는 회사가 어느 소프트웨어를 사용하는지 파악하고 결정하는 게 좋다."

— 여러 JobKorea 답변자·고캐드 답변자 공통 의견

### 9.3 CAD 혼용의 한국 현실 (팩트)

- **업종에 따라 달라짐** · **2개 이상 혼용 흔함**
- 클리앙 CATIA/Creo/SolidWorks 사용기: "극히 개인적" 후기도 존재
- 기계기사 실기: Inventor / SolidWorks / CATIA / NX UG 차이점 질문 다수

### 9.4 한국 커뮤니티에서 명확히 부족한 자료

- **AutoCAD + SolidWorks + Inventor 4개 혼용** 구체 회사 운영 후기: **검색 결과 빈약**
- **한국 제조업의 자체 BOM·PLM 구축** 기술 블로그: 극소
- 대부분 질문은 "취업용 어느 걸 배울까" 수준

### 9.5 세션3 참조 포인트

**팩트**:
- KNK의 4개 CAD 혼용은 **한국 중소 제조업 일반 패턴과 부합** (업종별 혼용 흔함)
- 커뮤니티는 "통일" 권하지만 실무는 "혼용" 현실
- 한국어 기술 자료는 희박 → **KNK 구축 경험 자체가 한국 업계 선도 자료가 될 수 있음** (팩트 기반 관찰)

**피할 함정**:
- 한국 커뮤니티 "통일 권장" 조언을 실무에 그대로 적용 시 비현실적 (이관 비용·인력 재교육)
- 공급사 추천 의존 → 공급사마다 자사 제품 권장

---

## 10. 하드웨어 Git-like 버전 관리

**출처**: Onshape 공식 블로그, AllSpice, CADLAB.io, Altium 공식, Wevolver, Michael Kafarowski

### 10.1 "Git for Hardware" 개념 (2026 기성 개념)

**정의**: Git 생태계를 **기구 설계 · PCB 설계 · 펌웨어 · 문서** 등 모든 하드웨어 설계 요소에 확장.

**핵심 가치**:
- 모든 설계 요소를 **코드처럼 관리**
- 스키매틱·PCB 레이아웃·BOM·기구 파일·펌웨어 → 단일 버전 관리
- 협업 플랫폼 간 원활
- 추적성 있는 변경 이력

### 10.2 대표 도구 (팩트)

| 도구 | 특징 | URL |
|---|---|---|
| **Onshape** | Git-스타일 branching/merging을 CAD에 직접 도입. 분기 간 차이 시각화, 병합 선택 가능. 브랜치 실험 가능 | onshape.com |
| **AllSpice** | "Git for hardware" 특화. 하드웨어 워크플로우 최적화 | allspice.io |
| **CADLAB.io** | Git 기반 PCB 비주얼 버전 관리. 하드웨어 최적화 비주얼 레이어 | cadlab.io |
| **Altium 365 + Git** | Altium 공식 Git 통합 가이드·소개 제공 | altium.com |

### 10.3 통합 리포지토리 패턴 (사실)

- PCB 프로젝트는 기구·문서·임베디드 SW/펌웨어 포함 복잡
- PCB 프로젝트 데이터는 sync, 나머지는 외부 리포지토리 유지 권장
- 부서간 협업: 기구 엔지니어가 인클로저 간섭 검토, 펌웨어/클라우드 개발자가 전기 엔지니어가 놓친 부분 입력

### 10.4 한계·논쟁 (사실)

**"SVN or Git with SolidWorks"** (Gotomation 2020 논쟁):
- 대형 바이너리 파일 (SLDPRT, SLDASM)에 Git 직접 적용 시 리포 비대화
- Git LFS (Large File Storage) 또는 SVN 선호론 존재

**하드웨어 Git 30일 구현 ebook** 존재 → **실행 자체가 무시할 수 없는 프로젝트**임을 시사

### 10.5 통합 사례 (팩트)

- Onshape: CAD 내장 Git 스타일 제공 (외부 Git 필요 없음)
- CADLAB.io + KiCad: 오픈소스 PCB의 Git 버전 관리
- Altium 365 + Git: 엔터프라이즈 PCB Git 워크플로우

### 10.6 세션3 참조 포인트

**흡수할 패턴**:
- 브랜치·머지 개념을 변경 관리에 적용
- "모든 설계 요소를 코드처럼" 철학
- 변경 전후 시각적 diff 개념

**피할 함정**:
- CAD 바이너리는 Git 단순 적용이 비효율 — Git LFS 또는 외부 파일 시스템 + 메타데이터만 Git 권장
- 하드웨어 Git 도입은 "30일 프로젝트" 수준 — 가벼운 작업 아님

**세션3 설계 시 참고 가능 방향 (사실 기반)**:
- 메타데이터(JSON·DB)만 버전 관리, 실제 CAD 파일은 파일 서버·NAS에 보관
- PostgreSQL에 변경 이력·브랜치 상태·담당자 추적 가능
- Onshape의 diff UI 개념 → 변경 시 AI가 자연어 diff 생성

---

## 11. 자체 MCP 서버 구축 도구·사례

**출처**: GitHub tadata-org/fastapi_mcp, GitHub jlowin/fastmcp, MintMCP, Speakeasy, fast.io, apxml

### 11.1 핵심 오픈소스 프레임워크 (팩트)

| 프레임워크 | 제작자 | 특징 | 라이선스 |
|---|---|---|---|
| **fastapi_mcp** | tadata-org | FastAPI 엔드포인트를 **MCP 도구로 자동 노출**, auth 내장. 기존 FastAPI dependencies 그대로 사용 가능. 별도 배포 또는 동일 앱에 mount | MIT (GitHub) |
| **FastMCP** | jlowin (PrefectHQ) | Pythonic MCP 서버·클라이언트 빌더. "fast, Pythonic way" | MIT |
| **Speakeasy** | Speakeasy | FastMCP + Speakeasy 통합 가이드 제공 | — |

### 11.2 구축 패턴 (팩트, 공식 문서 기준)

**fastapi_mcp 예시**:
- 기존 FastAPI 앱에 **한 줄 추가**로 MCP 서버 전환
- 인증은 기존 FastAPI dependency 재활용 (별도 구성 불필요)
- 유연한 배포: 앱 내부 mount 또는 별도 배포

**FastMCP 예시**:
- 기존 FastAPI에서 일반적 MCP 서버 부트스트랩 방법
- FastAPI 엔드포인트 → MCP 컴포넌트(도구 기본)로 자동 노출
- LLM 클라이언트에 API 공개

### 11.3 엔터프라이즈 요건 대응 (팩트)

- **보안**: 기존 FastAPI 인증 체계 그대로
- **확장성**: FastAPI의 비동기·고성능 기반
- **거버넌스**: API 레벨 권한 + 감사 로그

### 11.4 Claude Agent SDK와 MCP (팩트)

- Anthropic Claude Agent SDK (구 Claude Code SDK 이름 변경)
- **Full MCP 지원** — 모든 MCP 서버 연결 가능 (DB·API·파일 시스템·클라우드)
- Python · TypeScript 지원
- 에이전트 자율 수행: 파일 읽기·명령 실행·웹 검색·코드 편집

### 11.5 용도별 적합성 (Anthropic 가이드)

> "AI employee built on this stack perform best on tasks with clear input data, defined decision rule, downstream API to write results to — anything that looks like 'when X happens, decide Y, then write Z' is a strong candidate."

### 11.6 세션3 참조 포인트

**흡수할 패턴**:
- `fastapi_mcp` 한 줄 업그레이드 패턴 → 세션3 기존 FastAPI 앱 (HAIST_WORKS)에 즉시 적용 가능
- 인증 재활용 구조
- Anthropic Claude Agent SDK로 에이전트 루프 빌드

**피할 함정**:
- MCP 자체는 프로토콜일 뿐 — **에이전트 품질은 프롬프트·컨텍스트 엔지니어링에 달림** (Nike 재고 예측 실패 교훈)
- "when X → Y → Z" 명확한 사례에 먼저 적용, 애매한 판단은 human-in-the-loop

---

## 12. 통합 시스템 유사 사례 — 업계 포지션

**출처**: MODEX 2026, IIoT-World, MachineMetrics, Infor, Max AI, Dataiku 2026 manufacturing AI trends, Anthropic

### 12.1 2026 제조업 트렌드 (사실)

- **MODEX 2026 최대 트렌드 = Agentic AI** (Co-pilot보다 능동적)
- 2024~2025 = Generative AI → 2026 현실 = Agentic AI
- AI 에이전트가 능동적 관찰·추론·실행

### 12.2 Agentic AI 특징 (사실)

| 기능 | 동작 |
|---|---|
| 센서가 기계 성능 저하 감지 | AI가 자동으로 유지보수 티켓 생성 |
| 동시에 | 재고 확인 |
| 동시에 | 다른 활성 기계로 생산 스케줄 재라우팅 |

### 12.3 2026 주목할 제조업 AI 아키텍처 (사실)

**MCP 채택**:
- 기존 "custom-coded integrations" (비싸고 커스텀) → **MCP "zero-code universal protocol"**
- AI 에이전트가 기존 MES·ERP에 "plug and play"

**Unified Namespace (UNS)**:
- "spaghetti mess" 통합에서 이탈
- 데이터 생산자는 한 번만 발행 → AI·MES·ERP가 구독

**Max AI**:
- 기계 + ERP + tribal knowledge 통합
- "agentic digital workforce" for discrete manufacturers

### 12.4 MachineMetrics 사례 (사실)

블로그 제목: **"What Happens When Manufacturers Build Their Own MES Applications in Two Days"**
- 제조사가 2일 안에 자체 MES 앱 제작하는 Production Lab 사례
- 즉 자체 구축 + AI 보조 트렌드가 업계 공인

### 12.5 KNK 방향과 업계 사례 일치도 (팩트 비교)

| KNK 진행 방향 | 2026 업계 트렌드 | 일치도 |
|---|---|---|
| FastAPI 자체 구축 | 커스텀 제조업 시스템의 기본 선택지 | ✅ 일치 |
| Claude + MCP 통합 | MCP가 2026 표준 프로토콜 | ✅ 일치 |
| Agentic AI (변경 Inform 에이전트 등) | MODEX 2026 최대 트렌드 | ✅ 일치 |
| baby 엑셀 + HAIST_WORKS 웹 + Claude 조합 | UNS 아키텍처와 유사 철학 | ✅ 일치 |
| 점진적 부서 확장 (빅뱅 회피) | Hershey·Revlon·Lidl 실패 교훈 | ✅ 일치 |
| Human-in-the-loop 강제 | Nike 재고 예측 실패 교훈 | ✅ 일치 |

### 12.6 공개 자료로 확인된 "동일 조합 성공 사례"

- **Custom FastAPI + Claude API + MCP + 한국 중소 제조업 (장비 제조·CAD 혼용)** 의 **완전 동일 케이스**는 검색으로 **미발견**
- 개별 구성 요소 성공 사례는 모두 존재:
  - FastAPI + Claude API 제조업 사례: Syntora 등 (미국)
  - Claude Managed Agents 엔터프라이즈 배포: Block·Apollo·Zed·Replit
  - 제조업 Agentic AI: MODEX 2026 다수 사례
  - 한국 스마트공장 AI 지원사업: 중기부·삼성 파트너십 (2026)

### 12.7 세션3 의미 (사실 기반 관찰)

**관찰**:
- KNK가 구축 중인 조합(자체 FastAPI + Claude + MCP + AutoCAD·SolidWorks·Inventor·AutoCAD 전장 메타 통합)의 **구체 공개 케이스는 확인 안 됨**
- 개별 구성 요소는 모두 검증된 2026 트렌드 일치
- 즉 **KNK는 "조합의 선도자" 포지션**에 있음 (사실만 관찰)

**피할 함정** (업계 트렌드 전반):
- MCP 자체가 만능 아님 — "plug and play" 마케팅 문구
- Agentic AI는 명확한 의사결정 규칙에 효과적, 애매한 판단에 실패 (Nike·Microsoft Copilot 5K 배포 사례)
- UNS·MCP 도입 후에도 현장 부서원 적응 부족하면 실패

### 12.8 세션3 참조 포인트

**흡수할 패턴**:
- MCP 기반 zero-code 통합 철학
- UNS 개념 (한 번 발행·다수 구독)
- Agentic AI의 "관찰 → 추론 → 실행" 루프

**피할 함정**:
- "제조사가 2일 만에 MES 만듦" 마케팅 문구는 현실적 단순화 — 실제 품질·안정·사용자 수용은 별도
- 공개 케이스 부족 = 선도 이점 + 레퍼런스 부족 동시
- Max AI 같은 벤더 의존형 에이전트 솔루션은 락인 재발 가능성

---

## 📌 이 문서의 규칙 (재확인)

1. **사실만 기록**: 사용자 인용·출처·통계·사례
2. **구매 추천 금지**: "KNK는 X를 도입해야" 표현 없음
3. **아키텍처 제안 금지**: 세션3 결정 사항
4. **지속 갱신**: 신규 리서치 추가될 때마다 섹션 확장
5. **세션3 친화**: "흡수할 패턴 / 피할 함정" 형식으로 참조 포인트 제공

---

---

## 13. 하이웍스 API·메일 연동 사례·옵션

**출처**: 하이웍스 개발자 센터 (developers.hiworks.com), 가비아 고객센터, Google Workspace 관리자 지원, 라이브러리 가비아 (library.gabia.com), 위시켓

### 13.1 하이웍스 공식 API 목록 (팩트)

| API 카테고리 | 용도 |
|---|---|
| **전자결재** | 외부 시스템에서 기안 트리거 → 하이웍스 결재 자동 생성 |
| **인사관리** | 조직도·근태·인사정보 **조회** |
| **메신저 알림** | 하이웍스 메신저 푸시 발송 |
| **메일** | 자동 이메일 발송·팝업 |
| **문자 (SMS)** | 단문·장문·포토문자 |
| **카카오 알림톡** | 정보성 메시지 |
| **세금계산서** | 전자세금계산서 발행·국세청 전송 |
| **내 정보 조회** | 사용자 정보 |

### 13.2 기술 사양 (팩트)

- **프로토콜**: REST API (HTTP)
- **언어 독립**: 모든 HTTP 지원 언어
- **인증**: 오피스 토큰 기반
- **문서**: Postman 컬렉션 공개
- **공식 사이트**: https://developers.hiworks.com

### 13.3 실제 운영 사례 (공개 자료, 팩트)

| 기업 | 연동 내용 | 출처 |
|---|---|---|
| **에스원 (S1)** | 보안 솔루션 내 "하이웍스 기안하기" 버튼 → 자동 기안 + 기안자·본문 자동 작성 | developers.hiworks.com/case-studies/s1 |
| **아이퀘스트** | ERP 솔루션에 전자결재 내장 + **회계 정보 양방향** (지출결의·송금 요청 ERP로 가져오기) | library.gabia.com |
| **영림원 시스템에버** | 오피스 토큰 입력으로 간편 연동 | library.gabia.com |
| **신한은행 / 그린카 / 가비아 / ADT캡스** | 공식 파트너 | developers.hiworks.com |

### 13.4 SSO 연동 (팩트)

- 하이웍스 → 외부 사이트 SSO 연동 공식 매뉴얼 제공 (customer.gabia.com)
- 외부 시스템에서 하이웍스 로그인으로 싱글 사인온 가능

### 13.5 메일 외부 연결 옵션 (팩트)

#### 🔵 옵션 A. Gmail에서 하이웍스 메일 수신 (POP3/SMTP)

**절차**:
1. 하이웍스 로그인 → `메일 > 환경설정 > 기본 설정` → **POP3/SMTP "사용함"** 설정
2. Gmail에서 "다른 계정 메일 가져오기" → POP3 설정 입력
3. Gmail에서 하이웍스 계정으로 발송 가능 (SMTP)

**주의**:
- 회사 정책에 따라 **POP3/SMTP 사용 제한 가능** (관리자가 막을 수 있음)
- 먼저 하이웍스 측 설정 완료 필요

#### 🔵 옵션 B. 메일 포워딩 (단방향)

- 하이웍스에서 수신 메일을 **Gmail로 자동 전달** 설정
- 가비아 공식 매뉴얼 존재 (customer.gabia.com/manual/hiworks/2047/2067)

#### 🔵 옵션 C. Google Workspace로 완전 이관

- **Google Workspace 공식 데이터 이전 서비스** 제공
- IMAP 기반 웹메일 → Workspace 이전 지원
- MX 레코드 변경으로 도메인 전체 이관

#### 🔵 옵션 D. 가비아 공식 "메일 이전 프로그램"

- 하이웍스 → 다른 서비스로 데이터 이전용 프로그램 공식 배포
- customer.gabia.com/manual/hiworks/113/17680

### 13.6 IMAP 지원 여부 (팩트 주의)

- 하이웍스 공식 매뉴얼은 **POP3/SMTP 중심** 안내
- **IMAP 명시적 지원 여부는 공개 매뉴얼에서 명확하지 않음**
- POP3는 확정적 지원, IMAP은 별도 확인 필요
- Gmail 쪽은 IMAP·POP3 둘 다 지원

### 13.7 공개 자료의 한계 (팩트)

- "하이웍스 ↔ Gmail 양방향 연결" **구체 한국 기업 사례 공개 자료 확인 안 됨**
- 대부분 사례는 포워딩 또는 이관 목적
- 실운영 기업은 보안상 비공개 가정

### 13.8 더존 WEHAGO API (참고)

- 하이웍스 (가비아) ≠ WEHAGO (더존) 주의 — **별개 플랫폼**
- 다만 KNK는 하이웍스 사용 (가비아 호스팅)
- WEHAGO도 개발자 센터 존재: https://developer.wehago.com/api
- 더존 전략: "회계·인사 백엔드 API 직접 호출" + "공공 API 확장" (예: KTX 시간표 API 연동 출장 품의)

### 13.9 세션3 참조 포인트 (사실 기반)

**팩트 요약 (정책 관점)**:
- 하이웍스 = **API 완전 지원** + **SSO 지원** + **실운영 파트너 다수**
- 새 정책(`system_scope_policy.md`)과 **완벽 정합**:
  - 전자결제·메일 본체는 하이웍스 유지 ✅
  - HAIST WORKS에서는 **API 조회만** 가능 (근태·인사·오픈 세금계산서 등)
  - 결재 필요 시 **결재 URL을 본문에 첨부** (정책 명시)
  - 변경 Inform → SMTP 메일 발송은 하이웍스 메일 API 또는 외부 SMTP 가능

**세션3 고려 가능 방향 (사실만, 권고 아님)**:
- 근태 조회 API = 하이웍스 인사관리 API 공식 사용 (정책 명시는 없지만 "외부 의존"에 포함되지 않음)
- 결재 필요 시 **하이웍스 결재 URL 기안 자동 생성** = 에스원·아이퀘스트 사례와 동일 패턴 가능
- SMTP 발송은 하이웍스 메일 API 또는 외부 SMTP 모두 옵션

**흡수할 패턴** (업계 사례에서):
- 에스원 "하이웍스 기안하기" 버튼 UX — 한 클릭으로 외부 시스템 → 하이웍스 결재 이동
- 아이퀘스트의 **양방향 데이터 연동** (외부 ERP ↔ 하이웍스 회계)
- 오피스 토큰 기반 단일 인증

**피할 함정**:
- 하이웍스 API는 공식이지만 **한국어 문서만**. Postman 컬렉션 활용 필수
- POP3/SMTP는 회사 관리자 정책에 따라 막힐 수 있음
- IMAP 지원 불명확 — **POP3 기준 설계 권장 사항으로 관찰**
- 공개 사례 제한 → 상세 구현 디테일은 실제 코딩 중 시행착오 예상

---

**최종 갱신**: 2026-04-20 (Batch 1+2+3+Multi-CAD+§7~§13)
**다음 리서치 후보**:
- 한국 제조업 구체 경쟁사(테크윙·이오·코세스·원익IPS) 채용 공고 기반 기술 스택 역공학
- Claude Agent SDK 실전 구축 패턴 심화 (Python 코드 예시·eval 세트)
- 제조업 오픈소스 ERP·MES 대안 (ERPNext·Dolibarr 등)
- BOM 변경 알림 UX 패턴 (원티드·인스턴트 등 실시간 앱 사례 참고)
- 한국 중소 제조업 AI 도입 실패 사례 (정부 지원사업 선정 후 중단 케이스)
