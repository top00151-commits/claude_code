-- ============================================================
-- v5H226z115 — tasks 테이블 photo_path 컬럼 추가
-- ============================================================
-- 작성: 빅터(01) · 2026-05-31
-- 목적:
--   daily.html 업무 카드에 사진 첨부 (드래그앤드롭 + 클립보드)
--   - 단일 사진 (1 task = 1 photo)
--   - 저장 위치: /uploads/tasks/user_{uid}/task_{tid}_{timestamp}.ext
--   - DB는 상대 URL 경로만 저장
--
-- 안전:
--   - NULL 허용 (점진 마이그레이션)
--   - 기존 데이터 영향 0 (ADD COLUMN only)
--   - 컬럼 부재 시 graceful skip (database.py PRAGMA gate)
--
-- 적용:
--   sqlite3 /opt/knk_haist/data/main.db < v5H226z115_task_photo.sql
-- ============================================================

ALTER TABLE tasks ADD COLUMN photo_path TEXT;

-- 인덱스는 굳이 만들지 않음 (단일 카드 조회 시 t.id PK 로 충분)
