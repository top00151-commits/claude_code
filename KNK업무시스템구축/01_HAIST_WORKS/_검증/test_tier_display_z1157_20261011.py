#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""z1157 시험 — 고객 등급의 화면 색·순서를 기준 한 곳(customer_tier.py)으로 (대표 2026-10-11 「등급순 · VIP 먼저」 · 재고 출고도 「같이 바꿈」).

겪은 것: 고객 목록·관리자 고객 표·고객 상세 제목이 옛 A·B 등급 색을 보고 있었다(지금 등급엔 색이 안 들어감).
  고르기 목록 5곳(오늘 업무·일일업무·관리자·이슈 등록·재고 출고 + 고객 목록 대체 목록)은 `ORDER BY tier DESC` 라
  휴면→주요→일반→신규→VIP 로 나왔다.

§1 기준 한 곳(진짜 함수·진짜 정렬)  §2 앱 통째(임시 DB) — 진짜 주소 7곳의 순서·색  §3 배포 전 검사기 + 되돌림 5종
⛔ 운영 DB 무접촉(임시 DB · 가상 고객). fastapi 가 깔린 파이썬이 필요하다.
실행: python _검증/test_tier_display_z1157_20261011.py
"""
import io
import os
import re
import shutil
import sqlite3
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
# 재고 「직접 출고」 화면은 운영에서 잠겨 있다(WP-01 · 대표 결정 2026-07-24) — 이 시험 안에서만 열어 고객 순서를 본다
os.environ["KNK_ENABLE_STOCK_DIRECT_ISSUE"] = "1"

FAIL, CNT = [], 0


def check(name, ok, detail=""):
    global CNT
    CNT += 1
    print(("  ✅" if ok else "  ❌") + " %02d %s" % (CNT, name) + ("" if ok else "   ← %s" % (detail,)))
    if not ok:
        FAIL.append(name)


# ════════════════════════════════════════════════════════════════════
print("\n§1 기준 한 곳 — customer_tier.py")
from app import customer_tier as CT   # noqa: E402
check("TIER_ORDER = VIP→주요→일반→신규→휴면", CT.TIER_ORDER == ("VIP", "주요", "일반", "신규", "휴면"))
check("등급마다 알약 색이 다르고 5단계를 다 가진다", set(CT.TIER_PILL) == set(CT.TIER_ORDER) and len(set(CT.TIER_PILL.values())) == 5)
check("모르는 값(옛 A)·빈 값은 회색", CT.tier_pill_class("A") == "pill-muted" and CT.tier_pill_class(None) == "pill-muted")
check("VIP 빨강 알약(pill-danger) · 신규 pill-warn · 일반 pill-done",
      CT.tier_pill_class("VIP") == "pill-danger" and CT.tier_pill_class("신규") == "pill-warn" and CT.tier_pill_class("일반") == "pill-done")
_db = sqlite3.connect(":memory:")
_db.execute("CREATE TABLE customers(name TEXT, tier TEXT)")
_db.executemany("INSERT INTO customers VALUES(?,?)", [("가", "휴면"), ("나", "신규"), ("다", "일반"), ("라", "주요"), ("마", "VIP"), ("바", "A")])
got = [r[0] for r in _db.execute("SELECT name FROM customers ORDER BY " + CT.TIER_ORDER_SQL + ", name")]
old = [r[0] for r in _db.execute("SELECT name FROM customers ORDER BY tier DESC, name")]
check("TIER_ORDER_SQL 로 실제 정렬 → 마(VIP) 라(주요) 다(일반) 나(신규) 가(휴면) 바(옛 A)", got == ["마", "라", "다", "나", "가", "바"], got)
check("(비교) 예전 `ORDER BY tier DESC` → 가(휴면)부터 — 신고된 순서", old[0] == "가" and old.index("마") > old.index("나"), old)

# ════════════════════════════════════════════════════════════════════
print("\n§2 앱 통째 — 진짜 주소")
import app.database as D   # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1157_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
D.init_db()
with D.db_session() as c:   # 운영 users 엔 있는데 코드가 안 만드는 칸 — 운영과 같은 모양으로
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                     ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                     ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
import app.main as appmain                  # noqa: E402
from fastapi.testclient import TestClient   # noqa: E402

with D.db_session() as c:
    c.execute("INSERT INTO users(id, name, login_id, password, role) VALUES(901,'시험대표','T901','x','ceo')")
    for cid, name, tier in [(701, "가휴면", "휴면"), (702, "나신규", "신규"), (703, "다일반", "일반"), (704, "라주요", "주요"),
                            (705, "마VIP", "VIP"), (706, "바VIP", "VIP"), (707, "사옛등급", "A")]:
        c.execute("INSERT INTO customers(id, name, tier) VALUES(?,?,?)", (cid, name, tier))
BOSS = {"id": 901, "name": "시험대표", "role": "ceo", "team_id": None, "lang": "ko"}
appmain.get_user = lambda request: BOSS
cl = TestClient(appmain.app, follow_redirects=False)
WANT = ["마VIP", "바VIP", "라주요", "다일반", "나신규", "가휴면", "사옛등급"]


def order_in(html):
    pos = {n: html.find(n) for n in WANT}
    return [n for n, p in sorted(pos.items(), key=lambda kv: kv[1]) if p >= 0]


for url, what in [("/home/2026-10-12", "오늘 업무(fetch_customers)"), ("/daily/2026-10-12", "일일업무(fetch_customers)"),
                  ("/issues/new", "이슈 등록"), ("/stock/issue", "재고 출고(세션 05 화면 · 대표 「같이 바꿈」)"),
                  ("/admin", "관리자 고객 표")]:
    r = cl.get(url)
    o = order_in(r.text)
    check("%s %s → 200 · VIP 먼저(%s)" % (what, url, " ".join(o)), r.status_code == 200 and o == WANT, (r.status_code, o))
h = cl.get("/admin").text
check("관리자 고객 표: 알약 색 = 기준 한 곳(VIP pill-danger · 신규 pill-warn · 옛 A 회색)",
      '<span class="pill pill-danger">VIP</span>' in h and '<span class="pill pill-warn">신규</span>' in h
      and '<span class="pill pill-muted">A</span>' in h and "role-badge role-admin\">VIP" not in h)
h = cl.get("/customers").text
check("고객 목록: VIP 빨강·주요 pill-progress·휴면 회색(예전엔 전부 회색)",
      '<span class="pill pill-danger">VIP</span>' in h and '<span class="pill pill-progress">주요</span>' in h
      and '<span class="pill pill-muted">휴면</span>' in h)
h = cl.get("/customer/705").text
check("고객 상세(VIP): 제목 옆 「등급 VIP」 도 빨강(예전엔 A·B 기준이라 회색)",
      re.search(r'class="pill pill-danger" style="font-size:13px;">등급 VIP', h) is not None)
check("고객 상세(VIP): 아래 칸 알약도 같은 색(한 화면 두 기준 없앰)",
      re.search(r'class="pill pill-danger" style="font-size:18px;', h) is not None)
h = cl.get("/customers/702/edit").text
check("고객 수정(신규): 알약 pill-warn", re.search(r'class="pill pill-warn" style="font-size:12px;font-weight:700;">\s*신규', h) is not None)

# ════════════════════════════════════════════════════════════════════
print("\n§3 배포 전 검사기 — check_tier_display")
import check_standards as CS   # noqa: E402
check("지금 코드: 위반 0", CS.check_tier_display([]) == [], CS.check_tier_display([])[:3])
_root, _tpl = CS.ROOT, CS.TPL
tmp = tempfile.mkdtemp(prefix="z1157chk_")


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
    assert s.count(old) >= 1, (rel, old[:40])
    io.open(p, "w", encoding="utf-8", newline="").write(s.replace(old, new, 1))


def run():
    CS.ROOT, CS.TPL = tmp, os.path.join(tmp, "app", "templates")
    return CS.check_tier_display([])


MUT = [
    ("app/templates/customers_list.html", '<span class="pill {{ tier_pill(c.tier) }}">{{ c.tier }}</span>',
     '<span class="pill {% if c.tier == \'A\' %}pill-danger{% else %}pill-muted{% endif %}">{{ c.tier }}</span>', "①", "옛 A·B 색을 되살림"),
    ("app/templates/customer_form.html", '<span class="pill {{ tier_pill(customer.tier) }}"',
     '<span class="pill {% if customer.tier == \'VIP\' %}pill-danger{% else %}pill-done{% endif %}"', "②", "화면이 알약 색을 스스로 고름"),
    ("app/main.py", '"SELECT id, name, tier FROM customers ORDER BY " + _TIER_ORDER_SQL + ", name"',
     '"SELECT id, name, tier FROM customers ORDER BY tier DESC, name"', "③", "등급 글자 정렬을 되살림"),
    ("app/customer_tier.py", 'TIER_ORDER = ("VIP", "주요", "일반", "신규", "휴면")',
     'TIER_ORDER = ("휴면", "주요", "일반", "신규", "VIP")', "④", "순서 기준을 뒤집음"),
    ("app/main.py", 'tpl.env.globals["tier_pill"] = _tier_pill_class', 'pass', "⑤", "템플릿 전역 등록을 뺌"),
]
try:
    for rel, old, new, mark, what in MUT:
        fresh()
        edit(rel, old, new)
        hits = run()
        check("되돌림 「%s」 → %s 로 잡힘 (%d건)" % (what, mark, len(hits)), any(m.lstrip().startswith(mark) for _, _, m in hits),
              [m for _, _, m in hits][:2])
finally:
    CS.ROOT, CS.TPL = _root, _tpl
    shutil.rmtree(tmp, ignore_errors=True)

print("\n" + "=" * 60)
print("결과: %d개 중 실패 %d" % (CNT, len(FAIL)))
for n in FAIL:
    print("  ❌", n)
sys.exit(1 if FAIL else 0)
