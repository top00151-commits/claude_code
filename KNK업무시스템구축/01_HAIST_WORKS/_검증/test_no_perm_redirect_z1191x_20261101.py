# -*- coding: utf-8 -*-
"""z1191x 시험 — 권한이 없어 돌려보낼 때 말없이 돌려보내지 않고 · 주소창을 누른 주소로 남기지 않는다.

대표 2026-11-01 「1번 고쳐」 — 권한 없는 사람이 자재구매센터 탭을 누르면 주소창만 /logistics · 화면은 홈 · 안내 없음 · 스크립트 오류 1건.
임시 DB · 실제 경로 · 실제 chrome.html 렌더 · 화면 전환 함수는 Node 로 실제 실행.
"""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "app", "templates")
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191x-test-not-a-real-key"
import app.database as D  # noqa: E402

D.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_z1191x_"), "t.db")
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("rank", "TEXT"), ("team_id", "INTEGER")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, rank, can_view_logistics, can_view_sales) "
              "VALUES ('권한있음','member','X901','X901','x',1,'프로',1,1)")
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, rank, can_view_logistics, can_view_sales) "
              "VALUES ('권한없음','member','X902','X902','x',1,'프로',0,0)")
    USERS = {k: dict(c.execute("SELECT * FROM users WHERE employee_no=?", (k,)).fetchone()) for k in ("X901", "X902")}
import app.main as M  # noqa: E402
from app.i18n import get_all_translations  # noqa: E402
from jinja2 import Environment, FileSystemLoader  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

CUR = {"u": USERS["X902"]}
M.get_user = lambda request: CUR["u"]
cl = TestClient(M.app, raise_server_exceptions=False, follow_redirects=False)
OK = FAIL = 0


def chk(cond, msg):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + msg)
    else:
        FAIL += 1
        print("  [FAIL] " + msg)


def loc(p):
    r = cl.get(p)
    return r.status_code, r.headers.get("location", "")


print("§1 서버 — 센터 입구는 안내값을 붙여 돌려보낸다")
CUR["u"] = USERS["X902"]
chk(loc("/logistics") == (303, "/home?no_perm=logistics"), "권한 없음 /logistics → /home?no_perm=logistics · 실제 %s" % (loc("/logistics"),))
chk(loc("/sales") == (303, "/home?no_perm=sales"), "권한 없음 /sales → /home?no_perm=sales · 실제 %s" % (loc("/sales"),))
for p in ("/parts", "/po", "/projects", "/stock/movements", "/sales/quotations"):
    chk(loc(p) == (303, "/home"), "안쪽 메뉴 %s 는 서버 그대로 /home(안내는 화면 전환 쪽) · 실제 %s" % (p, loc(p)))
chk(loc("/sales/schedule") == (303, "/dept/schedule"), "작업일정표 → 전사 일정표(대신 보여 주는 화면 · 그대로)")
h = cl.get("/home?no_perm=logistics")
chk(h.status_code == 200, "돌아온 /home?no_perm=logistics 는 정상으로 열림(200)")
CUR["u"] = USERS["X901"]
chk(cl.get("/logistics").status_code == 200 and cl.get("/sales").status_code == 200, "권한 있음 /logistics · /sales = 200 그대로")
chk("no_perm_logi" in cl.get("/logistics").text, "권한 있는 화면에도 안내 글은 실려 있다(주소에 값이 없으면 안 뜸)")

print("§2 번역 글 — 베트남 직원 82명도 해당")
KO, VI = get_all_translations("ko"), get_all_translations("vi")
for k in ("ch_no_perm", "ch_no_perm_logi", "ch_no_perm_sales"):
    chk(bool(KO.get(k)) and bool(VI.get(k)) and KO[k] != VI[k], "%s = 한국어 · 베트남어 따로 있음 · %s" % (k, VI.get(k)))
chk("자재구매센터" in KO["ch_no_perm_logi"] and KO["ch_tab_logi"] in KO["ch_no_perm_logi"], "자재 안내 글의 이름 = 상단 탭 이름")
chk(KO["ch_tab_sales"] in KO["ch_no_perm_sales"], "매출 안내 글의 이름 = 상단 탭 이름")
chk(VI["ch_tab_logi"] in VI["ch_no_perm_logi"] and VI["ch_tab_sales"] in VI["ch_no_perm_sales"], "베트남어 안내 글의 이름 = 베트남어 상단 탭 이름")

print("§3 화면 틀 — 안내는 토스트 · 값은 주소에서 지움 · 다른 스크립트보다 먼저")
env = Environment(loader=FileSystemLoader(TPL))
env.globals.update({"url_for": lambda *a, **k: "#", "vname": lambda *a, **k: "", "vname_full": lambda *a, **k: "",
                    "t": lambda s="", *a, **k: s, "T": lambda s="", *a, **k: s, "_": lambda s="", *a, **k: s,
                    "money": lambda v=0, c="KRW", *a, **k: str(v), "now": lambda *a, **k: "2026-11-01"})


class _U:
    def __init__(self, p):
        self.path = p


class _R:
    def __init__(self, p):
        self.url = _U(p)


def render(lang):
    return env.get_template("_v5_partials/chrome.html").render(
        request=_R("/home"), user={"id": 1, "name": "시험", "role": "member", "position": "", "dept": "", "team_id": 4},
        nav_badges={}, unread=0, can_supplier=False, can_bom_design=False, can_bom_purchase=False, lang=lang, i=get_all_translations(lang))


for lang, tr in (("ko", KO), ("vi", VI)):
    h = render(lang)
    for js, k in (("no_perm", "ch_no_perm"), ("no_perm_logi", "ch_no_perm_logi"), ("no_perm_sales", "ch_no_perm_sales")):
        chk(("%s: %s," % (js, json.dumps(tr[k]))) in h, "%s 화면 CH.%s = 그 말의 글(tojson 표기 그대로)" % (lang, js))
h = render("ko")
pos = {n: h.find(s) for n, s in (("토스트", "window.KNKBusy = {"), ("안내", "searchParams.get('no_perm')"), ("뒤로 기록", "var KEY = 'knkNavStack'"),
                                 ("최근 탭", "id=\"knkPtabs\""), ("화면 전환", "__knkSpaInit"))}
chk(all(v >= 0 for v in pos.values()), "다섯 부분 다 화면에 있음 %s" % pos)
chk(pos["토스트"] < pos["안내"] < pos["뒤로 기록"], "순서: 토스트 준비 → 안내(주소에서 지움) → 뒤로 기록(값이 기록에 안 남음)")
chk("history.replaceState" in h[pos["안내"]:pos["안내"] + 400] and "searchParams.delete('no_perm')" in h[pos["안내"]:pos["안내"] + 400], "값을 주소에서 지운다(새로고침해도 다시 안 뜸)")
chk("KNKBusy.toast(m, 'err', 6000)" in h, "표준 토스트 6초")

print("§4 화면 전환 함수 — 돌려보내면 그 화면으로 전체 이동")
spa = io.open(os.path.join(TPL, "_v5_partials", "spa_nav.html"), encoding="utf-8").read()
nav = spa[spa.index("function navigate(url, push)"):spa.index("window.addEventListener('popstate'")]
chk("if (r.redirected) { fullNav(afterRedirect(url, r.url)); return null; }" in nav, "돌려보냄 → 전체 이동(본문만 갈아 끼우지 않음)")
chk(nav.index("if (r.redirected)") < nav.index("return r.text()") and nav.index("!r.ok") < nav.index("if (r.redirected)"), "오류 응답 판정 다음 · 본문 읽기 전")
chk("/\\/login(\\?|$)/" not in nav, "옛 「로그인만」 조건 없음(로그인도 같은 길)")
fn = spa[spa.index("function afterRedirect(asked, final)"):spa.index("function navigate(url, push)")]
CASES = [
    ("안쪽 메뉴 권한 없음", "/parts", "/home", "/home?no_perm=1"),
    ("수출입 권한 없음", "/export", "/home", "/home?no_perm=1"),
    ("탭(서버가 적음)", "/logistics", "/home?no_perm=logistics", "/home?no_perm=logistics"),
    ("탭(서버가 적음)", "/sales", "/home?no_perm=sales", "/home?no_perm=sales"),
    ("대신 보여 주는 화면", "/sales/schedule", "/dept/schedule", "/dept/schedule"),
    ("로그인 풀림", "/parts", "/login?next=%2Fparts", "/login?next=%2Fparts"),
    ("첫 주소", "/", "/home", "/home"),
    ("홈 → 홈", "/home", "/home", "/home"),
    ("다른 화면으로 정상 이동", "/team", "/team/3/permissions", "/team/3/permissions"),
    ("홈에 다른 값이 있을 때", "/parts", "/home?tab=me", "/home?tab=me&no_perm=1"),
]
node = shutil.which("node")
if node:
    js = ("var location={href:'https://x.test/meetings'};\n%s\nvar C=%s;\n"
          "C.forEach(function(c){var o=afterRedirect('https://x.test'+c[1],'https://x.test'+c[2]).replace('https://x.test','');"
          "console.log(JSON.stringify([c[0],c[1],c[3],o]));});" % (fn, json.dumps(CASES, ensure_ascii=False)))
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
        tf.write(js)
    out = subprocess.run([node, tf.name], capture_output=True, text=True, encoding="utf-8")
    os.unlink(tf.name)
    lines = [json.loads(x) for x in out.stdout.splitlines() if x.startswith("[")]
    chk(len(lines) == len(CASES), "Node 실행 %d줄 %s" % (len(lines), out.stderr[-200:]))
    for name, asked, want, got in lines:
        chk(got == want, "%s: %s → %s · 실제 %s" % (name, asked, want, got))
else:
    print("  (node 없음 — 함수 실행 건너뜀)")
print("§5 다른 곳 그대로")
chk("no_perm=dashboard" in io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read(), "대시보드 차단의 ?no_perm=dashboard 그대로(이제 안내가 보임)")
chk(re.search(r"history\.pushState\(\{ knkSpa: true \}, '', url\)", spa) is not None, "정상 화면 전환은 그대로 본문만 교체 · 주소 넣기")

print()
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
