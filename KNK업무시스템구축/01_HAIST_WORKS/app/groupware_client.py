"""
외부 그룹웨어 API 클라이언트 — HAIST WORKS 통합 알림 백엔드
=================================================================

세션3 리서치 기반:
- 메신저 알림 API: 사내 메신저로 푸시 (KNK 표준 채널)
- 인사관리 API: 근태/조직 조회
- 전자결재 API: 외부에서 기안 트리거 (Phase 2)

정책 (system_scope_policy.md):
- 자체 결재/메일 모듈 X → 외부 그룹웨어 API로 통합
- 토큰은 admin 설정에서 입력 (오피스 관리 > 환경설정 > API 관리)
- 토큰 미입력 시 silent skip (개발/대기 상태에서 알림 폭주 방지)

토큰 발급 안내 (사용자 작업):
1. 외부 그룹웨어 오피스 로그인 (관리자 권한)
2. 오피스 홈 → 오피스 관리 → 환경 설정 → API 관리
3. 필요 API별 토큰 생성:
   - hiworks_messenger_token (메신저 알림)
   - hiworks_hr_token (인사관리)
   - hiworks_approval_token (전자결재)
4. /admin/settings 페이지에 입력
"""
from __future__ import annotations
import json
import urllib.request
import urllib.error
from typing import Any

# 외부 그룹웨어 API 베이스 (세션3 가이드 A.1.3)
# v5H226z110 (2026-05-30): API URL 기본값 하드코딩 제거 — admin 설정 (groupware_api_base) 강제
# 미설정 시 silent skip (운영 시 admin이 API base URL 입력 필요)
GROUPWARE_API_BASE_DEFAULT = ""  # 빈 문자열 = silent skip
TIMEOUT_SEC = 5


def _http_post(url: str, payload: dict, token: str = "") -> tuple[bool, str]:
    """공통 POST 호출 (실패해도 예외 안 던짐)."""
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return (200 <= resp.status < 300), body
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, f"ERR: {type(e).__name__}: {e}"


def _http_get(url: str, token: str = "") -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, method="GET")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
            return True, resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return False, f"ERR: {type(e).__name__}: {e}"


# =====================================================
# 메신저 알림 API (KNK 표준 채널)
# =====================================================
def send_messenger(text: str, recipients: list[str] | str = None,
                   token: str = "", domain: str = "") -> bool:
    """사내 메신저로 푸시 메시지 발송 (외부 그룹웨어 API).

    Args:
        text: 메시지 본문
        recipients: 수신자 ID 리스트 (이메일/사번/그룹 ID — 그룹웨어 정책 따름).
                    문자열이면 단일 수신자.
        token: 메신저 알림 API 오피스 토큰 (admin 설정에서)
        domain: 회사 그룹웨어 도메인 (예: knk.co.kr)

    Returns:
        True if 발송 성공 또는 silent skip(토큰 없음).
        False if 명시적 실패.

    NOTE: 실제 엔드포인트 URL은 그룹웨어 API 문서 확인 후 확정 필요.
          토큰 미입력 시 stdout 로그만 출력하고 True 반환 (개발 친화).
    """
    if not token:
        # 토큰 없으면 silent skip (운영 시작 전까지 로그만)
        recip_label = recipients if isinstance(recipients, str) else (recipients or [])
        print(f"[HIWORKS-MSG SKIP] (토큰 없음) → {recip_label}: {text[:80]}")
        return True

    if isinstance(recipients, str):
        recipients = [recipients]

    payload = {
        "domain": domain,
        "recipients": recipients or [],
        "message": text,
    }
    # 엔드포인트는 외부 그룹웨어 API 문서 확정 후 교체 (가이드 A.3.3)
    api_base = _get_api_base()
    if not api_base:
        print(f"[GROUPWARE-MSG SKIP] (API base 미설정) → {recipients}: {text[:80]}")
        return True
    url = f"{api_base}/messenger/send"
    ok, body = _http_post(url, payload, token=token)
    if not ok:
        print(f"[HIWORKS-MSG FAIL] {body}")
    return ok


# =====================================================
# 전자결재 API — 외부에서 기안 트리거 (Phase 2)
# =====================================================
def create_approval_draft(doc_type: str, title: str, body: str,
                          drafter: str, approval_line: list[str],
                          token: str = "", domain: str = "") -> tuple[bool, str | None]:
    """외부 그룹웨어 전자결재에 기안 자동 생성.

    Returns:
        (success, approval_url) — 성공 시 결재 문서 URL 반환.
    """
    if not token:
        print(f"[HIWORKS-APV SKIP] (토큰 없음) {doc_type} '{title}' by {drafter}")
        return True, None

    payload = {
        "domain": domain,
        "doc_type": doc_type,
        "title": title,
        "body": body,
        "drafter": drafter,
        "approval_line": approval_line,
    }
    api_base = _get_api_base()
    if not api_base:
        print(f"[GROUPWARE-APV SKIP] (API base 미설정) {doc_type} '{title}'")
        return True, None
    url = f"{api_base}/approval/draft"
    ok, body_resp = _http_post(url, payload, token=token)
    approval_url = None
    if ok:
        try:
            data = json.loads(body_resp)
            approval_url = data.get("approval_url") or data.get("url")
        except Exception:
            pass
    else:
        print(f"[HIWORKS-APV FAIL] {body_resp}")
    return ok, approval_url


# =====================================================
# 인사관리 API — 근태·조직 조회 (Phase 2)
# =====================================================
def get_attendance_today(token: str = "", domain: str = "") -> list[dict]:
    """오늘 근태 조회 (휴가/출장/재택 등). 토큰 없으면 빈 리스트."""
    if not token:
        return []
    api_base = _get_api_base()
    if not api_base:
        return []
    url = f"{api_base}/hr/attendance/today?domain={domain}"
    ok, body = _http_get(url, token=token)
    if not ok:
        return []
    try:
        data = json.loads(body)
        return data.get("items", []) if isinstance(data, dict) else []
    except Exception:
        return []


# =====================================================
# 통합 알림 라우터 — settings에서 토큰 읽어 자동 발송
# =====================================================
def _get_api_base() -> str:
    """admin 설정의 그룹웨어 API base URL (구 키 fallback 포함)."""
    try:
        from .database import get_setting
        v = (get_setting("groupware_api_base", "") or
             get_setting("hiworks_api_base", "") or
             GROUPWARE_API_BASE_DEFAULT)
        return v.strip()
    except Exception:
        return GROUPWARE_API_BASE_DEFAULT


def notify(text: str, recipients=None) -> bool:
    """settings에서 토큰을 읽어 사내 메신저로 발송 (외부 그룹웨어 API).
    v5H226z110 (2026-05-30): groupware_* 키 우선, hiworks_* fallback (마이그레이션 호환)
    내부에서 import (순환 의존 방지)."""
    try:
        from .database import get_setting
        token = (get_setting("groupware_messenger_token", "") or
                 get_setting("hiworks_messenger_token", ""))
        domain = (get_setting("groupware_domain", "") or
                  get_setting("hiworks_domain", ""))
        return send_messenger(text, recipients=recipients, token=token, domain=domain)
    except Exception as e:
        print(f"[GROUPWARE notify ERR] {e}")
        return False
