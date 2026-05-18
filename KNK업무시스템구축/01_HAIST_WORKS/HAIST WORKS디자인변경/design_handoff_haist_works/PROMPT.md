# Claude Code 핸드오프 — HAIST WORKS · 시안1

## 사용법
이 폴더를 Claude Code 세션에 통째로 첨부하고 아래 지시문을 그대로 붙여넣으세요.

---

당신은 우리 ERP 코드베이스에 시안1 디자인을 구현한다. 이 폴더는 디자이너의 **확정된** 산출물이며, 픽셀 기준이다.

## 절대 규칙

1. **screenshots/*.png 가 정답이다.**
   - 모든 화면 1440×900 고정.
   - 코드 작성마다 해당 PNG와 픽셀 비교. 폰트 굵기/색/간격/숫자/문구까지 동일하게.

2. **tokens.css 그대로 가져간다.**
   - 새 색·간격 만들지 않는다 — 토큰에 없으면 디자이너 확인.
   - Pretendard Variable 필수.

3. **components-base.jsx / components-purchasing.jsx 의 코드를 1:1로 옮긴다.**
   - 클래스명(.btn .kpi .tbl .chip .seg .filterbar) 동일.
   - 메뉴 항목·이모지·뱃지·문구·숫자 모두 그대로.

4. **specs/<key>.md 를 먼저 읽고 코딩한다.**
   - 컬럼 폭·KPI 개수·정확한 문구·그리드가 명시. 임의 결정 금지.

5. **검증 (PR 단위)**
   - 1440×900 캡처 → screenshots/<key>.png 와 나란히 비교 → diff 영역만 수정.
   - 전체 재작성 금지.

## 우선순위
1. tokens.css + Pretendard
2. 공통(TopBar/Sidebar/PageHead/Mgmt/Chip/KPI/Tbl/Seg/FilterBar)
3. 매출 홈
4. 프로젝트 상세 (28컬럼 sticky — 가장 어려움)
5. 발주 관리 / BOM / 재고
6. 나머지

## 폴더
- tokens.css — 그대로 import
- components-base.jsx (1162줄) — 공통 + 영업·생산 5화면
- components-purchasing.jsx (770줄) — 구매·자재 6화면
- preview.html?page=KEY — 단독 미리보기
- screenshots/NN-key.png — 픽셀 기준
- specs/NN-key.md — 화면별 명세
- INDEX.md — 화면 목록

## 첫 출력 시 다음 확인:
- 어떤 프레임워크로 구현하는지
- tokens.css 를 어디 둘지
- Sidebar 키와 라우터 매핑
