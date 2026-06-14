# -*- coding: utf-8 -*-
"""sso_client.py — 메신저 SSO 클라이언트 (KNK Eum MAIL 독립 앱)

WORKS sso_client(2026-05-31)를 메일 앱용으로 이식.
- audience = 'knk-mail' (메신저가 메일을 새 SP로 등록 필요)
- 메신저(IdP)가 발급한 JWT(RS256) 검증 → 직원명부 미러(users) upsert → 세션
- 직원명부 동기화: GET /api/sso/directory (서비스키)

설계(WORKS와 동일 계약):
  - 진입: 메일 /login → build_login_url(redirect_uri=…/sso/land?next=) → 메신저
  - 콜백: 메신저가 redirect_uri?token=<JWT> 로 복귀 → verify_token → upsert → 세션
"""
from __future__ import annotations
import os
import time
from typing import Optional

import httpx
import jwt as pyjwt

# ── 설정 (환경변수 override) ──────────────────────────
MESSENGER_BASE = os.environ.get(
    "KNK_MESSENGER_SSO_BASE", "https://haist.knknara.co.kr/msg").rstrip("/")
MESSENGER_INTERNAL_BASE = os.environ.get(
    "KNK_MESSENGER_SSO_INTERNAL_BASE", MESSENGER_BASE).rstrip("/")
# 메일 전용 audience (WORKS='haist-works'와 구분)
SSO_AUDIENCE = os.environ.get("KNK_MAIL_SSO_AUDIENCE", "knk-mail")
SSO_ISSUER = os.environ.get("KNK_SSO_ISSUER", "https://haist.knknara.co.kr/msg/")

_PUBKEY_CACHE: dict = {"pem": None, "fetched_at": 0}
_PUBKEY_TTL_SEC = 3600
_PWV_CHECK_CACHE: dict = {}
PWV_CHECK_INTERVAL_SEC = 300
_HTTP_TIMEOUT_SEC = 5.0


# ── public key ────────────────────────────────────────
def get_public_key(force_refresh: bool = False) -> Optional[str]:
    now = time.time()
    if (not force_refresh) and _PUBKEY_CACHE["pem"] and (now - _PUBKEY_CACHE["fetched_at"] < _PUBKEY_TTL_SEC):
        return _PUBKEY_CACHE["pem"]
    try:
        r = httpx.get(f"{MESSENGER_INTERNAL_BASE}/api/sso/public-key",
                      timeout=_HTTP_TIMEOUT_SEC, follow_redirects=True)
        if r.status_code == 200 and r.text.strip().startswith("-----BEGIN"):
            _PUBKEY_CACHE["pem"] = r.text.strip()
            _PUBKEY_CACHE["fetched_at"] = now
            return _PUBKEY_CACHE["pem"]
        print(f"[SSO] public key fetch failed: {r.status_code}")
    except Exception as e:
        print(f"[SSO] public key error: {e}")
    return _PUBKEY_CACHE["pem"]


def invalidate_public_key_cache():
    _PUBKEY_CACHE["pem"] = None
    _PUBKEY_CACHE["fetched_at"] = 0


# ── JWT 검증 ──────────────────────────────────────────
def verify_token(token: str) -> Optional[dict]:
    if not token or not isinstance(token, str):
        return None
    pem = get_public_key()
    if not pem:
        print("[SSO] verify_token: public key 미수신 — 메신저 SP 등록 전?")
        return None
    try:
        return pyjwt.decode(token, pem, algorithms=["RS256"],
                            audience=SSO_AUDIENCE, issuer=SSO_ISSUER)
    except pyjwt.ExpiredSignatureError:
        print("[SSO] verify_token: 토큰 만료")
    except pyjwt.InvalidAudienceError:
        print(f"[SSO] verify_token: audience 불일치 (expected {SSO_AUDIENCE})")
    except pyjwt.InvalidIssuerError:
        print(f"[SSO] verify_token: issuer 불일치 (expected {SSO_ISSUER})")
    except pyjwt.InvalidTokenError as e:
        print(f"[SSO] verify_token: invalid - {e}")
    except Exception as e:
        print(f"[SSO] verify_token: 예외 ({e}) — public key 재조회 후 1회 재시도")
        invalidate_public_key_cache()
        pem2 = get_public_key(force_refresh=True)
        if pem2 and pem2 != pem:
            try:
                return pyjwt.decode(token, pem2, algorithms=["RS256"],
                                    audience=SSO_AUDIENCE, issuer=SSO_ISSUER)
            except Exception as e2:
                print(f"[SSO] verify_token: 재시도도 실패 ({e2})")
    return None


def fetch_userinfo(token: str) -> Optional[dict]:
    if not token:
        return None
    try:
        r = httpx.get(f"{MESSENGER_INTERNAL_BASE}/api/sso/userinfo",
                      headers={"Authorization": f"Bearer {token}"}, timeout=_HTTP_TIMEOUT_SEC)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (401, 403):
            return {"_invalid": True, "status": r.status_code}
        print(f"[SSO] userinfo unexpected status: {r.status_code}")
    except Exception as e:
        print(f"[SSO] userinfo error: {e}")
    return None


# ── pwv 주기 동기화 ───────────────────────────────────
def should_check_pwv(user_id: int) -> bool:
    return (time.time() - _PWV_CHECK_CACHE.get(user_id, 0)) >= PWV_CHECK_INTERVAL_SEC


def mark_pwv_checked(user_id: int):
    _PWV_CHECK_CACHE[user_id] = time.time()


def invalidate_pwv_check(user_id: int):
    _PWV_CHECK_CACHE.pop(user_id, None)


# ── 로그인 URL ────────────────────────────────────────
def build_login_url(redirect_uri: str, force: bool = False) -> str:
    from urllib.parse import urlencode
    params = {"redirect_uri": redirect_uri}
    if force:
        params["force"] = "1"
    return f"{MESSENGER_BASE}/sso/login?{urlencode(params)}"


# ── 직원명부 미러 upsert (메신저가 마스터) ────────────
def _resolve_team_id(c, dept):
    if not dept:
        return None
    try:
        r = c.execute("SELECT id FROM teams WHERE name=? OR code=? OR name LIKE ? ORDER BY id LIMIT 1",
                      (dept, dept, f"%{dept}%")).fetchone()
        return r["id"] if r else None
    except Exception:
        return None


def upsert_user_from_payload(c, payload: dict) -> Optional[int]:
    """JWT payload(또는 userinfo/directory)로 users 미러 upsert.
    매칭: ① employee_no → ② 이름 같고 사번 없는 레거시 병합 → ③ INSERT. Returns users.id 또는 None."""
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
    team_id = _resolve_team_id(c, dept)

    try:
        row = c.execute("SELECT id, role FROM users WHERE employee_no = ?", (emp_no,)).fetchone()
    except Exception:
        print("[SSO] users.employee_no 컬럼 없음 — 스키마 확인")
        return None

    if not row:
        try:
            legacy = c.execute(
                "SELECT id, role FROM users WHERE name = ? AND "
                "(employee_no IS NULL OR TRIM(employee_no)='') ORDER BY id LIMIT 1",
                (name_kr,)).fetchone()
        except Exception:
            legacy = None
        if legacy:
            try:
                c.execute("UPDATE users SET employee_no=?, login_id=? WHERE id=?",
                          (emp_no, emp_no, legacy["id"]))
            except Exception as _e:
                print(f"[SSO] 병합 실패: {_e}")
            row = legacy

    if row:
        c.execute(
            """UPDATE users SET
                 name = COALESCE(?, name), email = COALESCE(?, email), phone = COALESCE(?, phone),
                 name_en = COALESCE(?, name_en), name_vi = COALESCE(?, name_vi),
                 dept_code = COALESCE(?, dept_code), team_id = COALESCE(?, team_id),
                 rank = COALESCE(?, rank), entity = COALESCE(?, entity), is_active = 1
               WHERE id = ?""",
            (name_kr, email, phone, name_en, name_vi, dept, team_id, pos, entity, row["id"]))
        return row["id"]
    else:
        sentinel_pw = "sso_only_no_local_password"
        try:
            cur = c.execute(
                """INSERT INTO users (name, login_id, password, email, phone, employee_no, entity,
                     name_en, name_vi, dept_code, team_id, rank, role, is_active, password_version, lang)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?)""",
                (name_kr, emp_no, sentinel_pw, email, phone, emp_no, entity, name_en, name_vi,
                 dept, team_id, pos, "admin" if is_admin else "member",
                 "vi" if entity == "VN" else "ko"))
            return cur.lastrowid
        except Exception as e:
            print(f"[SSO] upsert INSERT failed: {e}")
            return None


# ── 직원명부 동기화 (메신저 GET /api/sso/directory) ────
SSO_SERVICE_KEY = os.environ.get("KNK_SSO_SERVICE_KEY", "")


def sync_directory_from_messenger(c) -> dict:
    """메신저 직원명부를 가져와 전 직원 upsert. 반환 {ok, synced, total} 또는 {ok:False, error}."""
    if not SSO_SERVICE_KEY:
        return {"ok": False, "error": "공유키(KNK_SSO_SERVICE_KEY) 미설정 — NAS .env 등록 필요"}
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
                "sub": u.get("employee_no"), "name_kr": u.get("name_kr"),
                "name_en": u.get("name_en"), "name_vi": u.get("name_vi"),
                "dept": u.get("dept"), "position": u.get("position"),
                "entity": u.get("entity"), "email": u.get("email"),
                "phone": u.get("phone"), "is_admin": u.get("is_admin"),
            }
            if upsert_user_from_payload(c, payload):
                synced += 1
        except Exception as _e:
            print(f"[SSO] 명부 동기화 항목 실패: {_e}")
    return {"ok": True, "synced": synced, "total": len(users)}
