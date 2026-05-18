# 📂 changed_templates — 실무팀1 수정본 사본

> **목적:** 실무팀1이 `01_HAIST_WORKS\app\templates\`의 22 페이지를 수정한 **최종본 사본**을 이 폴더에 1:1 복사하여, 대표·빅터가 한 곳에서 검토 가능하도록 함.

## 동작 방식

| 단계 | 행위 |
|---|---|
| 1 | 실무팀1이 `01_HAIST_WORKS\app\templates\home.html` 수정 |
| 2 | 같은 내용을 `01A_HAIST_WORKS_통합플랫폼\changed_templates\home.html` 로 자동 복사 |
| 3 | `output\CHANGES_LOG.md` 에 변경 항목 기록 (시간·내용·라인 변동) |
| 4 | `01A_확인.bat` 메뉴 [3] 으로 폴더 진입 가능 / [4] 로 진행률 확인 |

## 파일 명명 규칙

- 원본 파일명 그대로 (예: `home.html`, `daily.html`)
- 별도 prefix/suffix 없음 — 1:1 매치
- 파일이 존재 = 해당 페이지 시안1 적용 1차 완료 의미

## 빅터 통합 시점

- 실무팀1 22 페이지 모두 완료 (또는 그룹 단위 완료)
- `output\HANDOFF_TO_01_vN.md` 작성하여 변경 파일 목록 명시
- 빅터가 `changed_templates\` 폴더의 사본을 메인 폴더로 통합

## 절대 룰

- 이 폴더 안 파일은 **자동 생성** — 직접 수정 금지
- 직접 수정은 `01_HAIST_WORKS\app\templates\`의 원본만
- 사본은 원본 수정 후 즉시 갱신
