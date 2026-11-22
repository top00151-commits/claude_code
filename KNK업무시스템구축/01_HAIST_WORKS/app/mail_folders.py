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
_RS = {}           # (user_id) -> 읽음·지움·스팸 상태(바뀌면 숫자만 다시 셈 · 11-22)
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
    # 11-19 대표 「부서 이름 수정·삭제·추가」 — 메일 폴더에서만(회사 부서표·권한·결재는 그대로) · 사람마다 따로
    #   key: 't<부서id>' · 'tv'(20_베트남법인) · 'g<번호>'(내가 더한 부서 폴더)
    #   name = 메일에서 보일 이름 · parent = 'top'|'tv'|'g<번호>'(빈칸 = 자동) · merge = 지운 부서의 메일을 합칠 곳(빈칸 = 안 지움)
    c.execute("""CREATE TABLE IF NOT EXISTS mail_team_prefs(
        user_id INTEGER NOT NULL,
        key TEXT NOT NULL,
        name TEXT DEFAULT '',
        parent TEXT DEFAULT '',
        merge TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        PRIMARY KEY(user_id, key))""")
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
    # 11-22 대표 「옮길 때 지금부터만 / 지난 메일도 — 꼭 묻기 · 부서 폴더로도」 → 옮긴 규칙 = 옮긴 곳(폴더·부서·일반) + 언제부터
    #   target: 'f<폴더id>' · 't<부서id>' · 'gen' / since: '' = 지난 메일도 모두 · 'YYYY-MM-DD HH:MM:SS' = 그때부터 받은 메일
    #   같은 대상(사람·회사 주소)에 여러 줄 = 기간마다 다른 곳(예: 품질팀 → 11-22부터 설계팀)
    c.execute("""CREATE TABLE IF NOT EXISTS mail_move_rules(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        kind TEXT NOT NULL,
        pattern TEXT NOT NULL,
        target TEXT NOT NULL,
        since TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now','localtime')))""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_mailmove_user ON mail_move_rules(user_id, kind, pattern)")
    c.execute("""CREATE TABLE IF NOT EXISTS mail_folder_flags(
        user_id INTEGER NOT NULL,
        flag TEXT NOT NULL,
        val TEXT DEFAULT '',
        PRIMARY KEY(user_id, flag))""")
    # 옛 규칙 표(mail_folder_rules · 폴더 번호만)는 한 번만 새 표로 옮겨 적는다(옛 표는 그대로 둠 · 지우지 않음)
    try:
        if not c.execute("SELECT 1 FROM mail_folder_flags WHERE user_id=0 AND flag='rules_v2'").fetchone():
            c.execute("INSERT INTO mail_move_rules(user_id, kind, pattern, target, since, created_at) "
                      "SELECT r.user_id, r.kind, r.pattern, 'f'||r.folder_id, '', r.created_at FROM mail_folder_rules r "
                      "WHERE NOT EXISTS(SELECT 1 FROM mail_move_rules m WHERE m.user_id=r.user_id AND m.kind=r.kind "
                      "AND m.pattern=r.pattern) ORDER BY r.id")
            c.execute("INSERT OR REPLACE INTO mail_folder_flags(user_id, flag, val) VALUES(0,'rules_v2','1')")
    except Exception as e:
        print("[MAIL-FOLDERS] 옛 규칙 옮기기 실패(다음에 다시): %s" % str(e)[:160], flush=True)
        return
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
    try:
        apply_seed_v2(c, uid)
    except Exception:
        pass
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
    try:
        apply_seed_v2(c, uid)
    except Exception as e:
        print("[MAIL-FOLDERS] 삼성그룹 묶기 실패: %s" % str(e)[:160], flush=True)
    return made


# 11-22 대표 「삼성 경우는 삼성그룹으로 묶고 그 아래 삼성전자·삼성전기로 구분되는 건 구분해서 넣고 안 되는 건 삼성그룹으로」
#   (묶음, 새 폴더, 다른 이름, 아래로 넣을 폴더) — @samsung.com 은 삼성그룹 · 서명·보낸 사람 이름으로 아래 폴더를 한 번 더 찾음
SPLIT_SEED = (("1.고객사", "삼성그룹", "samsung.com, Samsung, 삼성", ("삼성전자", "삼성전기")),)


def apply_seed_v2(c, uid) -> int:
    """삼성그룹 폴더를 만들고 삼성전자·삼성전기를 그 아래로 — 사람마다 **한 번만**(나중에 지우거나 옮겨도 다시 안 만듦)."""
    ensure(c)
    if _flag(c, uid, "seed_v2"):
        return 0
    n = 0
    for gname, pname, al, names in SPLIT_SEED:
        g = c.execute("SELECT id FROM mail_folders WHERE user_id=? AND parent_id IS NULL AND name=?", (uid, gname)).fetchone()
        if not g:
            continue
        ks = []
        for nm in names:
            r = c.execute("SELECT id, sort FROM mail_folders WHERE user_id=? AND parent_id=? AND name=? "
                          "AND NOT EXISTS(SELECT 1 FROM mail_folders x WHERE x.parent_id=mail_folders.id)", (uid, g["id"], nm)).fetchone()
            if r:
                ks.append(r)
        if not ks or c.execute("SELECT 1 FROM mail_folders WHERE user_id=? AND name=?", (uid, pname)).fetchone():
            continue
        pid = c.execute("INSERT INTO mail_folders(user_id, parent_id, name, sort, kind, aliases) VALUES(?,?,?,?,'',?)",
                        (uid, g["id"], pname, min(r["sort"] for r in ks), al)).lastrowid
        for i, r in enumerate(ks):
            c.execute("UPDATE mail_folders SET parent_id=?, sort=? WHERE id=? AND user_id=?", (pid, (i + 1) * 10, r["id"], uid))
        n += 1
    _set_flag(c, uid, "seed_v2", "1")
    _CACHE.pop(uid, None)
    return n


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
            "SELECT id, COALESCE(code,'') AS code, name, COALESCE(display_order,0) AS ord, COALESCE(entity,'') AS entity FROM teams "
            "ORDER BY COALESCE(display_order,0), code, id").fetchall()]
    except Exception:
        pass
    try:   # 법인 칸이 없는 옛 DB
        return [dict(r) for r in c.execute(
            "SELECT id, COALESCE(code,'') AS code, name, COALESCE(display_order,0) AS ord FROM teams "
            "ORDER BY COALESCE(display_order,0), code, id").fetchall()]
    except Exception:
        return []


# 11-19 대표: 6.케이엔케이 = 「본사」·「베트남법인」 대분류 → 그 아래 각 법인 부서(본사 00_총괄~23_NEXT2028 · 베트남 00_총괄~09_구매팀)
#   법인 판정은 회사 부서표 teams.entity(KOR/VN · 회사 규칙 z747 단일소스) — 칸이 비어 있으면 「부서 코드가 숫자만 = 본사」
HQ_FOLDER_NAME = "본사"
VN_FOLDER_NAME = "베트남법인"
VN_FOLDER_CODE = 20   # (옛 「20_베트남법인」 · 쓰지 않음)


def is_vn_team(t: dict) -> bool:
    """베트남 법인 부서인가 — 회사 부서표 법인 칸(entity) 먼저(회사 규칙과 같게) ·
    칸이 비어 있으면 대표 11-18 「부서 앞에 번호가 있는 건 본사, 없는 건 베트남 법인」 + 이름이 베트남법인이면 베트남."""
    e = (t.get("entity") or "").strip().upper()
    if e in ("VN", "VNM"):
        return True
    if e in ("KOR", "KR", "KO"):
        return False
    if "베트남법인" in (t.get("name") or "").replace(" ", ""):
        return True
    code = (t.get("code") or "").strip()
    return not (code and code.isdigit())


def is_vn_bucket(t: dict) -> bool:
    """회사 부서표의 옛 「베트남법인」 부서(부서를 아직 못 정한 베트남 직원 묶음) — 메일에서는 「베트남법인」 폴더 바로 아래로."""
    return (t.get("name") or "").replace(" ", "") == "베트남법인"


def folder_team_label(t: dict) -> str:
    """메일 폴더 이름 — 본사 = 「00_총괄」(코드_이름) · 베트남 = 「VN」+코드의 번호 「VN00_총괄」「VN05_조립팀」(V00·05_2 → VN00·VN05 · 대표 11-19)."""
    if not is_vn_team(t):
        return team_label(t)
    m = re.search(r"(\d{1,2})", (t.get("code") or ""))
    return ("VN%02d_%s" % (int(m.group(1)), t["name"])) if m else ("VN_" + t["name"])


def team_prefs(c, uid) -> dict:
    """메일 부서 폴더 설정(이름·위치·지움) — {key: {name, parent, merge}}."""
    try:
        return {r["key"]: {"name": r["name"] or "", "parent": r["parent"] or "", "merge": r["merge"] or ""}
                for r in c.execute("SELECT key, name, parent, merge FROM mail_team_prefs WHERE user_id=?", (uid,)).fetchall()}
    except Exception:
        return {}


def set_team_pref(c, uid, key, **kw) -> None:
    ensure(c)
    key = (key or "").strip()
    if not key or not (key[:1] in ("t", "g") and (key[1:].isdigit() or key in ("tv", "th"))):
        raise ValueError("잘못된 부서 폴더")
    c.execute("INSERT OR IGNORE INTO mail_team_prefs(user_id, key) VALUES(?,?)", (uid, key))
    for f in ("name", "parent", "merge"):
        if f in kw:
            c.execute("UPDATE mail_team_prefs SET %s=? WHERE user_id=? AND key=?" % f, ((kw[f] or "").strip()[:60], uid, key))
    _CACHE.pop(uid, None)


def del_team_pref(c, uid, key) -> None:
    ensure(c)
    c.execute("DELETE FROM mail_team_prefs WHERE user_id=? AND key=?", (uid, key))
    _CACHE.pop(uid, None)


def add_team_group(c, uid, name) -> str:
    """새 부서 폴더(묶음) — 그 안에 기존 부서를 옮겨 넣을 수 있다(20_베트남법인처럼)."""
    ensure(c)
    nm = (name or "").strip()[:60]
    if not nm:
        raise ValueError("이름을 적어 주세요")
    n = 1
    for r in c.execute("SELECT key FROM mail_team_prefs WHERE user_id=? AND key LIKE 'g%'", (uid,)).fetchall():
        try:
            n = max(n, int(r["key"][1:]) + 1)
        except Exception:
            pass
    key = "g%d" % n
    c.execute("INSERT INTO mail_team_prefs(user_id, key, name) VALUES(?,?,?)", (uid, key, nm))
    _CACHE.pop(uid, None)
    return key


def del_team_group(c, uid, key) -> None:
    """부서 폴더(묶음) 지우기 — 안에 있던 부서는 「6.케이엔케이」 바로 아래로 · 이리로 합쳐 두었던 지운 부서는 「KNK 기타」로."""
    ensure(c)
    if key in ("tv", "th"):
        set_team_pref(c, uid, key, merge="x")
    else:
        c.execute("DELETE FROM mail_team_prefs WHERE user_id=? AND key=?", (uid, key))
    c.execute("UPDATE mail_team_prefs SET parent='' WHERE user_id=? AND parent=?", (uid, key))
    c.execute("UPDATE mail_team_prefs SET merge='tx' WHERE user_id=? AND merge=?", (uid, key))
    _CACHE.pop(uid, None)


def _lead_num(name):
    m = re.match(r"\s*(?:VN)?(\d+)", name or "", re.I)   # 「VN05_조립팀」도 번호 05 로(11-19)
    return int(m.group(1)) if m else 10 ** 5


def team_label(t: dict) -> str:
    code = (t.get("code") or "").strip()
    return ("%s_%s" % (code, t["name"])) if code and code.isdigit() else t["name"]


# ─── 분류 ─────────────────────────────────────────────────────────
# 11-22 대표 「자동 분류를 더 자세히 · 내가 옮기면 옮긴 위치가 기준 · 관련 메일 따라 이동 · 새 메일도 · 옮길 때 지금부터만/지난 메일도 꼭 묻기 ·
#   부서 이동은 바뀐 날부터 새 부서」 → 폴더는 **메일 한 통마다** 정한다(보낸 사람 단위로는 날짜 기준을 못 나타냄).
#   한 통의 폴더 = ① 「이 메일만」(fd_pin) ② 내가 옮긴 규칙(사람 규칙 → 회사 규칙 · 그 메일 받은 때에 걸리는 가장 새 규칙)
#                 ③ 우리 회사 직원 = 그 메일을 **받은 때의 부서**(fd_team · 받을 때 기록 · 처음 한 번은 지금 부서로 채움)
#                 ④ 보낸 사람 자동 분류(아래 ③~⑧)
#   정한 폴더는 메일 칸 fd_key 에 적어 둔다(목록 거르기·숫자 = 이 칸 하나) — 바뀐 메일만 고쳐 쓴다.
def _stamp(c, uid):
    a = c.execute("SELECT COUNT(*), COALESCE(MAX(id),0) FROM mail_messages WHERE user_id=? AND direction='in'",
                  (uid,)).fetchone()
    b = c.execute("SELECT COUNT(*), COALESCE(MAX(id),0) FROM mail_folders WHERE user_id=?", (uid,)).fetchone()
    try:   # 「이 메일만」 옮김이 바뀌면 다시 계산(같은 개수로 옮겨도 달라지게 옮긴 곳 글자까지)
        pn = tuple(c.execute("SELECT COUNT(*), COALESCE(SUM(id * (length(fd_pin) * 7 + unicode(fd_pin) + "
                             "COALESCE(CAST(substr(fd_pin,2) AS INTEGER),0))),0) FROM mail_messages "
                             "WHERE user_id=? AND COALESCE(fd_pin,'')<>''", (uid,)).fetchone())
    except Exception:
        pn = ()
    r = c.execute("SELECT COUNT(*), COALESCE(MAX(id),0), COALESCE(SUM(id),0) FROM mail_move_rules WHERE user_id=?",
                  (uid,)).fetchone()
    try:   # 11-19 부서 폴더 설정(이름·위치·지움)이 바뀌면 다시 계산
        r = tuple(r) + tuple(c.execute("SELECT COALESCE(group_concat(key||':'||name||':'||parent||':'||merge,'|'),'') "
                                       "FROM mail_team_prefs WHERE user_id=?", (uid,)).fetchone())
    except Exception:
        pass
    nm = c.execute("SELECT COALESCE(group_concat(id||':'||name||':'||COALESCE(parent_id,0)||':'||sort||':'||COALESCE(aliases,''),'|'),'') "
                   "FROM mail_folders WHERE user_id=?", (uid,)).fetchone()
    # 주소록·거래처 담당자·직원이 바뀌면 다시 계산
    ex = []
    for sql in ("SELECT COUNT(*), COALESCE(MAX(updated_at),'') FROM shared_contacts",
                "SELECT COUNT(*), COALESCE(MAX(id),0) FROM customer_contacts",
                "SELECT COUNT(*), COALESCE(MAX(id),0) FROM customers",
                "SELECT COUNT(*), COALESCE(SUM(COALESCE(team_id,0)),0) FROM users",
                "SELECT COUNT(*), COALESCE(MAX(id),0) FROM suppliers",
                "SELECT COUNT(*), COALESCE(SUM(id),0) FROM teams"):
        try:
            ex.append(tuple(c.execute(sql).fetchone()))
        except Exception:
            ex.append(None)
    return (tuple(a), tuple(b), tuple(r), nm[0], tuple(ex), pn)


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


def rules(c, uid) -> list:
    """내가 옮긴 규칙(새 것 먼저) — 폴더 관리 화면 목록. folder_name = 옮긴 곳 이름(폴더·부서·일반) · since = 언제부터('' = 지난 메일도)."""
    ensure(c)
    fn = {("f%d" % r["id"]): r["name"] for r in c.execute("SELECT id, name FROM mail_folders WHERE user_id=?", (uid,)).fetchall()}
    tn = {("t%d" % t["id"]): folder_team_label(t) for t in teams(c)}
    tp = team_prefs(c, uid)
    out = []
    for r in c.execute("SELECT id, kind, pattern, target, COALESCE(since,'') AS since, created_at FROM mail_move_rules "
                       "WHERE user_id=? ORDER BY id DESC", (uid,)).fetchall():
        d = dict(r)
        t = d["target"] or ""
        if t == "gen":
            nm = "일반"
        elif t.startswith("f"):
            nm = fn.get(t, "")
        elif t.startswith("t"):
            nm = (tp.get(t, {}).get("name") or tn.get(t, ""))
            nm = ("6.케이엔케이 › " + nm) if nm else ""
        else:
            nm = ""
        d["folder_name"] = nm
        out.append(d)
    return out


def _flag(c, uid, flag) -> str:
    try:
        r = c.execute("SELECT val FROM mail_folder_flags WHERE user_id=? AND flag=?", (uid, flag)).fetchone()
        return (r["val"] or "") if r else ""
    except Exception:
        return ""


def _set_flag(c, uid, flag, val) -> None:
    c.execute("INSERT INTO mail_folder_flags(user_id, flag, val) VALUES(?,?,?) "
              "ON CONFLICT(user_id, flag) DO UPDATE SET val=excluded.val", (uid, flag, val or ""))


def _rule_index(c, uid, valid):
    """규칙 → {주소: [(언제부터, 번호, 옮긴 곳)…]}(사람) · {회사 주소: […]}(회사). 새 기준·새 규칙 먼저. 없어진 곳으로 가는 규칙은 뺌."""
    em, dm = {}, {}
    for r in c.execute("SELECT id, kind, pattern, target, COALESCE(since,'') AS since FROM mail_move_rules WHERE user_id=?",
                       (uid,)).fetchall():
        if (r["target"] or "") not in valid:
            continue
        (em if r["kind"] == "email" else dm).setdefault((r["pattern"] or "").lower(), []).append(
            (r["since"] or "", r["id"], r["target"]))
    for m in (em, dm):
        for k in m:
            m[k].sort(reverse=True)
    return em, dm


def _rule_for(ri, e, ts):
    """그 메일(보낸 주소 e · 받은 때 ts)에 걸리는 규칙 → (옮긴 곳, 까닭) 또는 None.
    사람 규칙 먼저 → 회사 규칙. 같은 대상의 규칙이 여럿이면 **그 메일 받은 때에 이미 있던 가장 새 기준**(「지금부터만」 = 그때부터)."""
    if not ri:
        return None
    em, dm = ri
    ts = ts or ""
    d = _dom(e)
    for lst, how in ((em.get(e), "내 규칙(이 사람)"), (dm.get(d) if d else None, "내 규칙(회사 주소 @%s)" % d)):
        for since, _rid, tgt in (lst or ()):
            if since <= ts:
                return tgt, how + (" · %s부터 받은 메일" % since[:16] if since else "")
    return None


def _spec(hits, par):
    """찾은 폴더 중 다른 찾은 폴더의 윗 폴더는 뺀다(삼성그룹 + 삼성전기 → 삼성전기)."""
    hits = set(hits or ())
    if len(hits) < 2:
        return hits
    ups = set()
    for h in hits:
        p, hop = par.get(h), 0
        while p and hop < 5:
            ups.add(p)
            p, hop = par.get(p), hop + 1
    return hits - ups


def classify(c, uid) -> dict:
    """메일 → 폴더 열쇠(메일 한 통마다 · fd_key 칸). 반환 {
        'senders': {email: {'key'(보낸 사람 자동),'fin'(가장 최근 메일의 폴더),'how','n','u'}},
        'nodes':   [{key,name,depth,n,u,kind,children:[...]}],   # 화면용 나무(묶음 → 폴더 → 아래 폴더 · 6.케이엔케이 → 본사 → 부서)
        'labels':  {key: 이름}, 'keys_of': {key: set(자기+자손 열쇠)},
        'targets': 옮길 수 있는 곳(묶음·폴더·아래 폴더·부서·일반), 'valid': 그 열쇠 집합 }
    열쇠: 'f<폴더id>' · 't<부서id>'(6.케이엔케이 아래) · 'tx'(KNK 기타) · 'gen'(일반)."""
    ensure(c)
    try:   # 메일 표의 더한 칸(차단·보관·이 메일만 폴더·폴더 열쇠·받은 때 부서)이 먼저 있어야 아래 셈이 맞다
        from .mail_store import _ensure_security_cols
        _ensure_security_cols(c)
    except Exception:
        pass
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_mail_fdkey ON mail_messages(user_id, fd_key)")
    except Exception:
        pass
    st = _stamp(c, uid)
    hit = _CACHE.get(uid)
    if hit and hit[0] == st:
        # 11-22 대표 「폴더마다 안 읽은 메일 수」 — 읽음·지움·스팸만 바뀌면 나누기는 그대로 두고 숫자만 다시 센다
        rs = _read_stamp(c, uid)
        if rs == _RS.get(uid):
            return hit[1]
        if _recount(c, uid, hit[1]):
            _RS[uid] = rs
            return hit[1]
    fl = folders(c, uid)
    by_id = {f["id"]: f for f in fl}
    par = {f["id"]: f["parent_id"] for f in fl if f["parent_id"] and f["parent_id"] in by_id}
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

    def _names(f):
        out = [(f["id"], f["name"])]
        for a in re.split(r"[,\n]+", f.get("aliases") or ""):
            if a.strip():
                out.append((f["id"], a.strip()))
        return out
    # 이름·다른 이름(영문·회사 주소) 찾기 — 묶음 아래 폴더만
    _items = []
    for f in fl:
        if f["parent_id"]:
            _items.extend(_names(f))
    idx = NameIndex(_items)
    # 11-22 대표 「삼성은 삼성그룹으로 묶고 그 아래 삼성전자·삼성전기로 구분되는 건 구분 · 안 되면 삼성그룹」
    #   아래 폴더가 있는 폴더(삼성그룹)에 걸리면 서명의 회사 이름 → 보낸 사람 이름으로 아래 폴더를 한 번 더 찾는다(한 곳만 걸릴 때만)
    sub_idx = {}
    for pid, ks in kids.items():
        if pid in par:
            its = []
            for f in ks:
                its.extend(_names(f))
            sub_idx[pid] = NameIndex(its)
    split_keys = set()
    for pid in sub_idx:
        split_keys.add("f%d" % pid)
        split_keys |= {"f%d" % f["id"] for f in kids.get(pid, [])}
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

    from .mail_cleanup import _RE_ROBOT

    def refine(key, e, nm, last_id):
        """삼성그룹처럼 아래 폴더가 있는 폴더 → 서명의 회사 이름·보낸 사람 이름으로 아래 폴더(한 곳만 걸릴 때)."""
        if not key or not key.startswith("f") or not key[1:].isdigit():
            return key, ""
        si = sub_idx.get(int(key[1:]))
        if not si:
            return key, ""
        comp = dept = ""
        if not _RE_ROBOT.match(e.split("@")[0] or ""):
            comp, dept = _sig_of(c, e, last_id, nm)
        for txt, how in ((comp, "서명의 회사 이름"), (dept, "서명의 부서"), (nm or "", "보낸 사람 이름")):
            if txt:
                k = _one(si.find(txt))
                if k:
                    return "f%d" % k, " → %s(으)로 아래 폴더" % how
        return key, ""

    senders = {}
    _last_ids = {}
    staff_tid = {}
    rows = c.execute(
        "SELECT lower(from_email) AS e, MAX(from_name) AS nm, MAX(id) AS last_id, COUNT(*) AS n, "
        "SUM(CASE WHEN is_read=0 THEN 1 ELSE 0 END) AS u FROM mail_messages "
        "WHERE user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0 "
        "GROUP BY lower(from_email)", (uid,)).fetchall()
    for r in rows:
        e = (r["e"] or "").strip()
        d = _dom(e)
        key, how = None, ""
        # ② 우리 회사 — 지금 부서(새 메일에 적어 둘 부서 · 메일 한 통의 폴더는 그 메일 받은 때 부서)
        if d in OUR_DOMAINS:
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
                    staff_tid[e] = tid
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
            # ⑤ 회사 주소(@ 뒤)가 폴더의 영문 이름·적어 둔 주소와 같음(예: @partron.co.kr → 파트론 · @samsung.com → 삼성그룹)
            if key is None and d and d not in M["free"]:
                fid = _one(_spec(idx.find_domain(d), par))
                if fid:
                    key, how = "f%d" % fid, "회사 주소 @%s = 폴더 이름" % d
            # ⑥ 서명의 회사 이름(사람 주소만 — 알림·광고 주소는 건너뜀)
            if key is None and not _RE_ROBOT.match(e.split("@")[0] or ""):
                comp, _dept = _sig_of(c, e, r["last_id"], r["nm"])
                cn = norm_name(comp)
                if cn and len(cn) >= 2:
                    fid = _one(_spec(leaf_by_name.get(cn), par)) or _one(_spec(idx.find(comp), par))
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
                fid = _one(_spec(idx.find(r["nm"]), par))
                if fid:
                    key, how = "f%d" % fid, "보낸 사람 이름의 회사"
            if key is not None:
                k2, h2 = refine(key, e, r["nm"] or "", r["last_id"])
                if k2 != key:
                    key, how = k2, how + h2
        if key is None:
            key, how = "gen", "일반"
        senders[e] = {"key": key, "how": how, "n": r["n"] or 0, "u": r["u"] or 0, "nm": r["nm"] or ""}
        _last_ids[e] = r["last_id"]

    # ⑧ 같은 회사 주소의 다른 사람이 폴더 **한 곳**으로만 갔으면 나머지도 그리로(개인 메일·우리 회사 주소 · 여러 폴더가 나눠 쓰는 주소 제외)
    by_dom = {}
    for e2, s2 in senders.items():
        d2 = _dom(e2)
        if s2["key"].startswith("f") and d2 and d2 not in M["free"] and d2 not in OUR_DOMAINS:
            by_dom.setdefault(d2, set()).add(s2["key"])
    for e2, s2 in senders.items():
        if s2["key"] == "gen":
            d2 = _dom(e2)
            ks = by_dom.get(d2)
            if ks and len(ks) == 1 and not (ks & split_keys):
                s2["key"] = next(iter(ks))
                s2["how"] = "같은 회사 주소(@%s)의 다른 사람이 이 폴더" % d2

    # 11-19 지운 부서 폴더 — 그 부서 메일은 합친 곳(다른 부서·묶음·KNK 기타)으로
    _tp = team_prefs(c, uid)
    _merge = {k: v["merge"] for k, v in _tp.items() if k.startswith("t") and k not in ("tv", "th") and v.get("merge")}
    if not _tp.get("tv", {}).get("merge"):
        for _t in tlist:
            _tk = "t%d" % _t["id"]
            if is_vn_bucket(_t) and _tk not in _merge and not _tp.get(_tk, {}).get("parent"):
                _merge[_tk] = "tv"

    def mg(k):
        hop = 0
        while k in _merge and hop < 5:
            k, hop = _merge[k], hop + 1
        return k

    # 옮길 수 있는 곳 — 폴더(6.케이엔케이 묶음 칸 빼고) · 부서 · 일반
    valid = {"gen"} | {"f%d" % f["id"] for f in fl if not (not f["parent_id"] and f["kind"] == "staff")}
    if staff_g:
        valid |= {"t%d" % t["id"] for t in tlist}
    ri = _rule_index(c, uid, valid)

    # ── 메일 한 통마다 ──
    cnt, gcnt = {}, {}
    upd_key, upd_team = [], []
    _ref_cache = {}
    for r in c.execute("SELECT id, lower(from_email) AS e, COALESCE(received_at,'') AS ts, COALESCE(fd_pin,'') AS pin, "
                       "fd_team, COALESCE(fd_key,'') AS fk, is_read FROM mail_messages "
                       "WHERE user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0", (uid,)).fetchall():
        e = (r["e"] or "").strip()
        s = senders.get(e)
        pin = r["pin"]
        if pin and pin in valid:                       # ① 이 메일만
            k = pin
        else:
            rr = _rule_for(ri, e, r["ts"])             # ② 내가 옮긴 규칙(그 메일 받은 때 기준)
            if rr:
                k = rr[0]
                if k in split_keys and s is not None:   # 옮긴 폴더에 아래 폴더가 있으면(삼성그룹 등) 그 안에서 한 번 더
                    ck = (e, k)
                    if ck not in _ref_cache:
                        _ref_cache[ck] = refine(k, e, s.get("nm", ""), _last_ids.get(e))[0]
                    k = _ref_cache[ck]
            elif staff_g and _dom(e) in OUR_DOMAINS:   # ③ 직원 = 받은 때 부서
                tid = r["fd_team"]
                cur = staff_tid.get(e)
                if tid is None and cur is not None:
                    upd_team.append((cur, r["id"]))
                if tid is None or tid not in tmap:
                    tid = cur
                k = ("t%d" % tid) if (tid is not None and tid in tmap) else "tx"
            else:                                      # ④ 보낸 사람 자동
                k = s["key"] if s else "gen"
        k = mg(k)
        if k != r["fk"]:
            upd_key.append((k, r["id"]))
        a = cnt.setdefault(k, [0, 0])
        a[0] += 1
        a[1] += 0 if r["is_read"] else 1
        if k == "gen":
            g0 = gcnt.setdefault(e, [0, 0])
            g0[0] += 1
            g0[1] += 0 if r["is_read"] else 1
        if s is not None and r["id"] >= s.get("_lid", 0):
            s["_lid"], s["fin"] = r["id"], k
    for i in range(0, len(upd_team), 500):
        c.executemany("UPDATE mail_messages SET fd_team=? WHERE id=? AND fd_team IS NULL", upd_team[i:i + 500])
    for i in range(0, len(upd_key), 500):
        c.executemany("UPDATE mail_messages SET fd_key=? WHERE id=?", upd_key[i:i + 500])
    for s in senders.values():
        s.pop("_lid", None)
        s.setdefault("fin", mg(s["key"]))
        if s["key"] in _merge:
            s["key"] = mg(s["key"])
            s["how"] = (s["how"] or "") + " → 지운 부서라 합친 곳"

    labels, keys_of, nodes = {}, {}, []
    targets = []
    for g in groups:
        gk = "f%d" % g["id"]
        labels[gk] = g["name"]
        ch = []
        if g["kind"] != "staff":
            targets.append({"key": gk, "name": g["name"], "depth": 0})
        for f in kids.get(g["id"], []):
            fk = "f%d" % f["id"]
            labels[fk] = f["name"]
            targets.append({"key": fk, "name": f["name"], "depth": 1, "up": g["name"]})
            sub = []
            for f2 in kids.get(f["id"], []):
                f2k = "f%d" % f2["id"]
                labels[f2k] = f2["name"]
                keys_of[f2k] = {f2k}
                targets.append({"key": f2k, "name": f2["name"], "depth": 2, "up": f["name"]})
                sub.append({"key": f2k, "name": f2["name"], "n": cnt.get(f2k, [0, 0])[0], "u": cnt.get(f2k, [0, 0])[1],
                            "assignable": True, "al": f2.get("aliases") or ""})
            keys_of[fk] = {fk} | {x["key"] for x in sub}
            node = {"key": fk, "name": f["name"], "assignable": True, "al": f.get("aliases") or "",
                    "n": sum(cnt.get(k, [0, 0])[0] for k in keys_of[fk]), "u": sum(cnt.get(k, [0, 0])[1] for k in keys_of[fk])}
            if sub:
                node["children"] = sub
            ch.append(node)
        if g["kind"] == "staff":
            # 11-18 대표: 부서 앞 번호 있는 것 = 본사 · 없는 것 = 베트남 법인 → 「베트남법인」 폴더 안으로(번호 순서 자리)
            #   11-19: 메일에서만 이름 바꾸기·지우기(합치기)·부서 폴더 더하기·위치 옮기기(mail_team_prefs) · 순서 = 이름 앞 번호
            #   11-22: 부서 폴더도 옮길 곳(「품질팀 김정록 팀장 메일을 다른 부서로」) — 메일이 없는 부서도 옮길 곳 목록에는 나옴
            gdefs = []
            if not _tp.get("th", {}).get("merge"):
                gdefs.append(("th", _tp.get("th", {}).get("name") or HQ_FOLDER_NAME))
            if not _tp.get("tv", {}).get("merge"):
                gdefs.append(("tv", _tp.get("tv", {}).get("name") or VN_FOLDER_NAME))
            for gk2 in sorted([k for k in _tp if k.startswith("g")], key=lambda x: int(x[1:]) if x[1:].isdigit() else 0):
                gdefs.append((gk2, _tp[gk2].get("name") or "새 부서 폴더"))
            gnodes = {k: {"key": k, "name": nm, "children": [], "assignable": False, "group": True} for k, nm in gdefs}
            tgroups = {k: [] for k, _nm in gdefs}
            ttop = []
            top = []
            for oi, t in enumerate(tlist):
                tk = "t%d" % t["id"]
                pr = _tp.get(tk, {})
                nm = pr.get("name") or folder_team_label(t)
                labels[tk] = nm
                keys_of[tk] = {tk}
                if pr.get("merge"):
                    continue
                par_t = pr.get("parent") or ""
                if par_t == "top":
                    par_t = ""
                elif not par_t:
                    par_t = "tv" if is_vn_team(t) else "th"
                (tgroups[par_t] if par_t in tgroups else ttop).append({"key": tk, "name": nm, "_o": oi})
                if tk not in cnt:
                    continue
                node = {"key": tk, "name": nm, "n": cnt[tk][0], "u": cnt[tk][1], "assignable": True, "_o": oi,
                        "auto_name": folder_team_label(t), "renamed": bool(pr.get("name")), "par_pref": pr.get("parent") or "",
                        "vn": is_vn_team(t)}
                (gnodes[par_t]["children"] if par_t in gnodes else top).append(node)
            for gk2, gn in gnodes.items():
                labels[gk2] = gn["name"]
                gn["children"].sort(key=lambda x: (_lead_num(x["name"]), x.get("_o", 0)))
                keys_of[gk2] = {gk2} | {x["key"] for x in gn["children"]}
                gn["n"] = cnt.get(gk2, [0, 0])[0] + sum(x["n"] for x in gn["children"])
                gn["u"] = cnt.get(gk2, [0, 0])[1] + sum(x["u"] for x in gn["children"])
                if gn["children"] or gk2.startswith("g") or cnt.get(gk2):
                    # 대분류 순서: 본사 → 베트남법인 → 내가 더한 부서 폴더(이름 앞 번호) → 바로 아래 부서
                    gn["_o"] = {"th": -2, "tv": -1}.get(gk2, 0)
                    top.append(gn)
            top.sort(key=lambda x: ((0, x["_o"], 0) if x.get("group") else (1, _lead_num(x["name"]), x.get("_o", 0))))
            for x in top:
                x.pop("_o", None)
                for y in x.get("children") or []:
                    y.pop("_o", None)
            ch.extend(top)
            labels["tx"] = "KNK 기타(부서 모름)"
            keys_of["tx"] = {"tx"}
            if "tx" in cnt:
                ch.append({"key": "tx", "name": "KNK 기타(부서 모름)", "n": cnt["tx"][0], "u": cnt["tx"][1],
                           "assignable": False})
            # 옮길 곳 목록(부서) — 6.케이엔케이 › 본사 › 부서
            targets.append({"key": "", "name": g["name"], "depth": 0, "head": True})
            for gk2, nm in gdefs:
                lst = sorted(tgroups.get(gk2) or [], key=lambda x: (_lead_num(x["name"]), x["_o"]))
                if not lst:
                    continue
                targets.append({"key": "", "name": nm, "depth": 1, "head": True})
                for x in lst:
                    targets.append({"key": x["key"], "name": x["name"], "depth": 2, "up": nm, "team": True})
            for x in sorted(ttop, key=lambda x: (_lead_num(x["name"]), x["_o"])):
                targets.append({"key": x["key"], "name": x["name"], "depth": 1, "up": g["name"], "team": True})
        ks = {gk} | {x["key"] for x in ch} | {y["key"] for x in ch for y in (x.get("children") or [])}
        keys_of[gk] = ks
        nodes.append({"key": gk, "name": g["name"], "kind": g["kind"], "children": ch, "al": g.get("aliases") or "",
                      "n": sum(cnt.get(k, [0, 0])[0] for k in ks), "u": sum(cnt.get(k, [0, 0])[1] for k in ks),
                      "assignable": g["kind"] != "staff"})
    labels["gen"] = "일반"
    keys_of["gen"] = {"gen"}
    targets.append({"key": "gen", "name": "일반", "depth": 0})
    shown = {"gen"}
    for g in nodes:
        shown |= keys_of.get(g["key"], set())
    res = {"senders": senders, "nodes": nodes, "labels": labels, "keys_of": keys_of,
           "gen": {"n": cnt.get("gen", [0, 0])[0], "u": cnt.get("gen", [0, 0])[1]},
           "_idx": idx, "_last": dict(_last_ids), "targets": targets, "valid": valid, "_ri": ri,
           "gen_senders": gcnt, "_shown": shown, "_split": split_keys, "_staff_tid": staff_tid}
    _CACHE[uid] = (st, res)
    _RS[uid] = _read_stamp(c, uid)
    return res


def _read_stamp(c, uid):
    """읽음·지움·스팸 표시 상태(받은 메일) — 바뀌면 폴더 숫자만 다시 센다."""
    try:
        return tuple(c.execute(
            "SELECT COUNT(*), SUM(CASE WHEN is_read=0 THEN 1 ELSE 0 END), SUM(CASE WHEN is_deleted=1 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN COALESCE(is_blocked,0)=1 THEN 1 ELSE 0 END), "
            "COALESCE(SUM(CASE WHEN is_read=0 THEN id ELSE 0 END),0) FROM mail_messages WHERE user_id=? AND direction='in'",
            (uid,)).fetchone())
    except Exception:
        return None


def _recount(c, uid, res) -> bool:
    """폴더 나누기(메일마다 fd_key)는 그대로 · 폴더마다 통수·안 읽음 수만 다시.
    폴더 열쇠가 비었거나(지운 메일을 되살림 등) 나무에 없는 열쇠가 나오면 False(처음부터 다시)."""
    try:
        cnt = {}
        shown = res.get("_shown") or set()
        for r in c.execute("SELECT COALESCE(fd_key,'') AS k, COUNT(*) AS n, SUM(CASE WHEN is_read=0 THEN 1 ELSE 0 END) AS u "
                           "FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0 "
                           "GROUP BY COALESCE(fd_key,'')", (uid,)).fetchall():
            if not r["k"] or r["k"] not in shown:
                return False
            cnt[r["k"]] = [r["n"] or 0, r["u"] or 0]
        gs = {}
        for r in c.execute("SELECT lower(from_email) AS e, COUNT(*) AS n, SUM(CASE WHEN is_read=0 THEN 1 ELSE 0 END) AS u "
                           "FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0 "
                           "AND fd_key='gen' GROUP BY lower(from_email)", (uid,)).fetchall():
            gs[(r["e"] or "").strip()] = [r["n"] or 0, r["u"] or 0]
        res["gen_senders"] = gs
        ko = res.get("keys_of") or {}

        def walk(nodes):
            for x in nodes or []:
                ks = ko.get(x["key"]) or {x["key"]}
                x["n"] = sum(cnt.get(k, [0, 0])[0] for k in ks)
                x["u"] = sum(cnt.get(k, [0, 0])[1] for k in ks)
                walk(x.get("children"))
        walk(res.get("nodes"))
        res["gen"] = {"n": cnt.get("gen", [0, 0])[0], "u": cnt.get("gen", [0, 0])[1]}
        return True
    except Exception as e:
        print("[MAIL-FOLDERS] 숫자 다시 세기 실패(처음부터 다시): %s" % str(e)[:160], flush=True)
        return False


_RE_TAG = re.compile(r"[\[(（【<〔]\s*([^\])）】>〕]{2,24}?)\s*[\])）】>〕]")


def general_groups(c, uid, res, limit=300) -> list:
    """「일반」에 남은 메일을 보낸 곳(회사 주소 @ 뒤 · 개인 메일은 그 주소)별로 묶는다 — 일반 정리 화면용.
    단서(서명의 회사 이름 · 제목의 [회사])는 **추천**만 한다(사람이 누르기 전에는 옮기지 않음)."""
    free = _free_domains()
    idx = res.get("_idx")
    labels = res.get("labels", {})
    groups = {}
    for e, nu in (res.get("gen_senders") or {}).items():
        if not nu or not nu[0]:
            continue
        d = _dom(e)
        gk = e if (not d or d in free or d in OUR_DOMAINS) else d
        g = groups.setdefault(gk, {"key": gk, "is_domain": gk == d, "senders": [], "n": 0, "u": 0})
        g["senders"].append(e)
        g["n"] += nu[0]
        g["u"] += nu[1]
    out = sorted(groups.values(), key=lambda g: (-g["n"], g["key"]))[:limit]
    if not out:
        return []
    try:
        from .mail_find import bulk_senders
        bulk = set(bulk_senders(c, uid))
    except Exception:
        bulk = set()
    allsend = [e for g in out for e in g["senders"]]
    c.execute("CREATE TEMP TABLE IF NOT EXISTS _mf_gs(e TEXT PRIMARY KEY)")
    c.execute("DELETE FROM _mf_gs")
    c.executemany("INSERT OR IGNORE INTO _mf_gs(e) VALUES(?)", [(x,) for x in allsend])
    recent = {}
    for r in c.execute(
            "SELECT lower(from_email) AS e, from_name AS nm, subject AS sj, received_at AS at FROM mail_messages "
            "WHERE user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0 AND fd_key='gen' "
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
        # 11-22 대표 「일반에 많이 남은 곳 보강」 — 「＋ 새 폴더로」 이름 미리 채우기(서명의 회사 이름 → 회사 주소 맨 앞) · 알림·광고 표시
        g["new_name"] = _clean_comp(comps[0]) if comps else (_dom_label(g["key"]) if g["is_domain"] else "")
        g["robot"] = all(_is_robot(e, bulk) for e in g["senders"])
    return out


def _clean_comp(s) -> str:
    """서명의 회사 이름 → 폴더 이름(㈜·주식회사·Co., Ltd. 뺌)."""
    t = _RE_CORP.sub(" ", s or "")
    return re.sub(r"\s+", " ", t).strip(" ,.-·")[:40]


def _dom_label(d) -> str:
    """회사 주소 → 폴더 이름 후보(@ 뒤 맨 앞 · mail./co. 같은 앞 글자 빼고)."""
    parts = [x for x in (d or "").lower().split(".") if x and x not in ("mail", "email", "m", "www", "co", "com", "net", "kr", "or", "ac")]
    return parts[0] if parts else (d or "")


def _is_robot(e, bulk=()) -> bool:
    from .mail_cleanup import _RE_ROBOT
    return bool(_RE_ROBOT.match((e or "").split("@")[0] or "")) or e in (bulk or ())


ROBOT_FOLDER = "알림·광고"


def robot_senders(c, uid, res) -> dict:
    """「일반」에 남은 알림·광고 주소(noreply·newsletter… · 「📮 보낸 곳별 정리」가 광고·알림으로 본 곳) → {주소: 통수}."""
    try:
        from .mail_find import bulk_senders
        bulk = set(bulk_senders(c, uid))
    except Exception:
        bulk = set()
    return {e: nu[0] for e, nu in (res.get("gen_senders") or {}).items() if nu and nu[0] and _is_robot(e, bulk)}


def move_robots(c, uid, res) -> dict:
    """알림·광고 주소를 한 번에 「알림·광고」 묶음으로 — **주소 하나씩**(회사 주소 전체가 아님: noreply@거래처 때문에 거래처 메일이 따라가지 않게).
    지난 메일·앞으로 올 메일 모두 · ↺ 되돌리기(move_undo)."""
    ensure(c)
    rs = robot_senders(c, uid, res)
    if not rs:
        return {"ok": False, "message": "「일반」에 알림·광고 주소가 없습니다."}
    r = c.execute("SELECT id FROM mail_folders WHERE user_id=? AND parent_id IS NULL AND name=?", (uid, ROBOT_FOLDER)).fetchone()
    fid = r["id"] if r else add_folder(c, uid, ROBOT_FOLDER)
    undo = {"add": [], "del": [], "pins": []}
    for e in sorted(rs):
        _put_rule(c, uid, "email", e, "f%d" % fid, "", undo)
    import json as _json
    _set_flag(c, uid, "move_undo", _json.dumps(undo, ensure_ascii=False))
    _CACHE.pop(uid, None)
    classify(c, uid)
    return {"ok": True, "name": ROBOT_FOLDER, "senders": len(rs), "moved": sum(rs.values())}


def new_folder_move(c, uid, res, sender, name, parent_id) -> dict:
    """「＋ 새 폴더로」 — 폴더를 만들고(같은 이름이 그 자리에 있으면 그것) 그 보낸 곳의 지난·앞으로 메일을 모두 그리로."""
    ensure(c)
    nm = re.sub(r"\s+", " ", (name or "")).strip()[:60]
    if not nm:
        return {"ok": False, "message": "폴더 이름을 적어 주세요."}
    dp = _depth(c, uid, parent_id)
    g = c.execute("SELECT kind FROM mail_folders WHERE id=? AND user_id=?", (parent_id, uid)).fetchone()
    if dp not in (0, 1) or not g or (dp == 0 and g["kind"] == "staff"):
        return {"ok": False, "message": "넣을 곳을 골라 주세요."}
    tgt = rule_target(sender, res)
    if not tgt:
        return {"ok": False, "message": "보낸 사람 주소가 없습니다."}
    fid = None
    for r in c.execute("SELECT id, name FROM mail_folders WHERE user_id=? AND parent_id=?", (uid, parent_id)).fetchall():
        if norm_name(r["name"]) == norm_name(nm):
            fid = r["id"]
            break
    made = False
    if not fid:
        fid = add_folder(c, uid, nm, parent_id)
        made = True
    if not fid:
        return {"ok": False, "message": "폴더를 만들지 못했습니다."}
    undo = {"add": [], "del": [], "pins": []}
    _put_rule(c, uid, tgt[0], tgt[1], "f%d" % fid, "", undo)
    import json as _json
    _set_flag(c, uid, "move_undo", _json.dumps(undo, ensure_ascii=False))
    _CACHE.pop(uid, None)
    classify(c, uid)
    return {"ok": True, "folder_id": fid, "name": nm, "made": made, "kind": tgt[0], "pattern": tgt[1],
            "moved": _match_count(c, uid, [tgt], "f%d" % fid)}


def senders_in(res, key) -> list:
    ks = res["keys_of"].get(key)
    if not ks:
        return []
    return [e for e, s in res["senders"].items() if s.get("fin", s["key"]) in ks]


def folder_of(res, sender) -> dict:
    s = res["senders"].get((sender or "").strip().lower())
    if not s:
        return {"key": "gen", "name": "일반", "how": ""}
    k = s.get("fin", s["key"])
    return {"key": k, "name": res["labels"].get(k, "일반"), "how": s["how"]}


def mail_where(res, m) -> dict:
    """메일 한 통의 폴더 + 까닭(읽기 화면 「📁」 줄). 반환 {key, name, how, pinned}."""
    e = (m.get("from_email") or "").strip().lower()
    labels = res.get("labels") or {}
    pin = m.get("fd_pin") or ""
    if pin and pin in (res.get("valid") or ()):
        return {"key": pin, "name": labels.get(pin, "일반"), "how": "이 메일만 직접 옮김", "pinned": True}
    k = m.get("fd_key") or ""
    s = res["senders"].get(e) or {}
    if not k or k not in labels:
        k = s.get("fin", s.get("key", "gen")) if s else "gen"
    rr = _rule_for(res.get("_ri"), e, m.get("received_at") or "")
    if rr:
        how = rr[1]
    elif k.startswith("t") and _dom(e) in OUR_DOMAINS:
        how = "직원 — 이 메일 받은 때 부서"
    else:
        how = s.get("how", "") if s else ""
    return {"key": k, "name": labels.get(k, "일반"), "how": how, "pinned": False}


def assignable_list(res) -> list:
    """옮길 곳 고르기(여러 통 「📁」·이동 메뉴·끌어 놓기) — classify 결과에서(DB 다시 안 읽음).
    11-22: 열쇠로(폴더 f… · 부서 t… · 일반) · 머리 줄(head) = 고를 수 없는 이름(6.케이엔케이 · 본사 · 베트남법인)."""
    return list((res or {}).get("targets") or [])


def assignable(c, uid) -> list:
    """「📁 이 폴더로」 고를 수 있는 폴더(폴더 번호 · 6.케이엔케이 묶음은 빼고) — 일반 정리 화면·예전 경로."""
    out = []
    fl = folders(c, uid)
    groups = [f for f in fl if not f["parent_id"]]
    for g in groups:
        if g["kind"] != "staff":
            out.append({"id": g["id"], "name": g["name"], "depth": 0})
        for f in fl:
            if f["parent_id"] == g["id"]:
                out.append({"id": f["id"], "name": f["name"], "depth": 1, "group": g["name"]})
                for f2 in fl:
                    if f2["parent_id"] == f["id"]:
                        out.append({"id": f2["id"], "name": f2["name"], "depth": 2, "group": f["name"]})
    return out


# ─── 규칙 ─────────────────────────────────────────────────────────
def shared_domain(res, d) -> bool:
    """한 회사 주소를 여러 폴더가 나눠 쓰는가(예: @samsung.com = 삼성그룹·삼성전자·삼성전기) — 그러면 규칙은 그 사람 한 명."""
    if not res or not d:
        return False
    ks = set()
    for e, s in (res.get("senders") or {}).items():
        if _dom(e) == d:
            k = s.get("fin", s["key"])
            if k != "gen":
                ks.add(k)
    if len(ks) > 1:
        return True
    return bool(ks & (res.get("_split") or set()))


def rule_target(sender: str, res=None):
    """보낸 사람 주소 → 기억할 규칙. 회사 주소면 @ 뒤 전체, 개인 메일·우리 회사·여러 폴더가 나눠 쓰는 회사 주소면 그 주소 하나."""
    e = (sender or "").strip().lower()
    d = _dom(e)
    if not d:
        return None
    if d in _free_domains() or d in OUR_DOMAINS or shared_domain(res, d):
        return ("email", e)
    return ("domain", d)


def _put_rule(c, uid, kind, pat, target, since, undo) -> int:
    """규칙 하나 넣기. since='' (지난 메일도 모두) = 같은 대상의 예전 규칙을 모두 바꿈 ·
    since=지금 (지금부터만) = 예전 규칙은 지난 메일에 그대로 두고, 같은 때·그 뒤 규칙만 바꿈. 지운 규칙은 undo 에 남김."""
    if since:
        dels = c.execute("SELECT * FROM mail_move_rules WHERE user_id=? AND kind=? AND pattern=? AND COALESCE(since,'')>=? "
                         "AND COALESCE(since,'')<>''", (uid, kind, pat, since)).fetchall()
    else:
        dels = c.execute("SELECT * FROM mail_move_rules WHERE user_id=? AND kind=? AND pattern=?", (uid, kind, pat)).fetchall()
    for r in dels:
        undo["del"].append({k: r[k] for k in r.keys()})
        c.execute("DELETE FROM mail_move_rules WHERE id=?", (r["id"],))
    rid = c.execute("INSERT INTO mail_move_rules(user_id, kind, pattern, target, since) VALUES(?,?,?,?,?)",
                    (uid, kind, pat, target, since or "")).lastrowid
    undo["add"].append(rid)
    return rid


def set_rule(c, uid, folder_id, sender, res=None) -> dict:
    """「📁 이 폴더로」(예전 경로·일반 정리 화면) — 그 보낸 곳의 지난·앞으로 메일 모두. 반환 {ok, kind, pattern, moved}."""
    ensure(c)
    f = c.execute("SELECT id, parent_id, kind FROM mail_folders WHERE id=? AND user_id=?",
                  (folder_id, uid)).fetchone()
    if not f or (not f["parent_id"] and f["kind"] == "staff"):
        return {"ok": False, "message": "고를 수 없는 폴더입니다."}
    tgt = rule_target(sender, res)
    if not tgt:
        return {"ok": False, "message": "보낸 사람 주소가 없습니다."}
    kind, pat = tgt
    _put_rule(c, uid, kind, pat, "f%d" % folder_id, "", {"add": [], "del": []})
    n = _match_count(c, uid, [(kind, pat)])
    _CACHE.pop(uid, None)
    return {"ok": True, "kind": kind, "pattern": pat, "moved": n}


def _pat_tables(c, pats):
    c.execute("CREATE TEMP TABLE IF NOT EXISTS _mv_e(e TEXT PRIMARY KEY)")
    c.execute("CREATE TEMP TABLE IF NOT EXISTS _mv_d(d TEXT PRIMARY KEY)")
    c.execute("DELETE FROM _mv_e")
    c.execute("DELETE FROM _mv_d")
    c.executemany("INSERT OR IGNORE INTO _mv_e(e) VALUES(?)", [(p,) for k, p in pats if k == "email"])
    c.executemany("INSERT OR IGNORE INTO _mv_d(d) VALUES(?)", [(p,) for k, p in pats if k == "domain"])
    return ("(lower(from_email) IN (SELECT e FROM _mv_e) OR "
            "substr(lower(from_email), instr(lower(from_email),'@')+1) IN (SELECT d FROM _mv_d))")


def _match_count(c, uid, pats, key=None) -> int:
    """규칙 대상(사람·회사 주소)의 받은 메일 수(지운 것·스팸 빼고) · key 를 주면 그 폴더에 있는 것만."""
    if not pats:
        return 0
    w = _pat_tables(c, pats)
    sql = ("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 "
           "AND COALESCE(is_blocked,0)=0 AND " + w)
    args = [uid]
    if key is not None:
        sql += " AND COALESCE(fd_key,'')=?"
        args.append(key)
    return c.execute(sql, args).fetchone()[0] or 0


def _own_rows(c, uid, ids):
    nums = []
    for x in list(ids or [])[:500]:
        try:
            nums.append(int(x))
        except Exception:
            pass
    if not nums:
        return []
    q = ",".join("?" * len(nums))
    return [dict(r) for r in c.execute(
        "SELECT id, lower(from_email) AS e, COALESCE(fd_pin,'') AS pin, COALESCE(fd_key,'') AS fk FROM mail_messages "
        "WHERE user_id=? AND direction='in' AND id IN (" + q + ")", (uid, *nums)).fetchall()]


def _pat_label(pats) -> str:
    if len(pats) == 1:
        k, p = pats[0]
        return ("회사 주소 @" + p) if k == "domain" else p
    nd = sum(1 for k, _p in pats if k == "domain")
    ne = len(pats) - nd
    return "보낸 곳 %d곳" % len(pats) + (" (회사 %d · 사람 %d)" % (nd, ne) if nd and ne else "")


def move_scopes(c, uid, res, ids) -> dict:
    """옮기기 묻는 창 — 고른 메일의 보낸 곳 · 「회사 모두」/「이 사람만」 범위와 그 범위의 받은 메일 수."""
    rows = _own_rows(c, uid, ids)
    rows = [r for r in rows if "@" in (r["e"] or "")]
    if not rows:
        return {"ok": False, "message": "옮길 받은 메일이 없습니다(보낸 메일은 폴더에 넣지 않습니다)."}
    es = sorted({r["e"] for r in rows})
    comp = sorted({rule_target(e, res) for e in es if rule_target(e, res)})
    pers = sorted({("email", e) for e in es})
    out = {"ok": True, "n": len(rows), "same": comp == pers,
           "company": {"label": _pat_label(comp), "n": _match_count(c, uid, comp)},
           "person": {"label": _pat_label(pers), "n": _match_count(c, uid, pers)}}
    fk = {r["fk"] for r in rows if r["fk"]}
    out["from"] = (res.get("labels") or {}).get(next(iter(fk)), "") if len(fk) == 1 else ""
    return out


def move(c, uid, res, ids, target, when, scope) -> dict:
    """11-22 대표 「내가 옮기면 옮긴 위치가 기준 · 관련 메일도 따라 · 새 메일도 · 지금부터만/지난 메일도 꼭 묻기」.
    when = 'new'(지금부터 오는 메일 + 고른 메일) · 'all'(지난 메일도 모두) · 'one'(고른 메일만)
    scope = 'company'(회사 주소 모두 · 개인 메일·우리 회사·나눠 쓰는 주소는 그 사람) · 'person'(그 사람만).
    마지막 한 번은 ↺ 되돌리기(move_undo)."""
    ensure(c)
    valid = (res or {}).get("valid") or set()
    if target not in valid:
        return {"ok": False, "message": "옮길 수 없는 곳입니다."}
    if when not in ("new", "all", "one"):
        return {"ok": False, "message": "언제부터 옮길지 골라 주세요."}
    rows = [r for r in _own_rows(c, uid, ids) if "@" in (r["e"] or "")]
    if not rows:
        return {"ok": False, "message": "옮길 받은 메일이 없습니다(보낸 메일은 폴더에 넣지 않습니다)."}
    undo = {"add": [], "del": [], "pins": []}
    name = (res.get("labels") or {}).get(target, "")
    if when == "one":
        for r in rows:
            if r["pin"] != target:
                undo["pins"].append([r["id"], r["pin"]])
                c.execute("UPDATE mail_messages SET fd_pin=? WHERE id=? AND user_id=?", (target, r["id"], uid))
        pats = []
    else:
        es = sorted({r["e"] for r in rows})
        if scope == "person":
            pats = sorted({("email", e) for e in es})
        else:
            pats = sorted({rule_target(e, res) for e in es if rule_target(e, res)})
        since = ""
        if when == "new":
            since = c.execute("SELECT datetime('now','localtime')").fetchone()[0]
        for kind, pat in pats:
            _put_rule(c, uid, kind, pat, target, since, undo)
        if when == "all":
            # 지난 메일도 모두 — 그 보낸 곳의 「이 메일만」 옮김도 풀어 함께 따라가게
            w = _pat_tables(c, pats)
            for r in c.execute("SELECT id, fd_pin FROM mail_messages WHERE user_id=? AND direction='in' AND COALESCE(fd_pin,'')<>'' AND "
                               + w, (uid,)).fetchall():
                undo["pins"].append([r["id"], r["fd_pin"]])
            c.execute("UPDATE mail_messages SET fd_pin='' WHERE user_id=? AND direction='in' AND COALESCE(fd_pin,'')<>'' AND " + w, (uid,))
        else:
            # 지금부터만 — 고른 메일은 함께 옮김(끌어 놓은 메일이 제자리에 남지 않게) · 그 밖의 지난 메일은 그대로
            for r in rows:
                if r["pin"] != target:
                    undo["pins"].append([r["id"], r["pin"]])
                    c.execute("UPDATE mail_messages SET fd_pin=? WHERE id=? AND user_id=?", (target, r["id"], uid))
    before = _match_count(c, uid, pats, target) if pats else 0
    _CACHE.pop(uid, None)
    res2 = classify(c, uid)
    after = _match_count(c, uid, pats, target) if pats else 0
    total = _match_count(c, uid, pats) if pats else 0
    import json as _json
    _set_flag(c, uid, "move_undo", _json.dumps(undo, ensure_ascii=False))
    return {"ok": True, "name": name or res2.get("labels", {}).get(target, ""), "when": when, "scope": scope,
            "n_sel": len(rows), "moved": max(0, after - before), "in_target": after, "total": total,
            "kept": max(0, total - after), "label": _pat_label(pats) if pats else ""}


def move_undo(c, uid) -> int:
    """마지막 옮기기 되돌리기 — 넣은 규칙 지우고 · 바꾼 규칙 다시 넣고 · 「이 메일만」 표시를 예전대로."""
    ensure(c)
    import json as _json
    try:
        u = _json.loads(_flag(c, uid, "move_undo") or "{}")
    except Exception:
        u = {}
    if not u:
        return 0
    n = 0
    for rid in u.get("add") or []:
        n += c.execute("DELETE FROM mail_move_rules WHERE id=? AND user_id=?", (rid, uid)).rowcount
    for r in u.get("del") or []:
        c.execute("INSERT INTO mail_move_rules(user_id, kind, pattern, target, since, created_at) VALUES(?,?,?,?,?,?)",
                  (uid, r.get("kind"), r.get("pattern"), r.get("target"), r.get("since") or "", r.get("created_at")))
        n += 1
    for mid, pin in u.get("pins") or []:
        n += c.execute("UPDATE mail_messages SET fd_pin=? WHERE id=? AND user_id=?", (pin or "", mid, uid)).rowcount
    _set_flag(c, uid, "move_undo", "")
    _CACHE.pop(uid, None)
    return n


def delete_rule(c, uid, rule_id) -> bool:
    ensure(c)
    n = c.execute("DELETE FROM mail_move_rules WHERE id=? AND user_id=?", (rule_id, uid)).rowcount
    _CACHE.pop(uid, None)
    return bool(n)


def sub_suggest(c, uid, res, fid, limit=30) -> dict:
    """11-22 대표 「삼성그룹 하단에 더 구분 · 다른 회사도 구분」 — 그 폴더(아래 폴더 포함)에 든 메일의 서명 회사 이름·부서를 모아
    아래 폴더 후보와 통수를 돌려준다(화면에만 보임 · 사람이 골라 만듦). 이미 있는 아래 폴더·그 폴더 이름과 같은 것은 뺌."""
    ensure(c)
    f = c.execute("SELECT id, name, parent_id FROM mail_folders WHERE id=? AND user_id=?", (fid, uid)).fetchone()
    dp = _depth(c, uid, fid)
    if not f or dp not in (0, 1):
        return {"ok": False, "message": "이 폴더 아래로는 더 나눌 수 없습니다(3단계까지)."}
    key = "f%d" % fid
    ks = sorted((res.get("keys_of") or {}).get(key) or {key})
    have = {norm_name(f["name"])}
    for r in c.execute("SELECT name, COALESCE(aliases,'') AS al FROM mail_folders WHERE user_id=? AND parent_id=?", (uid, fid)).fetchall():
        have.add(norm_name(r["name"]))
        for a in re.split(r"[,\n]+", r["al"]):
            if a.strip():
                have.add(norm_name(a))
    q = ",".join("?" * len(ks))
    comps, depts = {}, {}
    for r in c.execute("SELECT lower(from_email) AS e, MAX(from_name) AS nm, MAX(id) AS lid, COUNT(*) AS n FROM mail_messages "
                       "WHERE user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0 AND COALESCE(fd_key,'') IN (" + q + ") "
                       "GROUP BY lower(from_email)", (uid, *ks)).fetchall():
        e = (r["e"] or "").strip()
        if not e or _is_robot(e):
            continue
        comp, dept = _sig_of(c, e, r["lid"], r["nm"])
        cn = _clean_comp(comp)
        nn = norm_name(cn)
        if cn and len(nn) >= 2 and nn not in have:
            a = comps.setdefault(nn, {"name": cn, "by": "회사", "senders": 0, "n": 0})
        elif dp == 0 or not (dept or "").strip() or norm_name(dept) in have:
            continue
        else:   # 회사 이름이 이 폴더와 같으면 부서로(예: 드림텍 → 사업부)
            dn = re.sub(r"\s+", " ", dept).strip()[:40]
            a = depts.setdefault(norm_name(dn), {"name": dn, "by": "부서", "senders": 0, "n": 0})
        a["senders"] += 1
        a["n"] += r["n"] or 0
    out = sorted(list(comps.values()) + list(depts.values()), key=lambda x: (-x["n"], x["name"]))[:limit]
    return {"ok": True, "folder": f["name"], "depth": dp, "items": out}


def make_subs(c, uid, fid, names) -> dict:
    """「💡 아래 폴더 추천」에서 고른 이름으로 아래 폴더를 만든다(같은 이름이 있으면 건너뜀) — 메일은 서명·이름으로 저절로 그 안으로."""
    ensure(c)
    if _depth(c, uid, fid) not in (0, 1):
        return {"ok": False, "message": "이 폴더 아래로는 더 나눌 수 없습니다(3단계까지)."}
    have = {norm_name(r["name"]) for r in c.execute("SELECT name FROM mail_folders WHERE user_id=? AND parent_id=?", (uid, fid)).fetchall()}
    made = []
    for nm in list(names or [])[:40]:
        nm = re.sub(r"\s+", " ", (nm or "")).strip()[:60]
        if not nm or norm_name(nm) in have:
            continue
        if add_folder(c, uid, nm, fid):
            made.append(nm)
            have.add(norm_name(nm))
    _CACHE.pop(uid, None)
    return {"ok": True, "made": made}


def stamp_arrival(c, mail_id, from_email) -> None:
    """11-22 대표 「부서 이동은 바뀐 날부터 새 부서」 — 새로 받은 사내 메일에 **지금 부서**를 적어 둔다
    (나중에 부서가 바뀌어도 이 메일은 이 부서 폴더 그대로). 주소로 한 부서만 나올 때만 · 못 찾으면 폴더를 열 때 채움."""
    e = (from_email or "").strip().lower()
    if _dom(e) not in OUR_DOMAINS:
        return
    tids = set()
    for sql in ("SELECT team_id FROM users WHERE lower(trim(COALESCE(email,'')))=?",
                "SELECT u.team_id FROM user_mail_creds m JOIN users u ON u.id=m.user_id WHERE lower(trim(m.smtp_email))=?",
                "SELECT u.team_id FROM mail_aliases m JOIN users u ON u.id=m.user_id WHERE lower(trim(m.address))=?"):
        try:
            tids |= {r[0] for r in c.execute(sql, (e,)).fetchall() if r[0] is not None}
        except Exception:
            pass
    if len(tids) == 1:
        c.execute("UPDATE mail_messages SET fd_team=? WHERE id=? AND fd_team IS NULL", (next(iter(tids)), mail_id))


# ─── 폴더 고치기(관리 화면) ────────────────────────────────────────
def add_folder(c, uid, name, parent_id=None, kind="") -> int:
    ensure(c)
    name = (name or "").strip()[:60]
    if not name:
        return 0
    if parent_id:
        if _depth(c, uid, parent_id) not in (0, 1):   # 11-22: 묶음 → 폴더 → 아래 폴더(삼성그룹 → 삼성전자)까지
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


def _depth(c, uid, fid):
    """폴더 깊이 — 0 묶음 · 1 폴더 · 2 아래 폴더 · 없으면 None."""
    d, cur = 0, fid
    for _ in range(5):
        r = c.execute("SELECT parent_id FROM mail_folders WHERE id=? AND user_id=?", (cur, uid)).fetchone()
        if not r:
            return None
        if not r["parent_id"]:
            return d
        d, cur = d + 1, r["parent_id"]
    return None


def set_parent(c, uid, fid, parent_id) -> bool:
    """폴더 위치 바꾸기(관리 화면 「위치」) — 묶음 바로 아래 또는 다른 폴더 아래(3단계까지 · 아래 폴더가 있는 폴더는 묶음 아래만)."""
    ensure(c)
    if _depth(c, uid, fid) not in (1, 2):
        return False
    pd = _depth(c, uid, parent_id)
    if pd not in (0, 1) or parent_id == fid:
        return False
    if pd == 1:
        if c.execute("SELECT 1 FROM mail_folders WHERE user_id=? AND parent_id=?", (uid, fid)).fetchone():
            return False
        g = c.execute("SELECT kind FROM mail_folders WHERE id=(SELECT parent_id FROM mail_folders WHERE id=?)", (parent_id,)).fetchone()
        if g and g["kind"] == "staff":
            return False
    mx = c.execute("SELECT COALESCE(MAX(sort),0) FROM mail_folders WHERE user_id=? AND parent_id=?", (uid, parent_id)).fetchone()[0]
    c.execute("UPDATE mail_folders SET parent_id=?, sort=? WHERE id=? AND user_id=?", (parent_id, (mx or 0) + 10, fid, uid))
    _CACHE.pop(uid, None)
    return True


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
    if not c.execute("SELECT 1 FROM mail_folders WHERE id=? AND user_id=?", (fid, uid)).fetchone():
        return 0
    ids, cur = [fid], [fid]
    for _ in range(3):   # 아래 폴더·그 아래 폴더까지
        q0 = ",".join("?" * len(cur))
        cur = [r["id"] for r in c.execute("SELECT id FROM mail_folders WHERE user_id=? AND parent_id IN (%s)" % q0,
                                          (uid, *cur)).fetchall()]
        if not cur:
            break
        ids += cur
    q = ",".join("?" * len(ids))
    c.execute("DELETE FROM mail_move_rules WHERE user_id=? AND target IN (%s)" % q, (uid, *["f%d" % i for i in ids]))
    try:   # 「이 메일만」 그 폴더로 옮긴 메일은 자동 분류로 되돌림(메일은 그대로)
        c.execute("UPDATE mail_messages SET fd_pin='' WHERE user_id=? AND fd_pin IN (%s)" % q, (uid, *["f%d" % i for i in ids]))
    except Exception:
        pass
    n = c.execute("DELETE FROM mail_folders WHERE user_id=? AND id IN (%s)" % q, (uid, *ids)).rowcount
    _CACHE.pop(uid, None)
    return n
