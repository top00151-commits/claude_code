# 📤 실무팀3 → 빅터(01) 핸드오프 — v11 (wo_print 시안1 / 작업지시 풀체인 완성)

> **세션:** 실무팀3 (자재구매센터)
> **워크트리:** `cranky-shtern-789fa2` — 메인 폴더 직접 작업 모드
> **기준일:** 2026-05-11
> **시스템 버전:** v5H226z58
> **차수:** 11차 (작업지시 풀체인 마무리)

---

## 1. 배경

빅터 추천 §11차 = **C. WO 인쇄** — wo_list (z57) + wo_form (9차 z58) 다음 누락이었던 **wo_print.html** 을 시안1 z58로 전면 재작성. 작업지시 풀체인 완성.

## 2. 산출물 (1 파일)

### `wo_print.html` — 인쇄 친화 A4

#### 핵심 특징
- **@page A4 + @media print** — 인쇄 시 화면 액션 숨김, 종이 사이즈 자동
- **외부 자산 0건** — 인라인 CSS, 외부 라이브러리 없음
- **시안1 모노톤** — 구버전 #1B5E20 (녹색) 제거 → 검정/회색만 (KNK 자체 디자인)
- **자동 인쇄 옵션** — `?auto=1` 쿼리 시 페이지 로드 후 200ms 후 자동 `window.print()`

#### 구성
1. **헤더** — KNK 로고 영역 + 회사 정보 (회사명·주소·TEL·FAX·사업자번호·대표·이메일) + 제목 "작업지시서 / WORK ORDER"
2. **메타 표 4행** —
   - WO번호 / 상태 chip / 발행일
   - 수주 / 프로젝트 / 발행자
   - 가공 부품 (이름·코드·규격) / 담당자
   - 생산 수량 / 계획 시작·종료일
3. **가공 사양 박스** — 자유 텍스트 (specifications) 또는 "(사양 미입력)" placeholder
4. **공정 표** — # / 공정명 / 공수(분) / 진행률 바 / 작업자 / 비고 + tfoot 합계
5. **비고 박스** — remarks 또는 "(비고 없음)" placeholder
6. **도장란 4종** — 작성 / 검토 / 승인 / 수령 (작성·수령은 자동 채움, 검토·승인은 빈칸 + 날짜선)
7. **푸터** — 자동 생성 안내 + WO번호 + 시스템 버전

## 3. 자체 검증 결과 (2패스)

### 1패스 — 결함 발견
- ❌ **company 키 명명 불일치** — `company.company_name` (잘못) vs 실제 `company.company_name_ko` 등 7개 키 정정 필요

### 2패스 — 결함 수정 후 통과
- ✅ company 키 7개 정정 (company_name_ko / company_address / company_tel / company_fax / company_biz_no / company_ceo_ko / company_email)
- ✅ wo 객체 18개 변수 활용 (wo_no / status / created_at / order_no_disp / project_disp / created_by_disp / part_disp / part_no / part_spec / assigned_disp / qty / part_unit / planned_start / planned_end / specifications / items / avg_progress / remarks)
- ✅ @page A4 + @media print
- ✅ 외부 자산 0건
- ✅ amber-grad / knk-red 0건

## 4. 작업지시 풀체인 완성 ✅

| 페이지 | 차수 | 상태 |
|---|---|---|
| wo_list (목록) | z57 (7차) | 🟢 chip-wo 5상태 + KPI 6 |
| wo_form (작성·상세) | z58 (9차) | 🟢 양 모드 통합 + 표준 공정 자동 |
| **wo_print (인쇄)** | **z58 (11차)** | **🟢 A4 + 도장란 + 자동 인쇄** |

→ **작업지시 F 그룹 풀체인 100%** ✅

## 5. UX 강화

### 자동 인쇄
URL에 `?auto=1` 붙이면 페이지 진입 → 200ms 후 자동 `window.print()` 호출 → 인쇄 다이얼로그 즉시 표시. wo_form 상세에서 "인쇄" 버튼 클릭 시 활용 가능.

### 도장란 자동 채움
- 작성: 발행자 (wo.created_by_disp) 자동 채움
- 수령: 담당자 (wo.assigned_disp) 자동 채움
- 검토 / 승인: 빈칸 (현장에서 수기 + 날인)

### 진행률 바
공정 라인별 진행률 % 시각화. 0%는 회색 막대, 100%는 초록(완료) 막대, 그 외는 파랑(진행중).

## 6. 룰 v4 + 발주서 7항 준수

| 항목 | 본 차수 |
|---|---|
| 메인 BAT | 0건 ✅ |
| 라벨 z58 | HTML 주석 ✅ |
| 워크트리 동기화 | 메인 직접 ✅ |
| 시안1 (e) 단계 | 인쇄 모노 톤 ✅ |
| 99_DISPATCH | 0건 ✅ |
| 다른 팀 페이지 | wo는 가공팀 영역이나 자재출고·BOM 직결 — 실무팀3 책임 ✅ |
| `_v5_partials/` partial | 0건 ✅ |
| DB 스키마 | 0건 ✅ |
| 라우트 추가/변경 | 0건 ✅ (기존 라우터 그대로) |
| 위하고 직접 연동 | 0건 ✅ |

## 7. 검수 절차

```
http://localhost:8081/production/work-orders/{id}/print           ← 일반 인쇄
http://localhost:8081/production/work-orders/{id}/print?auto=1    ← 자동 인쇄
```

검수 항목:
- 화면: 인쇄 버튼 + 돌아가기 링크 표시 (상단 print-bar)
- 인쇄 미리보기 (Ctrl+P): 화면 액션 숨김, A4 1페이지 또는 2페이지로 깔끔
- KNK 회사 정보 표시 (app_settings에서 가져옴 — 미입력 시 기본값)
- 도장란 4 칸: 작성/검토/승인/수령
- 진행률 바 + chip 상태 + 합계 tfoot

## 8. 빅터(01) 처리 요청

- [ ] wo_print.html 인쇄 미리보기 검수 (A4 1페이지 / 2페이지 어느 쪽 적정인지)
- [ ] 회사 정보 app_settings에 정확히 입력되어 있는지 확인 (회사명·주소·전화·사업자번호 등)
- [ ] STATUS.md `🟢 통합 완료` z58 11차 등록
- [ ] git push
- [ ] **다음 차수 (12차) 승인**

## 9. 다음 차수 권장 옵션

| 옵션 | 항목 | 분량 |
|---|---|---|
| **A. 검사 성적서 인쇄** | qc_report_print | 1 페이지 (대칭) |
| **B. 재고 출고 영역** | stock_issue / stock_issues / stock_qc / stock_adjustment | 4 페이지 묶음 |
| **C. 품질 대시보드** | qms_dashboard / qms_pareto / qms_capa | 3 페이지 |
| **D. 단가 이력 페이지** | part_prices | 1 페이지 |

빅터 추천: **A. qc_report_print** — wo_print와 대칭. 품질 풀체인 완성 (qc_report_list / qc_report_form / qc_report_print).

## 10. 운영 메모

- **인쇄 친화 패턴 정착**: @page + @media print + 외부 자산 0건 + 자동 인쇄 옵션
- **도장란 표준화**: 작성·검토·승인·수령 4종 — KNK 결재 라인 반영
- **작업지시 풀체인 완성 ✅** — F 그룹 3 페이지 모두 z57/z58 시안1

---

**보고:** 실무팀3 (자재구매센터) → 빅터(01)
**결재:** 김정락 대표이사 직접 라인
**자체 검증:** 2패스 통과 (결함 1건 발견 → 즉시 수정)
**완료 선언:** 2026-05-11 / 검증 후 정식 산출물 완료
**작업지시 풀체인 완성** — 11차 마감
