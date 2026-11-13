# -*- coding: utf-8 -*-
"""z1191z21 시험 — 2차 고객사 칸의 대수(「SEV 8대, SEVT 3대」)로 매출을 나눔 (대표 2026-11-11 「진행해」)
  대표 정리: 상품은 베트남 법인으로 한 번에 나가지만 장비로 만든 뒤 2차 고객사 두세 곳으로 나뉘어 납품 → 2차 칸에 「SEVT 몇 대, SEV 몇 대」
             → 총 금액 ÷ 전체 대수(1대 금액) × 회사별 대수
  ① 대수 읽기(괄호·쉼표·/···+ · 대분/대/식 · 이름 속 숫자는 대수 아님 · 같은 이름은 더함 · 대수 빠지면 안 나눔)
  ② 수주(상품·장비) · 소모품(위 칸 · 품목별 칸 z1191z20 과 겹쳐도) 나누기 — 나눈 합 = 원래 · 보고서 합계 = 매출 홈(세 기준)
  ③ KNK VINA 2차 표 · 상세 줄 「8대분」 · 보고용 엑셀  ④ 입력칸 안내 글
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z21-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z21_")
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
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상관리자', 'admin', 'T923', 'T923', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T923'").fetchone())
    VINA = ins(c, "customers", {"name": "KNK VINA", "alias": "KNK VINA"})
    c.execute("INSERT OR REPLACE INTO exchange_rates (from_currency, to_currency, rate, rate_date, source) VALUES ('USD','KRW',1359,'2026-10-01','월기준')")
    P = ins(c, "projects", {"code": "006M2510", "name": "MOT 부착기 V2", "mgmt_code": "006M2510", "customer_id": VINA, "customer_name": "KNK VINA",
                            "currency": "USD", "status": "출하", "biz_div": "M", "project_type": "NEW_EQUIP", "shipment_form": "PARTS",
                            "order_date": "2026-09-30", "due_date": "2026-11-20", "secondary_customer": "SEVT", "is_archived": 0})

    def so(no, end, items, d1="2026-10-16"):
        oid = ins(c, "orders", {"project_id": P, "order_no": no, "customer_id": VINA, "so_type": "PARTS_EXPORT", "currency": "USD", "status": "SHIPPED",
                                "order_date": "2026-09-30", "due_date": "2026-10-20", "end_customer": end, "unit_qty": 11, "total_amount": sum(a for _, a in items)})
        for lb, a in items:
            ins(c, "order_items", {"order_id": oid, "unit_label": lb, "qty": 11, "amount": a, "currency": "USD", "unit_status": "출하",
                                   "status_date": "2026-10-15", "tax_invoice_date": d1, "tax_invoice_amt1": a})
        return oid
    # M-260930-1 모양: 2차 「SEV(8대분), SEVT(3대분)」 · 품목 2줄 (1,100 · 2,200 USD)
    so("M-260930-1", "SEV(8대분), SEVT(3대분)", [("MCB", 1100), ("SENSOR", 2200)])
    so("M-261001-1", "SEVT 3대, SEV 8대", [("CABLE", 1100)])
    so("M-261002-1", "DRT1 5대, DRT2 5대", [("FAN", 500)])
    so("M-261003-1", "SEV(8대분), SEVT", [("BOLT", 300)])    # 대수 빠짐 → 안 나눔(여러 고객)
    so("M-261004-1", "DSV,DRT", [("NUT", 200)])            # 대수 없음 → 지금처럼
    # 소모품: 위 칸 대수 · 품목별(z1191z20)과 겹침
    def co(no, mg, sec, items):
        t = sum(a for _, a in items)
        cid = ins(c, "consumable_orders", {"co_no": no, "mgmt_code": mg, "customer_name": "KNK VINA", "customer_id": VINA, "currency": "USD",
                                           "total_amount": t, "status": "SHIPPED", "biz_div": "M", "order_date": "2026-10-02", "due_date": "2026-10-12",
                                           "status_date": "2026-10-12", "secondary_customer": sec, "tax_invoice_date": "2026-10-20", "tax_invoice_amt1": t})
        for n, (s2, a) in enumerate(items, 1):
            ins(c, "consumable_order_items", {"co_id": cid, "line_no": n, "part_name": "부품%d" % n, "qty": 1, "unit_price": a, "amount": a, "secondary_customer": s2})
    co("C-1", "101C2610", "SEV 2대, SEVT 1대", [("", 300)])
    co("C-2", "102C2610", "DSV,DRT", [("SEV 1대, SEVT 1대", 100), ("DRT", 100)])

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


def rep(basis="tax", m="10"):
    oi_map, _ = q(M._board_tax_oi_map)
    with D.db_session() as c:
        rates = M._fx_load_rates(c)
        return M._sales_report_z17(c, rates, oi_map, basis, "month", "2026", "4", m), M._sales_3way(c, rates, oi_map, "month", "2026", "4", m)


print("§1 대수 읽기")
CASES = [("SEV(8대분), SEVT(3대분)", [("SEV", 8), ("SEVT", 3)]), ("SEVT 3대, SEV 8대", [("SEVT", 3), ("SEV", 8)]),
         ("SEV 8대분 / SEVT 3대분", [("SEV", 8), ("SEVT", 3)]), ("SEV8대·SEVT3대", [("SEV", 8), ("SEVT", 3)]),
         ("SEV 2식+SEVT 1식", [("SEV", 2), ("SEVT", 1)]), ("SEV 1식, SEVT 1식", [("SEV", 1), ("SEVT", 1)]), ("SEV 1식 ,SEVT 1식", [("SEV", 1), ("SEVT", 1)]), ("DRT1 5대, DRT2 5대", [("DRT", 10)]), ("SEVT 3대", [("SEVT", 3)]),
         ("DREAMTECH VINA 2대, SEV 1.5대", [("DRT", 2), ("SEV", 1.5)])]
for v, want in CASES:
    got = M._z21_counts(M._z17_norm2(v))
    check(got == [(a, float(b)) for a, b in want], "「%s」 → %s" % (v, want), got)
for v in ("DRT2", "DSV,DRT", "SEV(8대분), SEVT", "베트남,인도", "", None):
    check(M._z21_counts(M._z17_norm2(v)) is None, "「%s」 → 나누지 않음(대수 없음·빠짐)" % v, M._z17_norm2(v))
check(M._z17_norm2("DRT2") == "DRT" and M._z17_norm2("DSV,DRT1") == "DSV,DRT", "이름 묶기는 그대로(DRT2 → DRT · 이름 속 숫자는 대수 아님)")
# z1191z21b (11-13): 「식」으로 적으면 묶음·상세 줄도 「식」 — 계산은 같음
_l = M._z21_split({"cust2": M._z17_norm2("SEV 1식 ,SEVT 1식"), "amt": 1000.0, "krw": 1000.0, "label": "SOL V/V"})
check(M._z17_norm2("SEV 1식 ,SEVT 1식") == "SEV(1식),SEVT(1식)" and [(x["cust2"], x["label"], x["amt"]) for x in _l]
      == [("SEV", "SOL V/V · 1식", 500.0), ("SEVT", "SOL V/V · 1식", 500.0)], "「SEV 1식 ,SEVT 1식」 → 묶음 「SEV(1식),SEVT(1식)」 · 상세 「· 1식」 · 반씩",
      [(x["cust2"], x["label"], x["amt"]) for x in _l])
check(M._z17_norm2("SEV 8대, SEVT 3대") == "SEV(8대분),SEVT(3대분)" and M._z17_norm2("SEV 1식, SEV 2대") == "SEV(3대분)",
      "대·대분 = 「대분」 그대로 · 같은 이름에 단위 섞이면 대분으로 더함", (M._z17_norm2("SEV 8대, SEVT 3대"), M._z17_norm2("SEV 1식, SEV 2대")))

print("§2 매출 보고서 — 세금계산서 2026년 10월")
R, S3 = rep()
want = (1100 + 2200 + 1100 + 500 + 300 + 200 + 300 + 200) * 1359
check(abs(R["total"] - want) < 1 and abs(R["total"] - S3["kpi"]["final"]) < 1 and R["checks_ok"], "합계 = 손계산 = 매출 홈 · 합계 맞춤", (R["total"], S3["kpi"]["final"]))
A = [x for x in R["lines"] if x["so"] == "M-260930-1"]
sev = sum(x["krw"] for x in A if x["cust2"] == "SEV"); sevt = sum(x["krw"] for x in A if x["cust2"] == "SEVT")
check(len(A) == 4 and abs(sev - 3300 * 1359 * 8 / 11) < 1e-6 and abs(sevt - 3300 * 1359 * 3 / 11) < 1e-6 and abs(sev + sevt - 3300 * 1359) < 1e-6,
      "M-260930-1: 품목 2줄 × (SEV 8 · SEVT 3) = 4줄 · SEV 8/11 · SEVT 3/11 · 합 그대로", [(x["label"], x["cust2"], round(x["krw"])) for x in A])
check(all(re.search(r"(8|3)대분$", x["label"]) for x in A) and any(x["label"] == "MCB · 8대분" for x in A), "상세 줄 표시 「MCB · 8대분」", [x["label"] for x in A])
B = {x["cust2"]: round(x["krw"]) for x in R["lines"] if x["so"] == "M-261001-1"}
check(B == {"SEV": round(1100 * 1359 * 8 / 11), "SEVT": round(1100 * 1359 * 3 / 11)}, "「SEVT 3대, SEV 8대」 도 같은 결과", B)
C2 = [(x["cust2"], round(x["krw"])) for x in R["lines"] if x["so"] == "M-261002-1"]
check(C2 == [("DRT", 500 * 1359)], "「DRT1 5대, DRT2 5대」 → DRT 한 줄(10대분)", C2)
D3 = [x["cust2"] for x in R["lines"] if x["so"] == "M-261003-1"]
check(D3 == ["SEV(8대분),SEVT"], "대수 빠짐(「SEV(8대분), SEVT」) → 안 나눔", D3)
E4 = [x["cust2"] for x in R["lines"] if x["so"] == "M-261004-1"]
check(E4 == ["DSV,DRT"], "대수 없음(「DSV,DRT」) → 지금처럼", E4)
F = {x["cust2"]: round(x["krw"]) for x in R["lines"] if x["so"] == "C-1"}
check(F == {"SEV": 200 * 1359, "SEVT": 100 * 1359}, "소모품 위 칸 「SEV 2대, SEVT 1대」 → 2 : 1", F)
G = {}
for x in R["lines"]:
    if x["so"] == "C-2":
        G[x["cust2"]] = G.get(x["cust2"], 0) + x["krw"]
check({k: round(v) for k, v in G.items()} == {"SEV": 50 * 1359, "SEVT": 50 * 1359, "DRT": 100 * 1359}, "소모품 품목별(z1191z20) + 대수: 품목1 「SEV 1대, SEVT 1대」 반반 · 품목2 DRT", G)
V = {a["name"]: (round(a["total"]), a["multi"]) for a in R["vina_rows"]}
check(V.get("SEV", (0,))[0] == round(sev + B["SEV"] + 200 * 1359 + 50 * 1359) and not V["SEV"][1] and "SEV(8대분),SEVT(3대분)" not in V,
      "KNK VINA 2차 표: SEV · SEVT 따로(「SEV(8대분),SEVT(3대분)」 줄 없음)", V)
check(V.get("SEV(8대분),SEVT", (0, False))[1] and V.get("DSV,DRT", (0, False))[1], "대수 빠짐·대수 없음은 「여러 고객」으로 남음", V)
check(abs(R["vina_total"] - want) < 1, "KNK VINA 합계 = 전체", R["vina_total"])
for basis, key, mm in (("ship", "prog", "10"), ("order", "order", "9")):   # 수주 기준 = 발주일(9/30) 달
    Rb, Sb = rep(basis, mm)
    check(abs(Rb["total"] - Sb["kpi"][key]) < 1 and Rb["checks_ok"] and any(x["cust2"] == "SEVT" for x in Rb["lines"] if x["so"] == "M-260930-1"),
          "%s 기준도 나눔 · 합계 = 매출 홈" % basis, (Rb["total"], Sb["kpi"][key]))

print("§3 화면 · 보고용 엑셀")
h = q(cl.get, "/sales/report?basis=tax&mode=month&year=2026&m=10")
check(h.status_code == 200 and "✅ 합계 맞춤" in h.text and "MCB · 8대분" in h.text, "보고서 화면 200 · 합계 맞춤 · 상세 「MCB · 8대분」", h.status_code)
x = q(cl.get, "/sales/report.xlsx?basis=tax&mode=month&year=2026&m=10")
import openpyxl  # noqa: E402
wb = openpyxl.load_workbook(io.BytesIO(x.content))
vs = [r[0] for r in wb["KNK VINA 2차"].iter_rows(values_only=True) if r and isinstance(r[0], str)]
check(x.status_code == 200 and "SEV" in vs and "SEVT" in vs and not any(v.startswith("SEV(8대분),SEVT(3대분)") for v in vs), "보고용 엑셀 KNK VINA 2차 시트: SEV · SEVT 따로", vs[:8])

print("§4 입력칸 안내 글")
pd = q(cl.get, "/project/%d?so=M-260930-1" % P).text
check("여러 곳: SEV 8대, SEVT 3대" in pd, "프로젝트 상세 수주 카드 2차 칸 안내")
qf = q(cl.get, "/projects/quick?biz_div=M").text
check("여러 곳: SEV 8대, SEVT 3대" in qf, "간편 등록 2차 칸 안내")
with D.db_session() as c:
    coid = c.execute("SELECT id FROM consumable_orders WHERE co_no='C-1'").fetchone()[0]
cd = q(cl.get, "/consumables/%d" % coid).text
check("여러 곳: SEV 8대, SEVT 3대" in cd, "소모품 상세 위 2차 칸 안내")
pf = q(cl.get, "/projects/%d/edit" % P).text
check("여러 곳: SEV 8대, SEVT 3대" in pf, "프로젝트 정보 수정 2차 칸 안내")

print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
