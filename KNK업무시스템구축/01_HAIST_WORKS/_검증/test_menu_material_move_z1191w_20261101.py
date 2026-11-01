# -*- coding: utf-8 -*-
"""z1191w 시험 — 자재 카탈로그·자재 요청서 메뉴가 공통 → 자재구매센터로 옮겨졌는가.

대표 2026-11-01 「사진에 표기한 두가지 항목은 공통에서 빼서 "자재구매센터" 항목으로 옮겨」
**실제 chrome.html 을 렌더해서** 메뉴 자리를 본다. 경로 권한은 안 바꿨다(로그인만 보면 열림) — 그것도 소스로 확인한다.
"""
import io
import os
import re
import sys

from jinja2 import Environment, FileSystemLoader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "app", "templates")
sys.path.insert(0, ROOT)
from app.i18n import get_all_translations  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")

env = Environment(loader=FileSystemLoader(TPL))
env.globals.update({
    "url_for": lambda *a, **k: "#",
    "vname": lambda u=None, *a, **k: (u or {}).get("name", "") if isinstance(u, dict) else "",
    "vname_full": lambda u=None, *a, **k: (u or {}).get("name", "") if isinstance(u, dict) else "",
    "t": lambda s="", *a, **k: s, "T": lambda s="", *a, **k: s, "_": lambda s="", *a, **k: s,
    "money": lambda v=0, c="KRW", *a, **k: str(v),
    "now": lambda *a, **k: "2026-11-01",
})

OK = FAIL = 0


def chk(cond, msg):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + msg)
    else:
        FAIL += 1
        print("  [FAIL] " + msg)


class _URL:
    def __init__(self, p):
        self.path = p


class _Req:
    def __init__(self, p):
        self.url = _URL(p)


def render(path, lang="ko", **flags):
    tpl = env.get_template("_v5_partials/chrome.html")
    base = dict(
        request=_Req(path),
        user={"id": 1, "name": "시험", "role": flags.pop("role", "member"), "position": "", "dept": "", "team_id": 4},
        _path=path, path=path, active="", nav_badges={}, unread=0,
        can_supplier=False, can_bom_design=False, can_bom_purchase=False,
        lang=lang, i=get_all_translations(lang),
    )
    base.update(flags)
    return tpl.render(**base)


TOK = re.compile(r'<div class="sb-group">([^<]*)</div>|<a class="sb-item( active)?" href="([^"]+)">\s*<span>([^<]*)</span>')


def groups(html):
    """사이드바를 위에서 아래로 읽어 [(묶음 이름, [(주소, 이름, 표시 켜짐)])]"""
    side = html[html.index('<aside class="sidebar"'):]
    side = side[:side.index("</aside>")]
    out = []
    for m in TOK.finditer(side):
        if m.group(3) is None:
            out.append((m.group(1).strip(), []))
        else:
            out[-1][1].append((m.group(3), m.group(4).strip(), bool(m.group(2))))
    return out


def hrefs(gs, name):
    return [h for n, its in gs if n == name for h, _, _ in its]


KO = get_all_translations("ko")
G_LOGI, G_COMMON = KO["ch_g_logi"], KO["ch_g_common"]
MOVED = ["/catalog", "/materials/requests"]

print("§1 자재구매센터 화면 — 두 메뉴가 자재구매센터 묶음에 · 공통엔 없음")
g = groups(render("/logistics"))
logi, common = hrefs(g, G_LOGI), hrefs(g, G_COMMON)
for p in MOVED:
    chk(logi.count(p) == 1, "자재구매센터 묶음에 %s 1개" % p)
    chk(p not in common, "공통 묶음에 %s 없음" % p)
    chk(sum(h == p for _, its in g for h, _, _ in its) == 1, "사이드바 전체에 %s 1개뿐" % p)
chk(logi[logi.index("/rates") + 1:logi.index("/rates") + 4] == ["/catalog", "/materials/requests", "/materials/new-review"],
    "자리 = 환율 → 자재 카탈로그 → 자재 요청서 → 신규 자재 검토")
chk(logi == ["/logistics", "/parts", "/bom/upload", "/po", "/po/new", "/stock/movements", "/stock/issues", "/rates",
             "/catalog", "/materials/requests", "/materials/new-review"],
    "자재구매센터 다른 메뉴 순서 그대로(권한 없는 BOM·구매처 제외) · 실제 %s" % logi)
labels = dict((h, n) for _, its in g for h, n, _ in its)
chk(labels.get("/catalog") == KO["ch_m_catalog"] and labels.get("/materials/requests") == KO["ch_m_matreq"], "이름 그대로(자재 카탈로그 · 자재 요청서)")

print("§2 통합 플랫폼 · 매출영업센터 화면 — 두 메뉴가 어디에도 없음")
EXPECT_COMMON = ["/dept/schedule", "/contacts", "/meetings", "/voice-notes", "/dept/requests", "/work-orders", "/rnd",
                 "/notifications", "/calendar", "/tickets", "/changes", "/issues", "/search"]
for path, hub in (("/home", "통합 플랫폼"), ("/sales", "매출영업센터"), ("/dept/schedule", "전사 일정표")):
    g = groups(render(path))
    allh = [h for _, its in g for h, _, _ in its]
    chk(not [p for p in MOVED if p in allh], "%s 화면 사이드바에 두 메뉴 없음" % hub)
    chk(hrefs(g, G_COMMON) == EXPECT_COMMON, "%s 화면 공통 묶음 = 나머지 그대로 · 순서 그대로 · 실제 %d개" % (hub, len(hrefs(g, G_COMMON))))

print("§3 그 화면에 들어가면 — 자재구매센터에 머문다 · 메뉴 표시 켜짐")
for tname in ("catalog.html", "catalog_cart.html", "materials_requests.html", "materials_request_detail.html"):
    src = io.open(os.path.join(TPL, tname), encoding="utf-8").read()
    chk('{% set active_tab = "logi" %}' in src, "%s 는 자재구매센터 화면(active_tab=logi)" % tname)
for path, want in (("/catalog", "/catalog"), ("/catalog/cart", "/catalog"), ("/materials/requests", "/materials/requests"),
                   ("/materials/requests/5", "/materials/requests")):
    h = render(path, active_tab="logi")
    g = groups(h)
    on = [hh for _, its in g for hh, _, a in its if a]
    chk(on == [want], "%s → 메뉴 표시 = %s 하나 · 실제 %s" % (path, want, on))
    chk(re.search(r'class="top-tab active" href="/logistics"', h) is not None, "%s → 상단 탭 = 자재구매센터" % path)
    chk(want in hrefs(g, G_LOGI), "%s → 사이드바 자재구매센터 묶음에 그 메뉴" % path)
on = [hh for _, its in groups(render("/materials/new-review", active_tab="logi")) for hh, _, a in its if a]
chk(on == [], "/materials/new-review 는 전처럼 표시 없음(요청서 메뉴에 잘못 안 켜짐) · 실제 %s" % on)

print("§4 다른 말(베트남어 · 영어)도 같은 자리")
for lang in ("vi", "en"):
    tr = get_all_translations(lang)
    g = groups(render("/logistics", lang=lang))
    lg, cm = hrefs(g, tr["ch_g_logi"]), hrefs(g, tr["ch_g_common"])
    chk(all(p in lg for p in MOVED) and not [p for p in MOVED if p in cm], "%s: 자재구매센터 묶음에 있고 공통엔 없음" % lang)
    names = dict((h, n) for _, its in g for h, n, _ in its)
    chk(names.get("/catalog") == tr["ch_m_catalog"] and names.get("/materials/requests") == tr["ch_m_matreq"],
        "%s: 메뉴 글 = %s · %s" % (lang, names.get("/catalog"), names.get("/materials/requests")))

print("§5 메뉴 번호 · 뒤로 단추")
chrome = io.open(os.path.join(TPL, "_v5_partials", "chrome.html"), encoding="utf-8").read()
chk(chrome.count("'M-02-29'") == 1 and chrome.count("'M-02-30'") == 1, "새 번호 M-02-29 · M-02-30 하나씩")
chk("'M-00-14'" not in chrome and "'M-00-15'" not in chrome, "옛 번호 M-00-14 · M-00-15 없음")
menu_cat = io.open(os.path.join(ROOT, "app", "menu_catalog.py"), encoding="utf-8").read()
chk('"M-02-29"' not in menu_cat and '"M-02-30"' not in menu_cat, "메뉴 번호 목록의 다른 화면과 안 겹침")
m = re.search(r"else if \(/\^\\/\(([^)]*)\)/\.test\(p\)\) location\.assign\('/logistics'\)", chrome)
chk(m is not None and "catalog" in m.group(1).split("|") and "materials" in m.group(1).split("|"),
    "이전 페이지 없을 때 뒤로 = /catalog · /materials → 자재구매센터")

print("§6 경로 권한은 안 바꿨다 — 메뉴 자리만")
main = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()


def body(sig):
    i = main.index(sig)
    j = main.find("\n@app.", i + 1)
    return main[i:j]


for sig, name in (('@app.get("/catalog", response_class=HTMLResponse)', "/catalog"),
                  ('@app.get("/catalog/cart", response_class=HTMLResponse)', "/catalog/cart"),
                  ('@app.get("/materials/requests", response_class=HTMLResponse)', "/materials/requests"),
                  ('@app.post("/materials/requests")', "POST /materials/requests")):
    b = body(sig)
    chk("get_user(req)" in b and "can_view_logistics" not in b and "can_use_logistics" not in b, "%s = 로그인만 본다(전과 같음)" % name)
chk("if not can_view_logistics(u):" in body('@app.get("/logistics", response_class=HTMLResponse)'),
    "/logistics = 센터 권한 없으면 홈으로(전과 같음)")

print()
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
