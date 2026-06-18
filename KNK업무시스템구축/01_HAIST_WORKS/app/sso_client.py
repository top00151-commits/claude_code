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
    - GET  https://msg.knknara.co.kr/sso/login?redirect_uri=...   (v5H226z492: 컨테이너 분리·전용 도메인)
    - GET  https://msg.knknara.co.kr/api/sso/public-key  (PEM 또는 ?format=jwk)
    - GET  https://msg.knknara.co.kr/api/sso/userinfo    (Bearer)
    - POST https://msg.knknara.co.kr/api/sso/revoke      (Bearer)

JWT 규격:
    - 알고리즘: RS256 (메신저 private 서명, SP는 public으로 검증만)
    - iss: https://msg.knknara.co.kr/   (⚠ 메신저가 이 issuer로 발행해야 검증 통과)
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
# v5H226z118 (2026-05-31): 두 base 분리
#   - PUBLIC: 브라우저 redirect 용 (반드시 외부 도메인)
#   - INTERNAL: 서버측 API 호출용 (NAT loopback 회피 시 localhost)
MESSENGER_BASE = os.environ.get(
    "KNK_MESSENGER_SSO_BASE",
    "https://msg.knknara.co.kr",   # v5H226z492 (2026-06-18): 컨테이너 분리 — 메신저 전용 도메인(기존 haist…/msg)
).rstrip("/")
# 서버 내부 호출용 base. 미설정 시 PUBLIC 과 동일 (NAT loopback 가능 환경)
MESSENGER_INTERNAL_BASE = os.environ.get(
    "KNK_MESSENGER_SSO_INTERNAL_BASE",
    MESSENGER_BASE,
).rstrip("/")
SSO_AUDIENCE = os.environ.get("KNK_SSO_AUDIENCE", "haist-works")
SSO_ISSUER   = os.environ.get(
    "KNK_SSO_ISSUER",
    "https://msg.knknara.co.kr/",   # v5H226z492: 메신저 전용 도메인 issuer (메신저 JWT iss 와 반드시 일치)
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
            f"{MESSENGER_INTERNAL_BASE}/api/sso/public-key",
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
      - iss == 'https://msg.knknara.co.kr/'   (v5H226z492: 컨테이너 분리·전용 도메인)
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
            f"{MESSENGER_INTERNAL_BASE}/api/sso/userinfo",
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
def build_login_url(redirect_uri: str, force: bool = False) -> str:
    """메신저 SSO 로그인 화면 URL 생성.
    redirect_uri 는 절대 URL 권장 (예: https://works.knknara.co.kr/sso/callback)
    force=True 면 force=1 을 실어, 메신저에 이미 로그인돼 있어도 '재로그인 화면'을 강제
    (대표 지시 2026-06-14: 항상 메신저를 통해 로그인). 메신저가 force 미지원이면 자동 무시(안전 폴백)."""
    from urllib.parse import urlencode
    params = {"redirect_uri": redirect_uri}
    if force:
        params["force"] = "1"
    return f"{MESSENGER_BASE}/sso/login?{urlencode(params)}"


# ── 사용자 upsert 헬퍼 (Q1=A 자동 upsert) ───────────────────
def _resolve_team_id(c, dept):
    """v5H226z140: 메신저 dept(부서명/코드) → HAIST WORKS teams.id 매핑.
    매칭 실패 시 None (기존 team_id 유지). 권한이 team_id 기반이라 중요."""
    if not dept:
        return None
    try:
        r = c.execute(
            "SELECT id FROM teams WHERE name=? OR code=? OR name LIKE ? ORDER BY id LIMIT 1",
            (dept, dept, f"%{dept}%"),
        ).fetchone()
        return r["id"] if r else None
    except Exception:
        return None


def upsert_user_from_payload(c, payload: dict) -> Optional[int]:
    """JWT payload (또는 userinfo) 로 HAIST WORKS users 테이블 upsert.

    매칭: ① employee_no → ② (없으면) 이름 같고 사번 없는 레거시/시드 계정 병합 → ③ INSERT
    team_id 는 dept 로 매핑해 설정(권한 동작).

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
    phone   = (payload.get("phone") or "").strip() or None
    is_admin = bool(payload.get("is_admin", False))

    team_id = _resolve_team_id(c, dept)   # 부서 → team_id (권한 동작용)

    # ① 사번으로 매칭
    try:
        row = c.execute(
            "SELECT id, role FROM users WHERE employee_no = ?",
            (emp_no,),
        ).fetchone()
    except Exception:
        # employee_no 컬럼 없음 → 마이그레이션 미적용
        print("[SSO] employee_no 컬럼 없음 — z109 마이그레이션 필요")
        return None

    # ② 사번 매칭 실패 → 이름 같고 사번 없는 레거시/시드 계정 병합 (중복 방지)
    if not row:
        try:
            legacy = c.execute(
                "SELECT id, role FROM users "
                "WHERE name = ? AND (employee_no IS NULL OR TRIM(employee_no)='') "
                "ORDER BY id LIMIT 1",
                (name_kr,),
            ).fetchone()
        except Exception:
            legacy = None
        if legacy:
            try:
                c.execute("UPDATE users SET employee_no=?, login_id=? WHERE id=?",
                          (emp_no, emp_no, legacy["id"]))
                print(f"[SSO] 레거시 계정 병합: {name_kr} → 사번 {emp_no} (id={legacy['id']})")
            except Exception as _e:
                print(f"[SSO] 병합 실패: {_e}")
            row = legacy

    if row:
        # 기존/병합 사용자 — 정보 갱신 (role·password 보존, team_id 는 매핑될 때만)
        c.execute(
            """UPDATE users SET
                 name = COALESCE(?, name),
                 email = COALESCE(?, email),
                 phone = COALESCE(?, phone),
                 name_en = COALESCE(?, name_en),
                 name_vi = COALESCE(?, name_vi),
                 dept_code = COALESCE(?, dept_code),
                 team_id = COALESCE(?, team_id),
                 rank = COALESCE(?, rank),
                 entity = COALESCE(?, entity),
                 is_active = 1
               WHERE id = ?""",
            (name_kr, email, phone, name_en, name_vi, dept, team_id, pos, entity, row["id"]),
        )
        return row["id"]
    else:
        # ③ 신규 사용자 — 메신저에서 처음 보는 사번
        sentinel_pw = "sso_only_no_local_password"  # 자체 로그인 미사용 (NOT NULL 충족용)
        try:
            cur = c.execute(
                """INSERT INTO users (
                     name, login_id, password, email, phone, employee_no, entity,
                     name_en, name_vi, dept_code, team_id, rank, role, is_active,
                     password_version, lang
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?)""",
                (
                    name_kr,
                    emp_no,        # login_id = 사번
                    sentinel_pw,
                    email,
                    phone,
                    emp_no,        # employee_no
                    entity,
                    name_en,
                    name_vi,
                    dept,
                    team_id,       # 부서 매핑된 팀
                    pos,
                    "admin" if is_admin else "member",
                    "vi" if entity == "VN" else "ko",
                ),
            )
            return cur.lastrowid
        except Exception as e:
            print(f"[SSO] upsert INSERT failed: {e}")
            return None


# =====================================================
# v5H226z142 (2026-05-31): 메신저 직원 명부 동기화
#   메신저 'GET /api/sso/directory' 호출 → 전 직원 upsert (사번·다국어이름·부서·메일·연락처)
#   발주: _TO_메신저세션/2026-05-31_직원명부API_발주.md
#   메신저 API 완료 전엔 통신오류 반환(휴면) — 완료되면 즉시 동작.
# =====================================================
SSO_SERVICE_KEY = os.environ.get("KNK_SSO_SERVICE_KEY", "")  # 서버↔서버 공유키


def sync_directory_from_messenger(c) -> dict:
    """메신저 직원 명부를 가져와 전 직원 upsert.
    반환: {ok, synced, total} 또는 {ok:False, error}"""
    if not SSO_SERVICE_KEY:
        return {"ok": False, "error": "공유키(KNK_SSO_SERVICE_KEY) 미설정 — NAS .env 에 등록 필요"}
    url = f"{MESSENGER_INTERNAL_BASE}/api/sso/directory"
    try:
        r = httpx.get(url, headers={"X-SSO-Service-Key": SSO_SERVICE_KEY}, timeout=20.0)
    except Exception as e:
        return {"ok": False, "error": f"메신저 연결 실패: {e} (명부 API 준비 전일 수 있음)"}
    if r.status_code == 403:
        return {"ok": False, "error": "서비스키 거부(403) — 양쪽 KNK_SSO_SERVICE_KEY 확인"}
    if r.status_code == 404:
        return {"ok": False, "error": "명부 API(/api/sso/directory) 없음 — 메신저 준비 전"}
    if r.status_code != 200:
        return {"ok": False, "error": f"예상치 못한 status {r.status_code}"}
    try:
        users = (r.json() or {}).get("users") or []
    except Exception as e:
        return {"ok": False, "error": f"응답 파싱 실패: {e}"}

    synced = 0
    for u in users:
        try:
            payload = {
                "sub": u.get("employee_no"),
                "name_kr": u.get("name_kr"),
                "name_en": u.get("name_en"),
                "name_vi": u.get("name_vi"),
                "dept": u.get("dept"),
                "position": u.get("position"),
                "entity": u.get("entity"),
                "email": u.get("email"),
                "phone": u.get("phone"),
                "is_admin": u.get("is_admin"),
            }
            if upsert_user_from_payload(c, payload):
                synced += 1
        except Exception as _e:
            print(f"[SSO] 명부 동기화 항목 실패: {_e}")
    return {"ok": True, "synced": synced, "total": len(users)}


# =====================================================
# v5H226z391 (2026-06-13, 대표 지시): WORKS → 메신저 업무 통보 (제작요청 등)
#   메신저 'POST /api/works/notify' 호출 → 'WORKS 알림' 봇이 대상 직원에게 1:1 메시지+푸시.
#   사번(employee_no) 기준. 공유키(X-SSO-Service-Key) 필수. 실패해도 호출측 등록은 진행하되
#   침묵 금지(에러 문자열 반환 — 연결성 안전 원칙).
# =====================================================
def notify_via_messenger(employee_nos, title, body, link="", timeout=10.0) -> dict:
    """대상 직원(사번 목록)에게 메신저로 1:1 업무 통보.
    반환: {ok, sent, skipped, room_count, skipped_list} 또는 {ok:False, error}."""
    emps = [str(e).strip() for e in (employee_nos or []) if str(e).strip()]
    if not emps:
        return {"ok": False, "error": "수신 사번 없음(메신저 통보 생략)"}
    if not SSO_SERVICE_KEY:
        return {"ok": False, "error": "공유키(KNK_SSO_SERVICE_KEY) 미설정 — NAS .env 등록 필요"}
    url = f"{MESSENGER_INTERNAL_BASE}/api/works/notify"
    try:
        r = httpx.post(
            url,
            headers={"X-SSO-Service-Key": SSO_SERVICE_KEY},
            json={"employee_nos": emps, "title": title, "body": body, "link": link},
            timeout=timeout,
        )
    except Exception as e:
        return {"ok": False, "error": f"메신저 연결 실패: {e} (통보 API 준비 전일 수 있음)"}
    if r.status_code == 403:
        return {"ok": False, "error": "서비스키 거부(403) — 양쪽 KNK_SSO_SERVICE_KEY 확인"}
    if r.status_code == 404:
        return {"ok": False, "error": "통보 API(/api/works/notify) 없음 — 메신저 배포 전"}
    if r.status_code != 200:
        return {"ok": False, "error": f"예상치 못한 status {r.status_code}"}
    try:
        d = r.json() or {}
    except Exception as e:
        return {"ok": False, "error": f"응답 파싱 실패: {e}"}
    return {
        "ok": bool(d.get("ok")),
        "sent": len(d.get("sent") or []),
        "skipped": len(d.get("skipped") or []),
        "room_count": d.get("room_count") or 0,
        "skipped_list": d.get("skipped") or [],
    }


# =====================================================
# v5H226z143 (2026-06-01): 메신저 직원 → WORKS **DB 직접** 1회 동기화
#   대표 지시(2026-06-01): API/공유키 방식 보류. WORKS·메신저가 같은 컨테이너에
#   떠 있으므로 메신저 DB 를 직접 읽어 전 직원을 WORKS 에 동일 등록.
#   기존 upsert_user_from_payload 재사용(사번매칭·이름병합·team_id매핑·COALESCE).
#   미리보기(dry-run)는 호출측에서 rollback 으로 처리.
# =====================================================
import sqlite3 as _sqlite3

MESSENGER_DB_PATH = os.environ.get(
    "KNK_MESSENGER_DB", "/opt/knk_messenger/data/messenger.db")


def _messenger_row_to_payload(r) -> dict:
    """메신저 users 행 → upsert_user_from_payload 가 받는 payload dict."""
    keys = r.keys()
    g = lambda k: (r[k] if k in keys else None)
    ent = (g("entity") or "").strip().upper()
    name_vn = (g("display_name_vn") or "").strip()
    if ent not in ("KOR", "VN"):
        ent = "VN" if name_vn else "KOR"   # entity 미지정 추정
    emp_no = ""
    if g("employee_no") and str(g("employee_no")).strip():
        emp_no = str(g("employee_no")).strip()
    elif g("username") and str(g("username")).strip():
        emp_no = str(g("username")).strip()   # 사번 없으면 username (사번=로그인ID 정책)
    name = (g("display_name") or "").strip() or (g("username") or "").strip()
    return {
        "sub": emp_no,
        "employee_no": emp_no,
        "name_kr": name,
        "name_en": (g("display_name_en") or "").strip() or None,
        "name_vi": name_vn or None,
        "dept": (g("department") or "").strip() or None,
        "position": (g("title") or "").strip() or None,
        "entity": ent,
        "email": (g("email") or "").strip() or None,
        "phone": (g("phone") or "").strip() or None,
        "is_admin": False,
    }


def _read_messenger_users(msg_db: str):
    """메신저 DB users (게스트 제외) 읽기. 컬럼 호환 위해 SELECT * 사용."""
    conn = _sqlite3.connect(f"file:{msg_db}?mode=ro", uri=True)
    conn.row_factory = _sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM users WHERE COALESCE(is_guest,0)=0 "
            "ORDER BY (employee_no IS NULL) ASC"
        ).fetchall()
    finally:
        conn.close()
    return rows


def sync_employees_from_messenger_db(c, msg_db: str = None) -> dict:
    """메신저 DB 직접 동기화. c=WORKS DB 커서(트랜잭션은 호출측 제어).

    dry-run/apply 구분은 호출측 commit/rollback 으로. 여기선 upsert 만 수행.
    반환: {ok, total, updated, inserted, skipped, works_only[], sample_new[], sample_upd[]}
          또는 {ok:False, error}
    """
    msg_db = msg_db or MESSENGER_DB_PATH
    if not os.path.exists(msg_db):
        return {"ok": False, "error": f"메신저 DB 를 찾을 수 없습니다: {msg_db} "
                "(같은 컨테이너 경로 확인 — 환경변수 KNK_MESSENGER_DB 로 지정 가능)"}
    try:
        rows = _read_messenger_users(msg_db)
    except Exception as e:
        return {"ok": False, "error": f"메신저 DB 읽기 실패: {e}"}

    # v5H226z493: 출처(DB)만 다르고 통계/upsert 로직은 공유 코어로 — API 출처와 동일하게.
    payloads = [_messenger_row_to_payload(r) for r in rows]
    res = _sync_employees_core(c, payloads)
    res["msg_db"] = msg_db
    res["source"] = "messenger_db"
    return res


def _sync_employees_core(c, payloads) -> dict:
    """payloads(upsert payload dict 목록) → 미리보기 통계 + upsert. 트랜잭션은 호출측(commit/rollback).
    출처(메신저 DB 파일 / HTTP 디렉터리 API) 무관하게 동일 로직.
    반환: {ok, total, updated, inserted, skipped, works_only[], sample_new[], sample_upd[]}"""
    updated = inserted = skipped = 0
    sample_new, sample_upd = [], []
    msg_names = set()
    for payload in payloads:
        emp_no = str(payload.get("sub") or payload.get("employee_no") or "").strip()
        name = (payload.get("name_kr") or payload.get("name") or "").strip()
        if name:
            msg_names.add(name)
        if not emp_no:
            skipped += 1
            continue
        # 신규/갱신 분류: upsert 전에 매칭 존재여부 확인
        exists = None
        try:
            exists = c.execute(
                "SELECT id FROM users WHERE employee_no=?", (emp_no,)).fetchone()
            if not exists and name:
                exists = c.execute(
                    "SELECT id FROM users WHERE name=? AND "
                    "(employee_no IS NULL OR TRIM(employee_no)='') LIMIT 1",
                    (name,)).fetchone()
        except Exception:
            exists = None
        try:
            rid = upsert_user_from_payload(c, payload)
        except Exception as _e:
            print(f"[SYNC] {name} 실패: {_e}")
            rid = None
        if rid is None:
            skipped += 1
            continue
        if exists:
            updated += 1
            if len(sample_upd) < 15:
                sample_upd.append(f"[{emp_no}] {name}")
        else:
            inserted += 1
            if len(sample_new) < 15:
                sample_new.append(f"[{emp_no}] {name}")

    # WORKS 에만 있고 메신저엔 없는 사람 (수동 판단용 — 자동 삭제/비활성 안 함)
    works_only = []
    if msg_names:
        try:
            ph = ",".join("?" * len(msg_names))
            works_only = [
                {"name": x["name"], "login_id": x["login_id"]}
                for x in c.execute(
                    f"SELECT name, login_id FROM users WHERE name NOT IN ({ph}) "
                    "ORDER BY name", tuple(msg_names)).fetchall()
            ]
        except Exception:
            works_only = []

    return {"ok": True, "total": len(payloads), "updated": updated,
            "inserted": inserted, "skipped": skipped,
            "works_only": works_only, "sample_new": sample_new,
            "sample_upd": sample_upd}


def sync_employees_from_messenger_api(c) -> dict:
    """v5H226z493 (컨테이너 분리·대표 지시): 메신저 명부를 'GET /api/sso/directory'(HTTP)로 받아 동기화.
    DB 파일 직접읽기(sync_employees_from_messenger_db) 대체 — 분리 후 볼륨 마운트 불필요.
    미리보기/적용은 호출측 commit/rollback. 반환 = _sync_employees_core 동일 형태(+source)."""
    if not SSO_SERVICE_KEY:
        return {"ok": False, "error": "공유키(KNK_SSO_SERVICE_KEY) 미설정 — NAS .env 에 등록 필요"}
    url = f"{MESSENGER_INTERNAL_BASE}/api/sso/directory"
    try:
        r = httpx.get(url, headers={"X-SSO-Service-Key": SSO_SERVICE_KEY}, timeout=20.0)
    except Exception as e:
        return {"ok": False, "error": f"메신저 연결 실패: {e} (명부 API 준비 전일 수 있음)"}
    if r.status_code == 403:
        return {"ok": False, "error": "서비스키 거부(403) — 양쪽 KNK_SSO_SERVICE_KEY 확인"}
    if r.status_code == 404:
        return {"ok": False, "error": "명부 API(/api/sso/directory) 없음 — 메신저 준비 전(또는 메신저 미배포)"}
    if r.status_code != 200:
        return {"ok": False, "error": f"예상치 못한 status {r.status_code}"}
    try:
        users = (r.json() or {}).get("users") or []
    except Exception as e:
        return {"ok": False, "error": f"응답 파싱 실패: {e}"}
    payloads = [{
        "sub": u.get("employee_no"), "employee_no": u.get("employee_no"),
        "name_kr": u.get("name_kr"), "name_en": u.get("name_en"), "name_vi": u.get("name_vi"),
        "dept": u.get("dept"), "position": u.get("position"), "entity": u.get("entity"),
        "email": u.get("email"), "phone": u.get("phone"), "is_admin": u.get("is_admin"),
    } for u in users]
    res = _sync_employees_core(c, payloads)
    res["source"] = "messenger_api"
    return res
