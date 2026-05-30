-- ============================================================
-- workflow_template 5개 시나리오 — 엑셀 "형태별업무진행순서.xlsx" 정답 기준 UPDATE
-- 일자: 2026-05-12
-- 근거: 대표 직접 지시 "엑셀 정확히 검증해서 일 순서 만들기에 수정 반영"
-- 엑셀 정독: 참고자료/형태별업무진행순서.xlsx (시트 2개, 시나리오 4개)
-- 메모리 룰: 사람 친화 용어 사용 규칙 + IC 표현 금지 (절대준수)
-- ============================================================

-- 백업 권장:
--   copy data\haist_works.db data\backup\haist_works_pre_excel_corrected_2026-05-12.db

-- ⚠ 텍스트만 정정. 노드 흐름(workflow_template_node)은 별도 빅터 처리 대상.

-- 엑셀 ① 본사 단독 (27 단계)
UPDATE workflow_template SET
  title_ko = '① 국내 고객 + 본사 단독 진행',
  description = '한국 고객사 → 본사가 주문 받고 → 본사에서 설계·제작·출하 → 국내 고객사 배송. 가장 단순한 흐름입니다.'
WHERE code = 's1_kr_domestic';

-- 엑셀 ② 국내+VN협업 제작+본사 최종 (34 단계)
-- (현재 s2 code가 "인도 등 KR 직수출"이라 의미 완전 재배정 — code는 호환성 위해 유지)
UPDATE workflow_template SET
  title_ko = '② 국내 고객 + 베트남 협업 제작 + 본사 최종 마감',
  description = '한국 고객사 → 본사가 주문 받고 → 설계는 본사·베트남 협업 → 베트남에서 제작 → 본사로 다시 들여와 최종 검증·마감 → 국내 고객사 배송.'
WHERE code = 's2_kr_export_in';

-- 엑셀 ③ 해외+VN제작+본사 수출 (34 단계)
UPDATE workflow_template SET
  title_ko = '③ 해외 고객 + 본사 주문 + 베트남 제작 + 본사 수출',
  description = '해외 고객사(인도·터키 등) → 본사가 주문 받음 → 본사·베트남 협업 설계 → 베트남 제작 → 본사로 들여와 최종 검증 → 본사가 해외로 직접 수출 → 해외 고객사 도착.'
WHERE code = 's3_vn_export';

-- 엑셀 ④ 해외+법인PO+본사 개발+VN 출하 (29 단계)
UPDATE workflow_template SET
  title_ko = '④ 해외 고객 + 베트남 법인 직접 주문 + 본사 개발 + 베트남 출하',
  description = '해외 고객사 → 베트남 법인이 직접 주문 받음 → 본사로 주문 발행 → 본사가 개발·자재·완성품 수출 → 베트남에서 제작 → 베트남 법인이 직접 해외 고객사에 출하.'
WHERE code = 's4_vn_local_po';

-- 분담 시나리오 (엑셀에 없음 — 시스템 보조용으로 유지, 빅터 결정 시 제거 가능)
UPDATE workflow_template SET
  title_ko = '⑤ 위 4가지에 안 맞는 경우 (자유 조합)',
  description = '위 4가지 자주 쓰는 흐름에 정확히 맞지 않는 복잡한 경우. 8가지 질문에 답하시면 자동으로 세부 맞춤됩니다.'
WHERE code = 's5_split';

-- 검증 쿼리
SELECT code, title_ko, description FROM workflow_template ORDER BY "order";

-- ROLLBACK (이전 값 — 직전 easy-text 적용본 기준)
-- UPDATE workflow_template SET title_ko = '① 국내 거래 (전부 한국 안에서)', description = '한국 고객 → 한국에서 만들고 → 한국 안으로 배송. 가장 단순하고 자주 쓰는 흐름입니다.' WHERE code = 's1_kr_domestic';
-- UPDATE workflow_template SET title_ko = '② 한국 → 해외 수출 (인도 등)', description = '해외 고객 → 한국에서 만들고 → 해외로 직접 보냄.' WHERE code = 's2_kr_export_in';
-- UPDATE workflow_template SET title_ko = '③ 한국이 주문 받고, 베트남이 만듭니다', description = '한국 본사가 주문 접수 → 베트남 법인이 생산·출하. 한국·베트남 사이 두 거래가 한 쌍으로 자동 생성 (한국→베트남 자재 판매 + 베트남→한국 완성품 매출).' WHERE code = 's3_vn_export';
-- UPDATE workflow_template SET title_ko = '④ 베트남이 전부 처리 (베트남 법인 단독)', description = '베트남 법인이 직접 주문 받고 → 베트남에서 만들고 → 베트남 현지로 배송. 소프트웨어 부분만 한국이 도와줄 수 있습니다.' WHERE code = 's4_vn_local_po';
-- UPDATE workflow_template SET title_ko = '⑤ 복잡한 경우 (한국·베트남 분담)', description = '위 4개에 안 맞는 경우. 설계는 한국·베트남이 함께, 생산은 한국에서… 처럼 섞인 흐름. 8가지 질문에 답하면 자동으로 세부 맞춤됩니다.' WHERE code = 's5_split';
