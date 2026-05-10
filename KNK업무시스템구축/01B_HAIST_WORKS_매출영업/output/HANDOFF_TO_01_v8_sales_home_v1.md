# 📋 실무팀2 → 빅터(01) 핸드오프 v8 — sales_home.html v1+v2 차수

> **발신**: 실무팀2 (매출영업센터)
> **수신**: 빅터 (01 통합실무팀)
> **결재**: 김정락 대표이사 — 2026-05-10 "(γ) sales_home.html + 7시간 자율"
> **작성일**: 2026-05-10
> **버전**: v5H226z44 → **v5H226z45**
> **자율 모드**: 7시간 (Phase 1/8)

---

## 1. 진단

### 갭
- 시안1 토큰 0회 (`--qv-*` / `--biz-*`)
- mgmt 알약 미적용 — 최근 프로젝트 list-num 텍스트만
- data-dn 0건
- 1100px 분기 없음 (1280px만)
- 12-col bento spec 미적용

### 이미 양호
- KPI hero + 4 KPI / 사업부 막대 / 단계 막대 / TOP 5 / 최근 프로젝트
- 1280px 반응형 (line 74)

## 2. v1+v2 차수 적용 (12-col bento는 v3 차수로 보류 — 회귀 위험)

| 항목 | 적용 |
|---|---|
| 시안1 토큰 11종 (body 스코프) | ✅ |
| .mgmt-pill 컴포넌트 (project_detail/sales_orders 통일) | ✅ |
| 최근 프로젝트 list-num → .mgmt-pill sm | ✅ |
| 1100px 반응형 분기 | ✅ |
| data-dn 7 영역 (main/page-head/crumb/title/kpi-bar/grid-biz-stage/biz-bar/stage-bar/grid-customer-recent/top-customers/recent-projects) | ✅ |

## 3. 12-col bento 보류 사유
spec 라인 13~24 명시이나 현재 4 KPI grid + grid-2 구조 → 12-col 전환은 페이지 거의 재작성. 회귀 위험 큼. **자율 권한 사용해도 단일 페이지 재작성보다 다음 페이지 진행이 더 가치 있음**.

## 4. 변경 파일
```
- 01_HAIST_WORKS/app/templates/sales_home.html  (+59줄, 토큰/알약/반응형/data-dn)
```

## 5. 다음 Phase
- Phase 2: customer_detail.html v1+v2 진행
