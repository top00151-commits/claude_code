# [01 → 09팀장] JS template literal placeholder 4건 정리 회신

**일시**: 2026-04-25 / **사이클**: 09 발주 → 01 작업 (현재) → 04 회귀 → 00 감사
**처리 방식**: 전체 **#2 aria-label 동적 추가** (시각적 라벨 추가는 도크/모달 좁은 폭 레이아웃 깨짐 우려, 표 헤더 `<th>납기</th>` 이미 존재로 라벨 중복 회피)

## 1. 4 위치별 처리

| # | 파일 | 라인 | placeholder | 추가 aria-label |
|---|------|------|-------------|----------------|
| 1 | `app/templates/base.html` | 519 | `@이름 검색` | `위임 대상자 검색 (@이름)` |
| 2 | `app/templates/base.html` | 522 | `위임 메시지 (선택)` | `위임 메시지 (선택)` |
| 3 | `app/templates/base.html` | 529 | `${I.comment_placeholder}` (i18n) | `${I.comment_placeholder}` (동적 동기) |
| 4 | `app/templates/po_form.html` | 214 | `YYYY-MM-DD` | `납기 (YYYY-MM-DD)` |

## 2. 변경 파일 + 라인 수

- `app/templates/base.html`: 3 lines (placeholder 동일, aria-label 속성 추가)
- `app/templates/po_form.html`: 1 line (aria-label 속성 추가)
- 합계: **2 files / 4 lines**

## 3. BAT 갱신 (LAST UPDATE)

- `KNK_시작.bat:3`: `LAST UPDATE: 2026-04-25 JS-placeholder (aria-label 4건 / base.html 3 + po_form.html 1)` (line 3·7·14 갱신)
- `START.bat:3`: `LAST UPDATE: 2026-04-25 JS-placeholder (aria-label x4 / base.html 3 + po_form.html 1)` (line 3·7·13 갱신)

## 4. 핫패치 G1~G4 grep 결과 (보존 PASS)

```
style.css:3627  핫패치 2026-04-25 17:30 — body.dock-open .topbar { padding-right: 420px } 제거.
style.css:3639  핫패치 2026-04-25 17:30 — top: 0 → top: var(--topbar-h)
base.html:94    핫패치 2026-04-25 17:30 — sb-toggle 화살표 버튼 제거
```
→ **3/3 라인 유지** (grep `핫패치 2026-04-25 17:30` 일치). v2 본체 미접촉. 외부 자산 0건.

## 5. 04 회귀 권고

- 위임 폼 `delegForm` 열기 후 키보드 Tab 진입 시 스크린리더 라벨 읽힘 확인
- 코멘트 textarea 한·영 i18n 전환 시 aria-label도 동기 갱신되는지 확인 (JS `${I.comment_placeholder}` 의존)
- po_form 라인 추가 → `item_delivery` input 포커스 시 `납기 (YYYY-MM-DD)` 읽힘 확인
