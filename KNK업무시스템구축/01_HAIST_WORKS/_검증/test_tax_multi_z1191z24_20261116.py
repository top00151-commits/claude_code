# -*- coding: utf-8 -*-
"""z1191z24 시험 — 수주(호기) 세금계산서 최대 10장 (대표 2026-11-16 「묶어 발행만 보류하고 나머지는 진행」)
  안지연·이새롬 프로 답: ① 비율로 나누지 말고 ＋로 한 장씩 추가 · 합이 맞으면 끝 ② 미수금 이름 = 1차·2차·3차…
                         ③ 소모품 해당 없음 ⑤ 작업일정표엔 세금계산서 1칸만 · 2~10은 숨김(필요할 때 추가)
  가상 수주 1건(호기 2대 · ₩1,000,000)을 1~5차(40·20·20·10·10%)로 발행 → 작업일정표·펼친 호기·상세·매출 홈·
  매출 보고서·미수금·같은 날 발행·엑셀이 모두 1~10차를 같은 기준으로 보는지.  임시 DB · TestClient · 운영 아님
"""
import contextlib, io, json, os, re, sys, tempfile, html as _html
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z24-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z24_")
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
              "VALUES ('가상관리자', 'admin', 'T924', 'T924', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T924'").fetchone())
    CU = ins(c, "customers", {"name": "가상전기", "alias": "가상전기"})
    P = ins(c, "projects", {"code": "924M2609", "name": "가상 장비", "mgmt_code": "924M2609", "customer_id": CU, "customer_name": "가상전기",
                            "currency": "KRW", "status": "진행중", "biz_div": "M", "project_type": "NEW_EQUIP", "shipment_form": "ASSEMBLY",
                            "order_date": "2026-09-01", "due_date": "2026-09-20", "is_archived": 0, "order_amount": 1000000})
    A = ins(c, "orders", {"project_id": P, "order_no": "M-260901-24", "customer_id": CU, "so_type": "EQUIPMENT", "currency": "KRW",
                          "status": "SHIPPED", "order_date": "2026-09-01", "due_date": "2026-09-20", "total_amount": 1000000})
    I1 = ins(c, "order_items", {"order_id": A, "unit_label": "1호기", "qty": 1, "amount": 500000, "unit_status": "출하", "due_date": "2026-09-20"})
    I2 = ins(c, "order_items", {"order_id": A, "unit_label": "2호기", "qty": 1, "amount": 500000, "unit_status": "출하", "due_date": "2026-09-20"})
    # 소모품(1~3차 그대로) — 같은 달
    CO = ins(c, "consumable_orders", {"co_no": "C-260905-24", "mgmt_code": "924C2609", "customer_id": CU, "customer_name": "가상전기",
                                      "currency": "KRW", "total_amount": 30000, "status": "CONFIRMED", "order_date": "2026-09-05",
                                      "due_date": "2026-09-21", "tax_invoice_date": "2026-09-30", "tax_invoice_amt1": 30000})

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
        FAIL += 1; print("  ❌", msg, "" if got is None else ("  ← %r" % (got,))[:600])


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def db1(sql, *a):
    with D.db_session() as c:
        return c.execute(sql, a).fetchone()


def rowtax(field, value):
    return q(cl.post, "/sales/schedule/row-tax", json={"ref_id": P, "uids": "", "field": field, "value": value})


def board_cell(kind, ref):
    h = q(cl.get, "/sales/schedule?ym=2026-09").text
    for m in re.finditer(r'<tr[^>]*data-kind="%s"[^>]*data-ref="%d"[^>]*>(.*?)</tr>' % (kind, ref), h, re.S):
        td = re.search(r'<td class="c-info cw-taxinv1([^"]*)"([^>]*)>(.*?)</td>', m.group(1), re.S)
        if td:
            return td.group(1), td.group(2), td.group(3), h
    return None, None, None, h


print("§1 칸·상수 — 호기 4~10차 · 날짜 검사 · 서버 상한 한 곳")
with D.db_session() as _c:
    oic = {r[1] for r in _c.execute("PRAGMA table_info(order_items)")}
    cocols = {r[1] for r in _c.execute("PRAGMA table_info(consumable_orders)")}
check(all(("tax_invoice_date%d" % n) in oic and ("tax_invoice_amt%d" % n) in oic for n in range(4, 11)), "order_items 에 4~10차 발행일·금액 칸(14개)")
check(D.TAX_TIER_MAX == M._TI_MAX == 10 and D.TAX_TIER_MAX_CONS == M._TI_MAX_CONS == 3, "상한 = 수주 10 · 소모품 3(DB·서버 같은 값)")
check("tax_invoice_date10" in D.DATE_CELL_FIELDS and "tax_invoice_date4" in D.DATE_CELL_FIELDS, "날짜 칸 검사 목록에 4~10차 발행일")
check("tax_invoice_date4" not in cocols, "소모품 칸은 1~3차 그대로(4차 안 만듦 · 해당 없음)")

print("§2 작업일정표 줄 저장(/row-tax) — 1~5차 · 호기 2대에 나눠 저장 · 잘못된 값 막기")
plan = [(1, "2026-09-05", 400000), (2, "2026-09-12", 200000), (3, "2026-09-19", 200000), (4, "2026-09-26", 100000), (5, "2026-09-30", 100000)]
oks = []
for n, d, a in plan:
    r1 = rowtax(M._ti_dcol(n), d); r2 = rowtax(M._ti_acol(n), str(a))
    oks.append(r1.status_code == 200 and r1.json().get("ok") and r2.status_code == 200 and r2.json().get("ok"))
check(all(oks), "1~5차 발행일·금액 저장 응답 ok", oks)
check(tuple(db1("SELECT tax_invoice_date4, tax_invoice_amt4, tax_invoice_amt5 FROM order_items WHERE id=?", I1)) == ("2026-09-26", 50000.0, 50000.0),
      "4·5차 = 호기마다 반씩(₩50,000) · 발행일 그대로", tuple(db1("SELECT tax_invoice_date4, tax_invoice_amt4, tax_invoice_amt5 FROM order_items WHERE id=?", I1)))
r = rowtax("tax_invoice_date5", "100000")
check(r.status_code == 400, "5차 발행일에 금액 글자 → 막음(400 · z1132 날짜만)", r.status_code)
r = rowtax("tax_invoice_date11", "2026-09-30")
check(r.status_code == 400, "11차 → 막음(최대 10장)", r.status_code)

print("§3 작업일정표 화면 — 세금계산서 1칸(첫 장 + 「＋4장 · 합」) · 2·3세금계산서 칸 없음")
cls, attrs, inner, H = board_cell("project", P)
check(inner is not None, "프로젝트 줄 세금계산서 칸이 있다", (H[:300] if inner is None else None))
if inner is not None:
    tis = json.loads(_html.unescape(re.search(r'data-tis="([^"]*)"', attrs).group(1)))
    check(len(tis) == 10 and tis[3] == ["2026-09-26", 100000.0] and tis[4] == ["2026-09-30", 100000.0] and tis[5] == ["", None],
          "data-tis = 10칸 · 4·5차 값 · 6차 빈칸", tis)
    check('data-timax="10"' in attrs and 'data-edit="taxinv1"' in attrs and "editable taxinv-cell" in cls, "프로젝트 줄 상한 10 · 누르면 입력 창(taxinv1)")
    check("2026-09-05" in inner and "₩400,000" in inner and "＋4장 · " in inner and "합 ₩1,000,000" in re.sub(r"<[^>]+>", "", inner), "칸 글 = 1차 날짜·금액 + 「＋4장 · 합 ₩1,000,000」", inner)
    check("5차 2026-09-30" in _html.unescape(attrs), "풍선 도움말에 5차까지", _html.unescape(attrs)[:300])
check('data-col="tax_inv2"' not in H and 'data-col="tax_inv3"' not in H and ">2세금계산서<" not in H, "2·3세금계산서 칸(머리글·칸·colgroup) 없음")
check("'statement','tax_inv1','sales_owner'" in H.replace("{% endif %}", "") or "'statement','tax_inv1'" in H, "칸 목록(JS COL_KEYS) = tax_inv1 하나")
check("knkTaxMulti" in H and 'data-ti-max="10"' in H and "var TI_MAX_JS = parseInt(" in H, "공용 입력 창(knk_tax_multi) 포함 · 상한 10(#schedWrap data-ti-max → JS)")
c_cls, c_attrs, c_inner, _ = board_cell("consumable", CO)
check(c_attrs is not None and 'data-timax="3"' in c_attrs and "2026-09-30" in (c_inner or ""), "소모품 줄 = 1칸 · 상한 3(1~3차 그대로)", (c_attrs, c_inner))

print("§4 펼친 호기(/units) · 호기 한 칸 저장(/unit-field)")
j = q(cl.get, "/sales/schedule/units?kind=project&ref_id=%d" % P).json()
u1 = [u for u in j.get("units", []) if u.get("iid") == I1]
check(u1 and u1[0].get("tax_invoice_date5") == "2026-09-30" and u1[0].get("tax_invoice_amt5") == 50000.0 and "tax_invoice_date10" in u1[0],
      "호기 JSON 에 4~10차(5차 = 2026-09-30 ₩50,000)", (u1[0] if u1 else j))
r = q(cl.post, "/sales/schedule/unit-field", json={"iid": I2, "field": "tax_invoice_amt7", "value": "1,234"})
check(r.status_code == 200 and r.json().get("ok") and db1("SELECT tax_invoice_amt7 FROM order_items WHERE id=?", I2)[0] == 1234.0, "호기 7차 금액 저장", r.text[:200])
r = q(cl.post, "/sales/schedule/unit-field", json={"iid": I2, "field": "tax_invoice_amt7", "value": ""})
check(r.status_code == 200 and db1("SELECT tax_invoice_amt7 FROM order_items WHERE id=?", I2)[0] is None, "빈 값 = 지움(NULL)")
r = q(cl.post, "/sales/schedule/unit-field", json={"iid": I2, "field": "tax_invoice_date7", "value": "abc"})
check(r.status_code == 400, "호기 7차 발행일에 글자 → 막음", r.status_code)

print("§5 매출 홈 최종매출 · 매출 보고서 세금계산서 기준 — 1~10차 모두")
with D.db_session() as c:
    rates = M._fx_load_rates(c)
    oi_map, _ = M._board_tax_oi_map()
    k3 = M._sales_3way(c, rates, oi_map, "year", "2026", "1", "1")["kpi"]
    lines = [x for x in M._z17_lines(c, rates, oi_map, "tax")[0] if x.get("kind") == "project" and x.get("code") == "924M2609"]
check(round(k3["final"]) == 1000000 + 30000, "최종매출 = 수주 1~5차 ₩1,000,000 + 소모품 ₩30,000(예전 코드는 4·5차 빠져 ₩830,000)", k3["final"])
check(sorted({x["nth"] for x in lines}) == ["1차", "2차", "3차", "4차", "5차"] and round(sum(x["amt"] for x in lines)) == 1000000,
      "보고서 줄 = 1~5차 · 합 ₩1,000,000", sorted({x["nth"] for x in lines}))

print("§6 미수금(납품·수금) — 이름 1차·2차…5차 · 전액 발행")
h = q(cl.get, "/sales/shipments-receipts?ym=2026-09").text
check("1차 ✓" in h and "5차 ✓" in h, "세금계산서 이름 = 1차 … 5차", re.findall(r"sr-tok on\">([^<]*)", h)[:8])
check("계약금 ✓" not in h and "잔금 ✓" not in h and "중도금 ✓" not in h, "계약금·중도금·잔금 이름 안 씀(대표 확정 · 두 분 답)")
with D.db_session() as c:
    oi_map, _ = M._board_tax_oi_map()
s = sum(float(oi_map[i].get("t%da" % n) or 0) for i in (I1, I2) for n in range(1, 11))
check(round(s) == 1000000, "호기 지도(_board_tax_oi_map) 1~10차 합 = ₩1,000,000(미수금·매출 공용)", s)

print("§7 같은 날 함께 발행 — 차수 1~10")
r = q(cl.get, "/sales/tax-invoice/same-day?tier=5&date=2026-09-30&iid=%d" % I1)
check(r.status_code == 200 and r.json().get("ok") and len(r.json().get("items", [])) >= 1, "5차(2026-09-30) 조회 ok(소모품 칸은 1~3차라 건너뜀)", r.text[:200])
r = q(cl.get, "/sales/tax-invoice/same-day?tier=11&date=2026-09-30&iid=%d" % I1)
check(r.status_code == 400, "11차 → 400", r.status_code)

print("§8 프로젝트 상세 수주 내역 — 세금계산서 1칸(data-multi)")
h = q(cl.get, "/project/%d" % P).text
check('data-multi="1"' in h and h.count('data-multi="1"') == 2, "호기 2대 모두 세금계산서 1칸(입력 창)", h.count('data-multi="1"'))
check("＋4장 · <span class=\"ti-sum\">합 ₩500,000</span>" in h, "호기 칸 = 1차 + 「＋4장 · 합 ₩500,000」")
check('data-datefield="tax_invoice_date2"' not in h and "최대 10장" in h, "2·3차 칸 없음 · 머리글 「최대 10장」")

print("§9 작업일정표 엑셀 저장 — 쓴 차수까지만 칸 추가")
import openpyxl  # noqa: E402
r = q(cl.get, "/sales/schedule/export.xlsx?ym=2026-09")
ws = openpyxl.load_workbook(io.BytesIO(r.content)).active
hdr = [c.value for c in ws[1]]
check("4세금계산서" in hdr and "5세금계산서" in hdr and "6세금계산서" not in hdr, "머리글 4·5세금계산서 있음 · 6 없음", hdr[-14:])
row = None
for rr in ws.iter_rows(min_row=2, values_only=True):
    if rr and rr[0] == "924M2609":
        row = rr
i5 = hdr.index("5세금계산서") if "5세금계산서" in hdr else None
check(row is not None and i5 is not None and row[i5] == "2026-09-30" and row[i5 + 1] in (100000, 100000.0), "5차 발행일·금액 칸 값", (row and i5 is not None and row[i5:i5 + 2]))
r = q(cl.get, "/sales/schedule/export.xlsx?ym=2026-01")
hdr0 = [c.value for c in openpyxl.load_workbook(io.BytesIO(r.content)).active[1]]
check("3세금계산서" in hdr0 and "4세금계산서" not in hdr0, "4차 이상 안 쓴 달 = 예전 양식 그대로(올리기 양식과 같음)", hdr0[-8:])

print("§10 칸 표시 함수(서버) — 빈칸 · 2차만 · 묶음 칩")
check(str(M._ti_cell_html({})) == "＋", "빈칸 = 「＋」")
h2 = str(M._ti_cell_html({"tax_invoice_date2": "2026-10-01", "tax_invoice_amt2": 5}, "USD"))
check('<span class="ti-n">2차</span>' in h2 and "$5.00" in h2 and "ti-more" not in h2, "2차만 있으면 「2차」 표시 · 외화 소수", h2)
h3 = str(M._ti_cell_html({"tax_invoice_date": "2026-10-01", "tax_invoice_amt1": 7}, "KRW", True, 10, {"id": 3, "no": "12"}))
check("📄 #12" in h3 and "INV" in h3, "1차 묶어 발행 = 📄 칩 · 수출 = INV", h3)
check(M._ti_bundle_json({"unit:1,2|2": {"id": 9, "no": "5"}}, "unit:1,2") == '{"2": {"id": 9, "no": "5"}}', "묶음 차수 JSON")

print()
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
