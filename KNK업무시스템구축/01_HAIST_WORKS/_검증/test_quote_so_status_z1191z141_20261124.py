# -*- coding: utf-8 -*-
"""z1191z141 (대표 11-24 「진행」): 수주마다 🟢 이 수주 견적 / 🔗 관리번호(앞 수주) 견적 사용 / ⚠ 금액 다름 / 없음 · 등록 화면 비슷한 지난 견적"""
import io, contextlib, json, os, sqlite3, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app import quote_link as Q
R = []


def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:300]))


def F(fid, up=None, amt=None, cur="KRW", qty=None, ack=None):
    return {"id": fid, "price": Q.q_price({"unit_price": up, "amount": amt, "currency": cur, "qty": qty}), "amt_ack_at": ack, "orig_name": "q%d.xlsx" % fid}


def O(oid, no, total, prices, cur="KRW"):
    return {"id": oid, "order_no": no, "price": Q.o_price(total, cur, prices)}


# 가격 읽기
check("견적 단가 없으면 합계 ÷ 수량", Q.q_price({"amount": "12,060,000", "qty": 6})[0] == 2010000)
check("수주 단가 = 품목 줄 단가가 모두 같을 때만", Q.o_price(4020000, "KRW", [2010000, 2010000])[0] == 2010000 and Q.o_price(5000, "KRW", [1000, 4000])[0] is None)
check("같음 = 원화 1원 · 외화 0.01 · 통화 다르면 다름", Q.same(100.4, "KRW", 100, "KRW") and not Q.same(100.02, "USD", 100, "USD") and Q.same(100, "USD", 100, "KRW") is False)
# 사진 같은 경우: 관리번호 견적서 6대 × 2,010,000 = 12,060,000 · 수주 4건(2대·2대·1대·1대)
orders = [O(1, "T-260826-1", 2010000, [2010000]), O(2, "T-260911-1", 2010000, [2010000]),
          O(3, "T-260930-9", 4020000, [2010000, 2010000]), O(4, "T-261016-4", 4020000, [2010000, 2010000])]
r = Q.resolve(orders, {}, F(10, up=2010000, amt=12060000, qty=6), {})
check("관리번호 견적서만 있고 단가 같음 → 모든 수주 🔗 관리번호 견적", all(r[i]["st"] == "link" and r[i]["via"] == "proj" and r[i]["f"]["id"] == 10 for i in (1, 2, 3, 4)), r)
# 이 수주 견적
r = Q.resolve(orders, {2: F(20, up=2010000, amt=2010000)}, None, {})
check("이 수주에 올린 견적 = 🟢", r[2]["st"] == "ok" and r[2]["via"] == "own")
check("뒤 수주(단가 같음) = 앞 수주 견적 🔗 · 그 앞 수주는 없음", r[3]["st"] == "link" and r[3]["via"] == "so" and r[3]["via_so"] == "T-260911-1" and r[1]["st"] == "none", r)
r = Q.resolve(orders, {2: F(20, up=1500000, amt=1500000)}, None, {})
check("이 수주 견적 금액 다름 = ⚠(z105 그대로) · 「확인했음」이면 🟢", r[2]["st"] == "diff" and
      Q.resolve(orders, {2: F(20, up=1500000, amt=1500000, ack="2026-11-24")}, None, {})[2]["st"] == "ok")
check("이 수주 견적: 단가만 같아도(합계 다름) 🟢", Q.resolve([O(5, "X", 4020000, [2010000, 2010000])], {5: F(30, up=2010000, amt=2010000, qty=1)}, None, {})[5]["st"] == "ok")
# 두 번째부터 금액이 달라질 때(대표 말씀 예)
o2 = [O(1, "A-1", 1000000, [1000000]), O(2, "A-2", 1200000, [1200000]), O(3, "A-3", 1200000, [1200000])]
r = Q.resolve(o2, {}, F(10, up=1000000, amt=1000000), {})
check("첫 수주 🔗 · 둘째(단가 다름) ⚠ · 셋째도 ⚠", r[1]["st"] == "link" and r[2]["st"] == "diff" and r[3]["st"] == "diff", r)
r = Q.resolve(o2, {2: F(20, up=1200000, amt=1200000)}, F(10, up=1000000, amt=1000000), {})
check("둘째에 새 견적 → 🟢 · 셋째(둘째와 단가 같음) = 둘째 견적 🔗(다시 안 올림)", r[2]["st"] == "ok" and r[3]["st"] == "link" and r[3]["via_so"] == "A-2" and r[3]["f"]["id"] == 20, r)
# 확인했음(따라가는 견적 금액 다름)
r = Q.resolve(o2, {}, F(10, up=1000000, amt=1000000), {2: 10})
check("둘째 「확인했음」(같은 견적서) → 🔗 · 확인함 표시 · 셋째는 그대로 ⚠", r[2]["st"] == "link" and r[2]["acked"] and r[3]["st"] == "diff", r)
r = Q.resolve(o2, {}, F(11, up=1000000, amt=1000000), {2: 10})
check("확인한 뒤 관리번호 견적서가 바뀌면 다시 ⚠", r[2]["st"] == "diff")
# 비교 못 함
r = Q.resolve(o2, {}, F(10), {})
check("관리번호 견적서 금액을 못 읽음 → 관리번호 견적 🔗(비교 못 함)", all(r[i]["st"] == "link" and r[i]["cmp"] is None for i in (1, 2, 3)))
r = Q.resolve([O(1, "B-1", None, [])], {}, F(10, up=5, amt=5), {})
check("수주 금액 없음 → 관리번호 견적 🔗", r[1]["st"] == "link")
check("견적서 하나도 없음 = 없음", Q.resolve(o2, {}, None, {})[1]["st"] == "none")
check("통화 다름 = ⚠", Q.resolve([O(1, "U-1", 100, [100], "USD")], {}, F(10, up=100, amt=100, cur="KRW"), {})[1]["st"] == "diff")
check("관리번호 견적서 없고 앞 수주 견적만 단가 다름 = 없음(따라갈 것 없음 → 이 수주 견적서 올릴 자리)",
      Q.resolve(o2[:2], {1: F(20, up=1000000, amt=1000000)}, None, {})[2]["st"] == "none")

# main 연결 — 등록 화면 비슷한 지난 견적(_z141_similar) · 견적 관리 판(_z105_board) 숫자
with contextlib.redirect_stdout(io.StringIO()):
    import app.main as M
c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
c.execute("CREATE TABLE projects(id INTEGER PRIMARY KEY, mgmt_code TEXT, name TEXT, customer_id INTEGER, customer_name TEXT, model_name TEXT, equip_name TEXT, is_archived INTEGER)")
c.execute("CREATE TABLE orders(id INTEGER PRIMARY KEY, project_id INTEGER, order_no TEXT, status TEXT, order_date TEXT, currency TEXT, total_amount REAL)")
M._z61_table(c)
c.executemany("INSERT INTO projects VALUES(?,?,?,?,?,?,?,0)", [(1, "006T2608", "PBA", 7, "한국성전", "VMS0952", "VSWR 검사기"),
                                                                 (2, "010T2601", "다른 것", 8, "다른회사", "VMS0952", "VSWR 검사기"),
                                                                 (3, "011M2601", "무관", 9, "무관회사", "ZZZ", "로봇")])
c.executemany("INSERT INTO orders VALUES(?,?,?,?,?,?,?)", [(1, 1, "T-260826-1", "SHIPPED", "2026-08-26", "KRW", 2010000), (2, 1, "T-260911-1", "CANCELLED", "2026-09-11", "KRW", 1)])
for fid, pid, oid in ((1, 1, None), (2, 2, None), (3, 3, None)):
    c.execute("INSERT INTO project_quote_files(id, tok, project_id, order_id, orig_name, created_at, read_json) VALUES(?,?,?,?,?,?,?)",
              (fid, "t%d" % fid, pid, oid, "q%d.xlsx" % fid, "2026-08-01 10:00",
               json.dumps({"fields": {"amount": 12060000, "currency": "KRW", "quote_date": "2026-08-0%d" % fid, "item_name": "VSWR 검사기"}})))
s = M._z141_similar(c, "7", "", "VMS0952", "")
check("비슷한 견적: 같은 고객사 먼저 · 모델 같은 다른 고객사 다음 · 무관한 것 없음", [x["fid"] for x in s] == [1, 2] and s[0]["same_cu"] and "VMS0952" in s[0]["hit"], s)
check("비슷한 견적: 수주 여부 = 취소 뺀 수주 건수", s[0]["orders"] == 1 and s[0]["order_nos"] == ["T-260826-1"] and s[1]["orders"] == 0)
check("비슷한 견적: 고객사 이름만으로도(띄어쓰기 무시)", [x["fid"] for x in M._z141_similar(c, "", "한국 성전", "", "")] == [1])
check("비슷한 견적: 최대 3건", len(M._z141_similar(c, "", "", "VMS0952 로봇 VSWR", "")) <= 3)
check("비슷한 견적 결과에 원가 칸 없음(앞장 머리 값만)", not any(k for x in s for k in x if "cost" in k or "원가" in k))
src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check("새 API 두 곳 권한 확인(can_use_sales·can_view_sales)", src.count("if not (can_use_sales(u) and can_view_sales(u)):") >= 2 and
      "/api/quotes-z141/similar" in src and "/api/quote-so-ack/{oid}" in src)
tpl_q = open(os.path.join(ROOT, "app", "templates", "sales_quotations.html"), encoding="utf-8").read()
check("견적 관리: 견적 있음(이 수주 + 관리번호 사용) · 금액 다름 · 정말 없음", "견적 있음" in tpl_q and "정말 없음" in tpl_q and "금액 다름(확인 필요)" in tpl_q and "🔗" in tpl_q)
tpl_f = open(os.path.join(ROOT, "app", "templates", "_v5_partials", "quote_fill.html"), encoding="utf-8").read()
check("등록 화면 안내 한 줄(z1191z156: 이번 수주번호에 붙음)", "[등록]하면 이번에 만드는 수주번호에 붙습니다" in tpl_f)
print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
