"""
KNK Mail — 메일함(받기) 저장·조회·AI 처리
=================================================================
KNK 자체 메일 시스템 Phase 0 POC (2026-06-13, 대표 지시).
- Cloudflare Email Routing(Worker) → /api/mail/inbound → 본 모듈로 적재
- 받은 메일을 mail_messages 에 보관, AI(ai_client)로 자동 분류·언어감지·요약
- 발송(SMTP/SES)은 mail_send.py 담당. 본 모듈은 '받기 + 보관 + 조회 + AI'.

설계 메모(절대 준수):
- 수신 주소(to) → WORKS 사용자 매핑: mail_aliases 우선, 없으면 대표(김정락 kjr) 기본
  (POC: test@knk-mailtest.com → 대표 메일함). owner_id 명시 시 그대로 사용(데모).
- 실패는 표면화 — except: pass 로 메일을 조용히 버리지 않는다(데이터 연결성 안전 원칙).
  AI 불가/오류 시에도 메일은 반드시 저장(분류='일반'·요약 없음 폴백).
- 본문은 Jinja 자동이스케이프로 출력(XSS 방지). HTML 원문은 보관만, 화면은 text 표시.
"""
from __future__ import annotations

import re
import json
from email.utils import parseaddr

# AI 가 판정하는 분류 4종
CATEGORIES = ("견적", "발주", "세금계산서", "일반")


# ─── 주소 정규화 / 수신자 매핑 ──────────────────────────────────────
def _norm_addr(addr: str) -> str:
    """'홍길동 <a@b.com>' → 'a@b.com' (소문자)."""
    _, mail = parseaddr(addr or "")
    return (mail or "").strip().lower()


def default_owner(c):
    """수신자 미지정 시 기본 소유자 — 대표 김정락(login_id=kjr) → 이름 → role=ceo 순.
    ★ 2026-06-13 수정: 'username' 컬럼은 없음(실제 컬럼 login_id) — 과거 1순위 쿼리가
      항상 실패해 try/except 로 가려진 채 이름 매칭으로 폴백되던 잠복버그(z383 원인 일부)."""
    for sql in (
        "SELECT id FROM users WHERE login_id='kjr' AND is_active=1",
        "SELECT id FROM users WHERE name='김정락' AND is_active=1 ORDER BY id LIMIT 1",
        "SELECT id FROM users WHERE role='ceo' AND is_active=1 ORDER BY id LIMIT 1",
        "SELECT id FROM users WHERE role IN ('admin','ceo') AND is_active=1 ORDER BY id LIMIT 1",
    ):
        try:
            r = c.execute(sql).fetchone()
        except Exception:
            r = None
        if r:
            return r["id"]
    return None


def resolve_recipient(c, to_email: str):
    """수신 주소 → WORKS 사용자 id.
    ① mail_aliases(주소별 매핑) → ② 관리자 지정 기본 수신자(mail_default_user_id) → ③ default_owner.
    ②는 관리자가 '내 메일함으로 받기'로 지정 — 운영 DB에 동명 계정이 여럿일 때 엉뚱한 계정으로 가는 것 방지."""
    addr = _norm_addr(to_email)
    if addr:
        try:
            r = c.execute("SELECT user_id FROM mail_aliases WHERE address=?", (addr,)).fetchone()
            if r and r["user_id"]:
                return r["user_id"]
        except Exception:
            pass
    # 관리자 지정 기본 수신자
    try:
        r = c.execute("SELECT value FROM app_settings WHERE key='mail_default_user_id'").fetchone()
        if r and (r["value"] or "").strip():
            uid = int(r["value"])
            ok = c.execute("SELECT 1 FROM users WHERE id=? AND is_active=1", (uid,)).fetchone()
            if ok:
                return uid
    except Exception:
        pass
    return default_owner(c)


# ─── AI 보조(분류·언어·요약) — 모두 안전 폴백 ──────────────────────
def _html_to_text(html: str) -> str:
    if not html:
        return ""
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _parse_classify(resp: str):
    """AI JSON 응답 → (category, lang). 파싱 실패 시 ('일반','')."""
    cat, lang = "일반", ""
    try:
        s = (resp or "").strip()
        i, j = s.find("{"), s.rfind("}")
        if i >= 0 and j > i:
            d = json.loads(s[i:j + 1])
            c2 = (d.get("category") or "").strip()
            if c2 in CATEGORIES:
                cat = c2
            l2 = (d.get("lang") or "").strip().lower()
            if l2 in ("ko", "vi", "en"):
                lang = l2
    except Exception:
        pass
    return (cat, lang)


def _ai_classify(subject: str, body: str):
    """메일 → (분류, 언어). AI 없거나 오류면 ('일반','')."""
    try:
        from . import ai_client
        if not ai_client.ai_available():
            return ("일반", "")
        text = f"제목: {subject}\n본문:\n{(body or '')[:2000]}"
        system = (
            "당신은 KNK(검사기·자동화 설비 제조)의 메일 분류기입니다. "
            "아래 메일을 읽고 JSON 한 줄로만 답하세요. "
            '형식: {"category":"견적|발주|세금계산서|일반","lang":"ko|vi|en"} . '
            "category=메일 성격(견적 요청·회신→견적, 주문·발주→발주, 세금계산서·인보이스→세금계산서, "
            "그 외→일반). lang=본문 주 언어. 설명·따옴표·다른 텍스트 금지, JSON 만 출력."
        )
        ok, resp = ai_client.ai_chat(text, system=system, max_tokens=60, temperature=0)
        if not ok:
            return ("일반", "")
        return _parse_classify(resp)
    except Exception:
        return ("일반", "")


def _ai_summary(body: str) -> str:
    """본문 → 5줄 불릿 요약. AI 없거나 오류면 ''."""
    try:
        from . import ai_client
        if not ai_client.ai_available():
            return ""
        if not (body or "").strip():
            return ""
        ok, resp = ai_client.ai_summarize(body, style="bullet")
        return (resp or "").strip() if ok else ""
    except Exception:
        return ""


# ─── 저장(받기) ─────────────────────────────────────────────────────
def store_inbound(c, *, to_email: str, from_email: str = "", from_name: str = "",
                  subject: str = "", text: str = "", html: str = "", cc: str = "",
                  size=0, owner_id=None, run_ai: bool = True, attachments=None):
    """받은 메일 1건 저장. 반환 (mail_id, owner_id).
    owner_id 미지정 시 to_email 로 수신자 해석. 수신자 없으면 (None, None).
    attachments: parse_raw_email 이 만든 [{filename,mime,size,content_id,inline,data}, ...]."""
    owner = owner_id or resolve_recipient(c, to_email)
    if not owner:
        return (None, None)
    subject = (subject or "(제목 없음)").strip()
    body = (text or "").strip() or _html_to_text(html)
    category, lang, summary = "일반", "", ""
    if run_ai:
        category, lang = _ai_classify(subject, body)
        summary = _ai_summary(body)
    try:
        sz = int(size or 0)
    except Exception:
        sz = 0
    cur = c.execute(
        """INSERT INTO mail_messages
           (user_id, direction, from_email, from_name, to_email, cc,
            subject, body_text, body_html, category, lang, summary, raw_size)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (owner, "in", _norm_addr(from_email), (from_name or "").strip(),
         _norm_addr(to_email), (cc or "").strip(), subject, body, html or "",
         category, lang, summary, sz),
    )
    mail_id = cur.lastrowid
    if attachments:
        _save_attachments(c, mail_id, attachments)
    return (mail_id, owner)


# ─── 조회 ───────────────────────────────────────────────────────────
def list_inbox(c, user_id: int, *, category: str = "", limit: int = 200, offset: int = 0):
    where = "user_id=? AND direction='in' AND is_deleted=0"
    args = [user_id]
    if category and category in CATEGORIES:
        where += " AND category=?"
        args.append(category)
    rows = c.execute(
        f"""SELECT id, from_email, from_name, subject, category, lang,
                   is_read, is_starred, received_at,
                   substr(COALESCE(summary,''),1,160) AS summary_short
            FROM mail_messages WHERE {where}
            ORDER BY received_at DESC, id DESC LIMIT ? OFFSET ?""",
        (*args, limit, offset),
    ).fetchall()
    return [dict(r) for r in rows]


def count_unread(c, user_id: int) -> int:
    r = c.execute(
        "SELECT COUNT(*) AS n FROM mail_messages "
        "WHERE user_id=? AND direction='in' AND is_deleted=0 AND is_read=0",
        (user_id,),
    ).fetchone()
    return (r["n"] if r else 0) or 0


def category_counts(c, user_id: int) -> dict:
    rows = c.execute(
        "SELECT category, COUNT(*) AS n FROM mail_messages "
        "WHERE user_id=? AND direction='in' AND is_deleted=0 GROUP BY category",
        (user_id,),
    ).fetchall()
    return {r["category"]: r["n"] for r in rows}


# ─── 보낸 메일(발송) ────────────────────────────────────────────────
def store_outbound(c, *, user_id: int, from_email: str, to_email: str, subject: str = "",
                   body: str = "", from_name: str = "", cc: str = "", size=0):
    """발송한 메일을 보낸편지함에 기록(direction='out')."""
    cur = c.execute(
        """INSERT INTO mail_messages
           (user_id, direction, from_email, from_name, to_email, cc,
            subject, body_text, category, is_read, raw_size)
           VALUES(?,?,?,?,?,?,?,?,?,1,?)""",
        (user_id, "out", _norm_addr(from_email), (from_name or "").strip(),
         _norm_addr(to_email), (cc or "").strip(), (subject or "(제목 없음)").strip(),
         body or "", "일반", int(size or 0)),
    )
    return cur.lastrowid


def list_sent(c, user_id: int, *, limit: int = 200, offset: int = 0):
    rows = c.execute(
        """SELECT id, to_email, from_name, subject, category, received_at, is_starred,
                  substr(COALESCE(body_text,''),1,160) AS summary_short
           FROM mail_messages WHERE user_id=? AND direction='out' AND is_deleted=0
           ORDER BY received_at DESC, id DESC LIMIT ? OFFSET ?""",
        (user_id, limit, offset),
    ).fetchall()
    return [dict(r) for r in rows]


def count_sent(c, user_id: int) -> int:
    r = c.execute(
        "SELECT COUNT(*) AS n FROM mail_messages "
        "WHERE user_id=? AND direction='out' AND is_deleted=0", (user_id,),
    ).fetchone()
    return (r["n"] if r else 0) or 0


def get_mail(c, mail_id: int, user_id: int):
    """본인 메일만 조회(소유권 강제). 없으면 None."""
    r = c.execute(
        "SELECT * FROM mail_messages WHERE id=? AND user_id=? AND is_deleted=0",
        (mail_id, user_id),
    ).fetchone()
    return dict(r) if r else None


def mark_read(c, mail_id: int, user_id: int) -> None:
    c.execute(
        "UPDATE mail_messages SET is_read=1, read_at=datetime('now','localtime') "
        "WHERE id=? AND user_id=? AND is_read=0",
        (mail_id, user_id),
    )


def toggle_star(c, mail_id: int, user_id: int):
    r = c.execute("SELECT is_starred FROM mail_messages WHERE id=? AND user_id=? AND is_deleted=0",
                  (mail_id, user_id)).fetchone()
    if not r:
        return None
    new = 0 if r["is_starred"] else 1
    c.execute("UPDATE mail_messages SET is_starred=? WHERE id=? AND user_id=?",
              (new, mail_id, user_id))
    return new


def soft_delete(c, mail_id: int, user_id: int) -> bool:
    cur = c.execute(
        "UPDATE mail_messages SET is_deleted=1, deleted_at=datetime('now','localtime') "
        "WHERE id=? AND user_id=? AND is_deleted=0",
        (mail_id, user_id),
    )
    return cur.rowcount > 0


# ─── 번역(요청 시) ──────────────────────────────────────────────────
def translate_mail(c, mail_id: int, user_id: int, target: str = "ko"):
    """메일 제목·본문을 target(ko/vi/en) 으로 번역. 반환 (성공, dict|메시지)."""
    m = get_mail(c, mail_id, user_id)
    if not m:
        return (False, "메일을 찾을 수 없습니다.")
    try:
        from . import ai_client
        if not ai_client.ai_available():
            return (False, "AI 번역이 비활성 상태입니다(AI 키 미설정).")
        ok1, tsubj = ai_client.ai_translate(m.get("subject") or "", target=target)
        ok2, tbody = ai_client.ai_translate(m.get("body_text") or "", target=target)
        if not (ok1 and ok2):
            return (False, "번역 중 오류가 발생했습니다.")
        return (True, {"subject": tsubj, "body": tbody})
    except Exception as e:
        return (False, f"번역 오류: {str(e)[:80]}")


# ─── 데모(Cloudflare 없이 화면 확인용) ──────────────────────────────
_DEMO_SAMPLES = {
    "vi": dict(
        from_email="sales@khachhang-vn.com", from_name="Trần Thị B (베트남 고객사)",
        subject="Yêu cầu báo giá thiết bị kiểm tra KNK-INS-300",
        text=("Kính gửi KNK,\n\nChúng tôi muốn nhận báo giá cho 2 bộ thiết bị kiểm tra "
              "model KNK-INS-300. Số lượng: 2 bộ. Thời gian giao hàng mong muốn: tháng 8.\n"
              "Vui lòng gửi báo giá kèm điều kiện thanh toán và thời gian bảo hành.\n\n"
              "Trân trọng,\nTrần Thị B\nPhòng Mua hàng"),
    ),
    "ko": dict(
        from_email="purchasing@dreamtech.co.kr", from_name="이상우 (드림텍 구매팀)",
        subject="자동화 설비 발주의 건",
        text=("KNK 담당자님,\n\n지난 견적(견적번호 Q-2026-118) 기준으로 자동화 설비 1식을 발주합니다.\n"
              "납기는 9월 말까지 부탁드리며, 정식 발주서는 금일 중 첨부하여 다시 보내겠습니다.\n"
              "세금계산서는 납품 후 발행 부탁드립니다.\n\n감사합니다.\n드림텍 구매팀 이상우"),
    ),
}


def make_demo_mail(c, user_id: int, lang: str = "vi"):
    """사용자 본인 메일함에 샘플 메일 1건 주입(Cloudflare 없이 동작 확인용)."""
    s = _DEMO_SAMPLES.get(lang, _DEMO_SAMPLES["vi"])
    return store_inbound(
        c, to_email="test@knk-mailtest.com", owner_id=user_id, run_ai=True,
        from_email=s["from_email"], from_name=s["from_name"],
        subject=s["subject"], text=s["text"], size=len(s["text"]),
    )


# ─── 받은 메일 원문(MIME) 파싱 — Cloudflare Email Worker 가 보내는 raw 처리 ──
def _decode_part(part) -> str:
    """MIME 파트 본문을 charset 고려해 문자열로."""
    try:
        payload = part.get_payload(decode=True)
        if payload is None:
            return ""
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
    except Exception:
        try:
            return part.get_payload() or ""
        except Exception:
            return ""


def parse_raw_email(raw) -> dict:
    """raw MIME(문자열/바이트) → {from_email, from_name, to_email, subject, text, html, cc, attachments}.
    파이썬 email 모듈로 안전 파싱(멀티파트·인코딩 헤더 대응). 실패 시 {}.

    ★ 반드시 바이트로 파싱(message_from_bytes). 문자열 파싱(message_from_string)은
      인코딩되지 않은 8bit 본문(한글·베트남어 등)을 raw-unicode-escape 로 망가뜨린다
      (2026-06-13 검증으로 확증). str 입력은 UTF-8 바이트로 변환 후 파싱."""
    from email import message_from_bytes
    from email.header import decode_header, make_header
    try:
        raw_bytes = raw if isinstance(raw, (bytes, bytearray)) else (raw or "").encode("utf-8", "surrogateescape")
        msg = message_from_bytes(raw_bytes)
    except Exception:
        return {}

    def _recover8(v) -> str:
        """message_from_bytes 가 raw 8bit 헤더 바이트를 surrogateescape(U+DC80~DCFF)로
        담는 경우 UTF-8 로 복구(비표준 메일 견고성). 정상 RFC2047 헤더는 영향 없음.
        Header 객체 등 str 이 아닌 입력도 안전 처리(절대 예외 X)."""
        try:
            if not isinstance(v, str):
                v = str(v)
        except Exception:
            return ""
        if v and any("\udc80" <= ch <= "\udcff" for ch in v):
            try:
                return v.encode("utf-8", "surrogateescape").decode("utf-8", "replace")
            except Exception:
                return v
        return v

    def _h(name: str) -> str:
        v = _recover8(msg.get(name, "") or "")
        try:
            return str(make_header(decode_header(v)))
        except Exception:
            return v

    subject = _h("Subject")
    from_name, from_addr = parseaddr(_h("From"))
    to_addr = parseaddr(_h("To"))[1] or _h("To")
    cc = _h("Cc")

    text, html, atts = "", "", []
    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue
            ctype = (part.get_content_type() or "").lower()
            disp = str(part.get("Content-Disposition") or "").lower()
            fname = part.get_filename()
            cid = (part.get("Content-ID") or "").strip().strip("<>").strip()
            # 첨부/인라인 판정: 파일명 있음 · disposition attachment/inline · 이미지+Content-ID
            is_att = bool(fname) or ("attachment" in disp) or ("inline" in disp) \
                or (cid and ctype.startswith("image/"))
            if is_att:
                fn = _recover8(fname) if fname else ""
                if fn:
                    try:
                        fn = str(make_header(decode_header(fn)))
                    except Exception:
                        pass
                try:
                    data = part.get_payload(decode=True) or b""
                except Exception:
                    data = b""
                atts.append({
                    "filename": fn or (cid or "image"),
                    "mime": ctype or "application/octet-stream",
                    "size": len(data),
                    "content_id": cid,
                    "inline": 1 if (("inline" in disp) or (cid and not fn)
                                    or (cid and ctype.startswith("image/"))) else 0,
                    "data": data,
                })
                continue
            if ctype == "text/plain" and not text:
                text = _decode_part(part)
            elif ctype == "text/html" and not html:
                html = _decode_part(part)
    else:
        if (msg.get_content_type() or "").lower() == "text/html":
            html = _decode_part(msg)
        else:
            text = _decode_part(msg)

    body = text or _html_to_text(html)
    # 텍스트 본문 끝에는 '진짜 첨부'(인라인 서명이미지 제외)만 표기
    real_atts = [a for a in atts if not a.get("inline")]
    if real_atts:
        body = (body or "").rstrip() + f"\n\n[첨부 {len(real_atts)}개: " \
            + ", ".join(a["filename"] for a in real_atts[:10]) + "]"
    return {
        "from_email": from_addr, "from_name": from_name, "to_email": to_addr,
        "subject": subject, "text": body, "html": html, "cc": cc, "attachments": atts,
    }


# ─── 첨부 저장·조회 + 안전 HTML 렌더(원본처럼 보이기) ────────────────
# 첨부 바이트는 POC 단계에서 DB(mail_attachments.data)에 보관. 상한 초과분은 메타만.
_ATT_STORE_MAX = 12 * 1024 * 1024   # 12MB/건


def _save_attachments(c, mail_id: int, attachments) -> None:
    """파싱된 첨부 리스트를 mail_attachments 에 저장(인라인 이미지 포함)."""
    for a in (attachments or []):
        try:
            data = a.get("data") or b""
            store = data if (data and len(data) <= _ATT_STORE_MAX) else None
            c.execute(
                """INSERT INTO mail_attachments
                   (mail_id, filename, mime, size, content_id, is_inline, data)
                   VALUES(?,?,?,?,?,?,?)""",
                (mail_id, (a.get("filename") or "")[:255], (a.get("mime") or "")[:120],
                 int(a.get("size") or 0), (a.get("content_id") or "")[:255],
                 1 if a.get("inline") else 0, store),
            )
        except Exception:
            # 데이터 연결성: 첨부 1건 실패가 메일 저장을 막지 않게(메일은 이미 저장됨)
            pass


def list_attachments(c, mail_id: int, *, inline=None):
    """메일의 첨부 목록(바이트 제외 메타). inline=True/False 로 인라인/일반 필터."""
    where = "mail_id=?"
    args = [mail_id]
    if inline is not None:
        where += " AND is_inline=?"
        args.append(1 if inline else 0)
    rows = c.execute(
        f"SELECT id, filename, mime, size, content_id, is_inline "
        f"FROM mail_attachments WHERE {where} ORDER BY id", args,
    ).fetchall()
    return [dict(r) for r in rows]


def get_attachment(c, att_id: int, user_id: int):
    """첨부 1건의 바이트(소유권 강제: 메일 소유자만). 없거나 미보관이면 None."""
    r = c.execute(
        "SELECT a.filename, a.mime, a.data FROM mail_attachments a "
        "JOIN mail_messages m ON m.id = a.mail_id "
        "WHERE a.id=? AND m.user_id=? AND m.is_deleted=0",
        (att_id, user_id),
    ).fetchone()
    if not r or r["data"] is None:
        return None
    return {"filename": r["filename"] or "attachment",
            "mime": r["mime"] or "application/octet-stream", "data": r["data"]}


def sanitize_html_for_view(html: str, mail_id: int, inline_atts) -> str:
    """받은 메일 HTML 을 '격리 iframe' 안에서 보여줄 안전 HTML 로 정리.
    - 스크립트/폼/임베드 등 위험 태그 제거, on* 이벤트·javascript: 스킴 제거.
    - 인라인 이미지(src="cid:...")는 우리 서버(/mail/{id}/att/{att_id})로 치환 → 서명 로고 표시.
    - 최종은 sandbox iframe 에 넣으므로(스크립트 실행 불가) 이중 안전.
    원격 이미지(http(s))는 원본 충실도를 위해 허용(내부 업무용)."""
    if not html:
        return ""
    s = html
    # 위험 쌍태그 통째 제거
    s = re.sub(r"(?is)<\s*(script|style|iframe|object|embed|form|noscript|svg|math)\b.*?<\s*/\s*\1\s*>", " ", s)
    # 위험 단독/잔여 태그 제거
    s = re.sub(r"(?is)<\s*/?\s*(script|style|iframe|object|embed|form|noscript|meta|base|link|input|button|textarea|select|svg|math)\b[^>]*>", " ", s)
    # on... 이벤트 핸들러 속성 제거
    s = re.sub(r"(?is)\son[a-z]+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", " ", s)
    # href/src 의 javascript: 스킴 무력화
    s = re.sub(r"(?is)(href|src)\s*=\s*([\"'])\s*javascript:[^\"']*\2", r'\1=\2#\2', s)
    # cid: 인라인 이미지 → 우리 서버 URL 로 치환
    cid_map = {(a.get("content_id") or "").lower(): a["id"]
               for a in (inline_atts or []) if a.get("content_id")}

    def _cid_sub(m):
        q, cid = m.group(1), m.group(2).strip().lower()
        aid = cid_map.get(cid)
        return f'src={q}/mail/{mail_id}/att/{aid}{q}' if aid else f'src={q}#{q}'

    s = re.sub(r"(?is)src\s*=\s*([\"'])\s*cid:([^\"']+)\1", _cid_sub, s)
    return s
