"""
받은 메일 폴더(아웃룩식) — 대표 지시 2026-11-17
=================================================================
「지금 아웃룩을 이런 식으로 구분해서 쓰고 있어」 → 이음웍스 받은편지함 왼쪽에 같은 폴더.
  1.고객사(업체별) · 2.기타 고객사 · 3.외주업체 · 4.PIN BLOCK 업체 · 5.CHIP업체 · 6.케이엔케이(부서별) · 일반

메일 → 폴더는 **보낸 사람 단위**로 정한다(아웃룩 규칙과 같다). 먼저 맞는 것:
  ① 내가 정한 규칙(「📁 이 폴더로」 — 주소 하나 / 회사 주소 @ 뒤)
  ② 우리 회사 주소(@knknara.co.kr) → 직원 명부의 부서(6.케이엔케이 아래 「01_기술영업팀」…)
     명부에서 못 찾으면 서명의 부서 이름 → 그래도 모르면 「KNK 기타」
  ③ 거래처: 주소록·거래처 담당자 이메일 정확 일치 → 같은 회사 주소(@ 뒤)가 한 거래처만 가리킬 때
  ④ 공급업체(자재구매 명단 — 읽기만): 이메일 정확 일치 → 같은 회사 주소가 한 업체만 가리킬 때
  ⑤ 서명의 회사 이름이 거래처 이름·폴더 이름과 **한 곳만** 정확히 같을 때
  거래처는 그 이름의 폴더로, 폴더가 없는 거래처는 「2.기타 고객사」로. 나머지 = 「일반」.
  둘 이상에 걸리면 짐작하지 않는다(데이터 연결 안전 원칙).

폴더 구조는 **사람마다 따로**(user_id). 대표 계정은 처음 열 때 아웃룩 구조 그대로 만들어 둔다.
메일 내용은 이 서버 안에서만 읽는다(외부 전송·AI 없음).
"""
from __future__ import annotations

import re

OUR_DOMAINS = ("knknara.co.kr",)

# 대표 아웃룩 폴더(11-17 화면 그대로) — 6.케이엔케이 아래는 회사 부서표(teams)에서 자동.
SEED = (
    ("1.고객사", "customer", ("탑엔지니어링", "세경하이테크", "두성테크", "드림텍", "삼성전기", "삼성전자",
                            "시노펙스", "씨젠", "아이마켓코리아", "에스아이플렉스", "욱광", "이엠텍", "엠씨넥스",
                            "일진디스플레이", "코리아이플렛폼", "파인텍", "파트론", "하나머티리얼즈", "한국성전")),
    ("2.기타 고객사", "other_customer", ()),
    ("3.외주업체", "vendor", ("배송 및 포장업체", "와이제이전자")),
    ("4.PIN BLOCK 업체", "vendor", ("GTS", "SRC", "다온", "디플러스", "메카텍", "이니텍")),
    ("5.CHIP업체", "vendor", ("AMS", "STMicroelectronics", "TLI", "리딩유아이", "멜파스", "시냅틱스",
                             "실리콘웍스", "싸이프레스", "어보브반도체")),
    ("6.케이엔케이", "staff", ()),
)
GROUP_KINDS = ("customer", "other_customer", "vendor", "staff", "")

_OK = {"v": False}
_CACHE = {}        # (user_id) -> (stamp, result)
_SIG_CACHE = {}    # (sender, latest_mail_id) -> (company, department)


def ensure(c) -> None:
    if _OK["v"]:
        return
    c.execute("""CREATE TABLE IF NOT EXISTS mail_folders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        parent_id INTEGER,
        name TEXT NOT NULL,
        sort INTEGER DEFAULT 0,
        kind TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now','localtime')))""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_mailfold_user ON mail_folders(user_id, parent_id)")
    c.execute("""CREATE TABLE IF NOT EXISTS mail_folder_rules(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        folder_id INTEGER NOT NULL,
        kind TEXT NOT NULL,
        pattern TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(user_id, kind, pattern))""")
    # 11-17 2차: 폴더마다 「다른 이름」(영문 이름·회사 주소) — 서명·보낸 사람 이름·회사 주소와 맞출 때 같이 본다
    try:
        c.execute("ALTER TABLE mail_folders ADD COLUMN aliases TEXT")
    except Exception:
        pass
    _OK["v"] = True


# 대표 아웃룩 폴더의 영문 이름(회사 주소 @ 뒤가 보통 영문이라 한글 폴더 이름만으로는 못 맞춤).
#   이름 맞추기에만 쓴다 — 관리 화면에서 보이고 고칠 수 있다. 점(.)이 들어간 것은 회사 주소 그대로.
SEED_ALIASES = {
    "탑엔지니어링": "TOP Engineering, topeng",
    "세경하이테크": "Sekyung Hitech, sekyunghitech",
    "두성테크": "Doosung Tech, doosungtech",
    "드림텍": "Dreamtech",
    "삼성전기": "Samsung Electro-Mechanics, SEMCO",
    "삼성전자": "Samsung Electronics",
    "시노펙스": "Synopex",
    "씨젠": "Seegene",
    "아이마켓코리아": "iMarketKorea, imarketkorea",
    "에스아이플렉스": "SI Flex, siflex",
    "이엠텍": "EM-Tech, emtech",
    "엠씨넥스": "MCNEX",
    "일진디스플레이": "Iljin Display, iljindisplay",
    "파트론": "Partron",
    "하나머티리얼즈": "Hana Materials, hanamaterials",
    "리딩유아이": "Leading UI, leadingui",
    "멜파스": "MELFAS",
    "시냅틱스": "Synaptics",
    "실리콘웍스": "Silicon Works, siliconworks, LX Semicon, lxsemicon",
    "싸이프레스": "Cypress",
    "어보브반도체": "ABOV, abov",
    "STMicroelectronics": "st.com, 에스티마이크로일렉트로닉스",
    "AMS": "ams.com, ams-osram.com, ams OSRAM",
}


# ─── 이름 맞추기 ────────────────────────────────────────────────────
_RE_CORP = re.compile(r"\(주\)|㈜|\(유\)|\(株\)|주식회사|유한회사|"
                      r"(?<![a-z])(?:co\.?,?\s*ltd\.?|corporation|corp\.?|inc\.?|limited|ltd\.?|company|vina|vietnam)(?![a-z])",
                      re.I)


def norm_name(s: str) -> str:
    """회사 이름 비교용 — ㈜·주식회사·Co., Ltd. 와 띄어쓰기·기호를 뺀 소문자."""
    t = _RE_CORP.sub(" ", s or "")
    t = re.sub(r"[\s\-_.,·&/()\[\]'\"]+", "", t)
    return t.lower()


_RE_HANGUL = re.compile(r"[가-힣]")
_RE_TOK = re.compile(r"[^0-9a-zA-Z가-힣]+")


class NameIndex:
    """폴더 이름·다른 이름 → 폴더. 글에서 폴더를 찾을 때 **한 곳만** 걸릴 때만 쓴다.
    - 같음: 글 전체(㈜·띄어쓰기 뺀)가 이름과 같음
    - 들어 있음: 한글 3자 이상 / 영문 5자 이상 이름이 글 안에 있음
    - 낱말 같음: 짧은 이름(다온·씨젠·GTS·SRC…)은 낱말 하나가 정확히 같을 때만(「김다온」은 안 걸림)."""

    def __init__(self, items):
        self.exact, self.contain, self.short, self.dom, self.label = {}, [], {}, {}, []
        for fid, raw in items:
            raw = (raw or "").strip()
            if not raw:
                continue
            if "." in raw and " " not in raw and not _RE_HANGUL.search(raw):
                self.dom.setdefault(raw.lower().lstrip("@"), set()).add(fid)
                continue
            n = norm_name(raw)
            if not n:
                continue
            self.exact.setdefault(n, set()).add(fid)
            long_enough = (len(n) >= 3) if _RE_HANGUL.search(n) else (len(n) >= 5)
            if long_enough:
                self.contain.append((n, fid))
            else:
                self.short.setdefault(n, set()).add(fid)
            if not _RE_HANGUL.search(n) and len(n) >= 4:
                self.label.append((n, fid))

    def find(self, text):
        """글 → 폴더 id 집합."""
        n = norm_name(text)
        if not n:
            return set()
        if n in self.exact:
            return set(self.exact[n])
        hit = {fid for k, fid in self.contain if k in n}
        for t in _RE_TOK.split(text or ""):
            t2 = norm_name(t)
            if t2 and t2 in self.short:
                hit |= self.short[t2]
        return hit

    def find_domain(self, d):
        """회사 주소(@ 뒤) → 폴더 id 집합. ① 적어 둔 주소 그대로(하위 주소 포함) ② 맨 앞 이름이 영문 이름과 같거나 그것으로 시작."""
        d = (d or "").lower()
        hit = set()
        for k, ids in self.dom.items():
            if d == k or d.endswith("." + k):
                hit |= ids
        if hit:
            return hit
        lab = re.sub(r"[^a-z0-9]", "", d.split(".")[0])
        if len(lab) >= 4:
            for k, fid in self.label:
                if lab == k or (len(k) >= 5 and lab.startswith(k)):
                    hit.add(fid)
        return hit


def _dom(e: str) -> str:
    e = (e or "").strip().lower()
    return e.rsplit("@", 1)[1] if "@" in e else ""


def _free_domains():
    from .mail_store import _NO_DOMAIN_GROUP
    return set(_NO_DOMAIN_GROUP)


# ─── 폴더 만들기·읽기 ──────────────────────────────────────────────
def has_tree(c, uid) -> bool:
    ensure(c)
    return bool(c.execute("SELECT 1 FROM mail_folders WHERE user_id=? LIMIT 1", (uid,)).fetchone())


def seed(c, uid) -> bool:
    """아웃룩 구조 그대로 만든다 — 폴더가 하나도 없을 때만(있으면 손대지 않음)."""
    ensure(c)
    if has_tree(c, uid):
        return False
    for gi, (gname, kind, kids) in enumerate(SEED):
        cur = c.execute("INSERT INTO mail_folders(user_id, parent_id, name, sort, kind) VALUES(?,?,?,?,?)",
                        (uid, None, gname, (gi + 1) * 10, kind))
        gid = cur.lastrowid
        for ki, kname in enumerate(kids):
            c.execute("INSERT INTO mail_folders(user_id, parent_id, name, sort, kind) VALUES(?,?,?,?,'')",
                      (uid, gid, kname, (ki + 1) * 10))
    _CACHE.pop(uid, None)
    return True


def seed_if_owner(c, uid) -> bool:
    """대표 계정(메일 기본 주인)만 처음 열 때 자동으로 — 다른 사람은 관리 화면의 단추로."""
    try:
        from .mail_store import default_owner
        if default_owner(c) != uid:
            return False
    except Exception:
        return False
    made = seed(c, uid)
    apply_seed_aliases(c, uid)
    return made


def apply_seed_aliases(c, uid) -> int:
    """대표 아웃룩 폴더에 영문 이름을 채운다 — 아직 비어 있는(NULL) 폴더만(사람이 고친 것은 그대로)."""
    ensure(c)
    n = 0
    for name, al in SEED_ALIASES.items():
        n += c.execute("UPDATE mail_folders SET aliases=? WHERE user_id=? AND name=? AND aliases IS NULL "
                       "AND parent_id IS NOT NULL", (al, uid, name)).rowcount
    if n:
        _CACHE.pop(uid, None)
    return n


def set_aliases(c, uid, fid, aliases) -> bool:
    al = ", ".join(x.strip() for x in re.split(r"[,\n]+", aliases or "") if x.strip())[:300]
    n = c.execute("UPDATE mail_folders SET aliases=? WHERE id=? AND user_id=?", (al, fid, uid)).rowcount
    _CACHE.pop(uid, None)
    return bool(n)


def folders(c, uid) -> list:
    ensure(c)
    return [dict(r) for r in c.execute(
        "SELECT id, parent_id, name, sort, COALESCE(kind,'') AS kind, COALESCE(aliases,'') AS aliases "
        "FROM mail_folders WHERE user_id=? "
        "ORDER BY sort, id", (uid,)).fetchall()]


def teams(c) -> list:
    try:
        return [dict(r) for r in c.execute(
            "SELECT id, COALESCE(code,'') AS code, name, COALESCE(display_order,0) AS ord FROM teams "
            "ORDER BY COALESCE(display_order,0), code, id").fetchall()]
    except Exception:
        return []


def team_label(t: dict) -> str:
    code = (t.get("code") or "").strip()
    return ("%s_%s" % (code, t["name"])) if code and code.isdigit() else t["name"]


def rules(c, uid) -> list:
    ensure(c)
    return [dict(r) for r in c.execute(
        "SELECT r.id, r.folder_id, r.kind, r.pattern, r.created_at, f.name AS folder_name "
        "FROM mail_folder_rules r LEFT JOIN mail_folders f ON f.id=r.folder_id "
        "WHERE r.user_id=? ORDER BY r.id DESC", (uid,)).fetchall()]


# ─── 분류 ─────────────────────────────────────────────────────────
def _stamp(c, uid):
    a = c.execute("SELECT COUNT(*), COALESCE(MAX(id),0) FROM mail_messages WHERE user_id=? AND direction='in'",
                  (uid,)).fetchone()
    b = c.execute("SELECT COUNT(*), COALESCE(MAX(id),0) FROM mail_folders WHERE user_id=?", (uid,)).fetchone()
    r = c.execute("SELECT COUNT(*), COALESCE(MAX(id),0) FROM mail_folder_rules WHERE user_id=?", (uid,)).fetchone()
    nm = c.execute("SELECT COALESCE(group_concat(id||':'||name||':'||COALESCE(parent_id,0)||':'||sort||':'||COALESCE(aliases,''),'|'),'') "
                   "FROM mail_folders WHERE user_id=?", (uid,)).fetchone()
    # 주소록·거래처 담당자·직원이 바뀌면 다시 계산
    ex = []
    for sql in ("SELECT COUNT(*), COALESCE(MAX(updated_at),'') FROM shared_contacts",
                "SELECT COUNT(*), COALESCE(MAX(id),0) FROM customer_contacts",
                "SELECT COUNT(*), COALESCE(MAX(id),0) FROM customers",
                "SELECT COUNT(*), COALESCE(SUM(COALESCE(team_id,0)),0) FROM users",
                "SELECT COUNT(*), COALESCE(MAX(id),0) FROM suppliers"):
        try:
            ex.append(tuple(c.execute(sql).fetchone()))
        except Exception:
            ex.append(None)
    return (tuple(a), tuple(b), tuple(r), nm[0], tuple(ex))


def _maps(c):
    """주소 → 거래처·공급업체·직원 지도."""
    free = _free_domains()
    cust_exact, cust_dom = {}, {}
    for sql in ("SELECT lower(trim(email)) AS e, customer_id AS cid FROM shared_contacts "
                "WHERE email LIKE '%_@_%.%' AND customer_id IS NOT NULL",
                "SELECT lower(trim(email)) AS e, customer_id AS cid FROM customer_contacts "
                "WHERE email LIKE '%_@_%.%' AND customer_id IS NOT NULL"):
        try:
            for r in c.execute(sql).fetchall():
                cust_exact.setdefault(r["e"], set()).add(r["cid"])
                d = _dom(r["e"])
                if d and d not in free:
                    cust_dom.setdefault(d, set()).add(r["cid"])
        except Exception:
            pass
    sup_exact, sup_dom = {}, {}
    try:
        for r in c.execute("SELECT id, lower(trim(email)) AS e FROM suppliers WHERE email LIKE '%_@_%.%'").fetchall():
            for e in re.split(r"[,;\s]+", r["e"] or ""):
                if "@" not in e:
                    continue
                sup_exact.setdefault(e, set()).add(r["id"])
                d = _dom(e)
                if d and d not in free:
                    sup_dom.setdefault(d, set()).add(r["id"])
    except Exception:
        pass
    customers, suppliers = {}, {}
    try:
        for r in c.execute("SELECT id, name FROM customers").fetchall():
            customers[r["id"]] = r["name"] or ""
    except Exception:
        pass
    try:
        for r in c.execute("SELECT id, name FROM suppliers").fetchall():
            suppliers[r["id"]] = r["name"] or ""
    except Exception:
        pass
    # 직원: 주소 → 부서
    staff_addr, staff_login, staff_name = {}, {}, {}
    try:
        urows = c.execute("SELECT id, name, login_id, lower(trim(COALESCE(email,''))) AS e, team_id, is_active "
                          "FROM users").fetchall()
    except Exception:
        urows = []
    uteam = {r["id"]: r["team_id"] for r in urows}
    for r in urows:
        if r["e"] and "@" in r["e"]:
            staff_addr.setdefault(r["e"], set()).add(r["team_id"])
        if r["is_active"] and r["login_id"]:
            staff_login.setdefault((r["login_id"] or "").strip().lower(), set()).add(r["team_id"])
        if r["is_active"] and r["name"]:
            staff_name.setdefault((r["name"] or "").strip(), set()).add(r["team_id"])
    for sql in ("SELECT user_id, lower(trim(smtp_email)) AS e FROM user_mail_creds WHERE smtp_email LIKE '%@%'",
                "SELECT user_id, lower(trim(address)) AS e FROM mail_aliases WHERE address LIKE '%@%'"):
        try:
            for r in c.execute(sql).fetchall():
                if r["user_id"] in uteam:
                    staff_addr.setdefault(r["e"], set()).add(uteam[r["user_id"]])
        except Exception:
            pass
    return {"free": free, "cust_exact": cust_exact, "cust_dom": cust_dom, "sup_exact": sup_exact,
            "sup_dom": sup_dom, "customers": customers, "suppliers": suppliers,
            "staff_addr": staff_addr, "staff_login": staff_login, "staff_name": staff_name}


def _one(s):
    s = {x for x in (s or ()) if x is not None}
    return next(iter(s)) if len(s) == 1 else None


def _sig_of(c, sender, mail_id, from_name):
    """그 보낸 사람의 가장 최근 메일 서명 → (회사, 부서). 서버 안에서만 읽음."""
    key = (sender, mail_id)
    if key in _SIG_CACHE:
        return _SIG_CACHE[key]
    comp = dept = ""
    try:
        from . import mail_signature as _ms
        r = c.execute("SELECT substr(COALESCE(body_text,''),1,20000) AS t, "
                      "substr(COALESCE(body_html,''),1,60000) AS h FROM mail_messages WHERE id=?",
                      (mail_id,)).fetchone()
        if r:
            text = _ms.html_to_lines(r["h"] or "") if (r["h"] or "").strip() else ""
            d = _ms.draft_from_text(text, from_name or "", sender) if text.strip() else None
            if d is None or not d.get("sig_text"):
                d = _ms.draft_from_text(r["t"] or "", from_name or "", sender)
            f = (d or {}).get("fields") or {}
            comp, dept = (f.get("company") or "").strip(), (f.get("department") or "").strip()
    except Exception:
        comp = dept = ""
    if len(_SIG_CACHE) > 20000:
        _SIG_CACHE.clear()
    _SIG_CACHE[key] = (comp, dept)
    return comp, dept


def classify(c, uid) -> dict:
    """보낸 사람별 폴더 열쇠. 반환 {
        'senders': {email: {'key','how','n','u'}},
        'nodes':   [{key,name,depth,n,u,kind,children:[...]}],   # 화면용 나무(묶음 → 자식)
        'labels':  {key: 이름}, 'keys_of': {key: set(자기+자손 열쇠)} }
    열쇠: 'f<폴더id>' · 't<부서id>'(6.케이엔케이 아래) · 'tx'(KNK 기타) · 'gen'(일반)."""
    ensure(c)
    st = _stamp(c, uid)
    hit = _CACHE.get(uid)
    if hit and hit[0] == st:
        return hit[1]
    fl = folders(c, uid)
    by_id = {f["id"]: f for f in fl}
    groups = [f for f in fl if not f["parent_id"]]
    kids = {}
    for f in fl:
        if f["parent_id"] and f["parent_id"] in by_id:
            kids.setdefault(f["parent_id"], []).append(f)
    staff_g = next((g for g in groups if g["kind"] == "staff"), None)
    other_g = next((g for g in groups if g["kind"] == "other_customer"), None)
    M = _maps(c)
    tlist = teams(c)
    tmap = {t["id"]: t for t in tlist}
    tname = {}
    for t in tlist:
        tname.setdefault(norm_name(t["name"]), set()).add(t["id"])
    # 폴더 이름 → 폴더(묶음 아래 칸만 · 같은 이름 둘이면 안 씀)
    leaf_by_name = {}
    for f in fl:
        if f["parent_id"]:
            leaf_by_name.setdefault(norm_name(f["name"]), set()).add(f["id"])
    # 이름·다른 이름(영문·회사 주소) 찾기 — 묶음 아래 폴더만
    _items = []
    for f in fl:
        if f["parent_id"]:
            _items.append((f["id"], f["name"]))
            for a in re.split(r"[,\n]+", f.get("aliases") or ""):
                if a.strip():
                    _items.append((f["id"], a.strip()))
    idx = NameIndex(_items)
    cust_by_name = {}
    for cid, nm in M["customers"].items():
        cust_by_name.setdefault(norm_name(nm), set()).add(cid)

    def folder_for_customer(cid):
        nm = norm_name(M["customers"].get(cid, ""))
        fid = _one(leaf_by_name.get(nm)) if nm else None
        if fid:
            return "f%d" % fid, "거래처"
        if other_g:
            return "f%d" % other_g["id"], "거래처(폴더 없음)"
        return None

    def folder_for_supplier(sid):
        nm = norm_name(M["suppliers"].get(sid, ""))
        fid = _one(leaf_by_name.get(nm)) if nm else None
        return ("f%d" % fid, "공급업체") if fid else None

    rl = {}
    for r in c.execute("SELECT folder_id, kind, pattern FROM mail_folder_rules WHERE user_id=?", (uid,)).fetchall():
        if r["folder_id"] in by_id:
            rl[(r["kind"], (r["pattern"] or "").lower())] = r["folder_id"]

    from .mail_cleanup import _RE_ROBOT
    senders = {}
    _last_ids = {}
    rows = c.execute(
        "SELECT lower(from_email) AS e, MAX(from_name) AS nm, MAX(id) AS last_id, COUNT(*) AS n, "
        "SUM(CASE WHEN is_read=0 THEN 1 ELSE 0 END) AS u FROM mail_messages "
        "WHERE user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0 "
        "GROUP BY lower(from_email)", (uid,)).fetchall()
    for r in rows:
        e = (r["e"] or "").strip()
        d = _dom(e)
        key, how = None, ""
        # ① 내 규칙
        if (("email", e) in rl):
            key, how = "f%d" % rl[("email", e)], "내 규칙(주소)"
        elif d and ("domain", d) in rl:
            key, how = "f%d" % rl[("domain", d)], "내 규칙(회사 주소 @%s)" % d
        # ② 우리 회사
        elif d in OUR_DOMAINS:
            if staff_g:
                tid = _one(M["staff_addr"].get(e))
                how = "직원 명부"
                if tid is None:
                    tid = _one(M["staff_login"].get(e.split("@")[0]))
                    how = "직원 명부(로그인 아이디)"
                if tid is None:
                    try:
                        from .mail_signature import _clean_header_name
                        hn = _clean_header_name(r["nm"] or "")[0]
                    except Exception:
                        hn = ""
                    tid = _one(M["staff_name"].get(hn)) if hn else None
                    how = "직원 명부(이름)"
                if tid is None:
                    _comp, dept = _sig_of(c, e, r["last_id"], r["nm"])
                    dn = norm_name(dept)
                    tid = _one(tname.get(dn)) if dn else None
                    if tid is None and dn:
                        # 「기술영업팀 과장」처럼 붙어 있는 경우 — 부서 이름이 한 곳만 들어 있을 때
                        hits = {t for k, ts in tname.items() if k and len(k) >= 3 and k in dn for t in ts}
                        tid = _one(hits)
                    how = "서명의 부서"
                if tid is not None and tid in tmap:
                    key = "t%d" % tid
                else:
                    key, how = "tx", "KNK(부서 모름)"
        else:
            # ③ 거래처 · ④ 공급업체
            cid = _one(M["cust_exact"].get(e))
            if cid is not None and cid in M["customers"]:
                got = folder_for_customer(cid)
                if got:
                    key, how = got[0], got[1] + "(주소록·담당자)"
            if key is None and not M["cust_exact"].get(e) and d and d not in M["free"]:
                cid = _one(M["cust_dom"].get(d))
                if cid is not None and cid in M["customers"]:
                    got = folder_for_customer(cid)
                    if got:
                        key, how = got[0], got[1] + "(같은 회사 주소)"
            if key is None:
                sid = _one(M["sup_exact"].get(e))
                if sid is None and d and d not in M["free"] and not M["sup_exact"].get(e):
                    sid = _one(M["sup_dom"].get(d))
                if sid is not None:
                    got = folder_for_supplier(sid)
                    if got:
                        key, how = got[0], got[1]
            # ⑤ 회사 주소(@ 뒤)가 폴더의 영문 이름·적어 둔 주소와 같음(예: @partron.co.kr → 파트론)
            if key is None and d and d not in M["free"]:
                fid = _one(idx.find_domain(d))
                if fid:
                    key, how = "f%d" % fid, "회사 주소 @%s = 폴더 이름" % d
            # ⑥ 서명의 회사 이름(사람 주소만 — 알림·광고 주소는 건너뜀)
            if key is None and not _RE_ROBOT.match(e.split("@")[0] or ""):
                comp, _dept = _sig_of(c, e, r["last_id"], r["nm"])
                cn = norm_name(comp)
                if cn and len(cn) >= 2:
                    fid = _one(leaf_by_name.get(cn)) or _one(idx.find(comp))
                    if fid:
                        key, how = "f%d" % fid, "서명의 회사 이름"
                    else:
                        cid = _one(cust_by_name.get(cn))
                        if cid is not None:
                            got = folder_for_customer(cid)
                            if got:
                                key, how = got[0], got[1] + "(서명의 회사 이름)"
            # ⑦ 보낸 사람 이름 칸(예: 「홍길동(드림텍)」「Dreamtech Kim」)
            if key is None and r["nm"]:
                fid = _one(idx.find(r["nm"]))
                if fid:
                    key, how = "f%d" % fid, "보낸 사람 이름의 회사"
        if key is None:
            key, how = "gen", "일반"
        senders[e] = {"key": key, "how": how, "n": r["n"] or 0, "u": r["u"] or 0}
        _last_ids[e] = r["last_id"]

    # ⑧ 같은 회사 주소의 다른 사람이 폴더 **한 곳**으로만 갔으면 나머지도 그리로(개인 메일·우리 회사 주소 제외)
    by_dom = {}
    for e2, s2 in senders.items():
        d2 = _dom(e2)
        if s2["key"].startswith("f") and d2 and d2 not in M["free"] and d2 not in OUR_DOMAINS \
                and not s2["how"].startswith("내 규칙(주소)"):
            by_dom.setdefault(d2, set()).add(s2["key"])
    for e2, s2 in senders.items():
        if s2["key"] == "gen":
            d2 = _dom(e2)
            ks = by_dom.get(d2)
            if ks and len(ks) == 1:
                s2["key"] = next(iter(ks))
                s2["how"] = "같은 회사 주소(@%s)의 다른 사람이 이 폴더" % d2

    cnt = {}
    for s in senders.values():
        a = cnt.setdefault(s["key"], [0, 0])
        a[0] += s["n"]
        a[1] += s["u"]

    labels, keys_of, nodes = {}, {}, []
    for g in groups:
        gk = "f%d" % g["id"]
        labels[gk] = g["name"]
        ch = []
        for f in kids.get(g["id"], []):
            fk = "f%d" % f["id"]
            labels[fk] = f["name"]
            keys_of[fk] = {fk}
            ch.append({"key": fk, "name": f["name"], "n": cnt.get(fk, [0, 0])[0], "u": cnt.get(fk, [0, 0])[1],
                       "assignable": True})
        if g["kind"] == "staff":
            for t in tlist:
                tk = "t%d" % t["id"]
                labels[tk] = team_label(t)
                keys_of[tk] = {tk}
                if tk in cnt:
                    ch.append({"key": tk, "name": team_label(t), "n": cnt[tk][0], "u": cnt[tk][1],
                               "assignable": False})
            labels["tx"] = "KNK 기타(부서 모름)"
            keys_of["tx"] = {"tx"}
            if "tx" in cnt:
                ch.append({"key": "tx", "name": "KNK 기타(부서 모름)", "n": cnt["tx"][0], "u": cnt["tx"][1],
                           "assignable": False})
        ks = {gk} | {x["key"] for x in ch}
        keys_of[gk] = ks
        nodes.append({"key": gk, "name": g["name"], "kind": g["kind"], "children": ch,
                      "n": sum(cnt.get(k, [0, 0])[0] for k in ks), "u": sum(cnt.get(k, [0, 0])[1] for k in ks),
                      "assignable": g["kind"] != "staff"})
    labels["gen"] = "일반"
    keys_of["gen"] = {"gen"}
    res = {"senders": senders, "nodes": nodes, "labels": labels, "keys_of": keys_of,
           "gen": {"n": cnt.get("gen", [0, 0])[0], "u": cnt.get("gen", [0, 0])[1]},
           "_idx": idx, "_last": dict(_last_ids)}
    _CACHE[uid] = (st, res)
    return res


_RE_TAG = re.compile(r"[\[(（【<〔]\s*([^\])）】>〕]{2,24}?)\s*[\])）】>〕]")


def general_groups(c, uid, res, limit=300) -> list:
    """「일반」에 남은 메일을 보낸 곳(회사 주소 @ 뒤 · 개인 메일은 그 주소)별로 묶는다 — 일반 정리 화면용.
    단서(서명의 회사 이름 · 제목의 [회사])는 **추천**만 한다(사람이 누르기 전에는 옮기지 않음)."""
    free = _free_domains()
    idx = res.get("_idx")
    labels = res.get("labels", {})
    groups = {}
    for e, s0 in res["senders"].items():
        if s0["key"] != "gen":
            continue
        d = _dom(e)
        gk = e if (not d or d in free or d in OUR_DOMAINS) else d
        g = groups.setdefault(gk, {"key": gk, "is_domain": gk == d, "senders": [], "n": 0, "u": 0})
        g["senders"].append(e)
        g["n"] += s0["n"]
        g["u"] += s0["u"]
    out = sorted(groups.values(), key=lambda g: (-g["n"], g["key"]))[:limit]
    if not out:
        return []
    allsend = [e for g in out for e in g["senders"]]
    c.execute("CREATE TEMP TABLE IF NOT EXISTS _mf_gs(e TEXT PRIMARY KEY)")
    c.execute("DELETE FROM _mf_gs")
    c.executemany("INSERT OR IGNORE INTO _mf_gs(e) VALUES(?)", [(x,) for x in allsend])
    recent = {}
    for r in c.execute(
            "SELECT lower(from_email) AS e, from_name AS nm, subject AS sj, received_at AS at FROM mail_messages "
            "WHERE user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0 "
            "AND lower(from_email) IN (SELECT e FROM _mf_gs) ORDER BY received_at DESC, id DESC LIMIT 6000",
            (uid,)).fetchall():
        recent.setdefault(r["e"], []).append(r)
    for g in out:
        rows = sorted((x for e in g["senders"] for x in recent.get(e, [])[:6]),
                      key=lambda x: (x["at"] or ""), reverse=True)
        g["names"] = []
        for x in rows:
            nm = (x["nm"] or "").strip()
            if nm and nm not in g["names"]:
                g["names"].append(nm)
            if len(g["names"]) >= 3:
                break
        g["subject"] = rows[0]["sj"] if rows else ""
        g["at"] = (rows[0]["at"] or "")[:16] if rows else ""
        g["sample"] = g["senders"][0]
        hints, sug = [], set()
        comps = []
        for e in g["senders"][:5]:
            lid = res.get("_last", {}).get(e)
            comp = (_SIG_CACHE.get((e, lid)) or ("", ""))[0] if lid else ""
            if comp and comp not in comps:
                comps.append(comp)
        for comp in comps[:2]:
            hints.append("서명: " + comp)
            if idx:
                sug |= idx.find(comp)
        tags = []
        for x in rows[:8]:
            for t in _RE_TAG.findall(x["sj"] or ""):
                t = t.strip()
                if t and t not in tags:
                    tags.append(t)
        for t in tags[:3]:
            hints.append("제목: [" + t + "]")
            if idx:
                sug |= idx.find(t)
        g["hints"] = hints
        fid = _one(sug)
        g["suggest"] = fid
        g["suggest_name"] = labels.get("f%d" % fid, "") if fid else ""
    return out


def senders_in(res, key) -> list:
    ks = res["keys_of"].get(key)
    if not ks:
        return []
    return [e for e, s in res["senders"].items() if s["key"] in ks]


def folder_of(res, sender) -> dict:
    s = res["senders"].get((sender or "").strip().lower())
    if not s:
        return {"key": "gen", "name": "일반", "how": ""}
    return {"key": s["key"], "name": res["labels"].get(s["key"], "일반"), "how": s["how"]}


def assignable(c, uid) -> list:
    """「📁 이 폴더로」 고를 수 있는 폴더(6.케이엔케이 묶음은 부서로 자동이라 뺌)."""
    out = []
    fl = folders(c, uid)
    groups = [f for f in fl if not f["parent_id"]]
    for g in groups:
        if g["kind"] != "staff":
            out.append({"id": g["id"], "name": g["name"], "depth": 0})
        for f in fl:
            if f["parent_id"] == g["id"]:
                out.append({"id": f["id"], "name": f["name"], "depth": 1, "group": g["name"]})
    return out


# ─── 규칙 ─────────────────────────────────────────────────────────
def rule_target(sender: str):
    """보낸 사람 주소 → 기억할 규칙. 회사 주소면 @ 뒤 전체, 개인 메일·우리 회사면 그 주소 하나."""
    e = (sender or "").strip().lower()
    d = _dom(e)
    if not d:
        return None
    if d in _free_domains() or d in OUR_DOMAINS:
        return ("email", e)
    return ("domain", d)


def set_rule(c, uid, folder_id, sender) -> dict:
    """「📁 이 폴더로」 — 규칙을 저장(같은 대상의 예전 규칙은 바꿈). 반환 {ok, kind, pattern, moved}."""
    ensure(c)
    f = c.execute("SELECT id, parent_id, kind FROM mail_folders WHERE id=? AND user_id=?",
                  (folder_id, uid)).fetchone()
    if not f or (not f["parent_id"] and f["kind"] == "staff"):
        return {"ok": False, "message": "고를 수 없는 폴더입니다."}
    tgt = rule_target(sender)
    if not tgt:
        return {"ok": False, "message": "보낸 사람 주소가 없습니다."}
    kind, pat = tgt
    c.execute("INSERT INTO mail_folder_rules(user_id, folder_id, kind, pattern) VALUES(?,?,?,?) "
              "ON CONFLICT(user_id, kind, pattern) DO UPDATE SET folder_id=excluded.folder_id, "
              "created_at=datetime('now','localtime')", (uid, folder_id, kind, pat))
    if kind == "domain":
        n = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 "
                      "AND lower(from_email) LIKE ?", (uid, "%@" + pat)).fetchone()[0]
    else:
        n = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 "
                      "AND lower(from_email)=?", (uid, pat)).fetchone()[0]
    _CACHE.pop(uid, None)
    return {"ok": True, "kind": kind, "pattern": pat, "moved": n}


def delete_rule(c, uid, rule_id) -> bool:
    ensure(c)
    n = c.execute("DELETE FROM mail_folder_rules WHERE id=? AND user_id=?", (rule_id, uid)).rowcount
    _CACHE.pop(uid, None)
    return bool(n)


# ─── 폴더 고치기(관리 화면) ────────────────────────────────────────
def add_folder(c, uid, name, parent_id=None, kind="") -> int:
    ensure(c)
    name = (name or "").strip()[:60]
    if not name:
        return 0
    if parent_id:
        p = c.execute("SELECT id FROM mail_folders WHERE id=? AND user_id=? AND parent_id IS NULL",
                      (parent_id, uid)).fetchone()
        if not p:
            return 0
        kind = ""
    else:
        parent_id = None
        kind = kind if kind in GROUP_KINDS else ""
    mx = c.execute("SELECT COALESCE(MAX(sort),0) FROM mail_folders WHERE user_id=? AND "
                   + ("parent_id=?" if parent_id else "parent_id IS NULL"),
                   ((uid, parent_id) if parent_id else (uid,))).fetchone()[0]
    cur = c.execute("INSERT INTO mail_folders(user_id, parent_id, name, sort, kind) VALUES(?,?,?,?,?)",
                    (uid, parent_id, name, (mx or 0) + 10, kind))
    _CACHE.pop(uid, None)
    return cur.lastrowid


def rename_folder(c, uid, fid, name) -> bool:
    name = (name or "").strip()[:60]
    if not name:
        return False
    n = c.execute("UPDATE mail_folders SET name=? WHERE id=? AND user_id=?", (name, fid, uid)).rowcount
    _CACHE.pop(uid, None)
    return bool(n)


def move_folder(c, uid, fid, step) -> bool:
    """같은 층에서 위(-1)·아래(+1)로 한 칸."""
    f = c.execute("SELECT id, parent_id FROM mail_folders WHERE id=? AND user_id=?", (fid, uid)).fetchone()
    if not f:
        return False
    if f["parent_id"]:
        sib = c.execute("SELECT id FROM mail_folders WHERE user_id=? AND parent_id=? ORDER BY sort, id",
                        (uid, f["parent_id"])).fetchall()
    else:
        sib = c.execute("SELECT id FROM mail_folders WHERE user_id=? AND parent_id IS NULL ORDER BY sort, id",
                        (uid,)).fetchall()
    ids = [r["id"] for r in sib]
    i = ids.index(fid)
    j = i + (1 if step > 0 else -1)
    if j < 0 or j >= len(ids):
        return False
    ids[i], ids[j] = ids[j], ids[i]
    for k, x in enumerate(ids):
        c.execute("UPDATE mail_folders SET sort=? WHERE id=?", ((k + 1) * 10, x))
    _CACHE.pop(uid, None)
    return True


def delete_folder(c, uid, fid) -> int:
    """폴더 지우기 — 그 폴더(와 아래 폴더)와 규칙만 지운다. 메일은 지우지 않는다(자동 분류·일반으로 돌아감)."""
    ids = [fid] + [r["id"] for r in c.execute(
        "SELECT id FROM mail_folders WHERE user_id=? AND parent_id=?", (uid, fid)).fetchall()]
    if not c.execute("SELECT 1 FROM mail_folders WHERE id=? AND user_id=?", (fid, uid)).fetchone():
        return 0
    q = ",".join("?" * len(ids))
    c.execute("DELETE FROM mail_folder_rules WHERE user_id=? AND folder_id IN (%s)" % q, (uid, *ids))
    n = c.execute("DELETE FROM mail_folders WHERE user_id=? AND id IN (%s)" % q, (uid, *ids)).rowcount
    _CACHE.pop(uid, None)
    return n
