# -*- coding: utf-8 -*-
"""z1191z83 시험 — 안 쓰는 메뉴를 왼쪽 메뉴 맨 아래 「🗂 지금 안 쓰는 메뉴」 한 묶음에 접어 두었는가.

대표 2026-11-19 「안 쓰고 있는 부분… 싹 정리… 삭제하거나 숨기기, 아니면 접어두기를 한쪽으로 몰았으면」
 + 대표 고름: 대표 대시 · A/S 관리 · 출고 요청(준비 중)도 접기.
**실제 chrome.html 을 렌더해서** 본다. 지운 메뉴가 없는지(전과 같은 주소 전부 · 한 번씩)도 본다.
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
    "now": lambda *a, **k: "2026-11-19",
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


def render(path, lang="ko", role="member", position="", dept="", can_use_sales=0, **flags):
    tpl = env.get_template("_v5_partials/chrome.html")
    base = dict(
        request=_Req(path),
        user={"id": 1, "name": "시험", "role": role, "position": position, "dept": dept, "team_id": 4, "can_use_sales": can_use_sales},
        _path=path, path=path, active="", nav_badges={}, unread=0,
        can_supplier=False, can_bom_design=False, can_bom_purchase=False,
        lang=lang, i=get_all_translations(lang),
    )
    base.update(flags)
    return tpl.render(**base)


TOK = re.compile(r'<div class="sb-group">([^<]*)</div>|<a class="sb-item( active)?" href="([^"]+)">\s*<span>([^<]*)</span>')


def side(html):
    s = html[html.index('<aside class="sidebar"'):]
    return s[:s.index("</aside>")]


def parse(html):
    """(위쪽 묶음들 [(이름, [(주소, 이름, 켜짐)])], 접은 묶음 [(주소, 이름, 켜짐)], 접은 묶음 머리 글, 전체 HTML 조각)"""
    sd = side(html)
    i0 = sd.index('<details class="sb-fold"')
    i1 = sd.index("</details>", i0)
    top, fold = sd[:i0], sd[i0:i1]
    out = []
    for m in TOK.finditer(top):
        if m.group(3) is None:
            out.append((m.group(1).strip(), []))
        else:
            out[-1][1].append((m.group(3), m.group(4).strip(), bool(m.group(2))))
    fl = [(m.group(3), m.group(4).strip(), bool(m.group(2))) for m in TOK.finditer(fold) if m.group(3)]
    head = re.search(r"<summary[^>]*>(.*?)</summary>", fold, re.S).group(1)
    return out, fl, head, sd


def hrefs(gs, name):
    return [h for n, its in gs if n == name for h, _, _ in its]


KO = get_all_translations("ko")
G_HOME, G_SALES, G_LOGI, G_COMMON, G_ADMIN = KO["ch_tab_home"], KO["ch_g_sales"], KO["ch_g_logi"], KO["ch_g_common"], KO["ch_g_admin"]

FOLD_MEMBER = ["/daily", "/now", "/weekly", "/calendar", "/board/company", "/team", "/dept/requests", "/work-orders", "/rnd",
               "/tickets", "/changes", "/issues", "/as", "/stock/issues", "/search"]
FOLD_CEO = ["/daily", "/now", "/weekly", "/calendar", "/board/company", "/team", "/dashboard", "/workflow/team", "/workflow",
            "/dept/requests", "/work-orders", "/rnd", "/tickets", "/changes", "/issues", "/as", "/stock/issues", "/search"]
COMMON_NOW = ["/dept/schedule", "/meetings", "/voice-notes", "/contacts", "/notifications"]
# 바꾸기 전(main 0109fffd) 사이드바에 있던 주소 — 전부 그대로 한 번씩 있어야 한다(지운 것 없음)
BEFORE_HOME = ["/home", "/daily", "/now", "/board/company", "/team", "/weekly"]
BEFORE_COMMON = ["/dept/schedule", "/contacts", "/meetings", "/voice-notes", "/dept/requests", "/work-orders", "/rnd",
                 "/notifications", "/calendar", "/tickets", "/changes", "/issues", "/search"]

print("§1 일반 직원 · 통합 플랫폼 — 위에는 많이 쓰는 것만, 나머지는 접은 묶음")
g, fl, head, sd = parse(render("/home"))
chk(hrefs(g, G_HOME) == ["/home"], "통합 플랫폼 묶음 = 업무현황 하나 · 실제 %s" % hrefs(g, G_HOME))
chk(hrefs(g, G_COMMON) == COMMON_NOW, "공통 = 전사 일정표 → 회의록 → 음성 메모 → 연락처 → 알림함 · 실제 %s" % hrefs(g, G_COMMON))
chk([h for h, _, _ in fl] == FOLD_MEMBER, "접은 묶음 = %d개(정한 순서) · 실제 %s" % (len(FOLD_MEMBER), [h for h, _, _ in fl]))
chk("(%d)" % len(FOLD_MEMBER) in head, "묶음 머리에 개수 (%d) · 실제 %s" % (len(FOLD_MEMBER), re.sub(r"<[^>]+>", "", head).strip()))
chk(KO["ch_g_fold"] in head, "묶음 이름 = 「%s」" % KO["ch_g_fold"])
chk('<details class="sb-fold" id="sbFold">' in sd, "기본은 접힘(open 없음)")
chk(G_ADMIN not in [n for n, _ in g], "일반 직원에겐 관리 묶음 없음(전과 같음)")
allh = [h for n, its in g for h, _, _ in its] + [h for h, _, _ in fl]
dup = sorted(set(h for h in allh if allh.count(h) > 1 and h != "/bom/tools?mode=design"))
chk(not dup, "같은 메뉴 두 번 없음 · 겹침 %s" % dup)
chk(all(allh.count(p) == 1 for p in BEFORE_HOME + BEFORE_COMMON), "바꾸기 전 통합·공통 주소가 전부 한 번씩 있음(지운 것 없음)")

print("§2 대표·관리자 — 대표 대시 · 우리 팀 현황 · 일 순서 만들기도 접은 묶음에 · 관리 묶음 그대로")
g, fl, head, sd = parse(render("/home", role="ceo", position="대표이사"))
chk([h for h, _, _ in fl] == FOLD_CEO, "접은 묶음 = %d개 · 실제 %s" % (len(FOLD_CEO), [h for h, _, _ in fl]))
chk("(%d)" % len(FOLD_CEO) in head, "묶음 머리 개수 (%d)" % len(FOLD_CEO))
chk(hrefs(g, G_HOME) == ["/home"], "통합 플랫폼 묶음 = 업무현황 하나(대표 대시도 접음)")
chk(hrefs(g, G_ADMIN) == ["/admin"], "관리 묶음 = 「⚙️ 관리」 하나(2단계 · 나머지는 관리 홈으로) · 실제 %s" % hrefs(g, G_ADMIN))
chk(sd.index('<div class="sb-group">' + G_ADMIN) < sd.index('<details class="sb-fold"'), "접은 묶음은 관리 아래(맨 아래)")
allh = [h for n, its in g for h, _, _ in its] + [h for h, _, _ in fl]
chk(all(allh.count(p) == 1 for p in BEFORE_HOME + BEFORE_COMMON + ["/dashboard", "/workflow/team", "/workflow"]),
    "대표에게 보이던 주소 전부 한 번씩(지운 것 없음)")
gl, fll, _, _ = parse(render("/home", role="member", position="팀장"))
chk("/workflow/team" in [h for h, _, _ in fll] and "/workflow" in [h for h, _, _ in fll] and "/dashboard" not in [h for h, _, _ in fll],
    "팀장(일반 역할) = 우리 팀 현황·일 순서는 보이고 대표 대시는 안 보임(전과 같은 조건)")

print("§3 매출영업 · 자재구매 화면 — A/S 관리 · 출고 요청은 묶음으로, 나머지 순서 그대로")
g, fl, _, _ = parse(render("/sales", active_tab="sales"))
# z1191z92 (대표 11-21 P0-2·P0-7): 「🆕 등록」(z1191z97 대표 11-22: 매출 홈 다음) · 맨 아래 「📖 처음이면 — 등록부터 입금까지」 두 줄이 더해짐
chk(hrefs(g, G_SALES) == ["/sales", "/projects/new", "/sales/opportunities", "/projects", "/sales/schedule", "/customers", "/sales/quotations",
                          "/sales/orders", "/sales/shipments-receipts", "/sales/outstanding", "/export", "/sales/flow-guide"],
    "매출·영업 묶음 = A/S 관리만 빠짐 · 실제 %s" % hrefs(g, G_SALES))
chk("/as" in [h for h, _, _ in fl], "A/S 관리는 접은 묶음에")
chk(hrefs(g, G_COMMON) == COMMON_NOW, "매출영업 화면에서도 공통 = 같은 5개")
g, fl, _, _ = parse(render("/logistics", active_tab="logi"))
chk(hrefs(g, G_LOGI) == ["/logistics", "/parts", "/bom/upload", "/po", "/po/new", "/stock/movements", "/rates",
                         "/catalog", "/materials/requests", "/materials/new-review"],
    "자재·구매 묶음 = 출고 요청만 빠짐 · 실제 %s" % hrefs(g, G_LOGI))
chk("/stock/issues" in [h for h, _, _ in fl], "출고 요청(준비 중)은 접은 묶음에")
g, fl, _, _ = parse(render("/sales", active_tab="sales", role="admin", can_use_sales=1))
chk("/sales/bank-recon" in hrefs(g, G_SALES), "입금 대사(재무 권한) 자리 그대로")
# z1191z94: 「💰 입금 확인」 = 매출 등록 권한(또는 대표)에게만 · 납품·수금 다음 · 미수금 앞 (위 일반 계정 목록에는 없음 = 맞음)
_h94 = hrefs(g, G_SALES)
chk("/sales/receipts-check" in _h94 and _h94.index("/sales/receipts-check") == _h94.index("/sales/shipments-receipts") + 1,
    "매출 등록 권한 = 💰 입금 확인(납품·수금 다음) · 실제 %s" % _h94)

print("§4 접은 메뉴 화면에 들어가면 — 그 메뉴가 켜지고 묶음이 저절로 펼쳐짐")
for p, want in (("/tickets", "/tickets"), ("/daily", "/daily"), ("/board/company", "/board/company"), ("/calendar", "/calendar")):
    g, fl, head, sd = parse(render(p))
    on = [h for h, _, a in fl if a]
    chk(on == [want], "%s → 접은 묶음 안에서 %s 켜짐 · 실제 %s" % (p, want, on))
    chk(not [h for _, its in g for h, _, a in its if a], "%s → 위쪽 메뉴엔 켜진 것 없음" % p)
chk("d.querySelector('.sb-item.active')" in sd and "d.open = true" in sd, "켜진 메뉴가 묶음 안에 있으면 펼치는 코드")
g, fl, _, _ = parse(render("/meetings/12"))
chk([h for _, its in g for h, _, a in its if a] == ["/meetings"] and not [h for h, _, a in fl if a], "/meetings/12 → 위쪽 회의록 켜짐(전과 같음)")

print("§5 펼침 기억 · 저장 실패해도 화면은 그대로")
chk("localStorage.getItem(K) === '1'" in sd and "localStorage.setItem(K, d.open ? '1' : '0')" in sd, "펼침/접힘을 이 기기에 기억(knk.sbFold)")
chk(sd.count("try {") >= 2, "저장소 읽기·쓰기 모두 try 로 감쌈(사생활 창에서도 안 깨짐)")
chk(KO["ch_fold_hint"] in sd and "지운 메뉴는 없습니다" in sd, "안내 글: 모아 두었을 뿐 · 지운 것 없음")

print("§6 다른 말(베트남어 · 영어)")
for lang in ("vi", "en"):
    tr = get_all_translations(lang)
    g, fl, head, sd = parse(render("/home", lang=lang))
    chk(tr["ch_g_fold"] in head and tr["ch_g_fold"] != KO["ch_g_fold"], "%s: 묶음 이름 = %s" % (lang, tr["ch_g_fold"]))
    chk([h for h, _, _ in fl] == FOLD_MEMBER, "%s: 같은 메뉴 같은 순서" % lang)
    chk(hrefs(g, tr["ch_g_common"]) == COMMON_NOW, "%s: 공통 같은 5개" % lang)

print("§7 주소·기능은 안 바뀜 — 서버 경로 그대로")
src = "".join(io.open(os.path.join(ROOT, "app", f), encoding="utf-8").read() for f in os.listdir(os.path.join(ROOT, "app")) if f.endswith(".py"))
for p in FOLD_CEO:
    chk(('@app.get("%s"' % p) in src, "경로 %s 그대로 있음" % p)

print("\n결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
