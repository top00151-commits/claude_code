# -*- coding: utf-8 -*-
"""z1191z81 시험 (대표 2026-11-19 「부서는 우리부서만 볼수있는 주소록(예, 구매팀 A사원이 등록하면 구매팀 전체가 확인 가능), 전사부분은 각 주소록에서
  접근이 가능한 담당자가 해당 주소록을 "전사"로 이동 시키면 전사 누구나 볼수있는 주소 · 총괄 부서원은 각 부서 주소록들도 다 볼수있게 ·
  각 부서에 주소록 등록은 개인주소록에 주소록을 복사 … 직접 등록 또는 협력사,고객사 초대」 + 「추가로 전사 주소록도 직접 등록 가능하도록」)
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z81-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z81_")
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
    TZ = ins(c, "teams", {"name": "총괄", "code": "00", "display_order": -1})
    UZ = user("총괄님", "T770", TZ, "010-0000-1111")
    UD = user("라구매", "T774", T2, "010-0000-2222")


def ids(h):
    return sorted(int(x) for x in re.findall(r'<tr data-id="(\d+)"', h))


def vis_of(cid):
    with D.db_session() as c:
        r = c.execute("SELECT visibility, share_team_id, created_by FROM shared_contacts WHERE id=?", (cid,)).fetchone()
        return tuple(r) if r else None


print("§1 부서 = 우리 부서만(구매팀 A가 등록 → 구매팀 전체)")
CUR["u"] = UD
check(C2 in ids(q(cl.get, "/contacts?tab=dept").text) and A3 not in ids(q(cl.get, "/contacts").text), "라구매(구매팀): 다구매가 등록한 구매팀 연락처 보임 · 영업팀 것은 안 보임")
check(q(cl.get, "/contacts/%d" % A3).status_code == 303, "다른 부서 연락처 상세는 못 열음")

print("§2 총괄 = 모든 부서 주소록")
CUR["u"] = UZ
hz = q(cl.get, "/contacts?tab=dept").text
check(set(ids(hz)) == {A3, C2}, "총괄님: 영업팀·구매팀 부서 주소록 모두", ids(hz))
check("(모든 부서 · 총괄)" in hz and "본사 총괄은 본사·법인 모든 부서공유" in hz, "책갈피·설명에 「모든 부서 · 총괄」(z1191z82: 본사 총괄 글)")
chips = re.findall(r'class="cx-corpf[^"]*" href="/contacts\?tab=dept[^"]*">([^<]+?) <span class="n">(\d+)</span>', hz)
check(chips == [("모든 부서", "2"), ("가상구매팀", "1"), ("가상영업팀", "1")] or chips == [("모든 부서", "2"), ("가상영업팀", "1"), ("가상구매팀", "1")], "부서별 고르기 단추(모든 부서 · 부서마다 개수)", chips)
check(ids(q(cl.get, "/contacts?tab=dept&team=%d" % T2).text) == [C2], "구매팀만 골라 보기")
check(q(cl.get, "/contacts/%d" % C2).status_code == 200 and ids(q(cl.get, "/contacts?tab=private").text) == [], "총괄도 남의 개인 연락처는 못 봄 · 부서 연락처 상세는 열림")
check('<span class="src-pill vis-dept" title="가상구매팀 부서공유">👥 부서공유 · 가상구매팀</span>' in hz, "공유 칸 = 「👥 부서공유」(총괄은 부서 이름도 · 가상구매팀)")

print("§3 개인 → 우리 부서에 복사(개인 것은 남김)")
CUR["u"] = UA
r = q(cl.post, "/contacts/bulk-copy-dept", json={"ids": [A1, A2, A4]}).json()
check(r["ok"] and r["copied"] == 2 and r["skipped"] == 1 and "내 개인 연락처는 그대로" in r["message"], "내 개인 2명 복사 · 전사 것(최전사)은 건너뜀", r)
check(vis_of(A1)[0] == "private" and vis_of(A2)[0] == "private", "원래 개인 연락처는 그대로 개인")
new = [x["id"] for x in r["results"] if x["status"] == "copied"]
check(all(vis_of(n_) == ("dept", T1, UA["id"]) for n_ in new), "복사본 = 영업팀 부서 · 등록자 = 가영업", [vis_of(n_) for n_ in new])
CUR["u"] = UB
check(set(new) <= set(ids(q(cl.get, "/contacts?tab=dept").text)), "같은 부서 나영업에게 바로 보임")
CUR["u"] = UA
r = q(cl.post, "/contacts/bulk-copy-dept", json={"ids": [A2]}).json()
check(r["copied"] == 0 and r["exists"] == 1, "다시 복사 → 이미 있음(두 번 안 만듦)", r)
CUR["u"] = UN
with D.db_session() as c:
    N1 = ins(c, "shared_contacts", {"name": "부서없는이", "created_by": UN["id"], "visibility": "private"})
r = q(cl.post, "/contacts/bulk-copy-dept", json={"ids": [N1]})
check(r.status_code == 400 and "소속 부서가 없어" in r.json()["message"], "부서 없는 사람 → 안내")

print("§4 전사로 이동 = 그 연락처를 볼 수 있는 담당자(부서원)도")
CUR["u"] = UB
hd = q(cl.get, "/contacts/%d" % A3).text
check("z81ToCompany()" in hd and "🌐 전사공유로 이동" in hd, "나영업(등록자 아님)도 우리 부서공유 연락처 상세에 「🌐 전사공유로 이동」")
r = q(cl.post, "/contacts/%d/share" % A3, data={"visibility": "private"})
check(r.status_code == 403, "부서원이 남의 것을 🔒 개인으로는 못 바꿈")
r = q(cl.post, "/contacts/%d/share" % A3, data={"visibility": "company"}).json()
check(r["ok"] and vis_of(A3)[0] == "company", "나영업이 영업팀 부서 연락처를 🌐 전사로 이동")
CUR["u"] = UC
check(A3 in ids(q(cl.get, "/contacts?tab=company").text), "다른 부서(다구매)도 전사에서 보임")
CUR["u"] = UB
r = q(cl.post, "/contacts/bulk-share", json={"ids": new + [C2], "visibility": "company"}).json()
check(r["done"] == 2 and r["skipped"] == 1, "여러 명 전사 이동: 우리 부서 것 2명 · 다른 부서 것(구매팀)은 그대로", r)
CUR["u"] = UZ
r = q(cl.post, "/contacts/bulk-share", json={"ids": [C2], "visibility": "company"}).json()
check(r["done"] == 1 and vis_of(C2)[0] == "company", "총괄은 다른 부서 연락처도 전사로 이동", r)

print("§5 부서·전사 바로 등록")
CUR["u"] = UA
f1 = q(cl.get, "/contacts/new?vis=company").text
f2 = q(cl.get, "/contacts/new?vis=dept").text
f3 = q(cl.get, "/contacts/new").text
check('value="company" checked' in f1 and 'value="dept" checked' in f2 and 'value="private" checked' in f3, "?vis=company → 🌐 전사 · ?vis=dept → 👥 부서 · 없으면 🔒 개인 골라져 있음")
check('href="/contacts/new?vis=company">＋ 전사공유 연락처 등록</a>' in q(cl.get, "/contacts?tab=company").text, "🌐 전사공유 책갈피의 단추 = 「＋ 전사공유 연락처 등록」")
check('href="/contacts/new?vis=dept">＋ 부서공유 연락처 등록</a>' in q(cl.get, "/contacts?tab=dept").text, "👥 부서공유 책갈피의 단추 = 「＋ 부서공유 연락처 등록」")
h_all = q(cl.get, "/contacts").text
check(">👥 부서공유<" in h_all.replace("<small", "<").split("<span class=\"n\">")[2] or "👥 부서공유" in h_all, "책갈피 이름 = 👥 부서공유 · 🌐 전사공유")
check("🌐 전사공유<span class=\"n\">" in h_all and ">🌐 전사<span" not in h_all, "🌐 전사공유 책갈피(옛 「🌐 전사」 없음)")
f_ = q(cl.get, "/contacts/new").text
check("<b>👥 부서공유</b>" in f_ and "<b>🌐 전사공유</b>" in f_, "등록 화면 공유 범위 = 👥 부서공유 · 🌐 전사공유")
r = q(cl.post, "/contacts", data={"name": "바로전사", "mobile": "010-1212-3434", "visibility": "company"})
nid = int(r.headers["location"].rsplit("/", 1)[-1])
check(vis_of(nid)[0] == "company", "바로 등록한 전사 연락처 = 🌐 전사")
CUR["u"] = UD
check(nid in ids(q(cl.get, "/contacts?tab=company").text), "다른 부서 직원에게도 보임")

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
