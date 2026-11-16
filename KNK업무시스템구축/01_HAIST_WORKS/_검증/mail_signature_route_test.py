# -*- coding: utf-8 -*-
"""📇 메일 → 주소록 등록 길 시험 — 가짜 직원·가짜 메일·임시 DB(운영 무접촉 · 실제 메일 없음).
① 초안 길이 서명에서 칸을 채워 돌려준다(저장은 안 함)  ② 저장 길이 확인한 칸 그대로 저장한다
③ 남의 메일로는 못 한다  ④ 메일 전용 주소(kmail)에서도 된다  ⑤ 읽기 화면에 단추·채움 칸이 나온다
⑥ 옛 방식(칸 없이 누름)도 그대로 된다
사용: py -3.13 _검증/mail_signature_route_test.py"""
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
    _TMP = tempfile.mkdtemp(prefix="knk_sigroute_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
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


SIG_BODY = """견적서 송부드립니다.

감사합니다.

홍길동 부장
㈜가나다전자 구매팀
Tel. 031-000-1234  Fax. 031-000-1235
Mobile. 010-0000-1234
주소: 경기도 화성시 가나다로 12, 3층
"""

with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9001,'t9001','시험일','member',1,'x')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9002,'t9002','시험이','member',1,'x')")
    MID, _ = ms.store_inbound(c, to_email="t9001@knknara.co.kr", from_email="gildong@ganada-elec.example", from_name="홍길동",
                              subject="견적서", text=SIG_BODY, owner_id=9001, run_ai=False, message_id="sig-1@test")
    MID2, _ = ms.store_inbound(c, to_email="t9001@knknara.co.kr", from_email="nosig@other.example", from_name="무서명",
                               subject="회신", text="네 알겠습니다.", owner_id=9001, run_ai=False, message_id="sig-2@test")
    MID3, _ = ms.store_inbound(c, to_email="t9002@knknara.co.kr", from_email="x@third.example", from_name="남의메일",
                               subject="남의 것", text=SIG_BODY, owner_id=9002, run_ai=False, message_id="sig-3@test")
    MID4, _ = ms.store_inbound(c, to_email="t9001@knknara.co.kr", from_email="old@oldway.example", from_name="옛방식",
                               subject="옛", text="감사합니다.", owner_id=9001, run_ai=False, message_id="sig-4@test")
check("가짜 메일 4통 저장", all((MID, MID2, MID3, MID4)), (MID, MID2, MID3, MID4))

_UID = {"v": 9001}
_keep = m.get_user


def _fake_user(req):
    if not _UID["v"]:
        return None
    return {"id": _UID["v"], "role": "member", "name": "시험", "team_id": None, "team_name": ""}


m.get_user = _fake_user


def client(port=5051, host="works.knknara.co.kr"):
    k = TestClient(m.app, base_url="http://127.0.0.1:%d" % port, raise_server_exceptions=False, follow_redirects=False)
    k.headers.update({"host": host, "x-forwarded-proto": "https"})
    return k


def rows(sql, a=()):
    with _db.db_session() as c:
        return [dict(r) for r in c.execute(sql, a).fetchall()]


try:
    k = client()
    print("== 1. 초안 길 — 채워서 돌려주되 저장하지 않는다 ==")
    r = k.get("/mail/%d/contact-draft" % MID)
    j = r.json() if r.status_code == 200 else {}
    f = j.get("fields") or {}
    check("초안 200 · ok", r.status_code == 200 and j.get("ok") is True, (r.status_code, r.text[:200]))
    check("초안: 이름·직급·회사·부서", (f.get("name"), f.get("position"), f.get("company"), f.get("department")) == ("홍길동", "부장", "㈜가나다전자", "구매팀"), f)
    check("초안: 휴대폰·전화·팩스", (f.get("mobile"), f.get("phone"), f.get("fax")) == ("010-0000-1234", "031-000-1234", "031-000-1235"), f)
    check("초안: 주소·메일 주소", f.get("address") == "경기도 화성시 가나다로 12, 3층" and f.get("email") == "gildong@ganada-elec.example", f)
    check("초안: 채운 칸 목록·서명 글", len(j.get("filled") or []) >= 6 and "홍길동 부장" in (j.get("sig_text") or ""), j.get("filled"))
    check("초안은 저장하지 않는다", rows("SELECT COUNT(*) n FROM shared_contacts")[0]["n"] == 0)
    check("초안 응답은 저장해 두지 않게(no-store)", "no-store" in (r.headers.get("cache-control") or ""))
    r = k.get("/mail/%d/contact-draft" % MID2)
    j = r.json()
    check("서명 없는 메일: 이름·메일만 + 안내", j["fields"]["name"] == "무서명" and not j["fields"]["mobile"] and any("찾지 못했습니다" in n for n in j["notes"]), j)
    r = k.post("/mail/%d/contact-draft" % MID2, data={"text": "무서명 과장\n(주)붙임상사\nH.P 010-0000-7777"})
    j = r.json()
    check("붙여 넣은 글로 다시 채우기", (j["fields"]["position"], j["fields"]["company"], j["fields"]["mobile"]) == ("과장", "(주)붙임상사", "010-0000-7777"), j)

    print("== 2. 남의 메일 · 로그인 안 함 ==")
    check("남의 메일 초안 → 404", k.get("/mail/%d/contact-draft" % MID3).status_code == 404)
    check("남의 메일 저장 → 404", k.post("/mail/%d/to-contact" % MID3, data={"name": "가"}).status_code == 404)
    _UID["v"] = 0
    check("로그인 안 함 초안 → 401", k.get("/mail/%d/contact-draft" % MID).status_code == 401)
    check("로그인 안 함 저장 → 401", k.post("/mail/%d/to-contact" % MID, data={"name": "가"}).status_code == 401)
    _UID["v"] = 9001
    check("아직 아무것도 저장 안 됨", rows("SELECT COUNT(*) n FROM shared_contacts")[0]["n"] == 0)

    print("== 3. 읽기 화면 — 단추와 채움 칸 ==")
    r = k.get("/mail/%d/pane" % MID)
    h = r.text
    check("읽기 창 200", r.status_code == 200, r.status_code)
    check("단추 「주소록에 등록」", 'id="mvContactBtn"' in h and "주소록에 등록" in h)
    check("채움 칸 9개(숨김 상태)", 'id="mvContact" style="display:none"' in h and all(('id="mvc_%s"' % x) in h for x in
          ("name", "position", "company", "department", "mobile", "phone", "fax", "email", "address")))
    check("스크립트: 초안 길·저장 길을 부른다", "/contact-draft" in h and "/to-contact" in h and "mvcSave" in h)
    r = k.get("/mail/%d" % MID)
    check("전체 화면에도 같은 칸", r.status_code == 200 and 'id="mvContact"' in r.text and ".mv-contact{" in r.text, r.status_code)

    print("== 4. 저장 길 — 확인한 칸 그대로 ==")
    form = {"name": "홍길동", "position": "부장", "company": "㈜가나다전자", "department": "구매팀", "mobile": "010-0000-1234",
            "phone": "031-000-1234", "fax": "031-000-1235", "email": "gildong@ganada-elec.example",
            "address": "경기도 화성시 가나다로 12, 3층", "visibility": "company", "customer_id": "999999"}
    r = k.post("/mail/%d/to-contact" % MID, data=form)
    j = r.json()
    check("저장 200 · ok · 새로 만듦", r.status_code == 200 and j.get("ok") and j.get("existed") is False and j.get("contact_id"), j)
    row = (rows("SELECT * FROM shared_contacts WHERE id=?", (j.get("contact_id") or 0,)) or [{}])[0]
    check("저장된 칸이 화면 값과 같다", all((row.get(x) or "") == form[x] for x in
          ("name", "position", "company", "department", "mobile", "phone", "fax", "email", "address")), row)
    check("출처=서명 · 등록자=나 · 전 직원 공유", (row.get("source"), row.get("created_by"), row.get("visibility")) == ("signature", 9001, "company"), row)
    check("없는 거래처 번호는 연결하지 않는다", row.get("customer_id") is None, row.get("customer_id"))
    r = k.post("/mail/%d/to-contact" % MID, data=form)
    j2 = r.json()
    check("한 번 더 누르면 새로 만들지 않는다", j2.get("existed") is True and j2.get("contact_id") == j.get("contact_id")
          and rows("SELECT COUNT(*) n FROM shared_contacts")[0]["n"] == 1, j2)
    h = k.get("/mail/%d/pane" % MID).text
    check("저장 뒤 읽기 창: 연락처 고리 · 채움 칸 없음", ("/contacts/%d" % j["contact_id"]) in h and 'id="mvContact"' not in h)
    r = k.get("/mail/%d/contact-draft" % MID)
    check("같은 메일 주소 기존 연락처를 알린다", any(d.get("id") == j["contact_id"] for d in (r.json().get("dups") or [])), r.json().get("dups"))

    print("== 5. 끼워넣기·긴 글 ==")
    bad = {"name": "<script>alert(1)</script>" + "가" * 200, "company": "x" * 500, "email": "주소아님", "visibility": "엉뚱"}
    r = k.post("/mail/%d/to-contact" % MID2, data=bad)
    j = r.json()
    row = (rows("SELECT * FROM shared_contacts WHERE id=?", (j.get("contact_id") or 0,)) or [{}])[0]
    check("이름 80자·회사 120자로 자름", len(row.get("name") or "") == 80 and len(row.get("company") or "") == 120, (len(row.get("name") or ""), len(row.get("company") or "")))
    check("메일 주소가 아니면 보낸 주소로", row.get("email") == "nosig@other.example", row.get("email"))
    check("엉뚱한 공유 범위는 「나만」", row.get("visibility") == "private", row.get("visibility"))
    h = k.get("/mail/%d/pane" % MID2).text
    check("저장한 이름이 화면에 글자로만(태그로 살아나지 않음)", "<script>alert(1)" not in h and "&lt;script&gt;alert(1)" in h)

    print("== 6. 옛 방식(칸 없이 누름) · 메일 전용 주소 ==")
    r = k.post("/mail/%d/to-contact" % MID4)
    j = r.json()
    row = (rows("SELECT * FROM shared_contacts WHERE id=?", (j.get("contact_id") or 0,)) or [{}])[0]
    check("옛 방식: 이름·메일만 저장", j.get("ok") and (row.get("name"), row.get("email"), row.get("source")) == ("옛방식", "old@oldway.example", "signature"), (j, row))
    km = client(5053, "kmail.knknara.co.kr")
    r = km.get("/mail/%d/contact-draft" % MID)
    check("메일 전용 주소에서도 초안 길이 열린다", r.status_code == 200 and r.json().get("ok") is True, (r.status_code, r.headers.get("location")))
    r = km.post("/mail/%d/contact-draft" % MID, data={"text": "가나 대리\n010-0000-2222"})
    check("메일 전용 주소에서도 다시 채우기", r.status_code == 200 and r.json()["fields"]["mobile"] == "010-0000-2222", r.status_code)

    print("== 7. 같은 도메인 기존 연락처 → 거래처 미리 고르기 ==")
    with _db.db_session() as c:
        c.execute("INSERT INTO customers(id, name) VALUES(77, '가나다전자')")
        c.execute("UPDATE shared_contacts SET customer_id=77 WHERE email='gildong@ganada-elec.example'")
        MID5, _ = ms.store_inbound(c, to_email="t9001@knknara.co.kr", from_email="new@ganada-elec.example", from_name="신입",
                                   subject="인사", text="잘 부탁드립니다.", owner_id=9001, run_ai=False, message_id="sig-5@test")
    j = k.get("/mail/%d/contact-draft" % MID5).json()
    check("거래처 한 곳 → 미리 고름 + 회사 이름", (j.get("customer") or {}).get("id") == 77 and j["fields"]["company"] == "㈜가나다전자", j)
    r = k.post("/mail/%d/to-contact" % MID5, data={"name": "신입", "company": "㈜가나다전자", "customer_id": "77"})
    row = (rows("SELECT * FROM shared_contacts WHERE id=?", (r.json().get("contact_id") or 0,)) or [{}])[0]
    check("거래처 연결 저장", row.get("customer_id") == 77, row)

    print("== 8. 다른 직원의 「나만 보는」 연락처는 드러내지 않는다 ==")
    with _db.db_session() as c:
        c.execute("INSERT INTO shared_contacts(name, company, mobile, email, visibility, created_by) "
                  "VALUES('남의개인연락처','비공개상사','010-0000-4321','hidden@secret.example','private',9002)")
        c.execute("INSERT INTO shared_contacts(name, company, mobile, email, visibility, created_by) "
                  "VALUES('전사연락처','공개상사','010-0000-4321','open@open.example','company',9002)")
        MID6, _ = ms.store_inbound(c, to_email="t9001@knknara.co.kr", from_email="same@mobile.example", from_name="같은번호",
                                   subject="번호", text="감사합니다.\n같은번호 대리\nM. 010-0000-4321", owner_id=9001,
                                   run_ai=False, message_id="sig-6@test")
    j = k.get("/mail/%d/contact-draft" % MID6).json()
    names = [d.get("name") for d in (j.get("dups") or [])]
    check("전 직원 공유 연락처는 알린다", "전사연락처" in names, names)
    check("남의 개인 연락처는 이름·회사가 나오지 않는다", "남의개인연락처" not in names and "비공개상사" not in str(j), names)
finally:
    m.get_user = _keep

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
