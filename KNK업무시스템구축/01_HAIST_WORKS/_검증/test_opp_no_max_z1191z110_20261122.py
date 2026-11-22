# -*- coding: utf-8 -*-
"""z1191z110 시험 — 영업 기회 번호 = 그 달 가장 큰 번호 + 1 (대표 11-22) · 지울 때 참여자 기록도 지움 · 빈 목록 안내 글
  §1 번호: 비었으면 001 · 001·002·003 중 002 지운 뒤 새 등록 = 004(예전엔 003 으로 겹침) · 형식이 다른 번호는 무시
  §2 삭제: 미팅·제안서 참여자(sales_opp_people)도 같이 지움 · 살아 있는 프로젝트로 승격된 건은 안 지워짐(그대로)
  §3 빈 목록 안내 = 왼쪽 메뉴 🆕 등록 → 🎯 영업 기회(z98 뒤 「+ 새 영업 기회」 단추는 없음)
  §4 삭제 = 대표 · 기술영업팀장(부서 정보의 팀장 지정 · 공용 _team_leader_id)만 · 화면 단추·서버 둘 다
"""
import contextlib
import io
import os
import re
import sys
import tempfile
from datetime import datetime

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z110-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z110_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
from app.migrations.m_z416_sales_opportunity import migrate as _m416   # noqa: E402
_m416(D.DB_PATH)
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, "
                 "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상대표', 'ceo', 'Z110', 'Z110', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    CEO = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z110'").fetchone())

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M.get_user = lambda request: CEO
cl = TestClient(M.app)
OK = FAIL = 0
PREF = "OPP-%s-" % datetime.now().strftime("%y%m")


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ✅", label)
    else:
        FAIL += 1
        print("  ❌", label, "" if got is None else ("→ %r" % (got,))[:400])


def new(title, people=None):
    data = {"title": title, "status": "active", "stage": "미팅", "people_form": "1"}
    if people:
        data["meeting_people"] = [str(x) for x in people]
    r = cl.post("/sales/opportunities", data=data, follow_redirects=False)
    oid = int(re.search(r"/sales/opportunities/(\d+)", r.headers["location"]).group(1))
    with D.db_session() as c:
        return oid, c.execute("SELECT opp_no FROM sales_opportunities WHERE id=?", (oid,)).fetchone()[0]


print("§1 번호")
h = cl.get("/sales/opportunities").text
check("§3 빈 목록 안내 = 왼쪽 메뉴 🆕 등록 → 🎯 영업 기회", "왼쪽 메뉴 🆕 등록 → 🎯 영업 기회에서 시작하세요" in h and "[+ 새 영업 기회]" not in h)
a = new("가상 하나")
b = new("가상 둘", people=[CEO["id"]])
c3 = new("가상 셋")
check("001 · 002 · 003", [a[1], b[1], c3[1]] == [PREF + "001", PREF + "002", PREF + "003"], [a[1], b[1], c3[1]])
r = cl.post("/sales/opportunities/%d/delete" % b[0], follow_redirects=False)
with D.db_session() as c:
    gone = c.execute("SELECT COUNT(*) FROM sales_opportunities WHERE id=?", (b[0],)).fetchone()[0] == 0
    ppl = c.execute("SELECT COUNT(*) FROM sales_opp_people WHERE opp_id=?", (b[0],)).fetchone()[0]
check("§2 002 삭제 · 참여자 기록도 지움", gone and ppl == 0, (gone, ppl))
d = new("가상 넷")
check("002 지운 뒤 새 등록 = 004(겹치지 않음)", d[1] == PREF + "004", d[1])
with D.db_session() as c:
    c.execute("INSERT INTO sales_opportunities (opp_no, title) VALUES (?, '형식 다름')", (PREF + "가나",))
    check("형식이 다른 번호는 무시 → 005", M._gen_opp_no(c) == PREF + "005", M._gen_opp_no(c))

print("§2 살아 있는 프로젝트로 승격된 건")
with D.db_session() as c:
    c.execute("INSERT INTO projects (mgmt_code, name) VALUES ('991T2611', '가상 승격 프로젝트')")
    pid = c.execute("SELECT id FROM projects WHERE mgmt_code='991T2611'").fetchone()[0]
    c.execute("UPDATE sales_opportunities SET promoted_project_id=?, status='won' WHERE id=?", (pid, d[0]))
cl.post("/sales/opportunities/%d/delete" % d[0], follow_redirects=False)
with D.db_session() as c:
    still = c.execute("SELECT COUNT(*) FROM sales_opportunities WHERE id=?", (d[0],)).fetchone()[0]
check("살아 있는 프로젝트로 승격된 건은 안 지워짐", still == 1)
h = cl.get("/sales/opportunities/%d" % d[0]).text
check("그 건 상세에는 삭제 단추가 없음", "/delete\"" not in h)

print("§4 삭제 권한 = 대표 · 기술영업팀장만(대표 11-22)")
with D.db_session() as c:
    tc = {r[1] for r in c.execute("PRAGMA table_info(teams)")}
    if not c.execute("SELECT 1 FROM teams WHERE id=1").fetchone():
        c.execute("INSERT INTO teams (id, code, name) VALUES (1, '01', '기술영업팀')" if "code" in tc else "INSERT INTO teams (id, name) VALUES (1, '기술영업팀')")
    for emp, nm in (("Z111", "가상영업원"), ("Z112", "가상영업팀장")):
        c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, "
                  "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                  "VALUES (?, 'member', ?, ?, 'sso_only_no_local_password', 1, 1, 1, 1, 1, 0, 0)", (nm, emp, emp))
    MEM = dict(c.execute("SELECT * FROM users WHERE employee_no='Z111'").fetchone())
    LEAD = dict(c.execute("SELECT * FROM users WHERE employee_no='Z112'").fetchone())
    c.execute("UPDATE teams SET leader_id=? WHERE id=1", (LEAD["id"],))
e = new("가상 권한")
M.get_user = lambda request: MEM
h = cl.get("/sales/opportunities/%d" % e[0]).text
check("영업 담당(팀장 아님): 삭제 단추 없음 · 안내 글", "/delete\"" not in h and "삭제는 기술영업팀장 · 대표만 할 수 있습니다" in h)
r = cl.post("/sales/opportunities/%d/delete" % e[0], follow_redirects=False)
with D.db_session() as c:
    alive = c.execute("SELECT COUNT(*) FROM sales_opportunities WHERE id=?", (e[0],)).fetchone()[0]
check("영업 담당이 주소로 직접 보내도 안 지워짐 · 안내", alive == 1 and "del_err=perm" in r.headers.get("location", ""), r.headers.get("location"))
check("안내 띠", "영업 기회 삭제는 <b>기술영업팀장 · 대표</b>만" in cl.get(r.headers["location"]).text)
M.get_user = lambda request: LEAD
check("기술영업팀장: 삭제 단추 있음", "/sales/opportunities/%d/delete" % e[0] in cl.get("/sales/opportunities/%d" % e[0]).text)
cl.post("/sales/opportunities/%d/delete" % e[0], follow_redirects=False)
with D.db_session() as c:
    alive = c.execute("SELECT COUNT(*) FROM sales_opportunities WHERE id=?", (e[0],)).fetchone()[0]
check("기술영업팀장은 지울 수 있음", alive == 0)
with D.db_session() as c:
    c.execute("UPDATE teams SET leader_id=NULL WHERE id=1")
    check("팀장 지정이 없으면 대표만(팀원 아무도 안 됨)", M._z110_can_del_opp(c, LEAD) is False and M._z110_can_del_opp(c, CEO) is True)
M.get_user = lambda request: CEO

print("\n결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
