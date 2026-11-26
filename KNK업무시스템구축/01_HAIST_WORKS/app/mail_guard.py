# -*- coding: utf-8 -*-
"""📮 받은 메일 스팸·피싱 판별 (대표 지시 2026-11-16 「스팸·피싱 위험 메일을 사전에 걸러내 보안 취약을 예방」).

원칙
  · 서버 안에서 규칙으로만 판단한다 — 메일 내용을 AI·외부 서비스로 보내지 않는다(메일 내용 외부 전송 규정).
  · 링크에 접속하지 않는다 · 메일 본문의 명령을 실행하지 않는다(글자만 본다).
  · 지우지 않는다 — 가장 센 처리도 「차단함」(복구 가능) 격리까지.

단계(level)
  0 = 안전(사내)   1 = 외부 발신(표시만)   2 = 의심(빨간 경고 · 링크 무력화)   3 = 위험(차단함 격리 · 경고)

판단 재료(이유는 사람이 읽는 글로 남긴다 → risk_note)
  ① 메일 서버의 인증 결과(Authentication-Results: SPF·DKIM·DMARC) — 사칭의 가장 강한 증거
  ② 우리 회사 주소를 흉내 낸 주소(knknara.co.kr 비슷한 철자 · 퓨니코드)
  ③ 이름 사칭(보낸 이 이름이 대표·직원·회사 이름인데 주소는 무료 메일)
  ④ 답장 주소(Reply-To)가 보낸 주소와 다른 회사
  ⑤ 링크: 보이는 주소와 실제 주소가 다름 · IP 주소 링크 · 단축 주소 · 퓨니코드 · '@' 속임
  ⑥ 첨부: 실행파일 · 이중 확장자 · 매크로 문서 · HTML 첨부 · 압축파일(+ 비밀번호 안내)
  ⑦ 송금·계좌 변경 요구(BEC: 거래처 사칭 송금 사기) · 계정·비밀번호 확인 요구 + 링크
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

OUR_DOMAINS = ("knknara.co.kr",)
COMPANY_NAMES = ("케이엔케이", "knk", "haist", "하이스트")
CEO_WORDS = ("대표이사", "대표님", "ceo", "사장")
FREE_MAIL = ("gmail.com", "naver.com", "daum.net", "hanmail.net", "nate.com", "outlook.com", "hotmail.com",
             "live.com", "yahoo.com", "yahoo.co.kr", "icloud.com", "qq.com", "163.com", "126.com", "aol.com",
             "proton.me", "protonmail.com", "gmx.com", "mail.ru", "yandex.com", "zoho.com")
SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly", "cutt.ly", "rebrand.ly",
              "han.gl", "me2.do", "vo.la", "url.kr", "zrr.kr", "t.ly", "shorturl.at", "rb.gy", "tiny.cc")
EXEC_EXTS = {".exe", ".scr", ".com", ".pif", ".bat", ".cmd", ".vbs", ".vbe", ".js", ".jse", ".jar", ".lnk",
             ".msi", ".reg", ".ps1", ".wsf", ".hta", ".cpl", ".scf", ".inf", ".chm", ".iso", ".img", ".vhd",
             ".vhdx", ".msc", ".appx", ".msix", ".application", ".gadget", ".sct", ".wsh", ".dll"}
MACRO_EXTS = {".docm", ".xlsm", ".pptm", ".xlam", ".dotm", ".xltm", ".potm", ".ppsm", ".xlsb"}
HTML_EXTS = {".html", ".htm", ".shtml", ".xhtml", ".svg", ".mht", ".mhtml"}
ARCHIVE_EXTS = {".zip", ".rar", ".7z", ".alz", ".egg", ".gz", ".tar", ".cab", ".arj", ".ace", ".z", ".xz", ".bz2"}
DOC_LIKE = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".hwp", ".hwpx", ".jpg", ".jpeg", ".png", ".txt"}

_BEC_PAT = re.compile(
    r"(계좌\s*(가|를|이)?\s*(변경|바뀌|바꾸|새로|신규)|변경\s*된\s*계좌|새\s*계좌|입금\s*계좌\s*(변경|안내)|"
    r"송금\s*계좌|결제\s*계좌\s*변경|bank\s*(account|details?)\s*(change|update|has\s*changed)|"
    r"new\s*bank\s*account|updated?\s*(banking|bank|payment)\s*(details?|information)|"
    r"change\s*of\s*bank|remit(tance)?\s*to\s*(our\s*)?new|tài\s*khoản\s*mới|thay\s*đổi\s*tài\s*khoản|"
    # 11-26 — 더 넓힌 말(「계좌번호가 변경」 · 통장 · 수취 · 입금처 · 은행 정보 · have changed · beneficiary)
    #   「계좌·통장·수취·입금처·은행 정보」와 「변경·바뀌·새」가 한 문장 안 20글자 이내에 같이 있으면
    r"(계좌\s*번호|계좌|통장|입금\s*처|수취\s*(인|은행|계좌)?|은행\s*(정보|계좌)|결제\s*처)[^.\n。!?]{0,20}(변경|바뀌|바꾸|바꿨|바뀐|새로|신규)|"
    r"(변경\s*된|바뀐|새로운|신규)\s*(입금\s*)?(계좌|통장|입금\s*처|수취\s*(은행|계좌)?|은행\s*(정보|계좌))|"
    r"(bank|banking|account|payment|remittance|wire)\s*(details?|information|info|instructions?)\s*(have|has)?\s*(been\s*)?(changed|updated)|"
    r"new\s*(beneficiary|banking\s*details|bank\s*details|remittance\s*details)|beneficiary\s*(details?\s*)?(change|update)|"
    r"(số\s*tài\s*khoản|ngân\s*hàng)\s*(mới|đã\s*thay\s*đổi))", re.I)
_CRED_PAT = re.compile(
    r"(비밀번호|계정\s*(확인|정지|잠금|만료|인증|보안)|본인\s*확인|로그인\s*(하|해|필요|시도)|보안\s*경고|"
    r"메일함\s*(용량|정지|만료)|사서함\s*(용량|정지|만료)|"
    r"password|verify\s*your|account\s*(suspend|locked|verify|expire)|sign\s*in\s*to|log\s*in\s*to|"
    r"mailbox\s*(full|quota|suspend)|unusual\s*(sign|activity)|security\s*alert|mật\s*khẩu|xác\s*minh)", re.I)
_URGENT_PAT = re.compile(r"(긴급|즉시|오늘\s*안|24\s*시간|정지\s*예정|urgent|immediately|within\s*24|asap|final\s*notice|khẩn)", re.I)
# 계정·메일함을 「정지·잠금·만료시킨다」는 으름장 — 긴급 문구가 없어도 피싱의 전형(2026-11-17 옛 시험 mail_security_test 가 잡아 줌)
_THREAT_PAT = re.compile(
    r"((계정|아이디|메일함|사서함|메일\s*계정|서비스)\s*(이|가|을|를|은|는)?\s*.{0,10}(정지|잠금|잠김|잠겼|만료|차단|중지|해지|삭제|폐쇄|비활성)|"
    r"(account|mailbox|e-?mail|access)\s.{0,20}(suspend|lock|expire|disabl|deactivat|terminat|restrict|clos)|"
    r"tài\s*khoản.{0,15}(khóa|tạm\s*ngưng|hết\s*hạn))", re.I)
_ARCH_PW_PAT = re.compile(r"(압축|첨부|파일).{0,20}(비밀번호|암호|password)|(password|비밀번호|암호)\s*[:：]\s*\S{3,}", re.I)


_NAME_TAIL = re.compile(r"[\s.\x00-\x1f​-‏‪-‮⁠-⁤﻿]+$")


def name_ext(fn) -> str:
    """11-26 — 첨부 이름의 확장자(소문자). 끝의 점·빈칸·보이지 않는 글자는 떼고 본다
    (윈도는 저장할 때 끝 점·빈칸을 지워 `invoice.js.` 가 `invoice.js` 가 됨). 이 함수 하나로 세 곳(판정·내려받기·저장)이 같게 읽는다."""
    fn = _NAME_TAIL.sub("", (fn or "").strip().lower())
    return ("." + fn.rsplit(".", 1)[-1]) if "." in fn else ""


def real_inline(a) -> bool:
    """본문 속 그림으로 믿어도 되는 첨부인가 — 「inline」 표시 + 그림 형식 + 그림 확장자.
    (그림이 아닌 첨부는 inline 표시가 있어도 보통 첨부처럼 판정한다.)"""
    if not a or not a.get("inline"):
        return False
    m = (a.get("mime") or "").lower().split(";")[0].strip()
    e = name_ext(a.get("filename") or "")
    return m.startswith("image/") and m != "image/svg+xml" and (e == "" or e in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".tif", ".tiff"))


def _ext(fn) -> str:
    return name_ext(fn)


def _domain(addr: str) -> str:
    a = (addr or "").strip().lower()
    if "<" in a and ">" in a:
        a = a[a.rfind("<") + 1:a.rfind(">")]
    return a.rsplit("@", 1)[-1].strip(" >.") if "@" in a else ""


def _is_ours(dom: str) -> bool:
    return bool(dom) and any(dom == d or dom.endswith("." + d) for d in OUR_DOMAINS)


def _base(dom: str) -> str:
    """등록 도메인 근사(뒤에서 두 마디 · co.kr 같은 2단계는 세 마디)."""
    p = [x for x in (dom or "").split(".") if x]
    if len(p) >= 3 and p[-2] in ("co", "or", "go", "ac", "ne", "re", "com", "net", "org", "edu", "gov"):
        return ".".join(p[-3:])
    return ".".join(p[-2:])


def _lev(a: str, b: str) -> int:
    if a == b:
        return 0
    if abs(len(a) - len(b)) > 3:
        return 9
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def lookalike_of_ours(dom: str) -> str:
    """우리 회사 주소를 흉내 낸 주소면 흉내 낸 대상을, 아니면 ''."""
    if not dom or _is_ours(dom):
        return ""
    if "xn--" in dom:
        return OUR_DOMAINS[0] if "knk" in dom or "nara" in dom else ""
    b = _base(dom)
    for ours in OUR_DOMAINS:
        ob = _base(ours)
        o1 = ob.split(".")[0]                       # knknara
        b1 = b.split(".")[0]
        if b == ob:
            continue
        # 철자 비슷 · 이름은 같은데 끝(.com 등)만 다름 · 우리 이름을 다른 주소 안에 끼워 넣음
        if _lev(b, ob) <= 2 or b1 == o1 or _lev(b1, o1) <= 1 or o1 in dom.replace("-", "").replace(".", ""):
            return ours
    return ""


def parse_auth_results(header_values) -> dict:
    """Authentication-Results 머리글(여러 줄 가능) → {'spf':'pass|fail|softfail|none|…','dkim':…,'dmarc':…}.
    가장 위(= 우리 쪽 메일 서버가 붙인 것)를 먼저 본다. 없으면 빈 dict."""
    out = {}
    for hv in (header_values or []):
        for key in ("spf", "dkim", "dmarc"):
            if key in out:
                continue
            mo = re.search(r"\b" + key + r"\s*=\s*([a-z]+)", str(hv or ""), re.I)
            if mo:
                out[key] = mo.group(1).lower()
    return out


# 11-26 — 링크 찾기를 정규식 한 개 대신 여는 태그·닫는 태그를 한 번씩만 훑어 짝짓는 방식으로(긴 본문에서도 빠르게).
#   잡는 링크는 예전과 같다: href 가 있는 <a> 부터 그 뒤 첫 </a> 까지 · 짝이 없으면 안 잡음 · 겹치지 않게 앞에서부터.
_A_OPEN = re.compile(r"(?is)<a\b((?:[^>\"']|\"[^\"]{0,4000}\"|'[^']{0,4000}'){0,4000})>")
_A_CLOSE = re.compile(r"(?is)</a\s*>")
_A_HREF = re.compile(r"(?is)href\s*=\s*([\"'])(.*?)\1")


def a_links(html: str):
    """[(시작, 끝, 따옴표, href, 안쪽 HTML)] — 닫는 </a> 가 있는 <a href="…"> 만."""
    import bisect
    if not html:
        return []
    closes = [(m.start(), m.end()) for m in _A_CLOSE.finditer(html)]
    cstart = [c[0] for c in closes]
    out, pos = [], 0
    for m in _A_OPEN.finditer(html):
        if m.start() < pos:
            continue
        hm = _A_HREF.search(m.group(1))
        if not hm:
            continue
        i = bisect.bisect_left(cstart, m.end())
        if i >= len(cstart):
            break
        out.append((m.start(), closes[i][1], hm.group(1), hm.group(2), html[m.end():cstart[i]]))
        pos = closes[i][1]
    return out


_URL_IN_TEXT = re.compile(r"(?i)\bhttps?://[^\s<>\"')]+")
_HOSTISH = re.compile(r"(?i)^(https?://)?(www\.)?([a-z0-9-]+\.)+[a-z]{2,}(/\S*)?$")


def _host(url: str) -> str:
    try:
        u = url.strip()
        if u.startswith("//"):
            u = "http:" + u
        if not re.match(r"(?i)^[a-z][a-z0-9+.-]*:", u):
            u = "http://" + u
        sp = urlsplit(u)
        return (sp.hostname or "").lower().strip(".")
    except Exception:
        return ""


def link_findings(html: str, text: str):
    """(이유 목록, 점수) — 링크 속임수. 링크에 접속하지 않는다(글자만 본다)."""
    notes, score = [], 0
    hrefs = []
    for _s, _e, _q, href, inner in a_links(html or ""):
        href = (href or "").strip()
        if not re.match(r"(?i)^https?://", href):
            continue
        vis = re.sub(r"(?s)<[^>]+>", "", inner or "").strip()
        vis = re.sub(r"&nbsp;|\s+", " ", vis).strip()
        hrefs.append(href)
        if vis and _HOSTISH.match(vis.replace(" ", "")):
            hv, hh = _host(vis), _host(href)
            if hv and hh and _base(hv) != _base(hh):
                notes.append("보이는 링크(%s)와 실제 연결(%s)이 다름" % (hv[:40], hh[:40]))
                score = max(score, 3)
    for u in _URL_IN_TEXT.findall(text or ""):
        hrefs.append(u)
    seen = set()
    for href in hrefs:
        h = _host(href)
        if not h or h in seen:
            continue
        seen.add(h)
        if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", h):
            notes.append("숫자(IP) 주소 링크(%s)" % h)
            score = max(score, 2)
        elif "xn--" in h:
            notes.append("글자를 흉내 낸 주소 링크(%s)" % h[:40])
            score = max(score, 2)
        elif _base(h) in SHORTENERS or h in SHORTENERS:
            notes.append("단축 주소 링크(%s) — 실제 연결을 숨김" % h)
            score = max(score, 1)
        la = lookalike_of_ours(h)
        if la:
            notes.append("우리 회사 주소를 흉내 낸 링크(%s)" % h[:40])
            score = max(score, 3)
        if re.match(r"(?i)^https?://[^/]*@", href):
            notes.append("주소 안에 '@' 속임수")
            score = max(score, 2)
    return notes[:6], score, len(seen)


def assess(from_email="", from_name="", subject="", body="", html="", attachments=None,
           auth=None, reply_to="", staff_names=(), codes=None):
    """반환 (level 0~3, note 글). note 는 사람이 읽는 이유를 ' / ' 로 잇는다.
    codes(목록을 넘기면) = 스팸함으로 옮길 만한 「강한 이유」 이름을 담는다(11-18 대표 「스팸은 자동으로 걸러」).
      링크 속임(광고 메일 추적 링크에도 흔함)·외부 발신·압축파일 그 자체는 넣지 않는다 — 정상 메일이 숨지 않게."""
    if codes is None:
        codes = []
    notes = []
    level = 0
    dom = _domain(from_email)
    ours = _is_ours(dom)
    external = bool(dom) and not ours
    blob = " ".join([subject or "", body or ""])
    au = auth or {}
    fails = [k.upper() for k in ("dmarc", "spf", "dkim") if au.get(k) in ("fail", "softfail", "permerror")]
    fails_hard = [k for k in ("dmarc", "spf", "dkim") if au.get(k) in ("fail", "permerror")]

    # ① 인증 결과
    if ours and (au.get("dmarc") == "fail" or au.get("spf") == "fail"):
        level = max(level, 3)
        codes.append("auth_ours")
        notes.append("우리 회사 주소로 왔지만 메일 서버 인증 실패(%s) — 회사 사칭 의심" % "·".join(fails))
    elif ours and au.get("via") == "inbound" and not (au.get("dmarc") == "pass" or (au.get("spf") == "pass" and au.get("dkim") == "pass")):
        # 11-27 바깥 받는 길(수신 입구)로 들어온 「우리 회사 주소」 메일인데 서버 확인(통과)이 없음
        level = max(level, 2)
        codes.append("ours_unverified")
        notes.append("우리 회사 주소로 왔지만 바깥에서 들어왔고 메일 서버 확인이 없음 — 회사 사칭 의심")
    elif external and au.get("dmarc") == "fail":
        level = max(level, 2)
        codes.append("auth")
        notes.append("보낸 회사 주소 인증 실패(DMARC) — 사칭 의심")
    elif external and au.get("spf") == "fail" and au.get("dkim") != "pass":
        level = max(level, 2)
        codes.append("auth")
        notes.append("메일 서버 인증 실패(%s)" % "·".join(fails))
    elif external and fails:
        # 전달(포워딩)·메일링 리스트에서도 흔하다 → 표시만
        level = max(level, 1)
        notes.append("메일 서버 인증 일부 실패(%s)" % "·".join(fails))

    # ② 우리 회사 흉내 주소
    la = lookalike_of_ours(dom)
    if la:
        level = max(level, 3)
        codes.append("lookalike")
        notes.append("우리 회사 주소(%s)를 흉내 낸 주소(%s)" % (la, dom))

    # ③ 이름 사칭
    nm = (from_name or "").strip().lower()
    if external and nm:
        free = _base(dom) in FREE_MAIL or dom in FREE_MAIL
        hit = ""
        if any(w in nm for w in COMPANY_NAMES):
            hit = "회사 이름"
        elif any(w in nm for w in CEO_WORDS):
            hit = "대표"
        else:
            for s in staff_names or ():
                if s and len(s) >= 2 and s.lower() in nm:
                    hit = "직원 이름(%s)" % s
                    break
        if hit and free:
            level = max(level, 2)
            # 11-18: 「사장·대표」 같은 흔한 직함만으로는 스팸함으로 안 옮김 — 작은 협력사 사장님이 개인 메일을 많이 씀(시험 서버에서 실제로 걸림)
            #   우리 회사 이름·우리 직원 이름을 쓴 경우만 옮길 이유
            if hit != "대표":
                codes.append("spoof_name")
            notes.append("보낸 이 이름은 %s인데 주소는 개인 무료 메일(%s) — 사칭 의심" % (hit, dom))
        elif hit and hit != "회사 이름" and not la:
            level = max(level, 1)
            notes.append("보낸 이 이름이 %s이지만 회사 밖 주소(%s)" % (hit, dom))

    # ④ 답장 주소
    rdom = _domain(reply_to)
    if rdom and dom and _base(rdom) != _base(dom) and not _is_ours(rdom):
        r_free = _base(rdom) in FREE_MAIL or rdom in FREE_MAIL
        f_free = _base(dom) in FREE_MAIL or dom in FREE_MAIL
        # 회사 주소로 보내면서 답장만 개인 무료 메일로 = 거래처 사칭의 전형. 그 밖(뉴스레터·접수 시스템)은 표시만.
        level = max(level, 2 if (r_free and not f_free) else 1)
        if r_free and not f_free:
            codes.append("reply_to")
        notes.append("답장이 다른 곳(%s)으로 가도록 돼 있음" % rdom)

    # ⑤ 링크 — 광고 메일의 추적 링크도 「보이는 주소 ≠ 실제 주소」라 격리(3)까지는 올리지 않는다(경고·링크 막기까지)
    lnotes, lscore, nlinks = link_findings(html, body)
    if lnotes and not ours:
        notes.extend(lnotes)
        level = max(level, min(lscore, 2))

    # ⑥ 첨부
    atts = attachments or []
    names = [(a.get("filename") or "") for a in atts if not real_inline(a)]
    exe = [n for n in names if _ext(n) in EXEC_EXTS]
    dbl = [n for n in names if _ext(n) in EXEC_EXTS and _ext(_NAME_TAIL.sub("", n.lower())[: -len(_ext(n))]) in DOC_LIKE]
    if dbl:
        level = max(level, 3)
        codes.append("exec")
        notes.append("문서로 위장한 실행파일(%s)" % ", ".join(dbl[:2]))
    elif exe:
        level = max(level, 3)
        if external:
            codes.append("exec")
        notes.append("실행파일 첨부(%s)" % ", ".join(exe[:3]))
    mac = [n for n in names if _ext(n) in MACRO_EXTS]
    if mac and external:
        level = max(level, 2)
        codes.append("macro")
        notes.append("매크로가 든 문서(%s) — 「콘텐츠 사용」을 누르지 말 것" % ", ".join(mac[:2]))
    hta = [n for n in names if _ext(n) in HTML_EXTS]
    if hta and external:
        level = max(level, 2)
        codes.append("html_att")
        notes.append("웹페이지 파일 첨부(%s) — 로그인 화면 위장에 흔함" % ", ".join(hta[:2]))
    # 11-18 첨부 「속」 검사(이름만 바꾼 실행파일 · 압축 안 실행파일 · 숨은 매크로 · 비밀번호 압축) — 이 서버 안에서만
    try:
        from . import mail_attcheck as _ac
        for a in atts:
            if real_inline(a) or not a.get("data"):
                continue
            r = _ac.inspect(a.get("filename") or "", a.get("mime") or "", a.get("data") or b"")
            if r["kind"] == "block" and not any(r["why"] in n for n in notes):
                level = max(level, 3)
                codes.append("att_block")
                notes.append("위험한 첨부 %s — %s" % (a.get("filename") or "", r["why"]))
            elif r["kind"] == "warn" and external and _ext(a.get("filename") or "") not in MACRO_EXTS | HTML_EXTS:
                if r["why"].startswith("이름은 PDF"):   # 깨진·특이한 PDF 도 있다 → 표시만(스팸함으로 안 옮김)
                    level = max(level, 1)
                else:
                    level = max(level, 2)
                    codes.append("att_warn")
                notes.append("주의할 첨부 %s — %s" % (a.get("filename") or "", r["why"]))
    except Exception:
        pass
    arc = [n for n in names if _ext(n) in ARCHIVE_EXTS]
    if arc and external:
        if _ARCH_PW_PAT.search(blob):
            level = max(level, 2)
            codes.append("zip_pw")
            notes.append("비밀번호 걸린 압축파일(%s) — 백신 검사를 피하는 수법" % ", ".join(arc[:2]))
        else:
            level = max(level, 1)
            notes.append("압축파일 첨부(%s) — 안의 파일 확인 후 열기" % ", ".join(arc[:2]))

    # ⑦ 송금·계좌 변경 / 계정 확인 요구
    if (external or fails or la) and _BEC_PAT.search(blob):
        level = max(level, 2)
        codes.append("bec")
        notes.append("송금·계좌 변경 요구 — 반드시 전화로 거래처에 직접 확인")
    elif ours and _BEC_PAT.search(blob):
        # 11-27 회사 주소는 바깥에서 흉내 낼 수 있다 — 사내 메일이라도 송금·계좌 변경은 경고(사내 메일은 스팸함으로 옮기지 않음)
        level = max(level, 2)
        codes.append("bec")
        notes.append("사내 주소로 온 송금·계좌 변경 요구 — 보낸 분께 전화로 직접 확인")
    if external and nlinks and _CRED_PAT.search(blob):
        _cl = 2 if (_URGENT_PAT.search(blob) or _THREAT_PAT.search(blob) or fails or lnotes) else 1
        level = max(level, _cl)
        if _cl >= 2:
            codes.append("cred")
        notes.append("계정·비밀번호 확인을 요구하는 링크")

    if external and not notes:
        level = max(level, 1)
        notes.append("외부 발신")
    # 같은 이유 두 번 쓰지 않기
    seen, uniq = set(), []
    for n in notes:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return level, " / ".join(uniq)[:600]


def should_quarantine(from_email="", attachments=None, auth=None, level=0) -> bool:
    """차단함으로 격리할 것인가 — 증거가 강한 경우만(정상 메일을 숨기는 일이 없게):
    우리 회사 흉내 주소 · 우리 주소인데 인증 실패 · 문서로 위장한 실행파일 · 회사 밖에서 온 실행파일."""
    if level < 3:
        return False
    dom = _domain(from_email)
    ours = _is_ours(dom)
    au = auth or {}
    if lookalike_of_ours(dom):
        return True
    if ours and (au.get("dmarc") == "fail" or au.get("spf") == "fail"):
        return True
    names = [(a.get("filename") or "") for a in (attachments or []) if not real_inline(a)]
    exe = [n for n in names if _ext(n) in EXEC_EXTS]
    dbl = [n for n in exe if _ext(_NAME_TAIL.sub("", n.lower())[: -len(_ext(n))]) in DOC_LIKE]
    if bool(dbl) or (bool(exe) and not ours):
        return True
    # 11-18 속까지 본 결과 「막아야 할」 첨부(이름만 바꾼 실행파일 · 압축 안 실행파일)
    try:
        from . import mail_attcheck as _ac
        for a in (attachments or []):
            if not real_inline(a) and a.get("data") and _ac.inspect(a.get("filename") or "", a.get("mime") or "", a.get("data"))["kind"] == "block":
                return True
    except Exception:
        pass
    return False


def defang_links_html(html: str) -> str:
    """의심 메일 보기용 — 링크를 누를 수 없게(주소는 글자로 보이게) 바꾼다."""
    if not html:
        return html

    def _sub(href, inner):
        href = (href or "").strip()
        inner = inner or ""
        h = _host(href) if re.match(r"(?i)^https?://", href) else ""
        tip = ("실제 연결: " + href[:200]).replace('"', "&quot;").replace("<", "&lt;")
        mark = (' <span style="font-size:11px;color:#b91c1c">[' + (h or "링크") + "]</span>") if h else ""
        return ('<span style="text-decoration:underline dotted;color:#6b7280;cursor:not-allowed" title="'
                + tip + '">' + inner + "</span>" + mark)
    parts, last = [], 0
    for s0, e0, _q, href, inner in a_links(html):
        parts.append(html[last:s0])
        parts.append(_sub(href, inner))
        last = e0
    parts.append(html[last:])
    # 11-26 — 닫는 </a> 가 없는 링크(브라우저는 끝까지 링크로 봄)도 누를 수 없게: 남은 <a …href=…> 의 주소 칸 이름을 바꿈
    return re.sub(r"(?is)(<a\b[^>]{0,4000}?)\bhref\s*=", r"\1data-x-href=", "".join(parts))
