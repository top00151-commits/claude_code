# -*- coding: utf-8 -*-
"""메일 3단계(대표 2026-11-20 「다음 진행해」) — ⑧ 🏢 회사 공통 서명 틀 · ⑨ 처음 쓰는 사람 안내 + 인쇄용 설명서.
메일만 하는 것 — 이음 메신저·포털·이음웍스와 겹치지 않게.

  ⑧ 🏢 회사 서명 틀 — 틀(글자 · {이름} 같은 자리표시)만 메일이 가진다.
     채우는 값은 **읽기만**: 이름·직책·부서·휴대폰·메일 = 웍스 직원 명단(users·teams) · 회사·주소·전화·팩스 = 웍스 회사 정보(app_settings).
     ⛔ 메일에는 회사 정보·직원 정보를 고치는 화면이 없다(웍스 일). 값이 비면 그 줄(또는 그 토막)만 빼고 「어디서 채우는지」 알려 준다.
  ⑨ 처음 안내 — 「다시 보지 않기」는 서버(사용자별 · mail_user_prefs)에 둔다(다른 컴퓨터·휴대폰에서도 안 뜨게).
     설명서 내용(MANUAL)은 여기 한 곳 — 단추 이름은 화면 글자 그대로(시험이 템플릿 글자와 맞대 봄).
"""
import base64 as _b64
import html as _html
import os as _os
import re

# 11-22 대표 「베트남 사람은 베트남어 서명을 기본으로」 — 회사 서명만 베트남어 틀을 더함(설명서·처음 안내의 베트남어는 여전히 보류)
LANGS = ("ko", "en", "vi")
LANG_NAME = {"ko": "한국어", "en": "English", "vi": "베트남어"}

# 자리표시 → (값 열쇠, 비었을 때 어디서 채우는지)
FIELDS = [
    ("이름", "name", "웍스 직원 명단"),
    ("직책", "rank", "웍스 직원 명단"),
    ("부서", "dept", "웍스 직원 명단"),
    ("회사", "company", "웍스 회사 정보"),
    ("주소", "address", "웍스 회사 정보"),
    ("전화", "tel", "웍스 회사 정보"),
    ("팩스", "fax", "웍스 회사 정보"),
    ("휴대폰", "mobile", "웍스 직원 명단"),
    ("메일", "email", "웍스 직원 명단"),
    ("영문이름", "name_en", "웍스 직원 명단(영문 이름 · 없으면 메일 주소 이름 부분)"),
    ("영문직책", "rank_en", "웍스 직원 명단"),
    ("한국이름", "name_ko", "웍스 직원 명단"),
    ("한국직책", "rank_ko", "웍스 직원 명단"),
    ("베트남이름", "name_vi", "웍스 직원 명단(베트남 이름 · 없으면 이름)"),
    ("홈페이지", "web", "회사 기본값"),
]
_FKEY = {k: v for k, v, _ in FIELDS}
_FWHERE = {k: w for k, _, w in FIELDS}
_PH = re.compile(r"\{(%s)\}" % "|".join(re.escape(k) for k, _, _ in FIELDS))
_SEP = re.compile(r"(\s+[·|/]\s+)")

# 기본 틀 — 관리자가 아직 정하지 않았을 때(코드에만 · DB 에 넣지 않음).
# 11-22 대표 「디자이너라면 어떻게 정리」 → 본사·베트남 같은 틀: 첫 줄 = 이름 직책 · 부서(굵게) · 둘째 줄 = 영문(회색)
#   · 연락처 = M·T·F·E·W 한 글자 표지 · 마지막 줄 = 회사 · 주소(회색) · 맨 위 로고 그림 · 맨 아래 보안 문구(NOTICE)
DEFAULT = {
    "ko": "{이름} {직책} · {부서}\n{영문이름} · {영문직책}\nM. {휴대폰} · T. {전화} · F. {팩스}\nE. {메일} · W. {홈페이지}\n{회사} · {주소}",
    "en": "{영문이름} · {영문직책}\n{한국이름} {한국직책} · {부서}\nM. {휴대폰} · T. {전화} · F. {팩스}\nE. {메일} · W. {홈페이지}\n{회사} · {주소}",
    "vi": "{베트남이름} · {영문직책}\n{한국이름} {한국직책} · {부서}\nM. {휴대폰} · T. {전화} · F. {팩스}\nE. {메일} · W. {홈페이지}\n{회사} · {주소}",
}
VN_COMPANY = "KNK VINA Co., Ltd."   # 웍스 수출 화면(export_ship)이 쓰는 법인 이름 그대로 — 웍스 회사 정보엔 법인 칸이 없음
# 11-22 베트남 법인 주소·베트남어 회사 표기·베트남어 보안 문구 = app/mail_sig_vi.py 한 곳(베트남어 글자는 거기만)
from .mail_sig_vi import VN_ADDRESS, VN_COMPANY_VI, NOTICE_VI
# 11-22 대표 「Tel. 031-8009-0407 | Fax. 031-267-0407 = 회사 대표번호·대표 팩스 · 본사 인원 전체 동일」 + 본사 서명 사진의 주소
#   웍스 「회사 정보」(관리자)에 값이 있으면 그 값이 먼저 · 비어 있으면 이 값(그 화면은 11-22 지금 저장이 안 되는 고장 — 세션 01 구역)
HQ_TEL = "031-8009-0407"
HQ_FAX = "031-267-0407"
HQ_ADDRESS = "경기도 화성시 병점구 기산로 87번길 2(기산동)"
# 11-22 대표 「본사 영문 주소」(영문 주소 검색 화면 사진 · 도로명 · 우편번호 18387) — 해외 거래처용이라 우편번호를 도 다음에
HQ_ADDRESS_EN = "2, Gisan-ro 87beon-gil, Byeongjeom-gu, Hwaseong-si, Gyeonggi-do 18387, Republic of Korea"
WEB = "www.knknara.com"
WEB_URL = "https://www.knknara.com"   # 11-22 대표 「QR 도 만들어 배치 · www.knknara.com 이 연결되도록」 — 로고·QR 을 누르면 이 주소
MAX_TPL = 1200

# 11-22 대표 「각 서명 아래에 보안 문구 · 고칠 부분 있으면 고쳐서」 — 회사 서명마다 맨 아래(본사 = 한국어 먼저 · 베트남 법인 = 영어 먼저)
#   고친 점: 「본 문서」→ 메일(첨부 포함) · 법률 정식 이름 · 손으로 끊은 줄(「금지/됩니다」) 없앰 · 영어 복수·대한민국 법 표기 · 중간 빈 줄 없앰
NOTICE = {
    "ko": ("이 메일(첨부 파일 포함)은 지정된 수신인만을 위한 것이며, 「부정경쟁방지 및 영업비밀보호에 관한 법률」 등 관련 법령에 따라 "
           "보호되는 영업비밀·산업기술 또는 기밀 정보를 담고 있을 수 있습니다. 이 메일에 담긴 정보의 전부 또는 일부를 허가 없이 "
           "제3자에게 공개·배포·복사하거나 사용하는 것은 엄격히 금지됩니다. 이 메일을 잘못 받으신 경우 발신인에게 알려 주시고 "
           "즉시 삭제해 주시기 바랍니다."),
    "en": ("This email, including any attachments, is intended solely for the named addressee(s) and may contain trade secrets, "
           "industrial technology, or other confidential information protected under applicable laws, including the Unfair Competition "
           "Prevention and Trade Secret Protection Act of the Republic of Korea. Any unauthorized disclosure, distribution, copying, "
           "or use of all or part of this information is strictly prohibited. If you have received this email in error, please "
           "notify the sender immediately and delete it."),
    "vi": NOTICE_VI,                  # 11-22 베트남어 서명용(app/mail_sig_vi.py)
}
SIG_PREF = "sig_default"     # 사람마다 「새 메일에 기본으로 넣을 서명」(mail_user_prefs) — 비면 회사 서명 기본 규칙
_LOGO = {}


def _img_src(fn: str) -> str:
    """서명 그림 — 본문에 품어(data:) 둠 → 보낼 때 인라인 첨부(cid)로 바뀌어 받는 쪽에서도 보임(mail_send._inline_data_images)."""
    if fn not in _LOGO:
        p = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "static", fn)
        try:
            with open(p, "rb") as fh:
                _LOGO[fn] = "data:image/png;base64," + _b64.b64encode(fh.read()).decode()
        except Exception:
            _LOGO[fn] = ""
    return _LOGO[fn]


def logo_src() -> str:
    return _img_src("mail_sig_logo.png")


def qr_src() -> str:
    """홈페이지 QR(https://www.knknara.com) — 이 PC 에서 만든 그림(static/mail_sig_qr.png · 외부 QR 서비스 안 씀)."""
    return _img_src("mail_sig_qr.png")


_RE_EN_FROM_MAIL = re.compile(r"^([a-z]{2,})[._]([a-z]{2,})$")


def en_name_from_mail(email: str) -> str:
    """영문 이름 칸이 없을 때 — 메일 주소 이름 부분 「jiman.park」→「Jiman Park」(본인이 정한 로마자 그대로 · 꼴이 다르면 빈 값)."""
    loc = (email or "").split("@", 1)[0].strip().lower()
    m = _RE_EN_FROM_MAIL.match(loc)
    return ("%s %s" % (m.group(1).title(), m.group(2).title())) if m else ""


def design_html(text: str, corp: str, lang: str = "ko") -> str:
    """채운 서명 글 → 메일 서명 모양(표 · 글자 모양은 칸마다 직접 — 메일 프로그램마다 같게).
    맨 위 로고 · 첫 줄 굵게 · 둘째 줄 회색(영문) · 마지막 줄 회색(회사·주소) · 맨 아래 보안 문구(본사 한국어 서명 = 한국어 먼저 · 베트남 법인·영어 서명 = 영어 먼저)."""
    lines = [ln for ln in (text or "").split("\n") if ln.strip()]
    n = len(lines)
    rows = []
    src, qr = logo_src(), qr_src()
    if src or qr:
        cells = ""
        if src:
            cells += ('<td style="vertical-align:middle;padding:0 14px 0 0"><a href="%s" target="_blank" style="text-decoration:none">'
                      '<img src="%s" width="220" alt="KNK HAIST Innovation" style="display:block;width:220px;height:auto;border:0"></a></td>'
                      % (WEB_URL, src))
        if qr:
            cells += ('<td style="vertical-align:middle;padding:0"><a href="%s" target="_blank" title="%s" style="text-decoration:none">'
                      '<img src="%s" width="56" height="56" alt="QR %s" style="display:block;width:56px;height:56px;border:0"></a></td>'
                      % (WEB_URL, WEB, qr, WEB))
        rows.append('<tr><td style="padding:0 0 10px"><table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse">'
                    '<tr>%s</tr></table></td></tr>' % cells)
    for i, ln in enumerate(lines):
        e = _html.escape(ln)
        if i == 0:
            st = "font-size:15px;font-weight:bold;color:#111827;line-height:1.5"
        elif (i == 1 and n >= 4) or (i == n - 1 and n >= 3):
            st = "font-size:12px;color:#6b7280;line-height:1.6"
        else:
            st = "font-size:12.5px;color:#1f2937;line-height:1.7"
        pad = "padding:0 0 4px" if (i == 1 and n >= 4) else "padding:0"
        rows.append('<tr><td style="%s;%s">%s</td></tr>' % (pad, st, e))
    order = ("vi", "en") if lang == "vi" else (("en", "ko") if (corp == "vn" or lang == "en") else ("ko", "en"))
    nt = "".join('<p style="margin:0 0 6px">%s</p>' % _html.escape(NOTICE[k]) for k in order)
    rows.append('<tr><td style="padding:12px 0 0"><div style="border-top:1px solid #e5e7eb;padding-top:8px;font-size:11px;'
                'line-height:1.55;color:#9ca3af;max-width:640px">%s</div></td></tr>' % nt)
    return ('<table class="knk-co-sig" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;'
            "font-family:'Malgun Gothic','Apple SD Gothic Neo',Arial,sans-serif;max-width:640px\">%s</table>" % "".join(rows))


def ensure(c):
    c.execute("""CREATE TABLE IF NOT EXISTS mail_company_sig(
        lang TEXT PRIMARY KEY,                  -- ko · en
        body TEXT DEFAULT '',                   -- 빈 글 = 이 말로는 회사 서명을 쓰지 않음(끄기)
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        updated_by INTEGER)""")
    c.execute("""CREATE TABLE IF NOT EXISTS mail_user_prefs(
        user_id INTEGER NOT NULL, key TEXT NOT NULL, value TEXT DEFAULT '',
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        PRIMARY KEY(user_id, key))""")


# ═══════════════════════ ⑧ 회사 서명 틀 ═══════════════════════
def get_templates(c) -> dict:
    """{lang: {body, custom(관리자가 정함), on, updated_at, updated_by}} — 세 말 모두(없으면 기본 틀)."""
    ensure(c)
    saved = {}
    for r in c.execute("SELECT lang, body, updated_at, updated_by FROM mail_company_sig").fetchall():
        saved[r["lang"]] = dict(r)
    out = {}
    for lg in LANGS:
        s = saved.get(lg)
        if s is not None:
            body = s["body"] or ""
            out[lg] = {"body": body, "custom": True, "on": bool(body.strip()), "updated_at": s["updated_at"] or "",
                       "updated_by": s["updated_by"]}
        else:
            out[lg] = {"body": DEFAULT[lg], "custom": False, "on": True, "updated_at": "", "updated_by": None}
    return out


def save_template(c, lang: str, body: str, uid, mode: str = "save"):
    """mode: save(이 글로) · off(이 말은 쓰지 않음) · default(기본 틀로 되돌림). 관리자 판정은 부르는 쪽(라우트)."""
    ensure(c)
    if lang not in LANGS:
        return False, "모르는 말입니다"
    if mode == "default":
        c.execute("DELETE FROM mail_company_sig WHERE lang=?", (lang,))
        return True, "기본 틀로 되돌렸습니다"
    body = "" if mode == "off" else _clean_tpl(body)
    if mode == "save" and not body.strip():
        return False, "틀이 비어 있습니다 — 이 말을 쓰지 않으려면 「이 말은 쓰지 않기」를 누르세요"
    c.execute("INSERT INTO mail_company_sig(lang, body, updated_at, updated_by) VALUES(?,?,datetime('now','localtime'),?) "
              "ON CONFLICT(lang) DO UPDATE SET body=excluded.body, updated_at=excluded.updated_at, updated_by=excluded.updated_by",
              (lang, body, uid))
    return True, ("저장했습니다" if body else "이 말은 쓰지 않게 했습니다")


def _clean_tpl(body: str) -> str:
    t = (body or "").replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"<[^>]*>", "", t)                       # 틀은 글자만(서식·그림은 개인 서명에서)
    lines = [ln.rstrip() for ln in t.split("\n")]
    while lines and not lines[-1].strip():
        lines.pop()
    while lines and not lines[0].strip():
        lines.pop(0)
    return "\n".join(lines)[:MAX_TPL]


def corp_of(c, uid) -> str:
    """kr(KNK 본사) · vn(KNK VINA 법인) — 웍스 주소록(contacts.list_staff)과 같은 판단: users.entity 'VN' 또는 사번 VN…"""
    try:
        cols = {r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()}
        en = "COALESCE(entity,'')" if "entity" in cols else "''"
        no = "COALESCE(employee_no,'')" if "employee_no" in cols else "''"
        r = c.execute("SELECT %s AS en, %s AS no FROM users WHERE id=?" % (en, no), (uid,)).fetchone()
        if r and ((r["en"] or "").upper() == "VN" or str(r["no"] or "").upper().startswith("VN")):
            return "vn"
    except Exception:
        pass
    return "kr"


def person_row(c, uid) -> dict:
    """웍스 직원 명단 한 사람(읽기만) — 이름·영문 이름·직책·부서·휴대폰·메일."""
    cols = {r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()}

    def col(n):
        return ("COALESCE(u.%s,'')" % n) if n in cols else "''"
    r = c.execute(
        "SELECT u.id, COALESCE(u.name,'') AS name, %s AS name_en, %s AS name_vi, %s AS lang, %s AS rank, %s AS phone, %s AS email, "
        "COALESCE(t.name,'') AS team_name FROM users u LEFT JOIN teams t ON t.id=u.team_id WHERE u.id=?"
        % (col("name_en"), col("name_vi"), col("lang"), col("rank"), col("phone"), col("email")), (uid,)).fetchone()
    return dict(r) if r else {}


def values_for(c, uid, lang: str, company: dict, rank_fn=None, from_addr: str = "") -> dict:
    """틀에 넣을 값 — 보는 사람 소속 법인 기준. company = 웍스 _company_info_dict() 결과(읽기만)."""
    p = person_row(c, uid)
    corp = corp_of(c, uid)
    nm = (p.get("name") or "").strip()
    if lang == "en" and (p.get("name_en") or "").strip():
        nm = p["name_en"].strip()
    rank = (p.get("rank") or "").strip()
    if rank and rank_fn and lang != "ko":
        try:
            rank = rank_fn(rank, lang) or rank
        except Exception:
            pass
    co = company or {}
    em = (from_addr or "").strip() or (p.get("email") or "").strip()
    nm_en = (p.get("name_en") or "").strip() or en_name_from_mail(em) or en_name_from_mail(p.get("email") or "")
    rank_en = ""
    if nm_en and rank and rank_fn:
        try:
            rank_en = (rank_fn((p.get("rank") or "").strip(), "en") or "").strip()
        except Exception:
            rank_en = ""
    if rank_en == (p.get("rank") or "").strip():
        rank_en = ""          # 영문으로 못 바꾼 직책(한글 그대로)은 영문 줄에 넣지 않음
    if corp == "vn":
        comp, addr, tel, fax = (VN_COMPANY_VI if lang == "vi" else VN_COMPANY), VN_ADDRESS, "", ""
    elif lang == "ko":
        comp, addr = co.get("company_name_ko", ""), (co.get("company_address", "") or "").strip() or HQ_ADDRESS
        tel, fax = (co.get("company_tel", "") or "").strip() or HQ_TEL, (co.get("company_fax", "") or "").strip() or HQ_FAX
    else:
        comp, addr = co.get("company_name_en", ""), (co.get("company_address_en", "") or "").strip() or HQ_ADDRESS_EN
        tel, fax = (co.get("company_tel", "") or "").strip() or HQ_TEL, (co.get("company_fax", "") or "").strip() or HQ_FAX
    email = (from_addr or "").strip() or (p.get("email") or "").strip()
    return {"name": nm, "rank": rank, "dept": (p.get("team_name") or "").strip(), "company": (comp or "").strip(),
            "address": (addr or "").strip(), "tel": (tel or "").strip(), "fax": (fax or "").strip(),
            "mobile": (p.get("phone") or "").strip(), "email": email, "name_en": nm_en, "rank_en": rank_en, "web": WEB,
            "name_ko": (p.get("name") or "").strip(), "rank_ko": (p.get("rank") or "").strip(),
            "name_vi": (p.get("name_vi") or "").strip() or (p.get("name") or "").strip(),
            "_corp": corp, "_vi_person": is_vi_person(p, corp)}


def is_vi_person(p: dict, corp: str) -> bool:
    """베트남 법인의 베트남 사람인가 — 이음 메신저에서 넘어온 쓰는 말(users.lang = vi). 한국 사람(ko)은 아님."""
    return corp == "vn" and (p.get("lang") or "").strip().lower() == "vi"


def sig_langs(c, uid) -> list:
    """이 사람의 회사 서명 말(맨 앞 = 기본) — 11-22 대표
    본사 = 한국어(기본)·영어 · 베트남 법인 한국 사람 = 한국어(기본)·영어 · 베트남 법인 베트남 사람 = 베트남어(기본)·한국어·영어."""
    corp = corp_of(c, uid)
    if is_vi_person(person_row(c, uid), corp):
        return ["vi", "ko", "en"]
    return ["ko", "en"]


def default_slot(c, uid, sig_list: list) -> str:
    """새 메일에 넣을 서명 — 사람이 고른 것(서명 화면) → 없으면 회사 서명 맨 앞(한국어 · 베트남 사람은 베트남어) → 없으면 개인 기본 서명.
    반환 = 서명 고르기 값('co-ko' · '0' · 'none' …)."""
    have = {str(g.get("slot")): g for g in (sig_list or [])}
    pref = (get_pref(c, uid, SIG_PREF, "") or "").strip()
    if pref == "none":
        return "none"
    if pref and pref in have and (pref.startswith("co-") or (have[pref].get("body") or "").strip()):
        return pref
    for g in sig_list or []:
        if str(g.get("slot", "")).startswith("co-"):
            return str(g["slot"])
    return "0" if "0" in have and (have["0"].get("body") or "").strip() else "none"


def fill(tpl: str, vals: dict) -> dict:
    """틀 + 값 → {text, html, missing[(자리, 어디서)], dropped}.
    · 자리표시가 있는 줄의 값이 **모두** 비면 그 줄을 뺀다
    · 일부만 비면 「 · 」「 | 」「 / 」로 나뉜 토막 중 빈 값 토막만 뺀다(T. 02… · F. (없음) → T. 02…)
    · 남은 빈 값은 지우고 빈칸을 한 칸으로."""
    out_lines, missing, dropped = [], [], 0
    used = set()
    for ln in (tpl or "").split("\n"):
        keys = _PH.findall(ln)
        if not keys:
            out_lines.append(ln.rstrip())
            continue
        for k in keys:
            used.add(k)
        if all(not (vals.get(_FKEY[k]) or "").strip() for k in keys):
            dropped += 1
            continue
        parts = _SEP.split(ln)          # [토막, 가름, 토막, …]
        segs = parts[0::2]
        seps = parts[1::2]
        keep = []
        for i, sg in enumerate(segs):
            ks = _PH.findall(sg)
            if ks and all(not (vals.get(_FKEY[k]) or "").strip() for k in ks):
                continue
            keep.append((seps[i - 1] if i > 0 else "", sg))
        s = ""
        for j, (sep, sg) in enumerate(keep):
            s += (sep if j > 0 else "") + sg
        s = _PH.sub(lambda m: (vals.get(_FKEY[m.group(1)]) or "").strip(), s)
        s = re.sub(r"[ \t]{2,}", " ", s).strip()
        s = re.sub(r"^[·|/]\s*|\s*[·|/]$", "", s).strip()
        if s:
            out_lines.append(s)
        else:
            dropped += 1
    while out_lines and not out_lines[-1].strip():
        out_lines.pop()
    for k, _, _ in FIELDS:
        if k in used and not (vals.get(_FKEY[k]) or "").strip():
            missing.append((k, _FWHERE[k]))
    text = "\n".join(out_lines)
    hl = []
    for i, ln in enumerate(out_lines):
        e = _html.escape(ln)
        hl.append(("<b>%s</b>" % e) if (i == 0 and e) else e)
    return {"text": text, "html": "<br>".join(hl), "missing": missing, "dropped": dropped}


def missing_note(missing, corp: str) -> str:
    """빈 칸 안내 한 줄 — 「휴대폰은 웍스 직원 명단에 없어 뺐습니다」."""
    if not missing:
        return ""
    by = {}
    for k, w in missing:
        by.setdefault(w, []).append(k)
    bits = []
    for w, ks in by.items():
        if corp == "vn" and w == "웍스 회사 정보":
            bits.append("%s — 베트남 법인 것은 웍스 회사 정보에 아직 칸이 없어 뺐습니다" % "·".join(ks))
        else:
            bits.append("%s — %s에 비어 있어 뺐습니다" % ("·".join(ks), w))
    return " · ".join(bits)


def company_sigs(c, uid, company: dict, rank_fn=None, from_addr: str = "", user_lang: str = "ko") -> list:
    """보는 사람 정보로 채운 회사 서명들 — [{slot:'co-ko', lang, name, body(html), text, note}] · 쓰는 말(on)만.
    순서 = 한국어 → 영어."""
    tpls = get_templates(c)
    order = sig_langs(c, uid)          # 11-22 대표: 사람마다 말·기본(맨 앞)이 정해짐 — 보는 화면 말과 상관없이
    on = [lg for lg in order if tpls[lg]["on"]]
    out = []
    for lg in on:
        v = values_for(c, uid, lg, company, rank_fn, from_addr)
        f = fill(tpls[lg]["body"], v)
        if not f["text"].strip():
            continue
        nm = "🏢 회사 서명" + ("" if len(on) == 1 else " (%s)" % LANG_NAME[lg])
        out.append({"slot": "co-" + lg, "lang": lg, "name": nm, "body": design_html(f["text"], v["_corp"], lg), "text": f["text"],
                    "first": not out,
                    "note": missing_note(f["missing"], v["_corp"]), "corp": v["_corp"]})
    return out


# ═══════════════════════ ⑨ 처음 안내 — 사용자별 「다시 보지 않기」 ═══════════════════════
TOUR_KEY = "tour_seen"


def get_pref(c, uid, key: str, default: str = "") -> str:
    ensure(c)
    r = c.execute("SELECT value FROM mail_user_prefs WHERE user_id=? AND key=?", (uid, key)).fetchone()
    return (r["value"] if r else default) or default


def set_pref(c, uid, key: str, value: str):
    ensure(c)
    c.execute("INSERT INTO mail_user_prefs(user_id, key, value, updated_at) VALUES(?,?,?,datetime('now','localtime')) "
              "ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
              (uid, key, str(value)[:200]))


def tour_seen(c, uid) -> bool:
    return get_pref(c, uid, TOUR_KEY, "") == "1"


def set_tour_seen(c, uid, seen: bool = True):
    set_pref(c, uid, TOUR_KEY, "1" if seen else "0")


# ═══════════════════════ ⑨ 인쇄용 설명서 — 한국어(베트남어는 대표 지시 전 보류) ═══════════════════════
# btn = 화면 글자 그대로(시험이 app/templates 의 글자와 맞대 봄) · find = 화면에서 찾을 글자(아이콘이 따로 떨어진 단추)
# 말별 글은 열쇠(ko)로 나눠 둠 — 나중에 말을 더할 때 같은 자리에 더함
MANUAL = [
    {"id": "open", "ic": "📧",
     "t": {"ko": "메일함 열기와 화면"},
     "items": [
         {"btn": "📧 HAIST WORKS 메일함", "find": "HAIST WORKS 메일함",
          "ko": "이음 메신저의 📧 아이콘을 누르면 메일함 창이 열립니다. 따로 로그인하지 않습니다."},
         {"btn": "📲 앱 설치",
          "ko": "위 빨간 줄의 「📲 앱 설치」를 누르면 바탕화면·홈 화면에 아이콘이 생깁니다(보일 때만)."},
         {"btn": "✏️ 새 메일", "find": "새 메일",
          "ko": "위 도구 줄은 늘 붙어 있습니다 — 「✏️ 새 메일」 · 「📥 받은편지함」 · 「⭐ 중요」 · 「↩ 회신 필요」 · 「🚩 기한」 · 「📤 보낸편지함」 · 「📝 임시보관함」 · 「📦 보관함」 · 「🗑 휴지통」 · 「🚫 스팸함」."},
         {"btn": "⚙ 설정·정리", "find": "설정·정리",
          "ko": "오른쪽 끝 「🎨 테마」 · 「🔠 글자 크게」 · 「⚙ 설정·정리」 · 「❔ 도움말」. 휴대폰에서는 도구 줄을 옆으로 밀면 더 있습니다."},
     ]},
    {"id": "read", "ic": "📥",
     "t": {"ko": "메일 읽기"},
     "items": [
         {"btn": "오늘 챙길 메일",
          "ko": "받은편지함 위 「오늘 챙길 메일」 한 줄 — ↩ 회신 필요 · 🚩 오늘까지 기한 · ⏳ 답 기다림 · ⏱ 오늘 예약. 숫자를 누르면 그 메일만 보입니다."},
         {"btn": "↩ 답장",
          "ko": "메일을 한 번 누르면 옆 칸에서 읽고, 두 번 누르면 새 창으로 엽니다. 메일 위에서 오른쪽 클릭 = 답장·전달·중요·보관·폴더로·삭제 메뉴."},
         {"btn": "↩↩ 전체답장",
          "ko": "열린 메일 위 단추 — 「↩ 답장」 · 「↩↩ 전체답장」 · 「↪ 전달」 · 「☆ 중요 표시」 · 「📦 보관」 · 「🗑 삭제」."},
         {"btn": "🚩 기한·알림",
          "ko": "「🚩 기한·알림 ▾」에서 이 메일의 기한(🚩)이나 다시 알림(⏰ 정한 때까지 숨겼다가 다시 보여 줌)을 정합니다."},
         {"btn": "📦 보관",
          "ko": "「📦 보관」은 지우지 않고 받은편지함에서만 뺍니다. 찾기·폴더·📦 보관함에는 그대로 있습니다."},
     ]},
    {"id": "write", "ic": "✏️",
     "t": {"ko": "메일 쓰기"},
     "items": [
         {"btn": "📇 주소록",
          "ko": "받는사람 칸에 이름이나 주소를 몇 글자만 치면 아래에 고를 사람이 나옵니다. 「📇 주소록」으로 골라 넣어도 됩니다."},
         {"btn": "📝 양식",
          "ko": "「📝 양식」 = 자주 쓰는 글(견적서 송부·발주 확인·납기 안내…). 노란 [빈칸]은 Tab 키로 차례로 채웁니다."},
         {"btn": "✍️ 서명",
          "ko": "「✍️ 서명」에서 내 서명을 만듭니다(3개까지). 본문 위 「✍」 고르기에서 서명을 바꾸거나 「🏢 회사 서명」을 고를 수 있습니다."},
         {"btn": "📤 보내기",
          "ko": "「📤 보내기」를 누르면 문제가 있을 때만 「보내기 전 확인」 창이 뜹니다(빈 제목·첨부 빠짐·받는 회사 여러 곳 등). 보낸 뒤 10초 안에는 「↺ 보내기 취소」."},
         {"btn": "⏱ 예약",
          "ko": "「⏱ 예약」 → 달력에서 날짜·시각 → 「✓ 확인」 → 「⏱ 예약 보내기」. 창을 닫아도 그때 서버가 보냅니다(시각 = 내 소속 기준)."},
         {"btn": "💾 임시저장",
          "ko": "다 못 썼으면 「💾 임시저장」 → 「📝 임시보관함」에서 이어 씁니다."},
     ]},
    {"id": "group", "ic": "👥",
     "t": {"ko": "그룹 메일 · 받는 사람 묶음"},
     "items": [
         {"btn": "받는 사람 묶음 · 그룹 메일",
          "ko": "knksales@ 같은 그룹 메일 주소를 받는사람에 넣으면 그 아래에 누가 받는지 보입니다. 자주 함께 보내는 사람은 「⚙ 설정·정리」 → 「받는 사람 묶음 · 그룹 메일」에서 묶어 둡니다."},
     ]},
    {"id": "wait", "ic": "⏳",
     "t": {"ko": "거래처 답 챙기기"},
     "items": [
         {"btn": "⏳ 답 받기",
          "ko": "바깥 거래처에 보낼 때 「⏳ 답 받기」에서 기한을 고르면, 그때까지 답이 없을 때 받은편지함 위에 알려 드립니다. 답이 오면 저절로 빠집니다."},
         {"btn": "⏳ 답 기다림",
          "ko": "왼쪽 「⏳ 답 기다림」에 모입니다. 보낸 메일을 열어 「⏳ 답 기다리기」를 눌러도 되고, 「✉ 다시 묻기」로 한 번 더 물을 수 있습니다."},
         {"btn": "📎 첨부 모아 보기",
          "ko": "왼쪽 「📎 첨부 모아 보기」 = 받은·보낸 메일의 첨부만(종류·기간·거래처·파일 이름으로 찾기)."},
     ]},
    {"id": "dlg", "ic": "👉", "pilot": True,
     "t": {"ko": "직원에게 맡기기 (시험 중 — 일부 직원만 보임)"},
     "items": [
         {"btn": "👉 맡기기",
          "ko": "메일을 열고 「👉 맡기기」 → 담당자·기한·한 줄 지시 → 이음 요청으로 갑니다. 독촉·결과 확인은 이음 요청에서 합니다."},
     ]},
    {"id": "away", "ic": "🏖",
     "t": {"ko": "출장·휴가 때"},
     "items": [
         {"btn": "부재중 자동 응답",
          "ko": "「⚙ 설정·정리」 → 「부재중 자동 응답」에서 기간과 글을 정하면, 그 동안 메일을 보낸 사람에게 한 번씩 자동으로 답합니다."},
     ]},
    {"id": "help", "ic": "❔",
     "t": {"ko": "도움말"},
     "items": [
         {"btn": "❔ 도움말", "find": "도움말",
          "ko": "위 「❔ 도움말」에서 단축키를 보고, 「🎓 처음 안내 다시 보기」와 「🖨 설명서(인쇄용)」를 엽니다."},
     ]},
]

SHORTCUTS = [("↑ ↓", "다음 메일"), ("R", "답장"), ("Shift+R", "전체 답장"), ("Shift+F", "전달"), ("Delete", "삭제"),
             ("E", "보관"), ("U", "읽음↔안 읽음"), ("S", "중요"), ("N", "새 메일")]

TITLE = {"ko": "HAIST WORKS 메일 설명서"}


def manual_labels() -> list:
    """설명서에 적은 단추 이름들(화면 글자 그대로여야 함) — 시험용."""
    out = []
    for s in MANUAL:
        for it in s["items"]:
            out.append(it.get("find") or it["btn"])
            for q in re.findall(r"「([^」]+)」", it["ko"]):
                out.append(q)
    return out
