# -*- coding: utf-8 -*-
"""z1191z18 시험 — 매출 보고서 엑셀 = 기술영업팀장 보고 양식(대표 「1-②, 2 넣고, 3 넣어, 4-① 진행해」 · 견본 확인 뒤 「1, 2 그대로 진행해」 2026-11-10)
  ① 1장 「보고」: 제목 · 기준 · 작성일 · 결재칸(작성/검토/팀장) · 백만원 표시(셀 값은 원) · A4 가로 한 장
  ② 총괄 = 이번 · 전월(전 분기) · 전년 같은 기간 · 올해 누계 · 전년 누계 / 선택 기준 + 참고 두 기준
  ③ 비교 기간이 WORKS 자료 시작(2025-11) 전이면 숫자 대신 「자료 부족」(대표 확정)
  ④ 보고·사업부·고객사·상세·월별 추이 합계 = 매출 홈 · 파일 이름 · 화면 단추 · 권한
  자료 준비는 z1191z17 시험과 같다(+ 4월 · 2025-11 · 2026-11 · 2025-05 줄). 임시 DB · TestClient · 운영 아님
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z18-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z18_")
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
              "VALUES ('가상관리자', 'admin', 'T917', 'T917', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T917'").fetchone())
    CU = {}
    for k, n, a in (("HS", "한국성전(주)", "한국성전"), ("VINA", "KNK VINA", "KNK VINA"), ("DT", "(주) 가상드림", "가상드림(동탄)")):
        CU[k] = ins(c, "customers", {"name": n, "alias": a})
    c.execute("INSERT OR REPLACE INTO exchange_rates (from_currency, to_currency, rate, rate_date, source) VALUES ('USD','KRW',1400,'2026-05-01','월기준')")
    c.execute("INSERT OR REPLACE INTO exchange_rates (from_currency, to_currency, rate, rate_date, source) VALUES ('USD','KRW',1450,'2026-06-01','월기준')")

    def proj(code, cust, ccy="KRW", sf="ASSEMBLY", sec=""):
        return ins(c, "projects", {"code": code, "name": "P-" + code, "mgmt_code": code, "customer_id": CU[cust], "customer_name": {"HS": "한국성전(주)", "VINA": "KNK VINA", "DT": "(주) 가상드림"}[cust],
                                   "currency": ccy, "status": "출하", "stage": "출하", "biz_div": code[3], "project_type": "NEW_EQUIP", "shipment_form": sf,
                                   "order_date": "2026-04-01", "due_date": "2026-05-20", "secondary_customer": sec, "is_archived": 0})

    def so(pid, no, cust, so_type="EQUIPMENT", ccy="KRW", end=None, **kw):
        r = {"project_id": pid, "order_no": no, "customer_id": CU[cust], "so_type": so_type, "currency": ccy, "status": "SHIPPED",
             "order_date": "2026-04-10", "due_date": "2026-05-15", "end_customer": end, "total_amount": 0}
        r.update(kw)
        return ins(c, "orders", r)

    def unit(oid, lbl, amt, **kw):
        r = {"order_id": oid, "unit_label": lbl, "qty": 1, "amount": amt, "unit_status": "출하"}
        r.update(kw)
        return ins(c, "order_items", r)

    # 검사기 · 한국성전 — 호기 계산서(5월) 2대 + 수주 계산서(호기 칸 비움 → 수주÷호기) 2대 + 6월 계산서 1대
    p1 = proj("001T2605", "HS")
    o1 = so(p1, "T-260501-1", "HS")
    unit(o1, "1호기", 2210000, tax_invoice_date="2026-05-29", tax_invoice_amt1=2210000)
    unit(o1, "2호기", 2410000, tax_invoice_date="2026-05-29", tax_invoice_amt1=2410000)
    o2 = so(p1, "T-260502-1", "HS", tax_invoice_date="2026-05-27", tax_invoice_amt1=9000000)
    unit(o2, "3호기", 4500000); unit(o2, "4호기", 4500000)
    unit(o1, "5호기", 1000000, tax_invoice_date="2026-06-10", tax_invoice_amt1=1000000, status_date="2026-06-09", due_date="2026-05-20")
    # 출하 표시 날(상태 발생일) 5월 · 납기 6월 → 출하 기준 5월
    unit(o1, "6호기", 700000, status_date="2026-05-30", due_date="2026-06-20")
    # 자동화 · KNK VINA — 상품(USD) 2차 DRT2 · 장비(USD) 2차 DREAMTECH VINA · 장비 2차 SEVT · 2차 없음
    p2 = proj("002M2605", "VINA", ccy="USD", sf="PARTS")
    o3 = so(p2, "M-260503-1", "VINA", so_type="PARTS_EXPORT", ccy="USD", end="DRT2", unit_qty=2)
    unit(o3, "BOLT", 100, currency="USD", tax_invoice_date="2026-05-20", tax_invoice_amt1=100)
    unit(o3, "NUT", 50, currency="USD", tax_invoice_date="2026-05-20", tax_invoice_amt1=50)
    p3 = proj("003T2605", "DT")
    o4 = so(p3, "T-260504-1", "VINA", ccy="USD", end="DREAMTECH VINA")
    unit(o4, "1호기", 1000, currency="USD", tax_invoice_date="2026-05-21", tax_invoice_amt1=1000)
    o5 = so(p3, "T-260504-2", "VINA", ccy="USD", end="SEVT")
    unit(o5, "2호기", 2000, currency="USD", tax_invoice_date="2026-05-22", tax_invoice_amt1=2000)
    o6 = so(p3, "T-260504-3", "VINA", ccy="USD")
    unit(o6, "3호기", 300, currency="USD", tax_invoice_date="2026-05-23", tax_invoice_amt1=300)
    # 소모품 화면 — 검사기 · 자동화(KNK VINA · 2차 여러 개)
    ins(c, "consumable_orders", {"co_no": "C1", "mgmt_code": "001C2605", "customer_name": "한국성전(주)", "currency": "KRW", "total_amount": 500000,
                                 "status": "SHIPPED", "biz_div": "T", "order_date": "2026-05-02", "due_date": "2026-05-10",
                                 "tax_invoice_date": "2026-05-31", "tax_invoice_amt1": 500000})
    ins(c, "consumable_orders", {"co_no": "C2", "mgmt_code": "002C2605", "customer_name": "KNK VINA", "currency": "USD", "total_amount": 400,
                                 "status": "SHIPPED", "biz_div": "M", "order_date": "2026-05-03", "due_date": "2026-05-12", "secondary_customer": "DSV,DRT1",
                                 "tax_invoice_date": "2026-05-31", "tax_invoice_amt1": 400})

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


def rep(basis, mode="month", m="5", y="2026"):
    oi_map, _ = q(M._board_tax_oi_map)
    with D.db_session() as c:
        rates = M._fx_load_rates(c)
        return M._sales_report_z17(c, rates, oi_map, basis, mode, y, "2", m), M._sales_3way(c, rates, oi_map, mode, y, "2", m)


# ── z1191z18 덧붙임 자료: 4월(전월) · 2025-11(자료 시작 달) · 2026-11 · 2025-05(자료 시작 전 — 비교하면 안 됨)
with D.db_session() as c:
    p9 = proj("009T2604", "HS")
    o9 = so(p9, "T-260401-9", "HS")
    unit(o9, "1호기", 1000000, tax_invoice_date="2026-04-15", tax_invoice_amt1=1000000)
    unit(o9, "2호기", 800000, tax_invoice_date="2025-11-20", tax_invoice_amt1=800000)
    unit(o9, "3호기", 1000000, tax_invoice_date="2026-11-05", tax_invoice_amt1=1000000)
    unit(o9, "4호기", 5000, tax_invoice_date="2025-05-10", tax_invoice_amt1=5000)


def xl(qs):
    r_ = q(cl.get, "/sales/report.xlsx?" + qs)
    import openpyxl
    return r_, openpyxl.load_workbook(io.BytesIO(r_.content))


def row_of(ws, text, col=1):
    for row in ws.iter_rows():
        v = row[col - 1].value
        if isinstance(v, str) and v.startswith(text):
            return row
    return None


def find_total(ws, label="합계"):
    """보고 시트에서 A칸이 정확히 label 인 줄들."""
    return [row for row in ws.iter_rows() if row[0].value == label]


print("§1 날짜 규칙(자료 시작 2025-11 · 대표 확정)")
check(M._Z18_DATA_FROM == "2025-11", "자료 시작 달 = 2025-11", M._Z18_DATA_FROM)
check(M._z18_has(2025, [11, 12]) and M._z18_has(2026, [1]) and not M._z18_has(2025, [10]) and not M._z18_has(2025, [10, 11, 12]),
      "_z18_has: 11·12월 있음 · 10월(또는 10월 섞인 분기) 없음")
check(M._z18_prev("month", 2026, "2", "1")[:2] == (2025, [12]) and M._z18_prev("quarter", 2026, "1", "1")[:2] == (2025, [10, 11, 12])
      and M._z18_prev("year", 2026, "1", "1")[:2] == (2025, list(range(1, 13))), "앞 기간: 1월→작년 12월 · 1분기→작년 4분기 · 연→전년")

print("§2 2026년 5월(세금계산서) — 파일 · 시트 · 1장 「보고」")
want5 = 2210000 + 2410000 + 9000000 + (100 + 50 + 1000 + 2000 + 300) * 1400 + 500000 + 400 * 1400
r5, wb = xl("basis=tax&mode=month&year=2026&m=5")
from urllib.parse import unquote  # noqa: E402
cd = unquote(r5.headers.get("content-disposition", ""))
today = M._kst_wall_now().strftime("%Y%m%d")
check(r5.status_code == 200 and "spreadsheetml" in r5.headers.get("content-type", ""), "엑셀 200 · xlsx 형식", r5.status_code)
check(("매出" not in cd) and ("매출보고_" in cd) and ("2026년5월_%s.xlsx" % today) in cd, "파일 이름 = 매출보고_<기준>_2026년5월_<오늘>.xlsx", cd)
check(wb.sheetnames == ["보고", "월별 추이", "고객사", "KNK VINA 2차", "프로젝트", "상세"], "시트 6개(보고 먼저)", wb.sheetnames)
ws = wb["보고"]
check(ws["A1"].value == "2026년 5월 매출 보고", "제목 「2026년 5월 매출 보고」", ws["A1"].value)
check("백만원" in (ws["A3"].value or "") and "작성일" in (ws["A3"].value or ""), "단위 백만원 · 작성일 줄", ws["A3"].value)
check([ws["H1"].value, ws["I1"].value, ws["J1"].value] == ["작성", "검토", "팀장"], "결재칸 작성/검토/팀장")
check(ws.page_setup.orientation == "landscape" and int(ws.page_setup.paperSize) == 9 and ws.page_setup.fitToWidth == 1
      and ws.page_setup.fitToHeight == 1, "인쇄: A4 가로 · 한 장(폭·높이 맞춤)")
main = row_of(ws, M._Z17_BASIS["tax"] + " 매출")
check(main is not None and abs(main[1].value - want5) <= 1 and ",," in main[1].number_format, "총괄 이번 = 손계산 · 백만원 표시(셀 값은 원)",
      main and (main[1].value, main[1].number_format))
check(main is not None and main[2].value == 1000000 and abs(main[3].value - (want5 - 1000000)) <= 1, "전월(4월) = 1,000,000 · 증감",
      main and (main[2].value, main[3].value))
check(main is not None and main[5].value == "자료 부족" and main[6].value == "—" and main[8].value == "자료 부족",
      "전년 같은 달(2025-05) · 전년 누계 = 「자료 부족」(5,000원 있어도 비교 안 함)", main and [x.value for x in main[5:10]])
check(main is not None and abs(main[7].value - (want5 + 1000000)) <= 1, "올해 누계(1~5월) = 4월 + 5월", main and main[7].value)
refs = [row for row in ws.iter_rows() if isinstance(row[0].value, str) and row[0].value.startswith("참고: ")]
check(len(refs) == 2, "참고 줄 2개(출하 · 수주)", [x[0].value for x in refs])
tots = find_total(ws)
check(len(tots) >= 2 and abs(tots[0][6].value - want5) <= 1 and abs(tots[1][1].value - want5) <= 1, "사업부 합계 · 고객사 합계 = 총괄",
      [(t[1].value, t[6].value) for t in tots])
vrow = row_of(ws, "KNK VINA 합계", col=6)
check(vrow is not None and abs(vrow[7].value - (150 + 1000 + 2000 + 300 + 400) * 1400) <= 1, "KNK VINA 합계(H칸)", vrow and vrow[7].value)
txt = "\n".join(str(c_.value) for row in ws.iter_rows() for c_ in row if isinstance(c_.value, str))
check("합계 맞춤" in txt and "2025년 11월" in txt and "자료 부족" in txt, "확인할 점: 합계 맞춤 · 자료 시작 달 안내")
check("⚠ 2차 미입력" in txt, "KNK VINA 2차 미입력 표시")
check(not any(ch in txt for ch in "🔧🏭🧪📦"), "1장에 그림 글자 없음")

print("§3 뒤 시트(원)")
det = wb["상세"]
last = list(det.iter_rows(values_only=True))[-1]
check(abs((last[14] or 0) - want5) <= 1 and "합계" in str(last[5]), "상세 합계 줄 = 총괄", last[14])
cu = wb["고객사"]
ct = [row for row in cu.iter_rows() if isinstance(row[1].value, str) and row[1].value.startswith("합계")]
check(ct and abs(ct[0][2].value - want5) <= 1, "고객사 시트 합계 = 총괄", ct and ct[0][2].value)
mo = wb["월별 추이"]
mt = row_of(mo, "합계")
check(mt is not None and any(isinstance(x.value, (int, float)) and abs(x.value - want5) <= 1 for x in mt), "월별 추이 합계 줄에 5월 값")
check(wb["프로젝트"].freeze_panes and det.auto_filter.ref, "머리줄 고정 · 거르기")

print("§4 전년 비교가 숫자로 나오는 달(2026-11 ↔ 2025-11)")
_, wb11 = xl("basis=tax&mode=month&year=2026&m=11")
m11 = row_of(wb11["보고"], M._Z17_BASIS["tax"] + " 매출")
check(m11 is not None and m11[1].value == 1000000 and m11[5].value == 800000 and abs(m11[6].value - 0.25) < 1e-9,
      "2026-11 = 1,000,000 · 전년 같은 달 800,000 · 전년 대비 25%", m11 and [x.value for x in m11[1:7]])
check(m11 is not None and m11[8].value == "자료 부족", "전년 누계(2025년 1~11월)는 자료 부족", m11 and m11[8].value)

print("§5 분기 · 연 · 출하 · 빈 기간")
_, wbq = xl("basis=tax&mode=quarter&year=2026&q=2")
mq = row_of(wbq["보고"], M._Z17_BASIS["tax"] + " 매출")
check(mq is not None and abs(mq[1].value - (want5 + 1000000 + 1000000)) <= 1 and mq[2].value == 0, "2분기 = 4·5·6월(6월 5호기 계산서 포함) · 전 분기(2026 1분기)는 자료 기간 안 → 0(숫자)",
      mq and [x.value for x in mq[1:4]])
_, wbq1 = xl("basis=tax&mode=quarter&year=2026&q=1")
mq1 = row_of(wbq1["보고"], M._Z17_BASIS["tax"] + " 매출")
check(mq1 is not None and mq1[2].value == "자료 부족" and mq1[4].value == "—", "1분기의 전 분기(2025 4분기 · 10월 섞임) = 「자료 부족」",
      mq1 and [x.value for x in mq1[1:5]])
_, wby = xl("basis=tax&mode=year&year=2026")
wy = wby["보고"]
my = row_of(wy, M._Z17_BASIS["tax"] + " 매출")
check(my is not None and wy.cell(row=6, column=3).value == "2025년(전년)" and my[2].value == "자료 부족" and my[5].value is None,
      "연간 = 올해·전년·증감·증감률 4칸 · 전년 자료 부족", my and [x.value for x in my[1:6]])
r_s, wbs = xl("basis=ship&mode=month&year=2026&m=5")
_, s3 = rep("ship", "month", "5")
ms = row_of(wbs["보고"], M._Z17_BASIS["ship"] + " 매출")
check(r_s.status_code == 200 and ms is not None and abs(ms[1].value - s3["kpi"]["prog"]) <= 1, "출하 기준 = 매출 홈 출하", ms and ms[1].value)
r_e, wbe = xl("basis=order&mode=month&year=2026&m=1")
check(r_e.status_code == 200 and wbe.sheetnames[0] == "보고", "자료 없는 달도 파일이 만들어진다", r_e.status_code)

print("§6 화면 · 권한")
h = q(cl.get, "/sales/report?basis=tax&mode=month&year=2026&m=5")
check("📥 보고용 엑셀 저장" in h.text and "📥 엑셀 저장<" not in h.text, "화면 단추 「📥 보고용 엑셀 저장」")
with D.db_session() as c:
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales) "
              "VALUES ('가상일반', 'member', 'T928', 'T928', 'sso_only_no_local_password', 1, 1, 0, 0)")
    MEM = dict(c.execute("SELECT * FROM users WHERE employee_no='T928'").fetchone())
M.get_user = lambda request: MEM
check(q(cl.get, "/sales/report.xlsx?basis=tax&mode=month&year=2026&m=5").status_code == 303, "매출 권한 없으면 엑셀 못 받음(303)")

print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
