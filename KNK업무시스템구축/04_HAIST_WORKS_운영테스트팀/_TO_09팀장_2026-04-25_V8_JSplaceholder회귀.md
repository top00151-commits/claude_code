# [04 → 09팀장] V8 JS placeholder 4건 적용 회귀 결과

**일시**: 2026-04-25 / **사이클**: V8 회귀 (01 적용 → 04 회귀 → 00 감사 → 99)
**범위**: base.html 519/522/529, po_form.html 214 + 핫패치 G1~G4 + v2 본체 + BAT
**방식**: Read/Grep 정적 실측 (서버·코드 미접촉)

## 검증 결과 — 5/5 PASS

| # | 항목 | 검증 | 결과 |
|---|------|------|------|
| 1 | base.html 519 | `placeholder="@이름 검색" aria-label="위임 대상자 검색 (@이름)"` 동시 존재 | PASS |
| 2 | base.html 522 | `placeholder="위임 메시지 (선택)" aria-label="위임 메시지 (선택)"` 동시 존재 | PASS |
| 3 | base.html 529 | `placeholder="${I.comment_placeholder}" aria-label="${I.comment_placeholder}"` (i18n 동기) | PASS |
| 4 | po_form.html 214 | `placeholder="YYYY-MM-DD" aria-label="납기 (YYYY-MM-DD)"` 동시 존재 | PASS |
| 5 | 핫패치 G1~G4 보존 | style.css:3627·3639 + base.html:94 grep 3/3 일치 | PASS |

## v2 본체 미변경 (style.css:4269~4574)

- 4269 `.empty { background: var(--sage-50); ... }` 그대로
- 4565~4576 `.topbar .user-info / .user-name / .logout-btn` 그대로
- 4278 `/* C안 (시안 12B 통째 이식) overrides — 2026-04-25 healing-c */` 헤더 보존

## BAT LAST UPDATE 인용

- `KNK_시작.bat:3` → `LAST UPDATE: 2026-04-25 JS-placeholder (aria-label 4건 / base.html 3 + po_form.html 1)`
- `START.bat:3`   → `LAST UPDATE: 2026-04-25 JS-placeholder (aria-label x4 / base.html 3 + po_form.html 1)`
- 양 파일 line 7 title 라인도 `[Updated 2026-04-25 JS-placeholder]` 동기 갱신 확인

## 결론

- placeholder 보존 + aria-label 동시 부착 방식 5/5 PASS, 회귀 부작용 0건
- 99 발사 권고: **가능**

— 04 운영테스트팀
