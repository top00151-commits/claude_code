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

import os
import re
import json
import secrets
import hashlib
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
# ─── 중복 메일 자동정리 (Message-ID 기반 · 데이터 안전: 진짜 같은 메일만) ───
# 여러 그룹메일에 포함돼 같은 메일이 N번 들어오는 중복을 안전하게 합친다.
# 키 = Message-ID(있으면 그것만, 가장 정확) / 없으면 보낸이+제목+본문 완전일치 해시.
# 제목만 같은 답장 스레드는 본문이 달라 해시가 달라짐 → 절대 안 묶임(연결성 안전 원칙).
_DEDUP_COLS_OK = False


def _ensure_dedup_cols(c):
    """mail_messages 에 dedup_hash·dup_count 컬럼/인덱스 보장(idempotent, 프로세스당 1회)."""
    global _DEDUP_COLS_OK
    if _DEDUP_COLS_OK:
        return
    for ddl in ("ALTER TABLE mail_messages ADD COLUMN dedup_hash TEXT",
                "ALTER TABLE mail_messages ADD COLUMN dup_count INTEGER DEFAULT 1"):
        try:
            c.execute(ddl)
        except Exception:
            pass
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_mailmsg_dedup ON mail_messages(user_id, dedup_hash)")
    except Exception:
        pass
    _DEDUP_COLS_OK = True


def _dedup_hash(message_id, from_email, subject, body) -> str:
    """'같은 메일' 식별 해시. Message-ID 있으면 그것만, 없으면 보낸이+제목+본문 완전일치."""
    mid = str(message_id or "").strip().strip("<>").strip()
    if mid:
        key = "mid:" + mid
    else:
        key = "c:" + _norm_addr(from_email) + "\x00" + (subject or "").strip() + "\x00" + (body or "").strip()
    return hashlib.sha1(key.encode("utf-8", "replace")).hexdigest()


# ── 스팸·피싱 방어 (대표 지시 2026-06-19): 차단목록 + 규칙기반 위험판별 ──
_SEC_COLS_OK = False
_OUR_DOMAINS = ("knknara.co.kr",)
DANGEROUS_EXTS = {".exe", ".scr", ".com", ".pif", ".bat", ".cmd", ".vbs", ".vbe", ".js",
                  ".jse", ".jar", ".lnk", ".msi", ".reg", ".ps1", ".wsf", ".hta", ".cpl",
                  ".scf", ".inf", ".chm", ".iso", ".img", ".vhd"}


def _ensure_security_cols(c):
    global _SEC_COLS_OK
    if _SEC_COLS_OK:
        return
    for ddl in ("ALTER TABLE mail_messages ADD COLUMN is_blocked INTEGER DEFAULT 0",
                "ALTER TABLE mail_messages ADD COLUMN risk_level INTEGER DEFAULT 0",
                "ALTER TABLE mail_messages ADD COLUMN risk_note TEXT"):
        try:
            c.execute(ddl)
        except Exception:
            pass
    try:
        c.execute("""CREATE TABLE IF NOT EXISTS mail_blocklist(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern TEXT UNIQUE, kind TEXT DEFAULT 'email',
            note TEXT, created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime')))""")
    except Exception:
        pass
    _SEC_COLS_OK = True


def _att_ext(filename) -> str:
    fn = (filename or "").strip().lower()
    return ("." + fn.rsplit(".", 1)[-1]) if "." in fn else ""


def is_sender_blocked(c, from_email) -> bool:
    """차단목록(이메일 정확일치 또는 도메인/서브도메인)에 걸리면 True."""
    addr = _norm_addr(from_email)
    if not addr:
        return False
    dom = addr.split("@")[-1] if "@" in addr else ""
    try:
        _ensure_security_cols(c)
        rows = c.execute("SELECT pattern, kind FROM mail_blocklist").fetchall()
    except Exception:
        return False
    for r in rows:
        pat = (r["pattern"] or "").strip().lower()
        if not pat:
            continue
        if r["kind"] == "domain":
            if dom == pat or dom.endswith("." + pat):
                return True
        elif addr == pat:
            return True
    return False


def add_block(c, pattern, kind="email", note="", by=None) -> bool:
    _ensure_security_cols(c)
    pat = (pattern or "").strip().lower()
    if kind == "domain":
        pat = pat.lstrip("@")
    if not pat or "." not in pat:
        return False
    try:
        c.execute("INSERT OR IGNORE INTO mail_blocklist(pattern,kind,note,created_by) VALUES(?,?,?,?)",
                  (pat, "domain" if kind == "domain" else "email", (note or "").strip(), by))
        return True
    except Exception:
        return False


def remove_block(c, block_id) -> None:
    _ensure_security_cols(c)
    try:
        c.execute("DELETE FROM mail_blocklist WHERE id=?", (block_id,))
    except Exception:
        pass


def list_blocks(c):
    _ensure_security_cols(c)
    try:
        return [dict(r) for r in c.execute(
            "SELECT * FROM mail_blocklist ORDER BY kind, pattern").fetchall()]
    except Exception:
        return []


_PHISH_KW = ("비밀번호", "암호", "계정", "본인확인", "인증", "정지", "차단", "송장", "청구",
             "결제", "환불", "긴급", "즉시", "invoice", "verify", "account", "password",
             "suspend", "urgent", "confirm", "payment", "refund", "login", "secur")


def assess_risk(from_email, to_email="", subject="", body="", html="", attachments=None):
    """규칙기반 위험판별(AI 아님·무료·빠름). 반환 (level 0~3, note문자열).
    3=실행파일 첨부 / 2=외부발신+의심링크+피싱문구 / 1=외부발신 / 0=내부·안전."""
    notes = []
    addr = _norm_addr(from_email)
    dom = addr.split("@")[-1] if "@" in addr else ""
    external = bool(dom) and not any(dom == d or dom.endswith("." + d) for d in _OUR_DOMAINS)
    level = 0
    danger = [a.get("filename") for a in (attachments or [])
              if _att_ext(a.get("filename")) in DANGEROUS_EXTS]
    if danger:
        level = 3
        notes.append("실행파일 첨부(" + ", ".join([d for d in danger if d][:3]) + ")")
    blob = ((subject or "") + " " + (body or "")).lower()
    _h = (html or "").lower()
    _b = (body or "").lower()
    has_link = ("http://" in _h or "https://" in _h or "http://" in _b or "https://" in _b)
    if external and has_link and any(k in blob for k in _PHISH_KW):
        level = max(level, 2)
        notes.append("외부 발신 + 의심 링크·문구(피싱 가능)")
    elif external:
        level = max(level, 1)
        notes.append("외부 발신")
    return level, " / ".join(notes)


def store_inbound(c, *, to_email: str, from_email: str = "", from_name: str = "",
                  subject: str = "", text: str = "", html: str = "", cc: str = "",
                  size=0, owner_id=None, run_ai: bool = True, attachments=None,
                  message_id: str = ""):
    """받은 메일 1건 저장. 반환 (mail_id, owner_id).
    owner_id 미지정 시 to_email 로 수신자 해석. 수신자 없으면 (None, None).
    attachments: parse_raw_email 이 만든 [{filename,mime,size,content_id,inline,data}, ...]."""
    owner = owner_id or resolve_recipient(c, to_email)
    if not owner:
        return (None, None)
    subject = (subject or "(제목 없음)").strip()
    body = (text or "").strip() or _html_to_text(html)
    # ── 중복 메일 자동정리: 같은 메일(고유번호/내용 완전일치)이 이미 있으면 새로 안 쌓고 dup_count++ ──
    _ensure_dedup_cols(c)
    _dh = _dedup_hash(message_id, from_email, subject, body)
    try:
        _dup = c.execute(
            "SELECT id FROM mail_messages WHERE user_id=? AND direction='in' "
            "AND is_deleted=0 AND dedup_hash=? ORDER BY id LIMIT 1", (owner, _dh)).fetchone()
    except Exception:
        _dup = None
    if _dup:
        try:
            c.execute("UPDATE mail_messages SET dup_count=COALESCE(dup_count,1)+1 WHERE id=?", (_dup["id"],))
        except Exception:
            pass
        return (_dup["id"], owner)   # 중복 — 새로 저장하지 않음(남은 1통에 N 표시)
    category, lang, summary = "일반", "", ""
    if run_ai:
        category, lang = _ai_classify(subject, body)
        summary = _ai_summary(body)
    # 사용자 자동분류 규칙이 일치하면 AI 결과를 덮어씀(명시 의도 우선)
    try:
        _rcat = match_rules(c, owner, from_email, from_name, subject)
        if _rcat:
            category = _rcat
    except Exception:
        pass
    try:
        sz = int(size or 0)
    except Exception:
        sz = 0
    # 보안: 차단목록 격리 + 규칙기반 위험판별 (대표 지시 2026-06-19)
    _ensure_security_cols(c)
    _blocked = 1 if is_sender_blocked(c, from_email) else 0
    _rlevel, _rnote = assess_risk(from_email, to_email, subject, body, html, attachments)
    cur = c.execute(
        """INSERT INTO mail_messages
           (user_id, direction, from_email, from_name, to_email, cc,
            subject, body_text, body_html, category, lang, summary, raw_size,
            dedup_hash, dup_count, is_blocked, risk_level, risk_note)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (owner, "in", _norm_addr(from_email), (from_name or "").strip(),
         _norm_addr(to_email), (cc or "").strip(), subject, body, html or "",
         category, lang, summary, sz, _dh, 1, _blocked, _rlevel, _rnote),
    )
    mail_id = cur.lastrowid
    if attachments:
        _save_attachments(c, mail_id, attachments)
    return (mail_id, owner)


def dedup_inbox(c, user_id: int) -> int:
    """받은편지함의 '진짜 같은 메일' 중복을 1통만 남기고 나머지를 휴지통으로(소프트삭제).
    읽음/별표는 그룹에 하나라도 있으면 보존, 남긴 메일에 dup_count 기록. 반환=정리한 통수.
    답장 스레드(제목만 같고 본문 다름)는 해시가 달라 절대 안 건드림."""
    _ensure_dedup_cols(c)
    # 과거 메일 dedup_hash 백필(예전엔 Message-ID 미저장 → 보낸이+제목+본문 기준)
    try:
        for r in c.execute(
                "SELECT id, from_email, subject, body_text FROM mail_messages "
                "WHERE user_id=? AND direction='in' AND (dedup_hash IS NULL OR dedup_hash='')",
                (user_id,)).fetchall():
            c.execute("UPDATE mail_messages SET dedup_hash=? WHERE id=?",
                      (_dedup_hash("", r["from_email"], r["subject"], r["body_text"]), r["id"]))
    except Exception:
        return 0
    removed = 0
    groups = c.execute(
        "SELECT dedup_hash FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 "
        "AND dedup_hash IS NOT NULL AND dedup_hash<>'' GROUP BY dedup_hash HAVING COUNT(*)>1",
        (user_id,)).fetchall()
    for g in groups:
        grp = c.execute(
            "SELECT id, is_read, is_starred FROM mail_messages WHERE user_id=? AND direction='in' "
            "AND is_deleted=0 AND dedup_hash=? ORDER BY id", (user_id, g["dedup_hash"])).fetchall()
        if len(grp) < 2:
            continue
        any_read = 1 if any(x["is_read"] for x in grp) else 0
        any_star = 1 if any(x["is_starred"] for x in grp) else 0
        c.execute("UPDATE mail_messages SET is_read=?, is_starred=?, dup_count=? WHERE id=?",
                  (any_read, any_star, len(grp), grp[0]["id"]))
        for x in grp[1:]:
            c.execute("UPDATE mail_messages SET is_deleted=1, deleted_at=datetime('now','localtime') "
                      "WHERE id=?", (x["id"],))
            removed += 1
    return removed


# ─── 자동분류 규칙 (사용자별) ────────────────────────────────────────
# 보낸사람(이메일/도메인/이름) 또는 제목 키워드가 포함되면 그 카테고리로 강제 분류.
# 받은 메일 저장 시 AI 분류 결과를 사용자 규칙이 '덮어쓰기'(명시 의도 우선).
def _ensure_rules(c):
    c.execute("""CREATE TABLE IF NOT EXISTS mail_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        match_type TEXT NOT NULL,
        pattern TEXT NOT NULL,
        category TEXT NOT NULL,
        enabled INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )""")


def list_rules(c, user_id: int):
    _ensure_rules(c)
    rows = c.execute("SELECT * FROM mail_rules WHERE user_id=? ORDER BY id", (user_id,)).fetchall()
    return [dict(r) for r in rows]


def add_rule(c, user_id: int, match_type: str, pattern: str, category: str):
    _ensure_rules(c)
    match_type = match_type if match_type in ("sender", "subject") else "sender"
    pattern = (pattern or "").strip()
    category = category if category in CATEGORIES else "일반"
    if not pattern:
        return None
    cur = c.execute("INSERT INTO mail_rules(user_id, match_type, pattern, category) VALUES(?,?,?,?)",
                    (user_id, match_type, pattern[:120], category))
    return cur.lastrowid


def delete_rule(c, rule_id: int, user_id: int):
    _ensure_rules(c)
    c.execute("DELETE FROM mail_rules WHERE id=? AND user_id=?", (rule_id, user_id))


def match_rules(c, user_id: int, from_email: str = "", from_name: str = "", subject: str = ""):
    """첫 일치 규칙의 카테고리 반환(없으면 None). 보낸사람=이메일/이름 부분일치, 제목=키워드 부분일치."""
    try:
        _ensure_rules(c)
        rules = c.execute("SELECT match_type, pattern, category FROM mail_rules "
                          "WHERE user_id=? AND enabled=1 ORDER BY id", (user_id,)).fetchall()
    except Exception:
        return None
    sender_hay = (from_email or "").lower() + " " + (from_name or "").lower()
    subj = (subject or "").lower()
    for r in rules:
        pat = (r["pattern"] or "").lower().strip()
        if not pat:
            continue
        if r["match_type"] == "sender" and pat in sender_hay:
            return r["category"]
        if r["match_type"] == "subject" and pat in subj:
            return r["category"]
    return None


def apply_rules_existing(c, user_id: int) -> int:
    """기존 받은편지함 메일에 규칙 소급 적용 — 카테고리 갱신. 변경 건수 반환."""
    _ensure_rules(c)
    rows = c.execute("SELECT id, from_email, from_name, subject, category FROM mail_messages "
                     "WHERE user_id=? AND direction='in' AND is_deleted=0", (user_id,)).fetchall()
    changed = 0
    for m in rows:
        newcat = match_rules(c, user_id, m["from_email"], m["from_name"], m["subject"])
        if newcat and newcat != m["category"]:
            c.execute("UPDATE mail_messages SET category=? WHERE id=?", (newcat, m["id"]))
            changed += 1
    return changed


# ─── 조회 ───────────────────────────────────────────────────────────
def list_inbox(c, user_id: int, *, category: str = "", q: str = "",
               starred=None, unread=None, date_from: str = "", date_to: str = "",
               has_att=None, cust: str = "", limit: int = 200, offset: int = 0):
    _ensure_security_cols(c)
    where = "user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0"
    args = [user_id]
    if category and category in CATEGORIES:
        where += " AND category=?"
        args.append(category)
    if starred:
        where += " AND is_starred=1"
    if unread:
        where += " AND is_read=0"
    # 날짜 범위(받은시각) — received_at 은 'YYYY-MM-DD HH:MM…' 정렬가능 문자열이라 문자열 비교로 충분
    date_from = (date_from or "").strip()
    date_to = (date_to or "").strip()
    if date_from:
        where += " AND received_at >= ?"
        args.append(date_from + " 00:00")
    if date_to:
        where += " AND received_at <= ?"
        args.append(date_to + " 23:59:59")
    # 첨부(일반 파일) 있는 메일만 — 인라인 이미지 제외
    if has_att:
        where += (" AND EXISTS(SELECT 1 FROM mail_attachments a "
                  "WHERE a.mail_id=mail_messages.id AND COALESCE(a.is_inline,0)=0)")
    # C1 거래처 폴더 — 보낸사람 이메일 정확일치(소문자)로만 거래처 매핑(추측 금지). cust='none'=미분류.
    cust = (cust or "").strip()
    if cust == "none":
        where += (" AND NOT EXISTS(SELECT 1 FROM shared_contacts sc "
                  "WHERE sc.email IS NOT NULL AND lower(sc.email)=lower(mail_messages.from_email) "
                  "AND sc.customer_id IS NOT NULL)")
    elif cust.isdigit():
        where += (" AND EXISTS(SELECT 1 FROM shared_contacts sc "
                  "WHERE sc.email IS NOT NULL AND lower(sc.email)=lower(mail_messages.from_email) "
                  "AND sc.customer_id=?)")
        args.append(int(cust))
    q = (q or "").strip()
    if q:
        where += " AND (from_email LIKE ? OR from_name LIKE ? OR subject LIKE ? OR body_text LIKE ?)"
        like = f"%{q}%"
        args += [like, like, like, like]
    rows = c.execute(
        f"""SELECT id, from_email, from_name, subject, category, lang,
                   is_read, is_starred, received_at, COALESCE(risk_level,0) AS risk_level,
                   substr(COALESCE(summary,''),1,160) AS summary_short
            FROM mail_messages WHERE {where}
            ORDER BY received_at DESC, id DESC LIMIT ? OFFSET ?""",
        (*args, limit, offset),
    ).fetchall()
    return [dict(r) for r in rows]


# ── 대화 묶기(스레드) — 같은 제목(RE/FW 접두 제거)으로 받은 메일을 한 대화로 (B1, 2026-06-14) ──
_SUBJ_PREFIX_RE = re.compile(r"^\s*(re|회신|답장|답신|fwd?|fw|전달)\s*[:：]\s*", re.IGNORECASE)


def _normalize_subject(s: str) -> str:
    """제목 앞의 RE:/FW:/회신:/답장: 등 반복 접두를 모두 제거해 '대화 식별 키' 생성.
    (그룹핑 전용 — 화면 표시는 대표 메일의 원본 제목을 쓴다.)"""
    s = (s or "").strip()
    prev = None
    while s and s != prev:          # 중첩(RE: RE: FW:) 반복 제거
        prev = s
        s = _SUBJ_PREFIX_RE.sub("", s, count=1).strip()
    s = re.sub(r"\s+", " ", s).strip()
    return s.lower() if s else "(제목 없음)"


def group_threads(mails: list) -> list:
    """list_inbox() 결과(받은시각 내림차순)를 같은 제목 대화로 묶는다.
    반환: [{key, latest(대표=최신), count, unread_count, items(최신순)}] — 그룹은 최신 대화 먼저.
    입력이 이미 내림차순이라 키 첫 등장 = 그 대화의 최신 → 그룹 순서가 자연히 최신순."""
    order, groups = [], {}
    for m in mails:
        key = _normalize_subject(m.get("subject"))
        g = groups.get(key)
        if g is None:
            g = {"key": key, "latest": m, "count": 0, "unread_count": 0, "items": []}
            groups[key] = g
            order.append(key)
        g["items"].append(m)
        g["count"] += 1
        if not m.get("is_read"):
            g["unread_count"] += 1
    return [groups[k] for k in order]


def customer_folder_counts(c, user_id: int) -> dict:
    """받은편지함을 보낸사람→연락처→거래처 매핑으로 거래처별 집계 (C1 폴더, 2026-06-14).
    매핑은 이메일 '정확일치(소문자)'만 — 추측 금지([[feedback-data-connectivity]]). 미매핑=미분류.
    반환: {total, total_unread, unclassified, unclassified_unread, customers:[{id,name,cnt,unread}]}."""
    base_args = (user_id,)
    tot = c.execute(
        "SELECT COUNT(*) AS n, SUM(CASE WHEN is_read=0 THEN 1 ELSE 0 END) AS u "
        "FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0",
        base_args).fetchone()
    rows = c.execute(
        """SELECT cu.id AS id, cu.name AS name,
                  COUNT(DISTINCT m.id) AS cnt,
                  COUNT(DISTINCT CASE WHEN m.is_read=0 THEN m.id END) AS unread
           FROM mail_messages m
           JOIN shared_contacts sc ON sc.email IS NOT NULL
                AND lower(sc.email)=lower(m.from_email) AND sc.customer_id IS NOT NULL
           JOIN customers cu ON cu.id=sc.customer_id
           WHERE m.user_id=? AND m.direction='in' AND m.is_deleted=0
           GROUP BY cu.id, cu.name
           ORDER BY cnt DESC, cu.name""",
        base_args).fetchall()
    unc = c.execute(
        """SELECT COUNT(*) AS n, SUM(CASE WHEN is_read=0 THEN 1 ELSE 0 END) AS u
           FROM mail_messages m
           WHERE m.user_id=? AND m.direction='in' AND m.is_deleted=0
             AND NOT EXISTS(SELECT 1 FROM shared_contacts sc
                  WHERE sc.email IS NOT NULL AND lower(sc.email)=lower(m.from_email)
                    AND sc.customer_id IS NOT NULL)""",
        base_args).fetchone()
    return {
        "total": (tot["n"] or 0) if tot else 0,
        "total_unread": (tot["u"] or 0) if tot else 0,
        "unclassified": (unc["n"] or 0) if unc else 0,
        "unclassified_unread": (unc["u"] or 0) if unc else 0,
        "customers": [dict(r) for r in rows],
    }


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
                   body: str = "", from_name: str = "", cc: str = "", bcc: str = "",
                   body_html: str = "", size=0):
    """발송한 메일을 보낸편지함에 기록(direction='out')."""
    cur = c.execute(
        """INSERT INTO mail_messages
           (user_id, direction, from_email, from_name, to_email, cc, bcc,
            subject, body_text, body_html, category, is_read, raw_size)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,1,?)""",
        (user_id, "out", _norm_addr(from_email), (from_name or "").strip(),
         _norm_addr(to_email), (cc or "").strip(), (bcc or "").strip(),
         (subject or "(제목 없음)").strip(), body or "", body_html or "", "일반", int(size or 0)),
    )
    return cur.lastrowid


# ─── 읽음 수동 표시 + 임시저장(Drafts) — 아웃룩 편의기능 ─────────────
def set_read(c, mail_id: int, user_id: int, read: bool = True) -> None:
    c.execute(
        "UPDATE mail_messages SET is_read=?, "
        "read_at=CASE WHEN ?=1 THEN datetime('now','localtime') ELSE NULL END "
        "WHERE id=? AND user_id=?",
        (1 if read else 0, 1 if read else 0, mail_id, user_id),
    )


def save_draft(c, *, user_id: int, draft_id=None, to_email: str = "", cc: str = "",
               bcc: str = "", subject: str = "", body: str = "", body_html: str = ""):
    """임시저장(direction='draft'). draft_id 있으면 갱신, 없으면 신규. 반환 draft_id."""
    subj = (subject or "(제목 없음)").strip()
    if draft_id:
        cur = c.execute(
            "UPDATE mail_messages SET to_email=?, cc=?, bcc=?, subject=?, body_text=?, "
            "body_html=?, received_at=datetime('now','localtime') "
            "WHERE id=? AND user_id=? AND direction='draft'",
            (to_email, cc, bcc, subj, body, body_html or "", draft_id, user_id))
        if cur.rowcount:
            return draft_id
    cur = c.execute(
        "INSERT INTO mail_messages(user_id, direction, to_email, cc, bcc, subject, "
        "body_text, body_html, is_read) VALUES(?,?,?,?,?,?,?,?,1)",
        (user_id, "draft", to_email, cc, bcc, subj, body, body_html or ""))
    return cur.lastrowid


def list_drafts(c, user_id: int):
    rows = c.execute(
        "SELECT id, to_email, subject, received_at, "
        "substr(COALESCE(body_text,''),1,160) AS summary_short "
        "FROM mail_messages WHERE user_id=? AND direction='draft' AND is_deleted=0 "
        "ORDER BY received_at DESC, id DESC LIMIT 200", (user_id,)).fetchall()
    return [dict(r) for r in rows]


def count_drafts(c, user_id: int) -> int:
    r = c.execute("SELECT COUNT(*) AS n FROM mail_messages "
                  "WHERE user_id=? AND direction='draft' AND is_deleted=0", (user_id,)).fetchone()
    return (r["n"] if r else 0) or 0


def get_draft(c, draft_id: int, user_id: int):
    r = c.execute("SELECT * FROM mail_messages WHERE id=? AND user_id=? "
                  "AND direction='draft' AND is_deleted=0", (draft_id, user_id)).fetchone()
    return dict(r) if r else None


def delete_draft(c, draft_id: int, user_id: int) -> None:
    c.execute("DELETE FROM mail_messages WHERE id=? AND user_id=? AND direction='draft'",
              (draft_id, user_id))


def list_sent(c, user_id: int, *, q: str = "", limit: int = 200, offset: int = 0):
    where = "user_id=? AND direction='out' AND is_deleted=0"
    args = [user_id]
    q = (q or "").strip()
    if q:
        where += " AND (to_email LIKE ? OR subject LIKE ? OR body_text LIKE ?)"
        like = f"%{q}%"
        args += [like, like, like]
    rows = c.execute(
        f"""SELECT id, to_email, from_name, subject, category, received_at, is_starred,
                  substr(COALESCE(body_text,''),1,160) AS summary_short
           FROM mail_messages WHERE {where}
           ORDER BY received_at DESC, id DESC LIMIT ? OFFSET ?""",
        (*args, limit, offset),
    ).fetchall()
    return [dict(r) for r in rows]


# ─── 편의: 서명 · 연락처 자동완성 (2026-06-13 대표 지시) ─────────────
def get_signature(c, user_id: int) -> str:
    r = c.execute("SELECT body FROM mail_signatures WHERE user_id=?", (user_id,)).fetchone()
    return (r["body"] if r else "") or ""


def save_signature(c, user_id: int, body: str) -> None:
    c.execute(
        "INSERT INTO mail_signatures(user_id, body, updated_at) "
        "VALUES(?,?,datetime('now','localtime')) "
        "ON CONFLICT(user_id) DO UPDATE SET body=excluded.body, updated_at=excluded.updated_at",
        (user_id, (body or "").strip()),
    )


def search_contacts(c, q: str, limit: int = 8):
    """전사 연락처(shared_contacts)에서 받는사람 자동완성 후보."""
    q = (q or "").strip()
    if not q:
        return []
    like = f"%{q}%"
    try:
        rows = c.execute(
            """SELECT name, email, company, position FROM shared_contacts
               WHERE email IS NOT NULL AND email<>''
                 AND (name LIKE ? OR email LIKE ? OR company LIKE ?)
               ORDER BY name LIMIT ?""",
            (like, like, like, int(limit) * 3),
        ).fetchall()
    except Exception:
        return []
    out, seen = [], set()
    for r in rows:
        em = (r["email"] or "").strip()
        if not em or em.lower() in seen:
            continue
        seen.add(em.lower())
        out.append({"name": r["name"] or "", "email": em,
                    "company": r["company"] or "", "position": r["position"] or ""})
        if len(out) >= limit:
            break
    return out


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


# ─── 휴지통 · 완전삭제(서버에서 진짜 제거) · 오래된 메일 일괄정리 (대표 지시 2026-06-14) ───
#   soft_delete 는 숨김(is_deleted=1)만 — DB·첨부는 NAS에 잔존. 아래는 '진짜 삭제'.
#   첨부는 FK ON DELETE CASCADE 지만 PRAGMA foreign_keys 미보장 → 명시적 DELETE 로 확실히 제거.
def list_blocked(c, user_id: int, *, limit: int = 300):
    """차단함 — 차단목록에 걸려 격리된 받은 메일(삭제 아님·복구 가능)."""
    _ensure_security_cols(c)
    rows = c.execute(
        """SELECT id, from_email, from_name, subject, category, received_at,
                  substr(COALESCE(summary,''),1,160) AS summary_short
           FROM mail_messages
           WHERE user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=1
           ORDER BY received_at DESC, id DESC LIMIT ?""", (user_id, limit)).fetchall()
    return [dict(r) for r in rows]


def count_blocked(c, user_id: int) -> int:
    _ensure_security_cols(c)
    try:
        return c.execute(
            "SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND direction='in' "
            "AND is_deleted=0 AND COALESCE(is_blocked,0)=1", (user_id,)).fetchone()[0]
    except Exception:
        return 0


def set_blocked(c, user_id, mail_id, blocked) -> None:
    """개별 메일 차단함 이동(1)/받은편지함 복구(0). 본인 메일만."""
    _ensure_security_cols(c)
    c.execute("UPDATE mail_messages SET is_blocked=? WHERE id=? AND user_id=? AND direction='in'",
              (1 if blocked else 0, mail_id, user_id))


def apply_block_to_existing(c, pattern, kind) -> int:
    """차단목록 추가 시 기존 받은 메일도 소급 차단함 이동. 반환 옮긴 건수."""
    _ensure_security_cols(c)
    pat = (pattern or "").strip().lower()
    if not pat:
        return 0
    if kind == "domain":
        cur = c.execute(
            "UPDATE mail_messages SET is_blocked=1 WHERE direction='in' AND is_deleted=0 "
            "AND COALESCE(is_blocked,0)=0 AND (lower(from_email) LIKE ? OR lower(from_email) LIKE ?)",
            ("%@" + pat, "%." + pat))
    else:
        cur = c.execute(
            "UPDATE mail_messages SET is_blocked=1 WHERE direction='in' AND is_deleted=0 "
            "AND COALESCE(is_blocked,0)=0 AND lower(from_email)=?", (pat,))
    return cur.rowcount if cur else 0


def list_trash(c, user_id: int, *, limit: int = 300):
    rows = c.execute(
        """SELECT id, from_email, from_name, to_email, direction, subject, category,
                  received_at, deleted_at, is_read, is_starred,
                  substr(COALESCE(summary,''),1,160) AS summary_short
           FROM mail_messages WHERE user_id=? AND is_deleted=1
           ORDER BY deleted_at DESC, id DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def count_trash(c, user_id: int) -> int:
    r = c.execute("SELECT COUNT(*) AS n FROM mail_messages WHERE user_id=? AND is_deleted=1",
                  (user_id,)).fetchone()
    return (r["n"] if r else 0) or 0


def restore_mail(c, mail_id: int, user_id: int) -> bool:
    cur = c.execute("UPDATE mail_messages SET is_deleted=0, deleted_at=NULL "
                    "WHERE id=? AND user_id=? AND is_deleted=1", (mail_id, user_id))
    return cur.rowcount > 0


def hard_delete_mail(c, mail_id: int, user_id: int) -> bool:
    """1건 완전삭제 — 본인 메일만(첨부 blob + 본문 행 진짜 제거)."""
    own = c.execute("SELECT id FROM mail_messages WHERE id=? AND user_id=?", (mail_id, user_id)).fetchone()
    if not own:
        return False
    c.execute("DELETE FROM mail_attachments WHERE mail_id=?", (mail_id,))
    cur = c.execute("DELETE FROM mail_messages WHERE id=? AND user_id=?", (mail_id, user_id))
    return cur.rowcount > 0


def empty_trash(c, user_id: int) -> int:
    """휴지통(is_deleted=1) 전부 완전삭제. 반환 삭제 건수."""
    c.execute("DELETE FROM mail_attachments WHERE mail_id IN "
              "(SELECT id FROM mail_messages WHERE user_id=? AND is_deleted=1)", (user_id,))
    cur = c.execute("DELETE FROM mail_messages WHERE user_id=? AND is_deleted=1", (user_id,))
    return cur.rowcount


def purge_old_count(c, user_id: int, before_iso: str) -> int:
    """받은 메일 중 before_iso(받은시각) 이전 건수(미리보기)."""
    r = c.execute("SELECT COUNT(*) AS n FROM mail_messages "
                  "WHERE user_id=? AND direction='in' AND received_at < ?",
                  (user_id, before_iso)).fetchone()
    return (r["n"] if r else 0) or 0


def purge_old(c, user_id: int, before_iso: str) -> int:
    """받은 메일 중 before_iso 이전 완전삭제(첨부 포함). 반환 삭제 건수."""
    c.execute("DELETE FROM mail_attachments WHERE mail_id IN "
              "(SELECT id FROM mail_messages WHERE user_id=? AND direction='in' AND received_at < ?)",
              (user_id, before_iso))
    cur = c.execute("DELETE FROM mail_messages WHERE user_id=? AND direction='in' AND received_at < ?",
                    (user_id, before_iso))
    return cur.rowcount


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
    message_id = str(msg.get("Message-ID") or msg.get("Message-Id") or "").strip().strip("<>").strip()

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
        "message_id": message_id,
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
    # 진짜 위험 요소만 제거(스크립트·폼·임베드 등). 서식·<style>·인라인 style 은 보존 →
    # 아웃룩 서명의 MsoNormal 여백 규칙이 살아 원본 간격이 유지됨. iframe 격리라 안전.
    s = re.sub(r"(?is)<\s*(script|noscript|iframe|object|embed|applet|form|svg|math)\b.*?<\s*/\s*\1\s*>", " ", s)
    s = re.sub(r"(?is)<\s*/?\s*(script|noscript|iframe|object|embed|applet|form|svg|math|meta|base|input|button|textarea|select)\b[^>]*>", " ", s)

    # <style> 내용은 보존하되 위험(@import 원격로드·expression·javascript:)만 제거
    def _style_clean(m):
        css = m.group(1)
        css = re.sub(r"(?is)@import[^;]*;", "", css)
        css = re.sub(r"(?is)expression\s*\([^)]*\)", "", css)
        css = re.sub(r"(?is)javascript:", "", css)
        return "<style>" + css + "</style>"
    s = re.sub(r"(?is)<style\b[^>]*>(.*?)</style>", _style_clean, s)

    # on... 이벤트 핸들러 속성 제거 · href/src javascript: 무력화
    s = re.sub(r"(?is)\son[a-z]+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", " ", s)
    s = re.sub(r"(?is)(href|src)\s*=\s*([\"'])\s*javascript:[^\"']*\2", r'\1=\2#\2', s)

    # cid 매칭 맵(content_id·파일명·도메인앞부분)
    cid_map = {}
    for a in (inline_atts or []):
        aid = a["id"]
        cidv = (a.get("content_id") or "").strip().lower()
        fname = (a.get("filename") or "").strip().lower()
        if cidv:
            cid_map[cidv] = aid
            if "@" in cidv:
                cid_map[cidv.split("@", 1)[0]] = aid
        if fname:
            cid_map.setdefault(fname, aid)

    # <img> 통째 처리: ①cid 해결→우리서버 URL ②cid 미해결→깔끔한 자리표시(깨진 박스 방지)
    #                   ③원격(http) 이미지는 그대로 표시
    def _img_sub(m):
        tag = m.group(0)
        cm = re.search(r"(?is)src\s*=\s*[\"']\s*cid:([^\"']+)[\"']", tag)
        if not cm:
            return tag  # 원격(http/https) 이미지 등은 그대로
        cid = cm.group(1).strip().lower()
        aid = cid_map.get(cid) or cid_map.get(cid.split("@", 1)[0])
        if aid:
            return re.sub(r"(?is)src\s*=\s*([\"'])\s*cid:[^\"']+\1",
                          f'src="/mail/{mail_id}/att/{aid}"', tag)
        # 미해결(예: 기능 이전 수신메일은 원문 이미지 미저장) → 깨진 이미지 대신 자리표시
        return ('<span style="display:inline-block;padding:1px 7px;font-size:11px;'
                'color:#9ca3af;border:1px dashed #d1d5db;border-radius:4px;'
                'font-family:sans-serif">\U0001F5BC 이미지</span>')

    s = re.sub(r"(?is)<img\b[^>]*>", _img_sub, s)
    return s


# ─── KNK 대용량 첨부 (큰 파일 → NAS 보관 + 다운로드 링크) ─────────────
# 파일은 data/mail_large/{token}/ (정적 비공개). /dl/{token} 라우트만 서빙(만료·횟수 검사).
def _large_root() -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 01_HAIST_WORKS
    return os.path.join(base, "data", "mail_large")


def new_large_token() -> str:
    return secrets.token_urlsafe(24)


def large_file_dir(token: str) -> str:
    return os.path.join(_large_root(), token)


def safe_filename(name: str) -> str:
    """경로조작·위험문자 제거. 빈 값이면 'file'."""
    name = os.path.basename((name or "").replace("\\", "/")).strip()
    name = re.sub(r'[\x00-\x1f<>:"/\\|?*]', "_", name)
    name = name.lstrip(".") or "file"
    return name[:180]


def register_large_file(c, *, token: str, user_id: int, filename: str, mime: str,
                        path: str, size: int, expiry_days: int = 30):
    """업로드 완료된 대용량 파일을 DB 등록. 반환 expires_at(문자열) 또는 None(무기한)."""
    exp = None
    if expiry_days and expiry_days > 0:
        row = c.execute("SELECT datetime('now','localtime',?) AS e",
                        (f"+{int(expiry_days)} days",)).fetchone()
        exp = row["e"] if row else None
    c.execute(
        """INSERT INTO mail_large_files
           (token, filename, mime, size, path, uploaded_by, expires_at)
           VALUES(?,?,?,?,?,?,?)""",
        (token, (filename or "file")[:255], (mime or "")[:120], int(size or 0),
         path, user_id, exp),
    )
    return exp


def get_large_file(c, token: str):
    """다운로드용 조회. 없으면 None. 만료 시 dict 에 expired=True."""
    r = c.execute(
        "SELECT token, filename, mime, size, path, expires_at, "
        "(expires_at IS NOT NULL AND datetime('now','localtime') > expires_at) AS is_expired "
        "FROM mail_large_files WHERE token=?", (token,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["expired"] = bool(d.pop("is_expired"))
    return d


def bump_large_download(c, token: str) -> None:
    try:
        c.execute("UPDATE mail_large_files SET download_count = download_count + 1 WHERE token=?",
                  (token,))
    except Exception:
        pass


def human_size(n) -> str:
    try:
        n = float(n or 0)
    except Exception:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} TB"


def large_links_block(c, tokens, base_url: str) -> str:
    """선택된 대용량 첨부 토큰들 → 메일 본문에 붙일 다운로드 링크 블록(텍스트)."""
    items = []
    for t in (tokens or []):
        info = get_large_file(c, t)
        if not info or info.get("expired"):
            continue
        items.append((info["filename"] or "file", info["size"], t))
    if not items:
        return ""
    base = (base_url or "").rstrip("/")
    lines = ["", "──────────────────────────────",
             "📎 대용량 첨부파일 (아래 링크로 다운로드 · 30일 유효)"]
    for fn, sz, tk in items:
        lines.append(f"• {fn} ({human_size(sz)})")
        lines.append(f"  {base}/dl/{tk}")
    lines.append("──────────────────────────────")
    return "\n".join(lines)
