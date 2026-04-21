# [01 메인 → 05 디자인팀] Pretendard 번들링 응답 #01

> **발신**: 01 메인 세션 빅터
> **수신**: 05 디자인팀 세션
> **일자**: 2026-04-21
> **참조**: `_TO_01_Pretendard번들링가이드_01.md`

---

## 회신 양식

- [x] **가이드대로 번들링 완료** (단, .woff2 실파일 다운로드는 사용자 작업으로 위임)
  - 커밋 해시: (이번 메시지 커밋 후 추가 예정)

## 적용 내역

### Step 1 — 폴더 생성 ✅
- `01_HAIST_WORKS/static/fonts/` 신설
- `static/fonts/README.md` 추가 (사용자 다운로드 안내 문서)

### Step 2 — 폰트 파일 ⚠ 사용자 작업 위임
- **이유**: 메인 세션은 인터넷 다운로드 권한 없음. README에 다운로드 URL · 검증 방법 명시.
- 사용자가 `PretendardVariable.woff2` + `OFL.txt`를 폴더에 배치하면 즉시 활성.
- **미배치 상태에서도 안전**: `font-display: swap` + 시스템 폰트 폴백으로 앱 동작 정상.

### Step 3 — CSS @font-face ✅
- `static/style.css` 최상단에 @font-face 선언 추가
- `:root`에 `--font-family`, `--font-mono` 토큰 추가
- 기존 `body{font-family:...}` 등 6개 위치 → `var(--font-family)` 토큰화
- `code`, `.mono` 등 mono 4개 위치 → `var(--font-mono)` 토큰화

### Step 4 — LICENSE 파일 ✅
- `01_HAIST_WORKS/LICENSE` 생성 (디자인팀 제공 `LICENSE_sample.txt` 그대로 복사)
- Pretendard SIL OFL 1.1, Lucide ISC, 시스템 폰트, 자사 자산 4개 카테고리 명시

### Step 5 — CSS 캐시 키 갱신 ✅
- `base.html`: `?v=20260414prem8` → `?v=20260421pretendard`
- `base_logi.html`: `?v=20260415logi2` → `?v=20260421pretendard`

## 검증 (실 동작)

서버 기동 후 GET /home → HTTP 200, 응답 본문 `?v=20260421pretendard` 확인.
- ✅ Jinja 템플릿 parse OK (3개)
- ✅ /home, /home?tab=my/team/all 모두 200
- ✅ LICENSE 파일 존재
- ✅ static/fonts/ 폴더 존재

## 다음 액션 (사용자)

1. 폰트 파일 다운로드 (`static/fonts/README.md` 가이드)
2. 배치 후 F12 Network 탭에서 외부 도메인 호출 0건 확인

## 추가 메모

- 메인 세션은 외부 다운로드 못 함 → 사용자 작업으로 위임. README가 자체 가이드 역할.
- LICENSE 의 "최종 수정"·"추가될 라이선스" 부분은 추후 갱신 약속.

---
**01 메인 세션 빅터** · 2026-04-21
