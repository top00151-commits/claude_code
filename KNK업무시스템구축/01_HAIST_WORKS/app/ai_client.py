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
#   🔴 z1168 (대표 지시 2026-10-13): 64분 녹음(원문 27,950자)이 936자로 눌렸다.
#      실측 — 원문 10,327→19,684→27,950자(2.7배)인데 정리는 760→970→936자(1.2배).
#      길이가 **안 따라 늘었다**. 까닭 둘 = ①답 길이 한도 1500 ②「짧고 쓸모 있게」뿐이라
#      길면 길게 하라는 말이 없었다. 둘 다 고친다.
#   🔴 z1168: 「나온 이름·회사·날짜」 묶음은 **뺀다**(대표 「없어도 됨 — 내용을 정리할 때
#      포함된 사항들이라」). 그만큼 요점·할 일에 자리를 내준다.
_NOTE_EXTRACT_SYSTEM = (
    "당신은 KNK 사내 AI 빅터입니다. 사람이 혼자 말한 녹음(회의가 아님)을 글자로 바꾼 원문을 읽고 "
    "쓸모 있게 정리한다.\n"
    "출력 규칙:\n"
    "- summary: 아래 형식(한국어, 여러 줄). 해당 없는 묶음은 통째로 뺀다.\n"
    "    요점\n"
    "    - <한 줄씩 · 말한 순서대로>\n"
    "    할 일\n"
    "    - <무엇을> — <누가/언제까지 · 원문에 나온 것만>\n"
    "  \U0001F534 안건·결정사항·참석자별 발언 귀속은 만들지 않는다(혼자 말한 것이다).\n"
    "  \U0001F534 이름·회사·날짜만 따로 모은 목록은 만들지 않는다 "
    "(요점·할 일 문장 안에 이미 들어 있다).\n"
    "  \U0001F534 원문을 **처음부터 끝까지** 읽고 **끝부분까지 빠짐없이** 정리한다. "
    "뒤로 갈수록 짧아지거나 중간에서 그만두면 안 된다.\n"
    "  \U0001F534 **원문이 길면 정리도 그만큼 길어야 한다** — 긴 녹음을 몇 줄로 누르지 말 것. "
    "원문 1,000자마다 요점을 **한 줄 이상** 남긴다.\n"
    "- title: 이 메모에 어울리는 짧은 제목(공백 포함 20자 이내). "
    "반드시 원문에 나온 말로만 짓는다(창작 금지). 지을 수 없으면 \"\".\n"
    "- 절대 추측·창작 금지. 원문에 없는 내용을 지어내지 않는다. 말이 짧으면 정리도 짧게.\n"
    "출력은 오직 아래 JSON 한 개. 마크다운 코드펜스·설명·인사말 금지.\n"
    '{"title":"","summary":""}'
)

#  🎤 음성 메모 정리에 줄 **답 길이** (z1168) — 원문이 길면 답도 길어야 한다.
#    0.16 = 원문 글자수 → 넉넉한 출력 토큰. 한국어는 글자당 약 1.5토큰이라
#    원문의 1/10 을 정리로 쓴다고 보면 0.15 안팎이면 남는다.
#      10,327자 → 1,652 · 19,684자 → 3,149 · 27,950자 → 4,472 · 50,000자 이상 → 8,000(상한)
_NOTE_TOK_MIN, _NOTE_TOK_MAX, _NOTE_TOK_RATIO = 1500, 8000, 0.16


def _note_budget(n_chars: int) -> int:
    """원문 글자수 → 답 길이 한도. 옛 값(1500)보다 작아지지 않는다."""
    return max(_NOTE_TOK_MIN, min(_NOTE_TOK_MAX, int(n_chars * _NOTE_TOK_RATIO)))


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
    text = body.strip()
    budget = _note_budget(len(text))                      # z1168 — 원문 길이에 맞춘다
    ok, resp = ai_chat(text, system=system, max_tokens=budget, temperature=0.1)
    if not ok:
        return (False, {"error": resp, **empty})
    data = _parse_json_loose(resp)
    #  🔴 z1168: 답이 **중간에서 끊기면** JSON 이 깨진다(닫는 괄호가 없다).
    #     전에는 그대로 「해석하지 못했습니다」로 끝났다 → 한 번만 더, 한도를 끝까지 올려 다시 부른다.
    if not isinstance(data, dict) and budget < _NOTE_TOK_MAX:
        ok2, resp2 = ai_chat(text, system=system, max_tokens=_NOTE_TOK_MAX, temperature=0.1)
        if ok2:
            data = _parse_json_loose(resp2)
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


# ── 받아쓸 때 미리 주는 힌트 (z1165 · 대표 지시 2026-10-11 「인식율·정확도를 올렸으면」) ──
#  🔎 왜: 운영 음성 회의록 24건(22.6만 자)을 훑어 보니, 회사가 「이 말은 잘못 들린다」고
#     **이미 적어 둔** 낱말이 그대로 틀려 있었다 —
#       MSCC·MSC·MHC ← MLCC · 표면장 ← 표면저항 · 동굴 ← 동글 ·
#       「OK 엔지」 ← OK/NG · 교수적으로 ← 기술적으로
#     원인은 그 목록(meeting_terms)을 **정리할 때만 주고 받아쓸 때는 안 줬기** 때문이다.
#     그래서 뒤에서도 못 건졌다 — 정리 글에 MSC 가 2번 그대로 남아 있었다.
#  ✅ 이음(메신저)이 2026-07-31 대표 지시로 **석 달째** 쓰는 방식과 같다(공개 시험 오인식률 40.4%→19.3%).
#  ⚠ 낱말은 많이 넣을수록 나쁘다 — 안 한 말을 지어낸다(환각). 자주 쓰고 잘못 들리기 쉬운 것만.
#  ⛔ 직원 명부는 넣지 않는다 (기존 규정: 명부 통째주입 금지). 사람 이름은 교정사전이 담당(z1166).
#  🔧 되돌리기: 환경변수 KNK_WORKS_STT_HINT=0 한 줄이면 z1165 이전과 글자 하나까지 같아진다.
STT_HINT_ON = (os.environ.get("KNK_WORKS_STT_HINT") or "1").strip() != "0"

# 현장에서 실제로 오가는 말 — 모델에 "이런 낱말이 나온다"고 미리 알려준다.
_STT_KEYWORDS = {
    "ko": ["케이엔케이", "하이스트", "사출", "금형", "지그", "포고핀", "프로브핀", "비전검사",
           "검사장비", "출하 검사기", "자동화", "공차", "치수", "품번", "발주", "견적", "납기",
           "검수", "협력사", "고객사", "베트남법인", "설비", "가동", "불량", "양산", "샘플",
           "도면", "센서", "컨베이어", "에어호스", "유닛", "조립체", "단가", "세금계산서",
           "동글", "정전기", "표면저항"],
    "vi": ["ép phun nhựa", "khuôn mẫu", "bản vẽ", "ngày giao hàng", "máy kiểm tra",
           "kích thước", "nghiệm thu", "báo giá", "nhà cung cấp", "dây khí", "cụm"],
    "en": ["injection molding", "mold", "jig", "pogo pin", "vision inspection",
           "tolerance", "part number", "purchase order", "quotation", "delivery date"],
}

# 사람별 말투(억양) — 사투리는 사람마다 다르다. 표준어 쓰는 분에게 주면 오히려 방해가 된다.
#  ⏭ z1166 에서 「내 프로필」 칸(users.stt_dialect)과 이어 붙인다. 지금은 받을 준비만 돼 있다.
#  ⚠ 키는 언어를 넘어 유일해야 한다 — 저장된 값 하나만 보고 어느 언어 것인지 알 수 있어야 한다.
_STT_DIALECTS = {
    "ko": {"gyeongsang": "경상도(부산·대구·경남·경북)", "jeolla": "전라도(광주·전남·전북)",
           "chungcheong": "충청도(대전·충남·충북)", "gangwon": "강원도", "jeju": "제주도"},
    "vi": {"vi_north": "북부(하노이·홍하 삼각주)", "vi_central": "중부(후에·다낭)",
           "vi_south": "남부(호찌민)"},
}
_STT_DIALECT_LANG = {k: lg for lg, m in _STT_DIALECTS.items() for k in m}

# 🇻🇳 베트남 지역별 발음 힌트 — 지역보다 「소리는 같은데 글자가 다른」 것이 진짜 문제다.
#   우리 직원 대부분은 하노이 주변(박닌·박장·꾸에보·푸토·타이응우옌) = 북부.
_STT_VI_DIALECT_HINT = {
    "vi_north": ("The speaker is from northern Vietnam (Hanoi / Red River Delta — Bac Ninh, Bac Giang, "
                 "Que Vo, Phu Tho, Thai Nguyen). In this accent tr/ch, s/x and r/d/gi sound identical and "
                 "initial n and l are often swapped. Do NOT transcribe these sounds letter by letter — "
                 "decide from context which standard Vietnamese spelling is meant, with correct diacritics. "),
    "vi_central": ("The speaker is from central Vietnam (Hue / Da Nang); tones and some final consonants "
                   "differ from the Hanoi standard. Write standard spelling with correct diacritics. "),
    "vi_south": ("The speaker is from southern Vietnam (Ho Chi Minh City); v/d/gi and some final consonants "
                 "differ from the Hanoi standard. Write standard spelling with correct diacritics. "),
}


def _stt_company_words() -> list:
    """관리자 → AI 설정의 「우리 회사 말」에서 **바른 말만** 뽑는다.
    그 목록은 'MLCC(적층 세라믹 콘덴서 · MSC/MSCC/MHC 로 잘못 들림), FPCB, …' 꼴이라
    괄호 앞이 바른 말이다. 괄호 안은 「잘못 들리는 보기」라 **넣으면 거꾸로 틀리게 만든다**."""
    out = []
    for part in (meeting_terms() or "").split(","):
        w = part.split("(")[0].strip()
        if 1 < len(w) <= 24 and w not in out:
            out.append(w)
    return out


def _stt_keywords(lang: str) -> list:
    """그 언어로 줄 낱말 목록. 언어를 모를 때(자동 감지)는 한국어+베트남어를 함께 준다."""
    lang = (lang or "").lower()
    if lang.startswith("ko"):
        words = list(_STT_KEYWORDS["ko"])
    elif lang.startswith("vi"):
        words = list(_STT_KEYWORDS["vi"])
    elif lang.startswith("en"):
        words = list(_STT_KEYWORDS["en"])
    else:
        words = list(_STT_KEYWORDS["ko"]) + list(_STT_KEYWORDS["vi"])
    if not lang or lang.startswith("ko"):   # 회사 말 목록은 한국어로 적혀 있다
        for w in _stt_company_words():
            if w not in words:
                words.append(w)
    return words


def _stt_prompt(lang: str = "", dialect: str = "", new_model: bool = True) -> str:
    """모델에 미리 주는 「무슨 회의인지」. 애매한 발음을 회사 업무 쪽으로 붙게 한다.

    🔴 구형(whisper-1)에는 **지시문을 주면 안 된다** — whisper 의 prompt 는 '앞서 받아쓴 글'
       취급이라 지시문이 결과에 그대로 튀어나온다. 그래서 낱말 나열만 준다.
    🔴 언어를 모를 때(자동 감지) **한국어 설명을 주면 베트남 회의를 한국어로 끌어당긴다** →
       그때는 어느 말도 편들지 않는 설명으로 준다."""
    lang = (lang or "").lower()
    if not new_model:
        return ", ".join(_stt_keywords(lang))[:800]      # 구형 = 낱말만 (지시문 금지)
    dialect = (dialect or "").strip()
    if dialect and _STT_DIALECT_LANG.get(dialect) != (lang if lang else None):
        dialect = ""                                     # 말투는 '그 언어의 것'일 때만
    if lang.startswith("ko"):
        p = ("㈜케이엔케이(KNK)·하이스트(HAIST) 임직원의 사내 업무 회의입니다. "
             "검사장비·자동화·사출·금형 제조와 납기·발주·견적·고객사 이야기가 자주 나옵니다. ")
        label = _STT_DIALECTS["ko"].get(dialect)
        if label:
            p += (f"말하는 사람은 {label} 억양의 한국어를 씁니다. 억양 때문에 표준 발음과 다를 수 있으니 "
                  "소리만으로 단정하지 말고 앞뒤 문맥으로 판단해 표준어 표기로 적어 주세요. ")
        p += ("말한 그대로 받아쓰세요. 요약·의역·문장 다듬기·설명 추가를 하지 마세요. "
              "알아듣지 못한 부분은 지어내지 말고 빼세요.")
        return p
    p = ("Internal work meeting at KNK / HAIST — inspection equipment, automation, injection molding "
         "and mold manufacturing, plus delivery dates, purchase orders, quotations and customers. ")
    if not lang:
        # 자동 감지 — 어느 말도 편들지 않는다(한국어 회의도 베트남어 회의도 있다)
        p += ("The speakers may be using Korean, Vietnamese, or both. ")
    if dialect:
        p += _STT_VI_DIALECT_HINT.get(dialect, "")
    p += ("Transcribe verbatim in the language actually spoken. Do not summarize, paraphrase, translate "
          "or add anything. If a part is unclear, omit it rather than guessing.")
    return p


def _stt_param_error(e) -> bool:
    """모델이 **힌트 항목 자체를 모를 때**인가 — 그러면 같은 모델로 힌트 없이 한 번 더 간다.
    🔴 이게 없으면 힌트가 거부될 때 곧장 whisper-1 로 떨어져 **정확도가 거꾸로 나빠진다**
       (whisper-1 은 앞 20초를 빠뜨리고 전문용어를 줄줄이 틀린 바로 그 모델이다)."""
    m = str(e or "").lower()
    return any(k in m for k in (
        "unknown parameter", "unknown_parameter", "unrecognized", "invalid parameter",
        "extra_body", "keywords", "not supported", "unsupported", "additional properties",
        "unexpected keyword"))


def ai_transcribe(audio_path: str, lang: str = "", dialect: str = "",
                  keywords=None) -> tuple[bool, str]:
    """음성 파일 → 텍스트. 기본 `gpt-transcribe`, 실패하면 `whisper-1` 로 한 번 더(z1140).
    audio_path: 디스크 경로(webm/m4a/mp4/mp3/wav 등). lang: 'ko'/'vi'/'en' 또는 ''(자동감지).
    dialect: 말하는 사람의 억양(_STT_DIALECTS 키 · ⏭z1166). keywords: 이 사람 전용으로 더 얹을 낱말.
    반환 (성공, 텍스트 또는 오류메시지). 호출부는 transcribe_available() 로 먼저 확인 권장.
    OpenAI 전용 — claude만 설정돼 있으면 (False, 사유) 반환.

    z1165: 회사 말·회의 설명을 **미리 준다**(STT_HINT_ON). 힌트 항목을 모르는 모델이면
      **같은 모델로 힌트 없이 한 번 더** 간 뒤에야 예비 모델로 내려간다(정확도 역행 방지)."""
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
    for mi, model in enumerate(models):
        for use_hint in ((True, False) if STT_HINT_ON else (False,)):
            kwargs: dict[str, Any] = {"model": model}
            new = _stt_is_new_model(model)
            if use_hint:
                p = _stt_prompt(lang, dialect, new_model=new)
                if p:
                    kwargs["prompt"] = p[:2000]
            if new:
                kwargs["response_format"] = "json"    # 신형은 text/verbose_json/srt/vtt 미지원
                extra: dict[str, Any] = {}
                if lang in ("ko", "vi", "en"):
                    extra["languages"] = [lang]       # 신형은 복수
                if use_hint:
                    words = _stt_keywords(lang)
                    for w in (keywords or []):
                        if w and w not in words:
                            words.append(w)
                    if words:
                        extra["keywords"] = words[:80]
                if extra:
                    kwargs["extra_body"] = extra
            else:
                if lang in ("ko", "vi", "en"):
                    kwargs["language"] = lang         # 구형은 단수
            try:
                with open(audio_path, "rb") as f:     # ⚠ 스트림은 시도마다 새로 연다(한 번 읽으면 다시 못 읽는다)
                    resp = client.audio.transcriptions.create(file=f, **kwargs)
                text = (getattr(resp, "text", "") or "").strip()
                if mi > 0:
                    print(f"[STT] {models[0]} 실패 → {model} 로 받아씀")
                if not use_hint and STT_HINT_ON:
                    print(f"[STT] {model}: 힌트를 안 받아 힌트 없이 받아씀")
                return (True, text)
            except Exception as e:
                last = f"{model}: {e}"
                print(f"[STT] {model} 실패(힌트={1 if use_hint else 0}): {str(e)[:160]}")
                if use_hint and _stt_param_error(e):
                    continue                          # 같은 모델로 힌트 없이 다시
                break                                 # 다른 이유 → 다음 모델로
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
