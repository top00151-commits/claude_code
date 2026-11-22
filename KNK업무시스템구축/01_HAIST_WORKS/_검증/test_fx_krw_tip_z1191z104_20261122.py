# -*- coding: utf-8 -*-
"""z1191z104 시험 — 외화 금액 = 원래 통화로 크게 + 「≈ ₩」 작게 · 「≈ ₩」에 마우스 → 몇 월 기준환율·얼마
(대표 11-22 「응 그렇게 바꾸고 다른 화면도 같이 맞춰줘 · 원화에 마우스 포인트 올리면 적용 환율이 언제 기준환율이고
 얼마로 적용됐는지도 보이게 · 다른 데로 이동하면 사라지고」)
  §1 공용 풍선 글(_ccy_breakdown(...)["tip"]) — 한 건 · 여러 달 · 그달 환율 없음(대체) · 작은 통화 단위 · 환율 아예 없음
  §2 매출 홈 「최근 프로젝트」 — $30,053.68 크게 + ≈ ₩4,470만 · 「(USD)」 꼬리 없음 · 원화 건은 ₩ 한 줄
  §3 프로젝트 상세 — 「≈ ₩」 = 월 기준환율(매출 홈과 같은 숫자) · 프로젝트에 적은 환율 글 없음 · 통화 섞인 수주
  §4 매출 보고서 상세 줄 — 외화 금액 앞 기호 · 원화 칸 풍선
  §5 고객사 상세 「총 수주액」 — 외화 한 통화도 ≈ ₩ + 풍선
  §6 풍선 장치는 모든 화면 틀에 한 번
"""
import contextlib
import html as _html
import io
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z104-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z104_")
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
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, "
                 "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상대표', 'ceo', 'Z104', 'Z104', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 0, 0)")
    CEO = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z104'").fetchone())
    conn.execute("INSERT OR IGNORE INTO field_access_policy (category, team_id) VALUES ('sales_amount', 1)")
    for ccy, d, r in [("USD", "2026-04-01", 1486.64), ("USD", "2026-05-01", 1487.39), ("VND", "2026-05-01", 0.0541)]:
        conn.execute("INSERT INTO exchange_rates (from_currency, to_currency, rate, rate_date) VALUES (?, 'KRW', ?, ?)", (ccy, r, d))
    conn.execute("INSERT INTO customers (name) VALUES ('가상수출고객')")
    CU = conn.execute("SELECT id FROM customers WHERE name='가상수출고객'").fetchone()[0]

    def proj(code, name, ccy, amt, od, dd):
        conn.execute("INSERT INTO projects (mgmt_code, name, customer_id, customer_name, currency, order_amount, "
                     "order_date, due_date, stage) VALUES (?, ?, ?, '가상수출고객', ?, ?, ?, ?, '수주확정')",
                     (code, name, CU, ccy, amt, od, dd))
        return conn.execute("SELECT id FROM projects WHERE mgmt_code=?", (code,)).fetchone()[0]

    def so(pid, no, ccy, amt, od, dd):
        conn.execute("INSERT INTO orders (project_id, order_no, customer_id, currency, total_amount, order_date, due_date, status) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, 'CONFIRMED')", (pid, no, CU, ccy, amt, od, dd))
        oid = conn.execute("SELECT id FROM orders WHERE order_no=?", (no,)).fetchone()[0]
        conn.execute("INSERT INTO order_items (order_id, amount, unit_label) VALUES (?, ?, '1호기')", (oid, amt))

    P_USD = proj("901M2604", "가상 달러 장비", "USD", 30053.68, "2026-04-08", "2026-05-15")
    so(P_USD, "Z-260408-1", "USD", 30053.68, "2026-04-08", "2026-05-15")
    P_KRW = proj("902E2611", "가상 원화 장비", "KRW", 13500000, "2026-11-01", "2026-11-30")
    P_MIX = proj("903M2604", "가상 섞인 장비", "KRW", 1000000, "2026-04-01", "2026-04-20")
    so(P_MIX, "Z-260401-1", "KRW", 1000000, "2026-04-01", "2026-04-20")
    so(P_MIX, "Z-260401-2", "USD", 1000, "2026-04-01", "2026-04-20")
    P_EUR = proj("904M2605", "가상 유로 장비", "EUR", 500, "2026-05-01", "2026-05-20")
    conn.execute("INSERT INTO customers (name) VALUES ('가상유로고객')")
    conn.execute("UPDATE projects SET customer_id=(SELECT id FROM customers WHERE name='가상유로고객'), "
                 "customer_name='가상유로고객' WHERE id=?", (P_EUR,))

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


def tips(h):
    return [_html.unescape(t) for t in re.findall(r'data-fx-tip="([^"]*)"', h)]


rates = M._fx_rates_now()
print("§1 공용 풍선 글")
bd = M._ccy_breakdown([{"a": 30053.68, "c": "USD", "d": "2026-05-15"}], "a", "c", date_keys=("d",), rates=rates)
t = bd["tip"]
check("한 건: 「2026년 5월 기준환율 적용」", "2026년 5월 기준환율 적용" in t, t)
check("한 건: 「1 USD = ₩1,487.39」", "1 USD = ₩1,487.39" in t, t)
check("한 건: 계산식 「$30,053.68 × 1,487.39 = ₩44,701,543」", "$30,053.68 × 1,487.39 = ₩44,701,543" in t, t)
check("한 건: 원화 합계 = 44,701,543", round(bd["krw"]) == 44701543, bd["krw"])
bd = M._ccy_breakdown([{"a": 100, "c": "USD", "d": "2026-07-03"}], "a", "c", date_keys=("d",), rates=rates)
check("그달(7월) 환율 없음 → 「2026년 7월 기준환율이 아직 없어 2026년 5월 환율로 계산」",
      "2026년 7월 기준환율이 아직 없어 2026년 5월 환율로 계산" in bd["tip"], bd["tip"])
bd = M._ccy_breakdown([{"a": 100, "c": "USD", "d": "2026-04-10"}, {"a": 200, "c": "USD", "d": "2026-05-10"},
                       {"a": 300, "c": "USD", "d": "2026-05-11"}], "a", "c", date_keys=("d",), rates=rates)
check("여러 달: 달마다 한 줄(4월 1건 · 5월 2건)",
      "2026년 4월 · 1 USD = ₩1,486.64 · 1건 $100.00" in bd["tip"] and "2026년 5월 · 1 USD = ₩1,487.39 · 2건 $500.00" in bd["tip"], bd["tip"])
bd = M._ccy_breakdown([{"a": 1000000, "c": "VND", "d": "2026-05-10"}], "a", "c", date_keys=("d",), rates=rates)
check("작은 통화: 「100 VND = ₩5.41」", "100 VND = ₩5.41" in bd["tip"], bd["tip"])
bd = M._ccy_breakdown([{"a": 5, "c": "EUR", "d": "2026-05-10"}], "a", "c", date_keys=("d",), rates=rates)
check("환율 아예 없음: krw None · 「기준환율이 없어 원화로 바꾸지 못했습니다」",
      bd["krw"] is None and "기준환율이 없어 원화로 바꾸지 못했습니다" in bd["tip"], bd["tip"])
bd = M._ccy_breakdown([{"a": 5, "c": "KRW"}], "a", "c", rates=rates)
check("원화뿐: 풍선 글 없음", bd["tip"] == "", bd["tip"])
check("기준 날짜 이름: 「납기 달 기준(없으면 발주 달)」",
      M._fx_basis_txt_z104(("due_date", "order_date")) == "납기 달 기준(없으면 발주 달)", M._fx_basis_txt_z104(("due_date", "order_date")))

print("§2 매출 홈 「최근 프로젝트」")
r = cl.get("/sales")
h = r.text
check("화면 열림 200", r.status_code == 200, r.status_code)
m = re.search(r'data-dn="recent-projects".*?</div>\s*</div>\s*</div>', h, re.S)
rp = m.group(0) if m else ""
check("달러 프로젝트: 원래 통화 「$30,053.68」 크게", '<span class="knk-fx-orig">$30,053.68</span>' in rp, rp[:600])
# z1191z115 (대표 11-23 「발주달로 통일」): 환율 = 발주 달(4월 1,486.64) — 예전 납기 달(5월 1,487.39 → ≈ ₩4,470만)
check("달러 프로젝트: 작게 「≈ ₩4,468만」(발주 달 4월 환율)", "≈ ₩4,468만" in rp, rp[:600])
check("「₩… (USD)」 꼬리 없음", "(USD)" not in rp, rp[:600])
tt = tips(rp)
check("풍선: 2026년 4월(발주 달) 기준환율 · 1 USD = ₩1,486.64 · 계산식",
      any("2026년 4월 기준환율 적용" in x and "1 USD = ₩1,486.64" in x and "= ₩44,679,003" in x for x in tt), tt)
check("풍선: 발주 달 기준이라고 밝힘(z1191z115)", any("발주 달 기준" in x for x in tt), tt)
check("원화 프로젝트: ₩13,500,000 한 줄(≈ 없음)", "₩13,500,000" in rp and rp.count(">≈ ") == 2, rp.count(">≈ "))
check("유로(환율 없음): 「€500.00」 + 「⚠ 기준환율 없음」", "€500.00" in rp and "⚠ 기준환율 없음" in rp, rp[:900])
check("통화 섞인 프로젝트: ₩1,000,000 · $1,000.00 둘 다 + ≈ ₩2,486,640",
      "₩1,000,000" in rp and "$1,000.00" in rp and "≈ ₩249만" in rp, rp[:1200])

print("§3 프로젝트 상세")
h = cl.get("/project/%d" % P_USD).text
check("「≈ ₩44,679,003」(발주 달 월 기준환율 · 매출 홈과 같은 숫자 · z1191z115)", "≈ ₩44,679,003" in h, re.findall(r"≈[^<]{0,30}", h)[:5])
check("프로젝트에 적은 환율 글 「(환율 1 USD =」 없음", "(환율 1 USD =" not in h)
check("풍선 붙음(2026년 4월 · 1 USD = ₩1,486.64 · 발주 달)",
      any("2026년 4월" in x and "1 USD = ₩1,486.64" in x for x in tips(h)), tips(h)[:3])
h = cl.get("/project/%d" % P_MIX).text
check("통화 섞인 수주: 수주액 칸에도 ≈ ₩2,486,640 + 풍선(건마다 그 달)",
      h.count("≈ ₩2,486,640") >= 2 and any("건마다 그 달 기준환율로 바꾼 합계" in x and "원화 1건 ₩1,000,000 — 그대로 더함" in x
                                            and "합계 ≈ ₩2,486,640" in x for x in tips(h)),
      re.findall(r"≈[^<]{0,30}", h)[:6])
h = cl.get("/project/%d" % P_EUR).text
check("유로 상세: 틀린 원화(≈ ₩500 · 환율 안 곱한 값)를 만들지 않음", "≈ ₩500" not in h and "≈ ₩0" not in h)

print("§4 매출 보고서 상세 줄")
r = cl.get("/sales/report?basis=order&mode=year&year=2026")
h = r.text
check("화면 열림 200", r.status_code == 200, r.status_code)
check("외화 금액 앞 기호 「$30,053.68」(예전 30,053.68)", "<td class=\"n\">$30,053.68</td>" in h, re.findall(r"30,053\.68[^<]{0,5}", h)[:3])
tt = tips(h)
check("원화 칸 풍선: 「발주 달 기준」 · 2026년 4월 · 1 USD = ₩1,486.64",
      any("발주 달 기준" in x and "2026년 4월 기준환율 적용" in x and "1 USD = ₩1,486.64" in x for x in tt), tt[:3])

print("§5 고객사 상세 「총 수주액」")
h = cl.get("/customer/%d" % CU).text
check("통화 섞임 → 통화별 + ≈ ₩ 에 풍선(원화 건 그대로 · 합계)",
      'class="knk-fx-tipon"' in h and any("원화" in x and "합계 ≈" in x for x in tips(h)), tips(h)[:2])

print("§6 풍선 장치")
h = cl.get("/sales").text
check("모든 화면 틀에 풍선 장치(한 번)", h.count("__knkFxTipZ104") == 2 and "#knkFxTip" in h, h.count("__knkFxTipZ104"))

print("\n결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
