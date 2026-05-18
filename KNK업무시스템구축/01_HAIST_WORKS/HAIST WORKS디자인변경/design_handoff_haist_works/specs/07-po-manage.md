# 07-po-manage · 발주 관리

- **컴포넌트**: `POManage` (in `components-purchasing.jsx`)
- **Sidebar key**: `po`
- **그리드**: FilterBar + 8 KPI + sticky 2컬럼 + 합계 tfoot
- **스크린샷**: `screenshots/07-po-manage.png`
- **미리보기**: `preview.html?page=po-manage`

---

## 핵심 — ERP-grade 발주 표

### 헤더
- 메타 "전체 38건 · 진행 18 · 완료 17 · **지연 2**"
- 액션: 표/칸반/분석 세그 + Excel + 신규 발주

### FilterBar
- 칩: 발주일(active) / 상태 / 사업부 / 공급사 / 담당자 / 금액 / 긴급만
- 검색 200 min-width
- 우측 결과 카운트

### KPI Strip (8개)
진행 발주 / 이번달 발주액 / 평균 단가 / 평균 리드타임 / OTD / 긴급 / 승인 대기 / 미입고 잔액

### 테이블 (32px row)
- 14컬럼: 체크(32 sticky) / 발주번호(104 sticky-2) / 발주일 / 사업부 / 공급사 / **품명** / 프로젝트 / 수량 / 단가 / 금액 / 납기 / L/T / 상태 / 담당
- min-width 1400
- 짝수 zebra
- 긴급/지연 행: var(--danger-soft)
- POChip 8종

### tfoot
"합계 (12건)" + 평균 + 총액 + "지연 2 · 미입고 14" — border-top 2px ink, sticky bottom

---

## 코드 위치
`design_handoff_haist_works/components-purchasing.jsx` 의 `const POManage =` 블록을 1:1 참조.

## 검증 체크리스트
- [ ] tokens.css 변수만 사용 (새 색 금지)
- [ ] Pretendard Variable 로드
- [ ] 1440×900 / PageHead 60 / Sidebar 220 / 본문 24px padding
- [ ] screenshots/07-po-manage.png 와 픽셀 비교 → diff 영역만 수정
- [ ] 숫자는 var(--font-mono) 또는 .num
- [ ] 사업부 색상 토큰 (--biz-t/m/e/c)
