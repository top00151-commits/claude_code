# -*- coding: utf-8 -*-
"""z1191z134 (대표 11-24 사진 「가끔 화면이 정확하게 안 나옴」 · 프로젝트 화면 제목 띠가 80px 내려와 위가 비고 단추 줄을 가림)
   원인: 처음 열린 화면 <head> 의 전용 스타일(전사 일정표 `.main{overflow:hidden !important}`)이 메뉴로 화면을 바꿔도 남음
        → 다음 화면 본문 스크롤 꺼짐 → 제목 띠 고정이 「화면 전체 스크롤」로 잘못 보고 상단바 높이만큼 내려 붙임.
   (실제 화면: 시험 서버 1616px · 전사 일정표 → 매출영업센터 → 프로젝트 · 고치기 전 틈 80px → 고친 뒤 0 · 다시 전사 일정표 = hidden · 스타일 수 30 그대로)"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = []
def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:300]))
P = os.path.join(ROOT, "app", "templates", "_v5_partials")
sp = open(os.path.join(P, "spa_nav.html"), encoding="utf-8").read()
sh = open(os.path.join(P, "knk_sticky_head.html"), encoding="utf-8").read()
ds = open(os.path.join(ROOT, "app", "templates", "dept_schedule.html"), encoding="utf-8").read()
check("재현 조건: 전사 일정표 <head> 에 본문 스크롤 끄기 전용 스타일", ".main{ overflow:hidden !important; }" in ds and ds.index(".main{ overflow:hidden") < ds.index("</head>") if "</head>" in ds else True)
check("① 처음 열 때 <head> 스타일에 표시(data-knk-orig)", "document.head.querySelectorAll('style, link[rel=\"stylesheet\"]').forEach(function(n){ n.setAttribute('data-knk-orig','1'); });" in sp)
i = sp.index("function syncPageStyles(doc)")
blk = sp[i:i + 1600]
check("① 화면 바꿀 때 새 화면에 없는 처음 스타일 지움", "document.head.querySelectorAll('[data-knk-orig]').forEach(function(n){ if (!want[_sig134(n)]) n.remove(); });" in blk)
check("① 같은지 비교는 표시 빼고(공용 스타일 두 번 안 넣음)", "existing[_sig134(n)] = 1" in blk and "if (existing[_sig134(n)]) return;" in blk)
check("① 지우기는 새 스타일 넣기보다 먼저", blk.index("[data-knk-orig]") < blk.index("clone.setAttribute('data-knk-page-style','1')"))
check("② 제목 띠: overflow hidden 도 본문 스크롤 칸으로", "/(auto|scroll|hidden)/.test(getComputedStyle(m).overflowY)" in sh)
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader(os.path.join(ROOT, "app", "templates")))
errs = []
for f in ("_v5_partials/spa_nav.html", "_v5_partials/knk_sticky_head.html"):
    try:
        env.parse(open(os.path.join(ROOT, "app", "templates", f), encoding="utf-8").read())
    except Exception as e:
        errs.append("%s: %s" % (f, e))
check("두 조각 문법 정상", not errs, errs)
print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
