# -*- coding: utf-8 -*-
"""메일 보내기 전 확인 — 서버가 보는 것 두 가지 (대표 2026-11-21 「신입사원 관점」 가 묶음).

  ① 다른 거래처 이름(4-2): 첨부 파일 이름·제목·내가 쓴 본문에 거래처 이름이 있는데,
     받는 사람(받는사람·참조·숨은참조) 중 그 거래처 사람이 없으면 알림.
     예) 「삼성전기_견적.xlsx」를 파트론에 보냄 → 「‘삼성전기’ 이야기가 있는데 받는 사람 중 삼성전기 사람이 없습니다」
  ② 처음 보내는 주소(4-1): 회사 밖 주소인데 내가 주고받은 적도 없고 주소록·거래처 담당자에도 없으면 알림
     + 비슷한 아는 주소가 있으면 「혹시 이 주소인가요?」(오타 · 비슷한 이름 잘못 고름).

원칙
  - 막지 않는다 — 알림만(화면이 「그래도 보내기」 한 번) · 대표 11-20 「입력하는 순간 실수를 찾아 알린다」
  - 내 메일함만 본다(남의 메일함 안 봄 · 자동 완성과 같은 원칙) · 주소록은 내가 볼 수 있는 것만(_vis_clause)
  - AI 안 씀 · 규칙만 · 쓰기 없음(읽기만)
  - 거래처 ↔ 주소 = 받은 메일 「거래처 폴더」와 같은 규칙(연락처 주소 정확 일치 → 없으면 한 거래처만 가리키는 회사 주소)
    + 거래처 담당자 표(customer_contacts) 주소도 함께.
"""
import re

OUR_DOMAINS = ("knknara.co.kr",)
OUR_NAMES = ("케이엔케이", "knk", "haist", "하이스트")
MAX_ADDRS = 60
MAX_TEXT = 20000

# 회사 이름 앞뒤 꾸밈말(비교용으로만 뺌)
_CORP_RE = re.compile(
    r"(\(\s*주\s*\)|㈜|주식\s*회사|유한\s*회사|\(\s*유\s*\)|"
    r"\b(co\.?\s*,?\s*ltd\.?|co\.?|ltd\.?|inc\.?|corp\.?|corporation|company|limited|llc|gmbh|jsc|"
    r"công\s*ty|tnhh|cổ\s*phần)\b|[.,])", re.I)
_LATIN = re.compile(r"[a-z]", re.I)
_ADDR_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def _dom(addr: str) -> str:
    return (addr or "").rsplit("@", 1)[-1].strip().lower()


def is_ours(addr: str) -> bool:
    d = _dom(addr)
    return bool(d) and any(d == o or d.endswith("." + o) for o in OUR_DOMAINS)


def norm_company(name: str) -> str:
    """「(주)드림텍」·「Dreamtech Co., Ltd.」 → 「드림텍」·「dreamtech」 (비교용)."""
    s = _CORP_RE.sub(" ", name or "")
    return re.sub(r"\s+", " ", s).strip().lower()


def _usable(alias: str) -> bool:
    """너무 짧거나 우리 회사 이름이면 찾지 않는다(잘못 잡힘 방지)."""
    if not alias:
        return False
    if any(o in alias for o in OUR_NAMES):
        return False
    if _LATIN.search(alias):
        return len(alias) >= 3
    return len(alias) >= 2


def lev(a: str, b: str, cap: int = 3) -> int:
    """편집 거리(cap 넘으면 cap+1)."""
    if a == b:
        return 0
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        lo = cur[0]
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
            lo = min(lo, cur[j])
        if lo > cap:
            return cap + 1
        prev = cur
    return prev[-1]


def parse_addrs(*fields) -> list:
    out, seen = [], set()
    for f in fields:
        for a in _ADDR_RE.findall(f or ""):
            k = a.strip().lower()
            if k not in seen:
                seen.add(k)
                out.append(k)
    return out[:MAX_ADDRS]


def _cols(c, table) -> set:
    try:
        return {r[1] for r in c.execute("PRAGMA table_info(%s)" % table).fetchall()}
    except Exception:
        return set()


# ── 거래처 이름·주소 ───────────────────────────────────────────────────────────
def customers(c) -> dict:
    """{cid: {"name": 화면 이름, "aliases": [비교용 이름…]}} — 쓰는 거래처만 · 연락처의 회사 이름(영문 등)도 별칭으로."""
    act = "is_active" in _cols(c, "customers")
    out = {}
    for r in c.execute("SELECT id, name FROM customers" + (" WHERE COALESCE(is_active,1)=1" if act else "")).fetchall():
        nm = (r["name"] or "").strip()
        if nm:
            out[r["id"]] = {"name": nm, "aliases": set()}
            a = norm_company(nm)
            if _usable(a):
                out[r["id"]]["aliases"].add(a)
    try:
        for r in c.execute("SELECT DISTINCT customer_id AS cid, company FROM shared_contacts "
                           "WHERE customer_id IS NOT NULL AND company IS NOT NULL AND company<>''").fetchall():
            if r["cid"] in out:
                a = norm_company(r["company"])
                if _usable(a):
                    out[r["cid"]]["aliases"].add(a)
    except Exception:
        pass
    # 두 거래처가 같은 별칭을 가지면(예: 계열사가 같은 영문 이름) 그 별칭은 쓰지 않는다 — 추측 안 함
    cnt = {}
    for v in out.values():
        for a in v["aliases"]:
            cnt[a] = cnt.get(a, 0) + 1
    for v in out.values():
        v["aliases"] = sorted(a for a in v["aliases"] if cnt[a] == 1)
    return out


def addr_customers(c, addrs) -> dict:
    """주소 → 거래처 번호(모르면 없음). ① 연락처·거래처 담당자 주소 정확 일치(한 거래처일 때) ② 한 거래처만 가리키는 회사 주소."""
    from .mail_store import _NO_DOMAIN_GROUP
    exact, dommap = {}, {}
    rows = []
    try:
        rows += [(r[0], r[1]) for r in c.execute(
            "SELECT lower(trim(email)), customer_id FROM shared_contacts WHERE customer_id IS NOT NULL AND email LIKE '%_@_%.%'").fetchall()]
    except Exception:
        pass
    try:
        rows += [(r[0], r[1]) for r in c.execute(
            "SELECT lower(trim(email)), customer_id FROM customer_contacts WHERE customer_id IS NOT NULL AND email LIKE '%_@_%.%'").fetchall()]
    except Exception:
        pass
    for em, cid in rows:
        exact.setdefault(em, set()).add(cid)
        d = _dom(em)
        if d and d not in _NO_DOMAIN_GROUP and not is_ours(em):
            dommap.setdefault(d, set()).add(cid)
    out = {}
    for a in addrs:
        s = exact.get(a)
        if s and len(s) == 1:
            out[a] = next(iter(s))
            continue
        if s and len(s) > 1:
            continue
        s = dommap.get(_dom(a))
        if s and len(s) == 1:
            out[a] = next(iter(s))
    return out


def find_mentions(text: str, custs: dict) -> list:
    """글 속 거래처 이름 → [(cid, 찾은 글자)] · 긴 이름이 이김(「삼성전기」 안의 「삼성」은 따로 안 셈)."""
    low = (text or "").lower()
    if not low:
        return []
    spans = []
    for cid, v in custs.items():
        for a in v["aliases"]:
            if _LATIN.search(a):
                pat = r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])"
            else:
                pat = re.escape(a)
            for mm in re.finditer(pat, low):
                spans.append((mm.start(), mm.end(), cid, text[mm.start():mm.end()]))
    keep = []
    for s in spans:
        if any(o is not s and o[0] <= s[0] and s[1] <= o[1] and (o[1] - o[0]) > (s[1] - s[0]) for o in spans):
            continue
        keep.append(s)
    out, seen = [], set()
    for s in sorted(keep):
        if s[2] not in seen:
            seen.add(s[2])
            out.append((s[2], s[3]))
    return out


# ── 아는 주소 ─────────────────────────────────────────────────────────────────
def known_addrs(c, user) -> set:
    """내가 아는 주소 = 내가 받은 메일 보낸 사람 + 내가 보낸 메일 받는 사람 + 내가 볼 수 있는 주소록 + 거래처 담당자 + 사내 직원."""
    uid = (user or {}).get("id")
    known = set()
    mcols = _cols(c, "mail_messages")      # 칸이 없는 DB(옛 DB·시험 DB)에서도 조용히 비지 않게 — 칸을 보고 고름
    blk = " AND COALESCE(is_blocked,0)=0" if "is_blocked" in mcols else ""
    for r in c.execute("SELECT DISTINCT lower(trim(from_email)) FROM mail_messages "
                       "WHERE user_id=? AND direction='in'" + blk + " AND from_email LIKE '%@%'", (uid,)).fetchall():
        if r[0]:
            known.add(r[0])
    for r in c.execute("SELECT to_email, cc, " + ("bcc" if "bcc" in mcols else "''") + " FROM mail_messages "
                       "WHERE user_id=? AND direction='out' AND COALESCE(is_deleted,0)=0", (uid,)).fetchall():
        for a in parse_addrs(r[0], r[1], r[2]):
            known.add(a)
    try:
        from .contacts import _vis_clause
        vsql, vargs = _vis_clause(user)
    except Exception:
        vsql, vargs = "(sc.created_by=? OR sc.visibility='company')", [uid]
    try:
        for r in c.execute("SELECT lower(trim(sc.email)) FROM shared_contacts sc WHERE sc.email LIKE '%@%'"
                           + ((" AND " + vsql) if vsql else ""), vargs).fetchall():
            if r[0]:
                known.add(r[0])
    except Exception as e:
        print("[MAIL-PRECHECK] 주소록 읽기 실패: %s" % type(e).__name__, flush=True)
    for sql in ("SELECT lower(trim(email)) FROM customer_contacts WHERE email LIKE '%@%'",
                "SELECT lower(trim(email)) FROM users WHERE email LIKE '%@%'"):
        try:
            for r in c.execute(sql).fetchall():
                if r[0]:
                    known.add(r[0])
        except Exception as e:
            print("[MAIL-PRECHECK] 주소 읽기 실패: %s" % type(e).__name__, flush=True)
    return known


def similar_known(addr: str, known: set, limit: int = 3) -> list:
    """처음 보는 주소와 비슷한 아는 주소 — 오타·비슷한 이름 잘못 고름.
    ① 같은 회사 주소(@ 뒤 같음) + 앞부분 1~2글자 다름 ② @ 뒤가 1~2글자 다른 아는 회사 주소(앞부분 같거나 1글자 다름)."""
    if "@" not in addr:
        return []
    loc, dom = addr.rsplit("@", 1)
    cand = []
    for k in known:
        if k == addr or "@" not in k:
            continue
        kl, kd = k.rsplit("@", 1)
        if kd == dom:
            if len(loc) >= 3:
                d = lev(loc, kl, 2)
                if 1 <= d <= 2:
                    cand.append((d, k))
        else:
            if len(dom) >= 6:
                dd = lev(dom, kd, 2)
                if 1 <= dd <= 2:
                    dl = lev(loc, kl, 1)
                    if dl <= 1:
                        cand.append((dd + dl, k))
    cand.sort()
    return [k for _, k in cand[:limit]]


# ── 한 번에 ───────────────────────────────────────────────────────────────────

# ── 11-21 마 묶음 4-3 — 본문 첫 줄에 부른 이름 ↔ 받는 사람 ─────────────────────────────
#   앞 메일을 베껴 쓰다 「박구매님」을 안 고치고 다른 사람에게 보내는 실수 · 이름을 아는 받는 사람이 있을 때만 봄
_TITLES = {"고객", "담당자", "담당", "관계자", "팀장", "과장", "부장", "차장", "대리", "주임", "사원", "대표", "대표이사", "사장",
           "회장", "이사", "상무", "전무", "실장", "소장", "본부장", "선생", "교수", "귀하", "프로", "매니저", "책임", "선임",
           "수석", "연구원", "위원", "고문", "부사장", "원장", "법인장", "반장", "조장", "센터장", "공장장", "여러분", "회원",
           "구매", "영업", "총무", "경리", "인사", "품질", "개발"}
_RE_GREET_KO = re.compile(r"(?<![가-힣])([가-힣]{1,4})(?:\s+([가-힣]{2,4}))?\s*님(?![가-힣])")
_RE_GREET_EN = re.compile(r"^\s*(?:dear|hi|hello)\s+(?:(?:mr|ms|mrs|miss|dr)\.?\s+)?([A-Za-z][A-Za-z\-]{1,20})\b", re.I)
_RE_NAMED = re.compile(r"\"?([^\"<>,;]{1,60}?)\"?\s*<\s*([^<>\s]+@[^<>\s]+)\s*>")


def greet_name(own: str) -> str:
    """본문 첫 두 줄에서 부른 이름(「박구매님」→ 박구매 · 「김 과장님」→ 김 · 「Dear Mr. Kim」→ Kim). 직함뿐이면 ""."""
    lines = [x.strip() for x in (own or "").replace("\r", "").split("\n") if x.strip()][:2]
    for li, ln in enumerate(lines):
        m = _RE_GREET_EN.match(ln)
        if m:
            return m.group(1)
        for m in _RE_GREET_KO.finditer(ln):
            if li > 0 and m.start() > 1:
                continue           # 둘째 줄은 줄 맨 앞에서 부를 때만(「어제 말씀하신 박구매님 것」은 부르는 말이 아님)
            t1, t2 = m.group(1), (m.group(2) or "")
            if t2 and t2 not in _TITLES:
                t1 = t2            # 「줄에 박구매님」 — 님 바로 앞 낱말이 직함이 아니면 그 낱말이 이름(「한드림 과장님」은 앞 낱말)
            if t1 in _TITLES or (len(t1) >= 2 and t1[:2] in ("안녕", "감사", "수고")):
                continue
            return t1
    return ""


def rec_names(c, user, raw_fields, addrs) -> dict:
    """받는 주소 → 아는 이름들(칸에 적힌 이름 · 내가 볼 수 있는 주소록 · 거래처 담당자 · 사내 직원)."""
    out = {a: set() for a in addrs}
    for f in raw_fields:
        for nm, a in _RE_NAMED.findall(f or ""):
            a = a.strip().lower()
            if a in out and nm.strip():
                out[a].add(nm.strip())
    if not addrs:
        return out
    q = ",".join("?" * len(addrs))
    try:
        from .contacts import _vis_clause
        vsql, vargs = _vis_clause(user)
    except Exception:
        vsql, vargs = "(sc.created_by=? OR sc.visibility='company')", [(user or {}).get("id")]
    for sql, args in (("SELECT lower(sc.email), sc.name FROM shared_contacts sc WHERE lower(sc.email) IN (" + q + ")"
                       + ((" AND " + vsql) if vsql else ""), list(addrs) + list(vargs)),
                      ("SELECT lower(email), name FROM customer_contacts WHERE lower(email) IN (" + q + ")", list(addrs)),
                      ("SELECT lower(email), name FROM users WHERE lower(email) IN (" + q + ")", list(addrs))):
        try:
            for r in c.execute(sql, args).fetchall():
                if r[0] in out and (r[1] or "").strip():
                    out[r[0]].add(r[1].strip())
        except Exception as e:
            print("[MAIL-PRECHECK] 받는 사람 이름 읽기 실패: %s" % str(e)[:120], flush=True)
    return out


def greet_warn(c, user, raw_fields, rec, own) -> list:
    g = greet_name(own)
    if not g or not rec:
        return []
    names = rec_names(c, user, raw_fields, rec)
    known = [(a, n) for a in rec for n in names.get(a, ())]
    if not known:
        return []                      # 받는 사람 이름을 하나도 모름 — 판단하지 않음
    gl = g.lower()
    if re.match(r"^[a-z]", gl) and not any(re.search(r"[A-Za-z]", n) for _a, n in known):
        return []                      # 영어로 불렀는데 아는 이름이 모두 한글 — 「Mr. Han」↔「한드림」 은 맞춰 볼 수 없음
    for a, n in known:
        nl = n.lower()
        if (len(g) == 1 and nl.startswith(gl)) or (len(g) > 1 and (gl in nl or nl in gl)):
            return []
    for a in rec:                      # 영어 이름은 주소 앞부분(kim@…)도 봄
        if len(g) > 1 and re.match(r"^[a-z]", gl) and gl in a.split("@")[0]:
            return []
    shown = ["받는 사람: " + ", ".join(sorted({n for _a, n in known})[:6])]
    return [{"ic": "🙋", "kind": "greet",
             "t": "본문 첫 줄에 「%s」 님을 불렀는데, 받는 사람에 그 이름이 없습니다" % g,
             "d": "앞 메일을 고쳐 쓰다 이름을 그대로 두지 않았는지 봐 주세요. 맞으면 그대로 보내도 됩니다.",
             "who": shown, "fix": []}]

def run(c, user, to="", cc="", bcc="", subject="", own="", att_names=None) -> list:
    """보내기 전 알림 목록 [{ic, t, d, who:[…], fix:[{from,to}]}] — 비면 알림 없음."""
    rec = parse_addrs(to, cc, bcc)
    ext = [a for a in rec if not is_ours(a)]
    warns = []
    try:   # 11-21 마 묶음 4-3 — 사내·바깥 모두
        gw = greet_warn(c, user, (to, cc, bcc), rec, own)
    except Exception as e:
        print("[MAIL-PRECHECK] 부른 이름 확인 실패: %s" % str(e)[:120], flush=True)
        gw = []
    if not ext:
        return gw             # 사내끼리 — 거래처 이야기도 정상 · 처음 주소도 해당 없음
    custs = customers(c)
    a2c = addr_customers(c, rec)
    rec_cids = {a2c[a] for a in rec if a in a2c}
    names = {cid: v["name"] for cid, v in custs.items()}

    # ② 처음 보내는 주소 (먼저 — 주소가 틀리면 거래처 비교도 틀어짐)
    known = known_addrs(c, user)
    for a in ext:
        if a in known:
            continue
        sim = similar_known(a, known)
        w = {"ic": "🆕", "kind": "first",
             "t": "처음 보내는 주소입니다: " + a,
             "d": "내가 주고받은 적도 없고, 주소록·거래처 담당자에도 없습니다. 주소가 맞는지 한 번 더 봐 주세요.",
             "who": [], "fix": []}
        for s in sim:
            cid = a2c.get(s) or addr_customers(c, [s]).get(s)
            w["who"].append("혹시 이 주소인가요? " + s + ((" (" + names[cid] + ")") if cid in names else ""))
            w["fix"].append({"from": a, "to": s})
        warns.append(w)
        if len(warns) >= 5:
            break

    # ① 다른 거래처 이름
    text_src = [("파일 이름", n) for n in (att_names or []) if n] + [("제목", subject or ""), ("본문", (own or "")[:MAX_TEXT])]
    found = {}
    for where, txt in text_src:
        for cid, hit in find_mentions(txt, custs):
            if cid in rec_cids:
                continue
            f = found.setdefault(cid, {"hit": hit, "where": []})
            lab = where + (": " + txt if where == "파일 이름" else "")
            if lab not in f["where"]:
                f["where"].append(lab)
    if found:
        rc_names = sorted({names[x] for x in rec_cids if x in names})
        unk = [a for a in ext if a not in a2c]
        recv = ("받는 회사: " + ", ".join(rc_names)) if rc_names else ""
        if unk:
            recv = (recv + " · " if recv else "") + "거래처를 모르는 주소: " + ", ".join(unk[:4]) + (" 외" if len(unk) > 4 else "")
        for cid, f in list(found.items())[:5]:
            nm = names.get(cid, f["hit"])
            warns.append({"ic": "🏷", "kind": "other_cust",
                          "t": "「%s」 이야기가 있는데, 받는 사람 중 %s 사람이 없습니다" % (f["hit"], nm),
                          "d": "다른 회사에 갈 내용(견적·도면·가격)이 아닌지 확인해 주세요. 받는 사람이 %s 사람이 맞으면 그대로 보내도 됩니다." % nm,
                          "who": ["찾은 곳 — " + w for w in f["where"][:4]] + ([recv] if recv else []), "fix": []})
    return warns + gw
