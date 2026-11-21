# -*- coding: utf-8 -*-
"""📅 본문 날짜 찾기 — 2026-11-21 대표 「신입사원 관점」 나 묶음 2-1.

메일 본문(보낸 사람이 이번에 직접 쓴 부분)에서 날짜 말을 찾아 「🚩 기한으로 정하기」 한 번 누르게 한다.
- 규칙으로만(AI·외부 전송 없음) · 읽기만(저장은 사람이 단추를 누를 때 기존 🚩 기한 길로)
- 「내일」「다음 주 화요일」 같은 말은 **메일을 받은 날**(보는 사람 소속 날짜) 기준으로 계산
- 「까지·마감·이내·by」가 붙은 것을 기한으로 보고 먼저 · 오늘보다 지난 날짜는 빼기 · 최대 3개
"""
import re
from datetime import date, timedelta

MAX_OUT = 3
_WD = "월화수목금토일"
_WD_EN = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
_MON_EN = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8,
           "sep": 9, "oct": 10, "nov": 11, "dec": 12}

# 기한 말(날짜 뒤 · 앞)
_RE_DL_AFTER = re.compile(r"^\s*(\(\s*[월화수목금토일]\s*\)\s*)?(오전|오후|아침|저녁|중|중으로|\d{1,2}\s*시(\s*\d{1,2}\s*분)?|\d{1,2}:\d{2}|\s)*\s*"
                          r"(까지|이내|안으로|마감|전까지|내로|내에|중으로|중에)")
_RE_WD_SAID = re.compile(r"^\s*\(\s*([월화수목금토일])\s*\)")   # 적힌 요일 — 실제 요일과 다르면 알림(입력 실수 찾기)
_RE_REL_OK =re.compile(r"^\s*(중|중으로|오전|오후|아침|저녁|\d{1,2}\s*시|회의|미팅|방문|출장|출하|납품|입고|발송|morning|afternoon|evening|\d{1,2}\s*(am|pm))", re.I)
_RE_DL_BEFORE =re.compile(r"(by|until|before|due|deadline|마감|기한|납기|까지는)\s*[:：]?\s*(on\s+|the\s+)?$", re.I)

_PATS = [
    # 2026-11-25 · 2026.11.25 · 2026/11/25
    ("ymd", re.compile(r"(?<!\d)(20\d{2})\s*[./\-년]\s*(\d{1,2})\s*[./\-월]\s*(\d{1,2})\s*일?(?!\d)")),
    # 11월 25일
    ("md_ko", re.compile(r"(?<!\d)(\d{1,2})\s*월\s*(\d{1,2})\s*일")),
    # 기한: 12/5 · 납기 12.05 — 앞에 기한 말이 있으면 요일·까지 없이도
    ("md_pre", re.compile(r"(?:기한|마감|납기|납품일|일정|날짜|due|by|until)\s*[:：]?\s*(\d{1,2})\s*[/.]\s*(\d{1,2})(?![\d./%])", re.I)),
    # 11/25(화) · 11/25 까지 · 11.25(화) — 분수·버전과 헷갈리지 않게 뒤에 요일·기한 말이 있을 때만
    ("md_sl", re.compile(r"(?<![\d./])(\d{1,2})\s*[/.]\s*(\d{1,2})(?![\d./%])(?=\s*(\(\s*[월화수목금토일]|까지|오전|오후|중|\d{1,2}\s*시|마감|이내|전까지))")),
    # 25일까지 · 25일(화) — 이번 달(지났으면 다음 달)
    ("d_ko", re.compile(r"(?<![\d월./])(\d{1,2})\s*일\s*(?=(\(\s*[월화수목금토일]|까지|오전|오후|중|\d{1,2}\s*시|마감|이내|전까지))")),
    # 오늘·금일 / 내일·명일 / 모레
    ("rel", re.compile(r"(오늘|금일|내일|명일|모레)(?!\s*(은|도)?\s*(날씨|기준))")),
    # 이번 주·다음 주·다다음 주 + 요일 / 요일만(금요일까지)
    ("wk", re.compile(r"(이번\s*주|금주|다음\s*주|차주|다다음\s*주|담주)?\s*([월화수목금토일])\s*요일")),
    # 이번 주 중·내 → 이번 주 금요일 · 다음 주 중 → 다음 주 금요일
    ("wk_in", re.compile(r"(이번\s*주|금주|다음\s*주|차주)\s*(중|내|안)(?!\s*요일)")),
    # Nov 25 · November 25th
    ("en_md", re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(st|nd|rd|th)?\b", re.I)),
    # 25 Nov · 25th November
    ("en_dm", re.compile(r"\b(\d{1,2})(st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\b", re.I)),
    # today · tomorrow · (next|this) Friday · by Friday
    ("en_rel", re.compile(r"\b(today|tomorrow)\b", re.I)),
    ("en_wd", re.compile(r"\b(this\s+|next\s+)?(mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)(day|nesday|sday|urday|rsday)?\b", re.I)),
]


def _safe(y, m, d):
    try:
        return date(int(y), int(m), int(d))
    except Exception:
        return None


def _md_year(base: date, m, d):
    """연도가 없는 월·일 — 받은 날 기준 가까운 쪽(12월 메일의 「1/5」 = 다음 해)."""
    t = _safe(base.year, m, d)
    if t and t < base - timedelta(days=60):
        t = _safe(base.year + 1, m, d)
    return t


def _week_day(base: date, which: str, wd: int):
    which = re.sub(r"\s+", "", which or "")
    mon = base - timedelta(days=base.weekday())
    if which in ("이번주", "금주", "this"):
        return mon + timedelta(days=wd)
    if which in ("다음주", "차주", "담주", "next"):
        return mon + timedelta(days=7 + wd)
    if which == "다다음주":
        return mon + timedelta(days=14 + wd)
    k = (wd - base.weekday()) % 7          # 요일만: 받은 날 또는 그 뒤 가장 가까운 그 요일
    return base + timedelta(days=k)


def _resolve(kind, g, base: date):
    if kind == "ymd":
        return _safe(g[0], g[1], g[2])
    if kind in ("md_ko", "md_sl", "md_pre"):
        if not (1 <= int(g[0]) <= 12 and 1 <= int(g[1]) <= 31):
            return None
        return _md_year(base, g[0], g[1])
    if kind == "d_ko":
        d = int(g[0])
        if not 1 <= d <= 31:
            return None
        t = _safe(base.year, base.month, d)
        if t is None or t < base:
            ny, nm = (base.year + 1, 1) if base.month == 12 else (base.year, base.month + 1)
            t = _safe(ny, nm, d)
        return t
    if kind == "rel":
        return base + timedelta(days={"오늘": 0, "금일": 0, "내일": 1, "명일": 1, "모레": 2}[g[0]])
    if kind == "wk":
        return _week_day(base, g[0] or "", _WD.index(g[1]))
    if kind == "wk_in":
        return _week_day(base, g[0], 4)
    if kind == "en_md":
        return _md_year(base, _MON_EN[g[0].lower()[:3]], g[1])
    if kind == "en_dm":
        return _md_year(base, _MON_EN[g[2].lower()[:3]], g[0])
    if kind == "en_rel":
        return base + timedelta(days=0 if g[0].lower() == "today" else 1)
    if kind == "en_wd":
        return _week_day(base, (g[0] or "").strip().lower(), _WD_EN[g[1].lower()[:3]])
    return None


_RE_QUOTE_HEAD = re.compile(r"^\s*(-{3,}\s*(original\s+message|원본\s*메시지|forwarded\s+message|전달된\s*메시지)\s*-{3,}|>\s?)", re.I | re.M)


def cut_quote(text: str) -> str:
    """옛 글(인용) 머리부터 뒤는 버림 — 날짜는 보낸 사람이 이번에 쓴 부분에서만 찾는다."""
    m = _RE_QUOTE_HEAD.search(text or "")
    return (text or "")[:m.start()] if m else (text or "")


def label(t: date) -> str:
    return "%d/%d(%s)" % (t.month, t.day, _WD[t.weekday()])


def find(text: str, base: date, today: date = None) -> list:
    """본문에서 날짜 찾기. 반환 [{"date": "YYYY-MM-DD", "label": "11/25(수)", "hit": "다음 주 화요일까지", "dl": True, "wd_bad": ""}] · 최대 3개.
    wd_bad = 본문에 적힌 요일이 실제와 다를 때 그 적힌 요일(예: 「11/25(화)」 → "화" · 실제는 수).
    base = 메일을 받은 날(보는 사람 소속) · today = 오늘(이보다 지난 날짜는 뺌)."""
    text = (text or "")[:8000]
    if not text.strip() or not base:
        return []
    today = today or base
    spans, found = [], []
    for kind, rx in _PATS:
        for m in rx.finditer(text):
            s, e = m.span()
            if any(not (e <= a or s >= b) for a, b in spans):
                continue          # 앞 규칙(더 분명한 것)이 이미 잡은 자리
            if kind == "en_wd" and not re.search(r"(by|until|before|on|this|next|due)\s+$", text[max(0, s - 8):s], re.I) \
                    and not (m.group(1) or "").strip():
                continue          # 영어 요일은 「by·on·next…」가 붙을 때만(서명·날짜 머리 「Mon,」 빼기)
            try:
                t = _resolve(kind, m.groups(), base)
            except Exception:
                t = None
            if not t:
                continue
            spans.append((s, e))
            after = text[e:e + 24]
            before = text[max(0, s - 14):s]
            mt = _RE_DL_AFTER.match(after)
            dl = bool(mt) or bool(_RE_DL_BEFORE.search(before)) or kind in ("md_pre", "wk_in")
            if kind in ("rel", "en_rel") and not dl and not _RE_REL_OK.match(after):
                spans.pop()
                continue          # 「오늘도 좋은 하루」 같은 인사말 빼기 — 기한·시각·일정 말이 붙을 때만
            hit = text[s:e] + (after[:mt.end()] if mt else "")
            if not mt and dl:
                hit = before.strip().split()[-1] + " " + hit if before.strip() else hit
            mw = _RE_WD_SAID.match(after)
            bad = mw.group(1) if (mw and mw.group(1) != _WD[t.weekday()]) else ""
            found.append((s, t, re.sub(r"\s+", " ", hit).strip()[:30], dl, bad))
    out, seen = [], set()
    for s, t, hit, dl, bad in sorted(found, key=lambda x: (not x[3], x[0])):
        if t < today or t > today + timedelta(days=400) or t.isoformat() in seen:
            continue
        seen.add(t.isoformat())
        out.append({"date": t.isoformat(), "label": label(t), "hit": hit, "dl": dl, "wd_bad": bad})
        if len(out) >= MAX_OUT:
            break
    return out
