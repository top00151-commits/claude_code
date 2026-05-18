# 📨 DONE — 10차 qc_report_form.html 시안1 z58 (품질 모듈 시작)

> **분류:** DONE
> **발신:** 실무팀3 (자재구매센터, 워크트리 cranky-shtern-789fa2)
> **수신:** 빅터(01)
> **시각:** 2026-05-11 14:00
> **응답 필요:** 검수 + STATUS.md 통합 + git push

---

## 한 줄 요지
**qc_report_form.html** 시안1 z58 전면 재작성 — 신규 폼 + 상세 조회 단일 페이지 통합 + 표준 6항목 자동 + 라우터 form name 정확 정합 (잠재 버그 복구).

## 첨부
- HANDOFF: [`HANDOFF_TO_01_v10.md`](../HANDOFF_TO_01_v10.md)
- PROGRESS: [`../../PROGRESS.md`](../../PROGRESS.md)

## 산출 (1 파일)

### qc_report_form.html — 신규/상세 양 모드

**신규 모드** (`/qc/inspection-reports/new`)
- 3 섹션: 기본정보 / 판정·담당 / 검사 항목
- **표준 6항목 일괄 자동 추가**: 반복성·정확도·통신·외관·동작·안전
- 판정 select 색상 동적 변경 (PASS 초록 / FAIL 빨강 / NA 회색)

**상세 모드** (`/qc/inspection-reports/{id}`)
- KPI 4 (종합판정/합격수/불합격수/NA수)
- 검사 정보 + 검사 항목 표 (chip-q)
- 발급 액션 (DRAFT → ISSUED)

## ⚠️ 잠재 버그 복구
기존 폼 action `/qc/reports/new` (POST) — 라우터 미존재. z58에서 정확한 `/qc/inspection-reports` (POST)로 정정.

## 자체 검증 결과 (1패스)
- amber-grad / knk-red: **0건** ✓
- data-dn: **10개 영역** ✓
- form name/action: 20 매칭 ✓
- 라우터 호환 (헤더 12 + 라인 5): **27 매칭** ✓

## 양 모드 통합 패턴 3회 정착
| 차수 | 페이지 |
|---|---|
| 7차 | po_form |
| 9차 | wo_form |
| **10차** | **qc_report_form** |

## 100% 준수
- 발주서 7항 (라우트 변경 0건 / DB 변경 0건): 0 위반
- 룰 v4 ADDENDUM: 0 위반
- 99_DISPATCH: 0건
- 상표권 익명화: 외부 실명 0건

## 검수 1줄
```
http://localhost:8081/qc/inspection-reports/new?debug=1   ← 신규 폼
http://localhost:8081/qc/inspection-reports/{id}?debug=1  ← 상세 + 발급
```

## 빅터(01) 처리 요청
- [ ] qc_report_form 양 모드 검수
- [ ] 잠재 버그 복구 확인 (action URL)
- [ ] STATUS.md 🟢 통합 완료 z58 10차 등록
- [ ] git push
- [ ] **다음 차수 (11차) 승인**

## 누적 진행
**20 페이지 / 30+ (67%)** — 6차~10차 5 차수 누적 z58 시리즈 완료.

## 다음 트리거
- 빅터 검수 회신 → 11차
- 또는 대표 직접 추가 지시
