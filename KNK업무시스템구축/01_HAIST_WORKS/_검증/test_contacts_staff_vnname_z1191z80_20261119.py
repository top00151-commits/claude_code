# -*- coding: utf-8 -*-
"""z1191z80 시험 (대표 2026-11-19 「베트남직원들 이름은 "팅_Nguyễn Văn Thịnh" 이런식으로 표현해줘.」 + 「이건 주소록에 이름만 얘기하는거야.」)
  주소록 「🏢 우리 회사 직원」 이름 · 임시 DB · 가짜 자료 · 운영 아님
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z80-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z80_")
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
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, phone, entity, rank, name_vi, name_en) "
              "VALUES ('팅', 'member', 'VN780', 'VN780', 'x', 1, 1, ?, '0987 111 222', 'VN', '프로', 'Nguyễn Văn Thịnh', 'NGUYEN VAN THINH')", (T2,))
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, phone, entity, rank, name_vi, name_en) "
              "VALUES ('땀', 'member', 'VN781', 'VN781', 'x', 1, 1, ?, '0987 333 444', NULL, '프로', 'Nguyễn Đình Tám', 'NGUYEN DINH TAM')", (T2,))
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, phone, entity, rank, name_vi, name_en) "
              "VALUES ('박주재', 'member', 'VN782', 'VN782', 'x', 1, 1, ?, '0987 555 666', 'VN', '법인장', NULL, 'PARK JU JAE')", (T2,))


def names(h):
    return sorted(re.findall(r"<tr><td><b>([^<]+)</b></td>", h))


print("§1 주소록 직원 이름")
CUR["u"] = UA
hv = q(cl.get, "/contacts?tab=staff&corp=vn").text
n = names(hv)
check("팅_Nguyễn Văn Thịnh" in n and "땀_Nguyễn Đình Tám" in n, "베트남 직원 = 「팅_Nguyễn Văn Thịnh」 · 법인 칸이 비어도 사번 VN… 이면 같게", n)
check("박주재" in n and not any(x.startswith("박주재_") for x in n), "베트남어 이름이 없는 법인 직원(한국인 주재원) = 이름만", n)
check("반 끄엉" in n, "베트남어 이름 칸이 비어 있으면 이름만(지금처럼)", n)
hk = q(cl.get, "/contacts?tab=staff&corp=kr").text
check("가영업" in names(hk) and not any("_" in x for x in names(hk)), "본사 직원 이름은 그대로", names(hk))

print("§2 찾기 — 한글 이름 · 베트남어 · 성조 없이 · 영문")
for qq in ("팅", "Thịnh", "thinh", "NGUYEN VAN THINH", "nguyen van"):
    got = names(q(cl.get, "/contacts", params={"tab": "staff", "q": qq}).text)
    check("팅_Nguyễn Văn Thịnh" in got, "「%s」로 찾으면 팅_Nguyễn Văn Thịnh" % qq, got)
check(names(q(cl.get, "/contacts", params={"tab": "staff", "q": "dinh tam"}).text) == ["땀_Nguyễn Đình Tám"], "「dinh tam」(đ 없이) → 땀_Nguyễn Đình Tám")

print("§3 휴대폰 저장(vCard) 이름도 같게")
v = q(cl.get, "/contacts/vcards.vcf?tab=staff&corp=vn").text
check("FN:팅_Nguyễn Văn Thịnh" in v and "FN:박주재\r\n" in v, "vCard 이름 = 팅_Nguyễn Văn Thịnh · 주재원은 이름만")

print("§4 주소록 직원 이름만 — 다른 곳은 그대로")
with D.db_session() as c:
    r = c.execute("SELECT name FROM users WHERE employee_no='VN780'").fetchone()
check(r[0] == "팅", "저장된 직원 이름(users.name)은 그대로 「팅」")
check("팅_Nguyễn" not in q(cl.get, "/contacts?tab=all").text, "직원 책갈피 밖(연락처 목록)에는 영향 없음")

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
