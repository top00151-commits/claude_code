# -*- coding: utf-8 -*-
"""받은 메일 폴더(아웃룩식) 시험 — 가짜 직원·가짜 거래처·가짜 메일·임시 DB(운영 무접촉 · 실제 메일 없음).
대표 지시 2026-11-17 「지금 아웃룩을 이런 식으로 구분해서 사용하고 있어」 「진행해」.
① 대표 계정은 처음 열면 아웃룩 구조 그대로 생김 · 다른 사람은 안 생김(예전 거래처 폴더 그대로)
② 나누기: 직원 명부(주소·로그인 아이디·이름) → 서명의 부서 → KNK 기타 / 주소록·거래처 담당자 / 같은 회사 주소 /
   공급업체 / 서명의 회사 이름 / 폴더 없는 거래처 → 기타 고객사 / 둘 이상이면 일반
③ 「📁 이 폴더로」 = 회사 주소 규칙(개인 메일은 그 주소) · 규칙이 자동보다 먼저 · 남의 메일 막기
④ 숫자 = 목록 · 화면(works·kmail) · 관리(이름·더하기·순서·지우기 · 메일은 안 지움)
사용: py -3.13 _검증/mail_folders_test.py"""
import _mail_ico; _mail_ico.install()  # noqa: E402  11-28 4단계: 화면의 선 아이콘을 [i:이름] 으로 읽음(그림 문자 대신 · 아이콘 이름까지 확인)
import io
import os
import sys
import tempfile
import time

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
    _TMP = tempfile.mkdtemp(prefix="knk_mfold_")
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
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id='kjr'")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9001,'kjr','시험대표','ceo',1,'x')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9002,'t9002','시험이','member',1,'x')")
    c.execute("INSERT INTO teams(id, code, name, display_order) VALUES(981,'81','시험영업팀',81)")
    c.execute("INSERT INTO teams(id, code, name, display_order) VALUES(982,'82','시험설계팀',82)")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id) VALUES(9101,'st_a','가직원','member',1,'x','a1@knknara.co.kr',981)")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, team_id) VALUES(9102,'bb2','나직원','member',1,'x',982)")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, team_id) VALUES(9103,'cc3','최명부','member',1,'x',981)")
    c.execute("INSERT INTO customers(id, name) VALUES(701,'삼성전기㈜')")
    c.execute("INSERT INTO customers(id, name) VALUES(702,'㈜가나다전자')")
    c.execute("INSERT INTO customers(id, name) VALUES(703,'㈜라마바')")
    c.execute("INSERT INTO customers(id, name) VALUES(704,'㈜사아자')")
    c.execute("INSERT INTO customer_contacts(customer_id, role, name, email) VALUES(701,'구매','박구매','p@semco.example')")
    c.execute("INSERT INTO shared_contacts(name, email, visibility, created_by, customer_id) VALUES('홍길동','gildong@ganada.example','company',9001,702)")
    c.execute("INSERT INTO shared_contacts(name, email, visibility, created_by, customer_id) VALUES('이라마','rama@shared.example','company',9001,703)")
    c.execute("INSERT INTO shared_contacts(name, email, visibility, created_by, customer_id) VALUES('정사아','saa@shared.example','company',9001,704)")
    c.execute("INSERT INTO suppliers(name, code, email) VALUES('GTS','SUP-T1','sales@gts.example')")


def put(frm, subject, text, owner=OWN, name="보낸이", unread=True):
    _SEQ[0] += 1
    with _db.db_session() as c:
        mid, _o = ms.store_inbound(c, to_email="t%d@knknara.co.kr" % owner, from_email=frm, from_name=name,
                                   subject=subject, text=text, owner_id=owner, run_ai=False,
                                   message_id="mf-%d@test" % _SEQ[0])
        c.execute("UPDATE mail_messages SET received_at=datetime('now','localtime', ?), is_read=? WHERE id=?",
                  ("-%d seconds" % (9000 - _SEQ[0]), 0 if unread else 1, mid))
    return mid


SIG_MELFAS = "샘플 일정 공유드립니다.\n\n감사합니다.\n\n김철수 과장\n㈜멜파스\nTel 02-1234-5678\nkim@melfas.example"
SIG_DEPT = "도면 첨부합니다.\n\n감사합니다.\n\n유영희 대리\n시험설계팀\nTel 031-123-4567"
ids = {}
ids["staff_addr"] = put("a1@knknara.co.kr", "주간보고", "보고드립니다.", name="가직원")
ids["staff_login"] = put("bb2@knknara.co.kr", "도면", "도면입니다.", name="나직원")
ids["staff_name"] = put("myungbu@knknara.co.kr", "견적", "견적입니다.", name="최명부 과장")
ids["staff_sig"] = put("yhyu@knknara.co.kr", "도면 송부", SIG_DEPT, name="Yu")
ids["staff_x"] = put("who@knknara.co.kr", "안내", "안내입니다.", name="?")
ids["cust_contact"] = put("p@semco.example", "삼성발주건", "발주서 송부", name="박구매")
ids["cust_dom"] = put("new.person@ganada.example", "문의", "문의드립니다.")
ids["cust_amb"] = put("x@shared.example", "공동", "두 거래처가 같이 쓰는 주소")
ids["sup_dom"] = put("eng@gts.example", "PIN 견적", "견적서")
ids["sig_comp"] = put("kim@melfas.example", "샘플", SIG_MELFAS, name="김철수")
ids["free"] = put("hello.yj@gmail.com", "외주 견적", "견적입니다.")
ids["free2"] = put("other.person@gmail.com", "안녕하세요", "개인 메일")
ids["newco1"] = put("a@newco.example", "처음", "처음 연락드립니다.")
ids["newco2"] = put("b@newco.example", "두번째", "두 번째 사람", unread=False)
ids["robot"] = put("noreply@service.example", "알림", "자동 발송 알림입니다.")
ids["other_user"] = put("p@semco.example", "남의 메일", "x", owner=OTHER)

print("== 1. 처음 열기 — 대표 계정만 아웃룩 구조 생성 ==")
_UID = {"v": OWN}
_keep = m.get_user
m.get_user = lambda req: ({"id": _UID["v"], "role": "member", "name": "시험", "team_id": None, "team_name": ""} if _UID["v"] else None)


def client(port=5051, host="works.knknara.co.kr"):
    k = TestClient(m.app, base_url="http://127.0.0.1:%d" % port, raise_server_exceptions=False, follow_redirects=False)
    k.headers.update({"host": host, "x-forwarded-proto": "https"})
    return k


try:
    k = client()
    h = k.get("/mail/inbox?thread=0").text
    with _db.db_session() as c:
        fl = mf.folders(c, OWN)
        fl_other = mf.folders(c, OTHER)
    gnames = [f["name"] for f in fl if not f["parent_id"]]
    check("대표 계정: 묶음 6개가 아웃룩 순서 그대로", gnames == ["1.고객사", "2.기타 고객사", "3.외주업체", "4.PIN BLOCK 업체", "5.CHIP업체", "6.케이엔케이"], gnames)
    # 11-22 대표 「삼성은 삼성그룹으로 묶고 그 아래 삼성전자·삼성전기」 → 1.고객사 아래 18곳(삼성그룹 포함) · 삼성그룹 아래 2곳
    _sg = [f for f in fl if f["name"] == "삼성그룹"]
    check("1.고객사 아래 18곳(삼성그룹) · 삼성그룹 아래 삼성전자·삼성전기 · 5.CHIP업체 아래 9곳",
          len([f for f in fl if f["parent_id"] == fl[0]["id"]]) == 18 and len(_sg) == 1 and _sg[0]["parent_id"] == fl[0]["id"]
          and sorted(f["name"] for f in fl if f["parent_id"] == _sg[0]["id"]) == ["삼성전기", "삼성전자"]
          and len([f for f in fl if f["parent_id"] == [g for g in fl if g["name"] == "5.CHIP업체"][0]["id"]]) == 9)
    check("왼쪽에 「📁 폴더」 + 묶음 이름 + 「일반」", "[i:folder] 폴더" in h and "1.고객사" in h and "4.PIN BLOCK 업체" in h and 'href="/mail/inbox?fd=gen"' in h)
    check("폴더가 생기면 예전 「📁 거래처 폴더」는 숨김", "[i:folder] 거래처 폴더" not in h)
    k.get("/mail/inbox")
    with _db.db_session() as c:
        check("두 번 열어도 두 번 만들지 않음", len(mf.folders(c, OWN)) == len(fl))

    # 11-24 대표 「초기값은 회사 부서를 내 메일 기준으로 잡고 나머지는 기준을 잡지마」 — 직원 = 「케이엔케이」 하나 + 대표 부서 폴더 설정 그대로
    with _db.db_session() as c:
        mf.set_team_pref(c, OWN, "tv", name="베트남")
        c.execute("UPDATE mail_folders SET name='3.케이엔케이' WHERE user_id=? AND name='6.케이엔케이'", (OWN,))
    _UID["v"] = OTHER
    h2 = k.get("/mail/inbox").text
    with _db.db_session() as c:
        _of = mf.folders(c, OTHER)
        _otp = mf.team_prefs(c, OTHER)
    check("다른 사람: 처음 열면 「케이엔케이」 묶음 하나만(고객사·외주·칩 업체 없음 · 대표 이름 앞 번호 뗌)",
          [(f["name"], f["kind"]) for f in _of] == [("케이엔케이", "staff")], _of)
    check("다른 사람: 부서 폴더 설정은 대표 것 그대로(베트남 이름)", (_otp.get("tv") or {}).get("name") == "베트남", _otp)
    check("다른 사람 왼쪽: 「📁 폴더」 + 케이엔케이 + 부서 · 대표 고객사 이름 없음",
          "[i:folder] 폴더" in h2 and "케이엔케이" in h2 and "시험영업팀" in h2 and "1.고객사" not in h2 and "탑엔지니어링" not in h2, h2[:300])
    with _db.db_session() as c:
        c.execute("DELETE FROM mail_folders WHERE user_id=?", (OTHER,))
    k.get("/mail/inbox")
    with _db.db_session() as c:
        check("다른 사람: 지운 뒤에는 저절로 다시 안 만듦(한 번만)", not mf.folders(c, OTHER))
    hf = k.get("/mail/folders").text
    check("다른 사람 관리 화면 단추 = 「케이엔케이 — 본사·베트남 부서」(고객사 목록 아님)",
          "본사·베트남 부서" in hf and "PIN BLOCK" not in hf, hf[:200])
    _UID["v"] = OWN
    with _db.db_session() as c:
        mf.del_team_pref(c, OWN, "tv")
        c.execute("UPDATE mail_folders SET name='6.케이엔케이' WHERE user_id=? AND name='3.케이엔케이'", (OWN,))

    print("== 2. 나누기 ==")
    with _db.db_session() as c:
        res = mf.classify(c, OWN)
        lab = res["labels"]

        def where(key):
            with _db.db_session() as c2:
                mm = c2.execute("SELECT from_email FROM mail_messages WHERE id=?", (ids[key],)).fetchone()
            s = res["senders"].get(mm["from_email"].lower())
            return (lab.get(s["key"]), s["how"]) if s else (None, None)
    check("직원 명부(주소) → 81_시험영업팀", where("staff_addr")[0] == "81_시험영업팀", where("staff_addr"))
    check("직원 명부(로그인 아이디) → 82_시험설계팀", where("staff_login")[0] == "82_시험설계팀", where("staff_login"))
    check("직원 명부(이름 「최명부 과장」) → 81_시험영업팀", where("staff_name")[0] == "81_시험영업팀", where("staff_name"))
    check("명부에 없는 직원 → 서명의 부서 「시험설계팀」", where("staff_sig")[0] == "82_시험설계팀", where("staff_sig"))
    check("부서를 모르는 우리 회사 주소 → KNK 기타", where("staff_x")[0] == "KNK 기타(부서 모름)", where("staff_x"))
    check("거래처 담당자 이메일 → 1.고객사/삼성전기(이름 ㈜ 무시)", where("cust_contact")[0] == "삼성전기", where("cust_contact"))
    check("같은 회사 주소 · 폴더 없는 거래처 → 2.기타 고객사", where("cust_dom")[0] == "2.기타 고객사", where("cust_dom"))
    check("두 거래처가 같이 쓰는 주소 → 짐작 안 함(일반)", where("cust_amb")[0] == "일반", where("cust_amb"))
    check("공급업체 명단 회사 주소 → 4.PIN BLOCK 업체/GTS", where("sup_dom")[0] == "GTS", where("sup_dom"))
    check("서명의 회사 이름 「㈜멜파스」 → 5.CHIP업체/멜파스", where("sig_comp")[0] == "멜파스", where("sig_comp"))
    check("모르는 개인 메일 → 일반", where("free")[0] == "일반" and where("robot")[0] == "일반")
    _stf = [g for g in res["nodes"] if g["kind"] == "staff"][0]
    check("6.케이엔케이 아래 = 「본사」(11-19 대분류) 안에 메일 있는 부서만 · 코드_이름 · 그다음 KNK 기타",
          [x["name"] for x in _stf["children"]] == ["본사", "KNK 기타(부서 모름)"] and [y["name"] for y in _stf["children"][0]["children"]] == ["81_시험영업팀", "82_시험설계팀"],
          [(x["name"], [y["name"] for y in (x.get("children") or [])]) for x in _stf["children"]])
    check("남의 메일은 내 폴더 숫자에 안 섞임", sum(s["n"] for s in res["senders"].values()) == len(ids) - 1)

    print("== 3. 숫자 = 목록 ==")
    bad = []
    for key in list(res["keys_of"].keys()):
        with _db.db_session() as c:
            lst = ms.list_inbox(c, OWN, senders=mf.senders_in(res, key), limit=500)
        node_n = None
        for g in res["nodes"]:
            if g["key"] == key:
                node_n = g["n"]
            for ch in g["children"]:
                if ch["key"] == key:
                    node_n = ch["n"]
        if key == "gen":
            node_n = res["gen"]["n"]
        if node_n is not None and node_n != len(lst):
            bad.append((key, node_n, len(lst)))
    check("모든 폴더: 왼쪽 숫자 = 눌렀을 때 목록 수", not bad, bad)
    tot = sum(g["n"] for g in res["nodes"]) + res["gen"]["n"]
    check("묶음 합 + 일반 = 받은편지함 전체(빠짐·겹침 없음)", tot == len(ids) - 1, tot)
    gen_h = k.get("/mail/inbox?fd=gen&thread=0").text
    check("「일반」 누르면 그 메일만 · 다른 폴더 메일(삼성발주건·주간보고)은 안 보임", "외주 견적" in gen_h and "삼성발주건" not in gen_h and "주간보고" not in gen_h)
    cust_key = [g for g in res["nodes"] if g["name"] == "1.고객사"][0]["key"]
    g_h = k.get("/mail/inbox?fd=%s&thread=0" % cust_key).text
    check("묶음(1.고객사)을 누르면 아래 폴더 메일 모두", "삼성발주건" in g_h and "외주 견적" not in g_h)
    check("엉뚱한 fd 는 무시(전체 받은편지함)", k.get("/mail/inbox?fd=f999999").status_code == 200)
    check("선택한 폴더는 검색해도 유지(숨은 칸)", 'name="fd" value="gen"' in gen_h)
    check("일반(분류안됨) 보기는 위 띠 없음(대표 11-23 「안 나오게」) · 다른 폴더는 띠 그대로", 'class="mf-cur"' not in gen_h
          and 'class="mf-cur"' in g_h and "✕ 전체 보기" in g_h)
    check("폴더를 안 고르면 띠 없음", 'class="mf-cur"' not in k.get("/mail/inbox").text)

    print("== 4. 「📁 이 폴더로」 ==")
    pane = k.get("/mail/%d/pane" % ids["free"]).text
    check("읽기 칸에 「폴더 · 📁 일반」 + 고르기", "[i:folder] 일반" in pane and 'id="mvFolderSel"' in pane and "와이제이전자" in pane)
    check("6.케이엔케이 묶음 이름은 고를 수 없는 머리 줄 · 그 아래 부서 폴더는 고를 수 있음(11-22 대표 「부서 폴더가 안 보임」)",
          '<option value="" disabled>6.케이엔케이</option>' in pane and 'value="t981"' in pane and 'value="t982"' in pane)
    with _db.db_session() as c:
        yj = c.execute("SELECT id FROM mail_folders WHERE user_id=? AND name='와이제이전자'", (OWN,)).fetchone()["id"]
        outs = c.execute("SELECT id FROM mail_folders WHERE user_id=? AND name='3.외주업체'", (OWN,)).fetchone()["id"]
        staff_g = c.execute("SELECT id FROM mail_folders WHERE user_id=? AND kind='staff'", (OWN,)).fetchone()["id"]
        semco = c.execute("SELECT id FROM mail_folders WHERE user_id=? AND name='삼성전기'", (OWN,)).fetchone()["id"]
    j = k.post("/mail/%d/folder" % ids["free"], data={"folder_id": yj, "when": "all"}).json()
    check("개인 메일 → 그 주소 하나만 기억", j.get("ok") and j.get("kind") == "email" and j.get("pattern") == "hello.yj@gmail.com" and j.get("folder") == "와이제이전자", j)
    with _db.db_session() as c:
        res = mf.classify(c, OWN)
    check("같은 gmail 의 다른 사람은 그대로 일반", mf.folder_of(res, "other.person@gmail.com")["name"] == "일반")
    j = k.post("/mail/%d/folder" % ids["newco1"], data={"folder_id": outs, "when": "all"}).json()
    check("회사 주소 → @newco.example 전체 기억 · 옮긴 메일 2통", j.get("ok") and j.get("kind") == "domain" and j.get("pattern") == "newco.example" and j.get("moved") == 2, j)
    with _db.db_session() as c:
        res = mf.classify(c, OWN)
    check("같은 회사 다른 사람(b@newco)도 3.외주업체로", mf.folder_of(res, "b@newco.example")["name"] == "3.외주업체")
    later = put("c@newco.example", "나중에 온 메일", "앞으로 올 메일도")
    with _db.db_session() as c:
        res = mf.classify(c, OWN)
    check("앞으로 올 메일도 같은 폴더로", mf.folder_of(res, "c@newco.example")["name"] == "3.외주업체")
    j = k.post("/mail/%d/folder" % ids["cust_amb"], data={"folder_id": semco, "when": "all"}).json()
    with _db.db_session() as c:
        res = mf.classify(c, OWN)
    check("내 규칙이 자동보다 먼저(짐작 못 하던 주소 → 삼성전기)", mf.folder_of(res, "x@shared.example")["name"] == "삼성전기", j)
    j2 = k.post("/mail/%d/folder" % ids["free"], data={"folder_id": staff_g, "when": "all"})
    check("6.케이엔케이 묶음으로는 못 옮김(400)", j2.status_code == 400)
    j3 = k.post("/mail/%d/folder" % ids["other_user"], data={"folder_id": yj, "when": "all"})
    check("남의 메일은 못 건드림(404)", j3.status_code == 404)
    with _db.db_session() as c:
        oth_f = mf.add_folder(c, OTHER, "남의 폴더")
    j4 = k.post("/mail/%d/folder" % ids["free2"], data={"folder_id": oth_f, "when": "all"})
    check("남의 폴더로는 못 옮김(400)", j4.status_code == 400)
    _UID["v"] = None
    check("로그인 안 하면 401", k.post("/mail/%d/folder" % ids["free"], data={"folder_id": yj, "when": "all"}).status_code == 401)
    _UID["v"] = OWN

    print("== 4b. 더 똑똑하게(영문 이름·회사 주소·보낸 사람 이름·같은 회사 사람) + 일반 정리 ==")
    with _db.db_session() as c:
        mf.apply_seed_aliases(c, OWN)
    ids2 = {}
    ids2["dom_alias"] = put("kim@partron.example", "견적", "견적입니다.")
    ids2["en_sig"] = put("lee@dt-global.example", "Sample", "Please check.\n\nBest regards,\n\nJohn Lee\nManager\nDreamtech Co., Ltd.\nTel +82-31-000-0000")
    ids2["name_tag"] = put("park@skht.example", "회의", "회의 일정", name="박부장(세경하이테크)")
    ids2["short_bad"] = put("kimdaon@personal-x.example", "안녕", "개인", name="김다온")
    ids2["short_ok"] = put("cs@daon-x.example", "견적", "견적", name="다온 김철수")
    ids2["prop_a"] = put("a1@abovsemi.example", "칩", "자료\n\n감사합니다.\n\n홍길동 과장\n㈜어보브반도체\nTel 043-000-0000")
    ids2["prop_b"] = put("b2@abovsemi.example", "칩2", "자료입니다.")
    ids2["sam_a"] = put("x@samsung.example", "기", "자료\n\n감사합니다.\n\n김삼성 책임\n삼성전기㈜\nTel 031-000-0000")
    ids2["sam_b"] = put("y@samsung.example", "자", "자료\n\n감사합니다.\n\n이삼성 프로\n삼성전자㈜\nTel 031-000-0001")
    ids2["sam_c"] = put("z@samsung.example", "?", "누구인지 모름")
    ids2["subj_tag"] = put("q@unknown-fine.example", "[파인텍] 견적 송부", "견적 송부드립니다.")
    with _db.db_session() as c:
        res = mf.classify(c, OWN)
    fo = lambda e: mf.folder_of(res, e)["name"]
    check("회사 주소 @partron… → 파트론(영문 이름)", fo("kim@partron.example") == "파트론", mf.folder_of(res, "kim@partron.example"))
    check("영문 서명 「Dreamtech Co., Ltd.」 → 드림텍", fo("lee@dt-global.example") == "드림텍", mf.folder_of(res, "lee@dt-global.example"))
    check("보낸 사람 이름 「박부장(세경하이테크)」 → 세경하이테크", fo("park@skht.example") == "세경하이테크", mf.folder_of(res, "park@skht.example"))
    check("짧은 이름은 낱말이 같을 때만 — 「김다온」은 다온 아님", fo("kimdaon@personal-x.example") == "일반")
    check("「다온 김철수」 → 다온", fo("cs@daon-x.example") == "다온", mf.folder_of(res, "cs@daon-x.example"))
    check("같은 회사 주소의 다른 사람이 어보브반도체 → 나머지도 어보브반도체", fo("b2@abovsemi.example") == "어보브반도체", mf.folder_of(res, "b2@abovsemi.example"))
    check("삼성: 서명 = 삼성전기·삼성전자 아래 폴더로 · 구분 안 되면 삼성그룹(11-22 대표)",
          fo("x@samsung.example") == "삼성전기" and fo("y@samsung.example") == "삼성전자" and fo("z@samsung.example") == "삼성그룹",
          [mf.folder_of(res, e) for e in ("x@samsung.example", "y@samsung.example", "z@samsung.example")])
    check("삼성: 한 주소를 여러 폴더가 나눠 쓰면 규칙은 그 사람 한 명(회사 주소 모두 아님)",
          mf.rule_target("z@samsung.example", res) == ("email", "z@samsung.example") and mf.rule_target("kim@partron.example", res) == ("domain", "partron.example"))
    check("제목 [파인텍] 만으로는 자동으로 옮기지 않음(추천만)", fo("q@unknown-fine.example") == "일반")
    check("이름 비교에서 Incheon 의 inc 를 지우지 않음", mf.norm_name("Incheon Tech") == "incheontech", mf.norm_name("Incheon Tech"))
    with _db.db_session() as c:
        gg = mf.general_groups(c, OWN, res)
    gmap = {g["key"]: g for g in gg}
    check("일반 정리: 회사 주소별로 묶음(@personal-x.example 한 줄)", "personal-x.example" in gmap and gmap["personal-x.example"]["n"] == 1, sorted(gmap)[:20])
    check("일반 정리: 제목 [파인텍] → 추천 폴더 파인텍", gmap.get("unknown-fine.example", {}).get("suggest_name") == "파인텍", gmap.get("unknown-fine.example"))
    check("일반 정리: 개인 메일은 주소 하나로", "other.person@gmail.com" in gmap and gmap["other.person@gmail.com"]["is_domain"] is False)
    gp = k.get("/mail/folders/general")
    check("일반 정리 화면 200 · 노란 추천 줄 · 추천대로 모두 옮기기", gp.status_code == 200 and "gn-row sug" in gp.text and "추천대로 모두 옮기기" in gp.text, gp.status_code)
    gh = k.get("/mail/inbox?fd=gen").text
    check("일반 보기 띠·왼쪽에 「🧹 일반 정리하기」", gh.count("🧹 일반 정리하기") >= 2)
    with _db.db_session() as c:
        fine = c.execute("SELECT id FROM mail_folders WHERE user_id=? AND name='파인텍'", (OWN,)).fetchone()["id"]
        init = c.execute("SELECT id FROM mail_folders WHERE user_id=? AND name='이니텍'", (OWN,)).fetchone()["id"]
    j = k.post("/mail/folders/rule", data={"sender": "q@unknown-fine.example", "folder_id": fine, "when": "all"}).json()
    with _db.db_session() as c:
        res = mf.classify(c, OWN)
    check("「옮기기」 → 회사 주소 규칙 · 파인텍으로", j.get("ok") and j.get("kind") == "domain" and fo("q@unknown-fine.example") == "파인텍", j)
    check("내 메일에 없는 주소로는 규칙 못 만듦(404)", k.post("/mail/folders/rule", data={"sender": "nobody@x.example", "folder_id": fine, "when": "all"}).status_code == 404)
    later2 = put("z9@newcorp.example", "새 회사", "처음")
    k.post("/mail/folders/op", data={"op": "aliases", "id": init, "aliases": "INITECH, newcorp.example"})
    with _db.db_session() as c:
        res = mf.classify(c, OWN)
        al = c.execute("SELECT aliases FROM mail_folders WHERE id=?", (init,)).fetchone()["aliases"]
    check("관리 화면에서 다른 이름(회사 주소) 적기 → 그 주소 메일이 이니텍으로", fo("z9@newcorp.example") == "이니텍" and al == "INITECH, newcorp.example", (al, mf.folder_of(res, "z9@newcorp.example")))
    with _db.db_session() as c:
        c.execute("UPDATE mail_folders SET aliases='내가 고친 이름' WHERE user_id=? AND name='파트론'", (OWN,))
        mf.apply_seed_aliases(c, OWN)
        al2 = c.execute("SELECT aliases FROM mail_folders WHERE user_id=? AND name='파트론'", (OWN,)).fetchone()["aliases"]
    check("사람이 고친 다른 이름은 다시 덮지 않음", al2 == "내가 고친 이름")
    mp = k.get("/mail/folders").text
    check("관리 화면에 다른 이름 칸 · 일반 정리 바로가기", 'name="aliases"' in mp and "/mail/folders/general" in mp)

    print("== 5. 관리 화면 ==")
    r = k.get("/mail/folders")
    check("관리 화면 열림 · 규칙 3개 보임", r.status_code == 200 and "@newco.example" in r.text and "hello.yj@gmail.com" in r.text, r.status_code)
    k.post("/mail/folders/op", data={"op": "rename", "id": yj, "name": "와이제이전자(외주)"})
    k.post("/mail/folders/op", data={"op": "add", "parent_id": outs, "name": "새외주"})
    with _db.db_session() as c:
        kids = [f["name"] for f in mf.folders(c, OWN) if f["parent_id"] == outs]
    check("이름 바꾸기 · 폴더 더하기", kids == ["배송 및 포장업체", "와이제이전자(외주)", "새외주"], kids)
    with _db.db_session() as c:
        nf = c.execute("SELECT id FROM mail_folders WHERE user_id=? AND name='새외주'", (OWN,)).fetchone()["id"]
    k.post("/mail/folders/op", data={"op": "up", "id": nf})
    with _db.db_session() as c:
        kids = [f["name"] for f in mf.folders(c, OWN) if f["parent_id"] == outs]
    check("위로 한 칸", kids == ["배송 및 포장업체", "새외주", "와이제이전자(외주)"], kids)
    with _db.db_session() as c:
        n_mail_before = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND is_deleted=0", (OWN,)).fetchone()[0]
    k.post("/mail/folders/op", data={"op": "delete", "id": outs})
    with _db.db_session() as c:
        n_mail_after = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND is_deleted=0", (OWN,)).fetchone()[0]
        left = c.execute("SELECT COUNT(*) FROM mail_move_rules WHERE user_id=? AND target IN (?,?)", (OWN, "f%d" % outs, "f%d" % yj)).fetchone()[0]
        res = mf.classify(c, OWN)
    check("묶음 지우기: 아래 폴더·규칙도 지움 · 메일은 그대로", left == 0 and n_mail_before == n_mail_after)
    check("지운 폴더의 메일 → 일반으로 돌아감", mf.folder_of(res, "a@newco.example")["name"] == "일반" and mf.folder_of(res, "hello.yj@gmail.com")["name"] == "일반")
    with _db.db_session() as c:
        rid = c.execute("SELECT id FROM mail_move_rules WHERE user_id=? AND pattern='shared.example'", (OWN,)).fetchone()["id"]
    k.post("/mail/folders/op", data={"op": "delrule", "id": rid})
    with _db.db_session() as c:
        res = mf.classify(c, OWN)
    check("규칙 지우기 → 자동 분류로 돌아감(공동 주소 → 일반)", mf.folder_of(res, "x@shared.example")["name"] == "일반")
    _UID["v"] = OTHER
    with _db.db_session() as c:
        c.execute("DELETE FROM mail_folders WHERE user_id=?", (OTHER,))
    k.post("/mail/folders/op", data={"op": "seed"})
    with _db.db_session() as c:
        _of2 = mf.folders(c, OTHER)
        check("다른 사람은 관리 화면 단추로 직접 만들 수 있음 = 「케이엔케이」 하나(11-24)",
              [f["name"] for f in _of2 if not f["parent_id"]] == ["케이엔케이"] and len(_of2) == 1, _of2)
    _UID["v"] = OWN

    print("== 6. kmail 주소 · 보낸편지함 ==")
    km = client(port=5053, host="kmail.knknara.co.kr")
    check("kmail: 받은편지함 폴더 보기 200", km.get("/mail/inbox?fd=gen").status_code == 200)
    check("kmail: 폴더 관리 200", km.get("/mail/folders").status_code == 200)
    check("kmail: 「📁 이 폴더로」 POST 동작", km.post("/mail/%d/folder" % ids["free2"], data={"folder_id": semco, "when": "all"}).json().get("ok"))
    check("보낸편지함·휴지통은 폴더 없이 그대로", k.get("/mail/sent").status_code == 200 and k.get("/mail/trash").status_code == 200)
    check("메일 전체 화면에도 폴더 줄", "mvFolderCur" in k.get("/mail/%d" % ids["sig_comp"]).text)

    print("== 7. 속도(가짜 보낸 사람 800명) ==")
    with _db.db_session() as c:
        for i in range(800):
            _SEQ[0] += 1
            ms.store_inbound(c, to_email="t9001@knknara.co.kr", from_email="u%d@corp%d.example" % (i, i % 300),
                             from_name="사람%d" % i, subject="제목 %d" % i,
                             text="본문입니다.\n\n감사합니다.\n\n사람%d 과장\n㈜회사%d\nTel 02-111-%04d" % (i, i % 300, i),
                             owner_id=OWN, run_ai=False, message_id="perf-%d@test" % i)
    mf._CACHE.clear()
    mf._SIG_CACHE.clear()
    t0 = time.time()
    with _db.db_session() as c:
        mf.classify(c, OWN)
    t1 = time.time()
    with _db.db_session() as c:
        mf.classify(c, OWN)
    t2 = time.time()
    mf._CACHE.clear()
    t3 = time.time()
    with _db.db_session() as c:
        mf.classify(c, OWN)
    t4 = time.time()
    print("    처음 %.2f초 · 바로 다시 %.3f초 · 새 메일 뒤(서명 기억) %.2f초" % (t1 - t0, t2 - t1, t4 - t3))
    check("서명을 실제로 읽었음(보낸 사람 800명분)", len(mf._SIG_CACHE) >= 800, len(mf._SIG_CACHE))
    check("처음 계산 3초 안", t1 - t0 < 3.0, t1 - t0)
    check("다시 열 때 0.2초 안", t2 - t1 < 0.2, t2 - t1)
    check("서명은 다시 읽지 않음(1초 안)", t4 - t3 < 1.0, t4 - t3)
    t5 = time.time()
    r = k.get("/mail/inbox?thread=0")
    print("    받은편지함 화면 %.2f초" % (time.time() - t5))
    check("받은편지함 화면 200", r.status_code == 200)
finally:
    m.get_user = _keep

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
