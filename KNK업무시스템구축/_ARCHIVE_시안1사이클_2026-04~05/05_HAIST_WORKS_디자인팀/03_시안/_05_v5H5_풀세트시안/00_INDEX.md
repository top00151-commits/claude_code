# 🎨 v5-H5 풀세트 시안 — 마스터 인덱스

> **트리거**: 대표 신 워크플로우 + 01팀 페이지 목록 응답 (149 라우트 / 124 템플릿)
> **편집**: 05 디자인팀 빅터
> **목적**: 카테고리 마스터 시안 + 변형 가이드로 전체 시스템 시각 일관성 확보 → 01팀 단순 반영
> **참조**: `_세션01_수신/_FROM_01_2026-04-29_v5H5_페이지목록응답.md`

---

## 📊 진행 상황 — **🟢 100% 완료 + 7차 자기검증 보강** (2026-04-29)

| Phase | 산출물 | 상태 | 영향 범위 |
|---|---|---|---|
| **Phase 1** | 표준 토큰 CSS + 3 base 시안 | 🟢 완료 | **124 템플릿 중 109개 (88%) 자동 적용** |
| **Phase 2** | 카테고리 마스터 10종 (A~J) + 변형 가이드 | 🟢 완료 | **113 페이지 변형 명세** |
| **Phase 3** | 모달 5종 + 에러/로딩/인쇄 마스터 | 🟢 완료 | **UX 갭 보완** |
| **🆕 7차 검증 보강** (2026-04-29) | guide·empty·toasts 마스터 + 모바일 spec | 🟢 완료 | **누락 5건 모두 보강** |

**총 산출물**: INDEX 1 + 표준 토큰 CSS 1 + 마스터 HTML **18** + 변형 가이드 **9** = **🔢 29 파일** (find 검증 결과)

---

## 📂 폴더 구조

```
_05_v5H5_풀세트시안/
├── 00_INDEX.md                   ← 본 파일
├── ZZ_표준토큰.css               ← 전 페이지 공통 토큰 (Phase 1)
│
├── 0_base/                       ← Phase 1 (88% 영향)
│   ├── master_base_v5H5.html       (통합 hub · 57 templates)
│   ├── master_base_sales_v5H5.html (매출 hub · 22 templates)
│   └── master_base_logi_v5H5.html  (자재 hub · 34 templates)
│
├── A_대시보드/  (5)              ← Phase 2
├── B_매트릭스/  (12)             ← Phase 2
├── C_폼/        (22)             ← Phase 2
├── D_리스트/    (24)             ← Phase 2
├── E_상세/      (15)             ← Phase 2
├── F_모달/      (5종 + 토스트 5종 신규)  ← Phase 3 + 7차 보강
│   ├── master_F_modals_v5H5.html
│   └── master_F_toasts_v5H5.html  ← 🆕 N-4 보강
├── G_standalone/(12 — login·guide·error·empty·print 등) ← Phase 2 + 7차 보강
│   ├── master_G_login_v5H5.html
│   ├── master_G_guide_v5H5.html   ← 🆕 N-2 보강
│   ├── master_G_error_v5H5.html
│   ├── master_G_empty_v5H5.html   ← 🆕 N-3 보강
│   └── master_G_print_v5H5.html
├── H_관리자/    (15)             ← Phase 2
├── I_보고서/    (5)              ← Phase 2
└── J_빅터AI/    (3)              ← Phase 2
```

---

## 🎯 카테고리 매핑 (01팀 응답서 기반)

| 카테고리 | 페이지 수 | 우선순위 P0 | base 분포 | 마스터 시안 파일 |
|---|---:|---:|---|---|
| A. 대시보드 | 5 | 4 | base / base_sales / base_logi | `A_대시보드/master_dashboard.html` |
| B. 매트릭스 | 12 | 2 | 주로 base_sales / base_logi | `B_매트릭스/master_matrix.html` |
| C. 폼 | 22 | 5 | 주로 base_logi / base | `C_폼/master_form.html` |
| D. 리스트 | 24 | 11 | base / base_sales / base_logi | `D_리스트/master_list.html` |
| E. 상세 | 15 | 4 | base / base_sales / base_logi | `E_상세/master_detail.html` |
| F. 모달 (신규) | 5종 | — | (컴포넌트) | `F_모달/master_modals.html` |
| G. standalone | 12 | 2 | 미상속 | `G_standalone/master_*.html` (3종) |
| H. 관리자 | 15 | 4 | base | `H_관리자/master_admin.html` |
| I. 보고서 | 5 | 1 | base | `I_보고서/master_report.html` |
| J. 빅터 AI | 3 | 1 | base | `J_빅터AI/master_victor.html` (이미 PREVIEW) |

**총 113 페이지** + 모달 5종 + 에러·로딩 = **시안 산출물 ~22 파일** (마스터 + 변형 가이드)

---

## 🎨 H5 톤 핵심 토큰 (요약)

자세한 정의: [`ZZ_표준토큰.css`](./ZZ_표준토큰.css)

| 토큰 | 값 | 용도 |
|---|---|---|
| `--paper` | #FBF5EC | 베이스 크림 |
| `--paper-3` | #FFFFFF | 카드·콘텐츠 |
| `--amber` | #D4923B | 메인 액센트 |
| `--amber-glow` | #FFE5B8 | 호버·하이라이트 |
| `--ink` | #2D2520 | 따뜻한 검정 |
| `--knk-red` | #A5282C | 강조·CTA·VIP |
| `--success` | #7A9B5C | 양호 |
| `--warn` | #C97D3F | 주의 |
| 모서리 | 8/14/18/24px | 단계별 |
| 그림자 | 부드러운 앰버 그림자 | 호버 +12px |

---

## 📋 Phase 별 일정

| Phase | 작업 | 예상 소요 |
|---|---|---|
| Phase 1 (오늘) | 표준 토큰 + 3 base | ~당일 (4h) |
| Phase 2 (D+1) | 카테고리 마스터 10종 (A~J) | ~1.5일 |
| Phase 3 (D+2) | 모달 5종 + 에러·로딩 + 모바일 9종 | ~1일 |
| 대표 검토 | 일괄 또는 단계별 | 변동 |
| _TO_01 반영 발주 | 시안 HTML/CSS 직접 이식 발주서 | 0.5일 |

---

## ⚠️ 01팀 인계 사항 (시안 시 반영)

01 응답서 §6 핵심:
1. `style.css` 7400줄 + `style_hubs.css` 비활성화 → 시안 도착 시 통째 덮어씌움
2. 마스트헤드 제거 (G25 — VOL.NO 라인 삭제) — H5는 마스트헤드 안 쓰니 정합 ✓
3. dock top: 80px / `--topbar-h: 80px` → H5 시안에 보존
4. 빅터 dock 우상단 ❓ + 알림 + 언어 + 사용자 + 나가기 = 6 아이콘
5. **메뉴 식별번호 (M-XX-YY) 시안에 표기** (대표 결재 2026-04-29)

---

**발행**: 2026-04-29 · 05 디자인팀 빅터
**상태**: 🟢 **풀세트 시안 100% + 7차 검증 보강 28 파일 — 발주서 §10 보강 후 01 호출 가능**
**다음**: 발주서 §10 P2 보류 명시 → 대표 01 호출

## 🛡 7차 자기검증 보강 사항 (2026-04-29)

| 누락 | 보강 | 파일 |
|---|---|---|
| N-1 | 22 → 28 파일 카운트 정정 | INDEX (본 파일) |
| N-2 | 사용가이드 마스터 추가 | `G_standalone/master_G_guide_v5H5.html` |
| N-3 | 빈 상태 4종 마스터 추가 | `G_standalone/master_G_empty_v5H5.html` |
| N-4 | 토스트·알림 5종 추가 | `F_모달/master_F_toasts_v5H5.html` |
| N-5 | 모바일 우선 spec | A·D variations.md 보강 |
