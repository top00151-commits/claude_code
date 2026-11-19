# -*- coding: utf-8 -*-
"""메일 화면 3단계 시험 — 📦 보관함 · 여러 통 한 번에 · 「이 메일만」 폴더 · 이전·다음 · 오래된 메일 보관 · 쓰기(넓게·단추 한 줄·📇 주소록)
가짜 직원·가짜 메일·임시 DB(운영 무접촉 · 실제 메일 없음). 대표 지시 2026-11-18 「3단계 진행해」.
사용: py -3.13 _검증/mail_stage3_test.py"""
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
    _TMP = tempfile.mkdtemp(prefix="knk_mst3_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_folders as mf
    from app import mail_reply as mr
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
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id='kjr'")
    c.execute("INSERT INTO teams(id, code, name, display_order) VALUES(981,'81','시험영업팀',81)")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id) VALUES(9001,'kjr','시험대표','ceo',1,'x','boss@knknara.co.kr',981)")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, team_id) VALUES(9002,'t9002','시험이','member',1,'x',981)")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, team_id) VALUES(9003,'t9003','남부서','member',1,'x',NULL)")
    c.execute("INSERT INTO customers(id, name) VALUES(701,'삼성전기㈜')")
    c.execute("INSERT INTO customer_contacts(customer_id, role, name, email) VALUES(701,'구매','박구매','p@semco.example')")
    c.execute("INSERT INTO suppliers(name, code, email) VALUES('GTS','SUP-T1','sales@gts.example')")
    # 주소록 공개 범위 시험용
    c.execute("INSERT INTO shared_contacts(name, email, company, visibility, created_by) VALUES('전사공개','all@pub.example','공개사','company',9002)")
    c.execute("INSERT INTO shared_contacts(name, email, company, visibility, created_by) VALUES('남의개인','secret@priv.example','비밀사','private',9002)")
    c.execute("INSERT INTO shared_contacts(name, email, company, visibility, created_by) VALUES('내개인','mine@priv.example','내회사','private',9001)")
    c.execute("INSERT INTO shared_contacts(name, email, company, visibility, created_by, share_team_id) VALUES('부서공유','dept@team.example','부서사','dept',9002,981)")


def put(frm, subject, text="내용", owner=OWN, name="보낸이", ago="-1 hours", read=False, star=False):
    _SEQ[0] += 1
    with _db.db_session() as c:
        mid, _o = ms.store_inbound(c, to_email="boss@knknara.co.kr", from_email=frm, from_name=name, subject=subject,
                                   text=text, owner_id=owner, run_ai=False, message_id="st3-%d@test" % _SEQ[0])
        c.execute("UPDATE mail_messages SET received_at=datetime('now','localtime', ?), is_read=?, is_starred=? WHERE id=?",
                  (ago, 1 if read else 0, 1 if star else 0, mid))
    return mid


ids = {}
ids["s1"] = put("p@semco.example", "발주서 송부", "발주서 송부드립니다. 회신 부탁드립니다.", name="박구매", ago="-10 minutes")
ids["s2"] = put("p@semco.example", "샘플 일정 문의", "샘플 가능할까요?", name="박구매", ago="-20 minutes")
ids["s3"] = put("q@semco.example", "품질 이슈", "공유드립니다.", name="윤품질", ago="-30 minutes", read=True)
ids["g1"] = put("eng@gts.example", "PIN quotation", "Please check.", name="GTS", ago="-40 minutes")
ids["old_read"] = put("old@oldco.example", "오래된 읽은 메일", "옛", ago="-120 days", read=True)
ids["old_unread"] = put("old@oldco.example", "오래된 안 읽은 메일", "옛", ago="-121 days", read=False)
ids["old_star"] = put("old@oldco.example", "오래된 중요 메일", "옛", ago="-122 days", read=True, star=True)
ids["recent_read"] = put("new@newco.example", "최근 읽은 메일", "새", ago="-5 days", read=True)
ids["other"] = put("p@semco.example", "남의 메일", "x", owner=OTHER)

_U = {"v": {"id": OWN, "role": "ceo", "name": "시험대표", "team_id": 981, "team_name": "시험영업팀"}}
_keep = m.get_user
m.get_user = lambda req: _U["v"]


def client(port=5051, host="works.knknara.co.kr"):
    k = TestClient(m.app, base_url="http://127.0.0.1:%d" % port, raise_server_exceptions=False, follow_redirects=False)
    k.headers.update({"host": host, "x-forwarded-proto": "https"})
    return k


def has(h, mid):
    return ('data-mail-id="%d"' % mid) in h


def fid_of(name):
    with _db.db_session() as c:
        r = c.execute("SELECT id FROM mail_folders WHERE user_id=? AND name=?", (OWN, name)).fetchone()
    return r["id"] if r else None


def node_n(name):
    with _db.db_session() as c:
        res = mf.classify(c, OWN)
    for g in res["nodes"]:
        for kk in g["children"]:
            if kk["name"] == name:
                return kk["n"]
    return None


try:
    k = client()
    print("== 0. 새 칸(운영 DB 에 더하는 것 둘) ==")
    k.get("/mail/inbox")
    with _db.db_session() as c:
        cols = [r[1] for r in c.execute("PRAGMA table_info(mail_messages)").fetchall()]
    check("mail_messages 에 is_archived · fd_pin 칸이 생김(받은편지함 처음 열 때)", "is_archived" in cols and "fd_pin" in cols, cols[-6:])
    with _db.db_session() as c:
        z = c.execute("SELECT COUNT(*) FROM mail_messages WHERE COALESCE(is_archived,0)<>0 OR COALESCE(fd_pin,'')<>''").fetchone()[0]
    check("기존 메일은 모두 보관 아님 · 옮김 없음(기본값)", z == 0, z)

    import sqlite3 as _sq
    _f = os.path.join(_TMP, "retry.db")
    _c0 = _sq.connect(_f)
    _c0.execute("CREATE TABLE mail_messages(id INTEGER PRIMARY KEY, user_id INT, direction TEXT)")
    _c0.commit()
    _c0.execute("PRAGMA query_only=1")          # 칸 만들기가 실패하는 때(잠김 등)를 흉내
    ms._ensure_security_cols(_c0)
    _c0.close()
    _c1 = _sq.connect(_f)
    ms._ensure_security_cols(_c1)               # 다음 요청 — 다시 만들어야 한다
    _cols = [r[1] for r in _c1.execute("PRAGMA table_info(mail_messages)").fetchall()]
    _c1.close()
    check("⭐칸 만들기가 한 번 실패해도 다음에 다시 만든다(메일함이 계속 안 열리는 일 없음)", "is_archived" in _cols and "fd_pin" in _cols, _cols)

    print("== 1. 📦 보관 ==")
    h = k.get("/mail/inbox?thread=0").text
    check("왼쪽 「📦 보관함」 · 처음엔 숫자 없음", 'href="/mail/inbox?arc=1"' in h and "📦 보관함</span></a>" in h)
    r = k.post("/mail/%d/archive" % ids["s2"], data={"on": "1"}).json()
    h = k.get("/mail/inbox?thread=0").text
    check("보관 → 받은편지함에서 빠짐", r.get("ok") and not has(h, ids["s2"]) and has(h, ids["s1"]), r)
    with _db.db_session() as c:
        rr = c.execute("SELECT is_archived, is_read, is_deleted FROM mail_messages WHERE id=?", (ids["s2"],)).fetchone()
    check("보관 = 지우지 않음 · 읽음으로", (rr["is_archived"], rr["is_read"], rr["is_deleted"]) == (1, 1, 0), dict(rr))
    ha = k.get("/mail/inbox?arc=1&thread=0").text
    check("📦 보관함에 나옴 · 띠 「보관함」 · 왼쪽 숫자 1", has(ha, ids["s2"]) and "📦 <b>보관함</b>" in ha and re.search(r"📦 보관함</span><span class=\"cnt\">1</span>", ha) is not None)
    check("보관함 목록에 「📦 보관」 표시", "📦 보관</span>" in ha)
    check("보관함 선택 띠는 「📥 받은편지함으로」", "mbxBulk('unarchive')" in ha and "mbxBulk('archive')" not in ha)
    hs = k.get("/mail/inbox?thread=0&q=샘플").text
    check("찾기에는 보관한 메일도 나옴", has(hs, ids["s2"]))
    semco = fid_of("삼성전기")
    hf = k.get("/mail/inbox?thread=0&fd=f%d" % semco).text
    check("폴더 보기에도 보관한 메일 나옴", has(hf, ids["s2"]))
    p = k.get("/mail/%d/pane" % ids["s2"]).text
    check("읽기 화면: 보관한 메일은 「📥 받은편지함으로」", 'id="mvArcBtn"' in p and "📥 받은편지함으로" in p)
    p1 = k.get("/mail/%d/pane" % ids["s1"]).text
    check("읽기 화면: 보통 메일은 「📦 보관」", 'id="mvArcBtn"' in p1 and ">📦 보관</button>" in p1)
    with _db.db_session() as c:
        sc = mr.scan(c, OWN)
    check("회신 필요에서 보관한 메일은 뺌", ids["s2"] not in sc, list(sc.keys()))
    r = k.post("/mail/%d/archive" % ids["s2"], data={"on": "0"}).json()
    check("📥 받은편지함으로 → 다시 나옴", r.get("ok") and has(k.get("/mail/inbox?thread=0").text, ids["s2"]))
    check("남의 메일은 보관 못 함(404)", k.post("/mail/%d/archive" % ids["other"], data={"on": "1"}).status_code == 404)

    print("== 2. 여러 통 한 번에 ==")
    h = k.get("/mail/inbox?thread=0").text
    check("목록 줄마다 고르는 네모 · 선택 띠(숨김)", h.count('class="mbx-ck"') >= 8 and 'id="mbxSel" hidden' in h)
    check("대화 묶음 머리 네모 = 그 대화 메일 모두", 'data-ids="' in k.get("/mail/inbox").text)
    j = k.post("/mail/bulk", data={"op": "read", "ids": "%d,%d,%d" % (ids["s1"], ids["g1"], ids["other"])}).json()
    with _db.db_session() as c:
        rd = {r["id"]: r["is_read"] for r in c.execute("SELECT id, is_read FROM mail_messages WHERE id IN (?,?,?)", (ids["s1"], ids["g1"], ids["other"])).fetchall()}
    check("읽음 — 내 메일 2통만(남의 메일은 조용히 빠짐)", j.get("n") == 2 and rd[ids["s1"]] == 1 and rd[ids["g1"]] == 1 and rd[ids["other"]] == 0, (j, rd))
    j = k.post("/mail/bulk", data={"op": "unread", "ids": "%d" % ids["s1"]}).json()
    j2 = k.post("/mail/bulk", data={"op": "star", "ids": "%d,%d" % (ids["s1"], ids["g1"])}).json()
    hst = k.get("/mail/inbox?star=1&thread=0").text
    check("안 읽음 · ⭐ 중요 — ⭐ 중요 목록에 나옴", j.get("n") == 1 and j2.get("n") == 2 and has(hst, ids["s1"]) and has(hst, ids["g1"]))
    k.post("/mail/bulk", data={"op": "archive", "ids": "%d" % ids["g1"]})
    check("⭐ 중요 목록에는 보관한 중요 메일도 나옴", has(k.get("/mail/inbox?star=1&thread=0").text, ids["g1"]))
    k.post("/mail/bulk", data={"op": "unarchive", "ids": "%d" % ids["g1"]})
    k.post("/mail/bulk", data={"op": "unstar", "ids": "%d,%d" % (ids["s1"], ids["g1"])})
    j = k.post("/mail/bulk", data={"op": "delete", "ids": "%d" % ids["recent_read"]}).json()
    with _db.db_session() as c:
        dl = c.execute("SELECT is_deleted FROM mail_messages WHERE id=?", (ids["recent_read"],)).fetchone()[0]
    check("삭제 = 휴지통(되살릴 수 있음)", j.get("n") == 1 and dl == 1 and has(k.get("/mail/trash").text, ids["recent_read"]))
    k.post("/mail/%d/restore" % ids["recent_read"])
    check("모르는 일 · 빈 고르기는 400", k.post("/mail/bulk", data={"op": "zap", "ids": "1"}).status_code == 400 and k.post("/mail/bulk", data={"op": "read", "ids": ""}).status_code == 400)

    print("== 3. 「이 메일만」 폴더 ==")
    gts, partron = fid_of("GTS"), fid_of("파트론")
    n_semco0, n_partron0 = node_n("삼성전기"), node_n("파트론")
    j = k.post("/mail/%d/pin" % ids["s1"], data={"folder_id": partron}).json()
    check("이 메일만 파트론으로", j.get("ok") and j.get("folder") == "파트론" and j.get("pinned"), j)
    hp = k.get("/mail/inbox?thread=0&fd=f%d" % partron).text
    hs = k.get("/mail/inbox?thread=0&fd=f%d" % semco).text
    check("파트론 폴더에 나오고 · 삼성전기 폴더에서는 빠짐 · 같은 사람 다른 메일은 삼성전기 그대로",
          has(hp, ids["s1"]) and not has(hs, ids["s1"]) and has(hs, ids["s2"]))
    check("왼쪽 숫자도 옮겨짐(삼성전기 -1 · 파트론 +1)", node_n("삼성전기") == n_semco0 - 1 and node_n("파트론") == n_partron0 + 1,
          (n_semco0, node_n("삼성전기"), n_partron0, node_n("파트론")))
    h = k.get("/mail/inbox?thread=0").text
    row = re.search(r'<a [^>]*data-mail-id="%d"[^>]*>.*?</a>' % ids["s1"], h, re.S)
    check("목록 꼬리표 = 옮긴 폴더(파트론)", row and ">파트론</span>" in row.group(0), row and row.group(0)[-400:])
    p = k.get("/mail/%d/pane" % ids["s1"]).text
    check("읽기 화면: 📁 파트론 · 「이 메일만 옮김」 · ↺ 자동으로", "📁 파트론" in p and "이 메일만 옮김" in p and "mailPinUndo()" in p)
    check("읽기 화면: 폴더 고르면 「이 메일만 / 이 회사 메일 모두」 묻기", 'id="mvFolderAsk"' in p and "mailFolderGo('one')" in p and "mailFolderGo('all')" in p)
    j = k.post("/mail/%d/pin" % ids["s1"], data={"folder_id": 0}).json()
    check("↺ 자동으로 → 삼성전기로 돌아감", j.get("ok") and j.get("folder") == "삼성전기" and not j.get("pinned"), j)
    check("케이엔케이(부서 자동) 폴더·없는 폴더로는 못 옮김(400)", k.post("/mail/%d/pin" % ids["s1"], data={"folder_id": 999999}).status_code == 400)
    j = k.post("/mail/bulk", data={"op": "pin", "ids": "%d,%d" % (ids["s1"], ids["s3"]), "folder_id": gts}).json()
    check("여러 통 「이 메일들만 폴더로」", j.get("n") == 2 and has(k.get("/mail/inbox?thread=0&fd=f%d" % gts).text, ids["s3"]))
    with _db.db_session() as c:
        mf.delete_folder(c, OWN, gts)
        pins = c.execute("SELECT COUNT(*) FROM mail_messages WHERE fd_pin=?", ("f%d" % gts,)).fetchone()[0]
    check("폴더를 지우면 그 폴더로 옮긴 메일은 자동 분류로(메일은 그대로)", pins == 0 and has(k.get("/mail/inbox?thread=0").text, ids["s3"]))
    check("남의 메일은 못 옮김(404)", k.post("/mail/%d/pin" % ids["other"], data={"folder_id": partron}).status_code == 404)

    print("== 4. 이전·다음 메일 ==")
    pf = k.get("/mail/%d" % ids["s2"]).text
    check("풀페이지: ‹ 이전(더 새 s1) · 다음(더 지난 s3)", ('href="/mail/%d"' % ids["s1"]) in pf and ('href="/mail/%d"' % ids["s3"]) in pf and "‹ 이전 메일" in pf and "다음 메일 ›" in pf)
    pp = k.get("/mail/%d/pane" % ids["s2"]).text
    check("읽기 칸: 지금 목록 기준으로 이동(mvNav)", "mvNav(-1)" in pp and "mvNav(1)" in pp)

    print("== 5. 오래된 메일 한 번에 보관 ==")
    j = k.post("/mail/archive/old", data={"months": "3", "dry": "1"}).json()
    check("셈만: 3개월 지난 읽은 메일 1통(안 읽은 것·중요·최근 제외)", j.get("ok") and j.get("dry") and j.get("n") == 1, j)
    j = k.post("/mail/archive/old", data={"months": "3", "dry": "0"}).json()
    with _db.db_session() as c:
        st = {r["id"]: r["is_archived"] for r in c.execute("SELECT id, COALESCE(is_archived,0) AS is_archived FROM mail_messages WHERE id IN (?,?,?,?)",
                                                         (ids["old_read"], ids["old_unread"], ids["old_star"], ids["recent_read"])).fetchall()}
    check("보관: 오래된 읽은 메일만", j.get("n") == 1 and st == {ids["old_read"]: 1, ids["old_unread"]: 0, ids["old_star"]: 0, ids["recent_read"]: 0}, st)
    check("이상한 개월 수는 3개월로", k.post("/mail/archive/old", data={"months": "99", "dry": "1"}).json().get("ok"))
    t = k.get("/mail/tools").text
    check("⚙ 설정·정리: 「오래된 메일 한 번에 보관」 · 「보관함 보기」", "오래된 메일 한 번에 보관" in t and 'href="/mail/inbox?arc=1"' in t and "mtOldGo()" in t)

    print("== 6. 쓰기 화면 · 📇 주소록 ==")
    cp = k.get("/mail/compose").text
    check("보내기 단추 한 번(위 한 줄 · 늘 붙어 있게)", cp.count("onclick=\"sendMail()\"") == 1 and 'id="cSendBtn"' in cp and "position:sticky" in cp)
    check("받는 사람·참조 옆 「📇 주소록」", cp.count("📇 주소록</button>") == 2 and "abOpen('cTo')" in cp and "abOpen('cCc')" in cp)
    check("쓰기 칸 넓게 — 11-19 대표 「모니터 비율에 자동」: 1120px 캡 없앰 → 모니터 폭 꽉", "max-width:1120px" not in cp and "padding:18px;margin:0 var(--content-pad,32px) 24px}" in cp)
    em = [x["email"] for x in k.get("/api/mail/contacts?browse=1").json()["items"]]
    check("주소록 고르기: 전사 공개·내 개인·내 부서 공유는 보임", {"all@pub.example", "mine@priv.example", "dept@team.example"} <= set(em), em)
    check("주소록 고르기: 남의 「나만」 연락처는 안 보임", "secret@priv.example" not in em, em)
    ac = [x["email"] for x in k.get("/api/mail/contacts?q=priv").json()["items"]]
    check("받는 사람 자동완성도 남의 「나만」 연락처 안 뜸(전엔 떴음)", "secret@priv.example" not in ac and "mine@priv.example" in ac, ac)
    _U["v"] = {"id": 9003, "role": "member", "name": "남부서", "team_id": None, "team_name": ""}
    em3 = [x["email"] for x in k.get("/api/mail/contacts?browse=1").json()["items"]]
    check("다른 부서 사람: 부서 공유 연락처 안 보임 · 전사 공개는 보임", "dept@team.example" not in em3 and "all@pub.example" in em3, em3)
    _U["v"] = {"id": OWN, "role": "ceo", "name": "시험대표", "team_id": 981, "team_name": "시험영업팀"}

    print("== 6b. 대표 규칙 「배포 적용 전 직전 상태 저장」 · 화면 전환 ==")
    check("쓰기: 쓰던 내용을 이 기기에 계속 저장 · 다시 열면 「되살리기」", "knkmail.keep.v1:" in cp and 'id="cKeep"' in cp and "cKeepRestore()" in cp)
    check("쓰기: 보내기·💾 임시저장 성공하면 저장본 지움(11-19 「취소→나가기」에서도)", cp.count("if(window.cKeepClear) window.cKeepClear();") >= 3 and "window._cmpSent=true; if(window.cKeepClear) window.cKeepClear();" in cp)
    _inp = {i: (re.search(r'<input id="%s"[^>]*>' % i, cp) or re.search("x^", "")) for i in ("cTo", "cCc", "cBcc", "cSubj")}
    check("쓰기: 받는 사람·참조·숨은참조·제목은 공통 틀 저장과 겹치지 않게(data-knk-no-draft — 칸마다)",
          all(mm and "data-knk-no-draft" in mm.group(0) for mm in _inp.values()), {k_: bool(v) for k_, v in _inp.items()})
    vs = open(os.path.join(ROOT, "app", "templates", "_v5_partials", "mail_view_styles.html"), encoding="utf-8").read()
    hi = k.get("/mail/inbox").text
    check("「글자 크게」 스크립트는 본문 안(머리 조각엔 스크립트 없음 · 화면 전환 때도 돎)",
          "<script" not in vs and hi.find("knkmail.big") > hi.find('<main class="main"') > 0)

    print("== 7. kmail · 로그인 ==")
    km = client(port=5053, host="kmail.knknara.co.kr")
    check("kmail 보관함 200 · 여러 통 POST 동작", km.get("/mail/inbox?arc=1").status_code == 200 and km.post("/mail/bulk", data={"op": "read", "ids": str(ids["s1"])}).json().get("ok"))
    check("kmail 오래된 메일 셈 · 이 메일만 POST", km.post("/mail/archive/old", data={"dry": "1"}).json().get("ok") and km.post("/mail/%d/pin" % ids["s1"], data={"folder_id": 0}).json().get("ok"))
    _U["v"] = None
    check("로그인 안 하면 401", all(k.post(p_, data={"ids": "1", "op": "read"}).status_code == 401 for p_ in ("/mail/bulk", "/mail/%d/archive" % ids["s1"], "/mail/%d/pin" % ids["s1"], "/mail/archive/old")))
finally:
    m.get_user = _keep

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
