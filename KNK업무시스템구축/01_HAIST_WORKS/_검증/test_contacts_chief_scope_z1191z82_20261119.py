# -*- coding: utf-8 -*-
"""z1191z82 시험 (대표 2026-11-19 「법인총괄은 법인 공유연락처만 확인할수있게해.. 단 본사총괄은 법인 공유연락처까지도 모두 볼수있게하고.」)
  임시 DB · 가짜 자료 · 운영 아님
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z82-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z82_")
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
    T1 = ins(c, "teams", {"name": "가상영업팀", "code": "T77A", "display_order": 1})
    T2 = ins(c, "teams", {"name": "가상구매팀", "code": "T77B", "display_order": 2})

    def user(nm, emp, team, phone, entity="KOR", active=1, role="member"):
        c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, phone, entity, rank, email) "
                  "VALUES (?, ?, ?, ?, 'sso_only_no_local_password', ?, 1, ?, ?, ?, '프로', ?)", (nm, role, emp, emp, active, team, phone, entity, emp.lower() + "@example.test"))
        return dict(c.execute("SELECT * FROM users WHERE employee_no=?", (emp,)).fetchone())
    UA = user("가영업", "T771", T1, "010-1111-2222")
    UB = user("나영업", "T772", T1, "01033334444")
    UC = user("다구매", "T773", T2, "010 5555 6666")
    UV = user("반 끄엉", "VN771", T2, "0912 345 678", entity="VN")
    UX = user("퇴사자", "T779", T1, "010-9999-0000", active=0)
    UN = user("부서없음", "T778", None, "010-8888-7777")

    def ct(nm, by, vis="private", team=None, **kw):
        row = dict(name=nm, created_by=by, visibility=vis, share_team_id=team, source="manual")
        row.update(kw)
        return ins(c, "shared_contacts", row)
    A1 = ct("'썬텔제조1곽일용부장'", UA["id"], mobile=None, email="kiy102@example.test")          # 메일에서 들어온 따옴표 이름 · 휴대폰 없음
    A2 = ct("=?utf-8?B?JyLsnoTrs5HrrLgiJw==?=", UA["id"], company="가상상사", mobile="010-3308-5245")  # 인코딩 글자 이름
    A3 = ct("박부서", UA["id"], "dept", T1, company="가상고객", mobile="01077778888", phone="0212345678")
    A4 = ct("최전사", UA["id"], "company", None, company="가상협력", mobile="010-2222-3333")
    C1 = ct("정개인", UC["id"], mobile="010-4444-5555")
    C2 = ct("한구매부서", UC["id"], "dept", T2, mobile="010-6666-7777")
    C3 = ct("오전사", UC["id"], "company", None, mobile="010-8888-9999")

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import app.contacts as CT  # noqa: E402
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


def ids(html):
    return sorted(int(x) for x in re.findall(r'<tr data-id="(\d+)"', html))


def counts(html):
    return dict(re.findall(r'href="/contacts\?tab=(\w+)[^"]*"[^>]*>[^<]*(?:<small[^>]*>[^<]*</small>)?<span class="n">(\d+)</span>', html))


with D.db_session() as c:
    c.execute("UPDATE teams SET entity='KOR' WHERE id IN (?,?)", (T1, T2))
    TK = ins(c, "teams", {"name": "총괄", "code": "00", "display_order": -1, "entity": "KOR"})
    TV0 = ins(c, "teams", {"name": "총괄", "code": "V00", "display_order": -1, "entity": "VN"})
    TV1 = ins(c, "teams", {"name": "조립팀", "code": "05_2", "display_order": 30, "entity": "VN"})
    TV2 = ins(c, "teams", {"name": "구매팀", "code": "V09", "display_order": 31, "entity": "VN"})
    UK = user("본사총괄", "T7700", TK, "010-0000-0001")
    UVC = user("법인총괄", "VN7700", TV0, "0900 000 001", entity="VN")
    UV1 = user("조립사원", "VN7701", TV1, "0900 000 002", entity="VN")
    UV2 = user("법인구매", "VN7702", TV2, "0900 000 003", entity="VN")
    V1 = ct("조립협력사", UV1["id"], "dept", TV1, mobile="0911 111 111")
    V2 = ct("법인구매처", UV2["id"], "dept", TV2, mobile="0922 222 222")
    VC = ct("법인총괄부서것", UVC["id"], "dept", TV0, mobile="0933 333 333")


def ids(h):
    return sorted(int(x) for x in re.findall(r'<tr data-id="(\d+)"', h))


print("§1 법인 총괄 = 법인 부서공유만")
CUR["u"] = UVC
h = q(cl.get, "/contacts?tab=dept").text
check(set(ids(h)) == {V1, V2, VC}, "법인총괄: 법인 조립팀·구매팀·총괄 부서공유 보임", ids(h))
check(A3 not in ids(h) and C2 not in ids(h), "본사 부서(영업팀·구매팀) 부서공유는 안 보임")
check("(법인 부서 · 법인 총괄)" in h and "법인 총괄은 법인 부서공유 전부" in h and "법인 부서 전체 <span" in h, "책갈피·설명·단추 = 「법인 부서 · 법인 총괄」")
check(q(cl.get, "/contacts/%d" % A3).status_code == 303 and q(cl.get, "/contacts/%d" % V1).status_code == 200, "본사 부서 연락처 상세는 못 열고 · 법인 것은 열림")
check(A4 in ids(q(cl.get, "/contacts?tab=company").text), "전사공유는 그대로 보임")

print("§2 본사 총괄 = 본사 + 법인 모두")
CUR["u"] = UK
h = q(cl.get, "/contacts?tab=dept").text
check(set(ids(h)) == {A3, C2, V1, V2, VC}, "본사총괄: 본사·법인 모든 부서공유", ids(h))
check("(모든 부서 · 총괄)" in h and "본사 총괄은 본사·법인 모든 부서공유" in h, "책갈피·설명 = 본사 총괄")
check(q(cl.get, "/contacts/%d" % V2).status_code == 200, "법인 부서 연락처 상세도 열림")

print("§3 일반 법인 직원은 자기 부서만")
CUR["u"] = UV1
check(ids(q(cl.get, "/contacts?tab=dept").text) == [V1], "조립사원: 조립팀 것만")

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
