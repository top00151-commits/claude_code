# 08-bom · BOM·소요량

- **컴포넌트**: `BOMExplosion` (in `components-purchasing.jsx`)
- **Sidebar key**: `bom`
- **그리드**: 좌 260 트리 / 우 BOM 전개
- **스크린샷**: `screenshots/08-bom.png`
- **미리보기**: `preview.html?page=bom`

---

## 레이아웃
- 좌 260: 진행 프로젝트 5건 (active KNK red border-left 3px)
- 우: BOM 전개 표 + 하단 액션바

## BOM 표 (커스텀 grid)
- columns: 24px 280px 90px 80px 80px 80px 90px 100px 120px
- 9컬럼: 토글 / 품목 / 품번 / EA당 / 총소요 / 가용재고 / 부족 / 액션 / 공급사

### 들여쓰기
- lv 0: surface-3, 700 (Assy)
- lv 1: surface-2, 600
- lv 2: 평문
- "  ".repeat(lv) 모노 들여쓰기

### 부족 색
- "-N" danger / "+N" ok / "0" ink-3

### 액션
- "● 부족 → 발주" danger
- "● 발주 필요" warn
- "● 충당 가능" ok

## 하단 액션 바
"발주 필요 12종 · 2,840만원 · L/T 6일 · D-8" + [→ 일괄 PO 생성]

---

## 코드 위치
`design_handoff_haist_works/components-purchasing.jsx` 의 `const BOMExplosion =` 블록을 1:1 참조.

## 검증 체크리스트
- [ ] tokens.css 변수만 사용 (새 색 금지)
- [ ] Pretendard Variable 로드
- [ ] 1440×900 / PageHead 60 / Sidebar 220 / 본문 24px padding
- [ ] screenshots/08-bom.png 와 픽셀 비교 → diff 영역만 수정
- [ ] 숫자는 var(--font-mono) 또는 .num
- [ ] 사업부 색상 토큰 (--biz-t/m/e/c)
