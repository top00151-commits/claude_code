"""
sso_client.py — 메신저 SSO 클라이언트 (HAIST WORKS Phase 2)
=================================================================

발주: _TO_빅터/메신저_사번SSO_인터페이스.md (2026-05-31 메신저 세션)
작성: 빅터(01) · 2026-05-31 (v5H226z117)

목적:
    HAIST WORKS 가 메신저(Identity Provider) 가 발급한 JWT RS256 토큰을
    검증하고 사용자 정보를 동기화하기 위한 클라이언트 모듈.

설계 결정 (대표 결재 2026-05-31):
    Q1=A: SSO callback 시 자동 upsert (메신저가 마스터, HAIST WORKS는 캐시)
    Q2=B: admin 백도어 유지 (메신저 장애 대비)
    Q3=A: public key 메모리 캐싱 (TTL 1시간)
    Q4=B: 5분 주기 pwv 동기화 (req 분당 < 정확성/부하 균형)
    Q5: 코드 작성 후 push, 메신저 cutover 통보 후 NAS 적용
    Q6=C: POST /login 은 admin 백도어 + 일반 사용자는 SSO redirect

확정 인터페이스 (메신저 측):
    - GET  https://haist.knknara.co.kr/msg/sso/login?redirect_uri=...
    - GET  https://haist.knknara.co.kr/msg/api/sso/public-key  (PEM 또는 ?format=jwk)
    - GET  https://haist.knknara.co.kr/msg/api/sso/userinfo    (Bearer)
    - POST https://haist.knknara.co.kr/msg/api/sso/revoke      (Bearer)

JWT 규격:
    - 알고리즘: RS256 (메신저 private 서명, SP는 public으로 검증만)
    - iss: https://haist.knknara.co.kr/msg/
    - aud: haist-works
    - exp: 3600초 (1시간)
    - sub: 사번 (employee_no)
    - claim: sub/uid/pwv/name_kr/name_en/name_vi/dept/position/entity/email/is_admin
"""
from __future__ import annotations
import os
import time
from typing import Optional

import httpx
import jwt as pyjwt


# ── 설정 (환경변수로 override 가능) ──────────────────────────
MESSENGER_BASE = os.environ.get(
    "KNK_MESSENGER_SSO_BASE",
    "https://haist.knknara.co.kr/msg",
).rstrip("/")
SSO_AUDIENCE = os.environ.get("KNK_SSO_AUDIENCE", "haist-works")
SSO_ISSUER   = os.environ.get(
    "KNK_SSO_ISSUER",
    "https://haist.knknara.co.kr/msg/",
)

# public key 캐싱 (메모리, TTL 1시간) — Q3=A
_PUBKEY_CACHE: dict = {
    "pem": None,        # 다운로드한 PEM 문자열
    "fetched_at": 0,    # epoch sec
}
_PUBKEY_TTL_SEC = 3600  # 1시간

# pwv 동기화 캐싱 (사용자별 마지막 확인 시각) — Q4=B
_PWV_CHECK_CACHE: dict[int, float] = {}  # user_id → epoch sec
PWV_CHECK_INTERVAL_SEC = 300  # 5분

# 요청 타임아웃
_HTTP_TIMEOUT_SEC = 5.0


# ── public key 캐싱 / fetch ──────────────────────────────────
def get_public_key(force_refresh: bool = False) -> Optional[str]:
    """메신저 public key (PEM) 조회 — 메모리 캐싱, TTL 1시간"""
    now = time.time()
    if (not force_refresh) and _PUBKEY_CACHE["pem"] and (now - _PUBKEY_CACHE["fetched_at"] < _PUBKEY_TTL_SEC):
        return _PUBKEY_CACHE["pem"]
    try:
        r = httpx.get(
            f"{MESSENGER_BASE}/api/sso/public-key",
            timeout=_HTTP_TIMEOUT_SEC,
            follow_redirects=True,
        )
        if r.status_code == 200 and r.text.strip().startswith("-----BEGIN"):
            _PUBKEY_CACHE["pem"] = r.text.strip()
            _PUBKEY_CACHE["fetched_at"] = now
            return _PUBKEY_CACHE["pem"]
        # 메신저가 키 미생성 시 503 — 캐싱 안 함 (다음 호출 재시도)
        print(f"[SSO] public key fetch failed: {r.status_code}")
    except Exception as e:
        print(f"[SSO] public key error: {e}")
    return _PUBKEY_CACHE["pem"]  # 옛 캐시라도 반환 (graceful)


def invalidate_public_key_cache():
    """수동 무효화 — 키 회전 등 운영 작업 시"""
    _PUBKEY_CACHE["pem"] = None
    _PUBKEY_CACHE["fetched_at"] = 0


# ── JWT 검증 ─────────────────────────────────────────────────
def verify_token(token: str) -> Optional[dict]:
    """JWT 검증 → payload dict 반환. 실패 시 None.

    검증 항목:
      - 서명 (RS256, public key)
      - aud == 'haist-works'
      - iss == 'https://haist.knknara.co.kr/msg/'
      - exp (자동)
    """
    if not token or not isinstance(token, str):
        return None
    pem = get_public_key()
    if not pem:
        print("[SSO] verify_token: public key 미수신 — 메신저 cutover 전?")
        return None
    try:
        payload = pyjwt.decode(
            token,
            pem,
            algorithms=["RS256"],
            audience=SSO_AUDIENCE,
            issuer=SSO_ISSUER,
            # exp/iat/nbf 검증 default ON
        )
        return payload
    except pyjwt.ExpiredSignatureError:
        print("[SSO] verify_token: 토큰 만료")
    except pyjwt.InvalidAudienceError:
        print(f"[SSO] verify_token: audience 불일치 (expected {SSO_AUDIENCE})")
    except pyjwt.InvalidIssuerError:
        print(f"[SSO] verify_token: issuer 불일치 (expected {SSO_ISSUER})")
    except pyjwt.InvalidTokenError as e:
        print(f"[SSO] verify_token: invalid - {e}")
    except Exception as e:
        # public key 만료/변경 → 캐시 무효화 + 1회 재시도
        print(f"[SSO] verify_token: 예외 ({e}) — public key 재조회 후 1회 재시도")
        invalidate_public_key_cache()
        pem2 = get_public_key(force_refresh=True)
        if pem2 and pem2 != pem:
            try:
                return pyjwt.decode(
                    token, pem2,
                    algorithms=["RS256"],
                    audience=SSO_AUDIENCE,
                    issuer=SSO_ISSUER,
                )
            except Exception as e2:
                print(f"[SSO] verify_token: 재시도도 실패 ({e2})")
    return None


# ── userinfo 호출 (pwv 검증 포함) ────────────────────────────
def fetch_userinfo(token: str) -> Optional[dict]:
    """Bearer 토큰으로 /api/sso/userinfo 호출 → 최신 사용자 정보.
    pwv 불일치 시 메신저가 401 반환 → 호출자가 세션 파기·재로그인 유도."""
    if not token:
        return None
    try:
        r = httpx.get(
            f"{MESSENGER_BASE}/api/sso/userinfo",
            headers={"Authorization": f"Bearer {token}"},
            timeout=_HTTP_TIMEOUT_SEC,
        )
        if r.status_code == 200:
            return r.json()
        if r.status_code in (401, 403):
            # pwv 불일치 / 토큰 무효 → 세션 파기 신호
            return {"_invalid": True, "status": r.status_code}
        print(f"[SSO] userinfo unexpected status: {r.status_code}")
    except Exception as e:
        print(f"[SSO] userinfo error: {e}")
    return None


# ── pwv 주기 동기화 (Q4=B: 5분) ──────────────────────────────
def should_check_pwv(user_id: int) -> bool:
    """이 사용자의 pwv 를 다시 확인할 시점인지.
    마지막 확인 후 5분 경과 시 True."""
    now = time.time()
    last = _PWV_CHECK_CACHE.get(user_id, 0)
    return (now - last) >= PWV_CHECK_INTERVAL_SEC


def mark_pwv_checked(user_id: int):
    """pwv 검증 완료 표시 (다음 5분간 skip)"""
    _PWV_CHECK_CACHE[user_id] = time.time()


def invalidate_pwv_check(user_id: int):
    """수동 무효화 — 세션 파기·재로그인 시"""
    _PWV_CHECK_CACHE.pop(user_id, None)


# ── 로그인 URL 빌더 ──────────────────────────────────────────
def build_login_url(redirect_uri: str) -> str:
    """메신저 SSO 로그인 화면 URL 생성.
    redirect_uri 는 절대 URL 권장 (예: https://works.knknara.co.kr/sso/callback)"""
    from urllib.parse import urlencode
    qs = urlencode({"redirect_uri": redirect_uri})
    return f"{MESSENGER_BASE}/sso/login?{qs}"


# ── 사용자 upsert 헬퍼 (Q1=A 자동 upsert) ───────────────────
def upsert_user_from_payload(c, payload: dict) -> Optional[int]:
    """JWT payload (또는 userinfo) 로 HAIST WORKS users 테이블 upsert.

    매칭: employee_no UNIQUE → 있으면 UPDATE / 없으면 INSERT

    Returns:
        users.id (내부 PK) 또는 None (실패)
    """
    if not payload:
        return None
    emp_no = str(payload.get("sub") or payload.get("employee_no") or "").strip()
    if not emp_no:
        return None

    name_kr = (payload.get("name_kr") or payload.get("name") or "").strip() or emp_no
    name_en = (payload.get("name_en") or "").strip() or None
    name_vi = (payload.get("name_vi") or "").strip() or None
    dept    = (payload.get("dept") or payload.get("dept_code") or "").strip() or None
    pos     = (payload.get("position") or payload.get("rank") or "").strip() or None
    entity  = (payload.get("entity") or "").strip() or None
    email   = (payload.get("email") or "").strip() or None
    is_admin = bool(payload.get("is_admin", False))

    # 기존 사용자 조회 (employee_no UNIQUE)
    try:
        row = c.execute(
            "SELECT id, role FROM users WHERE employee_no = ?",
            (emp_no,),
        ).fetchone()
    except Exception:
        # employee_no 컬럼 없음 → 마이그레이션 미적용
        print("[SSO] employee_no 컬럼 없음 — z109 마이그레이션 필요")
        return None

    if row:
        # 기존 사용자 — 정보 갱신 (role 은 보존, password 미변경)
        c.execute(
            """UPDATE users SET
                 name = COALESCE(?, name),
                 email = COALESCE(?, email),
                 name_en = COALESCE(?, name_en),
                 name_vi = COALESCE(?, name_vi),
                 dept_code = COALESCE(?, dept_code),
                 rank = COALESCE(?, rank),
                 entity = COALESCE(?, entity),
                 is_active = 1
               WHERE id = ?""",
            (name_kr, email, name_en, name_vi, dept, pos, entity, row["id"]),
        )
        return row["id"]
    else:
        # 신규 사용자 — 메신저에서 처음 보는 사번
        # password 는 사용 안 함 (자체 로그인은 admin 백도어만)
        # 그래도 NOT NULL 제약이 있으니 sentinel 값 저장
        sentinel_pw = "sso_only_no_local_password"
        try:
            cur = c.execute(
                """INSERT INTO users (
                     name, login_id, password, email, employee_no, entity,
                     name_en, name_vi, dept_code, rank, role, is_active,
                     password_version, lang
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?)""",
                (
                    name_kr,
                    emp_no,        # login_id = 사번
                    sentinel_pw,
                    email,
                    emp_no,        # employee_no
                    entity,
                    name_en,
                    name_vi,
                    dept,
                    pos,
                    "admin" if is_admin else "member",
                    "vi" if entity == "VN" else "ko",
                ),
            )
            return cur.lastrowid
        except Exception as e:
            print(f"[SSO] upsert INSERT failed: {e}")
            return None
