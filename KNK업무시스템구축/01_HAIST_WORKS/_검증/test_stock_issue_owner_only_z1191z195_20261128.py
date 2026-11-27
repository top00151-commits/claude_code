# -*- coding: utf-8 -*-
"""z1191z195 (대표 11-27 「자재출고 화면은 못 들어가게 비활성화해 · 거기는 나만 들어갈 수 있게」)
   재고 출고 화면(/stock/issue · /stock/issues · 승인) = 대표 김정락(users.id 85)만.
   ① 다른 사람(관리자·물류 쓰기 권한·다른 대표 역할 계정 포함) = 열기·저장 모두 /logistics?no_perm= 또는 403
   ② 85 = 목록 열림 ③ 메뉴·자재구매 홈 카드 = 85 에게만"""
import contextlib, io, os, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z195-test-only-not-a-real-key"   # 시험용 가짜 값
import app.database as D   # noqa: E402
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_z195_"), "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
OK = FAIL = 0


def check(cond, msg, got=None):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", msg)
    else:
        FAIL += 1; print("  ❌", msg, " ←", got)


with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    cols = {r[1] for r in c.execute("PRAGMA table_info(users)")}

    def mk(uid, name, role):
        d = {"id": uid, "name": name, "role": role, "login_id": "u%d" % uid, "password": "sso_only_no_local_password", "is_active": 1,
             "password_version": 1, "can_view_logistics": 1, "can_use_logistics": 1, "can_view_sales": 1, "can_use_sales": 1}
        d = {k: v for k, v in d.items() if k in cols}
        c.execute("INSERT INTO users (%s) VALUES (%s)" % (",".join(d), ",".join("?" * len(d))), list(d.values()))
        return dict(c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
    OWNER = mk(85, "가상대표", "ceo")
    OTHER_CEO = mk(2, "다른대표역할", "ceo")
    ADMIN = mk(30, "가상관리자", "admin")

import app.main as M   # noqa: E402
from fastapi.testclient import TestClient   # noqa: E402
CUR = {"u": None}
M.get_user = lambda request: CUR["u"]
with contextlib.redirect_stdout(io.StringIO()):
    try:
        M.startup()
    except Exception as _e:
        print("startup:", _e)
cl = TestClient(M.app)

print("§1 다른 사람 = 막힘")
for who, u in (("다른 대표 역할(2)", OTHER_CEO), ("관리자(30)", ADMIN)):
    CUR["u"] = u
    M._s2_guard = lambda req, _u=u: _u
    r1 = cl.get("/stock/issues", follow_redirects=False)
    r2 = cl.get("/stock/issue", follow_redirects=False)
    r3 = cl.post("/stock/issues", data={"part_id": "1", "qty": "1"}, follow_redirects=False)
    r4 = cl.post("/stock/issue", data={"part_id": "1", "quantity": "1"}, follow_redirects=False)
    r5 = cl.post("/stock/issues/1/approve", follow_redirects=False)
    check(r1.status_code == 303 and "no_perm=stock_issue" in r1.headers.get("location", ""), who + " 출고 목록 열기 → 막힘", (r1.status_code, r1.headers.get("location")))
    check(r2.status_code == 303 and "no_perm=stock_issue" in r2.headers.get("location", ""), who + " 직접 출고 화면 → 막힘", (r2.status_code, r2.headers.get("location")))
    check(r3.status_code == 403, who + " 출고 등록 저장 → 403", r3.status_code)
    check(r4.status_code == 303 and "no_perm=stock_issue" in r4.headers.get("location", ""), who + " 직접 출고 저장 → 막힘", (r4.status_code, r4.headers.get("location")))
    check(r5.status_code == 303 and "no_perm=stock_issue" in r5.headers.get("location", ""), who + " 출고 승인 → 막힘", (r5.status_code, r5.headers.get("location")))

print("§2 대표(85) = 열림")
CUR["u"] = OWNER
M._s2_guard = lambda req: OWNER
r = cl.get("/stock/issues", follow_redirects=False)
check(r.status_code == 200, "대표 출고 목록 열림", r.status_code)

print("§3 메뉴·카드")
t = open(os.path.join(ROOT, "app", "templates", "_v5_partials", "chrome.html"), encoding="utf-8").read()
check("{% if user and (user.id|int) == 85 %}{{ a('/stock/issues'" in t, "왼쪽 메뉴 출고 = 85 에게만")
h = open(os.path.join(ROOT, "app", "templates", "logistics_home.html"), encoding="utf-8").read()
i = h.find('href="/stock/issues"')
check(i > 0 and "{% if user and (user.id|int) == 85 %}" in h[max(0, i - 300):i], "자재구매 홈 출고 카드 = 85 에게만")
print()
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
