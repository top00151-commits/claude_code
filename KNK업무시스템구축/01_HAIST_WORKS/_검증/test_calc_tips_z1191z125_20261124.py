# -*- coding: utf-8 -*-
"""z1191z125 (대표 11-24 「계산 칸 제목에 마우스 → 계산 설명 · 96개 모두」):
   ① 화면에서 쓰는 설명 키가 모두 app/calc_tips.py 에 있다(오타 = 설명 안 뜸)
   ② 설명 글은 비지 않고 150자 안 · 속성으로 넣을 때 따옴표가 깨지지 않는다
   ③ 공용 풍선이 모든 화면 틀(chrome.html)에 들어 있다
   ④ 고친 템플릿이 모두 문법 오류 없이 읽힌다
   ⑤ 수주 목록 「이번주·이번달 납기」: 금액은 통화별(₩ 하나로 안 더함)"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app import calc_tips as CT
R = []
def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:300]))
TD = os.path.join(ROOT, "app", "templates")
FILES = ["sales_home", "sales_drill", "sales_report", "sales_order_detail", "sales_orders", "sales_outstanding", "sales_receipts_check",
         "sales_shipments_receipts", "sales_fx_gain", "sales_quotations", "sales_opportunities", "bank_recon", "project_detail",
         "project_quick_form", "schedule_board", "sales_glance"]
used, n_attr = set(), 0
for f in FILES:
    s = open(os.path.join(TD, f + ".html"), encoding="utf-8").read()
    ks = re.findall(r"(?:ct|calc_tip)\('([a-z_.]+)'\)", s) + re.findall(r"'([a-z]+\.[a-z_]+)'", " ".join(re.findall(r"ct\(\{[^}]*\}", s)))
    used |= set(ks)
    n_attr += len(re.findall(r"\{\{ ct\(|data-calc=", s))
missing = sorted(k for k in used if k not in CT.TIPS)
check("① 화면이 쓰는 설명 키 %d개 모두 있음" % len(used), not missing, missing)
check("① 설명 붙은 제목 90곳 넘음(%d)" % n_attr, n_attr >= 90, n_attr)
long_ = [k for k, v in CT.TIPS.items() if not v.strip() or len(v) > 150]
check("② 설명 글 비지 않고 150자 안", not long_, [(k, len(CT.TIPS[k])) for k in long_])
a = str(CT.attr("sales.order_rev"))
check("② 속성 모양 = data-calc=\"…\" · 따옴표 안 깨짐", a.startswith(' data-calc="') and a.count('"') == 2, a[:80])
check("② 없는 키는 아무것도 안 붙임", str(CT.attr("없는.키")) == "", CT.attr("없는.키"))
ch = open(os.path.join(TD, "_v5_partials", "chrome.html"), encoding="utf-8").read()
check("③ 모든 화면 틀에 풍선 조각 포함", "_v5_partials/knk_calc_tip.html" in ch)
pt = open(os.path.join(TD, "_v5_partials", "knk_calc_tip.html"), encoding="utf-8").read()
check("③ 풍선 = 중복 가드 · 휴대폰 누르기 · 스크롤하면 사라짐", "__knkCalcTipZ125" in pt and "touchstart" in pt and "'scroll', hide" in pt)
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader(TD))
errs = []
for f in FILES + ["_v5_partials/knk_calc_tip"]:
    try:
        env.parse(open(os.path.join(TD, f + ".html"), encoding="utf-8").read())
    except Exception as e:
        errs.append("%s: %s" % (f, e))
check("④ 템플릿 %d개 문법 정상" % (len(FILES) + 1), not errs, errs)
so = open(os.path.join(TD, "sales_orders.html"), encoding="utf-8").read()
check("⑤ 이번주·이번달 납기 금액 = 통화별(week_ccy·month_ccy)", "week_ccy" in so and "month_ccy" in so and "week_amount" not in so)
m = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check("⑤ 서버 = 이 탭 전체에서 다시 셈(최근 200건 아님) · 취소 제외", "[z1191z125] 이번주·이번달 납기" in m and "<>'CANCELLED' AND substr(o.due_date,1,10) BETWEEN" in m)
print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
