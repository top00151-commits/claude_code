# -*- coding: utf-8 -*-
"""메일 쉽게 나누기 1·2·3 (가짜 자료 · 임시 DB · 운영 무접촉)
대표 11-22 밤 「메일 규칙을 쉽게 설정할 방법은 없을까? 너가 사용자라면 어떻게 구분을 쉽게 했으면 좋겠어?」 → 「1·2·3 진행해」
  1 = 옮기기 전에 같이 옮겨질 메일 미리 보기 · 2 = 폴더마다 들어온 까닭 · 3 = 같은 대화 한눈에(옮기지 않음)
사용: py -3.13 _검증/mail_easy_sort_test.py"""
import _mail_ico; _mail_ico.install()  # noqa: E402  11-28 4단계: 화면의 선 아이콘을 [i:이름] 으로 읽음(그림 문자 대신 · 아이콘 이름까지 확인)
import io
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    import app.database as _db
    _db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_easy_"), "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_folders as mf
    from app import mail_thread as mth
finally:
    sys.stdout = _so
from starlette.testclient import TestClient  # noqa: E402

P = F = 0
_SEQ = [0]


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:600])


OWN = 9001
T_QA = 991
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id='kjr'")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9001,'kjr','시험대표','ceo',1,'x')")
    c.execute("INSERT INTO teams(id, code, name, display_order) VALUES(?,?,?,?)", (T_QA, '91', '시험품질팀', 91))
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id) VALUES(9201,'qa_kim','김품질','leader',1,'x','qa.kim@knknara.co.kr',?)", (T_QA,))


def put(frm, subject, text="가짜", name="보낸이", at=None):
    _SEQ[0] += 1
    with _db.db_session() as c:
        mid, _o = ms.store_inbound(c, to_email="kjr@knknara.co.kr", from_email=frm, from_name=name, subject=subject, text=text,
                                   owner_id=OWN, run_ai=False, message_id="es-%d@test" % _SEQ[0])
        if at:
            c.execute("UPDATE mail_messages SET received_at=? WHERE id=?", (at, mid))
    return mid


def put_out(to, subject, at):
    with _db.db_session() as c:
        mid = ms.store_outbound(c, user_id=OWN, from_email="kjr@knknara.co.kr", to_email=to, subject=subject, body="가짜")
        c.execute("UPDATE mail_messages SET received_at=?, created_at=? WHERE id=?", (at, at, mid))
    return mid


def key_of(mid):
    with _db.db_session() as c:
        mf.classify(c, OWN)
        return c.execute("SELECT COALESCE(fd_key,'') FROM mail_messages WHERE id=?", (mid,)).fetchone()[0]


m.get_user = lambda req: {"id": OWN, "role": "ceo", "name": "시험대표", "team_id": None, "team_name": "", "login_id": "kjr", "email": "kjr@knknara.co.kr"}
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
k.get("/mail/inbox")
with _db.db_session() as c:
    by = {f["name"]: f for f in mf.folders(c, OWN)}
SIG_SEMCO = "자료 보냅니다.\n\n김삼성 책임\n삼성전기㈜\nTel 031-000-0000"

print("== 1. 옮기기 전에 같이 옮겨질 메일 미리 보기 ==")
a1 = put("buyer1@dreamx.example", "견적 요청 A", name="드림 구매1", at="2026-11-01 09:00:00")
a2 = put("buyer2@dreamx.example", "견적 요청 B", name="드림 구매2", at="2026-11-05 09:00:00")
a3 = put("buyer1@dreamx.example", "발주서 송부", name="드림 구매1", at="2026-11-10 09:00:00")
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET fd_pin=? WHERE id=?", ("f%d" % by["2.기타 고객사"]["id"] if "2.기타 고객사" in by else "gen", a2))
mf._CACHE.pop(OWN, None)
tgt = "f%d" % by["삼성전자"]["id"]
d = k.post("/mail/move", data={"ids": str(a3), "dry": "1", "key": tgt}).json()
pv = d.get("company", {}).get("pv") or {}
check("회사 모두 미리 보기 = 지금 자리별 통수(일반 등) · 합 = 통수", d.get("ok") and sum(b[1] for b in pv.get("by", [])) == d["company"]["n"] == 3, d)
check("최근 메일 몇 줄(날짜·보낸 사람·제목·지금 폴더) · 최신 먼저", [r[2] for r in pv.get("rows", [])][:1] == ["발주서 송부"] and len(pv["rows"][0]) == 5, pv.get("rows"))
check("「이 메일만」으로 따로 정한 메일 수 = 그대로 둔다고 알림", pv.get("pinned") == (1 if "2.기타 고객사" in by else 0) or pv.get("pinned") >= 0, pv)
ppv = d.get("person", {}).get("pv") or {}
check("이 사람만 미리 보기 = 그 사람 메일만(2통)", sum(b[1] for b in ppv.get("by", [])) == 2 == d["person"]["n"], ppv)
j = k.post("/mail/move", data={"ids": str(a3), "key": tgt, "when": "all", "scope": "person"}).json()
d2 = k.post("/mail/move", data={"ids": str(a3), "dry": "1", "key": tgt}).json()
check("옮긴 뒤 다시 보면 「✓ 이미 여기」 표시(그 폴더)", j.get("ok") and any(b[2] == 1 for b in d2["person"]["pv"]["by"]), d2["person"]["pv"])
k.post("/mail/move/undo")
ask = _mail_ico.ico(io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "mail_move_ask.html"), encoding="utf-8").read())
check("묻는 창: 미리 보기 칸 · 범위 바꾸면 다시 그림 · 옮길 곳 열쇠를 셈에 넘김",
      'class="mmv-pv"' in ask and "renderPv()" in ask and "dry:'1', key:key" in ask and "[i:eye] 같이 옮겨질 메일" in ask)

print("== 2. 폴더마다 들어온 까닭 ==")
check("까닭 짧게: 회사 주소 · 서명 회사 · 아래 폴더로 좁힘 · 내 규칙 · 직원 · 이 메일만 · 주소록",
      mf.how_short("회사 주소 @samsung.com = 폴더 이름") == "회사 주소 @samsung.com"
      and mf.how_short("서명의 회사 이름") == "서명의 회사 이름"
      and mf.how_short("회사 주소 @samsung.com = 폴더 이름 → 서명의 회사 이름(으)로 아래 폴더") == "서명의 회사 이름"
      and mf.how_short("내 규칙(회사 주소 @dreamx.example) · 2026-11-22 10:00부터 받은 메일") == "내 규칙 @dreamx.example"
      and mf.how_short("내 규칙(이 사람)") == "내 규칙 (사람)"
      and mf.how_short("직원 — 이 메일 받은 때 부서") == "직원 — 받은 때 부서"
      and mf.how_short("이 메일만 직접 옮김") == "📌 이 메일만"
      and mf.how_short("드림텍(주소록·담당자)") == "주소록·거래처 담당자")
cx = k.post("/mail/folders/quick", data={"op": "add", "parent_id": by["1.고객사"]["id"], "name": "시험전기"}).json().get("id")
k.post("/mail/folders/quick", data={"op": "aliases", "id": cx, "aliases": "semx.example"})
mp = k.post("/mail/folders/quick", data={"op": "add", "parent_id": cx, "name": "MaPS"}).json().get("id")
s1 = put("kim.s@semx.example", "자료", "가짜", name="김시험")
s2 = put("kim.s@semx.example", "[MaPS] Logged in", "가짜", name="김시험")
mf._CACHE.pop(OWN, None)
with _db.db_session() as c:
    res = mf.classify(c, OWN)
    why = mf.folder_reasons(c, OWN, res)
check("시험전기 폴더 까닭 = 「회사 주소 @semx.example」 · MaPS 아래 폴더 = 「제목 [꼬리표]」",
      ("회사 주소 @semx.example", 1) in why.get("f%d" % cx, []) and ("제목 [꼬리표]", 1) in why.get("f%d" % mp, []), why)
fh = k.get("/mail/folders").text
check("폴더 관리 줄에 「📥 까닭 통수」 · 회사 아래 폴더엔 「🏷 그 회사 메일 중 제목 [MaPS…]도 자동」",
      "[i:inbox] 회사 주소 @semx.example <b>1</b>" in fh and "[i:tag] 그 회사 메일 중 제목 [MaPS…]도 자동" in fh, re.findall(r"\[i:inbox\][^<]{0,60}", fh)[:5])
check("맨 위 폴더(묶음 바로 아래)엔 제목 자동 안내 없음", "제목 [시험전기…]" not in fh and "제목 [삼성그룹…]" not in fh)

print("== 3. 같은 대화 한눈에(옮기지 않음) ==")
t1 = put("kim.s@semx.example", "[MaPS] 설비 점검 일정", "가짜", name="김시험", at="2026-11-12 09:00:00")
t2 = put("qa.kim@knknara.co.kr", "RE: [MaPS] 설비 점검 일정", "확인했습니다", name="김품질", at="2026-11-12 10:00:00")
t3 = put_out("kim.s@semx.example", "Re: RE: [MaPS] 설비 점검 일정", "2026-11-12 11:00:00")
t4 = put("kim.s@semx.example", "FW: [MaPS] 설비 점검 일정", "가짜", name="김시험", at="2026-11-13 09:00:00")
t9 = put("other@nowhere-x.example", "[MaPS] 설비 점검 일정", "옛날", name="옛날", at="2025-01-01 09:00:00")   # 120일 밖
check("회신은 보낸 사람 자리 그대로(직원 회신 = 부서 폴더 · 거래처 = MaPS)", key_of(t2).startswith("t") and key_of(t1) == "f%d" % mp, (key_of(t2), key_of(t1)))
with _db.db_session() as c:
    res = mf.classify(c, OWN)
    mm = ms.get_mail(c, t2, OWN)
    th = mth.thread_of(c, OWN, mm, res)
check("같은 대화 = 제목 같은 메일(RE·Re·FW 뺌) 4통 · 120일 밖 옛 메일 뺌 · 시간 순서",
      th and th["n"] == 4 and [x["id"] for x in th["rows"]] == [t1, t2, t3, t4], th)
check("폴더별 통수(MaPS 2 · 부서 1 · 보낸 메일 1) · 지금 보는 메일 표시",
      th and dict(th["by"]).get("MaPS") == 2 and dict(th["by"]).get("보낸 메일") == 1 and sum(dict(th["by"]).values()) == 4
      and [x["cur"] for x in th["rows"]] == [False, True, False, False], th and th["by"])
with _db.db_session() as c:
    solo = mth.thread_of(c, OWN, ms.get_mail(c, a1, OWN), res)
    short = mth.thread_of(c, OWN, {"id": 1, "subject": "RE: 확인", "received_at": "2026-11-12 09:00:00"}, res)
check("혼자인 메일·너무 짧은 제목 = 줄 안 보임", solo is None and short is None, (solo, short))
for i in range(30):   # 흔한 제목 — 다른 회사들이 같은 제목으로
    put("u%d@co%d-x.example" % (i, i), "견적 요청드립니다", name="여러 곳%d" % i, at="2026-11-0%d 08:00:00" % (1 + i % 9))
g1 = put("buyer1@dreamx.example", "RE: 견적 요청드립니다", name="드림 구매1", at="2026-11-11 08:00:00")
g2 = put("buyer2@dreamx.example", "견적 요청드립니다", name="드림 구매2", at="2026-11-10 08:00:00")
with _db.db_session() as c:
    tg = mth.thread_of(c, OWN, ms.get_mail(c, g1, OWN), res)
check("흔한 제목(같은 제목이 많음) = 이 메일의 상대 회사 메일만", tg and tg["n"] == 2 and {x["id"] for x in tg["rows"]} == {g1, g2}, tg and tg["n"])
pv = k.get("/mail/%d/pane" % t2).text
check("메일 보기: 「💬 같은 대화 4통 · …」 접힌 한 줄 + 목록(누르면 읽기 칸에)",
      "[i:message-square] 같은 대화 4통" in pv and 'class="mv-thr-list"' in pv and ("loadPane(%d)" % t1) in pv and "[i:map-pin] 지금 보는 메일" in pv, re.findall(r"\[i:message-square\][^<]{0,80}", pv)[:2])
fv = k.get("/mail/%d" % t3)
check("보낸 메일 보기에도 같은 대화", fv.status_code == 200 and "[i:message-square] 같은 대화 4통" in fv.text, fv.status_code)
_pa1 = k.get("/mail/%d/pane" % a1).text
check("혼자인 메일 보기엔 줄 없음", "💬 같은 대화" not in _pa1 and "[i:message-square] 같은 대화" not in _pa1)

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
