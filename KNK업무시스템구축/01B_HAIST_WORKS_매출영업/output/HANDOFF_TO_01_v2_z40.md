# 📋 실무팀2 → 빅터(01) 핸드오프 v2 — z40 핫패치 결과

> **발신**: 실무팀2 (매출영업센터)
> **수신**: 빅터 (01 통합실무팀)
> **결재**: 김정락 대표이사
> **작성일**: 2026-05-10
> **버전**: v5H226z39 → **v5H226z40**
> **이전 보고**: `output/HANDOFF_TO_01_v1_진단.md`

---

## 1. 적용 범위

**z40 = 갭 4 + 갭 5 동시 적용** (D-1 결재 1순위, 저위험·고가치)

| 갭 | 내용 | 상태 |
|---|---|---|
| 4 | `?debug=1` 영역 라벨링 | ✅ 적용 |
| 5 | 1100px 이하 반응형 | ✅ 적용 |

---

## 2. 변경 파일 (3건)

```
- KNK업무시스템구축/01_HAIST_WORKS/app/templates/project_detail.html  (+43줄)
- KNK업무시스템구축/KNK_시작.bat                                       (LAST UPDATE → z40)
- KNK업무시스템구축/START.bat                                          (LAST UPDATE → z40)
```

(신규 파일 — 01B 자체 폴더)
```
- KNK업무시스템구축/01B_HAIST_WORKS_매출영업/PROGRESS.md
- KNK업무시스템구축/01B_HAIST_WORKS_매출영업/output/HANDOFF_TO_01_v1_진단.md
- KNK업무시스템구축/01B_HAIST_WORKS_매출영업/output/HANDOFF_TO_01_v2_z40.md  ← 본 문서
```

---

## 3. 변경 상세

### 3-1. `?debug=1` 영역 라벨링 (갭 4)

`project_detail.html` 라인 109~141 신규 CSS:

```css
/* v5H226z40: ?debug=1 영역 라벨링 — 디버그 모드 4구역 시각화 */
body.debug-on .page-head,
body.debug-on .detail-grid > :first-child,
body.debug-on .so-card,
body.debug-on .so-units-wrapper { position: relative; outline: 2px dashed rgba(176,122,24,0.55); outline-offset: -2px; }
body.debug-on .page-head::before          { content: "📦 PAGE-HEAD";    background: rgba(176,122,24,0.85); }
body.debug-on .detail-grid > :first-child::before { content: "📋 MAIN-CONTENT"; background: rgba(30,58,138,0.85); }
body.debug-on .so-card::before            { content: "🧾 SO-CARD";      background: rgba(6,95,70,0.85); }
body.debug-on .so-units-wrapper::before   { content: "📊 PARTS-TABLE";  background: rgba(124,58,237,0.85); }
```

JS — body 닫기 직전 (라인 ~2440):
```js
(function(){
  try {
    if (new URLSearchParams(location.search).get('debug') === '1') {
      document.body.classList.add('debug-on');
    }
  } catch(e){}
})();
```

**활성 방법**: URL 끝에 `?debug=1` 추가 (예: `/project/123?debug=1`)
**해제**: `?debug=1` 제거 또는 `?debug=0`

### 3-2. 1100px 이하 반응형 (갭 5)

`project_detail.html` 라인 110~123 신규 CSS:

```css
@media (max-width: 1100px) {
  .detail-grid { gap: var(--space-3); }
  .page-head { padding-block: 10px; }
  .page-title { font-size: 18px !important; gap: 8px !important; }
  .so-meta { gap: 4px 10px !important; flex-wrap: wrap; }
  .parts-col-toggle { padding: 6px 8px; gap: 4px; font-size: 11px; }
  .parts-col-toggle button { padding: 2px 8px; font-size: 10.5px; }
  .parts-col-toggle .lbl { width: 100%; }
  .so-actions { flex-wrap: wrap; gap: 6px; }
  .def { grid-template-columns: 80px 1fr; font-size: 12.5px; gap: 6px 10px; }
  .section-card { padding: var(--space-4); }
}
```

**효과**:
- 14인치 노트북(1366px) 이하 환경에서 page-title 줄어듦, SO 메타 줄바꿈
- PARTS 컬럼 chip 토글 wrap 가능, 라벨 단독 줄
- SO 버튼 그룹 wrap, def-list 100→80px
- section-card padding 축소

---

## 4. 검증

### 4-1. 정적 검증
- ✅ `python -m py_compile` 대상 아님 (HTML+JS)
- ✅ inline `style=` 366회 → 변동 없음 (z40은 신규 추가만)
- ✅ `_v5_partials/` 미접촉
- ✅ `main.py` 라우트 미접촉
- ✅ DB 스키마 미접촉
- ✅ PARTS 28컬럼 백엔드 (`_parse_packing_list_xlsx`) 미접촉

### 4-2. 회귀 위험 점검
| 항목 | 영향 |
|---|---|
| z11~z19 누적 핫패치 (가로 스크롤·sticky proxy·풀스크린·인라인 편집) | ⭕ 영향 없음 — z40은 추가만, 기존 CSS 미수정 |
| 호기 일괄 상태 / 추가 발주 모달 / 엑셀 업로드 | ⭕ 영향 없음 |
| `?debug=1` 라벨이 일반 사용자에게 노출 | ⭕ 영향 없음 — `body.debug-on` 클래스 없으면 비활성 |

### 4-3. BAT 갱신 검증
```
KNK_시작.bat: REM LAST UPDATE / title / echo 라인 z38 → z40 (3곳)
START.bat:    REM LAST UPDATE / title / echo 라인 z38 → z40 (3곳)
```
※ 실제 코드는 z39였으나 BAT 표시는 z38이었음 (이전 세션 갱신 누락) → z40 갱신 시 정합 회복.

---

## 5. 다음 단계 — z42 진입 결재 요청

**(D-1) 결재 순서대로** 다음은 z42 (sticky 첫 3컬럼 No / 사진 / 품명).

대표님 결재 사항:
- [ ] **결재 A**: z40 git push 승인 → 푸시 후 다음 단계
- [ ] **결재 B**: z42 진입 시점 (지금 / 검증 후 / 대기)

빅터 권장:
1. 푸시 즉시 (변경 격리됨, 회귀 위험 없음)
2. z42 바로 진입

---

## 6. 위험 / 한계

- ⚠️ z40은 **시각 검증을 브라우저에서 직접 해야 함** (preview panel 활용)
- ⚠️ 1100px 분기는 단일 페이지(`project_detail.html`)에만 적용됨. 다른 매출영업 페이지는 별도 z 단계에서 적용.
- ⚠️ `?debug=1`은 본 페이지에만 적용. 향후 모든 매출영업 페이지에 표준화 필요 (별도 발주서 확장 검토).

---

**문의**: `_ORDERS/` 발주서 v2 / `99_DISPATCH/` 채널
