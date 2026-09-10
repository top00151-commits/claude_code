#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""z1097 통화 혼합 합계 시험 (대표 지시 2026-09-10 · "확인해봐" → "진행해")

무엇을 막는가
  원화와 달러를 **환산 없이 그대로 더한 금액**이 화면에 뜨는 것.
  대표 신고(2026-09-10): 프로젝트 005M2511 'BIM LINE' 아래쪽 「수주번호 합계」가
  $83,882.73 + ₩1,720,000 을 그냥 더해 **$1,803,882.73** 로 표시.
  운영 실측: 통화 섞인 프로젝트 25건 · 금액 오차 합계 약 41억원.
  ⭐ 같은 화면 **위쪽** '확정 매출' KPI 는 이미 통화별로 나눠 그리고 있었다 —
     한 곳만 고치고 끝낸 결과가 이 신고다(대표규정 「⛔한 곳만 고치고 완료 금지」).

⛔ 운영 DB 를 열지 않는다. 임시 DB + 아래 고정값으로만 한다.
   고정 환율은 **운영 exchange_rates 실측값**(2026-09-10 읽기전용 조회)을 그대로 옮긴 것.

실행:  python _검증/test_ccy_mix_total_20260910.py   → "실패 0" 이어야 통과
"""
import ast
import io
import os
import re
import sqlite3
import sys
import tempfile
import types

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from jinja2 import Environment, FileSystemLoader           # noqa: E402

TPL_DIR = os.path.join(ROOT, "app", "templates")
MAIN_PY = os.path.join(ROOT, "app", "main.py")

# ── app/main.py 의 **실제 함수 원문**만 뽑아 그대로 실행한다 ────────────────
#    (사본을 만들지 않는다. main.py 를 통째 import 하면 fastapi 등 운영 의존이
#     필요해 시험이 못 돌기 때문. 뽑는 대상은 아래 목록뿐이고, 못 찾으면 멈춘다.)
WANT = ["_fmt_qty", "_fmt_price", "_CCY_SYMBOL", "_fmt_money", "_ccy_sym",
        "_fx_load_rates", "_fx_pick", "_fx_rate_for", "_fx_to_krw",
        "_ccy_get", "_ccy_breakdown",
        "_recalc_project_amount", "_apply_project_amount"]
_tree = ast.parse(io.open(MAIN_PY, encoding="utf-8").read())
_picked, _found = [], set()
for _node in _tree.body:
    _nm = None
    if isinstance(_node, ast.FunctionDef):
        _nm = _node.name
    elif (isinstance(_node, ast.Assign) and len(_node.targets) == 1
          and isinstance(_node.targets[0], ast.Name)):
        _nm = _node.targets[0].id
    if _nm in WANT:
        _picked.append(_node)
        _found.add(_nm)
_miss = [w for w in WANT if w not in _found]
assert not _miss, "main.py 에서 못 찾은 것: %s" % _miss
M = types.ModuleType("knk_main_subset")
exec(compile(ast.Module(body=_picked, type_ignores=[]), MAIN_PY, "exec"), M.__dict__)

# ── 운영 월 기준환율 실측값 (2026-09-10 읽기전용 조회) ──────────────────────
REAL_USD = {
    "2025-07": 1366.95, "2025-08": 1375.22, "2025-09": 1389.66,
    "2025-10": 1391.83, "2025-11": 1423.36, "2025-12": 1457.77,
    "2026-01": 1467.40, "2026-02": 1456.51, "2026-03": 1449.32,
    "2026-04": 1486.64, "2026-05": 1487.39, "2026-06": 1490.11,
    "2026-07": 1527.30, "2026-08": 1497.43,
}
REAL_EUR = {"2026-04": 1718.26, "2026-08": 1709.78}

# 환율표는 **운영과 같은 방식**으로 만든다 — 손으로 만든 dict 가 아니라
# 실제 _fx_load_rates() 가 exchange_rates 를 읽게 한다(1일 행만 읽는 규칙까지 함께 검사).
_mem = sqlite3.connect(":memory:")
_mem.execute("CREATE TABLE exchange_rates(id INTEGER PRIMARY KEY, rate_date TEXT, "
             "from_currency TEXT, to_currency TEXT, rate REAL)")
for _ym, _v in list(REAL_USD.items()):
    _mem.execute("INSERT INTO exchange_rates(rate_date,from_currency,to_currency,rate) "
                 "VALUES(?,?,?,?)", (_ym + "-01", "USD", "KRW", _v))
for _ym, _v in list(REAL_EUR.items()):
    _mem.execute("INSERT INTO exchange_rates(rate_date,from_currency,to_currency,rate) "
                 "VALUES(?,?,?,?)", (_ym + "-01", "EUR", "KRW", _v))
# 1일이 아닌 행(z1072 덮임 방지) — 이 값이 읽히면 안 된다
_mem.execute("INSERT INTO exchange_rates(rate_date,from_currency,to_currency,rate) "
             "VALUES('2026-04-15','USD','KRW',9999.0)")
RATES = M._fx_load_rates(_mem)              # JPY 는 일부러 없음(미등록 시험용)

PASS, FAIL = [], []


def chk(no, name, cond, detail=""):
    (PASS if cond else FAIL).append(no)
    print("  %s %2s. %s%s" % ("OK  " if cond else "실패", no, name,
                              ("" if cond else "   → " + str(detail))))


def near(a, b, tol=0.01):
    if a is None or b is None:
        return a is b
    return abs(float(a) - float(b)) <= tol


# ═══════════════════════════════════════════════════════════════════════════
print("\n§1 공용 함수 _ccy_breakdown — 합산 규칙 한 곳")
chk(0, "환율표는 '매월 1일' 행만 읽는다(z1072 규칙 유지 · 4/15 의 9999 무시)",
    RATES.get("USD", {}).get("2026-04") == 1486.64, RATES.get("USD", {}).get("2026-04"))

bd = M._ccy_breakdown([], "amt", "cur", rates=RATES)
chk(1, "건이 없으면 통화줄 없음·섞임 아님", bd["by_ccy"] == [] and bd["mixed"] is False, bd)

rows = [{"amt": 1000, "cur": "KRW"}, {"amt": 2000, "cur": "KRW"}, {"amt": 500, "cur": "KRW"}]
bd = M._ccy_breakdown(rows, "amt", "cur", rates=RATES)
chk(2, "원화만 3건 → 섞임 아님·합 3,500",
    bd["mixed"] is False and len(bd["by_ccy"]) == 1 and near(bd["by_ccy"][0]["total"], 3500)
    and bd["by_ccy"][0]["cnt"] == 3, bd)

rows = [{"amt": 100, "cur": "USD", "dd": "2026-04-10"},
        {"amt": 200, "cur": "USD", "dd": "2026-08-05"}]
bd = M._ccy_breakdown(rows, "amt", "cur", date_keys=("dd",), rates=RATES)
exp = 100 * 1486.64 + 200 * 1497.43
chk(3, "달러만 2건 → 각 건 '그 달' 환율로 환산",
    bd["mixed"] is False and near(bd["krw"], exp), (bd["krw"], exp))

rows = [{"amt": 1720000, "cur": "KRW", "dd": "2026-08-19"},
        {"amt": 83882.73, "cur": "USD", "dd": "2026-04-01"}]
bd = M._ccy_breakdown(rows, "amt", "cur", date_keys=("dd",), rates=RATES)
exp_krw = 1720000 + 83882.73 * 1486.64
chk(4, "원화+달러 섞임 → 통화별 2줄·금액 큰 순",
    bd["mixed"] is True and len(bd["by_ccy"]) == 2
    and bd["by_ccy"][0]["currency"] == "KRW", [r["currency"] for r in bd["by_ccy"]])
chk(5, "섞임 원화 합계 = 각 건 기준월 환율 환산", near(bd["krw"], exp_krw), (bd["krw"], exp_krw))
chk(6, "통화 무시 단순합(naive)은 원화 합계와 다르다 — 이것이 결함의 정체",
    near(bd["naive"], 1803882.73) and not near(bd["naive"], bd["krw"], 1.0),
    (bd["naive"], bd["krw"]))

rows = [{"amt": 100, "cur": "KRW"}, {"amt": 50, "cur": "JPY"}]
bd = M._ccy_breakdown(rows, "amt", "cur", rates=RATES)
chk(7, "환율 없는 통화 → 원화 합계를 아예 안 낸다(반쪽 숫자 금지)",
    bd["krw"] is None and any(m[0] == "JPY" for m in bd["missing"]), bd)

rows = [{"amt": 100, "cur": ""}, {"amt": 100, "cur": None}, {"amt": 100}]
bd = M._ccy_breakdown(rows, "amt", "cur", rates=RATES)
chk(8, "통화 칸이 비면 원화로 본다",
    bd["mixed"] is False and bd["by_ccy"][0]["currency"] == "KRW"
    and near(bd["by_ccy"][0]["total"], 300), bd)

rows = [{"amt": None, "cur": "KRW"}, {"amt": "abc", "cur": "KRW"}, {"amt": "1,000", "cur": "KRW"}]
bd = M._ccy_breakdown(rows, "amt", "cur", rates=RATES)
chk(9, "금액이 비었거나 글자여도 죽지 않는다", near(bd["by_ccy"][0]["total"], 0), bd)

bd = M._ccy_breakdown([{"amt": 100, "cur": "USD", "dd": "2026-04-01"}], "amt", "cur",
                      date_keys=("dd",), rates=None)
chk(10, "환율표를 안 주면 원화 합계 없이 통화별만",
     bd["krw"] is None and len(bd["by_ccy"]) == 1, bd)


# ═══════════════════════════════════════════════════════════════════════════
print("\n§2 대표 신고 건 재현 — 005M2511 'BIM LINE' 실제 값")
SO_BIM = [
    {"order_no": "M-251127-1", "currency": "USD", "total_amount": 83882.73,
     "due_date": "2026-04-01", "order_date": "2025-11-27", "form_key": "", "unit_qty": 1},
    {"order_no": "M-260819-2", "currency": "KRW", "total_amount": 1720000.00,
     "due_date": "2026-08-19", "order_date": "2026-08-19", "form_key": "", "unit_qty": 1},
]
bim = M._ccy_breakdown(SO_BIM, "total_amount", "currency",
                       date_keys=("due_date", "order_date"), rates=RATES)
chk(11, "옛 방식 단순합이 사진의 1,803,882.73 과 같다(결함 정확히 재현)",
     near(bim["naive"], 1803882.73), bim["naive"])
chk(12, "새 방식: 달러·원화 두 줄로 분리",
     bim["mixed"] is True
     and sorted(r["currency"] for r in bim["by_ccy"]) == ["KRW", "USD"],
     [r["currency"] for r in bim["by_ccy"]])
chk(13, "새 방식 원화 합계 = 126,423,421.73 (운영 실측값과 일치)",
     near(bim["krw"], 126423421.73, 0.02), bim["krw"])


# ═══════════════════════════════════════════════════════════════════════════
print("\n§3 실제 템플릿 렌더 — project_detail.html 「수주번호 합계」")
env = Environment(loader=FileSystemLoader(TPL_DIR))
for _n in ("qtyfmt", "pricefmt", "money", "ccysym"):
    env.filters[_n] = getattr(M, {"qtyfmt": "_fmt_qty", "pricefmt": "_fmt_price",
                                  "money": "_fmt_money", "ccysym": "_ccy_sym"}[_n])
    env.globals[_n] = env.filters[_n]
env.globals.update({"url_for": lambda *a, **k: "#",
                    "vname": lambda *a, **k: "", "vname_full": lambda *a, **k: ""})
CCY_NS = env.get_template("_v5_partials/knk_ccy_total.html").module

SRC_PD = io.open(os.path.join(TPL_DIR, "project_detail.html"), encoding="utf-8").read()


def slice_between(src, start_marker, end_marker):
    i = src.index(start_marker)
    j = src.index(end_marker, i) + len(end_marker)
    return src[i:j]


BLOCK_TOTAL = slice_between(
    SRC_PD, "{% set _gtotal = namespace(",
    'title="단가·금액은 영업·관리 권한자만">(수주번호 합계)</span>{% endif %}')


def render_total(orders, proj, can_amt=True):
    bd = M._ccy_breakdown(orders, "total_amount", "currency",
                          date_keys=("due_date", "order_date"), rates=RATES)
    return env.from_string(BLOCK_TOTAL).render(
        _ccy=CCY_NS, project_orders=orders, p=proj,
        so_total_bd=bd, can_sales_amt=can_amt)


P_BIM = {"currency": "USD", "fx_rate": 1456.51}
html = render_total(SO_BIM, P_BIM)
chk(14, "섞임: 옛 숫자 1,803,882.73 이 화면에서 사라졌다", "1,803,882.73" not in html, html[:200])
chk(15, "섞임: 달러 $83,882.73 가 그대로 보인다", "$83,882.73" in html, html[:200])
chk(16, "섞임: 원화 ₩1,720,000 이 그대로 보인다", "₩1,720,000" in html, html[:200])
chk(17, "섞임: 월 기준환율로 바꾼 합계 ₩126,423,422 병기",
     "126,423,42" in html and "월 기준환율" in html, html[:400])
chk(18, "섞임: 프로젝트 환율(1,456.51) 병기 줄은 안 나온다(기준이 둘이면 혼란)",
     "1,456.51" not in html, html[:400])

SO_USD1 = [{"order_no": "A", "currency": "USD", "total_amount": 1000.0,
            "due_date": "2026-04-01", "form_key": "", "unit_qty": 1}]
html1 = render_total(SO_USD1, P_BIM)
chk(19, "통화 하나(USD): 예전 그대로 $1,000.00 + 프로젝트 환율 병기",
     "$1,000.00" in html1 and "1,456.51" in html1, html1[:400])

SO_KRW1 = [{"order_no": "A", "currency": "KRW", "total_amount": 5000000.0,
            "due_date": "2026-04-01", "form_key": "", "unit_qty": 1}]
html2 = render_total(SO_KRW1, {"currency": "KRW", "fx_rate": None})
chk(20, "통화 하나(KRW): 예전 그대로 ₩5,000,000 · 환산줄 없음",
     "₩5,000,000" in html2 and "월 기준환율" not in html2, html2[:400])

html3 = render_total(SO_BIM, P_BIM, can_amt=False)
chk(21, "금액 권한 없으면 잠김 표시만(금액 노출 없음)",
     "🔒" in html3 and "83,882" not in html3, html3[:200])

chk(22, "수량 집계(총 수량·완제품 대분)는 그대로 살아 있다",
     "총 수주번호" in html and "_gtotal" not in html, html[:200])


# ═══════════════════════════════════════════════════════════════════════════
print("\n§4 자식 프로젝트 「소모품·수리 누적」")
BLOCK_CHILD = slice_between(
    SRC_PD, "<td class=\"num\" style=\"color:var(--knk-red);\">{% if can_sales_amt %}",
    "{% else %}🔒{% endif %}</td>")
KIDS = [{"currency": "KRW", "total_so_amount": 3000000, "last_so_date": "2026-08-01"},
        {"currency": "USD", "total_so_amount": 2000.0, "last_so_date": "2026-04-01"}]
cbd = M._ccy_breakdown(KIDS, "total_so_amount", "currency",
                       date_keys=("last_so_date",), rates=RATES)
h4 = env.from_string(BLOCK_CHILD).render(_ccy=CCY_NS, child_total_bd=cbd, can_sales_amt=True)
chk(23, "섞임: 통화별로 나뉜다(₩3,000,000 · $2,000.00)",
     "₩3,000,000" in h4 and "$2,000.00" in h4, h4[:300])
chk(24, "섞임: 통화 무시 단순합 3,002,000 은 안 나온다", "3,002,000" not in h4, h4[:300])
chk(25, "섞임: 원화 합계 ₩5,973,280 병기",
     M._fmt_money(3000000 + 2000 * 1486.64, "KRW").replace("₩", "") in h4, h4[:300])
chk(26, "안내문이 더 이상 '통화 환산 미포함' 이라 말하지 않는다",
     "통화 환산 미포함" not in SRC_PD, "옛 안내문 잔존")


# ═══════════════════════════════════════════════════════════════════════════
print("\n§5 고객사 상세 「총 수주액」")
SRC_CD = io.open(os.path.join(TPL_DIR, "customer_detail.html"), encoding="utf-8").read()
BLOCK_CUST = slice_between(
    SRC_CD, '<div class="kpi-card"><div class="kpi-label">총 수주액</div>', "</div></div>")


def render_cust(pjts):
    bd = M._ccy_breakdown(pjts, "order_amount", "currency",
                          date_keys=("order_date", "due_date"), rates=RATES)
    return env.from_string(BLOCK_CUST).render(_ccy=CCY_NS, pjts=pjts, pjts_total_bd=bd)


MIXED_P = [{"order_amount": 313866272, "currency": "KRW", "order_date": "2026-08-01"},
           {"order_amount": 29008, "currency": "USD", "order_date": "2026-08-01"}]
h5 = render_cust(MIXED_P)
chk(27, "섞임(삼성전자 실측 조합): 통화별로 나뉜다",
     "₩313,866,272" in h5 and "$29,008.00" in h5, h5[:300])
chk(28, "섞임: 옛 단순합 313,895,280 이 안 나온다", "313,895,280" not in h5, h5[:300])
chk(29, "섞임: 원화 합계 병기(약 ₩357,297,527)",
     M._fmt_money(313866272 + 29008 * 1497.43, "KRW").replace("₩", "") in h5, h5[:300])
h6 = render_cust([{"order_amount": 5000, "currency": "USD", "order_date": "2026-08-01"}])
chk(30, "달러만 있는 고객사: '원' 이 아니라 $5,000.00 으로 정확히 적는다",
     "$5,000.00" in h6 and "원" not in h6, h6[:300])
h7 = render_cust([{"order_amount": 1000000, "currency": "KRW", "order_date": "2026-08-01"}])
chk(31, "원화만: ₩1,000,000", "₩1,000,000" in h7, h7[:300])


# ═══════════════════════════════════════════════════════════════════════════
print("\n§6 역검사 — 어긴 코드(옛 방식)로 바꾸면 시험이 실제로 잡는가")
OLD_BLOCK = """{% set _g = namespace(t=0) %}
{% for _so in project_orders %}{% set _g.t = _g.t + (_so.total_amount or 0) %}{% endfor %}
{{ money(_g.t, p.currency or 'KRW') }}"""
old_html = env.from_string(OLD_BLOCK).render(project_orders=SO_BIM, p=P_BIM)
chk(32, "옛 코드는 1,803,882.73 을 실제로 뱉는다(시험이 헛돌지 않음을 증명)",
     "1,803,882.73" in old_html, old_html)
chk(33, "그 옛 출력은 §3의 14번 조건을 통과하지 못한다(검사가 차별력 있음)",
     not ("1,803,882.73" not in old_html), old_html)


# ═══════════════════════════════════════════════════════════════════════════
print("\n§7 전수 — 매출·영업 화면에 통화 무시 금액 합산이 남아 있는가")
# 세션05(자재구매) 소유 파일은 이 시험의 담당이 아니다 — 대신 고치지 않는다(업무분장 V2).
S05_OWNED = {"po_list.html", "po_detail.html", "stock_balances.html", "stock_issues.html"}
MONEY_SUM = re.compile(r"\|\s*sum\(attribute\s*=\s*['\"]"
                       r"(total_amount|order_amount|total_so_amount|amount|price)['\"]")
JINJA_COMMENT = re.compile(r"\{#.*?#\}", re.S)
hits = []
for dirpath, _dn, files in os.walk(TPL_DIR):
    for fn in files:
        if not fn.endswith(".html"):
            continue
        if fn in S05_OWNED or "_legacy" in dirpath or fn.startswith("_legacy"):
            continue
        fp = os.path.join(dirpath, fn)
        body = JINJA_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"),
                                 io.open(fp, encoding="utf-8").read())
        for i, ln in enumerate(body.split("\n"), 1):
            if MONEY_SUM.search(ln):
                hits.append("%s:%d" % (fn, i))
chk(34, "매출·영업 템플릿에 통화 무시 금액 합산 0건", not hits, hits)

chk(35, "공용 표기 한 벌을 실제로 쓰고 있다(세 화면 모두)",
     SRC_PD.count("_ccy.ccy_total(") == 2 and SRC_CD.count("_ccy.ccy_total(") == 1,
     (SRC_PD.count("_ccy.ccy_total("), SRC_CD.count("_ccy.ccy_total(")))


# ===========================================================================
print("\n§8 배포 전 검사기(check_ccy_sum) 를 어긴 코드로 시험")
#   대표규정: 규정을 만들면 **어긴 코드로 검사기를 시험**해 실제로 잡히는지 확인한다.
import importlib.util                                       # noqa: E402
_cs_path = os.path.join(ROOT, "deploy", "check_standards.py")
_spec = importlib.util.spec_from_file_location("knk_check_standards", _cs_path)
CS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CS)

_lab = tempfile.mkdtemp(prefix="knk_ccychk_")


def probe(name, body):
    """가짜 템플릿 한 장을 만들어 검사기에 통과시키고 잡힌 줄 번호를 돌려준다."""
    fp = os.path.join(_lab, name)
    io.open(fp, "w", encoding="utf-8", newline="").write(body)
    return [ln for _f, ln, _m in CS.check_ccy_sum([fp])]


NL = chr(10)
chk(36, "위반① |sum(attribute='total_amount') 을 잡는다",
     probe("v1.html", "{% set t = orders|sum(attribute='total_amount') %}") == [1])
chk(37, "위반② namespace 금액 누적을 잡는다",
     probe("v2.html", "{% set ns = namespace(t=0) %}" + NL +
                     "{% set ns.t = ns.t + (o.total_amount or 0) %}") == [2])
chk(38, "위반③ order_amount 합산도 잡는다",
     probe("v3.html", "{{ pjts|sum(attribute='order_amount') }}") == [1])
chk(39, "정당① 수량 합산(qty)은 안 잡는다",
     probe("g1.html", "{% set q = items|sum(attribute='qty') %}") == [])
chk(40, "정당② 공수 합산(hours)은 안 잡는다",
     probe("g2.html", "{% set h = tasks|sum(attribute='hours') %}") == [])
chk(41, "정당③ 주석 안의 위반 문구는 안 잡는다(이 규칙을 설명하는 주석이 잡히면 안 됨)",
     probe("g3.html",
           "{# 예전엔 orders|sum(attribute='total_amount') 였다 #}" + NL +
           "{{ _ccy.ccy_total(so_total_bd) }}") == [])
chk(42, "정당④ 공용 매크로 호출은 안 잡는다",
     probe("g4.html", "{{ _ccy.ccy_total(pjts_total_bd, compact=true) }}") == [])
_real3 = [os.path.join(TPL_DIR, "project_detail.html"),
          os.path.join(TPL_DIR, "customer_detail.html"),
          os.path.join(TPL_DIR, "_v5_partials", "knk_ccy_total.html")]
chk(43, "고친 실제 파일 3장은 검사기를 통과한다",
     CS.check_ccy_sum(_real3) == [], CS.check_ccy_sum(_real3))

# ===========================================================================
print("\n§9 홈 화면 경영진 월매출 KPI — 같은 결함이 여기에도 있었다")
#   실측(2026-09-10 운영 읽기전용): 2026-07 화면 186,149,155.45원 vs
#   올바름 325,279,718.79원 — 1억 3,913만원(43%)이 빠져 있었다.
#   원인은 SUM(projects.order_amount) 한 줄 — 달러 프로젝트를 원화처럼 더했다.
JUL = [{"currency": "KRW", "order_amount": 186058000.0, "order_date": "2026-07-15"},
       {"currency": "USD", "order_amount": 91155.45, "order_date": "2026-07-15"}]
_jul = M._ccy_breakdown(JUL, "order_amount", "currency",
                        date_keys=("order_date",), rates=RATES)
chk(44, "옛 방식 단순합이 실측 화면값 186,149,155.45 와 같다(결함 재현)",
     near(_jul["naive"], 186149155.45), _jul["naive"])
chk(45, "새 방식 원화 합계 = 325,279,718.79 (실측 올바른 값과 일치)",
     near(_jul["krw"], 325279718.79, 0.02), _jul["krw"])
chk(46, "홈 KPI 코드가 통화 무시 단순합(SUM(order_amount)) 을 더 이상 쓰지 않는다",
     "SELECT COALESCE(SUM(order_amount),0) AS t " not in
     io.open(MAIN_PY, encoding="utf-8").read(),
     "main.py 에 옛 쿼리가 남아 있음")
chk(47, "홈 KPI 가 공용 _ccy_breakdown 을 쓴다",
     "_month_krw" in io.open(MAIN_PY, encoding="utf-8").read())

# ===========================================================================
print("\n§10 저장값 재계산 — 화면만 고치면 되살아난다")
#   z1097 은 화면을 고쳤다. 그런데 projects.order_amount 를 채우는 자리가 서버에 14곳
#   남아 있었고 전부 통화를 안 봤다 → 수주를 고치거나 상세를 열 때마다 다시 오염됐다.
#   z1093(매 기동 팀 시드)·z1094(기동 백필)와 같은 되살아남 함정.


def _mkdb():
    """운영과 같은 모양의 임시 DB(projects·orders·exchange_rates)."""
    d = sqlite3.connect(":memory:")
    d.row_factory = sqlite3.Row
    d.execute("CREATE TABLE projects(id INTEGER PRIMARY KEY, currency TEXT, order_amount REAL)")
    d.execute("CREATE TABLE orders(id INTEGER PRIMARY KEY, project_id INT, currency TEXT,"
              " total_amount REAL, due_date TEXT, order_date TEXT, status TEXT)")
    d.execute("CREATE TABLE exchange_rates(id INTEGER PRIMARY KEY, rate_date TEXT,"
              " from_currency TEXT, to_currency TEXT, rate REAL)")
    for _y, _v in list(REAL_USD.items()):
        d.execute("INSERT INTO exchange_rates(rate_date,from_currency,to_currency,rate)"
                  " VALUES(?,?,?,?)", (_y + "-01", "USD", "KRW", _v))
    return d


def _seed(d, pccy, orders, amt=0):
    d.execute("INSERT INTO projects(id,currency,order_amount) VALUES(1,?,?)", (pccy, amt))
    for i, o in enumerate(orders, 1):
        d.execute("INSERT INTO orders(id,project_id,currency,total_amount,due_date,status)"
                  " VALUES(?,1,?,?,?,?)", (i, o[0], o[1], o[2], o[3] if len(o) > 3 else None))
    return d


_d = _seed(_mkdb(), "KRW", [("KRW", 1000.0, "2026-04-10"), ("KRW", 2000.0, "2026-04-10")])
chk(48, "통화 하나(원화) → 예전과 같은 단순 합 3,000",
     near(M._recalc_project_amount(_d, 1), 3000.0))

_d = _seed(_mkdb(), "USD", [("USD", 100.0, "2026-04-10"), ("USD", 50.0, "2026-04-10")])
chk(49, "통화 하나(달러) → 환산하지 않고 150.00 그대로",
     near(M._recalc_project_amount(_d, 1), 150.0))

_d = _seed(_mkdb(), "KRW", [("KRW", 205500000.0, "2026-02-01"), ("USD", 425052.0, "2026-02-01")])
chk(50, "섞임 + 프로젝트=원화 → 원화 환산 합계 824,592,488.52 (운영 실측 003M2509)",
     near(M._recalc_project_amount(_d, 1), 205500000 + 425052 * 1456.51, 0.05),
     M._recalc_project_amount(_d, 1))

_d = _seed(_mkdb(), "USD", [("USD", 83882.73, "2026-04-01"), ("KRW", 1720000.0, "2026-08-19")])
_exp = round((83882.73 * 1486.64 + 1720000) / 1497.43, 2)   # 최신 납품월(8월) 환율로 되돌림
chk(51, "섞임 + 프로젝트=달러(BIM LINE) → 달러 기준 합계",
     near(M._recalc_project_amount(_d, 1), _exp, 0.02),
     (M._recalc_project_amount(_d, 1), _exp))
chk(52, "그 값은 옛 단순합 1,803,882.73 과 전혀 다르다",
     not near(M._recalc_project_amount(_d, 1), 1803882.73, 1.0))

_d = _seed(_mkdb(), "KRW", [("KRW", 100.0, "2026-04-10"), ("JPY", 50.0, "2026-04-10")])
chk(53, "환율 없는 통화가 섞이면 None — 반쪽 숫자로 덮어쓰지 않는다",
     M._recalc_project_amount(_d, 1) is None, M._recalc_project_amount(_d, 1))

_d = _mkdb()
_d.execute("INSERT INTO projects(id,currency,order_amount) VALUES(1,'KRW',0)")
chk(54, "수주가 없으면 0.0", near(M._recalc_project_amount(_d, 1), 0.0))

_d = _seed(_mkdb(), "KRW", [("KRW", 1000.0, "2026-04-10", "CANCELLED"),
                            ("KRW", 2000.0, "2026-04-10", "")])
chk(55, "취소 수주 제외 옵션이 실제로 뺀다 (3,000 → 2,000)",
     near(M._recalc_project_amount(_d, 1), 3000.0)
     and near(M._recalc_project_amount(_d, 1, exclude_cancelled=True), 2000.0),
     (M._recalc_project_amount(_d, 1), M._recalc_project_amount(_d, 1, exclude_cancelled=True)))

_d = _seed(_mkdb(), "KRW", [("KRW", 1000.0, "2026-04-10")], amt=999999.0)
M._apply_project_amount(_d, 1)
chk(56, "_apply_project_amount 가 실제로 저장한다 (999,999 → 1,000)",
     near(_d.execute("SELECT order_amount FROM projects WHERE id=1").fetchone()[0], 1000.0))

_d = _seed(_mkdb(), "KRW", [("KRW", 100.0, "2026-04-10"), ("JPY", 50.0, "2026-04-10")], amt=777.0)
_r = M._apply_project_amount(_d, 1)
chk(57, "환율이 없으면 저장하지 않고 기존 값을 지킨다 (777 유지)",
     _r is None
     and near(_d.execute("SELECT order_amount FROM projects WHERE id=1").fetchone()[0], 777.0))

print("\n§11 서버 코드 검사기(check_project_amount_sum) 역검사")
_lab2 = tempfile.mkdtemp(prefix="knk_pa_")
os.makedirs(os.path.join(_lab2, "app"), exist_ok=True)


def probe_py(body):
    io.open(os.path.join(_lab2, "app", "main.py"), "w", encoding="utf-8",
            newline="").write(body)
    _old = CS.ROOT
    CS.ROOT = _lab2
    try:
        return [ln for _f, ln, _m in CS.check_project_amount_sum()]
    finally:
        CS.ROOT = _old


chk(58, "위반① UPDATE projects SET order_amount 직접 실행을 잡는다",
     probe_py('c.execute("UPDATE projects SET order_amount=? WHERE id=?", (v, pid))') == [1])
chk(59, "위반② SUM(total_amount) FROM orders WHERE project_id 직접 조회를 잡는다",
     probe_py('row = c.execute("SELECT SUM(total_amount) FROM orders WHERE project_id=?", (pid,))')
     == [1])
chk(60, "면제 ccy-ok 표식이 있으면 안 잡는다",
     probe_py("# ccy-ok: 값은 _recalc_project_amount 결과" + NL +
              'c.execute("UPDATE projects SET order_amount=? WHERE id=?", (v, pid))') == [])
chk(61, "공용 함수 몸통 안은 안 잡는다",
     probe_py("def _apply_project_amount(c, pid):" + NL +
              '    c.execute("UPDATE projects SET order_amount=? WHERE id=?", (v, pid))') == [])
chk(62, "관계없는 UPDATE 는 안 잡는다",
     probe_py('c.execute("UPDATE projects SET status=? WHERE id=?", (v, pid))') == [])
chk(63, "지금 배포할 main.py 는 이 검사를 통과한다",
     CS.check_project_amount_sum() == [], CS.check_project_amount_sum())

# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 66)
print("  통과 %d건 · 실패 %d건" % (len(PASS), len(FAIL)))
if FAIL:
    print("  실패 번호: %s" % ", ".join(str(x) for x in FAIL))
print("=" * 66)
sys.exit(1 if FAIL else 0)
