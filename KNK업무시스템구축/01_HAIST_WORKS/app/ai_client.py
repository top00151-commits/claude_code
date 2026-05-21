"""
HAIST AI 클라이언트 — Claude(Anthropic) API 중앙 래퍼
=================================================================
용도 (대표 결정 2026-05-21):
  1) Victor AI 고도화 (Phase 2 — 자연어 이해·라우팅)
  2) 한↔베트남 번역
  3) 문서 요약 / 작성 도움

정책:
  - API 키는 OS 환경변수 ANTHROPIC_API_KEY 에서만 읽음 (보안 — 코드/DB/ git 에 키 저장 0)
  - 키 미설정 또는 anthropic SDK 미설치 시 → 안전 비활성 (ai_available()==False).
    호출부는 항상 ai_available() 로 먼저 확인하고, 비활성이면 기존 동작(키워드/룰)으로 폴백.
  - 프롬프트 캐싱 적용 (반복 system 프롬프트 캐시 → 비용·지연 절감)
  - AI 는 데이터를 수정하지 않음 — 생성·요약·번역·라우팅 보조만.

키 등록 방법 (사용자):
  - KNK_AI키등록.bat 더블클릭 → 키 입력 (파일에 안 남음, setx 로 영구 등록)
  - 또는 PowerShell:  setx ANTHROPIC_API_KEY "sk-ant-..."
  - 등록 후 서버 재시작 필요 (환경변수는 프로세스 시작 시 로딩).
"""
from __future__ import annotations

import os
from typing import Any, Optional

# ── 모델 (필요 시 환경변수로 오버라이드) ────────────────────────────
#   기본: 비용·속도 균형의 Sonnet 계열. 환경변수 KNK_AI_MODEL 로 교체 가능.
DEFAULT_MODEL = os.environ.get("KNK_AI_MODEL", "claude-sonnet-4-5")
DEFAULT_MAX_TOKENS = 1024
TIMEOUT_SEC = 30

_ENV_KEY = "ANTHROPIC_API_KEY"

# 모듈 로드 시 1회 import 시도 (실패해도 앱은 정상 — 비활성 상태로 동작)
try:
    import anthropic  # type: ignore
    _SDK_OK = True
except Exception:
    anthropic = None  # type: ignore
    _SDK_OK = False

_client: Optional[Any] = None
_client_key_fingerprint: Optional[str] = None


def get_api_key() -> str:
    """OS 환경변수에서 API 키를 읽음. 없으면 빈 문자열."""
    return (os.environ.get(_ENV_KEY) or "").strip()


def ai_available() -> bool:
    """AI 기능 사용 가능 여부 (SDK 설치 + 키 등록 둘 다 충족)."""
    return _SDK_OK and bool(get_api_key())


def ai_status() -> dict:
    """관리자/헬스 화면용 상태 요약 (키 원문은 절대 노출 안 함)."""
    key = get_api_key()
    masked = ""
    if key:
        masked = (key[:7] + "…" + key[-4:]) if len(key) > 14 else "설정됨"
    return {
        "sdk_installed": _SDK_OK,
        "key_registered": bool(key),
        "key_masked": masked,
        "model": DEFAULT_MODEL,
        "available": ai_available(),
    }


def _get_client():
    """anthropic.Anthropic 클라이언트 lazy 생성 (키 변경 시 재생성)."""
    global _client, _client_key_fingerprint
    if not _SDK_OK:
        return None
    key = get_api_key()
    if not key:
        return None
    fp = key[-8:]
    if _client is None or _client_key_fingerprint != fp:
        _client = anthropic.Anthropic(api_key=key, timeout=TIMEOUT_SEC)
        _client_key_fingerprint = fp
    return _client


def ai_chat(
    user_text: str,
    system: str = "",
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    model: str = "",
    temperature: float = 0.3,
    cache_system: bool = True,
) -> tuple[bool, str]:
    """
    단발 채팅 호출. 반환 (성공여부, 응답문자열 또는 오류메시지).
    호출부는 ai_available() 로 먼저 확인할 것 (비활성 시 (False, 사유) 반환).

    cache_system=True 이면 system 프롬프트에 캐시 컨트롤을 붙여
    반복 호출 시 입력 토큰 비용·지연을 줄임 (≥1024 토큰 system 에 효과적).
    """
    client = _get_client()
    if client is None:
        return (False, "AI 비활성 (키 미등록 또는 SDK 미설치)")

    try:
        kwargs: dict[str, Any] = {
            "model": model or DEFAULT_MODEL,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": user_text}],
        }
        if system:
            if cache_system:
                kwargs["system"] = [{
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }]
            else:
                kwargs["system"] = system

        resp = client.messages.create(**kwargs)
        parts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
        return (True, "".join(parts).strip())
    except Exception as e:
        return (False, f"AI 호출 오류: {e}")


def ai_translate(text: str, target: str = "vi") -> tuple[bool, str]:
    """
    한↔베트남 번역. target='vi' (베트남어) / 'ko' (한국어).
    반환 (성공여부, 번역문 또는 오류).
    """
    if not text or not text.strip():
        return (True, "")
    lang_name = {"vi": "베트남어(Tiếng Việt)", "ko": "한국어"}.get(target, target)
    system = (
        "당신은 KNK(검사기·자동화 설비 제조) 사내 메신저의 전문 번역기입니다. "
        f"입력 텍스트를 자연스러운 {lang_name}로 번역하세요. "
        "기술 용어·고객사명·모델명·치수는 원문 의미를 유지하고, "
        "번역문만 출력하세요(설명·따옴표 금지)."
    )
    return ai_chat(text, system=system, max_tokens=1500, temperature=0.2)


def ai_summarize(text: str, *, style: str = "bullet") -> tuple[bool, str]:
    """
    긴 글·대화·회의록 요약. style='bullet'(불릿) / 'short'(2~3줄).
    반환 (성공여부, 요약문 또는 오류).
    """
    if not text or not text.strip():
        return (True, "")
    fmt = "핵심을 불릿(•)으로 5개 이내" if style == "bullet" else "2~3줄로 짧게"
    system = (
        "당신은 KNK 업무 비서입니다. 아래 내용을 한국어로 요약하세요. "
        f"{fmt}. 결정사항·담당·기한이 있으면 반드시 포함. 요약문만 출력하세요."
    )
    return ai_chat(text, system=system, max_tokens=800, temperature=0.2)
