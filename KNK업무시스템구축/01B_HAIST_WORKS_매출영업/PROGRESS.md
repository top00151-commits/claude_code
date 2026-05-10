# 📊 작업 진행 추적

> 매 페이지 작업 시작·완료 시 이 파일 갱신.

## 작업 상태 표기
- 🔘 미착수 / 🟡 진행중 / 🟢 완료 / 🔴 차단

## 진행 현황

| 페이지 | 상태 | 시작 | 완료 | 비고 |
|---|---|---|---|---|
| project_detail.html | 🟡 z40 진행 | 2026-05-10 | — | v1 진단 리포트 + z40 핫패치 적용 (?debug=1 라벨링 + 1100px 반응형). push 결재 대기. 다음: z42 sticky 첫 3컬럼. |
| sales_orders.html | 🔘 | — | — | 발주서 명시 80% 진행됨 |
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
```

## 위험 / 차단 사항
- z11~z19 누적 핫패치 (가로 스크롤·sticky proxy·풀스크린·인라인 편집) → 회귀 위험 큼, 손대기 신중
- inline `style=` 366회 → 토큰화 시 누락 위험

## 빅터 보고 이력
- 2026-05-10 1차 보고: project_detail.html 진단 리포트 v1 (output/HANDOFF_TO_01_v1_진단.md)
- 2026-05-10 2차 보고: z40 핫패치 결과 v2 (output/HANDOFF_TO_01_v2_z40.md) — push 결재 대기
