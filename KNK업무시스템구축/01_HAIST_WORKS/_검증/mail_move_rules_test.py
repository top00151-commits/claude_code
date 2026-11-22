# -*- coding: utf-8 -*-
"""메일 자동 분류 — 옮기면 그곳이 기준 · 지금부터만/지난 메일도 · 부서 폴더 · 부서 이동 · 삼성그룹 시험.
가짜 직원·가짜 거래처·가짜 메일·임시 DB(운영 무접촉 · 실제 메일 없음).
대표 지시 2026-11-22:
 「너가 자동분류한걸 내가 이동하면 이동한 위치가 우선 · 관련 메일들은 이동시킨 곳으로 모두 · 새로 들어오는 것도 자동 반영」
 「삼성은 삼성그룹으로 묶고 그 아래 삼성전자·삼성전기로 구분되는 건 구분 · 안 되면 삼성그룹」
 「우리 회사 부서에서 온 메일을 다른 부서로 옮기려 하면 부서 폴더가 안 보임(예: 품질팀 김정록 팀장)」
 「옮길 때 지금부터 발생한 메일에 적용할지 이전 메일도 적용할지 꼭 물어보고 선택 · 부서 이동은 바뀐 날부터 새 부서」
사용: py -3.13 _검증/mail_move_rules_test.py"""
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
    _TMP = tempfile.mkdtemp(prefix="knk_mmove_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_folders as mf
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


OWN, OTHER = 9001, 9002
T_QA, T_DES = 991, 992   # 가짜 품질팀 · 설계팀
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id='kjr'")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9001,'kjr','시험대표','ceo',1,'x')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9002,'t9002','시험이','member',1,'x')")
    c.execute("INSERT INTO teams(id, code, name, display_order) VALUES(?,?,?,?)", (T_QA, '91', '시험품질팀', 91))
    c.execute("INSERT INTO teams(id, code, name, display_order) VALUES(?,?,?,?)", (T_DES, '92', '시험설계팀', 92))
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id) VALUES(9201,'qa_kim','김품질','leader',1,'x','qa.kim@knknara.co.kr',?)", (T_QA,))
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id) VALUES(9202,'des_lee','이설계','member',1,'x','des.lee@knknara.co.kr',?)", (T_DES,))


def put(frm, subject, text, owner=OWN, name="보낸이", ago=None):
    """가짜 메일 하나 — ago='-3 days' 처럼 주면 그만큼 예전에 받은 메일."""
    _SEQ[0] += 1
    with _db.db_session() as c:
        mid, _o = ms.store_inbound(c, to_email="t%d@knknara.co.kr" % owner, from_email=frm, from_name=name,
                                   subject=subject, text=text, owner_id=owner, run_ai=False,
                                   message_id="mm-%d@test" % _SEQ[0])
        if ago:
            c.execute("UPDATE mail_messages SET received_at=datetime('now','localtime', ?) WHERE id=?", (ago, mid))
    return mid


def row(mid):
    with _db.db_session() as c:
        return dict(c.execute("SELECT id, COALESCE(fd_key,'') AS fd_key, COALESCE(fd_pin,'') AS fd_pin, fd_team FROM mail_messages WHERE id=?",
                              (mid,)).fetchone())


def cls():
    with _db.db_session() as c:
        return mf.classify(c, OWN)


def key_of(mid):
    cls()
    return row(mid)["fd_key"]


def fid(name):
    with _db.db_session() as c:
        return c.execute("SELECT id FROM mail_folders WHERE user_id=? AND name=?", (OWN, name)).fetchone()["id"]


_UID = {"v": OWN}
m.get_user = lambda req: ({"id": _UID["v"], "role": "member", "name": "시험", "team_id": None, "team_name": ""} if _UID["v"] else None)


def client(port=5051, host="works.knknara.co.kr"):
    k = TestClient(m.app, base_url="http://127.0.0.1:%d" % port, raise_server_exceptions=False, follow_redirects=False)
    k.headers.update({"host": host, "x-forwarded-proto": "https"})
    return k


SIG_SEMCO = "자료 보냅니다.\n\n감사합니다.\n\n김삼성 책임\n삼성전기㈜\nTel 031-000-0000"
SIG_SEC = "자료 보냅니다.\n\n감사합니다.\n\n이삼성 프로\n삼성전자㈜\nTel 031-000-0001"

try:
    k = client()
    k.get("/mail/inbox")   # 대표 계정 = 아웃룩 폴더 + 삼성그룹 생김

    print("== 1. 삼성그룹(3단계) ==")
    with _db.db_session() as c:
        fl = mf.folders(c, OWN)
    by = {f["name"]: f for f in fl}
    check("삼성그룹 = 1.고객사 아래 · 삼성전자·삼성전기 = 삼성그룹 아래 · 다른 이름에 samsung.com",
          by["삼성그룹"]["parent_id"] == by["1.고객사"]["id"] and by["삼성전자"]["parent_id"] == by["삼성그룹"]["id"]
          and by["삼성전기"]["parent_id"] == by["삼성그룹"]["id"] and "samsung.com" in by["삼성그룹"]["aliases"])
    s_semco = put("kim.s@samsung.com", "자료", SIG_SEMCO, name="김삼성")
    s_sec = put("lee.s@samsung.com", "자료", SIG_SEC, name="이삼성")
    s_unk = put("who.s@samsung.com", "안내", "누구인지 모름", name="Park")
    s_name = put("choi.s@partner.samsung.com", "견적", "견적입니다", name="최삼성/삼성전기")
    check("@samsung.com + 서명 삼성전기 → 삼성전기", key_of(s_semco) == "f%d" % by["삼성전기"]["id"], row(s_semco))
    check("@samsung.com + 서명 삼성전자 → 삼성전자", key_of(s_sec) == "f%d" % by["삼성전자"]["id"], row(s_sec))
    check("@samsung.com 구분 안 됨 → 삼성그룹", key_of(s_unk) == "f%d" % by["삼성그룹"]["id"], row(s_unk))
    check("하위 주소(@partner.samsung.com) + 보낸 사람 이름 「최삼성/삼성전기」 → 삼성전기", key_of(s_name) == "f%d" % by["삼성전기"]["id"], row(s_name))
    res = cls()
    check("왼쪽 나무: 1.고객사 › 삼성그룹 › 삼성전자·삼성전기(숫자 = 아래 폴더 합)",
          any(k2["name"] == "삼성그룹" and k2["n"] == 4 and sorted(x["name"] for x in k2.get("children", [])) == ["삼성전기", "삼성전자"]
              for g in res["nodes"] for k2 in g["children"]))
    check("삼성 주소 규칙 = 그 사람 한 명(여러 폴더가 나눠 쓰는 주소)", mf.rule_target("who.s@samsung.com", res) == ("email", "who.s@samsung.com"))
    h = k.get("/mail/inbox?fd=f%d" % by["삼성그룹"]["id"]).text
    check("삼성그룹을 누르면 아래 폴더 메일까지 4통", h.count('class="mbx-row') + h.count('class="mbx-headlink') >= 4 and all(('data-mail-id="%d"' % x) in h for x in (s_semco, s_sec, s_unk, s_name)))
    with _db.db_session() as c:
        n2 = mf.apply_seed_v2(c, OWN)
    check("삼성그룹 묶기는 한 번만(다시 불러도 안 만듦)", n2 == 0)

    print("== 2. 부서 폴더가 옮길 곳에 보임(품질팀 → 설계팀) ==")
    q1 = put("qa.kim@knknara.co.kr", "품질 보고 1", "보고", name="김품질", ago="-10 days")
    q2 = put("qa.kim@knknara.co.kr", "품질 보고 2", "보고", name="김품질", ago="-5 days")
    check("직원 메일 = 받은 때 부서 적음(받을 때) · 폴더 = 품질팀", row(q1)["fd_team"] == T_QA and key_of(q1) == "t%d" % T_QA, row(q1))
    pane = k.get("/mail/%d/pane" % q2).text
    check("읽기 칸 「📁 다른 폴더로…」에 우리 회사 부서(설계팀) · 묶음 이름은 고를 수 없음",
          ('value="t%d"' % T_DES) in pane and '<option value="" disabled>6.케이엔케이</option>' in pane, re.findall(r'<option value="t\d+"[^>]*>[^<]*', pane)[:6])
    hi = k.get("/mail/inbox").text
    check("여러 통 고르기 「📁」·이동 메뉴에도 부서 폴더(옮길 곳 목록)", ('<option value="t%d">' % T_DES) in hi and ('"key": "t%d"' % T_DES) in hi)

    print("== 3. 묻는 창 셈(dry) ==")
    d = k.post("/mail/move", data={"ids": str(q2), "dry": "1"}).json()
    check("우리 회사 주소 = 회사 범위도 그 사람(같음) · 지금 2통", d.get("ok") and d.get("same") is True and d["person"]["n"] == 2 and d["person"]["label"] == "qa.kim@knknara.co.kr", d)
    p1 = put("a@partner-x.example", "견적 1", "견적", ago="-20 days")
    p2 = put("b@partner-x.example", "견적 2", "견적", ago="-3 days")
    d2 = k.post("/mail/move", data={"ids": str(p2), "dry": "1"}).json()
    check("회사 주소 = 「회사 주소 @partner-x.example 모두(2통)」 / 「이 사람만(1통)」", d2.get("ok") and not d2["same"]
          and d2["company"]["label"] == "회사 주소 @partner-x.example" and d2["company"]["n"] == 2 and d2["person"]["n"] == 1, d2)
    check("언제부터 고르지 않으면 안 옮김(400)", k.post("/mail/move", data={"ids": str(p2), "key": "f%d" % by["드림텍"]["id"]}).status_code == 400)
    check("옮길 수 없는 곳(6.케이엔케이 묶음·없는 곳)은 400",
          k.post("/mail/move", data={"ids": str(p2), "key": "f%d" % by["6.케이엔케이"]["id"], "when": "all"}).status_code == 400
          and k.post("/mail/move", data={"ids": str(p2), "key": "f999999", "when": "all"}).status_code == 400)
    oth = put("a@partner-x.example", "남의 메일", "x", owner=OTHER)
    check("남의 메일은 못 옮김", k.post("/mail/move", data={"ids": str(oth), "key": "gen", "when": "all"}).status_code == 400)

    print("== 4. 지난 메일도 모두 ==")
    dream = by["드림텍"]["id"]
    j = k.post("/mail/move", data={"ids": str(p2), "key": "f%d" % dream, "when": "all", "scope": "company"}).json()
    check("회사 주소 모두 → 드림텍(지난 메일 2통)", j.get("ok") and j["in_target"] == 2 and key_of(p1) == "f%d" % dream and key_of(p2) == "f%d" % dream, j)
    p3 = put("c@partner-x.example", "새 사람 새 메일", "견적")
    check("새로 받는 메일(같은 회사 새 사람)도 드림텍", key_of(p3) == "f%d" % dream, row(p3))
    with _db.db_session() as c:
        rl = mf.rules(c, OWN)
    check("규칙 = 회사 주소 @partner-x.example → 드림텍 · 지난 메일도 모두", any(r["pattern"] == "partner-x.example" and r["since"] == "" and r["folder_name"] == "드림텍" for r in rl), rl)
    fh = k.get("/mail/folders").text
    check("폴더 관리 「내가 정한 규칙」에 「⏪ 지난 메일도 모두」", "⏪ 지난 메일도 모두" in fh)
    hl = k.get("/mail/inbox?fd=f%d" % dream).text
    check("드림텍 폴더 목록 = 3통 모두", all(('data-mail-id="%d"' % x) in hl for x in (p1, p2, p3)))

    print("== 5. 지금부터만 ==")
    sec = by["세경하이테크"]["id"]
    j = k.post("/mail/move", data={"ids": str(p3), "key": "f%d" % sec, "when": "new", "scope": "company"}).json()
    check("지금부터만 → 고른 메일은 세경하이테크 · 지난 메일 2통은 드림텍 그대로", j.get("ok") and key_of(p3) == "f%d" % sec
          and key_of(p1) == "f%d" % dream and key_of(p2) == "f%d" % dream and j["kept"] == 2, (j, row(p1), row(p3)))
    p4 = put("a@partner-x.example", "옮긴 뒤 새 메일", "견적")
    check("그 뒤 받은 메일 → 세경하이테크", key_of(p4) == "f%d" % sec, row(p4))
    with _db.db_session() as c:
        rl = [r for r in mf.rules(c, OWN) if r["pattern"] == "partner-x.example"]
    check("규칙 두 줄(기간마다) — 지난 메일 = 드림텍 · 그때부터 = 세경하이테크", len(rl) == 2 and {r["folder_name"] for r in rl} == {"드림텍", "세경하이테크"}
          and any(r["since"] for r in rl) and any(not r["since"] for r in rl), rl)
    check("폴더 관리 규칙에 「⏩ …부터 받은 메일」", "부터 받은 메일" in k.get("/mail/folders").text)
    vp = k.get("/mail/%d/pane" % p4).text
    check("읽기 칸 「📁 세경하이테크」 + 까닭 = 내 규칙 · …부터", "📁 세경하이테크" in vp and "부터 받은 메일" in vp)

    print("== 6. ↺ 되돌리기 ==")
    j = k.post("/mail/move/undo").json()
    check("마지막 옮기기 되돌림 → 그 뒤 메일도 다시 드림텍", j.get("ok") and key_of(p4) == "f%d" % dream and key_of(p3) == "f%d" % dream and row(p3)["fd_pin"] == "", (j, row(p3), row(p4)))
    check("한 번 되돌린 뒤 또 되돌리기 = 할 것 없음", not k.post("/mail/move/undo").json().get("ok"))

    print("== 7. 이 사람만 · 이 메일만 ==")
    j = k.post("/mail/move", data={"ids": str(p1), "key": "f%d" % sec, "when": "all", "scope": "person"}).json()
    check("이 사람만(지난 메일도) → a@ 만 세경하이테크 · 같은 회사 b@ 는 드림텍", j.get("ok") and key_of(p1) == "f%d" % sec and key_of(p4) == "f%d" % sec
          and key_of(p2) == "f%d" % dream, (j, row(p1), row(p2)))
    j = k.post("/mail/move", data={"ids": str(p2), "key": "gen", "when": "one"}).json()
    check("이 메일만 → 일반(고른 메일만 · 규칙 안 생김)", j.get("ok") and key_of(p2) == "gen" and row(p2)["fd_pin"] == "gen" and key_of(p3) == "f%d" % dream, (j, row(p2)))
    j = k.post("/mail/bulk", data={"op": "pin", "ids": str(p2), "folder_id": "0"}).json()
    check("「이 메일만」 옮김 풀기 → 규칙대로(드림텍)", j.get("ok") and key_of(p2) == "f%d" % dream, row(p2))

    print("== 8. 부서 이동(품질팀 → 설계팀) ==")
    # (가) 직원 명부에서 부서를 바꿈 → 그날부터 오는 메일만 새 부서
    with _db.db_session() as c:
        c.execute("UPDATE users SET team_id=? WHERE id=9201", (T_DES,))
    q3 = put("qa.kim@knknara.co.kr", "설계 보고(부서 옮긴 뒤)", "보고", name="김품질")
    check("부서 바꾼 뒤 받은 메일 = 설계팀", row(q3)["fd_team"] == T_DES and key_of(q3) == "t%d" % T_DES, row(q3))
    check("부서 바꾸기 전 메일 = 품질팀 그대로(지난 메일 안 따라감)", key_of(q1) == "t%d" % T_QA and key_of(q2) == "t%d" % T_QA, (row(q1), row(q2)))
    hq = k.get("/mail/inbox?fd=t%d" % T_QA).text
    hd = k.get("/mail/inbox?fd=t%d" % T_DES).text
    check("왼쪽 품질팀 = 예전 메일 · 설계팀 = 새 메일", ('data-mail-id="%d"' % q1) in hq and ('data-mail-id="%d"' % q3) not in hq and ('data-mail-id="%d"' % q3) in hd)
    # (나) 대표가 직접 옮김(부서 폴더로 · 지금부터만)
    with _db.db_session() as c:
        c.execute("UPDATE users SET team_id=? WHERE id=9201", (T_QA,))
    q4 = put("qa.kim@knknara.co.kr", "다시 품질", "보고", name="김품질")
    j = k.post("/mail/move", data={"ids": str(q4), "key": "t%d" % T_DES, "when": "new", "scope": "company"}).json()
    q5 = put("qa.kim@knknara.co.kr", "옮긴 뒤", "보고", name="김품질")
    check("직원 메일을 부서 폴더로 옮김(지금부터만) — 고른 메일·새 메일 = 설계팀 · 지난 메일 = 품질팀",
          j.get("ok") and key_of(q4) == "t%d" % T_DES and key_of(q5) == "t%d" % T_DES and key_of(q1) == "t%d" % T_QA, (j, row(q4), row(q5)))
    check("우리 회사 주소는 회사 범위여도 그 사람 한 명", j.get("label") == "qa.kim@knknara.co.kr", j)
    # (다) 처음 한 번은 지금 부서로 채움(받을 때 적지 못한 메일)
    with _db.db_session() as c:
        c.execute("UPDATE mail_messages SET fd_team=NULL, fd_key='' WHERE id=?", (q1,))
    mf._CACHE.pop(OWN, None)   # (손으로 칸을 비운 것이라 기억한 결과를 지움 — 실제로는 새 메일·읽음이 바뀌면 다시 셈)
    cls()
    check("받은 때 부서가 비어 있던 메일 = 폴더 열 때 지금 부서로 한 번 채움", row(q1)["fd_team"] == T_QA, row(q1))

    print("== 9. 숫자 = 목록 ==")
    res = cls()
    tot = {}
    for g in res["nodes"]:
        for x in [g] + g["children"] + [y for x2 in g["children"] for y in (x2.get("children") or [])]:
            tot[x["key"]] = x["n"]
    for key in ("t%d" % T_QA, "t%d" % T_DES, "f%d" % dream, "f%d" % by["삼성그룹"]["id"]):
        with _db.db_session() as c:
            n_list = ms.list_inbox(c, OWN, count_only=True, fd_keys=sorted(res["keys_of"][key]), senders=[])
        check("폴더 숫자 = 목록 통수(%s)" % res["labels"].get(key), tot.get(key) == n_list, (key, tot.get(key), n_list))
    with _db.db_session() as c:
        c.execute("UPDATE mail_messages SET is_deleted=1 WHERE id=?", (p1,))
    res = cls()
    n_s = [x["n"] for g in res["nodes"] for x in g["children"] if x["key"] == "f%d" % sec]
    with _db.db_session() as c:
        c.execute("UPDATE mail_messages SET is_deleted=0 WHERE id=?", (p1,))
    res = cls()
    n_s2 = [x["n"] for g in res["nodes"] for x in g["children"] if x["key"] == "f%d" % sec]
    check("지웠다 되살리면 숫자도 따라감", n_s and n_s2 and n_s2[0] == n_s[0] + 1, (n_s, n_s2))

    print("== 10. 폴더 관리 — 아래 폴더 · 위치 ==")
    k.post("/mail/folders/op", data={"op": "add", "name": "시험그룹", "parent_id": by["1.고객사"]["id"]})
    g2 = fid("시험그룹")
    k.post("/mail/folders/op", data={"op": "add", "name": "시험그룹-가", "parent_id": g2})
    with _db.db_session() as c:
        fl2 = {f["name"]: f for f in mf.folders(c, OWN)}
    check("폴더 아래에 아래 폴더 더하기(3단계)", fl2["시험그룹-가"]["parent_id"] == g2)
    k.post("/mail/folders/op", data={"op": "add", "name": "4단계", "parent_id": fl2["시험그룹-가"]["id"]})
    with _db.db_session() as c:
        check("4단계는 안 만듦", not any(f["name"] == "4단계" for f in mf.folders(c, OWN)))
    k.post("/mail/folders/op", data={"op": "parent", "id": by["파트론"]["id"], "parent_id": g2})
    with _db.db_session() as c:
        check("「위치」로 다른 폴더 아래로 옮김", c.execute("SELECT parent_id FROM mail_folders WHERE id=?", (by["파트론"]["id"],)).fetchone()[0] == g2)
    r = k.post("/mail/folders/op", data={"op": "parent", "id": by["삼성그룹"]["id"], "parent_id": g2})
    with _db.db_session() as c:
        check("아래 폴더가 있는 폴더(삼성그룹)는 다른 폴더 아래로 못 감", c.execute("SELECT parent_id FROM mail_folders WHERE id=?", (by["삼성그룹"]["id"],)).fetchone()[0] == by["1.고객사"]["id"])
    fh = k.get("/mail/folders").text
    check("폴더 관리 화면: 아래 폴더 줄(mf-row k k2) · 위치 고르기 · 넣을 곳 고르기", 'class="mf-row k k2"' in fh and 'value="parent"' in fh and "「1.고객사」 바로 아래" in fh)
    k.post("/mail/folders/op", data={"op": "delete", "id": g2})
    with _db.db_session() as c:
        names = {f["name"] for f in mf.folders(c, OWN)}
    check("폴더 지우기 = 아래 폴더까지(메일은 그대로)", "시험그룹" not in names and "시험그룹-가" not in names and "파트론" not in names)

    print("== 11. 옛 규칙 표 한 번 옮기기 ==")
    with _db.db_session() as c:
        c.execute("INSERT INTO mail_folder_rules(user_id, folder_id, kind, pattern) VALUES(?,?,?,?)", (OWN, dream, "domain", "old-rule.example"))
        c.execute("DELETE FROM mail_folder_flags WHERE user_id=0 AND flag='rules_v2'")
        mf._OK["v"] = False
        mf.ensure(c)
        got = c.execute("SELECT target, since FROM mail_move_rules WHERE user_id=? AND pattern='old-rule.example'", (OWN,)).fetchall()
        mf._OK["v"] = False
        mf.ensure(c)
        got2 = c.execute("SELECT COUNT(*) FROM mail_move_rules WHERE user_id=? AND pattern='old-rule.example'", (OWN,)).fetchone()[0]
    check("옛 규칙(폴더 번호) → 새 규칙(f…·지난 메일도) · 두 번 옮기지 않음", len(got) == 1 and got[0]["target"] == "f%d" % dream and got[0]["since"] == "" and got2 == 1, [dict(x) for x in got])

    print("== 12. 화면 글 ==")
    hi = k.get("/mail/inbox").text
    check("묻는 창: 「지금부터 오는 메일만」·「지난 메일도 모두」·「고른 메일 N통만」 · 미리 골라 두지 않음(단추 둘)",
          "⏩ 지금부터 오는 메일만" in hi and "⏪ 지난 메일도 모두" in hi and "통만 옮기기" in hi and "data-when=\"new\"" in hi and "data-when=\"all\"" in hi)
    check("묻는 창 = 오른쪽 위 ✕ · Esc · 바깥 누르면 닫힘(옮기지 않음)", 'class="x" title="닫기(옮기지 않음)"' in hi and "e.key==='Escape'" in hi)
    check("일반에도 놓을 수 있음", 'data-fkey="gen"' in hi)
    check("로그인 안 하면 401", (lambda: (_UID.__setitem__("v", None), k.post("/mail/move", data={"ids": "1"}).status_code)[1])() == 401)
    _UID["v"] = OWN
    km = client(port=5052, host="mail.knknara.co.kr")
    check("kmail 화면도 같은 묻는 창", "mailMoveAsk" in km.get("/mail/inbox").text)

    print("== 13. 일반 정리 — 「＋ 새 폴더로」 · 알림·광고 한 번에(11-22 대표 「일반에 많이 남은 곳 보강」) ==")
    n1 = put("kim@newcomp-x.example", "첫 연락", "자료입니다.\n\n감사합니다.\n\n김뉴컴 과장\n㈜뉴컴프테크\nTel 02-000-0000", name="김뉴컴", ago="-9 days")
    n2 = put("park@newcomp-x.example", "둘째 연락", "자료입니다.", name="박뉴컴", ago="-8 days")
    r1 = put("noreply@newcomp-x.example", "[알림] 주문 접수", "자동 발송", name="뉴컴프 알림", ago="-7 days")
    r2 = put("newsletter@shop-x.example", "이번 주 소식", "광고", name="쇼핑", ago="-6 days")
    gp = k.get("/mail/folders/general").text
    check("일반 정리: 「＋ 새 폴더로」 · 이름 = 서명의 회사 이름(㈜ 뺌) · 넣을 곳 기본 = 기타 고객사",
          "＋ 새 폴더로" in gp and 'value="뉴컴프테크"' in gp and ('value="%d" selected' % by["2.기타 고객사"]["id"]) in gp)
    check("일반 정리: 알림·광고 줄 표시 + 위에 「한 번에」 단추(곳·통수)", "📢 알림·광고" in gp and "gnRobots()" in gp and "2곳" in gp)
    j = k.post("/mail/folders/general/new", data={"sender": "kim@newcomp-x.example", "name": "뉴컴프테크", "parent_id": by["2.기타 고객사"]["id"]}).json()
    with _db.db_session() as c:
        nf = c.execute("SELECT id, parent_id FROM mail_folders WHERE user_id=? AND name='뉴컴프테크'", (OWN,)).fetchone()
    check("「만들고 옮기기」 = 기타 고객사 아래 새 폴더 · 그 회사 메일 모두(사람 2통 + 알림 1통 = 회사 주소)",
          j.get("ok") and j.get("made") and nf and nf["parent_id"] == by["2.기타 고객사"]["id"] and key_of(n1) == "f%d" % nf["id"] and key_of(n2) == "f%d" % nf["id"], j)
    n3 = put("lee@newcomp-x.example", "새 사람", "안녕하세요", name="이뉴컴")
    check("그 회사 새 메일도 새 폴더로", key_of(n3) == "f%d" % nf["id"], row(n3))
    j2 = k.post("/mail/folders/general/new", data={"sender": "kim@newcomp-x.example", "name": "뉴컴프테크", "parent_id": by["2.기타 고객사"]["id"]}).json()
    check("같은 자리 같은 이름이면 새로 안 만들고 그 폴더", j2.get("ok") and not j2.get("made") and j2.get("folder_id") == nf["id"], j2)
    check("넣을 곳이 6.케이엔케이 묶음이면 400 · 이름 없으면 400",
          k.post("/mail/folders/general/new", data={"sender": "kim@newcomp-x.example", "name": "x", "parent_id": by["6.케이엔케이"]["id"]}).status_code == 400
          and k.post("/mail/folders/general/new", data={"sender": "kim@newcomp-x.example", "name": " ", "parent_id": by["2.기타 고객사"]["id"]}).status_code == 400)
    check("내 메일에 없는 주소는 404", k.post("/mail/folders/general/new", data={"sender": "nobody@x.example", "name": "x", "parent_id": by["2.기타 고객사"]["id"]}).status_code == 404)
    jr = k.post("/mail/folders/general/robots").json()
    with _db.db_session() as c:
        rf = c.execute("SELECT id, parent_id FROM mail_folders WHERE user_id=? AND name=?", (OWN, mf.ROBOT_FOLDER)).fetchone()
        rk = [r_["kind"] for r_ in c.execute("SELECT kind FROM mail_move_rules WHERE user_id=? AND target=?", (OWN, "f%d" % rf["id"])).fetchall()] if rf else []
    check("알림·광고 한 번에 = 「알림·광고」 묶음(맨 위) · 일반에 남은 알림 주소만 · 규칙은 주소 하나씩",
          jr.get("ok") and rf and rf["parent_id"] is None and key_of(r2) == "f%d" % rf["id"] and rk and set(rk) == {"email"}, (jr, rk))
    check("회사 폴더로 이미 간 알림(noreply@newcomp-x)은 그대로 · 같은 회사 사람 메일도 그대로", key_of(r1) == "f%d" % nf["id"] and key_of(n2) == "f%d" % nf["id"], (row(r1), row(n2)))
    ju = k.post("/mail/move/undo").json()
    check("알림·광고 ↺ 되돌리기 → 일반으로", ju.get("ok") and key_of(r2) == "gen", row(r2))
    check("알림이 없으면 400(할 것 없음)", k.post("/mail/folders/general/robots").status_code == 200 and k.post("/mail/move/undo").json().get("ok"))

    print("== 14. 왼쪽 폴더 오른쪽 클릭 메뉴 · 💡 아래 폴더 추천(11-22 대표 「삼성그룹 하단에 더 구분 · 다른 회사도 구분」) ==")
    sg = by["삼성그룹"]["id"]
    d1 = put("d1.s@samsung.com", "디스플레이 자료", "자료입니다.\n\n감사합니다.\n\n정디스 책임\n삼성디스플레이㈜\nTel 031-000-0002", name="정디스")
    d2 = put("d2.s@samsung.com", "디스플레이 자료2", "자료입니다.\n\n감사합니다.\n\n한디스 프로\n삼성디스플레이㈜\nTel 031-000-0003", name="한디스")
    s1 = put("s1.s@samsung.com", "SDI 자료", "자료입니다.\n\n감사합니다.\n\n오에스 책임\n삼성SDI㈜\nTel 031-000-0004", name="오에스")
    check("서명이 다른 삼성 계열사 메일 → 아직은 삼성그룹", key_of(d1) == "f%d" % sg and key_of(s1) == "f%d" % sg, (row(d1), row(s1)))
    sj = k.post("/mail/folders/quick", data={"op": "suggest", "id": sg}).json()
    nm_ = {x["name"]: x for x in sj.get("items", [])}
    check("💡 추천 = 서명의 회사 이름(삼성디스플레이 2명 · 삼성SDI 1명) · 이미 있는 삼성전자·삼성전기는 안 나옴",
          sj.get("ok") and nm_.get("삼성디스플레이", {}).get("senders") == 2 and "삼성SDI" in nm_ and "삼성전자" not in nm_ and "삼성전기" not in nm_, sj)
    mj = k.post("/mail/folders/quick", data={"op": "makesubs", "id": sg, "names": ["삼성디스플레이", "삼성SDI", "삼성전자"]}).json()
    with _db.db_session() as c:
        kid = {r_["name"]: r_["id"] for r_ in c.execute("SELECT id, name FROM mail_folders WHERE user_id=? AND parent_id=?", (OWN, sg)).fetchall()}
    check("고른 것 만들기 = 삼성그룹 아래 2곳(이미 있는 삼성전자는 건너뜀)", mj.get("ok") and sorted(mj["made"]) == ["삼성SDI", "삼성디스플레이"] and "삼성디스플레이" in kid, mj)
    check("만든 뒤 그 회사 메일이 저절로 아래 폴더로(서명) · 모르는 메일은 삼성그룹",
          key_of(d1) == "f%d" % kid["삼성디스플레이"] and key_of(d2) == "f%d" % kid["삼성디스플레이"] and key_of(s1) == "f%d" % kid["삼성SDI"] and key_of(s_unk) == "f%d" % sg,
          (row(d1), row(s1), row(s_unk)))
    # 내 규칙으로 옮긴 폴더에 아래 폴더가 있으면 그 안에서도 나눔
    with _db.db_session() as c:
        c.execute("UPDATE mail_folders SET aliases='' WHERE id=?", (sg,))   # 회사 주소 자동 매칭을 끄고 규칙만으로
    mf._CACHE.pop(OWN, None)
    k.post("/mail/move", data={"ids": str(d1), "key": "f%d" % sg, "when": "all", "scope": "person"})
    check("규칙으로 삼성그룹에 넣어도 서명으로 아래 폴더(삼성디스플레이)", key_of(d1) == "f%d" % kid["삼성디스플레이"], row(d1))
    with _db.db_session() as c:
        c.execute("UPDATE mail_folders SET aliases='samsung.com, Samsung, 삼성' WHERE id=?", (sg,))
    mf._CACHE.pop(OWN, None)
    # 부서로 나누기(다른 회사 — 폴더 이름 = 서명 회사 이름이면 부서)
    dr = by["드림텍"]["id"]
    e1 = put("a1@dt-x.example", "검사 1", "자료\n\n감사합니다.\n\n가드림 책임\n드림텍㈜\n품질보증팀\nTel 031-1", name="가드림")
    e2 = put("a2@dt-x.example", "검사 2", "자료\n\n감사합니다.\n\n나드림 책임\n드림텍㈜\n구매팀\nTel 031-2", name="나드림")
    k.post("/mail/move", data={"ids": str(e1), "key": "f%d" % dr, "when": "all", "scope": "company"})
    dj = k.post("/mail/folders/quick", data={"op": "suggest", "id": dr}).json()
    check("💡 추천(회사 폴더) = 서명의 부서(품질보증팀·구매팀)", dj.get("ok") and any(x["by"] == "부서" for x in dj.get("items", [])), dj)
    print("    (부서 후보 %d곳)" % len([x for x in dj.get("items", []) if x["by"] == "부서"]))
    # 빠른 고치기
    q = lambda **kw: k.post("/mail/folders/quick", data=kw)
    check("이름 바꾸기", q(op="rename", id=dr, name="드림텍(DT)").json().get("ok") and fid("드림텍(DT)") == dr)
    check("아래 폴더 만들기(2단계 아래) · 3단계 아래는 막음",
          q(op="add", parent_id=dr, name="드림텍 베트남").json().get("ok") and q(op="add", parent_id=fid("드림텍 베트남"), name="4단계").status_code == 400)
    check("다른 이름 저장", q(op="aliases", id=dr, aliases="Dreamtech, dt-x.example").json().get("ok"))
    with _db.db_session() as c:
        al = c.execute("SELECT aliases FROM mail_folders WHERE id=?", (dr,)).fetchone()[0]
    check("다른 이름 = 쉼표로 저장", al == "Dreamtech, dt-x.example", al)
    check("위로·아래로", q(op="up", id=dr).json().get("ok") and q(op="down", id=dr).json().get("ok"))
    check("부서 이름(메일에서만) 바꾸기 · 비우면 원래", q(op="teamname", key="t%d" % T_QA, name="품질(시험)").json().get("ok")
          and cls()["labels"].get("t%d" % T_QA) == "품질(시험)" and q(op="teamname", key="t%d" % T_QA, name="").json().get("ok"))
    _UID["v"] = OTHER
    check("남의 폴더는 못 고침(404)", q(op="rename", id=dr, name="x").status_code == 404 and q(op="delete", id=dr).status_code == 404)
    _UID["v"] = OWN
    dv = fid("드림텍 베트남")
    check("지우기(아래 폴더) · 메일은 그대로", q(op="delete", id=dv).json().get("ok"))
    check("모르는 일 400 · 로그인 안 하면 401", q(op="zzz").status_code == 400
          and (lambda: (_UID.__setitem__("v", None), q(op="rename", id=dr, name="y").status_code)[1])() == 401)
    _UID["v"] = OWN
    hi = k.get("/mail/inbox").text
    check("왼쪽 폴더 = 오른쪽 클릭 표시(data-fk·깊이·다른 이름) + 메뉴(이름 바꾸기·아래 폴더·추천·다른 이름·지우기)",
          ('data-fk="f%d" data-dep="1"' % dr) in hi and 'data-al="Dreamtech, dt-x.example"' in hi
          and all(x in hi for x in ("✏️ 이름 바꾸기", "＋ 아래 폴더 만들기", "💡 아래 폴더 추천", "🏷 다른 이름", "🗑 폴더 지우기", "/mail/folders/quick")))
finally:
    pass

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
