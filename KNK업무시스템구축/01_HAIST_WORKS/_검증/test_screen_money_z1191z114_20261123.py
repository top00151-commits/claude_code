# -*- coding: utf-8 -*-
"""z1191z114 시험 — 대표 11-23 「숫자가 칸에 잘려서 나와 … 전체 점검 · 매출 금액에 오류는 절대 있으면 안돼」
  §1 빈 값(None)이 화면에 「None」 글자로 안 나옴 — default 필터가 None 도 빈 값으로(0·빈 글자는 그대로 · boolean=True 는 원래대로)
       · 수주 목록 납품처 · 고객사 수정 화면 담당자 칸(그대로 저장하면 「None」 글자가 자료에 들어가던 길)
  §2 공용 잘림 막기 조각(knk_fit_num) — chrome 에 한 번 · 큰 숫자 칸 맞춤 · 머리 고정 표 가로 넘김 · 위쪽 띠 안 눌림 · 출하·입금 표 D+일수 아랫줄
  §3 수주 상세 발행·미수금 = 호기 세금계산서 기준 · 미수금 = 💰 입금 확인과 같은 함수의 그 수주 몫(부가세 포함) · 입금 완료 = 0
  §4 대표 대시 「이번달 수주매출」 = 매출 홈 수주매출(월간)과 같은 값(통화 섞어 그냥 더하지 않음 · 소모품 포함)
"""
import contextlib
import io
import os
import re
import sys
import tempfile
from datetime import date

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z114-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z114_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
TODAY = date.today()
YM = TODAY.strftime("%Y-%m")
PY, PM = (TODAY.year, TODAY.month - 1) if TODAY.month > 1 else (TODAY.year - 1, 12)
PYM = "%04d-%02d" % (PY, PM)
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, "
                 "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상대표', 'ceo', 'Z114', 'Z114', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    CEO = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z114'").fetchone())
    conn.execute("INSERT INTO customers (name, alias) VALUES ('가상고객(주)', '가상고객')")
    CID = conn.execute("SELECT id FROM customers WHERE name='가상고객(주)'").fetchone()[0]
    conn.execute("INSERT OR REPLACE INTO exchange_rates (rate_date, from_currency, to_currency, rate, source) VALUES (?, 'USD', 'KRW', 1400, '월기준')", (YM + "-01",))
    conn.execute("INSERT OR REPLACE INTO exchange_rates (rate_date, from_currency, to_currency, rate, source) VALUES (?, 'USD', 'KRW', 1300, '월기준')", (PYM + "-01",))
    conn.execute("INSERT INTO projects (code, name, mgmt_code, customer_id, customer_name, currency, order_date) VALUES ('P114', '가상 프로젝트', '001T9901', ?, '가상고객', 'KRW', ?)", (CID, YM + "-02"))
    PID = conn.execute("SELECT id FROM projects WHERE mgmt_code='001T9901'").fetchone()[0]

    def so(no, ccy, amt, d, status="CONFIRMED", ship_to=None):
        conn.execute("INSERT INTO orders (order_no, customer_id, project_id, order_date, total_amount, status, currency, ship_to) VALUES (?,?,?,?,?,?,?,?)",
                     (no, CID, PID, d, amt, status, ccy, ship_to))
        oid = conn.execute("SELECT id FROM orders WHERE order_no=?", (no,)).fetchone()[0]
        return oid
    O1 = so("T-Z114-1", "KRW", 1000000, YM + "-05")                 # 이번 달 원화 100만
    O2 = so("T-Z114-2", "USD", 1000, YM + "-06")                     # 이번 달 달러 1,000 → 140만
    O3 = so("T-Z114-3", "KRW", 500000, PYM + "-10")                 # 지난달 원화 50만
    O4 = so("T-Z114-4", "KRW", 2000000, YM + "-07", status="PAID")   # 입금 완료
    for oid, amt, ccy in ((O1, 1000000, "KRW"), (O2, 1000, "USD"), (O3, 500000, "KRW"), (O4, 2000000, "KRW")):
        conn.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label, currency) VALUES (?,1,?,?, '1호기', ?)", (oid, amt, amt, ccy))
    # O1: 1차 60만 + 2차 40만 발행 · 입금 33만 → 미수 = (60만+6만) + (40만+4만) − 33만 = 77만
    conn.execute("UPDATE order_items SET tax_invoice_date=?, tax_invoice_amt1=600000, tax_invoice_date2=?, tax_invoice_amt2=400000 WHERE order_id=?",
                 (YM + "-10", YM + "-15", O1))
    conn.execute("INSERT INTO receipts_payment (order_id, received_at, amount, currency) VALUES (?, ?, 330000, 'KRW')", (O1, YM + "-12"))
    # O4: 입금 완료(PAID) — 발행 200만, 입금 기록 없어도 미수 0
    conn.execute("UPDATE order_items SET tax_invoice_date=?, tax_invoice_amt1=2000000 WHERE order_id=?", (YM + "-08", O4))
    # 소모품 이번 달 30만
    conn.execute("INSERT INTO consumable_orders (co_no, customer_id, customer_name, order_date, currency, total_amount, status) VALUES ('C-Z114-1', ?, '가상고객', ?, 'KRW', 300000, 'CONFIRMED')", (CID, YM + "-09"))
    # 담당자 — 전화 빈칸(NULL)
    conn.execute("INSERT INTO customer_contacts (customer_id, role, name, phone) VALUES (?, '기타', '홍가상', NULL)", (CID,))

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M.get_user = lambda request: CEO
cl = TestClient(M.app)
OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ✅", label)
    else:
        FAIL += 1
        print("  ❌", label, "" if got is None else ("→ %r" % (got,))[:400])


def txt(h):
    h = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ", h)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))


print("§1 None 글자")
env = M.tpl.env
check("default: None → 대신할 글", env.from_string("{{ x|default('—') }}").render(x=None) == "—")
check("default: 정의 안 됨 → 대신할 글", env.from_string("{{ y|default('—') }}").render() == "—")
check("default: 0 은 그대로(0)", env.from_string("{{ x|default('—') }}").render(x=0) == "0")
check("default: 빈 글자는 그대로", env.from_string("[{{ x|default('—') }}]").render(x="") == "[]")
check("default(…, true): 빈 글자도 바꿈(원래 동작)", env.from_string("{{ x|default('—', true) }}").render(x="") == "—")
check("d 줄임 이름도 같게", env.from_string("{{ x|d('—') }}").render(x=None) == "—")
h = cl.get("/sales/orders").text
check("수주 목록 납품처 빈칸 → 「—」(None 글자 없음)", ">None<" not in h and "T-Z114-1" in h, re.findall(r".{60}>None<.{20}", h)[:2])
h = cl.get("/customers/%d/edit" % CID).text
m = re.search(r'name="contact_phone_1" value="([^"]*)"', h)
check("고객사 수정 화면 담당자 전화 빈칸 = 빈 값(「None」 아님 — 그대로 저장해도 「None」 글자 안 들어감)", m is not None and m.group(1) == "", m.group(1) if m else h[:200])

print("§2 공용 잘림 막기 조각")
P = os.path.join(ROOT, "app", "templates", "_v5_partials", "knk_fit_num.html")
src = io.open(P, encoding="utf-8").read()
chrome = io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "chrome.html"), encoding="utf-8").read()
check("chrome 에 한 번만 들어감", chrome.count('{% include "_v5_partials/knk_fit_num.html" %}') == 1)
check("큰 숫자 칸 = 한 줄 · 줄이기 대상(.kpi-num · 출하·입금 칸)", ".kpi-num, .knk-fit, [data-knk-fit]" in src and ".tbl[data-sr-table] .sr-v:not(.wrap)" in src and "base * 0.55" in src)
check("머리 고정 표 = 가로 넘김", ".tbl-wrap.tbl-sticky { overflow-x: auto; }" in src)
check("위쪽 띠 안 눌림(대표 대시·내 정보·주간 보고)", ".main > .dash-hero, .main > .profile-hero, .main > .victor-insight { flex-shrink: 0; }" in src)
check("중복 실행 막기", "window.__knkFitNum" in src)
h = cl.get("/sales").text
check("매출 홈에 조각이 실제로 실림", "window.__knkFitNum" in h and 'class="kpi-num"' in h)
sr = io.open(os.path.join(ROOT, "app", "templates", "sales_shipments_receipts.html"), encoding="utf-8").read()
check("출하·입금 표 D+일수·📋 단추 = 아랫줄", ".sr-v .sr-dday{display:block;}" in sr and ".sr-v .sr-hist-btn{display:block;margin-left:auto;}" in sr)

print("§3 수주 상세 발행·미수금")
def kpis(oid):
    h = cl.get("/sales/orders/%d" % oid).text
    return [txt(x).strip() for x in re.findall(r'class="kpi-num"[^>]*>(.*?)</div>', h, re.S)[:4]], h
v, h = kpis(O1)
check("수주 금액 ₩1,000,000", v[0] == "₩1,000,000", v)
check("세금계산서 발행(공급가) = 호기 1·2차 합 ₩1,000,000", v[1] == "₩1,000,000", v)
check("수금 누계 ₩330,000", v[2] == "₩330,000", v)
check("미수금(부가세 포함) = ₩770,000", v[3] == "₩770,000", v)
rc = sum(x["rem"] for x in M._rc_rows_z94(CEO)["rows"] if x["oid"] == O1)
check("미수금 = 💰 입금 확인 같은 함수 값", rc == 770000, rc)
check("부가세 포함 발행 ₩1,100,000 작은 글", "부가세 포함 ₩1,100,000" in txt(h))
check("세금계산서 목록 2장(1차·2차) · 옛 「발행된 송장이 없습니다」 없음", "🧾 세금계산서 (2장)" in txt(h) and "1차" in txt(h) and "2차" in txt(h) and "발행된 송장이 없습니다" not in h)
v, h = kpis(O4)
check("입금 완료(PAID) 수주 미수금 = ₩0 · 발행은 ₩2,000,000", v[3] == "₩0" and v[1] == "₩2,000,000", v)
v, h = kpis(O3)
check("발행 없는 수주 = 발행 ₩0 · 미수 ₩0 · 안내 글", v[1] == "₩0" and v[3] == "₩0" and "아직 세금계산서를 발행하지 않았습니다" in h, v)

print("§4 대표 대시 이번달 수주매출")
with D.db_session() as c:
    r = M._fx_load_rates(c)
    want = M._sales_3way(c, r, {}, "month", str(TODAY.year), "1", str(TODAY.month))["kpi"]["order"]
    prev = M._sales_3way(c, r, {}, "month", str(PY), "1", str(PM))["kpi"]["order"]
check("매출 홈 계산: 이번 달 = 100만 + $1,000×1,400 + 200만(입금 완료 포함) + 소모품 30만 = 470만", round(want) == 4700000, want)
h = txt(cl.get("/dashboard").text)
m = re.search(r"이번달 매출 ([\d,\.]+)(억|만)?원 전월비 ([+-][\d\.]+)%", h)
check("대표 대시 = 「이번달 매출 470만원」(옛: 통화 섞어 더해 300만 1,000원)", m is not None and m.group(1) == "470" and m.group(2) == "만", m.group(0) if m else h[h.find("경영 KPI"):h.find("경영 KPI") + 160])
g = round((want - prev) * 100 / prev, 1)
check("전월비 = 같은 계산의 지난달(50만) 대비 %+.1f%%" % g, m is not None and abs(float(m.group(3)) - g) < 0.05, m.group(3) if m else None)
check("설명 글 「수주매출 = 매출 홈과 같은 계산」", "수주매출 = 매출 홈과 같은 계산(발주일 · 외화는 그 달 환율)" in h)
check("카드 이름은 「이번달 매출」 그대로(매출 권한 거르기 _need1191g 가 이 이름을 본다)", '"이번달 매출": _sv1191g' in io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read() and "이번달 수주매출" not in h)

print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
