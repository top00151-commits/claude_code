# -*- coding: utf-8 -*-
"""KNK Eum MAIL — 자동 수신 스케줄러.

지금까지는 관리자가 '가져오기'를 눌러야 새 메일이 들어왔다.
이 모듈은 앱이 떠 있는 동안 일정 주기로 '모든 활성 계정'의 새 메일을
자동으로 받아 저장한다(수동 '가져오기'와 동일 로직 재사용).

설계(안전):
- 단일 워커(uvicorn 워커 1개) 전제 → 중복 실행 없음.
- 블로킹 POP3/IMAP·DB 작업은 asyncio.to_thread 로 별도 스레드에서 실행 → 이벤트루프 안 막음.
- 전 구간 try/except → 한 계정 실패가 전체/웹앱에 영향 없음. 실패해도 다음 주기에 재시도.
- 주기: 환경변수 KNK_MAIL_FETCH_INTERVAL(초, 기본 180). KNK_MAIL_AUTOFETCH=0 이면 끔.
- AI 분류는 비용·지연 때문에 기본 꺼짐(run_ai=False). 메일은 자동으로 들어오고,
  AI 자동분류가 필요하면 KNK_MAIL_AUTOFETCH_AI=1 로 켤 수 있음.
"""
from __future__ import annotations

import asyncio
import os
import traceback

from . import db
from . import mail_fetch as _mf
from . import mail_store as _ms
from . import mail_send as _mail

_INTERVAL = int(os.environ.get("KNK_MAIL_FETCH_INTERVAL", "180"))
_AI_ON = os.environ.get("KNK_MAIL_AUTOFETCH_AI", "0") == "1"


def _fetch_one(acct: dict) -> int:
    """계정 1개의 새 메일을 받아 저장. 반환: 저장 건수. (블로킹 — 스레드에서 호출)"""
    protocol = (acct.get("protocol") or "pop3").lower()
    host = acct.get("host") or ""
    port = acct.get("port")
    ssl = bool(acct.get("use_ssl"))
    user = acct.get("username") or ""
    owner_id = acct.get("owner_user_id")
    pw = _mail.decrypt(acct.get("password_enc") or "")
    if not (host and user and pw):
        return 0

    if protocol == "imap":
        res = _mf.imap_collect(host, port, ssl, user, pw, acct.get("last_uid") or 0)
    else:
        with db.db_session() as c:
            seen = _mf.get_seen(c, acct["id"])
        res = _mf.pop3_collect(host, port, ssl, user, pw, seen)

    if not res.get("ok"):
        with db.db_session() as c:
            _mf.set_status(c, owner_id, status="자동: 실패 " + (res.get("error") or "")[:120])
        return 0

    stored = 0
    with db.db_session() as c:
        for _key, raw in res.get("messages", []):
            try:
                parsed = _ms.parse_raw_email(raw)
                if not parsed:
                    continue
                mid, _own = _ms.store_inbound(
                    c,
                    to_email=(parsed.get("to_email") or user),
                    from_email=parsed.get("from_email", ""),
                    from_name=parsed.get("from_name", ""),
                    subject=parsed.get("subject", ""),
                    text=parsed.get("text", ""),
                    html=parsed.get("html", ""),
                    cc=parsed.get("cc", ""),
                    size=len(raw),
                    owner_id=owner_id,
                    run_ai=_AI_ON,
                    attachments=parsed.get("attachments"),
                )
                if mid:
                    stored += 1
            except Exception:
                pass
        if protocol == "imap":
            _mf.set_status(c, owner_id, last_uid=res.get("max_uid", acct.get("last_uid") or 0),
                           status="자동 가져오기 %d건" % stored, count=stored)
        else:
            _mf.add_seen(c, acct["id"], [k for (k, _r) in res.get("messages", [])])
            _mf.set_status(c, owner_id, status="자동 가져오기 %d건" % stored, count=stored)
    return stored


def _fetch_all_sync() -> tuple[int, int]:
    """모든 활성 계정 1회 수신. 반환 (총저장건수, 계정수). (블로킹)"""
    with db.db_session() as c:
        accts = _mf.list_enabled_accounts(c)
    total = 0
    for acct in accts:
        try:
            total += _fetch_one(acct)
        except Exception:
            traceback.print_exc()
    return total, len(accts)


async def _loop():
    await asyncio.sleep(20)  # 앱 기동 직후 부담 회피
    while True:
        try:
            total, n = await asyncio.to_thread(_fetch_all_sync)
            if total:
                print("[AUTO-FETCH] 저장 %d건 / 계정 %d개" % (total, n), flush=True)
        except Exception:
            traceback.print_exc()
        await asyncio.sleep(_INTERVAL)


def start(app):
    """main.py 에서 호출 — 앱 startup 시 백그라운드 자동수신 시작."""
    if os.environ.get("KNK_MAIL_AUTOFETCH", "1") == "0":
        print("[AUTO-FETCH] 비활성(KNK_MAIL_AUTOFETCH=0)", flush=True)
        return

    @app.on_event("startup")
    async def _start_auto_fetch():  # pragma: no cover
        try:
            asyncio.create_task(_loop())
            print("[AUTO-FETCH] 자동수신 시작 (주기 %ds, AI=%s)" % (_INTERVAL, _AI_ON), flush=True)
        except Exception:
            traceback.print_exc()
