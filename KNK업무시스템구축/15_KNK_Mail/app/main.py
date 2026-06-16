# -*- coding: utf-8 -*-
"""KNK Eum MAIL — 독립 FastAPI 앱 엔트리.

WORKS와 완전 분리된 별도 프로세스. 자체 DB(mail.db)·자체 세션·메신저 SSO.
- 인증/세션/SSO 라우트: 본 파일
- 메일 기능 라우트: mail_routes.py (APIRouter) → include_router
- 공통 헬퍼: deps.py (순환 import 회피)
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import os

from . import config
from . import db
from . import sso_client
from . import deps
from .deps import get_user, ctx, require, _safe_next_path

# ── 앱 / 미들웨어 ─────────────────────────────────────
app = FastAPI(title=config.APP_NAME)
app.add_middleware(
    SessionMiddleware,
    secret_key=config.SESSION_SECRET,
    session_cookie=config.SESSION_COOKIE,
    same_site="lax",
    https_only=config.HTTPS_ONLY,
)

config.ensure_dirs()
db.init_db()

if os.path.isdir(config.STATIC_DIR):
    app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

# 메일 기능 라우트 (별도 파일) — 분리로 main 은 인증/세션만 담당
from . import mail_routes
app.include_router(mail_routes.router)

# 자동 수신 — 주기적으로 모든 활성 계정의 새 메일을 자동으로 받아옴(수동 '가져오기' 불필요)
from . import auto_fetch
auto_fetch.start(app)


# ── 헬스 / 진단 ───────────────────────────────────────
@app.get("/healthz")
def healthz():
    tables = db.table_names()
    need = {"app_settings", "users", "mail_messages", "mail_attachments", "mail_aliases",
            "mail_large_files", "mail_signatures", "mail_fetch_accounts", "mail_fetch_seen", "mail_rules"}
    return JSONResponse({
        "ok": need.issubset(set(tables)), "app": config.APP_NAME,
        "db": os.path.basename(config.DB_PATH), "tables": len(tables),
        "missing": sorted(need - set(tables)),
    })


@app.get("/api/version")
def version():
    return JSONResponse({"app": "knk-mail", "phase": "feature-port"})


# ── 인증 (메신저 SSO + 로컬 dev 우회) ─────────────────
@app.get("/login", response_class=HTMLResponse)
def login(req: Request):
    if get_user(req):
        return RedirectResponse("/mail/inbox", status_code=303)
    return ctx(req, "login.html", dev_login=config.DEV_LOGIN)


@app.post("/login/dev")
async def login_dev(req: Request):
    """로컬 개발 전용 로그인 우회 (KNK_MAIL_DEV_LOGIN=1 일 때만). 운영 비활성."""
    if not config.DEV_LOGIN:
        return JSONResponse({"error": "dev login disabled"}, status_code=403)
    form = await req.form()
    name = (form.get("name") or "개발자").strip()
    with db.db_session() as c:
        uid = sso_client.upsert_user_from_payload(
            c, {"sub": "DEV001", "name_kr": name, "email": "dev@knknara.co.kr", "is_admin": True})
        if uid:
            c.execute("UPDATE users SET role='ceo' WHERE id=?", (uid,))
    req.session["user_id"] = uid
    return RedirectResponse("/mail/inbox", status_code=303)


# ── 메신저 SSO (WORKS와 동일 계약: /login→메신저, /sso/land?token=) ──
@app.get("/sso/login")
def sso_login(req: Request):
    from urllib.parse import quote
    nxt = _safe_next_path(req.query_params.get("next") or "/mail/inbox") or "/mail/inbox"
    redirect_uri = config.PUBLIC_BASE + "/sso/land?next=" + quote(nxt, safe="")
    return RedirectResponse(sso_client.build_login_url(redirect_uri), 303)


@app.get("/sso/land")
def sso_land(req: Request):
    """메신저가 발급한 JWT(token) 수신 → 검증 → 미러 upsert → 세션."""
    token = req.query_params.get("token") or ""
    if not token:
        return ctx(req, "login.html", dev_login=config.DEV_LOGIN,
                   error="입장 토큰이 없습니다. KNK Eum(메신저)에서 메일을 다시 열어주세요.")
    payload = sso_client.verify_token(token)
    if not payload:
        return ctx(req, "login.html", dev_login=config.DEV_LOGIN,
                   error="입장 토큰 검증 실패(만료 가능). 메신저에서 다시 열어주세요.")
    if not str(payload.get("sub") or payload.get("employee_no") or "").strip():
        return ctx(req, "login.html", dev_login=config.DEV_LOGIN,
                   error="직원 정보가 없는 토큰입니다. 관리자에게 문의해주세요.")
    with db.db_session() as c:
        uid = sso_client.upsert_user_from_payload(c, payload)
    if not uid:
        return ctx(req, "login.html", dev_login=config.DEV_LOGIN,
                   error="사용자 동기화 실패. 관리자에게 문의해주세요.")
    req.session["user_id"] = uid
    req.session["sso_pwv"] = int(payload.get("pwv") or 1)
    req.session["sso_token"] = token
    sso_client.mark_pwv_checked(uid)
    nxt = _safe_next_path(req.query_params.get("next") or "") or "/mail/inbox"
    return RedirectResponse(nxt, 303)


@app.post("/admin/dir-sync")
def dir_sync(req: Request):
    """직원명부 동기화 — 메신저 GET /api/sso/directory → 미러 upsert (관리자)."""
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"ok": False, "error": "관리자만"}, status_code=403)
    with db.db_session() as c:
        res = sso_client.sync_directory_from_messenger(c)
    return JSONResponse(res)


@app.get("/logout")
def logout(req: Request):
    try:
        uid = req.session.get("user_id")
        if uid:
            sso_client.invalidate_pwv_check(uid)
        req.session.clear()
    except Exception:
        pass
    return RedirectResponse("/login", status_code=303)


# ── 랜딩 ──────────────────────────────────────────────
@app.get("/")
def root(req: Request):
    return RedirectResponse("/mail/inbox" if get_user(req) else "/login", status_code=303)
