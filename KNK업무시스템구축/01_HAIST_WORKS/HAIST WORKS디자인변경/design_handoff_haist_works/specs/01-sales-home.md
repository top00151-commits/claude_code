# 01-sales-home · 매출 홈

- **컴포넌트**: `SalesHome` (in `components-base.jsx`)
- **Sidebar key**: `sales-home`
- **그리드**: 12 col × 6 row, gap 16
- **스크린샷**: `screenshots/01-sales-home.png`
- **미리보기**: `preview.html?page=sales-home`

---

## 레이아웃 (1440×900, Sidebar 220 / 본문 1200, PageHead 60)

- crumb "영업" / 제목 "매출 홈" / 우측: 월 세그 + Excel + 신규 수주
- 본문 12-col bento, gap 16

## 영역

| 영역 | col | row | 내용 |
|---|---|---|---|
| KPI×4 (각 3 col) | 1–12 | 1 | 이달 매출 / 수주 잔액 / 평균 ASP / OTD |
| 사업부 도넛 | 1–5 | 2–3 | T/M/E/C 비중 |
| 일별 막대 | 6–12 | 2–3 | 30일, KNK red bar |
| 프로젝트 표 | 1–8 | 4–6 | 5컬럼: 관리번호/사업부/거래처/진행률/상태 |
| 일정 | 9–12 | 4–6 | 오늘·내일·이번주 그룹 |

## KPI 카드
- 높이 120px, padding 20
- value 40px tabular-nums
- trend ↗/↘/→ + 퍼센트
- sparkline 우하단 80×32, opacity 0.6

---

## 코드 위치
`design_handoff_haist_works/components-base.jsx` 의 `const SalesHome =` 블록을 1:1 참조.

## 검증 체크리스트
- [ ] tokens.css 변수만 사용 (새 색 금지)
- [ ] Pretendard Variable 로드
- [ ] 1440×900 / PageHead 60 / Sidebar 220 / 본문 24px padding
- [ ] screenshots/01-sales-home.png 와 픽셀 비교 → diff 영역만 수정
- [ ] 숫자는 var(--font-mono) 또는 .num
- [ ] 사업부 색상 토큰 (--biz-t/m/e/c)
