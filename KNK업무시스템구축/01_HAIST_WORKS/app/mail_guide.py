# -*- coding: utf-8 -*-
"""메일 3단계(대표 2026-11-20 「다음 진행해」) — ⑧ 🏢 회사 공통 서명 틀 · ⑨ 처음 쓰는 사람 안내 + 인쇄용 설명서.
메일만 하는 것 — 이음 메신저·포털·이음웍스와 겹치지 않게.

  ⑧ 🏢 회사 서명 틀 — 틀(글자 · {이름} 같은 자리표시)만 메일이 가진다.
     채우는 값은 **읽기만**: 이름·직책·부서·휴대폰·메일 = 웍스 직원 명단(users·teams) · 회사·주소·전화·팩스 = 웍스 회사 정보(app_settings).
     ⛔ 메일에는 회사 정보·직원 정보를 고치는 화면이 없다(웍스 일). 값이 비면 그 줄(또는 그 토막)만 빼고 「어디서 채우는지」 알려 준다.
  ⑨ 처음 안내 — 「다시 보지 않기」는 서버(사용자별 · mail_user_prefs)에 둔다(다른 컴퓨터·휴대폰에서도 안 뜨게).
     설명서 내용(MANUAL)은 여기 한 곳 — 단추 이름은 화면 글자 그대로(시험이 템플릿 글자와 맞대 봄).
"""
import html as _html
import re

LANGS = ("ko", "en")          # 베트남어 틀은 대표 지시 전 보류(11-20 「베트남어는 아직 진행하지마」) — 말을 더할 땐 여기와 DEFAULT 만
LANG_NAME = {"ko": "한국어", "en": "English"}

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
]
_FKEY = {k: v for k, v, _ in FIELDS}
_FWHERE = {k: w for k, _, w in FIELDS}
_PH = re.compile(r"\{(%s)\}" % "|".join(re.escape(k) for k, _, _ in FIELDS))
_SEP = re.compile(r"(\s+[·|/]\s+)")

# 기본 틀 — 관리자가 아직 정하지 않았을 때(코드에만 · DB 에 넣지 않음). 첫 줄 = 「이름 직책 부서」(회사 이름 표시 규칙)
DEFAULT = {
    "ko": "{이름} {직책} {부서}\n{회사}\n{주소}\nT. {전화} · F. {팩스}\nM. {휴대폰} · E. {메일}",
    "en": "{이름} {직책} | {부서}\n{회사}\n{주소}\nT. {전화} · F. {팩스}\nM. {휴대폰} · E. {메일}",
}
VN_COMPANY = "KNK VINA Co., Ltd."   # 웍스 수출 화면(export_ship)이 쓰는 법인 이름 그대로 — 웍스 회사 정보엔 법인 칸이 없음
MAX_TPL = 1200


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
        "SELECT u.id, COALESCE(u.name,'') AS name, %s AS name_en, %s AS rank, %s AS phone, %s AS email, "
        "COALESCE(t.name,'') AS team_name FROM users u LEFT JOIN teams t ON t.id=u.team_id WHERE u.id=?"
        % (col("name_en"), col("rank"), col("phone"), col("email")), (uid,)).fetchone()
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
    if corp == "vn":
        comp, addr, tel, fax = VN_COMPANY, "", "", ""
    elif lang == "ko":
        comp, addr = co.get("company_name_ko", ""), co.get("company_address", "")
        tel, fax = co.get("company_tel", ""), co.get("company_fax", "")
    else:
        comp, addr = co.get("company_name_en", ""), co.get("company_address_en", "")
        tel, fax = co.get("company_tel", ""), co.get("company_fax", "")
    email = (from_addr or "").strip() or (p.get("email") or "").strip()
    return {"name": nm, "rank": rank, "dept": (p.get("team_name") or "").strip(), "company": (comp or "").strip(),
            "address": (addr or "").strip(), "tel": (tel or "").strip(), "fax": (fax or "").strip(),
            "mobile": (p.get("phone") or "").strip(), "email": email, "_corp": corp}


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
    order = [user_lang] if user_lang in LANGS else []
    order += [x for x in LANGS if x not in order]
    on = [lg for lg in order if tpls[lg]["on"]]
    out = []
    for lg in on:
        v = values_for(c, uid, lg, company, rank_fn, from_addr)
        f = fill(tpls[lg]["body"], v)
        if not f["text"].strip():
            continue
        nm = "🏢 회사 서명" + ("" if len(on) == 1 else " (%s)" % LANG_NAME[lg])
        out.append({"slot": "co-" + lg, "lang": lg, "name": nm, "body": f["html"], "text": f["text"],
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
