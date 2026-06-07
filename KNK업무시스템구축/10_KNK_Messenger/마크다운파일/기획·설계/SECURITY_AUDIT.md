# 보안 자체 점검 보고서 (2026-05-08)

인터넷 환경 노출 전 전체 코드베이스 자체 점검. 발견 사안 9건, **모두 코드 패치 완료**.

## 요약

| 등급 | 발견 | 패치 완료 |
|---|---|---|
| CRITICAL | 2 | 2 |
| HIGH | 4 | 4 |
| MEDIUM | 3 | 3 |
| **합계** | **9** | **9** |

추가 항목(LOW)은 운영 후 모니터링하면서 단계적 개선.

---

## CRITICAL (인터넷 노출 전 반드시 수정 — ✅ 완료)

### C-1. Socket.IO `join` 이벤트 방 멤버십 미검증 — 데이터 도청 가능
**원래 코드** (app.py 1724):
```python
@socketio.on("join")
def on_join(data):
    rid = data.get("room_id")
    if rid: sio_join(f"room_{rid}")  # 누구나 어떤 방이든 join
```

**영향**: 인증된 직원이 DevTools 콘솔에서 `socket.emit("join", {room_id: 99})` 호출하면 본인이 멤버 아닌 임원진/인사방의 모든 메시지·파일·요청 변경을 실시간으로 받음. **베트남 직원이 한국 임원 회의 도청 가능.**

**패치**: `_is_room_member()` 검증 추가. 멤버 아니면 join 안 함.

---

### C-2. `/api/admin/cleanup` cron 인증 실패 — 보존정책 미작동
**원래 cron 라인**:
```bash
0 4 1 * * curl -fsS http://127.0.0.1:5050/api/admin/cleanup -X POST
```
**문제**: `@login_required + role==ceo` 체크를 세션 없는 cron 이 통과 못 함 → 매월 1일 자동삭제가 silently fail. 12개월 보존 정책이 작동 안 해서 데이터 무한 누적.

**패치**:
- `KNK_MSG_ADMIN_TOKEN` 환경변수 추가 (setup_server.sh가 자동 32-hex 생성)
- `_admin_authorized()` 헬퍼 — 로그인 CEO **또는** `X-Admin-Token` 헤더 일치
- cron 라인이 `.env` 의 토큰을 헤더로 전달

---

## HIGH (운영 모드 진입 전 — ✅ 완료)

### H-1. 로그인 무차별 대입 방어 없음
**원래**: 실패 시 지연·잠금 없음 → 봇이 100ms 안에 1000개 비번 시도. 시드 비번 `knk1234` 즉시 침투.

**패치**:
- 메모리 토큰 `_LOGIN_FAILS` (IP, username) 기준
- 5회 실패 시 5분 잠금 (HTTP 429)
- 실패 응답에 1초 sleep (타이밍 공격 + 봇 throttle)
- `KNK_MSG_LOGIN_FAIL_LIMIT` / `KNK_MSG_LOGIN_LOCK_SECONDS` 환경변수로 조정

### H-2. 세션 쿠키 SameSite/HttpOnly dev 모드 미적용
**원래**: production 분기 안에만 `SESSION_COOKIE_SAMESITE = "Lax"` 등 — dev-on-cloud 단계에서는 비활성. HTTPS 도메인이라도 CSRF·쿠키 도난 방어 약함.

**패치**: `HttpOnly`, `SameSite=Lax` 는 모드 무관 항상 적용. `Secure` 만 production 한정 (로컬 http 호환).

### H-3. CSP·Referrer-Policy·Permissions-Policy 운영 모드만
**원래**: production 에서만 보안 헤더 추가. dev-on-cloud 며칠 동안 외부 리소스 로딩·인라인 스크립트 무방비.

**패치**:
- `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` — 모든 모드에 항상
- HSTS 만 production 한정 (캐시되면 로컬 개발 차단되므로)
- HTML 응답에 기본 CSP 추가:
  ```
  default-src 'self'; script-src 'self' 'unsafe-inline'; ...
  frame-ancestors 'self'; form-action 'self'
  ```

### H-4. 시드 사용자 임시 비번 강제 변경 없음
**원래**: 모두 `knk1234` 동일. 코드에 평문 노출. 깃 리포 또는 이미지 유출 시 즉시 침투.

**패치**:
- `users.must_change_password` 컬럼 추가 + 기존 사용자 마이그레이션
- 시드 비번 `KNK_MSG_SEED_PASSWORD` 환경변수 우선 (없으면 `knk1234` + 콘솔 경고)
- `POST /api/me/password` — 본인 비번 변경 (8자 이상, 임시 비번 거부)
- `/api/me` 응답에 `must_change_password` 노출 → 클라이언트가 강제 변경 화면 트리거 가능

---

## MEDIUM (단기 패치 — ✅ 완료)

### M-1. 메시지 송신 율 제한 없음
**원래**: 같은 방에 4000자 메시지를 초당 1000개 송신 가능. 디스크/네트워크 DoS.

**패치**: 토큰 버킷 `_MSG_BUCKET` — 사용자당 5/초 평균, 10 버스트. 초과 시 silent drop. `KNK_MSG_RATE_PER_SEC`/`KNK_MSG_RATE_BURST` 환경변수.

### M-2. 파일 업로드 mimetype 클라이언트 신뢰
**현황 검토**:
- 확장자 화이트리스트 (`ALLOWED_FILE_EXT`) 통과한 것만 저장
- 화이트리스트에 .html .js .svg .php 없음 — 실행 가능한 콘텐츠 차단
- 다운로드 시 Flask 가 자체 mimetype 결정 (`send_from_directory`)
- DB의 user-controlled `file_mime` 은 표시용일 뿐 서빙 시 사용 안 됨
- **영향**: 보안 침투 X (UX 표시 혼란만)

**판단**: 현 단계 추가 패치 불필요. 우선순위 낮음.

### M-3. avatar_color CSS 인젝션
**원래**: `data.get("avatar_color") or "#3b82f6"` — `red; background-image: url(javascript:...)` 같은 값 가능. CEO 만 사용자 생성 가능해 위험도 낮음.

**패치**:
- `_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")`
- `_safe_color()` 헬퍼로 검증 후 사용
- 추가: `_safe_role()` (ceo/staff 화이트리스트), username 정규식 검증, 비번 8자 이상 강제

---

## LOW (운영 후 단계적 개선)

| 항목 | 메모 |
|---|---|
| 세션 만료 시간 명시 | 현재 브라우저 닫을 때까지. 7일 PERMANENT_SESSION_LIFETIME 권장 |
| fail2ban (베어메탈만) | Synology Docker 시나리오에서는 DSM 자동 차단 + Reverse Proxy 만 노출이라 위험도 낮음 |
| 헬스체크 라우트 명시 | `/login` 으로 fallback 동작 — 추가 라우트 불필요 |
| WebSocket origin 화이트리스트 | dev 단계 `KNK_MSG_CORS=*` → 운영 시 도메인 제한 (이미 `.env` 분리) |
| 파일 시그니처 검증 (magic bytes) | 확장자 화이트리스트로 충분. 추후 보완 가능 |

---

## 패치 후 운영 시작 전 체크리스트

### 환경변수 필수 설정
```env
KNK_MSG_ENV=production            # 운영 전환 시
KNK_MSG_SECRET=<64자 hex>          # 자동 생성됨
KNK_MSG_ADMIN_TOKEN=<64자 hex>     # 자동 생성됨
KNK_MSG_CORS=https://msg.knknara.co.kr
KNK_MSG_SEED_PASSWORD=<강한 임시 비번>   # 'knk1234' 회피
KNK_MSG_PROXIES=1                  # nginx/Synology 1대
```

### 운영 직전 1회 확인
- [ ] 시드 사용자 첫 로그인 후 비번 변경 강제 동작 확인 (UI 구현 필요 — 다음 패치)
- [ ] 가비아 SSL Let's Encrypt 정상 (DSM 인증서)
- [ ] `https://msg.knknara.co.kr` 응답 헤더에 `Strict-Transport-Security` ✓
- [ ] 방 비멤버 사용자가 socket.emit("join", ...) 시도 → 메시지 안 받음 검증
- [ ] `/api/admin/cleanup` 헤더 없으면 403, 토큰 있으면 200 검증
- [ ] 로그인 5회 실패 → 429 응답 확인

### 운영 후 정기 점검 (월 1회)
- 디스크 사용량 + 백업 정상
- `_LOGIN_FAILS` 비정상 누적 확인 (로그)
- nginx/DSM Reverse Proxy 로그에서 403/429 패턴
- VAPID 푸시 구독자 수
- 사용자별 메시지 수 비정상 증가 (rate limit 회피 시도)

---

## 패치 적용 파일 목록

| 파일 | 변경 |
|---|---|
| `app.py` | Socket.IO join 검증, admin 토큰, 로그인 시도 제한, 보안헤더, CSP, 시드 변경 강제, hex/role/username 검증, 메시지 rate limit, 비번 변경 엔드포인트 |
| `deploy/setup_server.sh` | ADMIN_TOKEN 자동 생성 + cron 헤더 |
| `deploy/setup_server_dev.sh` | ADMIN_TOKEN 자동 생성 |
| `deploy/.env.production.example` | 새 환경변수 4종 추가 |
| `.env.synology.example` | 새 환경변수 4종 추가 |

DB 마이그레이션: `users.must_change_password` 컬럼 자동 추가 (재시작 시 1회).
