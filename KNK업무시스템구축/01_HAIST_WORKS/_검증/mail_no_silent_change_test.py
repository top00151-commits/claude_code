# -*- coding: utf-8 -*-
"""메일 — 사용자가 고르지 않은 자료는 저절로 바꾸지 않는다(대표 규정 knk-no-silent-change · 11-25) 시험.
가짜 직원·가짜 메일·임시 DB(운영 무접촉 · 실제 메일 없음).
① 「📁 이 폴더로」 예전 길·일반 정리 = 언제부터 꼭 · 먼저 셈 · ↺ 되돌리기
② 규칙 소급 적용 = 먼저 셈 · 되돌림 표 · 되돌리기
③ 새 폴더 만들며 옮기기 · 알림·광고 일괄 = 먼저 셈 · 되돌리기(새로 만든 폴더도)
④ 화면 열기만으로 옛 메일 「받은 때 부서」 저장 안 함 · 대표 폴더 「다른 이름」 채우기 한 번만
⑤ 직원 폴더 다시 만들기 되돌리기
⑥ 답 기다림 = 「답 옴(자동)」 이력 · 「아직 아님」 · 그 짝은 다시 안 붙음
⑦ 회사 전체 차단 = 미리 「직원 N명 · M통」(안 바꿈) · 확인 뒤 옮김 · 풀면 되돌림
사용: py -3.13 _검증/mail_no_silent_change_test.py"""
import io
import os
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
    _TMP = tempfile.mkdtemp(prefix="knk_mnsc_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_folders as mf
    from app import mail_work as mw
finally:
    sys.stdout = _so
from starlette.testclient import TestClient  # noqa: E402

P = F = 0


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:500])


OWN, ST, ST2 = 9601, 9602, 9603
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id='kjr'")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9601,'kjr','시험대표','ceo',1,'x')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9602,'t9602','시험직원','member',1,'x')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9603,'t9603','시험직원둘','member',1,'x')")
    c.execute("INSERT INTO teams(id, code, name, display_order) VALUES(961,'61','시험영업팀',61)")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id) VALUES(9611,'st_q','가직원','member',1,'x','q1@knknara.co.kr',961)")
    mw.ensure(c)
    ms._ensure_security_cols(c)

_SEQ = [0]


def put(frm, subject, owner=OWN, ago=1000, direction="in", to=""):
    _SEQ[0] += 1
    with _db.db_session() as c:
        if direction == "in":
            mid, _o = ms.store_inbound(c, to_email="t%d@knknara.co.kr" % owner, from_email=frm, from_name="보낸이",
                                       subject=subject, text="가짜 본문 %d" % _SEQ[0], owner_id=owner, run_ai=False,
                                       message_id="nsc-%d@test" % _SEQ[0])
        else:
            mid = c.execute("INSERT INTO mail_messages(user_id, direction, from_email, to_email, subject, body_text, is_read, is_deleted) "
                            "VALUES(?,?,?,?,?,?,1,0)", (owner, "out", "t%d@knknara.co.kr" % owner, to, subject, "가짜")).lastrowid
        c.execute("UPDATE mail_messages SET received_at=datetime('now','localtime', ?), is_read=1 WHERE id=?", ("-%d minutes" % ago, mid))
    return mid


def row(mid):
    with _db.db_session() as c:
        return dict(c.execute("SELECT id, fd_pin, fd_key, fd_team, category, is_blocked, wait_state, wait_reply_id FROM mail_messages WHERE id=?",
                              (mid,)).fetchone())


def rules_of(uid):
    with _db.db_session() as c:
        mf.ensure(c)
        return [dict(r) for r in c.execute("SELECT kind, pattern, target, COALESCE(since,'') AS since FROM mail_move_rules WHERE user_id=?",
                                           (uid,)).fetchall()]


_U = {"v": {"id": OWN, "role": "ceo", "name": "시험대표", "team_id": None, "team_name": ""}}
m.get_user = lambda req: _U["v"]
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})

# 메일 · 폴더 준비
a1 = put("a@acme-x.example", "견적 1", ago=3000)
a2 = put("b@acme-x.example", "견적 2", ago=2000)
a3 = put("c@acme-x.example", "견적 3", ago=1000)
z1 = put("z@zeta-x.example", "다른 회사", ago=900)
with _db.db_session() as c:
    mf.seed_if_owner(c, OWN)
    fl = mf.folders(c, OWN)
    g1 = [f for f in fl if f["name"] == "2.기타 고객사"][0]["id"]
    tgt = mf.add_folder(c, OWN, "에이크미", g1)

print("== ① 「📁 이 폴더로」 예전 길 · 일반 정리 ==")
before = rules_of(OWN)
j = k.post("/mail/%d/folder" % a1, data={"folder_id": tgt, "dry": "1"}).json()
check("셈만(dry) = 몇 통인지만 · 규칙 안 생김", j.get("ok") and j.get("dry") and j.get("count") == 3 and rules_of(OWN) == before, j)
r0 = k.post("/mail/%d/folder" % a1, data={"folder_id": tgt})
check("언제부터 안 고르면 안 바꿈(400 · need_when)", r0.status_code == 400 and r0.json().get("need_when") and rules_of(OWN) == before, r0.text[:200])
j = k.post("/mail/%d/folder" % a1, data={"folder_id": tgt, "when": "new"}).json()
rs = [r for r in rules_of(OWN) if r["pattern"] == "acme-x.example"]
check("「지금부터」 = 규칙에 시작 시각(지난 메일은 그대로)", j.get("ok") and j.get("when") == "new" and rs and rs[0]["since"] != "", (j, rs))
with _db.db_session() as c:
    res = mf.classify(c, OWN)
check("지금부터만 → 지난 메일 3통은 옮겨지지 않음", row(a2)["fd_key"] != "f%d" % tgt and row(a3)["fd_key"] != "f%d" % tgt, (row(a2), row(a3)))
u = k.post("/mail/move/undo").json()
check("↺ 되돌리기 = 규칙 사라짐", u.get("ok") and not [r for r in rules_of(OWN) if r["pattern"] == "acme-x.example"], (u, rules_of(OWN)))
j = k.post("/mail/folders/rule", data={"sender": "a@acme-x.example", "folder_id": tgt, "when": "all", "batch": "b1"}).json()
j2 = k.post("/mail/folders/rule", data={"sender": "z@zeta-x.example", "folder_id": tgt, "when": "all", "batch": "b1"}).json()
with _db.db_session() as c:
    mf.classify(c, OWN)
check("일반 정리 「지난 메일도」 = 그 회사 메일 모두 그 폴더로", j.get("ok") and j2.get("ok") and row(a2)["fd_key"] == "f%d" % tgt and row(z1)["fd_key"] == "f%d" % tgt,
      (j, row(a2), row(z1)))
u = k.post("/mail/move/undo").json()
with _db.db_session() as c:
    mf.classify(c, OWN)
check("여러 줄을 한 묶음(batch)으로 옮긴 것도 ↺ 한 번에 되돌림", u.get("ok") and row(a2)["fd_key"] != "f%d" % tgt and row(z1)["fd_key"] != "f%d" % tgt,
      (row(a2), row(z1)))
r0 = k.post("/mail/folders/rule", data={"sender": "a@acme-x.example", "folder_id": tgt})
check("일반 정리도 언제부터 없이 보내면 안 바꿈", r0.status_code == 400 and not [r for r in rules_of(OWN) if r["pattern"] == "acme-x.example"])
h = k.get("/mail/folders/general").text
check("일반 정리 화면 = 언제부터 묻는 창(지난 메일도 / 지금부터) · 완료 문구 · ↺", "언제부터 옮길까요?" in h and "지금부터 오는 메일만" in h and "완료 — 이 작업은 끝났습니다" in h and "gnUndo" in h)

print("== ② 규칙 소급 적용 ==")
with _db.db_session() as c:
    ms.add_rule(c, OWN, "domain", "acme-x.example", "발주")
    cats = {x: row(x)["category"] for x in (a1, a2, a3, z1)}
j = k.post("/mail/rules/apply", data={"dry": "1"}).json()
check("셈만 = 바뀔 통수만 · 분류 그대로", j.get("ok") and j.get("count") == 3 and {x: row(x)["category"] for x in (a1, a2, a3, z1)} == cats, j)
j = k.post("/mail/rules/apply").json()
check("적용 = 3통 바뀜 · 다른 회사 메일 그대로", j.get("changed") == 3 and row(a1)["category"] == "발주" and row(z1)["category"] == cats[z1], j)
u = k.post("/mail/rules/apply", data={"undo": "1"}).json()
check("↺ 되돌리기 = 예전 분류 그대로", u.get("ok") and u.get("undone") == 3 and {x: row(x)["category"] for x in (a1, a2, a3, z1)} == cats, u)
hr = k.get("/mail/rules").text
check("규칙 화면 = 먼저 「N통이 바뀝니다」 묻고 · 되돌리기", "통의 분류가 규칙대로 바뀝니다" in hr and "undo:'1'" in hr)

print("== ③ 새 폴더 만들며 옮기기 · 알림·광고 일괄 ==")
with _db.db_session() as c:
    nf0 = len(mf.folders(c, OWN))
j = k.post("/mail/folders/general/new", data={"sender": "z@zeta-x.example", "name": "제타", "parent_id": g1, "dry": "1"}).json()
with _db.db_session() as c:
    nf1 = len(mf.folders(c, OWN))
check("새 폴더 셈만 = 통수만 · 폴더 안 만듦", j.get("ok") and j.get("count") == 1 and nf1 == nf0, (j, nf0, nf1))
r0 = k.post("/mail/folders/general/new", data={"sender": "z@zeta-x.example", "name": "제타", "parent_id": g1, "when": "x"})
check("새 폴더도 언제부터 없으면 안 만듦", r0.status_code == 400)
j = k.post("/mail/folders/general/new", data={"sender": "z@zeta-x.example", "name": "제타", "parent_id": g1, "when": "all"}).json()
with _db.db_session() as c:
    made = [f for f in mf.folders(c, OWN) if f["name"] == "제타"]
check("확인 뒤 = 새 폴더 · 옮김", j.get("ok") and j.get("made") and made, j)
u = k.post("/mail/move/undo").json()
with _db.db_session() as c:
    gone = not [f for f in mf.folders(c, OWN) if f["name"] == "제타"]
check("↺ 되돌리기 = 규칙 + 새로 만든 폴더도 지움", u.get("ok") and gone and not [r for r in rules_of(OWN) if r["pattern"] in ("zeta-x.example", "z@zeta-x.example")], u)
rb = put("noreply@shop-x.example", "광고 메일", ago=500)
with _db.db_session() as c:
    nf0 = len(mf.folders(c, OWN))
    r0 = rules_of(OWN)
j = k.post("/mail/folders/general/robots", data={"dry": "1"})
jj = j.json() if j.status_code == 200 else {}
with _db.db_session() as c:
    nf1 = len(mf.folders(c, OWN))
check("알림·광고 셈만 = 곳·통수만 · 폴더·규칙 안 바뀜", (j.status_code == 400) or (jj.get("dry") and nf1 == nf0 and rules_of(OWN) == r0), j.text[:200])

print("== ④ 화면 열기만으로 저장 안 함 ==")
q = put("q1@knknara.co.kr", "사내 메일", ago=300)
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET fd_team=NULL WHERE id=?", (q,))
    mf._CACHE.pop(OWN, None)
    mf.classify(c, OWN)
check("옛 메일 「받은 때 부서」 = 화면 열 때 저장 안 함(보여 주기만)", row(q)["fd_team"] is None, row(q))
with _db.db_session() as c:
    c.execute("UPDATE mail_folders SET aliases=NULL WHERE user_id=? AND name='삼성전기'", (OWN,))
    mf.seed_if_owner(c, OWN)
    al = c.execute("SELECT aliases FROM mail_folders WHERE user_id=? AND name='삼성전기'", (OWN,)).fetchone()
check("대표 폴더 「다른 이름」 빈칸 = 한 번 채운 뒤에는 화면 열 때 다시 안 채움", (al is None) or (al["aliases"] is None), dict(al) if al else None)

print("== ⑤ 직원 폴더 다시 만들기 되돌리기 ==")
with _db.db_session() as c:
    mf.seed(c, ST)
    mf.add_folder(c, ST, "내가 만든 폴더", None, "")
    before_st = sorted((f["id"], f["name"]) for f in mf.folders(c, ST))
j = k.post("/mail/folders/reset-staff", data={"name": "시험직원"}).json()
with _db.db_session() as c:
    mid_st = sorted(f["name"] for f in mf.folders(c, ST))
check("다시 만들기 = 케이엔케이 하나", j.get("ok") and mid_st == ["케이엔케이"], (j, mid_st))
u = k.post("/mail/folders/reset-staff", data={"name": "시험직원", "undo": "1"}).json()
with _db.db_session() as c:
    after_st = sorted((f["id"], f["name"]) for f in mf.folders(c, ST))
check("↺ 되돌리기 = 예전 폴더 그대로(같은 번호 · 내가 만든 폴더 포함)", u.get("ok") and after_st == before_st, (u, len(before_st), len(after_st)))
check("되돌릴 것 없으면 400", k.post("/mail/folders/reset-staff", data={"name": "시험직원", "undo": "1"}).status_code == 400)

print("== ⑥ 답 기다림 「답 옴(자동)」·「아직 아님」 ==")
o1 = put("", "주문 문의", direction="out", to="buyer@client-x.example", ago=800)
with _db.db_session() as c:
    mw.ensure(c)
    c.execute("UPDATE mail_messages SET wait_state='wait', wait_until='2099-01-01' WHERE id=?", (o1,))
rp1 = put("buyer@client-x.example", "RE: 주문 문의", ago=700)
rp2 = put("buyer2@client-x.example", "RE: 주문 문의", ago=600)
with _db.db_session() as c:
    mw.list_waiting(c, OWN, "2026-11-25", ms._normalize_subject)
    lg = [dict(x) for x in c.execute("SELECT mail_id, reply_id, undone_at FROM mail_wait_auto_log WHERE mail_id=?", (o1,)).fetchall()]
check("답이 오면 저절로 「답 옴」 + 이력 남음", row(o1)["wait_state"] == "replied" and row(o1)["wait_reply_id"] == rp1 and lg and lg[0]["reply_id"] == rp1, (row(o1), lg))
hv = k.get("/mail/%d" % o1).text
check("메일 화면 = 「답 옴(자동)」 + 「아직 아님」", "답 옴(자동)" in hv and "아직 아님" in hv)
hw = k.get("/mail/waiting?all=1").text
check("답 기다림 목록 = 「답 옴(자동)」 + 「아직 아님」", "답 옴(자동)" in hw and "wtNotYet" in hw)
j = k.post("/mail/%d/wait-notyet" % o1).json()
check("「아직 아님」 = 다시 답 기다림", j.get("ok") and row(o1)["wait_state"] == "wait" and row(o1)["wait_reply_id"] is None, (j, row(o1)))
with _db.db_session() as c:
    mw.list_waiting(c, OWN, "2026-11-25", ms._normalize_subject)
check("그 짝(첫 답)은 다시 안 붙음 · 다른 답이 있으면 그것으로", row(o1)["wait_reply_id"] != rp1, row(o1))
check("「아직 아님」 = 자동 답 옴이 아닌 메일엔 400", k.post("/mail/%d/wait-notyet" % a1).status_code == 400)

print("== ⑦ 회사 전체 차단 ==")
b1 = put("spam@bad-x.example", "나쁜 메일 1", owner=OWN, ago=400)
b2 = put("spam@bad-x.example", "나쁜 메일 2", owner=ST, ago=390)
b3 = put("spam@bad-x.example", "나쁜 메일 3", owner=ST2, ago=380)
j = k.post("/mail/blocklist/add", data={"pattern": "spam@bad-x.example", "kind": "email", "dry": "1"}).json()
with _db.db_session() as c:
    bl = c.execute("SELECT COUNT(*) FROM mail_blocklist").fetchone()[0]
check("미리 셈 = 직원 3명 · 3통 · 차단 목록·메일 그대로", j.get("dry") and j.get("users") == 3 and j.get("mails") == 3 and bl == 0
      and not row(b1)["is_blocked"] and not row(b2)["is_blocked"], (j, bl))
jp = k.post("/mail/%d/block-sender?dry=1" % b1).json()
check("메일 화면 차단도 미리 셈만(안 바꿈)", jp.get("dry") and jp.get("mails") == 3 and not row(b1)["is_blocked"], jp)
j = k.post("/mail/blocklist/add", data={"pattern": "spam@bad-x.example", "kind": "email"}).json()
check("확인 뒤 = 3통 스팸함으로", j.get("ok") and j.get("moved") == 3 and row(b1)["is_blocked"] and row(b3)["is_blocked"], j)
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET is_blocked=0 WHERE id=?", (b3,))   # 직원이 「스팸 아님」으로 스스로 꺼냄
    bid = c.execute("SELECT id FROM mail_blocklist WHERE pattern='spam@bad-x.example'").fetchone()[0]
j = k.post("/mail/blocklist/remove", data={"id": bid}).json()
check("차단 풀기 = 옮겼던 메일 원래 자리로(이미 꺼낸 것은 그대로)", j.get("ok") and j.get("restored") == 2 and not row(b1)["is_blocked"]
      and not row(b2)["is_blocked"] and not row(b3)["is_blocked"], j)
hb = k.get("/mail/blocklist").text
check("차단 화면 = 미리 「직원 N명 · M통」 · 풀면 원래 자리 안내", "dry:'1'" in hb and "원래 자리로 돌아갑니다" in hb)
_U["v"] = {"id": ST, "role": "member", "name": "시험직원", "team_id": None, "team_name": ""}
check("직원은 차단 미리 셈도 못 함(403)", k.post("/mail/blocklist/add", data={"pattern": "x@y-x.example", "dry": "1"}).status_code == 403)

print("결과: %d 통과 · %d 실패" % (P, F))
sys.exit(1 if F else 0)
