# -*- coding: utf-8 -*-
"""z1191z98 시험 — 매출·영업 메뉴 14 → 10 (대표 11-22 「5-6 합치는 작업 완료 후 1번도 바로 진행해」 · 한 가지 일은 한 곳에서만)
  §1 메뉴 10줄 순서 · 권한(매출 등록 없는 분은 💰 입금 안 보임)
  §2 한 메뉴 안의 탭 화면 → 그 메뉴에 불
  §3 💰 입금 탭 줄(입금 확인 · 미수 현황 · 입금 대사) · 채권 노화 → 미수 현황으로
  §4 📊 미수 현황 숫자 = 💰 입금 확인과 같은 계산(부가세 포함 · 계산서 기준) · 지난 날수 구간
  §5 🧾 마감 = 계산서 발행 대기만 위에 · 수금 입력 칸 없음 · 입금 숫자 대신 💰 입금 링크
  §6 🎯 수주 전 탭(영업 기회 · 견적서) · 새로 만들기 단추 없음 · 🆕 등록에 🎯 · 📋 카드
  §7 📋 프로젝트 탭 줄에 📑 수주 목록 · 수주 목록 화면에도 같은 탭 줄
  §8 📖 처음이면 안내 글
"""
import contextlib
import io
import os
import re
import sys
import tempfile
from datetime import date, timedelta

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z98-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z98_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                     ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                     ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if not conn.execute("SELECT 1 FROM teams WHERE id=1").fetchone():
        tcols = {r[1] for r in conn.execute("PRAGMA table_info(teams)")}
        if "code" in tcols:
            conn.execute("INSERT INTO teams (id, code, name) VALUES (1, '01', '기술영업팀')")
        else:
            conn.execute("INSERT INTO teams (id, name) VALUES (1, '기술영업팀')")
    ins = ("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, "
           "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
           "VALUES (?, ?, ?, ?, 'sso_only_no_local_password', 1, 1, 1, 1, ?, 0, 0)")
    conn.execute(ins, ("가상영업", "member", "Z981", "Z981", 1))
    conn.execute(ins, ("가상보기", "member", "Z982", "Z982", 0))
    conn.execute(ins, ("가상대표", "ceo", "Z983", "Z983", 1))
    SALES = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z981'").fetchone())
    VIEWER = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z982'").fetchone())
    CEO = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z983'").fetchone())
    conn.execute("INSERT INTO customers (name, pay_days) VALUES ('가상고객A', 30)")
    conn.execute("INSERT INTO customers (name, pay_days) VALUES ('가상고객B', 0)")
    CA = conn.execute("SELECT id FROM customers WHERE name='가상고객A'").fetchone()[0]
    CB = conn.execute("SELECT id FROM customers WHERE name='가상고객B'").fetchone()[0]
    conn.execute("INSERT OR IGNORE INTO field_access_policy (category, team_id) VALUES ('sales_amount', 1)")

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

S = {"user": SALES}
M.get_user = lambda request: S["user"]
cl = TestClient(M.app)
OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def main_part(h):
    i = h.find('<main')
    return h[i:] if i >= 0 else h


def menu(h):
    """매출·영업 묶음의 메뉴 주소 목록(공통 묶음 앞까지)."""
    a = h.find('<aside class="sidebar"')
    b = h.find('<div style="margin: 14px 14px; border-top', a)
    return re.findall(r'<a class="sb-item[^"]*" href="([^"]+)"', h[a:b])


def active(h):
    m = re.search(r'<a class="sb-item active" href="([^"]+)"', h)
    return m.group(1) if m else None


BASE = {"quick": "1", "biz_div": "T", "project_type": "NEW_EQUIP", "po_type": "신규", "status": "진행중",
        "confirm_now": "1", "order_date": "2026-07-01", "due_date": "2026-08-01", "currency": "KRW",
        "equip_name": "가상장비", "unit_qty": "1", "model": "가상모델", "prod_mode": "none",
        "unit_price": "1000000", "order_amount": "1000000"}


def reg(name, cust, status="SHIPPED"):
    f = dict(BASE, project_name=name, customer_name=cust, sales="가상영업")
    r = q(cl.post, "/projects/new", data=f, follow_redirects=False)
    assert r.status_code == 303, r.status_code
    with D.db_session() as c:
        pid = c.execute("SELECT id FROM projects WHERE name=?", (name,)).fetchone()[0]
        oid = c.execute("SELECT id FROM orders WHERE project_id=?", (pid,)).fetchone()[0]
        c.execute("UPDATE orders SET customer_id=?, status=?, total_amount=1000000 WHERE id=?",
                  (CA if cust == "가상고객A" else CB, status, oid))
        if not c.execute("SELECT 1 FROM order_items WHERE order_id=?", (oid,)).fetchone():
            c.execute("INSERT INTO order_items (order_id, qty, unit_price, amount) VALUES (?, 1, 1000000, 1000000)", (oid,))
        c.execute("UPDATE order_items SET unit_status='출하' WHERE order_id=?", (oid,))
    return oid


def tax(oid, d, amt):
    with D.db_session() as c:
        iid = c.execute("SELECT id FROM order_items WHERE order_id=? ORDER BY id LIMIT 1", (oid,)).fetchone()[0]
        c.execute("UPDATE order_items SET tax_invoice_date=?, tax_invoice_amt1=? WHERE id=?", (d, amt, iid))


T = date.today()
O1 = reg("합치기시험1", "가상고객A")   # 발행 80일 전 + 30일 = 50일 지남 → 31~60일
O2 = reg("합치기시험2", "가상고객A")   # 발행 10일 전 + 30일 = 예정일 전
O3 = reg("합치기시험3", "가상고객B")   # 결제 조건 안 고름 → 기본 60일 · 발행 200일 전 → 140일 지남 → 90일 넘음
O4 = reg("합치기시험4", "가상고객B")   # 출하했는데 계산서 안 끊음 → 🧾 마감 발행 대기
tax(O1, (T - timedelta(days=80)).isoformat(), 1000000)
tax(O2, (T - timedelta(days=10)).isoformat(), 1000000)
tax(O3, (T - timedelta(days=200)).isoformat(), 1000000)
with D.db_session() as c:   # O1 에 일부 입금 300,000
    c.execute("INSERT INTO receipts_payment (order_id, received_at, amount, method, currency) VALUES (?, ?, 300000, '이체', 'KRW')",
              (O1, T.isoformat()))

print("§1 메뉴 10줄")
h = q(cl.get, "/sales").text
want = ["/sales", "/projects/new", "/sales/opportunities", "/projects", "/sales/schedule",
        "/sales/shipments-receipts", "/sales/receipts-check", "/customers", "/export", "/sales/flow-guide"]
check("매출 등록 권한: 10줄 = 매출 홈 · 등록 · 수주 전 · 프로젝트 · 일정표 · 마감 · 입금 · 고객사 · 수출입 · 처음이면", menu(h) == want, menu(h))
for gone in ("/sales/quotations", "/sales/orders", "/sales/outstanding", "/sales/bank-recon"):
    check("메뉴에서 빠짐: %s (탭으로)" % gone, ('href="%s"' % gone) not in h[h.find('<aside class="sidebar"'):h.find('</aside>')])
check("메뉴 이름: 🎯 수주 전 — 영업 기회·견적 · 🧾 마감 — 계산서 발행 · 💰 입금 — 확인·미수",
      "🎯 수주 전 — 영업 기회·견적" in h and "🧾 마감 — 계산서 발행" in h and "💰 입금 — 확인·미수" in h)
S["user"] = VIEWER
hv = q(cl.get, "/sales").text
check("매출 등록 권한 없음: 💰 입금 안 보임(들어가도 경로가 막음)", "/sales/receipts-check" not in menu(hv), menu(hv))
S["user"] = SALES

print("§2 탭 화면 → 그 메뉴에 불")
for path, want_act in (("/sales/outstanding", "/sales/receipts-check"), ("/sales/receipts-check", "/sales/receipts-check"),
                       ("/sales/quotations", "/sales/opportunities"), ("/sales/orders", "/projects"),
                       ("/sales/opportunities/new", "/projects/new"), ("/sales/quotes/new", "/projects/new"),
                       ("/sales/shipments-receipts", "/sales/shipments-receipts")):
    r = q(cl.get, path)
    check("%s → 메뉴 %s 에 불" % (path, want_act), r.status_code == 200 and active(r.text) == want_act, (r.status_code, active(r.text)))
S["user"] = CEO
r = q(cl.get, "/sales/bank-recon")
check("/sales/bank-recon(대표) → 메뉴 💰 입금 에 불", r.status_code == 200 and active(r.text) == "/sales/receipts-check", (r.status_code, active(r.text)))
S["user"] = SALES

print("§3 💰 입금 탭 줄")
hr = main_part(q(cl.get, "/sales/receipts-check").text)
check("입금 확인: 탭 줄 [💰 입금 확인(지금) · 📊 미수 현황] · 일반 영업은 🏦 입금 대사 없음",
      'data-group="money"' in hr and '<span class="t on">💰 입금 확인</span>' in hr and 'href="/sales/outstanding">📊 미수 현황' in hr and "/sales/bank-recon" not in hr)
S["user"] = CEO
hc = main_part(q(cl.get, "/sales/outstanding").text)
check("대표: 미수 현황 탭 줄에 🏦 입금 대사 탭", 'href="/sales/bank-recon">🏦 입금 대사' in hc and '<span class="t on">📊 미수 현황</span>' in hc)
hb = main_part(q(cl.get, "/sales/bank-recon").text)
check("입금 대사 화면에도 같은 탭 줄(입금 대사 = 지금)", '<span class="t on">🏦 입금 대사</span>' in hb and 'href="/sales/receipts-check"' in hb)
S["user"] = SALES
r = q(cl.get, "/sales/aging", follow_redirects=False)
check("옛 채권 노화 주소 → 📊 미수 현황으로 넘김", r.status_code == 303 and r.headers.get("location") == "/sales/outstanding", (r.status_code, r.headers.get("location")))

print("§4 미수 현황 숫자 = 입금 확인과 같은 계산")
d = M._rc_rows_z94(SALES)
rc_sum = sum(x["rem"] for x in d["rows"] if x["ccy"] == "KRW")
custs, kpi = M._ar_by_cust_z98(d["rows"])
check("받을 돈 합 = 입금 확인 줄 합(부가세 포함) = 800,000 + 1,100,000 + 1,100,000 = 3,000,000",
      rc_sum == 3000000 and sum(g["total"] for g in custs) == rc_sum, (rc_sum, [g["total"] for g in custs]))
ga = next(g for g in custs if g["cid"] == CA)
gb = next(g for g in custs if g["cid"] == CB)
check("A: 31~60일 지남 800,000(1,100,000 − 받은 300,000) · 예정일 전 1,100,000 · 가장 오래 50일",
      ga["d60"] == 800000 and ga["nd"] == 1100000 and ga["max_over"] == 50, ga)
check("B: 결제 조건 기본 60일 → 140일 지남 → 90일 넘음 1,100,000", gb["d90p"] == 1100000 and gb["max_over"] == 140 and gb["term_default"], gb)
check("가장 오래 지난 고객사가 맨 위(B → A)", [g["cid"] for g in custs][:2] == [CB, CA])
ho = main_part(q(cl.get, "/sales/outstanding").text)
check("화면: 받을 돈 ₩3,000,000 · 지난 돈 ₩1,900,000 · 고객사 2곳 · 가장 오래 140일",
      "₩3,000,000" in ho and "₩1,900,000" in ho and "2곳" in ho and "140일" in ho, kpi)
check("화면: 구간 칸 머리(예정일 전 · 1~30 · 31~60 · 61~90 · 90일 넘음) · 「입금 확인과 같은 계산」 안내",
      all(t in ho for t in ("예정일 전", "1~30일 지남", "31~60일", "61~90일", "90일 넘음", "입금 확인과 같은 계산")))
check("옛 「출하 수주·부가세 뺀」 미수 띠 없음", "ar-after-z94" not in ho and "ar-baseline-z92" not in ho)

print("§5 🧾 마감")
hs = main_part(q(cl.get, "/sales/shipments-receipts").text)
check("제목 「🧾 마감 — 계산서 발행」", "🧾 마감 — <em>계산서 발행</em>" in hs)
check("「＋ 수금 입력」 칸 없음(입금 기록은 💰 입금 한 곳)", '<form class="sr-recv-form"' not in hs and 'action="/sales/receipts"' not in hs)
check("입금 숫자 대신 「💰 입금에서 →」 링크 · 미수 띠 없음", "💰 입금에서 →" in hs and "총 미수(부가세 포함" not in hs and "ar-after-z94" not in hs)
sec = hs[hs.find("🔴 발행 대기"):hs.find("✅ 발행 완료")]
check("위 「🔴 발행 대기」 = 계산서 안 끊은 O4 만(예정일 지난 O1·O3 은 아래 발행 완료)",
      ("/sales/orders/%d\"" % O4) in sec and ("/sales/orders/%d\"" % O1) not in sec and ("/sales/orders/%d\"" % O3) not in sec,
      [("/sales/orders/%d\"" % o) in sec for o in (O1, O3, O4)])
check("아래 「✅ 발행 완료」 + 「입금 기록은 💰 입금 → 입금 확인에서」", "✅ 발행 완료" in hs and "💰 입금 → 입금 확인</a>에서" in hs)
r = q(cl.post, "/sales/receipts", data={"order_id": str(O2), "amount": "1", "received_at": T.isoformat(), "method": "이체", "currency": "KRW"})
check("옛 수금 입력 주소는 그대로 살아 있음(화면 단추만 뺌 · 되돌림 쉬움)", r.status_code in (200, 303), r.status_code)

print("§6 🎯 수주 전")
hp = main_part(q(cl.get, "/sales/opportunities").text)
check("영업 기회: 탭 줄 [🎯 영업 기회(지금) · 📋 견적서] · 「+ 새 영업 기회」 단추 없음",
      '<span class="t on">🎯 영업 기회</span>' in hp and 'href="/sales/quotations">📋 견적서' in hp and 'href="/sales/opportunities/new"' not in hp)
hq = main_part(q(cl.get, "/sales/quotations").text)
check("견적서: 같은 탭 줄(견적서 = 지금) · 「＋ 새 견적」·「＋ 첫 견적」 단추 없음",
      '<span class="t on">📋 견적서</span>' in hq and 'href="/sales/quotes/new"' not in hq)
hn = q(cl.get, "/projects/new").text
cards = [c.split("?")[0] for c in re.findall(r'<a class="pc-card[^"]*" href="([^"]+)"', hn)]
check("🆕 등록 카드 8개: … 소모품 · 🤝 고객사 · 🎯 영업 기회 · 📋 견적서",
      cards == ["/projects/quick", "/projects/quick", "/projects/quick", "/projects/new", "/consumables/new", "/customers/new",
                "/sales/opportunities/new", "/sales/quotes/new"], cards)
S["user"] = VIEWER
cards_v = [c.split("?")[0] for c in re.findall(r'<a class="pc-card[^"]*" href="([^"]+)"', q(cl.get, "/projects/new").text)]
check("매출 등록 권한 없는 분: 🎯 · 📋 카드 안 보임(경로가 막는 것과 같게)", "/sales/quotes/new" not in cards_v and "/sales/opportunities/new" not in cards_v, cards_v)
S["user"] = SALES

print("§7 📋 프로젝트 탭 줄에 📑 수주 목록")
for path in ("/projects", "/projects/ledger", "/prod-requests"):
    m = main_part(q(cl.get, path).text)
    check("%s: 탭 줄에 📑 수주 목록" % path, 'href="/sales/orders"' in m and "📑 수주 목록" in m)
hoo = main_part(q(cl.get, "/sales/orders").text)
check("수주 목록 화면: 프로젝트 탭 줄(수주 목록 = 지금) · 길 표시 「프로젝트 · 수주 목록」",
      'data-dn="proj-tabs-z98"' in hoo and 'href="/prod-requests"' in hoo and "<b>수주 목록</b>" in hoo)

_now = M._fmt_money(sum(x["rem"] for x in M._rc_rows_z94(SALES)["rows"] if x["ccy"] == "KRW"), "KRW")   # §5 에서 옛 주소로 1원 넣음 → ₩2,999,999
check("수주 목록 위 칸 「💰 받을 돈」 = 입금 확인과 같은 원화 합 %s(옛 「확정+납품+송장 합」 아님)" % _now,
      _now == "₩2,999,999" and "💰 받을 돈" in hoo and _now in hoo[hoo.find('data-dn="kpi-outstanding"'):hoo.find('data-dn="kpi-outstanding"') + 900]
      and "확정+납품+송장 합" not in hoo)
check("마감 화면 탭 제목 「마감 · KNK」", "<title>마감 · KNK</title>" in q(cl.get, "/sales/shipments-receipts").text)

print("§8 안내")
g = q(cl.get, "/sales/flow-guide").text
check("안내: 「🧾 마감」 발행 대기 · 「💰 입금 → 💰 입금 확인 탭」 · 「📊 미수 현황 탭」",
      "🧾 마감</span> → <b>🔴 발행 대기</b>" in g and "💰 입금</span> → <span class=\"fg-path\">💰 입금 확인</span> 탭" in g and "📊 미수 현황</span> 탭" in g)

print("\n결과: OK %d · FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
