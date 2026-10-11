#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""z1158 시험 — 고객 고르기 목록 전부를 기준 한 곳(customer_tier)으로 (대표 2026-10-11 「전부 같은 기준」).

겪은 것: 고르기 목록마다 정식 상호만 보여 같은 상호 「(주) 드림텍」 본사·아산·동탄이 똑같은 세 줄이었고,
  일일업무는 고른 글자로 고객을 찾아 **늘 첫 번째(본사)로 기록**했다. 순서도 화면마다 제각각(이름순·등급 글자순).
고친 뒤: 보이는 이름 = 시스템명 우선 + [종사업장번호](공용 선택기 z621 와 같다) · 순서 = VIP 먼저 → 보이는 이름 가나다.

§1 기준(진짜 함수·진짜 정렬)  §2 앱 통째 — 고르기 화면 8곳 + 공용 API + 공용 함수
§3 일일업무 — 화면에 실린 진짜 pickFromDatalist() 를 node 로 돌려 「고른 그 사업장」으로 기록되는지(+ 예전 모양은 늘 첫 번째)
§4 배포 전 검사기 + 되돌림 5종
⛔ 운영 DB 무접촉(임시 DB · 가상 고객). fastapi 가 깔린 파이썬 + node 가 필요하다.
실행: python _검증/test_customer_picker_z1158_20261011.py
"""
import io
import json
import os
import re
import shutil
import subprocess
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
sys.path.insert(0, os.path.join(ROOT, "deploy"))
os.environ["KNK_ENABLE_STOCK_DIRECT_ISSUE"] = "1"   # 운영에선 잠긴 「직접 출고」 화면 — 이 시험 안에서만 열어 순서를 본다

FAIL, CNT = [], 0


def check(name, ok, detail=""):
    global CNT
    CNT += 1
    print(("  ✅" if ok else "  ❌") + " %02d %s" % (CNT, name) + ("" if ok else "   ← %s" % (detail,)))
    if not ok:
        FAIL.append(name)


# ════════════════════════════════════════════════════════════════════
print("\n§1 기준 한 곳 — customer_tier.customer_pick_label · CUSTOMER_PICK_ORDER_SQL")
from app import customer_tier as CT   # noqa: E402
L = CT.customer_pick_label
check("시스템명이 있으면 시스템명 + [종사업장번호]", L({"name": "(주) 드림텍", "alias": "드림텍(아산)", "sub_biz_no": "0005"}) == "드림텍(아산) [0005]")
check("종사업장번호가 없으면 시스템명만", L({"name": "(주) 드림텍", "alias": "드림텍(본사)", "sub_biz_no": ""}) == "드림텍(본사)")
check("시스템명이 없으면 정식 상호", L({"name": "에스알씨", "alias": "", "sub_biz_no": None}) == "에스알씨")
check("공용 선택기 disp() 와 같은 규칙(customer_picker.html 원문에 같은 식이 있다)",
      "function disp(o){ return (o.alias||o.name)+(o.sub_biz_no?(' ['+o.sub_biz_no+']'):''); }"
      in io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "customer_picker.html"), encoding="utf-8").read())

# ════════════════════════════════════════════════════════════════════
print("\n§2 앱 통째 — 고르기 화면들")
import app.database as D   # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1158_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
D.init_db()
D.migrate_customers_name_unique()   # 운영은 앱이 켜질 때(startup) 상호 중복 금지를 푼다 — 같은 상호 여러 종사업장(드림텍 3곳)
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                     ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    c.execute("INSERT INTO users(id, name, login_id, password, role) VALUES(901,'시험대표','T901','x','ceo')")
    c.execute("DELETE FROM customers")
    for cid, name, alias, sub, tier in [
            (774, "(주) 드림텍", "드림텍(본사)", "", "VIP"), (775, "(주) 드림텍", "드림텍(아산)", "0005", "VIP"),
            (778, "(주) 드림텍", "드림텍(동탄)", "0007", "VIP"), (780, "주식회사 가나", "가나전자", "", "일반"),
            (781, "(주) 하휴면", "", "", "휴면"), (782, "Zeta Corp", "", "", "VIP")]:
        c.execute("INSERT INTO customers(id, name, alias, sub_biz_no, tier, is_active) VALUES(?,?,?,?,?,1)", (cid, name, alias, sub, tier))
import app.main as appmain                  # noqa: E402
from fastapi.testclient import TestClient   # noqa: E402
appmain.get_user = lambda request: {"id": 901, "name": "시험대표", "role": "ceo", "team_id": None, "lang": "ko", "can_use_logistics": 1, "can_use_sales": 1}
cl = TestClient(appmain.app, follow_redirects=False)
WANT = ["Zeta Corp", "드림텍(동탄) [0007]", "드림텍(본사)", "드림텍(아산) [0005]", "가나전자", "(주) 하휴면"]


def order_in(h):
    pos = {n: h.find(n) for n in WANT}
    return [n for n, p in sorted(pos.items(), key=lambda kv: kv[1]) if p >= 0]


for url, what in [("/home/2026-10-12", "오늘 업무"), ("/daily/2026-10-12", "일일업무"), ("/issues/new", "이슈 등록"),
                  ("/stock/issue", "재고 출고"), ("/consumables", "소모품"), ("/sales/quotes/new", "견적"),
                  ("/qc/inspection-reports/new", "품질 보고"), ("/contacts/new", "연락처")]:
    r = cl.get(url)
    o = order_in(r.text)
    check("%s %s → 200 · 시스템명·종사업장번호로 구별 · VIP 먼저(%s)" % (what, url, " | ".join(o)),
          r.status_code == 200 and o == WANT and r.text.count(">(주) 드림텍<") == 0, (r.status_code, o))
j = cl.get("/api/customers/options").json()
names = [(x["alias"] or x["name"]) + ((" [" + x["sub_biz_no"] + "]") if x.get("sub_biz_no") else "") for x in j.get("customers", [])]
check("공용 고객 선택기 API 순서도 같은 기준(%s)" % " | ".join(names), names == WANT, names)
check("공용 함수 customers_for_picker()(프로젝트 등록·영업 기회) 순서·이름표",
      [CT.customer_pick_label(x) for x in D.customers_for_picker()] == WANT)
h = cl.get("/quotes/new" if False else "/sales/quotes/new").text
check("견적 화면: 보이는 이름만 바뀌고 고르는 값은 고객 번호 그대로(value=775)", 'value="775">드림텍(아산) [0005]</option>' in h)

# ════════════════════════════════════════════════════════════════════
print("\n§3 일일업무 — 화면에 실린 진짜 pickFromDatalist() 를 node 로")
daily = cl.get("/daily/2026-10-12").text
m = re.search(r"function pickFromDatalist\(inputId, listId, dataAttr\) \{.*?\n  \}", daily, re.S)
check("화면에서 pickFromDatalist() 원문을 꺼냈다", m is not None)
opts_new = re.findall(r'<option data-cid="(\d+)" value="([^"]*)">', daily)
check("일일업무 목록의 글자가 모두 다르다(같은 상호도 구별) — %d개" % len(opts_new),
      len(opts_new) >= 6 and len({v for _, v in opts_new}) == len(opts_new), opts_new)


def run_pick(options, typed):
    js = ("const opts = %s;\n"
          "const document = { getElementById: () => ({ value: %s }),\n"
          "  querySelectorAll: () => opts.map(o => ({ value: o[1], dataset: { cid: o[0] } })) };\n"
          "%s\nconsole.log(JSON.stringify(pickFromDatalist('newCustomer', 'customerOptions', 'cid')));\n"
          % (json.dumps(options, ensure_ascii=False), json.dumps(typed, ensure_ascii=False), m.group(0)))
    p = subprocess.run(["node", "-e", js], capture_output=True, text=True, encoding="utf-8")
    return json.loads(p.stdout.strip() or "null")


if m:
    for cid, typed in [("775", "드림텍(아산) [0005]"), ("778", "드림텍(동탄) [0007]"), ("774", "드림텍(본사)")]:
        got = run_pick(opts_new, typed)
        check("「%s」 를 고르면 그 사업장(id %s)으로 기록" % (typed, cid), got and str(got.get("id")) == cid, got)
    old_opts = [(cid, "(주) 드림텍") for cid in ("774", "775", "778")]   # 예전 모양: 정식 상호만
    got = run_pick(old_opts, "(주) 드림텍")
    check("(비교) 예전 모양(정식 상호만)이면 어느 드림텍을 골라도 첫 번째(774)로 기록 — 신고된 버그", got and got.get("id") == 774, got)

# ════════════════════════════════════════════════════════════════════
print("\n§4 배포 전 검사기 — check_customer_picker")
import check_standards as CS   # noqa: E402
check("지금 코드: 위반 0", CS.check_customer_picker([]) == [], CS.check_customer_picker([])[:3])
_root, _tpl = CS.ROOT, CS.TPL
tmp = tempfile.mkdtemp(prefix="z1158chk_")


def fresh():
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(os.path.join(tmp, "app"))
    for f in os.listdir(os.path.join(ROOT, "app")):
        if f.endswith(".py"):
            shutil.copyfile(os.path.join(ROOT, "app", f), os.path.join(tmp, "app", f))
    shutil.copytree(os.path.join(ROOT, "app", "templates"), os.path.join(tmp, "app", "templates"))


def edit(rel, old, new):
    p = os.path.join(tmp, rel)
    s = io.open(p, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    assert s.count(old) >= 1, (rel, old[:50])
    io.open(p, "w", encoding="utf-8", newline="").write(s.replace(old, new, 1))


MUT = [
    ("app/templates/sales_quote_form.html", "{{ cust_label(c) }}</option>", "{{ c.name }}</option>", "①", "견적 고르기를 정식 상호만으로 되돌림"),
    ("app/templates/daily.html", 'value="{{ cust_label(c) }}"', 'value="{{ c.name }}"', "①", "일일업무를 정식 상호(=늘 첫 번째)로 되돌림"),
    ("app/main.py", '''"FROM customers WHERE COALESCE(is_active,1)=1 ORDER BY " + _CUST_PICK_ORDER_SQL).fetchall()''',
     '''"FROM customers WHERE COALESCE(is_active,1)=1 ORDER BY name COLLATE NOCASE").fetchall()''', "②", "공용 선택기 API 를 이름순으로 되돌림"),
    ("app/customer_tier.py", 'return base + (" [" + sub + "]" if sub else "")', 'return base', "③", "종사업장번호를 뺌"),
    ("app/main.py", 'tpl.env.globals["cust_label"] = _cust_pick_label', 'pass', "④", "템플릿 전역 등록을 뺌"),
]
try:
    for rel, old, new, mark, what in MUT:
        fresh()
        edit(rel, old, new)
        CS.ROOT, CS.TPL = tmp, os.path.join(tmp, "app", "templates")
        hits = CS.check_customer_picker([])
        check("되돌림 「%s」 → %s 로 잡힘 (%d건)" % (what, mark, len(hits)), any(x.lstrip().startswith(mark) for _, _, x in hits),
              [x for _, _, x in hits][:2])
    fresh()
    edit("app/templates/project_quick_form.html", "{# z1158-허용:", "{# 허용표시없음:")
    CS.ROOT, CS.TPL = tmp, os.path.join(tmp, "app", "templates")
    hits = CS.check_customer_picker([])
    check("허용 표시(z1158-허용)를 지우면 그 줄도 잡힌다(표시가 있어야만 예외)", any("project_quick_form" in p for p, _, _ in hits))
finally:
    CS.ROOT, CS.TPL = _root, _tpl
    shutil.rmtree(tmp, ignore_errors=True)

print("\n" + "=" * 60)
print("결과: %d개 중 실패 %d" % (CNT, len(FAIL)))
for n in FAIL:
    print("  ❌", n)
sys.exit(1 if FAIL else 0)
