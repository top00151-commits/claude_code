# BRIEF #02 — KNK HAIST WORKS · 풀세트 13 마스터 시안

> **사용 시점**: BRIEF #01에서 컨셉 1개 선정 후 사용. 선정된 컨셉으로 전체 13 카테고리 마스터 발행.
> **사용법**: 본 파일 전체 복사 → claude.ai/design 새 채팅 → 붙여넣기. 첨부: 선정된 BRIEF #01 컨셉의 5개 HTML + KNK 로고.
> **편집**: 빅터(05) 코디네이터 / **2026-05-08**

---

## 📋 Claude Design에게 — 의뢰 시작

안녕하세요. ㈜케이엔케이 김정락 대표입니다.

이전 BRIEF #01에서 3가지 컨셉(A 순백 / B 슬레이트 / C 사무용) 중 **컨셉 [_____]**을 선정했습니다. 이제 이 컨셉으로 전체 13 카테고리 마스터를 발행해주세요.

선정 컨셉의 5 페이지 HTML을 첨부했습니다. **동일한 톤·색·간격·모서리·폰트 스케일**을 모든 신규 페이지에 일관되게 적용해주세요.

---

## 1. 사용자 (페르소나) — BRIEF #01 동일

| 페르소나 | 나이 | 역할 |
|---|---|---|
| 김 부장 | 52 | 영업 (견적·고객) |
| 이 차장 | 48 | 자재·구매 (발주·재고) |
| 박 과장 | 45 | 생산·납기 |
| 최 대리 | 35 | 회계·세무 |
| 김 대표 | 60 | 의사결정·승인 |

**핵심**: "50-60대 어려워 보이지 않게."

---

## 2. 13 카테고리 마스터 (각 1 마스터 + variations)

### A. 대시보드 (이미 BRIEF #01에서 발행 — 참고용)
- `master_A_home.html` — 통합 대시보드
- variation: `master_A_home_김부장.html` (영업 페르소나 우선순위)
- variation: `master_A_home_이차장.html` (자재 페르소나 우선순위)
- variation: `master_A_home_대표.html` (의사결정 KPI 우선)

### B. 발주 (PO) — 이미 BRIEF #01에서 list/form/detail 발행
- `master_B_po_list.html` (참고용)
- `master_B_po_form.html` (참고용)
- `master_B_po_detail.html` (참고용)
- 신규: `master_B_po_approve.html` — 결재 화면 (승인·반려·코멘트)
- 신규: `master_B_po_print.html` — 인쇄용 발주서 양식 (A4 한 장)

### C. 견적 (Quote)
- `master_C_quote_list.html` — 견적 리스트
- `master_C_quote_form.html` — 견적 작성 (B 발주서와 유사 구조)
- `master_C_quote_detail.html` — 견적 상세 (PDF 미리보기)
- 변환 흐름: 견적 → 발주 (한 클릭 컨버전 UI)

### D. 자재 (Material)
- `master_D_material_list.html` — 자재 마스터 (검색·분류 중심)
- `master_D_material_detail.html` — 자재 상세 (재고·이력·거래처)
- `master_D_stock_alert.html` — 재고 알림 화면 (안전재고 미달 리스트)

### E. 거래처 (Customer)
- `master_E_customer_list.html` — 거래처 리스트
- `master_E_customer_detail.html` — 거래처 상세 (거래이력·연락처·신용)
- `master_E_customer_form.html` — 거래처 등록·수정

### F. 생산 (Production)
- `master_F_production_board.html` — 칸반 보드 (대기/진행/완료) 또는 표
- `master_F_production_detail.html` — 작업 상세
- ⚠ 칸반 사용 시 한 컬럼 카드 ≤ 5 (정책 §6)

### G. 회계 (Accounting)
- `master_G_invoice_list.html` — 세금계산서·일계표
- `master_G_invoice_detail.html` — 세금계산서 상세
- `master_G_payment.html` — 수금·지급 관리

### H. 결재 (Approval) — 통합 결재함
- `master_H_inbox.html` — 내 결재함 (탭: 대기 / 처리 / 위임)
- `master_H_approval_detail.html` — 결재 상세 (승인·반려·전결)
- ⚠ 외부 그룹웨어 전자결재 계속 사용 정책 (시스템 범위 정책) — 본 화면은 KNK 자체 결재 (간단 발주 결재용)

### I. 알림·메신저
- `master_I_notifications.html` — 알림 센터 (10_KNK_Messenger 연계)
- `master_I_messenger.html` — 사내 메신저 (10번 프로젝트와 통합)
- ⚠ 10_KNK_Messenger 디자인 토큰과 동기화

### J. 빅터 AI
- `master_J_victor_chat.html` — 빅터 AI 대화 (사이드 드로어 형식)
- `master_J_victor_recommendations.html` — AI 추천 모음 페이지

### K. 설정 (Settings)
- `master_K_settings.html` — 개인 설정 (프로필·알림·테마)
- `master_K_admin.html` — 관리자 설정 (사용자·권한·코드)

### L. 보고서 (Report)
- `master_L_report_list.html` — 보고서 목록
- `master_L_report_view.html` — 보고서 상세 (차트·표)
- ⚠ 차트 사용 시 색 ≤ 3색, 범례 명확

### M. 검색 (Global Search)
- `master_M_search.html` — 통합 검색 결과 페이지
- 카테고리 탭: 전체 / 발주 / 견적 / 자재 / 거래처 / 직원

---

## 3. 글로벌 컴포넌트 (모든 페이지 공통)

### Header
- 좌: KNK 로고 + "HAIST WORKS"
- 중: 글로벌 검색
- 우: 빅터 AI 호출 / 알림 / 결재함 / 아바타

### Sidebar
- 1차: 대시보드 / 발주 / 견적 / 자재 / 거래처 / 생산 / 회계 / 결재 / 보고서 / 설정
- 접기·펼치기 가능
- 활성 메뉴 표시 (선정 컨셉의 액센트 색)

### Footer
- ㈜케이엔케이 · 02-3142-XXXX · v6.0

---

## 4. 정책 §6 정보 분산 — 강제 적용

| 패턴 | 적용 위치 |
|---|---|
| 탭 분산 | 대시보드, 결재함, 검색결과, 보고서 |
| 접기 Collapse | 폼 (단계별), 상세 (이력·첨부) |
| 드로어 | 빅터 AI, 빠른 보기, 필터 |
| 페이지네이션 | 모든 리스트 (무한 스크롤 절대 금지) |

---

## 5. 산출물 형식

```
풀세트_컨셉[선정]/
├── A_대시보드/master_A_home.html (+ 3 variations)
├── B_발주/master_B_*.html (5개)
├── C_견적/master_C_*.html (3개)
├── D_자재/master_D_*.html (3개)
├── E_거래처/master_E_*.html (3개)
├── F_생산/master_F_*.html (2개)
├── G_회계/master_G_*.html (3개)
├── H_결재/master_H_*.html (2개)
├── I_알림메신저/master_I_*.html (2개)
├── J_빅터AI/master_J_*.html (2개)
├── K_설정/master_K_*.html (2개)
├── L_보고서/master_L_*.html (2개)
└── M_검색/master_M_search.html (1개)
```

총 약 **30+ 파일**.

각 파일:
- 단일 HTML, inline CSS
- Pretendard CDN
- 더미 데이터 한국어 (거래처: 삼성중공업·현대제철·LS전선·포스코·두산에너빌리티 등)
- 반응형 (`@media (max-width:768px)`)
- 선정 컨셉의 색·모서리·폰트 일관 적용

---

## 6. 자가검증 7종 (BRIEF #01 동일)

각 마스터 발행시 표로 보여주세요:

| # | 기준 |
|---|---|
| U-1 | 한 화면 카드 ≤ 5 |
| U-2 | 콘트라스트 ≥ 7:1 |
| U-3 | 무한 스크롤 = 0 |
| U-4 | 액센트 색 ≤ 5% |
| U-5 | 모서리 일관성 |
| U-6 | 외국 브랜드명 0건 |
| U-7 | 영문 코멘트 라벨 0건 |

추가:
| U-8 | 글로벌 헤더·사이드바·푸터 일관성 (전 페이지) |
| U-9 | 더미 데이터 한국어 자연스러움 |
| U-10 | 페르소나별 우선순위 반영 (variations) |

---

## 7. 발행 순서 (제안)

1. **A 대시보드 + variations 4개** — 페르소나 검증 우선
2. **B 발주 신규 2개** (approve, print)
3. **C 견적 3개** — 발주와 흐름 연결
4. **D, E, F, G** — 마스터 데이터 + 운영
5. **H, I, J** — 결재·메신저·AI
6. **K, L, M** — 설정·보고서·검색

각 단계 완료시 자가검증 표 + 다음 단계 진행 여부 확인.

감사합니다.

— 김정락 / ㈜케이엔케이 대표
