# 📊 작업 진행 추적

> 매 페이지 작업 시작·완료 시 이 파일 갱신.

## 작업 상태 표기
- 🔘 미착수 / 🟡 진행중 / 🟢 완료 / 🔴 차단

## 진행 현황

| 페이지 | 상태 | 시작 | 완료 | 비고 |
|---|---|---|---|---|
| project_detail.html | 🟢 v1 통과 + v2 완료 | 2026-05-10 | 2026-05-10 | REPLY v2 검수 v1 통과 (z40+z42+z41) + v2 차수 (z43 data-dn) 완료. 메인 동기화 완료. push 결재 대기. 다음: v3 (빈 스켈레톤) 또는 sales_orders.html 우선. |
| **(B) 도구** 01B_매출영업_상태확인.bat | 🟢 완료 | 2026-05-10 | 2026-05-10 | 더블클릭 → PROGRESS / 최근 HANDOFF / git log 매출영업만 / git status / P·L·O·G·Q 옵션 메뉴 |
| sales_orders.html | 🟢 v1 통과 + v2 이미 됨 | 2026-05-10 | 2026-05-10 | 진단 결과 data-dn 18 영역 이미 부착(v2 자동 통과). v1 차수 (z44 시안1 토큰 + .mgmt-pill 통일) 완료. v3 빨강 다이어트 보류. |
| sales_home.html | 🔘 | — | — | 시안1 12-col bento 미적용 |
| sales_order_detail.html | 🔘 | — | — | |
| customer_detail.html | 🔘 | — | — | |
| 견적 (4) / 납품수금 (1) / 미수금 (2) | 🔘 | — | — | |
| 소모품 (3) | 🔘 | — | — | |
| 수출입·FTA (11) | 🔘 | — | — | |

## 변경 파일 누적 목록

```
z40 (2026-05-10):
- 01_HAIST_WORKS/app/templates/project_detail.html  (+43줄: ?debug=1 라벨링 + 1100px 반응형)
- KNK_시작.bat                                      (LAST UPDATE z38→z40)
- START.bat                                         (LAST UPDATE z38→z40)

z42 (2026-05-10):
- 01_HAIST_WORKS/app/templates/project_detail.html  (+18줄: PARTS 좌측 첫 3컬럼 sticky)
- KNK_시작.bat                                      (LAST UPDATE z40→z42)
- START.bat                                         (LAST UPDATE z40→z42)

z41 (2026-05-10, D-1 진행 순서로는 z42 다음):
- 01_HAIST_WORKS/app/templates/project_detail.html  (+33줄: 시안1 토큰 11종 + mgmt-pill 컴포넌트 + line 118 잉크 알약)
- KNK_시작.bat                                      (LAST UPDATE z42→z41)
- START.bat                                         (LAST UPDATE z42→z41)

(B) 01B 자체 빠른 확인 도구 (대표 결재 2026-05-10):
- 01B_HAIST_WORKS_매출영업/01B_매출영업_상태확인.bat  (신규, 4.9KB, choice 메뉴)

z43 (2026-05-10, REPLY v2 v2 차수 = data-dn 부착):
- 01_HAIST_WORKS/app/templates/project_detail.html
  · z40 자체 ::before CSS 18줄 + JS 9줄 제거 (partial 시스템 통합)
  · data-dn 속성 6건 부착 (followup-order-modal / detail-grid / main-content / bulk-status-tools / parts-col-toggle / right-rail)
- (메인 BAT 미수정 — REPLY v2 라인 33,170 룰 준수)

메인 폴더 동기화 (옵션 A, 2026-05-10):
- 워크트리 → 메인 KNK업무시스템구축/01_HAIST_WORKS/app/templates/project_detail.html
- 워크트리 → 메인 01B/output/HANDOFF_TO_01_v1~v6.md
- 워크트리 → 메인 01B/PROGRESS.md
- 워크트리 → 메인 01B/01B_매출영업_상태확인.bat

z44 (2026-05-10, sales_orders.html v1 차수):
- 01_HAIST_WORKS/app/templates/sales_orders.html
  · 시안1 토큰 11종 신규 (project_detail z41 과 동일값)
  · .mgmt-pill 컴포넌트 신규 (페이지 간 일관성)
  · SO 리스트 .mgmt-tag 색상 amber #b45309 → 잉크 var(--qv-ink)
  · 임박 납기 .up-r1 .mgmt 색상 amber #b45309 → 잉크 var(--qv-ink)
- 메인 동기화: sales_orders.html + HANDOFF_v7 + PROGRESS
```

## 위험 / 차단 사항
- z11~z19 누적 핫패치 (가로 스크롤·sticky proxy·풀스크린·인라인 편집) → 회귀 위험 큼, 손대기 신중
- inline `style=` 366회 → 토큰화 시 누락 위험

## 빅터 보고 이력
- 2026-05-10 1차 보고: project_detail.html 진단 리포트 v1 (output/HANDOFF_TO_01_v1_진단.md)
- 2026-05-10 2차 보고: z40 핫패치 결과 v2 (output/HANDOFF_TO_01_v2_z40.md) — push 완료 (53d60a9)
- 2026-05-10 3차 보고: z42 핫패치 결과 v3 (output/HANDOFF_TO_01_v3_z42.md) — push 완료 (42f5550)
- 2026-05-10 4차 보고: z41 핫패치 결과 v4 (output/HANDOFF_TO_01_v4_z41.md) — push 결재 대기
- 2026-05-10 5차 보고: (B) 01B 자체 빠른 확인 도구 추가 v5 (output/HANDOFF_TO_01_v5_도구.md) — push 결재 대기
- 2026-05-10 6차 보고: v2 차수 z43 data-dn 부착 v6 (output/HANDOFF_TO_01_v6_data-dn.md) — REPLY v2 v1 통과 + v2 완료. 메인 동기화 완료. push 완료 (dd7f765).
- 2026-05-10 7차 보고: sales_orders.html v1 차수 z44 v7 (output/HANDOFF_TO_01_v7_sales_orders_v1.md) — 토큰 + 잉크 알약 통일. 메인 동기화. push 결재 대기.
