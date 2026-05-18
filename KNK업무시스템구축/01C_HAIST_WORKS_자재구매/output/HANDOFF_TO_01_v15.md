# 📤 실무팀3 → 빅터(01) 핸드오프 — v15 (stock_issues / 출고 이력)

> **세션:** 실무팀3 (자재구매센터)
> **워크트리:** `cranky-shtern-789fa2` — 메인 폴더 직접 작업 모드
> **기준일:** 2026-05-11
> **시스템 버전:** v5H226z58
> **차수:** 15차 (출고 풀체인 보완)

---

## 1. 배경

빅터 추천 §15차 = **A. stock_issues** (출고 이력) — 14차 stock_issue(출고 등록)와 자연 짝. stock_receipts(입고 이력, z57)와 대칭 디자인.

## 2. 산출물 (1 파일)

### `stock_issues.html` — 출고 이력 목록

- **KPI 4종**: 전체 / 대기 PENDING / 완료 ISSUED / 취소 CANCELLED
- **chip-iss 3상태 + UNKNOWN fallback** — PENDING=황 / ISSUED=초록 / CANCELLED=회색 취소선
- **7컬럼 dense 표**: GI번호·상태·자재·수량·용도·요청시각·출고시각
- **?success/?error 배너 자동**: 라우터 처리 메시지 즉시 표시
  - invalid: 자재/수량 입력 오류
  - notfound: 출고 건 없음
  - already-XXX: 이미 처리됨
- **빈 상태 + CTA** — "출고 이력 없음 → ＋ 출고 등록"
- **헤더 액션 3종**: 재고 현황 / 입고 이력 (대칭) / **＋ 출고 등록** (검은색 강조)

## 3. 라우터 호환

| 위치 | 라우터 (main.py:13605) | stock_issues.html |
|---|---|---|
| GET | `/stock/issues` | ✅ |
| 전달 변수 | issues (id/part_id/qty/purpose/status/requested_at/issued_at) | 모두 활용 ✅ |
| 라우터 status | PENDING / ISSUED / CANCELLED | chip-iss 3종 매칭 ✅ |
| 라우터 ?error= | invalid / notfound / already-XXX | 배너 자동 표시 ✅ |
| 라우터 ?success= | GI-{id} 형식 | 배너 표시 ✅ |

## 4. 자체 검증 결과 (1패스)

| 항목 | 결과 |
|---|---|
| amber-grad / knk-red | **0건** ✅ |
| data-dn / chip-iss | **13 매칭** ✅ |
| 라우터 status 값 정합 | PENDING/ISSUED/CANCELLED 일치 ✅ |
| stock_receipts 대칭 디자인 | KPI 4 + chip + 표 동일 패턴 ✅ |
| 토큰 z58 | ✅ |

## 5. E 재고 그룹 진행

| 페이지 | 상태 |
|---|---|
| stock_balances/movements/abc/safety/turnover/reorder/receipts | 🟢 z57 (7) |
| stock_issue | 🟢 z58 (14차) |
| **stock_issues** | **🟢 z58 (15차)** |
| stock_qc / stock_adjustment / stock_audit / stock_fifo | 🔘 (4) |

→ E 그룹 **9 / 13 (69%)**

## 6. 룰 v4 + 발주서 7항 준수

| 항목 | 본 차수 |
|---|---|
| 라우트 / DB 변경 | 0건 ✅ |
| 다른 팀 페이지 | 0건 ✅ |
| 99_DISPATCH | 0건 ✅ |
| 외부 자산 | 0건 ✅ |
| 시안1 톤 (amber 0) | ✅ |

## 7. 검수 절차

```
http://localhost:8081/stock/issues?debug=1
http://localhost:8081/stock/issues?success=GI-42&debug=1     ← 배너 테스트
http://localhost:8081/stock/issues?error=invalid&debug=1     ← 오류 배너 테스트
```

## 8. 빅터(01) 처리 요청

- [ ] stock_issues 검수 (KPI / 표 / 배너)
- [ ] STATUS.md z58 15차 등록
- [ ] git push
- [ ] **다음 차수 (16차) 승인**

## 9. 다음 차수 권장 옵션

| 옵션 | 항목 | 분량 | 비고 |
|---|---|---|---|
| **A. stock_adjustment** | 재고 조정 (실사 차이 보정) | 1 페이지 | E 그룹 |
| **B. stock_audit** | 재고 실사 | 1 페이지 | E 그룹 |
| **C. stock_fifo** | FIFO 레이어 조회 | 1 페이지 | E 그룹 |
| **D. qms_dashboard** | 품질 대시보드 | 1 페이지 | 품질 BI |

빅터 추천: **A. stock_adjustment** (재고 조정) — 입출고 외 재고 변동의 표준 진입로.

## 10. 누적 진행

**25 페이지 / 30+ (83%)** — 6차~15차 10 차수 누적.

---

**자체 검증:** 1패스 통과 (0 결함 + 13 매칭)
**완료 선언:** 2026-05-11 / 검증 후 정식 산출물 완료
