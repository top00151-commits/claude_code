# -*- coding: utf-8 -*-
"""z1191z115 시험 — 대표 11-23 「5. 발주달로 통일, 입금확인시에만 입금받은 달 환율로 계산필요, 환차익,환차손 확인 필요 · 6. 지워 · 7. 그렇게해」
  §1 외화 환율의 달 = 발주 달 — 매출 홈 수주·진행·최종매출 · 매출 보고서(줄·풍선) · 프로젝트 상세 「≈ ₩」
       (매출을 넣는 달은 그대로: 진행 = 출하일 · 최종 = 계산서 발행일)
  §2 입금 = 입금 받은 달 환율 → 환차익·환차손 — 입금 기록 창 미리 보기 · 기록 뒤 알림 · 💱 환차익·환차손 화면 · 수주 상세
       · 기초 정리(일괄) 줄은 따로(합계에 안 넣음) · 그 달 환율이 없으면 직전 달로 대신하고 그렇게 적음
  §3 프로젝트 목록 「예상 (+N%)」 없음 · 옛 매출 강화 대시(/sales/dashboard) → 📈 한눈에 보기
"""
import contextlib
import io
import json
import os
import re
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z115-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z115_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
Y = "2024"   # 지난 해로 고정(오늘 날짜와 상관없이)
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, "
                 "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상대표', 'ceo', 'Z115', 'Z115', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    CEO = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z115'").fetchone())
    conn.execute("INSERT INTO customers (name, alias) VALUES ('가상해외(주)', '가상해외')")
    CID = conn.execute("SELECT id FROM customers WHERE name='가상해외(주)'").fetchone()[0]
    for ym, r in (("2024-03", 1300), ("2024-05", 1400), ("2024-07", 1500)):
        conn.execute("INSERT OR REPLACE INTO exchange_rates (rate_date, from_currency, to_currency, rate, source) VALUES (?, 'USD', 'KRW', ?, '월기준')", (ym + "-01", r))
    conn.execute("INSERT INTO projects (code, name, mgmt_code, customer_id, customer_name, currency, order_date, due_date, order_amount, expected_amount) "
                 "VALUES ('P115', '가상 수출 장비', '001T2403', ?, '가상해외', 'USD', '2024-03-10', '2024-07-30', 1000, 100)", (CID,))
    PID = conn.execute("SELECT id FROM projects WHERE mgmt_code='001T2403'").fetchone()[0]

    def so(no, amt, d, due):
        conn.execute("INSERT INTO orders (order_no, customer_id, project_id, order_date, due_date, total_amount, status, currency) "
                     "VALUES (?,?,?,?,?,?, 'CONFIRMED', 'USD')", (no, CID, PID, d, due, amt))
        return conn.execute("SELECT id FROM orders WHERE order_no=?", (no,)).fetchone()[0]
    O1 = so("T-Z115-1", 1000, "2024-03-10", "2024-07-30")    # 발주 3월(1,300) · 출하 5월(1,400) · 계산서 7월(1,500)
    O2 = so("T-Z115-2", 200, "2024-03-12", "2024-07-30")     # 기초 정리(일괄) 입금 줄용
    conn.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label, currency, unit_status, status_date, tax_invoice_date, tax_invoice_amt1) "
                 "VALUES (?, 1, 1000, 1000, '1호기', 'USD', '출하', '2024-05-20', '2024-07-05', 1000)", (O1,))
    conn.execute("INSERT INTO order_items (order_id, qty, unit_price, amount, unit_label, currency, unit_status, status_date, tax_invoice_date, tax_invoice_amt1) "
                 "VALUES (?, 1, 200, 200, '1호기', 'USD', '출하', '2024-05-21', '2024-07-06', 200)", (O2,))
    conn.execute("INSERT INTO receipts_payment (order_id, received_at, amount, method, note, currency) "
                 "VALUES (?, '2024-07-25', 200, '기초정리(일괄)', '기초 정리(일괄) — 시험', 'USD')", (O2,))
    # 소모품 USD 100 · 발주 3월 · 출하 5월 · 계산서 7월
    conn.execute("INSERT INTO consumable_orders (co_no, customer_id, customer_name, order_date, currency, total_amount, status, status_date, tax_invoice_date, tax_invoice_amt1) "
                 "VALUES ('C-Z115-1', ?, '가상해외', '2024-03-02', 'USD', 100, 'SHIPPED', '2024-05-02', '2024-07-03', 100)", (CID,))

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


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


print("§1 환율의 달 = 발주 달")
oi_map, _pi = M._board_tax_oi_map()
with D.db_session() as c:
    rates = M._fx_load_rates(c)
    kp = M._sales_3way(c, rates, oi_map, "year", Y, "1", "1")["kpi"]
    km = {k: M._sales_3way(c, rates, oi_map, "month", Y, "1", m)["kpi"] for k, m in (("o", "3"), ("p", "5"), ("f", "7"))}
want = 1200 * 1300 + 100 * 1300   # 호기 1,000+200 · 소모품 100 — 모두 3월(발주) 환율 1,300
for nm, key in (("수주매출", "order"), ("진행매출", "prog"), ("최종매출", "final")):
    v = kp.get(key)
    v = v.get("total") if isinstance(v, dict) else v
    check("매출 홈 %s(%s년) = ₩%s (발주 달 3월 환율 1,300 · 예전: 진행 5월 1,400 · 최종 7월 1,500)" % (nm, Y, "{:,}".format(want)), v is not None and abs(float(v) - want) < 1, v)
for nm, k, key in (("수주매출 → 3월", "o", "order"), ("진행매출 → 5월(출하 달)", "p", "prog"), ("최종매출 → 7월(계산서 달)", "f", "final")):
    v = km[k].get(key)
    v = v.get("total") if isinstance(v, dict) else v
    check("매출을 넣는 달은 그대로: %s · 금액 ₩%s" % (nm, "{:,}".format(want)), v is not None and abs(float(v) - want) < 1, v)
with D.db_session() as c:
    lines = M._z17_lines(c, rates, oi_map, "tax")[0]
    ship = M._z17_lines(c, rates, oi_map, "ship")[0]
tl = [x for x in lines if str(x.get("date", ""))[:4] == Y]
check("매출 보고서(계산서 기준) 줄 원화 = 발주 달 환율 · 줄마다 환율 날짜(fxd) = 발주일",
      abs(sum(x["krw"] for x in tl) - want) < 1 and all(str(x.get("fxd", ""))[:7] == "2024-03" for x in tl), [(x.get("so"), x.get("krw"), x.get("fxd")) for x in tl])
sl = [x for x in ship if str(x.get("date", ""))[:4] == Y]
check("매출 보고서(출하 기준)도 발주 달 환율", abs(sum(x["krw"] for x in sl) - want) < 1, [(x.get("so"), x.get("krw")) for x in sl])
hr = q(cl.get, "/sales/report?basis=tax&mode=year&year=" + Y).text
tips = [t for t in re.findall(r'data-fx-tip="([^"]+)"', hr) if "기준환율" in t]
check("보고서 풍선 = 「2024년 3월」 기준환율 · 「발주 달 기준」", tips and all("2024년 3월" in t and "발주 달 기준" in t for t in tips), tips[:1])
hp = txt(q(cl.get, "/project/%d" % PID).text)
check("프로젝트 상세 「수주액 ≈ ₩」 = 수주 합 $1,200 × 3월 1,300 = ₩1,560,000(예전 납기 7월 → ₩1,800,000)",
      re.search(r"수주액[^≈]{0,300}≈ ₩1,560,000", hp) is not None, hp[hp.find("수주액"):hp.find("수주액") + 200])

print("§2 입금 = 입금 받은 달 환율 → 환차익·환차손")
pv = q(cl.get, "/sales/fx-gain/preview?oid=%d&date=2024-07-20&amount=1,000.00" % O1).json()
check("입금 창 미리 보기: $1,000 · 발주 3월 ₩1,300,000 · 입금 7월 ₩1,500,000 → 환차익 +₩200,000",
      pv.get("fx") and pv.get("diff") == 200000 and "환차익 +₩200,000" in pv.get("txt", "") and "2024년 3월" in pv["txt"] and "2024년 7월" in pv["txt"], pv)
pv2 = q(cl.get, "/sales/fx-gain/preview?oid=%d&date=2024-09-02&amount=1000" % O1).json()
check("입금 달(9월) 환율이 없으면 직전 7월로 대신 · 그렇게 적음", pv2.get("diff") == 200000 and "기준환율 없음 → 2024년 7월 환율로" in pv2.get("txt", ""), pv2)
r = q(cl.post, "/sales/receipts-check/record", json={"order_id": O1, "received_at": "2024-07-20", "amount": "1000", "note": "시험", "confirm": True})
j = r.json()
check("입금 기록 → 알림 글에 환차(환차익 +₩200,000)", r.status_code == 200 and j.get("ok") and "환차익 +₩200,000" in (j.get("fx_txt") or ""), j)
hg = txt(q(cl.get, "/sales/fx-gain?year=" + Y).text)
check("💱 화면: 실제 기록 1건 · 환차익 합계 +₩200,000 · 순 +₩200,000 · 기초 정리 줄은 기본에 없음",
      "외화 입금(실제 기록) 1건" in hg and "환차익 합계 +₩200,000" in hg and "순 환차(익 − 손) +₩200,000" in hg and "T-Z115-2" not in hg, hg[hg.find("외화 입금"):hg.find("외화 입금") + 300])
hb = txt(q(cl.get, "/sales/fx-gain?year=%s&base=1" % Y).text)
check("기초 정리(일괄) 보기: 그 줄도 보이고(T-Z115-2 · $200 × (1,500−1,300) = +₩40,000) 위 합계는 그대로 +₩200,000",
      "T-Z115-2" in hb and "+₩40,000" in hb and "환차익 합계 +₩200,000" in hb and "기초 정리(일괄) 1줄(참고만" in hb, hb[hb.find("외화 입금"):hb.find("외화 입금") + 500])
hd = q(cl.get, "/sales/orders/%d" % O1).text
check("수주 상세 수금 내역: 「💱 환차익 +₩200,000」 · 마우스 → 계산식", "💱 환차익 +₩200,000" in txt(hd) and "발주 달 2024년 3월" in hd, txt(hd)[txt(hd).find("수금 내역"):txt(hd).find("수금 내역") + 200])
hr2 = q(cl.get, "/sales/receipts-check").text
check("입금 확인 화면: 💱 탭 · 외화 미리 보기 칸(rcFx)", "/sales/fx-gain" in hr2 and 'id="rcFx"' in hr2 and "/sales/fx-gain/preview?" in hr2)
with D.db_session() as c:
    fk = M._fx_gain_calc_z115(M._fx_load_rates(c), "USD", 100, "2024-07-01", "2024-03-15")
check("환율이 내려가면 환차손(7월 1,500 발주 → 3월 1,300 입금 = −₩20,000)", fk and fk["diff"] == -20000 and fk["short"] == "환차손 −₩20,000", fk)
check("원화 입금은 환차 없음(None)", M._fx_gain_calc_z115({}, "KRW", 1000, "2024-03-01", "2024-07-01") is None)

print("§3 예상 줄 지움 · 옛 매출 대시")
hl = txt(q(cl.get, "/projects").text)
check("프로젝트 목록에 「예상 ₩… (+N%)」 없음(예상 $100 · 수주 $1,000)", "001T2403" in hl and not re.search(r"예상 [₩\$][\d,\.]+ \([+-]?\d+%\)", hl))
r = q(cl.get, "/sales/dashboard", follow_redirects=False)
check("옛 /sales/dashboard → /sales/glance", r.status_code == 303 and r.headers.get("location") == "/sales/glance", (r.status_code, r.headers.get("location")))
from app import menu_catalog as _mc                           # noqa: E402
check("메뉴 찾기 「매출 분석」 → /sales/glance", any(x[0] == "M-01-06" and x[3] == "/sales/glance" for x in _mc.MENU if isinstance(x, tuple)) if hasattr(_mc, "MENU") else "/sales/glance" in io.open(_mc.__file__, encoding="utf-8").read())

print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
