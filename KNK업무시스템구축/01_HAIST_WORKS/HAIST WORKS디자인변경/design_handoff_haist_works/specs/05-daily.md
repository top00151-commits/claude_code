# 05-daily · 일일 업무

- **컴포넌트**: `DailyWork` (in `components-base.jsx`)
- **Sidebar key**: `daily`
- **그리드**: 5 KPI / 업무리스트 + 시간표
- **스크린샷**: `screenshots/05-daily.png`
- **미리보기**: `preview.html?page=daily`

---

## 레이아웃
- 상: KPI 5 (오늘 일정 / 결재 / 미팅 / 마감 임박 / 내 업무)
- 본문: 좌 업무 리스트 / 우 시간표 (08:00–20:00)

## 업무 리스트
- 그룹: 오늘 마감 / 진행중 / 시작 전 / 완료
- 카드: 제목 + Mgmt + BizChip + 우선순위 dot + 마감일
- 체크박스

## 시간표
- 12시간, 30분 단위
- 일정 블록: 좌측 stripe + 제목 + 시간

---

## 코드 위치
`design_handoff_haist_works/components-base.jsx` 의 `const DailyWork =` 블록을 1:1 참조.

## 검증 체크리스트
- [ ] tokens.css 변수만 사용 (새 색 금지)
- [ ] Pretendard Variable 로드
- [ ] 1440×900 / PageHead 60 / Sidebar 220 / 본문 24px padding
- [ ] screenshots/05-daily.png 와 픽셀 비교 → diff 영역만 수정
- [ ] 숫자는 var(--font-mono) 또는 .num
- [ ] 사업부 색상 토큰 (--biz-t/m/e/c)
