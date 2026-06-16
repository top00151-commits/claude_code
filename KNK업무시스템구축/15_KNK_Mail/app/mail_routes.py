# -*- coding: utf-8 -*-
"""KNK Eum MAIL — 메일 기능 라우트 (APIRouter).

WORKS main.py 의 메일 라우트(47개)를 독립 앱으로 이식.
- 로직: mail_store(_mailbox)/mail_send(_mail)/mail_fetch(_mailfetch) (연결 인자 구조 그대로)
- 헬퍼: deps.ctx/get_user/require/ai_enabled_for/role_home
- WORKS 결합(보류): to-task(tasks)·to-contact/연락처자동완성/보낸이연결(shared_contacts)
  → 독립 앱엔 해당 테이블 없음. WORKS API 연동 전까지 안전 안내(데이터 미생성).
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse, Response, FileResponse
from starlette.concurrency import run_in_threadpool
import os
import hmac

from . import config, db, ai_client
from . import mail_send as _mail
from . import mail_store as _mailbox
from . import mail_fetch as _mailfetch
from .deps import ctx, get_user, require, role_home, ai_enabled_for

router = APIRouter()
db_session = db.db_session
get_setting = db.get_setting

_MAIL_CATEGORIES = ("견적", "발주", "세금계산서", "일반")
_MAIL_POC_ADDR = "test@knk-mailtest.com"
PUBLIC_BASE = config.PUBLIC_BASE
_LARGE_MAX = 500 * 1024 * 1024


def _mail_inbound_token() -> str:
    t = (get_setting("mail_inbound_token", "") or "").strip()
    if t:
        return t
    return (os.environ.get("KNK_MAIL_INBOUND_TOKEN") or "").strip()


def _mail_from_address() -> str:
    return (get_setting("mail_from_address", "") or "").strip() or _MAIL_POC_ADDR


# ═══════════════════════════════════════════════════════════════
#  받기 구멍 (Cloudflare Email Routing → POST /api/mail/inbound)
# ═══════════════════════════════════════════════════════════════
@router.post("/api/mail/inbound")
async def mail_inbound(req: Request):
    token_cfg = _mail_inbound_token()
    if not token_cfg:
        return JSONResponse({"ok": False, "message": "수신 기능 비활성 — 관리자 '메일 받기 설정'에서 토큰을 먼저 생성하세요."}, 403)
    token = (req.headers.get("X-KNK-Mail-Token") or req.query_params.get("token") or "").strip()
    # 상수시간 비교(타이밍 공격 방지)
    if not hmac.compare_digest(token, token_cfg):
        return JSONResponse({"ok": False, "message": "인증 실패"}, 401)
    try:
        d = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "message": "JSON 본문이 필요합니다."}, 400)
    f = {"to_email": (d.get("to") or "").strip(),
         "from_email": d.get("from") or "", "from_name": d.get("from_name") or "",
         "subject": d.get("subject") or "", "text": d.get("text") or "",
         "html": d.get("html") or "", "cc": d.get("cc") or "", "size": d.get("size") or 0}
    raw = d.get("raw") or ""
    # 크기 상한(앱 레이어) — nginx 600M 외에 본문 폭주 방어. 메일 업계 표준 25MB+여유.
    if raw and len(raw) > 30 * 1024 * 1024:
        return JSONResponse({"ok": False, "message": "메일이 너무 큽니다(30MB 초과)."}, 413)
    _atts = None
    if raw:
        parsed = _mailbox.parse_raw_email(raw)
        if parsed:
            for k in ("from_email", "from_name", "subject", "text", "html", "cc"):
                if parsed.get(k):
                    f[k] = parsed[k]
            if not f["to_email"] and parsed.get("to_email"):
                f["to_email"] = parsed["to_email"]
            f["size"] = len(raw)
            _atts = parsed.get("attachments")
    if not f["to_email"]:
        return JSONResponse({"ok": False, "message": "수신 주소(to)가 없습니다."}, 400)
    with db_session() as c:
        mid, owner = _mailbox.store_inbound(
            c, to_email=f["to_email"], from_email=f["from_email"], from_name=f["from_name"],
            subject=f["subject"], text=f["text"], html=f["html"], cc=f["cc"], size=f["size"],
            run_ai=True, attachments=_atts)
    if not mid:
        return JSONResponse({"ok": False, "message": "수신자 매핑 실패(받는 사람을 찾지 못함)"}, 422)
    return JSONResponse({"ok": True, "id": mid, "owner": owner})


# ═══════════════════════════════════════════════════════════════
#  PWA — 설치형 앱 (KNK Eum MAIL). scope /mail/
# ═══════════════════════════════════════════════════════════════
_MAIL_PWA_ICON_CACHE = {}
_MAIL_PWA_ICON_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512'>"
    "<rect width='512' height='512' rx='104' fill='#A5282C'/>"
    "<rect x='112' y='168' width='288' height='184' rx='20' fill='#fff'/>"
    "<path d='M120 180 L256 292 L392 180' fill='none' stroke='#A5282C' "
    "stroke-width='24' stroke-linejoin='round' stroke-linecap='round'/></svg>"
)


def _mail_pwa_icon_png(size: int) -> bytes:
    if size in _MAIL_PWA_ICON_CACHE:
        return _MAIL_PWA_ICON_CACHE[size]
    from PIL import Image, ImageDraw
    import io as _io
    S = size
    img = Image.new("RGBA", (S, S), (165, 40, 44, 255))
    d = ImageDraw.Draw(img)
    m = int(S * 0.24); w = S - 2 * m; h = int(w * 0.66)
    top = (S - h) // 2; left = m; right = m + w
    d.rounded_rectangle([left, top, right, top + h], radius=max(3, int(S * 0.04)), fill=(255, 255, 255, 255))
    lw = max(2, int(S * 0.025))
    d.line([(left, top), ((left + right) // 2, top + int(h * 0.55)), (right, top)],
           fill=(165, 40, 44, 255), width=lw, joint="curve")
    buf = _io.BytesIO(); img.save(buf, "PNG")
    data = buf.getvalue(); _MAIL_PWA_ICON_CACHE[size] = data
    return data


@router.get("/mail/manifest.webmanifest")
async def mail_manifest():
    return JSONResponse({
        "id": "/mail/app", "name": "KNK Eum MAIL", "short_name": "Eum MAIL",
        "description": "KNK Eum MAIL — 사내 메일", "start_url": "/mail/app", "scope": "/",
        "display": "standalone", "orientation": "portrait", "background_color": "#ffffff",
        "theme_color": "#A5282C", "lang": "ko",
        "icons": [
            {"src": "/mail/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/mail/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
            {"src": "/mail/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
        ],
        "categories": ["business", "productivity"],
        "launch_handler": {"client_mode": ["focus-existing", "auto"]},
        "handle_links": "preferred",
    }, media_type="application/manifest+json")


@router.get("/mail/sw.js")
async def mail_sw():
    js = ("// KNK Eum MAIL PWA 서비스워커 — 설치 가능 + 네트워크 기본(pass-through)\n"
          "const KNKMAIL_V='knkmail-v1';\n"
          "self.addEventListener('install',function(e){self.skipWaiting();});\n"
          "self.addEventListener('activate',function(e){e.waitUntil(self.clients.claim());});\n"
          "self.addEventListener('fetch',function(e){});\n")
    return Response(js, media_type="application/javascript",
                    headers={"Service-Worker-Allowed": "/mail/", "Cache-Control": "no-cache"})


@router.get("/mail/icon-{size:int}.png")
async def mail_icon_png(size: int):
    if size not in (180, 192, 512):
        size = 192
    return Response(_mail_pwa_icon_png(size), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=604800"})


@router.get("/mail/icon.svg")
async def mail_icon_svg():
    return Response(_MAIL_PWA_ICON_SVG, media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=604800"})


@router.get("/mail/app")
async def mail_app_launch(req: Request):
    """설치형 앱 시작 — 로그인돼 있으면 받은편지함, 아니면 로그인(→메신저 SSO)."""
    return RedirectResponse("/mail/inbox" if get_user(req) else "/login", 303)


# ═══════════════════════════════════════════════════════════════
#  받은편지함 / 보기 / 읽기 창
# ═══════════════════════════════════════════════════════════════
@router.get("/mail/inbox")
async def mail_inbox_page(req: Request, cat: str = "", q: str = "", star: int = 0, unread: int = 0,
                          df: str = "", dt: str = "", att: int = 0, thread: int = 1, cust: str = ""):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        mails = _mailbox.list_inbox(c, u["id"], category=cat, q=q, starred=bool(star),
                                    unread=bool(unread), date_from=df, date_to=dt, has_att=bool(att), cust=cust)
        unread_n = _mailbox.count_unread(c, u["id"])
        cat_counts = _mailbox.category_counts(c, u["id"])
        drafts_n = _mailbox.count_drafts(c, u["id"])
        folders = _mailbox.customer_folder_counts(c, u["id"])
    thread_on = bool(thread)
    threads = _mailbox.group_threads(mails) if thread_on else None
    return ctx(req, "mail_inbox.html", user=u, mails=mails, unread=unread_n,
               cat_counts=cat_counts, cur_cat=cat, categories=_MAIL_CATEGORIES, cur_df=df, cur_dt=dt,
               cur_att=bool(att), ai_on=ai_enabled_for(u), q=q, cur_star=bool(star), cur_unread=bool(unread),
               drafts_n=drafts_n, thread_on=thread_on, threads=threads,
               folders=folders, cur_cust=(cust or "").strip())


@router.get("/mail/drafts", response_class=HTMLResponse)
async def mail_drafts_page(req: Request):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        mails = _mailbox.list_drafts(c, u["id"])
        unread = _mailbox.count_unread(c, u["id"])
        drafts_n = _mailbox.count_drafts(c, u["id"])
    return ctx(req, "mail_inbox.html", user=u, mails=mails, unread=unread, cat_counts={}, cur_cat="",
               categories=_MAIL_CATEGORIES, ai_on=ai_enabled_for(u), box="draft", drafts_n=drafts_n)


@router.get("/mail/sent", response_class=HTMLResponse)
async def mail_sent_page(req: Request, q: str = ""):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        mails = _mailbox.list_sent(c, u["id"], q=q)
        sent_n = _mailbox.count_sent(c, u["id"])
        unread = _mailbox.count_unread(c, u["id"])
        drafts_n = _mailbox.count_drafts(c, u["id"])
    return ctx(req, "mail_inbox.html", user=u, mails=mails, unread=unread, cat_counts={}, cur_cat="",
               categories=_MAIL_CATEGORIES, ai_on=ai_enabled_for(u), box="sent", sent_n=sent_n, q=q, drafts_n=drafts_n)


@router.get("/mail/trash", response_class=HTMLResponse)
async def mail_trash_page(req: Request):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        mails = _mailbox.list_trash(c, u["id"])
        unread = _mailbox.count_unread(c, u["id"])
        drafts_n = _mailbox.count_drafts(c, u["id"])
    return ctx(req, "mail_inbox.html", user=u, mails=mails, unread=unread, cat_counts={}, cur_cat="",
               categories=_MAIL_CATEGORIES, ai_on=ai_enabled_for(u), box="trash", drafts_n=drafts_n)


# ─── 자동분류 규칙 ───────────────────────────────────────────
@router.get("/mail/rules", response_class=HTMLResponse)
async def mail_rules_page(req: Request):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        rules = _mailbox.list_rules(c, u["id"])
    return ctx(req, "mail_rules.html", user=u, rules=rules, categories=_MAIL_CATEGORIES)


@router.post("/mail/rules")
async def mail_rules_add(req: Request):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    form = await req.form()
    with db_session() as c:
        _mailbox.add_rule(c, u["id"], (form.get("match_type") or "sender"),
                          (form.get("pattern") or ""), (form.get("category") or "일반"))
    return RedirectResponse("/mail/rules", 303)


@router.post("/mail/rules/{rid:int}/delete")
async def mail_rules_delete(req: Request, rid: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False}, 401)
    with db_session() as c:
        _mailbox.delete_rule(c, rid, u["id"])
    return JSONResponse({"ok": True})


@router.post("/mail/rules/apply")
async def mail_rules_apply(req: Request):
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False, "message": "로그인 필요"}, 401)
    with db_session() as c:
        n = _mailbox.apply_rules_existing(c, u["id"])
    return JSONResponse({"ok": True, "changed": n, "message": f"기존 메일 {n}건을 규칙대로 다시 분류했습니다."})


# ─── 서명 ────────────────────────────────────────────────────
@router.get("/mail/signature", response_class=HTMLResponse)
async def mail_signature_page(req: Request):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        sig = _mailbox.get_signature(c, u["id"])
    return ctx(req, "mail_signature.html", user=u, sig=sig)


@router.post("/mail/signature")
async def mail_signature_save(req: Request):
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False}, 401)
    form = await req.form()
    with db_session() as c:
        _mailbox.save_signature(c, u["id"], (form.get("body") or ""))
    return JSONResponse({"ok": True})


# ─── 메일 쓰기 / 보내기 ──────────────────────────────────────
@router.get("/mail/compose", response_class=HTMLResponse)
async def mail_compose_page(req: Request, reply: int = 0, replyall: int = 0, forward: int = 0, draft: int = 0):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    prefill = {"to": "", "cc": "", "bcc": "", "subject": "", "body": "", "draft_id": ""}
    with db_session() as c:
        ready = _mail.system_send_ready(c)
        sig = _mailbox.get_signature(c, u["id"])
        sigblock = ""
        my_addr = (_mail_from_address() or "").lower()
        if draft:
            d = _mailbox.get_draft(c, draft, u["id"])
            if d:
                prefill.update(to=d.get("to_email") or "", cc=d.get("cc") or "", bcc=d.get("bcc") or "",
                               subject=(d.get("subject") or "").replace("(제목 없음)", ""),
                               body=d.get("body_text") or "", draft_id=str(draft))
        elif reply or replyall:
            m = _mailbox.get_mail(c, reply or replyall, u["id"])
            if m:
                prefill["to"] = m.get("from_email") or ""
                subj = (m.get("subject") or "").strip()
                prefill["subject"] = subj if subj.lower().startswith("re:") else f"Re: {subj}"
                if replyall:
                    seen, cc_list = set(), []
                    for fld in (m.get("to_email"), m.get("cc")):
                        for a in (fld or "").replace(";", ",").split(","):
                            a = a.strip(); al = a.lower()
                            if a and al not in seen and al not in (my_addr, (m.get("from_email") or "").lower()):
                                seen.add(al); cc_list.append(a)
                    prefill["cc"] = ", ".join(cc_list)
                prefill["body"] = sigblock + "\n\n\n──────── 원본 메일 ────────\n" + (m.get("body_text") or "")
        elif forward:
            m = _mailbox.get_mail(c, forward, u["id"])
            if m:
                subj = (m.get("subject") or "").strip(); lo = subj.lower()
                prefill["subject"] = subj if (lo.startswith("fwd:") or lo.startswith("fw:")) else f"Fwd: {subj}"
                hdr = ("\n\n──────── 전달된 메일 ────────\n"
                       f"보낸사람: {m.get('from_name') or ''} <{m.get('from_email') or ''}>\n"
                       f"제목: {m.get('subject') or ''}\n받은시각: {m.get('received_at') or ''}\n\n")
                prefill["body"] = sigblock + hdr + (m.get("body_text") or "")
        else:
            prefill["body"] = sigblock
    return ctx(req, "mail_compose.html", user=u, prefill=prefill, ready=ready,
               from_addr=_mail_from_address(), ai_on=ai_enabled_for(u), sig_html=("" if draft else sig))


@router.post("/mail/send")
async def mail_send_route(req: Request):
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False, "message": "로그인 필요"}, 401)
    form = await req.form()
    to_email = (form.get("to") or "").strip()
    cc = (form.get("cc") or "").strip()
    subject = (form.get("subject") or "").strip()
    body = (form.get("body") or "")
    bcc = (form.get("bcc") or "").strip()
    body_html = (form.get("body_html") or "")
    draft_id = (form.get("draft_id") or "").strip()
    large_tokens = [t.strip() for t in (form.get("large_tokens") or "").split(",") if t.strip()]
    attachments, total = [], 0
    for f in form.getlist("files"):
        if hasattr(f, "read"):
            data = await f.read()
            if not data:
                continue
            total += len(data)
            attachments.append((f.filename or "file", data,
                                getattr(f, "content_type", "") or "application/octet-stream"))
    if total > 24 * 1024 * 1024:
        return JSONResponse({"ok": False, "message": "첨부 합계가 24MB를 넘습니다. 큰 파일은 링크로 보내세요(대용량 첨부)."}, 400)
    if not _mail.is_valid_email(to_email):
        return JSONResponse({"ok": False, "message": "받는 메일주소가 올바르지 않습니다."}, 400)
    from_addr = _mail_from_address()
    with db_session() as c:
        if not _mail.system_send_ready(c):
            return JSONResponse({"ok": False, "message": "보내기 설정이 안 돼 있습니다. 관리자 '메일 보내기 설정'에서 발송망을 먼저 등록하세요."}, 400)
        large_block = _mailbox.large_links_block(c, large_tokens, PUBLIC_BASE) if large_tokens else ""
        send_body = body + large_block
        send_html = ""
        if body_html and body_html.strip():
            send_html = _mailbox.sanitize_html_for_view(body_html, 0, [])
            if large_block:
                import html as _htmlmod
                send_html += ("<pre style='font-family:inherit;white-space:pre-wrap;margin:0'>"
                              + _htmlmod.escape(large_block) + "</pre>")
        ok, msg = _mail.send_system(c, from_addr, to_email, subject, send_body,
                                    from_name=u.get("name") or "", cc=cc, attachments=attachments,
                                    bcc=bcc, html=send_html)
        if ok:
            _mailbox.store_outbound(c, user_id=u["id"], from_email=from_addr, from_name=u.get("name") or "",
                                    to_email=to_email, subject=subject, body=send_body, cc=cc, bcc=bcc,
                                    body_html=send_html, size=len(send_body or "") + total)
            if draft_id:
                try:
                    _mailbox.delete_draft(c, int(draft_id), u["id"])
                except Exception:
                    pass
    return JSONResponse({"ok": ok, "message": msg})


@router.post("/mail/draft/save")
async def mail_draft_save(req: Request):
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False}, 401)
    form = await req.form()
    did = (form.get("draft_id") or "").strip()
    with db_session() as c:
        nid = _mailbox.save_draft(c, user_id=u["id"], draft_id=int(did) if did.isdigit() else None,
                                  to_email=(form.get("to") or "").strip(), cc=(form.get("cc") or "").strip(),
                                  bcc=(form.get("bcc") or "").strip(), subject=(form.get("subject") or "").strip(),
                                  body=(form.get("body") or ""), body_html=(form.get("body_html") or ""))
    return JSONResponse({"ok": True, "draft_id": nid})


# ─── 대용량 첨부 ─────────────────────────────────────────────
@router.post("/mail/large/upload")
async def mail_large_upload(req: Request):
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False, "message": "로그인 필요"}, 401)
    import os as _os, shutil as _sh
    form = await req.form()
    f = form.get("file")
    if not f or not hasattr(f, "read"):
        return JSONResponse({"ok": False, "message": "파일이 없습니다."}, 400)
    fname = getattr(f, "filename", "") or "file"
    mime = getattr(f, "content_type", "") or "application/octet-stream"
    token = _mailbox.new_large_token()
    d = _mailbox.large_file_dir(token)
    _os.makedirs(d, exist_ok=True)
    path = _os.path.join(d, _mailbox.safe_filename(fname))
    size = 0
    try:
        with open(path, "wb") as out:
            while True:
                chunk = await f.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > _LARGE_MAX:
                    out.close(); _sh.rmtree(d, ignore_errors=True)
                    return JSONResponse({"ok": False, "message": "파일이 너무 큽니다(최대 500MB)."}, 400)
                out.write(chunk)
    except Exception as e:
        _sh.rmtree(d, ignore_errors=True)
        return JSONResponse({"ok": False, "message": f"업로드 실패: {str(e)[:80]}"}, 500)
    with db_session() as c:
        exp = _mailbox.register_large_file(c, token=token, user_id=u["id"], filename=fname,
                                           mime=mime, path=path, size=size, expiry_days=30)
    return JSONResponse({"ok": True, "token": token, "filename": fname, "size": size,
                         "size_h": _mailbox.human_size(size), "url": f"{PUBLIC_BASE}/dl/{token}", "expires_at": exp})


@router.get("/dl/{token}")
async def mail_large_download(req: Request, token: str):
    import os as _os
    def _msg(title, sub, code):
        return HTMLResponse(
            f"<!doctype html><meta charset=utf-8><div style='font-family:system-ui,sans-serif;"
            f"max-width:520px;margin:80px auto;text-align:center;color:#374151'>"
            f"<div style='font-size:40px'>📭</div><h2>{title}</h2>"
            f"<p style='color:#6b7280'>{sub}</p></div>", status_code=code)
    with db_session() as c:
        info = _mailbox.get_large_file(c, token)
        if not info:
            return _msg("다운로드할 수 없습니다", "링크가 잘못되었거나 파일이 삭제되었습니다.", 404)
        if info.get("expired"):
            return _msg("유효기간이 지났습니다", "이 다운로드 링크는 만료되었습니다(보낸 지 30일 경과).", 410)
        if not info.get("path") or not _os.path.exists(info["path"]):
            return _msg("파일을 찾을 수 없습니다", "파일이 서버에서 삭제되었을 수 있습니다.", 404)
        _mailbox.bump_large_download(c, token)
    import urllib.parse as _up
    fn = info["filename"] or "download"
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{_up.quote(fn)}",
               "X-Content-Type-Options": "nosniff"}
    return FileResponse(info["path"], media_type=info["mime"] or "application/octet-stream", headers=headers)


# ─── 메일 보기 / 읽기 창 / 첨부 ──────────────────────────────
@router.get("/mail/{mail_id:int}")
async def mail_view_page(req: Request, mail_id: int):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        m = _mailbox.get_mail(c, mail_id, u["id"])
        if not m:
            return RedirectResponse("/mail/inbox", 303)
        _mailbox.mark_read(c, mail_id, u["id"])
        all_atts = _mailbox.list_attachments(c, mail_id)
        inline_atts = [a for a in all_atts if a.get("is_inline")]
        file_atts = [a for a in all_atts if not a.get("is_inline")]
        safe_html = _mailbox.sanitize_html_for_view(m.get("body_html") or "", mail_id, inline_atts)
    # 보낸이↔연락처 연결은 WORKS(shared_contacts) 의존 → 독립 앱 보류(None)
    return ctx(req, "mail_view.html", user=u, m=m, ai_on=ai_enabled_for(u),
               safe_html=safe_html, file_atts=file_atts, has_html=bool(safe_html), sender_contact=None)


@router.get("/mail/{mail_id:int}/pane", response_class=HTMLResponse)
async def mail_view_pane(req: Request, mail_id: int):
    u = get_user(req)
    if not u:
        return HTMLResponse("<div style='padding:24px;color:#b91c1c'>로그인이 필요합니다.</div>", status_code=401)
    with db_session() as c:
        m = _mailbox.get_mail(c, mail_id, u["id"])
        if not m:
            return HTMLResponse("<div style='padding:24px;color:#b91c1c'>메일을 찾을 수 없습니다.</div>", status_code=404)
        _mailbox.mark_read(c, mail_id, u["id"])
        all_atts = _mailbox.list_attachments(c, mail_id)
        inline_atts = [a for a in all_atts if a.get("is_inline")]
        file_atts = [a for a in all_atts if not a.get("is_inline")]
        safe_html = _mailbox.sanitize_html_for_view(m.get("body_html") or "", mail_id, inline_atts)
    return ctx(req, "mail_view_pane.html", user=u, m=m, ai_on=ai_enabled_for(u),
               safe_html=safe_html, file_atts=file_atts, has_html=bool(safe_html), sender_contact=None)


@router.get("/mail/{mail_id:int}/att/{att_id:int}")
async def mail_attachment(req: Request, mail_id: int, att_id: int):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        a = _mailbox.get_attachment(c, att_id, u["id"])
    if not a:
        return Response(status_code=404)
    mime = a["mime"] or "application/octet-stream"
    import urllib.parse as _up
    fn = a["filename"] or "attachment"
    disp = "inline" if (mime.startswith("image/") or mime == "application/pdf") else "attachment"
    headers = {"Content-Disposition": f"{disp}; filename*=UTF-8''{_up.quote(fn)}",
               "X-Content-Type-Options": "nosniff", "Cache-Control": "private, max-age=3600"}
    return Response(content=a["data"], media_type=mime, headers=headers)


@router.get("/mail/{mail_id:int}/_diag")
async def mail_view_diag(req: Request, mail_id: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False, "message": "로그인 필요"}, 401)
    import re as _re
    with db_session() as c:
        m = _mailbox.get_mail(c, mail_id, u["id"])
        if not m:
            return JSONResponse({"ok": False, "message": "메일을 찾을 수 없음(본인 메일만)"}, 404)
        rows = c.execute("SELECT id, filename, mime, size, is_inline, content_id, "
                         "(data IS NOT NULL) AS has_data, length(data) AS dlen "
                         "FROM mail_attachments WHERE mail_id=? ORDER BY id", (mail_id,)).fetchall()
    atts = [dict(r) for r in rows]
    html = m.get("body_html") or ""
    cid_refs = _re.findall(r"(?is)src\s*=\s*[\"']\s*cid:([^\"']+)[\"']", html)
    img_srcs = _re.findall(r"(?is)<img[^>]*\ssrc\s*=\s*[\"']([^\"']{0,80})", html)
    return JSONResponse({"ok": True, "mail_id": mail_id, "html_len": len(html), "has_html": bool(html),
                         "attachments": atts, "cid_refs_in_html": cid_refs, "img_src_samples": img_srcs[:12]})


# ─── 상태 변경 (별표·삭제·읽음·복원·완전삭제) ────────────────
@router.post("/mail/{mail_id:int}/star")
async def mail_star(req: Request, mail_id: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False}, 401)
    with db_session() as c:
        new = _mailbox.toggle_star(c, mail_id, u["id"])
    if new is None:
        return JSONResponse({"ok": False}, 404)
    return JSONResponse({"ok": True, "starred": bool(new)})


@router.post("/mail/{mail_id:int}/delete")
async def mail_delete(req: Request, mail_id: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False}, 401)
    with db_session() as c:
        ok = _mailbox.soft_delete(c, mail_id, u["id"])
    return JSONResponse({"ok": ok})


@router.post("/mail/{mail_id:int}/read")
async def mail_set_read(req: Request, mail_id: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False}, 401)
    form = await req.form()
    read = (form.get("read") or "1") != "0"
    with db_session() as c:
        _mailbox.set_read(c, mail_id, u["id"], read=read)
    return JSONResponse({"ok": True, "read": read})


@router.post("/mail/{mail_id:int}/restore")
async def mail_restore(req: Request, mail_id: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False, "message": "로그인 필요"}, 401)
    with db_session() as c:
        ok_r = _mailbox.restore_mail(c, mail_id, u["id"])
    return JSONResponse({"ok": ok_r})


@router.post("/mail/{mail_id:int}/purge")
async def mail_purge_one(req: Request, mail_id: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False, "message": "로그인 필요"}, 401)
    with db_session() as c:
        ok_r = _mailbox.hard_delete_mail(c, mail_id, u["id"])
    return JSONResponse({"ok": ok_r})


@router.post("/mail/trash/empty")
async def mail_trash_empty(req: Request):
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False, "message": "로그인 필요"}, 401)
    with db_session() as c:
        n = _mailbox.empty_trash(c, u["id"])
    return JSONResponse({"ok": True, "count": n})


# ─── AI (번역 · 메일 정리) ───────────────────────────────────
@router.post("/api/mail/{mail_id:int}/translate")
async def mail_translate(req: Request, mail_id: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False, "message": "로그인 필요"}, 401)
    form = await req.form()
    target = (form.get("target") or "ko").strip()
    if target not in ("ko", "vi", "en"):
        target = "ko"
    with db_session() as c:
        ok, res = _mailbox.translate_mail(c, mail_id, u["id"], target=target)
    if not ok:
        return JSONResponse({"ok": False, "message": res})
    return JSONResponse({"ok": True, "subject": res["subject"], "body": res["body"]})


@router.get("/api/mail/contacts")
async def mail_contacts_api(req: Request, q: str = ""):
    """받는사람 자동완성 — WORKS 연락처(shared_contacts) 의존. 독립 앱 보류(빈 목록)."""
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False}, 401)
    return JSONResponse({"ok": True, "items": []})


@router.post("/api/mail/ai-compose")
async def mail_ai_compose(req: Request):
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False, "message": "로그인 필요"}, 401)
    form = await req.form()
    rough = (form.get("body") or "").strip()
    cur_subject = (form.get("subject") or "").strip()
    if not rough:
        return JSONResponse({"ok": False, "message": "먼저 본문에 요점을 적어주세요."})
    try:
        import json as _json
        if not ai_client.ai_available():
            return JSONResponse({"ok": False, "message": "AI가 비활성 상태입니다(키 미설정)."})
        system = (
            "당신은 ㈜케이엔케이(KNK·검사기/자동화 설비 제조)의 비즈니스 이메일 작성 도우미입니다. "
            "사용자가 적은 거친 메모·요점을 정중하고 명확한 업무 이메일로 다듬으세요. "
            "규칙: ①인사말·본문·맺음말을 갖춘 자연스러운 메일 ②메모에 없는 사실(수치·날짜·금액·약속)을 "
            "절대 지어내지 말 것 ③서명은 넣지 말 것(시스템이 따로 붙임) ④간결·정중·과장 금지 "
            "⑤원문이 베트남어면 베트남어로, 한국어면 한국어로 작성. "
            '출력은 JSON 한 줄만: {"subject":"제목 제안","body":"메일 본문"} . 다른 텍스트·설명·코드블록 금지.')
        prompt = f"[현재 제목]\n{cur_subject or '(없음)'}\n\n[거친 메모]\n{rough[:4000]}"
        ok, resp = ai_client.ai_chat(prompt, system=system, max_tokens=900, temperature=0.4)
        if not ok:
            return JSONResponse({"ok": False, "message": "AI 정리 실패 — 잠시 후 다시 시도해주세요."})
        subject, bodyout = cur_subject, (resp or "").strip()
        try:
            s = resp or ""
            i, j = s.find("{"), s.rfind("}")
            if i >= 0 and j > i:
                d = _json.loads(s[i:j + 1])
                bodyout = (d.get("body") or "").strip() or bodyout
                if not cur_subject:
                    subject = (d.get("subject") or "").strip() or subject
        except Exception:
            pass
        return JSONResponse({"ok": True, "subject": subject, "body": bodyout})
    except Exception as e:
        return JSONResponse({"ok": False, "message": f"오류: {str(e)[:80]}"})


# ─── 메일 → 업무 전환 (WORKS 연동 보류) ──────────────────────
@router.post("/mail/{mail_id:int}/to-task")
async def mail_to_task(req: Request, mail_id: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False, "message": "로그인 필요"}, 401)
    return JSONResponse({"ok": False, "message": "‘할 일로 보내기’는 WORKS 연동 준비 중입니다(메일 독립 분리 단계)."})


@router.post("/mail/{mail_id:int}/to-contact")
async def mail_to_contact(req: Request, mail_id: int):
    u = get_user(req)
    if not u:
        return JSONResponse({"ok": False, "message": "로그인 필요"}, 401)
    return JSONResponse({"ok": False, "message": "‘연락처로 등록’은 WORKS 연동 준비 중입니다(메일 독립 분리 단계)."})


# ═══════════════════════════════════════════════════════════════
#  관리자 — 받기/보내기/가져오기/정리 설정
# ═══════════════════════════════════════════════════════════════
@router.get("/admin/mail-inbound", response_class=HTMLResponse)
async def admin_mail_inbound_page(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        _au = get_user(req)
        return RedirectResponse(role_home(_au) if _au else "/login", 303)
    with db_session() as c:
        rid = _mailbox.resolve_recipient(c, _MAIL_POC_ADDR)
        rrow = c.execute("SELECT name, role FROM users WHERE id=?", (rid,)).fetchone() if rid else None
        recip_name = (rrow["name"] if rrow else "(미지정)")
    recip_is_me = bool(rid and rid == u["id"])
    return ctx(req, "admin_mail_inbound.html", user=u, active="admin",
               token=_mail_inbound_token(), inbound_url=f"{PUBLIC_BASE}/api/mail/inbound",
               poc_addr=_MAIL_POC_ADDR, recip_name=recip_name, recip_is_me=recip_is_me,
               bound=req.query_params.get("bound"), saved=(req.query_params.get("saved") == "1"))


@router.post("/admin/mail-inbound")
async def admin_mail_inbound_gen(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    import secrets
    new_token = secrets.token_urlsafe(32)
    with db_session() as c:
        c.execute("INSERT INTO app_settings(key, value) VALUES(?, ?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value", ("mail_inbound_token", new_token))
    return RedirectResponse("/admin/mail-inbound?saved=1", 303)


@router.post("/admin/mail-inbound/bind-me")
async def admin_mail_inbound_bind(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    with db_session() as c:
        c.execute("INSERT INTO app_settings(key, value) VALUES('mail_default_user_id', ?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(u["id"]),))
        c.execute("INSERT INTO mail_aliases(address, user_id) VALUES(?, ?) "
                  "ON CONFLICT(address) DO UPDATE SET user_id=excluded.user_id", (_MAIL_POC_ADDR, u["id"]))
        moved = c.execute("UPDATE mail_messages SET user_id=? WHERE to_email=? AND is_deleted=0",
                          (u["id"], _MAIL_POC_ADDR)).rowcount
    return RedirectResponse(f"/admin/mail-inbound?bound={moved}", 303)


@router.get("/admin/mail-send", response_class=HTMLResponse)
async def admin_mail_send_page(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        _au = get_user(req)
        return RedirectResponse(role_home(_au) if _au else "/login", 303)
    with db_session() as c:
        ready = _mail.system_send_ready(c)
    return ctx(req, "admin_mail_send.html", user=u, active="admin", ready=ready, mail_key=_mail.mail_available(),
               cur_host=get_setting("mail_send_host", ""), cur_port=(get_setting("mail_send_port", "") or "465"),
               cur_user=get_setting("mail_send_user", ""), has_pass=bool(get_setting("mail_send_pass_enc", "")),
               cur_from=_mail_from_address(), saved=(req.query_params.get("saved") == "1"))


@router.post("/admin/mail-send")
async def admin_mail_send_save(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        return RedirectResponse("/login", 303)
    if not _mail.mail_available():
        return JSONResponse({"ok": False, "message": "메일 암호화 키(KNK_MAIL_KEY)가 서버에 없습니다. 전산담당자에게 .env 등록 요청."}, 400)
    form = await req.form()
    with db_session() as c:
        _mail.save_send_config(c, (form.get("host") or "").strip(), (form.get("port") or "465").strip(),
                               (form.get("user") or "").strip(), (form.get("password") or "").strip())
        from_addr = (form.get("from_address") or "").strip()
        if from_addr:
            c.execute("INSERT INTO app_settings(key, value) VALUES('mail_from_address', ?) "
                      "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (from_addr,))
    return RedirectResponse("/admin/mail-send?saved=1", 303)


# ── 가져오기 (POP3/IMAP) ──────────────────────────────────────
def _mailfetch_creds(c, u, form=None):
    acct = _mailfetch.get_account(c, u["id"])
    if form is not None:
        protocol = (form.get("protocol") or (acct.get("protocol") if acct else "pop3") or "pop3").strip().lower()
        host = (form.get("host") or "").strip(); port = (form.get("port") or "").strip()
        ssl = bool(form.get("ssl")); user = (form.get("user") or "").strip(); pw = (form.get("password") or "")
    else:
        protocol = ((acct.get("protocol") if acct else "pop3") or "pop3")
        host = acct.get("host") if acct else ""; port = acct.get("port") if acct else 995
        ssl = bool(acct.get("use_ssl")) if acct else True
        user = acct.get("username") if acct else ""; pw = ""
    if not pw and acct:
        pw = _mail.decrypt(acct.get("password_enc") or "")
    return protocol, host, port, ssl, user, pw, acct


@router.get("/admin/mail-fetch", response_class=HTMLResponse)
async def admin_mail_fetch_page(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        _au = get_user(req)
        return RedirectResponse(role_home(_au) if _au else "/login", 303)
    with db_session() as c:
        acct = _mailfetch.get_account(c, u["id"])
    return ctx(req, "admin_mail_fetch.html", user=u, active="admin",
               acct=acct, key_ok=_mail.mail_available(), owner_name=(u.get("name") or "본인"))


@router.post("/admin/mail-fetch/save")
async def admin_mail_fetch_save(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"ok": False, "message": "권한 없음"}, 403)
    if not _mail.mail_available():
        return JSONResponse({"ok": False, "message": "메일 암호화 키(KNK_MAIL_KEY)가 서버에 없습니다. 전산담당자에게 .env 등록 요청."}, 400)
    form = await req.form()
    password = (form.get("password") or "")
    pw_enc = _mail.encrypt(password) if password else None
    with db_session() as c:
        _mailfetch.save_account(c, u["id"], protocol=(form.get("protocol") or "pop3").strip().lower(),
                                host=(form.get("host") or "").strip(), port=(form.get("port") or "").strip(),
                                use_ssl=bool(form.get("ssl")), username=(form.get("user") or "").strip(),
                                password_enc=pw_enc, label="하이웍스")
    return JSONResponse({"ok": True})


@router.post("/admin/mail-fetch/test")
async def admin_mail_fetch_test(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"ok": False, "message": "권한 없음"}, 403)
    form = await req.form()
    with db_session() as c:
        protocol, host, port, ssl, user, pw, _acct = _mailfetch_creds(c, u, form)
    if not (host and user and pw):
        return JSONResponse({"ok": False, "message": "서버·계정·비밀번호를 입력하세요."})
    res = await run_in_threadpool(_mailfetch.test_connection, protocol, host, port, ssl, user, pw)
    return JSONResponse(res)


@router.post("/admin/mail-fetch/start-point")
async def admin_mail_fetch_startpoint(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"ok": False, "message": "권한 없음"}, 403)
    with db_session() as c:
        protocol, host, port, ssl, user, pw, acct = _mailfetch_creds(c, u, None)
    if not acct or not (host and user and pw):
        return JSONResponse({"ok": False, "message": "먼저 계정·비밀번호를 저장하세요."}, 400)
    if protocol == "imap":
        res = await run_in_threadpool(_mailfetch.imap_current_max_uid, host, port, ssl, user, pw)
        if not res.get("ok"):
            return JSONResponse({"ok": False, "message": res.get("message", "연결 실패")})
        with db_session() as c:
            _mailfetch.set_status(c, u["id"], last_uid=res["uid"], status="시작점 설정(uid=%d)" % res["uid"])
        return JSONResponse({"ok": True, "uid": res["uid"]})
    res = await run_in_threadpool(_mailfetch.pop3_uidls, host, port, ssl, user, pw)
    if not res.get("ok"):
        return JSONResponse({"ok": False, "message": res.get("message", "연결 실패")})
    uidls = [uidl for (_num, uidl) in res.get("items", [])]
    with db_session() as c:
        _mailfetch.add_seen(c, acct["id"], uidls)
        _mailfetch.set_status(c, u["id"], status="시작점 설정(%d통 표시)" % len(uidls))
    return JSONResponse({"ok": True, "uid": len(uidls)})


@router.post("/admin/mail-fetch/run")
async def admin_mail_fetch_run(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"ok": False, "message": "권한 없음"}, 403)
    with db_session() as c:
        protocol, host, port, ssl, user, pw, acct = _mailfetch_creds(c, u, None)
    if not acct or not (host and user and pw):
        return JSONResponse({"ok": False, "message": "먼저 계정·비밀번호를 저장하세요."}, 400)
    if protocol == "imap":
        res = await run_in_threadpool(_mailfetch.imap_collect, host, port, ssl, user, pw, acct.get("last_uid") or 0)
    else:
        with db_session() as c:
            seen = _mailfetch.get_seen(c, acct["id"])
        res = await run_in_threadpool(_mailfetch.pop3_collect, host, port, ssl, user, pw, seen)
    if not res.get("ok"):
        with db_session() as c:
            _mailfetch.set_status(c, u["id"], status="실패: " + res.get("error", ""))
        return JSONResponse({"ok": False, "message": "가져오기 실패: " + res.get("error", "")})
    stored = 0
    ai_on = ai_enabled_for(u)
    with db_session() as c:
        for key, raw in res.get("messages", []):
            try:
                parsed = _mailbox.parse_raw_email(raw)
                if not parsed:
                    continue
                mid, _own = _mailbox.store_inbound(
                    c, to_email=(parsed.get("to_email") or user), from_email=parsed.get("from_email", ""),
                    from_name=parsed.get("from_name", ""), subject=parsed.get("subject", ""),
                    text=parsed.get("text", ""), html=parsed.get("html", ""), cc=parsed.get("cc", ""),
                    size=len(raw), owner_id=acct["owner_user_id"], run_ai=ai_on, attachments=parsed.get("attachments"))
                if mid:
                    stored += 1
            except Exception:
                pass
        if protocol == "imap":
            _mailfetch.set_status(c, u["id"], last_uid=res.get("max_uid", acct.get("last_uid") or 0),
                                  status="가져오기 %d건" % stored, count=stored)
        else:
            _mailfetch.add_seen(c, acct["id"], [k for (k, _r) in res.get("messages", [])])
            _mailfetch.set_status(c, u["id"], status="가져오기 %d건" % stored, count=stored)
    return JSONResponse({"ok": True, "count": stored})


# ── 오래된 메일 일괄정리 + 디스크정리(VACUUM) ─────────────────
def _purge_cutoff_iso(months) -> str:
    from datetime import datetime, timedelta
    try:
        m = max(1, int(months or 12))
    except Exception:
        m = 12
    return (datetime.now() - timedelta(days=m * 30)).strftime("%Y-%m-%d %H:%M:%S")


@router.get("/admin/mail-purge", response_class=HTMLResponse)
async def admin_mail_purge_page(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        _au = get_user(req)
        return RedirectResponse(role_home(_au) if _au else "/login", 303)
    with db_session() as c:
        trash_n = _mailbox.count_trash(c, u["id"])
    return ctx(req, "admin_mail_purge.html", user=u, active="admin", trash_n=trash_n)


@router.post("/admin/mail-purge/preview")
async def admin_mail_purge_preview(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"ok": False, "message": "권한 없음"}, 403)
    form = await req.form()
    before = _purge_cutoff_iso(form.get("months") or 12)
    with db_session() as c:
        n = _mailbox.purge_old_count(c, u["id"], before)
    return JSONResponse({"ok": True, "count": n, "before": before[:10]})


@router.post("/admin/mail-purge/run")
async def admin_mail_purge_run(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"ok": False, "message": "권한 없음"}, 403)
    form = await req.form()
    before = _purge_cutoff_iso(form.get("months") or 12)
    with db_session() as c:
        n = _mailbox.purge_old(c, u["id"], before)
    return JSONResponse({"ok": True, "count": n, "before": before[:10]})


@router.post("/admin/mail-purge/vacuum")
async def admin_mail_purge_vacuum(req: Request):
    u = require(req, ["admin", "ceo"])
    if not u:
        return JSONResponse({"ok": False, "message": "권한 없음"}, 403)
    import sqlite3
    try:
        conn = sqlite3.connect(config.DB_PATH, isolation_level=None, timeout=60)
        conn.execute("VACUUM")
        conn.close()
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "message": f"디스크정리 실패: {str(e)[:80]}"}, 500)
