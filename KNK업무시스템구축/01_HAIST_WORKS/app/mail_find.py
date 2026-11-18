# -*- coding: utf-8 -*-
"""메일 「쉽게 찾기·쉽게 구분·쉽게 보기」 도우미 (대표 지시 2026-11-18 · 2단계).

- 시간·날짜 묶음 이름(오늘은 시각, 올해는 월-일(요일), 그 전은 연-월-일)
- 회사 이름으로 찾기 → 그 이름의 폴더에 든 보낸 주소
- 광고·알림 주소 — 「📮 보낸 곳별 정리」(mail_cleanup.sender_groups)가 쓰는 기준 그대로(새 기준 없음)
- 「참조」로 받은 메일 — 내 주소가 받는 사람이 아니라 참조에 있을 때
- 이전 대화(인용) 접기 — 글 메일은 mail_signature.own_part 와 같은 규칙, 서식 메일은 인용 묶음 요소부터 끝까지를 <details> 로

화면만 돕는다 — 저장하는 것 없음(광고 주소는 이 프로세스 기억에만 · 메일이 바뀌면 다시 계산)."""
import re
from datetime import datetime, timedelta
from html.parser import HTMLParser

_WD = "월화수목금토일"


def _parse(ts):
    try:
        return datetime.strptime((ts or "")[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            return datetime.strptime((ts or "")[:16], "%Y-%m-%d %H:%M")
        except Exception:
            return None


def time_label(ts, now=None) -> str:
    """목록 오른쪽 시간 — 오늘 「06:53」 · 올해 「11-16 (월)」 · 그 전 「2025-12-03」."""
    d = _parse(ts)
    if not d:
        return (ts or "")[5:16]
    now = now or datetime.now()
    if d.date() == now.date():
        return d.strftime("%H:%M")
    if d.year == now.year:
        return "%s (%s)" % (d.strftime("%m-%d"), _WD[d.weekday()])
    return d.strftime("%Y-%m-%d")


def day_label(ts, now=None) -> str:
    """목록 날짜 묶음 — 오늘 · 어제 · 이번 주 · 지난주 · 이번 달 · 「2026년 10월」(그 전)."""
    d = _parse(ts)
    if not d:
        return ""
    now = now or datetime.now()
    dd, nd = d.date(), now.date()
    if dd == nd:
        return "오늘 · %d월 %d일 (%s)" % (dd.month, dd.day, _WD[dd.weekday()])
    if dd == nd - timedelta(days=1):
        return "어제 · %d월 %d일 (%s)" % (dd.month, dd.day, _WD[dd.weekday()])
    wk0 = nd - timedelta(days=nd.weekday())          # 이번 주 월요일
    if wk0 <= dd < nd:
        return "이번 주"
    if wk0 - timedelta(days=7) <= dd < wk0:
        return "지난주"
    if dd.year == nd.year and dd.month == nd.month:
        return "이번 달"
    return "%d년 %d월" % (dd.year, dd.month)


def period_range(per, now=None):
    """기간 단추 → (시작일, 끝일) 'YYYY-MM-DD'. 모르는 값·전체는 ('', '')."""
    now = now or datetime.now()
    t = now.date()
    if per == "today":
        a = t
    elif per == "week":
        a = t - timedelta(days=t.weekday())
    elif per == "month":
        a = t.replace(day=1)
    elif per == "3m":
        a = t - timedelta(days=92)
    elif per == "year":
        a = t.replace(month=1, day=1)
    else:
        return "", ""
    return a.isoformat(), t.isoformat()


PERIOD_NAMES = (("today", "오늘"), ("week", "이번 주"), ("month", "이번 달"), ("3m", "3개월"), ("year", "올해"), ("", "전체"))


# ─── 회사 이름으로 찾기 ─────────────────────────────────────────────
def folder_kinds(mf) -> dict:
    """폴더 열쇠 → 묶음 갈래(customer·other_customer·vendor·staff·gen) — 꼬리표 색."""
    out = {"gen": "gen"}
    for g in (mf or {}).get("nodes") or []:
        out[g["key"]] = g.get("kind") or ""
        for k in g.get("children") or []:
            out[k["key"]] = g.get("kind") or ""
    return out


def q_senders(mf, terms) -> list:
    """낱말마다 「그 이름(또는 다른 이름)의 폴더에 든 보낸 주소」 집합. 폴더가 없으면 빈 목록.
    두 글자 이상 낱말만 · 「일반」 같은 묶음 이름은 넓어서 뺀다."""
    out = []
    if not mf:
        return [set() for _ in terms]
    labels = mf.get("labels") or {}
    idx = mf.get("_idx")
    from . import mail_folders as _mf
    for t in terms:
        hit = set()
        tl = (t or "").strip().lower()
        if len(tl) >= 2 and tl not in ("일반", "기타"):
            keys = {k for k, nm in labels.items() if k != "gen" and tl in (nm or "").lower()}
            try:
                if idx:
                    keys |= {"f%d" % fid for fid in idx.find(t)}
            except Exception:
                pass
            for k in keys:
                hit |= set(_mf.senders_in(mf, k))
        out.append(hit)
    return out


def matched_folders(mf, terms) -> list:
    """결과 띠에 보일 「이 이름의 폴더 메일도 함께」 이름들."""
    if not mf:
        return []
    labels = mf.get("labels") or {}
    names = []
    for t in terms:
        tl = (t or "").strip().lower()
        if len(tl) < 2 or tl in ("일반", "기타"):
            continue
        for k, nm in labels.items():
            if k != "gen" and tl in (nm or "").lower() and nm not in names:
                names.append(nm)
    return names[:4]


# ─── 광고·알림 ─────────────────────────────────────────────────────
_BULK = {}


def bulk_senders(c, uid) -> set:
    """「📮 보낸 곳별 정리」가 「광고·알림으로 보이는 곳」이라고 본 주소(받은 메일 최근 5,000통 기준 · 같은 기준)."""
    try:
        st = tuple(c.execute("SELECT COUNT(*), COALESCE(MAX(id),0) FROM mail_messages WHERE user_id=? AND direction='in' "
                             "AND is_deleted=0 AND COALESCE(is_blocked,0)=0", (uid,)).fetchone())
        hit = _BULK.get(uid)
        import time as _t
        # 메일이 그대로면 그대로 · 새 메일이 와도 10분 안이면 앞 결과(받은편지함이 새 메일마다 0.4초씩 느려지지 않게)
        if hit and (hit[0] == st or _t.time() - hit[2] < 600):
            return hit[1]
        from . import mail_cleanup as _cl
        g = _cl.sender_groups(c, uid)
        res = {x["addr"] for x in g.get("groups", []) if x.get("kind") == "bulk" and x.get("addr")}
        _BULK[uid] = (st, res, _t.time())
        return res
    except Exception as e:
        print("[MAIL-FIND bulk ERR] %s: %s" % (type(e).__name__, e))
        return set()


# ─── 「참조」로 받은 메일 ───────────────────────────────────────────
_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def my_addresses(c, uid) -> set:
    out = set()
    for sql in ("SELECT email FROM users WHERE id=?", "SELECT address FROM mail_aliases WHERE user_id=?",
                "SELECT smtp_email FROM user_mail_creds WHERE user_id=?",
                "SELECT login_id || '@knknara.co.kr' FROM users WHERE id=?"):
        try:
            for r in c.execute(sql, (uid,)).fetchall():
                for e in _RE_EMAIL.findall((r[0] or "").lower()):
                    out.add(e)
        except Exception:
            pass
    return out


def is_cc(m, mine) -> bool:
    """내 주소가 받는 사람(첫 주소)이 아니고 참조에 있을 때만 True. 모르면 False(표시 안 함)."""
    if not mine or (m.get("direction") or "in") != "in":
        return False
    to = set(_RE_EMAIL.findall((m.get("to_email") or "").lower()))
    if to & mine:
        return False
    cc = set(_RE_EMAIL.findall((m.get("cc") or "").lower()))
    return bool(cc & mine)


# ─── 이전 대화(인용) 접기 ───────────────────────────────────────────
def split_quote_text(text):
    """글 메일 → (이번에 쓴 부분, 딸려 온 옛 글). 옛 글이 없거나 쓴 부분이 거의 없으면(전달 메일) 접지 않는다."""
    from .mail_signature import own_part
    t = (text or "").replace("\r", "")
    own = own_part(t)
    rest = t[len(own):] if t.startswith(own) else ""
    if not rest.strip() or len(re.sub(r"\s", "", own)) < 10:
        return t, ""
    return own.rstrip(), rest.lstrip("\n")


_QUOTE_TEXT = re.compile(
    r"^\s*(?:-{2,}\s*(?:original message|원본\s*메[시세]지|forwarded message|전달된?\s*메[시세]지)\s*-{2,}"
    r"|(?:from|보낸\s*사람)\s*[:：].{0,200}(?:sent|date|보낸\s*날짜|날짜)\s*[:：])", re.I | re.S)
_HEAD_FROM = re.compile(r"^\s*(?:from|보낸\s*사람|보낸이|발신)\s*[:：]", re.I)
_HEAD_NEXT = re.compile(r"(?:sent|date|subject|보낸\s*날짜|날짜|제목)\s*[:：]", re.I)
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
_BLOCK = {"div", "p", "table", "blockquote", "section", "article", "td", "center"}


class _QuoteFinder(HTMLParser):
    """인용이 시작되는 요소(시작 위치)와 그 부모가 닫히는 위치를 찾는다."""

    def __init__(self, src):
        super().__init__(convert_charrefs=True)
        self.src = src
        self.lines = [0]
        for ln in src.split("\n")[:-1]:
            self.lines.append(self.lines[-1] + len(ln) + 1)
        self.stack = []          # [(tag, start_off, attrs)]
        self.cut = None          # (start_off, depth)
        self.end = None
        self.text_before = []

    def off(self):
        ln, col = self.getpos()
        return self.lines[ln - 1] + col

    def handle_starttag(self, tag, attrs):
        o = self.off()
        if self.cut is None:
            a = {k: (v or "") for k, v in attrs}
            cls = a.get("class", "").lower()
            iid = a.get("id", "").lower()
            if (tag == "blockquote" or (tag == "div" and ("gmail_quote" in cls or iid in ("divrplyfwdmsg", "appendonsend")
                                                           or "moz-cite-prefix" in cls or "yahoo_quoted" in cls))):
                self.cut = (o, len(self.stack))
        if tag not in _VOID:
            self.stack.append((tag, o))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        o = self.off()
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                if self.cut is not None and self.end is None and i < self.cut[1]:
                    self.end = o            # 인용 요소의 부모가 닫히는 곳
                del self.stack[i:]
                break

    def _is_head(self, data):
        if _QUOTE_TEXT.match(data or ""):
            return True
        if _HEAD_FROM.match(data or ""):
            # 「보낸 사람:」 뒤(줄바꿈으로 나뉜 다음 글) 600자 안에 「보낸 날짜:/날짜:/제목:/Sent:」 가 오면 옛 글의 머리
            o = self.off() + len(data)
            nxt = re.sub(r"<[^>]+>", " ", self.src[o:o + 600])
            return bool(_HEAD_NEXT.search(nxt))
        return False

    def handle_data(self, data):
        if self.cut is None:
            if self._is_head(data):
                # 글로 된 「보낸 사람: … 날짜:」 머리 — 그 글을 품은 가장 가까운 블록 요소부터
                for i in range(len(self.stack) - 1, -1, -1):
                    if self.stack[i][0] in _BLOCK:
                        self.cut = (self.stack[i][1], i)
                        return
                self.cut = (self.off(), len(self.stack))
                return
            self.text_before.append(data or "")


def fold_quote_html(html):
    """서식 메일 → 인용 묶음부터 그 부모 끝까지를 <details> 로 접는다. 못 찾거나 위에 쓴 글이 거의 없으면 그대로."""
    if not html or len(html) > 1500000:
        return html
    try:
        f = _QuoteFinder(html)
        f.feed(html)
        f.close()
    except Exception:
        return html
    if not f.cut:
        return html
    before = re.sub(r"\s", "", "".join(f.text_before))
    if len(before) < 10:
        return html
    a = f.cut[0]
    b = f.end if (f.end is not None and f.end > a) else len(html)
    return (html[:a] + '<details class="knk-q"><summary>▸ 이전 메일 보기</summary>' + html[a:b] + "</details>" + html[b:])


QUOTE_CSS = ("details.knk-q{margin-top:14px;border-top:1px dashed #d1d5db;padding-top:8px}"
             "details.knk-q>summary{cursor:pointer;color:#6b7280;font-size:13px;list-style:none;user-select:none}"
             "details.knk-q>summary::-webkit-details-marker{display:none}"
             "details.knk-q[open]>summary{margin-bottom:8px}")
