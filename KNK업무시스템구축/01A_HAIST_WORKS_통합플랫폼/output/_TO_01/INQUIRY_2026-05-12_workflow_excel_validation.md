# 🔎 INQUIRY — 엑셀 "형태별업무진행순서.xlsx" 정독 결과 + workflow 시나리오 노드 흐름 재구성 요청

**발신:** 실무팀1 (통합플랫폼)
**수신:** 빅터 (01) 또는 workflow 빌더 담당 팀
**일자:** 2026-05-12
**대표 직접 보고:** "엑셀 정확히 검증해서 일 순서 만들기에 수정 반영"

---

## 1. 엑셀 정독 결과 (정답 기준)

**출처:** `참고자료/형태별업무진행순서.xlsx`
**전체 덤프:** `01A_HAIST_WORKS_통합플랫폼/notes/형태별업무진행순서_dump.json` (모든 시트·모든 행 JSON)

### 시트 구조
- 시트 1: `본사PO` (시나리오 ①·②·③, 총 95 단계)
- 시트 2: `베트남PO` (시나리오 ④, 29 단계)

### 4개 시나리오 정답

| # | 흐름 | 단계 수 |
|---|---|---|
| ① | 고객사국내 → 본사PO → 본사개발 → 본사제작 → 본사출하 → 국내고객사 | **27** |
| ② | 고객사국내 → 본사PO → 본사개발(VN협업) → VN제작 → 본사입고 → 본사최종제작 → 본사출하 → 국내고객사 | **34** |
| ③ | 고객사해외 → 본사PO → VN제작 → 본사입고 → 본사최종제작 → 본사수출 → 해외고객사 | **34** |
| ④ | 고객사해외 → 법인PO → 본사PO → 본사개발 → 본사 상품·제품 수출 → VN제작 → 법인출하 | **29** |

---

## 2. 현재 시스템 vs 엑셀 차이

### 텍스트 차이 (이미 정정 완료 — 본 INQUIRY 적용 시 DB UPDATE 필요)
- 이미 `sql_easy_text/workflow_scenarios_excel_corrected.sql` 작성 — 5개 row UPDATE
- migration 파일(`m_z104_workflow_builder.py`) 동기 수정 완료
- wizard.html SCENARIO_INFO 동기 수정 완료

### 노드 흐름 차이 (빅터 처리 필요)

#### 현재 s1_kr_domestic (31 nodes) vs 엑셀 ① (27 단계)
**상태:** 비슷하나 단계 수 4개 차이. 엑셀에는 없는 노드가 4개 더 있을 가능성. 검증 필요.

#### 현재 s2_kr_export_in (31 nodes) vs 엑셀 ② (34 단계)
**상태:** 의미 완전 다름.
- 현재 s2: "한국 → 인도 등 해외 수출" (KR 단독)
- 엑셀 ②: **"국내 고객 + VN 협업 제작 + 본사 최종 마감"** (한국 안에서 끝남)
- **노드 재구성 필요:** ic.kr_sale_to_vn / ic.vn_buy_from_kr / prod.vn_assy / ic.vn_sale_to_kr / ic.kr_buy_from_vn + 본사 최종 검증 노드 + logi.ship_kr (국내 배송)
- 현재 s2의 logi.export_doc / logi.customs는 제거 (해외 수출 아님)

#### 현재 s3_vn_export (36 nodes) vs 엑셀 ③ (34 단계)
**상태:** 흐름이 다름.
- 현재 s3: "본사 수주 → VN 출하" (VN 직접 출하)
- 엑셀 ③: **"본사 수주 → VN 제작 → 본사 입고 → 본사 최종 → 본사 수출"** (본사가 수출)
- **노드 재구성 필요:** logi.ship_vn → 제거. 본사 입고 + 본사 최종 검증 + logi.export_doc + logi.customs + logi.ship_kr 추가.

#### 현재 s4_vn_local_po (30 nodes) vs 엑셀 ④ (29 단계)
**상태:** 비슷하나 본사 개발 단계 부족.
- 현재 s4: "VN 법인이 직접 수주·생산·VN 현지 출하 (SW만 한국 지원 가능)"
- 엑셀 ④: **"법인PO → 본사PO → 본사 개발 → 본사 상품·제품 수출 → VN 제작 → 법인 출하"** (본사 개발 + 본사가 자재·제품을 VN으로 수출)
- **노드 재구성 필요:** 본사 PO 입수 / 본사 개발 / 본사 상품 수출(ic.kr_sale_to_vn) 노드 추가. design.sw_kr 외 design.mech_kr / design.elec_kr / design.review 등도 본사 진행.

#### 현재 s5_split (분담 시나리오)
**상태:** 엑셀에 없음.
- **결정 필요:** (a) 제거 / (b) 시스템 보조 옵션으로 유지

---

## 3. 권한 명시

- 시나리오 텍스트(title_ko, description) — 이미 실무팀1 직접 수정 완료 (대표 직접 지시 + 빅터 자동 처리 미작동 상태에서 일시 권한 확장)
- **노드 흐름(workflow_template_node, TEMPLATES nodes list)** — 코드 로직 영향 큼, **빅터 권한**
- **workflow_node_master 테이블** — 신규 노드 추가 필요할 수도, **빅터 권한**

## 4. 권장 처리 순서

### Step A (즉시 적용 — 텍스트만)
1. DB 백업
2. `sql_easy_text/workflow_scenarios_excel_corrected.sql` 적용 (5개 row UPDATE)
3. `/workflow` 새로고침 검증

### Step B (빅터 검수 후 — 노드 흐름 재구성)
1. 엑셀 4개 시나리오의 각 단계 → 시스템 노드 매핑표 작성
2. workflow_node_master에서 누락된 노드 식별 (예: prod.kr_final_assy, qa.kr_inspect_after_vn, ic.kr_buy_from_vn_in_kr 등)
3. workflow_template_node 5개 시나리오 노드 list 재구성
4. migration 파일의 TEMPLATES nodes list 동기 수정
5. wizard.html nodes 카운트 동기 수정

### Step C (분담 시나리오 결정)
- (a) s5_split 제거 + 5번째 카드 숨김
- (b) 시스템 보조 옵션으로 유지 (현재 시안 — "위 4가지에 안 맞을 때")

## 5. 노드 흐름 재구성 시안 (참고용)

엑셀 ① (27 단계) 매핑 시안:
```
sales.lead → sales.meeting → sales.requirement → sales.quote → sales.po_receive →
design.spec(컨셉회의/제안서) → design.bom → design.mech_kr(3D설계) → design.elec_kr(전장설계) →
design.sw_kr(소프트웨어) → design.review → purchase.new_review(장납기 자재) →
purchase.po_issue(자재 발주) → purchase.outsource_po(가공품 발주) → purchase.receive →
prod.kr_assy(기구조립) → prod.kr_electric(전장작업) → prod.kr_io_check(I/O 체크) →
prod.kr_program(프로그램 적용) → qa.final(출하검증) → qa.fat(장비출하준비) →
logi.packing → logi.ship_kr → logi.delivery(셋업) → logi.setup → as.manual(설비 매뉴얼) →
finance.invoice(출하처리) → as.handover(최종 마감 정리)
```
→ 신규 노드 후보: `prod.kr_electric`, `prod.kr_io_check`, `prod.kr_program`, `purchase.outsource_po`, `as.manual`

(엑셀 ②·③·④도 유사 분석 필요 — 본 INQUIRY로 빅터 분석 위임)

## 6. 첨부 자료

- **엑셀 전체 덤프 JSON:** `01A_HAIST_WORKS_통합플랫폼/notes/형태별업무진행순서_dump.json`
- **즉시 적용 SQL:** `01A_HAIST_WORKS_통합플랫폼/sql_easy_text/workflow_scenarios_excel_corrected.sql`
- **자동 적용 도구:** `01A_HAIST_WORKS_통합플랫폼/sql_easy_text/APPLY_workflow_easy_text.bat` (SQL 파일명 변경 필요 — 본 INQUIRY 처리 시 안내)

## 7. 결론

- 시나리오 **텍스트는 엑셀 기준으로 즉시 정정** (이미 적용 + SQL 대기)
- **노드 흐름은 엑셀과 큰 차이** — 시나리오 ②·③·④ 모두 단계·부서·흐름 재구성 필요
- 분담 시나리오(⑤) 처리 방향 결정 필요

**빅터 처리 요청:**
1. SQL 적용 (5개 row UPDATE)
2. 노드 흐름 4개 시나리오 재구성 (workflow_template_node + TEMPLATES nodes list + workflow_node_master 보강)
3. 분담 시나리오 유지/제거 결정
4. 라이브 검증
