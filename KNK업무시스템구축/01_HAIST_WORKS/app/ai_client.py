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
import json
import base64
import hashlib
import re
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


# ── 회의록 추출 (16_KNK_Meeting 모드 A·B) — 구조화 정리 + 회사 맥락 주입 ──────────
# "AI 학습"을 파인튜닝 대신 ① 구조화 정리 지시 ② 회사 맥락(용어·참석자) 주입으로 구현.
_KNK_MEETING_CONTEXT = (
    "[회사 배경] KNK(㈜케이엔케이)는 반도체·디스플레이 검사기와 자동화 설비를 제조한다. "
    "자주 쓰는 용어 — 호기(설비 1대 단위), 사업부(검사기T·자동화M·라이프밸류L·기타E·소모품C), "
    "제작요청(설비 제작 시작), 수주(SO), 납기, 고객사, 출하, 셋업, 양산. "
    "음성→글자 변환 오타로 보이는 이런 회사 용어·사람 이름은 문맥상 자연스럽게 바로잡되, 불확실하면 원문을 유지한다."
)

# z1142 (대표 지시 2026-10-07): 회의 녹음을 글자로 바꿀 때 잘못 들린 우리 회사 말을
#   「정리」 단계에서 바로잡는다. 실측(같은 회의 원문 3,648자 · 5회 반복):
#     표면장 → 표면저항, 카트리스트 → 파트리스트 = 5회 모두 바로잡힘
#     목록에만 있고 회의에 없던 말(코그넥스·YOLO·텔레센트릭) = 0회 (억지로 넣지 않음)
#   🔴 회의 제목에 틀린 말이 적혀 있으면 그 말만은 흔들린다 → 제목을 고쳐야 확실하다.
#   🔴 원문(body)은 절대 바꾸지 않는다. 바로잡기는 정리 글에서만 일어난다.
_MEETING_TERMS_DEFAULT = (
    "MLCC(적층 세라믹 콘덴서 · MSC/MSCC/MHC 로 잘못 들림), FPCB, "
    "파트리스트(부품 목록 · 카트리스트로 잘못 들림), 표면저항(표면장으로 잘못 들림), "
    "정전기, 러버, PVC, 비딩(입찰), OK/NG 판정, 출하 검사기, 치수 검사, 외관 검사, "
    "텔레센트릭 렌즈, 코그넥스, 오픈CV, YOLO"
)


def meeting_terms() -> str:
    """회의록 정리에 함께 주는 「우리 회사 말」. 관리자 → AI 설정에서 고친다.
    빈 값이면 기본 목록 · "-" 한 글자면 이 기능을 끈다(안 보냄)."""
    v = _setting("meeting_terms")
    if v == "-":
        return ""
    return (v or _MEETING_TERMS_DEFAULT).strip()


_MEETING_EXTRACT_SYSTEM = (
    "당신은 KNK 사내 AI 빅터입니다. 회의 원문(음성→글자 변환 포함 가능)을 분석해 "
    "깔끔하게 정리·구성한 회의록과 결정사항·할 일을 만든다.\n"
    "출력 규칙:\n"
    "- summary: 회의록 본문을 아래 형식으로 구조화(한국어, 여러 줄):\n"
    "    핵심: <회의 결론 한 줄>\n"
    "    [안건명] (안건이 여럿이면 안건별로)\n"
    "    - <논의 요점> — 발언에 강조·우려·이견·합의 톤이 분명하면 끝에 (강조)/(우려)/(이견)/(합의) 표시\n"
    "  참석자 이름이 원문에 나오면 그 이름으로 발언·의견을 귀속한다. 안건이 하나뿐이면 안건 머리말 없이 요점만.\n"
    "- decisions: 회의에서 '확정된' 결정만. 각 {who, what, due}. "
    "who=책임자(참석자 이름 우선, 없으면 \"\"), what=무엇을 결정했는지(필수), due=기한 YYYY-MM-DD 또는 표현 그대로(없으면 \"\").\n"
    "- actions: 실행할 일. 각 {assignee, task, due}. assignee=담당자 이름(없으면 \"\"), task=내용(필수), due=기한(없으면 \"\").\n"
    "- title: 이 회의에 어울리는 짧은 제목(공백 포함 20자 이내, 고객사·안건 중심). "
    "반드시 원문에 나온 말로만 짓는다(창작 금지). 지을 수 없으면 \"\".\n"
    "- 절대 추측·창작 금지. 원문에 없는 내용을 지어내지 않는다. 결정·할 일 없으면 빈 배열.\n"
    "출력은 오직 아래 JSON 한 개. 마크다운 코드펜스·설명·인사말 금지.\n"
    '{"title":"","summary":"",'
    '"decisions":[{"who":"","what":"","due":""}],'
    '"actions":[{"assignee":"","task":"","due":""}]}'
)


def _parse_json_loose(text: str) -> Optional[dict]:
    """LLM 응답에서 JSON 객체를 견고하게 파싱. 코드펜스/잡텍스트 제거 후 시도.
    실패하면 None."""
    if not text:
        return None
    s = text.strip()
    # ```json ... ``` 펜스 제거
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s).strip()
    # strict=False: 여러 줄 summary 안의 raw 줄바꿈/탭(제어문자)도 허용해 견고하게 파싱.
    try:
        return json.loads(s, strict=False)
    except Exception:
        pass
    # 본문 중 첫 '{' ~ 마지막 '}' 구간만 추출 재시도
    i, j = s.find("{"), s.rfind("}")
    if i != -1 and j != -1 and j > i:
        try:
            return json.loads(s[i:j + 1], strict=False)
        except Exception:
            return None
    return None


def ai_extract_meeting(body: str, context: str = "") -> tuple[bool, dict]:
    """회의 원문 → 구조화 정리(summary)·결정사항·할 일 추출 (모드 A·B).
    context: 이번 회의 정보(제목·참석자·날짜 등) — 참석자 이름 귀속·맥락 정리에 사용.
    반환 (성공여부, {"summary":str, "decisions":[...], "actions":[...]}).
    호출부는 ai_available() 로 먼저 확인할 것. 실패 시 (False, {"error": 사유}).

    데이터 안전(메모리 feedback_data_connectivity): 추출 결과는 '제안'일 뿐,
    실제 일일카드 등록은 사용자 1-클릭 검토 후에만(자동 등록 금지)."""
    empty = {"decisions": [], "actions": [], "summary": ""}
    if not body or not body.strip():
        return (True, dict(empty))
    system = _MEETING_EXTRACT_SYSTEM + "\n\n" + _KNK_MEETING_CONTEXT
    if context and context.strip():
        system += "\n\n[이번 회의 정보]\n" + context.strip()
    _terms = meeting_terms()           # z1142 — 우리 회사 말(관리자가 고칠 수 있음)
    if _terms:
        system += ("\n\n[우리 회사 말 — 음성 변환이 흔히 틀리는 말]\n" + _terms
                   + "\n\U0001F534 위 말이 원문에 비슷하게 들어 있으면 그 말로 바로잡는다. "
                     "원문에 없는 말은 절대 넣지 않는다. "
                     "회의 제목·참석자에 적힌 말이라도 이 목록과 어긋나면 이 목록 쪽을 따른다"
                     "(제목도 사람이 잘못 적었을 수 있다).")
    ok, resp = ai_chat(
        body.strip(),
        system=system,
        max_tokens=2000,
        temperature=0.1,
    )
    if not ok:
        return (False, {"error": resp, **empty})
    data = _parse_json_loose(resp)
    if not isinstance(data, dict):
        return (False, {"error": "AI 응답을 회의록 형식(JSON)으로 해석하지 못했습니다.", **empty})

    # 형식 정규화 — 키 누락/타입 오류 방어
    def _norm_list(items, keys):
        out = []
        if isinstance(items, list):
            for it in items:
                if not isinstance(it, dict):
                    continue
                row = {k: str(it.get(k, "") or "").strip() for k in keys}
                # 핵심 필드(what/task)가 비면 버림
                core = "what" if "what" in keys else "task"
                if row.get(core):
                    out.append(row)
        return out

    result = {
        "decisions": _norm_list(data.get("decisions"), ("who", "what", "due")),
        "actions": _norm_list(data.get("actions"), ("assignee", "task", "due")),
        "summary": str(data.get("summary", "") or "").strip(),
        # 제목 제안 — '제목 없는 회의'를 AI가 내용 기반으로 채우는 데 사용(호출부에서 기본제목일 때만 반영)
        "title": str(data.get("title", "") or "").strip()[:60],
    }
    return (True, result)


# ── 🎤 음성 메모 정리 (z1144 · 대표 지시 2026-10-08) ─────────────────────────
#   회의가 아니다 — 혼자 말한 생각·전화 통화·현장 메모·말로 하는 보고.
#   🔴 회의용 틀(안건·결정사항·참석자 귀속)을 씌우면 **없는 결정을 지어내거나 빈칸만** 나온다.
#      그래서 요점·할 일만 뽑는 **다른 틀**을 쓴다.
_NOTE_EXTRACT_SYSTEM = (
    "당신은 KNK 사내 AI 빅터입니다. 사람이 혼자 말한 녹음(회의가 아님)을 글자로 바꾼 원문을 읽고 "
    "짧고 쓸모 있게 정리한다.\n"
    "출력 규칙:\n"
    "- summary: 아래 형식(한국어, 여러 줄). 해당 없는 묶음은 통째로 뺀다.\n"
    "    요점\n"
    "    - <한 줄씩 · 말한 순서대로>\n"
    "    할 일\n"
    "    - <무엇을> — <누가/언제까지 · 원문에 나온 것만>\n"
    "    나온 이름·회사·날짜\n"
    "    - <원문에 나온 것만 그대로>\n"
    "  \U0001F534 안건·결정사항·참석자별 발언 귀속은 만들지 않는다(혼자 말한 것이다).\n"
    "- title: 이 메모에 어울리는 짧은 제목(공백 포함 20자 이내). "
    "반드시 원문에 나온 말로만 짓는다(창작 금지). 지을 수 없으면 \"\".\n"
    "- 절대 추측·창작 금지. 원문에 없는 내용을 지어내지 않는다. 말이 짧으면 정리도 짧게.\n"
    "출력은 오직 아래 JSON 한 개. 마크다운 코드펜스·설명·인사말 금지.\n"
    '{"title":"","summary":""}'
)


def ai_extract_note(body: str) -> tuple[bool, dict]:
    """🎤 음성 메모 원문 → {"summary", "title"} (z1144).
    회의용 ai_extract_meeting 과 **틀이 다르다**(안건·결정사항 없음).
    「우리 회사 말」 바로잡기(meeting_terms)는 회의록과 **같은 한 벌**을 쓴다."""
    empty = {"summary": "", "title": ""}
    if not body or not body.strip():
        return (True, dict(empty))
    system = _NOTE_EXTRACT_SYSTEM + "\n\n" + _KNK_MEETING_CONTEXT
    _terms = meeting_terms()
    if _terms:
        system += ("\n\n[우리 회사 말 — 음성 변환이 흔히 틀리는 말]\n" + _terms
                   + "\n\U0001F534 위 말이 원문에 비슷하게 들어 있으면 그 말로 바로잡는다. "
                     "원문에 없는 말은 절대 넣지 않는다.")
    ok, resp = ai_chat(body.strip(), system=system, max_tokens=1500, temperature=0.1)
    if not ok:
        return (False, {"error": resp, **empty})
    data = _parse_json_loose(resp)
    if not isinstance(data, dict):
        return (False, {"error": "AI 응답을 정리 형식(JSON)으로 해석하지 못했습니다.", **empty})
    return (True, {
        "summary": str(data.get("summary", "") or "").strip(),
        "title": str(data.get("title", "") or "").strip()[:60],
    })


# ── 음성→글자 (16_KNK_Meeting 모드 B 음성 회의) ─────────────────────────────
# Whisper STT 는 OpenAI 전용(Claude 미지원). 공급사 설정과 무관하게 OPENAI 키가 있어야 동작.
# 정의서 제약3 DEC-3: OpenAI API 데이터는 학습 미사용(opt-out 기본). 음성 파일은 사내 저장.
def transcribe_available() -> bool:
    """음성→글자(Whisper) 사용 가능 여부 — OpenAI SDK + OpenAI 키."""
    return bool(_OPENAI_OK and _key_for("openai"))


# ── 음성 → 글자 모델 (z1140 · 대표 지시 2026-10-06) ─────────────────────────
#  같은 녹음 5분을 나란히 받아쓴 실측(회의 53):
#    whisper-1 은 **회의 앞 20초를 통째로 빠뜨렸고**, 코그넥스→「코고넥스」·동글→「동굴」·
#    OKNG→「OK 엔지」·2D→「3D」·기술적으로→「교수적으로」 처럼 전문용어를 줄줄이 틀렸다.
#    gpt-transcribe 는 그 낱말을 거의 다 맞히고 더 빠르다(15초→8~10초). 값도 더 싸다.
#    이음(메신저)은 2026-07-31 대표 지시로 이미 바꿔 석 달째 쓰고 있다.
#  🔎 같이 재 봤지만 **넣지 않은 것**: 언어 지정(ko)·힌트 낱말·소리 품질 올리기 —
#    이 표본에서 이득을 증명하지 못했다. 특히 언어 지정은 베트남 직원 회의를 한국어로
#    강제할 위험이 있어 뺐다(호출자가 lang 을 주면 그때만 쓴다).
#  🔧 되돌리기: 환경변수 KNK_WORKS_STT_MODEL=whisper-1 한 줄.
STT_MODEL = (os.environ.get("KNK_WORKS_STT_MODEL") or "gpt-transcribe").strip()
STT_FALLBACK_MODEL = (os.environ.get("KNK_WORKS_STT_FALLBACK") or "whisper-1").strip()


def _stt_is_new_model(model: str) -> bool:
    """신형 전사 모델(gpt-transcribe·gpt-4o-transcribe…)인가.
    신형: 언어는 `extra_body.languages`(복수) · 응답형식은 json 만.
    구형(whisper-1): `language`(단수) · 🔴 prompt 는 '앞서 받아쓴 글' 취급이라 지시문을 주면 결과에 튀어나온다."""
    return (model or "").lower().startswith("gpt")


def ai_transcribe(audio_path: str, lang: str = "") -> tuple[bool, str]:
    """음성 파일 → 텍스트. 기본 `gpt-transcribe`, 실패하면 `whisper-1` 로 한 번 더(z1140).
    audio_path: 디스크 경로(webm/m4a/mp4/mp3/wav 등). lang: 'ko'/'vi'/'en' 또는 ''(자동감지).
    반환 (성공, 텍스트 또는 오류메시지). 호출부는 transcribe_available() 로 먼저 확인 권장.
    OpenAI 전용 — claude만 설정돼 있으면 (False, 사유) 반환."""
    key = _key_for("openai")
    if not _OPENAI_OK:
        return (False, "음성→글자: openai SDK 미설치 (pip install openai)")
    if not key:
        return (False, "음성→글자: OpenAI 키가 필요합니다(현재 미설정/무효). 관리자 → AI 설정에서 등록하세요.")
    if not audio_path or not os.path.exists(audio_path):
        return (False, "음성 파일을 찾을 수 없습니다.")
    models = [STT_MODEL] + ([STT_FALLBACK_MODEL] if (STT_FALLBACK_MODEL and STT_FALLBACK_MODEL != STT_MODEL) else [])
    client = openai.OpenAI(api_key=key, timeout=300)
    last = ""
    for i, model in enumerate(models):
        kwargs: dict[str, Any] = {"model": model}
        if _stt_is_new_model(model):
            kwargs["response_format"] = "json"        # 신형은 text/verbose_json/srt/vtt 미지원
            if lang in ("ko", "vi", "en"):
                kwargs["extra_body"] = {"languages": [lang]}
        else:
            if lang in ("ko", "vi", "en"):
                kwargs["language"] = lang             # 구형은 단수
        try:
            with open(audio_path, "rb") as f:         # ⚠ 스트림은 시도마다 새로 연다(한 번 읽으면 다시 못 읽는다)
                resp = client.audio.transcriptions.create(file=f, **kwargs)
            text = (getattr(resp, "text", "") or "").strip()
            if i > 0:
                print(f"[STT] {models[0]} 실패 → {model} 로 받아씀")
            return (True, text)
        except Exception as e:
            last = f"{model}: {e}"
            print(f"[STT] {model} 실패: {str(e)[:160]}")
    return (False, f"음성→글자 오류(openai): {last}")


def test_provider(provider: str) -> tuple[bool, str]:
    """특정 공급사 키를 강제로 써서 최소 호출(키 유효성) 점검. provider: 'openai'|'claude'.
    get_provider() 선택과 무관하게 그 공급사 키만 직접 검사 → 두 키를 따로 확인할 수 있음.
    반환 (성공, 짧은 응답 또는 오류). 키 없으면 (False, '키 미설정')."""
    provider = "claude" if provider in ("claude", "anthropic") else "openai"
    key = _key_for(provider)
    if not key:
        return (False, "키 미설정")
    if not _sdk_ok(provider):
        return (False, f"{provider} SDK 미설치")
    try:
        if provider == "claude":
            client = anthropic.Anthropic(api_key=key, timeout=TIMEOUT_SEC)
            resp = client.messages.create(
                model=DEFAULT_MODEL_CLAUDE, max_tokens=10, temperature=0,
                messages=[{"role": "user", "content": "Reply only: OK"}])
            parts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
            return (True, ("".join(parts).strip() or "OK")[:60])
        else:
            client = openai.OpenAI(api_key=key, timeout=TIMEOUT_SEC)
            resp = _openai_create(
                client, DEFAULT_MODEL_OPENAI,
                [{"role": "user", "content": "Reply only: OK"}], 10, 0)
            return (True, ((resp.choices[0].message.content or "").strip() or "OK")[:60])
    except Exception as e:
        return (False, str(e)[:200])
