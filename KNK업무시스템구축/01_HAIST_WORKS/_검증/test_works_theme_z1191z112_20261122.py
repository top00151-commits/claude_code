# -*- coding: utf-8 -*-
"""z1191z112 시험 — 웍스 화면 테마 3가지(대표 11-22 「웍스 화면에도 같은 테마 3가지」
 → 결정: 메일과 따로 고르기 · 기본 = 부드럽게 · 어둡게에서도 KNK 빨강은 그대로)
  §1 모든 화면 틀에 한 번 · 상단바 🎨 단추 · 고르기 카드 3장
  §2 조각 내용: 저장 열쇠 knk.theme(메일 knkmail.theme 과 따로) · 기본 soft · 색 값 = 메일 테마와 같은 값 · 인쇄 때 끔 · 빨강 지키기
  §3 사전: 한국어·베트남어 글 · 베트남어 화면에도 나옴
  §4 메일 테마 파일은 그대로(세션 15 소유)
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z112-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z112_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("must_change_pw", "INTEGER DEFAULT 0"), ("lang", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, "
              "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상대표', 'ceo', 'Z112', 'Z112', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    CEO = dict(c.execute("SELECT * FROM users WHERE employee_no='Z112'").fetchone())
import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
U = {"u": CEO}
M.get_user = lambda request: U["u"]
cl = TestClient(M.app)
OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", label)
    else:
        FAIL += 1; print("  ❌", label, "" if got is None else ("→ %r" % (got,))[:300])


print("§1 모든 화면 틀에 한 번 · 🎨 단추 · 카드 3장")
for u in ("/sales", "/projects", "/sales/quotations", "/sales/opportunities", "/home", "/customers", "/stock/adjust"):
    r = cl.get(u)
    h = r.text
    check("%s: 200 · 테마 한 번 · 🎨 단추 하나 · 카드 3장" % u,
          r.status_code == 200 and h.count("window.__knkThemeZ112 = 1") == 1 and h.count('id="knkThemeBtn"') == 1
          and h.count('class="kt-card"') == 3 and 'onclick="knkThemeToggle(event)"' in h,
          (r.status_code, h.count("__knkThemeZ112"), h.count('id="knkThemeBtn"')))

print("§2 조각 내용")
src = io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "knk_theme.html"), encoding="utf-8").read()
check("저장 열쇠 = knk.theme (메일 knkmail.theme 과 따로)", "localStorage.getItem('knk.theme')" in src and "knkmail.theme')" not in src.replace("`knkmail.theme`", ""))
check("안 고른 사람 = 부드럽게(soft)", "var t = 'soft'; try { t = localStorage.getItem('knk.theme') || 'soft'; }" in src)
mail = io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "mail_theme.html"), encoding="utf-8").read()
# z1191z113: 웍스 배색은 대표 지적(배색 괴리감)으로 중립 회색 한 벌을 기준으로 다시 잡음 — 메일과 같은 값 검사는 뺌
check("배색 한 벌(z113): 면 = 흰색 · 바탕 = 한 단계 낮은 회색 · 글자 짙은 남색", "--knk-bg-surface:#ffffff" in src and "--knk-bg-page:#f3f4f6" in src and "--knk-text-primary:#111827" in src)
check("filter 는 <html> 에만(붙어 있는 창 위치 그대로)", 'filter:brightness(.93); }' in src and 'html[data-kt="dark"] { filter:invert(.9) hue-rotate(180deg);' in src
      and not re.search(r"\.main[^{]*\{[^}]*filter", src))
check("어둡게: 사진·그림·로고 원래 색 · KNK 빨강 바탕 지키기", 'html[data-kt="dark"] img' in src and "knk-kt-keep" in src and "Math.abs(+m[1] - 165) < 30" in src)
check("인쇄 때 테마 끔", "@media print { html[data-kt] { filter:none !important; } }" in src)
check("다른 창도 같이 바뀜(storage)", "e.key === 'knk.theme'" in src)

print("§3 사전(한국어·베트남어)")
import app.i18n as I  # noqa: E402
keys = ["ch_theme_t", "ch_theme_clear", "ch_theme_clear_d", "ch_theme_soft", "ch_theme_soft_d", "ch_theme_dark", "ch_theme_dark_d", "ch_theme_note"]
check("8개 글 모두 ko·vi", all(I.T.get(k, {}).get("ko") and I.T.get(k, {}).get("vi") for k in keys))
h = cl.get("/sales").text
check("한국어 화면: 「화면 테마」·「부드럽게」", "🎨 화면 테마" in h and "🌤 부드럽게" in h)
with D.db_session() as c:
    c.execute("UPDATE users SET lang='vi' WHERE id=?", (CEO["id"],))
    U["u"] = dict(c.execute("SELECT * FROM users WHERE id=?", (CEO["id"],)).fetchone())
h = cl.get("/sales").text
check("베트남어 사용자 화면: 「Giao diện màn hình」·「Dịu mắt」", "Giao diện màn hình" in h and "Dịu mắt" in h, ("Giao diện" in h))
U["u"] = CEO

print("§4 메일 테마는 그대로")
check("메일 테마 파일에 웍스 테마 흔적 없음", "knk.theme'" not in mail and "data-kt" not in mail)
print("\n결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
