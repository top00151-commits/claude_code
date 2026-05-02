# _ARCHIVE_2026-04-29 (보존 자료)

> **보존일**: 2026-04-29
> **결재**: 대표 직접 지시 (옵션 가 — 외부 이동) / 빅터 권고
> **목적**: 활성 코드와 분리된 과거 자산 보존
> **상태**: 🔒 **읽기 전용** — 수정·import 금지

---

## 0. 한 줄

본 폴더는 HAIST WORKS 운영에 사용되지 않는 **과거 보존 자료**. 활성 시스템(`01_HAIST_WORKS/`)과 분리되어 있으며, 어떤 활성 코드에서도 import 되지 않음.

---

## 1. 보관 자료

### 1-1. `_LEGACY_v1_logistics_backup/` (이동: 2026-04-29 12:42)
- **무엇**: HAIST WORKS v1 시절 물류 시스템 백업
- **언제까지 사용**: 2026-04 초중순 (v2 통합 전)
- **왜 보존**: 추후 v1 동작 비교·과거 기능 참고용
- **포함 파일** (총 11개):
  - `app/database.py` — v1 DB 레이어 (일부 함수가 v2 와 호환되지 않음)
  - `app/main.py` — v1 라우트 (현재 시스템과 다름)
  - `app/templates/base.html` — v1 사이드바·헤더 (구버전)
  - `app/templates/base_logi_REMOVED.html` — v1 자재 base (제거된 버전)
  - `app/templates/home.html` — v1 홈
  - `app/templates/parts.html` — v1 부품 마스터
  - `app/templates/part_form.html` — v1 부품 등록 폼
  - `app/templates/projects.html` — v1 프로젝트 목록
  - `app/templates/project_form.html` — v1 프로젝트 폼
  - `static/style.css` — v1 스타일시트
  - `run.py` — v1 단독 실행 스크립트

### 1-2. `_OLD_baby_archive/` (이동: 2026-04-29 22:50)
- **무엇**: 옛 위치 `KNK업무시스템구축/HAIST_WORKS_baby/_archive_~04-24/`
- **상태**: 활성 baby 폴더(`02_HAIST_WORKS_baby/`)로 대체됨
- **이유**: 빈 archive — 이름 중복으로 검색 노이즈 발생
- **메모**: baby Excel 시스템은 web 완료 후 폐기 예정 (대표 정책 2026-04-20)

### 1-3. `_OLD_Research_archive/` (이동: 2026-04-29 22:50)
- **무엇**: 옛 위치 `KNK업무시스템구축/HAIST_WORKS_Research/_archive_~04-24/` + `_TO_09팀장_PlanY_리서치계획.md`
- **상태**: 활성 research 폴더(`03_HAIST_WORKS_Research/`)로 대체됨
- **이유**: 빈 archive — 이름 중복

### 1-4. `_DEPRECATED_카카오워크_금지/` (이동: 2026-04-29 23:00)
- **무엇**: `_GUIDE_카카오워크_Webhook_발급.md`
- **사유**: **대표 직접 지시 — 카카오워크 절대 사용 금지** (2026-04-22)
- **상태**: 본 가이드 더 이상 유효하지 않음. 보관만 (참조 금지)
- **대체 시스템**: 하이웍스 메신저·메일 (또는 시스템 내 알림 — `notify_user()` 헬퍼 사용)

---

## 2. 절대 금지 사항

| 금지 | 이유 |
|---|---|
| ❌ `from _ARCHIVE_2026-04-29.* import` | 활성 시스템에 영향 |
| ❌ 본 폴더 내 코드 수정 | 보존 자료 변형 금지 |
| ❌ `python run.py` 등 실행 | 포트 충돌 / DB 충돌 |

---

## 3. 활성 시스템 위치

현재 운영 중인 코드는:
```
KNK업무시스템구축/01_HAIST_WORKS/
├── app/main.py        (10,540+ 행 — Phase 1 정리됨)
├── app/database.py    (7,800+ 행 — Phase 1 정리됨)
├── app/menu_catalog.py
└── ...
```

자세한 구조: `01_HAIST_WORKS/_INDEX_코드구조.md`

---

## 4. 복원 방법 (필요 시)

만약 v1 시절 어떤 기능이 필요하면:
1. 본 폴더에서 해당 파일 **읽기만** 함
2. 코드 참고하여 활성 시스템(`01_HAIST_WORKS/`)에 **다시 작성**
3. 직접 import·복사하지 말 것 (구조 다름)

---

## 5. 폐기 결재

영구 삭제 시 git history에 남아있으므로 복원 가능:
- 위치: GitHub `top00151-commits/claude_code` 저장소
- 본 폴더 보관 후 6개월 동안 미사용 시 영구 삭제 후보 (대표 결재 필요)

---

*이전: `01_HAIST_WORKS/_LEGACY_v1_logistics_backup/` → `_ARCHIVE_2026-04-29/_LEGACY_v1_logistics_backup/`*
*이전 사유: 활성 코드와 분리 / 검색 노이즈 제거 / 시각적 정리*
*이전자: 빅터 (대표 결재 옵션 가 채택)*
