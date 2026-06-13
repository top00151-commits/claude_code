"""
HAIST AI 클라이언트 — 공급사 무관(Claude / OpenAI) 중앙 래퍼
=================================================================
용도 (대표 결정 2026-05-21):
  1) Victor AI 고도화 (Phase 2 — 자연어 이해·라우팅)
  2) 한↔베트남 번역
  3) 문서 요약 / 작성 도움

공급사 선택 (환경변수):
  KNK_AI_PROVIDER = claude | openai   (미설정 시 자동 감지)
    - claude  : ANTHROPIC_API_KEY 사용 (anthropic SDK)
    - openai  : OPENAI_API_KEY    사용 (openai SDK)
  자동 감지 순서: KNK_AI_PROVIDER → ANTHROPIC_API_KEY 있으면 claude
                  → OPENAI_API_KEY 있으면 openai → 없으면 비활성

모델 (환경변수 KNK_AI_MODEL 로 오버라이드 가능):
  - claude 기본: claude-sonnet-4-5
  - openai 기본: gpt-4o-mini  (저렴 — 번역·요약). 고품질은 gpt-4o.

정책:
  - 키는 OS 환경변수에서만 읽음 (코드/DB/git 저장 0)
  - 키·SDK 없거나 결제 전이면 → 안전 비활성 (ai_available()==False).
    호출부는 항상 ai_available() 확인 후, 비활성이면 기존(룰/키워드)로 폴백.
  - Claude 는 system 프롬프트 캐싱 적용(반복 호출 비용↓). OpenAI 는 자동 캐싱.
  - AI 는 데이터를 수정하지 않음 — 생성·요약·번역·라우팅 보조만.

키 등록: KNK_AI키등록.bat (Claude/OpenAI 선택 → 알맞은 환경변수에 setx)
"""
from __future__ import annotations

import os
import base64
import hashlib
from typing import Any, Optional

# ── 공급사·모델 기본값 ────────────────────────────────────────────
_CLAUDE_KEY_ENV = "ANTHROPIC_API_KEY"
_OPENAI_KEY_ENV = "OPENAI_API_KEY"
DEFAULT_MODEL_CLAUDE = "claude-sonnet-4-5"
DEFAULT_MODEL_OPENAI = "gpt-4o-mini"
DEFAULT_MAX_TOKENS = 1024
TIMEOUT_SEC = 30

# SDK lazy import (없어도 앱 정상 — 해당 공급사만 비활성)
try:
    import anthropic  # type: ignore
    _ANTHROPIC_OK = True
except Exception:
    anthropic = None  # type: ignore
    _ANTHROPIC_OK = False

try:
    import openai  # type: ignore
    _OPENAI_OK = True
except Exception:
    openai = None  # type: ignore
    _OPENAI_OK = False

_client: Optional[Any] = None
_client_signature: Optional[str] = None  # (provider, key 끝8자) — 변경 시 재생성


def _setting(key: str) -> str:
    """app_settings 에서 값 읽기 (없거나 오류 시 ''). v5H226z138 — 앱 내 AI 설정."""
    try:
        from .database import db_session
        with db_session() as c:
            r = c.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
            return ((r[0] if r else "") or "").strip()
    except Exception:
        return ""


# ── v5H226z381 (대표 지시): 화면(관리자 AI 설정)에서 키 입력·저장 ──────────
#   기존 정책(키=OS 환경변수 only)에서 → 화면 DB 저장 허용으로 확장.
#   보안 완화책: ① 저장 시 난독화(KNK_SECRET_KEY 기반 XOR, 평문 회피) ② 화면 마스킹만
#   ③ admin/ceo 전용 라우트. (강한 암호화는 아님 — DB/백업 접근 관리는 별도 필요)
def _obfus_salt() -> bytes:
    """KNK_SECRET_KEY 기반 난독화 솔트(32B). 미설정 시 고정 솔트(약함 — 평문 회피용)."""
    secret = (os.environ.get("KNK_SECRET_KEY") or "knk-haist-works-ai-keystore-v1").encode("utf-8")
    return hashlib.sha256(secret).digest()


def _enc(raw: str) -> str:
    """평문 키 → 'enc:'+base64(XOR salt). DB 평문 저장 회피용 난독화(강한 암호화 아님)."""
    if not raw:
        return ""
    salt = _obfus_salt()
    b = raw.encode("utf-8")
    x = bytes(ch ^ salt[i % len(salt)] for i, ch in enumerate(b))
    return "enc:" + base64.b64encode(x).decode("ascii")


def _dec(stored: str) -> str:
    """저장값 → 평문. 'enc:' 접두 없으면 평문(직접 입력/구버전)으로 간주."""
    if not stored:
        return ""
    if not stored.startswith("enc:"):
        return stored.strip()
    try:
        x = base64.b64decode(stored[4:])
        salt = _obfus_salt()
        b = bytes(ch ^ salt[i % len(salt)] for i, ch in enumerate(x))
        return b.decode("utf-8")
    except Exception:
        return ""


def _mask(k: str) -> str:
    if not k:
        return ""
    return (k[:7] + "…" + k[-4:]) if len(k) > 14 else "설정됨"


def save_api_key(provider: str, raw: str) -> None:
    """공급사 키를 난독화해 app_settings 저장 (provider: 'openai'|'claude')."""
    skey = "openai_api_key" if provider == "openai" else "anthropic_api_key"
    try:
        from .database import db_session
        with db_session() as c:
            c.execute(
                "INSERT INTO app_settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (skey, _enc(raw)))
    except Exception:
        pass


def clear_api_key(provider: str) -> None:
    skey = "openai_api_key" if provider == "openai" else "anthropic_api_key"
    try:
        from .database import db_session
        with db_session() as c:
            c.execute("DELETE FROM app_settings WHERE key=?", (skey,))
    except Exception:
        pass


def key_info() -> dict:
    """공급사별 키 상태(마스킹·출처) — 원문 비노출. 화면 표시용.
    src: 'db'(화면 저장) / 'env'(환경변수) / ''(미설정)."""
    out = {}
    for prov, skey, env in (("openai", "openai_api_key", _OPENAI_KEY_ENV),
                            ("claude", "anthropic_api_key", _CLAUDE_KEY_ENV)):
        dbval = _setting(skey)
        dbk = _dec(dbval) if dbval else ""
        envk = (os.environ.get(env) or "").strip()
        if dbk:
            out[prov] = {"set": True, "src": "db", "masked": _mask(dbk)}
        elif envk:
            out[prov] = {"set": True, "src": "env", "masked": _mask(envk)}
        else:
            out[prov] = {"set": False, "src": "", "masked": ""}
    return out


def get_provider() -> str:
    """현재 사용할 공급사 결정. claude | openai | '' (비활성).
    v5H226z381 (대표 지시): 화면(DB) 설정 우선 → 환경변수 → 키 자동감지."""
    p = _setting("ai_provider").lower()
    if not p:
        p = (os.environ.get("KNK_AI_PROVIDER") or "").strip().lower()
    if p in ("claude", "anthropic"):
        return "claude"
    if p in ("openai", "gpt"):
        return "openai"
    # 자동 감지: Claude 키 우선, 없으면 OpenAI (화면 DB 키 + 환경변수 모두 고려)
    if _key_for("claude"):
        return "claude"
    if _key_for("openai"):
        return "openai"
    return ""


def _key_for(provider: str) -> str:
    # v5H226z381 (대표 지시): 화면(DB)에 등록된 키 우선 → 없으면 OS 환경변수 폴백.
    skey = "openai_api_key" if provider == "openai" else "anthropic_api_key"
    dbval = _setting(skey)
    if dbval:
        k = _dec(dbval)
        if k:
            return k
    env = _CLAUDE_KEY_ENV if provider == "claude" else _OPENAI_KEY_ENV
    return (os.environ.get(env) or "").strip()


def _sdk_ok(provider: str) -> bool:
    return _ANTHROPIC_OK if provider == "claude" else _OPENAI_OK


def default_model(provider: str = "") -> str:
    """모델 결정. v5H226z381: 화면(DB) ai_model 우선 → 환경변수 KNK_AI_MODEL → 공급사 기본."""
    override = _setting("ai_model")
    if not override:
        override = (os.environ.get("KNK_AI_MODEL") or "").strip()
    if override:
        return override
    provider = provider or get_provider()
    return DEFAULT_MODEL_OPENAI if provider == "openai" else DEFAULT_MODEL_CLAUDE


def get_api_key() -> str:
    """현재 공급사의 API 키 (없으면 빈 문자열)."""
    p = get_provider()
    return _key_for(p) if p else ""


def ai_available() -> bool:
    """AI 사용 가능 여부 (공급사 결정 + 해당 SDK 설치 + 키 등록)."""
    p = get_provider()
    return bool(p) and _sdk_ok(p) and bool(_key_for(p))


def ai_status() -> dict:
    """관리자/헬스 화면용 상태 (키 원문 절대 노출 안 함)."""
    p = get_provider()
    key = _key_for(p) if p else ""
    masked = ""
    if key:
        masked = (key[:7] + "…" + key[-4:]) if len(key) > 14 else "설정됨"
    return {
        "provider": p or "(없음)",
        "sdk_installed": _sdk_ok(p) if p else False,
        "key_registered": bool(key),
        "key_masked": masked,
        "model": default_model(p) if p else "",
        "available": ai_available(),
        "providers_sdk": {"claude": _ANTHROPIC_OK, "openai": _OPENAI_OK},
    }


def _get_client(provider: str):
    """공급사별 클라이언트 lazy 생성 (공급사·키 변경 시 재생성)."""
    global _client, _client_signature
    if not _sdk_ok(provider):
        return None
    key = _key_for(provider)
    if not key:
        return None
    sig = f"{provider}:{key[-8:]}"
    if _client is None or _client_signature != sig:
        if provider == "claude":
            _client = anthropic.Anthropic(api_key=key, timeout=TIMEOUT_SEC)
        else:
            _client = openai.OpenAI(api_key=key, timeout=TIMEOUT_SEC)
        _client_signature = sig
    return _client


def _openai_create(client, mdl, messages, max_tokens, temperature):
    """OpenAI 호출 — 구·신형 모델 파라미터 차이 자동 대응. (v5H226z139)
    신형(GPT-5 / o 계열)은 max_tokens 대신 'max_completion_tokens', temperature 미지원 가능.
    파라미터 오류일 때만 변형 재시도하고, 그 외 오류(키·모델없음)는 즉시 전달."""
    variants = [
        {"max_tokens": max_tokens, "temperature": temperature},          # 구형 표준
        {"max_completion_tokens": max_tokens, "temperature": temperature},  # 신형
        {"max_completion_tokens": max_tokens},                            # 신형 + temperature 미지원
        {"max_tokens": max_tokens},                                       # 구형 + temperature 미지원
    ]
    last = None
    for v in variants:
        try:
            return client.chat.completions.create(model=mdl, messages=messages, **v)
        except Exception as e:
            last = e
            m = str(e).lower()
            is_param = ("unsupported_parameter" in m or "not supported" in m
                        or "max_completion_tokens" in m or "max_tokens" in m
                        or "temperature" in m)
            if not is_param:
                raise   # 파라미터 문제 아님 → 그대로 전달
    raise last


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
    단발 채팅 호출 (공급사 자동). 반환 (성공여부, 응답 또는 오류메시지).
    호출부는 ai_available() 로 먼저 확인할 것.
    """
    provider = get_provider()
    if not provider:
        return (False, "AI 비활성 (공급사·키 미설정)")
    client = _get_client(provider)
    if client is None:
        return (False, f"AI 비활성 ({provider} 키 미등록 또는 SDK 미설치)")

    mdl = model or default_model(provider)
    try:
        if provider == "claude":
            kwargs: dict[str, Any] = {
                "model": mdl,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": user_text}],
            }
            if system:
                if cache_system:
                    kwargs["system"] = [{
                        "type": "text", "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }]
                else:
                    kwargs["system"] = system
            resp = client.messages.create(**kwargs)
            parts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
            return (True, "".join(parts).strip())
        else:  # openai
            msgs = []
            if system:
                msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": user_text})
            resp = _openai_create(client, mdl, msgs, max_tokens, temperature)
            return (True, (resp.choices[0].message.content or "").strip())
    except Exception as e:
        return (False, f"AI 호출 오류({provider}): {e}")


def ai_vision(
    image_b64: str,
    mime: str,
    user_text: str,
    system: str = "",
    *,
    max_tokens: int = 700,
    model: str = "",
    temperature: float = 0.0,
) -> tuple[bool, str]:
    """
    v5H227c — 멀티모달(비전) 단발 호출. 이미지(base64)+지시문 → 응답 텍스트.
    명함 사진 직접 판독 등에 사용. 반환 (성공여부, 응답 또는 오류메시지).
    호출부는 ai_available() 로 먼저 확인할 것. 기본 모델(gpt-4o-mini / claude-sonnet)은
    모두 비전 지원. 키/SDK 없으면 (False, 사유) 반환 → 호출부가 폴백.
    """
    provider = get_provider()
    if not provider:
        return (False, "AI 비활성 (공급사·키 미설정)")
    client = _get_client(provider)
    if client is None:
        return (False, f"AI 비활성 ({provider} 키 미등록 또는 SDK 미설치)")
    mdl = model or default_model(provider)
    try:
        if provider == "claude":
            content = [
                {"type": "image", "source": {
                    "type": "base64", "media_type": mime, "data": image_b64}},
                {"type": "text", "text": user_text},
            ]
            kwargs: dict[str, Any] = {
                "model": mdl, "max_tokens": max_tokens, "temperature": temperature,
                "messages": [{"role": "user", "content": content}],
            }
            if system:
                kwargs["system"] = system
            resp = client.messages.create(**kwargs)
            parts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
            return (True, "".join(parts).strip())
        else:  # openai
            content = [
                {"type": "text", "text": user_text},
                {"type": "image_url",
                 "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
            ]
            msgs = []
            if system:
                msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": content})
            resp = _openai_create(client, mdl, msgs, max_tokens, temperature)
            return (True, (resp.choices[0].message.content or "").strip())
    except Exception as e:
        return (False, f"AI 비전 호출 오류({provider}): {e}")


def ai_translate(text: str, target: str = "vi") -> tuple[bool, str]:
    """한↔베트남 번역. target='vi'(베트남어)/'ko'(한국어)."""
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
    """긴 글·대화·회의록 요약. style='bullet'/'short'."""
    if not text or not text.strip():
        return (True, "")
    fmt = "핵심을 불릿(•)으로 5개 이내" if style == "bullet" else "2~3줄로 짧게"
    system = (
        "당신은 KNK 업무 비서입니다. 아래 내용을 한국어로 요약하세요. "
        f"{fmt}. 결정사항·담당·기한이 있으면 반드시 포함. 요약문만 출력하세요."
    )
    return ai_chat(text, system=system, max_tokens=800, temperature=0.2)
