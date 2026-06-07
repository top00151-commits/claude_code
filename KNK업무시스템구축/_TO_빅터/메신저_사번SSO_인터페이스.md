# [메신저 → 실무팀1] 사번 SSO 인터페이스 확정서

> 발신: 메신저 세션 · 수신: 실무팀1 빅터(HAIST WORKS Phase 2) · 작성: 2026-05-31
> 근거 발주: `_TO_메신저세션/2026-05-29_사번SSO.md` §3.5 · §7
> 상태: **메신저 측 코드 구현 완료**, 키 생성·라이브 마이그레이션은 cutover 대기

---

## 0. 한 줄
메신저 = 사내 단일 인증 서버(Identity Provider). HAIST WORKS 는 자체 로그인 제거하고
메신저 SSO(JWT RS256)로 로그인 → `/sso/callback` 에서 토큰 검증·세션 생성.

---

## 1. 엔드포인트 (확정)

| 용도 | 메서드 | URL |
|---|---|---|
| 로그인 화면(진입점) | GET | `https://haist.knknara.co.kr/msg/sso/login?redirect_uri={SP콜백}` |
| 토큰 발급 | POST | `https://haist.knknara.co.kr/msg/api/sso/token` |
| 사용자정보 | GET | `https://haist.knknara.co.kr/msg/api/sso/userinfo` (Bearer) |
| 공개키 | GET | `https://haist.knknara.co.kr/msg/api/sso/public-key` (`?format=jwk` 지원) |
| 토큰 무효화 | POST | `https://haist.knknara.co.kr/msg/api/sso/revoke` (Bearer) |

## 2. 토큰 규격 (확정)

| 항목 | 값 |
|---|---|
| 알고리즘 | **RS256** (메신저 private 서명 / SP 는 public 으로 검증만) |
| Issuer (`iss`) | `https://haist.knknara.co.kr/msg/` |
| Audience (`aud`) | `["haist-works", "knk-internal"]` → HAIST WORKS 는 **`haist-works`** 로 검증 |
| 만료 (`exp`) | **3600초 (1시간)** |
| Subject (`sub`) | **사번**(employee_no) — 예: `5`, `43`, `VN001` |

**JWT payload claim** (userinfo 와 동일 필드):
```
sub(사번), uid(내부PK), pwv(비번버전), name_kr, name_en, name_vi,
dept, position, entity('KOR'|'VN'), email, is_admin(bool)
```

## 3. SSO 로그인 흐름 (구현된 동작)

```
직원 → works.knknara.co.kr 접속 (미인증)
  → SP가 /msg/sso/login?redirect_uri=https://works.knknara.co.kr/sso/callback 로 redirect
  → (메신저) 이미 로그인돼 있으면 즉시 토큰 발급, 아니면 평소 로그인 화면 그대로
  → 로그인 성공 → redirect_uri 로 ?token=<JWT> 붙여 복귀
  → (SP) /sso/callback 에서 JWT 검증(public key) → 세션 생성 → /home
```
- 로그인 화면은 **기존 메신저 화면 그대로** (새 화면 없음, 학습 0) — 발주서 §8.4
- 다국어(한국어/베트남어)는 기존 i18n 자동 분기 그대로 — §8.5

## 4. 검증 코드 (SP 측 참고 — Python)

```python
import jwt
public_key = open("jwt_rs256_public.pem").read()   # /api/sso/public-key 로 받음
decoded = jwt.decode(
    token, public_key, algorithms=["RS256"],
    audience="haist-works",
    issuer="https://haist.knknara.co.kr/msg/",
)
# ★ pwv 검증: SP 는 매 요청마다 /api/sso/userinfo 호출로 최신 유효성 확인 권장.
#   메신저가 비번 변경/revoke 시 password_version+1 → 옛 토큰의 pwv 불일치 → userinfo 가 401.
#   userinfo 401 이면 SP 는 세션 파기 후 /sso/login 으로 재유도.
```

## 5. 보안 정책 (확정)

- **HTTPS 필수** — `/api/sso/*` 는 운영에서 HTTP 거부
- **CORS** — `*.knknara.co.kr` Origin 만 허용
- **Rate limit** — `/api/sso/token` IP당 분당 10회 초과 차단
- **비번 변경/revoke** → `password_version` 증가 → 발급된 토큰 즉시 무효(다음 userinfo 에서 거부)
- private key 는 메신저만 보관, **SP 에는 절대 전달 안 함** (public key 만 공유)

## 6. 실무팀1 측 작업 (HAIST WORKS Phase 2 — 후속)

1. HAIST WORKS `users` 에 `employee_no` 컬럼 + 메신저 사번 기준 매핑
2. 자체 로그인 화면 제거 → `/msg/sso/login?redirect_uri=...` 로 redirect
3. `/sso/callback` 추가 — JWT 수신·검증·세션 생성
4. JWT 검증 미들웨어 (메신저 public key 캐싱, 주기적 갱신)
5. 보호 라우트 진입 시 세션 없으면 `/sso/login` 으로 유도
6. (선택) 매 요청 또는 N분마다 `/api/sso/userinfo` 로 최신 권한·유효성 동기화

## 7. 전달 자산 (cutover 시 함께 제공)

- [ ] `jwt_rs256_public.pem` (cutover 에서 키 생성 후 `/api/sso/public-key` 로 공개)
- [x] API endpoint URL 4개 (위 §1)
- [x] audience 이름: `haist-works`
- [x] 토큰 만료(1시간)·CORS(`*.knknara.co.kr`)·알고리즘(RS256)
- [ ] 테스트용 사번/비번 1쌍 (cutover 후 대표 승인 하에 별도 전달)

## 8. 현재 상태 / 주의

- 메신저 코드(스키마·SSO API·로그인 redirect·비번버전) **구현+로컬검증 완료**, 배포됨
- **키 미생성 상태에서는 `/api/sso/*` 가 503** 반환 (정상 — cutover 에서 키 생성하면 활성)
- 사번 라이브 마이그레이션(130명 username 전환)은 **점심/새벽 백업 직후** 별도 실행 예정
- ⚠ SP 통합 테스트는 **메신저 cutover 완료 후** 시작 (그 전엔 토큰 발급 안 됨)
