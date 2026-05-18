# 03-project · 프로젝트 상세

- **컴포넌트**: `ProjectDetail` (in `components-base.jsx`)
- **Sidebar key**: `projects`
- **그리드**: sticky 헤더 + 28컬럼 그룹 토글 표
- **스크린샷**: `screenshots/03-project.png`
- **미리보기**: `preview.html?page=project`

---

## 핵심 — 가장 복잡한 화면

### 헤더
- Mgmt(lg) + 제목 + BizChip + StatusChip
- 거래처 / 납기 / PM / 진행률 bar
- 우측: 인쇄 / 사본 / 결재 / 편집

### PARTS 28컬럼 표 (핵심)
- **그룹 토글** 5개: 기본정보 / 자재 / 공정 / 품질 / 납품
- **sticky 첫 3컬럼**: No / 부품번호 / 부품명
- 행 32 (dense)
- tfoot 합계: 수량/금액/시수
- 미달 셀 var(--danger), 초과 var(--ok)

### 컬럼 (28)
기본(3): No / 부품번호 / 부품명
자재(7): 재질 / 규격 / 단위 / 수량 / 단가 / 금액 / 공급사
공정(6): 공정 / 작업장 / 표준시간 / 실작업 / 작업자 / 상태
품질(5): 검사항목 / 규격 / 측정 / 결과 / 검사자
납품(7): 납품일 / 출고일 / 송장 / 운송 / 수령자 / 인수확인 / 비고

---

## 코드 위치
`design_handoff_haist_works/components-base.jsx` 의 `const ProjectDetail =` 블록을 1:1 참조.

## 검증 체크리스트
- [ ] tokens.css 변수만 사용 (새 색 금지)
- [ ] Pretendard Variable 로드
- [ ] 1440×900 / PageHead 60 / Sidebar 220 / 본문 24px padding
- [ ] screenshots/03-project.png 와 픽셀 비교 → diff 영역만 수정
- [ ] 숫자는 var(--font-mono) 또는 .num
- [ ] 사업부 색상 토큰 (--biz-t/m/e/c)
