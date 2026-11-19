# -*- coding: utf-8 -*-
"""z1191z78 시험 (대표 2026-11-19 세션 10 창 「초대시 등록하고 QR이 발행된 고객사 협력사 담당자 정보는 연락처로 저장이 될수있게해줘 …
  이음웍스에 "연락처(주소록)" … 우리부서공개 연락처에 저장」 → 세션 01 창 「둘 다 진행해」)
  이음 서버 → WORKS POST /api/contacts/from-eum · 임시 DB · TestClient · 가짜 자료 · 운영 아님
"""
import contextlib, io, os, re, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
KEY = "z1191z78-test-only-not-a-real-key"
os.environ["KNK_SSO_SERVICE_KEY"] = KEY
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z78_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()


def ins(c, table, row):
    cols = {r[1] for r in c.execute("PRAGMA table_info(%s)" % table)}
    ks = [k for k in row if k in cols]
    c.execute("INSERT INTO %s (%s) VALUES (%s)" % (table, ",".join('"%s"' % k for k in ks), ",".join("?" * len(ks))), [row[k] for k in ks])
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0"), ("rank", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    T1 = ins(c, "teams", {"name": "가상영업팀", "code": "T78A", "display_order": 1})
    T2 = ins(c, "teams", {"name": "가상구매팀", "code": "T78B", "display_order": 2})

    def user(nm, emp, team, active=1):
        c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, phone, rank) "
                  "VALUES (?, 'member', ?, ?, 'sso_only_no_local_password', ?, 1, ?, '010-0000-0000', '프로')", (nm, emp, emp, active, team))
        return dict(c.execute("SELECT * FROM users WHERE employee_no=?", (emp,)).fetchone())
    UA = user("가영업", "T781", T1)
    UB = user("나영업", "T782", T1)
    UC = user("다구매", "T783", T2)
    UN = user("부서없음", "VN781", None)
    UX = user("퇴사자", "T789", T1, active=0)
    OLD = ins(c, "shared_contacts", {"name": "기존고객", "company": "", "mobile": "010-5555-0001", "email": "", "created_by": UB["id"],
                                     "visibility": "dept", "share_team_id": T1, "source": "manual", "note": "직접 적은 메모"})

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
CUR = {"u": UA}
M.get_user = lambda request: CUR["u"]
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0


def check(cond, msg, got=None):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", msg)
    else:
        FAIL += 1; print("  ❌", msg, "" if got is None else ("  ← %r" % (got,)))


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def post(body, key=KEY):
    h = {"X-SSO-Service-Key": key} if key is not None else {}
    return q(cl.post, "/api/contacts/from-eum", json=body, headers=h)


def row(cid):
    with D.db_session() as c:
        r = c.execute("SELECT * FROM shared_contacts WHERE id=?", (cid,)).fetchone()
        return dict(r) if r else None


P1 = {"name": "김고객", "position": "책임", "company": "가상전자(주)", "department": "생산기술팀", "mobile": "01012345678",
      "email": "Kim.Gogaek@Example.TEST", "kind": "customer", "note": "KNK 이음 고객사 초대 · 방: 가상전자 PBA 검사기 · 담당업무: 설비 셋업", "eum_invite_id": 101}

print("§1 공유키 · 본문 검사")
check(post({"inviter_employee_no": "T781", "contacts": [P1]}, key=None).status_code == 401, "공유키 없으면 401")
check(post({"inviter_employee_no": "T781", "contacts": [P1]}, key="wrong").status_code == 401, "틀린 공유키 401")
r = post({"inviter_employee_no": "T999", "contacts": [P1]})
check(r.status_code == 400 and r.json()["error"] == "inviter_not_found", "없는 사번 → 400 inviter_not_found", r.json())
r = post({"inviter_employee_no": "T789", "contacts": [P1]})
check(r.status_code == 400 and r.json()["error"] == "inviter_not_found", "퇴사자 사번 → 400", r.json())
check(post({"inviter_employee_no": "T781", "contacts": []}).status_code == 400, "contacts 비면 400")
check(post({"inviter_employee_no": "T781", "contacts": [dict(P1, eum_invite_id=900 + i) for i in range(11)]}).json()["error"] == "too_many", "11명 → too_many(최대 10)")
check(q(cl.post, "/api/contacts/from-eum", content=b"not json", headers={"X-SSO-Service-Key": KEY, "Content-Type": "application/json"}).status_code == 400, "JSON 아님 → 400")

print("§2 새로 저장 = 초대한 직원 부서의 👥 부서 연락처")
r = post({"inviter_employee_no": "t781", "contacts": [P1]}).json()
res = r["results"][0]
check(r["ok"] and res["status"] == "created" and res["eum_invite_id"] == 101 and res["visibility"] == "dept" and res["contact_id"], "사번 대소문자 상관없이 · created · 부서", r)
x = row(res["contact_id"])
check(x["visibility"] == "dept" and x["share_team_id"] == T1 and x["created_by"] == UA["id"] and x["source"] == "eum", "부서 = 가영업 부서(영업팀) · 등록자 = 가영업 · 출처 이음", x)
check(x["mobile"] == "010-1234-5678" and x["email"] == "kim.gogaek@example.test" and x["company"] == "가상전자(주)" and x["position"] == "책임" and x["department"] == "생산기술팀",
      "휴대폰 010-1234-5678 모양 · 이메일 소문자 · 회사·직책·부서", x)
check(x["note"].startswith("[고객사] KNK 이음 고객사 초대") and "이음 초대 #101" in x["note"], "비고 = [고객사] + 이음이 보낸 글 + 「이음 초대 #101」", x["note"])
CID1 = res["contact_id"]
CUR["u"] = UB
hb = q(cl.get, "/contacts?tab=dept").text
check('<tr data-id="%d"' % CID1 in hb and '<span class="src-pill src-eum"' in hb, "같은 부서 나영업 「👥 부서」에 보임 · 출처 「이음」")
CUR["u"] = UC
check('<tr data-id="%d"' % CID1 not in q(cl.get, "/contacts").text, "다른 부서 다구매에게는 안 보임")
CUR["u"] = UA

print("§3 같은 사람 다시 초대 → 새로 안 만듦 · 빈 칸만")
r = post({"inviter_employee_no": "T781", "contacts": [P1]}).json()["results"][0]
check(r["status"] == "exists" and r["contact_id"] == CID1, "같은 초대 다시 → exists(같은 연락처)", r)
P1b = dict(P1, eum_invite_id=202, position="수석", company="바뀐회사", mobile="010-1234-5678", email="", note="방: 다른 방")
r = post({"inviter_employee_no": "T782", "contacts": [P1b]}).json()["results"][0]   # 같은 부서 다른 직원이 다른 방에 초대
x = row(CID1)
check(r["status"] == "updated" and r["contact_id"] == CID1 and x["position"] == "책임" and x["company"] == "가상전자(주)" and "이음 초대 #202" in x["note"],
      "같은 휴대폰(다른 방 · 같은 부서 다른 직원) → 같은 연락처 · 직책·회사 안 덮어씀 · 초대 번호만 더함", (r, x["position"], x["company"], x["note"]))
r = post({"inviter_employee_no": "T781", "contacts": [{"name": "기존고객", "mobile": "010 5555 0001", "company": "가상정밀", "email": "old@example.test", "kind": "partner", "eum_invite_id": 303}]}).json()["results"][0]
x = row(OLD)
check(r["status"] == "updated" and r["contact_id"] == OLD and x["company"] == "가상정밀" and x["email"] == "old@example.test" and x["note"].startswith("직접 적은 메모") and x["created_by"] == UB["id"],
      "부서에 이미 있던 사람(나영업이 적은 것) → 빈 회사·이메일만 채움 · 메모·등록자 그대로", x)
r = post({"inviter_employee_no": "T781", "contacts": [{"name": "번호없음", "email": "noph@example.test", "eum_invite_id": 404}]}).json()["results"][0]
r2 = post({"inviter_employee_no": "T781", "contacts": [{"name": "번호없음", "email": "NOPH@example.test", "eum_invite_id": 405}]}).json()["results"][0]
check(r["status"] == "created" and r2["status"] == "updated" and r2["contact_id"] == r["contact_id"], "휴대폰 없으면 이메일로 같은 사람", (r, r2))
r3 = post({"inviter_employee_no": "T781", "contacts": [{"name": "아무것도없음", "eum_invite_id": 406}]}).json()["results"][0]
r4 = post({"inviter_employee_no": "T781", "contacts": [{"name": "아무것도없음", "eum_invite_id": 406}]}).json()["results"][0]
check(r3["status"] == "created" and r4["status"] == "exists" and r4["contact_id"] == r3["contact_id"], "번호·이메일 없어도 이음 초대 번호로 다시 보낸 것 알아봄", (r3, r4))

print("§4 다른 부서 · 부서 없는 직원 · 이름 없음")
r = post({"inviter_employee_no": "T783", "contacts": [P1]}).json()["results"][0]
check(r["status"] == "created" and r["contact_id"] != CID1 and row(r["contact_id"])["share_team_id"] == T2, "구매팀 직원이 같은 고객을 초대 → 구매팀 부서 연락처에 따로(영업팀 것은 못 보니까)", r)
r = post({"inviter_employee_no": "VN781", "contacts": [{"name": "부서없는초대", "mobile": "0912345678", "eum_invite_id": 501}]}).json()["results"][0]
x = row(r["contact_id"])
check(r["status"] == "created" and r["visibility"] == "private" and x["visibility"] == "private" and "부서가 없어" in r["reason"] and x["mobile"] == "0912345678",
      "부서 없는 직원 → 그 직원 🔒 개인 연락처(잃지 않게) · 베트남 번호는 그대로", (r, x["mobile"]))
r = post({"inviter_employee_no": "T781", "contacts": [{"name": "", "mobile": "01099990000", "eum_invite_id": 601}, "문자열"]}).json()
check(r["ok"] and [x["status"] for x in r["results"]] == ["skipped", "skipped"] and r["results"][0]["reason"] == "이름 없음", "이름 없음·모양 다른 것 → skipped(나머지는 계속)", r)
r = post({"inviter_employee_no": "T781", "contacts": [dict(P1, name="여러명1", mobile="01011110001", eum_invite_id=701), dict(P1, name="여러명2", mobile="01011110002", eum_invite_id=702)]}).json()
check([x["status"] for x in r["results"]] == ["created", "created"], "여러 명 한 번에(이메일이 같아도 휴대폰이 다르면 다른 사람)", r)
check("이음" in q(cl.get, "/contacts?tab=dept").text, "목록에 출처 「이음」 표시")

print("§5 z1191z82 — 초대한 직원의 개인 카드(직접 등록)는 건드리지 않음")
with D.db_session() as c:
    MINE = ins(c, "shared_contacts", {"name": "가영업 본인 카드", "mobile": "010-8282-0001", "department": "", "note": "직접 적은 메모",
                                      "created_by": UA["id"], "visibility": "private", "source": "manual"})
r = post({"inviter_employee_no": "T781", "contacts": [{"name": "시험고객", "mobile": "01082820001", "department": "기술", "company": "시험회사", "eum_invite_id": 801}]}).json()["results"][0]
x = row(MINE)
check(r["status"] == "created" and r["contact_id"] != MINE and r["visibility"] == "dept", "같은 번호가 내 개인 카드에 있어도 → 부서공유에 새로 저장", r)
check(x["department"] == "" and x["note"] == "직접 적은 메모" and x["visibility"] == "private", "내 개인 카드는 그대로(부서·비고 안 바뀜)", x)
r2 = post({"inviter_employee_no": "VN781", "contacts": [{"name": "부서없는초대", "mobile": "0912345678", "eum_invite_id": 502}]}).json()["results"][0]
check(r2["status"] in ("updated", "exists") and r2["visibility"] == "private", "부서 없는 직원이 같은 사람을 다시 보내면 → 이음에서 들어온 그 개인 저장분을 찾음(두 번 안 만듦)", r2)

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
