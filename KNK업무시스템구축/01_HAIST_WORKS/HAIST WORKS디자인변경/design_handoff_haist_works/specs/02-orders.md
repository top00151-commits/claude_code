# 02-orders · 수주 관리

- **컴포넌트**: `OrdersPage` (in `components-base.jsx`)
- **Sidebar key**: `orders`
- **그리드**: 좌 캘린더 1fr / 우 360 일정
- **스크린샷**: `screenshots/02-orders.png`
- **미리보기**: `preview.html?page=orders`

---

## 레이아웃
- 좌: 풀 월간 (요일 헤더 + 7×6)
- 우: 360 일정 패널 (필터 + 그룹 리스트)

## 캘린더 셀
- 7×6, min-height 110
- 오늘: 좌상 KNK red dot 6×6
- 일정 칩: h18, padding 0 6, font 11, 좌측 사업부 stripe 2px
- 셀당 최대 3개, 초과 "+N more"

## 우측 패널
- 헤더 "일정" + 필터 칩 (전체/수주/납기/회의)
- 그룹: 오늘/내일/이번 주/다음 주
- 카드: 시간 + 제목 + BizChip + Mgmt

---

## 코드 위치
`design_handoff_haist_works/components-base.jsx` 의 `const OrdersPage =` 블록을 1:1 참조.

## 검증 체크리스트
- [ ] tokens.css 변수만 사용 (새 색 금지)
- [ ] Pretendard Variable 로드
- [ ] 1440×900 / PageHead 60 / Sidebar 220 / 본문 24px padding
- [ ] screenshots/02-orders.png 와 픽셀 비교 → diff 영역만 수정
- [ ] 숫자는 var(--font-mono) 또는 .num
- [ ] 사업부 색상 토큰 (--biz-t/m/e/c)
