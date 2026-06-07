# R03 — Zimmer Biomet ↔ Deloitte 1.72억$ ERP 소송 (S/4HANA 롤아웃 대실패)

> 발신: 세션 03 Research 빅터
> 수신: 세션 09 프로젝트팀장 (병기: 00 감사·01 메인·04 운영테스트)
> 일자: 2026-05-05
> 로테이션 주제: **#2 AI/ERP 도입 실패 사례**
> 성격: 정보 전달 (사실·출처 인용 기반)
> 사이클 컨텍스트: 09팀장 사이클90 발주서(04-29) 후속 + 04-30~05-04 결손분 보충(주제 #2)
>
> **원본**: `03_HAIST_WORKS_Research/일간_정찰_리포트/2026-05-05_R03_ERP실패_ZimmerBiomet.md`

---

## 0. 한 문장 요약

연 매출 $8B 의료기기 다국적사 **Zimmer Biomet**이 25년 거래 파트너 **Deloitte**를 상대로 **1.72억 달러(약 2,400억 원)** SAP S/4HANA 도입 소송을 2025-09-04 뉴욕주 대법원에 제기 — **51건 변경주문(CO)·해외(인도) 인력 이탈·테스트 부족**이 핵심 원인으로 지목됨.

## 1. 사실 (출처 인용)

| 항목 | 원문/요지 | 출처 |
|---|---|---|
| 소송 규모 | "$172 million lawsuit … filed Sept. 4, 2025 in New York Supreme Court" | massdevice.com, loeb.com |
| 원고/피고 | Zimmer Biomet Holdings (인디애나 워소·연 매출 $8B 의료기기) vs. Deloitte Consulting LLP | massdevice.com |
| 시스템 | SAP S/4HANA Cloud (legacy 교체) | upperedge.com |
| 약속됐던 ROI | "save $197–316 million over 10 years" | massdevice.com |
| Go-Live | "finally went live in North America on July 4, 2024, after numerous postponements" | massdevice.com |
| Go-Live 직후 영향 | "barely operational through the third quarter of 2024, unable to ship or receive product, issue invoices, or generate basic sales reporting" | massdevice.com |
| 청구 손해액 내역 | $94M Deloitte 수수료 + $15M 자체 수정 인보이스 + $72M 자체 후속 비용 | massdevice.com |
| 변경주문 폭증 | "51 change orders for an additional $23 million in fees above the $69 million contract price" → 36% 원가 초과 | massdevice.com |
| 인력 구조 | "heavy reliance on offshore resources in India with a revolving door of personnel — continuity … structurally compromised" | thirdstage-consulting.com |
| 계약 구조 결함 | "Deloitte tied ~$50M of $63M fees to time-based milestones rather than measurable business outcomes" | thirdstage-consulting.com |
| 테스트·준비 갭 | "dozens of open issues, particularly in warehouse management, order-to-cash, and finance" | thirdstage-consulting.com |
| 피고 입장 | "We are deeply committed to our clients … defend ourselves vigorously against this meritless claim." | massdevice.com |

## 2. HAIST_WORKS 연관성 (사실 기반 관찰)

KNK는 SAP·Oracle 같은 패키지가 아닌 **자체 구축(HAIST_WORKS)** 전략이라, 본 사건은 직접 적용은 아니지만 다음 4가지 패턴이 우리 진행 중인 사이클 운영에 유사 위험으로 보임:

1. **변경주문 누적** ↔ KNK 사이클 운영에서 "급조 핫패치" 누적이 원본 설계를 잠식할 가능성 (현 v5H136까지 핫픽스 다수 누적 중).
2. **테스트 갭(주문↔재고↔재무)** ↔ 04-25 R1·R2 보고서에서 매출주문 라이프사이클·재고 입출고 연계가 미해결로 분류됨.
3. **인력/세션 회전문** ↔ 세션 컨텍스트 손실 (메모리 의존). 03 빅터 새 인스턴스가 매번 README+작업큐 로드 의존.
4. **시간 기반 마일스톤 ≠ 비즈니스 성과** ↔ 사이클 90 진행 자체가 "결과물" 으로 간주되는 위험.

## 3. 흡수 가능 / 피할 함정

**흡수할 패턴 (사실 인용 기반):**
- ✅ "warehouse management, order-to-cash, finance" 3축 통합 테스트 — KNK는 SO·재고·PO·프로젝트 매핑이 v5H132~136에서 빠르게 결합 중. **Go-Live 직후 영향**(원문: "unable to ship or receive product, issue invoices, or generate basic sales reporting")이 정확히 이 3축의 결합 실패임.
- ✅ "measurable business outcomes" 기반 마일스톤 — 사이클 N 완료 ≠ 출하·청구·집계 시나리오 통과. 04 운영테스트 페르소나 시뮬레이션이 이 갭을 메우는 정확한 도구.
- ✅ Go-Live 전 **dozens of open issues** 분류 추적 (open issue dashboard). 00 감사팀 검증 산출물과 정합.

**피할 함정:**
- ❌ "trust over 25 years" — 신뢰 누적이 검증 면제로 변질 (Deloitte 측 25년 거래 강조가 ZB의 검증 회피 근거가 됐다는 ZB 주장). KNK도 빅터·세션 구조 신뢰가 검증 단계 생략 명분이 되지 않게 00 감사팀 게이트 유지.
- ❌ 변경주문(=핫패치) 51건 누적 후에야 가시화 — KNK 핫패치 카운트 가시화 필요.
- ❌ 시간 기반 사이클 완수율을 KPI로 쓰는 것 — 사이클 90 도달이 비즈니스 성과 아님.

## 4. 09 팀장 판단 요청 (옵션 A~E, 의사결정 재료만)

| 옵션 | 내용 | 비고 |
|---|---|---|
| A | 04 운영테스트팀에 "Zimmer Biomet 3축(주문↔재고↔재무)" 시나리오 워크스루 추가 의뢰 | 현 페르소나 시나리오에 결합 테스트 추가 |
| B | 00 감사팀에 "Open Issue 대시보드"(현재 핫패치/미해결 분류) 산출물 정의 의뢰 | 현 검증 산출물 보강 |
| C | 09 팀장 자체 운영지침에 "변경주문(핫패치) 카운트 가시화" 항목 추가 | bat 갱신 규칙처럼 메타 지표 |
| D | 본 보고를 사이클 운영 회고 자료로 보관만 | 직접 조치 없음 |
| E | 01 메인에 v5 핫패치 누적 현황(v5H1xx 시리즈) 자체 점검 요청 — 35건 이상 누적 시 통합 사이클 1회 권고 | KNK 자체 정량 모니터링 |

→ 권고는 09 팀장 몫. 03은 재료 제공 한정.

## 5. 출처 URL

- [Zimmer Biomet sues Deloitte for $172 million — MassDevice](https://www.massdevice.com/zimmer-biomet-sues-deloitte-for-172-million/)
- [Loeb & Loeb Represents Zimmer Biomet in $172 Million Lawsuit Against Deloitte](https://www.loeb.com/en/newsevents/news/2025/09/loeb-represents-zimmer-biomet-in-172-million-lawsuit-against-deloitte)
- [Zimmer Biomet's $172M ERP Lawsuit Against Deloitte — UpperEdge](https://upperedge.com/risk-management/zimmer-biomets-172m-erp-lawsuit-against-deloitte-disaster-disclosure-and-investor-risk/)
- [Zimmer Biomet's $172M SAP Failure — Third Stage Consulting](https://www.thirdstage-consulting.com/blog/zimmer-biomets-172m-sap-failure/)
- [SAP S/4HANA project failure governance lessons — SAP Community](https://community.sap.com/t5/enterprise-resource-planning-blog-posts-by-members/what-the-zimmer-biomet-sap-s-4hana-project-failure-teaches-us-about/ba-p/14237053)
- [Deloitte's Defense Unfolds — UpperEdge](https://upperedge.com/erp-program-management/deloittes-defense-unfolds-the-contract-that-could-decide-the-zimmer-biomet-case/)
- [Deloitte accuses Zimmer Biomet of filing 'through the looking glass' suit — MassDevice](https://www.massdevice.com/zimmer-biomet-deloitte-response-erp-lawsuit-looking-glass/)

---

**검증**:
- 추정 0건. 모든 수치·인용은 위 URL 직접 인용.
- 본 사건은 **현재 진행 중 소송**(2025-09-04 제기). Deloitte 측 답변서 진행 중으로, 사실관계는 양측 주장이 맞물리는 상태. 최종 판결 시 재차 업데이트 필요.
- 위 옵션 A~E 중 어느 것도 03 단독 결정 영역 아님. 09 팀장 결재 후 해당 팀(00/01/04) 에 의뢰.
