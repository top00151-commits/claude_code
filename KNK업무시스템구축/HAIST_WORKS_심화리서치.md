# HAIST WORKS 심화 리서치 — KNK 통합 업무 시스템 + AI 로드맵

> **목적**: 두 작업 세션(HAIST_WORKS 웹 / HAIST_WORKS_baby 엑셀)이 이 한 문서만 읽고 "어떤 도구를 흡수·대체·통합할지", "AI를 어떻게 접목할지", "어떤 순서로 만들지"를 근거 있게 결정할 수 있게 하는 단일 진실 소스.
>
> **작성**: 2026-04-20, HAIST_WORKS_Research 세션 빅터 (Claude / Anthropic)
> **저장 위치**: `C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\HAIST_WORKS_심화리서치.md`
> **다음 세션 로드**: `@KNK업무시스템구축/HAIST_WORKS_심화리서치.md`
> **상위 문서**:
> - `HAIST_WORKS_설문요약.md` (274줄, 12부서 설문 압축)
> - `HAIST_WORKS_설문분석.md` (1039줄, 부서별 응답 원문)
> - `HAIST_WORKS_종합설계분석.md` (493줄, baby↔web 통합 청사진)
> **사용 방식**:
> 1. 새 세션 시작 시 먼저 이 문서를 로드
> 2. 본인이 작업할 영역의 "KNK 적합도" 판정 확인
> 3. "구현 권고" 섹션의 구체 지침대로 즉시 착수
>
> **리서치 규모**: 18회 외부 웹 검색 (한국·영어 병행, 2025Q4~2026Q1 자료 중심) + 설문 12부서 응답 교차 참조

---

## 📋 목차

1. [Executive Summary — 5분 결정용](#1-executive-summary)
2. [KNK 현 상태 스냅샷](#2-knk-현-상태-스냅샷)
3. [5대 설계 원칙 (절대 원칙)](#3-5대-설계-원칙)
4. [도구 10종 심화 분석](#4-도구-10종-심화-분석)
5. [AI 2026 트렌드 심화](#5-ai-2026-트렌드-심화)
6. [제조업 AI 성공·실패 사례](#6-제조업-ai-성공실패-사례)
7. [한국 SME 제조업 현실](#7-한국-sme-제조업-현실)
8. [반도체 검사기·자동화 동종업계 인사이트](#8-반도체-검사기자동화-동종업계-인사이트)
9. [Build vs Buy — KNK 결론](#9-build-vs-buy-knk-결론)
10. [KNK 적합도 매트릭스](#10-knk-적합도-매트릭스)
11. [KNK 통합 아키텍처 (FastAPI + Claude + MCP)](#11-knk-통합-아키텍처)
12. [8주 단기 로드맵](#12-8주-단기-로드맵)
13. [6개월 중기 로드맵 + 1년 장기](#13-6개월-중기-로드맵--1년-장기)
14. [위험 회피 체크리스트](#14-위험-회피-체크리스트)
15. [세션별 다음 액션](#15-세션별-다음-액션)
16. [부록: 리서치 소스 인덱스](#부록-리서치-소스-인덱스)

---

<a id="1-executive-summary"></a>
## 1. Executive Summary — 5분 결정용

### 1.1 한 문장 결론

> **KNK에 맞는 정답은 "하이브리드 자체 구축 + 선택적 SaaS 연동 + Claude AI 에이전트 레이어"다. 패키지 ERP 전면 도입은 73% 실패 확률이고, 풀 SaaS(Notion/Monday 만으로 운영)는 5천행 벽·이중 입력 문제로 KNK 규모(140명·관리코드 450+)에 부적합하다.**

### 1.2 3가지 핵심 발견

| # | 발견 | 근거 | 시사점 |
|---|---|---|---|
| 1 | **설문 1·2순위(진행률·변경 Inform·요청 티켓)는 상용 도구로 80% 해결 가능하지만 Excel/ERP 이중 입력이 발생** | 구매·관리팀 설문 + Notion 제조업 사례(15~20분/주문 수작업) | 기존 도구(WEHAGO 하이웍스·KNK PMS·카톡)를 **유지하면서** 그 위에 얇은 통합 레이어(`HAIST WORKS`)를 깔아야 함 |
| 2 | **AI 2026 트렌드 = Agentic (자율 에이전트) + MCP (데이터 연결 표준)**. Microsoft는 이미 "제품 변경 관리 에이전트" 상용화 — 승인 기간 몇 주→며칠, BOM 종속성 누락 80% 감소 | Microsoft Industry Blog 2025.12 · Anthropic Managed Agents 2026.01 · MODEX 2026 | **설문 1순위 ②(변경 Inform)는 AI 에이전트의 가장 적합한 적용 영역**. KNK의 제조2 사고(변경 통보 누락)를 정확히 해결 |
| 3 | **KNK의 `baby`(엑셀) + `web`(FastAPI)은 이미 2026 모범 패턴과 정확히 일치** — FastAPI로 12개 마이크로서비스, Claude API로 PDF→구조화 데이터, 제조업 맞춤 ERP는 "20영업일 안에 1주차 결과" 가능 | FastAPI 2026 production guide · Syntora Claude manufacturing | **지금 방향이 맞다**. 상용 ERP로 갈아타는 건 비용·위험·KNK 표준(관리코드 8자리 `001T2604`) 손실 측면에서 불합리 |

### 1.3 의사결정 매트릭스 (즉시 답)

| 질문 | 답 | 근거 요약 |
|---|---|---|
| **SAP B1 / Odoo / 더존으로 전면 교체?** | ❌ 하지 마라 | SAP SME 실패율 73%, Lidl $500M 손실, Revlon 공장 중단. KNK 규모로는 과잉 투자 |
| **Notion만으로 통합?** | ❌ 불가능 | 10,000행 성능 저하, 복잡 자동화 한계, 관리코드 450+ 수용 불안 |
| **Airtable + Monday 조합으로 대체?** | 🟡 부분 | Airtable 50K 레코드 한도, 한국 세관·WEHAGO·하이웍스 연동 부재 |
| **MRPeasy / OpenBOM 구매?** | 🟡 검토 가치 있음 | 4·5단계 입고·재고 + BOM 영역만 한정 도입 가능. 단 $79/user 비용 |
| **Claude Managed Agents / MCP 도입?** | ✅ **즉시 도입 권장** | 설문 1순위 ②(변경 Inform)에 정확히 매칭. 비용은 API 사용량만 (사용자당 월 $10~30 예상) |
| **AI 시대에 자체 구축이 맞나?** | ✅ **지금이 최적기** | Claude API로 20영업일 안에 커스텀 ERP 가능, 공공 스마트공장 지원사업(최대 3억원·75%)도 활용 가능 |

### 1.4 첫 3개월 실행 요약

```
[Month 1 — 4월]
  ★ 변경 Inform + AI 영향 판단 (MCP로 baby 엑셀 + web DB 연결)
  ★ baby V2 영업 보완 마무리 (수금·매출예측·KNKVN)

[Month 2 — 5월]
  ★ 요청 티켓 (카톡 보조) + 진행률 대시보드 모바일
  ★ AI 에이전트 레이어 골격 (Claude API + RAG BOM 검색)

[Month 3 — 6월]
  ★ 도면 버전 관리 + 이슈/AS DB + 근태 조회
  ★ 스마트공장 AI 지원사업 신청 (6월 선정)
```

**예상 효과**: 10팀 공통 고통 해결 + 제조2 사고 재발 방지 + 영업팀 매출 가시화. **총 투자**: 내부 시간 12주 + API 비용 월 ~$2K.

---

<a id="2-knk-현-상태-스냅샷"></a>
## 2. KNK 현 상태 스냅샷

### 2.1 조직·규모

| 항목 | 수치 |
|---|---|
| 본사 인원 | ~80명 |
| 베트남법인(KNKVN) | ~60명 |
| **합계** | **140명** |
| 부서 수 | 13개 (12개 응답, 베트남 미회신) |
| 사업부 | 검사기(T) · 자동화(M) 2개 + 소모품 |
| 관리코드 누적 | **450+** (KNK PMS 8자리 표준 `001T2604`) |
| 실데이터 사용자 | 83명 시드 완료 (web DB) |

### 2.2 기존 시스템 스택

| 시스템 | 역할 | 상태 |
|---|---|---|
| **KNK PMS v3** (엑셀+Python) | 31시트, 부서입력 15파일, sync_v2.py 2384줄 | 운영 중 (데이터 입력의 단일 진실) |
| **KNK 데일리허브 v2** (`knk_v2`) | FastAPI + SQLite + i18n 3언어 | 140명 사용 중 (8080포트) |
| **HAIST_WORKS 웹** | FastAPI + SQLite, 8커밋 ~17,000줄 | 구축 중 (8081포트) |
| **HAIST_WORKS_baby** | 엑셀 V1·V2 (영업 중심 재설계) | V1 완료, V2 진행 중 |
| **카카오톡** | 일상 커뮤니케이션 | 전사 사용 (대체 불가) |
| **WEHAGO/하이웍스** | 근태·전자결재·급여 | 운영 중 (파트너 API 존재) |
| **Altium / SolidWorks** | 회로·기구 CAD | 설계팀 사용 |
| **Git** | SW팀 코드 저장소 | SW팀 사용 |

### 2.3 설문 12부서 — 전사 공통 고통 TOP 5

| 순위 | 고통 | 언급 부서 수 | 사고 사례 |
|---|---|---|---|
| 1 | 카톡·구두 요청 기록 누락 | 10팀 | 출고 누락 월 2~3회 |
| 2 | 진행률 통합 대시보드 부재 | 8팀 | 매일 아침 15분 일정 미팅 |
| 3 | 상류→하류 변경 Inform 지연 | 6팀 | **제조2 실사고 — 잘못된 도면 가공** |
| 4 | 핵심 파일 팀장 PC | 5팀 | 부재 시 업무 마비 |
| 5 | 도면 버전 관리 부재 | 5팀 | **제조2 — 30일 link 만료로 작업 중단** |

---

<a id="3-5대-설계-원칙"></a>
## 3. 5대 설계 원칙 (절대 원칙)

설문 + 리서치 결과 통합으로 정립한 **KNK 시스템의 절대 원칙**. 어떤 도구·AI를 도입하든 이 5개를 위반하면 실패.

### 원칙 1. 이중 입력 금지 (No Double Data Entry)

**근거**:
- 구매(정성진): "수불 ERP·엑셀 이중 입력"
- 관리(박지은): "데이터 구조 통합·업무 기준 강제화 후 자동화 → 차츰 확대"
- Notion 제조업 실패 사례: "15~20분/주문 × 30~40주문/주 = 주 8~10시간 수작업"
- SAP 실패 통계 2025: "poor data migration"이 실패 원인 Top 3

**적용**:
- 데이터 소유자(owner) = 단 하나의 시스템
- 다른 시스템은 read-only로 참조만
- 예: 관리코드 → baby 엑셀이 owner, web은 import만

### 원칙 2. 기존 도구 연동 우선 (Integrate, Don't Replace)

**근거**:
- 설문: Git·Altium·SolidWorks·WEHAGO·카톡 모두 교체 요구 0건
- 구매(정성진): "카톡 출고 요청 기록" — 카톡 대체가 아니라 티켓화
- 2026 MCP 트렌드: "Claude now has directory with 75+ connectors" — 연동이 표준
- BOM-ERP 통합 연구: "common database를 통한 중복 제거"

**적용**:
- CAD 도구 메타데이터만 수집 (파일 변경 시 BOM 자동 감지)
- Git commit 메타데이터만 수집 (SW 표준 라이브러리 탐색)
- 카톡은 그대로, 중요 요청만 티켓 변환

### 원칙 3. 카톡 대체 아닌 보조 (Chat Augmentation, Not Replacement)

**근거**:
- 카카오톡 한국 M/S 90%, 전사 표준 커뮤니케이션 도구
- Kakao Work / Slack 모두 한국 제조업 도입률 미미
- Zendesk 연동 사례: "Support teams collaborate behind the scenes on tickets while messaging continues"
- n8n KakaoTalk API: Kakao Send-to-Me API로 알림 자동화 가능

**적용**:
- 카톡에서 "!티켓 자재요청 [내용]" → 웹 티켓 자동 생성
- 웹 티켓 상태 변경 → 카톡 요청자에게 푸시
- 일상 잡담은 그대로 카톡

### 원칙 4. 읽기 자동, 쓰기 최소 (Auto-Read, Minimal-Write)

**근거**:
- SW팀(이한중): "일을 위한 일 최소화"
- 전장(김형렬): "현업 부담 최소화 방향 설계"
- Microsoft Copilot 사례: "cut approval times from weeks to days"
- 제조업 대시보드 모범사례: "user-specific, 역할별 뷰 자동 생성"

**적용**:
- 대시보드는 baby 엑셀 자동 import (1일 1회) + 실시간 WebSocket
- 상태 변경은 1~2 클릭 (모바일 친화)
- 질문은 AI 에이전트에게 자연어로 (RAG)

### 원칙 5. 시스템 정체 설명 가능 (Explainable System)

**근거**:
- 가공팀(윤영조): "시스템 정체를 이해할 수 있게 설명 필요"
- 변경 관리 연구 (Hershey 실패): "inadequate change management가 실패 원인 1위"
- 디지털 트랜스포메이션 독일 SME 연구: "employee satisfaction이 ROI 지표 중 하나"

**적용**:
- 부서별 사용 가이드 `.md` 작성 (스크린샷 포함)
- 모든 자동화 규칙은 UI에 "왜 이렇게 되었나" 노출
- "이 변경이 누구에게 영향?" = AI 설명 버튼

---

<a id="4-도구-10종-심화-분석"></a>
## 4. 도구 10종 심화 분석

각 도구마다 **강점 · 한계 · KNK 적합도 · 흡수할 기능**을 정리. 적합도는 ⭐⭐⭐⭐⭐ (핵심 채택) / ⭐⭐⭐⭐ (선택적) / ⭐⭐⭐ (참고) / ⭐⭐ (부분 기능만) / ⭐ (부적합).

### 4.1 Notion — ⭐⭐⭐ (참고용·제한적)

**강점**:
- 위키·노트·데이터베이스 올인원, 무료 티어 강함
- Notion AI (GPT-5/Claude Opus/o3 내장, Business plan 포함)
- Notion 3.0 에이전트 — DB 변화 감지·응답 초안·페이지 업데이트 자동화
- 한국어 번역 품질 우수

**한계 (KNK 규모에서 치명적)**:
- **데이터베이스 성능 저하**: 수천 행 넘으면 느려짐, 10,000행에서 눈에 띄게 지연 — KNK 관리코드 450+ + 부품 수천개면 한계 도달
- **자동화 한계**: 복잡 워크플로우는 Zapier/Make 의존 필수
- **Workers (AI 에이전트 코드 실행)**: 30초 타임아웃 + 128MB 메모리 + 도메인 화이트리스트만 허용 + Enterprise plan 전용
- **Airtable 대비 자동화 오류율 23% vs 8%** (실측)
- **제조업 실패 사례**: "purchase order → production task 자동 생성 못 해 15~20분/주문 수작업"

**KNK 적합도 판정**: ⭐⭐⭐
- **도입 영역**: 위키 · 사용자 가이드 · 회의록 · SOP 문서 (데이터 아닌 텍스트)
- **절대 하지 말 것**: 관리코드 마스터, BOM, 발주, 진척
- **Notion AI의 Q&A 기능**: KNK 자체 구축한 RAG로 대체 가능 (Claude API + pgvector)

**흡수할 기능 (KNK 자체 구축 시 참고)**:
- 페이지 사이드바 네비게이션 패턴
- 인라인 데이터베이스 링크 방식
- `@` 멘션·태그 시스템
- 체크리스트 · 토글 UI 패턴

### 4.2 Airtable — ⭐⭐⭐⭐ (선택적 채택 가치)

**강점**:
- 관계형 DB + 스프레드시트 UI 하이브리드
- 자동화 오류율 8% (Notion 대비 1/3)
- API 응답 2~3배 빠름 (Zapier/Make 연동 우수)
- **AI 필드** — 자동 카테고리, 감성 분석, 요약, 콘텐츠 생성 (자동 트리거)
- 50,000 레코드/base (유료), Enterprise 500K — **KNK 규모 수용 가능**
- 명확한 rate limit 공개 → 용량 계획 예측 가능

**한계**:
- **가격 비쌈**: $20/seat/월 = Monday.com $9 대비 2배
- 한국어 UI는 있으나 어색한 번역
- 한국 세관·WEHAGO·하이웍스 연동 부재
- 오프라인 접근 불가 (클라우드 전용)

**KNK 적합도 판정**: ⭐⭐⭐⭐
- **도입 영역 후보**:
  1. **이슈·AS DB** (3순위 ⑦) — 고객사·모델·증상·처리 구조화
  2. **증빙 제출 포털** (3순위 ⑩) — 사진 업로드 + 자동 분류
  3. **표준 Library 인덱스** (3순위 ⑨) — SW팀 코드 스니펫 메타데이터
- **절대 하지 말 것**: 관리코드 마스터 (baby 엑셀이 owner), 발주, BOM
- **대안**: 자체 FastAPI로 구현하면 Airtable의 80%를 $0로 가능

**흡수할 기능**:
- Grid / Kanban / Gallery / Calendar 뷰 전환 UI
- 필드 타입 (Linked record · Lookup · Rollup · Formula)
- AI 필드 개념 (자동 카테고리·요약)

### 4.3 Monday.com — ⭐⭐⭐ (UX 참고)

**강점**:
- 시각적 프로젝트 관리, 보드 기반
- 색상·상태 커스터마이징 직관적
- 상대적으로 저렴 ($9/seat/월)
- 한국 레퍼런스 존재 (스타트업 중심)

**한계**:
- 관계형 데이터 모델 약함 (Airtable 대비)
- 복잡한 자동화·조건부 로직 제한
- Airtable의 추론 능력 부재
- 이중 라이선스(Monday+Airtable 병행) 사례 많음 → $660/월 비효율

**KNK 적합도 판정**: ⭐⭐⭐
- **도입 영역**: 단기 프로젝트 관리 (신제품 개발·M&A 대응 등 임시 이슈)
- **절대 하지 말 것**: 상시 운영 시스템 대체
- **대안**: Monday의 시각적 보드 UI만 흡수하여 자체 구현

**흡수할 기능**:
- 상태별 색상 뱃지 + 드래그 앤 드롭
- 자동 알림 (@멘션·상태 변경)
- 타임라인 + 간트 차트 뷰
- 주간 업무 보고 요약 자동 생성

### 4.4 MRPeasy — ⭐⭐⭐⭐ (입고·재고 한정 검토)

**강점 (검증된 실적)**:
- **실제 SME 성공 사례**:
  - 영국 Motion Impossible — 외부 컨설턴트 없이 자체 구축
  - Vanquish Hardware — 도입 후 매출 25% 상승, 직원 1~2명만 추가
  - 익명 고객 — 재고비 20% 감소 · 10개월 내 40% 성장
- SME 타겟 ERP 중 문서·비디오 튜토리얼 품질 1등급
- **BOM · MRP · PO · 재고 · 작업지시서 통합** (KNK 4·5단계 입고/재고 완벽 커버)

**한계**:
- **비쌈**: $79/user/월 (Odoo $24 · SAP B1 $149 중간)
- 한국어 지원 제한
- 카톡·WEHAGO 연동 부재
- KNK 표준 관리코드(`001T2604`) 강제화 어려움 (MRPeasy 내부 코드 체계 존재)

**KNK 적합도 판정**: ⭐⭐⭐⭐ (한정 영역)
- **도입 영역 후보**: 4·5단계 입고/재고 — **단, KNK PMS 관리코드를 MRPeasy 외부코드로 매핑**
- **절대 하지 말 것**: 전체 ERP 대체 (baby 엑셀 포기 불가)
- **의사결정**: 
  - 5명 구매팀 × $79 × 12월 = **연 $4,740** (~700만원)
  - 자체 구축 대비 ROI 판단: **자체가 낫다** (baby 이미 60% 커버 + web 확장이 더 유연)

**흡수할 기능**:
- BOM 계층 트리 UI (다중 레벨)
- MRP 제안 알고리즘 (수요→발주 자동 제안)
- 작업지시서(Work Order) 상태 흐름
- 재고 로트 추적 (lot tracking)

### 4.5 OpenBOM — ⭐⭐⭐⭐ (BOM 통합 강력 후보)

**강점**:
- 클라우드 PLM — 실시간 BOM 업데이트 · 공급망 관리 · 구매 계획
- **가격 우수**: $25/user/월 (Aras $0 코어 + 유료 옵션보다 저렴·간단)
- G2 사용자 만족도 84점 / 723 리뷰 — 중소기업 채택률 77%
- CAD 통합 우수 (SolidWorks · Fusion · Inventor · Altium)
- "마이크로 팀의 스프레드시트 지옥 탈출"로 평가됨

**한계**:
- **Full PLM 아님** — 설계 승인 워크플로우 단순
- 한국어 UI 제한적
- Aras 대비 커스터마이징 깊이 부족 (analyst rating 72 vs Aras 92)

**KNK 적합도 판정**: ⭐⭐⭐⭐
- **도입 영역 후보**: 
  1. BOM 통합 마스터 (3순위 ⑥) — 설계+전장+수불 단일 출처
  2. Altium/SolidWorks → BOM 자동 동기화
  3. 공급업체 가격 관리 통합
- **의사결정**:
  - 설계·전장·구매·SW 15명 × $25 × 12월 = **연 $4,500** (~650만원)
  - baby 엑셀 BOM 시트와의 병행 운영 가능 (OpenBOM이 source, baby가 요약)
  - **도입 권장 단, baby V2와 API 연동 필수**

**흡수할 기능**:
- BOM 다중 레벨 전개 (Single-level / Multi-level)
- 공급업체 가격 이력 (3개 견적 비교)
- CAD 변경 → BOM 자동 감지

### 4.6 Aras Innovator — ⭐⭐ (KNK에는 과한 도구)

**강점**:
- 대기업급 PLM — 디지털 스레드 (as-designed → as-manufactured → as-maintained)
- low-code 아키텍처 — 매우 깊은 커스터마이징
- 코어 기능 무료 (파트너 유지보수 유료)
- 대형 OEM 자동차·항공 레퍼런스 다수

**한계**:
- **KNK 규모에는 오버킬** — 중대형 기업 대상
- 파트너 구축 비용 수억원 예상
- 한국 파트너 제한적
- 내부 인력 학습 곡선 6개월+

**KNK 적합도 판정**: ⭐⭐
- **도입 영역**: 없음 (현재 규모)
- **재검토 시점**: 직원 300명+, 연매출 500억+ 도달 시

**흡수할 기능**: 없음 (참고용)

### 4.7 SOLIDWORKS PDM — ⭐⭐⭐⭐ (도면 버전 관리 1순위 후보)

**강점**:
- **싱글 사이트 소형 회사에 특화** — KNK 본사 완벽 매칭
- check-in/check-out · reference 관리 · 상태 기반 권한
- SolidWorks와 native 통합 — 설계자 학습 곡선 0
- 제조2 실사고(30일 link 만료) 정확히 해결

**한계**:
- SolidWorks 전용 (Altium은 별도)
- 라이선스 비용 있음 (Standard ~$1,500/user 1회)
- 한국어 UI 제한

**KNK 적합도 판정**: ⭐⭐⭐⭐ (설계·전장 한정)
- **도입 영역**: 도면 버전 관리 (3순위 ⑧ → **격상 검토**, 제조2 사고 방지)
- **의사결정**:
  - 설계 5명 × ~$1,500 1회 = **~1천만원**
  - 자체 구축 시 파일 NAS + web 메타데이터 DB로 구축 가능
  - **하이브리드 권장**: SolidWorks PDM (설계팀만) + web 메타데이터 (전사 조회)

**흡수할 기능**:
- 리비전 상태(In Work → Approved → Released)
- Where Used 추적
- 30일 link 만료 → 영구 링크로 전환

### 4.8 Slack / Kakao Work — ⭐⭐ (카톡 대체 불가)

**Slack 강점**:
- 글로벌 표준, 1000+ 앱 통합
- Slack AI — 스레드 요약, 검색
- 티켓 연동 탁월 (Zendesk 공식 통합)

**Kakao Work 강점**:
- 카카오톡 UI 계승 — 한국인 친숙도 최고
- 한국 보안·암호화
- 조직도 내장

**공통 한계 (KNK 관점)**:
- **카톡 이미 쓰는데 중복** — 전사 전환 저항 예상
- Slack은 해외 툴 (관리팀 우려)
- Kakao Work도 별도 ID 발급 필요 (카톡과 다른 앱)
- 설문에서 어느 부서도 요청하지 않음

**KNK 적합도 판정**: ⭐⭐
- **결론**: **도입 불필요** — 카톡 + 웹 티켓 시스템으로 대체
- **대안**: n8n + Kakao Send-to-Me API로 카톡 알림 발송

**흡수할 기능**:
- Slack의 채널·스레드 구조 → 웹 티켓 코멘트 구조
- Slack의 `/command` 단축 → 웹 검색 UI
- Zendesk-Slack 통합 흐름 → 카톡-HAIST WORKS 통합

### 4.9 SAP Business One / Odoo — 한국 ERP 대안 ⭐⭐

**SAP Business One** ($149/user/월):
- **강점**: MRP · 재고 · 공급망 완비, 재무 안정
- **한계**: 설정 어려움, 화면 복잡, UI 옛스러움, 맞춤화 제한
- **한국 실패 사례 (글로벌)**: Hershey($112M 손실), Haribo(재고 추적 중단), Lidl($500M 포기), Revlon(공장 가동 중단)

**Odoo** ($24/user/월):
- **강점**: 모듈화, 오픈소스 커뮤니티, 저렴
- **한계**: 모듈 조합에 따라 파편화, 공식 지원 제한

**더존 / 영림원** (한국):
- **더존 ERP**: 중소기업 1위, 전국 지원망 — 단 스마트A 2023.12 단종, 2025년 말 유지보수 종료
- **영림원 K-System Ace**: 제조·건설 특화 커스터마이징 깊이 우수

**KNK 적합도 판정**: ⭐⭐ (재무·급여만 WEHAGO로 기존 운영)
- **결론**: **전면 도입 금지** — 73% 실패 확률 + 관리코드 표준 손실
- **활용 방식**: WEHAGO/하이웍스는 근태·전자결재·급여 영역으로 **유지**, 나머지는 KNK 자체 시스템

**흡수할 기능**:
- Odoo의 모듈화 개념 (web 사이드바 모듈 구조)
- SAP의 MRP 계획 알고리즘 (재주문점 · 안전재고)

### 4.10 WEHAGO / 하이웍스 (더존) — ⭐⭐⭐⭐⭐ (필수 유지)

**강점 (KNK에게 완벽)**:
- **한국 기업용 그룹웨어 M/S 1위**
- 근태·전자결재·급여·지출결의 완비
- **파트너 API 공식 제공** — HTTP REST
- 파트너 솔루션 근태·출입 연동 가능
- 전자결재 + 전표 처리 자동화 (더존 DNA)

**한계**:
- 사용자 경험 구식
- 모바일 UI 한계
- 프로젝트 관리·BOM·PLM 영역 없음

**KNK 적합도 판정**: ⭐⭐⭐⭐⭐ (이미 도입·필수 유지)
- **도입 영역**: 근태·전자결재·급여·지출 — **절대 대체 금지**
- **HAIST_WORKS와 연동 방식**:
  1. 하이웍스 근태 API → HAIST_WORKS 대시보드 "오늘 휴가·출장" 표시
  2. 증빙 제출 포털 → 전자결재 자동 생성
  3. 인사 변동 → HAIST_WORKS 사용자 자동 동기화

**흡수할 기능**: 없음 (그대로 사용)

---

### 4.11 도구 10종 종합 비교표

| 도구 | 월 비용(1인) | KNK 적합 영역 | 도입 판정 |
|---|---|---|---|
| Notion | Free~$18 | 위키·SOP | 🟡 부분 도입 (텍스트만) |
| Airtable | $20 | 이슈DB·증빙 | 🟢 자체 구축 대체 가능 |
| Monday.com | $9 | 단기 프로젝트 | 🔴 불필요 |
| MRPeasy | $79 | 입고·재고 후보 | 🟡 자체 구축 비교 필요 |
| OpenBOM | $25 | BOM 통합 | 🟢 **도입 검토** (연 650만) |
| Aras Innovator | 파트너 | — | 🔴 오버킬 |
| SolidWorks PDM | ~$1.5K 1회 | 도면 버전 | 🟢 **도입 검토** (설계 5명) |
| Slack/Kakao Work | $7~13 | — | 🔴 불필요 (카톡 유지) |
| SAP B1/Odoo | $24~149 | — | 🔴 과도한 교체 |
| WEHAGO/하이웍스 | 기존 | 근태·전자결재 | 🟢 **필수 유지** |

**권고 결론**:
- **신규 구매**: OpenBOM (BOM), SolidWorks PDM (도면 — 선택)
- **기존 유지**: WEHAGO/하이웍스
- **자체 구축**: 나머지 전부 — FastAPI + Claude API

---

<a id="5-ai-2026-트렌드-심화"></a>
## 5. AI 2026 트렌드 심화

### 5.1 Agentic AI (자율 에이전트) — 2026 최대 트렌드

**시장 현황**:
- 2026 agentic AI 엔터프라이즈 시장: **$9B** (예상), 파일럿→프로덕션 전환 급가속
- MODEX 2026 핵심 트렌드: "agentic AI가 자동으로 유지보수 티켓·재고 확인·스케줄 재조정"
- PwC × Anthropic 파트너십: 생명과학·금융 에이전트 배포
- Accenture × Anthropic: 다년 파트너십 (규제 산업 에이전트)

**핵심 기술 스택**:
1. **Claude Managed Agents** (Anthropic, 2026.01 Public Beta) — 인프라 추상화, 10배 속도, 샌드박스·인증 처리
2. **Microsoft Agent Framework** (2025.10 AutoGen+Semantic Kernel 통합) — 2026Q1 GA
3. **LangGraph** — 장기 실행 워크플로우, 감사 가능, 오류 복구
4. **CrewAI** — 역할 기반 협업 에이전트 (manager, coder, reviewer)
5. **Claude Cowork** (2026.01.12) — 로컬 자율 에이전트, 문서 처리·다단계 워크플로우

**KNK 적용 가능성**:
- **변경 Inform 에이전트**: 변경 등록 → BOM 종속성 자동 분석 → 영향 부서 자동 알림 (설문 1순위 ② 정확히 매칭)
- **일일 요약 에이전트**: 매일 아침 8시 자동 요약 (이슈·지연·진행) — 대표/팀장용
- **티켓 분류 에이전트**: 카톡 메시지 → 카테고리 분류 → 담당 부서 할당
- **문서 검색 에이전트** (RAG): "이 증상 이전에 겪은 적 있나?" → 이슈 DB 자동 검색

### 5.2 MCP (Model Context Protocol) — AI와 기업 데이터 연결 표준

**MCP란?**
- 2024년 Anthropic 발표 → 2025 오픈소스 공개 → 2026 Agentic AI Foundation 이관
- **AI가 기업 데이터·도구와 표준 방식으로 대화하는 프로토콜**
- 예: MCP 서버 = KNK의 baby 엑셀·web DB·Altium → Claude가 직접 읽고 분석

**2026 현황**:
- AWS, Cloudflare, Google Cloud, Azure 모두 MCP 배포 지원
- Anthropic 디렉터리 75+ 커넥터
- 초기 채택자: Block, Apollo, Zed, Replit, Codeium, Sourcegraph

**엔터프라이즈 요구사항**:
- 중앙화 인증 (로컬 MCP로는 부족)
- 감사 추적(audit trail) 필수
- 거버넌스·샌드박스 실행·credential management

**KNK MCP 설계**:
```
┌─────────────────────────────────────────────────────┐
│  Claude (Opus 4.7 1M context)                       │
│      ↕ MCP                                          │
├─────────────────────────────────────────────────────┤
│ MCP Servers (KNK 자체 구축)                         │
│  1. knk-pms-mcp    → baby 엑셀 read-only            │
│  2. knk-web-mcp    → web DB (projects, tickets, ..) │
│  3. knk-cad-mcp    → Altium/SolidWorks metadata    │
│  4. knk-git-mcp   → SW팀 Git 메타데이터             │
│  5. knk-hiworks-mcp → WEHAGO/하이웍스 근태          │
└─────────────────────────────────────────────────────┘
```

### 5.3 RAG (Retrieval-Augmented Generation) for Manufacturing

**2026 RAG 트렌드**:
- "2026~2030년 모든 엔터프라이즈가 지식 집약적 — 제조·물류·소매·호스피탈리티"
- **Document GraphRAG**: 지식 그래프 + 벡터 임베딩 조합 (제조업 문서 구조 살림)
- 세 가지 지식 표현 공존: 벡터 임베딩 + 지식 그래프 + 계층 인덱스

**제조업 RAG 활용 사례**:
- "이 품질 문제 이전 보고서·사진 자동 검색"
- "메인 드라이브 토크 스펙이 뭐지?" → 사양서 + 분해도 동시 제시
- BOM 기반 "이 부품 어디에 쓰이나" 자동 답변

**KNK RAG 설계**:
- **임베딩 데이터**: 설문 1039줄 + 관리코드 450건 + 이슈·AS 이력 + 도면 메타데이터
- **벡터 DB**: pgvector (PostgreSQL 확장) 또는 Qdrant
- **검색 인터페이스**: 웹 상단 검색바 → Claude가 컨텍스트 수집 후 답변
- **질의 예시**:
  - "8자리 관리코드 채번 규칙이 뭐야?"
  - "이 부품 어떤 모델에 들어갔지?"
  - "작년에 검사기 X에서 발생했던 이슈 요약해줘"

### 5.4 Microsoft Copilot for Manufacturing

**2026 Copilot 실적**:
- Forrester ROI 연구: **112~457%** (3년, 25,000명 기준)
- SMB (중소) 연구: **132~353%** (3년)
- 제품 변경 관리 에이전트: **승인 기간 "몇 주 → 며칠"** · BOM 종속성 누락 **80% 감소** · 문서 업데이트 지연 "몇 주 → 며칠"
- 평균 공장 다운타임 월 27시간 → 첫 분기에 재무 영향

**Copilot 활용 영역 (제조업)**:
1. **Production Schedule Optimizer Agent** — BOM+작업지시+장비 상태+인력 일정 통합 최적화
2. **Product Change Management Agent** — 영향 분석·승인 라우팅·기록 업데이트 자동
3. **Teams에서 Copilot 호출** — 회의록·요약·답변 생성

**KNK 시사점**:
- **Copilot 라이선스 직접 도입은 비싸다** ($30/user/월 × 140명 = 월 4,200$)
- **핵심 개념(변경 관리 에이전트)을 Claude API로 자체 구현**이 경제적
- Microsoft 제품 변경 관리 에이전트 = KNK 설문 1순위 ②와 정확히 매칭

### 5.5 오픈소스 AI 스택 — 자체 구축 옵션

| 프레임워크 | 특징 | KNK 적합도 |
|---|---|---|
| **LangGraph** | 장기 워크플로우·감사 가능·오류 복구, LangChain 기반 | ⭐⭐⭐⭐ 변경 Inform 에이전트에 최적 |
| **CrewAI** | 역할 기반 협업 에이전트 | ⭐⭐⭐ 일일 요약 에이전트 가능 |
| **AutoGen (Microsoft Agent Framework)** | 대화형 협업·2025.10 통합 | ⭐⭐⭐ Azure 생태계 선호 시 |
| **Dify** | RAG 파이프라인 통합·디버거 우수 | ⭐⭐⭐⭐ **RAG 도입 시 추천** |
| **Langflow** | DataStax 백엔드·Astra DB 통합·비주얼 IDE | ⭐⭐⭐ 비주얼 선호 시 |
| **Flowise** | LangChain 노드 빌더·30분 내 챗봇 | ⭐⭐ KNK에는 단순 |
| **OpenAI Agents SDK** | OpenAI 공식 | ⭐⭐ Claude 선택했으므로 제외 |

**KNK 권장 스택**:
- **1차 (단순)**: Claude API 직접 호출 (Python `anthropic` SDK) + 자체 MCP 서버
- **2차 (확장)**: LangGraph (장기 에이전트 필요 시) + Dify (RAG 파이프라인)
- **불필요**: CrewAI·Flowise (복잡도 대비 가치 낮음)

### 5.6 워크플로우 자동화 플랫폼

| 도구 | 특징 | KNK 적합도 |
|---|---|---|
| **Zapier** | 5,000+ 앱 통합, 유료 | ⭐⭐ 비싸고 락인 |
| **Make** | 시각적 시나리오 빌더 | ⭐⭐⭐ 중간 |
| **n8n** | 자체 호스팅 무료·실행 한계 없음·80~90% 비용 절감 | ⭐⭐⭐⭐⭐ **KNK 권장** |

**n8n KNK 활용 예시**:
- baby 엑셀 변경 → web DB 자동 sync (5분 cron)
- 카톡 메시지 webhook → 티켓 자동 생성
- WEHAGO 근태 데이터 → 대시보드 자동 갱신
- Altium BOM 내보내기 → OpenBOM API 자동 업로드

**자체 호스팅 사례**: StepStone (유럽 최대 구직 플랫폼) — **200+ 프로덕션 워크플로우** n8n 운영 중.

### 5.7 AI 코딩 어시스턴트

**현재 진행 중인 KNK 방식**:
- **Claude Code CLI** (김정락 대표 직접 사용) — 빅터(Claude)와 페어 코딩
- 8커밋·17,000줄 이미 달성 — 2026 agentic coding 트렌드 정확히 구현

**2026 실적 사례** (Anthropic Agentic Coding Report):
- Rakuten · CRED · TELUS · Zapier — Claude 기반 멀티 에이전트 배포
- "Claude Code가 프로그래밍 변혁" — Anthropic CEO

**KNK 시사점**: **지금 방식이 최적**. 다른 도구 이전 불필요.

---

<a id="6-제조업-ai-성공실패-사례"></a>
## 6. 제조업 AI 성공·실패 사례

### 6.1 AI 성공 사례

| 기업 (유형) | AI 영역 | 결과 |
|---|---|---|
| 익명 전자제조 | AI 품질 검사 | 불량탈출율 **2.3% → 0.1%**, 연 $1.8M 보증 비용 절감 |
| 익명 자동차 (CNC·로봇 200+) | 예측 유지보수 | 계획외 다운타임 **47% 감소**, 연 $3.2M 절감 |
| Continental AG (타이어 공장 4개) | 예측 유지보수 | 다운타임 **37% 감소**, 연 **€8M+ 절감** |
| Microsoft Copilot 적용 고객 | 제품 변경 관리 | 승인 기간 몇 주→며칠, BOM 종속성 누락 **80% 감소** |

**AI 제조업 ROI 벤치마크 (2026)**:
- 품질 검사: 3년 ROI **250~350%**
- 예측 유지보수: 3년 ROI **400~500%**
- 전반적 AI 인프라: **200~300%**
- 평균 ROI 회수: 12~24개월

### 6.2 AI 제조업 채택 현황 (2026)

- **42% 제조업체가 AI 배포** 중
- 단 **12%만 엔터프라이즈 스케일** (나머지는 파일럿·단일 유스케이스)
- → **KNK가 지금 진입하면 아직 선도 그룹**

### 6.3 ERP 실패 사례 (AI 없이 전통 방식)

| 기업 | 실패 내용 | KNK 교훈 |
|---|---|---|
| **Hershey** (1999) | SAP 할로윈 전 전환 실패, 1천 2백만불 손실, 주가 8% 하락 | 단계적 롤아웃 필수 |
| **Nike** (2000) | i2 수요예측 실패, $100M 재고 손실 | AI 예측은 human-in-the-loop 필수 |
| **HP** (2004) | SAP 이관 실패, $160M 주문 손실 | 데이터 마이그레이션 품질 |
| **Lidl** (2018) | SAP S/4HANA 7년 $500M 포기 | 기존 프로세스에 맞추지 말고 표준 따라라 (역설: KNK는 표준 무시하는 커스텀이 맞음) |
| **Revlon** (2018) | SAP 전환 중 공장 가동 중단, 주요 소매업체 납품 실패 | 제조 운영에 직접 영향 |
| **Haribo** (2018) | S/4HANA 전환 후 원자재·재고 추적 불가, 마트 품절 | 마이그레이션 전 제로 검증 |
| **Invacare** (2021) | SAP 업그레이드 중단 후 온라인 주문 제한, 매출 채권 지연 | 점진적 확장 |
| **전체 통계** | **73%의 제조업 ERP 프로젝트가 목표 미달**, 평균 비용 초과 215% | 실패 원인 Top 3: 변경 관리 미흡 · 데이터 마이그 품질 · 팀 경험 |

**Make-to-Order 제조업 (KNK 같은) 특유 리스크**:
- MRP 계산·계획 계층 복잡성 과소평가
- 창고 관리 시스템 통합 부족
- 마스터 데이터 품질 → 수요예측 영향

### 6.4 KNK가 피해야 할 5가지 함정

1. ❌ **빅뱅 전환** (하루 아침에 모든 부서 전환) — Revlon/Lidl 실패
2. ❌ **패키지 강제 적용** (KNK 프로세스를 SAP에 맞추기) — Haribo 실패
3. ❌ **데이터 이전 졸속** (KNK PMS 관리코드 마이그레이션 소홀) — HP 실패
4. ❌ **변경 관리 경시** (직원 교육·가이드 없이 도입) — 73% 실패 공통 원인
5. ❌ **Full AI 대체** (Human-in-the-loop 없이 AI 자동 결정) — Nike 재고 예측 실패

### 6.5 KNK가 따를 5가지 성공 공식

1. ✅ **점진적 모듈 추가** (변경 Inform → 티켓 → 대시보드 → BOM 순)
2. ✅ **KNK 표준 유지** (관리코드·수주번호 손대지 않기)
3. ✅ **기존 도구 연동 (MCP)** (baby·WEHAGO·카톡 그대로)
4. ✅ **부서별 사용 가이드 작성** (가공팀 "정체 설명" 원칙)
5. ✅ **AI는 초안 생성, 최종은 인간 승인** (Human-in-the-loop)

---

<a id="7-한국-sme-제조업-현실"></a>
## 7. 한국 SME 제조업 현실

### 7.1 한국 ERP 시장 구도

| 업체 | 포지션 | 2026 상황 |
|---|---|---|
| **더존** | 중소기업 1위, 회계·재무 강함 | 스마트A 2023.12 단종 → 2025.12 유지보수 종료. 고객 교체 고민 중 |
| **영림원** | 제조·건설 특화 (K-System Ace) | 깊은 커스터마이징 제공 |
| **WEHAGO** | 더존 계열, 근태·전자결재 | KNK 이미 사용 중 |
| **하이웍스** | 그룹웨어 시장 점유율 1위 | KNK 이미 사용 중 |
| **SAP** | 대기업·중견 | K-스타트업은 B1 도입 많음 |
| **Odoo** | 오픈소스, 한국 파트너 증가 | 가격 경쟁력 우수 |

**한국 ERP 도입 현실**:
- 표준화된 범용 ERP는 중소기업 맞춤 한계
- 맞춤 설정 많을수록 초기 구축 + 유지보수 비용 상승
- 성공 핵심: **사내 전산팀이 계속 최적화·개발**해 간 기업

**KNK 시사점**: 사내 개발 역량 확보가 중장기 관건.

### 7.2 2026 스마트 제조혁신 지원사업 (정부 지원)

**2026년 스마트 제조혁신 지원사업 통합공고** (bizinfo.go.kr)

| 트랙 | 지원 | KNK 적합도 |
|---|---|---|
| **제조AI특화 스마트공장** (자율형공장 AI트랙) | 공정 최적화·예측 유지보수·AI에이전트·온디바이스AI | ⭐⭐⭐⭐ |
| **대·중소 상생형** (삼성전자 협력) | AI 트랙 신설, 최대 **3억원 (75%)** | ⭐⭐⭐⭐⭐ 신청 강력 추천 |
| **AI 응용제품 신속 상용화** | AI 제품화 지원 | ⭐⭐⭐ |
| **제조로봇 자동화 지원** | 로봇 도입 | ⭐⭐ 해당 없음 |

**신청 일정**: 4월 6일 ~ 5월 8일 온라인 접수 → 6월 중 선정. **즉시 검토 필요 (2026-04-20 현재 진행 중)**.

**2026 신청 전략**:
- 트랙: 대·중소 상생형 **AI 트랙**
- 과제명: "검사기·자동화 장비 수주 → 출하 전주기 AI 지원 시스템 (HAIST WORKS)"
- 핵심 어필: 설문 기반 설계 · 기존 운영 시스템(데일리허브) · 자체 개발 역량 (8커밋 증명)
- 기대 지원액: 2~3억원

### 7.3 한국 중소 제조업 디지털 전환 성공 요인

OECD + 독일 SME 연구 종합:
1. 데이터 기반 의사결정 (data analytics)
2. 직원 만족도 → ROI 지표
3. 최고경영자의 명확한 비전 → KNK 김정락 대표 ✅
4. 작은 파일럿 → 확장 → 전사
5. APAC 선두 (19% 디지털 챔피언 in 제조업)

---

<a id="8-반도체-검사기자동화-동종업계-인사이트"></a>
## 8. 반도체 검사기·자동화 동종업계 인사이트

### 8.1 PLM-ERP 통합의 반도체 업계 정답

**핵심 원칙**:
- 대부분 제조업체가 **PLM (제품 설계·개발용) + ERP (회사 관리용) 분리 운영**
- 통합의 가치: 데이터 중복 입력 제거, 공통 DB, 오류 감소, 효율 향상
- 반도체 검사기: 웨이퍼·칩 결함 검사 장비, 장비 자체가 매우 복잡함 → BOM 수백~수천 계층

**KNK 적용**:
- **baby 엑셀** = PMS (간이 ERP) + 부서별 진척
- **HAIST_WORKS 웹** = PLM + 협업 + 알림
- **OpenBOM** (추가 도입 검토) = BOM 통합 마스터
- 세 개가 MCP·API로 연결되어 단일 DB처럼 동작

### 8.2 KNK가 학습할 반도체 검사기 업계 best practice

1. **MES (Manufacturing Execution System)** 개념 — 실시간 생산 실행 추적
   → KNK: 조립·검수 공정을 web 진행률에 실시간 반영
2. **디지털 트윈** — 실제 장비와 가상 장비 동기화
   → KNK (중장기): 설치 완료 장비의 설정·서비스 이력 디지털 관리
3. **도면 전자화 (Engineering Drawing Digital)**
   → KNK: SolidWorks PDM + web 메타데이터 (3순위 ⑧)

### 8.3 경쟁사 벤치마크 (한국 반도체 검사기·자동화)

일반적 관찰 (구체 데이터 미공개이므로 업계 공통 추정):
- **3DEngg / Siemens Opcenter** 사용 기업: 중견 이상 (KNK 규모 상회)
- **Critical Manufacturing MES** 사용 기업: 반도체 후공정 라인 특화
- 대부분 중소 검사기 제조업체: **엑셀 + 노션 조합** 또는 **내부 개발 웹앱**
- 업계 공통 고통: BOM 변경 전파 지연, 도면 버전, AS 이력 분산 — **KNK 설문과 동일**

**결론**: KNK의 고통은 업계 공통. 해결 방식(자체 구축 하이브리드)은 중소 제조업의 모범 답안과 일치.

---

<a id="9-build-vs-buy-knk-결론"></a>
## 9. Build vs Buy — KNK 결론

### 9.1 3가지 접근 비교

| 접근 | 초기 투자 | 연 운영비 | 위험 | 장점 | 단점 |
|---|---|---|---|---|---|
| **A. 상용 패키지 전면 도입** (SAP B1/Odoo/영림원) | 1~3억 | 5천만~1억 | 🔴 73% 실패 | "완전 ERP" 기대 | KNK 표준 손실, 5~12개월 구축, 직원 교체 |
| **B. 풀 SaaS 조합** (Notion+Airtable+Monday+OpenBOM) | 0 | 3천만+ | 🟡 락인·5K행 한계·이중 입력 | 빠른 시작 | 한국 특화 연동 부재·성능·락인 |
| **C. 하이브리드 자체 구축 + 선택적 SaaS + AI** | 0 (내부 시간) | 2천만 이하 (API·일부 SaaS) | 🟢 KNK 표준 유지·점진적 | **KNK 완벽 맞춤** · AI 직접 활용 · 무한 확장 | 내부 개발 필요 (현재 확보) |

### 9.2 C안 (하이브리드) 경제성 추정

**투자 (첫해)**:

| 항목 | 금액 |
|---|---|
| 내부 개발 시간 (대표·빅터 AI 페어코딩) | 기존 인력 활용 = 0 |
| Claude API (Opus 4.7 1M) | ~$2K/월 × 12 = **$24K (~3,400만원)** |
| OpenBOM (15명) | ~$4,500 (650만원) |
| SolidWorks PDM (5명, 1회) | ~$7,500 (1,100만원) |
| n8n self-hosted 서버 | 무료 (기존 서버) |
| NAS 추가 디스크 (도면·증빙) | ~100만원 |
| **합계** | **~5,250만원** |

**국가 지원 적용 시**:
- 스마트공장 AI트랙 **75% × 최대 3억원** 가능
- 실 부담 **1,300만원 수준**

**연간 효과 (보수적)**:
- 카톡 요청 누락 월 2~3건 × 부서 10 × 건당 10만원 = **월 300만원 절감**
- 제조2 재작업 방지 (연 1~2회 × 500만원) = **500~1,000만원**
- 영업 매출 가시화 → 수주 전환율 5% 상승 = **억 단위**
- **ROI 10배 이상**

### 9.3 A안·B안 치명적 결함

**A안 (SAP 등) 치명적 결함**:
- 설문 1순위 "변경 Inform" — 패키지에 거의 없는 기능
- KNK 관리코드(`001T2604`) 강제 포기
- WEHAGO/하이웍스와 기능 중복 → 이중 지출
- Hershey·Haribo·Revlon 실패 재연 가능성

**B안 (SaaS 조합) 치명적 결함**:
- Notion 10,000행 저하 + Airtable 50K 한도 + Monday 관계형 약함
- 다수 라이선스 월 지출: 140명 × $50~100 = 월 **1,400만원**
- 한국 특화 부재 (WEHAGO·카톡·세관·국세청)
- AI 통합 파편화 (각 도구별 별도 AI)

### 9.4 C안 확신 근거

**Syntora 사례** (Claude + Manufacturing 자동화):
- "FastAPI app이 core logic → webhook이 Lambda 호출 → PDF를 Claude API에 → 구조화 데이터 반환"
- "20영업일 내 커스텀 제조 프로세스 구축 · 첫 달에 결과"
- **KNK 이미 8커밋 완료 = 경로 검증됨**

**Microsoft Agent 사례 역이용**:
- MS Product Change Management Agent = 승인 기간 몇 주→며칠, BOM 누락 80% 감소
- **같은 개념을 Claude API + MCP로 자체 구현 가능** (Microsoft 라이선스 없이)

**FastAPI 2026 입증**:
- FastAPI 12개 마이크로서비스 + Kong API Gateway = 독립 배포
- IoT 게이트웨이 사례: 500+ 센서 · 10,000+ msg/s · 시계열 DB 기록
- KNK 규모에는 **과도한 스케일조차 남아돎**

---

<a id="10-knk-적합도-매트릭스"></a>
## 10. KNK 적합도 매트릭스

### 10.1 12부서 × 기능 × 도구/AI 매핑

| 부서 | 1위 고통 | 기능 대응 | baby | web | AI | 외부 도구 |
|---|---|---|---|---|---|---|
| **구매** | 카톡 누락 + 이중 입력 | 요청 티켓 + ERP read-only | 🟢 입력 owner | 🟢 티켓 UI | 🟢 카테고리 분류 AI | — |
| **관리** | 증빙 제출 지연 + 법인카드 | 증빙 포털 + 자동 라우팅 | — | 🟢 포털 UI | 🟢 영수증 OCR→분류 | WEHAGO |
| **영업** | 진척율 가시화·Set Up | 모델별 진척 모바일 + KNKVN 뷰 | 🟢 V2 진행 | 🟢 모바일 import | 🟢 이메일→수주 요약 | — |
| **전장** | 기구 변경 대기 1~3일 | **변경 Inform** + 영향 분석 | — | 🟢 등록 UI | 🟢 **영향 판단 에이전트** | — |
| **설계** | 본사↔베트남 공유 | 통합 뷰 + 변경 Inform | 🟡 V2 KNKVN | 🟢 타임라인 | 🟢 번역 자동 | — |
| **검사기** | 의사소통 단편 + 이력 | 게시판 + 이슈 DB | 🟡 부서 sync | 🟢 이슈 DB | 🟢 **유사 이슈 검색 RAG** | — |
| **가공** | 우선순위 기준 + 도면 버전 | 긴급도 플래그 + PDM | — | 🟢 티켓 우선도 | 🟢 **AI 우선순위 제안** | SolidWorks PDM |
| **품질** | 이슈 종이 기록 | 이슈 DB + 사진 업로드 | — | 🟢 DB | 🟢 **사진 분류 AI** | — |
| **제조1** | 작업일정 PC | 공용 저장소 + 진행 | — | 🟢 upload | 🟡 | NAS |
| **제조2** | 변경 통보 누락 사고 | **변경 Inform** + PDM | — | 🟢 등록 | 🟢 **영향 부품 자동 표시 AI** | SolidWorks PDM |
| **SW** | 표준 라이브러리 부재 | Git 메타데이터 + 스니펫 검색 | — | 🟢 인덱스 | 🟢 **코드 스니펫 RAG** | — |
| **개발혁신** | 공정별 실시간 가시화 | 진행률 대시보드 | 🟢 import | 🟢 mobile | 🟢 이상 공정 감지 AI | — |

### 10.2 설문 기능 × 구현 우선순위 × AI 활용

| 우선순위 | 기능 | 구현 복잡도 | AI 활용 레벨 | 예상 기간 |
|---|---|---|---|---|
| 🔴 1순위 ① | 진행률 대시보드 (baby import) | 🟢 낮음 | 🟡 요약 AI | 1주 |
| 🔴 1순위 ② | **변경 Inform + AI 영향 분석** | 🟡 중간 | 🟢 **핵심 AI** | 2주 |
| 🟠 2순위 ③ | 요청 티켓 (카톡 보조) + AI 분류 | 🟢 낮음 | 🟡 분류 AI | 1주 |
| 🟠 2순위 ④ | 개인 PC → 공용 NAS 이전 | 🟢 정책 | ⚪ 없음 | 1주 |
| 🟠 2순위 ⑤ | 전사 근태 (WEHAGO 연동) | 🟢 낮음 | ⚪ 없음 | 3일 |
| 🟡 3순위 ⑥ | BOM 통합 마스터 | 🔴 높음 | 🟢 RAG 검색 | 4주 |
| 🟡 3순위 ⑦ | 이슈·AS DB + 유사 이슈 검색 | 🟡 중간 | 🟢 **RAG 핵심** | 3주 |
| 🟡 3순위 ⑧ | 도면 버전 관리 (PDM 연동) | 🟡 중간 | ⚪ 없음 | 2주 |
| 🟡 3순위 ⑨ | 표준 Library (Git 메타) | 🟡 중간 | 🟢 코드 RAG | 3주 |
| 🟡 3순위 ⑩ | 증빙 제출 포털 + OCR | 🟡 중간 | 🟢 OCR+분류 AI | 2주 |
| 🟡 3순위 ⑪ | KNKVN 통합 뷰 | 🟢 낮음 | 🟡 번역 AI | 1주 |
| 🟡 3순위 ⑫ | 4·5단계 입고·재고 | 🔴 높음 | 🟡 MRP 제안 | 6주 |

### 10.3 AI 활용 8가지 구체 시나리오

#### 시나리오 1. 변경 Inform 에이전트 (최우선)

**트리거**: 설계자가 web에서 변경 등록 ("기구 도면 변경 — 부품 ABC123을 ABC125로 교체")

**AI 작업**:
1. BOM 조회 → 영향 받는 상위 어셈블리·모델 리스트 자동 생성
2. 어셈블리 담당 부서(전장·SW·제조·가공·구매) 자동 판별
3. 과거 유사 변경 검색 → "2025-12 유사 변경 시 SW 코드도 수정됨" 알림
4. 변경 전/후 비교 요약 생성 → 카톡·메일 자동 발송
5. 승인 라우팅 초안 제시

**기술**:
- Claude API + MCP (baby BOM·web changes·CAD 메타)
- Microsoft PCM Agent 패턴 차용, 자체 구현

**효과**: 제조2 실사고 방지, 승인 기간 며칠→시간, BOM 누락 80% 감소

#### 시나리오 2. 일일 요약 에이전트 (매일 아침 8시)

**트리거**: 매일 아침 8시 자동 실행

**AI 작업**:
1. baby 엑셀에서 어제 업데이트된 모든 관리코드 추출
2. 지연 공정 자동 탐지 (기준일 초과)
3. 어제 등록된 티켓·변경·이슈 요약
4. 대표·팀장별 개인화 요약 생성
5. 카톡·메일 발송

**기술**: n8n cron + Claude API (요약) + 역할별 프롬프트

**효과**: 설문 매일 아침 1위 요구 충족, 미팅 시간 15분→0분

#### 시나리오 3. 카톡 티켓 자동 변환

**트리거**: 카톡 채널에서 메시지에 `!티켓` 접두어

**AI 작업**:
1. 메시지 내용 분석 → 카테고리 자동 분류 (자재요청·긴급가공·MODIFY·AS·검수)
2. 긴급도 판단 (긴급·보통·느림)
3. 담당 부서 자동 할당
4. 티켓 초안 생성 (제목·설명·첨부)
5. web 티켓 DB 저장 + 담당자 알림

**기술**: Kakao webhook → FastAPI → Claude API 분류 → DB

**효과**: 10팀 카톡 누락 해결, 기록 자동화

#### 시나리오 4. 이슈·AS 유사 사례 검색 (RAG)

**트리거**: 품질팀이 새 이슈 등록 시

**AI 작업**:
1. 이슈 내용을 벡터 임베딩
2. 이슈 DB에서 유사 사례 Top 3 검색
3. 과거 해결 방법 요약 제시
4. 재발 방지 체크리스트 자동 생성

**기술**: pgvector + Claude API

**효과**: 반복 이슈 재작업 감소, 지식 자산화

#### 시나리오 5. SW 표준 라이브러리 검색 (코드 RAG)

**트리거**: SW팀이 "비전 카메라 I/O 제어 코드" 검색

**AI 작업**:
1. Git 메타데이터에서 관련 함수·모듈 검색
2. 과거 프로젝트 X 코드 예시 제시
3. 사용법·주의사항 설명

**기술**: Git hooks로 커밋 메타 수집 → pgvector → Claude

**효과**: "매번 새로 작성" 문제 해결

#### 시나리오 6. 증빙 OCR 자동 분류

**트리거**: 관리팀이 사진 업로드

**AI 작업**:
1. 영수증 OCR (상호·금액·날짜·품목)
2. 사업자번호 → 거래처 자동 매칭
3. 법인카드 사용자 자동 식별
4. WEHAGO 전자결재 초안 생성

**기술**: Claude Vision + WEHAGO API

**효과**: 관리팀 최대 고통 (증빙 지연) 해결

#### 시나리오 7. 영업 이메일 → 수주 정보 추출

**트리거**: 영업팀이 고객 이메일 복사/붙여넣기

**AI 작업**:
1. 고객사·모델·수량·납기 자동 추출
2. 과거 같은 고객 수주 이력 검색
3. baby PMS 입력 초안 생성
4. 견적 자동 계산 제안

**기술**: Claude API + RAG

**효과**: 영업 반복 입력 시간 절감

#### 시나리오 8. 문서 질의응답 (Universal Q&A)

**트리거**: 아무 직원이 웹 상단 검색바에서 자연어 질문

**예시 질문**:
- "관리코드 채번 규칙이 뭐야?"
- "작년 검사기 X 이슈 요약해줘"
- "이 부품 어떤 모델에 들어갔지?"
- "어제 변경 Inform 몇 건이야?"

**AI 작업**:
1. 질문 의도 파악
2. 적절한 MCP 서버 선택 (baby·web·CAD)
3. 컨텍스트 수집 후 답변 생성

**기술**: Claude + MCP 오케스트레이션

**효과**: 시스템 학습 곡선 제거, 가공팀 "정체 설명" 원칙 충족

---

<a id="11-knk-통합-아키텍처"></a>
## 11. KNK 통합 아키텍처 (FastAPI + Claude + MCP)

### 11.1 전체 구조도

```
┌──────────────────────────────────────────────────────────────┐
│                    사용자 (140명)                             │
│  카톡 · 웹 브라우저 (PC/모바일) · 이메일                       │
└────────────────────┬─────────────────────────────────────────┘
                     │
      ┌──────────────┴──────────────┐
      │                             │
      ▼                             ▼
┌──────────────┐            ┌──────────────────┐
│ 카톡 Bot      │            │ HAIST WORKS 웹   │
│ (n8n + Kakao)│◀──────────▶│ (FastAPI, 8081)  │
└──────┬───────┘            └─────┬────────────┘
       │                          │
       │       ┌──────────────────┼──────────────┐
       │       │                  │              │
       ▼       ▼                  ▼              ▼
┌────────────────────┐    ┌───────────────┐  ┌──────────────┐
│ Claude API 레이어   │    │ 기존 시스템    │  │ 외부 도구     │
│ + MCP 오케스트레이션 │    │               │  │              │
│ ─────────────────── │    │ baby 엑셀 PMS │  │ WEHAGO/하이웍스│
│ - 변경 Inform AI   │◀──▶│ - 관리코드     │  │ - 근태        │
│ - 일일 요약 AI     │    │ - 수주·진척    │  │ - 전자결재    │
│ - 티켓 분류 AI     │    │ - 매출·자금    │  │               │
│ - RAG (이슈/BOM)   │    │               │  │ OpenBOM(선택) │
│ - 영향 분석 AI     │    │ 데일리허브 v2  │  │ - BOM 마스터  │
│ - OCR 분류 AI      │    │ (8080, 140명) │  │               │
└────────┬───────────┘    └───────────────┘  │ SolidWorks PDM│
         │                                    │ - 도면 버전    │
         ▼                                    │               │
┌─────────────────────┐                      │ Git (SW팀)    │
│ KNK DB (PostgreSQL) │                      │ - 메타데이터   │
│ - projects          │                      └──────────────┘
│ - changes           │
│ - tickets           │
│ - issues            │
│ - users             │
│ - boards            │
│ - embeddings(pgvec) │
└─────────────────────┘
```

### 11.2 MCP 서버 설계 (KNK 자체 구축)

5개 MCP 서버를 자체 개발. 각 서버는 Claude가 표준 방식으로 데이터 조회·조작 가능.

#### MCP Server 1: knk-pms-mcp

**역할**: baby 엑셀 PMS read-only 접근

**제공 Tool**:
- `list_projects(biz_div, status)` — 관리코드 리스트
- `get_project_detail(mgmt_code)` — 특정 프로젝트 전체
- `list_bom(mgmt_code)` — BOM 조회
- `get_delivery_status(mgmt_code)` — 진척도

**구현**: Python + openpyxl + FastMCP

#### MCP Server 2: knk-web-mcp

**역할**: web DB read/write (변경·티켓·이슈·게시판)

**제공 Tool**:
- `create_change(title, description, changed_parts)` — 변경 Inform 등록
- `list_affected_departments(change_id)` — 영향 부서 조회
- `create_ticket(category, requester, description)` — 티켓 생성
- `list_recent_issues(since)` — 최근 이슈
- `notify_user(user_id, message)` — 알림 발송

**구현**: FastAPI 엔드포인트 + FastMCP wrapper

#### MCP Server 3: knk-cad-mcp

**역할**: Altium · SolidWorks 메타데이터 조회

**제공 Tool**:
- `list_cad_files(project)` — 프로젝트 CAD 파일 목록
- `get_cad_bom(file_path)` — CAD에서 BOM 추출
- `get_latest_revision(file_path)` — 최신 리비전
- `where_used(part_number)` — 부품이 쓰인 곳

**구현**: SolidWorks API + Altium SDK + 파일시스템 감지

#### MCP Server 4: knk-git-mcp

**역할**: SW팀 Git 저장소 메타데이터

**제공 Tool**:
- `search_code(keyword)` — 코드 스니펫 검색
- `list_recent_commits(repo, since)` — 최근 커밋
- `get_function_history(function_name)` — 함수 변경 이력

**구현**: Git CLI + 로컬 인덱스

#### MCP Server 5: knk-hiworks-mcp

**역할**: WEHAGO/하이웍스 API 게이트웨이

**제공 Tool**:
- `get_attendance(user_id, date)` — 근태 조회
- `get_today_status(user_id)` — 오늘 휴가·출장
- `create_expense_report(expense_data)` — 전자결재 생성
- `list_pending_approvals(user_id)` — 미결재

**구현**: 하이웍스 REST API 호출 래퍼

### 11.3 Claude 에이전트 레이어 설계

**핵심 에이전트 (Anthropic Managed Agents 또는 자체 구축)**:

1. **change-inform-agent**
   - 시스템 프롬프트: "너는 KNK 변경 영향 분석 전문가"
   - 도구: knk-pms-mcp · knk-web-mcp · knk-cad-mcp
   - 트리거: `/changes/new` POST

2. **daily-summary-agent**
   - 시스템 프롬프트: "너는 매일 아침 대표·팀장용 KNK 요약가"
   - 도구: knk-pms-mcp · knk-web-mcp
   - 트리거: n8n cron 매일 08:00

3. **ticket-classifier-agent**
   - 시스템 프롬프트: "카톡 메시지를 KNK 티켓 카테고리로 분류"
   - 트리거: Kakao webhook

4. **rag-qa-agent**
   - 시스템 프롬프트: "너는 KNK 시스템 질의응답 어시스턴트"
   - 도구: pgvector 검색 + 모든 MCP
   - 트리거: 웹 검색바

### 11.4 기술 스택 세부

| 레이어 | 기술 | 이유 |
|---|---|---|
| 웹 프레임워크 | **FastAPI** | 이미 8커밋·17,000줄 축적, 비동기 우수, OpenAPI 자동 |
| DB | **SQLite → PostgreSQL 전환** | 140명 + 관리코드 450 → 멀티 사용자 쓰기 발생 시 PG 필요 |
| 임베딩 DB | **pgvector** (PG 확장) | 별도 DB 없이 PG에서 벡터 검색 |
| 프론트 | **Jinja2 + Vanilla JS** (HTMX 선택) | 기존 데일리허브 패턴 일치 |
| AI | **Anthropic Claude API** (Opus 4.7 1M context) | 김정락 대표 이미 페어코딩 사용 |
| MCP | **FastMCP (Python)** | 표준 프로토콜, Claude 공식 |
| 자동화 | **n8n self-hosted** | 무료·확장성, Kakao API 연동 우수 |
| 모바일 | **PWA** (Progressive Web App) | 네이티브 앱 개발 없이 모바일 대응 |
| 파일저장 | **로컬 NAS** + S3 호환 (MinIO 옵션) | 도면·증빙 용량 고려 |
| 인증 | **기존 데일리허브 세션** | 단일 로그인 |

### 11.5 DB 스키마 핵심 테이블

```sql
-- projects (기존 + 보강)
CREATE TABLE projects (
  id SERIAL PRIMARY KEY,
  mgmt_code VARCHAR(8) UNIQUE, -- 001T2604
  order_no VARCHAR(20), -- KNK-T-2604-001
  biz_div CHAR(1), -- T / M / S
  customer VARCHAR(100),
  model VARCHAR(100),
  status VARCHAR(20),
  due_date DATE,
  created_at TIMESTAMP
);

-- project_phases (1순위 ①)
CREATE TABLE project_phases (
  id SERIAL PRIMARY KEY,
  mgmt_code VARCHAR(8) REFERENCES projects(mgmt_code),
  phase_code VARCHAR(20), -- concept/design/elec/sw/...
  status VARCHAR(20), -- planned/in_progress/done/delayed
  assignee_id INT REFERENCES users(id),
  planned_date DATE,
  actual_date DATE,
  notes TEXT
);

-- changes (1순위 ②)
CREATE TABLE changes (
  id SERIAL PRIMARY KEY,
  title VARCHAR(200),
  description TEXT,
  changed_parts JSONB, -- [{before: "ABC123", after: "ABC125"}]
  affected_mgmt_codes TEXT[], -- AI가 자동 판별
  affected_departments TEXT[], -- AI가 자동 판별
  ai_impact_analysis JSONB, -- Claude 생성
  status VARCHAR(20), -- draft/reviewing/approved/rejected
  requester_id INT,
  approver_id INT,
  created_at TIMESTAMP
);

-- tickets (2순위 ③)
CREATE TABLE tickets (
  id SERIAL PRIMARY KEY,
  category VARCHAR(30), -- material/urgent_mach/modify/inspection/as
  source VARCHAR(20), -- web/kakao/email
  priority VARCHAR(10),
  requester_id INT,
  assignee_id INT,
  status VARCHAR(20),
  title VARCHAR(200),
  description TEXT,
  ai_classification JSONB, -- Claude 분류 결과
  created_at TIMESTAMP,
  resolved_at TIMESTAMP
);

-- issues (3순위 ⑦)
CREATE TABLE issues (
  id SERIAL PRIMARY KEY,
  customer VARCHAR(100),
  model VARCHAR(100),
  symptom TEXT,
  root_cause TEXT,
  solution TEXT,
  prevention TEXT,
  attachments JSONB,
  embedding VECTOR(1536), -- OpenAI/Claude 임베딩
  reported_by INT,
  reported_at TIMESTAMP
);

-- document_versions (3순위 ⑧)
CREATE TABLE document_versions (
  id SERIAL PRIMARY KEY,
  file_name VARCHAR(200),
  file_type VARCHAR(20), -- drawing/schematic/bom/manual
  version VARCHAR(20),
  path VARCHAR(500),
  is_latest BOOLEAN,
  mgmt_code VARCHAR(8),
  uploaded_by INT,
  uploaded_at TIMESTAMP,
  expires_at TIMESTAMP -- 30일 문제 해결
);

-- standard_library (3순위 ⑨)
CREATE TABLE code_snippets (
  id SERIAL PRIMARY KEY,
  name VARCHAR(200),
  category VARCHAR(50), -- vision/io/axis/ui
  description TEXT,
  code TEXT,
  language VARCHAR(20),
  repo VARCHAR(100),
  path VARCHAR(500),
  author VARCHAR(50),
  embedding VECTOR(1536),
  created_at TIMESTAMP
);

-- embeddings (범용 RAG)
CREATE TABLE knowledge_embeddings (
  id SERIAL PRIMARY KEY,
  source_type VARCHAR(30), -- issue/change/project/board/code
  source_id INT,
  content TEXT,
  embedding VECTOR(1536),
  metadata JSONB,
  created_at TIMESTAMP
);

CREATE INDEX ON knowledge_embeddings USING ivfflat (embedding vector_cosine_ops);
```

### 11.6 AI 호출 패턴

**변경 Inform 영향 분석 예시** (Python):

```python
from anthropic import Anthropic

client = Anthropic()

async def analyze_change_impact(change: ChangeDraft):
    # 1. MCP 도구 연결
    mcp_tools = [
        {"type": "mcp", "server": "knk-pms-mcp"},
        {"type": "mcp", "server": "knk-web-mcp"},
        {"type": "mcp", "server": "knk-cad-mcp"},
    ]
    
    # 2. Claude 호출 (prompt caching 필수)
    response = await client.messages.create(
        model="claude-opus-4-7",
        max_tokens=4000,
        system=[
            {
                "type": "text",
                "text": KNK_CHANGE_ANALYSIS_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"}  # 캐시
            }
        ],
        tools=mcp_tools,
        messages=[
            {"role": "user", "content": f"변경 내용: {change.description}\n변경 부품: {change.changed_parts}\n영향 부서·모델·다음 액션을 분석해줘."}
        ]
    )
    
    return response
```

**prompt caching** 필수 — Claude API 모범 사례에 따라 시스템 프롬프트와 자주 쓰는 컨텍스트 캐시 → 비용 90% 절감 가능.

---

<a id="12-8주-단기-로드맵"></a>
## 12. 8주 단기 로드맵

### Week 1 (4/20~4/26) — 변경 Inform AI 에이전트 (1순위 ②)

**목표**: 설문 1순위 ② + 제조2 사고 재발 방지

**작업**:
- [ ] DB 스키마: `changes` 테이블 + `change_impacts` 연결
- [ ] MCP 서버 `knk-web-mcp` 골격 (Tool: create_change, list_affected)
- [ ] Claude API 연동 (영향 분석 프롬프트)
- [ ] UI: `/changes/new` 폼 + 자동 분석 결과 표시
- [ ] 알림: 영향 부서 카톡 발송 (n8n + Kakao API)

**완료 조건**: 전장·제조2에서 시범 운영 → 1건 이상 성공

### Week 2 (4/27~5/3) — MCP baby 연동 + RAG 기초

**목표**: baby 엑셀 read-only → web에 관리코드 노출

**작업**:
- [ ] MCP 서버 `knk-pms-mcp` (list_projects, get_bom 등)
- [ ] pgvector 설치 + `knowledge_embeddings` 테이블
- [ ] 과거 설문·변경·이슈 임베딩 배치 작업 (최초 indexing)
- [ ] RAG Q&A 엔드포인트 `/api/ask`
- [ ] 영업·개발혁신 시범

### Week 3 (5/4~5/10) — 요청 티켓 + 카톡 연동

**목표**: 10팀 공통 카톡 누락 해결

**작업**:
- [ ] DB: `tickets` 테이블
- [ ] UI: 티켓 생성/조회/상태변경
- [ ] Kakao webhook 수신 엔드포인트
- [ ] AI 분류 에이전트 (카테고리·긴급도)
- [ ] 카테고리: 자재요청 · 긴급가공 · MODIFY · 검수 · AS

### Week 4 (5/11~5/17) — 진행률 대시보드 + baby import

**목표**: 10팀 매일 아침 요구 충족

**작업**:
- [ ] baby 엑셀 자동 import 스크립트 (n8n cron 1일 1회)
- [ ] `project_phases` 테이블 동기화
- [ ] 매트릭스 뷰 UI (관리코드 × 공정)
- [ ] 모바일 반응형
- [ ] 지연 알림 (기준일 초과 시 빨간색)

### Week 5 (5/18~5/24) — 일일 요약 AI + 근태 조회

**목표**: 매일 아침 8시 자동 요약 + 설문 근태 요구

**작업**:
- [ ] n8n cron 08:00 스케줄
- [ ] Claude 요약 프롬프트 (대표/팀장별 개인화)
- [ ] `knk-hiworks-mcp` 서버 구축
- [ ] 근태 대시보드 (오늘 휴가·출장·재택)
- [ ] 카톡·메일 자동 발송

### Week 6 (5/25~5/31) — 이슈·AS DB + RAG 검색

**목표**: 품질·검사기·SW 공통 요구

**작업**:
- [ ] `issues` 테이블 + 사진 업로드
- [ ] Claude Vision으로 사진 분류 보조
- [ ] 등록 시 유사 이슈 Top 3 자동 검색 표시
- [ ] 재발 방지 체크리스트 AI 생성

### Week 7 (6/1~6/7) — 도면 버전 관리 + 공용 저장소

**목표**: 제조2 30일 만료 사고 방지 + 5팀 공통 요구

**작업**:
- [ ] NAS + web 메타데이터 DB (`document_versions`)
- [ ] SolidWorks PDM 도입 검토 결정
- [ ] 업로드 → 자동 버전 증가 UI
- [ ] "Where Used" 조회 (특정 부품이 쓰인 도면)
- [ ] 5팀(제조2·품질·가공·영업·제조1) 개인 PC 파일 이전 마이그레이션 스크립트

### Week 8 (6/8~6/14) — 증빙 포털 + OCR + 스마트공장 신청

**목표**: 관리팀 증빙 지연 해결 + 정부 지원 신청

**작업**:
- [ ] `/expense/new` 사진 업로드
- [ ] Claude Vision OCR (상호·금액·날짜)
- [ ] WEHAGO 전자결재 자동 생성 (knk-hiworks-mcp 활용)
- [ ] **스마트공장 AI 트랙 신청서 작성** (5/8 마감이므로 이 일정은 조정 필요)

### 8주 완료 시 기대 상태

- ✅ 설문 1순위 2개 기능 완비
- ✅ 설문 2순위 3개 기능 완비
- ✅ 3순위 중 2개 (이슈·도면) 착수
- ✅ AI 에이전트 3개 가동 (변경·요약·티켓분류)
- ✅ MCP 서버 3개 가동
- ✅ 스마트공장 지원사업 신청 완료
- ✅ 10팀 중 최소 7팀이 일상에서 사용

---

<a id="13-6개월-중기-로드맵--1년-장기"></a>
## 13. 6개월 중기 로드맵 + 1년 장기

### 13.1 Month 3~6 (7월~10월)

**7월 — 표준 Library + Git 연동**
- SW팀 Git 메타데이터 수집 (hooks)
- 코드 스니펫 검색 UI
- `code-snippet-rag-agent` 구축

**8월 — BOM 통합 마스터**
- OpenBOM 도입 또는 자체 구축 결정
- 설계·전장·구매 통합 BOM
- Altium/SolidWorks → BOM 자동 sync

**9월 — KNKVN 통합 뷰 + 다국어**
- 본사↔베트남 실시간 공유
- 한국어·베트남어·영어 전환 (데일리허브 i18n 재활용)
- 베트남 법인 피드백 수집

**10월 — 4·5단계 입고·재고**
- 원래 web 로드맵의 입고/재고 모듈 (baby PMS와 양방향 연동)
- 물류팀 20명 시범
- MRP 제안 알고리즘 (AI 기반)

### 13.2 Month 7~12 (11월~2027년 3월)

**11~12월 — AI 고도화**
- Claude Managed Agents 이관 검토
- 에이전트 추가: 매출 예측·수요 계획·재고 최적화
- 기존 에이전트 프롬프트 튜닝 + eval 시스템

**1월 (2027) — 모바일 네이티브 전환**
- PWA → React Native 전환 검토
- 설문 이한빈 연구소장 요구: 현장 모바일 조회

**2월 — 외부 시스템 고도화**
- Altium / SolidWorks 실시간 연동 (메타데이터 → 실시간)
- Git + Altium + SolidWorks + baby + WEHAGO 완전 통합
- 디지털 트윈 개념 적용 (설치 완료 장비 관리)

**3월 — 전사 적용 완료 + 회고**
- 13개 부서 × 80+60명 완전 도입
- 설문 재실시 (1년 성과 측정)
- 다음 단계 로드맵 (AS 확대·고객 포털·IoT)

### 13.3 KPI 추적 (월별)

| 지표 | 기준 (0월) | 6월 목표 | 12월 목표 |
|---|---|---|---|
| 카톡 누락 월 건수 | 20~30 | <5 | <1 |
| 변경 Inform 사고 | 월 1~2 | 0 | 0 |
| 매일 아침 미팅 시간 | 15분×13팀=195분 | 5분×13팀=65분 | 0분 |
| 이슈 재발률 | 측정 불가 | 20% 감소 | 50% 감소 |
| 도면 만료 사고 | 분기 1건 | 0 | 0 |
| 직원 만족도 | 기준 설정 | +20% | +40% |
| AI 에이전트 개수 | 0 | 4 | 8 |
| MCP 서버 개수 | 0 | 3 | 5 |

---

<a id="14-위험-회피-체크리스트"></a>
## 14. 위험 회피 체크리스트

### 14.1 구축 위험 (Top 10)

| # | 위험 | 발생 시 피해 | 회피책 |
|---|---|---|---|
| 1 | **baby ↔ web 이중 입력** | 직원 신뢰 상실 | baby는 owner, web은 read-only import |
| 2 | **관리코드 표준 손실** | 450+ 이력 끊김 | 절대 대체 금지, MCP로 read-only만 |
| 3 | **Claude API 비용 폭증** | 월 $10K+ 가능 | prompt caching 필수, 배치 요약 |
| 4 | **AI 환각 (hallucination)** | 잘못된 변경 전파 | Human-in-the-loop + 영향 분석은 초안만 |
| 5 | **5천행 Notion 벽** | 성능 저하 | Notion은 위키만, 데이터는 PG |
| 6 | **SaaS 락인** | 이전 비용 수천만 | 데이터 owner는 KNK DB, SaaS는 참조만 |
| 7 | **카톡 대체 저항** | 전사 보이콧 | 카톡 유지, 티켓은 선택적 |
| 8 | **WEHAGO 중복 개발** | 이중 투자 | 근태·결재·급여는 WEHAGO 위임 |
| 9 | **직원 교육 부족** | 사용 저조 | 부서별 사용 가이드 .md + 스크린샷 |
| 10 | **김정락 대표 번아웃** | 추진력 상실 | AI 페어코딩으로 시간 절약, 단계적 위임 |

### 14.2 보안·컴플라이언스 체크

| 항목 | 상태 | 조치 |
|---|---|---|
| 영업비밀 (BOM·원가) | 🟡 주의 | web DB 접근 권한 부서별 분리 |
| 개인정보 (140명 인사) | 🟡 주의 | WEHAGO에서만 관리, web은 사용자ID만 |
| 고객사 정보 | 🟡 주의 | 이슈 DB 고객사 이름 마스킹 옵션 |
| Claude API 데이터 | 🟢 안전 | Anthropic 정책: 기본 학습에 안 씀 |
| MCP 서버 인증 | 🔴 필수 | 로컬 MCP는 부족, OAuth·감사추적 구현 |
| 감사 로그 | 🔴 필수 | 모든 AI 호출·변경 승인·티켓 기록 보관 |

### 14.3 기술 부채 관리

- **DB 마이그레이션**: SQLite → PostgreSQL 전환 계획 필수 (140명 동시 쓰기 한계)
- **테스트 커버리지**: pytest 기본 + AI 에이전트 eval 세트
- **백업**: NAS + 클라우드 (일일 snapshot)
- **모니터링**: Grafana + Loki (데일리허브 패턴 재활용)
- **업데이트**: 월 1회 의존성 업그레이드 (Dependabot)

---

<a id="15-세션별-다음-액션"></a>
## 15. 세션별 다음 액션

### 15.1 HAIST_WORKS 메인 세션 (웹 구현)

**즉시 작업 (이번 주)**:

```
@KNK업무시스템구축/HAIST_WORKS_심화리서치.md 읽고
Week 1 변경 Inform + AI 영향 분석 에이전트 구축 시작해줘.

특히 다음 순서로:
1. `changes` 테이블 DB 스키마 추가
2. `knk-web-mcp` 서버 골격 (create_change 도구)
3. Claude API 연동 (영향 분석 프롬프트)
4. `/changes/new` 폼 + 자동 분석 결과 UI
5. 카톡 알림 (n8n webhook)
```

**필수 참조**:
- 이 문서 §10.3 시나리오 1 (변경 Inform 에이전트)
- 이 문서 §11.5 DB 스키마
- 이 문서 §11.6 AI 호출 패턴 (prompt caching 필수)
- `HAIST_WORKS_설문분석.md` §제조2 응답 (실사고 컨텍스트)

**금지 사항**:
- baby 엑셀에 쓰기 시도 금지 (read-only MCP만)
- 4·5단계 입고/재고 선착수 금지 (우선순위 후순위)
- 카톡 대체 시도 금지 (티켓은 선택적)

### 15.2 HAIST_WORKS_baby 세션 (엑셀 작업)

**즉시 작업**:

```
@KNK업무시스템구축/HAIST_WORKS_심화리서치.md 읽고
baby V2 영업 보완 마무리해줘.

구체 항목:
1. A-1 수금조건 컬럼 + A-2 실제입금 추적
2. A-3 수주잔고 대시보드 시트
3. A-4 월별 매출예측 시트
4. B-4 KNKVN 이관 뷰
5. shared/knk_standard.py 에 web MCP와 연동 가능한 관리코드 API 노출
```

**필수 참조**:
- 이 문서 §4.10 WEHAGO 연동 패턴
- 이 문서 §11.2 MCP Server 1 knk-pms-mcp 설계
- `HAIST_WORKS_종합설계분석.md` §3 baby V2 설계
- `HAIST_WORKS_baby/V1/README_v1.md`

**금지 사항**:
- 관리코드 채번 규칙 변경 금지 (web과 호환 깨짐)
- 새 엑셀 컬럼 이름은 `shared/knk_standard.py`와 일치시킬 것
- 부서별 입력 파일과 PMS 시트 양방향 sync 로직 깨지지 않게 검증

### 15.3 리서치 세션 (HAIST_WORKS_Research, 나)

**향후 작업 (사용자 요청 시)**:
- 월간 트렌드 리포트 (신 AI 모델·새 MCP 서버·규제 변화)
- 경쟁사 벤치마크 심화 (구체 기업 3~5개)
- 스마트공장 지원사업 신청서 작성 보조
- Eval 세트 설계 (AI 에이전트 품질 측정)
- 사용자 피드백 수집 방법론 (베트남 법인 포함)

---

<a id="부록-리서치-소스-인덱스"></a>
## 부록: 리서치 소스 인덱스

### A. 수행한 18회 웹 검색 리스트

| # | 주제 | 핵심 소스 |
|---|---|---|
| 1 | Notion SME manufacturing limits | ones.com · hackceleration.com · Notion Help Center |
| 2 | Monday vs Airtable manufacturing | thedigitalprojectmanager.com · tadabase.io · capterra |
| 3 | MRPeasy SME case study | mrpeasy.com blog · capterra reviews · bytegrid case |
| 4 | OpenBOM vs Aras PLM | selecthub.com · g2.com · trustradius |
| 5 | Slack/Kakao Work enterprise | kedglobal.com · slack.com blog · koreatechtoday |
| 6 | AI agent enterprise 2026 MCP | anthropic.com · venturebeat · thenewstack · intuitionlabs |
| 7 | Microsoft Copilot manufacturing | aufaittechnologies · 2wtech · microsoft.com |
| 8 | RAG manufacturing BOM docs | docsie.io · nstarxinc · mdpi GraphRAG research |
| 9 | Notion AI Airtable AI 2026 | tech-insider.org · productivetemply · max-productive |
| 10 | AI ECN change management 2026 | microsoft.com industry blog · autodesk · varseno |
| 11 | SAP ERP failure manufacturing | panorama-consulting · cio.com · godlan stats |
| 12 | Digital transformation SME hidden champion | jsbs.scholasticahq · oecd.org · springer · scirp |
| 13 | AI manufacturing predictive QC ROI | pravaahconsulting · standardbots · alphabold · masterofcode |
| 14 | Odoo vs SAP B1 SME | odoo.com · infraxio · navabrindsol · tatvamasilabs |
| 15 | 한국 SME ERP 실패 더존 영림원 | korea-erp.com · thelec.kr · clien 커뮤니티 |
| 16 | 반도체 검사기 PLM ERP | deskera · infosys · critical manufacturing · siemens |
| 17 | AI agent framework LangChain CrewAI | intuz · fungies · turing · o-mega · lindy |
| 18 | KakaoTalk work ticket 자동화 | wikidocs n8n · sendbird · 360smsapp |
| 19 | WEHAGO 하이웍스 API | developers.hiworks.com · hiworks.com · wehago.com · foxcg |
| 20 | n8n Zapier Make 워크플로우 | digidop · zapier blog · cipherprojects · goodspeed |
| 21 | FastAPI enterprise production | fastlaunchapi · dev.to · flatlogic · syntora.io |
| 22 | Dify Langflow Flowise enterprise | toolhalla · zenml · aixsociety · stackai |
| 23 | Linear ClickUp Jira small team | clickup · monday · efficient.app · agileleadershipday |
| 24 | 한국 중소기업 AI 스마트공장 2026 | bizinfo.go.kr · smart-factory.kr · dfinite.ai · nexusb |
| 25 | Claude Anthropic MCP enterprise deploy | docs.anthropic.com · mintmcp · dextralabs · truefoundry |

### B. 확인된 핵심 레퍼런스 URL (다음 세션용)

**AI 플랫폼**:
- https://www.anthropic.com/news/donating-the-model-context-protocol (MCP 오픈 이관)
- https://www.anthropic.com/research/anthropic-economic-index-september-2025-report (AI 채택률)
- https://venturebeat.com/orchestration/anthropics-claude-managed-agents (Managed Agents)
- https://docs.anthropic.com/en/docs/claude-code/mcp (MCP 공식 문서)

**제조업 AI**:
- https://www.microsoft.com/en-us/industry/blog/manufacturing-and-mobility/manufacturing/2025/12/09/accelerate-innovation-with-ai-introducing-the-product-change-management-agent-template/ (MS PCM Agent)
- https://www.dataiku.com/stories/blog/manufacturing-ai-trends-2026 (2026 제조업 AI 트렌드)
- https://www.pravaahconsulting.com/post/ai-in-manufacturing (AI ROI 벤치마크)

**도구 비교**:
- https://www.mrpeasy.com/blog/tag/mrpeasy-case-study/ (MRPeasy 성공 사례)
- https://www.selecthub.com/plm-software/aras-vs-openbom/ (Aras vs OpenBOM)

**한국 현황**:
- https://www.bizinfo.go.kr/sii/siia/selectSIIA200Detail.do?pblancId=PBLN_000000000115998 (제조AI 스마트공장)
- https://developers.hiworks.com/about (하이웍스 개발자센터)
- https://korea-erp.com/erp-company-top5/ (한국 ERP TOP5)

**ERP 실패**:
- https://www.panorama-consulting.com/hersheys-erp-failure/ (Hershey)
- https://www.panorama-consulting.com/lidl-erp-failure/ (Lidl)
- https://www.panorama-consulting.com/revlon-erp-failure/ (Revlon)
- https://godlan.com/erp-implementation-failure-statistics/ (73% 실패율)

### C. 이후 조사 필요 (스코프 밖)

- 구체 한국 자동화·검사기 경쟁사 IR/기술블로그 (직접 해당 회사 자료 수집 필요)
- 베트남 현지 시스템 도입 사례 (이용식 법인장 인터뷰 후 보강)
- Claude API 실제 월간 토큰 사용량 추정 (파일럿 2주 후 측정)
- KNK 특화 보안 요구 (방산·보안장비 고객 여부 확인 필요)

---

## 📌 다음 세션 시작 치트시트

### HAIST_WORKS (메인) 세션 첫 메시지
```
@KNK업무시스템구축/HAIST_WORKS_심화리서치.md 읽고 Week 1 (변경 Inform AI) 구축 시작해줘.
```

### HAIST_WORKS_baby 세션 첫 메시지
```
@KNK업무시스템구축/HAIST_WORKS_심화리서치.md 읽고 baby V2 영업 A-1~B-4 마무리 + shared 관리코드 API 노출해줘.
```

### HAIST_WORKS_Research (이 세션) 추가 작업 요청 시
```
@KNK업무시스템구축/HAIST_WORKS_Research/00_작업큐.md 보고 2순위 임무 진행해줘.
```

---

**문서 버전**: 1.0
**다음 업데이트**: Week 2 완료 후 실전 사용 피드백 반영
**작성자**: 빅터 (Claude Opus 4.7, HAIST_WORKS_Research 세션)
**검수 대상**: 김정락 대표이사 (KNK / HAIST Innovation)
