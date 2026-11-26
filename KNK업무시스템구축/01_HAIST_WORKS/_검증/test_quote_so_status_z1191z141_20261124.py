# -*- coding: utf-8 -*-
"""z1191z141 (대표 11-24 「진행」): 수주마다 견적서 상태 · 등록 화면 비슷한 지난 견적
z1191z160 (대표 11-26)로 바꾼 것: 🔗 따라가기·⚠ 금액 다름·「확인했음」 시험 → 「수주마다 그 수주 견적서 전부(여러 장) · 없으면 없음 · 비교 없음」"""
import io, contextlib, json, os, sqlite3, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app import quote_link as Q
R = []


def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:300]))


def F(fid, amt=None, cur="KRW"):
    return {"id": fid, "amt": amt, "cur": cur, "orig_name": "q%d.xlsx" % fid}


def O(oid, no):
    return {"id": oid, "order_no": no}


# 가격 읽기(보여 주기용 · 비교 아님)
check("견적 단가 없으면 합계 ÷ 수량(읽은 값 보여 주기용)", Q.q_price({"amount": "12,060,000", "qty": 6})[0] == 2010000)
# z1191z160 (대표 11-26 「검토하는 기능을 빼줘 · 여러 개 등록될 수 있게」): 금액 비교·따라가기·확인했음 없음
check("z1191z160: 금액 비교 함수(same·match·o_price) 없음", not any(hasattr(Q, n) for n in ("same", "match", "o_price")))
orders = [O(1, "T-260826-1"), O(2, "T-260911-1"), O(3, "T-260930-9"), O(4, "T-261016-4")]
r = Q.resolve(orders, {2: [F(20, 2010000)]})
check("이 수주에 올린 견적 = ok · 그 견적서만", r[2]["st"] == "ok" and [x["id"] for x in r[2]["fs"]] == [20])
check("z1191z160: 뒤 수주는 앞 수주 견적을 따라가지 않음 = 없음", r[3]["st"] == "none" and r[3]["fs"] == [] and r[1]["st"] == "none", r)
r = Q.resolve(orders, {2: [F(20, 2010000), F(25, 1500000), F(22, 9)]})
check("z1191z160: 한 수주에 여러 장 = 모두(최근 위) · 금액이 달라도 ⚠ 없음", r[2]["st"] == "ok" and [x["id"] for x in r[2]["fs"]] == [25, 22, 20], r[2])
check("결과 칸 = st·fs 뿐(via·cmp·acked 없음)", set(r[2]) == {"st", "fs"})
check("한 장만 넘겨도(옛 부르는 모양) 목록으로", Q.resolve([O(5, "X")], {5: F(30)})[5]["fs"][0]["id"] == 30)
check("견적서 하나도 없음 = 없음", Q.resolve(orders, {})[1] == {"st": "none", "fs": []})
check("옛 인자(관리번호 견적서·확인 목록)를 넘겨도 쓰지 않음", Q.resolve(orders, {}, F(10, 1), {2: 10})[2]["st"] == "none")

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
check("비슷한 견적 API 권한 확인(can_use_sales·can_view_sales) · z1191z160: 「확인했음」 주소 없음", src.count("if not (can_use_sales(u) and can_view_sales(u)):") >= 2 and
      "/api/quotes-z141/similar" in src and '@app.post("/api/quote-so-ack/' not in src)
tpl_q = open(os.path.join(ROOT, "app", "templates", "sales_quotations.html"), encoding="utf-8").read()
check("견적 관리: 견적서 있음 · 견적서 없음 · z1191z160: 금액 다름·🔗 따라가기 없음", "견적서 있음" in tpl_q and "견적서 없음" in tpl_q and "금액 다름(확인 필요)" not in tpl_q and "🔗" not in tpl_q)
tpl_f = open(os.path.join(ROOT, "app", "templates", "_v5_partials", "quote_fill.html"), encoding="utf-8").read()
check("등록 화면 안내 한 줄(z1191z156: 이번 수주번호에 붙음)", "[등록]하면 이번에 만드는 수주번호에 붙습니다" in tpl_f)
print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
