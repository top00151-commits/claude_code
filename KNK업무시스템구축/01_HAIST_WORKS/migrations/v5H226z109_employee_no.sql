-- ============================================================
-- v5H226z109 — users 테이블 사번(employee_no) 컬럼 추가
-- ============================================================
-- 발주서: KNK업무시스템구축/_TO_메신저세션/2026-05-29_사번SSO.md
-- 작성일: 2026-05-30
-- 작성: 빅터(01) — HAIST WORKS 측 사번 인프라 (메신저 SSO 클라이언트 준비)
--
-- 목적:
--   1. 사번 체계 도입 (본사: '1','5','43'... / VN: 'VN001','VN094'...)
--   2. JWT 토큰 무효화용 password_version 추가
--   3. 엑셀 직원명부와 호환되는 컬럼 확장 (영문·베트남어·휴대폰·부서코드)
--   4. 첫 로그인 강제 비번 변경 플래그
--
-- 안전:
--   - 모든 컬럼 NULL 허용 (점진 마이그레이션)
--   - 기존 데이터 무영향 (ADD COLUMN only)
--   - 컬럼 부재 시 안전한 graceful degradation 코드 호환
--
-- 적용:
--   sqlite3 /opt/knk_haist/data/main.db < v5H226z109_employee_no.sql
--   또는 database.py 자동 마이그레이션 (PRAGMA gate)
--
-- 롤백:
--   SQLite 는 DROP COLUMN 지원 안 함 → 컬럼 추가는 불가역
--   값만 비우려면: UPDATE users SET employee_no = NULL, ...
-- ============================================================

-- ── 1. users 테이블 컬럼 확장 (8개 신규) ──────────────────

-- 사번 (본사: 숫자 / VN: 'VN' + 숫자)
ALTER TABLE users ADD COLUMN employee_no TEXT;

-- 소속 법인 (KOR/VN) — JWT claim 에 entity 로 들어감
ALTER TABLE users ADD COLUMN entity TEXT;

-- JWT 토큰 무효화용 버전 카운터 (비번 변경 시 +1)
ALTER TABLE users ADD COLUMN password_version INTEGER DEFAULT 1;

-- 영문 이름 (예: Kim Jung-rack)
ALTER TABLE users ADD COLUMN name_en TEXT;

-- 베트남어 이름 (예: Nguyễn Văn A) — VN 직원만
ALTER TABLE users ADD COLUMN name_vi TEXT;

-- 휴대폰 (초기 비밀번호 생성용 + 연락처)
ALTER TABLE users ADD COLUMN phone TEXT;

-- 부서 코드 (엑셀 형식: '01_KOR/00_총괄', '02_VN/01_기술팀')
-- 기존 team_id 와 병행 (team_id 는 기존 시스템 호환, dept_code 는 엑셀 마스터)
ALTER TABLE users ADD COLUMN dept_code TEXT;

-- 첫 로그인 시 강제 비번 변경 플래그
ALTER TABLE users ADD COLUMN must_change_pw INTEGER DEFAULT 0;


-- ── 2. 인덱스 추가 ───────────────────────────────────────

-- 사번으로 로그인 조회 (UNIQUE)
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_employee_no
    ON users(employee_no)
    WHERE employee_no IS NOT NULL;

-- 법인별 사용자 조회
CREATE INDEX IF NOT EXISTS idx_users_entity ON users(entity);

-- 부서별 사용자 조회
CREATE INDEX IF NOT EXISTS idx_users_dept_code ON users(dept_code);


-- ── 3. 검증 쿼리 (적용 후 수동 실행) ─────────────────────
-- PRAGMA table_info(users);
-- SELECT COUNT(*) FROM users WHERE employee_no IS NOT NULL;
-- SELECT entity, COUNT(*) FROM users GROUP BY entity;


-- ── 4. 다음 단계 ─────────────────────────────────────────
-- 1) 130명 일괄 import 스크립트 실행 (deploy/import_employees_from_excel.py)
--    → 엑셀 '본사(KOR)' 시트 + '베트남법인(VN)' 시트 → users 테이블
--    → 매칭 키: name + email 또는 name + phone
--    → 미매칭 사용자 리스트 출력 → 대표 수동 판단
--
-- 2) 로그인 화면 (login.html) 사번 입력 지원
--    → login_id 입력란 → "사번 또는 이메일" 안내
--    → main.py login_post 에서 사번 우선 매칭 → 없으면 login_id 매칭
--
-- 3) 첫 로그인 시 비번 변경 화면 (must_change_pw = 1)
--    → 사용자가 새 비번 입력 → 저장 → must_change_pw = 0
--
-- 4) (향후 메신저 SSO 완료 시) SSO 클라이언트 추가
--    → /sso/callback 엔드포인트 → JWT 검증 → users.employee_no 로 매칭
--    → req.session["user_id"] 생성
