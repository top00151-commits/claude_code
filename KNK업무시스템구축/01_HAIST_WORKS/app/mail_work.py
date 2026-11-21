# -*- coding: utf-8 -*-
"""메일 1단계(대표 2026-11-19 「1단계 진행해」) — 실무자 시간 줄이기 · 메일만 하는 것.
이음 메신저(요청·상태·휴가)·포털·이음웍스(할 일·위임·홈 카드·주소록 고치기)와 겹치지 않게 — 웍스 직원·부서 명단은 **읽기만**.

  ① 📝 자주 쓰는 글(양식)   — 내 양식 · 회사 양식(관리자) · 기본 양식(코드 · 한/영/베) · 빈칸 [품명]
  ② ⏳ 답장 기다리는 메일   — 바깥 거래처에 보낸 메일 · 기한까지 답이 없으면 알림 · 「다시 묻기」
  ③ 📎 첨부 모아 찾기       — 받은·보낸 메일 첨부만 · 종류·기간·상대·이름
  ④ 👥 받는 사람 묶음       — 내 묶음(펼쳐 넣기) · 부서 묶음(웍스 부서 읽기) · 회사 그룹 메일 명단(knksales@ 같은 공용 주소에 누가 있는지)
"""
import json
import re

OUR_DOMAINS = ("knknara.co.kr",)
_OK = set()


def _key(c):
    try:
        return c.execute("PRAGMA database_list").fetchone()[2] or ("mem:%x" % id(c))
    except Exception:
        return "?"


def ensure(c):
    """새 표 둘 + 메일 표 칸 셋(답 기다리기). 기존 자료는 건드리지 않음(만들기만)."""
    k = _key(c)
    if k in _OK:
        return
    c.execute("""CREATE TABLE IF NOT EXISTS mail_templates(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER,                       -- NULL = 회사 양식(관리자)
        title TEXT NOT NULL, subject TEXT DEFAULT '', body TEXT DEFAULT '', lang TEXT DEFAULT 'ko',
        created_at TEXT DEFAULT (datetime('now','localtime')), updated_at TEXT DEFAULT (datetime('now','localtime')),
        updated_by INTEGER)""")
    c.execute("""CREATE TABLE IF NOT EXISTS mail_groups(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL DEFAULT 'mine',      -- 'company' = 회사 그룹 메일(공용 주소 하나) · 'mine' = 내 묶음(펼쳐 넣기)
        owner_id INTEGER,                       -- mine 의 주인 · company 는 NULL
        name TEXT NOT NULL, address TEXT DEFAULT '', members TEXT DEFAULT '[]', note TEXT DEFAULT '',
        updated_at TEXT DEFAULT (datetime('now','localtime')), updated_by INTEGER)""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_mailgrp_addr ON mail_groups(address)")
    for ddl in ("ALTER TABLE mail_messages ADD COLUMN wait_until TEXT",
                "ALTER TABLE mail_messages ADD COLUMN wait_state TEXT",
                "ALTER TABLE mail_messages ADD COLUMN wait_reply_id INTEGER"):
        try:
            c.execute(ddl)
        except Exception:
            pass
    cols = {r[1] for r in c.execute("PRAGMA table_info(mail_messages)").fetchall()}
    if {"wait_until", "wait_state", "wait_reply_id"} <= cols:
        _OK.add(k)


def is_ours(addr):
    d = (addr or "").split("@")[-1].strip().lower()
    return any(d == o or d.endswith("." + o) for o in OUR_DOMAINS)


_ADDR_RE = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")


def addrs_in(text):
    out, seen = [], set()
    for a in _ADDR_RE.findall(text or ""):
        a = a.lower()
        if a not in seen:
            seen.add(a)
            out.append(a)
    return out


# ═══════════════════════ ① 자주 쓰는 글(양식) ═══════════════════════
# 기본 양식 — 코드에만 있음(DB 에 넣지 않음) · 「내 양식으로 복사」해서 고쳐 씀 · [내 이름] 은 넣을 때 저절로 내 이름
BUILTIN = [
    {"key": "b-quote-ko", "lang": "ko", "title": "견적서 송부", "subject": "[KNK] [품명] 견적서 송부",
     "body": "안녕하세요, [거래처] [담당자]님.\nKNK [내 이름]입니다.\n\n요청하신 [품명] 견적서를 첨부와 같이 보내 드립니다.\n- 견적 금액: [금액] (부가세 별도)\n- 납기: [납기]\n- 견적 유효기간: 견적일로부터 30일\n\n검토하시고 궁금하신 점은 언제든 말씀해 주십시오.\n감사합니다."},
    {"key": "b-order-ko", "lang": "ko", "title": "발주서 접수 확인", "subject": "[KNK] 발주서 접수 확인 — [발주 번호]",
     "body": "안녕하세요, [거래처] [담당자]님.\nKNK [내 이름]입니다.\n\n보내 주신 발주서를 잘 받았습니다.\n- 발주 번호: [발주 번호]\n- 품명·수량: [품명] / [수량]\n- 납기: [납기]\n\n일정에 변동이 생기면 바로 알려 드리겠습니다.\n감사합니다."},
    {"key": "b-ship-ko", "lang": "ko", "title": "납기·출하 안내", "subject": "[KNK] [품명] 납기 안내",
     "body": "안녕하세요, [거래처] [담당자]님.\nKNK [내 이름]입니다.\n\n주문하신 [품명]의 납기를 안내드립니다.\n- 출하 예정일: [출하일]\n- 도착 예정일: [도착일]\n- 운송: [운송 방법]\n\n궁금하신 점은 회신 주시면 바로 확인하겠습니다.\n감사합니다."},
    {"key": "b-tax-ko", "lang": "ko", "title": "세금계산서 발행 안내", "subject": "[KNK] [년월] 세금계산서 발행 안내",
     "body": "안녕하세요, [거래처] [담당자]님.\nKNK [내 이름]입니다.\n\n[년월] 거래분 세금계산서를 발행했습니다.\n- 공급가액: [금액]\n- 세액: [세액]\n- 발행일: [발행일]\n\n국세청 홈택스에서 확인하실 수 있습니다. 확인 부탁드립니다.\n감사합니다."},
    {"key": "b-req-ko", "lang": "ko", "title": "자료 요청", "subject": "[KNK] [자료 이름] 요청드립니다",
     "body": "안녕하세요, [거래처] [담당자]님.\nKNK [내 이름]입니다.\n\n[자료 이름]을(를) [기한]까지 보내 주실 수 있을까요?\n- 쓰는 곳: [목적]\n\n바쁘신 중에 번거롭게 해 드려 죄송합니다.\n감사합니다."},
    {"key": "b-nudge-ko", "lang": "ko", "title": "확인 다시 부탁(재촉)", "subject": "[확인 요청] [원래 제목]",
     "body": "안녕하세요, [담당자]님.\nKNK [내 이름]입니다.\n\n지난번 보내 드린 메일(아래)에 대해 확인을 부탁드리고자 다시 연락드립니다.\n바쁘시겠지만 회신 주시면 감사하겠습니다.\n감사합니다."},
    # 11-21 대표 「신입사원 관점」 라 묶음 5-6 — 사내 양식(윗분께 보고·지시 확인·일정 지연) + 거래처 첫 인사
    {"key": "b-in-report-ko", "lang": "ko", "title": "[사내] 업무 보고", "subject": "[보고] [업무 이름] 진행 상황",
     "body": "[받는 분] [직책]님,\n[부서] [내 이름]입니다.\n\n[업무 이름] 진행 상황 보고드립니다.\n- 한 일: [한 일]\n- 남은 일: [남은 일]\n- 문제·도움 필요: [문제]\n- 다음 일정: [다음 일정]\n\n감사합니다."},
    {"key": "b-in-ack-ko", "lang": "ko", "title": "[사내] 지시 확인 답장", "subject": "",
     "body": "[받는 분] [직책]님,\n말씀하신 [업무 이름] 확인했습니다.\n[기한]까지 처리하고 결과 보고드리겠습니다.\n\n감사합니다."},
    {"key": "b-in-delay-ko", "lang": "ko", "title": "[사내] 일정 지연 안내·사과", "subject": "[일정 변경] [업무 이름]",
     "body": "[받는 분] [직책]님,\n[부서] [내 이름]입니다.\n\n[업무 이름]이(가) 처음 말씀드린 [원래 기한]보다 늦어질 것 같아 미리 말씀드립니다. 죄송합니다.\n- 늦어지는 까닭: [까닭]\n- 새 예정일: [새 기한]\n- 줄이려고 하는 일: [대책]\n\n다시 늦어지지 않도록 챙기겠습니다.\n감사합니다."},
    {"key": "b-first-ko", "lang": "ko", "title": "거래처 첫 인사(새 담당)", "subject": "[KNK] 새 담당 인사드립니다 — [내 이름]",
     "body": "안녕하세요, [거래처] [담당자]님.\nKNK [부서] [내 이름]입니다.\n\n이번에 [거래처] 업무를 맡게 되어 인사드립니다.\n앞으로 [맡은 일] 관련해서는 저에게 연락 주시면 됩니다.\n- 전화: [전화]\n\n잘 부탁드립니다.\n감사합니다."},
    {"key": "b-quote-en", "lang": "en", "title": "Quotation", "subject": "[KNK] Quotation for [item]",
     "body": "Dear [contact name],\n\nThis is [my name] from KNK.\nPlease find attached our quotation for [item].\n- Amount: [amount] (VAT excluded)\n- Lead time: [lead time]\n- Valid for 30 days from the quotation date\n\nPlease feel free to contact me if you have any questions.\n\nBest regards,"},
    {"key": "b-order-en", "lang": "en", "title": "Order confirmation", "subject": "[KNK] Order confirmation — [PO number]",
     "body": "Dear [contact name],\n\nThis is [my name] from KNK.\nWe have received your purchase order.\n- PO number: [PO number]\n- Item / Qty: [item] / [quantity]\n- Delivery: [delivery date]\n\nWe will let you know right away if there is any change in the schedule.\n\nBest regards,"},
    {"key": "b-ship-en", "lang": "en", "title": "Delivery schedule", "subject": "[KNK] Delivery schedule for [item]",
     "body": "Dear [contact name],\n\nThis is [my name] from KNK.\nPlease find the delivery schedule for [item] below.\n- Shipping date: [shipping date]\n- Estimated arrival: [arrival date]\n- Shipping method: [method]\n\nPlease reply if you have any questions.\n\nBest regards,"},
    {"key": "b-req-en", "lang": "en", "title": "Request for documents", "subject": "[KNK] Request for [document]",
     "body": "Dear [contact name],\n\nThis is [my name] from KNK.\nCould you please send us [document] by [due date]?\n- Purpose: [purpose]\n\nThank you for your help.\n\nBest regards,"},
    {"key": "b-nudge-en", "lang": "en", "title": "Follow-up", "subject": "[Follow-up] [original subject]",
     "body": "Dear [contact name],\n\nThis is [my name] from KNK.\nI am following up on my previous email below.\nI would appreciate it if you could reply at your earliest convenience.\n\nBest regards,"},
    {"key": "b-quote-vi", "lang": "vi", "title": "Báo giá", "subject": "[KNK] Báo giá [tên hàng]",
     "body": "Kính gửi anh/chị [người phụ trách],\n\nTôi là [tên tôi] từ công ty KNK.\nChúng tôi xin gửi báo giá [tên hàng] trong tệp đính kèm.\n- Giá: [số tiền] (chưa bao gồm VAT)\n- Thời gian giao hàng: [ngày giao]\n- Hiệu lực báo giá: 30 ngày kể từ ngày báo giá\n\nNếu có thắc mắc, xin vui lòng liên hệ với tôi.\n\nTrân trọng,"},
    {"key": "b-order-vi", "lang": "vi", "title": "Xác nhận đơn hàng", "subject": "[KNK] Xác nhận đơn hàng — [số PO]",
     "body": "Kính gửi anh/chị [người phụ trách],\n\nTôi là [tên tôi] từ công ty KNK.\nChúng tôi đã nhận được đơn đặt hàng của quý công ty.\n- Số PO: [số PO]\n- Hàng / Số lượng: [tên hàng] / [số lượng]\n- Ngày giao: [ngày giao]\n\nNếu lịch có thay đổi, chúng tôi sẽ báo ngay.\n\nTrân trọng,"},
    {"key": "b-req-vi", "lang": "vi", "title": "Yêu cầu tài liệu", "subject": "[KNK] Yêu cầu [tên tài liệu]",
     "body": "Kính gửi anh/chị [người phụ trách],\n\nTôi là [tên tôi] từ công ty KNK.\nAnh/chị có thể gửi giúp [tên tài liệu] trước [hạn] được không?\n- Mục đích: [mục đích]\n\nXin cảm ơn.\n\nTrân trọng,"},
    {"key": "b-nudge-vi", "lang": "vi", "title": "Nhắc lại", "subject": "[Nhắc lại] [tiêu đề gốc]",
     "body": "Kính gửi anh/chị [người phụ trách],\n\nTôi là [tên tôi] từ công ty KNK.\nTôi xin nhắc lại email đã gửi trước đây (bên dưới).\nRất mong nhận được phản hồi của anh/chị.\n\nTrân trọng,"},
]
LANG_NAME = {"ko": "한국어", "en": "영어", "vi": "베트남어"}


def _tpl_row(r):
    d = dict(r)
    d["company"] = d.get("owner_id") is None
    return d


def list_templates(c, uid):
    ensure(c)
    mine = [_tpl_row(r) for r in c.execute(
        "SELECT id, owner_id, title, subject, body, lang, updated_at FROM mail_templates WHERE owner_id=? ORDER BY title COLLATE NOCASE", (uid,)).fetchall()]
    comp = [_tpl_row(r) for r in c.execute(
        "SELECT id, owner_id, title, subject, body, lang, updated_at FROM mail_templates WHERE owner_id IS NULL ORDER BY title COLLATE NOCASE").fetchall()]
    return {"mine": mine, "company": comp, "builtin": [dict(b) for b in BUILTIN]}


def save_template(c, uid, *, tid=0, title="", subject="", body="", lang="ko", company=False, is_admin=False):
    """만들기·고치기. 회사 양식은 관리자만. 남의 양식은 못 고침. → (ok, message, id)"""
    ensure(c)
    title, subject, body = (title or "").strip()[:80], (subject or "").strip()[:300], (body or "").strip()[:20000]
    lang = lang if lang in LANG_NAME else "ko"
    if not title:
        return False, "양식 이름을 넣어 주세요.", 0
    if not body and not subject:
        return False, "제목이나 내용을 넣어 주세요.", 0
    if company and not is_admin:
        return False, "회사 양식은 관리자만 만들고 고칠 수 있습니다.", 0
    owner = None if company else uid
    if tid:
        r = c.execute("SELECT owner_id FROM mail_templates WHERE id=?", (tid,)).fetchone()
        if not r:
            return False, "양식을 찾지 못했습니다.", 0
        if r["owner_id"] is None and not is_admin:
            return False, "회사 양식은 관리자만 고칠 수 있습니다.", 0
        if r["owner_id"] is not None and r["owner_id"] != uid:
            return False, "내 양식만 고칠 수 있습니다.", 0
        c.execute("UPDATE mail_templates SET title=?, subject=?, body=?, lang=?, owner_id=?, updated_at=datetime('now','localtime'), updated_by=? WHERE id=?",
                  (title, subject, body, lang, owner, uid, tid))
        return True, "저장했습니다.", tid
    cur = c.execute("INSERT INTO mail_templates(owner_id, title, subject, body, lang, updated_by) VALUES(?,?,?,?,?,?)",
                    (owner, title, subject, body, lang, uid))
    return True, "양식을 만들었습니다.", cur.lastrowid


def delete_template(c, uid, tid, is_admin=False):
    ensure(c)
    r = c.execute("SELECT owner_id FROM mail_templates WHERE id=?", (tid,)).fetchone()
    if not r:
        return False, "양식을 찾지 못했습니다."
    if (r["owner_id"] is None and not is_admin) or (r["owner_id"] is not None and r["owner_id"] != uid):
        return False, "지울 수 없는 양식입니다."
    c.execute("DELETE FROM mail_templates WHERE id=?", (tid,))
    return True, "지웠습니다."


# ═══════════════════════ ④ 받는 사람 묶음 · 회사 그룹 메일 ═══════════════════════
def _staff_by_email(c, emails):
    """웍스 직원 명단 읽기(이름·직책·부서) — 고치지 않음."""
    out = {}
    emails = [e for e in {(e or "").lower() for e in emails} if e]
    for i in range(0, len(emails), 200):
        part = emails[i:i + 200]
        q = ",".join("?" * len(part))
        try:
            for r in c.execute(
                    "SELECT u.id, u.name, COALESCE(u.rank,'') AS rank, lower(u.email) AS em, COALESCE(t.name,'') AS team_name "
                    "FROM users u LEFT JOIN teams t ON t.id=u.team_id WHERE u.is_active=1 AND lower(u.email) IN (%s)" % q, part).fetchall():
                out[r["em"]] = dict(r)
        except Exception:
            pass
    return out


def parse_members(text):
    """「이름 <주소>」·주소만 · 줄/쉼표로 여러 명 → [{name, email}] (같은 주소 한 번)."""
    out, seen = [], set()
    for part in re.split(r"[\n,;]+", text or ""):
        part = part.strip()
        if not part:
            continue
        m = re.match(r'^\s*"?([^"<]*?)"?\s*<\s*([^<>\s]+@[^<>\s]+)\s*>\s*$', part)
        if m:
            nm, em = m.group(1).strip(), m.group(2).strip()
        else:
            ems = _ADDR_RE.findall(part)
            if not ems:
                continue
            em = ems[0]
            nm = part.replace(em, "").strip(" <>()\t\"'")
        em = em.lower()
        if em in seen:
            continue
        seen.add(em)
        out.append({"name": nm[:60], "email": em})
    return out[:300]


def _grp_row(c, r, staff=None):
    d = dict(r)
    try:
        mem = json.loads(d.get("members") or "[]")
    except Exception:
        mem = []
    d["members"] = mem
    d["n"] = len(mem)
    return d


def list_groups(c, uid):
    ensure(c)
    comp = [_grp_row(c, r) for r in c.execute(
        "SELECT * FROM mail_groups WHERE kind='company' ORDER BY name COLLATE NOCASE").fetchall()]
    mine = [_grp_row(c, r) for r in c.execute(
        "SELECT * FROM mail_groups WHERE kind='mine' AND owner_id=? ORDER BY name COLLATE NOCASE", (uid,)).fetchall()]
    return {"company": comp, "mine": mine, "dept": dept_groups(c)}


def dept_groups(c):
    """웍스 부서에서 저절로(읽기만) — 부서별 재직 직원 중 메일 주소 있는 사람."""
    out = []
    try:
        rows = c.execute(
            "SELECT t.id AS tid, t.name AS tname, COALESCE(t.display_order,0) AS ord, u.name, COALESCE(u.rank,'') AS rank, u.email "
            "FROM teams t JOIN users u ON u.team_id=t.id "
            "WHERE u.is_active=1 AND u.email IS NOT NULL AND u.email LIKE '%@%' ORDER BY ord, t.name, u.name").fetchall()
    except Exception:
        return out
    by = {}
    for r in rows:
        g = by.get(r["tid"])
        if not g:
            g = by[r["tid"]] = {"id": "d%s" % r["tid"], "name": "%s 전체" % r["tname"], "team": r["tname"], "members": []}
            out.append(g)
        g["members"].append({"name": r["name"] or "", "email": (r["email"] or "").lower(), "rank": r["rank"], "team_name": r["tname"]})
    for g in out:
        g["n"] = len(g["members"])
    return out


def save_group(c, uid, *, gid=0, kind="mine", name="", address="", members_text="", note="", is_admin=False):
    ensure(c)
    kind = "company" if kind == "company" else "mine"
    name, note = (name or "").strip()[:60], (note or "").strip()[:300]
    address = (address or "").strip().lower()
    if not name:
        return False, "이름을 넣어 주세요.", 0
    if kind == "company":
        if not is_admin:
            return False, "회사 그룹 메일 명단은 관리자만 등록·고칠 수 있습니다.", 0
        if not _ADDR_RE.fullmatch(address or ""):
            return False, "그룹 메일 주소(예: knksales@knknara.co.kr)를 넣어 주세요.", 0
        dup = c.execute("SELECT id FROM mail_groups WHERE kind='company' AND address=? AND id<>?", (address, int(gid or 0))).fetchone()
        if dup:
            return False, "이미 등록된 그룹 메일 주소입니다.", 0
    else:
        address = ""
    mem = parse_members(members_text)
    if not mem:
        return False, "명단에 주소를 한 명 이상 넣어 주세요.", 0
    st = _staff_by_email(c, [m["email"] for m in mem])
    for m in mem:                      # 직원이면 웍스 이름으로(직접 적은 이름보다 정확)
        s = st.get(m["email"])
        if s:
            m["name"] = s["name"] or m["name"]
            m["staff"] = 1
    js = json.dumps(mem, ensure_ascii=False)
    if gid:
        r = c.execute("SELECT kind, owner_id FROM mail_groups WHERE id=?", (gid,)).fetchone()
        if not r:
            return False, "묶음을 찾지 못했습니다.", 0
        if r["kind"] == "company" and not is_admin:
            return False, "회사 그룹 메일은 관리자만 고칠 수 있습니다.", 0
        if r["kind"] == "mine" and r["owner_id"] != uid:
            return False, "내 묶음만 고칠 수 있습니다.", 0
        c.execute("UPDATE mail_groups SET name=?, address=?, members=?, note=?, updated_at=datetime('now','localtime'), updated_by=? WHERE id=?",
                  (name, address, js, note, uid, gid))
        return True, "저장했습니다 · %d명" % len(mem), gid
    cur = c.execute("INSERT INTO mail_groups(kind, owner_id, name, address, members, note, updated_by) VALUES(?,?,?,?,?,?,?)",
                    (kind, (None if kind == "company" else uid), name, address, js, note, uid))
    return True, "등록했습니다 · %d명" % len(mem), cur.lastrowid


def delete_group(c, uid, gid, is_admin=False):
    ensure(c)
    r = c.execute("SELECT kind, owner_id FROM mail_groups WHERE id=?", (gid,)).fetchone()
    if not r:
        return False, "묶음을 찾지 못했습니다."
    if (r["kind"] == "company" and not is_admin) or (r["kind"] == "mine" and r["owner_id"] != uid):
        return False, "지울 수 없는 묶음입니다."
    c.execute("DELETE FROM mail_groups WHERE id=?", (gid,))
    return True, "지웠습니다."


def company_group_map(c):
    ensure(c)
    out = {}
    for r in c.execute("SELECT * FROM mail_groups WHERE kind='company'").fetchall():
        d = _grp_row(c, r)
        if d.get("address"):
            out[d["address"]] = d
    return out


def addr_info(c, addrs):
    """주소마다 — 회사 그룹 메일(명단) · 사내 직원 · 명단 없는 사내 주소(그룹일 수 있음) · 바깥."""
    addrs = [a.lower() for a in addrs if a][:60]
    grp = company_group_map(c)
    st = _staff_by_email(c, addrs + [m.get("email", "") for a in addrs if a in grp for m in grp[a]["members"]])
    out = {}
    for a in addrs:
        if a in grp:
            g = grp[a]
            mem = []
            for m in g["members"]:
                s = st.get(m.get("email", ""))
                mem.append({"email": m.get("email", ""), "name": (s or {}).get("name") or m.get("name") or "",
                            "rank": (s or {}).get("rank", ""), "team_name": (s or {}).get("team_name", ""), "staff": bool(s)})
            out[a] = {"kind": "group", "name": g["name"], "note": g.get("note") or "", "n": len(mem), "members": mem}
        elif a in st:
            s = st[a]
            out[a] = {"kind": "staff", "name": s["name"], "rank": s["rank"], "team_name": s["team_name"]}
        elif is_ours(a):
            out[a] = {"kind": "unknown"}
        else:
            out[a] = {"kind": "external"}
    return out


def guess_members(c, address, days=365):
    """관리자 돕기 — 이 공용 주소로 온 메일이 실제로 들어간 메일함(이음웍스로 받아 오는 사람만) · 명단 정답은 하이웍스 관리자 화면."""
    a = (address or "").strip().lower()
    if not _ADDR_RE.fullmatch(a):
        return []
    like = "%" + a + "%"
    try:
        rows = c.execute(
            "SELECT m.user_id, COUNT(*) AS n, MAX(m.received_at) AS last, u.name, lower(u.email) AS em "
            "FROM mail_messages m JOIN users u ON u.id=m.user_id "
            "WHERE m.direction='in' AND (lower(COALESCE(m.to_email,'')) LIKE ? OR lower(COALESCE(m.to_all,'')) LIKE ? OR lower(COALESCE(m.cc,'')) LIKE ?) "
            "AND m.received_at >= datetime('now','localtime',?) GROUP BY m.user_id ORDER BY n DESC LIMIT 100",
            (like, like, like, "-%d days" % int(days))).fetchall()
    except Exception:
        return []
    return [{"name": r["name"] or "", "email": r["em"] or "", "n": r["n"], "last": (r["last"] or "")[:10]} for r in rows if r["em"]]


def ac_items(c, uid, q, limit=4):
    """받는 사람 자동완성 맨 위 — 회사 그룹 메일(주소 하나) · 내 묶음 · 부서 묶음(펼쳐 넣기)."""
    q = (q or "").strip().lower()
    if not q:
        return []
    ensure(c)
    out = []

    def hit(*xs):
        return any(q in (x or "").lower() for x in xs)
    for g in company_group_map(c).values():
        if hit(g["name"], g["address"], g.get("note")):
            out.append({"name": "👥 " + g["name"], "email": g["address"], "company": "", "position": "",
                        "src": "그룹 메일 · %d명" % g["n"]})
    for r in c.execute("SELECT * FROM mail_groups WHERE kind='mine' AND owner_id=?", (uid,)).fetchall():
        g = _grp_row(c, r)
        if hit(g["name"], g.get("note")):
            out.append({"name": "👥 " + g["name"], "email": "", "src": "내 묶음 · %d명 한꺼번에" % g["n"],
                        "expand": [{"name": m.get("name", ""), "email": m.get("email", "")} for m in g["members"]]})
    if len(q) >= 2:
        for g in dept_groups(c):
            if hit(g["name"], g["team"]):
                out.append({"name": "👥 " + g["name"], "email": "", "src": "부서 · %d명 한꺼번에" % g["n"],
                            "expand": [{"name": m["name"], "email": m["email"]} for m in g["members"]]})
    return out[:limit]


# ═══════════════════════ ② 답장 기다리는 메일 ═══════════════════════
def external_rcpts(row):
    return [a for a in addrs_in((row.get("to_email") or "") + "," + (row.get("cc") or "")) if not is_ours(a)]


def set_wait(c, uid, mail_id, until_date):
    """until_date='YYYY-MM-DD'(보는 사람 소속 날짜) · '' 이면 그만."""
    ensure(c)
    r = c.execute("SELECT id, to_email, cc FROM mail_messages WHERE id=? AND user_id=? AND direction='out' AND is_deleted=0",
                  (mail_id, uid)).fetchone()
    if not r:
        return False, "내가 보낸 메일만 정할 수 있습니다."
    if until_date:
        if not external_rcpts(dict(r)):
            return False, "바깥 거래처가 없는 메일입니다 — 사내 업무는 이음 요청이 독촉·회신까지 챙겨 줍니다."
        c.execute("UPDATE mail_messages SET wait_until=?, wait_state='wait', wait_reply_id=NULL WHERE id=?", (until_date, mail_id))
        return True, "⏳ %s까지 답을 기다립니다" % until_date[5:].replace("-", "/")
    c.execute("UPDATE mail_messages SET wait_state='off' WHERE id=?", (mail_id,))
    return True, "답 기다리기를 그만두었습니다."


def _find_reply(c, uid, row, norm):
    doms = sorted({a.split("@")[-1] for a in external_rcpts(row)})
    if not doms:
        return None
    key = norm(row.get("subject") or "")
    for d in doms:
        for r in c.execute(
                "SELECT id, subject FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 "
                "AND lower(from_email) LIKE ? AND received_at > ? ORDER BY received_at LIMIT 50",
                (uid, "%@" + d, row.get("received_at") or "")).fetchall():
            if norm(r["subject"] or "") == key:
                return r["id"]
    return None


def list_waiting(c, uid, today, norm, include_done=False):
    """기다리는 메일 — 답이 오면 저절로 「답 옴」으로 바뀜. today = 보는 사람 소속 날짜."""
    ensure(c)
    rows = [dict(r) for r in c.execute(
        "SELECT id, to_email, cc, subject, received_at, wait_until, wait_state, wait_reply_id FROM mail_messages "
        "WHERE user_id=? AND direction='out' AND is_deleted=0 AND wait_state IN (%s) ORDER BY wait_until, received_at"
        % ("'wait','replied','done'" if include_done else "'wait'"), (uid,)).fetchall()]
    out = []
    for r in rows:
        if r["wait_state"] == "wait":
            rid = _find_reply(c, uid, r, norm)
            if rid:
                c.execute("UPDATE mail_messages SET wait_state='replied', wait_reply_id=? WHERE id=?", (rid, r["id"]))
                r["wait_state"], r["wait_reply_id"] = "replied", rid
                if not include_done:
                    continue
        r["overdue"] = r["wait_state"] == "wait" and bool(r.get("wait_until")) and r["wait_until"] <= today
        r["rcpts"] = external_rcpts(r)
        out.append(r)
    return out


def count_waiting(c, uid, today, norm):
    try:
        ws = list_waiting(c, uid, today, norm)
    except Exception:
        return {"all": 0, "due": 0}
    return {"all": len(ws), "due": sum(1 for w in ws if w["overdue"])}


# ═══════════════════════ ③ 첨부 모아 찾기 ═══════════════════════
KINDS = {
    "pdf": ("PDF", ("pdf",)),
    "xls": ("엑셀", ("xls", "xlsx", "xlsm", "csv")),
    "doc": ("문서", ("doc", "docx", "hwp", "hwpx", "ppt", "pptx", "txt")),
    "cad": ("도면", ("dwg", "dxf", "step", "stp", "igs", "iges", "x_t", "sldprt", "sldasm", "stl", "ipt", "iam")),
    "img": ("사진", ("jpg", "jpeg", "png", "gif", "bmp", "webp", "heic", "tif", "tiff")),
    "zip": ("압축", ("zip", "7z", "rar", "alz", "egg")),
}


def kind_of(fn):
    ext = (fn or "").rsplit(".", 1)[-1].lower() if "." in (fn or "") else ""
    for k, (_lab, exts) in KINDS.items():
        if ext in exts:
            return k
    return "etc"


def list_files(c, uid, *, q="", kind="", direction="", days=0, who="", limit=100, offset=0):
    where = ["m.user_id=?", "m.is_deleted=0", "COALESCE(m.is_blocked,0)=0", "m.direction IN ('in','out')",
             "COALESCE(a.is_inline,0)=0", "COALESCE(a.filename,'')<>''"]
    args = [uid]
    if direction in ("in", "out"):
        where.append("m.direction=?")
        args.append(direction)
    if q:
        where.append("a.filename LIKE ?")
        args.append("%" + q.strip() + "%")
    if who:
        w = "%" + who.strip() + "%"
        where.append("(m.from_email LIKE ? OR m.from_name LIKE ? OR m.to_email LIKE ? OR m.subject LIKE ?)")
        args += [w, w, w, w]
    if days:
        where.append("m.received_at >= datetime('now','localtime',?)")
        args.append("-%d days" % int(days))
    if kind in KINDS:
        exts = KINDS[kind][1]
        where.append("(" + " OR ".join(["lower(a.filename) LIKE ?"] * len(exts)) + ")")
        args += ["%." + e for e in exts]
    elif kind == "etc":
        allx = [e for _k, (_l, xs) in KINDS.items() for e in xs]
        where.append("(" + " AND ".join(["lower(a.filename) NOT LIKE ?"] * len(allx)) + ")")
        args += ["%." + e for e in allx]
    sql = ("SELECT a.id AS att_id, a.filename, a.size, m.id AS mail_id, m.direction, m.subject, m.from_email, m.from_name, "
           "m.to_email, m.received_at FROM mail_attachments a JOIN mail_messages m ON m.id=a.mail_id WHERE "
           + " AND ".join(where) + " ORDER BY m.received_at DESC, a.id LIMIT ? OFFSET ?")
    rows = [dict(r) for r in c.execute(sql, args + [int(limit) + 1, int(offset)]).fetchall()]
    more = len(rows) > limit
    rows = rows[:limit]
    for r in rows:
        r["kind"] = kind_of(r["filename"])
        r["who"] = (r["from_name"] or r["from_email"] or "") if r["direction"] == "in" else (r["to_email"] or "").split(",")[0]
    return rows, more



# ═══════════════ ④-2 회사 그룹 메일 명단 — 하이웍스 「그룹메일」 파일 올리기(대표 2026-11-20) ═══════════════
# 하이웍스 관리자 화면에서 받은 「knknara.co.kr_그룹메일.xls」(속은 HTML 표) · 엑셀(.xlsx) · CSV 모두 읽음.
# 칸: 그룹명( 계정수 ) · 그룹메일주소 · 사용자명 · 메일주소 — 그룹 첫 줄에만 그룹 칸이 있고 다음 줄은 사람만(rowspan).
# 흐름: 올리기 → 미리 보기(새 그룹·바뀐 그룹(+/-)·그대로·파일에 없는 그룹) → 「✓ 이대로 반영」 → 원본↔저장 대조(✅/⚠).
_IMP_KEY = "mail_groups_import_last"
_GRP_HDR = {"group": ("그룹명", "group name", "group"), "gaddr": ("그룹메일주소", "그룹 메일 주소", "group email", "group address"),
            "uname": ("사용자명", "이름", "name"), "uaddr": ("메일주소", "메일 주소", "email", "e-mail")}


def _rows_from_html(text):
    from html.parser import HTMLParser

    class _P(HTMLParser):
        def __init__(s):
            super().__init__()
            s.rows, s.cur, s.cell = [], None, None

        def handle_starttag(s, t, a):
            if t == "tr":
                s.cur = []
            elif t in ("td", "th"):
                s.cell = []

        def handle_endtag(s, t):
            if t in ("td", "th") and s.cell is not None and s.cur is not None:
                s.cur.append(" ".join("".join(s.cell).split()))
                s.cell = None
            elif t == "tr" and s.cur is not None:
                s.rows.append(s.cur)
                s.cur = None

        def handle_data(s, d):
            if s.cell is not None:
                s.cell.append(d)
    p = _P()
    p.feed(text)
    return p.rows


def _rows_from_xlsx(data):
    import io as _io
    from openpyxl import load_workbook
    wb = load_workbook(_io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.worksheets[0]
    out = []
    for r in ws.iter_rows(values_only=True):
        out.append(["" if v is None else str(v).strip() for v in r])
    return out


def _rows_from_csv(text):
    import csv as _csv
    import io as _io
    return [[(x or "").strip() for x in r] for r in _csv.reader(_io.StringIO(text))]


def parse_group_file(data, filename=""):
    """→ {"groups":[{name, address, declared, members:[{name,email}]}], "warnings":[...], "error": ""}"""
    out = {"groups": [], "warnings": [], "error": ""}
    if not data:
        out["error"] = "빈 파일입니다."
        return out
    if data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        out["error"] = "옛 엑셀(.xls) 형식은 읽지 못합니다 — 하이웍스에서 받은 파일을 그대로 올리거나, 엑셀에서 「다른 이름으로 저장 → .xlsx」 해 주세요."
        return out
    try:
        if data[:2] == b"PK":
            rows = _rows_from_xlsx(data)
        else:
            text = None
            for enc in ("utf-8-sig", "cp949", "euc-kr"):
                try:
                    text = data.decode(enc)
                    break
                except Exception:
                    continue
            if text is None:
                text = data.decode("utf-8", "replace")
            rows = _rows_from_html(text) if "<t" in text[:5000].lower() else _rows_from_csv(text)
    except Exception as e:
        out["error"] = "파일을 읽지 못했습니다(%s)." % str(e)[:80]
        return out
    hi, col = -1, {}
    for i, r in enumerate(rows[:20]):
        low = [(x or "").replace(" ", "").lower() for x in r]
        found = {}
        for k in ("gaddr", "group", "uaddr", "uname"):
            for j, cell in enumerate(low):
                if j in found.values():
                    continue
                if any(cell.startswith(n.replace(" ", "").lower()) for n in _GRP_HDR[k]):
                    found[k] = j
                    break
        if {"group", "gaddr", "uaddr"} <= set(found):
            hi, col = i, found
            break
    if hi < 0:
        out["error"] = "「그룹명 · 그룹메일주소 · 사용자명 · 메일주소」 머리 줄을 찾지 못했습니다 — 하이웍스 그룹 메일 목록 파일인지 확인해 주세요."
        return out
    ncol = len(rows[hi])
    groups, seen_addr = [], {}
    cur = None
    for ln, r in enumerate(rows[hi + 1:], start=hi + 2):
        if not any((x or "").strip() for x in r):
            continue
        if len(r) >= ncol:
            gname, gaddr = r[col["group"]].strip(), r[col["gaddr"]].strip().lower()
            uname = r[col["uname"]].strip() if "uname" in col else ""
            uaddr = r[col["uaddr"]].strip().lower()
        elif len(r) == 2:                      # 하이웍스 표: 그룹 칸이 위 줄에 합쳐짐(rowspan) → 사람만
            gname, gaddr, uname, uaddr = "", "", r[0].strip(), r[1].strip().lower()
        else:
            out["warnings"].append("%d번째 줄: 칸 수가 맞지 않아 건너뜀" % ln)
            continue
        if gaddr:
            if not _ADDR_RE.fullmatch(gaddr):
                out["warnings"].append("%d번째 줄: 그룹 주소가 올바르지 않아 그 그룹을 건너뜀 (%s)" % (ln, gname[:30]))
                cur = None
                continue
            m = re.match(r"^(.*?)\s*\(\s*(\d+)\s*\)\s*$", gname)
            nm, declared = ((m.group(1).strip(), int(m.group(2))) if m else (gname, None))
            if gaddr in seen_addr:
                cur = seen_addr[gaddr]
            else:
                cur = {"name": (nm or gaddr.split("@")[0])[:60], "address": gaddr, "declared": declared, "members": [], "_seen": set()}
                seen_addr[gaddr] = cur
                groups.append(cur)
        if cur is None:
            continue
        if uaddr:
            if not _ADDR_RE.fullmatch(uaddr):
                out["warnings"].append("%d번째 줄: 사람 주소가 올바르지 않아 건너뜀 (%s)" % (ln, cur["name"][:30]))
                continue
            if uaddr not in cur["_seen"] and len(cur["members"]) < 2000:
                cur["_seen"].add(uaddr)
                cur["members"].append({"name": uname[:60], "email": uaddr})
    for g in groups:
        g.pop("_seen", None)
        if g["declared"] is not None and g["declared"] != len(g["members"]):
            out["warnings"].append("「%s」: 파일에 적힌 계정수 %d · 읽은 사람 %d" % (g["name"], g["declared"], len(g["members"])))
    out["groups"] = [g for g in groups if g["members"]]
    if len(out["groups"]) > 500:
        out["error"] = "그룹이 너무 많습니다(500개까지)."
    if not out["groups"] and not out["error"]:
        out["error"] = "읽은 그룹이 없습니다."
    return out


def _ensure_src(c):
    try:
        c.execute("ALTER TABLE mail_groups ADD COLUMN src TEXT")
    except Exception:
        pass


def import_plan(c, groups):
    """미리 보기 — 지금 등록된 회사 그룹 메일과 비교."""
    ensure(c)
    _ensure_src(c)
    now = {}
    for r in c.execute("SELECT * FROM mail_groups WHERE kind='company'").fetchall():
        d = _grp_row(c, r)
        now[d["address"]] = d
    plan = {"new": [], "changed": [], "same": 0, "missing": [], "people": 0}
    names = _staff_by_email(c, [m["email"] for g in groups for m in g["members"]])

    def disp(m):
        return (names.get(m["email"]) or {}).get("name") or m.get("name") or m["email"]
    faddr = set()
    for g in groups:
        faddr.add(g["address"])
        plan["people"] += len(g["members"])
        old = now.get(g["address"])
        if not old:
            plan["new"].append({"name": g["name"], "address": g["address"], "n": len(g["members"])})
            continue
        oe = {m.get("email") for m in old["members"]}
        ne = {m["email"] for m in g["members"]}
        add = [disp(m) for m in g["members"] if m["email"] not in oe]
        rem = [(m.get("name") or m.get("email")) for m in old["members"] if m.get("email") not in ne]
        if add or rem or old["name"] != g["name"]:
            plan["changed"].append({"name": g["name"], "old_name": old["name"], "address": g["address"], "n": len(ne), "add": add, "rem": rem})
        else:
            plan["same"] += 1
    for a, d in now.items():
        if a not in faddr:
            plan["missing"].append({"name": d["name"], "address": a, "n": d["n"], "from_file": (d.get("src") == "file")})
    return plan


def import_apply(c, uid, groups, *, remove_missing=True, filename="", who=""):
    """반영 — 파일에 있는 그룹은 명단을 파일대로(직원은 웍스 이름) · 파일에 없는 그룹은 「파일로 올린 것」만 지움(손으로 등록한 것은 남김).
    끝나면 원본↔저장 대조(대표규정: 엑셀 올리기 = 원본과 저장 전 항목 대조)."""
    ensure(c)
    _ensure_src(c)
    st = _staff_by_email(c, [m["email"] for g in groups for m in g["members"]])
    res = {"added": 0, "updated": 0, "same": 0, "removed": 0, "kept": 0}
    plan = import_plan(c, groups)
    same_addr = {g["address"] for g in groups} - {x["address"] for x in plan["new"]} - {x["address"] for x in plan["changed"]}
    for g in groups:
        mem = []
        for m in g["members"]:
            s = st.get(m["email"])
            d = {"name": (s or {}).get("name") or m.get("name") or "", "email": m["email"]}
            if s:
                d["staff"] = 1
            mem.append(d)
        js = json.dumps(mem, ensure_ascii=False)
        r = c.execute("SELECT id FROM mail_groups WHERE kind='company' AND address=?", (g["address"],)).fetchone()
        if r:
            c.execute("UPDATE mail_groups SET name=?, members=?, src='file', updated_at=datetime('now','localtime'), updated_by=? WHERE id=?",
                      (g["name"], js, uid, r["id"]))
            res["same" if g["address"] in same_addr else "updated"] += 1
        else:
            c.execute("INSERT INTO mail_groups(kind, owner_id, name, address, members, note, updated_by, src) VALUES('company', NULL, ?, ?, ?, '', ?, 'file')",
                      (g["name"], g["address"], js, uid))
            res["added"] += 1
    for x in plan["missing"]:
        if remove_missing and x["from_file"]:
            c.execute("DELETE FROM mail_groups WHERE kind='company' AND address=?", (x["address"],))
            res["removed"] += 1
        else:
            res["kept"] += 1
    stored = {d["address"]: {m.get("email") for m in d["members"]} for d in
              (_grp_row(c, r) for r in c.execute("SELECT * FROM mail_groups WHERE kind='company'").fetchall())}
    bad = [g["name"] for g in groups if stored.get(g["address"]) != {m["email"] for m in g["members"]}]
    res["verify_ok"] = not bad
    res["verify_bad"] = bad[:20]
    res["groups"] = len(groups)
    res["people"] = sum(len(g["members"]) for g in groups)
    info = {"at": "", "by": who, "file": (filename or "")[:120], "groups": res["groups"], "people": res["people"], "ok": res["verify_ok"]}
    try:
        info["at"] = c.execute("SELECT datetime('now','localtime')").fetchone()[0]
        c.execute("INSERT INTO app_settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                  (_IMP_KEY, json.dumps(info, ensure_ascii=False)))
    except Exception:
        pass
    return res


def import_last(c):
    try:
        r = c.execute("SELECT value FROM app_settings WHERE key=?", (_IMP_KEY,)).fetchone()
        return json.loads(r[0]) if r and r[0] else {}
    except Exception:
        return {}
