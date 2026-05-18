# 09-inventory · 재고

- **컴포넌트**: `Inventory` (in `components-purchasing.jsx`)
- **Sidebar key**: `stock`
- **그리드**: FilterBar + dense table + StkBar
- **스크린샷**: `screenshots/09-inventory.png`
- **미리보기**: `preview.html?page=inventory`

---

## 핵심 — 안전재고 시각화 (StkBar)

### 헤더
메타 "총 47종 · 본사 38 · 제2 9 · **미달 3종**"
세그: 표/창고맵/이동이력

### FilterBar
창고 / 카테고리 / 상태(미달만 active) / 공급사 / L/T

### 테이블 (12컬럼, 32px)
체크(32 sticky) / 자재코드(120 sticky-2) / 품명 / 분류 / 창고 / **현재고/안전재고 (StkBar 200)** / 단위 / L/T / 공급사 / 단가 / 재고가치 / 최근 이동

### StkBar (핵심)
- h18, bg surface-3, radius 3
- fill = 현재/최대
- 색: <안전×0.5 danger / <안전 warn / 외 ok
- 안전재고 위치: 검정 세로 2px
- 텍스트 "현재 / 안전" mix-blend difference

### tfoot
"합계 12종 · 미달 3 · 진행 4 · 입고 7 · 12,428,000원"

---

## 코드 위치
`design_handoff_haist_works/components-purchasing.jsx` 의 `const Inventory =` 블록을 1:1 참조.

## 검증 체크리스트
- [ ] tokens.css 변수만 사용 (새 색 금지)
- [ ] Pretendard Variable 로드
- [ ] 1440×900 / PageHead 60 / Sidebar 220 / 본문 24px padding
- [ ] screenshots/09-inventory.png 와 픽셀 비교 → diff 영역만 수정
- [ ] 숫자는 var(--font-mono) 또는 .num
- [ ] 사업부 색상 토큰 (--biz-t/m/e/c)
