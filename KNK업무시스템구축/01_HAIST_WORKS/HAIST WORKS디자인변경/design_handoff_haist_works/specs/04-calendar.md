# 04-calendar · 캘린더

- **컴포넌트**: `CalendarPage` (in `components-base.jsx`)
- **Sidebar key**: `calendar`
- **그리드**: 좌 240 미니캘 / 우 풀월간
- **스크린샷**: `screenshots/04-calendar.png`
- **미리보기**: `preview.html?page=calendar`

---

## 레이아웃
- 좌 240: 미니 캘린더 + 분류 필터 + 범례
- 우: 풀 월간 (7×6)

## 미니 캘린더
- 220 width, 셀 28×28
- 오늘: KNK red 채움
- 일정 있는 날: 하단 dot 4×4 (사업부 색)

## 분류 필터
- 내/팀/회사/외부 일정
- 체크박스 + 색 dot

## 범례
- 사업부 4종 dot + 라벨

---

## 코드 위치
`design_handoff_haist_works/components-base.jsx` 의 `const CalendarPage =` 블록을 1:1 참조.

## 검증 체크리스트
- [ ] tokens.css 변수만 사용 (새 색 금지)
- [ ] Pretendard Variable 로드
- [ ] 1440×900 / PageHead 60 / Sidebar 220 / 본문 24px padding
- [ ] screenshots/04-calendar.png 와 픽셀 비교 → diff 영역만 수정
- [ ] 숫자는 var(--font-mono) 또는 .num
- [ ] 사업부 색상 토큰 (--biz-t/m/e/c)
