# -*- coding: utf-8 -*-
"""KNK Eum MAIL — 공유 헬퍼(deps).

main.py·mail_routes.py 공통. 순환 import 회피용(이 모듈은 main을 import 하지 않음).
WORKS의 get_user/ctx/require/ai_enabled_for/role_home 에 해당.
"""
from __future__ import annotations
from fastapi import Request
from fastapi.templating import Jinja2Templates

from . import config
from . import db
from . import ai_client

tpl = Jinja2Templates(directory=config.TEMPLATES_DIR)


def vname(u, name_vi=None, entity=None):
    """표시 이름 — 메일 템플릿(mail_app_head) 전역. WORKS vname 의 간이판."""
    if not u:
        return ""
    if isinstance(u, dict):
        return (u.get("name") or u.get("name_kr") or u.get("name_en") or u.get("name_vi") or "")
    return str(u)


# 메일 템플릿이 쓰는 Jinja 전역 등록 (WORKS 와 동일 이름)
tpl.env.globals["vname"] = vname


def _load_user(uid):
    """미러 users 행 → dict (없으면 None)."""
    if not uid:
        return None
    try:
        with db.db_session() as c:
            r = c.execute("SELECT * FROM users WHERE id=? AND COALESCE(is_active,1)=1", (uid,)).fetchone()
            return dict(r) if r else None
    except Exception:
        return None


def get_user(req: Request):
    """세션 user_id → 미러 users 로드 (WORKS와 동일 계약: 세션엔 id만)."""
    try:
        return _load_user(req.session.get("user_id"))
    except Exception:
        return None


def require(req: Request, roles=None):
    """로그인(+선택 역할) 필요. 충족 시 user dict, 아니면 None(호출측 redirect 처리)."""
    u = get_user(req)
    if not u:
        return None
    if roles and u.get("role") not in roles:
        return None
    return u


def role_home(u) -> str:
    return "/mail/inbox"


def can_money(u) -> bool:
    """단가/금액 열람 권한 — role 기반(WORKS can_money 정합은 후속)."""
    return bool(u) and (u.get("role") in ("ceo", "admin") or u.get("can_money"))


def ai_enabled_for(u) -> bool:
    """AI 기능 사용 가능 여부 — 키 활성(ai_client) 기준."""
    try:
        return bool(ai_client.ai_available())
    except Exception:
        return False


def _safe_next_path(nxt: str) -> str:
    """SSO 착지 경로 — 내부 경로만 허용(오픈 리다이렉트 차단)."""
    nxt = (nxt or "").strip()
    if not nxt or not nxt.startswith("/"):
        return ""
    if nxt.startswith("//") or nxt.startswith("/\\"):
        return ""
    if any(ch in nxt for ch in ("\\", "\n", "\r", "\t", " ")):
        return ""
    return nxt


def ctx(req: Request, name: str, **kw):
    """공통 컨텍스트 주입 후 렌더. 라우트가 user=·ai_on= 등을 명시하면 그 값 우선."""
    u = kw.pop("user", None)
    if u is None:
        u = get_user(req)
    base = dict(
        request=req, app_name=config.APP_NAME, theme_color=config.THEME_COLOR,
        user=u or {}, is_admin=bool(u and u.get("role") in ("admin", "ceo")),
        can_money=can_money(u), ai_on=ai_enabled_for(u), mail_app=True,
    )
    base.update(kw)
    return tpl.TemplateResponse(name, base)
