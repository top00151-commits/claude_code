# -*- coding: utf-8 -*-
"""z1191z106 시험 — 페이지 제목 띠 고정(대표 11-22 「타이틀 제목 부분은 스크롤 동작에서 제외 … 모두 동일하게」)
  §1 모든 화면 틀(chrome.html)에 고정 조각 한 번 · 매출·자재·관리 화면 모두
  §2 조각 내용: 제목 띠 sticky top:0(본문 기준) · 폰 폭 제외 · 배경은 우선순위 0(:where) · 본문 위 여백만큼 올려 붙임
     · 본문이 스크롤하는 다른 고정(표 머리줄·옆 칸)은 제목 높이만큼 내림 · 두 번째 제목 띠는 고정 안 함
  ※ 실제 스크롤 모양은 운영 자료 사본 + 브라우저로 107개 화면을 재서 확인(작업기록 · scratchpad/z106/survey.py)
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z106-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z106_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, "
              "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상대표', 'ceo', 'Z106', 'Z106', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    CEO = dict(c.execute("SELECT * FROM users WHERE employee_no='Z106'").fetchone())
import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
M.get_user = lambda request: CEO
cl = TestClient(M.app)
OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", label)
    else:
        FAIL += 1; print("  ❌", label, "" if got is None else ("→ %r" % (got,))[:300])


print("§1 모든 화면 틀에 한 번")
for u in ("/sales", "/projects/new", "/projects", "/sales/receipts-check", "/sales/quotations", "/home", "/stock/adjust", "/customers"):
    r = cl.get(u)
    h = r.text
    check("%s: 200 · 고정 조각 한 번" % u, r.status_code == 200 and h.count("window.__knkStickyHeadZ106 = 1") == 1
          and ".main .knk-page-head:not(.knk-head-free), .main .page-head:not(.knk-head-free)" in h, (r.status_code, h.count("__knkStickyHeadZ106")))

print("§2 조각 내용")
src = io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "knk_sticky_head.html"), encoding="utf-8").read()
css = src[src.find("<style>"):src.find("</style>")]
check("제목 띠 = sticky · top:0 · z-index", "position: sticky; top: 0; z-index: 40;" in css)
check("폰 폭(767px 이하) 제외", "@media (min-width: 768px)" in css and "matchMedia('(min-width: 768px)')" in src)
check("배경·줄은 우선순위 0(:where) — 화면이 정한 배경 그대로", ":where(.main) :where(.knk-page-head, .page-head)" in css)
check("넓은 화면(본문 스크롤) = 본문 위 여백만큼 올려 붙임 · 좁은 창(몸통 스크롤 768~1023px) = 위 상단바 바로 아래",
      "h.style.top = (mainScrolls ? -pt : off) + 'px'" in src and "function shellBottom" in src and "/(auto|scroll)/.test(getComputedStyle(m).overflowY)" in src)
check("다른 고정(표 머리줄·옆 칸) = 원래 top + 제목 높이 · 중간 칸이 스크롤하면 그대로",
      "stuck[j].style.top = (mainScrolls ? (t0 + Math.max(0, hh - pt)) : (Math.max(t0, off) + hh)) + 'px'" in src and "function scrollsInside" in src)
check("자체 고정 틀 화면(권한 일괄 z1191i)은 건드리지 않음", "function ownFrame" in src and "if (!h) {" in src)
check("두 번째 제목 띠는 고정 안 함", "hs[k].classList.add('knk-head-free')" in src)
check("!important 없음", "!important" not in css)
print("\n결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
