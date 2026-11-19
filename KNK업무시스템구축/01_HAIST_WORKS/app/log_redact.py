# -*- coding: utf-8 -*-
"""z1191z84 — 서버 기록에 로그인 토큰 값이 찍히지 않게 가린다 (대표 2026-11-20 「토큰 기록 고쳐」)

왜: 이음 → 웍스 로그인 주소 `/sso/land?token=<JWT>`(그리고 `/mail/app?token=`·`/sso/callback?token=`)가 서버 접속 기록
    (logs/uvicorn.log)에 주소째 남았다. 토큰은 1시간 살아 있어, 그 사이 기록 파일을 본 사람은 그 직원으로 들어올 수 있었다.
어떻게: uvicorn 이 기록을 쓰기 직전(로거 거름망)에 주소 안의 비밀 이름 변수 값만 `***` 로 바꾼다.
    - 주소·화면·로그인 동작은 그대로(기록 글자만 바뀜)
    - 가리는 이름: token · access_token · id_token · refresh_token · jwt · password · pw · secret · otp · sig · signature · api_key · service_key
    - 일반 이름(code=관리번호 · key=안내 예시 · session=녹음 조각 번호)은 일 추적에 필요하고 비밀이 아니라 그대로 둔다
"""
from __future__ import annotations

import logging
import re

_NAMES = r"(?:access_token|id_token|refresh_token|token|jwt|password|passwd|pw|secret|otp|signature|sig|api_key|apikey|service_key)"
_RX = re.compile(r"([?&;]" + _NAMES + r"=)[^&\s\"']*", re.I)


def redact(s):
    """글자 안의 `?token=…`·`&password=…` 값을 *** 로. 글자가 아니면 그대로."""
    if not isinstance(s, str) or "=" not in s:
        return s
    return _RX.sub(r"\1***", s)


class TokenRedactFilter(logging.Filter):
    def filter(self, record):  # 기록은 언제나 남긴다(True) — 글자만 가린다
        try:
            if isinstance(record.args, tuple) and record.args:
                record.args = tuple(redact(a) for a in record.args)
            elif isinstance(record.args, dict):
                record.args = {k: redact(v) for k, v in record.args.items()}
            if isinstance(record.msg, str):
                record.msg = redact(record.msg)
        except Exception:
            pass
        return True


_F = TokenRedactFilter()


def install():
    """uvicorn 접속·오류 기록과 knk 기록에 거름망을 단다(여러 번 불러도 한 번만)."""
    for name in ("uvicorn.access", "uvicorn.error", "uvicorn", "knk"):
        lg = logging.getLogger(name)
        if _F not in lg.filters:
            lg.addFilter(_F)
    return _F
