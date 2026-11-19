# -*- coding: utf-8 -*-
"""z1191z79 시험 (대표 2026-11-19 「우리회사직원은 본사,법인 인원을 따로 볼수있게 해줘.」)
  연락처 「🏢 우리 회사 직원」 = 전체 · KNK 본사 · KNK VINA 법인 · 임시 DB · 가짜 자료 · 운영 아님
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z79-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z79_")
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


with D.db_session() as c:   # 법인 칸이 비었지만 사번이 VN… 인 사람(운영에 39명 그런 경우) · 본사 사번 숫자
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, phone, entity, rank) "
              "VALUES ('득 응옥', 'member', 'VN772', 'VN772', 'x', 1, 1, ?, '0987 654 321', NULL, '프로')", (T2,))
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, phone, entity, rank) "
              "VALUES ('본사신입', 'member', '777', '777', 'x', 1, 1, ?, '010-7777-0000', NULL, '프로')", (T1,))


def names(h):
    return sorted(re.findall(r"<tr><td><b>([^<]+)</b></td>", h))


def corp_counts(h):
    return re.findall(r'class="cx-corpf[^"]*" href="/contacts\?tab=staff[^"]*">[^<]*<span class="n">(\d+)</span>', h)


print("§1 본사 · 법인 따로 보기")
CUR["u"] = UA
h = q(cl.get, "/contacts?tab=staff").text
check(corp_counts(h) == ["7", "5", "2"], "단추 「전체 7 · KNK 본사 5 · KNK VINA 법인 2」", corp_counts(h))
check('class="cx-corpf on" href="/contacts?tab=staff">전체' in h and "KNK 본사 5 · KNK VINA 법인 2" in h, "처음은 전체 · 설명에 본사·법인 인원")
hk = q(cl.get, "/contacts?tab=staff&corp=kr").text
check(names(hk) == sorted(["가영업", "나영업", "다구매", "부서없음", "본사신입"]) and "KNK VINA</span>" not in hk, "KNK 본사 = 본사 직원만", names(hk))
hv = q(cl.get, "/contacts?tab=staff&corp=vn").text
check(names(hv) == sorted(["반 끄엉", "득 응옥"]), "KNK VINA 법인 = 법인 직원만(법인 칸이 비어도 사번 VN… 이면 법인)", names(hv))
check('class="cx-corpf on" href="/contacts?tab=staff&corp=vn"' in hv, "고른 단추가 켜짐")
check(names(q(cl.get, "/contacts?tab=staff&corp=zz").text) == names(h), "이상한 값은 전체")

print("§2 찾기 · 휴대폰 저장도 고른 쪽만")
hs = q(cl.get, "/contacts", params={"tab": "staff", "corp": "vn", "q": "321"}).text
check(names(hs) == ["득 응옥"] and '<input type="hidden" name="corp" value="vn">' in hs, "법인에서 찾기(번호 뒷자리) · 찾은 뒤에도 법인 그대로", names(hs))
check(names(q(cl.get, "/contacts", params={"tab": "staff", "corp": "kr", "q": "321"}).text) == [], "본사에서 찾으면 법인 사람은 안 나옴")
check('href="/contacts/vcards.vcf?tab=staff&amp;corp=vn"' in hv or 'href="/contacts/vcards.vcf?tab=staff&corp=vn"' in hv, "법인 화면의 휴대폰 저장 링크 = 법인만")
v = q(cl.get, "/contacts/vcards.vcf?tab=staff&corp=vn")
check(v.status_code == 200 and v.text.count("BEGIN:VCARD") == 2 and "FN:득 응옥" in v.text and "가영업" not in v.text, "법인 vCard = 법인 2명", v.text.count("BEGIN:VCARD"))
check("KNK_VINA" in v.headers.get("content-disposition", ""), "파일 이름 직원연락처_KNK_VINA.vcf")
v2 = q(cl.get, "/contacts/vcards.vcf?tab=staff&corp=kr")
check(v2.text.count("BEGIN:VCARD") == 5 and "반 끄엉" not in v2.text, "본사 vCard = 본사 5명")
check(q(cl.get, "/contacts/vcards.vcf?tab=staff").text.count("BEGIN:VCARD") == 7, "전체 vCard = 7명")

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
