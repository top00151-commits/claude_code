# 📋 실무팀2 → 빅터(01) 핸드오프 v5 — (B) 01B 자체 빠른 확인 도구

> **발신**: 실무팀2 (매출영업센터)
> **수신**: 빅터 (01 통합실무팀)
> **결재**: 김정락 대표이사 (2026-05-10 명시 결재 (B))
> **작성일**: 2026-05-10
> **이전 보고**: `output/HANDOFF_TO_01_v4_z41.md`

---

## 1. 결재 배경

대표 직접 질문: "매출영업 관련 수정 사항은 01B 파트에서도 수정한걸 내가 직접 볼 수 있는거야?"

빅터 4가지 옵션 보고 → 대표 **(B) "01B 자체에 별도 BAT 같은 빠른 확인 도구"** 결재.

---

## 2. 신규 파일

```
KNK업무시스템구축/01B_HAIST_WORKS_매출영업/01B_매출영업_상태확인.bat  (신규, 4.9KB)
```

## 3. 동작 방식

**더블클릭** → 콘솔 한 화면에 5섹션 한눈에:

| # | 섹션 | 내용 |
|---|---|---|
| 1 | 현재 시스템 버전 | 양파일(`KNK_시작.bat` + `START.bat`) `LAST UPDATE` 라인 |
| 2 | 진행 현황 | `PROGRESS.md` 본문 (페이지별 진행 표) |
| 3 | 빅터 → 대표 보고서 | `output/HANDOFF_TO_01_*.md` 최신순 파일 목록 |
| 4 | git log 매출영업 관련 | 매출영업 30+ 페이지 + `01B_*` 폴더에 한정한 최근 10 커밋 |
| 5 | 미커밋 변경 | `git status -s` (작업 중 파일) |

**옵션 메뉴 5가지** (choice 명령):
| 키 | 동작 |
|---|---|
| **P** | `PROGRESS.md` 메모장 열기 |
| **L** | 최신 `HANDOFF_TO_01_*.md` 메모장 열기 (최신순 자동 선택) |
| **O** | `output/` 폴더 탐색기 열기 |
| **G** | GitHub 브랜치(`claude/charming-yonath-a72046/01B_*`) 페이지 열기 |
| **Q** | 종료 |

## 4. 매출영업 30+ 페이지 git log 필터 — 명시 경로

발주서 작업 범위 7그룹 30+ 페이지 모두 포함 (그룹별 자세히 — BAT 파일 라인 35~58):
- 그룹 A: project_detail.html / projects.html / project_form.html / project_new_chooser.html
- 그룹 A-2: sales_home / sales_dashboard / sales_forecast / sales_production
- 그룹 E: sales_orders / sales_order_detail
- 그룹 D: sales_quotations / sales_quote_detail / sales_quote_form / quotation_print
- 그룹 F: sales_shipments_receipts / sales_outstanding / sales_aging
- 그룹 C: customers_list / customer_detail / customer_form
- 그룹 G: consumables / consumable_detail / consumable_form_upload
- 그룹 H: export_*.html (와일드카드) / fta_*.html (와일드카드)
- + 01B_HAIST_WORKS_매출영업/ 자체 폴더

→ 다른 팀(01A/01C) 변경은 보이지 않음. 매출영업만 격리 표시.

## 5. 검증

### 5-1. 정적 검증
- ✅ 파일 위치: `01B_HAIST_WORKS_매출영업/01B_매출영업_상태확인.bat` (4,964 bytes)
- ✅ `chcp 65001` UTF-8 명시 → 한글 깨짐 방지
- ✅ `cd /d "%~dp0"` → 더블클릭 위치 무관 정상 동작
- ✅ `pushd "%~dp0..\..\"` → worktree 루트 이동 후 git 명령 (worktree 보존)
- ✅ git 명령 실패 시 `2>nul` 으로 silent — BAT 멈추지 않음
- ✅ `choice /c PLOGQ /n` 명시 키만 입력 받음 — 무한 입력 루프 방지

### 5-2. 회귀 위험 점검
| 항목 | 영향 |
|---|---|
| 기존 양파일 BAT | ⭕ 영향 없음 — 본 BAT은 01B 폴더 안 별개 도구 |
| 통합 시스템 실행 (`START.bat`) | ⭕ 영향 없음 |
| 다른 팀 (01A 통합 / 01C 자재) | ⭕ 영향 없음 — 본 BAT은 매출영업만 필터 |
| z40~z42 핫패치 | ⭕ 영향 없음 |

### 5-3. 사용자 안전
- ⭕ destructive 명령 0건 (오직 read-only: findstr / type / dir / git log / git status)
- ⭕ explorer / notepad / start 명령은 사용자 도구 호출 — 시스템 변경 없음
- ⭕ choice 메뉴 없이도 그냥 종료 가능 (Q)

## 6. 한계

- ⚠️ Windows 전용 BAT — Mac/Linux 환경에서는 동작 안 함 (대표 PC Windows 11 확인됨)
- ⚠️ git log 명령은 인터넷 없이도 동작하나, 옵션 G (GitHub 열기)는 인터넷 필요
- ⚠️ 더블클릭으로 실행 시 콘솔창이 새로 뜸 — 메뉴 선택 또는 종료(Q) 시 닫힘

## 7. 다음 단계

(B) 작업은 z41 와 별개 결재였으나, 동일 워크트리·브랜치라 commit 누적 → push 결재 시 함께 origin 반영.

- [ ] **결재 A**: z41 + (B) 도구 git push 일괄 승인
- [ ] **결재 B**: z43 (빨강 다이어트) 진입 시점

빅터 권장:
1. 대표 직접 BAT 더블클릭 → 출력 확인 (5섹션 + 메뉴 동작) → 사용성 피드백
2. push 즉시 + z43 즉시 진입

---

**문의**: `_ORDERS/` 발주서 v2 / `99_DISPATCH/` 채널
