# 06-purchase-home · 구매 홈

- **컴포넌트**: `PurchaseHome` (in `components-purchasing.jsx`)
- **Sidebar key**: `po-home`
- **그리드**: 12-col, KPI 6 + 발주흐름 + 입고임박 + 부족알림
- **스크린샷**: `screenshots/06-purchase-home.png`
- **미리보기**: `preview.html?page=purchase-home`

---

## 레이아웃 12-col

| 영역 | col | row |
|---|---|---|
| KPI×6 (각 2 col) | 1–12 | 1 |
| 발주 흐름 (7단계) | 1–7 | 2 |
| 사업부 비교 | 8–12 | 2 |
| 입고 임박 D-3 | 1–7 | 3 |
| 안전재고 미달 (3건) | 8–12 | 3 |

## KPI 6장
1. 이달 발주액 3.62억 (+8.2%)
2. 진행 발주 18건
3. 이번 주 입고 7건
4. **납기 지연 2건** (KNK red 카드)
5. 안전재고 미달 3품목
6. 공급사 OTD 94.2%

## 발주 흐름 7단계
품의/승인/발주/부분입고/입고완료/검수/종결
각 단계 막대 위 건수, 아래 금액

## 사업부 비교
- T/M/E/C 4행
- 채움 막대 = 구매 비중, 검정 라인 = 매출 비중
- "해석" 박스

## 안전재고 미달 카드 (우)
- 빨간 배경
- StkBar (현재/안전/최대)
- 사용중 프로젝트 표시

---

## 코드 위치
`design_handoff_haist_works/components-purchasing.jsx` 의 `const PurchaseHome =` 블록을 1:1 참조.

## 검증 체크리스트
- [ ] tokens.css 변수만 사용 (새 색 금지)
- [ ] Pretendard Variable 로드
- [ ] 1440×900 / PageHead 60 / Sidebar 220 / 본문 24px padding
- [ ] screenshots/06-purchase-home.png 와 픽셀 비교 → diff 영역만 수정
- [ ] 숫자는 var(--font-mono) 또는 .num
- [ ] 사업부 색상 토큰 (--biz-t/m/e/c)
