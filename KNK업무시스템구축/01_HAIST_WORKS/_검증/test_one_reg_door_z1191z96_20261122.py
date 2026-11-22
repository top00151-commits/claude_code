# -*- coding: utf-8 -*-
"""z1191z96 시험 — 등록 입구 하나로 (대표 11-22 「먼저 등록 중복만 정리」 · 작업 일정표 「＋ 신규 등록」 없애기)
  §1 🆕 등록 첫 화면: 「무엇을 등록하나요?」 · 카드 6개(검사기·자동화·라이프밸류·기타·소모품·🤝 고객사) · 프로젝트 탭 줄 없음
  §2 다른 화면에 등록 입구 없음: 📋 프로젝트 · 📒 관리번호대장 · 📋 제작요청서목록 탭 · 📅 작업 일정표 단추 · 🤝 고객사 목록 단추
     — 그 자리에는 「＋ 등록은 왼쪽 메뉴 🆕 등록에서」 안내 글(누르는 단추 아님)
  §3 메뉴 불: 등록 화면들(프로젝트 등록 폼 · 소모품 · 고객사 새 등록)에서 「🆕 등록」 · 고객사 새 등록 길 표시 「🆕 등록 · 고객사」
  §4 고객사 새 등록은 그대로 됨(주소 /customers/new)
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z96-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z96_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                     ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                     ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if not conn.execute("SELECT 1 FROM teams WHERE id=1").fetchone():
        tcols = {r[1] for r in conn.execute("PRAGMA table_info(teams)")}
        if "code" in tcols:
            conn.execute("INSERT INTO teams (id, code, name) VALUES (1, '01', '기술영업팀')")
        else:
            conn.execute("INSERT INTO teams (id, name) VALUES (1, '기술영업팀')")
    conn.execute("INSERT OR IGNORE INTO field_access_policy (category, team_id) VALUES ('sales_amount', 1)")
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, "
                 "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상영업', 'member', 'Z961', 'Z961', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 0, 0)")
    SALES = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z961'").fetchone())

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M.get_user = lambda request: SALES
cl = TestClient(M.app)
OK = FAIL = 0
HINT = "＋ 등록은 왼쪽 메뉴 <b>🆕 등록</b>에서"


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def main_part(h):
    """왼쪽 메뉴(chrome) 밖 = 화면 본문만(메뉴의 🆕 등록 링크는 빼고 본다)."""
    i = h.find('<main')
    return h[i:] if i >= 0 else h


print("§1 🆕 등록 첫 화면")
h = q(cl.get, "/projects/new").text
check("제목 「🆕 등록 — 무엇을 등록하나요?」", "무엇을 등록하나요?" in h)
cards = re.findall(r'<a class="pc-card[^"]*" href="([^"]+)"', h)
# z1191z98: 🎯 영업 기회 · 📋 견적서 카드가 뒤에 더해짐(새로 만들기는 모두 🆕 등록)
check("카드 = 검사기·자동화·라이프밸류·기타·소모품·고객사 (+ z98 영업 기회·견적서)",
      [c.split("?")[0] for c in cards] == ["/projects/quick", "/projects/quick", "/projects/quick", "/projects/new", "/consumables/new", "/customers/new",
                                           "/sales/opportunities/new", "/sales/quotations"], cards)   # z1191z105: 견적서 카드 → 견적 관리
check("프로젝트 탭 줄(전체 목록·제작요청서목록·관리번호대장) 없음", 'href="/prod-requests"' not in main_part(h) and 'href="/projects/ledger"' not in main_part(h))

print("§2 다른 화면에 등록 입구 없음")
for path, name in (("/projects", "📋 프로젝트"), ("/projects/ledger", "📒 관리번호대장"), ("/prod-requests", "📋 제작요청서목록")):
    r = q(cl.get, path)
    m = main_part(r.text)
    check("%s: 화면 안 /projects/new 링크 없음(탭·빈 목록 단추)" % name, r.status_code == 200 and 'href="/projects/new"' not in m, (r.status_code, m.count('href="/projects/new"')))
mp = main_part(q(cl.get, "/projects").text)
check("📋 프로젝트: 탭 줄 오른쪽에 안내 글(단추 아님)", HINT in mp and "reg-hint-z96" in mp)
hs = q(cl.get, "/sales/schedule").text
check("📅 작업 일정표: 「＋ 신규 등록」 단추 없음 · 안내 글", 'onclick="openRegModal()"' not in hs and HINT in hs, ('openRegModal()"' in hs, HINT in hs))
hc = q(cl.get, "/customers").text
mc = main_part(hc)
check("🤝 고객사 목록: 「＋ 고객사 등록」 단추 없음 · 「새 고객사는 🆕 등록 → 🤝 고객사」",
      'href="/customers/new"' not in mc and "＋ 새 고객사는 왼쪽 메뉴 <b>🆕 등록 → 🤝 고객사</b>" in mc, mc.count('href="/customers/new"'))

print("§3 메뉴 불 · 길 표시")
for path in ("/projects/new", "/projects/quick?biz_div=T", "/consumables/new", "/customers/new"):
    hh = q(cl.get, path).text
    mm = re.search(r'<a class="sb-item active" href="([^"]+)"', hh)
    check("%s → 메뉴 「🆕 등록」에 불" % path, bool(mm) and mm.group(1) == "/projects/new", mm.group(1) if mm else None)
hn = q(cl.get, "/customers/new").text
check("고객사 새 등록 길 표시 「🆕 등록 · 고객사」", '<a href="/projects/new">🆕 등록</a> · <b>고객사</b>' in hn)

print("§4 고객사 새 등록 그대로")
r = q(cl.post, "/customers/new", data={"name": "입구시험고객", "biz_no": "123-45-60000", "ceo_name": "홍길동", "address": "서울", "is_active": "1"},
      follow_redirects=False)
with D.db_session() as c:
    n = c.execute("SELECT COUNT(*) FROM customers WHERE name='입구시험고객'").fetchone()[0]
check("등록 → 저장됨", r.status_code in (302, 303) and n == 1, (r.status_code, n))
g = q(cl.get, "/sales/flow-guide").text
check("안내 1단계: 카드에 🤝 고객사 · 「등록은 이곳 한 곳에서만」", "🤝 고객사)를 고릅니다" in g and "등록은 이곳 한 곳에서만" in g)

print("\n결과: OK %d · FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
