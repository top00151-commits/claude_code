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


# ── WORKS 단일 로그아웃 (대표 지시 2026-07-05): 사번으로 로그아웃 시각 조회 (토큰 불필요·1분 주기) ──
_STATUS_CHECK_CACHE: dict[int, float] = {}   # user_id → epoch sec
STATUS_CHECK_INTERVAL_SEC = 60


def should_check_status(user_id: int) -> bool:
    """메신저 로그아웃 상태를 다시 확인할 시점인지 (마지막 확인 후 60초)."""
    return (time.time() - _STATUS_CHECK_CACHE.get(user_id, 0)) >= STATUS_CHECK_INTERVAL_SEC


def mark_status_checked(user_id: int):
    """상태 확인 완료 표시 — 성공/실패 무관(장애 시 폭주 방지 위해 실패도 60초 쓰로틀)."""
    _STATUS_CHECK_CACHE[user_id] = time.time()


def fetch_sso_status(employee_no: str) -> Optional[dict]:
    """[서비스키] 사번으로 메신저의 pwv + 로그아웃 시각(logout_at) 조회. 토큰 불필요(만료 무관).
    반환 {pwv, logout_at} 또는 None(오류·미도달·키없음). None 이면 판단 보류(로그아웃 안 함=graceful)."""
    emp = str(employee_no or "").strip()
    if not emp:
        return None
    key = get_service_key()
    if not key:
        return None
    try:
        r = httpx.get(
            f"{MESSENGER_INTERNAL_BASE}/api/sso/pwv",
            params={"employee_no": emp},
            headers={"X-SSO-Service-Key": key},
            timeout=_HTTP_TIMEOUT_SEC,
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[SSO] status 조회 오류: {e}")
    return None


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
def parse_messenger_dept(dept):
    """v5H226z540 (대표 지시 '메신저 체계 도입'): 메신저 부서코드 분해.
    예) '01_KOR/00_총괄' → {'entity':'KOR','func':'총괄','func_code':'00','raw':...}
        '02_VN/04_설계'  → {'entity':'VN','func':'설계','func_code':'04', ...}
        '기술영업팀'      → {'entity':None,'func':'기술영업팀','func_code':None, ...}
    법인(KOR/VN)은 entity 축으로 분리하고, 팀 매핑은 '기능부서명(func)'으로 한다."""
    import re
    if not dept:
        return {"entity": None, "func": None, "func_code": None, "raw": ""}
    raw = str(dept).strip()
    entity = None
    m = re.search(r"(KOR|KR|KO|VN|VNM)", raw, re.I)
    if m:
        tok = m.group(1).upper()
        entity = "VN" if tok in ("VN", "VNM") else "KOR"   # KR/KO/KOR → KOR
    tail = raw.split("/")[-1].strip()           # '00_총괄'
    func_code = None
    mm = re.match(r"\s*(\d+)\s*[_\-]\s*(.+)$", tail)
    if mm:
        func_code = mm.group(1)
        func = mm.group(2).strip()
    else:
        # 선두 코드가 없으면 tail 자체가 부서명 (단, '01_KOR' 같은 국가토큰은 부서명 아님)
        func = "" if re.fullmatch(r"\d+[_\-](KOR|KR|KO|VN|VNM)", tail, re.I) else tail
    return {"entity": entity, "func": (func or None), "func_code": func_code, "raw": raw}


def _norm_entity(entity):
    """KR/KO/KOR → 'KOR', VN/VNM → 'VN', 그 외 → 'KOR'(기본=본사)."""
    e = str(entity or "").strip().upper()
    if e in ("VN", "VNM"):
        return "VN"
    return "KOR"


def _create_team_for_func(c, func, func_code=None, entity="KOR"):
    """기능부서명(func)+법인(entity)에 해당하는 WORKS 팀을 생성하고 id 반환. '메신저 체계 도입'용.
    이름은 메신저 부서명 그대로(예 '설계팀'), 법인은 entity 컬럼에 저장(이름 충돌 허용)·코드는 유일하게 생성."""
    name = (func or "").strip()
    if not name:
        return None
    ent = _norm_entity(entity)
    # 코드: 법인 접두(V) + 부서코드 → KOR/VN 코드 충돌 회피·가독
    base = ("V" if ent == "VN" else "") + ((str(func_code).strip() if func_code else "") or ("M" + name[:4]))
    code = base
    n = 1
    try:
        while c.execute("SELECT 1 FROM teams WHERE code=?", (code,)).fetchone():
            n += 1
            code = f"{base}_{n}"
        mo = c.execute("SELECT COALESCE(MAX(display_order),0)+1 FROM teams").fetchone()[0]
        # entity 컬럼 존재 여부 가드(마이그레이션 전 환경 호환)
        has_ent = any(r[1] == "entity" for r in c.execute("PRAGMA table_info(teams)").fetchall())
        if has_ent:
            cur = c.execute(
                "INSERT INTO teams(code, name, display_order, entity) VALUES(?,?,?,?)",
                (code, name, mo or 100, ent))
        else:
            cur = c.execute(
                "INSERT INTO teams(code, name, display_order) VALUES(?,?,?)",
                (code, name, mo or 100))
        return cur.lastrowid
    except Exception as e:
        print(f"[SSO] 팀 자동생성 실패({ent}/{name}): {e}")
        return None


def _resolve_team_id(c, dept, create_missing=False, entity_hint=None):
    """v5H226z542: 메신저 부서코드(01_KOR/00_총괄 형식) → WORKS teams.id (법인 분리).
    부서를 (법인 KOR/VN, 기능부서명 func)로 분해 → '같은 법인'의 팀에만 매핑.
    ① 정확매칭(이름/이름+'팀'/코드, 같은 법인) → ② 느슨매칭(LIKE, 같은 법인) →
    ③ create_missing 이면 그 법인 새 팀 생성. KOR 은 entity NULL(레거시)도 본사로 인정.
    매칭 실패 & 생성 안 함 → None(기존 team_id 유지)."""
    if not dept:
        return None
    info = parse_messenger_dept(dept)
    func = info.get("func")
    if not func:
        return None
    # v5H226z544: 법인은 ① 부서코드(02_VN/…)에서 읽되, 없으면 ② payload 의 entity 칸(권위) 사용.
    #   메신저가 부서코드에 법인을 안 붙이고 entity 로만 줄 때도 베트남이 본사로 합쳐지지 않게.
    ent = _norm_entity(info.get("entity") or entity_hint)
    # 법인 필터: KOR 은 entity='KOR' 또는 NULL/''(레거시 본사) 허용 / VN 은 entity='VN' 만
    has_ent = any(r[1] == "entity" for r in c.execute("PRAGMA table_info(teams)").fetchall())
    if not has_ent:
        ent_sql, ent_params = "", ()                       # 컬럼 없으면 법인 무시(구 동작)
    elif ent == "KOR":
        ent_sql, ent_params = " AND COALESCE(entity,'KOR')='KOR'", ()
    else:
        ent_sql, ent_params = " AND entity='VN'", ()
    cands = [func, func + "팀", (dept or "").strip()]
    # ① 정확 매칭(같은 법인)
    for d in cands:
        if not d:
            continue
        try:
            r = c.execute(
                f"SELECT id FROM teams WHERE (name=? OR code=?){ent_sql} ORDER BY id LIMIT 1",
                (d, d, *ent_params)).fetchone()
            if r:
                return r["id"]
        except Exception:
            pass
    # ② 느슨 매칭(같은 법인) — 기능부서명 부분일치
    try:
        r = c.execute(
            f"SELECT id FROM teams WHERE name LIKE ?{ent_sql} ORDER BY id LIMIT 1",
            (f"%{func}%", *ent_params)).fetchone()
        if r:
            return r["id"]
    except Exception:
        pass
    # ③ 도입: 같은 법인에 없으면 새 팀 생성
    if create_missing:
        return _create_team_for_func(c, func, info.get("func_code"), ent)
    return None


def _is_system_account(emp_no, name="") -> bool:
    """v5H226z541: 메신저의 봇/시스템 계정 식별 — WORKS 직원 명부에 들이지 않는다.
    예) 'zz_ai_report'(업무보고 봇)·'zz_works_notify'·'_deleted_user'(삭제 자리표시).
    실 사번은 숫자(예 '5') 또는 'VN001' 형식 → zz* / _* 접두는 봇/시스템으로 간주."""
    e = str(emp_no or "").strip().lower()
    if not e:
        return False
    if e.startswith("zz") or e.startswith("_"):
        return True
    return False


def upsert_user_from_payload(c, payload: dict) -> Optional[int]:
    """JWT payload (또는 userinfo) 로 HAIST WORKS users 테이블 upsert.

    매칭: ① employee_no → ② (없으면) 이름 같고 사번 없는 레거시/시드 계정 병합 → ③ INSERT
    team_id 는 dept 로 매핑해 설정(권한 동작).

    Returns:
        users.id (내부 PK) 또는 None (실패/제외)
    """
    if not payload:
        return None
    emp_no = str(payload.get("sub") or payload.get("employee_no") or "").strip()
    if not emp_no:
        return None
    # z541: 메신저 봇/시스템 계정(zz*, _*)은 WORKS 직원으로 만들지 않음 — 동기화 때마다 되살아나던 원인.
    if _is_system_account(emp_no, payload.get("name_kr") or payload.get("name") or ""):
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

    team_id = _resolve_team_id(c, dept, create_missing=True, entity_hint=entity)   # 부서 → team_id (z540 자동생성·z544 법인은 payload entity 우선)

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
SSO_SERVICE_KEY = os.environ.get("KNK_SSO_SERVICE_KEY", "")  # 서버↔서버 공유키(환경변수)


def get_service_key() -> str:
    """공유키 해석: 환경변수(KNK_SSO_SERVICE_KEY) 우선 → 없으면 WORKS DB(app_settings.sso_service_key).
    DB는 영구(재부팅 유지)·관리자 페이지(/admin/sso-key)서 설정 가능 → SSH/.env 없이도 동작."""
    k = (os.environ.get("KNK_SSO_SERVICE_KEY", "") or "").strip()
    if k:
        return k
    try:
        from . import database as _db
        return (_db.get_setting("sso_service_key", "") or "").strip()
    except Exception:
        return ""


def service_key_source() -> str:
    """'env' | 'db' | 'none' — 키 출처(화면 표시용)."""
    if (os.environ.get("KNK_SSO_SERVICE_KEY", "") or "").strip():
        return "env"
    try:
        from . import database as _db
        if (_db.get_setting("sso_service_key", "") or "").strip():
            return "db"
    except Exception:
        pass
    return "none"


def test_directory(key: str = "") -> dict:
    """주어진(또는 저장된) 공유키로 메신저 명부 API 연결만 시험(저장·반영 안 함).
    반환: {ok, status, count, base, error}."""
    k = (key or get_service_key() or "").strip()
    base = MESSENGER_INTERNAL_BASE
    if not k:
        return {"ok": False, "error": "키가 비어 있습니다.", "base": base}
    url = f"{base}/api/sso/directory"
    try:
        r = httpx.get(url, headers={"X-SSO-Service-Key": k}, timeout=15.0)
    except Exception as e:
        return {"ok": False, "error": f"메신저 연결 실패(주소/네트워크): {str(e)[:140]}", "base": base}
    if r.status_code == 403:
        return {"ok": False, "status": 403, "error": "키 거부(403) — 메신저에 설정된 키와 다릅니다.", "base": base}
    if r.status_code == 404:
        return {"ok": False, "status": 404, "error": "명부 API 없음(404) — 메신저 준비 전/미배포.", "base": base}
    if r.status_code == 503:
        return {"ok": False, "status": 503, "error": "메신저 쪽 공유키 미설정(503) — 메신저 컨테이너 .env 에 KNK_SSO_SERVICE_KEY 등록 필요(전산).", "base": base}
    if r.status_code != 200:
        return {"ok": False, "status": r.status_code, "error": f"오류 응답 {r.status_code}", "base": base}
    try:
        cnt = len((r.json() or {}).get("users") or [])
    except Exception:
        cnt = 0
    return {"ok": True, "status": 200, "count": cnt, "base": base}


def sync_directory_from_messenger(c) -> dict:
    """메신저 직원 명부를 가져와 전 직원 upsert.
    반환: {ok, synced, total} 또는 {ok:False, error}"""
    _key = get_service_key()
    if not _key:
        return {"ok": False, "error": "공유키 미설정 — 관리자 페이지(/admin/sso-key) 또는 NAS .env 에 등록"}
    url = f"{MESSENGER_INTERNAL_BASE}/api/sso/directory"
    try:
        r = httpx.get(url, headers={"X-SSO-Service-Key": _key}, timeout=20.0)
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
def notify_via_messenger(employee_nos, title, body, link="", timeout=10.0, card=None) -> dict:
    """대상 직원(사번 목록)에게 메신저로 1:1 업무 통보.
    card(선택, v5H226z595): 구조화 카드 데이터(dict). 메신저가 지원하면 '제작요청 카드'로 렌더,
      미지원이면 body(평문)로 폴백. 하위호환 — body 는 항상 함께 전송.
    반환: {ok, sent, skipped, room_count, skipped_list} 또는 {ok:False, error}."""
    emps = [str(e).strip() for e in (employee_nos or []) if str(e).strip()]
    if not emps:
        return {"ok": False, "error": "수신 사번 없음(메신저 통보 생략)"}
    _key = get_service_key()
    if not _key:
        return {"ok": False, "error": "공유키 미설정 — 관리자 페이지(/admin/sso-key) 또는 NAS .env 에 등록"}
    url = f"{MESSENGER_INTERNAL_BASE}/api/works/notify"
    _payload = {"employee_nos": emps, "title": title, "body": body, "link": link}
    if card:
        _payload["card"] = card   # 메신저가 무시해도 무해(평문 body 폴백)
    try:
        r = httpx.post(
            url,
            headers={"X-SSO-Service-Key": _key},
            json=_payload,
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
    # z541: 메신저 봇/시스템 계정(zz*, _* — 업무보고/삭제자리표시 등) 제외 → 통계·부서표·명부 전부에서 빠짐.
    payloads = [p for p in (payloads or [])
                if not _is_system_account(
                    p.get("sub") or p.get("employee_no"),
                    p.get("name_kr") or p.get("name") or "")]
    updated = inserted = skipped = 0
    sample_new, sample_upd = [], []
    msg_names = set()

    # v5H226z540: 메신저 부서 목록 + WORKS 팀 매핑 상태 (업서트 전 읽기전용으로 '사전 상태' 캡처).
    #             → 동기화 미리보기 화면에 그대로 표시(수동 목록 입력 불필요·메신저 체계 가시화).
    dept_counts = {}
    for payload in payloads:
        d = (payload.get("dept") or payload.get("dept_code") or "").strip()
        if d:
            # z544: 부서별 인원수 + 법인(payload entity 우선 — 부서코드에 법인 없을 때 대비)
            _pe = (payload.get("entity") or "").strip() or None
            if d not in dept_counts:
                dept_counts[d] = {"count": 0, "entity": _pe}
            dept_counts[d]["count"] += 1
            if not dept_counts[d]["entity"] and _pe:
                dept_counts[d]["entity"] = _pe
    dept_map = []
    for d, _agg in sorted(dept_counts.items()):
        cnt = _agg["count"]
        _pe = _agg.get("entity")
        tid = _resolve_team_id(c, d, create_missing=False, entity_hint=_pe)
        tname = None
        if tid:
            try:
                _tr = c.execute("SELECT name FROM teams WHERE id=?", (tid,)).fetchone()
                tname = _tr["name"] if _tr else None
            except Exception:
                tname = None
        info = parse_messenger_dept(d)
        dept_map.append({
            "dept": d, "count": cnt,
            "entity": info.get("entity") or _pe, "func": info.get("func"),
            "team": tname,
            "action": "연결" if tname else "새 팀 생성",
        })

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
            "sample_upd": sample_upd, "dept_map": dept_map}


def sync_employees_from_messenger_api(c) -> dict:
    """v5H226z493 (컨테이너 분리·대표 지시): 메신저 명부를 'GET /api/sso/directory'(HTTP)로 받아 동기화.
    DB 파일 직접읽기(sync_employees_from_messenger_db) 대체 — 분리 후 볼륨 마운트 불필요.
    미리보기/적용은 호출측 commit/rollback. 반환 = _sync_employees_core 동일 형태(+source)."""
    _key = get_service_key()
    if not _key:
        return {"ok": False, "error": "공유키 미설정 — 관리자 페이지(/admin/sso-key) 또는 NAS .env 에 등록"}
    url = f"{MESSENGER_INTERNAL_BASE}/api/sso/directory"
    try:
        r = httpx.get(url, headers={"X-SSO-Service-Key": _key}, timeout=20.0)
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
