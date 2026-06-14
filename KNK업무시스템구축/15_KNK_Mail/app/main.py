# -*- coding: utf-8 -*-
"""KNK Eum MAIL — 독립 FastAPI 앱 엔트리 (골격 / Phase 1).

WORKS와 완전 분리된 별도 프로세스. 자체 DB(mail.db)·자체 세션·메신저 SSO.
Phase 1(골격): 앱 기동 + DB 스키마 + 세션/헬퍼 + 독립 레이아웃 + 헬스/랜딩/기본 메일함.
Phase 2: 메일 모듈·47 라우트·실제 템플릿·AI·첨부 이식.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import os

from . import config
from . import db
from . import sso_client

# ── 앱 / 미들웨어 ─────────────────────────────────────
app = FastAPI(title=config.APP_NAME)
# 세션 쿠키(브라우저 닫으면 만료) — max_age 없음. WORKS/메신저 인증 표준과 동일.
app.add_middleware(
    SessionMiddleware,
    secret_key=config.SESSION_SECRET,
    session_cookie=config.SESSION_COOKIE,
    same_site="lax",
    https_only=(os.environ.get("KNK_MAIL_HTTPS_ONLY", "0") == "1"),
)

config.ensure_dirs()
db.init_db()

tpl = Jinja2Templates(directory=config.TEMPLATES_DIR)
if os.path.isdir(config.STATIC_DIR):
    app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")


# ── 공통 헬퍼 ─────────────────────────────────────────
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


def require(req: Request):
    """로그인 필요 — 미로그인 시 RedirectResponse 반환(호출측에서 return)."""
    u = get_user(req)
    if not u:
        return None, RedirectResponse("/login", status_code=303)
    return u, None


def can_money(u) -> bool:
    """단가/금액 열람 권한 — 임시(role 기반). Phase 2에서 WORKS 규칙과 정합."""
    return bool(u) and (u.get("role") in ("ceo", "admin") or u.get("can_money"))


def ctx(req: Request, name: str, **kw):
    """공통 컨텍스트 주입 후 템플릿 렌더."""
    u = get_user(req)
    base = dict(
        request=req,
        app_name=config.APP_NAME,
        theme_color=config.THEME_COLOR,
        user=u or {},
        is_admin=bool(u and u.get("role") in ("admin", "ceo")),
        can_money=can_money(u),
        mail_app=True,
    )
    base.update(kw)
    return tpl.TemplateResponse(name, base)


# ── 헬스 / 진단 ───────────────────────────────────────
@app.get("/healthz")
def healthz():
    tables = db.table_names()
    need = {"app_settings", "users", "mail_messages", "mail_attachments", "mail_aliases",
            "mail_large_files", "mail_signatures", "mail_fetch_accounts", "mail_fetch_seen", "mail_rules"}
    return JSONResponse({
        "ok": need.issubset(set(tables)),
        "app": config.APP_NAME,
        "db": os.path.basename(config.DB_PATH),
        "tables": len(tables),
        "missing": sorted(need - set(tables)),
    })


@app.get("/api/version")
def version():
    return JSONResponse({"app": "knk-mail", "phase": "skeleton-1"})


# ── 인증 (골격: 메신저 SSO 자리 + 로컬 dev 우회) ───────
@app.get("/login", response_class=HTMLResponse)
def login(req: Request):
    if get_user(req):
        return RedirectResponse("/mail/inbox", status_code=303)
    # Phase 2(task#22)에서 메신저 SSO(sso_client) 연결. 골격은 안내 + dev 우회만.
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
    """메신저 SSO 로그인으로 보냄. redirect_uri = 이 앱 /sso/land."""
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
    # 게이트: 인증된 직원(사번 보유)이면 입장. (메신저가 mail_access claim 추가 시 강화)
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
    u, redir = require(req)
    if redir:
        return redir
    if u.get("role") not in ("admin", "ceo"):
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


# ── 랜딩 / 앱 진입 ────────────────────────────────────
@app.get("/")
def root(req: Request):
    return RedirectResponse("/mail/inbox" if get_user(req) else "/login", status_code=303)


@app.get("/mail/app")
def mail_app(req: Request):
    return RedirectResponse("/mail/inbox" if get_user(req) else "/login", status_code=303)


# ── 기본 메일함 (골격: mail.db 조회 확인용. Phase 2에서 실제 UI 이식) ──
@app.get("/mail/inbox", response_class=HTMLResponse)
def inbox(req: Request):
    u, redir = require(req)
    if redir:
        return redir
    with db.db_session() as c:
        rows = c.execute(
            "SELECT id, subject, from_name, from_email, received_at, is_read, category "
            "FROM mail_messages WHERE COALESCE(is_deleted,0)=0 AND (user_id=? OR ?='ceo') "
            "ORDER BY received_at DESC LIMIT 100",
            (u.get("id"), u.get("role")),
        ).fetchall()
        total = c.execute("SELECT COUNT(*) AS n FROM mail_messages WHERE COALESCE(is_deleted,0)=0").fetchone()["n"]
    return ctx(req, "inbox_min.html", mails=[dict(r) for r in rows], total=total)
