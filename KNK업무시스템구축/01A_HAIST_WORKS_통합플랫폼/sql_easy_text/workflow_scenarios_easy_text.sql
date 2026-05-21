-- ============================================================
-- workflow_template 5개 시나리오 텍스트 쉬운 표현 UPDATE
-- 일자: 2026-05-12
-- 근거: 대표 직접 지시 "설명이 너무 어렵다 / IC 표현 사용하지 마"
-- 메모리 룰: 사람 친화 용어 사용 규칙 (절대준수)
-- ============================================================

-- 적용 전 백업 권장:
--   copy data\haist_works.db data\backup\haist_works_pre_easy_text_2026-05-12.db

UPDATE workflow_template SET
  title_ko = '① 국내 거래 (전부 한국 안에서)',
  description = '한국 고객 → 한국에서 만들고 → 한국 안으로 배송. 가장 단순하고 자주 쓰는 흐름입니다.'
WHERE code = 's1_kr_domestic';

UPDATE workflow_template SET
  title_ko = '② 한국 → 해외 수출 (인도 등)',
  description = '해외 고객 → 한국에서 만들고 → 해외로 직접 보냄.'
WHERE code = 's2_kr_export_in';

UPDATE workflow_template SET
  title_ko = '③ 한국이 주문 받고, 베트남이 만듭니다',
  description = '한국 본사가 주문 접수 → 베트남 법인이 생산·출하. 한국·베트남 사이 두 거래가 한 쌍으로 자동 생성 (한국→베트남 자재 판매 + 베트남→한국 완성품 매출).'
WHERE code = 's3_vn_export';

UPDATE workflow_template SET
  title_ko = '④ 베트남이 전부 처리 (베트남 법인 단독)',
  description = '베트남 법인이 직접 주문 받고 → 베트남에서 만들고 → 베트남 현지로 배송. 소프트웨어 부분만 한국이 도와줄 수 있습니다.'
WHERE code = 's4_vn_local_po';

UPDATE workflow_template SET
  title_ko = '⑤ 복잡한 경우 (한국·베트남 분담)',
  description = '위 4개에 안 맞는 경우. 설계는 한국·베트남이 함께, 생산은 한국에서… 처럼 섞인 흐름. 8가지 질문에 답하면 자동으로 세부 맞춤됩니다.'
WHERE code = 's5_split';

-- 검증 쿼리 (적용 후 실행)
SELECT code, title_ko, description FROM workflow_template ORDER BY "order";

-- ROLLBACK (필요 시)
-- UPDATE workflow_template SET title_ko = '① 국내 (한국 고객·KR 수주·KR 출하)', description = '본사 수주 → 한국 설계·생산 → 국내 출하' WHERE code = 's1_kr_domestic';
-- UPDATE workflow_template SET title_ko = '② KR 수출 (인도 등 KR 직수출)', description = '본사 수주 → 한국 설계·생산 → 인도/해외 수출' WHERE code = 's2_kr_export_in';
-- UPDATE workflow_template SET title_ko = '③ VN 수출 (본사 수주 → VN 출하·KR↔VN IC)', description = '본사가 수주받고 VN 법인이 생산·출하 (KR→VN 자재판매 + VN→KR 가공품 매출 IC 페어)' WHERE code = 's3_vn_export';
-- UPDATE workflow_template SET title_ko = '④ VN 현지 수주 (VN 법인 직수주·VN 출하)', description = 'VN 법인이 직접 수주·생산·VN 현지 출하 (SW만 한국 지원 가능)' WHERE code = 's4_vn_local_po';
-- UPDATE workflow_template SET title_ko = '⑤ 분담 시나리오 (설계 KR+VN, 생산 KR)', description = '복합 케이스 — 마법사 8문항으로 미세조정' WHERE code = 's5_split';
