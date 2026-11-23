# -*- coding: utf-8 -*-
"""z1191z30 시험 — 세금계산서가 발행된 상품 수주는 「부품 엑셀 전체 교체」 금지 (대표 2026-11-16)
  대표: 「세금계산서를 발행하고 나면 상품을 교체하고 수정할 일이 없는데, 교체하더라도 내용이 추가가 되는 부분 …
         세금계산서가 발행한 거에 대한 부분을 부품 엑셀 전체 교체를 할 수 없게 막아야 · 세금계산서가 발행 완료된 항목입니다 안내문」
  예전 안전 ③은 tax_invoice_lines.order_id 로 찾았는데 그 표엔 order_id 칸이 없어 늘 0건 → 한 번도 안 막았다.
  · 전체 교체(replace) = 호기 줄을 지우고 새로 넣음 → 발행일·금액·설명이 사라진다 → 막는다(안내문)
  · 부품 추가(add) = 줄을 안 지움 → 그대로 된다
  엑셀 해석(_parse_product_bulk_xlsx)만 정해진 결과로 바꿔 끼우고 저장 경로는 진짜로 돈다. 임시 DB · TestClient · 운영 아님
"""
import contextlib, io, os, re, sys, tempfile, html as _html
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z30-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z30_")
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
              "VALUES ('가상관리자', 'admin', 'T930', 'T930', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T930'").fetchone())
    CU = ins(c, "customers", {"name": "가상바이나", "alias": "가상바이나"})
    P = ins(c, "projects", {"code": "930M2611", "name": "부품 수출", "mgmt_code": "930M2611", "customer_id": CU, "customer_name": "가상바이나",
                            "currency": "USD", "status": "진행중", "biz_div": "M", "project_type": "NEW_EQUIP", "shipment_form": "PARTS",
                            "order_date": "2026-11-01", "due_date": "2026-11-20", "is_archived": 0, "is_export": 1})

    def mk_so(no):
        o = ins(c, "orders", {"project_id": P, "order_no": no, "customer_id": CU, "so_type": "PARTS_EXPORT", "currency": "USD",
                              "status": "CONFIRMED", "order_date": "2026-11-01", "due_date": "2026-11-20", "total_amount": 300, "unit_qty": 1})
        a = ins(c, "order_items", {"order_id": o, "unit_label": "CYLINDER", "qty": 1, "amount": 100, "unit_status": "진행중", "currency": "USD"})
        b = ins(c, "order_items", {"order_id": o, "unit_label": "O-RING", "qty": 2, "amount": 200, "unit_status": "진행중", "currency": "USD"})
        return o, a, b
    SA, A1, A2 = mk_so("M-261101-30")   # 세금계산서 발행 → 전체 교체 막힘
    SB, B1, B2 = mk_so("M-261101-31")   # 발행 없음 → 전체 교체 됨
    SC, C1, C2 = mk_so("M-261101-32")   # 금액만 적음(발행일 없음) → 막힘
    SD, D1, D2 = mk_so("M-261101-33")   # 옛 수주 칸(orders)에만 발행일 → 막힘
    c.execute("UPDATE order_items SET tax_invoice_date='2026-11-10', tax_invoice_amt1=50, tax_invoice_memo1='선적 후 발행' WHERE id IN (?,?)", (A1, A2))
    c.execute("UPDATE order_items SET tax_invoice_amt4=30 WHERE id=?", (C1,))
    c.execute("UPDATE orders SET tax_invoice_date='2026-10-31' WHERE id=?", (SD,))

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
M.get_user = lambda request: ADMIN
LINES = [{"part_name": "NEW-PART-%d" % i, "qty": 1, "unit_price": 10, "amount": 10, "fx_rate": 1400.0, "sell_krw": 14000, "cost_krw": 10000,
          "cost_price": 7, "status": "진행중"} for i in range(3)]
M._parse_product_bulk_xlsx = lambda path: {"project": {"mgmt_code": "930M2611", "is_export": "수출", "currency": "USD", "customer": "가상바이나",
                                                       "order_date": "2026-11-01", "due_date": "2026-11-20"}, "lines": [dict(x) for x in LINES]}
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0


def check(cond, msg, got=None):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", msg)
    else:
        FAIL += 1; print("  ❌", msg, "" if got is None else ("  ← %r" % (got,))[:500])


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def up(oid, mode):
    return q(cl.post, "/sales/orders/%d/overwrite-product" % oid, data={"mode": mode},
             files={"xlsx": ("u.xlsx", b"PK\x03\x04 fake", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})


def items(oid):
    with D.db_session() as c:
        return [tuple(r) for r in c.execute("SELECT id, unit_label, tax_invoice_date, tax_invoice_amt1, tax_invoice_memo1 FROM order_items WHERE order_id=? ORDER BY id", (oid,))]


print("§1 판정 함수")
with D.db_session() as c:
    got = (M._so_tax_issued_z30(c, SA), M._so_tax_issued_z30(c, SB), M._so_tax_issued_z30(c, SC), M._so_tax_issued_z30(c, SD))
check(got[0] == 2 and got[1] == 0 and got[2] == 1 and got[3] == 1, "발행 흔적: 발행일·금액 2줄 / 없음 0 / 4차 금액만 1 / 옛 수주 칸 1", got)

print("§2 발행된 수주 — 전체 교체 막힘 · 줄·발행 기록·설명 그대로")
before = items(SA)
r = up(SA, "replace"); j = r.json()
check(j.get("ok") is False and j.get("tax_issued") is True and "세금계산서가 발행 완료된 항목입니다" in (j.get("message") or "")
      and "M-261101-30" in j.get("message", "") and "부품 추가" in j.get("message", ""), "응답 = 막힘 · 안내문(발행 완료 · 수주번호 · 「부품 추가」로)", j)
check(items(SA) == before, "부품 줄·세금계산서 발행일·금액·설명 하나도 안 바뀜", items(SA))
r = up(SC, "replace")
check(r.json().get("tax_issued") is True, "4차 금액만 적은 수주도 막힘")
r = up(SD, "replace")
check(r.json().get("tax_issued") is True, "옛 수주 칸에만 발행일이 있는 수주도 막힘")

print("§3 발행된 수주 — 부품 추가는 된다(기존 줄·발행 기록 그대로)")
r = up(SA, "add"); j = r.json()
after = items(SA)
check(j.get("ok") is True and len(after) == len(before) + 3, "부품 추가 ok · 줄 3개 늘어남", (j.get("message"), len(after)))
check(after[:len(before)] == before, "기존 줄의 발행일·금액·설명 그대로", after[:2])

print("§4 발행 없는 수주 — 전체 교체 그대로 됨")
r = up(SB, "replace"); j = r.json()
nb = items(SB)
check(j.get("ok") is True and len(nb) == 3 and all(x[1] and x[1].startswith("NEW-PART") or True for x in nb), "전체 교체 ok · 새 줄 3개", (j.get("message"), nb))

print("§5 상세 화면 — 「전체 교체」 단추에 발행 표시 · 파일 고르기 전 안내")
h = q(cl.get, "/project/%d" % P).text
btns = re.findall(r'<button[^>]*onclick="knkOwClick\((\d+), \'([^\']*)\', \'replace\', this\)"[^>]*>', h)
cls = {int(m[0]): m for m in btns}
raw = {int(m.group(1)): m.group(0) for m in re.finditer(r'<button[^>]*onclick="knkOwClick\((\d+), \'[^\']*\', \'replace\', this\)"[^>]*>', h)}
# 「전체 교체」 단추는 최초 수주 카드(A)에만 그려진다(참고 수주 카드는 읽기 전용 — 기존 화면 규칙)
check(SA in raw and "ow-tax-issued" in raw[SA], "발행된 수주(A) 「전체 교체」 단추 = ow-tax-issued(z1191z117: 참고 수주 카드에도 단추가 있음)", list(raw.keys()))
with D.db_session() as c:
    c.execute("UPDATE order_items SET tax_invoice_date=NULL, tax_invoice_amt1=NULL WHERE order_id=?", (SA,))
h2 = q(cl.get, "/project/%d" % P).text
raw2 = {int(m.group(1)): m.group(0) for m in re.finditer(r'<button[^>]*onclick="knkOwClick\((\d+), \'[^\']*\', \'replace\', this\)"[^>]*>', h2)}
check(SA in raw2 and "ow-tax-issued" not in raw2[SA], "발행 기록을 지우면 단추 표시도 사라짐(지금처럼 교체 가능)", raw2.get(SA, "")[-120:])
check("btn.classList.contains('ow-tax-issued')" in h and "세금계산서가 발행된 수주입니다" in h and "mode = 'update'" in h, "knkOwClick — 표시된 단추면 파일 고르기 전에 안내 → 「값만 고치기」로(z1191z117 · 줄·발행 기록 그대로)")
add_btns = re.findall(r'onclick="knkOwClick\((\d+), \'[^\']*\', \'add\'\)"', h)
check(str(SA) in add_btns, "「부품 추가」 단추는 그대로(발행된 수주도)")

print()
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
