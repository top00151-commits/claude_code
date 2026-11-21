# -*- coding: utf-8 -*-
"""④ 회신 필요(추정) — 규칙으로만 판단(AI·외부 전송 없음 · 메일 속 링크 접속 없음).

대표 지시(2026-11-17 「규칙으로 먼저 만들어」): 회신해야 하는 메일을 표시하고 중요도를 함께.
판단 재료 = 보낸 사람이 **이번에 직접 쓴 부분**(답장으로 딸려 온 옛 글은 뺌)의 요청·질문 문구 + 제목.
빼는 것 = 광고·알림·자동 발송 · 피싱 의심 · 이미 내가 답장한 메일 · 같은 대화의 더 새 메일이 있는 옛 메일 · 오래된 메일.
사람이 고칠 수 있게: 「회신 안 해도 됨」(끄기) / 「회신 필요로 표시」(켜기) — 본인에게만(mail_reply_marks).
"""
import re

_CACHE = {}               # (메일 번호, 제목, 분류, 위험도, 거래처 여부) → assess 결과
REPLY_DAYS = 14            # 최근 며칠 메일만 「회신 필요」로 본다(옛 메일 수천 통이 한꺼번에 뜨지 않게)
SCAN_LIMIT = 3000          # 그 기간에서 훑는 최대 통수(화면 속도)
OUR_DOMAINS = ("knknara.co.kr",)

# ── 문구 규칙 ────────────────────────────────────────────────────────────────
# 강한 요청: 「회신/검토/확인… + 부탁·요청·바랍니다·주세요」 · 「~해 주시기 바랍니다」 · 「…까지 회신」
_RE_STRONG = re.compile(
    r"((회신|답신|답변|답장|피드백|의견|확인|검토|승인|결재|컨펌|회람|재가|조치|처리)\s*(을|를|이|가|좀|해|하여|후|하신\s*후)?\s*"
    r"(부탁|요청|바랍|바람|주시|주십시오|주세요|해\s*주|요망|필요\s*합니다|드려도\s*될까)"
    r"|(알려|보내|전달|송부|공유|제출|검토|확인|처리|진행|준비|회신|답변|결정|지시|승인|결재|검토해)\s*(해|하여)?\s*"
    r"(주시기|주십시오|주세요|주실|주시면|줄\s*수|주시겠|주셨으면|주시길)"
    r"|까지\s*(회신|답변|답장|송부|전달|제출|확인|보내|알려|결정)"
    r"|요청\s*(드립니다|드려요|합니다|드리오니|드리며|드려|사항)"
    r"|(please|pls|kindly)\s+(confirm|advise|reply|respond|let|send|check|review|provide|update|share|approve|quote|"
    r"arrange|revert|feedback|sign|proceed|inform|note\s+and\s+confirm)"
    r"|could\s+you|can\s+you|would\s+you|let\s+(me|us)\s+know|look(ing)?\s+forward\s+to\s+(your|hearing)"
    r"|await(ing)?\s+your|at\s+your\s+earliest|your\s+(confirmation|reply|feedback|approval)\s+(is|would)"
    r"|vui\s+lòng|xin\s+vui\s+lòng|phản\s+hồi|xác\s+nhận\s+giúp|nhờ\s+(anh|chị)|giúp\s+em)", re.I)
# 지시 말투 — 2026-11-21 대표 「신입사원 관점」 나 묶음 3-1 · **사내 메일에만**(광고의 「지금 신청하세요」 같은 것을 잘못 잡지 않게)
#   「제출 바랍니다」「준비하세요」「진행 바랍니다」「보고할 것」「보고해 주세요」「처리해」「가져와요」
_DIR_VERB = (r"(제출|준비|진행|보고|처리|정리|작성|검토|확인|송부|전달|공유|회신|조치|점검|파악|수정|보완|완료|마무리|"
             r"등록|입력|발행|협의|조율|연락|문의|요청|챙겨|참석|출장|방문|업데이트|체크|정산|결재\s*올려|올려|보내|가져와|가져오|챙기)")
_RE_DIRECTIVE = re.compile(
    _DIR_VERB + r"\s*(을|를|도|좀)?\s*"
    r"(하세요|하십시오|하시오|하시기\s*바랍|해\s*주세요|해\s*주십시오|해\s*주시기|해\s*주시길|해\s*주시고|해\s*줘|해\s*주라|해라|"
    r"하도록\s*(하세요|해|합시다|바랍)|할\s*것|바랍니다|바람|바라며|요망|부탁\s*(합니다|드립니다|해요)?|"
    r"세요|십시오|주세요|요(?=\s*[.!~\n]|\s*$)|해요(?=\s*[.!~\n]|\s*$)|해(?=\s*[.!~\n]|\s*$))", re.M)
# 「보고 드립니다」「진행 중입니다」「처리했습니다」처럼 내가 한 일을 알리는 말은 지시가 아님 — 위 규칙이 말끝으로 가름
# 인사말(「좋은 하루 보내세요」「건강 챙기세요」)은 지시가 아님 — 바로 앞 말로 뺀다
_RE_GREET_BEFORE = re.compile(r"(하루|주말|휴일|연휴|휴가|명절|한\s*주|저녁|오후|시간|밤|연말|새해|추석|설|건강|감기|몸)\s*(잘|즐겁게|편히|편안히|행복하게|도)?\s*$")


def _directive(own: str):
    for md in _RE_DIRECTIVE.finditer(own):
        if _RE_GREET_BEFORE.search(own[max(0, md.start() - 12):md.start()]):
            continue
        return md
    return None
# 질문: 묻는 말끝
_RE_QUESTION = re.compile(
    r"(할까요|될까요|있을까요|좋을까요|어떨까요|가능할까요|가능한지|가능하신지|가능하실까요|되나요|되는지요|인가요|"
    r"있나요|없나요|맞나요|맞는지|맞습니까|어떠신지|어떻습니까|어떻게\s*(할까|하면|해야|진행)|인지요|하실지|주실\s*수\s*있|"
    r"계신가요|하셨나요|받으셨나요|받으셨는지|보셨나요|아시나요)", re.I)
# 「참고하세요」류 — 이것만 있으면 회신 필요 아님
_RE_FYI = re.compile(
    r"(참고\s*(바랍|하시기|부탁|해\s*주|용|자료)|공유\s*드립|보고\s*드립|알려\s*드립|안내\s*드립|공지|for\s+your\s+(information|reference)|\bFYI\b)",
    re.I)
# 「답장 필요 없음」을 분명히 적은 것
_RE_NO_REPLY = re.compile(
    r"(회신\s*(은|은\s*)?(불필요|필요\s*없|하지\s*않으셔도|안\s*하셔도|생략)|답장\s*(은\s*)?(불필요|필요\s*없|안\s*하셔도)|"
    r"no\s+(action|reply|response)\s+(is\s+)?(needed|required)|do\s+not\s+reply|no\s+need\s+to\s+reply)", re.I)
# 제목만으로 요청인 것
_RE_SUBJ_REQ = re.compile(
    r"(요청|문의|검토\s*부탁|승인\s*요청|결재\s*요청|회신\s*요망|회신\s*바랍|확인\s*요청|견적\s*요청|협조\s*요청|"
    r"\bRFQ\b|\bRFI\b|request|inquiry|enquiry|question|please\s+(confirm|advise)|yêu\s+cầu|hỏi)", re.I)
# 사람이 쓰지 않은 메일(자동 응답·배달 실패·읽음 확인)
_RE_AUTO_SUBJ = re.compile(
    r"^\s*(자동\s*회신|자동\s*응답|부재\s*중|부재중|automatic\s+reply|auto(matic)?[-\s]?reply|out\s+of\s+(the\s+)?office|"
    r"undeliverable|undelivered|delivery\s+(status|failure)|mail\s+delivery|배달\s*(실패|안\s*됨)|전송\s*실패|"
    r"읽음\s*확인|read\s*:|수신\s*확인|returned\s+mail)", re.I)
_RE_AD_SUBJ = re.compile(r"[\(\[（]\s*(광고|AD)\s*[\)\]）]", re.I)
_RE_UNSUB = re.compile(r"(수신\s*거부|수신을\s*원(치|하지)|구독\s*취소|unsubscribe|opt[-\s]?out)", re.I)
_RE_URGENT = re.compile(
    r"(긴급|급히|급합니다|급한|시급|지급으로|오늘\s*(중|까지|안)|금일|내일\s*(오전|오후)?\s*(\d{1,2}\s*시\s*)?까지|ASAP|urgent|"
    r"as\s+soon\s+as\s+possible|마감|deadline|khẩn)", re.I)
_RE_URL = re.compile(r"(https?://|www\.)\S+", re.I)
_RE_SUBJ_PREFIX = re.compile(r"^\s*(re|회신|답장|답신|fwd?|fw|전달)\s*[:：]\s*", re.I)
_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def norm_subject(s: str) -> str:
    s = (s or "").strip()
    prev = None
    while s and s != prev:
        prev = s
        s = _RE_SUBJ_PREFIX.sub("", s, count=1).strip()
    return re.sub(r"\s+", " ", s).strip().lower()


def _short(m) -> str:
    t = re.sub(r"\s+", " ", m.group(0)).strip()
    return t[:24]


def _is_robot(addr: str) -> bool:
    try:
        from . import mail_cleanup as _mc
        local = (addr or "").split("@")[0]
        return bool(_mc._RE_ROBOT.match(local))
    except Exception:
        return False


def _is_internal(addr: str) -> bool:
    """우리 회사 주소(사내 직원)에서 온 메일 — 지시 말투 규칙은 여기에만."""
    a = (addr or "").strip().lower()
    return "@" in a and a.rsplit("@", 1)[-1] in OUR_DOMAINS


def _own(text: str) -> str:
    try:
        from . import mail_signature as _ms
        own = _ms.own_part(text or "")
    except Exception:
        own = text or ""
    return own[:6000]


def assess(*, subject: str = "", body: str = "", from_email: str = "", category: str = "",
           risk_level: int = 0, partner: bool = False) -> tuple:
    """한 통 판단. 반환 (lv, reasons) — lv 0 = 표시 안 함 · 1 = 회신 필요(보통) · 2 = 회신 필요(높음).
    partner = 거래처(주소록에 거래처와 함께 있거나 같은 회사 주소)에서 온 메일."""
    subj = subject or ""
    addr = (from_email or "").strip().lower()
    if not addr or (risk_level or 0) >= 2:
        return 0, []
    if _RE_AUTO_SUBJ.search(subj) or _RE_AD_SUBJ.search(subj) or _is_robot(addr):
        return 0, []
    full = body or ""
    if _RE_UNSUB.search(full[-2500:]):
        return 0, []
    own = _RE_URL.sub(" ", _own(full))
    if _RE_NO_REPLY.search(own) or _RE_NO_REPLY.search(subj):
        return 0, []
    reasons = []
    m = _RE_STRONG.search(own)
    if m:
        reasons.append("「%s」" % _short(m))
    if not reasons and _is_internal(addr):
        md = _directive(own)
        if md:
            reasons.append("사내 지시 「%s」" % _short(md))
    # 제목만으로 보는 것은 처음 온 메일만 — RE:/FW: 메일의 제목은 앞사람(우리일 수도)의 요청이라 이번 글의 뜻이 아님
    ms = None if _RE_SUBJ_PREFIX.match(subj) else _RE_SUBJ_REQ.search(norm_subject(subj))
    if ms and not reasons:
        reasons.append("제목 「%s」" % _short(ms))
    if not reasons:
        mq = _RE_QUESTION.search(own)
        if mq:
            reasons.append("묻는 말 「%s」" % _short(mq))
        elif "?" in own or "？" in own:
            reasons.append("물음표(?)가 있는 글")
    if not reasons:
        return 0, []
    # 「참고 바랍니다」만 있고 요청이 약하면(물음표 하나뿐) 빼기
    if _RE_FYI.search(own) and reasons[0].startswith("물음표"):
        return 0, []
    lv = 1
    mu = _RE_URGENT.search(own) or _RE_URGENT.search(subj)
    if mu:
        lv = 2
        reasons.append("급함 「%s」" % _short(mu))
    if category in ("발주", "견적"):
        lv = 2
        reasons.append("%s 메일" % category)
    if partner:
        lv = 2
        reasons.append("거래처 메일")
    return lv, reasons


# ── 표시 끄기·켜기(본인에게만) ─────────────────────────────────────────────────
def ensure(c) -> None:
    c.execute("""CREATE TABLE IF NOT EXISTS mail_reply_marks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        mail_id INTEGER NOT NULL,
        state TEXT NOT NULL,                -- done(회신 안 해도 됨) / need(회신 필요로 표시)
        created_at TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(user_id, mail_id))""")


def _marks(c, user_id) -> dict:
    try:
        return {r[0]: r[1] for r in c.execute(
            "SELECT mail_id, state FROM mail_reply_marks WHERE user_id=?", (user_id,)).fetchall()}
    except Exception:
        return {}      # 표가 아직 없음(처음 쓰기 전) — 읽는 길에서는 만들지 않는다


def set_mark(c, user_id, mail_id, state: str) -> bool:
    """state: done / need / clear. 본인 받은 메일만."""
    own = c.execute("SELECT 1 FROM mail_messages WHERE id=? AND user_id=? AND direction='in'",
                    (int(mail_id), int(user_id))).fetchone()
    if not own:
        return False
    ensure(c)
    if state == "clear":
        c.execute("DELETE FROM mail_reply_marks WHERE user_id=? AND mail_id=?", (int(user_id), int(mail_id)))
    elif state in ("done", "need"):
        c.execute("INSERT INTO mail_reply_marks(user_id, mail_id, state) VALUES(?,?,?) "
                  "ON CONFLICT(user_id, mail_id) DO UPDATE SET state=excluded.state, created_at=datetime('now','localtime')",
                  (int(user_id), int(mail_id), state))
    else:
        return False
    return True


def set_done_many(c, user_id, ids) -> list:
    """11-22 대표 「회신 필요 일괄 처리」 — 여러 통을 한 번에 「회신 안 해도 됨」. 본인 받은 메일만.
    반환 [(mail_id, 바꾸기 전 표시('' = 규칙대로 · 'need'))] — ↺ 되돌리기가 그대로 쓴다. 이미 「안 해도 됨」인 것은 뺀다."""
    nums = []
    for x in list(ids or [])[:5000]:
        try:
            nums.append(int(x))
        except Exception:
            pass
    if not nums:
        return []
    ensure(c)
    marks = _marks(c, user_id)
    own = []
    for i in range(0, len(nums), 400):
        chunk = nums[i:i + 400]
        own += [r[0] for r in c.execute("SELECT id FROM mail_messages WHERE user_id=? AND direction='in' AND id IN ("
                                        + ",".join("?" * len(chunk)) + ")", (int(user_id), *chunk)).fetchall()]
    out = []
    for mid in own:
        prev = marks.get(mid) or ""
        if prev == "done":
            continue
        c.execute("INSERT INTO mail_reply_marks(user_id, mail_id, state) VALUES(?,?, 'done') "
                  "ON CONFLICT(user_id, mail_id) DO UPDATE SET state='done', created_at=datetime('now','localtime')",
                  (int(user_id), int(mid)))
        out.append((mid, prev))
    return out


def restore_marks(c, user_id, items) -> int:
    """↺ 되돌리기 — [(mail_id, 바꾸기 전 표시)] 를 그대로 돌려놓는다(지금 「안 해도 됨」인 것만 · 본인 것만)."""
    ensure(c)
    n = 0
    for mid, prev in list(items or [])[:5000]:
        try:
            mid = int(mid)
        except Exception:
            continue
        cur = c.execute("SELECT state FROM mail_reply_marks WHERE user_id=? AND mail_id=?", (int(user_id), mid)).fetchone()
        if not cur or cur[0] != "done":
            continue
        if prev == "need":
            c.execute("UPDATE mail_reply_marks SET state='need' WHERE user_id=? AND mail_id=?", (int(user_id), mid))
        else:
            c.execute("DELETE FROM mail_reply_marks WHERE user_id=? AND mail_id=?", (int(user_id), mid))
        n += 1
    return n


# ── 거래처 판단 재료 ───────────────────────────────────────────────────────────
def _partner_keys(c) -> tuple:
    """(거래처와 연결된 연락처 주소, 한 거래처만 가리키는 회사 주소)."""
    emails, doms = set(), set()
    try:
        for r in c.execute("SELECT lower(email) FROM shared_contacts WHERE email IS NOT NULL AND customer_id IS NOT NULL").fetchall():
            if r[0]:
                emails.add(r[0].strip())
    except Exception:
        pass
    try:
        from .mail_store import _CUST_DOMAIN_MAP_SQL
        for r in c.execute(_CUST_DOMAIN_MAP_SQL).fetchall():
            doms.add(r[0])
    except Exception:
        pass
    return emails, doms


def _is_partner(addr, emails, doms) -> bool:
    a = (addr or "").strip().lower()
    return a in emails or (a.rsplit("@", 1)[-1] in doms if "@" in a else False)


def _replied_index(c, user_id, since: str) -> dict:
    """내가 보낸 메일: 받는 주소 → [(정리한 제목, 보낸 시각)]."""
    idx = {}
    for r in c.execute("SELECT to_email, cc, subject, received_at FROM mail_messages "
                       "WHERE user_id=? AND direction='out' AND received_at>=? ORDER BY id DESC LIMIT 5000",
                       (user_id, since)).fetchall():
        ns = norm_subject(r["subject"])
        for e in set(_RE_EMAIL.findall(((r["to_email"] or "") + " " + (r["cc"] or "")).lower())):
            idx.setdefault(e, []).append((ns, r["received_at"] or ""))
    return idx


def _prep(c) -> None:
    """받은편지함 목록(list_inbox)과 같은 준비 — 위험도·차단 칸이 없는 옛 DB 에서도 판단이 멈추지 않게."""
    try:
        from .mail_store import _ensure_security_cols
        _ensure_security_cols(c)
    except Exception:
        pass


def scan(c, user_id, days: int = REPLY_DAYS) -> dict:
    """최근 메일 중 회신 필요(추정)를 찾는다. 반환 {mail_id: {"lv", "why", "manual"}} — 화면이 그대로 쓴다.
    「회신 안 해도 됨」으로 끈 것은 빠지고, 「회신 필요로 표시」한 것은 기간·규칙과 상관없이 들어간다(답장하면 빠짐)."""
    user_id = int(user_id)
    _prep(c)
    try:   # (11-18 3단계) 📦 보관 칸이 없으면 먼저 만든다
        from .mail_store import _ensure_security_cols
        _ensure_security_cols(c)
    except Exception:
        pass
    since_row = c.execute("SELECT datetime('now','localtime', ?)", ("-%d days" % int(days),)).fetchone()
    since = since_row[0] if since_row else ""
    marks = _marks(c, user_id)
    need_ids = [k for k, v in marks.items() if v == "need"]
    rows = c.execute(
        "SELECT id, from_email, subject, category, COALESCE(risk_level,0) AS risk_level, received_at "
        "FROM mail_messages "
        "WHERE user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0 AND received_at>=? "
        "AND COALESCE(is_archived,0)=0 "   # 📦 보관한 메일 = 다 본 메일 → 회신 필요에서 뺀다(11-18)
        "ORDER BY received_at DESC, id DESC LIMIT ?", (user_id, since, SCAN_LIMIT)).fetchall()
    rows = [dict(r) for r in rows]
    have = {r["id"] for r in rows}
    if need_ids:
        extra = [i for i in need_ids if i not in have][:500]
        if extra:
            q = ",".join("?" * len(extra))
            for r in c.execute(
                    "SELECT id, from_email, subject, category, COALESCE(risk_level,0) AS risk_level, received_at "
                    "FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 "
                    "AND id IN (" + q + ")", (user_id, *extra)).fetchall():
                rows.append(dict(r))
    oldest = min([r["received_at"] or "" for r in rows] or [since])
    replied = _replied_index(c, user_id, oldest or since)
    emails, doms = _partner_keys(c)
    newest_in_thread = {}
    for r in rows:      # 받은시각 내림차순 → 대화(같은 제목)의 첫 등장이 가장 새 메일
        newest_in_thread.setdefault(norm_subject(r["subject"]), r["id"])
    out, todo = {}, []
    for r in rows:
        mid = r["id"]
        st = marks.get(mid)
        if st == "done":
            continue
        addr = (r["from_email"] or "").strip().lower()
        ns = norm_subject(r["subject"])
        did_reply = any(s == ns and t > (r["received_at"] or "") for s, t in replied.get(addr, ()))
        if did_reply:
            continue
        if st == "need":
            out[mid] = {"lv": 2, "why": "직접 「회신 필요」로 표시함", "manual": True}
            continue
        if newest_in_thread.get(ns) != mid:
            continue      # 같은 대화에 더 새 메일이 있으면 그 메일에서만 판단
        todo.append((r, addr, _is_partner(addr, emails, doms)))
    # 본문 판단은 한 번 한 메일은 기억(받은 메일 본문은 바뀌지 않음) — 받은편지함을 열 때마다 본문을 다시 읽지 않게
    keyf = lambda r, part: (r["id"], r["subject"] or "", r["category"] or "", int(r["risk_level"] or 0), part)
    miss = [r["id"] for r, _a, part in todo if keyf(r, part) not in _CACHE]
    bodies = {}
    for i in range(0, len(miss), 400):
        chunk = miss[i:i + 400]
        for b in c.execute("SELECT id, substr(COALESCE(body_text,''),1,4000) AS body FROM mail_messages WHERE id IN ("
                           + ",".join("?" * len(chunk)) + ")", chunk).fetchall():
            bodies[b["id"]] = b["body"]
    if len(_CACHE) > 30000:
        _CACHE.clear()
    for r, addr, part in todo:
        k = keyf(r, part)
        if k not in _CACHE:
            _CACHE[k] = assess(subject=r["subject"], body=bodies.get(r["id"], ""), from_email=addr,
                               category=r["category"], risk_level=r["risk_level"], partner=part)
        lv, reasons = _CACHE[k]
        if lv:
            out[r["id"]] = {"lv": lv, "why": " · ".join(reasons + ["아직 답장 안 함"]), "manual": False}
    return out


def one(c, user_id, mail_id) -> dict:
    """읽기 화면용 한 통 상태(이 메일만 판단 — 목록 훑기와 같은 규칙). {"lv", "why", "state"} — state: done/need/None."""
    user_id, mail_id = int(user_id), int(mail_id)
    _prep(c)
    r = c.execute("SELECT id, direction, from_email, subject, category, COALESCE(risk_level,0) AS risk_level, "
                  "COALESCE(is_blocked,0) AS blk, received_at, substr(COALESCE(body_text,''),1,4000) AS body "
                  "FROM mail_messages WHERE id=? AND user_id=? AND is_deleted=0", (mail_id, user_id)).fetchone()
    if not r or r["direction"] != "in":
        return {}
    st = _marks(c, user_id).get(mail_id)
    res = {"lv": 0, "why": "", "state": st}
    if st == "done" or r["blk"]:
        return res
    addr = (r["from_email"] or "").strip().lower()
    ns = norm_subject(r["subject"])
    got = r["received_at"] or ""
    for o in c.execute("SELECT to_email, cc, subject FROM mail_messages WHERE user_id=? AND direction='out' "
                       "AND received_at>? ORDER BY id DESC LIMIT 2000", (user_id, got)).fetchall():
        if norm_subject(o["subject"]) == ns and addr in _RE_EMAIL.findall(((o["to_email"] or "") + " " + (o["cc"] or "")).lower()):
            return res          # 이미 답장함
    if st == "need":
        res.update(lv=2, why="직접 「회신 필요」로 표시함")
        return res
    since_row = c.execute("SELECT datetime('now','localtime', ?)", ("-%d days" % REPLY_DAYS,)).fetchone()
    if got < (since_row[0] if since_row else ""):
        return res              # 오래된 메일
    for o in c.execute("SELECT id, subject FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 "
                       "AND COALESCE(is_blocked,0)=0 AND (received_at>? OR (received_at=? AND id>?)) "
                       "ORDER BY received_at DESC LIMIT 500", (user_id, got, got, mail_id)).fetchall():
        if norm_subject(o["subject"]) == ns:
            return res          # 같은 대화의 더 새 메일에서 판단
    emails, doms = _partner_keys(c)
    lv, reasons = assess(subject=r["subject"], body=r["body"], from_email=addr, category=r["category"],
                         risk_level=r["risk_level"], partner=_is_partner(addr, emails, doms))
    if lv:
        res.update(lv=lv, why=" · ".join(reasons + ["아직 답장 안 함"]))
    return res
