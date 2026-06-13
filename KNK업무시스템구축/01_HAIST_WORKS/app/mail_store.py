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
    """수신자 미지정 시 기본 소유자 — 대표 김정락(kjr) → 이름 → role=ceo 순."""
    for sql in (
        "SELECT id FROM users WHERE username='kjr' AND is_active=1",
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
                  size=0, owner_id=None, run_ai: bool = True):
    """받은 메일 1건 저장. 반환 (mail_id, owner_id).
    owner_id 미지정 시 to_email 로 수신자 해석. 수신자 없으면 (None, None)."""
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
    return (cur.lastrowid, owner)


# ─── 조회 ───────────────────────────────────────────────────────────
def list_inbox(c, user_id: int, *, category: str = "", limit: int = 200, offset: int = 0):
    where = "user_id=? AND is_deleted=0"
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
        "SELECT COUNT(*) AS n FROM mail_messages WHERE user_id=? AND is_deleted=0 AND is_read=0",
        (user_id,),
    ).fetchone()
    return (r["n"] if r else 0) or 0


def category_counts(c, user_id: int) -> dict:
    rows = c.execute(
        "SELECT category, COUNT(*) AS n FROM mail_messages "
        "WHERE user_id=? AND is_deleted=0 GROUP BY category",
        (user_id,),
    ).fetchall()
    return {r["category"]: r["n"] for r in rows}


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


def parse_raw_email(raw: str) -> dict:
    """raw MIME 문자열 → {from_email, from_name, to_email, subject, text, html, cc, attachments}.
    파이썬 email 모듈로 안전 파싱(멀티파트·인코딩 헤더 대응). 실패 시 {}."""
    from email import message_from_string
    from email.header import decode_header, make_header
    try:
        msg = message_from_string(raw or "")
    except Exception:
        return {}

    def _h(name: str) -> str:
        v = msg.get(name, "") or ""
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
            if "attachment" in disp or fname:
                if fname:
                    try:
                        atts.append(str(make_header(decode_header(fname))))
                    except Exception:
                        atts.append(fname)
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
    if atts:
        body = (body or "").rstrip() + f"\n\n[첨부 {len(atts)}개: " + ", ".join(atts[:10]) + "]"
    return {
        "from_email": from_addr, "from_name": from_name, "to_email": to_addr,
        "subject": subject, "text": body, "html": html, "cc": cc, "attachments": atts,
    }
