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


_RE_ANGLE_ADDR = re.compile(r"<\s*([^<>\s]+@[^<>\s]+?)\s*>")
_RE_BARE_ADDR = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def split_from(raw: str, decoded: str = "") -> tuple:
    """보낸 사람(From)·답장 주소(Reply-To) 머리 → (이름, 주소).
    11-22 대표 「보낸 사람 메일 주소가 없어?」 — 예전엔 머리를 먼저 글자로 푼 뒤 주소를 읽어, 이름에 쉼표·@ 가 있으면
    (예: 「홍길동, KNK VINA」) 파이썬이 이름·주소를 둘 다 빈 값으로 돌려줌 → 보낸 사람 「? <>」.
    → 주소는 **풀기 전 원문**에서 먼저 읽고, 이름만 따로 푼다. 그래도 없으면 <…> 안·맨 주소 꼴을 찾는다."""
    from email.header import decode_header, make_header
    raw = raw or ""
    decoded = decoded or raw
    try:
        name_raw, addr = parseaddr(raw)
    except Exception:
        name_raw, addr = "", ""
    # 11-22 (2차) 「=?euc-kr?b?…?= hong@x.com」(꺾쇠 없이 이름 뒤 주소) 같은 머리는 덩어리 전체가 주소로 돌아옴 → 올바른 주소 꼴만 받음
    if addr and not _RE_BARE_ADDR.fullmatch(addr.strip()):
        addr = ""
    if not addr or "@" not in addr:
        m = _RE_ANGLE_ADDR.search(raw) or _RE_ANGLE_ADDR.search(decoded)
        if not m:
            m = _RE_BARE_ADDR.search(decoded) or _RE_BARE_ADDR.search(raw)
            addr = m.group(0) if m else ""
        else:
            addr = m.group(1)
        name_raw = ""
    name = ""
    if name_raw:
        try:
            name = str(make_header(decode_header(name_raw)))
        except Exception:
            name = name_raw
    if not name:
        # 11-22 (2차) 머리에 주소가 아예 없는 메일(「From: 임태훈」·「From: <임태훈>」) — 예전엔 이름이 **주소 칸**에 들어갔고
        #   1차 고침 뒤엔 이름까지 버렸음 → 이름은 살리고 주소는 비움(주소는 다른 머리에서 — parse_from_headers)
        name = decoded.replace("<" + addr + ">", " ").replace(addr, " ") if addr else decoded
        name = re.sub(r"[<>]", " ", name)
    if addr and addr in name:
        name = name.replace(addr, " ")
    name = re.sub(r"\s+", " ", (name or "")).strip().strip('"').strip("'").strip()
    return name, (addr or "").strip()


# 11-22 대표 「보낸 사람 메일 주소가 확인 안 되는 게 있어 — 근본적인 원인을 찾아 해결」
#   보낸 사람 머리(From)에 주소가 없는 메일(상대 메일 시스템이 이름만 넣어 보냄)이 있음 → 같은 메일의 다른 머리에서 주소를 찾는다.
#   순서 = 보낸 이(Sender) → 답장 주소(Reply-To) → 반송 주소(Return-Path) → X-Original-From · X-Sender
FROM_FALLBACK_HEADERS = ("Sender", "Reply-To", "Return-Path", "X-Original-From", "X-Sender",
                         "Resent-From", "X-Envelope-From", "Envelope-From")   # 11-24 대표 「다른 직원 메일은 정확하게 보낸 사람이」 — 셋 더함
# 11-24 마지막 길: 메일 서버가 적은 봉투 주소 — Received 「(envelope-from <a@b>)」 · Authentication-Results 「smtp.mailfrom=a@b」
_RE_ENV_FROM = re.compile(r"envelope-from\s*[=:]?\s*<?\s*([A-Za-z0-9._%+\-=]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})", re.I)
_RE_SMTP_MAILFROM = re.compile(r"smtp\.mailfrom\s*=\s*<?\s*([A-Za-z0-9._%+\-=]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})", re.I)
_SKIP_ENV = ("mailer-daemon@", "postmaster@")


def envelope_from(received=(), auth_results=()) -> str:
    """봉투 주소(보낸 메일 서버가 알린 주소) — 맨 위 Received 부터 · 없으면 Authentication-Results smtp.mailfrom."""
    for txt in list(received or ()):
        m = _RE_ENV_FROM.search(str(txt or ""))
        if m and not m.group(1).lower().startswith(_SKIP_ENV):
            return m.group(1)
    for txt in list(auth_results or ()):
        for m in _RE_SMTP_MAILFROM.finditer(str(txt or "")):
            a = m.group(1)
            if a and not a.lower().startswith(_SKIP_ENV):
                return a
    return ""


def parse_from_headers(get_raw, get_dec, received=(), auth_results=()) -> tuple:
    """(이름, 주소, 주소를 찾은 머리) — get_raw(머리 이름)=원문 · get_dec(머리 이름)=풀어 쓴 글.
    순서: From → Sender → Reply-To → Return-Path → X-Original-From → X-Sender → Resent-From → X-Envelope-From → Envelope-From
          → Received 의 envelope-from → Authentication-Results 의 smtp.mailfrom (11-24)."""
    name, addr = split_from(get_raw("From"), get_dec("From"))
    if addr and "@" in addr:
        return name, addr, "From"
    for hd in FROM_FALLBACK_HEADERS:
        try:
            a = split_from(get_raw(hd), get_dec(hd))[1]
        except Exception:
            a = ""
        if a and "@" in a and not a.lower().startswith(_SKIP_ENV):
            return name, a, hd
    try:
        a = envelope_from(received, auth_results)
    except Exception:
        a = ""
    if a:
        return name, a, "Received"
    return name, "", ""


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
        if not ai_client.mail_ai_available():   # 11-18 메일 AI = OpenAI 만(대표 규칙)
            return ("일반", "")
        text = f"제목: {subject}\n본문:\n{(body or '')[:2000]}"
        system = (
            "당신은 KNK(검사기·자동화 설비 제조)의 메일 분류기입니다. "
            "아래 메일을 읽고 JSON 한 줄로만 답하세요. "
            '형식: {"category":"견적|발주|세금계산서|일반","lang":"ko|vi|en"} . '
            "category=메일 성격(견적 요청·회신→견적, 주문·발주→발주, 세금계산서·인보이스→세금계산서, "
            "그 외→일반). lang=본문 주 언어. 설명·따옴표·다른 텍스트 금지, JSON 만 출력."
        )
        ok, resp = ai_client.ai_chat(text, system=system, max_tokens=60, temperature=0,
                                     provider=ai_client.MAIL_AI_PROVIDER)
        if not ok:
            return ("일반", "")
        return _parse_classify(resp)
    except Exception:
        return ("일반", "")


def _ai_summary(body: str) -> str:
    """본문 → 5줄 불릿 요약. AI 없거나 오류면 ''."""
    try:
        from . import ai_client
        if not ai_client.mail_ai_available():   # 11-18 메일 AI = OpenAI 만
            return ""
        if not (body or "").strip():
            return ""
        ok, resp = ai_client.ai_summarize(body, style="bullet", provider=ai_client.MAIL_AI_PROVIDER)
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
try:   # 11-18 판별(mail_guard)과 같은 목록으로 — 두 목록이 달라 .dll·.msix 등이 경고 없이 내려받아지던 것
    from .mail_guard import EXEC_EXTS as _GEXE
    DANGEROUS_EXTS = DANGEROUS_EXTS | set(_GEXE)
except Exception:
    pass


def _owner_mail_ai_ok(c, owner) -> bool:
    """받는 사람에게 메일 AI 를 돌려도 되는가 — 메일 AI(OpenAI) 가능 + 그 사람 AI 허용(can_use_ai 칸이 있으면)."""
    try:
        from . import ai_client
        if not ai_client.mail_ai_available():
            return False
    except Exception:
        return False
    try:
        r = c.execute("SELECT * FROM users WHERE id=?", (owner,)).fetchone()
        if r is not None and "can_use_ai" in r.keys() and r["can_use_ai"] is not None:
            return bool(r["can_use_ai"])
    except Exception:
        pass
    return True


def is_known_sender(c, user_id, email) -> bool:
    """아는 사람인가(11-18 스팸함 자동에서 빼는 사람 · 그림 보이기) — 사내 주소 · 「스팸 아님」 누른 사람 ·
    주소록 · 거래처 담당자 · 협력사 · 내가 메일을 보낸 적 있는 사람 · 내 폴더 규칙에 넣은 곳."""
    a = _norm_addr(email)
    if not a or "@" not in a:
        return False
    dom = a.split("@")[-1]
    if any(dom == d or dom.endswith("." + d) for d in _OUR_DOMAINS):
        return True
    checks = [
        ("SELECT 1 FROM mail_user_allow WHERE user_id=? AND email=? LIMIT 1", (user_id, a)),
        ("SELECT 1 FROM shared_contacts WHERE email IS NOT NULL AND lower(email)=? LIMIT 1", (a,)),
        ("SELECT 1 FROM customer_contacts WHERE email IS NOT NULL AND lower(email)=? LIMIT 1", (a,)),
        ("SELECT 1 FROM suppliers WHERE email IS NOT NULL AND lower(email)=? LIMIT 1", (a,)),
        ("SELECT 1 FROM mail_folder_rules WHERE user_id=? AND lower(pattern) IN (?, ?) LIMIT 1", (user_id, a, dom)),
        ("SELECT 1 FROM mail_messages WHERE user_id=? AND direction='out' AND is_deleted=0 "
         "AND (lower(to_email) LIKE ? OR lower(COALESCE(cc,'')) LIKE ?) LIMIT 1", (user_id, "%" + a + "%", "%" + a + "%")),
    ]
    for q, p in checks:
        try:
            if c.execute(q, p).fetchone():
                return True
        except Exception:
            continue   # 표가 없는 DB(시험·옛 사본)는 건너뜀
    return False


def allow_sender(c, user_id, email) -> bool:
    """「스팸 아님」 — 이 사람은 앞으로 스팸함으로 옮기지 않는다(나에게만). 새 표 mail_user_allow(처음 누를 때 생김)."""
    a = _norm_addr(email)
    if not a or not user_id:
        return False
    c.execute("""CREATE TABLE IF NOT EXISTS mail_user_allow(
        user_id INTEGER NOT NULL,
        email TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        PRIMARY KEY(user_id, email))""")
    c.execute("INSERT OR IGNORE INTO mail_user_allow(user_id, email) VALUES(?,?)", (user_id, a))
    return True


NOT_PHISH_MARK = "내가 확인: 피싱 아님 / "   # 11-26 이 메일 경고를 사용자가 직접 푼 표시(되돌리기 때 원래대로)


def _ensure_trust(c):
    c.execute("""CREATE TABLE IF NOT EXISTS mail_user_trust(
        user_id INTEGER NOT NULL,
        email TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        PRIMARY KEY(user_id, email))""")


def trust_sender(c, user_id, email) -> bool:
    """11-26 대표 「피싱이 아닌 것으로 확정 · 의심을 풀어야 다음부터 정상으로」 — 이 보낸 사람(주소 그대로)을 믿음(나에게만).
    앞으로 이 사람 메일이 링크·문구만으로 「의심」이 되면 경고를 띄우지 않는다(save 참고). 첨부·사칭·인증·송금 경고는 그대로."""
    a = _norm_addr(email)
    if not a or "@" not in a or not user_id:
        return False
    _ensure_trust(c)
    c.execute("INSERT OR IGNORE INTO mail_user_trust(user_id, email) VALUES(?,?)", (user_id, a))
    return True


def untrust_sender(c, user_id, email) -> None:
    a = _norm_addr(email)
    if not a or not user_id:
        return
    _ensure_trust(c)
    c.execute("DELETE FROM mail_user_trust WHERE user_id=? AND email=?", (user_id, a))


# 11-26 대표 「피싱 아님을 누르면 그 주소로 들어온 것들은 다 정상으로」 — 이미 받은 메일에도 같은 규칙.
#   받을 때 규칙(store_inbound)과 같게: 의심(2) 가운데 「강한 이유」(codes)가 없는 것만 = 링크·문구만으로 생긴 의심.
#   저장된 메일엔 codes 가 없으므로, mail_guard 가 그 이유를 적을 때 쓰는 글자로 가려냄(하나라도 있으면 그대로 둠 · 넉넉히).
STRONG_REASON_KEYS = ("인증 실패", "사칭", "를 흉내 낸 주소(", "개인 무료 메일", "답장이 다른 곳", "실행파일", "매크로",
                      "웹페이지 파일", "위험한 첨부", "주의할 첨부", "비밀번호 걸린", "송금", "계좌", "계정·비밀번호")


def is_link_only_suspicion(level, note) -> bool:
    n = note or ""
    return int(level or 0) == 2 and not n.startswith(NOT_PHISH_MARK) and not any(k in n for k in STRONG_REASON_KEYS)


def not_phish_same_sender(c, user_id, email, skip_id=0) -> list:
    """나에게 같은 주소로 온 다른 메일 중 링크·문구만으로 의심(2)인 것 → 외부(1) + 「내가 확인: 피싱 아님」 표시.
    스팸함으로 옮겨져 있던 것은 받은편지함으로. 바꾼 메일 번호 목록."""
    a = _norm_addr(email)
    if not a or not user_id:
        return []
    done = []
    for r in c.execute("SELECT id, risk_level, risk_note, COALESCE(is_blocked,0) AS b FROM mail_messages "
                       "WHERE user_id=? AND direction='in' AND COALESCE(is_deleted,0)=0 AND risk_level=2 "
                       "AND lower(from_email)=? AND id<>?", (user_id, a, int(skip_id or 0))).fetchall():
        if not is_link_only_suspicion(r["risk_level"], r["risk_note"]):
            continue
        c.execute("UPDATE mail_messages SET risk_level=1, risk_note=? WHERE id=? AND user_id=? AND risk_level=2",
                  ((NOT_PHISH_MARK + (r["risk_note"] or ""))[:600], r["id"], user_id))
        if int(r["b"] or 0):
            set_blocked(c, user_id, r["id"], False)
        done.append(r["id"])
    return done


def undo_not_phish_same_sender(c, user_id, email, skip_id=0) -> list:
    """되돌리기 — 같은 주소 메일 중 「내가 확인: 피싱 아님」 표시가 붙은 것을 의심(2)으로 · 표시 지움."""
    a = _norm_addr(email)
    if not a or not user_id:
        return []
    done = []
    for r in c.execute("SELECT id, risk_note FROM mail_messages WHERE user_id=? AND direction='in' AND risk_level=1 "
                       "AND lower(from_email)=? AND id<>? AND risk_note LIKE ?",
                       (user_id, a, int(skip_id or 0), NOT_PHISH_MARK + "%")).fetchall():
        c.execute("UPDATE mail_messages SET risk_level=2, risk_note=? WHERE id=? AND user_id=?",
                  ((r["risk_note"] or "")[len(NOT_PHISH_MARK):], r["id"], user_id))
        done.append(r["id"])
    return done


def is_trusted_sender(c, user_id, email) -> bool:
    a = _norm_addr(email)
    if not a or not user_id:
        return False
    try:
        return bool(c.execute("SELECT 1 FROM mail_user_trust WHERE user_id=? AND email=? LIMIT 1", (user_id, a)).fetchone())
    except Exception:
        return False   # 표가 아직 없음(아무도 안 누름)


def _ensure_security_cols(c):
    """메일 표에 더한 칸(차단·위험 · 11-18 보관·이 메일만 폴더)을 만든다.
    ⭐(11-18) 「만들었다」를 기억하기 전에 **칸이 실제로 있는지** 확인한다 — 처음 열 때 DB 가 잠깐 잠겨 ALTER 가
    실패해도 다음 요청에서 다시 만든다(예전엔 실패해도 다 된 것으로 기억해 서버를 다시 켤 때까지 메일함이 열리지 않을 수 있었음).
    DB 파일마다 따로 기억(시험처럼 한 프로세스에서 DB 를 바꿔도 맞게)."""
    global _SEC_COLS_OK
    try:
        key = c.execute("PRAGMA database_list").fetchone()[2] or ("mem:%x" % id(c))   # 메모리 DB 는 연결마다 따로
    except Exception:
        key = "?"
    if _SEC_COLS_OK is True or (isinstance(_SEC_COLS_OK, set) and key in _SEC_COLS_OK):
        if _SEC_COLS_OK is True:
            _SEC_COLS_OK = {key}
        else:
            return
    need = {"is_blocked": "INTEGER DEFAULT 0", "risk_level": "INTEGER DEFAULT 0", "risk_note": "TEXT",
            # 11-18 대표 「3단계 진행해」 — 📦 보관(받은편지함에서만 빠짐 · 지우지 않음) · 📁 이 메일만 폴더
            "is_archived": "INTEGER DEFAULT 0", "fd_pin": "TEXT DEFAULT ''",
            # 11-19 대표 「1단계」 — 받은 메일의 「받는 사람」 전원(원문 To 그대로). to_email 은 첫 주소만이라 전체 답장 명단이 빠지던 것
            "to_all": "TEXT DEFAULT ''",
            # 11-19 2단계 — 🚩 기한(YYYY-MM-DD · 받는 사람 현지 날짜) · ⏰ 다시 알림(서버 시각 · 그때까지 받은편지함에서 숨김) · 돌아온 시각
            "flag_due": "TEXT DEFAULT ''", "snooze_until": "TEXT DEFAULT ''", "snooze_back": "TEXT DEFAULT ''",
            # 11-19 2단계-나 — ⏱ 예약 발송(direction='sched' 줄) · 보낼 때(서버 시각) · 상태 wait|sending|fail · 못 보낸 까닭 · 덧붙임(JSON)
            "sched_at": "TEXT DEFAULT ''", "sched_state": "TEXT DEFAULT ''", "sched_err": "TEXT DEFAULT ''", "sched_meta": "TEXT DEFAULT ''",
            # 11-22 대표 「자동 분류 · 옮기면 옮긴 위치가 기준 · 부서 이동은 바뀐 날부터」 — 메일 한 통마다 정한 폴더 열쇠(mail_folders.classify 가 적음)
            #   · 받은 때 보낸 직원의 부서(사내 메일 · 받을 때 적음 → 부서가 바뀌어도 지난 메일은 그 부서 폴더)
            "fd_key": "TEXT DEFAULT ''", "fd_team": "INTEGER"}
    try:
        have = {r[1] for r in c.execute("PRAGMA table_info(mail_messages)").fetchall()}
    except Exception:
        have = set()
    for col, typ in need.items():
        if col not in have:
            try:
                c.execute("ALTER TABLE mail_messages ADD COLUMN %s %s" % (col, typ))
            except Exception as e:
                print("[MAIL-COLS] %s 칸 만들기 실패(다음에 다시): %s" % (col, e))
    try:
        c.execute("""CREATE TABLE IF NOT EXISTS mail_blocklist(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern TEXT UNIQUE, kind TEXT DEFAULT 'email',
            note TEXT, created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime')))""")
    except Exception:
        pass
    try:
        have = {r[1] for r in c.execute("PRAGMA table_info(mail_messages)").fetchall()}
    except Exception:
        have = set()
    if all(col in have for col in need):
        if not isinstance(_SEC_COLS_OK, set):
            _SEC_COLS_OK = set()
        _SEC_COLS_OK.add(key)


def _att_ext(filename) -> str:
    """11-26 — 끝 점·빈칸·보이지 않는 글자를 떼고 읽음(판정과 같게)."""
    from .mail_guard import name_ext
    return name_ext(filename)


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


def remove_block(c, block_id) -> int:
    """차단 풀기 — 11-25: 그 차단으로 옮겼던 메일도 원래 자리로. 반환 되돌린 통수."""
    _ensure_security_cols(c)
    n = 0
    try:
        r = c.execute("SELECT pattern, kind FROM mail_blocklist WHERE id=?", (block_id,)).fetchone()
        c.execute("DELETE FROM mail_blocklist WHERE id=?", (block_id,))
        if r:
            n = restore_block_moves(c, r["pattern"], r["kind"])
    except Exception as e:
        print("[MAIL-BLOCK] 차단 풀기 되돌림 실패(차단은 풀림): %s" % str(e)[:120], flush=True)
    return n


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


_STAFF_NAMES = {"t": 0.0, "v": ()}


def _staff_names(c):
    """재직 직원 이름(이름 사칭 판별용) — 10분 캐시. 실패하면 빈 값(판별만 약해질 뿐 저장은 계속)."""
    import time as _t
    if c is None:
        return ()
    if _t.time() - _STAFF_NAMES["t"] < 600:
        return _STAFF_NAMES["v"]
    try:
        rows = c.execute("SELECT name FROM users WHERE COALESCE(is_active,1)=1").fetchall()
        v = tuple(sorted({(r[0] or "").strip() for r in rows if r and len((r[0] or "").strip()) >= 2}))
    except Exception:
        v = ()
    _STAFF_NAMES.update(t=_t.time(), v=v)
    return v


def assess_risk(from_email, to_email="", subject="", body="", html="", attachments=None,
                *, from_name="", auth=None, reply_to="", c=None, codes=None):
    """규칙기반 위험판별(AI 아님·무료·빠름 · 메일 내용을 밖으로 보내지 않음). 반환 (level 0~3, note).
    2026-11-16 대표 지시로 판별을 app/mail_guard.py 로 넓힘(인증 결과·흉내 주소·이름 사칭·답장 주소·링크 속임·
    매크로/HTML/압축 첨부·송금 계좌 변경). 3=위험(차단함 격리) / 2=의심(경고·링크 무력화) / 1=외부 / 0=사내."""
    try:
        from . import mail_guard as _mg
        return _mg.assess(from_email=from_email, from_name=from_name, subject=subject, body=body, html=html,
                          attachments=attachments, auth=auth, reply_to=reply_to, staff_names=_staff_names(c),
                          codes=codes)
    except Exception:
        pass
    # ↓ 새 판별이 실패하면 옛 규칙으로(저장은 막지 않는다)
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
                  message_id: str = "", auth=None, reply_to: str = "", to_all: str = "",
                  raw_headers: str = "", sent_at: str = "", ai_later=None):
    """받은 메일 1건 저장. 반환 (mail_id, owner_id).
    ai_later(목록을 넘기면): AI 분류·요약을 여기서 기다리지 않고 메일 번호만 담는다 → 부른 쪽이 저장(commit) 뒤 ai_fill_later 로
      (11-27 — 저장 묶음이 DB 를 잡은 채 AI 를 기다리면 그동안 웍스 저장이 실패한다).
    raw_headers: 원문 머리글(11-22 대표 「보낸 사람 주소를 알 수 없는 건 치명적」) — 서버 안에 남겨 언제든 다시 읽게(save_raw_headers).
    to_all: 원문 「받는 사람」 머리 그대로(여러 명) — 전체 답장 명단용(11-19).
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
    if run_ai is None:   # 11-18: 바깥 입구(/api/mail/inbound)도 받는 사람의 AI 허용·메일 AI(OpenAI) 여부를 따른다
        run_ai = _owner_mail_ai_ok(c, owner)
    _ai_defer = bool(run_ai) and ai_later is not None
    if run_ai and not _ai_defer:
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
    # 2026-11-16: 받는 사람이 「다시 안 받기」로 한 발신 → 그 사람의 차단함으로(나에게만 · 회사 전체 차단목록과 별개)
    try:
        from . import mail_cleanup as _mc
        if _mc.is_muted(c, owner, from_email):
            _blocked = 1
    except Exception:
        pass
    _codes = []
    _rlevel, _rnote = assess_risk(from_email, to_email, subject, body, html, attachments,
                                  from_name=from_name, auth=auth, reply_to=reply_to, c=c, codes=_codes)
    # 11-26 내가 「피싱 아님」으로 믿기로 한 보낸 사람 = 링크·문구만으로 생긴 「의심(2)」은 외부(1)로(경고 띠 없음 · 링크 그대로).
    #   이유 코드가 하나라도 있으면(첨부·사칭·인증 실패·답장 주소·송금 변경·계정 요구) 그대로 경고 — 믿는 사람 계정이 털린 경우를 막음
    if _rlevel == 2 and not _codes:
        try:
            if is_trusted_sender(c, owner, from_email):
                _rlevel = 1
                _rnote = ("믿는 보낸 사람(내가 「피싱 아님」 확인) / " + (_rnote or ""))[:600]
        except Exception:
            pass
    # 2026-11-16: 위험(3) = 차단함으로 격리(지우지 않음 · 차단함에서 복구 가능)
    #   증거가 강한 경우만(우리 회사 흉내 주소 · 우리 주소 인증 실패 · 위장 실행파일 · 회사 밖 실행파일) — 정상 메일을 숨기지 않게
    try:
        from . import mail_guard as _mg
        if _mg.should_quarantine(from_email, attachments, auth, _rlevel):
            _blocked = 1
    except Exception:
        pass
    # 11-18 대표 「스팸메일은 자동으로 걸러」(확실+의심까지 · 아는 사람은 제외): 의심(2) 이상이고 강한 이유가 있으면 스팸함으로.
    #   주소록·거래처 담당자·내가 메일을 보낸 적 있는 사람·「스팸 아님」 누른 사람·사내 주소는 옮기지 않는다(경고만).
    if not _blocked and _rlevel >= 2 and _codes:
        try:
            if not is_known_sender(c, owner, from_email):
                _blocked = 1
                _rnote = ("스팸함으로 옮김 / " + (_rnote or ""))[:600]
        except Exception:
            pass
    # 11-23 원래 보낸 날짜(Date 머리) — 「지난 메일 가져오기」로 들어온 옛 메일도 6개월·12개월 규칙이 맞게(받은 시각은 그대로 둠)
    #   ⭐칸을 못 만들었으면(잠김 등) 날짜 없이 저장 — 메일 받기는 절대 멈추지 않게
    _with_sent = False
    try:
        from .mail_body_pack import ensure as _pack_ensure, has_sent_at as _has_sent
        _pack_ensure(c)
        _with_sent = _has_sent(c)
    except Exception:
        _with_sent = False
    # 11-24 받은 시각 = 메일 서버에 도착한 시각(맨 위 Received · 없으면 Date) — 예전엔 저장 시각(가져온 때)이 들어감
    _arr = ""
    try:
        _arr = arrival_at(raw_headers, sent_at)
    except Exception:
        _arr = ""
    _vals = (owner, "in", _norm_addr(from_email), (from_name or "").strip(),
             _norm_addr(to_email), (cc or "").strip(), subject, body, html or "",
             category, lang, summary, sz, _dh, 1, _blocked, _rlevel, _rnote, (to_all or "").strip()[:4000])
    if _with_sent:
        cur = c.execute(
            """INSERT INTO mail_messages
               (user_id, direction, from_email, from_name, to_email, cc,
                subject, body_text, body_html, category, lang, summary, raw_size,
                dedup_hash, dup_count, is_blocked, risk_level, risk_note, to_all, sent_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", _vals + ((sent_at or "").strip()[:19],))
    else:
        cur = c.execute(
            """INSERT INTO mail_messages
               (user_id, direction, from_email, from_name, to_email, cc,
                subject, body_text, body_html, category, lang, summary, raw_size,
                dedup_hash, dup_count, is_blocked, risk_level, risk_note, to_all)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", _vals)
    mail_id = cur.lastrowid
    if _ai_defer:
        ai_later.append(mail_id)
    if _arr:
        try:
            c.execute("UPDATE mail_messages SET received_at=? WHERE id=?", (_arr, mail_id))
        except Exception as _e:
            print("[MAIL-RECV] 도착 시각 적기 실패(저장 시각 그대로): %s" % str(_e)[:120], flush=True)
    if attachments:
        _save_attachments(c, mail_id, attachments)
    if raw_headers:
        try:
            save_raw_headers(c, mail_id, raw_headers, from_ok="@" in _norm_addr(from_email))
        except Exception as _e:
            print("[MAIL-HDR] 원문 머리글 남기기 실패(메일은 저장됨): %s" % str(_e)[:120], flush=True)
    try:   # 11-22 사내 메일 = 받은 때 부서를 적어 둠(부서가 바뀌어도 이 메일은 그 부서 폴더)
        from . import mail_folders as _mfo
        _mfo.stamp_arrival(c, mail_id, from_email)
    except Exception as _e:
        print("[MAIL-FOLDERS] 받은 때 부서 적기 실패(폴더 열 때 채움): %s" % str(_e)[:120], flush=True)
    try:   # 11-26 대표 「1번 진행해」 — 서식 본문 받을 때 바로 압축 · 같은 본문(그룹 메일)은 보관함 한 벌을 같이 씀
        from .mail_body_pack import pack_now as _pack_now
        _pack_now(c, mail_id, html or "")
    except Exception as _e:
        print("[MAIL-BODY-PACK] 받을 때 압축 건너뜀(본문 그대로): %s" % str(_e)[:120], flush=True)
    return (mail_id, owner)


AI_LATER_MAX = 40   # 11-27 한 번 받기에서 AI 분류·요약을 돌리는 최대 통수(메일이 한꺼번에 몰려도 비용·시간이 끝없이 늘지 않게)


def ai_fill_later(session, ids, limit=AI_LATER_MAX) -> int:
    """store_inbound(ai_later=…) 로 미뤄 둔 AI 분류·요약 채우기 — 저장(commit)이 끝난 뒤 부른다.
    읽기 → (DB 를 잡지 않은 채) AI 기다리기 → 짧게 UPDATE. 그 사이 사람이 종류를 바꿨으면 종류는 그대로 둔다.
    session = database.db_session. 반환 = 채운 통수. 실패한 메일은 AI 없이 그대로(메일은 이미 저장됨)."""
    done = 0
    for mid in list(ids or [])[:max(0, int(limit or 0))]:
        try:
            with session() as c:
                r = c.execute("SELECT user_id, from_email, from_name, subject, body_text, category "
                              "FROM mail_messages WHERE id=?", (mid,)).fetchone()
            if not r:
                continue
            cat, lang = _ai_classify(r["subject"] or "", r["body_text"] or "")
            summ = _ai_summary(r["body_text"] or "")
            with session() as c:
                try:
                    _rcat = match_rules(c, r["user_id"], r["from_email"], r["from_name"], r["subject"])
                except Exception:
                    _rcat = None
                # 저장 때 넣은 처음 값(규칙 결과 또는 「일반」) 그대로일 때만 종류를 바꾼다 — 사람이 바꾼 종류는 덮지 않음
                c.execute("UPDATE mail_messages SET category=CASE WHEN category=? THEN ? ELSE category END, "
                          "lang=CASE WHEN COALESCE(lang,'')='' THEN ? ELSE lang END, "
                          "summary=CASE WHEN COALESCE(summary,'')='' THEN ? ELSE summary END WHERE id=?",
                          (_rcat or "일반", _rcat or cat, lang, summ, mid))
            done += 1
        except Exception as _e:
            print("[MAIL-AI-LATER] %s 번 AI 채우기 건너뜀(메일은 저장됨): %s" % (mid, str(_e)[:120]), flush=True)
    _left = len(list(ids or [])) - max(0, int(limit or 0))
    if _left > 0:
        print("[MAIL-AI-LATER] 한 번 받기 AI 한도(%d통) 넘음 — %d통은 AI 없이 저장" % (limit, _left), flush=True)
    return done


def dedup_inbox(c, user_id: int, hard: bool = False) -> int:
    """받은편지함의 '진짜 같은 메일' 중복을 1통만 남기고 나머지를 정리. 반환=정리한 통수.
    읽음/별표는 그룹에 하나라도 있으면 남긴 1통에 보존, dup_count(왔던 총통수) 기록.
    답장 스레드(제목만 같고 본문 다름)는 해시가 달라 절대 안 건드림.
    hard=False(기본): 휴지통으로 소프트삭제(복구 가능) — 사람이 누르는 수동 정리용.
    hard=True: 중복 사본을 첨부까지 영구삭제(원본 1통은 100% 보존 → 잃는 정보 0) — 자동 정리·용량 회수용.
              신규 중복을 아예 안 쌓는 것(store_inbound)과 같은 원리. 휴지통에 안 쌓여 용량이 실제로 줄어듦."""
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
            if hard:
                # 영구삭제: 첨부 BLOB 먼저, 그다음 메일 행. 원본(grp[0])은 보존 → 정보손실 0.
                c.execute("DELETE FROM mail_attachments WHERE mail_id=?", (x["id"],))
                c.execute("DELETE FROM mail_messages WHERE id=?", (x["id"],))
            else:
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


def _ensure_rules_apply_bak(c):
    c.execute("""CREATE TABLE IF NOT EXISTS mail_rules_apply_bak(
        batch TEXT NOT NULL, user_id INTEGER NOT NULL, mail_id INTEGER NOT NULL, old_category TEXT,
        PRIMARY KEY(batch, mail_id))""")


def apply_rules_existing(c, user_id: int, dry: bool = False) -> int:
    """기존 받은편지함 메일에 규칙 소급 적용 — 카테고리 갱신. 변경(dry=셈만) 건수 반환.
    11-25 대표 규정 knk-no-silent-change: dry=True 면 몇 통이 바뀌는지만(아무것도 안 바꿈) ·
    바꿀 때는 바꾸기 전 값을 되돌림 표(mail_rules_apply_bak · 묶음)에 남김 → undo_rules_apply."""
    _ensure_rules(c)
    rows = c.execute("SELECT id, from_email, from_name, subject, category FROM mail_messages "
                     "WHERE user_id=? AND direction='in' AND is_deleted=0", (user_id,)).fetchall()
    changed = 0
    batch = ""
    if not dry:
        import datetime as _dt
        _ensure_rules_apply_bak(c)
        batch = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    for m in rows:
        newcat = match_rules(c, user_id, m["from_email"], m["from_name"], m["subject"])
        if newcat and newcat != m["category"]:
            changed += 1
            if dry:
                continue
            c.execute("INSERT OR REPLACE INTO mail_rules_apply_bak(batch, user_id, mail_id, old_category) VALUES(?,?,?,?)",
                      (batch, user_id, m["id"], m["category"]))
            c.execute("UPDATE mail_messages SET category=? WHERE id=?", (newcat, m["id"]))
    return changed


def undo_rules_apply(c, user_id: int) -> int:
    """마지막 「규칙 소급 적용」 묶음을 그대로 되돌림 — 되돌린 통수."""
    _ensure_rules_apply_bak(c)
    r = c.execute("SELECT MAX(batch) FROM mail_rules_apply_bak WHERE user_id=?", (user_id,)).fetchone()
    b = r[0] if r else None
    if not b:
        return 0
    n = 0
    for x in c.execute("SELECT mail_id, old_category FROM mail_rules_apply_bak WHERE batch=? AND user_id=?", (b, user_id)).fetchall():
        n += c.execute("UPDATE mail_messages SET category=? WHERE id=? AND user_id=?", (x["old_category"], x["mail_id"], user_id)).rowcount
    c.execute("DELETE FROM mail_rules_apply_bak WHERE batch=? AND user_id=?", (b, user_id))
    return n


# ─── 조회 ───────────────────────────────────────────────────────────
# 같은 회사 주소(@ 뒤)로 거래처 묶기에서 빼는 주소 — 개인 메일(여러 회사 사람이 같이 씀) · 우리 회사.
_NO_DOMAIN_GROUP = tuple(sorted(set(
    ("gmail.com", "naver.com", "daum.net", "hanmail.net", "kakao.com", "nate.com", "outlook.com", "hotmail.com",
     "live.com", "yahoo.com", "yahoo.co.kr", "icloud.com", "me.com", "qq.com", "163.com", "126.com", "proton.me",
     "protonmail.com", "msn.com", "aol.com", "korea.com", "lycos.co.kr", "gmx.com", "mail.ru", "yandex.com",
     "zoho.com", "hotmail.co.kr", "outlook.kr", "empas.com", "dreamwiz.com", "paran.com", "freechal.com",
     "chol.com", "hitel.net", "sina.com", "foxmail.com", "yahoo.com.vn")
    + _OUR_DOMAINS)))


def _dom_sql(col: str) -> str:
    """메일 주소 칸 → 소문자 회사 주소(@ 뒤) SQL 식."""
    return "lower(substr(%s, instr(%s,'@')+1))" % (col, col)


# 회사 주소 → 거래처: 그 주소를 쓰는 연락처들이 **한 거래처만** 가리킬 때만(둘 이상이면 묶지 않음 · 추측 금지).
_CUST_DOMAIN_MAP_SQL = (
    "SELECT " + _dom_sql("trim(email)") + " AS dom, MIN(customer_id) AS cid FROM shared_contacts "
    "WHERE email LIKE '%_@_%.%' AND customer_id IS NOT NULL "
    "GROUP BY " + _dom_sql("trim(email)") + " "
    "HAVING COUNT(DISTINCT customer_id)=1 AND " + _dom_sql("trim(email)") + " NOT IN ("
    + ",".join("'%s'" % d for d in _NO_DOMAIN_GROUP) + ")")


def _dup_count_sql(c) -> str:
    """목록에 쓸 「합친 통수」 식. 칸이 없는 DB(읽기 전용 사본 · 옛 DB)에서도 목록이 죽지 않게 — 읽는 길에서는 칸을 만들지 않는다."""
    try:
        cols = [r[1] for r in c.execute("PRAGMA table_info(mail_messages)").fetchall()]
        return "COALESCE(dup_count,1)" if "dup_count" in cols else "1"
    except Exception:
        return "1"


KIND_WORDS = {
    "견적": ("견적", "quotation", "quote", "rfq", "estimate", "báo giá", "bao gia"),
    "발주": ("발주", "주문서", "purchase order", "p/o", "po no", "po#", "po :", "po:", "đơn đặt hàng", "don dat hang"),
    "세금계산서": ("세금계산서", "계산서", "tax invoice", "invoice", "hóa đơn", "hoa don"),
}


def mail_kind(m) -> str:
    """메일 종류 — 저장된 종류(AI·내 규칙)가 먼저, 「일반」이면 제목 낱말로(11-19 · AI 꺼진 직원도 모아 보기가 되게)."""
    cat = (m.get("category") or "").strip()
    if cat in KIND_WORDS:
        return cat
    subj = (m.get("subject") or "").lower()
    for k, words in KIND_WORDS.items():
        if any(w in subj for w in words):
            return k
    return ""


def list_inbox(c, user_id: int, *, category: str = "", q: str = "",
               starred=None, unread=None, date_from: str = "", date_to: str = "",
               has_att=None, cust: str = "", limit: int = 200, offset: int = 0, only_ids=None,
               senders=None, qf: str = "all", with_sent: bool = False, who: str = "", dom: str = "",
               q_senders=None, noad=None, count_only: bool = False, arc: bool = False, fd_keys=None,
               flagged: bool = False, snoozed: bool = False, kind_words=None, ad_only=None):
    """받은편지함 목록.
    (11-23) kind_words = 「🏷 내 종류」 낱말 — 제목·보낸 사람(이름·주소)에 하나라도 들어간 메일.
    (11-18 대표 「쉽게 찾기」) q = 띄어 쓴 낱말 **모두** 들어간 메일(낱말마다 보낸 사람·받는 사람·참조·제목·본문·첨부 파일 이름 중 한 곳) ·
    qf = all|from|subj|att(어디서 찾을지) · with_sent = 보낸 메일도 함께 · who/dom = 이 사람·이 회사와 주고받은 메일 ·
    q_senders = 낱말마다 「그 이름의 폴더에 든 보낸 주소」(회사 이름을 치면 영문 주소로 온 메일도) · noad = 빼고 볼 광고·알림 주소 ·
    count_only = 통수만.
    (3단계) arc = 📦 보관함(보관한 받은 메일만) · 그냥 받은편지함은 보관한 메일을 뺀다(폴더·찾기·중요·회신 보기에는 그대로 나옴) ·
    fd_keys = 지금 폴더(와 아래 폴더) 열쇠 — 「이 메일만」 옮긴 메일은 보낸 사람과 상관없이 그 폴더로."""
    _ensure_security_cols(c)
    who = (who or "").strip().lower()
    dom = (dom or "").strip().lower().lstrip("@")
    _sent_ok = bool(with_sent or who or dom) and senders is None and not cust and only_ids is None
    if _sent_ok:
        where = ("user_id=? AND is_deleted=0 AND (direction='out' OR (direction='in' AND COALESCE(is_blocked,0)=0))")
    else:
        where = "user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0"
    args = [user_id]
    if who:
        where += " AND (lower(from_email)=? OR lower(COALESCE(to_email,'')) LIKE ? OR lower(COALESCE(cc,'')) LIKE ?)"
        args += [who, "%" + who + "%", "%" + who + "%"]
    if dom:
        where += (" AND (lower(from_email) LIKE ? OR lower(COALESCE(to_email,'')) LIKE ? "
                  "OR lower(COALESCE(cc,'')) LIKE ?)")
        args += ["%@" + dom, "%@" + dom + "%", "%@" + dom + "%"]
    _terms0 = search_terms(q)
    if arc:
        where += " AND direction='in' AND COALESCE(is_archived,0)=1"
    elif senders is None and not _terms0 and not who and not dom and not starred and only_ids is None and not cust \
            and not flagged and not snoozed:
        where += " AND COALESCE(is_archived,0)=0"
    # 11-19 2단계 — 🚩 기한 보기 · ⏰ 다시 알림 보기 · 그 밖에는 「다시 알림」 기다리는 메일을 숨김(시간이 되면 다시 보임)
    if flagged:
        where += " AND COALESCE(flag_due,'')<>''"
    elif snoozed:
        where += " AND (COALESCE(snooze_until,'')<>'' OR snooze_back >= datetime('now','localtime','-3 days'))"
    elif only_ids is None:
        where += " AND (COALESCE(snooze_until,'')='' OR snooze_until <= datetime('now','localtime'))"
    if category and category in KIND_WORDS:
        _kw = KIND_WORDS[category]
        where += (" AND (category=? OR (COALESCE(category,'일반') IN ('일반','') AND ("
                  + " OR ".join(["lower(subject) LIKE ?"] * len(_kw)) + ")))")
        args += [category] + ["%" + w + "%" for w in _kw]
    elif category and category in CATEGORIES:
        where += " AND category=?"
        args.append(category)
    _kws = [str(w).strip().lower() for w in (kind_words or []) if str(w).strip()][:20]
    if _kws:
        where += (" AND (" + " OR ".join(["(lower(COALESCE(subject,'')) LIKE ? OR lower(COALESCE(from_name,'')) LIKE ? "
                                          "OR lower(COALESCE(from_email,'')) LIKE ?)"] * len(_kws)) + ")")
        for w in _kws:
            args += ["%" + w + "%"] * 3
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
    # C1 거래처 폴더 — ① 보낸사람 이메일 정확일치(소문자) ② (11-17 대표 지시 「업체별 구분」) 정확일치가 없으면
    #   같은 회사 주소(@ 뒤)가 **한 거래처만** 가리킬 때 그 거래처로. 개인 메일·우리 회사 주소는 묶지 않음. cust='none'=미분류.
    cust = (cust or "").strip()
    _exact_any = ("EXISTS(SELECT 1 FROM shared_contacts sc "
                  "WHERE sc.email IS NOT NULL AND lower(sc.email)=lower(mail_messages.from_email) "
                  "AND sc.customer_id IS NOT NULL)")
    _mdom = _dom_sql("mail_messages.from_email")
    if cust == "none":
        where += (" AND NOT " + _exact_any +
                  " AND " + _mdom + " NOT IN (SELECT dom FROM (" + _CUST_DOMAIN_MAP_SQL + "))")
    elif cust.isdigit():
        where += (" AND (EXISTS(SELECT 1 FROM shared_contacts sc "
                  "WHERE sc.email IS NOT NULL AND lower(sc.email)=lower(mail_messages.from_email) "
                  "AND sc.customer_id=?)"
                  " OR (NOT " + _exact_any + " AND " + _mdom +
                  " IN (SELECT dom FROM (" + _CUST_DOMAIN_MAP_SQL + ") WHERE cid=?)))")
        args += [int(cust), int(cust)]
    # ④ 회신 필요(추정) 보기 — 고른 메일만(mail_reply.scan 결과)
    if only_ids is not None:
        _ids = [int(i) for i in list(only_ids)[:500]]
        if not _ids:
            return []
        where += " AND id IN (" + ",".join("?" * len(_ids)) + ")"
        args += _ids
    # (11-17 대표 지시 「아웃룩처럼 폴더」) 폴더 = 보낸 사람 묶음 — mail_folders.classify 가 정한 주소들만.
    #   주소가 수백 개일 수 있어 IN (?,?,…) 대신 이 연결 전용 임시 표로 거른다(SQLite 인자 개수 한도 회피).
    #   11-22: 폴더 = 메일 한 통마다 적어 둔 폴더 열쇠(fd_key · 「이 메일만」·내 규칙·받은 때 부서까지 반영) — 열쇠가 오면 그것만 본다
    if fd_keys is not None:
        _fk = sorted({k for k in fd_keys if k})
        if not _fk:
            return 0 if count_only else []
        c.execute("CREATE TEMP TABLE IF NOT EXISTS _mf_keys(k TEXT PRIMARY KEY)")
        c.execute("DELETE FROM _mf_keys")
        c.executemany("INSERT OR IGNORE INTO _mf_keys(k) VALUES(?)", [(x,) for x in _fk])
        where += " AND direction='in' AND COALESCE(fd_key,'') IN (SELECT k FROM _mf_keys)"
    elif senders is not None:
        _ss = sorted({(x or "").strip().lower() for x in senders})
        if not _ss:
            return 0 if count_only else []
        c.execute("CREATE TEMP TABLE IF NOT EXISTS _mf_senders(e TEXT PRIMARY KEY)")
        c.execute("DELETE FROM _mf_senders")
        c.executemany("INSERT OR IGNORE INTO _mf_senders(e) VALUES(?)", [(x,) for x in _ss])
        where += " AND lower(from_email) IN (SELECT e FROM _mf_senders)"
    # 광고·알림 빼고 보기(11-18) — 「보낸 곳별 정리」가 광고·알림으로 본 주소(받은 메일만 해당)
    #   11-23 {주소: 그때부터} 도 받음(내가 「날짜부터 광고·알림」으로 표시) · 📢 광고·알림 칸 = ad_only(같은 기준 · 그 메일만)
    for _flag, _src in (("noad", noad), ("ad", ad_only)):
        if not _src:
            continue
        _pairs = sorted({((x or "").strip().lower(), (_src.get(x) or "") if isinstance(_src, dict) else "") for x in _src if x})
        _tb = "_mf_ad_" + _flag
        c.execute("CREATE TEMP TABLE IF NOT EXISTS " + _tb + "(e TEXT PRIMARY KEY, s TEXT NOT NULL DEFAULT '')")
        c.execute("DELETE FROM " + _tb)
        c.executemany("INSERT OR REPLACE INTO " + _tb + "(e, s) VALUES(?,?)", _pairs)
        _ex = ("(direction='in' AND EXISTS(SELECT 1 FROM " + _tb + " t WHERE t.e=lower(mail_messages.from_email) "
               "AND COALESCE(mail_messages.received_at,'') >= t.s))")
        where += (" AND NOT " + _ex) if _flag == "noad" else (" AND " + _ex)
    if ad_only is not None and not ad_only:
        where += " AND 0"
    terms = search_terms(q)
    if terms:
        qf = qf if qf in ("all", "from", "subj", "att") else "all"
        _att = ("EXISTS(SELECT 1 FROM mail_attachments a WHERE a.mail_id=mail_messages.id "
                "AND COALESCE(a.is_inline,0)=0 AND a.filename LIKE ?)")
        _qs = list(q_senders or [])
        if any(_qs):
            c.execute("CREATE TEMP TABLE IF NOT EXISTS _mf_qs(t INTEGER, e TEXT, PRIMARY KEY(t, e))")
            c.execute("DELETE FROM _mf_qs")
        for i, t in enumerate(terms):
            like = "%" + t + "%"
            if qf == "from":
                parts = ["from_email LIKE ?", "from_name LIKE ?", "(direction='out' AND COALESCE(to_email,'') LIKE ?)"]
                pargs = [like, like, like]
            elif qf == "subj":
                parts, pargs = ["subject LIKE ?"], [like]
            elif qf == "att":
                parts, pargs = [_att], [like]
            else:
                parts = ["from_email LIKE ?", "from_name LIKE ?", "subject LIKE ?", "body_text LIKE ?",
                         "COALESCE(to_email,'') LIKE ?", "COALESCE(cc,'') LIKE ?", _att]
                pargs = [like] * 7
            ss = sorted({(x or "").strip().lower() for x in (_qs[i] if i < len(_qs) else None) or [] if x})
            if ss and qf in ("all", "from"):
                c.executemany("INSERT OR IGNORE INTO _mf_qs(t, e) VALUES(?,?)", [(i, x) for x in ss])
                parts.append("(direction='in' AND lower(from_email) IN (SELECT e FROM _mf_qs WHERE t=%d))" % i)
            where += " AND (" + " OR ".join(parts) + ")"
            args += pargs
    if count_only:
        return int(c.execute(f"SELECT COUNT(*) FROM mail_messages WHERE {where}", args).fetchone()[0] or 0)
    _order = ("flag_due ASC, received_at DESC, id DESC" if flagged else
              ("CASE WHEN COALESCE(snooze_until,'')<>'' THEN 0 ELSE 1 END, snooze_until ASC, snooze_back DESC, id DESC" if snoozed
               else "received_at DESC, id DESC"))
    # 11-27 대표 「폴더를 누르면 느려」 — 폴더(fd_keys·senders)는 거르는 칸이 모두 덮는 색인(idx_mail_cov_*)에 있어
    #   그 색인만 보고 이 쪽 번호(200통)를 먼저 고른 뒤 그 번호의 줄만 읽는다. 전에는 받은 때 순서로 메일 줄을 하나씩
    #   (본문 뒤 칸까지) 읽으며 폴더 것을 찾아 폴더가 작을수록 메일함 전체를 읽었음(2.6만 통 가짜 자료 192 → 15ms).
    #   고른 메일·순서는 같다(같은 조건 · 같은 정렬 · 번호가 끝 기준이라 순서가 하나로 정해짐).
    if fd_keys is not None or senders is not None:
        where = ("id IN (SELECT id FROM mail_messages WHERE " + where + " ORDER BY " + _order + " LIMIT ? OFFSET ?)")
        args = [*args, limit, offset]
        limit, offset = -1, 0
    rows = c.execute(
        f"""SELECT id, direction, from_email, from_name, to_email, cc, subject, category, lang,
                   is_read, is_starred, received_at, COALESCE(risk_level,0) AS risk_level,
                   COALESCE(is_archived,0) AS is_archived, COALESCE(fd_pin,'') AS fd_pin, COALESCE(fd_key,'') AS fd_key,
                   COALESCE(flag_due,'') AS flag_due, COALESCE(snooze_until,'') AS snooze_until, COALESCE(snooze_back,'') AS snooze_back,
                   {_dup_count_sql(c)} AS dup_count,
                   (SELECT COUNT(*) FROM mail_attachments a WHERE a.mail_id=mail_messages.id
                      AND COALESCE(a.is_inline,0)=0) AS att_n,
                   substr(COALESCE(summary,''),1,160) AS summary_short,
                   trim(replace(replace(replace(substr(COALESCE(body_text,''),1,240), char(13),' '), char(10),' '), char(9),' ')) AS preview
            FROM mail_messages WHERE {where}
            ORDER BY {_order} LIMIT ? OFFSET ?""",
        (*args, limit, offset),
    ).fetchall()
    return [dict(r) for r in rows]


def _own_ids(c, user_id, ids, inbound_only=False) -> list:
    """고른 번호 중 내 메일(지우지 않은 것)만 — 남의 메일·없는 번호는 조용히 뺀다. 최대 500."""
    out = []
    for x in list(ids or [])[:500]:
        try:
            out.append(int(x))
        except Exception:
            pass
    if not out:
        return []
    q = ",".join("?" * len(out))
    extra = " AND direction='in'" if inbound_only else ""
    return [r[0] for r in c.execute("SELECT id FROM mail_messages WHERE user_id=? AND is_deleted=0" + extra +
                                    " AND id IN (" + q + ")", (user_id, *out)).fetchall()]


def set_flag(c, user_id, ids, due: str = "") -> int:
    """🚩 기한 정하기/풀기(11-19 2단계) — due='YYYY-MM-DD' · 빈 값 = 풀기. 받은·보낸 메일 모두."""
    _ensure_security_cols(c)
    due = (due or "").strip()[:10]
    if due:
        import re as _re
        if not _re.match(r"^\d{4}-\d{2}-\d{2}$", due):
            return 0
    own = _own_ids(c, user_id, ids)
    if not own:
        return 0
    q = ",".join("?" * len(own))
    c.execute("UPDATE mail_messages SET flag_due=? WHERE user_id=? AND id IN (" + q + ")", (due, user_id, *own))
    return len(own)


def set_snooze(c, user_id, ids, until: str = "") -> int:
    """⏰ 다시 알림(11-19 2단계) — until='YYYY-MM-DD HH:MM:SS'(서버 시각) 까지 받은편지함에서 숨김 · 읽음으로. 빈 값 = 풀기(바로 다시 보임)."""
    _ensure_security_cols(c)
    own = _own_ids(c, user_id, ids, inbound_only=True)
    if not own:
        return 0
    q = ",".join("?" * len(own))
    if until:
        c.execute("UPDATE mail_messages SET snooze_until=?, snooze_back='', is_read=1, "
                  "read_at=COALESCE(read_at, datetime('now','localtime')) WHERE user_id=? AND id IN (" + q + ")",
                  (until, user_id, *own))
    else:
        c.execute("UPDATE mail_messages SET snooze_until='' WHERE user_id=? AND id IN (" + q + ")", (user_id, *own))
    return len(own)


def snooze_wake(c, user_id) -> int:
    """시간이 된 「다시 알림」 메일 깨우기 — 안 읽음으로 되돌리고 「돌아온 시각」을 남김(⏰ 보기에 3일 동안 보임)."""
    _ensure_security_cols(c)
    cur = c.execute("UPDATE mail_messages SET is_read=0, read_at=NULL, snooze_back=snooze_until, snooze_until='' "
                    "WHERE user_id=? AND COALESCE(snooze_until,'')<>'' AND snooze_until <= datetime('now','localtime')",
                    (user_id,))
    return cur.rowcount or 0


def count_flag(c, user_id, today: str) -> dict:
    """🚩 기한 숫자 — 전체 · 오늘까지(지난 것 포함)."""
    _ensure_security_cols(c)
    r = c.execute("SELECT COUNT(*) AS n, SUM(CASE WHEN flag_due<=? THEN 1 ELSE 0 END) AS due FROM mail_messages "
                  "WHERE user_id=? AND is_deleted=0 AND COALESCE(flag_due,'')<>''", (today, user_id)).fetchone()
    return {"n": int(r["n"] or 0), "due": int(r["due"] or 0)}


def count_snoozed(c, user_id) -> int:
    _ensure_security_cols(c)
    r = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND is_deleted=0 AND COALESCE(snooze_until,'')<>''",
                  (user_id,)).fetchone()
    return int(r[0] or 0)


def latest_inbox(c, user_id):
    """받은편지함 맨 위 새 메일(번호·보낸 사람·제목) — 새 메일이 왔는지 알아보기용(11-19 2단계 · 내 메일만)."""
    _ensure_security_cols(c)
    # 11-25 읽은 메일은 「새 메일」이 아님 — 아웃룩 옛 메일 가져오기(읽음으로 들어옴)가 알림을 띄우지 않게
    r = c.execute("SELECT id, from_name, from_email, subject FROM mail_messages WHERE user_id=? AND direction='in' "
                  "AND is_deleted=0 AND COALESCE(is_blocked,0)=0 AND COALESCE(is_archived,0)=0 AND COALESCE(is_read,0)=0 "
                  "AND (COALESCE(snooze_until,'')='' OR snooze_until <= datetime('now','localtime')) "
                  "ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    return dict(r) if r else None


def set_archived(c, user_id, ids, on=True) -> int:
    """📦 보관 / 받은편지함으로 — 받은 메일만. 보관할 때는 읽음으로도(안 읽은 숫자가 보이지 않는 곳에 남지 않게)."""
    _ensure_security_cols(c)
    own = _own_ids(c, user_id, ids, inbound_only=True)
    if not own:
        return 0
    q = ",".join("?" * len(own))
    if on:
        sql = ("UPDATE mail_messages SET is_archived=1, is_read=1, read_at=COALESCE(read_at, datetime('now','localtime')) "
               "WHERE user_id=? AND id IN (" + q + ")")
    else:
        sql = "UPDATE mail_messages SET is_archived=0 WHERE user_id=? AND id IN (" + q + ")"
    return c.execute(sql, (user_id, *own)).rowcount


def archive_old(c, user_id, months=3, dry=True) -> int:
    """오래된 메일 한 번에 보관 — 받은 지 N개월 지난 **읽은** 메일(⭐ 중요 표시·차단·휴지통 제외). dry=True 면 셈만."""
    _ensure_security_cols(c)
    months = int(months) if str(months).isdigit() and int(months) in (1, 3, 6, 12) else 3
    cut = c.execute("SELECT datetime('now','localtime', ?)", ("-%d months" % months,)).fetchone()[0]
    where = ("user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0 AND COALESCE(is_archived,0)=0 "
             "AND is_read=1 AND COALESCE(is_starred,0)=0 AND received_at < ?")
    if dry:
        return int(c.execute("SELECT COUNT(*) FROM mail_messages WHERE " + where, (user_id, cut)).fetchone()[0] or 0)
    return c.execute("UPDATE mail_messages SET is_archived=1 WHERE " + where, (user_id, cut)).rowcount


def unarchive_recent(c, user_id, months=3, dry=True):
    """11-23 📦 보관함 → 📥 받은편지함 — 받은 지 N개월 안(최근 3·6·12개월)의 보관 메일을 한 번에 되돌림.
    「오래된 메일 한 번에 보관」(archive_old · 받은 날짜 기준)을 기간을 잘못 골라 했을 때 쉽게 바로잡게. 내 받은 메일만.
    dry=True 면 (통수, 기준 날짜) · 아니면 (되돌린 메일 번호 목록, 기준 날짜)."""
    _ensure_security_cols(c)
    months = int(months) if str(months).isdigit() and int(months) in (3, 6, 12) else 3
    cut = c.execute("SELECT datetime('now','localtime', ?)", ("-%d months" % months,)).fetchone()[0]
    where = ("user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_archived,0)=1 AND received_at >= ?")
    if dry:
        return int(c.execute("SELECT COUNT(*) FROM mail_messages WHERE " + where, (user_id, cut)).fetchone()[0] or 0), cut
    ids = [r[0] for r in c.execute("SELECT id FROM mail_messages WHERE " + where, (user_id, cut)).fetchall()]
    for i in range(0, len(ids), 500):
        part = ids[i:i + 500]
        c.execute("UPDATE mail_messages SET is_archived=0 WHERE user_id=? AND id IN (" + ",".join("?" * len(part)) + ")",
                  (user_id, *part))
    return ids, cut


def rearchive_ids(c, user_id, ids) -> int:
    """「↺ 되돌리기」 — 방금 받은편지함으로 꺼낸 메일을 다시 보관함으로(내 메일만)."""
    n = 0
    ids = [int(x) for x in ids if str(x).isdigit()]
    for i in range(0, len(ids), 500):
        part = ids[i:i + 500]
        n += c.execute("UPDATE mail_messages SET is_archived=1 WHERE user_id=? AND direction='in' AND id IN ("
                       + ",".join("?" * len(part)) + ")", (user_id, *part)).rowcount
    return n


def bulk_apply(c, user_id, ids, op) -> int:
    """여러 통 한 번에 — read · unread · star · unstar · archive · unarchive · delete(휴지통) · restore(휴지통에서 되살림). 내 메일만."""
    if op == "archive":
        return set_archived(c, user_id, ids, True)
    if op == "unarchive":
        return set_archived(c, user_id, ids, False)
    if op == "restore":  # 휴지통에서 되살리기(11-18 끌어서 옮기기 「↺ 되돌리기」) — 내 메일 · 지운 것만
        nums = []
        for x in list(ids or [])[:500]:
            try:
                nums.append(int(x))
            except Exception:
                pass
        if not nums:
            return 0
        q = ",".join("?" * len(nums))
        return c.execute("UPDATE mail_messages SET is_deleted=0, deleted_at=NULL WHERE user_id=? AND is_deleted=1 AND id IN (" + q + ")",
                         (user_id, *nums)).rowcount
    own = _own_ids(c, user_id, ids)
    if not own:
        return 0
    q = ",".join("?" * len(own))
    sets = {"read": "is_read=1, read_at=COALESCE(read_at, datetime('now','localtime'))", "unread": "is_read=0",
            "star": "is_starred=1", "unstar": "is_starred=0",
            "delete": "is_deleted=1, deleted_at=datetime('now','localtime')"}.get(op)
    if not sets:
        return 0
    return c.execute("UPDATE mail_messages SET " + sets + " WHERE user_id=? AND id IN (" + q + ")", (user_id, *own)).rowcount


def unread_ids(c, user_id, senders=None, fd_keys=None, noad=None) -> list:
    """11-22 대표 「✓ 모두 읽음」 — 안 읽은 받은 메일 번호.
    senders=None → 받은편지함 전체(왼쪽 「받은편지함」 안 읽음 숫자와 같은 조건 · 누르면 그 숫자가 0) ·
    senders(+fd_keys) → 그 폴더(왼쪽 폴더 숫자와 같은 조건: 스팸 빼고 · 보관·다시 알림 포함)."""
    where = "user_id=? AND direction='in' AND is_deleted=0 AND is_read=0"
    args = [user_id]
    if fd_keys is not None or senders is not None:
        _ensure_security_cols(c)
        where += " AND COALESCE(is_blocked,0)=0"
    if fd_keys is not None:   # 11-22: 메일마다 적어 둔 폴더 열쇠(목록 거르기와 같은 조건)
        _fk = sorted({k for k in fd_keys if k})
        if not _fk:
            return []
        c.execute("CREATE TEMP TABLE IF NOT EXISTS _mf_keys(k TEXT PRIMARY KEY)")
        c.execute("DELETE FROM _mf_keys")
        c.executemany("INSERT OR IGNORE INTO _mf_keys(k) VALUES(?)", [(x,) for x in _fk])
        where += " AND COALESCE(fd_key,'') IN (SELECT k FROM _mf_keys)"
    elif senders is not None:
        _ss = sorted({(x or "").strip().lower() for x in senders})
        if not _ss:
            return []
        c.execute("CREATE TEMP TABLE IF NOT EXISTS _mf_senders(e TEXT PRIMARY KEY)")
        c.execute("DELETE FROM _mf_senders")
        c.executemany("INSERT OR IGNORE INTO _mf_senders(e) VALUES(?)", [(x,) for x in _ss])
        where += " AND lower(from_email) IN (SELECT e FROM _mf_senders)"
    if noad and senders is None and fd_keys is None:   # 11-23 받은편지함 「✓ 모두 읽음」 = 보이는 메일만(광고·알림은 📢 칸에서)
        where += _noad_where(c, noad)
    return [r[0] for r in c.execute("SELECT id FROM mail_messages WHERE " + where + " ORDER BY id", args).fetchall()]


def set_read_many(c, user_id, ids, read: bool) -> int:
    """여러 통 읽음/안 읽음(500통 넘어도) — 내 받은 메일만. ✓ 모두 읽음 · ↺ 되돌리기."""
    nums = []
    for x in list(ids or [])[:50000]:
        try:
            nums.append(int(x))
        except Exception:
            pass
    n = 0
    sets = "is_read=1, read_at=COALESCE(read_at, datetime('now','localtime'))" if read else "is_read=0"
    for i in range(0, len(nums), 400):
        chunk = nums[i:i + 400]
        n += c.execute("UPDATE mail_messages SET " + sets + " WHERE user_id=? AND direction='in' AND is_read=? AND id IN ("
                       + ",".join("?" * len(chunk)) + ")", (user_id, 0 if read else 1, *chunk)).rowcount
    return n


def set_pin(c, user_id, ids, key) -> int:
    """📁 이 메일만 폴더로(key='f<폴더id>') · key='' 면 자동 분류로 되돌림. 받은 메일만 · 폴더는 내 것만(부르는 쪽이 확인)."""
    _ensure_security_cols(c)
    own = _own_ids(c, user_id, ids, inbound_only=True)
    if not own:
        return 0
    q = ",".join("?" * len(own))
    return c.execute("UPDATE mail_messages SET fd_pin=? WHERE user_id=? AND id IN (" + q + ")",
                     ((key or ""), user_id, *own)).rowcount


def nav_ids(c, user_id, m) -> dict:
    """풀페이지 읽기의 ‹ 이전 메일 · 다음 메일 › — 받은편지함 순서(새 메일이 위 · 보관·차단·휴지통 제외)."""
    out = {"prev": None, "next": None}
    try:
        if (m.get("direction") or "in") != "in":
            return out
        base = ("user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0 AND COALESCE(is_archived,0)=0")
        ra, mid = m.get("received_at") or "", m["id"]
        r = c.execute("SELECT id FROM mail_messages WHERE " + base + " AND (received_at>? OR (received_at=? AND id>?)) "
                      "ORDER BY received_at ASC, id ASC LIMIT 1", (user_id, ra, ra, mid)).fetchone()
        out["prev"] = r[0] if r else None
        r = c.execute("SELECT id FROM mail_messages WHERE " + base + " AND (received_at<? OR (received_at=? AND id<?)) "
                      "ORDER BY received_at DESC, id DESC LIMIT 1", (user_id, ra, ra, mid)).fetchone()
        out["next"] = r[0] if r else None
    except Exception:
        pass
    return out


def count_archived(c, user_id) -> int:
    try:
        _ensure_security_cols(c)
        return int(c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 "
                             "AND COALESCE(is_blocked,0)=0 AND COALESCE(is_archived,0)=1", (user_id,)).fetchone()[0] or 0)
    except Exception:
        return 0


def search_terms(q) -> list:
    """찾기 칸 글 → 낱말(띄어쓰기로 나눔 · 「따옴표 안」은 한 낱말 · 같은 낱말 한 번 · 최대 6개)."""
    import shlex
    q = (q or "").strip()
    if not q:
        return []
    try:
        raw = shlex.split(q.replace("“", '"').replace("”", '"'))
    except Exception:
        raw = q.split()
    out = []
    for t in raw:
        t = t.strip()
        if t and t.lower() not in [x.lower() for x in out]:
            out.append(t[:60])
        if len(out) >= 6:
            break
    return out


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
    # 11-19 3단계 — 같은 제목이라도 상대 회사(주소 @ 뒤)가 다르면 다른 대화(「견적 요청」이 여러 회사에서 와도 섞이지 않게).
    #   우리 회사 사람끼리 주고받은 메일은 같은 제목의 바깥 회사가 하나뿐이면 그 대화에 붙인다.
    def _dom(m):
        if (m.get("direction") or "in") == "out":
            a = (m.get("to_email") or "").split(",")[0]
        else:
            a = m.get("from_email") or ""
        a = a.strip().lower()
        d = a.rsplit("@", 1)[-1].strip(" >") if "@" in a else ""
        return "" if (not d or any(d == o or d.endswith("." + o) for o in _OUR_DOMAINS)) else d
    subj_doms = {}
    for m in mails:
        subj_doms.setdefault(_normalize_subject(m.get("subject")), set()).add(_dom(m))
    order, groups = [], {}
    for m in mails:
        sj = _normalize_subject(m.get("subject"))
        d = _dom(m)
        if not d:
            ext = subj_doms.get(sj, set()) - {""}
            d = next(iter(ext)) if len(ext) == 1 else ""
        key = sj + "\x1f" + d
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


def customer_folder_counts(c, user_id: int, total_only: bool = False) -> dict:
    """받은편지함을 보낸사람→연락처→거래처 매핑으로 거래처별 집계 (C1 폴더, 2026-06-14).
    매핑 ① 이메일 '정확일치(소문자)' ② (2026-11-17) 정확일치가 없으면 같은 회사 주소(@ 뒤)가 한 거래처만 가리킬 때
    — 둘 이상이면 묶지 않음(추측 금지 [[feedback-data-connectivity]]). 미매핑=미분류. 목록 거르기(list_inbox cust=)와 같은 규칙.
    반환: {total, total_unread, unclassified, unclassified_unread, customers:[{id,name,cnt,unread,by_domain}]}.
    (11-27) total_only = 전체 통수만(받은편지함에 폴더 나무가 있으면 화면이 「거래처 폴더」 줄을 안 그려 total 만 씀 — 거래처별 셈 생략)."""
    tot = c.execute(
        "SELECT COUNT(*) AS n, SUM(CASE WHEN is_read=0 THEN 1 ELSE 0 END) AS u "
        "FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0",
        (user_id,)).fetchone()
    if total_only:
        return {"total": (tot["n"] or 0) if tot else 0, "total_unread": (tot["u"] or 0) if tot else 0,
                "unclassified": 0, "unclassified_unread": 0, "customers": [], "total_only": True}
    exact, dom_map = {}, {}
    try:
        for r in c.execute("SELECT lower(email) AS e, customer_id AS cid FROM shared_contacts "
                           "WHERE email IS NOT NULL AND customer_id IS NOT NULL").fetchall():
            exact.setdefault(r["e"], set()).add(r["cid"])
        for r in c.execute(_CUST_DOMAIN_MAP_SQL).fetchall():
            dom_map[r["dom"]] = r["cid"]
    except Exception:
        exact, dom_map = {}, {}
    names = {}
    try:
        for r in c.execute("SELECT id, name FROM customers").fetchall():
            names[r["id"]] = r["name"]
    except Exception:
        pass
    per = {}
    unc_n = unc_u = 0
    for r in c.execute(
            "SELECT lower(from_email) AS e, COUNT(*) AS n, SUM(CASE WHEN is_read=0 THEN 1 ELSE 0 END) AS u "
            "FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 GROUP BY lower(from_email)",
            (user_id,)).fetchall():
        e = r["e"] or ""
        n, un = r["n"] or 0, r["u"] or 0
        cids = [x for x in exact.get(e, ()) if x in names]
        by_dom = False
        if not exact.get(e):
            d = e.rsplit("@", 1)[-1] if "@" in e else ""
            if d in dom_map and dom_map[d] in names:
                cids, by_dom = [dom_map[d]], True
        if not cids:
            if not exact.get(e):
                unc_n += n
                unc_u += un
            continue
        for cid in cids:
            p = per.setdefault(cid, {"id": cid, "name": names[cid], "cnt": 0, "unread": 0, "by_domain": 0})
            p["cnt"] += n
            p["unread"] += un
            if by_dom:
                p["by_domain"] += n
    customers = sorted(per.values(), key=lambda x: (-x["cnt"], x["name"] or ""))
    return {
        "total": (tot["n"] or 0) if tot else 0,
        "total_unread": (tot["u"] or 0) if tot else 0,
        "unclassified": unc_n,
        "unclassified_unread": unc_u,
        "customers": customers,
    }


def _noad_where(c, admap, tb="_mf_ad_cnt"):
    """11-23 광고·알림 빼기 조건(보낸 주소 + 그때부터) — list_inbox 와 같은 식. admap 이 비면 ''."""
    if not admap:
        return ""
    pairs = sorted({((x or "").strip().lower(), (admap.get(x) or "") if isinstance(admap, dict) else "") for x in admap if x})
    c.execute("CREATE TEMP TABLE IF NOT EXISTS " + tb + "(e TEXT PRIMARY KEY, s TEXT NOT NULL DEFAULT '')")
    c.execute("DELETE FROM " + tb)
    c.executemany("INSERT OR REPLACE INTO " + tb + "(e, s) VALUES(?,?)", pairs)
    return (" AND NOT EXISTS(SELECT 1 FROM " + tb + " t WHERE t.e=lower(mail_messages.from_email) "
            "AND COALESCE(mail_messages.received_at,'') >= t.s)")


def count_unread(c, user_id: int, noad=None) -> int:
    """받은편지함 안 읽음 숫자. 11-23 noad = 광고·알림 표({주소: 그때부터}) — 주면 그 메일은 빼고 셈(📢 광고·알림 칸에만 보이므로)."""
    r = c.execute(
        "SELECT COUNT(*) AS n FROM mail_messages "
        "WHERE user_id=? AND direction='in' AND is_deleted=0 AND is_read=0" + _noad_where(c, noad),
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
    """발송한 메일을 보낸편지함에 기록(direction='out').
    (11-19) 받는 사람 여러 명 = 전원 기록(소문자 주소 · 쉼표) — 전에는 첫 주소만 남아 누구에게 갔는지 추적이 안 됐다."""
    try:
        from .mail_send import parse_addr_list as _pal
        _tl = [a.lower() for _n, a in _pal(to_email)[0]]
    except Exception:
        _tl = []
    to_rec = ", ".join(_tl) if _tl else _norm_addr(to_email)
    cur = c.execute(
        """INSERT INTO mail_messages
           (user_id, direction, from_email, from_name, to_email, cc, bcc,
            subject, body_text, body_html, category, is_read, raw_size)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,1,?)""",
        (user_id, "out", _norm_addr(from_email), (from_name or "").strip(),
         to_rec, (cc or "").strip(), (bcc or "").strip(),
         (subject or "(제목 없음)").strip(), body or "", body_html or "", "일반", int(size or 0)),
    )
    _oid = cur.lastrowid
    try:   # 11-26 서식 본문 보낼 때 바로 압축(받을 때와 같은 규칙)
        from .mail_body_pack import pack_now as _pack_now
        _pack_now(c, _oid, body_html or "")
    except Exception as _e:
        print("[MAIL-BODY-PACK] 보낼 때 압축 건너뜀(본문 그대로): %s" % str(_e)[:120], flush=True)
    return _oid


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


# ─── 11-19 2단계-나 ① 서명 여러 개 — 0번 = 지금 쓰는 기본 서명(mail_signatures 그대로) · 1·2번 = 더 만든 서명 ───
def _ensure_sig_alt(c):
    c.execute("""CREATE TABLE IF NOT EXISTS mail_signature_alts(
        user_id INTEGER NOT NULL, slot INTEGER NOT NULL, name TEXT DEFAULT '', body TEXT DEFAULT '',
        updated_at TEXT DEFAULT (datetime('now','localtime')), PRIMARY KEY(user_id, slot))""")


def get_signatures(c, user_id: int) -> list:
    """[{slot, name, body}] — 0 = 기본(늘 있음) · 1·2 = 내용이 있는 것만."""
    _ensure_sig_alt(c)
    out = [{"slot": 0, "name": "기본 서명", "body": get_signature(c, user_id)}]
    for r in c.execute("SELECT slot, name, body FROM mail_signature_alts WHERE user_id=? AND slot IN (1,2) ORDER BY slot",
                       (user_id,)).fetchall():
        if (r["body"] or "").strip():
            out.append({"slot": r["slot"], "name": (r["name"] or "").strip() or ("서명 %d" % (r["slot"] + 1)), "body": r["body"]})
    return out


def get_signature_slot(c, user_id: int, slot: int) -> dict:
    if not slot:
        return {"slot": 0, "name": "기본 서명", "body": get_signature(c, user_id)}
    _ensure_sig_alt(c)
    r = c.execute("SELECT name, body FROM mail_signature_alts WHERE user_id=? AND slot=?", (user_id, slot)).fetchone()
    return {"slot": slot, "name": (r["name"] if r else "") or "", "body": (r["body"] if r else "") or ""}


def save_signature_slot(c, user_id: int, slot: int, name: str, body: str) -> None:
    if not slot:
        return save_signature(c, user_id, body)
    if slot not in (1, 2):
        return
    _ensure_sig_alt(c)
    c.execute("INSERT INTO mail_signature_alts(user_id, slot, name, body, updated_at) VALUES(?,?,?,?,datetime('now','localtime')) "
              "ON CONFLICT(user_id, slot) DO UPDATE SET name=excluded.name, body=excluded.body, updated_at=excluded.updated_at",
              (user_id, slot, (name or "").strip()[:40], (body or "").strip()))


# ─── 11-19 2단계-나 ② ⏱ 예약 발송 — direction='sched' 줄(목록·숫자에는 안 섞임) · 첨부는 그 줄에 저장 ───
def create_scheduled(c, *, user_id: int, to_email: str, cc: str, bcc: str, subject: str, body: str, body_html: str,
                     sched_at: str, meta: str = "", attachments=None) -> int:
    _ensure_security_cols(c)
    cur = c.execute(
        "INSERT INTO mail_messages(user_id, direction, to_email, cc, bcc, subject, body_text, body_html, is_read, "
        "sched_at, sched_state, sched_meta) VALUES(?,?,?,?,?,?,?,?,1,?,?,?)",
        (user_id, "sched", to_email, cc, bcc, (subject or "(제목 없음)").strip(), body or "", body_html or "",
         sched_at, "wait", meta or ""))
    mid = cur.lastrowid
    if attachments:
        _save_attachments(c, mid, attachments)
    return mid


def list_scheduled(c, user_id: int) -> list:
    _ensure_security_cols(c)
    return [dict(r) for r in c.execute(
        "SELECT id, to_email, cc, subject, sched_at, sched_state, sched_err, "
        "(SELECT COUNT(*) FROM mail_attachments a WHERE a.mail_id=mail_messages.id) AS att_n "
        "FROM mail_messages WHERE user_id=? AND direction='sched' AND is_deleted=0 ORDER BY sched_at", (user_id,)).fetchall()]


def count_scheduled(c, user_id: int) -> dict:
    _ensure_security_cols(c)
    r = c.execute("SELECT COUNT(*) AS n, SUM(CASE WHEN sched_state='fail' THEN 1 ELSE 0 END) AS f FROM mail_messages "
                  "WHERE user_id=? AND direction='sched' AND is_deleted=0", (user_id,)).fetchone()
    return {"n": int(r["n"] or 0), "fail": int(r["f"] or 0)}


def due_scheduled(c, limit: int = 20) -> list:
    """보낼 때가 된 예약(모든 사람) — 번호 · 주인."""
    _ensure_security_cols(c)
    return [dict(r) for r in c.execute(
        "SELECT id, user_id FROM mail_messages WHERE direction='sched' AND is_deleted=0 AND sched_state='wait' "
        "AND sched_at<>'' AND sched_at <= datetime('now','localtime') ORDER BY sched_at LIMIT ?", (limit,)).fetchall()]


def claim_scheduled(c, mail_id: int) -> bool:
    """「보내는 중」으로 잡기 — 한 번만 잡힘(두 번 보내지 않게)."""
    cur = c.execute("UPDATE mail_messages SET sched_state='sending' WHERE id=? AND direction='sched' AND sched_state='wait'", (mail_id,))
    return bool(cur.rowcount)


def scheduled_done(c, mail_id: int) -> None:
    """보낸 뒤 — 예약 줄과 그 첨부를 지움(보낸편지함에는 보낸 메일이 따로 남음)."""
    c.execute("DELETE FROM mail_attachments WHERE mail_id=?", (mail_id,))
    c.execute("DELETE FROM mail_messages WHERE id=? AND direction='sched'", (mail_id,))


def scheduled_fail(c, mail_id: int, err: str) -> None:
    c.execute("UPDATE mail_messages SET sched_state='fail', sched_err=? WHERE id=? AND direction='sched'", ((err or "")[:300], mail_id))


def scheduled_to_draft(c, user_id: int, mail_id: int) -> bool:
    """예약 취소 → 📝 임시보관함으로(내용·받는 사람 그대로 · 첨부는 다시 붙여야)."""
    cur = c.execute("UPDATE mail_messages SET direction='draft', sched_state='', sched_at='', received_at=datetime('now','localtime') "
                    "WHERE id=? AND user_id=? AND direction='sched' AND sched_state IN ('wait','fail')", (mail_id, user_id))
    if cur.rowcount:
        c.execute("DELETE FROM mail_attachments WHERE mail_id=?", (mail_id,))
    return bool(cur.rowcount)


def scheduled_retry_now(c, user_id: int, mail_id: int) -> bool:
    cur = c.execute("UPDATE mail_messages SET sched_state='wait', sched_err='', sched_at=datetime('now','localtime') "
                    "WHERE id=? AND user_id=? AND direction='sched' AND sched_state IN ('wait','fail')", (mail_id, user_id))
    return bool(cur.rowcount)


# ─── 11-19 2단계-나 ③ 🏖 부재중 자동 응답 ───
def _ensure_autoreply(c):
    c.execute("""CREATE TABLE IF NOT EXISTS mail_autoreply(
        user_id INTEGER PRIMARY KEY, enabled INTEGER DEFAULT 0, start_date TEXT DEFAULT '', end_date TEXT DEFAULT '',
        subject TEXT DEFAULT '', body TEXT DEFAULT '', only_known INTEGER DEFAULT 1,
        updated_at TEXT DEFAULT (datetime('now','localtime')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS mail_autoreply_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, addr TEXT, mail_id INTEGER,
        sent_at TEXT DEFAULT (datetime('now','localtime')))""")
    c.execute("CREATE INDEX IF NOT EXISTS ix_mar_log ON mail_autoreply_log(user_id, addr)")


def get_autoreply(c, user_id: int) -> dict:
    _ensure_autoreply(c)
    r = c.execute("SELECT * FROM mail_autoreply WHERE user_id=?", (user_id,)).fetchone()
    d = dict(r) if r else {"user_id": user_id, "enabled": 0, "start_date": "", "end_date": "", "subject": "", "body": "", "only_known": 1}
    return d


def save_autoreply(c, user_id: int, *, enabled: bool, start_date: str, end_date: str, subject: str, body: str, only_known: bool) -> None:
    _ensure_autoreply(c)
    c.execute("INSERT INTO mail_autoreply(user_id, enabled, start_date, end_date, subject, body, only_known, updated_at) "
              "VALUES(?,?,?,?,?,?,?,datetime('now','localtime')) ON CONFLICT(user_id) DO UPDATE SET enabled=excluded.enabled, "
              "start_date=excluded.start_date, end_date=excluded.end_date, subject=excluded.subject, body=excluded.body, "
              "only_known=excluded.only_known, updated_at=excluded.updated_at",
              (user_id, 1 if enabled else 0, start_date, end_date, (subject or "").strip()[:200], (body or "").strip()[:4000], 1 if only_known else 0))


_AUTO_ADDR_RE = re.compile(r"(?:^|[._+-])(no-?reply|do-?not-?reply|mailer-daemon|postmaster|bounce|bounces|notification|notifications|"
                           r"alert|alerts|newsletter|news|info-?mail|auto|daemon|system|admin)(?:[._+-]|@)", re.I)


def autoreply_should(c, owner_id: int, mail: dict, today: str, my_addrs=(), auto_hdr: bool = False, bulk=()) -> tuple:
    """이 메일에 부재중 자동 응답을 보낼까 — (보냄?, 까닭). 하나라도 걸리면 안 보냄(조심스럽게)."""
    st = get_autoreply(c, owner_id)
    if not st.get("enabled"):
        return (False, "꺼짐")
    if not (st.get("start_date") and st.get("end_date") and st["start_date"] <= today <= st["end_date"]):
        return (False, "기간 밖")
    frm = (mail.get("from_email") or "").strip().lower()
    if not frm or "@" not in frm:
        return (False, "보낸 사람 없음")
    mine = {a.lower() for a in my_addrs if a}
    if frm in mine:
        return (False, "나 자신")
    if auto_hdr:
        return (False, "자동 발송 메일(뉴스레터·알림·자동 응답·반송)")
    if _AUTO_ADDR_RE.search(frm.split("@")[0] + "@"):
        return (False, "자동 발송 주소")
    if mail.get("is_blocked") or int(mail.get("risk_level") or 0) >= 2:
        return (False, "스팸·위험 메일")
    if frm in set(bulk or ()):
        return (False, "광고·알림으로 보이는 곳")
    to_all = (mail.get("to_all") or mail.get("to_email") or "").lower()
    if mine and not any(a in to_all for a in mine):
        return (False, "나를 참조로만 넣은 메일")
    if st.get("only_known") and not is_known_sender(c, owner_id, frm):
        return (False, "모르는 사람(아는 사람에게만)")
    _ensure_autoreply(c)
    if c.execute("SELECT 1 FROM mail_autoreply_log WHERE user_id=? AND addr=? AND sent_at >= ?", (owner_id, frm, st["start_date"])).fetchone():
        return (False, "이번 기간에 이미 보냄")
    if (c.execute("SELECT COUNT(*) FROM mail_autoreply_log WHERE user_id=? AND sent_at >= datetime('now','localtime','-1 day')",
                  (owner_id,)).fetchone()[0] or 0) >= 50:
        return (False, "하루 50통 넘음")
    return (True, "")


def autoreply_log(c, owner_id: int, addr: str, mail_id: int) -> None:
    _ensure_autoreply(c)
    c.execute("INSERT INTO mail_autoreply_log(user_id, addr, mail_id) VALUES(?,?,?)", (owner_id, (addr or "").lower(), mail_id))


def search_contacts(c, q: str, limit: int = 8, user=None, browse: bool = False):
    """전사 연락처(shared_contacts)에서 받는사람 자동완성 후보.
    (11-18) user 를 주면 연락처 공개 범위(내가 등록 · 전사 공유 · 내 부서 공유)만 — contacts._vis_clause 와 같은 규칙.
    browse=True 면 검색어 없이도 목록(📇 주소록에서 고르기)."""
    q = (q or "").strip()
    if not q and not browse:
        return []
    like = f"%{q}%"
    vsql, vargs = "", []
    if user:
        try:
            from .contacts import _vis_clause
            vsql, vargs = _vis_clause(user)
        except Exception:
            vsql, vargs = "(sc.created_by=? OR sc.visibility='company')", [user.get("id")]
    try:
        # 11-21 마 묶음 4-5 — 회사 이름이 비어 있으면 연결된 거래처 이름(같은 이름 두 사람 구분 · 한드림 → ㈜드림텍)
        try:
            _cc = {r[1] for r in c.execute("PRAGMA table_info(shared_contacts)").fetchall()}
            _co = ("COALESCE(NULLIF(sc.company,''), (SELECT cu.name FROM customers cu WHERE cu.id=sc.customer_id), '') AS company"
                   if "customer_id" in _cc else "sc.company")
        except Exception:
            _co = "sc.company"
        rows = c.execute(
            "SELECT sc.name, sc.email, " + _co + ", sc.position FROM shared_contacts sc "
            "WHERE sc.email IS NOT NULL AND sc.email<>'' "
            + ("AND (sc.name LIKE ? OR sc.email LIKE ? OR sc.company LIKE ?) " if q else "")
            + (("AND " + vsql + " ") if vsql else "")
            + "ORDER BY " + ("sc.name" if q else "sc.company COLLATE NOCASE, sc.name COLLATE NOCASE") + " LIMIT ?",
            ([like, like, like] if q else []) + vargs + [int(limit) * 3],
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
    # 11-19 대표 「1단계」 — 자동완성 후보에 사내 직원 · 내가 메일을 주고받은 사람도(연락처에 없어도)
    #   찾는 낱말이 있을 때만 · 내 메일함 것만(남의 메일함 안 봄)
    if q and not browse and len(out) < limit:
        try:
            for r in c.execute(
                    "SELECT u.name, u.email, COALESCE(t.name,'') AS team_name, COALESCE(u.rank,'') AS rank FROM users u LEFT JOIN teams t ON t.id=u.team_id "
                    "WHERE u.is_active=1 AND u.email IS NOT NULL AND u.email<>'' "
                    "AND (u.name LIKE ? OR u.email LIKE ?) ORDER BY u.name LIMIT ?", (like, like, int(limit))).fetchall():
                em = (r["email"] or "").strip()
                if em and em.lower() not in seen and "@" in em:
                    seen.add(em.lower())
                    out.append({"name": r["name"] or "", "email": em, "company": "KNK",   # 11-21 4-5 직책 + 부서(이름 표시 규칙)
                                "position": " ".join(x for x in ((r["rank"] or "").strip(), (r["team_name"] or "").strip()) if x), "src": "사내"})
                    if len(out) >= limit:
                        break
        except Exception:
            pass
    if q and not browse and user and len(out) < limit:
        try:
            for r in c.execute(
                    "SELECT from_email, MAX(from_name) AS from_name, MAX(received_at) AS t FROM mail_messages "
                    "WHERE user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0 "
                    "AND from_email<>'' AND (from_email LIKE ? OR from_name LIKE ?) "
                    "GROUP BY from_email ORDER BY t DESC LIMIT ?", (user.get("id"), like, like, int(limit) * 2)).fetchall():
                em = (r["from_email"] or "").strip()
                if em and em.lower() not in seen:
                    seen.add(em.lower())
                    out.append({"name": r["from_name"] or "", "email": em, "company": em.split("@")[-1], "position": "", "src": "주고받은 메일"})
                    if len(out) >= limit:
                        break
        except Exception:
            pass
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
    if not r:
        return None
    d = dict(r)
    # 11-23 본문 정리 — 압축해 「본문 보관함」으로 옮긴 HTML 은 여기서 풀어 채움(화면·답장·전달·번역이 그대로 돎)
    try:
        from .mail_body_pack import fill as _pack_fill
        _pack_fill(c, d)
    except Exception:
        pass
    # 11-22 예전 방식이 주소 없는 보낸 사람 머리에서 **이름을 주소 칸에** 넣은 메일(예: 「<임태훈>」) — 화면·답장에서는 이름으로 · 주소는 빈칸
    fe = (d.get("from_email") or "").strip()
    if fe and "@" not in fe:
        d["from_name"] = (d.get("from_name") or "").strip() or fe
        d["from_email"] = ""
        d["from_bad"] = fe
    elif fe:
        try:   # 11-22 우리 자료로 찾아 채운 주소 = 「추정」 표시(근거)
            from .mail_from_guess import guess_label
            d["from_guess"] = guess_label(c, d["id"], fe)
        except Exception:
            d["from_guess"] = ""
    return d


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


def _block_where(pattern, kind):
    pat = (pattern or "").strip().lower().lstrip("@")
    if kind == "domain":
        return pat, "(lower(from_email) LIKE ? OR lower(from_email) LIKE ?)", ("%@" + pat, "%." + pat)
    return pat, "lower(from_email)=?", (pat,)


def _ensure_block_moved(c):
    c.execute("""CREATE TABLE IF NOT EXISTS mail_block_moved(
        pattern TEXT NOT NULL, kind TEXT NOT NULL, mail_id INTEGER NOT NULL,
        moved_at TEXT DEFAULT (datetime('now','localtime')), PRIMARY KEY(pattern, kind, mail_id))""")


def block_preview(c, pattern, kind) -> dict:
    """11-25 대표 「ok」 — 회사 전체 차단 누르기 전에 「직원 N명 · M통이 스팸함으로」(아무것도 안 바꿈 · 숫자만)."""
    _ensure_security_cols(c)
    pat, w, args = _block_where(pattern, kind)
    if not pat:
        return {"users": 0, "mails": 0}
    r = c.execute("SELECT COUNT(DISTINCT user_id), COUNT(*) FROM mail_messages WHERE direction='in' AND is_deleted=0 "
                  "AND COALESCE(is_blocked,0)=0 AND " + w, args).fetchone()
    return {"users": r[0] or 0, "mails": r[1] or 0}


def apply_block_to_existing(c, pattern, kind) -> int:
    """차단목록 추가 시 기존 받은 메일도 소급 차단함 이동. 반환 옮긴 건수.
    11-25 — 옮긴 메일 번호를 되돌림 표(mail_block_moved)에 남김 → 차단을 풀면 restore_block_moves 로 원래 자리."""
    _ensure_security_cols(c)
    pat, w, args = _block_where(pattern, kind)
    if not pat:
        return 0
    _ensure_block_moved(c)
    ids = [r[0] for r in c.execute("SELECT id FROM mail_messages WHERE direction='in' AND is_deleted=0 "
                                   "AND COALESCE(is_blocked,0)=0 AND " + w, args).fetchall()]
    kd = "domain" if kind == "domain" else "email"
    for i in range(0, len(ids), 500):
        part = ids[i:i + 500]
        c.executemany("INSERT OR IGNORE INTO mail_block_moved(pattern, kind, mail_id) VALUES(?,?,?)", [(pat, kd, x) for x in part])
        c.execute("UPDATE mail_messages SET is_blocked=1 WHERE id IN (%s)" % ",".join("?" * len(part)), part)
    return len(ids)


def restore_block_moves(c, pattern, kind) -> int:
    """차단을 풀 때 — 그 차단으로 스팸함에 옮겼던 메일을 원래 자리로(지금도 스팸함에 있는 것만 · 사람이 다시 옮긴 건 그대로)."""
    _ensure_security_cols(c)
    _ensure_block_moved(c)
    pat = (pattern or "").strip().lower().lstrip("@")
    kd = "domain" if kind == "domain" else "email"
    ids = [r[0] for r in c.execute("SELECT mail_id FROM mail_block_moved WHERE pattern=? AND kind=?", (pat, kd)).fetchall()]
    n = 0
    for i in range(0, len(ids), 500):
        part = ids[i:i + 500]
        n += c.execute("UPDATE mail_messages SET is_blocked=0 WHERE COALESCE(is_blocked,0)=1 AND id IN (%s)"
                       % ",".join("?" * len(part)), part).rowcount
    c.execute("DELETE FROM mail_block_moved WHERE pattern=? AND kind=?", (pat, kd))
    return n


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
        if not ai_client.mail_ai_available():
            return (False, "AI 번역이 꺼져 있습니다(메일 AI = OpenAI 키 필요).")
        _p = ai_client.MAIL_AI_PROVIDER
        ok1, tsubj = ai_client.ai_translate(m.get("subject") or "", target=target, provider=_p)
        ok2, tbody = ai_client.ai_translate(m.get("body_text") or "", target=target, provider=_p)
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
def decode_guess(b) -> str:
    """글자 방식을 모르는 바이트 → UTF-8 → 한국어(cp949) → UTF-8(깨진 글자 대체) 순으로 짐작해 풂.
    HTML 이면 안의 <meta charset> 를 먼저 봄. (11-23 대표 「빈 화면 메일」)"""
    if not b:
        return ""
    if isinstance(b, str):
        return b
    b = bytes(b)
    try:
        m = re.search(rb"""charset\s*=\s*["']?\s*([A-Za-z0-9_.:\-]+)""", b[:4096])
        if m:
            return b.decode(m.group(1).decode("ascii", "ignore"), errors="replace")
    except Exception:
        pass
    for cs in ("utf-8", "cp949"):
        try:
            return b.decode(cs)
        except Exception:
            pass
    return b.decode("utf-8", errors="replace")


def _decode_part(part) -> str:
    """MIME 파트 본문을 charset 고려해 문자열로."""
    try:
        payload = part.get_payload(decode=True)
        if payload is None:
            return ""
        charset = part.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, errors="replace")
        except LookupError:
            # 11-23 모르는 글자 방식(x-unknown 등) — 예전엔 아래 except 로 빠져 풀지 않은 원문(base64 글자)이 본문이 됐음
            return decode_guess(payload)
    except Exception:
        try:
            return part.get_payload() or ""
        except Exception:
            return ""


def _sent_at(v) -> str:
    """메일 Date 머리 → 서버 시각(받은 시각과 같은 기준) 'YYYY-MM-DD HH:MM:SS'. 못 읽으면 ''. (11-23)"""
    from email.utils import parsedate_to_datetime
    try:
        d = parsedate_to_datetime(str(v or "").strip())
        if d is None:
            return ""
        if d.tzinfo is not None:
            d = d.astimezone().replace(tzinfo=None)   # 서버 시간대로(SQLite localtime 과 같은 기준)
        return d.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def arrival_at(hdr: str, sent_at: str = "") -> str:
    """메일이 우리 메일 서버(하이웍스·가비아)에 **도착한 시각** — 11-24 대표 「받은 날짜가 가져온 날짜로 기록 · 아주 중요」.
    맨 위 Received 머리(마지막으로 받은 서버가 적은 줄)의 ; 뒤 날짜 → 서버 시각 'YYYY-MM-DD HH:MM:SS'.
    없거나 못 읽으면 Date 머리(sent_at) · 그것도 없으면 '' (그때는 저장 시각).
    이상한 값(2000년 전·지금보다 10분 넘게 뒤)은 쓰지 않는다."""
    import datetime as _dt
    v = ""
    try:
        cur, lines = None, []
        for ln in (hdr or "").replace("\r\n", "\n").split("\n"):
            if ln[:1] in (" ", "\t") and cur is not None:
                cur += " " + ln.strip()
                continue
            if cur is not None:
                lines.append(cur)
            cur = ln
        if cur is not None:
            lines.append(cur)
        for ln in lines:
            if ln.split(":", 1)[0].strip().lower() == "received" and ";" in ln:
                v = _sent_at(ln.rsplit(";", 1)[1])
                break
    except Exception:
        v = ""
    now = _dt.datetime.now()
    for cand in (v, (sent_at or "").strip()[:19]):
        if not cand:
            continue
        try:
            t = _dt.datetime.strptime(cand, "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
        if t.year >= 2000 and t <= now + _dt.timedelta(minutes=10):
            return cand
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

    _hb = {"v": None}

    def _raw_field(name: str) -> str:
        """11-24 머리를 원문 바이트에서 직접(8비트 이름이 파이썬 쪽에서 \ufffd 로 깨진 경우) — UTF-8 → CP949(EUC-KR) 순."""
        if _hb["v"] is None:
            b = bytes(raw_bytes)
            cut = [i for i in (b.find(b"\r\n\r\n"), b.find(b"\n\n")) if i >= 0]
            _hb["v"] = b[:min(cut)] if cut else b[:65536]
        m = re.search(rb"(?im)^" + re.escape(name.encode()) + rb"[ \t]*:[ \t]*(.*(?:\r?\n[ \t].*)*)", _hb["v"])
        if not m:
            return ""
        val = re.sub(rb"\r?\n[ \t]+", b" ", m.group(1)).strip()
        for enc in ("utf-8", "cp949"):
            try:
                return val.decode(enc)
            except Exception:
                pass
        return val.decode("utf-8", "replace")

    def _get8(name: str) -> str:
        v = _recover8(msg.get(name, "") or "")
        if "\ufffd" in v:
            r = _raw_field(name)
            if r and "\ufffd" not in r:
                return r
        return v

    def _h(name: str) -> str:
        v = _get8(name)
        try:
            return str(make_header(decode_header(v)))
        except Exception:
            return v

    subject = _h("Subject")
    # 11-22 원문에서 주소 먼저 · (2차) From 에 주소가 없으면 Sender·Reply-To·Return-Path 에서
    try:
        _rcv = [str(x) for x in (msg.get_all("Received") or [])]
        _aur = [str(x) for x in (msg.get_all("Authentication-Results") or [])]
    except Exception:
        _rcv, _aur = [], []
    from_name, from_addr, _from_hd = parse_from_headers(_get8, _h, _rcv, _aur)
    to_addr = parseaddr(_h("To"))[1] or _h("To")
    cc = _h("Cc")
    message_id = str(msg.get("Message-ID") or msg.get("Message-Id") or "").strip().strip("<>").strip()
    # 스팸·피싱 판별 재료(2026-11-16): 메일 서버가 붙인 인증 결과 · 답장 주소
    try:
        from . import mail_guard as _mg
        _auth = _mg.parse_auth_results([_recover8(str(v)) for v in (msg.get_all("Authentication-Results") or [])])
    except Exception:
        _auth = {}
    reply_to = split_from(_recover8(msg.get("Reply-To", "") or ""), _h("Reply-To"))[1]
    # 11-19 2단계-나 — 자동으로 보낸 메일인가(부재중 자동 응답이 답하지 않게: 뉴스레터·알림·다른 자동 응답·반송)
    try:
        _as = (msg.get("Auto-Submitted") or "").strip().lower()
        _pr = (msg.get("Precedence") or "").strip().lower()
        auto_hdr = bool((_as and _as != "no") or _pr in ("bulk", "junk", "list", "auto_reply")
                        or msg.get("List-Id") or msg.get("List-Unsubscribe") or msg.get("X-Autoreply")
                        or msg.get("X-Autorespond") or msg.get("X-Auto-Response-Suppress")
                        or (msg.get("Return-Path") or "").strip() == "<>")
    except Exception:
        auto_hdr = False

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
            # 11-23 대표 「애플 영수증이 이음메일에서 빈 화면」 — 자동 발송 메일 중 본문(글·HTML) 부분에
            #   'Content-Disposition: inline'(때로 파일 이름까지)을 붙이는 곳이 꽤 있음 → 예전엔 본문을 인라인 첨부로 보내
            #   글·HTML 이 모두 비었다. 'attachment' 가 아닌 글/HTML 부분은 아직 그 종류 본문이 없으면 본문으로.
            if is_att and ctype in ("text/plain", "text/html") and "attachment" not in disp \
                    and ((ctype == "text/html" and not html) or (ctype == "text/plain" and not text)):
                is_att = False
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
                    # 11-23 'inline' 표시는 그림만 숨김(본문 속 그림) — 맥·아이폰 메일이 PDF·엑셀도 inline 으로 보내
                    #   첨부 목록에서 사라지던 것. 그림이 아닌 파일은 첨부로 보임.
                    "inline": 1 if ((("inline" in disp) and ctype.startswith("image/")) or (cid and not fn)
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
        "from_email": from_addr, "from_name": from_name, "to_email": to_addr, "to_all": _h("To"),
        "subject": subject, "text": body, "html": html, "cc": cc, "attachments": atts,
        "message_id": message_id, "auth": _auth, "reply_to": reply_to, "auto_hdr": auto_hdr,
        "raw_headers": header_block(raw_bytes),
        "sent_at": _sent_at(msg.get("Date")),
    }


# ─── 원문 머리글 보관 (11-22 대표 「메일이 왔는데 보낸 사람 메일 주소를 알 수 없는 건 너무 치명적 · 완벽하게 해결」) ──
#   까닭: 예전엔 원문을 남기지 않아, 읽기가 틀린 메일은 하이웍스 원본(POP3 는 최근 몇백 통만 보임)에서만 다시 읽을 수 있었다.
#   → 받을 때 머리글을 서버에 남긴다. 주소를 읽은 메일 = 주소 관련 머리만(작게) · **주소를 못 읽은 메일 = 머리글 전부**.
#   읽는 방식을 또 고치면 서버 안에서 바로 다시 읽어 채울 수 있다(reparse_from).
HDR_KEEP = ("from", "sender", "reply-to", "return-path", "to", "cc", "message-id", "date",
            "x-original-from", "x-sender", "x-original-sender", "resent-from", "envelope-from", "x-envelope-from",
            "authentication-results",   # 11-27 메일 서버 확인 결과 줄(회사 주소 위조 판정을 운영 자료로 맞추려고 · 메일 내용 아님)
            "received")   # 11-27 거쳐 온 서버 줄(서버 이름·시각만 · 메일 내용 아님) — 진짜 사내 메일이 늘 같은 길로 오는지 재 보려고
HDR_MAX = 64 * 1024


def header_block(raw) -> str:
    """원문(바이트/글) → 머리글 부분(첫 빈 줄 앞)만 글로. 64KB 까지."""
    try:
        b = raw if isinstance(raw, (bytes, bytearray)) else (raw or "").encode("utf-8", "surrogateescape")
        b = bytes(b)
        cut = [i for i in (b.find(b"\r\n\r\n"), b.find(b"\n\n")) if i >= 0]
        hb = b[:min(cut)] if cut else b[:HDR_MAX]
        return hb[:HDR_MAX].decode("utf-8", "replace")
    except Exception:
        return ""


def _hdr_subset(hdr: str) -> str:
    """머리글 중 주소에 관한 것만(이어진 줄 포함)."""
    out, keep = [], False
    for ln in (hdr or "").replace("\r\n", "\n").split("\n"):
        if ln[:1] in (" ", "\t"):
            if keep:
                out.append(ln)
            continue
        nm = ln.split(":", 1)[0].strip().lower()
        keep = nm in HDR_KEEP
        if keep:
            out.append(ln)
    return "\n".join(out)


def _ensure_raw_hdr(c):
    c.execute("""CREATE TABLE IF NOT EXISTS mail_raw_headers (
        mail_id INTEGER PRIMARY KEY,
        hdr TEXT,
        full INTEGER DEFAULT 0,          -- 1 = 머리글 전부(보낸 사람 주소를 못 읽은 메일)
        from_ok INTEGER DEFAULT 1,       -- 받을 때 보낸 사람 주소를 읽었나
        created_at TEXT DEFAULT (datetime('now','localtime')))""")


def save_raw_headers(c, mail_id, hdr: str, from_ok: bool = True):
    _ensure_raw_hdr(c)
    if not hdr:
        return
    body = hdr[:HDR_MAX] if not from_ok else _hdr_subset(hdr)
    c.execute("INSERT OR REPLACE INTO mail_raw_headers(mail_id, hdr, full, from_ok) VALUES(?,?,?,?)",
              (int(mail_id), body, 0 if from_ok else 1, 1 if from_ok else 0))


def reparse_from(c, mail_id):
    """서버에 남긴 머리글로 보낸 사람을 다시 읽음 → (이름, 주소, 찾은 머리) · 머리글이 없으면 None."""
    _ensure_raw_hdr(c)
    r = c.execute("SELECT hdr FROM mail_raw_headers WHERE mail_id=?", (int(mail_id),)).fetchone()
    if not r or not (r["hdr"] or "").strip():
        return None
    p = parse_raw_email((r["hdr"] or "").rstrip("\r\n") + "\r\n\r\n") or {}
    return ((p.get("from_name") or "").strip(), (p.get("from_email") or "").strip(), "원문 머리글")


# ─── 첨부 저장·조회 + 안전 HTML 렌더(원본처럼 보이기) ────────────────
# 첨부 바이트는 나스 파일(data/mail_att/)에 저장하고 DB엔 path 만 → DB 경량화(2026-08-30 대표 지시).
# 마이그 전/폴백은 DB(mail_attachments.data BLOB). get_attachment 가 path 우선·없으면 BLOB.
_ATT_STORE_MAX = 12 * 1024 * 1024   # 12MB/건


def _att_dir():
    """첨부 파일 저장 폴더(나스·DB 옆 data/mail_att/)."""
    from .database import DB_PATH
    return os.path.join(os.path.dirname(DB_PATH), "mail_att")


def _att_sha256(data: bytes) -> str:
    """첨부 바이트의 내용 지문(sha256) — 같은 내용 = 같은 지문(중복 판별용, 대표 확정 2026-08-31)."""
    return hashlib.sha256(data).hexdigest()


def _content_att_path(sha: str) -> str:
    """내용주소 저장 경로: data/mail_att/sha256/<앞2글자>/<전체해시>.
    같은 내용은 항상 같은 경로 → 물리 파일 1개만(중복제거). 앞2글자=폴더 분산(한 폴더 과밀 방지)."""
    return os.path.join(_att_dir(), "sha256", sha[:2], sha)


_ATT_COLS_OK = False


def _ensure_att_cols(c):
    """mail_attachments 에 sha256 컬럼/인덱스 보장(idempotent, 프로세스당 1회)."""
    global _ATT_COLS_OK
    if _ATT_COLS_OK:
        return
    try:
        c.execute("ALTER TABLE mail_attachments ADD COLUMN sha256 TEXT")
    except Exception:
        pass
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_mailatt_sha ON mail_attachments(sha256)")
    except Exception:
        pass
    _ATT_COLS_OK = True


def _write_content_file(p: str, data: bytes) -> bool:
    """내용해시 파일을 원자적으로 기록(임시파일→rename). 이미 있고 크기 같으면 안 씀(중복제거).
    반환 True=파일 최종 존재(신규 기록 or 기존 재사용). 실패 시 False.
    ⭐파일 삭제는 어디서도 하지 않음 → 여러 메일이 한 파일 공유해도 서로 깨질 위험 0(고아만 남을 뿐)."""
    try:
        if os.path.exists(p) and os.path.getsize(p) == len(data):
            return True                     # 같은 내용 이미 있음 → 재사용(중복제거)
        d = os.path.dirname(p)
        os.makedirs(d, exist_ok=True)
        import tempfile
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp, p)              # 원자적 교체(동시 기록·중단 안전)
        except Exception:
            try:
                os.remove(tmp)
            except Exception:
                pass
            raise
        return True
    except Exception:
        return False


def _save_attachments(c, mail_id: int, attachments) -> None:
    """파싱된 첨부 리스트를 저장(인라인 포함). 바이트는 나스 파일(내용해시 경로)로, DB엔 경로+지문만.
    ⭐내용해시 저장 = 같은 내용은 물리 파일 1개만(중복제거·대표 확정 2026-08-31). 여러 메일이 그 파일을 참조.
    파일명·mime 는 첨부 행마다 그대로(같은 물리파일이라도 메일별 원래 이름으로 표시)."""
    _ensure_att_cols(c)
    for a in (attachments or []):
        try:
            data = a.get("data") or b""
            keep = bool(data and len(data) <= _ATT_STORE_MAX)
            sha = None
            p = None
            if keep:
                sha = _att_sha256(data)
                if _write_content_file(_content_att_path(sha), data):
                    p = _content_att_path(sha)   # 파일 확보 성공 시에만 경로 기록
            # 파일 기록 실패(디스크 등) 시 데이터 손실 방지: 그 건만 예외적으로 BLOB 저장(폴백).
            _blob = data if (keep and p is None) else None
            c.execute(
                """INSERT INTO mail_attachments
                   (mail_id, filename, mime, size, content_id, is_inline, data, path, sha256)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (mail_id, (a.get("filename") or "")[:255], (a.get("mime") or "")[:120],
                 int(a.get("size") or 0), (a.get("content_id") or "")[:255],
                 1 if a.get("inline") else 0, _blob, p, sha),
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
    """첨부 1건의 바이트(소유권 강제: 메일 소유자만). 나스 파일(path) 우선, 없으면 DB(data) 폴백.
    둘 다 없으면 None. (파일 우선 덕분에 마이그 전 기존 첨부는 BLOB 로 그대로 열림.)"""
    r = c.execute(
        "SELECT a.filename, a.mime, a.data, a.path FROM mail_attachments a "
        "JOIN mail_messages m ON m.id = a.mail_id "
        "WHERE a.id=? AND m.user_id=? AND m.is_deleted=0",
        (att_id, user_id),
    ).fetchone()
    if not r:
        return None
    data = None
    if r["path"]:
        try:
            with open(r["path"], "rb") as f:
                data = f.read()
        except Exception:
            data = None
    if data is None:
        data = r["data"]   # 마이그 전/폴백: DB BLOB
    if data is None:
        return None
    return {"filename": r["filename"] or "attachment",
            "mime": r["mime"] or "application/octet-stream", "data": data}


# ─── 🔒 읽기 전용 조회 도우미 (AI 비서 '락아' 용 · 대표 지시 2026-11-09) ──────
# 아래 둘은 '순수 함수'라 앱을 띄우지 않고도 시험할 수 있다 — 보안 핵심이라 반드시 시험한다.

def ro_allowed(user) -> bool:
    """메일 읽기 전용 조회를 쓸 수 있는 사람 — 지금은 김정락 대표 한 명(사번 5 / login_id 'kjr').
    ※ ceo 역할 계정이 둘이라(z411 선례) role 로 막지 않고 본인만 정확히 지정한다.
    넓힐 일이 생기면 이 함수 한 곳만 고치면 된다."""
    if not isinstance(user, dict):
        return False
    empno = str(user.get("employee_no") or "").strip()
    login = str(user.get("login_id") or "").strip().lower()
    return empno == "5" or login == "kjr"


# 바깥(http(s)) 으로 자동 요청이 나가는 참조만 고른다. cid: 와 우리 서버 상대경로(/mail/...)는 남긴다.
_RO_REMOTE_ATTR = re.compile(r'''(?is)\s(?:src|background|poster)\s*=\s*["\']?\s*(?:https?:)?//[^\s"\'>]*["\']?''')
_RO_REMOTE_CSSURL = re.compile(r"""(?is)url\(\s*["']?\s*(?:https?:)?//[^)]*\)""")


def strip_remote_refs(html: str) -> str:
    """추적 픽셀·원격 이미지가 '열리지 않게' 바깥 참조를 떼어낸다.
    화면용 sanitize_html_for_view 는 원본 충실도를 위해 원격 이미지를 허용하지만,
    읽기 전용(락아)은 내용을 읽는 게 목적이라 바깥으로 나가는 요청을 만들지 않는다."""
    if not html:
        return ""
    s = _RO_REMOTE_ATTR.sub(' data-knk-remote-removed="1"', html)
    s = _RO_REMOTE_CSSURL.sub("none", s)
    return s


def html_has_content(h: str) -> bool:
    """정리한 HTML 에 화면에 보일 것(글자·그림)이 있나 — 없으면 글 본문으로 보여 줌(빈 칸 대신)."""
    if not (h or "").strip():
        return False
    if re.search(r"(?is)<img\b", h):
        return True
    t = re.sub(r"(?is)<(style|title|head)\b.*?</\1>", " ", h)
    t = re.sub(r"(?s)<[^>]+>|&nbsp;|&#160;|\s", "", t)
    return bool(t)


_ATT_NOTE_RE = re.compile(r"\s*\[첨부 \d+개:[^\]]*\]\s*$")


def inline_is_file(a) -> bool:
    """예전에 받은 메일의 '인라인' 첨부 중 실은 파일(그림·본문 글이 아닌 것 — PDF·엑셀 등)인가. 보기 때 첨부 목록에 보임."""
    mime = (a.get("mime") or "").lower()
    return bool(a.get("is_inline")) and not mime.startswith("image/") and mime not in ("text/html", "text/plain")


def view_body_fallback(c, m, all_atts):
    """11-23 대표 「애플 영수증이 빈 화면」 — 예전(고치기 전)에 받은 메일 중 본문이 '인라인 첨부'로 잘못 저장된 것은
    서버에 그 부분(text/html · text/plain)이 그대로 있다 → 보기 때 그것을 본문으로 꺼내 보여 줌(DB 는 바꾸지 않음).
    반환 (html, text, 본문으로 쓴 첨부 번호들). 쓸 것이 없으면 번호 목록은 비어 있음."""
    html = (m.get("body_html") or "") if m else ""
    text = (m.get("body_text") or "") if m else ""
    used = []

    def _read(aid):
        try:
            r = c.execute("SELECT data, path FROM mail_attachments WHERE id=?", (aid,)).fetchone()
        except Exception:
            return b""
        if not r:
            return b""
        if r["path"]:
            try:
                with open(r["path"], "rb") as f:
                    return f.read()
            except Exception:
                pass
        return r["data"] or b""

    inl = [a for a in (all_atts or []) if a.get("is_inline")]
    if not html.strip():
        ha = next((a for a in inl if (a.get("mime") or "").lower() == "text/html"), None)
        if ha:
            b = _read(ha["id"])
            if b:
                html = decode_guess(b)
                used.append(ha["id"])
    if not _ATT_NOTE_RE.sub("", text).strip():
        ta = next((a for a in inl if (a.get("mime") or "").lower() == "text/plain"), None)
        if ta:
            b = _read(ta["id"])
            if b:
                note = _ATT_NOTE_RE.search(text)
                text = decode_guess(b).strip() + (("\n\n" + note.group(0).strip()) if note else "")
                used.append(ta["id"])
        elif html.strip() and used:
            note = _ATT_NOTE_RE.search(text)
            text = _html_to_text(html) + (("\n\n" + note.group(0).strip()) if note else "")
    return html, text, used


_URL_ATTR_RE = re.compile(r"(?is)\b(href|src|action|formaction|xlink:href|background|poster|dynsrc|lowsrc)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))")
_BAD_URL_HEADS = ("javascript:", "vbscript:", "livescript:", "data:text/html", "data:application/", "data:text/xml")


def _defuse_url_attrs(s: str) -> str:
    """11-26 — 주소 칸(href·src 등)의 javascript:·vbscript:·HTML 데이터 주소를 「#」으로.
    따옴표 없는 값 · 글자 숨김(&#106; · 탭·줄바꿈 끼우기)도 풀어서 본다(전에는 따옴표 있고 그대로 쓴 javascript: 만)."""
    import html as _h

    def _one(mm):
        v = next((g for g in (mm.group(2), mm.group(3), mm.group(4)) if g is not None), "")
        dv = re.sub(r"[\s\x00-\x20]+", "", _h.unescape(_h.unescape(v))).lower()
        if dv.startswith(_BAD_URL_HEADS):
            return mm.group(1) + '="#"'
        return mm.group(0)
    return _URL_ATTR_RE.sub(_one, s)


def sanitize_html_for_view(html: str, mail_id: int, inline_atts, defang: bool = False) -> str:
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
    # 11-23 대표 「빈 화면 메일」: 예전엔 <form>…</form>·<noscript>…</noscript> 를 내용째 지워, 본문 전체를 <form> 으로
    #   감싼 영수증(단추 있는 메일)이 통째로 사라졌다 → 이 둘은 아래에서 태그만 뗀다(스크립트는 이미 지움 · 단추·입력칸도 지움).
    #   스스로 닫는 <svg/>·<math/> 는 먼저 지움(안 그러면 뒤쪽 </svg> 까지 본문을 함께 지웠음) · <embed> 는 닫는 태그가 없는 태그.
    s = re.sub(r"(?is)<\s*(svg|math)\b[^>]*/\s*>", " ", s)
    s = re.sub(r"(?is)<\s*(script|iframe|object|applet|svg|math)\b.*?<\s*/\s*\1\s*>", " ", s)
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
    #   11-26 — 앞이 빈칸이 아닌 경우(빗금·따옴표 바로 뒤)도 같이 지움 · 답장·전달 쓰기 화면도 이 결과를 씀
    #   브라우저는 태그 이름 바로 뒤·따옴표 바로 뒤의 빗금(/)을 빈칸처럼 읽는다 → 그 빗금만 빈칸으로(주소 값 속 빗금은 그대로)
    s = re.sub(r"(?is)(<[a-z][a-z0-9:-]*|[\"'`])/+(?=\s*on[a-z]+\s*=)", r"\1 ", s)
    s = re.sub(r"(?is)(?<=[\s\"'`])on[a-z]+\s*=\s*(\"[^\"]*\"|'[^']*'|`[^`]*`|[^\s>]+)", " ", s)
    s = _defuse_url_attrs(s)

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
    if defang:
        # 의심·위험 메일: 링크를 누를 수 없게(실제 주소는 마우스를 올리면 보임) — 2026-11-16
        try:
            from . import mail_guard as _mg
            s = _mg.defang_links_html(s)
        except Exception:
            pass
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


LARGE_DAY_MAX_N = 20                       # 11-27 한 사람 하루 큰 파일 개수
LARGE_DAY_MAX_BYTES = 3 * 1024 ** 3        # 11-27 한 사람 하루 합계 3GB
LARGE_PURGE_GRACE_DAYS = 7                 # 기한이 지나고 이만큼 더 지나면 파일을 지움(표의 줄은 남김)


def large_today(c, user_id) -> tuple:
    """오늘(한국시간 날짜) 이 사람이 올린 큰 파일 (개수, 합계 바이트)."""
    r = c.execute("SELECT COUNT(*), COALESCE(SUM(size),0) FROM mail_large_files "
                  "WHERE uploaded_by=? AND date(created_at)=date('now','localtime')", (user_id,)).fetchone()
    return (int(r[0] or 0), int(r[1] or 0))


def purge_expired_large(session) -> int:
    """기한이 지나고 LARGE_PURGE_GRACE_DAYS 일 더 지난 큰 파일을 디스크에서 지움 — 표의 줄은 남김(path 만 비움).
    큰 파일 보관 폴더 안의 것만 지운다. 반환 = 지운 파일 수."""
    import shutil
    root = os.path.realpath(_large_root())
    with session() as c:
        rows = c.execute("SELECT id, token, path FROM mail_large_files WHERE expires_at IS NOT NULL "
                         "AND COALESCE(path,'')<>'' AND datetime('now','localtime') > datetime(expires_at, ?)",
                         ("+%d days" % LARGE_PURGE_GRACE_DAYS,)).fetchall()
    n = 0
    for r in rows:
        d = os.path.realpath(large_file_dir(r["token"]))
        if not d.startswith(root + os.sep):
            print("[MAIL-LARGE] 보관 폴더 밖 경로라 건너뜀: %s" % r["id"], flush=True)
            continue
        try:
            shutil.rmtree(d, ignore_errors=True)
            with session() as c:
                c.execute("UPDATE mail_large_files SET path='' WHERE id=?", (r["id"],))
            n += 1
        except Exception as _e:
            print("[MAIL-LARGE] 지우기 실패 %s: %s" % (r["id"], str(_e)[:120]), flush=True)
    return n


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


_LARGE_DL_OK = set()
LARGE_DL_KEEP = 200     # 한 파일에 시각 기록은 200줄까지(처음 것 + 최근 것 · 횟수는 따로 다 셈 — 표가 끝없이 커지지 않게)


def ensure_large_dl(c):
    """⑦ 큰 파일 받아 간 시각(11-20 2단계) — 링크 번호 · 시각만(받아 간 사람의 주소·IP·브라우저는 적지 않음)."""
    try:
        k = c.execute("PRAGMA database_list").fetchone()[2] or ("mem:%x" % id(c))
    except Exception:
        k = "?"
    if k in _LARGE_DL_OK:
        return
    c.execute("CREATE TABLE IF NOT EXISTS mail_large_dl(id INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT NOT NULL, "
              "at TEXT DEFAULT (datetime('now','localtime')))")
    c.execute("CREATE INDEX IF NOT EXISTS idx_mail_large_dl_tk ON mail_large_dl(token, id)")
    _LARGE_DL_OK.add(k)


def bump_large_download(c, token: str) -> None:
    try:
        c.execute("UPDATE mail_large_files SET download_count = download_count + 1 WHERE token=?",
                  (token,))
    except Exception:
        pass
    try:   # 11-20 2단계 ⑦ — 받아 간 시각(서버 시각 · 보여 줄 때 보는 사람 소속 시각으로 바꿈)
        ensure_large_dl(c)
        c.execute("INSERT INTO mail_large_dl(token) VALUES(?)", (token,))
        n = c.execute("SELECT COUNT(*) FROM mail_large_dl WHERE token=?", (token,)).fetchone()[0]
        if int(n or 0) > LARGE_DL_KEEP:   # 처음 것과 최근 것은 남기고 그 사이 오래된 것부터 지움
            c.execute("DELETE FROM mail_large_dl WHERE id=(SELECT id FROM mail_large_dl WHERE token=? ORDER BY id LIMIT 1 OFFSET 1)", (token,))
    except Exception as e:
        print("[MAIL-LARGE] 받아 간 시각 기록 실패: %s" % type(e).__name__, flush=True)


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
