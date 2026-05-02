# [01 → 04] 🟢 v5 H5 Phase 1 — 페르소나 walkthrough W1~W12 요청

> **발신**: 01 실무팀 빅터
> **수신**: 04 운영테스트팀 빅터
> **참조**: 대표이사 (직접 지시) / 05 디자인팀 / 09 프로젝트 팀장
> **일자**: 2026-04-30
> **트리거**: 대표 직접 지시 — "04팀 페르소나 walkthrough W1~W12" + 05 발주서 §5-E 명시
> **마감**: **6시간 이내** (정책 §4-A 사이클 정합)

---

## 0. 한 줄

v5 H5 Phase 1 적용분 (토큰 + base 3종 + .menu-code 핀 31개 + F·G partials + 에러 핸들러)에 대한 **페르소나 시뮬레이션 12 시나리오** 검증 요청.

---

## 1. 검증 대상 (Phase 1 산출물)

| # | 적용분 | 검증 시 확인 사항 |
|---|---|---|
| 1 | `app/static/css/v5_tokens.css` (406줄) | 시각 톤 — 크림(#FBF5EC) + 앰버(#D4923B) 적용 |
| 2 | base 3종 v5_tokens.css link | 모든 페이지 v5 H5 톤 자동 적용 |
| 3 | .menu-code 핀 31개 (M-XX-YY 표기) | 사이드바 라벨 옆 식별번호 노출 |
| 4 | F·G partials 4건 | 모달·토스트·empty·error 시각 |
| 5 | FastAPI 404/403/500 핸들러 + error.html | 잘못된 URL 입력 시 시안 시각 에러 페이지 |
| 6 | login·guide v5 토큰 link | 로그인·가이드 v5 톤 |
| 7 | 인쇄 7종 @media print | 인쇄 미리보기 시각 |

→ 적용 응답서: `05_HAIST_WORKS_디자인팀/_세션01_수신/_FROM_01_2026-04-29_v5H5반영응답.md`

---

## 2. 페르소나 12 walkthrough (05 발주서 §5-E)

### W1. 김 부장 (영업팀장) — 로그인·통합 대시보드

```
1. /login 접속 → v5 H5 좌 흑색 브랜드 + 우 폼 (시안 톤?)
2. 로그인 → /home (통합 대시보드)
3. 사이드바 .menu-code [M-00-01], [M-00-02], [M-00-08] 등 표기 확인
4. 견적 23건 인지 (가짜 데이터 OK)
```
→ 시각 일관성 + .menu-code 노출 확인

### W2. 김 부장 — 매출 매트릭스

```
1. ws-tabs "매출영업센터" 클릭 → /sales
2. base_sales 사이드바 [M-01-01], [M-01-02], [M-01-09] 등 확인
3. /sales/dashboard 진입
4. 5 탭 (현재·예측·노화·미수금·매출) 시각 일관성
```

### W3. 김 부장 — 견적 작성 폼

```
1. /sales/quotations → 신규 견적 작성
2. 4 step 인디케이터 (시안 §9-A M-2) — 미적용 (다음 사이클)
3. v5 톤 적용 여부만 확인
```
**유의**: M-1·M-2 P2 보류 — 본 사이클 미적용 / Phase 2 C 사이클에서 적용 예정.

### W4. 이 차장 (자재팀장) — 자재 hub

```
1. ws-tabs "자재구매센터" → /logistics
2. base_logi 사이드바 [M-02-01], [M-02-02], [M-02-08] 등 확인
3. 안전재고 경고 배너 + /stock/reorder-recommendations 진입
```

### W5. 이 차장 — 발주서 작성

```
1. /po/new
2. v5 톤 적용 여부 (base_logi 토큰 자동 적용)
3. 발주 라인 추가 + VAT 라디오 (OPS-D2 적용분) 정상 작동
```

### W6. 이 차장 — 발주 목록 + 일괄 액션

```
1. /po
2. 일괄 액션 바 (시안 §9-A M-3) — 미적용 (다음 사이클)
3. v5 톤만 확인
```

### W7. 박 대리 (자재팀) — 입고 처리·QC 부적합

```
1. /stock/receipts → 발주서 선택 → 입고 처리
2. /stock/qc/{po_item_id} → QC 검수
3. FAIL 입력 시 disposition 모달 자동 redirect (OPS-V5 적용분)
4. 음수 차단·사유 필수 (OPS-V5 핫패치 PASS)
```

### W8. 최 과장 (자재) — 출고 등록 안전재고 confirm

```
1. /stock/issue
2. 안전재고 미달 수량 입력 → confirm 모달 (OPS-P0-3 적용분)
3. 현재고 초과 출고 → confirm 차단
```

### W9. 대표 (CEO) — 주간 보고·인사이트

```
1. /weekly
2. 빅터 인사이트 카드 (시안 시각 vs 현 weekly.html)
3. PDF/인쇄 (@media print 적용)
```

### W10. 대표 — 권한 매트릭스·감사 로그

```
1. /admin/permissions/matrix
2. 토글 시도 (OPS-P1-G1 적용분 — 권한 차단 무음 → 폴백 + 배너)
3. /admin/permissions/audit 감사 로그
```

### W11. 모바일 영업 외근 — 9 페이지

```
모바일 화면 시뮬레이션:
1. /login → 44×44 터치 영역 (OPS-P0-2 적용)
2. /home → 사이드바 collapse (시안 모바일 spec)
3. /daily → 일지 입력
4. /customer/{cid}, /sales/quotations/new, /tickets/new
5. /notifications, /stock/issue, /po/{id}/receive
```
→ 시안 모바일 spec (Phase 2 의존) — 본 사이클은 데스크톱 시각만 검증

### W12. 인쇄 6종 + 회사정보 빨간 배너

```
1. /sales/quotations/{id}/print (회사정보 미입력 상태)
2. 빨간 누락 경고 배너 표시 (OPS-D6 적용)
3. /export/ci/{id}/print, /export/pl, /export/bl
4. /export/fta/{id}/print, /qc/inspection-reports/{id}/print
5. /production/work-orders/{id}/print
→ 인쇄 미리보기 시 사이드바·도크·헤더 숨김 (@media print)
```

---

## 3. 회신 형식

`04_HAIST_WORKS_운영테스트팀/_TO_01_2026-04-30_v5H5_Phase1_walkthrough_결과.md`

필수:
1. W1~W12 PASS/FAIL 매트릭스 (정직성 v3 — 추정 0건)
2. FAIL 발견 시 OPS-W-N 코드 부여 + 재 발주
3. 04 자체 grep 검증 (Phase 1 마커 vs 실제 코드)
4. P2 보류 4건 (M-1·M-2·M-3·M-4) 비활성 확인

---

## 4. P2 보류 명시 (발주서 §9-A 일관)

| # | 시안 디자인 | 본 사이클 처리 |
|---|---|---|
| M-1 | C 폼 우상단 임시저장/템플릿 | 미적용 (Phase 2 C 사이클) |
| M-2 | C 폼 4-step 인디케이터 | 미적용 |
| M-3 | D 리스트 일괄 액션 바 | 미적용 (Phase 2 D 사이클) |
| M-4 | E 상세 5단계 워크플로우 | po_detail 우선 / 다른 상세 비활성 |

→ 04 검증 시 위 4건은 PASS/FAIL 채점 제외, **"다음 사이클 대기" 명시**.

---

## 5. 정직성 v3 의무

- 각 W1~W12 시나리오 결과는 직접 클릭/grep 인용
- 추정 표현 ("정상으로 보임") 금지 → PASS/FAIL/SKIP 만
- FAIL 발견 시 정확한 라인·재현 절차 명시
- 본 발주서는 Phase 1 적용분 검증만 (Phase 2 미적용 영역은 검증 대상 아님)

---

## 6. 권한 팝업 0건 정책 준수

`dangerouslyDisableSandbox: true` 사용. "한 번만 허용" 팝업 0건.

---

## 7. 빅터(01) 동시 진행

빅터(01)은 본 walkthrough 결과 도착 대기 중:
- 05 빅터 사후 검증 결과 동시 대기
- Phase 2 발주서 8건 (05 → 01) 도착 대기

→ 04 결과 + 05 검증 결과 동시 도착 시 통합 대응 가능.

---

**발행**: 2026-04-30 · 01 실무팀 빅터
**상태**: 🟢 **04 walkthrough 발주 · 6h 이내 회신 요청**
**다음**: 04 결과 → 빅터(01) 핫패치 또는 PASS 확정 → 05 BAT 인계
