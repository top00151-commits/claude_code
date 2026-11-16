# -*- coding: utf-8 -*-
"""메일 서명 → 주소록 채우기 (2026-11-16 대표 지시 · 세션 15)

대표 말씀: 「메일 전달받은 사람을 주소록에 등록 … 메일 어드레스, 휴대폰 번호, 이름, 직급, 회사, 회사 주소 …
          서명이 있는 메일의 거는 그대로 붙일 수 있어서 주소록에 저장했으면 좋겠고」

하는 일 — 받은 메일에서 **보낸 사람 본인의 서명 줄**만 골라 연락처 칸(이름·직급·회사·부서·휴대폰·전화·팩스·주소)을
채운 「초안」을 만든다. 저장은 사람이 화면에서 확인한 뒤에만 한다(자동 저장 없음).

지키는 것
  · 규칙으로만 읽는다 — AI·외부 서비스로 메일 내용을 보내지 않는다.
  · 답장에 딸려 온 **옛 글(인용)** 은 잘라낸다 — 거기엔 우리 직원 서명이 들어 있어, 그대로 읽으면
    거래처 사람에게 우리 직원 전화번호를 붙이는 사고가 난다.
  · 메일 주소는 **보낸 주소(머리글)** 를 쓴다 — 받은편지함의 「보낸 사람 ↔ 연락처」 연결이 그 주소로 맺어진다.
  · 거래처 연결은 **같은 메일 도메인의 기존 연락처가 한 거래처만 가리킬 때** 만 미리 고른다(추측 연결 금지).
  · 못 읽으면 빈 칸으로 둔다(틀린 값을 채우느니 비워 둔다).
"""
from __future__ import annotations

import html as _html
import re

from . import contacts as _ct

# 우리 회사 주소(서명 줄에 이게 있는데 보낸 사람은 바깥이면 = 인용된 우리 서명)
OUR_DOMAINS = ("knknara.co.kr",)
# 개인 무료 메일 — 도메인으로 회사를 짐작하면 안 되는 곳
FREE_MAIL = frozenset((
    "gmail.com", "naver.com", "daum.net", "hanmail.net", "kakao.com", "nate.com", "outlook.com",
    "hotmail.com", "live.com", "yahoo.com", "yahoo.co.kr", "icloud.com", "me.com", "qq.com", "163.com",
    "126.com", "proton.me", "protonmail.com", "msn.com", "aol.com", "korea.com", "lycos.co.kr",
))

MAX_SIG_LINES = 14          # 서명으로 볼 꼬리 줄 수
MAX_LINE_LEN = 110          # 이보다 긴 줄은 서명이 아니라 본문·안내문

# ─── ① 본문을 줄 단위 글로 ───────────────────────────────────────────────────
_RE_QUOTE_HTML = (
    re.compile(r"(?is)<blockquote\b.*?</blockquote>"),
    # 지메일 인용 묶음 · 아웃룩 답장 머리(그 뒤는 전부 옛 글)
    re.compile(r"(?is)<div[^>]+class=[\"'][^\"']*gmail_quote[^\"']*[\"'].*$"),
    re.compile(r"(?is)<div[^>]+id=[\"']?(?:divRplyFwdMsg|appendonsend)[\"']?.*$"),
)


def html_to_lines(html: str) -> str:
    """HTML 본문 → 줄이 살아 있는 글. (받은편지함용 변환은 줄을 다 붙여 버려 서명을 못 읽는다)"""
    if not html:
        return ""
    t = re.sub(r"(?is)<(script|style|head|title)\b.*?</\1>", " ", html)
    t = re.sub(r"(?is)<!--.*?-->", " ", t)
    for rx in _RE_QUOTE_HTML:
        t = rx.sub("\n", t)
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</(p|div|tr|li|h[1-6]|table|ul|ol|pre|address)\s*>", "\n", t)
    t = re.sub(r"(?i)<(p|div|tr|li|h[1-6]|hr)\b[^>]*>", "\n", t)
    t = re.sub(r"(?i)</t[dh]\s*>", "  ", t)
    t = re.sub(r"(?s)<[^>]+>", "", t)
    t = _html.unescape(t).replace("\xa0", " ").replace("​", "")
    return "\n".join(ln.rstrip() for ln in t.replace("\r", "").split("\n"))


# ─── ② 옛 글(인용·전달 머리) 잘라내기 ─────────────────────────────────────────
_RE_CUT_LINE = re.compile(
    r"^\s*(?:"
    r"-{2,}\s*(?:original message|원본\s*메[시세]지|forwarded message|전달된?\s*메[시세]지|원문)\s*-{2,}"
    r"|_{10,}|={10,}"
    r"|on\s.{6,90}\swrote\s*:?"
    r"|\d{4}\s*년\s.{3,90}(?:작성|썼습니다|wrote)\s*:?"
    r"|.{2,90}님이\s*(?:작성|보낸|쓴)\s*(?:했습니다|메[시세]지)?\s*:?"
    r"|begin forwarded message\s*:?"
    r")\s*$", re.I)
_RE_HEAD_FROM = re.compile(r"^\s*(?:from|보낸\s*사람|보낸이|발신|보낸\s*이)\s*[:：]", re.I)
_RE_HEAD_NEXT = re.compile(r"^\s*(?:sent|date|to|subject|cc|보낸\s*날짜|날짜|받는\s*사람|받는이|수신|제목|참조)\s*[:：]", re.I)


def own_part(text: str) -> str:
    """보낸 사람이 **이번에 직접 쓴 부분** 만. 답장·전달로 딸려 온 옛 글은 버린다."""
    lines = (text or "").replace("\r", "").split("\n")
    cut = len(lines)
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s:
            continue
        if _RE_CUT_LINE.match(s):
            cut = i
            break
        if _RE_HEAD_FROM.match(s):
            # 「보낸 사람:」 줄 뒤 4줄 안에 「날짜:/받는 사람:/제목:」 이 따라오면 옛 글의 머리
            nxt = [x.strip() for x in lines[i + 1:i + 6] if x.strip()]
            if any(_RE_HEAD_NEXT.match(x) for x in nxt[:4]):
                cut = i
                break
        if s.startswith(">"):
            # '>' 로 시작하는 줄이 잇달아 2줄 이상 = 인용 묶음
            nxt = [x.strip() for x in lines[i + 1:i + 4] if x.strip()]
            if nxt and nxt[0].startswith(">"):
                cut = i
                break
    return "\n".join(lines[:cut])


# ─── ③ 서명 줄 고르기 ─────────────────────────────────────────────────────────
_RE_CLOSING = re.compile(
    r"(감사합니다|감사드립니다|고맙습니다|수고하세요|수고하십시오|부탁드립니다|부탁 드립니다|드림\b|배상\b|올림\b"
    r"|좋은 하루|행복한 하루|안녕히|이상입니다"
    r"|best regards|kind regards|warm regards|regards\s*,?$|sincerely|thanks\s*[,.!]?$|thank you|many thanks"
    r"|tr[âa]n tr[ọo]ng|c[ảa]m [ơo]n)", re.I)
_RE_SIG_DELIM = re.compile(r"^\s*(?:--\s?|—{2,}|-{3,}|_{3,}|={3,}|\*{3,}|~{3,})\s*$")
_RE_JUNK = re.compile(
    r"(sent from my|나의\s*\S+에서 보냄|에서 보냈습니다|get outlook for|outlook for (?:ios|android)|보낸 메일입니다"
    r"|confidential|기밀|비밀\s*정보|법적\s*(?:보호|책임)|수신인|무단|intended (?:only|solely|recipient)"
    r"|disclaimer|unsubscribe|수신\s*거부|바이러스|virus|본 메일은|이 메일은|this e-?mail|this message|please consider the environment"
    r"|인쇄하기 전에)", re.I)
_RE_INTL = re.compile(r"\+\d{1,3}[\s\-.(]*\d[\d\s\-.()]{6,17}\d")
_RE_URL = re.compile(r"(?:https?://|www\.)\S+", re.I)


_RE_PROSE_KO = re.compile(r"(?:니다|세요|어요|아요|에요|예요|지요|네요|군요|니까|겠다|한다|된다|이다|있다|없다|바람|드림|올림|배상)[.!?~^ )]*$")


def _is_prose(ln: str) -> bool:
    """글월(문장)인가 — 서명 줄은 낱말·번호의 나열이지 문장이 아니다.
    본문 끝의 「010-…로 전화 주세요.」 같은 줄을 서명으로 읽지 않으려는 것."""
    s = (ln or "").strip()
    if not s:
        return False
    if _RE_PROSE_KO.search(s):
        return True
    return len(s.split()) >= 8 and s[-1] in ".!?" and not _ct._RE_EMAIL.search(s.split()[-1])


def _has_signal(ln: str) -> bool:
    """이 줄이 서명 재료(전화·메일·회사·직책·주소·홈페이지)를 담고 있는가."""
    return bool(_ct._RE_EMAIL.search(ln) or _ct._RE_PHONE.search(ln) or _RE_INTL.search(ln)
                or _ct._RE_COMPANY.search(ln) or _ct._extract_position(ln)
                or _ct._RE_ADDR.search(ln) or _RE_URL.search(ln))


def signature_block(own_text: str) -> str:
    """직접 쓴 부분의 꼬리에서 서명 줄만. 없으면 빈 글."""
    raw = [ln.strip() for ln in (own_text or "").split("\n")]
    while raw and not raw[-1]:
        raw.pop()
    if not raw:
        return ""
    # 꼬리의 안내문(기밀 고지·「아이폰에서 보냄」)·긴 줄은 버린다
    lines = []
    for ln in raw[-60:]:
        if not ln:
            lines.append("")
            continue
        if len(ln) > MAX_LINE_LEN or _RE_JUNK.search(ln):
            continue
        lines.append(ln)
    while lines and not lines[-1]:
        lines.pop()
    if not lines:
        return ""
    tail_from = max(0, len(lines) - 30)
    start = None
    # ⓐ 서명 가름줄(-- · ___) 이 꼬리에 있으면 그 아래
    for i in range(len(lines) - 1, tail_from - 1, -1):
        if _RE_SIG_DELIM.match(lines[i]) and any(x for x in lines[i + 1:]):
            start = i + 1
            break
    # ⓑ 맺음말(감사합니다 · Best regards) 이 꼬리에 있으면 그 아래
    if start is None:
        for i in range(len(lines) - 1, tail_from - 1, -1):
            if lines[i] and len(lines[i]) <= 40 and _RE_CLOSING.search(lines[i]) and not _has_signal(lines[i]):
                if any(x for x in lines[i + 1:]):
                    start = i + 1
                break
    # ⓒ 둘 다 없으면 — 맨 끝에서 위로, 글월(문장)이 나오기 전까지의 줄 묶음만(본문 속 번호를 서명으로 읽지 않게)
    if start is None:
        nz = [i for i in range(tail_from, len(lines)) if lines[i]]
        run = []
        for i in reversed(nz):
            if _is_prose(lines[i]) or len(run) >= MAX_SIG_LINES:
                break
            run.append(i)
        if not run:
            return ""
        start = run[-1]
    block = [ln for ln in lines[start:] if ln and not _RE_SIG_DELIM.match(ln) and not _is_prose(ln)]
    block = block[:MAX_SIG_LINES]
    # 서명 재료가 하나도 없으면 서명이 아니다(이름만 달랑 있는 꼬리는 머리글 이름으로 충분)
    if not any(_has_signal(ln) for ln in block):
        return ""
    return "\n".join(block)


# ─── ④ 서명 글 → 칸 ───────────────────────────────────────────────────────────
_RE_SPLIT = re.compile(r"\s*[|│┃]\s*|\s+ㅣ\s+|\s+/\s+|\s{3,}")
_RE_KR_NAME = re.compile(r"[가-힣]{2,4}")
_FUNC = (r"(?:영업|구매|관리|총무|인사|재무|회계|생산|품질|기술|개발|설계|자재|물류|해외|국내|경영|기획|마케팅|연구|제조|공무|전산"
         r"|무역|수출|수입|서비스|고객|지원|전략|법무|홍보|디자인|시공|공사|안전|환경|검사|조립|가공)")
_RE_DEPT_WORD = re.compile(r"[가-힣A-Za-z0-9&·]{1,14}(?:사업부|본부|연구소|센터|팀|실|그룹|지사|지점|파트)(?=\s|$)"
                           r"|" + _FUNC + r"\d*(?:부|과)(?=\s|$)")
_RE_DEPT_TAIL = re.compile(r"^(.*\S)\s+(\S{1,14}(?:사업부|본부|연구소|센터|팀|실|부|과|그룹|지사|지점|파트))$")
_RE_COMP_TOKEN = re.compile(
    r"(?:주식회사\s*\S+|\S+\s*주식회사|\(주\)\s*\S+|\S+\s*\(주\)|㈜\s*\S+|\S+\s*㈜"
    r"|[A-Za-z][\w&.\- ]{1,40}?(?:Co\.,?\s*Ltd\.?|Ltd\.?|Inc\.?|Corp\.?|LLC|GmbH|JSC|Vina))", re.I)
_LAB_ADDR = re.compile(r"^\s*(?:주소|address|addr|소재지|a)\s*[.:：)\]]\s*(.+)$", re.I)
_RE_EN_NAME = re.compile(r"^[A-Z][a-z]+(?:[ \-][A-Z][a-z'\-]+){1,3}$")
_EN_TITLES = (
    "general manager", "sales manager", "purchasing manager", "project manager", "account manager",
    "senior manager", "deputy manager", "assistant manager", "team leader", "managing director",
    "vice president", "president", "director", "manager", "engineer", "ceo", "cto", "cfo", "coo",
    "buyer", "supervisor", "specialist", "executive", "representative", "researcher",
)


def _fix_intl(text: str) -> str:
    """+82 10-1234-5678 · +82 (0)2-123-4567 → 010-… · 02-… (국내 번호 규칙이 읽을 수 있게)."""
    return re.sub(r"\+\s*82[\s\-.]*\(?0?\)?[\s\-.]*(?=\d)", "0", text or "")


def _pieces(block: str) -> list:
    """서명 줄을 한 항목씩으로 — 「홍길동 부장 | 구매팀 | T. 02-…」 처럼 한 줄에 여럿인 서명 대응."""
    out = []
    for ln in (block or "").split("\n"):
        ln = ln.strip()
        if not ln:
            continue
        parts = [p.strip() for p in _RE_SPLIT.split(ln) if p and p.strip()]
        out.extend(parts if len(parts) > 1 else [ln])
    return out


def _clean_header_name(from_name: str) -> tuple:
    """머리글의 보낸 이름 → (이름, 직책). 「홍길동 부장」「홍길동(구매팀)」「홍길동/구매팀/가나다」 대응."""
    s = (from_name or "").strip().strip("\"'")
    if not s or "@" in s:
        return "", ""
    base = re.split(r"[(\[/|<]", s, 1)[0].strip()
    base = re.sub(r"\s+", " ", base).strip(" ,.-·")
    pos = ""
    for p in _ct._POSITIONS:                      # 긴 낱말 먼저
        if base.endswith(p):
            head = base[:-len(p)].strip()
            # 「홍길동 부장」「홍길동부장」 만 — 「이사랑」「김대리」 처럼 이름의 일부인 것은 떼지 않는다
            if len(head.replace(" ", "")) >= 2 and (base[:-len(p)].endswith(" ") or len(head.replace(" ", "")) >= 3):
                base, pos = head, p
            break
        if base.startswith(p + " "):
            base, pos = base[len(p):].strip(), p
            break
    m = _RE_KR_NAME.fullmatch(base.replace(" ", "")) if base else None
    if m and not _ct._RE_COMPANY.search(base):
        return base.replace(" ", ""), pos
    return base[:40], pos


def parse_block(block: str) -> dict:
    """서명 글 → 칸. contacts.parse_signature(기존 규칙) 위에 한 줄 여러 항목·해외 표기·주소·부서 보강."""
    f = _ct._empty_fields()
    pieces = _pieces(_fix_intl(block))
    if not pieces:
        return f
    f.update(_ct.parse_signature("\n".join(pieces)))
    # 번호 칸에 번호가 아닌 글이 들어갔으면 비운다(라벨 오인: 「대표: 홍길동」 등)
    for k in ("mobile", "phone", "fax"):
        if f[k] and len(re.sub(r"\D", "", f[k])) < 7:
            f[k] = ""
    # 해외 번호(+84 …) — 국내 규칙이 못 읽는 것만 채운다
    if not (f["mobile"] and f["phone"]):
        for p in pieces:
            for m in _RE_INTL.finditer(p):
                num = re.sub(r"\s+", " ", m.group(0)).strip()
                low = p[:m.start()].lower()[-14:]
                if any(x in low for x in ("fax", "팩스", "f.", "f:")):
                    f["fax"] = f["fax"] or num
                elif any(x in low for x in ("mobile", "cell", "hp", "h.p", "m.", "m:", "휴대", "핸드폰", "zalo")):
                    f["mobile"] = f["mobile"] or num
                else:
                    f["phone"] = f["phone"] or num
    # 회사 — 줄 전체가 아니라 회사 이름 부분만(「㈜가나다 구매팀 홍길동 부장」 → ㈜가나다)
    comp = f["company"]
    if comp:
        m = _RE_COMP_TOKEN.search(comp)
        dm = _RE_DEPT_TAIL.match(comp)
        if m and len(comp) > len(m.group(0)) + 1:
            rest = (comp[:m.start()] + " " + comp[m.end():]).strip()
            f["company"] = m.group(0).strip()
            if not f["department"]:
                d2 = _RE_DEPT_WORD.search(rest)
                if d2:
                    f["department"] = d2.group(0)
        elif dm and not f["department"]:
            f["company"], f["department"] = dm.group(1).strip(), dm.group(2).strip()
    # 부서 — 따로 한 줄인 경우(「구매팀」「영업1팀 / 과장」)
    if not f["department"]:
        for p in pieces:
            if p == comp or _ct._RE_EMAIL.search(p) or _ct._RE_PHONE.search(p) or _ct._RE_ADDR.search(p):
                continue
            if _ct._RE_COMPANY.search(p) or len(p) > 22:
                continue
            d = _RE_DEPT_WORD.search(p)
            if d:
                f["department"] = d.group(0)
                break
    # 주소 — 라벨(주소: · Address:) 먼저, 없으면 주소 낱말이 든 줄(전화·메일 줄 제외)
    if not f["address"]:
        for p in pieces:
            m = _LAB_ADDR.match(p)
            if m and len(m.group(1).strip()) >= 6:
                f["address"] = m.group(1).strip()
                break
    if not f["address"]:
        for p in pieces:
            if _ct._RE_ADDR.search(p) and len(p) >= 10 and not _ct._RE_EMAIL.search(p) \
                    and not _ct._RE_PHONE.search(p) and re.search(r"\d", p):
                f["address"] = p
                break
    if f["address"]:
        f["address"] = re.sub(r"^\s*(?:주소|address|addr|소재지|본사|사무실|본점|head office|office)\s*[.:：)\]]\s*",
                              "", f["address"], flags=re.I)[:200]
    # 영문 서명 — 이름·직함
    if not f["name"]:
        for p in pieces[:4]:
            if _RE_EN_NAME.match(p) and not _ct._RE_COMPANY.search(p):
                f["name"] = p
                break
    if not f["position"]:
        for p in pieces:
            low = p.lower()
            if _ct._RE_EMAIL.search(p) or len(p) > 40:
                continue
            for t in _EN_TITLES:
                if re.search(r"(?<![a-z])" + re.escape(t) + r"(?![a-z])", low):
                    f["position"] = p if len(p) <= 30 and not _ct._RE_COMPANY.search(p) else t.title()
                    break
            if f["position"]:
                break
    # 이름 칸에 이름이 아닌 것이 들어갔으면 비운다(맺음말·회사·직책)
    nm = f["name"]
    if nm and (_RE_CLOSING.search(nm) or _ct._RE_COMPANY.search(nm) or nm in _ct._POSITIONS
               or _ct._RE_EMAIL.search(nm) or re.search(r"\d{3,}", nm)
               or nm == f["department"] or _RE_DEPT_WORD.fullmatch(nm)):
        f["name"] = ""
    # 걸러져 비었으면 한 번 더 — 「부장 홍길동」(직책이 앞) · 부서 줄을 뺀 나머지에서
    if not f["name"]:
        rest = [p for p in pieces if not _RE_DEPT_WORD.fullmatch(p) and p != f["company"]]
        for p in rest:
            for pos in _ct._POSITIONS:
                if p.startswith(pos + " "):
                    m = _RE_KR_NAME.fullmatch(p[len(pos):].strip().replace(" ", ""))
                    if m:
                        f["name"] = m.group(0)
                    break
            if f["name"]:
                break
        if not f["name"]:
            nm = _ct._extract_name(rest, f["company"])
            if nm and not (_RE_CLOSING.search(nm) or _RE_DEPT_WORD.fullmatch(nm) or nm == f["department"]):
                f["name"] = nm
    for k in f:
        f[k] = (f[k] or "").strip()[:200]
    return f


# ─── ⑤ 메일 한 통 → 연락처 초안 ───────────────────────────────────────────────
def _domain(email: str) -> str:
    e = (email or "").strip().lower()
    return e.rsplit("@", 1)[1] if "@" in e else ""


def company_hint(c, from_email: str) -> dict:
    """같은 메일 도메인의 기존 연락처에서 회사·거래처 짐작 — **한 곳만 가리킬 때만**.
    반환 {"company": str, "customer_id": int|None}. 무료 메일·우리 도메인은 짐작하지 않는다."""
    out = {"company": "", "customer_id": None}
    dom = _domain(from_email)
    if not dom or dom in FREE_MAIL or dom in OUR_DOMAINS or c is None:
        return out
    try:
        rows = c.execute(
            "SELECT company, customer_id FROM shared_contacts "
            "WHERE email IS NOT NULL AND lower(email) LIKE ? LIMIT 200", ("%@" + dom,)).fetchall()
    except Exception:
        return out
    comps = {(r[0] or "").strip() for r in rows if (r[0] or "").strip()}
    custs = {r[1] for r in rows if r[1]}
    if len(comps) == 1:
        out["company"] = next(iter(comps))
    if len(custs) == 1:
        out["customer_id"] = next(iter(custs))
    return out


def draft_from_text(text: str, from_name: str = "", from_email: str = "", *, is_block: bool = False) -> dict:
    """글(본문 또는 사람이 붙여 넣은 서명) → {"fields", "sig_text", "notes"}.
    is_block=True 면 text 를 서명 그 자체로 본다(사람이 붙여 넣은 글 — 자르거나 고르지 않는다)."""
    notes = []
    from_email = (from_email or "").strip()
    block = (text or "").strip() if is_block else signature_block(own_part(text or ""))
    sender_dom = _domain(from_email)
    # 서명 줄의 메일 주소가 보낸 사람 것이 아니고 우리 회사 것이면 = 딸려 온 우리 서명 → 읽지 않는다
    if block and not is_block and sender_dom and sender_dom not in OUR_DOMAINS:
        ems = [e.lower() for e in _ct._RE_EMAIL.findall(block)]
        if ems and from_email.lower() not in ems and any(_domain(e) in OUR_DOMAINS for e in ems):
            block = ""
    f = parse_block(block) if block else _ct._empty_fields()
    sig_email = f.get("email") or ""
    hname, hpos = _clean_header_name(from_name)
    # 이름 — 머리글 이름이 한글 이름이면 그것(서명 글에서 고른 이름보다 확실하다)
    if hname and _RE_KR_NAME.fullmatch(hname):
        f["name"] = hname
    elif not f["name"]:
        f["name"] = hname or (from_email.split("@")[0] if from_email else "")
    if not f["position"] and hpos:
        f["position"] = hpos
    if from_email:
        f["email"] = from_email
        if sig_email and sig_email.lower() != from_email.lower() and _domain(sig_email) != sender_dom:
            notes.append("서명에 적힌 메일 주소(%s)가 보낸 주소와 다릅니다 — 보낸 주소로 채웠습니다." % sig_email)
    filled = [k for k in ("position", "company", "department", "mobile", "phone", "fax", "address") if f.get(k)]
    if not block:
        notes.append("이 메일에서 글로 된 서명을 찾지 못했습니다(서명이 그림이거나 없는 메일). 이름·메일 주소만 채웠습니다.")
    elif not filled:
        notes.append("서명에서 읽을 수 있는 칸이 없었습니다. 이름·메일 주소만 채웠습니다.")
    return {"fields": f, "sig_text": block, "notes": notes, "filled": filled}


def draft_from_mail(m: dict, c=None) -> dict:
    """받은 메일 한 통 → 연락처 초안(+같은 도메인 기존 연락처에서 회사·거래처 짐작)."""
    text = html_to_lines(m.get("body_html") or "")
    d = draft_from_text(text, m.get("from_name") or "", m.get("from_email") or "") if text.strip() else None
    if d is None or not d["sig_text"]:
        d2 = draft_from_text(m.get("body_text") or "", m.get("from_name") or "", m.get("from_email") or "")
        if d is None or d2["sig_text"]:
            d = d2
    hint = company_hint(c, m.get("from_email") or "")
    d["customer_id"] = hint["customer_id"]
    if not d["fields"].get("company") and hint["company"]:
        d["fields"]["company"] = hint["company"]
        d["notes"].append("회사 이름은 같은 메일 주소(@%s)를 쓰는 기존 연락처에서 가져왔습니다." % _domain(m.get("from_email") or ""))
    return d
