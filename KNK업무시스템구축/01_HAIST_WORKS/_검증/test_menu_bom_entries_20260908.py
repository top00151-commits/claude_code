# -*- coding: utf-8 -*-
"""z1096 시험 — BOM 입구 분리 메뉴가 권한별로 맞게 보이는가.

세션05 연결표(2026-09-08 16:30) 대로 붙인 뒤, 판정 문서 §3 공동 확인 항목을
**실제 chrome.html 을 렌더해서** 확인한다(사본 재작성 아님).

세션01 판단: 구매 담당자에게는 구매 입구 하나만 — 입구가 둘이면 "뭘 눌러야 하지"가 된다.
"""
import io
import os
import re
import sys

from jinja2 import Environment, FileSystemLoader

# _검증/ 안에서 실행 — 부모가 01_HAIST_WORKS
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "app", "templates")

env = Environment(loader=FileSystemLoader(TPL))
env.globals.update({
    "url_for": lambda *a, **k: "#",
    "vname": lambda u=None, *a, **k: (u or {}).get("name", "") if isinstance(u, dict) else "",
    "vname_full": lambda u=None, *a, **k: (u or {}).get("name", "") if isinstance(u, dict) else "",
    "t": lambda s="", *a, **k: s, "T": lambda s="", *a, **k: s, "_": lambda s="", *a, **k: s,
    "money": lambda v=0, c="KRW", *a, **k: str(v),
    "now": lambda *a, **k: "2026-09-08",
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


DESIGN_MENU = "설계 BOM 만들기"
PURCH_MENU = "구매 서류 만들기"
OLD_MENU = "BOM 도구"


class _URL:
    def __init__(self, p):
        self.path = p


class _Req:
    """chrome.html 은 `_path = request.url.path` 로 허브를 정한다(12행) — 실제와 같게 흉내낸다."""
    def __init__(self, p):
        self.url = _URL(p)


def render(path, **flags):
    """실제 chrome.html 을 그대로 렌더한다. flags 로 권한 변수를 준다."""
    tpl = env.get_template("_v5_partials/chrome.html")
    base = dict(
        request=_Req(path),
        user={"id": 1, "name": "시험", "role": flags.pop("role", "member"),
              "position": "", "dept": "", "team_id": 4},
        _path=path, path=path, active="", nav_badges={}, unread=0,
        can_supplier=False, can_bom_design=False, can_bom_purchase=False,
    )
    base.update(flags)
    return tpl.render(**base)


def menus(html):
    """사이드바에 실제로 뜬 메뉴 이름만 뽑는다."""
    return re.findall(r'<a class="sb-item[^"]*" href="([^"]+)">\s*<span>([^<]+)</span>', html)


print("=" * 78)
print("§1 설계 권한자 — 설계 입구만, 자재구매센터를 거치지 않는가")
print("=" * 78)
for path, hub in (("/home", "통합 플랫폼"), ("/sales", "매출영업센터"), ("/logistics", "자재구매센터")):
    h = render(path, can_bom_design=True, can_bom_purchase=False)
    names = [n for _, n in menus(h)]
    chk(any(DESIGN_MENU in n for n in names), "%s 화면에서도 「설계 BOM 만들기」 보임" % hub)
h = render("/home", can_bom_design=True, can_bom_purchase=False)
names = [n for _, n in menus(h)]
chk(not any(PURCH_MENU in n for n in names), "설계자에게 「구매 서류 만들기」 안 보임")
hrefs = dict((n.strip(), p) for p, n in menus(h))
chk(any("mode=design" in p for n, p in hrefs.items() if DESIGN_MENU in n),
    "설계 입구 목적지 = /bom/tools?mode=design")

print()
print("=" * 78)
print("§2 구매 권한자 — 구매 입구 하나만 (세션01 판단)")
print("=" * 78)
h = render("/logistics", can_bom_design=True, can_bom_purchase=True)
names = [n for _, n in menus(h)]
chk(any(PURCH_MENU in n for n in names), "「구매 서류 만들기」 보임")
chk(not any(DESIGN_MENU in n for n in names),
    "「설계 BOM 만들기」는 감춤 — 입구 하나 (실제 %s)"
    % [n for n in names if "BOM" in n or "만들기" in n])
hrefs = dict((n.strip(), p) for p, n in menus(h))
chk(any("mode=purchase" in p for n, p in hrefs.items() if PURCH_MENU in n),
    "구매 입구 목적지 = /bom/tools?mode=purchase")

print()
print("=" * 78)
print("§3 권한 없는 사람 — 메뉴가 아예 안 보이는가")
print("=" * 78)
for path, hub in (("/home", "통합"), ("/logistics", "자재구매")):
    h = render(path, can_bom_design=False, can_bom_purchase=False)
    names = [n for _, n in menus(h)]
    chk(not any(DESIGN_MENU in n for n in names), "%s — 설계 입구 안 보임" % hub)
    chk(not any(PURCH_MENU in n for n in names), "%s — 구매 입구 안 보임" % hub)

print()
print("=" * 78)
print("§4 옛 「BOM 도구」 이름이 남아 있지 않은가")
print("=" * 78)
src = io.open(os.path.join(TPL, "_v5_partials/chrome.html"), encoding="utf-8").read()
# 주석이 아니라 **실제로 화면에 뜨는 메뉴 이름**으로 본다(주석에는 옛 이름을 근거로 남겨 둔다)
_h_old = render("/logistics", can_bom_design=True, can_bom_purchase=True)
chk(not any(OLD_MENU in n for _, n in menus(_h_old)), "화면에 옛 이름 「BOM 도구」 안 뜸")
chk(src.count("/bom/tools") == 2, "BOM 입구는 정확히 2개 (실제 %d)" % src.count("/bom/tools"))
chk("M-00-25" in src and "M-02-28" in src, "메뉴코드 M-00-25 · M-02-28 부여")

print()
print("=" * 78)
print("§5 다른 메뉴 회귀 — 허브 3탭·공통 그룹 나머지가 그대로인가")
print("=" * 78)
# 허브별 메뉴는 그 허브 화면에서만 뜬다 — 각각의 자리에서 확인한다
CASES = [
    ("/sales", "매출영업", ["매출 홈", "프로젝트", "작업 일정표", "고객사", "견적서", "수주"]),
    ("/logistics", "자재구매", ["자재 홈", "부품 마스터", "BOM 보드", "협력사", "발주 목록", "환율"]),
    ("/home", "통합", ["업무현황"]),
]
for path, hub, must in CASES:
    h = render(path, can_bom_design=True, can_bom_purchase=True, can_supplier=True, role="admin")
    names = [n for _, n in menus(h)]
    missing = [m for m in must if not any(m in n for n in names)]
    chk(not missing, "%s 허브 메뉴 %d개 그대로 (빠진 것 %s)"
        % (hub, len(must), missing or "없음"))

# 공통 그룹은 어느 허브에서나 그대로
h_all = render("/logistics", can_bom_design=True, can_bom_purchase=True, can_supplier=True,
               role="admin")
names = [n for _, n in menus(h_all)]
common = ["전사 일정표", "자재 카탈로그", "자재 요청서", "연락처", "회의록",
          "알림함", "캘린더", "검색", "변경 공지"]
missing = [m for m in common if not any(m in n for n in names)]
chk(not missing, "공통 메뉴 %d개 그대로 (빠진 것 %s)" % (len(common), missing or "없음"))
for hub in ("통합 플랫폼", "매출영업센터", "자재구매센터"):
    chk(hub in h_all, "허브 탭 「%s」 그대로" % hub)

print()
print("=" * 78)
print("§6 BOM 보드(/bom/upload)는 건드리지 않았는가")
print("=" * 78)
chk("/bom/upload" in src, "BOM 보드 메뉴 유지")
chk(src.count("/bom/upload") == 1, "BOM 보드는 1개 그대로")

print()
print("=" * 78)
print("§7 ⭐옛 이름 「BOM 도구」가 **화면에 뜨는 곳**이 하나도 없는가 — 전수")
print("=" * 78)
# 🔴 2026-09-08: 사이드바·자재 홈 카드를 고치고도 project_bom.html 의 버튼이 남아 있었다.
#   (grep 만 하면 주석까지 세어 '있다'고 나오고, 주석만 보고 넘기면 진짜를 놓친다)
#   → **주석을 걷어낸 뒤** 남는 것만 위반으로 본다.
JINJA_CMT = re.compile(r"\{#.*?#\}", re.S)
HTML_CMT = re.compile(r"<!--.*?-->", re.S)
OLD_NAMES = ["BOM 도구"]
bad = []
for dirpath, _dirs, files in os.walk(TPL):
    for fn in files:
        if not fn.endswith(".html"):
            continue
        p = os.path.join(dirpath, fn)
        body = HTML_CMT.sub("", JINJA_CMT.sub("", io.open(p, encoding="utf-8").read()))
        for nm in OLD_NAMES:
            if nm in body:
                rel = os.path.relpath(p, TPL)
                ln = body[:body.index(nm)].count("\n") + 1
                bad.append("%s (주석 걷어낸 기준 %d번째 줄)" % (rel, ln))
chk(not bad, "화면에 뜨는 옛 이름 0건 (실제 %s)" % (bad or "없음"))

print()
print("=" * 78)
print("§8 프로젝트 BOM 화면 버튼도 같은 규칙인가")
print("=" * 78)
pb = io.open(os.path.join(TPL, "project_bom.html"), encoding="utf-8").read()
chk("can_bom_purchase" in pb and "can_bom_design" in pb, "권한 분기 있음")
for nm in ("구매 서류 만들기", "설계 BOM 만들기", "BOM 자료 보기"):
    chk(nm in pb, "「%s」 버튼 있음" % nm)
chk("mode=purchase" in pb and "mode=design" in pb, "목적지에 mode 붙음")

print()
print("=" * 78)
print("결과: %d OK / %d FAIL" % (OK, FAIL))
print("=" * 78)
sys.exit(1 if FAIL else 0)
