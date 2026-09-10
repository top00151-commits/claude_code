#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""발주 목록 합계 = 통화별로 (세션01 전달 건 · 대표 지시 2026-09-10 "셋 - 진행해")

무엇을 막나
  발주 목록의 「총 발주액·평균 발주액·표 아래 합계」가 **통화를 안 보고 그냥 더했다.**
  지금은 발주가 원화 1건뿐이라 숫자가 안 틀리지만,
  **외화 발주가 처음 들어오는 순간 조용히 틀리기 시작한다.**

⚠ 매출 쪽이 딱 그렇게 당했다 — 통화 섞인 25건·오차 41억.
  그중 **24건은 실제보다 작게** 나와 아무도 신고하지 않았다(부풀려진 1건만 신고됨).
  작게 나오는 오류는 스스로 드러나지 않는다. 그래서 시험으로 못박는다.

⛔ 운영 DB 를 열지 않는다. 실명·거래처·실단가 없음(가상 자료).
"""
import os
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

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_poccy_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
D.init_db()

import app.main as appmain                                 # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

CUR = {"u": None}
appmain.get_user = lambda request: CUR["u"]
cl = TestClient(appmain.app, follow_redirects=False)

BUYER = {"id": 903, "name": "시험구매", "role": "member", "team_id": 10,
         "can_use_logistics": 1, "can_view_logistics": 1}

with D.db_session() as conn:
    conn.execute("INSERT INTO users(id, name, login_id, password, role) VALUES(?,?,?,'x',?)",
                 (BUYER["id"], BUYER["name"], "P903", BUYER["role"]))
    conn.execute("DELETE FROM field_access_policy")
    for cat in ("purchase_price", "supplier_info"):
        conn.execute("INSERT INTO field_access_policy(category, team_id) VALUES(?,10)", (cat,))
    # 월 기준환율 — 그 달 1일 행만 읽는다(z1072)
    conn.execute("DELETE FROM exchange_rates")
    conn.execute("INSERT INTO exchange_rates(rate_date, from_currency, to_currency, rate) "
                 "VALUES('2026-06-01','USD','KRW',1300)")

FAIL, CNT = [], 0


def check(name, ok, detail=""):
    global CNT
    CNT += 1
    print(("  ✅" if ok else "  ❌") + f" {CNT:02d} {name}" + ("" if ok else f" — {detail}"))
    if not ok:
        FAIL.append(name)


def clear_po():
    with D.db_session() as c:
        c.execute("DELETE FROM purchase_orders")


def add_po(no, amount, ccy="KRW", d="2026-06-10"):
    with D.db_session() as c:
        c.execute("INSERT INTO purchase_orders(po_number, order_date, expected_date, "
                  "currency, total_amount, status) VALUES(?,?,?,?,?, '발주완료')",
                  (no, d, d, ccy, amount))


def page():
    CUR["u"] = BUYER
    r = cl.get("/po")
    assert r.status_code == 200, r.status_code
    return r.text


print("=" * 72)
print("  발주 목록 합계 = 통화별로")
print("=" * 72)

# ── ① 원화만 — 예전 모습 그대로여야 한다 (잘 되는건 안 건드린다) ──
clear_po()
add_po("PO-1", 12000000)
add_po("PO-2", 8000000)
t = page()
check("① 원화만: 합계가 예전처럼 「만/억」 으로 보인다", "2,000<span class=\"knk-kpi__unit\">만" in t
      or "2,000만" in t, t.count("knk-kpi__unit"))
check("① 원화만: 통화별로 쪼개 보이지 않는다(예전 모습 유지)",
      "knk-ccy-mix" not in t)

# ── ② 통화가 섞이면 — 절대 한 숫자로 더하지 않는다 ──
clear_po()
add_po("PO-1", 1720000, "KRW")
add_po("PO-2", 83882.73, "USD")
t = page()
naive = "{:,.0f}".format(1720000 + 83882.73)          # 1,803,883 — 이게 보이면 사고
check("② 섞임: **환산 없는 단순합이 화면에 없다**", naive not in t, naive)
check("② 섞임: 통화별로 나눠 보인다", "knk-ccy-mix" in t)
check("② 섞임: 원화 환산 합계를 함께 보여준다", "knk-ccy-krw" in t and "월 기준환율" in t)
_krw = 1720000 + 83882.73 * 1300
check("② 섞임: 환산값이 월 기준환율(1,300)로 맞다",
      "{:,.0f}".format(_krw)[:6] in t, "{:,.0f}".format(_krw))

# ── ③ 외화 하나뿐 — 원화 단위(억/만)를 붙이면 안 된다 ──
clear_po()
add_po("PO-1", 50000, "USD")
t = page()
check("③ 달러만: 「만/억」 같은 원화 단위를 안 붙인다",
      "knk-kpi__unit\">만" not in t and "knk-kpi__unit\">억" not in t)
check("③ 달러만: 달러로 표기된다", "$" in t or "USD" in t)

# ── ④ 환율이 없는 통화 — 반쪽 숫자를 내지 않는다 ──
clear_po()
add_po("PO-1", 1000000, "KRW")
add_po("PO-2", 500, "VND")
t = page()
check("④ 환율 없음: 원화 합계를 억지로 내지 않고 **못 낸다고 알린다**",
      "knk-ccy-nofx" in t and "기준환율 미등록" in t)
check("④ 환율 없음: 그래도 통화별 합계는 보여준다", "knk-ccy-mix" in t)

# ── ⑤ 평균도 같은 규칙 ──
clear_po()
add_po("PO-1", 1000000, "KRW")
add_po("PO-2", 1000, "USD")
t = page()
check("⑤ 평균: 섞였을 때 단순평균을 내지 않는다",
      "{:,.0f}".format((1000000 + 1000) / 2) not in t)

clear_po()
add_po("PO-1", 1000000, "KRW")
add_po("PO-2", 500, "VND")     # 환율 없음 → 원화 못 냄 → 평균도 안 냄
t = page()
check("⑤ 평균: 원화를 못 내면 평균도 내지 않는다(반쪽 숫자 금지)",
      t.count("knk-ccy-nofx") >= 1)

# ── ⑥ 발주가 하나도 없어도 죽지 않는다 ──
clear_po()
t = page()
check("⑥ 발주 0건: 화면이 정상으로 뜬다", "총 발주액" in t or "필터 합계" in t)

# ── ⑦ 역검사 — 시험이 헛돌지 않는지 ──
#     통화 칸을 전부 KRW 로 바꾸면 ②의 단순합이 **정당하게** 나와야 한다.
clear_po()
add_po("PO-1", 1720000, "KRW")
add_po("PO-2", 83883, "KRW")
t = page()
check("⑦ 역검사: 전부 원화면 합쳐진 값이 정상으로 나온다",
      "180" in t and "knk-ccy-mix" not in t)

# ── ⑧ 권한 없는 사람에게는 금액 자체가 안 보인다 (기존 규칙 보존) ──
clear_po()
add_po("PO-1", 1720000, "KRW")
add_po("PO-2", 83882.73, "USD")
NOPRICE = {"id": 904, "name": "시험조회", "role": "member", "team_id": 9,
           "can_use_logistics": 0, "can_view_logistics": 1}
with D.db_session() as c:
    c.execute("INSERT OR IGNORE INTO users(id, name, login_id, password, role) "
              "VALUES(?,?,?,'x',?)", (904, "시험조회", "P904", "member"))
CUR["u"] = NOPRICE
t = cl.get("/po").text
check("⑧ 단가 열람권한 없으면 금액 대신 자물쇠 (기존 규칙 그대로)",
      "🔒" in t and "knk-ccy-mix" not in t)

print("-" * 72)
print(f"  시험 {CNT}건 · 실패 {len(FAIL)}건" + ("" if not FAIL else " → " + ", ".join(FAIL)))
sys.exit(1 if FAIL else 0)
