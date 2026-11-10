# -*- coding: utf-8 -*-
"""z1191z20 시험 — 소모품 품목마다 「2차 고객사」 (이새롬 프로 엑셀 152줄 · 대표 「2 ① 진행해」 2026-11-10)
  ① DB 칸 추가(빈칸 = 발주 공통 2차)  ② 품목 한 칸 저장 · 모두 저장 · 이력 · 「None」 → 빈칸
  ③ 매출 보고서: 2차가 둘 이상이면 그 소모품 매출을 품목 금액 비율로 나눔 — 나눈 합 = 원래 · 보고서 합계 = 매출 홈 · 「여러 고객」 사라짐
     빈 품목 = 발주 공통 · 전부 같은 2차면 한 줄 · 품목 2차가 없으면 지금과 같음 · 출하 기준도
  ④ 상세 화면: 비고 다음 「2차 고객사(품목별)」 칸 · 머리 칸 수 = 너비/이름 배열 수 · 합계 줄 칸 수  ⑤ 권한
  임시 DB · TestClient · 운영 아님
"""
import contextlib, io, os, re, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z20-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z20_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()


def ins(c, table, row):
    cols = {r[1] for r in c.execute("PRAGMA table_info(%s)" % table)}
    ks = [k for k in row if k in cols]
    c.execute("INSERT INTO %s (%s) VALUES (%s)" % (table, ",".join('"%s"' % k for k in ks), ",".join("?" * len(ks))), [row[k] for k in ks])
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


with D.db_session() as c:
    COI_COLS = {r[1] for r in c.execute("PRAGMA table_info(consumable_order_items)")}
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상관리자', 'admin', 'T921', 'T921', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T921'").fetchone())
    VINA = ins(c, "customers", {"name": "KNK VINA", "alias": "KNK VINA"})
    c.execute("INSERT OR REPLACE INTO exchange_rates (from_currency, to_currency, rate, rate_date, source) VALUES ('USD','KRW',1400,'2026-05-01','월기준')")

    def co(no, mg, sec, items, tax=True, total=None):
        t = sum(a for _, a in items) if total is None else total
        cid = ins(c, "consumable_orders", {"co_no": no, "mgmt_code": mg, "customer_name": "KNK VINA", "customer_id": VINA, "currency": "USD",
                                           "total_amount": t, "status": "SHIPPED", "biz_div": "T", "order_date": "2026-05-02",
                                           "due_date": "2026-05-12", "secondary_customer": sec,
                                           "tax_invoice_date": "2026-05-20" if tax else None, "tax_invoice_amt1": t if tax else None})
        ids = []
        for n, (s2, a) in enumerate(items, 1):
            ids.append(ins(c, "consumable_order_items", {"co_id": cid, "line_no": n, "part_name": "부품%d" % n, "qty": 1, "unit": "EA",
                                                         "unit_price": a, "amount": a, "secondary_customer": s2}))
        return cid, ids
    # ㉠ 「DSV,DRT」 발주 · 품목 DRT 600 · DSV 300 · HMP 100 (엑셀 116C2605 같은 모양)
    CA, IA = co("C-A", "116C2605", "DSV,DRT", [("DRT", 600), ("DSV", 300), ("HMP", 100)])
    # ㉡ 발주 2차 SEV · 품목 DRT2 하나 + 빈칸 하나(→ SEV)
    CB, IB = co("C-B", "117C2605", "SEV", [("DRT2", 70), ("", 30)])
    # ㉢ 「DSV,KNK VINA」 · 품목 모두 DRT → 한 줄 DRT
    CC, IC = co("C-C", "118C2605", "DSV,KNK VINA", [("DRT", 40), ("DRT", 60)])
    # ㉣ 품목 2차 없음 → 지금과 같음(「DRT,HMP」 여러 고객 그대로)
    CD, ID = co("C-D", "119C2605", "DRT,HMP", [("", 50), ("", 50)])
    # ㉤ 품목 금액 0 → 나누지 않음
    CE, IE = co("C-E", "120C2605", "DSV,DRT", [("DRT", 0), ("DSV", 0)], total=200)

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
M.get_user = lambda request: ADMIN
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0


def check(cond, msg, got=None):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", msg)
    else:
        FAIL += 1; print("  ❌", msg, "" if got is None else ("  ← %r" % (got,)))


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def rep(basis="tax"):
    oi_map, _ = q(M._board_tax_oi_map)
    with D.db_session() as c:
        rates = M._fx_load_rates(c)
        return M._sales_report_z17(c, rates, oi_map, basis, "month", "2026", "2", "5"), M._sales_3way(c, rates, oi_map, "month", "2026", "2", "5")


print("§1 DB 칸")
check("secondary_customer" in COI_COLS, "consumable_order_items.secondary_customer 칸 생김(init_db)")

print("§2 매출 보고서 — 품목 비율로 나눔")
R, S3 = rep()
want = (1000 + 100 + 100 + 100 + 200) * 1400
check(abs(R["total"] - want) < 1 and abs(R["total"] - S3["kpi"]["final"]) < 1, "합계 = 손계산 = 매출 홈(나눠도 합은 그대로)", (R["total"], S3["kpi"]["final"]))
check(R["checks_ok"], "합계 맞춤(사업부·구분·고객사·프로젝트)", R["checks"])
A = [x for x in R["lines"] if x["so"] == "C-A"]
check(sorted((x["cust2"], round(x["krw"])) for x in A) == [("DRT", 840000), ("DSV", 420000), ("HMP", 140000)] and abs(sum(x["krw"] for x in A) - 1400000) < 1e-6,
      "㉠ DSV,DRT → DRT 840,000 · DSV 420,000 · HMP 140,000 (합 1,400,000)", [(x["cust2"], x["krw"], x["label"]) for x in A])
check(all(x["label"].startswith("품목 ") for x in A) and abs(sum(x["amt"] for x in A) - 1000) < 1e-9, "나눈 줄 표시 「품목 n줄」 · 원 통화 합 1,000", [x["label"] for x in A])
B = {x["cust2"]: round(x["krw"]) for x in R["lines"] if x["so"] == "C-B"}
check(B == {"DRT": 98000, "SEV": 42000}, "㉡ 품목 DRT2 → DRT · 빈칸 → 발주 공통 SEV", B)
Cc = [(x["cust2"], round(x["krw"])) for x in R["lines"] if x["so"] == "C-C"]
check(Cc == [("DRT", 140000)], "㉢ 품목이 모두 DRT → 한 줄 DRT(발주 공통 「DSV,KNK VINA」 대신)", Cc)
Dd = [(x["cust2"], round(x["krw"])) for x in R["lines"] if x["so"] == "C-D"]
check(Dd == [("DRT,HMP", 140000)], "㉣ 품목 2차 없음 → 지금과 같음(「DRT,HMP」 한 줄)", Dd)
Ee = [(x["cust2"], round(x["krw"])) for x in R["lines"] if x["so"] == "C-E"]
check(Ee == [("DSV,DRT", 280000)], "㉤ 품목 금액 0 → 나누지 않음", Ee)
V = {a["name"]: (round(a["total"]), a["multi"]) for a in R["vina_rows"]}
check(V.get("DRT") == (840000 + 98000 + 140000, False) and V.get("DSV") == (420000, False) and V.get("HMP") == (140000, False)
      and V.get("SEV") == (42000, False), "KNK VINA 2차 표: DRT · DSV · HMP · SEV 따로 · 여러 고객 아님", V)
check(abs(R["vina_total"] - want) < 1, "KNK VINA 합계 = 전체(모두 KNK VINA)", R["vina_total"])
Rs, Ss = rep("ship")
As = sorted((x["cust2"], round(x["krw"])) for x in Rs["lines"] if x["so"] == "C-A")
check(As == [("DRT", 840000), ("DSV", 420000), ("HMP", 140000)] and abs(Rs["total"] - Ss["kpi"]["prog"]) < 1, "출하 기준도 나눔 · 합계 = 매출 홈 출하", As)

print("§3 품목 한 칸 저장 · 모두 저장 · 이력")
r = q(cl.post, "/consumables/%d/items/%d/edit" % (CD, ID[0]), data={"secondary_customer": " DRT "})
with D.db_session() as c:
    v = c.execute("SELECT secondary_customer FROM consumable_order_items WHERE id=?", (ID[0],)).fetchone()[0]
    h = [tuple(x) for x in c.execute("SELECT label, old_value, new_value FROM consumable_history WHERE item_id=? AND field='secondary_customer'", (ID[0],))]
check(r.status_code == 200 and r.json().get("ok") and v == "DRT", "한 칸 저장(앞뒤 빈칸 정리) → DRT", (r.status_code, v))
check(h and h[-1][0] == "2차 고객사(품목)" and h[-1][2] == "DRT", "이력 「2차 고객사(품목)」", h)
r = q(cl.post, "/consumables/%d/save-all" % CD, json={"page_co": CD, "header": {}, "lines": [{"iid": ID[1], "fields": {"secondary_customer": "HMP"}}]})
with D.db_session() as c:
    v2 = c.execute("SELECT secondary_customer FROM consumable_order_items WHERE id=?", (ID[1],)).fetchone()[0]
check(r.status_code == 200 and v2 == "HMP", "모두 저장(💾) → HMP", (r.status_code, r.text[:120], v2))
R2, _ = rep()
D2 = {x["cust2"]: round(x["krw"]) for x in R2["lines"] if x["so"] == "C-D"}
check(D2 == {"DRT": 70000, "HMP": 70000}, "넣은 뒤 보고서: C-D = DRT 70,000 · HMP 70,000", D2)
q(cl.post, "/consumables/%d/items/%d/edit" % (CD, ID[1]), data={"secondary_customer": "None"})
with D.db_session() as c:
    v3 = c.execute("SELECT secondary_customer FROM consumable_order_items WHERE id=?", (ID[1],)).fetchone()[0]
check(v3 == "", "「None」 글자 → 빈칸", v3)

print("§4 상세 화면")
h = q(cl.get, "/consumables/%d" % CA)
html = h.text
thead = re.search(r'<table[^>]*class="[^"]*items[^"]*"[^>]*>.*?<thead>(.*?)</thead>', html, re.S)
nth = len(re.findall(r"<th[ >]", thead.group(1))) if thead else -1
wd = re.search(r"const ITEMS_COLW_DEFAULTS = \[([^\]]*)\]", html)
lb = re.search(r"const ITEMS_COL_LABELS = \[([^\]]*)\]", html)
nwd = len(wd.group(1).split(",")) if wd else -1
nlb = len(lb.group(1).split(",")) if lb else -1
check(h.status_code == 200 and "2차 고객사<br>" in html and 'data-k="secondary_customer"' in html, "상세 200 · 「2차 고객사(품목별)」 칸 · 입력칸", h.status_code)
check(nth == 19 and nwd == 19 and nlb == 19, "머리 칸 19 = 너비 배열 19 = 이름 배열 19", (nth, nwd, nlb))
foot = re.search(r"<tfoot>(.*?)</tfoot>", html, re.S)
spans = sum(int(x) for x in re.findall(r'colspan="(\d+)"', foot.group(1))) + len(re.findall(r"<td(?![^>]*colspan)", foot.group(1))) if foot else -1
check(spans == 19, "합계 줄 칸 수 19", spans)
row1 = re.search(r'<tr data-iid="%d">(.*?)</tr>' % IA[0], html, re.S)
check(row1 and 'value="DRT"' in row1.group(1) and 'placeholder="DSV,DRT"' in row1.group(1), "품목 줄: 값 DRT · 빈칸 안내 = 발주 공통 「DSV,DRT」")
check("co_items_view_v5" in html, "칸 너비 저장 키 v5(옛 18칸 설정 무효)")

print("§5 권한")
with D.db_session() as c:
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales) "
              "VALUES ('가상일반', 'member', 'T922', 'T922', 'sso_only_no_local_password', 1, 1, 0, 0)")
    MEM = dict(c.execute("SELECT * FROM users WHERE employee_no='T922'").fetchone())
M.get_user = lambda request: MEM
r = q(cl.post, "/consumables/%d/items/%d/edit" % (CA, IA[0]), data={"secondary_customer": "XXX"})
with D.db_session() as c:
    v4 = c.execute("SELECT secondary_customer FROM consumable_order_items WHERE id=?", (IA[0],)).fetchone()[0]
check(r.status_code == 403 and v4 == "DRT", "권한 없으면 403 · 그대로", (r.status_code, v4))

print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
