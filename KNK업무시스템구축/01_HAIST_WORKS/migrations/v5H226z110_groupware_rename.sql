-- ============================================================
-- v5H226z110 — hiworks_* → groupware_* 키 마이그레이션
-- ============================================================
-- 발주: 익명화 후속 4건 (대표 결재 2026-05-22 + 5-30 추가)
-- 작성일: 2026-05-30
-- 작성: 빅터(01)
--
-- 목적:
--   app_settings 테이블의 hiworks_* 키 값을 groupware_* 키로 복사
--   사용자가 admin 페이지에서 입력한 그룹웨어 URL 보존
--
-- 안전:
--   INSERT OR IGNORE 로 신규 키만 추가 (기존 groupware_* 값 보존)
--   기존 hiworks_* 키는 그대로 유지 (즉시 삭제 X, 추후 별도 정리)
--
-- 적용:
--   sqlite3 /opt/knk_haist/data/main.db < v5H226z110_groupware_rename.sql
--
-- 검증 (적용 후):
--   SELECT key, value FROM app_settings WHERE key LIKE 'groupware_%';
-- ============================================================

-- 8개 그룹웨어 설정 키 복사 (hiworks_* → groupware_*)

INSERT OR IGNORE INTO app_settings (key, value)
SELECT REPLACE(key, 'hiworks_', 'groupware_'), value
FROM app_settings
WHERE key IN (
    'hiworks_main_url',
    'hiworks_approval_url',
    'hiworks_mail_url',
    'hiworks_domain',
    'hiworks_attendance_url',
    'hiworks_leave_url',
    'hiworks_payroll_url',
    'hiworks_profile_url'
);

-- HIWORKS 토큰류 (선택 — 메신저·HR·결재 API 토큰)
INSERT OR IGNORE INTO app_settings (key, value)
SELECT REPLACE(key, 'hiworks_', 'groupware_'), value
FROM app_settings
WHERE key IN (
    'hiworks_messenger_token',
    'hiworks_hr_token',
    'hiworks_approval_token'
);

-- ── 검증 쿼리 (적용 후 수동 실행) ─────────────────────
-- SELECT key, value FROM app_settings WHERE key LIKE 'groupware_%' ORDER BY key;
-- SELECT key, value FROM app_settings WHERE key LIKE 'hiworks_%' ORDER BY key;
-- → 두 결과 동일해야 (값 복사 확인)


-- ── 다음 단계 (추후 별도 사이클) ────────────────────────
-- 1. 일정 기간 후 (~3개월) hiworks_* 키 일괄 삭제:
--    DELETE FROM app_settings WHERE key LIKE 'hiworks_%';
-- 2. database.py 의 get_setting() fallback 로직 제거
