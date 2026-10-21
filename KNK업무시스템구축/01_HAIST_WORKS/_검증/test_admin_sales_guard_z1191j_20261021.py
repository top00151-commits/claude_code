# -*- coding: utf-8 -*-
"""z1191j 시험 — 매출 화면 문지기(_s1_guard · 매출 경로 23곳)·매출 삭제(can_delete_sales)도 관리자는 체크대로
   (z1191g 빈틈 · 세션 05 2026-10-21 18:25 전달 「체크 없는 관리자가 매출 화면 23개를 직접 주소로 열 수 있다」)
  §1 판정: _s1_guard·can_delete_sales — 체크 없는 관리자 거짓 · 매출 등록 체크 관리자 참 · 대표·임원 참 · 팀원은 체크대로(그대로)
  §2 경로(임시 DB · TestClient): 매출 화면 11곳 — 체크 없는 관리자 → /home(303) · 매출 보기만 관리자 → /home ·
     매출 등록 관리자·대표·임원·매출 등록 팀원 → 열림(303 /home 아님) · 알림 확인 API 401/열림
  §3 원문: _s1_guard·can_delete_sales 에 관리자 자동 허용 없음
"""
import contextlib
import io
import os
import re
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191j-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191j_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("name_vi", "TEXT"), ("dept_code", "TEXT"), ("rank", "TEXT"),
                     ("team_id", "INTEGER"), ("password_version", "INTEGER DEFAULT 1")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "entity" not in {r[1] for r in conn.execute("PRAGMA table_info(teams)")}:
        conn.execute("ALTER TABLE teams ADD COLUMN entity TEXT")
    conn.execute("INSERT INTO teams (name, entity, code, display_order) VALUES ('가상총괄','KOR','ZJHQ',0)")
    HQ = conn.execute("SELECT MAX(id) FROM teams").fetchone()[0]
    conn.execute("INSERT INTO teams (name, entity, code, display_order) VALUES ('가상총괄','VN','ZJVH',10)")
    VH = conn.execute("SELECT MAX(id) FROM teams").fetchone()[0]
    PEOPLE = [  # 사번, 역할, 팀, (매출보기, 매출등록, 자재보기, 자재등록)
        ("J900", "ceo", HQ, (1, 1, 1, 1)),
        ("J910", "executive", HQ, (0, 0, 0, 0)),
        ("J920", "admin", VH, (0, 0, 0, 0)),     # 이용식 법인장 같은 경우
        ("J921", "admin", HQ, (1, 1, 0, 0)),     # 매출 등록 체크 관리자
        ("J922", "admin", HQ, (1, 0, 0, 0)),     # 매출 보기만 관리자
        ("J930", "member", HQ, (1, 1, 0, 0)),    # 매출 등록 팀원
        ("J931", "member", HQ, (1, 0, 0, 0)),    # 매출 보기만 팀원
    ]
    U = {}
    for sb, role, tm, fl in PEOPLE:
        conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, "
                     "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) VALUES (?,?,?,?,'x',1,1,?,?,?,?,?)",
                     ("가상" + sb, role, sb, sb, tm) + fl)
        U[sb] = dict(conn.execute("SELECT * FROM users WHERE employee_no=?", (sb,)).fetchone())

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


class _Req:
    pass


def guard(sb):
    M.get_user = lambda request, _u=U[sb]: _u
    return M._s1_guard(_Req()) is not None


print("=" * 78)
print("§1 판정")
print("=" * 78)
g = {sb: guard(sb) for sb in U}
check("1 매출 화면 문지기: 체크 없는 관리자·매출 보기만 관리자 = 막힘", g["J920"] is False and g["J922"] is False, g)
check("   매출 등록 관리자·대표·임원·매출 등록 팀원 = 통과 · 매출 보기만 팀원 = 막힘(그대로)",
      g["J921"] and g["J900"] and g["J910"] and g["J930"] and g["J931"] is False, g)
d = {sb: bool(M.can_delete_sales(U[sb])) for sb in U}
check("2 매출 삭제: 체크 없는 관리자 = 못 함 · 매출 등록 관리자 = 함 · 대표·임원 = 함 · 매출 등록 팀원 = 함(그대로)",
      d["J920"] is False and d["J922"] is False and d["J921"] and d["J900"] and d["J910"] and d["J930"] and d["J931"] is False, d)

print()
print("=" * 78)
print("§2 경로 — 매출 화면 9곳 + 저장 주소 2곳")
print("=" * 78)
PAGES = ["/sales/quotations", "/sales/orders", "/sales/production", "/sales/shipments-receipts",
         "/sales/dashboard", "/sales/forecast", "/sales/outstanding", "/sales/aging", "/sales/quotes/new"]
POSTS = ["/sales/shipments", "/sales/receipts"]   # 저장만 받는 주소 — 막힘만 본다(열리는 쪽은 저장이 일어나므로 안 누름)


def hit(sb, path, method="get"):
    M.get_user = lambda request, _u=U[sb]: _u
    with contextlib.redirect_stdout(io.StringIO()):
        r = getattr(cl, method)(path)
    return r.status_code, r.headers.get("location", "")


home = (303, "/home")
for sb, want_open in (("J920", False), ("J922", False), ("J921", True), ("J900", True), ("J910", True), ("J930", True)):
    res = {p: hit(sb, p) for p in PAGES}
    if want_open:
        bad = {p: v for p, v in res.items() if v == home or v[0] >= 500}
        check("3 %s(%s · 매출 %s) — 매출 화면 9곳 열림(홈으로 안 감·오류 없음)" % (sb, U[sb]["role"], "".join(str(U[sb][k]) for k in ("can_view_sales", "can_use_sales"))),
              not bad, bad)
    else:
        res.update({p + " (POST)": hit(sb, p, "post") for p in POSTS})
        bad = {p: v for p, v in res.items() if not (v == home or (p.endswith("(POST)") and v[0] == 401))}   # 저장 주소는 막히면 401
        check("3 %s(%s · 매출 %s) — 매출 화면 9곳 홈으로(303) · 저장 주소 2곳 401" % (sb, U[sb]["role"], "".join(str(U[sb][k]) for k in ("can_view_sales", "can_use_sales"))),
              not bad, bad)
a0, a1 = hit("J920", "/sales/alerts/check", "post"), hit("J921", "/sales/alerts/check", "post")
check("4 매출 알림 확인 API: 체크 없는 관리자 401 · 매출 등록 관리자 200", a0[0] == 401 and a1[0] == 200, (a0, a1))

print()
print("=" * 78)
print("§3 원문")
print("=" * 78)
src = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
s1 = re.search(r"def _s1_guard\(req: Request\):.*?(?=\n\n)", src, re.S).group(0)
cd = re.search(r"def can_delete_sales\(user\) -> bool:.*?(?=\n\n)", src, re.S).group(0)
check("5 _s1_guard·can_delete_sales 코드에 관리자 자동 허용 없음",
      '"admin"' not in s1.split('"""', 2)[-1] and '"admin"' not in cd.split('"""', 2)[-1])

print()
print("결과: %d개 중 실패 %d" % (OK + FAIL, FAIL))
sys.exit(1 if FAIL else 0)
