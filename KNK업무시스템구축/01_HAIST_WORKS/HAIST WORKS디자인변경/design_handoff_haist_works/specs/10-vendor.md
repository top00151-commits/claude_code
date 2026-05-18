# 10-vendor · 공급사 관리

- **컴포넌트**: `VendorMgmt` (in `components-purchasing.jsx`)
- **Sidebar key**: `vendor`
- **그리드**: FilterBar + 2-col 스코어카드
- **스크린샷**: `screenshots/10-vendor.png`
- **미리보기**: `preview.html?page=vendor`

---

## 레이아웃 — 스코어카드 (표 아님)

### 헤더
메타 "47개 · 활성 32 · 전략 5 · **단일소스 3**"

### FilterBar
등급(전략·주력 active) / 카테고리 / OTD<90% / 리스크high(active)

### 카드 (2-col grid, gap 12)
- **로고 박스** 42×42 검정, 회사명 첫 2글자 흰색
- 우측:
  - 코드 Mgmt + 등급 chip (전략=검정/주력=info/단일=warn/일반=grey) + 카테고리
  - 회사명 15px 700
  - 4-col 메트릭: OTD/품질/거래액/L/T (각 셀 surface-2, padding 6 8, radius 5)
  - 라벨 9.5px ink-3, 값 14px 700
  - OTD 색: ≥95 ok / ≥90 ink / 미만 danger
- risk_note: 빨간 박스 ("OTD 78% · 지연 3건")
- risk=high: 카드 bg danger-soft + KNK red 보더

### 하단 합계
"거래액 X.X억 · 발주 N건 · OTD 평균 92.8% · 평가 분기 1회"

---

## 코드 위치
`design_handoff_haist_works/components-purchasing.jsx` 의 `const VendorMgmt =` 블록을 1:1 참조.

## 검증 체크리스트
- [ ] tokens.css 변수만 사용 (새 색 금지)
- [ ] Pretendard Variable 로드
- [ ] 1440×900 / PageHead 60 / Sidebar 220 / 본문 24px padding
- [ ] screenshots/10-vendor.png 와 픽셀 비교 → diff 영역만 수정
- [ ] 숫자는 var(--font-mono) 또는 .num
- [ ] 사업부 색상 토큰 (--biz-t/m/e/c)
