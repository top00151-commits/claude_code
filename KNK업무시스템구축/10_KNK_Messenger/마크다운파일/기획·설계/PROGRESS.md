# 메신저 세션 PROGRESS — 사번 SSO 도입

> 발주: `_TO_메신저세션/2026-05-29_사번SSO.md` · 착수: 2026-05-31 · 담당: 메신저 세션(빅터)
> 완료보고 채널: `_TO_빅터/메신저_사번SSO_완료_YYYYMMDD.md` · 막힘: 99_DISPATCH / 대표 직접

## 핵심 스키마 매핑 (발주서 가정 → 실제 메신저 컬럼)
| 발주서 | 실제 `users` 컬럼 | 비고 |
|---|---|---|
| login_id | `username` (UNIQUE) | 로그인 ID |
| name_kr | `display_name` | |
| name_en / name_vi | `display_name_en` / `display_name_vn` | |
| dept / position | `department` / `title` | |
| employee_no | `employee_no` | ✅ 이미 존재 |
| entity | `entity` | 🆕 추가 |
| password_version | `password_version` | 🆕 추가 (방안 A) |
| is_admin | `role == 'ceo'` | role 기반 |

- 비번 해시: `werkzeug.security` (generate/check_password_hash)
- 로그인: `login()` `SELECT * FROM users WHERE username=?`
- 비번 변경: `PUT /api/me/password`, `reset_password`, 관리자 set
- 초기비번: 본사=휴대폰 숫자 / VN=9999 (기존 로직 재사용)
- 엑셀 소스: `C:\Users\top00\JR\01_업무관련\03_인사업무\KNK_직원등록(본사|베트남).xlsx`
  - 본사(KOR) 7열 / 베트남법인(VN) 8열

## 단계 진행 (체크)
- [x] **3.1** 스키마: `entity` + `password_version` 컬럼 + `employee_no` UNIQUE index (#163)
- [x] **3.4.4** 비번 변경 2곳(자체변경·관리자초기화)에 `password_version += 1` (#164)
- [x] **3.4** SSO 헬퍼: 키 로딩 + JWT 발급/검증(pwv) (#165)
- [x] **3.4** SSO API 4종 + 보안(rate limit/CORS/HTTPS/log) + `/sso/login` redirect (#166)
- [x] **4.1** requirements PyJWT + `deploy/gen_sso_keys.sh` (#167)
- [x] **3.2** `sso_work/migrate_employee_no.py` (dry-run+apply 합성DB 검증 완료) (#168)
- [x] **3.3/3.5** `sso_work/update_guide_sheet.py` + `_TO_빅터/메신저_사번SSO_인터페이스.md` (#169)
- [ ] **[GATED]** 라이브 cutover(백업·점심/새벽) + 키생성 + PyJWT설치 + 배포검증 + 완료보고 (#170)

## 로컬 검증 결과
- app.py `py_compile` OK (SSO 모듈 + 로그인 redirect 삽입 후)
- JWT RS256 왕복 테스트: 발급·검증·pwv불일치·iss거부·aud거부·exp거부·JWK 전부 통과
- 마이그레이션 합성DB: 매칭3·신규127·DB-only1·게스트제외 정합, username=사번 갱신·INSERT SQL 정상
- 안내시트 §2: 로그인ID 회사이메일/영문이름 → **사번** 치환 7셀 확인

## 안전 원칙
- 코드/스크립트/문서 = 즉시 진행
- **실서비스 130명 login_id 라이브 변경**은 백업 직후 점심(12:00~13:00)/새벽에만 (발주서 §8.2)
- `users.id`(내부 PK) 절대 불변 — 모든 외래키 기반
- 자동 비활성화 금지 — 메신저-only 미매칭은 목록만 출력 → 대표 수동 판단 (§8.1)
- 폴더스코프: 산출물은 `KNK업무시스템구축\` 내부에만 생성

## 로그
- 2026-05-31 발주 정독·정찰 완료(스키마/엑셀/인증코드 확인) → 구현 착수
- 2026-05-31 #163~169 구현+로컬검증 완료 → 배포(app.py 580515, /healthz 200, SSO 4종 503 확인) → push 3d4fa70
- 다음: #170 라이브 cutover (대표 go·타이밍 + 운영DB 상태 확인 후)

## cutover 결과 (#170) — 2026-05-31 완료 ✅
1. [x] dry-run(운영DB): 매칭 130 · 신규 0 · 충돌 0 · DB-only 2(테스트계정)
2. [x] 운영 DB 백업 `data/backup_pre_employee_no_20260531_013142.db`
3. [x] PyJWT 2.9.0 venv 설치 + RS256 키 생성(`keys/`)
4. [x] `--apply` 적용(2-패스 임시리네임으로 username UNIQUE 전이충돌 해결) → 커밋 완료
5. [x] 검증: employee_no NULL 0 · username=employee_no 0 불일치 · 대표 `5`=ceo · VN `VN001`=VN · healthz 200 · SSO public-key 200 · token 더미 401
6. [~] DB-only 2(175 김빅터/999, 178 이빅터/998) → **대표 수동판단 대기**(완료보고서 §4)
7. [~] 안내시트 갱신 스크립트 준비 — HR 원본 교체는 대표 확인 후(폴더정책)
8. [x] 완료보고 `_TO_빅터/메신저_사번SSO_완료_20260531.md`
9. [i] env `KNK_MSG_OWNER_USERNAME=5` 권장 — 현재 대표 role=ceo 정상 유지 확인됨

**발견**: 운영 DB는 이미 username=employee_no=사번 상태(이전 일괄등록 사이클)였음. 이번 apply 의 실효는 `entity` 채움 + 필드 HR정렬. 로그인 끊김 위험 없었음.
